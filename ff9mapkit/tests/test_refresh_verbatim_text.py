"""``tools/refresh_verbatim_text.py`` -- rewrite a verbatim fork's stale us/uk text sidecar, and ONLY that defect.

Before master aa627d52 every verbatim fork's ``<NAME>.verbatim_mes.json`` held one English body as both us and uk,
and a re-deploy re-ships the sidecar unchanged. The tool rewrites a sidecar only when its difference from the donor
is exactly that mis-pick. Offline, against a fake donor text: the dry run writes nothing, ``--apply`` rewrites the
two defect directions in the import's exact format with a backup, a second run is all OK, a hand-edited sidecar is
refused unless ``--force``, and ``main`` refuses outright when the resource-path index can't be read. Against the
install: sidecars rebuilt in the old defect shape from real donor text (uk wrong in block 33, us wrong in block 47)
come back byte-identical to what a fresh import writes.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from ff9mapkit import dialogue
from ff9mapkit._fieldtext import EVENT_ID_TO_MES
from ff9mapkit.config import LANGS

REPO = Path(__file__).resolve().parents[2]
REAL = {L: f"[STRT=1,1]{L} donor text[ENDN]" for L in LANGS}   # a donor whose us and uk differ, like all 64


def _load():
    spec = importlib.util.spec_from_file_location("refresh_verbatim_text", REPO / "tools" / "refresh_verbatim_text.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


T = _load()


def _fork(root: Path, name: str, text: dict, donor=105) -> Path:
    """A verbatim fork project as `import --verbatim` writes it (the [verbatim_eb] lines verbatim); -> the sidecar."""
    d = root / name
    d.mkdir(parents=True)
    donor_line = f"donor = {donor}   # the real field this is forked from (for engine-hotfix warnings)\n" if donor else ""
    (d / f"{name}.field.toml").write_text(
        f'[verbatim_eb]\nbin = "{name}.verbatim_eb.bin"\n{donor_line}'
        f'text = "{name}.verbatim_mes.json"   # the donor field text (its index-txids resolve in)\n', encoding="utf-8")
    (d / f"{name}.verbatim_eb.bin").write_bytes(b"\x00EB")
    side = d / f"{name}.verbatim_mes.json"
    side.write_text(json.dumps(text), encoding="utf-8")
    return side


@pytest.fixture
def forks(tmp_path):
    return {
        "uk_wrong": _fork(tmp_path, "UK_WRONG", dict(REAL, uk=REAL["us"])),
        "us_wrong": _fork(tmp_path, "US_WRONG", dict(REAL, us=REAL["uk"])),
        "current": _fork(tmp_path, "CURRENT", dict(REAL)),
        "no_donor": _fork(tmp_path, "NO_DONOR", dict(REAL, uk=REAL["us"]), donor=None),
        "edited": _fork(tmp_path, "EDITED", dict(REAL, uk=REAL["us"], fr="[STRT=1,1]hand edit[ENDN]")),
    }


def _snapshot(root: Path) -> dict:
    return {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}


def _run(root, **kw):
    lines = []
    tally = T.refresh([root], extract=lambda donor: dict(REAL), out=lines.append, **kw)
    return tally, "\n".join(lines)


def test_classify_names_both_defect_directions_and_nothing_else():
    assert T.classify(dict(REAL), REAL)[0] == "ok"
    assert T.classify(dict(REAL, uk=REAL["us"]), REAL) == ("defect", "uk was the US text")
    assert T.classify(dict(REAL, us=REAL["uk"]), REAL) == ("defect", "us was the UK text")
    assert T.classify(dict(REAL, uk=REAL["us"], fr="x"), REAL)[0] == "unexplained"   # another language differs
    assert T.classify(dict(REAL, us="x", uk="x"), REAL)[0] == "unexplained"          # one body, but not the donor's
    assert T.classify({L: b for L, b in REAL.items() if L != "jp"}, REAL)[0] == "unexplained"   # a language missing


def test_dry_run_reports_every_fork_and_writes_nothing(tmp_path, forks):
    before = _snapshot(tmp_path)
    tally, log = _run(tmp_path)
    assert tally == {"fixed": 0, "would-fix": 2, "ok": 1, "refused": 1, "skipped": 1}
    assert _snapshot(tmp_path) == before
    assert "uk was the US text" in log and "us was the UK text" in log and "block 33" in log


def test_apply_rewrites_only_the_defect_in_the_import_format_with_a_backup(tmp_path, forks):
    before = _snapshot(tmp_path)
    tally, _ = _run(tmp_path, apply=True)
    assert tally == {"fixed": 2, "would-fix": 0, "ok": 1, "refused": 1, "skipped": 1}
    for k in ("uk_wrong", "us_wrong"):
        side = forks[k]
        assert side.read_text(encoding="utf-8") == json.dumps(REAL)          # exactly what the import writes
        (bak,) = side.parent.glob(f"{side.name}.pre-refresh-*")
        assert bak.read_bytes() == before[side]
    after = _snapshot(tmp_path)
    untouched = [p for p in before if p not in (forks["uk_wrong"], forks["us_wrong"])]
    assert all(after[p] == before[p] for p in untouched)                    # tomls, .eb bins, the other sidecars
    assert len(after) == len(before) + 2                                     # the two backups, nothing else
    tally, _ = _run(tmp_path, apply=True)                                    # idempotent: nothing left to fix
    assert tally["fixed"] == 0 and tally["ok"] == 3 and _snapshot(tmp_path) == after


def test_force_rewrites_a_sidecar_the_defect_does_not_explain(tmp_path, forks):
    tally, log = _run(tmp_path, apply=True)
    assert "REFUSE" in log and forks["edited"].read_text(encoding="utf-8") != json.dumps(REAL)
    tally, _ = _run(tmp_path, apply=True, force=True)
    assert tally["fixed"] == 1 and forks["edited"].read_text(encoding="utf-8") == json.dumps(REAL)


def test_main_writes_nothing_when_the_resource_index_is_unreadable(tmp_path, forks, monkeypatch):
    """Without the engine's path index the text would be re-guessed from content -- the very defect -- so main()
    stops before checking anything."""
    monkeypatch.setattr(T.dialogue, "_mes_path_index", lambda game=None: None)
    before = _snapshot(tmp_path)
    assert T.main([str(tmp_path), "--apply"]) == 2
    assert _snapshot(tmp_path) == before


def _index_ready():
    try:
        import UnityPy  # noqa: F401
        return dialogue._mes_path_index() is not None
    except Exception:                                  # noqa: BLE001 -- no install / no UnityPy
        return False


@pytest.mark.skipif(not _index_ready(), reason="needs the FF9 install + UnityPy")
def test_real_donor_sidecars_in_the_defect_shape_come_back_as_a_fresh_import(tmp_path, capsys):
    """Donor 105 (block 33, where uk got the US copy) and 351 (block 47, where us got the UK copy), each rebuilt in
    the shape the old kit wrote: main() --apply returns them to exactly what `import --verbatim` now writes."""
    assert (EVENT_ID_TO_MES[105], EVENT_ID_TO_MES[351]) == (33, 47)
    real = {d: dialogue.extract_field_mes_all_langs(d) for d in (105, 351)}
    assert all(r["us"] != r["uk"] for r in real.values())
    sides = {105: _fork(tmp_path, "ALEX", dict(real[105], uk=real[105]["us"]), donor=105),
             351: _fork(tmp_path, "DALI", dict(real[351], us=real[351]["uk"]), donor=351)}
    assert T.main([str(tmp_path), "--apply"]) == 0
    log = capsys.readouterr().out
    assert "uk was the US text" in log and "us was the UK text" in log
    for d, side in sides.items():
        assert side.read_text(encoding="utf-8") == json.dumps(real[d])
