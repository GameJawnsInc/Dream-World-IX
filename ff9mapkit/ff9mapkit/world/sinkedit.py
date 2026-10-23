"""Sinking an island as the overworld editor drives it (rung C5): the sinkable islands as clickable shapes, the
island under a click, its ghost, and the ONE place the editor's ``world-sink`` command is built.

THE CLI STAYS THE ORACLE, as for the forest and the mountain: Check runs :func:`command` with ``--dry-run`` and
Accept without, and both read the verdict ``--report-json`` writes.

THE ISLAND LIST is ``transplant.sink_candidates``: every real island of the disc with its verdict (a whole-tile sink,
the footprint sink that keeps its neighbours, or a cluster), and now its outline. It reads every stock block, about
three minutes on disc 1, so :func:`candidates` keeps it in the kit's cache per install and disc: stock land does
not change under a draft (the sink reads stock, not the folder).

THE DISC-4 HALF IN A DRAFT. ``world-sink``'s own disc-4 step is the mirror, which REPLAYS the sink on disc 4's
ground where disc 4 differs, and copies it where it does not. A draft cannot mirror (it has no bundles), so
:func:`commands` is the disc-1 sink and then the same sink on disc 4 (``--disc 4 --skip-mirror``), the very call
the replay makes. On promote, the live folder's mirror copies over it where disc 4 matches disc 1 and holds it where
they differ, so disc 4 ends as ``world-sink`` itself would leave it.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from .forestedit import CENTRE_STEP, SoupIndex, _pip, fmt_num, read_verdict   # noqa: F401  (the tools' shared kit)

SEA_Y = 0.3                        # the ghost's height: just over the sea plane, where the island would go


def _cache_file(game, disc: int) -> Path:
    from ..provision import cache_dir
    key = hashlib.sha256(str(Path(game).resolve()).lower().encode()).hexdigest()[:12]
    return Path(cache_dir()) / "world-sink" / f"candidates-disc{disc}-{key}.json"


def candidates(game, *, disc: int = 1, refresh: bool = False, scan=None) -> list:
    """The sinkable islands of ``disc`` (``transplant.sink_candidates`` rows, outlines included), from the cache when
    it holds them; ``scan`` is the test seam for the three-minute scan."""
    path = _cache_file(game, disc)
    if not refresh:
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
            if doc.get("version") == 1 and all("outline" in r for r in doc["rows"]):
                return doc["rows"]
        except (OSError, ValueError, KeyError):
            pass
    if scan is None:
        from . import transplant as TR
        rows = TR.sink_candidates(disc=disc, game=game)
    else:
        rows = scan(disc=disc, game=game)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"version": 1, "game": str(game), "disc": disc, "rows": rows},
                              default=lambda o: list(o) if isinstance(o, tuple) else str(o)), encoding="utf-8")
    tmp.replace(path)
    return rows


def hit(rows, x: float, z: float, *, reach: float = 6.0):
    """The island under ``(x, z)``: the row whose outline holds the point (the smallest, when outlines nest), else the
    row whose outline comes within ``reach`` of it, else None."""
    p = np.array([[float(x), float(z)]])
    inside = []
    for r in rows:
        poly = np.asarray(r.get("outline") or [], dtype=np.float64)
        if len(poly) >= 3 and _pip(p, poly)[0]:
            inside.append(r)
    if inside:
        return min(inside, key=lambda r: r["land_u2"])
    best, bd = None, reach
    for r in rows:
        poly = np.asarray(r.get("outline") or [], dtype=np.float64)
        if len(poly) < 2:
            continue
        e = np.roll(poly, -1, axis=0) - poly
        t = np.clip(((p - poly) * e).sum(axis=1) / ((e * e).sum(axis=1) + 1e-12), 0.0, 1.0)
        d = float(np.sqrt((((poly + t[:, None] * e) - p) ** 2).sum(axis=1)).min())
        if d < bd:
            best, bd = r, d
    return best


def verdict(row, *, cluster: bool = False, allow_entrances: bool = False) -> dict:
    """The island's precomputed verdict as the card's preview: ``{"ok", "why", "where", "how"}``."""
    if row is None:
        return {"ok": False, "why": "no sinkable island here", "where": [], "how": None}
    where = [tuple(row["at"])]
    if cluster:
        c = row.get("cluster") or {}
        if not c.get("ok"):
            why = c.get("why") or "it joins no other island's water (sink it alone)"
            return {"ok": False, "why": f"as a cluster: {why}", "where": where, "how": None}
        how = f"with the {len(c['members'])} islands its water joins"
    elif not row.get("ok"):
        return {"ok": False, "why": row.get("why") or "refused", "where": where, "how": None}
    else:
        how = "its land only, its neighbours kept" if row.get("fill") == "footprint" else "re-tiled as open water"
    if row.get("entrance_tris") and not allow_entrances:
        return {"ok": False, "why": f"it has {row['entrance_tris']} entrance tris (a place on it would never open "
                                    "again): allow entrances to sink it anyway", "where": where, "how": how}
    return {"ok": True, "why": "", "where": [], "how": how}


def ghost(row):
    """``(tris (n, 3, 3), rim (m, 3))``: the island's outline at sea level, filled (where the sea would close)."""
    poly = np.asarray(row["outline"], dtype=np.float64)
    rim = np.c_[poly[:, 0], np.full(len(poly), SEA_Y), poly[:, 1]]
    c = rim.mean(axis=0)
    tris = np.array([[c, rim[k], rim[(k + 1) % len(rim)]] for k in range(len(rim))], dtype=np.float64)
    return tris, rim


def is_draft(mod_folder, game) -> bool:
    """Is ``mod_folder`` a world draft (``world.draft``), the folder whose disc-4 half the editor writes itself?"""
    from . import draft as D
    p = Path(str(mod_folder))
    return p.is_absolute() and D.read_meta(p) is not None


def command(mod_folder, at, *, cluster: bool = False, allow_entrances: bool = False, disc: int = 1,
            skip_mirror: bool = False, dry_run: bool = True, report=None) -> list:
    """The ``world-sink`` argv (after ``python -m ff9mapkit``) for this island. ``at`` is the island's own point (the
    one ``world-sink --list`` prints), on the editor's grid."""
    argv = ["world-sink", "--mod-folder", str(mod_folder), "--at", fmt_num(at[0], 0.001), fmt_num(at[1], 0.001)]
    if disc != 1:
        argv += ["--disc", str(int(disc))]
    if cluster:
        argv.append("--cluster")
    if allow_entrances:
        argv.append("--allow-entrances")
    if skip_mirror:
        argv.append("--skip-mirror")
    if dry_run:
        argv.append("--dry-run")
    if report is not None:
        argv += ["--report-json", str(report)]
    return argv


def commands(mod_folder, at, *, cluster: bool = False, allow_entrances: bool = False, report=None,
             report4=None) -> list:
    """Accept's two calls into a draft: the disc-1 sink, then the same sink on disc 4 (``--skip-mirror``), the call
    ``world-sink``'s replay makes (module docstring)."""
    return [command(mod_folder, at, cluster=cluster, allow_entrances=allow_entrances, dry_run=False, report=report),
            command(mod_folder, at, cluster=cluster, allow_entrances=allow_entrances, disc=4, skip_mirror=True,
                    dry_run=False, report=report4)]
