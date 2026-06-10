"""import-chain (P2): fork a walked region into a campaign -- N retargeted field.tomls + a campaign.toml.

P1 (chain.py) walks the door graph and returns a GraphResult. P2 turns that into an authorable, buildable
campaign: it assigns each forkable member a new id (id_base + i, BFS order), forks each real field, and --
the load-bearing step -- RETARGETS every in-chain gateway so it points at the chain's own new id instead of
the live game's. Out-of-chain / scripted / overworld / menu connections are recorded in campaign.toml as
[[seam]]s (NOT live gateways -- a live door to a real id would warp the player back into the live game and
can crash, e.g. field 100). Build-all/deploy-all/flag-allocation are later phases (P3/P4/P5).

The retarget itself happens at extract._imported_content_toml's single gateway-emit site via the threaded
``id_remap`` kwarg; this module orchestrates the id assignment, per-member fork loop, and manifest render.

Each member lands in its OWN subdir (camera.bgx/walkmesh.bgi have fixed names and would otherwise collide):
    <out>/IC_ENT/IC_ENT.field.toml + camera.bgx + walkmesh.bgi
    <out>/campaign.toml          (references "IC_ENT/IC_ENT.field.toml")
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from . import chain

_MAP_SEG = re.compile(r"^map\d", re.I)     # the 'map<NNN>' segment of an FBG folder


class CampaignError(ValueError):
    """A campaign manifest / build-all problem (caught + printed by the CLI)."""


@dataclass
class Member:
    real_id: int
    new_id: int
    name: str                 # IC_ENT, ...
    mode: str                 # "borrow" | "editable"
    src_area: int
    folder: str               # ID_TO_FBG[real_id]
    toml_rel: str             # "IC_ENT/IC_ENT.field.toml"
    needs_export: bool        # editable member whose art wasn't [Export]'d in-game yet


@dataclass
class CampaignPlan:
    name: str
    mod_folder: str
    id_base: int
    flag_base: int
    flags_per_field: int
    entry_name: str
    entry_entrance: int
    members: "list[Member]" = field(default_factory=list)
    edges: list = field(default_factory=list)   # {frm, to, entrance, story_conditional}
    seams: list = field(default_factory=list)    # {frm, to_real, kind, note, to_member?}

    @property
    def needs_export(self):
        return [m.name for m in self.members if m.needs_export]


def member_name(folder: str, idx: int, taken: set) -> str:
    """Deterministic, collision-safe member name from an FBG folder. ``fbg_n05_iccv_map085_ic_ent_0`` ->
    ``IC_ENT`` (the segments after ``map<NNN>``, trailing variant digit dropped). Collisions get a zone
    prefix then a numeric suffix. Falls back to ``<ZONE>_<idx>`` when the folder has no map segment."""
    parts = folder.split("_")
    mi = next((i for i, p in enumerate(parts) if _MAP_SEG.match(p)), None)
    tail = parts[mi + 1:] if mi is not None else []
    if tail and tail[-1].isdigit():            # drop the trailing variant index (..._0 / ..._4)
        tail = tail[:-1]
    base = "_".join(tail).upper() if tail else f"{chain.zone_label(folder).upper()}_{idx:03d}"
    nm = base
    if nm in taken:
        nm = f"{chain.zone_label(folder).upper()}_{base}"
        k = 2
        while nm in taken:
            nm = f"{base}_{k}"
            k += 1
    taken.add(nm)
    return nm


def assign_ids(result, *, id_base: int):
    """(members_ids, new_id, name_of) for the FORKABLE nodes of a walk, in BFS discovery order.
    members_ids[i] -> id_base + i; name_of[real] is the unique member name."""
    from . import extract
    members_ids = [fid for fid, info in result.nodes.items() if info.get("found")]
    new_id = {real: id_base + i for i, real in enumerate(members_ids)}
    taken: set = set()
    name_of = {real: member_name(extract.ID_TO_FBG[real], i, taken)
               for i, real in enumerate(members_ids)}
    return members_ids, new_id, name_of


def _emit_logic_only_member(folder, member_dir, name, field_id, id_remap, live_seams, game):
    """An editable member whose art was never [Export]'d: still emit camera.bgx + walkmesh.bgi (offline)
    and a logic-only field.toml (retargeted gateways, NO [[layers]]) so the campaign STRUCTURE is complete.
    The human exports the art in-game later, then re-forks with --editable to add the repaintable layers."""
    from . import extract
    meta = extract.extract_field(folder, member_dir, game=game)        # camera.bgx + walkmesh.bgi
    safe_area = extract.safe_custom_area(meta["area"])
    content_blocks, control_dir, summary = extract._content_for_import(
        folder, game, out_dir=member_dir, name=name, id_remap=id_remap, live_seams=live_seams)
    meta["imported_content"] = summary
    cm = meta["camera"]
    x, z = meta["player_start"]
    scroll = "[camera.scroll]\nenabled = true\n" if meta["scrolling"] else ""
    control_line = f"control_direction = {control_dir}\n" if control_dir is not None else ""
    toml = (
        f"# EDITABLE member (logic + camera + walkmesh) of {meta['field']} (source area {meta['area']}).\n"
        f"# !! NEEDS ART: export this field in-game once (Memoria.ini [Export] Field=1), then re-run\n"
        f"#    `ff9mapkit import {folder} --editable` to add the repaintable layer_*.png. The gateways,\n"
        f"#    walkmesh and camera here are correct + retargeted; only the background art is missing.\n"
        f"# Camera: pitch {cm['pitch_deg']} deg, FOV {cm['fov_deg']} deg.\n\n"
        f"[field]\nid = {field_id}\nname = \"{name}\"\narea = {safe_area}\ntext_block = 1073\n\n"
        f"[camera]\nborrow = \"camera.bgx\"\n{control_line}{scroll}\n"
        f"[walkmesh]\nbgi = \"walkmesh.bgi\"\n\n"
        f"[player]\nspawn = [{x}, {z}]\n\n"
        f"{extract._content_section(content_blocks, x, z)}"
    )
    p = Path(member_dir) / f"{name}.field.toml"
    p.write_text(toml, encoding="utf-8", newline="\n")
    meta["field_toml"] = str(p)
    return meta, p


def _dedup(rows, keys):
    seen, out = set(), []
    for r in rows:
        k = tuple(r.get(x) for x in keys)
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out


def _collect_edges_seams(result, members_ids, new_id, name_of):
    """Build the [[edge]] (in-chain walk-in) + [[seam]] (everything else) rows for the manifest."""
    inchain = set(members_ids)
    edges = []
    for real, info in result.nodes.items():
        if not info.get("found") or real not in inchain:
            continue
        # group walk-in edges by zone polygon to detect story-conditional stacked exits
        groups: dict = {}
        for e in info["edges"]:
            if e["kind"] == chain.WALK_IN:
                groups.setdefault(tuple(map(tuple, e.get("zone") or [])), []).append(e)
        for e in info["edges"]:
            if e["kind"] != chain.WALK_IN:
                continue
            to = int(e["to"])
            if to not in inchain:
                continue                                      # out-of-chain -> a seam (below), not an edge
            grp = groups[tuple(map(tuple, e.get("zone") or []))]
            cond = bool(e.get("story_conditional")) and sum(1 for x in grp if int(x["to"]) in inchain) >= 2
            edges.append({"frm": name_of[real], "to": name_of[to],
                          "entrance": int(e.get("entrance", 0)), "story_conditional": cond})

    seams = []
    for s in result.seams:                                   # scripted / teleport warps
        to = int(s["to"])
        seams.append({"frm": name_of.get(s["from"], str(s["from"])), "to_real": to, "kind": "scripted",
                      "note": f"trigger:{s.get('trigger')}", "to_member": name_of.get(to)})
    for real, info in result.nodes.items():                  # overworld exits
        if info.get("overworld_exits"):
            seams.append({"frm": name_of.get(real, str(real)), "to_real": "WORLDMAP", "kind": "overworld",
                          "note": f"{len(info['overworld_exits'])} WorldMap op(s)"})
    for p in result.portals:                                 # out-of-scope walk-in targets
        seams.append({"frm": name_of.get(p["from"], str(p["from"])), "to_real": int(p["to"]),
                      "kind": "portal", "note": f"zone {p.get('to_zone')}; {p.get('reason')}",
                      "to_member": name_of.get(int(p["to"]))})
    for u in result.unforkable:                              # shop/menu/variant targets (no background)
        seams.append({"frm": name_of.get(u["from"], str(u["from"])), "to_real": int(u["to"]),
                      "kind": "menu", "note": "no background (shop/menu/variant)"})
    # dedup: a scripted warp can recur across cutscene variants; a double-door is one edge
    return _dedup(edges, ("frm", "to", "entrance")), _dedup(seams, ("frm", "to_real", "kind"))


def write_campaign(result, out_dir, *, id_base=6000, flag_base=8300, flags_per_field=64,
                   name: str, mod_folder: str, game=None, live_seams=False,
                   entry_entrance=0) -> CampaignPlan:
    """Fork the walk into ``out_dir``: a per-member subdir each + a top-level campaign.toml. Returns the
    CampaignPlan. Members in area>=10 BG-borrow (fully offline); area<10 members are editable and, if their
    art was never exported in-game, degrade to logic-only (camera+walkmesh+retargeted gateways) + needs_export."""
    from . import extract
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    members_ids, new_id, name_of = assign_ids(result, id_base=id_base)
    if not members_ids:
        raise ValueError("no forkable fields in the walk -- nothing to fork (try a different seed/--zones)")

    members = []
    for real in members_ids:
        folder = extract.ID_TO_FBG[real]
        area, _ = extract.parse_fbg_folder(folder)
        mode = "borrow" if area >= extract.MIN_CUSTOM_AREA else "editable"
        mname = name_of[real]
        mdir = out / mname
        mdir.mkdir(parents=True, exist_ok=True)
        needs_export = False
        try:
            if mode == "borrow":
                _meta, p = extract.write_field_project(folder, mdir, name=mname, field_id=new_id[real],
                                                       game=game, id_remap=new_id, live_seams=live_seams)
            else:
                _meta, p = extract.write_editable_project(folder, mdir, name=mname, field_id=new_id[real],
                                                          game=game, id_remap=new_id, live_seams=live_seams)
        except RuntimeError as e:
            if mode == "editable" and "[Export]" in str(e):
                _meta, p = _emit_logic_only_member(folder, mdir, mname, new_id[real], new_id, live_seams, game)
                needs_export = True
            else:
                raise
        members.append(Member(real, new_id[real], mname, mode, area, folder,
                              f"{mname}/{p.name}", needs_export))

    edges, seams = _collect_edges_seams(result, members_ids, new_id, name_of)
    plan = CampaignPlan(name=name, mod_folder=mod_folder, id_base=id_base, flag_base=flag_base,
                        flags_per_field=flags_per_field, entry_name=name_of[members_ids[0]],
                        entry_entrance=entry_entrance, members=members, edges=edges, seams=seams)
    (out / "campaign.toml").write_text(render_campaign_toml(plan), encoding="utf-8", newline="\n")
    return plan


def _q(note: str) -> str:
    """A TOML-safe basic string (drop the only char that would break a quoted value)."""
    return str(note).replace('"', "'")


def render_campaign_toml(plan: CampaignPlan) -> str:
    """The campaign.toml text -- valid TOML (array-of-tables, multi-line): [campaign] header, [[field]]
    members, [[edge]] in-chain graph, [[seam]] non-gateway connections, [initial_flags]. Parseable by
    tomllib (so P3's build-all can load it)."""
    L = ["# Campaign manifest emitted by ff9mapkit import-chain (P2).",
         "# Members are forked real fields with gateways RETARGETED to this chain's own ids.",
         "# [[edge]] = in-chain connectivity (each is a live retargeted [[gateway]] in a member toml).",
         "# [[seam]] = scripted/overworld/menu/portal connections that are NOT live gateways -- author by hand.",
         "",
         "[campaign]",
         f'name            = "{plan.name}"',
         f'mod_folder      = "{plan.mod_folder}"',
         f"id_base         = {plan.id_base}",
         f"flag_base       = {plan.flag_base}",
         f"flags_per_field = {plan.flags_per_field}",
         f'entry_field     = "{plan.entry_name}"',
         f"entry_entrance  = {plan.entry_entrance}",
         "",
         "# Members in BFS discovery order; id = id_base + i."]
    for m in plan.members:
        L.append("[[field]]")
        L.append(f'name = "{m.name}"')
        L.append(f"source = {m.real_id}")
        L.append(f"id = {m.new_id}")
        L.append(f'mode = "{m.mode}"')
        L.append(f'toml = "{m.toml_rel}"')
        if m.needs_export:
            L.append("needs_export = true   # export this field in-game ([Export] Field=1) to add its art")
        L.append("")
    L += ["# In-chain connectivity (each = a retargeted live [[gateway]] in the member toml)."]
    for e in plan.edges:
        L.append("[[edge]]")
        L.append(f'from = "{e["frm"]}"')
        L.append(f'to = "{e["to"]}"')
        L.append(f"entrance = {e['entrance']}")
        if e.get("story_conditional"):
            L.append(f'gated_by = ""   # STORY-COND stacked same-zone exit -- set requires_flag '
                     f'(suggest {plan.flag_base + 7})')
        L.append("")
    if plan.seams:
        L += ["# Seams: NOT live gateways -- scripted teleports / overworld exits / menu / out-of-chain."]
        for s in plan.seams:
            L.append("[[seam]]")
            L.append(f'from = "{s["frm"]}"')
            L.append('to_real = "WORLDMAP"' if s["to_real"] == "WORLDMAP" else f"to_real = {s['to_real']}")
            L.append(f'kind = "{s["kind"]}"')
            if s.get("to_member"):
                L.append(f'to_member = "{s["to_member"]}"')
            L.append(f'note = "{_q(s["note"])}"')
            L.append("")
    L += ["[initial_flags]", "# GLOB flags pre-set at campaign entry (empty by default)", ""]
    return "\n".join(L)


# ---- P3: load a campaign.toml + build all members into one mod ---------------------------
def load_campaign(path) -> CampaignPlan:
    """Parse a campaign.toml back into a CampaignPlan (the inverse of render_campaign_toml). Members keep
    their FINAL ids + retargeted gateways (those live in the member field.tomls, not here)."""
    with open(path, "rb") as fh:
        data = tomllib.load(fh)
    if "campaign" not in data:
        raise CampaignError(f"{path}: not a campaign manifest (no [campaign] table)")
    c = data["campaign"]
    members = [Member(real_id=int(f.get("source", 0)), new_id=int(f["id"]), name=f["name"],
                      mode=f.get("mode", "borrow"), src_area=0, folder="",
                      toml_rel=f["toml"], needs_export=bool(f.get("needs_export", False)))
               for f in data.get("field", [])]
    return CampaignPlan(
        name=c.get("name", "CAMPAIGN"), mod_folder=c.get("mod_folder", "FF9CustomMap"),
        id_base=int(c.get("id_base", 4000)), flag_base=int(c.get("flag_base", 8300)),
        flags_per_field=int(c.get("flags_per_field", 64)), entry_name=c.get("entry_field", ""),
        entry_entrance=int(c.get("entry_entrance", 0)), members=members,
        edges=[{"frm": e["from"], "to": e["to"], "entrance": int(e.get("entrance", 0)),
                "story_conditional": "gated_by" in e} for e in data.get("edge", [])],
        # normalize seams to the in-memory shape (from -> frm), exactly as edges above; render_campaign_toml
        # writes `from`, but _collect_edges_seams/lint/campaign_graph all key on `frm`, so a raw passthrough
        # left loaded seams with `from` (dropping them from the resolved graph + nulling lint messages).
        seams=[{"frm": s.get("frm", s.get("from")), "to_real": s.get("to_real"), "kind": s.get("kind"),
                "note": s.get("note", ""), "to_member": s.get("to_member")}
               for s in data.get("seam", [])])


def validate_ids(plan: CampaignPlan):
    """The one campaign-level check P3 owns: ids non-empty, distinct, and in the custom band [4000, 32767]
    (>=4000 per CLAUDE.md; <=32767 because the live fldMapNo is Int16 -> a higher id is unreachable).
    Per-field schema/placement validation runs later inside build_field/validate."""
    if not plan.members:
        raise CampaignError("campaign has no [[field]] members to build")
    ids = [m.new_id for m in plan.members]
    dups = sorted({i for i in ids if ids.count(i) > 1})
    if dups:
        raise CampaignError(f"duplicate member ids {dups} -- EventDB/SceneData are global dicts and collide at launch")
    bad = [i for i in ids if not (4000 <= i <= 32767)]
    if bad:
        raise CampaignError(f"member ids out of range {sorted(set(bad))}: must be 4000-32767 (fldMapNo is Int16)")


def build_campaign(campaign_path, out=None, *, author="", description="", allow_artless=False) -> dict:
    """Compile every member of a campaign.toml into ONE staged Memoria mod (DictionaryPatch + BattlePatch +
    ModDescription + per-field assets), reusing build.build_mod. Returns build_mod's dict + ``plan``/``out``.
    Does NOT deploy (P4). ``out`` defaults to ``<campaign-dir>/dist``."""
    from .build import FieldProject, build_mod
    campaign_path = Path(campaign_path)
    manifest_dir = campaign_path.parent
    plan = load_campaign(campaign_path)
    lint_errors, lint_warnings = lint_campaign(plan, manifest_dir)
    if lint_errors:
        raise CampaignError("campaign lint failed:\n  - " + "\n  - ".join(lint_errors))
    out = Path(out) if out else (manifest_dir / "dist")

    projects = []
    for m in plan.members:
        toml_path = (manifest_dir / m.toml_rel).resolve()      # member subdir -> sidecars resolve via base_dir
        if not toml_path.is_file():
            raise CampaignError(f"member {m.name}: field.toml not found at {toml_path}")
        if m.needs_export and not allow_artless:
            raise CampaignError(
                f"member {m.name} needs in-game art before build: export it once (Memoria.ini [Export] "
                f"Field=1) + re-fork --editable, or pass --allow-artless to build it with no background.")
        proj = FieldProject.load(toml_path)
        # Do NOT override text_block to a per-member id. The FieldScene textid (6th DictionaryPatch token)
        # MUST already be a key in FF9DBAll.MesDB, or DataPatchers SKIPS the whole scene registration
        # (DataPatchers.cs:392-395 `if (!MesDB.ContainsKey(mesID)) continue;` -- verified in-game: textid
        # 30100 -> "invalid message file ID 30100" -> the field never registers, absent from F6). Empty
        # members ship no .mes, so they keep the kit default 1073 (a real base block in MesDB). Distinct
        # textids only become needed -- AND valid -- once a member SHIPS its own .mes for dialogue; doing
        # that safely (a custom .mes that registers its id in MesDB) is a follow-up, not done here.
        projects.append(proj)

    info = build_mod(projects, out, mod_name=plan.mod_folder, author=author, description=description)
    info["plan"] = plan
    info["out"] = str(Path(out).resolve())
    info["warnings"] = list(lint_warnings) + list(info.get("warnings", []))
    return info


# ---- P5: campaign lint (structural + cross-field flags) ---------------------------------
_CONSUME_KEYS = ("requires_flag", "requires_flag_clear")    # explicit flag READS (gates)
_PRODUCE_KEYS = ("flag", "set_flag")                        # explicit flag WRITES


def _collect_flags(obj, produced: set, consumed: set):
    """Walk a member field.toml dict, collecting EXPLICIT GLOB flag indices (ints) under the gate/set
    keys. Auto-allocated 'once' flags are NOT in the toml (computed at build) -> not seen here; per-member
    auto-allocation is a deferred follow-up, so this is the explicit-flag cross-field check."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in _CONSUME_KEYS and isinstance(v, int):
                consumed.add(v)
            elif k in _PRODUCE_KEYS and isinstance(v, int):
                produced.add(v)
            else:
                _collect_flags(v, produced, consumed)
    elif isinstance(obj, list):
        for it in obj:
            _collect_flags(it, produced, consumed)


def _member_flags_from_toml(member_raw: dict):
    produced, consumed = set(), set()
    _collect_flags(member_raw, produced, consumed)
    return produced, consumed


def lint_campaign(plan: CampaignPlan, manifest_dir) -> tuple:
    """Validate a campaign without building. Returns ``(errors, warnings)``; errors abort build-all,
    warnings are advisory. Pure manifest + member-toml read (no game install). For the empty forks
    import-chain produces, the structural checks fire and the flag checks are silent (correct)."""
    from collections import defaultdict
    manifest_dir = Path(manifest_dir)
    errors, warnings = [], []
    names = {m.name for m in plan.members}

    try:                                          # (a) ids non-empty / distinct / in [4000,32767]
        validate_ids(plan)
    except CampaignError as e:
        errors.append(str(e))

    mem_names = [m.name for m in plan.members]    # (a2) names distinct (they key edges/seams + the navigator)
    name_dups = sorted({n for n in mem_names if mem_names.count(n) > 1})
    if name_dups:
        errors.append(f"duplicate member names {name_dups} -- names must be unique "
                      f"(edges/seams + the campaign navigator key on them)")

    for e in plan.edges:                          # (b) edges resolve to members
        if e.get("frm") not in names:
            errors.append(f"edge from {e.get('frm')!r}: not a campaign member")
        if e.get("to") not in names:
            errors.append(f"edge to {e.get('to')!r}: not a campaign member")
    if plan.members and plan.entry_name not in names:
        errors.append(f"entry_field {plan.entry_name!r} is not a campaign member")

    for s in plan.seams:                          # (c) seams: frm member; to_real int|WORLDMAP; to_member valid
        tr = s.get("to_real")
        if tr != "WORLDMAP" and not isinstance(tr, int):
            errors.append(f"seam from {s.get('frm')!r}: to_real must be an int or 'WORLDMAP' (got {tr!r})")
        if plan.members and s.get("frm") not in names:
            warnings.append(f"seam from {s.get('frm')!r}: not a campaign member (stale name?)")
        tm = s.get("to_member")
        if tm and tm not in names:
            warnings.append(f"seam from {s.get('frm')!r}: to_member {tm!r} is not a member (stale name?)")

    member_raw = {}                               # (e) member field.toml exists (+ cache for flags)
    for m in plan.members:
        p = manifest_dir / m.toml_rel
        if not p.is_file():
            errors.append(f"member {m.name}: field.toml not found at {p}")
            continue
        try:
            with open(p, "rb") as fh:
                member_raw[m.name] = tomllib.load(fh)
        except (OSError, tomllib.TOMLDecodeError) as ex:
            errors.append(f"member {m.name}: field.toml unreadable ({ex})")

    for nm in plan.needs_export:                  # (f) artless members
        warnings.append(f"member {nm}: needs in-game art ([Export] Field=1) before a real build")

    stacked = defaultdict(int)                     # (g) ungated stacked story-conditional door
    for e in plan.edges:
        if e.get("story_conditional"):
            stacked[e["frm"]] += 1
    for frm, n in stacked.items():
        if n >= 2:
            warnings.append(f"member {frm}: {n} stacked same-zone exits (story-conditional) -- set "
                            f"requires_flag on each in its field.toml, else the engine resolves only one")

    if not errors:                                 # (h) explicit cross-field flag dependencies
        producers, consumers = {}, []
        for m in plan.members:
            raw = member_raw.get(m.name)
            if raw is None:
                continue
            prod, cons = _member_flags_from_toml(raw)
            for idx in prod:
                producers.setdefault(idx, set()).add(m.name)
            for idx in cons:
                consumers.append((idx, m.name))
        for idx, who in consumers:
            if idx not in producers:
                warnings.append(f"member {who}: requires explicit flag {idx}, but no member sets it -- "
                                f"the gate is permanently locked")
        for idx, who in sorted(producers.items()):
            if len(who) >= 2:
                warnings.append(f"explicit flag {idx} written by multiple members {sorted(who)} -- "
                                f"unintended cross-field coupling (use distinct indices)")

    return errors, warnings


# ---- read-only resolved graph (the campaign-workspace view; pure, no game) ---------------
@dataclass
class GraphNode:
    """A member resolved into its place in the chain: its live in/out doors (to member NAMES, not raw ids)
    + onward seams, plus reachability/leaf flags. A pure derived view -- nothing here that isn't already
    in the CampaignPlan."""
    name: str
    new_id: int
    real_id: int
    mode: str
    needs_export: bool
    is_entry: bool
    reachable: bool                 # reachable from the entry via LIVE edges (seams don't count)
    dead_end: bool                  # no onward connection at all (no edges, no seams)
    out_edges: list                 # [{"to": name, "entrance": int, "gated": bool}]
    in_edges: list                  # [{"frm": name, "entrance": int, "gated": bool}]
    seams: list                     # [{"to_real": int|"WORLDMAP", "kind": str, "note": str, "to_member"}]


@dataclass
class CampaignGraph:
    """The whole campaign resolved for navigation/visualization: members as GraphNodes (in BFS-id order) +
    the campaign-level findings a workspace UI surfaces (unreachable members, dead-ends, dangling edges)."""
    entry: "str | None"             # resolved entry member name (falls back to first member)
    entry_valid: bool               # plan.entry_name actually names a member
    nodes: list                     # list[GraphNode], in member (id) order
    unreachable: list               # member names with no live-door path from the entry
    dead_ends: list                 # member names with no onward connection
    dangling_edges: list            # [[edge]] rows whose from/to is not a member (stale manifest)
    dangling_seams: list            # [[seam]] rows whose `from` is not a member (stale manifest)

    @property
    def by_name(self) -> dict:
        return {n.name: n for n in self.nodes}


def _as_int(v, default=0):
    """``int(v)`` but tolerant -- a malformed/None value (from a hand-edited manifest) degrades to
    ``default`` instead of raising, so campaign_graph keeps its 'never choke on a stale toml' contract."""
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def campaign_graph(plan: CampaignPlan) -> CampaignGraph:
    """Resolve a CampaignPlan into a navigable graph: every member with its in/out live doors (to member
    NAMES), onward seams, and reachability from the entry. PURE over the plan -- the retargeted gateways
    live in the member field.tomls, but the manifest's [[edge]] rows mirror them 1:1, so connectivity is
    fully derivable here (no member-toml read, no game install). Tolerant of a stale / hand-edited
    manifest: an edge to a non-member is recorded in ``dangling_edges`` rather than raising (that's
    lint_campaign's job). Entry resolution mirrors deploy_campaign (explicit member name > first member)."""
    names = [m.name for m in plan.members]
    nameset = set(names)
    out_by = {n: [] for n in names}
    in_by = {n: [] for n in names}
    seams_by = {n: [] for n in names}
    dangling_edges, dangling_seams = [], []
    for e in plan.edges:
        frm, to = e.get("frm"), e.get("to")
        gated = bool(e.get("story_conditional"))
        ent = _as_int(e.get("entrance"))
        if frm not in nameset or to not in nameset:
            dangling_edges.append(dict(e))
            continue
        out_by[frm].append({"to": to, "entrance": ent, "gated": gated})
        in_by[to].append({"frm": frm, "entrance": ent, "gated": gated})
    for s in plan.seams:
        frm = s.get("frm")
        if frm in seams_by:
            seams_by[frm].append({"to_real": s.get("to_real"), "kind": s.get("kind"),
                                  "note": s.get("note", ""), "to_member": s.get("to_member")})
        else:                                            # a seam from a non-member -> surface it, don't drop it
            dangling_seams.append(dict(s))

    entry_valid = plan.entry_name in nameset
    entry = plan.entry_name if entry_valid else (names[0] if names else None)

    reached = set()                                      # BFS from the entry over live edges only
    if entry is not None:
        reached.add(entry)
        stack = [entry]
        while stack:
            for nxt in (oe["to"] for oe in out_by.get(stack.pop(), [])):
                if nxt not in reached:
                    reached.add(nxt)
                    stack.append(nxt)

    nodes = []
    for m in plan.members:
        dead = not out_by[m.name] and not seams_by[m.name]
        nodes.append(GraphNode(
            name=m.name, new_id=m.new_id, real_id=m.real_id, mode=m.mode, needs_export=m.needs_export,
            is_entry=(m.name == entry), reachable=(m.name in reached), dead_end=dead,
            out_edges=out_by[m.name], in_edges=in_by[m.name], seams=seams_by[m.name]))
    return CampaignGraph(
        entry=entry, entry_valid=entry_valid, nodes=nodes,
        unreachable=[m.name for m in plan.members if m.name not in reached],
        dead_ends=[n.name for n in nodes if n.dead_end],
        dangling_edges=dangling_edges, dangling_seams=dangling_seams)


def render_graph(plan: CampaignPlan) -> str:
    """A human-readable view of a LOADED campaign's connectivity -- the post-fork twin of chain.render
    (which only works on a fresh GraphResult). Each member, its live doors resolved to member names, onward
    seams, and dead-end / unreachable / needs-export flags. Backs the `lint-campaign --graph` CLI + the
    campaign workspace's text graph panel."""
    g = campaign_graph(plan)
    ids = [m.new_id for m in plan.members]
    rng = f"{min(ids)}..{max(ids)}" if ids else "-"
    note = "" if g.entry_valid or not plan.members else "  (entry_field not a member -- using first)"
    out = [f"campaign {plan.name}  ({len(plan.members)} members, ids {rng})  "
           f"entry: {g.entry or '(none)'} (entrance {plan.entry_entrance}){note}", ""]
    for n in g.nodes:
        tags = []
        if n.is_entry:
            tags.append("ENTRY")
        if n.mode != "borrow":
            tags.append(n.mode)
        if n.needs_export:
            tags.append("needs-export")
        if not n.reachable:
            tags.append("UNREACHABLE")
        if n.dead_end:
            tags.append("dead-end")
        tagstr = ("  [" + ", ".join(tags) + "]") if tags else ""
        out.append(f"{n.name:<16} id={n.new_id} (was {n.real_id}){tagstr}")
        for oe in n.out_edges:
            out.append(f"    -> {oe['to']} (entrance {oe['entrance']})" + (" [gated]" if oe["gated"] else ""))
        for s in n.seams:
            tgt = s["to_member"] or ("WORLDMAP" if s["to_real"] == "WORLDMAP" else s["to_real"])
            out.append(f"    ~> seam[{s['kind']}] -> {tgt}" + (f"  ({s['note']})" if s.get("note") else ""))
        if not n.out_edges and not n.seams:
            out.append("    (no onward connections)")
        out.append("")
    if g.unreachable:
        out.append("UNREACHABLE FROM ENTRY: " + ", ".join(g.unreachable))
    if g.dangling_edges:
        out.append("DANGLING EDGES (target not a member -- stale manifest?): "
                   + ", ".join(f"{e.get('frm')}->{e.get('to')}" for e in g.dangling_edges))
    if g.dangling_seams:
        out.append("DANGLING SEAMS (from not a member -- stale manifest?): "
                   + ", ".join(f"{s.get('frm')}->{s.get('to_real')}" for s in g.dangling_seams))
    return "\n".join(out).rstrip() + "\n"
