"""The Trace document — click-authoring Rung 1's Workspace host (studies/click-authoring/PLAN.md).

The image→field on-ramp as a first-class surface: open a photo, see the EXACT 384x448
cover-crop the build will use (the same ``imagefield._cover_crop`` code, at the retired HTML
tracer's 2x display resolution — so a traced point IS a build canvas pixel, never a stretch),
click the floor outline on a :class:`~.backdrop.BackdropCanvas` in trace mode, slide the
camera pitch until the dashed horizon sits on the photo's own eye level, then Generate — which
runs the SAME ``py -m ff9mapkit image-field`` CLI the terminal loop uses, streamed through the
shell's ``run_job``. Only this view is Qt; the argv is the tracer's own emitted command.

Laws honoured: no I/O at construction or tab show (the startup-spend law — disk is touched
only by the user's own Open/Generate); file dialogs are INSTANCE dialogs behind the
``_ask_image``/``_ask_out`` seams (a static execs in C++ past every test patch); the canvas
is painted, so CALIBRE arrives via ``set_scale`` and themes via ``retheme`` (the mapview
rule); undo is a host-side history of ``on_floor`` snapshots (the canvas never writes); the
id box validates through ``pack.check_custom_id`` (the shared band validator, not a copy).
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSlider,
    QVBoxLayout, QWidget,
)

from .. import imagefield
from ..scene import cam as _cam
from ..scene import guide
from . import widgets
from .backdrop import BackdropCanvas

PITCH_BAND = (6, 48)             # the tracer's slider band (vanilla room pitches)
_HISTORY_CAP = 100


class TraceDoc(QWidget):
    """Trace a photo into a walkable field, entirely on the art. ``run`` = ``shell.run_job``."""

    def __init__(self, pal, kit_root, *, run, problems=None, scale=100):
        super().__init__()
        self.pal = pal
        self.kit = Path(kit_root)                     # `-m ff9mapkit` cwd (this checkout's package)
        self._run = run
        self._problems = problems
        # Default output base: the repo parent for a checkout; an installed copy writes to a
        # discoverable user folder instead (ImportDoc's own rule, same reason).
        self.proj_base = (self.kit.parent if (self.kit / "pyproject.toml").is_file()
                          else Path.home() / "Dream World IX")
        self._image = None                            # Path of the opened photo (the CLI arg)
        self._img_size = None                         # its ORIGINAL (w, h) — the cut-out frame check
        self._pixmap = None                           # its display cover-crop (2x canvas res)
        self._floor = []                              # mirror of the canvas trace (canvas px)
        self._fg = []                                 # rung 2: [{"contact": (cx, cy), "image": str|None}]
        self._regions = []                            # rung 4: [{"kind", "to", "entrance",
                                                      #   "message", "quad": [(cx, cy)] * 4}] —
                                                      # CANVAS px, the authoring truth (a pitch
                                                      # change re-judges, exactly like vertices)
        self._history = []                            # prior snapshots, one per gesture (undo)
        self._region_rows_cache = []                  # the last judged canvas feed
        self._region_back = []                        # feed row -> self._regions index
        self._project = None                          # {"out", "name", "fid"} after a Generate:
                                                      # later Generates go IN PLACE (no dialog)
        self._stamped = True                          # False = gestures since the last Generate
        self._offer_path = None                       # the OPEN field's toml (the shell's feed)
        self._offer_rejected = None                   # a non-project offer, remembered (no re-parse)
        # The session camera's pose BEYOND pitch. A reopened project restores its own values (a
        # project generated at another distance/fov re-projects through the wrong camera with no
        # exception otherwise -- the exact PLAN.md rung-7 bug); a new photo resets to the default
        # rig. Generate passes them back through the CLI's own --distance/--fov.
        self._distance = imagefield.DEFAULT_DISTANCE
        self._fov = imagefield.DEFAULT_FOV

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 10)
        root.setSpacing(8)
        # ONE line of standing prose — at CALIBRE 150 every fixed row here is height the canvas
        # (the primary surface) loses; the tracing teach lives in the status line's empty state.
        crown, _ = widgets.nameplate(
            "", "Trace",
            "Turn a photo into a walkable field by clicking its floor — the build uses the "
            "exact crop shown here.")
        root.addWidget(crown)

        row = QHBoxLayout()
        row.setSpacing(8)
        self.open_btn = QPushButton("Open an image…")
        self.open_btn.setToolTip("Pick the photo/painting to trace. It appears as the exact "
                                 "384×448 cover-crop the build will use.")
        self.open_btn.clicked.connect(self.on_open)
        row.addWidget(self.open_btn)
        self.offer_btn = QPushButton()                 # "Load <open field>" -- shown by offer_project
        self.offer_btn.setToolTip("Reopen the field currently open in the Editor as a trace "
                                  "session — no navigating to its folder.")
        self.offer_btn.clicked.connect(self.on_offer)
        self.offer_btn.hide()
        row.addWidget(self.offer_btn)
        self.img_label = QLabel("no image")
        self.img_label.setProperty("role", "muted")
        row.addWidget(self.img_label)
        row.addSpacing(12)
        pl = QLabel("Pitch")
        row.addWidget(pl)
        self.pitch = QSlider(Qt.Orientation.Horizontal)
        self.pitch.setObjectName("tracePitch")     # carries the reserved focus ring (style.py)
        self.pitch.setRange(*PITCH_BAND)
        self.pitch.setValue(int(imagefield.DEFAULT_PITCH))
        self.pitch.setAccessibleName("Camera pitch")
        self.pitch.setAccessibleDescription(
            "Downward camera angle in degrees; the dashed horizon line re-derives from it")
        self.pitch.setMinimumWidth(140)
        self.pitch.setToolTip("Slide until the dashed horizon sits on the image's own eye "
                              "level — floor clicks must stay below it.")
        self.pitch.valueChanged.connect(self._on_pitch)
        pl.setBuddy(self.pitch)
        row.addWidget(self.pitch)
        self.pitch_label = QLabel()
        row.addWidget(self.pitch_label)
        row.addStretch(1)
        root.addLayout(row)

        # the TOOLS row (rung 2c/4): the strip + the active tool's own cluster + the gesture
        # verbs — its OWN row, because sharing the photo row squeezed the strip to a blank chip
        # (the snap caught it: an oversubscribed row shaves every control, the round-7 law)
        row = QHBoxLayout()
        row.setSpacing(8)
        # the per-canvas TOOL strip: one explicit click semantic at a time
        self.tools = widgets.ToolStrip(
            [("floor", "Floor", "Trace the walkable floor — click its outline in order, below "
                                "the horizon."),
             ("cutout", "Cut-outs", "Mark a foreground occluder (a pillar, a crate): click where "
                                    "the object MEETS the floor — its base — then attach its "
                                    "full-canvas cut-out PNG. Occlusion flips exactly there."),
             ("regions", "Regions", "Draw trigger quads on the photo — gateways and walk-in "
                                    "events (4 clicks = one zone).")])
        self.tools.changed.connect(self._on_tool)
        row.addWidget(self.tools)
        self.fg_btn = self.tools.button("cutout")      # the Add-cut-out control, now a segment
        # the Regions tool's own cluster (visible only while it is the active tool)
        from PySide6.QtWidgets import QButtonGroup, QRadioButton, QSpinBox
        self.rkind_group = QButtonGroup(self)
        self.rkind_btns = {}
        for key, label in (("gateway", "Gateway"), ("event", "Event")):
            rb = QRadioButton(label)
            rb.setAccessibleName(f"Draw {label} zones")
            rb.toggled.connect(lambda _on=False: self._sync_region_cluster())
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
        self.gw_to.setToolTip("The field id this door sends the player to.")
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
        self.ev_msg = QLineEdit("...")
        self.ev_msg.setMaximumWidth(180)
        self.ev_msg.setAccessibleName("Event message")
        self.ev_msg.setToolTip("The message a drawn event zone shows on walk-in (captured per "
                               "zone as you draw it — the photo lane regenerates its toml, so "
                               "the words live in this session, not in the file).")
        row.addWidget(self.ev_msg)
        row.addStretch(1)
        self.undo_btn = QPushButton("Undo")
        self.undo_btn.setToolTip("Take back the last vertex or cut-out gesture.")
        self.undo_btn.clicked.connect(self.on_undo)
        row.addWidget(self.undo_btn)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setToolTip("Remove every traced vertex (one Undo brings them back).")
        self.clear_btn.clicked.connect(self.on_clear)
        row.addWidget(self.clear_btn)
        root.addLayout(row)

        # rung 2's strip: the marked cut-outs (hidden until one exists — canvas height is precious)
        fg_row = QHBoxLayout()
        fg_row.setSpacing(8)
        self.fg_label = QLabel("Cut-outs")
        fg_row.addWidget(self.fg_label)
        self.fg_box = QComboBox()
        self.fg_box.setAccessibleName("Foreground cut-outs")
        self.fg_box.setToolTip("Each marked occluder: its floor-contact pixel, the overlay depth "
                              "the build will emit, and its attached cut-out PNG.")
        self.fg_box.setMinimumWidth(260)
        self.fg_label.setBuddy(self.fg_box)
        fg_row.addWidget(self.fg_box)
        self.fg_attach_btn = QPushButton("Attach PNG…")
        self.fg_attach_btn.setToolTip("Attach the selected contact's cut-out — a full-canvas PNG "
                                      "with alpha (only the object opaque).")
        self.fg_attach_btn.clicked.connect(self.on_fg_attach)
        fg_row.addWidget(self.fg_attach_btn)
        self.fg_remove_btn = QPushButton("Remove")
        self.fg_remove_btn.setToolTip("Remove the selected cut-out contact (one Undo brings it back).")
        self.fg_remove_btn.clicked.connect(self.on_fg_remove)
        fg_row.addWidget(self.fg_remove_btn)
        self.fg_show = QCheckBox("Show")
        self.fg_show.setChecked(True)
        self.fg_show.setToolTip("Preview the cut-outs on the art (uncheck to trace a vertex "
                                "hiding under one).")
        self.fg_show.toggled.connect(lambda _on: self._refresh_cutouts())
        fg_row.addWidget(self.fg_show)
        fg_row.addStretch(1)
        root.addLayout(fg_row)
        self._fg_widgets = (self.fg_label, self.fg_box, self.fg_attach_btn, self.fg_remove_btn,
                            self.fg_show)

        self.canvas = BackdropCanvas(pal, scale=scale, on_floor=self._on_floor)
        self.canvas.set_trace_mode(True)
        self.canvas.set_backdrop(None, self._camera())   # pure math — no disk at construction
        self.canvas.click_refused.connect(self._on_refused)
        self.canvas.contact_clicked.connect(self._on_contact)
        self.canvas.cutout_moved.connect(self._on_cutout_moved)
        self.canvas.contact_moved.connect(self._on_contact_moved)
        self.canvas.region_drawn.connect(self._on_region_drawn)
        self.canvas.region_changed.connect(self._on_region_changed)
        self.canvas.region_deleted.connect(self._on_region_deleted)
        self.canvas.region_retarget.connect(self._on_region_retarget)
        self.canvas.region_reword.connect(self._on_region_reword)
        root.addWidget(self.canvas, 1)
        self._sync_region_cluster()                    # the boxes exist now: settle visibility

        out_row = QHBoxLayout()
        out_row.setSpacing(8)
        nl = QLabel("Name")
        out_row.addWidget(nl)
        self.name_box = QLineEdit("PICTURE")
        self.name_box.setMaximumWidth(160)
        self.name_box.setAccessibleName("Field name")
        self.name_box.setToolTip("The generated project's field name (<name>.field.toml).")
        nl.setBuddy(self.name_box)
        out_row.addWidget(self.name_box)
        il = QLabel("Field id")
        out_row.addWidget(il)
        self.id_box = QLineEdit("30058")
        self.id_box.setMaximumWidth(90)
        self.id_box.setAccessibleName("Field id")
        self.id_box.setToolTip(widgets.BAND_HINT)
        il.setBuddy(self.id_box)
        out_row.addWidget(self.id_box)
        self.gen_btn = QPushButton("Generate field project…")
        self.gen_btn.clicked.connect(self.on_generate)
        out_row.addWidget(self.gen_btn)
        out_row.addStretch(1)
        root.addLayout(out_row)

        self.status = QLabel("Open an image to begin.")
        self.status.setProperty("role", "muted")
        root.addWidget(self.status)
        self._refresh()

    # ------------------------------------------------------------------ camera + status
    def _camera(self):
        return guide.make_camera(float(self.pitch.value()), self._distance,
                                 fov_x_deg=self._fov)

    def _valid_count(self):
        """(valid, bad): vertices below/above the current camera's horizon."""
        cam = self.canvas.camera()
        good = bad = 0
        for p in self._floor:
            try:
                imagefield.click_to_world(cam, p)
                good += 1
            except imagefield.ImageFieldError:
                bad += 1
        return good, bad

    def _fg_state(self, fg):
        """A contact judged against the CURRENT camera -> ``(z, err)`` (one of them None). Derived
        per refresh, never stored — a pitch change re-judges every contact exactly as it re-judges
        the trace (an anchored z is camera-dependent; a stale one would lie in the argv)."""
        try:
            return imagefield.occluder_z(self.canvas.camera(), fg["contact"]), None
        except imagefield.ImageFieldError as e:
            return None, str(e)

    def _photo_wh(self):
        return self._img_size or (imagefield.CANVAS_W, imagefield.CANVAS_H)

    def _canvas_scale(self):
        """Photo px -> logical canvas px: the photo's own cover scale (the same factor the build
        applies at 4x, so a snip previews at exactly the size it will ship)."""
        pw, ph = self._photo_wh()
        return max(imagefield.CANVAS_W / pw, imagefield.CANVAS_H / ph)

    def _attach_cutout(self, i, path):
        """Classify + wire an attached PNG. Photo-frame aspect -> REGISTERED (fills the frame,
        pixel-for-pixel where the artist painted it, inert). Anything else -> a positionable
        SNIP: shown at its natural photo scale with its base parked on the contact, draggable —
        the first playtest's 531x473 object crop is a feature now, not a giant dog. Returns a
        short teach note for snips (None for registered)."""
        from PIL import Image
        with Image.open(path) as im:
            sw, sh = im.size
        f = self._fg[i]
        f["image"] = str(path)
        f["size"] = (sw, sh)
        f["pm"] = QPixmap(str(path))
        pw, ph = self._photo_wh()
        if abs(sw / sh - pw / ph) <= 0.02 * (pw / ph):
            f["kind"], f["offset"] = "full", None
            return None
        k = self._canvas_scale()
        cx, cy = f["contact"]
        f["kind"] = "snip"
        f["offset"] = (round(cx - sw * k / 2, 1), round(cy - sh * k, 1))
        return "a snip — drag it into place on the art (its contact anchor rides along)"

    def _fg_problems(self):
        """(invalid, unattached) counts across the marked cut-outs — the Generate gates."""
        invalid = sum(1 for f in self._fg if self._fg_state(f)[1] is not None)
        unattached = sum(1 for f in self._fg if not f.get("image"))
        return invalid, unattached

    def _refresh(self, note="", state=""):
        hy = _cam.horizon_canvas_y(self.canvas.camera())
        pose = ("" if (self._distance, self._fov) ==
                (imagefield.DEFAULT_DISTANCE, imagefield.DEFAULT_FOV)
                else f" · distance {self._distance:g} · fov {self._fov:g}")
        self.pitch_label.setText(
            (f"{self.pitch.value()}° · horizon y {hy:.0f}" if 0 <= hy < imagefield.CANVAS_H
             else f"{self.pitch.value()}° · horizon above the frame") + pose)
        good, bad = self._valid_count()
        fg_invalid, fg_unattached = self._fg_problems()
        _shim, _back, rg_bad = self._region_shim()
        rg_untargeted = sum(1 for r in self._regions
                            if r["kind"] == "gateway" and not r.get("to"))
        ready = (self._image is not None and good >= 3 and bad == 0
                 and fg_invalid == 0 and fg_unattached == 0 and rg_bad == 0
                 and rg_untargeted == 0)
        self.gen_btn.setEnabled(ready)
        self.gen_btn.setText(f"Regenerate {self._project['name']} — in place"
                             if self._project else "Generate field project…")
        if ready and self._project:
            tip = (f"Rebuild {self._project['out']} with the current trace/cut-outs — no "
                   f"dialog (open a new image to start a different project).")
        elif ready:
            tip = ("Build the field project (walkmesh + art + field.toml) with the exact command "
                   "the CLI tracer emits — it streams to the Output panel.")
        elif fg_invalid or fg_unattached:
            tip = ("Every cut-out needs a valid floor contact (below the horizon, below the base "
                   "layer) and an attached PNG — fix or Remove the flagged ones.")
        elif rg_untargeted:
            tip = ("A drawn door has NO target field — it would compile to Field(0), a "
                   "guaranteed black screen. Right-click the quad → Set gateway target.")
        elif rg_bad:
            tip = ("A region has a corner above the horizon at this pitch — reshape or delete "
                   "it (right-click the quad).")
        else:
            tip = "Needs an open image and at least 3 traced vertices, all below the horizon."
        self.gen_btn.setToolTip(tip)
        self.undo_btn.setEnabled(bool(self._history))
        self.clear_btn.setEnabled(bool(self._floor))
        for key in ("cutout", "regions"):
            self.tools.button(key).setEnabled(self._image is not None)
        self._refresh_fg_strip()
        if not note:
            if self._image is None:
                note = "Open an image to begin."
            elif not self._floor:
                note = ("Click the floor's outline in order, below the dashed horizon — "
                        "drag a vertex to adjust, right-click one to delete it.")
            else:
                note = f"{good} vertices traced" + (f" · {bad} above the horizon (red)" if bad
                                                    else "")
                if self._fg:
                    note += f" · {len(self._fg)} cut-out{'' if len(self._fg) == 1 else 's'}"
                    if fg_invalid:
                        note += f" · {fg_invalid} contact{'' if fg_invalid == 1 else 's'} invalid"
                    if fg_unattached:
                        note += f" · {fg_unattached} PNG{'' if fg_unattached == 1 else 's'} missing"
                if self._regions:
                    note += f" · {len(self._regions)} region{'' if len(self._regions) == 1 else 's'}"
                    warned = sum(1 for r in getattr(self, '_region_rows_cache', []) if r.get("warn"))
                    if rg_untargeted:
                        note += (f" · ⚠ {rg_untargeted} door{'' if rg_untargeted == 1 else 's'} "
                                 f"without a target (right-click → Set gateway target)")
                    if warned:
                        note += f" · ⚠ {warned} with law warnings"
                    if rg_bad:
                        note += f" · {rg_bad} above the horizon"
        if self._project and not self._stamped:        # edits the project on disk doesn't have
            note += f" · ⚠ not stamped — Regenerate {self._project['name']} to update the project"
            state = state or "warn"
        self.status.setText(note)
        widgets.set_state(self.status, state)

    def _refresh_fg_strip(self):
        """The cut-out strip: hidden until a contact exists; each row names its pixel, the derived
        overlay z (or why it has none), and its PNG (or the gap)."""
        show = bool(self._fg)
        for w in self._fg_widgets:
            w.setVisible(show)
        keep = self.fg_box.currentIndex()
        self.fg_box.blockSignals(True)
        self.fg_box.clear()
        for i, f in enumerate(self._fg):
            cx, cy = f["contact"]
            z, err = self._fg_state(f)
            head = f"fg{i} @ ({cx:g},{cy:g})"
            head += f" · z {z}" if err is None else " · ⚠ invalid contact"
            head += f" · {Path(f['image']).name}" if f.get("image") else " · ⚠ needs its PNG"
            if f.get("kind") == "snip":
                head += " · snip"
            self.fg_box.addItem(head)
        if 0 <= keep < self.fg_box.count():
            self.fg_box.setCurrentIndex(keep)
        elif self.fg_box.count():
            self.fg_box.setCurrentIndex(self.fg_box.count() - 1)
        self.fg_box.blockSignals(False)
        has = self.fg_box.currentIndex() >= 0
        self.fg_attach_btn.setEnabled(has)
        self.fg_remove_btn.setEnabled(has)

    def _refresh_cutouts(self):
        """The canvas's cut-out furniture: attached PNGs PREVIEWED on the art (a registered
        full-frame fills it; a snip sits at its rect and drags) + a draggable contact handle per
        cut-out labelled with the derived z (INVALID marks red, exactly like a bad vertex)."""
        show = self.fg_show.isChecked()
        k = self._canvas_scale()
        out = []
        for i, f in enumerate(self._fg):
            z, err = self._fg_state(f)
            rect = None
            if f.get("kind") == "snip" and f.get("offset") and f.get("size"):
                sw, sh = f["size"]
                rect = (f["offset"][0], f["offset"][1], sw * k, sh * k)
            out.append({"i": i, "pixmap": (f.get("pm") if show else None), "rect": rect,
                        "contact": f["contact"],
                        "label": f"fg{i} · z {z}" if err is None else f"fg{i} · no floor",
                        "bad": err is not None,
                        "locked": f.get("kind") != "snip"})
        self.canvas.set_cutouts(out)

    def _on_cutout_moved(self, i, x, y):
        """A snip drag ended: ONE undoable gesture — the image moves AND its contact anchor
        rides by the same delta (the base line travels with the object; z re-derives)."""
        if not 0 <= i < len(self._fg) or self._fg[i].get("offset") is None:
            return
        self._push_history()
        ox, oy = self._fg[i]["offset"]
        cx, cy = self._fg[i]["contact"]
        self._fg[i]["offset"] = (round(x, 1), round(y, 1))
        self._fg[i]["contact"] = (round(cx + (x - ox), 1), round(cy + (y - oy), 1))
        z, err = self._fg_state(self._fg[i])
        self._refresh_cutouts()
        self._refresh(err if err else f"fg{i} moved → z {z}", "error" if err else "")

    def _on_contact_moved(self, i, cx, cy):
        """A contact-handle drag ended: re-anchor the depth alone (the image stays put) — for
        tuning where the flip line sits under an already-placed object."""
        if not 0 <= i < len(self._fg):
            return
        self._push_history()
        self._fg[i]["contact"] = (round(cx, 1), round(cy, 1))
        z, err = self._fg_state(self._fg[i])
        self._refresh_cutouts()
        self._refresh(err if err else f"fg{i} re-anchored → z {z}", "error" if err else "")

    # ------------------------------------------------------------------ image
    def on_open(self):
        path = self._ask_image()
        if path:
            try:
                if str(path).endswith(".trace.json"):  # a generated project's session record
                    self.load_trace(path)
                elif str(path).endswith(".toml"):      # the project's field.toml works too
                    self.load_project(path)
                else:
                    self.load_image(path)
            except Exception as e:                     # noqa: BLE001 -- a bad file must not crash the tab
                self._refresh(f"Could not open {Path(path).name}: {e}", "error")

    def load_image(self, path):
        """The one image ingest: the SAME cover-crop the build performs, at 2x display res.
        Opening a new image clears the trace (the old polygon means nothing on new art)."""
        from PIL import Image
        src = Image.open(path).convert("RGB")
        self._img_size = src.size
        disp = imagefield._cover_crop(src, imagefield.CANVAS_W * 2, imagefield.CANVAS_H * 2)
        buf = io.BytesIO()
        disp.save(buf, "PNG")
        pm = QPixmap()
        pm.loadFromData(buf.getvalue(), "PNG")
        self._image = Path(path)
        self._pixmap = pm
        self._floor = []
        self._fg = []                                  # old contacts mean nothing on new art
        self._regions = []                             # nor do old zones
        self._history = []
        self._project = None                           # a new photo is a NEW project
        self._distance = imagefield.DEFAULT_DISTANCE   # a new photo shoots on the default rig
        self._fov = imagefield.DEFAULT_FOV
        self.tools.set_current("floor")
        self.canvas.set_floor([])
        self.canvas.set_cutouts([])
        self.canvas.set_regions([])
        self._region_rows_cache, self._region_back = [], []
        self.canvas.set_backdrop(pm, self._camera(), refit=True)
        self.img_label.setText(self._image.name)
        self._refresh()

    def _on_pitch(self, _v):
        self._stamped = False                          # a camera change alters the build
        self.canvas.set_backdrop(self._pixmap, self._camera(), refit=False)
        self._refresh_cutouts()                        # anchored z's are camera-dependent
        self._refresh_regions()                        # zone worlds re-judge with the horizon
        self._refresh()

    # ------------------------------------------------------------------ trace + contact gestures
    def _push_history(self):
        """One snapshot per completed gesture — floor, cut-outs AND regions together, so Undo
        walks back through every gesture kind in the order they happened."""
        self._history.append({"floor": list(self._floor), "fg": [dict(f) for f in self._fg],
                              "regions": [dict(r) for r in self._regions]})
        del self._history[:-_HISTORY_CAP]
        self._stamped = False                          # a gesture the project doesn't have yet

    def _on_floor(self, pts):
        self._push_history()
        self._floor = list(pts)
        self._refresh()

    def _on_refused(self, msg):
        self._refresh(msg, "warn")

    def on_undo(self):
        if not self._history:
            return
        snap = self._history.pop()
        self._floor = list(snap["floor"])
        self._fg = [dict(f) for f in snap["fg"]]
        self._regions = [dict(r) for r in snap.get("regions", [])]
        self.canvas.set_floor(self._floor)             # the host write path: no on_floor echo
        self._refresh_cutouts()
        self._refresh_regions()
        self._refresh()

    def on_clear(self):
        if not self._floor:
            return
        self._push_history()
        self._floor = []
        self.canvas.set_floor([])
        self._refresh()

    # ------------------------------------------------------------------ the tool strip
    def _on_tool(self, key):
        """ONE owner of tool -> canvas click semantics (the strip made the mode explicit —
        rung 2c's owner ask, mandatory once regions became a fourth semantic)."""
        if key == "cutout":
            self.canvas.set_contact_mode(True)
            self._sync_region_cluster()
            self._refresh("Click where the object MEETS the floor — its base, not up its body.")
            return
        if key == "regions":
            self.canvas.set_region_mode(True)
        else:
            self.canvas.set_trace_mode(True)
        self._sync_region_cluster()
        self._refresh()

    def _sync_region_cluster(self):
        """The Regions tool's own boxes show only while it is active (visibility swaps — a row
        that grows on selection shrinks the canvas out from under itself)."""
        if getattr(self, "ev_msg", None) is None:
            return                                 # construction order: radios fire before the boxes
        on = self.tools.current() == "regions"
        gw = on and self.rkind_btns["gateway"].isChecked()
        for w in (self.rkind_btns["gateway"], self.rkind_btns["event"]):
            w.setVisible(on)
        for w in (self.gw_to_label, self.gw_to, self.gw_ent_label, self.gw_ent):
            w.setVisible(gw)
        self.ev_msg.setVisible(on and not gw)

    # ------------------------------------------------------------------ rung 4: trigger regions
    def _region_worlds(self, quad_px):
        """A stored canvas-px quad -> world corners under the CURRENT camera, or None where a
        corner sits above the horizon (a pitch change re-judges regions exactly like vertices)."""
        cam = self.canvas.camera()
        out = []
        for p in quad_px:
            try:
                out.append(imagefield.click_to_world(cam, p))
            except imagefield.ImageFieldError:
                out.append(None)
        return out

    def _region_shim(self):
        """The session's regions as the doc-dict shape ``placedoc.region_rows`` judges — ONE
        owner of the labels + both region laws for every host. Returns (shim, map) where map
        takes the shim's (kind, per-kind index) back to ``self._regions`` indices; rows with an
        above-horizon corner are left OUT of the shim (counted in the status instead)."""
        shim = {"gateway": [], "event": []}
        back = {}
        bad = 0
        for ri, r in enumerate(self._regions):
            worlds = self._region_worlds(r["quad"])
            if any(w is None for w in worlds):
                bad += 1
                continue
            zone = [[int(round(x)), int(round(z))] for x, z in worlds]
            kind = r["kind"]
            row = {"name": f"door{len(shim['gateway'])}" if kind == "gateway"
                   else f"zone{len(shim['event'])}", "zone": zone}
            if kind == "gateway":
                row["to"] = r.get("to", 0)
                if r.get("entrance"):
                    row["entrance"] = r["entrance"]
            else:
                row["message"] = r.get("message") or "..."
            back[(kind, len(shim[kind]))] = ri
            shim[kind].append(row)
        return shim, back, bad

    def _refresh_regions(self):
        """Feed the canvas from the session's regions, laws judged (the placedoc derivation —
        one owner). The row list is kept for gesture routing."""
        from . import placedoc
        shim, back, _bad = self._region_shim()
        rows = placedoc.region_rows(shim)
        self._region_rows_cache = rows
        self._region_back = [back[(r["kind"], r["index"])] for r in rows]
        self.canvas.set_regions(rows)

    def _on_region_drawn(self, quad_world):
        """Four accepted clicks: store the quad in CANVAS px (the authoring truth — the exact
        inverse of the click conversion, so the round-trip is the tripwire's own)."""
        cam = self.canvas.camera()
        quad_px = [tuple(round(v, 1) for v in imagefield.world_to_click(cam, w))
                   for w in quad_world]
        self._push_history()
        kind = "gateway" if self.rkind_btns["gateway"].isChecked() else "event"
        self._regions.append({"kind": kind, "to": self.gw_to.value(),
                              "entrance": self.gw_ent.value(),
                              "message": self.ev_msg.text().strip() or "...",
                              "quad": quad_px})
        self._refresh_regions()
        note = "drew a gateway zone" if kind == "gateway" else "drew an event zone"
        if kind == "gateway" and not self.gw_to.value():
            note += " — set its target field id (the 'to field' box)"
        self._refresh(note)

    def _on_region_changed(self, i, quad_world):
        if not 0 <= i < len(getattr(self, "_region_back", [])):
            return
        cam = self.canvas.camera()
        try:
            quad_px = [tuple(round(v, 1) for v in imagefield.world_to_click(cam, w))
                       for w in quad_world]
        except imagefield.ImageFieldError:
            return                                     # a corner behind the camera: keep the old quad
        self._push_history()
        self._regions[self._region_back[i]]["quad"] = quad_px
        self._refresh_regions()
        self._refresh("region reshaped")

    def _on_region_deleted(self, i):
        if not 0 <= i < len(getattr(self, "_region_back", [])):
            return
        self._push_history()
        del self._regions[self._region_back[i]]
        self._refresh_regions()
        self._refresh("region deleted")

    def _on_region_retarget(self, i):
        """Retarget a drawn door in place (the Field(0) black-screen lesson: the 'to field' box
        feeds NEW draws only, so an already-drawn door needs its own edit path)."""
        if not 0 <= i < len(getattr(self, "_region_back", [])):
            return
        r = self._regions[self._region_back[i]]
        if r["kind"] != "gateway":
            return
        to = self._ask_field_id(r.get("to") or 0)
        if to is None:
            return
        self._push_history()
        r["to"] = int(to)
        self._refresh_regions()
        self._refresh(f"door retargeted -> field {int(to)}")

    def _on_region_reword(self, i):
        """Reword a drawn event zone in place (its message lives in this SESSION — the photo
        lane's toml is regenerated, so there is no other editor for it)."""
        if not 0 <= i < len(getattr(self, "_region_back", [])):
            return
        r = self._regions[self._region_back[i]]
        if r["kind"] != "event":
            return
        cur = r.get("message") or ""
        text = self._ask_message("" if cur == "..." else cur)
        if text is None:
            return
        self._push_history()
        r["message"] = text.strip() or "..."
        self._refresh_regions()
        self._refresh("event reworded")

    def _ask_field_id(self, current):
        """Instance dialog behind a seam (a static execs in C++ past every test patch)."""
        from PySide6.QtWidgets import QInputDialog
        dlg = QInputDialog(self)
        dlg.setInputMode(QInputDialog.InputMode.IntInput)
        dlg.setIntRange(1, 32767)
        dlg.setIntValue(max(1, int(current) if isinstance(current, int) and current > 0 else 1))
        dlg.setWindowTitle("Gateway target")
        dlg.setLabelText("Destination field id (a stock field or one of yours —\n"
                         "reference/field-manifest.tsv names the stock ones):")
        if dlg.exec() != QInputDialog.DialogCode.Accepted:
            return None
        return dlg.intValue()

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

    # ------------------------------------------------------------------ rung 2: cut-out contacts

    def _on_contact(self, cx, cy):
        """A contact click, judged through the ONE owner (``imagefield.occluder_z``): above the
        horizon or at/behind the base layer refuses with the CLI's own message and stays armed
        for a retry; a good contact records ONE undoable gesture and asks for its PNG."""
        contact = (round(cx, 1), round(cy, 1))
        try:
            z = imagefield.occluder_z(self.canvas.camera(), contact)
        except imagefield.ImageFieldError as e:
            self._refresh(str(e), "error")
            return
        self._push_history()
        self._fg.append({"contact": contact, "image": None})
        self.tools.set_current("floor")                # one contact per arm -> back to tracing
        self.fg_box.setCurrentIndex(len(self._fg) - 1)
        path = self._ask_cutout()
        teach = None
        if path:
            teach = self._attach_cutout(len(self._fg) - 1, path)
        note = (f"cut-out fg{len(self._fg) - 1} anchored at ({contact[0]:g},{contact[1]:g})"
                f" → z {z}" + ("" if path else " — attach its PNG before Generate"))
        if teach:
            note += f" · {teach}"
        self._refresh_cutouts()
        self._refresh(note)

    def on_fg_attach(self):
        i = self.fg_box.currentIndex()
        if not 0 <= i < len(self._fg):
            return
        path = self._ask_cutout()
        if not path:
            return
        self._push_history()
        teach = self._attach_cutout(i, path)
        self._refresh_cutouts()
        self._refresh(f"fg{i}: {teach}" if teach else "")

    def on_fg_remove(self):
        i = self.fg_box.currentIndex()
        if not 0 <= i < len(self._fg):
            return
        self._push_history()
        del self._fg[i]
        self._refresh_cutouts()
        self._refresh()

    # ------------------------------------------------------------------ generate
    def on_generate(self):
        if self._image is None:
            self._refresh("Open an image first.", "error")
            return
        good, bad = self._valid_count()
        if good < 3 or bad:
            self._refresh("Trace at least 3 vertices, all below the horizon.", "error")
            return
        fg_invalid, fg_unattached = self._fg_problems()
        if fg_invalid or fg_unattached:
            self._refresh("Every cut-out needs a valid contact and an attached PNG — fix or "
                          "Remove the flagged ones.", "error")
            return
        from .. import pack
        try:
            fid = pack.check_custom_id(self.id_box.text())
        except ValueError as e:
            self._refresh(str(e), "error")
            return
        name = self.name_box.text().strip() or "PICTURE"
        if self._project is not None:                  # set up once -> every later Generate is
            out = Path(self._project["out"])           # IN PLACE (owner-asked; no dialog)
        else:
            parent = self._ask_out()
            if not parent:
                return
            out = Path(parent) / f"{self._image.stem}-field"
        argv = [sys.executable, "-m", "ff9mapkit", "image-field", str(self._image),
                "--floor", " ".join(f"{x:g},{y:g}" for x, y in self._floor),
                "--out", str(out), "--name", name, "--id", str(fid)]
        for i, f in enumerate(self._fg):               # the tracer's own form: path@cx,cy anchors
            cx, cy = f["contact"]                      # the occluder at its floor-contact pixel
            img = f["image"]
            if f.get("kind") == "snip":                # a placed snip ships as a composed full frame
                img = str(self._composed_fg_path(i, f))
            argv += ["--foreground", f"{img}@{cx:g},{cy:g}"]
        for r in self._regions:                        # zones ride in canvas px, the same frame as
            pts = ";".join(f"{cx:g},{cy:g}" for cx, cy in r["quad"])   # --floor (pitch-coupled)
            if r["kind"] == "gateway":
                head = f"{r.get('to', 0)},{r['entrance']}" if r.get("entrance") else str(r.get("to", 0))
                argv += ["--gateway", f"{head}@{pts}"]
            else:
                argv += ["--event-zone", f"{r.get('message') or '...'}@{pts}"]
        if float(self.pitch.value()) != imagefield.DEFAULT_PITCH:
            argv += ["--pitch", f"{self.pitch.value():g}"]
        if float(self._fov) != imagefield.DEFAULT_FOV:        # a reopened project regenerates
            argv += ["--fov", f"{self._fov:g}"]               # through its OWN rig, not the
        if float(self._distance) != imagefield.DEFAULT_DISTANCE:   # default one
            argv += ["--distance", f"{self._distance:g}"]
        started = self._run(
            argv, cwd=str(self.kit), subject="Image → field",
            ok_headline=f"{name} generated → {out}",
            ok_next=f"Deploy it: py tools/deploy_field.py {out / (name + '.field.toml')} "
                    f"--id {fid} — then ~ → Warp to field → {fid}.",
            fail_hint="See the Output panel — the usual causes are a vertex above the horizon "
                      "or a floor larger than the Int16 world bound.")
        if started:
            self._project = {"out": str(out), "name": name, "fid": int(fid)}
            self._stamped = True                       # the project now matches the session
            self._write_trace_sidecar(out)             # the re-editable session record
            self._refresh(f"Generating {name} → {out} …")

    def _write_trace_sidecar(self, out):
        """The tab's session as ``<out>/<image-stem>.trace.json`` — floor, pitch, cut-outs
        (contacts + offsets + PNG paths), name/id — so Open can restore the whole editable
        state later (the 'set it up once' half of in-place regeneration). Best-effort: a
        sidecar failure must never block the build itself."""
        import json
        try:
            Path(out).mkdir(parents=True, exist_ok=True)
            fg = [{"contact": list(f["contact"]), "image": f.get("image"),
                   "offset": (list(f["offset"]) if f.get("offset") else None)}
                  for f in self._fg]
            (Path(out) / f"{self._image.stem}.trace.json").write_text(json.dumps({
                "image": str(self._image), "pitch": self.pitch.value(),
                "distance": self._distance, "fov": self._fov,
                "floor": [list(p) for p in self._floor], "fg": fg,
                "regions": [{"kind": r["kind"], "to": r.get("to", 0),
                             "entrance": r.get("entrance", 0),
                             "message": r.get("message", "..."),
                             "quad": [list(p) for p in r["quad"]]} for r in self._regions],
                "name": self.name_box.text().strip() or "PICTURE",
                "id": self.id_box.text().strip()}, indent=2), encoding="utf-8")
        except OSError:
            pass

    def load_trace(self, path):
        """Reopen a generated project's ``.trace.json``: the photo, floor, pitch, cut-outs
        (with their dragged offsets), name/id — and the project itself, so the next Generate
        goes straight IN PLACE."""
        import json
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        self.load_image(data["image"])                 # clears floor/fg/history/project
        self._distance = float(data.get("distance", imagefield.DEFAULT_DISTANCE))
        self._fov = float(data.get("fov", imagefield.DEFAULT_FOV))
        self.pitch.setValue(int(data.get("pitch", imagefield.DEFAULT_PITCH)))
        # setValue only re-feeds the canvas when the pitch CHANGED -- the pose must land either way
        self.canvas.set_backdrop(self._pixmap, self._camera(), refit=False)
        self._floor = [tuple(p) for p in data.get("floor", [])]
        self.canvas.set_floor(self._floor)
        for e in data.get("fg", []):
            self._fg.append({"contact": tuple(e["contact"]), "image": None})
            if e.get("image") and Path(e["image"]).is_file():
                self._attach_cutout(len(self._fg) - 1, e["image"])
                if e.get("offset") and self._fg[-1].get("offset") is not None:
                    self._fg[-1]["offset"] = tuple(e["offset"])   # the dragged spot wins
        self._regions = [{"kind": r.get("kind", "gateway"), "to": int(r.get("to", 0)),
                          "entrance": int(r.get("entrance", 0)),
                          "message": str(r.get("message", "...")),
                          "quad": [tuple(p) for p in r.get("quad", [])]}
                         for r in data.get("regions", []) if len(r.get("quad", [])) == 4]
        self.name_box.setText(str(data.get("name") or "PICTURE"))
        if data.get("id"):
            self.id_box.setText(str(data["id"]))
        self._project = {"out": str(Path(path).parent), "name": self.name_box.text(),
                         "fid": data.get("id")}
        self._stamped = True                           # the record IS the project's state
        self._refresh_cutouts()
        self._refresh_regions()
        self._refresh(f"Reopened {Path(path).name} — Generate updates the project in place.")

    def load_project(self, path):
        """Reopen a generated image-field PROJECT from its field.toml: prefer the folder's
        ``.trace.json`` session record; without one (a pre-sidecar project) BACKFILL the
        session from the compiled artifacts themselves — the walkmesh ring inverted back
        through the -48u collision outset, the [camera] pitch, and the generator's own
        anchored-contact comments. Either way the project ends armed for in-place Generate."""
        import re
        import tomllib
        path = Path(path)
        side = sorted(path.parent.glob("*.trace.json"))
        if side:
            self.load_trace(side[0])
            return
        text = path.read_text(encoding="utf-8")
        data = tomllib.loads(text)
        # Honest refusals FIRST, before any session state is touched -- the shell auto-loads the
        # open field into a pristine tab, so without these a wrong-camera project re-projects
        # into off-canvas garbage with no exception. Each message names where the file IS
        # editable instead.
        if (path.parent / "floorplan.json").is_file() or \
           (path.parent.parent / "floorplan.json").is_file():
            raise ValueError("a floorplan-composed room — its shape is owned by the plan "
                             "(Floorplan tab → Open… the dungeon's floorplan.json); place "
                             "content on it in the Place tab")
        layers = data.get("layers", []) or []
        base_rel = next((la["image"] for la in layers if la.get("z") == imagefield.Z_BASE),
                        layers[0]["image"] if layers else None)
        obj_rel = (data.get("walkmesh") or {}).get("obj")
        if base_rel is None or obj_rel is None:
            raise ValueError("not an image-field project (no [[layers]] art / [walkmesh] obj) "
                             "— open the photo instead and trace fresh")
        cam_tbl = data.get("camera") or {}
        if cam_tbl.get("pitch") is None:
            raise ValueError("no [camera] pose in this project — a fork's camera lives in its "
                             "donor's .bgx; Trace serves generated image-field projects")
        rng = cam_tbl.get("range")
        if (cam_tbl.get("scroll") or cam_tbl.get("window_width") or
                (isinstance(rng, (list, tuple)) and len(rng) == 2
                 and (int(rng[0]), int(rng[1])) != (imagefield.CANVAS_W, imagefield.CANVAS_H))):
            raise ValueError("a scrolling room — the Trace canvas serves the fixed "
                             f"{imagefield.CANVAS_W}×{imagefield.CANVAS_H} frame; reshape it in "
                             "the Floorplan tab, or place content on it in the Place tab")
        self.load_image(path.parent / base_rel)        # the flattened base IS the photo, 1:1
        self._distance = float(cam_tbl.get("distance", imagefield.DEFAULT_DISTANCE))
        self._fov = float(cam_tbl.get("fov", imagefield.DEFAULT_FOV))
        self.pitch.setValue(int(round(float(cam_tbl.get("pitch", imagefield.DEFAULT_PITCH)))))
        self.canvas.set_backdrop(self._pixmap, self._camera(), refit=False)  # the pose lands
        cam = self.canvas.camera()                     # even when the pitch did not change
        ring = []
        for line in (path.parent / obj_rel).read_text(encoding="utf-8").splitlines():
            if line.startswith("v "):
                p = line.split()
                ring.append((float(p[1]), float(p[3])))
        if len(ring) < 3:
            raise ValueError(f"{obj_rel} has no walkmesh ring to invert")
        inner = imagefield.outset_polygon(ring, -imagefield.COLLISION_OUTSET)
        self._floor = [(round(cx, 1), round(cy, 1))
                       for cx, cy in (imagefield.world_to_click(cam, p) for p in inner)]
        self.canvas.set_floor(self._floor)
        # the generator writes each anchored occluder's contact as a comment above its layer —
        # the one place the SOURCE pixel survives compilation (tomllib drops comments; regex it)
        for m in re.finditer(r'# occluder anchored at floor contact '
                             r'\((-?[\d.]+),(-?[\d.]+)\)[^"]*?image = "([^"]+)"', text, re.S):
            self._fg.append({"contact": (round(float(m.group(1)), 1),
                                         round(float(m.group(2)), 1)), "image": None})
            fg_path = path.parent / m.group(3)
            if fg_path.is_file():
                self._attach_cutout(len(self._fg) - 1, str(fg_path))
        # regions: the compiled toml's WORLD zones invert to canvas px through the same camera.
        # Only the GENERATOR'S OWN rows join the session (one owner: is_generated_region —
        # the same claim the regenerate merge makes); a hand/Place row stays file-side, where
        # the merge preserves it verbatim.
        for kind in ("gateway", "event"):
            for e in data.get(kind, []) or []:
                if not imagefield.is_generated_region(data, kind, e.get("name")):
                    continue
                z = e.get("zone")
                if not isinstance(z, (list, tuple)) or len(z) not in (4, 5):
                    continue
                pts = [tuple(map(float, p)) for p in z]
                if len(pts) == 5 and pts[-1] == pts[-2]:
                    pts = pts[:4]                      # the IsInQuad-safe doubled stored form
                try:
                    quad = [tuple(round(v, 1) for v in imagefield.world_to_click(cam, p))
                            for p in pts]
                except imagefield.ImageFieldError:
                    continue                           # a corner behind the camera: not this lane's
                self._regions.append({"kind": kind, "to": int(e.get("to", 0) or 0),
                                      "entrance": int(e.get("entrance", 0) or 0),
                                      "message": str(e.get("message", "...")), "quad": quad})
        name = str((data.get("field") or {}).get("name") or "PICTURE")
        fid = (data.get("field") or {}).get("id")
        self.name_box.setText(name)
        if fid:
            self.id_box.setText(str(fid))
        self._project = {"out": str(path.parent), "name": name, "fid": fid}
        self._stamped = True                           # rebuilt FROM the project = in sync
        self._refresh_cutouts()
        self._refresh_regions()
        self._refresh(f"Reopened {path.name} — session REBUILT from the compiled project (no "
                      f".trace.json yet; the next Generate writes one). Generate goes in place.")

    # ------------------------------------------------------------------ the open-field offer
    def offer_project(self, path):
        """The shell's feed on tab show: the field currently open in the Editor. A PRISTINE tab
        auto-loads a reopenable project outright (the owner-asked best case — the one sanctioned
        tab-show disk touch); a tab mid-session shows a one-click button instead of clobbering.
        A non-project toml (a fork, a hand toml) is remembered and never re-parsed."""
        self._offer_path = str(path) if path else None
        self.offer_btn.hide()
        if not self._offer_path or self._offer_path == self._offer_rejected:
            return
        cur = Path(self._project["out"]) if self._project else None
        if cur is not None and Path(self._offer_path).parent == cur:
            return                                     # already this project
        pristine = self._image is None and not self._floor and not self._fg
        if pristine:
            try:
                self.load_project(self._offer_path)
            except Exception:                          # noqa: BLE001 -- not a traceable project
                self._offer_rejected = self._offer_path
            return
        self.offer_btn.setText(f"Load {Path(self._offer_path).stem.replace('.field', '')} "
                               f"(the open field)")
        self.offer_btn.show()

    def on_offer(self):
        if not self._offer_path:
            return
        try:
            self.load_project(self._offer_path)
        except Exception as e:                         # noqa: BLE001
            self._offer_rejected = self._offer_path
            self.offer_btn.hide()
            self._refresh(f"Not a traceable project: {e}", "warn")

    # ------------------------------------------------------------------ dialog seams
    def _ask_image(self):
        """Instance dialog behind a seam (a static execs in C++ past every test patch)."""
        dlg = QFileDialog(self, "Open an image, a generated project's field.toml, or its "
                          ".trace.json", str(self._image.parent if self._image else Path.home()))
        dlg.setFileMode(QFileDialog.FileMode.ExistingFile)
        dlg.setNameFilter("Images or trace projects (*.png *.jpg *.jpeg *.bmp *.webp "
                          "*.trace.json *.field.toml);;Images (*.png *.jpg *.jpeg *.bmp *.webp);;"
                          "Trace projects (*.trace.json *.field.toml)")
        if dlg.exec() != QFileDialog.DialogCode.Accepted:
            return None
        files = dlg.selectedFiles()
        return files[0] if files else None

    def _ask_out(self):
        dlg = QFileDialog(self, "Where to put the project folder", str(self.proj_base))
        dlg.setFileMode(QFileDialog.FileMode.Directory)
        dlg.setOption(QFileDialog.Option.ShowDirsOnly, True)
        if dlg.exec() != QFileDialog.DialogCode.Accepted:
            return None
        files = dlg.selectedFiles()
        return files[0] if files else None

    def _composed_fg_path(self, i, f):
        """A placed SNIP composed onto the photo's transparent full frame at the 4x art
        resolution the build crops from — written beside the source image (the emitted command
        must stay re-runnable, so its inputs need a durable home). The paste scale is the
        photo's own cover scale: the shipped pixels match the preview exactly."""
        from PIL import Image
        W = imagefield.CANVAS_W * imagefield.UPSCALE
        H = imagefield.CANVAS_H * imagefield.UPSCALE
        s = self._canvas_scale() * imagefield.UPSCALE
        sw, sh = f["size"]
        ox, oy = f["offset"]
        frame = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        snip = Image.open(f["image"]).convert("RGBA").resize(
            (max(1, round(sw * s)), max(1, round(sh * s))), Image.LANCZOS)
        frame.paste(snip, (round(ox * imagefield.UPSCALE), round(oy * imagefield.UPSCALE)), snip)
        out = self._image.parent / f"{self._image.stem}.fg{i}.png"
        frame.save(out)
        return out

    def _ask_cutout(self):
        """The cut-out PNG picker (instance dialog behind a seam, like the others): a full-canvas
        image with alpha — only the occluding object opaque."""
        dlg = QFileDialog(self, "The cut-out PNG (full canvas, alpha — only the object opaque)",
                          str(self._image.parent if self._image else Path.home()))
        dlg.setFileMode(QFileDialog.FileMode.ExistingFile)
        dlg.setNameFilter("Cut-out images (*.png *.webp)")
        if dlg.exec() != QFileDialog.DialogCode.Accepted:
            return None
        files = dlg.selectedFiles()
        return files[0] if files else None

    # ------------------------------------------------------------------ shell plumbing
    def retheme(self, pal):
        self.pal = pal
        self.canvas.retheme(pal)

    def set_scale(self, pct):
        self.canvas.set_scale(pct)
