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
    QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSlider, QVBoxLayout, QWidget,
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
        self._pixmap = None                           # its display cover-crop (2x canvas res)
        self._floor = []                              # mirror of the canvas trace (canvas px)
        self._history = []                            # prior floors, one per gesture (undo)

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
        self.undo_btn = QPushButton("Undo")
        self.undo_btn.setToolTip("Take back the last vertex add, move, or delete.")
        self.undo_btn.clicked.connect(self.on_undo)
        row.addWidget(self.undo_btn)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setToolTip("Remove every traced vertex (one Undo brings them back).")
        self.clear_btn.clicked.connect(self.on_clear)
        row.addWidget(self.clear_btn)
        root.addLayout(row)

        self.canvas = BackdropCanvas(pal, scale=scale, on_floor=self._on_floor)
        self.canvas.set_trace_mode(True)
        self.canvas.set_backdrop(None, self._camera())   # pure math — no disk at construction
        self.canvas.click_refused.connect(self._on_refused)
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

    def _refresh(self, note="", state=""):
        hy = _cam.horizon_canvas_y(self.canvas.camera())
        self.pitch_label.setText(
            f"{self.pitch.value()}° · horizon y {hy:.0f}" if 0 <= hy < imagefield.CANVAS_H
            else f"{self.pitch.value()}° · horizon above the frame")
        good, bad = self._valid_count()
        ready = self._image is not None and good >= 3 and bad == 0
        self.gen_btn.setEnabled(ready)
        self.gen_btn.setToolTip(
            "Build the field project (walkmesh + art + field.toml) with the exact command the "
            "CLI tracer emits — it streams to the Output panel." if ready else
            "Needs an open image and at least 3 traced vertices, all below the horizon.")
        self.undo_btn.setEnabled(bool(self._history))
        self.clear_btn.setEnabled(bool(self._floor))
        if not note:
            if self._image is None:
                note = "Open an image to begin."
            elif not self._floor:
                note = ("Click the floor's outline in order, below the dashed horizon — "
                        "drag a vertex to adjust, right-click one to delete it.")
            else:
                note = f"{good} vertices traced" + (f" · {bad} above the horizon (red)" if bad
                                                    else "")
        self.status.setText(note)
        widgets.set_state(self.status, state)

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
        disp = imagefield._cover_crop(src, imagefield.CANVAS_W * 2, imagefield.CANVAS_H * 2)
        buf = io.BytesIO()
        disp.save(buf, "PNG")
        pm = QPixmap()
        pm.loadFromData(buf.getvalue(), "PNG")
        self._image = Path(path)
        self._pixmap = pm
        self._floor = []
        self._history = []
        self.canvas.set_floor([])
        self.canvas.set_backdrop(pm, self._camera(), refit=True)
        self.img_label.setText(self._image.name)
        self._refresh()

    def _on_pitch(self, _v):
        self.canvas.set_backdrop(self._pixmap, self._camera(), refit=False)
        self._refresh()

    # ------------------------------------------------------------------ trace gestures
    def _on_floor(self, pts):
        self._history.append(list(self._floor))
        del self._history[:-_HISTORY_CAP]
        self._floor = list(pts)
        self._refresh()

    def _on_refused(self, msg):
        self._refresh(msg, "warn")

    def on_undo(self):
        if not self._history:
            return
        self._floor = self._history.pop()
        self.canvas.set_floor(self._floor)             # the host write path: no on_floor echo
        self._refresh()

    def on_clear(self):
        if not self._floor:
            return
        self._history.append(list(self._floor))
        self._floor = []
        self.canvas.set_floor([])
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

    # ------------------------------------------------------------------ shell plumbing
    def retheme(self, pal):
        self.pal = pal
        self.canvas.retheme(pal)

    def set_scale(self, pct):
        self.canvas.set_scale(pct)
