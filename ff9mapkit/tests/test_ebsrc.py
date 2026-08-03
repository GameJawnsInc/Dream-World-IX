"""`.ebs` whole-file round-trip (eb/ebsrc.py) — the eb-roundtrip arc's Rung 2/3 tests.

Offline tests drive KIT-AUTHORED synthetic .eb bytes (assembled here — zero Square-Enix
bytes), covering: the envelope grammar the Rung-1 census froze (interior + trailing empty
slots, zero-length funcs, loc/flags/pad, byte2, the name block), the adversarial-review
hardening (off= overrides for kit-edited layouts, the raw= entry escape hatch, the
EbSrcError-everywhere contract, BOM tolerance, hand-authored-source fixpoint), and the three
CLI verbs. The install-gated sweep round-trips REAL binaries and reports its count loudly —
a partial corpus must never read as a full pass.
"""
import struct

import pytest

from ff9mapkit.eb.ebsrc import EbSrcError, assemble_source, write_source
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
