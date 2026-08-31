"""Can the harness move a cursor inside a menu? The NGUI navigation acceptance test.

Opening a menu was already possible -- Menu/Confirm/Cancel route through HonoInputManager.IsInput.
MOVING inside one did not, because NGUI reads its cursor direction from UnityXInput.Input.GetAxisRaw
via UICamera.GetDirection, a path the original hooks never touched. That single site governs the
battle command cursor, every field dialogue choice, and every menu in the game
(studies/test-harness/INPUT-COVERAGE.md).

There is no cursor-index readout in the state channel, so this scenario cannot self-assert the way
walk_check.py can: it captures a frame per step and the verdict is read off the images. That is a
deliberate limit, stated rather than papered over -- publishing the highlighted-widget name would
make this fully automatic and is the obvious follow-up.

    py tools/play.py studies/test-harness/scenarios/menu_nav.py --field 30801
"""

FIELD = 30801
STEP = 6          # frames per cursor nudge; NGUI thresholds the axis, so a 2-frame tap can be missed


def run(g, field: int = FIELD):
    g.note("menu_nav: can injected input move an NGUI cursor")
    g.newgame()
    g.warp(field)
    g.wait_frames(60)

    g.press("menu", 6)
    g.wait_frames(45)
    opened = g.state
    g.shot("menu-00-open")
    g.check(opened.ui_state != "FieldHUD", "the main menu opened",
            f"ui_state={opened.ui_state}")

    for n in (1, 2, 3):
        g.press("down", STEP)
        g.wait_frames(20)
        g.shot(f"menu-{n:02d}-down")

    g.press("up", STEP)
    g.wait_frames(20)
    g.shot("menu-04-up")

    g.press("cancel", 6)
    g.wait_frames(45)
    closed = g.state
    g.shot("menu-05-closed")
    g.check(closed.ui_state == "FieldHUD", "the menu closed again",
            f"ui_state={closed.ui_state}")
    print(f"[menu] open={opened.ui_state} closed={closed.ui_state}")
