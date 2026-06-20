"""The multi-campaign journey ASSEMBLER (overworld's lane) -- one level above ``campaign.py``.

A **journey** is a complete playable arc = **one or more chained campaigns**, picked at the World Hub
(memory ``project-ff9-world-hub``; design ``docs/JOURNEYS.md``). A ``campaign.toml`` (``import-chain``) is a
connected slice of fields; a journey sits one level up: it names an ordered set of campaigns, says where the
player STARTS, seeds the starting story state, and defines how each campaign HANDS OFF to the next. The
World Hub is a journey selector -- this module turns a ``journeys.toml`` registry into (a) the namespace
guarantee that makes the whole thing buildable + (b) the hub field that selects + warps into each journey.

**Why this is the hard part (docs/JOURNEYS.md ``§8``):** EventDB / SceneData / the ``gEventGlobal`` flag
heap are GLOBAL -- distinct ids + non-overlapping flag windows are required even across mod folders. A single
campaign's ``assign_ids`` keeps its own members disjoint; only the *journey* layer can guarantee disjointness
ACROSS every campaign of every journey that ships together (the hub offers them all, so they're all
registered at launch). That cross-campaign guarantee is this module's whole job.

The schema unifies overworld's proven single-field hub journeys with the editor_gui handoff's multi-campaign
shape -- ONE ``journeys.toml`` whose ``[[journey]]`` rows are EITHER::

    [[journey]]                         # BARE single-field journey (overworld's proven floor: Dali, Treno)
    id    = "treno"
    name  = "Treno, City of Nobles"
    entry = 4501                        # a real/forked field id the hub warps straight into
    set_scenario = 7550                 # optional hub-side beat seed

    [[journey]]                         # MULTI-CAMPAIGN journey (the assembler's job)
    id        = "escape_ice"
    name      = "Escape to the Ice Cavern"
    campaigns = ["evil_forest", "ice_cavern"]    # ORDERED folder names (each holds a campaign.toml)
    entry     = { campaign = "evil_forest", field = "EVF_START" }   # member NAME (preferred) or raw id
    [journey.seed]                      # == the story_flags New-Game capstone (NOT a parallel mechanism)
    scenario  = 0
    party     = ["Zidane", "Vivi"]
    [[journey.link]]                    # how one campaign hands off to the next (the cross-campaign warp)
    from = { campaign = "evil_forest", field = "EVF_EXIT" }   # the boundary member (an out-of-chain seam)
    to   = { campaign = "ice_cavern",  field = "IC_ENT" }     # the next campaign's entry member

plus the shared ``[hub]`` presentation table (:mod:`ff9mapkit.hub`). ``gen-hub`` builds ONLY the bare rows
(it rejects multi-campaign ones); ``assemble-journey`` resolves BOTH (a bare row is the degenerate
zero-campaign journey -- just warp to ``entry``) and folds :func:`ff9mapkit.hub.render_hub_field_toml` in as
its hub-emit step, so one renderer serves both paths.

This session ships the OFFLINE core (model + resolution + lint + hub emit) -- the namespace guarantee, fully
unit-testable with no game install. The in-game deploy ORCHESTRATION (``deploy_journey``: build each
campaign at its band, realize each link as a live warp, seed the entry, deploy the hub, wire New Game) layers
on top of the existing ``tools/deploy_campaign.py`` + ``retarget_newgame_warp.py`` and is the next, in-game
step (Hard Constraint §2: I can't see the running game, so deploys are human-verified).
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from . import campaign as _campaign
from . import hub as _hub
from .flags import CHOICE_SCRATCH_FLOOR, FIRST_SAFE_FLAG

SCENARIO_MAX = 32767
ID_LO, ID_HI = 4000, 32767                  # custom field-id band (Int16 cap; CLAUDE.md §3)
_SLUG_RE = re.compile(r"^[A-Za-z0-9_]+$")    # a journey id slug -> hub-choice key + seed namespace


class JourneyError(ValueError):
    """A journeys.toml / assembler problem (caught + printed by the CLI)."""


# ---------------------------------------------------------------- the parsed model
@dataclass
class JourneyRef:
    """A reference to a field. For a journey INSIDE a campaign: ``campaign`` is the folder name and ``field``
    is a member NAME (preferred) or a raw global id. For a BARE single-field journey: ``campaign`` is None and
    ``field`` is the real/forked field id the hub warps straight into."""
    campaign: "str | None"
    field: "str | int"


@dataclass
class JourneyLink:
    """A cross-campaign hand-off: the boundary member ``src_field`` in ``src_campaign`` is realized as a live
    warp into ``dst``. This is an explicit OVERRIDE row; ALL other cross-campaign warps auto-wire from the real
    ``.eb`` seams at deploy (:func:`auto_seam_links`), so a journey needs NO link rows and the wired set is the
    full connectivity GRAPH, not N-1."""
    src_campaign: str
    src_field: str            # the boundary member name (handoff schema: from.field, alias from.seam)
    dst: JourneyRef
    dst_entrance: int = 0     # arrival entrance in the next campaign's entry field (to.entrance; default 0)


@dataclass
class JourneySeed:
    """The journey's starting story-state -- the story_flags New-Game capstone, verbatim (NOT a parallel seed
    mechanism). ``raw`` is the whole ``[journey.seed]`` table so the inventory/equipment passthrough the
    capstone supports survives untouched; ``scenario`` + ``party`` are pulled out for lint + the hub seed."""
    scenario: "int | None" = None
    party: list = field(default_factory=list)
    raw: dict = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        return self.scenario is None and not self.party and not self.raw


@dataclass
class Journey:
    """One ``[[journey]]`` row, normalized. ``campaigns`` empty => a BARE single-field journey (``entry.field``
    is a real id, no links). Otherwise a multi-campaign arc: ``entry`` lands inside the first campaign and
    ``links`` chain the rest."""
    id: str
    name: str
    campaigns: list                      # ordered folder names; [] => bare single-field journey
    entry: JourneyRef
    seed: JourneySeed
    links: list                          # [JourneyLink]
    set_scenario: "int | None" = None    # bare-row hub-side beat seed (the proven single-field lever)
    entrance: "int | None" = None        # arrival entrance into the entry field (frames the entry camera)
    exits: tuple = ()                    # DECLARED intended-boundary field ids: a forked field's warp to one of
                                         #   these is the arc's edge (a deliberate exit to vanilla / a not-yet-forked
                                         #   next zone), NOT a bug -> the leak lint stays quiet about it.

    @property
    def is_bare(self) -> bool:
        return not self.campaigns

    @property
    def hub_scenario(self) -> "int | None":
        """The beat the hub seeds before warping in: the seed's scenario if present, else the bare-row
        ``set_scenario``. (For a multi-campaign journey the seed is applied as the full capstone on the entry
        field; the hub still seeds the scenario so the F6/select path lands on the right beat.)"""
        return self.seed.scenario if self.seed.scenario is not None else self.set_scenario


@dataclass
class JourneyManifest:
    """A whole ``journeys.toml``: the ``[hub]`` presentation table (raw dict; :mod:`ff9mapkit.hub` owns its
    schema) + the parsed journeys + the manifest path (its parent is the project root the campaign folders are
    relative to)."""
    hub: dict
    journeys: list                       # [Journey]
    path: Path

    @property
    def root(self) -> Path:
        return self.path.parent


# ---------------------------------------------------------------- the resolved plan
@dataclass
class ResolvedJourney:
    """A journey resolved into the global namespace: the entry field id the hub warps into, each campaign's
    member id list (for disjointness reporting) + assigned flag window, and each link's resolved src/dst global
    ids. A pure derived view over the manifest + the loaded campaign plans -- the assembler's deploy step
    consumes this; lint produces its findings from the same resolution."""
    journey: Journey
    entry_id: int
    campaign_ids: dict                   # folder -> [member new_ids]
    flag_windows: dict                   # folder -> (lo, hi, per_field)
    flag_high: int                       # high-water flag index (exclusive) within this journey
    links: list                          # [{src_campaign, src_field, src_id, dst_campaign, dst_field, dst_id}]


# ---------------------------------------------------------------- loading (pure, tk-free)
def _ref_from(value, *, what: str) -> JourneyRef:
    """Parse an ``entry`` / link endpoint value: a bare int (-> a campaign-less ref) or an inline table
    ``{campaign, field}``. Raises :class:`JourneyError` on a malformed table (the structural floor)."""
    if isinstance(value, dict):
        if "campaign" not in value or "field" not in value:
            raise JourneyError(f"{what} table needs both 'campaign' and 'field' (got {sorted(value)})")
        return JourneyRef(campaign=str(value["campaign"]), field=value["field"])
    try:
        return JourneyRef(campaign=None, field=int(value))
    except (TypeError, ValueError):
        raise JourneyError(f"{what} must be a field id (int) or a {{campaign, field}} table (got {value!r})")


def _link_from(raw: dict, jid: str) -> JourneyLink:
    """Parse one ``[[journey.link]]`` row. ``from`` names the boundary member (key ``field`` preferred, alias
    ``seam`` for the handoff schema); ``to`` is the next campaign's entry ref."""
    if "from" not in raw or "to" not in raw:
        raise JourneyError(f"journey {jid!r}: a [[journey.link]] needs both 'from' and 'to'")
    frm = raw["from"]
    if not isinstance(frm, dict) or "campaign" not in frm:
        raise JourneyError(f"journey {jid!r}: link 'from' must be a {{campaign, field}} table")
    # the boundary member: `field` (preferred) or `seam` (handoff alias) -- both name the source member
    src_field = frm.get("field", frm.get("seam"))
    if src_field is None:
        raise JourneyError(f"journey {jid!r}: link 'from' needs 'field' (the boundary member; alias 'seam')")
    to = raw["to"]
    entrance = int(to["entrance"]) if isinstance(to, dict) and "entrance" in to else 0
    return JourneyLink(src_campaign=str(frm["campaign"]), src_field=str(src_field),
                       dst=_ref_from(to, what=f"journey {jid!r} link 'to'"), dst_entrance=entrance)


def _seed_from(raw) -> JourneySeed:
    if raw is None:
        return JourneySeed()
    if not isinstance(raw, dict):
        raise JourneyError(f"[journey.seed] must be a table (got {type(raw).__name__})")
    sc = raw.get("scenario")
    party = list(raw.get("party", []))
    return JourneySeed(scenario=int(sc) if sc is not None else None, party=party, raw=dict(raw))


def load_journeys(path) -> JourneyManifest:
    """Parse a ``journeys.toml`` into a :class:`JourneyManifest`. Raises :class:`JourneyError` on a STRUCTURAL
    problem (not a manifest; a journey missing ``id``/``entry``; a multi-campaign row whose ``entry`` isn't a
    ``{campaign, field}`` table; a malformed link). Semantic checks (campaigns exist, id/flag disjointness,
    links resolve, ranges) are :func:`lint_manifest`'s job so the CLI prints them all at once. Pure + tk-free
    (mirrors :func:`ff9mapkit.campaign.load_campaign`) -- unit-testable with no game install."""
    p = Path(path)
    with open(p, "rb") as fh:
        data = tomllib.load(fh)
    if "hub" not in data and "journey" not in data:
        raise JourneyError(f"{p}: not a journeys manifest (no [hub] table and no [[journey]] rows)")

    journeys = []
    for i, j in enumerate(data.get("journey", [])):
        if "id" not in j:
            raise JourneyError(f"[[journey]] #{i}: missing required key 'id' (the stable slug)")
        jid = str(j["id"])
        if "entry" not in j:
            raise JourneyError(f"journey {jid!r}: missing required key 'entry' (the New-Game landing field)")
        campaigns = [str(c) for c in j.get("campaigns", [])]
        entry = _ref_from(j["entry"], what=f"journey {jid!r} entry")
        # consistency: a multi-campaign journey's entry must name a campaign; a bare row's must not.
        if campaigns and entry.campaign is None:
            raise JourneyError(f"journey {jid!r}: has campaigns but entry is a bare field id -- a "
                               f"multi-campaign entry must be {{campaign = \"<folder>\", field = \"<member>\"}}")
        if not campaigns and entry.campaign is not None:
            raise JourneyError(f"journey {jid!r}: entry names campaign {entry.campaign!r} but the journey "
                               f"lists no 'campaigns' -- add it to campaigns, or use a bare entry = <id>")
        links = [_link_from(lk, jid) for lk in j.get("link", [])]
        if not campaigns and links:
            raise JourneyError(f"journey {jid!r}: a bare single-field journey can't have [[journey.link]]s "
                               f"(links chain campaigns; this journey has none)")
        sc = j.get("set_scenario")
        ent = j.get("entrance")
        try:
            exits = tuple(int(x) for x in (j.get("exits") or []))
        except (TypeError, ValueError):
            raise JourneyError(f"journey {jid!r}: 'exits' must be a list of field ids (ints)")
        journeys.append(Journey(
            id=jid, name=str(j.get("name") or _hub._humanize(jid)), campaigns=campaigns, entry=entry,
            seed=_seed_from(j.get("seed")), links=links,
            set_scenario=int(sc) if sc is not None else None,
            entrance=int(ent) if ent is not None else None, exits=exits))

    return JourneyManifest(hub=dict(data.get("hub", {})), journeys=journeys, path=p)


# ---------------------------------------------------------------- resolution
def _campaign_path(root, folder) -> Path:
    return Path(root) / folder / "campaign.toml"


def load_campaign_plans(manifest: JourneyManifest) -> dict:
    """Load every campaign folder referenced by the manifest exactly once: ``folder -> (CampaignPlan, dir)``.
    Raises :class:`JourneyError` if a referenced folder has no readable ``campaign.toml`` (the prerequisite
    docs/JOURNEYS.md §7 -- you must fork the campaigns first)."""
    plans: dict = {}
    for j in manifest.journeys:
        for folder in j.campaigns:
            if folder in plans:
                continue
            cpath = _campaign_path(manifest.root, folder)
            if not cpath.is_file():
                raise JourneyError(f"campaign folder {folder!r}: no campaign.toml at {cpath} -- fork it first "
                                   f"(`ff9mapkit import-chain <seed> --out {folder}`; docs/JOURNEYS.md §7)")
            try:
                plans[folder] = (_campaign.load_campaign(cpath), cpath.parent)
            except (_campaign.CampaignError, tomllib.TOMLDecodeError, OSError) as e:
                raise JourneyError(f"campaign folder {folder!r}: {e}")
    return plans


# The scaffold placeholders a freshly-built / just-reconciled journey leaves for the human to fill: an entry
# (ENTRY_MEMBER) or a link boundary the reconcile couldn't auto-detect (BOUNDARY_MEMBER source / ARRIVAL_MEMBER
# target). They are NOT errors in the data -- they are "fill me" markers, so resolve SKIPS them (the rest of
# the journey still resolves) and lint reports them as actionable "not filled yet", not "bad member name".
UNFILLED_PLACEHOLDERS = frozenset({"ENTRY_MEMBER", "BOUNDARY_MEMBER", "ARRIVAL_MEMBER"})


def _is_unfilled(fieldref) -> bool:
    return isinstance(fieldref, str) and fieldref in UNFILLED_PLACEHOLDERS


def _member_id(plan: "_campaign.CampaignPlan", fieldref, *, what: str) -> int:
    """Resolve a member NAME (preferred) or a raw id against a campaign's members -> the global field id.
    A name must match a member; a raw int passes through (lint flags a raw id that isn't a member)."""
    by_name = {m.name: m for m in plan.members}
    if isinstance(fieldref, str) and fieldref in by_name:
        return by_name[fieldref].new_id
    if _is_unfilled(fieldref):
        raise JourneyError(f"{what}: still the {fieldref!r} placeholder -- fill it with a real member name "
                           f"('Fill entry from forks' couldn't auto-detect it; pick the member by hand)")
    try:
        return int(fieldref)
    except (TypeError, ValueError):
        raise JourneyError(f"{what}: {fieldref!r} is neither a member name nor a field id")


def _flag_windows(journey: Journey, plans: dict) -> "tuple[dict, int]":
    """Lay each campaign of a journey end-to-end in the safe flag band: campaign k gets
    ``len(members) * flags_per_field`` bits starting where k-1 ended, from :data:`FIRST_SAFE_FLAG`. Campaigns
    in ONE journey run together (you can be mid-arc across a boundary), so their windows must not overlap.
    Returns ``({folder: (lo, hi, per_field)}, high_water_exclusive)``. (Different journeys are mutually
    exclusive -- one New Game = one journey -- so their windows MAY reuse the same band; lint only requires a
    journey's own total to fit below the choice scratch.)"""
    windows: dict = {}
    cur = FIRST_SAFE_FLAG
    for folder in journey.campaigns:
        plan, _ = plans[folder]
        span = max(1, len(plan.members)) * plan.flags_per_field
        windows[folder] = (cur, cur + span - 1, plan.flags_per_field)
        cur += span
    return windows, cur


def auto_seam_links(campaigns, plain, *, exclude_members=frozenset()) -> list:
    """EVERY cross-campaign warp the forked ``.eb`` seams imply, as resolved link dicts -- so a journey needs NO
    ``[[journey.link]]`` rows: the deploy retargets each so a forked region's warps stay in-fork (leak-proof),
    derived from the real game connectivity, not the listed order. ``plain`` = ``{folder: CampaignPlan}``;
    ``exclude_members`` = ``(campaign, member)`` pairs an explicit ``[[journey.link]]`` already controls (an
    author override takes the whole member). A FIELD seam self-describes (its ``to_real`` -> the sibling that
    forks it; order-INDEPENDENT); a world-map exit, which names no destination, falls back to the listed order
    (its campaign -> the NEXT campaign's entry). PURE."""
    conn = campaign_connectivity(campaigns, plain)
    by_real = {c: {m.real_id: m for m in plain[c].members if m.real_id} for c in campaigns if c in plain}
    new_id = {c: {m.name: m.new_id for m in plain[c].members} for c in campaigns if c in plain}
    out, warp_seen = [], set()
    for a in campaigns:                              # (1) FIELD seams -> ONE link per distinct Field(to_real)
        rec = conn.get(a)                            #     warp (else a member warping to N fields would leave
        if not rec:                                  #     N-1 of them UN-retargeted -> leaks)
            continue
        for b, seams in rec["to"].items():
            for frm, to_real, _k in seams:
                sid = new_id[a].get(frm)             # guard: an orphaned seam's `frm` may be a stringified real id
                if sid is None or (a, frm) in exclude_members or (a, frm, to_real) in warp_seen:
                    continue                          # (not a member) -> skip, don't KeyError the whole deploy/lint
                arr = by_real[b].get(to_real)
                if arr is None:
                    continue                          # one Field(to_real) -> ONE place (shared donor: first b wins)
                warp_seen.add((a, frm, to_real))
                out.append({"src_campaign": a, "src_field": frm, "src_id": sid,
                            "dst_campaign": b, "dst_field": arr.name, "dst_id": arr.new_id, "dst_entrance": 0})
    wired = {(d["src_campaign"], d["dst_campaign"]) for d in out}
    for a, b in zip(campaigns, campaigns[1:]):        # (2) world-map exits -> fall back to the listed order
        rec = conn.get(a)
        if rec and rec.get("worldmap") and (a, b) not in wired and a in plain and b in plain:
            wm = rec["worldmap"][0][0]
            sid = new_id[a].get(wm)                   # same guard for a non-member world-map seam source
            if sid is None or (a, wm) in exclude_members:
                continue
            out.append({"src_campaign": a, "src_field": wm, "src_id": sid,
                        "dst_campaign": b, "dst_field": plain[b].entry_name,
                        "dst_id": new_id[b][plain[b].entry_name], "dst_entrance": 0})
    return out


def resolve_journey(journey: Journey, plans: dict) -> ResolvedJourney:
    """Resolve a journey into the global namespace using the pre-loaded campaign plans (see
    :func:`load_campaign_plans`): the entry field id, per-campaign member id lists, assigned flag windows, and
    the cross-campaign links. Links are the explicit ``[[journey.link]]`` OVERRIDES + every other cross-campaign
    warp AUTO-DERIVED from the real ``.eb`` seams (:func:`auto_seam_links`) -- so a journey deploys leak-proof
    with no link rows. PURE over the manifest + plans (no game install)."""
    if journey.is_bare:
        return ResolvedJourney(journey=journey, entry_id=int(journey.entry.field),
                               campaign_ids={}, flag_windows={}, flag_high=FIRST_SAFE_FLAG, links=[])

    entry_plan, _ = plans[journey.entry.campaign]
    entry_id = _member_id(entry_plan, journey.entry.field, what=f"journey {journey.id!r} entry")
    campaign_ids = {f: [m.new_id for m in plans[f][0].members] for f in journey.campaigns}
    flag_windows, flag_high = _flag_windows(journey, plans)

    links, override_members = [], set()
    for lk in journey.links:                          # explicit links are OVERRIDES (the author takes the member)
        if _is_unfilled(lk.src_field) or _is_unfilled(lk.dst.field):
            continue                                  # an un-filled FILL/BOUNDARY scaffold row -> skip (lint flags)
        src_plan, _ = plans[lk.src_campaign]
        dst_plan, _ = plans[lk.dst.campaign]
        override_members.add((lk.src_campaign, lk.src_field))
        links.append({
            "src_campaign": lk.src_campaign, "src_field": lk.src_field,
            "src_id": _member_id(src_plan, lk.src_field, what=f"journey {journey.id!r} link from"),
            "dst_campaign": lk.dst.campaign, "dst_field": lk.dst.field,
            "dst_id": _member_id(dst_plan, lk.dst.field, what=f"journey {journey.id!r} link to"),
            "dst_entrance": lk.dst_entrance})
    plain = {f: plans[f][0] for f in journey.campaigns if f in plans}
    links.extend(auto_seam_links(journey.campaigns, plain, exclude_members=override_members))
    return ResolvedJourney(journey=journey, entry_id=entry_id, campaign_ids=campaign_ids,
                           flag_windows=flag_windows, flag_high=flag_high, links=links)


# ---------------------------------------------------------------- lint (the namespace guarantee)
def _member_has_seam(plan: "_campaign.CampaignPlan", name: str) -> bool:
    """True if member ``name`` has an out-of-chain SEAM (a scripted/overworld/menu/portal exit) -- the
    boundary that a link realizes as a cross-campaign warp. The graph derives seams_by from the plan."""
    g = _campaign.campaign_graph(plan)
    node = g.by_name.get(name)
    return bool(node and node.seams)


def lint_manifest(manifest: JourneyManifest, *, deep: bool = True) -> "tuple[list, list]":
    """Validate a whole ``journeys.toml`` offline. Returns ``(errors, warnings)`` -- errors abort assembly,
    warnings are advisory (mirrors :func:`ff9mapkit.campaign.lint_campaign`). Covers docs/JOURNEYS.md §4.7:
    campaigns exist + parse + pass campaign-lint; the GLOBAL id-disjointness guarantee (§8 -- the whole job);
    per-journey flag windows fit; links resolve to real members + boundaries; entry valid; seed range-checked.
    ``deep=False`` skips the per-campaign :func:`lint_campaign` recursion (structure only) for speed."""
    errors, warnings = [], []

    if not manifest.journeys:
        # an empty SELECTOR hub ([hub] + no rows yet) is a valid in-progress scaffold -> a warning, not a hard
        # error (the build/assemble path still rejects it at validate_hub). Only a hub-less manifest errors.
        (warnings if manifest.hub else errors).append(
            "no [[journey]] rows yet -- add a journey (GUI: 'Add journey...') before deploying")
    if not manifest.hub:
        warnings.append("no [hub] table -- the journey graph lints, but `assemble-journey` can't emit the "
                        "hub field without it (add a [hub] block: name/id/borrow_bg/camera).")

    # (a) journey id slugs: valid tokens, unique
    seen: set = set()
    for i, j in enumerate(manifest.journeys):
        if not j.id or not _SLUG_RE.match(j.id):
            errors.append(f"journey #{i}: id {j.id!r} must be a token (A-Z, 0-9, _) -- the hub-choice key")
        elif j.id in seen:
            errors.append(f"journey id {j.id!r} is duplicated -- ids must be unique")
        seen.add(j.id)

    # (a2) two menu rows warping to the SAME bare entry field -> almost always a typo (a copy-pasted row).
    entry_seen: dict = {}
    for j in manifest.journeys:
        if j.is_bare and isinstance(j.entry.field, int):
            if j.entry.field in entry_seen:
                warnings.append(f"journeys {entry_seen[j.entry.field]!r} and {j.id!r} both warp to field "
                                f"{j.entry.field} -- two menu rows to the same destination (likely a copy-paste)")
            else:
                entry_seen[j.entry.field] = j.id

    # (b) load every referenced campaign (folder exists + parses). Bare journeys reference none.
    try:
        plans = load_campaign_plans(manifest)
    except JourneyError as e:
        errors.append(str(e))
        return errors, warnings                  # can't resolve ids without the plans -- stop here

    # (c) per-campaign lint (structure/flags/art) -- prefix each finding with its folder
    if deep:
        for folder, (plan, cdir) in plans.items():
            try:
                cerr, cwarn = _campaign.lint_campaign(plan, cdir, in_journey=True)
            except (_campaign.CampaignError, ValueError) as e:
                errors.append(f"campaign {folder!r}: {e}")
                continue
            errors.extend(f"campaign {folder!r}: {e}" for e in cerr)
            warnings.extend(f"campaign {folder!r}: {w}" for w in cwarn)

    # (d) THE GLOBAL ID-DISJOINTNESS GUARANTEE (docs/JOURNEYS.md §8): every field the assembler REGISTERS -- a
    #     campaign member or the hub -- must have a globally unique id (one EventDB/SceneData namespace). A bare
    #     entry only REFERENCES an installed field (the hub warps to it), so it must not collide with a
    #     registered field, but two bare journeys MAY warp to the SAME destination (e.g. New Game vs New Game+).
    owner: dict = {}                              # global field id -> a human label of who REGISTERS it
    def _claim(fid: int, label: str):
        if not isinstance(fid, int):
            return
        if fid in owner and owner[fid] != label:
            errors.append(f"field id {fid} is claimed by BOTH {owner[fid]} and {label} -- EventDB/SceneData "
                          f"are global; give them disjoint id bands (re-fork a campaign with a different "
                          f"`import-chain --id-base`, or re-point a bare journey).")
        else:
            owner.setdefault(fid, label)
    for folder, (plan, _) in plans.items():
        for m in plan.members:
            _claim(m.new_id, f"campaign {folder!r} member {m.name!r}")
    # the [hub] field id is ALSO registered -- it renders alongside every campaign, so a hub/member collision is
    # the same global-EventDB black screen. Claim it (before the bare-entry check, so a bare-vs-hub clash shows).
    if manifest.hub.get("id") is not None:
        try:
            _claim(int(manifest.hub["id"]), "the [hub] field")
        except (TypeError, ValueError):
            errors.append(f"[hub] id {manifest.hub.get('id')!r} must be a field id (int)")
    bare_ids: list = []
    for j in manifest.journeys:
        if j.is_bare:
            try:
                fid = int(j.entry.field)
            except (TypeError, ValueError):
                errors.append(f"journey {j.id!r}: bare entry {j.entry.field!r} must be a field id (int)")
                continue
            bare_ids.append(fid)
            if fid in owner:                      # a bare entry collides with a REGISTERED field (member / hub)
                errors.append(f"field id {fid} is claimed by BOTH {owner[fid]} and journey {j.id!r} (bare entry) "
                              f"-- a campaign member / the hub registers it; re-point this journey.")
            # NB: NOT claimed into `owner` -- two bare journeys may legally warp to the same installed field
            # (the duplicate-destination case is the (a2) warning above, not a hard error).

    # (e) id band range (every registered id + every bare entry in the custom band)
    for fid, label in sorted(list(owner.items()) + [(b, f"a bare entry") for b in bare_ids]):
        if not (ID_LO <= fid <= ID_HI):
            errors.append(f"{label}: field id {fid} out of band -- custom ids are {ID_LO}-{ID_HI} "
                          f"(the live fldMapNo is Int16, so a higher id registers but is unreachable)")

    # (f) per-journey resolution: entry, flag windows, links, seed
    for j in manifest.journeys:
        _lint_journey(j, plans, errors, warnings)

    return errors, warnings


def _lint_journey(j: Journey, plans: dict, errors: list, warnings: list) -> None:
    """Per-journey semantic checks (entry resolves, flag window fits, links resolve to real members +
    boundaries, the chain is connected, seed in range). Appends to the shared errors/warnings lists."""
    # entry
    if j.is_bare:
        if j.set_scenario is not None and not (0 <= j.set_scenario <= SCENARIO_MAX):
            errors.append(f"journey {j.id!r}: set_scenario {j.set_scenario} out of range (0-{SCENARIO_MAX})")
    else:
        for folder in j.campaigns:
            if folder not in plans:               # already errored in load_campaign_plans, but be defensive
                return
        entry_plan = plans[j.entry.campaign][0]
        if j.entry.campaign not in j.campaigns:
            errors.append(f"journey {j.id!r}: entry campaign {j.entry.campaign!r} is not in this journey's "
                          f"campaigns {j.campaigns}")
        elif isinstance(j.entry.field, str) and j.entry.field not in {m.name for m in entry_plan.members}:
            errors.append(f"journey {j.id!r}: entry field {j.entry.field!r} is not a member of campaign "
                          f"{j.entry.campaign!r}")
        elif isinstance(j.entry.field, int) and j.entry.field not in {m.new_id for m in entry_plan.members}:
            # a raw int entry that resolves to no member is a hard error (same as a bad NAME): it would flow into
            # plan.entry_field_id and `deploy_journey --newgame entry` would wire an unreachable New-Game target.
            errors.append(f"journey {j.id!r}: entry id {j.entry.field} is not a member of campaign "
                          f"{j.entry.campaign!r} -- prefer a member NAME (stable across re-id)")

        # flag windows fit below the choice scratch
        _, high = _flag_windows(j, plans)
        if high > CHOICE_SCRATCH_FLOOR:
            errors.append(f"journey {j.id!r}: campaigns need {high - FIRST_SAFE_FLAG} flags "
                          f"({FIRST_SAFE_FLAG}..{high - 1}) -- past the choice-scratch floor "
                          f"{CHOICE_SCRATCH_FLOOR}. Fewer members, smaller flags_per_field, or split the arc.")

        # links: resolve + boundary + connectivity
        names_by = {f: {m.name for m in plans[f][0].members} for f in j.campaigns}
        for lk in j.links:
            if lk.src_campaign not in j.campaigns:
                errors.append(f"journey {j.id!r}: link from campaign {lk.src_campaign!r} not in this journey")
                continue
            if lk.dst.campaign not in j.campaigns:
                errors.append(f"journey {j.id!r}: link to campaign {lk.dst.campaign!r} not in this journey")
                continue
            if _is_unfilled(lk.src_field) or _is_unfilled(lk.dst.field):
                # an OBSOLETE leftover placeholder (a legacy file) -- cross-campaign links auto-wire from the
                # real seams now, so it's not needed. Warn (don't block); resolve skips it.
                warnings.append(f"journey {j.id!r}: a leftover {lk.src_field if _is_unfilled(lk.src_field) else lk.dst.field!r} "
                                f"placeholder on the {lk.src_campaign!r} -> {lk.dst.campaign!r} link -- delete the "
                                f"row; cross-campaign warps auto-wire at deploy from the real .eb connectivity.")
            elif lk.src_field not in names_by[lk.src_campaign]:
                errors.append(f"journey {j.id!r}: link source {lk.src_field!r} is not a member of "
                              f"{lk.src_campaign!r}")
            elif not _member_has_seam(plans[lk.src_campaign][0], lk.src_field):
                warnings.append(f"journey {j.id!r}: link source {lk.src_campaign!r}/{lk.src_field!r} has no "
                                f"out-of-chain seam -- it's not a boundary, so there's nothing to retarget "
                                f"into the next campaign (the assembler will inject a fresh warp instead).")
            dstf = lk.dst.field
            if not _is_unfilled(lk.src_field) and not _is_unfilled(dstf) \
                    and isinstance(dstf, str) and dstf not in names_by[lk.dst.campaign]:
                errors.append(f"journey {j.id!r}: link target {dstf!r} is not a member of {lk.dst.campaign!r}")

        # connectivity: every campaign reachable from the entry over the AUTO-WIRED + override links
        plain = {f: plans[f][0] for f in j.campaigns if f in plans}
        _lint_chain_connectivity(j, errors, warnings, plain=plain)
        # LEAK check (single- AND multi-campaign): a forked field whose carried Field()/door warps the player to a
        # field NO journey campaign forks -> an exit into the un-forked real game. A SCRIPTED (forced cutscene/ATE)
        # one SOFTLOCKS; a PORTAL (walk-out door) is more often the arc's intended edge. A target DECLARED in the
        # journey's `exits = [...]` is an intended boundary -> stays quiet. Sibling-aware via campaign_connectivity.
        conn = campaign_connectivity(j.campaigns, plain)
        _ids = lambda s: ",".join(str(t) for t in sorted(s)[:8]) + (" ..." if len(s) > 8 else "")
        for folder in j.campaigns:
            ext = [(tid, knd) for _f, tid, knd in (conn.get(folder) or {}).get("external", [])
                   if knd in ("scripted", "portal") and tid not in j.exits]
            forced = {tid for tid, knd in ext if knd == "scripted"}
            doors = {tid for tid, knd in ext if knd == "portal"}
            if forced:
                warnings.append(f"journey {j.id!r}: campaign {folder!r} has a FORCED warp to un-forked field(s) "
                                f"{_ids(forced)} -- a carried cutscene/ATE Field() exits the journey into the real "
                                f"game; a grey/unskippable one SOFTLOCKS the player. Fork those in, redirect the "
                                f"warp, or declare it intended via the journey's `exits = [...]`.")
            if doors:
                warnings.append(f"journey {j.id!r}: campaign {folder!r} has a walk-out door to un-forked field(s) "
                                f"{_ids(doors)} -- likely the arc's edge; fork the next zone or declare it intended "
                                f"via `exits = [...]`.")

    # seed range (== story_flags capstone; deeper item/party validation is story_flags' at apply-time)
    if j.seed.scenario is not None and not (0 <= j.seed.scenario <= SCENARIO_MAX):
        errors.append(f"journey {j.id!r}: [journey.seed] scenario {j.seed.scenario} out of range "
                      f"(0-{SCENARIO_MAX})")
    for pc in j.seed.party:
        if not isinstance(pc, str) or not pc.strip():
            errors.append(f"journey {j.id!r}: [journey.seed] party entries must be character names (got {pc!r})")
    if j.seed.raw.get("inventory") is not None or j.seed.raw.get("start_inventory") is not None \
            or j.seed.raw.get("equipment") is not None:
        warnings.append(f"journey {j.id!r}: [journey.seed] inventory/equipment map to the MOD-GLOBAL New-Game "
                        f"CSVs (read once at New Game, SHARED across every journey of the hub) -- clean only "
                        f"for a single-journey hub, and shadowed under the campaigns' --no-warp deploy unless "
                        f"promoted to the highest folder. For PER-JOURNEY items, add an `[[on_entry]] "
                        f"items = [[\"Potion\", 5]] gil = 200 flag = <N>` block to the entry member's "
                        f"field.toml -- scripted, once-gated, baked into the entry fork's own .eb (no global "
                        f"leak). scenario/party already seed cleanly that way.")


def _lint_chain_connectivity(j: Journey, errors: list, warnings: list, *, plain=None) -> None:
    """A journey's campaigns must be reachable from the entry campaign -- over the explicit ``[[journey.link]]``
    OVERRIDES *and* the warps AUTO-WIRED from the real ``.eb`` seams (``plain`` = ``{folder: CampaignPlan}``).
    An unreachable campaign means the game's real warps don't connect it in this set (a wrong region/entry).
    NO link-count check: the journey wires the full connectivity GRAPH, so >N-1 links is normal + faithful."""
    if len(j.campaigns) <= 1:
        return
    adj: dict = {c: set() for c in j.campaigns}
    for lk in j.links:                               # explicit overrides
        if lk.src_campaign in adj and lk.dst.campaign in adj and not _is_unfilled(lk.src_field):
            adj[lk.src_campaign].add(lk.dst.campaign)
    if plain:                                        # + the auto-derived cross-campaign warps (the real graph)
        for d in auto_seam_links(j.campaigns, plain):
            adj[d["src_campaign"]].add(d["dst_campaign"])
    reached, stack = {j.entry.campaign}, [j.entry.campaign]
    while stack:
        for nxt in adj.get(stack.pop(), ()):
            if nxt not in reached:
                reached.add(nxt)
                stack.append(nxt)
    unreachable = [c for c in j.campaigns if c not in reached]
    if unreachable:
        warnings.append(f"journey {j.id!r}: campaign(s) {unreachable} unreachable from the entry campaign "
                        f"{j.entry.campaign!r} via [[journey.link]]s -- the game's real warps don't connect them "
                        f"in this set (a wrong region/entry, or they join via an order-only world-map hop).")
    # NB: NO link-count check. The journey wires the REAL connectivity GRAPH (every cross-campaign warp), so more
    # than N-1 links is normal + faithful (you can walk between regions both ways, as in the game). Reachability
    # above is the real test -- a missing connection shows up as an unreachable campaign, not a wrong count.


# ---------------------------------------------------------------- hub fold-in (reuse hub.py's renderer)
def manifest_to_hub_spec(manifest: JourneyManifest) -> "_hub.HubSpec":
    """Resolve every journey (bare + multi-campaign) to its global entry id + hub-side scenario seed and build
    the :class:`ff9mapkit.hub.HubSpec` -- so the assembler's hub-emit step IS gen-hub's renderer
    (:func:`ff9mapkit.hub.render_hub_field_toml`), one source of truth. Raises :class:`JourneyError` if there's
    no ``[hub]`` table (nothing to render into)."""
    if not manifest.hub:
        raise JourneyError("no [hub] table in the manifest -- can't emit a hub field (add a [hub] block).")
    plans = load_campaign_plans(manifest)
    hub_journeys = []
    for j in manifest.journeys:
        rj = resolve_journey(j, plans)
        hub_journeys.append(_hub.Journey(id=j.id, name=j.name, entry=rj.entry_id,
                                         set_scenario=j.hub_scenario, entrance=j.entrance))
    return _hub.hubspec_from_table(manifest.hub, hub_journeys)


def generate_hub(journeys_path, out_path=None, *, extract_camera=False, game=None, force=False) -> dict:
    """Load a ``journeys.toml``, lint it, and emit the hub ``field.toml`` (resolving bare + multi-campaign
    journeys alike). Returns ``{path, spec, errors, warnings, extracted}``. Raises :class:`JourneyError` on a
    lint error. The existing build/deploy path then compiles the emitted hub field. (gen-hub is the bare-only
    twin; this is the full assembler's hub step.)

    ``extract_camera`` (needs the install + UnityPy): auto-provision the hub's backdrop camera from ``[hub]
    borrow_field`` into the gitignored workspace cache and point the emitted ``[camera] borrow`` at it -- so a
    journey assemble/deploy "just works" without a manual extract step (the same lever as ``gen-hub
    --extract-camera``)."""
    manifest = load_journeys(journeys_path)
    errors, warnings = lint_manifest(manifest)
    if errors:
        raise JourneyError("journeys.toml lint failed:\n  - " + "\n  - ".join(errors))
    spec = manifest_to_hub_spec(manifest)
    herr, hwarn = _hub.validate_hub(spec)
    if herr:
        raise JourneyError("hub validation failed:\n  - " + "\n  - ".join(herr))
    out_path = Path(out_path) if out_path else (manifest.root / "hub.field.toml")
    if out_path.is_dir():
        out_path = out_path / "hub.field.toml"
    extracted = None
    if extract_camera:
        extracted = _hub.extract_camera_into_spec(spec, out_path.parent, game=game, force=force)
    text = _hub.render_hub_field_toml(spec, source=manifest.path.name)
    out_path.write_text(text, encoding="utf-8", newline="\n")
    return {"path": out_path, "spec": spec, "errors": errors, "warnings": list(warnings) + list(hwarn),
            "extracted": extracted}


# ---------------------------------------------------------------- read-only resolved view
def _toml_str(s) -> str:
    """Escape a value for a double-quoted TOML string (backslash + quote)."""
    return str(s).replace("\\", "\\\\").replace('"', '\\"')


def render_journey_row(jid: str, name: str, entry: int, *, scenario=None, entrance=None) -> str:
    """One bare ``[[journey]]`` block -- a World-Hub menu row that warps into an ALREADY-INSTALLED field
    (``entry``). Pure text (no game). Raises :class:`JourneyError` on a bad slug / non-int entry."""
    jid = str(jid).strip()
    if not _SLUG_RE.match(jid):
        raise JourneyError(f"journey id {jid!r} must be a slug (A-Z, 0-9, _) -- it's the hub-choice key")
    try:
        entry = int(entry)
    except (TypeError, ValueError):
        raise JourneyError(f"entry {entry!r} must be a field id (the installed field the hub warps into)")
    L = ["[[journey]]",
         f'id = "{_toml_str(jid)}"',
         f'name = "{_toml_str(name) or jid}"',
         f"entry = {entry}          # the installed field this menu row warps into (>= 4000)"]
    if scenario is not None:
        L.append(f"set_scenario = {int(scenario)}        # seed this story beat before warping in")
    if entrance is not None:
        L.append(f"entrance = {int(entrance)}")
    return "\n".join(L) + "\n"


_JOURNEY_HDR = re.compile(r"\s*\[\[\s*journey\s*\]\]\s*(#.*)?$")   # a TOP-LEVEL [[journey]] (not journey.link)


def remove_journey_row(text: str, jid: str) -> str:
    """Remove the ``[[journey]]`` block whose ``id`` is ``jid`` from a journeys.toml's TEXT. A block runs from
    its ``[[journey]]`` header to the next ``[[journey]]`` header (or EOF), carrying any ``[journey.seed]`` /
    ``[[journey.link]]`` sub-tables. Preserves the ``[hub]`` table + every other journey + comments. Raises
    :class:`JourneyError` if no journey with that id is present."""
    lines = text.splitlines()
    starts = [i for i, ln in enumerate(lines) if _JOURNEY_HDR.match(ln)]
    for k, s in enumerate(starts):
        end = starts[k + 1] if k + 1 < len(starts) else len(lines)
        bid = None
        for ln in lines[s:end]:
            m = re.match(r'\s*id\s*=\s*"([^"]*)"', ln)
            if m:
                bid = m.group(1)
                break
        if bid == jid:
            del lines[s:end]
            while lines and not lines[-1].strip():     # don't leave a trailing blank pile-up at EOF
                lines.pop()
            return ("\n".join(lines) + "\n") if lines else "\n"
    raise JourneyError(f"no journey {jid!r} to remove in this manifest")


def render_selector_hub_toml(*, hub_name="World Hub", hub_id=4600, borrow_bg=None, hub_area=None,
                             borrow_field=None, journeys=None) -> str:
    """A WORLD-HUB (journey-selector) ``journeys.toml``: ``[hub]`` + one bare ``[[journey]]`` row per
    already-installed slice. New Game lands on the hub; each row is a menu choice that warps into its field.
    The hub backdrop defaults to MOGNET CENTRAL (FF9's journey nexus + a real ``borrow_field`` so
    ``deploy_journey --apply`` auto-extracts the camera). ``journeys`` = list of ``{id, name, entry,
    scenario?}``; an empty list emits a commented example to fill (in the GUI: 'Add journey...')."""
    if borrow_bg is None:                              # default the hub to Mognet Central (the journey nexus)
        from . import refarc as _refarc
        borrow_bg, hub_area, borrow_field = _refarc.HUB_BORROW_BG, _refarc.HUB_BORROW_AREA, _refarc.HUB_BORROW_FIELD
    L = ["# A WORLD HUB -- a journey SELECTOR. New Game lands here; each [[journey]] row below is a menu",
         "# choice that warps into an ALREADY-INSTALLED slice (a forked field / arc in its own mod folder).",
         "# Keep every journey installed at once; the hub just needs each one's {name, entry id, seed}.",
         "# Add a row per installed journey (GUI: 'Add journey...'), then deploy + point New Game at the hub.",
         "",
         "[hub]",
         f'name = "{_hub.name_token(hub_name)}"      # an EVT_/FBG_ token (no spaces -- becomes the field name)',
         f"id = {int(hub_id)}                  # the hub field id (custom band, >= 4000)"]
    if hub_area is not None:
        L.append(f"area = {int(hub_area)}                  # the borrowed room's FBG area (FBG_N<area>_...)")
    else:                                              # custom borrow_bg with no area -> the default 21 is likely wrong
        L.append("# area = 21          # SET ME: must equal the borrowed room's real FBG area (the default 21 is "
                 "usually WRONG for a custom room -> black screen)")
    L.append(f'borrow_bg = "{_toml_str(borrow_bg)}"   # the room whose art the hub reuses (`list-fields`)')
    if borrow_field is not None:
        L.append(f"borrow_field = {int(borrow_field)}              # the real field -> `deploy_journey --apply` "
                 "auto-extracts its camera")
    else:
        L.append("# borrow_field = <real field id>   # uncomment so `deploy_journey --apply` auto-extracts the camera")
    L.append("")
    rows = list(journeys or [])
    if rows:
        for r in rows:
            L.append(render_journey_row(r["id"], r.get("name", r["id"]), r["entry"],
                                        scenario=r.get("scenario")).rstrip("\n"))
            L.append("")
    else:
        L += ["# Add a journey row per installed slice (or use the GUI 'Add journey...'). Example:",
              "# [[journey]]",
              '# id = "dali"',
              '# name = "Dali"',
              "# entry = 4100          # the installed field New Game warps into for this journey",
              "# set_scenario = 2600   # optional: seed the story beat"]
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- real connectivity (the seam oracle)
# Zones / id order are an ORGANIZING convenience, never a constraint -- a custom chain can run in any order the
# author wants. So we derive how campaigns ACTUALLY connect from the real warps in each forked .eb (the seams the
# fork already records), not from zone tokens or seed-id adjacency. This tells the author where a campaign really
# hands off (which may be a non-adjacent or non-chronological sibling) without forcing the game into our pattern.
def campaign_connectivity(folders, plans) -> dict:
    """The cross-campaign warp graph read from each forked campaign's actual ``.eb`` seams (scripted / overworld
    / portal), NOT from zones or id order. ``folders`` = the journey's campaign list; ``plans`` = a
    ``{folder: CampaignPlan}`` map (unforked folders simply absent). Returns ``{folder: {"to": {dst_folder:
    [(frm, to_real, kind), ...]}, "external": [(frm, to_real, kind), ...], "worldmap": [(frm, kind), ...]}}`` --
    where each campaign's seams land: a SIBLING campaign in this journey, an unforked real field (a leak / a
    boundary out of the journey), or the world map. PURE over the plans."""
    owner: dict = {}                                 # real field id -> [campaigns that fork it] (a donor id MAY be
    for f in folders:                                #   forked by >1 sibling -- distinct new_ids, same real_id)
        p = plans.get(f)
        if p is None:
            continue
        for m in p.members:
            if m.real_id:
                owner.setdefault(int(m.real_id), []).append(f)
    out: dict = {}
    for f in folders:
        p = plans.get(f)
        if p is None:
            continue
        rec = {"to": {}, "external": [], "worldmap": []}
        for s in p.seams:
            frm, kind, tr = s.get("frm"), (s.get("kind") or "scripted"), s.get("to_real")
            if tr == "WORLDMAP":
                rec["worldmap"].append((frm, kind))
                continue
            try:
                tr = int(tr)
            except (TypeError, ValueError):
                continue
            owners = owner.get(tr, [])
            siblings = [d for d in owners if d != f]
            if not owners:
                rec["external"].append((frm, tr, kind))      # lands in a field NO journey campaign forks (a leak)
            for d in siblings:                                # name EVERY sibling that forks the target (not just one)
                rec["to"].setdefault(d, []).append((frm, tr, kind))
            # owners == [f] only -> a seam back into the same campaign; not a cross-campaign edge
        out[f] = rec
    return out


def _field_list(seams, limit=4) -> str:
    """A compact, de-duplicated, sorted list of the real field ids in a seam list: ``'200,202,206 ...'``."""
    ids = sorted({t for _, t, _ in seams})
    return ",".join(str(t) for t in ids[:limit]) + (" ..." if len(ids) > limit else "")


def _kind_tag(seams) -> str:
    """The warp KIND across a seam list -- ``scripted`` (a story/cutscene Field(), maybe gated) vs ``portal`` (a
    door edge) vs mixed -- so a one-time cutscene warp isn't mistaken for a freely-walkable connection."""
    kinds = sorted({k for _, _, k in seams})
    return kinds[0] if len(kinds) == 1 else "mixed"


def connection_targets(conn_rec) -> str:
    """One-line 'dst (via 204,209 scripted); other (via 55,67 scripted)' summary of a single campaign's
    ``campaign_connectivity`` record -- the siblings its seams reach + the warp kind, for a reconcile/lint hint.
    ``''`` if it reaches no sibling."""
    if not conn_rec or not conn_rec.get("to"):
        return ""
    return "; ".join(f"{dst} (via {_field_list(seams)} {_kind_tag(seams)})"
                     for dst, seams in conn_rec["to"].items())


def render_connectivity(folders, plans, *, wired=frozenset(), conn=None) -> "list[str]":
    """Human report lines for :func:`campaign_connectivity`: each campaign and which siblings its real seams
    reach + the warp kind, plus out-of-journey leaks (with ids). ``wired`` = the ``(src, dst)`` campaign pairs
    actually wired (from the resolved links -- explicit + auto-derived); an edge NOT in it is flagged
    ``[NOT wired]`` (rare -- a field seam always auto-wires; a non-adjacent overworld hop may not). ``conn`` = a
    precomputed map (else computed). Only campaigns with an out-of-campaign seam are listed. ``[]`` if nothing."""
    if conn is None:
        conn = campaign_connectivity(folders, plans)
    if not conn:
        return []
    rows = []
    for f in folders:
        rec = conn.get(f)
        if rec is None:                              # not forked yet -> omit (don't pad the report)
            continue
        bits = []
        for dst, seams in rec["to"].items():
            tag = "" if (f, dst) in wired else "  [NOT wired]"   # almost always wired (every field seam auto-wires)
            bits.append(f"-> {dst} (via {_field_list(seams)} {_kind_tag(seams)}){tag}")
        if rec["worldmap"]:
            bits.append(f"-> world map x{len(rec['worldmap'])}")
        if rec["external"]:                          # out-of-journey leaks: ALWAYS shown, with ids (leak-hunting)
            bits.append(f"-> {len(rec['external'])} leak(s) to unforked fields ({_field_list(rec['external'])})")
        if bits:                                     # skip a terminal campaign with no out-of-campaign seams
            rows.append(f"  {f}: " + "  ".join(bits))
    if not rows:
        return []
    return ["real connectivity (from each forked campaign's .eb seams -- the actual warps, not zone/id order; "
            "every field warp AUTO-WIRES at deploy, leak-proof):"] + rows


def render_journey_plan(manifest: JourneyManifest) -> str:
    """A human-readable view of the assembled namespace: each journey, its entry global id + hub seed, and (for
    a multi-campaign arc) its campaigns' id bands + flag windows + resolved cross-campaign links. Backs the
    `lint-journey --graph` / `assemble-journey` dry-run output. Tolerant of an un-resolvable manifest (prints
    what it can)."""
    out = [f"journeys manifest: {manifest.path.name}  ({len(manifest.journeys)} journey(s))"]
    if manifest.hub:
        out.append(f"  hub: {manifest.hub.get('name', '?')} (field {manifest.hub.get('id', '?')})")
    out.append("")
    try:
        plans = load_campaign_plans(manifest)
    except JourneyError as e:
        return "\n".join(out) + f"\n!! cannot resolve campaigns: {e}\n"
    _plain = {f: p for f, (p, _) in plans.items()}   # {folder: CampaignPlan} for campaign_connectivity
    for j in manifest.journeys:
        rj = resolve_journey(j, plans)
        seed = f"  seed scenario={j.hub_scenario}" if j.hub_scenario is not None else ""
        if j.is_bare:
            out.append(f"* {j.name}  [{j.id}]  -> field {rj.entry_id}  (bare single-field){seed}")
            continue
        out.append(f"* {j.name}  [{j.id}]  -> entry field {rj.entry_id}{seed}")
        for folder in j.campaigns:
            ids = rj.campaign_ids[folder]
            lo, hi, k = rj.flag_windows[folder]
            rng = f"{min(ids)}..{max(ids)}" if ids else "(empty)"
            out.append(f"    [{folder:<16}] ids {rng} ({len(ids)} fields)   flags {lo}..{hi} (K={k})")
        n_override = sum(1 for lk in j.links if not _is_unfilled(lk.src_field) and not _is_unfilled(lk.dst.field))
        n_auto = len(rj.links) - n_override
        out.append(f"    links: {len(rj.links)} cross-campaign warp(s) wired"
                   + (f" ({n_override} override + {n_auto} auto from .eb seams)" if n_override else
                      f" (all auto-derived from the real .eb seams -- no link rows)") + "; graph below")
        conn = campaign_connectivity(j.campaigns, _plain)        # the real warp graph, computed once per journey
        wired = {(d["src_campaign"], d["dst_campaign"]) for d in rj.links}   # explicit + auto-derived
        # the REAL connectivity from each campaign's .eb seams (zones/id order are a convenience, not a rule)
        for line in render_connectivity(j.campaigns, _plain, wired=wired, conn=conn):
            out.append("    " + line)
        if j.seed.party:
            out.append(f"    party: {', '.join(j.seed.party)}")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


# ---------------------------------------------------------------- the deploy plan (the in-game step's brain)
@dataclass
class CampaignDeployStep:
    """One campaign's deploy parameters within a journey: WHERE it installs (its own stacked ``mod_folder``,
    from its campaign.toml), its id band, and the journey-assigned disjoint ``flag_base`` (passed to
    ``build_campaign(flag_base=)`` so its bits don't clobber a sibling campaign's). Each campaign needs its
    OWN folder -- ``deploy_campaign`` WHOLESALE-replaces a folder, so two campaigns sharing one would clobber."""
    folder: str
    campaign_path: Path
    mod_folder: str
    id_lo: int
    id_hi: int
    flag_base: int
    members: int
    seed_blocks: "dict | None" = None    # the [journey.seed] capstone (entry campaign only; build_campaign seed=)


@dataclass
class LinkRewrite:
    """A cross-campaign hand-off realized as a byte-patch on the boundary member's deployed ``.eb`` (every
    language copy). ``mode`` picks how:
      * ``field_remap`` -- rewrite ``Field(seam.to_real)`` -> ``dst_id`` in place (``remap``;
        ``content.verbatim.remap_fields``, length-preserving). For a scripted/portal seam.
      * ``worldmap_inject`` -- body-replace the boundary's walk-out region handler (the one running
        ``WorldMap(loc)``) with a ``Field(dst_id)`` warp, reusing its existing map-edge zone (the elided
        world-map leg). ``dst_entrance`` = the arrival entrance set on the warp.
      * ``none`` -- not auto-wirable (no onward seam / ambiguous); ``retargetable`` is False."""
    src_campaign: str
    src_field: str
    src_id: int
    src_mod_folder: str
    eb_name: str                 # "EVT_<member>" -- the deployed .eb to patch (every lang copy)
    mode: str                    # "field_remap" | "worldmap_inject" | "none"
    remap: dict                  # {seam_to_real: dst_id}  (field_remap only; empty otherwise)
    dst_campaign: str
    dst_field: str
    dst_id: int
    dst_entrance: int
    seam_kinds: list
    retargetable: bool
    note: str = ""


@dataclass
class JourneyDeployPlan:
    """The whole manifest's in-game deploy, derived offline: each multi-campaign journey's campaign steps +
    link rewrites, the bare journeys (already-deployed -- the hub just points at them), the hub field id (New
    Game's target), and any mod-folder clobber conflict. Consumed by ``tools/deploy_journey.py``."""
    hub_field_id: "int | None"
    campaign_steps: list         # [CampaignDeployStep]  (deduped across journeys, by folder)
    links: list                  # [LinkRewrite]
    bare_entries: list           # [(journey_id, name, entry_id)]
    folder_conflicts: list       # [(mod_folder, folder_a, folder_b)] -- a wholesale-replace clobber
    entry_field_id: "int | None" = None   # the resolved opening entry id IF the manifest has exactly ONE
    #                                        journey (else None) -- the "New Game -> straight into the opening,
    #                                        no hub menu" target (deploy_journey.py --newgame entry)
    hub_folder: "str | None" = None       # the DEDICATED mod folder the hub field + the New-Game override deploy
    #                                        into (FF9CustomMap-<hub token>) -- a journey-OWNED folder the user
    #                                        stacks HIGHEST, NOT the ambient deploy-time highest (which a journey
    #                                        re-stack/band-collision may drop) and NOT a campaign folder (whose
    #                                        wholesale re-deploy would wipe the override).


def seed_to_field_blocks(seed: "JourneySeed | None") -> dict:
    """Translate a ``[journey.seed]`` into the story_flags New-Game capstone blocks the build already consumes
    (``startup`` / ``party`` / ``start_inventory`` / ``equipment``) -- NO new mechanism (docs/JOURNEYS.md §4.4).
    Returns only the blocks the seed sets (empty seed -> ``{}``). ``scenario`` + ``party`` are the
    **per-journey-clean** levers: they bake into the entry fork's OWN ``.eb`` (no cross-journey collision).
    ``inventory`` / ``equipment`` map to the **mod-global** New-Game CSVs (`InitialItems`/`DefaultEquipment`,
    read once at New Game, SHARED across a hub's journeys) -- clean only for a single-journey hub; for a
    multi-journey hub prefer scripted ``give_item`` on the entry (a follow-up). Party drops ``Zidane`` (New
    Game already seeds slot 0)."""
    if seed is None or seed.is_empty:
        return {}
    blocks: dict = {}
    startup: dict = {}
    if seed.scenario is not None:
        startup["scenario"] = seed.scenario
    if seed.raw.get("flags"):
        startup["flags"] = seed.raw["flags"]
    if startup:
        blocks["startup"] = startup
    add = [p for p in seed.party if str(p).strip().lower() != "zidane"]
    if add:
        blocks["party"] = {"add": add}
    inv = seed.raw.get("start_inventory", seed.raw.get("inventory"))
    if inv is not None:
        blocks["start_inventory"] = inv if isinstance(inv, dict) else {"items": inv}
    if seed.raw.get("equipment") is not None:
        blocks["equipment"] = seed.raw["equipment"]
    return blocks


def _seam_remap(src_plan: "_campaign.CampaignPlan", member_name: str, dst_id: int, *,
                dst_reals=frozenset()) -> dict:
    """Resolve a boundary member's onward seam into the cross-campaign link MODE. Returns a dict
    ``{mode, remap, kinds, retargetable, note}``. ``dst_reals`` = the REAL field ids that ARE the next campaign
    (its members' donor ids); supplying it lets a door straight INTO the next campaign be told apart from an
    incidental in-zone door. Order:
      * ``field_remap`` (PRECISE) -- the member has a ``Field()`` door whose target is in ``dst_reals`` (a real
        warp straight into the next campaign, e.g. a dungeon mouth -> the next field): patch that door to
        ``dst_id`` (``content.verbatim.remap_fields``). Beats the overworld -- the real door is the exact boundary.
      * ``worldmap_inject`` -- NO door into the next campaign, but an OVERWORLD seam (a zone's world-map exit):
        the boundary leaves to the world map, so body-REPLACE its walk-out region with a ``Field(dst_id)`` warp
        (``apply_link_rewrites``). This is the cross-zone boundary for a world-connected chain, and is NOT
        shadowed by the member's incidental in-zone ``Field()`` doors (the dali/south_gate fix).
      * ``field_remap`` (REPURPOSE) -- no overworld and exactly ONE out-of-chain ``Field()`` door (not into the
        next campaign): repurpose it to ``dst_id`` (the lone-onward-door heuristic).
      * ``none`` -- no onward seam, or several ``Field()`` doors and no overworld (ambiguous): not auto-wired.

    NB (in-game-UNVERIFIED): the worldmap_inject-over-in-zone-doors path is a deploy-side change -- it matches the
    real game (you leave a zone via the world map) and preserves the proven Ice Cavern cases (entrance = pure
    overworld -> inject; internal exit = a lone ``Field()`` -> remap), but a both-seams boundary's wiring should
    be confirmed in a playtest (``apply_link_rewrites`` reports found=False if no walk-out region matches)."""
    g = _campaign.campaign_graph(src_plan)
    node = g.by_name.get(member_name)
    seams = node.seams if node else []
    kinds = sorted({s.get("kind") for s in seams if s.get("kind")})
    targets = sorted({s["to_real"] for s in seams if isinstance(s.get("to_real"), int)})
    into_next = [t for t in targets if t in dst_reals]
    if into_next:                                # a real door straight into the next campaign -> PRECISE boundary
        return {"mode": "field_remap", "remap": {into_next[0]: dst_id}, "kinds": kinds, "retargetable": True,
                "note": "" if len(into_next) == 1 else f"{len(into_next)} doors into the next campaign "
                        f"{into_next}; took the first"}
    if "overworld" in kinds:                      # no door into the next campaign -> the world-map exit IS it
        return {"mode": "worldmap_inject", "remap": {}, "kinds": kinds, "retargetable": True,
                "note": "overworld exit -- body-replace the walk-out region with Field(dst) (elided world leg)"
                        + (f"; ignores {len(targets)} in-zone Field() door(s) {targets}" if targets else "")}
    if len(targets) == 1:                         # a lone out-of-chain Field() door -> repurpose it to the next
        return {"mode": "field_remap", "remap": {targets[0]: dst_id}, "kinds": kinds,
                "retargetable": True, "note": ""}
    if len(targets) > 1:
        return {"mode": "none", "remap": {}, "kinds": kinds, "retargetable": False,
                "note": f"{len(targets)} Field() seam targets {targets} -- ambiguous; pick a "
                        f"single-onward-seam boundary member, or split the boundary"}
    return {"mode": "none", "remap": {}, "kinds": kinds, "retargetable": False,
            "note": "no onward seam on the boundary member -- nothing to retarget into the next campaign"}


def build_deploy_plan(manifest: JourneyManifest) -> JourneyDeployPlan:
    """Resolve the whole manifest into its in-game deploy plan (PURE over the manifest + campaign plans; no
    game install). Lint first (:func:`lint_manifest`) -- this assumes a clean manifest. Each multi-campaign
    journey contributes its campaigns (each at its disjoint flag window, into its own mod folder) + link
    rewrites; bare journeys are recorded as already-deployed hub targets."""
    plans = load_campaign_plans(manifest)
    steps, links, bare, conflicts = [], [], [], []
    folder_seen: dict = {}                       # mod_folder -> the campaign folder that claimed it
    done_folders: set = set()                    # campaign folders already turned into a step (dedup)
    entry_ids: list = []                         # each journey's resolved entry id (for the single-journey case)
    for j in manifest.journeys:
        if j.is_bare:
            bare.append((j.id, j.name, int(j.entry.field)))
            entry_ids.append(int(j.entry.field))
            continue
        rj = resolve_journey(j, plans)
        entry_ids.append(rj.entry_id)
        for folder in j.campaigns:
            plan, _ = plans[folder]
            if folder not in done_folders:
                ids = rj.campaign_ids[folder]
                lo, _hi, _k = rj.flag_windows[folder]
                seed_blocks = seed_to_field_blocks(j.seed) if folder == j.entry.campaign else {}
                steps.append(CampaignDeployStep(
                    folder=folder, campaign_path=_campaign_path(manifest.root, folder),
                    mod_folder=plan.mod_folder, id_lo=min(ids), id_hi=max(ids), flag_base=lo,
                    members=len(ids), seed_blocks=seed_blocks or None))
                done_folders.add(folder)
                prior = folder_seen.get(plan.mod_folder)
                if prior is not None and prior != folder:
                    conflicts.append((plan.mod_folder, prior, folder))
                folder_seen.setdefault(plan.mod_folder, folder)
        # BATCH the field_remap links by source member: many cross-campaign warps land on ONE member's .eb
        # (a cutscene hub like at_sln retargets ~14 Field()s), so merge them into a SINGLE multi-entry remap --
        # one .eb patch + one backup per member (no per-link read-after-write accumulation). worldmap_inject
        # links stay per-link (each body-replaces a distinct region).
        field_groups: dict = {}                      # src_field -> merged remap (insertion-ordered)
        for lk in rj.links:
            src_plan = plans[lk["src_campaign"]][0]
            dst_plan = plans[lk["dst_campaign"]][0]
            # the arrival member's DONOR id -> a boundary door that lands there is the precise cross-zone warp
            dst_real = next((m.real_id for m in dst_plan.members if m.new_id == lk["dst_id"]), None)
            sr = _seam_remap(src_plan, lk["src_field"], lk["dst_id"],
                             dst_reals=frozenset({dst_real}) if dst_real else frozenset())
            if sr["mode"] == "field_remap" and sr["remap"]:
                g = field_groups.get(lk["src_field"])
                if g is None:
                    g = field_groups[lk["src_field"]] = {"remap": {}, "lk": lk, "src_plan": src_plan,
                                                          "kinds": set(), "dsts": []}
                g["remap"].update(sr["remap"])           # merge {to_real: dst_id}; distinct to_reals never collide
                g["kinds"].update(sr["kinds"])
                g["dsts"].append(lk["dst_campaign"])
            else:                                        # worldmap_inject / none -> one LinkRewrite per link
                links.append(LinkRewrite(
                    src_campaign=lk["src_campaign"], src_field=lk["src_field"], src_id=lk["src_id"],
                    src_mod_folder=src_plan.mod_folder, eb_name=f"EVT_{lk['src_field']}",
                    mode=sr["mode"], remap=sr["remap"],
                    dst_campaign=lk["dst_campaign"], dst_field=str(lk["dst_field"]), dst_id=lk["dst_id"],
                    dst_entrance=int(lk.get("dst_entrance", 0)),
                    seam_kinds=sr["kinds"], retargetable=sr["retargetable"], note=sr["note"]))
        for sf, g in field_groups.items():               # one merged field_remap LinkRewrite per source member
            lk, n = g["lk"], len(g["remap"])
            dcs = sorted(set(g["dsts"]))
            links.append(LinkRewrite(
                src_campaign=lk["src_campaign"], src_field=sf, src_id=lk["src_id"],
                src_mod_folder=g["src_plan"].mod_folder, eb_name=f"EVT_{sf}",
                mode="field_remap", remap=dict(g["remap"]),
                dst_campaign=dcs[0] if len(dcs) == 1 else f"{len(dcs)} campaigns",
                dst_field=f"{n} warp(s)" if n > 1 else str(lk["dst_field"]), dst_id=lk["dst_id"],
                dst_entrance=0, seam_kinds=sorted(g["kinds"]), retargetable=True,
                note=f"{n} cross-campaign warp(s) -> {', '.join(dcs)}"))
    hub_id = int(manifest.hub["id"]) if manifest.hub.get("id") is not None else None
    single_entry = entry_ids[0] if len(manifest.journeys) == 1 else None    # "straight into the opening" target
    hub_folder = None
    if hub_id is not None:                       # a dedicated journey-owned folder for the hub + New-Game override
        from . import hub as _hub
        base = f"FF9CustomMap-{_hub.name_token(manifest.hub.get('name', 'hub')).lower()}"
        camp = {s.mod_folder for s in steps}     # keep it distinct from EVERY campaign folder (no re-deploy clobber)
        hub_folder, i = base, 1                   # loop (not one-shot) so the fallback can't itself collide
        while hub_folder in camp:
            hub_folder = f"{base}-hub{'' if i == 1 else i}"
            i += 1
    return JourneyDeployPlan(hub_field_id=hub_id, campaign_steps=steps, links=links, bare_entries=bare,
                             folder_conflicts=conflicts, entry_field_id=single_entry, hub_folder=hub_folder)


# ---- pre-flight collision sweep (the "remove these stale folders" report, before any install) ----

@dataclass
class JourneyCollisions:
    """Does this journey's FINAL set of registrations clash with the live ``Memoria.ini`` ``FolderNames`` stack?
    Computed BEFORE any install (``EventDB`` is GLOBAL across folders -- a shared id loads the wrong ``.eb`` ->
    black screen; CLAUDE.md §3).

    ``external_*`` collide with a folder that is NOT part of this journey -- the real BLOCKER (a superseded prior
    deploy / an unrelated mod on the same band); the fix is to drop that folder from ``FolderNames``.
    ``stale_own`` are this journey's OWN folders that still hold a PRIOR deploy whose ids overlap a SIBLING's
    final band -- harmless (each is wholesale-replaced on deploy), but they would trip ``deploy_campaign``'s
    per-folder id check mid-install, which is exactly why ``deploy_journey`` relaxes THAT one check
    (``--allow-id-collision``) once this external sweep comes back clean."""
    external_ids: tuple = ()      # (id, my_folder, my_name, other_folder, other_kind, other_name)
    external_names: tuple = ()    # (kind, name, my_folder, other_folder)
    stale_own: tuple = ()         # (folder, (overlapping_ids, ...))
    external_folders: tuple = ()  # the distinct external folders that collide (the "remove these" headline)

    @property
    def has_blockers(self) -> bool:
        return bool(self.external_ids or self.external_names)


def _journey_registrations(plan, *, dists=None, hub_name=None):
    """This journey's FINAL registrations: ``{id: (mod_folder, name)}``, ``{eb_name: mod_folder}``,
    ``{scene_name: mod_folder}``. Reads the built dists when given (authoritative, incl. FBG scene names), else
    derives ids + ``EVT_<member>`` names straight from each campaign manifest (no build -- the dry-run path).
    ``hub_name`` (the ``[hub] name``) adds the hub's own ``EVT_<token>`` to the name axis -- a BG-borrow hub
    ships its ``.eb`` but NO novel FBG scene dir (it points at the borrowed real art), so EVT is its only own
    name."""
    from . import deploystack as _DS
    ids: dict = {}
    eb: dict = {}
    scene: dict = {}
    for s in plan.campaign_steps:
        d = (dists or {}).get(s.folder)
        if d is not None:                                  # authoritative: read what was actually built
            d = Path(d)
            for i, (_k, nm) in _DS.dictionary_ids_at(d).items():
                ids[i] = (s.mod_folder, nm)
            for nm in _DS.eb_names_at(d):
                eb[nm] = s.mod_folder
            for nm in _DS.scene_names_at(d):
                scene[nm] = s.mod_folder
        else:                                              # cheap pre-build derivation (ids + EVT names)
            cp = _campaign.load_campaign(s.campaign_path)
            for m in cp.members:
                ids[m.new_id] = (s.mod_folder, m.name)
                eb[f"EVT_{m.name}"] = s.mod_folder
    if plan.hub_field_id is not None and plan.hub_folder:   # the hub registers its own id (+ EVT name) too
        ids.setdefault(int(plan.hub_field_id), (plan.hub_folder, "hub"))
        if hub_name:
            eb.setdefault(f"EVT_{_hub.name_token(hub_name)}", plan.hub_folder)
    return ids, eb, scene


def preflight_collisions(plan, game_dir, *, dists=None, hub_name=None) -> JourneyCollisions:
    """Sweep this journey's FINAL ids/names against the live ``Memoria.ini`` ``FolderNames`` stack BEFORE any
    install. Folders this journey OWNS are excluded from the blocker set (each is wholesale-replaced); a
    leftover/superseded FOREIGN folder on the same band is the real blocker. Read-only -- touches no game files.
    Pass ``dists`` (``{folder: dist_dir}``) after the offline build for an authoritative pass (FBG names too),
    and ``hub_name`` (the ``[hub] name``) to also sweep the hub's ``EVT_<token>`` vs foreign folders."""
    from . import deploystack as _DS
    game_dir = Path(game_dir)
    ini = game_dir / "Memoria.ini"
    order = _DS.parse_folder_names(ini.read_text(encoding="utf-8", errors="ignore")) if ini.is_file() else []
    own = {s.mod_folder for s in plan.campaign_steps}
    if plan.hub_folder:
        own.add(plan.hub_folder)
    want_ids, want_eb, want_scene = _journey_registrations(plan, dists=dists, hub_name=hub_name)
    ext_ids: list = []
    ext_names: list = []
    ext_folders: set = set()
    for f in [x for x in order if x not in own]:           # only FOREIGN folders are blockers
        their = _DS.dictionary_ids_at(game_dir / f)
        for i in sorted(want_ids):
            if i in their:
                mf, nm = want_ids[i]
                ok, on = their[i]
                ext_ids.append((i, mf, nm, f, ok, on))
                ext_folders.add(f)
        their_eb = _DS.eb_names_at(game_dir / f)
        for nm in sorted(want_eb):
            if nm in their_eb:
                ext_names.append(("eb", nm, want_eb[nm], f))
                ext_folders.add(f)
        their_sc = _DS.scene_names_at(game_dir / f)
        for nm in sorted(want_scene):
            if nm in their_sc:
                ext_names.append(("scene", nm, want_scene[nm], f))
                ext_folders.add(f)
    # informational: which of THIS journey's OWN folders still hold a SIBLING's band (replaced on deploy)
    own_final = set(want_ids)
    stale: list = []
    for s in plan.campaign_steps:
        live = set(_DS.dictionary_ids_at(game_dir / s.mod_folder))
        sib = sorted(i for i in live & own_final if want_ids[i][0] != s.mod_folder)
        if sib:
            stale.append((s.mod_folder, tuple(sib)))
    return JourneyCollisions(tuple(ext_ids), tuple(ext_names), tuple(stale), tuple(sorted(ext_folders)))


def render_collision_report(col: JourneyCollisions) -> str:
    """A human-readable pre-flight report (``""`` when fully clean): names the superseded ``FolderNames``
    folders to remove (the blocker), then notes this journey's own folders that will be replaced in place."""
    from .chain import format_id_ranges
    lines: list = []
    if col.has_blockers:
        lines.append("PRE-FLIGHT COLLISION: this journey re-registers ids/names that a Memoria.ini FolderNames "
                     "folder NOT part of this journey still uses. FF9DBAll.EventDB is GLOBAL across folders, so a "
                     "shared id loads the WRONG .eb (-> black screen).")
        for (i, mf, nm, f, ok, on) in col.external_ids:
            lines.append(f"  - id {i}  ({mf} '{nm}')  collides with  '{f}' ({ok} '{on}')")
        for (kind, nm, mf, f) in col.external_names:
            lines.append(f"  - {kind} name '{nm}'  ({mf})  collides with  '{f}'")
        lines.append("FIX: remove the superseded folder(s) from Memoria.ini [Mod] FolderNames -- "
                     + ", ".join(col.external_folders) + " -- then re-deploy (this journey re-registers those "
                     "bands itself). No game files were touched.")
    if col.stale_own:
        if lines:
            lines.append("")
        lines.append("note: these of THIS journey's OWN folders still hold a prior deploy whose ids overlap a "
                     "sibling; each is wholesale-replaced on deploy, so the per-folder id check is relaxed:")
        for (f, ids) in col.stale_own:
            lines.append(f"  - {f}: had id(s) {format_id_ranges(list(ids))}")
    return "\n".join(lines)


def render_deploy_playbook(manifest: JourneyManifest, *, hub_toml: str = "<hub.field.toml>",
                           repo_rel: str = "", journeys_ref: "str | None" = None) -> str:
    """The ordered, copy-pasteable command sequence to deploy a journeys manifest in-game, built from the
    deploy plan. Each step is an EXISTING, individually revert-guarded tool (so the human applies + playtests
    incrementally -- "one change per in-game test"); the only journey-unique step is the link `.eb` remap
    (``deploy_journey.py --apply-links``). PURE text (no game touched). ``repo_rel`` prefixes campaign paths;
    ``journeys_ref`` is the manifest path as the human will type it (default: its bare name)."""
    plan = build_deploy_plan(manifest)
    pre = (repo_rel.rstrip("/") + "/") if repo_rel else ""
    jref = journeys_ref or manifest.path.name
    seeded = [s for s in plan.campaign_steps if s.seed_blocks]
    L = ["# === Journey deploy playbook (run from the repo root; apply + PLAYTEST each step in order) ===",
         "# Memoria.ini [Mod] FolderNames must STACK every folder below; the hub folder is HIGHEST.",
         f"# ONE-SHOT: `py tools/deploy_journey.py {jref} --apply` runs steps 1-3 (campaigns + links + hub) + "
         "seeds the entry + writes ONE revert. New Game is NOT touched (reach the hub via F6; add "
         "--newgame hub|entry to opt in).",
         ("# (the manual steps below do NOT apply [journey.seed] -- use --apply for a seeded journey)"
          if seeded else ""),
         ""]
    L = [x for i, x in enumerate(L) if x or i == len(L) - 1]   # drop the empty seeded-note line if absent
    if plan.folder_conflicts:
        L.append("# !! MOD-FOLDER CLOBBER -- these campaigns share a folder (deploy_campaign wholesale-replaces "
                 "it):")
        for mf, a, b in plan.folder_conflicts:
            L.append(f"#    {a!r} and {b!r} both -> {mf!r}. Give each campaign its OWN mod_folder.")
        L.append("")
    L.append("# 1. Deploy each campaign into its own stacked folder, at its disjoint flag window (--no-warp: "
             "the hub owns New Game):")
    for s in plan.campaign_steps:
        seed_note = ""
        if s.seed_blocks:
            bits = []
            if s.seed_blocks.get("startup", {}).get("scenario") is not None:
                bits.append(f"scenario={s.seed_blocks['startup']['scenario']}")
            if s.seed_blocks.get("party", {}).get("add"):
                bits.append(f"party+={s.seed_blocks['party']['add']}")
            seed_note = f"   # SEED (via --apply): {', '.join(bits)}" if bits else "   # SEED (via --apply)"
        L.append(f"py tools/deploy_campaign.py {pre}{s.campaign_path.as_posix() if not pre else s.folder + '/campaign.toml'} "
                 f"--apply --no-warp --mod-folder {s.mod_folder} --flag-base {s.flag_base}"
                 f"   # ids {s.id_lo}..{s.id_hi}{seed_note}")
    if not plan.campaign_steps:
        L.append("#   (no multi-campaign journeys -- all journeys are bare single fields, already deployed)")
    L.append("")
    L.append("# 2. Wire the cross-campaign links (retarget each boundary .eb Field() exit -> the next entry):")
    wired = [lk for lk in plan.links if lk.retargetable]
    for lk in plan.links:
        dst = f"[{lk.dst_campaign}/{lk.dst_field}]"
        if lk.mode == "field_remap":
            L.append(f"#    {lk.src_campaign}/{lk.src_field} (EVT, field {lk.src_id})  Field({list(lk.remap)[0]}) "
                     f"-> Field({lk.dst_id})  {dst}")
        elif lk.mode == "worldmap_inject":
            L.append(f"#    {lk.src_campaign}/{lk.src_field} (EVT, field {lk.src_id})  overworld exit "
                     f"-> Field({lk.dst_id}) region  {dst}  (elided world-map leg)")
        else:
            L.append(f"#    !! {lk.src_campaign}/{lk.src_field} -> {lk.dst_campaign}/{lk.dst_field}: NOT "
                     f"auto-wired -- {lk.note}")
    if wired:
        L.append(f"py tools/deploy_journey.py {jref} --apply-links")
        L.append("#    !! run --apply-links LAST + re-run it after ANY campaign re-deploy: deploy_campaign "
                 "wholesale-replaces a folder, which WIPES the link patch.")
    elif plan.links:
        L.append("#   (no auto-wirable links -- see the notes above)")
    else:
        L.append("#   (no cross-campaign links)")
    L.append("")
    L.append(f"# 3. Emit + deploy the hub field into its OWN folder {plan.hub_folder!r} (reach it via F6 -> Warp; "
             "New Game stays untouched):")
    L.append(f"py -m ff9mapkit assemble-journey {jref} --out {hub_toml}")
    if plan.hub_field_id is not None:
        L.append(f"py tools/deploy_field.py {hub_toml} --id {plan.hub_field_id} --mod-folder {plan.hub_folder}")
        L.append("# OPTIONAL New-Game landing (SINGLE-OWNER -- replaces your current target; into the hub folder):")
        L.append(f"py tools/wire_newgame_from_stock.py {plan.hub_field_id} --mod-folder {plan.hub_folder}"
                 f"   # New Game -> the hub MENU")
        if plan.entry_field_id is not None:
            L.append(f"py tools/wire_newgame_from_stock.py {plan.entry_field_id} --mod-folder {plan.hub_folder}"
                     f"   # New Game -> STRAIGHT into the opening (single arc; keeps the real FMV)")
    L.append("")
    if plan.bare_entries:
        L.append("# Bare single-field journeys (already deployed elsewhere -- the hub just warps to them):")
        for jid, name, eid in plan.bare_entries:
            L.append(f"#    {name!r} [{jid}] -> field {eid}")
    folders = ([plan.hub_folder] if plan.hub_folder else []) + [s.mod_folder for s in plan.campaign_steps]
    if folders:
        L.append("# Memoria.ini [Mod] FolderNames (HIGHEST first), then your video/passthrough mods below:")
        L.append("#   FolderNames = " + ", ".join(f'"{f}"' for f in folders) + ', "<your other mods, e.g. Moguri>"')
    if plan.campaign_steps:
        lo = min(s.id_lo for s in plan.campaign_steps)
        hi = max(s.id_hi for s in plan.campaign_steps)
        L.append(f"#   This journey uses field ids {lo}..{hi} -- REMOVE any OTHER custom-field folder that deploys "
                 f"in that range (EventDB is GLOBAL -> a collision black-screens).")
    L.append("# Then RELAUNCH once (new ids register on a fresh launch) and PLAYTEST.")
    return "\n".join(L) + "\n"


# The WorldMap opcode (an overworld exit). Its operand is a world-map LOCATION id (9000-9012), NOT a field
# id -- so it can't be Field-retargeted; the elided world-map leg body-REPLACES the walk-out region instead.
# (eb/_optables.py; ground-truthed against real fields 300/311/312.)
_WORLDMAP_OP = 0xB6


def _worldmap_warp_body(dst_id: int, entrance: int = 0) -> bytes:
    """The proven walk-out region handler body that warps ``Field(dst_id)`` -- lifted from the in-game-proven
    field-109 gateway template (:mod:`ff9mapkit.content.gateway`): its tag-2 (tread) func body, patched with
    the destination field + arrival entrance. Spliced over a boundary field's WorldMap walk-out handler, it
    reuses that region's existing map-edge zone (its tag-0 SetRegion is untouched), turning "leave to the
    world map" into "warp into the next campaign" (the elided world-map leg)."""
    import struct
    from . import data
    from .content import gateway
    tpl = bytearray(data.region_template())
    struct.pack_into("<H", tpl, gateway.REL_ENTRANCE, int(entrance) & 0xFFFF)
    struct.pack_into("<H", tpl, gateway.REL_FIELD, int(dst_id) & 0xFFFF)
    fc, fbase = tpl[1], 2
    funcs = [(tpl[fbase + i * 4] | (tpl[fbase + i * 4 + 1] << 8),
              tpl[fbase + i * 4 + 2] | (tpl[fbase + i * 4 + 3] << 8)) for i in range(fc)]
    idx = next((i for i, (t, _) in enumerate(funcs) if t == 2), None)
    if idx is None:                                # kit invariant: the template's warp lives in tag 2
        raise JourneyError("gateway template has no tag-2 warp func (kit invariant broken)")
    start = fbase + funcs[idx][1]
    end = fbase + funcs[idx + 1][1] if idx + 1 < fc else len(tpl)
    return bytes(tpl[start:end])


def _worldmap_region_funcs(eb_bytes: bytes) -> list:
    """The walk-out region handlers that run an overworld exit: ``(entry_idx, func_tag)`` for every tag-2
    (tread) func containing a ``WorldMap`` op. These are the bodies the world-map-leg injection replaces with
    a ``Field(dst)`` warp; their entry's tag-0 SetRegion (the map-edge zone) is left intact, so the player
    crossing that same edge now warps into the next campaign instead of the world map."""
    from .eb import EbScript
    eb = EbScript.from_bytes(eb_bytes)
    hits = []
    for ei, e in enumerate(eb.entries):
        if e.empty:
            continue
        for f in e.funcs:
            if f.tag == 2 and any(i.op == _WORLDMAP_OP for i in eb.instrs(f)):
                hits.append((ei, f.tag))
    return hits


def apply_link_rewrites(plan: JourneyDeployPlan, game_root, *, dry_run=False, backup_dir=None) -> list:
    """Apply each retargetable :class:`LinkRewrite` to the boundary member's DEPLOYED ``.eb`` (every language
    copy under ``<game>/<src_mod_folder>``) -- the one journey-unique in-game step. Two modes:
      * ``field_remap`` -- ``content.verbatim.remap_fields`` patches the ``Field(to_real)`` literal -> dst,
        length-preserving.
      * ``worldmap_inject`` -- ``eb.edit.replace_function_body`` swaps each WorldMap walk-out region handler
        for the proven ``Field(dst)`` warp body (the elided world-map leg), reusing the region's zone.
    Returns ``[{eb, mode, langs, regions, backups, found}]``. ``dry_run`` reports without writing; each
    patched file is backed up to ``backup_dir`` first (reversibility -- Hard Constraint §2)."""
    from .content.verbatim import remap_fields
    from .eb import edit as _edit
    game_root = Path(game_root)
    results = []
    for lk in plan.links:
        if not lk.retargetable:
            continue
        mod = game_root / lk.src_mod_folder
        ebs = sorted(mod.rglob(f"{lk.eb_name}.eb.bytes")) if mod.is_dir() else []
        body = _worldmap_warp_body(lk.dst_id, lk.dst_entrance) if lk.mode == "worldmap_inject" else None
        touched, backups, regions = [], [], 0
        for p in ebs:
            blob = p.read_bytes()
            if lk.mode == "field_remap":
                out = remap_fields(blob, lk.remap)
            elif lk.mode == "worldmap_inject":
                out, n = blob, 0
                for (ei, tag) in _worldmap_region_funcs(blob):   # slot indices are stable across replaces
                    out = _edit.replace_function_body(out, ei, tag, body)
                    n += 1
                regions = n                                      # structural -> identical across langs
            else:
                out = blob
            if out == blob:                       # nothing matched in this copy (wrong lang / no region)
                continue
            if not dry_run:
                if backup_dir:
                    Path(backup_dir).mkdir(parents=True, exist_ok=True)
                    # path-relative slug so per-lang copies (same filename, different dir) don't collide
                    rel = p.relative_to(mod).as_posix().replace("/", "_")
                    bk = Path(backup_dir) / f"{lk.src_mod_folder}_{rel}.preLINK"
                    if not bk.exists():               # keep the ORIGINAL: a member with several auto-wired warps
                        bk.write_bytes(blob)           # gets multiple rewrites -- don't clobber the first backup
                    backups.append((str(p), str(bk)))
                p.write_bytes(out)
            touched.append(str(p))
        results.append({"eb": lk.eb_name, "mode": lk.mode, "remap": dict(lk.remap), "dst_id": lk.dst_id,
                        "langs": len(touched), "regions": regions, "files": touched, "backups": backups,
                        "found": bool(touched)})
    return results
