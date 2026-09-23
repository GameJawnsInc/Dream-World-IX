"""RUNG 1 of the fight-ledger arc -- the declarative [scene.ledger], in-game. One harness launch.

    py tools/play.py studies/fight-ledger/rung1_ledger.py --label fl-rung1

Benches (studies/fight-ledger/bench/, all FF9CustomMap): field 30880 LEDGER1 declares dwix_fl1 (persist,
id 6004880, 12 cells) + the story flag fl1_slain (8910) and reads the ledger with EXISTING surface only;
field 30883 LEDGER1N declares no table; battle 30881 LEDGER1W (two Goblins sharing AI entry 2 + a Fang on
entry 1) and 30882 LEDGER1S (compiled against the never-deployed 13-cell ledger1_v2 declaration) carry
DECLARATIVE [scene.ledger] blocks -- no raw RPN.

    NC1  New Game -> 30883 -> fight 30881 before any field seeded the ledger: the flag lands, no table is created
    NC2  30880's first entry seeds 12 cells (killer seed 15)
         fight 1 from 30880: kill Fang, Goblin A, Goblin B; per-slot hit counts, the replay, the slot filter,
         killer / ability / killer HP, the story flag; the field ANNOUNCES the win and consumes the outcome
    NC5  re-entering 30880 keeps the ledger and does not re-narrate
         an escape: the field announces "you ran"; Init rows kept, no dying rows
    NC6  the stale scene: its dying hook ran (witness flag 8911) but the live gate kept every write out --
         cell 12 would have APPENDED on the 12-cell table
"""
from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "studies" / "persistent-tables"))
sys.path.insert(0, str(REPO / "ff9mapkit"))
import rung0_persist as R0  # noqa: E402  (the calibrated helpers: _hud, _sandbox, sentinel)
from ff9mapkit import save as _save  # noqa: E402
from ff9mapkit.content import behavior as B  # noqa: E402
from ff9mapkit.eb.model import EbScript  # noqa: E402

FIELD, NOTABLE, NEUTRAL = 30880, 30883, 30863
WIN, STALE = 30881, 30882
T, G, N = 6004880, 7004880, 12
W12, W13 = B.persist_check_word("dwix_fl1", 12), B.persist_check_word("dwix_fl1", 13)
SLAIN, WITNESS = 8910, 8911
TOLD_WIN, TOLD_RAN = 14868, 14869                  # 30880's public flags (printed by its build)
ORDER = (6, 4, 5)                                  # kill the Fang, then Goblin A, then Goblin B
SEED = [0, 0, 0, 0, 0, -1, 0, 0, 15, -1, -1, 0]
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
_s = R0.sentinel
ROWS = {"T SIZE": _s(2), "CHECK OK": _s(1), "OUTCOME": _s(1), "FIGHTS": _s(2), "HITS0": _s(3), "KILLS": _s(3),
        "KILLER": _s(2), "WHERE": _s(5)}


def _hud(g, **kw):
    return R0._hud(g, ROWS, want_header="LEDGER 1 30880", **kw)


def _vecs(g) -> dict:
    g.wait_frames(30)
    return _save.read_extra_vectors(R0._sandbox(g) / "SavedData_ww_Memoria_Autosave.dat") or {}


def _deployed_eb(name: str) -> EbScript:
    p = (GAME / "FF9CustomMap" / "StreamingAssets" / "Assets" / "Resources" / "CommonAsset" / "EventEngine"
         / "EventBinary" / "Battle" / "us" / f"EVT_BATTLE_{name}.eb.bytes")
    return EbScript.from_bytes(p.read_bytes())


def _preflight(g) -> None:
    g.check((W12, W13) == (17972799, 26511439), "the two check words are the formula's", f"{W12}, {W13}")
    win, stale = _deployed_eb("LEDGER1W"), _deployed_eb("LEDGER1S")
    g.check(win.entries[2].func_by_tag(9) is not None and win.entries[1].func_by_tag(7) is not None,
            "deployed LEDGER1W: entry 2 carries the ADDED tag 9, the Fang's entry 1 the ADDED tag 7")
    w12 = W12.to_bytes(4, "little")[:3]
    w13 = W13.to_bytes(4, "little")[:3]
    g.check(w12 in win.data and w13 not in win.data, "deployed LEDGER1W gates on the 12-cell check word")
    g.check(w13 in stale.data and w12 not in stale.data, "deployed LEDGER1S gates on the 13-cell (stale) word")


def _policy_counter(counts: dict):
    def policy(s, _slot):
        alive = {u["slot"] for u in s.units(player=False) if u.get("alive") and u.get("targetable")}
        for t in ORDER:
            if t in alive:
                counts[t] = counts.get(t, 0) + 1
                return {"command": "Attack", "target": t}
        return None
    return policy


def _fight(g, scene: int, label: str) -> dict:
    counts: dict = {}
    st = g.start_battle(scene, group=0)
    roster = sorted((u["slot"], u.get("hp_max_raw")) for u in st.units(player=False))
    out = {"roster": roster, "counts": counts, "result": None, "stalled": False, "zhp": None}
    g.shot(f"{label}-start")
    try:
        out["result"] = g.fight(policy=_policy_counter(counts), finish=False, timeout=300, max_turns=60)
    except Exception as err:                        # noqa: BLE001 -- reported as a check
        out["stalled"] = True
        print(f"[fl-rung1] {label}: {err}")
        g.shot(f"{label}-stalled")
    st = g.state
    z = [u for u in st.units(player=True) if u.get("slot") == 0]
    out["zhp"] = z[0].get("hp_raw") if z else None
    out["bits"] = {b: st.flag(b) for b in (SLAIN, WITNESS)}
    g.shot(f"{label}-over")
    return out


def _back(g, field: int, direction: str) -> float:
    g.leave_battle()
    back = g.wait_for(lambda s: s.ui_state == "FieldHUD" and s.field_id == field and not s.fading,
                      timeout=90, what=f"the return to {field}")
    x0, z0 = back.player_x, back.player_z
    g.wait_frames(20)
    g.walk(direction, 30)
    st = g.state
    return ((st.player_x - x0) ** 2 + (st.player_z - z0) ** 2) ** 0.5


def _wait_flag_and_text(g, bit: int, text: str, timeout: float = 15.0) -> tuple:
    seen_text, deadline = False, time.time() + timeout
    while time.time() < deadline:
        st = g.state
        seen_text = seen_text or any(text in t for t in st.texts)
        if st.flag(bit) and seen_text:
            return True, True
        g.wait_frames(4)
    st = g.state
    return bool(st.flag(bit)), seen_text


def _quiet(g, seconds: float = 10.0) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        st = g.state
        if st.flag(TOLD_WIN) or st.flag(TOLD_RAN):
            return False
        g.wait_frames(10)
    return True


def run(g) -> None:
    _preflight(g)
    sandbox = R0._sandbox(g)
    parked = g.run_dir / "sandbox-before"
    for p in sorted(sandbox.glob("SavedData_ww*.dat")):
        parked.mkdir(parents=True, exist_ok=True)
        shutil.move(str(p), str(parked / p.name))
    g.note("fight-ledger rung 1")
    g.newgame()
    g.watch(SLAIN, WITNESS, TOLD_WIN, TOLD_RAN)

    # -- NC1: a fight before any declaring field seeded the ledger ----------------------------------
    g.warp(NOTABLE)
    f0 = _fight(g, WIN, "0-unseeded")
    g.check(f0["roster"] == [(4, 60), (5, 60), (6, 40)], "LEDGER1W spawns Goblin A, Goblin B and the Fang",
            str(f0["roster"]))
    g.check(f0["result"] in (1, 2) and not f0["stalled"], "NC1: the unseeded fight ends in victory", str(f0))
    g.check(f0["bits"][SLAIN], "NC1: the flag row landed with the gate closed (Goblin B's dying hook ran)",
            str(f0["bits"]))
    moved = _back(g, NOTABLE, "left")
    g.check(moved > 50, "the field resumed after the unseeded fight", f"walked {moved:.0f}u")
    g.warp(NEUTRAL)
    v = _vecs(g)
    g.check(T not in v and G not in v,
            "NC1: no table and no guard were CREATED -- the gate kept every cell write out of a never-seeded save",
            str({k: v[k] for k in v if k in (T, G)}))
    g.flag(SLAIN, False)

    # -- NC2: the seed ----------------------------------------------------------------------------
    g.warp(FIELD)
    seed = _hud(g)
    g.shot("1-seeded")
    g.check(seed == {"T SIZE": N, "CHECK OK": 1, "OUTCOME": 0, "FIGHTS": 0, "HITS0": 0, "KILLS": 0, "KILLER": 15,
                     "WHERE": 0}, "NC2: 30880's first entry seeded 12 cells (killer seed 15)", str(seed))
    g.check(_quiet(g, 5), "NC2: nothing to narrate before a fight")

    # -- fight 1 ----------------------------------------------------------------------------------
    f1 = _fight(g, WIN, "2-fight1")
    g.check(f1["result"] in (1, 2) and not f1["stalled"], "fight 1 ends in victory: two die_atk Goblins died "
            "without stalling", str(f1))
    g.check(f1["bits"][SLAIN], "fight 1: fl1_slain set before the field returned", str(f1["bits"]))
    moved = _back(g, FIELD, "left")
    g.check(moved > 50, "the field resumed after fight 1", f"walked {moved:.0f}u")
    told, text = _wait_flag_and_text(g, TOLD_WIN, "THEY FELL")
    g.shot("3-told-win")
    g.check(told and text, "THE CATCHING FIELD NARRATED THE FIGHT: its table_eq branch announced "
            "'LEDGER: THEY FELL' and raised told_win", f"flag {told}, text {text}")
    g.warp(NEUTRAL)
    v = _vecs(g)
    led = v.get(T)
    c = f1["counts"]
    want = [0, 1, c.get(4), c.get(5), c.get(6), 0, 2, 1, 0, 176, f1["zhp"], FIELD]
    print(f"[fl-rung1] ledger after fight 1: {led} guard {v.get(G)}; attacks {c}; Zidane HP {f1['zhp']}")
    g.check(led is not None and len(led) == N and v.get(G) == [W12],
            "the ledger is still 12 cells under its own check word", f"{led} guard {v.get(G)}")
    if led is not None and len(led) == N:
        g.check(led[0] == 0, "the reader CONSUMED the outcome (1 -> 0) after announcing it", str(led[0]))
        g.check(led[1] == 1, "NC3: fights = 1 -- the slot filter ran slot 0's init row once, not once per Goblin",
                str(led[1]))
        g.check(led[2] == c.get(4) and led[3] == c.get(5),
                "the Goblins' hit counts include the killing blow (the reaction rows REPLAYED into tag 9)",
                f"{led[2:4]} vs attacks {c.get(4)}, {c.get(5)}")
        g.check(led[4] == c.get(6), "the Fang's ADDED tag 7 counted every hit, its lethal one included",
                f"{led[4]} vs {c.get(6)}")
        g.check(led[5] == 0, "Goblin B's last HP is the lethal 0 (the replayed hp row)", str(led[5]))
        g.check(led[6] == 2 and led[7] == 1,
                "NC4: one dying per Goblin (kills 2), none for the Fang; Goblin B's own tally 1 (slot filter "
                "in tag 9)", str(led[6:8]))
        g.check(led[8] == 0, "the killer is a CharacterId: 0 = Zidane (B_SYSLIST[0] B_MEMBER(70) B_PICK)",
                str(led[8]))
        g.check(led[9] == 176, "the killing ability: Attack (176)", str(led[9]))
        g.check(f1["zhp"] is not None and led[10] == f1["zhp"], "the killer's HP at the kill",
                f"{led[10]} vs published {f1['zhp']}")
        g.check(led[11] == FIELD, "the field the fight began in", str(led[11]))
    after1 = led

    # -- NC5: re-entry keeps it and does not re-narrate -------------------------------------------
    g.warp(FIELD)
    kept = _hud(g)
    g.shot("4-reentered")
    exp = None if after1 is None else {"T SIZE": N, "CHECK OK": 1, "OUTCOME": after1[0], "FIGHTS": after1[1],
                                       "HITS0": after1[2], "KILLS": after1[6], "KILLER": after1[8],
                                       "WHERE": after1[11]}
    g.check(exp is not None and kept == exp, "NC5: 30880's fresh Main_Init KEPT the battle-written ledger",
            f"{kept} vs {exp}")
    g.check(_quiet(g, 10), "NC5: a consumed outcome is not narrated again")

    # -- an escape ---------------------------------------------------------------------------------
    st = g.start_battle(WIN, group=0)
    fled = g.flee(timeout=120)
    g.check(fled, "the escape battle: the party fled")
    moved = _back(g, FIELD, "right")
    g.check(moved > 50, "the field resumed after the escape", f"walked {moved:.0f}u")
    told, text = _wait_flag_and_text(g, TOLD_RAN, "YOU RAN")
    g.check(told and text, "the field narrated the escape: outcome 2 (init) -> 'LEDGER: YOU RAN'",
            f"flag {told}, text {text}")
    g.warp(NEUTRAL)
    v = _vecs(g)
    led2 = v.get(T)
    exp2 = None if after1 is None else [0, 2] + after1[2:]
    g.check(led2 == exp2, "an escape keeps the Init rows (fights 2) and runs no dying row", f"{led2} vs {exp2}")

    # -- NC6: the stale scene ----------------------------------------------------------------------
    g.warp(FIELD)
    f3 = _fight(g, STALE, "5-stale")
    g.check(f3["result"] in (1, 2) and not f3["stalled"], "the stale-scene fight ends in victory", str(f3))
    g.check(f3["bits"][WITNESS], "NC6: the stale scene's dying hook RAN (its witness flag 8911 landed)",
            str(f3["bits"]))
    moved = _back(g, FIELD, "left")
    g.check(moved > 50, "the field resumed after the stale fight", f"walked {moved:.0f}u")
    g.check(_quiet(g, 10), "NC6: nothing to narrate -- the stale scene wrote no outcome")
    g.warp(NEUTRAL)
    v = _vecs(g)
    g.check(v.get(T) == led2 and v.get(G) == [W12],
            "NC6: the stale scene's writes stayed behind the live gate: the ledger is unchanged, still 12 cells "
            "(cell 12 would have APPENDED) and never re-seeded", f"{v.get(T)} guard {v.get(G)}")
    g.warp(FIELD)
    final = _hud(g)
    g.shot("6-final")
    g.check(final is not None and final["T SIZE"] == N and final["FIGHTS"] == 2 and final["CHECK OK"] == 1,
            "30880 still reads the ledger the fights wrote", str(final))
    g.quit()
