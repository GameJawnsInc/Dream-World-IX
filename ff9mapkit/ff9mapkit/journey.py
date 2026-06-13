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
    """A cross-campaign hand-off: the boundary member ``src_field`` in ``src_campaign`` (an out-of-chain seam
    -- the point where, in the live game, the player would leave for the world map) is realized as a live warp
    into ``dst`` (the next campaign's entry). One link per campaign boundary (N campaigns -> N-1 links)."""
    src_campaign: str
    src_field: str            # the boundary member name (handoff schema: from.field, alias from.seam)
    dst: JourneyRef


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
    return JourneyLink(src_campaign=str(frm["campaign"]), src_field=str(src_field),
                       dst=_ref_from(raw["to"], what=f"journey {jid!r} link 'to'"))


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
        journeys.append(Journey(
            id=jid, name=str(j.get("name") or _hub._humanize(jid)), campaigns=campaigns, entry=entry,
            seed=_seed_from(j.get("seed")), links=links,
            set_scenario=int(sc) if sc is not None else None))

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


def _member_id(plan: "_campaign.CampaignPlan", fieldref, *, what: str) -> int:
    """Resolve a member NAME (preferred) or a raw id against a campaign's members -> the global field id.
    A name must match a member; a raw int passes through (lint flags a raw id that isn't a member)."""
    by_name = {m.name: m for m in plan.members}
    if isinstance(fieldref, str) and fieldref in by_name:
        return by_name[fieldref].new_id
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


def resolve_journey(journey: Journey, plans: dict) -> ResolvedJourney:
    """Resolve a journey into the global namespace using the pre-loaded campaign plans (see
    :func:`load_campaign_plans`): the entry field id, per-campaign member id lists, assigned flag windows, and
    each link's src/dst global ids. PURE over the manifest + plans (no game install). Assumes the campaigns
    referenced exist in ``plans`` -- :func:`lint_manifest` validates that first."""
    if journey.is_bare:
        return ResolvedJourney(journey=journey, entry_id=int(journey.entry.field),
                               campaign_ids={}, flag_windows={}, flag_high=FIRST_SAFE_FLAG, links=[])

    entry_plan, _ = plans[journey.entry.campaign]
    entry_id = _member_id(entry_plan, journey.entry.field, what=f"journey {journey.id!r} entry")
    campaign_ids = {f: [m.new_id for m in plans[f][0].members] for f in journey.campaigns}
    flag_windows, flag_high = _flag_windows(journey, plans)

    links = []
    for lk in journey.links:
        src_plan, _ = plans[lk.src_campaign]
        dst_plan, _ = plans[lk.dst.campaign]
        links.append({
            "src_campaign": lk.src_campaign, "src_field": lk.src_field,
            "src_id": _member_id(src_plan, lk.src_field, what=f"journey {journey.id!r} link from"),
            "dst_campaign": lk.dst.campaign, "dst_field": lk.dst.field,
            "dst_id": _member_id(dst_plan, lk.dst.field, what=f"journey {journey.id!r} link to")})
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
        errors.append("no [[journey]] rows -- a journeys manifest needs at least one journey to select")
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
                cerr, cwarn = _campaign.lint_campaign(plan, cdir)
            except (_campaign.CampaignError, ValueError) as e:
                errors.append(f"campaign {folder!r}: {e}")
                continue
            errors.extend(f"campaign {folder!r}: {e}" for e in cerr)
            warnings.extend(f"campaign {folder!r}: {w}" for w in cwarn)

    # (d) THE GLOBAL ID-DISJOINTNESS GUARANTEE (docs/JOURNEYS.md §8): every member of every campaign + every
    #     bare entry id share one EventDB/SceneData namespace -- all are registered at launch, so a collision
    #     is a hard launch failure regardless of which journey the player picks.
    owner: dict = {}                              # global field id -> a human label of who claims it
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
    for j in manifest.journeys:
        if j.is_bare:
            try:
                _claim(int(j.entry.field), f"journey {j.id!r} (bare entry)")
            except (TypeError, ValueError):
                errors.append(f"journey {j.id!r}: bare entry {j.entry.field!r} must be a field id (int)")

    # (e) id band range (every claimed id in the custom band)
    for fid, label in sorted(owner.items()):
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
            warnings.append(f"journey {j.id!r}: entry id {j.entry.field} is not a member of campaign "
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
            if lk.src_field not in names_by[lk.src_campaign]:
                errors.append(f"journey {j.id!r}: link source {lk.src_field!r} is not a member of "
                              f"{lk.src_campaign!r}")
            elif not _member_has_seam(plans[lk.src_campaign][0], lk.src_field):
                warnings.append(f"journey {j.id!r}: link source {lk.src_campaign!r}/{lk.src_field!r} has no "
                                f"out-of-chain seam -- it's not a boundary, so there's nothing to retarget "
                                f"into the next campaign (the assembler will inject a fresh warp instead).")
            dstf = lk.dst.field
            if isinstance(dstf, str) and dstf not in names_by[lk.dst.campaign]:
                errors.append(f"journey {j.id!r}: link target {dstf!r} is not a member of {lk.dst.campaign!r}")

        # connectivity: every campaign reachable from the entry campaign via links; link count = N-1
        _lint_chain_connectivity(j, errors, warnings)

    # seed range (== story_flags capstone; deeper item/party validation is story_flags' at apply-time)
    if j.seed.scenario is not None and not (0 <= j.seed.scenario <= SCENARIO_MAX):
        errors.append(f"journey {j.id!r}: [journey.seed] scenario {j.seed.scenario} out of range "
                      f"(0-{SCENARIO_MAX})")
    for pc in j.seed.party:
        if not isinstance(pc, str) or not pc.strip():
            errors.append(f"journey {j.id!r}: [journey.seed] party entries must be character names (got {pc!r})")


def _lint_chain_connectivity(j: Journey, errors: list, warnings: list) -> None:
    """A journey's campaigns must form a connected chain from the entry campaign via its links (else a listed
    campaign is unreachable -- dead content). Warns on an unreachable campaign + on a link count that isn't the
    expected N-1 for a simple chain."""
    if len(j.campaigns) <= 1:
        if j.links:
            warnings.append(f"journey {j.id!r}: {len(j.links)} link(s) but only {len(j.campaigns)} campaign "
                            f"-- a single-campaign journey needs no links")
        return
    adj: dict = {c: set() for c in j.campaigns}
    for lk in j.links:
        if lk.src_campaign in adj and lk.dst.campaign in adj:
            adj[lk.src_campaign].add(lk.dst.campaign)
    reached, stack = {j.entry.campaign}, [j.entry.campaign]
    while stack:
        for nxt in adj.get(stack.pop(), ()):
            if nxt not in reached:
                reached.add(nxt)
                stack.append(nxt)
    unreachable = [c for c in j.campaigns if c not in reached]
    if unreachable:
        warnings.append(f"journey {j.id!r}: campaign(s) {unreachable} unreachable from the entry campaign "
                        f"{j.entry.campaign!r} via [[journey.link]]s -- add a link, or drop them.")
    if len(j.links) != len(j.campaigns) - 1:
        warnings.append(f"journey {j.id!r}: {len(j.links)} link(s) for {len(j.campaigns)} campaigns "
                        f"(a simple chain has {len(j.campaigns) - 1}).")


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
                                         set_scenario=j.hub_scenario))
    return _hub.hubspec_from_table(manifest.hub, hub_journeys)


def generate_hub(journeys_path, out_path=None) -> dict:
    """Load a ``journeys.toml``, lint it, and emit the hub ``field.toml`` (resolving bare + multi-campaign
    journeys alike). Returns ``{path, spec, errors, warnings}``. Raises :class:`JourneyError` on a lint error.
    Pure offline codegen -- the existing build/deploy path then compiles the emitted hub field. (gen-hub is
    the bare-only twin; this is the full assembler's hub step.)"""
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
    text = _hub.render_hub_field_toml(spec, source=manifest.path.name)
    out_path.write_text(text, encoding="utf-8", newline="\n")
    return {"path": out_path, "spec": spec, "errors": errors, "warnings": list(warnings) + list(hwarn)}


# ---------------------------------------------------------------- read-only resolved view
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
        for lk in rj.links:
            out.append(f"    link  {lk['src_campaign']}/{lk['src_field']} (field {lk['src_id']})  "
                       f"-->  {lk['dst_campaign']}/{lk['dst_field']} (field {lk['dst_id']})")
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


@dataclass
class LinkRewrite:
    """A cross-campaign hand-off realized as a byte-patch: rewrite the boundary member's deployed ``.eb``
    ``Field(seam.to_real)`` exit -> the next campaign's entry global id (``content.verbatim.remap_fields``,
    length-preserving, all 7 langs). ``retargetable`` is False when the boundary has no ``Field()`` seam (an
    overworld exit -- the elided world-map leg needs a region-injected warp, a future step) or is ambiguous."""
    src_campaign: str
    src_field: str
    src_id: int
    src_mod_folder: str
    eb_name: str                 # "EVT_<member>" -- the deployed .eb to patch (every lang copy)
    remap: dict                  # {seam_to_real: dst_id}  (empty when not retargetable)
    dst_campaign: str
    dst_field: str
    dst_id: int
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


def _seam_remap(src_plan: "_campaign.CampaignPlan", member_name: str, dst_id: int):
    """Resolve a boundary member's onward seam into the ``Field()`` remap for a cross-campaign link. Returns
    ``(remap, seam_kinds, retargetable, note)``. Exactly ONE int seam target -> ``{to_real: dst_id}``; none
    (overworld-only) or several (ambiguous) -> empty remap + a note (not auto-wired)."""
    g = _campaign.campaign_graph(src_plan)
    node = g.by_name.get(member_name)
    seams = node.seams if node else []
    kinds = sorted({s.get("kind") for s in seams if s.get("kind")})
    targets = sorted({s["to_real"] for s in seams if isinstance(s.get("to_real"), int)})
    if len(targets) == 1:
        return {targets[0]: dst_id}, kinds, True, ""
    if not targets:
        return {}, kinds, False, ("no Field() seam on the boundary (overworld exit?) -- the elided world-map "
                                  "leg needs a region-injected warp, not a Field() retarget (future step)")
    return {}, kinds, False, (f"{len(targets)} Field() seam targets {targets} -- ambiguous; pick a "
                              f"single-onward-seam boundary member, or split the boundary")


def build_deploy_plan(manifest: JourneyManifest) -> JourneyDeployPlan:
    """Resolve the whole manifest into its in-game deploy plan (PURE over the manifest + campaign plans; no
    game install). Lint first (:func:`lint_manifest`) -- this assumes a clean manifest. Each multi-campaign
    journey contributes its campaigns (each at its disjoint flag window, into its own mod folder) + link
    rewrites; bare journeys are recorded as already-deployed hub targets."""
    plans = load_campaign_plans(manifest)
    steps, links, bare, conflicts = [], [], [], []
    folder_seen: dict = {}                       # mod_folder -> the campaign folder that claimed it
    done_folders: set = set()                    # campaign folders already turned into a step (dedup)
    for j in manifest.journeys:
        if j.is_bare:
            bare.append((j.id, j.name, int(j.entry.field)))
            continue
        rj = resolve_journey(j, plans)
        for folder in j.campaigns:
            plan, _ = plans[folder]
            if folder not in done_folders:
                ids = rj.campaign_ids[folder]
                lo, _hi, _k = rj.flag_windows[folder]
                steps.append(CampaignDeployStep(
                    folder=folder, campaign_path=_campaign_path(manifest.root, folder),
                    mod_folder=plan.mod_folder, id_lo=min(ids), id_hi=max(ids), flag_base=lo,
                    members=len(ids)))
                done_folders.add(folder)
                prior = folder_seen.get(plan.mod_folder)
                if prior is not None and prior != folder:
                    conflicts.append((plan.mod_folder, prior, folder))
                folder_seen.setdefault(plan.mod_folder, folder)
        for lk in rj.links:
            src_plan = plans[lk["src_campaign"]][0]
            remap, kinds, ok, note = _seam_remap(src_plan, lk["src_field"], lk["dst_id"])
            links.append(LinkRewrite(
                src_campaign=lk["src_campaign"], src_field=lk["src_field"], src_id=lk["src_id"],
                src_mod_folder=src_plan.mod_folder, eb_name=f"EVT_{lk['src_field']}", remap=remap,
                dst_campaign=lk["dst_campaign"], dst_field=str(lk["dst_field"]), dst_id=lk["dst_id"],
                seam_kinds=kinds, retargetable=ok, note=note))
    hub_id = int(manifest.hub["id"]) if manifest.hub.get("id") is not None else None
    return JourneyDeployPlan(hub_field_id=hub_id, campaign_steps=steps, links=links,
                             bare_entries=bare, folder_conflicts=conflicts)


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
    L = ["# === Journey deploy playbook (run from the repo root; apply + PLAYTEST each step in order) ===",
         "# Memoria.ini [Mod] FolderNames must STACK every folder below; the hub folder is HIGHEST.",
         ""]
    if plan.folder_conflicts:
        L.append("# !! MOD-FOLDER CLOBBER -- these campaigns share a folder (deploy_campaign wholesale-replaces "
                 "it):")
        for mf, a, b in plan.folder_conflicts:
            L.append(f"#    {a!r} and {b!r} both -> {mf!r}. Give each campaign its OWN mod_folder.")
        L.append("")
    L.append("# 1. Deploy each campaign into its own stacked folder, at its disjoint flag window (--no-warp: "
             "the hub owns New Game):")
    for s in plan.campaign_steps:
        L.append(f"py tools/deploy_campaign.py {pre}{s.campaign_path.as_posix() if not pre else s.folder + '/campaign.toml'} "
                 f"--apply --no-warp --mod-folder {s.mod_folder} --flag-base {s.flag_base}"
                 f"   # ids {s.id_lo}..{s.id_hi}")
    if not plan.campaign_steps:
        L.append("#   (no multi-campaign journeys -- all journeys are bare single fields, already deployed)")
    L.append("")
    L.append("# 2. Wire the cross-campaign links (retarget each boundary .eb Field() exit -> the next entry):")
    wired = [lk for lk in plan.links if lk.retargetable]
    for lk in plan.links:
        if lk.retargetable:
            L.append(f"#    {lk.src_campaign}/{lk.src_field} (EVT, field {lk.src_id})  Field({list(lk.remap)[0]}) "
                     f"-> Field({lk.dst_id})  [{lk.dst_campaign}/{lk.dst_field}]")
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
    L.append("# 3. Emit + deploy the hub field, then point New Game at it:")
    L.append(f"py -m ff9mapkit assemble-journey {jref} --out {hub_toml}")
    if plan.hub_field_id is not None:
        L.append(f"py tools/deploy_field.py {hub_toml} --id {plan.hub_field_id}   "
                 f"# --mod-folder <the highest stacked folder>")
        L.append(f"py tools/retarget_newgame_warp.py {plan.hub_field_id}   # New Game -> the hub")
    L.append("")
    if plan.bare_entries:
        L.append("# Bare single-field journeys (already deployed elsewhere -- the hub just warps to them):")
        for jid, name, eid in plan.bare_entries:
            L.append(f"#    {name!r} [{jid}] -> field {eid}")
    L.append("# Then RELAUNCH once (new ids register on a fresh launch) and PLAYTEST.")
    return "\n".join(L) + "\n"


def apply_link_rewrites(plan: JourneyDeployPlan, game_root, *, dry_run=False, backup_dir=None) -> list:
    """Apply each retargetable :class:`LinkRewrite` to the boundary member's DEPLOYED ``.eb`` (every language
    copy under ``<game>/<src_mod_folder>``) via ``content.verbatim.remap_fields`` -- the one journey-unique
    in-game step. Returns a list of ``{eb, langs, remap, backups}`` results. ``dry_run`` reports without
    writing. Backs up each patched file to ``backup_dir`` first (reversibility -- Hard Constraint §2)."""
    from .content.verbatim import remap_fields
    game_root = Path(game_root)
    results = []
    for lk in plan.links:
        if not lk.retargetable:
            continue
        mod = game_root / lk.src_mod_folder
        ebs = sorted(mod.rglob(f"{lk.eb_name}.eb.bytes")) if mod.is_dir() else []
        touched, backups = [], []
        for p in ebs:
            data = p.read_bytes()
            out = remap_fields(data, lk.remap)
            if out == data:                       # the Field(to_real) wasn't present in this copy
                continue
            if not dry_run:
                if backup_dir:
                    Path(backup_dir).mkdir(parents=True, exist_ok=True)
                    # path-relative slug so per-lang copies (same filename, different dir) don't collide
                    rel = p.relative_to(mod).as_posix().replace("/", "_")
                    bk = Path(backup_dir) / f"{lk.src_mod_folder}_{rel}.preLINK"
                    bk.write_bytes(data)
                    backups.append((str(p), str(bk)))
                p.write_bytes(out)
            touched.append(str(p))
        results.append({"eb": lk.eb_name, "remap": dict(lk.remap), "langs": len(touched),
                        "files": touched, "backups": backups,
                        "found": bool(touched)})
    return results
