"""[[folklore]] -- the Folklore codex data spine: entries minted as FF9 KEY ITEMS (important-id band
80-254), their name / help / long-lore text shipped as the three cumulative mod-side KeyItem ``.mes``
overlays, and grants riding the existing ``AddItem`` opcode with a pool-encoded item id.

The engine facts this module encodes (all source-verified -- studies/folklore-codex/PLAN.md):

- Real FF9 key items occupy important ids 0-79 (all 7 languages); **80-254 is empty** -> the Folklore
  band (175 slots). **255 is reserved** (``FF9FITEM_RARE_NONE``, the empty-list sentinel row).
- Ownership lives in ``rare_item_obtained`` (a ``HashSet<Int32>``) -- NOT ``gEventGlobal`` -- and every
  save double-writes it (legacy 2-bit bitfield ids 0-255 + the uncapped ``rareItemsEx`` sidecar), so
  the band is save-robust with zero flag bookkeeping (``HashSet.Add`` is idempotent).
- Text: ``FF9TextTool``'s three KeyItem setters index uncapped per-id dictionaries, fed by the
  cumulative importer from ``EmbeddedAsset/Text/<lang>/KeyItem/{imp_name,imp_help,imp_skin}.mes``.
  A mod overlay carries ONLY its own ids -- the ``[TXID=<id>]<text>[ENDN]`` sentence dialect (same as
  the in-game-proven command/ability name overlays; NOT the field-dialogue dialect, which leads with
  ``_`` and carries [STRT]/[TAIL]). The importer's id counter starts at 0 and auto-increments for
  entries WITHOUT a [TXID=] -> every entry we emit MUST lead with its [TXID=] or it would clobber
  real key item 0.
- Grant: ``AddItem`` (0x48) with item id ``256 + important_id`` routes through the engine's pool
  decode (``FF9Item_Add_Generic``: id%1000 in [256,512) -> important) -- silent, no dialog/SFX/flag/
  achievement side effects, count>0 grants exactly one.
"""
from __future__ import annotations

FIRST_FOLKLORE_ID = 80     # 0-79 = real key items (all 7 languages censused empty above 79)
LAST_FOLKLORE_ID = 254     # 255 = FF9FITEM_RARE_NONE (the Key Items screen's empty-list sentinel)
POOL_BASE = 256            # AddItem pool-encode: important id N -> item id 256+N (336-510)

# the ``[[folklore]]`` channel -> overlay-file stem -> in-game surface
CHANNELS = (("name", "imp_name"),   # the Key Items list-row name (required -- a blank row otherwise)
            ("help", "imp_help"),   # the short help line under the list (optional)
            ("lore", "imp_skin"))   # the long "skin" popup lore text (optional)

# THE SKIN BUDGET (playtest 2026-07-20: over-long lore CLIPS -- the parchment popup is a FIXED panel,
# no scroll). Vanilla ground truth, measured across all 7 languages' real imp_skin.mes/imp_help.mes
# (extracted from resources.assets): the longest vanilla lore = 210 visible chars, HAND-wrapped into
# at most 7 lines of ~28 chars; the longest help = 135 chars. Kit lore relies on the engine's
# AUTO-wrap (~32 chars/line at the menu font, ~6 lines shown before the clip in the playtest), so the
# kit budgets 6 estimated lines -- conservative by design. Explicit newlines each consume a line.
LORE_MAX_LINES = 6
LORE_CHARS_PER_LINE = 32
HELP_MAX_CHARS = 135


def lore_lines_estimate(text: str) -> int:
    """Estimated wrapped line count of a lore text in the skin popup (auto-wrap ~32 chars/line;
    an explicit newline starts a new line)."""
    return sum(max(1, -(-len(seg) // LORE_CHARS_PER_LINE))       # ceil-div
               for seg in str(text).split("\n"))


class FolkloreError(ValueError):
    """A [[folklore]] block or reference the kit can't honour."""


def _norm(s) -> str:
    return "".join(c for c in str(s).lower() if c.isalnum())


def _check_band(iid) -> int:
    if isinstance(iid, bool) or not isinstance(iid, int):   # a float 80.5 must REPORT, not floor to 80
        raise FolkloreError(f"folklore id must be an integer, got {iid!r}")
    if not (FIRST_FOLKLORE_ID <= iid <= LAST_FOLKLORE_ID):
        raise FolkloreError(
            f"folklore id {iid} out of band {FIRST_FOLKLORE_ID}-{LAST_FOLKLORE_ID} "
            f"(0-79 = real FF9 key items; 255 = the engine's empty-list sentinel)")
    return iid


def resolve(name_or_id, blocks=None) -> int:
    """A [[folklore]] entry NAME or important-id -> its numeric important id (80-254).

    An int / digit-string passes through (band-checked); a name is matched case/space/punct-
    insensitively against the given ``blocks`` (the field's ``[[folklore]]`` list). Deliberately
    INDEPENDENT of :func:`ff9mapkit.items.resolve` (which caps at 255 regular ids and would reject the
    pool encoding) and :func:`ff9mapkit.keyitems.resolve` (the install's REAL key-item names)."""
    if isinstance(name_or_id, bool):
        raise FolkloreError("folklore entry cannot be a boolean")
    if isinstance(name_or_id, float):                      # 80.5 must REPORT as a bad id, not read as a name
        raise FolkloreError(f"folklore id must be an integer, got {name_or_id!r}")
    if isinstance(name_or_id, int):
        return _check_band(name_or_id)
    s = str(name_or_id).strip()
    if not s:
        raise FolkloreError("folklore entry name is empty")
    if s.isdigit():
        return _check_band(int(s))
    key = _norm(s)
    for b in blocks or []:
        if isinstance(b, dict) and _norm(b.get("name", "")) == key and "id" in b:
            return _check_band(b["id"])
    raise FolkloreError(f"unknown folklore entry {name_or_id!r} -- name one of this field's "
                        f"[[folklore]] blocks (or pass its numeric id 80-254)")


def pool_id(important_id: int) -> int:
    """The important id -> the AddItem operand (the engine's pool encoding). 80 -> 336, 254 -> 510."""
    return POOL_BASE + _check_band(important_id)


def _check_text(text, where: str) -> str:
    """Type + structural guard: folklore text must be a REAL string (a stray int/bool/list must report,
    not str()-coerce into shipped in-game text), and the overlay dialect delimits entries with the
    literal ``[ENDN]`` / keys them on a LEADING ``[TXID=`` -- text containing either would corrupt the
    whole file's parse. The single choke point both the build's warn-and-skip dry-run and validate()
    route through."""
    if not isinstance(text, str):
        raise FolkloreError(f"{where} must be a string, got {text!r}")
    if "[ENDN]" in text:
        raise FolkloreError(f"{where} contains the literal '[ENDN]' -- it is the overlay entry "
                            "terminator and cannot appear in folklore text")
    if text.lstrip().startswith("[TXID="):
        raise FolkloreError(f"{where} starts with '[TXID=' -- it is the overlay entry key and cannot "
                            "lead folklore text")
    return text


def render_overlays(blocks) -> dict:
    """The field/mod's ``[[folklore]]`` blocks -> the three overlay bodies:
    ``{"imp_name": .., "imp_help": .., "imp_skin": ..}`` (an empty string = no entries supply that
    channel -> the emitter skips writing that file).

    Each body is the exact cumulative-importer dialect -- ``[TXID=<id>]<text>[ENDN]`` sentences
    concatenated with NO separator, ascending by id (order is cosmetic: every entry carries its own
    [TXID=], which resets the importer's counter). Assumes blocks were already sanitized (the build's
    ``_emit_folklore`` warns-and-skips; ``validate()`` reports precisely)."""
    entries = [(_check_band(b.get("id") if isinstance(b, dict) else b), b) for b in blocks or []]
    entries.sort(key=lambda t: t[0])                       # band-check BEFORE sorting: a bad id reports
    out = {stem: [] for _, stem in CHANNELS}               # cleanly instead of a mixed-type sort error
    for iid, b in entries:
        for chan, stem in CHANNELS:
            text = b.get(chan)
            if text is None:
                continue
            body = _check_text(text, f"[[folklore]] id {iid} {chan}")
            if not body:
                continue
            out[stem].append(f"[TXID={iid}]{body}[ENDN]")
    return {stem: "".join(parts) for stem, parts in out.items()}


def validate_blocks(blocks) -> list:
    """Lint a field's ``[[folklore]]`` list -> human-readable problems (empty => OK). The precise
    counterpart of the build's warn-and-skip pass (the recurring lesson: build/deploy do NOT run
    validate, so both layers exist)."""
    problems: list = []
    seen: dict = {}
    for k, b in enumerate(blocks or []):
        where = f"[[folklore]] #{k}"
        if not isinstance(b, dict):
            problems.append(f"{where} must be a table (got {type(b).__name__})")
            continue
        if "id" not in b:
            problems.append(f"{where} needs an id = N (the important-item id, "
                            f"{FIRST_FOLKLORE_ID}-{LAST_FOLKLORE_ID})")
            continue
        try:
            iid = _check_band(b["id"])                     # strict: bool/float/string ids REPORT (never floor)
        except FolkloreError as e:
            problems.append(f"{where}: {e}")
            continue
        if iid in seen:
            problems.append(f"{where} id {iid} already used by [[folklore]] #{seen[iid]} "
                            "(each entry needs its own id)")
        seen[iid] = k
        nm = b.get("name")
        if not isinstance(nm, str) or not nm.strip():
            problems.append(f"{where} (id {iid}) needs a non-empty name = \"...\" "
                            "(a missing imp_name renders a BLANK Key Items row)")
        for chan, _stem in CHANNELS:
            v = b.get(chan)
            if v is None:
                continue
            if not isinstance(v, str):
                problems.append(f"{where} (id {iid}) {chan} must be a string, got {v!r}")
                continue
            try:
                _check_text(v, f"{where} (id {iid}) {chan}")
            except FolkloreError as e:
                problems.append(str(e))
                continue
            if chan == "lore":
                est = lore_lines_estimate(v)
                if est > LORE_MAX_LINES:
                    problems.append(
                        f"{where} (id {iid}) lore is ~{est} wrapped lines -- the skin popup fits only "
                        f"~{LORE_MAX_LINES} (a fixed parchment panel, NO scroll; playtest-proven clip). "
                        f"Trim to <= ~{LORE_MAX_LINES * LORE_CHARS_PER_LINE} chars or split entries.")
            elif chan == "help" and len(v) > HELP_MAX_CHARS:
                problems.append(
                    f"{where} (id {iid}) help is {len(v)} chars -- the vanilla maximum is "
                    f"{HELP_MAX_CHARS} (the help bar clips beyond it). Trim it.")
    return problems
