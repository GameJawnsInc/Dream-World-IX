"""The FF9 reference-arc scaffold (:mod:`ff9mapkit.refarc`): the curated arc->seed table loader + the
multi-campaign journeys.toml / fork-playbook generators. Pure + tk-free -- no game install, no Qt."""

from __future__ import annotations

import pytest

from ff9mapkit import journey, refarc


# --------------------------------------------------------------------------- the packaged disc-1 table
def test_packaged_table_loads_in_story_order():
    aset = refarc.load_reference_arcs()
    assert aset.title and len(aset.arcs) >= 10
    keys = [a.key for a in aset.arcs]
    assert keys[0] == "alexandria" and "ice_cavern" in keys and "dali" in keys
    # every arc has a real-field seed + a name; keys are unique
    assert all(a.seed > 0 and a.name for a in aset.arcs)
    assert len(set(keys)) == len(keys), "arc keys must be unique (each = a distinct campaign folder)"


def test_id_bases_are_disjoint_and_prefixes_unique():
    aset = refarc.load_reference_arcs()
    bases = [refarc.arc_id_base(i) for i in range(len(aset.arcs))]
    assert bases == sorted(bases) and len(set(bases)) == len(bases), "id bands must not overlap"
    assert all(b2 - b1 >= 25 for b1, b2 in zip(bases, bases[1:])), "each band must clear import-chain's 25 members"
    prefixes = refarc.arc_name_prefixes(aset)
    assert len(set(prefixes.values())) == len(prefixes), "FBG/EVT name prefixes must be unique (by-name resolution)"


def test_compose_region_fork_single_and_composed():
    # the GUI "Fork FF9 regions" catalog: one region -> its seed + its tag; several -> composed seeds, no prefix
    aset = refarc.load_reference_arcs()
    a0, a1 = aset.arcs[0], aset.arcs[1]
    seeds1, pfx1, n1 = refarc.compose_region_fork(aset, [a0.key])
    assert seeds1 == str(a0.seed) and "," not in seeds1 and n1 == 1
    assert pfx1 == refarc.arc_name_prefixes(aset)[a0.key]          # single -> the region's unique tag
    seeds2, pfx2, n2 = refarc.compose_region_fork(aset, [a0.key, a1.key])
    assert seeds2 == f"{a0.seed},{a1.seed}" and n2 == 2 and pfx2 == ""   # composed in CATALOG order, author names it
    # order follows the CATALOG, not the selection order -- even for a 3-pick out-of-order selection
    if len(aset.arcs) >= 5:
        ks = [aset.arcs[4].key, aset.arcs[0].key, aset.arcs[2].key]
        assert refarc.compose_region_fork(aset, ks)[0] == ",".join(str(aset.arcs[i].seed) for i in (0, 2, 4))
    # unknown keys are silently dropped -> a lone real pick stays a SINGLE pick (still gets its tag)
    assert refarc.compose_region_fork(aset, [a0.key, "__nope__"]) == (str(a0.seed), pfx1, 1)
    assert refarc.compose_region_fork(aset, [a0.key, a0.key])[2] == 1     # duplicate keys collapse (set-dedup)
    with pytest.raises(refarc.RefArcError):
        refarc.compose_region_fork(aset, [])                      # nothing selected
    with pytest.raises(refarc.RefArcError):
        refarc.compose_region_fork(aset, ["__only_unknown__"])    # all unknown -> nothing to fork


def test_members_roundtrip_and_fork_command_emits_ids(tmp_path):
    # an arc WITH members forks just that cluster (--ids); WITHOUT, the whole zone (--whole-zone). Both round-trip.
    aset = refarc.ReferenceArcSet(title="T", arcs=[
        refarc.ReferenceArc(key="opening", name="Opening", seed=100, zone="alxt",
                            members=[*range(100, 118), 150, 151]),     # non-contiguous cluster
        refarc.ReferenceArc(key="whole", name="Whole", seed=300, zone="iccv")])     # no members
    cmd_ids = refarc.fork_command(aset.arcs[0], id_base=6000, tag="OP", flags_per_field=32)
    assert "--ids 100-117,150-151" in cmd_ids and "--whole-zone" not in cmd_ids
    cmd_whole = refarc.fork_command(aset.arcs[1], id_base=6200, tag="WH", flags_per_field=32)
    assert "--whole-zone" in cmd_whole and "--ids" not in cmd_whole
    # render -> reload preserves members exactly (compact range string), and None stays None
    p = tmp_path / "rc.toml"
    p.write_text(refarc.render_arc_table_toml(aset), encoding="utf-8")
    back = refarc.load_reference_arcs(p)
    assert back.arcs[0].members == [*range(100, 118), 150, 151]
    assert back.arcs[1].members is None
    # a malformed members string is rejected loudly
    p.write_text('title="x"\n[[arc]]\nkey="k"\nname="K"\nseed=1\nmembers="9-1"\n', encoding="utf-8")
    with pytest.raises(refarc.RefArcError):
        refarc.load_reference_arcs(p)


def test_compose_region_ids_unions_and_falls_back():
    aset = refarc.ReferenceArcSet(title="T", arcs=[
        refarc.ReferenceArc(key="a", name="A", seed=100, zone="z", members=[100, 101, 102]),
        refarc.ReferenceArc(key="b", name="B", seed=200, zone="z", members=[200, 201]),
        refarc.ReferenceArc(key="whole", name="W", seed=300, zone="z")])   # no members
    assert refarc.compose_region_ids(aset, ["a"]) == "100-102"
    assert refarc.compose_region_ids(aset, ["a", "b"]) == "100-102,200-201"   # union of both clusters
    assert refarc.compose_region_ids(aset, ["a", "whole"]) is None            # any whole-zone region -> fall back
    assert refarc.compose_region_ids(aset, []) is None
    assert refarc.compose_region_ids(aset, ["__nope__"]) is None


def test_fork_playbook_lines_are_runnable_import_chain_commands():
    aset = refarc.load_reference_arcs()
    pb = refarc.fork_playbook(aset)
    assert len(pb) == len(aset.arcs)
    folders = []
    for arc, cmd in pb:
        assert cmd.startswith("py -m ff9mapkit import-chain ")
        assert f"import-chain {arc.seed}" in cmd and f"--out {arc.key}" in cmd
        assert "--verbatim" in cmd and "--id-base" in cmd and "--name-prefix" in cmd
        assert "--mod-folder FF9CustomMap-" in cmd       # each arc deploys into its OWN stacked folder
        assert "--flags-per-field" in cmd                # ...and a chain-sized flag block
        folders.append(cmd.split("--mod-folder ", 1)[1].split()[0])
    # the assembler ABORTS on a shared mod_folder -> the playbook must give every arc a distinct one
    assert len(set(folders)) == len(folders), f"mod folders must be disjoint: {folders}"


def test_playbook_flag_windows_fit_the_safe_band():
    # the assembler lays every campaign's flag window end-to-end inside the safe band; at the default 64
    # flags/field a 12-arc chain OVERFLOWS, so the playbook must emit a smaller --flags-per-field that fits.
    aset = refarc.load_reference_arcs()
    fpf = refarc.arc_flags_per_field(len(aset.arcs))
    assert len(aset.arcs) * refarc.MAX_FIELDS_PER_ARC * fpf <= refarc.SAFE_FLAG_BUDGET, "flag windows overflow"
    assert all(f"--flags-per-field {fpf}" in cmd for _a, cmd in refarc.fork_playbook(aset))
    # the per-arc-count sizing actually shrinks as the chain grows
    assert refarc.arc_flags_per_field(2) >= refarc.arc_flags_per_field(12) >= refarc.arc_flags_per_field(40)


def test_default_hub_is_mognet_central():
    # the reference-arc hub defaults to Mognet Central (FF9's journey nexus) -- thematic + a real borrow_field
    # so `deploy_journey --apply` auto-extracts the camera (closing the earlier no-camera gap).
    t = refarc.render_arc_journey_toml(refarc.load_reference_arcs())
    assert f'borrow_bg = "{refarc.HUB_BORROW_BG}"' in t and f"area = {refarc.HUB_BORROW_AREA}" in t
    assert f"borrow_field = {refarc.HUB_BORROW_FIELD}" in t
    # a CUSTOM borrow_bg is passed through with no (unknown) area/borrow_field, just the commented hint
    t2 = refarc.render_arc_journey_toml(refarc.load_reference_arcs(), borrow_bg="GRGR_MAP420_GR_CEN_0")
    assert 'borrow_bg = "GRGR_MAP420_GR_CEN_0"' in t2
    assert "# borrow_field = <real field id>" in t2 and f"area = {refarc.HUB_BORROW_AREA}" not in t2


def test_parse_fork_commands_roundtrips_the_emitted_playbook():
    # the GUI 'Fork the arcs' panel recovers the per-arc import-chain commands from the journeys.toml header.
    aset = refarc.load_reference_arcs()
    text = refarc.render_arc_journey_toml(aset)
    parsed = refarc.parse_fork_commands(text)
    assert [p.key for p in parsed] == [a.key for a in aset.arcs]      # every arc, in file order
    assert [p.seed for p in parsed] == [a.seed for a in aset.arcs]
    ic = next(p for p in parsed if p.key == "ice_cavern")
    assert ic.command.startswith("import-chain 300 --out ice_cavern") and "--flags-per-field 16" in ic.command
    assert refarc.parse_fork_commands('[hub]\nid = 4600\n') == []     # a hand-written file has no playbook


def test_packaged_seeds_are_real_forkable_fields():
    # every disc-1 seed must resolve to a real FF9 field (a dead id only fails at STEP-1 fork time -- catch it
    # here so a future edit to the table is caught offline). The id->FBG table is provenance-clean + baked.
    from ff9mapkit import extract
    if not getattr(extract, "ID_TO_FBG", None):
        pytest.skip("ID_TO_FBG table unavailable in this install")
    aset = refarc.load_reference_arcs()
    dead = [(a.key, a.seed) for a in aset.arcs if a.seed not in extract.ID_TO_FBG]
    assert not dead, f"these arc seeds are not real forkable fields: {dead}"


# --------------------------------------------------------------------------- the journeys.toml output
def test_rendered_journey_loads_through_the_real_journey_loader(tmp_path):
    aset = refarc.load_reference_arcs()
    text = refarc.render_arc_journey_toml(aset, hub_name="My Disc 1", hub_id=4711)
    p = tmp_path / "journeys.toml"
    p.write_text(text, encoding="utf-8")
    m = journey.load_journeys(p)                            # the structural schema is valid
    assert m.hub.get("id") == 4711 and m.hub.get("name") == "My_Disc_1"   # hub name -> EVT/FBG token
    j = m.journeys[0]
    assert j.campaigns == [a.key for a in aset.arcs] and not j.is_bare
    assert j.entry.campaign == aset.arcs[0].key             # entry names the first arc's campaign
    # the fork playbook + each arc's seed/command live in the header comments
    assert "STEP 1" in text and f"import-chain {aset.arcs[2].seed}" in text
    # ascii-only (a generated, hand-edited file -- no cp1252 surprises)
    assert all(ord(c) < 128 for c in text)


def test_rendered_journey_lints_with_fork_first_guidance(tmp_path):
    # the campaigns aren't forked yet -> lint flags exactly that, pointing at the import-chain command. This
    # is the intended ONBOARDING signal (mirrors the multi template), not a structural defect.
    aset = refarc.load_reference_arcs()
    p = tmp_path / "journeys.toml"
    p.write_text(refarc.render_arc_journey_toml(aset), encoding="utf-8")
    errs, _warns = journey.lint_manifest(journey.load_journeys(p))
    assert errs and any("fork it first" in e and "import-chain" in e for e in errs), errs


def test_custom_table_and_validation(tmp_path):
    good = tmp_path / "arcs.toml"
    good.write_text('title = "Mini"\n[[arc]]\nkey = "a"\nname = "A"\nseed = 300\n'
                    '[[arc]]\nkey = "b"\nname = "B"\nseed = 350\nbeat = 2600\n', encoding="utf-8")
    aset = refarc.load_reference_arcs(good)
    assert [a.key for a in aset.arcs] == ["a", "b"] and aset.arcs[1].beat == 2600
    # a beat on the FIRST arc -> a live [journey.seed] (not a commented template)
    a0 = tmp_path / "seeded.toml"
    a0.write_text('[[arc]]\nkey = "z"\nname = "Z"\nseed = 300\nbeat = 1950\n', encoding="utf-8")
    text = refarc.render_arc_journey_toml(refarc.load_reference_arcs(a0))
    assert "[journey.seed]" in text and "scenario = 1950" in text and "# [journey.seed]" not in text

    dup = tmp_path / "dup.toml"
    dup.write_text('[[arc]]\nkey = "x"\nname = "X"\nseed = 1\n[[arc]]\nkey = "x"\nname = "Y"\nseed = 2\n',
                   encoding="utf-8")
    with pytest.raises(refarc.RefArcError):
        refarc.load_reference_arcs(dup)
    missing = tmp_path / "missing.toml"
    missing.write_text('[[arc]]\nname = "no key"\nseed = 1\n', encoding="utf-8")
    with pytest.raises(refarc.RefArcError):
        refarc.load_reference_arcs(missing)
    empty = tmp_path / "empty.toml"
    empty.write_text('title = "nothing"\n', encoding="utf-8")
    with pytest.raises(refarc.RefArcError):
        refarc.load_reference_arcs(empty)


# --------------------------------------------------------------------------- STEP 2 reconcile (after Fork-All)
from ff9mapkit import campaign as _campaign


def _write_forked_campaign(base, key, *, entry, members, seams):
    """Materialize a forked ``<key>/campaign.toml`` (the STEP-1 artifact reconcile reads). ``members`` =
    ``[(name, source_real_id, new_id)]``; ``seams`` = ``[(frm, to_real, kind)]``."""
    plan = _campaign.CampaignPlan(
        name=key, mod_folder=f"FF9CustomMap-{key}", id_base=members[0][2],
        flag_base=_campaign.FIRST_SAFE_FLAG, flags_per_field=16, entry_name=entry, entry_entrance=0,
        members=[_campaign.Member(src, nid, nm, "native", 11, "", f"{nm}/{nm}.field.toml", False)
                 for (nm, src, nid) in members],
        seams=[{"frm": f, "to_real": tr, "kind": k, "note": "", "to_member": None} for (f, tr, k) in seams],
        verbatim=True)
    d = base / key
    d.mkdir(parents=True, exist_ok=True)
    (d / "campaign.toml").write_text(_campaign.render_campaign_toml(plan), encoding="utf-8", newline="\n")


def _three_arc_scaffold():
    aset = refarc.ReferenceArcSet(title="Test Arc", arcs=[
        refarc.ReferenceArc(key="arc_a", name="Arc A", seed=100, beat=0),
        refarc.ReferenceArc(key="arc_b", name="Arc B", seed=200),
        refarc.ReferenceArc(key="arc_c", name="Arc C", seed=300)])
    return refarc.render_arc_journey_toml(aset)


def test_reconcile_fills_entry_no_link_rows(tmp_path):
    # (i): reconcile fills the ENTRY + strips link templates; it writes NO link rows -- cross-campaign warps
    # AUTO-WIRE at DEPLOY from the real .eb seams. resolve_journey is where the connectivity materializes.
    _write_forked_campaign(tmp_path, "arc_a", entry="A1",
                           members=[("A1", 100, 6000), ("A2", 101, 6001)], seams=[("A2", 200, "scripted")])
    _write_forked_campaign(tmp_path, "arc_b", entry="B1",
                           members=[("B1", 200, 6100), ("B2", 201, 6101)], seams=[("B2", "WORLDMAP", "overworld")])
    _write_forked_campaign(tmp_path, "arc_c", entry="C1",
                           members=[("C1", 300, 6200), ("C2", 301, 6201)], seams=[])
    out, notes = refarc.reconcile_arc_journey(_three_arc_scaffold(), tmp_path)
    assert "ENTRY_MEMBER" not in out and out.count("\n[[journey.link]]") == 0   # entry filled, NO active link rows
    assert any(n.level == "filled" and "entry" in n.text for n in notes)
    assert any("auto-wire at DEPLOY" in n.text for n in notes)
    p = tmp_path / "journeys.toml"
    p.write_text(out, encoding="utf-8")
    m = journey.load_journeys(p)
    j = m.journeys[0]
    assert j.entry.campaign == "arc_a" and j.entry.field == "A1" and j.links == []   # zero explicit links
    rj = journey.resolve_journey(j, journey.load_campaign_plans(m))     # connectivity AUTO-DERIVED here
    edges = {(l["src_campaign"], l["src_field"], l["dst_campaign"], l["dst_field"]) for l in rj.links}
    assert ("arc_a", "A2", "arc_b", "B1") in edges                     # precise Field 200 -> B1
    assert ("arc_b", "B2", "arc_c", "C1") in edges                     # overworld -> arc_c entry (listed order)


def test_reconcile_flags_a_stranded_campaign(tmp_path):
    # arc_a's seams reach arc_c (Field 300), NOT the next arc_b, and nothing warps INTO arc_b -> reconcile reports
    # arc_b STRANDED (the game doesn't connect it in this set), the lint warns unreachable. No BOUNDARY_MEMBER.
    _write_forked_campaign(tmp_path, "arc_a", entry="A1", members=[("A1", 100, 6000), ("A2", 101, 6001)],
                           seams=[("A2", 300, "scripted")])
    _write_forked_campaign(tmp_path, "arc_b", entry="B1", members=[("B1", 200, 6100), ("B2", 201, 6101)], seams=[])
    _write_forked_campaign(tmp_path, "arc_c", entry="C1",
                           members=[("C1", 300, 6200), ("C2", 301, 6201)], seams=[])
    out, notes = refarc.reconcile_arc_journey(_three_arc_scaffold(), tmp_path)
    assert "BOUNDARY_MEMBER" not in out
    assert any("arc_b" in n.text and "no real warp connects" in n.text for n in notes)
    p = tmp_path / "journeys.toml"
    p.write_text(out, encoding="utf-8")
    _e, warns = journey.lint_manifest(journey.load_journeys(p))
    assert any("unreachable" in w and "arc_b" in w for w in warns)


def test_reconcile_skips_when_not_forked(tmp_path):
    # no campaign folders on disk yet -> a 'skip' note pointing at STEP 1, and the text is unchanged.
    text = _three_arc_scaffold()
    out, notes = refarc.reconcile_arc_journey(text, tmp_path)
    assert out == text
    assert any(n.level == "skip" and "fork the campaigns first" in n.text for n in notes)


def test_reconcile_is_idempotent(tmp_path):
    for k, e, mem, sm in [("arc_a", "A1", [("A1", 100, 6000), ("A2", 101, 6001)], [("A2", 200, "scripted")]),
                          ("arc_b", "B1", [("B1", 200, 6100), ("B2", 201, 6101)], [("B2", "WORLDMAP", "overworld")]),
                          ("arc_c", "C1", [("C1", 300, 6200), ("C2", 301, 6201)], [])]:
        _write_forked_campaign(tmp_path, k, entry=e, members=mem, seams=sm)
    once, _ = refarc.reconcile_arc_journey(_three_arc_scaffold(), tmp_path)
    twice, notes = refarc.reconcile_arc_journey(once, tmp_path)    # re-running must not duplicate links / re-touch
    assert twice == once
    assert any(n.level == "skip" for n in notes)


def test_auto_wire_precise_arrival_over_overworld(tmp_path):
    # A boundary member with a Field() door INTO the next arc AND an incidental overworld exit keeps its PRECISE
    # arrival (the door's real target member B2), not the generic entry -- the Field seam wins over the overworld.
    _write_forked_campaign(tmp_path, "arc_a", entry="A1", members=[("A1", 100, 6000), ("A2", 101, 6001)],
                           seams=[("A2", 201, "scripted"), ("A2", "WORLDMAP", "overworld")])
    # arc_b: B1 is the entry (source 200); B2 (source 201) is the NON-entry member the A2 door lands on.
    _write_forked_campaign(tmp_path, "arc_b", entry="B1", members=[("B1", 200, 6100), ("B2", 201, 6101)], seams=[])
    aset = refarc.ReferenceArcSet(title="P", arcs=[refarc.ReferenceArc(key="arc_a", name="A", seed=100, beat=0),
                                                   refarc.ReferenceArc(key="arc_b", name="B", seed=200)])
    out, _ = refarc.reconcile_arc_journey(refarc.render_arc_journey_toml(aset), tmp_path)
    p = tmp_path / "journeys.toml"
    p.write_text(out, encoding="utf-8")
    m = journey.load_journeys(p)
    rj = journey.resolve_journey(m.journeys[0], journey.load_campaign_plans(m))
    edges = {(l["src_campaign"], l["src_field"], l["dst_campaign"], l["dst_field"]) for l in rj.links}
    assert ("arc_a", "A2", "arc_b", "B2") in edges                 # precise B2 (real 201), not the entry B1


def test_cli_reconcile_fills_in_place(tmp_path, capsys):
    # the `reference-arcs --reconcile <journeys.toml>` CLI path: emit a 2-arc scaffold, simulate the forks, then
    # reconcile in place (return 0, ENTRY_MEMBER gone, NO link rows -- links auto-wire). In-process via cli.main.
    from ff9mapkit import cli
    (tmp_path / "arcs.toml").write_text(
        'title = "Mini"\n[[arc]]\nkey = "ca"\nname = "A"\nseed = 100\nbeat = 0\n'
        '[[arc]]\nkey = "cb"\nname = "B"\nseed = 200\n', encoding="utf-8")
    assert cli.main(["reference-arcs", "--table", str(tmp_path / "arcs.toml"), "--emit", str(tmp_path)]) == 0
    _write_forked_campaign(tmp_path, "ca", entry="A1",
                           members=[("A1", 100, 6000), ("A2", 101, 6001)], seams=[("A2", 200, "scripted")])
    _write_forked_campaign(tmp_path, "cb", entry="B1", members=[("B1", 200, 6100)], seams=[])
    jp = tmp_path / "journeys.toml"
    assert cli.main(["reference-arcs", "--reconcile", str(jp)]) == 0
    txt = jp.read_text(encoding="utf-8")
    assert "ENTRY_MEMBER" not in txt and 'field = "A1"' in txt and txt.count("\n[[journey.link]]") == 0   # no rows
    assert cli.main(["reference-arcs", "--reconcile", str(jp)]) == 0   # idempotent (second run a no-op)


def test_reconcile_is_resumable_under_incremental_forks(tmp_path):
    # Fork arc_a + arc_b but NOT arc_c -> reconcile fills the entry (only needs arc_a), writes NO links, and notes
    # "fork arc_c first" (the connectivity graph needs every fork). Then fork arc_c + re-run -> the WHOLE chain
    # auto-wires at deploy (resolve_journey shows it). No silently-missing handoff.
    _write_forked_campaign(tmp_path, "arc_a", entry="A1",
                           members=[("A1", 100, 6000), ("A2", 101, 6001)], seams=[("A2", 200, "scripted")])
    _write_forked_campaign(tmp_path, "arc_b", entry="B1",
                           members=[("B1", 200, 6100), ("B2", 201, 6101)], seams=[("B2", "WORLDMAP", "overworld")])
    out1, notes1 = refarc.reconcile_arc_journey(_three_arc_scaffold(), tmp_path)
    assert 'field = "A1"' in out1 and "ENTRY_MEMBER" not in out1            # entry fills early
    assert out1.count("\n[[journey.link]]") == 0                            # NO real link rows
    assert any(n.level == "verify" and "arc_c" in n.text for n in notes1)   # fork arc_c first to preview
    _write_forked_campaign(tmp_path, "arc_c", entry="C1",
                           members=[("C1", 300, 6200), ("C2", 301, 6201)], seams=[])
    out2, _ = refarc.reconcile_arc_journey(out1, tmp_path)                  # now every campaign forked
    p = tmp_path / "journeys.toml"
    p.write_text(out2, encoding="utf-8")
    m = journey.load_journeys(p)
    rj = journey.resolve_journey(m.journeys[0], journey.load_campaign_plans(m))
    edges = {(l["src_campaign"], l["dst_campaign"]) for l in rj.links}      # whole chain auto-wires
    assert ("arc_a", "arc_b") in edges and ("arc_b", "arc_c") in edges


def test_fork_playbook_uses_whole_zone_and_fixed_seeds():
    # reference-arc forks must capture the WHOLE zone (cutscene zones don't door-connect from the seed), and
    # the previously-ISOLATED entry seeds were corrected to connected entrances (so the chain arrives walkable).
    aset = refarc.load_reference_arcs()
    for _arc, cmd in refarc.fork_playbook(aset):
        assert "--whole-zone" in cmd, cmd
    by_key = {a.key: a.seed for a in aset.arcs}
    assert by_key["evil_forest"] == 250    # ef_ent (entrance), not 152/ef_fr6 (an isolated cutscene screen)
    assert by_key["cargo_ship"] == 507     # ca_dck_0 (walkable deck), not 500/ca_dck_1 (a cutscene variant)
    assert by_key["treno"] == 1908         # tr_gat (city gate), not 916/tr_whf (isolated)


# --------------------------------------------------------------------------- generated zone catalog (the picker)
def test_generate_zone_catalog_real_seeds():
    # derived from the game's real field->zone data -> accurate by construction (no hand-drafted seeds).
    cat = refarc.generate_zone_catalog()
    primary = {}                                # the FIRST (lowest-id) cluster per zone = the disc-1 visit
    for a in cat.arcs:
        primary.setdefault(a.zone, a)
    assert primary["tshp"].seed == 50           # Prima Vista opening (lowest id = cargo room = the New-Game entry)
    assert primary["evft"].seed == 250          # Evil Forest ENTRANCE via the _ENT heuristic, NOT the 152 cutscene
    assert primary["iccv"].seed == 300          # Ice Cavern entrance
    assert primary["alxt"].seed == 100          # Alexandria town (its own region, separate from Prima Vista)
    assert "invalidfieldmapid" not in primary   # field 70 (the FMV opening script, no real BG) is filtered out
    assert len(cat.arcs) > 30 and all(a.zone and a.seed > 0 for a in cat.arcs)


def test_generate_zone_catalog_splits_visits():
    # FF9 stores a place's revisits as separate id clusters -> one [[arc]] per visit, each scoped to its ids.
    cat = refarc.generate_zone_catalog()
    alxt = [a for a in cat.arcs if a.zone == "alxt"]
    assert len(alxt) >= 4                                       # opening + the returns + the ending
    opening = alxt[0]
    assert opening.key == "alexandria" and opening.seed == 100  # the primary keeps the clean key/name + lowest id
    assert opening.members == list(range(100, 118))             # the disc-1 cluster ONLY (18 fields, not all 48)
    assert all(100 <= m <= 117 for a0 in [opening] for m in a0.members)
    later = alxt[1]                                             # a later visit -> suffixed key/name, higher ids
    assert later.key.startswith("alexandria_") and min(later.members) >= 1850
    # one zone, every cluster member is disjoint from the others (no field forked twice within a zone)
    seen = set()
    for a in alxt:
        assert not (set(a.members) & seen), f"{a.key} overlaps a sibling visit"
        seen.update(a.members)
    # and --no-split-visits restores one whole-zone arc (members=None -> --whole-zone dynamic re-gather) per zone
    whole = refarc.generate_zone_catalog(split_visits=False)
    walxt = [a for a in whole.arcs if a.zone == "alxt"]
    assert len(walxt) == 1 and walxt[0].members is None
    assert "--whole-zone" in refarc.fork_command(walxt[0], id_base=6000, tag="AL", flags_per_field=32)


def test_generate_zone_catalog_disambiguates_cross_zone_names():
    # distinct zones sharing one manifest area label (Dali = vgdl/udft/airp) get a [zone] suffix so the picker
    # rows are distinguishable; a name unique to one zone is left clean.
    cat = refarc.generate_zone_catalog()
    names = [a.name for a in cat.arcs]
    assert len(names) == len(set(names)), "every display name must be unique in the picker"
    dali = [a for a in cat.arcs if a.zone in ("vgdl", "udft", "airp") and a.seed in (359, 404, 450)]
    assert all(a.name.endswith(f"[{a.zone}]") for a in dali) and len(dali) == 3
    alex = next(a for a in cat.arcs if a.key == "alexandria")
    assert alex.name == "Alexandria"                            # unique to alxt -> no suffix


def test_region_catalog_round_trips_and_ships_current():
    import tomllib
    cat = refarc.generate_zone_catalog()
    tomllib.loads(refarc.render_arc_table_toml(cat))                  # the rendered table is valid TOML
    # the PICKER reads the shipped data/region_catalog.toml; it must be the accurate all-zones catalog...
    picker = refarc.load_region_catalog()
    assert any(a.zone == "tshp" and a.seed == 50 for a in picker.arcs)
    # ...and current (not a stale committed file) -- same (zone, seed) set as a fresh generation.
    assert {(a.zone, a.seed) for a in picker.arcs} == {(a.zone, a.seed) for a in cat.arcs}


def test_regenerate_region_catalog_writes(tmp_path):
    p, n = refarc.regenerate_region_catalog(out=tmp_path / "rc.toml")
    assert p.is_file() and n > 30
    reloaded = refarc.load_reference_arcs(p)
    assert any(a.zone == "evft" and a.seed == 250 for a in reloaded.arcs)


# --------------------------------------------------------------------------- append_region_to_arc (grow a chain)
def _two_arc_scaffold():
    aset = refarc.ReferenceArcSet(title="Test Arc", arcs=[
        refarc.ReferenceArc(key="arc_a", name="Arc A", seed=100, beat=0, note="first"),
        refarc.ReferenceArc(key="arc_b", name="Arc B", seed=200, note="second")])
    return refarc.render_arc_journey_toml(aset)


def _arc_c():
    return refarc.ReferenceArc(key="arc_c", name="Arc C", seed=300, note="third")


def test_append_region_with_members_emits_ids():
    # a catalog region carries members -> its appended fork line scopes to that visit (--ids), not --whole-zone
    arc = refarc.ReferenceArc(key="arc_c", name="Arc C", seed=300, zone="iccv",
                              members=[*range(300, 312)], note="third")
    out, _ = refarc.append_region_to_arc(_two_arc_scaffold(), arc)
    cline = next(ln for ln in out.splitlines() if "--out arc_c" in ln)   # the NEW arc's fork line only
    assert "--ids 300-311" in cline and "--whole-zone" not in cline
    refarc.parse_fork_commands(out)                            # the playbook still round-trips


def test_append_region_grows_campaigns_playbook_and_link():
    import tomllib
    out, notes = refarc.append_region_to_arc(_two_arc_scaffold(), _arc_c())
    data = tomllib.loads(out)                                  # still valid TOML
    j = next(x for x in data["journey"] if x.get("campaigns"))
    assert j["campaigns"] == ["arc_a", "arc_b", "arc_c"], j["campaigns"]
    # a fork command for arc_c in the header playbook, with a DISJOINT id band (max 6200 + 200 = 6400)
    assert "--out arc_c" in out and "--id-base 6400" in out and "--name-prefix ARC" in out
    assert "--mod-folder FF9CustomMap-" in out and "--verbatim" in out and "--whole-zone" in out
    # a commented [[journey.link]] template for the new boundary (arc_b -> arc_c), which reconcile later fills
    assert '# from = { campaign = "arc_b"' in out and '# to = { campaign = "arc_c"' in out
    # the cosmetic count comments stay honest, and the new region's note rides along in the playbook
    assert "the 3 arc folders" in out and "(3 arcs -> 2 links)" in out and "Arc C: third" in out
    assert any(n.level == "filled" and "arc_c" in n.text for n in notes)
    # parsed by the real journey loader (3 campaigns, structurally sound)
    refarc.parse_fork_commands(out)                            # the playbook round-trips


def test_append_region_is_idempotent():
    once, _ = refarc.append_region_to_arc(_two_arc_scaffold(), _arc_c())
    twice, notes = refarc.append_region_to_arc(once, _arc_c())
    assert twice == once and any(n.level == "skip" and "already in this arc" in n.text for n in notes)


def test_append_region_disjoint_band_is_above_the_max():
    # grow twice: arc_c lands at 6400, arc_d at 6600 (each = the running max band + ARC_ID_SPAN, never reused).
    out1, _ = refarc.append_region_to_arc(_two_arc_scaffold(), _arc_c())
    out2, _ = refarc.append_region_to_arc(out1, refarc.ReferenceArc(key="arc_d", name="Arc D", seed=400))
    assert "--out arc_c --whole-zone --verbatim --id-base 6400" in out2
    assert "--out arc_d --whole-zone --verbatim --id-base 6600" in out2


def test_append_region_skips_a_bare_journey():
    bare = '[hub]\nname = "H"\nid = 4600\n\n[[journey]]\nid = "x"\nname = "X"\nentry = 4100\n'
    out, notes = refarc.append_region_to_arc(bare, _arc_c())
    assert out == bare and any(n.level == "skip" and "no multi-campaign" in n.text for n in notes)


def test_count_comments_are_grammatical_across_arc_counts():
    # a 1-arc journey (the intended fork-a-region-at-a-time START) reads in the SINGULAR; growing it re-pluralizes
    # the count comments (and a 2-arc chain has exactly "1 link", not "1 links").
    one = refarc.render_arc_journey_toml(refarc.ReferenceArcSet(
        title="Solo", arcs=[refarc.ReferenceArc(key="arc_a", name="Arc A", seed=100)]))
    assert "the 1 arc folder " in one and "(1 arc -> 0 links)" in one, one
    assert "1 arc folders" not in one and "1 arcs ->" not in one, "no plural-with-1 wart at render"
    grown, _ = refarc.append_region_to_arc(one, refarc.ReferenceArc(key="arc_b", name="Arc B", seed=200))
    assert "the 2 arc folders" in grown and "(2 arcs -> 1 link)" in grown, grown
    assert "(2 arcs -> 1 links)" not in grown, "1 link is singular after the bump"


def test_append_region_then_reconcile_wires_the_new_boundary(tmp_path):
    # the full loop: grow the chain with arc_c, fork all three, reconcile (entry only) -> the new arc_b->arc_c
    # boundary AUTO-WIRES at deploy from arc_b's Field(300) seam (resolve_journey shows it; no link rows).
    grown, _ = refarc.append_region_to_arc(_two_arc_scaffold(), _arc_c())
    _write_forked_campaign(tmp_path, "arc_a", entry="A1",
                           members=[("A1", 100, 6000), ("A2", 101, 6001)], seams=[("A2", 200, "scripted")])
    _write_forked_campaign(tmp_path, "arc_b", entry="B1",
                           members=[("B1", 200, 6200), ("B2", 201, 6201)], seams=[("B2", 300, "scripted")])
    _write_forked_campaign(tmp_path, "arc_c", entry="C1",
                           members=[("C1", 300, 6400), ("C2", 301, 6401)], seams=[])
    out, _ = refarc.reconcile_arc_journey(grown, tmp_path)
    p = tmp_path / "journeys.toml"
    p.write_text(out, encoding="utf-8")
    m = journey.load_journeys(p)
    assert m.journeys[0].links == []                                       # no link rows -- auto-wired at deploy
    rj = journey.resolve_journey(m.journeys[0], journey.load_campaign_plans(m))
    edges = {(l["src_campaign"], l["dst_campaign"]) for l in rj.links}
    assert ("arc_a", "arc_b") in edges and ("arc_b", "arc_c") in edges
