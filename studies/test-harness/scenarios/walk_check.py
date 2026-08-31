"""Does an injected direction actually WALK the character? The harness's own acceptance test.

This is the scenario that would have caught the analog-axis bug on day one. The earlier smoke test
asserted that a press was *received* -- key_up true, move_key true -- and every one of those was true
while the character stood perfectly still, because [AnalogControl] zeroed the move vector downstream
of all of them. So this asserts the only thing that cannot be faked by a half-wired input path:
the position changed.

    py tools/play.py studies/test-harness/scenarios/walk_check.py --field 30801
"""

FIELD = 30801          # override with --field; any field with walkable ground under the arrival
FRAMES = 120           # 2 seconds at 60fps -- far enough to be unambiguous, short enough to be cheap
MIN_DISPLACEMENT = 1.0


def run(g, field: int = FIELD):
    g.note("walk_check: does injected input translate the character")
    g.newgame()
    g.warp(field)

    # Settle first. Control goes true before the field's entry/arrival sequence has finished, and
    # input during that window is legitimately ignored -- so measuring from here would blame the
    # harness for the field script doing its job.
    g.wait_frames(60)
    before = g.state
    g.shot("walk-before")
    print(f"[walk] start {before!r}")

    if before.player_x is None:
        g.check(False, "the player position is readable", repr(before))
        return

    g.walk("up", FRAMES)
    g.wait_frames(10)
    after = g.state
    g.shot("walk-after")
    print(f"[walk] end   {after!r}")

    moved = max(abs(after.player_x - before.player_x), abs(after.player_z - before.player_z))
    g.check(
        moved >= MIN_DISPLACEMENT,
        f"holding Up for {FRAMES} frames moves the character",
        f"displacement {moved:.2f} (from {before.pos} to {after.pos})",
    )

    # The engine's own view, so a future failure says WHICH half broke rather than just 'it did not move'.
    inp = after.raw.get("input", {})
    g.check(bool(inp.get("key_up") is not None), "the engine input diagnostic is published", repr(inp))
    print(f"[walk] engine input view: {inp}")
