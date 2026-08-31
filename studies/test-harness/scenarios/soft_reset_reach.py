"""WHERE does the soft reset actually work? Measured, because reading the code gave two answers.

The suite runner's recovery ladder rests on one claim: FF9's own soft reset (L1+L2+R1+R2+Start+Select)
returns to the title from anywhere, and is therefore the only rung that can rescue a scenario that
left the game in a menu, a battle, or a dialogue -- none of which `warp` can touch.

Reading the engine casts doubt on it. `UIKeyTrigger.Update` runs
`if (HandleMenuControlKeyPressCustomInput()) return;` BEFORE it ever reaches the soft-reset check, and
that handler consumes `Control.Select` unconditionally (`:688`) and returns true. Notably the
neighbouring Pause branch (`:681`) IS guarded with `&& !SoftResetKeyPSXForPause` -- the authors
protected the combo from one branch and not the other. So the combo should be swallowed wherever
`GetSceneFromState(State)` returns a real scene.

And yet the runner soft-reset out of a FIELD ten times in a row, successfully.

Both readings cannot be right, and the harness exists precisely so this does not have to be settled
by argument. This maps the reach empirically: try it from each state and report which ones land on
the title. Whatever it says, the ladder and its documentation get corrected to match.

    py tools/play.py studies/test-harness/scenarios/soft_reset_reach.py --field 30801
"""

FIELD = 30801


def _try_reset(g, where: str) -> bool:
    """Fire the combo and report whether the title arrived. Never raises -- 'no' is the finding."""
    try:
        g.soft_reset(timeout=12.0)
        reached = g.state.ui_state == "Title"
    except Exception as err:
        print(f"[reach] {where}: NO -- {str(err)[:120]}")
        return False
    print(f"[reach] {where}: {'YES' if reached else 'NO'} (ui_state={g.state.ui_state})")
    return reached


def _back_to_field(g, field: int) -> None:
    g.newgame()
    g.warp(field)
    g.wait_frames(45)


def run(g, field: int = FIELD):
    g.note("where does the soft reset reach?")

    # --- from a plain field ------------------------------------------------------------------
    _back_to_field(g, field)
    from_field = _try_reset(g, "FieldHUD")
    g.check(from_field, "the soft reset reaches the title FROM A FIELD",
            "this is the rung the suite runner's ladder ends on; if it stops working the ladder "
            "loses its only route back to the baseline")

    # --- from an open main menu --------------------------------------------------------------
    # ⚠ ASSERTED AS **NO**, which is a measurement this scenario made and the ladder is built around.
    # UIKeyTrigger.Update runs `if (HandleMenuControlKeyPressCustomInput()) return;` BEFORE the
    # soft-reset check, and that handler consumes Control.Select unconditionally (:688) -- while the
    # neighbouring Pause branch (:681) IS guarded with `&& !SoftResetKeyPSXForPause`. So the combo
    # cannot reach the check from inside a menu.
    #
    # If this ever goes YES the engine changed, and `restore_baseline`'s close-UI rung -- which
    # exists solely because of this -- can be reconsidered. Either way the ladder should be told.
    _back_to_field(g, field)
    g.open_menu()
    in_menu = g.state.ui_state
    from_menu = _try_reset(g, f"menu ({in_menu})")
    g.check(not from_menu,
            "the soft reset is SWALLOWED inside a menu (the reason the ladder closes UI first)",
            f"from ui_state={in_menu!r}: {'reached the title -- the engine changed' if from_menu else 'blocked, as expected'}")

    # --- and the ladder gets out of that menu anyway -------------------------------------------
    # The whole point: a scenario is far more likely to end in a menu than anywhere else, and `warp`
    # also refuses outside FieldHUD. If the ladder cannot recover here it would poison every
    # scenario after one that left a menu open.
    ok, why = g.restore_baseline()
    g.check(ok, "the recovery ladder reaches the baseline from inside a menu anyway", why)
    g.check(g.state.ui_state == "Title", "and it is genuinely at the title afterwards",
            repr(g.state))
