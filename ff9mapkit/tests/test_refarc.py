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


def test_reconcile_fills_entry_and_links(tmp_path):
    # arc_a/A2 has a scripted Field() seam to 200 (== arc_b/B1's source) -> PRECISE field_remap (exact arrival);
    # arc_b/B2 exits to the world map -> worldmap_inject (arrival = arc_c's entry member). Both auto-fill.
    _write_forked_campaign(tmp_path, "arc_a", entry="A1",
                           members=[("A1", 100, 6000), ("A2", 101, 6001)], seams=[("A2", 200, "scripted")])
    _write_forked_campaign(tmp_path, "arc_b", entry="B1",
                           members=[("B1", 200, 6100), ("B2", 201, 6101)], seams=[("B2", "WORLDMAP", "overworld")])
    _write_forked_campaign(tmp_path, "arc_c", entry="C1",
                           members=[("C1", 300, 6200), ("C2", 301, 6201)], seams=[])

    out, notes = refarc.reconcile_arc_journey(_three_arc_scaffold(), tmp_path)
    assert "ENTRY_MEMBER" not in out and "BOUNDARY_MEMBER" not in out and "ARRIVAL_MEMBER" not in out
    p = tmp_path / "journeys.toml"
    p.write_text(out, encoding="utf-8")
    j = journey.load_journeys(p).journeys[0]                       # parses + resolves structurally
    assert j.entry.campaign == "arc_a" and j.entry.field == "A1"
    assert [(l.src_campaign, l.src_field, l.dst.campaign, l.dst.field) for l in j.links] == [
        ("arc_a", "A2", "arc_b", "B1"),                            # precise: A2 -> B1 (the matched source)
        ("arc_b", "B2", "arc_c", "C1")]                            # overworld: B2 -> arc_c's entry
    assert any(n.level == "filled" and "entry" in n.text for n in notes)


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


def test_reconcile_flags_a_boundary_with_no_seam(tmp_path):
    # arc_a's only member has NO onward seam -> reconcile can't find a boundary; it still scaffolds the link row
    # (so the journey is structurally complete) but leaves a FILL placeholder + a 'verify' note for the human.
    _write_forked_campaign(tmp_path, "arc_a", entry="A1", members=[("A1", 100, 6000)], seams=[])
    _write_forked_campaign(tmp_path, "arc_b", entry="B1", members=[("B1", 200, 6100)], seams=[])
    out, notes = refarc.reconcile_arc_journey(
        refarc.render_arc_journey_toml(refarc.ReferenceArcSet(title="T", arcs=[
            refarc.ReferenceArc(key="arc_a", name="A", seed=100),
            refarc.ReferenceArc(key="arc_b", name="B", seed=200)])), tmp_path)
    assert "BOUNDARY_MEMBER" in out and "FILL" in out             # placeholder + an inline FILL hint
    assert any(n.level == "verify" for n in notes)


def test_cli_reconcile_fills_in_place(tmp_path, capsys):
    # the `reference-arcs --reconcile <journeys.toml>` CLI path: emit a 2-arc scaffold, simulate the forks, then
    # reconcile in place (return 0, ENTRY_MEMBER gone, the link filled). In-process via cli.main (no subprocess).
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
    assert "ENTRY_MEMBER" not in txt and 'field = "A1"' in txt and 'field = "A2"' in txt and 'field = "B1"' in txt
    # idempotent: a second run writes nothing + says so
    assert cli.main(["reference-arcs", "--reconcile", str(jp)]) == 0
    assert "nothing to fill" in capsys.readouterr().out


def test_reconcile_is_resumable_under_incremental_forks(tmp_path):
    # Fork arc_a + arc_b but NOT arc_c -> reconcile fills the entry (only needs arc_a) but KEEPS every link
    # template (a partial fill would strip the b->c template and a re-run could never recover it -- the HIGH
    # review finding). Then fork arc_c and re-run -> the WHOLE chain links. No silently-missing handoff.
    _write_forked_campaign(tmp_path, "arc_a", entry="A1",
                           members=[("A1", 100, 6000), ("A2", 101, 6001)], seams=[("A2", 200, "scripted")])
    _write_forked_campaign(tmp_path, "arc_b", entry="B1",
                           members=[("B1", 200, 6100), ("B2", 201, 6101)], seams=[("B2", "WORLDMAP", "overworld")])
    out1, notes1 = refarc.reconcile_arc_journey(_three_arc_scaffold(), tmp_path)
    assert 'field = "A1"' in out1 and "ENTRY_MEMBER" not in out1            # entry fills early
    assert "# [[journey.link]]" in out1                                     # ALL link templates kept...
    assert out1.count("\n[[journey.link]]") == 0                            # ...and NO real link rows written yet
    assert any(n.level == "verify" and "arc_c" in n.text for n in notes1)
    _write_forked_campaign(tmp_path, "arc_c", entry="C1",
                           members=[("C1", 300, 6200), ("C2", 301, 6201)], seams=[])
    out2, _ = refarc.reconcile_arc_journey(out1, tmp_path)                  # now every boundary resolves
    p = tmp_path / "journeys.toml"
    p.write_text(out2, encoding="utf-8")
    j = journey.load_journeys(p).journeys[0]
    assert [(l.src_campaign, l.dst.campaign) for l in j.links] == [("arc_a", "arc_b"), ("arc_b", "arc_c")]


def test_reconcile_marks_an_ambiguous_precise_tie_inline(tmp_path):
    # TWO members of arc_a each have a single Field() seam landing in arc_b -> a precise TIE. Reconcile picks one
    # but MUST mark it inline (# VERIFY) so it isn't silently wrong (the GUI status promises an inline marker).
    _write_forked_campaign(tmp_path, "arc_a", entry="A1", members=[("A1", 100, 6000), ("A2", 101, 6001)],
                           seams=[("A1", 200, "scripted"), ("A2", 201, "scripted")])
    _write_forked_campaign(tmp_path, "arc_b", entry="B1", members=[("B1", 200, 6100), ("B2", 201, 6101)], seams=[])
    aset = refarc.ReferenceArcSet(title="Tie", arcs=[refarc.ReferenceArc(key="arc_a", name="A", seed=100, beat=0),
                                                     refarc.ReferenceArc(key="arc_b", name="B", seed=200)])
    out, notes = refarc.reconcile_arc_journey(refarc.render_arc_journey_toml(aset), tmp_path)
    assert "# VERIFY" in out and "exit into arc_b" in out                  # the tie is flagged in the file
    assert any(n.level == "verify" for n in notes)
    p = tmp_path / "journeys.toml"
    p.write_text(out, encoding="utf-8")
    journey.load_journeys(p)                                               # still valid TOML
