"""Audio playback for the Sounds tab -- three tiers behind one small interface.

The Workspace is pinned to PySide6-**Essentials** (pyproject: the GPL-only Qt modules live in Addons),
and Qt's audio module, QtMultimedia, is an Addons module. So the in-app player cannot be a plain
import: it is CHOSEN, at the user's first Play and never at import or construction --

1. :class:`QtPlayer` -- QtMultimedia when the environment happens to have it (a full ``PySide6``
   install). Real transport: pause, seek, position, a loop-region preview.
2. :class:`FfplayPlayer` -- ``ffplay`` (ffmpeg's player; the kit already asks for ffmpeg to import
   audio). Plays in the app with a clock-estimated position; pause and seek restart it at an offset.
3. :class:`ExternalPlayer` -- hand the file to the system's default player. No transport at all.

:func:`make_player` picks the best one available. ``FF9MAPKIT_NO_AUDIO=1`` forces :class:`NullPlayer`
(silent, stateful) -- the belt for test processes, on top of the doc's own ``player_factory`` seam.

Every player speaks milliseconds and the three states ``"playing"`` / ``"paused"`` / ``"stopped"``.
"""
from __future__ import annotations

import os
import shutil

from PySide6.QtCore import QElapsedTimer, QObject, QProcess, QTimer, QUrl, Signal

PLAYING, PAUSED, STOPPED = "playing", "paused", "stopped"


class Player(QObject):
    """The interface, and the silent base every tier fills in."""

    positionChanged = Signal(int)                 # ms into the file
    durationChanged = Signal(int)                 # ms; 0 = unknown
    stateChanged = Signal(str)                    # PLAYING | PAUSED | STOPPED
    failed = Signal(str)                          # a sentence for the user

    name = "none"
    label = "No audio player"
    inline = True                                 # False: playback happens outside the app
    can_seek = False
    can_pause = False

    def __init__(self, parent=None):
        super().__init__(parent)
        self._path = None
        self._state = STOPPED
        self._duration = 0
        self._loop = None                         # (start_ms, end_ms) or None
        self._volume = 0.6

    # -- the surface the doc drives --
    def load(self, path, *, duration_ms=0):
        """Point the player at a file (stopping whatever was playing). ``duration_ms`` is the caller's
        own knowledge of the length -- a tier that cannot measure it reports this."""
        self.stop()
        self._path = str(path)
        self._duration = int(duration_ms or 0)
        self.durationChanged.emit(self._duration)

    def play(self):
        self._set_state(PLAYING)

    def pause(self):
        self._set_state(PAUSED)

    def stop(self):
        self._set_state(STOPPED)

    def seek(self, ms):
        self.positionChanged.emit(max(0, int(ms)))

    def position(self) -> int:
        return 0

    def duration(self) -> int:
        return self._duration

    def state(self) -> str:
        return self._state

    def path(self):
        return self._path

    def set_loop(self, start_ms=None, end_ms=None):
        """Loop the region ``start_ms..end_ms`` while playing (the track's own loop points), or pass
        nothing to play straight through. A preview: the jump lands on the tier's own clock tick, so it
        is audibly close to, not sample-exact with, the in-game loop."""
        ok = start_ms is not None and end_ms is not None and int(end_ms) > int(start_ms) >= 0
        self._loop = (int(start_ms), int(end_ms)) if ok else None

    def set_volume(self, v: float):
        self._volume = min(1.0, max(0.0, float(v)))

    def volume(self) -> float:
        return self._volume

    def shutdown(self):
        """Release the device / kill the child. Safe to call twice."""
        self.stop()

    # -- shared --
    def _set_state(self, st):
        if st != self._state:
            self._state = st
            self.stateChanged.emit(st)


class NullPlayer(Player):
    """Silent and stateful: says it is playing, emits no sound, advances no clock."""
    name = "null"
    label = "Audio is off (FF9MAPKIT_NO_AUDIO)"
    can_seek = True
    can_pause = True

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pos = 0

    def load(self, path, *, duration_ms=0):
        super().load(path, duration_ms=duration_ms)
        self._pos = 0

    def seek(self, ms):
        self._pos = max(0, int(ms))
        self.positionChanged.emit(self._pos)

    def stop(self):
        self._pos = 0
        super().stop()

    def position(self) -> int:
        return self._pos


class QtPlayer(Player):
    """QtMultimedia. Constructing this imports the module -- callers go through :func:`make_player`."""
    name = "qt"
    label = "Qt audio"
    can_seek = True
    can_pause = True

    def __init__(self, parent=None):
        # the import comes FIRST: on an Essentials-only install it raises here, before a QObject
        # parented to the tab exists to be left behind half-built (make_player catches it)
        from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
        super().__init__(parent)
        self._QMediaPlayer = QMediaPlayer
        self._out = QAudioOutput(self)
        self._out.setVolume(self._volume)
        self._mp = QMediaPlayer(self)
        self._mp.setAudioOutput(self._out)
        self._mp.positionChanged.connect(self._on_position)
        self._mp.durationChanged.connect(self._on_duration)
        self._mp.playbackStateChanged.connect(self._on_state)
        self._mp.mediaStatusChanged.connect(self._on_status)
        self._mp.errorOccurred.connect(lambda _e, text: self.failed.emit(text or "The file could not be played."))

    def load(self, path, *, duration_ms=0):
        self._mp.stop()
        self._path = str(path)
        self._duration = int(duration_ms or 0)
        self._mp.setSource(QUrl.fromLocalFile(self._path))
        self.durationChanged.emit(self._duration)

    def play(self):
        self._mp.play()

    def pause(self):
        self._mp.pause()

    def stop(self):
        self._mp.stop()

    def seek(self, ms):
        self._mp.setPosition(max(0, int(ms)))

    def position(self) -> int:
        return int(self._mp.position())

    def set_volume(self, v: float):
        super().set_volume(v)
        self._out.setVolume(self._volume)

    def shutdown(self):
        self._mp.stop()
        self._mp.setSource(QUrl())                 # let go of the file (Windows holds it open)

    def _on_position(self, ms):
        if self._loop is not None and self._state == PLAYING and ms >= self._loop[1]:
            self._mp.setPosition(self._loop[0])
            return
        self.positionChanged.emit(int(ms))

    def _on_duration(self, ms):
        if ms > 0:                                 # the decoder's own length beats the caller's estimate
            self._duration = int(ms)
            self.durationChanged.emit(self._duration)

    def _on_state(self, st):
        S = self._QMediaPlayer.PlaybackState
        self._set_state({S.PlayingState: PLAYING, S.PausedState: PAUSED}.get(st, STOPPED))

    def _on_status(self, status):
        if status == self._QMediaPlayer.MediaStatus.EndOfMedia and self._loop is not None:
            self._mp.setPosition(self._loop[0])    # a loop whose end is the file's end
            self._mp.play()


def ffplay_argv(exe, path, start_ms=0, volume=0.6) -> list:
    """The ``ffplay`` command line for one headless playback from ``start_ms``. Pure."""
    argv = [str(exe), "-nodisp", "-autoexit", "-hide_banner", "-loglevel", "error",
            "-volume", str(int(round(min(1.0, max(0.0, float(volume))) * 100)))]
    if start_ms and int(start_ms) > 0:
        argv += ["-ss", f"{int(start_ms) / 1000.0:.3f}"]
    return argv + [str(path)]


class FfplayPlayer(Player):
    """``ffplay`` as a child process. The position is this process's own clock from the moment the
    child started (ffplay reports none on a pipe we would want to parse), so it is an estimate; pause
    and seek are a restart at an offset, which costs a short gap."""
    name = "ffplay"
    label = "ffplay"
    can_seek = True
    can_pause = True
    TICK_MS = 100

    def __init__(self, exe, parent=None):
        super().__init__(parent)
        self._exe = str(exe)
        self._proc = None
        self._offset = 0                           # ms the current run started at
        self._clock = QElapsedTimer()
        self._tick = QTimer(self)
        self._tick.setInterval(self.TICK_MS)
        self._tick.timeout.connect(self._on_tick)

    def load(self, path, *, duration_ms=0):
        self._kill()
        self._offset = 0
        self._path = str(path)
        self._duration = int(duration_ms or 0)
        self._set_state(STOPPED)
        self.durationChanged.emit(self._duration)

    def play(self):
        if self._path is None or self._state == PLAYING:
            return
        self._start(self._offset)

    def pause(self):
        if self._state != PLAYING:
            return
        self._offset = self.position()
        self._kill()
        self._set_state(PAUSED)

    def stop(self):
        self._kill()
        self._offset = 0
        self._set_state(STOPPED)
        self.positionChanged.emit(0)

    def seek(self, ms):
        ms = max(0, int(ms))
        if self._state == PLAYING:
            self._start(ms)
        else:
            self._offset = ms
            self.positionChanged.emit(ms)

    def position(self) -> int:
        if self._state == PLAYING and self._clock.isValid():
            return self._offset + int(self._clock.elapsed())
        return self._offset

    def shutdown(self):
        self._kill()
        self._set_state(STOPPED)

    def _start(self, at_ms):
        self._kill()
        self._offset = int(at_ms)
        proc = QProcess(self)
        proc.finished.connect(lambda _code, _status, p=proc: self._on_finished(p))
        proc.errorOccurred.connect(lambda _err, p=proc: self._on_error(p))
        argv = ffplay_argv(self._exe, self._path, self._offset, self._volume)
        self._proc = proc
        proc.start(argv[0], argv[1:])
        self._clock.start()
        self._tick.start()
        self._set_state(PLAYING)

    def _kill(self):
        self._tick.stop()
        proc, self._proc = self._proc, None
        if proc is not None:                       # detach first: our own kill must not read as "ended"
            proc.kill()
            proc.waitForFinished(500)
            proc.deleteLater()

    def _on_tick(self):
        pos = self.position()
        if self._loop is not None and pos >= self._loop[1]:
            self._start(self._loop[0])
            return
        self.positionChanged.emit(pos)

    def _on_finished(self, proc):
        if proc is not self._proc:                 # a child we killed ourselves
            return
        self._tick.stop()
        self._proc = None
        proc.deleteLater()
        if self._loop is not None and self._state == PLAYING:
            self._start(self._loop[0])
            return
        self._offset = 0
        self._set_state(STOPPED)
        self.positionChanged.emit(0)

    def _on_error(self, proc):
        if proc is not self._proc:
            return
        self._tick.stop()
        self._proc = None
        self._offset = 0
        self._set_state(STOPPED)
        self.failed.emit("ffplay could not be started.")


class ExternalPlayer(Player):
    """The system's default player for the file type. The app cannot stop, seek or follow it."""
    name = "external"
    label = "your system's default player"
    inline = False

    def play(self):
        if self._path is None:
            return
        from PySide6.QtGui import QDesktopServices
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(self._path)):
            self.failed.emit("No application is registered to open .ogg files.")

    def pause(self):
        pass

    def stop(self):
        pass


def find_ffplay():
    """Path to ``ffplay``, or None. ``$FFPLAY`` overrides the PATH lookup."""
    env = os.environ.get("FFPLAY")
    if env and shutil.which(env):
        return shutil.which(env)
    return shutil.which("ffplay")


def audio_disabled() -> bool:
    return bool(os.environ.get("FF9MAPKIT_NO_AUDIO"))


def make_player(parent=None) -> Player:
    """The best player this environment has (see the module docstring). Never raises: a tier that
    cannot be built is skipped, and the last one needs nothing but a file association."""
    if audio_disabled():
        return NullPlayer(parent)
    try:
        return QtPlayer(parent)
    except Exception:       # noqa: BLE001 -- no QtMultimedia (the Essentials pin) or no audio backend
        pass
    exe = find_ffplay()
    if exe:
        return FfplayPlayer(exe, parent)
    return ExternalPlayer(parent)


def format_ms(ms) -> str:
    """``84700 -> "1:24"``."""
    s = max(0, int(ms or 0)) // 1000
    return f"{s // 60}:{s % 60:02d}"
