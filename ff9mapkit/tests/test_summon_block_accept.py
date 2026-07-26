"""Install-gated acceptance for the ``[[summon]]`` hybrid lane (DESIGN section 4).

Two rungs, BOTH skip cleanly when their inputs are absent (the fresh-worktree trap: a bare checkout has
no FF9 install and no SCRATCH model, so these SKIP -- the runner must read the real skip counts, not
assume green). This round STAGES into a temp mirror + compares against the LIVE install READ-ONLY; it
never mutates the live game folder.

  * RUNG A (install-only, READ-ONLY): the block-schema layer + ``deploy.sfxhybrid_updates`` reproduce the
    LIVE M1b deployment's ini + DictionaryPatch line -- the ``[SfxHybrid]`` values (modulo ``Log``,
    first-cast-only) and ``3DModel 6201 GEO_MON_B0_M201``.
  * RUNG B (install + SCRATCH model): ``summon.emit`` STAGES the hybrid artifacts into a TEMP mod-root
    mirror (reading the donor ``.seq`` from the live install read-only, drift-guarded) and byte-compares
    the staged host ``.seq`` + FBX to the live deployment.
"""
from pathlib import Path

import pytest

from ff9mapkit import config
from ff9mapkit.content import summon
from ff9mapkit.summons import deploy
from tests.test_summon_block import acceptance_block

LIVE_MODEL = Path(r"C:/gd/SCRATCH/summon-transplant/thomas_skinned.fbx")


def _game():
    try:
        return Path(config.find_game_path())
    except config.ConfigError:
        pytest.skip("no FF9 install resolvable -- install-gated summon acceptance skipped")


def _live_mod():
    game = _game()
    mod = game / "FF9CustomMap"
    if not mod.is_dir():
        pytest.skip(f"live mod folder {mod} absent -- M1b acceptance skipped")
    return game, mod


# ------------------------------------------------------------------ RUNG A (install-only, read-only)
def test_mint_directive_matches_the_live_dictionarypatch():
    _game_, mod = _live_mod()
    dp = mod / "DictionaryPatch.txt"
    if not dp.is_file():
        pytest.skip(f"{dp} absent")
    lines = dp.read_text(encoding="utf-8", errors="replace").splitlines()
    assert "3DModel 6201 GEO_MON_B0_M201" in lines, "the productized mint directive is not the live line"


def test_sfxhybrid_updates_match_the_live_memoria_ini():
    game, _mod = _live_mod()
    ini = game / "Memoria.ini"
    if not ini.is_file():
        pytest.skip(f"{ini} absent")
    live = _read_ini_section(ini.read_text(encoding="utf-8", errors="replace"), "SfxHybrid")
    if not live or str(live.get("Enabled", "0")).strip() == "0":
        # absent OR disarmed (Enabled = 0 -- the TIER W cast-1 state: the hybrid mask
        # off so the native creature shows): the lane is not live, nothing to compare
        pytest.skip("[SfxHybrid] not armed in the live Memoria.ini -- nothing to compare")
    updates = deploy.sfxhybrid_updates(summon.resolve_spec(acceptance_block()), log=True)
    for key, want in updates.items():
        if key == "Log":                                  # first-cast-only per RUNBOOK section 5
            continue
        assert key in live, f"[SfxHybrid] {key} missing from the live ini"
        assert str(live[key]).strip() == str(want), f"[SfxHybrid] {key}: live {live[key]!r} != {want!r}"


# ------------------------------------------------------------------ RUNG B (install + SCRATCH model)
def test_hybrid_lane_stages_seq_and_fbx_byte_for_byte(tmp_path):
    game, mod = _live_mod()
    if not LIVE_MODEL.is_file():
        pytest.skip(f"{LIVE_MODEL} absent -- the retargeted bench model is SCRATCH-only")
    live_seq = mod / "StreamingAssets" / "Data" / "SpecialEffects" / "ef084" / "PlayerSequence.seq"
    live_fbx = mod / "StreamingAssets" / "Assets" / "Resources" / "Models" / "3" / "6201" / "6201.fbx"
    if not (live_seq.is_file() and live_fbx.is_file()):
        pytest.skip("live M1b ef084 .seq / 6201.fbx absent -- nothing to byte-compare")

    block = acceptance_block()
    block["model"] = str(LIVE_MODEL)
    # stage into a TEMP mod-root mirror (never the live folder); donor .seq is READ from the live install
    result = summon.emit(block, tmp_path, game)

    staged_seq = Path(result["seq"]["seq_dest"]).read_bytes()
    assert staged_seq == live_seq.read_bytes(), "staged host .seq != the live proven ef084 PlayerSequence.seq"
    staged_fbx = Path(result["mint"]["fbx_dest"]).read_bytes()
    assert staged_fbx == live_fbx.read_bytes(), "staged 6201.fbx != the live neutral-bind mint"
    # the staged DictionaryPatch carries the acceptance directive
    assert result["mint"]["directive"] == "3DModel 6201 GEO_MON_B0_M201"


def _read_ini_section(text: str, section: str) -> dict:
    """Parse one ``[section]`` from an ini into ``{key: value}`` (last write wins, like the engine)."""
    out, cur = {}, None
    for ln in text.splitlines():
        s = ln.strip()
        if s.startswith("[") and s.endswith("]"):
            cur = s[1:-1].strip()
            continue
        if cur == section and "=" in s and not s.startswith(";"):
            k, _, v = s.partition("=")
            out[k.strip()] = v.strip()
    return out
