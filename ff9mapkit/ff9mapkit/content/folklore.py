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

THE displayRef GRAMMAR (s46 rung 4, the render-rig kit lane -- studies/folklore-codex/RENDER-RIG.md
section 3): an optional ``display = "<ref>"`` key on ``[[folklore]]`` puts a live 3D creature/model
portrait behind an entry, wired through ``FolklorePatch.txt``'s THIRD column (the engine already
parses + stores it as ``Entry.Display``, s45 patch:925-930,986 -- the engine whitespace-splits, so the
wire token is ONE space-free string). The kit's canonical wire form is ``model:GEO_NAME`` (GEO names
are ``[A-Z0-9_]+`` by construction, so the emitted token always matches ``^model:GEO_[A-Z0-9_]+$``).
:func:`resolve_display` resolves an author's ``<ref>`` in order:

  1. a friendly archetype/creature name (``"moogle"``, ``"bandersnatch"``) -- the SAME curated tables
     ``[[npc]] archetype =`` resolves against (:mod:`ff9mapkit.archetypes`, the playable-character
     presets + ``ARCHETYPES`` + ``CREATURES``; lookup pattern mirrors ``infohub._model_of_archetype``);
  2. an exact GEO model name (case-insensitive) or a numeric GEO id, via :mod:`ff9mapkit.catalog`
     (``catalog.model`` / ``catalog.resolve_model`` -- an unknown name/id raises ``catalog``'s own
     ``ValueError`` with difflib near-miss hints, propagated VERBATIM, never rephrased);
  3. an explicit ``model:`` scheme prefix is accepted (and stripped first) but never required --
     ``display = "model:GEO_MON_B3_118"`` and ``display = "GEO_MON_B3_118"`` resolve identically.

No raw enemy display names (``"Bomb"``): no such catalog exists in the kit and building one is a
separate provenance-sensitive project. Display is NOT gated on ``category`` (a ``places`` entry
showing a landmark model is legitimate).

THE idle GRAMMAR (the render-rig kit lane's per-entry idle-clip override): an optional ``idle =
"<ref>"`` key on ``[[folklore]]`` is meaningful ONLY alongside ``display`` -- it names which of the
portrait model's OWN animation clips plays as its living idle, instead of the engine's default
(``animList[0]``). The engine already resolves an optional 4th ``FolklorePatch.txt`` token
``idle:<clipName>`` against the model's own discovered clip list (exact match first, else a unique
``_<suffix>`` match), fail-soft (a bad token falls back to the default clip, never text-only). The
kit resolves the SAME way, offline, so a bad ref is caught at lint/build time instead of a silent
in-game fallback:

  1. a full clip name (``"ANH_MON_B3_118_003"``), any case -> canonicalized to the animation DB's
     exact casing;
  2. a bare suffix (``"003"`` or ``"3"``) -- zero-pad-aware: a clip matches when it ends with ``"_"``
     + the literal form given, OR (for a digit ref) its own trailing ``"_"``-delimited token is
     numeric and equal in VALUE (so ``"3"`` finds a clip suffixed ``"_003"``).

Both forms resolve against ``ref``'s model's own clip list ONLY -- re-implementing the engine's
GEO-suffix join (:func:`resolve_idle`'s ``identifier = geoName[4:]``, a clip matches when
``clipName[4:]`` -- both prefixes stripped -- starts with it; the same (group, form-free, token) join
:func:`ff9mapkit.catalog.animations_for_model` uses, but over the model's FULL clip list rather than
just its named movement actions). An unknown ref raises with difflib near-miss hints (or the model's
own clip list, when nothing is close); an ambiguous bare suffix raises naming every candidate.
:func:`render_patch_lines` appends the resolved full clip name as a 4th, whitespace-free
``idle:<clipName>`` token -- and, structurally, NEVER without a preceding ``display`` token.

**Canonicalization law:** friendly names die at the kit boundary -- the engine has no archetype
table, so the emitted token always names the REQUESTED GEO model, never a post-alias donor (the
engine's own loader replays the alias chain at load time; :func:`ff9mapkit.models.extract.resolve_prefab`
documents the chain). ``resolve_display("GEO_MAIN_B0_000")`` stays ``"model:GEO_MAIN_B0_000"`` even
though that id's shipping geometry is actually Zidane's field body (``GEO_MAIN_F0_ZDN``) -- lint
(:func:`validate_blocks`) surfaces that substitution as an INFO note so a playtest isn't a surprise;
the build (``build._emit_folklore``) never bakes the donor in either.

**The build-vs-lint split** (the recurring pattern, both routing through :func:`resolve_display`):
``validate_blocks`` (lint, offline, no install) resolves + additionally runs
:func:`ff9mapkit.models.extract.resolve_prefab` per entry -- ``pgid == -1`` is an ERROR (the id has NO
shipping geometry at all), a donor mismatch is an INFO (named, not blocking). ``build._emit_folklore``
resolves the SAME way but never blocks an entry on a bad display: a resolution failure WARNS and drops
the display token ONLY -- the entry still ships its two-token ``<id> <category>`` line (the kit's
standing fail-safe philosophy, one notch finer-grained than the whole-entry warn-and-skip above).
"""
from __future__ import annotations

import difflib
import re

from .. import archetypes as _archetypes
from .. import catalog as _catalog
from .npc import PRESETS as _CHAR_PRESETS   # vivi/zidane -- the SAME curated presets `archetypes.py` uses

FIRST_FOLKLORE_ID = 80     # 0-79 = real key items (all 7 languages censused empty above 79)
LAST_FOLKLORE_ID = 254     # 255 = FF9FITEM_RARE_NONE (the Key Items screen's empty-list sentinel)
POOL_BASE = 256            # AddItem pool-encode: important id N -> item id 256+N (336-510)

# the ``[[folklore]]`` channel -> overlay-file stem -> in-game surface
CHANNELS = (("name", "imp_name"),   # the Key Items list-row name (required -- a blank row otherwise)
            ("help", "imp_help"),   # the short help line under the list (optional)
            ("lore", "imp_skin"))   # the long "skin" popup lore text (optional)

# the codex categories (the s45 dedicated screen's L1/R1 pages). ``category`` in a [[folklore]] block;
# shipped to the engine via the mod-root ``FolklorePatch.txt`` (line grammar ``<id> <category>``, read
# by FolkloreRegistry low->high across mod folders -- the DictionaryPatch idiom, no registration).
CATEGORIES = ("bestiary", "places", "lore")
DEFAULT_CATEGORY = "lore"


def render_patch_lines(blocks) -> list:
    """The field/mod's ``[[folklore]]`` blocks -> ``FolklorePatch.txt`` lines (``<id> <category>
    [displayRef] [idle:<clipName>]``, ascending by id). A block's ``display`` key (when present) is
    resolved via :func:`resolve_display` and appended as the third token; a block with no ``display``
    (or ``None``) emits the plain two-token line. A block's ``idle`` key is resolved via
    :func:`resolve_idle` and appended as a 4th token ONLY when ``display`` is also present -- the
    nesting is structural, so an ``idle`` alongside no ``display`` is silently never emitted here
    (the lint-time hard error lives in :func:`validate_blocks`; the build's warn-and-drop lives in
    ``build._emit_folklore``). Assumes sanitized blocks (the build warns-and-skips -- including
    dropping an unresolvable ``display``/``idle`` before it ever reaches here; ``validate_blocks``
    reports)."""
    lines = []
    for b in sorted(blocks or [], key=lambda x: _check_band(x.get("id") if isinstance(x, dict) else x)):
        cat = str(b.get("category", DEFAULT_CATEGORY)).strip().lower()
        if cat not in CATEGORIES:
            raise FolkloreError(f"[[folklore]] id {b['id']}: unknown category {b.get('category')!r} "
                                f"(one of {', '.join(CATEGORIES)})")
        line = f"{_check_band(b['id'])} {cat}"
        disp = b.get("display")
        if disp is not None:
            line += f" {resolve_display(disp)}"
            idle = b.get("idle")
            if idle is not None:
                line += f" idle:{resolve_idle(disp, idle)}"
        lines.append(line)
    return lines

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


# ---- displayRef (s46 rung 4: the render-rig kit lane -- see the module docstring for the grammar) ----
_DISPLAY_TOKEN_RE = re.compile(r"^model:GEO_[A-Z0-9_]+$")


def _friendly_geo(name: str):
    """A friendly archetype/creature NAME -> its GEO model name, or ``None`` if ``name`` isn't one (not
    an error yet -- callers fall through to the exact-name/numeric-id path). A local copy of
    ``infohub._model_of_archetype``'s cheap direct-lookup pattern (the SAME two curated tables
    ``[[npc]] archetype =`` resolves against) rather than importing :mod:`infohub` itself, which would
    drag in the prop catalog + the description-comment scraper for one dict lookup; and rather than
    calling :func:`ff9mapkit.archetypes.resolve`, which RAISES on an unknown key (wrong here -- a miss
    must fall through to the next resolution step) and does needless animation-table work on a hit."""
    key = name.strip().lower()
    if key in _CHAR_PRESETS:
        model = _CHAR_PRESETS[key][0]           # vivi=8 / zidane=None (keeps the cloned player's model)
    else:
        spec = _archetypes.ARCHETYPES.get(key) or _archetypes.CREATURES.get(key)
        model = spec["model"] if spec else None
    if model is None:
        return None
    m = _catalog.model(model)
    return m.name if m else None


def resolve_display(ref) -> str:
    """A ``[[folklore]] display = "<ref>"`` value -> the canonical wire token ``"model:GEO_..."`` (the
    ``FolklorePatch.txt`` third column, ``Entry.Display``). See the module docstring for the full
    3-step grammar. Raises :class:`FolkloreError` for a structurally bad ``ref`` (not a string/int,
    empty, embedded whitespace, or a bare ``model:`` with nothing after it) and propagates
    :mod:`ff9mapkit.catalog`'s own ``ValueError`` VERBATIM for an unknown model name/id (difflib
    near-miss hints, ``catalog.resolve_model``) -- never rephrased, so the hint text reaches the
    author unchanged."""
    if isinstance(ref, bool):
        raise FolkloreError(f"display must be a string or an integer GEO id, got {ref!r}")
    if isinstance(ref, int):
        body = str(ref)
    elif isinstance(ref, str):
        s = ref.strip()
        if not s:
            raise FolkloreError("display is empty")
        if any(c.isspace() for c in s):
            raise FolkloreError(f"display {ref!r} must be a single whitespace-free token (a friendly "
                                "name, a GEO_ name, a numeric id, or 'model:GEO_...')")
        body = s[6:].strip() if s[:6].lower() == "model:" else s
        if not body:
            raise FolkloreError(f"display {ref!r} names no model after its 'model:' prefix")
    else:
        raise FolkloreError(f"display must be a string or an integer GEO id, got {ref!r}")

    geo = _friendly_geo(body)
    if geo is None:
        mid = _catalog.resolve_model(body)      # unknown -> ValueError w/ difflib hints, propagated verbatim
        m = _catalog.model(mid)
        geo = m.name if m else None
    if geo is None:                             # pragma: no cover -- defensive: resolve_model already raised
        raise FolkloreError(f"display {ref!r} did not resolve to a model")

    token = f"model:{geo}"
    if not _DISPLAY_TOKEN_RE.fullmatch(token):  # pragma: no cover -- defensive: MODELS names are GEO_[A-Z0-9_]+
        raise FolkloreError(f"internal: resolved display token {token!r} doesn't match "
                            "^model:GEO_[A-Z0-9_]+$ -- the catalog has a non-canonical GEO name")
    return token


def _idle_suffix_matches(clip_name: str, ref: str) -> bool:
    """A bare idle suffix (``'002'`` / ``'2'``) matches ``clip_name`` when it ends with ``'_'`` + the
    literal ``ref`` given (case-insensitive), OR -- zero-pad-aware, for a digit ``ref`` only -- when
    the clip's own trailing ``'_'``-delimited token is itself numeric and equal to ``ref`` in VALUE
    (so ``'2'`` finds a clip suffixed ``'_002'`` without needing to know the model's pad width)."""
    if clip_name.upper().endswith("_" + ref.upper()):
        return True
    if ref.isdigit():
        tail = clip_name.rsplit("_", 1)[-1]
        return tail.isdigit() and int(tail) == int(ref)
    return False


def resolve_idle(display_ref, idle_ref) -> str:
    """A ``[[folklore]] display = "<display_ref>"`` + ``idle = "<idle_ref>"`` pair -> the canonical
    FULL clip name (the ``FolklorePatch.txt`` 4th column, ``idle:<clipName>``). See the module
    docstring for the full grammar. ``display_ref`` is resolved first via :func:`resolve_display`
    (its structural :class:`FolkloreError`\\ s and :mod:`ff9mapkit.catalog`'s own ``ValueError``
    propagate VERBATIM -- ``idle`` is never even considered against a display that doesn't resolve).
    Raises :class:`FolkloreError` for a structurally bad ``idle_ref`` (not a string/int, empty, or
    embedded whitespace), for an unknown ref (difflib near-miss hints, or the model's own clip list
    when nothing is close), and for an ambiguous bare suffix (every matching candidate named)."""
    token = resolve_display(display_ref)        # propagates display errors verbatim; also the canonical geo
    geo = token[len("model:"):]
    identifier = geo[4:]                         # strip 'GEO_' -- the engine's own suffix-join rule

    if isinstance(idle_ref, bool):
        raise FolkloreError(f"idle must be a string or an integer suffix, got {idle_ref!r}")
    if isinstance(idle_ref, int):
        ref = str(idle_ref)
    elif isinstance(idle_ref, str):
        ref = idle_ref.strip()
        if not ref:
            raise FolkloreError("idle is empty")
        if any(c.isspace() for c in ref):
            raise FolkloreError(f"idle {idle_ref!r} must be a single whitespace-free token (a full "
                                "clip name or a bare numeric/literal suffix)")
    else:
        raise FolkloreError(f"idle must be a string or an integer suffix, got {idle_ref!r}")

    # the model's own clip list -- re-implements the engine's GEO-suffix filter (GetAnimationsOfModel)
    # against the kit's own animation DB: identifier = geoName[4:] (strip 'GEO_'), a clip matches when
    # clipName[4:] (strip 'ANH_') starts with it. Deliberately the FULL clip list, not just the named
    # movement actions catalog.animations_for_model narrows to.
    own = {aid: nm for aid, nm in _catalog.ANIMATIONS.items()
           if nm.startswith("ANH_") and nm[4:].startswith(identifier)}
    names = sorted(set(own.values()))
    by_upper = {nm.upper(): nm for nm in names}

    hit = by_upper.get(ref.upper())               # 1) a full clip name, any case
    if hit is not None:
        return hit

    matches = sorted({nm for nm in names if _idle_suffix_matches(nm, ref)})   # 2) a bare suffix
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise FolkloreError(f"idle {idle_ref!r} is ambiguous for {geo} -- matches "
                            f"{', '.join(matches)} (give the full clip name to disambiguate)")

    hints = difflib.get_close_matches(ref.upper(), list(by_upper), n=6, cutoff=0.4)
    if hints:
        extra = f" Did you mean: {', '.join(by_upper[h] for h in hints)}?"
    elif names:
        extra = f" {geo}'s own clips: {', '.join(names)}."
    else:
        extra = f" {geo} has no clips of its own."
    raise FolkloreError(f"unknown idle clip {idle_ref!r} for {geo}.{extra}")


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
        cat = b.get("category", DEFAULT_CATEGORY)
        if not isinstance(cat, str) or cat.strip().lower() not in CATEGORIES:
            problems.append(f"{where} (id {iid}) category must be one of "
                            f"{', '.join(CATEGORIES)} (got {cat!r})")
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
        disp = b.get("display")
        idle = b.get("idle")
        if disp is not None:
            try:
                token = resolve_display(disp)
            except (TypeError, ValueError) as e:               # the catalog near-miss error, verbatim
                problems.append(f"{where} (id {iid}) display {disp!r}: {e}")
            else:
                geo = token[len("model:"):]
                from ..models.extract import resolve_prefab as _resolve_prefab   # offline, baked tables only
                try:
                    resolved_name, pgid, _ptint = _resolve_prefab(geo)
                except (TypeError, ValueError) as e:
                    problems.append(f"{where} (id {iid}) display {disp!r}: {e}")
                else:
                    if pgid == -1:
                        problems.append(
                            f"{where} (id {iid}) display {disp!r} ({geo}): ERROR -- no shipping "
                            "geometry (the id exists in the model table but no prefab ships for it; "
                            "the codex portrait would render nothing, degrading to the text-only pane)")
                    elif resolved_name != geo:
                        problems.append(
                            f"{where} (id {iid}) display {disp!r} ({geo}): INFO -- an alias-only id "
                            f"with no prefab of its own; the engine renders {resolved_name}'s shipping "
                            "geometry instead (automatic substitution, named here so it doesn't "
                            "surprise anyone at playtest)")
                if idle is not None:
                    try:
                        resolve_idle(disp, idle)
                    except (TypeError, ValueError) as e:        # the resolve_idle error, verbatim
                        problems.append(f"{where} (id {iid}) idle {idle!r}: {e}")
        elif idle is not None:
            problems.append(f"{where} (id {iid}) idle {idle!r} needs a display = \"...\" -- idle is "
                            "meaningless without a portrait (ERROR: fix by adding display or removing idle)")
    return problems
