"""Rung 1 — THE FIRST TREES IN-GAME (behavior-trees study).

A fresh native fork of the top-down Zaghnol arena (559) at field 30410 ("BTREE"),
carrying FIVE units whose tag-1/action functions are fully COMPILED from behavior
trees (ff9mapkit.content.behavior) — zero hand-written bytecode:

  patroller (soldier)   Selector( near(player,400) -> Chase(player),  Patrol(square ring) )
                        THE CORE DEMO: patrols, notices you, approaches, resumes.
  veteran (elite, hp 6) Die if hp<=0; SwingAt(beast) when adjacent; else Hold(post).
  beast (Fang, hp 4)    Die if hp<=0; SwingAt(veteran) when adjacent; else Patrol
                        north-point <-> the veteran's post.
                        THE AUTONOMOUS DUEL: runs with no player involvement — beast
                        marches in, they duel (~1 dmg/s each), beast dies at 4 ticks,
                        the veteran (2 hp left) resumes his post.
  greeter (old man)     Once("greet", near(player,500) -> Chase(player)); else Hold.
                        THE ONCE DEMO (sticky): chases WHILE you're near; the first
                        time you escape past 500, never again (until ~ Reload).
  stalker (Mu)          Cooldown(150, near(player,700) -> Chase(player)); else Hold.
                        THE COOLDOWN DEMO (sticky): chases while you're near; once you
                        escape, needs ~2.5s before it can re-engage.

Usage (repo root):   py studies/behavior-trees/bt_bench.py gen | deploy
First deploy of 30410 needs a RELAUNCH; after that ~ -> Reload field hot-reloads and
fully resets (Main_Init re-preset). Revert: py tools/scroll_out/revert_deploy_30410.py
The deploy prints + saves the compile report — the ~ Flags watch map (selected bytes
are the LIVE node trace per unit).
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

BENCH = Path("C:/gd/_bt_bench")
BASE_TOML = BENCH / "LDBM_NATIVE.field.toml"
BENCH_TOML = BENCH / "BTREE.field.toml"
REPORT = BENCH / "behavior-report.txt"
FIELD_ID = 30410
FIELD_NAME = "BTREE"
MOD_FOLDER = "FF9CustomMap"
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
DONOR = "fbg_n11_ldbm_map158_lb_plz_0"                            # 559, pitch 68.8

# name -> (model GEO name, model id, dialogue)
CAST = {
    "patroller": ("GEO_NPC_F0_CSO", 217, "Patrol duty.  Move along."),
    "veteran":   ("GEO_NPC_F2_CSO", 218, "Hold the line!"),
    "beast":     ("GEO_MON_F0_FFG", 247, "Grrrr."),
    "greeter":   ("GEO_NPC_F0_JJY", 117, "Ah!  A visitor!  Come here!"),
    "stalker":   ("GEO_MON_F0_MUU", 248, "..."),
}
STANDBY = bytes([0x22, 0x00, 0x01, 0x01, 0xFA, 0xFF])             # content.npc standby loop


# --------------------------------------------------------------- walkmesh helpers
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
        raise SystemExit(f"only {len(pts)} lattice points — mesh read wrong?")
    return pts


def nearest(pts, x, z):
    return min(pts, key=lambda p: (p[0] - x) ** 2 + (p[1] - z) ** 2)


def layout() -> dict:
    pts = lattice()
    ring = [nearest(pts, *p) for p in
            [(-1437, -680), (-903, -680), (-903, -1748), (-1437, -1748)]]
    vet_post = nearest(pts, -1971, 1990)
    beast_north = nearest(pts, -2505, 2524)
    spawn = read_spawn()
    greeter_post = nearest(pts, spawn[0] + 500, spawn[1] + 350)
    stalker_post = nearest(pts, -400, -300)
    lay = {"ring": ring, "vet_post": vet_post, "beast_north": beast_north,
           "greeter_post": greeter_post, "stalker_post": stalker_post,
           "spawn": spawn}
    if len(set(ring)) != 4:
        raise SystemExit(f"patrol ring collapsed: {ring}")
    return lay


# --------------------------------------------------------------- the trees
def build_behavior(entries: dict[str, int], lay: dict) -> B.FieldBehavior:
    fb = B.FieldBehavior([
        B.UnitSpec("patroller", entries["patroller"], spawn=lay["ring"][0], walk_speed=40),
        B.UnitSpec("veteran", entries["veteran"], spawn=lay["vet_post"], hp=6, walk_speed=45),
        B.UnitSpec("beast", entries["beast"], spawn=lay["beast_north"], hp=4, walk_speed=40),
        B.UnitSpec("greeter", entries["greeter"], spawn=lay["greeter_post"], walk_speed=55),
        B.UnitSpec("stalker", entries["stalker"], spawn=lay["stalker_post"], walk_speed=55),
    ])
    fb.units["patroller"].tree = B.Selector(
        B.Sequence(fb.near("patroller", B.PLAYER, 400), B.Do(B.Chase(B.PLAYER))),
        B.Do(B.Patrol(lay["ring"], arrive_r=150)),
    )
    fb.units["veteran"].tree = B.Selector(
        B.Sequence(fb.hp_le("veteran", 0), B.Do(B.Die())),
        B.Sequence(fb.active("beast"), fb.near("veteran", "beast", 250),
                   B.Do(B.SwingAt("beast"))),
        B.Do(B.Hold(lay["vet_post"])),
    )
    fb.units["beast"].tree = B.Selector(
        B.Sequence(fb.hp_le("beast", 0), B.Do(B.Die())),
        B.Sequence(fb.active("veteran"), fb.near("beast", "veteran", 250),
                   B.Do(B.SwingAt("veteran"))),
        B.Do(B.Patrol([lay["beast_north"], lay["vet_post"]], arrive_r=150)),
    )
    fb.units["greeter"].tree = B.Selector(
        B.Once("greet", B.Sequence(fb.near("greeter", B.PLAYER, 500),
                                   B.Do(B.Chase(B.PLAYER)))),
        B.Do(B.Hold(lay["greeter_post"])),
    )
    fb.units["stalker"].tree = B.Selector(
        B.Cooldown(150, B.Sequence(fb.near("stalker", B.PLAYER, 700),
                                   B.Do(B.Chase(B.PLAYER)))),
        B.Do(B.Hold(lay["stalker_post"])),
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
    text = re.sub(r"(?ms)^\[\[gateway\]\].*?(?=^\[|\Z)", "", text)   # a closed room

    lay = layout()
    parts = [text, "\n# ---- BT BENCH (generated by studies/behavior-trees/bt_bench.py) ----\n"]
    spawn_of = {"patroller": lay["ring"][0], "veteran": lay["vet_post"],
                "beast": lay["beast_north"], "greeter": lay["greeter_post"],
                "stalker": lay["stalker_post"]}
    for name, (geo, _mid, line) in CAST.items():
        x, z = spawn_of[name]
        parts.append(f'\n[[npc]]\nname = "{name}"\nmodel = "{geo}"\n'
                     f'pos = [{x}, {z}]\ndialogue = "{line}"\n')
    BENCH_TOML.write_text("".join(parts), encoding="utf-8")
    print(f"wrote {BENCH_TOML}")
    print(f"  layout: {lay}")


def discover(data: bytes) -> dict[str, int]:
    eb = EbScript.from_bytes(data)
    out: dict[str, int] = {}
    for name, (_geo, mid, _line) in CAST.items():
        sig = bytes([0x2F, 0x00]) + struct.pack("<H", mid)
        found = []
        for idx in range(eb.entry_count):
            e = eb.entry(idx)
            f0, f1 = e.func_by_tag(0), e.func_by_tag(1)
            if f0 is None or f1 is None:
                continue
            if sig in bytes(data[f0.abs_start:f0.abs_end]) \
                    and bytes(data[f1.abs_start:f1.abs_end]) == STANDBY:
                found.append(idx)
        if len(found) != 1:
            raise SystemExit(f"unit {name!r}: expected 1 entry (model {mid}), got {found}")
        out[name] = found[0]
    return out


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
        fb = build_behavior(discover(data), lay)
        cb = fb.compile()
        p.write_bytes(fb.install(data, cb))
        report = cb.report
        print(f"patched {p.name} ({len(data)} bytes in)")
    REPORT.write_text(report + "\n", encoding="utf-8")
    print(f"\n{report}\n\nreport saved -> {REPORT}")
    print(f"""
PLAYTEST (RELAUNCH first — new id {FIELD_ID}): ~ -> Warp -> {FIELD_ID}
  1 PATROLLER (soldier, the square): walks the 4-corner ring; walk up within ~400 ->
    he comes to YOU; walk away -> he resumes the ring at the nearest corner.
  2 THE DUEL (north plaza, runs by itself): the Fang marches from the north to the
    elite soldier's post; they square up and trade blows ~1/s; the Fang dies (~4s)
    and VANISHES; the elite (2 hp left) walks back to his post. ~ Reload re-runs it.
  3 GREETER (old man near spawn): chases you while you're within ~500; escape once ->
    he gives up FOREVER (until Reload). The Once demo.
  4 STALKER (Mu, east): chases while you're within ~700; escape -> it needs ~2.5s
    cooldown before it will re-engage. The Cooldown demo.
  5 Everything resets with ~ -> Reload field.
  Revert: py tools/scroll_out/revert_deploy_{FIELD_ID}.py""")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["gen", "deploy"])
    (gen if ap.parse_args().cmd == "gen" else deploy)()


if __name__ == "__main__":
    main()
