"""Can the harness hold a conversation? The dialogue acceptance test.

Movement was the physical axis; this is the narrative one, and it is the axis most of this project's
content actually lives on. It exercises `interact` (press Confirm and see whether anything answers),
`advance` (page a conversation to its end, keeping the text), and reports every line the game showed
-- text that no external screenshot could have given me, since it comes from `Dialog.Phrase` in the
state channel.

It PROBES for the interactable rather than hard-coding where it is: walk a ring around the arrival
point, press Confirm at each stop, and report where something answered. That makes the scenario
survive a bench being re-authored, and doubles as the "where is the trigger" tool.

    py tools/play.py studies/test-harness/scenarios/talk_check.py --field 30801
"""

FIELD = 30801
RADII = (210, 130)
BEARINGS = [(1, 0, "east"), (-1, 0, "west"), (0, 1, "north"), (0, -1, "south")]


def run(g, field: int = FIELD):
    g.note("talk_check: interact + advance")
    g.newgame()
    g.warp(field)
    g.wait_frames(60)
    g.calibrate_axes()

    home = g.state
    hx, hz = home.player_x, home.player_z
    print(f"[talk] arrival {home.pos}")
    g.shot("talk-00-arrival")

    transcripts = []
    for radius in RADII:
        for ux, uz, name in BEARINGS:
            label = f"{name}-{radius}"
            # Approach from the arrival point each time so every probe starts from the same place and
            # a failed approach cannot silently shift the next one.
            g.walk_to(hx, hz, tolerance=60, strict=False)
            reached = g.walk_to(hx + ux * radius, hz + uz * radius, tolerance=60, strict=False)

            opened = g.interact(timeout=3.0)
            if opened is None:
                print(f"[talk] {label:12} approach={'ok' if reached else 'blocked'}  -- no response")
                continue

            g.shot(f"talk-{label}")
            if opened.choice:
                # A CHOICE, not a monologue. `advance` deliberately refuses to page through one --
                # a Confirm there would silently take whichever option happened to be highlighted --
                # so drive the cursor instead. This is also the only in-game proof that the NGUI
                # navigation hook reaches dialogue choices and not just menus.
                opts = g.options()
                print(f"[talk] {label:12} PROMPT: {g.prompt()!r}")
                print(f"[talk] {label:12} CHOICE of {opened.choice.get('count')}: {opts[:4]}...")
                target = min(3, len(opts) - 1)
                landed = g.select(target)
                g.check(landed == target, f"moved the choice cursor to option {target}",
                        f"{label}: landed on {landed} of {opened.choice.get('count')} "
                        f"= {opts[target]!r}")
                g.shot(f"talk-{label}-selected")
                # The screenshot is the arbiter here: state can only report the INDEX, so the proof
                # that index and label agree is that the rendered cursor sits on options[target].
                print(f"[talk] {label:12} cursor should be on {opts[target]!r} "
                      f"-- verify in talk-{label}-selected.png")
                transcripts.append((label, opts))
                g.press("cancel", 4)      # back out rather than commit to an unknown branch
                g.wait_frames(20)
            else:
                pages = g.advance()
                transcripts.append((label, pages))
                print(f"[talk] {label:12} SPOKE: {pages}")
            # Leave no box open behind us -- an unclosed dialogue eats the next probe's Confirm.
            for _ in range(4):
                if not g.state.dialog_open:
                    break
                g.press("confirm", 3)
                g.wait_frames(10)

        if transcripts:
            break        # found something at this radius; no need to close in further

    g.check(bool(transcripts), "something on this field answered a Confirm",
            f"{len(transcripts)} responder(s): {[t[0] for t in transcripts]}")
    if transcripts:
        # EVERY responder must yield words, not just one of them. The first run passed on "something
        # answered" while one of the two mages returned an open box and zero pages -- the harness had
        # photographed the gap between a box being registered and its text being assigned. Asserting
        # per-responder is what turned that from a shrug into a fixed bug.
        silent = [label for label, pages in transcripts
                  if not any(p.strip() for p in pages)]
        g.check(not silent,
                "every responder's dialogue text was readable from the state channel",
                f"silent responders: {silent}" if silent else
                f"{sum(len(p) for _, p in transcripts)} page(s) captured")
        print("\n[talk] transcript:")
        for label, pages in transcripts:
            for i, page in enumerate(pages):
                print(f"  [{label} p{i}] {page!r}")
