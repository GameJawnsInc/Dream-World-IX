"""The Place document — click-authoring Rung 3's placement host (studies/click-authoring/PLAN.md).

Content placement on ANY forked real field, on the art: the shell PUSHES the open field.toml
(the BehaviorDoc feed contract — this doc reads no files at construction or tab show), and one
explicit **Load the room** click builds the donor surface off the GUI thread — the composited
background (``extract.compose_background``, per-camera, disk-cached under the provision cache),
the donor's real camera (``extract.cache_field`` → ``camera.bgx``), and its real walkmesh in
RENDER-frame triangles (``imagefield.mesh_world_tris`` — the y-flip lives there, never here).
:class:`~.backdrop.BackdropCanvas` in place mode then raycasts every click against the mesh
(you click what you SEE; a stacked-floor pixel disambiguates through a menu, never a guess).

Rung 4 adds the REGIONS tool (a :class:`~.widgets.ToolStrip` — one click semantic at a
time, explicit): gateway / walk-in-event trigger quads drawn as four clicks on the art,
reshaped by corner or whole-quad drags, the walk-out edge rotated from the quad's own menu —
with both region laws RENDERED, not just accepted (the TREADQUAD overlap starvation and the
IsInQuad engine-fan audit, judged in :func:`region_rows`).

Writes land in the OPEN doc through PURE ops (:func:`place_npc` / :func:`place_prop` /
:func:`set_spawn` / :func:`set_arrival` / :func:`place_gateway` / :func:`place_event` /
:func:`move_zone` / :func:`delete_region`) + exactly ONE ``on_edit(member, label)`` per drop —
the shell records the undo step and Save persists through the ordinary editor path, so Place
can never grow a private writer. Refusals are hard and honest: a bundled example / installed
copy (``editor.model.protected_reason``) refuses the whole surface; a VERBATIM fork refuses
spawn/arrival (the donor's own entry sequence runs) while npc/prop stay live — the build seats
them below the donor's party-character band.

★ **A NOVEL FIELD PLACES HERE TOO** (click-authoring Rung 7d). This doc used to refuse anything
without a donor real room and send the author to Blender or the Editor forms — but that was a test
of PROVENANCE, and a surface only needs a CAMERA and a WALKMESH. A composed floorplan room, an
``ff9mapkit new`` scaffold and a traced photo field all have both, exactly; a composed room's
camera is in fact better known than a forked one's, because the composer solved it. The one
predicate blocked all three from-scratch lanes at once. :func:`build_surface_from_project` resolves
them through the ordinary build resolvers (so ``[camera.scroll]`` and ``[[camera]]`` are honoured
and the surface matches what the build ships) and touches no game install.
"""

from __future__ import annotations

import os
import threading
from pathlib import Path

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QCursor, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup, QComboBox, QHBoxLayout, QLabel, QMenu, QPushButton, QRadioButton,
    QSizePolicy, QSpinBox, QVBoxLayout, QWidget,
)

from .. import imagefield
from ..editor import names as _names
from ..editor.model import protected_reason
from . import widgets
from .backdrop import BackdropCanvas

_DEFAULT_PROP = "barrel"          # neutral set-dressing (NOT "chest" — a real openable is [[chest]])


# --------------------------------------------------------------------- pure placement ops
# Each op mutates the OPEN doc's dict and returns the undo label the shell records. One op per
# drop — the StageCanvas/behaviorscan discipline, so a place gesture is exactly one undo step.
def place_npc(data: dict, x, z, taken=()) -> str:
    # No dialogue by default (THE DEFAULT-VALUE LAW, rung-4 playtests): a hand-rolled "..."
    # placeholder ships a fake window; dialogue-less, the build's silent-talk channel emits
    # the CANONICAL FF9 silent line on both lanes (word it in the Editor when it should speak).
    # ``taken``: names the scene.toml already uses -- the build merges rows BY NAME (finding P2).
    lst = data.setdefault("npc", [])
    nm = _names.fresh_npc_name([n.get("name") for n in lst if isinstance(n, dict)] + list(taken))
    lst.append({"name": nm, "preset": "vivi",
                "pos": [int(round(x)), int(round(z))]})
    return f"place NPC {nm}"


def place_prop(data: dict, x, z) -> str:
    lst = data.setdefault("prop", [])
    nm = _fresh_name("prop", lst)                   # never len(): after a delete that is a live name
    lst.append({"name": nm, "prop": _DEFAULT_PROP,
                "pos": [int(round(x)), int(round(z))]})
    return f"place prop {nm}"


def set_spawn(data: dict, x, z) -> str:
    data.setdefault("player", {})["spawn"] = [int(round(x)), int(round(z))]
    return "move spawn"


def set_arrival(data: dict, entrance, x, z) -> str:
    """Upsert the ``[[player.arrival]]`` row for ``entrance`` (one row per entrance — the
    schema's own key)."""
    rows = data.setdefault("player", {}).setdefault("arrival", [])
    pos = [int(round(x)), int(round(z))]
    for r in rows:
        if isinstance(r, dict) and r.get("entrance", 0) == int(entrance):
            r["pos"] = pos
            return f"move arrival {int(entrance)}"
    rows.append({"entrance": int(entrance), "pos": pos})
    return f"place arrival {int(entrance)}"


def _fresh_name(prefix, rows, taken=()) -> str:
    names = {e.get("name") for e in rows if isinstance(e, dict)} | set(taken)
    n = 0
    while f"{prefix}{n}" in names:
        n += 1
    return f"{prefix}{n}"


def _zone_ints(quad) -> list:
    return [[int(round(x)), int(round(z))] for x, z in quad]


def place_gateway(data: dict, quad, to, entrance=0, taken=()) -> str:
    """Append a ``[[gateway]]`` from a drawn quad. Corner ORDER is authored geometry — the
    canvas emits the click order, and corners 0→1 become the walk-out edge the exit walks
    the player across (rotate via the canvas menu). ``taken``: the scene.toml's names."""
    lst = data.setdefault("gateway", [])
    nm = _fresh_name("door", lst, taken)
    row = {"name": nm, "to": int(to), "zone": _zone_ints(quad)}
    if int(entrance):
        row["entrance"] = int(entrance)
    lst.append(row)
    return f"draw gateway {nm} -> {int(to)}"


def place_event(data: dict, quad, taken=()) -> str:
    """Append a walk-in ``[[event]]`` zone from a drawn quad (message placeholder — the
    Editor form owns the words). ``taken``: the scene.toml's names."""
    lst = data.setdefault("event", [])
    nm = _fresh_name("zone", lst, taken)
    lst.append({"name": nm, "message": "...", "zone": _zone_ints(quad)})
    return f"draw event {nm}"


def set_event_message(data: dict, index, text) -> str:
    """Reword a drawn event zone in place (the quad menu's Set message — the drawn-zone
    placeholder '...' otherwise ships as a literal popup). Raises ValueError on a blank line: it
    builds clean and shows nothing in-game (finding P10) -- the one owner of that rule, for the
    menu and for the ask right after a draw."""
    if not str(text).strip():
        raise ValueError("an empty line shows nothing when the player walks in")
    ev = data.get("event", [])[index]
    ev["message"] = str(text)
    return f"reword event {ev.get('name') or index}"


def set_gateway_target(data: dict, index, to) -> str:
    """Retarget a drawn door (the canvas menu's Set gateway target — the 'to field' box only
    feeds NEW draws, the in-game lesson of the Field(0) black screen)."""
    gw = data.get("gateway", [])[index]
    gw["to"] = int(to)
    return f"retarget {gw.get('name') or 'gateway'} -> {int(to)}"


def move_zone(data: dict, kind, index, quad) -> str:
    """Rewrite one row's zone from a canvas gesture (corner drag / whole-quad drag /
    walk-out rotate). Writes exactly the corners the canvas holds — a doubled 5th point
    was normalized away at feed time and the build re-doubles (``quad_zone``)."""
    row = data.get(kind, [])[index]
    old = [tuple(p) for p in row.get("zone") or []]
    if len(old) == 5 and old[-1] == old[-2]:           # the stored doubled form, as the canvas saw it
        old = old[:4]
    row["zone"] = _zone_ints(quad)
    name = row.get("name") or f"{kind} {index}"
    if len(old) >= 3 and row["zone"] == _zone_ints(old[1:] + old[:1]):   # the menu's rotate: the
        return f"rotate walk-out edge of {name}"          # same corners, order turned by one
    return f"reshape {kind} {name} zone"


def delete_region(data: dict, kind, index) -> str:
    rows = data.get(kind, [])
    label = rows[index].get("name") or f"{kind} {index}"
    del rows[index]
    return f"delete {kind} {label}"


def region_rows(data: dict) -> list:
    """The canvas feed: every ``[[gateway]]``/``[[event]]`` row with a plottable zone —
    ``[{"i", "kind", "index", "quad", "label", "warn"}]``. A doubled trailing vertex (the
    IsInQuad-safe stored form) is dropped for display; a 5-DISTINCT-point zone keeps all
    five corners (its fan is judged verbatim, dead zones included). ``warn`` carries the two
    region laws: the TREADQUAD overlap judge (``build.region_overlap_pairs`` — one owner
    with the lint) and the engine-fan audit (``imagefield.zone_fan_audit``)."""
    from .. import build                            # lazy: the judge, not the builder
    from .. import pack                             # the one owner of the id bands
    rows = []
    for kind in ("gateway", "event"):
        for idx, e in enumerate(data.get(kind, []) or []):
            z = e.get("zone")
            if not isinstance(z, (list, tuple)) or len(z) not in (4, 5):
                continue
            try:
                pts = [(float(p[0]), float(p[1])) for p in z]
            except (TypeError, ValueError, IndexError):
                continue
            if len(pts) == 5 and pts[-1] == pts[-2]:
                pts = pts[:4]
            if kind == "gateway":
                label = f"{e.get('name') or 'gateway'} → {e.get('to', '?')}"
                if e.get("entrance"):
                    label += f" e{e['entrance']}"
            else:
                label = e.get("name") or f"event {idx}"
            rows.append({"i": len(rows), "kind": kind, "index": idx, "quad": pts,
                         "label": label, "warn": None})
    overlaps = {}
    for ka, kb in build.region_overlap_pairs(data):
        overlaps.setdefault((ka[0], ka[1]), []).append(kb[2])
        overlaps.setdefault((kb[0], kb[1]), []).append(ka[2])
    for r in rows:
        warns = []
        if r["kind"] == "gateway":
            to = (data.get("gateway", []) or [])[r["index"]].get("to")
            if isinstance(to, bool) or (isinstance(to, int) and to <= 0) or to is None:
                warns.append("NO TARGET — this door compiles to Field(0), a guaranteed black "
                             "screen; right-click it → Set gateway target")
            elif isinstance(to, int) and to >= pack.CUSTOM_ID_MIN:
                try:                                 # the band owner judges a custom id (a REAL
                    pack.check_custom_id(to, "target")   # field id below the band is a legal target)
                except ValueError as e:
                    why = str(e).split(" -- ")[0].split(" (")[0]   # the band, not the engine's
                    warns.append(f"{why} — the door black-screens in-game; "   # own table names
                                 "right-click it → Set gateway target")
        else:
            ev = (data.get("event", []) or [])[r["index"]]
            if ev.get("message") == "..." and not (ev.get("received") and "give_item" in ev):
                warns.append("placeholder message — it ships as a literal '...' popup; "
                             "right-click → Set message (or add a reward in the Editor)")
        warns += [f"overlaps {other} — the engine fires ONE tread region per frame, the "
                  f"later-armed one silently starves" for other in
                  overlaps.get((r["kind"], r["index"]), [])]
        audit = imagefield.zone_fan_audit(r["quad"])
        if not imagefield.fan_triangles(r["quad"]):   # the audit has no interior to judge (P11)
            warns.append("no area — its corners lie in a line or on one spot, so it can never "
                         "fire; drag a corner out")
        if audit["gap"] > 0.02:
            warns.append(f"dead zone ~{audit['gap']:.0%} — part of the drawn area never fires")
        if audit["spill"] > 0.02:
            warns.append(f"over-trigger ~{audit['spill']:.0%} — fires outside the drawn outline")
        r["warn"] = "; ".join(warns) or None
    return rows


# --------------------------------------------------------------------- pure marker derivation
def content_markers(data: dict) -> list:
    """Every placed thing with a floor position -> ``[{"xz", "label", "kind", "index"}]``
    (world (x, z); the doc resolves height against the loaded walkmesh — :func:`floor_y_at`).
    ``index``: the row's place in ``data``'s own list (None for the spawn), read once, when the
    doc resolves the ROW a marker gesture will write."""
    out = []

    def rows(section, kind, label_of):
        for i, e in enumerate(data.get(section, []) or []):
            if isinstance(e, dict) and isinstance(e.get("pos"), (list, tuple)) and len(e["pos"]) >= 2:
                out.append({"xz": (float(e["pos"][0]), float(e["pos"][1])),
                            "label": label_of(e, i), "kind": kind, "index": i})

    rows("npc", "npc", lambda e, i: e.get("name") or f"npc {i}")
    rows("prop", "prop", lambda e, i: e.get("name") or e.get("prop") or f"prop {i}")
    rows("chest", "chest", lambda e, i: f"chest {i}")
    player = data.get("player") or {}
    sp = player.get("spawn")
    if isinstance(sp, (list, tuple)) and len(sp) >= 2:
        out.append({"xz": (float(sp[0]), float(sp[1])), "label": "spawn", "kind": "spawn",
                    "index": None})
    for i, r in enumerate(player.get("arrival", []) or []):
        p = r.get("pos") if isinstance(r, dict) else None
        if isinstance(p, (list, tuple)) and len(p) >= 2:
            out.append({"xz": (float(p[0]), float(p[1])),
                        "label": f"arrival {r.get('entrance', 0)}", "kind": "arrival", "index": i})
    return out


def move_placed(row: dict, key, x, z, what) -> str:
    """A marker drag: rewrite the ``key`` position (``pos``, or ``spawn`` on ``[player]``) of
    the row the marker was drawn from -- the row OBJECT, never a list index."""
    row[key] = [int(round(x)), int(round(z))]
    return f"move {what}"


def delete_placed(rows: list, row, what) -> str:
    """Remove ``row`` from ``rows`` by IDENTITY: two rows may share a name, a position, or the
    index the other had before an Editor delete."""
    del rows[next(k for k, r in enumerate(rows) if r is row)]
    return f"delete {what}"


# The render-frame height resolver moved to the pure home (the canvas needs it too, for
# projecting zone corners); the name stays importable here — call sites and fences hold.
floor_y_at = imagefield.floor_y_at


# --------------------------------------------------------------------- the async surface load
class _SurfaceLoader(QObject):
    """One background build of a donor room's place surface (camera + mesh + composited art).
    The thumbs idiom: pure worker logic behind a queued signal; every failure lands as a
    ``failed`` message instead of a crash (a machine without the install degrades honestly).
    Both signals carry the REQUEST key ``(source, cam_index)``: the doc acts only on the load it
    is waiting for, and a request's camera may come back clamped in the bundle."""

    loaded = Signal(object, dict)
    failed = Signal(object, str)

    def start(self, source, cam_index):
        t = threading.Thread(target=self._work, args=(source, int(cam_index)),
                             name="ff9-place-surface", daemon=True)
        t.start()

    def _work(self, source, cam_index):
        try:
            kind, ref = source
            self.loaded.emit((source, cam_index),
                             build_surface(int(ref), cam_index) if kind == "real"
                             else build_surface_from_project(ref, cam_index))
        except Exception as e:                         # noqa: BLE001 -- no install / bad art / anything
            try:
                self.failed.emit((source, cam_index), f"{type(e).__name__}: {e}")
            except RuntimeError:                       # the C++ half died (app exit) -- stop quietly
                pass


def build_surface_from_project(toml_path, cam_index: int = 0) -> dict:
    """The same surface bundle as :func:`build_surface`, for a field that has NO donor real room --
    a composed floorplan room, an ``ff9mapkit new`` scaffold, a traced photo field.

    ★ PLACE'S REFUSAL WAS ABOUT PROVENANCE, NOT GEOMETRY. It blocked on
    ``build.donor_field_id(data) is None`` and told the author "a novel field places content in
    Blender or the Editor forms" -- but everything the surface actually needs is a CAMERA and a
    WALKMESH, and a novel field has both, exactly and by construction. A composed room's camera is
    not merely available, it is *better known* than a forked one's: the composer solved it.

    ★ AND IT UNBLOCKS ALL THREE FROM-SCRATCH LANES AT ONCE, because they failed on the same
    predicate: the floorplan composer, ``pack.new_project`` (File > New Field), and the Trace lane.

    Everything here goes through the ordinary build resolvers -- ``resolve_cameras`` honours
    ``[camera.scroll]`` and ``[[camera]]``, ``resolve_walkmesh`` is already uniform across
    ``obj`` / ``bgi`` / ``quad`` / ``auto`` -- so the surface the author clicks on is the one the
    build ships. No game install is touched."""
    from pathlib import Path as _Path
    from .. import build as _build
    from ..scene import bgi as _bgi

    project = _build.FieldProject.load(str(toml_path))
    cams = _build.resolve_cameras(project)
    if not cams:
        raise imagefield.ImageFieldError(f"{_Path(toml_path).name}: no camera to place against")
    ci = max(0, min(int(cam_index), len(cams) - 1))
    # The FLOOR is camera 0's under every camera, as the build frames it (an auto walkmesh differs
    # per camera); the selected camera only draws it and casts the clicks (review finding E4).
    mesh = _bgi.BgiWalkmesh.from_bytes(_build.resolve_walkmesh(project, cams[0]))
    tris, floors = imagefield.mesh_world_tris(mesh)
    return {"donor": None, "source": ("project", str(toml_path)), "cam_index": ci,
            "n_cams": len(cams), "cam": cams[ci],
            "png": _project_backdrop(project, cams[ci], ci), "tris": tris, "floors": floors}


def _project_backdrop(project, camera, cam_index: int = 0):
    """The picked camera's ``[[layers]]`` composited back-to-front into one PNG, or None.

    Laid out the way the build ships them: :func:`build.build_overlays` owns each layer's
    ``position``, ``size`` (default: the camera's whole frame), ``camera`` and ``shader``, so
    only ``cam_index``'s layers are drawn, each scaled to its size at its position on a canvas
    the size of the camera frame -- never the accumulator resized to a later layer (review
    finding P3: an ``import --editable`` fork's tight depth crops each became the whole room).
    A blend-shader layer (light, glow) is left out: the floor reads without it, and painted
    opaque it would hide the room.

    ★ BACK TO FRONT IS DESCENDING z: FF9 sorts by OT depth with SMALLER IN FRONT, so the largest z
    is the furthest layer and must be painted first. Getting this backwards puts the floor under
    the backdrop and the author places content against a slab of flat colour.

    Written to the kit's cache, keyed per file and camera -- never into the author's project
    folder (finding P9)."""
    import hashlib
    try:
        from PIL import Image
    except ImportError:
        return None
    from .. import build as _build, provision
    from ..scene import bgx as _bgx
    fw, fh = (int(v) for v in (camera.range or (imagefield.CANVAS_W, imagefield.CANVAS_H)))
    try:
        overlays = _build.build_overlays(project, range_wh=(fw, fh))
    except (KeyError, TypeError, ValueError, IndexError):    # a malformed layer: the mesh still places
        return None
    picked = []
    for spec, ov in zip(project.raw.get("layers") or [], overlays):
        if ov.camera_id != int(cam_index) or ov.shader != _bgx.DEFAULT_SHADER:
            continue
        try:
            p = project.path(spec["image"])
        except Exception:                              # noqa: BLE001 -- a bad ref is not fatal here
            continue
        if p.is_file():
            picked.append((ov, p))
    if not picked:
        return None
    picked.sort(key=lambda t: -t[0].position[2])
    ims = [(ov, Image.open(p).convert("RGBA")) for ov, p in picked]
    # the art's own resolution: a full-cover painting larger than the frame keeps its detail
    k = max(1.0, min(4.0, max(im.width / max(1, ov.size[0]) for ov, im in ims)))
    out = Image.new("RGBA", (round(fw * k), round(fh * k)), (0, 0, 0, 0))
    for ov, im in ims:
        w, h = max(1, round(ov.size[0] * k)), max(1, round(ov.size[1] * k))
        layer = Image.new("RGBA", out.size, (0, 0, 0, 0))
        layer.paste(im.resize((w, h)) if im.size != (w, h) else im,
                    (round(ov.position[0] * k), round(ov.position[1] * k)))
        out = Image.alpha_composite(out, layer)
    src = str(project.toml_path or project.path("."))
    key = hashlib.sha1(os.path.normcase(os.path.abspath(src)).encode("utf-8")).hexdigest()[:12]
    dest = provision.cache_dir() / "place" / f"project_{key}_cam{int(cam_index)}.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.save(dest)
    return str(dest)


def build_surface(donor: int, cam_index: int = 0) -> dict:
    """Worker body (Qt-free, testable): the donor's cameras + render-frame walkmesh triangles +
    the per-camera composited background PNG (disk-cached — the game art is static, so the key
    is (field, camera) alone). ``env_lock`` serializes the UnityPy env against every other
    reader (the thumbs discipline)."""
    from .. import extract, provision
    from ..scene import bgi as _bgi
    from ..scene import cam as _cam

    with extract.env_lock:
        info = extract.cache_field(donor)
    cams = _cam.parse_bgx_cameras(info["camera"])
    if not cams:
        raise imagefield.ImageFieldError(f"field {donor}: no camera in its .bgx")
    ci = max(0, min(int(cam_index), len(cams) - 1))
    if info.get("walkmesh") is None:
        raise imagefield.ImageFieldError(
            f"field {donor}: no walkmesh — there is no surface to place content on")
    mesh = _bgi.BgiWalkmesh.from_bytes(Path(info["walkmesh"]).read_bytes())
    tris, floors = imagefield.mesh_world_tris(mesh)
    png = provision.cache_dir() / "place" / f"real_{donor}_cam{ci}.png"
    if not png.is_file():
        png.parent.mkdir(parents=True, exist_ok=True)
        with extract.env_lock:
            ok = extract.compose_background(str(donor), png, draw_footprint=False,
                                            camera_index=ci)
        if ok is None:                                 # no readable art: the mesh alone still places
            png = None
    return {"donor": donor, "source": ("real", donor), "cam_index": ci, "n_cams": len(cams),
            "cam": cams[ci], "png": str(png) if png else None, "tris": tris, "floors": floors}


# --------------------------------------------------------------------- the document
class PlaceDoc(QWidget):
    """Click-to-place on a forked real field's own art. ``on_edit(member, label)`` is the ONE
    write channel — the shell checkpoints the mutation this doc made in the open doc's dict.
    ``on_open(member, key)``: the shell's way to a row's Editor form (``key`` as the tree has it,
    ``npc:2`` or ``player``); without one, no marker offers it."""

    MODES = (("npc", "NPC"), ("prop", "Prop"), ("spawn", "Spawn"), ("arrival", "Arrival"))
    MODE_TIPS = {
        "npc": "Click the floor to stand an NPC there, drawn as a circle. It starts as a silent "
               "Vivi; give it a model and words in the Editor (NPCs).",
        "prop": "Click the floor to set a prop there, drawn as a square. It starts as a barrel; "
                "pick its model in the Editor (Props).",
        "spawn": "Where the player stands when the field loads without coming through a door "
                 "(New Game, a warp): the default entry point. Drawn as a triangle.",
        "arrival": "Where the player lands coming in through a door: one spot per entrance "
                   "number, the number the source field's gateway sends. Drawn as a diamond.",
    }

    def __init__(self, pal, *, on_edit, on_open=None, scale=100):
        super().__init__()
        self.pal = pal
        self.on_edit = on_edit
        self.on_open = on_open
        self._member = None
        self._data = None                       # the OPEN doc's dict (the shell's reference)
        self._path = None
        self._donor = None
        self._blocked = None                    # protected_reason / no-donor text (placement refused)
        self._verbatim = False
        self._bundles = {}                      # (donor, cam_index) -> build_surface dict
        self._cam_pick = {}                     # surface source -> its chosen camera index
        self._region_rows_cache = []            # the last region_rows derivation (canvas feed)
        self._marker_rows_cache = []            # per fed marker: the row object it was drawn from
        self._loading = None                   # (source, ci) in flight, else None
        self._resume = set()                    # project sources the author loaded this session:
        #                                         re-read, unasked, on the way back (_resume_room)
        self._loader = _SurfaceLoader()
        self._loader.loaded.connect(self._on_loaded)
        self._loader.failed.connect(self._on_load_failed)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 10)
        root.setSpacing(8)
        crown, _ = widgets.nameplate(
            "", "Place",
            "Click the room's own art to place content — every click raycasts the real walkmesh.")
        root.addWidget(crown)

        # The control row is a SpillRow (the Cutscene scene bar's cure, finding P17): one
        # non-wrapping row floored the whole window at its SUM (1391px at 150% with a fork open,
        # over a 1280 window; at 1024/125% it crushed Load and the tool strip to '…'). The field,
        # Load and camera LEAD; the tool strip and its cluster TAIL, dropping to a second line
        # only when the column cannot hold both. The field name elides (full text in its tooltip).
        lead = QWidget()
        row = QHBoxLayout(lead)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        # min_ch 24: the lead stays narrower than the tail (the floor is unchanged), but the row
        # spills before the name is cut -- at 10 it read 'hut_int — d…' in a 1280 window
        self.field_label = widgets.ElideLabel("no field", "muted", min_ch=24)
        # Preferred, not ElideLabel's Ignored: it takes its whole text when there is room and
        # yields to min_ch when there is not, so Load stays beside it instead of at the far end
        self.field_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        row.addWidget(self.field_label)
        row.addSpacing(10)
        self.load_btn = QPushButton("Load the room")
        self.load_btn.clicked.connect(self.on_load)
        row.addWidget(self.load_btn)
        self.cam_label = QLabel("Camera")
        row.addWidget(self.cam_label)
        self.cam_box = QComboBox()
        self.cam_box.setAccessibleName("Camera")
        self.cam_box.setToolTip("A multi-camera field composites per camera — pick the angle "
                                "to place under.")
        self.cam_box.currentIndexChanged.connect(self._on_cam_changed)
        self.cam_label.setBuddy(self.cam_box)
        row.addWidget(self.cam_box)
        self.cam_box.setVisible(False)             # shown by _sync_cam_box on a multi-camera field
        self.cam_label.setVisible(False)
        row.addStretch(1)
        tail = QWidget()
        row = QHBoxLayout(tail)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        self.tools = widgets.ToolStrip(
            [("place", "Place", "Click the walkable footprint to place content — NPCs, "
                                "props, spawn, arrival."),
             ("regions", "Regions", "Draw trigger zones on the art — gateways and walk-in "
                                    "events (4 clicks = one zone; Esc cancels a half-drawn "
                                    "one).")])
        self.tools.changed.connect(lambda _k: self._apply_tool())
        row.addWidget(self.tools)
        row.addSpacing(6)
        self.mode_group = QButtonGroup(self)
        self.mode_btns = {}
        for key, label in self.MODES:
            rb = QRadioButton(label)
            rb.setAccessibleName(f"Place {label}")
            rb.setToolTip(self.MODE_TIPS[key])
            rb.toggled.connect(self._on_mode_toggled)
            self.mode_group.addButton(rb)
            self.mode_btns[key] = rb
            row.addWidget(rb)
        self.mode_btns["npc"].setChecked(True)
        self.ent_label = QLabel("entrance")
        row.addWidget(self.ent_label)
        self.ent_box = QSpinBox()
        self.ent_box.setRange(0, 255)
        self.ent_box.setAccessibleName("Arrival entrance")
        self.ent_box.setToolTip("Which entrance index this arrival row serves — the value the "
                                "source door writes.")
        self.ent_label.setBuddy(self.ent_box)
        row.addWidget(self.ent_box)
        # the Regions tool's own cluster (visible only while it is the active tool)
        self.rkind_group = QButtonGroup(self)
        self.rkind_btns = {}
        for key, label in (("gateway", "Gateway"), ("event", "Event")):
            rb = QRadioButton(label)
            rb.setAccessibleName(f"Draw {label} zones")
            rb.toggled.connect(self._on_rkind_toggled)
            self.rkind_group.addButton(rb)
            self.rkind_btns[key] = rb
            row.addWidget(rb)
        self.rkind_btns["gateway"].setChecked(True)
        self.gw_to_label = QLabel("to field")
        row.addWidget(self.gw_to_label)
        self.gw_to = QSpinBox()
        self.gw_to.setRange(0, 32767)
        self.gw_to.setSpecialValueText("?")
        self.gw_to.setAccessibleName("Gateway target field id")
        self.gw_to.setToolTip("The field id this door sends the player to (a real field or "
                              "one of yours) — set it before or after drawing; the Editor "
                              "form edits it too.")
        self.gw_to_label.setBuddy(self.gw_to)
        row.addWidget(self.gw_to)
        self.gw_ent_label = QLabel("entrance")
        row.addWidget(self.gw_ent_label)
        self.gw_ent = QSpinBox()
        self.gw_ent.setRange(0, 255)
        self.gw_ent.setAccessibleName("Gateway arrival entrance")
        self.gw_ent.setToolTip("The entrance index the destination's [[player.arrival]] rows "
                               "dispatch on.")
        self.gw_ent_label.setBuddy(self.gw_ent)
        row.addWidget(self.gw_ent)
        self.control_row = widgets.SpillRow(lead, tail, margins=(0, 0, 0, 0))
        root.addWidget(self.control_row)

        self.canvas = BackdropCanvas(pal, scale=scale)
        self.canvas.surface_clicked.connect(self._on_surface_clicked)
        self.canvas.region_drawn.connect(self._on_region_drawn)
        self.canvas.region_changed.connect(self._on_region_changed)
        self.canvas.region_deleted.connect(self._on_region_deleted)
        self.canvas.region_retarget.connect(self._on_region_retarget)
        self.canvas.region_reword.connect(self._on_region_reword)
        self.canvas.marker_moved.connect(self._on_marker_moved)
        self.canvas.marker_clicked.connect(self._on_marker_clicked)
        self.canvas.marker_deleted.connect(self._on_marker_deleted)
        self.canvas.marker_opened.connect(self._on_marker_opened)
        self.canvas.click_refused.connect(lambda m: self._refresh(m, "warn"))
        root.addWidget(self.canvas, 1)
        # A refused field (a bundled example, an installed copy, an unsaved doc) has nothing to
        # draw or click: the canvas gives way to the reason and the way out, centred (P19)
        self.refused_msg = QLabel("")
        self.refused_msg.setProperty("role", "muted")
        self.refused_msg.setWordWrap(True)
        self.refused_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.refused_msg.setContentsMargins(48, 0, 48, 0)
        self.refused_msg.setVisible(False)
        root.addWidget(self.refused_msg, 1)

        self.status = QLabel("")
        self.status.setProperty("role", "muted")
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        self.show_none()

    # ---------------------------------------------------------------- the shell feed
    def show_none(self):
        self._member = self._data = self._path = self._donor = self._source = None
        self._scene = {}
        self._blocked = None
        self._verbatim = False
        self._region_rows_cache = []
        self._marker_rows_cache = []
        self.canvas.set_place_mode(False)
        self.canvas.set_region_mode(False)
        self.canvas.set_surface([])
        self.canvas.set_markers([])
        self.canvas.set_regions([])
        self.canvas.set_backdrop(None, None)
        self.field_label.setText("no field")
        self._sync_cam_box(1)
        self._sync_modes()
        # the constructor ends HERE, so this is the clusters' first sync: without it both tools'
        # controls showed until a field was fed, and their sum (~1140px) became the window floor
        self._sync_tool_clusters()
        self._sync_load_tip()
        self._refresh()

    def show_field(self, member, data, path, *, dirty=False, scene=None):
        """The one feed: the OPEN doc's parsed dict (by reference — the ops mutate exactly the
        buffer the Editor and Save see). Cheap by design: no disk here (the startup-spend law);
        the donor surface loads on the user's own Load click.

        ``scene``: the parsed Blender ``scene.toml`` the build overlays on this field (scene wins
        per key, rows merged by name -- ``build._merge_scene``). Place SHOWS what it places where
        the build puts it, marked as Blender's, and refuses to move, retarget or delete it or to
        set a [player] key it sets: those writes would land in the field.toml and the build would
        ship the scene's value anyway (finding P2). Never written."""
        from .. import build                        # lazy: the resolver, not the builder
        # "The same field" is the same SURFACE SOURCE (a project's own file, or a donor room), never
        # just the same name: every traced project is called PICTURE, and a name match kept the
        # previous room's art and walkmesh armed while clicks wrote into the new doc (finding P5).
        old = (self._member, self._source)
        self._member, self._data = member, data
        self._scene = scene if isinstance(scene, dict) else {}
        self._path = Path(path) if path else None
        self._donor = build.donor_field_id(data)
        self._verbatim = bool(data.get("verbatim_eb"))
        self._blocked = protected_reason(self._path) if self._path else None
        # ★ THE SURFACE'S SOURCE, NOT THE FIELD'S PROVENANCE. Place used to refuse anything without
        # a donor real room -- "a novel field places content in Blender or the Editor forms" -- but
        # what a surface actually needs is a CAMERA and a WALKMESH, and a novel field has both, by
        # construction and exactly. A composed room's camera is better known than a forked one's:
        # the composer solved it. One predicate blocked the floorplan composer, `ff9mapkit new` and
        # the Trace lane all at once, and it was about where the field came from, not about
        # geometry.
        # A fork that ships its OWN scene art ([[layers]]: an `import --editable` fork) is placed on
        # its own surface even though it records its donor: its walkmesh.obj may be reshaped and its
        # layers repainted, and the donor's real room would not show either.
        own_scene = bool(data.get("layers") or self._scene.get("layers"))   # (the scene's win)
        self._source = (("real", self._donor) if self._donor is not None and not own_scene
                        else ("project", str(self._path)) if self._path else None)
        same = old == (self._member, self._source)
        if self._blocked is None and self._source is None:
            self._blocked = ("this field has not been saved to disk yet — Place needs a file to "
                             "resolve its camera and walkmesh from")
        self.field_label.setText(f"{member} — donor field #{self._donor}"
                                 if self._donor is not None else str(member))
        self._sync_load_tip()
        if not same:                                # (a late load of the old room never lands here:
            #                                         _on_loaded applies only the request it waits for)
            if self._loading is None or self._loading != getattr(self, "_stale_load", None):
                self._loading = None                # ...but a load already marked stale STAYS "in
            #                                         flight": were it forgotten, a second Load of the
            #                                         same room could start beside it, and whichever
            #                                         of the two landed LAST would be the one cached
            self._drop_project_surfaces()           # coming back to a project room re-reads it (P4)
            self._clear_surface()
        bundle = self._bundle()
        if bundle is not None and self._blocked is None:
            self._apply_bundle(bundle, refit=not same)
        else:
            self._sync_modes()
            self._refresh()
            self._resume_room()

    # ★ A PROJECT SURFACE IS KEPT ONLY WHILE THE AUTHOR STAYS HERE, ON THAT ROOM (review finding P4).
    # Its files can be rewritten whenever the author is elsewhere (a Blender re-export, a Floorplan
    # recompose, a hand edit), and a cached one re-armed on the way back let clicks raycast a floor
    # that no longer exists. Leaving the tab or the room drops it; Load reads the files again. The
    # edit re-feeds (one per placed click) happen while staying, so they keep it. A donor room's
    # surface is the install's and stays cached for the session.
    def hideEvent(self, e):
        if not e.spontaneous():                    # the author LEFT the tab. (A minimised window is a
            #                                        spontaneous hide: nobody went anywhere, and
            #                                        dropping the room there threw away a half-drawn
            #                                        region quad for nothing.)
            self._drop_project_surfaces()
            if self._loading is not None and self._loading[0][0] == "project":
                self._stale_load = self._loading   # ...and a read still in flight lands on a hidden
            #                                        tab: it must not be cached and re-armed on return
            if self._source is not None and self._source[0] == "project":
                self._clear_surface(keep_view=True)
        super().hideEvent(e)

    def showEvent(self, e):
        super().showEvent(e)
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self._resume_room)    # after the shell's own re-feed, whichever is first

    def _resume_room(self):
        """Dropping a project room on the way out is what keeps a stale floor from being clicked;
        making the author press Load again on every return would be the price. So a room they had
        loaded is read again, unasked and off the GUI thread, when they are back on it -- always
        from disk, never from the cache. Only while this tab is SHOWING (a hidden tab reads no
        disk), and never again after a load of it failed (that one waits for a real click)."""
        key = (self._source, self._cam_index())
        if (self.isVisible() and self._blocked is None and self._data is not None
                and self._source is not None and self._source in self._resume
                and key not in self._bundles and self._loading != key):
            self._resumed = key                        # the same room again: keep the author's view
            self.on_load()

    def _drop_project_surfaces(self):
        for key in [k for k in self._bundles if k[0][0] == "project"]:
            del self._bundles[key]

    def _clear_surface(self, *, keep_view=False):
        """Nothing drawn and nothing clickable: no floor stays armed that this doc cannot vouch for.
        ``keep_view``: the same room is about to be read again (a tab round trip), so the author's
        zoom and pan stay where they were."""
        self.canvas.set_backdrop(None, None, refit=not keep_view)
        self.canvas.set_surface([])
        self.canvas.set_markers([])
        self.canvas.set_regions([])
        self.canvas.set_place_mode(False)
        self.canvas.set_region_mode(False)

    @staticmethod
    def _is_file(a, b) -> bool:
        """One file under two spellings (a junction, a subst drive, another case) is still one."""
        try:
            return os.path.samefile(a, b)
        except (OSError, ValueError):
            return os.path.normcase(os.path.abspath(str(a))) == os.path.normcase(os.path.abspath(str(b)))

    def forget_surface(self, path):
        """Drop every cached surface built from the PROJECT file ``path``: its walkmesh, camera
        or art changed on disk (a Trace regenerate), and a cached project surface is re-applied
        on every re-feed while the author stays on it — so the art and the floor the clicks
        raycast would stay the OLD ones until the next Load click. A load of it still
        IN FLIGHT read the old files too: its result is thrown away when it lands. A donor
        room's surface (``("real", id)``) is the install's, not this file's, and stays."""
        def ours(source):
            return source is not None and source[0] == "project" and self._is_file(source[1], path)
        for key in [k for k in self._bundles if ours(k[0])]:
            del self._bundles[key]
        if self._loading is not None and ours(self._loading[0]):
            self._stale_load = self._loading

    # ---------------------------------------------------------------- surface load
    def _room_words(self):
        """Whose art Load brings: a donor room's, or this field's own (novel, traced, composed,
        an editable fork) -- Place serves every lane, and says which one it is on."""
        if self._source is not None and self._source[0] == "real":
            return f"donor field #{self._source[1]}'s"
        return "this field's own"

    def _sync_load_tip(self):
        if self._source is None:
            tip = "Open a field first: Load reads its camera, walkmesh and art."
        elif self._source[0] == "real":
            tip = (f"Extract donor field #{self._source[1]}'s camera and walkmesh and composite its "
                   "background (cached after the first load).")
        else:
            tip = ("Read this field's own camera, walkmesh and art from its files (read again on "
                   "every Load, so a re-export shows).")
        self.load_btn.setToolTip(tip)

    def _cam_index(self):
        # by SOURCE, not by name: another file called PICTURE has its own cameras (finding P29)
        return self._cam_pick.get(self._source, 0)

    def _bundle(self):
        if self._source is None:
            return None
        return self._bundles.get((self._source, self._cam_index()))

    def on_load(self):
        if self._blocked is not None or self._source is None or self._data is None:
            self._refresh()
            return
        key = (self._source, self._cam_index())
        # A donor room is the install's and never changes; a PROJECT room is read from files the
        # author can rewrite at any time (a Blender re-export, a Floorplan recompose, a hand edit),
        # so an explicit Load of one always goes back to disk -- it is cheap. (Review finding P4.)
        if key in self._bundles and key[0][0] == "real":
            self._apply_bundle(self._bundles[key], refit=True)
            return
        if self._loading == key:
            return
        if key[0][0] == "project":
            self._resume.add(key[0])                # the author wants THIS room on the canvas
        self._loading = key
        self.load_btn.setEnabled(False)
        angle = f" (camera {key[1]})" if self.cam_box.count() > 1 else ""
        if key[0][0] == "real":
            self._refresh(f"Loading donor field #{key[0][1]}{angle} — extracting its art, camera "
                          "and walkmesh…")
        else:
            self._refresh(f"Loading {self._member}{angle} — reading its camera, walkmesh and art…")
        self._loader.start(*key)

    def _settle(self, key) -> bool:
        """A load ``key`` ended: True when it is the room and camera on screen, so its outcome is
        shown. Only the load being waited for clears the wait and re-enables Load; any other (the
        previous room's, another camera's) never touches either (finding P6). A result for the
        room on screen is shown even when the wait was forgotten on the way: Load on A, a glance
        at B, back on A -- it is still the one asked for."""
        if getattr(self, "_stale_load", None) == key:
            self._stale_load = None
        if key == self._loading:
            self._loading = None
            self.load_btn.setEnabled(self._blocked is None and self._data is not None)
        return key == (self._source, self._cam_index())

    def _on_loaded(self, key, bundle):
        stale = getattr(self, "_stale_load", None) == key   # forget_surface ran while this one
        mine = self._settle(key)                             # was reading the OLD files
        if stale:
            if mine:
                self._refresh("The room changed on disk while it was loading — press Load the "
                              "room again.", "warn")
            self._resume_room()                     # (a room the author had loaded is simply read again)
            return                                  # never cached
        self._bundles[(bundle["source"], bundle["cam_index"])] = bundle
        if mine:                                    # (any other: cached, not applied)
            # a pick the room no longer has came back clamped: the pick follows it
            self._cam_pick[self._source] = bundle["cam_index"]
            resumed, self._resumed = getattr(self, "_resumed", None) == key, None
            self._apply_bundle(bundle, refit=not resumed)

    def _on_load_failed(self, key, msg):
        self._resume.discard(key[0])               # do not retry a failing read on every re-feed
        if self._settle(key):
            # a failed re-read leaves no floor behind: the old one is not what is on disk (P4)
            self._bundles.pop(key, None)
            self._clear_surface()
            self._refresh(f"Could not load the room: {msg}", "error")

    def _apply_bundle(self, bundle, *, refit):
        pm = QPixmap(bundle["png"]) if bundle["png"] else None
        if pm is not None and pm.isNull():
            pm = None
        self.canvas.set_backdrop(pm, bundle["cam"], refit=refit)
        self.canvas.set_surface(bundle["tris"], bundle["floors"])
        self._sync_cam_box(bundle["n_cams"])
        self._sync_modes()
        self._refresh_markers()
        self._refresh_regions()
        self._apply_tool()                          # activates the current tool's click mode

    def _sync_cam_box(self, n_cams):
        self.cam_box.blockSignals(True)
        self.cam_box.clear()
        for i in range(max(1, n_cams)):
            self.cam_box.addItem(f"camera {i}")
        self.cam_box.setCurrentIndex(min(self._cam_index(), max(1, n_cams) - 1))
        self.cam_box.blockSignals(False)
        multi = n_cams > 1
        self.cam_box.setVisible(multi)
        self.cam_label.setVisible(multi)

    def _on_cam_changed(self, i):
        if self._source is None or i < 0 or i == self._cam_index():
            return
        self._cam_pick[self._source] = int(i)
        self.on_load()                              # cached per (donor, camera) -> instant when warm

    # ---------------------------------------------------------------- placement
    def _mode(self):
        for key, _label in self.MODES:
            if self.mode_btns[key].isChecked():
                return key
        return "npc"

    def _on_mode_toggled(self, _on=False):
        """The entrance spinner belongs to the ARRIVAL mode alone — visible only while it is the
        selected (and permitted) placement, under the Place tool."""
        if getattr(self, "ent_box", None) is None:
            return                               # construction order: the radios exist before the spinner
        placing = getattr(self, "tools", None) is None or self.tools.current() == "place"
        arrival = (placing and self.mode_btns["arrival"].isChecked()
                   and self.mode_btns["arrival"].isEnabled())
        self.ent_box.setVisible(arrival)
        self.ent_label.setVisible(arrival)

    # ---------------------------------------------------------------- rung 4: the tool strip
    def _apply_tool(self):
        """ONE owner of tool -> canvas click semantics: Place raycasts, Regions draws quads —
        and neither arms without a loaded surface (the camera is the conversion)."""
        loaded = self._bundle() is not None and self._blocked is None and self._data is not None
        tool = self.tools.current()
        if loaded and tool == "regions":
            self.canvas.set_region_mode(True)
        elif loaded:
            self.canvas.set_place_mode(True)
        else:
            self.canvas.set_place_mode(False)
            self.canvas.set_region_mode(False)
        self._sync_tool_clusters()
        self._refresh()

    def _sync_tool_clusters(self):
        """The control row shows exactly the active tool's cluster (a strip that grows on
        selection shrinks the canvas out from under itself — visibility swaps, never adds)."""
        if getattr(self, "gw_ent", None) is None:
            return                               # construction order: radios fire before the boxes
        placing = self.tools.current() == "place"
        for key, _label in self.MODES:
            self.mode_btns[key].setVisible(placing)
        for w in (self.rkind_btns["gateway"], self.rkind_btns["event"]):
            w.setVisible(not placing)
        gw = not placing and self.rkind_btns["gateway"].isChecked()
        for w in (self.gw_to_label, self.gw_to, self.gw_ent_label, self.gw_ent):
            w.setVisible(gw)
        self._on_mode_toggled()

    # ---------------------------------------------------------------- the Blender scene (P2)
    def _view(self) -> dict:
        """The field as the build sees it: the open doc with its scene.toml overlaid. Read-only --
        every write goes to ``self._data``."""
        if not self._scene or self._data is None:
            return self._data or {}
        from .. import build
        return build._merge_scene(self._data, self._scene)

    def _scene_names(self, kind) -> set:
        return {e.get("name") for e in self._scene.get(kind, []) or []
                if isinstance(e, dict) and e.get("name")}

    def _scene_player(self, key) -> bool:
        pl = self._scene.get("player")
        return isinstance(pl, dict) and key in pl

    # the author's words for what a scene.toml key sets (never the key itself)
    _SCENE_WORDS = {"to": "target", "zone": "zone", "message": "message", "entrance": "entrance",
                    "pos": "position"}
    # why a verbatim fork takes no spawn/arrival: the radios' tooltip and a marker drag's refusal
    _VERBATIM_ENTRY = ("a verbatim fork runs the donor's own entry sequence — spawn/arrival rows "
                       "are ignored on it (the donor's real per-door arrivals carry)")
    _PLAYER_WORDS = {"spawn": "the spawn point", "arrival": "the arrival points"}
    _FIELD_ID_PROMPT = "Destination field id (a stock field or one of yours):"

    @staticmethod
    def _blender_says(what):
        return (f"Placed in Blender — the scene.toml sets {what}, so a change here would not "
                "ship. Change it in Blender and re-export, then press F5.")

    def _scene_refusal(self, r, key, thing="this zone"):
        """Why Place must not write ``key`` of canvas row ``r`` (None = delete it), else None.
        ``thing``: what to call a scene-only row the add-on wrote without a name."""
        srow = r.get("scene")
        # No field.toml row to write, named or NOT: the add-on writes no name= for an unnamed
        # gateway or event, so a scene-only row need not match a scene name (review of P2).
        if r.get("data_index") is None:
            name = (srow or {}).get("name") or thing
            return (f"Placed in Blender — {name} lives only in the scene.toml; change or delete "
                    "it in Blender and re-export, then press F5.")
        if srow is None:
            return None
        name = srow.get("name")
        if key is None:
            return (f"Placed in Blender — {name} is in the scene.toml too, so deleting it "
                    "here would still ship the scene's one. Delete it in Blender and re-export, "
                    "then press F5.")
        if key in srow:
            return self._blender_says(f"{name}'s {self._SCENE_WORDS.get(key, key)}")
        return None

    def _refuse_for_scene(self, r, key) -> bool:
        why = self._scene_refusal(r, key)
        if why is None:
            return False
        self._refresh_regions()                     # a dragged quad snaps back to where it ships
        self._refresh(why, "warn")
        return True

    def _on_rkind_toggled(self, on=False):
        self._sync_tool_clusters()
        if on and getattr(self, "status", None) is not None:   # (construction checks one first)
            self._refresh()                       # the status names the kind being drawn

    def _refresh_regions(self):
        """Re-derive the canvas's region feed from the OPEN doc (both region laws judged in
        ``region_rows`` — the overlap starvation and the engine-fan audit)."""
        if self._data is None or self._blocked is not None or self._bundle() is None:
            self._region_rows_cache = []
            self.canvas.set_regions([])
            return
        view = self._view()
        rows = region_rows(view)                     # judged as the build ships them
        for r in rows:
            # the merge keeps the field's rows in order and appends scene-only ones, so a row
            # below the field list's length IS that field row; past it, there is none to write
            n_own = len(self._data.get(r["kind"], []) or [])
            r["data_index"] = r["index"] if r["index"] < n_own else None
            name = (view.get(r["kind"]) or [])[r["index"]].get("name")
            r["scene"] = next((e for e in self._scene.get(r["kind"], []) or []
                               if isinstance(e, dict) and name and e.get("name") == name), None)
            if r["scene"] is not None or r["data_index"] is None:
                r["label"] += " (Blender)"
            if r["data_index"] is None:
                # no field.toml row at all: EVERY gesture is refused (_scene_refusal), so the
                # canvas must not offer one -- no grab cursor, no handles, no menu, no Delete
                r["locked"] = self._scene_refusal(r, None)
        self._region_rows_cache = rows
        self.canvas.set_regions(self._region_rows_cache)

    def _on_region_drawn(self, quad):
        if self._blocked is not None or self._data is None:
            self._refresh()
            return
        # A door with no target, and every event, ask right away (P27): the answer and the zone
        # land as ONE undo step; Cancel keeps the flagged placeholder. Asked BEFORE any write,
        # and the answer goes only to the field it was asked for (the dialog is modal, and the
        # shell can re-feed under it).
        data = self._data
        gateway = self.rkind_btns["gateway"].isChecked()
        to = self.gw_to.value() if gateway else None
        if gateway and not to:
            asked = self._ask_field_id(0)
        elif not gateway:
            asked = self._ask_message("")
        else:
            asked = None
        if self._data is not data:
            # true whether THIS field was reloaded or another one opened under the prompt
            self._refresh("The field changed while you answered — the zone was not drawn.",
                          "warn")
            return
        state = ""
        if gateway:
            to = to or asked or 0
            label = place_gateway(self._data, quad, to, self.gw_ent.value(),
                                  taken=self._scene_names("gateway"))
            note = label + ("" if to else " — set its target ('to field', or the Editor form)")
        else:
            note = label = place_event(self._data, quad, taken=self._scene_names("event"))
            if asked is not None:
                try:
                    set_event_message(self._data, len(self._data["event"]) - 1, asked)
                except ValueError as e:             # the blank-line rule, from its one owner
                    note += (f" — kept the placeholder: {e}. Right-click it → Set message.")
                    state = "warn"
        if self.on_edit:
            self.on_edit(self._member, label)
        self._refresh_regions()
        self._refresh(note, state)

    def _on_region_changed(self, i, quad):
        if self._data is None or not 0 <= i < len(self._region_rows_cache):
            return
        r = self._region_rows_cache[i]
        if self._refuse_for_scene(r, "zone"):
            return
        label = move_zone(self._data, r["kind"], r["data_index"], quad)
        if self.on_edit:
            self.on_edit(self._member, label)
        self._refresh_regions()
        self._refresh(f"{label} · {r['label']}")

    def _on_region_deleted(self, i):
        if self._data is None or not 0 <= i < len(self._region_rows_cache):
            return
        r = self._region_rows_cache[i]
        if self._refuse_for_scene(r, None):
            return
        label = delete_region(self._data, r["kind"], r["data_index"])
        if self.on_edit:
            self.on_edit(self._member, label)
        self._refresh_regions()
        self._refresh(label)

    def _on_region_retarget(self, i):
        if self._data is None or not 0 <= i < len(self._region_rows_cache):
            return
        r = self._region_rows_cache[i]
        if r["kind"] != "gateway" or self._refuse_for_scene(r, "to"):
            return
        cur = (self._data.get("gateway", []) or [])[r["data_index"]].get("to")
        if cur is not None and not isinstance(cur, int):   # "worldmap" (or any non-id): the id
            self._refresh(f"{r['label']} leads to the world map, not a field — change where it "
                          "leads in the Editor form (Gateways).", "warn")   # (the id dialog cannot say it)
            return
        to = self._ask_field_id(cur or 0)
        if to is None:
            return
        label = set_gateway_target(self._data, r["data_index"], to)
        if self.on_edit:
            self.on_edit(self._member, label)
        self._refresh_regions()
        self._refresh(label)

    def _on_region_reword(self, i):
        if self._data is None or not 0 <= i < len(self._region_rows_cache):
            return
        r = self._region_rows_cache[i]
        if r["kind"] != "event" or self._refuse_for_scene(r, "message"):
            return
        cur = (self._data.get("event", []) or [])[r["data_index"]].get("message") or ""
        text = self._ask_message("" if cur == "..." else cur)
        if text is None:
            return
        try:
            label = set_event_message(self._data, r["data_index"], text)
        except ValueError as e:                     # '' builds clean and shows nothing in-game
            self._refresh(f"Kept {r['label']}'s message — {e}. Type the words, or Cancel.", "warn")
            return
        if self.on_edit:
            self.on_edit(self._member, label)
        self._refresh_regions()
        self._refresh(label)

    def _ask_field_id(self, current):
        """Instance dialog behind a seam (a static execs in C++ past every test patch)."""
        from PySide6.QtWidgets import QInputDialog
        dlg = self._field_id_dialog(current)
        if dlg.exec() != QInputDialog.DialogCode.Accepted:
            return None
        return dlg.intValue()

    def _field_id_dialog(self, current):
        """The target prompt as built (apart from its exec, so a test can read what it shows)."""
        from PySide6.QtWidgets import QInputDialog
        dlg = QInputDialog(self)
        dlg.setInputMode(QInputDialog.InputMode.IntInput)
        dlg.setIntRange(1, 32767)
        dlg.setIntValue(max(1, int(current) if isinstance(current, int) and current > 0 else 1))
        dlg.setWindowTitle("Gateway target")
        dlg.setLabelText(self._FIELD_ID_PROMPT)
        return dlg

    def _ask_message(self, current):
        """Instance dialog behind a seam (a static execs in C++ past every test patch)."""
        from PySide6.QtWidgets import QInputDialog
        dlg = QInputDialog(self)
        dlg.setInputMode(QInputDialog.InputMode.TextInput)
        dlg.setTextValue(str(current))
        dlg.setWindowTitle("Event message")
        dlg.setLabelText("The line this zone shows on walk-in:")
        if dlg.exec() != QInputDialog.DialogCode.Accepted:
            return None
        return dlg.textValue()

    def _sync_modes(self):
        """Placement affordances match what the BUILD will honour: a verbatim fork runs the
        donor's own entry sequence, so spawn/arrival are refused there (not silently dropped)."""
        blocked = self._blocked is not None or self._data is None
        for tool in ("place", "regions"):
            self.tools.button(tool).setEnabled(not blocked)
        for key, _label in self.MODES:
            self.mode_btns[key].setEnabled(not blocked)
            self.mode_btns[key].setToolTip(self.MODE_TIPS[key])   # a refusal below never sticks
        for w in (self.rkind_btns["gateway"], self.rkind_btns["event"],
                  self.gw_to, self.gw_ent):
            w.setEnabled(not blocked)
        if not blocked and self._verbatim:
            for key in ("spawn", "arrival"):
                self.mode_btns[key].setEnabled(False)
                self.mode_btns[key].setToolTip(self._VERBATIM_ENTRY)
            if self._mode() in ("spawn", "arrival"):
                self.mode_btns["npc"].setChecked(True)
        if not blocked:                             # a [player] key the scene.toml sets (P2)
            for key in ("spawn", "arrival"):
                if self._scene_player(key):
                    self.mode_btns[key].setEnabled(False)
                    self.mode_btns[key].setToolTip(self._blender_says(self._PLAYER_WORDS[key]))
                    if self._mode() == key:
                        self.mode_btns["npc"].setChecked(True)
        self._on_mode_toggled()
        self.load_btn.setEnabled(not blocked and self._loading is None)

    def _on_surface_clicked(self, payload):
        if self._blocked is not None or self._data is None:
            self._refresh()
            return
        row, picked = self._pick_hit(payload)
        if row is None:
            return
        self._apply_hit(row, picked=picked)

    def _pick_hit(self, payload):
        """``(hit, asked)``: the hit to write, after asking only when the pixel lies over MORE
        THAN ONE floor. A ray through a shared triangle edge meets one floor twice; each floor is
        offered once (the nearest crossing). ``(None, True)`` = the author cancelled."""
        rows, seen = [], set()
        for r in payload.get("stacked") or []:
            key = r.get("floor") if r.get("floor") is not None else ("tri", r.get("tri"))
            if key not in seen:
                seen.add(key)
                rows.append(r)
        if len(rows) <= 1:
            return payload, False
        return self._choose_hit(rows), True

    def _choose_hit(self, rows):
        """A stacked walkmesh under the pixel (a bridge over a floor): the author picks which
        floor the click means, nearest-first with the VISIBLE one marked — never a silent guess.
        What that records is the SPOT where the click meets that floor; only (x, z) is stored,
        and the game finds the height there (review finding P7). Behind a seam so tests drive the
        choice without a popup."""
        menu = QMenu(self)
        note = menu.addAction("Only the spot is stored — the game finds the height there")
        note.setEnabled(False)
        menu.addSeparator()
        acts = []
        for i, r in enumerate(rows):
            tag = "the visible floor" if i == 0 else "the floor behind"
            x, z = r["xz"]
            which = f" (floor {r['floor']})" if r.get("floor") is not None else ""
            acts.append(menu.addAction(f"Where the click meets {tag}{which}: "
                                       f"x {x:.0f}, z {z:.0f}"))
        chosen = menu.exec(QCursor.pos())
        if chosen is None:
            return None
        return rows[acts.index(chosen)]

    def _apply_hit(self, row, picked=False):
        """ONE pure op per drop into the OPEN doc, then the one host callback (the shell
        records the undo step + re-feeds; the marker appears through that round-trip).
        ``picked``: the author chose among stacked floors -- the note says what that recorded."""
        x, z = row["xz"]
        mode = self._mode()
        if mode in ("spawn", "arrival") and self._scene_player(mode):
            self._refresh(self._blender_says(self._PLAYER_WORDS[mode]), "warn")
            return
        if mode == "npc":
            label = place_npc(self._data, x, z, taken=self._scene_names("npc"))
        elif mode == "prop":
            label = place_prop(self._data, x, z)
        elif mode == "spawn":
            label = set_spawn(self._data, x, z)
        else:
            label = set_arrival(self._data, self.ent_box.value(), x, z)
        note = f"{label} at ({int(round(x))}, {int(round(z))})"
        if picked:
            note += (f" · where the click met floor {row['floor']}; only the spot is stored, and "
                     "the game finds the height there")
        if mode == "npc":
            note += " — give it a model and words in the Editor (NPCs)"
        elif mode == "prop":
            note += " — pick its model in the Editor (Props)"
        if self.on_edit:
            self.on_edit(self._member, label)
        self._refresh(note)

    # ---------------------------------------------------------------- markers + status
    def _refresh_markers(self):
        bundle = self._bundle()
        if bundle is None or self._data is None:
            self._marker_rows_cache = []
            self.canvas.set_markers([])
            return
        from ..scene import cam as _cam
        eye = tuple(_cam.decompose(bundle["cam"])["C"])
        blender_npcs = {e.get("name") for e in self._scene.get("npc", []) or []
                        if isinstance(e, dict) and e.get("pos") is not None}
        marks, owners = [], []
        for m in content_markers(self._view()):     # where the BUILD puts each thing (P2)
            x, z = m["xz"]
            y = floor_y_at(bundle["tris"], x, z, eye)
            if y is None:
                continue                            # an empty mesh never got this far, but be safe
            label = m["label"]
            if ((m["kind"] == "npc" and label in blender_npcs)
                    or (m["kind"] in ("spawn", "arrival") and self._scene_player(m["kind"]))):
                label += " (Blender)"
            e = self._marker_owner(m)
            locked = self._marker_why(e, "pos")     # a move refused = every gesture refused
            marks.append({"pos": (x, y, z), "label": label, "kind": m["kind"], "locked": locked,
                          "keep": locked is None and self._marker_why(e, None) is not None,
                          "open": self.on_open is not None})
            owners.append(e)
        self._marker_rows_cache = owners
        self.canvas.set_markers(marks)

    def _marker_owner(self, m) -> dict:
        """The field.toml ROW a marker's gestures write, resolved once from the marker's index
        (the view keeps the field's own rows first, in order: ``build._merge_entities``), and
        held as the object from then on. ``row`` is None where no field.toml row places it."""
        kind, idx = m["kind"], m["index"]
        pl = self._data.get("player") if isinstance(self._data.get("player"), dict) else None
        out = {"kind": kind, "label": m["label"], "row": None, "scene": None, "data_index": None}
        if kind == "spawn":
            out["row"] = None if self._scene_player("spawn") else pl
        elif kind == "arrival":
            own = (pl or {}).get("arrival") or []
            if not self._scene_player("arrival") and idx < len(own):
                out["row"] = own[idx]
        else:
            own = self._data.get(kind) or []
            if idx < len(own):
                out["row"], out["data_index"] = own[idx], idx
            if kind == "npc":                       # npcs merge by name with the scene's (P2)
                out["scene"] = next((e for e in self._scene.get("npc", []) or []
                                     if isinstance(e, dict) and m["label"]
                                     and e.get("name") == m["label"]), None)
        return out

    def _marker_rows(self, e):
        """The live list (or the [player] table) that holds ``e``'s row, read from the OPEN doc."""
        if e["kind"] == "spawn":
            return None
        if e["kind"] == "arrival":
            pl = self._data.get("player")
            return (pl.get("arrival") if isinstance(pl, dict) else None) or []
        return self._data.get(e["kind"]) or []

    def _marker_target(self, i, key):
        """The cache entry a marker gesture writes (``key``: "pos" to move, None to delete), or
        None after saying why not. The row is checked BY IDENTITY against the open doc: an Editor
        delete since the last feed must refuse, never land on the row now at that index."""
        if self._blocked is not None or self._data is None:
            self._refresh()
            return None
        if not 0 <= i < len(self._marker_rows_cache):
            return None
        e = self._marker_rows_cache[i]
        why = self._marker_why(e, key)
        if why is not None:                         # (the canvas already redrew it where it is)
            self._refresh(why, "warn")
            return None
        return e

    def _marker_why(self, e, key):
        """Why a gesture on cache entry ``e`` must not write (``key`` as in _marker_target), else
        None. Judged once: the feed asks it too, so a marker Place always refuses is never drawn
        as a grab handle (review of P16)."""
        why = None
        if e["kind"] in ("spawn", "arrival"):
            if self._verbatim:
                why = self._VERBATIM_ENTRY[0].upper() + self._VERBATIM_ENTRY[1:] + "."
            elif self._scene_player(e["kind"]):
                why = self._blender_says(self._PLAYER_WORDS[e["kind"]])
            elif key is None and e["kind"] == "spawn":
                why = ("The spawn point can be moved but not deleted — drag it to where the "
                       "player should stand.")
        elif e["kind"] == "npc":
            why = self._scene_refusal(e, key, thing="this NPC")
        if why is None:
            rows = self._marker_rows(e)
            here = (self._data.get("player") is e["row"] if rows is None
                    else any(r is e["row"] for r in rows))
            if e["row"] is None or not here:
                why = f"{e['label']} is no longer in this field — nothing changed."
        return why

    @staticmethod
    def _marker_words(e):
        return {"npc": f"NPC {e['label']}", "prop": f"prop {e['label']}"}.get(e["kind"], e["label"])

    def _on_marker_moved(self, i, payload):
        e = self._marker_target(i, "pos")
        if e is None:
            return
        row, _picked = self._pick_hit(payload)
        if row is None:
            return
        x, z = row["xz"]
        label = move_placed(e["row"], "spawn" if e["kind"] == "spawn" else "pos", x, z,
                            self._marker_words(e))
        if self.on_edit:
            self.on_edit(self._member, label)
        self._refresh_markers()
        self._refresh(f"{label} to ({int(round(x))}, {int(round(z))})")

    def _on_marker_deleted(self, i):
        e = self._marker_target(i, None)
        if e is None:
            return
        label = delete_placed(self._marker_rows(e), e["row"], self._marker_words(e))
        if self.on_edit:
            self.on_edit(self._member, label)
        self._refresh_markers()
        self._refresh(label)

    def _on_marker_opened(self, i):
        """The marker menu's Open in the Editor: the row it was drawn from, found BY IDENTITY in
        the open doc (an Editor delete since the feed moved it), handed to the shell."""
        if self.on_open is None or self._data is None or not 0 <= i < len(self._marker_rows_cache):
            return
        e = self._marker_rows_cache[i]
        rows = self._marker_rows(e)
        if e["kind"] in ("spawn", "arrival"):          # [player]'s form holds both
            key = "player"
        else:
            key = next((f"{e['kind']}:{k}" for k, r in enumerate(rows) if r is e["row"]), None)
        if e["row"] is None or key is None:
            self._refresh(f"{e['label']} is no longer in this field — nothing changed.", "warn")
            return
        self.on_open(self._member, key)

    def _on_marker_clicked(self, i):
        """A click ON a placed marker places nothing (P16): say what is there and how to change it."""
        if not 0 <= i < len(self._marker_rows_cache):
            return
        e = self._marker_rows_cache[i]
        name = "the spawn point" if e["kind"] == "spawn" else e["label"]
        locked = self._marker_why(e, "pos")
        if locked is not None:                      # never advertise a drag it will refuse
            self._refresh(f"That is {name}. {locked} Nothing was added.", "warn")
            return
        keep = self._marker_why(e, None) is not None
        if self.on_open is not None:                # the Editor form: a move without a drag
            how = ("drag it to move it, or right-click it to open it in the Editor" if keep
                   else "drag it to move it, or right-click it to delete it or open it in the "
                        "Editor")
        else:
            how = ("drag it to move it" if keep
                   else "drag it to move it, or right-click it to delete it")
        self._refresh(f"That is {name}, already placed — {how}. Nothing was added.")

    def _refresh(self, note="", state=""):
        if self._blocked is not None:
            # protected_reason is the CLI's and the editor's too, and names `ff9mapkit new`: Place
            # keeps its head and words the way out in the app's own terms (finding P22)
            head = self._blocked.split(" -- ")[0]
            way = (" Save a copy in a folder of your own, or start one with Field ▸ New Field."
                   if head != self._blocked else "")
            note = note or f"Placement is off here — {head}.{way}"
            state = state or "warn"
        elif self._member is None:
            note = note or ("Open a field and come back — a fork of a real room, a traced photo, "
                            "a Floorplan room or a Field ▸ New Field scaffold all place here.")
        elif self._bundle() is None:
            note = note or (f"Load the room to place content — {self._room_words()} art, camera "
                            "and walkmesh arrive together.")
        elif not note and self.tools.current() == "regions":
            n = len(self._region_rows_cache)
            warned = sum(1 for r in self._region_rows_cache if r.get("warn"))
            gateway = self.rkind_btns["gateway"].isChecked()
            note = (f"Click 4 corners to draw {'a gateway' if gateway else 'an event'} zone · "
                    f"{n} zone{'' if n == 1 else 's'}")
            if warned:
                note += f" · ⚠ {warned} with law warnings (hover a marked zone)"
            if gateway:
                note += (" · your first two corners make the walk-out edge, drawn thick with an "
                         "arrow (right-click a zone to rotate or delete it)")
            else:
                note += " · right-click a zone to set its message or delete it"
            if self._verbatim:
                note += " · verbatim fork: new content seats below the donor's party band"
        elif not note:
            n = len(content_markers(self._view()))
            note = (f"Click the walkable footprint to place · {n} placed thing"
                    f"{'' if n == 1 else 's'} shown")
            if any(self._marker_why(e, "pos") is None for e in self._marker_rows_cache):
                note += " · drag one to move it, right-click it to delete it"
            if self._verbatim:
                note += " · verbatim fork: new content seats below the donor's party band"
        self.status.setText(note)
        widgets.set_state(self.status, state)
        refused = self._blocked is not None
        self.refused_msg.setText(note if refused else "")
        self.refused_msg.setVisible(refused)
        self.canvas.setVisible(not refused)
        self.status.setVisible(not refused)

    # ---------------------------------------------------------------- shell plumbing
    def crumb_label(self):
        return f"Place — {self._member}" if self._member else "Place"

    def retheme(self, pal):
        self.pal = pal
        self.canvas.retheme(pal)

    def set_scale(self, pct):
        self.canvas.set_scale(pct)
