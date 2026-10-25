"""Coast morphs as the overworld editor drives them (rung C5): a real block's lawful morph windows, clickable, with
each verb's depth ceiling as the handle's stop, and the ONE place the editor's ``world-transplant --in-place`` command
is built.

THE CLI STAYS THE ORACLE: Check runs :func:`command` with ``--dry-run`` and Accept without, and both read the verdict
``--report-json`` writes.

THE WINDOWS are ``coastscan.scan_block``: a block's beach waterline runs and cliff base runs, each verb probed down a
depth ladder by the real builders and certified by an in-place dry run, so a ceiling is a depth the verb deploys
(``world-morphs`` prints the same catalog). A scan reads stock and takes a few seconds per block, so :func:`windows`
keeps each block's in the kit's cache. They are STOCK's windows: a block a folder of the stack (or the draft)
already overrides is morphed from those bytes instead, so the editor offers no window there (:func:`edited`).

THE DRAFT'S DISC-4 HALF, as for the sink (``world.sinkedit``): ``world-transplant --in-place`` replays the morph on
disc 4's own ground where disc 4 differs; a draft cannot mirror, so Accept runs the morph on disc 1 and then the same
morph on disc 4 (``--disc 4 --skip-mirror``, the replay's own call).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from .forestedit import CENTRE_STEP, SoupIndex, fmt_num, read_verdict   # noqa: F401  (the tools' shared kit)

VERBS = ("cliff-bump", "cliff-headland", "cliff-bay", "beach-bump", "beach-reshape", "beach-slide")
DEPTH_STEP = 0.5                   # every probe ladder's rung spacing
RIBBON_Y = 1.0                     # the window's ribbon height above the sea (a cliff base sits near it)
PREFER_TIE = 0.05                  # the held window keeps a click this near as near as the nearest (a centre is 0.01u)


def _cache_file(game, disc: int, cell) -> Path:
    from ..provision import cache_dir
    key = hashlib.sha256(str(Path(game).resolve()).lower().encode()).hexdigest()[:12]
    return Path(cache_dir()) / "world-coast" / f"windows-disc{disc}-{key}-{cell[0]}_{cell[1]}.json"


def _jsonable(o):
    if isinstance(o, tuple):
        return list(o)
    if isinstance(o, dict):
        return {k: _jsonable(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_jsonable(v) for v in o]
    return o


def windows(game, cell, *, disc: int = 1, refresh: bool = False, scan=None) -> list:
    """Block ``cell``'s lawful morph windows (``coastscan.scan_block``), from the cache when it holds them; ``scan``
    is the test seam."""
    path = _cache_file(game, disc, cell)
    if not refresh:
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
            if doc.get("version") == 1:
                return doc["windows"]
        except (OSError, ValueError, KeyError):
            pass
    if scan is None:
        from . import coastscan as CS
        ws = CS.scan_block(int(cell[0]), int(cell[1]), disc=disc, game=game)
    else:
        ws = scan(int(cell[0]), int(cell[1]), disc=disc, game=game)
    ws = _jsonable(ws)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"version": 1, "cell": list(cell), "disc": disc, "windows": ws}), encoding="utf-8")
    tmp.replace(path)
    return ws


def edited(cell, folders, *, disc: int = 1, game=None) -> list:
    """The folders (of ``folders``: the draft first, then the stack) that already override block ``cell``: a morph
    there would read their bytes, not the stock the windows were scanned on."""
    from . import mesh as M
    out = []
    for fo in folders:
        for d in (disc, 4):
            if M.existing_overrides([tuple(cell)], str(fo), disc=d, game=game):
                out.append(Path(str(fo)).name)
                break
    return out


def lawful(window) -> dict:
    """``{verb: (lo, hi)}``: each verb's lawful depth range in this window (a cliff verb ``(step, ceiling)``; a beach
    verb from its landward ceiling, negative, to its seaward one). Verbs with no lawful rung are left out."""
    out = {}
    for verb, pr in (window.get("probes") or {}).items():
        if window["kind"] == "cliff":
            if pr.get("depth"):
                out[verb] = (DEPTH_STEP, float(pr["depth"]))
        else:
            sea, land = pr.get("seaward"), pr.get("landward")
            if sea is not None or land is not None:
                out[verb] = (float(land) if land is not None else DEPTH_STEP,
                             float(sea) if sea is not None else -DEPTH_STEP)
    return out


def span(window, verb) -> tuple:
    """The verb's own window ends ``((x0, z0), (x1, z1))`` (a cliff verb may have trimmed the run)."""
    pr = (window.get("probes") or {}).get(verb) or {}
    w = pr.get("window") or (window["start"], window["end"])
    return tuple(float(v) for v in w[0]), tuple(float(v) for v in w[1])


def _on_run(w, x: float, z: float):
    """``(distance, point)``: the point of window ``w``'s run nearest ``(x, z)``."""
    p = np.array([float(x), float(z)])
    pts = np.asarray(w.get("run") or [w["start"], w["end"]], dtype=np.float64)
    a, b = pts[:-1], pts[1:]
    if not len(a):
        return float(np.hypot(*(pts[0] - p))), pts[0]
    e = b - a
    t = np.clip(((p - a) * e).sum(axis=1) / ((e * e).sum(axis=1) + 1e-12), 0.0, 1.0)
    q = a + t[:, None] * e
    d = np.sqrt(((q - p) ** 2).sum(axis=1))
    i = int(d.argmin())
    return float(d[i]), q[i]


def nearest(ws, x: float, z: float, *, reach: float = 12.0, prefer=None):
    """The window (with at least one lawful verb) whose run passes nearest ``(x, z)``, within ``reach``; else None.
    ``prefer`` (the window the card holds) wins a tie, so a handle that moves nothing never swaps the window. It is
    found in ``ws`` by value too: every read of a block's windows is a fresh JSON load, equal windows as new dicts
    (review of C12: an edit's held window lost to its own twin and its depth reset to the ceiling)."""
    best, bd = None, reach
    for w in ws:
        if not lawful(w):
            continue
        d = _on_run(w, x, z)[0]
        if d < bd:
            best, bd = w, d
    held = None if prefer is None else (next((w for w in ws if w is prefer), None)
                                        or next((w for w in ws if w == prefer), None))
    if held is not None and best is not held and lawful(held) and _on_run(held, x, z)[0] <= bd + PREFER_TIE:
        best = held                                      # a nearer window listed before it does not take the tie
    return best


def anchor(window, verb) -> tuple:
    """A point on the window's run by the middle of the verb's span: where the card puts its centre when it opens on a
    placed morph, so the window it holds is the nearest one there."""
    (x0, z0), (x1, z1) = span(window, verb)
    q = _on_run(window, (x0 + x1) / 2.0, (z0 + z1) / 2.0)[1]
    return float(q[0]), float(q[1])


def row_spec(row) -> str:
    """A ``[[morph]]`` row's window and depth in :func:`spec`'s spelling (the card matches a window by it)."""
    (x0, z0), (x1, z1) = row["window"]
    return f"{float(x0):.4f},{float(z0):.4f}:{float(x1):.4f},{float(z1):.4f}:{float(row['depth']):g}"


def verdict(window, verb, depth, *, edited_by=()) -> dict:
    """The cheap laws for this window, verb and depth: ``{"ok", "why", "where"}``."""
    if edited_by:
        return {"ok": False, "why": f"this block is already edited in {', '.join(edited_by)} (the windows are stock's)",
                "where": []}
    if window is None:
        return {"ok": False, "why": "no lawful coast window here", "where": []}
    rng = lawful(window).get(verb)
    mid = tuple(np.mean(np.asarray(span(window, verb)), axis=0)) if verb in VERBS else None
    if rng is None:
        pr = (window.get("probes") or {}).get(verb) or {}
        why = pr.get("binding") or pr.get("seaward_binding") or pr.get("landward_binding") or "no lawful depth"
        return {"ok": False, "why": f"{verb} has no lawful depth here ({why})", "where": [mid] if mid else []}
    lo, hi = min(rng), max(rng)
    if not (lo - 1e-9 <= float(depth) <= hi + 1e-9) or abs(float(depth)) < 1e-9:
        return {"ok": False, "why": f"depth {depth:g} is outside the window's lawful {lo:g}..{hi:g}", "where": [mid]}
    return {"ok": True, "why": "", "where": []}


def ghost(window, verb):
    """``(tris, rim)``: the verb's window as a raised ribbon along its run (the rim the morph moves)."""
    (x0, z0), (x1, z1) = span(window, verb)
    run = np.asarray(window.get("run") or [window["start"], window["end"]], dtype=np.float64)
    keep = [p for p in run if min(x0, x1) - 0.01 <= p[0] <= max(x0, x1) + 0.01
            and min(z0, z1) - 0.01 <= p[1] <= max(z0, z1) + 0.01] if window["kind"] == "cliff" else []
    pts = np.array(keep if len(keep) >= 2 else [(x0, z0), (x1, z1)], dtype=np.float64)
    rim = np.c_[pts[:, 0], np.full(len(pts), RIBBON_Y), pts[:, 1]]
    tris = []
    for a, b in zip(rim[:-1], rim[1:]):
        lo_a, lo_b = a - (0, 0.6, 0), b - (0, 0.6, 0)
        tris += [[a, b, lo_b], [a, lo_b, lo_a]]
    return np.array(tris, dtype=np.float64).reshape(-1, 3, 3), rim


def spec(window, verb, depth) -> str:
    (x0, z0), (x1, z1) = span(window, verb)
    return f"{x0:.4f},{z0:.4f}:{x1:.4f},{z1:.4f}:{float(depth):g}"


def command(mod_folder, cell, verb, spec_str, *, disc: int = 1, skip_mirror: bool = False, allow_entrances: bool = False,
            dry_run: bool = True, report=None) -> list:
    """The ``world-transplant --in-place`` argv (after ``python -m ff9mapkit``) for one morph."""
    if verb not in VERBS:
        raise ValueError(f"{verb} is not a coast morph the editor offers ({', '.join(VERBS)})")
    c = f"{int(cell[0])},{int(cell[1])}"
    argv = ["world-transplant", "--mod-folder", str(mod_folder), "--cell", c, "--donor", c, "--in-place",
            f"--{verb}", spec_str]
    if disc != 1:
        argv += ["--disc", str(int(disc))]
    if allow_entrances:
        argv.append("--allow-entrances")
    if skip_mirror:
        argv.append("--skip-mirror")
    if dry_run:
        argv.append("--dry-run")
    if report is not None:
        argv += ["--report-json", str(report)]
    return argv


def commands(mod_folder, cell, verb, spec_str, *, allow_entrances: bool = False, report=None, report4=None) -> list:
    """Accept's two calls into a draft: the disc-1 morph, then the same morph on disc 4 (module docstring)."""
    return [command(mod_folder, cell, verb, spec_str, allow_entrances=allow_entrances, dry_run=False, report=report),
            command(mod_folder, cell, verb, spec_str, disc=4, skip_mirror=True, allow_entrances=allow_entrances,
                    dry_run=False, report=report4)]
