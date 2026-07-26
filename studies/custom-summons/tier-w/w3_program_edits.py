r"""TIER W rung 3 -- E1, THE PROGRAM EDIT SET for stretching ``ef227:c0`` state 0 by N = +48.

    py w3_program_edits.py                 # print the table + re-derive it from arithmetic

WHAT THIS IS
------------
``w3-recon/A2-PROGRAM.md`` found s0's phase length encoded **three times**: the ``slti`` threshold
(69) at image ``0x1278``, a magic reciprocal for **/69** at image ``0x0b6c``, and a magic reciprocal
for **/45** (= 69 - 24) at image ``0x0c54``.  ``w3-recon/B0-CLOCK-AUDIT.md`` traced what each one
drives and decided the policy: **the phase's discrete beats keep their stock ticks; the two
phase-normalised PROGRESS ramps are retuned proportionally so they still land on their stock
terminal values, exactly, on the new last tick.**

This module is the resulting edit set, as data.  ``retime.py`` consumes ``PROGRAM_EDITS`` verbatim
and must call :func:`verify_stock` (or check ``EXPECT_OLD`` itself) before writing a single byte --
every entry is an in-place, same-length splice into one 4-byte MIPS instruction, and every one of
them is wrong if the container underneath is not the container this was derived against.

THE SEVEN SITES (all in chunk 0's id-3 image; image base = container file ``0x2D000``)
--------------------------------------------------------------------------------------
=====  =========  ==========  =============================  ==========================
 #      image      file        instruction                    change
=====  =========  ==========  =============================  ==========================
 E1a    0x1278     0x2E278     ``slti $v0, $s5, 69``          imm16  69 -> 117
 E1b    0x0B6C     0x2DB6C     ``lui  $v1, <M69.hi>``         imm16 -> M117 high half
 E1c    0x0B70     0x2DB70     ``ori  $v1, $v1, <M69.lo>``    imm16 -> M117 low half
 E1d    0x0C04     0x2DC04     ``lui  $v1, <M45.hi>``         imm16 -> M93 high half
 E1e    0x0C54     0x2DC54     ``lui  $v1, <M45.hi>``         imm16 -> M93 high half
 E1f    0x0C58     0x2DC58     ``ori  $v1, $v1, <M45.lo>``    imm16 -> M93 low half
 E1g    0x0C70     0x2DC70     ``sra  $v1, $v1, 5``           shamt  5 -> 6
=====  =========  ==========  =============================  ==========================

E1d and E1e are the SAME ``lui`` emitted twice -- once in the delay slot of the ``clock == 24``
one-shot's ``bne`` (so it is live on the not-equal path) and once on the equal path's fall-through.
Patch one and not the other and the creature's arrival ramp is correct on exactly half the ticks.
This is the single easiest way to get a half-broken retime, which is why both are here as peers.

WHY THE SHAMT MOVES ON E1g AND NOT ON E1b/E1c
---------------------------------------------
The image uses two forms of the magic-division idiom:

* **no add-back** -- ``q = (mulhi_s(x, M) >> s) - (x >> 31)``, valid while ``M < 2**31``;
* **add-back**    -- ``q = ((mulhi_s(x, M) + x) >> s) - (x >> 31)``, the compiler's encoding for a
  magic that needs 33 bits (the stored ``M`` is ``M_u - 2**32``, and the add-back recovers the
  unsigned high half).

/69 is the no-add-back form and /117 also has a no-add-back magic at the SAME shift 5
(``0x46046047``), so E1b/E1c are a pure two-immediate swap.  /45 is the add-back form; the smallest
shift whose /93 magic still needs 33 bits is **6**, so E1g moves the shift by one to keep the
add-back skeleton intact.  No instruction is added, removed or nop-ed anywhere in the set.

PROVENANCE
----------
Every ``new_bytes`` here is OUR value, computed by :func:`recompute` from arithmetic alone.  The
``EXPECT_OLD`` map holds eight 2-byte stock scalars used only as write guards -- the same posture as
``rescore.py``'s registered sha and W2's ``roll = 0 / H = 256``.  No stock byte run is embedded and
nothing here is derived from a stock dump.

The derivation is not fitted to 117: run :func:`build_edits` at **N = 0** and splice the result into
the shipping container and **zero bytes differ**.  The rule that picks the new reciprocals
reproduces the shipping ones exactly, which is why it is trusted to pick the new ones.
"""
from __future__ import annotations

import struct
from typing import Dict, List, NamedTuple, Optional, Tuple

#: chunk 0's id-3 payload base inside the container (``ef_container.parse_header``; A2 section 1).
IMAGE_BASE = 0x2D000

#: the stock threshold and the locked stretch.  N = +48 = exactly two loops of the 24-frame float
#: clip, so the creature's clip phase at the new phase end is identical to stock (A2 section 7).
STOCK_THRESHOLD = 69
N_TICKS = 48
NEW_THRESHOLD = STOCK_THRESHOLD + N_TICKS            # 117

#: the arrival ramp's origin: it is normalised over ``clock - 24 .. threshold``, so its divisor is
#: ``threshold - 24``.  24 is the ``clock >= 24`` creature gate and does NOT move.
ARRIVAL_ORIGIN = 24
STOCK_ARRIVAL_SPAN = STOCK_THRESHOLD - ARRIVAL_ORIGIN   # 45
NEW_ARRIVAL_SPAN = NEW_THRESHOLD - ARRIVAL_ORIGIN       # 93


class ProgramEdit(NamedTuple):
    """One in-place splice.  The tuple order is the contract ``retime.py`` unpacks."""
    offset: int          #: container FILE offset of the first byte written
    old_len: int         #: bytes replaced -- always equal to ``len(new_bytes)``
    new_bytes: bytes     #: OUR value, little-endian, ready to splice
    meaning: str         #: one line a human can check against the audit report


def _u16(v: int) -> bytes:
    if not 0 <= v <= 0xFFFF:
        raise ValueError("not a u16: %r" % (v,))
    return struct.pack("<H", v)


# ------------------------------------------------------------------ the magic-reciprocal search
def _s32(v: int) -> int:
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v & 0x80000000 else v


def magic_div(x: int, magic: int, shift: int, addback: bool) -> int:
    """The image's own idiom, bit-exact: ``mult`` is SIGNED and ``mfhi`` takes the high half."""
    hi = (_s32(x) * _s32(magic)) >> 32                 # python >> is arithmetic
    v = ((hi + x) & 0xFFFFFFFF) if addback else (hi & 0xFFFFFFFF)
    return (_s32(v) >> shift) - (_s32(x) >> 31)


def _exact(divisor: int, shift: int, addback: bool, xmax: int) -> Optional[int]:
    """The stored 32-bit magic for this (shift, add-back) pair, or ``None`` if the pair cannot work.

    ``addback=False`` needs ``M < 2**31`` (a positive ``mult`` operand);
    ``addback=True`` needs ``2**31 <= M < 2**32`` (a magic that only fits with the add-back's
    implicit 33rd bit).  Either way the result is checked against real division, not assumed.
    """
    m = ((1 << (32 + shift)) + divisor - 1) // divisor
    if addback and not (1 << 31) <= m < (1 << 32):
        return None
    if not addback and not 0 < m < (1 << 31):
        return None
    stored = m & 0xFFFFFFFF
    step = max(1, xmax // 40000)
    for x in list(range(0, xmax + 1, step)) + list(range(0, min(xmax, 20000) + 1)):
        if magic_div(x, stored, shift, addback) != x // divisor:
            return None
    return stored


def pick_reciprocal(divisor: int, addback: bool, xmax: int) -> Tuple[int, int]:
    """``(shift, magic)`` for a divisor, under the skeleton the image already has.

    The selection rule is the one the original compiler evidently used, and it is testable:
    applied to the STOCK divisors it reproduces the STOCK shifts (both 5).  See
    :func:`_selftest_reproduces_stock`.

    * no add-back -- take the LARGEST shift whose magic still fits in 31 bits (most precision);
    * add-back    -- take the SMALLEST shift whose magic needs the 33rd bit (so the add-back
      instruction at ``0x0C6C`` stays correct rather than becoming a spurious ``+ x``).
    """
    order = range(24, -1, -1) if not addback else range(0, 25)
    for sh in order:
        m = _exact(divisor, sh, addback, xmax)
        if m is not None:
            return sh, m
    raise ValueError("no %s magic exists for /%d under this skeleton"
                     % ("add-back" if addback else "plain", divisor))


def recompute(n: int = N_TICKS) -> Dict[str, int]:
    """Re-derive every value in :data:`PROGRAM_EDITS` from arithmetic, for an arbitrary N.

    Nothing is read from the container here -- this is the *authoring* half.  The emulator calls it
    and asserts the frozen table matches, so the table can never drift from its derivation.
    """
    thr = STOCK_THRESHOLD + n
    span = thr - ARRIVAL_ORIGIN
    if thr < 47 or span < 1:
        raise ValueError("N = %+d puts the threshold at %d; B0 section 7 sets the floor at 47 "
                         "(the largest intra-phase gate is clock < 46)" % (n, thr))
    # inputs are ``clock << 12`` and ``(clock-24) << 12``; a 2x ceiling keeps the magics exact well
    # past any tick the phase can reach
    p_sh, p_m = pick_reciprocal(thr, False, (2 * thr) << 12)
    a_sh, a_m = pick_reciprocal(span, True, (2 * span) << 12)
    return {"threshold": thr,
            "progress_divisor": thr, "progress_magic": p_m, "progress_shift": p_sh,
            "arrival_divisor": span, "arrival_magic": a_m, "arrival_shift": a_sh}


def _selftest_reproduces_stock() -> None:
    """The selection rule must reproduce the STOCK shifts from the STOCK divisors, or it is a
    rationalisation rather than a reading of the compiler's idiom."""
    sh, m = pick_reciprocal(STOCK_THRESHOLD, False, (2 * STOCK_THRESHOLD) << 12)
    assert (sh, m) == (5, 0x76B981DB), (sh, hex(m))
    sh, m = pick_reciprocal(STOCK_ARRIVAL_SPAN, True, (2 * STOCK_ARRIVAL_SPAN) << 12)
    assert (sh, m) == (5, 0xB60B60B7), (sh, hex(m))
    # and the two GATE-coupled reciprocals in the same case body, for good measure
    assert pick_reciprocal(46, True, 46 * 150 * 2) == (5, 0xB21642C9)


_selftest_reproduces_stock()

_D = recompute(N_TICKS)
#: /117, shift 5, NO add-back -- the same skeleton, the same shift, as the stock /69
PROGRESS_MAGIC = _D["progress_magic"]                  # 0x46046047
PROGRESS_SHIFT = _D["progress_shift"]                  # 5 -- unchanged, so no shift edit is emitted
#: /93, shift 6, add-back -- the stock /45 skeleton with its shift moved by one
ARRIVAL_MAGIC = _D["arrival_magic"]                    # 0xB02C0B03
ARRIVAL_SHIFT = _D["arrival_shift"]                    # 6

#: the stock shift instructions' low halfwords.  ``sra $v1,$t1,5`` @0x0B84 and ``sra $v1,$v1,5``
#: @0x0C70 differ only in ``rt``, which lives in the HIGH halfword -- so both low halves are equal.
_SRA_LOW_STOCK = 0x1943
STOCK_SHIFT = 5


def _sra_low(shift: int) -> int:
    return (_SRA_LOW_STOCK & ~(0x1F << 6)) | ((shift & 0x1F) << 6)


#: image offsets of every site the recipe can touch, whether or not this N touches it
SITE_IMAGE = {
    "E1a": 0x1278,   # slti -- the threshold
    "E1b": 0x0B6C,   # lui  -- progress magic, high half
    "E1c": 0x0B70,   # ori  -- progress magic, low half
    "E1d": 0x0C04,   # lui  -- arrival magic, high half (delay-slot copy)
    "E1e": 0x0C54,   # lui  -- arrival magic, high half (equal-path copy)
    "E1f": 0x0C58,   # ori  -- arrival magic, low half
    "E1g": 0x0C70,   # sra  -- arrival shift
    "E1h": 0x0B84,   # sra  -- progress shift (NOT emitted at N = +48; the shift stays 5)
}

#: write guards: ``{file offset: the stock u16 that MUST be there}``.  Small scalars only, and the
#: map covers EVERY candidate site so a drifted skeleton is caught even where this N does not write.
EXPECT_OLD: Dict[int, int] = {
    IMAGE_BASE + 0x1278: STOCK_THRESHOLD,   # 69
    IMAGE_BASE + 0x0B6C: 0x76B9,            # /69 magic, high half
    IMAGE_BASE + 0x0B70: 0x81DB,            # /69 magic, low half
    IMAGE_BASE + 0x0B84: _SRA_LOW_STOCK,    # sra $v1,$t1,5 -- the progress shift
    IMAGE_BASE + 0x0C04: 0xB60B,            # /45 magic, high half (delay-slot copy)
    IMAGE_BASE + 0x0C54: 0xB60B,            # /45 magic, high half (equal-path copy)
    IMAGE_BASE + 0x0C58: 0x60B7,            # /45 magic, low half
    IMAGE_BASE + 0x0C70: _SRA_LOW_STOCK,    # sra $v1,$v1,5 -- the arrival shift
}


def build_edits(n: int = N_TICKS) -> List[ProgramEdit]:
    """The E1 set for an arbitrary N.  A shift site is emitted only when its shift actually moves."""
    d = recompute(n)
    thr, span = d["threshold"], d["arrival_divisor"]
    pm, ps = d["progress_magic"], d["progress_shift"]
    am, ash = d["arrival_magic"], d["arrival_shift"]
    out = [
        ProgramEdit(IMAGE_BASE + 0x1278, 2, _u16(thr),
                    "E1a THRESHOLD: slti $v0,$s5,%d -> %d -- s0 now lasts %d ticks (clock 0..%d)"
                    % (STOCK_THRESHOLD, thr, thr + 1, thr)),
        ProgramEdit(IMAGE_BASE + 0x0B6C, 2, _u16(pm >> 16),
                    "E1b PROGRESS RAMP hi: lui $v1 -> /%d magic 0x%08X (shift %d, no add-back). "
                    "Drives the effect model's scale/tilt/RGB, the camera-shake decay envelope and "
                    "the light column's rcos angle; lands on 4096 exactly at clock %d."
                    % (thr, pm, ps, thr)),
        ProgramEdit(IMAGE_BASE + 0x0B70, 2, _u16(pm & 0xFFFF),
                    "E1c PROGRESS RAMP lo: ori $v1,$v1 -> /%d magic low half" % thr),
    ]
    if ps != STOCK_SHIFT:
        out.append(ProgramEdit(IMAGE_BASE + 0x0B84, 2, _u16(_sra_low(ps)),
                               "E1h PROGRESS RAMP shift: sra $v1,$t1,%d -> %d (shamt only)"
                               % (STOCK_SHIFT, ps)))
    out += [
        ProgramEdit(IMAGE_BASE + 0x0C04, 2, _u16(am >> 16),
                    "E1d ARRIVAL RAMP hi (DELAY-SLOT copy, live on the clock != 24 path): lui $v1 "
                    "-> /%d magic 0x%08X (shift %d, add-back).  THIS is the load-bearing copy."
                    % (span, am, ash)),
        ProgramEdit(IMAGE_BASE + 0x0C54, 2, _u16(am >> 16),
                    "E1e ARRIVAL RAMP hi (EQUAL-PATH copy, live only on the clock == 24 tick): "
                    "same value as E1d.  Inert at this N because arrival(24) = 0 for any magic, "
                    "patched so the two copies never disagree."),
        ProgramEdit(IMAGE_BASE + 0x0C58, 2, _u16(am & 0xFFFF),
                    "E1f ARRIVAL RAMP lo: ori $v1,$v1 -> /%d magic low half. Drives the creature's "
                    "fly-in radius (1224->24), its scale (6144->2048) and its spiral angle; lands "
                    "on 4096 exactly at clock %d." % (span, thr)),
    ]
    if ash != STOCK_SHIFT:
        out.append(ProgramEdit(IMAGE_BASE + 0x0C70, 2, _u16(_sra_low(ash)),
                               "E1g ARRIVAL RAMP shift: sra $v1,$v1,%d -> sra $v1,$v1,%d (shamt "
                               "only; rt/rd/funct unchanged).  /%d needs 33 bits at shift %d, "
                               "which is what keeps the add-back at 0x0C6C correct."
                               % (STOCK_SHIFT, ash, span, ash)))
    return out


#: THE LOCKED SET -- N = +48.  Seven sites, 14 bytes written, 12 bytes actually different.
PROGRAM_EDITS: List[ProgramEdit] = build_edits(N_TICKS)

#: the gate/one-shot immediates this edit set deliberately LEAVES ALONE.  ``{file offset: value}``.
#: B0 section 4 justifies each one; a retimer that touches any of them has left the locked policy.
UNTOUCHED_GATES: Dict[int, Tuple[int, str]] = {
    IMAGE_BASE + 0x0B8C: (12, "slti clock<12 -- the intro fade block, self-contained /12 ramp"),
    IMAGE_BASE + 0x0BF0: (24, "slti clock<24 -- the creature-half split"),
    IMAGE_BASE + 0x0BFC: (24, "addiu 24 -- the clock==24 one-shot that starts the float clip"),
    IMAGE_BASE + 0x0E48: (44, "addiu 44 -- the clock==44 one-shot that latches the trail arm"),
    IMAGE_BASE + 0x0E50: (45, "slti clock<45 -- the bone-trail on-switch (saturates at 4096)"),
    IMAGE_BASE + 0x0FA4: (35, "slti clock<35 -- the particle spawner's odd-tick arm"),
    IMAGE_BASE + 0x0FB0: (35, "slti clock<35 -- the particle spawner's even-tick arm"),
    IMAGE_BASE + 0x1188: (46, "slti clock<46 -- the light-column sub-phase, self-contained /46 ramp"),
}


# ------------------------------------------------------------------ the call-site guards
class ProgramEditError(RuntimeError):
    pass


def verify_stock(blob: bytes) -> None:
    """Refuse to patch anything unless every stock u16 is exactly where it is supposed to be.

    A law in a docstring is a wish: ``retime.py`` must call this (or reimplement it) BEFORE the
    first write.  Every failure message names the site, so a drifted container is diagnosable
    without a disassembler.
    """
    if len(blob) < IMAGE_BASE + 0x2000:
        raise ProgramEditError("blob is too short to be an ef227 container (%d B)" % len(blob))
    by_off = {IMAGE_BASE + img: tag for tag, img in SITE_IMAGE.items()}
    for off, want in sorted(EXPECT_OLD.items()):
        got = struct.unpack_from("<H", blob, off)[0]
        if got != want:
            raise ProgramEditError(
                "%s: container file 0x%X (image 0x%04X) holds 0x%04X, expected the stock 0x%04X. "
                "The donor is not the container this edit set was derived against -- re-run the B0 "
                "audit before trusting any of these offsets."
                % (by_off.get(off, "?"), off, off - IMAGE_BASE, got, want))
    for off, (val, why) in sorted(UNTOUCHED_GATES.items()):
        got = struct.unpack_from("<H", blob, off)[0]
        if got != val:
            raise ProgramEditError(
                "untouched gate at file 0x%X holds %d, expected %d (%s)" % (off, got, val, why))


def apply_edits(blob: bytes, edits: List[ProgramEdit] = None) -> bytes:
    """Splice E1 into a COPY.  Same length in, same length out, or it raises."""
    edits = PROGRAM_EDITS if edits is None else edits
    verify_stock(blob)
    out = bytearray(blob)
    seen = set()
    for off, old_len, new_bytes, why in edits:
        if len(new_bytes) != old_len:
            raise ProgramEditError("edit at 0x%X is not same-length: %d != %d"
                                   % (off, len(new_bytes), old_len))
        word = (off - IMAGE_BASE) & ~3
        if ((off - IMAGE_BASE) - word) + old_len > 4:
            raise ProgramEditError("edit at 0x%X straddles an instruction boundary" % off)
        for i in range(old_len):
            if off + i in seen:
                raise ProgramEditError("two edits write byte 0x%X" % (off + i))
            seen.add(off + i)
        out[off:off + old_len] = new_bytes
    if len(out) != len(blob):
        raise ProgramEditError("length changed: %d -> %d" % (len(blob), len(out)))
    return bytes(out)


def changed_byte_count(blob: bytes) -> int:
    patched = apply_edits(blob)
    return sum(1 for a, b in zip(blob, patched) if a != b)


def _main() -> int:
    d = recompute(N_TICKS)
    print("TIER W3 / E1 -- ef227:c0 state 0, N = +%d ticks (%d -> %d)"
          % (N_TICKS, STOCK_THRESHOLD, NEW_THRESHOLD))
    print("  progress ramp  /%d -> /%d   magic 0x%08X  shift %d  add-back no"
          % (STOCK_THRESHOLD, d["progress_divisor"], d["progress_magic"], d["progress_shift"]))
    print("  arrival  ramp  /%d -> /%d   magic 0x%08X  shift %d  add-back YES"
          % (STOCK_ARRIVAL_SPAN, d["arrival_divisor"], d["arrival_magic"], d["arrival_shift"]))
    assert d["progress_magic"] == PROGRESS_MAGIC and d["arrival_magic"] == ARRIVAL_MAGIC
    print()
    total = 0
    for off, old_len, nb, why in PROGRAM_EDITS:
        total += old_len
        print("  file 0x%06X (image 0x%04X)  %d B  old=0x%04X  new=0x%s"
              % (off, off - IMAGE_BASE, old_len, EXPECT_OLD[off], nb[::-1].hex().upper()))
        print("        %s" % why)
    print("\n  %d sites, %d bytes written." % (len(PROGRAM_EDITS), total))
    return 0


if __name__ == "__main__":               # pragma: no cover
    raise SystemExit(_main())
