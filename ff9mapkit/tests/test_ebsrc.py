"""`.ebs` whole-file round-trip (eb/ebsrc.py) — the eb-roundtrip arc's Rung 2/3 tests.

Offline tests drive KIT-AUTHORED synthetic .eb bytes (assembled here — zero Square-Enix
bytes), covering: the envelope grammar the Rung-1 census froze (interior + trailing empty
slots, zero-length funcs, loc/flags/pad, byte2, the name block), the adversarial-review
hardening (off= overrides for kit-edited layouts, the raw= entry escape hatch, the
EbSrcError-everywhere contract, BOM tolerance, hand-authored-source fixpoint), the Rung-4
comment enrichment (presentation only — every join must leave the bytes alone), and the
three CLI verbs. The install-gated sweep round-trips REAL binaries and reports its count
loudly — a partial corpus must never read as a full pass.
"""
import struct

import pytest

from ff9mapkit.eb import cmdasm
from ff9mapkit.eb.ebsrc import (EbSrcError, assemble_against, assemble_source, count_functions,
                                write_source)
from ff9mapkit.eb.model import EbScript

RET = b"\x04"


def _expr_scenario() -> bytes:
    return b"\x05\xDC\x00\x7F"                           # SET: push ScenarioCounter, end


def _switchex(default_rel: int, pairs) -> bytes:
    vals = [default_rel]
    for v, r in pairs:
        vals += [v, r]
    return bytes([0x06, len(pairs)]) + b"".join(struct.pack("<H", x) for x in vals)


def _window(txid: int) -> bytes:
    return bytes([0x1F, 0x00, 0, 0]) + struct.pack("<H", txid)       # WindowSync(u8, u8, txid u16)


def _jmp(rel: int) -> bytes:
    return b"\x01" + struct.pack("<h", rel)


def _eb_file(entries, *, name: bytes = b"", byte2: int = 2, slot_meta=None) -> bytes:
    """Assemble a synthetic multi-entry .eb. ``entries``: per slot either None (EMPTY) or a
    (etype, [(tag, body)]) pair. Empty-slot offs follow the census rule; ``slot_meta`` maps
    slot -> (loc, flags, pad) for non-empty slots."""
    slot_meta = slot_meta or {}
    blobs = []
    for e in entries:
        if e is None:
            blobs.append(None)
            continue
        etype, funcs = e
        fc = len(funcs)
        table, bodies, fpos = b"", b"", fc * 4
        for tag, body in funcs:
            table += struct.pack("<HH", tag, fpos)
            bodies += body
            fpos += len(body)
        blobs.append(bytes([etype, fc]) + table + bodies)
    head = bytearray(0x80)
    head[0:2] = b"EV"
    head[2] = byte2
    head[3] = len(blobs)
    nm = (name + bytes(124))[:124]
    head[4:0x80] = nm
    offs, pos = [], 8 * len(blobs)
    for b in blobs:
        if b is None:
            offs.append(None)
        else:
            offs.append(pos)
            pos += len(b)
    nonempty = [o for o in offs if o is not None]
    for i, o in enumerate(offs):
        if o is None:
            nxt = next((x for x in offs[i + 1:] if x is not None), None)
            offs[i] = nxt if nxt is not None else nonempty[-1]
    slots, out = b"", b""
    for i, b in enumerate(blobs):
        loc, flags, pad = slot_meta.get(i, (0, 0, 0))
        slots += struct.pack("<HHBBH", offs[i], len(b) if b else 0, loc, flags, pad)
        if b is not None:
            out += b
    return bytes(head) + slots + out


def _demo_eb(**kw) -> bytes:
    """Main entry (spawn-free init with a story-beat switch + a jump), an interior EMPTY, an
    object entry with a talk func and a ZERO-LENGTH placeholder func, then trailing EMPTIES.
    Layout of entry-0 func-0 (rel offsets): expr@0(4B), switch@4(12B, anchor 8), JMP@16(3B),
    RET@19, end 20. Switch arms hit real boundaries: default->16, 1900->19, 2005->20 (end)."""
    sw = _switchex(8, [(1900, 11), (2005, 12)])
    init = _expr_scenario() + sw + _jmp(-len(sw) - 3 - len(_expr_scenario())) + RET
    talk = _window(500) + RET
    return _eb_file(
        [
            (0, [(0, init), (1, RET)]),
            None,                                         # interior empty
            (2, [(0, RET), (3, talk), (7, b"")]),         # zero-length func 7
            None, None,                                   # trailing empties
        ],
        **kw,
    )


# --------------------------------------------------------------------- core round trip

def test_roundtrip_synthetic():
    data = _demo_eb(name=b"Test/Room\x00")
    src = write_source(data, title="synthetic demo")     # self-verifies internally
    assert assemble_source(src) == data
    assert "# synthetic demo" in src.splitlines()[0]


def test_canonical_emission_pins_grammar():
    """The writer's CANONICAL form is part of grammar v1: derived values are omitted. A
    format regression (emitting pad=0, off= on canonical entries, .byte2 2) breaks here."""
    src = write_source(_demo_eb())
    assert "pad=" not in src                              # all pads are 0 -> omitted
    assert "off=" not in src                              # fully canonical layout -> derived
    assert ".byte2" not in src                            # byte2 == 2 -> omitted
    assert "raw=" not in src                              # all entries structured
    meta = write_source(_demo_eb(byte2=7, slot_meta={2: (3, 1, 9)}))
    assert ".byte2 7" in meta and "pad=9" in meta and meta.count("pad=") == 1


def test_hand_authored_source_fixpoint():
    """Hand-written source (comments, blank lines, hex ints, loose spacing) assembles; the
    writer's decompile of that result is then a true fixpoint of assemble/write."""
    hand = (
        "\n# hand-authored\n.ebs 1\n\n.name " + "ab" * 124 + "\n"
        ".entry 0 type=0x0 loc=0 flags=0x0   # main\n"
        ".func 0\n"
        "  WindowSync(1, 128, 0x1F4)   # txid 500 in hex\n"
        "  RET()\n"
        ".entry 1 EMPTY\n"
    )
    data = assemble_source(hand)
    eb = EbScript.from_bytes(data)
    assert eb.entry_count == 2 and not eb.entries[0].empty and eb.entries[1].empty
    src = write_source(data)                              # normalized form
    assert assemble_source(src) == data
    assert write_source(assemble_source(src)) == src      # fixpoint of the normalized form


def test_parse_matches_model_view():
    data = _demo_eb(name=b"NM", byte2=7, slot_meta={2: (3, 1, 9)})
    src = write_source(data)
    assert ".entry 2 type=2 loc=3 flags=1 pad=9" in src
    assert src.count(".entry") == 5 and src.count("EMPTY") == 3
    eb = EbScript.from_bytes(assemble_source(src))
    assert [e.empty for e in eb.entries] == [False, True, False, True, True]
    assert [f.tag for f in eb.entries[2].funcs] == [0, 3, 7]
    assert eb.entries[2].funcs[2].length == 0            # the zero-length func survives


def test_name_block_preserved_verbatim():
    tail = b"jpname\x00\xa6\xf1\xb2\xba" + bytes(10)     # binary blob after a NUL (the jp shape)
    data = _demo_eb(name=b"Room\x00" + tail)
    src = write_source(data)
    assert assemble_source(src)[4:0x80] == data[4:0x80]


def test_bom_tolerated():
    src = write_source(_demo_eb())
    assert assemble_source(chr(0xFEFF) + src) == assemble_source(src)


# --------------------------------------------------------------------- kit-shaped layouts

def test_stale_empty_parked_off_roundtrips_with_override():
    """A kit length-changing edit leaves EMPTY parked offs stale (eb/edit.py fixups skip
    size-0 slots). The writer emits an explicit off= override and the file round-trips."""
    data = bytearray(_demo_eb())
    eb = EbScript.from_bytes(bytes(data))
    empt = next(e for e in eb.entries if e.empty)
    at = 0x80 + empt.index * 8
    data[at:at + 2] = struct.pack("<H", 12345)           # break the parked-off rule
    src = write_source(bytes(data))
    assert f".entry {empt.index} EMPTY off=12345" in src
    assert assemble_source(src) == bytes(data)


def test_out_of_order_physical_layout_roundtrips():
    """append_entry-class layouts: table order != physical order (a middle slot's body sits
    physically after a later slot's). The writer emits off= overrides and the file
    round-trips — no gap bytes involved, the bodies are merely swapped."""
    base = _demo_eb()
    eb = EbScript.from_bytes(base)
    e0, e2 = eb.entries[0], eb.entries[2]
    b0 = base[e0.abs_start:e0.abs_end]
    b2 = base[e2.abs_start:e2.abs_end]
    table_end = 0x80 + eb.entry_count * 8
    d = bytearray(base[:table_end]) + b2 + b0             # physical order: e2 then e0
    off2, off0 = table_end - 0x80, table_end - 0x80 + len(b2)
    for idx, off in ((0, off0), (2, off2)):
        at = 0x80 + idx * 8
        d[at:at + 2] = struct.pack("<H", off)
    at1 = 0x80 + 1 * 8                                    # interior empty: next non-empty = slot 2
    d[at1:at1 + 2] = struct.pack("<H", off2)
    for idx in (3, 4):                                    # trailing empties: last non-empty = slot 2
        at = 0x80 + idx * 8
        d[at:at + 2] = struct.pack("<H", off2)
    src = write_source(bytes(d))
    assert "off=" in src
    assert assemble_source(src) == bytes(d)


def test_blank_template_overhang_gap_roundtrips():
    """The kit's blank-template lineage: entry 0 DECLARES a size smaller than its func
    table's reach, so its Main_Loop body physically sits between entries — covered by no
    declared span. The writer must preserve those orphan bytes via a .gap record (the
    engine reads funcs by fpos and never consults the size: they are live code)."""
    base = _eb_file([(0, [(0, RET)]), (2, [(0, RET)])])
    d = bytearray(base)
    eb = EbScript.from_bytes(base)
    e0 = eb.entries[0]
    # shrink entry 0's declared size by 0 but push entry 1 out, leaving a 4-byte hole whose
    # bytes are live: extend the file layout by hand — entry 1 moves +4, hole holds a RET
    e1 = eb.entries[1]
    blob1 = base[e1.abs_start:e1.abs_end]
    d = bytearray(base[:e0.abs_end]) + b"\x00\x00\x04\x00" + blob1
    at = 0x80 + 1 * 8
    d[at:at + 2] = struct.pack("<H", e1.off + 4)
    src = write_source(bytes(d))
    assert ".gap off=" in src and "raw=00000400" in src
    assert assemble_source(src) == bytes(d)
    gap = next(ln for ln in src.splitlines() if ln.startswith(".gap"))
    assert "# gap:" in gap                                # the enriched form explains what a gap IS
    assert ".gap" in write_source(bytes(d), enrich=False) and "#" not in write_source(bytes(d), enrich=False)


def test_lying_func_table_falls_back_to_raw():
    """The kit's blank template declares a func table whose fpos points past the entry end;
    such an entry is emitted as a verbatim raw= blob and still round-trips."""
    talk = _window(9) + RET
    data = bytearray(_eb_file([(0, [(0, RET)]), (2, [(0, RET), (3, talk)])]))
    eb = EbScript.from_bytes(bytes(data))
    e1 = eb.entries[1]
    ft = e1.abs_start + 2 + 4                             # func-table slot of tag 3: (tag, fpos)
    data[ft + 2:ft + 4] = struct.pack("<H", 9999)        # fpos far past the entry end
    src = write_source(bytes(data))
    assert "raw=" in src and ".entry 1 " in src
    assert assemble_source(src) == bytes(data)
    assert ".func" in src                                 # entry 0 stays structured


# --------------------------------------------------------------------- Rung 4: comment enrichment

def _rich_eb() -> bytes:
    """A synthetic field with one of every enrichable shape: Main_Init spawns an object entry and
    writes a kit-band story flag; the object sets a model and its talk handler shows a line, grants
    an item and warps. Bodies are ASSEMBLED from source (kit-authored, zero real game bytes)."""
    init = cmdasm.assemble_block("\n".join([
        "InitObject(2, 0)",
        "SET({ Global.Bit[8712] const(1) B_LET B_EXPR_END })",
        "RET()",
    ]))
    obj_init = cmdasm.assemble_block("SetModel(179, 100)\nRET()")
    talk = cmdasm.assemble_block("\n".join([
        "WindowSync(0, 128, 7)",
        "AddItem(236, 1)",
        "Field(355)",
        "RET()",
    ]))
    return _eb_file([(0, [(0, init)]), None, (2, [(0, obj_init), (3, talk)])])


def _mes(text: str, txid: int = 7) -> dict:
    from ff9mapkit.dialogue import MesEntry
    return {txid: MesEntry(txid=txid, text=text)}


_KW = dict(mes_entries=_mes("Hello there.\nHow are you?"), field_names={355: "Test/Room"})


def _comment(src: str, needle: str) -> str:
    """The comment on the first line containing ``needle`` ('' when the line has none)."""
    line = next(ln for ln in src.splitlines() if needle in ln)
    return line.split("#", 1)[1].strip() if "#" in line else ""


def test_enriched_output_still_assembles_byte_exact():
    """The whole point: comments are presentation. Both parsers strip '#', so the enriched text
    reassembles to the same bytes as the plain text — and write_source's self-verify already
    demanded it on the way out."""
    data = _rich_eb()
    rich = write_source(data, title="rich demo", **_KW)
    assert rich.count("#") > 6                            # it really did comment
    assert assemble_source(rich) == data
    assert assemble_source(rich) == assemble_source(write_source(data, enrich=False))


def test_enrichment_is_deterministic_and_a_fixpoint():
    data = _rich_eb()
    a = write_source(data, **_KW)
    assert a == write_source(data, **_KW)                 # same inputs -> identical text
    assert write_source(assemble_source(a), **_KW) == a   # and a fixpoint with the kwargs held


def test_instruction_comments_join_their_catalogs():
    src = write_source(_rich_eb(), **_KW)
    assert _comment(src, "AddItem(236, 1)") == "Potion"
    assert _comment(src, "SetModel(179, 100)") == "GEO_NPC_F1_DAL"
    assert _comment(src, "InitObject(2, 0)").startswith("spawn entry 2 (npc")
    warp = _comment(src, "Field(355)")                    # friendly name wins, EVT in parens
    assert warp.startswith("-> Test/Room (EVT_")
    flag = _comment(src, "Global.Bit[8712]")              # the BAND is the fact worth stating
    assert "8712" in flag and "kit band" in flag
    assert _comment(src, "WindowSync(0, 128, 7)") == '"Hello there. / How are you?"'


def test_field_warp_falls_back_to_the_evt_name():
    """Without a manifest (the normal case — it is gitignored) a warp still names its target from
    the in-package field table."""
    src = write_source(_rich_eb(), mes_entries=_KW["mes_entries"])
    assert _comment(src, "Field(355)").startswith("-> EVT_")


def test_window_preview_needs_mes_entries():
    src = write_source(_rich_eb(), field_names={355: "Test/Room"})
    assert _comment(src, "WindowSync(0, 128, 7)") == ""
    assert "no .mes given" in src.splitlines()[0]


def test_header_entry_and_func_comments():
    src = write_source(_rich_eb(), title="rich demo", **_KW)
    assert src.splitlines()[0] == "# rich demo"           # the title line stays first
    assert "2 entries, 3 routines" in src.splitlines()[1]     # slot 1 is EMPTY -> not counted
    assert _comment(src, ".entry 0 type=0") == "main"
    ent2 = _comment(src, ".entry 2 type=2")
    assert ent2.startswith("npc (GEO_NPC_F1_DAL)") and "talkable" in ent2
    assert _comment(src, ".func 0").startswith("Field startup")
    talk = _comment(src, ".func 3")
    assert talk.startswith("Talk handler") and "says 1 line" in talk


def test_enrich_false_emits_no_comments_beyond_the_title():
    src = write_source(_rich_eb(), title="plain demo", enrich=False, **_KW)
    lines = src.splitlines()
    assert lines[0] == "# plain demo"
    assert not any("#" in ln for ln in lines[1:])
    assert assemble_source(src) == _rich_eb()


def test_comments_are_sanitized_to_one_line():
    """A comment may hold a '#' harmlessly, but a NEWLINE would turn its tail into a source line —
    and an unbounded preview would make the file unreadable. Both are collapsed."""
    long_text = "line one\r\nline\ttwo # not a problem " + "very long tail " * 20
    src = write_source(_rich_eb(), title="a\nb", mes_entries=_mes(long_text),
                       field_names=_KW["field_names"])
    win = next(ln for ln in src.splitlines() if "WindowSync(0, 128, 7)" in ln)
    assert "\r" not in win and "\t" not in win
    assert win.endswith('..."') and len(_comment(src, "WindowSync(0, 128, 7)")) <= 70
    assert src.splitlines()[0] == "# a b"                 # even the title collapses
    assert assemble_source(src) == _rich_eb()             # ... and none of it moved a byte


def test_lying_func_table_degrades_to_instruction_comments_only():
    """The kit's blank-template lineage points an fpos PAST the entry end, which sends the
    whole-file logic scanner walking garbage. That must cost only the structural labels — the
    per-instruction pass clamps per func, so its comments survive — and the loss is announced."""
    data = bytearray(_rich_eb())
    e2 = EbScript.from_bytes(bytes(data)).entries[2]
    ft = e2.abs_start + 2 + 4                                           # func-table slot of tag 3
    data[ft + 2:ft + 4] = struct.pack("<H", 9999)                       # its fpos: past the end
    src = write_source(bytes(data))
    assert src.splitlines()[0].startswith("# entry/routine labels unavailable (IndexError")
    assert _comment(src, "InitObject(2, 0)") == "spawn entry 2"         # no entry role to add
    assert "kit band" in _comment(src, "Global.Bit[8712]")
    assert _comment(src, ".entry 0 type=0") == "" and _comment(src, ".func 0") == ""
    assert assemble_source(src) == bytes(data)


def test_enrichment_failure_is_reported_not_swallowed(monkeypatch):
    """The outer guard: comments must never cost the round trip (the whole-corpus gate runs this
    path) — but a naming layer that blew up in an UNFORESEEN way is ANNOUNCED in the header, never
    silently blank. Injected at a labeller used ONLY by enrichment, past the inner guard."""
    from ff9mapkit import logic_map

    def _boom(*a, **kw):
        raise RuntimeError("labeller exploded")

    monkeypatch.setattr(logic_map, "kind_label", _boom)
    data = _rich_eb()
    src = write_source(data, title="rich demo")
    assert src.splitlines()[1] == "# comments unavailable (RuntimeError: labeller exploded)"
    assert not any("#" in ln for ln in src.splitlines()[2:])
    assert assemble_source(src) == data


def test_battle_scene_comments_name_and_warn():
    """A scripted Battle names its scene (the high bit of btlId is Steiner's state, NOT the scene);
    SetRandomBattles names its slots, collapsing the usual all-four-the-same repeat; and a BSC_B3_*
    pick is a model holder that crashes as an encounter, so the comment says so where the byte is."""
    from ff9mapkit import catalog
    good = catalog.resolve_scene("BSC_IC_R000")
    bucket = next(sid for _nm, sid in catalog.battle_scenes(include_model_bucket=True)
                  if catalog.is_model_bucket_scene(sid))
    body = cmdasm.assemble_block("\n".join([
        f"Battle(0, {good | 0x8000})",                     # bit 15 set -> same scene
        f"SetRandomBattles(1, {good}, {good}, {good}, {good})",
        f"Battle(0, {bucket})",
        "RET()",
    ]))
    src = write_source(_eb_file([(0, [(0, body)])]))
    assert _comment(src, f"Battle(0, {good | 0x8000})") == f"scene {good} BSC_IC_R000"
    assert _comment(src, "SetRandomBattles") == f"random encounters: scene {good} BSC_IC_R000"
    assert "NOT fightable (model bucket)" in _comment(src, f"Battle(0, {bucket})")


def test_battle_ex_names_its_scene_too():
    """BattleEx (0x8C) is the same event — a scripted battle — with a group operand, so its btlId
    sits at arg 2 under the same 0x7FFF mask. Naming Battle but not BattleEx left the scripted
    battles of the fields that use the group form unlabelled."""
    from ff9mapkit import catalog
    good = catalog.resolve_scene("BSC_IC_R000")
    body = cmdasm.assemble_block(f"BattleEx(0, 3, {good | 0x8000})\nRET()")
    src = write_source(_eb_file([(0, [(0, body)])]))
    assert _comment(src, "BattleEx(") == f"scene {good} BSC_IC_R000"


# ------------------------------------------------------- the armed-entry set (all three Init ops)

def _armed_eb() -> bytes:
    """Every ARMING shape in one synthetic field: entry 2 spawned as an object from Main_Init,
    entry 3 armed as CODE, entry 4 armed as a REGION from a talk handler (NOT Main_Init), a party
    slot selector, and entry 5 armed by nobody."""
    init = cmdasm.assemble_block("\n".join([
        "InitObject(2, 0)",
        "InitCode(3, 0)",
        "InitObject(252, 0)",
        "RET()",
    ]))
    npc_init = cmdasm.assemble_block("SetModel(179, 100)\nRET()")
    npc_talk = cmdasm.assemble_block("InitRegion(4, 0)\nRET()")
    return _eb_file([(0, [(0, init)]), None, (2, [(0, npc_init), (3, npc_talk)]),
                     (0, [(0, cmdasm.assemble_block("RET()"))]),
                     (1, [(0, cmdasm.assemble_block("RET()")),
                          (2, cmdasm.assemble_block("RET()"))]),
                     (0, [(0, cmdasm.assemble_block("RET()"))])])


def test_init_fact_table_covers_every_engine_init_op():
    """Drift guard: the comment layer's Init* table IS eventscan.INIT_OPS. If the engine census
    ever grows a fourth arming op, this fails instead of silently mislabelling its entries."""
    from ff9mapkit import eventscan
    from ff9mapkit.eb import ebsrc as _e
    assert set(_e._INIT_FACT) == set(eventscan.INIT_OPS)


def test_all_three_init_ops_arm_an_entry():
    """'defined, not spawned' must read the WHOLE arming surface. InitObject alone misses an entry
    armed as code (0x07) or as a region (0x08) — and misses arming done anywhere but Main_Init —
    which mislabelled live entries as dead across most of the real corpus (field 2510's gateway
    entry 13 among them)."""
    src = write_source(_armed_eb())
    assert "defined, not spawned" not in _comment(src, ".entry 2 ")     # InitObject, Main_Init
    assert "defined, not spawned" not in _comment(src, ".entry 3 ")     # InitCode
    assert "defined, not spawned" not in _comment(src, ".entry 4 ")     # InitRegion, from a talk fn
    assert "defined, not spawned" in _comment(src, ".entry 5 ")         # armed by nobody: dead
    assert _comment(src, "InitCode(3, 0)") == "arm code entry 3 (script helper)"
    assert _comment(src, "InitRegion(4, 0)") == "arm region entry 4 (invisible trigger)"
    assert assemble_source(src) == _armed_eb()


def test_party_slot_init_object_is_not_an_entry_index():
    """InitObject 251-254 select a PARTY MEMBER (the engine's partyUID[sid - 251]), not entry 251+
    — so they name the slot, and they arm no entry."""
    src = write_source(_armed_eb())
    assert _comment(src, "InitObject(252, 0)") == "spawn party member (slot 1)"
    assert "spawn entry 252" not in src


def test_armed_more_than_once_is_counted():
    body = cmdasm.assemble_block("InitObject(1, 0)\nInitCode(1, 0)\nRET()")
    src = write_source(_eb_file([(0, [(0, body)]),
                                 (0, [(0, cmdasm.assemble_block("RET()"))])]))
    assert _comment(src, ".entry 1 ").endswith("armed x2")


def test_the_writer_reuses_the_enrichment_decode(monkeypatch):
    """Finding 3: the comment layer and the body disassembler decoded every function TWICE. The
    cache must actually be CONSUMED (a cache nobody hits is the check-that-cannot-fail shape) and
    must not change one byte of the emitted text."""
    from ff9mapkit.battle import battleai
    from ff9mapkit.eb import ebsrc as _e

    data = _armed_eb()
    calls = []
    real = battleai._decode_func_pretty
    monkeypatch.setattr(battleai, "_decode_func_pretty",
                        lambda *a, **k: (calls.append(a[1:]), real(*a, **k))[1])
    with_cache = write_source(data)
    hits = len(calls)
    calls.clear()
    monkeypatch.setattr(_e._Enrichment, "predecoded", lambda self, a, b: None)
    without_cache = write_source(data)
    assert with_cache == without_cache                    # same text, byte for byte
    assert hits < len(calls)                              # ... and strictly fewer decodes


# --------------------------------------------------------------------- error contract

@pytest.mark.parametrize("mutate,msg", [
    (lambda s: s.replace(".ebs 1", ".ebs 9"), "version"),
    (lambda s: s.replace(".ebs 1\n", ""), "first directive|missing .ebs"),
    (lambda s: "\n".join(ln for ln in s.splitlines() if not ln.startswith(".name")), "missing .name"),
    (lambda s: s.replace(".entry 1 EMPTY\n", ""), "missing .entry"),
    (lambda s: s.replace(".entry 1 EMPTY", ".entry 1 EMPTY\n.entry 1 EMPTY"), "duplicate .entry"),
    (lambda s: s.replace(".entry 1 EMPTY", ".entry 1 EMPTY\nRET()"), "outside a .func"),
    (lambda s: s.replace(".entry 1 EMPTY", ".entry 1 EMPTY\n.func 0"), "outside a non-empty"),
    (lambda s: s + ".wat 3\n", "unknown directive"),
    (lambda s: s.replace(".name", ".byte2 xx\n.name"), "not an integer"),
    (lambda s: s.replace("type=0", "type=0 type=0"), "duplicate attribute"),
    (lambda s: s.replace("type=0", "type=zz"), "not an integer"),
    (lambda s: s.replace(".entry 4 EMPTY", ".entry 4 EMPTY zz=1"), "only an off="),
    (lambda s: s.replace("RET()", "JMP({ const(1) B_EXPR_END })", 1), "entry 0 tag 0"),
    (lambda s: s.replace("WindowSync(0, ", "WindowSync(xx, ", 1), "entry 2 tag 3"),
])
def test_grammar_errors(mutate, msg):
    src = write_source(_demo_eb())
    with pytest.raises(EbSrcError, match=msg):
        assemble_source(mutate(src))


def test_slot_index_bounds():
    core = ".ebs 1\n.name " + "00" * 124 + "\n.entry 0 type=0\n.func 0\nRET()\n"
    with pytest.raises(EbSrcError, match="highest index"):
        assemble_source(core + ".entry 255 EMPTY\n")
    full = core + "".join(f".entry {i} EMPTY\n" for i in range(1, 255))
    data = assemble_source(full)                          # 255 slots (max) assembles fine
    assert data[3] == 255
    assert assemble_source(write_source(data)) == data


def test_all_empty_refused():
    with pytest.raises(EbSrcError, match="non-empty"):
        assemble_source(".ebs 1\n.name " + "00" * 124 + "\n.entry 0 EMPTY\n")


@pytest.mark.parametrize("corrupt", [
    lambda d: d[:16],                                     # truncated mid-header
    lambda d: d[:0x80 + 8],                               # ends mid-entry-table
    lambda d: d[:3] + b"\xc8" + d[4:],                    # entryCount 200, table past EOF
    lambda d: (lambda x: (x.__setitem__(slice(0x80 + 16, 0x80 + 18), struct.pack("<H", 0xFFF0)), bytes(x))[1])(bytearray(d)),  # entry off past EOF
    lambda d: b"XX" + d[2:],                              # bad magic
])
def test_corrupt_input_is_refused_not_crashed(corrupt):
    with pytest.raises(EbSrcError):
        write_source(corrupt(_demo_eb()))


def test_expression_on_flagless_opcode_refused():
    """The cmdasm silent-encoding hole: a { ... } operand on an op with no argFlag byte
    (JMP, switches, low ops) must be a hard error, never silently different bytecode."""
    core = ".ebs 1\n.name " + "00" * 124 + "\n.entry 0 type=0\n.func 0\n"
    for line in ("op_07({ B_EXPR_END }, 2)", "JMP({ const(5) B_EXPR_END })"):
        with pytest.raises(EbSrcError, match="argFlag|expression"):
            assemble_source(core + line + "\nRET()\n")


# --------------------------------------------------------------------- the CLI verbs

def _ns(**kw):
    import argparse
    kw.setdefault("plain", False)                         # eb-src's comment switch (Rung 4)
    return argparse.Namespace(**kw)


def test_cli_eb_src_and_eb_asm_roundtrip(tmp_path, capsys):
    from ff9mapkit.cli import _cmd_eb_asm, _cmd_eb_src
    eb_path = tmp_path / "demo.eb.bytes"
    eb_path.write_bytes(_demo_eb())
    src_path = tmp_path / "demo.ebs"
    assert _cmd_eb_src(_ns(target=str(eb_path), lang="us", out=str(src_path),
                           verify_all=False)) == 0
    out_path = tmp_path / "out.eb"
    assert _cmd_eb_asm(_ns(src=str(src_path), out=str(out_path),
                           verify_against=str(eb_path))) == 0
    assert out_path.read_bytes() == _demo_eb()
    capsys.readouterr()


def test_cli_eb_src_plain_switch(tmp_path, capsys):
    """Comments are ON by default; --plain drops them. Either way the source assembles back to
    the same bytes (a bare .eb PATH carries no field id, so no .mes / manifest is consulted)."""
    from ff9mapkit.cli import _cmd_eb_src
    eb_path = tmp_path / "demo.eb.bytes"
    eb_path.write_bytes(_rich_eb())
    rich, plain = tmp_path / "rich.ebs", tmp_path / "plain.ebs"
    assert _cmd_eb_src(_ns(target=str(eb_path), lang="us", out=str(rich), verify_all=False)) == 0
    assert _cmd_eb_src(_ns(target=str(eb_path), lang="us", out=str(plain), verify_all=False,
                           plain=True)) == 0
    rich_txt, plain_txt = rich.read_text(encoding="utf-8"), plain.read_text(encoding="utf-8")
    assert "AddItem(236, 1)  # Potion" in rich_txt
    assert plain_txt.splitlines()[0] == "# demo.eb.bytes"
    assert not any("#" in ln for ln in plain_txt.splitlines()[1:])
    assert assemble_source(rich_txt) == assemble_source(plain_txt) == _rich_eb()
    capsys.readouterr()


def _patch_naming_seams(monkeypatch, *, mes=True, names=True, boom=False):
    """Stand in for the INSTALL at exactly the seams `_eb_src_naming` reads — the .mes extract,
    its parser, and the (gitignored, dev-only) field-name manifest — so the field-ID path of
    eb-src is testable with no FF9 install and no real game bytes."""
    from ff9mapkit import dialogue, extract

    def _boom(*a, **kw):
        raise RuntimeError("no install here")

    monkeypatch.setattr(extract, "extract_event_script", lambda t, lang="us": _rich_eb())
    monkeypatch.setattr(dialogue, "extract_field_mes",
                        _boom if boom else (lambda t, lang="us": b"raw" if mes else b""))
    monkeypatch.setattr(dialogue, "parse_mes", lambda body: _KW["mes_entries"])
    monkeypatch.setattr(extract, "_manifest_field_names",
                        _boom if boom else (lambda: {355: "Test/Room"} if names else {}))


def test_cli_eb_src_by_field_id_names_what_it_found(monkeypatch, tmp_path, capsys):
    """The field-ID path is the one that carries names: the title line gets the field's friendly +
    EVT identity, warps resolve through the manifest, and dialogue previews come from the .mes.
    KILLS the mutant that makes the naming layer return empties — every assertion here is about a
    name that only the naming layer can supply."""
    from ff9mapkit.cli import _cmd_eb_src
    _patch_naming_seams(monkeypatch)
    out = tmp_path / "byid.ebs"
    assert _cmd_eb_src(_ns(target="355", lang="us", out=str(out), verify_all=False)) == 0
    txt = out.read_text(encoding="utf-8")
    title = txt.splitlines()[0]                           # friendly | FBG folder | EVT name
    assert title.startswith("# field 355 lang us -- Test/Room | fbg_") and "| EVT_" in title
    assert _comment(txt, "Field(355)").startswith("-> Test/Room (EVT_")
    assert _comment(txt, "WindowSync(0, 128, 7)") == '"Hello there. / How are you?"'
    assert assemble_source(txt) == _rich_eb()
    capsys.readouterr()


def test_cli_eb_src_survives_a_naming_layer_that_blows_up(monkeypatch, tmp_path, capsys):
    """Names are PRESENTATION: an install/text-block/manifest that raises must cost the comments'
    wording and nothing else. KILLS the mutant that drops `_eb_src_naming`'s guards — under it
    this raises instead of returning 0."""
    from ff9mapkit.cli import _cmd_eb_src
    _patch_naming_seams(monkeypatch, boom=True)
    out = tmp_path / "boom.ebs"
    assert _cmd_eb_src(_ns(target="355", lang="us", out=str(out), verify_all=False)) == 0
    txt = out.read_text(encoding="utf-8")
    assert txt.splitlines()[0] == "# field 355 lang us"   # no suffix -- but the command WORKED
    assert "no .mes given" in txt.splitlines()[1]
    assert _comment(txt, "Field(355)").startswith("-> EVT_")   # the in-package table still names it
    assert assemble_source(txt) == _rich_eb()
    assert "Traceback" not in capsys.readouterr().err


def test_cli_eb_src_stdout_survives_a_legacy_code_page(monkeypatch, capsys):
    """A jp/fr dialogue preview through a cp1252 console must PRINT (degraded), never traceback,
    and must say ONCE that what you are looking at is no longer the exact source. KILLS the mutant
    that reverts the print to a bare `print(src)` — that raises UnicodeEncodeError here."""
    import io
    import sys as _sys
    from ff9mapkit import dialogue
    from ff9mapkit.cli import _cmd_eb_src

    _patch_naming_seams(monkeypatch)
    monkeypatch.setattr(dialogue, "parse_mes", lambda body: _mes("ダガーの剣"))
    stream = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict", newline="")
    monkeypatch.setattr(_sys, "stdout", stream)
    assert _cmd_eb_src(_ns(target="355", lang="us", out=None, verify_all=False)) == 0
    stream.flush()
    printed = stream.buffer.getvalue().decode("cp1252")
    assert ".ebs 1" in printed and '"???' in printed           # it printed, and it degraded
    err = capsys.readouterr().err
    assert err.count("cp1252") == 1 and "-o FILE" in err       # said so ONCE, and how to fix it


def test_cli_eb_asm_verify_mismatch_exits_1(tmp_path, capsys):
    from ff9mapkit.cli import _cmd_eb_asm, _cmd_eb_src
    eb_path = tmp_path / "demo.eb.bytes"
    eb_path.write_bytes(_demo_eb())
    src_path = tmp_path / "demo.ebs"
    _cmd_eb_src(_ns(target=str(eb_path), lang="us", out=str(src_path), verify_all=False))
    other = tmp_path / "other.eb"
    other.write_bytes(_demo_eb(byte2=9))
    assert _cmd_eb_asm(_ns(src=str(src_path), out=str(tmp_path / "o.eb"),
                           verify_against=str(other))) == 1
    assert "MISMATCH" in capsys.readouterr().err


def test_cli_eb_asm_refuses_to_clobber_its_source(tmp_path, capsys):
    from ff9mapkit.cli import _cmd_eb_asm
    src = tmp_path / "misnamed.eb"                        # .eb suffix -> default out == input
    src.write_text(write_source(_demo_eb()), encoding="utf-8")
    assert _cmd_eb_asm(_ns(src=str(src), out=None, verify_against=None)) == 2
    assert "destroy" in capsys.readouterr().err
    assert src.read_text(encoding="utf-8").startswith("#") or ".ebs" in src.read_text(encoding="utf-8")


def test_cli_clean_errors_exit_2(tmp_path, capsys):
    from ff9mapkit.cli import _cmd_eb_asm, _cmd_eb_src
    bad = tmp_path / "bad.ebs"
    bad.write_text(".ebs 1\nRET()\n", encoding="utf-8")
    assert _cmd_eb_asm(_ns(src=str(bad), out=str(tmp_path / "o.eb"), verify_against=None)) == 2
    assert _cmd_eb_asm(_ns(src=str(tmp_path / "missing.ebs"), out=None, verify_against=None)) == 2
    noteb = tmp_path / "not.eb.bytes"
    notes = noteb.write_bytes(b"PNG not an eb, definitely long enough to read")
    assert _cmd_eb_src(_ns(target=str(noteb), lang="us", out=None, verify_all=False)) == 2
    errs = capsys.readouterr().err
    assert "eb-asm:" in errs and "eb-src:" in errs and "Traceback" not in errs


def test_cli_verify_all_refuses_partial_corpus(monkeypatch, capsys):
    from ff9mapkit import cli, extract

    class _Env:
        container = {}

    monkeypatch.setattr(extract, "_events_bundle", lambda game=None: "p0data7.bin")
    monkeypatch.setattr(extract, "_streaming_assets", lambda game=None: __import__("pathlib").Path("."))
    monkeypatch.setattr(extract, "_load_env", lambda p: _Env())
    assert cli._eb_src_verify_all() == 2
    assert "partial corpus" in capsys.readouterr().err


def test_cli_verify_all_no_install_exits_2(monkeypatch, capsys):
    from ff9mapkit import cli, extract
    from ff9mapkit.config import ConfigError

    def _boom(game=None):
        raise ConfigError("no FF9 install")

    monkeypatch.setattr(extract, "_events_bundle", _boom)
    assert cli._eb_src_verify_all() == 2
    assert "no FF9 install" in capsys.readouterr().err


def _noisy_eb() -> bytes:
    clean = bytes([0x1F, 0x00, 0, 0]) + struct.pack("<H", 500) + RET
    noisy = bytes([0x1F, 0x80, 0, 0]) + struct.pack("<H", 500) + RET   # unused argFlag bit 7
    return _eb_file([(0, [(0, RET)]), (2, [(0, clean)]), (2, [(0, noisy)])])


def test_cli_verify_all_bounds_the_raw_fallback(monkeypatch, capsys):
    """The raw= escape round-trips TRIVIALLY, so an encoder regression that degrades readable
    source to hex would keep the byte-exact count green — the gate must bound the raw= count
    against the stock baseline and go RED on a surge. KILLS the mutant that drops the bound."""
    from ff9mapkit import cli, extract

    class _Obj:
        def read(self):
            return _noisy_eb()

    class _Env:
        container = {"x/eventbinary/field/us/evt_noise.eb.bytes": _Obj()}

    monkeypatch.setattr(extract, "_events_bundle", lambda game=None: "p0data7.bin")
    monkeypatch.setattr(extract, "_streaming_assets", lambda game=None: __import__("pathlib").Path("."))
    monkeypatch.setattr(extract, "_load_env", lambda p: _Env())
    monkeypatch.setattr(extract, "_raw_bytes", lambda x: x)
    monkeypatch.setattr(cli, "_EB_CORPUS_FLOOR", 1)
    monkeypatch.setattr(cli, "_EB_RAW_BASELINE", 0)
    assert cli._eb_src_verify_all() == 1                  # byte-exact 1/1, but raw= 1 > baseline 0
    cap = capsys.readouterr()
    assert "1/1 binaries round-trip byte-exact" in cap.out
    assert "raw= entries 1" in cap.out
    assert "silently degrading" in cap.err
    monkeypatch.setattr(cli, "_EB_RAW_BASELINE", 1)       # at baseline -> green
    assert cli._eb_src_verify_all() == 0


def test_raw_fallback_names_its_reason_on_the_line():
    """A raw= fallback is never silent: the emitted line says WHY (the encode-verify case names
    the argFlag/encoder cause), so a corpus grep for 'kept verbatim' audits every degradation."""
    src = write_source(_noisy_eb())
    raw_line = next(ln for ln in src.splitlines() if " raw=" in ln)
    assert "kept verbatim" in raw_line and "does not re-encode byte-exact" in raw_line


def test_encoder_regression_is_contained_and_named(monkeypatch):
    """The review's HIGH probe as a standing test: a corrupting encoder makes affected entries
    fall back to raw= (self-verify still byte-exact) with the reason NAMED — and the gate-side
    raw= bound (tested above) is what turns the surge red. The unaffected entry stays readable."""
    real = cmdasm.assemble_block

    def _bad(text):
        out = bytearray(real(text))
        if "WindowSync" in text and len(out) > 2:         # a plausible one-opcode regression
            out[2] ^= 0x01
        return bytes(out)

    monkeypatch.setattr(cmdasm, "assemble_block", _bad)
    from ff9mapkit.eb import ebsrc as _e
    data = _demo_eb()
    src = _e.write_source(data, enrich=False)
    assert real is not cmdasm.assemble_block
    assert assemble_source_with(real, src) == data        # the SOURCE is still faithful
    lines = src.splitlines()
    assert any("kept verbatim" in ln and "does not re-encode" in ln for ln in lines)
    assert any(ln.strip().startswith(".func") for ln in lines)     # the clean entry stays readable


def assemble_source_with(real_assemble, src):
    """assemble_source with the REAL encoder (the monkeypatched one corrupts) — proving the
    emitted source itself is faithful even while the in-process encoder is broken."""
    import unittest.mock as _m
    with _m.patch.object(cmdasm, "assemble_block", real_assemble):
        return assemble_source(src)


def test_gap_overlap_is_refused_not_overwritten():
    """The full assembler must REFUSE a layout whose .gap pin lands under a relocated entry body
    (it used to write the gap blob over the bytecode, exit 0). KILLS the mutant that drops the
    overlap guard."""
    donor = _gap_eb()
    src = write_source(donor)
    grown = src.replace("op_22(2)", "op_22(2)\nop_22(4)")
    with pytest.raises(EbSrcError, match=r"\.gap off=\d+ .*overlaps entry \d+'s body"):
        assemble_source(grown)
    assert assemble_source(src) == donor                  # the unedited layout still assembles


# --------------------------------------------------------------------- the REAL-corpus sweep

def _bundle_binaries(langs):
    from ff9mapkit import extract
    bundle = extract._events_bundle()
    if not bundle:
        raise RuntimeError("no events bundle")
    env = extract._load_env(extract._streaming_assets() / bundle)
    out = {lg: {} for lg in langs}
    for k, obj in env.container.items():
        kl = k.lower()
        if "eventbinary/field/" not in kl or not kl.endswith(".eb.bytes"):
            continue
        parts = kl.split("eventbinary/field/")[1].split("/")
        lang, evt = parts[0], parts[-1][:-len(".eb.bytes")]
        if lang in out:
            out[lang][evt] = obj
    return out


def test_roundtrip_real_corpus_sweep():
    """Every US field binary + a cross-language sample must round-trip byte-exact. The count
    is asserted LOUDLY (>= 800 us files) so a partial/missing corpus fails instead of passing
    green on nothing. Only the KNOWN no-install failure modes skip; any other loader crash is
    a real failure. The full 818x7 sweep is the CLI: ``ff9mapkit eb-src --verify-all``."""
    from ff9mapkit import extract
    from ff9mapkit.config import ConfigError
    try:
        by_lang = _bundle_binaries(["us", "jp", "fr"])
    except (ImportError, ModuleNotFoundError, RuntimeError, ConfigError, FileNotFoundError):
        pytest.skip("needs the FF9 install + UnityPy")
    checked = 0
    for evt, obj in sorted(by_lang["us"].items()):
        data = extract._raw_bytes(obj.read())
        assert assemble_source(write_source(data)) == data, f"us/{evt}"
        checked += 1
    assert checked >= 800, f"us corpus incomplete: only {checked} binaries seen"
    for lang in ("jp", "fr"):                             # the divergent langs, sampled
        sample = sorted(by_lang[lang])[::17]
        assert len(sample) >= 40, f"{lang} sample too small ({len(sample)})"
        for evt in sample:
            data = extract._raw_bytes(by_lang[lang][evt].read())
            assert assemble_source(write_source(data)) == data, f"{lang}/{evt}"


# ================================================================ Rung 6: edit-through-source
#
# `assemble_against` SPLICES only the functions whose source changed into the donor's own bytes.
# What these tests pin: nothing else moves (the minimality claim), the two independent paths
# (splice vs. full reassembly) agree, and every STRUCTURAL edit is refused by name.

def _lint_errors(data: bytes):
    from ff9mapkit import eblint
    return eblint.errors(eblint.lint_eb(data))


def _diff_offsets(a: bytes, b: bytes) -> list:
    return [i for i in range(min(len(a), len(b))) if a[i] != b[i]]


def _func_bytes(data: bytes, entry: int, fi: int) -> bytes:
    f = EbScript.from_bytes(data).entries[entry].funcs[fi]
    return data[f.abs_start:f.abs_end]


def _splice_eb() -> bytes:
    """A lint-clean donor for the splice tests: Main_Init arms an object, the object's talk handler
    grants an item, and entry 3 pairs a plain func with a SWITCH-bearing sibling AFTER it (so an
    edit to the first relocates the second)."""
    init = cmdasm.assemble_block("InitObject(2, 0)\nInitCode(3, 0)\nRET()")
    obj_init = cmdasm.assemble_block("SetModel(179, 100)\nRET()")
    talk = cmdasm.assemble_block("AddItem(236, 1)\nWindowSync(0, 128, 7)\nRET()")
    first = cmdasm.assemble_block("op_22(2)\nRET()")               # op_22 == Wait(n)
    switcher = cmdasm.assemble_block("\n".join([
        "SET({ const(1) B_EXPR_END })",
        "SWITCH(1, Ldef, Lone, Ltwo)",
        "Lone:", "op_22(1)", "RET()",
        "Ltwo:", "op_22(3)", "RET()",
        "Ldef:", "RET()",
    ]))
    return _eb_file([(0, [(0, init)]), None, (2, [(0, obj_init), (3, talk)]),
                     (0, [(0, first), (1, switcher)])])


def _gap_eb() -> bytes:
    """A KIT-shaped donor: entry 0 declares a size smaller than its func table's reach, so live
    bytes sit between the entries covered by no declared span (a ``.gap``), and a trailing EMPTY
    slot's parked off is stale (an explicit ``off=`` override). Both are VERBATIM carriers."""
    body = cmdasm.assemble_block("op_22(2)\nAddItem(236, 1)\nRET()")
    base = _eb_file([(0, [(0, body)]), (2, [(0, cmdasm.assemble_block("RET()"))]), None])
    eb = EbScript.from_bytes(base)
    e0, e1 = eb.entries[0], eb.entries[1]
    d = bytearray(base[:e0.abs_end]) + b"\x22\x00\x09" + base[e1.abs_start:]     # a Wait(9) orphan
    for idx in (1, 2):                                    # entry 1 moves +3; the empty parks stale
        at = 0x80 + idx * 8
        d[at:at + 2] = struct.pack("<H", (e1.off + 3) if idx == 1 else 4242)
    return bytes(d)


def _dup_tag_eb() -> bytes:
    """14 of the 818 shipping field EVTs repeat a func tag inside one entry, so a splice addressed
    BY TAG would hit the first namesake. This donor reproduces that shape."""
    a = cmdasm.assemble_block("op_22(1)\nRET()")
    b = cmdasm.assemble_block("op_22(2)\nRET()")
    return _eb_file([(0, [(0, cmdasm.assemble_block("RET()")), (5, a), (5, b)])])


# ---------------------------------------------------------------- the no-edit identity

def test_against_no_edit_is_the_donor_byte_for_byte():
    """The floor of the whole feature: unedited source splices NOTHING. (The internal agreement
    check then also proves assemble_source reproduces the donor from the same text.)"""
    for donor in (_demo_eb(name=b"Test/Room\x00"), _rich_eb(), _splice_eb(), _gap_eb()):
        out, report = assemble_against(write_source(donor), donor)
        assert out == donor
        assert report == []


def test_against_no_edit_tolerates_the_comment_layer_and_a_bom():
    donor = _splice_eb()
    src = write_source(donor, title="donor", **_KW)
    assert "#" in src
    out, report = assemble_against(chr(0xFEFF) + src, donor)
    assert out == donor and report == []


# ---------------------------------------------------------------- minimal-diff splicing

def test_against_single_function_edit_touches_only_that_function():
    """A length-preserving hand edit must move EXACTLY the bytes of the instruction it edited —
    no table fixups, no neighbours. KILLS any implementation that rebuilds the file."""
    donor = _splice_eb()
    src = write_source(donor)
    edited = src.replace("AddItem(236, 1)", "AddItem(238, 1)")
    assert edited != src
    out, report = assemble_against(edited, donor)
    n = len(_func_bytes(donor, 2, 1))                      # the talk handler, unchanged in length
    assert report == [f"entry 2 tag 3: {n}B -> {n}B"]
    assert len(out) == len(donor)
    f = EbScript.from_bytes(donor).entries[2].funcs[1]
    diffs = _diff_offsets(out, donor)
    assert diffs and all(f.abs_start <= d < f.abs_end for d in diffs)
    assert out == assemble_source(edited)                 # the agreement invariant
    assert _lint_errors(out) == []


def test_against_length_changing_edit_relocates_the_switch_sibling():
    """Growing a func that has a SWITCH-bearing sibling AFTER it in the same entry: the sibling's
    fpos, the entry size and every later entry's table off must move — and the switch's own
    (function-relative) arms must survive, which the linter checks."""
    donor = _splice_eb()
    src = write_source(donor)
    edited = src.replace("op_22(2)\nRET()", "op_22(2)\nop_22(4)\nRET()")
    assert edited != src
    out, report = assemble_against(edited, donor)
    n = len(_func_bytes(donor, 3, 0))
    assert report == [f"entry 3 tag 0: {n}B -> {n + 3}B"]  # op_22(4) is 3 bytes
    assert len(out) == len(donor) + 3
    sw_old = EbScript.from_bytes(donor).entries[3].funcs[1]
    sw_new = EbScript.from_bytes(out).entries[3].funcs[1]
    assert sw_new.fpos == sw_old.fpos + 3                 # the sibling's fpos moved
    assert _func_bytes(out, 3, 1) == _func_bytes(donor, 3, 1)      # ... its bytes did not
    assert _lint_errors(out) == []                        # ... and its switch arms still land
    assert out == assemble_source(edited)


def test_against_edit_in_an_early_entry_moves_every_later_entry():
    """The relocation the whole splice rests on: grow entry 0's Main_Init and entries 2/3 shift,
    bodies intact. The empty slot 1's PARKED off follows the census rule (it tracks the next
    non-empty entry) — the fixup replace_function_body cannot do, because an empty slot has no
    body to relocate."""
    donor = _splice_eb()
    edited = write_source(donor).replace("InitObject(2, 0)", "InitObject(2, 0)\nop_22(5)")
    out, report = assemble_against(edited, donor)
    n = len(_func_bytes(donor, 0, 0))
    assert report == [f"entry 0 tag 0: {n}B -> {n + 3}B"]
    old, new = EbScript.from_bytes(donor), EbScript.from_bytes(out)
    for i in (2, 3):
        assert new.entries[i].off == old.entries[i].off + 3
        assert out[new.entries[i].abs_start:new.entries[i].abs_end] == \
            donor[old.entries[i].abs_start:old.entries[i].abs_end]
    assert new.entries[1].empty and new.entries[1].off == new.entries[2].off
    assert _lint_errors(out) == []
    assert out == assemble_source(edited)


def test_against_splices_the_right_namesake_when_a_tag_repeats():
    """A func tag is NOT unique inside an entry (14 shipping EVTs repeat one). Addressing the
    splice by TAG hits the FIRST namesake; this pins the positional addressing. KILLS the mutant
    that drops replace_function_body's func_index."""
    donor = _dup_tag_eb()
    edited = write_source(donor).replace("op_22(2)", "op_22(7)")   # the SECOND tag-5 func
    out, report = assemble_against(edited, donor)
    n = len(_func_bytes(donor, 0, 2))
    assert report == [f"entry 0 tag 5: {n}B -> {n}B"]
    assert _func_bytes(out, 0, 1) == b"\x22\x00\x01\x04"           # first namesake: untouched
    assert _func_bytes(out, 0, 2) == b"\x22\x00\x07\x04"           # second: edited
    assert out == assemble_source(edited)


def test_against_carries_gaps_and_off_overrides_verbatim():
    """A kit-shaped donor (a .gap of live overhang code + a stale parked off=) takes a body edit
    with both carriers untouched: their bytes are the donor's own, not re-derived."""
    donor = _gap_eb()
    src = write_source(donor)
    assert ".gap off=" in src and "EMPTY off=4242" in src
    edited = src.replace("AddItem(236, 1)", "AddItem(238, 1)")
    out, report = assemble_against(edited, donor)
    n = len(_func_bytes(donor, 0, 0))
    assert report == [f"entry 0 tag 0: {n}B -> {n}B"]
    assert len(_diff_offsets(out, donor)) == 1            # ONE operand byte, nothing else
    gap = next(ln for ln in src.splitlines() if ln.startswith(".gap"))
    off = int(gap.split("off=")[1].split()[0])
    assert out[0x80 + off:0x80 + off + 3] == b"\x22\x00\x09"      # the orphan Wait(9) survives
    assert EbScript.from_bytes(out).entries[2].off == 4242        # the stale park is not "fixed"
    assert out == assemble_source(edited)


def test_against_refuses_an_edit_that_breaks_the_control_flow():
    """The second self-verify: dropping a function's terminator assembles fine and BOTH paths agree
    on the bytes — only the linter knows the engine would then run the IP into the next function.
    KILLS the mutant that removes the lint gate."""
    donor = _splice_eb()
    edited = write_source(donor).replace("op_22(2)\nRET()", "op_22(2)")
    assert _lint_errors(donor) == []                      # the donor itself is clean, so 0 is the bar
    with pytest.raises(EbSrcError, match="does not lint clean.*runs off the end"):
        assemble_against(edited, donor)
    assemble_source(edited)                               # ... and the FULL assembler still allows it


def test_against_refuses_when_the_two_paths_cannot_agree():
    """A NON-DERIVED layout (a .gap pins an absolute position) plus a LENGTH-changing edit is the
    one shape neither path may emit: the splice moved bytes the pin points at. The full assembler
    now REFUSES it (the gap-overlap guard — it used to silently overwrite relocated bytecode), and
    assemble_against surfaces that refusal with the safe remedies, never minting the file."""
    donor = _gap_eb()
    src = write_source(donor)
    with pytest.raises(EbSrcError, match="full-reassembly self-verify refused") as ex:
        assemble_against(src.replace("op_22(2)", "op_22(2)\nop_22(4)"), donor)
    assert "overlaps entry" in str(ex.value) and "length-preserving" in str(ex.value)


# ---------------------------------------------------------------- the structural refusals

def _rename_block(src: str) -> str:
    old = src.split(".name ")[1].split("\n")[0]
    return src.replace(".name " + old, ".name " + "ff" * 124)


@pytest.mark.parametrize("mutate,msg", [
    (lambda s: s.replace(".entry 3 ", ".func 9\nRET()\n.entry 3 "), r"\.func tags"),   # added .func
    (lambda s: s.replace(".func 3", ".func 4"), r"\.func tags"),                       # re-tagged
    (lambda s: s.replace("loc=0", "loc=2", 1), "loc="),
    (lambda s: s.replace("type=2", "type=5", 1), "type="),
    (lambda s: s.replace("flags=0", "flags=1", 1), "flags="),
    (lambda s: s.replace(".entry 1 EMPTY", ".entry 1 EMPTY off=999"), "off="),
    (lambda s: s + ".entry 4 EMPTY\n", "slot count"),
    (_rename_block, r"\.name differs"),
    (lambda s: s.replace(".ebs 1", ".ebs 1\n.byte2 7"), r"\.byte2"),
])
def test_against_refuses_a_structural_change(mutate, msg):
    """Each of these assembles FINE through the full assembler — it is only the SPLICE that cannot
    honour them, because it promises to touch nothing but function bodies. So each must refuse by
    NAME, pointing at plain eb-asm."""
    donor = _splice_eb()
    src = write_source(donor)
    mutated = mutate(src)
    assert mutated != src, "the mutation did not apply -- the test would pass on nothing"
    with pytest.raises(EbSrcError, match=msg) as ex:
        assemble_against(mutated, donor)
    assert "drop --against" in str(ex.value)


def test_against_refuses_an_entry_that_changed_shape():
    donor = _splice_eb()
    src = write_source(donor)
    with pytest.raises(EbSrcError, match="EMPTY here and structured|structured here and EMPTY"):
        assemble_against(src.replace(".entry 1 EMPTY", ".entry 1 type=0\n.func 0\nRET()"), donor)


def test_against_refuses_an_edited_raw_entry():
    """A raw= entry is a VERBATIM carrier for a func table this grammar cannot express; editing its
    hex is a structural change no splice can localise."""
    talk = _window(9) + RET
    data = bytearray(_eb_file([(0, [(0, RET)]), (2, [(0, RET), (3, talk)])]))
    e1 = EbScript.from_bytes(bytes(data)).entries[1]
    data[e1.abs_start + 2 + 4 + 2:e1.abs_start + 2 + 4 + 4] = struct.pack("<H", 9999)
    donor = bytes(data)
    src = write_source(donor)
    raw = next(ln for ln in src.splitlines() if "raw=" in ln)
    blob = raw.split("raw=")[1].split()[0]
    assert assemble_against(src, donor)[0] == donor       # untouched: fine
    with pytest.raises(EbSrcError, match="raw= blob differs"):
        assemble_against(src.replace(blob, blob[:-2] + ("aa" if blob[-2:] != "aa" else "bb")), donor)


def test_against_refuses_an_edited_gap():
    donor = _gap_eb()
    src = write_source(donor)
    with pytest.raises(EbSrcError, match=r"\.gap off=\d+: the raw= bytes differ"):
        assemble_against(src.replace("raw=220009", "raw=220008"), donor)
    with pytest.raises(EbSrcError, match=r"\.gap records are at offsets"):
        assemble_against(src.replace(".gap off=", ".gap off=1 raw=00\n.gap off=", 1), donor)


def test_against_refuses_a_donor_the_grammar_cannot_carry():
    with pytest.raises(EbSrcError, match="does not round-trip"):
        assemble_against(write_source(_splice_eb()), b"XX" + _splice_eb()[2:])


def test_against_reports_a_body_error_with_its_entry_and_tag():
    donor = _splice_eb()
    with pytest.raises(EbSrcError, match="entry 2 tag 3"):
        assemble_against(write_source(donor).replace("AddItem(236, 1)", "AddItem(zz, 1)"), donor)


def test_replace_function_body_by_index_asserts_the_tag():
    """The positional splice keeps the tag as a stated EXPECTATION, so a caller whose index and tag
    disagree is caught instead of quietly rewriting a neighbour."""
    from ff9mapkit.eb import edit
    donor = _dup_tag_eb()
    out = edit.replace_function_body(donor, 0, 5, b"\x04", func_index=2)
    assert _func_bytes(out, 0, 1) == b"\x22\x00\x01\x04" and _func_bytes(out, 0, 2) == b"\x04"
    with pytest.raises(ValueError, match="has tag 0, not the expected 5"):
        edit.replace_function_body(donor, 0, 5, b"\x04", func_index=0)
    with pytest.raises(ValueError, match="out of range"):
        edit.replace_function_body(donor, 0, 5, b"\x04", func_index=9)


def test_count_functions_counts_the_spliceable_bodies():
    assert count_functions(write_source(_splice_eb())) == 5        # 1 + 2 + 2; the EMPTY has none
    talk = _window(9) + RET
    data = bytearray(_eb_file([(0, [(0, RET)]), (2, [(0, RET), (3, talk)])]))
    e1 = EbScript.from_bytes(bytes(data)).entries[1]
    data[e1.abs_start + 2 + 4 + 2:e1.abs_start + 2 + 4 + 4] = struct.pack("<H", 9999)
    assert count_functions(write_source(bytes(data))) == 1         # the raw= entry contributes none


# ---------------------------------------------------------------- the --against CLI

def test_cli_eb_asm_against_splices_and_composes_with_verify(tmp_path, capsys):
    """The happy path AND the composition the demo needs: --verify-against the donor PASSES on an
    unedited source (exit 0) and FAILS on an edited one (exit 1) — the bytes really did change."""
    from ff9mapkit.cli import _cmd_eb_asm, _cmd_eb_src
    donor = _splice_eb()
    eb_path = tmp_path / "donor.eb"
    eb_path.write_bytes(donor)
    src_path = tmp_path / "donor.ebs"
    assert _cmd_eb_src(_ns(target=str(eb_path), lang="us", out=str(src_path), verify_all=False)) == 0
    out = tmp_path / "same.eb"
    assert _cmd_eb_asm(_ns(src=str(src_path), out=str(out), against=str(eb_path),
                           verify_against=str(eb_path))) == 0
    assert out.read_bytes() == donor
    said = capsys.readouterr().out
    assert "0 function(s) spliced, 5 untouched" in said

    src_path.write_text(src_path.read_text(encoding="utf-8").replace("AddItem(236, 1)",
                                                                     "AddItem(238, 1)"),
                        encoding="utf-8")
    edited = tmp_path / "edited.eb"
    assert _cmd_eb_asm(_ns(src=str(src_path), out=str(edited), against=str(eb_path),
                           verify_against=str(eb_path))) == 1     # intentionally differs now
    cap = capsys.readouterr()
    assert "spliced entry 2 tag 3: 12B -> 12B" in cap.out
    assert "1 function(s) spliced, 4 untouched" in cap.out
    assert "MISMATCH" in cap.err


def test_cli_eb_asm_against_refusals_exit_2(tmp_path, capsys):
    from ff9mapkit.cli import _cmd_eb_asm
    donor = _splice_eb()
    eb_path = tmp_path / "donor.eb"
    eb_path.write_bytes(donor)
    src_path = tmp_path / "donor.ebs"
    src_path.write_text(write_source(donor).replace(".func 3", ".func 4"), encoding="utf-8")
    out = tmp_path / "o.eb"
    assert _cmd_eb_asm(_ns(src=str(src_path), out=str(out), against=str(eb_path),
                           verify_against=None)) == 2
    assert _cmd_eb_asm(_ns(src=str(src_path), out=str(out), against=str(tmp_path / "nope.eb"),
                           verify_against=None)) == 2
    errs = capsys.readouterr().err
    assert "eb-asm:" in errs and "Traceback" not in errs
    assert not out.exists()                               # a refusal writes NOTHING


def test_cli_eb_asm_against_refuses_to_overwrite_the_donor(tmp_path, capsys):
    """The donor is the reference the splice is verified against AND the only copy of the original
    bytes. Writing the result over it is the one-keystroke way to lose both."""
    from ff9mapkit.cli import _cmd_eb_asm
    donor = _splice_eb()
    eb_path = tmp_path / "donor.eb"
    eb_path.write_bytes(donor)
    src_path = tmp_path / "donor.ebs"
    src_path.write_text(write_source(donor), encoding="utf-8")
    assert _cmd_eb_asm(_ns(src=str(src_path), out=str(eb_path), against=str(eb_path),
                           verify_against=None)) == 2
    assert "destroys your only copy" in capsys.readouterr().err
    assert eb_path.read_bytes() == donor


# ---------------------------------------------------------------- the install-gated real donor

def test_against_no_edit_on_a_real_field():
    """One real donor through the splice path, unedited: byte-identical out. Install-gated like the
    rest of the real-corpus work (a decompiled .ebs is derived from SE bytecode, never committed)."""
    from ff9mapkit import extract
    from ff9mapkit.config import ConfigError
    try:
        data = extract.extract_event_script("302", lang="us")     # Ice Cavern (EVT_ICE_IC_TER_0)
    except (ImportError, ModuleNotFoundError, RuntimeError, ConfigError, FileNotFoundError):
        pytest.skip("needs the FF9 install + UnityPy")
    if data is None:
        pytest.skip("field 302 not resolvable in this install")
    src = write_source(data)
    out, report = assemble_against(src, data)
    assert out == data and report == []
    edited = src.replace("AddItem(236, 1)", "AddItem(238, 1)", 1)
    assert edited != src
    out2, report2 = assemble_against(edited, data)
    assert len(report2) == 1 and out2 != data
    assert len(_diff_offsets(out2, data)) == 1 and len(out2) == len(data)
    assert _lint_errors(out2) == []


# ---------------------------------------------------------------- Rung 7: the non-field corpus

def test_argflag_noise_falls_back_to_raw():
    """The decoder consults only argFlag bits 0..argc-1 and the encoder zeroes the rest, so a
    body carrying NOISE in the unused bits decodes cleanly but cannot re-encode byte-exact (the
    2 jp-only world binaries in the whole corpus). Such an entry must ship as raw= — never a
    silent normalization, never a whole-file refusal. KILLS a mutant that drops the per-func
    encode-verify in _structured_funcs."""
    clean = bytes([0x1F, 0x00, 0, 0]) + struct.pack("<H", 500) + RET
    noisy = bytes([0x1F, 0x80, 0, 0]) + struct.pack("<H", 500) + RET   # bit 7 = noise
    data = _eb_file([(0, [(0, RET)]), (2, [(0, clean)]), (2, [(0, noisy)])])
    src = write_source(data)                              # self-verifies byte equality
    assert assemble_source(src) == data
    lines = src.splitlines()
    e1 = next(ln for ln in lines if ln.startswith(".entry 1 "))
    e2 = next(ln for ln in lines if ln.startswith(".entry 2 "))
    assert "raw=" not in e1                               # the clean twin stays structured
    assert "raw=" in e2                                   # the noisy one takes the escape hatch


def _nonfield_binaries(groups):
    from ff9mapkit import extract
    bundle = extract._events_bundle()
    if not bundle:
        raise RuntimeError("no events bundle")
    env = extract._load_env(extract._streaming_assets() / bundle)
    out = {g: [] for g in groups}
    for k, obj in env.container.items():
        kl = k.lower()
        if "eventbinary/" not in kl or not kl.endswith(".eb.bytes"):
            continue
        group = kl.split("eventbinary/")[1].split("/")[0]
        if group in out:
            out[group].append((kl, obj))
    return out


def test_roundtrip_nonfield_corpus_sweep():
    """Rung 7: ALL 93 world event binaries (including the 2 jp argFlag-noise files, which must
    now round-trip via the raw= fallback) + a battle sample. Loud counts — a missing group
    fails, never skips silently. The full 9753 sweep is the CLI gate."""
    from ff9mapkit.config import ConfigError
    try:
        by_group = _nonfield_binaries(["battle", "world"])
    except (ImportError, ModuleNotFoundError, RuntimeError, ConfigError, FileNotFoundError):
        pytest.skip("needs the FF9 install + UnityPy")
    from ff9mapkit import extract
    world = sorted(by_group["world"])
    assert len(world) >= 90, f"world corpus incomplete: {len(world)}"
    for key, obj in world:
        data = extract._raw_bytes(obj.read())
        assert assemble_source(write_source(data, enrich=False)) == data, key
    battle = sorted(by_group["battle"])[::60]
    assert len(battle) >= 60, f"battle sample too small: {len(battle)}"
    for key, obj in battle:
        data = extract._raw_bytes(obj.read())
        assert assemble_source(write_source(data, enrich=False)) == data, key
