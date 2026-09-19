"""Offline tests for the summon lane's mint-id allocation and its 3DModel-id collision guard
(``summons/deploy.py`` ``alloc_mint_id`` / ``_resolve_ids`` / ``_warn_model_id_collision`` / the dry-run
mirror). Everything runs against ``tmp_path``: a throwaway 'game' dir (no native effects, so a pinned
private_ef 84 validates; a synthetic donor .seq where an emit needs one) and mod folders holding only a
``DictionaryPatch.txt`` and/or an empty model directory -- no FF9 install, zero SE bytes."""

from pathlib import Path

from ff9mapkit.models import export as _mexport
from ff9mapkit.summons import deploy as D

_RES = _mexport._RES

_DONOR_SEQ = (                       # the synthetic offline cast test_summon_deploy.py drives the hybrid lane with
    "Message: Casting\r\n"
    "LoadSFX: SFX=Foo__Full ; Reflect=True ; UseCamera=True\r\n"
    "WaitSFXLoaded: SFX=Foo__Full\r\n"
    "PlaySFX: SFX=Foo__Full ; Reflect=True\r\n"
    "WaitSFXDone: SFX=Foo__Full\r\n"
    "Turn: back\r\n"
)


def _game(tmp_path, folders=("A", "B")) -> Path:
    g = tmp_path / "game"
    g.mkdir(exist_ok=True)
    names = ", ".join(f'"{f}"' for f in folders)
    (g / "Memoria.ini").write_text(f"[Mod]\nFolderNames = {names}\n", encoding="utf-8")
    return g


def _register(root: Path, *lines: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "DictionaryPatch.txt").write_text("".join(f"{ln}\n" for ln in lines), encoding="utf-8")


def _spec(**over) -> dict:
    # the least an id-less block needs to resolve offline: an explicit donor (no drift guard is consulted
    # here) and a PINNED private_ef (84 is stock-absent, and the tmp 'game' carries no native ef084)
    block = {"donor": 500, "model": "unused.fbx", "private_ef": 84, "lane": "overlay"}
    block.update(over)
    return D.normalize_spec(block)


def _hybrid_block(tmp_path, game: Path, **over) -> dict:
    """A hybrid-lane block that emits offline: donor 502 (unregistered in EXPECTED_DONOR_SEQ_SHA, so no
    drift guard) with a synthetic loose .seq under the tmp 'game', and a stub FBX with no textures."""
    seq_dir = game / "StreamingAssets" / "Data" / "SpecialEffects" / "ef502"
    seq_dir.mkdir(parents=True, exist_ok=True)
    (seq_dir / "PlayerSequence.seq").write_text(_DONOR_SEQ, encoding="utf-8")
    fbx = tmp_path / "m.fbx"
    fbx.write_bytes(b"FAKE-FBX-BYTES")
    block = {"donor": 502, "model": str(fbx), "private_ef": 84, "lane": "hybrid"}
    block.update(over)
    return block


# ---- alloc_mint_id ---------------------------------------------------------------------------

def test_alloc_skips_a_registered_id_with_no_models_dir(tmp_path):
    """REGRESSION (scout 9b): a weapon mint (GEO_WEP_*, type 6) lives under BattleMap/BattleModel/6/,
    OUTSIDE the Models/ tree the allocator scanned -- so the next id-less summon re-minted its id and the
    folder ended up with two `3DModel 6000` lines (the engine's last writer wins: one side loads the wrong
    mesh, no error). The folder's DictionaryPatch is the engine's own list; the allocator seeds from it --
    the registry LINE alone is what closes the hole (asserted before the weapon's directory even exists)."""
    mod = tmp_path / "A"
    _register(mod, "3DModel 6000 GEO_WEP_B1_M000")
    assert D.alloc_mint_id(mod) == 6001
    mod.joinpath(*_RES, *_mexport.model_dir_parts(6, 6000)).mkdir(parents=True)   # the real weapon layout
    assert D.alloc_mint_id(mod) == 6001


def test_alloc_still_skips_a_bare_models_dir(tmp_path):
    """CHARACTERIZATION (unchanged): an empty folder allocates the band start, and an UNREGISTERED leftover
    Models/<type>/<id>/ folder is still not adopted by a fresh mint."""
    mod = tmp_path / "A"
    assert D.alloc_mint_id(mod) == D.MINT_BAND_START
    mod.joinpath(*_RES, "Models", "3", "6000").mkdir(parents=True)
    assert D.alloc_mint_id(mod) == 6001


def test_alloc_honours_the_callers_avoid_set(tmp_path):
    assert D.alloc_mint_id(tmp_path / "A", avoid={6000, 6001}) == 6002


# ---- _resolve_ids: the cross-folder avoid set ----------------------------------------------

def test_resolve_ids_skips_an_id_another_stacked_folder_registers(tmp_path):
    """REGRESSION (scout 9b): FF9BattleDB.GEO is GLOBAL across FolderNames folders, and the summon lane was
    the one deploy lane that never consulted deploystack -- an id-less block took 6000 while a sibling
    folder already registered `3DModel 6000`: the wrong model in battle, no error anywhere."""
    game = _game(tmp_path)
    _register(game / "B", "3DModel 6000 GEO_MON_B0_M000")
    lines: list = []
    spec = D._resolve_ids(_spec(), game / "A", game, out=lines.append)
    assert spec["id"] == 6001
    assert spec["name"] == D.derive_summon_name(6001, D.DEFAULT_GROUP, D.DEFAULT_FORM)   # the name follows
    assert lines == []                                       # the guard never crashed -> nothing to say


def test_resolve_ids_without_a_memoria_ini_is_quiet(tmp_path):
    """No ini beside `game` -> an empty stack -> no avoid set, no line, the plain band start."""
    game = tmp_path / "game"
    game.mkdir()
    lines: list = []
    spec = D._resolve_ids(_spec(), game / "A", game, out=lines.append)
    assert spec["id"] == D.MINT_BAND_START and lines == []


def test_resolve_ids_with_no_game_is_quiet(tmp_path):
    """game=None is the emitters' documented offline shape (test_summon_curves drives them with it; the
    lane's `_install_has_native_ef` returns False for it) -- the guard degrades to 'no stack' SILENTLY
    there, never to the 'guard unavailable -- fix it' crash line (nothing is broken)."""
    lines: list = []
    spec = D._resolve_ids(_spec(), tmp_path / "A", None, out=lines.append)
    assert spec["id"] == D.MINT_BAND_START and lines == []


def test_a_guard_crash_degrades_loudly_and_still_allocates(tmp_path, monkeypatch):
    """The sibling lanes' print-on-crash contract: a checker that blows up must not take the deploy down,
    and must not be swallowed either (a check that cannot fail is no check)."""
    def boom(*a, **k):
        raise RuntimeError("synthetic")
    monkeypatch.setattr(D.deploystack, "check_model_id_collisions", boom)
    game = _game(tmp_path)
    lines: list = []
    spec = D._resolve_ids(_spec(), game / "A", game, out=lines.append)
    assert spec["id"] == D.MINT_BAND_START                   # the own-folder allocation survived
    assert len(lines) == 1 and "3DModel-id guard unavailable" in lines[0] and "synthetic" in lines[0]
    D._warn_model_id_collision(spec, game / "A", game, lines.append)
    assert len(lines) == 2 and "3DModel-id guard unavailable" in lines[1]


# ---- _warn_model_id_collision: the pinned-id banner ----------------------------------------

def test_warn_fires_on_a_pinned_collision(tmp_path):
    """The sibling lanes' contract (tools/deploy_field.py, deploy_battle.py, `model-mint --deploy`): a
    PINNED id another stacked folder registers is a loud WARN through `out`, never an abort."""
    game = _game(tmp_path)
    _register(game / "B", "3DModel 6000 GEO_MON_B0_M000")
    lines: list = []
    D._warn_model_id_collision(_spec(id=6000), game / "A", game, lines.append)
    text = "\n".join(lines)
    assert "3DMODEL ID COLLISION" in text and "'B'" in text and "GEO_MON_B0_M000" in text


def test_a_pinned_redeploy_into_its_own_folder_is_quiet(tmp_path):
    """The target folder's OWN registration of the pinned id is a redeploy, not a collision -- the checker
    excludes the folder by NAME, so this pins that `Path(mod_root).name` is the name it is excluded under."""
    game = _game(tmp_path)
    _register(game / "A", "3DModel 6000 GEO_MON_B0_M000")
    lines: list = []
    D._warn_model_id_collision(_spec(id=6000), game / "A", game, lines.append)
    assert lines == []


# ---- the emitters: once per emit, through `out` --------------------------------------------

def test_emit_hybrid_warns_exactly_once_and_through_out(tmp_path, capsys):
    game = _game(tmp_path, folders=("mod", "B"))
    _register(game / "B", "3DModel 6201 GEO_MON_B0_M201")
    block = _hybrid_block(tmp_path, game, id=6201)
    lines: list = []
    res = D.emit_hybrid(block, tmp_path / "mod", str(game), out=lines.append)
    assert Path(res["mint"]["fbx_dest"]).is_file()                       # the emit itself went through
    assert sum("3DMODEL ID COLLISION" in ln for ln in lines) == 1
    assert "COLLISION" not in capsys.readouterr().out                    # nothing leaked past `out`


def test_stage_import_warns_exactly_once_and_through_out(tmp_path, capsys):
    """stage_import resolves the id itself (to name the FBX) and THEN dispatches to an emitter that
    resolves again -- the banner must still print once, and on the caller's `out`, not stdout."""
    game = _game(tmp_path, folders=("mod", "B"))
    _register(game / "B", "3DModel 6201 GEO_MON_B0_M201")
    block = _hybrid_block(tmp_path, game, id=6201)
    stub = tmp_path / "import.fbx"
    # a binary header skips the ASCII-FBX validation; the bare texture name satisfies the STRIP-path check
    stub.write_bytes(b"Kaydara FBX Binary  \x00" + b"\x00" * 16 + b"Thomas_d.png" + b"\x00" * 16)
    block.pop("model")
    lines: list = []
    res = D.stage_import(stub, block, game=str(game), mod_root=tmp_path / "mod", out=lines.append)
    assert res["imported_from"] == str(stub)
    assert sum("3DMODEL ID COLLISION" in ln for ln in lines) == 1
    assert "COLLISION" not in capsys.readouterr().out


# ---- the dry-run mirror ---------------------------------------------------------------------

def test_dry_run_allocates_against_the_live_registry(tmp_path, monkeypatch):
    """A dry run stages into a scratch mirror that carries the live folder's NAME (so the cross-folder
    checker excludes it as 'self') -- and now its REGISTRY too, so the receipt reports the id the real
    deploy would mint instead of one the live folder already holds. The live side is only read."""
    from ff9mapkit.summons import export as _sexport
    monkeypatch.setattr(_sexport, "DEFAULT_OUT_DIR", tmp_path / "scratch")
    game = _game(tmp_path, folders=("FF9CustomMap", "B"))
    live = tmp_path / "FF9CustomMap"
    _register(live, "3DModel 6000 GEO_MON_B0_M000")
    before = (live / "DictionaryPatch.txt").read_bytes()
    lines: list = []
    res = D.deploy(_hybrid_block(tmp_path, game), game=str(game), mod_root=str(live), dry_run=True,
                   out=lines.append)
    assert res["dry_run"] and res["spec"]["id"] == 6001
    assert Path(res["mod_root"]) == tmp_path / "scratch" / "m2_stage" / "FF9CustomMap"
    assert res["mint"]["directive_added"] is True                        # a genuinely new id
    assert (live / "DictionaryPatch.txt").read_bytes() == before         # untouched
    mirror_lines = (Path(res["mod_root"]) / "DictionaryPatch.txt").read_text().splitlines()
    assert mirror_lines[0] == "3DModel 6000 GEO_MON_B0_M000" and "3DModel 6001" in mirror_lines[1]
    assert not any("COLLISION" in ln for ln in lines)                    # own registrations are not foreign


def test_dry_run_of_a_pinned_redeploy_reports_no_new_id(tmp_path, monkeypatch):
    """The receipt's 'NEW GEO id -- RELAUNCH' line keys off `directive_added`; a dry run of a plain
    redeploy must say what the live deploy would (nothing new), which needs the seeded registry."""
    from ff9mapkit.summons import export as _sexport
    monkeypatch.setattr(_sexport, "DEFAULT_OUT_DIR", tmp_path / "scratch")
    game = _game(tmp_path, folders=("FF9CustomMap", "B"))
    live = tmp_path / "FF9CustomMap"
    _register(live, "3DModel 6201 GEO_MON_B0_M201")
    res = D.deploy(_hybrid_block(tmp_path, game, id=6201), game=str(game), mod_root=str(live),
                   dry_run=True, out=lambda *a, **k: None)
    assert res["spec"]["id"] == 6201 and res["mint"]["directive_added"] is False


# ---- the CLI: --dry-run honours --mod-folder -----------------------------------------------

def test_cli_summon_deploy_dry_run_honours_mod_folder(tmp_path, monkeypatch):
    """`summon-deploy --dry-run` passed mod_root=None, so deploy() mirrored the DEFAULT folder whatever
    --mod-folder said -- and the cross-folder checker then treated the user's real target as FOREIGN
    (a false collision banner on a plain redeploy). The resolved folder goes down on both paths."""
    import argparse
    from ff9mapkit import cli
    seen: dict = {}

    def fake_deploy(block, **kw):
        seen.update(kw)
        raise ValueError("stop here")                        # the handler's clean-exit branch (rc 2)
    monkeypatch.setattr(D, "deploy", fake_deploy)
    monkeypatch.setattr(cli, "_summon_block_from_args", lambda a: {"model": "x.fbx"})
    game = tmp_path / "game"
    game.mkdir()
    args = argparse.Namespace(game=str(game), mod_folder="FF9CustomMap-world", dry_run=True, arm=False)
    assert cli._cmd_summon_deploy(args) == 2
    assert seen["dry_run"] is True
    assert Path(seen["mod_root"]) == (game / "FF9CustomMap-world").resolve()
