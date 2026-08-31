"""Can the harness PLAY a battle? The acceptance test for the s83 rev4 play verbs.

rev 3 made a battle VISIBLE -- roster, HP, ATB, statuses, cursor, rewards, result. It could not take
a single turn. Two measured obstacles, both dissolved here:

* ``SendNetCommand`` opens with ``if (playerIndex == CurrentPlayerIndex) return false;`` because it
  exists to replay a REMOTE co-op player's command and must lose a race against the menu that slot
  has open locally. In a solo fight that is always the one slot you want. The agent now calls the
  public ``SetIdle()`` first -- the UI's own post-commit teardown, which closes the panels and sets
  ``CurrentPlayerIndex = -1`` -- so the slot is free before the command is offered.
* A re-issued ``hold`` dropped the button for exactly one frame (``Schedule`` restarted
  ``_downFrame`` at ``frameCount + 1``). ``BattleHUD._runCounter`` counts UNBROKEN seconds and gates
  the escape roll at 1.0, so a flee re-issued every 0.8s NEVER ROLLED ONCE -- while
  ``btl_escape_key``, set before that counter is even tested, kept the character running on screen
  the whole time. That is what the owner saw. The agent now extends a live hold instead.

WHAT EACH CHECK IS FOR. The claim under test is "a command the harness issued was actually
EXECUTED", and the only honest evidence for that is the game state changing: an enemy's HP falling,
the fight reaching a result, the rewards being paid. "The step acked" is what both defects above
could already produce, so nothing here asserts on an ack.

⚠ THE OUTCOME OF THE FIGHT IS NOT THE CLAIM. A level-1 party can lose to scene 67, and a scenario
that required a win would be asserting on the enemy's dice. Reaching a RESULT is the capability;
which result it was is reported, not required.

    py tools/play.py studies/test-harness/scenarios/battle_play.py --field 30801

Battle scene 67 is `BSC_EF_R007` -- Goblin + Fang, Evil Forest -- an early-game encounter a New Game
party can actually fight (`py -m ff9mapkit encounters Goblin --monster`).
"""

FIELD = 30801
#: BSC_EF_R004 -- Goblin AND Fang. Deliberately not scene 67, which fielded a lone 33 HP Goblin the
#: first time this ran: one Attack killed it, fight() reported a clean victory having taken ZERO
#: turns, and the multi-turn loop went untested behind a green report. Two enemies cannot be cleared
#: in one command, so the loop has to run for this to pass.
SCENE = 306


def _enemy_hp(st):
    """Total HP across every enemy still standing -- the number a working Attack must move."""
    return sum(int(u.get("hp", 0)) for u in st.units(player=False) if u.get("alive"))


def run(g, field: int = FIELD):
    g.note("battle play: the s83 rev4 verbs")
    st = g.state
    g.check((st.protocol or 0) >= 4, "the deployed engine speaks protocol 4 or later",
            f"published v={st.protocol} (3 = the pre-rev4 DLL is still deployed; a rebuild needs a "
            f"full RELAUNCH, not ~ Reload field)")

    g.newgame()
    g.warp(field)
    g.wait_frames(60)
    g.start_battle(SCENE)
    g.shot("play-00-battle-up")

    # ---- whose turn, and what can they do --------------------------------------------------
    # `turn.slot` is BattleHUD.CurrentPlayerIndex, which the HUD sets in SwitchPlayer for the first
    # ready slot that has not answered. It is the game's own "your move", not a guess assembled
    # from ATB values -- and until rev4 the channel could not see it at all.
    slot = g.wait_turn(timeout=90.0)
    g.check(slot >= 0, "the game asks a party member for a command, and the channel can see who",
            f"turn.slot={slot}")

    menu = g.menus(slot)
    st = g.state
    offered = [c.get("name") for c in menu.get("commands", []) if c.get("offered")]
    g.check(bool(offered), "the character's command menu is readable BY NAME",
            f"slot {slot} offers {offered}")
    # The names come from FF9TextTool via the character's preset and trance state, so this also
    # proves the resolution ran against THIS character rather than against a table in the driver.
    attack = st.command("Attack")
    g.check(attack is not None and attack.get("sub", 0) > 0,
            "Attack resolves to the exact arguments a command needs",
            f"{attack!r}")
    print(f"[play] slot {slot} commands={offered}")
    print(f"[play]   abilities={[a.get('name') for a in menu.get('abilities', [])]}")
    print(f"[play]   items={[i.get('name') for i in menu.get('items', [])][:6]}")

    # ---- ONE turn, and the proof that it happened ------------------------------------------
    before = _enemy_hp(g.state)
    roster = [(u.get("name"), u.get("hp"), u.get("hp_max")) for u in g.state.units()]
    print(f"[play] roster: {roster}")
    rec = g.act("Attack", slot=slot)
    print(f"[play] acted: {rec}")

    # ⚠ THE ONLY EVIDENCE THAT COUNTS. A refused command acks exactly like an accepted one -- that
    # is precisely how the pre-rev4 harness looked like it was fighting while SendNetCommand was
    # returning false on every call. Damage landing is the outcome; everything else is a proxy.
    try:
        st = g.wait_for(lambda s: _enemy_hp(s) < before or s.battle_result != 0,
                        timeout=45.0, what="the enemy to take the damage we ordered")
        landed = True
    except Exception as err:
        st = g.state
        landed = False
        print(f"[play] no damage observed: {err}")
    g.check(landed, "a command the harness issued is actually EXECUTED by the engine",
            f"enemy HP {before} -> {_enemy_hp(st)}; result={st.battle_result_name}")
    g.shot("play-01-after-one-turn")

    # ---- play it out -----------------------------------------------------------------------
    result = None
    try:
        result = g.fight(timeout=240.0, finish=False)
        reached = True
        detail = f"result={g.state.battle_result_name}"
    except Exception as err:
        reached = False
        detail = str(err)[:200]
    g.check(reached, "the harness plays the battle through to a RESULT", detail)
    # ⚠ AND THAT THE LOOP ACTUALLY RAN. A victory says nothing about how many turns were taken, and
    # the first live run of this scenario proved it: the single Attack above had already killed the
    # only enemy, so fight() returned "victory" in ZERO turns and the multi-turn path was untested
    # behind a completely green report. That is the gate-is-not-an-oracle shape, in this file.
    turns = (g.last_fight or {}).get("turns", 0)
    g.check(turns >= 1, "and the turn loop is what got it there, not a fight already over",
            f"fight() took {turns} turn(s) after the one issued by hand")
    st = g.state
    print(f"[play] {st.battle_result_name}: exp={st.battle.get('bonus', {}).get('exp')} "
          f"gil={st.battle.get('bonus', {}).get('gil')} ap={st.battle.get('bonus', {}).get('ap')}")

    # The rewards are the engine's own record that a fight finished the way it says. ⚠ Only on a
    # WIN: a defeat pays nothing, so requiring them unconditionally would be asserting on the dice.
    if result == 1:
        bonus = st.battle.get("bonus", {})
        g.check(int(bonus.get("exp", 0)) > 0 or int(bonus.get("gil", 0)) > 0,
                "a won battle pays out, which is the engine's own record that it finished",
                f"bonus={bonus}")
    else:
        print(f"[play] not a victory ({st.battle_result_name}) -- the rewards check is skipped "
              f"rather than asserted against a party that lost. Reaching the result is the claim.")

    where = g.leave_battle()
    g.check(where not in ("BattleHUD",), "and the harness gets back out of the battle screen",
            f"ui_state={where} field={g.state.field_id}")
    g.shot("play-02-after-the-fight")
