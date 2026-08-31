"""Can the harness SEE a battle? The acceptance test for the s83 rev3 battle block.

Battles are a first-class pillar of this project -- custom enemies, AI, tuning, summons, a 13th
playable character -- and until now the state channel was 100% dark on them. `sys_mode`, `scene` and
`ui_state` carried a coarse "something battle-ish is happening" and nothing else: no HP, no ATB, no
unit list, no result. Every behavioural claim about a battle cost a human playtest.

WHAT THIS ASSERTS, AND WHY EACH ONE. Almost every value in `FF9Battle` is AMBIGUOUS or STALE rather
than absent, so the default failure mode here is a plausible wrong answer rather than a blank:

* `btl_result` is 0 DURING a battle and also BEFORE any battle has ever run, and it PERSISTS
  unchanged afterwards. So the start edge is `party.battle_no` (`epoch`), which is monotonic, and
  every wait is anchored to it.
* `IsBattleScene()` is true for the DIORAMA too, which runs under `isDebug` where the engine
  suppresses the auto-end -- a battle that can never finish. A result assertion there would be green
  having observed nothing, so `in_battle` excludes it.
* The ATB gauge advancing is the one signal that cannot be faked by a stale document: it proves the
  battle is not merely present but RUNNING.

    py tools/play.py studies/test-harness/scenarios/battle_check.py --field 30801

Battle scene 67 is `BSC_EF_R007` -- Goblin + Fang, Evil Forest -- an early-game encounter a New Game
party can actually fight (`py -m ff9mapkit encounters Goblin --monster`).
"""

FIELD = 30801
SCENE = 67


def run(g, field: int = FIELD):
    g.note("battle observability: the s83 rev3 block")
    st = g.state
    # >= 3, not == 3. This scenario proves the rev3 BLOCK and every later revision keeps it; an
    # equality check here goes red on rev4 for a block that is perfectly intact, which is a test
    # failing for a reason that has nothing to do with what it tests. rev2_proof learned this first.
    g.check((st.protocol or 0) >= 3, "the deployed engine speaks protocol 3 or later",
            f"published v={st.protocol}")

    g.newgame()
    g.warp(field)
    g.wait_frames(60)

    # ---- the block is dark on a field, and that is deliberate -------------------------------
    # Every mid-battle value the engine keeps is STALE rather than cleared, so publishing it here
    # would hand a scenario a complete, plausible, entirely historical battle.
    on_field = g.state
    g.check(not on_field.in_battle and not on_field.units(),
            "no battle is reported while standing on a field",
            f"battle={ {k: v for k, v in on_field.battle.items() if k != 'bonus'} }")
    epoch_before = on_field.battle_epoch

    # ---- boot a real battle ------------------------------------------------------------------
    st = g.start_battle(SCENE)
    g.shot("battle-00-start")
    g.check(st.in_battle, "a REAL battle is running (not the diorama)",
            f"active={st.battle.get('active')} debug={st.battle.get('debug')}")
    g.check(st.battle_epoch == epoch_before + 1,
            "the battle-start EDGE was observed on party.battle_no",
            f"epoch {epoch_before} -> {st.battle_epoch}")
    g.check(st.battle.get("scene") == SCENE, f"the battle scene is {SCENE}",
            f"scene={st.battle.get('scene')}")

    # ---- the unit list ------------------------------------------------------------------------
    units = st.units()
    party = st.units(player=True)
    foes = st.units(player=False)
    for u in units:
        print(f"[btl] {'PC ' if u['player'] else 'foe'} slot {u['slot']:>2} {u['name']!r:<20} "
              f"hp {u['hp']}/{u['hp_max']} (raw {u['hp_raw']}/{u['hp_max_raw']}) "
              f"mp {u['mp']}/{u['mp_max']} atb {u['atb']}/{u['atb_max']} "
              f"alive={u['alive']} can_act={u['can_act']}")
    g.check(bool(party) and bool(foes),
            "the unit list carries both the party and the enemies",
            f"{len(party)} party + {len(foes)} enemy of {len(units)} total")
    g.check(all(u["hp_max"] > 0 for u in units),
            "every unit reports a positive max HP",
            f"{[(u['name'], u['hp'], u['hp_max']) for u in units]}")
    # The slot is computed with a BOUNDED loop on purpose: the engine's own BattleUnit.GetIndex() is
    # `while (1 << index != Data.btl_id) ++index;` with no limit, so a btl_id of 0 would spin
    # forever inside the state publisher -- hanging the very game this is here to observe.
    g.check(all(u["slot"] >= 0 for u in units),
            "every unit's slot resolved (the bounded btl_id decode)",
            f"slots={[u['slot'] for u in units]}")
    # The same rendered-vs-source split the dialogue needed, found again here: an enemy came back as
    # "[STRT=27,1]Fang[ENDN]" on the first live run. The HUD's UILabel eats those tags, so a scenario
    # matching the raw string would be matching something nobody ever sees.
    tagged = [u["name"] for u in units if "[" in (u.get("name") or "")]
    g.check(not tagged, "unit names are published RENDERED, not as tagged source",
            f"tagged: {tagged}" if tagged else
            f"clean: {[u['name'] for u in units]} (raw: {[u.get('name_raw') for u in units]})")

    # ---- it is RUNNING, not merely present ----------------------------------------------------
    # The ATB gauge advancing is the assertion a stale document cannot satisfy.
    def atb_total(state) -> int:
        return sum(max(0, u.get("atb") or 0) for u in state.units())

    start_atb = atb_total(g.state)
    try:
        moved = g.wait_for(lambda s: atb_total(s) > start_atb, timeout=25.0,
                           what="the ATB gauges to advance (proof the battle is RUNNING)")
        g.check(True, "the ATB gauges advance -- the battle is live, not a photograph",
                f"total ATB {start_atb} -> {atb_total(moved)}")
    except Exception as err:
        g.check(False, "the ATB gauges advance -- the battle is live, not a photograph", str(err))

    # ---- the command cursor -------------------------------------------------------------------
    # BattleHUD does not drive a separate cursor: it rides the same NGUI focus, and what
    # OnKeyConfirm consumes is ButtonGroupState.ActiveButton -- NOT UICamera.selectedObject, which
    # is the accessor a diagnostic reads. Publishing the fallback was this arc's own law still live
    # in the code, so this asserts on the group the engine actually decides by.
    try:
        turn = g.wait_for(lambda s: (s.battle_cursor.get("group") or "").startswith("Battle."),
                          timeout=40.0, what="a battle command menu to open")
        cursor = turn.battle_cursor
        g.check(True, "the battle command cursor is published by GROUP and BUTTON",
                f"group={cursor.get('group')!r} button={cursor.get('button')!r} "
                f"label={cursor.get('label')!r}")
        g.shot("battle-01-command")
    except Exception as err:
        g.check(False, "the battle command cursor is published by GROUP and BUTTON", str(err))

    # ---- watch a fight actually happen ---------------------------------------------------------
    # ⚠ THIS SCENARIO ASSERTS OBSERVABILITY, NOT CONTROL, and the distinction is deliberate rather
    # than a retreat: it is the half that must keep working whether or not anyone takes a turn.
    # PLAYING a battle is a separate capability, proven separately in scenarios/battle_play.py and
    # scenarios/flee_check.py (s83 rev4).
    #
    # ⚠ THIS COMMENT USED TO NAME TWO OBSTACLES AND ONE OF THEM WAS WRONG. It said fleeing could not
    # work while a command menu was open, because `btl_sys.CheckEscape` needs
    # `BattleHUD.IsNativeEnableAtb()` and WAIT ATB mode freezes the gauge while a menu is up. Read
    # again: in WAIT mode that method returns
    # `CurrentPlayerIndex == -1 || ActiveGroup == "Battle.Command" || ActiveGroup == ""`, so the
    # TOP-LEVEL command list -- which is precisely where the trace found the cursor -- leaves it
    # ENABLED. Only a SUBMENU freezes it. flee_check.py now escapes in-game with `turn.slot 0` and
    # the cursor on `Battle.Command`, which settles it by measurement.
    # The real cause was the DRIVER: it re-issued its hold every 0.8s against a 1.0-second threshold
    # of UNBROKEN holding, and re-issuing restarted `_downFrame` at `frameCount + 1` -- dropping the
    # button for the one frame each request landed on, and resetting `_runCounter` every time. The
    # roll was never reached at all. The other obstacle was real: `SendNetCommand` opens with
    # `if (playerIndex == CurrentPlayerIndex) return false;` and refuses the local slot, which the
    # agent now dissolves by calling the public `SetIdle()` first.
    #
    # What a fight DOES give this scenario for free is the strongest observability assertion
    # available: the channel tracking live combat state as it changes. HP moving is something no
    # stale document and no half-wired reader can produce.
    st = g.state
    g.check(st.can_escape is not None,
            "the channel says whether this scene permits running at all",
            f"scene_info={st.battle.get('scene_info')}")
    print(f"[btl] scene {st.battle.get('scene')} runaway={st.can_escape} "
          f"message={st.battle_message!r}")

    # Internal consistency of the published roster. This is pure observability -- it needs nobody to
    # take a turn -- and it can fail: a mis-wired reader would cross the logical and raw HP pairs, or
    # report a unit at 0 HP as dead when the engine's own liveness test is the Death STATUS bit.
    bad = []
    for u in st.units():
        if not (0 <= u["hp"] <= u["hp_max"]):
            bad.append(f"{u['name']} hp {u['hp']}/{u['hp_max']}")
        if not (0 <= u["hp_raw"] <= u["hp_max_raw"]):
            bad.append(f"{u['name']} raw hp {u['hp_raw']}/{u['hp_max_raw']}")
        if u["atb_max"] <= 0:
            bad.append(f"{u['name']} atb_max {u['atb_max']}")
    g.check(not bad, "every unit's published numbers are internally consistent",
            "; ".join(bad) if bad else
            f"{len(st.units())} unit(s): " +
            ", ".join(f"{u['name']} {u['hp']}/{u['hp_max']} atb/{u['atb_max']}" for u in st.units()))

    g.shot("battle-02-after")
    end = g.state
    g.check(end.battle_epoch == epoch_before + 1,
            "and every reading still belongs to the battle we started",
            f"epoch still {end.battle_epoch}, result={end.battle_result_name}")
    print(f"[btl] result so far: {end.battle_result_name}  bonus={end.battle.get('bonus')}")
    print("[btl] NOTE: driving a battle to a RESULT is a separate, UNPROVEN capability -- see "
          "studies/test-harness/PLAN.md. This scenario asserts what the channel can SEE.")
