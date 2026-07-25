"""THE DATA-TABLE BENCH — gScriptVector tables as compiler vocabulary, and the
FIRST IN-GAME CONSUMER of the 0xD3 computed-array-indexing lane anywhere (the
Path-B falsification dividend: `exprasm` learned VECTOR 2026-07-24, offline-only
until this field runs).

Field **30415** ("BTTABLE", a fresh 559 native fork, the same top-down Zaghnol
arena as 30410-30414), PURE PRODUCT PATH: everything is `[behavior]` TOML + plain
deploy_field — zero bench bytecode patching.

What it proves (each beat = one mechanism):
  THE SEED        Main_Init writes the tables into the save's gScriptVector
                  (size<-0, size<-n, non-zero cells) — if any announce ever fires,
                  the seed landed.
  THE WAVE CLOCK  [[behavior.schedule]]: `wave += 1` while the countdown HUD sits
                  below `sched[wave]` — the read's INDEX is the wave cell itself
                  (a nested VECTOR read = genuine computed indexing at runtime).
                  Bands are DATA: sched = [100, 80, 60] on a 120s clock.
  THE COUNTER     `die = "kills"` bumps a cell from a dispatch body (edge-safe:
                  the body runs once); `counter_ge` reads it back.
  THE TERMINATOR  after wave 3 the clock reads sched[3] — off the end — which
                  fails soft to 0, so the clock STOPS ITSELF (no latch flag).
                  Proof = the field keeps running with no fourth announce and
                  no softlock.

The demo — a tiny timed raid:
  herald (spawn-side)   calls the waves: "Wave one/two/three" as the clock crosses
                        each band, and "the tally reads two" once both fangs die.
  fang0 / fang1 (Mu)    DORMANT at the far wall until their wave arrives
                        (branches gated on counter_ge["wave", 1/2]) — then they
                        march mid-arena, duel the guard (MUTUAL), and die into
                        the kill counter.
  guard (mid-arena)     the intercept: swings at any fang in reach, hp 8.

Usage (repo root):   py studies/behavior-trees/bttable_bench.py gen | deploy
First deploy of 30415 needs a RELAUNCH; then ~ -> Reload field = the full reset
(tables re-seed, counters zero, fangs return to the wall, the clock restarts).
Revert: py tools/scroll_out/revert_deploy_30415.py
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
from ff9mapkit.scene.bgi import BgiWalkmesh, _pt_in_tri_xz        # noqa: E402

BENCH = Path("C:/gd/_bttable_bench")
BASE_TOML = BENCH / "LDBM_NATIVE.field.toml"
BENCH_TOML = BENCH / "BTTABLE.field.toml"
REPORT = BENCH / "behavior-report.txt"
FIELD_ID = 30415
FIELD_NAME = "BTTABLE"
MOD_FOLDER = "FF9CustomMap"
DONOR = "fbg_n11_ldbm_map158_lb_plz_0"                            # 559, pitch 68.8

HERALD_MODEL = "GEO_NPC_F2_CSO"
GUARD_MODEL = "GEO_NPC_F0_CSO"
FANG_MODEL = "GEO_MON_F0_MUU"

SIEGE_SECONDS = 120
SCHED = [100, 80, 60]                        # wave start-times (remaining seconds)
N_FANGS = 2
CONTACT_R = 250                              # swing reach (> the 160 chase standoff)


# --------------------------------------------------------------- walkmesh helpers
def read_spawn() -> tuple[int, int]:
    m = re.search(r"(?m)^spawn = \[(-?\d+), (-?\d+)\]", BASE_TOML.read_text(encoding="utf-8"))
    if not m:
        raise SystemExit("no [player] spawn in the base toml")
    return int(m.group(1)), int(m.group(2))


def lattice() -> list[tuple[int, int]]:
    """Lattice points on the SPAWN'S OWN FLOOR only — 559 is multi-floor (plaza +
    balconies + stairs), and the round-1 playtest put fang0's dormant post on a
    BALCONY (the bbox corner belongs to an upper floor): it could never walk down
    to the duel, so the kill tally could never complete. Posts must share the
    player's floor."""
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
    floor = max(holding, key=lambda f: len(by_floor[f]))     # overlap -> the big floor
    tris = by_floor[floor]
    xs = [v[0] for tri in tris for v in tri]
    zs = [v[2] for tri in tris for v in tri]

    def on_mesh(x, z):
        return any(_pt_in_tri_xz(x, z, a, b, c) for a, b, c in tris)

    pts = []
    for z in range(int(min(zs)) + 300, int(max(zs)) - 299, 250):
        for x in range(int(min(xs)) + 300, int(max(xs)) - 299, 250):
            if on_mesh(x, z):
                pts.append((x, z))
    if len(pts) < 30:
        raise SystemExit(f"only {len(pts)} lattice points on floor {floor} — mesh read wrong?")
    return pts


def nearest(pts, x, z):
    return min(pts, key=lambda p: (p[0] - x) ** 2 + (p[1] - z) ** 2)


def layout() -> dict:
    pts = lattice()
    spawn = read_spawn()
    xs, zs = [p[0] for p in pts], [p[1] for p in pts]
    cx, cz = (min(xs) + max(xs)) // 2, (min(zs) + max(zs)) // 2
    lay = {
        "spawn": spawn,
        "herald": nearest(pts, spawn[0] + 350, spawn[1]),        # spawn-side caller
        "mid": nearest(pts, cx, cz),                             # the guard's post
        "wall": [nearest(pts, max(xs) - 300, max(zs) - 300),     # fang0's dormant spot
                 nearest(pts, min(xs) + 400, max(zs) - 300)],    # fang1's
    }
    if len({lay["herald"], lay["mid"], *lay["wall"]}) != 4:
        raise SystemExit(f"posts collapsed: {lay}")
    return lay


# --------------------------------------------------------------- TOML emit helpers
def _t(v) -> str:
    if isinstance(v, str):
        return f'"{v}"'
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(_t(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{ " + ", ".join(f"{k} = {_t(x)}" for k, x in v.items()) + " }"
    return str(v)


def _branch(when=None, do=None, **keys) -> str:
    out = ["\n  [[behavior.unit.branch]]"]
    if when:
        out.append("  when = [" + ", ".join(_t(c) for c in when) + "]")
    out.append("  do = " + _t(do))
    for k, v in keys.items():
        out.append(f"  {k} = {_t(v)}")
    return "\n".join(out) + "\n"


def behavior_toml(lay: dict) -> str:
    parts = [f"\n[behavior]\nwarmup = 45\ntimer = {SIEGE_SECONDS}\n"
             f'counters = ["wave", "kills"]\n'
             f'\n[[behavior.table]]\nname = "sched"\nvalues = {_t(SCHED)}\n'
             f'\n[[behavior.schedule]]\ncounter = "wave"\ntable = "sched"\n']
    # THE HERALD: pure announcer — every line is a table/counter readout
    parts.append(f'\n[[behavior.unit]]\nnpc = "herald"\nspeed = 40\n')
    parts.append(_branch(when=[{"counter_ge": ["kills", N_FANGS]}],
                         do={"announce": "Both fangs are down, kupo!"
                                         "  The tally cell reads two."},
                         once="won"))
    # w1 also exercises table_ge with a COMPUTED index (sched[wave] at wave==1 is 80)
    parts.append(_branch(when=[{"counter_eq": ["wave", 1]},
                               {"table_ge": ["sched", "wave", 1]}],
                         do={"announce": "Wave one!  The clock crossed the first band."},
                         once="w1"))
    parts.append(_branch(when=[{"counter_eq": ["wave", 2]}],
                         do={"announce": "Wave two!  Second band."},
                         once="w2"))
    parts.append(_branch(when=[{"counter_eq": ["wave", 3]}],
                         do={"announce": "Wave three is a BLANK — three bands in the"
                                         " table, only two fangs exist.  The clock"
                                         " stops itself now; nothing else happens."},
                         once="w3"))
    parts.append(_branch(do={"hold": list(lay["herald"])}))
    # THE GUARD: the intercept at mid-arena (MUTUAL with the fangs)
    parts.append(f'\n[[behavior.unit]]\nnpc = "guard"\nhp = 8\nspeed = 50\n')
    parts.append(_branch(when=[{"hp_le": 0}], do={"die": True}))
    for f in range(N_FANGS):
        parts.append(_branch(when=[{"active": f"fang{f}"},
                                   {"near": [f"fang{f}", CONTACT_R]}],
                             do={"swing_at": f"fang{f}", "interval": 25}))
    parts.append(_branch(do={"hold": list(lay["mid"])}))
    # THE FANGS: dormant at the wall until their wave; then march mid, duel, die
    # into the kill counter (die = "kills" bumps the cell once, edge-safe)
    for f in range(N_FANGS):
        wx, wz = lay["wall"][f]
        parts.append(f'\n[[behavior.unit]]\nnpc = "fang{f}"\nhp = 3\nspeed = 45\n')
        parts.append(_branch(when=[{"hp_le": 0}], do={"die": "kills"}))
        parts.append(_branch(when=[{"active": "guard"},
                                   {"near": ["guard", CONTACT_R]}],
                             do={"swing_at": "guard", "interval": 35}))
        # the approach is a ROUTED march (route="auto"): the straight chord is
        # heavily off-mesh on this plaza (fountain/tower) — the round-1 fang only
        # arrived by blocked-walk sliding; the router splices real detours
        parts.append(_branch(when=[{"counter_ge": ["wave", f + 1]}],
                             do={"march": [[wx, wz], list(lay["mid"])],
                                 "route": "auto", "speed": 55}))
        parts.append(_branch(do={"hold": [wx, wz]}))
    return "".join(parts)


# --------------------------------------------------------------- gen / deploy
def _compile_report(parts: list) -> tuple:
    """Validate + dry-compile (placeholder txids) — returns (raw, report text)."""
    import tomllib
    raw = tomllib.loads("".join(parts))
    problems = BT.validate(raw)
    if problems:
        raise SystemExit("behavior validate:\n  " + "\n  ".join(problems))
    all_units = [u["npc"] for u in raw["behavior"]["unit"]]
    txids = {(ui, bi): 900 + 10 * ui + bi
             for ui, bi, _br in BT.announce_lines(raw)}
    routed = None
    if BT.wants_autoroute(raw):
        wmesh = BgiWalkmesh.from_bytes((BENCH / "walkmesh.bgi").read_bytes())
        routed = BT.autoroute_plan(raw, wmesh)
        for line in BT.describe_autoroute(routed, raw):
            print("  route:", line)
    fb = BT.build(raw, npc_slots={n: i + 2 for i, n in enumerate(all_units)},
                  npc_txids_by_name={n.get("name"): 0 for n in raw.get("npc", [])},
                  behavior_txids=txids, routed=routed)
    return raw, fb.compile().report


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

    lay = layout()
    parts = [text, "\n# ---- DATA-TABLE BENCH (generated by "
                   "studies/behavior-trees/bttable_bench.py) ----\n"]
    hx, hz = lay["herald"]
    parts.append(f'\n[[npc]]\nname = "herald"\nmodel = "{HERALD_MODEL}"\n'
                 f'pos = [{hx}, {hz}]\ndialogue = "The schedule is data, kupo."\n')
    mx, mz = lay["mid"]
    parts.append(f'\n[[npc]]\nname = "guard"\nmodel = "{GUARD_MODEL}"\n'
                 f'pos = [{mx}, {mz}]\ndialogue = "I hold the middle."\n')
    for f in range(N_FANGS):
        wx, wz = lay["wall"][f]
        parts.append(f'\n[[npc]]\nname = "fang{f}"\nmodel = "{FANG_MODEL}"\n'
                     f'pos = [{wx}, {wz}]\ndialogue = "Kweeeh!"\n')
    parts.append(behavior_toml(lay))
    _raw, report = _compile_report(parts)
    BENCH_TOML.write_text("".join(parts), encoding="utf-8")
    print(f"wrote {BENCH_TOML}")
    print(f"  layout: {lay}")
    print("\n" + report)


def deploy() -> None:
    if not BENCH_TOML.exists():
        gen()
    r = subprocess.run([sys.executable, str(REPO / "tools" / "deploy_field.py"),
                        str(BENCH_TOML), "--id", str(FIELD_ID), "--name", FIELD_NAME,
                        "--text-block", str(FIELD_ID), "--mod-folder", MOD_FOLDER])
    if r.returncode != 0:
        raise SystemExit("deploy_field failed")
    raw, report = _compile_report([BENCH_TOML.read_text(encoding="utf-8")])
    REPORT.write_text(report + "\n(dry-run placeholders; the build bound the real "
                      "slots/txids)\n", encoding="utf-8")
    print(f"\nreport saved -> {REPORT}")
    print(f"""
PLAYTEST (~ -> Warp -> {FIELD_ID}; already registered -> ~ Reload is enough):
  This field is the FIRST IN-GAME RUN of .eb computed array indexing (0xD3
  VECTOR) — the wave schedule lives in a gScriptVector table, not in code.
  0 BOOT: a 2:00 countdown HUD; herald + guard posted, two Mus DORMANT at the
    far wall. Nobody moves for ~1.5s (warm-up), then stillness EXCEPT idle —
    the schedule holds until the first band.
  1 ~20s in (clock 1:40): herald pops "Wave one!" and fang0 marches mid-arena.
    (The clock read sched[wave] with wave ITSELF a table cell — if this fires
    at 1:40 sharp, computed indexing works.)
  2 The duel: fang0 reaches the guard -> MUTUAL swings -> fang0 drops (its
    death bumps the kill cell).
  3 ~40s (1:20): "Wave two!" -> fang1 marches. Kill it the same way.
  4 When the SECOND fang drops: herald pops "Both fangs are down" — that
    branch reads counter_ge["kills", 2] straight from the vector.
  5 ~60s (1:00): "Wave three — the schedule is spent." NOTHING spawns (data
    says 3 bands, only 2 fangs) and — the terminator proof — the clock walks
    off the table's end, reads 0, and STOPS ITSELF: no fourth announce ever,
    no softlock, the field keeps running to 0:00 uneventfully.
  6 ~ -> Reload field: tables RE-SEED (counters zero, fangs back at the wall,
    clock restarts at 2:00) — the whole system is deterministic per entry.
  Revert: py tools/scroll_out/revert_deploy_{FIELD_ID}.py""")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["gen", "deploy"])
    (gen if ap.parse_args().cmd == "gen" else deploy)()


if __name__ == "__main__":
    main()
