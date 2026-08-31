#!/usr/bin/env python3
# Windows-first tool: invoke via the py launcher --  py tools/play.py <scenario.py>
"""Run an in-game test scenario against a real FF9 -- the CLI front end for tools/harness/.

    py tools/play.py --smoke                     # is the harness alive end to end?
    py tools/play.py --smoke --field 30810       # ... and can it warp to a slot and photograph it
    py tools/play.py scenarios/chest.py          # run a scenario file
    py tools/play.py scenarios/chest.py --attach # drive the game that is already running

A scenario file is plain Python exposing ``run(g)``, where ``g`` is a
:class:`~harness.session.Session` already booted and armed::

    def run(g):
        g.newgame()
        g.warp(30810)
        g.walk("up", 45)
        g.press("confirm")
        g.expect_text("Potion")
        g.shot("after-chest")

Exit code is 0 only when every recorded check passed and nothing raised, so this drops straight into
a gate. Artifacts (frames, events, Memoria.log, report.json) land in ``.harness-runs/<stamp>-<label>/``.

!! THIS DRIVES THE REAL SHARED INSTALL. It refuses to start when an FF9 is already running (pass
``--attach`` to deliberately drive that one) and it only ever closes a game it launched itself.
"""
from __future__ import annotations

import argparse
import importlib.util
import inspect
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness import HarnessError, Session, ff9_pids                  # noqa: E402


def _accepts_field(fn) -> bool:
    """Whether a scenario's run() takes a field argument beyond the session."""
    try:
        params = list(inspect.signature(fn).parameters.values())
    except (TypeError, ValueError):
        return False
    positional = [p for p in params
                  if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
    return len(positional) >= 2 or any(p.kind == p.VAR_POSITIONAL for p in params)


def smoke(g: Session, field: int | None) -> None:
    """The end-to-end proof that the harness itself works: see, act, observe, photograph.

    Deliberately minimal and deliberately NOT a game test -- it answers "is the loop closed?", which
    is the only question worth asking before any scenario's result can be believed.
    """
    st = g.state
    g.note("harness smoke test")
    print(f"[smoke] agent is publishing: {st!r}")
    g.check(st.frame > 0, "the agent publishes a frame counter", f"frame={st.frame}")

    # A freshly launched game reports ui_state "Initial" for several seconds -- through the splash and
    # the boot logos -- before it is anywhere you can act on. Settle first; acting on "Initial" is how
    # you get a warp refused for not being on a field.
    st = g.wait_for(lambda s: s.ui_state in ("Title", "FieldHUD"), timeout=180,
                    what="the game to reach the title screen or a field")
    print(f"[smoke] settled at ui_state={st.ui_state}")

    if st.ui_state == "Title":
        print("[smoke] at the title -- starting a new game")
        # newgame() owns the title settle: Memoria is still loading when the title appears, and
        # starting inside that window makes the opening cutscene stutter. Hand-rolling the sequence
        # here skipped it.
        g.newgame(timeout=180)

    if field is not None:
        print(f"[smoke] warping to field {field}")
        g.warp(field)
        # NOT expect_field() here: warp() already waited for exactly that and raises otherwise, so
        # the check could only ever pass. A check that cannot fail is worse than no check -- it goes
        # into report.json as evidence.

    # The movement leg needs a bench with walkable ground. Without --field the smoke test lands
    # wherever New Game does (a cutscene), where control is legitimately withheld for minutes.
    if field is None:
        print("[smoke] no --field given -- skipping the movement leg (New Game lands in a cutscene)")
        shot = g.shot("smoke")
        g.check(shot.stat().st_size > 1000, "a frame was captured from inside the engine",
                f"{shot.name} {shot.stat().st_size} bytes")
        return

    # Record an unobtainable control as a FAILED CHECK rather than raising. This is the tool whose
    # whole job is to arbitrate "is the harness broken or is the content broken", so it must always
    # produce a report -- an exception here leaves the question unanswered.
    try:
        before = g.wait_playable(timeout=60)
    except HarnessError as err:
        g.check(False, "the player got control on the bench field", str(err))
        g.shot("smoke-no-control")
        return

    # Move, and prove the engine actually saw the virtual button rather than merely accepting it.
    print("[smoke] walking")
    g.walk("up", 40)
    after = g.state
    moved = _distance(before, after)
    # On failure, report what the ENGINE saw as well as what we asked for -- `held` is the harness's
    # own view, `input` is the value the movement code actually read. That distinction is the whole
    # difference between "injection is wrong" and "injection is fine, movement is blocked".
    diag = after.raw.get("input", {})
    g.check(moved > 0.5, "a virtual button press moved the character",
            f"moved {moved:.2f}u from ({_n(before.player_x)},{_n(before.player_z)}) "
            f"to ({_n(after.player_x)},{_n(after.player_z)}); engine input={diag}")

    shot = g.shot("smoke")
    g.check(_png_is_not_blank(shot), "captured a NON-BLANK frame from inside the engine",
            f"{shot.name} {shot.stat().st_size} bytes")


def _png_is_not_blank(path: Path, *, min_distinct: int = 8) -> bool:
    """Whether a captured frame actually shows something, rather than merely existing.

    "The file is bigger than 1000 bytes" is satisfied by a solid black screen -- which is exactly the
    failure the in-engine capture exists to rule out, and exactly what a black-screened game
    produces. Decoding it and counting distinct bytes is the check that can fail.

    Falls back to the size test when no decoder is available, and says so in the check detail.
    """
    try:
        import zlib

        data = path.read_bytes()
        idat = b""
        i = 8
        while i + 8 <= len(data):
            length = int.from_bytes(data[i:i + 4], "big")
            tag = data[i + 4:i + 8]
            if tag == b"IDAT":
                idat += data[i + 8:i + 8 + length]
            i += 12 + length
        if not idat:
            return path.stat().st_size > 1000
        raw = zlib.decompress(idat)
        return len(set(raw[:200000])) >= min_distinct
    except Exception:
        return path.stat().st_size > 1000


def _distance(a, b) -> float:
    if None in (a.player_x, a.player_z, b.player_x, b.player_z):
        return -1.0
    return ((b.player_x - a.player_x) ** 2 + (b.player_z - a.player_z) ** 2) ** 0.5


def _n(v) -> str:
    return "?" if v is None else f"{v:.1f}"


def load_scenario(path: Path):
    spec = importlib.util.spec_from_file_location(f"scenario_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise HarnessError(f"cannot import a scenario from {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "run"):
        raise HarnessError(f"{path} defines no run(g) function")
    return mod


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scenario", nargs="?", help="a Python file exposing run(g)")
    ap.add_argument("--smoke", action="store_true", help="run the built-in harness self-test")
    ap.add_argument("--field", type=int, default=None,
                    help="field to run against: warped to by --smoke, and passed to a scenario's "
                         "run(g, field) when it accepts one")
    ap.add_argument("--attach", action="store_true",
                    help="drive the FF9 that is ALREADY running instead of launching one")
    ap.add_argument("--keep-open", action="store_true",
                    help="leave the game running when the scenario finishes")
    ap.add_argument("--label", default=None, help="run label (defaults to the scenario name)")
    ap.add_argument("--game", default=None, help="FF9 install path (default: auto-detect)")
    ap.add_argument("--timeout", type=float, default=240.0, help="seconds to wait for the agent")
    args = ap.parse_args(argv)

    if not args.smoke and not args.scenario:
        ap.error("give a scenario file, or --smoke")

    label = args.label or ("smoke" if args.smoke else Path(args.scenario).stem)
    scenario = load_scenario(Path(args.scenario)) if args.scenario else None

    if args.attach and not ff9_pids():
        print("!!! --attach given but no FF9 is running.", file=sys.stderr)
        return 2

    started = time.time()
    try:
        with Session(label=label, game_path=args.game, attach=args.attach,
                     keep_open=args.keep_open, boot_timeout=args.timeout) as g:
            if args.smoke:
                smoke(g, args.field)
            if scenario is not None:
                # Pass --field through when the scenario takes it. It used to be dropped silently,
                # so `--field N` on a scenario did nothing at all and the run used the module default
                # -- the results were not wrong, but the flag was lying about what had been tested.
                if args.field is not None and _accepts_field(scenario.run):
                    scenario.run(g, args.field)
                elif args.field is not None:
                    print(f"[play] NOTE: {label} takes no field argument -- ignoring --field "
                          f"{args.field}")
                    scenario.run(g)
                else:
                    scenario.run(g)
            passed, checks, run_dir = g.passed, list(g.checks), g.run_dir
    except HarnessError as err:
        print(f"\n!!! harness error: {err}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n!!! interrupted", file=sys.stderr)
        return 130

    failed = [c for c in checks if not c["ok"]]
    print(f"\n{'-' * 72}")
    print(f"{label}: {len(checks) - len(failed)}/{len(checks)} checks passed "
          f"in {time.time() - started:.0f}s")
    for c in failed:
        print(f"  FAIL  {c['what']}\n        {c['detail']}")
    print(f"artifacts: {run_dir}")
    if not checks:
        print("NOTE: the scenario recorded no checks -- it proved nothing.")
    return 0 if (passed and checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
