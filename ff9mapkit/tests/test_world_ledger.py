"""The world deploy ledger + the ownership refusal at THE one write seam (audit rec 6).

Hermetic (tmp game root, synthetic meshes). The pinned invariants, most important first:
the DETERMINISM regression guard -- ledgering must never touch mesh bytes (this is the
test that would have caught an embedded-provenance-chunk design); the append-only JSONL
line per write; the ownership refusal when on-disk bytes match no ledger entry (18+
concurrent sessions share ONE install); backup-on-differing-overwrite with a name the
disc mirror and the fuse existing-overrides gate both ignore; the bootstrap permissive
case; the read-side version reject; and the stamp _META_NAMES exclusion.
"""
from __future__ import annotations

import hashlib
import json

import pytest

from ff9mapkit import stamp
from ff9mapkit.world import discmirror as DM, fuse as F, mesh as M, placement as P
from ff9mapkit.world.extract import BlockMesh, encode_id, CH_POS, CH_NRM, CH_UV, CH_TAN

GRASS = float(encode_id(topograph=0))


def _bm(y=3.2, x=5, by=7):
    corners = [(0.0, y, 0.0), (8.0, y, 0.0), (0.0, y, -8.0)]
    pos, nrm, uv, tan, flat = [], [], [], [], []
    for c in corners:
        pos.append(list(c)); nrm.append([0.0, 1.0, 0.0]); uv.append([0.0, 0.0])
        tan.append([GRASS, 0.0, 0.0, 1.0]); flat.append(len(pos) - 1)
    return BlockMesh(name=f"Block[{x}][{by}] Terrain", disc=1, x=x, y=by, lod="0_1",
                     vcount=3, stride=48,
                     channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)},
                     chan_arrays={CH_POS: pos, CH_NRM: nrm, CH_UV: uv, CH_TAN: tan},
                     flat_index=flat, tris=[[0, 1, 2]], raw_vbuf=b"", raw_ibuf=b"",
                     use32=True, submeshes=[])


def _deploy(tmp, bm, **kw):
    return M.deploy_override(bm, mod_folder="TestMod", game=tmp, **kw)


def _ledger_lines(tmp):
    p = tmp / "TestMod" / M.LEDGER_NAME
    return [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines()] if p.is_file() else []


def test_deploys_stay_byte_deterministic_and_each_write_ledgers(tmp_path):
    """THE DETERMINISM PIN: two identical deploys produce byte-identical mesh files (the
    ledger is a SIDECAR -- embedding provenance in the format is refused by design), the
    ledger gains one line per write, and identical bytes take no backup."""
    p1 = _deploy(tmp_path, _bm())
    b1 = p1.read_bytes()
    p2 = _deploy(tmp_path, _bm())
    assert p1 == p2 and p2.read_bytes() == b1
    lines = _ledger_lines(tmp_path)
    assert len(lines) == 2
    assert lines[0]["cell"] == [5, 7] and lines[0]["part"] == "Terrain"
    assert lines[0]["sha256"] == hashlib.sha256(b1).hexdigest()
    assert not list(p1.parent.glob("*.bak-*"))            # identical bytes: no backup churn


def test_differing_redeploy_backs_up_and_the_backup_is_invisible(tmp_path):
    """A legitimate re-deploy (prior bytes ARE ledgered) succeeds, parks the old bytes as
    .bak-<ts>, and that name is invisible to the disc mirror's block regex AND the fuse
    existing-overrides gate (whose bare startswith was a live hazard)."""
    p1 = _deploy(tmp_path, _bm(y=3.2))
    old = p1.read_bytes()
    p2 = _deploy(tmp_path, _bm(y=5.0))
    assert p2.read_bytes() != old
    baks = list(p2.parent.glob("*.bak-*"))
    assert len(baks) == 1 and baks[0].read_bytes() == old
    assert DM._BLOCK_RE.match(baks[0].name) is None
    hits = F._existing_overrides([(5, 7)], "TestMod", disc=1, lod="0_1", game=tmp_path)
    assert [h for h in hits if ".bak-" in h] == [] and len(hits) == 1


def test_foreign_bytes_refuse_and_force_overrides(tmp_path):
    """THE OWNERSHIP REFUSAL: on-disk bytes matching NO ledger entry belong to another
    session or a hand edit -- refuse before the damage, name the last ledger write. The
    escape hatch is explicit."""
    p1 = _deploy(tmp_path, _bm(y=3.2))
    p1.write_bytes(p1.read_bytes() + b"X")                # a hand edit / another era
    with pytest.raises(ValueError, match="match(es)? no ledger entry"):
        _deploy(tmp_path, _bm(y=5.0))
    p2 = _deploy(tmp_path, _bm(y=5.0), force_overwrite=True)
    assert p2.read_bytes() == M.ff9mesh_bytes(_bm(y=5.0))


def test_preledger_tree_is_permissive_but_still_backs_up(tmp_path):
    """Bootstrap: a deployed tree with NO ledger (every pre-rec-6 world) must not refuse --
    but the differing overwrite still parks a backup."""
    dest = tmp_path / "TestMod" / M.override_relpath(1, 5, 7, "0_1", "Terrain")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(b"F9WM" + b"\x00" * 32)              # unledgered pre-existing bytes
    p = _deploy(tmp_path, _bm())
    assert p.read_bytes() == M.ff9mesh_bytes(_bm())
    assert len(list(p.parent.glob("*.bak-*"))) == 1


def test_read_rejects_a_foreign_version(tmp_path):
    """An abandoned experiment's v2 file used to ride along silently -- now the read side
    refuses it by version, not just magic."""
    p = M.write_ff9mesh(_bm(), tmp_path / "v.ff9mesh")
    raw = bytearray(p.read_bytes())
    raw[4] = 9                                            # version int32 LE at offset 4
    p.write_bytes(bytes(raw))
    with pytest.raises(ValueError, match="version 9"):
        M.read_ff9mesh(p)


def test_ledger_name_is_meta_everywhere():
    """The _META_NAMES lesson (stamp.py): a meta file missing from the exclusion set makes
    a correct deploy report an 'extra' file. One literal, pinned across both owners."""
    assert stamp.WORLD_LEDGER_NAME == M.LEDGER_NAME
    assert M.LEDGER_NAME in stamp._META_NAMES


def test_argv_rides_the_ledger(tmp_path):
    M.set_deploy_argv(["world-terrain", "--at", "1", "2"])
    try:
        _deploy(tmp_path, _bm())
        assert _ledger_lines(tmp_path)[-1]["argv"] == ["world-terrain", "--at", "1", "2"]
    finally:
        M.set_deploy_argv([])


def test_backup_lands_in_the_target_namespace(tmp_path):
    """THE READ/WRITE DISC SPLIT law, carried into the seam backup: with disc=9 the
    compare, the backup, and the write all aim at the Disc9 namespace -- comparing or
    backing up Disc1 while writing Disc9 would back up the wrong file (the law the
    deploy_changed test pinned before the backup moved to the seam)."""
    p1 = _deploy(tmp_path, _bm(y=3.2), disc=9)
    old = p1.read_bytes()
    assert "Disc9" in p1.parts
    p2 = _deploy(tmp_path, _bm(y=5.0), disc=9)
    baks = list(p2.parent.glob("*.bak-*"))
    assert len(baks) == 1 and baks[0].read_bytes() == old
    assert "Disc9" in baks[0].parts
    d1 = tmp_path / "TestMod" / "FF9_Data" / "WorldMap" / "Disc1"
    assert not d1.exists()                                # nothing leaked into Disc1


# ---- the engine-boundary seam validation (audit rec 10 steps 1-2) ---------------------------------------------------

def _bad(**mut):
    bm = _bm()
    for k, v in mut.items():
        object.__setattr__(bm, k, v) if hasattr(type(bm), "__dataclass_fields__") else setattr(bm, k, v)
    return bm


def test_validate_blockmesh_engine_predicates_each_refuse(tmp_path):
    """One test per s34 ReadMesh predicate (transcribed verbatim; the drift test pins the
    patch's literals): a runtime-rejected override does NOT fall back to ocean on a
    reclaimed cell -- it becomes a DIFFERENT block's walkable geometry -- so nothing
    rejectable may reach a file. ValueError, not assert (the -O trapdoor)."""
    import dataclasses
    ok = _bm()
    M.validate_blockmesh(ok)                              # the control
    with pytest.raises(ValueError, match="UNINDEXED"):
        M.validate_blockmesh(dataclasses.replace(ok, flat_index=[0, 1]))
    # each fixture keeps tris coherent with flat_index -- the rec-18 dual-topology check
    # runs first and would otherwise mask the predicate under test
    with pytest.raises(ValueError, match="out of range"):
        M.validate_blockmesh(dataclasses.replace(ok, vcount=0, flat_index=[], tris=[]))
    with pytest.raises(ValueError, match="16-bit"):
        big = dataclasses.replace(ok, vcount=70002, flat_index=list(range(70002)),
                                  tris=[[i, i + 1, i + 2] for i in range(0, 70002, 3)])
        M.validate_blockmesh(big)
    with pytest.raises(ValueError, match="triangle index"):
        M.validate_blockmesh(dataclasses.replace(ok, flat_index=[0, 1, 7], tris=[[0, 1, 7]]))
    with pytest.raises(ValueError, match="divergence"):
        # the rec-18 check itself: tris says one topology, flat_index another
        M.validate_blockmesh(dataclasses.replace(ok, tris=[[0, 2, 1]]))
    with pytest.raises(ValueError, match="non-finite"):
        bad_pos = [list(v) for v in ok.chan_arrays[CH_POS] if True]
        bad_pos[1][1] = float("nan")
        ca = dict(ok.chan_arrays); ca[CH_POS] = bad_pos
        M.validate_blockmesh(dataclasses.replace(ok, chan_arrays=ca))
    # and the seam actually calls it: the write refuses too
    with pytest.raises(ValueError, match="non-finite"):
        ca2 = dict(ok.chan_arrays)
        p2 = [list(v) for v in ok.chan_arrays[CH_POS]]
        p2[0][0] = float("inf")
        ca2[CH_POS] = p2
        M.write_ff9mesh(dataclasses.replace(ok, chan_arrays=ca2), tmp_path / "x.ff9mesh")


def test_engine_patch_literals_are_pinned():
    """THE DRIFT PIN: validate_blockmesh transcribes s34 ReadMesh. If the engine side bumps
    a literal, this fails the kit's suite instead of silently voiding every deploy."""
    from pathlib import Path
    patch = (Path(__file__).resolve().parents[2] / "memoria-patches" /
             "s34-worldmap-mesh-override.patch").read_text(encoding="utf-8", errors="replace")
    assert "SupportedVersion = 1" in patch
    assert "vcount > 65535" in patch
    assert "icount > vcount * 3" in patch
    assert "idx < 0 || idx >= vcount" in patch


def test_shared_header_parser_is_the_one_owner():
    """worldscan and coastnav each carried a private header parse; both now route through
    mesh.read_ff9mesh_header."""
    p = M.write_ff9mesh(_bm(), __import__("tempfile").mkdtemp() + "/h.ff9mesh")
    ver, vcount, icount, flags = M.read_ff9mesh_header(p.read_bytes())
    assert (ver, vcount, icount) == (1, 3, 3) and flags & 4
    with pytest.raises(ValueError, match="bad magic"):
        M.read_ff9mesh_header(b"XXXX" + b"\x00" * 16)
    import inspect
    from ff9mapkit.world import coastnav as CN
    from ff9mapkit.workspace import worldscan as WS
    assert "read_ff9mesh_header" in inspect.getsource(CN._parse_header)
    assert "read_ff9mesh_header" in inspect.getsource(WS)


# --------------------------------------------------------------- THE DONOR SIDECAR'S OWN GUARD

def _sidecar(tmp, donor=(7, 17), cell=(5, 7), **kw):
    return M.deploy_donor_sidecar(donor[0], donor[1], mod_folder="TestMod", disc=1,
                                  x=cell[0], y=cell[1], game=tmp, **kw)


def test_sidecar_write_ledgers_part_Donor(tmp_path):
    """Every sidecar write appends a row keyed part="Donor" on the WRITE disc -- until 2026-08-27
    deploy_donor_sidecar was a bare write_text with no ledger, no backup, no refusal, on 177 live
    load-bearing files (Donor.txt picks the s34 divert's render prefab)."""
    p = _sidecar(tmp_path)
    assert p.read_text(encoding="utf-8") == "7,17"
    rows = _ledger_lines(tmp_path)
    assert len(rows) == 1
    assert rows[0]["cell"] == [5, 7] and rows[0]["part"] == "Donor" and rows[0]["write_disc"] == 1
    assert rows[0]["sha256"] == hashlib.sha256(b"7,17").hexdigest()


def test_sidecar_foreign_bytes_refuse_and_force_overrides(tmp_path):
    """THE OWNERSHIP REFUSAL, sidecar edition: a hand edit / another session's differing payload
    with no matching ledger row refuses BEFORE the damage; the hatch stays explicit."""
    p = _sidecar(tmp_path)
    p.write_text("9,9", encoding="utf-8")                 # foreign: matches no ledger row
    with pytest.raises(ValueError, match="match(es)? no ledger entry"):
        _sidecar(tmp_path, donor=(3, 13))
    assert p.read_text(encoding="utf-8") == "9,9"         # refused write must not have landed
    p2 = _sidecar(tmp_path, donor=(3, 13), force_overwrite=True)
    assert p2.read_text(encoding="utf-8") == "3,13"


def test_sidecar_own_redeploy_backs_up_and_passes(tmp_path):
    """A legitimate re-point (prior payload IS ledgered) succeeds and parks the old payload as
    .bak-<ts> -- a name invisible to the disc mirror's block regex and to existing_overrides'
    extension filter, so backups never masquerade as occupancy."""
    _sidecar(tmp_path, donor=(7, 17))
    p = _sidecar(tmp_path, donor=(3, 13))
    assert p.read_text(encoding="utf-8") == "3,13"
    baks = list(p.parent.glob("*Donor.txt.bak-*"))
    assert len(baks) == 1 and baks[0].read_text(encoding="utf-8") == "7,17"
    assert DM._BLOCK_RE.match(baks[0].name) is None
    hits = M.existing_overrides([(5, 7)], "TestMod", disc=1, lod="0_1", game=tmp_path)
    assert [h for h in hits if ".bak-" in h] == []


def test_sidecar_preledger_tree_is_permissive(tmp_path):
    """Bootstrap parity with the mesh seam: a pre-existing unledgered sidecar (every pre-2026-08-27
    world -- 177 live files) must not refuse; the differing overwrite still parks a backup."""
    dest = tmp_path / "TestMod" / M.donor_sidecar_relpath(1, 5, 7, "0_1")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("9,9", encoding="utf-8")              # unledgered pre-existing payload
    p = _sidecar(tmp_path, donor=(7, 17))
    assert p.read_text(encoding="utf-8") == "7,17"
    baks = list(p.parent.glob("*Donor.txt.bak-*"))
    assert len(baks) == 1 and baks[0].read_text(encoding="utf-8") == "9,9"


def test_sidecar_identical_repoint_takes_no_backup(tmp_path):
    """Re-writing the SAME payload is not an overwrite: no refusal path, no backup churn (the
    deploy loops re-run their sidecar writes on every deploy)."""
    _sidecar(tmp_path)
    p = _sidecar(tmp_path)
    assert p.read_text(encoding="utf-8") == "7,17"
    assert list(p.parent.glob("*Donor.txt.bak-*")) == []
    assert len(_ledger_lines(tmp_path)) == 2              # every write still ledgers
