"""Move a campaign's field ids -- the refactor the kit could not previously do.

A member's field id is MATERIALIZED, not derived: ``assign_ids`` computes ``id_base + i`` exactly once
at fork time and :func:`campaign.write_campaign` bakes the result into the manifest AND into the member's
own ``field.toml``, plus every door that names it. Nothing recomputes it afterwards -- which is what makes
a campaign stable, and also what makes moving one a hand edit across N+1 files (~5 numbers per member) with
no verification anywhere that all of them landed. The kit's own comments record the absence as deliberate
("ids are next-free (never renumbered -- a renumber would have to rewrite every member's retargeted
gateways)", :mod:`campaign`) -- this is that work, done once, in one transaction.

**It is a pure TEXT refactor.** The shipped ``.eb``/``.bin`` sidecars are RAW DONOR BYTES; their
``Field()`` destinations are remapped at BUILD time from the ``[verbatim_eb] retarget`` table
(:func:`ff9mapkit.content.verbatim.verbatim_eb`), so there is no bytecode to patch -- only TOML.

**It rewrites text surgically, never by re-rendering.** ``campaign.render_campaign_toml`` and
``editor.model.dumps`` both regenerate a file from a parsed model and drop hand-written comments
(``editor/model.py`` says so outright). A forked member toml is dense with generated AND authored
commentary -- exactly the notes an author needs when a 40-field campaign moves band -- so every edit here
replaces the numeric token in place and leaves every other byte alone.

**Two implementations must agree before anything is written.** :func:`_semantic_apply` computes the
expected post-move document as a pure dict transform; the surgical rewriter produces new TEXT; the text is
re-parsed and must equal the expected dict. A regex that matched too much or too little fails there rather
than in-game. Then a RESIDUAL SCAN re-reads every toml for any leftover old id, so a site this module does
not know about is reported rather than shipped.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field as _dcfield
from pathlib import Path

from . import campaign as _campaign
from . import fsutil

# --- what a value at a given (section path, key) MEANS -----------------------------------
SCALAR = "scalar"            # the whole value is one of OUR field ids
TABLE_VALUES = "table"       # an INLINE table {<donor real id> = <our fork id>} -- VALUES only
SECTION_VALUES = "section"   # a [a.b] table written long-form: every row's VALUE is one of ours

# The member field.toml sites. KEYS of a retarget table are DONOR real ids and must never move; only the
# values are ours. `text_block` is handled per-member (see _member_rules): it moves ONLY when it equals the
# member's own old id, because an explicit block that differs is the DONOR's real mesID, which a fork keeps
# (voice acting + dual-language key off it) -- build.default_text_block is identity, so an ABSENT text_block
# follows the id for free and needs no edit at all.
MEMBER_RULES = {
    (("field",), "id"): SCALAR,
    (("gateway",), "to"): SCALAR,
    (("verbatim_eb",), "retarget"): TABLE_VALUES,
    (("verbatim_eb", "retarget"), None): SECTION_VALUES,
    (("gateway_carry",), "retarget"): TABLE_VALUES,
    (("gateway_carry", "retarget"), None): SECTION_VALUES,
    (("ladder",), "top_field"): SCALAR,          # navigable ladder destination (build.py:1611-1614)
    (("cutscene",), "then_warp"): SCALAR,        # auto-return destination, "must be a field id" (build.py:2654)
    # [[logic_edit]] `new` is OURS but ONLY when kind="field"; `old` is the DONOR literal standing in the
    # donor .eb and must never move (logic_edit.py:115). The kind gate is not optional: for kind="gil" or
    # "flag_index" the SAME key holds a gil amount or a flag index, and the custom id band overlaps both --
    # so an unconditional rewrite would corrupt an unrelated number that merely looks like one of our ids.
    (("logic_edit",), "new"): SCALAR,
}
MANIFEST_RULES = {
    (("field",), "id"): SCALAR,
}

_HEADER = re.compile(r"^\s*\[\[?\s*(?P<path>[^\]]+?)\s*\]\]?\s*(?:#.*)?$")
_INT_KV = re.compile(r"^(?P<pre>\s*(?P<key>[A-Za-z_][A-Za-z0-9_\-]*)\s*=\s*)"
                     r"(?P<val>-?\d+)(?P<post>\s*(?:#.*)?)$")
_NUM_KV = re.compile(r"^(?P<pre>\s*(?P<key>\"?\d+\"?)\s*=\s*)(?P<val>-?\d+)(?P<post>\s*(?:#.*)?)$")
# an inline table of int=int pairs on ONE line (what content.verbatim.render_retarget emits). `#` is
# excluded from the body so a trailing comment can never be swallowed into it.
_TBL_KV = re.compile(r"^(?P<pre>\s*(?P<key>[A-Za-z_][A-Za-z0-9_\-]*)\s*=\s*\{)"
                     r"(?P<body>[^{}#]*)(?P<post>\}\s*(?:#.*)?)$")
_TBL_PAIR = re.compile(r"(?P<pre>\"?-?\d+\"?\s*=\s*)(?P<val>-?\d+)")


class ReidError(ValueError):
    """A refusal: an unsafe target band, a collision, or a rewrite that could not be verified."""


@dataclass
class Edit:
    path: Path
    before: str
    after: str
    changes: list = _dcfield(default_factory=list)   # human-readable "what moved" lines


@dataclass
class ReidPlan:
    campaign_path: Path
    remap: dict                                       # old our-id -> new our-id (only ids that MOVE)
    edits: list = _dcfield(default_factory=list)
    warnings: list = _dcfield(default_factory=list)
    followups: list = _dcfield(default_factory=list)
    residual: list = _dcfield(default_factory=list)   # old ids still present after the rewrite

    @property
    def moved(self) -> int:
        return len(self.remap)


def _section_of(line: str, cur: tuple) -> tuple:
    """The section path a header line opens, else ``cur`` unchanged. ``[[a]]`` and ``[a]`` collapse to the
    same path: an array-of-tables and a table address the same key namespace for our purposes."""
    m = _HEADER.match(line)
    if not m:
        return cur
    return tuple(p.strip().strip('"').strip("'") for p in m.group("path").split("."))


def _rule_for(rules, section: tuple, key: str):
    """The rule for (section, key): an exact (path, key) match, else a (path, None) whole-section rule."""
    if (section, key) in rules:
        return rules[(section, key)]
    return rules.get((section, None))


def rewrite_text(text: str, rules: dict, remap: dict, *, key_remaps=None,
                 index_filter=None) -> "tuple[str, list, list]":
    """Rewrite every OUR-id occurrence the rules point at, in place. Returns (new_text, changes, skipped).

    ``key_remaps`` overrides ``remap`` for specific ``(section, key)`` sites -- how ``text_block`` is limited
    to a member's own id. A value not present in the applicable map is LEFT ALONE: it is a donor id, a real
    field, or a door out of this campaign, and moving it would be the corruption this verb exists to avoid.

    ``skipped`` records a targeted site whose value did not match the strict int / inline-table shapes --
    reported, never silently passed over, because a shape this cannot rewrite is a shape it cannot verify.
    """
    key_remaps = key_remaps or {}
    index_filter = index_filter or {}
    out, changes, skipped = [], [], []
    section: tuple = ()
    aot_n: dict = {}                                  # array-of-tables path -> index of the CURRENT block

    def _blocked(sec, key):
        """True when a rule is limited to certain [[block]] indices and this is not one of them."""
        allowed = index_filter.get((sec, key))
        return allowed is not None and aot_n.get(sec, 0) not in allowed

    for lineno, line in enumerate(text.splitlines(keepends=True), 1):
        body = line.rstrip("\r\n")
        nl = line[len(body):]
        stripped = body.lstrip()
        if stripped.startswith("#") or not stripped:      # a comment is prose: never rewritten
            out.append(line)
            continue
        if _HEADER.match(body):
            section = _section_of(body, section)
            if stripped.startswith("[["):
                aot_n[section] = aot_n.get(section, -1) + 1
            out.append(line)
            continue

        m = _INT_KV.match(body)
        if m:
            rule = _rule_for(rules, section, m.group("key"))
            if rule == SCALAR and not _blocked(section, m.group("key")):
                use = key_remaps.get((section, m.group("key")), remap)
                old = int(m.group("val"))
                if old in use:
                    new = use[old]
                    out.append(f"{m.group('pre')}{new}{m.group('post')}{nl}")
                    changes.append(f"{'.'.join(section)}.{m.group('key')}: {old} -> {new}")
                    continue
            out.append(line)
            continue

        m = _NUM_KV.match(body)                            # a long-form retarget row: 300 = 6000
        if m and _rule_for(rules, section, None) == SECTION_VALUES:
            old = int(m.group("val"))
            if old in remap:
                new = remap[old]
                out.append(f"{m.group('pre')}{new}{m.group('post')}{nl}")
                changes.append(f"{'.'.join(section)}: {m.group('key')} -> {new} (was {old})")
                continue
            out.append(line)
            continue

        m = _TBL_KV.match(body)
        if m and _rule_for(rules, section, m.group("key")) == TABLE_VALUES:
            hits = []

            def _sub(pm):
                old = int(pm.group("val"))
                if old in remap:
                    hits.append((old, remap[old]))
                    return f"{pm.group('pre')}{remap[old]}"
                return pm.group(0)

            new_body = _TBL_PAIR.sub(_sub, m.group("body"))
            if hits:
                out.append(f"{m.group('pre')}{new_body}{m.group('post')}{nl}")
                changes.append(f"{'.'.join(section)}.{m.group('key')}: "
                               + ", ".join(f"{a}->{b}" for a, b in hits))
                continue
            out.append(line)
            continue

        # a site we were told to rewrite whose value is not a plain int / inline int-table
        key = body.split("=", 1)[0].strip() if "=" in body else None
        if key and _rule_for(rules, section, key) in (SCALAR, TABLE_VALUES):
            skipped.append(f"line {lineno}: {'.'.join(section)}.{key} -- value is not a plain integer or "
                           f"an inline table of integers, so it was left alone: {body.strip()[:80]}")
        out.append(line)
    return "".join(out), changes, skipped


def _semantic_apply(doc, rules: dict, remap: dict, *, key_remaps=None, section: tuple = (),
                    index_filter=None, index: int = 0) -> dict:
    """The SAME transformation as :func:`rewrite_text`, computed as a pure dict transform. The rewritten
    TEXT must re-parse to exactly this -- two independent implementations agreeing is what makes a regex
    edit trustworthy on a file the author hand-annotated."""
    key_remaps = key_remaps or {}
    index_filter = index_filter or {}
    if isinstance(doc, list):
        return [_semantic_apply(v, rules, remap, key_remaps=key_remaps, section=section,
                                index_filter=index_filter, index=i) for i, v in enumerate(doc)]
    if not isinstance(doc, dict):
        return doc
    out = {}
    for k, v in doc.items():
        rule = _rule_for(rules, section, k)
        allowed = index_filter.get((section, k))
        if rule == SCALAR and allowed is not None and index not in allowed:
            out[k] = v
        elif rule == SCALAR and isinstance(v, int) and not isinstance(v, bool):
            out[k] = key_remaps.get((section, k), remap).get(v, v)
        elif rule == TABLE_VALUES and isinstance(v, dict):
            out[k] = {dk: (remap.get(dv, dv) if isinstance(dv, int) and not isinstance(dv, bool) else dv)
                      for dk, dv in v.items()}
        elif isinstance(v, (dict, list)):
            sub = section + (k,)
            if _rule_for(rules, sub, None) == SECTION_VALUES and isinstance(v, dict):
                out[k] = {dk: (remap.get(dv, dv) if isinstance(dv, int) and not isinstance(dv, bool) else dv)
                          for dk, dv in v.items()}
            else:
                out[k] = _semantic_apply(v, rules, remap, key_remaps=key_remaps, section=sub,
                                         index_filter=index_filter)
        else:
            out[k] = v
    return out


def _edit_for(path: Path, rules: dict, remap: dict, *, key_remaps=None,
              index_filter=None) -> "tuple[Edit, list]":
    """Rewrite one file and PROVE the rewrite: the new text must re-parse to the semantically-expected
    document. A mismatch raises rather than writes."""
    # newline="" -> NO universal-newline translation. The default would fold a CRLF file (which is what a
    # git checkout hands you under autocrlf) to LF in memory, and writing it back would rewrite every line
    # ending in the file -- a three-number edit showing up as a whole-file diff.
    before = path.read_text(encoding="utf-8", newline="")
    doc = tomllib.loads(before)
    after, changes, skipped = rewrite_text(before, rules, remap, key_remaps=key_remaps,
                                           index_filter=index_filter)
    expected = _semantic_apply(doc, rules, remap, key_remaps=key_remaps, index_filter=index_filter)
    try:
        got = tomllib.loads(after)
    except tomllib.TOMLDecodeError as ex:                 # the rewrite broke the file -- never write it
        raise ReidError(f"{path}: the id rewrite produced invalid TOML ({ex}). No file was written.") from ex
    if got != expected:
        raise ReidError(
            f"{path}: the surgical rewrite disagrees with the expected result, so nothing was written. "
            f"This means a value was matched that should not have been (or missed). Report it with the "
            f"file -- reid refuses rather than guess.")
    return Edit(path=path, before=before, after=after, changes=changes), skipped


# --- planning -----------------------------------------------------------------------------
# Keys whose value is an integer in the same numeric range as a field id but is NOT one. The residual scan
# would otherwise flag them: the custom id band (4000-9899) OVERLAPS the story-flag band (8712+), so a
# [[flag]] index can equal an old field id by coincidence.
_NOT_A_FIELD_ID = frozenset({
    # flags: the custom id band (4000-9899) OVERLAPS the story-flag band (8712+)
    "index", "flag", "set_flag", "requires_flag", "requires_flag_clear", "flag_base", "flags_per_field",
    # ScenarioCounter beats span 0..32767 -- the ENTIRE field-id range
    "scenario", "scenario_min", "scenario_max", "requires_scenario", "set_scenario",
    # WORLD COORDINATES are routinely 4-5 digits: a campaign at 6000-6039 sits squarely inside the x/z
    # range of an ordinary room, and a walkmesh has no id to validate against
    "x", "y", "z", "pos", "start", "radius", "zone", "poly", "arrive", "act_hop_to", "top", "bottom",
    "top_worldmap", "act_hop", "offset", "height", "width", "dist", "range",
    # donor-side ids and non-id ordinals
    "area", "entrance", "region_key", "song", "model", "anim", "source", "source_field", "donor",
    "donor_tag", "donor_entry", "battle", "id_base", "item", "count", "gil", "ap", "template",
    "borrow_tcb", "scene",
    # NOT excluded on purpose: `id` (a stray [[mint]] id false positive is a far better trade than
    # blinding the net to a [field] id or a floorplan rooms[].id the rules failed to move), and
    # `to_real` -- a seam target is donor-by-default but CAN hold a sibling campaign's fork id, which
    # reid must never rewrite silently and must therefore surface for a human to judge.
})


def _parse_mapping(pairs) -> dict:
    """``--map 6000=6500 --map 6001=6501`` -> ``{6000: 6500, 6001: 6501}``."""
    out = {}
    for raw in pairs or ():
        if "=" not in str(raw):
            raise ReidError(f"--map wants <old>=<new> (got {raw!r})")
        a, b = str(raw).split("=", 1)
        try:
            out[int(a)] = int(b)
        except ValueError as ex:
            raise ReidError(f"--map wants integers (got {raw!r})") from ex
    return out


def _validate_targets(plan, remap: dict, reserved) -> None:
    """Refuse a move that cannot work, BEFORE any file is touched."""
    from .coop import COOP_FIELD, COOP_MOD
    from .journey import WORLD_ID_HI, WORLD_ID_LO
    # The co-op room is registered from its OWN folder, which is deliberately absent from Memoria.ini
    # FolderNames ("never touched by campaign redeploys") -- so the live-registration sweep structurally
    # CANNOT see it and a scratch-band move onto it would pass every gate the kit has.
    reserved = set(reserved or ()) | {COOP_FIELD}
    keep = [m.new_id for m in plan.members if m.new_id not in remap]
    final = sorted(keep + list(remap.values()))
    bad = sorted({i for i in remap.values() if not (4000 <= i <= 32767)})
    if bad:
        raise ReidError(f"target ids {bad} are outside the custom band -- must be 4000-32767 (the live "
                        f"fldMapNo is Int16, so a higher id registers but is unreachable).")
    hole = sorted({i for i in remap.values() if WORLD_ID_LO <= i <= WORLD_ID_HI})
    if hole:
        raise ReidError(f"target ids {hole} land in the engine-RESERVED world-map hole {WORLD_ID_LO}-"
                        f"{WORLD_ID_HI} (EVT_WORLD_WORLD00..12) -- a FieldScene there clobbers the world-map "
                        f"scripts. Pick a base that clears it.")
    dups = sorted({i for i in final if final.count(i) > 1})
    if dups:
        raise ReidError(f"the move collides inside the campaign: ids {dups} would be held by two members. "
                        f"EventDB/SceneData are global dicts -- a shared id loads the wrong .eb (black screen).")
    clash = sorted(set(remap.values()) & reserved)
    if clash:
        why = (f" ({COOP_FIELD} is the co-op room in the {COOP_MOD} folder, which the live sweep cannot see)"
               if COOP_FIELD in clash else "")
        raise ReidError(f"target ids {clash} are already registered elsewhere{why} -- pick a clear band. "
                        f"EventDB is GLOBAL across mod folders, so a collision in another folder is still "
                        f"a collision.")


def live_reserved(game, *, own_folder=None) -> "tuple[set, list]":
    """``(ids, folders)`` -- every field id the LIVE stacked mod folders currently register, minus the ones
    registered ONLY by this campaign's own folder (those are the ids we are moving OFF, not obstacles).

    The live DictionaryPatch stack is the only truth about what is registered; EventDB is GLOBAL across
    folders, so a collision in an unrelated folder is still the null-.eb black screen. ``folders == []``
    means the stack could not be read -- :func:`deploylog.registrations` is explicit that a caller must then
    conclude NOTHING, so we return an empty set and let the caller say the check did not run.
    """
    from . import deploylog
    reg, folders = deploylog.registrations(game)
    if not folders:
        return set(), []
    ids = {fid for fid, kinds in reg.items()
           if not (own_folder and set(kinds.values()) == {own_folder})}
    return ids, folders


def plan_reid(campaign_path, *, id_base=None, mapping=None, reserved_ids=None,
              skip_lint=False) -> ReidPlan:
    """Resolve a move into the exact set of file edits -- verified, but not yet written.

    ``id_base`` shifts every member by one delta, PRESERVING GAPS: a removed member leaves a hole and
    ``campaign._next_member_id`` is max+1, so compacting would silently reuse a retired id -- the one number
    a stale save must never land on. ``mapping`` moves only the ids named.

    Lints FIRST. A campaign whose manifest and member tomls already disagree cannot be moved safely, because
    reid would faithfully carry the disagreement into a new band; ``lint_campaign`` (e3) is that check.
    """
    campaign_path = Path(campaign_path)
    plan = _campaign.load_campaign(campaign_path)
    root = campaign_path.parent
    if not plan.members:
        raise ReidError(f"{campaign_path}: campaign has no [[field]] members to move")
    if not skip_lint:
        errors, _w = _campaign.lint_campaign(plan, root)
        if errors:
            raise ReidError("this campaign does not lint clean, so a move would carry the problem into a new "
                            "band instead of fixing it. Resolve these first (or --skip-lint to move anyway):"
                            "\n  - " + "\n  - ".join(errors))

    olds = [m.new_id for m in plan.members]
    if mapping:
        remap = _parse_mapping(mapping)
        unknown = sorted(set(remap) - set(olds))
        if unknown:
            raise ReidError(f"--map names ids {unknown} that are not members of this campaign "
                            f"(members: {min(olds)}..{max(olds)})")
    elif id_base is not None:
        delta = int(id_base) - min(olds)
        remap = {o: o + delta for o in olds}
    else:
        raise ReidError("give --id-base <N> (shift the whole campaign) or --map <old>=<new> (move some ids)")
    remap = {o: n for o, n in remap.items() if o != n}          # a no-op id is not an edit
    if not remap:
        raise ReidError("that move is a no-op -- every id already has the requested value.")
    _validate_targets(plan, remap, reserved_ids)

    rp = ReidPlan(campaign_path=campaign_path, remap=remap)
    new_base = min([m.new_id for m in plan.members if m.new_id not in remap] + list(remap.values()))
    man_rules = dict(MANIFEST_RULES)
    man_keys = {}
    if plan.id_base != new_base:                                 # id_base is the ALLOCATION seed, not an id
        man_rules[(("campaign",), "id_base")] = SCALAR
        man_keys[(("campaign",), "id_base")] = {plan.id_base: new_base}
    edit, skipped = _edit_for(campaign_path, man_rules, remap, key_remaps=man_keys)
    rp.edits.append(edit)
    rp.warnings += [f"{campaign_path.name}: {s}" for s in skipped]

    for m in plan.members:
        mpath = root / m.toml_rel
        if not mpath.is_file():
            raise ReidError(f"member {m.name}: field.toml not found at {mpath} -- nothing was written.")
        # text_block moves ONLY when it is this member's OWN id. An explicit block that DIFFERS is the
        # donor's real mesID, which a fork KEEPS (voice acting + dual language key off it). An ABSENT
        # text_block needs no edit: build.default_text_block is identity, so it follows the new id for free.
        rules = dict(MEMBER_RULES)
        rules[(("field",), "text_block")] = SCALAR
        keyed = {(("field",), "text_block"): {m.new_id: remap[m.new_id]} if m.new_id in remap else {}}
        # [[logic_edit]] `new` is a field id ONLY on a kind="field" row -- elsewhere the same key holds a
        # gil amount / flag index / txid, any of which can numerically equal one of our old ids.
        raw = tomllib.loads(mpath.read_text(encoding="utf-8"))
        idxf = {(("logic_edit",), "new"): {i for i, le in enumerate(raw.get("logic_edit", []) or [])
                                           if isinstance(le, dict) and le.get("kind") == "field"}}
        edit, skipped = _edit_for(mpath, rules, remap, key_remaps=keyed, index_filter=idxf)
        rp.edits.append(edit)
        rp.warnings += [f"{m.name}: {s}" for s in skipped]

    fp = _floorplan_edit(root, remap)      # a click-authored dungeon's plan holds the ids too
    if fp is not None:
        rp.edits.append(fp)

    rp.residual = _residual_scan(root, rp)
    rp.followups = _followups(plan, rp)
    return rp


def _floorplan_edit(root: Path, remap: dict) -> "Edit | None":
    """``floorplan.json`` is the SOURCE OF TRUTH for a click-authored dungeon -- it carries ``id_base`` and
    each ``rooms[].id``. Leave it behind and the very next Compose re-emits the campaign at the OLD ids,
    silently undoing the move. It is machine-written (``json.dumps(indent=2)``, floorplan.py:1862) and JSON
    cannot carry comments, so a round-trip loses nothing."""
    import json
    p = root / "floorplan.json"
    if not p.is_file():
        return None
    before = p.read_text(encoding="utf-8", newline="")     # newline="" -> keep CRLF/LF exactly as found
    try:
        doc = json.loads(before)
    except ValueError:
        return None

    changes = []

    def _sub(m):
        old = int(m.group("val"))
        if old in remap:
            changes.append(f'"{m.group("key")}": {old} -> {remap[old]}')
            return f'{m.group("pre")}{remap[old]}'
        return m.group(0)

    # Only a value that IS one of our old ids is touched, so no other "id"-named key can be caught: a
    # number in `remap` is by construction a field id this campaign owns.
    after = re.sub(r'(?P<pre>"(?P<key>id|id_base)"\s*:\s*)(?P<val>\d+)', _sub, before)
    if not changes:
        return None
    expect = json.loads(before)
    expect["id_base"] = remap.get(expect.get("id_base"), expect.get("id_base"))
    for r in expect.get("rooms", []) or []:
        if isinstance(r, dict) and isinstance(r.get("id"), int):
            r["id"] = remap.get(r["id"], r["id"])
    if json.loads(after) != expect:
        raise ReidError(f"{p}: the floorplan.json rewrite disagrees with the expected result -- nothing "
                        f"was written. Report it with the file; reid refuses rather than guess.")
    return Edit(path=p, before=before, after=after, changes=changes)


def _residual_scan(root: Path, rp: ReidPlan) -> list:
    """Is any OLD id still written anywhere in the campaign tree after the rewrite? This is the net under the
    rule table: a site this module does not model gets REPORTED rather than silently shipped. Keys holding a
    same-range integer that is not a field id are excluded (the custom band overlaps the flag band)."""
    news = {e.path: e.after for e in rp.edits}
    olds = set(rp.remap)
    hits = []
    # .json too: floorplan.json and the Trace lane's <stem>.trace.json both carry our ids, and a cache that
    # still names an old id will quietly re-emit it on the next compose.
    for p in sorted(list(root.rglob("*.toml")) + list(root.rglob("*.json"))):
        text = news.get(p)
        if text is None:
            try:
                text = p.read_text(encoding="utf-8")
            except OSError:
                continue
        sep = ":" if p.suffix == ".json" else "="            # JSON is `"key": v`, TOML is `key = v`
        for n, line in enumerate(text.splitlines(), 1):
            s = line.strip()
            if s.startswith("#") or sep not in s:
                continue
            key = s.split(sep, 1)[0].strip().strip('"')
            if key in _NOT_A_FIELD_ID or key.isdigit():          # a retarget row's KEY is a donor id
                continue
            rhs = s.split(sep, 1)[1].split("#", 1)[0] if sep == "=" else s.split(sep, 1)[1]
            if any(int(v) in olds for v in re.findall(r"-?\d+", rhs)):
                hits.append(f"{p.relative_to(root)}:{n}: {s[:90]}")
    return hits


def _followups(plan, rp: ReidPlan) -> list:
    """What reid CANNOT fix, because it lives outside the campaign directory. Being explicit is the point --
    the ids in a deployed folder, a journey manifest and a save file are not this verb's to move."""
    lo, hi = min(rp.remap.values()), max(rp.remap.values())
    return [
        f"REDEPLOY -- the live mod folder ({plan.mod_folder}) still registers the OLD ids. The FIRST deploy "
        f"of a new id also needs a game RELAUNCH to register its DictionaryPatch line.",
        "REVERT the old deploy first (tools/scroll_out/revert_deploy.py, or revert_deploy_<id>.py), else the "
        "old FieldScene entries linger alongside the new ones.",
        "RE-WIRE New Game if this campaign owns the opening (tools/wire_newgame_from_stock.py <entry id>): "
        "deploy_campaign re-runs the retarget itself, but a wholesale replace wipes the override.",
        "If this campaign sits in a JOURNEY, re-run `ff9mapkit lint-journey`: the manifest's entry row and any "
        "cross-campaign [[journey.link]] name the old ids, and the hub is generated from them.",
        "RE-AUTHOR any OVERWORLD ENTRANCE into this campaign (`world-entrance --field-direct <id>`). The "
        "destination is baked into the world dispatcher's .eb inside the SEPARATE -world mod folder, which a "
        "campaign redeploy never rewrites -- and warping to a retired id crashes rather than fails soft.",
        "If a journeys.toml carries a commented fork PLAYBOOK, update its `--id-base`: refarc scrapes that "
        "COMMENT to place the next arc, so a stale one hands the next region a band this campaign now owns.",
        f"EXISTING SAVES made inside this campaign are void -- a save stores the field id it was made in, and "
        f"{lo}..{hi} did not exist when it was written. Story-FLAG windows are UNCHANGED: they key off member "
        f"POSITION and flag_base, neither of which this verb touches.",
    ]


def apply_reid(rp: ReidPlan) -> list:
    """Write every verified edit. Each write is atomic, and each edit was already proven to re-parse to the
    expected document (:func:`_edit_for`), so an interrupted run cannot leave a torn id behind."""
    written = []
    for e in rp.edits:
        if e.after != e.before:
            # newline="" == NO translation. The rewriters carry each source line's own ending through
            # verbatim, so the default (newline=None) would rewrite every LF to CRLF on Windows and turn a
            # three-number edit into a whole-file diff -- the autocrlf smudge class, self-inflicted.
            fsutil.atomic_write_text(e.path, e.after, newline="")
            written.append(e.path)
    if written:
        # THE CACHE CANNOT SEE THIS EDIT. tomlcache memoizes on (st_mtime_ns, st_size) and names its one
        # stale window as "an edit that preserves BOTH mtime_ns and size" -- which a reid does BY
        # CONSTRUCTION whenever old and new have the same digit count (6000 -> 6500 is the normal case).
        # Any same-process re-read (lint, build, the Workspace) could then be served the pre-move tree.
        from . import tomlcache
        tomlcache.clear()
    return written


def render_report(rp: ReidPlan, *, applied: bool) -> str:
    """The human-facing summary: what moved, what to check, and what reid cannot reach."""
    n_files = sum(1 for e in rp.edits if e.after != e.before)
    L = [f"{'moved' if applied else 'would move'} {rp.moved} field id(s) across {n_files} file(s):"]
    L += [f"    {o} -> {rp.remap[o]}" for o in sorted(rp.remap)]
    for e in rp.edits:
        if e.after != e.before:
            L.append(f"  {e.path.name}")
            L += [f"      {c}" for c in e.changes]
    if rp.warnings:
        L.append("  warnings:")
        L += [f"    ! {w}" for w in rp.warnings]
    if rp.residual:
        L.append("  ADVISORY -- an OLD id is still written at these sites, which reid does not model. "
                 "Check them by hand:")
        L += [f"    ? {h}" for h in rp.residual]
    L.append("  next:" if applied else "  next (re-run with --apply):")
    L += [f"    * {f}" for f in rp.followups]
    return "\n".join(L)
