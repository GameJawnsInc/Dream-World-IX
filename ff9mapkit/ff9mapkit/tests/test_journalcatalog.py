

# ============================ the SIDE-counter records (M3) ============================
def test_side_counters_agree_with_the_journal_readers():
    """The equivalence proof: each C record's primitive read, evaluated over a synthetic heap,
    must equal journal's own offline reader for the row it mirrors -- one source, two renderers."""
    from ff9mapkit import journal as J

    geg = bytearray(2048)
    geg[J.BEAK_LEVEL_OFF] = 57
    geg[J.DIG_ABILITY_OFF] = 3
    geg[J.RAGTIME_OFF] = 11 << 3
    for i in range(13):                                   # beaches: 13 of 21 bits set
        b = J.SANDY_BEACH_BIT + i
        geg[b >> 3] |= 1 << (b & 7)

    def read(kind, a, b, c):
        if kind == "byte":
            return geg[a]
        if kind == "bit":
            return (geg[a >> 3] >> (a & 7)) & 1
        if kind == "bitcount":
            return sum((geg[(a + i) >> 3] >> ((a + i) & 7)) & 1 for i in range(b))
        if kind == "field":
            return (geg[a] >> b) & ((1 << c) - 1)
        return None                                       # sysvar: not a geg read

    by = {}
    for sec, label, kind, a, b, c, denom in JC.side_counters():
        by[(sec, label)] = read(kind, a, b, c)
    assert by[("side.chocobo-hot-cold", "Beak level")] == 57
    assert by[("side.chocobo-hot-cold", "Dig terrain")] == 3
    assert by[("side.chocobo-hot-cold", "Beaches")] == 13
    assert by[("side.ragtime-mouse", "Quizzes")] == 11
    # journal's own readers on the same heap agree (the cross-check that makes this ONE source)
    st = type("S", (), {"geg": bytes(geg)})()
    assert J.row_spec("chocobo.beak_level").read(st).value == 57
    assert J.row_spec("chocobo.dig_ability").read(st).value == 3
    assert J.row_spec("chocobo.beaches").read(st).value == 13
    assert J.row_spec("minigame.ragtime_quiz").read(st).value == 11


def test_side_counter_records_ride_the_patch():
    body = JC.render_patch()
    rows = [ln.split("\t") for ln in body.splitlines() if ln.startswith("C\t")]
    assert len(rows) == len(JC.side_counters())
    for r in rows:
        assert len(r) == len(JC.PATCH_COUNTER_COLS), r
        assert r[3] in ("byte", "bit", "bitcount", "field", "sysvar")
