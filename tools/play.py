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
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness import HarnessError, Session, ff9_pids                  # noqa: E402


def smoke(g: Session, field: int | None) -> None:
    """The end-to-end proof that the harness itself works: see, act, observe, photograph.

    Deliberately minimal and deliberately NOT a game test -- it answers "is the loop closed?", which
    is the only question worth asking before any scenario's result can be believed.
    """
    st = g.state
    g.note("harness smoke test")
    print(f"[smoke] agent is publishing: {st!r}")
    g.check(st.frame > 0, "the agent publishes a frame counter", f"frame={st.frame}")

    if st.ui_state == "Title":
        print("[smoke] at the title -- starting a new game")
        g.newgame()
    else:
        print(f"[smoke] already in game (ui_state={st.ui_state})")

    if field is not None:
        print(f"[smoke] warping to field {field}")
        g.warp(field)
        g.expect_field(field)

    g.wait_playable(timeout=60)
    before = g.state
    g.check(before.control, "the player has control", repr(before))

    # Move, and prove the engine actually saw the virtual button rather than merely accepting it.
    print("[smoke] walking")
    g.walk("up", 40)
    after = g.state
    moved = _distance(before, after)
    g.check(moved > 0.5, "a virtual button press moved the character",
            f"moved {moved:.2f}u from ({_n(before.player_x)},{_n(before.player_z)}) "
            f"to ({_n(after.player_x)},{_n(after.player_z)})")

    shot = g.shot("smoke")
    g.check(shot.stat().st_size > 1000, "captured a frame from inside the engine",
            f"{shot.name} {shot.stat().st_size} bytes")


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
    ap.add_argument("--field", type=int, default=None, help="warp here first (smoke test)")
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
