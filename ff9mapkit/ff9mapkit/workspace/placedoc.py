"""The Place document — click-authoring Rung 3's placement host (studies/click-authoring/PLAN.md).

Content placement on ANY forked real field, on the art: the shell PUSHES the open field.toml
(the BehaviorDoc feed contract — this doc reads no files at construction or tab show), and one
explicit **Load the room** click builds the donor surface off the GUI thread — the composited
background (``extract.compose_background``, per-camera, disk-cached under the provision cache),
the donor's real camera (``extract.cache_field`` → ``camera.bgx``), and its real walkmesh in
RENDER-frame triangles (``imagefield.mesh_world_tris`` — the y-flip lives there, never here).
:class:`~.backdrop.BackdropCanvas` in place mode then raycasts every click against the mesh
(you click what you SEE; a stacked-floor pixel disambiguates through a menu, never a guess).

Writes land in the OPEN doc through PURE ops (:func:`place_npc` / :func:`place_prop` /
:func:`set_spawn` / :func:`set_arrival`) + exactly ONE ``on_edit(member, label)`` per drop —
the shell records the undo step and Save persists through the ordinary editor path, so Place
can never grow a private writer. Refusals are hard and honest: a bundled example / installed
copy (``editor.model.protected_reason``) refuses the whole surface; a field with no donor
(``build.donor_field_id`` — novel fields place via Blender/the Editor) refuses; a VERBATIM
fork refuses spawn/arrival (the donor's own entry sequence runs) while npc/prop stay live —
the build seats them below the donor's party-character band.
"""

from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QCursor, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup, QComboBox, QHBoxLayout, QLabel, QMenu, QPushButton, QRadioButton, QSpinBox,
    QVBoxLayout, QWidget,
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
def place_npc(data: dict, x, z) -> str:
    lst = data.setdefault("npc", [])
    nm = _names.fresh_npc_name(n.get("name") for n in lst if isinstance(n, dict))
    lst.append({"name": nm, "preset": "vivi", "dialogue": "...",
                "pos": [int(round(x)), int(round(z))]})
    return f"place NPC {nm}"


def place_prop(data: dict, x, z) -> str:
    lst = data.setdefault("prop", [])
    lst.append({"name": f"prop{len(lst)}", "prop": _DEFAULT_PROP,
                "pos": [int(round(x)), int(round(z))]})
    return "place prop"


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


# --------------------------------------------------------------------- pure marker derivation
def content_markers(data: dict) -> list:
    """Every placed thing with a floor position -> ``[{"xz", "label", "kind"}]`` (world (x, z);
    the doc resolves height against the loaded walkmesh — :func:`floor_y_at`)."""
    out = []

    def rows(section, kind, label_of):
        for i, e in enumerate(data.get(section, []) or []):
            if isinstance(e, dict) and isinstance(e.get("pos"), (list, tuple)) and len(e["pos"]) >= 2:
                out.append({"xz": (float(e["pos"][0]), float(e["pos"][1])),
                            "label": label_of(e, i), "kind": kind})

    rows("npc", "npc", lambda e, i: e.get("name") or f"npc {i}")
    rows("prop", "prop", lambda e, i: e.get("name") or e.get("prop") or f"prop {i}")
    rows("chest", "chest", lambda e, i: f"chest {i}")
    player = data.get("player") or {}
    sp = player.get("spawn")
    if isinstance(sp, (list, tuple)) and len(sp) >= 2:
        out.append({"xz": (float(sp[0]), float(sp[1])), "label": "spawn", "kind": "spawn"})
    for r in player.get("arrival", []) or []:
        p = r.get("pos") if isinstance(r, dict) else None
        if isinstance(p, (list, tuple)) and len(p) >= 2:
            out.append({"xz": (float(p[0]), float(p[1])),
                        "label": f"arrival {r.get('entrance', 0)}", "kind": "arrival"})
    return out


def floor_y_at(tris, x, z, eye=None):
    """The RENDER-frame height of the walkmesh under plan point (x, z): barycentric containment
    in XZ over ``tris`` (``mesh_world_tris``'s output). Stacked floors resolve to the candidate
    nearest ``eye`` (the camera position — the same visibility bias the raycast has). Falls back
    to the NEAREST VERTEX's y when no triangle contains the point — off-mesh content must still
    show (at its neighbour floor's height), or the author can't see it to fix it. ``None`` only
    on an empty mesh."""
    cands, best_v, best_d = [], None, None
    for a, b, c in tris:
        (ax, ay, az), (bx, by, bz), (cx, cy, cz) = a, b, c
        for vx, vy, vz in (a, b, c):
            d = (vx - x) ** 2 + (vz - z) ** 2
            if best_d is None or d < best_d:
                best_d, best_v = d, vy
        den = (bz - cz) * (ax - cx) + (cx - bx) * (az - cz)
        if abs(den) < 1e-12:
            continue                             # degenerate in plan view (a vertical wall tri)
        w0 = ((bz - cz) * (x - cx) + (cx - bx) * (z - cz)) / den
        w1 = ((cz - az) * (x - cx) + (ax - cx) * (z - cz)) / den
        w2 = 1.0 - w0 - w1
        if min(w0, w1, w2) < -1e-9:
            continue
        cands.append(w0 * ay + w1 * by + w2 * cy)
    if not cands:
        return best_v
    if eye is None or len(cands) == 1:
        return cands[0]
    ex, ey, ez = eye
    return min(cands, key=lambda y: (x - ex) ** 2 + (y - ey) ** 2 + (z - ez) ** 2)


# --------------------------------------------------------------------- the async surface load
class _SurfaceLoader(QObject):
    """One background build of a donor room's place surface (camera + mesh + composited art).
    The thumbs idiom: pure worker logic behind a queued signal; every failure lands as a
    ``failed`` message instead of a crash (a machine without the install degrades honestly)."""

    loaded = Signal(dict)
    failed = Signal(str)

    def start(self, donor, cam_index):
        t = threading.Thread(target=self._work, args=(int(donor), int(cam_index)),
                             name="ff9-place-surface", daemon=True)
        t.start()

    def _work(self, donor, cam_index):
        try:
            self.loaded.emit(build_surface(donor, cam_index))
        except Exception as e:                         # noqa: BLE001 -- no install / bad art / anything
            try:
                self.failed.emit(f"{type(e).__name__}: {e}")
            except RuntimeError:                       # the C++ half died (app exit) -- stop quietly
                pass


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
    return {"donor": donor, "cam_index": ci, "n_cams": len(cams), "cam": cams[ci],
            "png": str(png) if png else None, "tris": tris, "floors": floors}


# --------------------------------------------------------------------- the document
class PlaceDoc(QWidget):
    """Click-to-place on a forked real field's own art. ``on_edit(member, label)`` is the ONE
    write channel — the shell checkpoints the mutation this doc made in the open doc's dict."""

    MODES = (("npc", "NPC"), ("prop", "Prop"), ("spawn", "Spawn"), ("arrival", "Arrival"))

    def __init__(self, pal, *, on_edit, scale=100):
        super().__init__()
        self.pal = pal
        self.on_edit = on_edit
        self._member = None
        self._data = None                       # the OPEN doc's dict (the shell's reference)
        self._path = None
        self._donor = None
        self._blocked = None                    # protected_reason / no-donor text (placement refused)
        self._verbatim = False
        self._bundles = {}                      # (donor, cam_index) -> build_surface dict
        self._cam_pick = {}                     # member -> its chosen camera index
        self._loading = None                    # (donor, ci) in flight, else None
        self._gen = 0                           # bumped per feed: a stale load result is dropped
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

        row = QHBoxLayout()
        row.setSpacing(8)
        self.field_label = QLabel("no field")
        self.field_label.setProperty("role", "muted")
        row.addWidget(self.field_label)
        row.addSpacing(10)
        self.load_btn = QPushButton("Load the room")
        self.load_btn.setToolTip("Extract the donor's camera + walkmesh and composite its "
                                 "background (cached after the first load).")
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
        self.mode_group = QButtonGroup(self)
        self.mode_btns = {}
        for key, label in self.MODES:
            rb = QRadioButton(label)
            rb.setAccessibleName(f"Place {label}")
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
        root.addLayout(row)

        self.canvas = BackdropCanvas(pal, scale=scale)
        self.canvas.surface_clicked.connect(self._on_surface_clicked)
        self.canvas.click_refused.connect(lambda m: self._refresh(m, "warn"))
        root.addWidget(self.canvas, 1)

        self.status = QLabel("")
        self.status.setProperty("role", "muted")
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        self.show_none()

    # ---------------------------------------------------------------- the shell feed
    def show_none(self):
        self._member = self._data = self._path = self._donor = None
        self._blocked = None
        self._verbatim = False
        self._gen += 1
        self.canvas.set_place_mode(False)
        self.canvas.set_surface([])
        self.canvas.set_markers([])
        self.canvas.set_backdrop(None, None)
        self.field_label.setText("no field")
        self._sync_cam_box(1)
        self._sync_modes()
        self._refresh("Open a field (a fork of a real room) and come back — or fork one on the "
                      "Import tab.")

    def show_field(self, member, data, path, *, dirty=False):
        """The one feed: the OPEN doc's parsed dict (by reference — the ops mutate exactly the
        buffer the Editor and Save see). Cheap by design: no disk here (the startup-spend law);
        the donor surface loads on the user's own Load click."""
        same = member == self._member
        from .. import build                        # lazy: the resolver, not the builder
        self._member, self._data = member, data
        self._path = Path(path) if path else None
        self._donor = build.donor_field_id(data)
        self._verbatim = bool(data.get("verbatim_eb"))
        self._blocked = protected_reason(self._path) if self._path else None
        if self._blocked is None and self._donor is None:
            self._blocked = ("this field has no donor real room (no [verbatim_eb] donor / "
                             "[field] source_field / borrow_field) — Place serves forks; a "
                             "novel field places content in Blender or the Editor forms")
        self.field_label.setText(f"{member} — donor field #{self._donor}"
                                 if self._donor is not None else str(member))
        if not same:
            self._gen += 1                          # a stale in-flight load must not land here
            self._loading = None
            self.canvas.set_backdrop(None, None)
            self.canvas.set_surface([])
            self.canvas.set_place_mode(False)
        bundle = self._bundle()
        if bundle is not None and self._blocked is None:
            self._apply_bundle(bundle, refit=not same)
        else:
            self._sync_modes()
            self._refresh()

    # ---------------------------------------------------------------- surface load
    def _cam_index(self):
        return self._cam_pick.get(self._member, 0)

    def _bundle(self):
        if self._donor is None:
            return None
        return self._bundles.get((self._donor, self._cam_index()))

    def on_load(self):
        if self._blocked is not None or self._donor is None or self._data is None:
            self._refresh()
            return
        key = (self._donor, self._cam_index())
        if key in self._bundles:
            self._apply_bundle(self._bundles[key], refit=True)
            return
        if self._loading == key:
            return
        self._loading = key
        self.load_btn.setEnabled(False)
        self._refresh(f"Loading field #{key[0]} (camera {key[1]}) — extracting + compositing…")
        self._loader.start(*key)

    def _on_loaded(self, bundle):
        self._loading = None
        self.load_btn.setEnabled(True)
        self._bundles[(bundle["donor"], bundle["cam_index"])] = bundle
        if bundle["donor"] != self._donor or bundle["cam_index"] != self._cam_index():
            return                                  # the user moved on mid-load: cached, not applied
        self._apply_bundle(bundle, refit=True)

    def _on_load_failed(self, msg):
        self._loading = None
        self.load_btn.setEnabled(True)
        self._refresh(f"Could not load the room: {msg}", "error")

    def _apply_bundle(self, bundle, *, refit):
        pm = QPixmap(bundle["png"]) if bundle["png"] else None
        if pm is not None and pm.isNull():
            pm = None
        self.canvas.set_backdrop(pm, bundle["cam"], refit=refit)
        self.canvas.set_surface(bundle["tris"], bundle["floors"])
        self.canvas.set_place_mode(True)
        self._sync_cam_box(bundle["n_cams"])
        self._sync_modes()
        self._refresh_markers()
        self._refresh()

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
        if self._member is None or i < 0 or i == self._cam_index():
            return
        self._cam_pick[self._member] = int(i)
        self.on_load()                              # cached per (donor, camera) -> instant when warm

    # ---------------------------------------------------------------- placement
    def _mode(self):
        for key, _label in self.MODES:
            if self.mode_btns[key].isChecked():
                return key
        return "npc"

    def _on_mode_toggled(self, _on=False):
        """The entrance spinner belongs to the ARRIVAL mode alone — visible only while it is the
        selected (and permitted) placement."""
        if getattr(self, "ent_box", None) is None:
            return                               # construction order: the radios exist before the spinner
        arrival = self.mode_btns["arrival"].isChecked() and self.mode_btns["arrival"].isEnabled()
        self.ent_box.setVisible(arrival)
        self.ent_label.setVisible(arrival)

    def _sync_modes(self):
        """Placement affordances match what the BUILD will honour: a verbatim fork runs the
        donor's own entry sequence, so spawn/arrival are refused there (not silently dropped)."""
        blocked = self._blocked is not None or self._data is None
        for key, _label in self.MODES:
            self.mode_btns[key].setEnabled(not blocked)
        if not blocked and self._verbatim:
            for key in ("spawn", "arrival"):
                self.mode_btns[key].setEnabled(False)
                self.mode_btns[key].setToolTip(
                    "a verbatim fork runs the donor's own entry sequence — spawn/arrival rows "
                    "are ignored on it (the donor's real per-door arrivals carry)")
            if self._mode() in ("spawn", "arrival"):
                self.mode_btns["npc"].setChecked(True)
        self._on_mode_toggled()
        self.load_btn.setEnabled(not blocked and self._loading is None)

    def _on_surface_clicked(self, payload):
        if self._blocked is not None or self._data is None:
            self._refresh()
            return
        row = payload
        stacked = payload.get("stacked") or []
        if len(stacked) > 1:
            row = self._choose_hit(stacked)
            if row is None:
                return
        self._apply_hit(row)

    def _choose_hit(self, rows):
        """A stacked walkmesh under the pixel (a bridge over a floor): the author picks the
        floor, nearest-first with the VISIBLE one marked — never a silent guess. Behind a seam
        so tests drive the choice without a popup."""
        menu = QMenu(self)
        acts = []
        for i, r in enumerate(rows):
            y = -r["pos"][1]                        # render frame -> world height (the y-flip)
            tag = "visible" if i == 0 else "behind"
            acts.append(menu.addAction(f"floor {r['floor']} · height {y:.0f} ({tag})"))
        chosen = menu.exec(QCursor.pos())
        if chosen is None:
            return None
        return rows[acts.index(chosen)]

    def _apply_hit(self, row):
        """ONE pure op per drop into the OPEN doc, then the one host callback (the shell
        records the undo step + re-feeds; the marker appears through that round-trip)."""
        x, z = row["xz"]
        mode = self._mode()
        if mode == "npc":
            label = place_npc(self._data, x, z)
        elif mode == "prop":
            label = place_prop(self._data, x, z)
        elif mode == "spawn":
            label = set_spawn(self._data, x, z)
        else:
            label = set_arrival(self._data, self.ent_box.value(), x, z)
        note = f"{label} at ({int(round(x))}, {int(round(z))})"
        if row.get("floor") is not None:
            note += f" · floor {row['floor']}"
        if self.on_edit:
            self.on_edit(self._member, label)
        self._refresh(note)

    # ---------------------------------------------------------------- markers + status
    def _refresh_markers(self):
        bundle = self._bundle()
        if bundle is None or self._data is None:
            self.canvas.set_markers([])
            return
        from ..scene import cam as _cam
        eye = tuple(_cam.decompose(bundle["cam"])["C"])
        marks = []
        for m in content_markers(self._data):
            x, z = m["xz"]
            y = floor_y_at(bundle["tris"], x, z, eye)
            if y is None:
                continue                            # an empty mesh never got this far, but be safe
            marks.append({"pos": (x, y, z), "label": m["label"], "kind": m["kind"]})
        self.canvas.set_markers(marks)

    def _refresh(self, note="", state=""):
        if self._blocked is not None:
            note = note or f"Placement is off here — {self._blocked}."
            state = state or "warn"
        elif self._member is None:
            note = note or ("Open a field (a fork of a real room) and come back — or fork one "
                            "on the Import tab.")
        elif self._bundle() is None:
            note = note or ("Load the room to place content — the donor's art, camera, and "
                            "walkmesh arrive together.")
        elif not note:
            n = len(content_markers(self._data or {}))
            note = (f"Click the walkable footprint to place · {n} placed thing"
                    f"{'' if n == 1 else 's'} shown")
            if self._verbatim:
                note += " · verbatim fork: new content seats below the donor's party band"
        self.status.setText(note)
        widgets.set_state(self.status, state)

    # ---------------------------------------------------------------- shell plumbing
    def crumb_label(self):
        return self._member or "Place"

    def retheme(self, pal):
        self.pal = pal
        self.canvas.retheme(pal)

    def set_scale(self, pct):
        self.canvas.set_scale(pct)
