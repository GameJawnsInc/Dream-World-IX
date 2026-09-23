"""A fork's donor MapConfigData (MCF) -- shipped by EDITABLE and BG-borrow forks too, re-keyed through a
reshaped walkmesh.

The engine lights and shadows every field actor from the field's MCF (``fldmcf.ff9fieldMCFService``: the
model's row + the light of the floor it stands on). An ``import --editable`` fork, and a plain (BG-borrow)
``import``, used to ship none, so the build's census shadow ops (content.shadow) reached its player and
``[[npc]]``s but never its grafted ``[[object]]``s, and nothing tinted any model. Both now ship the donor MCF
exactly as a native fork does -- a borrow always verbatim, since the engine runs it on the donor's own .bgi.

THE INVARIANT pinned here: shipping the MCF changes an editable or borrow fork's build by EXACTLY the MCF file
plus the kit shadow ops it retires (the MCF shadows every actor itself). Every other file is byte-identical,
and the grafted objects' bytes never change. The per-floor lights follow their floors through a reshape that
renumbers them. All bytes here are authored; the build half is template-gated like tests/test_shadow.py.
"""
from __future__ import annotations

import json
import struct

import pytest

from ff9mapkit import build, data, eventscan, extract, mapconfig
from ff9mapkit.config import ModLayout
from ff9mapkit.content import prop as _prop
from ff9mapkit.eb import EbScript
from ff9mapkit.scene import bgi

from .test_shadow import _assert_only_shadow_ops_added

FLOOR, DEFAULT, LADDER = mapconfig.LIGHT_FLOOR, mapconfig.LIGHT_DEFAULT, mapconfig.LIGHT_LADDER


def _mcf(lights, chars=((0xFFFF, 3, 9),), *, light_use=None) -> bytes:
    """An authored MCF: ``lights`` = ``(type, shadowI, shadowR, (clr x4), (floor x4))``."""
    b = struct.pack("<HHHBBBBBB", 0, 1, 0, len(lights), len(lights) if light_use is None else light_use,
                    len(chars), len(chars), 0, 0)
    for t, si, sr, clr, fl in lights:
        b += struct.pack("<4b", t, 0, si, sr) + struct.pack("<4b", *clr) + struct.pack("<4b", *fl)
    for geo, si, sr in chars:
        b += struct.pack("<Hbb", geo, si, sr) + bytes([4, 5, 6, 0])
    return b


U = mapconfig.FLOOR_UNUSED
LIGHTS = [(FLOOR, 1, 0, (2, 2, 2, 0), (0, 1, U, U)),       # floors 0+1 share a light
          (FLOOR, 2, 1, (-3, -3, -3, 0), (2, U, U, U)),    # floor 2 has its own
          (DEFAULT, 0, 0, (0, 0, 0, 0), (1, 2, 3, 4)),     # type 1/2 floor bytes are never read: kept
          (LADDER, 0, 0, (0, 0, 0, 0), (0, 0, 0, 0))]


# ---- mapconfig.remap_light_floors ------------------------------------------------------------------------

def test_remap_identity_is_byte_identical():
    raw = _mcf(LIGHTS)
    assert mapconfig.remap_light_floors(raw, {0: 0, 1: 1, 2: 2}) == raw


def test_remap_rekeys_only_the_per_floor_lights():
    raw = _mcf(LIGHTS)
    out = mapconfig.remap_light_floors(raw, {0: 0, 2: 1})         # floor 1 deleted: floor 2 is now floor 1
    assert len(out) == len(raw)
    a, b = mapconfig.parse(raw), mapconfig.parse(out)
    assert b.lights[0].floor == (0, U, U, U)                      # its floor-1 share is gone, not re-pointed
    assert b.lights[1].floor == (1, U, U, U)                      # follows its floor
    assert b.lights[2:] == a.lights[2:]                           # default + ladder lights untouched
    assert (b.chars, b.attr, b.light_use, b.char_use) == (a.chars, a.attr, a.light_use, a.char_use)
    # outside the two rewritten light-floor quads, not one byte moved
    diff = [i for i in range(len(raw)) if raw[i] != out[i]]
    assert diff and all(12 + 8 <= i < 12 + 12 or 24 + 8 <= i < 24 + 12 for i in diff), diff


def test_lit_floors_reads_only_used_floor_lights():
    assert mapconfig.lit_floors(_mcf(LIGHTS)) == {0, 1, 2}
    assert mapconfig.lit_floors(_mcf(LIGHTS, light_use=1)) == {0, 1}


# ---- bgi.obj_built_floor_donors: the donor floor behind each BUILT floor ---------------------------------

def _quad(x):
    return [(x, 0, 0), (x + 100, 0, 0), (x + 100, 0, 100), (x, 0, 100)]


def _obj(tmp_path, names, fn="wm.obj"):
    """One quad per floor, written in ``names`` order (None = the flat re-export: no ``o`` line)."""
    L, v = [], 0
    for k, n in enumerate(names):
        L += [f"v {x} {y} {z}" for x, y, z in _quad(200 * k)]
        if n is not None:
            L.append(f"o {n}")
        L += [f"f {v + 1} {v + 2} {v + 3}", f"f {v + 1} {v + 3} {v + 4}"]
        v += 4
    p = tmp_path / fn
    p.write_text("\n".join(L) + "\n", encoding="utf-8")
    return p


@pytest.mark.parametrize("names, donors", [
    (["floor_0", "floor_1", "floor_2"], [0, 1, 2]),                # the unedited round-trip
    (["floor_0", "floor_2"], [0, 2]),                              # floor 1 deleted -> renumbered
    (["floor_2", "floor_0", "floor_1"], [2, 0, 1]),                # reordered
    (["floor_0", "balcony", "floor_2"], [0, None, 2]),             # an authored floor names no donor
    ([None], [0]),                                                 # single-floor flat re-export
])
def test_obj_built_floor_donors(tmp_path, names, donors):
    p = _obj(tmp_path, names)
    assert bgi.obj_built_floor_donors(str(p)) == donors
    # ...and the list is indexed by the floor bgi.build really gives each face
    verts, faces, fids = bgi.load_obj_floors(str(p))
    assert len(bgi.build(verts, faces, floor_ids=fids).floors) == len(donors)


def test_the_editable_reexport_keeps_every_floor_index(tmp_path):
    # extract._world_walkmesh_obj_text is what `import --editable` writes; census: identity on all 816
    # shipping walkmeshes. Pinned here on a floor order that is NOT ascending in the tri list.
    wm = bgi.build(_quad(0) + _quad(200) + _quad(400),
                   [(0, 1, 2), (0, 2, 3), (4, 5, 6), (4, 6, 7), (8, 9, 10), (8, 10, 11)],
                   floor_ids=[0, 0, 1, 1, 2, 2])
    p = tmp_path / "wm.obj"
    p.write_text(extract._world_walkmesh_obj_text(wm), encoding="utf-8")
    assert bgi.obj_built_floor_donors(str(p)) == [0, 1, 2]


# ---- build.mapconfig_bytes: what the build ships ---------------------------------------------------------

def _proj(tmp_path, walkmesh: str, *, mapconfig_key=True):
    (tmp_path / "mapconfig.bytes").write_bytes(_mcf(LIGHTS))
    p = tmp_path / "f.field.toml"
    p.write_text('[field]\nid=30990\nname="EDM"\narea=21\ntext_block=30990\n'
                 + ('mapconfig = "mapconfig.bytes"\n' if mapconfig_key else "")
                 + '[camera]\npitch=30\ndistance=900\nfov=40\n' + walkmesh, encoding="utf-8")
    return build.FieldProject.load(p)


def test_no_mapconfig_ships_nothing(tmp_path):
    assert build.mapconfig_bytes(_proj(tmp_path, "", mapconfig_key=False)) is None


def test_a_verbatim_bgi_ships_the_mcf_verbatim(tmp_path):
    (tmp_path / "walkmesh.bgi").write_bytes(bgi.build(_quad(0), [(0, 1, 2), (0, 2, 3)]).to_bytes())
    assert build.mapconfig_bytes(_proj(tmp_path, '[walkmesh]\nbgi="walkmesh.bgi"\n')) == _mcf(LIGHTS)


def test_an_unrenumbered_reshape_ships_the_mcf_verbatim(tmp_path):
    _obj(tmp_path, ["floor_0", "floor_1", "floor_2"])
    w = []
    assert build.mapconfig_bytes(_proj(tmp_path, '[walkmesh]\nobj="wm.obj"\n'), w) == _mcf(LIGHTS)
    assert w == []


def test_a_renumbering_reshape_rekeys_the_lights_and_says_what_it_dropped(tmp_path):
    _obj(tmp_path, ["floor_0", "floor_2"])                        # floor 1 deleted
    w = []
    out = build.mapconfig_bytes(_proj(tmp_path, '[walkmesh]\nobj="wm.obj"\n'), w)
    lights = mapconfig.parse(out).lights
    assert (lights[0].floor, lights[1].floor) == ((0, U, U, U), (1, U, U, U))   # floor 2's light -> built floor 1
    assert len(w) == 1 and "[1]" in w[0]
    build.mapconfig_bytes(_proj(tmp_path, '[walkmesh]\nobj="wm.obj"\n'), w)
    assert len(w) == 1                                            # per-language rebuilds warn once


@pytest.mark.parametrize("walkmesh", ['[walkmesh]\nreference="walkmesh.bgi"\n',   # what `import` writes
                                      '[walkmesh]\nobj="wm.obj"\n'])               # a stray renumbering .obj
def test_a_borrow_fork_ships_the_mcf_verbatim_whatever_its_walkmesh_says(tmp_path, walkmesh):
    # a BG-borrow ships no walkmesh: the engine runs it on the donor's own .bgi, so the lights key exactly
    _obj(tmp_path, ["floor_0", "floor_2"])                        # would renumber, if it were ever built
    p = tmp_path / "b.field.toml"
    p.write_text('[field]\nid=30990\nname="BOR"\narea=34\nborrow_bg="MDSR_MAP579_MS_KTN_0"\ntext_block=30990\n'
                 'mapconfig = "mapconfig.bytes"\n[camera]\npitch=30\ndistance=900\nfov=40\n' + walkmesh,
                 encoding="utf-8")
    (tmp_path / "mapconfig.bytes").write_bytes(_mcf(LIGHTS))
    w = []
    assert build.mapconfig_bytes(build.FieldProject.load(p), w) == _mcf(LIGHTS)
    assert w == []


def test_validate_flags_a_missing_mapconfig_on_any_scene(tmp_path):
    p = tmp_path / "f.field.toml"
    p.write_text('[field]\nid=30990\nname="EDM"\narea=21\ntext_block=30990\nmapconfig="nope.bytes"\n'
                 '[camera]\npitch=30\ndistance=900\nfov=40\n', encoding="utf-8")
    assert any("mapconfig" in s for s in build.validate(build.FieldProject.load(p)))


# ---- THE INVARIANT: a fork with vs without its donor MCF (template-gated) --------------------------------

# the scene half of each fork shape: what `import --editable` writes (a custom scene -- per-depth [[layers]],
# the donor walkmesh as a verbatim .bgi) and what a plain `import` writes (BG-borrow -- the donor's own art,
# walkmesh and camera; the .bgi is a validation reference only, never shipped)
_SCENES = {
    "editable": ('area=21\n', '[walkmesh]\nbgi = "walkmesh.bgi"\n[[layers]]\nimage = "layer_0.png"\nz = 100\n'),
    "borrow": ('area=34\nborrow_bg = "MDSR_MAP579_MS_KTN_0"\n', '[walkmesh]\nreference = "walkmesh.bgi"\n'),
}


def _fork(root, *, with_mcf: bool, scene: str = "editable"):
    """A fork of ``scene``'s shape: the donor walkmesh (an authored 2-floor .bgi), the player, a kit [[npc]],
    and a grafted [[object]] -- its entry bytes a kit-authored prop, so no game data -- with or without
    `[field] mapconfig`."""
    field, scene_toml = _SCENES[scene]
    root.mkdir()
    wm = bgi.build(_quad(-300) + _quad(0), [(0, 1, 2), (0, 2, 3), (4, 5, 6), (4, 6, 7)],
                   floor_ids=[0, 0, 1, 1])
    (root / "walkmesh.bgi").write_bytes(wm.to_bytes())
    (root / "layer_0.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)
    (root / "mapconfig.bytes").write_bytes(_mcf(LIGHTS, chars=((0xFFFF, 3, 9), (133, 2, 11))))
    spec = eventscan.scan_objects_verbatim(
        _prop.inject_prop(data.blank_field_bytes("us"), -250, 50, model=133, pose=1872))[0]
    (root / "EDM.object0.bin").write_bytes(spec["entry_bytes"])
    toml = ('[field]\nid=30990\nname="EDM"\n' + field + 'text_block=30990\n'
            + ('mapconfig = "mapconfig.bytes"\n' if with_mcf else "")
            + '[camera]\npitch=30\ndistance=900\nfov=40\n'
            + scene_toml
            + '[player]\nspawn = [-150, 50]\n'
            '[[npc]]\nname = "a"\nmodel = "GEO_NPC_F0_CSO"\npos = [50, 50]\ndialogue = "hi"\n\n'
            + extract._object_block(spec, "EDM.object0.bin") + "\n")
    (root / "EDM.field.toml").write_text(toml, encoding="utf-8")
    return build.FieldProject.load(root / "EDM.field.toml"), spec


def _tree(out):
    return {p.relative_to(out).as_posix(): p.read_bytes() for p in out.rglob("*") if p.is_file()}


def _object_entry(ebb: bytes, spec) -> bytes:
    back = [o for o in eventscan.scan_objects_verbatim(ebb) if o["model_id"] == spec["model_id"]]
    assert len(back) == 1
    return eventscan._entry_bytes(ebb, back[0]["donor_idx"])


@pytest.mark.parametrize("scene", sorted(_SCENES))
def test_the_donor_mcf_changes_a_fork_by_exactly_the_file_and_the_retired_shadow_ops(
        tmp_path, monkeypatch, scene):
    on_p, spec = _fork(tmp_path / "on", with_mcf=True, scene=scene)
    off_p, _ = _fork(tmp_path / "off", with_mcf=False, scene=scene)
    assert build.validate(on_p) == [] and build.validate(off_p) == []
    build.build_mod([on_p], tmp_path / "out_on", mod_name="M")
    build.build_mod([off_p], tmp_path / "out_off", mod_name="M")
    on, off = _tree(tmp_path / "out_on"), _tree(tmp_path / "out_off")

    # 1. ON ships the donor MCF, byte for byte, under the fork's event name; OFF ships none
    mcf = ModLayout(tmp_path / "out_on").mapconfig_path("EVT_EDM").relative_to(tmp_path / "out_on").as_posix()
    assert on.pop(mcf) == (tmp_path / "on" / "mapconfig.bytes").read_bytes()
    assert mcf not in off
    # 2. every other file is the same file with the same bytes -- except the .eb, below, and the build
    #    stamp, whose per-file hash table must then differ by exactly those same files
    assert set(on) == set(off)
    ebs = sorted(k for k in on if k.endswith("EVT_EDM.eb.bytes"))
    stamp = ".ff9build.json"
    assert ebs and all(on[k] == off[k] for k in on if k not in ebs and k != stamp)
    fon, foff = (json.loads(t[stamp])["files"] for t in (on, off))
    assert fon.pop(mcf) and mcf not in foff
    assert {k for k in fon if fon[k] != foff.get(k)} == set(ebs) and set(fon) == set(foff)
    if scene == "borrow":                  # ...a borrow still ships no scene of its own: the donor's renders
        assert not any(k.endswith((".bgx", ".bgi.bytes", ".png")) for k in on), sorted(on)
    for k in ebs:
        # 3. the OFF .eb = the ON .eb + exactly the kit shadow ops on the player and the [[npc]] ...
        _assert_only_shadow_ops_added(on[k], off[k], actors=2)
        # 4. ... and the grafted object carries NONE either way -- the MCF, not the script, shadows it --
        #    its entry byte-identical to the donor's in both builds
        assert _object_entry(on[k], spec) == _object_entry(off[k], spec) == spec["entry_bytes"]
    # 5. the ON .eb IS the OFF build with its script shadows forced off: the MCF retires them and nothing else
    with monkeypatch.context() as m:
        m.setattr(build, "_casts_stock_shadows", lambda p, w=None: False)
        build.build_mod([off_p], tmp_path / "out_forced", mod_name="M")
    forced = _tree(tmp_path / "out_forced")
    assert all(on[k] == forced[k] for k in ebs)


def test_a_native_fork_still_ships_its_mcf_verbatim_and_no_shadow_ops(tmp_path):
    # the native path's contract, unchanged by the move out of the native branch
    proj = tmp_path / "p"
    proj.mkdir()
    (proj / "scene.bgs.bytes").write_bytes(b"BGS")
    (proj / "atlas.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)
    (proj / "mapconfig.bytes").write_bytes(_mcf(LIGHTS))
    (proj / "walkmesh.bgi").write_bytes(bgi.build(_quad(0), [(0, 1, 2), (0, 2, 3)]).to_bytes())
    (proj / "n.field.toml").write_text(
        '[field]\nid = 30990\nname = "NAT"\narea = 11\ntext_block = 30990\n'
        'bgs = "scene.bgs.bytes"\natlas = "atlas.png"\nmapconfig = "mapconfig.bytes"\n\n'
        '[camera]\npitch = 45\nfov = 42.2\n\n[walkmesh]\nbgi = "walkmesh.bgi"\n\n[player]\nspawn = [50, 50]\n',
        encoding="utf-8")
    build.build_mod([build.FieldProject.load(proj / "n.field.toml")], tmp_path / "mod", mod_name="M")
    lay = ModLayout(tmp_path / "mod")
    assert lay.mapconfig_path("EVT_NAT").read_bytes() == _mcf(LIGHTS)
    eb = EbScript.from_bytes(lay.eb_path("us", "EVT_NAT.eb.bytes").read_bytes())
    assert not any(i.op in (0x81, 0x85) for e in eb.entries if not e.empty for f in e.funcs
                   for i in eb.instrs(f))


# ---- the importer (install-gated) ------------------------------------------------------------------------

def _game_ready():
    try:
        import UnityPy  # noqa: F401
        from ff9mapkit import config
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_editable_import_ships_the_donor_mcf(tmp_path):
    field = "fbg_n08_udft_map122_uf_sto_0"                        # Dali storage room: the object-carry field
    meta, toml = extract.write_editable_project(field, tmp_path, field_id=30990)
    assert meta["mapconfig"] is True
    assert (tmp_path / "mapconfig.bytes").read_bytes() == extract.extract_mapconfig(field)
    proj = build.FieldProject.load(toml)
    assert proj.field["mapconfig"] == "mapconfig.bytes"
    assert proj.raw.get("object"), "the fork carries the donor's objects"
    assert build._casts_stock_shadows(proj) is False                 # the MCF owns every actor's shadow


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_borrow_import_ships_the_donor_mcf(tmp_path):
    # a plain `import` (BG-borrow) carries the donor's objects too -- the Madain Sari kitchen's moogles and
    # pots -- so it ships the donor MCF, verbatim: the engine runs a borrow on the donor's own .bgi
    field = "1607"                                                # area 34: borrowable; rung 1's donor
    meta, toml = extract.write_field_project(field, tmp_path / "f", name="KTB", field_id=30990)
    donor = extract.extract_mapconfig(field)
    assert donor and meta["mapconfig"] is True
    assert (tmp_path / "f" / "mapconfig.bytes").read_bytes() == donor
    proj = build.FieldProject.load(toml)
    assert proj.field["mapconfig"] == "mapconfig.bytes" and proj.field["borrow_bg"]
    assert proj.raw.get("object"), "the fork carries the donor's objects"
    assert build._casts_stock_shadows(proj) is False                 # the MCF owns every actor's shadow
    out = tmp_path / "mod"
    build.build_mod([proj], out, mod_name="M")
    assert ModLayout(out).mapconfig_path("EVT_KTB").read_bytes() == donor
