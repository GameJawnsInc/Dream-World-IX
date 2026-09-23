"""The game's two exception logs, and how to read an exception out of either.

WHICH LOG AN EXCEPTION LANDS IN IS DECIDED BY WHO CATCHES IT, not by "Unity vs Memoria":

* ``Memoria.log`` -- anything thrown under a Memoria ``catch (Exception err) { Log.Error(err); }``,
  as ``|E|`` lines with the whole stack, one timestamped line per frame. ALL battle code is here:
  ``HonoluluBattleMain.Update`` wraps the battle loop exactly that way.
* ``x64/FF9_Data/output_log.txt`` -- Unity's own log. An exception nobody caught (a MonoBehaviour
  ``Update`` throwing, e.g. ``FieldMapActorController.MovePC``) lands here ONLY, as an untimestamped
  block. Rewritten on every launch.

Measured 2026-09-23 (harness run ``mp-retype-3``): 637 battle-init NREs in Memoria.log and 0 in
output_log; 18 MovePC NREs in output_log and 0 in Memoria.log. A check that reads one file returns a
false clean for the other half, which is how a scenario once reported "no exception" beside 637 of
them. So nothing here reads one log without the other; :class:`harness.Session` owns the paths, the
marks and the staleness rules, and this module only parses.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

#: The two logs, by the file name they are archived under in a run directory.
MEMORIA_LOG = "Memoria.log"
UNITY_LOG = "output_log.txt"

#: Where Unity 5.2 writes its log for this install: beside the player's ``_Data`` folder.
UNITY_LOG_PATH = Path("x64") / "FF9_Data" / UNITY_LOG

#: `dd.MM.yyyy HH:mm:ss |L| message` -- every Memoria line, a stack frame included.
MEMORIA_LINE = re.compile(r"^(\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}:\d{2}) \|(\w)\| ?(.*)$")

#: An exception type anywhere in a Memoria ``|E|`` message (the header may carry a context prefix).
_TYPE_IN = re.compile(r"\b((?:[A-Za-z_][\w.]*)?Exception)\b")

#: A Unity exception header: the type at column 0, then ``: message`` or nothing. Anchored, because
#: output_log is mostly free text and a sentence that merely mentions an exception is not one.
_UNITY_HEAD = re.compile(r"^((?:[A-Za-z_][\w.]*)?Exception)(?::\s*(.*))?$")

#: The method a stack frame names: ``Type.Method (args) [0x00000] in ...``, optionally behind a
#: ``(wrapper managed-to-native)`` tag, which names the transition and not the method.
_FRAME = re.compile(r"^(?:\(wrapper [^)]*\)\s*)?([^\s(]+)")

#: How far back a mark looks for the start of the line it lands in.
_SNAP_WINDOW = 64 * 1024


@dataclass
class LogException:
    """One exception read out of either log."""

    log: str                        #: MEMORIA_LOG or UNITY_LOG -- which one says who caught it
    type: str                       #: as logged: ``System.NullReferenceException`` / ``NullReferenceException``
    message: str
    trace: list[str] = field(default_factory=list)   #: frames, innermost first, without the ``at ``
    stamp: str | None = None        #: Memoria's ``dd.MM.yyyy HH:mm:ss``; None in Unity's untimestamped log

    @property
    def name(self) -> str:
        """The type without its namespace, so the two logs compare equal."""
        return self.type.rsplit(".", 1)[-1]

    @property
    def where(self) -> str | None:
        """The innermost frame's method, e.g. ``btl_init.OrganizeEnemyData`` -- None with no trace."""
        return frame_method(self.trace[0]) if self.trace else None

    def through(self, *names: str) -> bool:
        """True when any frame of the trace mentions any of ``names``."""
        return any(n in f for f in self.trace for n in names)

    def __str__(self) -> str:
        return f"{self.name} at {self.where or '?'} ({self.log})"


def frame_method(frame: str) -> str | None:
    """The method a frame names (``at `` already stripped or not)."""
    text = frame.strip()
    if text.startswith("at "):
        text = text[3:]
    m = _FRAME.match(text)
    return m.group(1) if m else None


def _memoria_body(line: str) -> str:
    m = MEMORIA_LINE.match(line)
    return m.group(3) if m else line


def frame_after(lines: list[str], i: int) -> str | None:
    """The innermost frame of the exception whose header is ``lines[i]``, in either log's format.

    Only the very next line: anything further may already be the NEXT exception's trace.
    """
    if i + 1 >= len(lines):
        return None
    body = _memoria_body(lines[i + 1]).strip()
    return frame_method(body) if body.startswith("at ") else None


def parse_memoria(lines: list[str]) -> list[LogException]:
    """Every ``|E|`` exception in Memoria.log ``lines``, with the ``|E|   at`` frames that follow it."""
    out: list[LogException] = []
    cur: LogException | None = None
    for line in lines:
        m = MEMORIA_LINE.match(line)
        if not m or m.group(2) != "E":
            cur = None
            continue
        stamp, body = m.group(1), m.group(3)
        if body.lstrip().startswith("at ") and body[:1].isspace():
            if cur is not None:
                cur.trace.append(body.strip()[3:])
            continue
        head = body.strip()
        t = _TYPE_IN.search(head)
        if t is None:
            cur = None                              # an error message, not an exception
            continue
        rest = head[t.end():].lstrip()
        # `Type: message` keeps just the message; a header with a context prefix keeps all of it.
        message = rest[1:].strip() if t.start() == 0 and rest.startswith(":") else head
        cur = LogException(MEMORIA_LOG, t.group(1), message, stamp=stamp)
        out.append(cur)
    return out


def parse_unity(lines: list[str]) -> list[LogException]:
    """Every exception block in output_log.txt ``lines``: a column-0 header, then indented frames.

    Takes :func:`split_lines` output, and tolerates ``str.splitlines()`` output too: that reads each
    ``CR CR LF`` frame end as a frame plus an EMPTY line, so an empty line inside a trace is skipped
    rather than taken as its end. The block's real terminator is a line holding one space.
    """
    out: list[LogException] = []
    cur: LogException | None = None
    for line in lines:
        if cur is not None and line.rstrip("\r\n") == "":
            continue
        text = line.rstrip()
        if cur is not None and text[:1].isspace() and text.lstrip().startswith("at "):
            cur.trace.append(text.strip()[3:])
            continue
        m = _UNITY_HEAD.match(text)
        if m:
            cur = LogException(UNITY_LOG, m.group(1), (m.group(2) or "").strip())
            out.append(cur)
        else:
            cur = None
    return out


PARSERS = {MEMORIA_LOG: parse_memoria, UNITY_LOG: parse_unity}


def line_start_offset(path: Path) -> int:
    """The file's size, snapped back to the start of a line the writer has not finished.

    A mark taken mid-line would split a header from its own frames -- the header before the mark,
    the frames after -- and the exception would then be invisible from both sides. Snapping back
    re-reads that one line instead: the error it can make is a line too many, never a false clean.
    """
    with open(path, "rb") as f:
        f.seek(0, 2)
        size = f.tell()
        back = min(size, _SNAP_WINDOW)
        f.seek(size - back)
        tail = f.read(back)
    cut = tail.rfind(b"\n")
    return size - back + cut + 1 if cut >= 0 else size - back


def split_lines(text: str) -> list[str]:
    """Lines split on LF alone, their trailing CRs dropped.

    NOT ``str.splitlines()``, nor a text-mode read: Unity ends every stack frame but the last with
    ``CR CR LF`` (measured, this install's output_log.txt), which both read as the frame AND an empty
    line -- so every trace ended after its first frame and the line budget of a tail went to blanks.
    """
    lines = [line.rstrip("\r") for line in text.split("\n")]
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def read_from(path: Path, offset: int = 0) -> str:
    """The text written at or after byte ``offset``. A file SHORTER than the offset was rewritten
    (a relaunch) since the offset was taken, so all of it is new."""
    with open(path, "rb") as f:
        f.seek(0, 2)
        if offset > f.tell():
            offset = 0
        f.seek(offset)
        data = f.read()
    return data.decode("utf-8-sig", errors="replace")
