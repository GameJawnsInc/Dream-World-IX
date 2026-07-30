"""The Floorplan document — click-authoring Rung 6c's Workspace host.

Charter: ``studies/click-authoring/PLAN.md`` rung 6; the buildable math and every constant's
provenance: ``studies/click-authoring/RUNG6.md``. The author lays several rooms out on a
plan-view chart, declares which shared walls are doors, and presses Compose to get a wired
dungeon — one FF9 field per room, gateways both ways, an arrival position AND FACING per side.
:func:`ff9mapkit.floorplan.compose` already does all the thinking; this is its face.

★ **THE CHART IS NOT A CAMERA.** :class:`PlanCanvas` owns ONE isotropic px<->world affine pair
(:meth:`PlanCanvas.world_to_scene` / :meth:`PlanCanvas.scene_to_world`) and no call site scales
anything ad hoc. A pitch-90 :class:`~.backdrop.BackdropCanvas` camera *is* exactly affine, but it
is anisotropic by ``1/K_VSCALE`` = 15/14, so a drawn square would become a 15:14 room — and
``BackdropCanvas.click_to_world`` hard-raises when its camera is None, so it cannot be borrowed
for a chart at all (RUNG6.md §2). The factor is :data:`_WORLD`, the same one
:class:`~.behaviordoc.StageCanvas` uses, so the two plan-view instruments and the offline layout
probe all read a room at the same size. **+z is UP the screen** (the layout probe's frame).

★ **THE CANVAS EMITS, IT NEVER WRITES** (``backdrop.py``'s own law). Every gesture ends in
exactly ONE signal per DROP and the host owns the document mutation and the undo step. A press on
something grabbable is only PROVISIONAL — :meth:`PlanCanvas.release_world` re-resolves it, because
a dungeon is rooms that SHARE walls and a new room's first corner is therefore the neighbour's own
corner, which a grab would swallow.

★ **THE COLOUR LIVES IN THE STROKES; CHART TEXT IS ONLY ``text`` OR ``muted``.** THE NINTH-GROUND
LAW: a room's wash is a third colour under chart text, so no fg/bg fence covers it. See
:data:`_FILL_ALPHA` for the measured numbers this rule replaced.

★ **UNDO IS DOC-LOCAL**, a :meth:`FloorplanDoc._push_history` snapshot stack over the whole
geometry document — deliberately NOT the shell's ``_checkpoint``. ``shell._UndoRec`` is
single-member, so a door edit — which necessarily spans TWO rooms, emitting a gateway on one
side and an arrival row on the other — could never be one shell undo step. A half-undone door
pair is a gateway with no arrival: the destination falls through to ``[player] spawn``
SILENTLY (``lint_player_arrivals`` catches only self-loops), which is precisely the hazard
gate G3 exists to refuse. A snapshot stack makes the pair atomic by construction.

★ **THE LIVE GATE FEEDBACK IS THE TAB'S REAL VALUE.** ``compose`` is pure and raises
``ComposeError`` carrying EVERY problem, so it runs on every edit: offending rooms and doors
paint in the error colour, every problem is listed (an unattributable one is still listed —
never swallowed), and Compose is disabled with a tooltip saying why. It is not free (~0.5s per
room, dominated by :func:`~ff9mapkit.floorplan.standable`'s grid sampling), so it runs
debounced on a worker thread with a generation counter, exactly like BehaviorDoc's sweep; a
stale verdict never paints and Compose never rides one.

Laws honoured: no I/O at construction or on tab show (the startup-spend law — the only disk
touches are the user's own Open and Compose clicks); dialogs are INSTANCE dialogs behind
per-instance seams (a static execs in C++ past every test patch); the canvas is painted, so
CALIBRE arrives via ``set_scale`` and themes via ``retheme`` (the mapview rule); the id box is
built by :func:`~.widgets.id_field` and validated through ``pack.check_custom_id`` (the one
shared band voice, not a copy).
"""

from __future__ import annotations

import copy
import math
import re
import sys
import threading
from pathlib import Path

from PySide6.QtCore import QPointF, QRect, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (
    QFileDialog, QFormLayout, QGraphicsScene, QGraphicsView, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

from .. import floorplan as FP
from . import widgets

# world units -> scene px at zoom 1. StageCanvas's own factor (behaviordoc._WORLD), spent here
# on purpose: two plan-view charts that disagree about how big 500u is are two different rooms.
_WORLD = 0.12
_ZOOM_MIN, _ZOOM_MAX = 0.02, 8.0
_HANDLE_R = 4                  # a room vertex handle's screen radius (px, zoom-immune)
_CLICK_SLOP_PX = 4             # press->release travel at/under this is a CLICK, past it a pan
_CLOSE_PX = 12                 # a click this close (screen px) to the first corner CLOSES the room
_PICK_PX = 10                  # screen-px reach when picking a door / candidate segment
_HISTORY_CAP = 100
_BARE_SPAN = 4000.0            # the empty chart's framed world span, so a bare tab has a scale

# ★ THE NINTH-GROUND LAW, paid in full. A room's wash is a THIRD colour under chart text, so no
# existing fg/bg fence covers it — and the first cut proved why: the room NAME was drawn in the
# SAME token as its own fill (accent on accent@38, warn on warn@44, error on error@60), which
# measures 2.16:1 on nord, 2.72-2.94 on solarized-dark/gruvbox — sub-AA in most of the 8 palettes,
# under even the 3.0 NON-text floor in six of them. The rule that replaced it, and the only reason
# these numbers are provable: **THE COLOUR LIVES IN THE STROKES; CHART TEXT IS ONLY ``text`` OR
# ``muted``.** 20 is the largest alpha at which BOTH clear 4.5 over every accent/warn/error wash
# in every palette (worst 5.13 / 4.53; at 44 muted is 3.77 and at 60 it is 3.11). A room's state
# is still said three ways that survive this: the stroke colour, the stroke WIDTH, and a ✕ / !
# glyph on the name — so it also survives colour blindness, which the ink never did.
# Fenced by test_workspace_floorplan.test_every_chart_ink_clears_its_ground.
_FILL_ALPHA = 20


def _poly_pts(poly):
    """A stored polygon (json lists or tuples) as float ``(x, z)`` tuples."""
    return [(float(p[0]), float(p[1])) for p in poly]


# ``compose``'s messages have a SUBJECT, and it is always at the head. Parsing it is what keeps
# the paint honest: the reachability warning reads "unreachable from ROOM1: ROOM2, ROOM3", and a
# bare whole-message scan lit up ROOM1 — the entry room, the one room the warning is NOT about.
# (The snap caught that: all three rooms wore the warn colour and only two were unreachable.)
_HEADS = (
    # (pattern, which capture groups hold room names, whether the group is a comma LIST)
    (re.compile(r"^unreachable from [^:]+:\s*(.+?)\s+--"), (1,), True),
    (re.compile(r"^rooms (.+?) and (.+?) overlap"), (1, 2), False),
    (re.compile(r"^room ([^:,]+)[:,]"), (1,), False),
    (re.compile(r"^two rooms are both named '(.+?)'"), (1,), False),
    (re.compile(r"^entry room '(.+?)' is not in the floorplan"), (1,), False),
)


def attribute_problems(problems, room_names, doors):
    """``(bad_rooms, bad_doors, unattributed)`` — which room / door each problem is ABOUT.

    ``compose`` writes its messages ``room <NAME>: ...`` and ``door <A>-<B>: ...`` for exactly
    this purpose, so the SUBJECT is parsed off the head first (see :data:`_HEADS`). Only when no
    head form matches does it fall back to a whole-message scan, and that scan is word-bounded —
    never a bare substring, which would make ``ROOM1`` light up for every problem on ``ROOM10``.
    A problem that names nothing recognisable comes back in ``unattributed`` so the host can
    still LIST it: a swallowed problem is worse than an unattributed one.

    Pure, so the fences drive it directly.
    """
    known = {str(n) for n in room_names if n}
    bad_rooms, bad_doors, loose = set(), set(), []
    for p in problems:
        hit = False
        for pat, groups, is_list in _HEADS:
            m = pat.match(p)
            if not m:
                continue
            for g in groups:
                for raw in (m.group(g).split(",") if is_list else [m.group(g)]):
                    nm = raw.strip()
                    if nm in known:
                        bad_rooms.add(nm)
                        hit = True
            break
        for di, d in enumerate(doors):
            a, b = str(d.get("a") or ""), str(d.get("b") or "")
            if not (a and b):
                continue
            if re.search(rf"\b{re.escape(a)}-{re.escape(b)}\b", p) \
                    or re.search(rf"\b{re.escape(b)}-{re.escape(a)}\b", p):
                bad_doors.add(di)
                bad_rooms.update({a, b} & known)
                hit = True
        if hit:
            continue
        for n in sorted(known):                    # the fallback: a shape _HEADS does not know
            if re.search(rf"\b{re.escape(n)}\b", p):
                bad_rooms.add(n)
                hit = True
        if not hit:
            loose.append(p)
    return bad_rooms, bad_doors, loose


def candidate_doors(rooms, doors, *, tol=8.0):
    """Every wall two rooms SHARE that is not already a declared door, longest first.

    ``shared_edges`` OFFERS candidates; the author declares the door (THE DRAWN-MESH LAW). The
    already-declared filter matches on the room PAIR plus the segment midpoint within ``tol``,
    because a declared door's stored segment is the rounded candidate, not a fresh one.

    Pure (no Qt), so both the canvas feed and the fences read the same list.
    """
    taken = []
    for d in doors:
        seg = _poly_pts(d.get("seg") or ())
        if len(seg) == 2:
            taken.append((frozenset((str(d.get("a")), str(d.get("b")))), FP.midpoint(seg)))
    out = []
    for i, ra in enumerate(rooms):
        pa = _poly_pts(ra.get("poly") or ())
        if len(pa) < 3:
            continue
        for rb in rooms[i + 1:]:
            pb = _poly_pts(rb.get("poly") or ())
            if len(pb) < 3:
                continue
            pair = frozenset((str(ra.get("name")), str(rb.get("name"))))
            try:
                cands = FP.shared_edges(pa, pb, tol=tol)
            except (FP.ComposeError, ValueError, ZeroDivisionError):
                continue                       # a sick outline offers nothing; G1 reports it
            for c in cands:
                m = FP.midpoint(c["seg"])
                if any(p == pair and math.hypot(m[0] - t[0], m[1] - t[1]) <= tol
                       for p, t in taken):
                    continue                   # already a door on this wall
                out.append({"a": str(ra.get("name")), "b": str(rb.get("name")),
                            "seg": c["seg"], "length": c["length"]})
    out.sort(key=lambda r: -r["length"])
    return out


# ---------------------------------------------------------------- the screen-fixed chip clearance
# ★ THE CHIPS ARE NOT ON THE CHART, SO NO SCENE-SPACE REASONING CAN SEE THEM. Every other
# de-collision in this file argues in world/scene space against other chart ink — a room outline, a
# door strip, a neighbour's label stack (see _draw_room, _draw_candidates, _draw_doors, and their
# shared rule: "offsetting is geometry; raising z is not"). ``_hint`` and ``_compass`` are QLabel
# CHILDREN OF THE VIEWPORT pinned to its corners by :meth:`PlanCanvas._place_hint`; they live in
# viewport px, are painted by Qt ABOVE the scene, and are invisible to all of it by construction.
# That the chips own bands of the viewport is already known where the chart's HEIGHT is budgeted —
# but a floor only says how much room the chart gets, never where a label inside it lands.
#
# Measured (native, 1280x850, dark, the refused plan): the door caption
# '✕ ROOM1↔ROOM2 · 100u deep · selected' prints INSIDE the zoom hint, 186px x 16px at chart height
# 178, easing to a 7px bite at 228 and clean past ~270; at CALIBRE 125 the same caption bites
# 89px x 11px over chart heights ~156-226. The band is a function of chart HEIGHT alone (same
# widget, same viewport width, same fit math), so every layout that can produce those heights
# prints it. The other four tiers _label serves (room name / metrics / entry, the shared-wall
# caption, the pending-corner caption) never reached a chip in the census, which is exactly why the
# fence is on the CLASS and not on that one string.
#
# The cure is this file's own: OFFSET IS GEOMETRY. A label whose ink would land on a chip flips to
# the other side of its own anchor — behaviordoc's ``dx = -dx - width`` mirror, the same "canvas
# labels flip LEFT at the right edge" idiom — so the leader point it names stays honest.
#
# ...and it is judged on INK, never on the boundingRect. A text item's box carries the font's
# leading and descent, so a label sitting one clean line above a chip still INTERSECTS it by a few
# px: an intersection is not a collision. Measured (Segoe UI at CALIBRE 150) the door caption's box
# is 22.0px tall around 15.7px of ink — 5.4px of slack above the glyphs and 0.9 below. Flipping on
# box intersection would move labels that are visibly clear; ignoring the 8px box intersection at
# chart height 228 would leave 7.1px of real glyph buried under the chip. So the box is deflated to
# the ink Qt actually paints (``QFontMetricsF.tightBoundingRect``) and any positive intersection of
# THAT is a collision. Fenced by test_workspace_floorplan's chip-clearance block.


def _overlap(ax, ay, aw, ah, bx, by, bw, bh):
    """Two rects' intersection as ``(w, h)``, ``(0, 0)`` when they do not meet."""
    ow = min(ax + aw, bx + bw) - max(ax, bx)
    oh = min(ay + ah, by + bh) - max(ay, by)
    return (ow, oh) if ow > 0 and oh > 0 else (0.0, 0.0)


def label_offsets(dx, dy, w, h, *, centre=False):
    """A label's authored offset, then its MIRRORS about the anchor: x, then y, then both.

    The mirror is behaviordoc's own (``dx = -dx - width``): the label lands the same distance from
    the anchor on the OPPOSITE side, so the point it labels is still the point it points at.

    x BEFORE y, measured: the chips are viewport-CORNER bands about 31px tall, and a y mirror moves
    a label by little more than its own height — the door caption straddles its own anchor
    (dy=-14, box 22px), so its y mirror is a 6px step that lands it right back in the chip, while
    its x mirror is ``width + 2*dx`` = 326px and leaves decisively. A ``centre``d label has no x
    side to swap to (its offset IS -w/2), so its x mirror is itself and drops out.

    Pure, so the fences drive it directly.
    """
    xs = [-w / 2.0] if centre else [dx, -dx - w]
    out = []
    for oy in (dy, -dy - h):
        for ox in xs:
            if (ox, oy) not in out:
                out.append((ox, oy))
    return out


def clear_of_chips(offsets, anchor, ink, chips, viewport=None):
    """Which of ``offsets`` keeps a label's INK off the screen-fixed viewport chips.

    ``anchor`` is ``(ax, ay)`` in viewport px; ``ink`` the label's ink box ``(x, y, w, h)`` in
    label-local px, which the chosen offset translates; ``chips`` a list of ``(x, y, w, h)``
    viewport rects; ``viewport`` an optional ``(w, h)`` used ONLY to prefer a mirror that stays on
    screen.

    ★ ``offsets[0]`` — the authored placement — WINS UNLESS IT ACTUALLY COLLIDES, and that early
    return is the whole safety of this pass. It is a chip clearance and nothing else: with no chip
    under the label the geometry every other comment in this file was measured against comes back
    byte for byte, so a mirror can never appear for a reason nobody can see, and the tier
    thresholds, the ``_along`` offsets and the centring all keep meaning exactly what they say.

    Among the alternatives the order is behaviordoc's: clear beats overlapping, on-screen beats
    clipped, then the shallowest bite, then the authored order. That makes the choice TOTAL — every
    candidate scores, ties break on index — so the same geometry always picks the same offset and a
    redraw can never oscillate between two of them.

    Pure, so the fences drive it directly.
    """
    if not offsets:
        return (0.0, 0.0)
    if not chips:
        return offsets[0]
    ix, iy, iw, ih = ink
    ax, ay = anchor

    def bite(ox, oy):
        """The deepest ink-vs-chip intersection this offset produces (0 = clear)."""
        bx, by = ax + ox + ix, ay + oy + iy
        return max([min(_overlap(bx, by, iw, ih, *c)) for c in chips], default=0.0)

    if bite(*offsets[0]) <= 0:
        return offsets[0]
    best, best_key = offsets[0], None
    for i, (ox, oy) in enumerate(offsets):
        d = bite(ox, oy)
        clipped = 0
        if viewport is not None:
            vw, vh = viewport
            bx, by = ax + ox + ix, ay + oy + iy
            clipped = 0 if (bx >= 0 and by >= 0 and bx + iw <= vw and by + ih <= vh) else 1
        key = (1 if d > 0 else 0, clipped, d, i)
        if best_key is None or key < best_key:
            best, best_key = (ox, oy), key
    return best


class PlanCanvas(QGraphicsView):
    """The floorplan as a plan-view CHART: rooms drawn corner by corner, shared walls offered
    as door candidates, +z up-screen, one isotropic world<->px pair.

    View grammar is the atlas family's (Ctrl+scroll zoom / Ctrl+0 fit / Ctrl+1 1:1, pan by
    drag); a press-release pair that travels no further than :data:`_CLICK_SLOP_PX` is a CLICK,
    so panning and drawing share the left button without a mode.

    Picking is done in WORLD space against the fed geometry (``_pick_*``), never through
    ``itemAt``/``parentItem`` — which sidesteps the shiboken ownership flip that deletes a
    C++-owned item when ``parentItem()`` returns None (studies/pyside-gc-crash) and gives the
    fences a coordinate seam they can drive without synthesising Qt mouse events.

    The canvas emits, it never writes: one signal per DROP, the host owns the document.
    """

    room_drawn = Signal(object)            # a CLOSED outline: [(x, z), ...] plan-frame world units
    room_reshaped = Signal(int, object)    # (room index, its new polygon) — vertex OR whole-room drag
    room_rename = Signal(int)              # the room menu's Rename… — the host asks + writes
    room_entry = Signal(int)               # …Make this the entry
    room_deleted = Signal(int)             # …Delete
    door_declared = Signal(object)         # a candidate the author accepted: {"a", "b", "seg"}
    door_selected = Signal(int)            # an existing door clicked (-1 = the selection cleared)
    door_deleted = Signal(int)             # the door menu's Delete
    note = Signal(str)                     # a teach / refusal line for the host's status area

    MODES = ("rooms", "doors")

    def __init__(self, palette, *, scale=100):
        super().__init__()
        self.pal = palette
        self._scale = scale if scale in range(50, 301) else 100
        self._mode = "rooms"
        self._rooms = []                   # [{"name", "poly"}] — fed, never mutated here
        self._doors = []                   # [{"a", "b", "seg", "depth"}]
        self._cands = []                   # candidate_doors() rows
        self._bad_rooms = set()
        self._warn_rooms = set()
        self._bad_doors = set()
        self._entry = None                 # the entry room's name
        self._sel_door = None
        self._pending = []                 # the outline being drawn, world (x, z)
        self._hover = None                 # cursor world point, for the rubber band
        self._drag = None                  # live drag state; survives a _draw (it IS the source)
        self._zoom = 1.0
        self._fit_pending = True
        self._press_pos = None
        self._kids = []                    # STRONG refs to parented children (THE GC-CHILD LAW)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setBackgroundBrush(QColor(palette["surface"]))
        self.setAccessibleName("Floorplan chart")
        self.setAccessibleDescription(
            "A plan view of the dungeon's rooms in shared world units, +z up the screen: click "
            "to draw a room's corners, drag a corner or a room to move it, and in Doors mode "
            "click a highlighted shared wall to declare a door")
        self._hint = QLabel("Ctrl+scroll zooms · Ctrl+0 fits", self.viewport())
        self._hint.setObjectName("floorplanHint")      # selector-scoped (the round-9 census law)
        self._hint.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._compass = QLabel("+z north ▲ · −z south (the camera side) ▼ · +x east ▶",
                               self.viewport())
        self._compass.setObjectName("floorplanHint")
        self._compass.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._coords = QLabel("", self.viewport())
        self._coords.setObjectName("floorplanHint")
        self._coords.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._coords.hide()
        self._style_hint()
        self._draw()

    # ------------------------------------------------------------------ text + theme (CALIBRE)
    def _font(self, pt, bold=False):
        weight = QFont.Weight.DemiBold if bold else QFont.Weight.Normal
        return QFont("Segoe UI", max(1, round(pt * self._scale / 100)), weight)

    def set_scale(self, pct):
        pct = pct if pct in range(50, 301) else 100
        if pct == self._scale:
            return
        self._scale = pct
        self._style_hint()
        self._draw()

    def retheme(self, palette):
        self.pal = palette
        self.setBackgroundBrush(QColor(palette["surface"]))
        self._style_hint()
        self._draw()

    def _style_hint(self):
        surf = QColor(self.pal["surface"])
        sheet = ("QLabel#floorplanHint {"
                 f"color: {self.pal['muted']};"
                 f"background: rgba({surf.red()},{surf.green()},{surf.blue()},0.86);"
                 "border-radius: 9px; padding: 2px 9px; }")
        for lab in (self._hint, self._compass, self._coords):
            lab.setFont(self._font(8))
            lab.setStyleSheet(sheet)
        self._coords.setStyleSheet(sheet.replace(self.pal["muted"], self.pal["text"], 1))
        self._place_hint()

    def _place_hint(self):
        self._hint.adjustSize()            # measure AFTER polish -- construction adjustSize lies
        vp = self.viewport()
        self._hint.move(max(8, vp.width() - self._hint.width() - 10),
                        max(4, vp.height() - self._hint.height() - 8))
        self._compass.adjustSize()
        self._compass.move(10, 8)          # top-left: clear of the zoom hint's corner
        self._coords.adjustSize()
        self._coords.move(10, max(4, vp.height() - self._coords.height() - 8))

    # ------------------------------------------------------------------ THE frame pair
    @staticmethod
    def world_to_scene(x, z):
        """Plan-frame world ``(x, z)`` -> scene px. +z is UP, so scene y is negated."""
        return (x * _WORLD, -z * _WORLD)

    @staticmethod
    def scene_to_world(sx, sy):
        """Scene px -> plan-frame world ``(x, z)`` — the exact inverse of :meth:`world_to_scene`."""
        return (sx / _WORLD, -sy / _WORLD)

    def world_tol(self, px):
        """``px`` screen pixels as a WORLD distance at the current zoom (isotropic, so one number)."""
        return px / max(1e-6, self._zoom * _WORLD)

    def widget_to_world(self, pos):
        sp = self.mapToScene(pos.toPoint() if hasattr(pos, "toPoint") else pos)
        return self.scene_to_world(sp.x(), sp.y())

    # ------------------------------------------------------------------ public feed
    def set_mode(self, key):
        if key not in self.MODES or key == self._mode:
            return
        self._mode = key
        self._pending = []
        self._drag = None
        self._coords.hide()
        self._draw()

    def mode(self):
        return self._mode

    def set_plan(self, rooms, doors, *, candidates=(), bad_rooms=(), warn_rooms=(),
                 bad_doors=(), entry=None, selected_door=None, refit=False):
        """The whole fed state in one call — the host re-feeds after every write it makes.

        ``refit`` on a NEW document only: a same-document re-render keeps the user's zoom and
        pan (the map's own contract)."""
        self._rooms = [{"name": str(r.get("name") or ""), "poly": _poly_pts(r.get("poly") or ())}
                       for r in rooms]
        self._doors = [dict(d) for d in doors]
        self._cands = [dict(c) for c in candidates]
        self._bad_rooms = set(bad_rooms)
        self._warn_rooms = set(warn_rooms)
        self._bad_doors = set(bad_doors)
        self._entry = entry
        self._sel_door = selected_door
        self._drag = None                  # a re-feed replaces the geometry a drag was editing
        self._coords.hide()
        if refit:
            self.resetTransform()
            self._zoom = 1.0
            self._fit_pending = True
        self._draw()

    def pending(self):
        """The outline being drawn (world points) — the fences read it."""
        return list(self._pending)

    def clear_pending(self):
        if self._pending:
            self._pending = []
            self._draw()

    # ------------------------------------------------------------------ picking (world space)
    def _poly(self, ri):
        """Room ``ri``'s polygon, with a live drag's override applied."""
        d = self._drag
        if d is not None and d["ri"] == ri:
            return d["poly"]
        return self._rooms[ri]["poly"]

    def _pick_vertex(self, x, z, *, px=None):
        """``(room index, vertex index)`` of the nearest room corner within reach, else None."""
        tol = self.world_tol(_HANDLE_R + 4 if px is None else px)
        best = None
        for ri in range(len(self._rooms)):
            for vi, (vx, vz) in enumerate(self._poly(ri)):
                d = math.hypot(x - vx, z - vz)
                if d <= tol and (best is None or d < best[0]):
                    best = (d, (ri, vi))
        return None if best is None else best[1]

    def _pick_room(self, x, z):
        """The index of the topmost (last-drawn) room whose interior holds the point, else None."""
        for ri in range(len(self._rooms) - 1, -1, -1):
            poly = self._poly(ri)
            if len(poly) >= 3 and FP.point_in_poly(x, z, poly):
                return ri
        return None

    @staticmethod
    def _seg_dist(pt, seg):
        a, b = seg
        dx, dz = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dz * dz
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((pt[0] - a[0]) * dx + (pt[1] - a[1]) * dz) / L2))
        return math.hypot(pt[0] - (a[0] + t * dx), pt[1] - (a[1] + t * dz))

    def _pick_candidate(self, x, z):
        tol = self.world_tol(_PICK_PX)
        best = None
        for i, c in enumerate(self._cands):
            d = self._seg_dist((x, z), c["seg"])
            if d <= tol and (best is None or d < best[0]):
                best = (d, i)
        return None if best is None else best[1]

    def _pick_door(self, x, z):
        tol = self.world_tol(_PICK_PX)
        best = None
        for i, dr in enumerate(self._doors):
            seg = _poly_pts(dr.get("seg") or ())
            if len(seg) != 2:
                continue
            d = self._seg_dist((x, z), seg)
            if d <= tol and (best is None or d < best[0]):
                best = (d, i)
        return None if best is None else best[1]

    # ------------------------------------------------------------------ gestures (world space)
    # Mouse handlers are thin wrappers over these, which is the suite's own convention: the
    # tests drive the gesture, not Qt's event synthesis.
    def click_world(self, x, z):
        """One slop-click at world ``(x, z)`` in the current mode."""
        if self._mode == "doors":
            ci = self._pick_candidate(x, z)
            if ci is not None:
                c = self._cands[ci]
                self.door_declared.emit({"a": c["a"], "b": c["b"],
                                         "seg": [tuple(p) for p in c["seg"]]})
                return
            di = self._pick_door(x, z)
            self.door_selected.emit(-1 if di is None else di)
            if di is None and not self._cands:
                self.note.emit("No shared wall here. Two rooms must ABUT along a wall (within "
                               "8u, near-parallel) before it can become a door.")
            return
        pt = (int(round(x)), int(round(z)))
        if len(self._pending) >= 3:
            first = self._pending[0]
            if math.hypot(x - first[0], z - first[1]) <= self.world_tol(_CLOSE_PX):
                self._close_pending()
                return
        if self._pending and math.hypot(x - self._pending[-1][0],
                                        z - self._pending[-1][1]) < 1.0:
            self.note.emit("That is the corner you just placed — a duplicated corner is refused "
                           "by gate G1, so it is not added.")
            return
        self._pending.append(pt)
        self._draw()
        n = len(self._pending)
        self.note.emit(f"{n} corner{'' if n == 1 else 's'} placed — "
                       + ("keep clicking; a room needs at least 3." if n < 3 else
                          "click the first corner again (or double-click) to close the room."))

    def double_click_world(self, x, z):
        if self._mode == "rooms" and len(self._pending) >= 3:
            self._close_pending()
            return True
        return False

    def _close_pending(self):
        poly, self._pending = list(self._pending), []
        self._hover = None
        self.room_drawn.emit(poly)

    def press_world(self, x, z):
        """Begin a drag if something grabbable is under the point. True = the press is ours.

        ★ A True here is NOT yet a decision — :meth:`release_world` re-resolves it. See there."""
        if self._mode != "rooms" or self._pending:
            return False
        hit = self._pick_vertex(x, z)
        if hit is not None:
            ri, vi = hit
            self._drag = {"kind": "vert", "ri": ri, "vi": vi, "poly": list(self._rooms[ri]["poly"]),
                          "start": list(self._rooms[ri]["poly"])}
            self._update_coords()
            # the coords chip just APPEARED, and it is one of the screen-fixed chips the labels
            # are judged against: a press that never moves would otherwise leave it sitting on a
            # label until the drag's own redraw.
            self._draw()
            return True
        ri = self._pick_room(x, z)
        if ri is not None:
            self._drag = {"kind": "room", "ri": ri, "grab": (x, z),
                          "poly": list(self._rooms[ri]["poly"]),
                          "start": list(self._rooms[ri]["poly"])}
            self._update_coords()
            self._draw()
            return True
        return False

    def drag_world(self, x, z):
        d = self._drag
        if not d:
            return
        if d["kind"] == "vert":
            poly = list(d["start"])
            poly[d["vi"]] = (int(round(x)), int(round(z)))
            d["poly"] = poly
        else:
            dx = int(round(x - d["grab"][0]))
            dz = int(round(z - d["grab"][1]))
            d["poly"] = [(int(round(px)) + dx, int(round(pz)) + dz) for px, pz in d["start"]]
        self._update_coords()
        self._draw()

    def release_world(self, x, z, *, travel_px=0.0):
        """Resolve the press: a DRAG that moved is committed, a press that did not is a CLICK.

        ★ THE ONE GESTURE THAT MATTERS ON THIS CHART IS A ROOM THAT ABUTS ANOTHER, and its first
        corner is by definition the neighbour's own corner or wall. :meth:`press_world` grabs on
        anything under the cursor, so without this re-resolution that first click was swallowed by
        a zero-travel room/vertex grab: nothing appeared, nothing was said, and the author could
        not start an abutting room at all. Measured on the real Qt path (a synthesised
        press+release pair at ROOM1's corner left ``pending()`` empty) — invisible to the
        ``click_world`` seam, which never runs ``press_world``. So the grab is only PROVISIONAL:
        the release decides, exactly the way the pan/click split already did.
        """
        d = self._drag
        moved = d is not None and ([tuple(p) for p in d["poly"]]
                                   != [tuple(p) for p in d["start"]])
        if d is not None and not moved and travel_px <= _CLICK_SLOP_PX:
            self._drag = None                      # never a grab: it was a click all along
            self._coords.hide()
            self._draw()
            self.click_world(x, z)
            return
        self.end_drag()

    def end_drag(self):
        """Commit: EXACTLY one callback, and only when the geometry actually changed."""
        d, self._drag = self._drag, None
        self._coords.hide()
        if not d:
            return
        if [tuple(p) for p in d["poly"]] != [tuple(p) for p in d["start"]]:
            self.room_reshaped.emit(d["ri"], [tuple(p) for p in d["poly"]])
        else:
            self._draw()

    def _update_coords(self):
        d = self._drag
        if not d:
            return
        name = self._rooms[d["ri"]]["name"] if 0 <= d["ri"] < len(self._rooms) else "room"
        if d["kind"] == "vert":
            x, z = d["poly"][d["vi"]]
            self._coords.setText(f"{name} corner {d['vi']} · x {x} · z {z}")
        else:
            x0, z0, x1, z1 = FP.bbox(d["poly"])
            self._coords.setText(f"{name} · centre x {int(round((x0 + x1) / 2))} · "
                                 f"z {int(round((z0 + z1) / 2))}")
        self._coords.show()
        self._place_hint()

    # ------------------------------------------------------------------ Qt events
    def paintEvent(self, ev):                      # noqa: N802 (Qt override)
        if self._fit_pending:                      # deferred to the first REAL paint: at feed
            self._fit_pending = False              # time the tab may be hidden, the viewport stale
            self.fit()
        super().paintEvent(ev)

    def resizeEvent(self, ev):                     # noqa: N802 (Qt override)
        super().resizeEvent(ev)
        self._place_hint()
        self._draw()                               # the chip clearance is SCREEN space and the
        #                                            chips just moved with the corners, so every
        #                                            label has to be re-judged against them
        #                                            (behaviordoc's "re-run per draw, fit, zoom").
        #                                            The height band this fixes is REACHED by a
        #                                            resize, so a clearance that did not re-run
        #                                            here would be one the author drags out of.

    def wheelEvent(self, event):                   # noqa: N802 (Qt override)
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            f = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            z = max(_ZOOM_MIN, min(_ZOOM_MAX, self._zoom * f))
            if z != self._zoom:
                self.scale(z / self._zoom, z / self._zoom)
                self._zoom = z
                self._draw()                       # handles are screen-px: re-derive their world size
            event.accept()
            return
        super().wheelEvent(event)

    def keyPressEvent(self, event):                # noqa: N802 (Qt override)
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_0:
                self.fit()
                event.accept()
                return
            if event.key() == Qt.Key.Key_1:
                self.resetTransform()
                self._zoom = 1.0
                self._draw()
                event.accept()
                return
        if event.key() == Qt.Key.Key_Escape and self._pending:
            self.clear_pending()
            self.note.emit("outline abandoned")
            event.accept()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event):              # noqa: N802 (Qt override)
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.position()     # recorded EITHER WAY: release_world needs the
            #                                        travel to tell a grab from a click (see there)
            x, z = self.widget_to_world(event.position())
            if self.press_world(x, z):
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):               # noqa: N802 (Qt override)
        if self._drag:
            x, z = self.widget_to_world(event.position())
            self.drag_world(x, z)
            event.accept()
            return
        if self._mode == "rooms" and self._pending:
            self._hover = self.widget_to_world(event.position())
            self._draw()                           # the rubber band follows the cursor
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):            # noqa: N802 (Qt override)
        press, self._press_pos = self._press_pos, None
        travel = (0.0 if press is None
                  else float((event.position() - press).manhattanLength()))
        if self._drag and event.button() == Qt.MouseButton.LeftButton:
            x, z = self.widget_to_world(event.position())
            self.release_world(x, z, travel_px=travel)
            event.accept()
            return
        super().mouseReleaseEvent(event)
        if press is None or event.button() != Qt.MouseButton.LeftButton:
            return
        if travel > _CLICK_SLOP_PX:
            return                                 # it was a pan
        x, z = self.widget_to_world(event.position())
        self.click_world(x, z)

    def mouseDoubleClickEvent(self, event):        # noqa: N802 (Qt override)
        if event.button() == Qt.MouseButton.LeftButton:
            x, z = self.widget_to_world(event.position())
            if self.double_click_world(x, z):
                event.accept()
                return
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):             # noqa: N802 (Qt override)
        if self._pending:                          # right-click abandons the outline mid-draw
            self.clear_pending()
            self.note.emit("outline abandoned")
            event.accept()
            return
        x, z = self.widget_to_world(event.pos())
        if self._mode == "doors":
            di = self._pick_door(x, z)
            if di is not None:
                self._door_menu(di, event.globalPos())
                event.accept()
                return
            return super().contextMenuEvent(event)
        hit = self._pick_vertex(x, z)
        ri = hit[0] if hit is not None else self._pick_room(x, z)
        if ri is None:
            return super().contextMenuEvent(event)
        self._room_menu(ri, event.globalPos())
        event.accept()

    # -- the two menu SEAMS (a popup the fences would have to click is not a seam) --
    def _room_menu(self, ri, global_pos):
        from PySide6.QtWidgets import QMenu
        name = self._rooms[ri]["name"] if 0 <= ri < len(self._rooms) else f"room {ri}"
        menu = QMenu(self)
        ren = menu.addAction("Rename…")
        ent = menu.addAction(f"Make {name} the entry room")
        ent.setEnabled(name != self._entry)
        rm = menu.addAction(f"Delete {name}")
        act = menu.exec(global_pos)
        if act is ren:
            self.room_rename.emit(ri)
        elif act is ent:
            self.room_entry.emit(ri)
        elif act is rm:
            self.room_deleted.emit(ri)

    def _door_menu(self, di, global_pos):
        from PySide6.QtWidgets import QMenu
        d = self._doors[di] if 0 <= di < len(self._doors) else {}
        menu = QMenu(self)
        rm = menu.addAction(f"Delete the {d.get('a')}–{d.get('b')} door")
        act = menu.exec(global_pos)
        if act is rm:
            self.door_deleted.emit(di)

    # ------------------------------------------------------------------ view grammar
    def fit(self):
        # DRAW FIRST. The scene rect is derived from the geometry, so measuring before the redraw
        # fits the PREVIOUS plan's box -- and the snap showed exactly that: three rooms sitting in
        # a 120px cluster inside a 877x304 viewport, fitted against a stale rect.
        self._draw()
        r = self._scene.sceneRect()
        if r.isEmpty():
            return
        vw, vh = max(1, self.viewport().width()), max(1, self.viewport().height())
        z = min(vw / max(1.0, r.width()), vh / max(1.0, r.height())) * 0.92
        z = max(_ZOOM_MIN, min(3.0, z))
        self.resetTransform()
        self.scale(z, z)
        self._zoom = z
        self.centerOn(r.center())
        self._draw()                               # ...and again: the labels are zoom-dependent

    # ------------------------------------------------------------------ drawing
    def _fixed(self, item):
        """Screen-fixed chart furniture (labels, corner handles) — readable at any zoom."""
        item.setFlag(item.GraphicsItemFlag.ItemIgnoresTransformations)
        return item

    def _anchor(self, x, z):
        """A zero-size, zoom-immune anchor at a world point: its CHILDREN live in screen px."""
        sx, sy = self.world_to_scene(x, z)
        a = self._scene.addRect(QRectF(0, 0, 0, 0), QPen(Qt.PenStyle.NoPen))
        a.setPos(sx, sy)
        return self._fixed(a)

    def _child(self, item, anchor):
        """Adopt a SCENE-CREATED item as ``anchor``'s child. THE GC-CHILD LAW: constructing an
        item WITH a parent makes it Python-owned to shiboken, so the wrapper's GC deletes the
        C++ child under a live scene and its finalizer double-frees after ``scene.clear()``.
        ``addX`` + ``setParentItem`` keeps ownership C++-side; ``_kids`` is the belt."""
        item.setParentItem(anchor)
        self._kids.append(item)
        return item

    def _label(self, text, x, z, *, dx=6, dy=-16, color=None, bold=False, pt=8, centre=False):
        """A screen-px text label anchored at a world point.

        ``centre`` shifts it left by HALF ITS OWN measured width, which is not a nicety: with a
        fixed left offset a room name ran right out of its own polygon and collided with its
        neighbour's (the first snap showed ``ROOM1 (entry`` overprinting ``ROOM2`` on the shared
        wall). A plan is a chart of adjacent boxes, so every label has to stay inside its box.

        ★ AND THEN IT CLEARS THE VIEWPORT CHIPS. This is the ONE seam all five label tiers funnel
        through, which is why the screen-space clearance lives here and not at any call site —
        see the module note above :func:`label_offsets` for the measurement and the reasoning."""
        a = self._anchor(x, z)
        t = self._child(self._scene.addSimpleText(text), a)
        font = self._font(pt, bold)
        t.setFont(font)
        t.setBrush(QBrush(QColor(color or self.pal["muted"])))
        t.setPos(*self._chip_clear(x, z, text, font, t.boundingRect(), dx, dy, centre))
        return a

    @staticmethod
    def _ink_box(text, font, br):
        """``(x, y, w, h)``: the ink Qt ACTUALLY PAINTS inside a text item's ``boundingRect``.

        ``tightBoundingRect`` is baseline-relative and ``addSimpleText`` puts the baseline one
        ascent below the box top, so that is the shift. Clamped back into ``br`` because a tight
        box may reach past it (an accent, a glyph with a deep descender), and falling back to the
        whole box when a string measures to nothing keeps an empty label judged, never skipped."""
        from PySide6.QtGui import QFontMetricsF
        fm = QFontMetricsF(font)
        tb = fm.tightBoundingRect(text)
        box = QRectF(tb.x(), fm.ascent() + tb.y(), tb.width(), tb.height()).intersected(br)
        if box.isEmpty():
            box = br
        return (box.x(), box.y(), box.width(), box.height())

    def _chip_rects(self):
        """The screen-fixed chips as viewport-px rects (they are the viewport's own children).

        ``isVisibleTo`` and not ``isVisible``: a canvas that has never been SHOWN reports every
        child invisible, which would make the clearance — and any fence driving it — quietly
        vacuous on exactly the headless path the suite runs on."""
        vp = self.viewport()
        out = []
        for lab in (self._hint, self._compass, self._coords):
            if lab.isVisibleTo(vp):
                g = lab.geometry()
                out.append((float(g.x()), float(g.y()), float(g.width()), float(g.height())))
        return out

    def _chip_clear(self, x, z, text, font, br, dx, dy, centre):
        """A label's offset, mirrored off a viewport chip when the authored one lands on one."""
        offs = label_offsets(dx, dy, br.width(), br.height(), centre=centre)
        vp = self.viewport()
        if vp.width() <= 40 or vp.height() <= 40:
            return offs[0]                         # no real viewport yet: the chips are not placed
        chips = self._chip_rects()
        if not chips:
            return offs[0]
        sx, sy = self.world_to_scene(x, z)
        # ``viewportTransform()``, not ``mapFromScene``: the latter returns an INTEGER QPoint, and
        # that half-pixel of rounding is enough to disagree with where Qt paints the glyphs. It
        # left a sub-pixel bite in the census at exactly one chart height — the label was judged
        # clear at a rounded anchor and painted 0.4px into the chip. Screen-space furniture is
        # anchored in FLOATS (the label ignores the view transform, so this maps the whole subtree).
        base = self.viewportTransform().map(QPointF(sx, sy))
        return clear_of_chips(offs, (float(base.x()), float(base.y())),
                              self._ink_box(text, font, br), chips,
                              viewport=(float(vp.width()), float(vp.height())))

    def _pen(self, color, width, *, dash=None, alpha=None):
        c = QColor(color)
        if alpha is not None:
            c.setAlpha(alpha)
        p = QPen(c, width)
        p.setCosmetic(True)                        # must survive fit zoom (the atlas lesson)
        if dash:
            p.setDashPattern(dash)
        return p

    def _scene_bounds(self):
        pts = []
        for ri in range(len(self._rooms)):
            pts += list(self._poly(ri))
        pts += self._pending
        for c in self._cands:
            pts += list(c["seg"])
        if not pts:
            h = _BARE_SPAN / 2.0
            return QRectF(-h * _WORLD, -h * _WORLD, _BARE_SPAN * _WORLD, _BARE_SPAN * _WORLD)
        x0, z0, x1, z1 = FP.bbox(pts)
        pad = max(240.0, 0.08 * max(x1 - x0, z1 - z0))
        a = self.world_to_scene(x0 - pad, z1 + pad)
        b = self.world_to_scene(x1 + pad, z0 - pad)
        return QRectF(a[0], a[1], b[0] - a[0], b[1] - a[1])

    def _draw(self):
        sc = self._scene
        self._kids = []                            # the old scene's children die WITH the clear
        sc.clear()
        sc.setSceneRect(self._scene_bounds())
        self._draw_origin()
        for ri, room in enumerate(self._rooms):
            self._draw_room(ri, room)
        if self._mode == "doors":
            self._draw_candidates()
        self._draw_doors()
        if self._mode == "rooms":
            for ri in range(len(self._rooms)):     # handles TOPMOST (the behaviordoc law)
                self._draw_handles(ri)
        self._draw_pending()

    def _draw_origin(self):
        """The plan frame's origin — a chart with no fixed mark cannot be read at all."""
        pen = self._pen(self.pal["border"], 1.0, dash=[3, 5])
        r = self._scene.sceneRect()
        ox, oy = self.world_to_scene(0, 0)
        if r.left() <= ox <= r.right():
            self._scene.addLine(ox, r.top(), ox, r.bottom(), pen)
        if r.top() <= oy <= r.bottom():
            self._scene.addLine(r.left(), oy, r.right(), oy, pen)

    def _room_ink(self, name):
        """``(stroke colour, glyph)`` for a room's state. THE COLOUR IS IN THE STROKE, NEVER IN
        THE TEXT — see :data:`_FILL_ALPHA` and :meth:`_ink_on_fill`."""
        if name in self._bad_rooms:
            return self.pal["error"], "✕ "
        if name in self._warn_rooms:
            return self.pal["warn"], "! "
        return self.pal["accent"], ""

    def _draw_room(self, ri, room):
        poly = self._poly(ri)
        if len(poly) < 2:
            if poly:
                self._label(room["name"] or f"room {ri}", poly[0][0], poly[0][1],
                            color=self.pal["muted"])
            return
        ink, glyph = self._room_ink(room["name"])
        width = 3.0 if glyph == "✕ " else (2.6 if glyph else 2.0)   # state also in the STROKE
        qp = QPolygonF([QPointF(*self.world_to_scene(x, z)) for x, z in poly])
        item = self._scene.addPolygon(qp, self._pen(ink, width),
                                      QBrush(self._fill(ink, _FILL_ALPHA)))
        item.setZValue(-5)
        x0, z0, x1, z1 = FP.bbox(poly)
        cx, cz = (x0 + x1) / 2.0, (z0 + z1) / 2.0
        # A label is SCREEN px on a room that is not: zoomed out far enough, two neighbours'
        # footprints overprint into unreadable mush (measured on the first snap). So each tier
        # only draws while the room is wide enough on screen to hold THAT TIER'S OWN STRING --
        # measured, never a magic px threshold. The thresholds used to be 60/96/100, and the
        # moment the state glyph was prepended ('✕ ROOM1' is ~14px wider than 'ROOM1') a 68px-wide
        # room at CALIBRE 125 overprinted its neighbour again. A number that has to be re-tuned
        # every time the string changes is not a fence, it is a coincidence.
        wide = (x1 - x0) * _WORLD * self._zoom
        name = glyph + (room["name"] or f"room {ri}")
        named = self._fits(name, wide, pt=9, bold=True)
        if named:
            self._label(name, cx, cz, dy=-9, color=self.pal["text"], bold=True, pt=9, centre=True)
        metrics = f"{int(round(x1 - x0))} × {int(round(z1 - z0))}u"
        if self._fits(metrics, wide):
            self._label(metrics, cx, cz, dy=5, color=self.pal["muted"], centre=True)
        # ...and the tiers below the name are gated on the NAME, because 'entry' is short enough to
        # fit almost anywhere: without this, a room too narrow for its own name still wore a bare
        # 'entry' and read as a box labelled nothing else (snap-caught at light/125).
        if named and room["name"] and room["name"] == self._entry and self._fits("entry", wide):
            # Its OWN tier. On the name it pushed the widest label out of the room; appended to
            # the metrics it overflowed a 102px-wide room by ~8px (both measured on a snap).
            self._label("entry", cx, cz, dy=19, color=self.pal["muted"], centre=True)

    def _fits(self, text, room_px, *, pt=8, bold=False):
        """Does ``text`` fit inside a room that is ``room_px`` wide on screen, in the LIVE font?"""
        from PySide6.QtGui import QFontMetricsF
        return QFontMetricsF(self._font(pt, bold)).horizontalAdvance(text) + 8 <= room_px

    @staticmethod
    def _fill(color, alpha):
        c = QColor(color)
        c.setAlpha(alpha)
        return c

    def _draw_handles(self, ri):
        poly = self._poly(ri)
        d = self._drag
        for vi, (x, z) in enumerate(poly):
            a = self._anchor(x, z)
            r = _HANDLE_R + (2 if d and d["kind"] == "vert" and d["ri"] == ri and d["vi"] == vi
                             else 0)
            dot = self._child(self._scene.addEllipse(-r, -r, 2 * r, 2 * r), a)
            dot.setPen(self._pen(self.pal["text"], 1.4))
            dot.setBrush(QBrush(QColor(self.pal["surface"])))

    @staticmethod
    def _along(seg, t):
        """A point ``t`` of the way along ``seg``. Wall labels sit OFF the midpoint (t != 0.5) on
        purpose: a door lies on the boundary between two rooms whose own labels sit at their
        centres, which for an axis-aligned pair is the same row — measured as a three-way
        overprint in the first snap."""
        (ax, az), (bx, bz) = seg
        return (ax + (bx - ax) * t, az + (bz - az) * t)

    def _draw_candidates(self):
        for c in self._cands:
            (ax, az), (bx, bz) = c["seg"]
            p0, p1 = self.world_to_scene(ax, az), self.world_to_scene(bx, bz)
            self._scene.addLine(p0[0], p0[1], p1[0], p1[1],
                                self._pen(self.pal["success"], 5.0, dash=[4, 3]))
            if c["length"] * _WORLD * self._zoom < 70:
                continue                           # too small on screen to label without mush
            # OFF the strip and off its END, for the same reason the door label is (below): a
            # centred label on a 5px dashed strip is struck through by it, and on a shared wall it
            # ALSO crosses the neighbouring room's own 2px outline. Snap-measured at 100%: the
            # strip cut the baseline of '1200u shared wall -- click for a door' and ROOM3's west
            # wall ran through the 'e'. Offsetting is geometry; raising z is not (the fix that did
            # not work for the door label).
            m = self._along(c["seg"], 1.0)
            self._label(f"{int(round(c['length']))}u shared wall — click for a door",
                        m[0], m[1], dx=10, dy=-20, color=self.pal["text"])

    def _draw_doors(self):
        for i, dr in enumerate(self._doors):
            seg = _poly_pts(dr.get("seg") or ())
            if len(seg) != 2:
                continue
            bad = i in self._bad_doors
            ink = self.pal["error"] if bad else self.pal["accent"]
            width = 7.0 if i == self._sel_door else 5.0
            (ax, az), (bx, bz) = seg
            p0, p1 = self.world_to_scene(ax, az), self.world_to_scene(bx, bz)
            line = self._scene.addLine(p0[0], p0[1], p1[0], p1[1], self._pen(ink, width))
            line.setZValue(4)
            if math.hypot(bx - ax, bz - az) * _WORLD * self._zoom < 70:
                continue                           # too small on screen to label without mush
            m = self._along(seg, 0.15)              # clear of BOTH rooms' centre label stacks
            head = ("✕ " if bad else "") + f"{dr.get('a')}↔{dr.get('b')}"
            if not dr.get("two_way", True):
                head = f"{dr.get('a')}→{dr.get('b')} (one way)"
            head += f" · {int(round(float(dr.get('depth') or FP.DEPTH_DEFAULT)))}u deep"
            if i == self._sel_door:
                head += " · selected"
            # OFF the strip, not merely above it. Centred on the wall, the label's middle glyph
            # lands ON 5-7px of solid door ink -- '250u deep' read as '50u deep' in the snap even
            # with the label's z raised above the line's. Starting it clear of the strip is
            # geometry rather than stacking order, so nothing can re-cover it.
            # ...and the ink is `text`, not the door's own colour: a door label lands on a room's
            # wash as often as on the bare canvas (accent-on-accent@20 measures 3.6:1 on dark and
            # 2.2:1 on nord). The strip carries the colour; the glyph carries the refusal.
            lab = self._label(head, m[0], m[1], dx=10, dy=-14, color=self.pal["text"],
                              bold=(i == self._sel_door))
            lab.setZValue(6)

    def _draw_pending(self):
        if not self._pending:
            return
        pen = self._pen(self.pal["accent"], 2.0)
        pts = self._pending
        for a, b in zip(pts, pts[1:]):
            p0, p1 = self.world_to_scene(*a), self.world_to_scene(*b)
            self._scene.addLine(p0[0], p0[1], p1[0], p1[1], pen)
        if self._hover is not None:
            p0 = self.world_to_scene(*pts[-1])
            p1 = self.world_to_scene(*self._hover)
            self._scene.addLine(p0[0], p0[1], p1[0], p1[1],
                                self._pen(self.pal["accent"], 1.6, dash=[5, 4]))
            if len(pts) >= 3:                      # ...and the closing leg, so the shape is legible
                p2 = self.world_to_scene(*pts[0])
                self._scene.addLine(p1[0], p1[1], p2[0], p2[1],
                                    self._pen(self.pal["accent"], 1.2, dash=[2, 5]))
        for i, (x, z) in enumerate(pts):
            a = self._anchor(x, z)
            r = _HANDLE_R + (2 if i == 0 else 0)
            dot = self._child(self._scene.addEllipse(-r, -r, 2 * r, 2 * r), a)
            dot.setPen(self._pen(self.pal["accent"], 1.6))
            dot.setBrush(QBrush(QColor(self.pal["accent"] if i == 0 else self.pal["surface"])))
        self._label(f"{len(pts)} corner{'' if len(pts) == 1 else 's'}"
                    + (" — click the big dot to close" if len(pts) >= 3 else ""),
                    pts[0][0], pts[0][1], dy=-20, color=self.pal["text"])


class FloorplanDoc(QWidget):
    """The Floorplan tab: draw rooms, declare doors, Compose a wired dungeon.

    ``run`` = ``shell.run_job``; ``problems`` = ``shell._show_problems`` (the gate refusals go
    to the shared Problems panel, not only to this tab's own list); ``on_composed(campaign_toml)``
    fires after a clean Compose so the shell can open the result as a live campaign.
    """

    _judged = Signal(object)               # (gen, composed|None, errors, warnings) worker -> GUI

    def __init__(self, palette, kit_root, *, run, problems=None, scale=100, on_composed=None):
        super().__init__()
        self.pal = palette
        self.kit = Path(kit_root)                     # `-m ff9mapkit` cwd (this checkout's package)
        self._run = run
        self._problems = problems
        self.on_composed = on_composed
        self._session = {"rooms": [], "doors": [], "entry": None}
        self._history = []                            # doc-LOCAL undo (see the module docstring)
        self._sel_door = None
        self._last_gesture = None                     # coalesces a depth-editing burst into one step
        self._project = None                          # {"out": str} after the first Compose
        self._stamped = True                          # False = gestures since the last Compose
        self._gen = 0                                 # judge generation: a stale verdict never paints
        self._pending_judge = False
        self._verdict = None                          # (composed|None, errors, warnings)
        self._id_base_cache = None                    # .ff9deploy.toml, read on FIRST USE only
        self._id_base_read = False
        self._note, self._note_state = "", ""         # the last gesture's own line, re-painted
        self._polished = False                        # see showEvent: measure AFTER polish

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 10)
        root.setSpacing(6)
        # NO standing prose at all, not even one line. THE CHART IS THE PRIMARY SURFACE and at
        # CALIBRE 150 it had 134px of a 556px document: measured, the note cost 28px of that and
        # said nothing the status line ('Draw a room: click its corners...') and the two ToolStrip
        # tooltips do not already say at the moment they are needed. Prose that repeats a live
        # teach is not information, it is a floor under the instrument.
        crown, _ = widgets.nameplate("", "Floorplan")
        root.addWidget(crown)

        # -- the tools row: the click semantics, the Doors cluster, the gesture verbs --
        row = QHBoxLayout()
        row.setSpacing(8)
        self.tools = widgets.ToolStrip(
            [("rooms", "Rooms", "Draw a room: click its corners in order, then click the first "
                                "corner again (or double-click) to close it. Drag a corner to "
                                "move it, drag the middle to move the whole room, right-click "
                                "to rename or delete."),
             ("doors", "Doors", "Every wall two rooms SHARE is offered as a highlighted "
                                "segment — click one to declare a door. Click a door to select "
                                "it, right-click to delete it.")])
        self.tools.changed.connect(self._on_tool)
        row.addWidget(self.tools)
        self.depth_label = QLabel("Door depth")
        row.addWidget(self.depth_label)
        self.depth = QSpinBox()
        # NOT clamped at floorplan.DEPTH_MIN, deliberately. THE DEFAULT-VALUE LAW's second half:
        # the core REFUSES a strip shallower than 2*R_WALK (the standable window would be a
        # sliver), so a too-shallow value must reach the gate and be REFUSED OUT LOUD -- silently
        # clamping it to a legal number is exactly the quietly-plausible value the law forbids.
        self.depth.setRange(1, 4000)
        self.depth.setSingleStep(10)
        self.depth.setValue(int(FP.DEPTH_DEFAULT))
        self.depth.setSuffix(" u")
        self.depth.setAccessibleName("Door strip depth")
        self.depth.setToolTip(
            f"How far into each room the door's trigger strip reaches. {FP.DEPTH_DEFAULT:g}u is "
            f"the default and {FP.DEPTH_WARN:g}u is the in-game-proven floor; under "
            f"{FP.DEPTH_MIN:g}u the composer refuses it. Edits the selected door, and sets the "
            f"depth for the next one you declare.")
        self.depth_label.setBuddy(self.depth)
        self.depth.valueChanged.connect(self._on_depth)
        row.addWidget(self.depth)
        # ElideLabel, not a bare QLabel: a status word in a FIXED row must yield, never widen it
        # (the tick-stepper's own lesson — a plain QLabel demands its whole rendered string).
        self.sel_label = widgets.ElideLabel("", "muted")
        row.addWidget(self.sel_label, 1)
        row.addStretch(1)                          # ...and a REAL spacer: with the elide label
        #                                            hidden (Rooms mode) its stretch goes with it,
        #                                            and Undo/Clear then stretched half the row
        #                                            each at CALIBRE 150 (snap-caught)
        self.undo_btn = QPushButton("Undo")
        self.undo_btn.setAccessibleName("Undo the last floorplan gesture")
        self.undo_btn.setToolTip("Take back the last gesture. Undo is local to this tab and "
                                 "walks the WHOLE plan back one step, so a door — which spans "
                                 "two rooms — can never be half-undone.")
        self.undo_btn.clicked.connect(self.on_undo)
        row.addWidget(self.undo_btn)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setAccessibleName("Clear every room and door")
        self.clear_btn.setToolTip("Remove every room and door (one Undo brings them back).")
        self.clear_btn.clicked.connect(self.on_clear)
        row.addWidget(self.clear_btn)
        root.addLayout(row)

        self.canvas = PlanCanvas(palette, scale=scale)
        self.canvas.room_drawn.connect(self._on_room_drawn)
        self.canvas.room_reshaped.connect(self._on_room_reshaped)
        self.canvas.room_rename.connect(self._on_room_rename)
        self.canvas.room_entry.connect(self._on_room_entry)
        self.canvas.room_deleted.connect(self._on_room_deleted)
        self.canvas.door_declared.connect(self._on_door_declared)
        self.canvas.door_selected.connect(self._on_door_selected)
        self.canvas.door_deleted.connect(self._on_door_deleted)
        self.canvas.note.connect(self._on_note)
        root.addWidget(self.canvas, 1)

        # -- the envelope: what the composed dungeon is called, and where its ids live.
        # THE ROUND-7 LAW (an oversubscribed row shaves EVERY control) is why this is TWO rows.
        # Measured at CALIBRE 150 in a 905px document: the one-row version demanded 1096px, so Qt
        # shaved every member -- `FF9CustomMap` rendered as `FF9CustomMa` with the p cut in half
        # (5x crop), and the band caption, squeezed into a 164px column, wrapped to THREE lines and
        # put 72px under the chart all by itself. Splitting drops the widest row to ~735px, so no
        # box is shaved and the caption is one line: 48px of the 124px envelope came back.
        row = QHBoxLayout()
        row.setSpacing(8)
        self.open_btn = QPushButton("Open…")
        self.open_btn.setAccessibleName("Open a floorplan")
        self.open_btn.setToolTip("Reopen a composed dungeon's floorplan.json as an editable "
                                 "session (the sidecar round-trip).")
        self.open_btn.clicked.connect(self.on_open)
        row.addWidget(self.open_btn)
        nl = QLabel("Dungeon")
        row.addWidget(nl)
        self.name_box = QLineEdit("DUNGEON")
        self.name_box.setAccessibleName("Dungeon name")
        self.name_box.setToolTip("The composed campaign's name (its campaign.toml).")
        nl.setBuddy(self.name_box)
        self.name_box.textChanged.connect(lambda _t: self._touch(judge=True))
        #                                  judge=True: the name becomes a FOLDER, and _name_problem
        #                                  is one of the gates -- see there
        row.addWidget(self.name_box)
        ml = QLabel("Mod")
        row.addWidget(ml)
        self.mod_box = QLineEdit("FF9CustomMap")
        self.mod_box.setCursorPosition(0)          # the snap showed "CustomMap": a box that opens
        #                                            scrolled to the CARET hides its own default
        self.mod_box.setAccessibleName("Mod folder")
        self.mod_box.setToolTip("The Memoria mod folder this dungeon deploys into — leave as "
                                "FF9CustomMap unless you keep separate mod stacks.")
        ml.setBuddy(self.mod_box)
        self.mod_box.textChanged.connect(lambda _t: self._touch())
        row.addWidget(self.mod_box)
        row.addStretch(1)
        root.addLayout(row)

        # -- the id row. THE ONE BAND LESSON, taught by the shared helper (never a private copy of
        # the numbers), and on its own row so the caption gets its one line.
        # The box starts EMPTY: a minted id must be real or loudly refused, and this tab cannot
        # know a real one at construction (reading .ff9deploy.toml then would be a startup disk
        # touch). It resolves on FIRST USE, and refuses out loud if nothing real is available.
        row = QHBoxLayout()
        row.setSpacing(8)
        idform = QFormLayout()
        idform.setContentsMargins(0, 0, 0, 0)
        idform.setSpacing(2)
        self.id_box = widgets.id_field(idform, "First id", value="", placeholder="auto")
        self.id_box.setAccessibleName("First field id")
        self.id_box.setToolTip("The first room's field id; the rest follow consecutively. Empty "
                               "reads this worktree's own .ff9deploy.toml `campaign_id_base` — "
                               "and refuses out loud if there is none, because a guessed id "
                               "collides in the GLOBAL EventDB.")
        self.id_box.textChanged.connect(lambda _t: self._touch(judge=True))
        row.addLayout(idform, 1)                   # the stretch: the band caption needs the width
        self.compose_btn = QPushButton("Compose…")
        self.compose_btn.setObjectName("accent")
        self.compose_btn.setAccessibleName("Compose the dungeon")
        self.compose_btn.clicked.connect(self.on_compose)
        row.addWidget(self.compose_btn, 0, Qt.AlignmentFlag.AlignTop)
        root.addLayout(row)

        # ONE LINE, and it ELIDES. A wrapping status took a second line at every scale and a third
        # at 150 — height the chart pays for. So it is an ElideLabel with the VERDICT first and the
        # gesture echo last: an elide then loses the echo, never the judgement, and the whole
        # string survives in the tooltip.
        self.status = widgets.ElideLabel("", "muted")
        root.addWidget(self.status)
        # The findings list is HIDDEN while the plan is clean and sized to its real row count
        # otherwise. THE CHART IS THE PRIMARY SURFACE and the snap measured what a standing box
        # costs it: an always-visible 5-row well left the canvas 221px of an 850px window. The
        # clean-state teach lives in the status line instead (TraceDoc's own choice, same reason).
        self.plist = widgets.PlaceholderListWidget("", palette["muted"])
        self.plist.setAccessibleName("Floorplan gate findings")
        self.plist.setToolTip("What the composer says about the plan as it stands. Compose stays "
                              "off while any of these is an error.")
        self.plist.setWordWrap(True)               # a clipped gate message is half a message; the
        #                                            snap showed the tail of a 150-char one cut off
        self.plist.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        #                                          ...and wrap only happens when the row CANNOT
        #                                          scroll sideways: with the bar allowed, the snap
        #                                          at 150 showed one clipped line and a scrollbar
        self.plist.setVerticalScrollMode(self.plist.ScrollMode.ScrollPerPixel)
        #                                          per PIXEL, so a row taller than the cap can be
        #                                          read to its end instead of being cut (see
        #                                          _fit_plist -- sizeHintForRow reported 46 for an
        #                                          84px row and the range stayed 0..0)
        self.plist.hide()
        root.addWidget(self.plist)
        self._judged.connect(self._finish_judge)
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(140)               # coalesce a burst of gestures into one judge
        self._debounce.timeout.connect(lambda: self.judge_now())
        self._apply_scale(scale)
        self._refresh(judge=False)

    # ================================================================== the document
    def plan(self):
        """The live session as the ``floorplan.json`` shape ``floorplan.compose`` consumes."""
        p = {"version": 1,
             "name": self.name_box.text().strip() or "DUNGEON",
             "mod_folder": self.mod_box.text().strip() or "FF9CustomMap",
             "rooms": [{"name": r["name"], "poly": [[int(round(x)), int(round(z))]
                                                    for x, z in r["poly"]]}
                       for r in self._session["rooms"]],
             "doors": [{"a": d["a"], "b": d["b"],
                        "seg": [[int(round(x)), int(round(z))] for x, z in d["seg"]],
                        "depth": float(d.get("depth") or FP.DEPTH_DEFAULT),
                        "two_way": bool(d.get("two_way", True))}
                       for d in self._session["doors"]]}
        if self._session.get("entry"):
            p["entry"] = self._session["entry"]
        try:
            base = self.id_base()
        except ValueError:
            base = None            # an out-of-band box is reported by _id_problem, not raised at
            #                        the judge: a half-typed id must not take the whole gate down
        if base is not None:
            p["id_base"] = int(base)
        return p

    def _envelope_problems(self):
        """The gates on the values that live OUTSIDE the geometry (the name, the id base).

        ONE list, spent by BOTH the live paint and ``on_compose``. It was two: the paint added the
        id finding, ``on_compose`` re-derived its own id check and knew nothing about the name — so
        a refusal the chart was already showing did not stop the click. A gate is only a gate at
        every call site that can pass it."""
        return [w for w in (self._name_problem(), self._id_problem()) if w]

    def _name_problem(self):
        """The dungeon name's own gate finding, or None.

        The name is not decoration: ``on_compose`` writes the sidecar to
        ``<chosen parent>/<name>.lower()``, so it IS a directory name — a typed ``../old`` would
        have written the plan outside the folder the author picked, silently. Room names are
        already validated through ``campaign._validate_member_name`` (the one owner of that rule);
        this spends the same validator on the one other string that becomes a path."""
        from .. import campaign as C
        name = self.name_box.text().strip()
        if not name:
            return None                            # falls back to DUNGEON, which is real
        try:
            C._validate_member_name(name)
        except C.CampaignError as e:
            return f"dungeon name {name!r} cannot be a folder: {e}"
        return None

    # ONE voice: the listed gate finding and the Compose refusal are the same sentence.
    _NO_ID = ("No first field id: type one in the box, or add `campaign_id_base` to this "
              "worktree's .ff9deploy.toml. A guessed id collides in the GLOBAL EventDB, which is "
              "the classic null-.eb black screen.")

    def _id_problem(self):
        """The id box's own gate finding, or None.

        It rides with ``compose``'s problems rather than being raised out of :meth:`plan`, so a
        half-typed id shows up as one more listed problem (and holds Compose off) instead of
        taking the whole live judge down with a traceback.

        ★ AN UNRESOLVED id base IS ONE OF THOSE PROBLEMS. It was not, and THE DEFAULT-VALUE LAW
        caught it on a clean checkout (``.ff9deploy.toml`` is gitignored, so 'no pin' is every new
        user's first run): ``plan()`` simply omitted ``id_base``, ``floorplan.compose`` fell back
        to its own default of 30000, and the tab then said **"✓ composes: 1 field(s), ids
        30000-30000"** with **Compose ENABLED** — after which the click refused and did nothing.
        A live button that promises ids the tab will not mint is a lie twice over. The refusal now
        arrives before the click, listed, with Compose off."""
        txt = self.id_box.text().strip()
        if not txt:
            if not self._session["rooms"]:
                return None                        # nothing to mint ids FOR, and consulting the
                #                                    pin here would make the lazy .ff9deploy.toml
                #                                    read a CONSTRUCTION disk touch (its own fence
                #                                    caught exactly that). Compose is already off
                #                                    with 'draw at least one room first'.
            return None if self.id_base() is not None else self._NO_ID
        try:
            self.id_base()
        except ValueError as e:
            return str(e)
        return None

    def id_base(self):
        """The first field id, resolved LAZILY and never invented.

        Order: the box (validated by ``pack.check_custom_id`` — the shared band voice), then this
        worktree's own ``.ff9deploy.toml`` ``campaign_id_base``. If neither answers, this returns
        None and Compose REFUSES: THE DEFAULT-VALUE LAW forbids minting a plausible-looking id,
        and an id collision in the GLOBAL EventDB is the classic null-``.eb`` black screen.
        Raises ``ValueError`` when the box holds something out of band.
        """
        txt = self.id_box.text().strip()
        if txt:
            from .. import pack
            return pack.check_custom_id(txt, what="first field id")
        if not self._id_base_read:                    # the FIRST-USE disk touch, once per session
            self._id_base_read = True
            self._id_base_cache = self._read_deploy_id_base()
        return self._id_base_cache

    def deploy_pin_path(self):
        """This worktree's ``.ff9deploy.toml``, as ONE overridable seam.

        A test that reads the developer's real pin is a report on the developer — this repo's
        most-recurring test defect — and the pin is gitignored, so its very presence differs per
        machine. One accessor is what lets ``conftest``-style pinning aim at a tmp file instead of
        patching the reader and losing the reader's own coverage."""
        return self.kit.parent / ".ff9deploy.toml"

    def _read_deploy_id_base(self):
        import tomllib
        f = self.deploy_pin_path()
        try:
            if not f.is_file():
                return None
            d = tomllib.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        v = d.get("campaign_id_base")
        try:
            return int(v) if v is not None else None
        except (TypeError, ValueError):
            return None

    def _fresh_room_name(self):
        """``ROOM1``, ``ROOM2``, … — REAL, not a placeholder: a legal ``campaign`` member name
        (it becomes an on-disk member dir and the field's own name), unique in the plan, and it
        renders and behaves in-game with zero further edits."""
        taken = {r["name"] for r in self._session["rooms"]}
        n = 1
        while f"ROOM{n}" in taken:
            n += 1
        return f"ROOM{n}"

    @staticmethod
    def check_room_name(name, taken):
        """None if ``name`` is a legal, free room name, else why not.

        The path-safety half is ``campaign._validate_member_name``, the ONE owner — a member
        name becomes a subdirectory and the key every edge/seam references, so a second copy of
        that rule here is a second chance to disagree with the writer that enforces it."""
        from .. import campaign as C
        name = str(name)
        try:
            C._validate_member_name(name)
        except C.CampaignError as e:
            return str(e)
        if name in set(taken):
            return f"another room is already called {name!r}"
        return None

    # ================================================================== undo (DOC-LOCAL)
    def _push_history(self, gesture=None):
        """One snapshot of the WHOLE geometry document per gesture.

        Doc-local on purpose — see the module docstring: ``shell._UndoRec`` is single-member, so
        a door edit (a gateway on one side, an arrival row on the other) could not be one shell
        undo step, and a half-undone pair is a gateway with no arrival. ``gesture`` coalesces a
        burst that is logically one edit (dragging a spin box) into a single step.
        """
        if gesture is not None and gesture == self._last_gesture and self._history:
            return
        self._last_gesture = gesture
        self._history.append(copy.deepcopy(self._session))
        del self._history[:-_HISTORY_CAP]
        self._stamped = False

    def on_undo(self):
        if not self._history:
            return
        self._session = self._history.pop()
        self._last_gesture = None
        self._sel_door = None
        self._stamped = False
        self._refresh("undone")

    def on_clear(self):
        if not (self._session["rooms"] or self._session["doors"]):
            return
        self._push_history()
        self._session = {"rooms": [], "doors": [], "entry": None}
        self._sel_door = None
        self._refresh("cleared — draw a room to begin")

    def _touch(self, *, judge=False):
        """An envelope edit (name / mod folder / id base) the composed project does not have.

        The boxes carry Qt's own per-field undo and are NOT in the history stack: the stack owns
        the geometry document, which is the only thing a canvas gesture can touch. ``judge`` is
        True for the two envelope values a gate reads: the id base (G5) and the dungeon NAME,
        which becomes the composed folder (see :meth:`_name_problem`)."""
        self._last_gesture = None
        if self._project is not None:
            self._stamped = False
        self._refresh(judge=judge)

    # ================================================================== the tool strip
    def _on_tool(self, key):
        self.canvas.set_mode(key)
        self._refresh(judge=False)

    def _on_note(self, msg):
        self._refresh(msg, judge=False)

    # ================================================================== room gestures
    def _on_room_drawn(self, poly):
        why = FP.polygon_problem(_poly_pts(poly))
        self._push_history()
        name = self._fresh_room_name()
        self._session["rooms"].append({"name": name,
                                       "poly": [(int(round(x)), int(round(z))) for x, z in poly]})
        if not self._session.get("entry"):
            self._session["entry"] = name           # the first room drawn IS the way in
        self._refresh(f"{name} drawn — {len(poly)} corners"
                      + (f" · ⚠ {why}" if why else ""))

    def _on_room_reshaped(self, ri, poly):
        if not 0 <= ri < len(self._session["rooms"]):
            return
        self._push_history()
        self._session["rooms"][ri]["poly"] = [(int(round(x)), int(round(z))) for x, z in poly]
        self._refresh(f"{self._session['rooms'][ri]['name']} reshaped")

    def _on_room_rename(self, ri):
        if not 0 <= ri < len(self._session["rooms"]):
            return
        old = self._session["rooms"][ri]["name"]
        new = self._ask_room_name(old)
        if new is None or new.strip() == old:
            return
        new = new.strip()
        why = self.check_room_name(new, [r["name"] for i, r in enumerate(self._session["rooms"])
                                         if i != ri])
        if why:
            self._refresh(f"cannot rename {old} → {new!r}: {why}", "error")
            return
        self._push_history()
        self._session["rooms"][ri]["name"] = new
        for d in self._session["doors"]:            # a door names its rooms — retarget both ends
            if d["a"] == old:
                d["a"] = new
            if d["b"] == old:
                d["b"] = new
        if self._session.get("entry") == old:
            self._session["entry"] = new
        self._refresh(f"renamed {old} → {new}")

    def _on_room_entry(self, ri):
        if not 0 <= ri < len(self._session["rooms"]):
            return
        self._push_history()
        self._session["entry"] = self._session["rooms"][ri]["name"]
        self._refresh(f"{self._session['entry']} is the entry room — the composer warns about "
                      f"any room no chain of doors reaches from here")

    def _on_room_deleted(self, ri):
        if not 0 <= ri < len(self._session["rooms"]):
            return
        self._push_history()
        name = self._session["rooms"].pop(ri)["name"]
        # A door to a room that no longer exists is not a door. Dropping both ends here is what
        # keeps the pair atomic -- G3's reciprocity can only hold if the two sides live or die
        # together, and they are one undo step because the whole document is one snapshot.
        gone = [i for i, d in enumerate(self._session["doors"])
                if name in (d["a"], d["b"])]
        for i in reversed(gone):
            del self._session["doors"][i]
        if self._session.get("entry") == name:
            self._session["entry"] = (self._session["rooms"][0]["name"]
                                      if self._session["rooms"] else None)
        self._sel_door = None
        self._refresh(f"deleted {name}"
                      + (f" and its {len(gone)} door(s)" if gone else ""))

    # ================================================================== door gestures
    def _on_door_declared(self, cand):
        self._push_history()
        self._session["doors"].append({
            "a": cand["a"], "b": cand["b"],
            "seg": [(int(round(x)), int(round(z))) for x, z in cand["seg"]],
            "depth": float(self.depth.value()), "two_way": True})
        self._sel_door = len(self._session["doors"]) - 1
        self._refresh(f"declared a door between {cand['a']} and {cand['b']} "
                      f"({self.depth.value()}u deep)")

    def _on_door_selected(self, i):
        self._sel_door = None if i < 0 else int(i)
        if self._sel_door is not None and 0 <= self._sel_door < len(self._session["doors"]):
            d = self._session["doors"][self._sel_door]
            self.depth.blockSignals(True)           # showing a value is not editing it
            self.depth.setValue(int(round(float(d.get("depth") or FP.DEPTH_DEFAULT))))
            self.depth.blockSignals(False)
        self._last_gesture = None
        self._refresh(judge=False)

    def _on_door_deleted(self, i):
        if not 0 <= i < len(self._session["doors"]):
            return
        self._push_history()
        d = self._session["doors"].pop(i)
        self._sel_door = None
        self._refresh(f"deleted the {d['a']}–{d['b']} door")

    def _on_depth(self, value):
        i = self._sel_door
        if i is None or not 0 <= i < len(self._session["doors"]):
            self._refresh(judge=False)              # it is the depth for the NEXT door
            return
        self._push_history(gesture=("depth", i))    # one undo step per editing burst
        self._session["doors"][i]["depth"] = float(value)
        self._refresh(f"the {self._session['doors'][i]['a']}–"
                      f"{self._session['doors'][i]['b']} door is {value}u deep")

    # ================================================================== the live gate
    def judge_now(self, *, sync=False):
        """Run ``compose`` over the current plan. Default lane is a WORKER THREAD.

        It is not free — measured ~0.5s per room, dominated by ``standable``'s 8u grid sampling
        — so a three-room plan would freeze the GUI for a second and a half on every gesture.
        ``compose`` is pure Python with no Qt and no disk, so a thread is safe by construction.
        ``sync=True`` is the deterministic lane the fences, the snaps and Compose itself use.

        A generation counter drops a stale verdict (BehaviorDoc's sweep idiom): the plan a
        gesture changed is not the plan the in-flight worker was judging, and painting the old
        verdict would say a fixed problem is still there — or, worse, say a new one is not.
        """
        self._gen += 1
        gen = self._gen
        plan = self.plan()
        if not plan["rooms"]:
            self._pending_judge = False
            self._verdict = None
            self._paint_verdict()
            return
        self._pending_judge = True
        if sync:
            self._finish_judge((gen,) + self._judge_work(plan))
            return
        threading.Thread(target=self._judge_worker, args=(gen, plan), daemon=True).start()

    @staticmethod
    def _judge_work(plan):
        """``(composed|None, errors, warnings)`` — pure, so it is safe off the GUI thread."""
        try:
            c = FP.compose(plan)
        except FP.ComposeError as e:
            return (None, list(e.problems), [])
        except Exception as e:                     # noqa: BLE001 -- a half-drawn plan must never
            return (None, [f"the composer could not judge this plan: "   # crash the tab
                           f"{type(e).__name__}: {e}"], [])
        return (c, [], list(c.warnings))

    def _judge_worker(self, gen, plan):
        res = self._judge_work(plan)
        try:
            self._judged.emit((gen,) + res)
        except RuntimeError:                       # the doc died under the worker
            pass

    def _finish_judge(self, payload):
        gen, composed, errors, warnings = payload
        if gen != self._gen:
            return                                 # a stale verdict never paints
        self._pending_judge = False
        self._verdict = (composed, errors, warnings)
        self._paint_verdict()

    def _paint_verdict(self):
        """Feed the canvas + the findings list + the Compose gate from the last verdict."""
        rooms = self._session["rooms"]
        doors = self._session["doors"]
        names = [r["name"] for r in rooms]
        composed, errors, warnings = self._verdict or (None, [], [])
        env = self._envelope_problems()
        if env:
            errors = list(errors) + env
            composed = None
        bad_rooms, bad_doors, loose = attribute_problems(errors, names, doors)
        warn_rooms, _wd, _wl = attribute_problems(warnings, names, doors)
        self.canvas.set_plan(rooms, doors,
                            candidates=(candidate_doors(rooms, doors)
                                        if self.tools.current() == "doors" else ()),
                            bad_rooms=bad_rooms, warn_rooms=warn_rooms - bad_rooms,
                            bad_doors=bad_doors, entry=self._session.get("entry"),
                            selected_door=self._sel_door)
        self.plist.clear()
        for glyph, msg in ([("✕", p) for p in errors] + [("!", w) for w in warnings]):
            self.plist.addItem(f"{glyph}  {msg}")
            self.plist.item(self.plist.count() - 1).setToolTip(msg)
        if loose and errors:
            # Never swallowed: an unattributable problem paints no room, but it is still SAID.
            self.plist.addItem(f"·  {len(loose)} of these name no single room or door")
        self._fit_plist()
        ready = bool(rooms) and not errors and not self._pending_judge
        self.compose_btn.setEnabled(ready)
        if not rooms:
            tip = ("Draw at least one room first — click its corners on the chart, then close "
                   "the outline.")
        elif self._pending_judge:
            tip = "Checking the plan against every compose gate…"
        elif errors:
            tip = (f"{len(errors)} problem(s) would make this an illegal dungeon — they are "
                   f"listed below the chart. Compose stays off until they are fixed.")
        elif composed is not None:
            tip = (f"Write floorplan.json and run `ff9mapkit floorplan` on it: "
                   f"{len(composed.rooms)} field(s), ids "
                   f"{composed.rooms[0].field_id}-{composed.rooms[-1].field_id}.")
        else:
            tip = "Compose the plan into a wired dungeon."
        self.compose_btn.setToolTip(tip)
        self.compose_btn.setText("Recompose" if self._project else "Compose…")
        self._paint_status(composed, errors, warnings)

    def _paint_status(self, composed, errors, warnings):
        """One elided line: THE GESTURE NOTE LEADS, then the verdict, then the counts.

        The order is the design, because an ElideLabel drops its TAIL. The note is the freshest
        thing the author is owed — a refusal ("cannot rename … : no path separators", "No first
        field id") is a note, and burying it behind the standing verdict is how a refusal goes
        unread. The verdict can afford to trail: it is ALSO carried by the Compose button's
        enabled state and tooltip and by every row of the findings well, and the whole string
        survives in the tooltip and the accessible name (``ElideLabel.setText``).
        """
        note, state = self._note, self._note_state
        rooms = self._session["rooms"]
        head, tip = "", ""
        if not rooms:
            head = ("Draw a room: click its corners on the chart, then click the first corner "
                    "again to close it.")
        elif self._pending_judge:
            head = "checking the gates…"
        elif errors:
            head = (f"✕ {len(errors)} problem{'' if len(errors) == 1 else 's'} — see the list "
                    f"below")
            state = state or "error"
        elif composed is not None:
            ids = [r.field_id for r in composed.rooms]
            head = f"✓ composes: {len(composed.rooms)} field(s), ids {ids[0]}-{ids[-1]}"
            if warnings:
                head += f" · ! {len(warnings)} warning{'' if len(warnings) == 1 else 's'}"
                state = state or "warn"
            # the FULL per-room fit lives in the TOOLTIP: a six-room dungeon's distances would
            # take three lines of height off the chart
            tip = (f"entry {composed.entry}. Fitted camera per room: "
                   + ", ".join(f"{r.name} id {r.field_id}, distance {r.distance}u, "
                               f"pitch {r.pitch:g}, off_r {r.off_r}" for r in composed.rooms))
        if self._project and not self._stamped:
            head += " · ⚠ not composed yet — Recompose to update the project"
            state = state or "warn"
        counts = (f"{len(rooms)} room{'' if len(rooms) == 1 else 's'} · "
                  f"{len(self._session['doors'])} door"
                  f"{'' if len(self._session['doors']) == 1 else 's'}") if rooms else ""
        line = " · ".join(x for x in (note, head, counts) if x)
        self.status.setText(line)
        self.status.setToolTip(f"{line}\n\n{tip}" if tip else line)
        widgets.set_state(self.status, state)

    def _refresh(self, note="", state="", *, judge=True):
        """Repaint from the session. ``judge`` schedules the debounced compose re-run."""
        self._note, self._note_state = note, state
        cur = self.tools.current()
        self.depth_label.setVisible(cur == "doors")
        self.depth.setVisible(cur == "doors")
        self.sel_label.setVisible(cur == "doors")
        n = len(self._session["doors"])
        if cur == "doors":
            if self._sel_door is not None and 0 <= self._sel_door < n:
                d = self._session["doors"][self._sel_door]
                self.sel_label.setText(f"{d['a']}–{d['b']}")
            else:
                self.sel_label.setText("for the next door")
        self.undo_btn.setEnabled(bool(self._history))
        self.clear_btn.setEnabled(bool(self._session["rooms"] or self._session["doors"]))
        if judge:
            # THE GENERATION ADVANCES WHEN THE DOCUMENT CHANGES, not when the next judge starts.
            # Bumping it only inside judge_now was a real hole the fence caught: a worker launched
            # BEFORE this gesture still carried the current generation, so its verdict — computed
            # for the old plan — painted over the new one, naming a room that had just been
            # deleted. A gesture invalidates every verdict in flight, so it says so here.
            self._gen += 1
            self._verdict = None
            self._debounce.start()
            self._pending_judge = bool(self._session["rooms"])
        self._paint_verdict()

    # ================================================================== Open / Compose
    def on_open(self):
        path = self._ask_open()
        if not path:
            return
        try:
            self.load_plan(path)
        except Exception as e:                     # noqa: BLE001 -- a bad file must not kill the tab
            self._refresh(f"Could not open {Path(path).name}: {e}", "error", judge=False)

    def load_plan(self, path):
        """Read a ``floorplan.json`` back into an EDITABLE session (the round trip).

        Its folder becomes the project, so the next Compose goes straight in place — the same
        'set it up once' contract the Trace lane's ``.trace.json`` has."""
        data = FP.load_plan(path)
        rooms, doors = [], []
        for r in data.get("rooms") or []:
            poly = [(int(round(float(p[0]))), int(round(float(p[1]))))
                    for p in (r.get("poly") or [])]
            rooms.append({"name": str(r.get("name") or ""), "poly": poly})
        known = {r["name"] for r in rooms}
        for d in data.get("doors") or []:
            seg = [(int(round(float(p[0]))), int(round(float(p[1]))))
                   for p in (d.get("seg") or [])]
            if len(seg) != 2 or str(d.get("a")) not in known or str(d.get("b")) not in known:
                continue                           # a door with no rooms is not a door
            doors.append({"a": str(d["a"]), "b": str(d["b"]), "seg": seg,
                          "depth": float(d.get("depth") or FP.DEPTH_DEFAULT),
                          "two_way": bool(d.get("two_way", True))})
        self._session = {"rooms": rooms, "doors": doors,
                         "entry": (str(data["entry"]) if data.get("entry") in known else
                                   (rooms[0]["name"] if rooms else None))}
        self._history = []
        self._sel_door = None
        self.name_box.setText(str(data.get("name") or "DUNGEON"))
        self.mod_box.setText(str(data.get("mod_folder") or "FF9CustomMap"))
        if data.get("id_base"):
            self.id_box.setText(str(int(data["id_base"])))
        self._project = {"out": str(Path(path).parent)}
        self._stamped = True                       # the sidecar IS the project's state
        self.canvas.set_plan(rooms, doors, entry=self._session["entry"], refit=True)
        self._refresh(f"Reopened {Path(path).name} — Compose updates the project in place.")

    def on_compose(self):
        rooms = self._session["rooms"]
        if not rooms:
            self._refresh("Draw at least one room first.", "error", judge=False)
            return
        self.judge_now(sync=True)                  # never compose on a debounced stale verdict
        composed, errors, warnings = self._verdict or (None, ["the plan was not judged"], [])
        env = self._envelope_problems()            # the SAME gates the chart is already painting
        errors = list(errors) + env
        if errors:
            self._report(errors, warnings)
            # An envelope refusal LEADS the status line. It is the one the author can act on in one
            # keystroke ('type an id', 'take the slash out of the name'), and burying it behind a
            # count is how a refusal goes unread -- the same reasoning _paint_status is built on.
            self._refresh(env[0] if env else
                          f"{len(errors)} problem(s) — this plan cannot become a legal dungeon "
                          f"yet.", "error", judge=False)
            return
        if self.id_base() is None:                 # env cleared it; belt, not a second gate
            self._refresh(self._NO_ID, "error", judge=False)
            return
        if self._project is not None:
            out = Path(self._project["out"])
        else:
            parent = self._ask_out()
            if not parent:
                return
            out = Path(parent) / self.plan()["name"].lower()
        try:
            plan_path = FP.save_plan(self.plan(), out / FP.SIDECAR)
        except OSError as e:
            self._refresh(f"Could not write {out / FP.SIDECAR}: {e}", "error", judge=False)
            return
        # EXACTLY this argv: the verb reads name / ids / mod folder / rooms / doors FROM the json
        # and defaults --out to the plan file's own directory, so the GUI hands it ONE path and
        # nothing else. Any flag added here would be a second source of truth for the same value.
        argv = [sys.executable, "-m", "ff9mapkit", "floorplan", str(plan_path)]
        camp = out / "campaign.toml"
        started = self._run(
            argv, cwd=str(self.kit), subject="Floorplan → dungeon",
            ok_headline=f"{self.plan()['name']} composed → {out}",
            ok_next=(f"Build it: py -m ff9mapkit build-all {camp} — then deploy ONE ROOM AT A "
                     f"TIME with tools/deploy_field.py --id N (deploy-campaign --apply would "
                     f"rmtree the whole mod folder)."),
            fail_hint="See the Output panel — the composer prints every gate it refused on.",
            on_finished=lambda code: self._after_compose(code, camp))
        if started:
            self._project = {"out": str(out)}
            self._stamped = True
            self._refresh(f"Composing {self.plan()['name']} → {out} …", judge=False)

    def _after_compose(self, code, campaign_toml):
        """A clean run hands the composed dungeon to the shell, so its graph is visible at once
        (PLAN.md §5 call site 3 — ``open_campaign``, never a private opener)."""
        if code != 0:
            self._refresh("Compose failed — see the Output panel.", "error", judge=False)
            return
        if self.on_composed is not None and Path(campaign_toml).is_file():
            self.on_composed(campaign_toml)

    def _report(self, errors, warnings):
        """Push the gate findings at the shared Problems panel as well as this tab's list."""
        if self._problems is None:
            return
        from ..editor import feedback as fb
        self._problems(fb.classify(errors, warnings, subject="Floorplan",
                                   clean_headline="Floorplan — every gate clear"),
                       fb.problems(errors, warnings))

    # ================================================================== dialog seams
    def _ask_open(self):
        """Instance dialog behind a seam (a static execs in C++ past every test patch)."""
        start = self._project["out"] if self._project else str(Path.home())
        dlg = QFileDialog(self, "Open a floorplan.json", start)
        dlg.setFileMode(QFileDialog.FileMode.ExistingFile)
        dlg.setNameFilter("Floorplans (floorplan.json *.json)")
        if dlg.exec() != QFileDialog.DialogCode.Accepted:
            return None
        files = dlg.selectedFiles()
        return files[0] if files else None

    def _ask_out(self):
        base = (self.kit.parent if (self.kit / "pyproject.toml").is_file()
                else Path.home() / "Dream World IX")
        dlg = QFileDialog(self, "Where to put the composed dungeon", str(base))
        dlg.setFileMode(QFileDialog.FileMode.Directory)
        dlg.setOption(QFileDialog.Option.ShowDirsOnly, True)
        if dlg.exec() != QFileDialog.DialogCode.Accepted:
            return None
        files = dlg.selectedFiles()
        return files[0] if files else None

    def _ask_room_name(self, current):
        """Instance dialog behind a seam (a static execs in C++ past every test patch)."""
        from PySide6.QtWidgets import QInputDialog
        dlg = QInputDialog(self)
        dlg.setInputMode(QInputDialog.InputMode.TextInput)
        dlg.setTextValue(str(current))
        dlg.setWindowTitle("Rename the room")
        dlg.setLabelText("The room's name. It becomes the member folder and the field's own\n"
                         "name, so no path separators and no leading or trailing space:")
        if dlg.exec() != QInputDialog.DialogCode.Accepted:
            return None
        return dlg.textValue()

    # ================================================================== shell plumbing
    def showEvent(self, ev):                       # noqa: N802 (Qt override)
        """Re-derive the text-sized boxes on the FIRST show — measure AFTER polish.

        The constructor's ``_apply_scale`` runs before the app stylesheet has reached these
        widgets, so ``fontMetrics()`` there is the default font's, not CALIBRE's. Snap-caught at
        150: the boxes kept 100%-scale widths and rendered ``!NKEN`` / ``FF9Custoı`` / ``500``.
        ``set_scale`` covers a LIVE dial change; this covers a tab constructed at 150."""
        super().showEvent(ev)
        if not self._polished:
            self._polished = True
            self._apply_scale(self.canvas._scale)

    def resizeEvent(self, ev):                     # noqa: N802 (Qt override)
        """A finding's WRAPPED height depends on the pane's width, so the well is re-measured
        whenever the pane moves — not only when the judge repaints. Without this, a doc that
        narrows after a verdict silently re-wraps a row taller than the box it is in."""
        super().resizeEvent(ev)
        self._fit_plist()

    def crumb_label(self):
        n = len(self._session["rooms"])
        name = self.name_box.text().strip() or "DUNGEON"
        return f"{name} — {n} room{'' if n == 1 else 's'}" if n else "Floorplan"

    def retheme(self, pal):
        self.pal = pal
        self.plist.placeholder_color = pal["muted"]
        self.canvas.retheme(pal)

    def set_scale(self, pct):
        self.canvas.set_scale(pct)
        self._apply_scale(pct)

    # (attribute, the WIDEST STRING it must show whole, headroom in '0's).
    # NOT a character count times averageCharWidth. That is what the first cut did and it clipped:
    # `averageCharWidth()` is 10px at CALIBRE 150 while `FF9CustomMap` really advances 145 (14.5
    # each -- it is all capitals and round bowls), so 16 chars bought 160px for a string needing
    # 185 and the trailing `p` was cut in half (5x crop of the 150 snap). The advance of the REAL
    # string cannot be wrong about the real string.
    _BOX_WIDEST = (("name_box", "DUNGEONNAME", 2), ("mod_box", "FF9CustomMap", 4),
                   ("id_box", "32767", 3))

    def _apply_scale(self, pct):
        """Re-derive every text-sized box from the LIVE font. A px width cannot hear the dial, and
        the snap proved it twice at 150: a 5-digit id read as ``0500`` and ``FF9CustomMap`` as
        ``FF9CustomMa`` — a box scrolled to its caret hides its own value, and a box narrower than
        its own text clips it.

        The frame + `input_pad` + caret allowance is taken from the widget's OWN ``sizeHint``
        rather than guessed: Qt sizes a QLineEdit at 17 characters, so the difference between that
        hint and the advance of 17 characters IS the chrome, in whatever the live stylesheet says.
        """
        for attr, widest, slack in self._BOX_WIDEST:
            box = getattr(self, attr)
            fm = box.fontMetrics()
            chrome = max(0, box.sizeHint().width() - fm.horizontalAdvance("x" * 17))
            need = fm.horizontalAdvance(widest + "0" * slack) + chrome
            box.setMinimumWidth(need)
            box.setMaximumWidth(round(need * 1.35))
            box.setCursorPosition(0)
        self._fit_plist()
        _ = pct                                    # every number above comes from the live font

    _PLIST_ROWS = 2                                # the cap; past it the well scrolls. Two, not
    #                                                five: at CALIBRE 150 the chart had 134px left
    #                                                (snap-measured), and Compose posts the WHOLE
    #                                                list to the shell's Problems panel anyway.
    _PLIST_LINE_CAP = 4                            # ...and no single row may claim more than this
    # THE ROW'S OWN CHROME. Horizontally it is read off the sheet: `QListWidget::item` is
    # `padding: $row_pad` (6px 8px) plus `border-left: 3px` (style.py:485), so the text rect is
    # 19px narrower than the item. Vertically the sheet's 12 is NOT enough and the render is what
    # said so: at exactly wrapped+12 the delegate still elided the third line, because
    # QStyledItemDelegate adds its own focus-frame margins on top of the sheet's padding. 20 is the
    # measured figure (re-verified by snap at 100 and 150), and being a few px generous costs the
    # chart nothing while being a few px short costs the author the end of a sentence.
    _PLIST_PAD_W, _PLIST_PAD_H = 19, 20

    def _fit_plist(self):
        """Size the findings well to its rows' REAL WRAPPED height, and hide it when empty.

        A px constant cannot hear the text dial, and a QListWidget's own sizeHint is ~256x192
        regardless of content (the ``fit_dialog`` lesson) — so an unmanaged well puts a fixed
        floor under the chart at every scale.

        ★ WHY THE HEIGHT IS BOTH MEASURED **AND** STAMPED ON THE ITEM. Neither ``sizeHintForRow``
        nor a flat n-line allowance works. Measured natively at CALIBRE 150 on the real refusal
        (`door ROOM1-ROOM2: depth 100u leaves a standable window only 20u wide -- ...`):
        ``sizeHintForRow`` said **46px** for a row that needs **84** at that viewport width, so the
        scrollbar range stayed **0..0** and the last third of the sentence was gone with no
        affordance at all — a clipped gate message is half a message, which is the one thing this
        well exists not to be. ``QFontMetrics.boundingRect(TextWordWrap)`` over the live viewport
        width says 84, which is what the pixels say. So: compute it, ``setSizeHint`` it (that is
        what gives the view a truthful scroll range when a row overflows the cap), and scroll per
        PIXEL so a capped row can still be read to its end.
        """
        n = self.plist.count()
        self.plist.setVisible(bool(n))
        if not n:
            return
        fm = self.plist.fontMetrics()
        line = fm.height()
        # The scrollbar's width is reserved ALWAYS. Otherwise the row that overflows the cap makes
        # the bar appear, which narrows the viewport, which re-wraps the row taller -- the exact
        # feedback loop that leaves a tail cut off no matter how many passes the caller makes.
        bar = self.plist.verticalScrollBar().sizeHint().width()
        avail = max(80, self.plist.viewport().width() - bar)
        text_w = max(60, avail - self._PLIST_PAD_W)
        total = 0
        for i in range(n):
            need = fm.boundingRect(QRect(0, 0, text_w, 1 << 20),
                                   int(Qt.TextFlag.TextWordWrap),
                                   self.plist.item(i).text()).height() + self._PLIST_PAD_H
            self.plist.item(i).setSizeHint(QSize(avail, need))
            if i < self._PLIST_ROWS:
                total += min(need, self._PLIST_LINE_CAP * line + self._PLIST_PAD_H)
        # ...and a CEILING on the well as a whole, because two three-line findings would otherwise
        # claim ~200px and the chart is the primary surface. Cutting HERE is honest in a way that
        # cutting a row was not: the first finding is always whole, and the scroll range is now
        # truthful (the stamped item hints), so the rest is one flick away instead of gone.
        first = self.plist.item(0).sizeHint().height()
        if self.height() > 200:
            total = min(total, max(first, self.height() // 4))
        self.plist.setMaximumHeight(total + 2 * self.plist.frameWidth() + 4)
