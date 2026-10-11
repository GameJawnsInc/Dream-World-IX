"""``[household]`` -- the sims productization (:mod:`ff9mapkit.content.household`).

Golden provenance: the desugared output mirrors ``studies/sims/sims_bench2.py``'s rung-4 and rung-6 emission
(in-game proven on benches 30433 and 30435) block for block. The two fixtures are that generator's OUTPUT,
frozen: ``fixtures/household_rung{4,6}.field.toml``. A parity test is a REGRESSION harness, not an oracle -- it
proves the block says what the generator said, not that the generator was right (the harness runs did that).
"""
from __future__ import annotations

import copy
import tomllib
from pathlib import Path

import pytest

from ff9mapkit import build as BLD
from ff9mapkit.content import behaviortoml as BT, household as H

HERE = Path(__file__).resolve().parent
FIX = HERE / "fixtures"
EXAMPLE = HERE.parent / "examples" / "household" / "household.field.toml"
GENERATED = ("npc", "prop", "marker", "behavior", "choice")


def _fixture(name: str) -> dict:
    return tomllib.loads((FIX / name).read_text(encoding="utf-8"))


def _desugared(base: dict, household: dict) -> dict:
    """The fixture's HEAD (field/camera/walkmesh/layers/player) + the block, desugared."""
    raw = {k: copy.deepcopy(v) for k, v in base.items() if k not in GENERATED}
    raw["household"] = household
    H.desugar(raw)
    return raw


def _same(got: dict, want: dict) -> None:
    for key in GENERATED:
        assert got.get(key) == want.get(key), key


# ------------------------------------------------------------------------------------------------ parity
def test_bare_household_is_the_rung4_bench():
    want = _fixture("household_rung4.field.toml")
    _same(_desugared(want, {}), want)


def test_household_with_job_and_shop_is_the_rung6_bench():
    want = _fixture("household_rung6.field.toml")
    _same(_desugared(want, {"job": {"skill_table": 6430001}, "shop": {"request_flag": 8890}}), want)


def test_the_behavior_the_block_emits_compiles():
    want = _fixture("household_rung6.field.toml")
    raw = _desugared(want, {"job": {"skill_table": 6430001}, "shop": {"request_flag": 8890}})
    assert BT.validate(raw) == []
    fb, cb = BT.dry_compile(raw)
    assert cb.report


# ------------------------------------------------------------------------------------------------ tuning
def _bare(extra: dict | None = None) -> dict:
    raw = {"field": {"id": 4811}, "household": extra or {}}
    H.desugar(raw)
    return raw


def test_overrides_reach_the_emitted_rows():
    raw = _bare({"urge_at": 30, "need": {"hunger": {"decay": 90, "pose": "laugh", "verb": "snack",
                                                     "pos": [0, -600], "spot": [0, -900]}}})
    b = raw["behavior"]
    assert [d for d in b["drift"] if d.get("index") == 0 and d.get("table") == "need"][0]["every"] == 90
    urge = [br for br in b["unit"][0]["branch"] if br.get("raise_flags") == ["t_hunger"]][0]
    assert urge["when"] == [{"table_le": ["need", 0, 30]}]
    assert any(o["text"] == "Bilba, snack." for c in raw["choice"] for o in c["options"])
    assert {"name": "hunger_spot", "pos": [0, -900]} in raw["marker"]
    # the zone is centred on the OBJECT, not the spot
    zone = [c for c in raw["choice"] if c["prompt"] == "The soup pot."][0]["zone"]
    assert zone == [[-260, -840], [260, -840], [260, -360], [-260, -360]]


def test_a_renamed_sim_names_every_menu_row():
    raw = _bare({"sim": "pip", "label": "Pip", "need": {"energy": {"prompt": "Pip's bed."}}})
    texts = [o["text"] for c in raw["choice"] for o in c["options"]]
    assert "Pip, eat something." in texts and "Pip, stay up all night!" in texts
    assert raw["behavior"]["unit"][0]["npc"] == "pip" and raw["npc"][0]["name"] == "pip"


def test_the_skill_table_id_defaults_to_the_field_id():
    raw = _bare({"job": {}})
    skill = [t for t in raw["behavior"]["table"] if t["name"] == "skill"][0]
    assert skill["id"] == 6_000_000 + 4811 and skill["persist"] is True


def test_no_job_means_the_mood_strip_and_job_means_the_purse_strip():
    plain, jobbed = _bare(), _bare({"job": {}})
    assert "MOOD" in plain["behavior"]["hud"][0]["text"] and "GIL" not in plain["behavior"]["hud"][0]["text"]
    assert "GIL" in jobbed["behavior"]["hud"][0]["text"] and "SELECT" not in jobbed["behavior"]["hud"][0]["text"]
    assert "SELECT: shop" in _bare({"job": {}, "shop": {}})["behavior"]["hud"][0]["text"]


# ------------------------------------------------------------------------------------------------ refusals
@pytest.mark.parametrize("block,frag", [
    ({"bogus": 1}, "unknown"),
    ({"need": {"sleepiness": {}}}, "five needs"),
    ({"need": {"hunger": {"decya": 3}}}, "unknown"),
    ({"need": {"hunger": {"pos": [1]}}}, "[x, z] point"),
    ({"need": {"hunger": {"use": [2]}}}, "[by, every]"),
    ({"need": {"hunger": {"use": [2, 0]}}}, "every"),
    ({"urge_at": 95}, "below full_at"),
    ({"start_hour": 24}, "start_hour"),
    ({"shop": {}}, "needs [household.job]"),
    ({"job": {"skill_table": 5}}, "PERSISTENT"),
    ({"job": {"wage_lo": 60, "wage_hi": 60}}, "must differ"),
    ({"job": {}, "shop": {"pose": "laugh"}}, "raw clip id"),
    ({"job": {"nope": 1}}, "unknown"),
])
def test_from_raw_rejects(block, frag):
    with pytest.raises(H.HouseholdError) as ei:
        H.from_raw(block)
    assert frag in str(ei.value)


def test_a_hand_written_behavior_conflicts():
    raw = {"field": {"id": 4811}, "household": {}, "behavior": {"warmup": 1}}
    H.desugar(raw)
    assert raw["behavior"] == {"warmup": 1}                       # untouched
    assert any("owns the field's [behavior]" in p for p in H.problems(raw))


def test_a_job_with_no_field_id_and_no_skill_table_is_refused():
    raw = {"household": {"job": {}}}
    H.desugar(raw)
    assert "behavior" not in raw
    assert any("skill_table" in p for p in H.problems(raw))


# ------------------------------------------------------------------------------------------------ the example
def test_the_example_validates_and_desugars():
    p = BLD.FieldProject.load(EXAMPLE)
    assert BLD.validate(p) == []
    assert [n["name"] for n in p.raw["npc"]] == ["bilba", "toy"]
    assert len(p.raw["choice"]) == 5 + 1 + 1                      # five objects, the ledger, the catalogue
    assert p.raw["behavior"]["unit"][0]["npc"] == "bilba"


def test_the_example_lints_without_false_positives():
    p = BLD.FieldProject.load(EXAMPLE)
    logic = BLD.lint_logic(p)
    assert not [w for w in logic if "no event sets it" in w], logic
    report = BLD.lint_all(p)
    assert not report.errors, report.errors


def test_the_example_builds(tmp_path):
    p = BLD.FieldProject.load(EXAMPLE)
    result = BLD.build_mod([p], tmp_path, mod_name="Household")
    assert any("FieldScene 4811 11 MANOR MANOR" in line for line in result["dictionary"])
    assert (tmp_path / "FF9_Data/embeddedasset/text/us/field/4811.mes").is_file()


# ------------------------------------------------------------------------------------------------ the Workspace tab
def test_the_behavior_tab_renders_a_household_read_only_and_names_the_owner():
    from ff9mapkit.workspace import behaviorscan as BS
    raw = tomllib.loads(EXAMPLE.read_text(encoding="utf-8"))          # the AUTHORED dict: no [behavior] yet
    assert not BS.has_behavior(raw)
    view, owner = BS.generated_view(raw)
    assert owner == "household" and BS.has_behavior(view)
    assert "behavior" not in raw                                      # the open dict was never touched
    assert BS.generated_view({**raw, "behavior": {"warmup": 1}}) is None   # a hand [behavior] is the author's
