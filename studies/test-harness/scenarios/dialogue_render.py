"""E4 + E5: is the published dialogue what the PLAYER reads, and do the choice indexes agree?

These are the two items in the s83 rev2 batch that nothing outside the engine could have fixed, and
the two that could produce the most expensive kind of wrong answer -- a scenario that reports GREEN
for a story branch it never took.

**E4.** `Dialog.Phrase` is `CurrentParser.InitialText`: the raw sub-page SOURCE, every `[STRT=…]` /
`[TIME=…]` tag intact, before variable substitution. Asserting on it means matching a string the
player never sees -- a false RED on ordinary dialogue, and a possible false GREEN when the words
happen to sit inside a tag parameter. The agent now publishes `ParsedText` as `texts` and keeps the
source as `phrase_raw`. This asserts they are BOTH present and that the rendered one is clean, rather
than asserting they differ -- a box with no tags renders identically, and demanding a difference
would be an assertion about the bench rather than about the mechanism.

**E5.** A choice line disabled by the field script is physically REMOVED from the parsed text, while
`SelectChoice` still counts the ABSOLUTE list including it. So `options()[i]` was not the option
`select(i)` lands on. The proof here is the strongest available: ask for an option BY NAME, move the
cursor, and then read back from the engine's own `SelectChoice` that the option it is sitting on is
the one that was named. That is the exact step where the historical off-by-one asked for index 3,
which read "Minigames", and left the cursor on "Tetra Master".

    py tools/play.py studies/test-harness/scenarios/dialogue_render.py --field 30801

Bench 30801 has two responders 210 units out: EAST is a multi-option choice menu (the same one whose
15 options published only 13 phrases), WEST is a plain window.
"""

FIELD = 30801
EAST = (210.0, -837.0)          # the choice menu
WEST = (-210.0, -837.0)         # a plain text window
WANT = "Tetra Master"


def run(g, field: int = FIELD):
    g.note("E4/E5: rendered dialogue and the choice index space")
    g.newgame()
    g.warp(field)
    g.wait_frames(60)
    g.calibrate_axes()

    # ---- E5: the choice index space ---------------------------------------------------------
    g.walk_to(*EAST, tolerance=45, strict=False)
    opened = g.interact(timeout=6)
    if opened is None or not opened.choice:
        g.check(False, "the east responder opened a choice dialogue", repr(g.state))
        return

    ch = g.state.choice
    count = int(ch.get("count", 0))
    raw = list(ch.get("options", []))
    active = ch.get("active")
    disabled = ch.get("disabled")
    print(f"[dlg] choice: count={count} raw_options={len(raw)} active={active} disabled={disabled}")
    for i, name in enumerate(raw):
        print(f"[dlg]   raw[{i}] = {name!r}")

    g.check(active is not None,
            "the engine publishes the choice's ACTIVE index list",
            f"active={active} disabled={disabled} -- without this nothing can map a name to a cursor "
            f"index when any line is masked out")

    names = g.options()
    print(f"[dlg] options() -> {names}")

    # THE ASSERTION THAT MATTERS. Ask by name, then read back from the engine's own SelectChoice
    # which option the cursor actually landed on. Counting keypresses is what produced the original
    # off-by-one; this closes the loop against the engine rather than against our own arithmetic.
    if WANT in names:
        index = g.option_index(WANT)
        landed = g.select(index)
        after = g.state.choice or {}
        at_cursor = None
        opts = list(after.get("options", []))
        act = after.get("active") or list(range(len(opts) - 1))
        if landed in act:
            pos = act.index(landed)
            if 0 <= pos + 1 < len(opts):
                at_cursor = opts[pos + 1]        # element 0 is the pre-choice header
        g.check(at_cursor is not None and at_cursor.strip() == WANT,
                f"asking for {WANT!r} by name leaves the cursor ON {WANT!r}",
                f"option_index -> {index}, engine SelectChoice -> {landed}, "
                f"the option there reads {at_cursor!r}")
        g.shot("dlg-choice-selected")
    else:
        g.check(False, f"the bench offers an option called {WANT!r}", f"it offers {names}")

    # ⚠ THIS CHOICE CANNOT BE CANCELLED. The first cut pressed Cancel four times and then blamed the
    # game for never returning control -- the harness was right that control never came back and
    # wrong about why. A scripted choice with no cancel row consumes Cancel and sits there. So take
    # the branch and page out of whatever it shows, which is the only exit this dialogue has.
    g.press("confirm", 4)
    g.wait_frames(12)
    pages = g.advance(max_pages=12)
    print(f"[dlg] the branch showed {len(pages)} page(s)")
    for _ in range(6):
        if not g.state.dialog_open:
            break
        g.press("confirm", 3)
        g.wait_frames(12)

    # ---- E4: rendered vs source -------------------------------------------------------------
    g.wait_control(timeout=30)
    g.walk_to(*WEST, tolerance=45, strict=False)
    box = g.interact(timeout=6)
    if box is None:
        g.check(False, "the west responder opened a text window", repr(g.state))
        return

    st = g.state
    rendered, source = st.texts, st.raw_texts
    print(f"[dlg] rendered : {rendered}")
    print(f"[dlg] source   : {source}")

    g.check(bool(rendered) and bool(source),
            "the channel publishes BOTH the rendered dialogue and its source",
            f"texts={len(rendered)} entry(s), phrase_raw={len(source)} entry(s)")

    # The rendered string is what an assertion matches against, so it must not carry markup. This is
    # the check that would have gone red on the old engine, where `texts` WAS the source.
    text = st.text
    markup = [tag for tag in ("[STRT", "[TIME", "[FEED", "[TABL", "[CHOM") if tag in text]
    g.check(not markup, "the rendered dialogue carries no control markup",
            f"found {markup} in {text[:120]!r}" if markup else f"clean: {text[:120]!r}")
    g.check(bool(g.expect_text("SCRIBE")), "and expect_text matches against what is on screen",
            repr(text[:80]))
    g.shot("dlg-plain-window")
