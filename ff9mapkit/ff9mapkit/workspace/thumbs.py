"""Field background THUMBNAILS for the Workspace -- the first place the GUI shows the actual art.

A tiny service with a strict contract:

- ``cached(member)`` -- the ready thumbnail PNG path (or None), instant, GUI-thread safe.
- ``request(member, project_toml, real_id)`` -- returns the cached path if fresh, else enqueues a build on
  the ONE worker thread and returns None; ``ready(member, png)`` fires (queued) when a build lands.

Source fallback chain (mirrors what import modes leave on disk -- see extract.py):

1. the project's own ``background.png`` (BG-borrow / editable / lightweight projects write it) -- game-free;
2. an install-side composite of the donor real field (``extract.compose_background``, camera 0, no
   footprint) -- needs the game + UnityPy; the first-ever call may build the field index (~1-2 min), so it
   NEVER runs on the GUI thread, and the in-process bundle cache keeps later fields cheap.

Native/verbatim projects have no ``background.png`` (their atlas.png is tile-packed -- unusable raw), so
they resolve via their donor id (tier 2). Thumbs are scaled to :data:`THUMB_W` and disk-cached under
``provision.cache_dir()/thumbs`` (per-user / gitignored -- composited PNGs are SE-derived art and must
never land in a shareable project folder). Every failure is swallowed into an in-memory MISS so a machine
without the game degrades to no-image, and never retries in a click loop.

Disable with ``FF9MAPKIT_NO_THUMBS=1`` (the smoke does -- no worker threads in headless self-tests).
"""

from __future__ import annotations

import hashlib
import os
import queue
import tempfile
import threading
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from .. import provision

THUMB_W = 360                                   # cached thumbnail width (px) -- Inspector-sized; Map scales down


def enabled() -> bool:
    return os.environ.get("FF9MAPKIT_NO_THUMBS", "") not in ("1", "true", "yes")


def _cache_dir() -> Path:
    return provision.cache_dir() / "thumbs"


def _project_background(project_toml) -> Path | None:
    """The project-local composite an import wrote beside ``project_toml`` (best-effort everywhere it's
    written, so it may legitimately not exist)."""
    if not project_toml:
        return None
    p = Path(project_toml).parent / "background.png"
    return p if p.is_file() else None


def _key_for(source_png: Path | None, real_id) -> str | None:
    """The cache-file stem: a project PNG keys on its identity+mtime+size (repaints refresh); a real-field
    composite keys on the id (the game art is static)."""
    if source_png is not None:
        st = source_png.stat()
        h = hashlib.sha1(str(source_png.resolve()).encode("utf-8")).hexdigest()[:12]
        return f"proj_{h}_{st.st_mtime_ns}_{st.st_size}"
    if real_id is not None:
        return f"real_{int(real_id)}"
    return None


def _scale_to_cache(src_png: Path, out_png: Path) -> Path:
    """Down-scale ``src_png`` to :data:`THUMB_W` and write the cache PNG (atomic-ish: tmp then replace)."""
    from PIL import Image
    im = Image.open(src_png).convert("RGB")
    if im.width > THUMB_W:
        im = im.resize((THUMB_W, max(1, round(im.height * THUMB_W / im.width))), Image.LANCZOS)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_png.with_suffix(".tmp.png")
    im.save(tmp, "PNG", optimize=True)
    tmp.replace(out_png)
    return out_png


def build_thumb(project_toml, real_id) -> Path | None:
    """Synchronously produce (or reuse) the cached thumbnail for a field. Pure worker logic -- no Qt.
    Returns the PNG path, or None when no source is available (no project art + no id / no install)."""
    src = _project_background(project_toml)
    key = _key_for(src, real_id)
    if key is None:
        return None
    out = _cache_dir() / f"{key}.png"
    if out.is_file():
        return out
    if src is not None:
        png = _scale_to_cache(src, out)
        stale_prefix = key.rsplit("_", 2)[0]       # proj_<hash> -- older mtime/size variants of the SAME
        for old in _cache_dir().glob(f"{stale_prefix}_*.png"):     # source are dead weight: prune them
            if old != out:
                try:
                    old.unlink()
                except OSError:
                    pass
        return png
    # install-side composite of the real/donor field (slow-once; bundle cache keeps siblings cheap).
    # env_lock serializes against any GUI-thread reader of the same cached UnityPy environments (the SPS
    # detail preview) -- their SerializedFile readers are stateful and not thread-safe.
    from .. import extract
    with tempfile.TemporaryDirectory(prefix="ff9-thumb-") as td:
        full = Path(td) / "full.png"
        # camera 0 keeps multi-camera fields clean (index None jams every overlay onto one canvas)
        with extract.env_lock:
            ok = extract.compose_background(str(int(real_id)), full, draw_footprint=False, camera_index=0)
        if ok is None:
            return None
        return _scale_to_cache(full, out)


# ---------------------------------------------------------------- 3D model previews (the Models tab)
# The pure cache/render logic is Qt-free in models/thumbcache.py (the Info Hub + the catalog pickers
# read the cache tk-free); re-exported here so the Workspace side keeps one import site.
from ..models.thumbcache import (MODEL_THUMB, build_model_thumb, model_thumb_meta,   # noqa: F401,E402
                                 model_thumb_paths)


class ThumbService(QObject):
    """The Workspace-side async wrapper: one daemon worker drains a queue of (member, toml, real_id) and
    emits ``ready(member, png_path)`` for each success. Failures are remembered as misses (no re-try storm);
    ``invalidate()`` clears the misses (e.g. after F5 / a re-import)."""

    ready = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._q = queue.Queue()
        self._done = {}                          # member -> png path (str)
        self._miss = set()                       # members that resolved to no-source/no-install
        self._pending = set()
        self._gen = 0                            # bumped by invalidate(): in-flight results older than the
        self._lock = threading.Lock()            # bump are DROPPED (they may have read pre-refresh art)
        self._worker = None

    # ---- GUI-thread API ----
    def cached(self, member) -> str | None:
        return self._done.get(member)

    def request(self, member, project_toml, real_id) -> str | None:
        """The cached path (instant) or None; a None ENQUEUES a background build unless it's a known miss."""
        if not enabled():
            return None
        png = self._done.get(member)
        if png:
            return png
        # enqueue + worker liveness under ONE lock: the worker only retires (sets _worker = None) under the
        # same lock after a final empty-queue check, so a put can never be stranded by a dying worker.
        with self._lock:
            if member in self._miss or member in self._pending:
                return None
            self._pending.add(member)
            self._q.put((member, str(project_toml) if project_toml else None, real_id))
            if self._worker is None:
                self._worker = threading.Thread(target=self._drain, name="ff9-thumbs", daemon=True)
                self._worker.start()
        return None

    def invalidate(self, member=None):
        """Forget results/misses/pendings (one member, or all) so the next request re-resolves -- F5's
        analogue. Bumps the generation so an IN-FLIGHT build (which may have read the old art) is dropped
        instead of landing stale over the fresh state."""
        with self._lock:
            self._gen += 1
            if member is None:
                self._done.clear()
                self._miss.clear()
                self._pending.clear()
            else:
                self._done.pop(member, None)
                self._miss.discard(member)
                self._pending.discard(member)

    # ---- worker ----
    def _drain(self):
        while True:
            try:
                member, toml, real_id = self._q.get(timeout=2.0)
            except queue.Empty:
                with self._lock:                  # retire ATOMICALLY vs request(): re-check under the lock
                    if self._q.empty():
                        self._worker = None       # published before death -> the next request starts fresh
                        return
                continue                          # a put landed in the gap -> keep draining
            with self._lock:
                gen = self._gen
            try:
                png = build_thumb(toml, real_id)
            except Exception:   # noqa: BLE001  (no install / bad art / anything) -> a remembered miss
                png = None
            with self._lock:
                if gen != self._gen:              # invalidated mid-build: the result may be stale -> drop
                    self._pending.discard(member)
                    continue
                self._pending.discard(member)
                if png is None:
                    self._miss.add(member)
                else:
                    self._done[member] = str(png)
            if png is not None:
                try:
                    self.ready.emit(member, str(png))   # queued into the GUI thread
                except RuntimeError:              # the service's C++ half died (app exit) -- stop quietly
                    return


class ModelThumbService(QObject):
    """Async 3D-model preview renders for the Models tab -- the same contract + locking discipline as
    :class:`ThumbService` (cached/request/ready/invalidate, one daemon worker, remembered misses,
    generation-dropped in-flight results), keyed by GEO NAME. The worker keeps the p0data bundles +
    the p0data5 env alive between renders (``self._ctx``, worker-thread-confined), so a browse session
    pays the bundle load once. A model whose prefab isn't on disc (the model DB lists some ids the
    install never shipped) lands as a remembered miss -- the list shows it un-thumbnailed."""

    ready = Signal(str, str)                     # (geo name, png path)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._q = queue.Queue()
        self._done = {}                          # geo name -> png path (str)
        self._miss = set()
        self._pending = set()
        self._gen = 0
        self._lock = threading.Lock()
        self._worker = None
        self._ctx = {}                           # p0data bundle cache; touched ONLY by the worker thread

    # ---- GUI-thread API ----
    def cached(self, name) -> str | None:
        return self._done.get(name)

    def request(self, name) -> str | None:
        """The cached path (instant) or None; a None ENQUEUES a background render unless it's a known
        miss. Same worker-liveness discipline as ThumbService.request (enqueue + start under one lock)."""
        if not enabled():
            return None
        png = self._done.get(name)
        if png:
            return png
        with self._lock:
            if name in self._miss or name in self._pending:
                return None
            self._pending.add(name)
            self._q.put(name)
            if self._worker is None:
                self._worker = threading.Thread(target=self._drain, name="ff9-model-thumbs", daemon=True)
                self._worker.start()
        return None

    def invalidate(self, name=None):
        with self._lock:
            self._gen += 1
            if name is None:
                self._done.clear()
                self._miss.clear()
                self._pending.clear()
            else:
                self._done.pop(name, None)
                self._miss.discard(name)
                self._pending.discard(name)

    # ---- worker ----
    def _drain(self):
        while True:
            try:
                name = self._q.get(timeout=2.0)
            except queue.Empty:
                with self._lock:
                    if self._q.empty():
                        self._worker = None
                        return
                continue
            with self._lock:
                gen = self._gen
            try:
                png = build_model_thumb(name, self._ctx)
            except Exception:   # noqa: BLE001  (no install / no prefab on disc / anything) -> a miss
                png = None
            with self._lock:
                if gen != self._gen:
                    self._pending.discard(name)
                    continue
                self._pending.discard(name)
                if png is None:
                    self._miss.add(name)
                else:
                    self._done[name] = str(png)
            if png is not None:
                try:
                    self.ready.emit(name, str(png))
                except RuntimeError:
                    return
