"""`.ebs` whole-file round-trip (eb/ebsrc.py) — the eb-roundtrip arc's Rung 2/3 tests.

Offline tests drive a KIT-AUTHORED synthetic .eb (raw instruction bytes assembled here — zero
Square-Enix bytes), covering the envelope grammar the Rung-1 census froze: interior + trailing
empty slots (the parked-off rule), zero-length funcs, loc/flags/pad attrs, byte2, the name
block, and the writer's self-verify refusal on a non-canonical layout. The install-gated
sweep round-trips REAL binaries (all us + a cross-language sample) and reports its count
loudly — a partial corpus must never read as a full pass.
"""
import struct

import pytest

from ff9mapkit.eb import ebsrc
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


def test_roundtrip_synthetic():
    data = _demo_eb(name=b"Test/Room\x00")
    src = write_source(data, title="synthetic demo")     # self-verifies internally
    assert assemble_source(src) == data
    assert "# synthetic demo" in src.splitlines()[0]


def test_writer_is_a_fixpoint():
    data = _demo_eb()
    src = write_source(data)
    assert write_source(assemble_source(src)) == src


def test_parse_matches_model_view():
    data = _demo_eb(name=b"NM", byte2=7, slot_meta={2: (3, 1, 9)})
    src = write_source(data)
    assert ".byte2 7" in src
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


def test_self_verify_refuses_noncanonical_layout():
    data = bytearray(_demo_eb())
    eb = EbScript.from_bytes(bytes(data))
    empt = next(e for e in eb.entries if e.empty)
    off_at = 0x80 + empt.index * 8
    data[off_at:off_at + 2] = struct.pack("<H", 12345)   # break the parked-off rule
    with pytest.raises(EbSrcError, match="self-verify"):
        write_source(bytes(data))


@pytest.mark.parametrize("mutate,msg", [
    (lambda s: s.replace(".ebs 1", ".ebs 9"), "version"),
    (lambda s: s.replace(".ebs 1\n", ""), "first directive|missing .ebs"),
    (lambda s: "\n".join(ln for ln in s.splitlines() if not ln.startswith(".name")), "missing .name"),
    (lambda s: s.replace(".entry 1 EMPTY\n", ""), "missing .entry"),
    (lambda s: s.replace(".entry 1 EMPTY", ".entry 1 EMPTY\n.entry 1 EMPTY"), "duplicate .entry"),
    (lambda s: s.replace(".entry 1 EMPTY", ".entry 1 EMPTY\nRET()"), "outside a .func"),
    (lambda s: s.replace(".entry 1 EMPTY", ".entry 1 EMPTY\n.func 0"), "outside a non-empty"),
    (lambda s: s + ".wat 3\n", "unknown directive"),
])
def test_grammar_errors(mutate, msg):
    src = write_source(_demo_eb())
    with pytest.raises(EbSrcError, match=msg):
        assemble_source(mutate(src))


def test_all_empty_refused():
    with pytest.raises(EbSrcError, match="non-empty"):
        assemble_source(".ebs 1\n.name " + "00" * 124 + "\n.entry 0 EMPTY\n")


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
    green on nothing. The full 818x7 sweep is the CLI: ``ff9mapkit eb-src --verify-all``."""
    from ff9mapkit import extract
    try:
        by_lang = _bundle_binaries(["us", "jp", "fr"])
    except Exception:                                     # noqa: BLE001 -- no install / no UnityPy
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
