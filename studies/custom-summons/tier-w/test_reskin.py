r"""Tests for TIER W rung 4 -- THE RESKIN (``reskin.py``).

Runs WITHOUT the extracted corpus: most tests synthesise their own ``ef###``-shaped container (a
minimal id-0 scenery CLUT resource + an id-4/id-5 creature package, following
``test_retime.py``'s posture of building a container BY HAND rather than trusting the real install),
so the transform, the five hard rules, the build-time refusals and the ledger/revert round-trip are
all exercised on bytes this file wrote.  A handful of tests need the user's own FF9 install (the real
ef227 container) or the extracted corpus and are skipped when absent, exactly as ``test_rescore.py``
and ``test_retime.py`` do.

    py -m pytest studies/custom-summons/tier-w/test_reskin.py -q

THE SYNTHETIC CONTAINER (section 0) is deliberately minimal: ONE chunk carrying an id-0 scenery
resource (one inline CLUT rect spanning VRAM rows 244-245, so the two named cells the real
``ATTRIBUTION`` table already declares -- ``(0,244)`` SHARED ``water_and_sky_gradient`` and
``(0,245)`` ``sky_dome`` -- resolve without inventing new attribution), an id-3 filler resource (a
stand-in "program image", any bytes), and an id-4/id-5 creature package (N parts, each an 8bpp page
+ a whole 256-entry CLUT row, laid out exactly as ``ff9mapkit.summons.texture.texture_check``
requires).  No camera archive (id-2) is included -- the all-zero sequence stream decodes to a single
immediate END op, so ``summon_camera.extract_shots`` resolves zero shots, which is a legitimate
(if unusually quiet) container rather than an error.

Every CLUT word in this file is COMPUTED (a small arithmetic generator), never a byte run copied from
the corpus or the install -- ``ff9mapkit``'s provenance rule applies to this file exactly as it does
to ``reskin.py`` itself.
"""
from __future__ import annotations

import dataclasses
import glob
import hashlib
import os
import struct
import subprocess
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import reskin as RS                                             # noqa: E402  (sets up sys.path)
import ef_container as EC                                        # noqa: E402
import summon_camera as W                                        # noqa: E402
from ff9mapkit.summons import container as KC                    # noqa: E402
from ff9mapkit.summons import texture as KT                       # noqa: E402

#: this module has no corpus-only test (its install-gated tests already exercise the real ef227 data
#: the corpus was extracted from) -- kept for parity with test_rescore.py's / test_retime.py's own
#: posture, in case a future addition here needs it.
CORPUS = W.SCRATCH_CORPUS
have_corpus = bool(glob.glob(os.path.join(CORPUS, "ef*.bytes")))
needs_corpus = pytest.mark.skipif(not have_corpus, reason="no extracted corpus at %s" % CORPUS)


def _has_install() -> bool:
    try:
        from ff9mapkit import config
        return bool(config.find_game_path(None))
    except Exception:
        return False


needs_install = pytest.mark.skipif(not _has_install(), reason="no FF9 install resolvable")

SPEC = os.path.join(_HERE, "bahamut_reskin.toml")
SECTOR = W.SECTOR


# ============================================================ (0) the synthetic container
#: the two real VRAM cells ``ATTRIBUTION`` already names -- reused so the synthetic scenery
#: resolves to real (SHARED / non-shared) names rather than inventing new attribution rows.
_SHARED_WORD = 0x3D00          # VRAM (0, 244) -> scenery.water_and_sky_gradient (16-entry, SHARED)
_SKYDOME_WORD = 0x3D40         # VRAM (0, 245) -> scenery.sky_dome (256-entry, not shared)


def _pad_sector(payload: bytes):
    n = max(1, (len(payload) + SECTOR - 1) // SECTOR)
    return payload.ljust(n * SECTOR, b"\x00"), n


def synth_clut16(zero_first: bool = True):
    """16 COMPUTED BGR555 words (never a byte run copied from anywhere)."""
    out = []
    for i in range(16):
        if i == 0 and zero_first:
            out.append(0)
            continue
        r, g, b = (i * 3 + 1) & 0x1F, (i * 7 + 2) & 0x1F, (i * 11 + 5) & 0x1F
        stp = 0x8000 if i % 4 == 0 else 0
        out.append(stp | r | (g << 5) | (b << 10))
    return out


def synth_clut256(seed: int = 1, zero_first: bool = True):
    out = []
    for i in range(256):
        if i == 0 and zero_first:
            out.append(0)
            continue
        r = (i * seed + 1) & 0x1F
        g = (i * seed * 3 + 2) & 0x1F
        b = (i * seed * 5 + 7) & 0x1F
        stp = 0x8000 if i % 6 == 0 else 0
        out.append(stp | r | (g << 5) | (b << 10))
    return out


def _words(ws):
    return struct.pack("<%dH" % len(ws), *ws)


def _build_scenery_id0(pal16, pal256) -> bytes:
    """One id-0 payload: a single inline rect covering VRAM rows 244-245 (w=256, h=2), with a
    16-entry CLUT at row 244 x=0 and a 256-entry CLUT at row 245 x=0 -- exactly the layout
    ``reskin.id0_palettes`` decodes (module docstring section (1))."""
    buf = bytearray(0x424)
    struct.pack_into("<iii", buf, 0x00, 0x14, 0x1C, 1)      # pageBlockRel, inlineRel, nInline=1
    struct.pack_into("<HH", buf, 0x0C, 1, 1)                 # nClut4=1, nClut8=1
    struct.pack_into("<HH", buf, 0x10, _SHARED_WORD, _SKYDOME_WORD)
    struct.pack_into("<ii", buf, 0x14, 0x424, 0)             # pixelDataRel, nPageRects=0
    struct.pack_into("<HHHH", buf, 0x1C, 0, 244, 256, 2)     # inline rect: x=0 y=244 w=256 h=2
    row244 = bytearray(512)
    row244[0:32] = _words(pal16)
    buf[0x24:0x24 + 512] = row244
    buf[0x224:0x224 + 512] = _words(pal256)
    return bytes(buf)


def _build_creature_id4(npart: int, pal256_list) -> bytes:
    """One id-4 payload: a header (``texOffset=0x180``, ``motionCount=0``) + ``npart`` 8bpp pages
    (zero pixel data -- the palette tests never sample the pixels) + ``npart`` 256-entry CLUT rows,
    one per part, at consecutive strip rows starting ``KT.CLUT_STRIP_Y`` (matching
    ``texture_check``'s decodable layout exactly: mode-1 tpage, entry0 == 0, row in range)."""
    tex_off = 0x180
    tex_bytes = npart * KT.PAGE_BYTES
    clut_rows = npart
    clut_bytes = clut_rows * 0x200
    header = bytearray(tex_off)
    struct.pack_into("<hhhH", header, 0, tex_off, 0, npart, clut_rows)
    struct.pack_into("<II", header, 8, tex_bytes, clut_bytes)
    struct.pack_into("<II", header, 0x10, 0, 0)               # modelBytes/firstBlock -- unused here
    for i in range(npart):
        struct.pack_into("<H", header, 0x18 + 2 * i, 0x80)    # tpage: mode 1 (8bpp)
        clutword = ((KT.CLUT_STRIP_Y + i) << 6) | 0x10        # row i, entry0 == 0
        struct.pack_into("<H", header, 0x24 + 2 * i, clutword)
        struct.pack_into("<H", header, 0x30 + 2 * i, 0)       # v_offset
    pages = bytes(npart * KT.PAGE_BYTES)
    cluts = b"".join(_words(w) for w in pal256_list)
    return bytes(header) + pages + cluts


def build_synth_container(npart: int = 2, id3_size: int = 1) -> bytes:
    """A whole ``ef###.bytes``-shaped container: one chunk with id-0 (scenery), id-3 (a filler
    "program image"), id-4+id-5 (the creature).  No id-2 camera archive -- the all-zero sequence
    stream decodes to a single immediate END op, so ``extract_shots`` resolves zero shots."""
    id0 = _build_scenery_id0(synth_clut16(), synth_clut256(seed=3))
    id3 = bytes([0x55]) * (id3_size * SECTOR)
    id4 = _build_creature_id4(npart, [synth_clut256(seed=5 + i) for i in range(npart)])
    id5 = bytes([0x66]) * SECTOR
    resources = [(0, id0), (3, id3), (4, id4), (5, id5)]
    padded = [(rid,) + _pad_sector(p) for rid, p in resources]
    head = bytearray(struct.pack("<h", 1))                    # chunk_count = 1
    head += struct.pack("<hh", 0, len(padded))                # chunkIndex=0, resourceCount
    for rid, _p, n in padded:
        head += struct.pack("<bbh", rid, 0, n)
    assert len(head) <= SECTOR
    blob = bytearray(head.ljust(SECTOR, b"\x00"))
    for _rid, p, _n in padded:
        blob += p
    return bytes(blob)


def _spec(blob: bytes, targets, effect: int = 999, spans=None) -> dict:
    r = {"effect": effect, "label": "synthtest", "expect_sha256": hashlib.sha256(blob).hexdigest(),
        "target": targets}
    if spans:
        r["spans"] = spans
    return {"reskin": r}


def test_synth_container_is_well_formed_and_resolves_the_expected_palettes():
    """Sanity-checks the fixture ITSELF (section 0) so a later test failure cannot be a synthetic
    container bug masquerading as a ``reskin.py`` bug."""
    blob = build_synth_container(npart=2)
    c = EC.parse_header(blob, strict=True)
    assert c.cursor_end == len(blob)
    mp = KC.creature_package(blob)
    assert mp is not None
    chk = KT.texture_check(blob, mp)
    assert chk["decodable"], chk["reasons"]
    pmap = RS.palette_map(blob)
    names = sorted(p.name for p in pmap.palettes)
    assert names == ["creature.part0", "creature.part1",
                     "scenery.sky_dome", "scenery.water_and_sky_gradient"]
    shared = {p.name: p.shared for p in pmap.palettes}
    assert shared["scenery.water_and_sky_gradient"] is True
    assert shared["scenery.sky_dome"] is False
    assert shared["creature.part0"] is False


# ============================================================ (1) BGR555 decode/encode round-trip
def test_apply_word_identity_transform_round_trips_every_16bit_word_including_stp():
    """The identity ``Transform()`` (hue 0, sat 1, val 1) must be BYTE-EXACT on EVERY possible
    16-bit word -- both STP states and all 32768 RGB combinations -- proving decode-then-encode is
    lossless before any hue/sat/val math is layered on top."""
    bad = []
    for w in range(65536):
        nw, clip = RS.apply_word(w, RS.Transform())
        if nw != w or clip:
            bad.append((w, nw, clip))
    assert not bad, bad[:10]


def test_apply_word_reconstructs_the_five_bit_channels_exactly_for_a_pure_hue_rotation():
    """A hue-only rotation (sat=val=1) must be an EXACT permutation of the 5-bit wheel: rotating by
    +120 degrees three times must return to the original word for every non-achromatic sample (an
    achromatic S=0 entry is invariant under hue rotation by construction, so it is excluded)."""
    for w in range(1, 65536, 37):
        r, g, b = w & 0x1F, (w >> 5) & 0x1F, (w >> 10) & 0x1F
        if r == g == b:                                        # achromatic: hue is undefined/inert
            continue
        cur = w
        for _ in range(3):
            cur, _clamped = RS.apply_word(cur, RS.Transform(hue=120.0))
        # 3 x 120deg == a full turn: same STP, same-ish colour (allow the 5-bit re-quantisation's
        # own rounding to differ by at most 1 per channel after three round-trips)
        assert (cur & 0x8000) == (w & 0x8000)
        for shift in (0, 5, 10):
            a, bch = (w >> shift) & 0x1F, (cur >> shift) & 0x1F
            assert abs(a - bch) <= 1, (hex(w), hex(cur))


# ============================================================ (2) the STP-preservation refusal
def test_apply_word_carries_stp_bit_never_recomputes_it():
    """Sweep a broad range of transforms (including ones no spec would ever declare) against words
    with STP both set and clear: bit 15 of the output must ALWAYS equal bit 15 of the input --
    ``apply_word`` slices it off before the HSV math and ORs it back after, so this cannot fail by
    construction; the sweep is the proof, not a hope."""
    hues = (0, 30, 90, 137.5, 182, 270, 359.9)
    sats = (0, 0.01, 0.5, 1.0, 2.0, 4.0)
    vals = (0, 0.01, 0.5, 1.0, 2.0, 4.0)
    checked = 0
    for w in range(1, 65536, 101):                            # word 0 is covered separately below
        for h in hues:
            for s in sats:
                for v in vals:
                    nw, _c = RS.apply_word(w, RS.Transform(hue=h, sat=s, val=v))
                    assert (nw & 0x8000) == (w & 0x8000), (hex(w), h, s, v, hex(nw))
                    checked += 1
    assert checked > 20000


def test_palette_result_ok_is_true_when_stp_populations_match():
    """The REAL check path: ``apply_palette`` on a genuine (small) CLUT, then ``.ok`` reads True
    because ``apply_word`` really did carry every STP bit."""
    blob = build_synth_container(npart=1)
    pmap = RS.palette_map(blob)
    pal = pmap.by_name("creature.part0")
    res = RS.apply_palette(blob, pal, RS.Transform(hue=77.0, sat=0.6, val=1.1))
    assert res.stp_stock == res.stp_new
    assert res.ok


def test_palette_result_ok_fires_false_on_a_crafted_stp_mismatch():
    """Prove the GUARD fires, not just that the honest path passes: take a real, good result and
    corrupt exactly the field the rule reads (``stp_new``) to simulate a hypothetical STP-flipping
    bug -- ``.ok`` must flip to False on that alone, with nothing else touched."""
    blob = build_synth_container(npart=1)
    pmap = RS.palette_map(blob)
    pal = pmap.by_name("creature.part0")
    good = RS.apply_palette(blob, pal, RS.Transform(hue=10.0))
    assert good.ok
    bad = dataclasses.replace(good, stp_new=good.stp_new + 1)
    assert not bad.ok
    # and the self_check-level expression (the one `self_check` itself evaluates per palette) agrees
    assert bad.stp_stock != bad.stp_new


# ============================================================ (3) entry-0 immutability
def test_apply_word_zero_entry_is_invariant_under_any_transform():
    """``0x0000`` must return ``0x0000`` under EVERY transform this sweep can construct -- rule 1
    is checked FIRST in ``apply_word``, before any HSV math runs at all."""
    hues = range(0, 360, 15)
    sats = (0, 0.5, 1.0, 2.0, 4.0, 1000.0)
    vals = (0, 0.5, 1.0, 2.0, 4.0, 1000.0)
    for h in hues:
        for s in sats:
            for v in vals:
                assert RS.apply_word(0, RS.Transform(hue=h, sat=s, val=v)) == (0, 0)


def test_entry0_guard_fires_on_a_crafted_non_zero_entry0():
    """Stock entry 0 of ``creature.part0`` is ``0x0000`` (by our fixture's own construction).  A
    genuine hue rotation cannot move it (previous test).  Here we simulate what WOULD happen if a
    hypothetical bug did move it -- corrupt ``result.new``'s own bytes so entry 0 reads non-zero --
    and confirm the exact boolean ``self_check`` evaluates per target
    (``_u16(stock,0)==0 and _u16(new,0)!=0``) reports it as a violation."""
    blob = build_synth_container(npart=1)
    pmap = RS.palette_map(blob)
    pal = pmap.by_name("creature.part0")
    good = RS.apply_palette(blob, pal, RS.Transform(hue=25.0))
    assert RS._u16(good.stock, 0) == 0                        # the fixture's own precondition
    assert RS._u16(good.new, 0) == 0                          # rule 1 held for real

    corrupted_new = bytearray(good.new)
    struct.pack_into("<H", corrupted_new, 0, 0x1234)          # simulate a broken transform
    bad = dataclasses.replace(good, new=bytes(corrupted_new))
    assert RS._u16(bad.stock, 0) == 0 and RS._u16(bad.new, 0) != 0, "the guard failed to fire"


def test_zero_positions_held_guard_fires_when_a_cutout_entry_moves():
    """The broader rule ("no 0x0000 moved, and no entry became one") is its own field
    (``zero_positions_held``); prove ``.ok`` reads it independently of the STP check by flipping
    ONLY this field on an otherwise-good result."""
    blob = build_synth_container(npart=1)
    pmap = RS.palette_map(blob)
    pal = pmap.by_name("creature.part0")
    good = RS.apply_palette(blob, pal, RS.Transform(hue=200.0))
    assert good.ok
    bad = dataclasses.replace(good, zero_positions_held=False)
    assert not bad.ok


# ============================================================ (4) channel clamping at 0/31
def test_clamp01_boundaries():
    assert RS._clamp01(-0.5) == 0.0
    assert RS._clamp01(1.5) == 1.0
    assert RS._clamp01(0.37) == 0.37
    assert RS._clamp01(0.0) == 0.0
    assert RS._clamp01(1.0) == 1.0


def test_apply_word_output_channels_always_land_in_0_31_even_at_extreme_scales():
    """``_clamp01`` bounds ``s``/``v`` into ``[0,1]`` BEFORE ``colorsys.hsv_to_rgb`` runs, and HSV's
    own algebra guarantees ``max(r,g,b) == v`` -- so no legal channel value can ever exceed 31,
    however large ``saturation``/``value`` are asked to go (the 4x ceiling is enforced by the SPEC
    layer, ``_transform_of``, not by ``apply_word`` itself).  This sweeps well past that ceiling to
    prove the OUTPUT stays in range regardless."""
    hues = (0, 45, 137.5, 271.3)
    extreme = (0, 0.01, 1.0, 4.0, 1000.0, 1_000_000.0)
    n = 0
    for w in range(1, 65536, 251):
        for h in hues:
            for s in extreme:
                for v in extreme:
                    nw, _c = RS.apply_word(w, RS.Transform(hue=h, sat=s, val=v))
                    r, g, b = nw & 0x1F, (nw >> 5) & 0x1F, (nw >> 10) & 0x1F
                    assert 0 <= r <= 31 and 0 <= g <= 31 and 0 <= b <= 31
                    n += 1
    assert n > 2000


def test_apply_word_channel_clamp_bit_is_structurally_unreachable():
    """``CLIP_CHANNEL`` can never fire through this path: ``_clamp01`` caps ``s``/``v`` to ``[0,1]``
    before the HSV math, and ``hsv_to_rgb``'s largest component is exactly ``v``, so
    ``int(f * 31.0 + 0.5)`` tops out at ``int(31.5) == 31``.

    This is pinned because it is exactly WHY the channel clamp must not be the reported instrument:
    a counter that cannot count reports "all clear" for every input, including a ruinous one.  The
    reachable clip -- the HSV one -- is what ``reskin`` counts and gates, and the two tests below
    prove THAT one fires."""
    hit = 0
    for w in range(0, 65536, 97):
        for h in (0, 90, 180, 270):
            for s in (0.0, 1.0, 4.0, 1e6):
                for v in (0.0, 1.0, 4.0, 1e6):
                    _nw, clip = RS.apply_word(w, RS.Transform(hue=h, sat=s, val=v))
                    hit |= clip & RS.CLIP_CHANNEL
    assert hit == 0


def test_apply_word_flags_a_value_knob_that_pushes_an_entry_past_the_cube():
    """THE REGRESSION TEST for the dead-instrument defect.  A bright entry under ``value > 1`` must
    set ``CLIP_VAL`` -- this is the case the old ``clamped`` counter reported as zero."""
    bright = 28 | (28 << 5) | (28 << 10)                        # V = 28/31 = 0.9032, ef227's own peak
    _nw, clip = RS.apply_word(bright, RS.Transform(val=1.12))   # 0.9032 * 1.12 = 1.0116 -> clipped
    assert clip & RS.CLIP_VAL
    assert not clip & RS.CLIP_SAT                               # achromatic: S = 0, nothing to clip
    assert not clip & RS.CLIP_CHANNEL                           # ...and the belt still never fires
    # ...and the SAME entry under a value that fits reports nothing
    _nw2, clip2 = RS.apply_word(bright, RS.Transform(val=1.10))  # 0.9032 * 1.10 = 0.9935 -> fits
    assert clip2 == 0


def test_apply_word_flags_a_saturation_knob_that_pushes_an_entry_past_the_cube():
    """The other half: a fully-saturated entry under ``saturation > 1`` sets ``CLIP_SAT``."""
    saturated = 31 | (0 << 5) | (0 << 10)                       # pure red: S = 1.00, V = 1.00
    _nw, clip = RS.apply_word(saturated, RS.Transform(sat=1.30))
    assert clip & RS.CLIP_SAT
    assert not clip & RS.CLIP_VAL                               # V = 1.00 * 1.00 fits exactly
    _nw2, clip2 = RS.apply_word(saturated, RS.Transform(sat=1.0))
    assert clip2 == 0


def test_apply_palette_counts_the_clip_per_palette_and_splits_saturation_from_value():
    """The counter has to survive the aggregation step too: ``apply_palette`` must report a non-zero
    ``clipped`` with the sat/value split and a ``worst_*`` overshoot above 1.0, and must report zero
    for a transform that fits."""
    blob = build_synth_container(npart=1)
    pmap = RS.palette_map(blob)
    pal = pmap.by_name("creature.part0")

    hot = RS.apply_palette(blob, pal, RS.Transform(val=3.0))
    assert hot.clipped > 0
    assert hot.val_clipped == hot.clipped and hot.sat_clipped == 0
    assert hot.worst_val > 1.0
    assert hot.chan_clamped == 0                                # the belt, still inert
    assert 0.0 < hot.clip_fraction <= 1.0

    calm = RS.apply_palette(blob, pal, RS.Transform(hue=90.0))
    assert calm.clipped == 0 and calm.sat_clipped == 0 and calm.val_clipped == 0
    assert calm.worst_val <= 1.0 and calm.clip_fraction == 0.0


def test_self_check_blowout_gate_FAILS_on_an_over_bright_knob_and_refuses_the_stage():
    """THE GATE, not the counter: a ``value`` large enough to flatten most of a palette onto the
    ceiling must make ``self_check`` report NOT ok, which is what stops ``reskin.py build`` from
    staging it.  This is the failure the old always-True gate would have printed as PASS."""
    blob = build_synth_container(npart=1)
    spec = _spec(blob, [{"name": "creature.part0", "hue_rotate": 0.0, "value": 3.0}])
    b = RS.build(spec, "t", blob=blob)
    c = RS.self_check(b)
    blow = [g for g in c.rules if "flattens more than" in g.name]
    assert len(blow) == 1
    assert not blow[0].ok, blow[0].detail
    assert "BLOWN OUT" in blow[0].detail and "creature.part0" in blow[0].detail
    assert not c.ok                                             # -> `build` refuses to stage


def test_self_check_blowout_gate_PASSES_when_only_a_few_ceiling_entries_clip():
    """The gate must not be a tripwire on any clip at all: a handful of already-at-the-ceiling
    entries is normal (they cannot go further) and must still pass, with the census REPORTED."""
    blob = build_synth_container(npart=1)
    pmap = RS.palette_map(blob)
    pal = pmap.by_name("creature.part0")
    # find a value scale that clips a small, non-zero share of this fixture's own palette
    knob = next((v for v in [1.0 + i / 200.0 for i in range(1, 60)]
                 if 0 < RS.apply_palette(blob, pal, RS.Transform(val=v)).clip_fraction
                 <= RS.BLOWOUT_FRACTION), None)
    assert knob is not None, "the fixture palette admits no small-clip value knob"
    spec = _spec(blob, [{"name": "creature.part0", "value": knob}])
    b = RS.build(spec, "t", blob=blob)
    c = RS.self_check(b)
    blow = [g for g in c.rules if "flattens more than" in g.name][0]
    assert blow.ok
    assert "clipped" in blow.detail and "creature.part0" in blow.detail    # reported, not hidden
    assert "BLOWN OUT" not in blow.detail


def test_self_check_channel_belt_gate_is_reported_separately_from_the_hsv_census():
    """The structural belt gets its OWN gate so the two are never confused again: it passes with a
    zero count, and its detail says WHY zero is expected rather than implying nothing clipped."""
    blob = build_synth_container(npart=1)
    spec = _spec(blob, [{"name": "creature.part0", "hue_rotate": 30.0}])
    b = RS.build(spec, "t", blob=blob)
    c = RS.self_check(b)
    belt = [g for g in c.rules if "channel clamp never had to fire" in g.name]
    assert len(belt) == 1 and belt[0].ok
    assert "0 entries clamped" in belt[0].detail
    assert "_clamp01" in belt[0].detail


# ============================================================ (5) build()-level refusals (7 kinds,
#     matching the B1 report's "7/7 negative tests refuse")
def test_build_refuses_a_shared_clut_named_without_acknowledgment():
    blob = build_synth_container(npart=1)
    spec = _spec(blob, [{"name": "scenery.water_and_sky_gradient", "hue_rotate": 30.0}])
    with pytest.raises(RS.ReskinError, match="SHARED palette"):
        RS.build(spec, "t", blob=blob)


def test_build_accepts_a_shared_clut_named_with_acknowledgment():
    blob = build_synth_container(npart=1)
    spec = _spec(blob, [{"name": "scenery.water_and_sky_gradient", "hue_rotate": 30.0,
                         "acknowledge_shared": True}])
    b = RS.build(spec, "t", blob=blob)
    assert b.targets[0].enabled and b.targets[0].result is not None
    assert len(b.patched) == len(b.orig)


def test_build_refuses_an_unknown_target_name():
    blob = build_synth_container(npart=1)
    spec = _spec(blob, [{"name": "creature.part99", "hue_rotate": 30.0}])
    with pytest.raises(RS.ReskinError, match="no palette named"):
        RS.build(spec, "t", blob=blob)


def test_build_refuses_a_drifted_stock_hash():
    blob = build_synth_container(npart=1)
    spec = _spec(blob, [{"name": "creature.part0", "hue_rotate": 30.0}])
    spec["reskin"]["expect_sha256"] = "0" * 64
    with pytest.raises(RS.R.StockDriftError):
        RS.build(spec, "t", blob=blob)


def test_build_refuses_a_saturation_scale_past_the_4x_clip_ceiling():
    blob = build_synth_container(npart=1)
    spec = _spec(blob, [{"name": "creature.part0", "hue_rotate": 30.0, "saturation": 4.01}])
    with pytest.raises(RS.ReskinError, match="above 4x"):
        RS.build(spec, "t", blob=blob)


def test_build_refuses_a_disagreeing_per_target_offset_guard():
    blob = build_synth_container(npart=1)
    spec = _spec(blob, [{"name": "creature.part0", "hue_rotate": 30.0, "expect_offset": 0x1234}])
    with pytest.raises(RS.ReskinError, match="the derivation says"):
        RS.build(spec, "t", blob=blob)


def test_build_refuses_a_disagreeing_vram_guard():
    blob = build_synth_container(npart=1)
    spec = _spec(blob, [{"name": "creature.part0", "hue_rotate": 30.0, "expect_vram": [1, 2]}])
    with pytest.raises(RS.ReskinError, match="the header declares"):
        RS.build(spec, "t", blob=blob)


def test_build_refuses_a_disagreeing_span_guard():
    blob = build_synth_container(npart=1)
    spec = _spec(blob, [{"name": "creature.part0", "hue_rotate": 30.0}],
                 spans={"creature_clut_strip": {"offset": 0x1234, "length": 999}})
    with pytest.raises(RS.ReskinError, match="refusing to splice"):
        RS.build(spec, "t", blob=blob)


# ============================================================ (6) span containment + orthogonality
#     falsifiability (the "regions" self-check, which reskin.py's own docstring files under
#     ORTHOGONALITY: "on top of that it gates whole regions byte-identical")
def test_self_check_flags_a_byte_changed_outside_every_named_span_and_region():
    """Plant a single byte diff INSIDE the creature's texture PAGES -- outside the
    ``creature_clut_strip`` span, outside the scenery span, and with zero enabled targets (so no
    target owns it either).  Every one of the following must independently notice:
      * accounting: the byte is unexplained (`in owner`) AND outside every derived span
      * regions: the id-4 header+texel region is no longer byte-identical
      * the dedicated "texel region untouched" gate also fails
    This is the falsifiability half of ORTHOGONALITY (reskin.py's own docstring: the self-check
    "gates whole regions byte-identical" IS the orthogonality proof's other leg, on top of the
    W2/W3 rebuild-intersection check)."""
    blob = build_synth_container(npart=2)
    pmap = RS.palette_map(blob)
    mp = KC.creature_package(blob)
    flip_off = mp.tex_file_offset + 100                       # well inside part0's page, not a CLUT
    patched = bytearray(blob)
    patched[flip_off] ^= 0xFF
    patched = bytes(patched)

    b = RS.Build(effect=999, label="synth", spec_path="t.toml", source="(synthetic)",
                orig=blob, patched=patched, sha_in=hashlib.sha256(blob).hexdigest(),
                sha_out=hashlib.sha256(patched).hexdigest(), pmap=pmap, targets=[])
    chk = RS.self_check(b)
    assert not chk.ok

    acc_by_name = {g.name: g for g in chk.accounting}
    assert acc_by_name["every changed byte belongs to a named target"].ok is False
    assert acc_by_name["every changed byte lands inside a derived CLUT span"].ok is False

    reg_by_name = {g.name: g for g in chk.regions}
    region_gate = reg_by_name["every geometry / program / camera / sequence region is "
                              "BYTE-IDENTICAL"]
    assert region_gate.ok is False
    assert "texel pages" in region_gate.detail

    texel_gate = reg_by_name["the id-4 TEXEL region is untouched and still decodes"]
    assert texel_gate.ok is False


def test_region_gate_fires_on_a_planted_diff_inside_the_id3_program_image():
    """The most literal reading of the falsifiability requirement: plant the diff inside the id-3
    resource itself -- ``_regions`` names it "id-3 effect program image" -- and confirm the regions
    gate catches exactly that hit, by name, while a build that never touches id-3 stays clean."""
    blob = build_synth_container(npart=1)
    pmap = RS.palette_map(blob)
    id3 = next(r for r in EC.parse_header(blob).chunks[0].resources if r.id == 3)
    patched = bytearray(blob)
    patched[id3.offset + 5] ^= 0xFF
    patched = bytes(patched)

    b = RS.Build(effect=999, label="synth", spec_path="t.toml", source="(synthetic)",
                orig=blob, patched=patched, sha_in=hashlib.sha256(blob).hexdigest(),
                sha_out=hashlib.sha256(patched).hexdigest(), pmap=pmap, targets=[])
    chk = RS.self_check(b)
    assert not chk.ok
    reg_by_name = {g.name: g for g in chk.regions}
    region_gate = reg_by_name["every geometry / program / camera / sequence region is "
                              "BYTE-IDENTICAL"]
    assert region_gate.ok is False
    assert "id-3 effect program image" in region_gate.detail


def test_self_check_passes_accounting_and_regions_for_a_real_target_driven_build():
    """The positive control: a build that only ever spliced bytes through a real, enabled target
    must report every accounting/region/rule gate clean (quality is NOT asserted here -- our
    synthetic CLUT is arithmetic noise, not a real palette, so the luminance-ordering quality gate
    is not expected to hold on it; that gate is about REAL art, not about this fixture).

    The saturation knob here is a REDUCTION for the same fixture reason: this synthetic CLUT is a
    modular arithmetic ramp, so an unnaturally large share of its entries sit at S = 1.00 and any
    saturation LIFT clips them (measured: ``1.2`` clips 63 of 510, 12.4%, past ``BLOWOUT_FRACTION``).
    That is a property of the fixture, not a defect -- the blow-out gate's own behaviour on a lift is
    asserted directly in section (4), on both sides."""
    blob = build_synth_container(npart=2)
    spec = _spec(blob, [{"name": "creature.part0", "hue_rotate": 90.0},
                        {"name": "scenery.sky_dome", "hue_rotate": 45.0, "saturation": 0.8}])
    b = RS.build(spec, "t", blob=blob)
    chk = RS.self_check(b)
    for g in chk.accounting + chk.rules:
        assert g.ok, (g.name, g.detail)
    for g in chk.regions:
        assert g.ok, (g.name, g.detail)


def test_orthogonality_rebuild_gates_are_present_and_named():
    """``_orthogonality`` always emits exactly two named gates (W2 disjoint, W3 disjoint), whether
    or not the real specs/install are available -- a missing install turns them FAIL, not absent."""
    blob = build_synth_container(npart=1)
    pmap = RS.palette_map(blob)
    b = RS.Build(effect=999, label="synth", spec_path="t.toml", source="(synthetic)",
                orig=blob, patched=blob, sha_in=hashlib.sha256(blob).hexdigest(),
                sha_out=hashlib.sha256(blob).hexdigest(), pmap=pmap, targets=[])
    chk = RS.self_check(b)
    names = [g.name for g in chk.orthogonality]
    assert any("W2's rescore" in n for n in names)
    assert any("W3's retime" in n for n in names)


# ============================================================ (7) the ledger / revert round-trip,
#     in temp dirs, including --root
def _manifest(root) -> dict:
    out = {}
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            p = os.path.join(dirpath, f)
            with open(p, "rb") as fh:
                out[os.path.relpath(p, root).replace("\\", "/")] = \
                    hashlib.sha256(fh.read()).hexdigest()
    return out


def _minimal_build(effect: int = 999, npart: int = 1) -> RS.Build:
    blob = build_synth_container(npart=npart)
    pmap = RS.palette_map(blob)
    patched = bytearray(blob)
    patched[EC.parse_header(blob).chunks[0].resources[1].offset] ^= 0xFF   # id-3 filler, any change
    patched = bytes(patched)
    return RS.Build(effect=effect, label="synth", spec_path="t.toml", source="(synthetic)",
                    orig=blob, patched=patched, sha_in=hashlib.sha256(blob).hexdigest(),
                    sha_out=hashlib.sha256(patched).hexdigest(), pmap=pmap, targets=[])


@pytest.mark.parametrize("seed_existing", [False, True])
def test_deploy_and_revert_round_trip_on_a_fake_mod_folder(tmp_path, seed_existing):
    """Proven against a MOCK live tree, never the install -- both the fresh-folder and the
    already-carrying-an-override cases, plus idempotent re-deploy and re-revert."""
    b = _minimal_build()
    game_root = tmp_path / "FAKE_GAME"
    mod = game_root / "FF9CustomMap"
    dest_dir = mod / "FF9_Data" / "SpecialEffects"
    dest_dir.mkdir(parents=True)
    prior = b"a pre-existing override that must come back byte-for-byte" if seed_existing else None
    if prior is not None:
        (dest_dir / "ef999").write_bytes(prior)
    before = _manifest(mod)

    out = RS.stage(b, root=tmp_path / "stage", game_root=str(game_root), previews=False)
    p = subprocess.run([sys.executable, out["scripts"]["deploy"]], capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr
    assert (dest_dir / "ef999").read_bytes() == b.patched

    # re-deploy is idempotent (the snapshot is taken once and reused)
    p2 = subprocess.run([sys.executable, out["scripts"]["deploy"]], capture_output=True, text=True)
    assert p2.returncode == 0
    assert (dest_dir / "ef999").read_bytes() == b.patched

    p3 = subprocess.run([sys.executable, out["scripts"]["revert"]], capture_output=True, text=True)
    assert p3.returncode == 0, p3.stdout + p3.stderr
    after = _manifest(mod)
    assert after == before
    if seed_existing:
        assert (dest_dir / "ef999").read_bytes() == prior
    else:
        assert not (dest_dir / "ef999").exists()

    # a second revert is idempotent
    p4 = subprocess.run([sys.executable, out["scripts"]["revert"]], capture_output=True, text=True)
    assert p4.returncode == 0
    assert _manifest(mod) == before


def test_deploy_script_refuses_with_no_root_and_succeeds_with_an_explicit_root_flag(tmp_path):
    """The W3-verifier-incident rule: a plan with no baked default mod folder (``game_root=None``
    at stage time) must REFUSE outright rather than guess, and must accept ``--root`` explicitly."""
    b = _minimal_build()
    out = RS.stage(b, root=tmp_path / "stage", game_root=None, previews=False)

    p = subprocess.run([sys.executable, out["scripts"]["deploy"]], capture_output=True, text=True)
    assert p.returncode != 0
    assert "no mod root" in p.stdout

    mod = tmp_path / "FAKE_GAME2" / "FF9CustomMap"
    (mod / "FF9_Data" / "SpecialEffects").mkdir(parents=True)
    p2 = subprocess.run([sys.executable, out["scripts"]["deploy"], "--root", str(mod)],
                        capture_output=True, text=True)
    assert p2.returncode == 0, p2.stdout + p2.stderr
    dest = mod / "FF9_Data" / "SpecialEffects" / "ef999"
    assert dest.read_bytes() == b.patched

    p3 = subprocess.run([sys.executable, out["scripts"]["revert"], "--root", str(mod)],
                        capture_output=True, text=True)
    assert p3.returncode == 0
    assert not dest.exists()


def test_deploy_refuses_a_mod_folder_carrying_a_modfilelist(tmp_path):
    """``TryFindAssetInModOnDisc`` TRUSTS an existing ``ModFileList.txt`` and never calls
    ``File.Exists``, so an unlisted override would be silently invisible -- the generated deploy
    script refuses outright rather than writing a file the engine will never find."""
    b = _minimal_build()
    mod = tmp_path / "FAKE_GAME" / "FF9CustomMap"
    mod.mkdir(parents=True)
    (mod / "ModFileList.txt").write_text("something/else\n", encoding="utf-8")
    out = RS.stage(b, root=tmp_path / "stage", game_root=str(tmp_path / "FAKE_GAME"), previews=False)
    p = subprocess.run([sys.executable, out["scripts"]["deploy"]], capture_output=True, text=True)
    assert p.returncode != 0
    assert "ModFileList.txt" in p.stdout


# ============================================================ (8) staging refusals (provenance)
def test_staging_refuses_the_repo():
    _repo = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
    with pytest.raises(RS.R.RescoreError, match="repo"):
        RS.R._refuse_repo_path(os.path.join(_repo, "studies", "x"))


def test_staging_refuses_the_install_unless_allow_install(tmp_path):
    game = tmp_path / "FINAL FANTASY IX"
    (game / "FF9CustomMap").mkdir(parents=True)
    b = _minimal_build()
    with pytest.raises(RS.R.RescoreError, match="game install"):
        RS.stage(b, root=game / "FF9CustomMap", game_root=str(game), previews=False)


# ============================================================ (9) the real install + corpus (skipped
#     when absent) -- exercises the ACTUAL shipped bahamut_reskin.toml against ef227
@needs_install
def test_the_shipped_spec_builds_and_self_checks_against_this_install():
    spec = RS.load_spec(SPEC)
    b = RS.build(spec, SPEC)
    b.check = RS.self_check(b)
    assert len(b.patched) == len(b.orig)
    assert b.check.ok, "\n".join("%s: %s" % (g.name, g.detail) for g in b.check.gates if not g.ok)


@needs_install
def test_the_install_still_matches_the_registered_drift_hash():
    import rescore as R
    blob, src = R.read_stock_effect(227)
    assert R.drift_guard(227, blob) == RS.R.EXPECTED_STOCK_SHA[227]
    assert "resources.assets" in src
