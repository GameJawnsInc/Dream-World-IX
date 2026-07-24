"""Rung 3 — THE SHOWCASE (behavior-trees study): a scene only the system makes writable.

Field **30412** ("BTRAID", the proven 559 top-down donor): a walled COMPOUND under
bandit raid — layered, interruptible, readable, and exercising every rung-3 verb:

  watchman (soldier, the gate)   Notices EITHER bandit within 600 -> his cry (Announce,
                                 ONE shared body via the dedupe) RAISES "alarm"
                                 (Do raise_flags); once they push past, he sprints
                                 (speed 70) for the keep. No hp — a herald, not a fighter.
  guard0/guard1 (soldiers)       PATROL SHIFTS: one alternator clock (400 ticks) flips
                                 "shift"; guard0 walks the OUTER ring on shift, the
                                 INNER otherwise — guard1 the exact opposite (Invert),
                                 so they visibly TRADE rings when the clock flips.
                                 On alarm: converge on the rally point at speed 65,
                                 chase bandits (standoff 180), duel at contact.
                                 At hp<=1: FLEE (speed 75) — priority refuges: the
                                 keep; if a bandit camps it (avoid_r 600), the market.
  captain (elite, hp 6, dmg 2)   Holds the keep. On alarm, a bandit within 1000 draws
                                 his war cry (sticky Once -> Announce; the closing
                                 bandit's CONTACT duel preempts the idle), then he
                                 duels at DOUBLE damage — the keep's boss.
  bandit0 (hp 4) / bandit1 (hp 6) Camp outside until the LEVER raises "raid": march
                                 the keep at speed 55, duel whoever meets them
                                 (MUTUAL), gloat ONCE if they reach the keep.
  civilian (old man, the market) WANDER: random drift (B_SYSVAR[0] RNG) around the
                                 market at speed 30, fresh target every ~110 ticks.
                                 On alarm (while bandits live): PANIC — Flee at
                                 speed 80 to the safehouse (or the east nook if a
                                 bandit camps the safehouse). War over -> ambles again.

The expected STORY (hp math, damage 1 per 30-tick swing unless noted): the lever arms
the raid -> the watchman cries + alarm -> guards break patrol and converge -> guard0
(hp 5) duels bandit0 (hp 4): bandit0 dies as guard0 hits 1 -> guard0 FLEES to the keep;
guard1 (hp 3) duels bandit1 (hp 6): at hp 1 guard1 flees mid-duel -> bandit1 (wounded)
resumes the march -> the captain's war cry, then kills it in 2 swings (damage 2).
Aftermath: alarm stays latched but with no bandit alive the guards RESUME their patrol
shifts, the civilian ambles back to the market, the wounded rest at the keep.

Usage (repo root):  py studies/behavior-trees/btraid_bench.py gen | deploy
First deploy of 30412 needs a RELAUNCH. Revert: tools/scroll_out/revert_deploy_30412.py
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

BENCH = Path("C:/gd/_btraid_bench")
BASE_TOML = BENCH / "LDBM_NATIVE.field.toml"
BENCH_TOML = BENCH / "BTRAID.field.toml"
REPORT = BENCH / "behavior-report.txt"
FIELD_ID = 30412
FIELD_NAME = "BTRAID"
MOD_FOLDER = "FF9CustomMap"
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
DONOR = "fbg_n11_ldbm_map158_lb_plz_0"

# toml order; duplicate models resolved by ORDER within each model group
CAST = [
    ("watchman", "GEO_NPC_F0_CSO", 217, "Bandits at the gate!  Sound the alarm!"),
    ("guard0",   "GEO_NPC_F0_CSO", 217, "Patrol shift's almost done."),
    ("guard1",   "GEO_NPC_F0_CSO", 217, "Keep to your route."),
    ("captain",  "GEO_NPC_F2_CSO", 218, "To arms!  Not one step past the keep!"),
    ("bandit0",  "GEO_MON_F0_FFG", 247, "The keep is ours!"),
    ("bandit1",  "GEO_MON_F0_FFG", 247, "Nothing left to stop us!"),
    ("civilian", "GEO_NPC_F0_JJY", 117, "Oh dear, oh dear..."),
]
STANDBY = bytes([0x22, 0x00, 0x01, 0x01, 0xFA, 0xFF])
CONTACT, STANDOFF = 300, 180


# --------------------------------------------------------------- helpers
def read_spawn() -> tuple[int, int]:
    m = re.search(r"(?m)^spawn = \[(-?\d+), (-?\d+)\]", BASE_TOML.read_text(encoding="utf-8"))
    if not m:
        raise SystemExit("no [player] spawn in the base toml")
    return int(m.group(1)), int(m.group(2))


def lattice(min_clear: float = 100.0) -> list[tuple[int, int]]:
    """On-mesh grid points at least ``min_clear`` from any walkmesh boundary edge —
    probe round 2's lesson: a bare on-mesh test accepts 1u edge slivers (the market
    landed on one), and walkers shoved by the 48u collision radius drift off any
    line that hugs a wall. Snap targets only to CLEAR points."""
    mesh = BgiWalkmesh.from_bytes((BENCH / "walkmesh.bgi").read_bytes())
    wv = mesh.world_verts()
    idx_tris = [tuple(t.vtx) for t in mesh.tris]
    tris = [tuple(wv[i] for i in t) for t in idx_tris]
    xs, zs = [v[0] for v in wv], [v[2] for v in wv]

    cnt: dict = {}
    for a, b, c in idx_tris:
        for u, v in ((a, b), (b, c), (c, a)):
            k = (v, u) if u > v else (u, v)
            cnt[k] = cnt.get(k, 0) + 1
    bedges = [((wv[a][0], wv[a][2]), (wv[b][0], wv[b][2]))
              for (a, b), n in cnt.items() if n == 1]

    def seg_d(px, pz, e0, e1):
        ax, az = e0
        bx, bz = e1
        dx, dz = bx - ax, bz - az
        L2 = dx * dx + dz * dz
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / L2))
        cx, cz = ax + t * dx, az + t * dz
        return ((px - cx) ** 2 + (pz - cz) ** 2) ** 0.5

    def clear(x, z):
        return (any(_pt_in_tri_xz(x, z, a, b, c) for a, b, c in tris)
                and min(seg_d(x, z, e0, e1) for e0, e1 in bedges) >= min_clear)

    pts = []
    for z in range(int(min(zs)) + 300, int(max(zs)) - 299, 250):
        for x in range(int(min(xs)) + 300, int(max(xs)) - 299, 250):
            if clear(x, z):
                pts.append((x, z))
    if len(pts) < 30:
        raise SystemExit(f"only {len(pts)} clear lattice points")
    return pts


def nearest(pts, x, z):
    return min(pts, key=lambda p: (p[0] - x) ** 2 + (p[1] - z) ** 2)


def layout() -> dict:
    pts = lattice()
    lay = {
        "spawn": read_spawn(),
        "keep": nearest(pts, -2250, 2250),
        # the GATEHOUSE = the neck between the plaza and the NW keep arm: every
        # keep-bound walk routes THROUGH it (probe round 2: straight lines to the
        # keep from anywhere south clip the bay west of the neck)
        "gatehouse": nearest(pts, -1391, 900),
        "watch_post": nearest(pts, -1050, -1300),
        "camp0": nearest(pts, -450, -1750),
        "camp1": nearest(pts, -850, -1780),
        "market": nearest(pts, -1641, 150),
        "safehouse": nearest(pts, -1891, -1600),   # sweep-picked: the ONE straight
                                                   # market->SW line with no off-mesh
                                                   # nick (7u parallel wall slide)
        "east_nook": nearest(pts, -500, 600),
        # routeA = THE MONUMENT CIRCUIT (probe round 1: the old outer ring's west and
        # north legs crossed off-mesh notches — guards stalled in 2 places; the field
        # is a donut around the central monument, so the outer patrol IS the donut).
        # Six corners: the hole bulges west to ~x-850 at its waist (probe round 2),
        # so the west side detours through the court's clear column at x-1141.
        "routeA": [nearest(pts, *p) for p in
                   [(-891, 1150), (1109, 1150), (1109, -850), (-891, -850),
                    (-1141, -100), (-1141, 400)]],
        # routeB = the west-court beat. The court's north half is cluttered (interior
        # notches); the z=500 chord is the SWEPT best (14u) — raw sweep-verified
        # points, deliberately NOT lattice-snapped
        "routeB": [(-1641, 500), (-1141, 500), (-1141, -100), (-1891, -100)],
    }
    for ring in ("routeA", "routeB"):
        if len(set(lay[ring])) != len(lay[ring]):
            raise SystemExit(f"{ring} collapsed: {lay[ring]}")
    if lay["camp0"] == lay["camp1"]:
        raise SystemExit("bandit camps collapsed onto one lattice point")
    return lay


def spawn_of(lay: dict) -> dict:
    # visual start = each unit's initial duty (shift flag starts 0: guard0 walks the
    # INNER ring first, guard1 — Invert — the outer)
    return {"watchman": lay["watch_post"], "guard0": lay["routeB"][0],
            "guard1": lay["routeA"][0], "captain": lay["keep"],
            "bandit0": lay["camp0"], "bandit1": lay["camp1"],
            "civilian": lay["market"]}


# --------------------------------------------------------------- the trees
def build_behavior(entries: dict[str, int], lay: dict,
                   txids: dict[str, int] | None = None) -> B.FieldBehavior:
    txids = txids or {}
    posts = spawn_of(lay)
    hp = {"guard0": 5, "guard1": 3, "captain": 6, "bandit0": 4, "bandit1": 6}
    fb = B.FieldBehavior(
        [B.UnitSpec(n, entries[n], spawn=posts[n], hp=hp.get(n), walk_speed=40)
         for n in posts])
    fb.public_flag("raid")                             # the lever arms the raid
    shift = fb.alternator("shift", 400)                # the patrol-shift clock
    bandits_up = fb.any_flag("bandit0.active", "bandit1.active")

    def duel(me: str, foe: str, damage: int = 1) -> B.Sequence:
        return B.Sequence(fb.active(foe), fb.near(me, foe, CONTACT),
                          B.Do(B.SwingAt(foe, damage=damage)))

    # --- watchman: notice EITHER bandit -> ONE cry raises the alarm, ONCE EVER.
    # RAID-gated (playtest-1 fix): the camps sit near the gate, so an ungated notice
    # box "saw" the dormant camp at field entry. STICKY-Once (playtest-2 fix): without
    # it, every re-entry of a bandit into the notice box re-dispatched the Announce —
    # the window spammed all battle. Once: he cries while they push the gate; the
    # moment they pass out of 450 it latches forever, and the alarm branch sends him
    # sprinting for the keep.
    cry = B.Announce(txids.get("watchman", 0))
    notice = fb.any_of(
        fb.all_of(fb.active("bandit0"), fb.near("watchman", "bandit0", 450)),
        fb.all_of(fb.active("bandit1"), fb.near("watchman", "bandit1", 450)))
    fb.units["watchman"].tree = B.Selector(
        B.Once("cry", B.Sequence(fb.flag("raid"), notice,
                                 B.Do(cry, raise_flags="alarm"))),
        # falls back to the MARKET with the wounded (probe round 3: every keep-bound
        # line from his post grazes the neck bay at 1-3u; the market route sweeps
        # clean at 18u+). March = the multi-leg walk verb this scene minted.
        B.Sequence(fb.flag("alarm"),
                   B.Do(B.March([(-1141, -100), lay["market"]],
                                arrive_r=250, speed=70))),
        B.Do(B.Hold(lay["watch_post"])),
    )

    # --- guards: die -> flee at hp<=1 -> alarm combat -> patrol shifts.
    # Flee refuges = market then east nook (probe round 2: any keep-bound flee line
    # clips the neck bay, and a wounded guard parked at the gatehouse sits in the
    # bandits' march lane -- he'd be finished at contact)
    for g, my_shift in (("guard0", shift), ("guard1", B.Invert(shift))):
        fb.units[g].tree = B.Selector(
            B.Sequence(fb.hp_le(g, 0), B.Do(B.Die())),
            B.Sequence(fb.hp_le(g, 1),
                       B.Do(B.Flee("bandit1", [lay["market"], lay["east_nook"]],
                                   avoid_r=600, speed=75))),
            B.Sequence(fb.flag("alarm"), bandits_up, B.Selector(
                duel(g, "bandit0"),
                duel(g, "bandit1"),
                B.Sequence(fb.active("bandit0"), fb.near(g, "bandit0", 900),
                           B.Do(B.Chase("bandit0", standoff=STANDOFF, speed=65))),
                B.Sequence(fb.active("bandit1"), fb.near(g, "bandit1", 900),
                           B.Do(B.Chase("bandit1", standoff=STANDOFF, speed=65))),
                B.Do(B.WalkTo(lay["gatehouse"], speed=65)),
            )),
            B.Sequence(my_shift, B.Do(B.Patrol(lay["routeA"], arrive_r=150))),
            B.Do(B.Patrol(lay["routeB"], arrive_r=150)),
        )

    # --- captain: the keep's boss — war cry, then double-damage duels
    fb.units["captain"].tree = B.Selector(
        B.Sequence(fb.hp_le("captain", 0), B.Do(B.Die())),
        B.Sequence(fb.flag("alarm"), bandits_up, B.Selector(
            duel("captain", "bandit0", damage=2),
            duel("captain", "bandit1", damage=2),
            B.Once("warcry", B.Sequence(
                fb.any_of(fb.near("captain", "bandit0", 1000),
                          fb.near("captain", "bandit1", 1000)),
                B.Do(B.Announce(txids.get("captain", 0))))),
            B.Do(B.Hold(lay["keep"])),
        )),
        B.Do(B.Hold(lay["keep"])),
    )

    # --- bandits: THE TWO LANES (the field's own topology — two ways around the
    # monument). bandit1 storms the short WEST lane through the gatehouse; bandit0
    # swings the long EAST lane around the monument and arrives as a SECOND WAVE.
    # March (minted here) walks each lane's probe-swept waypoints and holds the keep;
    # duels preempt and the march resumes at the current waypoint.
    lanes = {
        "bandit0": [(859, -850), (1109, 1150), (-891, 1150),
                    lay["gatehouse"], lay["keep"]],
        "bandit1": [lay["gatehouse"], lay["keep"]],
    }
    for i, b in enumerate(("bandit0", "bandit1")):
        fb.units[b].tree = B.Selector(
            B.Sequence(fb.hp_le(b, 0), B.Do(B.Die())),
            B.Sequence(fb.flag("raid"), B.Selector(
                duel(b, "captain"),
                duel(b, "guard0"),
                duel(b, "guard1"),
                B.Once(f"gloat{i}", B.Sequence(
                    fb.near_point(b, lay["keep"], 300),
                    B.Do(B.Announce(txids.get(b, 0))))),
                B.Do(B.March(lanes[b], arrive_r=250, speed=55)),
            )),
            B.Do(B.Hold(posts[b])),
        )

    # --- civilian: ambles (Wander) -> panics (Flee) -> ambles again
    fb.units["civilian"].tree = B.Selector(
        B.Sequence(fb.flag("alarm"), bandits_up,
                   B.Do(B.Flee("bandit0", [lay["safehouse"], lay["east_nook"]],
                               avoid_r=600, speed=80))),
        B.Do(B.Wander(lay["market"], radius=500, hold=110, speed=30)),
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
    posts = spawn_of(lay)
    # flag indices must match deploy-time compilation: same construction order
    fb = build_behavior({n: 0 for n in posts}, lay)
    raid = fb.public_flag("raid")

    parts = [text, "\n# ---- BT RAID BENCH (generated by btraid_bench.py) ----\n"]
    for name, geo, _mid, line in CAST:
        x, z = posts[name]
        parts.append(f'\n[[npc]]\nname = "{name}"\nmodel = "{geo}"\n'
                     f'pos = [{x}, {z}]\ndialogue = "{line}"\n')
    # probe-visible spatial plan (build-inert): named points for every static target
    # + ROUTE markers (`path`) for every scripted walk line, so the probe's sweep
    # verifies straight-walk legality of the rings, the marches, and the flee lines
    wp = {"keep": lay["keep"], "gatehouse": lay["gatehouse"], "market": lay["market"],
          "safehouse": lay["safehouse"], "east_nook": lay["east_nook"]}
    for name, (x, z) in wp.items():
        parts.append(f'\n[[marker]]\nname = "{name}"\npos = [{x}, {z}]\n')

    def route(name: str, points: list, closed: bool = False) -> str:
        pp = ", ".join(f"[{x}, {z}]" for x, z in points)
        x0, z0 = points[0]
        return (f'\n[[marker]]\nname = "{name}"\npos = [{x0}, {z0}]\n'
                f"path = [{pp}]\nclosed = {'true' if closed else 'false'}\n")

    parts.append(route("ringA", lay["routeA"], closed=True))
    parts.append(route("ringB", lay["routeB"], closed=True))
    parts.append(route("march0", [posts["bandit0"], (859, -850), (1109, 1150),
                                  (-891, 1150), lay["gatehouse"], lay["keep"]]))
    parts.append(route("march1", [posts["bandit1"], lay["gatehouse"], lay["keep"]]))
    parts.append(route("panic", [lay["market"], lay["safehouse"]]))
    # representative flee line: a guard wounded at the ring's SW reach -> the market
    parts.append(route("gflee", [lay["routeA"][4], lay["market"]]))
    parts.append(route("watch_run", [lay["watch_post"], (-1141, -100), lay["market"]]))
    cx, cz = lay["spawn"]
    h = 220
    parts.append(
        f'\n[[choice]]\nzone = [[{cx - h},{cz + h}],[{cx + h},{cz + h}],'
        f'[{cx + h},{cz - h}],[{cx - h},{cz - h}]]\n'
        f'prompt = "Raid bench: loose the bandits?"\ninstant = true\n'
        f'\n[[choice.options]]\ntext = "Begin the raid"\n'
        f'reply = "Torches on the ridge..."\nset_flag = [{raid}, 1]\n'
        f'\n[[choice.options]]\ntext = "Not yet."\n')
    BENCH_TOML.write_text("".join(parts), encoding="utf-8")
    print(f"wrote {BENCH_TOML}\n  layout {lay}\n  raid flag {raid}")


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
        eb = EbScript.from_bytes(data)
        txids = {n: _talk_txid(data, eb, entries[n])
                 for n in ("watchman", "captain", "bandit0", "bandit1")}
        fb = build_behavior(entries, lay, txids)
        cb = fb.compile()
        p.write_bytes(fb.install(data, cb))
        report = cb.report
    REPORT.write_text(report + "\n", encoding="utf-8")
    print(f"\n{report}\n\nreport saved -> {REPORT}")
    print(f"""
PLAYTEST (layout probe-verified this round — every walk line sweeps ON-MESH):
  ~ -> Warp -> {FIELD_ID}  (~ Reload picks up this redeploy; RELAUNCH only if first time)
  1 BEFORE THE RAID: one soldier walks THE MONUMENT CIRCUIT (the big ring around
    the central rotunda, dipping into the west court), the other a compact court
    beat; every ~7s the shift clock flips and they TRADE routes. The old man
    ambles around the market at a stroll; the watchman holds the south gate;
    the captain the north-west keep; two Fangs camp south, dormant.
  2 THE LEVER (at spawn): "Begin the raid" -> THE TWO LANES: the big Fang (6hp)
    storms the short WEST lane through the gatehouse; the small Fang (4hp) swings
    the long EAST lane around the monument — a SECOND WAVE (~30s behind).
  3 THE ALARM: as they leave camp past the gate the watchman's line pops ONCE
    (fixed — no more spam), then he falls back to the market (70). The old man
    PANICS: bolts (80) south-west for the safehouse, right past your spawn.
  4 THE BATTLE: the guards drop their routes, converge on the gatehouse at 65,
    intercept, duel. A guard at 1 hp turns and FLEES mid-fight — to the market
    (or the east nook if a bandit is camping the market). The wounded Fang that
    breaks through draws the captain's war cry at the keep and dies to his
    double-damage blade. Watch wave 2 arrive from the north-east afterwards.
  5 AFTERMATH: no bandit alive -> the old man wanders back to the market; guards
    above 1 hp resume their traded routes; 1-hp survivors shelter at the market.
  6 ~ -> Reload resets everything (flags, HP, corpses, the shift clock, waves).
  Revert: py tools/scroll_out/revert_deploy_{FIELD_ID}.py""")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["gen", "deploy"])
    (gen if ap.parse_args().cmd == "gen" else deploy)()


if __name__ == "__main__":
    main()
