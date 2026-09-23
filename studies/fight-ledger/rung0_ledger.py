"""RUNG 0 of board entry #4 -- can an enemy's battle .eb write a field's PERSISTENT ledger?

One harness launch. The falsifier the board calls cheap move #3 ("the battle-side lvalue probe"),
plus the hook questions the design has to settle before any kit surface is minted:

    py tools/play.py studies/fight-ledger/rung0_ledger.py --label fl-rung0

Benches (studies/fight-ledger/bench/): field 30870 LEDGER0 declares the persistent table
fight_ledger0 (id 6004870, guard 7004870, 16 zero cells) and carries a tag-10 Main_Reinit;
battle scenes 30871 (LEDGER_A: one Goblin, HP 90, NO die_atk) and 30872 (LEDGER_B: the same with
die_atk) splice writes into the Goblin's AI (entry 2): tag 0 Init, tag 7 post-hit, and an added
tag 9 Dying. The cell map is in each battle.toml header.

    New Game -> 30870: the table seeds (16 zeros, check word) -- the NEGATIVE control
    battle A: Attack the Goblin to death; flag 8900 set before the field returns; walk (tag 10 ran)
    battle B: the same; flag 8901 (the tag-9 hook) set before the field returns; walk;
              the field's OWN ticker then raises seen_b (14868) off cell 8 -- the catching field
              reads the fight in the same session
    30863 (declares no table): its entry autosave = the ledger exactly as the fights left it
    30870: its entry autosave (before Main_Init) + its HUD (after the guard) -- the declaring
           field's fresh entry KEEPS the battle-written cells
    30863 again: the autosave after that Main_Init still holds them

The player's own save is never touched: the s83 agent sandboxes saves while armed.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "studies" / "persistent-tables"))
sys.path.insert(0, str(REPO / "ff9mapkit"))
import rung0_persist as R0  # noqa: E402  (the calibrated helpers: _hud, _sandbox)
from ff9mapkit import save as _save  # noqa: E402
from ff9mapkit.content import behavior as B  # noqa: E402

FIELD, NEUTRAL = 30870, 30863
SCENE_A, SCENE_B = 30871, 30872
T, G = 6004870, 7004870
N = 16
W = B.persist_check_word("fight_ledger0", N)
BIT_A, BIT_B = 8900, 8901                  # set by the battle hooks (explicit, above FIRST_SAFE_FLAG)
SEEN_B = 14868                             # field 30870's public flag `seen_b` (printed by its build)
GOBLIN = 4                                 # the one enemy's slot (btl_id 16 << 0)


_sent = R0.sentinel                        # the HUD's open-pass placeholder for a `digits` width


# label -> placeholder, from ledger0.field.toml's `digits = [2, 1, 5, 2, 1, 5, 1, 3]`
ROWS = {"T SIZE": _sent(2), "CHECK OK": _sent(1), "A SCENE": _sent(5), "A HITS": _sent(2),
        "A TAG9": _sent(1), "B SCENE": _sent(5), "B TAG9": _sent(1), "B KILLER HP": _sent(3)}


def _hud(g, **kw):
    return R0._hud(g, ROWS, want_header="LEDGER 0 30870", **kw)


def _vecs(g) -> dict:
    return _save.read_extra_vectors(R0._sandbox(g) / "SavedData_ww_Memoria_Autosave.dat") or {}


def _preflight(g) -> None:
    g.check(W == 20525896, "the ledger's check word is the value the bench's HUD literal carries", str(W))
    g.check(str(W) in (HERE / "bench" / "ledger0.field.toml").read_text(encoding="utf-8"),
            "ledger0.field.toml's CHECK OK row compares against that word")


def _kill(g, label: str) -> dict:
    """Attack the Goblin until the battle ends. Returns what was seen before the field came back."""
    def policy(s, _slot):
        foes = [u for u in s.units(player=False) if u.get("alive") and u.get("targetable")]
        return {"command": "Attack", "target": foes[0]["slot"]} if foes else None
    out = {"result": None, "turns": None, "stalled": False}
    try:
        out["result"] = g.fight(policy=policy, finish=False, timeout=240, max_turns=40)
        out["turns"] = (g.last_fight or {}).get("turns")
    except Exception as err:                       # noqa: BLE001 - a stalled death is a RESULT here
        out["stalled"] = True
        print(f"[fl-rung0] {label}: the fight did not end ({err}); fleeing")
        g.shot(f"{label}-stalled")
        try:
            g.flee(timeout=90)
        except Exception as err2:                  # noqa: BLE001
            print(f"[fl-rung0] {label}: flee failed too: {err2}")
    st = g.state
    out["ui"] = st.ui_state
    out["bits"] = {BIT_A: st.flag(BIT_A), BIT_B: st.flag(BIT_B)}
    return out


def _back_and_walk(g, label: str, direction: str) -> float:
    g.leave_battle()
    back = g.wait_for(lambda s: s.ui_state == "FieldHUD" and s.field_id == FIELD and not s.fading,
                      timeout=90, what=f"the return to {FIELD} after {label}")
    x0, z0 = back.player_x, back.player_z
    g.wait_frames(20)
    g.walk(direction, 30)
    st = g.state
    return ((st.player_x - x0) ** 2 + (st.player_z - z0) ** 2) ** 0.5


def run(g) -> None:
    _preflight(g)
    sandbox = R0._sandbox(g)
    parked = g.run_dir / "sandbox-before"
    for p in sorted(sandbox.glob("SavedData_ww*.dat")):
        parked.mkdir(parents=True, exist_ok=True)
        shutil.move(str(p), str(parked / p.name))
    g.note("fight-ledger rung 0")
    g.newgame()
    g.watch(BIT_A, BIT_B, SEEN_B)

    # -- the seed: New Game, first entry --------------------------------------------------------
    g.warp(FIELD)
    seed = _hud(g)
    g.shot("1-field-seeded")
    g.check(seed == {"T SIZE": N, "CHECK OK": 1, "A SCENE": 0, "A HITS": 0, "A TAG9": 0, "B SCENE": 0,
                     "B TAG9": 0, "B KILLER HP": 0},
            "NEGATIVE CONTROL: the first entry seeded 16 zero cells under the check word", str(seed))
    g.check(not g.state.flag(BIT_A) and not g.state.flag(BIT_B) and not g.state.flag(SEEN_B),
            "no hook bit and no seen_b before any fight")

    # -- battle A: no die_atk -------------------------------------------------------------------
    st = g.start_battle(SCENE_A, group=0)
    foes = st.units(player=False)
    zid = st.units(player=True)
    g.check(st.battle.get("scene") == SCENE_A and len(foes) == 1 and foes[0].get("hp_max_raw") == 90,
            "battle A is the minted scene: one enemy, max HP 90 (the bench's raw16, not the donor's 33)",
            str([(u["slot"], u.get("name"), u.get("hp_raw"), u.get("hp_max_raw")) for u in st.units()]))
    g.shot("2-battle-a")
    a = _kill(g, "A")
    g.shot("3-battle-a-over")
    g.check(a["result"] in (1, 2) and not a["stalled"], "battle A ended in victory", str(a))
    g.check(a["bits"][BIT_A], "battle A's tag-7 death branch set flag 8900 before the field returned",
            str(a))
    g.check(not a["bits"][BIT_B], "...and battle B's bit is still clear")
    moved = _back_and_walk(g, "battle A", "left")
    g.check(moved > 50, "the field resumed after battle A: Main_Reinit ran and returned",
            f"walked {moved:.0f}u")
    g.wait_frames(60)
    g.check(not g.state.flag(SEEN_B), "the in-field reader stays quiet after A (cell 8 is still 0)")

    # -- battle B: die_atk ----------------------------------------------------------------------
    st = g.start_battle(SCENE_B, group=0)
    foes = st.units(player=False)
    zid = [u for u in st.units(player=True) if u.get("slot") == 0]
    killer_hp = zid[0].get("hp_max_raw") if zid else None
    g.check(st.battle.get("scene") == SCENE_B and len(foes) == 1 and foes[0].get("hp_max_raw") == 90,
            "battle B is the minted die_atk scene", str([(u["slot"], u.get("name"), u.get("hp_max_raw"))
                                                          for u in st.units()]))
    g.shot("4-battle-b")
    b = _kill(g, "B")
    g.shot("5-battle-b-over")
    g.check(b["result"] in (1, 2) and not b["stalled"],
            "battle B ended in victory -- die_atk on a Goblin never authored for it did not stall",
            str(b))
    g.check(b["bits"][BIT_B], "battle B's TAG-9 (Dying) body ran: flag 8901 set before the field returned",
            str(b))
    moved = _back_and_walk(g, "battle B", "right")
    g.check(moved > 50, "the field resumed after battle B", f"walked {moved:.0f}u")
    try:
        g.wait_for(lambda s: s.flag(SEEN_B), timeout=15, what="seen_b")
        seen = True
    except Exception:                          # noqa: BLE001
        seen = False
    g.check(seen, "THE CATCHING FIELD READ THE FIGHT: its own ticker saw cell 8 and raised seen_b")

    # -- the ledger as the fights left it -------------------------------------------------------
    g.warp(NEUTRAL)
    g.wait_frames(30)
    v1 = _vecs(g)
    led = v1.get(T)
    print(f"[fl-rung0] ledger after the fights: {led}  guard {v1.get(G)}  "
          f"A={a} B={b} killer max HP {killer_hp}")
    g.check(led is not None and len(led) == N and v1.get(G) == [W],
            "the ledger is still 16 cells under its check word: nothing appended, nothing re-seeded",
            f"{led} guard {v1.get(G)}")
    if led is not None and len(led) == N:
        g.check(led[0] == SCENE_A and led[1] == FIELD,
                "BATTLE-SIDE WRITE: A's Init wrote its own scene id and the field it came from",
                str(led[:2]))
        g.check(led[2] >= 2 and (a["turns"] is None or led[2] <= a["turns"]),
                "A's tag 7 ran once per hit", f"hits {led[2]}, attacks issued {a['turns']}")
        g.check(led[3] != 0 and led[4] == 90,
                "A's tag 7 ran on the lethal hit too (no die_atk): it recorded the killing ability "
                "and its own max HP through B_SYSLIST[1] B_MEMBER(35) B_PICK", str(led[3:5]))
        g.check(led[5] == 0, "NEGATIVE CONTROL: without die_atk, tag 9 never ran", str(led[5]))
        g.check(led[6] == SCENE_B, "B's Init wrote its scene id", str(led[6]))
        g.check(led[8] == 1, "B's tag 9 (Dying) ran on the killing blow", str(led[8]))
        g.check(led[9] == 1, "B_SYSLIST[0] in tag 9 is the killer's battle id (Zidane, slot 0 = 1)",
                str(led[9]))
        g.check(led[10] == 1 and led[11] == led[3],
                "B_SYSVAR[28]/[29] in tag 9 are the killing command (Attack) and the same ability id "
                "A recorded", str(led[10:12]))
        g.check(led[12] == 0, "own cur.hp inside tag 9 reads 0", str(led[12]))
        g.check(killer_hp is not None and led[13] == killer_hp,
                "B_SYSLIST[0] B_MEMBER(35) B_PICK in tag 9 is the killer's max HP",
                f"{led[13]} vs published {killer_hp}")
        g.check(led[14] == 1, "the dying enemy is still in the enemy list inside tag 9 (count 1 = last)",
                str(led[14]))
        g.check(led[15] == 0 and (b["turns"] is None or led[7] <= b["turns"] - 1),
                "only ONE hook per kill: tag 9 took level 0, the lethal hit's tag-7 request was refused",
                f"tag-7 bodies at 0 HP: {led[15]}, tag-7 hits {led[7]}, attacks issued {b['turns']}")

    # -- the declaring field's fresh entry keeps it -------------------------------------------
    g.warp(FIELD)
    g.wait_frames(10)
    v2 = _vecs(g)
    g.check(v2.get(T) == led and v2.get(G) == [W],
            "30870's entry autosave (before its Main_Init) holds the same ledger", str(v2.get(T)))
    kept = _hud(g)
    g.shot("6-field-reentered")
    want = None if led is None or len(led) != N else {
        "T SIZE": N, "CHECK OK": 1, "A SCENE": led[0], "A HITS": led[2], "A TAG9": led[5],
        "B SCENE": led[6], "B TAG9": led[8], "B KILLER HP": led[13]}
    g.check(want is not None and kept == want,
            "THE GUARD KEPT IT: the declaring field's fresh Main_Init did not re-seed the battle-written "
            "ledger", f"{kept} vs {want}")
    g.warp(NEUTRAL)
    g.wait_frames(30)
    v3 = _vecs(g)
    g.check(v3.get(T) == led and v3.get(G) == [W],
            "the autosave taken after that Main_Init still holds the fights' ledger", str(v3.get(T)))
    g.quit()
