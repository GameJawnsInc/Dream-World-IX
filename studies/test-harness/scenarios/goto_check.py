"""Can the harness put the character on a chosen SPOT? The closed-loop movement acceptance test.

Position-targeted movement is what makes scenarios portable. Frame counts are not: the calibration
run showed a 75-frame hold covering 1014 units where the measured speed implies 2250, because the
character reached the walkmesh edge and stopped. A scenario written in frames would have silently
been standing somewhere else.

Also exercises `calibrate_axes`, which discovers the button->world mapping by probing rather than
assuming. FF9 fields are viewed by frequently-yawed fixed cameras and movement is screen-space, so
"up" is +z here and something else on the next field.

    py tools/play.py studies/test-harness/scenarios/goto_check.py --field 30801
"""

FIELD = 30801
TOLERANCE = 40.0


def run(g, field: int = FIELD):
    g.note("goto_check: closed-loop walk_to")
    g.newgame()
    g.warp(field)
    g.wait_frames(60)

    basis = g.calibrate_axes()
    g.check(basis["v"] is not None and basis["h"] is not None,
            "the button->world axes calibrated on this field",
            f"up={basis['v']} right={basis['h']}")

    origin = g.state
    print(f"[goto] start {origin.pos}")
    g.shot("goto-00-start")

    # Targets relative to where he actually is, so this works on any flat bench rather than only on
    # one hard-coded spot. Kept well inside the 30801 board so a miss means the verb is wrong, not
    # that the target was off the walkmesh.
    #
    # DELIBERATELY AWKWARD OFFSETS. The first cut used +300 everywhere and scored 0.0u on every leg --
    # which looked like a triumph and was really an artefact: the run speed is exactly 30 units/frame,
    # so 300 divides evenly and a single burst landed dead on the target. That test could not have
    # detected a convergence bug. These are chosen NOT to be multiples of either 30 (run) or 15 (walk),
    # so arriving requires the loop to actually close.
    ox, oz = origin.player_x, origin.player_z
    targets = [
        ("north", ox, oz + 253),
        ("northeast", ox + 137, oz + 391),
        ("southwest", ox - 214, oz - 68),
        ("home", ox, oz),
    ]

    for n, (label, tx, tz) in enumerate(targets, start=1):
        arrived = g.walk_to(tx, tz, tolerance=TOLERANCE, strict=False)
        err = g.distance_to(tx, tz)
        g.shot(f"goto-{n:02d}-{label}")
        g.check(arrived, f"walked to the {label} target",
                f"target ({tx:.0f}, {tz:.0f}) -- landed {err:.1f}u away (tolerance {TOLERANCE:.0f})")
        print(f"[goto] {label:6} -> {g.state.pos}  err {err:.1f}u")
