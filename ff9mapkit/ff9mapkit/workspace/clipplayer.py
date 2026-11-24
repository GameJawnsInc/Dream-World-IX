"""The rendered-clip PLAYER -- one transport, one playback state machine, two surfaces.

Stage B built this inside the Models tab. Stage C needed the same thing inside the animation PICKER
dialog (you cannot choose a gesture you cannot see), and a second implementation of "loop the
contiguous cached prefix, extend it as frames land, hold the last picture on a gap" is exactly the
kind of copy that drifts. So the state machine + the transport row live HERE as a mixin over any
QWidget host, and both surfaces spend it:

    class ModelsDoc(clipplayer.ClipPlayer, QWidget): ...
    class AnimPickerDialog(clipplayer.ClipPlayer, QDialog): ...

The host owes exactly two things:

* ``_set_detail_image(png)`` -- where a frame is painted (the Models tab paints into its 224px still
  box; the dialog paints into its own preview box);
* ``_still_png()`` -- what Reset restores (the tab's cached ModelThumbService still; the dialog has
  none, so Reset just rewinds).

Everything else -- the identity fence at the paint, the warm-disk synchronous answer, the honest
strided rate, the SVG transport icons -- is the same code for both, which is the point.

**A fill is 5-10 seconds, and the strip is built around that.** Measured on real clips: ~100-140ms to
rasterize a frame against ~10ms to skin it, so a 45-frame idle is ~5s and the first frame is there in
under one. Three consequences, all here:

* the strip says HOW FAR (``clipPlanned`` carries the total: "Rendering 12 of 45 frames");
* playback FOLLOWS THE FRONTIER during a fill instead of looping the prefix -- at 30fps against ~8
  landing a second, a looping prefix restarts every few frames and reads as a stutter; holding on the
  newest frame until the next lands reads as the clip being drawn, and it loops the moment it is whole;
* with motion on (``anim.enabled()`` -- the user's preference, default OFF everywhere but production)
  an armed clip PLAYS without a second click. Picking a clip is asking to watch it. With motion off
  the strip waits for Play exactly as it always did, which is what a reduce-motion setting means.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QSizePolicy, QSlider, QWidget

from . import anim as motion, icons, thumbs as thumbs_mod, widgets

SPEEDS = (1.0, 0.5, 0.25, 2.0)                    # the speed button's cycle; 1x first, slow-mo before fast
_SPEED_LABEL = {1.0: "1×", 0.5: "½×", 0.25: "¼×", 2.0: "2×"}


class ClipPlayer:
    """Transport + playback for ONE armed (model, clip). A plain-object mixin: the host is the QWidget
    (so ``self`` really is a QObject for the receiver-scoped signal connects)."""

    # ------------------------------------------------------------------ construction
    def _init_player(self, anim_frames, *, service_parent=None):
        """Wire the frame source and reset the playback state. ``anim_frames`` is injected in tests (a
        double with the same surface), so no test can reach a worker thread or this machine's install."""
        from . import animframes
        self.anims = anim_frames if anim_frames is not None else \
            animframes.AnimFrameService(service_parent if service_parent is not None else self)
        self.anims.clipPlanned.connect(self._clip_planned)
        self.anims.frameReady.connect(self._frame_ready)
        self.anims.clipDone.connect(self._clip_done)
        self.anims.clipMissed.connect(self._clip_missed)
        self._armed = None                        # (geo name, anim id) the strip is playing, or None
        self._seq = []                            # [(frame index, png path)] -- the CONTIGUOUS cached
        self._clip_meta = None                    # prefix from frame 0, extended as frames land
        self._filling = False                     # a fill is streaming: playback follows the frontier
        self._expected = 0                        # frames that fill will render (0 = not told yet)
        self._speed = SPEEDS[0]                   # playback rate multiplier (survives a clip switch)
        self._play_timer = QTimer(self)
        self._play_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._play_timer.timeout.connect(self._advance)

    def _build_transport(self, *, note="Pick a model, then a clip."):
        """The transport ROW (play/pause + reset + scrubber + counter) as ``self.anim_strip``, plus
        ``self.anim_foot`` -- the prose line ``self.anim_note`` with the speed button at its right end.
        The host places BOTH (strip, then foot): hiding the strip must not hide the sentence that
        explains why. Returns the strip."""
        self.anim_strip = QWidget()
        # EXACT-CLASS transparent (widgets.TRANSPARENT): the universal QWidget{background:$bg} rule
        # painted this bare container as a dark band across the section card it sits in
        self.anim_strip.setStyleSheet(widgets.TRANSPARENT)
        srow = QHBoxLayout(self.anim_strip)
        srow.setContentsMargins(0, 0, 0, 0)
        srow.setSpacing(8)
        # Transport controls wear SVG icons (icons.py), NEVER the unicode media glyphs -- U+23F5 and
        # friends fall back to the Windows emoji face and render as colour blobs (the Behavior tab
        # paid for that one on a snap; the owner's rule is no emoji, the SVGs exist for this).
        self.anim_play = QPushButton()
        self.anim_play.setProperty("role", "quiet")
        self.anim_play.setCheckable(True)
        self.anim_play.setIcon(icons.icon("play", self.pal["text"]))
        self.anim_play.setAccessibleName("Play or pause the animation preview")
        self.anim_play.setToolTip("Play / pause the frames rendered so far (it loops)")
        self.anim_play.toggled.connect(self._on_play_toggled)
        srow.addWidget(self.anim_play)
        self.anim_reset_btn = QPushButton()
        self.anim_reset_btn.setProperty("role", "quiet")
        self.anim_reset_btn.setIcon(icons.icon("reset", self.pal["text"]))
        self.anim_reset_btn.setAccessibleName("Stop and show the still preview")
        self.anim_reset_btn.setToolTip("Stop, rewind to frame 0, and put the still preview back")
        self.anim_reset_btn.clicked.connect(self.reset_player)
        srow.addWidget(self.anim_reset_btn)
        self.anim_slider = QSlider(Qt.Orientation.Horizontal)
        self.anim_slider.setObjectName("animFrameSlider")   # carries the reserved focus ring (style.py)
        self.anim_slider.setAccessibleName("Animation frame")
        self.anim_slider.setAccessibleDescription(
            "Scrub the frames rendered so far for the selected clip")
        self.anim_slider.setToolTip("Scrub the rendered frames (← → step one frame when focused)")
        self.anim_slider.setRange(0, 0)
        self.anim_slider.setMinimumWidth(120)               # never starved to a sliver by the counter
        self.anim_slider.valueChanged.connect(self._on_scrub)
        srow.addWidget(self.anim_slider, 1)
        self.anim_count = widgets.ElideLabel("", "muted", mono=True, min_ch=12)
        # ELIDE, BUT BE BUDGETED. ElideLabel ships QSizePolicy.Ignored so a compound caption can yield
        # all the way to "…" -- and QWidgetItem ZEROES an Ignored item's sizeHint width, while
        # qSmartMinSize still honours the explicit min_ch minimum. That inverts the invariant
        # qGeomCalc assumes (hint >= min), and its SURPLUS branch hands such an item its hint: 0. The
        # counter was laid out at x == the strip's full width -- entirely off the edge, snap-caught
        # (min_ch only ever bit in the squeeze branch, which is why the Behavior strip, where these
        # labels own a whole row, never showed it). Preferred keeps the ShrinkFlag -- it still yields
        # down to the same min_ch floor, and the elide still runs in resizeEvent.
        self.anim_count.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        srow.addWidget(self.anim_count)
        self.anim_note = widgets.caption(note)
        # SPEED is the one control a 30fps gesture needs to be READ rather than glimpsed: an attack
        # wind-up is six frames. A cycling button, not a combo (a QComboBox's minimum is its widest
        # item plus an arrow) -- and on the NOTE's row, not the transport's. Snap-caught: the transport
        # is at the pane's width floor at the default window, and a fifth control there squeezed the
        # counter to "f 9/16 · 3…". The note wraps, so its row always has a corner to spare.
        self.anim_speed = QPushButton(_SPEED_LABEL[self._speed])
        self.anim_speed.setProperty("role", "quiet")
        self.anim_speed.setAccessibleName("Playback speed")
        self.anim_speed.setToolTip("Playback speed — click to cycle 1× → ½× → ¼× → 2×")
        self.anim_speed.clicked.connect(self.cycle_speed)
        # FIXED, and a spacer beside it: a caption is width-CAPPED (widgets.caption's measure), so in a
        # wide host the row's surplus goes to the only item that will take it -- snap-caught as a
        # "1×" button stretched across half the picker dialog. The spacer's stretch is 1 against the
        # note's 100, so in a NARROW host the note still gets the row.
        self.anim_speed.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.anim_foot = QWidget()
        self.anim_foot.setStyleSheet(widgets.TRANSPARENT)
        frow = QHBoxLayout(self.anim_foot)
        frow.setContentsMargins(0, 0, 0, 0)
        frow.setSpacing(8)
        frow.addWidget(self.anim_note, 100)
        frow.addStretch(1)
        frow.addWidget(self.anim_speed, 0, Qt.AlignmentFlag.AlignTop)
        self._set_transport(False)
        if not thumbs_mod.enabled():             # the tab's own idiom (see count_lbl / _on_select)
            self.anim_strip.hide()
            self.anim_speed.hide()               # nothing plays -> nothing to time; the note stays
            self.anim_note.setText("Previews off — the clip list is still browsable "
                                   "(ids paste straight into anims=).")
        return self.anim_strip

    # ------------------------------------------------------------------ host hooks
    def _still_png(self):
        """What Reset restores when there is no clip frame to show (None = just rewind)."""
        return None

    # ------------------------------------------------------------------ the clip player
    def _set_transport(self, on, *, reason=""):
        """Enable/disable the transport as ONE decision (a 1-frame clip is armed but unplayable)."""
        for w in (self.anim_play, self.anim_reset_btn, self.anim_slider, self.anim_speed):
            w.setEnabled(bool(on))
        if reason:
            self.anim_note.setText(reason)

    def arm_clip(self, geo_name, anim_id):
        """Point the strip at one (model, clip). Supersedes whatever was filling, then either paints
        a WARM clip synchronously (request_clip's return value IS the answer -- no signal arrives for
        a disk hit) or waits for the streamed frames."""
        self.stop_playback()
        self.anims.supersede()
        self._armed = (str(geo_name), int(anim_id))
        self._seq = []
        self._clip_meta = None
        self._filling, self._expected = False, 0
        self.anim_slider.blockSignals(True)
        self.anim_slider.setRange(0, 0)
        self.anim_slider.setValue(0)
        self.anim_slider.blockSignals(False)
        self.anim_count.setText("")
        if not thumbs_mod.enabled():
            self._set_transport(False)
            return
        meta = self.anims.request_clip(geo_name, anim_id)
        if meta is not None:                      # warm disk: no worker, no signals -- read it here
            self._clip_meta = meta
            for f in meta.get("rendered_frames") or []:
                png = self.anims.cached_frame(geo_name, anim_id, f)
                if png:
                    self._add_frame(f, png)
            self._finish_clip()
            return
        why = self.anims.missed_reason(geo_name, anim_id)
        if why:                                   # a remembered miss enqueues nothing: say so NOW
            self._set_transport(False, reason=f"No preview for this clip — {why}")
            return
        self._filling = True
        self._set_transport(False, reason="Rendering frames… (they play as they land)")

    def _add_frame(self, frame_idx, png):
        """Extend the contiguous cached prefix. The fill streams in ascending frame order, so the
        arrival order IS the play order; the strip never gates on 'all frames'."""
        self._seq.append((int(frame_idx), str(png)))
        self.anim_slider.blockSignals(True)
        self.anim_slider.setRange(0, len(self._seq) - 1)
        self.anim_slider.blockSignals(False)
        if len(self._seq) == 1:
            self._show_frame(0)
        if len(self._seq) > 1:
            self._set_transport(True)
        if self._filling:
            self.anim_note.setText(self._fill_note())
            if len(self._seq) == 2:
                self._autoplay()                  # two frames are already motion -- do not wait for all
        self._update_counter()

    def _fill_note(self) -> str:
        """HOW FAR a streaming fill is. The total arrives with ``clipPlanned`` (after the posing pass);
        until then the count alone is still honest."""
        n = len(self._seq)
        if self._expected > 0:
            return f"Rendering {n} of {self._expected} frames… (they play as they land)"
        return f"Rendering frames… {n} so far (they play as they land)"

    def _autoplay(self):
        """Start playing an armed clip unasked -- ONLY with motion on (see the module docstring)."""
        if motion.enabled() and len(self._seq) > 1 and not self.anim_play.isChecked():
            self.anim_play.setChecked(True)

    def _show_frame(self, pos):
        """Paint one position of the prefix into the host's image box. A missing/undecodable frame HOLDS
        the previous picture (``_set_detail_image`` ignores a null pixmap) rather than blanking."""
        if not (0 <= pos < len(self._seq)):
            return
        self._set_detail_image(self._seq[pos][1])
        self._update_counter()

    def _update_counter(self):
        if not self._seq:
            self.anim_count.setText("")
            return
        meta = self._clip_meta or {}
        fps = float(meta.get("fps") or meta.get("sample_rate") or 30.0)
        stride = int(meta.get("stride") or 1)
        rate = f"preview {fps:g}fps" if stride > 1 else f"{fps:g}fps"
        pos = min(max(self.anim_slider.value(), 0), len(self._seq) - 1)
        self.anim_count.setText(f"f {pos + 1}/{len(self._seq)} · {rate}")

    def _play_interval(self) -> int:
        fps = float((self._clip_meta or {}).get("fps") or 30.0) * self._speed
        return max(16, int(round(1000.0 / fps)) if fps > 0 else 33)

    def cycle_speed(self):
        """Step the speed button through :data:`SPEEDS`; a running clock re-times on the spot."""
        self._speed = SPEEDS[(SPEEDS.index(self._speed) + 1) % len(SPEEDS)] \
            if self._speed in SPEEDS else SPEEDS[0]
        self.anim_speed.setText(_SPEED_LABEL[self._speed])
        if self._play_timer.isActive():
            self._play_timer.start(self._play_interval())

    def _on_play_toggled(self, on):
        if on and len(self._seq) > 1:
            self._play_timer.start(self._play_interval())
        else:
            self._play_timer.stop()
        self.anim_play.setIcon(icons.icon("pause" if self._play_timer.isActive() else "play",
                                          self.pal["text"]))

    def _advance(self):
        n = len(self._seq)
        if n < 2:
            return
        nxt = self.anim_slider.value() + 1
        if nxt >= n:
            if self._filling:
                return                            # HOLD on the frontier: the next frame is being drawn
            nxt = 0                               # the clip is whole -> LOOP it
        self.anim_slider.setValue(nxt)

    def _on_scrub(self, value):
        self._show_frame(int(value))

    def stop_playback(self):
        self._play_timer.stop()
        if self.anim_play.isChecked():
            self.anim_play.blockSignals(True)     # no re-entry into _on_play_toggled
            self.anim_play.setChecked(False)
            self.anim_play.blockSignals(False)
        self.anim_play.setIcon(icons.icon("play", self.pal["text"]))

    def reset_player(self):
        """Stop, rewind, and put the host's STILL back (the Models tab's cached ModelThumbService PNG --
        already warm on disk whenever the detail pane painted one)."""
        self.stop_playback()
        self.anim_slider.blockSignals(True)
        self.anim_slider.setValue(0)
        self.anim_slider.blockSignals(False)
        self._update_counter()
        png = self._still_png()
        if png:
            self._set_detail_image(png)

    def _rate_note(self) -> str:
        """The honest rate in PROSE. The counter beside the slider is an ElideLabel, so at the wide
        CALIBRE rungs it can lose its tail ('30f…') -- and the rate is the one part that must not go
        missing, because a strided clip really is playing slower than the clip runs in-game. This
        line word-wraps at full width, so it always survives."""
        meta = self._clip_meta or {}
        fps = float(meta.get("fps") or meta.get("sample_rate") or 30.0)
        stride = int(meta.get("stride") or 1)
        total = int(meta.get("frame_count") or len(self._seq))
        if stride > 1:
            return (f"{total} frames sampled every {stride} → {len(self._seq)} rendered, "
                    f"played at {fps:g}fps")
        return f"{len(self._seq)} frames at {fps:g}fps"

    def _finish_clip(self):
        n = len(self._seq)
        self._filling = False                     # whole (or as whole as it will get): playback may loop
        if n > 1:
            self._set_transport(True, reason=f"Ready — {self._rate_note()} (it loops).")
            self._autoplay()                      # the WARM path lands here without ever streaming
        elif n == 1:
            self._set_transport(False, reason="A single-frame clip (a held pose) — nothing to play.")
        else:
            self._set_transport(False, reason="No frames rendered for this clip.")
        self._update_counter()

    def disarm(self):
        """Forget the armed clip and cancel its fill (a model switch, or leaving the surface)."""
        self.stop_playback()
        self.anims.supersede()
        self._armed, self._seq, self._clip_meta = None, [], None
        self._filling, self._expected = False, 0
        self._set_transport(False)

    # ---- service slots: the identity fence lives HERE, at the paint ----
    def _clip_planned(self, geo, anim, total):
        if self._armed != (str(geo), int(anim)) or not self._filling:
            return
        self._expected = int(total)
        self.anim_note.setText(self._fill_note())

    def _frame_ready(self, geo, anim, frame, png):
        if self._armed != (str(geo), int(anim)):
            return                                # a superseded clip's late frame paints NOTHING
        self._add_frame(frame, png)

    def _clip_done(self, geo, anim):
        if self._armed != (str(geo), int(anim)):
            return
        self._clip_meta = self.anims.cached_meta(geo, anim)
        self._finish_clip()

    def _clip_missed(self, geo, anim, reason):
        if self._armed != (str(geo), int(anim)):
            return
        self._filling = False
        self.stop_playback()
        self._set_transport(False, reason=f"No preview for this clip — {reason}")
