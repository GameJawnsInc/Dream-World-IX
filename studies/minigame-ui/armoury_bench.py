"""THE ARMOURY BENCH — the native shop as a hire menu (survey substrate #3),
first in-game run of the ITEM POOL bridge.

Field **30418** ("ARMOURY", a fresh 559 native fork like NUMPAD/the behavior
benches): the whole hire loop is SHIPPED vocabulary composed — `[[shop]]` +
`opens_shop` (the native Menu(2,id) shop UI) sells a CONTRACT item, and the NEW
`[[behavior.pool]] item =` lane converts held contracts into pooled spawns, one
per tick, at the player's feet. No DLL, no new opcode: `B_HAVE_ITEM` (0x64) is
the request, `RemoveItem` at the spawn site is the payment, and the shop UI's
own script-pause means purchases muster the moment the shop closes.

The contract is stock **Annoyntment** (id 248 — FF9's most obscure consumable)
re-texted "Soldier Contract" via `[[item_text]]` (net-new item ids are
DLL-bound; the TOML references the REAL name, the player sees the new one).
⚠ The rename rides the mod folder's TextPatch, so while this bench is deployed
Annoyntment reads "Soldier Contract" everywhere in this install. If the save
already holds any, they convert at boot — that's the bridge working, not a bug.

Beats (each independently verifiable):
  THE STRIP     "WRITS n | GIL n" — the NEW `item:` hud source, live inventory.
  THE SHOP      the Sutler sells Soldier Contracts (300 gil) — [[item]] price
                tune + [[shop]] + [[item_text]], all shipped lanes.
  THE MUSTER    close the shop holding N contracts -> N soldiers pop at your
                feet one tick apart; WRITS drains as they do.
  THE CRIER     a `have_item >= 3` cond fires a once-announce — the inventory
                cond proven separately from the pool.
  THE CAP       the levy is 4 soldiers; a 5th contract stays in the bag
                (an exhausted pool consumes NOTHING — check WRITS).
  THE RELOAD    ~ Reload refills the pool (v1 pooled semantics) but contracts
                are REAL inventory — leftovers convert again on re-entry.

Usage (repo root):   py studies/minigame-ui/armoury_bench.py gen | deploy
First deploy of 30418 = RELAUNCH once (id registration + the item CSVs +
TextPatch all load at launch). Revert: tools/scroll_out/revert_deploy_30418.py
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

BENCH = Path("C:/gd/_armoury_bench")
BASE_TOML = BENCH / "LDBM_NATIVE.field.toml"
BENCH_TOML = BENCH / "ARMOURY.field.toml"
FIELD_ID = 30418
FIELD_NAME = "ARMOURY"
MOD_FOLDER = "FF9CustomMap"
DONOR = "fbg_n11_ldbm_map158_lb_plz_0"                            # 559, pitch 68.8

SUTLER_MODEL = "GEO_NPC_F2_CSO"
SOLDIER_MODEL = "GEO_NPC_F0_CSO"
CONTRACT = "Annoyntment"          # stock id 248, re-texted "Soldier Contract"
CONTRACT_PRICE = 300
SHOP_ID = 40
LEVY = 4                          # the pool cap — a 5th contract must stay held


def read_spawn() -> tuple[int, int]:
    m = re.search(r"(?m)^spawn = \[(-?\d+), (-?\d+)\]", BASE_TOML.read_text(encoding="utf-8"))
    if not m:
        raise SystemExit("no [player] spawn in the base toml")
    return int(m.group(1)), int(m.group(2))


def posts() -> dict:
    """Sutler + crier on the SPAWN'S OWN FLOOR, inside the boot camera view
    (the NUMPAD lessons: floor-filter the lattice, keep the cast near the
    spawn->fountain axis, probe before claiming)."""
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

    lay = {"sutler": nearest(spawn[0] + 500, spawn[1] + 550),    # NE, toward the fountain
           "crier": nearest(spawn[0] + 100, spawn[1] + 500)}     # NNE, left of the sutler
    sx, sz = lay["sutler"]
    cx, cz = lay["crier"]
    if max(abs(sx - cx), abs(sz - cz)) < 250:
        raise SystemExit(f"posts collapsed: {lay}")
    return lay


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
    # the entry-settle directive: every authored field keeps the player experience
    if "entry_settle" not in text:
        text = text.replace("[camera]\n", '[camera]\nentry_settle = "auto"\n', 1)
        if "entry_settle" not in text:
            raise SystemExit("no [camera] block to hang entry_settle on — base toml changed?")

    lay = posts()
    sx, sz = lay["sutler"]
    cx, cz = lay["crier"]
    spawn = read_spawn()
    parts = [text, "\n# ---- THE ARMOURY (generated by "
                   "studies/minigame-ui/armoury_bench.py) ----\n"]
    # the contract: a stock consumable re-texted + re-priced, sold by a custom shop
    parts.append(f'''
[[item_text]]
name = "{CONTRACT}"
display_name = "Soldier Contract"
description = \"\"\"A sealed levy writ.
One soldier musters per writ the moment you leave the counter.\"\"\"

[[item]]
name = "{CONTRACT}"
price = {CONTRACT_PRICE}

[[shop]]
id = {SHOP_ID}
comment = "The Armoury"
sells = ["{CONTRACT}", "Potion", "Tent"]

[[npc]]
name = "sutler"
model = "{SUTLER_MODEL}"
pos = [{sx}, {sz}]
dialogue = "Writs for soldiers, soldier for a writ."
opens_shop = {SHOP_ID}

[[npc]]
name = "crier"
model = "{SUTLER_MODEL}"
pos = [{cx}, {cz}]
dialogue = "The muster grows."
''')
    # the levy: pooled soldiers whose currency is the contract item
    for i in range(LEVY):
        # PARKED dormant seats (the parked-choice idiom): a pooled unit never
        # boot-spawns — its 2-frame settle happens here, far off-play, before
        # MoveInstantEx lands it at the player's feet. Keeps the probe clean.
        parts.append(f'''
[[npc]]
name = "levy{i}"
model = "{SOLDIER_MODEL}"
pos = [{9000 + 400 * i}, 9000]
dialogue = "At your command!"
''')
    parts.append(f'''
[behavior]
warmup = 30

[[behavior.pool]]
name = "levy"
item = "{CONTRACT}"

[[behavior.hud]]
text = "[MPOS=10,48]WRITS [NUMB=0]   GIL [NUMB=1]"
values = ["item:{CONTRACT}", "gil"]
digits = [2, 6]

[[behavior.unit]]
npc = "crier"
  [[behavior.unit.branch]]
  when = [{{ have_item = ["{CONTRACT}", 3] }}]
  do = {{ announce = "Three writs and counting — the armoury runs deep, kupo!" }}
  once = "deep"
  [[behavior.unit.branch]]
  when = [{{ have_item = ["{CONTRACT}", 3] }}]
  do = {{ add_shop_item = [{SHOP_ID}, "Elixir"] }}
  once = "stock2"
  [[behavior.unit.branch]]
  do = {{ hold = [{cx}, {cz}] }}
''')
    for i in range(LEVY):
        parts.append(f'''
[[behavior.unit]]
npc = "levy{i}"
pooled = true
pool = "levy"
  [[behavior.unit.branch]]
  do = {{ hold_post = true }}
''')
    toml = "".join(parts)
    BENCH_TOML.write_text(toml, encoding="utf-8")
    from ff9mapkit import build as BLD                            # noqa: E402
    problems = BLD.validate(BLD.FieldProject.load(BENCH_TOML))
    if problems:
        raise SystemExit("validate:\n  " + "\n  ".join(problems))
    print(f"wrote {BENCH_TOML}\n  posts: {lay}  spawn: {spawn}\n  validate: clean")


def deploy() -> None:
    if not BENCH_TOML.exists():
        gen()
    r = subprocess.run([sys.executable, str(REPO / "tools" / "deploy_field.py"),
                        str(BENCH_TOML), "--id", str(FIELD_ID), "--name", FIELD_NAME,
                        "--text-block", str(FIELD_ID), "--mod-folder", MOD_FOLDER])
    if r.returncode != 0:
        raise SystemExit("deploy_field failed")
    print(f"""
PLAYTEST (first deploy of {FIELD_ID} = RELAUNCH once — the id, the item CSVs and
the TextPatch rename all load at launch — then ~ -> Warp -> {FIELD_ID}):
  0 BOOT: the WRITS/GIL strip top-left; the Sutler + the crier stand between
    spawn and the fountain; NO soldiers yet. (If your save already held
    Annoyntments they convert at boot — that IS the bridge; sell the spares
    at the shop if you want the clean run.)
  1 THE SHOP: talk to the Sutler -> a real item shop selling "Soldier
    Contract" (300 gil), Potion, Tent. Buy TWO contracts. WRITS reads 2 the
    moment you're back out.
  2 THE MUSTER: within a second of the shop closing, two soldiers pop at
    your feet, one tick apart, and WRITS drains 2 -> 1 -> 0. They hold where
    they mustered ("At your command!" on talk).
  3 THE CRIER + THE UNLOCK (round 3 — the snapshot fix): buy THREE in one
    visit (exactly 3 works now — round 2's four-writ skew was the pool eating
    one before the cond counted; have_item reads a top-of-tick snapshot) ->
    on exit the crier calls "Three writs and counting" ONCE and the SAME
    moment unlocks new stock — reopen the Sutler's shop: it now ALSO sells
    Elixir. Spawning in with 3 already held fires both too.
    The unlock is SESSION state: it survives ~ Reload AND New Game (the shop
    table is process memory, above the save layer) and resets at relaunch,
    where the condition simply re-asserts it when writs reach 3 again.
  4 THE CAP: keep buying — the levy stops at {LEVY} soldiers, and the extra
    contract STAYS in the bag (WRITS holds at 1+; an exhausted pool never
    consumes). Sellable back at the Sutler, it's a real item.
  5 ~ -> Reload field: the levy resets (v1 pooled semantics) but your held
    writs are SAVE state — they convert again as the field boots.
  Revert: py tools/scroll_out/revert_deploy_{FIELD_ID}.py""")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["gen", "deploy"])
    (gen if ap.parse_args().cmd == "gen" else deploy)()


if __name__ == "__main__":
    main()
