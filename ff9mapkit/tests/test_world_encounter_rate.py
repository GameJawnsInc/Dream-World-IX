"""Overworld ENCOUNTER-RATE authoring (world/encounter.py) -- retune RunWorldCode(26) rate writes.

Hermetic core: the rate math (transform_prob), mode validation, and the in-place byte rewrite over a
hand-built minimal .eb (find SET-26 -> rewrite the v2 immediate -> round-trips, length-preserving, idempotent
vs a pristine source). Game-gated: the real 13 dispatchers carry exactly the shipping 18 writes / two danger
values, and deploy lands per-language .eb.bytes that re-read with the new rate.
"""
from __future__ import annotations

import pytest

from ff9mapkit import config
from ff9mapkit.eb import cmdasm, model
from ff9mapkit.world import encounter as EC


def _game_ready() -> bool:
    try:
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


def _mini_eb(*probs: int) -> bytes:
    """A minimal valid .eb: entry 0, one function (tag 0) whose body is one RunWorldCode(26, prob) per `probs`
    (plus a decoy RunWorldCode(2, 1) so the finder must key on function 26, not just the opcode)."""
    parts = [cmdasm.assemble_instruction("RunWorldCode", [2, 1])]        # decoy: func 2 (minimap on), not 26
    for p in probs:
        parts.append(cmdasm.assemble_instruction("RunWorldCode", [EC.FUNC_ENCOUNT, p]))
    code = b"".join(parts)
    fc = 1
    body = bytes([0, fc]) + (0).to_bytes(2, "little") + (4 * fc).to_bytes(2, "little") + code  # tag 0, fpos=table end
    off = model.ENTRY_SLOT_SIZE * 1                                      # entry table = 1 slot; body follows it
    slot = off.to_bytes(2, "little") + len(body).to_bytes(2, "little") + bytes(4)
    header = bytearray(model.ENTRY_TABLE_OFF)
    header[0:2] = model.MAGIC
    header[3] = 1                                                        # entryCount
    return bytes(header) + slot + body


# --------------------------------------------------------------------------- the rate math (hermetic)

def test_transform_prob_multiplier_is_a_frequency_scale():
    # 2x frequency halves the period (prob+1): 231 -> round(232/2)-1 = 115; 365 -> round(366/2)-1 = 182
    assert EC.transform_prob(231, multiplier=2.0) == 115
    assert EC.transform_prob(365, multiplier=2.0) == 182
    # 0.5x frequency doubles the period
    assert EC.transform_prob(231, multiplier=0.5) == 463
    # identity
    assert EC.transform_prob(231, multiplier=1.0) == 231


def test_transform_prob_set_peaceful_and_clamps():
    assert EC.transform_prob(999, set_prob=231) == 231
    assert EC.transform_prob(10, peaceful=True) == EC.PROB_MAX == 0xFFFF
    assert EC.transform_prob(50, set_prob=10 ** 9) == EC.PROB_MAX           # clamp high
    assert EC.transform_prob(50, set_prob=-5) == 0                          # clamp low
    assert EC.transform_prob(231, multiplier=10 ** 6) == 0                  # huge frequency -> floor 0 (p=1/1)


def test_mode_validation_requires_exactly_one():
    for bad in (dict(), dict(multiplier=2.0, set_prob=1), dict(multiplier=2.0, peaceful=True)):
        with pytest.raises(ValueError):
            EC._validate_mode(bad.get("multiplier"), bad.get("set_prob"), bad.get("peaceful", False))
    for bad_mult in (0, -1, "x", True):
        with pytest.raises(ValueError):
            EC.transform_prob(231, multiplier=bad_mult)


# --------------------------------------------------------------------------- find + rewrite (hermetic)

def test_rate_writes_finds_only_func_26():
    eb = _mini_eb(231, 365)
    found = [(i.imm(0), i.imm(1)) for _, _, _, i in EC.rate_writes(eb)]
    assert found == [(26, 231), (26, 365)]                                 # decoy func-2 write excluded


def test_apply_rewrites_in_place_and_round_trips():
    eb = _mini_eb(231, 365)
    out, changes = EC.apply_encounter_rate(eb, pristine=eb, multiplier=2.0)
    assert len(out) == len(eb)                                             # pure in-place, length preserved
    assert [(c["from"], c["to"]) for c in changes] == [(231, 115), (365, 182)]
    # the rewritten values read back through the disassembler
    assert [i.imm(1) for _, _, _, i in EC.rate_writes(out)] == [115, 182]
    # only the value bytes changed (231->115 shares its 0x00 high byte; 365->182 both bytes) -> 3 bytes differ
    assert sum(a != b for a, b in zip(eb, out)) == 3
    # the decoy func-2 write is untouched
    from ff9mapkit.eb.model import EbScript
    ops = [i for f in EbScript(out).entry(0).funcs for i in EbScript(out).instrs(f) if i.op == EC.WPRM]
    assert (ops[0].imm(0), ops[0].imm(1)) == (2, 1)


def test_multiplier_is_idempotent_via_pristine():
    pristine = _mini_eb(231, 365)
    once, _ = EC.apply_encounter_rate(pristine, pristine=pristine, multiplier=2.0)
    twice, ch = EC.apply_encounter_rate(once, pristine=pristine, multiplier=2.0)   # re-apply to the scaled copy
    assert twice == once                                                   # derives from pristine, not the override
    assert [c["to"] for c in ch] == [115, 182]


def test_set_and_peaceful_apply_everywhere():
    eb = _mini_eb(231, 365)
    out_s, _ = EC.apply_encounter_rate(eb, set_prob=100)
    assert [i.imm(1) for _, _, _, i in EC.rate_writes(out_s)] == [100, 100]
    out_p, _ = EC.apply_encounter_rate(eb, peaceful=True)
    assert [i.imm(1) for _, _, _, i in EC.rate_writes(out_p)] == [0xFFFF, 0xFFFF]


# --------------------------------------------------------------------------- real dispatchers (game-gated)

@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_real_dispatchers_carry_the_shipping_rate_writes():
    from ff9mapkit.world import entrance as E
    alld = E.load_all_dispatchers()
    free_roam = {f"evt_world_world{n:02d}" for n in (0, 2, 3, 5, 7, 8, 9, 10, 11)}
    cutscene = {f"evt_world_world{n:02d}" for n in (1, 4, 6, 12)}
    total = 0
    values = set()
    for name in free_roam:
        writes = list(EC.rate_writes(alld[name]["us"]))
        tags = sorted(t for _, t, _, _ in writes)
        assert tags == [0, 10], f"{name} should carry Main_Init(0)+Main_Reinit(10) rate writes, got {tags}"
        values.update(i.imm(1) for _, _, _, i in writes)
        total += len(writes)
    for name in cutscene:
        assert list(EC.rate_writes(alld[name]["us"])) == [], f"{name} (cutscene) should carry no rate writes"
    assert total == 18                                                     # 9 free-roam x 2
    assert values == {231, 365}                                            # the game's only two danger values


def test_deploy_writes_per_language_eb_that_rereads(tmp_path, monkeypatch):
    """Hermetic: stub the dispatcher SOURCE with synthetic .eb (a free-roam state with writes + a cutscene state
    without), redirect the mod-folder DESTINATION to tmp, and confirm deploy lands per-language .eb.bytes that
    re-read with the retuned rate, skipping the write-less state."""
    from pathlib import Path
    from ff9mapkit.world import entrance as E
    synth = {
        "evt_world_world00": {"us": _mini_eb(231, 365), "jp": _mini_eb(231, 365)},
        "evt_world_world01": {"us": _mini_eb(), "jp": _mini_eb()},          # cutscene: decoy only, no func-26
    }
    monkeypatch.setattr(E, "load_all_dispatchers", lambda game=None: synth)
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    summary = EC.deploy_encounter_rate(mod_folder="FF9CustomMap", multiplier=2.0, langs=["us", "jp"])
    assert not summary["dry_run"] and summary["written"]
    assert summary["skipped_no_writes"] == ["evt_world_world01"]
    seen_langs, seen_names = set(), set()
    for p in summary["written"]:
        pp = Path(p)
        seen_langs.add(pp.parent.name)
        seen_names.add(pp.name)
        assert pp.relative_to(tmp_path).parts[0] == "FF9CustomMap"          # landed in the mod folder
        vals = {i.imm(1) for _, _, _, i in EC.rate_writes(pp.read_bytes())}
        assert vals == {115, 182}                                          # retuned, both beats present
    assert seen_langs == {"us", "jp"} and seen_names == {"EVT_WORLD_WORLD00.eb.bytes"}
    # idempotent redeploy: re-running reads the scaled override but derives from pristine -> same bytes
    before = (tmp_path / "FF9CustomMap" / EC._WORLD_EB_SUBDIR / "us" / "EVT_WORLD_WORLD00.eb.bytes").read_bytes()
    EC.deploy_encounter_rate(mod_folder="FF9CustomMap", multiplier=2.0, langs=["us", "jp"])
    after = (tmp_path / "FF9CustomMap" / EC._WORLD_EB_SUBDIR / "us" / "EVT_WORLD_WORLD00.eb.bytes").read_bytes()
    assert before == after
