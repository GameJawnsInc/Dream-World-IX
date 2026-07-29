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
        self._history = []                            # prior (floor, fg) snapshots, one per gesture (undo)

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
        self.fg_btn = QPushButton("Add cut-out")
        self.fg_btn.setCheckable(True)
        self.fg_btn.setToolTip("Mark a foreground occluder (a pillar, a crate): click where the "
                               "object MEETS the floor — its base — then attach its full-canvas "
                               "cut-out PNG. Occlusion flips exactly at that line in-game.")
        self.fg_btn.toggled.connect(self._on_fg_arm)
        row.addWidget(self.fg_btn)
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
        root.addWidget(self.canvas, 1)

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
        return guide.make_camera(float(self.pitch.value()), imagefield.DEFAULT_DISTANCE,
                                 fov_x_deg=imagefield.DEFAULT_FOV)

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
        self.pitch_label.setText(
            f"{self.pitch.value()}° · horizon y {hy:.0f}" if 0 <= hy < imagefield.CANVAS_H
            else f"{self.pitch.value()}° · horizon above the frame")
        good, bad = self._valid_count()
        fg_invalid, fg_unattached = self._fg_problems()
        ready = (self._image is not None and good >= 3 and bad == 0
                 and fg_invalid == 0 and fg_unattached == 0)
        self.gen_btn.setEnabled(ready)
        if ready:
            tip = ("Build the field project (walkmesh + art + field.toml) with the exact command "
                   "the CLI tracer emits — it streams to the Output panel.")
        elif fg_invalid or fg_unattached:
            tip = ("Every cut-out needs a valid floor contact (below the horizon, below the base "
                   "layer) and an attached PNG — fix or Remove the flagged ones.")
        else:
            tip = "Needs an open image and at least 3 traced vertices, all below the horizon."
        self.gen_btn.setToolTip(tip)
        self.undo_btn.setEnabled(bool(self._history))
        self.clear_btn.setEnabled(bool(self._floor))
        self.fg_btn.setEnabled(self._image is not None)
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
        self._history = []
        self.fg_btn.setChecked(False)
        self.canvas.set_floor([])
        self.canvas.set_cutouts([])
        self.canvas.set_backdrop(pm, self._camera(), refit=True)
        self.img_label.setText(self._image.name)
        self._refresh()

    def _on_pitch(self, _v):
        self.canvas.set_backdrop(self._pixmap, self._camera(), refit=False)
        self._refresh_cutouts()                        # anchored z's are camera-dependent
        self._refresh()

    # ------------------------------------------------------------------ trace + contact gestures
    def _push_history(self):
        """One snapshot per completed gesture — floor AND cut-outs together, so Undo walks back
        through vertex and contact gestures in the order they happened."""
        self._history.append({"floor": list(self._floor), "fg": [dict(f) for f in self._fg]})
        del self._history[:-_HISTORY_CAP]

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
        self.canvas.set_floor(self._floor)             # the host write path: no on_floor echo
        self._refresh_cutouts()
        self._refresh()

    def on_clear(self):
        if not self._floor:
            return
        self._push_history()
        self._floor = []
        self.canvas.set_floor([])
        self._refresh()

    # ------------------------------------------------------------------ rung 2: cut-out contacts
    def _on_fg_arm(self, on):
        """The Add-cut-out toggle: armed = the canvas emits contact pixels (the traced polygon
        stays visible, inert); disarmed = back to floor tracing."""
        if on:
            self.canvas.set_contact_mode(True)
            self._refresh("Click where the object MEETS the floor — its base, not up its body. "
                          "Esc = the button again to cancel.")
        else:
            self.canvas.set_trace_mode(True)
            self._refresh()

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
        self.fg_btn.setChecked(False)                  # -> _on_fg_arm(False) -> trace mode
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
        if float(self.pitch.value()) != imagefield.DEFAULT_PITCH:
            argv += ["--pitch", f"{self.pitch.value():g}"]
        started = self._run(
            argv, cwd=str(self.kit), subject="Image → field",
            ok_headline=f"{name} generated → {out}",
            ok_next=f"Deploy it: py tools/deploy_field.py {out / (name + '.field.toml')} "
                    f"--id {fid} — then ~ → Warp to field → {fid}.",
            fail_hint="See the Output panel — the usual causes are a vertex above the horizon "
                      "or a floor larger than the Int16 world bound.")
        if started:
            self._refresh(f"Generating {name} → {out} …")

    # ------------------------------------------------------------------ dialog seams
    def _ask_image(self):
        """Instance dialog behind a seam (a static execs in C++ past every test patch)."""
        dlg = QFileDialog(self, "Open an image to trace",
                          str(self._image.parent if self._image else Path.home()))
        dlg.setFileMode(QFileDialog.FileMode.ExistingFile)
        dlg.setNameFilter("Images (*.png *.jpg *.jpeg *.bmp *.webp)")
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
