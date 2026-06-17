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
    assert m.hub.get("id") == 4711 and m.hub.get("name") == "My Disc 1"
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
