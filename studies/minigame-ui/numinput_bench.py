"""THE NUMERIC-INPUT BENCH — the Treno bid stepper as kit vocabulary
(`[[numeric_input]]`, content/numinput.py), first in-game run.

Field **30417** ("NUMPAD", a fresh 559 native fork — the same top-down Zaghnol
arena as the behavior benches 30410-30416), pure product path: field.toml +
plain deploy_field, zero bench patching, NO [behavior] block (the stepper is
field content — it must stand alone on stock Memoria).

Two instances prove the parameterization (both share the modal scratch — only
one is ever open):
  THE BID (broker, east)     digits 3 x100, gil_ceiling, start 1 — the stock
                             Treno shape: pink cursor overlay, per-place steps,
                             the held-key auto-repeat ramp, the live gil clamp,
                             cancel vs the "[NUMB=0]" submit echo.
  THE MUSTER (quartermaster, west)  digits 2 x1, max 20 — the fort-condor
                             "how many units" picker. Its submit raises flag
                             8290 and lands Global.Int16[2000]; the choice's
                             flag-gated "Report" row APPEARS after the first
                             submit — the persistent-result proof, no log
                             reading needed.

Usage (repo root):   py studies/minigame-ui/numinput_bench.py gen | deploy
First deploy of 30417 needs a RELAUNCH (a new DictionaryPatch line); then
~ -> Reload field re-reads everything. Revert: tools/scroll_out/revert_deploy_30417.py
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

BENCH = Path("C:/gd/_numinput_bench")
BASE_TOML = BENCH / "LDBM_NATIVE.field.toml"
BENCH_TOML = BENCH / "NUMPAD.field.toml"
FIELD_ID = 30417
FIELD_NAME = "NUMPAD"
MOD_FOLDER = "FF9CustomMap"
DONOR = "fbg_n11_ldbm_map158_lb_plz_0"                            # 559, pitch 68.8

BROKER_MODEL = "GEO_NPC_F2_CSO"
QUARTER_MODEL = "GEO_NPC_F0_CSO"
MUSTER_FLAG = 8290           # kit-internal band (events 8000 / cutscene 8100 / choice 8200);
                             # clear of the mognet lock 8376+ and the story-safe 8712+


# --------------------------------------------------------------- walkmesh helpers
def read_spawn() -> tuple[int, int]:
    m = re.search(r"(?m)^spawn = \[(-?\d+), (-?\d+)\]", BASE_TOML.read_text(encoding="utf-8"))
    if not m:
        raise SystemExit("no [player] spawn in the base toml")
    return int(m.group(1)), int(m.group(2))


def posts() -> dict:
    """Two talk posts on the SPAWN'S OWN FLOOR (the bttable round-1 balcony lesson:
    559 is multi-floor and a bbox pick can land on an upper sheet)."""
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
    floor = max(holding, key=lambda f: len(by_floor[f]))
    tris = by_floor[floor]
    xs = [v[0] for tri in tris for v in tri]
    zs = [v[2] for tri in tris for v in tri]

    def on_mesh(x, z):
        return any(_pt_in_tri_xz(x, z, a, b, c) for a, b, c in tris)

    pts = [(x, z)
           for z in range(int(min(zs)) + 300, int(max(zs)) - 299, 250)
           for x in range(int(min(xs)) + 300, int(max(xs)) - 299, 250)
           if on_mesh(x, z)]
    if len(pts) < 30:
        raise SystemExit(f"only {len(pts)} lattice points on floor {floor} — mesh read wrong?")

    def nearest(x, z):
        return min(pts, key=lambda p: (p[0] - x) ** 2 + (p[1] - z) ** 2)

    lay = {"broker": nearest(spawn[0] + 500, spawn[1] + 550),    # SE flank — clear of donor
           "quarter": nearest(spawn[0] - 350, spawn[1])}         # arrival 9 (jam radius, probe-caught)
    bx, bz = lay["broker"]
    qx, qz = lay["quarter"]
    if max(abs(bx - qx), abs(bz - qz)) < 250:                    # the ~192u actor-jam law + margin
        raise SystemExit(f"posts collapsed: {lay}")
    return lay


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
    # strip the carried donor bystanders (Zidane-object, townsfolk, the TGR creature) —
    # the condor-bench lesson: dressing that LOOKS like cast makes the real cast
    # unfindable (round 1 here: "the broker is MIA" with both NPCs present)
    text = re.sub(r"(?ms)^\[\[object\]\].*?(?=^\[|\Z)", "", text)

    lay = posts()
    bx, bz = lay["broker"]
    qx, qz = lay["quarter"]
    parts = [text, "\n# ---- NUMERIC-INPUT BENCH (generated by "
                   "studies/minigame-ui/numinput_bench.py) ----\n"]
    # THE BID — the stock Treno shape, x100 with the live gil clamp
    parts.append(f'''
[[npc]]
name = "broker"
model = "{BROKER_MODEL}"
pos = [{bx}, {bz}]

[[numeric_input]]
name = "bid"
result = 2004
digits = 3
multiplier = 100
gil_ceiling = true
start = 1
label = "Bid"
suffix = " Gil"
echo = "You bid [NUMB=0] Gil.  (The clamp is your purse, kupo.)"

[[choice]]
npc = "broker"
prompt = "Care to bid on the lot, kupo?"
instant = true
[[choice.options]]
text = "Place a bid"
input = "bid"
[[choice.options]]
text = "Never mind"
''')
    # THE MUSTER — the condor-shaped count picker + the persistent-result proof row
    parts.append(f'''
[[npc]]
name = "quarter"
model = "{QUARTER_MODEL}"
pos = [{qx}, {qz}]

[[numeric_input]]
name = "muster"
result = 2000
digits = 2
max = 20
label = "Soldiers"
echo = "[NUMB=0] soldiers, on the ledger."
flag = {MUSTER_FLAG}

[[choice]]
npc = "quarter"
prompt = "The muster roll, then?"
instant = true
[[choice.options]]
text = "How many soldiers?"
input = "muster"
[[choice.options]]
text = "Report"
requires_flag = {MUSTER_FLAG}
reply = "The order stands at [NUMB=0] soldiers."
[[choice.options]]
text = "Never mind"
''')
    toml = "".join(parts)
    BENCH_TOML.write_text(toml, encoding="utf-8")
    from ff9mapkit import build as BLD                            # noqa: E402
    problems = BLD.validate(BLD.FieldProject.load(BENCH_TOML))
    if problems:
        raise SystemExit("validate:\n  " + "\n  ".join(problems))
    print(f"wrote {BENCH_TOML}\n  posts: {lay}\n  validate: clean")


def deploy() -> None:
    if not BENCH_TOML.exists():
        gen()
    r = subprocess.run([sys.executable, str(REPO / "tools" / "deploy_field.py"),
                        str(BENCH_TOML), "--id", str(FIELD_ID), "--name", FIELD_NAME,
                        "--text-block", str(FIELD_ID), "--mod-folder", MOD_FOLDER])
    if r.returncode != 0:
        raise SystemExit("deploy_field failed")
    print(f"""
PLAYTEST (round 2 — ~ Reload / re-warp is enough, {FIELD_ID} is registered):
  The plaza now holds EXACTLY TWO people (donor bystanders stripped): the two
  City Soldiers. The BROKER stands UP-RIGHT of spawn (toward the fountain);
  the QUARTERMASTER is just LEFT of spawn. The menus name themselves
  (probe-verified: screen-up = north on this camera).
  THE BID (the broker — "Care to bid on the lot, kupo?"):
   1 Talk -> "Place a bid" -> the stepper: a "00100 Gil"-style line mid-left,
     the RIGHTMOST digit tinted PINK, a button legend below. No walking while
     it's open (the choice bracket holds control).
   2 Left/Right moves the pink tint across the three digits; Up/Down steps
     1/10/100 (x100 on screen). HOLD Up: after a short beat it auto-repeats.
   3 The ceiling: the bid can never exceed 999 OR your purse / 100 — try to
     step past your gil and it pins.
   4 Cancel (B) -> everything closes, NO echo. Re-open: back at 100 (re-seeded).
   5 Confirm -> "You bid N Gil." with EXACTLY the number shown.
  THE MUSTER (the quartermaster, WEST):
   6 "How many soldiers?" -> a 2-digit picker, caps at 20.
   7 Submit -> "N soldiers, on the ledger." — then reopen the menu: a new
     "Report" row exists now (the submit flag) and reads the number back —
     THE RESULT PROOF (Global.Int16 + flag both landed).
   8 ~ -> Reload field: both steppers still work (scratch re-seeds), and the
     "Report" ROW is still there (the flag persists). Its NUMBER resets to 0
     until the next submit — gMesValue is per-session display state; the
     durable value a consumer reads is Global.Int16[2000] (~ Flags shows it).
  Revert: py tools/scroll_out/revert_deploy_{FIELD_ID}.py""")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["gen", "deploy"])
    (gen if ap.parse_args().cmd == "gen" else deploy)()


if __name__ == "__main__":
    main()
