"""THE RENDER GATE — the V-shore bench binding of the kit's offline renderer.

PROMOTED (2026-08-04): the site-parameterized library now lives at
``ff9mapkit.world.render`` (the meshedit precedent — study file becomes the
thin shim, the kit owns the math). This module keeps the bench preset, the
corpus ``state_src`` table, and the exact CLI the studies call; every function
here delegates. Registration + calibration record: RENDER-GATE.md. The
blind-spot ledger lives in ``ff9mapkit.world.render``'s docstring and is
printed by the ``world-render`` verb.

Usage:
  py render_gate.py render <baseline|v1|v2|live>
  py render_gate.py calibrate            # P-A..P-E corpus run + diffs
  py render_gate.py flow [tag]           # texture-flow check (default: live)
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "ff9mapkit"))

from ff9mapkit import config                                # noqa: E402
from ff9mapkit.world import render as R                     # noqa: E402

# the bench constants, unchanged addresses for every study consumer
GAME = Path(config.find_game_path(None))
MOD = R.BENCH_VSHORE.mod_folder
DISC = R.BENCH_VSHORE.disc
CELLS = list(R.BENCH_VSHORE.cells)
BLOCK = 64.0
OUTD = HERE / "out" / "render_gate"
BK = Path(r"C:\gd\Dream-World-IX\backups")
TEXDIR = GAME / "MoguriMain" / "StreamingAssets" / "Assets" / "Resources" / \
    "worldmap" / "textures"
WATER_TEX = dict(R.WATER_TEX)
PARTS = list(R.PARTS)
SKY = R.SKY
BLANK_WHITE = R.BLANK_WHITE
RES = R.RES
VIEWS = dict(R.BENCH_VIEWS)
CORNER_BBOX = R.BENCH_CORNER_BBOX

SITE = R.BENCH_VSHORE

# pure functions, re-exported at their historical addresses
sample = R.sample
face_grads = R.face_grads
flow_records = R.flow_records
_flow_summary = R._flow_summary


def tex_for(part):
    return R.tex_for(part, SITE)


def live_path(bx, by, part):
    return R.live_path(SITE, bx, by, part)


def load_batches(part_src=None):
    return R.load_batches(SITE, part_src)


def project(view, verts):
    return R.project(view, verts, RES)


def raster(view, batches, title, cull=True, want_ids=False):
    return R.raster(view, batches, title, site=SITE, out_dir=OUTD,
                    cull=cull, want_ids=want_ids)


def diff(a, b, title, thresh=18):
    return R.diff(a, b, title, out_dir=OUTD, thresh=thresh)


# ---------------------------------------------------------------- states
def state_src(tag):
    park = HERE / "out" / "vcorner_park"
    if tag == "live":
        return {}
    if tag == "baseline":                                   # == live (parked); explicit
        return {
            (5, 7, "Terrain"): BK / "Block[5][7] Terrain.ff9mesh.r7.20260802-025232",
            (5, 8, "Terrain"): BK / "Block[5][8] Terrain.ff9mesh.r8.20260802-025232",
            (5, 7, "Sea4"): park / "Block[5][7] Sea4.ff9mesh",
            (5, 8, "Sea4"): park / "Block[5][8] Sea4.ff9mesh",
        }
    if tag == "v1":
        return {
            (5, 7, "Terrain"): BK / "Block[5][7] Terrain.ff9mesh.r7.20260802-032654",
            (5, 8, "Terrain"): BK / "Block[5][8] Terrain.ff9mesh.r8.20260802-032654",
            (5, 7, "Sea4"): park / "Block[5][7] Sea4.ff9mesh",
            (5, 8, "Sea4"): park / "Block[5][8] Sea4.ff9mesh",
        }
    if tag == "v2":
        return {
            (5, 7, "Terrain"): BK / "Block[5][7] Terrain.ff9mesh.park.20260802-033102",
            (5, 8, "Terrain"): BK / "Block[5][8] Terrain.ff9mesh.park.20260802-033102",
            (5, 7, "Sea4"): BK / "Block[5][7] Sea4.ff9mesh.park.20260802-033102",
            (5, 8, "Sea4"): BK / "Block[5][8] Sea4.ff9mesh.park.20260802-033102",
        }
    raise SystemExit(f"unknown state {tag}")


# ---------------------------------------------------------------- verbs
# `state_src` is looked up through the module at CALL time (the lambda), so
# terrain_gate.py's monkeypatch (`RG.state_src = wrapper(RG.state_src)`)
# keeps working across the promotion.
def cmd_flow(tag="live"):
    return R.cmd_flow(tag, site=SITE, corner_bbox=CORNER_BBOX,
                      state_src=lambda t: state_src(t))


def cmd_render(tag):
    return R.render_state(tag, site=SITE, views=VIEWS, out_dir=OUTD,
                          state_src=lambda t: state_src(t))


def cmd_calibrate():
    R.calibrate(site=SITE, views=VIEWS, out_dir=OUTD,
                state_src=lambda t: state_src(t))


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    if sys.argv[1] == "render":
        cmd_render(sys.argv[2] if len(sys.argv) > 2 else "live")
    elif sys.argv[1] == "calibrate":
        cmd_calibrate()
    elif sys.argv[1] == "flow":
        cmd_flow(sys.argv[2] if len(sys.argv) > 2 else "live")
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
