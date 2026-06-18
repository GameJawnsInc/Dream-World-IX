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
# Safe GLOB story-flag allocation band -- single source of truth in ``flags`` (grounded in
# research/STORY_FLAGS.md §4, a 676-field census): real FF9 uses bit-flags up to 8511 (the treasure-chest
# bitfield 8376-8511); the choice scratch is at bit 16320+; custom flags live in [8512, 16320). The old
# flag_base=8300 + 64/field collided with the chest block from member index 1 onward.
from .flags import (CHEST_FLAG_HI, CHEST_FLAG_LO, CHOICE_SCRATCH_FLOOR, FIRST_SAFE_FLAG,
                    collect_flag_defs, resolve_project_flags)

_MAP_SEG = re.compile(r"^map\d", re.I)     # the 'map<NNN>' segment of an FBG folder


class CampaignError(ValueError):
    """A campaign manifest / build-all problem (caught + printed by the CLI)."""


@dataclass
class Member:
    real_id: int
    new_id: int
    name: str                 # IC_ENT, ...
    mode: str                 # "borrow" (area>=10) | "native" (area<10 fork) | "editable" (blank room)
    src_area: int
    folder: str               # ID_TO_FBG[real_id]
    toml_rel: str             # "IC_ENT/IC_ENT.field.toml"
    needs_export: bool        # member with no usable background art -> a logic-only stub


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
    flags: list = field(default_factory=list)    # [[flag]] shared named flags: {name, index} (cross-field)
    verbatim: bool = False                       # forked with --verbatim: every member ships its donor's WHOLE
    #                                              .eb, so a story-conditional stacked door is carried + resolved
    #                                              by the engine at runtime (NOT re-authored from [[edge]]s).

    @property
    def needs_export(self):
        return [m.name for m in self.members if m.needs_export]


def member_name(folder: str, idx: int, taken: set, prefix: str = "") -> str:
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
    # A campaign-unique PREFIX makes the deployed FBG_N<area>_<NAME> + EVT_<NAME> globally unique, so two
    # campaigns/worktrees that fork the SAME source field don't collide on the by-NAME, highest-folder-wins
    # scene/.eb file resolution (a stacked-FolderNames shadow that serves the WRONG fork -> torn load).
    pfx = prefix.strip().upper().rstrip("_")
    return f"{pfx}_{nm}" if pfx else nm


def assign_ids(result, *, id_base: int, name_prefix: str = "", prior=None, reserved_ids=None):
    """(members_ids, new_id, name_of) for the FORKABLE nodes of a walk, in BFS discovery order.

    Without ``prior`` (a fresh fork): ``members_ids[i] -> id_base + i``; ``name_of[real]`` is the unique
    member name (``name_prefix`` namespaces it globally so cross-campaign/cross-worktree forks of the same
    field don't collide on the deployed names).

    With ``prior`` (a ``{source_real_id: (fork_id, member_name)}`` map from an existing campaign.toml --
    STABLE-ID mode, the save-survives-a-re-fork path): a re-discovered donor keeps its EXACT prior fork-id +
    name, and a net-NEW donor is APPENDED at the next id ABOVE every prior id (never reusing a prior id, so a
    stale save can't land on the wrong field; the append-above-max rule also keeps every prior member's
    POSITION when the caller emits members id-sorted -> its position-based flag window is stable too). Names
    stay stable: prior names are reused verbatim and new names are disambiguated against them. ``reserved_ids``
    (the new ids of EVERY prior member, including source-less / hand-appended ones NOT in ``prior``) are
    protected from re-allocation so a net-new donor can never collide with one. ``prior={}`` + no
    ``reserved_ids`` reproduces the original index-based allocation byte-for-byte."""
    from . import extract
    members_ids = [fid for fid, info in result.nodes.items() if info.get("found")]
    prior = prior or {}
    taken: set = {pname for (_pid, pname) in prior.values()}   # a new name can't collide with a reused one
    used: set = {pid for (pid, _pname) in prior.values()} | set(reserved_ids or ())  # every prior id is off-limits
    cursor = max([id_base - 1, *used]) + 1                      # net-new members append above EVERY prior id
    new_id: dict = {}
    name_of: dict = {}
    for i, real in enumerate(members_ids):
        if real in prior:                                      # re-discovered: freeze its id + name
            new_id[real], name_of[real] = prior[real]
        else:                                                  # net-new donor: a fresh non-colliding id
            while cursor in used:
                cursor += 1
            new_id[real] = cursor
            used.add(cursor)
            cursor += 1
            name_of[real] = member_name(extract.ID_TO_FBG[real], i, taken, name_prefix)
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


def write_campaign(result, out_dir, *, id_base=6000, flag_base=FIRST_SAFE_FLAG, flags_per_field=64,
                   name: str, mod_folder: str, game=None, live_seams=False,
                   entry_entrance=0, verbatim=False, swap_player=None,
                   neutralize_gestures=False, name_prefix="", prior_plan=None) -> CampaignPlan:
    """Fork the walk into ``out_dir``: a per-member subdir each + a top-level campaign.toml. Returns the
    CampaignPlan. Members in area>=10 BG-borrow; area<10 members fork as a NATIVE scene (own atlas+.bgs, no
    .bgx -- seamless, no in-game export needed). Both are fully offline; a field with no usable background
    atlas degrades to a logic-only stub (camera+walkmesh+retargeted gateways) flagged needs_export.

    ``verbatim`` (the MOST faithful chain -- docs/FORK_FIDELITY.md): fork EVERY member native + VERBATIM --
    each ships its donor's WHOLE event script (entry-0 + objects + gateways, run as-is) with the in-chain
    ``Field()`` exits retargeted to this chain's own member ids, plus the donor's whole ``.mes`` at the
    donor's OWN registered textid (``EVENT_ID_TO_MES`` -- a valid MesDB key, so the FieldScene registers;
    same-zone members share it harmlessly, ship identical text). The chain then plays its real logic +
    speaks its real lines, doors wired to each other instead of back into the live game."""
    from . import extract
    from ._fieldtext import EVENT_ID_TO_MES
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    # STABLE-ID mode: when re-forking on top of an existing campaign (``prior_plan``), freeze every
    # re-discovered donor's prior fork-id + name and APPEND net-new donors above the highest prior id, so an
    # in-fork SAVE survives the re-fork (it stores the field id + position-based story-flag window).
    prior = {m.real_id: (m.new_id, m.name) for m in prior_plan.members if m.real_id} if prior_plan else None
    # EVERY prior member's id is reserved (incl. source-less / hand-appended ones absent from `prior`), so a
    # net-new donor can't collide with one even though only real donors can be re-discovered by name/id.
    reserved = {m.new_id for m in prior_plan.members} if prior_plan else None
    members_ids, new_id, name_of = assign_ids(result, id_base=id_base, name_prefix=name_prefix,
                                              prior=prior, reserved_ids=reserved)
    if not members_ids:
        raise ValueError("no forkable fields in the walk -- nothing to fork (try a different seed/--zones)")
    # Carry forward any prior member the new walk did NOT re-discover (a hand-appended out-of-band fork like a
    # missed cross-zone cutscene field, OR a source-less blank-room/logic member) -- keep its files + id so
    # (a) it isn't orphaned/dropped and its cross-link doesn't re-leak, and (b) other members' retargets to it
    # still resolve. Carry only a member whose field.toml is still on disk; flag any whose files vanished
    # (can't carry -> later members' positions/flag windows shift).
    carried: list = []
    carried_missing: list = []
    if prior_plan:
        discovered = set(members_ids)
        for m in prior_plan.members:
            if m.real_id and m.real_id in discovered:
                continue                                  # re-discovered -> re-forked below with its frozen id
            if (out / m.toml_rel).exists():
                if m.real_id:
                    new_id[m.real_id] = m.new_id          # so re-forked members' Field(real)->fork resolve
                    name_of[m.real_id] = m.name           # keep new_id/name_of CONSISTENT: a re-forked verbatim
                    #   member's Field(carried) exit feeds the edge-synth `name_of[d]` below -- a carried id in
                    #   new_id but absent from name_of crashes it (KeyError). real_id 0 never a Field() dest.
                carried.append(m)
            else:
                carried_missing.append(m)

    swap_name = None
    if swap_player and verbatim:                             # the swap patches each member's verbatim donor .eb
        from . import playerswap
        swap_name, _ = playerswap.resolve_char(swap_player)  # fail fast on a bad char before forking the chain
    members = []
    member_exits: dict = {}                                  # real -> its donor .eb Field() dests (verbatim)
    degraded: list = []                                      # verbatim members that fell back to declarative
    swap_gesture_warn: dict = {}                             # mname -> scripted-gesture count (will glitch on swap)
    swap_skipped: list = []                                  # verbatim members with no swappable player entry
    for real in members_ids:
        folder = extract.ID_TO_FBG[real]
        donor = str(real)                                    # identify the donor by ID, not the FBG folder --
        #     several field ids can SHARE one folder (the same room at a different story beat, e.g. 52/3008), so
        #     a folder-name lookup is ambiguous + DROPS the member; the id resolves its own scene + .eb exactly.
        area, _ = extract.parse_fbg_folder(folder)
        # verbatim ships its own native scene + the donor's whole .eb, so it forks NATIVE for any area
        mode = "native" if verbatim else ("borrow" if area >= extract.MIN_CUSTOM_AREA else "native")
        mname = name_of[real]
        mdir = out / mname
        mdir.mkdir(parents=True, exist_ok=True)
        needs_export = False
        try:
            if verbatim:
                # the donor's OWN registered textid (a valid MesDB key); shipping its .mes there is an
                # identity override, and same-zone members share it (identical text -> harmless).
                tb = EVENT_ID_TO_MES.get(real, 1073)
                _meta, p = extract.write_native_project(donor, mdir, name=mname, field_id=new_id[real],
                                                        text_block=tb, game=game, id_remap=new_id,
                                                        live_seams=live_seams, verbatim=True)
                member_exits[real] = _meta.get("imported_content", {}).get("field_exits", [])
                if swap_name:                            # play as one char across the chain (per-member swap)
                    try:
                        n = extract.apply_player_swap(p, swap_name, neutralize=neutralize_gestures)
                        if n:
                            swap_gesture_warn[mname] = n
                    except playerswap.NoSwappablePlayer:
                        swap_skipped.append(mname)       # no swappable player entry (e.g. a cutscene member)
                        # a real overflow/corruption ValueError is NOT caught here -> it propagates loudly
            elif mode == "borrow":
                _meta, p = extract.write_field_project(donor, mdir, name=mname, field_id=new_id[real],
                                                       game=game, id_remap=new_id, live_seams=live_seams)
            else:   # area<10: NATIVE fork (own atlas+.bgs, NO .bgx) -- seamless + fully offline (no [Export])
                _meta, p = extract.write_native_project(donor, mdir, name=mname, field_id=new_id[real],
                                                        game=game, id_remap=new_id, live_seams=live_seams)
        except RuntimeError:                                # a field with no usable background atlas (rare)
            if mode == "borrow":
                raise
            # verbatim degrades to a logic-only stub too (loses the verbatim .eb for this one member)
            _meta, p = _emit_logic_only_member(donor, mdir, mname, new_id[real], new_id, live_seams, game)
            needs_export = True
            if verbatim:
                degraded.append(mname)                       # surfaced loudly in the CLI summary (NOT verbatim)
        members.append(Member(real, new_id[real], mname, mode, area, folder,
                              f"{mname}/{p.name}", needs_export))

    edges, seams = _collect_edges_seams(result, members_ids, new_id, name_of)
    # In a verbatim chain the LIVE doors are the donor .eb's retargeted Field() exits -- which include
    # scripted/self warps that aren't walk-in [[edge]]s. Surface every in-chain retarget as an edge so the
    # graph/reachability reflect what was baked into the shipped .eb (else a member reachable only via a
    # retargeted scripted warp reads as UNREACHABLE). Skip self-loops; dedup against the walk-in edges.
    if verbatim:
        have = {(e["frm"], e["to"]) for e in edges}
        for real, exits in member_exits.items():
            for d in exits:
                if d in new_id and d != real and (name_of[real], name_of[d]) not in have:
                    edges.append({"frm": name_of[real], "to": name_of[d], "entrance": 0,
                                  "story_conditional": False})
                    have.add((name_of[real], name_of[d]))
    members.extend(carried)               # keep prior forks the new walk didn't re-discover (no orphan/re-leak)
    members.sort(key=lambda m: m.new_id)  # id-sorted == position-stable: a re-discovered member keeps its index
    #                                       -> its position-based story-flag window (flag_base + i*K) survives too.
    #                                       Fresh fork: ids are id_base+i in walk order, so this is already sorted.
    # Entry: the first-discovered (seed) member, BUT on a stable re-fork keep the PRIOR entry if that member
    # still exists -- a changed discovery order must not silently repoint New Game / the journey entry.
    entry_name = name_of[members_ids[0]]
    if prior_plan and prior_plan.entry_name and any(m.name == prior_plan.entry_name for m in members):
        entry_name = prior_plan.entry_name
    plan = CampaignPlan(name=name, mod_folder=mod_folder, id_base=id_base, flag_base=flag_base,
                        flags_per_field=flags_per_field, entry_name=entry_name,
                        entry_entrance=entry_entrance, members=members, edges=edges, seams=seams)
    plan.stable_ids = bool(prior_plan)    # transient: re-fork reused the prior donor->id+name map
    plan.reused_ids = sorted(r for r in members_ids if prior and r in prior)   # re-discovered, frozen id
    plan.appended_ids = sorted(r for r in members_ids if not (prior and r in prior))  # net-new this fork
    plan.carried = [m.name for m in carried]              # prior forks kept verbatim (not re-discovered)
    plan.carried_missing = [(m.name, m.new_id) for m in carried_missing]  # prior forks whose files vanished
    plan.verbatim = bool(verbatim)        # PERSISTED: gates the declarative-only stacked-door lint (the donor
    #                                       .eb resolves story-conditional doors itself -- nothing to re-author)
    plan.verbatim_degraded = degraded     # transient build-time signal (NOT persisted): verbatim members
    plan.swap_player = swap_name          # transient: --swap-player char applied to every member, + the
    plan.swap_gesture_warn = swap_gesture_warn   # members whose scripted gestures will glitch on the new rig,
    plan.swap_skipped = swap_skipped      # and members with no swappable player entry (left as the donor's)
    plan.neutralized = bool(neutralize_gestures and swap_name)   # those gestures were rewritten to idle (won't glitch)
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
         f"entry_entrance  = {plan.entry_entrance}"]
    if plan.verbatim:                             # verbatim members ship the donor .eb whole -> story-conditional
        L.append("verbatim        = true   # every member ships its donor's whole .eb (real logic + real doors)")
    L += ["",
          "# Members id-sorted. Fresh fork: id = id_base + BFS-index. Stable re-fork (--out had a prior",
          "# campaign.toml): a re-discovered donor keeps its prior id+name; net-new donors append above the max."]
    for m in plan.members:
        L.append("[[field]]")
        L.append(f'name = "{m.name}"')
        L.append(f"source = {m.real_id}")
        L.append(f"id = {m.new_id}")
        L.append(f'mode = "{m.mode}"')
        L.append(f'toml = "{m.toml_rel}"')
        if m.needs_export:
            L.append("needs_export = true   # logic-only stub: this field had no usable background atlas")
        L.append("")
    L += ["# In-chain connectivity (each = a retargeted live [[gateway]] in the member toml)."]
    for e in plan.edges:
        L.append("[[edge]]")
        L.append(f'from = "{e["frm"]}"')
        L.append(f'to = "{e["to"]}"')
        L.append(f"entrance = {e['entrance']}")
        if e.get("story_conditional"):
            L.append("story_conditional = true")   # explicit marker -> survives load (NOT inferred from gated_by,
            #                                         which verbatim omits) so a DEGRADED-member lint still fires
            if plan.verbatim:
                # the donor .eb owns this conditional door (if(flag){A}else{B}) -- it's carried verbatim and the
                # engine resolves it at runtime, so there is NOTHING to gate here (informational only).
                L.append("# the donor .eb resolves this story-conditional door at runtime (informational)")
            else:
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
    if plan.flags:
        L += ["# Shared NAMED flags -- members gate by NAME (requires_flag = \"<name>\"). Place ABOVE the",
              "# per-member auto-flag blocks; indices must be in [8512, 16320), clear of real-FF9 usage."]
        for fdef in plan.flags:
            L += ["[[flag]]", f'name = "{fdef.get("name", "")}"', f"index = {int(fdef.get('index', 0))}", ""]
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
        id_base=int(c.get("id_base", 4000)), flag_base=int(c.get("flag_base", FIRST_SAFE_FLAG)),
        flags_per_field=int(c.get("flags_per_field", 64)), entry_name=c.get("entry_field", ""),
        entry_entrance=int(c.get("entry_entrance", 0)), members=members,
        verbatim=bool(c.get("verbatim", False)),
        flags=list(data.get("flag", [])),
        edges=[{"frm": e["from"], "to": e["to"], "entrance": int(e.get("entrance", 0)),
                # the explicit marker (new) OR a legacy gated_by placeholder (back-compat with older forks)
                "story_conditional": bool(e.get("story_conditional")) or ("gated_by" in e)}
               for e in data.get("edge", [])],
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


def apply_seed_blocks(raw: dict, blocks: dict) -> None:
    """Merge story-flags capstone blocks (``startup`` / ``party`` / ``start_inventory`` / ``equipment``) into a
    member's ``FieldProject.raw`` IN PLACE -- additive (scenario replaces, flags + party-adds union, the bag /
    equipment lists replace). The journey assembler's seed lever (:func:`ff9mapkit.journey.seed_to_field_blocks`
    produces ``blocks``): it seeds a journey's ENTRY member without rewriting its forked field.toml on disk, so
    the fork stays clean and a re-deploy is idempotent. Empty ``blocks`` -> no mutation (byte-identical build)."""
    if not blocks:
        return
    if "startup" in blocks:
        su = raw.setdefault("startup", {})
        if "scenario" in blocks["startup"]:
            su["scenario"] = blocks["startup"]["scenario"]
        if blocks["startup"].get("flags"):
            su["flags"] = list(su.get("flags", [])) + list(blocks["startup"]["flags"])
    if "party" in blocks:
        add = list(raw.setdefault("party", {}).get("add", []))
        for m in blocks["party"].get("add", []):
            if m not in add:
                add.append(m)
        raw["party"]["add"] = add
    if "start_inventory" in blocks:
        raw["start_inventory"] = blocks["start_inventory"]
    if "equipment" in blocks:
        raw["equipment"] = blocks["equipment"]


def build_campaign(campaign_path, out=None, *, author="", description="", allow_artless=False,
                   flag_base=None, seed_blocks=None) -> dict:
    """Compile every member of a campaign.toml into ONE staged Memoria mod (DictionaryPatch + BattlePatch +
    ModDescription + per-field assets), reusing build.build_mod. Returns build_mod's dict + ``plan``/``out``.
    Does NOT deploy (P4). ``out`` defaults to ``<campaign-dir>/dist``.

    ``flag_base`` (the JOURNEY assembler's lever): override the campaign's own ``flag_base`` so the journey
    can hand each of its campaigns a NON-OVERLAPPING ``gEventGlobal`` flag window (two campaigns in one
    journey run together -- they must not clobber each other's bits; :mod:`ff9mapkit.journey`). Applied
    before lint, so the per-member auto-flag blocks + the safe-band checks both use the override.

    ``seed_blocks`` (the journey ``[journey.seed]`` capstone): a dict of ``startup``/``party``/
    ``start_inventory``/``equipment`` blocks merged into the ENTRY member's project before build
    (:func:`apply_seed_blocks`) -- so the journey boots at its seeded beat/party (the ``.eb`` channel) without
    rewriting the forked entry field.toml. ``None`` -> no seeding."""
    from .build import FieldProject, build_mod
    campaign_path = Path(campaign_path)
    manifest_dir = campaign_path.parent
    plan = load_campaign(campaign_path)
    if flag_base is not None:                              # journey-assigned disjoint flag window
        plan.flag_base = int(flag_base)
    lint_errors, lint_warnings = lint_campaign(plan, manifest_dir)
    if lint_errors:
        raise CampaignError("campaign lint failed:\n  - " + "\n  - ".join(lint_errors))
    out = Path(out) if out else (manifest_dir / "dist")

    campaign_names = collect_flag_defs({"flag": plan.flags})   # shared [[flag]] names (lint already validated)
    projects = []
    for i, m in enumerate(plan.members):
        toml_path = (manifest_dir / m.toml_rel).resolve()      # member subdir -> sidecars resolve via base_dir
        if not toml_path.is_file():
            raise CampaignError(f"member {m.name}: field.toml not found at {toml_path}")
        if m.needs_export and not allow_artless:
            raise CampaignError(
                f"member {m.name} needs in-game art before build: export it once (Memoria.ini [Export] "
                f"Field=1) + re-fork --editable, or pass --allow-artless to build it with no background.")
        proj = FieldProject.load(toml_path, flag_names=campaign_names)   # members gate by shared flag NAME
        # Per-member once-flag base so member i's auto chest/event/cutscene/choice flags can't alias a
        # sibling's (the per-field-counter-resets-per-build bug). Block = [flag_base + i*K, +K), packed
        # by build._FlagAlloc. lint_campaign asserts every block is in the provably-safe band.
        proj.flag_base = plan.flag_base + i * plan.flags_per_field
        proj.flags_per_field = plan.flags_per_field     # the overflow guard's per-member block width
        # Do NOT override text_block to a per-member id. The FieldScene textid (6th DictionaryPatch token)
        # MUST already be a key in FF9DBAll.MesDB, or DataPatchers SKIPS the whole scene registration
        # (DataPatchers.cs:392-395 `if (!MesDB.ContainsKey(mesID)) continue;` -- verified in-game: textid
        # 30100 -> "invalid message file ID 30100" -> the field never registers, absent from F6). Empty
        # members ship no .mes, so they keep the kit default 1073 (a real base block in MesDB). Distinct
        # textids only become needed -- AND valid -- once a member SHIPS its own .mes for dialogue; doing
        # that safely (a custom .mes that registers its id in MesDB) is a follow-up, not done here.
        projects.append(proj)

    # each member's per-member flag_base was set on its FieldProject above; build_script's _FlagAlloc packs
    # that member's auto chest/event/cutscene/choice flags into its own disjoint block (no cross-field alias).
    # the entry member's project (by member index) -> precise non-entry lint for the mod-global new-game blocks
    entry_project = next((projects[i] for i, m in enumerate(plan.members) if m.name == plan.entry_name), None)
    if seed_blocks and entry_project is not None:        # the journey [journey.seed] capstone, on the entry only
        apply_seed_blocks(entry_project.raw, seed_blocks)
    info = build_mod(projects, out, mod_name=plan.mod_folder, author=author, description=description,
                     entry_project=entry_project)
    # [ff9mapkit] fork-fidelity: ForkDonorPatch.txt maps each custom-id fork -> its donor real field id, so
    # the engine's behaviors hardcoded on a real fldMapNo (off-mesh exemptions, cutscene party-shape guards,
    # scroll player-binds -- docs/FORK_IDGATE_MAP.md) still fire for the fork. Read by the patched DataPatchers
    # (memoria-patches/s24-fork-donor-remap); a no-op on a stock engine that doesn't read the file.
    donor_lines = [f"{m.new_id} {m.real_id}" for m in plan.members
                   if getattr(m, "real_id", None) and m.new_id != m.real_id]
    if donor_lines:
        (Path(out) / "ForkDonorPatch.txt").write_text(
            "# ff9mapkit fork-fidelity: <forkId> <donorRealId>\n" + "\n".join(donor_lines) + "\n",
            encoding="utf-8", newline="\n")
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

    K = plan.flags_per_field                      # (a3) per-member flag blocks: in the provably-safe band,
    for i, m in enumerate(plan.members):          #      clear of real-FF9's chest bitfield + the scratch
        lo, hi = plan.flag_base + i * K, plan.flag_base + i * K + K - 1
        if lo < FIRST_SAFE_FLAG:
            errors.append(f"member {m.name}: flag block {lo}-{hi} dips below the safe floor "
                          f"{FIRST_SAFE_FLAG} (overlaps real-FF9 flags) -- raise [campaign] flag_base.")
        if lo <= CHEST_FLAG_HI and hi >= CHEST_FLAG_LO:
            errors.append(f"member {m.name}: flag block {lo}-{hi} intersects real-FF9's treasure-chest "
                          f"band {CHEST_FLAG_LO}-{CHEST_FLAG_HI} -> SAVE CORRUPTION -- set [campaign] "
                          f"flag_base = {FIRST_SAFE_FLAG}.")
        if hi >= CHOICE_SCRATCH_FLOOR:
            cap = (CHOICE_SCRATCH_FLOOR - plan.flag_base) // K
            errors.append(f"member {m.name}: flag block {lo}-{hi} reaches the choice-scratch floor "
                          f"{CHOICE_SCRATCH_FLOOR} -- too many members for the band (max {cap} at this base/K).")

    try:                                          # (a4) shared [[flag]] names: valid + clear of member blocks
        shared = collect_flag_defs({"flag": plan.flags})
    except ValueError as ex:
        shared, _ = {}, errors.append(f"campaign [[flag]]: {ex}")
    block_hi = plan.flag_base + len(plan.members) * K - 1   # member auto-flag blocks span [flag_base, block_hi]
    for nm, idx in sorted(shared.items()):
        if plan.flag_base <= idx <= block_hi:
            errors.append(f"shared flag {nm!r} (index {idx}) falls inside the per-member auto-flag blocks "
                          f"[{plan.flag_base}, {block_hi}] -- put shared flags ABOVE them (>= {block_hi + 1}).")

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

    member_raw = {}                               # (e) member field.toml exists, within the campaign folder
    for m in plan.members:
        p = manifest_dir / m.toml_rel
        if not _within(manifest_dir, p):          # a crafted toml_rel ('../..') must not read outside
            errors.append(f"member {m.name}: field.toml path escapes the campaign folder ({m.toml_rel})")
            continue
        if not p.is_file():
            errors.append(f"member {m.name}: field.toml not found at {p}")
            continue
        try:
            with open(p, "rb") as fh:
                member_raw[m.name] = tomllib.load(fh)
        except (OSError, tomllib.TOMLDecodeError) as ex:
            errors.append(f"member {m.name}: field.toml unreadable ({ex})")

    for m in plan.members:                        # (e2) explicit flags must avoid real-FF9's chest band
        raw = member_raw.get(m.name)
        if raw is None:
            continue
        prod, cons = _member_flags_from_toml(raw)
        for idx in sorted(prod | cons):
            if CHEST_FLAG_LO <= idx <= CHEST_FLAG_HI:
                errors.append(f"member {m.name}: explicit flag {idx} is inside real-FF9's treasure-chest "
                              f"band {CHEST_FLAG_LO}-{CHEST_FLAG_HI} -> SAVE CORRUPTION -- use an index in "
                              f"[{FIRST_SAFE_FLAG}, {CHOICE_SCRATCH_FLOOR}).")
            elif idx >= FIRST_SAFE_FLAG and idx >= CHOICE_SCRATCH_FLOOR:
                warnings.append(f"member {m.name}: explicit flag {idx} is at/above the choice-scratch floor "
                                f"{CHOICE_SCRATCH_FLOOR} (engine-owned) -- pick a lower index.")

    for nm in plan.needs_export:                  # (f) artless members
        warnings.append(f"member {nm}: needs in-game art ([Export] Field=1) before a real build")

    # (g) ungated stacked story-conditional door -- DECLARATIVE gateways only. A VERBATIM member ships the donor
    #     .eb whole, so its if(flag){A}else{B} door is carried + resolved by the engine (nothing authored to
    #     gate -> the warning would be a false positive). BUT a DEGRADED member (needs_export: a logic-only stub)
    #     re-authors its gateways declaratively even in a verbatim chain, so it still needs the gating advice.
    degraded = set(plan.needs_export)
    stacked = defaultdict(int)
    for e in plan.edges:
        frm = e.get("frm")
        if e.get("story_conditional") and (not plan.verbatim or frm in degraded):
            stacked[frm] += 1
    for frm, n in stacked.items():
        if n >= 2:
            warnings.append(f"member {frm}: {n} stacked same-zone exits (story-conditional) -- set "
                            f"requires_flag on each in its field.toml, else the engine resolves only one")

    if not errors:                                 # (h) cross-field flag dependencies (NAME gates included)
        producers, consumers = {}, []
        for m in plan.members:
            raw = member_raw.get(m.name)
            if raw is None:
                continue
            try:                                   # resolve member-own + shared NAME gates -> indices, so a
                resolve_project_flags(raw, extra_names=shared)   # name-based dependency is seen (not skipped)
            except ValueError as ex:               # a gate on a name defined NOWHERE -> the build would fail too
                errors.append(f"member {m.name}: {ex}")
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
    # A VERBATIM fork ships each member's WHOLE donor .eb, so its real connectivity -- story-scripted warps,
    # per-door arrival tables, story-gated transitions -- is intact and runs in-game, but the static walk-in-edge
    # BFS can't see it: a whole-zone fork's screens reached only by cutscene, or other-disc room variants, read
    # as "unreachable" though every forked real field WAS reachable in the real game (FF9 has no unused fields).
    # So don't flag verbatim members as unreachable -- it's a false-positive flood, not stranded content. (A
    # DECLARATIVE campaign's reachability IS meaningful: its gateways are authored from these very edges.)
    if getattr(plan, "verbatim", False):
        reached = set(names)

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


# ---- P6: mutation / creation API (author/edit a campaign WITHOUT import-chain) -----------
# import-chain FORKS a connected real-game region; this is the from-scratch / hand-edit twin -- create an
# empty campaign and add/remove/rename members + edges by hand. Every mutation re-renders campaign.toml
# through render_campaign_toml so the manifest stays the single round-trip-safe source of truth, and ids
# are next-free (never renumbered -- a renumber would have to rewrite every member's retargeted gateways).
def _save_plan(plan: CampaignPlan, manifest_dir) -> Path:
    """(Re)write campaign.toml from the in-memory plan -- the single persistence point for every mutation."""
    p = Path(manifest_dir) / "campaign.toml"
    p.write_text(render_campaign_toml(plan), encoding="utf-8", newline="\n")
    return p


def _next_member_id(plan: CampaignPlan) -> int:
    """Next free member id: max existing + 1 (ids needn't be contiguous; removes leave gaps), or id_base
    for the first member. Never renumbers existing members (that would rewrite their retargeted gateways)."""
    return max((m.new_id for m in plan.members), default=plan.id_base - 1) + 1


def _subdir_of(member: Member) -> str:
    """The member's on-disk subdir (the first path component of toml_rel)."""
    return Path(member.toml_rel).parts[0]


def _within(base, path) -> bool:
    """True if ``path`` resolves to ``base`` itself or somewhere inside it -- the guard that keeps a
    crafted/stale ``toml_rel`` (``../..``) from letting a mutation rename/rmtree/read OUTSIDE the campaign."""
    base, path = Path(base).resolve(), Path(path).resolve()
    return path == base or base in path.parents


def _validate_member_name(name: str) -> str:
    """A member name is a simple token -- it becomes an on-disk subdir + the key edges/seams reference, so
    no path separators / traversal / surrounding whitespace."""
    name = str(name)
    if not name or name != name.strip() or name in (".", "..") or any(c in name for c in "/\\"):
        raise CampaignError(f"invalid member name {name!r} (no path separators / leading-trailing space)")
    return name


def _safe_member_dir(manifest_dir, member: Member) -> Path:
    """A member's subdir, RESOLVED and validated to stay within manifest_dir -- the guard before any
    destructive rename/rmtree (a crafted toml_rel must never reach outside the campaign folder)."""
    sub = Path(manifest_dir) / _subdir_of(member)
    if not _within(manifest_dir, sub):
        raise CampaignError(f"member {member.name!r}: subdir escapes the campaign folder ({member.toml_rel})")
    return sub.resolve()


def _resolve_source_id(source) -> int:
    """A real field reference (an id, or a unique FBG-folder substring) -> its FIELD ID (the donor). For
    add_field's fork path. The ID is what disambiguates a folder SHARED by several fields (the same room at
    different story beats, e.g. 52/3008) -- a folder name can't, so a shared-folder substring is rejected
    (pass the id). Raises if it's not a single known field. (Mirrors import-chain's fork-by-id; the donor must
    resolve its OWN .eb, not the folder-keyed winner.)"""
    from . import extract
    try:
        fid = int(source)
        if fid in extract.ID_TO_FBG:
            return fid
    except (TypeError, ValueError):
        pass
    s = str(source).lower()
    hits = sorted(fid for fid, f in extract.ID_TO_FBG.items() if s in f.lower())
    if len(hits) == 1:
        return hits[0]
    raise CampaignError(f"source {source!r} matched {len(hits)} fields {hits[:8]} -- give a field id "
                        f"(a shared FBG folder maps to several fields) or a unique FBG name")


def new_campaign(name, mod_folder, manifest_dir, *, id_base=4000, flag_base=FIRST_SAFE_FLAG,
                 flags_per_field=64, entry_entrance=0) -> CampaignPlan:
    """Create an EMPTY campaign (no members) and write its campaign.toml -- the from-scratch path that
    import-chain (which forks a real region) doesn't cover. Add members with :func:`add_field`. The default
    flag_base is the census-grounded safe floor (clear of real-FF9 chest flags); see :mod:`flags`."""
    if not (4000 <= id_base <= 32767):
        raise CampaignError(f"id_base {id_base} out of range (must be 4000-32767)")
    plan = CampaignPlan(name=str(name), mod_folder=str(mod_folder), id_base=int(id_base),
                        flag_base=int(flag_base), flags_per_field=int(flags_per_field),
                        entry_name="", entry_entrance=int(entry_entrance))
    Path(manifest_dir).mkdir(parents=True, exist_ok=True)
    _save_plan(plan, manifest_dir)
    return plan


def add_field(plan: CampaignPlan, manifest_dir, *, name, source=None, game=None) -> Member:
    """Add a member to a campaign + re-render campaign.toml. ``source=None`` scaffolds a BLANK room
    (offline, via pack.new_project -- placeholder art, walkable). A ``source`` (a real field id or a unique
    FBG-folder substring) FORKS that real field (needs the game install, like import-chain), retargeting
    any gateway that points at an existing member. The member gets the next free id (no renumber). The
    first member added becomes the entry if none is set yet."""
    from . import extract
    name = _validate_member_name(name)
    manifest_dir = Path(manifest_dir)
    if any(m.name == name for m in plan.members):
        raise CampaignError(f"member name {name!r} is already in this campaign")
    new_id = _next_member_id(plan)
    if new_id > 32767:
        raise CampaignError(f"next member id {new_id} exceeds 32767 (the live fldMapNo is Int16)")
    if source is None:                                   # blank/template member -- fully offline
        from . import pack
        pack.new_project(name, manifest_dir, field_id=new_id, area=11)
        member = Member(0, new_id, name, "editable", 11, "", f"{name}/{name.lower()}.field.toml", False)
    else:                                                # fork a real field -- needs the game
        real_id = _resolve_source_id(source)             # the donor ID (disambiguates a shared FBG folder)
        folder = extract.ID_TO_FBG[real_id]
        donor = str(real_id)                             # fork by ID, not the (possibly shared) folder name --
        #     so the writers ship THIS field's .eb/scene, not the folder-keyed winner (mirrors write_campaign).
        area, _ = extract.parse_fbg_folder(folder)
        mode = "borrow" if area >= extract.MIN_CUSTOM_AREA else "native"
        mdir = manifest_dir / name
        mdir.mkdir(parents=True, exist_ok=True)
        remap = {m.real_id: m.new_id for m in plan.members if m.real_id}
        remap[real_id] = new_id                          # so a self/back-reference retargets to this member
        needs_export = False
        try:                                             # area<10 forks NATIVE (own atlas+.bgs, no .bgx)
            fork = extract.write_field_project if mode == "borrow" else extract.write_native_project
            _meta, p = fork(donor, mdir, name=name, field_id=new_id, game=game, id_remap=remap)
        except RuntimeError:                             # a field with no usable background atlas (rare)
            if mode == "borrow":
                raise
            _meta, p = _emit_logic_only_member(donor, mdir, name, new_id, remap, False, game)
            needs_export = True
        member = Member(real_id, new_id, name, mode, area, folder, f"{name}/{p.name}", needs_export)
    plan.members.append(member)
    if not plan.entry_name:
        plan.entry_name = name
    _save_plan(plan, manifest_dir)
    return member


def remove_field(plan: CampaignPlan, manifest_dir, name) -> None:
    """Drop a member from the campaign: remove its subdir, prune every edge/seam that referenced it, and
    re-point the entry if it was the removed member. Leaves an id gap (no renumber)."""
    import shutil
    manifest_dir = Path(manifest_dir)
    m = next((x for x in plan.members if x.name == name), None)
    if m is None:
        raise CampaignError(f"no member named {name!r}")
    mdir = _safe_member_dir(manifest_dir, m)             # validate within manifest_dir BEFORE any mutation
    plan.members.remove(m)
    plan.edges = [e for e in plan.edges if e.get("frm") != name and e.get("to") != name]
    plan.seams = [s for s in plan.seams if s.get("frm") != name]
    for s in plan.seams:
        if s.get("to_member") == name:
            s["to_member"] = None
    if plan.entry_name == name:
        plan.entry_name = plan.members[0].name if plan.members else ""
    if mdir.is_dir():
        shutil.rmtree(mdir, ignore_errors=True)
    _save_plan(plan, manifest_dir)


def rename_field(plan: CampaignPlan, manifest_dir, old, new) -> None:
    """Rename a member's STRUCTURAL identity: its subdir + toml_rel + campaign.toml name, and rekey every
    edge/seam/entry that referenced it. Does NOT touch the field's in-game ``[field] name`` (that's the
    separate display name the Logic Editor owns) or the inner field.toml filename -- a structural rename
    only. Ids are unchanged, so no member's gateways need rewriting."""
    manifest_dir = Path(manifest_dir)
    m = next((x for x in plan.members if x.name == old), None)
    if m is None:
        raise CampaignError(f"no member named {old!r}")
    new = _validate_member_name(new)
    if old == new:
        return
    if any(x.name == new for x in plan.members):
        raise CampaignError(f"member name {new!r} is already in this campaign")
    old_dir = _safe_member_dir(manifest_dir, m)          # validated within manifest_dir before the rename
    new_dir = (manifest_dir / new).resolve()
    if old_dir.is_dir() and old_dir != new_dir:
        if new_dir.exists():
            raise CampaignError(f"cannot rename onto existing path {new_dir}")
        old_dir.rename(new_dir)
    m.toml_rel = f"{new}/{Path(m.toml_rel).name}"        # keep the inner filename; swap the subdir
    m.name = new
    for e in plan.edges:
        if e.get("frm") == old:
            e["frm"] = new
        if e.get("to") == old:
            e["to"] = new
    for s in plan.seams:
        if s.get("frm") == old:
            s["frm"] = new
        if s.get("to_member") == old:
            s["to_member"] = new
    if plan.entry_name == old:
        plan.entry_name = new
    _save_plan(plan, manifest_dir)


def set_entry(plan: CampaignPlan, manifest_dir, name, *, entrance=None) -> None:
    """Set the campaign's entry member (and optionally its entrance). Validates the member exists."""
    if name not in {m.name for m in plan.members}:
        raise CampaignError(f"entry {name!r} is not a campaign member")
    plan.entry_name = name
    if entrance is not None:
        plan.entry_entrance = int(entrance)
    _save_plan(plan, manifest_dir)


def add_edge(plan: CampaignPlan, manifest_dir, frm, to, *, entrance=0, gated=False) -> None:
    """Record an in-chain connection in the graph (campaign.toml [[edge]]). NOTE: this is the graph-level
    reflection of connectivity -- the LIVE door is a ``[[gateway]]`` you author in the source member's
    field.toml (the Logic Editor). Both ends must be members."""
    names = {m.name for m in plan.members}
    if frm not in names or to not in names:
        raise CampaignError(f"edge {frm!r}->{to!r}: both ends must be campaign members")
    plan.edges.append({"frm": frm, "to": to, "entrance": int(entrance),
                       "story_conditional": bool(gated)})
    _save_plan(plan, manifest_dir)


def remove_edge(plan: CampaignPlan, manifest_dir, frm, to) -> None:
    """Remove the graph edge(s) frm->to (campaign.toml [[edge]])."""
    plan.edges = [e for e in plan.edges if not (e.get("frm") == frm and e.get("to") == to)]
    _save_plan(plan, manifest_dir)


def _shared_flag_floor(plan: CampaignPlan) -> int:
    """The lowest index a shared [[flag]] may take: just ABOVE every per-member auto-flag block (which span
    [flag_base, flag_base + members*K)), and never below the census-safe floor."""
    block_hi = plan.flag_base + len(plan.members) * plan.flags_per_field - 1
    return max(block_hi + 1, FIRST_SAFE_FLAG)


def add_flag(plan: CampaignPlan, manifest_dir, name, index=None) -> dict:
    """Add a shared NAMED campaign flag (a cross-field story gate) to campaign.toml's [[flag]] table; members
    then gate by NAME (``requires_flag = "<name>"``). ``index=None`` auto-picks the next free safe index
    ABOVE the per-member auto-flag blocks (inside [FIRST_SAFE_FLAG, CHOICE_SCRATCH_FLOOR)). Validates name +
    band; returns the new ``{name, index}``."""
    name = str(name).strip()
    if not name:
        raise CampaignError("a shared flag needs a name")
    floor = _shared_flag_floor(plan)
    used = {int(f.get("index", -1)) for f in plan.flags}
    if index is None:
        index = max([floor] + [i + 1 for i in used])
    index = int(index)
    if not (floor <= index < CHOICE_SCRATCH_FLOOR):
        raise CampaignError(f"flag index {index} must be in [{floor}, {CHOICE_SCRATCH_FLOOR}) -- above the "
                            f"per-member auto-flag blocks, below the choice scratch")
    if index in used:
        raise CampaignError(f"flag index {index} is already used by another shared flag")
    plan.flags.append({"name": name, "index": index})
    try:
        collect_flag_defs({"flag": plan.flags})      # re-validate (dup name, safe band); rollback on failure
    except ValueError as e:
        plan.flags.pop()
        raise CampaignError(str(e))
    _save_plan(plan, manifest_dir)
    return {"name": name, "index": index}


def remove_flag(plan: CampaignPlan, manifest_dir, name) -> None:
    """Remove the shared named flag ``name`` from the campaign's [[flag]] table."""
    keep = [f for f in plan.flags if f.get("name") != name]
    if len(keep) == len(plan.flags):
        raise CampaignError(f"no shared flag named {name!r}")
    plan.flags = keep
    _save_plan(plan, manifest_dir)
