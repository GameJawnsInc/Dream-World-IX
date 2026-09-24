"""``storytrace`` -- the kit side of the story-write trace (memoria-patch s88; studies/story-trace/PLAN.md).

What these pin, offline: the proto-1 row contract is ENFORCED (an unknown kind, a missing/extra field, a string
number, a value the engine cannot emit -- each an error naming its line, never a skipped row); epochs segment
the rows and every suppressed count lands on the site it belongs to; the story-noise mask is the kit's one mask
(flags.story_noise_bits) with the per-width rule; THE JOIN lands an ``eb`` row on the store instruction that
wrote it or reports why it cannot, never a guess; a fork's prepend and a same-length operand remap align to
the donor; and every diff category of the N-vs-N comparison.

Synthetic scripts are assembled from eb-src text (``cmdasm.assemble_block``), so each offset below is one a
reader can check against the source. The real-bytes join (field 552 from the install) warns and skips
without an install -- the worktree skip trap, said out loud.
"""

from __future__ import annotations

import json
import struct
import warnings

import pytest

from ff9mapkit import cli, flags
from ff9mapkit import storytrace as S
from ff9mapkit.eb import EbScript, cmdasm
from ff9mapkit.eb.exprsem import WRITE_OPS
from ff9mapkit.eb.model import pack_entry

COMMON = dict(f=100, p=7, m=1, fld=552, don=552, sc=3115)


def _w(**kw) -> dict:
    row = dict(k="w", **COMMON, src="eb", sid=0, uid=0, lvl=0, ip=10, tag=0, add=0, byte=9, w="Int16",
               bit=-1, old=0, new=1582)
    row.update(kw)
    row.setdefault("same", int(row["old"] == row["new"]))
    return row


def _e(why: str, **kw) -> dict:
    return {"k": "e", **COMMON, "why": why, **kw}


def _r(byte: int, old: int, new: int, why: str = "frame", **kw) -> dict:
    return {"k": "r", **COMMON, "byte": byte, "old": old, "new": new, "why": why, **kw}


def _c(w: dict, n: int, last: int) -> dict:
    """The count row for ``w``'s site (the engine emits the site key -- its fld/don/m are the site's -- n and
    the last suppressed value)."""
    site = {k: w[k] for k in ("fld", "don", "m", "src", "sid", "tag", "ip", "byte", "w", "bit")}
    return {"k": "c", **COMMON, **site, "n": n, "last": last}


def _text(*rows) -> str:
    return "".join(json.dumps(r, separators=(",", ":")) + "\n" for r in rows)


def _rows(*rows) -> list:
    return S.parse_text(_text(*rows))


def _eb(*entries) -> bytes:
    """A .eb whose entries are ``[(tag, eb-src text), ...]`` (None = an empty slot)."""
    bodies = [b"" if funcs is None else pack_entry(0, [(t, cmdasm.assemble_block(src)) for t, src in funcs])
              for funcs in entries]
    head = bytearray(0x80)
    head[0:2], head[2], head[3] = b"EV", 2, len(entries)
    table, pos = b"", len(entries) * 8
    for body in bodies:
        table += struct.pack("<HHBBH", pos, len(body), 0, 0, 0)
        pos += len(body)
    return bytes(head) + table + b"".join(bodies)


def _ip(data: bytes, sid: int, tag: int, rel: int) -> int:
    """The engine's ip (entry-relative) for function offset ``rel`` of (sid, tag)."""
    e = EbScript.from_bytes(data).entries[sid]
    return e.func_by_tag(tag).abs_start - e.abs_start + rel


# The donor: Main_Init writes Int16[9] (+0) and Bit[8800] (+8); entry 1's talk handler writes Bit[9000] (+0),
# warps (+9), and after its RET (+13) carries a store no path reaches (+14 -- the census cannot count it).
MAIN = [(0, "SET({Global.Int16[9] const(1582) B_LET B_EXPR_END})\n"
            "SET({Global.Bit[8800] const(1) B_LET B_EXPR_END})\nRET()"),
        (10, "SET({Global.Byte[300] const(4) B_LET B_EXPR_END})\nRET()")]
NPC = [(3, "SET({Global.Bit[9000] const(1) B_LET B_EXPR_END})\nField(552)\nRET()\n"
           "SET({Global.Bit[9001] const(1) B_LET B_EXPR_END})\nRET()")]
DONOR = _eb(MAIN, NPC)
# The fork: [startup] prepends an SC stamp (8 bytes) to Main_Init; the verbatim Field() is remapped in place.
PREPEND = "SET({Global.UInt16[0] const(3115) B_LET B_EXPR_END})\n"
FORK = _eb([(0, PREPEND + MAIN[0][1]), MAIN[1]], [(3, NPC[0][1].replace("Field(552)", "Field(30823)"))])


# ======================================================================= the row contract
def test_every_kind_parses_to_a_row_with_numbers_kept_numbers():
    w = _w()
    rows = _rows(_e("arm"), w, _r(100, 0, 5), _c(w, 3, 1582), _e("off"))
    assert [r.k for r in rows] == ["e", "w", "r", "c", "e"]
    wr = rows[1]
    assert (wr.width, wr.byte, wr.new, wr.target, wr.line) == ("Int16", 9, 1582, "Global.Int16[9]", 2)
    assert rows[3].site == wr.site and rows[3].n == 3
    bit = S.parse_row(_w(byte=1100, w="Bit", bit=8800, old=0, new=1))
    assert bit.is_bit and bit.target == "Global.Bit[8800]" and list(bit.span) == [1100]


@pytest.mark.parametrize("row, match", [
    ({**_w(), "k": "x"}, "unknown row kind 'x'"),
    ({k: v for k, v in _w().items() if k != "ip"}, "missing ip"),
    ({**_w(), "caller": 3}, "carries caller, which proto 1 does not define"),
    ({**_w(), "byte": "9"}, "byte must be a JSON integer"),
    ({**_w(), "same": True}, "same must be a JSON integer"),
    ({**_w(), "w": "u16"}, "not an engine variable width"),
    (_w(w="Bit", bit=8801, byte=9, old=0, new=1), "bit 8801 is not a bit of byte 9"),
    (_w(bit=3), "only a bit store has one"),
    ({**_w(), "same": 1}, "disagrees with old"),
    (_w(src="cs"), "names a writer"),
    (_w(add=1, tag=0), "addition-buffer row carries a tag"),
    (_w(w="Byte", byte=40, old=0, new=300), "outside what a Byte reads as"),
    (_w(byte=2047), "runs past gEventGlobal"),
    (_r(100, 5, 5), "not a byte that changed"),
    (_r(100, 0, 5, why="late"), "residue why 'late'"),
    (_e("reboot"), "epoch why 'reboot'"),
    ({**_c(_w(), 1, 0), "n": 0}, "suppressing 0 rows"),
    ([1, 2], "a row is a JSON object"),
])
def test_a_contract_break_is_an_error_naming_the_line_never_a_skipped_row(row, match):
    with pytest.raises(S.TraceError, match=match) as ex:
        S.parse_text(_text(_e("arm"), row))
    assert "line 2" in str(ex.value)


def test_a_live_read_holds_back_the_append_in_flight_but_a_collected_trace_does_not():
    text = _text(_e("arm"), _w()) + '{"k":"w","f":1'           # the engine is mid-append
    assert [r.k for r in S.parse_text(text, live=True)] == ["e", "w"]
    with pytest.raises(S.TraceError, match="line 3: not JSON"):
        S.parse_text(text)                                       # collected: a torn line is a defect
    with pytest.raises(S.TraceError, match="line 2: not JSON"):
        S.parse_text(_text(_e("arm")) + "garbage\n", live=True)      # a COMPLETE bad line is never held


# ======================================================================= epochs + counts
def test_epochs_segment_the_rows_and_counts_fold_onto_their_site():
    a, b = _w(), _w(ip=30, byte=300, w="Byte", old=0, new=4)
    rows = _rows(_e("arm"), a, _r(100, 0, 1), b, _c(a, 5, 7), _e("swap"), b, _e("off"), _e("arm"), a)
    eps = S.epochs(rows)
    assert [(ep.why, ep.closed_by) for ep in eps] == [("arm", "swap"), ("swap", "off"), ("arm", None)]
    first = eps[0]
    assert len(first.writes) == 2 and len(first.residue) == 1
    site = first.sites[S.parse_row(a).site]
    assert (site.suppressed, site.last) == (5, 7)
    assert eps[1].sites[S.parse_row(b).site].suppressed == 0      # counts are per epoch


@pytest.mark.parametrize("rows, match", [
    ([_w()], "outside any epoch"),                                # a trace opens with an epoch
    ([_e("arm"), _e("off"), _w()], "outside any epoch"),          # nothing between off and the next arm
    ([_e("arm"), _w(), _c(_w(ip=99), 2, 0), _e("off")], "never emitted"),
    ([_e("arm"), _w(), _c(_w(fld=553, don=553), 2, 0), _e("off")], "never emitted"),   # the key is per field
    ([_e("arm"), _w(), _c(_w(), 2, 0), _w(), _e("off")], "after the epoch's counts"),
])
def test_the_engines_epoch_shape_is_enforced(rows, match):
    with pytest.raises(S.TraceError, match=match):
        S.epochs(_rows(*rows))


# ======================================================================= runs + completeness
def test_a_file_splits_into_one_run_per_arm_and_a_digest_takes_exactly_one():
    """The engine only appends: every `storytrace 1` of a launch lands in one file. Read whole, a key reached
    in 1 of 3 runs would count as reached in 1 of 1 -- so a digest refuses more than one run."""
    a = _w()
    rows = _rows(_e("arm"), a, _e("off"), _e("arm"), a, _c(a, 2, 1582), _e("arm"), _e("off"))
    assert [[r.k for r in run] for run in S.split_runs(rows)] == [["e", "w", "e"], ["e", "w", "c"], ["e", "e"]]
    stock, _fork = _sources()
    with pytest.raises(S.TraceError, match="3 traced runs where one was given"):
        S.digest("all", rows, scripts=stock)
    with pytest.raises(S.TraceError, match="no traced run"):
        S.digest("none", [], scripts=stock)


def test_rows_before_the_first_arm_are_another_arms_tail_never_this_run():
    """A leaked run's `storytrace 0` (StoryTrace.Stop: residue, counts, off) landing after this run's reset."""
    w = _w()
    with pytest.raises(S.TraceError, match="line 1: .*before the first `arm`"):
        S.split_runs(_rows(_r(100, 0, 1), _c(w, 12, 1582), _e("off"), _e("arm"), w, _e("off")))


def test_a_run_with_no_off_is_incomplete_and_every_report_says_so():
    """StoryTrace.Fail turns the tracer off with NO `off` row: its run is cut, and a key past the cut must not
    read as "never written" (an empty STOCK ONLY for a broken instrument)."""
    stock, fork = _sources()
    full = S.digest("full", _rows(*_stock_run()), scripts=stock)
    cut = S.digest("cut", _rows(*_stock_run()[:2]), scripts=stock)          # faulted after one write
    assert not full.incomplete and "no `off`" in cut.incomplete
    c = S.compare([cut], [S.digest("fork", _rows(*_fork_run()), scripts=fork, donor_scripts=stock)])
    assert c.incomplete == [cut]
    text = S.report(c)
    assert text.splitlines()[1].startswith("!! 1 run(s) INCOMPLETE") and "  cut: the trace ends inside" in text
    assert "!! 1 run(s) INCOMPLETE" in S.report_runs([cut]) and "INCOMPLETE" not in S.report_runs([full])
    # a second `storytrace 1` without an `off` cuts the first run too (Start's Resync: counts, then `arm`)
    first, second = S.split_runs(_rows(*_stock_run()[:3], *_stock_run()))
    assert S.digest("a", first, scripts=stock).incomplete and not S.digest("b", second, scripts=stock).incomplete


def test_the_one_side_report_lists_writes_in_the_order_the_engine_wrote_them():
    """Rung 0 asks whether Main_Init's writes arrive in script order. Re-sorted by offset, the list would show
    script order whatever the engine emitted -- a check that cannot fail."""
    stock, _fork = _sources()
    early = _w(ip=_ip(DONOR, 0, 0, 0))                                        # Int16[9] at +0
    late = _w(ip=_ip(DONOR, 0, 0, 8), w="Bit", byte=1100, bit=8800, old=0, new=1)
    text = S.report_runs([S.digest("r", _rows(_e("arm"), late, early, _c(early, 40, 1600), _e("off")),
                                   scripts=stock)])
    writes = [ln for ln in text.splitlines() if ln.startswith("  line ")]
    assert [ln.split()[1] for ln in writes] == ["2", "3", "4"]
    assert " +8 " in writes[0] and " +0 " in writes[1]                     # emitted +8 first: listed first
    assert "= 1600" in writes[2] and "counted at the epoch's close" in writes[2]


# ======================================================================= the mask
def test_the_mask_is_flags_story_noise_bits_with_the_per_width_rule():
    assert S.noise_regions(S.parse_row(_w(w="Bit", byte=23, bit=191, old=1, new=0))) == ("boot_scratch",)
    assert S.noise_regions(S.parse_row(_w(w="Bit", byte=1100, bit=8800, old=0, new=1))) == ()
    # a word wholly inside noise bytes masks; one straddling a noise byte and a story byte does not
    assert S.noise_regions(S.parse_row(_w(w="UInt16", byte=2032, old=0, new=1)))
    assert all(b in flags.story_noise_bits() for b in range(1045 * 8, 1046 * 8))
    assert not any(b in flags.story_noise_bits() for b in range(1046 * 8, 1047 * 8))
    assert S.noise_regions(S.parse_row(_w(w="UInt16", byte=1045, old=0, new=1))) == ()
    assert S.noise_regions(S.parse_row(_w(w="Byte", byte=1024, old=0, new=1))) == ("mognet_mailbox",)
    # residue masks per BYTE: byte 23 carries clear spare bits (185-188, 190), so it stays visible
    assert S.noise_regions(S.parse_row(_r(23, 0, 2))) == ()
    assert S.noise_regions(S.parse_row(_r(2033, 0, 2)))


# ======================================================================= THE JOIN
def test_a_row_joins_the_store_that_wrote_it_with_its_text_and_name():
    si = S.ScriptIndex(DONOR, field_id=552)
    j = si.join(S.parse_row(_w(ip=_ip(DONOR, 0, 0, 8), byte=1100, w="Bit", bit=8800, old=0, new=1)))
    assert (j.status, j.entry, j.tag, j.rel, j.census) == ("store", 0, 0, 8, True)
    assert j.text == "SET({Global.Bit[8800] const(1) B_LET B_EXPR_END})"
    assert j.name.endswith("(tag 0)")


@pytest.mark.parametrize("kw, reason", [
    (dict(ip=-1), "no opcode latch"),
    (dict(sid=7, uid=7), "sid 7 is not an entry"),
    (dict(ip=5000), "outside entry 0"),
    (dict(tag=10), "puts ip .* in tag 0, the row says tag 10"),
    (dict(ip="+3"), r"\+3 is not an instruction boundary"),
    (dict(ip="+17"), "not a store"),                             # RET
    (dict(byte=11), r"stores to Global.Int16\[9\], not Global.Int16\[11\]"),
    (dict(w="UInt16"), r"not Global.UInt16\[9\]"),
])
def test_a_row_that_does_not_land_on_its_store_is_a_join_failure(kw, reason):
    kw = dict(kw)
    if isinstance(kw.get("ip"), str):
        kw["ip"] = _ip(DONOR, 0, 0, int(kw["ip"][1:]))
    kw.setdefault("ip", _ip(DONOR, 0, 0, 0))
    j = S.ScriptIndex(DONOR).join(S.parse_row(_w(**kw)))
    assert j.status == "fail" and not j.ok
    assert __import__("re").search(reason, j.reason), j.reason


def test_an_empty_slot_and_a_non_store_opcode_fail_by_name():
    data = _eb(MAIN, None, NPC)
    j = S.ScriptIndex(data).join(S.parse_row(_w(sid=1, uid=1, ip=0)))
    assert j.status == "fail" and "empty slot" in j.reason
    warp = _ip(data, 2, 3, 9)                                    # Field(552)
    j = S.ScriptIndex(data).join(S.parse_row(_w(sid=2, uid=2, tag=3, ip=warp, w="Bit", byte=1125, bit=9000,
                                                old=0, new=1)))
    assert j.status == "fail" and j.text == "Field(552)" and "not a store" in j.reason


def test_a_store_through_a_non_literal_lvalue_is_unverified_not_guessed():
    data = _eb([(0, "SET({const(5) const(1) B_LET B_EXPR_END})\nRET()")])
    j = S.ScriptIndex(data).join(S.parse_row(_w(ip=_ip(data, 0, 0, 0), w="Byte", byte=5, old=0, new=1)))
    assert j.status == "unverified" and "not a literal variable" in j.reason and j.ok


def test_the_oeilvert_hotfix_is_a_named_engine_write_not_a_failure():
    """DoEventCode.cs REQEW: on field 2209 a RunScriptSync into tag 74 clears a party bit INSIDE the opcode."""
    data = _eb([(0, "RunScriptSync(0, 4, 74)\nRET()")])
    row = S.parse_row(_w(ip=_ip(data, 0, 0, 0), w="Bit", byte=442, bit=3536, old=1, new=0, fld=2209, don=2209))
    assert S.ScriptIndex(data).join(row, donor=2209).status == "engine"
    assert S.ScriptIndex(data).join(row, donor=552).status == "fail"       # only where the engine does it


def test_a_store_the_census_cannot_see_joins_but_is_flagged():
    si = S.ScriptIndex(DONOR)
    dead = S.parse_row(_w(sid=1, uid=1, tag=3, ip=_ip(DONOR, 1, 3, 14), w="Bit", byte=1125, bit=9001,
                          old=0, new=1))
    j = si.join(dead)
    assert j.status == "store" and j.rel == 14 and not j.census   # after RET: no CFG path reaches it


def test_every_write_operator_is_classified():
    """A new exprsem WRITE op must be placed: a literal-lvalue store, the member-list putv family, or not a
    variable store at all. Anything else would silently read as "stores nothing"."""
    member = {n for n in WRITE_OPS if n.endswith(("_A", "_E"))}
    assert WRITE_OPS == set(S._LVALUE_DEPTH) | member | S._NOT_A_VARIABLE_STORE
    assert not set(S._LVALUE_DEPTH) & member


# ======================================================================= fork alignment
def test_a_prepend_and_a_same_length_remap_align_to_the_donor():
    fork, donor = S.ScriptIndex(FORK), S.ScriptIndex(DONOR)
    assert S.align_function(fork, donor, 0, 0) == 8               # the [startup] stamp
    assert S.align_function(fork, donor, 0, 10) == 0              # untouched
    assert S.align_function(fork, donor, 1, 3) == 0               # Field(552) -> Field(30823), same length
    rewritten = S.ScriptIndex(_eb([(0, "SET({Global.Int16[9] const(1) B_LET B_EXPR_END})\nRET()")], NPC))
    assert S.align_function(rewritten, donor, 0, 0) is None      # nothing lines up: the fork's own function
    assert S.align_function(fork, donor, 5, 0) is None


# ======================================================================= digests + the N-vs-N comparison
def _stock_run(extra=()):
    return [_e("arm"),
            _w(ip=_ip(DONOR, 0, 0, 0)),                                          # Int16[9] = 1582
            _w(ip=_ip(DONOR, 0, 0, 8), w="Bit", byte=1100, bit=8800, old=0, new=1),
            _w(sid=1, uid=1, tag=3, ip=_ip(DONOR, 1, 3, 0), w="Bit", byte=1125, bit=9000, old=0, new=1),
            _w(ip=_ip(DONOR, 0, 0, 16), w="Bit", byte=23, bit=191, old=1, new=0),  # masked (boot_scratch)
            _w(src="harness", sid=-1, uid=-1, lvl=-1, ip=-1, tag=-1, w="Byte", byte=236, old=0, new=15),
            _w(src="cs", sid=-1, uid=-1, lvl=-1, ip=-1, tag=-1, w="Byte", byte=600, old=0, new=2),
            _r(100, 0, 9), *extra, _e("off")]


def _fork_run(extra=()):
    fk = dict(fld=30823, don=552)
    return [_e("arm", **fk),
            _w(ip=_ip(FORK, 0, 0, 0), w="UInt16", byte=0, old=0, new=3115, **fk),   # the prepend
            _w(ip=_ip(FORK, 0, 0, 8), **fk),                                          # donor +0
            _w(ip=_ip(FORK, 0, 0, 16), w="Bit", byte=1100, bit=8800, old=0, new=1, **fk),
            _w(src="cs", sid=-1, uid=-1, lvl=-1, ip=-1, tag=-1, w="Byte", byte=600, old=0, new=2, **fk),
            _w(ip=_ip(FORK, 0, 0, 3), w="Byte", byte=40, old=0, new=1, **fk),        # not a boundary
            *extra, _e("off", **fk)]


def _sources():
    """The stock side resolves only the donor (never the install); the fork side its own build first."""
    stock = {552: S.ScriptIndex(DONOR, field_id=552)}.get
    fork = S.mod_script_source([], fallback=stock, explicit={30823: FORK})
    return stock, fork


def test_every_diff_category_lands_where_it_belongs():
    stock, fork = _sources()
    dead = _w(sid=1, uid=1, tag=3, ip=_ip(DONOR, 1, 3, 14), w="Bit", byte=1125, bit=9001, old=0, new=1)
    sd = [S.digest(f"stock{i}", _rows(*_stock_run([dead] if i < 2 else [])), scripts=stock) for i in range(3)]
    fd = [S.digest(f"fork{i}", _rows(*_fork_run()), scripts=fork, donor_scripts=stock) for i in range(3)]
    c = S.compare(sd, fd)
    sig = lambda keys: [(k.sid, k.tag, k.off, k.target, k.value) for k in keys]      # noqa: E731
    assert sig(c.stock_only) == [(1, 3, 0, "Global.Bit[9000]", 1)]
    assert sig(c.fork_only) == [(0, 0, -8, "Global.UInt16[0]", 3115)]
    assert sig(c.unstable) == [(1, 3, 14, "Global.Bit[9001]", 1)]
    assert sorted(sig(c.matched)) == sorted([(-1, -1, -1, "Global.Byte[600]", 2), (0, 0, 0, "Global.Int16[9]", 1582),
                                             (0, 0, 8, "Global.Bit[8800]", 1)])
    assert c.residue == {100: (3, 0)}
    gaps = {k.target: c.seen[k].gap for k in c.census_gaps}
    assert set(gaps) == {"Global.Byte[600]", "Global.Bit[9001]"}
    assert "setVarManually" in gaps["Global.Byte[600]"] and "census does not count" in gaps["Global.Bit[9001]"]
    assert all(len(d.failures) == 1 and "instruction boundary" in d.failures[0][1] for d in fd)
    assert all(d.harness == 1 and d.masked == {"boot_scratch": 1} for d in sd)
    text = S.report(c)
    for head in ("STOCK ONLY (1) -- in 3/3 stock runs, 0/3 fork runs", "FORK ONLY (1) -- in 0/3 stock runs, 3/3", "UNSTABLE (1)",
                 "RESIDUE (1 byte(s)", "CENSUS GAPS (2)", "JOIN FAILURES (3)"):
        assert head in text, head
    assert "552 e0 " in text and " -8 [the fork's prepend]" in text
    assert "SET({Global.Bit[9000] const(1) B_LET B_EXPR_END})" in text
    assert "stock masked (story noise, flags.story_noise_bits): boot_scratch 3" in text


def test_a_suppressed_count_adds_its_last_value_to_its_own_fields_site():
    stock, _fork = _sources()
    w = _w(ip=_ip(DONOR, 0, 0, 0))
    d = S.digest("one", _rows(_e("arm"), w, _c(w, 40, 1600), _e("off")), scripts=stock)
    assert sorted(k.value for k in d.keys) == [1582, 1600]
    # sibling fields share one (sid, tag, ip) -- Dali's Bit[2102] store in 350/352/.../358 and 450 -- and a field
    # change opens no epoch: the engine keys the site by field, so each field's store and count are its own
    other = {**w, "fld": 553, "don": 553}
    si = S.ScriptIndex(DONOR)
    rows = _rows(_e("arm"), w, other, _c(w, 5, 1600), _c(other, 3, 1601), _e("off"))
    [ep] = S.epochs(rows)
    assert sorted((s.key[0], s.suppressed, s.last) for s in ep.sites.values()) == [(552, 5, 1600), (553, 3, 1601)]
    d = S.digest("two", rows, scripts={552: si, 553: si}.get)
    assert sorted((k.donor, k.value) for k in d.keys) == [(552, 1582), (552, 1600), (553, 1582), (553, 1601)]


def test_a_fork_with_no_donor_row_is_keyed_through_the_override():
    stock, fork = _sources()
    rows = _rows(_e("arm", fld=30823, don=30823), _w(ip=_ip(FORK, 0, 0, 8), fld=30823, don=30823),
                 _e("off", fld=30823, don=30823))
    bare = S.digest("bare", rows, scripts=fork, donor_scripts=stock)
    assert [k.donor for k in bare.keys] == [30823] and bare.notes    # no stock .eb for "donor" 30823
    fixed = S.digest("fixed", rows, scripts=fork, donor_scripts=stock, donors={30823: 552})
    [k] = fixed.keys
    assert (k.donor, k.off, k.aligned) == (552, 0, True)


def test_battle_and_addition_rows_keep_the_engines_attribution_as_census_gaps():
    stock, _fork = _sources()
    d = S.digest("x", _rows(_e("arm"), _w(m=2, sid=3, uid=3, tag=5, ip=77),
                            _w(add=1, tag=-1, ip=4), _e("off")), scripts=stock)
    assert {(k.m, k.tag, k.off) for k in d.keys} == {(2, 5, 77), (1, -1, 4)}
    assert all(o.gap for o in d.keys.values()) and not d.failures


# ======================================================================= where the scripts come from
def test_the_fork_script_comes_from_the_mod_root_that_registers_it(tmp_path):
    from ff9mapkit.config import ModLayout
    a, b = tmp_path / "A", tmp_path / "B"
    for root in (a, b):
        root.mkdir()
    (a / "DictionaryPatch.txt").write_text("FieldScene 30823 11 552 MYFORK 30823\n", encoding="utf-8")
    path = ModLayout(a).eb_path("us", "EVT_MYFORK.eb.bytes")
    path.parent.mkdir(parents=True)
    path.write_bytes(FORK)
    assert S.mod_registrations(a) == {30823: "MYFORK"}
    src = S.mod_script_source([a, b], fallback=lambda fid: "stock")
    assert src(30823).data == FORK and src(552) == "stock"
    (b / "DictionaryPatch.txt").write_text("FieldScene 30823 11 552 OTHER 30823\n", encoding="utf-8")
    with pytest.raises(S.TraceError, match="registered by 2 mod folders"):
        S.mod_script_source([a, b])(30823)


def test_a_mod_folder_overriding_a_stock_script_is_named(tmp_path):
    from ff9mapkit.config import ModLayout
    from ff9mapkit.extract import ID_TO_EVT
    path = ModLayout(tmp_path).eb_path("us", f"{ID_TO_EVT[70]}.eb.bytes")
    path.parent.mkdir(parents=True)
    path.write_bytes(DONOR)
    assert S.stock_overrides(70, [tmp_path]) == [tmp_path] and S.stock_overrides(552, [tmp_path]) == []


def test_the_fork_side_joins_a_stock_field_against_the_override_the_game_ran(tmp_path):
    """Field 70 (New Game) is overridden on the live install: a fork run through it ran the mod folder's
    bytes, and joining it against the install's would mint false join failures."""
    from ff9mapkit.config import ModLayout
    from ff9mapkit.extract import ID_TO_EVT
    a, b = tmp_path / "A", tmp_path / "B"
    path = ModLayout(a).eb_path("us", f"{ID_TO_EVT[70]}.eb.bytes")
    path.parent.mkdir(parents=True)
    path.write_bytes(FORK)
    b.mkdir()
    src = S.mod_script_source([a, b], fallback=lambda fid: "stock")
    assert src(70).data == FORK and src(552) == "stock"
    other = ModLayout(b).eb_path("us", f"{ID_TO_EVT[70]}.eb.bytes")
    other.parent.mkdir(parents=True)
    other.write_bytes(DONOR)
    with pytest.raises(S.TraceError, match="overridden by 2 mod folders"):
        S.mod_script_source([a, b])(70)


def test_the_cli_reports_both_sides_and_strict_fails_on_stock_only(tmp_path, capsys):
    (tmp_path / "donor.eb").write_bytes(DONOR)
    (tmp_path / "fork.eb").write_bytes(FORK)
    runs = []
    for name, rows in (("s1", _stock_run()), ("f1", _fork_run())):
        (tmp_path / name).mkdir()
        (tmp_path / name / "story.jsonl").write_text(_text(*rows), encoding="utf-8")
        runs.append(str(tmp_path / name))
    argv = ["story-trace", runs[0], "--script", f"552={tmp_path / 'donor.eb'}", "--fork", runs[1],
            "--fork-script", f"30823={tmp_path / 'fork.eb'}", "--fork-root", str(tmp_path / "none")]
    assert cli.main(argv) == 0
    out = capsys.readouterr().out
    assert "STOCK ONLY (1) -- in 1/1 stock runs, 0/1 fork runs" in out and "s1/story.jsonl" in out
    assert cli.main(argv + ["--strict"]) == 1
    assert cli.main(["story-trace", runs[0], "--script", f"552={tmp_path / 'donor.eb'}",
                     "--fork-root", str(tmp_path / "none")]) == 0
    assert "WRITES -- s1/story.jsonl" in capsys.readouterr().out
    (tmp_path / "bad.jsonl").write_text(_text(_e("arm"), {**_w(), "k": "z"}), encoding="utf-8")
    assert cli.main(["story-trace", str(tmp_path / "bad.jsonl"), "--fork-root", str(tmp_path)]) == 1
    assert "unknown row kind 'z'" in capsys.readouterr().err


def test_the_cli_counts_each_run_in_a_file_and_strict_fails_a_cut_one(tmp_path, capsys):
    (tmp_path / "donor.eb").write_bytes(DONOR)
    (tmp_path / "fork.eb").write_bytes(FORK)
    dead = _w(sid=1, uid=1, tag=3, ip=_ip(DONOR, 1, 3, 14), w="Bit", byte=1125, bit=9001, old=0, new=1)
    for name, rows in (("two", [*_stock_run([dead]), *_stock_run()]), ("f1", _fork_run()),
                       ("cut", _stock_run()[:2])):
        (tmp_path / name).mkdir()
        (tmp_path / name / "story.jsonl").write_text(_text(*rows), encoding="utf-8")
    base = ["--script", f"552={tmp_path / 'donor.eb'}", "--fork-root", str(tmp_path / "none")]
    fork = ["--fork", str(tmp_path / "f1"), "--fork-script", f"30823={tmp_path / 'fork.eb'}"]
    # two runs in one file are two runs on the side: the key only the first reached is UNSTABLE, not STOCK ONLY
    assert cli.main(["story-trace", str(tmp_path / "two"), *base, *fork]) == 0
    got = capsys.readouterr()
    assert "holds 2 traced runs" in got.err and "stock x2 vs fork x1" in got.out
    assert "STOCK ONLY (1) -- in 2/2 stock runs" in got.out and "UNSTABLE (1)" in got.out
    assert "two/story.jsonl#1" in got.out and "two/story.jsonl#2" in got.out
    assert cli.main(["story-trace", str(tmp_path / "two") + "#2", *base]) == 0
    assert "story trace: 1 run(s)" in capsys.readouterr().out
    assert cli.main(["story-trace", str(tmp_path / "two") + "#3", *base]) == 1
    assert "holds 2 traced run(s)" in capsys.readouterr().err
    # a cut stock run (the tracer faulted) is bannered, and --strict fails it even with STOCK ONLY empty
    assert cli.main(["story-trace", str(tmp_path / "cut"), *base, *fork]) == 0
    assert "!! 1 run(s) INCOMPLETE" in capsys.readouterr().out
    assert cli.main(["story-trace", str(tmp_path / "cut"), *base, *fork, "--strict"]) == 1


def test_the_cli_names_the_override_each_side_ran(tmp_path, capsys):
    from ff9mapkit.config import ModLayout
    from ff9mapkit.extract import ID_TO_EVT
    root = tmp_path / "mod"
    path = ModLayout(root).eb_path("us", f"{ID_TO_EVT[70]}.eb.bytes")
    path.parent.mkdir(parents=True)
    path.write_bytes(FORK)
    (tmp_path / "donor.eb").write_bytes(DONOR)
    at70 = dict(fld=70, don=70)
    (tmp_path / "f.jsonl").write_text(_text(_e("arm", **at70), _w(ip=_ip(FORK, 0, 0, 8), **at70),
                                            _e("off", **at70)), encoding="utf-8")
    # the same rows on both sides: the stock side is pinned to the donor's bytes (--script), where +8 is
    # another store; the fork side must find the override the game ran, where +8 IS this store
    argv = ["story-trace", str(tmp_path / "f.jsonl"), "--fork", str(tmp_path / "f.jsonl"),
            "--script", f"70={tmp_path / 'donor.eb'}", "--fork-root", str(root)]
    assert cli.main(argv) == 0
    got = capsys.readouterr()
    assert "the fork side's field 70 joins against" in got.err and "WARN" not in got.err
    assert "JOIN FAILURES (1)" in got.out and "not Global.Int16[9]" in got.out   # the stock side's, alone
    assert "FORK ONLY (1)" in got.out and "Global.Int16[9] = 1582" in got.out


# ======================================================================= real bytes (install-gated)
@pytest.fixture(scope="module")
def lindblum_552():
    try:
        from ff9mapkit.extract import EventBundle
        data = EventBundle().eb_for_id(552)
    except Exception:                                            # noqa: BLE001 -- no install here
        data = None
    if not data:
        warnings.warn(
            "the story-trace JOIN went UNVERIFIED against real bytes in this run: the game install's field "
            "event bundle is not readable here. Run in the MAIN repo / on the machine with the install.",
            UserWarning)
        pytest.skip("game install unavailable (field 552's .eb)")
    return data


def test_the_join_lands_on_stock_552_main_init_stores(lindblum_552):
    """Lindblum 552 (the rung-0 calibration field): Main_Init's literal stores join at their eb-src offsets,
    each a census site; the byte-23 boot scratch it clears is masked; a non-store offset fails."""
    si = S.ScriptIndex(lindblum_552, field_id=552)
    main = si.eb.entries[0].func_by_tag(0)
    items = {rel: t for rel, t in cmdasm.disassemble_items(lindblum_552, main.abs_start, main.abs_end)
             if rel is not None}
    stores = [(rel, t) for rel, t in items.items() if t.startswith("SET({Global.") and " B_LET " in t]
    assert len(stores) >= 5
    ip0 = main.abs_start - si.eb.entries[0].abs_start
    checked = 0
    for rel, text in stores:
        var = text[len("SET({"):].split()[0]                      # Global.Int16[9]
        width, idx = var[len("Global."):].rstrip("]").split("[")
        idx = int(idx)
        bit = width in S.BIT_WIDTHS
        row = S.parse_row(_w(ip=ip0 + rel, w=width, byte=idx >> 3 if bit else idx, bit=idx if bit else -1,
                             old=0, new=1))
        j = si.join(row, donor=552)
        assert (j.status, j.rel, j.text, j.census) == ("store", rel, text, True), (rel, text, j)
        checked += 1
        if var == "Global.Bit[191]":
            assert S.noise_regions(row) == ("boot_scratch",)
    assert checked == len(stores)
    jmp = next(rel for rel, t in items.items() if t.startswith("JMP_IFNOT"))
    assert si.join(S.parse_row(_w(ip=ip0 + jmp))).status == "fail"


def test_the_kits_own_startup_prepend_aligns_on_real_bytes(lindblum_552):
    """build._apply_startup's emitter (a once-guarded seed + SC stamp, prepended to Main_Init) shifts every
    later function in the file; per-function suffix alignment must put every donor write back on the donor's
    key, and key the stamp itself inside the prepend."""
    from ff9mapkit.content.startup import inject_startup

    fork = inject_startup(lindblum_552, [(8800, 1)], 3115, once_flag=12200)
    donor, forked = S.ScriptIndex(lindblum_552, field_id=552), S.ScriptIndex(fork, field_id=30823)
    prefix = len(fork) - len(lindblum_552)
    for e in donor.eb.entries:
        for f in e.funcs:
            assert S.align_function(forked, donor, e.index, f.tag) == (prefix if (e.index, f.tag) == (0, 0) else 0)
    main = donor.eb.entries[0].func_by_tag(0)
    ip0 = main.abs_start - donor.eb.entries[0].abs_start           # the fork's Main_Init starts where it did
    rows = _rows(_e("arm", fld=30823), _w(ip=ip0 + prefix + 51, new=1582, fld=30823),   # Int16[9] = 1582
                 _e("off", fld=30823))
    d = S.digest("fork", rows, scripts={30823: forked}.get, donor_scripts={552: donor}.get)
    [k] = d.keys
    assert (k.donor, k.sid, k.tag, k.off, k.aligned) == (552, 0, 0, 51, True)
