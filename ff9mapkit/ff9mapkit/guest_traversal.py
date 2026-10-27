"""The co-op GUEST TRAVERSAL table (engine patch s156): which stock press interactions a following guest may run
on its own copy of the room -- ladders, jumps, carries -- and the CRC-32 of every function each one runs.

THE GENERATOR. It reads YOUR install's field event scripts READ-ONLY (UnityPy over ``StreamingAssets/p0data*.bin``;
it may read an existing ``.ff9mapkit-events-bundle.txt`` and never writes into the install), classifies every QUAD
press closure with :mod:`ff9mapkit.eb.pressclosure`, keeps the census's LOCO-ONLY player movers, applies the
fail-closed ship filter R1-R13 below, and emits

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
                "255); R13 write (the closure writes a Global or Null var: it may write only Map and Instance vars)",
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
    """The row a verdict would ship in ONE language, with its first R1-R8 / R12 / R13 refusal and its R11 trace (R9
    compares these across languages; the caller picks the final refusal)."""
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


def derive_field(fid: int, by_lang: dict, langs=LANGS):
    """``(candidates, rows, refused, quad_roots)`` for one field: ``by_lang`` maps each language in ``langs`` to its
    ``.eb`` bytes (None = missing). The US (first-listed) language classifies; every other one must agree (R9).
    Install-free: the offline tests feed it kit-assembled synthetic fields."""
    base = langs[0]
    data = by_lang.get(base)
    fld = P.FieldModel.from_bytes(data, fid)
    verdicts = P.analyze_regions(fld)
    others = {}
    rows, refused, cands = [], [], 0
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
                od = _derive_one(ofld, ov)
                if _signature(od) != _signature(mine):
                    diffs.append(f"{lang} differs ({od['tier']}/{od['kind']}, {len(od['funcs'])} functions)")
            if diffs:
                refusal = "R9 language: " + "; ".join(diffs)
        if refusal is None:
            refusal = mine["r11"]
        row = {"field": fid, "entry": v.region, "kind": KIND_MAP[v.kind]}
        if refusal is None:
            from .extract import ID_TO_EVT
            _check_r10(fld.eb, mine["funcs"], f"field {fid} ({base})")
            for lang in langs[1:]:
                _check_r10(others[lang].eb, mine["funcs"], f"field {fid} ({lang})")
            row.update({"evt": ID_TO_EVT.get(fid, ""), "async": mine["async"], "funcs": mine["funcs"],
                        "census_kind": v.kind, "gate": mine["gate"], "player_entries": mine["player_entries"]})
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
    """The JSON object, keys in their fixed order, from the per-field results."""
    rows = sorted(rows, key=lambda r: (r["field"], r["entry"]))
    refused = sorted(refused, key=lambda r: (r["field"], r["entry"]))
    counts = {"fields_scanned": counts_in["fields_scanned"], "quad_roots": counts_in["quad_roots"],
              "census_candidates": counts_in["census_candidates"], "rows": len(rows),
              "funcs": sum(len(r["funcs"]) for r in rows), "fields": len({r["field"] for r in rows}),
              "refused": len(refused)}
    return {"schema": SCHEMA, "generated_from": "install by guest_traversal.py", "regenerate": REGENERATE,
            "langs": list(LANGS), "rule": dict(RULE), "counts": counts, "table_crc": _hex(table_crc(rows)),
            "rows": rows, "refused": refused, "eb_sha1": sha1, "op_classes": build_op_classes(),
            "selftest": build_selftest()}


def derive(game=None, *, events: "InstallEvents | None" = None) -> dict:
    """Re-derive the whole table from the install, read-only. Raises :class:`TableError` on a generator error."""
    ev = events or InstallEvents(game)
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
        c, r, x, q = derive_field(fid, by_lang)
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


def _components(wm) -> dict:
    """tri -> player-walkable component index (walkmesh_pass.py's rule: active and not CPC-restricted)."""
    from collections import deque
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
            if not _player_walkable(wm.tris[t]):
                continue
            for n in wm.tris[t].nbr:
                if 0 <= n < len(wm.tris) and n not in comp_of and _player_walkable(wm.tris[n]):
                    q.append(n)
        ci += 1
    return comp_of


def _zone_points(fld: P.FieldModel, ei: int):
    """The region's static SetRegion quad: its centre then its corners (walkmesh_pass.py's probe points), or None."""
    from .eventscan import _region_points, _zone_quad
    for f in fld.eb.entry(ei).funcs:
        for ins in fld.instrs(ei, f.tag):
            if ins.op == 0x29:
                pts = _region_points(ins)
                if len(pts) >= 3:
                    q = _zone_quad(pts)
                    return [(sum(p[0] for p in q) / len(q), sum(p[1] for p in q) / len(q))] + [tuple(p) for p in q]
    return None


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


def far_tread_report(game=None, obj: "dict | None" = None, *, events: "InstallEvents | None" = None) -> str:
    """INFORMATIONAL (D5; not a gate input): for every shipped row whose census walkmesh verdict is
    LINKS-COMPONENTS, the field's tag-2 (tread) regions and the effect classes their closures carry -- what a guest
    who climbs onto newly reachable ground could walk into on its own copy. A region's walkmesh component is named
    only when the field index ALREADY exists and parses (:func:`_existing_field_index`); this report never builds
    it, and its walkmesh loads go through the parsed index, never ``resolve_field``."""
    obj = obj or load()
    ev = events or InstallEvents(game)
    verdicts = _study_verdicts()
    index = _existing_field_index(ev.game)
    index_built = index is not None
    L = ["# far-component tread report -- guest traversal (s156), INFORMATIONAL, not a gate input",
         "# Generated by `py -m ff9mapkit.guest_traversal --write --report <this file>` (read-only against the install).",
         "# For each shipped row whose census walkmesh verdict (guest_local_candidates.tsv) is LINKS-COMPONENTS: the",
         "# field's tag-2 tread regions and the effect classes of their closures (exit / battle / window / GLOB write /",
         "# item). Field ENCOUNT is skipped only while the guest mirrors the host's story (D5's own_story term), so a",
         "# walk-in on newly reachable ground is the first playtest's question. Ids and classes only -- no game bytes.",
         ""]
    if verdicts is None:
        L.append("# walkmesh verdicts: unknown (the study's guest_local_candidates.tsv is not in this tree) -- every row listed")
    if not index_built:
        L.append(f"# {UNKNOWN_COMPONENT}")
    by_field = defaultdict(list)
    for r in obj["rows"]:
        wv = None if verdicts is None else verdicts.get((r["field"], r["entry"]))
        if verdicts is None or wv == "LINKS-COMPONENTS":
            by_field[r["field"]].append(r)
    L.append(f"# {sum(len(v) for v in by_field.values())} rows in {len(by_field)} fields")
    for fid in sorted(by_field):
        data = ev.eb(fid, "us")
        fld = P.FieldModel.from_bytes(data, fid)
        comp_of, wm = None, None
        if index_built:
            try:
                wm = _index_walkmesh(ev, index, fid)
                comp_of = _components(wm)
            except Exception as ex:                       # noqa: BLE001 -- informational; say why and go on
                L.append(f"# field {fid}: walkmesh unreadable ({type(ex).__name__})")

        def comp(ei):
            if comp_of is None:
                return UNKNOWN_COMPONENT if not index_built else "component: unknown (no walkmesh)"
            pts = _zone_points(fld, ei)
            if pts is None:
                return "component: unknown (no static SetRegion)"
            hits = sorted({comp_of[t] for (x, z) in pts for t in wm.tris_at(x, z) if _player_walkable(wm.tris[t])})
            return "component: " + ("/".join(str(h) for h in hits) if hits else "off-mesh")
        L.append("")
        L.append(f"field {fid} {by_field[fid][0].get('evt', '')}".rstrip())
        for r in by_field[fid]:
            L.append(f"  row {fid}:{r['entry']} {r['kind']}  quad {comp(r['entry'])}")
        treads = []
        for e in fld.eb.entries:
            if e.empty or e.index == 0:
                continue
            kinds = fld.kind.get(e.index, set())
            if kinds & {"region", "region?"} and any(f.tag == 2 for f in e.funcs):
                treads.append(e.index)
        if not treads:
            L.append("  (no tag-2 tread regions)")
        for ei in treads:
            v = P.analyze_root(fld, ei, 2)
            eff = _effect_classes(v)
            L.append(f"  tread {fid}:{ei}  effects: {', '.join(eff) if eff else '-'}  tier {v.tier}  {comp(ei)}")
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
    for part in ("rows", "refused"):
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
