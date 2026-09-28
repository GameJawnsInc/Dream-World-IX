"""``storytrace`` -- the kit side of the story-write trace (memoria-patch s88; studies/story-trace/PLAN.md).

What these pin, offline: the proto-1 row contract is ENFORCED (an unknown kind, a missing/extra field, a string
number, a value the engine cannot emit -- each an error naming its line, never a skipped row); epochs segment
the rows and every suppressed count lands on the site it belongs to; the story-noise mask is the kit's one mask
(flags.story_noise_bits) with the per-width rule; THE JOIN lands an ``eb`` row on the store instruction that
wrote it or reports why it cannot, never a guess; a fork's prepend and a same-length operand remap align to
the donor; and every diff category of the N-vs-N comparison. Rung 3's step 0: a chain's MEMBER set cuts
the fork side's SEAM (its rows in a real non-member field) out of the matched / STOCK ONLY keys and names
the crossing; WRITERS names who wrote each stock value; a word store changing a byte outside the variable
stock writes there is a NEIGHBOUR-BYTE CLOBBER; a prepend stamping a value every stock run writes itself is
PRE-EMPTED. Without a member set the reports are byte-for-byte rung 2's.

Synthetic scripts are assembled from eb-src text (``cmdasm.assemble_block``), so each offset below is one a
reader can check against the source. The real-bytes tests (field 552, and the Dali fields a real stock tour
ran -- ``fixtures/story_rung3s1_dali.jsonl``, rung 3 step 1's archived trace) warn and skip without an
install -- the worktree skip trap, said out loud.
"""

from __future__ import annotations

import json
import struct
import warnings
from pathlib import Path

import pytest

from ff9mapkit import cli, flags
from ff9mapkit import storytrace as S
from ff9mapkit.eb import EbScript, cmdasm
from ff9mapkit.eb.exprsem import WRITE_OPS
from ff9mapkit.eb.model import pack_entry

COMMON = dict(f=100, p=7, m=1, fld=552, don=552, sc=3115)
FIXTURES = Path(__file__).parent / "fixtures"


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


def test_the_cli_takes_the_fork_sides_member_set_and_strict_fails_a_seam(tmp_path, capsys):
    for name, data in (("donor.eb", DONOR), ("other.eb", OTHER), ("fork.eb", FORK)):
        (tmp_path / name).write_bytes(data)
    (tmp_path / "s.jsonl").write_text(_text(*_tour(False)), encoding="utf-8")
    (tmp_path / "f.jsonl").write_text(_text(*_tour(True)), encoding="utf-8")
    base = ["story-trace", str(tmp_path / "s.jsonl"), "--script", f"552={tmp_path / 'donor.eb'}",
            "--script", f"553={tmp_path / 'other.eb'}", "--fork-root", str(tmp_path / "none")]
    fork = ["--fork", str(tmp_path / "f.jsonl"), "--fork-script", f"30823={tmp_path / 'fork.eb'}"]
    # no member set: the seam rows match stock, today's report, and --strict has nothing to fail
    assert cli.main(base + fork + ["--strict"]) == 0
    out = capsys.readouterr().out
    assert "SEAM" not in out and "matched in every run of both sides: 4 key(s)\n" in out
    assert cli.main(base + fork + ["--member", "30823=552"]) == 0
    out = capsys.readouterr().out
    assert "-- 553 reached only across a seam from member(552), fork 1/1" in out
    assert "  Global.Bit[9002] := 1 <- {553}   -- no member's donor writes it" in out
    assert cli.main(base + fork + ["--member", "30823=552", "--strict"]) == 1        # the seam is a defect
    assert cli.main(base + ["--member", "30823=552"]) == 1
    assert "--member names the FORK side's chain" in capsys.readouterr().err
    assert cli.main(base + fork + ["--member", "30823=552,30823=553"]) == 1
    assert "--member gives field 30823 two values" in capsys.readouterr().err
    assert cli.main(base + ["--writers"]) == 0
    assert "  Global.Bit[9002] := 1 <- {553}\n" in capsys.readouterr().out
    # the full index keeps the member set's mark: the values no member's donor writes lead it, and say so
    assert cli.main(base + fork + ["--member", "30823=552", "--writers"]) == 0
    out = capsys.readouterr().out
    assert ("WRITERS (4; 2 written only outside the members) -- every donor that wrote each value in the stock "
            "runs\n  Global.Byte[13] := 2 <- {553}   -- no member's donor writes it\n"
            "  Global.Bit[9002] := 1 <- {553}   -- no member's donor writes it\n") in out


def test_strict_fails_a_member_whose_rows_name_another_donor(tmp_path, capsys):
    """With --member the SET keys a member's rows, so a deploy missing its ForkDonorPatch row (every row then
    says don == fld) compares clean -- --strict must still fail it: the run did not exercise the deploy named."""
    for name, data in (("donor.eb", DONOR), ("other.eb", OTHER), ("fork.eb", FORK)):
        (tmp_path / name).write_bytes(data)
    (tmp_path / "s.jsonl").write_text(_text(*_tour(False)), encoding="utf-8")
    argv = ["story-trace", str(tmp_path / "s.jsonl"), "--script", f"552={tmp_path / 'donor.eb'}",
            "--script", f"553={tmp_path / 'other.eb'}", "--fork-root", str(tmp_path / "none"),
            "--fork-script", f"30823={tmp_path / 'fork.eb'}", "--fork-script", f"30824={tmp_path / 'other.eb'}",
            "--member", "30823=552,30824=553", "--strict", "--fork"]
    for don, want in ((552, 0), (30823, 1)):
        (tmp_path / "f.jsonl").write_text(_text(*_tour(True, into=30824, don=don)), encoding="utf-8")
        assert cli.main(argv + [str(tmp_path / "f.jsonl")]) == want, don
        out = capsys.readouterr().out
        assert "matched in every run of both sides: 4 key(s)" in out and "STOCK ONLY (0)" in out
        assert ("member 30823: its rows name donor 30823 (no ForkDonorPatch row)" in out) == bool(want)


# ======================================================================= today's report, pinned
#: the report the "every diff category" comparison printed BEFORE members/seams/writers/clobbers existed --
#: every section populated, so a change to any line of a no-member-set report fails here
NO_MEMBERS_REPORT = """\
story trace: stock x3 vs fork x3
  stock0: 1 epoch(s) [arm], 7 write rows (+0 suppressed), 5 story keys
  stock1: 1 epoch(s) [arm], 7 write rows (+0 suppressed), 5 story keys
  stock2: 1 epoch(s) [arm], 6 write rows (+0 suppressed), 4 story keys
  fork0: 1 epoch(s) [arm], 5 write rows (+0 suppressed), 4 story keys
  fork1: 1 epoch(s) [arm], 5 write rows (+0 suppressed), 4 story keys
  fork2: 1 epoch(s) [arm], 5 write rows (+0 suppressed), 4 story keys
  stock masked (story noise, flags.story_noise_bits): boot_scratch 3
  stock harness pokes (the seed, never compared): 3 rows
  matched in every run of both sides: 3 key(s)

STOCK ONLY (1) -- in 3/3 stock runs, 0/3 fork runs
  552 e1 Action trigger (tag 3) +0  Global.Bit[9000] = 1   SET({Global.Bit[9000] const(1) B_LET B_EXPR_END})

FORK ONLY (1) -- in 0/3 stock runs, 3/3 fork runs
  552 e0 Field startup (tag 0) -8 [the fork's prepend]  Global.UInt16[0] = 3115   SET({Global.UInt16[0] const(3115) B_LET B_EXPR_END})

UNSTABLE (1)
  552 e1 Action trigger (tag 3) +14  Global.Bit[9001] = 1   SET({Global.Bit[9001] const(1) B_LET B_EXPR_END})   stock 2/3 fork 0/3

RESIDUE (1 byte(s) changed with no hooked store)
  byte 100 (NaviMode): stock 3/3 fork 0/3

CENSUS GAPS (2)
  552 C#  Global.Byte[600] = 2   stock 3/3 fork 3/3 -- a C# writer through setVarManually -- no script position
  552 e1 Action trigger (tag 3) +14  Global.Bit[9001] = 1   SET({Global.Bit[9001] const(1) B_LET B_EXPR_END})   stock 2/3 fork 0/3 -- a store the census does not count (unreachable per the CFG, not the statement's lead variable, or not a SET)

JOIN FAILURES (3)
  fork0 line 6: field 30823 e0 tag 0 ip 13 Global.Byte[40] = 1 -- +3 is not an instruction boundary of tag 0
  fork1 line 6: field 30823 e0 tag 0 ip 13 Global.Byte[40] = 1 -- +3 is not an instruction boundary of tag 0
  fork2 line 6: field 30823 e0 tag 0 ip 13 Global.Byte[40] = 1 -- +3 is not an instruction boundary of tag 0
"""


def test_without_a_member_set_the_report_is_todays_byte_for_byte():
    """Rung 3's step 0 adds sections; a comparison with no member set (and no clobber, no ``writers``) must
    print exactly what rung 2 read -- the one-side report too."""
    stock, fork = _sources()
    dead = _w(sid=1, uid=1, tag=3, ip=_ip(DONOR, 1, 3, 14), w="Bit", byte=1125, bit=9001, old=0, new=1)
    sd = [S.digest(f"stock{i}", _rows(*_stock_run([dead] if i < 2 else [])), scripts=stock) for i in range(3)]
    fd = [S.digest(f"fork{i}", _rows(*_fork_run()), scripts=fork, donor_scripts=stock) for i in range(3)]
    c = S.compare(sd, fd)
    assert S.report(c) == NO_MEMBERS_REPORT
    assert not c.clobbers and not c.across_seam and not c.seam_only and not c.seams
    text = S.report_runs(sd)
    assert "WRITERS" not in text and "SEAM" not in text and text.startswith("story trace: 3 run(s)\n")


# ======================================================================= members + seams (rung 3 step 0)
# Field 553 stands for Dali's 450: a REAL field the chain did not fork. Its Main_Init writes Byte[13] (+0);
# its walk-in trigger writes the "ping" Bit[9002] (+0) and leaves; entry 2 writes Bit[9000] (+0) -- the value
# 552's talk handler writes too, so WRITERS has two donors to name -- and the ping again (+9), a second site.
OTHER = _eb([(0, "SET({Global.Byte[13] const(2) B_LET B_EXPR_END})\nRET()")],
            [(2, "SET({Global.Bit[9002] const(1) B_LET B_EXPR_END})\nField(552)\nRET()")],
            [(2, "SET({Global.Bit[9000] const(1) B_LET B_EXPR_END})\n"
                 "SET({Global.Bit[9002] const(1) B_LET B_EXPR_END})\nRET()")])
MEMBERS = {30823: 552}


def _seam_sources(explicit=None):
    stock = {552: S.ScriptIndex(DONOR, field_id=552), 553: S.ScriptIndex(OTHER, field_id=553),
             70: S.ScriptIndex(DONOR, field_id=70)}.get
    return stock, S.mod_script_source([], fallback=stock, explicit={30823: FORK, **(explicit or {})})


def _tour(fork: bool, *, into=None, don=552) -> list:
    """One tour: 552's Main_Init, its talk handler (whose store is the last before the door), then 553 --
    its Main_Init and its ping. ``fork``: 552 runs as the member 30823 (its rows name ``don``); 553 is the
    real field, or the fork id ``into`` when the chain forked it too."""
    m = dict(fld=30823, don=don) if fork else dict(fld=552, don=552)
    o = dict(fld=into, don=553) if into else dict(fld=553, don=553)
    base = FORK if fork else DONOR
    return [_e("arm", fld=70, don=70),
            _w(ip=_ip(base, 0, 0, 8 if fork else 0), f=200, **m),                            # Int16[9] = 1582
            _w(sid=1, uid=1, tag=3, ip=_ip(base, 1, 3, 0), w="Bit", byte=1125, bit=9000, old=0, new=1, f=210, **m),
            _w(ip=_ip(OTHER, 0, 0, 0), w="Byte", byte=13, old=0, new=2, f=500, **o),
            _w(sid=1, uid=1, tag=2, ip=_ip(OTHER, 1, 2, 0), w="Bit", byte=1125, bit=9002, old=0, new=1, f=520, **o),
            _e("off", **o)]


def _sig(keys) -> list:
    return [(k.donor, k.sid, k.tag, k.off, k.target, k.value) for k in keys]


def test_a_fork_run_across_a_seam_is_named_and_never_matched():
    """F0's shape: the member's exit leads into a real field. Its rows there key exactly like stock's (a key
    carries no field) -- so they are kept apart, the crossing is named, and the stock keys reached only
    there say so in plain words."""
    stock, fork = _seam_sources()
    sd = [S.digest("stock", _rows(*_tour(False)), scripts=stock)]
    fd = [S.digest("fork", _rows(*_tour(True)), scripts=fork, donor_scripts=stock, members=MEMBERS)]
    c = S.compare(sd, fd, members=MEMBERS)
    assert _sig(c.matched) == [(552, 0, 0, 0, "Global.Int16[9]", 1582), (552, 1, 3, 0, "Global.Bit[9000]", 1)]
    assert c.stock_only == [] and c.fork_only == [] and c.unstable == [] and c.seam_only == []
    assert _sig(c.across_seam) == [(553, 0, 0, 0, "Global.Byte[13]", 2), (553, 1, 2, 0, "Global.Bit[9002]", 1)]
    [s] = fd[0].seams
    assert (s.frm, s.donor, s.to, s.frame, s.line, s.fields) == (30823, 552, 553, 500, 4, [553])
    assert s.exit.target == "Global.Bit[9000]" and s.exit_where == "e1 Action trigger (tag 3) +0"
    assert not fd[0].notes and not fd[0].failures
    text = S.report(c)
    assert ("\nSEAMS (1) -- a fork run left its members into the real game; every row from there is the real "
            "game's own, kept apart from the keys above\n"
            "  member(552) [fork 30823] -> real 553: 1/1 fork runs; first seam row at frame 500 (fork line 4); "
            "the member's last write before it: e1 Action trigger (tag 3) +0  Global.Bit[9000] = 1\n"
            "    real fields seen across it: 553\n") in text
    assert ("  553 e1 Contact trigger (tag 2) +0  Global.Bit[9002] = 1   SET({Global.Bit[9002] const(1) B_LET "
            "B_EXPR_END})   -- 553 reached only across a seam from member(552), fork 1/1") in text
    assert "REACHED ONLY ACROSS A SEAM (2)" in text and "SEAM ONLY (0)" in text
    assert "  matched in every run of both sides: 2 key(s) (fork MEMBERS only" in text
    assert "  fork: 1 epoch(s) [arm], 4 write rows (+0 suppressed), 2 story keys, 2 across 1 seam crossing(s)" in text
    # WRITERS: the values the members never wrote, and who did -- 553 is no member's donor
    assert ("WRITERS (2; 2 written only outside the members) -- who wrote each STOCK ONLY / across-seam value "
            "in the stock runs\n  Global.Byte[13] := 2 <- {553}   -- no member's donor writes it\n"
            "  Global.Bit[9002] := 1 <- {553}   -- no member's donor writes it\n") in text


def test_without_the_member_set_the_same_rows_merge_silently_and_as_a_member_they_are_clean():
    """The two mutants rung 3 registered: the seam rows read with no member set MATCH stock (the silent merge
    the member set exists to stop), and the same visit as a MEMBER comes out clean, no seam at all."""
    stock, fork = _seam_sources()
    sd = [S.digest("stock", _rows(*_tour(False)), scripts=stock)]
    bare = S.digest("fork", _rows(*_tour(True)), scripts=fork, donor_scripts=stock)
    c = S.compare(sd, [bare])
    assert len(c.matched) == 4 and not c.stock_only and not bare.seams and not bare.seam_keys
    assert "SEAM" not in S.report(c) and "WRITERS" not in S.report(c)
    both = {30823: 552, 30824: 553}
    _stock, fork2 = _seam_sources({30824: OTHER})
    d = S.digest("fork", _rows(*_tour(True, into=30824)), scripts=fork2, donor_scripts=stock, members=both)
    c = S.compare(sd, [d], members=both)
    assert len(c.matched) == 4 and not (c.stock_only or c.fork_only or c.across_seam or c.seam_only or d.seams)
    assert "\nSEAMS (0) -- " in S.report(c) and "\nWRITERS (0) -- " in S.report(c)


def test_a_seam_ends_at_a_member_and_only_real_fields_after_one_are_across_it():
    """Rows in a real field BEFORE the run stood in a member (New Game's 70) are the fork's own; a custom field
    that is no member (a hub) is the fork's own ground; back in a member, the run is inside again; and a count
    closing a seam site lands on the seam side, as its own suppressed value."""
    stock, fork = _seam_sources({30999: DONOR})
    m, o, hub = dict(fld=30823, don=552), dict(fld=553, don=553), dict(fld=30999, don=30999)
    ping = _w(ip=_ip(OTHER, 0, 0, 0), w="Byte", byte=13, old=0, new=2, **o)
    rows = _rows(_e("arm", fld=70, don=70),
                 _w(ip=_ip(DONOR, 0, 0, 0), fld=70, don=70),                                  # pre-member: own
                 _w(ip=_ip(FORK, 0, 0, 8), **m),
                 ping,                                                                         # across
                 _w(sid=1, uid=1, tag=3, ip=_ip(FORK, 1, 3, 0), w="Bit", byte=1125, bit=9000, old=0, new=1, **m),
                 _w(ip=_ip(DONOR, 0, 0, 0), **hub),                                            # a hub: own
                 _c(ping, 2, 3), _e("off", **hub))
    d = S.digest("fork", rows, scripts=fork, donor_scripts=stock, members=MEMBERS)
    assert [(s.frm, s.to, s.fields) for s in d.seams] == [(30823, 553, [553])]
    assert sorted((k.donor, k.target, k.value) for k in d.keys) == [
        (70, "Global.Int16[9]", 1582), (552, "Global.Bit[9000]", 1), (552, "Global.Int16[9]", 1582),
        (30999, "Global.Int16[9]", 1582)]
    assert sorted((k.donor, k.target, k.value, o.counted) for k, o in d.seam_keys.items()) == [
        (553, "Global.Byte[13]", 2, False), (553, "Global.Byte[13]", 3, True)]
    assert "no stock .eb for donor 30999" in d.notes[0]


def test_a_member_whose_rows_name_another_donor_is_noted_and_keyed_by_the_member_set():
    """R3-DONOR: an engine with no ForkDonorPatch row writes don == fld -- the member set still keys the rows
    under the donor, and the run says the deploy is missing its row."""
    stock, fork = _seam_sources()
    d = S.digest("fork", _rows(*_tour(True, don=30823)), scripts=fork, donor_scripts=stock, members=MEMBERS)
    assert d.notes == ["member 30823: its rows name donor 30823 (no ForkDonorPatch row), the member set says 552"]
    assert {k.donor for k in d.keys} == {552}


def test_compare_refuses_a_member_set_its_runs_were_not_digested_with():
    """The seam is cut in digest(), where the rows are in the engine's order: a comparison claiming a member
    set over runs digested without it would merge the very rows it exists to keep apart."""
    stock, fork = _seam_sources()
    sd = [S.digest("stock", _rows(*_tour(False)), scripts=stock)]
    bare = S.digest("fork", _rows(*_tour(True)), scripts=fork, donor_scripts=stock)
    with pytest.raises(S.TraceError, match="fork: digested with member set none, compared with"):
        S.compare(sd, [bare], members=MEMBERS)
    fd = [S.digest("fork", _rows(*_tour(True)), scripts=fork, donor_scripts=stock, members=MEMBERS)]
    with pytest.raises(S.TraceError, match="compared with none"):
        S.compare(sd, fd)
    odd = S.digest("stock", _rows(*_tour(False)), scripts=stock, members=MEMBERS)
    with pytest.raises(S.TraceError, match="a stock run digested with a member set"):
        S.compare([odd], fd, members=MEMBERS)


# ======================================================================= WRITERS
def test_writers_names_every_donor_of_each_stock_value_across_the_runs():
    """``Global.Bit[9000] := 1 <- {552, 553 (1/3)}``: counted once per RUN (553 writing the ping at a second
    site in run 0 is still one run), a donor seen in fewer than all runs says in how many -- and the full
    index sorts by the byte each variable starts at."""
    stock, _fork = _seam_sources()
    extra = [_w(sid=2, uid=2, tag=2, ip=_ip(OTHER, 2, 2, 0), w="Bit", byte=1125, bit=9000, old=0, new=1,
                fld=553, don=553),
             _w(sid=2, uid=2, tag=2, ip=_ip(OTHER, 2, 2, 9), w="Bit", byte=1125, bit=9002, old=1, new=1,
                fld=553, don=553)]
    runs = [S.digest(f"s{i}", _rows(*_tour(False)[:-1], *(extra if i == 0 else []), _e("off")), scripts=stock)
            for i in range(3)]
    assert len({k for k in runs[0].keys if (k.target, k.value) == ("Global.Bit[9002]", 1)}) == 2
    idx = S.writers(runs)
    assert idx[("Global.Bit[9000]", 1)] == {552: 3, 553: 1} and idx[("Global.Bit[9002]", 1)] == {553: 3}
    text = S.report_runs(runs, writers=True)
    assert [ln for ln in text.splitlines() if " := " in ln] == [
        "  Global.Int16[9] := 1582 <- {552}", "  Global.Byte[13] := 2 <- {553}",
        "  Global.Bit[9000] := 1 <- {552, 553 (1/3)}", "  Global.Bit[9002] := 1 <- {553}"]
    assert "WRITERS (4) -- every donor that wrote each value in these runs" in text
    assert "WRITERS" not in S.report_runs(runs)
    fork = [S.digest("f", _rows(*_tour(False)), scripts=stock)]
    assert "  Global.Bit[9000] := 1 <- {552, 553 (1/3)}" in S.report(S.compare(runs, fork), writers=True)


# ======================================================================= NEIGHBOUR-BYTE CLOBBERS
def test_byte_changes_read_a_value_the_way_the_engine_lays_it_down():
    row = lambda **kw: S.parse_row(_w(**kw))                                   # noqa: E731
    assert row(w="UInt16", byte=0, old=2540, new=2600).byte_changes() == {0: (236, 40), 1: (9, 10)}
    assert row(old=-1, new=1483).byte_changes() == {9: (255, 203), 10: (255, 5)}      # two's complement
    assert row(w="UInt16", byte=296, old=256, new=192).byte_changes() == {296: (0, 192), 297: (1, 0)}
    assert row(w="UInt16", byte=296, old=192, new=192).byte_changes() == {}
    assert row(w="Int24", byte=40, old=-1, new=0).byte_changes() == {40: (255, 0), 41: (255, 0), 42: (255, 0)}
    assert row(w="Bit", byte=1100, bit=8800, old=0, new=1).byte_changes() == {}


def test_outside_a_variable_takes_stock_evidence_and_names_it():
    both = {(296, "SByte"): {"Global.SByte[296]"}, (297, "UInt16"): {"Global.UInt16[297]"},
            (239, "Int16"): {"Global.Int16[239]"}}
    assert S.outside_target(both, 296, 297) == ("the stock runs store byte 297 as Global.UInt16[297], and "
                                                "byte 296 only as Global.SByte[296]")
    assert S.outside_target({(296, "SByte"): {"Global.SByte[296]"}}, 296, 297) == \
        "the stock runs store byte 296 only as Global.SByte[296]"
    assert S.outside_target({(297, "UInt16"): {"Global.UInt16[297]"}}, 296, 297) == \
        "the stock runs store byte 297 as Global.UInt16[297]"
    assert S.outside_target(both, 239, 240) == ""               # stock's own word at 239 covers 240
    assert S.outside_target({}, 296, 297) == ""                 # no evidence, no claim
    # stock ALSO writes a word at 296: its own shape covers 297, however else stock writes 297
    assert S.outside_target({**both, (296, "UInt16"): {"Global.UInt16[296]"}}, 296, 297) == ""


def test_only_a_neighbour_byte_is_ever_a_clobber_never_the_stores_own_start():
    """A store's start byte is its own target by definition: even where stock writes that byte only as the
    tail of another variable (Int16[295]), the word at 296 clobbers nothing there -- only 297 is asked about."""
    key = S.WriteKey(552, 1, "eb", 0, 0, -17, "Global.UInt16[296]", 192)
    row = S.parse_row(_w(w="UInt16", byte=296, old=256, new=192))
    fork = S.RunDigest("f", [], keys={key: S.Observed(key, row, changed={296: (0, 192, 2), 297: (1, 0, 2)})})
    tail = S.RunDigest("s", [], stores={(295, "Int16"): {"Global.Int16[295]"}})
    assert S.find_clobbers([tail], [fork]) == []
    hub = S.RunDigest("s", [], stores={(297, "UInt16"): {"Global.UInt16[297]"}})
    assert [(cl.byte, cl.old, cl.new) for cl in S.find_clobbers([tail, hub], [fork])] == [(297, 1, 0)]


# Dali's shape in miniature: the stock field writes byte 296 as a signed byte (the ping countdown), the word at
# 297 (the hub word) in another function, and Int16[239] (the room code); its fork's [startup] prepends the
# round-4 seed's two 16-bit words.
CLOB = [(0, "SET({Global.SByte[296] const(65472) B_LET B_EXPR_END})\n"
            "SET({Global.Int16[239] const(2) B_LET B_EXPR_END})\nRET()"),
        (1, "SET({Global.UInt16[297] const(1) B_LET B_EXPR_END})\nRET()")]
CLOB_DONOR = _eb(CLOB)
CLOB_FORK = _eb([(0, "SET({Global.UInt16[296] const(192) B_LET B_EXPR_END})\n"
                     "SET({Global.UInt16[239] const(6) B_LET B_EXPR_END})\n" + CLOB[0][1]), CLOB[1]])


def _rel(data: bytes, sid: int, tag: int, text: str) -> int:
    """The function offset of the instruction eb-src prints as ``text``."""
    f = EbScript.from_bytes(data).entries[sid].func_by_tag(tag)
    return next(rel for rel, t in cmdasm.disassemble_items(data, f.abs_start, f.abs_end) if t == text)


def test_a_word_store_that_changes_its_neighbour_byte_is_a_clobber_flagged_in_fork_only():
    """The round-4 seed wrote byte 296 = 192 as a 16-bit word, zeroing hub byte 297. The trace records no
    reads, so the gate it killed never shows -- only this store's old/new do: byte 297 went 1 -> 0, and stock
    stores 297 as its own word and 296 as a byte."""
    stock = {552: S.ScriptIndex(CLOB_DONOR, field_id=552)}.get
    fork = S.mod_script_source([], fallback=stock, explicit={30826: CLOB_FORK})
    at = lambda data, text, tag=0: _ip(data, 0, tag, _rel(data, 0, tag, text))           # noqa: E731
    sbyte = "SET({Global.SByte[296] const(65472) B_LET B_EXPR_END})"
    room = "SET({Global.Int16[239] const(2) B_LET B_EXPR_END})"
    word = "SET({Global.UInt16[296] const(192) B_LET B_EXPR_END})"
    seed = "SET({Global.UInt16[239] const(6) B_LET B_EXPR_END})"
    stock_rows = [_e("arm"),
                  _w(ip=at(CLOB_DONOR, sbyte), w="SByte", byte=296, old=0, new=-64),
                  _w(ip=at(CLOB_DONOR, room), byte=239, old=0, new=2),
                  _w(tag=1, ip=at(CLOB_DONOR, "SET({Global.UInt16[297] const(1) B_LET B_EXPR_END})", 1),
                     w="UInt16", byte=297, old=0, new=1),
                  _e("off")]
    fk = dict(fld=30826, don=552)

    def fork_run(word_old, seed_old, *counted):
        first = _w(ip=at(CLOB_FORK, word), w="UInt16", byte=296, old=word_old, new=192, **fk)
        return [_e("arm", **fk), first,
                _w(ip=at(CLOB_FORK, seed), w="UInt16", byte=239, old=seed_old, new=6, **fk),
                _w(ip=at(CLOB_FORK, sbyte), w="SByte", byte=296, old=-64, new=-64, **fk),
                _w(ip=at(CLOB_FORK, room), byte=239, old=6, new=2, **fk),
                *(_c(first, n, last) for n, last in counted), _e("off", **fk)]

    sd = [S.digest("stock", _rows(*stock_rows), scripts=stock)]
    # run A: 297 held the hub's 1 -> clobbered; run B: already 0 -> the word changes no neighbour. The seed's
    # word at 239 changes byte 240 in run B, but stock's own Int16[239] covers 240: never a clobber. Run A's
    # word site also counts a suppressed 200 -- a value with no old, which never borrows the first row's bytes
    fd = [S.digest("forkA", _rows(*fork_run(256, 0, (3, 200))), scripts=fork, donor_scripts=stock),
          S.digest("forkB", _rows(*fork_run(192, 256)), scripts=fork, donor_scripts=stock)]
    c = S.compare(sd, fd)
    assert [(k.target, k.value) for k in c.unstable] == [("Global.UInt16[296]", 200)]
    [cl] = c.clobbers
    assert (cl.key.target, cl.key.value, cl.byte, cl.old, cl.new, cl.runs, cl.label, cl.line) == \
        ("Global.UInt16[296]", 192, 297, 1, 0, 1, "forkA", 2)
    assert cl.key.off < 0 and cl.key in c.fork_only
    text = S.report(c)
    fork_only = text.split("\nFORK ONLY")[1].split("\n\n")[0].splitlines()[1:]
    flagged = [ln for ln in fork_only if "!!" in ln]                     # the seed's 239 word is not
    assert len(fork_only) == 2 and len(flagged) == 1 and "Global.UInt16[296] = 192" in flagged[0]
    assert flagged[0].endswith("   !! NEIGHBOUR-BYTE CLOBBER: byte 297 1 -> 0")
    assert ("NEIGHBOUR-BYTE CLOBBERS (1) -- a fork store changed a byte outside the variable the stock runs "
            "write at its start\n  552 e0 Field startup (tag 0) -17 [the fork's prepend]  Global.UInt16[296] = "
            "192   SET({Global.UInt16[296] const(192) B_LET B_EXPR_END})   changes byte 297: 1 -> 0 in 1/2 "
            "fork runs (first forkA line 2) -- the stock runs store byte 297 as Global.UInt16[297], and byte "
            "296 only as Global.SByte[296]\n") in text
    # no stock evidence for byte 297 (a stock side that never ran the hub word): no claim
    bare = [S.digest("stock", _rows(*stock_rows[:1], *stock_rows[1:3], stock_rows[-1]), scripts=stock)]
    assert [cl.why for cl in S.compare(bare, fd).clobbers] == [
        "the stock runs store byte 296 only as Global.SByte[296]"]
    assert S.compare([S.digest("stock", _rows(_e("arm"), _e("off")), scripts=stock)], fd).clobbers == []


def test_a_word_stock_itself_stores_there_is_never_a_clobber():
    """A verbatim fork runs stock's own wide stores, old/new and all: stock storing that word puts its own
    (start, width) in the layout, which covers every byte the word touches -- so the fork is never flagged for
    it, even where the word zeroes a byte stock also stores as another variable."""
    word = "SET({Global.UInt16[296] const(192) B_LET B_EXPR_END})"
    hub = "SET({Global.UInt16[297] const(1) B_LET B_EXPR_END})"
    data = _eb([(0, word + "\nRET()"), (1, hub + "\nRET()")])
    stock = {552: S.ScriptIndex(data, field_id=552)}.get
    fork = S.mod_script_source([], fallback=stock, explicit={30826: data})

    def run(**fk):
        return _rows(_e("arm", **fk), _w(tag=1, ip=_ip(data, 0, 1, 0), w="UInt16", byte=297, old=0, new=1, **fk),
                     _w(ip=_ip(data, 0, 0, 0), w="UInt16", byte=296, old=256, new=192, **fk), _e("off", **fk))

    c = S.compare([S.digest("stock", run(), scripts=stock)],
                  [S.digest("fork", run(fld=30826, don=552), scripts=fork, donor_scripts=stock)])
    [k] = [k for k in c.matched if k.target == "Global.UInt16[296]"]
    assert c.seen[k].changed == {296: (0, 192, 3), 297: (1, 0, 3)} and c.clobbers == []


# ======================================================================= PRE-EMPTED
# The seed's shape in miniature: the fork's prepend stamps Bit[9000] := 1 -- the value stock's talk handler writes
# itself (entry 1, +0) -- ahead of the SC stamp.
LATCH = "SET({Global.Bit[9000] const(1) B_LET B_EXPR_END})\n"
LATCH_FORK = _eb([(0, LATCH + PREPEND + MAIN[0][1]), MAIN[1]], [(3, NPC[0][1].replace("Field(552)", "Field(30823)"))])


def test_a_prepend_stamping_a_value_stock_writes_itself_is_pre_empted():
    """Round 5's fix, named by the trace: the prepend key is FORK ONLY by construction (a negative offset), so
    only beside the stock store of the same value does it say what it is -- the seed doing the story's work."""
    stock = {552: S.ScriptIndex(DONOR, field_id=552)}.get
    fork = S.mod_script_source([], fallback=stock, explicit={30823: LATCH_FORK})
    fk = dict(fld=30823, don=552)
    latch, sc = _rel(LATCH_FORK, 0, 0, LATCH.strip()), _rel(LATCH_FORK, 0, 0, PREPEND.strip())
    fork_run = [_e("arm", **fk),
                _w(ip=_ip(LATCH_FORK, 0, 0, latch), w="Bit", byte=1125, bit=9000, old=0, new=1, **fk),
                _w(ip=_ip(LATCH_FORK, 0, 0, sc), w="UInt16", byte=0, old=0, new=3115, **fk),
                _w(ip=_ip(LATCH_FORK, 0, 0, sc + 8), **fk), _e("off", **fk)]
    sd = [S.digest(f"stock{i}", _rows(*_stock_run()), scripts=stock) for i in range(3)]
    fd = [S.digest(f"fork{i}", _rows(*fork_run), scripts=fork, donor_scripts=stock) for i in range(2)]
    c = S.compare(sd, fd)
    assert [(k.target, k.value, k.off) for k in c.fork_only] == [("Global.Bit[9000]", 1, -17),
                                                                  ("Global.UInt16[0]", 3115, -8)]
    [p] = c.pre_empted                                           # SC 3115: no stock run writes it itself
    assert (p.target, p.value, [k.off for k in p.stamps]) == ("Global.Bit[9000]", 1, [-17])
    assert [(k.donor, k.sid, k.tag, k.off, n) for k, n in p.stock.items()] == [(552, 1, 3, 0, 3)]
    assert ("\nPRE-EMPTED (1) -- the fork's prepend stamps a value every stock run writes itself, at its own "
            "site: the seed does the story's work before the story does\n  Global.Bit[9000] := 1  stamped by "
            "the prepend in 1 donor(s) (552); stock writes it at 552 e1 Action trigger (tag 3) +0 (3/3)\n") \
        in S.report(c)
    # not in EVERY stock run: stock does not reliably write it, so nothing is pre-empted
    sd[2] = S.digest("stock2", _rows(*[r for r in _stock_run() if r.get("bit") != 9000]), scripts=stock)
    assert S.compare(sd, fd).pre_empted == [] and "PRE-EMPTED" not in S.report(S.compare(sd, fd))
    # a stamp in only some fork runs is UNSTABLE, not FORK ONLY: not pre-empted either
    sd[2] = S.digest("stock2", _rows(*_stock_run()), scripts=stock)
    fd[1] = S.digest("fork1", _rows(*fork_run[:1], *fork_run[2:]), scripts=fork, donor_scripts=stock)
    assert S.compare(sd, fd).pre_empted == []


# ======================================================================= fork-report's traced axis (rung 4)
def test_a_fields_share_is_every_category_cut_to_its_donor():
    """The share of 552 holds each of the comparison's categories whose key names 552, over the same runs;
    the whole comparison's totals come with it, so a clean field in a broken chain never reads clean."""
    stock, fork = _sources()
    dead = _w(sid=1, uid=1, tag=3, ip=_ip(DONOR, 1, 3, 14), w="Bit", byte=1125, bit=9001, old=0, new=1)
    other = _w(fld=553, don=553, ip=5, w="Byte", byte=13, old=0, new=2)          # no script: a join failure
    sd = [S.digest(f"stock{i}", _rows(*_stock_run([dead] if i < 2 else [])), scripts=stock) for i in range(3)]
    fd = [S.digest(f"fork{i}", _rows(*_fork_run([other] if i == 0 else [])), scripts=fork, donor_scripts=stock)
          for i in range(3)]
    sh = S.field_share(552, sd, fd)
    c = sh.comparison
    sig = lambda keys: [(k.sid, k.tag, k.off, k.target, k.value) for k in keys]      # noqa: E731
    assert sig(sh.stock_only) == sig(c.stock_only) == [(1, 3, 0, "Global.Bit[9000]", 1)]
    assert sig(sh.fork_only) == [(0, 0, -8, "Global.UInt16[0]", 3115)]
    assert sig(sh.unstable) == [(1, 3, 14, "Global.Bit[9001]", 1)]
    assert len(sh.matched) == 3 and len(sh.writes) == 5
    assert [(label, r.fld) for label, r, _why in sh.failures] == [("fork0", 30823), ("fork1", 30823), ("fork2", 30823)]
    assert sh.chain["STOCK ONLY"] == 1 and "SEAMS" not in sh.chain                  # no member set: no seams
    text = S.format_field_share(sh)
    assert text.startswith("  Story writes, TRACED -- field 552 (stock x3 vs fork x3)\n")
    for head in ("    matched in every run of both sides: 3 of the 5 key(s) the stock runs wrote here\n",
                 "    STOCK ONLY (1) -- in 3/3 stock runs, 0/3 fork runs: the fork never wrote these here\n",
                 "    FORK ONLY (1) -- in 0/3 stock runs, 3/3 fork runs", "    UNSTABLE (1) -- ",
                 "    JOIN FAILURES (3) -- rows written in field 552\n",
                 "    the whole comparison (every field): STOCK ONLY 1, FORK ONLY 1, UNSTABLE 1, "):
        assert head in text, head
    assert "552 e1 Action trigger (tag 3) +0  Global.Bit[9000] = 1   SET({Global.Bit[9000]" in text
    # 553's share: only the one fork run's orphan row wrote there -- its failure, nothing of 552's
    other_sh = S.field_share(553, sd, fd)
    assert other_sh.touched and other_sh.stock_only == other_sh.fork_only == other_sh.matched == []
    assert [(label, r.fld) for label, r, _why in other_sh.failures] == [("fork0", 553)]
    # a field no run wrote in: said so, never an empty clean-looking report
    none = S.field_share(70, sd, fd)
    assert not none.touched
    assert "no traced run, on either side, wrote in field 70" in S.format_field_share(none)


def test_a_fields_share_of_a_chain_names_its_member_its_seam_and_what_it_reached_only_across_one():
    """F0's shape, cut per field: 552 is the member and its exit is the seam; 553 is NO member, and every
    stock write in it the fork side made only in the REAL 553, across that seam."""
    stock, fork = _seam_sources()
    sd = [S.digest("stock", _rows(*_tour(False)), scripts=stock)]
    fd = [S.digest("fork", _rows(*_tour(True)), scripts=fork, donor_scripts=stock, members=MEMBERS)]
    member, real = S.field_share(552, sd, fd, members=MEMBERS), S.field_share(553, sd, fd, members=MEMBERS)
    assert member.members == [30823] and real.members == []
    assert _sig(member.matched) == [(552, 0, 0, 0, "Global.Int16[9]", 1582), (552, 1, 3, 0, "Global.Bit[9000]", 1)]
    assert member.across_seam == [] and member.stock_only == []
    assert _sig(real.across_seam) == [(553, 0, 0, 0, "Global.Byte[13]", 2), (553, 1, 2, 0, "Global.Bit[9002]", 1)]
    assert real.matched == [] and real.stock_only == []
    for sh in (member, real):                                   # the crossing leaves 552's member into 553
        [(s, labels)] = sh.seams
        assert (s.frm, s.donor, s.to, labels) == (30823, 552, 553, ["fork"])
    assert member.chain == real.chain == {"STOCK ONLY": 0, "FORK ONLY": 0, "UNSTABLE": 0, "SEAMS": 1,
                                          "REACHED ONLY ACROSS A SEAM": 2, "SEAM ONLY": 0,
                                          "NEIGHBOUR-BYTE CLOBBERS": 0, "PRE-EMPTED": 0}
    text = S.format_field_share(real, whole="WHOLE")
    assert text.startswith("  Story writes, TRACED -- field 553 (stock x1 vs fork x1; the fork side is a chain of "
                           "1 member(s), field 553 NO member of it)\n")
    assert ("    REACHED ONLY ACROSS A SEAM (2) -- in 1/1 stock runs, written by no fork member: the fork side "
            "reached them only in the REAL field 553\n") in text
    assert ("  553 e1 Contact trigger (tag 2) +0  Global.Bit[9002] = 1   SET({Global.Bit[9002] const(1) B_LET "
            "B_EXPR_END})   -- 553 reached only across a seam from member(552), fork 1/1\n") in text
    assert "      member(552) [fork 30823] -> real 553: 1/1 fork runs; real fields seen across it: 553\n" in text
    assert text.endswith("REACHED ONLY ACROSS A SEAM 2, SEAM ONLY 0, NEIGHBOUR-BYTE CLOBBERS 0, PRE-EMPTED 0 -- "
                         "print it whole with WHOLE\n")
    assert "field 552 its member 30823" in S.format_field_share(member)


def test_a_chain_read_with_no_member_set_is_named_where_its_rows_would_silently_match():
    """The same tour digested with no member set: the real 553's rows MATCH stock (the silent merge) -- so the
    share says a fork run left its own fields into the real game and the chain went unnamed. Named, it is
    quiet; and a fork run that never stood in a field of its own crosses nothing."""
    stock, fork = _seam_sources()
    sd = [S.digest("stock", _rows(*_tour(False)), scripts=stock)]
    bare = [S.digest("fork", _rows(*_tour(True)), scripts=fork, donor_scripts=stock)]
    sh = S.field_share(553, sd, bare)
    assert len(sh.matched) == 2 and sh.unnamed_crossings == [("fork", 30823, 553)]
    assert ("    !! 1 fork run(s) left their own fields into the real game (fork: 30823 -> real 553) and no member "
            "set names the chain: their rows there MATCH stock as if the fork wrote them -- name the chain's "
            "members (--member FORK=DONOR,...) to keep them apart\n") in S.format_field_share(sh)
    named = [S.digest("fork", _rows(*_tour(True)), scripts=fork, donor_scripts=stock, members=MEMBERS)]
    assert S.field_share(553, sd, named, members=MEMBERS).unnamed_crossings == []
    stock_side = [S.digest("fork", _rows(*_tour(False)), scripts=stock)]          # real fields only
    assert S.field_share(553, sd, stock_side).unnamed_crossings == []


def test_a_fields_share_names_the_prepend_it_pre_empts_and_the_clobber_it_makes():
    """PRE-EMPTED and CLOBBERS are cut to the field too: the stamp in 552's member and the stock store it
    pre-empts are both 552's; a field with neither shows neither."""
    stock = {552: S.ScriptIndex(DONOR, field_id=552)}.get
    fork = S.mod_script_source([], fallback=stock, explicit={30823: LATCH_FORK})
    fk = dict(fld=30823, don=552)
    latch, sc = _rel(LATCH_FORK, 0, 0, LATCH.strip()), _rel(LATCH_FORK, 0, 0, PREPEND.strip())
    fork_run = [_e("arm", **fk),
                _w(ip=_ip(LATCH_FORK, 0, 0, latch), w="Bit", byte=1125, bit=9000, old=0, new=1, **fk),
                _w(ip=_ip(LATCH_FORK, 0, 0, sc), w="UInt16", byte=0, old=0, new=3115, **fk),
                _w(ip=_ip(LATCH_FORK, 0, 0, sc + 8), **fk), _e("off", **fk)]
    sd = [S.digest(f"stock{i}", _rows(*_stock_run()), scripts=stock) for i in range(2)]
    fd = [S.digest(f"fork{i}", _rows(*fork_run), scripts=fork, donor_scripts=stock) for i in range(2)]
    sh = S.field_share(552, sd, fd)
    [p] = sh.pre_empted
    assert (p.target, p.value) == ("Global.Bit[9000]", 1)
    assert ("    PRE-EMPTED (1) -- the fork's prepend stamps a value every stock run writes itself: the seed does "
            "the story's work before the story does\n      Global.Bit[9000] := 1  stamped in donor(s) 552; stock "
            "writes it at 552 e1 Action trigger (tag 3) +0 (2/2)\n") in S.format_field_share(sh)
    assert S.field_share(553, sd, fd).pre_empted == []


def test_a_field_alone_lists_the_stock_walks_writes_against_the_static_candidates():
    """No fork side: the stock walk's writes in the field, each in how many runs, in the order first written --
    and fork-report's static candidates split into written on these walks / never run (no evidence) / and
    the traced writes no candidate lists."""
    stock, _fork = _sources()
    dead = _w(sid=1, uid=1, tag=3, ip=_ip(DONOR, 1, 3, 14), w="Bit", byte=1125, bit=9001, old=0, new=1)
    sd = [S.digest(f"stock{i}", _rows(*_stock_run([dead] if i == 1 else [])), scripts=stock) for i in range(3)]
    sh = S.field_share(552, sd)
    assert sh.comparison is None and sh.chain == {} and sh.stock_only == [] and sh.seams == []
    assert [(k.target, k.value, n) for k, _o, n in sh.writes] == [
        ("Global.Int16[9]", 1582, 3), ("Global.Bit[8800]", 1, 3), ("Global.Bit[9000]", 1, 3),
        ("Global.Byte[600]", 2, 3), ("Global.Bit[9001]", 1, 1)]
    text = S.format_field_share(sh, static=[(8800, None), (9001, None), (9005, "somewhere")])
    assert text.startswith("  Story writes, TRACED -- field 552 (stock x3)\n    WRITES (5) -- the stock walk's "
                           "story writes in field 552, in the order first written; n/3 = the stock runs that "
                           "wrote it\n      3/3  552 e0 Field startup (tag 0) +0  Global.Int16[9] = 1582")
    assert "      1/3  552 e1 Action trigger (tag 3) +14  Global.Bit[9001] = 1" in text
    assert ("    static candidates (the Story writes line above): 3 -- written on these walks: 8800, 9001 (1/3)\n"
            "      not written on them: 9005  (these walks never ran the store -- no evidence either way)\n"
            "    written, and no static candidate: Global.Int16[9] (1582), Global.Byte[600] (2), Global.Bit[9000] "
            "(1)  (") in text
    assert "whole comparison" not in text and "STOCK ONLY" not in text
    assert "static candidates" not in S.format_field_share(sh)            # no static list given: none shown


def test_a_cut_run_heads_a_fields_share_and_the_share_refuses_what_it_cannot_read():
    stock, fork = _sources()
    cut = S.digest("cut", _rows(*_stock_run()[:-1]), scripts=stock)
    text = S.format_field_share(S.field_share(552, [cut]))
    assert text.splitlines()[1] == ("    !! 1 run(s) INCOMPLETE -- a key such a run never reached may lie past its "
                                    "cut, so no absence below is evidence")
    fd = [S.digest("fork", _rows(*_fork_run()), scripts=fork, donor_scripts=stock)]
    with pytest.raises(S.TraceError, match="needs the stock side's runs"):
        S.field_share(552, [], fd)
    with pytest.raises(S.TraceError, match="member set names the FORK side's chain"):
        S.field_share(552, [cut], members=MEMBERS)


def test_fork_report_takes_the_traces_and_refuses_a_trace_option_with_nothing_to_read(tmp_path, capsys,
                                                                                         monkeypatch):
    """The CLI: `--trace` (and `--fork-trace`) put the traced axis under the report, loaded exactly as
    `story-trace` loads them; without --trace the report is today's byte for byte; a trace option with no
    --trace, or with --explain, is refused -- never silently ignored."""
    from ff9mapkit import forkreport as FR

    monkeypatch.setattr(FR, "resolve_field_id", lambda token, game=None: int(token))
    monkeypatch.setattr(FR, "analyze", lambda fid, game=None: FR.analyze_eb(DONOR, field_id=fid))
    (tmp_path / "donor.eb").write_bytes(DONOR)
    (tmp_path / "fork.eb").write_bytes(FORK)
    for name, rows in (("s1", _stock_run()), ("f1", _fork_run())):
        (tmp_path / name).mkdir()
        (tmp_path / name / "story.jsonl").write_text(_text(*rows), encoding="utf-8")
    none = ["--fork-root", str(tmp_path / "none")]
    stock = ["--trace", str(tmp_path / "s1"), "--script", f"552={tmp_path / 'donor.eb'}"]
    fork = ["--fork-trace", str(tmp_path / "f1"), "--fork-script", f"30823={tmp_path / 'fork.eb'}"]
    assert cli.main(["fork-report", "552"]) == 0
    plain = capsys.readouterr().out
    assert "TRACED" not in plain and "Story writes  : sets 3 story flag(s): 8800, 9000, 9001" in plain
    assert cli.main(["fork-report", "552", *stock, *fork, *none]) == 0
    out = capsys.readouterr().out
    assert out.startswith(plain.rstrip("\n") + "\n\n  Story writes, TRACED -- field 552 (stock x1 vs fork x1)\n")
    assert "    STOCK ONLY (1) -- in 1/1 stock runs, 0/1 fork runs" in out
    assert ("-- print it whole with `ff9mapkit story-trace <the --trace runs> --fork <the --fork-trace runs>` and "
            "the same --member/--donor/--script/--fork-script/--fork-root\n") in out
    assert cli.main(["fork-report", "552", *stock, *none]) == 0
    out = capsys.readouterr().out
    assert "    WRITES (4) -- the stock walk's story writes in field 552" in out
    assert "static candidates (the Story writes line above): 3 -- written on these walks: 8800, 9000\n" in out
    for argv, err in ((["fork-report", "552", *fork], "--fork-trace, --fork-script read story traces"),
                      (["fork-report", "552", "--member", "30823=552"], "--member read story traces"),
                      (["fork-report", "552", *stock, "--explain"], "--explain prints no report"),
                      (["fork-report", "552", *stock, *none, "--member", "30823=552"],
                       "--member names the FORK side's chain -- give its runs with --fork-trace")):
        assert cli.main(argv) == 2, argv
        assert err in capsys.readouterr().err, argv


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


#: rung 2's report as it read on the day (studies/story-trace/PLAN.md "Rung 2 result"), before rung 3 step 0
RUNG2_REPORT = """\
story trace: stock 552 x3 vs verbatim fork 30830 x3
  stock#1: 1 epoch(s) [arm], 15 write rows (+0 suppressed), 11 story keys
  stock#3: 1 epoch(s) [arm], 15 write rows (+0 suppressed), 11 story keys
  stock#5: 1 epoch(s) [arm], 15 write rows (+0 suppressed), 11 story keys
  fork#2: 1 epoch(s) [arm], 15 write rows (+0 suppressed), 11 story keys
  fork#4: 1 epoch(s) [arm], 15 write rows (+0 suppressed), 11 story keys
  fork#6: 1 epoch(s) [arm], 15 write rows (+0 suppressed), 11 story keys
  stock masked (story noise, flags.story_noise_bits): boot_scratch 3, field_menu_guard 3
  stock harness pokes (the seed, never compared): 6 rows
  fork masked (story noise, flags.story_noise_bits): boot_scratch 3, field_menu_guard 3
  fork harness pokes (the seed, never compared): 6 rows
  matched in every run of both sides: 11 key(s)

STOCK ONLY (0) -- in 3/3 stock runs, 0/3 fork runs

FORK ONLY (0) -- in 0/3 stock runs, 3/3 fork runs

UNSTABLE (0)

RESIDUE (3 byte(s) changed with no hooked store)
  byte 0 (ScenarioCounter): stock 3/3 fork 3/3
  byte 1 (ScenarioCounter): stock 3/3 fork 3/3
  byte 2 (FieldEntrance): stock 3/3 fork 3/3

CENSUS GAPS (0)

JOIN FAILURES (0)
"""


def test_the_rung_2_report_is_unchanged_on_its_real_rows(lindblum_552):
    """The pin rung 3's step 0 promised: stock 552 x3 vs its verbatim fork 30830 x3, from rung 2's archived
    trace (fixtures/story_rung2_552.jsonl), prints the report rung 2 read, byte for byte. The fork side joins
    against the stock bytes: a verbatim fork's Field() remap is same-length, so its rows land where they did."""
    runs = S.split_runs(S.read_trace(FIXTURES / "story_rung2_552.jsonl"))
    stock = {552: S.ScriptIndex(lindblum_552, field_id=552)}.get
    fork = S.mod_script_source([], fallback=stock, explicit={30830: lindblum_552})
    ds = [S.digest(f"{'fork' if i % 2 else 'stock'}#{i + 1}", run, scripts=fork if i % 2 else stock,
                   donor_scripts=stock) for i, run in enumerate(runs)]
    c = S.compare(ds[0::2], ds[1::2])
    assert S.report(c, title="story trace: stock 552 x3 vs verbatim fork 30830 x3") == RUNG2_REPORT


# ======================================================================= the Dali retrodiction on REAL rows
DALI = range(350, 360)          # the members' donors: import-chain 351 --whole-zone (357 is never entered)


@pytest.fixture(scope="module")
def dali():
    """Rung 3 step 1's REAL stock run -- an unattended blind tour of stock Dali from 359 @ SC 2540 until the
    story left 2600 (fixtures/story_rung3s1_dali.jsonl, the archived trace) -- and the install's scripts."""
    src = S.stock_script_source()
    try:
        ok = all(src(fid) is not None for fid in (*DALI, 450))
    except Exception:                                            # noqa: BLE001 -- no install here
        ok = False
    if not ok:
        warnings.warn(
            "the story-trace Dali retrodiction went UNVERIFIED against real bytes in this run: the game install's "
            "field event bundle is not readable here. Run in the MAIN repo / on the machine with the install.",
            UserWarning)
        pytest.skip("game install unavailable (Dali's .eb)")
    text = (FIXTURES / "story_rung3s1_dali.jsonl").read_text(encoding="utf-8")
    return [json.loads(ln) for ln in text.splitlines() if ln.strip()], src


def _members(donors) -> dict:
    return {30831 + i: d for i, d in enumerate(donors)}


def _chain_run(objs, members, *, until=None) -> list:
    """The stock rows as a verbatim chain would have the engine write them: a row in a member's donor field
    runs in the member (``fld`` the fork id, ``don`` still the donor, as ForkDonorPatch has it) -- up to the
    first row in ``until``, the real field a missing member's exit walks into. From there the run is the real
    game's, row for row. A count row follows its site."""
    fork_of = {d: f for f, d in members.items()}
    cut = next((i for i, o in enumerate(objs) if o["fld"] == until and o["k"] != "c"), len(objs))
    moved, out = set(), []
    for i, o in enumerate(objs):
        o = dict(o)
        site = tuple(o.get(k) for k in ("fld", "m", "src", "sid", "tag", "ip", "byte", "w", "bit"))
        if (o["k"] == "c" and site in moved) or (o["k"] != "c" and i < cut and o["fld"] in fork_of):
            if o["k"] == "w":
                moved.add(site)
            o["fld"] = fork_of[o["fld"]]
        out.append(o)
    return out


def _chain_digest(src, members, label, rows, explicit=None):
    fork = S.mod_script_source([], fallback=src, explicit={**{f: src(d).data for f, d in members.items()},
                                                            **(explicit or {})})
    return S.digest(label, S.parse_text(_text(*rows)), scripts=fork, donor_scripts=src, members=members)


def test_the_real_dali_tour_names_the_missing_member_with_no_script_read(dali):
    """R3-NULL-PRE, R3-SEAM and R3-PING offline, on the REAL stock rows: the chain today's import-chain builds
    (members 350-359, no 450: another FBG zone) walks the same tour. Up to the seam it writes what stock
    writes (STOCK ONLY empty); 350's exit takes it into the real 450, and the ping comes out as a stock key
    reached only across that seam, written by 450 alone -- PLAYTEST.md's hand-found defect, from the trace."""
    objs, src = dali
    members = _members(DALI)
    sd = S.digest("stock", S.parse_text(_text(*objs)), scripts=src)
    fd = _chain_digest(src, members, "F0", _chain_run(objs, members, until=450))
    c = S.compare([sd], [fd], members=members)
    assert not sd.failures and not fd.failures and not sd.incomplete and not fd.notes
    assert c.stock_only == [] and c.fork_only == [] and c.unstable == [] and c.seam_only == []
    [(s, labels)] = c.seams
    assert (s.frm, s.donor, s.to, s.frame, labels) == (30831, 350, 450, 19677, ["F0"])
    assert (s.exit.sid, s.exit.tag, s.exit.target, s.exit.new) == (32, 2, "Global.Int16[2]", 1)   # 350's door
    [ping] = [k for k in c.across_seam if (k.target, k.value) == ("Global.Bit[2102]", 1)]
    assert (ping.donor, ping.sid, ping.tag, c.seen[ping].row.ip) == (450, 19, 2, 89)   # PLAN.md: e19 tag 2 ip 89
    assert c.writers[("Global.Bit[2102]", 1)] == {450: 1}
    assert c.writers[("Global.Byte[8]", 125)][450] == 1        # two 450 sites write it: still one run
    text = S.report(c)
    assert ("Global.Bit[2102] = 1   SET({Global.Bit[2102] const(1) B_LET B_EXPR_END})   -- 450 reached only "
            "across a seam from member(350), fork 1/1") in text
    assert "\n  Global.Bit[2102] := 1 <- {450}   -- no member's donor writes it\n" in text
    assert "\n  member(350) [fork 30831] -> real 450: 1/1 fork runs; first seam row at frame 19677 " in text


def test_on_the_real_rows_no_member_set_merges_the_seam_and_450_as_a_member_is_clean(dali):
    """The registered mutants, on real rows: read with no member set, the real 450's ping MATCHES stock's --
    the chain looks whole; and the chain with 450 as a member (every Dali field forked) has no seam and
    matches stock key for key."""
    objs, src = dali
    sd = S.digest("stock", S.parse_text(_text(*objs)), scripts=src)
    members = _members(DALI)
    fork = S.mod_script_source([], fallback=src, explicit={f: src(d).data for f, d in members.items()})
    bare = S.digest("F0", S.parse_text(_text(*_chain_run(objs, members, until=450))), scripts=fork,
                    donor_scripts=src)
    c = S.compare([sd], [bare])
    assert not c.stock_only
    assert any((k.donor, k.target, k.value) == (450, "Global.Bit[2102]", 1) for k in c.matched)
    whole = _members([*DALI, 450])
    d = _chain_digest(src, whole, "F-whole", _chain_run(objs, whole))
    c = S.compare([sd], [d], members=whole)
    assert not (d.seams or c.stock_only or c.fork_only or c.unstable or c.across_seam or c.seam_only)
    assert len(c.matched) == len(sd.keys)


def test_the_round_4_seed_word_clobbers_hub_byte_297_on_the_real_rows(dali):
    """R3-LATCH's hidden half, offline: round 4 prepended SC 2600, the latches 2064/2075/2079 and the words
    239 = 6 and 296 = 192 to every member's Main_Init. Put that prepend (the kit's own inject_startup, no
    once-sentinel) on member 351's real bytes, its rows where the engine writes them -- first in 351, with
    byte 297 holding the 1 that 359 wrote -- and the stock runs' own widths name the clobber."""
    from ff9mapkit.content.startup import inject_startup
    from ff9mapkit.eb._exprtable import VAR_TYPE

    objs, src = dali
    members = _members(DALI)
    fid = next(f for f, d in members.items() if d == 351)
    donor = src(351)
    seeded = inject_startup(donor.data, [(2064, 1), (2075, 1), (2079, 1)], 2600, words=[(239, 6), (296, 192)])
    delta = len(seeded) - len(donor.data)
    e0 = donor.eb.entries[0]
    main_ip = e0.func_by_tag(0).abs_start - e0.abs_start
    rows = _chain_run(objs, members, until=450)
    for o in rows:                                  # entry 0 from Main_Init on moved down by the prepend
        if o["fld"] == fid and o.get("sid") == 0 and o["ip"] >= main_ip:
            o["ip"] += delta
    si = S.ScriptIndex(seeded)
    main = si.eb.entries[0].func_by_tag(0)
    first = next(i for i, o in enumerate(rows) if o["fld"] == fid)
    was = {"Global.UInt16[0]": (2540, 2600), "Global.UInt16[239]": (0, 6), "Global.UInt16[296]": (256, 192)}
    seed = []
    for ins in si.instrs(main.abs_start, main.abs_start + delta):
        [(_src, vt, idx)] = S.instruction_stores(seeded, ins)
        width = VAR_TYPE[vt]
        bit = width in S.BIT_WIDTHS
        old, new = was.get(f"Global.{width}[{idx}]", (0, 1))
        seed.append(_w(ip=ins.off - e0.abs_start, w=width, byte=idx >> 3 if bit else idx, bit=idx if bit else -1,
                       old=old, new=new, fld=fid, don=351, **{k: rows[first][k] for k in ("f", "p", "sc")}))
    sd = S.digest("stock", S.parse_text(_text(*objs)), scripts=src)
    fd = _chain_digest(src, members, "F4", [*rows[:first], *seed, *rows[first:]], explicit={fid: seeded})
    c = S.compare([sd], [fd], members=members)
    assert not fd.failures and c.stock_only == []
    assert sorted((k.target, k.value) for k in c.fork_only) == [
        ("Global.Bit[2064]", 1), ("Global.Bit[2075]", 1), ("Global.Bit[2079]", 1), ("Global.UInt16[0]", 2600),
        ("Global.UInt16[239]", 6), ("Global.UInt16[296]", 192)]
    assert all(k.donor == 351 and k.off < 0 for k in c.fork_only)           # every one the prepend's
    [cl] = c.clobbers                                                        # SC and 239: stock's own widths
    assert (cl.key.target, cl.key.value, cl.byte, cl.old, cl.new) == ("Global.UInt16[296]", 192, 297, 1, 0)
    assert cl.why == ("the stock runs store byte 297 as Global.UInt16[297], and byte 296 only as "
                      "Global.SByte[296]")
    [line] = [ln for ln in S.report(c).split("\nUNSTABLE")[0].splitlines() if "Global.UInt16[296] = 192" in ln]
    assert line.endswith("   !! NEIGHBOUR-BYTE CLOBBER: byte 297 1 -> 0")
    # and the latches' half: each one the seed stamps, stock writes itself -- 351's lobby exit sets 2064 on the
    # way out, the controller flips 2079/2075 where its count runs out (356 here), the wake stamps SC 2600
    got = {(p.target, p.value): sorted((k.donor, k.sid, k.tag, k.off) for k in p.stock) for p in c.pre_empted}
    assert got == {("Global.UInt16[0]", 2600): [(352, 17, 1, 4385)], ("Global.Bit[2064]", 1): [(351, 16, 2, 112)],
                   ("Global.Bit[2075]", 1): [(356, 2, 1, 315), (358, 4, 1, 98)],
                   ("Global.Bit[2079]", 1): [(356, 2, 1, 222)]}
    assert ("  Global.Bit[2064] := 1  stamped by the prepend in 1 donor(s) (351); stock writes it at 351 e16 "
            "Walk-in trigger (tag 2) +112 (1/1)\n") in S.report(c)


def test_fork_reports_traced_axis_names_450_on_the_real_rows(dali):
    """Rung 4 on real rows: today's chain (members 350-359, no 450) walks the real stock tour. fork-report 450's
    traced axis says the chain has no 450 and that every stock write in it -- the ping among them -- the fork
    side made only in the REAL 450, across member(350)'s seam; 350's own share is clean and names that seam."""
    objs, src = dali
    members = _members(DALI)
    sd = S.digest("stock", S.parse_text(_text(*objs)), scripts=src)
    fd = _chain_digest(src, members, "F0", _chain_run(objs, members, until=450))
    real, member = S.field_share(450, [sd], [fd], members=members), S.field_share(350, [sd], [fd], members=members)
    assert real.members == [] and real.stock_only == real.fork_only == real.matched == []
    assert {k for k, _o, _n in real.writes} == set(real.across_seam)             # every stock key in 450
    assert ("Global.Bit[2102]", 1) in {(k.target, k.value) for k in real.across_seam}
    assert member.members == [30831] and member.stock_only == member.fork_only == []
    assert [(s.frm, s.to) for s, _l in member.seams] == [(30831, 450)] == [(s.frm, s.to) for s, _l in real.seams]
    text = S.format_field_share(real)
    assert "field 450 NO member of it)" in text.splitlines()[0]
    assert ("  450 e19 Walk-in trigger (tag 2) +59  Global.Bit[2102] = 1   SET({Global.Bit[2102] const(1) B_LET "
            "B_EXPR_END})   -- 450 reached only across a seam from member(350), fork 1/1") in text
