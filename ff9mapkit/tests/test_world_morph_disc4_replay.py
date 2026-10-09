"""THE DISC-4 REPLAY FOR IN-PLACE COAST MORPHS (terrain study O2, recommendation 4).

A coast morph's tweaks are built from one disc's bytes, so where disc 4's real cell differs the mirror cannot copy the
edit: before this, the edit stayed on disc 1 and disc 4 kept its stock coast with one SKIP line. Now
``world-transplant --in-place`` hands the mirror a replay -- the same command on disc 4, every morph rebuilt from disc
4's own bytes through the same gates -- and a dry run says what disc 4 will do.
"""
from __future__ import annotations

import warnings
from pathlib import Path

import pytest

from ff9mapkit import cli, config
from ff9mapkit.world import coastmorph as CM, discmirror as DM, extract as X, mesh as M, transplant as TR

BUMP = ["--cliff-bump", "1,2:3,4:2.5"]


def _args(*extra):
    return cli.build_parser().parse_args(["world-transplant", "--mod-folder", "MOD", "--in-place", "--cell", "2,7",
                                          "--donor", "2,7", *BUMP, *extra])


class _Lift:
    """Raise the terrain vertex at local (24, 24) by 1u."""
    part = "terrain"

    @staticmethod
    def _at(v):
        return abs(v[0][0] - 152.0) < 1e-6 and abs(v[0][2] + 472.0) < 1e-6

    def apply(self, part, poly):
        if part != "terrain" or not any(self._at(v) for v in poly):
            return poly
        return [((v[0][0], v[0][1] + 1.0, v[0][2]), *v[1:]) if self._at(v) else v for v in poly]

    def emit(self):
        return []

    def gate(self):
        return {"gate": "lift", "ok": True}


def _soup():
    idall = float(X.encode_id(topograph=20, area=14))

    def v(x, z):
        return ((128.0 + x, 3.0, -448.0 - z), (0.0, 1.0, 0.0), (0.1, 0.6), (idall, 0.0, 0.0, 1.0))
    return [[v(20, 20), v(24, 20), v(20, 24)], [v(24, 20), v(24, 24), v(20, 24)]]


def test_morph_in_place_hands_its_replay_to_the_mirror(monkeypatch):
    soup = _soup()
    monkeypatch.setattr(TR, "world_tris_stacked",
                        lambda mod, bx, by, p, **k: ((soup if p == "terrain" else []), None))
    monkeypatch.setattr(TR, "world_tris", lambda bx, by, p, **k: soup if p == "terrain" else [])
    monkeypatch.setattr(M, "deploy_override", lambda bm, **k: Path(f"x/{bm.name}"))
    seen = {}
    monkeypatch.setattr(DM, "auto_mirror", lambda written, **k: seen.update(k, written=list(written)))

    def hook(d):
        return None
    s = TR.morph_in_place("MOD", cell=(2, 7), tweaks=[_Lift()], replay=hook)
    assert s["clean"] and s["touched"] == ["terrain"]
    assert seen["replay"] is hook and seen["skip_mirror"] is False and len(seen["written"]) == 1


def test_the_cli_replays_the_whole_morph_on_disc4(monkeypatch):
    """The replay re-runs the command with --disc 4: the builders read disc 4's bytes, the morph runs on disc 4, and
    that call's own mirror is the silent REPLAY no-op. A refusal there raises, so the mirror leaves disc 4 alone."""
    built, runs = [], []
    monkeypatch.setattr(CM, "cliff_bump", lambda donor, p0, p1, depth, **k: built.append((donor, p0, p1, depth,
                                                                                         k["disc"])) or [_Lift()])

    def morph(mod, **k):
        runs.append(k)
        return {"op": "morph-in-place", "cell": list(k["cell"]), "touched": ["terrain"], "gates": [],
                "clean": True, "dry_run": k["dry_run"], "deployed": []}
    monkeypatch.setattr(TR, "morph_in_place", morph)
    assert cli._cmd_world_transplant(_args()) == 0
    assert runs[0]["disc"] == 1 and runs[0]["skip_mirror"] is False and built[0][-1] == 1
    runs[0]["replay"](4)
    assert built[1] == ((2, 7), (1.0, 2.0), (3.0, 4.0), 2.5, 4)
    assert runs[1]["disc"] == 4 and runs[1]["skip_mirror"] == DM.REPLAY and runs[1]["cell"] == (2, 7)
    assert runs[1]["dry_run"] is False

    def refuse(donor, p0, p1, depth, **k):
        if k["disc"] == 4:
            raise ValueError("start/end are not on one connected cliff-base run")
        return [_Lift()]
    monkeypatch.setattr(CM, "cliff_bump", refuse)
    with pytest.raises(ValueError, match="--disc 4 refused the same morph"):
        runs[0]["replay"](4)


@pytest.fixture
def dry(monkeypatch):
    """A dry-run world: cliff_bump refuses on disc 4 when ``state['refuse4']``; ``copy_refusal`` returns
    ``state['why']``."""
    state = {"why": None, "refuse4": False, "asked": [], "runs": []}

    def bump(donor, p0, p1, depth, **k):
        if k["disc"] == 4 and state["refuse4"]:
            raise ValueError("depth 2.5 folds a tile at the waterline")
        return [_Lift()]
    monkeypatch.setattr(CM, "cliff_bump", bump)

    def morph(mod, **k):
        state["runs"].append(k)
        return {"op": "morph-in-place", "cell": list(k["cell"]), "touched": ["terrain"],
                "gates": [{"gate": "lift", "ok": True}], "clean": True, "dry_run": k["dry_run"], "deployed": []}
    monkeypatch.setattr(TR, "morph_in_place", morph)
    monkeypatch.setattr(DM, "copy_refusal", lambda blk, **k: state["asked"].append((blk, k)) or state["why"])
    return state


def test_a_dry_run_says_disc4_copies_an_identical_cell(dry, capsys):
    assert cli._cmd_world_transplant(_args("--dry-run")) == 0
    out = capsys.readouterr().out
    assert "disc 4: the deploy copies this edit there" in out
    assert dry["asked"] == [((2, 7), {"src_disc": 1, "dst_disc": 4, "game": None})]
    assert [r["disc"] for r in dry["runs"]] == [1]                      # nothing to replay


def test_a_dry_run_replays_on_a_cell_disc4_changed(dry, capsys):
    dry["why"] = "real cell differs across discs in ['terrain']"
    assert cli._cmd_world_transplant(_args("--dry-run")) == 0
    out = capsys.readouterr().out
    assert "disc 4: real cell differs across discs in ['terrain'] -- the deploy re-runs this morph" in out
    assert "disc 4: the replay passes its gates -- the deploy edits both discs" in out
    assert [(r["disc"], r["dry_run"]) for r in dry["runs"]] == [(1, True), (4, True)]
    assert dry["runs"][1]["skip_mirror"] == DM.REPLAY
    assert out.count("dry run: ") == 1                                  # the disc-4 run prints no deploy hint


def test_a_dry_run_names_a_coast_disc4_cannot_take(dry, capsys):
    dry["why"], dry["refuse4"] = "real cell differs across discs in ['sea3', 'terrain']", True
    assert cli._cmd_world_transplant(_args("--dry-run")) == 0             # disc 1's own verdict is clean
    cap = capsys.readouterr()
    assert "the replay REFUSES there (above) -- the deploy edits disc 1 only" in cap.out
    assert "folds a tile at the waterline" in cap.err


def test_no_disc4_preview_when_skipped_or_on_disc4(dry, capsys):
    dry["why"] = "real cell differs"
    assert cli._cmd_world_transplant(_args("--dry-run", "--skip-mirror")) == 0
    assert cli._cmd_world_transplant(_args("--dry-run", "--disc", "4")) == 0
    assert "disc 4:" not in capsys.readouterr().out and dry["asked"] == []


def test_copy_refusal_reads_both_discs(monkeypatch):
    parts = {1: {(2, 7): {"terrain", "sea4"}}, 4: {(2, 7): {"terrain", "sea4"}, (3, 7): {"terrain"}}}
    monkeypatch.setattr(DM, "_real_parts", lambda disc, lod="0_1", **k: parts[disc])
    monkeypatch.setattr(DM, "_parts_identical", lambda blk, pt, *a, **k: pt != "terrain")
    assert DM.copy_refusal((2, 7)) == "real cell differs across discs in ['terrain']"
    assert DM.copy_refusal((3, 7)) == "real cell part sets differ across discs ([] vs ['terrain'])"
    assert DM.copy_refusal((9, 9)) is None                                # open sea on disc 4: copied


def _need_install() -> None:
    try:
        import UnityPy  # noqa: F401
        ok = (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        ok = False
    if not ok:
        warnings.warn("the disc-4 morph replay went unchecked on real data in this run: no FF9 install + UnityPy. "
                      "Re-run in the MAIN repo (C:/gd/Dream-World-IX/ff9mapkit).", UserWarning)
        pytest.skip("needs the FF9 install + UnityPy (see the warnings summary)")


@pytest.mark.parametrize("cell,spec,verdict", [
    ((2, 7), "174.76953125,-512.0:179.55859375,-448.0:2.5", "the replay passes its gates"),
    ((13, 3), "852.890625,-216.2109375:896.0,-236.34375:2.5", "!! the replay REFUSES there"),
])
def test_real_cliff_bump_on_a_cell_disc4_redrew(cell, spec, verdict, capsys):
    """Two of the terrain study's 129 coastal cells disc 4 redrew (s7_morph_replay.py): (2,7)'s bump replays on disc
    4's own coast; on (13,3) the same depth folds a tile at disc 4's waterline. Dry runs only: nothing is written."""
    _need_install()
    c = f"{cell[0]},{cell[1]}"
    args = cli.build_parser().parse_args(["world-transplant", "--mod-folder", "FF9CustomMap_test_nonexistent",
                                          "--in-place", "--cell", c, "--donor", c, "--cliff-bump", spec, "--dry-run"])
    assert cli._cmd_world_transplant(args) == 0
    out = capsys.readouterr().out
    assert "disc 4: real cell differs across discs in" in out and f"disc 4: {verdict}" in out
