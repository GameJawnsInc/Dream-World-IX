"""The co-op GUEST TRAVERSAL table (engine patch s156): which stock press interactions a following guest may run
on its own copy of the room -- ladders, jumps, carries -- and the CRC-32 of every function each one runs.

THE GENERATOR. It reads YOUR install's field event scripts READ-ONLY (UnityPy over ``StreamingAssets/p0data*.bin``;
it may read an existing ``.ff9mapkit-events-bundle.txt`` and never writes into the install), classifies every QUAD
press closure with :mod:`ff9mapkit.eb.pressclosure`, keeps the census's LOCO-ONLY player movers, applies the
fail-closed ship filter R1-R15 below (R15 also reads each candidate field's stock walkmesh, read-only, through the
install's ALREADY-built field index -- a field it cannot read is a :class:`TableError`, never a silent row; R16 is
specified and measured but NOT enforced, :data:`R16_ENFORCED`), and emits

* ``data/guest_traversal.json`` -- the committed twin (package data; :func:`load`), the ONLY owner of the table's
  row / function / field counts and its CRC: nothing else hard-codes them;
* ``Memoria/Netsync/NetSyncGuestLocalTable.cs`` -- the generated engine table, DATA ONLY (the row / function
  structs are hand-written in ``NetSyncGuestLocal.cs``). :func:`render_cs` is a pure function of the JSON: no kit
  version, date, path or machine string, so an unchanged install regenerates a zero diff.

    py -m ff9mapkit.guest_traversal [--check | --write] [--cs PATH] [--report PATH] [--game PATH]

``--check`` (the default) re-derives in memory and diffs against the committed JSON (and against ``--cs`` /
``--report`` files when given); ``--write`` rewrites them. Provenance: field ids, entry/tag indices, byte lengths,
CRC-32 digests of functions of 8 bytes or more, the .eb files' SHA-1 and Memoria's open-source EVT names -- no game
bytes (``docs/PROVENANCE.md``).

THE SHIP FILTER (a candidate is a QUAD root whose census tier is LOCO-ONLY and whose kind moves the player):

  R1  closure: truncated, a decode failure, or an unresolved / computed uid or tag
  R2  edge: a call other than ctrl (uid 250) / fixed_ctrl (a fixed uid naming DefinePlayerCharacter entries) /
      seq (RunSharedScript) -- self, party, sender (RunScriptObject*), spawn (Init*), fixed_other
  R3  roles: one closure function reached in two roles (or the region function reached by a call)
  R4  table: a closure function's entry table not strictly increasing, an fpos past its entry, or its tag listed twice
  R5  card: the region entry has a tag-8 handler (a Special press would reach unverified code)
  R6  seq: a RunSharedScript target that is not exactly one function with tag 0
  R7  body: no ctrl / fixed_ctrl body, ctrl and fixed_ctrl bodies mixed, or two fixed uids
  R8  short: a function shorter than 8 bytes (keeps every digest one-way by construction)
  R9  language: a language's .eb missing, or its tier / closure / roles / player set / (len, crc) differing
  R10 (a hard generator error, never a refusal) :func:`func_slice` disagrees with the kit's EbScript model
  R11 latch: an outside function -- ANY function outside the closure, not only the census's read sites -- READS a
      MAP / instance var the closure writes on some path before a plain write covers it (the path-aware audit,
      :func:`ff9mapkit.eb.pressclosure.latch_access`: ``+=`` / ``++`` and ``x = x + 1`` read, a write covers only
      its own bits), unless it is a load-once reader (:func:`ff9mapkit.eb.pressclosure.load_once_why`; a tag-1
      reader is not one when any ReturnEntryFunctions can restart its entry)
  R12 op: a closure function holds ReturnEntryFunctions (0x97: it restarts an entry's tag 1, code outside the
      CRC), or a TerminateEntry (0x1C) that is not the constant self-end 255 (it disposes another object) -- the
      census's Seq-run TerminateEntry exemption stays verbatim for the tier; this is what ships
  R13 write: the closure writes a Global (gEventGlobal) or Null (Memoria custom / save-data) var -- it may write
      only Map and Instance vars, which R11 audits
  R14 key: a closure function polls a key mask that is not directions-only -- a host-owned bit (pressclosure's
      ``key_press``: Select, Triangle, Circle, Cross, Square, Cancel, Confirm, MenuControl, Special, Menu), a computed
      mask, or a constant with no direction bit (``key_other``). A live guest's NetSyncField.FilterScriptButtons masks
      exactly the host-owned bits during a control-off climb whenever ScriptKeyLockActive is on (the host merely busy
      anywhere is enough), so such a loop waits forever, with no watchdog; the census buckets all three NEUTRAL
  R15 walk-in: the climb newly opens walkmesh ground that carries an EXPOSED walk-in. ARRIVAL = the player-walkable
      components (walkmesh_pass.player_components, with the tris Main_Init's constant EnablePath /
      EnablePathTriangle(..., 0) disable on any branch taken off first) where a player entry's tag 0 leaves the player
      with walk control -- the last placement on each path that ends with pathing on and no ladder attribute
      (:func:`spawn_points`, placed by the engine's GetTriIdxAtPos pick; CreateObject's default height is the
      topmost tri). ARRIVAL is a UNION over entrance branches: on one visit the player spawns on ONE of them, so a
      per-visit exposure (a climb from one entrance's ground onto another entrance's) remains BY DESIGN. LANDING =
      the components the closure's landing points match (walkmesh_pass's nearest-height walkable tri within 250 u);
      a FINAL landing (one some path ends the function at -- a ladder's mid-air mounts are not final) at a computed
      point or on no walkable tri cannot be named, so it lands on EVERY walkable component (fail closed). NEW =
      LANDING - ARRIVAL. A walk-in -- a tread region (a region entry's tag 2: its area, EventEngine.IsInQuad's every
      three consecutive points, or everything for a computed SetRegion or a QuadCircleData hot-fix region) or a bump
      object (an object entry's tag 2, the CheckNPCPush path: the walkable tris within its bump reach of every point
      its tag-0 placement walk leaves it at; a WALKER -- moved elsewhere only by its own pathing-on walks and constant
      CreateObjects, nothing turning its pathing off, no Ex / attach op naming it (uid 255 in a Seq it runs names it)
      -- the tris its placements reach through tris that are active or that code can turn on (:func:`activatable`)
      and every walkable tri within its reach and +-400 height window of them; everything when that is unknown or it
      moves elsewhere) -- is EXPOSED when its tag-2 closure cannot be judged whole (a closure gap -- a tag 1 an Init* or
      ReturnEntryFunctions starts among them -- or an open scan: whatever its tier), or tiers STATEFUL and is not the
      hidden-item template
      (pressclosure.WatchScan.exempt_why: a closed scan that visited every closure function and saw a site for each
      STATEFUL bucket of the closure, every effect / STATEFUL site dominated by a user-control test AND a constant
      Confirm / Special / Select poll -- which F1 strips at control-on -- proved together, no yield or control write
      between them). An exposed walk-in touching a NEW component refuses: nothing gates a tread or a bump for a
      spectator (EventCollision.CollisionRequest runs the stock Request(obj, 1, 2) on the guest's own copy).
      THE JP WAIVER (:data:`WAIVER_WHY`): a row whose only refusal is R15 in Japanese, and that passes R15 there once
      the KEY fact also accepts Cancel (where ETb.ProcessJapaneseLayout puts a Japanese guest's Confirm), ships and is
      listed in the JSON's ``waivers`` -- a pre-existing hole of the co-op key mask on any ground, until the engine's
      ControlOnScriptKeys strips the JP-mapped bits
  R16 watcher (SPECIFIED, MEASURED, NOT ENFORCED -- :data:`R16_ENFORCED`): a function the engine starts on its own
      (pressclosure.watch_roots: every tag 0 / tag 1, Main_Reinit), outside the row's closure, with an effect op whose
      firing depends (control dependence, or a Map / Instance var a guest can taint) on (a) a host-owned or computed
      key poll and that no user-control test dominates, or (b) the controlled player's whereabouts and that no constant
      F1-stripped poll dominates; a scan that cannot see everything trips too. On the stock install it refuses bench
      rows (207's Main_Loop scenario guard, 114's 3:1), so it is reported, not shipped
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import struct
import sys
import zlib
from collections import defaultdict
from pathlib import Path

from . import config
from .eb import pressclosure as P
from .eb.model import EbScript

SCHEMA = 1
LANGS = tuple(config.LANGS)                       # us uk fr gr it es jp
ROLE_CODES = {"region": 0, "ctrl": 1, "fixed_ctrl": 2, "seq": 3}
KIND_CODES = {"ladder": 1, "jump": 2, "carry": 3}
#: census loco kind -> table kind; a candidate of any other mover kind is a generator error
KIND_MAP = {"ladder-navigable": "ladder", "ladder-auto": "ladder", "jump": "jump", "carry-loop": "carry"}
#: the trip-wire opcode classes (index = the class byte; 0 = no class): pressclosure's non-NEUTRAL opcode buckets
OP_CLASS_NAMES = (None, "exit", "battle", "window", "choice", "menu", "fmv", "ate", "item_party",
                  "flex_state", "spawn", "tile_bg", "sps", "walkmesh", "timer", "world", "control_swap")
OP_CLASS_SIZE = 0x120                             # every opcode 0x000..0x11F (0x100 + n = the 0xFF-prefixed page)
MIN_FUNC_LEN = 8
CTRL_UID = P.PLAYER_UID

JSON_PATH = Path(__file__).resolve().parent / "data" / "guest_traversal.json"
REGENERATE = ("py -m ff9mapkit.guest_traversal --write "
              "[--cs <Memoria>/Assembly-CSharp/Memoria/Netsync/NetSyncGuestLocalTable.cs]")
CS_NAME = "NetSyncGuestLocalTable.cs"
UNKNOWN_COMPONENT = "component: unknown (field index not built; this report never builds it)"

RULE = {
    "tier": "census tier LOCO-ONLY of the QUAD press closure (ff9mapkit.eb.pressclosure == "
            "studies/field-coop/guest-traversal/interaction_census.py): player locomotion only -- no window, choice, "
            "exit, battle, menu, persistent write, latch, spawn, tile or SPS op anywhere in the closure",
    "kinds": "ladder-navigable and ladder-auto -> ladder (1), jump -> jump (2), carry-loop -> carry (3); a candidate "
             "of any other mover kind (walk, teleport) is a generator error",
    "slice": "start = 2 + fpos of the FIRST func-table row whose tag matches (EventEngine.GetIP); end = the next body "
             "in (fpos, table index) order -- a tie goes to the later-listed row -- never past the entry "
             "(ff9mapkit eb/model.py); a start past the entry has length 0; a table that does not fit its entry, or "
             "no matching tag, is absent",
    "crc": "CRC-32/ISO-HDLC: zlib.crc32 == Unity.IO.Compression.Crc32Helper.UpdateCrc32(0u, buf, off, len); a "
           "function matches only when its length agrees first and then its CRC",
    "uid": "the DISPATCH uid: ctrl 250 (RunScript* through the control uid: the control character's own function), "
           "fixed_ctrl its fixed uid (1..249, naming DefinePlayerCharacter entries), region and seq 0",
    "func_order": "the region function (the row's entry, tag 3) first, then the rest by (role, entry, tag) "
                  "ascending, each triple once per row",
    "refusals": "R1 closure (truncated, decode failure, unresolved or computed uid/tag); R2 edge (self, party, sender, "
                "spawn, fixed_other); R3 roles (one function in two roles); R4 table (not strictly increasing, an fpos "
                "past the entry, a duplicated closure tag); R5 card (a tag-8 handler on the region); R6 seq (a "
                "RunSharedScript target that is not exactly one tag-0 function); R7 body (none, ctrl and fixed_ctrl "
                "mixed, two fixed uids); R8 short (a function under 8 bytes); R9 language (a language missing or "
                "different); R10 is a generator error (the C# slice twin disagrees with the kit model); R11 latch (any "
                "function outside the closure reads a MAP/instance var the closure writes on some CFG path before a "
                "plain B_LET covers it -- compound *_LET, ++/-- and an RHS self-read are reads, a write covers only "
                "its own bits -- exempt only when it is a tag-0/1 load-once reader: no RunScript*/RunScriptObject*/"
                "Seq targets it, no ReturnEntryFunctions can restart it (tag 1), its every uncovered read precedes "
                "its first backward-jump target, and its entry is created only by entry 0's tag-0 Init*); R12 op (a "
                "closure function holds ReturnEntryFunctions, or a TerminateEntry that is not the constant self-end "
                "255); R13 write (the closure writes a Global or Null var: it may write only Map and Instance vars); R14 key "
                "(a closure function polls a key mask that is not directions-only: a host-owned bit, a computed mask or "
                "a constant with no direction bit -- a live guest's FilterScriptButtons masks the host-owned bits during "
                "a control-off climb whenever ScriptKeyLockActive is on, so the loop would wait forever); R15 walk-in "
                "(the climb newly opens ground carrying an EXPOSED walk-in: NEW = the walkable components its landing "
                "points match (the walkable tri nearest the point's height, within 250 u; a final landing -- one some "
                "path ends its function at -- at a computed point or on no walkable tri lands on EVERY walkable "
                "component) minus the ARRIVAL components (where a player entry's tag 0 leaves the player with pathing on "
                "and no ladder attribute, on any entrance branch -- a UNION, so per-visit exposures remain by design -- "
                "placed by the engine's nearest-height tri pick, CreateObject's default height the topmost tri, with "
                "Main_Init's constant path / triangle disables taken off the walkmesh first); a walk-in is a tag-2 "
                "region (its area: every three consecutive points; a computed or QuadCircleData hot-fix region touches "
                "everything) or a tag-2 object (the walkable tris within its bump reach of where its tag 0 leaves it; "
                "a walker moved only by its own pathing-on walks and constant CreateObjects: the tris its placements "
                "reach through active tris and every walkable tri within its reach and +-400 height window of them; "
                "any other unknown or moved one touches everything), and it is EXPOSED when its tag-2 closure cannot "
                "be judged whole (truncated, a decode failure, unresolved, an expression / unknown / party target, an "
                "open scan: whatever its tier) or tiers STATEFUL and is not exempt -- exempt only when the scan visited "
                "every closure function, saw a site for each of its STATEFUL buckets, and every effect / STATEFUL site "
                "is dominated by both a user-control test and a constant Confirm / Special / Select poll proved "
                "together, with no yield or control write between them; THE JP WAIVER: a row whose only refusal is "
                "R15 in Japanese and that passes R15 there once the key fact also accepts Cancel -- where a Japanese "
                "guest's Confirm lands, a pre-existing hole of the co-op key mask on any ground -- ships, listed in "
                "\"waivers\", until the engine's ControlOnScriptKeys strips the JP-mapped bits); R16 watcher "
                "(specified and measured, NOT ENFORCED: a function the engine starts on its "
                "own whose effect fires on a host-owned key poll with no user-control test, or on the player's "
                "whereabouts with no constant F1-stripped poll -- it refuses bench rows on the stock install)",
}


class TableError(RuntimeError):
    """A hard generator error (R10, an unmapped candidate kind, a broken vector): the table is not emitted."""


# ================================================================================================ the slice + CRC rule
def _u16(b: bytes, i: int) -> int:
    return b[i] | (b[i + 1] << 8)


def func_slice(entry: bytes, tag: int) -> "tuple[int, int] | None":
    """``(start, length)`` of function ``tag`` inside one entry blob (the engine's ``allObjsEBData[sid]``), or None
    when absent -- the ONE rule both sides run (the C# twin is ``NetSyncGuestLocal.Slice``). ``start`` is GetIP's
    ``2 + fpos`` of the FIRST row whose tag matches; the end is the smallest ``2 + fpos[j]`` over the other rows with
    ``fpos[j] > fpos[hit]``, or ``fpos[j] == fpos[hit]`` and ``j > hit`` (a tie goes to the later-listed row), else the
    blob's length; ``length = max(0, min(end, len) - start)``."""
    n = len(entry)
    if n < 2:
        return None
    count = entry[1]
    if 2 + 4 * count > n:
        return None
    tags = [_u16(entry, 2 + 4 * k) for k in range(count)]
    fpos = [_u16(entry, 4 + 4 * k) for k in range(count)]
    want = tag & 0xFFFF
    hit = next((k for k in range(count) if tags[k] == want), None)
    if hit is None:
        return None
    start = 2 + fpos[hit]
    end = n
    for j in range(count):
        if j != hit and (fpos[j] > fpos[hit] or (fpos[j] == fpos[hit] and j > hit)):
            end = min(end, 2 + fpos[j])
    return start, max(0, min(end, n) - start)


def crc_flip(entry: bytes, start: int, length: int, at: int) -> int:
    """CRC-32 of ``entry[start:start+length]`` with byte ``at`` (relative) XOR 0x01, chained over three pieces
    (prefix, the flipped byte, suffix) exactly as the C# ``CrcFlip`` chains Crc32Helper; ``at`` outside
    ``0..length-1`` is the plain CRC. Never writes ``entry`` (the mutate lever perturbs only the hasher's input)."""
    if not (0 <= at < length):
        return zlib.crc32(bytes(entry[start:start + length])) & 0xFFFFFFFF
    crc = zlib.crc32(bytes(entry[start:start + at]))
    crc = zlib.crc32(bytes([entry[start + at] ^ 0x01]), crc)
    crc = zlib.crc32(bytes(entry[start + at + 1:start + length]), crc)
    return crc & 0xFFFFFFFF


def func_matches(entry: bytes, tag: int, want_len: int, want_crc: int, flip_at: int = -1) -> bool:
    """The gate's FuncMatches: the slice, then the LENGTH (load-bearing: code appended after a function's original
    return keeps its prefix CRC), then the CRC."""
    s = func_slice(entry, tag)
    if s is None or s[1] != want_len:
        return False
    return crc_flip(entry, s[0], s[1], flip_at) == (want_crc & 0xFFFFFFFF)


def _crc_int(v) -> int:
    return int(v, 16) if isinstance(v, str) else int(v)


def serialize_rows(rows) -> bytes:
    """The canonical TableCrc serialization: per row ``<HBBB`` (field, entry, kind, funcCount), then per function
    in row order ``<BBHBHI`` (role, entry, tag, uid, length, crc) -- little-endian, no padding."""
    out = bytearray()
    for r in rows:
        funcs = r["funcs"]
        out += struct.pack("<HBBB", r["field"], r["entry"], KIND_CODES[r["kind"]], len(funcs))
        for f in funcs:
            out += struct.pack("<BBHBHI", ROLE_CODES[f["role"]], f["entry"], f["tag"], f["uid"], f["len"],
                               _crc_int(f["crc"]))
    return bytes(out)


def table_crc(rows) -> int:
    """``zlib.crc32`` of :func:`serialize_rows` -- the C# ``TableCrcOf`` over the compiled arrays."""
    return zlib.crc32(serialize_rows(rows)) & 0xFFFFFFFF


def _hex(v: int) -> str:
    return "0x%08x" % (v & 0xFFFFFFFF)


# ================================================================================================ the shared vectors
#: kit-authored entry blobs (no game bytes), in BlobNames order -- each tests one edge of the slice rule
SELFTEST_BLOBS = (
    ("A", "010300000c0002000e00030011000400057f04010203040506070804"),   # a sorted table
    ("A+", "010300000c0002000e00030011000400057f0401020304050607080400"),  # A + one appended byte
    ("B", "01020300080003000b0004000004"),                                 # tag 3 listed twice
    ("C", "010200000b00010008000a0b0401020304"),                           # an unsorted table
    ("D", "01090000"),                                                     # a table claiming 9 rows in 4 bytes
    ("E", ""),                                                             # empty
    ("T", "0104000010000800160003001600020012000004057a027f2201040004"),   # a tie alias + a listed-last body
    ("P", "01010300c80004"),                                               # a body past the blob's end
)
SELFTEST_SLICE = (("A", 0), ("A", 2), ("A", 3), ("A", 9), ("A+", 3), ("B", 3), ("C", 1), ("C", 0), ("D", 0),
                  ("E", 0), ("T", 0), ("T", 2), ("T", 3), ("T", 8), ("T", 5), ("P", 3))
SELFTEST_FLIP = (("T", 3, 2), ("T", 3, 5), ("A", 3, 0), ("A", 3, 8))
SELFTEST_CRC_TEXT = ("", "123456789", "The quick brown fox jumps over the lazy dog")
_TOY1 = [{"field": 114, "entry": 9, "kind": "ladder", "funcs": [
    {"role": "region", "entry": 9, "tag": 3, "uid": 0, "len": 102, "crc": "0xf4e530de"},
    {"role": "ctrl", "entry": 11, "tag": 17, "uid": 250, "len": 644, "crc": "0x0ec1a3e4"}]}]
_TOY3 = _TOY1 + [
    {"field": 207, "entry": 10, "kind": "ladder", "funcs": [
        {"role": "region", "entry": 10, "tag": 3, "uid": 0, "len": 102, "crc": "0x5472f911"},
        {"role": "ctrl", "entry": 15, "tag": 50, "uid": 250, "len": 657, "crc": "0x8c63cbe3"},
        {"role": "seq", "entry": 3, "tag": 0, "uid": 0, "len": 42, "crc": "0xe0262dce"},
        {"role": "seq", "entry": 4, "tag": 0, "uid": 0, "len": 38, "crc": "0xc1a5853a"}]},
    {"field": 301, "entry": 7, "kind": "jump", "funcs": [
        {"role": "region", "entry": 7, "tag": 3, "uid": 0, "len": 101, "crc": "0x81ac1ae1"},
        {"role": "fixed_ctrl", "entry": 20, "tag": 26, "uid": 20, "len": 90, "crc": "0xdbb0de95"}]}]
SELFTEST_TOYS = (("toy1", _TOY1), ("toy3", _TOY3))


def _blob_as_eb(blob: bytes) -> bytes:
    """One entry blob wrapped as a one-slot ``.eb`` (header zeros, slot 0 right after the table) so the kit's own
    EbScript model can slice it -- the R10 cross-check on the vectors."""
    head = bytearray(0x80)
    head[0:2] = b"EV"
    head[2] = 2
    head[3] = 1
    slot = struct.pack("<HHBBH", 8, len(blob), 0, 0, 0)
    return bytes(head) + slot + bytes(blob)


def _model_slice(eb: EbScript, entry: int, tag: int) -> "tuple[int, int] | None":
    e = eb.entry(entry)
    if e.empty:
        return None
    f = e.func_by_tag(tag)
    if f is None:
        return None
    return f.abs_start - e.abs_start, f.length


def build_selftest() -> dict:
    """The shared vector set (JSON ``selftest`` -> the generated arrays -> the engine selftest + the kit's test). The
    expected values are COMPUTED here by :func:`func_slice` / :func:`crc_flip` / zlib and cross-checked against the
    kit model on every blob it can parse (R10)."""
    blobs = {name: bytes.fromhex(h) for name, h in SELFTEST_BLOBS}
    for name, blob in blobs.items():
        try:
            eb = EbScript.from_bytes(_blob_as_eb(blob))
        except Exception:
            continue                                   # D (truncated) cannot be parsed by the kit model
        for tag in sorted({t for (b, t) in SELFTEST_SLICE if b == name}):
            try:
                want = _model_slice(eb, 0, tag)
            except Exception:
                continue
            if func_slice(blob, tag) != want:
                raise TableError(f"R10: func_slice({name}, {tag}) = {func_slice(blob, tag)} but the kit model "
                                 f"slices {want}")
    out = {"crc": [{"text": t, "crc": _hex(zlib.crc32(t.encode("ascii")))} for t in SELFTEST_CRC_TEXT],
           "blobs": [{"name": n, "hex": h} for n, h in SELFTEST_BLOBS],
           "slice": [], "flip": [], "match": [], "toy": []}
    for name, tag in SELFTEST_SLICE:
        s = func_slice(blobs[name], tag)
        if s is None:
            out["slice"].append({"blob": name, "tag": tag, "start": -1, "len": -1, "crc": None})
        else:
            out["slice"].append({"blob": name, "tag": tag, "start": s[0], "len": s[1],
                                 "crc": _hex(zlib.crc32(blobs[name][s[0]:s[0] + s[1]]))})
    for name, tag, at in SELFTEST_FLIP:
        s = func_slice(blobs[name], tag)
        out["flip"].append({"blob": name, "tag": tag, "at": at, "crc": _hex(crc_flip(blobs[name], s[0], s[1], at))})
    a3 = next(c for c in out["slice"] if (c["blob"], c["tag"]) == ("A", 3))
    want = int(a3["crc"], 16)
    for name, crc, expect in (("A", want, True), ("A+", want, False), ("A", want ^ 1, False)):
        ok = func_matches(blobs[name], 3, a3["len"], crc)
        if ok != expect:
            raise TableError(f"match vector {name}/3 crc {_hex(crc)}: got {ok}, the vector says {expect}")
        out["match"].append({"blob": name, "tag": 3, "len": a3["len"], "crc": _hex(crc), "ok": ok})
    for name, rows in SELFTEST_TOYS:
        out["toy"].append({"name": name, "rows": rows, "table_crc": _hex(table_crc(rows))})
    return out


def build_op_classes() -> dict:
    """``OpClass[op]`` = the index in :data:`OP_CLASS_NAMES` of pressclosure's bucket for ``op`` when it is one of
    those classes, else 0 (NEUTRAL buckets, ``locomotion`` -- its effect depends on its target -- and unbucketed
    ops). The expression-level KEY ops are not opcodes and never appear here."""
    idx = {n: i for i, n in enumerate(OP_CLASS_NAMES) if n}
    return {"names": list(OP_CLASS_NAMES), "table": [idx.get(P.B.get(op), 0) for op in range(OP_CLASS_SIZE)]}


# ================================================================================================ the read-only loader
class InstallEvents:
    """The install's field event scripts, READ-ONLY (D16): UnityPy over ``StreamingAssets/p0data*.bin``, the
    bundle named by an existing ``.ff9mapkit-events-bundle.txt`` when present (else probed p0data7-first WITHOUT
    writing that cache). Nothing here writes the install or a cache inside it."""

    def __init__(self, game=None):
        from . import extract
        self._x = extract
        self.game = config.find_game_path(game)
        sa = self.game / "StreamingAssets"
        names = []
        cache = sa / extract._EVENTS_BUNDLE_CACHE
        if cache.is_file():
            n = cache.read_text(encoding="utf-8").strip()
            if n:
                names.append(n)
        if not names:
            names = sorted((p.name for p in sa.glob("p0data*.bin")), key=lambda n: (0 if n == "p0data7.bin" else 1, n))
        env = None
        for n in names:
            try:
                cand = extract._load_env(sa / n)
            except Exception:
                continue
            if any("eventbinary/field/" in k.lower() for k in cand.container):
                env = cand
                break
        if env is None:
            raise FileNotFoundError(f"no field event bundle (eventbinary/field/...) under {sa}")
        self._by = {lang: {} for lang in LANGS}
        for k, obj in env.container.items():
            kl = k.lower()
            if not kl.endswith(".eb.bytes"):
                continue
            for lang in LANGS:
                marker = f"eventbinary/field/{lang}/"
                i = kl.find(marker)
                if i >= 0:
                    self._by[lang][kl[i + len(marker):-len(".eb.bytes")]] = obj
                    break
        self._cache = {}

    def eb(self, fid: int, lang: str = "us") -> "bytes | None":
        key = (int(fid), lang)
        if key not in self._cache:
            evt = self._x.ID_TO_EVT.get(int(fid))
            obj = self._by[lang].get(evt.lower()) if evt else None
            data = None
            if obj is not None:
                with self._x.env_lock:
                    data = self._x._raw_bytes(obj.read())
            self._cache[key] = data or None
        return self._cache[key]


# ================================================================================================ one row
def _entry_blob(eb: EbScript, ei: int) -> bytes:
    e = eb.entry(ei)
    return eb.data[e.abs_start:e.abs_end]


def _var_text(v) -> str:
    return P.var_name(*v)


def _func_roles(v: P.PressVerdict):
    """Per closure function: the set of dispatch kinds that reach it, and the edges that do (DFS order)."""
    roles = defaultdict(set)
    via = defaultdict(list)
    for ed in v.edges:
        if ed.tag is None:
            continue
        for t in ed.targets:
            roles[(t, ed.tag)].add(ed.kind)
            via[(t, ed.tag)].append(ed)
    return roles, via


def _table_why(eb: EbScript, ei: int, tag: int) -> "str | None":
    """R4 on one closure function's entry: its table strictly increasing, inside the entry, the tag listed once."""
    e = eb.entry(ei)
    offs = [f.fpos for f in e.funcs]
    if any(b <= a for a, b in zip(offs, offs[1:])):
        return f"entry {ei}'s func table is not strictly increasing"
    if any(2 + o > e.size for o in offs):
        return f"entry {ei} lists an fpos past its end"
    if sum(1 for f in e.funcs if f.tag == tag) > 1:
        return f"entry {ei} lists tag {tag} twice"
    return None


def _derive_one(fld: P.FieldModel, v: P.PressVerdict) -> dict:
    """The row a verdict would ship in ONE language, with its first R1-R8 / R12-R14 refusal and its R11 trace (R9
    compares these across languages; the caller picks the final refusal and runs R15)."""
    eb = fld.eb
    region = v.region
    roles, via = _func_roles(v)
    funcs, pre = [], None

    def refuse(code, why):
        nonlocal pre
        if pre is None:
            pre = f"{code}: {why}"

    if v.truncated:
        refuse("R1 closure", "the walk was truncated (depth > 8 or past its node budget)")
    if v.decode_fail:
        refuse("R1 closure", "an instruction or expression failed to decode")
    if v.unresolved:
        refuse("R1 closure", "unresolved " + ", ".join(f"{k} x{n}" for k, n in v.unresolved))
    for ed in v.edges:
        if ed.kind in ("expr", "unknown", "party"):
            refuse("R1 closure", f"{ed.src[0]}:{ed.src[1]} {ed.call} has a {ed.kind} target")
    for ed in v.edges:
        if ed.kind not in P.SHIPPABLE_EDGES:
            refuse("R2 edge", f"{ed.src[0]}:{ed.src[1]} {ed.call}"
                              f"({'' if ed.uid is None else 'uid %d, ' % ed.uid}tag {ed.tag}) is a {ed.kind} edge")
    for node in v.funcs:
        ks = set(roles.get(node, ()))
        if node == (region, 3):
            if ks:
                refuse("R3 roles", f"the region function {region}:3 is also reached as {'/'.join(sorted(ks))}")
            role = "region"
        elif len(ks) != 1:
            refuse("R3 roles", f"{node[0]}:{node[1]} is reached as {'/'.join(sorted(ks)) or 'nothing'}")
            role = "/".join(sorted(ks)) or None
        else:
            role = next(iter(ks))
        uids = sorted({ed.uid for ed in via.get(node, ()) if ed.kind == "fixed_ctrl"})
        if role == "ctrl":
            uid = CTRL_UID
        elif role == "fixed_ctrl":
            uid = uids[0] if uids else None
            if len(uids) > 1:
                refuse("R7 body", f"{node[0]}:{node[1]} is reached through fixed uids {uids}")
        else:
            uid = 0
        s = func_slice(_entry_blob(eb, node[0]), node[1])
        f = {"role": role, "entry": node[0], "tag": node[1], "uid": uid,
             "len": s[1] if s else -1, "crc": _hex(zlib.crc32(_entry_blob(eb, node[0])[s[0]:s[0] + s[1]])) if s else None}
        first = via.get(node, ())
        if role in ("ctrl", "fixed_ctrl") and first:
            f["call"] = first[0].call
            f["level"] = first[0].level
        funcs.append(f)
        tw = _table_why(eb, node[0], node[1])
        if tw:
            refuse("R4 table", tw)
    if any(f.tag == 8 for f in eb.entry(region).funcs):
        refuse("R5 card", f"region entry {region} has a tag-8 (Special / card) handler")
    for ed in v.edges:
        if ed.kind != "seq":
            continue
        if not ed.targets:
            refuse("R6 seq", f"{ed.src[0]}:{ed.src[1]} RunSharedScript names an empty entry {ed.missing}")
            continue
        tf = [g.tag for g in eb.entry(ed.targets[0]).funcs]
        if tf != [0]:
            refuse("R6 seq", f"RunSharedScript({ed.targets[0]}) targets an entry with functions {tf}, not one tag 0")
    ctrl = [f for f in funcs if f["role"] == "ctrl"]
    fixed = [f for f in funcs if f["role"] == "fixed_ctrl"]
    if not ctrl and not fixed:
        refuse("R7 body", "no ctrl or fixed_ctrl body function")
    elif ctrl and fixed:
        refuse("R7 body", "ctrl and fixed_ctrl bodies are mixed")
    elif len({f["uid"] for f in fixed}) > 1:
        refuse("R7 body", f"two fixed uids {sorted({f['uid'] for f in fixed})}")
    for f in funcs:
        if f["len"] < MIN_FUNC_LEN:
            refuse("R8 short", f"{f['entry']}:{f['tag']} is {f['len']} bytes (< {MIN_FUNC_LEN})")
    for node in v.funcs:                               # R12: every hashed function, op by op
        start = fld.func(*node).abs_start
        for ins in fld.instrs(*node):
            if ins.op not in (P.RETURN_ENTRY_OP, P.TERMINATE_OP):
                continue
            arg = ("an expression" if ins.arg_is_expr[0] else ins.args[0]) if ins.args else "nothing"
            if ins.op == P.RETURN_ENTRY_OP:
                refuse("R12 op", f"{node[0]}:{node[1]} +{ins.off - start} ReturnEntryFunctions({arg}) restarts an "
                                 "entry's tag 1 (code outside the closure)")
            elif ins.op == P.TERMINATE_OP and not P.is_const_self_end(ins):
                refuse("R12 op", f"{node[0]}:{node[1]} +{ins.off - start} TerminateEntry({arg}) is not the constant "
                                 "self-end 255 (it disposes another object)")
    for (src, typ, idx, _owner) in v.closure.writes:   # R13: the closure may write only Map (1) / Instance (2) vars
        if src not in (1, 2):
            refuse("R13 write", f"the closure writes {P.var_name(src, typ, idx)} ("
                                f"{'a GLOB gEventGlobal' if src == 0 else 'a Null Memoria-custom / save-data'} var; "
                                "only Map and Instance vars may be written)")
    for (kop, mask, bucket, (ke, kt), _off) in v.closure.key_sites:   # R14: every key poll directions-only
        if bucket == "key_dir":
            continue
        if mask is None or bucket == "key_press":
            refuse("R14 key", f"{ke}:{kt} polls {kop}({'a computed mask' if mask is None else '0x%X' % mask}) -- a "
                              "host-owned key a live guest's climb cannot see")
        else:
            refuse("R14 key", f"{ke}:{kt} polls {kop}(0x{mask:X}) -- no direction bit (a live guest's climb answers "
                              "only its own direction keys)")
    readers = P.latch_consumers(fld, v)
    bad = defaultdict(list)
    for r in readers:
        if r.consumer:
            bad[r.var].append(r.label)
    r11 = None
    if bad:
        r11 = "R11 latch: " + "; ".join(f"{_var_text(var)} is read before it is written by {', '.join(lbls)}"
                                        for var, lbls in sorted(bad.items()))
    head = [f for f in funcs if f["role"] == "region"]
    rest = sorted((f for f in funcs if f["role"] != "region"),
                  key=lambda f: (ROLE_CODES.get(f["role"], 9), f["entry"], f["tag"]))
    asyn = any(ed.kind in ("ctrl", "fixed_ctrl") and ed.op == 0x10 for ed in v.edges)
    return {"tier": v.tier, "kind": v.kind, "gate": list(v.gate), "player_entries": list(v.player_entries),
            "funcs": head + rest, "async": asyn, "pre": pre, "r11": r11,
            "exempt": [r.exempt_why for r in readers if r.first == "read" and r.exempt_why]}


# ================================================================================================ R15: the walk-ins
#: walkmesh_pass.comp_y's landing match: the WALKABLE tri at the point's (x, z) whose centre height is nearest its y,
#: within this many units
LAND_TOL = 250
#: EventEngine.POS_COMMAND_DEFAULTY = 32768 (EventEngine.Constructor.cs:11): CreateObject / MoveInstantEx place an object
#: at Unity y = +32768 (EventEngine.DoEventCode.cs:384) and FieldMapActorController.SetPosition snaps it to the tri
#: GetTriIdxAtPos picks nearest that height (FieldMapActorController.cs:44, :1279-1303). Unity y is the walkmesh's
#: NEGATED y (WalkMesh.cs:54; getvobj's f[1] = -pos[1], EBin.cs), so in the kit's y-down script frame the default is
#: y = -32768: the TOPMOST tri under the point
ENGINE_DEFAULT_Y = -32768
#: the moves R15's placement walk follows in an entry's tag 0 (pressclosure.PLACE_ARGS): CreateObject, MoveInstantXZY,
#: Walk / WalkXZY / SideWalkXZY and SetupJump move the entry itself; MoveInstantXZYEx / MoveInstantEx move their uid
SPAWN_OPS = frozenset(P.PLACE_ARGS)
#: moves of the entry itself the walk cannot place (WalkTowardObject, Slide, WalkToExit -- MOVJ walks gCur to the
#: sMapJumpX / Z a CalculateExitPosition computed, EventEngine.DoEventCode.cs:872-876): the path's point becomes unknown
UNPLACED_SELF_OPS = frozenset({0x24, 0xA5, 0xA0})
#: WalkEx (0x117, its operand 0 the moved uid) moves another object the walk cannot place either
UNPLACED_EX_OPS = frozenset({0x117})
#: the PATHING switch the spawn walk follows (FieldMapActorController.charFlags bit 0, on at creation,
#: FieldMapActorController.cs:110; off, the player has no walk control -- ServiceChar is skipped, :360):
#: CreateObject / MoveInstantEx turn it on (EventEngine.DoEventCode.cs:287), MoveInstantXZY / MoveInstantXZYEx
#: (:2237-2239) and SetupJump (:3017-3021) off, SetPathing(v) (:2679-2689) sets it -- field 2508's entry 2 never on
PATH_ON_OPS, PATH_OFF_OPS, SET_PATHING_OP = frozenset({0x1D, 0xBF}), frozenset({0xA1, 0xAD, 0xE2}), 0xA8
#: AddCharacterAttribute / RemoveCharacterAttribute (EventEngine.DoEventCode.cs:2696-2707): bit 4 is the ladder
#: attribute (the census's ladder_flag); a field starts with every attribute clear (EventEngine.cs:594 clears charArray,
#: a model gets a new FF9Char, :1131-1136)
ATTR_ADD_OP, ATTR_CLEAR_OP, LADDER_ATTR = 0xCC, 0xCD, 4
#: an object's moves outside its own tag-0 placement walk: its own SELF_MOVE_OPS in another function, or anyone's Ex /
#: attach op that can name it -- its bump then touches every component (it is not where its tag 0 left it)
SELF_MOVE_OPS = SPAWN_OPS | UNPLACED_SELF_OPS | {0xDC}
EX_MOVE_OPS = frozenset({0xAD, 0xBF}) | UNPLACED_EX_OPS
ATTACH_OPS = frozenset({0x4C, 0xD4})
#: the BUMP REACH (WalkMesh.Collision, WalkMesh.cs:908-931, in mode 2 -- CollisionRequest's tag-2 test,
#: EventCollision.cs:290-306): 4 * collRad(player) + 4 * collRad(object) + the object's speed + 60. collRad is a
#: SetObjectLogicalSize's operand 1 (EventEngine.DoEventCode.cs:1528-1553; PosObj's default 16, PosObj.cs:13; a
#: computed one counts its Byte maximum), speed its Byte maximum (Actor.cs:116); the height window (only
#: -400 < dy < 400 bumps, WalkMesh.cs:919-920) is applied to a WALKER's footprint only (:meth:`Ground.walker_touched`)
SIZE_OP, DEFAULT_COLL_RAD, MAX_BYTE, BUMP_SLACK, BUMP_DY = 0x4B, 16, 255, 60, 400
#: V1's WALKER: an object whose every move outside its tag-0 placement walk is one of its own pathing-on walks (Walk,
#: WalkXZY, SideWalkXZY: with pathing on an actor steps only onto an ACTIVE neighbour tri,
#: WalkMesh.BGI_findAccessibleTriangle, WalkMesh.cs:1144-1170) or a CreateObject at a constant point (pathing on,
#: EventEngine.DoEventCode.cs:287) stays on the tris its placements' tris reach through active tris
WALK_OPS = frozenset({0x23, 0xA2, 0xE8})
#: ... and what can turn its pathing off or carry it (FAIL CLOSED: the bound is not taken): MoveInstantXZY(Ex) and
#: SetupJump (PATH_OFF_OPS), SetPathing of anything but a constant non-zero, an attach, a move the walk cannot place
#: (WalkTowardObject, Slide, WalkToExit) and Jump
WALKER_BREAK_OPS = PATH_OFF_OPS | ATTACH_OPS | UNPLACED_SELF_OPS | {0xDC}
#: the engine's own per-field switches that can turn a tri ON whatever the script's operands say (fldMapNo / effMapNo
#: -> tris): Treno/Pub's RunScriptAsync 62 (EventEngine.DoEventCode.cs:150-151), Daguerreo's RunScript 105 / 106
#: (:159-164; turnOffTriManually sets them from a var, EventEngine.turnOffTriManually.cs:40-44), Fossil Roo's
#: CreateObject 109 / 110 (:297-311), EnablePathTriangle's forced 107 (:2674-2675) and its 207 -> 208 twin (:2672-2673)
HOTFIX_ON_TRIS = {900: frozenset({62}), 2803: frozenset({105, 106}), 1421: frozenset({109, 110}),
                  1606: frozenset({107}), 1753: frozenset({208})}
#: EnablePathTriangle / EnablePath (EventEngine.DoEventCode.cs:2661-2678 -> WalkMesh.BGI_triSetActive /
#: BGI_floorSetActive) and BAFRAME (0x10A, :3184-3187 -> WalkMesh.BGI_animShowFrame, WalkMesh.cs:1081-1121: it turns a
#: walkmesh animation frame's tris on)
PATH_TRI_OP, PATH_FLOOR_OP, BAFRAME_OP = 0x9A, 0xCB, 0x10A
#: EventEngineUtils.QuadCircleData's keys (EventEngineUtils.cs:1722-1738 -- engine code, no game bytes): fldMapNo * 1000
#: + the region's sid (EMinigame.CreateNPCID, EMinigame.cs:315-318). EventEngine.IsInQuadHotFix (EventEngine.TreadQuad.cs
#: :41-54) tests such a region against a hard-coded circle instead of, or as well as, its SetRegion: it touches all
QUAD_CIRCLE_KEYS = frozenset({2222004, 2901007, 916005, 1553006, 356014, 404007, 601005, 2151003, 757006, 2950023,
                              2950022, 2952022, 2255002, 561008})
#: the walk-in tiers R15 refuses on newly reachable ground (TRIVIAL, EXIT-ONLY and every other tier ship)
WALKIN_TIERS = frozenset({"STATEFUL"})
#: a row derive_field could not judge (no walkmesh provider); assemble refuses to emit a table that holds one
R15_NOT_EVALUATED = "R15 walk-in: not evaluated (derive_field was given no walkmesh provider)"
#: THE JP WAIVER (V6, the lead's decision): a row whose ONLY refusal is R15 in Japanese, and that passes R15 there once
#: the KEY fact also accepts the Cancel bit (pressclosure.JP_F1_STRIPPED), SHIPS -- recorded in the JSON's "waivers"
#: and the far report, never in what the engine compiles. A Japanese guest's physical Confirm reaches a Japanese chest's
#: KEYON(Cancel | Special) at control-on on ANY ground today (ETb.ProcessJapaneseLayout swaps it into Cancel before
#: NetSyncField.FilterScriptButtons, and ControlOnScriptKeys strips Confirm / Special / Select only): a pre-existing hole
#: in the co-op key mask, not one a climb opens. The engine follow-up strips the JP-mapped bits in ControlOnScriptKeys
#: (NetSyncField.cs:955); then the waiver goes
WAIVER_LANG = "jp"
WAIVER_WHY = ("exempt once F1's control-on mask also strips Cancel, where ETb.ProcessJapaneseLayout puts a Japanese "
              "guest's Confirm (the engine follow-up: NetSyncField.ControlOnScriptKeys)")
_ENV_CAP = 64                                    # the placement walk's path environments per block (more: dropped)
_POS, _PATH, _LADDER = "@pos", "@path", "@ladder"   # its keys for this path's last placement and switches


def _overlap_xz(a, b) -> bool:
    """Two XZ triangles share a point, edges inclusive: no edge normal of either separates them (the separating-axis
    test in exact integer arithmetic; a zero-length edge has no normal and separates nothing)."""
    for tri in (a, b):
        for i in range(3):
            (x1, z1), (x2, z2) = tri[i], tri[(i + 1) % 3]
            nx, nz = z2 - z1, x1 - x2
            if nx == 0 and nz == 0:
                continue
            pa = [nx * x + nz * z for (x, z) in a]
            pb = [nx * x + nz * z for (x, z) in b]
            if max(pa) < min(pb) or max(pb) < min(pa):
                return False
    return True


def _dist_xz(px, pz, tri) -> float:
    """The XZ distance from a point to a triangle (0 inside or on it)."""
    if _overlap_xz(((px, pz),) * 3, tri):
        return 0.0
    best = None
    for i in range(3):
        (ax, az), (bx, bz) = tri[i], tri[(i + 1) % 3]
        dx, dz = bx - ax, bz - az
        n = dx * dx + dz * dz
        t = 0.0 if n == 0 else max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / n))
        d = ((px - ax - t * dx) ** 2 + (pz - az - t * dz) ** 2) ** 0.5
        best = d if best is None or d < best else best
    return best


class Ground:
    """One field's walkmesh as R15 reads it, read-only over a parsed ``BgiWalkmesh``: walkmesh_pass's player-walkable
    components (:func:`_components`) with ``disabled`` tris (:func:`main_init_disables`) taken off first, the engine's
    placement pick, walkmesh_pass's landing match, and the walk-in region area and bump reach; ``blocked``
    (:func:`walker_blocks`) the tris no walker can ever step on, ``enabled`` (:func:`activatable`) the tris code of the
    field can turn on."""

    def __init__(self, wm, disabled=frozenset(), blocked=frozenset(), enabled=frozenset()):
        self.wm = wm
        self.disabled = frozenset(disabled)
        self.blocked = frozenset(blocked)
        self.enabled = frozenset(enabled)
        self.comp_of = _components(wm, self.disabled)
        wv = wm.world_verts()
        self.static_walk = [_player_walkable(t) for t in wm.tris]
        self.walk = [w and i not in self.disabled for i, w in enumerate(self.static_walk)]
        self.height = [sum(wv[k][1] for k in t.vtx) / 3.0 for t in wm.tris]
        self.yr = [(min(wv[k][1] for k in t.vtx), max(wv[k][1] for k in t.vtx)) for t in wm.tris]
        self.xz = [tuple((wv[k][0], wv[k][2]) for k in t.vtx) for t in wm.tris]
        self.walkable = frozenset(self.comp_of[t] for t in range(len(wm.tris)) if self.walk[t])

    def _comps(self, tris) -> set:
        """The walkable components of ``tris``. A statically walkable tri Main_Init disabled stands for the walkable
        components its disabled run borders: a script that re-enables it joins them."""
        out, seen = set(), set()
        stack = [t for t in tris if not self.walk[t] and self.static_walk[t]]
        out |= {self.comp_of[t] for t in tris if self.walk[t]}
        while stack:
            t = stack.pop()
            if t in seen:
                continue
            seen.add(t)
            for n in self.wm.tris[t].nbr:
                if 0 <= n < len(self.walk):
                    if self.walk[n]:
                        out.add(self.comp_of[n])
                    elif self.static_walk[n]:
                        stack.append(n)
        return out

    def placed_tri(self, x, y, z) -> "int | None":
        """The tri an object placed at ``(x, y, z)`` stands on: FieldMapActorController.GetTriIdxAtPos -- of EVERY tri
        whose XZ projection holds the point (no flag test), the first whose centre height is nearest y (None:
        CreateObject's :data:`ENGINE_DEFAULT_Y`, the topmost) -- or None off the mesh."""
        yy = ENGINE_DEFAULT_Y if y is None else y
        best = None
        for t in self.wm.tris_at(x, z):
            d = abs(yy - self.height[t])
            if best is None or d < best[0]:
                best = (d, t)
        return None if best is None else best[1]

    def placed(self, x, y, z) -> "int | None":
        """The component of :meth:`placed_tri`, or None off the mesh (SetDefaultCharPos's tri 0 is never counted an
        arrival)."""
        t = self.placed_tri(x, y, z)
        return None if t is None else self.comp_of[t]

    def landed(self, x, y, z) -> set:
        """walkmesh_pass's landing match: the component of the WALKABLE tri at ``(x, z)`` whose centre height is nearest
        y, within :data:`LAND_TOL`; with no y (absent or computed) EVERY walkable tri's component there (fail closed);
        empty when no walkable floor is under the point -- mid-air."""
        tris = [t for t in self.wm.tris_at(x, z) if self.walk[t]]
        if y is None:
            return {self.comp_of[t] for t in tris}
        best = None
        for t in tris:
            d = abs(y - self.height[t])
            if best is None or d < best[0]:
                best = (d, t)
        return {self.comp_of[best[1]]} if best is not None and best[0] <= LAND_TOL else set()

    def touched(self, poly) -> set:
        """The components a walk-in region can fire on: every walkable tri whose XZ projection overlaps the region's
        AREA, edges inclusive. The area is EventEngine.IsInQuad's: the union of the triangles of every three consecutive
        points (a centre-and-corners probe misses a tri the polygon only crosses)."""
        n = len(poly)
        area = [tuple(tuple(poly[(i + k) % n]) for k in range(3)) for i in range(n)]
        return self._comps([t for t, tri in enumerate(self.xz)
                            if self.static_walk[t] and any(_overlap_xz(tri, q) for q in area)])

    def touched_all(self, polys) -> set:
        return set().union(*(self.touched(p) for p in polys))

    def near(self, x, z, reach) -> set:
        """The components a bump at ``(x, z)`` can fire on: every walkable tri within ``reach`` of it in XZ."""
        return self._comps([t for t, tri in enumerate(self.xz) if self.static_walk[t] and _dist_xz(x, z, tri) <= reach])

    def region(self, seeds) -> set:
        """Every tri a pathing-on walker standing on ``seeds`` can reach: its own tri, then any neighbour that is
        statically ACTIVE (triFlags bit 0) or :attr:`enabled`, and not :attr:`blocked` -- the restriction bits are
        ignored (an NPC is blocked by bit 0x40 only, the player by 0x80, WalkMesh.cs:1155-1169, and SetTriangleFlagMask
        can lift both), and a tri Main_Init disables still joins what a re-enable would unless it is blocked."""
        out, stack = set(), list(seeds)
        while stack:
            t = stack.pop()
            if t in out:
                continue
            out.add(t)
            stack += [n for n in self.wm.tris[t].nbr if 0 <= n < len(self.wm.tris) and n not in out
                      and (self.wm.tris[n].tri_flags & 1 or n in self.enabled) and n not in self.blocked]
        return out

    def walker_touched(self, region, reach) -> set:
        """The components a walker on ``region`` can bump into: its own walkable tris, and every walkable tri within
        ``reach`` of one of them in XZ whose height range comes within :data:`BUMP_DY` of it (WalkMesh.Collision bumps
        only for -400 < dy < 400)."""
        box = {t: (min(x for x, _ in self.xz[t]), max(x for x, _ in self.xz[t]),
                   min(z for _, z in self.xz[t]), max(z for _, z in self.xz[t])) for t in range(len(self.xz))}
        hit = set(region)
        for u in range(len(self.xz)):
            if u in hit or not self.static_walk[u]:
                continue
            bu = box[u]
            for t in region:
                bt = box[t]
                if bt[0] - bu[1] > reach or bu[0] - bt[1] > reach or bt[2] - bu[3] > reach or bu[2] - bt[3] > reach:
                    continue
                (t0, t1), (u0, u1) = self.yr[t], self.yr[u]
                if max(0, u0 - t1, t0 - u1) >= BUMP_DY:
                    continue
                if _overlap_xz(self.xz[t], self.xz[u]) or \
                        min(min(_dist_xz(x, z, self.xz[u]) for (x, z) in self.xz[t]),
                            min(_dist_xz(x, z, self.xz[t]) for (x, z) in self.xz[u])) <= reach:
                    hit.add(u)
                    break
        return self._comps(hit)


def main_init_disables(fld: P.FieldModel, wm) -> frozenset:
    """The tris Main_Init (entry 0's tag 0) turns off with constant operands -- EnablePathTriangle(tri, 0) and
    EnablePath(floor, 0) (EventEngine.DoEventCode.cs:2661-2678 -> WalkMesh.BGI_triSetActive / BGI_floorSetActive clear
    triFlags bit 0) -- on ANY of its branches (the conservative direction: a disabled tri splits components). A later
    re-enable is not followed (:meth:`Ground._comps` lets a disabled tri stand for what it borders)."""
    out = set()
    for ins in fld.instrs(0, 0):
        if ins.op not in (0x9A, 0xCB) or len(ins.args) < 2 or any(ins.arg_is_expr[:2]) or ins.args[1] != 0:
            continue
        if ins.op == 0x9A:
            out.add(ins.args[0])
        elif ins.args[0] < len(wm.floors):
            out |= set(wm.floors[ins.args[0]].tri_ndx_list)
    return frozenset(t for t in out if 0 <= t < len(wm.tris))


def activatable(fld: P.FieldModel, wm) -> frozenset:
    """The tris code of the field can turn ON (triFlags bit 0) once the walkmesh is loaded: an EnablePathTriangle /
    EnablePath whose flag is not the constant 0 -- its tri, or its floor's tris -- and the field's
    :data:`HOTFIX_ON_TRIS`; EVERY tri when one names a computed tri or floor, when the field runs any BAFRAME (it turns
    on a walkmesh animation frame's tris; the frames are not read), or when a function does not decode (FAIL CLOSED)."""
    every = frozenset(range(len(wm.tris)))
    out = set(HOTFIX_ON_TRIS.get(fld.fid, ()))
    for (ce, ct) in fld.iter_funcs():
        if fld.decode_failed(ce, ct):
            return every
        for ins in fld.instrs(ce, ct):
            if ins.op == BAFRAME_OP:
                return every
            if ins.op not in (PATH_TRI_OP, PATH_FLOOR_OP) or len(ins.args) < 2 or \
                    (not ins.arg_is_expr[1] and ins.args[1] == 0):
                continue
            if ins.arg_is_expr[0]:
                return every
            if ins.op == PATH_TRI_OP:
                out.add(ins.args[0])
            elif ins.args[0] < len(wm.floors):
                out |= set(wm.floors[ins.args[0]].tri_ndx_list)
    return frozenset(t for t in out if 0 <= t < len(wm.tris))


def walker_blocks(fld: P.FieldModel, wm) -> frozenset:
    """The tris no walker can ever step on: those Main_Init -- and Main_Reinit, which restarts the field's objects in
    place after a battle on a reloaded walkmesh (EventEngine.cs:686-690) -- disables with constant operands on EVERY
    path before its first yield (a forward MUST dataflow over its CFG: until entry 0 yields no other object has run, an
    object it creates is skipped by the pass that created it, EBin.ProcessCode stateNew, EBin.cs:115-119) and that NO
    code of the field can turn back on (:func:`activatable`). FAIL CLOSED: a CFG that does not build blocks nothing."""

    def off_by(ins) -> set:
        if ins.op not in (0x9A, 0xCB) or len(ins.args) < 2 or any(ins.arg_is_expr[:2]) or ins.args[1] != 0:
            return set()
        if ins.op == 0x9A:
            return {ins.args[0]}
        return set(wm.floors[ins.args[0]].tri_ndx_list) if ins.args[0] < len(wm.floors) else set()

    def surely_off(tag) -> frozenset:
        flow = P._flow(fld, 0, tag)
        if flow is None or not flow.blocks or fld.decode_failed(0, tag):
            return frozenset()
        state, work, finals = {flow.entry: frozenset()}, [flow.entry], []
        while work:
            b = work.pop()
            cur = state[b]
            for ins in flow.blocks[b].instrs:
                if ins.op in P.YIELD_OPS:
                    break
                cur = cur | off_by(ins)
                if P._ends_path(ins):
                    break
            else:
                for (n, _c) in flow.blocks[b].succs:
                    if n not in state or not state[n] <= cur:
                        state[n] = cur if n not in state else state[n] & cur
                        work.append(n)
                if flow.blocks[b].succs:
                    continue
            finals.append(cur)
        return frozenset.intersection(*finals) if finals else frozenset()
    sure = surely_off(0)
    if fld.func(0, 10) is not None:
        sure &= surely_off(10)
    return frozenset(t for t in sure - activatable(fld, wm) if 0 <= t < len(wm.tris))


def field_ground(fld: P.FieldModel, wm) -> Ground:
    return Ground(wm, main_init_disables(fld, wm), walker_blocks(fld, wm), activatable(fld, wm))


def _lets(fld: P.FieldModel, ei: int, tag: int, ins) -> "list | None":
    """The placement walk's view of one instruction's var writes: ``[(var, const | None)]`` -- the constant only for a
    plain ``SET(var = const)`` -- or None when a write's target is not a var (the walk then forgets every var)."""
    from .eb.cfg import parse_set
    writes = []
    for w in fld.expr_info(ei, tag, ins):
        for wr in w["writes"]:
            if len(wr) != 3:
                return None
            writes.append(tuple(wr))
    if len(writes) != 1:
        return [(w, None) for w in writes]
    st = parse_set(fld.data, ins) if ins.op == 0x05 else None
    if st is not None and st.kind == "assign" and st.pure and st.value is not None \
            and (st.source, st.vtype, st.index) == writes[0]:
        return [(writes[0], st.value)]
    return [(writes[0], None)]


def _apply_lets(env: frozenset, lets, tracked) -> frozenset:
    """``env`` (a tracked var -> its constant on this path) after ``lets``: a write forgets every var it overlaps (a
    Byte store inside an Int16), then a constant store to a ``tracked`` var is known. The walk's own keys survive."""
    if lets is None:
        return frozenset(kv for kv in env if isinstance(kv[0], str))
    if not lets:
        return env
    d = dict(env)
    for (var, val) in lets:
        bits = P.var_bits(var[1], var[2])
        for k in [k for k in d if not isinstance(k, str) and k[0] == var[0] and P.var_bits(k[1], k[2]) & bits]:
            del d[k]
        if val is not None and var in tracked:
            d[var] = val
    return frozenset(d.items())


def _leaf(toks) -> "tuple | None":
    """An operand expression that is ONE token: ``("var", (src, typ, idx))``, ``("const", value)`` or ``("self", k)``
    (``obj(uid=255).f[k]``, the entry's own x / y / z), else None."""
    head = []
    for t in (toks or ()):
        if t[0] == 0x7F:
            break
        head.append(t)
    if len(head) != 1:
        return None
    o, val = head[0]
    if o >= 0xC0:
        return "var", (o & 3, (o >> 2) & 7, val)
    if o == 0x78 and val[0] == P.SELF_UID and val[1] in (0, 1, 2):
        return "self", val[1]
    return ("const", val) if o in (0x7D, 0x7E) else None


def _operand(ins, toks, i, env) -> "int | None":
    """Operand ``i`` of a placement op: its immediate, or an expression that is ONE constant, ONE var read or ONE read
    of the entry's own position whose value this path knows; else None."""
    if i is None or i >= len(ins.args):
        return None
    if not ins.arg_is_expr[i]:
        return P.s16(ins.args[i])
    leaf = _leaf(toks[i])
    if leaf is None:
        return None
    d = dict(env)
    if leaf[0] == "var":
        val = d.get(leaf[1])
    elif leaf[0] == "self":
        val = None if d.get(_POS) is None else d[_POS][2 + leaf[1]]
    else:
        val = leaf[1]
    return None if val is None else P.s16(val & 0xFFFF)


def _moves(fld: P.FieldModel, ei: int, ins, wanted) -> "str | None":
    """How one instruction of entry ``ei``'s code moves an entry of ``wanted``: ``"place"`` (a :data:`SPAWN_OPS` op of
    it), ``"lost"`` (a move the walk cannot place -- :data:`UNPLACED_SELF_OPS`, an unplaced Ex op, an Ex op whose uid
    is computed or does not resolve, or one naming it among others) or None."""
    op = ins.op
    if op in UNPLACED_SELF_OPS:
        return "lost" if ei in wanted else None
    if op not in SPAWN_OPS and op not in UNPLACED_EX_OPS:
        return None
    if op not in (0xAD, 0xBF) and op not in UNPLACED_EX_OPS:
        return "place" if ei in wanted else None
    if not ins.args or ins.arg_is_expr[0]:
        return "lost"
    tgts, why = fld.resolve_uid(ins.args[0], ei)
    if why:
        return "lost"
    if not (tgts & wanted):
        return None
    return "place" if tgts <= wanted and op not in UNPLACED_EX_OPS else "lost"


def _switches(fld: P.FieldModel, ei: int, ins, how, d) -> None:
    """The placement walk's pathing and ladder-attribute switches for one instruction of entry ``ei``'s tag 0 (``d`` is
    the path's environment, updated in place; None = unknown)."""
    op = ins.op
    if how == "place":
        if op in PATH_ON_OPS:
            d[_PATH] = 1
        elif op in PATH_OFF_OPS:
            d[_PATH] = 0
    elif how == "lost":
        d[_PATH] = None
    elif op == SET_PATHING_OP and ins.args:
        v = None if ins.arg_is_expr[0] else int(bool(ins.args[0]))
        d[_PATH] = 0 if (v == 1 and fld.fid == 2508 and ei == 2) else v      # EventEngine.DoEventCode.cs:2682-2683
    elif op in (ATTR_ADD_OP, ATTR_CLEAR_OP) and ins.args:
        if ins.arg_is_expr[0]:
            d[_LADDER] = None
        elif ins.args[0] & LADDER_ATTR:
            d[_LADDER] = 1 if op == ATTR_ADD_OP else 0


_WIDTH = {0: 1, 1: 1, 2: 0xFFFFFF, 3: 0xFFFFFF, 4: 0xFF, 5: 0xFF, 6: 0xFFFF, 7: 0xFFFF}


def _on_edge(env: frozenset, conds) -> "frozenset | None":
    """``env`` along a CFG edge whose guard is ``conds`` (eb.cfg's: an AND of atoms that PROVABLY hold on it), or None
    when this path's known values contradict an exact atom (``==``, ``!=``, ``in``: the edge is not taken). An exact
    ``==`` / single-value ``in`` on a var the path does not know yet is LEARNED -- a switch on the entrance index
    keeps each arm's value, so a later ``if Global.Int16[2] == 122`` follows only that arm. Ordered compares decide
    nothing."""
    if not conds:
        return env
    d = dict(env)
    for c in conds:
        key = (c.source, c.vtype, c.index)
        vals = c.value if c.cmp == "in" else (c.value,)
        if c.cmp not in ("==", "!=", "in") or not all(isinstance(v, int) for v in vals):
            continue
        m = _WIDTH.get(c.vtype, 0xFFFFFFFF)
        if key in d:
            hit = any((d[key] - v) & m == 0 for v in vals)
            if hit != (c.cmp != "!="):
                return None
        elif c.cmp != "!=" and len(vals) == 1:
            d[key] = vals[0]
    return frozenset(d.items())


def _place_walk(fld: P.FieldModel, ei: int, wanted) -> "tuple[list, bool, frozenset] | None":
    """The path-sensitive walk over entry ``ei``'s tag 0: ``(ends, dropped, placed)`` with one ``(point, pathing,
    ladder)`` per path end -- ``point`` the path's LAST placement of an entry of ``wanted`` as ``(off, op, x, y, z)``
    (None: none, or unknown -- a saved or computed position, a var set outside the function, an unknown y on an op that
    carries one, a move the walk cannot place), ``pathing`` / ``ladder`` the player's switches there (1 / 0 / None unknown; a path
    starts with pathing on and no ladder attribute). An operand that is one var read takes the var's constant on that
    path (each branch's ``SET(Map.Int16[0] = c)``, tracking only the vars a placement reads), ``obj(uid=255).f[0..2]``
    the path's own last point; an edge whose guard this path's known values contradict is not taken (:func:`_on_edge`).
    ``dropped``: a path past :data:`_ENV_CAP` environments was not followed; ``placed``: every point any path placed it
    at (None among them: a placement or move it could not resolve). None when the function does not decode or its CFG
    does not build."""
    from .eb.disasm import instr_expr_tokens
    flow = P._flow(fld, ei, 0)
    if flow is None or not flow.blocks or fld.decode_failed(ei, 0):
        return None
    how, toks, tracked = {}, {}, set()          # the moves, their operand tokens, and the vars they read
    for ins in fld.instrs(ei, 0):
        m = _moves(fld, ei, ins, wanted)
        if m:
            how[ins.off] = m
        if m == "place":
            try:
                toks[ins.off] = instr_expr_tokens(fld.data, ins)
            except Exception:                     # noqa: BLE001 -- an undecodable operand: the path's point is unknown
                toks[ins.off] = None
            tracked |= {lf[1] for t in (toks[ins.off] or ()) for lf in [_leaf(t)] if lf and lf[0] == "var"}
    ends, dropped, placed = [], False, set()

    def ended(envs):
        for env in envs:
            d = dict(env)
            ends.append((d.get(_POS), d.get(_PATH), d.get(_LADDER)))
    state, work = {flow.entry: {frozenset({(_PATH, 1), (_LADDER, 0)})}}, [flow.entry]
    while work:
        b = work.pop()
        cur = set(state[b])
        for ins in flow.blocks[b].instrs:
            m = how.get(ins.off)
            moved = set()
            for env in cur:
                d = dict(env)
                if m == "place":
                    xi, yi, zi = P.PLACE_ARGS[ins.op]
                    x, y, z = ((None,) * 3 if toks[ins.off] is None else
                               (_operand(ins, toks[ins.off], k, env) for k in (xi, yi, zi)))
                    if x is not None and z is not None and (yi is None or y is not None):
                        d[_POS] = (ins.off, ins.op, x, y, z)
                    else:
                        d.pop(_POS, None)
                    placed.add(d.get(_POS))
                elif m == "lost":
                    d.pop(_POS, None)
                    placed.add(None)
                _switches(fld, ei, ins, m, d)
                moved.add(frozenset(d.items()))
            cur = {_apply_lets(env, _lets(fld, ei, 0, ins), tracked) for env in moved}
            if P._ends_path(ins):
                ended(cur)
                break
        else:
            if not flow.blocks[b].succs:
                ended(cur)
            for (s, conds) in flow.blocks[b].succs:
                nxt = {e for e in (_on_edge(env, conds) for env in cur) if e is not None}
                have = state.get(s, set())
                if nxt and not nxt <= have:
                    if len(have | nxt) > _ENV_CAP:
                        dropped = True                # past the cap a path is not followed
                        continue
                    state[s] = have | nxt
                    work.append(s)
    return ends, dropped, frozenset(placed)


def spawn_points(fld: P.FieldModel) -> list:
    """Where the field's own scripts leave the controlled player at field entry: ``(entry, off, op, x, y, z)`` -- the
    LAST placement (:data:`SPAWN_OPS`) on each path through a player entry's tag 0 (:func:`_place_walk`), so every
    entrance branch's own point (a CreateObject that a MoveInstantXZY then lifts to its floor counts once, at the
    lift), KEPT only where the path ends with the player's pathing ON and no ladder attribute -- a path that leaves the
    player with pathing off (SetPathing(0), a MoveInstantXZY with no SetPathing(1) after it) or on a ladder
    (AddCharacterAttribute(4)) hands it no walk control there: its tag 1 carries it on, and that is not followed.
    FAIL CLOSED toward FEWER arrivals: a path whose last placement or switches stay unknown places nothing, a path past
    :data:`_ENV_CAP` environments is not followed, and a function whose CFG does not build yields none. What is NOT
    proved: that a kept point is never moved again before control (a player's tag 1 or Main_Init may still move it)."""
    out = set()
    for pe in sorted(fld.player):
        res = _place_walk(fld, pe, fld.player)
        for (pos, path, ladder) in (res[0] if res else ()):
            if pos is not None and path == 1 and ladder == 0:
                out.add((pe,) + pos)
    return sorted(out)


def _is_final(fld: P.FieldModel, node, off: int, lands) -> bool:
    """Some path from the landing op at ``off`` to its function's end runs no further landing op of that function
    (``lands``: their offsets). A function whose CFG does not build counts every landing final (FAIL CLOSED)."""
    flow = P._flow(fld, *node)
    b0 = None if flow is None else flow.block_at(off)
    if b0 is None:
        return True
    stack, seen = [(b0, off)], set()
    while stack:
        b, after = stack.pop()
        hit = None
        for ins in flow.blocks[b].instrs:
            if after is not None and ins.off <= after:
                continue
            if ins.off in lands:
                hit = "land"
                break
            if P._ends_path(ins):
                hit = "end"
                break
        if hit == "end" or (hit is None and not flow.blocks[b].succs):
            return True
        if hit is None:
            for (s, _c) in flow.blocks[b].succs:
                if s not in seen:
                    seen.add(s)
                    stack.append((s, None))
    return False


def landing_points(fld: P.FieldModel, v: P.PressVerdict) -> list:
    """The closure's player landing points (pressclosure's ``Closure.landings``, walkmesh_pass's ``landings``) as
    ``(op, x, y, z, node, off, final)``: ``final`` when some path from the op to its function's end runs no further
    landing op -- where a climb can leave the player standing. A ladder's mount points hang mid-air on the ladder and
    are always followed by its loop and a dismount, so they are not final."""
    lands = defaultdict(set)
    for (_op, _x, _y, _z, node, off) in v.closure.landings:
        lands[node].add(off)
    out = []
    for (op, x, y, z, node, off) in dict.fromkeys(v.closure.landings):
        out.append((op, x, y, z, node, off, _is_final(fld, node, off, lands[node])))
    return out


def region_polys(fld: P.FieldModel, ei: int) -> "list | None":
    """Every static SetRegion polygon of entry ``ei`` (none: the region never fires), or None when one is computed."""
    from .eventscan import _region_points
    polys = []
    for f in fld.eb.entry(ei).funcs:
        for ins in fld.instrs(ei, f.tag):
            if ins.op == 0x29:
                pts = _region_points(ins)
                if not pts:
                    return None
                polys.append(pts)
    return polys


def tread_regions(fld: P.FieldModel) -> list:
    """Every tag-2 walk-in region of the field (the far report's set: a region entry other than 0 with a tag-2
    function) as ``(entry, polygons, verdict)``: ``polygons`` the entry's :func:`region_polys` (None when one is
    computed: FAIL CLOSED, it may touch anything); ``verdict`` its tag-2 closure."""
    out = []
    for e in fld.eb.entries:
        if e.empty or e.index == 0 or not (fld.kind.get(e.index, set()) & {"region", "region?"}) \
                or not any(f.tag == 2 for f in e.funcs):
            continue
        out.append((e.index, region_polys(fld, e.index), P.analyze_root(fld, e.index, 2)))
    return out


def bump_objects(fld: P.FieldModel) -> list:
    """Every object the controlled player can BUMP into: an object entry (an InitObject's, or an ``object?``) other
    than a player entry with a tag-2 function -- EventCollision.CollisionRequest's ``CheckNPCPush`` path runs the stock
    ``Request(obj, 1, 2)`` on the guest's own copy with no gate (EventCollision.cs:305-306; WalkMesh.Collision, mode 2,
    only ever returns an Actor, cid 4, WalkMesh.cs:917) -- as ``(entry, verdict)``, ``verdict`` its tag-2 closure."""
    out = []
    for e in fld.eb.entries:
        if e.empty or e.index == 0 or e.index in fld.player \
                or not (fld.kind.get(e.index, set()) & {"object", "object?"}) or not any(f.tag == 2 for f in e.funcs):
            continue
        out.append((e.index, P.analyze_root(fld, e.index, 2)))
    return out


def _coll_rad(fld: P.FieldModel, entries) -> int:
    """The largest collRad any SetObjectLogicalSize of ``entries`` can set (a computed one: the Byte maximum), else
    PosObj's default."""
    best = DEFAULT_COLL_RAD
    for ei in entries:
        for f in fld.eb.entry(ei).funcs:
            for ins in fld.instrs(ei, f.tag):
                if ins.op == SIZE_OP and len(ins.args) >= 2:
                    best = max(best, MAX_BYTE if ins.arg_is_expr[1] else ins.args[1] & 0xFF)
    return best


def bump_reach(fld: P.FieldModel, ei: int) -> int:
    """How far from object ``ei`` the player's bump fires (the BUMP REACH formula above)."""
    return 4 * _coll_rad(fld, sorted(fld.player)) + 4 * _coll_rad(fld, [ei]) + MAX_BYTE + BUMP_SLACK


def _own_code(fld: P.FieldModel, ei: int) -> "list | None":
    """Every function whose moves move object ``ei`` ITSELF: its own, then the tag 0 of every Seq it runs (a Seq keeps
    its caller's body, EBin.ProcessCode's objV0, EBin.cs:165-166), transitively -- None when a Seq's entry is
    computed (it may run anything on it)."""
    out, stack = [], [(ei, f.tag) for f in fld.eb.entry(ei).funcs]
    while stack:
        node = stack.pop(0)
        if node in out:
            continue
        out.append(node)
        for ins in fld.instrs(*node):
            if ins.op == P.SEQ_OP and ins.args:
                if ins.arg_is_expr[0]:
                    return None
                t = ins.args[0]
                if 0 <= t < fld.eb.entry_count and not fld.eb.entry(t).empty and fld.eb.entry(t).funcs:
                    stack.append((t, fld.eb.entry(t).funcs[0].tag))
    return out


def _moved_elsewhere(fld: P.FieldModel, ei: int) -> "str | None":
    """Why object ``ei`` may stand somewhere its tag-0 walk does not say, or None: a move of its own outside its tag 0
    (:func:`_own_code`: its other functions, and any Seq it runs -- the tag-0 walk follows no Seq either), or anyone's
    Ex / attach op whose uid is computed or can name it (:func:`_ex_named`)."""
    from .eb._optables import OP_NAMES
    own = _own_code(fld, ei)
    if own is None:
        return "it runs a Seq of a computed entry"
    for (ce, ct) in own:
        if (ce, ct) == (ei, 0):
            continue
        for ins in fld.instrs(ce, ct):
            if ins.op in SELF_MOVE_OPS and ins.op not in (0xAD, 0xBF):
                return f"its {ce}:{ct} runs {OP_NAMES.get(ins.op, hex(ins.op))}"
    return _ex_named(fld, ei)


def _ex_named(fld: P.FieldModel, ei: int) -> "str | None":
    """Anyone's Ex move / attach op whose uid is computed or can name object ``ei``, as its why. Uid 255 is gCur
    (EventEngine.GetObjUID, EventEngine.cs:959-962): the executing entry, and inside a Seq the body that runs it
    (EBin.ProcessCode objV0, EBin.cs:164-165; ad3, :181) -- so it names ``ei`` in ``ei``'s own code (:func:`_own_code`,
    every Seq it runs included) as well as in the entry's own."""
    from .eb._optables import OP_NAMES
    own = set(_own_code(fld, ei) or ())
    for (ce, ct) in fld.iter_funcs():
        for ins in fld.instrs(ce, ct):
            if ins.op in EX_MOVE_OPS or ins.op in ATTACH_OPS:
                if not ins.args:
                    continue
                uids = [None if ins.arg_is_expr[k] else ins.args[k]
                        for k in range(min(len(ins.args), 2 if ins.op in ATTACH_OPS else 1))]
                for uid in uids:
                    tgts, why = (set(), "computed") if uid is None else fld.resolve_uid(uid, ce)
                    if why or ei in tgts or (uid == P.SELF_UID and (ce, ct) in own):
                        return f"{ce}:{ct} runs {OP_NAMES.get(ins.op, hex(ins.op))} on it"
    return None


def _walk_bound(fld: P.FieldModel, ei: int) -> "tuple[set, str | None]":
    """V1 -- the WALKER bound on object ``ei``: ``(points, None)`` when its every move outside its tag-0 placement
    walk (:func:`_own_code`) is a :data:`WALK_OPS` walk of its own or a CreateObject at a constant point (``points``:
    those), nothing in its code can turn its pathing off (:data:`WALKER_BREAK_OPS`, a SetPathing of anything but a
    constant non-zero -- field 2508's entry 2 never), and no Ex / attach op anywhere can name it (:func:`_ex_named`);
    else ``(set(), why)``."""
    from .eb._optables import OP_NAMES
    own = _own_code(fld, ei)
    if own is None:
        return set(), "it runs a Seq of a computed entry"
    pts = set()
    for (ce, ct) in own:
        for ins in fld.instrs(ce, ct):
            name = OP_NAMES.get(ins.op, hex(ins.op))
            if ins.op in WALKER_BREAK_OPS:
                return set(), f"its {ce}:{ct} runs {name}"
            if ins.op == SET_PATHING_OP and (not ins.args or ins.arg_is_expr[0] or not ins.args[0]
                                             or (fld.fid == 2508 and ei == 2)):
                return set(), f"its {ce}:{ct} runs {name} (its pathing may go off)"
            # a move of its own body outside tag 0 (whose placements are the walk's; an Ex op is judged by its uid,
            # _ex_named): only a WALK_OPS walk, or a CreateObject at a constant point
            if (ce, ct) == (ei, 0) or ins.op not in SELF_MOVE_OPS or ins.op in EX_MOVE_OPS or ins.op in WALK_OPS:
                continue
            if ins.op != 0x1D:
                return set(), f"its {ce}:{ct} runs {name}"
            _op, x, _y, z = P.place_point(ins)
            if x is None or z is None:
                return set(), f"its {ce}:{ct} runs {name} at a computed point"
            pts.add((ins.off, ins.op, x, None, z))
    why = _ex_named(fld, ei)
    return (set(), why) if why else (pts, None)


def bump_touched(fld: P.FieldModel, ei: int, ground: Ground) -> "tuple[set, str | None]":
    """``(components, why_all)``: where a bump of object ``ei`` can fire -- the walkable tris within its
    :func:`bump_reach` of every point its tag-0 placement walk ends at; for a WALKER (moved elsewhere,
    :func:`_moved_elsewhere`, but only as :func:`_walk_bound` allows) the tris every placement point's tri reaches
    (:meth:`Ground.region`) and every walkable tri within its reach and height window of them
    (:meth:`Ground.walker_touched`) -- or EVERY walkable component with the reason (FAIL CLOSED) when a path ends with
    no known placement, the walk drops a path or does not build, or the object is moved elsewhere unbounded (or from a
    point off the walkmesh)."""
    res = _place_walk(fld, ei, {ei})
    why = None
    if res is None:
        why = f"{ei}:0's CFG does not build"
    elif res[1]:
        why = f"{ei}:0 has more paths than the placement walk follows"
    elif not res[0] or any(pos is None for (pos, _p, _l) in res[0]):
        why = f"{ei}:0 leaves it at no known point on some path"
    else:
        why = _moved_elsewhere(fld, ei)
        if why:
            extra, unbound = _walk_bound(fld, ei)
            seeds = [None] if None in res[2] else [ground.placed_tri(x, y, z) for (_o, _op, x, y, z) in res[2] | extra]
            if unbound is None and None not in seeds:
                return ground.walker_touched(ground.region(seeds), bump_reach(fld, ei)), None
    if why:
        return set(ground.walkable), why
    reach = bump_reach(fld, ei)
    out = set()
    for (_off, _op, x, _y, z) in {pos for (pos, _p, _l) in res[0]}:
        out |= ground.near(x, z, reach)
    return out, None


def walk_judgement(fld: P.FieldModel, ei: int, tv: P.PressVerdict, stripped: int = P.F1_STRIPPED) -> tuple:
    """``(exempt, gap)`` of walk-in ``ei``'s tag-2 closure ``tv``. ``gap``: why it cannot be judged whole -- its closure
    walk's own gaps (pressclosure.closure_gaps) or an open scan (the scan follows Init* here, as the closure walk does)
    -- which leaves the walk-in EXPOSED whatever its tier (V4, FAIL CLOSED); ``exempt``: the hidden-item exemption
    (pressclosure.WatchScan.exempt_why) with ``stripped`` the control-on mask a KEY fact needs."""
    ws = P.watch_scan(fld, ei, 2, spawn=True, stripped=stripped)
    gaps = P.closure_gaps(tv) + [f"its scan is open: {w}" for w in ws.open[:1]]
    return ws.exempt_why(tv) is None, "; ".join(gaps) or None


def walk_ins(fld: P.FieldModel, ground: Ground, stripped: int = P.F1_STRIPPED) -> list:
    """Every walk-in R15 judges, resolved on ``ground``: ``(kind, entry, components, why_all, verdict, exempt, gap)``
    -- ``kind`` "walk-in" (a tag-2 region: its area, :meth:`Ground.touched`) or "bump" (an object:
    :func:`bump_touched`); ``components`` None with ``why_all`` when it may touch everything (a computed SetRegion, a
    QuadCircleData region, an object at no static point); ``exempt`` / ``gap`` its :func:`walk_judgement` (``stripped``
    the KEY fact's mask -- the JP waiver passes pressclosure.JP_F1_STRIPPED)."""
    out = []
    for (ei, polys, tv) in tread_regions(fld):
        if (fld.fid or 0) * 1000 + ei in QUAD_CIRCLE_KEYS:
            comps, why = None, "the engine's QuadCircleData hot-fix tests it against its own circle"
        elif polys is None:
            comps, why = None, "its region is computed"
        else:
            comps, why = ground.touched_all(polys), None
        out.append(("walk-in", ei, comps, why, tv) + walk_judgement(fld, ei, tv, stripped))
    for (ei, tv) in bump_objects(fld):
        comps, why = bump_touched(fld, ei, ground)
        out.append(("bump", ei, None if why else comps, why, tv) + walk_judgement(fld, ei, tv, stripped))
    return out


def exposed(walk) -> bool:
    """R15's EXPOSED: a walk-in whose tag-2 closure cannot be judged whole (its ``gap``), or one of a
    :data:`WALKIN_TIERS` tier that is not ``exempt``."""
    (_k, _e, _c, _w, tv, exempt, gap) = walk
    return bool(gap) or (tv.tier in WALKIN_TIERS and not exempt)


def _walkin_effects(tv: P.PressVerdict) -> str:
    return ", ".join(_effect_classes(tv)) or ", ".join(tv.reasons) or tv.tier


def walkin(fld: P.FieldModel, v: P.PressVerdict, ground: Ground, arrival: set, walks: list) -> dict:
    """R15 on one row: ``{"land", "new", "wild", "why", "hits"}`` -- the components its landing points match, those
    that are not an ARRIVAL (``arrival``: where :func:`spawn_points` stands the player), the final landings it cannot
    name, the refusal or None, and every exposed walk-in on NEW ground as ``(kind, entry)``. A FINAL landing at a
    computed point or on no walkable tri within LAND_TOL cannot be named, so it may leave the player on ANY walkable
    component (FAIL CLOSED: its landing is all of them; a non-final one is in flight). An :func:`exposed` walk-in
    (``walks``, :func:`walk_ins`) whose components meet a NEW one refuses: nothing gates a tag-2 tread or bump for a
    spectator, so a guest who climbs there runs it on its own copy."""
    from .eb._optables import OP_NAMES
    land, named, wild = set(), set(), []
    for (op, x, y, z, node, off, final) in landing_points(fld, v):
        at = f"{node[0]}:{node[1]} +{off - fld.func(*node).abs_start} {OP_NAMES.get(op, hex(op))}"
        if x is None or z is None:
            if final:
                wild.append(f"{at} can end the climb at a computed point")
            continue
        got = ground.landed(x, y, z)
        if not got and final:
            wild.append(f"{at}({x}, {y}, {z}) can end the climb on no walkable tri within {LAND_TOL} u")
        named |= got
    land = named | (set(ground.walkable) if wild else set())
    new = land - arrival
    why, hits = None, []
    for walk in walks:
        (kind, ei, comps, why_all, tv, _exempt, gap) = walk
        if not new or not exposed(walk):
            continue
        hit = sorted(new) if comps is None else sorted(comps & new)
        if not hit:
            continue
        hits.append((kind, ei))
        if why is not None:
            continue
        c = hit[0]
        how = "may carry" if comps is None else "carries"
        why = f"R15 walk-in: landing component {c} (not an arrival) {how} {kind} {ei}:2 ({_walkin_effects(tv)})"
        if gap:
            why += f" -- its tag-2 closure cannot be judged whole ({gap})"
        if comps is None:
            why += f" -- {why_all}"
        if c not in named:
            why += f" -- {wild[0]}, so the climb may land on any walkable component"
    return {"land": land, "new": new, "wild": wild, "why": why, "hits": hits}


def field_arrival(fld: P.FieldModel, ground: Ground) -> set:
    """The ARRIVAL components: where the engine stands each :func:`spawn_points` point (empty when none resolves).
    ARRIVAL is a UNION over the field's entrance branches: on one visit the player spawns on ONE of them, so a climb
    from there can still reach a walk-in on another branch's arrival ground -- a per-visit exposure R15 keeps by
    design (the union is the field's own "reachable on foot from SOME entrance")."""
    return {ground.placed(x, y, z) for (_e, _o, _op, x, y, z) in spawn_points(fld)} - {None}


# ================================================================================================ R16: the watchers
#: R16 is SPECIFIED and MEASURED but NOT ENFORCED: on the stock install it refuses bench rows (207:10 / 207:11 through
#: the stock scenario-guard idiom in 207's Main_Loop, 114:9 through 114's 3:1), and those must ship -- derive() runs
#: derive_field with r16=R16_ENFORCED; flip it only once the lead has ruled on the measured set
R16_ENFORCED = False


def _watch_why(fld: P.FieldModel, ws: P.WatchScan) -> "str | None":
    """Why one watch root trips R16, or None: (a) an effect a host-owned key poll triggers that no user-control test
    dominates, (b) an effect the controlled player's whereabouts trigger that no constant F1-stripped poll dominates,
    or an open scan (FAIL CLOSED)."""
    r = f"{ws.root[0]}:{ws.root[1]}"
    if ws.open:
        return f"{r} cannot be fully scanned ({ws.open[0]})"
    a = ws.key_triggered()
    if a:
        e = a[0]
        polls = ", ".join(dict.fromkeys(p.what for p in ws.host_polls())) or "a key-tainted var"
        return f"(a) {r} {e.what} at {e.at(fld)} fires on a host-owned key poll ({polls}) with no user-control test"
    b = ws.position_triggered()
    if b:
        e = b[0]
        reads = ", ".join(dict.fromkeys(x.what for x in ws.reads)) or "a position-tainted var"
        return (f"(b) {r} {e.what} at {e.at(fld)} fires on the player's whereabouts ({reads}) with no constant "
                "Confirm / Special / Select poll before it")
    return None


def watchers(fld: P.FieldModel) -> list:
    """R16 on one field: ``[(root, why)]`` for every :func:`pressclosure.watch_roots` root (under the field's taint,
    :func:`pressclosure.field_watch`) that trips (:func:`_watch_why`)."""
    out = []
    for root, ws in P.field_watch(fld).items():
        why = _watch_why(fld, ws)
        if why:
            out.append((root, why))
    return out


def watcher_refusal(fld: P.FieldModel, v: P.PressVerdict, found: list) -> "str | None":
    """R16 on one row: the first watcher outside the row's own closure functions, as its refusal text."""
    inside = set(v.funcs)
    for (root, why) in found:
        if root not in inside:
            return f"R16 watcher: {why}"
    return None


def _signature(d: dict) -> tuple:
    return (d["tier"], d["kind"], tuple(d["player_entries"]), d["pre"], d["r11"],
            tuple((f["role"], f["entry"], f["tag"], f["uid"], f["len"], f["crc"]) for f in d["funcs"]))


def _check_r10(eb: EbScript, funcs, where: str) -> None:
    """R10 (a hard error): the C# slice twin equals the kit model on every function the table ships."""
    for f in funcs:
        mine = func_slice(_entry_blob(eb, f["entry"]), f["tag"])
        model = _model_slice(eb, f["entry"], f["tag"])
        if mine != model:
            raise TableError(f"R10 at {where} {f['entry']}:{f['tag']}: func_slice {mine} != the kit model {model}")


def derive_field(fid: int, by_lang: dict, langs=LANGS, *, walkmesh=None, r16=False):
    """``(candidates, rows, refused, quad_roots)`` for one field: ``by_lang`` maps each language in ``langs`` to its
    ``.eb`` bytes (None = missing). The US (first-listed) language classifies; every other one must agree (R9).
    ``walkmesh`` is R15's provider: a zero-argument callable returning the field's ``BgiWalkmesh``, called at most once
    and only when a row reaches R15 (it raises to refuse the whole table). Without one a row that passes R1-R14 is
    returned with ``"r15": R15_NOT_EVALUATED`` -- never a pass: :func:`assemble` refuses to emit it. A row whose only
    R15 refusal is :data:`WAIVER_LANG`'s and that passes R15 there under pressclosure.JP_F1_STRIPPED ships with
    ``"waived"`` (THE JP WAIVER, :data:`WAIVER_WHY`). ``r16`` applies R16 (:func:`watchers`, every language) after R15
    -- a waived row it refuses is refused; :func:`derive` passes :data:`R16_ENFORCED`.
    Install-free: the offline tests feed it kit-assembled synthetic fields (and a kit-built walkmesh)."""
    base = langs[0]
    data = by_lang.get(base)
    fld = P.FieldModel.from_bytes(data, fid)
    verdicts = P.analyze_regions(fld)
    others, other_v = {}, {}
    wm, walk_ctx, watch_ctx = None, {}, {}
    rows, refused, cands = [], [], 0

    def r15(lang, lf, lv, stripped=P.F1_STRIPPED):
        nonlocal wm
        if wm is None:
            wm = walkmesh()
        if lang not in walk_ctx:
            ground = field_ground(lf, wm)
            walk_ctx[lang] = (ground, field_arrival(lf, ground))
        if (lang, stripped) not in walk_ctx:
            walk_ctx[(lang, stripped)] = walk_ins(lf, walk_ctx[lang][0], stripped)
        return walkin(lf, lv, *walk_ctx[lang], walk_ctx[(lang, stripped)])

    def r16_why(lang, lf, lv):
        if lang not in watch_ctx:
            watch_ctx[lang] = watchers(lf)
        return watcher_refusal(lf, lv, watch_ctx[lang])

    for v in verdicts:
        if not v.candidate:
            continue
        cands += 1
        if v.kind not in KIND_MAP:
            raise TableError(f"field {fid} entry {v.region}: candidate kind {v.kind!r} has no table kind")
        mine = _derive_one(fld, v)
        refusal = mine["pre"]
        if refusal is None:
            diffs = []
            for lang in langs[1:]:
                blob = by_lang.get(lang)
                if not blob:
                    diffs.append(f"{lang} has no .eb")
                    continue
                if lang not in others:
                    others[lang] = P.FieldModel.from_bytes(blob, fid)
                ofld = others[lang]
                ov = next((x for x in P.analyze_regions(ofld) if x.region == v.region), None)
                if ov is None:
                    diffs.append(f"{lang}: entry {v.region} is not a QUAD root")
                    continue
                other_v[(lang, v.region)] = ov
                od = _derive_one(ofld, ov)
                if _signature(od) != _signature(mine):
                    diffs.append(f"{lang} differs ({od['tier']}/{od['kind']}, {len(od['funcs'])} functions)")
            if diffs:
                refusal = "R9 language: " + "; ".join(diffs)
        if refusal is None:
            refusal = mine["r11"]
        unjudged = refusal is None and walkmesh is None
        waived = None
        if refusal is None and walkmesh is not None:  # R15: every language's spawns and walk-ins, one walkmesh
            for lang in langs:
                lf, lv = (fld, v) if lang == base else (others[lang], other_v[(lang, v.region)])
                w = r15(lang, lf, lv)
                if w["why"] and lang == WAIVER_LANG and not r15(lang, lf, lv, P.JP_F1_STRIPPED)["why"]:
                    waived = (f"R15 walk-in waived: jp F1 hole -- {', '.join(f'{k} {e}:2' for k, e in w['hits'])} "
                              f"{WAIVER_WHY}")
                    continue
                if w["why"]:
                    refusal = w["why"] if lang == base else f"{w['why']} [{lang}]"
                    break
        if refusal is None and r16:                    # R16: every language's watchers, no walkmesh needed
            for lang in langs:
                why = r16_why(lang, fld, v) if lang == base else r16_why(lang, others[lang], other_v[(lang, v.region)])
                if why:
                    refusal = why if lang == base else f"{why} [{lang}]"
                    break
        row = {"field": fid, "entry": v.region, "kind": KIND_MAP[v.kind]}
        if refusal is None:
            from .extract import ID_TO_EVT
            _check_r10(fld.eb, mine["funcs"], f"field {fid} ({base})")
            for lang in langs[1:]:
                _check_r10(others[lang].eb, mine["funcs"], f"field {fid} ({lang})")
            row.update({"evt": ID_TO_EVT.get(fid, ""), "async": mine["async"], "funcs": mine["funcs"],
                        "census_kind": v.kind, "gate": mine["gate"], "player_entries": mine["player_entries"]})
            if unjudged:
                row["r15"] = R15_NOT_EVALUATED
            if waived:
                row["waived"] = waived
            rows.append(row)
        else:
            row.update({"refusal": refusal, "funcs": mine["funcs"]})
            refused.append(row)
    return cands, rows, refused, len(verdicts)


# ================================================================================================ the whole table
def _field_ids():
    from ._fieldtable import FIELD_BY_ID
    return sorted(FIELD_BY_ID)


def assemble(rows, refused, counts_in, sha1) -> dict:
    """The JSON object, keys in their fixed order, from the per-field results. A row R15 did not judge is a hard
    error: the committed table only ever ships rows every rule passed. A waived row's ``"waived"`` moves to the
    top-level ``"waivers"`` (``{field, entry, waiver}``, ascending): the rows -- and so :func:`table_crc` and
    :func:`render_cs` -- never carry it."""
    rows_in = rows
    unjudged = [f"{r['field']}:{r['entry']}" for r in rows if "r15" in r]
    if unjudged:
        raise TableError(f"R15 was not evaluated for {', '.join(unjudged)} (derive_field ran with no walkmesh "
                         "provider) -- the table never ships an unjudged row")
    rows = sorted(({k: x for k, x in r.items() if k != "waived"} for r in rows), key=lambda r: (r["field"], r["entry"]))
    waivers = [{"field": r["field"], "entry": r["entry"], "waiver": r["waived"]}
               for r in sorted(rows_in, key=lambda r: (r["field"], r["entry"])) if r.get("waived")]
    refused = sorted(refused, key=lambda r: (r["field"], r["entry"]))
    counts = {"fields_scanned": counts_in["fields_scanned"], "quad_roots": counts_in["quad_roots"],
              "census_candidates": counts_in["census_candidates"], "rows": len(rows),
              "funcs": sum(len(r["funcs"]) for r in rows), "fields": len({r["field"] for r in rows}),
              "refused": len(refused)}
    return {"schema": SCHEMA, "generated_from": "install by guest_traversal.py", "regenerate": REGENERATE,
            "langs": list(LANGS), "rule": dict(RULE), "counts": counts, "table_crc": _hex(table_crc(rows)),
            "rows": rows, "refused": refused, "waivers": waivers, "eb_sha1": sha1, "op_classes": build_op_classes(),
            "selftest": build_selftest()}


def _r15_walkmesh(ev, index: "dict | None", fid: int):
    """R15's walkmesh for one field, read-only through the ALREADY-built field index (the far report's loader, never
    ``build_field_index``). A missing index or walkmesh is a :class:`TableError` naming it: the generator never ships
    a row R15 could not judge."""
    from . import extract
    if index is None:
        raise TableError(f"R15 walk-in needs field {fid}'s walkmesh, but the install's field index "
                         f"(StreamingAssets/{extract.INDEX_NAME}) is not built or does not parse -- this generator "
                         "never builds it (that writes into the install); any kit command that resolves a stock field "
                         "(e.g. `ff9mapkit import`) writes it once")
    try:
        return _index_walkmesh(ev, index, fid)
    except Exception as ex:                               # noqa: BLE001 -- any loader failure refuses the table
        raise TableError(f"R15 walk-in needs field {fid}'s walkmesh: {type(ex).__name__}: {ex}") from ex


def derive(game=None, *, events: "InstallEvents | None" = None) -> dict:
    """Re-derive the whole table from the install, read-only. Raises :class:`TableError` on a generator error --
    R15's walkmesh included (:func:`_r15_walkmesh`)."""
    ev = events or InstallEvents(game)
    index = _existing_field_index(ev.game)
    rows, refused = [], []
    counts = {"fields_scanned": 0, "quad_roots": 0, "census_candidates": 0}
    touched = []
    for fid in _field_ids():
        us = ev.eb(fid, "us")
        if not us:
            continue
        try:
            EbScript.from_bytes(us)
        except Exception:
            continue
        counts["fields_scanned"] += 1
        verdicts = P.analyze_regions(P.FieldModel.from_bytes(us, fid))
        if not any(v.candidate for v in verdicts):
            counts["quad_roots"] += len(verdicts)
            continue
        by_lang = {lang: ev.eb(fid, lang) for lang in LANGS}
        c, r, x, q = derive_field(fid, by_lang, walkmesh=lambda fid=fid: _r15_walkmesh(ev, index, fid),
                                  r16=R16_ENFORCED)
        counts["census_candidates"] += c
        counts["quad_roots"] += q
        rows += r
        refused += x
        if r or x:
            touched.append(fid)
    sha1 = []
    for fid in sorted(touched):
        ent = {"field": fid}
        for lang in LANGS:
            b = ev.eb(fid, lang)
            ent[lang] = hashlib.sha1(b).hexdigest() if b else None
        sha1.append(ent)
    return assemble(rows, refused, counts, sha1)


# ================================================================================================ rendering
def render_json(obj: dict) -> str:
    return json.dumps(obj, indent=1, ensure_ascii=True) + "\n"


def load() -> dict:
    """The committed table, parsed (package data: works from a wheel; reads only)."""
    try:
        from importlib.resources import files
        text = files("ff9mapkit").joinpath("data/guest_traversal.json").read_text(encoding="utf-8")
    except (ImportError, FileNotFoundError, OSError):
        text = JSON_PATH.read_text(encoding="utf-8")
    return json.loads(text)


def _x8(v) -> str:
    return "0x%08Xu" % _crc_int(v)


def _cs_row(r, start) -> str:
    return f"new GuestLocalRow({r['field']}, {r['entry']}, {KIND_CODES[r['kind']]}, {start}, {len(r['funcs'])})"


def _cs_func(f) -> str:
    return (f"new GuestLocalFunc({ROLE_CODES[f['role']]}, {f['entry']}, {f['tag']}, {f['uid']}, {f['len']}, "
            f"{_x8(f['crc'])})")


_CS_HEADER = (
    "// <auto-generated/>",
    "// [ff9mapkit netsync s156] THE GUEST TRAVERSAL TABLE -- generated data only. DO NOT EDIT BY HAND.",
    "// JSON twin: ff9mapkit/ff9mapkit/data/guest_traversal.json, pinned to this file row for row by",
    "// ff9mapkit/tests/test_guest_traversal_table.py (a generated file is only ever replaced WHOLE).",
    "// Regenerate (reads YOUR FF9 install, read-only):",
    "//   py -m ff9mapkit.guest_traversal --write --cs <Memoria>/Assembly-CSharp/Memoria/Netsync/NetSyncGuestLocalTable.cs",
    "// PROVENANCE: field ids, entry and tag indices, byte lengths and CRC-32 digests of stock .eb functions of 8 bytes",
    "// or more -- no game bytes (ff9mapkit/docs/PROVENANCE.md). CRC-32 is a bijection only on inputs of 4 bytes or",
    "// fewer, so no digest here can be inverted to its function.",
    "// SLICE: start = 2 + fpos of the FIRST func-table row whose tag matches (EventEngine.GetIP); end = the next body",
    "// in (fpos, table index) order -- a tie goes to the later-listed row -- never past the entry; a start past the",
    "// entry has length 0; a table that does not fit its entry, or no matching tag, is absent.",
    "// CRC: Unity.IO.Compression.Crc32Helper.UpdateCrc32(0u, ...) == Python zlib.crc32. A function matches only when",
    "// its length agrees first and then its CRC. TableCrc: CRC-32 over each row as <HBBB (field, entry, kind, count)",
    "// then its functions as <BBHBHI (role, entry, tag, uid, length, crc), little-endian, table order.",
    "// The row and function structs (GuestLocalRow, GuestLocalFunc) are hand-written in NetSyncGuestLocal.cs.",
)


def _int_list(vals, per=16, indent="            ") -> list:
    lines = []
    vals = list(vals)
    for i in range(0, len(vals), per):
        chunk = ", ".join(str(v) for v in vals[i:i + per])
        lines.append(indent + chunk + ("," if i + per < len(vals) else ""))
    return lines


def render_cs(obj: dict) -> str:
    """The generated ``NetSyncGuestLocalTable.cs`` -- ASCII, CRLF, no BOM; a pure function of the JSON."""
    rows = obj["rows"]
    st = obj["selftest"]
    names = [b["name"] for b in st["blobs"]]
    bix = {n: i for i, n in enumerate(names)}
    L = list(_CS_HEADER)
    L += ["using System;", "", "namespace Memoria.Netsync", "{",
          "    internal static class NetSyncGuestLocalTable", "    {",
          f"        internal const Int32 Schema = {obj['schema']};",
          f"        internal const Int32 RowCount = {len(rows)};",
          f"        internal const Int32 FuncCount = {sum(len(r['funcs']) for r in rows)};",
          f"        internal const UInt32 TableCrc = {_x8(obj['table_crc'])};",
          "",
          "        // (field, entry, kind 1 ladder / 2 jump / 3 carry, first function, function count), ascending by (field, entry)",
          "        internal static readonly GuestLocalRow[] Rows =", "        {"]
    start = 0
    for i, r in enumerate(rows):
        sep = "," if i + 1 < len(rows) else ""
        L.append(f"            {_cs_row(r, start)}{sep}   // {r['field']}:{r['entry']} {r['kind']} {r.get('evt', '')}".rstrip())
        start += len(r["funcs"])
    L += ["        };", "",
          "        // (role 0 region / 1 ctrl / 2 fixed_ctrl / 3 seq, entry, tag, dispatch uid, length, crc), in row order",
          "        internal static readonly GuestLocalFunc[] Funcs =", "        {"]
    total = sum(len(r["funcs"]) for r in rows)
    k = 0
    for r in rows:
        for j, f in enumerate(r["funcs"]):
            k += 1
            sep = "," if k < total else ""
            note = f"   // {r['field']}:{r['entry']}" if j == 0 else ""
            L.append(f"            {_cs_func(f)}{sep}{note}")
    L += ["        };", ""]
    oc = obj["op_classes"]
    L += ["        // trip-wire opcode classes (pressclosure's non-NEUTRAL opcode buckets): OpClass[op] indexes OpClassNames",
          "        internal static readonly String[] OpClassNames =", "        {"]
    L += _int_list(["null" if n is None else f'"{n}"' for n in oc["names"]], per=9)
    L += ["        };",
          f"        internal static readonly Byte[] OpClass =   // exactly {len(oc['table'])} entries, index = opcode 0x000..0x{len(oc['table']) - 1:03X}",
          "        {"]
    L += _int_list(oc["table"], per=16)
    L += ["        };", "",
          "        // the shared selftest vectors (the JSON's \"selftest\"; the kit's Python test runs the same ones)",
          "        internal static readonly String[] CrcText = { " + ", ".join(json.dumps(c["text"]) for c in st["crc"]) + " };",
          "        internal static readonly UInt32[] CrcWant = { " + ", ".join(_x8(c["crc"]) for c in st["crc"]) + " };",
          "        internal static readonly String[] BlobNames = { " + ", ".join(f'"{n}"' for n in names) + " };",
          "        internal static readonly Byte[][] Blobs =", "        {"]
    for i, b in enumerate(st["blobs"]):
        raw = bytes.fromhex(b["hex"])
        body = ", ".join("0x%02X" % x for x in raw)
        sep = "," if i + 1 < len(st["blobs"]) else ""
        L.append(f"            new Byte[] {{ {body} }}{sep}   // {b['name']}" if body else
                 f"            new Byte[] {{ }}{sep}   // {b['name']}")
    L += ["        };",
          "        // per case: blob, tag, start, len (-1, -1 = absent)",
          "        internal static readonly Int32[] SliceCases =", "        {"]
    sc = st["slice"]
    for i, c in enumerate(sc):
        sep = "," if i + 1 < len(sc) else ""
        L.append(f"            {bix[c['blob']]}, {c['tag']}, {c['start']}, {c['len']}{sep}   // slice.{c['blob']}.{c['tag']}")
    L += ["        };",
          "        internal static readonly UInt32[] SliceCrc = { " + ", ".join(_x8(c["crc"] or 0) for c in sc) + " };",
          "        // per case: blob, tag, at",
          "        internal static readonly Int32[] FlipCases = { "
          + ", ".join(f"{bix[c['blob']]}, {c['tag']}, {c['at']}" for c in st["flip"]) + " };",
          "        internal static readonly UInt32[] FlipCrc = { " + ", ".join(_x8(c["crc"]) for c in st["flip"]) + " };",
          "        // per case: blob, tag, wantLen, ok (1|0)",
          "        internal static readonly Int32[] MatchCases = { "
          + ", ".join(f"{bix[c['blob']]}, {c['tag']}, {c['len']}, {1 if c['ok'] else 0}" for c in st["match"]) + " };",
          "        internal static readonly UInt32[] MatchCrc = { " + ", ".join(_x8(c["crc"]) for c in st["match"]) + " };",
          "        internal static readonly String[] ToyNames = { " + ", ".join(f'"{t["name"]}"' for t in st["toy"]) + " };",
          "        internal static readonly GuestLocalRow[][] ToyRows =", "        {"]
    toys = st["toy"]
    for i, t in enumerate(toys):
        s, parts = 0, []
        for r in t["rows"]:
            parts.append(_cs_row(r, s))
            s += len(r["funcs"])
        L.append("            new GuestLocalRow[] { " + ", ".join(parts) + " }" + ("," if i + 1 < len(toys) else ""))
    L += ["        };", "        internal static readonly GuestLocalFunc[][] ToyFuncs =", "        {"]
    for i, t in enumerate(toys):
        L.append("            new GuestLocalFunc[]")
        L.append("            {")
        fl = [f for r in t["rows"] for f in r["funcs"]]
        for j, f in enumerate(fl):
            L.append(f"                {_cs_func(f)}" + ("," if j + 1 < len(fl) else ""))
        L.append("            }" + ("," if i + 1 < len(toys) else ""))
    L += ["        };",
          "        internal static readonly UInt32[] ToyTableCrc = { " + ", ".join(_x8(t["table_crc"]) for t in toys) + " };",
          "    }", "}"]
    text = "\r\n".join(L) + "\r\n"
    text.encode("ascii")                                 # ASCII only: a non-ASCII byte is a generator bug
    return text


# ================================================================================================ the far-tread report
def _player_walkable(t) -> bool:
    return bool((t.tri_flags & 1) and not ((t.tri_flags >> 8) & 0x80))


def _components(wm, disabled=frozenset()) -> dict:
    """tri -> player-walkable component index (walkmesh_pass.py's rule: active and not CPC-restricted), with the
    ``disabled`` tris (Main_Init's constant disables) counted not walkable."""
    from collections import deque

    def ok(t):
        return t not in disabled and _player_walkable(wm.tris[t])
    comp_of, ci = {}, 0
    for s0 in range(len(wm.tris)):
        if s0 in comp_of:
            continue
        q = deque([s0])
        while q:
            t = q.popleft()
            if t in comp_of:
                continue
            comp_of[t] = ci
            if not ok(t):
                continue
            for n in wm.tris[t].nbr:
                if 0 <= n < len(wm.tris) and n not in comp_of and ok(n):
                    q.append(n)
        ci += 1
    return comp_of


def _effect_classes(v: P.PressVerdict) -> list:
    S = set(v.buckets)
    out = []
    for name, keys in (("exit", {"exit"}), ("battle", {"battle"}), ("window", {"window"}),
                       ("GLOB write", {"glob_write", "scenario_write", "entrance_write", "exit_glob"}),
                       ("item", {"item_party", "party_add"})):
        if S & keys:
            out.append(name)
    return out


def _study_verdicts() -> "dict | None":
    tsv = Path(__file__).resolve().parents[2] / "studies" / "field-coop" / "guest-traversal" / "guest_local_candidates.tsv"
    if not tsv.is_file():
        return None
    out = {}
    lines = tsv.read_text(encoding="utf-8").splitlines()
    head = lines[0].split("\t")
    for ln in lines[1:]:
        c = dict(zip(head, ln.split("\t")))
        if c.get("tag") == "3":
            out[(int(c["field_id"]), int(c["entry"]))] = c.get("walkmesh", "")
    return out


def _existing_field_index(game: Path) -> "dict | None":
    """The install's field index (folder -> bundle) when it ALREADY exists and PARSES as an object, else None -- read
    once, read-only. A missing, empty, truncated or non-object index reads as absent: it never rebuilds or writes
    (``extract.build_field_index`` would rescan every bundle and rewrite it inside the install)."""
    from . import extract
    try:
        index = json.loads((Path(game) / "StreamingAssets" / extract.INDEX_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return index if isinstance(index, dict) else None


def _index_walkmesh(ev, index: dict, fid: int):
    """A stock field's walkmesh through an ALREADY-parsed field index: its folder's bundle loaded read-only by name
    (``extract.find_field``'s explicit-bundle branch), so the lookup can never reach ``resolve_field`` (which builds a
    missing index). FileNotFoundError when the index does not list the field or the bundle has no ``.bgi``."""
    from . import extract
    from .scene import bgi
    folder = extract.ID_TO_FBG.get(int(fid))
    bundle = index.get(folder) if folder else None
    if not folder or not isinstance(bundle, str) or not bundle:
        raise FileNotFoundError(f"field {fid} is not in the field index")
    with extract.env_lock:
        _path, folder, roles, env = extract.find_field(folder, game=ev.game, bundle=bundle)
        if "bgi" not in roles:
            raise FileNotFoundError(f"field {fid} ({folder}) has no .bgi walkmesh in its bundle")
        data = extract._raw_bytes(env.container[roles["bgi"]].read())
    if not data:
        raise FileNotFoundError(f"field {fid} ({folder}): the .bgi walkmesh read back empty")
    return bgi.BgiWalkmesh.from_bytes(data)


def _comps_text(comps) -> str:
    return "/".join(str(c) for c in sorted(comps)) if comps else "-"


def far_tread_report(game=None, obj: "dict | None" = None, *, events: "InstallEvents | None" = None) -> str:
    """R15's inputs, field by field (INFORMATIONAL: the gate is R15 in :func:`derive_field`): for every shipped row
    whose census walkmesh verdict is LINKS-COMPONENTS, every waived row (the JSON's ``waivers``, THE JP WAIVER) and
    every row R15 refused, the field's ARRIVAL components, each row's landing and NEW components, and the field's
    walk-ins -- tag-2 (tread) regions and bump objects -- with the effect classes and tier of their closures, whether
    the hidden-item exemption holds or the closure cannot be judged whole, and the components they touch -- what a
    guest who climbs onto newly reachable ground could walk into on its own copy. Components are named only
    when the field index ALREADY exists and parses (:func:`_existing_field_index`); this report never builds it, and
    its walkmesh loads go through the parsed index, never ``resolve_field``."""
    from .extract import ID_TO_EVT
    obj = obj or load()
    ev = events or InstallEvents(game)
    verdicts = _study_verdicts()
    index = _existing_field_index(ev.game)
    index_built = index is not None
    L = ["# far-component tread report -- guest traversal (s156): the R15 walk-in gate's inputs, INFORMATIONAL",
         "# Generated by `py -m ff9mapkit.guest_traversal --write --report <this file>` (read-only against the install).",
         "# For each shipped row whose census walkmesh verdict (guest_local_candidates.tsv) is LINKS-COMPONENTS, and each",
         "# row R15 refused: the field's ARRIVAL components (where its player entries' tag 0 leaves the player with",
         "# walk control, the union over every entrance branch), each row's landing and NEW (landing, not arrival)",
         "# components, and the field's walk-ins -- tag-2 tread regions and tag-2 bump objects -- with the effect classes",
         "# of their closures (exit / battle / window / GLOB write / item), their tier, `exempt` when every effect op is",
         "# dominated by a user-control test and a constant Confirm / Special / Select poll proved together, `incomplete`",
         "# when the closure cannot be judged whole, and the walkable components they touch. R15 refuses a row whose NEW",
         "# ground carries an incomplete walk-in or a STATEFUL one that is not exempt (derive_field; nothing gates a tag-2",
         "# tread or bump for a spectator). Ids and classes only -- no game bytes. The walk-ins below are the US script's.",
         "# THE JP WAIVER: a row whose only refusal is R15 in Japanese, exempt there once the key mask also strips Cancel",
         "# (where ETb.ProcessJapaneseLayout puts a Japanese guest's Confirm), ships -- WAIVED below, until the engine's",
         "# NetSyncField.ControlOnScriptKeys strips the JP-mapped bits.",
         ""]
    if verdicts is None:
        L.append("# walkmesh verdicts: unknown (the study's guest_local_candidates.tsv is not in this tree) -- every row listed")
    if not index_built:
        L.append(f"# {UNKNOWN_COMPONENT}")
    waived = {(w["field"], w["entry"]): w["waiver"] for w in obj.get("waivers", [])}
    L.append(f"# {len(waived)} waived rows: " + (" ".join(f"{f}:{e}" for (f, e) in sorted(waived)) or "-"))
    by_field = defaultdict(list)
    for r in obj["rows"]:
        wv = None if verdicts is None else verdicts.get((r["field"], r["entry"]))
        if verdicts is None or wv == "LINKS-COMPONENTS" or (r["field"], r["entry"]) in waived:
            by_field[r["field"]].append(r)
    for r in obj.get("refused", []):
        if r["refusal"].startswith("R15 "):
            by_field[r["field"]].append(r)
    L.append(f"# {sum(len(v) for v in by_field.values())} rows in {len(by_field)} fields")
    for fid in sorted(by_field):
        data = ev.eb(fid, "us")
        fld = P.FieldModel.from_bytes(data, fid)
        ground, walks = None, None
        if index_built:
            try:
                ground = field_ground(fld, _index_walkmesh(ev, index, fid))
                walks = walk_ins(fld, ground)
            except Exception as ex:                       # noqa: BLE001 -- informational; say why and go on
                L.append(f"# field {fid}: walkmesh unreadable ({type(ex).__name__})")
        treads = tread_regions(fld)

        def comp(polys):
            if ground is None:
                return UNKNOWN_COMPONENT if not index_built else "component: unknown (no walkmesh)"
            if polys is None:
                return "component: unknown (a computed SetRegion)"
            return "component: " + (_comps_text(ground.touched_all(polys)) if polys else "off-mesh")
        L.append("")
        L.append(f"field {fid} {ID_TO_EVT.get(fid, '')}".rstrip())
        arrival = None
        if ground is not None:
            arrival = field_arrival(fld, ground)
            L.append(f"  arrival components: {_comps_text(arrival)}  ({len(spawn_points(fld))} spawn points, "
                     f"{len(ground.disabled)} tris Main_Init disables)")
        for r in sorted(by_field[fid], key=lambda r: r["entry"]):
            line = f"  row {fid}:{r['entry']} {r['kind']}  quad {comp(region_polys(fld, r['entry']))}"
            if ground is not None:
                w = walkin(fld, P.analyze_root(fld, r["entry"], 3), ground, arrival, walks)
                line += f"  landing {_comps_text(w['land'])}  new {_comps_text(w['new'])}"
                if w["wild"]:
                    line += f"  (any walkable component: {w['wild'][0]})"
            L.append(line)
            if "refusal" in r:
                L.append(f"    REFUSED {r['refusal']}")
            if (fid, r["entry"]) in waived:
                L.append(f"    WAIVED {waived[(fid, r['entry'])]}")
        if not treads:
            L.append("  (no tag-2 tread regions)")

        def judged(tv, ex, gap):
            if gap:
                return f"  incomplete ({gap})"
            return "  exempt" if ex and tv.tier in WALKIN_TIERS else ""
        resolved = {(k, ei): (comps, why, ex, gap) for (k, ei, comps, why, _tv, ex, gap) in (walks or ())}
        for (ei, polys, tv) in treads:
            eff = _effect_classes(tv)
            got = resolved.get(("walk-in", ei))
            where = comp(polys) if got is None or got[1] is None else f"component: any ({got[1]})"
            ex = judged(tv, got[2], got[3]) if got else ""
            L.append(f"  tread {fid}:{ei}  effects: {', '.join(eff) if eff else '-'}  tier {tv.tier}{ex}  {where}")
        for (k, ei, comps, why, tv, ex, gap) in (walks or ()):
            if k != "bump" or (tv.tier not in WALKIN_TIERS and not gap):
                continue
            eff = _effect_classes(tv)
            where = f"component: any ({why})" if comps is None else "component: " + (_comps_text(comps) or "off-mesh")
            L.append(f"  bump {fid}:{ei}  effects: {', '.join(eff) if eff else '-'}  tier {tv.tier}"
                     f"{judged(tv, ex, gap)}  {where}")
    return "\n".join(L) + "\n"


# ================================================================================================ check + CLI
def _row_key(r):
    return f"{r['field']}:{r['entry']}"


def diff_tables(old: dict, new: dict) -> list:
    """Human-readable differences between two table objects (rows, refusals, counts, crc, sha1)."""
    out = []
    for k in ("counts", "table_crc", "rule", "langs", "op_classes", "selftest", "eb_sha1"):
        if old.get(k) != new.get(k):
            out.append(f"{k}: {json.dumps(old.get(k))[:200]} -> {json.dumps(new.get(k))[:200]}")
    for part in ("rows", "refused", "waivers"):
        a = {_row_key(r): r for r in old.get(part, [])}
        b = {_row_key(r): r for r in new.get(part, [])}
        for key in sorted(set(a) | set(b), key=lambda s: tuple(int(x) for x in s.split(":"))):
            if key not in b:
                out.append(f"{part} {key}: gone")
            elif key not in a:
                out.append(f"{part} {key}: new")
            elif a[key] != b[key]:
                out.append(f"{part} {key}: {json.dumps(a[key])[:240]} -> {json.dumps(b[key])[:240]}")
    return out


def check(game=None, *, events: "InstallEvents | None" = None) -> "tuple[bool, str]":
    """Re-derive from the install and compare with the committed JSON: ``(True, 'OK ...')`` or ``(False, diff)``."""
    new = derive(game, events=events)
    old_text = JSON_PATH.read_text(encoding="utf-8") if JSON_PATH.is_file() else ""
    if render_json(new) == old_text.replace("\r\n", "\n"):
        return True, (f"OK: {new['counts']['rows']} rows / {new['counts']['funcs']} functions / "
                      f"{new['counts']['fields']} fields regenerate exactly ({' '.join(LANGS)}), table crc "
                      f"{new['table_crc']}")
    old = json.loads(old_text) if old_text else {}
    lines = diff_tables(old, new) or ["(the JSON text differs only in formatting)"]
    return False, "DIFF against the committed table:\n  " + "\n  ".join(lines)


def _compare_file(path: Path, want: str, what: str, crlf: bool) -> "tuple[bool, str]":
    if not path.is_file():
        return False, f"{what}: {path} does not exist"
    have = path.read_bytes().decode("ascii", "replace")
    if have == want:
        return True, f"{what}: {path} is identical"
    d = difflib.unified_diff(have.splitlines(), want.splitlines(), str(path), "regenerated", lineterm="", n=1)
    lines = list(d)[:40]
    eol = " (line endings differ)" if have.replace("\r\n", "\n") == want.replace("\r\n", "\n") else ""
    return False, f"{what}: {path} differs{eol}\n  " + "\n  ".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="py -m ff9mapkit.guest_traversal", description=__doc__.split("\n\n")[0])
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="re-derive and diff (the default)")
    mode.add_argument("--write", action="store_true", help="rewrite the committed JSON (and --cs / --report)")
    ap.add_argument("--cs", type=Path, help="the engine's Memoria/Netsync/NetSyncGuestLocalTable.cs")
    ap.add_argument("--report", type=Path, help="the far-component tread report (informational)")
    ap.add_argument("--game", help="the FF9 install (default: the kit's usual resolution)")
    a = ap.parse_args(argv)
    try:
        ev = InstallEvents(a.game)
        new = derive(events=ev)
    except (TableError, FileNotFoundError, config.ConfigError, RuntimeError) as ex:
        print(f"guest_traversal: {type(ex).__name__}: {ex}", file=sys.stderr)
        return 2
    ok = True
    if a.write:
        JSON_PATH.write_bytes(render_json(new).encode("ascii"))
        print(f"wrote {JSON_PATH} ({new['counts']['rows']} rows / {new['counts']['funcs']} functions / "
              f"{new['counts']['fields']} fields, {new['counts']['refused']} refused, table crc {new['table_crc']})")
        for r in new["refused"]:
            print(f"  refused {r['field']}:{r['entry']} -- {r['refusal']}")
        if a.cs:
            a.cs.write_bytes(render_cs(new).encode("ascii"))
            print(f"wrote {a.cs}")
        if a.report:
            a.report.write_bytes(far_tread_report(obj=new, events=ev).encode("ascii"))
            print(f"wrote {a.report}")
        return 0
    old_text = JSON_PATH.read_text(encoding="utf-8") if JSON_PATH.is_file() else ""
    if render_json(new) == old_text.replace("\r\n", "\n"):
        print(f"OK: {new['counts']['rows']} rows / {new['counts']['funcs']} functions / {new['counts']['fields']} "
              f"fields regenerate exactly ({' '.join(LANGS)}), table crc {new['table_crc']}")
    else:
        ok = False
        old = json.loads(old_text) if old_text else {}
        print("DIFF against the committed table:\n  " + "\n  ".join(diff_tables(old, new) or ["(formatting only)"]))
    if a.cs:
        good, msg = _compare_file(a.cs, render_cs(new), "C#", True)
        ok &= good
        print(msg)
    if a.report:
        good, msg = _compare_file(a.report, far_tread_report(obj=new, events=ev), "report", False)
        ok &= good
        print(msg)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
