"""An mtime+size-keyed TOML parse cache -- ONE seam for paths that re-parse the same files.

Opening a journey in the Workspace parses ~1850 tomls for ~890 distinct files (lint loads every
campaign.toml + member field.toml, the overview loads the campaigns again, the flag-name annotator
reads every field toml a third time) -- ~60% of the open interval was tomllib re-parsing identical
bytes. This module memoizes the PARSE on ``(st_mtime_ns, st_size)`` and hands every caller a fresh
structural copy, so:

- an on-disk edit is always seen (the stat signature changes -> re-parse; the GUI's F5/refresh and
  the CLI build path stay honest -- correctness > speed);
- no two consumers ever share a parsed tree. Callers MUTATE these dicts in place
  (:func:`ff9mapkit.flags.resolve_project_flags` rewrites flag names to indices,
  :func:`ff9mapkit.campaign.apply_seed_blocks` merges seed blocks) -- a shared entry would be
  poisoned by the first lint and served rewritten to the next consumer;
- errors behave exactly like ``tomllib.load(open(p, "rb"))``: OSError / TOMLDecodeError propagate
  to the caller and are NEVER cached (a broken file is re-read every call until it parses).

The signature is read with ``os.fstat`` on the very handle that is parsed, so a cached tree always
matches the bytes it was parsed from. The one stale-read window left is an edit that preserves BOTH
mtime_ns and size -- below filesystem timestamp resolution on NTFS/ext4.
"""
from __future__ import annotations

import os
import tomllib
from threading import Lock

_lock = Lock()
_cache: "dict[str, tuple[tuple[int, int], dict]]" = {}   # abspath -> ((mtime_ns, size), parsed tree)


def _fresh(x):
    """A structural copy of a tomllib tree: dict/list containers are rebuilt, scalars (str/int/float/
    bool/datetime) are immutable and shared. Much cheaper than copy.deepcopy (no memo, no dispatch)."""
    if isinstance(x, dict):
        return {k: _fresh(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_fresh(v) for v in x]
    return x


def load_toml(path) -> dict:
    """``tomllib.load(open(path, "rb"))``, memoized on the file's ``(st_mtime_ns, st_size)``.
    Returns a private copy per call -- callers may mutate the result freely.

    A warm hit is served STAT-FIRST: one ``os.stat``, no open. At journey scale (~1850 calls per
    open, ~2/3 of them hits) the open+fstat handshake was the cache's own overhead (~80 ms/open,
    measured 2026-07-24). A missing/unreadable file still raises OSError exactly like the open would
    have. A miss (or a signature change) falls through to the open path, which re-checks the cache
    against ``os.fstat`` of the very handle it parses -- so a cached tree always matches the bytes
    it was parsed from, and the stat-first serve introduces no staleness the fstat path didn't have
    (the one stale window remains an edit preserving BOTH mtime_ns and size)."""
    key = os.path.abspath(os.fspath(path))
    with _lock:
        hit = _cache.get(key)
    if hit is not None:
        st = os.stat(key)
        if hit[0] == (st.st_mtime_ns, st.st_size):
            return _fresh(hit[1])
    with open(key, "rb") as fh:
        st = os.fstat(fh.fileno())
        sig = (st.st_mtime_ns, st.st_size)
        with _lock:
            hit = _cache.get(key)
        if hit is not None and hit[0] == sig:
            return _fresh(hit[1])
        data = tomllib.load(fh)
    with _lock:
        _cache[key] = (sig, data)
    return _fresh(data)


def clear() -> None:
    """Drop every cached parse (tests; or bounding memory in a long-lived session)."""
    with _lock:
        _cache.clear()
