"""Sit through a scripted sequence and bring back its script.

A withheld-control sequence is the state a naive harness hangs in: every movement verb silently does
nothing and the run dies much later on an unrelated timeout pointing at the wrong thing.
`watch_cutscene` makes the wait explicit, advances the boxes a scripted scene is waiting on, and
returns the transcript -- which is the part worth asserting, because once control comes back the text
is gone from the state channel for good.

The verb has TWO jobs and they are proven separately here, because a bench that exercises one does
not necessarily exercise the other:

  1. WAIT -- on 30601, which `recon_all` reported arriving with control withheld.
  2. COLLECT -- on 30801, by opening a black mage's box and letting the verb page it away. The first
     version of this scenario asserted collection on 30601 and failed: that bench withholds control
     briefly on arrival but plays no dialogue, so it could never have proven the collect path. The
     verb was right and the expectation was wrong.

    py tools/play.py studies/test-harness/scenarios/cutscene_check.py --field 30601
"""
import time

FIELD = 30601
TALKER = 30801


def run(g, field: int = FIELD):
    g.note("cutscene_check")
    g.newgame()

    # -- job 1: wait through withheld control -------------------------------------------------
    # NOT g.warp(): warp waits for the destination to be playable, and a field that opens on a
    # scripted sequence is deliberately not playable yet.
    g.send(f"warp {int(field)} -1 -1")
    g.wait_for(lambda s: s.field_id == int(field), timeout=45, what=f"field {field} to load")
    g.shot("cut-00-arrival")
    arrived = g.state
    print(f"[cut] {field}: arrived control={arrived.control}")

    started = time.time()
    pages = g.watch_cutscene(timeout=90.0)
    held_for = time.time() - started
    after = g.state
    g.shot("cut-01-after")

    g.check(after.control, "control returned after the scripted sequence", repr(after))
    g.check(after.player_x is not None, "the player has a position once control returns",
            f"pos={after.pos}")
    # Reported, not asserted: whether this particular bench has anything to say is a property of the
    # bench. Claiming it as a pass would be asserting on someone else's content.
    print(f"[cut] {field}: control withheld ~{held_for:.1f}s, {len(pages)} page(s) collected "
          f"-- {'a real scripted scene' if held_for > 2 else 'just the entry settle'}")

    # -- job 2: collect dialogue ---------------------------------------------------------------
    g.warp(TALKER)
    g.wait_frames(60)
    g.calibrate_axes()
    home = g.state
    g.walk_to(home.player_x - 210, home.player_z, tolerance=60, strict=False)

    opened = g.interact(timeout=4.0)
    if opened is None:
        g.check(False, "found a talker on the collect bench", "nothing responded to Confirm")
        return

    collected = g.watch_cutscene(timeout=30.0)
    g.shot("cut-02-collected")
    g.check(bool(collected), "watch_cutscene collected the dialogue it paged through",
            f"{len(collected)} page(s): {collected[0][:60]!r}..." if collected else "none")
    g.check(g.state.control and not g.state.dialog_open,
            "it returned with the box closed and control back", repr(g.state))

    print(f"\n[cut] collected transcript ({len(collected)} pages):")
    for i, page in enumerate(collected):
        print(f"  [p{i}] {page!r}")
