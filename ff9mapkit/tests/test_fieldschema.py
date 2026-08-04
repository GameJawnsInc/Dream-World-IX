"""The harvested field.toml schema: the recording wrapper, the checker, and the shipped data.

The vocabulary is PROBE-harvested (``fieldschema.py``): the schema is what the pipeline's own
consumers ask about, not what authored files happen to use -- usage isn't a schema. These tests
pin four things: the recorder's semantics (what counts as a probe), the checker's behavior on
realistic typos (including the cross-section class a flat usage-scraped list can never catch),
the no-false-positives bar (every authored example in the repo checks CLEAN -- the failure that
killed the usage-harvested attempt), and the shipped data's own invariants (editor form specs
covered; a lint-stage probe subset so a new consumer read can't outrun a regen silently).
"""
from __future__ import annotations

import copy
import tomllib
from pathlib import Path

import pytest

from ff9mapkit import _fieldschema, _regen_fieldschema, build, fieldschema as fs

KIT_ROOT = Path(__file__).resolve().parents[1]
HUT = KIT_ROOT / "examples" / "vivi-hut" / "hut_int.field.toml"


def _schema():
    return fs.load_schema()


# --------------------------------------------------------------------- the recording wrapper

def test_probes_record_per_path_present_or_not():
    rec = fs.Recorder()
    spy = fs.wrap({"field": {"id": 1}, "npc": [{"name": "a", "anims": {"walk": 500}}]}, rec)
    spy.get("field")
    assert "field" in rec.probes[""]
    spy["field"].get("missing_key")                     # a probe for an ABSENT key still records
    assert "missing_key" in rec.probes["field"]
    n = spy["npc"][0]                                   # list entries share the list key's path
    _ = "model" in n
    assert "model" in rec.probes["npc"]
    n["anims"].get("run")
    assert "run" in rec.probes["npc.anims"]
    n.setdefault("face", 0)
    n.pop("nope", None)
    assert {"face", "nope"} <= rec.probes["npc"]


def test_exhaustive_reads_record_nothing_but_children_stay_wrapped():
    rec = fs.Recorder()
    spy = fs.wrap({"camera": {"pitch": 48}, "npc": [{"name": "a"}]}, rec)
    list(spy.items())
    list(spy)
    plain = {**spy}                                     # C-level copy: bypasses overrides
    assert not any(rec.probes.values())                 # copying a dict is not a probe
    plain["camera"].get("pitch")                        # ...but the copied VALUES are still spies
    assert "pitch" in rec.probes["camera"]


def test_consumer_writes_and_deepcopy_are_safe():
    rec = fs.Recorder()
    spy = fs.wrap({"choice": [{"options": [{"text": "x"}]}]}, rec)
    spy["extra"] = {"sub": 1}                           # a consumer write-back stays recordable
    spy["extra"].get("sub")
    assert "sub" in rec.probes["extra"]
    dup = copy.deepcopy(spy)                            # degrades to a plain dict, never crashes
    assert type(dup) is dict and dup["choice"][0]["options"][0]["text"] == "x"


def test_load_seam_wraps_only_inside_harvesting():
    with fs.harvesting(fs.Recorder()) as rec:
        proj = build.FieldProject.load(HUT)
    assert type(proj.raw) is not dict                   # wrapped (the seam fired)
    assert "ferry" in rec.probes[""]                    # the load pipeline itself probed (desugar)
    proj2 = build.FieldProject.load(HUT)                # outside the context: plain production load
    assert type(proj2.raw) is dict


# --------------------------------------------------------------------- the checker

def test_every_authored_example_checks_clean():
    """THE no-false-positives bar. A usage-scraped whitelist died here; the probe harvest must not."""
    vocab, enforced = _schema()
    roots = [KIT_ROOT / "examples", KIT_ROOT.parent / "examples"]
    seen = 0
    for root in roots:
        if not root.is_dir():
            continue
        for f in sorted(root.rglob("*.field.toml")):
            with f.open("rb") as fh:
                data = tomllib.load(fh)
            assert fs.check(data, vocab=vocab, enforced=enforced) == [], f
            seen += 1
    assert seen >= 12                                   # the bundled corpus, at least


_TYPOS = [
    # (doc, substring the finding must carry) -- realistic slips, one per line
    ({"feild": {"id": 1}}, "did you mean 'field'"),
    ({"npc": [{"dialouge": "hi"}]}, "did you mean 'dialogue'"),
    ({"gateway": [{"entrace": 0}]}, "did you mean 'entrance'"),
    ({"npc": [{"requires_flags": 1}]}, "did you mean 'requires_flag'"),
    ({"field": {"text_blok": 8}}, "did you mean 'text_block'"),
    ({"event": [{"giv_item": [1, 1]}]}, "did you mean 'give_item'"),
    ({"camera": {"pich": 48}}, "did you mean 'pitch'"),
    ({"walkmseh": {"quad": []}}, "did you mean 'walkmesh'"),
    ({"chest": [{"itme": [1, 1]}]}, "did you mean 'item'"),
]


@pytest.mark.parametrize("doc,want", _TYPOS, ids=[t[1].split("'")[1] for t in _TYPOS])
def test_realistic_typos_are_caught_with_suggestions(doc, want):
    vocab, enforced = _schema()
    found = fs.check(doc, vocab=vocab, enforced=enforced)
    assert len(found) == 1 and want in found[0], found


def test_cross_section_key_names_where_it_belongs():
    """'zone' is real on gateways/events -- a FLAT usage list would wave it through on an [[npc]].
    This is exactly the 5/7 failure class of the scraped-whitelist attempt."""
    vocab, enforced = _schema()
    assert "zone" not in vocab["npc"]                   # if this ever fails, the test is obsolete, not the code
    found = fs.check({"npc": [{"zone": []}]}, vocab=vocab, enforced=enforced)
    assert len(found) == 1 and "is a key of" in found[0] and "not of [[npc]]" in found[0], found


def test_key_unknown_anywhere_carries_the_regen_hint():
    vocab, enforced = _schema()
    found = fs.check({"npc": [{"frobnicate": 1}]}, vocab=vocab, enforced=enforced)
    assert len(found) == 1 and "_regen_fieldschema" in found[0], found


def test_unenforced_paths_are_skipped_not_guessed():
    """A section whose consumers never ran end-to-end in the corpus is recorded but NOT enforced --
    honest degradation beats a confident false positive. ([scene] is the durable example: its `file`
    is probed on the PRE-merge base, before the harvest seam, so no corpus run can enforce it.
    `mint` graduated when the regen started generating boletta's payload.)"""
    vocab, enforced = _schema()
    assert "scene" in vocab[""] and "scene" not in enforced
    assert fs.check({"scene": {"anything_at_all": 1}}, vocab=vocab, enforced=enforced) == []


def test_nothing_is_checked_below_an_unknown_key():
    vocab, enforced = _schema()
    found = fs.check({"npcs": [{"dialouge": "x", "postion": []}]}, vocab=vocab, enforced=enforced)
    assert len(found) == 1                              # the section finding only, no noise below it


# --------------------------------------------------------------------- lint integration

def test_lint_unknown_keys_reads_the_authored_file(tmp_path):
    p = tmp_path / "typo.field.toml"
    p.write_text('[field]\nid = 31998\nname = "T"\narea = 11\ntext_blok = 9\n\n[camera]\npitch = 48\n'
                 'distance = 4500\nfov = 42.2\n', encoding="utf-8")
    proj = build.FieldProject.load(p)
    found = build.lint_unknown_keys(proj)
    assert len(found) == 1 and "text_blok" in found[0]
    rep = build.lint_all(proj)
    assert rep.unknown == found and found[0] in rep.warnings and not rep.ok


def test_project_from_dict_has_no_authored_file_to_check():
    proj = build.FieldProject({"field": {"id": 1, "name": "X", "area": 11, "text_blok": 9}}, Path("."))
    assert build.lint_unknown_keys(proj) == []


# --------------------------------------------------------------------- the shipped data

def test_schema_invariants():
    vocab, enforced = _schema()
    assert "" in vocab and "" in enforced
    assert enforced <= set(vocab)                       # never enforce where there is no vocabulary
    assert all(vocab[p] for p in enforced)
    assert _regen_fieldschema._REQUIRED_ENFORCED <= enforced   # the won ground stays won


def test_editor_form_specs_are_covered():
    """The editor WRITES its spec keys; every one must be legal to the checker. Ties the two curated
    surfaces together -- if a form gains a key the build never reads, this fails until a regen."""
    vocab, _ = _schema()
    for path, keys in _regen_fieldschema._seed_vocab().items():
        assert keys <= vocab.get(path, frozenset()), (path, keys - vocab.get(path, frozenset()))


def test_lint_stage_probes_are_a_subset_of_the_shipped_vocab():
    """Freshness, cheap half: everything load+validate+lint probe on the golden example must already
    be in the shipped vocabulary. A new consumer key read at these stages fails here until
    `py -m ff9mapkit._regen_fieldschema` runs. (Build-stage-only additions are caught by the
    examples-clean test the moment a fixture uses the new key.)"""
    vocab, _ = _schema()
    with fs.harvesting(fs.Recorder()) as rec:
        proj = build.FieldProject.load(HUT)
    build.validate(proj)
    build.lint_all(proj)
    for path, keys in rec.probes.items():
        assert keys <= vocab.get(path, frozenset()), (path, keys - vocab.get(path, frozenset()))
