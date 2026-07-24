"""Rung 2 — THE REGRESSION PROOF (behavior-trees study).

The fort-condor skirmish re-expressed ENTIRELY as compiled behavior trees on a fresh
field **30411** ("BTWAR", the same 559 top-down donor): 2 Fang attackers march on a goal
post (an elite herald stands there), 2 soldier defenders posted on the square acquire,
intercept, and duel; lane A's defender wins (5 hp vs 3), lane B's attacker wins (5 vs 3),
resumes the march, and the herald's breach line pops ONCE at the goal — the exact
staging, HP, and outcomes of fort-condor playtest 6, with ZERO hand-written bytecode and
no referee: the compiler subsumes it.

Variant 2 ("+ militia"): two extra soldiers posted on lane B's approach stand in for
placed recruits — they acquire either attacker within 700, chase to standoff, and duel
(MUTUAL — attackers fight back, the fort-condor rung-3 debt closed by trees for free).
With militia, lane B's attacker dies before the gate: no breach.

The lever at spawn arms it: row 1 = the pure regression; row 2 = + militia; ~ -> Reload
resets everything (flags, HP, corpses).

Usage (repo root):  py studies/behavior-trees/btwar_bench.py gen | deploy
First deploy of 30411 needs a RELAUNCH. Revert: tools/scroll_out/revert_deploy_30411.py
"""
from __future__ import annotations

import argparse
import re
import struct
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))

from ff9mapkit.content import behavior as B                       # noqa: E402
from ff9mapkit.eb.model import EbScript                           # noqa: E402
from ff9mapkit.scene.bgi import BgiWalkmesh, _pt_in_tri_xz        # noqa: E402

BENCH = Path("C:/gd/_btwar_bench")
BASE_TOML = BENCH / "LDBM_NATIVE.field.toml"
BENCH_TOML = BENCH / "BTWAR.field.toml"
REPORT = BENCH / "behavior-report.txt"
FIELD_ID = 30411
FIELD_NAME = "BTWAR"
MOD_FOLDER = "FF9CustomMap"
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
DONOR = "fbg_n11_ldbm_map158_lb_plz_0"

# toml order; duplicate models are resolved by ORDER within each model group
CAST = [
    ("attacker0", "GEO_MON_F0_FFG", 247, "Grrrr."),
    ("attacker1", "GEO_MON_F0_FFG", 247, "Grrrr!"),
    ("defender0", "GEO_NPC_F0_CSO", 217, "Hold the west line!"),
    ("defender1", "GEO_NPC_F0_CSO", 217, "Hold the east line!"),
    ("militia0",  "GEO_NPC_F0_CSO", 217, "Reporting for duty!"),
    ("militia1",  "GEO_NPC_F0_CSO", 217, "Ready, sir!"),
    ("herald",    "GEO_NPC_F2_CSO", 218, "The beasts broke through!  The gate is lost!"),
]
STANDBY = bytes([0x22, 0x00, 0x01, 0x01, 0xFA, 0xFF])
CONTACT, ACQUIRE, STANDOFF = 300, 700, 180


# --------------------------------------------------------------- helpers
def read_spawn() -> tuple[int, int]:
    m = re.search(r"(?m)^spawn = \[(-?\d+), (-?\d+)\]", BASE_TOML.read_text(encoding="utf-8"))
    if not m:
        raise SystemExit("no [player] spawn in the base toml")
    return int(m.group(1)), int(m.group(2))


def lattice() -> list[tuple[int, int]]:
    mesh = BgiWalkmesh.from_bytes((BENCH / "walkmesh.bgi").read_bytes())
    wv = mesh.world_verts()
    tris = [tuple(wv[i] for i in t.vtx) for t in mesh.tris]
    xs, zs = [v[0] for v in wv], [v[2] for v in wv]

    def on_mesh(x, z):
        return any(_pt_in_tri_xz(x, z, a, b, c) for a, b, c in tris)

    pts = []
    for z in range(int(min(zs)) + 300, int(max(zs)) - 299, 250):
        for x in range(int(min(xs)) + 300, int(max(xs)) - 299, 250):
            if on_mesh(x, z):
                pts.append((x, z))
    if len(pts) < 30:
        raise SystemExit(f"only {len(pts)} lattice points")
    return pts


def nearest(pts, x, z):
    return min(pts, key=lambda p: (p[0] - x) ** 2 + (p[1] - z) ** 2)


def layout() -> dict:
    pts = lattice()
    return {
        "spawn": read_spawn(),
        "atk": [nearest(pts, -2391, 2400), nearest(pts, -891, 2400)],
        "def": [nearest(pts, -1391, -600), nearest(pts, -891, -600)],
        "militia": [nearest(pts, -1141, -1100), nearest(pts, -641, -1100)],
        "goal": nearest(pts, -1391, -1850),
        "herald": nearest(pts, -1041, -1850),
    }


# --------------------------------------------------------------- the trees
def build_behavior(entries: dict[str, int], lay: dict,
                   herald_txid: int = 0) -> B.FieldBehavior:
    hp = {"attacker0": 3, "attacker1": 5, "defender0": 5, "defender1": 3,
          "militia0": 3, "militia1": 3}
    posts = {"attacker0": lay["atk"][0], "attacker1": lay["atk"][1],
             "defender0": lay["def"][0], "defender1": lay["def"][1],
             "militia0": lay["militia"][0], "militia1": lay["militia"][1]}
    fb = B.FieldBehavior(
        [B.UnitSpec(n, entries[n], spawn=posts[n], hp=hp[n],
                    walk_speed=40 if n.startswith("attacker") else 50)
         for n in posts])
    fb.public_flag("war.arm")
    fb.public_flag("war.militia")
    armed = fb.any_flag("war.arm", "war.militia")

    def duel(me: str, foe: str) -> list:
        """The mutual-combat branch pair: swing at contact, else close to standoff."""
        return [
            B.Sequence(fb.active(foe), fb.near(me, foe, CONTACT), B.Do(B.SwingAt(foe))),
        ]

    for lane in (0, 1):
        a, d = f"attacker{lane}", f"defender{lane}"
        fb.units[a].tree = B.Selector(
            B.Sequence(fb.hp_le(a, 0), B.Do(B.Die())),
            B.Sequence(armed,
                       B.Selector(
                           *duel(a, d),
                           # fight militia ONLY in the militia variant — in the pure
                           # regression they stand down and the march ignores them
                           B.Sequence(fb.flag("war.militia"),
                                      B.Selector(*duel(a, "militia0"),
                                                 *duel(a, "militia1"))),
                           B.Once("breach", B.Sequence(
                               fb.near_point(a, lay["goal"], 200),
                               B.Do(B.Announce(herald_txid)))),
                           B.Do(B.WalkTo(lay["goal"])),
                       )),
            B.Do(B.Hold(posts[a])),
        )
        fb.units[d].tree = B.Selector(
            B.Sequence(fb.hp_le(d, 0), B.Do(B.Die())),
            B.Sequence(armed, fb.active(a),
                       B.Selector(
                           *duel(d, a),
                           B.Sequence(fb.near(d, a, ACQUIRE),
                                      B.Do(B.Chase(a, standoff=STANDOFF))),
                           B.Do(B.Hold(posts[d])),
                       )),
            B.Do(B.Hold(posts[d])),
        )
    for m in ("militia0", "militia1"):
        engage = []
        for a in ("attacker0", "attacker1"):
            engage += duel(m, a)
            engage.append(B.Sequence(fb.active(a), fb.near(m, a, ACQUIRE),
                                     B.Do(B.Chase(a, standoff=STANDOFF))))
        fb.units[m].tree = B.Selector(
            B.Sequence(fb.hp_le(m, 0), B.Do(B.Die())),
            B.Sequence(fb.flag("war.militia"), B.Selector(
                *engage, B.Do(B.Hold(posts[m])))),
            B.Do(B.Hold(posts[m])),
        )
    return fb


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
    text = re.sub(r"(?ms)^\[\[gateway\]\].*?(?=^\[|\Z)", "", text)

    lay = layout()
    posts = {"attacker0": lay["atk"][0], "attacker1": lay["atk"][1],
             "defender0": lay["def"][0], "defender1": lay["def"][1],
             "militia0": lay["militia"][0], "militia1": lay["militia"][1],
             "herald": lay["herald"]}
    # flag indices must match deploy-time compilation: same construction order
    fb = build_behavior({n: 0 for n, *_ in CAST if n != "herald"}, lay)
    arm = fb.public_flag("war.arm")
    mil = fb.public_flag("war.militia")

    parts = [text, "\n# ---- BT WAR BENCH (generated by btwar_bench.py) ----\n"]
    for name, geo, _mid, line in CAST:
        x, z = posts[name]
        parts.append(f'\n[[npc]]\nname = "{name}"\nmodel = "{geo}"\n'
                     f'pos = [{x}, {z}]\ndialogue = "{line}"\n')
    cx, cz = lay["spawn"]
    h = 220
    parts.append(
        f'\n[[choice]]\nzone = [[{cx - h},{cz + h}],[{cx + h},{cz + h}],'
        f'[{cx + h},{cz - h}],[{cx - h},{cz - h}]]\n'
        f'prompt = "War bench: begin the assault?"\ninstant = true\n'
        f'\n[[choice.options]]\ntext = "Skirmish (the regression)"\n'
        f'reply = "The beasts are loose!"\nset_flag = [{arm}, 1]\n'
        f'\n[[choice.options]]\ntext = "Skirmish + militia"\n'
        f'reply = "Militia, to your posts!"\nset_flag = [{mil}, 1]\n'
        f'\n[[choice.options]]\ntext = "Not yet."\n')
    BENCH_TOML.write_text("".join(parts), encoding="utf-8")
    print(f"wrote {BENCH_TOML}\n  layout {lay}\n  arm flag {arm}, militia flag {mil}")


def discover(data: bytes) -> dict[str, int]:
    eb = EbScript.from_bytes(data)
    by_model: dict[int, list[int]] = {}
    for idx in range(eb.entry_count):
        e = eb.entry(idx)
        f0, f1 = e.func_by_tag(0), e.func_by_tag(1)
        if f0 is None or f1 is None:
            continue
        if bytes(data[f1.abs_start:f1.abs_end]) != STANDBY:
            continue
        for _n, _g, mid, _l in CAST:
            if bytes([0x2F, 0x00]) + struct.pack("<H", mid) in bytes(data[f0.abs_start:f0.abs_end]):
                by_model.setdefault(mid, []).append(idx)
                break
    out: dict[str, int] = {}
    for name, _geo, mid, _line in CAST:                # toml order within a model group
        group = by_model.get(mid, [])
        if not group:
            raise SystemExit(f"unit {name!r}: no entry left for model {mid}")
        out[name] = group.pop(0)
    return out


def _talk_txid(data: bytes, eb: EbScript, idx: int) -> int:
    f3 = eb.entry(idx).func_by_tag(3)
    body = bytes(data[f3.abs_start:f3.abs_end])
    at = body.index(bytes([0x1F, 0x00]))
    return struct.unpack_from("<H", body, at + 4)[0]


def deploy() -> None:
    if not BENCH_TOML.exists():
        gen()
    r = subprocess.run([sys.executable, str(REPO / "tools" / "deploy_field.py"),
                        str(BENCH_TOML), "--id", str(FIELD_ID), "--name", FIELD_NAME,
                        "--text-block", str(FIELD_ID), "--mod-folder", MOD_FOLDER])
    if r.returncode != 0:
        raise SystemExit("deploy_field failed")
    lay = layout()
    ebs = [p for p in sorted((GAME / MOD_FOLDER).rglob(f"*{FIELD_NAME}*.eb*"))
           if p.suffix in (".eb", ".bytes")]
    if not ebs:
        raise SystemExit("no deployed .eb found")
    report = None
    for p in ebs:
        data = p.read_bytes()
        entries = discover(data)
        txid = _talk_txid(data, EbScript.from_bytes(data), entries["herald"])
        units = {k: v for k, v in entries.items() if k != "herald"}
        fb = build_behavior(units, lay, herald_txid=txid)
        cb = fb.compile()
        p.write_bytes(fb.install(data, cb))
        report = cb.report
    REPORT.write_text(report + "\n", encoding="utf-8")
    print(f"\n{report}\n\nreport saved -> {REPORT}")
    print(f"""
PLAYTEST (RELAUNCH first — new id {FIELD_ID}): ~ -> Warp -> {FIELD_ID}
  A THE REGRESSION (lever row 1): the exact fort-condor playtest-6 show —
    both Fangs march from the north; the defenders step out, stop at spear's
    length, duel; WEST lane: the soldier (5hp) kills the beast (3hp) and
    returns to post; EAST lane: the beast (5hp) kills the soldier (3hp),
    resumes the march, reaches the gate -> the herald's breach line, ONCE.
  B + MILITIA (reload, lever row 2): two extra soldiers near the gate join in —
    the east beast gets ganged (mutual combat: it fights back) and dies BEFORE
    the gate: NO breach. Militia losses are possible; survivors return to post.
  C ~ -> Reload resets everything (flags, HP, corpses).
  Revert: py tools/scroll_out/revert_deploy_{FIELD_ID}.py""")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["gen", "deploy"])
    (gen if ap.parse_args().cmd == "gen" else deploy)()


if __name__ == "__main__":
    main()
