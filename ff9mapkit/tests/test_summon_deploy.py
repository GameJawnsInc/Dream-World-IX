"""``summons.deploy`` -- the productized [[summon]] transplant DEPLOY engine (M2).

Two lanes (the suite's game-gated pattern):
  * PURE-LOGIC (always runs) -- the host-.seq splice (hybrid + overlay + calibrate), the HideMeshes clause
    format, the private-ef absent-set + validators, the [[summon]] normalize refusals (DESIGN section 1),
    the [SfxHybrid] rendering, and the _Ledger revert round-trip. No install, no stock bytes.
  * INSTALL-GATED -- the donor .seq drift verify, the DLL string-probe gate, and THE M1b BYTE-IDENTITY
    ACCEPTANCE (DESIGN section 4): the hybrid lane regenerates the LIVE proven deployment byte-for-byte.
    Skips cleanly when the FF9 install / the user's model FBX / the live M1b deployment are absent (the
    fresh-worktree trap -- these tests SKIP, they do not silently pass).
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

from ff9mapkit import config
from ff9mapkit.summons import deploy as D

# --- local input paths (the user's own retargeted model + the offline donor state) ---
_MODEL_FBX = Path(r"C:/gd/SCRATCH/summon-transplant/thomas_skinned.fbx")
_TEXTURE = Path(r"C:/gd/SCRATCH/thomas/Thomas_d.png")


def _game():
    try:
        return config.find_game_path()
    except config.ConfigError:
        return None


def _live_m1b(game):
    """The live M1b deployment paths (the byte-identity acceptance target), or None if not deployed."""
    if game is None:
        return None
    live = Path(game) / "FF9CustomMap"
    fbx = live / "StreamingAssets/Assets/Resources/Models/3/6201/6201.fbx"
    seq = live / "StreamingAssets/Data/SpecialEffects/ef084/PlayerSequence.seq"
    return live if (fbx.is_file() and seq.is_file()) else None


def _sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# A realistic synthetic donor .seq (CRLF, one anchor line, surrounded by other ops).
_DONOR_SEQ = (
    "Message: Casting\r\n"
    "LoadSFX: SFX=Foo__Full ; Reflect=True ; UseCamera=True\r\n"
    "WaitSFXLoaded: SFX=Foo__Full\r\n"
    "PlaySFX: SFX=Foo__Full ; Reflect=True\r\n"
    "WaitSFXDone: SFX=Foo__Full\r\n"
    "Turn: back\r\n"
)


# =========================================================================== PURE LOGIC (always runs)

def test_splice_hybrid_patches_only_the_anchor():
    out = D.splice_host_seq(_DONOR_SEQ, ["0033B990", "0x0034BA50"], overlay=False)
    assert "PlaySFX: SFX=Foo__Full ; Reflect=True ; HideMeshes=0x0033B990,0x0034BA50\r\n" in out
    # every OTHER line is untouched (the LoadSFX ; Reflect line, which is NOT the anchor, is preserved)
    assert "LoadSFX: SFX=Foo__Full ; Reflect=True ; UseCamera=True\r\n" in out
    assert out.count("PlaySFX:") == 1
    assert out.count("HideMeshes") == 1


def test_splice_calibrate_is_byte_identical_to_donor():
    assert D.splice_host_seq(_DONOR_SEQ, None, overlay=False) == _DONOR_SEQ
    assert D.splice_host_seq(_DONOR_SEQ, [], overlay=False) == _DONOR_SEQ


def test_splice_overlay_inserts_startthread_before_anchor():
    out = D.splice_host_seq(_DONOR_SEQ, ["0033B990"], private_ef=84, overlay=True)
    lines = out.splitlines()
    st = lines.index("StartThread: Condition=1 == 1 ; Sync=False")
    anchor = next(i for i, l in enumerate(lines) if l.startswith("PlaySFX: SFX=Foo__Full ; Reflect=True ; HideMeshes"))
    assert st < anchor                                            # the thread is BEFORE the anchor
    assert "\tLoadSFX: SFX=84 ; Char=Caster ; UseCamera=False" in lines
    assert "\tPlaySFX: SFX=84 ; SkipSequence=True" in lines
    assert "EndThread" in lines


def test_splice_preserves_line_ending_lf():
    lf = _DONOR_SEQ.replace("\r\n", "\n")
    out = D.splice_host_seq(lf, ["0033B990"], overlay=False)
    assert "PlaySFX: SFX=Foo__Full ; Reflect=True ; HideMeshes=0x0033B990\n" in out
    assert "\r\n" not in out


def test_find_anchor_missing_and_ambiguous():
    with pytest.raises(D.DonorDriftError):
        D.find_anchor("no anchor here\r\nMessage: x\r\n")
    two = ("PlaySFX: SFX=A__Full ; Reflect=True\r\n"
           "PlaySFX: SFX=B__Full ; Reflect=True\r\n")
    with pytest.raises(D.DonorDriftError):
        D.find_anchor(two)                                       # ambiguous -> refuse
    idx, sfx, nl = D.find_anchor(two, sfx_name="B__Full")        # disambiguated
    assert idx == 1 and sfx == "B__Full" and nl == "\r\n"


def test_hide_meshes_arg_format():
    assert D._hide_meshes_arg(None) == ""
    assert D._hide_meshes_arg([]) == ""
    assert D._hide_meshes_arg(["0033B990"]) == " ; HideMeshes=0x0033B990"
    # a 0x prefix on input is stripped, then re-added once
    assert D._hide_meshes_arg(["0x0033B990", "0034BA50"]) == " ; HideMeshes=0x0033B990,0x0034BA50"


def test_derive_summon_name_matches_bench():
    assert D.derive_summon_name(6201, "MON", "B0") == "GEO_MON_B0_M201"
    assert D.derive_summon_name(6000, "MON", "B0") == "GEO_MON_B0_M000"


def test_absent_set_is_the_24_id_census():
    assert len(D.ABSENT_EF_IDS) == 24
    assert 84 in D.ABSENT_EF_IDS and 18 in D.ABSENT_EF_IDS and 488 in D.ABSENT_EF_IDS
    assert 227 not in D.ABSENT_EF_IDS                            # a real donor is never in the pool


@pytest.mark.parametrize("block,needle", [
    ({"lane": "bogus"}, "lane must be one of"),
    ({"donor": 227, "private_ef": 227}, "equals donor"),
    ({"donor": 227, "private_ef": 100}, "not a stock-absent"),
    ({"id": 5999}, "below the mint band"),
    ({"donor": "Bahamut__Full"}, "NUMERIC effect id"),
    ({"hide_meshes": ["zznothex"]}, "not a hex mesh key"),
    ({"staging": "weird"}, "staging must be"),
])
def test_normalize_refusals(block, needle):
    with pytest.raises(D.SummonDeployError) as ei:
        D.normalize_spec(block)
    assert needle in str(ei.value)


def test_validate_private_ef_static_half():
    D.validate_private_ef(84, 227)                               # ok, install-independent
    with pytest.raises(D.SummonDeployError):
        D.validate_private_ef(227, 227)                          # == donor
    with pytest.raises(D.SummonDeployError):
        D.validate_private_ef(999, 227)                          # not absent


def test_normalize_defaults_and_textures_carry():
    spec = D.normalize_spec({"donor": 227, "model": "x.fbx", "textures": ["a.png", "b.png"],
                             "id": 6201, "group": "MON"})
    assert spec["lane"] == "hybrid" and spec["name"] == "GEO_MON_B0_M201"
    assert spec["node_count"] == 93 and spec["hide_mask"] == "0x3"
    assert spec["textures"] == ["a.png", "b.png"]


@pytest.mark.parametrize("given,want", [
    (3, "0x3"), (0, "0x0"), (12, "0xc"), (255, "0xff"),
    ("0x3", "0x3"), ("0Xc", "0Xc"), ("0xFF", "0xFF"),
])
def test_hide_mask_accepts_int_and_hex_string(given, want):
    """REGRESSION (Finding 2): a TOML int must render to the '0x...' form the engine's LoadHex parser
    expects (str()-ing the int alone would arm e.g. HideMask=12 which LoadHex reads AS HEX = 18); a
    '0x...' string is kept as given."""
    spec = D.normalize_spec({"donor": 227, "hide_mask": given})
    assert spec["hide_mask"] == want


@pytest.mark.parametrize("bad", ["12", "3", "not-hex", "0xZZ", "", "0x"])
def test_hide_mask_bare_or_non_hex_string_is_refused(bad):
    """A bare decimal-looking string (no '0x') is exactly the shape that silently mis-arms the mask
    (LoadHex would parse "12" as hex 0x12 = 18) -- refuse it with a clear message instead of guessing."""
    with pytest.raises(D.SummonDeployError) as ei:
        D.normalize_spec({"donor": 227, "hide_mask": bad})
    assert "hide_mask" in str(ei.value)


def test_hide_mask_rejects_bool():
    with pytest.raises(D.SummonDeployError):
        D.normalize_spec({"donor": 227, "hide_mask": True})


def test_sfxhybrid_block_matches_the_acceptance():
    spec = D.normalize_spec({"donor": 227, "id": 6201, "name": "GEO_MON_B0_M201",
                             "private_ef": 84, "node_count": 93, "hide_mask": "0x3"})
    up = D.sfxhybrid_updates(spec, log=True)
    assert up == {"Enabled": "1", "EffectId": "227", "ModelPath": "GEO_MON_B0_M201",
                  "HideNative": "1", "HideMask": "0x3", "NodeCount": "93",
                  "ApplyColumnScale": "0", "Log": "1"}
    block = D.render_sfxhybrid_block(spec, log=True)
    assert block.startswith("[SfxHybrid]\n")
    for line in ("Enabled = 1", "EffectId = 227", "ModelPath = GEO_MON_B0_M201", "HideMask = 0x3"):
        assert line in block


def test_arm_updates_apply_via_coop_writer():
    """The arm step's section text (pure): applying sfxhybrid_updates to a fresh ini via the coop writer
    yields the exact [SfxHybrid] block -- no install, no DLL (that half is the gate, tested game-side)."""
    from ff9mapkit import coop
    spec = D.normalize_spec({"donor": 227, "id": 6201, "name": "GEO_MON_B0_M201", "private_ef": 84})
    text = "[SfxProbe]\nEnabled = 0\n"
    new = coop.update_ini_section(text, "SfxHybrid", D.sfxhybrid_updates(spec, log=False))
    assert "[SfxHybrid]" in new and "EffectId = 227" in new and "ModelPath = GEO_MON_B0_M201" in new
    assert "[SfxProbe]" in new                                   # the other section survives


def test_lint_emits_model_and_vfx1_reminder():
    probs = D.lint_spec({"donor": 227, "private_ef": 84})
    assert any("needs a" in p and "model" in p for p in probs)
    assert any("vfx1" in p for p in probs)


def test_ledger_revert_round_trip(tmp_path):
    """The _Ledger writes files + a DictionaryPatch line and renders a stdlib-only revert script that
    removes newly-created files + drops the line (the tools/deploy_field.py revert convention)."""
    ledger = D._Ledger(tmp_path / ".bak")
    f = tmp_path / "sub" / "a.txt"
    ledger.write_bytes(f, b"hello")
    dp = tmp_path / "DictionaryPatch.txt"
    assert ledger.append_dict_line(dp, "3DModel 6201 GEO_MON_B0_M201") is True
    assert ledger.append_dict_line(dp, "3DModel 6201 GEO_MON_B0_M201") is False   # idempotent
    rev = ledger.write_revert_script(tmp_path / ".rev", "6201")
    assert f.exists() and "3DModel 6201 GEO_MON_B0_M201" in dp.read_text()
    rc = subprocess.run([sys.executable, str(rev)], capture_output=True, text=True)
    assert rc.returncode == 0, rc.stderr
    assert not f.exists()                                        # newly-created file removed
    assert "3DModel 6201 GEO_MON_B0_M201" not in dp.read_text() # line dropped


def test_hybrid_deploy_revert_restores_the_armed_ini(tmp_path):
    """REGRESSION (arm/revert wiring): a hybrid ``deploy(..., arm=True)`` must produce a revert script that
    actually undoes the ``[SfxHybrid]`` Memoria.ini arm, not just the mint + host .seq -- previously
    ``_Ledger.record_ini`` was dead code (defined, never called anywhere), so an armed deploy's revert
    script's ini-restore/neutralize branch never ran and the arm silently survived a 'revert'. Exercises
    the real ``deploy()`` + ``arm_sfxhybrid()`` + revert-script path against a synthetic offline 'install'
    (a stub Assembly-CSharp.dll carrying the SfxHybridDrive marker so ``probe_hybrid_engine`` passes, a
    fake donor .seq, and a throwaway Memoria.ini) -- no real FF9 install needed, so this ALWAYS runs."""
    game = tmp_path / "game"
    dll = game / "x64" / "FF9_Data" / "Managed" / "Assembly-CSharp.dll"
    dll.parent.mkdir(parents=True)
    dll.write_bytes(b"...SfxHybridDrive...")                       # satisfies probe_hybrid_engine
    ini = game / "Memoria.ini"
    original = "[Other]\nFoo = 1\n"
    ini.write_text(original, encoding="utf-8")
    donor = 500                                                    # NOT in EXPECTED_DONOR_SEQ_SHA -> no drift guard
    seq_dir = game / "StreamingAssets" / "Data" / "SpecialEffects" / f"ef{donor:03d}"
    seq_dir.mkdir(parents=True)
    (seq_dir / "PlayerSequence.seq").write_text(_DONOR_SEQ, encoding="utf-8")

    mod = tmp_path / "mod"
    fbx = tmp_path / "m.fbx"
    fbx.write_bytes(b"FAKE-FBX-BYTES")
    block = {"donor": donor, "model": str(fbx), "id": 6201, "private_ef": 84, "lane": "hybrid"}
    res = D.deploy(block, game=str(game), mod_root=str(mod), arm=True, out=lambda *a, **k: None)

    assert res["armed"] is True
    armed_text = ini.read_text(encoding="utf-8")
    assert armed_text != original and "[SfxHybrid]" in armed_text     # the ini really was mutated

    rc = subprocess.run([sys.executable, res["revert_script"]], capture_output=True, text=True)
    assert rc.returncode == 0, rc.stderr
    assert ini.read_text(encoding="utf-8") == original                # THE FIX: the arm is actually undone


def test_overlay_manifest_shape():
    spec = D.normalize_spec({"donor": 227, "id": 6201, "name": "GEO_MON_B0_M201", "private_ef": 84})
    man = D._sfxmodel_manifest(spec, [0, 1])
    assert man["FBX"][0]["Path"] == "GEO_MON_B0_M201"           # bare GEO name (Hop 4/5)
    assert man["FBX"][0]["Animations"] == [{"Path": "Animations/6201/0"}, {"Path": "Animations/6201/1"}]
    assert D._sfxmodel_manifest(spec, [])["FBX"][0].get("Animations") is None


def test_cli_block_builder_resolves_a_name_donor(tmp_path):
    """REGRESSION (Finding 1): summon-deploy/-import are the ONLY deploy path, and deploy.normalize_spec
    takes a NUMERIC donor -- so the shared CLI block builder must resolve a DOCUMENTED name donor
    (`donor = "Bahamut__Full"`, which build/lint accept) to its id before handing the block to
    deploy.deploy()/stage_import(); otherwise a lint-clean block dies at deploy. _summon_block_from_args
    (shared by both verbs, covering the --from-toml path a name arrives through) resolves it."""
    import argparse

    from ff9mapkit import cli
    toml = tmp_path / "s.toml"
    toml.write_text('[[summon]]\ndonor = "Bahamut__Full"\nmodel = "x.fbx"\n', encoding="utf-8")
    block = cli._summon_block_from_args(argparse.Namespace(from_toml=str(toml)))
    assert block["donor"] == 227                                 # name -> numeric id
    D.normalize_spec(block)                                      # the deploy engine now ACCEPTS it (no raise)


def test_cli_block_builder_unknown_name_is_a_clean_exit(tmp_path):
    """An unknown donor name surfaces as a clean SystemExit (CLI-style), not an uncaught traceback."""
    import argparse

    from ff9mapkit import cli
    toml = tmp_path / "s.toml"
    toml.write_text('[[summon]]\ndonor = "NotASummon"\nmodel = "x.fbx"\n', encoding="utf-8")
    with pytest.raises(SystemExit):
        cli._summon_block_from_args(argparse.Namespace(from_toml=str(toml)))


# =========================================================================== INSTALL-GATED

@pytest.mark.skipif(_game() is None, reason="no FF9 install resolvable")
def test_fetch_donor_seq_drift_verify():
    game = _game()
    if not D.donor_seq_path(game, 227).is_file():
        pytest.skip("donor ef227/PlayerSequence.seq not loose in this install")
    text = D.fetch_donor_seq(game, 227)                         # passes the drift guard
    idx, sfx, nl = D.find_anchor(text)
    assert sfx == "Bahamut__Full" and nl == "\r\n"


@pytest.mark.skipif(_game() is None, reason="no FF9 install resolvable")
def test_probe_hybrid_engine_gate():
    game = _game()
    dll = Path(game) / "x64/FF9_Data/Managed/Assembly-CSharp.dll"
    if not dll.is_file():
        pytest.skip("no deployed Assembly-CSharp.dll")
    # the result is a real fact about THIS install's engine; assert the probe agrees with the raw bytes
    assert D.probe_hybrid_engine(game) == (b"SfxHybridDrive" in dll.read_bytes())


@pytest.mark.skipif(
    _game() is None or _live_m1b(_game()) is None or not _MODEL_FBX.is_file() or not _TEXTURE.is_file(),
    reason="needs the FF9 install, the live M1b deployment, and the user's model FBX + texture")
def test_m1b_byte_identity_acceptance(tmp_path):
    """DESIGN section 4: the productized HYBRID lane regenerates the 5 live M1b artifacts byte-for-byte,
    and emits NONE of the overlay residue."""
    game = _game()
    live = _live_m1b(game)
    mod = tmp_path / "FF9CustomMap"
    block = {
        "donor": 227, "model": str(_MODEL_FBX), "textures": [str(_TEXTURE)],
        "lane": "hybrid", "id": 6201, "name": "GEO_MON_B0_M201", "group": "MON",
        "private_ef": 84, "node_count": 93, "hide_mask": "0x3",
        "hide_meshes": ["0033B990", "0033B9D0", "0035BAD0", "0035BA90",
                        "0034BA10", "0034BA50", "0097BD02"],
    }
    res = D.emit_hybrid(D.normalize_spec(block), mod, game, work_dir=tmp_path)

    m = mod / "StreamingAssets/Assets/Resources/Models/3/6201"
    lm = live / "StreamingAssets/Assets/Resources/Models/3/6201"
    # 1 + 2: the user's own model + texture, byte-identical to the live deploy
    assert _sha(m / "6201.fbx") == _sha(lm / "6201.fbx")
    assert _sha(m / "Thomas_d.png") == _sha(lm / "Thomas_d.png")
    # 3: the DictionaryPatch line
    assert "3DModel 6201 GEO_MON_B0_M201" in (mod / "DictionaryPatch.txt").read_text().splitlines()
    # 4: the host .seq, BYTE-IDENTICAL to the live proven ef084/PlayerSequence.seq
    staged_seq = (mod / "StreamingAssets/Data/SpecialEffects/ef084/PlayerSequence.seq").read_bytes()
    live_seq = (live / "StreamingAssets/Data/SpecialEffects/ef084/PlayerSequence.seq").read_bytes()
    assert staged_seq == live_seq
    # 5: the staged [SfxHybrid] arm block matches the live section (modulo Log)
    for line in ("EffectId = 227", "ModelPath = GEO_MON_B0_M201", "HideMask = 0x3", "NodeCount = 93"):
        assert line in res["arm_manifest"]

    # EXCLUSIONS (DESIGN section 4): the clean hybrid lane emits NO overlay residue
    ef084 = mod / "StreamingAssets/Data/SpecialEffects/ef084"
    assert not (ef084 / "FileList.txt").exists()
    assert not list(ef084.glob("*.sfxmodel"))
    assert not (mod / "StreamingAssets/Assets/Resources/Models/3/6200").exists()


def test_revert_script_survives_hostile_plan_values(tmp_path):
    """The reverttmpl hardening class (44fcf794): a plan value containing triple quotes or
    backslash-quote soup must not break out of the generated revert script's code. (Windows
    can't create such paths, so the hostile value is injected at the plan seam directly --
    the TEMPLATE's codegen is what's under test.)"""
    import json as _json
    from ff9mapkit.summons.deploy import _Ledger

    led = _Ledger(tmp_path / "bk")
    hostile = r'C:\evil """ dir \" x\victim.txt'
    led.files.append((hostile, None))
    script_path = led.write_revert_script(tmp_path, "hostile")
    src = script_path.read_text(encoding="utf-8")
    compile(src, str(script_path), "exec")  # must be valid Python despite the hostile value
    # the injected literal is a single-line repr'd str; eval just that literal and round-trip it
    line = src.split("PLAN = json.loads(", 1)[1].splitlines()[0]
    plan = _json.loads(eval(line[: line.rindex(")")]))
    assert hostile in [f for f, _ in plan["files"]]
