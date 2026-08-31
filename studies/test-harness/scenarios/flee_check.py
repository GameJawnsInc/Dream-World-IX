"""Does the escape actually ROLL -- and was the recorded reason it did not the RIGHT one?

WHY THIS EXISTS AS ITS OWN SCENARIO. Until s83 rev 4 the harness could not run away from a fight,
and the cause was written up twice before it was measured:

1. "The scene forbids running." FALSE -- scene 67's `btl_scene.Info.Runaway` is true, checked below.
2. "A command menu freezes the ATB that `CheckEscape` requires." ALSO FALSE, and this scenario is
   what settles it. `IsNativeEnableAtb()` in WAIT mode returns
   `CurrentPlayerIndex == -1 || ActiveGroup == "Battle.Command" || ActiveGroup == ""`, so the
   TOP-LEVEL command list -- which is exactly where the trace found the cursor -- leaves the gauge
   ENABLED. Only a submenu (target / ability / item panel) freezes it. The gate was open the whole
   time.

The real cause was the driver re-issuing its hold every 0.8s against a threshold of 1.0 UNBROKEN
seconds, while `HarnessAgent.Schedule` restarted `_downFrame` at `frameCount + 1` and so dropped the
button for the frame each re-issue landed on. `BattleHUD._runCounter` reset in that hole every time,
`btl_sys.CheckEscape(true)` was therefore never reached, and `btl_escape_key` -- set BEFORE the
counter is even tested -- kept Zidane running on screen throughout. Owner-observed: "the flee
animation for a couple of seconds but he didn't actually leave."

So this holds ONCE, continuously, and records what was on screen when the roll landed. The rate is
`200 / avgEnemyLevel * avgPlayerLevel / 16` percent per roll, integer division throughout
(BattleCalculator.cs:358) -- single digits -- which is why it is willing to wait.

    py tools/play.py studies/test-harness/scenarios/flee_check.py --field 30801
"""

FIELD = 30801
SCENE = 67


def run(g, field: int = FIELD):
    g.note("battle play: the escape rolls")
    g.newgame()
    g.warp(field)
    g.wait_frames(60)
    st = g.start_battle(SCENE)
    g.check(st.can_escape is not False, "this scene permits running at all",
            f"scene_info={st.battle.get('scene_info')}")

    # Wait for a command menu to be OPEN before holding, so the run happens under exactly the
    # condition the ATB-deadlock story said was fatal. If that story were right, nothing below
    # could ever succeed.
    try:
        slot = g.wait_turn(timeout=90.0)
        cursor = g.state.battle_cursor
    except Exception as err:
        slot, cursor = -1, {}
        print(f"[flee] no turn came up before the hold: {err}")
    print(f"[flee] holding with turn.slot={slot} cursor={cursor}")

    got = False
    for attempt in range(3):
        try:
            got = g.flee(timeout=60.0)
        except Exception as err:
            print(f"[flee] attempt {attempt}: {err}")
            break
        st = g.state
        print(f"[flee] attempt {attempt}: escaped={got} escaping={st.escaping} "
              f"turn.slot={st.turn_slot} result={st.battle_result_name}")
        if got or not st.in_battle:
            break
    g.check(got, "the party actually runs away (a roll of a few percent per held second)",
            f"three 60s windows is ~180 rolls; a red after that is a gate, not luck. "
            f"result={g.state.battle_result_name}")

    # ⚠ THE CORRECTION, MEASURED RATHER THAN ARGUED. A menu was open when the hold started, and the
    # roll landed anyway -- so the command menu is not what was blocking the escape. Recorded here
    # because the wrong cause was already written into the docs and the memory once.
    if got:
        g.check(slot >= 0,
                "and it rolled with a command menu OPEN, which the recorded cause said was fatal",
                f"turn.slot was {slot} ({cursor.get('group')!r}) when the hold began; "
                f"IsNativeEnableAtb is true for the top-level command group in WAIT mode")

    # `escaping` is the queued SysEscape -- the roll won. The RESULT lands once the party has
    # finished leaving, and that is the outcome worth asserting: a queued escape that never became
    # one would be a new and much stranger bug.
    try:
        g.wait_for(lambda s: s.battle_result == 4 or not s.in_battle,
                   timeout=45.0, what="the escape to finish and the battle to end")
        ended = g.state.battle_result
    except Exception as err:
        ended = None
        print(f"[flee] the escape queued but the battle did not end: {err}")
    g.check(ended == 4, "and the battle ends in an escape, not merely a queued one",
            f"result={g.state.battle_result_name} ({ended})")
    g.shot("flee-00-after")
