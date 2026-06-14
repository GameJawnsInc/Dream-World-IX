"""Emit a drop-in Memoria ``AbilityFeatures.txt`` from ``[[ability_feature]]`` -- the no-DLL DSL for what
support/active abilities DO: Auto-Haste, killers (Man Eater), MP+20%, Counter, gil-gated casts, command
disables, etc. (Memoria wiki: Supporting-/Active-ability-features.)

The kit emits a PARTIAL file (only the author's ``>SA``/``>AA``/``>CMD`` blocks); the engine reads every mod
folder low->high and accumulates per-ability over the base, so the base supplies the 64 SAs / 192 AAs we don't
touch. We pass the ``[code=...]`` / feature-line body through OPAQUE -- the engine validates the NCalc formula at
load; the kit only STRUCTURE-checks (id range per kind, balanced ``[code]``/``[/code]``, no nested header, known
``[code=TAG]`` for the closed AA/CMD sets, the cumulate/replace merge flag).

Header grammar (the engine regex, ``ff9abil.cs:515``): ``^(>SA|>AA|>CMD)\\s+(\\d+|GlobalEnemyLast|GlobalEnemy|
GlobalLast|Global)(\\+?)`` -- a kind, a numeric id OR a special word, an optional ``+`` (cumulate). ``+`` ADDS
the block on top of the base + lower folders; NO ``+`` CLEARS the lower-priority features for that id first (full
override). Default here is ``cumulate=true`` (the safe partial). Provenance: emits only the author's own blocks;
the SA name<->id table is committed (open-source ``SupportAbility`` enum, reused from :mod:`characterdelta`); AA
names resolve LIVE against the install's ``Actions.csv`` (ships nothing).
"""
from __future__ import annotations

import re

from . import characterdelta as _cd

_KINDS = ("SA", "AA", "CMD")
_SA_MAX, _AA_MAX = 63, 191

# the special-id words -> canonical casing + which kinds they actually ACT for (the engine silently no-ops the
# rest: for >AA/>CMD only "Global" reaches a branch, the other three fall through both -> a dead block).
_SPECIALS = {"global": "Global", "globallast": "GlobalLast",
             "globalenemy": "GlobalEnemy", "globalenemylast": "GlobalEnemyLast"}
_SPECIAL_OK = {"SA": {"Global", "GlobalLast", "GlobalEnemy", "GlobalEnemyLast"},
               "AA": {"Global"}, "CMD": {"Global"}}

# >SA feature-type verbs (a body line's first token) -- structural recognition only (the formula args are opaque).
_SA_FEATURE_KW = ("Permanent", "BattleStart", "BattleResult", "StatusInit", "Ability", "Command",
                  "EnemyFeature", "MorphFeature")
# the CLOSED [code=TAG] sets for >AA / >CMD; a tag outside them is a silent no-op in the engine -> warn (not a
# hard error -- the set could be incomplete, and the formula text is the author's to own).
_AA_TAGS = frozenset({"Condition", "Patch", "Priority", "Power", "HitRate", "Element", "Status",
                      "Target", "SpecialEffect", "GilCost", "MPCost", "ItemRequirement", "Disable"})
_CMD_TAGS = frozenset({"Condition", "Patch", "Disable", "HardDisable"})

_HEADER_RE = re.compile(r"^\s*>(SA|AA|CMD)\b", re.I)
_CODE_OPEN = re.compile(r"\[code=([^\]]*)\]", re.I)
_CODE_CLOSE = re.compile(r"\[/code\]", re.I)
_FILE_HEADER = "# ff9mapkit [[ability_feature]] -- a partial AbilityFeatures.txt (merged per-ability over the base)."


class AbilityFeatureError(ValueError):
    pass


def _as_list(features):
    if features is None:
        return []
    if isinstance(features, dict):
        return [features]
    if isinstance(features, list):
        return features
    raise AbilityFeatureError("[[ability_feature]] must be a table or a list of tables")


def _norm(s) -> str:
    return re.sub(r"[^0-9a-z]", "", str(s).lower())


def _resolve_kind(blk, ctx) -> str:
    k = str(blk.get("kind", "SA")).strip().upper()
    if k not in _KINDS:
        raise AbilityFeatureError(f"{ctx}: kind {blk.get('kind')!r} must be one of SA / AA / CMD")
    return k


def _resolve_cumulate(blk, ctx) -> bool:
    """``cumulate`` (default True) -> the trailing ``+``. ``replace`` is the inverse alias (replace=True ==
    cumulate=False = full override). Both given must agree (cumulate != replace)."""
    cum, rep = blk.get("cumulate"), blk.get("replace")
    if cum is not None and rep is not None:
        if bool(cum) == bool(rep):
            raise AbilityFeatureError(f"{ctx}: cumulate and replace are inverses -- set one, or make them differ")
        return bool(cum)
    if rep is not None:
        return not bool(rep)
    if cum is not None:
        return bool(cum)
    return True                                            # safe partial: stack on top of the base


def _resolve_ability(blk, kind, *, game, strict, ctx):
    """``ability`` -> (header_id_str, display_name). For an AA NAME with strict=False and no install, returns
    (None, name) -- deferred to build (the offline lint can't read Actions.csv)."""
    tok = blk.get("ability")
    if tok is None or isinstance(tok, bool):
        raise AbilityFeatureError(f"{ctx}: needs an 'ability' (a name, an id, or Global/GlobalLast/...)")
    if isinstance(tok, str) and _norm(tok) in _SPECIALS:   # a special-id word
        word = _SPECIALS[_norm(tok)]
        if word not in _SPECIAL_OK[kind]:
            raise AbilityFeatureError(f"{ctx}: '{word}' has no effect for >{kind} (only "
                                      f"{'/'.join(sorted(_SPECIAL_OK[kind]))} act; the engine ignores the rest)")
        return word, word
    _is_int = isinstance(tok, int) or (isinstance(tok, str) and tok.strip().lstrip("-").isdigit())
    if kind == "SA":
        if _is_int:
            aid = int(tok)
            if not 0 <= aid <= _SA_MAX:
                raise AbilityFeatureError(f"{ctx}: SA id {aid} out of range (0-{_SA_MAX})")
            return str(aid), _cd._SA_NAMES[aid]
        aid = _cd._SA_BY_NORM.get(_cd._norm_sa(tok))
        if aid is None:
            raise AbilityFeatureError(f"{ctx}: unknown SupportAbility {tok!r} (a name like 'Auto-Haste', "
                                      f"or a 0-{_SA_MAX} id)")
        return str(aid), _cd._SA_NAMES[aid]
    if kind == "CMD":
        if _is_int:
            cid = int(tok)
            if cid < 1:
                raise AbilityFeatureError(f"{ctx}: CMD id {cid} invalid (id 0 no-ops; use a command id >= 1)")
            return str(cid), str(cid)
        raise AbilityFeatureError(f"{ctx}: CMD is id-only (give an int command id, not a name {tok!r})")
    # kind == "AA"
    if _is_int:
        aid = int(tok)
        if not 0 <= aid <= _AA_MAX:
            raise AbilityFeatureError(f"{ctx}: AA id {aid} out of range (0-{_AA_MAX})")
        return str(aid), str(aid)
    if not strict and game is None:
        return None, str(tok)                              # AA-by-name defers to build (needs Actions.csv)
    from . import actiondelta as _ad
    try:
        _opt, _leg, cols, rows = _ad._read_raw(_ad._csv_path("Actions.csv", game))
        aid = _ad._resolve_id(tok, rows, _ad._name_index(rows, cols), kind="ability_feature", max_id=_AA_MAX)
    except _ad.ActionDeltaError as ex:
        raise AbilityFeatureError(f"{ctx}: {ex}")
    except (FileNotFoundError, OSError, RuntimeError) as ex:
        raise AbilityFeatureError(f"{ctx}: AA-by-name needs your FF9 install to read Actions.csv ({ex})")
    return str(aid), str(tok)


def _features_text(blk, ctx) -> str:
    present = [k for k in ("features", "code", "body") if blk.get(k) is not None]
    if not present:
        raise AbilityFeatureError(f"{ctx}: needs a 'features' block (the [code=...] / feature-line body)")
    if len(present) > 1:
        raise AbilityFeatureError(f"{ctx}: set only one of features/code/body (got {', '.join(present)})")
    v = blk[present[0]]
    if not isinstance(v, str):
        raise AbilityFeatureError(f"{ctx}: '{present[0]}' must be a string")
    return v


def _check_body(body, kind, ctx, warnings) -> None:
    if not body.strip():
        raise AbilityFeatureError(f"{ctx}: empty 'features' body (a header with no feature patches nothing)")
    lines = body.splitlines()
    for ln in lines:                                       # (d) a body line that is itself a header would split blocks
        if _HEADER_RE.match(ln):
            raise AbilityFeatureError(f"{ctx}: a body line is itself a >SA/>AA/>CMD header ({ln.strip()!r}) -- "
                                      f"use ONE [[ability_feature]] per header")
    toks = sorted([(m.start(), 1) for m in _CODE_OPEN.finditer(body)]      # (e) [code]/[/code] balance + no nesting
                  + [(m.start(), -1) for m in _CODE_CLOSE.finditer(body)])
    depth = 0
    for _pos, d in toks:
        depth += d
        if depth < 0 or depth > 1:
            raise AbilityFeatureError(f"{ctx}: unbalanced or nested [code=...]/[/code] tags")
    if depth != 0:
        raise AbilityFeatureError(f"{ctx}: unbalanced [code=...]/[/code] tags (a [code=...] without [/code])")
    for m in re.finditer(r"\[code=.*?\[/code\]", body, re.DOTALL):   # the engine [code] regex is NOT multiline ->
        if "\n" in m.group(0):                             # a [code=...] spanning lines is silently ignored
            warnings.append(f"{ctx}: a [code=...]...[/code] spans multiple lines -- the engine's [code] regex is "
                            f"NOT multiline and will IGNORE it; keep each [code=...] block on one line")
            break
    if kind in ("AA", "CMD"):                              # (g) closed tag set -> warn on an unknown / cross-kind tag
        allowed = _AA_TAGS if kind == "AA" else _CMD_TAGS
        other_kind, other_set = ("CMD", _CMD_TAGS) if kind == "AA" else ("AA", _AA_TAGS)
        for m in _CODE_OPEN.finditer(body):
            tag = m.group(1).strip()
            if tag and tag not in allowed:
                hint = f" (it's a >{other_kind} tag)" if tag in other_set else ""
                warnings.append(f"{ctx}: [code={tag}] is not a known >{kind} feature tag{hint} -- the engine "
                                f"silently ignores an unknown tag")
    elif kind == "SA":                                     # (f) first body line should be a feature verb (lenient)
        first = next((ln.strip() for ln in lines if ln.strip()), "")
        first_tok = first.split(None, 1)[0] if first else ""   # exact token (no prefix false-accept like "Abilityx")
        if first_tok not in _SA_FEATURE_KW:
            warnings.append(f"{ctx}: a >SA body should start with a feature type "
                            f"({' / '.join(_SA_FEATURE_KW)}); got {first_tok!r}")


def _resolve_comment(blk, default_name, ctx) -> str:
    c = blk.get("comment")
    if c is None:
        return str(default_name)
    return re.sub(r"\s+", " ", str(c)).strip()             # the engine ignores the tail, but keep it one line


def _emit_block(blk, n, *, game, strict, warnings, seen) -> list:
    ctx = f"[[ability_feature]] #{n}"
    if not isinstance(blk, dict):
        raise AbilityFeatureError(f"{ctx} must be a table")
    kind = _resolve_kind(blk, ctx)
    cumulate = _resolve_cumulate(blk, ctx)
    id_str, display = _resolve_ability(blk, kind, game=game, strict=strict, ctx=ctx)
    if kind == "AA" and id_str == "0":
        warnings.append(f"{ctx}: >AA id 0 is Void (a no-op active ability) -- this block won't apply")
    has_body = any(blk.get(k) is not None for k in ("features", "code", "body"))
    body = _features_text(blk, ctx) if has_body else ""
    if body.strip():
        _check_body(body, kind, ctx, warnings)
    elif cumulate:                                         # a `+` header with no features patches nothing
        raise AbilityFeatureError(f"{ctx}: empty 'features' -- a cumulate (+) header with no body patches "
                                  f"nothing; add a feature body, or set replace=true to CLEAR the ability's "
                                  f"base features")
    # else: empty body + replace (no `+`) = a legitimate "clear all lower-priority features" override (header only)
    if id_str is not None:                                 # a 2nd block for the same id with replace WIPES the first
        key = (kind, id_str)
        if key in seen and not cumulate:
            warnings.append(f"{ctx}: a 2nd >{kind} {id_str} with replace/no-cumulate WIPES the earlier block")
        seen[key] = n
    comment = _resolve_comment(blk, display, ctx)
    header = f">{kind} {id_str if id_str is not None else display}" + ("+" if cumulate else "")
    if comment:
        header += " " + comment
    # STRIP each line (not just rstrip): a >SA feature verb must sit at column 0 -- the engine matcher `^verb\b`
    # is Multiline but does NOT consume leading whitespace, so an indented verb is silently dropped. Indentation
    # is never meaningful in this DSL (the [code=...] regex is position-free), so normalizing is safe.
    body_lines = [ln.strip() for ln in body.splitlines()]
    while body_lines and not body_lines[0]:
        body_lines.pop(0)
    while body_lines and not body_lines[-1]:
        body_lines.pop()
    return [header, *body_lines, ""]


def build_lines(features, *, game=None, strict=True):
    """``[[ability_feature]]`` blocks -> (lines, warnings). Offline for SA/CMD-id + AA-id; an AA NAME needs the
    install (``game``) -- with ``strict=False`` + no install it structure-checks and defers id resolution."""
    blocks = _as_list(features)
    if not blocks:
        return [], []
    warnings, seen, out = [], {}, [_FILE_HEADER, ""]
    for n, blk in enumerate(blocks):
        out += _emit_block(blk, n, game=game, strict=strict, warnings=warnings, seen=seen)
    return out, warnings


def validate_blocks(features, *, game=None) -> list:
    """Offline structural + range problems (empty => OK). Re-runs emission on a copy; AA-by-name id resolution
    defers to build (install-gated), like ``[[battle_attack]]``'s by-name path."""
    try:
        build_lines(features, game=game, strict=False)
    except AbilityFeatureError as ex:
        return [str(ex)]
    return []


def write_ability_features(layout, features, *, game=None) -> list:
    """Build + write ``layout.ability_features_txt`` (cp1252 / LF, byte-faithful with the base). Returns
    warnings; writes nothing when there are no blocks."""
    lines, warnings = build_lines(features, game=game, strict=True)
    if not lines:
        return warnings
    path = layout.ability_features_txt
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="cp1252", errors="replace", newline="\n")
    return warnings


# ---- non-clobbering merge into a live AbilityFeatures.txt (deferred -- the MVP deploy whole-file-copies) ----
def _markers(marker_id):
    return (f"## >>> ff9mapkit ability_feature {marker_id} (auto -- edit the toml, not here)",
            f"## <<< ff9mapkit ability_feature {marker_id}")


def merge_ability_features(live_text: str, block_lines, marker_id) -> str:
    """Splice ``block_lines`` between ``##`` sentinel markers, replacing a prior same-id block + preserving the
    rest. ``##`` lines don't start with ``>SA/>AA/>CMD`` so the engine skips them. Idempotent; an empty
    ``block_lines`` just strips our prior block."""
    begin, end = _markers(marker_id)
    kept, skip = [], False
    for ln in live_text.splitlines():
        if ln.strip() == begin:
            skip = True
            continue
        if ln.strip() == end:
            skip = False
            continue
        if not skip:
            kept.append(ln)
    while kept and not kept[-1].strip():
        kept.pop()
    if block_lines:
        kept += ["", begin, *block_lines, end]
    return "\n".join(kept) + "\n"
