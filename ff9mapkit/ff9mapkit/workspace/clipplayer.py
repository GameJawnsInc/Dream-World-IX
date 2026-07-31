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
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QSizePolicy, QSlider, QWidget

from . import icons, thumbs as thumbs_mod, widgets


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
        self.anims.frameReady.connect(self._frame_ready)
        self.anims.clipDone.connect(self._clip_done)
        self.anims.clipMissed.connect(self._clip_missed)
        self._armed = None                        # (geo name, anim id) the strip is playing, or None
        self._seq = []                            # [(frame index, png path)] -- the CONTIGUOUS cached
        self._clip_meta = None                    # prefix from frame 0, extended as frames land
        self._play_timer = QTimer(self)
        self._play_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._play_timer.timeout.connect(self._advance)

    def _build_transport(self, *, note="Pick a model, then a clip."):
        """The transport ROW (play/pause + reset + scrubber + counter) as ``self.anim_strip``, plus
        ``self.anim_note`` (the prose line -- the host places it, because hiding the strip must not hide
        the sentence that explains why). Returns the strip."""
        self.anim_strip = QWidget()
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
        self.anim_slider.setToolTip("Scrub the rendered frames")
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
        self._set_transport(False)
        if not thumbs_mod.enabled():             # the tab's own idiom (see count_lbl / _on_select)
            self.anim_strip.hide()
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
        for w in (self.anim_play, self.anim_reset_btn, self.anim_slider):
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
        self._update_counter()

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
        fps = float((self._clip_meta or {}).get("fps") or 30.0)
        return max(16, int(round(1000.0 / fps)) if fps > 0 else 33)

    def _on_play_toggled(self, on):
        if on and len(self._seq) > 1:
            self._play_timer.start(self._play_interval())
        else:
            self._play_timer.stop()
        self.anim_play.setIcon(icons.icon("pause" if self._play_timer.isActive() else "play",
                                          self.pal["text"]))

    def _advance(self):
        if len(self._seq) < 2:
            return
        self.anim_slider.setValue((self.anim_slider.value() + 1) % len(self._seq))   # LOOP the prefix

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
        if n > 1:
            self._set_transport(True, reason=f"Ready — {self._rate_note()} (it loops).")
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
        self._set_transport(False)

    # ---- service slots: the identity fence lives HERE, at the paint ----
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
        self.stop_playback()
        self._set_transport(False, reason=f"No preview for this clip — {reason}")
