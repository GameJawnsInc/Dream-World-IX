"""Battle-calc telemetry via the Scripts-DLL Overload channel (ff9mapkit battle-telemetry).

Offline tests pin the emitted C# (a plain STATIC feature class -- the IOverload* interfaces + transcribed
engine defaults live in the Overload HUB, tested in test_overload.py), the install/remove lifecycle
(compile mocked), and the JSONL parser/summarizer. A csc+install-gated test proves the rendered feature +
hub actually compile against the LIVE engine's managed DLLs.
"""
from __future__ import annotations

import json

import pytest

from ff9mapkit.battle import overload, scriptcompile, telemetry
from ff9mapkit.config import ModLayout


# ---- the emitted C# (no install) ---------------------------------------------------------------
def test_source_shape():
    src = telemetry.telemetry_source()
    # a plain static feature class: the hub owns the interfaces (one implementer per interface per DLL),
    # so the feature source must carry NO IOverload token (that's also what the collision gate scans for)
    assert "IOverload" not in src
    assert "public static class BattleTelemetry" in src
    for method in ("LogBattleInit()", "LogCalc(BattleCalculator v)",
                   "LogResult(BattleCalculator v)", "LogApplied(BattleCalculator v)"):
        assert method in src                                    # the hub's splice targets
    assert "namespace Memoria.Scripts.Telemetry" in src
    assert src.count("{") == src.count("}")                     # balanced (the .format brace-doubling survived)
    assert "{basename}" not in src and "{jsonl}" not in src     # every placeholder substituted
    assert telemetry.JSONL_BASENAME in src
    # every telemetry write is swallowed -- the feature must never break a battle
    assert src.count("catch { }") >= 4


def test_source_carries_no_engine_defaults():
    """The displaced engine defaults (backstab/kill-frozen, reflect, the DamageModifier pair) moved to the
    hub VERBATIM -- duplicating them here would run them twice. Pinned in test_overload.py instead."""
    src = telemetry.telemetry_source()
    assert "TryKillFrozen" not in src
    assert "GetReflectMultiplierOnTarget" not in src
    assert "v.Context.Attack" not in src


# ---- install / remove lifecycle (compile mocked; no install, no csc) ----------------------------
def _mock_compiles(monkeypatch):
    calls = []
    def fake(srcs, out_dll, *, game=None):
        calls.append(([str(s) for s in srcs], str(out_dll)))
        from pathlib import Path
        Path(out_dll).parent.mkdir(parents=True, exist_ok=True)
        Path(out_dll).write_bytes(b"MZ fake dll")
    monkeypatch.setattr(overload, "compile_sources", fake)      # the ONE compile path (overload.compile_tree)
    return calls


def test_install_writes_source_and_compiles_all(tmp_path, monkeypatch):
    calls = _mock_compiles(monkeypatch)
    mod = tmp_path / "FF9CustomMap"
    layout = ModLayout(root=mod)
    # a pre-existing minted battle formula must ride along into the SAME dll
    layout.scripts_sources_dir.mkdir(parents=True)
    (layout.scripts_sources_dir / "0256_XScript.cs").write_text("// formula", encoding="utf-8")
    dll = telemetry.install(mod)
    assert telemetry.installed(layout)
    srcs, out = calls[-1]
    assert any("0256_XScript.cs" in s for s in srcs) and any(telemetry.TELEMETRY_BASENAME in s for s in srcs)
    assert any(overload.HUB_BASENAME in s for s in srcs)        # the hub rides along (it owns the interfaces)
    assert out.endswith("Memoria.Scripts.FF9CustomMap.dll")     # DLL name derives from the FOLDER name
    assert str(dll) == out


def test_install_sources_survive_battle_wipe(tmp_path, monkeypatch):
    """The hook lives in Sources/Telemetry -- a SIBLING of Sources/Battle -- so the field build's
    write_scripts wipe (which owns Battle only) can't delete it."""
    _mock_compiles(monkeypatch)
    mod = tmp_path / "FF9CustomMap"
    layout = ModLayout(root=mod)
    telemetry.install(mod)
    import shutil
    shutil.rmtree(layout.scripts_sources_dir, ignore_errors=True)   # what write_scripts does
    assert telemetry.installed(layout)


def test_remove_recompiles_or_deletes(tmp_path, monkeypatch):
    calls = _mock_compiles(monkeypatch)
    mod = tmp_path / "FF9CustomMap"
    layout = ModLayout(root=mod)
    # case 1: other formulas remain -> recompile without the hook (and without the now-feature-less hub)
    layout.scripts_sources_dir.mkdir(parents=True)
    (layout.scripts_sources_dir / "0256_XScript.cs").write_text("// formula", encoding="utf-8")
    telemetry.install(mod)
    dll = telemetry.remove(mod)
    assert dll is not None and not telemetry.installed(layout)
    srcs, _ = calls[-1]
    assert not any(telemetry.TELEMETRY_BASENAME in s for s in srcs)
    assert not any(overload.HUB_BASENAME in s for s in srcs)    # no features -> no hub dir either
    # case 2: telemetry was the only content -> the DLL (+ stamp) is deleted outright
    (layout.scripts_sources_dir / "0256_XScript.cs").unlink()
    layout.scripts_sources_dir.rmdir()                          # an empty Battle dir also counts as "nothing"
    telemetry.install(mod)
    dll_path = layout.scripts_dll("FF9CustomMap")
    scriptcompile._stamp_path(dll_path).write_text("{}", encoding="utf-8")
    assert telemetry.remove(mod) is None
    assert not dll_path.exists() and not scriptcompile._stamp_path(dll_path).exists()


# ---- the read side: parser + summarizer --------------------------------------------------------
def _sample_events():
    z = {"id": 1, "name": "Zidane", "player": True, "lv": 5, "hp": 100, "maxhp": 105, "mp": 20, "maxmp": 24}
    g = {"id": 8, "name": "Goblin", "player": False, "lv": 1, "hp": 33, "maxhp": 33, "mp": 0, "maxmp": 0}
    return [
        {"e": "battle", "b": 1, "t": "2026-07-07T00:00:00Z", "field": 4003, "scene": 45, "units": [z, g]},
        {"e": "calc", "b": 1, "c": 1, "script": 1, "cmd": 1, "ability": "Attack", "power": 9,
         "caster": z, "target": g},
        {"e": "result", "b": 1, "c": 1, "hpDmg": 42, "mpDmg": 0, "flags": 1, "ctxFlags": 0,
         "crit": False, "heal": False},
        {"e": "applied", "b": 1, "c": 1, "hpDmg": 42, "mpDmg": 0, "tHp": 0, "flags": 1},
        # a miss: calc with no result/applied
        {"e": "calc", "b": 1, "c": 2, "script": 1, "cmd": 1, "ability": "Attack", "power": 9,
         "caster": g, "target": z},
    ]


def test_read_events_skips_malformed(tmp_path):
    p = tmp_path / "t.jsonl"
    lines = [json.dumps(e) for e in _sample_events()]
    lines.insert(2, '{"e":"calc","b":1,"c"')                    # a crash-truncated tail mid-file
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    events = telemetry.read_events(p)
    assert len(events) == len(_sample_events())


def test_join_and_summarize():
    rows = telemetry.join_calcs(_sample_events())
    assert len(rows) == 2
    assert rows[0]["result"]["hpDmg"] == 42 and rows[0]["applied"]["tHp"] == 0
    assert rows[1]["result"] is None                            # the miss
    text = telemetry.summarize(_sample_events())
    assert "battles: 1" in text and "calcs: 2" in text
    assert "Attack" in text and " 50%" in text                  # 1 hit / 2 casts
    assert "Zidane 42" in text                                  # damage dealt
    assert "Goblin 42" in text                                  # damage taken


def test_summarize_empty():
    assert "no telemetry events" in telemetry.summarize([])


def test_summarize_strips_ff9_text_tags():
    """Enemy names arrive as the engine's raw tagged string ([STRT=27,1]Fang[ENDN], seen in the first live
    capture) -- the REPORT strips the markup; the JSONL keeps the faithful raw."""
    assert telemetry.strip_text_tags("[STRT=27,1]Fang[ENDN]") == "Fang"
    events = _sample_events()
    events[4]["caster"] = dict(events[4]["caster"], name="[STRT=33,1]Goblin[ENDN]")
    events[4]["ability"] = "[STRT=69,1]Goblin Punch[ENDN]"
    text = telemetry.summarize(events)
    assert "Goblin Punch" in text and "[STRT" not in text


# ---- the money test: the rendered feature + hub compile against the LIVE engine (install + csc gated) ---
def test_hook_compiles_against_live_engine(tmp_path):
    if not scriptcompile.toolchain_available():
        pytest.skip("no C# compiler (csc) to build the hook DLL")
    try:
        scriptcompile._managed_dir(None)
    except Exception:
        pytest.skip("no FF9 install for the managed DLLs")
    # telemetry as it actually ships: the static feature class + the hub that implements the interfaces
    layout = ModLayout(root=tmp_path / "TelemetryProbe")
    cs = telemetry.telemetry_cs(layout)
    cs.parent.mkdir(parents=True)
    cs.write_text(telemetry.telemetry_source(), encoding="utf-8", newline="\n")
    out = overload.compile_tree(layout, "TelemetryProbe")
    assert out is not None and out.is_file() and out.stat().st_size > 0
