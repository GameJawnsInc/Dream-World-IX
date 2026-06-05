"""Compile a declarative ``field.toml`` project into a Memoria mod folder.

One ``field.toml`` describes one field; a mod is one or more of them sharing a mod root. The
builder turns a project into:
  * the background scene  FieldMaps/<FBG>/<FBG>.bgx + overlay PNGs + <FBG>.bgi.bytes (walkmesh)
  * the event script      field/<lang>/EVT_<name>.eb.bytes  (all languages), built from the
                          blank field by the content injectors
  * dialogue text         FF9_Data/embeddedasset/text/<lang>/field/<textBlock>.mes
  * registration          a DictionaryPatch FieldScene line, BattlePatch (if encounters),
                          and ModDescription.xml

See docs/FORMAT.md for the schema. The whole build is offline and deterministic, so it can be
validated by diffing against known-good assets before ever launching the game.
"""

from __future__ import annotations

import math
import shutil
import tomllib
from dataclasses import dataclass, field as _dc_field
from pathlib import Path

from .config import LANGS, ModLayout, fbg_name
from .content import camera as _camera
from .content import encounter as _enc
from .content import gateway as _gw
from .content import movement as _movement
from .content import music as _music
from .content import npc as _npc
from .content import reinit as _reinit
from .content import text as _text
from . import data as _data
from .scene import bgi, bgx, cam, guide


class BuildError(RuntimeError):
    pass


# --------------------------------------------------------------------------- project model

@dataclass
class FieldProject:
    raw: dict
    base_dir: Path

    @classmethod
    def load(cls, toml_path) -> "FieldProject":
        p = Path(toml_path)
        with p.open("rb") as fh:
            return cls(tomllib.load(fh), p.parent)

    # convenience accessors
    @property
    def field(self) -> dict:
        return self.raw.get("field", {})

    @property
    def id(self) -> int:
        return int(self.field["id"])

    @property
    def name(self) -> str:
        return self.field["name"]

    @property
    def area(self) -> int:
        return int(self.field["area"])

    @property
    def text_block(self) -> int:
        return int(self.field.get("text_block", 1073))

    @property
    def fbg(self) -> str:
        return fbg_name(self.area, self.name)

    def path(self, rel: str) -> Path:
        return (self.base_dir / rel).resolve()


# --------------------------------------------------------------------------- validation

def validate(project: FieldProject) -> list[str]:
    """Return a list of human-readable problems (empty => OK)."""
    problems = []
    f = project.field
    for key in ("id", "name", "area"):
        if key not in f:
            problems.append(f"[field] missing required key '{key}'")
    if "area" in f and int(f["area"]) < 10:
        problems.append(f"[field] area must be >= 10 (got {f['area']}); single-digit areas black-screen")
    cam_cfg = project.raw.get("camera", {})
    if not cam_cfg:
        problems.append("[camera] section is required")
    elif "borrow" not in cam_cfg and "pitch" not in cam_cfg:
        problems.append("[camera] needs either 'borrow' or 'pitch' (+ distance/fov)")
    wm = project.raw.get("walkmesh", {})
    if wm.get("obj") and not project.path(wm["obj"]).is_file():
        problems.append(f"[walkmesh] obj not found: {wm['obj']}")
    if wm.get("bgi") and not project.path(wm["bgi"]).is_file():
        problems.append(f"[walkmesh] bgi not found: {wm['bgi']}")
    if wm.get("links") and not project.path(wm["links"]).is_file():
        problems.append(f"[walkmesh] links not found: {wm['links']}")
    if wm.get("reference") and not project.path(wm["reference"]).is_file():
        problems.append(f"[walkmesh] reference not found: {wm['reference']}")
    for layer in project.raw.get("layers", []):
        if "image" not in layer:
            problems.append("[[layers]] entry missing 'image'")
        elif not project.path(layer["image"]).is_file():
            problems.append(f"[[layers]] image not found: {layer['image']}")
    for gw in project.raw.get("gateway", []):
        z = gw.get("zone", [])
        if len(z) not in (4, 5):
            problems.append(f"[[gateway]] zone must have 4 or 5 points (got {len(z)})")
    return problems


# --------------------------------------------------------------------------- scene assembly

def is_scrolling(project: FieldProject) -> bool:
    """True if the field is a larger-than-screen scrolling room ([camera.scroll] enabled)."""
    return bool(project.raw.get("camera", {}).get("scroll", {}).get("enabled"))


def resolve_camera(project: FieldProject) -> cam.Cam:
    c = project.raw["camera"]
    if "borrow" in c:
        cams = cam.parse_bgx_cameras(str(project.path(c["borrow"])))
        if not cams:
            raise BuildError(f"no CAMERA in borrowed scene {c['borrow']}")
        return cams[0]
    range_wh = tuple(c.get("range", (384, 448)))
    # viewport: explicit wins; else auto scroll bounds (span the painting) for a scrolling field;
    # else the static single-screen default.
    if "viewport" in c:
        viewport = tuple(c["viewport"])
    elif is_scrolling(project):
        viewport = cam.scroll_bounds(range_wh)
    else:
        viewport = guide.DEFAULT_VIEWPORT
    common = dict(
        yaw_deg=float(c.get("yaw", 0)), range_wh=range_wh,
        depth_offset=int(c.get("depth_offset", guide.DEFAULT_DEPTH_OFFSET)),
        viewport=viewport, center_offset=tuple(c.get("center_offset", (0, 0))),
    )
    pitch, dist = float(c["pitch"]), float(c.get("distance", 4500))
    # focal length: an explicit `proj` wins; else FOV measured at `window_width` (the visible screen
    # width for a scrolling field — default = the painting width, so normal fields are unchanged).
    # This decouples the focal length from a wide Range (a 768-wide painting must not double the FOV).
    if "proj" in c:
        return guide.make_camera(pitch, dist, proj=int(c["proj"]), **common)
    fov = float(c.get("fov", 42.2))
    win_w = int(c.get("window_width", range_wh[0]))
    if win_w != range_wh[0]:
        return guide.make_camera(pitch, dist, proj=guide.proj_from_fov_x(fov, win_w), **common)
    return guide.make_camera(pitch, dist, fov_x_deg=fov, **common)


def _shift_toward_camera(corners, camera: cam.Cam, dist: float):
    """Slide flat-floor corners `dist` world-units toward the camera (in the xz-plane).

    Used to apply the CHARACTER_GROUND_OFFSET so a 3D-rendered character looks planted on the
    2D-projected painted floor (see cam.CHARACTER_GROUND_OFFSET_Z). dist=0 is a no-op (identity).
    """
    pts = [(c[0], 0, c[1]) if len(c) == 2 else tuple(c) for c in corners]
    if not dist:
        return pts
    C = cam.decompose(camera)["C"]
    cx = sum(p[0] for p in pts) / len(pts)
    cz = sum(p[2] for p in pts) / len(pts)
    dx, dz = C[0] - cx, C[2] - cz
    n = math.hypot(dx, dz)
    if n < 1e-6:
        return pts
    ux, uz = dx / n, dz / n
    return [(p[0] + ux * dist, p[1], p[2] + uz * dist) for p in pts]


def _read_links(links_path):
    """Parse a walkmesh.links.toml adjacency sidecar -> (seams, header). Seams in the shape
    `BgiWalkmesh.apply_seams` expects: (a_floor, a_edge, b_floor, b_edge), each edge a sorted pair of
    (x,y,z) tuples (matching the WORLD-position keys extract_seams emits)."""
    with open(links_path, "rb") as fh:
        d = tomllib.load(fh)
    seams = []
    for s in d.get("seam", []):
        a = tuple(sorted(tuple(int(c) for c in p) for p in s["a_edge"]))
        b = tuple(sorted(tuple(int(c) for c in p) for p in s["b_edge"])) if s.get("b_edge") else None
        seams.append((int(s["a_floor"]), a, int(s.get("b_floor", s["a_floor"])), b))
    return seams, d.get("header", {})


def _apply_links(mesh, links_path, warnings):
    """Reconcile cross-floor seams (+ restore header) onto a freshly (re)built multi-floor walkmesh."""
    seams, header = _read_links(links_path)
    linked, missing, misses = mesh.apply_seams(seams)
    if "active_floor" in header:
        mesh.activeFloor = int(header["active_floor"])
    if "active_tri" in header:
        mesh.activeTri = int(header["active_tri"])
    cp = header.get("char_pos")
    if cp and len(cp) == 3:
        mesh.charPos = bgi.Vec3(int(cp[0]), int(cp[1]), int(cp[2]))
    if missing and warnings is not None:
        fa, a_edge, fb, _ = misses[0]
        warnings.append(
            f"walkmesh: {missing} of {linked + missing} cross-floor seam(s) couldn't be matched "
            f"(a connecting edge was moved/deleted, e.g. floor {fa}<->{fb} near {a_edge[0]}). "
            f"Re-anchor it in the .obj or restore [walkmesh] bgi (docs/WALKMESH_EDITING.md).")


def _borrow_walkmesh(project: FieldProject):
    """The real walkmesh a BG-borrow fork runs on, for content validation ONLY (never shipped). Uses
    `[walkmesh] reference` if set, else the sibling `walkmesh.bgi` the importer wrote next to the
    field.toml. Returns a BgiWalkmesh, or None if neither is present (hand-written borrow toml)."""
    ref = project.raw.get("walkmesh", {}).get("reference")
    p = project.path(ref) if ref else (project.base_dir / "walkmesh.bgi")
    return bgi.BgiWalkmesh.from_bytes(p.read_bytes()) if p.is_file() else None


def _validate_content_placement(project: FieldProject, wmesh, warnings: list) -> None:
    """Warn when authored content sits OFF the walkable area -- the recurring in-game mistake (an NPC
    floats / the player can't reach a trigger / spawns off the floor). Top-down XZ point-in-walkmesh
    test. Custom-scene only (where the kit has the walkmesh); a warning, never a hard error."""
    def off(x, z):
        return wmesh.point_on_walkmesh(int(round(x)), int(round(z))) is None
    for i, n in enumerate(project.raw.get("npc", [])):
        p = n.get("pos")
        if p and off(p[0], p[1]):
            warnings.append(
                f"NPC {n.get('name', f'#{i}')!r} at ({int(p[0])}, {int(p[1])}) is off the walkmesh -- "
                f"it will float / be unreachable. Move it onto the walkable area.")
    sp = project.raw.get("player", {}).get("spawn")
    if sp and off(sp[0], sp[1]):
        warnings.append(
            f"player spawn ({int(sp[0])}, {int(sp[1])}) is off the walkmesh -- you'll start off the floor.")
    for gw in project.raw.get("gateway", []):
        zone = gw.get("zone", [])
        if zone:
            cx, cz = sum(p[0] for p in zone) / len(zone), sum(p[1] for p in zone) / len(zone)
            if off(cx, cz):
                warnings.append(
                    f"gateway -> field {gw.get('to')}: zone centre ({int(cx)}, {int(cz)}) is off the "
                    f"walkmesh -- the player may not be able to reach the trigger.")


def resolve_walkmesh(project: FieldProject, camera: cam.Cam, warnings=None) -> bytes:
    wm = project.raw.get("walkmesh", {})
    if wm.get("bgi"):
        # ship a pre-built .bgi verbatim (e.g. an imported real field's walkmesh). This PRESERVES its
        # exact floors + neighbor/edge connectivity -- a multi-floor obj->build would rebuild links by
        # shared vertex index and disconnect floors that use disjoint vertex sets (stairs/tunnels).
        return project.path(wm["bgi"]).read_bytes()
    # frame: "world" => emit verts verbatim with org=0/floor.org=0 (imported real fields, or any
    # geometry already in exact world coords); "legacy" (default) => the calibrated flat-room path
    # (build_flat, org=(0,0,300) + optional character_offset). Multi-floor is always world.
    world_frame = wm.get("frame") == "world"
    if wm.get("obj"):
        verts, faces, floor_ids = bgi.load_obj_floors(str(project.path(wm["obj"])))
        if world_frame or len(set(floor_ids)) > 1:
            # WORLD frame: the verts ARE the exact in-game positions, so NO character shift (that
            # slide is a flat-room paint-alignment hack, not a real frame transform).
            mesh = bgi.build(verts, faces, floor_ids=floor_ids)
            if wm.get("links"):
                # reconcile the imported field's cross-floor connectivity onto the edited geometry
                # (rebuild_neighbors only links within a floor). v2 -- see docs/WALKMESH_EDITING.md.
                _apply_links(mesh, project.path(wm["links"]), warnings)
            return mesh.to_bytes()
        # single-floor legacy (e.g. flat Blender-authored): the author placed the verts; no shift.
        off = float(wm.get("character_offset", 0.0))
        verts = _shift_toward_camera(verts, camera, off)
        return bgi.build_flat(verts, faces).to_bytes()
    if wm.get("quad"):
        corners = [(c[0], 0, c[1]) if len(c) == 2 else tuple(c) for c in wm["quad"]]
        if world_frame:
            return bgi.build(corners, [(0, 1, 2), (0, 2, 3)]).to_bytes()
        off = float(wm.get("character_offset", 0.0))
        return bgi.quad(_shift_toward_camera(wm["quad"], camera, off)).to_bytes()
    # auto: frame the floor from the camera, then slide the walkmesh toward the camera by the
    # character ground offset so a 3D character looks planted on the scale-1-painted floor.
    fr = project.raw.get("camera", {}).get("frame", {})
    try:
        frame = guide.frame_floor(camera, back_canvas_y=float(fr.get("back", 205)),
                                  front_canvas_y=float(fr.get("front", 432)))
    except ValueError as e:
        raise BuildError(f"[camera.frame] {e}") from e
    off = float(wm.get("character_offset", cam.CHARACTER_GROUND_OFFSET_Z))
    corners = _shift_toward_camera(guide.walkmesh_corners(frame), camera, off)
    return bgi.quad(corners).to_bytes()


def build_overlays(project: FieldProject, range_wh=(384, 448)) -> list:
    overlays = []
    for layer in project.raw.get("layers", []):
        pos = layer.get("position", [0, 0])
        overlays.append(bgx.Overlay(
            image=Path(layer["image"]).name,
            position=(int(pos[0]), int(pos[1]), int(layer["z"])),
            # a full-cover layer defaults to the painted canvas size (the camera Range), so a
            # larger-than-screen scrolling painting isn't clipped to a single 384x448 screen.
            size=tuple(layer.get("size", (int(range_wh[0]), int(range_wh[1])))),
            shader=layer.get("shader", bgx.DEFAULT_SHADER),
        ))
    return overlays


# --------------------------------------------------------------------------- script assembly

def resolve_control_value(project: FieldProject, camera: cam.Cam) -> int:
    """The SetControlDirection (TWIST) value that makes WASD match the camera.

    Explicit ``[camera] control_direction`` wins; otherwise it is derived from the camera's yaw so a
    yawed/orbited camera still moves "up = up the screen". A front-facing camera yields -1 (the kit
    default = 0 deg), so front-facing fields are byte-identical to before."""
    c = project.raw.get("camera", {})
    if "control_direction" in c:
        return int(c["control_direction"])
    return _movement.control_value_for_angle(cam.yaw_deg(camera))


def build_script(project: FieldProject, lang: str, dialogue_txids: dict,
                 control_value: int = -1) -> bytes:
    """Build one language's .eb by applying the project's content to the blank field."""
    eb = _data.blank_field_bytes(lang)
    # movement control-direction first (shift-free, before any appends that move bytecode)
    if control_value != -1:
        eb = _movement.set_control_direction(eb, control_value)
    has_encounter = "encounter" in project.raw

    # larger-than-screen scrolling: enable the field's camera services (Active flag) so the engine's
    # 3D scroll follows the player. The wide Range + scroll Viewport come from the camera/scene.
    sc = project.raw.get("camera", {}).get("scroll", {})
    if sc.get("enabled"):
        eb = _camera.enable_camera_services(eb, frame_count=int(sc.get("frame_count", 0)),
                                            scroll_type=int(sc.get("scroll_type", 0)))

    # NPCs (cloned from the player object) first, so their cloned positions are independent.
    for i, n in enumerate(project.raw.get("npc", [])):
        pos = n["pos"]
        txid = dialogue_txids.get(i, int(n.get("text_id", _text.DEFAULT_BASE_TXID)))
        kwargs = {}
        if "preset" in n:
            kwargs["preset"] = n["preset"]
        else:
            kwargs.update(model=n.get("model"), animset=n.get("animset"), anims=n.get("anims"))
        eb = _npc.inject_npc(eb, int(pos[0]), int(pos[1]), talk_text_id=txid, **kwargs)

    # gateways
    for gw in project.raw.get("gateway", []):
        zone = gw["zone"]
        if len(zone) == 4:
            zone = _gw.quad_zone(zone)
        eb = _gw.inject_gateway(eb, int(gw["to"]), entrance=int(gw.get("entrance", 0)),
                                zone=[tuple(p) for p in zone])

    # player spawn (order-independent w.r.t. the appends above)
    if "player" in project.raw and "spawn" in project.raw["player"]:
        sp = project.raw["player"]["spawn"]
        eb = _npc.set_player_spawn(eb, int(sp[0]), int(sp[1]))

    # encounter (+ the after-battle reinit it requires)
    if has_encounter:
        e = project.raw["encounter"]
        eb = _enc.inject_encounter(eb, scene=int(e["scene"]), freq=int(e.get("freq", 255)),
                                   pattern=int(e.get("pattern", 1)),
                                   scenes=e.get("scenes"))
        eb = _reinit.add_reinit(eb, with_fade=True)

    # field music
    if "music" in project.raw:
        song = int(project.raw["music"]["song"])
        eb = _music.add_field_music(eb, song)
        if has_encounter:  # resume after battle
            eb = _music.add_music_to_reinit(eb, song)
    elif has_encounter:
        # encounter but no music still needs reinit (added above); nothing else to do
        pass

    return eb


def collect_dialogue(project: FieldProject):
    """Return (mes_body, txid_by_npc_index). Empty body if no NPC has dialogue."""
    lines, idx_map = [], {}
    for i, n in enumerate(project.raw.get("npc", [])):
        if "dialogue" in n:
            idx_map[i] = len(lines)
            lines.append(n["dialogue"])
    if not lines:
        return "", {}
    body, mapping = _text.build_mes(lines, start_txid=_text.DEFAULT_BASE_TXID)
    txid_by_npc = {npc_i: mapping[line_i] for npc_i, line_i in idx_map.items()}
    return body, txid_by_npc


# --------------------------------------------------------------------------- the build

@dataclass
class FieldResult:
    dict_line: str
    battle: tuple | None = None     # (scene, music) for BattlePatch, or None
    fbg: str = ""
    warnings: list = _dc_field(default_factory=list)


def build_field(project: FieldProject, layout: ModLayout, *, langs=LANGS) -> FieldResult:
    """Write one field's assets into the mod ``layout``. Returns its registration info."""
    problems = validate(project)
    if problems:
        raise BuildError("invalid field project:\n  - " + "\n  - ".join(problems))

    fbg = project.fbg
    layout.ensure_dirs(fbg, langs=langs)

    camera = resolve_camera(project)
    warnings = []
    pw = cam.pitch_warning(cam.pitch_deg(camera))
    if pw:
        warnings.append(pw)

    # BG-borrow (import mode): the DictionaryPatch points the BG lookup at a REAL base-game field
    # (areaID + borrow_bg mapid), so the engine renders that field's art + walkmesh + camera while
    # running OUR script. We ship only the .eb (no custom scene). The borrowed `camera.bgx` still
    # drives movement/scroll derivation + content guidance. Proven path (Session 4). Otherwise build
    # a full custom scene (camera + walkmesh + overlays -> .bgx / .bgi / PNGs).
    borrow_bg = project.field.get("borrow_bg")
    if not borrow_bg:
        bgi_bytes = resolve_walkmesh(project, camera, warnings)
        wmesh = bgi.BgiWalkmesh.from_bytes(bgi_bytes)
        # content placement: warn when an NPC / spawn / gateway sits OFF the walkable area -- the
        # recurring in-game mistake (an NPC floats, the player can't reach a trigger). Always checked.
        _validate_content_placement(project, wmesh, warnings)
        # reachability + degenerate-tri guards for (re)BUILT walkmeshes (obj/quad/auto): rebuild_neighbors
        # links only within a floor, so a multi-floor obj strands its floors. A verbatim [walkmesh] bgi is
        # the authoritative original and is SKIPPED -- some real fields legitimately reach floors by script,
        # not on foot (e.g. UDFT: 9 of 23 floors walk-reachable), so checking it cries wolf.
        if not project.raw.get("walkmesh", {}).get("bgi"):
            stranded = wmesh.all_floors() - wmesh.reachable_floors()
            if stranded:
                warnings.append(
                    f"walkmesh: floor(s) {sorted(stranded)} not walk-reachable from the start "
                    f"({len(stranded)} of {len(wmesh.all_floors())} floors stranded). A multi-floor "
                    f"[walkmesh] obj loses cross-floor links (rebuild_neighbors only links within a "
                    f"floor) -- ship the original with [walkmesh] bgi, or declare seams "
                    f"(docs/WALKMESH_EDITING.md).")
            degen = wmesh.degenerate_tris()
            if degen:
                warnings.append(
                    f"walkmesh: {len(degen)} zero-area triangle(s) {degen[:5]}"
                    f"{'...' if len(degen) > 5 else ''} -- collinear verts make a dead zone in the "
                    f"engine's IsInQuad test (the player can't stand there); fix them in the .obj.")
        overlays = build_overlays(project, range_wh=tuple(camera.range))
        bgx_text = bgx.build(camera, overlays, header_comment=project.field.get("title", project.name))

        fm = layout.fieldmap_dir(fbg)
        (fm / f"{fbg}.bgx").write_text(bgx_text, encoding="utf-8", newline="\n")
        (fm / f"{fbg}.bgi.bytes").write_bytes(bgi_bytes)
        for layer in project.raw.get("layers", []):
            src = project.path(layer["image"])
            shutil.copyfile(src, fm / Path(layer["image"]).name)
    else:
        # BG-borrow ships no walkmesh (the engine uses the borrowed field's real one), but we can still
        # validate content placement against it: [walkmesh] reference (or the sibling walkmesh.bgi the
        # importer wrote). Makes the off-walkmesh guard universal -- borrow forks are the common case.
        ref = _borrow_walkmesh(project)
        if ref is not None:
            _validate_content_placement(project, ref, warnings)

    # --- dialogue + per-language script ---
    mes_body, txids = collect_dialogue(project)
    control_value = resolve_control_value(project, camera)
    for lang in langs:
        eb = build_script(project, lang, txids, control_value)
        layout.eb_path(lang, f"EVT_{project.name}.eb.bytes").write_bytes(eb)
        if mes_body:
            layout.mes_path(lang, project.text_block).write_text(mes_body, encoding="utf-8", newline="\n")

    bg_mapid = borrow_bg if borrow_bg else project.name
    dict_line = f"FieldScene {project.id} {project.area} {bg_mapid} {project.name} {project.text_block}"
    battle = None
    if "encounter" in project.raw:
        e = project.raw["encounter"]
        battle = (int(e["scene"]), int(e.get("battle_music", 0)))
    return FieldResult(dict_line=dict_line, battle=battle, fbg=fbg, warnings=warnings)


def build_mod(projects, out_root, *, mod_name="FF9CustomMap", author="", description="",
              langs=LANGS) -> dict:
    """Build one or more fields into a mod at ``out_root``; write the registration files."""
    layout = ModLayout(Path(out_root).resolve())
    results = [build_field(p, layout, langs=langs) for p in projects]

    layout.dictionary_patch.write_text(
        "\n".join(r.dict_line for r in results) + "\n", encoding="utf-8", newline="\n")

    battles = [r.battle for r in results if r.battle]
    if battles:
        lines = []
        for scene, mus in battles:
            lines.append(f"Battle: {scene}")
            lines.append(f"Music: {mus}")
        layout.battle_patch.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    layout.mod_description.write_text(
        "<Mod>\n"
        f"    <Name>{mod_name}</Name>\n"
        f"    <Author>{author}</Author>\n"
        f"    <InstallationPath>{mod_name}</InstallationPath>\n"
        "    <Category></Category>\n"
        f"    <Description>{description}</Description>\n"
        "</Mod>\n",
        encoding="utf-8", newline="\n")

    return {"root": str(layout.root), "fields": [r.fbg for r in results],
            "dictionary": [r.dict_line for r in results],
            "warnings": [w for r in results for w in r.warnings]}
