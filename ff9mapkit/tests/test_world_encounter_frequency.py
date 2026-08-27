"""Overworld ENCOUNTER-FREQUENCY authoring (world/encounter.py) -- retune the per-ZONE ENCRATE ladder.

The lever this file covers is the ORDINARY overworld encounter rate: the `SetRandomBattleFrequency` (0x57)
ladder each free-roam dispatcher switches on GET-sysvar 207 (the zone), which feeds `ProcessEncount`'s step
accumulator. Its sibling `test_world_encounter_rate.py` covers the OTHER lever in the same module --
`w_frameEventBattleProb`, which only moves the Ragtime Mouse. The two were conflated for a year; keeping the
suites apart keeps the distinction visible.

Hermetic core: the quadratic frequency math (incl. a seeded simulation that pins WHY it is quadratic), mode
and zone validation, the structure gate that refuses a non-shipping ladder, and the in-place byte rewrite over
an assembled minimal `.eb`. Game-gated: the real dispatchers carry exactly the shipping ladder.
"""
from __future__ import annotations

import random

import pytest

from ff9mapkit import config
from ff9mapkit.eb.ebsrc import assemble_source
from ff9mapkit.world import encounter as EC

STOCK = [12, 16, 11, 14, 16, 14, 16, 14, 16, 16, 24, 12, 16, 16, 16, 11, 16, 16, 16, 14, 16, 16, 16, 32, 16]


def _game_ready() -> bool:
    try:
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


def _ladder_eb(vals=STOCK, *, selector: int = EC.SYSVAR_ZONE, var: str = "Instance.Byte[0]",
               arm_var: "str | None" = None, immediate: "int | None" = None) -> bytes:
    """Assemble a minimal dispatcher-shaped `.eb`: one function holding a `SWITCH` on GET-sysvar *selector*
    whose arms each write `var = const(v)`, then one `SetRandomBattleFrequency({var})`. The knobs exist so a
    test can build a DEFORMED ladder (wrong selector / wrong arm variable / wrong arm count) and assert the
    structure gate refuses it. *immediate* appends a second, literal `SetRandomBattleFrequency(N)` site."""
    arm_var = arm_var or var
    lines = [".ebs 1", ".name " + "00" * 124, ".entry 0 type=0 loc=0 flags=0", ".func 1", "L0:",
             f"SET({{B_SYSVAR[{selector}] B_EXPR_END}})",
             "SWITCH(0, LEND, " + ", ".join(f"LZ{i}" for i in range(len(vals))) + ")"]
    for i, v in enumerate(vals):
        lines += [f"LZ{i}:", f"SET({{{arm_var} const({v}) B_LET B_EXPR_END}})", "JMP(LEND)"]
    lines += ["LEND:", f"SetRandomBattleFrequency({{{var} B_EXPR_END}})"]
    if immediate is not None:
        lines.append(f"SetRandomBattleFrequency({immediate})")
    lines.append("RET()")
    return assemble_source("\n".join(lines) + "\n")


def _zone_map(data: bytes) -> dict:
    return {w["zone"]: w["value"] for w in EC.freq_writes(data) if w["kind"] == "zone"}


# --------------------------------------------------------------------------- the frequency math (hermetic)

def test_transform_freq_multiplier_is_quadratic():
    # frequency scales as sqrt(encratio), so the verb applies M**2
    assert EC.transform_freq(16, multiplier=2.0) == 64
    assert EC.transform_freq(16, multiplier=0.5) == 4
    assert EC.transform_freq(12, multiplier=2.0) == 48
    assert EC.transform_freq(32, multiplier=1.0) == 32          # identity
    assert EC.transform_freq(11, multiplier=1.5) == 25          # round(11 * 2.25)


def test_transform_freq_clamps_to_the_byte_and_never_silently_disables():
    """encratio is a Byte in BOTH the ladder target and the opcode cast, so 256 truncates to 0 = encounters
    OFF. A clamp -- not a wrap -- is the whole safety property here."""
    assert EC.transform_freq(16, set_freq=300) == EC.FREQ_MAX == 255
    assert EC.transform_freq(16, set_freq=-5) == 0
    assert EC.transform_freq(255, multiplier=100.0) == 255      # clamps, does not wrap to a small value
    assert EC.transform_freq(64, multiplier=2.0) == 255         # 256 would truncate to 0; clamp catches it
    # a tiny multiplier floors at 1 -- "very rare", never an accidental total disable
    assert EC.transform_freq(11, multiplier=0.001) == 1
    assert EC.transform_freq(11, multiplier=0.1) == 1
    # only `peaceful` means zero, and it means it
    assert EC.transform_freq(32, peaceful=True) == 0


def test_transform_freq_rejects_bad_modes():
    with pytest.raises(ValueError, match="give exactly one of multiplier / set_freq / peaceful"):
        EC.transform_freq(16)                                   # no mode
    # the three below must all fail on the VALUE, never fall through to the no-mode guard above
    for bad in (0, -2, True):                                   # 0 / negative / bool-is-not-a-number
        with pytest.raises(ValueError, match="multiplier must be a positive number"):
            EC.transform_freq(16, multiplier=bad)
    for kw in ({"multiplier": 2.0, "set_freq": 20}, {}, {"multiplier": 2.0, "peaceful": True}):
        with pytest.raises(ValueError):
            EC._validate_freq_mode(kw.get("multiplier"), kw.get("set_freq"), kw.get("peaceful", False))


def test_the_quadratic_law_matches_a_simulation_of_processencount():
    """Pin WHY transform_freq squares the multiplier. Replays the engine's accumulator
    (`_encountBase += encratio`; battle when `random8() < _encountBase >> 3`, then reset) and checks that
    `encratio * M**2` really delivers frequency M. Seeded, so this is deterministic."""
    def mean_ticks(encratio, trials=4000, seed=99):
        rng = random.Random(seed)
        total = base = n = 0
        for _ in range(trials):
            while True:
                base += encratio
                n += 1
                if rng.randrange(256) < (base >> 3):
                    total += n
                    base = n = 0
                    break
        return total / trials

    ref = mean_ticks(16)
    for m in (0.5, 2.0):
        got = ref / mean_ticks(EC.transform_freq(16, multiplier=m))
        assert abs(got - m) / m < 0.12, f"multiplier {m} delivered {got:.3f}x"
    # and the relationship really is non-linear: a LINEAR scale would badly overshoot
    linear = ref / mean_ticks(32)                                # 16*2, the naive reading
    assert linear < 1.6, f"linear scaling gave {linear:.3f}x -- would not be 2x"


# --------------------------------------------------------------------------- locating the ladder (hermetic)

def test_freq_writes_finds_every_zone_arm_and_the_immediate():
    data = _ladder_eb(immediate=11)
    ws = list(EC.freq_writes(data))
    assert len(ws) == EC.ZONE_COUNT + 1
    assert _zone_map(data) == dict(enumerate(STOCK))
    imm = [w for w in ws if w["kind"] == "immediate"]
    assert len(imm) == 1 and imm[0]["value"] == 11 and imm[0]["zone"] is None and imm[0]["width"] == 1
    # every reported (off, width) really holds the reported value -- no silent wrong offset
    for w in ws:
        assert int.from_bytes(data[w["off"]:w["off"] + w["width"]], "little") == w["value"]


@pytest.mark.parametrize("kwargs, why", [
    ({"selector": 193}, r"switch selector is .*, not B_SYSVAR\[207\] \(the zone\)"),
    ({"arm_var": "Map.Byte[7]"}, r"zone \d+ arm is .*, not a single `.*` write"),
    ({"vals": [12, 16, 11]}, r"ladder has 3 arms, expected 25"),
])
def test_structure_gate_refuses_a_deformed_ladder(kwargs, why):
    """A rule that is not enforced at the call site is not enforced. A dispatcher some other tool has
    restructured must RAISE, not be silently mis-patched -- and must raise for THE DEFORMATION IT WAS
    HANDED. ``why`` was documentation until it became the match: the gate has eight distinct refusals
    sharing one exception class, so a bare raises() passed even if every case tripped the same one."""
    with pytest.raises(EC.EncrateStructureError, match=why):
        list(EC.freq_writes(_ladder_eb(**kwargs)))


# --------------------------------------------------------------------------- the rewrite (hermetic)

def test_apply_rewrites_in_place_and_round_trips():
    data = _ladder_eb(immediate=11)
    out, changes = EC.apply_encounter_frequency(data, pristine=data, multiplier=2.0)
    assert len(out) == len(data)                                 # length-preserving: offsets survive
    assert len(changes) == EC.ZONE_COUNT + 1
    assert _zone_map(out) == {z: v * 4 for z, v in enumerate(STOCK)}
    assert [w["value"] for w in EC.freq_writes(out) if w["kind"] == "immediate"] == [44]


def test_multiplier_is_idempotent_via_pristine():
    data = _ladder_eb()
    once, _ = EC.apply_encounter_frequency(data, pristine=data, multiplier=2.0)
    twice, _ = EC.apply_encounter_frequency(once, pristine=data, multiplier=2.0)
    assert twice == once                                         # derives from pristine, so it does not compound
    compounded, _ = EC.apply_encounter_frequency(once, multiplier=2.0)
    assert compounded != once                                    # ...but without pristine it does


def test_set_and_peaceful_apply_everywhere():
    data = _ladder_eb(immediate=11)
    out, _ = EC.apply_encounter_frequency(data, set_freq=200)
    assert set(_zone_map(out).values()) == {200}
    off, _ = EC.apply_encounter_frequency(data, peaceful=True)
    assert set(_zone_map(off).values()) == {0}
    assert [w["value"] for w in EC.freq_writes(off) if w["kind"] == "immediate"] == [0]


def test_zone_targeting_touches_only_that_arm():
    data = _ladder_eb(immediate=11)
    out, changes = EC.apply_encounter_frequency(data, pristine=data, zones=[6], set_freq=64)
    assert len(changes) == 1 and changes[0]["zone"] == 6
    after = _zone_map(out)
    assert after[6] == 64
    assert {z: v for z, v in after.items() if z != 6} == {z: v for z, v in enumerate(STOCK) if z != 6}
    # the standalone immediate carries no zone, so a zone-scoped edit must leave it alone
    assert [w["value"] for w in EC.freq_writes(out) if w["kind"] == "immediate"] == [11]


def test_zone_out_of_range_is_rejected():
    data = _ladder_eb()
    for bad in ([EC.ZONE_COUNT], [-1], [3, 99]):
        with pytest.raises(ValueError, match="out of range"):
            EC.apply_encounter_frequency(data, zones=bad, set_freq=20)


# --------------------------------------------------------------------------- the real dispatchers (gated)

@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_real_dispatchers_carry_the_shipping_ladder():
    from ff9mapkit.world import entrance as E
    alld = E.load_all_dispatchers()
    free_roam = {f"evt_world_world{n:02d}" for n in (0, 2, 3, 5, 7, 8, 9, 10, 11)}
    cutscene = {f"evt_world_world{n:02d}" for n in (1, 4, 6, 12)}
    for name in cutscene:
        assert list(EC.freq_writes(alld[name]["us"])) == [], f"{name} (cutscene) should carry no ENCRATE"
    immediates = 0
    for name in free_roam:
        for lang, data in alld[name].items():                    # EVERY language ships the SAME vector
            assert _zone_map(data) == dict(enumerate(STOCK)), f"{name}/{lang}"
            immediates += sum(1 for w in EC.freq_writes(data) if w["kind"] == "immediate")
    # WORLD05 alone carries a standalone immediate (entry 15 tag 1), in each of the 7 languages
    assert immediates == len(EC.LANGS)
    assert sum(1 for w in EC.freq_writes(alld["evt_world_world05"]["us"])
               if w["kind"] == "immediate") == 1


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_real_dispatcher_rewrite_is_length_preserving_and_rereads():
    from ff9mapkit.world import entrance as E
    data = E.load_all_dispatchers()["evt_world_world00"]["us"]
    out, changes = EC.apply_encounter_frequency(data, pristine=data, multiplier=2.0)
    assert len(out) == len(data) and len(changes) == EC.ZONE_COUNT
    assert _zone_map(out) == {z: v * 4 for z, v in enumerate(STOCK)}
    assert sum(1 for a, b in zip(data, out) if a != b) > 0


def test_deploy_writes_per_language_eb_that_rereads(tmp_path, monkeypatch):
    """Hermetic: stub the dispatcher SOURCE with synthetic `.eb` (a free-roam state with a ladder + a cutscene
    state without), redirect the mod-folder DESTINATION to tmp, and confirm deploy lands per-language
    `.eb.bytes` that re-read with the retuned frequency, skipping the ENCRATE-less state."""
    from pathlib import Path
    from ff9mapkit.world import entrance as E
    bare = assemble_source(".ebs 1\n.name " + "00" * 124 + "\n.entry 0 type=0 loc=0 flags=0\n.func 1\nRET()\n")
    synth = {
        "evt_world_world00": {"us": _ladder_eb(), "jp": _ladder_eb()},
        "evt_world_world01": {"us": bare, "jp": bare},                     # cutscene: no ENCRATE at all
    }
    monkeypatch.setattr(E, "load_all_dispatchers", lambda game=None: synth)
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    summary = EC.deploy_encounter_frequency(mod_folder="FF9CustomMap", multiplier=2.0, langs=["us", "jp"])
    assert not summary["dry_run"] and summary["written"]
    assert summary["skipped_no_writes"] == ["evt_world_world01"]
    seen_langs, seen_names = set(), set()
    for p in summary["written"]:
        pp = Path(p)
        seen_langs.add(pp.parent.name)
        seen_names.add(pp.name)
        assert pp.relative_to(tmp_path).parts[0] == "FF9CustomMap"          # landed in the mod folder
        assert _zone_map(pp.read_bytes()) == {z: v * 4 for z, v in enumerate(STOCK)}
    assert seen_langs == {"us", "jp"} and seen_names == {"EVT_WORLD_WORLD00.eb.bytes"}
    # idempotent redeploy: re-running reads the scaled override but derives from pristine -> same bytes
    live = tmp_path / "FF9CustomMap" / EC._WORLD_EB_SUBDIR / "us" / "EVT_WORLD_WORLD00.eb.bytes"
    before = live.read_bytes()
    EC.deploy_encounter_frequency(mod_folder="FF9CustomMap", multiplier=2.0, langs=["us", "jp"])
    assert live.read_bytes() == before


def test_deploy_dry_run_writes_nothing(tmp_path, monkeypatch):
    from ff9mapkit.world import entrance as E
    monkeypatch.setattr(E, "load_all_dispatchers",
                        lambda game=None: {"evt_world_world00": {"us": _ladder_eb()}})
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    summary = EC.deploy_encounter_frequency(mod_folder="FF9CustomMap", multiplier=2.0,
                                            langs=["us"], dry_run=True)
    assert summary["dry_run"] and summary["dispatchers"]
    assert not (tmp_path / "FF9CustomMap" / EC._WORLD_EB_SUBDIR).exists()
# --------------------------------------------------------------------------- the CLI surface

def _stub_cli(monkeypatch, tmp_path, ladder=None):
    """Point the CLI verb at a synthetic dispatcher set and a tmp game root."""
    from ff9mapkit.world import entrance as E
    monkeypatch.setattr(E, "load_all_dispatchers",
                        lambda game=None: {"evt_world_world00": {"us": ladder or _ladder_eb()}})
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)


def test_cli_list_without_a_mod_folder(monkeypatch, tmp_path, capsys):
    from ff9mapkit import cli
    _stub_cli(monkeypatch, tmp_path)
    assert cli.main(["world-encounter-frequency", "--list"]) == 0
    out = capsys.readouterr().out
    assert "per-ZONE ENCRATE ladder" in out
    for z, v in enumerate(STOCK):                                   # every zone row is printed
        assert f"{z:4d}  {v:8d}" in out
    assert "[14]" in out                                            # zone 6's areas, the kit's safe-road stamp


def test_cli_list_reads_a_deployed_override(monkeypatch, tmp_path, capsys):
    """The --mod-folder branch of --list resolves the mod root and reads the deployed .eb. It regressed once
    on a NameError that no library test could catch, so it gets its own CLI-level test."""
    from ff9mapkit import cli
    _stub_cli(monkeypatch, tmp_path)
    live = tmp_path / "FF9CustomMap" / EC._WORLD_EB_SUBDIR / "us" / "EVT_WORLD_WORLD00.eb.bytes"
    live.parent.mkdir(parents=True, exist_ok=True)
    retuned, _ = EC.apply_encounter_frequency(_ladder_eb(), pristine=_ladder_eb(), multiplier=2.0)
    live.write_bytes(retuned)
    assert cli.main(["world-encounter-frequency", "--list", "--mod-folder", "FF9CustomMap"]) == 0
    out = capsys.readouterr().out
    assert "showing the DEPLOYED override" in out
    assert "2.00x" in out                                           # 4x the value reads back as 2x frequency
    assert f"{0:4d}  {STOCK[0] * 4:8d}" in out


def test_cli_deploy_dry_run_and_errors(monkeypatch, tmp_path, capsys):
    from ff9mapkit import cli
    _stub_cli(monkeypatch, tmp_path)
    rc = cli.main(["world-encounter-frequency", "--mod-folder", "FF9CustomMap",
                   "--multiplier", "2.0", "--dry-run"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "would retune the ORDINARY overworld encounter rate" in out and "all zones" in out
    assert not (tmp_path / "FF9CustomMap" / EC._WORLD_EB_SUBDIR).exists()
    # zone scoping is reflected in the banner
    assert cli.main(["world-encounter-frequency", "--mod-folder", "FF9CustomMap",
                     "--zone", "6", "--set", "64", "--dry-run"]) == 0
    assert "zone(s) 6" in capsys.readouterr().out
    # no mode -> refused
    assert cli.main(["world-encounter-frequency", "--mod-folder", "FF9CustomMap", "--dry-run"]) == 2
    assert "exactly one of" in capsys.readouterr().err
    # a mode but no destination -> refused
    assert cli.main(["world-encounter-frequency", "--multiplier", "2.0"]) == 2
    assert "--mod-folder is required" in capsys.readouterr().err
    # an out-of-range zone -> refused, not clamped
    assert cli.main(["world-encounter-frequency", "--mod-folder", "FF9CustomMap",
                     "--zone", "99", "--set", "10", "--dry-run"]) == 2
    assert "out of range" in capsys.readouterr().err
