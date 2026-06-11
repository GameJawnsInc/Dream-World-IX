"""Faithful TEXT carry -- ship a donor field's referenced ``.mes`` text VERBATIM + remap the txids.

The object graft (:mod:`content.object`) and player-function graft (:mod:`content.player`) carry a real
field's NPCs/props + their interactions byte-for-byte. But a window those grafted bytes open
(``WindowSync``/``WindowAsync[Ex]``) names a donor ``.mes`` TXID -- and a fork ships its OWN ``.mes`` block
(authored lines from :func:`build.collect_text`, at a high band), so that donor id resolves to nothing: an
EMPTY window. This module closes that last gap: it CARRIES the donor's referenced field text (per language,
verbatim) and REMAPS each grafted window's TXID to a fresh band, so the forked interactions show the real
words. It is the faithful counterpart to ``import --dialogue`` (which appends EDITABLE ``[[npc]]`` stubs the
author re-writes); carry ships the donor strings unchanged.

It is IMPORT-ONLY and OPT-IN (the ``import --carry-text`` flag). It never touches the authored-dialogue path
(:mod:`content.text` / :func:`build.collect_text` stay byte-for-byte; the hut golden is preserved): carried
text is APPENDED after the authored block, in a disjoint txid band.

Engine / format facts this relies on (verified against the real bytes -- see docs/TEXT_CARRY.md):

  * A window's TXID is a 2-BYTE immediate operand (operand 2 for ``WindowSync``/``WindowAsync`` 0x1F/0x20,
    operand 3 for the ``...Ex`` variants 0x95/0x96 -- :data:`dialogue.WINDOW_OPS`). Re-emitting at a band
    >= :data:`CARRY_BASE_TXID` (1000) keeps the new id in 2 bytes -> a SAME-LENGTH in-place patch via
    :func:`content.object._arg_byte_offset` (the exact primitive the slot/uid remap uses). FF9 NEVER computes
    a window txid (census: 0/24166 expression txids), so every one is statically remappable.
  * The carry BAND must clear the base game's real txids (census max = 863, field 1607) AND the fork's own
    authored band (:data:`content.text.DEFAULT_BASE_TXID` = 500). 1000 is the first unconditionally-safe
    floor (no real field uses a txid >= 1000) and still a 2-byte immediate (<= 65535).
  * ``.mes`` text is PER-LANGUAGE (the 7 :data:`config.LANGS`). The carried text is shipped in EVERY language
    the build ships; a per-language entry is carried VERBATIM -- an empty entry stays empty (field 357 txid
    470 is empty in us/uk but populated in fr/gr/it/jp -- a us-fallback would WIPE the French/German text).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from .. import dialogue as _dialogue
from ..config import LANGS
from ..eb import EbScript
from ..eb.disasm import argsize
from . import object as _object

# The carried-text txid band: clear of the base game (max real txid 863) AND the fork's authored 500+ band,
# and still a 2-byte immediate so every window remap is a same-length in-place patch. See the module note.
CARRY_BASE_TXID = 1000


@dataclass(frozen=True)
class CarriedEntry:
    """One donor ``.mes`` entry carried per-language. ``texts[lang]`` is the verbatim string for that
    language (``''`` for an empty/absent donor entry -- carried as-is, never us-filled). ``strt``/``tail``
    are the donor's window-geometry tags, preserved verbatim from the language the scan was keyed on (they
    are language-independent geometry, not text)."""
    donor_txid: int
    new_txid: int
    texts: dict                       # lang -> verbatim text (may be "")
    strt: Optional[str] = None
    tail: Optional[str] = None


# --------------------------------------------------------------- which txids a graft will SHOW ---
def _grafted_object_windows(donor_eb, specs) -> set:
    """Every TXID a CARRIED object's grafted bytes will open. For each spec, the carried funcs are its
    ``carry_tags`` (``None`` = whole entry); we decode the donor entry and collect each window operand's txid
    in the kept funcs. A REFUSED spec (``graft_safety == "refuse"``) carries nothing -> skipped, matching
    :func:`content.object.graft_objects`."""
    eb = donor_eb if isinstance(donor_eb, EbScript) else EbScript.from_bytes(donor_eb)
    out: set = set()
    for s in specs:
        if s.get("graft_safety") == "refuse":
            continue
        slot = int(s["donor_idx"])
        if not 0 <= slot < eb.entry_count:
            continue
        keep = s.get("carry_tags")
        keep = None if keep is None else {int(t) for t in keep}
        e = eb.entry(slot)
        if e.empty:
            continue
        for f in e.funcs:
            if keep is not None and f.tag not in keep:
                continue
            for ins in eb.instrs(f):
                opnd = _dialogue.WINDOW_OPS.get(ins.op)
                if opnd is None:
                    continue
                if opnd < len(ins.arg_is_expr) and ins.arg_is_expr[opnd]:
                    continue                         # computed txid (does not occur in real fields) -- skip
                txid = ins.imm(opnd)
                if txid is not None:
                    out.add(int(txid))
    return out


def _grafted_player_windows(player_specs) -> set:
    """Every TXID a grafted PLAYER function will open. Only ``clean`` and ``text`` player funcs are carried
    (a ``text`` func is graftable once its windows are remapped -- the whole point of carry); we decode each
    grafted body and collect its window txids. Other safety classes are not grafted -> skipped."""
    out: set = set()
    for s in player_specs:
        if s.get("safety") not in ("clean", "text"):
            continue
        body = s.get("body")
        if not body:
            continue
        for ins in _object_iter(body):
            opnd = _dialogue.WINDOW_OPS.get(ins.op)
            if opnd is None:
                continue
            if opnd < len(ins.arg_is_expr) and ins.arg_is_expr[opnd]:
                continue
            txid = ins.imm(opnd)
            if txid is not None:
                out.add(int(txid))
    return out


def _object_iter(body):
    from ..eb.disasm import iter_code
    return iter_code(bytes(body), 0, len(body))


# --------------------------------------------------------------- collect the carry plan ---
def collect_carry(donor_eb, object_specs, player_specs, field, lang_loader) -> list:
    """Build the carry plan: the donor txids the grafts will SHOW, each assigned a fresh band txid and its
    per-language text. ``donor_eb`` is the donor field's ``.eb`` bytes; ``object_specs`` /  ``player_specs``
    are the graft specs (:func:`eventscan.scan_objects_verbatim` / :func:`scan_player_funcs`). ``field`` is
    the donor field id (for the text loader). ``lang_loader(txids, lang) -> {txid: MesEntry}`` reads the
    donor's per-language ``.mes`` (injected so this stays install-free + testable -- in the kit it is
    :func:`_field_text_loader`).

    Returns an ordered ``list[CarriedEntry]`` (sorted by donor txid for determinism), one per distinct
    referenced txid. ``new_txid`` is :data:`CARRY_BASE_TXID` + i. An empty plan (no grafted windows) returns
    ``[]`` -- the build then carries no text (byte-identical to no-carry).
    """
    wanted = _grafted_object_windows(donor_eb, object_specs) | _grafted_player_windows(player_specs)
    if not wanted:
        return []
    donor_txids = sorted(wanted)

    # per-language text. The geometry tags (strt/tail) are read once from the primary language (us); they
    # are language-independent window geometry. Each language's TEXT is carried independently (verbatim).
    per_lang: dict = {}
    for lang in LANGS:
        per_lang[lang] = lang_loader(donor_txids, lang) or {}
    primary = per_lang.get(LANGS[0], {})

    plan = []
    for i, dt in enumerate(donor_txids):
        texts = {}
        for lang in LANGS:
            e = per_lang[lang].get(dt)
            texts[lang] = e.text if (e is not None and e.text is not None) else ""
        pe = primary.get(dt)
        plan.append(CarriedEntry(donor_txid=dt, new_txid=CARRY_BASE_TXID + i, texts=texts,
                                 strt=(pe.strt if pe else None), tail=(pe.tail if pe else None)))
    return plan


def _field_text_loader(field, game=None):
    """The kit's real per-language loader for :func:`collect_carry`: reads the donor field's ``<zone>.mes``
    block from the install (the authoritative ``eventIDToMESID`` zone), picking the requested language. A
    thin wrapper over :func:`dialogue._load_field_text` keyed on the field's text zone -- so the SAME block
    selection :func:`dialogue.read_field_dialogue` proved is used (the want-txids coverage + language score
    pick the right per-language copy)."""
    from .._fieldtext import EVENT_ID_TO_MES
    zone_id = EVENT_ID_TO_MES.get(int(field))

    def _load(txids, lang):
        return _dialogue._load_field_text(txids, lang, game=game, zone_id=zone_id)
    return _load


# --------------------------------------------------------------- remap the grafted windows ---
def _remap_windows_in_entry(eb_bytes, entry_index, txid_map, carry_tags=None) -> bytes:
    """Same-length, in-place remap of every window TXID a grafted entry's CARRIED funcs reference, donor ->
    carried band, via the decoder-derived 2-byte offset (:func:`content.object._arg_byte_offset`). Only the
    ``carry_tags`` funcs are patched (``None`` = whole entry), mirroring what was actually grafted. A txid
    not in ``txid_map`` (e.g. a system window pointing at a base id we chose not to carry) is left
    untouched. The patch is byte-for-byte length-preserving (2-byte immediate -> 2-byte immediate)."""
    eb = EbScript.from_bytes(eb_bytes)
    b = bytearray(eb_bytes)
    keep = None if carry_tags is None else {int(t) for t in carry_tags}
    for f in eb.entry(entry_index).funcs:
        if keep is not None and f.tag not in keep:
            continue
        for ins in eb.instrs(f):
            opnd = _dialogue.WINDOW_OPS.get(ins.op)
            if opnd is None:
                continue
            if opnd < len(ins.arg_is_expr) and ins.arg_is_expr[opnd]:
                continue
            txid = ins.imm(opnd)
            if txid is None or int(txid) not in txid_map:
                continue
            new = txid_map[int(txid)]
            bo = _object._arg_byte_offset(ins, opnd)
            if bo is None or argsize(ins.op, opnd) != 2:
                continue                             # only same-length 2-byte window operands are patchable
            b[ins.off + bo] = new & 0xFF
            b[ins.off + bo + 1] = (new >> 8) & 0xFF
    return bytes(b)


def remap_object_windows(eb_bytes, object_specs, slot_map, txid_map) -> bytes:
    """Patch each carried OBJECT's grafted entry (now at its fork slot ``slot_map[donor_idx]``) so its
    window TXIDs point at the carried band. ``slot_map`` is the donor_idx -> fork-slot map the object graft
    built; ``txid_map`` is donor_txid -> carried_txid. A refused/un-slotted spec is skipped."""
    data = eb_bytes
    for s in object_specs:
        if s.get("graft_safety") == "refuse":
            continue
        slot = slot_map.get(int(s["donor_idx"]))
        if slot is None:
            continue
        data = _remap_windows_in_entry(data, slot, txid_map, s.get("carry_tags"))
    return data


def remap_player_func_windows(eb_bytes, player_entry, tag_map, txid_map) -> bytes:
    """Patch each grafted PLAYER function (now at its fork tag ``tag_map[donor_tag]`` on the player entry) so
    its window TXIDs point at the carried band. ``tag_map`` is donor_tag -> fork-tag; only the grafted tags
    are touched. Same same-length 2-byte patch as the object path."""
    eb = EbScript.from_bytes(eb_bytes)
    fork_tags = set(tag_map.values())
    data = eb_bytes
    for f in eb.entry(player_entry).funcs:
        if f.tag not in fork_tags:
            continue
        data = _remap_windows_in_entry(data, player_entry, txid_map, [f.tag])
    return data


# --------------------------------------------------------------- emit the carried .mes ---
def _mes_entry_verbatim(entry: CarriedEntry, lang: str) -> str:
    """One carried ``.mes`` entry for ``lang``, re-emitted FAITHFULLY at its new txid: the donor's exact STRT
    (window geometry, kept verbatim) + its TAIL only if the donor had one + the language's verbatim text. NOT
    :func:`content.text.mes_entry` (which forces a default STRT/TAIL) -- a carried entry must preserve the
    donor's own geometry tags, else the window resizes."""
    strt = entry.strt if entry.strt is not None else "10,1"
    tail = f"[TAIL={entry.tail}]" if entry.tail else ""
    return f"_[TXID={entry.new_txid}][STRT={strt}]{tail}{entry.texts.get(lang, '')}[ENDN]"


def carried_mes_body(plan, lang: str) -> str:
    """The carried ``.mes`` block for one language: every :class:`CarriedEntry` re-emitted at its new txid,
    verbatim. Each entry carries its own ``[TXID=]`` re-index (so it is position-independent), letting this
    block be APPENDED after the fork's authored block without disturbing it. Empty plan -> ``''``."""
    if not plan:
        return ""
    return "\n".join(_mes_entry_verbatim(e, lang) for e in plan) + "\n"


# --------------------------------------------------------------- the sidecar (import write / build read) ---
SIDECAR_VERSION = 1


def plan_to_sidecar(plan, *, field=None) -> dict:
    """Serialise the carry plan to a JSON-able dict (the ``<name>.carrytext.json`` sidecar). One record per
    carried entry: the donor/new txids, the donor geometry tags, and the per-language verbatim text. The
    strings are SE-derived, so the sidecar is gitignored (mirrors ``.object*.bin`` / ``.dialogue.json``)."""
    return {
        "version": SIDECAR_VERSION,
        "field": (int(field) if field is not None else None),
        "base_txid": CARRY_BASE_TXID,
        "langs": list(LANGS),
        "entries": [{"donor_txid": e.donor_txid, "new_txid": e.new_txid,
                     "strt": e.strt, "tail": e.tail, "texts": dict(e.texts)} for e in plan],
    }


def write_sidecar(path, plan, *, field=None) -> None:
    """Write the carry sidecar to ``path`` (UTF-8 JSON). No-op file is still written for an empty plan so the
    build's ``[carry_text] bin`` ref always resolves."""
    from pathlib import Path
    Path(path).write_text(json.dumps(plan_to_sidecar(plan, field=field), ensure_ascii=False, indent=1),
                          encoding="utf-8")


def load_sidecar(path) -> list:
    """Read a ``<name>.carrytext.json`` sidecar back into an ordered ``list[CarriedEntry]`` (the build's
    consume side). Each entry's ``texts`` is filled for every shipped language (missing -> ``''``, so an
    absent language never errors -- it ships an empty window, harmless)."""
    from pathlib import Path
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    out = []
    for rec in raw.get("entries", []):
        texts = {lang: (rec.get("texts", {}).get(lang) or "") for lang in LANGS}
        out.append(CarriedEntry(donor_txid=int(rec["donor_txid"]), new_txid=int(rec["new_txid"]),
                                texts=texts, strt=rec.get("strt"), tail=rec.get("tail")))
    return out
