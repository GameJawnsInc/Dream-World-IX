"""Drive a menu BY NAME. The label-navigation acceptance test.

The NGUI hook already moved a cursor, but nothing reported where it landed, so choosing an entry
meant counting keypresses and hoping. That is precisely how the dialogue-choice off-by-one silently
selected the wrong option, and a menu is worse: entries get reordered by content changes and hidden
by story state, so "three downs from the top" means different things on different saves.

The agent now publishes the highlighted widget's label, so this reads the menu, picks an entry by
name, and asserts the game actually went there.

    py tools/play.py studies/test-harness/scenarios/menu_pick_check.py --field 30801
"""

FIELD = 30801
TARGET = "Status"


def run(g, field: int = FIELD):
    g.note("menu_pick_check")
    g.newgame()
    g.warp(field)
    g.wait_frames(60)

    opened = g.open_menu()
    g.shot("pick-00-open")
    g.check(opened.ui_state == "MainMenu", "the main menu opened", f"ui={opened.ui_state}")
    g.check(bool(opened.menu_label), "the engine publishes what is highlighted",
            f"highlight={opened.menu_label!r} widget={opened.menu_selected!r}")
    print(f"[pick] highlight on open: {opened.menu_label!r} ({opened.menu_selected!r})")

    labels = g.menu_labels()
    print(f"[pick] menu offers: {labels}")
    g.check(len(labels) >= 3, "walked the menu and read its entries", f"{labels}")

    # Re-open so the walk above leaves no residue, then pick by name.
    g.close_menu()
    g.open_menu()
    landed = g.menu_pick(TARGET)
    g.shot("pick-01-picked")
    after = g.state
    g.check(landed.strip().lower() == TARGET.lower(),
            f"highlighted {TARGET!r} before confirming", f"landed on {landed!r}")
    g.check(after.ui_state != "FieldHUD",
            f"confirming {TARGET!r} went somewhere, not back to the field",
            f"ui={after.ui_state} highlight={after.menu_label!r}")
    print(f"[pick] after confirming {TARGET!r}: ui={after.ui_state} highlight={after.menu_label!r}")

    g.close_menu()
    g.check(g.state.ui_state == "FieldHUD", "backed out to the field again", repr(g.state))
