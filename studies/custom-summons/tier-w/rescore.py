r"""TIER W rung 2 -- THE CONTENT RESCORE.  **Study shim over the promoted kit module.**

    py rescore.py init   --ef 211                    # derive a guarded starter spec for ANY effect
    py rescore.py plan   bahamut_rescore.toml        # resolve + print the delta, write nothing
    py rescore.py build  bahamut_rescore.toml        # stage the override + emit the revert script
    py rescore.py verify bahamut_rescore.toml        # X1/X2 against a staged build

WHAT THIS FILE IS NOW
---------------------
The rescore engine was PROMOTED into the kit as :mod:`ff9mapkit.summons.rescore`, behind the
``summon-rescore`` verb.  Everything load-bearing went: the three hard constraints and the call sites
that enforce them (durations unchanged, byte length unchanged, the frame word's high bits never
written), the three-sequence alternates verdict, the dynamic-op disclosure gate, the drift guard,
``read_stock_effect``, the staging ledger and the scaffold generator.  None of it changed shape in
the move.

This file is the STUDY's view of that module: it re-exports it under the study's own name and adds
back what is deliberately study-only.

``sys.modules[__name__] = _kit`` makes ``import rescore as R`` yield **the kit module object
itself**.  That matters twice over:

* the underscored names the study reaches for (``_EDIT_KEYS``, ``_RESCORE_KEYS``, ``_phase_rows``,
  ``_quote_check``, ``_refuse_repo_path``, ``_refuse_install_path``, ``_Ledger``, ``_REPO``) resolve,
  which a ``from ... import *`` re-export could never carry;
* ``monkeypatch.setattr(R, "SCRATCH_W5_BASE", ...)`` and ``monkeypatch.setattr(R,
  "read_stock_effect", ...)`` mutate the object the kit's own code reads, so those tests keep
  testing something instead of patching a shadow.

Every function defined below therefore reaches back through ``_kit.`` for anything a caller could
patch.  A bare global here would resolve in THIS file's namespace, which no test and no gate can see
-- and a monkeypatch that silently does nothing is exactly the fail-open this rung is shaped against.

WHAT IS ADDED BACK HERE, AND WHY IT DID NOT GO
-----------------------------------------------
1. **The SCRATCH staging roots** (``SCRATCH_W2_ROOT`` / ``SCRATCH_W5_BASE`` / ``SCRATCH_ROOT`` /
   ``LEGACY_STAGING_EFFECT``, and the ``staging_root`` that reads them).  ef227's ``rescore-w2/`` kit
   is a DEPLOYED, cast-proven revert chain on this machine; the pin that keeps it where it is is
   installation history, not a property of the tool.  The kit ships the same function with a
   local-only default base (``export.DEFAULT_OUT_DIR``) and an empty ``LEGACY_STAGING`` map for a
   caller to re-pin -- which is precisely what happens below.
2. **The ``--from-corpus`` arm of ``scaffold_bytes``.**  It reads the 372-file SCRATCH extraction and
   cross-checks it against the install.  That whole branch exists only because two copies of the
   bytes can disagree; the kit has one copy (the user's install), so the branch is dead there.
3. **The spec registry** (``discover_specs`` / ``resolve_spec``).  ``_HERE``-relative discovery of
   ``*_rescore.toml`` -- a gate-RUNNER concept.  The kit verb takes an explicit spec path.
4. **The study CLI** (``main`` / ``cli``), with its ``init`` verb name, its ``_HERE`` spec defaults
   and its ``W.recover_machines`` phase column.  The kit registers ``summon-rescore scaffold`` in
   ``cli.py`` instead, and defaults ``machines=()``.

THE BOOTSTRAP IS LOAD-BEARING (do not reorder)
-----------------------------------------------
``<repo>/ff9mapkit`` must be first on ``sys.path`` before the kit import so the LOCAL package shadows
any editable install, and ``thomas-swap/disasm`` must be there because ``retime``, ``w_survey``,
``test_reskin`` and the gate runners all import ``ef_container`` on the strength of importing this
module first (``reskin.py``'s own import literally carries the comment "sets up sys.path").

PROVENANCE
----------
Unchanged: the stock container is read at RUN TIME from ``resources.assets`` in the user's install --
never from the repo, never from a previously-written override.  A sha256 DRIFT GUARD (hash only; no
stock bytes) refuses a donor whose install bytes drifted.  Staged output goes under
``C:\gd\SCRATCH\summon-format``; the kit's ``_refuse_repo_path`` (a ``.git``-ancestor search, correct
in an installed wheel where counting directories up from ``__file__`` is not) refuses any destination
inside a checkout or a mod-asset tree.
"""
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
_STUDY = os.path.dirname(_HERE)                                  # studies/custom-summons
_REPO = os.path.dirname(os.path.dirname(_STUDY))                 # <repo>
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_STUDY, "thomas-swap", "disasm"))
sys.path.insert(0, os.path.join(_REPO, "ff9mapkit"))

import summon_camera as W                                        # noqa: E402  (the study shim)
from ff9mapkit.summons import rescore as _kit                    # noqa: E402

#: THE ALIAS.  Every later ``import rescore`` -- and this module's own name -- now resolves to the kit
#: module object.  Names are set ON that object below, never left in this file's globals.
sys.modules[__name__] = _kit

#: W2's staging root -- ef227's, and ONLY ef227's.  Its ``mod/``, its backups and its
#: ``revert_summon_camera_227.py`` are the cast-proven W2/W3 revert chain; W5 did not move them and
#: neither does the promotion.
SCRATCH_W2_ROOT = os.environ.get("FF9_RESCORE_SCRATCH",
                                 r"C:\gd\SCRATCH\summon-format\rescore-w2")

#: W5's staging BASE -- every OTHER effect gets ``<base>\ef%03d\``.  Before this split ``--mod-root``
#: defaulted to ``rescore-w2/mod`` for every effect, so building ef211 dropped its container and its
#: ``revert_summon_camera_211.py`` INSIDE ef227's revert kit (B5 hit exactly this and had to clean it
#: by hand).  Two effects staged in one session could then also overwrite each other's backups.
SCRATCH_W5_BASE = os.environ.get("FF9_RESCORE_SCRATCH_W5",
                                 r"C:\gd\SCRATCH\summon-format\rescore-w5")

#: kept as a NAME for w2_gates and every caller that predates the split; it is ef227's root.
SCRATCH_ROOT = SCRATCH_W2_ROOT

#: the effect whose staging layout is frozen (W2 shipped and cast it); everything else is W5-lane.
LEGACY_STAGING_EFFECT = 227

_kit._HERE = _HERE
_kit._STUDY = _STUDY
#: the repo root, re-pinned from THIS file's location, for the gates and tests that cite it by name.
_kit._REPO = _REPO
_kit.SCRATCH_W2_ROOT = SCRATCH_W2_ROOT
_kit.SCRATCH_W5_BASE = SCRATCH_W5_BASE
_kit.SCRATCH_ROOT = SCRATCH_ROOT
_kit.LEGACY_STAGING_EFFECT = LEGACY_STAGING_EFFECT
#: the kit ships this map EMPTY on purpose -- a pin belongs to an installation's deployment history,
#: not to the tool.  This is that history.
_kit.LEGACY_STAGING = {LEGACY_STAGING_EFFECT: SCRATCH_W2_ROOT}
#: the ledger's study-era private name; ``retime.py`` and ``test_rescore.py`` both cite it.
_kit._Ledger = _kit.Ledger


def staging_root(effect: int, root=None) -> str:
    """The per-effect staging WORK dir, against the STUDY's SCRATCH roots.

    Byte-for-byte the kit's own function with ONE change: the default base is read off the module at
    CALL time (``_kit.SCRATCH_W5_BASE``) rather than frozen into ``STAGING_BASE`` at import, because
    ``test_rescore`` monkeypatches that constant and a default captured at import would ignore it --
    the staged bytes would land in the real SCRATCH root while the test asserted about a tmpdir.
    """
    pinned = _kit.LEGACY_STAGING.get(int(effect))
    if pinned:
        return str(pinned)
    return os.path.join(str(root or _kit.SCRATCH_W5_BASE), "ef%03d" % int(effect))


_kit.staging_root = staging_root


# ============================================================ the corpus arm of `init` (study-only)
def scaffold_bytes(ef_id: int, game=None, from_corpus: bool = False,
                   cross_check: bool = True) -> Tuple[bytes, str]:
    """The container ``init`` reads, and a REFUSAL when the two available copies disagree.

    The drift hash the scaffold writes must be the hash of the bytes the BUILD will read, and the
    build always reads the install.  So a corpus-derived scaffold is only sound while the corpus copy
    still matches the install -- and when both are readable that is checked, not assumed.

    Study-only in full: the kit has exactly one copy of the bytes (the user's install), so the whole
    disagreement branch is dead there and ``read_stock_effect`` stands alone.
    """
    if not from_corpus:
        return _kit.read_stock_effect(ef_id, game)
    blob, name = W._load(ef_id)
    source = os.path.join(W.SCRATCH_CORPUS, "%s.bytes" % name)
    if cross_check:
        try:
            live, live_src = _kit.read_stock_effect(ef_id, game)
        except Exception:                                        # no install here -- corpus stands
            return blob, source + "  (corpus copy; no install resolvable to cross-check against)"
        if hashlib.sha256(live).hexdigest() != hashlib.sha256(blob).hexdigest():
            raise _kit.StockDriftError(
                "the extracted corpus copy of ef%03d does NOT match this install's bytes.\n"
                "  corpus  %s\n  install %s\n  (%s)\n"
                "A scaffold derived from the corpus would write a drift hash the build can never "
                "satisfy. Re-extract the corpus, or drop --from-corpus and read the install."
                % (ef_id, hashlib.sha256(blob).hexdigest(), hashlib.sha256(live).hexdigest(),
                   live_src))
        source += "  (corpus copy, sha-identical to %s)" % live_src
    return blob, source


_kit.scaffold_bytes = scaffold_bytes


# ============================================================ the scaffold's VOICE (study-only)
#: The generated spec names the tool that generated it, and the two tools are different: the kit's
#: scaffold is produced by ``ff9mapkit summon-rescore scaffold`` and tells its reader to run
#: ``ff9mapkit summon-rescore read``; the study's is produced by ``py rescore.py init`` and tells its
#: reader to run ``py summon_camera.py read``.  A kit user has no ``summon_camera.py`` to run, and a
#: study spec that told the author to run a verb this checkout's gates do not exercise would be
#: wrong in the other direction -- so the header is re-voiced here rather than made generic.
#:
#: ``(kit text, study text, required)``.  A REQUIRED substitution that does not fire RAISES: if the
#: kit re-words one of these lines, this file must fail loudly rather than quietly emit the kit's
#: voice into a study spec and let ``test_rescore``'s pins be the only thing that notices.
_STUDY_VOICE: Tuple[Tuple[str, str, bool], ...] = (
    ("# CONTENT RESCORE spec for ef",
     "# TIER W -- CONTENT RESCORE spec for ef", True),
    ("#     ff9mapkit summon-rescore scaffold --ef %d",
     "#     py rescore.py init --ef %d", True),
    ("#     ff9mapkit summon-rescore read --ef %d",
     "#     py summon_camera.py read %d", True),
    # conditional: only emitted for a shot with no phases supplied
    ("#     phases    : none supplied for this shot. The reframe budget is then UNKNOWN,\n"
     "#                 not loose -- judge it from an in-game cast.",
     "#     phases    : none recovered for this shot (R3's inspector found no clean state\n"
     "#                 machine, or its chunk never ran program 0). The reframe budget is\n"
     "#                 then UNKNOWN, not loose -- judge it from an in-game cast.", False),
    # conditional: only emitted when the quote budget refused the per-track stock values
    ("read the read-out to see them",
     "run `summon_camera.py read %d` to see them", False),
)


def _scaffold_text(sc) -> str:
    """The kit's scaffold, re-voiced for the study's own CLI.

    Thin on purpose: the GENERATOR is the kit's (one implementation of what a scaffold contains, so
    the two cannot drift on substance).  Only the tool names differ, and only those are touched.
    """
    text = _kit._kit_scaffold_text(sc)
    for kit_s, study_s, required in _kit._STUDY_VOICE:
        k = kit_s % sc.effect if "%d" in kit_s else kit_s
        s = study_s % sc.effect if "%d" in study_s else study_s
        if k not in text:
            if required:
                raise _kit.RescoreError(
                    "the study shim cannot re-voice the generated scaffold: the kit no longer emits\n"
                    "    %r\n"
                    "  Update _STUDY_VOICE in studies/custom-summons/tier-w/rescore.py to match the "
                    "kit's current wording -- silently shipping the kit's voice into a study spec is "
                    "the failure this refusal exists to prevent." % k)
            continue
        text = text.replace(k, s)
    return text


#: the kit's own generator, kept reachable under a distinct name so the override is not recursive.
#: GUARDED against a second application: this module aliases itself into ``sys.modules`` so it should
#: execute once, but capturing an already-overridden ``_scaffold_text`` here would build an infinitely
#: recursive wrapper -- a failure worth one ``hasattr`` to make impossible rather than unlikely.
if not hasattr(_kit, "_kit_scaffold_text"):
    _kit._kit_scaffold_text = _kit._scaffold_text
_kit._STUDY_VOICE = _STUDY_VOICE
_kit._scaffold_text = _scaffold_text


# ============================================================ the spec registry (study-only)
def discover_specs(root=None) -> List[Tuple[str, Optional[int]]]:
    """``[(path, pinned effect or None)]`` -- the gate runner's registry, in a stable order.

    ef227's spec is PINNED to 227 externally so a toml that changed its own ``effect`` would be
    caught by the runner rather than quietly gated against a different container.  Any other
    ``*_rescore.toml`` beside it is discovered and gated too, but unpinned: there is no external
    expectation to check it against, and inventing one from a filename would be a guess.
    """
    here = Path(root or _kit._HERE)
    out: List[Tuple[str, Optional[int]]] = []
    pinned = here / "bahamut_rescore.toml"
    if pinned.is_file():
        out.append((str(pinned), 227))
    for p in sorted(here.glob("*_rescore.toml")):
        if p.resolve() != pinned.resolve():
            out.append((str(p), None))
    return out


def resolve_spec(spec: Optional[str], ef: Optional[int], root=None) -> str:
    """Which toml a bare ``plan``/``build``/``verify`` acts on.

    There used to be a silent default of ``bahamut_rescore.toml``.  On a one-effect tool that was
    convenience; on a tool that now scaffolds ANY effect it is a footgun -- ``py rescore.py plan``
    meaning "my new effect" and quietly rebuilding Bahamut is exactly the "nothing changed" symptom
    this whole rung is shaped around.  So: name the spec, or name ``--ef N`` and let the standard
    filename resolve it, or be told what is available.
    """
    here = Path(root or _kit._HERE)
    if spec:
        return spec
    if ef is not None:
        for cand in (here / ("ef%03d_rescore.toml" % ef), here / ("ef%d_rescore.toml" % ef)):
            if cand.is_file():
                return str(cand)
        raise _kit.RescoreError(
            "no spec for ef%03d beside this tool (looked for %s). Generate one with "
            "`py rescore.py init --ef %d`."
            % (ef, ", ".join("%s" % c.name for c in (here / ("ef%03d_rescore.toml" % ef),)), ef))
    known = _kit.discover_specs(here)
    raise _kit.RescoreError(
        "name the spec to act on -- there is no default any more, because a tool that scaffolds any "
        "effect must not quietly rebuild Bahamut when you meant yours.\n"
        "  specs beside this tool: %s\n  or: py rescore.py init --ef N"
        % (", ".join(os.path.basename(p) for p, _e in known) or "(none)"))


_kit.discover_specs = discover_specs
_kit.resolve_spec = resolve_spec


# ============================================================ the study CLI (study-only)
def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("verb", choices=("init", "plan", "build", "verify"))
    ap.add_argument("spec", nargs="?", default=None,
                    help="the rescore toml (plan/build/verify). Omit it and pass --ef N to resolve "
                         "ef###_rescore.toml beside this tool.")
    ap.add_argument("--ef", type=int, default=None,
                    help="the stock effect id. REQUIRED by `init`; resolves the spec for the others.")
    ap.add_argument("--out", default=None,
                    help="`init` output path (default: ef###_rescore.toml beside this tool)")
    ap.add_argument("--from-corpus", action="store_true",
                    help="`init` reads the extracted SCRATCH corpus instead of the install, and "
                         "REFUSES if the two copies disagree")
    ap.add_argument("--no-phases", action="store_true",
                    help="`init` skips R3's state-machine recovery (faster; the scaffold then "
                         "cannot report a reframe budget)")
    ap.add_argument("--force", action="store_true", help="`init` may overwrite an existing spec")
    ap.add_argument("--mod-root", default=None,
                    help="staging mod root (default: the PER-EFFECT SCRATCH root -- ef227 keeps "
                         "W2's rescore-w2/mod, everything else gets rescore-w5/ef###/mod; the repo "
                         "and the install are refused)")
    ap.add_argument("--work-dir", default=None,
                    help="where backups + the revert script land (default: the resolved mod root's "
                         "PARENT, so they can never end up in a different effect's kit)")
    ap.add_argument("--game", default=None)
    ap.add_argument("--live", action="store_true",
                    help="allow a --mod-root INSIDE the game install (the real deploy). Off by "
                         "default: W2 stages, the orchestrator deploys with the user present.")
    a = ap.parse_args(argv)

    if a.verb == "init":
        if a.ef is None:
            raise SystemExit("init needs --ef N (the stock effect id to scaffold)")
        blob, source = _kit.scaffold_bytes(a.ef, a.game, a.from_corpus)
        machines = () if a.no_phases else W.recover_machines(blob, "ef%03d" % a.ef)
        sc = _kit.scaffold(a.ef, blob, source, machines)
        out = Path(a.out or os.path.join(_kit._HERE, "ef%03d_rescore.toml" % a.ef))
        p = _kit.write_scaffold(sc, out, a.force)
        print("\n".join(_kit.scaffold_summary(sc)))
        print("\n  WROTE %s" % p)
        print("  next: py rescore.py plan %s" % p.name)
        return 0

    spec_path = _kit.resolve_spec(a.spec, a.ef)
    spec = _kit.load_spec(spec_path)
    b = _kit.build_patched(spec, spec_path, a.game)
    print("\n".join(_kit.describe(b)))
    if a.verb == "plan":
        print("\nplan only -- nothing written.")
        return 0

    from ff9mapkit import config
    try:
        game_root = config.find_game_path(a.game)
    except Exception:                                            # pragma: no cover
        game_root = None
    if a.verb == "build":
        out = _kit.stage(b, a.mod_root, a.work_dir, game_root, allow_install=a.live)
        print("\n  %s" % ("DEPLOYED (--live)" if a.live else "STAGED"))
        for k, v in out.items():
            print("    %-22s %s" % (k, v))
        if not out["modfilelist_present"]:
            print("    (no ModFileList.txt in this mod folder -- correct: one must never be "
                  "CREATED, or every other file in the folder becomes invisible)")
        return 0

    v = _kit.verify(b, a.mod_root)
    if not v["ok"] and v.get("sha256") is None:
        print("\nVERIFY FAILED: %s" % v["reason"])
        return 1
    print("\n  VERIFY  staged %d B sha %s -> %s"
          % (v["bytes"], (v["sha256"] or "")[:16],
             "MATCHES the rebuild" if v["ok"] else "DIVERGES from the rebuild"))
    return 0 if v["ok"] else 1


def cli(argv: Optional[Sequence[str]] = None) -> int:
    """``main`` with the refusals presented as refusals.

    A refusal is a RESULT of this tool, not a crash: a traceback buries the paragraph the author is
    supposed to read (the disclosure, the drift, the ambiguous frame) under a stack.  ``main`` itself
    still RAISES, so every caller that wants the exception -- the tests, the gate runner -- keeps
    getting it.
    """
    try:
        return _kit.main(argv)
    except (_kit.RescoreError, W.SummonCameraError) as e:
        print("\nREFUSED\n%s" % e, file=sys.stderr)
        return 2


_kit.main = main
_kit.cli = cli

if __name__ == "__main__":                                       # pragma: no cover
    raise SystemExit(cli())
