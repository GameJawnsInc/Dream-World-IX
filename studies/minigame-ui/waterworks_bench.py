"""THE WATERWORKS BENCH — `[[gauge]]` (tiles-as-sprites) first in-game run.
Survey substrate #5, the last one.

Field **30420** ("WATERWORKS", a fresh 559 native fork like the other minigame
benches): two live bars drawn INTO the plaza art — no DLL, no window. The
engine mechanism: segments+1 generated fill-state PNGs as scene overlays + a
SingleFrame tile ANIMATION, driven by ONE SetTileAnimationFrame per tick from
a looping daemon whose state is entry LOCALS (stock field 64's `allocate 2`).
This bench also proves the substrates COMPOSE: the numeric stepper (#2) sets
the water bar, the native shop (#3's lane) moves the gil bar.

Beats:
  THE STRONGBOX  a 12-cell gold bar sits over the plaza from frame 1 — the
                 party's gil against 5000, live. Buy potions from the CLERK
                 -> it falls as you spend; sell them back -> it climbs.
  THE COVER      the blue CISTERN bar is HIDDEN on arrival (its flag is
                 clear). KEEPER -> "Uncover the well" -> it appears; "Cover"
                 -> gone again (frame 255 = the whole-bar hide).
  THE STEPPER    KEEPER -> "Draw water" -> the Treno stepper; submit N pails
                 -> the cistern jumps to N/100 at once (the daemon re-reads
                 Global.Int16[2000] every tick).
  THE PULSE      set water <= 20 (level <= 2) -> the low bar shimmers with
                 field 64's own Sin glow; raise it -> steady color again.
  THE RELOAD     ~ -> Reload field: water, gil, and the cover state all hold
                 (save-backed GLOB + gil; the scene .bgx re-parses).

Usage (repo root):   py studies/minigame-ui/waterworks_bench.py gen | deploy
First deploy of 30420 = RELAUNCH once (id registration), then ~ -> Warp.
Revert: tools/scroll_out/revert_deploy_30420.py
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))

from ff9mapkit.scene.bgi import BgiWalkmesh, _pt_in_tri_xz        # noqa: E402
from ff9mapkit.scene import cam as CAM                            # noqa: E402

BENCH = Path("C:/gd/_waterworks_bench")
BASE_TOML = BENCH / "LDBM_NATIVE.field.toml"
BENCH_TOML = BENCH / "WATERWORKS.field.toml"
FIELD_ID = 30420
FIELD_NAME = "WATERWORKS"
MOD_FOLDER = "FF9CustomMap"
DONOR = "fbg_n11_ldbm_map158_lb_plz_0"

KEEPER_MODEL = "GEO_NPC_F2_CSO"
CLERK_MODEL = "GEO_NPC_F0_CSO"
SHOP_ID = 42                      # distinct from the ARMOURY's 40/50/51 (ShopItems merges by id)
COVER_FLAG = 8320                 # GLOB bit: SET = the well is uncovered (the cistern bar shows)
WATER_VAR = 2000                  # Global.Int16 the stepper writes / the cistern reads
BAR_W, BAR_H = 96, 12


def read_spawn() -> tuple[int, int]:
    m = re.search(r"(?m)^spawn = \[(-?\d+), (-?\d+)\]", BASE_TOML.read_text(encoding="utf-8"))
    if not m:
        raise SystemExit("no [player] spawn in the base toml")
    return int(m.group(1)), int(m.group(2))


def _spawn_floor_tris():
    mesh = BgiWalkmesh.from_bytes((BENCH / "walkmesh.bgi").read_bytes())
    wv = mesh.world_verts()
    spawn = read_spawn()
    by_floor: dict = {}
    for t in mesh.tris:
        by_floor.setdefault(t.floor_ndx, []).append(tuple(wv[i] for i in t.vtx))
    holding = [f for f, ts in by_floor.items()
               if any(_pt_in_tri_xz(spawn[0], spawn[1], a, b, c) for a, b, c in ts)]
    if not holding:
        raise SystemExit(f"spawn {spawn} is on no floor — mesh read wrong?")
    return by_floor[max(holding, key=lambda f: len(by_floor[f]))], spawn


def posts() -> dict:
    """Keeper + clerk on the spawn's floor at the ARMOURY-proven offsets
    (floor-filtered lattice, near the boot camera, 250u+ apart)."""
    tris, spawn = _spawn_floor_tris()
    xs = [v[0] for tri in tris for v in tri]
    zs = [v[2] for tri in tris for v in tri]

    def on_mesh(x, z):
        return any(_pt_in_tri_xz(x, z, a, b, c) for a, b, c in tris)

    pts = [(x, z)
           for z in range(int(min(zs)) + 300, int(max(zs)) - 299, 250)
           for x in range(int(min(xs)) + 300, int(max(xs)) - 299, 250)
           if on_mesh(x, z)]
    if len(pts) < 30:
        raise SystemExit(f"only {len(pts)} lattice points — mesh read wrong?")

    def nearest(x, z):
        return min(pts, key=lambda p: (p[0] - x) ** 2 + (p[1] - z) ** 2)

    lay = {"keeper": nearest(spawn[0] + 500, spawn[1] + 550),   # NE, the proven sutler spot
           "clerk": nearest(spawn[0] + 100, spawn[1] + 500)}    # NNE, the proven crier spot
    a, b = lay["keeper"], lay["clerk"]
    if max(abs(a[0] - b[0]), abs(a[1] - b[1])) < 250:
        raise SystemExit(f"posts collapsed: {lay}")
    return lay


def bar_anchor() -> tuple[int, int]:
    """Canvas top-left for the bar stack, INSIDE THE BOOT CAMERA WINDOW.

    cam.to_canvas now folds in a REAL camera's GTE ``centerOffset`` (this donor:
    [26, 400] — the case that exposed the bug; regression-pinned in
    ff9mapkit/tests/test_cameras.py). From the spawn's canvas point, the boot
    window = the camera CENTER clamped to the scroll viewport band ± the PSX
    half-screen (160, 112) — the probe showed the naive spawn-column anchor
    landed OFF the boot view entirely."""
    tris, spawn = _spawn_floor_tris()
    tri = next(t for t in tris if _pt_in_tri_xz(spawn[0], spawn[1], *t))
    sy = sum(v[1] for v in tri) / 3.0
    c0 = CAM.parse_bgx_cameras_text((BENCH / "camera.bgx").read_text(encoding="utf-8"))[0]
    cx, cy = CAM.to_canvas((spawn[0], sy, spawn[1]), c0)
    vx0, vx1, vy0, vy1 = c0.viewport                     # the camera-CENTER clamp band
    win_x0 = max(vx0, min(vx1, cx)) - 160                # the 320x224 boot window's top-left
    win_y0 = max(vy0, min(vy1, cy)) - 112
    return int(win_x0 + 320 - BAR_W - 24), int(win_y0 + 16)   # upper-right of the boot view


def gen() -> None:
    if not BASE_TOML.exists():
        print(f"importing donor {DONOR} ...")
        r = subprocess.run([sys.executable, "-m", "ff9mapkit", "import", DONOR,
                            "--native", "--out", str(BENCH)], cwd=REPO / "ff9mapkit")
        if r.returncode != 0:
            raise SystemExit("donor import failed")
    text = BASE_TOML.read_text(encoding="utf-8")
    text = re.sub(r"(?m)^text_block = \d+", f"text_block = {FIELD_ID}", text)
    text = re.sub(r"(?m)^id = \d+", f"id = {FIELD_ID}", text)
    text = re.sub(r'(?m)^name = "[^"]+"', f'name = "{FIELD_NAME}"', text)
    text = re.sub(r"(?ms)^\[\[gateway\]\].*?(?=^\[|\Z)", "", text)   # a closed room
    text = re.sub(r"(?ms)^\[\[object\]\].*?(?=^\[|\Z)", "", text)    # no donor bystanders
    if "entry_settle" not in text:                       # the owner directive
        text = text.replace("[camera]\n", '[camera]\nentry_settle = "auto"\n', 1)
        if "entry_settle" not in text:
            raise SystemExit("no [camera] block to hang entry_settle on")

    lay = posts()
    kx, kz = lay["keeper"]
    cx, cz = lay["clerk"]
    bx, by = bar_anchor()
    parts = [text, "\n# ---- THE WATERWORKS (generated by "
                   "studies/minigame-ui/waterworks_bench.py) ----\n"]
    parts.append(f'''
[[gauge]]
name = "cistern"
source = "global:{WATER_VAR}"
max = 100
segments = 10
pos = [{bx}, {by}]
width = {BAR_W}
height = {BAR_H}
color = "#40c8ff"
pulse_below = 2
requires_flag = {COVER_FLAG}

[[gauge]]
name = "strongbox"
source = "gil"
max = 5000
segments = 12
pos = [{bx}, {by + BAR_H + 6}]
width = {BAR_W}
height = {BAR_H}
color = "#e8c040"

[[npc]]
name = "keeper"
model = "{KEEPER_MODEL}"
pos = [{kx}, {kz}]

[[numeric_input]]
name = "draw"
result = {WATER_VAR}
digits = 3
max = 100
start = 50
label = "Pails"
echo = "[NUMB=0] pails, into the cistern."

[[choice]]
npc = "keeper"
prompt = "The waterworks, at your service."
instant = true
[[choice.options]]
text = "Draw water"
input = "draw"
[[choice.options]]
text = "Uncover the well"
requires_flag_clear = {COVER_FLAG}
set_flag = [{COVER_FLAG}, 1]
reply = "There she is — the blue line tells the level."
[[choice.options]]
text = "Cover the well"
requires_flag = {COVER_FLAG}
set_flag = [{COVER_FLAG}, 0]
reply = "Covered. The line will keep the level all the same."
[[choice.options]]
text = "Never mind"

[[shop]]
id = {SHOP_ID}
comment = "The Waterworks canteen"
sells = ["Potion", "Hi-Potion", "Tent"]

[[npc]]
name = "clerk"
model = "{CLERK_MODEL}"
pos = [{cx}, {cz}]
dialogue = "Potions bought and sold. Watch the gold bar go."
opens_shop = {SHOP_ID}
''')
    BENCH_TOML.write_text("".join(parts), encoding="utf-8")
    from ff9mapkit import build as BLD                            # noqa: E402
    problems = BLD.validate(BLD.FieldProject.load(BENCH_TOML))
    if problems:
        raise SystemExit("validate:\n  " + "\n  ".join(problems))
    print(f"wrote {BENCH_TOML}\n  posts: {lay}\n  bars at canvas ({bx}, {by})\n  validate: clean")


def deploy() -> None:
    if not BENCH_TOML.exists():
        gen()
    r = subprocess.run([sys.executable, str(REPO / "tools" / "deploy_field.py"),
                        str(BENCH_TOML), "--id", str(FIELD_ID), "--name", FIELD_NAME,
                        "--text-block", str(FIELD_ID), "--mod-folder", MOD_FOLDER])
    if r.returncode != 0:
        raise SystemExit("deploy_field failed")
    print(f"""
PLAYTEST (first deploy of {FIELD_ID} = RELAUNCH once, then ~ -> Warp -> {FIELD_ID}):
  1 THE STRONGBOX: a gold segmented bar floats over the plaza from frame 1 —
    your gil against 5000. (The blue cistern bar is NOT there yet.)
  2 THE CLERK (near spawn): buy a few potions -> the gold bar drops a cell or
    two AS the shop closes; sell them back -> it climbs. Live, no window.
  3 THE KEEPER (up-right): "Uncover the well" -> the blue bar appears above
    the gold one. "Draw water" -> the stepper; submit 80 -> the blue bar
    fills to 8/10 the moment the menu closes.
  4 THE PULSE: draw <= 20 pails -> the low blue bar SHIMMERS (the field-64
    glow); draw 50+ -> steady again.
  5 THE COVER: "Cover the well" -> the blue bar vanishes whole; uncover ->
    back at the same level. ~ Reload -> water, gil, cover all hold.
  Revert: py tools/scroll_out/revert_deploy_{FIELD_ID}.py""")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["gen", "deploy"])
    (gen if ap.parse_args().cmd == "gen" else deploy)()


if __name__ == "__main__":
    main()
