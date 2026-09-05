"""Can the harness drive the battle HUD -- the CURSOR path, not the command entry point?

WHY THIS IS A SEPARATE PROOF. `battle_play.py` proves a battle can be PLAYED, but every turn it takes
goes through `act()`, which commits via `BattleHUD.SendNetCommand` and never presses a button. That
tests the battle logic and says nothing about the menu itself. The NGUI navigation hook
(`UnityXInput.Input.GetAxisRaw` -> `HarnessAgent.TryGetNavigationAxis`) was proven on the FIELD main
menu and on a dialogue choice; INPUT-COVERAGE.md records the battle command/target cursors as riding
the same site and "expected to follow, but not yet separately proven in-game". `battle_pick` and
`battle_act` exist for exactly that path and no scenario had ever called them -- an unproven verb
with a confident docstring is precisely the shape this arc keeps paying for.

WHAT EACH CHECK IS FOR. The claim is "an injected direction press moves the BATTLE cursor, and a
command confirmed through the HUD is executed". So the evidence is, in order: the cursor label
CHANGED after a press (the navigation hook reaches the battle HUD); `battle_pick` parked the cursor
on the command it was asked for BY THE ENGINE'S OWN `ButtonGroupState.ActiveButton`; confirming
opened the TARGET group (a second NGUI group, so the confirm was consumed by the HUD rather than
swallowed); and after confirming the target the enemy's HP FELL. "The press acked" proves nothing --
the analog-axis bug acked every press while the character stood still.

⚠ The fight is played out afterwards with `fight()` so the suite's recovery ladder is not asked to
climb out of a live battle for this member; which side won is reported, never required.

    py tools/play.py studies/test-harness/scenarios/battle_hud_check.py --field 30801
"""

FIELD = 30801
#: BSC_EF_R004 -- Goblin AND Fang, the same two-enemy encounter battle_play uses: a single HUD
#: Attack cannot end it, so the HP-fell check is about the command landing, not the fight ending.
SCENE = 306


def _enemy_hp(st) -> int:
    return sum(int(u.get("hp", 0)) for u in st.units(player=False) if u.get("alive"))


def _cursor(st) -> tuple[str, str]:
    c = st.battle_cursor
    return (c.get("group") or ""), (c.get("label") or "")


def run(g, field: int = FIELD):
    g.note("battle HUD: the cursor path")
    g.newgame()
    g.warp(field)
    g.wait_frames(60)
    g.start_battle(SCENE)

    # ---- a command menu is open, and the channel says which group/button --------------------
    try:
        st = g.wait_for(lambda s: _cursor(s)[0] == "Battle.Command" and bool(_cursor(s)[1]),
                        timeout=90.0, what="the battle command menu with a labelled cursor")
        group, first = _cursor(st)
        g.check(True, "the battle command cursor is open with a labelled button",
                f"group={group!r} label={first!r} turn.slot={st.turn_slot}")
    except Exception as err:
        g.check(False, "the battle command cursor is open with a labelled button", str(err))
        g.shot("hud-no-menu")
        return
    g.shot("hud-00-command-menu")

    # ---- an injected direction press moves the BATTLE cursor -------------------------------
    # The direct proof of the INPUT-COVERAGE claim. Asserted on the engine's published ActiveButton
    # label changing, which a press that was accepted but not routed to NGUI cannot produce.
    g.press("down", 4)
    try:
        moved = g.wait_for(lambda s: _cursor(s)[0] == "Battle.Command" and _cursor(s)[1] != first,
                           timeout=6.0, what="the battle cursor label to change after `down`")
        g.check(True, "a `down` press moves the battle command cursor (the NGUI hook reaches BattleHUD)",
                f"{first!r} -> {_cursor(moved)[1]!r}")
    except Exception as err:
        g.check(False, "a `down` press moves the battle command cursor (the NGUI hook reaches BattleHUD)",
                f"label stayed {first!r}: {err}")

    # ---- battle_pick parks the cursor on a NAMED command, verified against ActiveButton ----------
    # ⚠ The cursor is now BELOW Attack (the `down` above moved it), and the first live run proved
    # the command list is a two-column grid that does not wrap: a one-direction walk saw
    # `Steal -> Item -> Item...` and never Attack. battle_pick searches both ways and both columns.
    picked = False
    try:
        landed = g.battle_pick("Attack", confirm=False)
        now = _cursor(g.state)
        picked = g.check(now[1].strip().lower() == "attack" and now[0] == "Battle.Command",
                         "battle_pick parks the cursor on 'Attack' by the engine's own ActiveButton "
                         "(reached from BELOW it)",
                         f"returned {landed!r}; cursor now group={now[0]!r} label={now[1]!r}")
    except Exception as err:
        g.check(False, "battle_pick parks the cursor on 'Attack' by the engine's own ActiveButton "
                       "(reached from BELOW it)", str(err))

    # ---- confirming through the HUD opens the TARGET group, and the command is EXECUTED ----------
    # ⚠ THE GROUP MUST BE Battle.Target EXACTLY. Battle.Ability and Battle.Item are submenus, and
    # the first cut accepted "any group but the command list" -- which passed with the ITEM LIST
    # open (the screenshot showed Potion highlighted) and then confirmed a Potion instead of an
    # enemy. And nothing is confirmed at all unless the pick landed: confirming whatever happens
    # to be highlighted is not a test of Attack.
    what_target = "confirming Attack through the HUD opens the Battle.Target group"
    what_landed = "a command confirmed through the HUD cursor is EXECUTED (enemy HP fell)"
    before = _enemy_hp(g.state)
    if not picked:
        g.check(False, what_target, "not attempted: the cursor never reached Attack")
        g.check(False, what_landed, "not attempted: the cursor never reached Attack, so confirming "
                                    "would have committed whatever was highlighted")
    else:
        g.press("confirm", 4)
        on_target = False
        try:
            tgt = g.wait_for(lambda s: _cursor(s)[0] in (g.BATTLE_TARGET_GROUP,) + g.BATTLE_SUBMENU_GROUPS,
                             timeout=8.0, what="a cursor group to follow the Attack confirm")
            on_target = g.check(_cursor(tgt)[0] == g.BATTLE_TARGET_GROUP, what_target,
                                f"group={_cursor(tgt)[0]!r} label={_cursor(tgt)[1]!r}")
            g.shot("hud-01-target")
        except Exception as err:
            g.check(False, what_target, str(err))
        if on_target:
            g.press("confirm", 4)
            try:
                st = g.wait_for(lambda s: _enemy_hp(s) < before or s.battle_result != 0,
                                timeout=45.0, what="the enemy to take the damage ordered through the HUD")
                g.check(_enemy_hp(st) < before, what_landed,
                        f"enemy HP {before} -> {_enemy_hp(st)}; result={st.battle_result_name}")
            except Exception as err:
                g.check(False, what_landed, f"enemy HP still {before}: {err}")
        else:
            g.press("cancel", 4)             # back out of whatever submenu opened instead
            g.check(False, what_landed, "not attempted: the target cursor never opened")
    g.shot("hud-02-after-attack")

    # ---- play the rest out so the next member does not inherit a live battle -------------------
    try:
        g.fight(timeout=240.0)
        print(f"[hud] fight finished: {(g.last_fight or {}).get('name')} "
              f"in {(g.last_fight or {}).get('turns')} further turn(s)")
    except Exception as err:
        # Not a check: which way the dice went is not this scenario's claim, and the ladder can
        # recover from a battle. Say so loudly, though, because the recovery costs the suite time.
        print(f"[hud] NOTE: could not play the fight out ({err}); the suite's ladder will recover")
