"""Read/edit an FF9 (Memoria/Steam) save file's story state -- the RECREATE verb.

The on-disc save lives under **AppData\\LocalLow** (NOT Roaming/Local):
``%USERPROFILE%\\AppData\\LocalLow\\SquareEnix\\FINAL FANTASY IX\\Steam\\EncryptedSavedData\\SavedData_ww.dat``
(:func:`default_save_dir` returns it). It is a container of fixed-size **save blocks**, each independently
AES-256-CBC encrypted. Layout (all from the engine, ``SharedDataBytesStorage.MetaData``):

    [0, 320)          metadata header
    [320, 320+150*1024)   150 preview blocks (1024 B each)
    BASE=153920 onward    1 autosave + 150 slot/save data blocks, 18432 B each

A data block decrypts (raw CBC, 18432 is a multiple of 16 -> no padding) to ``"SAVE"`` + a flat,
schema-ordered value stream. ``gEventGlobal`` (the 2048-byte story heap) is stored as a String4K field:
its 2048 bytes Base64'd to a 2732-char string. We locate that string, decode -> edit -> re-encode (always
2732 chars, so byte-length-stable) -> re-encrypt the block. Because AES-CBC is a bijection,
``encrypt(decrypt(block)) == block`` exactly, so an unedited block round-trips byte-identical and an edit
moves ONLY the bytes it must -- no checksum, no offset shift. (Crypto: ``AESCryptography.cs`` -- AES-256-CBC,
PBKDF2-HMAC-SHA1 1000 iters, salt ``[3,3,1,4,7,0,9,7]``; the password is the literal string
``"System.Security.SecureString"`` -- the decompiled ``SecureString.ToString()`` returns the type name,
and that *is* the key. Verified against a real save.)

Requires ``pycryptodome`` (``py -m pip install pycryptodome``) -- imported lazily so the rest of the kit
doesn't depend on it.
"""
from __future__ import annotations

import base64
import hashlib
import os
import re
import struct
from dataclasses import dataclass

from . import flags as _flags
from . import fsutil as _fsutil

# --- container layout (SharedDataBytesStorage.MetaData) ---
BASE_SAVE_BLOCK_OFFSET = 153920     # MetaDataReservedSize(320) + TotalSaveCount(150)*PreviewReservedSize(1024)
SAVE_BLOCK_SIZE = 18432
SLOT_COUNT = 10
SAVE_COUNT = 15                     # saves per slot
GEG_B64_LEN = 2732                  # base64 length of 2048 bytes (always)

# --- crypto (AESCryptography.cs) ---
_SALT = bytes([3, 3, 1, 4, 7, 0, 9, 7])
_PASSWORD = b"System.Security.SecureString"   # the SecureString.ToString() quirk IS the key (verified)
_ITERS = 1000


def _key_iv():
    dk = hashlib.pbkdf2_hmac("sha1", _PASSWORD, _SALT, _ITERS, 48)
    return dk[:32], dk[32:48]


def _aes():
    try:
        from Crypto.Cipher import AES
    except ImportError as e:    # pragma: no cover - environment-dependent
        raise RuntimeError(
            "save editing needs pycryptodome -- install it with:  py -m pip install pycryptodome") from e
    return AES


def block_index(slot: int, save: int) -> int:
    """The data-block index for (slot, save). Block 0 is the autosave; manual saves are
    ``1 + slot*SAVE_COUNT + save`` (slot 0..9, save 0..14), matching the in-game load menu."""
    return 1 + slot * SAVE_COUNT + save


def extra_file_path(main_path, block: int):
    """The Memoria per-slot EXTRA-save path for a data block, or None if ``main_path`` isn't a ``.dat``.
    Memoria stores the AUTHORITATIVE gEventGlobal (+ gAbilityUsage/gScriptVector/...) in this plaintext
    file and RESTORES it on load, overriding the vanilla main block -- so a story-state edit must patch it
    too. Layout: ``SavedData_ww_Memoria_Autosave.dat`` (block 0) / ``..._Memoria_{slot}_{save}.dat``
    (``MetaData.GetMemoriaExtraSaveFilePath``)."""
    p = str(main_path)
    if not p.endswith(".dat"):
        return None
    stem = p[:-4]
    if block == 0:
        return stem + "_Memoria_Autosave.dat"
    slot, save = (block - 1) // SAVE_COUNT, (block - 1) % SAVE_COUNT
    return f"{stem}_Memoria_{slot}_{save}.dat"


def _find_b64_geg(buf: bytes):
    """(start, end) of the gEventGlobal Base64 (the run that decodes to 2048 bytes) in a plaintext
    buffer, or None. Shared by the encrypted main block and the plaintext extra file."""
    for m in re.finditer(rb"[A-Za-z0-9+/]{2700,}={0,2}", buf):
        try:
            if len(base64.b64decode(m.group())) == 2048:
                return (m.start(), m.start() + len(m.group()))
        except Exception:       # noqa: BLE001
            continue
    return None


def read_extra_gEventGlobal(path):
    """The 2048-byte gEventGlobal from a Memoria extra-save file (plaintext), or None if absent."""
    try:
        buf = open(path, "rb").read()
    except OSError:
        return None
    span = _find_b64_geg(buf)
    return base64.b64decode(buf[span[0]:span[1]]) if span else None


def patch_extra_gEventGlobal(path, blob: bytes) -> bool:
    """Replace the gEventGlobal Base64 in a Memoria extra-save file with ``blob`` (2048 bytes), in place
    (length-stable). Returns True if patched, False if the file has no gEventGlobal field."""
    if len(blob) != 2048:
        raise ValueError(f"gEventGlobal must be 2048 bytes (got {len(blob)})")
    buf = bytearray(open(path, "rb").read())
    span = _find_b64_geg(bytes(buf))
    if span is None:
        return False
    buf[span[0]:span[1]] = base64.b64encode(blob)
    with open(path, "wb") as fh:
        fh.write(bytes(buf))
    return True


@dataclass
class SaveSlot:
    block: int
    slot: int           # -1 for the autosave
    save: int           # -1 for the autosave
    scenario: int
    beat: str
    mognet_locks: int      # set bits in the Mognet lock band (bytes 1047-1063; long mislabelled chests)


class FF9Save:
    """An FF9 ``SavedData_ww.dat``, decrypted block-by-block on demand. Edits stay in memory until
    :meth:`write`. Never mutates the source file (load reads; write takes an explicit path)."""

    def __init__(self, data: bytes):
        self.data = bytearray(data)
        self.key, self.iv = _key_iv()

    @classmethod
    def load(cls, path) -> "FF9Save":
        with open(path, "rb") as fh:
            return cls(fh.read())

    # --- block crypto ---
    def _block_span(self, n: int):
        off = BASE_SAVE_BLOCK_OFFSET + SAVE_BLOCK_SIZE * n
        if off + SAVE_BLOCK_SIZE > len(self.data):
            raise IndexError(f"block {n} is past the end of the save file")
        return off, off + SAVE_BLOCK_SIZE

    def _decrypt_block(self, n: int) -> bytes:
        AES = _aes()
        lo, hi = self._block_span(n)
        return AES.new(self.key, AES.MODE_CBC, self.iv).decrypt(bytes(self.data[lo:hi]))

    def _encrypt_block(self, n: int, plaintext: bytes):
        AES = _aes()
        lo, hi = self._block_span(n)
        ct = AES.new(self.key, AES.MODE_CBC, self.iv).encrypt(bytes(plaintext))
        self.data[lo:hi] = ct

    @staticmethod
    def is_save_block(plaintext: bytes) -> bool:
        return plaintext[:4] == b"SAVE"

    # --- gEventGlobal find / get / set ---
    _find_geg_span = staticmethod(_find_b64_geg)   # the gEventGlobal Base64 span in a decrypted block

    def gEventGlobal(self, n: int) -> bytes:
        """The 2048-byte gEventGlobal of data block ``n`` (raises if the block isn't a valid save)."""
        pt = self._decrypt_block(n)
        if not self.is_save_block(pt):
            raise ValueError(f"block {n} is not a populated save (no 'SAVE' magic)")
        span = self._find_geg_span(pt)
        if span is None:
            raise ValueError(f"block {n}: could not locate the gEventGlobal field")
        return base64.b64decode(pt[span[0]:span[1]])

    def set_gEventGlobal(self, n: int, blob: bytes):
        """Replace block ``n``'s gEventGlobal with ``blob`` (exactly 2048 bytes) and re-encrypt the block
        in place. Only the Base64 chars that actually change move; everything else stays byte-identical."""
        if len(blob) != 2048:
            raise ValueError(f"gEventGlobal must be 2048 bytes (got {len(blob)})")
        pt = bytearray(self._decrypt_block(n))
        span = self._find_geg_span(pt)
        if span is None:
            raise ValueError(f"block {n}: could not locate the gEventGlobal field")
        nb64 = base64.b64encode(blob)
        assert len(nb64) == GEG_B64_LEN, len(nb64)     # 2048 bytes -> always 2732 base64 chars
        pt[span[0]:span[1]] = nb64
        self._encrypt_block(n, bytes(pt))

    # --- enumeration ---
    def populated(self) -> "list[SaveSlot]":
        """Every populated save block (autosave + manual), decoded enough to identify it."""
        out = []
        n = 0
        # 1 autosave + SLOT_COUNT*SAVE_COUNT manual blocks
        while True:
            try:
                lo, hi = self._block_span(n)
            except IndexError:
                break
            pt = self._decrypt_block(n)
            if self.is_save_block(pt):
                span = self._find_geg_span(pt)
                if span is not None:
                    geg = base64.b64decode(pt[span[0]:span[1]])
                    sc = geg[0] | geg[1] << 8
                    ms = _flags.nearest_milestone(sc)
                    locks = sum(bin(geg[b]).count("1") for b in range(_flags.MOGNET_LOCK_LO >> 3, (_flags.MOGNET_LOCK_HI >> 3) + 1))
                    slot, save = (-1, -1) if n == 0 else ((n - 1) // SAVE_COUNT, (n - 1) % SAVE_COUNT)
                    out.append(SaveSlot(n, slot, save, sc, ms[1] if ms else "(pre-story)", locks))
            n += 1
        return out

    def write(self, path):
        """Write the whole container back to ``path`` ATOMICALLY (a sibling ``.tmp`` + ``os.replace``) --
        the live save must never be observed half-written."""
        _fsutil.atomic_write_bytes(path, bytes(self.data))


# --- the high-level read (VIEW; used by the GUI inspector + a future CLI flag) ---
def default_save_dir():
    """The FF9 Steam save folder if it exists, else None. Steam FF9 saves live under **AppData/LocalLow**
    (``%USERPROFILE%/AppData/LocalLow/SquareEnix/FINAL FANTASY IX/Steam/EncryptedSavedData``) -- a frontend
    uses this as a file-dialog's start directory so the user doesn't have to hunt for SavedData_ww.dat."""
    base = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    cand = os.path.join(base, "AppData", "LocalLow", "SquareEnix", "FINAL FANTASY IX", "Steam",
                        "EncryptedSavedData")
    return cand if os.path.isdir(cand) else None


def _slot_label(s: "SaveSlot") -> str:
    return "autosave" if s.slot < 0 else f"slot {s.slot + 1} · save {s.save + 1}"


def inspect(path) -> "list[tuple[str, _flags.SaveReport]]":
    """Decode a save's story state for VIEWING -- returns ``[(label, SaveReport)]``. Accepts, in order: a
    Memoria plaintext extra-save (a ``.dat`` with a loose gEventGlobal -- no crypto); an encrypted
    ``SavedData_ww.dat`` container (one entry per populated block -- needs pycryptodome); or an open save
    JSON / bare Base64 gEventGlobal (one entry). Raises with a clear message if nothing decodes."""
    p = str(path)
    if p.lower().endswith(".dat"):
        blob = read_extra_gEventGlobal(p)               # a Memoria plaintext extra-save? (no crypto needed)
        if blob is not None:
            return [("Memoria extra-save", _flags.decode_gEventGlobal(blob))]
        sv = FF9Save.load(p)                             # the encrypted container (needs pycryptodome)
        out = []
        for s in sv.populated():
            # Memoria writes a per-slot extra file holding the AUTHORITATIVE gEventGlobal and RESTORES from
            # it on LOAD -- so when it exists, THAT is the state the game uses (the main block is stale).
            # Read it (and tag the slot) so inspect shows what the game actually loads, not the main block.
            extra = extra_file_path(p, s.block)
            eblob = read_extra_gEventGlobal(extra) if (extra and os.path.exists(extra)) else None
            blob = eblob if eblob is not None else sv.gEventGlobal(s.block)
            out.append((_slot_label(s) + (" · Memoria extra" if eblob is not None else ""),
                        _flags.decode_gEventGlobal(blob)))
        if not out:
            raise ValueError("no populated save slots found in this file")
        return out
    blob = _flags.gEventGlobal_from_save(p)             # an open save JSON / bare Base64 gEventGlobal
    return [("gEventGlobal", _flags.decode_gEventGlobal(blob))]


# --- the high-level edit (used by the CLI) ---
def edit_story_state(geg: bytearray, *, scenario: int | None = None,
                     set_flags=(), clear_flags=()) -> "list[str]":
    """Apply story-state edits to a 2048-byte gEventGlobal IN PLACE; returns a list of human change notes.
    ``scenario`` sets ScenarioCounter (bytes 0-1). ``set_flags`` / ``clear_flags`` are GLOB bit indices.
    Refuses to touch a reserved region (chest band / worldmap / handshake / scratch) or a named word's
    byte range (ScenarioCounter, TranceGaugeFlag, ...) -- those corrupt real state. Flag indices outside
    [0, 16383] are rejected."""
    notes = []
    if scenario is not None:
        if not 0 <= scenario <= 0xFFFF:
            raise ValueError(f"scenario {scenario} out of range (0-65535)")
        old = geg[0] | geg[1] << 8
        geg[0], geg[1] = scenario & 0xFF, scenario >> 8 & 0xFF
        ms = _flags.nearest_milestone(scenario)
        notes.append(f"ScenarioCounter {old} -> {scenario}" + (f" ({ms[1]})" if ms else ""))
    for bit, on in [(b, True) for b in set_flags] + [(b, False) for b in clear_flags]:
        if not 0 <= bit < 2048 * 8:
            raise ValueError(f"flag {bit} out of range (0-16383)")
        if _flags.is_reserved(bit):
            r = _flags.bit_region(bit)
            raise ValueError(f"flag {bit} is in the reserved region '{r.name}' -- refusing to edit it "
                             f"(would corrupt real FF9 state). {r.meaning}")
        w = _flags.named_word_at(bit)
        if w is not None:
            raise ValueError(f"flag {bit} is inside the named word '{w.name}' (byte {w.byte}) -- refusing "
                             f"to edit it (would corrupt real FF9 state). {w.meaning}")
        byte, mask = bit >> 3, 1 << (bit & 7)
        if on:
            geg[byte] |= mask
        else:
            geg[byte] &= ~mask
        notes.append(f"flag {bit} {'set' if on else 'cleared'}")
    return notes


# --- overworld position array (lives IN gEventGlobal; in-game proven 2026-07-05) ---
# The world .eb stores each overworld actor's world X/Z as 24-bit little-endian fixed-point (world = raw/256)
# in a per-actor ARRAY: record 0 = the player @ X64/Z69, record 1 = the chocobo (Choco) @ X83/Z88, on a
# fixed +19-byte stride. Y is NOT stored (the engine ground-snaps on load). Editing a record's bytes
# relocates that actor on load (player write-tested in-game: (258,-884) -> (272,-1142) landed exactly;
# Choco is a single persistent companion that stays parked where you dismount). Records 2+ (boat/airships)
# are the same stride but their indices are not yet confirmed. See memory project-ff9-overworld-vehicles.
WORLD_POS_X_OFF = 64           # record 0 (player) X; Z = X + 5
WORLD_POS_Z_OFF = 69
WORLD_POS_W = 3                 # bytes per coord (24-bit)
WORLD_POS_FP = 256             # fixed-point scale (world units = raw / 256)
WORLD_POS_STRIDE = 19          # per-actor record spacing
WORLD_ACTORS = ("player", "chocobo")   # record 0, 1 (proven); boat/airships = later records (TBD)
_WORLD_POS_MIN = -(1 << 23) / WORLD_POS_FP
_WORLD_POS_MAX = ((1 << 23) - 1) / WORLD_POS_FP


def world_actor_index(actor) -> int:
    """A record index for a named actor (or a raw int index passed through). Raises on an unknown name."""
    if isinstance(actor, int):
        return actor
    try:
        return WORLD_ACTORS.index(actor)
    except ValueError:
        raise ValueError(f"unknown world actor {actor!r}; known: {', '.join(WORLD_ACTORS)}") from None


def _world_offsets(actor) -> "tuple[int, int]":
    """(x_off, z_off) into gEventGlobal for a named actor's position record (record 0 + index*stride)."""
    base = WORLD_POS_STRIDE * world_actor_index(actor)
    return WORLD_POS_X_OFF + base, WORLD_POS_Z_OFF + base


def decode_world_position(geg, actor="player") -> "tuple[float, float]":
    """An overworld actor's ``(X, Z)`` world coords from a 2048-byte gEventGlobal (default the player;
    ``"chocobo"`` = Choco's parked position). Y is not stored (the engine ground-snaps on load). ONLY
    meaningful for a save taken on the OVERWORLD -- in a field this bit region holds field flags, so decoding
    it there is nonsense."""
    xo, zo = _world_offsets(actor)
    x = int.from_bytes(geg[xo:xo + WORLD_POS_W], "little", signed=True) / WORLD_POS_FP
    z = int.from_bytes(geg[zo:zo + WORLD_POS_W], "little", signed=True) / WORLD_POS_FP
    return x, z


def _fp24(v: float) -> bytes:
    raw = int(round(v * WORLD_POS_FP))
    if not -(1 << 23) <= raw <= (1 << 23) - 1:
        raise ValueError(f"world coord {v} out of range ({_WORLD_POS_MIN:.0f}..{_WORLD_POS_MAX:.0f})")
    return raw.to_bytes(WORLD_POS_W, "little", signed=True)


def edit_world_position(geg: bytearray, x: float | None = None, z: float | None = None,
                        actor="player") -> "list[str]":
    """Set an overworld actor's X and/or Z in a 2048-byte gEventGlobal IN PLACE (24-bit fixed-point); returns
    change notes. ``actor`` = ``"player"`` (default) or ``"chocobo"`` (Choco's parked spot). Leaves Y
    (unstored) and all other bytes untouched. ⚠ ONLY valid for an OVERWORLD save, and only relocate to a
    WALKABLE spot -- an invalid spawn can black-screen brick the world (the "no controlled actor" freeze).
    Keep the same world-scene state (gEventGlobal[0-1]) unless you also mean to change disc/continent context."""
    xo, zo = _world_offsets(actor)
    tag = "" if actor == "player" else f"{actor} "     # keep the player note text stable (API contract)
    notes = []
    ox, oz = decode_world_position(geg, actor)
    if x is not None:
        geg[xo:xo + WORLD_POS_W] = _fp24(x)
        notes.append(f"{tag}world X {ox:.2f} -> {float(x):.2f}")
    if z is not None:
        geg[zo:zo + WORLD_POS_W] = _fp24(z)
        notes.append(f"{tag}world Z {oz:.2f} -> {float(z):.2f}")
    return notes


def _unique_backup_path(base: str) -> str:
    """``base`` if nothing is there yet, else the first ``base.N`` (N=1, 2, ...) that isn't -- a
    timestamp is only 1-second resolution, so two edits inside the same second must never share a
    backup path (that would silently overwrite an already-pristine backup with a post-edit copy)."""
    if not os.path.exists(base):
        return base
    n = 1
    while os.path.exists(f"{base}.{n}"):
        n += 1
    return f"{base}.{n}"


def apply_story_edit(path, *, block: int, scenario: int | None = None, set_flags=(), clear_flags=(),
                     world_x: float | None = None, world_z: float | None = None, world_actor="player",
                     do_backup: bool = True, dry_run: bool = False) -> dict:
    """Edit a real ``SavedData_ww.dat``'s story state IN PLACE and write it back -- the convenience the GUI's
    "Apply" uses (the CLI's ``save-edit --in-place`` path as one call). Reads ``block``'s gEventGlobal from
    the Memoria per-slot extra file when present (it overrides the main block on load), applies
    :func:`edit_story_state`, backs up the ``.dat`` (+ the extra) when ``do_backup``, writes the ``.dat``,
    and patches the extra. ``dry_run`` validates + lists the changes but writes NOTHING (the GUI's "Preview").
    Returns ``{"notes", "extra", "backups", "written"}``. Raises ValueError on a bad edit (e.g. a
    reserved-region flag) BEFORE writing -- nothing is touched until the edit validates. The edit shares the
    same core (:func:`edit_story_state`) as the CLI, so the reserved-region guard holds."""
    import time
    sv = FF9Save.load(path)
    extra = extra_file_path(path, block)
    extra_exists = bool(extra and os.path.exists(extra))
    src = read_extra_gEventGlobal(extra) if extra_exists else None
    if src is None:
        src = sv.gEventGlobal(block)
    geg = bytearray(src)
    notes = edit_story_state(geg, scenario=scenario, set_flags=set_flags, clear_flags=clear_flags)
    notes += edit_world_position(geg, world_x, world_z, actor=world_actor)
    if not notes or dry_run:
        return {"notes": notes, "extra": extra_exists, "extra_patched": None, "backups": [], "written": False}
    sv.set_gEventGlobal(block, bytes(geg))

    def _bk(p):
        b = _unique_backup_path(f"{p}.bak.{time.strftime('%Y%m%d-%H%M%S')}")
        with open(p, "rb") as s, open(b, "wb") as d:
            d.write(s.read())
        return b

    backups = [_bk(path)] if do_backup else []
    sv.write(path)
    extra_patched = None
    if extra_exists:
        if do_backup:
            backups.append(_bk(extra))
        ok = patch_extra_gEventGlobal(extra, bytes(geg))
        chk = read_extra_gEventGlobal(extra)             # re-read to CONFIRM: the extra is what the game LOADS,
        extra_patched = bool(ok) and chk is not None and bytes(chk) == bytes(geg)   # so this must take or the
    #                                                      edit won't show in-game even though the .dat changed
    return {"notes": notes, "extra": extra_exists, "extra_patched": extra_patched,
            "backups": backups, "written": True}
