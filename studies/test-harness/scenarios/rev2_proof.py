"""The acceptance run for the s83 REVISION-2 engine batch.

WHAT THIS IS FOR. Every item in that batch was written because the agent could make a FALSE
STATEMENT -- ack a step it never ran, corrupt its own channel, publish the raw dialogue source as
though it were what the player reads, or acknowledge a refused engine action as a success. The
offline suite proves the DRIVER handles the fixed protocol; it drives a stand-in and certifies
nothing about the DLL on disk. This is the half that can only be answered by a real game.

Each check asserts on the OUTCOME, never on a proxy: the character did not move, the channel is
still parseable, the position did not change, the group label changed. "The step acked" is exactly
what every one of these defects could already fake.

    py tools/play.py studies/test-harness/scenarios/rev2_proof.py --field 30801

⚠ It must be run against the REBUILT engine. On an older DLL the driver logs a DEGRADED warning at
startup and several of these will fail for the right reason -- which is itself a useful negative
control, but do not read it as the batch being broken.
"""

FIELD = 30801


def run(g, field: int = FIELD):
    g.note("s83 rev2 acceptance")
    st = g.state
    proto = st.protocol
    # >= 2, not == 2. This scenario proves the rev2 BATCH, and every later revision keeps it -- a
    # protocol equality check here would go red on rev3 for a batch that is perfectly intact, which
    # is a test failing for a reason that has nothing to do with what it tests.
    g.check(proto is not None and proto >= 2,
            "the deployed engine speaks protocol 2 or later",
            f"published v={proto} (1 = the pre-batch DLL is still deployed)")

    # ---- E11: the save sandbox ------------------------------------------------------------
    # First, because it is the one whose failure costs the OWNER something rather than costing a
    # re-run. Session.start() already refuses to continue when this is false; asserting it here
    # records the path in the report so a green run says WHERE the saves went, not just that they
    # went somewhere.
    sandboxed = st.raw.get("save_sandboxed")
    save_path = st.raw.get("save_path") or ""
    g.check(sandboxed is True and "ff9harness" in save_path,
            "saves are redirected into the harness channel, not the player's folder",
            f"save_sandboxed={sandboxed} save_path={save_path!r}")

    g.newgame()
    g.warp(field)
    g.wait_frames(60)
    g.shot("rev2-00-bench")

    # ---- E2: `release` must not press ------------------------------------------------------
    # The old verb wrote only the release frame, so on a button that was NOT down IsHeld went true
    # for exactly one frame -- a defensive release injected a phantom press. Assert the character
    # did not move, because a one-frame press is exactly what a "did the button register" probe
    # cannot see.
    before = g.state
    g.send("release up")
    g.wait_frames(30)
    after = g.state
    drift = ((after.player_x - before.player_x) ** 2 + (after.player_z - before.player_z) ** 2) ** 0.5
    g.check(drift < 1.0, "releasing a button that is not held moves nothing",
            f"drifted {drift:.2f}u from {before.pos} to {after.pos}")

    # ---- E3: a bad watch must not corrupt the channel ---------------------------------------
    # -1 >> 3 is -1, so the old bound test passed and the array read threw with the key already in
    # the document buffer -- leaving every later state.json unparseable, which the driver reports as
    # "the agent never published state; this engine predates s83" about a perfectly healthy game.
    # The verb is sent RAW because the driver now refuses it locally, and the point is the engine.
    try:
        g.send("watch -1", timeout=8)
        refused = False
    except Exception as err:                     # HarnessError: the agent reported the refusal
        refused = "range" in str(err).lower() or "watch" in str(err).lower()
    g.wait_frames(10)
    still_alive = g.channel.state()
    g.check(still_alive is not None and still_alive.frame > 0,
            "an out-of-range watch bit leaves the state channel readable",
            f"refused={refused} classify={g.channel.classify()}")
    g.check(refused, "an out-of-range watch bit is REPORTED rather than silently swallowed",
            "the agent should raise; a silent accept is how the channel got corrupted before")

    # ---- E1: the error latch is per-request -------------------------------------------------
    # One refusal used to poison every later step: the driver saw a non-null error on a healthy ack
    # and raised, quoting a stale message against an innocent request.
    try:
        g.press("confirm")
        g.wait_frames(10)
        sticky = False
    except Exception as err:
        sticky = True
        print(f"[rev2] the innocent step inherited the blame: {err}")
    g.check(not sticky, "a healthy step after a refused one is not blamed for it",
            "the agent clears its error latch per request (error_seq stamps the owner)")

    # ---- E7: timescale cannot stop the clock ------------------------------------------------
    # At scale 0 the engine runs no logical ticks while frame-count scheduling keeps advancing:
    # presses open and close, waits elapse, everything acks, against a game that executed nothing.
    try:
        g.send("timescale 0", timeout=8)
        zero_ok = True
    except Exception:
        zero_ok = False
    g.check(not zero_ok, "timescale 0 is refused by the engine",
            "a paused game acks every step having run none of them")
    g.timescale(1.0)

    # ---- E6: a refused engine action explains itself ----------------------------------------
    # From a FIELD, a world warp is refused by the debug menu ("world warp: overworld only"). It
    # used to ack clean, and the driver then timed out blaming the destination field.
    try:
        g.send(f"worldwarp {field} -1 -1", timeout=10)
        explained = False
        detail = "the engine ACKED a world warp it refused"
    except Exception as err:
        explained = "overworld" in str(err).lower() or "world" in str(err).lower()
        detail = str(err)[:160]
    g.check(explained, "a refused world warp reports the engine's own reason", detail)
    g.check(g.state.field_id == field, "and the refused warp left the field alone",
            f"still on {g.state.field_id}")

    # ---- E9: reset releases everything ------------------------------------------------------
    # `hold` is non-blocking, so a scenario that raises mid-hold leaves a button DOWN into whatever
    # runs next. Without this verb, isolation between scenarios means a whole disarm/re-arm cycle.
    g.send("hold up 600", wait=False)
    g.wait_frames(6)
    held_before = g.state.held
    g.reset_agent()
    g.wait_frames(10)
    st = g.state
    g.check(not st.held, "reset releases every held button",
            f"held {held_before} -> {st.held}")
    settle = g.state
    g.wait_frames(20)
    moved = ((g.state.player_x - settle.player_x) ** 2
             + (g.state.player_z - settle.player_z) ** 2) ** 0.5
    g.check(moved < 1.0, "and the character is actually stationary afterwards",
            f"drifted {moved:.2f}u -- 'held is empty' is the proxy, this is the outcome")

    # ---- E10: the menu group is observable --------------------------------------------------
    # ui_state does NOT change for a menu sub-screen, so nothing published could verify a menu was
    # entered or left -- the rung a between-scenario recovery ladder cannot skip.
    g.open_menu()
    group_open = g.state.menu_group
    g.close_menu()
    group_closed = g.state.menu_group
    g.check(group_open is not None and group_open != group_closed,
            "the menu button-group changes when a menu opens and closes",
            f"{group_open!r} (open) -> {group_closed!r} (closed); ui_state={g.state.ui_state}")
    label, button = g.state.menu_label, g.state.raw.get("menu", {}).get("button_label")
    print(f"[rev2] menu label={label!r} button_label={button!r}")

    g.shot("rev2-01-final")
    print(f"[rev2] final: {g.state!r}")
