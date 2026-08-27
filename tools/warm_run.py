#!/usr/bin/env python3
# Windows-first tool: invoke via the py launcher --  py tools/warm_run.py <target> ...
"""Warm-process iteration driver for the "offline eye" edit -> rerun -> inspect loop (stage 2 of the
overworld performance work; stage 1 shipped `ff81316` -- world/extract.py's read_block container
index + bounded decode memo, stashed AS ATTRIBUTES ON THE UnityPy ENV OBJECT).

A cold `py studies/....py` / `py -m ff9mapkit <verb> ...` invocation pays ~1.3s of FIXED per-process
tax on every single rerun before it does any real work: ~1.0s UnityPy attrs-codegen import, ~0.2s
interpreter/CLI start, ~0.3s bundle open. None of that is the law you just edited -- it's the same
every time. warm_run.py runs the SAME target repeatedly inside ONE process instead: UnityPy (and every
other third-party module) stays resident for the life of the session, and the loaded p0data envs
(with their stage-1 mesh index) are carried from run to run -- while every FIRST-PARTY module
(ff9mapkit.* by name, plus anything living under the repo tree or the target's own directory --
bare-name sibling helpers included) is purged from sys.modules and re-imported fresh from disk before
every single run, so a law you just edited is NEVER stale. See --help (mechanism / hazards / deny
list) for the full contract.

Usage:
    py tools/warm_run.py studies/overworld-topography/crag_anatomy.py
    py tools/warm_run.py -m ff9mapkit world-terrain --mod-folder FF9CustomMap --radius 10 --at 100 -50 --raise 5 --dry-run
    py tools/warm_run.py --watch studies/overworld-topography/crag_anatomy.py
    py tools/warm_run.py --selfcheck

Run from the repo root, matching every other tools/*.py convention (the target scripts insert their
own sys.path entries by `__file__`, so cwd is not actually load-bearing for imports -- see --help).
"""
from __future__ import annotations

import argparse
import fnmatch
import importlib
import os
import runpy
import shutil
import sys
import tempfile
import time
import traceback
from pathlib import Path

# Same idiom every tools/*.py uses (deploy_field.py etc): the repo's ff9mapkit/ dir on sys.path so
# `import ff9mapkit...` resolves the LOCAL package, not a pip install. Needed unconditionally (not just
# for `-m ff9mapkit` targets) because _prepare()'s reimport step below runs on EVERY iteration,
# including the very first one -- before a script-mode target has had a chance to insert its own path.
REPO_ROOT = Path(__file__).resolve().parent.parent
KIT_DIR = REPO_ROOT / "ff9mapkit"                 # contains the ff9mapkit/ package -- sys.path entry
KIT_PKG_DIR = KIT_DIR / "ff9mapkit"                # the package dir itself -- watched for --watch
if str(KIT_DIR) not in sys.path:
    sys.path.insert(0, str(KIT_DIR))


# ---------------------------------------------------------------------------------------------------
# THE CARRY/PURGE/REIMPORT MECHANISM (frozen design). Parameterized by `cache_module` so --selfcheck
# can run this EXACT code against a synthetic module tree instead of a re-implementation of it.
# ---------------------------------------------------------------------------------------------------

_CACHE_MODULE = "ff9mapkit.extract"                # ff9mapkit.extract._STREAM_ENV_CACHE (stage 1)
_CACHE_ATTR = "_STREAM_ENV_CACHE"
_MEMO_ATTR = "_ff9mapkit_block_memo"               # the canonical UNSAFE attr: holds ff9mapkit BlockMesh
                                                    # instances of the OUTGOING import's class identity.
_CARRY_SAFE_ATTRS = {"_ff9mapkit_mesh_index",       # the ONLY env attrs allowed to ride across a purge:
                     "_ff9mapkit_clip_index"}       # their values are UnityPy-typed (pptr objects), and
                                                    # UnityPy's class identity is stable across a purge
                                                    # (UnityPy itself is never purged -- the whole point).
                                                    # Every OTHER _ff9mapkit_* attr is stripped by
                                                    # default: safe-by-default beats a hardcoded name.
                                                    # NOTE: extract._MOD_ENV_CACHE (mod-folder bundles)
                                                    # is deliberately NEVER carried -- those bundles
                                                    # mutate on deploy, so a field-art/deployed-mod
                                                    # target simply pays its own bundle-open each run.


def _save_envs(cache_module: str):
    """Step 1: harvest the loaded-env entries out of `cache_module`'s env cache, via getattr --
    degrade to cold (return None) if the module was never imported or the cache is empty/absent."""
    mod = sys.modules.get(cache_module)
    if mod is None:
        return None
    cache = getattr(mod, _CACHE_ATTR, None)
    if not cache:
        return None
    return list(cache.items())                     # preserves OrderedDict recency order


def _strip_unsafe_attrs(saved, verbose: bool) -> int:
    """Step 2: strip every ``_ff9mapkit_*`` attribute off each saved env EXCEPT the ``_CARRY_SAFE_ATTRS``
    allowlist. Holding a ff9mapkit-class instance across the purge is the one cross-boundary
    class-identity hazard this driver exists to prevent, and the review found that deleting a single
    hardcoded NAME (the block memo) would fail silent on the NEXT kit attribute that stashes one --
    so the strip is safe-by-default: a future ``_ff9mapkit_*`` attr is dropped automatically unless
    someone consciously adds it to the allowlist after proving its values are purge-stable."""
    if not saved:
        return 0
    stripped = 0
    for _key, env in saved:
        d = getattr(env, "__dict__", None)
        if not d:
            continue
        for attr in [a for a in d if a.startswith("_ff9mapkit_") and a not in _CARRY_SAFE_ATTRS]:
            try:
                delattr(env, attr)
                stripped += 1
            except AttributeError:
                pass
    if verbose:
        print(f"[warm_run] verbose: stripped {stripped} unsafe _ff9mapkit_* attr(s) across "
              f"{len(saved)} carried env(s)")
    return stripped


def _module_file_under(mod, roots, driver_file):
    """True if `mod`'s __file__ (or a namespace __path__ entry) lives under one of `roots` -- and
    never for the driver's own file."""
    if mod is None or not roots:
        return False
    mpaths = []
    f = getattr(mod, "__file__", None)
    if f:
        mpaths.append(f)
    else:
        mpaths.extend(list(getattr(mod, "__path__", ()) or ()))
    for p in mpaths:
        try:
            rp = os.path.normcase(os.path.abspath(str(p)))
        except (OSError, ValueError, TypeError):
            continue
        if rp == driver_file:
            return False
        if any(rp.startswith(root) for root in roots):
            return True
    return False


def _purge_modules(extra_purge_names, verbose: bool, purge_roots=()):
    """Step 3: drop every FIRST-PARTY entry from sys.modules -- matched by NAME (`ff9mapkit` /
    `ff9mapkit.*`, plus any extra prefixes) AND by FILE LOCATION (any module whose __file__/__path__
    lives under a purge root: the repo tree + a script target's own directory). The path axis is what
    catches a study script's bare-name sibling helpers (`import helper_next_door`) -- name prefixes
    alone left those silently stale (review finding, the one HIGH). `__main__`/`__mp_main__` and the
    driver's own file are never purged. THIS is the entire freshness guarantee -- the next import
    re-executes every module from disk, so a law you just edited can never be stale. Deliberately NOT
    importlib.reload (reload leaves OLD class objects reachable from anything that still references
    an old instance; a fresh sys.modules del+reimport is the only way to guarantee every class in the
    reimported tree is brand new)."""
    prefixes = ("ff9mapkit",) + tuple(extra_purge_names)
    roots = []
    for r in purge_roots:
        try:
            roots.append(os.path.normcase(os.path.abspath(str(r))) + os.sep)
        except (OSError, ValueError):
            pass
    driver_file = os.path.normcase(os.path.abspath(__file__))
    dropped = []
    for name, mod in list(sys.modules.items()):
        if name in ("__main__", "__mp_main__"):
            continue
        hit = any(name == pfx or name.startswith(pfx + ".") for pfx in prefixes)
        if not hit:
            hit = _module_file_under(mod, roots, driver_file)
        if hit:
            del sys.modules[name]
            dropped.append(name)
    if verbose:
        remaining = [m for m, mod in sys.modules.items()
                     if m not in ("__main__", "__mp_main__")
                     and (any(m == pfx or m.startswith(pfx + ".") for pfx in prefixes)
                          or _module_file_under(mod, roots, driver_file))]
        assert not remaining, f"purge left {remaining!r} in sys.modules"
        print(f"[warm_run] verbose: purged {len(dropped)} module(s) (name-prefix {prefixes} + "
              f"{len(roots)} path root(s)) -- post-purge matching entries in sys.modules = 0 (asserted)")
    return dropped


def _reimport_and_reseed(cache_module: str, saved, verbose: bool) -> int:
    """Step 4: re-import `cache_module` fresh (guaranteed fresh -- step 3 just purged it) and reseed
    its brand-new, empty cache with the saved envs. Guarded per the frozen design: any failure here
    (import error, cache attr renamed/removed, shape mismatch) degrades to a cold run rather than
    crashing the session."""
    try:
        mod = importlib.import_module(cache_module)
    except Exception as e:                         # noqa: BLE001 -- import can fail in many shapes
        print(f"[warm_run] warning: could not re-import {cache_module} ({e}) -- running cold",
              file=sys.stderr)
        return 0
    if not saved:
        return 0
    try:
        cache = getattr(mod, _CACHE_ATTR, None)
        if cache is None:
            return 0
        for key, env in saved:
            cache[key] = env
    except Exception as e:                          # noqa: BLE001 -- shape mismatch -> cold, never crash
        print(f"[warm_run] warning: could not reseed {cache_module}.{_CACHE_ATTR} ({e}) -- running cold",
              file=sys.stderr)
        return 0
    if verbose:
        for key, env in saved:
            bad = [a for a in getattr(env, "__dict__", {})
                   if a.startswith("_ff9mapkit_") and a not in _CARRY_SAFE_ATTRS]
            assert not bad, f"carried env {key!r} still has unsafe attr(s) {bad!r} at iteration start"
        print(f"[warm_run] verbose: reseeded {len(saved)} carried env(s) into the fresh cache -- "
              f"asserted none carry an unsafe _ff9mapkit_* attr")
    return len(saved)


def _prepare(cold: bool, verbose: bool, extra_purge_names=(), cache_module: str = _CACHE_MODULE,
             purge_roots=()) -> int:
    """Run steps 1-4 between iterations. `cold=True` skips the save (an explicit cold restart, or the
    very first iteration -- nothing to carry either way). Returns the count of envs carried forward.
    The harvest (steps 1-2) is guarded like the reseed (step 4): any failure degrades to a cold run,
    never a crash (review finding: the original guard was asymmetric, save-side failures crashed)."""
    saved = None
    if not cold:
        try:
            saved = _save_envs(cache_module)
            _strip_unsafe_attrs(saved, verbose)
        except Exception as e:                      # noqa: BLE001 -- harvest failure -> cold, never crash
            print(f"[warm_run] warning: could not harvest the env cache ({e}) -- running cold",
                  file=sys.stderr)
            saved = None
    _purge_modules(extra_purge_names, verbose, purge_roots)
    return _reimport_and_reseed(cache_module, saved, verbose)


def _run_target(mode: str, module_name, script_path, target_argv):
    """Step 5: run the target via runpy with run_name="__main__" and a per-iteration sys.argv. Script
    mode also inserts the script's own directory at sys.path[0] for the duration -- `py script.py`
    does that implicitly and runpy.run_path does NOT (review finding: without it, a target's bare-name
    sibling import resolves under `py` but breaks under warm_run). Callers wrap this in their own
    try/except (a broken law edit must print a traceback and return to the prompt, never kill the
    session)."""
    old_argv = sys.argv
    inserted_dir = None
    try:
        if mode == "module":
            sys.argv = [module_name] + list(target_argv)
            runpy.run_module(module_name, run_name="__main__", alter_sys=True)
        else:
            sdir = str(Path(script_path).resolve().parent)
            if sdir not in sys.path:
                sys.path.insert(0, sdir)
                inserted_dir = sdir
            sys.argv = [str(script_path)] + list(target_argv)
            runpy.run_path(str(script_path), run_name="__main__")
    finally:
        sys.argv = old_argv
        if inserted_dir is not None:
            try:
                sys.path.remove(inserted_dir)
            except ValueError:
                pass


# ---------------------------------------------------------------------------------------------------
# Deny list (enforced BEFORE anything runs) + a non-blocking caution list.
# ---------------------------------------------------------------------------------------------------

# The frozen 4: one-shot, game-install-writing paths. Refused outright -- run them directly instead.
_DENY_SCRIPT_BASENAMES = {"deploy_field.py", "wire_newgame_from_stock.py"}
_DENY_SCRIPT_GLOBS = ("revert_deploy*.py",)        # tools/scroll_out/revert_deploy.py, revert_deploy_<id>.py
_DENY_MODULE_VERB = "world-mirror"                 # ff9mapkit.cli._cmd_world_mirror -> writes Disc4 tree

# Recon's expanded write-verb census: these `ff9mapkit` CLI verbs also write into the live game install
# BY DEFAULT (their --mod-folder is a real destination, not display text like world-morphs'), but each
# one supports --dry-run to preview safely -- so they're a CAUTION, not a hard refusal, per the frozen
# design's own scope (only the 4 named items above are refused).
_CAUTION_VERBS = {
    "world-deploy", "world-retarget", "world-mesh-build", "world-atlas-reskin",
    "world-terrain", "world-reclaim", "world-coast", "world-transplant", "world-island",
    "world-forest", "world-hill", "world-mountain", "world-water", "world-atlas-add-tile",
    "world-entrance", "world-fuse", "world-environment", "world-minimap",
    "world-rename-markers", "world-encounter-rate", "world-encounter-frequency", "world-encounters",
    "deploy-campaign", "newgame",
}


def _deny_reason(mode, module_name, script_path, target_argv):
    if mode == "script":
        base = Path(script_path).name
        if base in _DENY_SCRIPT_BASENAMES:
            return (f"{base} writes to the LIVE game install and is meant to run one-shot.\n"
                    f"    Run it directly instead:  py tools/{base} <args>")
        for pat in _DENY_SCRIPT_GLOBS:
            if fnmatch.fnmatch(base.lower(), pat.lower()):
                return (f"{base} reverts a deploy against the LIVE game install -- one-shot only.\n"
                        f"    Run it directly instead:  py tools/scroll_out/{base}")
    else:
        if module_name == "ff9mapkit" and _DENY_MODULE_VERB in target_argv:
            return (f"'{_DENY_MODULE_VERB}' writes the Disc4 mirror tree into the LIVE game install -- "
                    f"one-shot only.\n"
                    f"    Run it directly instead:  py -m ff9mapkit {_DENY_MODULE_VERB} ...")
    return None


def _caution_reason(mode, module_name, target_argv):
    if mode != "module" or module_name != "ff9mapkit":
        return None
    hit = _CAUTION_VERBS.intersection(target_argv)
    if hit and "--dry-run" not in target_argv:
        return (f"note: {sorted(hit)} write into the live game install by default (stage-2 recon "
                f"census) -- pass --dry-run to preview safely under warm_run, or run it directly, "
                f"one-shot, when you actually mean to write.")
    return None


def _parse_target(extra):
    """`extra` = the raw argv tail after warm_run's own flags. Either a script path, or "-m <module>
    <module args...>" (mirrors `python -m`). Returns (mode, module_name, script_path, target_argv)."""
    if not extra:
        return None
    if extra[0] == "-m":
        if len(extra) < 2:
            return None                             # "-m" with nothing after it
        return "module", extra[1], None, list(extra[2:])
    return "script", None, extra[0], list(extra[1:])


# ---------------------------------------------------------------------------------------------------
# --watch: 0.5s-poll mtime watcher over the target + the whole ff9mapkit package tree (+ the target's
# own directory for a script target), ~300ms debounce, re-checked once more right after a run so an
# edit saved WHILE the target was running is never silently absorbed into the new baseline.
# ---------------------------------------------------------------------------------------------------

def _collect_watch_paths(mode, script_path):
    paths = set()
    if KIT_PKG_DIR.is_dir():
        paths.update(KIT_PKG_DIR.rglob("*.py"))
    if mode == "script" and script_path:
        sp = Path(script_path).resolve()
        paths.add(sp)
        try:
            paths.update(sp.parent.glob("*.py"))    # sibling helpers in the target's own directory
        except OSError:
            pass
    return sorted(paths, key=str)


def _snapshot_mtimes(paths):
    snap = {}
    for p in paths:
        try:
            snap[str(p)] = p.stat().st_mtime
        except OSError:
            pass                                    # deleted/renamed mid-watch -- just drop it
    return snap


def _wait_for_change(paths, baseline, poll=0.5):
    while True:
        time.sleep(poll)
        snap = _snapshot_mtimes(paths)
        if snap != baseline:
            return snap


def _debounce_settle(paths, snap, debounce=0.3):
    """Keep re-sampling every ~300ms until two consecutive snapshots agree (an editor/save tool that
    writes in several small flushes settles before we act on it)."""
    while True:
        time.sleep(debounce)
        snap2 = _snapshot_mtimes(paths)
        if snap2 == snap:
            return snap2
        snap = snap2


# ---------------------------------------------------------------------------------------------------
# One iteration + the two drivers (interactive prompt / --watch).
# ---------------------------------------------------------------------------------------------------

def run_iteration(n, mode, module_name, script_path, target_argv, extra_purge, cold, verbose,
                  purge_roots=()):
    """Returns True if the iteration prepared normally; False if prepare itself was interrupted
    (half-purged state -- the caller must start the NEXT iteration cold)."""
    t0 = time.perf_counter()
    try:
        carried = _prepare(cold=cold, verbose=verbose, extra_purge_names=extra_purge,
                           purge_roots=purge_roots)
    except KeyboardInterrupt:
        print("\n[warm_run] KeyboardInterrupt during prepare -- carried state dropped, "
              "next run starts cold.")
        return False
    try:
        _run_target(mode, module_name, script_path, target_argv)
    except KeyboardInterrupt:
        print("\n[warm_run] KeyboardInterrupt -- run stopped, back to the prompt.")
    except SystemExit as e:
        if e.code not in (0, None):
            print(f"[warm_run] target exited via sys.exit({e.code!r})")
    except Exception:                               # noqa: BLE001 -- a broken law must not kill the session
        traceback.print_exc()
        print("[warm_run] target raised -- back to the prompt. Every iteration re-imports ff9mapkit "
              "fresh from disk, so a fixed law is picked up on the very next rerun -- no restart needed.")
    elapsed = time.perf_counter() - t0
    warm = "warm" if carried else "cold"
    print(f"\n=== iteration {n} -- {elapsed:.2f}s -- envs carried: {carried} ({warm}) -- "
          f"laws are fresh-from-disk every iteration ===")
    return True


def interactive_loop(mode, module_name, script_path, target_argv, extra_purge, verbose,
                     purge_roots=()):
    n = 0
    cold = True                                     # iteration 1: nothing carried yet either way
    while True:
        n += 1
        ok = run_iteration(n, mode, module_name, script_path, target_argv, extra_purge, cold, verbose,
                           purge_roots)
        cold = not ok                               # interrupted prepare -> half-purged, restart cold
        try:
            choice = input("[warm_run] Enter=rerun   c=cold restart   q=quit > ").strip().lower()
            if not sys.stdin.isatty():
                print()                             # a piped Enter isn't echoed by a terminal -- emit the
                                                    # newline ourselves so the NEXT run's first output line
                                                    # never merges onto the prompt line in captured logs
        except EOFError:
            print()
            break
        if choice.startswith("q"):
            break
        if choice.startswith("c"):
            cold = True
            print("[warm_run] next run starts cold (dropping all carried state).")


def watch_loop(mode, module_name, script_path, target_argv, extra_purge, verbose, purge_roots=()):
    watch_paths = _collect_watch_paths(mode, script_path)
    extra_note = " + the target's own directory" if mode == "script" else ""
    print(f"[warm_run] --watch: polling {len(watch_paths)} file(s) every 0.5s, ~300ms debounce "
          f"(the target + ff9mapkit/ff9mapkit/**/*.py{extra_note}); Ctrl+C to quit.")
    baseline = _snapshot_mtimes(watch_paths)
    n = 0
    cold = True
    pending = None                                  # a change observed right after the previous run
    first = True
    while True:
        if first:
            first = False
        elif pending is not None:
            baseline = _debounce_settle(watch_paths, pending)
            pending = None
        else:
            changed = _wait_for_change(watch_paths, baseline)
            baseline = _debounce_settle(watch_paths, changed)
        n += 1
        ok = run_iteration(n, mode, module_name, script_path, target_argv, extra_purge, cold, verbose,
                           purge_roots)
        cold = not ok                               # interrupted prepare -> half-purged, restart cold
        post = _snapshot_mtimes(watch_paths)
        if post != baseline:                        # a save landed WHILE the target was running
            pending = post


# ---------------------------------------------------------------------------------------------------
# --selfcheck: exercises the REAL _prepare()/_run_target() functions above (not a reimplementation)
# against a synthetic module tree + a trivial target, entirely offline, no game install / UnityPy
# needed. No established tools/ pytest convention exists (recon-confirmed: no tools/tests/, no
# conftest.py, no pytest.ini reference) -- this flag is the locally-consistent alternative.
# ---------------------------------------------------------------------------------------------------

_SELFCHECK_PKG = "wr_selfcheck_pkg"

_SELFCHECK_EXTRACT_PY = '''\
"""Synthetic stand-in for ff9mapkit.extract, used only by warm_run.py --selfcheck."""
from collections import OrderedDict

_STREAM_ENV_CACHE = OrderedDict()


class Memo:
    """Stand-in for a ff9mapkit dataclass instance (e.g. world.extract.BlockMesh) -- gets a NEW class
    object every re-import: exactly the stage-2 stale-class hazard warm_run guards against by
    stripping _ff9mapkit_block_memo before every purge+reimport."""

    def __init__(self, tag):
        self.tag = tag
'''

_SELFCHECK_TARGET_PY = '''\
"""Trivial warm_run --selfcheck target -- touches the synthetic package's env cache exactly the way a
real study script touches ff9mapkit.extract._STREAM_ENV_CACHE via world/extract.py's read_block: reuse
or create an env, stash one "safe" cross-boundary value and one "unsafe" one. Also imports a BARE-NAME
SIBLING module (the review's HIGH finding: siblings bypass a name-prefix purge) so the selfcheck can
prove the path-based purge keeps siblings fresh too."""
import wr_selfcheck_helper as H                      # sibling next to this script -- path-purged, never stale
import wr_selfcheck_pkg.extract as extract

env = extract._STREAM_ENV_CACHE.get("envA")
if env is None:
    class FakeEnv:
        pass
    env = FakeEnv()
    extract._STREAM_ENV_CACHE["envA"] = env

if not hasattr(env, "_ff9mapkit_mesh_index"):
    env._ff9mapkit_mesh_index = ("stable-marker",)   # SAFE -- UnityPy-shaped, must survive every purge

env._ff9mapkit_block_memo = extract.Memo("this iteration's own decode")   # UNSAFE -- must not survive
env._wr_helper_value = H.VALUE                       # records which VERSION of the sibling this run saw

print("selfcheck target ran")
'''

_SELFCHECK_HELPER_V1 = '"""sibling helper, version 1."""\nVALUE = 1\n'
_SELFCHECK_HELPER_V2 = '"""sibling helper, version 2 -- the mid-session edit."""\nVALUE = 2\n'


def run_selfcheck(verbose: bool = True) -> bool:
    print("[warm_run] --selfcheck: exercising the real _prepare()/_run_target() against a synthetic "
          "module tree (no game install / UnityPy needed)...")
    tmp = tempfile.mkdtemp(prefix="ff9mapkit_warmrun_selfcheck_")
    tmp_path = Path(tmp)
    pkg_dir = tmp_path / _SELFCHECK_PKG
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
    (pkg_dir / "extract.py").write_text(_SELFCHECK_EXTRACT_PY, encoding="utf-8")
    target_script = tmp_path / "wr_selfcheck_target.py"
    target_script.write_text(_SELFCHECK_TARGET_PY, encoding="utf-8")
    helper_path = tmp_path / "wr_selfcheck_helper.py"
    helper_path.write_text(_SELFCHECK_HELPER_V1, encoding="utf-8")

    inserted = str(tmp_path) not in sys.path
    if inserted:
        sys.path.insert(0, str(tmp_path))

    failures = []

    def check(cond, msg):
        if not cond:
            failures.append(msg)
            print(f"[warm_run]   FAIL: {msg}")
        elif verbose:
            print(f"[warm_run]   ok: {msg}")

    cache_module = f"{_SELFCHECK_PKG}.extract"
    extra_purge = (_SELFCHECK_PKG,)
    purge_roots = (tmp_path,)                       # the sibling helper is ONLY caught by the path axis
    try:
        env_ref = None
        for n in (1, 2, 3):
            cold = (n == 1)
            carried = _prepare(cold=cold, verbose=verbose, extra_purge_names=extra_purge,
                                cache_module=cache_module, purge_roots=purge_roots)
            check("wr_selfcheck_helper" not in sys.modules,
                  f"iter {n}: bare-name sibling helper purged before the run (path-based purge)")
            extract_mod = sys.modules.get(cache_module)
            check(extract_mod is not None, f"iter {n}: {cache_module} re-imported")

            if n == 1:
                check(carried == 0, f"iter {n}: cold start carries 0 envs (got {carried})")
            else:
                check(carried == 1, f"iter {n}: warm start carries the 1 saved env (got {carried})")
                cache = getattr(extract_mod, _CACHE_ATTR, None) if extract_mod else None
                env = cache.get("envA") if cache else None
                check(env is not None, f"iter {n}: carried env present in the fresh cache")
                check(env is env_ref, f"iter {n}: carried env is the SAME object (identity preserved)")
                check(not hasattr(env, _MEMO_ATTR),
                      f"iter {n}: carried env has NO {_MEMO_ATTR} (stripped before this iteration)")
                check(getattr(env, "_ff9mapkit_mesh_index", None) == ("stable-marker",),
                      f"iter {n}: carried env's _ff9mapkit_mesh_index survived unchanged (safe attr)")

            try:
                _run_target("script", None, str(target_script), [])
                ran_ok = True
            except Exception:                       # noqa: BLE001 -- report, don't abort the self-test
                ran_ok = False
                traceback.print_exc()
            check(ran_ok, f"iter {n}: the trivial target ran without raising")

            extract_mod2 = sys.modules.get(cache_module)
            cache2 = getattr(extract_mod2, _CACHE_ATTR, None) if extract_mod2 else None
            env_ref = cache2.get("envA") if cache2 else None
            check(env_ref is not None, f"iter {n}: target populated the env cache")
            check(hasattr(env_ref, _MEMO_ATTR), f"iter {n}: target set its own {_MEMO_ATTR} this run")

            # the sibling-freshness leg (regression test for the review's HIGH): iteration 1 sees the
            # v1 helper; the file is then edited mid-session; every later iteration MUST see v2.
            want = 1 if n == 1 else 2
            check(getattr(env_ref, "_wr_helper_value", None) == want,
                  f"iter {n}: target saw sibling helper VALUE={want} "
                  f"(got {getattr(env_ref, '_wr_helper_value', None)!r}) -- fresh-from-disk")
            if n == 1:
                helper_path.write_text(_SELFCHECK_HELPER_V2, encoding="utf-8")

        # a purge with NOTHING carried (a bare cold prepare) must still leave sys.modules clean --
        # exactly the package + its one submodule (importing "pkg.extract" always imports "pkg" too)
        _prepare(cold=True, verbose=verbose, extra_purge_names=extra_purge, cache_module=cache_module,
                 purge_roots=purge_roots)
        check("wr_selfcheck_helper" not in sys.modules,
              "final: sibling helper not resident after the last cold prepare")
        remaining = sorted(m for m in sys.modules
                            if m == _SELFCHECK_PKG or m.startswith(_SELFCHECK_PKG + "."))
        check(remaining == [_SELFCHECK_PKG, cache_module],
              f"final: only {_SELFCHECK_PKG} + {cache_module} resident after the last cold prepare "
              f"(got {remaining!r})")
    finally:
        for m in [m for m in list(sys.modules)
                  if m == _SELFCHECK_PKG or m.startswith(_SELFCHECK_PKG + ".")
                  or m in ("wr_selfcheck_helper", "wr_selfcheck_target")]:
            del sys.modules[m]
        if inserted and str(tmp_path) in sys.path:
            sys.path.remove(str(tmp_path))
        shutil.rmtree(tmp, ignore_errors=True)

    ok = not failures
    print(f"[warm_run] --selfcheck: {'PASS' if ok else 'FAIL'} ({len(failures)} failure(s))")
    return ok


# ---------------------------------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------------------------------

# warm_run's own flags never take a value, so a simple leading-token scan splits them from the target
# unambiguously -- no argparse tug-of-war over a target's OWN --verbose/--watch-shaped flag (everything
# from the target's first token onward is passed through verbatim, exactly like `python -m` itself).
_OWN_FLAGS = {"--watch", "--verbose", "-v", "--selfcheck", "-h", "--help"}


def _split_argv(argv):
    i = 0
    while i < len(argv) and argv[i] in _OWN_FLAGS:
        i += 1
    return argv[:i], argv[i:]


_EPILOG = """\
target (required, unless --selfcheck):
  a study-script path                    py tools/warm_run.py studies/overworld-topography/crag_anatomy.py
  or -m ff9mapkit <verb> [args...]       py tools/warm_run.py -m ff9mapkit world-terrain --mod-folder FF9CustomMap --radius 10 --at 100 -50 --raise 5 --dry-run

  warm_run's own flags (--watch/--verbose/--selfcheck) MUST come before the target -- everything from
  the target's first token onward is passed through verbatim, so a target's OWN same-named flag is
  never swallowed.

examples:
  py tools/warm_run.py studies/overworld-topography/crag_anatomy.py
  py tools/warm_run.py --watch studies/overworld-topography/crag_anatomy.py
  py tools/warm_run.py --verbose -m ff9mapkit world-morphs --block 5,5
  py tools/warm_run.py --selfcheck

refused outright (one-shot, game-install-writing -- run these directly instead):
  tools/deploy_field.py, tools/wire_newgame_from_stock.py, tools/scroll_out/revert_deploy*.py,
  -m ff9mapkit world-mirror

caution, not refused (writes by default -- pass --dry-run to preview safely under warm_run):
  world-deploy, world-retarget, world-mesh-build, world-atlas-reskin, world-terrain, world-reclaim,
  world-coast, world-transplant, world-island, world-forest, world-hill, world-mountain, world-water,
  world-atlas-add-tile, world-entrance, world-fuse, world-environment, world-minimap,
  world-rename-markers, world-encounter-rate, world-encounter-frequency, world-encounters,
  deploy-campaign, newgame

mechanism (between every pair of iterations):
  1. save the loaded UnityPy envs out of ff9mapkit.extract._STREAM_ENV_CACHE (guarded: a harvest
     failure degrades to a cold run, never a crash). The mod-folder bundle cache (_MOD_ENV_CACHE) is
     deliberately NEVER carried -- those bundles mutate on deploy, so a field-art/deployed-mod target
     just pays its own bundle-open each iteration.
  2. strip every _ff9mapkit_* attribute off each saved env EXCEPT _ff9mapkit_mesh_index/_clip_index
     (those are UnityPy-typed and purge-stable; anything else -- e.g. the block memo's ff9mapkit
     BlockMesh instances -- is a stale-class hazard and is dropped by default)
  3. purge every FIRST-PARTY module from sys.modules: ff9mapkit/ff9mapkit.* by NAME, plus ANY module
     whose file lives under the repo tree or the target script's own directory (bare-name sibling
     helpers included) -- THIS is the freshness guarantee: every law is re-read from disk every
     single iteration, by construction
  4. re-import ff9mapkit.extract and reseed its fresh _STREAM_ENV_CACHE with the saved envs (guarded:
     any failure here degrades to a cold run, never a crash)
  5. run the target (script mode inserts the script's own directory at sys.path[0], matching plain
     `py script.py`); a broken law edit prints a traceback and returns to the prompt instead of
     killing the session (Ctrl+C during a run OR during prepare does the same -- an interrupted
     prepare just forces the next run cold; Ctrl+C at the prompt quits)

hazards checked at recon time (both came back negative -- nothing to special-case here): no
multiprocessing/ProcessPoolExecutor anywhere in ff9mapkit/studies/tools (the Windows-spawn
re-import-of-__main__ risk this driver would otherwise need to guard against does not exist in this
codebase today), and no atexit handlers that could go stale across a purge. Re-check this list if a
future study script adds multiprocessing/joblib.
"""


def _build_argparser():
    ap = argparse.ArgumentParser(
        prog="warm_run.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Warm-process iteration driver for the offline-eye edit -> rerun -> inspect loop. Runs a "
            "study script (or an `ff9mapkit` CLI verb) repeatedly in ONE interpreter process, carrying "
            "UnityPy + the loaded p0data envs across reruns (the ~1.0s attrs-codegen import + ~0.3s "
            "bundle-open tax) while purging every ff9mapkit.* module between iterations, so a law you "
            "just edited is picked up fresh from disk on the very next run -- never stale, no restart."
        ),
        epilog=_EPILOG,
    )
    ap.add_argument("--watch", action="store_true",
                     help="poll the target + ff9mapkit/ff9mapkit/**/*.py (+ the target's own directory "
                          "for a script target) every 0.5s (~300ms debounce) and rerun automatically on "
                          "change, instead of the Enter-to-rerun prompt")
    ap.add_argument("--verbose", "-v", action="store_true",
                     help="print the purge count and assert zero first-party modules (by name OR by "
                          "file location) remain in sys.modules right before the re-import; assert "
                          "every carried env has no unsafe _ff9mapkit_* attribute at iteration start")
    ap.add_argument("--selfcheck", action="store_true",
                     help="run the internal purge/carry/reseed self-test against a synthetic module "
                          "tree and a trivial target, print PASS/FAIL, and exit (no target needed)")
    return ap


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    own_argv, target_argv_raw = _split_argv(argv)
    ap = _build_argparser()
    args = ap.parse_args(own_argv)                  # -h/--help prints and exits inside this call

    if args.selfcheck:
        ok = run_selfcheck(verbose=True)
        return 0 if ok else 1

    if not target_argv_raw:
        ap.print_help()
        print("\n[warm_run] error: no target given -- pass a study-script path or "
              "'-m ff9mapkit <verb> ...' (or --selfcheck)", file=sys.stderr)
        return 2

    parsed = _parse_target(target_argv_raw)
    if parsed is None:
        print("[warm_run] error: '-m' needs a module name after it, "
              "e.g. -m ff9mapkit world-morphs --all", file=sys.stderr)
        return 2
    mode, module_name, script_path, target_argv = parsed

    deny = _deny_reason(mode, module_name, script_path, target_argv)
    if deny:
        print(f"[warm_run] REFUSED: {deny}", file=sys.stderr)
        return 3

    purge_roots = [REPO_ROOT]                       # everything first-party under the repo goes fresh
    if mode == "script":
        sp = Path(script_path)
        if not sp.is_file():
            print(f"[warm_run] error: no such file: {script_path}", file=sys.stderr)
            return 2
        script_path = str(sp)
        extra_purge = (sp.stem,)                    # belt only -- the path-based purge (purge_roots)
        purge_roots.append(sp.resolve().parent)     # is what actually catches siblings/self
    else:
        extra_purge = () if module_name == "ff9mapkit" else (module_name,)
    purge_roots = tuple(purge_roots)

    caution = _caution_reason(mode, module_name, target_argv)
    if caution:
        print(f"[warm_run] {caution}")

    shown = ("-m " + module_name + " " + " ".join(target_argv)) if mode == "module" else script_path
    print(f"[warm_run] target: {shown}")
    print("[warm_run] every iteration purges ff9mapkit.* from sys.modules and re-imports it fresh from "
          "disk before running -- a law edit is picked up on the very next rerun.")

    try:
        if args.watch:
            watch_loop(mode, module_name, script_path, target_argv, extra_purge, args.verbose,
                       purge_roots)
        else:
            interactive_loop(mode, module_name, script_path, target_argv, extra_purge, args.verbose,
                             purge_roots)
    except KeyboardInterrupt:
        print("\n[warm_run] quitting.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
