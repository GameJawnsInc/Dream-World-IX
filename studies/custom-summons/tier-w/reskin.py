r"""TIER W rungs 4+5 -- THE RESKIN.  **Study shim over the promoted kit module.**

    py reskin.py scaffold --ef 211              # read the container, EMIT a complete guarded toml
    py reskin.py plan   bahamut_reskin.toml     # resolve every target + print the numbers, write nothing
    py reskin.py build  bahamut_reskin.toml     # stage the container + the deploy/revert scripts + previews
    py reskin.py verify bahamut_reskin.toml     # re-check what is staged, as bytes

WHAT THIS FILE IS NOW
---------------------
The reskin engine was PROMOTED into the kit as :mod:`ff9mapkit.summons.reskin`, behind the
``summon-reskin`` verb.  Everything load-bearing went, unchanged in shape: the slot-keyed palette
derivation and its alias map, the derived attribution + shared flag, the multi-writer and dual-depth
refusals, the texanim region gate, the per-target headroom measurement, the whole-set envelope, the
scenery-only path, the byte-accounting self-check and its region gates, the previews, and the
per-effect staging.  Lever #2 (texel repaint) is still refused there, for the reasons this docstring
gave when the code lived here.

This file is the STUDY's view of that module: it re-exports it under the study's own name and adds
back what is deliberately study-only.

``sys.modules[__name__] = _kit`` makes ``import reskin as RS`` yield **the kit module object
itself**.  Two consequences the study depends on:

* the underscored names (``_orthogonality``, ``_clamp01``, ``_u16``) resolve, and so does the
  attribute literally named ``R`` -- ``test_reskin`` reaches THROUGH reskin to rescore as ``RS.R.*``
  (``StockDriftError``, ``RescoreError``, ``_refuse_repo_path``, and a monkeypatch of
  ``EXPECTED_STOCK_SHA``), which only works because ``RS.R`` is the same module object the rescore
  shim re-pinned;
* ``monkeypatch.setattr(RS, "SCRATCH_W5_BASE", ...)`` mutates the object ``stage`` actually reads.

Every function defined below therefore reaches back through ``_kit.`` for anything a caller could
patch.  A bare global here would resolve in THIS file's namespace, which no test can see.

WHAT IS ADDED BACK HERE, AND WHY IT DID NOT GO
-----------------------------------------------
1. **The SCRATCH staging roots** (``SCRATCH_W4_ROOT`` / ``SCRATCH_W5_BASE`` / ``SCRATCH_ROOT`` /
   ``LEGACY_STAGING_EFFECT``, and the ``staging_root`` that reads them).  ef227's ``reskin-w4/`` kit --
   its ``mod/``, ``previews/``, ``live-snapshot/`` and ``revert_summon_reskin_227.py`` -- is a
   DEPLOYED, cast-proven artifact on this machine.  Where it sits is installation history, not a
   property of the tool, so the kit ships the same function against a local-only default base and an
   empty ``LEGACY_STAGING`` map for a caller to re-pin.  This is that caller.
2. **The reference orthogonality specs** (``DEFAULT_ORTH_SPECS``).  The kit ships NONE on purpose: a
   default filename nobody's tree contains would turn every user's orthogonality gate into a
   "SKIPPED: not found" that reads like a proof.  The study has the files, so it pins them -- as
   ABSOLUTE paths, because a relative name resolves against the SPEC's own directory and these must
   resolve the same way from anywhere.
3. **The RETIME rebuilder** (``_rebuild_retime``, registered into ``ORTH_REBUILDERS``).  W3's retime
   lane was NOT promoted -- its writing half is refusal-gated study work -- so the kit knows only how
   to rebuild the rescore sibling and answers a declared ``retime`` table with an explicit
   "study-only lane" SKIP.  Registering the rebuilder here turns that skip back into what W4 actually
   proved: a real changed-offset intersection against W3's aligned AND mis-retimed containers.
4. **The study CLI** (``main``), with its ``bahamut_reskin.toml`` default and its ``--root`` default
   of the SCRATCH staging root.  The kit registers ``summon-reskin`` in ``cli.py`` instead, where the
   spec is explicit and the staging root is a local-only default.

THE BOOTSTRAP IS LOAD-BEARING (do not reorder)
-----------------------------------------------
``import rescore as R`` first, exactly as this file has always done -- it is what puts
``thomas-swap/disasm``, ``tier-r`` and ``<repo>/ff9mapkit`` on ``sys.path``, and ``test_reskin.py``
and ``w4_gates.py`` both import ``ef_container`` on the strength of importing THIS module first.  It
is also what guarantees the rescore shim's study re-pins are in place before anything here reads
``R.SCRATCH_*``.

PROVENANCE
----------
Unchanged: the stock container is read at RUN TIME from the user's own install under a sha256 drift
guard (hash only, no stock bytes).  Staged containers and the stock-derived previews go under
``C:\gd\SCRATCH\summon-format``; the repo and the install are refused.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict, Optional, Sequence, Set, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
_STUDY = os.path.dirname(_HERE)                              # studies/custom-summons
_REPO = os.path.dirname(os.path.dirname(_STUDY))             # <repo>
sys.path.insert(0, _HERE)

import rescore as R                                          # noqa: E402  (sets up sys.path)
from ff9mapkit.summons import reskin as _kit                 # noqa: E402

#: THE ALIAS.  Every later ``import reskin`` -- and this module's own name -- now resolves to the kit
#: module object.  Names are set ON that object below, never left in this file's globals.
sys.modules[__name__] = _kit

#: W4's staging root -- ef227's, and ONLY ef227's.  Its ``mod/``, ``previews/``, ``live-snapshot/``
#: and ``revert_summon_reskin_227.py`` are a cast-proven, deployed artifact; W5 did not move them and
#: neither does the promotion.
SCRATCH_W4_ROOT = os.environ.get("FF9_RESKIN_SCRATCH",
                                 r"C:\gd\SCRATCH\summon-format\reskin-w4")

#: W5's staging BASE -- every other effect gets ``<base>\ef%03d\``, so two effects staged in one
#: session can never collide on ``mod/``, ``previews/``, ``build_manifest.json`` or the ledger.
SCRATCH_W5_BASE = os.environ.get("FF9_RESKIN_SCRATCH_W5",
                                 r"C:\gd\SCRATCH\summon-format\reskin-w5")

#: kept as a NAME for the W4 gate runner and any caller that predates the split; it is ef227's root.
SCRATCH_ROOT = SCRATCH_W4_ROOT

#: the effect whose staging layout is frozen (W4 shipped and cast it); everything else is W5-lane.
LEGACY_STAGING_EFFECT = 227

_kit._HERE = _HERE
_kit._STUDY = _STUDY
#: the repo root, re-pinned from THIS file's location, for the gates and tests that cite it by name.
_kit._REPO = _REPO
_kit.SCRATCH_W4_ROOT = SCRATCH_W4_ROOT
_kit.SCRATCH_W5_BASE = SCRATCH_W5_BASE
_kit.SCRATCH_ROOT = SCRATCH_ROOT
_kit.LEGACY_STAGING_EFFECT = LEGACY_STAGING_EFFECT
#: the kit ships this map EMPTY on purpose -- a pin belongs to an installation's deployment history,
#: not to the tool.  This is that history.
_kit.LEGACY_STAGING = {LEGACY_STAGING_EFFECT: SCRATCH_W4_ROOT}


def staging_root(effect: int, root=None) -> str:
    """The per-effect staging root, against the STUDY's SCRATCH roots.

    Byte-for-byte the kit's own function with ONE change: the default base is read off the module at
    CALL time (``_kit.SCRATCH_W5_BASE``) rather than frozen into ``STAGING_BASE`` at import, because
    ``test_reskin`` monkeypatches that constant and a default captured at import would ignore it --
    the staged container and its previews would land in the real SCRATCH root while the test
    asserted about a tmpdir.
    """
    pinned = _kit.LEGACY_STAGING.get(int(effect))
    if pinned:
        return str(pinned)
    return os.path.join(str(root or _kit.SCRATCH_W5_BASE), "ef%03d" % int(effect))


_kit.staging_root = staging_root


# ============================================================ orthogonality: the study's siblings
#: ABSOLUTE, per the kit's own note: a RELATIVE name resolves against the spec file's directory, and
#: these two must resolve to the study's reference specs from wherever a build was invoked.
DEFAULT_ORTH_SPECS: Dict[str, str] = {
    "rescore": os.path.join(_HERE, "bahamut_rescore.toml"),
    "retime": os.path.join(_HERE, "bahamut_retime.toml"),
}


def _rebuild_retime(path: str, mine: Set[int]) -> Tuple[Set[int], str]:
    """Rebuild W3's retime from its own toml and return ``(changed offsets, the detail line)``.

    BOTH containers count.  W3 builds an ALIGNED retime (the camera and the program's phase constants
    moved together) and a MIS-RETIME (the camera moved and the program did not) as its own falsifier;
    a reskin has to be disjoint from the union, or the two rungs could not ship in one container
    under either build.
    """
    import retime as _RT
    b3 = _RT.build_containers(_RT.load_spec(path), os.path.basename(path))
    d3 = {i for i in range(len(b3.orig)) if b3.orig[i] != b3.aligned[i]}
    dm = {i for i in range(len(b3.orig)) if b3.orig[i] != b3.misretime[i]}
    d = d3 | dm
    detail = ("W3 aligned changes %d bytes spanning %#x..%#x, mis-retime %d; "
              "intersection with this reskin %d"
              % (len(d3), min(d3), max(d3), len(dm), len(d & mine)))
    return d, detail


_kit.DEFAULT_ORTH_SPECS = DEFAULT_ORTH_SPECS
_kit._rebuild_retime = _rebuild_retime
#: the kit registers only ``rescore``; the retime lane is study-only, so the study registers it and
#: gets a real intersection proof back instead of the kit's honest "no rebuilder" SKIP.
_kit.ORTH_REBUILDERS = dict(_kit.ORTH_REBUILDERS, retime=_rebuild_retime)


# ============================================================ the study CLI (study-only)
def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("verb", choices=("plan", "build", "verify", "scaffold"))
    ap.add_argument("spec", nargs="?", default=None,
                    help="the *_reskin.toml (default: bahamut_reskin.toml); unused by `scaffold`")
    ap.add_argument("--root", default=None,
                    help="staging root (default: the per-effect SCRATCH root -- ef227 keeps W4's, "
                         "everything else gets reskin-w5/ef###; the repo and the install are refused)")
    ap.add_argument("--ef", type=int, default=None, help="scaffold: which effect to read")
    ap.add_argument("--from", dest="from_path", default=None,
                    help="scaffold: read this container file instead of the install (a corpus "
                         "ef###.bytes, for an effect the install cannot resolve)")
    ap.add_argument("--out", default=None, help="scaffold: write the toml here instead of stdout")
    ap.add_argument("--game", default=None)
    ap.add_argument("--previews", action="store_true",
                    help="plan: also render the previews (they are stock-derived, SCRATCH only)")
    ap.add_argument("--no-previews", action="store_true", help="build: skip the preview render")
    ap.add_argument("--live", action="store_true",
                    help="allow a --root INSIDE the game install. Off by default: this tool stages, "
                         "and the generated deploy script is what touches the install.")
    a = ap.parse_args(argv)

    try:
        from ff9mapkit import config
        game_root = config.find_game_path(a.game)
    except Exception:                                        # pragma: no cover
        game_root = None

    if a.verb == "scaffold":
        if a.ef is None:
            print("scaffold needs --ef N")
            return 2
        blob, src = (None, "")
        if a.from_path:
            with open(a.from_path, "rb") as fh:
                blob = fh.read()
            src = a.from_path
        text, _pmap = _kit.scaffold(a.ef, blob=blob, game=a.game, source=src)
        if a.out:
            from ff9mapkit import fsutil
            fsutil.atomic_write_text(a.out, text, encoding="utf-8", newline="\n")
            print("wrote %s (%d lines)" % (a.out, text.count("\n")))
        else:
            sys.stdout.write(text)
        return 0

    a.spec = a.spec or os.path.join(_kit._HERE, "bahamut_reskin.toml")
    spec = _kit.load_spec(a.spec)
    if a.root is None:
        a.root = _kit.staging_root(int(spec["reskin"]["effect"]))

    b = _kit.build(spec, a.spec, a.game)
    b.check = _kit.self_check(b)
    print("\n".join(_kit.describe(b)))
    print("\n".join(_kit.check_lines(b)))

    if a.verb == "plan":
        if a.previews:
            files = _kit.render_previews(b, Path(a.root) / "previews")
            print("\n  previews (stock-derived, SCRATCH only):")
            for f in files:
                print("    %s" % f)
        else:
            print("\nplan only -- nothing written.")
        return 0 if b.check.ok else 1

    if not b.check.ok:
        print("\nREFUSING TO STAGE -- the self-check failed (see above).")
        return 1

    if a.verb == "build":
        out = _kit.stage(b, a.root, game_root, allow_install=a.live, previews=not a.no_previews)
        print("\n  %s" % ("DEPLOYED (--live)" if a.live else "STAGED"))
        for k, v in out.items():
            if k in ("transforms", "per_target_bytes"):
                continue
            if isinstance(v, dict):
                for k2, v2 in v.items():
                    print("    %-22s %s" % (k2, v2))
            elif isinstance(v, list):
                for v2 in v:
                    print("    %-22s %s" % (k, v2))
            else:
                print("    %-22s %s" % (k, v))
        return 0

    # verify: the staged bytes, re-checked as bytes (not as a rebuild)
    v = _kit.verify(b, a.root)
    for ln in v["lines"]:
        print("  " + ln)
    ok = v["ok"] and b.check.ok
    print("\n  VERIFY: %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


_kit.main = main

if __name__ == "__main__":                                   # pragma: no cover
    raise SystemExit(main())
