"""WHY does holding L1+R1 not always escape? An instrument, not an assertion.

The escape worked once and then failed twice with the bumpers demonstrably held, so something other
than the hold decides it. `btl_sys.CheckEscape` has exactly two gates:

    if ((ff9Battle.cmd_status & 1) != 0) return;                    // a command is in flight
    if (!ff9Battle.btl_scene.Info.Runaway) { "Cannot escape!" }      // measured TRUE on scene 67
    else if (calc_check && UIManager.Battle.IsNativeEnableAtb())     // <-- the untested one
        SBattleCalculator.CalcMain(null, null, null, fleeScriptId);

`IsNativeEnableAtb()` is the suspect: FF9 pauses the ATB while a command menu is open, and the
harness has been sitting in `Battle.Command` the whole time -- the cursor readout says so. If that is
it, the roll never fires no matter how long the bumpers are down, and the running animation plays
regardless because `btl_escape_key` is set BEFORE any of these gates.

This samples the published state while holding, so the answer comes from the game rather than from
another reading of the source. It records ONE check -- that it collected a usable trace -- because
its output is a measurement, not a pass/fail.

    py tools/play.py studies/test-harness/scenarios/flee_probe.py --field 30801
"""

FIELD = 30801
SCENE = 67
SAMPLES = 60


def run(g, field: int = FIELD):
    g.note("flee probe: what gates the escape?")
    g.newgame()
    g.warp(field)
    g.wait_frames(60)
    g.start_battle(SCENE)

    print(f"[flee] scene {g.state.battle.get('scene')} runaway={g.state.can_escape}")
    print("[flee]  t     held  escape_key  turn.slot  cursor.group        result  message")

    trace = []
    for i in range(SAMPLES):
        # Re-issue every iteration so the bumpers are never up: _runCounter resets the instant
        # either one lifts, and the threshold is 1.0 REAL second.
        g.send("hold l1 90", "hold r1 90", wait=False)
        st = g.state
        row = {
            "i": i,
            "held": sorted(st.held),
            "escape_key": st.battle.get("escape_held"),
            "turn": st.battle.get("turn", {}).get("slot"),
            "group": st.battle_cursor.get("group"),
            "result": st.battle_result,
            "message": st.battle_message,
        }
        trace.append(row)
        print(f"[flee] {i:>3}  {str(row['held']):<22} {row['escape_key']}      "
              f"{str(row['turn']):>3}       {str(row['group'])!r:<22} "
              f"{row['result']}     {row['message']!r}")
        if st.battle_result != 0 or not st.in_battle:
            print(f"[flee] ESCAPED/ENDED at sample {i}: {st.battle_result_name}")
            break
        g.wait_frames(20)

    # What the trace says, stated plainly.
    saw_key = [r for r in trace if r["escape_key"]]
    menu_open = [r for r in trace if (r["turn"] or -1) >= 0]
    ended = [r for r in trace if r["result"] != 0]
    print(f"[flee] SUMMARY over {len(trace)} samples: "
          f"escape_key set in {len(saw_key)}, a command menu was open in {len(menu_open)}, "
          f"result reached in {len(ended)}")
    if saw_key and not ended:
        print("[flee] the engine SAW the hold (escape_key was set) and still never rolled -- so the "
              "gate is downstream of the input, i.e. cmd_status or IsNativeEnableAtb.")
    if not saw_key:
        print("[flee] the engine never even set escape_key -- the hold is not reaching BattleHUD.")

    g.check(len(trace) >= 3, "collected a usable trace of the escape attempt",
            f"{len(trace)} samples; escape_key set in {len(saw_key)}, menu open in {len(menu_open)}")
