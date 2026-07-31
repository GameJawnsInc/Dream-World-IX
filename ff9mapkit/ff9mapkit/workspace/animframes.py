"""Animated 3D-model CLIP frames for the Workspace -- the async half of
:func:`ff9mapkit.models.thumbcache.build_anim_clip`.

Same LAWS as :class:`~.thumbs.ModelThumbService`, because they are the same laws:

* ``FF9MAPKIT_NO_THUMBS`` gates EVERYTHING (headless self-tests spawn no worker and read no cache);
* a WARM DISK hit answers :meth:`AnimFrameService.request_clip` SYNCHRONOUSLY, with **no** signal emit
  -- a caller that also waits for a signal would wait forever, so the return value is the contract;
* ``hold()`` / ``release()`` pause builds between clips (counted);
* the p0data bundles + p0data5 env live in ``self._ctx``, WORKER-THREAD-CONFINED (a second ~625ms
  bundle load per session, deliberately not shared with ModelThumbService's own thread-confined ctx);
* a clip that cannot be resolved/rendered lands as a REMEMBERED MISS -- never a retry storm.

**The queue is CLIP-shaped, not thumb-shaped.** A thumb job is ~0.2s and a FIFO with no cancel costs
nothing; a clip fill is seconds, so arming a new clip must be able to *cancel* the last one. Hence
:meth:`supersede`, and hence the per-job GENERATION stamped at enqueue: ``should_abort()`` is simply
"my generation is no longer the current one", which covers the running job, the queued jobs, and a job
that was parked behind :meth:`hold` in one comparison. (``ModelThumbService``'s counter only moves on
``invalidate()``, so a mis-click there would have cost the whole fill.)

**Identity rides the payload.** ``frameReady(geo, anim, frame, path)`` carries the FULL identity, so
the consumer drops what it did not arm at the SLOT -- the fence lives where the paint happens, not in
a counter that a late queued emit can outrun.
"""

from __future__ import annotations

import queue
import threading

from PySide6.QtCore import QObject, Signal

from ..models import thumbcache
from . import thumbs as thumbs_mod


class AnimFrameService(QObject):
    """One clip fill at a time, streamed frame by frame into the GUI thread."""

    frameReady = Signal(str, int, int, str)      # (geo name, anim id, frame index, png path)
    clipDone = Signal(str, int)                  # (geo name, anim id) -- the fill finished
    clipMissed = Signal(str, int, str)           # (geo name, anim id, reason) -- nothing to play

    def __init__(self, parent=None):
        super().__init__(parent)
        self._q = queue.Queue()
        self._miss = {}                          # (geo, anim) -> reason (remembered; no retry storm)
        self._pending = set()
        self._gen = 0                            # bumped by supersede(): older jobs abort
        self._lock = threading.Lock()
        self._worker = None
        self._holds = 0                          # hold()/release() depth -- fills pause while > 0
        self._gate = threading.Event()           # cleared while held; _drain blocks between clips
        self._gate.set()
        self._ctx = {}                           # bundles + env5 + clip/collect memos; WORKER-ONLY

    # ---- GUI-thread API ----------------------------------------------------------------
    def hold(self):
        """Pause fills (counted -- pair with :meth:`release`). A frame already being rasterized
        finishes (bounded: one); nothing new starts."""
        with self._lock:
            self._holds += 1
            self._gate.clear()

    def release(self):
        """Undo one hold(); at depth 0 resume, starting the worker if a clip queued meanwhile."""
        with self._lock:
            self._holds = max(0, self._holds - 1)
            if self._holds == 0:
                self._gate.set()
                if self._worker is None and not self._q.empty():
                    self._start_worker()

    def cached_frame(self, geo_name, anim_id, frame) -> "str | None":
        """One rendered frame's PNG if the DISK already has it -- one stat, no render, any thread."""
        gid = self._geo_id(geo_name)
        if gid is None:
            return None
        return thumbcache.cached_anim_frame(gid, anim_id, frame)

    def cached_meta(self, geo_name, anim_id) -> "dict | None":
        """The clip's sidecar (frame_count / sample_rate / stride / fps / rendered_frames / fit), or
        None. Cache reads only -- the player strip drives playback entirely off this."""
        gid = self._geo_id(geo_name)
        if gid is None:
            return None
        return thumbcache.anim_clip_meta(gid, anim_id)

    def missed_reason(self, geo_name, anim_id) -> "str | None":
        """Why this clip is not renderable, if a build already found out. Without it a re-armed
        known miss would sit on 'rendering…' forever: a remembered miss enqueues nothing, so no
        clipMissed would ever arrive a second time."""
        try:
            return self._miss.get((str(geo_name), int(anim_id)))
        except (TypeError, ValueError):
            return None

    def request_clip(self, geo_name, anim_id) -> "dict | None":
        """The clip's meta if every rendered frame is already ON DISK (instant, NO signal), else None
        after enqueuing ONE background fill. Arming a clip supersedes whatever was filling before."""
        if not thumbs_mod.enabled():
            return None
        try:
            key = (str(geo_name), int(anim_id))
        except (TypeError, ValueError):
            return None
        meta = self.cached_meta(*key)
        if meta and all(self.cached_frame(*key, f) for f in (meta.get("rendered_frames") or [])):
            return meta                          # warm disk: the return value IS the answer
        with self._lock:
            if key in self._miss or key in self._pending:
                return None
            self._pending.add(key)
            self._q.put((key, self._gen))        # the generation stamped at ENQUEUE -- see the header
            if self._worker is None and self._holds == 0:   # held: release() starts the worker
                self._start_worker()
        return None

    def supersede(self):
        """Cancel the in-flight fill and drop everything queued. The running build's
        ``should_abort()`` reads the generation this bumps, so it stops between frames."""
        with self._lock:
            self._gen += 1
            while True:
                try:
                    self._q.get_nowait()
                except queue.Empty:
                    break
            self._pending.clear()

    # ---- internals ---------------------------------------------------------------------
    def _start_worker(self):
        """Caller holds ``self._lock`` (enqueue + liveness under ONE lock, like ThumbService: the
        worker only retires under the same lock after a final empty-queue check)."""
        self._worker = threading.Thread(target=self._drain, name="ff9-anim-frames", daemon=True)
        self._worker.start()

    @staticmethod
    def _geo_id(geo_name):
        if geo_name is None:
            return None
        return thumbs_mod._geo_id(str(geo_name))     # ONE lazily-built {name -> id} map, not a scan

    def _stale(self, gen) -> bool:
        with self._lock:
            return gen != self._gen

    # ---- worker ------------------------------------------------------------------------
    def _drain(self):
        while True:
            try:
                key, gen = self._q.get(timeout=2.0)
            except queue.Empty:
                with self._lock:                  # retire ATOMICALLY vs request_clip
                    if self._q.empty():
                        self._worker = None
                        return
                continue
            self._gate.wait()                     # held -> pause BETWEEN clips
            geo, aid = key
            if self._stale(gen):                  # superseded while queued (or while held)
                with self._lock:
                    self._pending.discard(key)
                continue

            def _on_frame(idx, path, _g=geo, _a=aid):
                try:
                    self.frameReady.emit(_g, _a, int(idx), str(path))   # queued into the GUI thread
                except RuntimeError:              # the service's C++ half died (app exit)
                    pass

            reason = ""
            try:
                meta = thumbcache.build_anim_clip(geo, aid, self._ctx, on_frame=_on_frame,
                                                  should_abort=lambda g=gen: self._stale(g))
            except Exception as e:   # noqa: BLE001  (no install / no p0data5 / bad clip) -> a miss
                meta, reason = None, f"{type(e).__name__}: {e}"
            aborted = self._stale(gen)
            with self._lock:
                self._pending.discard(key)
                if not aborted and meta is None:
                    self._miss[key] = reason or ("no bundled clip for this model on this install "
                                                 "(minted and loose clips have no preview yet)")
            if aborted:                           # a newer clip is armed -- say nothing about this one
                continue
            try:
                if meta is not None:
                    self.clipDone.emit(geo, aid)
                else:
                    self.clipMissed.emit(geo, aid, self._miss[key])
            except RuntimeError:                  # the service's C++ half died (app exit)
                return
