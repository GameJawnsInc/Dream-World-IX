"""THE AUTO-ROUTE BENCH — PATH A: static behavior feeds through the walkmesh pathfinder.

Field **30414** ("BTROUTE", a fresh 559 native fork — the donut arena whose CONCAVE
monument hole is the very obstacle that minted the wedge laws), PURE PRODUCT PATH:
`[behavior]` TOML + plain deploy_field, zero bench patching.

THE A/B — the same jamming chord, twice:
  wedge (soldier F0)   patrols the naive 2-point chord STRAIGHT across the donut
                       hole, NO route= — walks into the concave notch and WEDGES
                       there forever (the disease, live).
  clever (soldier F2)  patrols the SAME chord with `route = "auto"` — the build
                       spliced pathfinder detours around the hole; he circuits
                       cleanly, forever (the cure, live).

gen prints the OFFLINE PROOF first: the sweep's jam report for the naive chord and
the exact detour waypoints the plan spliced for the routed one.

Usage (repo root):   py studies/behavior-trees/btroute_bench.py gen | deploy
First deploy of 30414 needs a RELAUNCH; then ~ -> Reload field resets.
Revert: py tools/scroll_out/revert_deploy_30414.py
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))

from ff9mapkit.content import behaviortoml as BT                  # noqa: E402
from ff9mapkit.content import pathfind                            # noqa: E402
from ff9mapkit.scene import routes as R                           # noqa: E402
from ff9mapkit.scene.bgi import BgiWalkmesh, _pt_in_tri_xz        # noqa: E402

BENCH = Path("C:/gd/_btroute_bench")
BASE_TOML = BENCH / "LDBM_NATIVE.field.toml"
BENCH_TOML = BENCH / "BTROUTE.field.toml"
FIELD_ID = 30414
FIELD_NAME = "BTROUTE"
MOD_FOLDER = "FF9CustomMap"
DONOR = "fbg_n11_ldbm_map158_lb_plz_0"                            # 559, pitch 68.8

WEDGE_MODEL = "GEO_NPC_F0_CSO"
CLEVER_MODEL = "GEO_NPC_F2_CSO"


# --------------------------------------------------------------- walkmesh helpers
def read_spawn() -> tuple[int, int]:
    m = re.search(r"(?m)^spawn = \[(-?\d+), (-?\d+)\]", BASE_TOML.read_text(encoding="utf-8"))
    if not m:
        raise SystemExit("no [player] spawn in the base toml")
    return int(m.group(1)), int(m.group(2))


def mesh() -> BgiWalkmesh:
    return BgiWalkmesh.from_bytes((BENCH / "walkmesh.bgi").read_bytes())


def lattice(wm: BgiWalkmesh, step: int = 400) -> list[tuple[int, int]]:
    wv = wm.world_verts()
    tris = [tuple(wv[i] for i in t.vtx) for t in wm.tris]
    xs, zs = [v[0] for v in wv], [v[2] for v in wv]

    def on_mesh(x, z):
        return any(_pt_in_tri_xz(x, z, a, b, c) for a, b, c in tris)

    pts = []
    for z in range(int(min(zs)) + 300, int(max(zs)) - 299, step):
        for x in range(int(min(xs)) + 300, int(max(xs)) - 299, step):
            if on_mesh(x, z):
                pts.append((x, z))
    if len(pts) < 20:
        raise SystemExit(f"only {len(pts)} lattice points -- mesh read wrong?")
    return pts


def pick_chord(wm: BgiWalkmesh) -> tuple[tuple[int, int], tuple[int, int], list]:
    """A deterministic 2-point chord that (a) JAMS straight (off-mesh span = the
    donut hole) and (b) fits a routed CLOSED patrol under the 8-point ceiling.
    O(n) scan: for each lattice point, its point-reflection through the walkable
    centroid — those chords cross the middle, where the hole is. Both ends kept
    >=100u from walls (the rung-3 target-clearance law); longest-jam candidates
    are tried first."""
    pts = lattice(wm)
    bedges = R.mesh_boundary_edges(wm)

    def wall_d(p):
        return min(R.seg_dist_xz(p[0], p[1], a, b) for a, b in bedges)

    good = [p for p in pts if wall_d(p) >= 100.0]
    cx = sum(p[0] for p in good) / len(good)
    cz = sum(p[1] for p in good) / len(good)

    def reflect(p):                                # nearest lattice point to 2c - p
        rx, rz = 2 * cx - p[0], 2 * cz - p[1]
        return min(good, key=lambda q: (q[0] - rx) ** 2 + (q[1] - rz) ** 2)

    cands = []
    for a in good:
        b = reflect(a)
        if b == a or (b, a) in [(x[1], x[2]) for x in cands]:
            continue
        legs = R.sweep_polyline([a, b], wm, [], closed=False)
        spans = legs[0]["spans"]
        jam = sum((t1 - t0) for t0, t1 in spans) * legs[0]["len"] if spans else 0.0
        if jam >= 200.0:                           # a real hole, not a nick
            cands.append((-jam, a, b))
    cands.sort()
    for _negjam, a, b in cands:
        try:
            routed, inserted = pathfind.route_polyline(wm, [a, b], closed=True)
        except pathfind.RouteLegError:
            continue
        if inserted and len(routed) <= BT.ROUTE_CEILING:
            return a, b, routed
    raise SystemExit("no chord found that jams straight AND routes under the ceiling")


# --------------------------------------------------------------- gen / deploy
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

    wm = mesh()
    a, b, routed = pick_chord(wm)

    # THE OFFLINE PROOF — the same story lint tells:
    naive_legs = R.sweep_polyline([a, b], wm, closed=True)
    print("== offline proof ==")
    for w in R.describe_leg_problems("chord (naive)", naive_legs):
        print(f"  NAIVE  {w}")
    print(f"  ROUTED {a} -> {b} -> back becomes {routed} "
          f"({len(routed)}/{BT.ROUTE_CEILING} points)")
    routed_legs = R.sweep_polyline(routed, wm, closed=True)
    if any(leg["spans"] for leg in routed_legs):
        raise SystemExit("routed chord still jams?! (should be impossible)")
    print("  ROUTED sweep: clean\n")

    parts = [text, "\n# ---- AUTO-ROUTE BENCH (generated by "
                   "studies/behavior-trees/btroute_bench.py) ----\n"]
    parts.append(f'\n[[marker]]\nname = "chord_naive"\npos = [{a[0]}, {a[1]}]\n'
                 f"path = [[{a[0]}, {a[1]}], [{b[0]}, {b[1]}]]\nclosed = true\n")
    parts.append(f'\n[[marker]]\nname = "chord_auto"\npos = [{a[0]}, {a[1]}]\n'
                 f"path = [[{a[0]}, {a[1]}], [{b[0]}, {b[1]}]]\nclosed = true\n")
    parts.append(f'\n[[npc]]\nname = "wedge"\nmodel = "{WEDGE_MODEL}"\n'
                 f'pos = [{a[0]}, {a[1]}]\ndialogue = "Straight lines. It is the '
                 f'only way I know."\n')
    parts.append(f'\n[[npc]]\nname = "clever"\nmodel = "{CLEVER_MODEL}"\n'
                 f'pos = [{a[0] + 80}, {a[1] + 80}]\ndialogue = "I go around.  The '
                 f'kit showed me how."\n')
    parts.append(
        "\n[behavior]\nwarmup = 45\n"
        '\n[[behavior.unit]]\nnpc = "wedge"\nspeed = 50\n'
        '\n  [[behavior.unit.branch]]\n  do = { patrol = "chord_naive" }\n'
        '\n[[behavior.unit]]\nnpc = "clever"\nspeed = 50\n'
        '\n  [[behavior.unit.branch]]\n  do = { patrol = "chord_auto", route = "auto" }\n')
    BENCH_TOML.write_text("".join(parts), encoding="utf-8")
    print(f"wrote {BENCH_TOML}")
    print(f"  chord: {a} <-> {b}; routed circuit = {routed}")


def deploy() -> None:
    if not BENCH_TOML.exists():
        gen()
    r = subprocess.run([sys.executable, str(REPO / "tools" / "deploy_field.py"),
                        str(BENCH_TOML), "--id", str(FIELD_ID), "--name", FIELD_NAME,
                        "--text-block", str(FIELD_ID), "--mod-folder", MOD_FOLDER])
    if r.returncode != 0:
        raise SystemExit("deploy_field failed")
    print(f"""
PLAYTEST (first deploy of {FIELD_ID} needs a RELAUNCH; then ~ -> Warp -> {FIELD_ID}):
  Both soldiers patrol THE SAME two-point chord across the donut hole.
  1 WEDGE (the F0 soldier): walks straight at the far point, hits the hole's
    concave wall, and STAYS there pressing into it -- the disease, live.
  2 CLEVER (the F2 soldier): circuits cleanly around the hole, forever -- the
    build spliced the pathfinder detours in (route = "auto"); he never touches
    the notch.
  3 ~ -> Reload field: both reset to the start and repeat.
  Revert: py tools/scroll_out/revert_deploy_{FIELD_ID}.py""")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["gen", "deploy"])
    (gen if ap.parse_args().cmd == "gen" else deploy)()


if __name__ == "__main__":
    main()
