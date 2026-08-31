"""Read and write story flags. The narrative-state acceptance test.

`gEventGlobal` is where FF9 keeps story progress, and it is the axis most of this project's harder
work runs on -- story-gated forks, scenario seeding, the narrative-state engine. The harness has had
`flag` / `byte` / `watch` ops since the first build and none of them was ever proven in-game: they
were written, compiled, and assumed.

This proves the round trip, and specifically that a flag written by the harness is the SAME bit the
engine reads -- `gEventGlobal[n >> 3]` bit `n & 7`. A bit-order mistake would pass any offline test
and quietly set a neighbouring flag in-game.

⚠ SAFE BAND ONLY. Bits are allocated from 8712 up. 8512-8711 is stock read-mail payload that ordinary
play writes a whole byte at a time, and 8376-8511 is the MOGNET lock band; writing either is a live
save-corrupter. This scenario never saves, but using the wrong band here would still be the wrong
example to copy.

    py tools/play.py studies/test-harness/scenarios/flag_check.py --field 30801
"""

FIELD = 30801
BITS = (8712, 8713, 8714, 8719)     # 8712..8714 share a byte; 8719 is the top bit of that same byte
BYTE_INDEX = 8712 >> 3              # the byte those bits live in, for the raw cross-check


def run(g, field: int = FIELD):
    g.note("flag_check: gEventGlobal round trip")
    g.newgame()
    g.warp(field)
    g.wait_frames(45)

    g.watch(*BITS)
    g.wait_frames(6)
    start = g.state
    print(f"[flag] initial: {[(b, start.flag(b)) for b in BITS]}")
    g.check(all(start.flag(b) is False for b in BITS),
            "the safe-band bits start clear on a new game",
            str({b: start.flag(b) for b in BITS}))

    # -- set one, and ONLY one -----------------------------------------------------------------
    g.flag(BITS[0], True)
    g.wait_frames(6)
    st = g.state
    g.check(st.flag(BITS[0]) is True, f"setting bit {BITS[0]} reads back as set",
            str({b: st.flag(b) for b in BITS}))
    # The neighbours are the real test: a bit-order or shift error sets an adjacent flag instead, and
    # in a story context that silently opens a different gate.
    g.check(all(st.flag(b) is False for b in BITS[1:]),
            "its neighbours in the same byte are untouched",
            str({b: st.flag(b) for b in BITS[1:]}))

    # -- clear it again ------------------------------------------------------------------------
    g.flag(BITS[0], False)
    g.wait_frames(6)
    g.check(g.state.flag(BITS[0]) is False, f"clearing bit {BITS[0]} reads back as clear",
            str({b: g.state.flag(b) for b in BITS}))

    # -- a raw byte poke must agree with the bit view ------------------------------------------
    # 0b10000101 -> bits 0, 2 and 7 of the byte = flags 8712, 8714 and 8719.
    g.poke(BYTE_INDEX, 0b10000101)
    g.wait_frames(6)
    st = g.state
    expected = {8712: True, 8713: False, 8714: True, 8719: True}
    got = {b: st.flag(b) for b in BITS}
    g.check(got == expected,
            "a raw byte poke decodes to the expected bits (g[n>>3] bit n&7)",
            f"expected {expected}, got {got}")

    # -- does it survive a field change? -------------------------------------------------------
    # GLOB flags are save-persistent state, so a warp must not disturb them. If this fails, anything
    # that seeds story state before entering a field is unreliable.
    g.warp(field)
    g.wait_frames(45)
    g.watch(*BITS)
    g.wait_frames(6)
    after = g.state
    g.check({b: after.flag(b) for b in BITS} == expected,
            "the flags survived a field reload",
            str({b: after.flag(b) for b in BITS}))

    # Leave the byte as we found it -- the harness shares one install with everything else.
    g.poke(BYTE_INDEX, 0)
    g.wait_frames(6)
    g.check(all(g.state.flag(b) is False for b in BITS), "cleaned up after itself",
            str({b: g.state.flag(b) for b in BITS}))
