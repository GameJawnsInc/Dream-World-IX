"""THE READ/WRITE DISC SPLIT (Path D).

A world builder's ``disc`` has always done two jobs at once: which stock tree to BORROW real bytes from, and
which override namespace to WRITE into. For the two real discs those coincide. A Path D world does not: it
keeps ``currentDisc == 1`` (so every GetDisc/vehicle/asset consumer keeps working) while resolving its per-cell
overrides against a SENTINEL namespace (engine patch s74), so its cells cannot collide with real disc-1 edits at
the same coordinates. The 56 live disc-1 override cells bleeding into world 9013 is the observed case that
motivated it.

Two invariants are pinned here:
  1. ``mesh.deploy_override`` writes to ``disc=`` when given, else to ``bm.disc`` -- and the default is
     byte-identical to the pre-split behaviour, which is what protects real disc-1/4 authoring.
  2. ``discmirror.auto_mirror`` REFUSES a synthetic source namespace. Mirroring exists to close THE DISC-4 GAP
     between the two real discs; copying sentinel cells into the real Disc4 tree would recreate exactly the
     collision the sentinel exists to prevent. Before this guard it was stopped only by accident -- a ValueError
     raised after a ~50-bundle p0data rescan, swallowed as a benign skip.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ff9mapkit.world import discmirror as DM
from ff9mapkit.world import mesh as M


class _BM:
    """Minimal BlockMesh stand-in -- deploy_override only reads .disc/.x/.y before handing off to write_ff9mesh."""
    def __init__(self, disc=1, x=5, y=5):
        self.disc, self.x, self.y, self.tris = disc, x, y, ()


def _captured_dest(monkeypatch, tmp_path, bm, **kw):
    seen = {}
    monkeypatch.setattr(M.config, "find_game_path", lambda game=None: tmp_path)
    monkeypatch.setattr(M, "write_ff9mesh", lambda b, dest: seen.setdefault("dest", dest))
    M.deploy_override(bm, mod_folder="MOD", **kw)
    return Path(seen["dest"])


# --- 1. deploy_override -------------------------------------------------------------------------------------

def test_default_writes_to_the_meshes_own_disc(monkeypatch, tmp_path):
    """No disc= -> byte-identical to before the split. This is the real-play regression guard."""
    dest = _captured_dest(monkeypatch, tmp_path, _BM(disc=1, x=5, y=5))
    assert "Disc1" in dest.parts
    assert dest.name == "Block[5][5] Terrain.ff9mesh"


def test_explicit_disc_retargets_the_write_only(monkeypatch, tmp_path):
    """disc= sends the WRITE to the sentinel namespace; the mesh still carries its READ disc unchanged."""
    bm = _BM(disc=1, x=5, y=5)
    dest = _captured_dest(monkeypatch, tmp_path, bm, disc=9)
    assert "Disc9" in dest.parts and "Disc1" not in dest.parts
    assert bm.disc == 1, "the write target must not mutate the mesh's own read disc"


def test_sentinel_and_real_cell_do_not_collide(monkeypatch, tmp_path):
    """The whole point: the same grid coords in two namespaces are two different files."""
    real = _captured_dest(monkeypatch, tmp_path, _BM(disc=1, x=5, y=5))
    path_d = _captured_dest(monkeypatch, tmp_path, _BM(disc=1, x=5, y=5), disc=9)
    assert real != path_d


def test_disc_zero_is_honoured_not_treated_as_falsy(monkeypatch, tmp_path):
    """`if disc is None`, not `if disc` -- a 0 must not silently fall back to bm.disc."""
    dest = _captured_dest(monkeypatch, tmp_path, _BM(disc=1, x=5, y=5), disc=0)
    assert "Disc0" in dest.parts


# --- 2. the discmirror foreign-namespace refusal --------------------------------------------------------------

def _auto_mirror_over(monkeypatch, written, dst_disc=4):
    calls, logged = [], []
    monkeypatch.setattr(DM, "mirror", lambda *a, **k: calls.append(k) or {"mirrored": [], "pinned": [], "skipped": []})
    DM.auto_mirror(written, mod_folder="MOD", dst_disc=dst_disc, log=logged.append)
    return calls, logged


def _p(tmp_path, disc, x, y):
    """A REAL file -- auto_mirror's EVIDENCE CONTRACT filters out anything that does not exist on disk."""
    p = tmp_path / "MOD" / "FF9_Data" / "WorldMap" / f"Disc{disc}" / "0_1" / f"r{y}" / f"Block[{x}][{y}] Terrain.ff9mesh"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"\x00")
    return p


def test_real_disc1_source_still_mirrors(monkeypatch, tmp_path):
    """The guard must not disturb the real disc-1 -> disc-4 mirror that ordinary authoring depends on."""
    calls, _ = _auto_mirror_over(monkeypatch, [_p(tmp_path, 1, 5, 5)])
    assert len(calls) == 1 and calls[0]["src_disc"] == 1


def test_sentinel_source_is_refused(monkeypatch, tmp_path):
    """A Path D write must never be copied into the real Disc4 tree."""
    calls, logged = _auto_mirror_over(monkeypatch, [_p(tmp_path, 9, 5, 5)])
    assert calls == [], "mirror() must not be reached for a synthetic namespace"
    assert any("refused" in m.lower() for m in logged), f"the refusal must be logged, got {logged}"


def test_mixed_write_set_mirrors_real_and_refuses_synthetic(monkeypatch, tmp_path):
    """A build that touched both namespaces must not be all-or-nothing."""
    calls, _ = _auto_mirror_over(monkeypatch, [_p(tmp_path, 1, 5, 5), _p(tmp_path, 9, 6, 6)])
    assert [c["src_disc"] for c in calls] == [1]


# --- 3. the interior verbs (world-forest / world-hill / world-mountain) ---------------------------------------
# These work ON the deployed island, so like terrain.reshape the READ moves with target_disc too:
# a Disc1 read would hand the carve real disc-1 land while the caller believes it is on a synthetic world.

def test_read_deployed_blocks_reads_the_target_namespace(monkeypatch, tmp_path):
    from ff9mapkit import config
    from ff9mapkit.world import interior as IN
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    seen = []
    monkeypatch.setattr(IN.M, "blockmesh_from_ff9mesh",
                        lambda p, **kw: seen.append((Path(p), kw)) or object())
    _p(tmp_path, 9, 5, 5)                                    # the synthetic island's override
    _p(tmp_path, 1, 5, 5)                                    # a REAL disc-1 override at the same coords
    out = IN.read_deployed_blocks("MOD", near=(64.0 * 5 + 32, -(64.0 * 5) - 32), reach=10.0,
                                  disc=1, target_disc=9)
    assert (5, 5) in out and len(seen) == 1
    assert "Disc9" in seen[0][0].parts and seen[0][1]["disc"] == 9


def test_read_deployed_blocks_default_is_unchanged(monkeypatch, tmp_path):
    from ff9mapkit import config
    from ff9mapkit.world import interior as IN
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    seen = []
    monkeypatch.setattr(IN.M, "blockmesh_from_ff9mesh",
                        lambda p, **kw: seen.append(Path(p)) or object())
    _p(tmp_path, 1, 5, 5)
    IN.read_deployed_blocks("MOD", near=(64.0 * 5 + 32, -(64.0 * 5) - 32), reach=10.0, disc=1)
    assert "Disc1" in seen[0].parts


def test_deploy_changed_compares_and_writes_in_the_same_namespace(monkeypatch, tmp_path):
    """The byte-compare/backup root and the write must aim at ONE namespace: comparing against
    Disc1 while writing Disc9 would defeat the converge check and back up the wrong file."""
    from ff9mapkit import config
    from ff9mapkit.world import interior as IN
    from ff9mapkit.world import discmirror as DM
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    dep9 = _p(tmp_path, 9, 5, 5)                             # existing Disc9 override, stale bytes
    seen = {}
    monkeypatch.setattr(IN.M, "write_ff9mesh",
                        lambda bm, dest: (dest.write_bytes(b"NEW"), dest)[1])

    def fake_deploy(bm, **kw):
        seen["disc"] = kw.get("disc")
        return dep9

    monkeypatch.setattr(IN.M, "deploy_override", fake_deploy)
    monkeypatch.setattr(DM, "auto_mirror", lambda *a, **k: None)
    out = IN.deploy_changed({(5, 5): _BM(disc=9, x=5, y=5)}, mod_folder="MOD",
                            disc=1, target_disc=9, backup=True)
    assert seen["disc"] == 9, "the write must land in the target namespace"
    assert out, "stale Disc9 bytes must be seen as a CHANGE (the compare read the target file)"
    # the pre-write backup moved to THE one write seam (deploy_override, audit rec 6) --
    # its in-the-TARGET-namespace law is pinned by
    # test_world_ledger.py::test_backup_lands_in_the_target_namespace


# --- 4. fuse_layout threads the split into its engine and its collision pre-check -----------------------------

def test_fuse_layout_collision_precheck_scans_the_target_namespace(monkeypatch, tmp_path):
    from ff9mapkit.world import fuse as FU
    monkeypatch.setattr(FU.config, "find_game_path", lambda game=None: tmp_path)
    _p(tmp_path, 9, 7, 7)
    hits9 = FU._existing_overrides([(7, 7)], "MOD", disc=9, lod="0_1")
    hits1 = FU._existing_overrides([(7, 7)], "MOD", disc=1, lod="0_1")
    assert hits9 and not hits1


def test_fuse_layout_threads_target_disc_into_every_transplant_call(monkeypatch, tmp_path):
    from ff9mapkit.world import fuse as FU
    from ff9mapkit.world import discmirror as DM
    calls = []

    def fake_region(mod_folder, **kw):
        calls.append((mod_folder, kw))
        return {"donor": [0, 0], "cell": list(kw["cell"]), "rot": 0, "shift": [0, 0],
                "size": [1, 1], "tsize": [1, 1], "gates": [], "clean": True,
                "frame_profile": {}, "deployed": ["x"], "dry_run": kw.get("dry_run", False)}

    monkeypatch.setattr(FU.TR, "transplant_region", fake_region)
    monkeypatch.setattr(FU.config, "find_game_path", lambda game=None: tmp_path)
    monkeypatch.setattr(DM, "auto_mirror", lambda *a, **k: None)
    FU.fuse_layout("MOD", [{"cell": (7, 7), "donor": (0, 0), "size": (1, 1)}],
                   disc=1, target_disc=9, all_sea_target=True)
    assert len(calls) == 2, "the gate pass and the deploy pass must both run"
    for _mf, kw in calls:
        assert kw["disc"] == 1, "the stock read disc must stay put"
        assert kw["target_disc"] == 9 and kw["all_sea_target"] is True
