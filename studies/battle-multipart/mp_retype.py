"""THE MULTIPART RETYPE CHECK -- does `[[scene.enemy]] slot = 0, type = 0` leave a multipart boss whole, in-game?

    py tools/play.py studies/battle-multipart/mp_retype.py --label mp-retype

Benches (scratch, FF9CustomMap; bench/scene_*/battle.toml carry the lines that regenerate them):
  30910 MPBOSS   GT_R004 (Sand Golem MASTER + its Core SLAVE part; Core HP 100, Golem speed/level 1) built by the kit at 9f7e1c0b:
                 slot 0 = (type 0, SB2_PUT flags 3), slot 1 = (1, 3)
  30911 MPBOSSX  the SAME battle.toml, its deployed raw16 replaced by the PRE-FIX kit's output for it:
                 slot 0 = (0, 1). One byte differs (offset 17; make_control.py). The negative control -- run LAST: the
                 engine is expected to throw in battle init (btl_init.OrganizeEnemyData, a null master).

Engine exceptions land in Memoria.log as `|E|` lines WITH their stack traces (`|E|   at ...`). Unity's
x64/FF9_Data/output_log.txt does NOT get them on this build -- the first run of this scenario read that file,
so its exception checks could not fail (the control's NRE was in Memoria.log all along). Every log check is
scoped to lines written during ONE battle and to traces through the battle code; the control, run in the same
launch, is what proves the parser can see the failure.
"""
from __future__ import annotations

from pathlib import Path

FIELD = 30801                                        # the standard harness bench (TEST30801, FF9CustomMap)
FIX, CTL = 30910, 30911
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
SCENES = GAME / "FF9CustomMap" / "StreamingAssets" / "assets" / "resources" / "BattleMap" / "BattleScene"
GOLEM, CORE = 4, 5                                   # unit slots: enemies start at 4 (btl_id 16 << pattern slot)
BATTLE_FRAMES = ("OrganizeEnemyData", "GetMasterEnemyBtlPtr", "btl_init", "btlseq", "btl_mot", "SBattleCalculator",
                 "BattleHUD", "btl_cmd", "battle.Battle")


def _puts(name: str) -> list:
    raw = (SCENES / f"EVT_BATTLE_{name}" / "dbfile0000.raw16.bytes").read_bytes()
    return [(raw[16 + 12 * s], raw[17 + 12 * s]) for s in range(2)]


def _mlog(g) -> list:
    p = g.engine_log()                               # the newest Memoria.log = this run's
    try:
        return p.read_text(encoding="utf-8", errors="replace").splitlines() if p else []
    except OSError:
        return []


def _exceptions(lines: list) -> list:
    """[(header, [trace lines])] for every `|E|` exception in ``lines``."""
    out = []
    for i, line in enumerate(lines):
        if "|E|" in line and "Exception" in line and "|E|   at " not in line:
            trace = []
            for t in lines[i + 1:i + 25]:
                if "|E|   at " not in t:
                    break
                trace.append(t.split("|E|", 1)[1].strip())
            out.append((line.split("|E|", 1)[1].strip(), trace))
    return out


def _battle_exceptions(g, mark: int) -> tuple:
    """(every exception since ``mark``, those whose trace runs through the battle code)."""
    g.wait_frames(30)                                # let the log catch up
    exc = _exceptions(_mlog(g)[mark:])
    hits = [(h, t) for h, t in exc if any(f in " ".join(t) for f in BATTLE_FRAMES)]
    return exc, hits


def _show(exc: list) -> str:
    return "; ".join(f"{h} @ {t[0] if t else '?'}" for h, t in exc[:4]) or "none"


def _foes(st) -> list:
    return sorted((u["slot"], u["name"], u.get("hp_raw"), u.get("hp_max_raw"), u.get("alive"), u.get("targetable"))
                  for u in st.units(player=False))


def run(g) -> None:
    g.note("multipart retype: GT_R004 slot 0 type 0")
    g.check(_puts("MPBOSS") == [(0, 3), (1, 3)], "deployed 30910 MPBOSS: master (0, 3) + slave (1, 3) -- the fix's bytes",
            str(_puts("MPBOSS")))
    g.check(_puts("MPBOSSX") == [(0, 1), (1, 3)], "deployed 30911 MPBOSSX: master stripped to (0, 1) -- the pre-fix bytes",
            str(_puts("MPBOSSX")))
    g.newgame()
    g.warp(FIELD)
    g.wait_frames(60)

    # -- the fix ------------------------------------------------------------------------------------------
    mark = len(_mlog(g))
    st = g.start_battle(FIX, group=0)
    g.shot("1-fix-start")
    foes = _foes(st)
    print(f"[mp] fix roster: {foes}")
    g.check(st.battle.get("scene") == FIX, "the fix: battle 30910 is running", f"scene={st.battle.get('scene')}")
    g.check([f[0] for f in foes] == [GOLEM, CORE] and "Golem" in foes[0][1] and "Core" in foes[1][1],
            "the fix: the roster is the Sand Golem (slot 4) and its Core (slot 5)", str(foes))
    try:
        slot = g.wait_turn(timeout=60)
        g.check(True, "the fix: battle init completed -- a party member is asked for a command", f"slot {slot}")
    except Exception as err:                         # noqa: BLE001 -- reported as a check
        g.check(False, "the fix: battle init completed -- a party member is asked for a command", str(err))
    core_hp: list = []

    def at_core(s, _slot):
        core = [u for u in s.units(player=False) if u["slot"] == CORE]
        if core and core[0].get("alive"):
            core_hp.append(core[0].get("hp_raw"))
            return {"command": "Attack", "target": CORE}
        return None                                  # the Core is down: wait for the Golem's AI to fold

    result = None
    try:
        result = g.fight(policy=at_core, finish=False, timeout=300, max_turns=40)
    except Exception as err:                         # noqa: BLE001
        print(f"[mp] fix fight: {err}")
    end = g.state
    g.shot("2-fix-over")
    print(f"[mp] fix: result {result} ({end.battle_result_name}), Core HP seen {core_hp}, "
          f"turns {(g.last_fight or {}).get('turns')}, roster {_foes(end)}")
    g.check(result in (1, 2), "the fix: VICTORY -- killing the slave Core ended the fight through its master",
            f"result {result} ({end.battle_result_name})")
    g.check(len(core_hp) >= 2 and core_hp[-1] < core_hp[0] and all(a >= b for a, b in zip(core_hp, core_hp[1:])),
            "the fix: attack after attack on the SLAVE landed (each hit routes to the master's object) and wore it down",
            f"Core HP before each attack: {core_hp}")
    exc, hits = _battle_exceptions(g, mark)
    g.check(not hits, "the fix: no exception traced through the battle code during the fight",
            f"battle-code: {_show(hits)} | all new: {_show(exc)}")
    g.leave_battle()
    if result in (1, 2):
        back = g.wait_for(lambda s: s.ui_state == "FieldHUD" and s.field_id == FIELD and not s.fading, timeout=90,
                          what=f"the return to {FIELD}")
        g.check(back.field_id == FIELD, "the fix: the party returned to the field", f"field {back.field_id}")
    else:                                            # a defeat ends on the title: start over so the control runs
        g.newgame()
        g.warp(FIELD)
        g.wait_frames(60)

    # -- the negative control: the pre-fix bytes ------------------------------------------------------------
    mark = len(_mlog(g))
    up, asked = False, False
    try:
        g.start_battle(CTL, group=0, timeout=60)
        up = True
    except Exception as err:                         # noqa: BLE001
        print(f"[mp] control start: {err}")
    try:
        g.shot("3-ctl-start")
    except Exception as err:                         # noqa: BLE001
        print(f"[mp] control shot: {err}")
    if up:
        print(f"[mp] control roster: {_foes(g.state)}")
        try:
            g.wait_turn(timeout=45)
            asked = True
        except Exception as err:                     # noqa: BLE001
            print(f"[mp] control turn: {err}")
    exc, hits = _battle_exceptions(g, mark)
    org = [(h, t) for h, t in hits if "NullReferenceException" in h and any("OrganizeEnemyData" in x for x in t)]
    print(f"[mp] control exceptions: {_show(exc)}")
    g.check(bool(org), "CONTROL: the pre-fix bytes throw a NullReferenceException in btl_init.OrganizeEnemyData "
            "(the slave's master lookup came back null)", f"battle-code: {_show(hits)}")
    g.check(not asked, "CONTROL: the pre-fix battle never reached a command prompt",
            f"battle up={up}, asked={asked}")
    g.quit()
