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
        self.disc, self.x, self.y = disc, x, y


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
