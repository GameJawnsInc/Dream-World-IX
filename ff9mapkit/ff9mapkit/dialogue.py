"""The dialogue spine -- the READ side of FF9 field text, plus a UI-agnostic view of a field's lines.

The kit has always been able to *write* dialogue (an NPC line / event message / choice menu / cutscene
``say`` becomes a ``.mes`` entry + a ``WindowSync`` opcode, via :mod:`ff9mapkit.content.text` and
:func:`ff9mapkit.build.collect_text`). It could never *read* it back. This module closes the loop and is
the core every dialogue frontend (the CLI ``dialogue`` commands, the standalone editor, a Campaign-Editor
tab) sits on -- so the data logic is written and tested once, independent of any UI. It is **read-only**
authoring infrastructure: it never changes the proven write path (:func:`ff9mapkit.content.text.build_mes`
/ ``wrap_text`` stay byte-for-byte identical, so the golden ``.eb`` is untouched).

It answers three questions:

  * ``parse_mes(body)``            -> WHAT text does a ``.mes`` block hold? (txid -> :class:`MesEntry`)
  * ``scan_dialogue(eb)``          -> WHICH lines does a field's ``.eb`` SHOW, and at what txid?
  * ``read_local_dialogue`` /      -> JOIN the two: "this NPC says <text>" for a built mod folder, or
    ``read_field_dialogue``           for a real FF9 field read live from the install.

Plus :func:`project_dialogue` (the authored lines of a ``field.toml``, for the viewer/editor) and the
formatting helpers (:func:`wrap_preview` / :func:`overflow` / :func:`format_lines`) that wrap the existing
:mod:`content.text` wrapper so simple dialogue stays well-formatted.

Engine facts this relies on (verified against Memoria source + the kit's own data):
  * ``.mes`` grammar: ``_[TXID=n][STRT=a,b][TAIL=code]<text>[ENDN]`` -- the exact inverse of
    :func:`content.text.mes_entry`; ``<text>`` may span ``\\n`` (wrapped) and hold ``[PAGE]``.
  * a field's text file is ``<fieldZoneId>.mes`` (``FF9TextTool.GetFieldTextFileName`` == the zone id as a
    string); the zone id is the DictionaryPatch FieldScene 6th token (1073 for the hut; the field's own
    text-zone id for a real field). Battle text uses the same ``<id>.mes`` convention in resources.assets.
  * dialogue window opcodes carry the txid as an immediate operand: ``WindowSync``/``WindowAsync``
    (0x1F/0x20) at operand 2, the ``...Ex`` variants (0x95/0x96) at operand 3.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field as _dc_field
from pathlib import Path
from typing import Optional

from .content import text as _text
from .eb import EbScript

# dialogue window opcodes -> the operand index that carries the text id (eb/opcodes.py + _optables.py).
WINDOW_OPS = {0x1F: 2, 0x20: 2, 0x95: 3, 0x96: 3}
SET_MODEL = 0x2F                  # SetModel(model:u16, animset:u8) -- the NPC's model lives in operand 0
TALK_TAG = 3                      # an NPC's _SpeakBTN func tag (the "press to talk" handler)


# --------------------------------------------------------------------------- data ---
@dataclass(frozen=True)
class MesEntry:
    """One parsed ``.mes`` entry. ``text`` is verbatim (tags intact, may hold ``\\n``/``[PAGE]``)."""
    txid: int
    text: str
    tail: Optional[str] = None
    strt: Optional[str] = None


@dataclass(frozen=True)
class DialogueCall:
    """One dialogue-window call decoded from a field's ``.eb``: which entry/func shows which txid (and,
    best-effort for a kit-built NPC, the model + floor position the entry creates itself at)."""
    entry_idx: int
    func_tag: int
    txid: Optional[int]          # None when the text id is an expression (computed at runtime)
    x: Optional[int] = None
    z: Optional[int] = None
    model: Optional[int] = None
    op: int = 0x1F
    flags: Optional[int] = None  # the window flags operand; the 0x80 bit marks a real dialogue box

    @property
    def kind(self) -> str:
        # an NPC's talk handler is func tag 3; everything else (Init / region / code entry) is "scene"
        return "npc" if self.func_tag == TALK_TAG else "scene"

    @property
    def is_system(self) -> bool:
        # real dialogue carries the 0x80 (text-box) flag; flags==0 windows are system/notification overlays
        # (the field's error guard, the "Received item!" popup) -- not conversation.
        return self.flags is not None and not (self.flags & 0x80)


@dataclass
class ViewedLine:
    """One joined, human-viewable line -- what a frontend lists. ``text`` is None when the ``.mes`` had no
    entry for this txid (the call was found but its text couldn't be resolved)."""
    source: str                  # 'npc' / 'event' / 'cutscene' / 'choice' / 'scene' / 'text'
    who: str                     # a human label (the NPC/event name, or "entry 7")
    txid: Optional[int]
    text: Optional[str]
    tail: Optional[str] = None
    pos: Optional[tuple] = None
    entry: Optional[int] = None  # the source .eb entry (for de-duping a line shown from several funcs)
    system: bool = False         # a system/notification window (flags lacking the dialogue-box bit), not dialogue


# ------------------------------------------------------------------- .mes parse ---
# .mes layout (mirrors Memoria's FF9TextTool.ExtractSentense): a stream of `[STRT=a,b]...text...[ENDN]`
# entries whose txid is the entry's 0-based POSITION -- base-game field text carries NO `[TXID=]` tags. An
# optional `[TXID=n]` marker RE-INDEXES the running id (the kit's mod-add trick emits one per line); ids
# increment from there. So we split on `[TXID=` (re-index points), then on `[STRT=` (entries), as the engine
# does. This reads real FF9 field text (index-implicit) AND round-trips the kit's explicit `[TXID=n]` output.
_TAIL_RE = re.compile(r"\[TAIL=([^\]]*)\]")


def _parse_entry(seg: str):
    """One entry from a ``[STRT=`` split segment (``"a,b]<...>text[ENDN]..."``) -> ``(strt, tail, text)``. The
    text is everything after the STRT (and an optional leading TAIL) tag up to ``[ENDN]`` (verbatim -- keeps
    embedded colour/name tags + ``\\n``/``[PAGE]``); a missing ``[ENDN]`` takes the rest of the segment."""
    bracket = seg.find("]")
    if bracket < 0:
        return None
    strt, rest = seg[:bracket], seg[bracket + 1:]
    tail = None
    mt = _TAIL_RE.match(rest)
    if mt:
        tail, rest = mt.group(1), rest[mt.end():]
    end = rest.find("[ENDN]")
    return strt, tail, (rest[:end] if end >= 0 else rest)


def parse_mes(body: str) -> dict:
    """Parse a ``.mes`` block into ``{txid: MesEntry}`` -- the reader the kit never had. Handles BOTH the
    base game's index-implicit entries (txid = position) and the kit's explicit ``[TXID=n]`` re-index form,
    so it reads real FF9 field text AND round-trips :func:`content.text.build_mes` exactly."""
    out: dict = {}
    for bi, block in enumerate(("" if body is None else body).split("[TXID=")):
        idx = 0
        if bi > 0:                                    # a `[TXID=n]` re-index marker -> `n]` then the entries
            end = block.find("]")
            if end < 0:
                continue
            try:
                idx = int(block[:end])
            except ValueError:
                continue
            block = block[end + 1:]
        for seg in block.split("[STRT=")[1:]:         # each `[STRT=` starts one entry; [0] is pre-entry junk
            parsed = _parse_entry(seg)
            if parsed is not None:
                strt, tail, text = parsed
                out[idx] = MesEntry(txid=idx, text=text, tail=tail or None, strt=strt or None)
            idx += 1
    return out


def strip_tags(text: str) -> str:
    """A readable rendering of one line: drop FF9 control tags, render ``[PAGE]`` as a separator, and turn a
    renameable name tag (``[VIVI]``) into its plain code. For a 'clean' preview, not for re-building."""
    if text is None:
        return ""
    t = text.replace("[PAGE]", "\n---\n")

    def _sub(m):
        code = m.group(0)[1:-1].split("=", 1)[0].strip().upper()
        return code.title() if code in _text._NAME_TAGS else ""
    return _text._TAG_RE.sub(_sub, t)


# ----------------------------------------------------------------- .eb scan ---
def _signed16(v: int) -> int:
    return v - 0x10000 if v >= 0x8000 else v


def _var_const(body: bytes, var_index: int):
    """The 2-byte signed const a ``SetVar D9(var_index) = const`` assigns, or None. Pattern (the kit's
    player-clone NPC sets its x at D9(0), z at D9(4)): ``05 D9 <var> 7D <lo> <hi>`` -- mirrors
    :func:`content.npc._find_var_const` but never raises."""
    pat = bytes([0x05, 0xD9, var_index & 0xFF, 0x7D])
    i = body.find(pat)
    if i < 0 or i + len(pat) + 1 >= len(body):
        return None
    j = i + len(pat)
    return _signed16(body[j] | (body[j + 1] << 8))


def _entry_pos_model(eb: EbScript, entry):
    """Best-effort ``(x, z, model)`` an entry's Init (tag-0) func creates itself at. Reliable for kit-built
    NPCs (player-object clones); a real-field NPC that positions itself differently just yields Nones."""
    f0 = entry.func_by_tag(0)
    if f0 is None:
        return None, None, None
    body = eb.data[f0.abs_start:f0.abs_end]
    model = None
    for ins in eb.instrs(f0):
        if ins.op == SET_MODEL:
            model = ins.imm(0)
            break
    return _var_const(body, 0), _var_const(body, 4), model


def scan_dialogue(eb) -> list:
    """Every dialogue-window call in a field's ``.eb``, in entry/func/code order -- a list of
    :class:`DialogueCall`. ``eb`` may be raw bytes or an :class:`EbScript`. NPC talk lines are
    ``func_tag == 3`` (kind 'npc'); event/cutscene/region lines are other tags (kind 'scene')."""
    if isinstance(eb, (bytes, bytearray)):
        eb = EbScript.from_bytes(bytes(eb))
    calls: list = []
    for entry in eb.entries:
        if entry.empty:
            continue
        pos_model = None
        for func in entry.funcs:
            for ins in eb.instrs(func):
                opnd = WINDOW_OPS.get(ins.op)
                if opnd is None:
                    continue
                if pos_model is None:
                    pos_model = _entry_pos_model(eb, entry)
                x, z, model = pos_model
                calls.append(DialogueCall(entry.index, func.tag, ins.imm(opnd), x, z, model, ins.op,
                                          ins.imm(1)))   # operand 1 = window flags (0x80 = dialogue box)
    return calls


# ------------------------------------------------------------------- join ---
def _who(call: DialogueCall, field_label: str) -> str:
    if call.kind == "npc":
        tail = f", model {call.model}" if call.model is not None else ""
        return f"NPC (entry {call.entry_idx}{tail})"
    return f"{field_label} (entry {call.entry_idx}, func {call.func_tag})"


def join(calls, mes_map: dict, *, field_label: str = "field", trust_positions: bool = True) -> list:
    """JOIN decoded ``.eb`` calls (:func:`scan_dialogue`) with parsed ``.mes`` text (:func:`parse_mes`) on
    txid -> ordered :class:`ViewedLine`s (LOSSLESS -- every call, system windows flagged, no de-dup; use
    :func:`present` for the clean reading view). A call whose txid has no ``.mes`` entry keeps ``text=None``.
    ``trust_positions=False`` drops the ``(x,z)`` -- the position heuristic is the kit player-clone's
    ``D9(0)/D9(4)`` convention, which is meaningless on a real field's own NPCs (set it False for those)."""
    out = []
    for c in calls:
        e = mes_map.get(c.txid) if c.txid is not None else None
        pos = (c.x, c.z) if (trust_positions and c.x is not None and c.z is not None) else None
        out.append(ViewedLine(
            source=c.kind, who=_who(c, field_label), txid=c.txid,
            text=(e.text if e else None), tail=(e.tail if e else None),
            pos=pos, entry=c.entry_idx, system=c.is_system))
    return out


def present(lines, *, show_system: bool = False, dedupe: bool = True) -> list:
    """The clean reading view over the lossless :func:`join` output: hide system/notification windows (the
    ``flags=0`` error/'Received item!' overlays) unless ``show_system``, and collapse a line referenced from
    several funcs of the SAME object to one row (preferring its NPC-talk representation over a scene/init
    one). Distinct objects that share a txid stay separate (two NPCs may speak the same line)."""
    rows = [ln for ln in lines if show_system or not ln.system]
    if not dedupe:
        return rows
    out, seen = [], {}
    for ln in rows:
        key = (ln.entry, ln.txid, ln.text)
        if key not in seen:
            seen[key] = len(out)
            out.append(ln)
        elif out[seen[key]].source != "npc" and ln.source == "npc":
            out[seen[key]] = ln                        # prefer the NPC-talk row as the representative
    return out


# ---------------------------------------------------------- read: a mod folder (offline) ---
def _parse_dictionary_patch(path: Path) -> list:
    """The ``FieldScene <id> <area> <mapid> <name> <textid>`` rows of a mod's DictionaryPatch.txt."""
    rows = []
    try:
        lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return rows
    for ln in lines:
        t = ln.split()
        if len(t) >= 6 and t[0] == "FieldScene" and t[1].lstrip("-").isdigit() and t[5].lstrip("-").isdigit():
            rows.append({"id": int(t[1]), "area": t[2], "mapid": t[3], "name": t[4], "textid": int(t[5])})
    return rows


def _match_scene(rows: list, field):
    """Pick the FieldScene row for ``field`` (a numeric id, or a name/mapid substring; case-insensitive)."""
    s = str(field).strip()
    if s.lstrip("-").isdigit():
        fid = int(s)
        return next((r for r in rows if r["id"] == fid), None)
    sl = s.lower()
    exact = [r for r in rows if sl in (r["name"].lower(), r["mapid"].lower())]
    if exact:
        return exact[0]
    sub = [r for r in rows if sl in r["name"].lower() or sl in r["mapid"].lower()]
    return sub[0] if len(sub) == 1 else (None if not sub else sub[0])


def _local_eb_bytes(layout, name: str, lang: str):
    """The ``.eb`` bytes a mod folder holds for a field NAME, trying ``EVT_<NAME>``/``evt_<name>`` then any
    file in the lang dir whose stem contains the name (forked fields keep their original evt name)."""
    d = layout.eventbinary_field_dir / lang
    cands = [f"EVT_{name}.eb.bytes", f"evt_{name.lower()}.eb.bytes"]
    for c in cands:
        p = d / c
        if p.is_file():
            return p.read_bytes()
    if d.is_dir():
        key = name.lower()
        for p in sorted(d.glob("*.eb.bytes")):
            if key in p.name.lower():
                return p.read_bytes()
    return None


def read_local_dialogue(mod_folder, field, lang: str = "us") -> list:
    """Read + join the dialogue of a field in a BUILT mod folder on disk (no game install, no UnityPy) --
    the offline 'view this field's dialogue' path (and the demo: the kit's own ``release/FF9CustomMap`` hut
    shows 'NPC ... -> "I miss you Zidane"'). Resolves the field via the mod's DictionaryPatch."""
    from .config import ModLayout
    layout = ModLayout(Path(mod_folder))
    rows = _parse_dictionary_patch(layout.dictionary_patch)
    if not rows:
        raise FileNotFoundError(f"no FieldScene rows in {layout.dictionary_patch} (is {mod_folder} a built mod?)")
    row = _match_scene(rows, field)
    if row is None:
        names = ", ".join(sorted(r["name"] for r in rows))
        raise FileNotFoundError(f"field {field!r} not in {mod_folder} (have: {names})")
    eb_bytes = _local_eb_bytes(layout, row["name"], lang)
    if eb_bytes is None:
        raise FileNotFoundError(f"no .eb for {row['name']!r} in {layout.eventbinary_field_dir / lang}")
    mes_path = layout.mes_path(lang, row["textid"])
    mes_map = parse_mes(mes_path.read_text(encoding="utf-8", errors="replace")) if mes_path.is_file() else {}
    return join(scan_dialogue(eb_bytes), mes_map, field_label=row["mapid"])


# ------------------------------------------------------- read: a real FF9 field (install) ---
def _resolve_field_id(field) -> int:
    """A field id from a numeric id or a unique FBG-folder substring (e.g. 'alexandria', 'iccv')."""
    from . import extract
    s = str(field).strip()
    if s.lstrip("-").isdigit():
        return int(s)
    sl = s.lower()
    hits = sorted(fid for fid, folder in extract.ID_TO_FBG.items() if sl in folder)
    if not hits:
        raise FileNotFoundError(f"no field id or FBG folder matches {field!r}. Try: ff9mapkit list-fields {sl}")
    if len(hits) > 1:
        raise ValueError(f"{field!r} matches {len(hits)} fields; pass an id or a more specific name "
                         f"(e.g. {hits[:6]}).")
    return hits[0]


_MES_NAME_RE = re.compile(r"^(\d+)\.mes$", re.I)


def _resources_assets(game=None):
    """The resources.assets that holds the base ``<n>.mes`` field/battle text (x64 build, else flat)."""
    from .config import find_game_path
    g = find_game_path(game)
    for cand in (g / "x64" / "FF9_Data" / "resources.assets", g / "FF9_Data" / "resources.assets"):
        if cand.exists():
            return cand
    return None


# Common function words per language -- the reliable signal for picking the requested language among the
# per-language copies of a `<zone>.mes` (they share entry indices, so coverage can't tell them apart, and
# resources.assets carries no language in the asset path). Raw letter counts DON'T work (German/French are
# wordier than English and would win on length); whole-word stopword hits separate them cleanly.
_STOPWORDS = {
    "en": ("the", "you", "and", "to", "of", "is", "it", "that", "have", "with", "this", "what", "your",
           "are", "for", "but", "was", "not", "they", "here", "there", "will", "don't", "i'm", "we"),
    "fr": ("le", "la", "les", "je", "ne", "pas", "vous", "est", "une", "des", "que", "qui", "pour", "tu",
           "il", "ce", "mais", "c'est", "moi", "tout"),
    "it": ("che", "di", "non", "il", "per", "sono", "una", "gli", "sei", "ho", "ti", "mi", "questo",
           "come", "qui", "ma", "anche", "siamo"),
    "es": ("que", "el", "los", "las", "una", "por", "con", "esto", "eres", "pero", "como", "para", "tu",
           "muy", "aqui", "esta", "soy"),
    "de": ("der", "die", "das", "und", "ist", "nicht", "ein", "ich", "zu", "es", "mit", "du", "war",
           "sein", "wir", "aber", "auch", "hier", "wie"),
}
# kit lang code -> stopword set (uk==us==en; gr is German)
_LANG_ALIAS = {"us": "en", "uk": "en", "gr": "de", "fr": "fr", "it": "it", "es": "es"}
_WORD_RE = re.compile(r"[a-zàâäçéèêëîïôûùüöñ']+")


def _lang_score(text: str, lang: str) -> int:
    """A 'is this block the requested language' score, to disambiguate the per-language copies of a
    ``<zone>.mes``. ``jp`` = the CJK block; every other language is picked by how many of its common
    function words (the/und/que/...) appear as whole words. Best-effort but reliably separates English from
    German/French/Italian/Spanish on real field text."""
    cjk = sum(1 for c in text if "぀" <= c <= "鿿")
    if lang == "jp":
        return cjk
    sw = set(_STOPWORDS.get(_LANG_ALIAS.get(lang, "en"), _STOPWORDS["en"]))
    hits = sum(1 for w in _WORD_RE.findall(text.lower()) if w in sw)
    return hits - 3 * cjk                              # a CJK block is never a romance/germanic match


def _load_field_text(want_txids, lang: str, game=None, zone_id: Optional[int] = None) -> dict:
    """Best-effort ``{txid: MesEntry}`` for a real field's text, read live from the install. A field's text
    file is ``<zone-id>.mes`` (named by the field's text-zone id, not its map id). With ``zone_id`` it reads
    that block (picking the requested LANGUAGE among its per-lang copies); otherwise it scans every
    ``<n>.mes`` and picks the block that best covers ``want_txids`` (a field references a contiguous range, so
    the best-overlap block is its own), tie-broken by language. Returns ``{}`` -- never raises -- when nothing
    resolves, so the caller still shows the decoded calls. (Install-/layout-dependent: verified vs the game.)"""
    from . import extract
    ra = _resources_assets(game)
    if ra is None:
        return {}
    try:
        UnityPy = extract._unitypy()
        env = UnityPy.load(str(ra))
    except Exception:                                  # noqa: BLE001 -- missing UnityPy / unreadable asset
        return {}
    want = set(t for t in (want_txids or []) if t is not None)
    cands = []                                         # (coverage, lang_score, parsed)
    for o in env.objects:
        if o.type.name != "TextAsset":
            continue
        try:
            d = o.read()
            m = _MES_NAME_RE.match(getattr(d, "m_Name", "") or "")
            if not m or (zone_id is not None and int(m.group(1)) != int(zone_id)):
                continue
            body = extract._raw_bytes(d)
            raw = body.decode("utf-8", "replace") if body else ""
            parsed = parse_mes(raw)
        except Exception:                              # noqa: BLE001 -- skip an unreadable block
            continue
        cov = len(want & set(parsed)) if want else len(parsed)
        if zone_id is None and want and cov == 0:      # auto-detect: ignore blocks that share no txid at all
            continue
        cands.append((cov, _lang_score(raw, lang), parsed))
    if not cands:
        return {}
    cands.sort(key=lambda c: (c[0], c[1]), reverse=True)   # best coverage, then best language match
    return cands[0][2]


def read_field_dialogue(field, lang: str = "us", game=None, zone_id: Optional[int] = None) -> list:
    """Read + join a REAL FF9 field's dialogue, live from the install (needs UnityPy). Decodes the field's
    ``.eb`` for its dialogue calls and resolves the text block ``<zone_id>.mes`` -- ``zone_id`` defaults to
    the engine's own field-map-id -> text-id table (:data:`_fieldtext.EVENT_ID_TO_MES`, i.e. Memoria's
    ``eventIDToMESID``), so the RIGHT block + language is read (txids are 0-based positions every field's text
    shares, so they can't pick the block). Unresolved text stays ``None`` (the calls + txids still show). This
    is the 'import a real field's dialogue to prove plausibility' path."""
    from . import extract
    from ._fieldtext import EVENT_ID_TO_MES
    fid = _resolve_field_id(field)
    eb_bytes = extract.EventBundle(game=game, lang=lang).eb_for_id(fid)
    if eb_bytes is None:
        raise FileNotFoundError(f"no field event script for {field!r} (id {fid}) -- a world/special field?")
    calls = scan_dialogue(eb_bytes)
    txids = [c.txid for c in calls]
    if zone_id is None:                                # the AUTHORITATIVE field -> text-block id (the engine's
        zone_id = EVENT_ID_TO_MES.get(fid)            # own eventIDToMESID); txids alone can't pick the block
    mes_map = _load_field_text(txids, lang, game=game, zone_id=zone_id)
    folder = extract.ID_TO_FBG.get(fid, str(fid))
    # real fields don't use the kit's D9(0)/D9(4) spawn convention -> the (x,z) heuristic is noise here
    return join(calls, mes_map, field_label=folder, trust_positions=False)


# ---------------------------------------------------------- read: an authored field.toml ---
def _iter_txids(obj, prefix=""):
    """Yield ``(label, txid)`` for every int leaf in a collect_text txid map (dict/list, possibly nested --
    a choice maps its prompt + per-option reply ids)."""
    if isinstance(obj, dict):
        items = obj.items()
    elif isinstance(obj, (list, tuple)):
        items = enumerate(obj)
    else:
        return
    for k, v in items:
        lbl = f"{prefix}{k}"
        if isinstance(v, int):
            yield lbl, v
        else:
            yield from _iter_txids(v, prefix=f"{lbl}.")


def project_dialogue(project) -> list:
    """The authored dialogue of a loaded ``field.toml`` (a ``build.FieldProject``), as ordered
    :class:`ViewedLine`s with the FINAL wrapped text -- so the viewer/editor shows exactly what ships. Built
    by running the unchanged :func:`build.collect_text` and parsing its ``.mes`` back, so it can never drift
    from the real build output."""
    from . import build as _build
    mes_body, npc_txids, ev_txids, cs_txids, ch_txids = _build.collect_text(project)
    mes = parse_mes(mes_body)
    raw = getattr(project, "raw", {}) or {}
    npcs, events = raw.get("npc", []), raw.get("event", [])

    label: dict = {}                                   # txid -> (source, who)
    for k, t in _iter_txids(npc_txids):
        i = int(str(k).split(".")[0]) if str(k).split(".")[0].isdigit() else None
        label.setdefault(t, ("npc", _name(npcs, i, f"NPC #{k}")))
    for k, t in _iter_txids(ev_txids):
        i = int(str(k).split(".")[0]) if str(k).split(".")[0].isdigit() else None
        label.setdefault(t, ("event", _name(events, i, f"event #{k}")))
    for k, t in _iter_txids(cs_txids):
        label.setdefault(t, ("cutscene", f"cutscene say {k}"))
    for k, t in _iter_txids(ch_txids):
        label.setdefault(t, ("choice", f"choice {k}"))

    out = []
    for txid in sorted(mes):
        src, who = label.get(txid, ("text", f"txid {txid}"))
        e = mes[txid]
        out.append(ViewedLine(src, who, txid, e.text, e.tail, None))
    return out


def _name(lst, i, fallback):
    if i is not None and isinstance(lst, list) and 0 <= i < len(lst):
        return lst[i].get("name") or fallback
    return fallback


# ----------------------------------------------------- editable refs (for the GUI) ---
@dataclass(frozen=True)
class TextRef:
    """A pointer to ONE editable dialogue line in a field.toml's data, so a UI can list + edit every line
    in one place without knowing the section shapes. ``path`` locates the text value; ``speaker_path`` /
    ``tail_path`` (when present) locate its sibling speaker name + window tail. The dialogue editor renders
    one of these per row."""
    section: str                 # 'npc' / 'event' / 'choice' / 'reply' / 'cutscene'
    label: str
    path: tuple
    speaker_path: Optional[tuple] = None
    tail_path: Optional[tuple] = None


def collect_text_refs(data: dict) -> list:
    """Every editable dialogue line in a field.toml ``data`` dict, in author order -- NPC lines, event
    messages, choice prompts + per-option replies, and cutscene ``say`` steps. The unified list the
    dialogue editor edits (placement/structure stays the Logic Editor's; this owns the WORDS)."""
    refs: list = []
    for i, n in enumerate(data.get("npc", []) or []):
        if "dialogue" in n:
            refs.append(TextRef("npc", f"NPC: {n.get('name') or '#' + str(i)}", ("npc", i, "dialogue"),
                                ("npc", i, "speaker"), ("npc", i, "tail")))
    for i, e in enumerate(data.get("event", []) or []):
        if "message" in e:
            refs.append(TextRef("event", f"Event: {e.get('name') or '#' + str(i)}", ("event", i, "message"),
                                ("event", i, "speaker"), ("event", i, "tail")))
    for i, c in enumerate(data.get("choice", []) or []):
        who = c.get("npc") or ("zone" if "zone" in c else "#" + str(i))
        if "prompt" in c:
            refs.append(TextRef("choice", f"Choice {who}: prompt", ("choice", i, "prompt"),
                                ("choice", i, "speaker"), ("choice", i, "tail")))
        for j, o in enumerate(c.get("options", []) or []):
            refs.append(TextRef("reply", f"Choice {who}: reply to “{o.get('text') or '#' + str(j)}”",
                                ("choice", i, "options", j, "reply")))
    cs = data.get("cutscene")
    if isinstance(cs, dict):
        for k, st in enumerate(cs.get("steps", []) or []):
            if "say" in st:
                refs.append(TextRef("cutscene", f"Cutscene: say #{k}", ("cutscene", "steps", k, "say")))
    return refs


def get_text(data: dict, path: tuple):
    """The value at ``path`` (a collect_text_refs path) in ``data``, or None if any step is missing."""
    cur = data
    for k in path:
        if isinstance(cur, dict):
            cur = cur.get(k)
        elif isinstance(cur, list) and isinstance(k, int) and 0 <= k < len(cur):
            cur = cur[k]
        else:
            return None
    return cur


def set_text(data: dict, path: tuple, value) -> bool:
    """Set (or, for an empty/None ``value``, REMOVE) the dict-keyed leaf at ``path``. Intermediate list/dict
    steps must already exist (they do for a collect_text_refs path -- only the final key may be absent, e.g.
    adding a ``speaker``/``reply``). Returns True on success."""
    cur = data
    for k in path[:-1]:
        if isinstance(cur, dict):
            cur = cur.get(k)
        elif isinstance(cur, list) and isinstance(k, int) and 0 <= k < len(cur):
            cur = cur[k]
        else:
            return False
        if cur is None:
            return False
    last = path[-1]
    if not isinstance(cur, dict):
        return False
    if value is None or value == "":
        cur.pop(last, None)
    else:
        cur[last] = value
    return True


# ------------------------------------------------------------------- formatting ---
def wrap_preview(text: str, width=None) -> str:
    """How a line breaks on the FF9 screen (the proportional approximation -- see content.text). Reuses the
    exact build-time wrapper so the preview matches what ships."""
    return _text.wrap_text(text or "", width if width is not None else _text.DEFAULT_WRAP_WIDTH)[0]


def overflow(text: str, width=None) -> list:
    """Final wrapped lines that still exceed ``width`` -- an unbreakable over-wide word. Empty = it fits."""
    return _text.overflow_lines(text or "", width if width is not None else _text.DEFAULT_WRAP_WIDTH)


def format_lines(lines, *, clean: bool = False, show_system: bool = False, dedupe: bool = True) -> str:
    """Render :class:`ViewedLine`s as a readable block (the CLI viewer's output), through :func:`present`
    (hide system windows + de-dupe by default; ``show_system`` / ``dedupe=False`` give the raw view).
    ``clean=True`` strips FF9 control tags from the text for a plain read; otherwise tags are kept verbatim."""
    out = []
    for ln in present(lines, show_system=show_system, dedupe=dedupe):
        meta = []
        meta.append(f"txid {ln.txid}" if ln.txid is not None else "txid <expr>")
        if ln.tail:
            meta.append(f"tail {ln.tail}")
        if ln.pos:
            meta.append(f"@ {ln.pos[0]}, {ln.pos[1]}")
        if ln.system:
            meta.append("system")
        out.append(f"[{ln.source}] {ln.who}   ({', '.join(meta)})")
        if ln.text is None:
            out.append("    (text not resolved)")
        else:
            shown = strip_tags(ln.text) if clean else ln.text
            out.extend("    " + part for part in shown.split("\n"))
        out.append("")
    return "\n".join(out).rstrip() + "\n"
