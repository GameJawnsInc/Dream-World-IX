"""[ff9mapkit netsync s167] THE WALK-ON ENTRANCE: ``world-entrance --field-direct`` warns when it writes an auto-warp body
into a co-op walk world (WORLD02 / WORLD10 / WORLD11).

On those world maps a following co-op guest walks its own copy free (S166-DESIGN.md decisions 13-14), and the engine
refuses the guest's entrances at the Confirm READ (decision 18's EntryRefusalRule, decision 19's kit-cell close). An
auto-warp body reads no key, so a free guest who steps on it enters the field alone (the s167 whole-diff review,
W3A-SAFE-1). The confirm-gated forms (--action-prompt, --nameplate-name) read Confirm and stay quiet, as does the
dispatcher-case route (--field / --case), and so does an auto-warp written only into non-walk worlds.
"""
from __future__ import annotations

import pytest

WARN = "!! CO-OP WARNING"


def _fake(written):
    def fake(**kw):
        return {"tag_hex": "0x0000", "field": kw.get("direct_field") or 300, "dry_run": True, "cell": (19, 21),
                "case": 4, "dest_note": "", "dispatchers_written": [{"name": n, "base_len": 0} for n in written],
                "dispatchers_skipped": [], "langs": ["us"], "tiles_set": 3, "block": (9, 10), "event": 1,
                "backups": [], "tile_area": [14], "tile_area_mode": "host",
                "tile_area_host": {"area": 14, "source": "ring", "votes": {14: 9}}}
    return fake


def _run(monkeypatch, capsys, written, flags):
    from ff9mapkit import cli
    from ff9mapkit.world import entrance as EN
    monkeypatch.setattr(EN, "author_entrance", _fake(written))
    rc = cli.main(["world-entrance", "--cell", "19", "21", "--mod-folder", "X", "--dry-run", *flags])
    return rc, capsys.readouterr().out


def test_the_walk_set_is_the_engines():
    from ff9mapkit import cli
    assert cli.COOP_WALK_WORLDS == (9002, 9010, 9011)


def test_an_auto_warp_on_a_walk_world_warns_naming_the_worlds(monkeypatch, capsys):
    rc, out = _run(monkeypatch, capsys, ["evt_world_01", "evt_world_02", "evt_world_10", "evt_world_11"],
                   ["--field-direct", "6610"])
    assert rc == 0
    assert WARN in out
    line = next(ln for ln in out.splitlines() if WARN in ln)
    assert "9002, 9010, 9011" in line and "9001" not in line
    assert "field 6610 ALONE" in line and "--action-prompt" in line


@pytest.mark.parametrize("written, want", [(["evt_world_11"], "9011"), (["evt_world_02", "evt_world_04"], "9002")])
def test_one_walk_world_is_enough(written, want, monkeypatch, capsys):
    rc, out = _run(monkeypatch, capsys, written, ["--field-direct", "6610"])
    assert rc == 0
    line = next(ln for ln in out.splitlines() if WARN in ln)
    assert want in line


@pytest.mark.parametrize("flags", [["--field-direct", "6610", "--action-prompt"],
                                   ["--field-direct", "6610", "--action-prompt", "--nameplate"],
                                   ["--field-direct", "6610", "--nameplate-name", "Somewhere"],
                                   ["--field", "300"], ["--case", "4"]])
def test_a_confirm_gated_or_dispatcher_entrance_is_quiet(flags, monkeypatch, capsys):
    rc, out = _run(monkeypatch, capsys, ["evt_world_02", "evt_world_10", "evt_world_11"], flags)
    assert rc == 0
    assert WARN not in out


def test_an_auto_warp_off_the_walk_set_is_quiet(monkeypatch, capsys):
    rc, out = _run(monkeypatch, capsys, ["evt_world_01", "evt_world_03", "evt_world_04", "evt_world_05"],
                   ["--field-direct", "6610"])
    assert rc == 0
    assert WARN not in out
