"""The Behavior document -- rungs A-C of the Behavior GUI: render, edit, and AUTHOR ON THE
STAGE a field's ``[behavior]`` block (charter: ``studies/behavior-trees/GUI-VISION.md``).

Three surfaces inside one doc, all fed by :mod:`.behaviorscan`'s pure projections:

- **The Cast** (left): units / groups / pools / the data layer. Selecting a unit scopes the
  ladder and lights its radii on the stage.
- **The Ladder over the Stage** (center, stacked -- the owner's call on open question #1):
  branches as guarded priority rows, TOML order == priority order, the fallback labeled; below
  it the field's behavior geometry (posts, routes, refuges, scan/wander boxes, the selected
  unit's rings) in the map/world canvas grammar -- +z is UP-screen, the layout probe's frame.
- **The Instruments** (right): the compiler's own truth. ``validate()`` problems render
  always (pure, instant, from the OPEN document); the dry-compile report (blackboard map,
  byte histogram, flag indices) runs only behind the user's Compile click, on a worker
  thread, and reads the SAVED file -- the CLI's truth, labeled as such when the doc is dirty
  (the deploy-snapshot two-truths law).

Laws honoured by construction: no I/O at construction or on tab show (the startup-spend law --
the shell feeds the doc the already-parsed open dict); the canvas is painted, so CALIBRE
reaches it via ``set_scale`` and ``retheme`` redraws (the mapview rule); no widget stylesheet
except the canvas hint's selector-scoped one (the round-9 census shape); pane splits are NOT
persisted in rung A (nothing to fossilize); the doc EDITS nothing -- rung B owns writes.
"""

from __future__ import annotations

import threading

from PySide6.QtCore import QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetrics, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFrame, QGraphicsEllipseItem, QGraphicsRectItem,
    QGraphicsScene, QGraphicsSimpleTextItem, QGraphicsView, QHBoxLayout, QLabel, QListWidget,
    QPlainTextEdit, QPushButton, QScrollArea, QSlider, QSplitter, QStackedLayout, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, QWidget,
)

from . import behaviorscan, behaviorsim, icons, widgets

_WORLD = 0.12                                     # world units -> scene px at zoom 1
_ZOOM_MIN, _ZOOM_MAX = 0.05, 6.0
_POST_R = 5                                       # a post marker's screen radius (px, zoom-immune)


SPACING_U = 192                                   # actors jam under ~192u (the layout skill's law)


class StageCanvas(QGraphicsView):
    """The behavior geometry as a chart: +z up-screen (the layout probe's frame, so the two
    instruments agree), Ctrl+scroll zoom / Ctrl+0 fit / Ctrl+1 1:1 (the atlas grammar). Posts
    and labels are screen-fixed furniture (the nameplate trick); rings and routes are real
    world geometry and scale with the zoom.

    Rung C adds EDIT mode: draggable handles over every writable point (the pure ids from
    :func:`behaviorscan.stage_handles`), a resize grip on the selected unit's rings, the
    layout-probe guides (world compass, the ~192u jam-spacing ring, live coordinates while
    dragging), and painted sweep verdicts. The canvas never touches the raw dict — a drag
    ends in ONE callback (``on_move``/``on_radius``/``on_insert``/``on_delete``) and the
    host doc owns the write + the undo step."""

    def __init__(self, palette, *, scale=100, on_move=None, on_radius=None,
                 on_insert=None, on_delete=None):
        super().__init__()
        self.pal = palette
        self._model = None
        self._selected = None                     # unit whose rings are lit
        self._scale = scale if scale in range(50, 301) else 100
        self._zoom = 1.0
        self._fit_pending = False
        self._edit = False
        self._handles = []                        # behaviorscan.stage_handles rows
        self._verdicts = None                     # behaviorscan.SweepResult (persists redraws)
        self._drag = None                         # live drag state, cleared by every _draw
        self._move_items = []                     # [{anchor, handle}] rebuilt per draw
        self._grip_items = []                     # [{anchor, rid, cx, cz, r, ellipse}]
        self._sim_items = []                      # rung E1: the stepper's live layer (only
        self._sim_mode = False                    # these churn per tick — never the scene)
        self._labels = []                         # every _label call, for the de-collision pass
        self.on_sim_click = None                  # sim mode's one input: click = move player
        self.on_move = on_move
        self.on_radius = on_radius
        self.on_insert = on_insert
        self.on_delete = on_delete
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setBackgroundBrush(QColor(palette["surface"]))
        self.setAccessibleName("Behavior stage")
        self.setAccessibleDescription(
            "The field's behavior geometry: unit posts, routes, refuges, scan boxes, and the "
            "selected unit's engagement radii")
        self._hint = QLabel("Ctrl+scroll zooms · Ctrl+0 fits", self.viewport())
        self._hint.setObjectName("behaviorHint")   # selector-scoped (the round-9 census law)
        self._hint.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        # the edit-mode guides: a WORLD compass (the laying-out skill's cardinal law — the
        # room's FRONT is -z, the camera side, which this frame draws DOWN-screen) and the
        # live coordinate readout while a drag is in flight
        self._compass = QLabel("+z back ▲ · −z front (camera) ▼ · +x east ▶", self.viewport())
        self._compass.setObjectName("behaviorHint")
        self._compass.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._compass.hide()
        self._coords = QLabel("", self.viewport())
        self._coords.setObjectName("behaviorHint")
        self._coords.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._coords.hide()
        self._style_hint()

    # -- text + geometry (CALIBRE) --
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
        sheet = ("QLabel#behaviorHint {"
                 f"color: {self.pal['muted']};"
                 f"background: rgba({surf.red()},{surf.green()},{surf.blue()},0.86);"
                 "border-radius: 9px; padding: 2px 9px; }")
        for lab in (self._hint, self._compass, self._coords):
            lab.setFont(self._font(8))
            lab.setStyleSheet(sheet)
        self._coords.setStyleSheet(sheet.replace(self.pal["muted"], self.pal["text"], 1))
        self._place_hint()

    def _place_hint(self):
        self._hint.adjustSize()                    # measure AFTER polish -- construction adjustSize lies
        vp = self.viewport()
        self._hint.move(vp.width() - self._hint.width() - 10,
                        vp.height() - self._hint.height() - 8)
        self._compass.adjustSize()
        self._compass.move(10, 8)                  # top-left: clear of the zoom hint's corner
        self._coords.adjustSize()
        self._coords.move(10, vp.height() - self._coords.height() - 8)

    # -- public --
    def set_model(self, model, selected=None, *, refit=False, handles=None):
        """New geometry (+ the unit whose rings light). ``refit`` on a FIELD change only -- a
        same-field re-render keeps the user's zoom/pan (the map's own contract). ``handles``
        is the edit mode's draggable-point list (None outside edit mode)."""
        self._model = model
        self._selected = selected
        self._handles = handles or []
        if refit:
            self.resetTransform()
            self._zoom = 1.0
            self._fit_pending = True
        self._draw()

    def set_edit(self, on):
        """Edit mode: handles + guides appear; panning stays (a drag starts only ON a
        handle). The host re-feeds set_model with handles right after."""
        on = bool(on)
        if on == self._edit:
            return
        self._edit = on
        self._compass.setVisible(on)
        if not on:
            self._handles = []
        self._draw()

    def set_verdicts(self, res):
        """Paint (or clear, with None) a sweep's verdicts. They persist across redraws
        until the host replaces them — a re-render must not silently un-say a finding."""
        self._verdicts = res
        self._draw()

    def select_unit(self, name):
        if name != self._selected:
            self._selected = name
            self._draw()

    # -- rung E1: the tick-stepper's live layer --
    def set_sim_mode(self, on):
        self._sim_mode = bool(on)
        if not on:
            self.set_sim(None)

    def set_sim(self, state):
        """Draw (or clear, with None) one sim snapshot: a filled dot per living unit at its
        SIMULATED position, an ✕ where one died, and the sim player. Only these items churn
        per tick — a full scene rebuild at 30 Hz would burn the user's pan/zoom."""
        for it in self._sim_items:
            try:
                self._scene.removeItem(it)
            except RuntimeError:                   # scene rebuilt underneath (a _draw ran)
                pass
        self._sim_items = []
        if not state:
            return
        pal = self.pal

        def dot(x, z, color, *, filled, r=5, tag="sim"):
            sx, sy = self._pt(x, z)
            pen = QPen(QColor(color), 1.4)
            pen.setCosmetic(True)
            brush = QBrush(QColor(color)) if filled else QBrush(Qt.BrushStyle.NoBrush)
            it = self._scene.addEllipse(sx - r, sy - r, 2 * r, 2 * r, pen, brush)
            it.setFlag(it.GraphicsItemFlag.ItemIgnoresTransformations)
            it.setPos(sx, sy)
            it.setRect(-r, -r, 2 * r, 2 * r)
            it.setData(0, tag)
            self._sim_items.append(it)

        for u in state["units"].values():
            if u.get("dormant"):
                continue
            if u["alive"]:
                dot(u["x"], u["z"], pal["text"], filled=True)
            else:
                dot(u["x"], u["z"], pal["muted"], filled=False, r=4, tag="simdead")
        px, pz = state["player"]
        dot(px, pz, pal["text"], filled=False, r=8, tag="simplayer")
        dot(px, pz, pal["text"], filled=True, r=2, tag="simplayer")

    # -- frame mapping: +z is UP-screen (scene y grows down) --
    @staticmethod
    def _pt(x, z):
        return (x * _WORLD, -z * _WORLD)

    def _fit(self):
        r = self._scene.sceneRect()
        if r.isEmpty():
            return
        vw, vh = max(1, self.viewport().width()), max(1, self.viewport().height())
        z = min(vw / max(1.0, r.width()), vh / max(1.0, r.height())) * 0.94
        z = max(_ZOOM_MIN, min(3.0, z))
        self.resetTransform()
        self.scale(z, z)
        self._zoom = z
        self.centerOn(r.center())
        self._decollide_labels()

    def _decollide_labels(self):
        """Shuffle overlapping labels to free vertical tiers. Labels live in SCREEN px
        (zoom-immune furniture), so what collides depends on the current transform —
        the pass re-runs after every draw, fit, and zoom step. Anchors never move;
        only each text child's dy shifts, so the leader point stays honest."""
        placed = []
        step = 13
        vw = self.viewport().width()
        for lab in self._labels:
            try:
                base = self.mapFromScene(lab["anchor"].pos())
            except RuntimeError:                   # scene rebuilt under a stale list
                return
            t = lab["item"]
            br = t.boundingRect()
            dx = lab["dx"]
            if vw > 40 and base.x() + dx + br.width() > vw - 2:
                dx = -dx - br.width()              # off the right edge: mirror to the left
            x = base.x() + dx
            cands, down = [lab["dy"]], []
            for k in range(1, 7):                  # nearest tier first, above before below
                cands.append(lab["dy"] - step * k)
                down.append(lab["dy"] + step * k)
            # a DOWN tier must clear the anchor's own marker row (r≈5 + breathing room):
            # the first down candidate from dy=-16 lands the text ACROSS the dots
            # (snap-caught strike-through on the ×N cluster labels)
            cands += [dy for dy in down if dy >= 8 or dy + br.height() <= -8]
            pick = cands[0]
            for onscreen_only in (True, False):    # prefer a tier that stays in the
                found = False                      # viewport; overlap-free beats clipped
                for dy in cands:
                    rect = QRectF(x, base.y() + dy, br.width(), br.height())
                    if onscreen_only and rect.top() < 1:
                        continue
                    if not any(rect.intersects(pl) for pl in placed):
                        pick, found = dy, True
                        break
                if found:
                    break
            t.setPos(dx, pick)
            placed.append(QRectF(x, base.y() + pick, br.width(), br.height()))

    def paintEvent(self, ev):                      # noqa: N802 (Qt override)
        if self._fit_pending:                      # deferred to the first REAL paint: at set_model
            self._fit_pending = False              # time the tab may be hidden, the viewport stale
            self._fit()
        super().paintEvent(ev)

    def resizeEvent(self, ev):                     # noqa: N802 (Qt override)
        super().resizeEvent(ev)
        self._place_hint()

    def wheelEvent(self, event):                   # noqa: N802 (Qt override)
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            f = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            z = max(_ZOOM_MIN, min(_ZOOM_MAX, self._zoom * f))
            if z != self._zoom:
                self.scale(z / self._zoom, z / self._zoom)
                self._zoom = z
                self._decollide_labels()           # screen-px labels re-negotiate per zoom
            event.accept()
            return
        super().wheelEvent(event)

    def keyPressEvent(self, event):                # noqa: N802 (Qt override)
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_0:
                self._fit()
                event.accept()
                return
            if event.key() == Qt.Key.Key_1:
                self.resetTransform()
                self._zoom = 1.0
                self._decollide_labels()
                event.accept()
                return
        super().keyPressEvent(event)

    # -- rung C: the drag machinery. Mouse handlers are thin wrappers over the world-frame
    # methods below (the testable seam, the suite's own convention): press resolves an item
    # to a handle/grip, move updates ONLY the grabbed items + guides, release commits ONE
    # callback and the host's re-render redraws everything.
    def _resolve_grab(self, item):
        """Walk an itemAt() hit up to its tagged anchor; ('handle', i) / ('grip', i) / None."""
        while item is not None:
            tag = item.data(0)
            if tag == "handle":
                return ("handle", int(item.data(1)))
            if tag == "ringgrip":
                return ("grip", int(item.data(1)))
            item = item.parentItem()
        return None

    def _begin_drag(self, grab):
        kind, i = grab
        if kind == "handle":
            if not 0 <= i < len(self._move_items):
                return False
            row = self._move_items[i]
            h = row["handle"]
            d = {"kind": "move", "row": row, "x": h["x"], "z": h["z"], "spacing": None}
            if h["kind"] in ("post", "player"):    # the jam-spacing guide rides the drag
                pen = QPen(QColor(self.pal["muted"]), 1.0)
                pen.setCosmetic(True)
                pen.setDashPattern([2, 3])
                rr = SPACING_U * _WORLD
                sx, sy = self._pt(h["x"], h["z"])
                d["spacing"] = self._scene.addEllipse(sx - rr, sy - rr, 2 * rr, 2 * rr, pen)
            self._drag = d
        else:
            if not 0 <= i < len(self._grip_items):
                return False
            g = self._grip_items[i]
            self._drag = {"kind": "ring", "g": g, "r": g["r"]}
        self._update_coords()
        return True

    def _drag_world(self, x, z):
        """One drag step, WORLD coords (the tests drive this directly)."""
        d = self._drag
        if not d:
            return
        if d["kind"] == "move":
            d["x"], d["z"] = int(round(x)), int(round(z))
            sx, sy = self._pt(d["x"], d["z"])
            d["row"]["anchor"].setPos(sx, sy)
            if d["spacing"] is not None:
                rr = SPACING_U * _WORLD
                d["spacing"].setRect(sx - rr, sy - rr, 2 * rr, 2 * rr)
        else:
            g = d["g"]
            from math import hypot
            from . import behaviorscan as _bs
            d["r"] = max(_bs.RADIUS_FLOOR, int(round(hypot(x - g["cx"], z - g["cz"]))))
            rr = d["r"] * _WORLD
            sx, sy = self._pt(g["cx"], g["cz"])
            g["ellipse"].setRect(sx - rr, sy - rr, 2 * rr, 2 * rr)
            g["anchor"].setPos(sx + rr, sy)
        self._update_coords()

    def _end_drag(self):
        """Commit: exactly one callback; the host's re-render rebuilds the scene."""
        d, self._drag = self._drag, None
        self._coords.hide()
        if not d:
            return
        if d["kind"] == "move":
            if d["spacing"] is not None:
                self._scene.removeItem(d["spacing"])
            h = d["row"]["handle"]
            if (d["x"], d["z"]) != (h["x"], h["z"]) and self.on_move:
                self.on_move(h["id"], d["x"], d["z"])
        else:
            g = d["g"]
            if d["r"] != g["r"] and self.on_radius:
                self.on_radius(g["rid"], d["r"])

    def _update_coords(self):
        d = self._drag
        if not d:
            return
        if d["kind"] == "move":
            self._coords.setText(f"{d['row']['handle']['label']} · x {d['x']} · z {d['z']}")
        else:
            self._coords.setText(f"radius {d['r']}u")
        self._coords.show()
        self._place_hint()

    def mousePressEvent(self, event):              # noqa: N802 (Qt override)
        if self._sim_mode and event.button() == Qt.MouseButton.LeftButton \
                and self.on_sim_click:
            sp = self.mapToScene(event.position().toPoint())
            self.on_sim_click(sp.x() / _WORLD, -sp.y() / _WORLD)
            event.accept()
            return
        if self._edit and event.button() == Qt.MouseButton.LeftButton:
            grab = self._resolve_grab(self.itemAt(event.position().toPoint()))
            if grab and self._begin_drag(grab):
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):               # noqa: N802 (Qt override)
        if self._drag:
            sp = self.mapToScene(event.position().toPoint())
            self._drag_world(sp.x() / _WORLD, -sp.y() / _WORLD)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):            # noqa: N802 (Qt override)
        if self._drag:
            self._end_drag()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):             # noqa: N802 (Qt override)
        """Right-click on a route point (edit mode): the list ops. The menu is built
        through the ``_route_menu`` seam so tests drive the choices without a popup."""
        if not self._edit:
            return super().contextMenuEvent(event)
        grab = self._resolve_grab(self.itemAt(event.pos()))
        if not grab or grab[0] != "handle":
            return super().contextMenuEvent(event)
        h = self._move_items[grab[1]]["handle"]
        if not h.get("list_id"):
            return super().contextMenuEvent(event)
        self._route_menu(h, event.globalPos())
        event.accept()

    def _route_menu(self, handle, global_pos):
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        ins = menu.addAction("Insert a point after this one")
        rm = menu.addAction("Delete this point")
        act = menu.exec(global_pos)
        if act is ins and self.on_insert:
            self.on_insert(handle["list_id"])
        elif act is rm and self.on_delete:
            self.on_delete(handle["list_id"])

    # -- drawing --
    def _fixed(self, item):
        """Screen-fixed chart furniture (labels, post markers) -- readable at any zoom."""
        item.setFlag(item.GraphicsItemFlag.ItemIgnoresTransformations)
        return item

    def _anchor(self, x, z, tag):
        """A zero-size, zoom-immune anchor at a world point: its CHILDREN live in screen px
        (the nameplate trick -- readable furniture at any zoom)."""
        sx, sy = self._pt(x, z)
        anchor = self._scene.addRect(QRectF(0, 0, 0, 0), QPen(Qt.PenStyle.NoPen))
        anchor.setPos(sx, sy)
        anchor.setData(0, tag)
        return self._fixed(anchor)

    def _label(self, text, x, z, *, dx=8, dy=-16, color=None, bold=False, pt=8, tip=None):
        anchor = self._anchor(x, z, "label")
        t = QGraphicsSimpleTextItem(text, anchor)
        t.setFont(self._font(pt, bold))
        t.setBrush(QBrush(QColor(color or self.pal["muted"])))
        t.setPos(dx, dy)                           # screen px, relative to the anchor
        if tip:
            anchor.setToolTip(tip)
        self._labels.append({"anchor": anchor, "item": t, "dx": dx, "dy": dy})
        return anchor

    def _marker(self, x, z, color, *, hollow=False, r=_POST_R, tag="post"):
        anchor = self._anchor(x, z, tag)
        dot = QGraphicsEllipseItem(-r, -r, 2 * r, 2 * r, anchor)
        dot.setPen(QPen(QColor(color), 1.6))
        dot.setBrush(QBrush(Qt.BrushStyle.NoBrush) if hollow else QBrush(QColor(color)))
        return anchor

    def _draw(self):
        sc, pal = self._scene, self.pal
        self._drag = None                          # scene.clear() deletes any grabbed item
        self._coords.hide()
        self._move_items, self._grip_items = [], []
        self._labels = []                          # rebuilt below; the de-collision pass reads it
        sc.clear()
        m = self._model
        if not m or m.get("bounds") is None:
            t = self._fixed(sc.addSimpleText(
                "No positions to draw — behavior units bind to named [[npc]]s with pos.",
                self._font(9)))
            t.setBrush(QBrush(QColor(pal["muted"])))
            sc.setSceneRect(-200, -60, 400, 120)
            t.setPos(-190, -8)
            return
        x0, z0, x1, z1 = m["bounds"]
        pad = max(120.0, 0.12 * max(x1 - x0, z1 - z0, 1))
        left, top = self._pt(x0 - pad, z1 + pad)
        right, bot = self._pt(x1 + pad, z0 - pad)
        sc.setSceneRect(QRectF(left, top, right - left, bot - top))

        def cosmetic(color, w=1.6, dash=None):
            pen = QPen(QColor(color), w)
            pen.setCosmetic(True)                  # rings/routes must survive fit zoom (the
            if dash:                               # atlas's vanishing-ring lesson)
                pen.setDashPattern(dash)
            return pen

        muted, border = pal["muted"], pal["border"]
        # wander + scan boxes (Chebyshev = squares in world frame). A wander box carries no
        # label of its own -- its unit's post sits at the centre and says whose it is
        # (snap-caught: the label pile-up at fit zoom was the canvas's dominant noise).
        for box, name in ([(w, None) for w in m["wanders"]]
                          + [(s, s["name"]) for s in m["scans"]]):
            bx0, by0 = self._pt(box["x"] - box["r"], box["z"] + box["r"])
            bx1, by1 = self._pt(box["x"] + box["r"], box["z"] - box["r"])
            it = sc.addRect(QRectF(bx0, by0, bx1 - bx0, by1 - by0),
                            cosmetic(border if name is None else muted, 1.2, [4, 4]))
            it.setData(0, "scan" if name else "wander")
            if name:
                self._label(f"scan · {name}", box["x"] - box["r"], box["z"] + box["r"],
                            dx=4, dy=4)
        # routes (patrol/march): real geometry, muted; the wrap leg only when closed
        for r in m["routes"]:
            pts = [self._pt(x, z) for x, z in r["points"]]
            seq = pts + [pts[0]] if r["closed"] and len(pts) > 2 else pts
            for a, b in zip(seq, seq[1:]):
                ln = sc.addLine(a[0], a[1], b[0], b[1], cosmetic(muted, 2.0))
                ln.setData(0, "route")
            for x, z in r["points"]:
                self._marker(x, z, muted, r=2.5, tag="routept")
            # label the FIRST LEG's midpoint, not point 0 -- a route usually starts at (or near)
            # its walker's post, and two labels on one spot was the snap's worst collision
            (ax, az), (bx2, bz2) = r["points"][0], r["points"][1 % len(r["points"])]
            self._label(f"{r['verb']} · {r['unit']}" + (" · auto" if r["auto"] else ""),
                        (ax + bx2) / 2, (az + bz2) / 2, dy=4)
        # flee refuges: numbered flags in priority order
        for ref in m["refuges"]:
            for i, (x, z) in enumerate(ref["points"], 1):
                self._marker(x, z, pal["warn"], hollow=True, r=4, tag="refuge")
                self._label(f"⚑{i} {ref['unit']}", x, z, color=pal["warn"], dy=-18)
        # the selected unit's rings: real world radii, quiet accent (selection state,
        # the one accent this canvas spends -- the map's ring language)
        rings = (m["rings"] or {}).get(self._selected or "", [])
        posts = {p["name"]: (p["x"], p["z"]) for p in m["posts"]}
        for ring in rings:
            cx = ring.get("x", posts.get(self._selected, (None, None))[0])
            cz = ring.get("z", posts.get(self._selected, (None, None))[1])
            if cx is None:
                continue
            rr = ring["radius"] * _WORLD
            sx, sy = self._pt(cx, cz)
            it = sc.addEllipse(sx - rr, sy - rr, 2 * rr, 2 * rr,
                               cosmetic(self.pal["accent"], 1.4, [5, 4]))
            it.setData(0, "ring")
            if self._edit and ring.get("rid"):     # the resize grip sits on the ring's east edge
                anchor = self._anchor(cx + ring["radius"], cz, "ringgrip")
                anchor.setData(1, len(self._grip_items))
                sq = QGraphicsRectItem(-4, -4, 8, 8, anchor)
                sq.setPen(QPen(QColor(pal["accent"]), 1.4))
                sq.setBrush(QBrush(QColor(pal["surface"])))
                anchor.setToolTip(f"Drag to resize — {ring['label']}")
                self._grip_items.append({"anchor": anchor, "rid": tuple(ring["rid"]),
                                         "cx": cx, "cz": cz, "r": ring["radius"],
                                         "ellipse": it})
        # posts + player last (loudest). Same-unit members standing in a knot (a class
        # row's squad at a [siege] entrance) share ONE "name ×N" label at the knot's
        # centroid — five stacked spawn labels were an unreadable smear (snap-caught);
        # every member keeps its own dot, and the label's hover names them all.
        by_unit = {}
        for p in m["posts"]:
            by_unit.setdefault(p.get("unit", p["name"]), []).append(p)
        for uname, ps in by_unit.items():
            done = [False] * len(ps)
            for i, p in enumerate(ps):
                if done[i]:
                    continue
                done[i] = True
                knot = [p]
                grew = True
                while grew:                        # transitive: a RANK chains member to
                    grew = False                   # member (the [siege] park spaces them
                    for j in range(len(ps)):       # 400u apart — an anchor test misses
                        if done[j]:                # everyone past the first)
                            continue
                        if any(max(abs(ps[j]["x"] - q["x"]),
                                   abs(ps[j]["z"] - q["z"])) <= 2.5 * SPACING_U
                               for q in knot):     # Chebyshev, the house metric
                            done[j] = True
                            knot.append(ps[j])
                            grew = True
                col = muted if p["pooled"] else pal["success"]
                for q in knot:
                    self._marker(q["x"], q["z"], col, hollow=q["pooled"])
                # a CLASS row's members all light when their class is selected ("unit"
                # carries the owning row's name; a plain post has name == unit)
                sel = self._selected in ([uname] + [q["name"] for q in knot])
                if len(knot) == 1:
                    text, tip = p["name"], None
                else:
                    text = f"{uname} ×{len(knot)}"
                    tip = ", ".join(q["name"] for q in knot)
                self._label(text + (" · pooled" if p["pooled"] else ""),
                            sum(q["x"] for q in knot) / len(knot),
                            sum(q["z"] for q in knot) / len(knot),
                            color=pal["text"] if sel else muted, bold=sel, pt=8.5, tip=tip)
        if m.get("player"):
            px, pz = m["player"]
            self._marker(px, pz, pal["text"], hollow=True, r=4, tag="player")
            self._label("player spawn", px, pz, color=pal["text"], dy=-18)
        # sweep verdicts, in place (rung C): the jammed SUB-SEGMENT in error over its route
        # leg, wall-hug legs re-traced in warn dashes, a pursuit family's worst pairs as
        # dotted legs. Persist until the host clears/replaces them.
        v = self._verdicts
        if v is not None and getattr(v, "ok", False):
            for j in v.jams:
                (ax, az), (bx, bz) = j["a"], j["b"]
                p0 = self._pt(ax + (bx - ax) * j["t0"], az + (bz - az) * j["t0"])
                p1 = self._pt(ax + (bx - ax) * j["t1"], az + (bz - az) * j["t1"])
                ln = sc.addLine(p0[0], p0[1], p1[0], p1[1], cosmetic(pal["error"], 3.0))
                ln.setData(0, "jam")
                self._marker(j["mid"][0], j["mid"][1], pal["error"], hollow=True, r=5,
                             tag="jam")
                self._label("✕ floor break (no seam)" if j.get("kind") == "floor"
                            else f"✕ off-mesh ~{j['span']:.0f}u",
                            j["mid"][0], j["mid"][1], color=pal["error"], dy=-20)
            for hg in v.hugs:
                (ax, az), (bx, bz) = hg["a"], hg["b"]
                p0, p1 = self._pt(ax, az), self._pt(bx, bz)
                ln = sc.addLine(p0[0], p0[1], p1[0], p1[1],
                                cosmetic(pal["warn"], 2.0, [3, 3]))
                ln.setData(0, "hug")
                mx, mz = (ax + bx) / 2, (az + bz) / 2
                self._label(f"{hg['minwall']:.0f}u from a wall", mx, mz,
                            color=pal["warn"], dy=4)
            for p in v.pursuits:
                for k, h in enumerate(p["worst"]):
                    (ax, az), (bx, bz) = h["a"], h["b"]
                    p0, p1 = self._pt(ax, az), self._pt(bx, bz)
                    ln = sc.addLine(p0[0], p0[1], p1[0], p1[1],
                                    cosmetic(pal["warn"], 1.4, [1, 3]))
                    ln.setData(0, "pursuit")
                    self._marker(h["mid"][0], h["mid"][1], pal["warn"], hollow=True,
                                 r=4, tag="pursuit")
                    if k == 0:                     # one caption per family, on its worst pair --
                        # its OWN tier (dy) because a pursuit's worst pair often crosses the
                        # exact wall a route jam already labels (snap-caught collision)
                        pct = 100.0 * p["blocked"] / max(1, p["tested"])
                        self._label(f"{p['unit']} pursuit jams ({pct:.0f}% of pairs)",
                                    h["mid"][0], h["mid"][1], color=pal["warn"], dy=-36)
        # the edit handles, LAST (topmost for itemAt): a hollow grip square per writable
        # point; the geometry underneath keeps its kind colour — the grip is an affordance,
        # not a legend entry
        if self._edit:
            for i, h in enumerate(self._handles):
                anchor = self._anchor(h["x"], h["z"], "handle")
                anchor.setData(1, i)
                sq = QGraphicsRectItem(-4, -4, 8, 8, anchor)
                sq.setPen(QPen(QColor(pal["text"]), 1.2))
                sq.setBrush(QBrush(QColor(pal["surface"])))
                anchor.setToolTip(h["label"] + (
                    "\nDrag to move · right-click for point ops" if h.get("list_id")
                    else "\nDrag to move"))
                self._move_items.append({"anchor": anchor, "handle": h})
        self._decollide_labels()                   # labels negotiate tiers at the current zoom


class LadderView(QWidget):
    """The selected unit's branches as priority rows -- rung B makes them EDITABLE: each row
    carries move-up/down (the priority edit), Edit (opens the branch editor), and Delete; the
    header offers Add branch / Remove unit. ``actions`` is a dict of callbacks the host doc
    provides (move/edit/delete/add/remove_unit); rows stay dumb -- every mutation goes through
    the host, which owns the raw dict and the shell's undo contract."""

    def __init__(self, pal, actions=None):
        super().__init__()
        self.pal = pal
        self.actions = actions or {}
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(10, 8, 10, 8)
        self._lay.setSpacing(6)
        self._prios = []                           # rung E1: the sim sweep's row markers
        self.setAccessibleName("Behavior ladder")

    def set_sim_sel(self, sels):
        """Mark the branch rows the tick-stepper selected this tick (a SET — a class row's
        members can select different branches). Shape, not colour: ▶ on the priority chip."""
        sels = sels or set()
        for i, lab in enumerate(self._prios):
            lab.setText(("▶ " if i in sels else "") + str(i + 1))

    def set_rows(self, unit_name, rows):
        self._prios = []
        while self._lay.count():
            w = self._lay.takeAt(0).widget()
            if w is not None:
                w.hide()                           # HIDE FIRST: reparenting a VISIBLE widget to
                w.setParent(None)                  # None makes it a top-level OS window for the
                w.deleteLater()                    # instant before deleteLater lands -- a reorder
        #                                            sprayed phantom "pythonw" windows (playtest-
        #                                            caught). The reparent itself stays: a
        #                                            deleteLater-only clear leaves zombie children
        #                                            until the loop runs (the harness's own
        #                                            DeferredDelete lesson).
        last_uncond = max((i for i, r in enumerate(rows) if r["unconditional"]), default=None)
        for i, row in enumerate(rows):
            self._lay.addWidget(self._row(row, fallback=(i == last_uncond and i == len(rows) - 1)))
        if not rows:
            self._lay.addWidget(widgets.caption(
                "This unit has no branches yet — every [[behavior.unit]] needs at least an "
                "unconditional fallback (patrol / hold / march / flee / wander / walk_to)."))
        self._lay.addStretch(1)

    def _chip(self, text):
        lab = widgets.role_label(text, "chip")
        lab.setProperty("mono", True)
        return lab

    def _row(self, row, *, fallback):
        frame = widgets.card()
        h = QHBoxLayout(frame)
        h.setContentsMargins(10, 6, 10, 6)
        h.setSpacing(7)
        prio = widgets.role_label(str(row["index"]), "caption")
        prio.setProperty("mono", True)
        prio.setMinimumWidth(prio.fontMetrics().horizontalAdvance("▶ 88"))   # ▶ must not reflow
        h.addWidget(prio)
        self._prios.append(prio)
        # the action buttons sit LEFT, pinned beside the priority number: a long row h-scrolls,
        # and a right-aligned control inside a scrolling row lives off-screen (snap-caught)
        if self.actions:
            bi = row["index"] - 1
            for glyph, tip, cb in (
                    ("↑", "Raise this branch's priority", lambda _=False, b=bi: self.actions["move"](b, -1)),
                    ("↓", "Lower this branch's priority", lambda _=False, b=bi: self.actions["move"](b, +1)),
                    ("✎", "Edit this branch (its own TOML, with insert menus)",
                     lambda _=False, b=bi: self.actions["edit"](b)),
                    ("✕", "Delete this branch (Ctrl+Z undoes)",
                     lambda _=False, b=bi: self.actions["delete"](b))):
                btn = QPushButton(glyph)
                btn.setProperty("role", "rowtool")   # repeated furniture, not four buttons
                btn.setToolTip(tip)
                btn.setAccessibleName(f"{tip} — branch {row['index']}")
                btn.clicked.connect(cb)
                h.addWidget(btn)
        if row["conds"]:
            for ci, c in enumerate(row["conds"]):
                if ci:
                    h.addWidget(widgets.role_label("AND", "subtle"))
                h.addWidget(self._chip(c))
        else:
            h.addWidget(self._chip("always"))
        h.addWidget(widgets.role_label("→", "subtle"))
        verb = widgets.role_label(row["verb"], "cardtitle")
        verb.setProperty("mono", True)
        h.addWidget(verb)
        if row["detail"]:
            det = widgets.role_label(row["detail"], "caption")
            det.setProperty("mono", True)
            h.addWidget(det)
        h.addStretch(1)
        for d in row["decos"]:
            kind = "warn" if d.startswith(("raise ", "clear ")) else "info"
            h.addWidget(widgets.status_chip(d, kind))
        if row.get("shadow"):
            dead = widgets.status_chip(f"never selects — row {row['shadow']} wins first",
                                       "warn")
            dead.setToolTip(
                "First-match priority: whenever this row's conditions hold, row "
                f"{row['shadow']}'s already hold — and row {row['shadow']} has no "
                "once/cooldown gate, so it wins every tick. Reorder the rows, tighten "
                f"row {row['shadow']}'s conditions, or gate it (once / cooldown / flag).")
            h.addWidget(dead)
        if fallback:
            h.addWidget(widgets.status_chip("fallback · required", "good"))
        frame.setAccessibleName(
            f"branch {row['index']}: " + (" and ".join(row["conds"]) or "always")
            + f" then {row['verb']}")
        return frame


class BranchEditor(QFrame):
    """The inline branch editor: one branch as its own TOML (the ladder's chips are LITERALLY
    this text), with When/Do insert menus generated from the compiler's verb tables and a live
    parse + validate() readout. Apply hands the parsed branch to the host; nothing here touches
    the raw dict."""

    def __init__(self, pal, *, on_apply, on_close, check):
        super().__init__()
        self.setProperty("role", "card")
        self.pal = pal
        self.on_apply = on_apply
        self.on_close = on_close
        self.check = check                          # (text) -> (branch|None, note, state)
        self.unit = None
        self.bi = None
        v = QVBoxLayout(self)
        v.setContentsMargins(10, 8, 10, 8)
        v.setSpacing(6)
        head = QHBoxLayout()
        head.setSpacing(8)
        self.title = widgets.role_label("Branch", "cardtitle")
        head.addWidget(self.title)
        head.addStretch(1)
        from PySide6.QtWidgets import QMenu, QToolButton
        for label, rows in (("When ▾", behaviorscan.cond_templates()),
                            ("Do ▾", behaviorscan.action_templates())):
            btn = QToolButton()
            btn.setText(label)
            btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
            btn.setToolTip("Insert a template at the cursor — the verb list IS the compiler's "
                           "own table, so it can never go stale.")
            btn.setAccessibleName(f"Insert {label[:-2].strip().lower()} template")
            menu = QMenu(btn)
            for verb, snippet in rows:
                act = menu.addAction(verb)
                act.setToolTip(snippet)
                act.triggered.connect(lambda _=False, s=snippet: self.box.insertPlainText(s))
            btn.setMenu(menu)
            head.addWidget(btn)
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setToolTip("Write this branch into the open document (Ctrl+Z undoes).")
        self.apply_btn.clicked.connect(lambda: self.on_apply())
        head.addWidget(self.apply_btn)
        close_btn = QPushButton("Close")
        close_btn.setProperty("role", "quiet")
        close_btn.clicked.connect(lambda: self.on_close())
        head.addWidget(close_btn)
        hw = QWidget()
        hw.setLayout(head)
        v.addWidget(hw)
        self.box = QPlainTextEdit()
        self.box.setAccessibleName("Branch TOML")
        fm = QFontMetrics(self.box.font())
        self.box.setMinimumHeight(fm.lineSpacing() * 5)
        self.box.textChanged.connect(self._on_typed)
        v.addWidget(self.box, 1)
        self.note = widgets.caption("")
        self.note.setWordWrap(True)
        v.addWidget(self.note)
        from PySide6.QtCore import QTimer
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(250)
        self._debounce.timeout.connect(self._judge)

    def open_branch(self, unit, bi, text):
        self.unit, self.bi = unit, bi
        self.title.setText(f"{unit} — branch {bi + 1}")
        self.box.blockSignals(True)
        self.box.setPlainText(text)
        self.box.blockSignals(False)
        self._judge()
        self.show()
        self.box.setFocus()

    def _on_typed(self):
        self._debounce.start()

    def _judge(self):
        """The live legality readout -- the compiler's words, never a paraphrase."""
        if self.unit is None:
            return
        _branch, note, state = self.check(self.box.toPlainText())
        self.note.setText(note)
        widgets.set_state(self.note, state)


class ArchetypeWizard(QDialog):
    """Rung D's stamp picker grown into ONE teaching surface (owner ask: "more of an
    interactive wizard than a set of 2 picker windows"): the proven trees on the left
    with their teach text, the actor bindings appearing exactly when the picked
    archetype needs them, and a LIVE preview of the ladder the stamp will write — the
    REAL op on a scratch copy of the open document, never a paraphrase (stamp-parity
    by construction, the Info Hub snippet law).

    Testable without ``exec()``: construct, drive ``list``/``who``/``vs``/``partner``,
    read the preview label, call ``accept()``, read ``picked()``. The doc's modal seam
    (``_ask_stamp``) is the only exec() site."""

    def __init__(self, pal, raw, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Stamp an archetype")
        self.pal = pal
        self._raw = raw
        self._picked = None
        self._free = behaviorscan.npc_candidates(raw)
        self._members = ([m for u in raw["behavior"]["unit"]
                          for m in behaviorscan.BT.row_members(u)]
                         if behaviorscan.has_behavior(raw) else [])
        outer = QVBoxLayout(self)
        outer.setSpacing(10)
        body = QHBoxLayout()
        body.setSpacing(14)
        left = QVBoxLayout()
        left.setSpacing(4)
        left.addWidget(widgets.role_label("THE PROVEN TREES", "subtle"))
        self.list = QListWidget()
        self.list.setAccessibleName("Behavior archetypes")
        for a in behaviorscan.BEHAVIOR_ARCHETYPES:
            self.list.addItem(a["name"])
        left.addWidget(self.list, 1)
        body.addLayout(left, 1)
        right = QVBoxLayout()
        right.setSpacing(6)
        self.teach = widgets.caption("")
        self.teach.setWordWrap(True)
        right.addWidget(self.teach)

        def combo_row(caption, a11y):
            row = QWidget()
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(8)
            h.addWidget(widgets.role_label(caption, "caption"))
            box = QComboBox()
            box.setAccessibleName(a11y)
            h.addWidget(box, 1)
            return row, box

        self._who_row, self.who = combo_row("Stamp onto", "Stamp onto npc")
        self.who.addItems(self._free)
        right.addWidget(self._who_row)
        self._vs_row, self.vs = combo_row("Fights", "Guard target unit")
        self.vs.addItems(self._members)
        right.addWidget(self._vs_row)
        self._partner_row, self.partner = combo_row("Partner", "Shift partner npc")
        right.addWidget(self._partner_row)
        right.addWidget(widgets.role_label("THE LADDER IT WRITES", "subtle"))
        self.preview = QLabel("")
        self.preview.setProperty("mono", True)     # the QSS mono rule names QLabel
        self.preview.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.preview.setAccessibleName("Stamp preview")
        right.addWidget(self.preview, 1)
        self.note = widgets.caption("")
        self.note.setWordWrap(True)
        right.addWidget(self.note)
        body.addLayout(right, 2)
        outer.addLayout(body, 1)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                              | QDialogButtonBox.StandardButton.Cancel)
        self._ok = bb.button(QDialogButtonBox.StandardButton.Ok)
        self._ok.setText("Stamp")
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        outer.addWidget(bb)
        self.list.currentRowChanged.connect(self._sync)
        self.who.currentIndexChanged.connect(self._sync)
        self.vs.currentIndexChanged.connect(self._refresh)
        self.partner.currentIndexChanged.connect(self._refresh)
        self.list.setCurrentRow(0)                 # fires _sync -> _refresh
        widgets.fit_dialog(self, ch=96, list_rows=max(
            6, len(behaviorscan.BEHAVIOR_ARCHETYPES)), lines=18)

    # -- state --
    def _archetype(self):
        i = self.list.currentRow()
        rows = behaviorscan.BEHAVIOR_ARCHETYPES
        return rows[i] if 0 <= i < len(rows) else None

    def selection(self):
        """The would-be stamp as ``(key, npc, target-or-partner)`` — pieces may be None
        while the dialog is mid-thought; :meth:`_refresh` owns legality."""
        a = self._archetype()
        if a is None:
            return None
        target = None
        if a.get("needs_target"):
            target = self.vs.currentText() or None
        if a.get("needs_partner"):
            target = self.partner.currentText() or None
        return (a["key"], self.who.currentText() or None, target)

    def _sync(self, *_):
        """Archetype/primary changed: teach text, which binding rows exist, and the
        partner list (always the free npcs MINUS the primary)."""
        a = self._archetype()
        if a is None:
            return
        self.teach.setText(a["teach"])
        self._vs_row.setVisible(bool(a.get("needs_target")))
        self._partner_row.setVisible(bool(a.get("needs_partner")))
        if a.get("needs_partner"):
            keep = self.partner.currentText()
            rest = [n for n in self._free if n != self.who.currentText()]
            self.partner.blockSignals(True)
            self.partner.clear()
            self.partner.addItems(rest)
            if keep in rest:
                self.partner.setCurrentText(keep)
            self.partner.blockSignals(False)
        self._refresh()

    def _refresh(self, *_):
        """Preview = the REAL stamp on a scratch copy; anything illegal disables Stamp
        and says why in the compiler-teaching voice."""
        a = self._archetype()
        if a is None:
            return
        key, who, target = self.selection()
        problem = ""
        if not who:
            problem = ("This field has no free named [[npc]]s — add one in the Editor "
                       "tab's NPCs group first.")
        elif a.get("needs_target") and not self._members:
            problem = (f"The {key} archetype fights an EXISTING unit — cancel and seat "
                       "its enemy first (＋ Add unit… or another archetype).")
        elif a.get("needs_partner") and not target:
            problem = (f"The {key} archetype seats a PAIR — it needs two free named "
                       "[[npc]]s (add another first).")
        elif a.get("needs_target") and not target:
            problem = "Pick the enemy unit."
        if problem:
            self.note.setText(problem)
            widgets.set_state(self.note, "warn")
            self.preview.setText("")
            self._ok.setEnabled(False)
            return
        import copy
        scratch = copy.deepcopy(self._raw)
        try:
            behaviorscan.stamp_archetype(scratch, key, who, target)
        except Exception as e:                     # noqa: BLE001 -- surface it, never crash
            self.note.setText(str(e))
            widgets.set_state(self.note, "warn")
            self.preview.setText("")
            self._ok.setEnabled(False)
            return
        lines = self._ladder_lines(scratch, who)
        if a.get("needs_partner") and target:      # a PAIR stamp writes two ladders --
            lines += [""] + self._ladder_lines(scratch, target)   # show them both
        minted = (scratch.get("marker") or [])[len(self._raw.get("marker") or []):]
        if minted:
            names = ", ".join(str(m.get("name")) for m in minted)
            lines += ["", f"+ mints the {names} route — drag its points with Stage edit"]
        self.preview.setText("\n".join(lines))
        self.note.setText("One undo step (Ctrl+Z); shape the minted geometry on the stage.")
        widgets.set_state(self.note, "")
        self._ok.setEnabled(True)

    @staticmethod
    def _ladder_lines(raw, unit):
        rows = behaviorscan.ladder_model(raw, unit)
        out = [f"{unit}:"]
        for r in rows:
            cond = " AND ".join(r["conds"]) if r["conds"] else "always"
            line = f"  {r['index']}  {cond}  →  {r['verb']}"
            if r["detail"]:
                line += f" {r['detail']}"
            if r["decos"]:
                line += "   · " + " · ".join(r["decos"])
            out.append(line)
        return out

    def accept(self):                              # noqa: N802 (Qt override)
        if not self._ok.isEnabled():
            return                                 # Enter on an illegal state stamps nothing
        self._picked = self.selection()
        super().accept()

    def picked(self):
        """(key, npc, target-or-partner) after an accepted run, else None."""
        return self._picked


class BranchWizard(QDialog):
    """＋ Branch grown into a small teaching picker: a blank row (the old behaviour)
    first, then the BRANCH archetypes — one proven guarded row each — with their teach
    text, a target picker when the row binds one, and a verbatim preview of the exact
    branch that will land (``branch_archetype_body`` through the ladder's own
    formatters). Same modal-seam contract as the big wizard."""

    def __init__(self, pal, raw, unit_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Add a branch — {unit_name}")
        self._raw = raw
        self._unit = unit_name
        self._picked = None
        self._members = [m for u in raw["behavior"]["unit"]
                         for m in behaviorscan.BT.row_members(u)
                         if m not in behaviorscan.BT.row_members(
                             behaviorscan._unit_row(raw, unit_name) or {})] \
            if behaviorscan.has_behavior(raw) else []
        outer = QVBoxLayout(self)
        outer.setSpacing(8)
        self.list = QListWidget()
        self.list.setAccessibleName("Branch archetypes")
        self.list.addItem("Blank branch — author it yourself")
        for a in behaviorscan.BRANCH_ARCHETYPES:
            self.list.addItem(a["name"])
        outer.addWidget(self.list, 1)
        self.teach = widgets.caption("")
        self.teach.setWordWrap(True)
        outer.addWidget(self.teach)
        trow = QWidget()
        th = QHBoxLayout(trow)
        th.setContentsMargins(0, 0, 0, 0)
        th.setSpacing(8)
        th.addWidget(widgets.role_label("Against", "caption"))
        self.vs = QComboBox()
        self.vs.setAccessibleName("Branch target")
        self.vs.addItems(["player"] + self._members)
        th.addWidget(self.vs, 1)
        self._vs_row = trow
        outer.addWidget(trow)
        self.preview = QLabel("")
        self.preview.setProperty("mono", True)
        self.preview.setAccessibleName("Branch preview")
        outer.addWidget(self.preview)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                              | QDialogButtonBox.StandardButton.Cancel)
        self._ok = bb.button(QDialogButtonBox.StandardButton.Ok)
        self._ok.setText("Add")
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        outer.addWidget(bb)
        self.list.currentRowChanged.connect(self._refresh)
        self.vs.currentIndexChanged.connect(self._refresh)
        self.list.setCurrentRow(0)
        widgets.fit_dialog(self, ch=76, list_rows=len(behaviorscan.BRANCH_ARCHETYPES) + 1,
                           lines=8)

    def _archetype(self):
        i = self.list.currentRow() - 1             # row 0 = the blank branch
        rows = behaviorscan.BRANCH_ARCHETYPES
        return rows[i] if 0 <= i < len(rows) else None

    def selection(self):
        a = self._archetype()
        if a is None:
            return ("blank", None)
        target = self.vs.currentText() or None if a.get("needs_target") else None
        return (a["key"], target)

    def _refresh(self, *_):
        a = self._archetype()
        if a is None:                              # the blank row
            self.teach.setText("An inert row above the fallback: its guard flag starts "
                               "unraised, so it does nothing until you shape it in the "
                               "branch editor (which opens on Add).")
            self._vs_row.setVisible(False)
            self.preview.setText("")
            self._ok.setEnabled(True)
            return
        self.teach.setText(a["teach"])
        self._vs_row.setVisible(bool(a.get("needs_target")))
        want = ([] if a.get("unit_only") else ["player"]) + self._members
        have = [self.vs.itemText(i) for i in range(self.vs.count())]
        if want != have:                           # swing_at binds a UNIT; the player row
            keep = self.vs.currentText()           # appears only where it is legal
            self.vs.blockSignals(True)
            self.vs.clear()
            self.vs.addItems(want)
            if keep in want:
                self.vs.setCurrentText(keep)
            self.vs.blockSignals(False)
        if a.get("needs_target") and not want:
            self.teach.setText(f"{a['teach']}\n\nThis row strikes another UNIT — seat "
                               "a second behavior unit first.")
            self.preview.setText("")
            self._ok.setEnabled(False)
            return
        key, target = self.selection()
        body = behaviorscan.branch_archetype_body(self._raw, self._unit, key, target)
        conds = [behaviorscan.fmt_cond(c) for c in body.get("when") or []]
        verb, detail = behaviorscan.fmt_action(body.get("do") or {})
        line = (" AND ".join(conds) or "always") + f"  →  {verb}"
        if detail:
            line += f" {detail}"
        decos = behaviorscan._decos(body)
        if decos:
            line += "   · " + " · ".join(decos)
        self.preview.setText(line)
        self._ok.setEnabled(True)

    def accept(self):                              # noqa: N802 (Qt override)
        self._picked = self.selection()
        super().accept()

    def picked(self):
        return self._picked


class BehaviorDoc(QWidget):
    """The Behavior tab. The shell feeds it the OPEN field's parsed dict (``show_field``) on
    tab show / tree select -- never a file read; the doc's ONLY disk touches are the two
    user-invoked lanes, Compile (the saved file through the real compiler) and the first
    Sweep (the saved field's walkmesh; re-sweeps ride the warm mesh)."""

    _compile_done = Signal(object)                 # CompileResult (worker -> GUI thread)
    _sweep_done = Signal(object)                   # (gen, SweepResult, wmesh|None) -> GUI thread

    def __init__(self, pal, *, scale=100, on_edit=None):
        super().__init__()
        self.pal = pal
        self._scale = scale
        self.on_edit = on_edit                     # (member, label) after each committed edit --
        #                                            the shell's touch/checkpoint/re-feed hook
        self._ask_unit = self._ask_unit_dialog     # the modal seam: tests/snaps inject, prod asks
        self._ask_stamp = self._ask_stamp_dialog   # the archetype WIZARD (one surface, one seam)
        self._ask_branch = self._ask_branch_dialog  # ...and its little sibling on ＋ Branch
        self._view = None                          # what the projections RENDER: the open dict,
        self._readonly = False                     # or a [siege] field's desugared copy (read-only
        #                                            -- the [siege] block owns the behavior table)
        self._member = None
        self._path = None
        self._dirty = False
        self._raw = None
        self._result = None                        # the last CompileResult -- STATE, not widget
        #                                            visibility (a hidden tab must not forget it)
        self._selected_unit = None
        self._busy = False
        self._guide_state = "nofield"
        self._wmesh = None                         # the sweep lane's cached walkmesh (per field)
        self._sweep_busy = False
        self._sweep_armed = False                  # first EXPLICIT sweep arms auto re-sweeps --
        #                                            after it, edits re-judge on the worker with
        #                                            the warm mesh (no uninvited disk I/O before)
        self._sweep_gen = 0                        # bumps on field switch/close: a worker still
        #                                            in flight for the OLD field lands stale and
        #                                            is dropped, never painted on the new one
        self._sim = None                           # rung E1: the live behaviorsim.Sim (or None)
        self._sim_pos = 0
        self._rail_user = False                    # the cast rail auto-fits per field; a user
        self._rail_setting = False                 # DRAG (not a squeeze) holds until the next
        self._rail_pending = False                 # field switch
        self._sim_timer = QTimer(self)
        self._sim_timer.setInterval(33)            # ~30 ticks/s -- the engine's own rate
        self._sim_timer.timeout.connect(lambda: self._sim_show(self._sim_pos + 1))
        self._compile_done.connect(self._finish_compile)
        self._sweep_done.connect(self._finish_sweep)
        self._resweep_timer = QTimer(self)
        self._resweep_timer.setSingleShot(True)
        self._resweep_timer.setInterval(500)
        self._resweep_timer.timeout.connect(self._resweep)
        # The Instruments column is NOT one of this doc's panes: the shell docks it into its
        # INSPECTOR while this tab shows (owner's call -- a third in-doc column starved the
        # ladder of width). Built here, owned here; the shell only mounts/unmounts it.
        self.instruments = self._build_instruments()
        self._stack = QStackedLayout(self)
        self._stack.setContentsMargins(0, 0, 0, 0)
        self._guide_page = self._build_guide(self._guide_state)
        self._stack.addWidget(self._guide_page)
        self._content = self._build_content()
        self._stack.addWidget(self._content)
        self._stack.setCurrentWidget(self._guide_page)

    # -- pages --
    def _build_guide(self, state):
        glyph = icons.pixmap("script", self.pal["muted"], 46)
        if state == "nobehavior":
            return widgets.empty_state(
                "", "This field has no [behavior] block",
                teach="Behavior gives named [[npc]]s compiled AI — patrols, chases, alarms, "
                      "combat — as priority branches you author by hand or stamp from an "
                      "archetype (docs/BEHAVIOR.md). The OTHER route is one [siege] block: "
                      "a whole tower-defense minigame whose army is GENERATED at build — "
                      "this tab then renders that army read-only, and the Editor form's "
                      "[siege] section is its editing surface. One field, one route: "
                      "[siege] owns the behavior table (examples/siege is the shipped one).",
                actions=[("Add a behavior unit…", self._add_unit),
                         ("Stamp an archetype…", self._stamp_archetype),
                         ("Generate a [siege] minigame…", self._stamp_siege)],
                icon_pixmap=glyph)
        return widgets.empty_state(                # "nofield" -- the front door
            "", "Behavior renders a field's [behavior] block",
            teach="Open a campaign or a loose field and select a field in the tree — its "
                  "behavior units, ladders, and stage geometry render here, read-only.",
            icon_pixmap=glyph)

    def _show_guide(self, state):
        self._guide_state = state
        old = self._guide_page
        self._guide_page = self._build_guide(state)
        self._stack.addWidget(self._guide_page)
        self._stack.setCurrentWidget(self._guide_page)
        self._stack.removeWidget(old)
        old.deleteLater()

    def _build_content(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(10, 8, 10, 10)
        outer.setSpacing(8)
        head = QHBoxLayout()
        head.setSpacing(10)
        self.head_title = widgets.role_label("Behavior", "head")
        head.addWidget(self.head_title)
        # ElideLabel, not a plain caption: a long summary (the [siege] read-only banner)
        # must YIELD width, never floor the whole doc's minimum (snap-caught: it put a
        # 2300px sizeHint under the siege surface and starved the cast rail)
        self.head_sum = widgets.ElideLabel("")
        head.addWidget(self.head_sum, 1)
        outer.addLayout(head)
        split = QSplitter()
        split.setChildrenCollapsible(False)
        # cast rail (+ the Add-unit door)
        cast_col = QWidget()
        cv = QVBoxLayout(cast_col)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.setSpacing(4)
        self.cast = QTreeWidget()
        self.cast.setHeaderHidden(True)
        self.cast.setAccessibleName("Behavior cast")
        self.cast.setAccessibleDescription(
            "Units, groups, pools, and data (counters, tables, schedules, scans, HUD strips). "
            "Selecting a unit shows its ladder and lights its radii on the stage.")
        self.cast.itemSelectionChanged.connect(self._on_cast_select)
        cv.addWidget(self.cast, 1)
        self.add_unit_btn = QPushButton("＋ Add unit…")
        self.add_unit_btn.setProperty("role", "quiet")
        self.add_unit_btn.setToolTip("Give a named [[npc]] a behavior tree (a minimal legal "
                                     "ladder: a death branch + a hold fallback).")
        self.add_unit_btn.clicked.connect(self._add_unit)
        cv.addWidget(self.add_unit_btn)
        self.archetype_btn = QPushButton("＋ Archetype…")
        self.archetype_btn.setProperty("role", "quiet")
        self.archetype_btn.setToolTip(
            "Stamp a whole proven tree onto a named [[npc]] — sentry (watch + alarm), "
            "patroller (a minted beat), civilian (panics and flees). One undo step; "
            "shape the minted geometry with Stage edit.")
        self.archetype_btn.clicked.connect(self._stamp_archetype)
        cv.addWidget(self.archetype_btn)
        split.addWidget(cast_col)
        # center: the unit bar OUTSIDE the scroll (right-aligned controls inside an h-scrolling
        # container live off-screen -- snap-caught), then ladder over stage (stacked -- the
        # ratified answer to open question #1) with the branch editor between them
        center = QWidget()
        cl = QVBoxLayout(center)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(4)
        bar = QWidget()
        bh = QHBoxLayout(bar)
        bh.setContentsMargins(10, 4, 10, 0)
        bh.setSpacing(10)
        self.unit_title = widgets.role_label("—", "cardtitle")
        bh.addWidget(self.unit_title)
        self.unit_stats = widgets.ElideLabel("", min_ch=12)   # yields width, but never to
        bh.addWidget(self.unit_stats, 1)                      # NOTHING (12ch ≈ "4 hp · 6 br…")
        self.add_branch_btn = QPushButton("＋ Branch")
        self.add_branch_btn.setProperty("role", "quiet")
        self.add_branch_btn.setToolTip("Insert a new branch just above the fallback row "
                                       "(inert until you edit it — its guard flag starts unraised).")
        self.add_branch_btn.clicked.connect(self._add_branch)
        bh.addWidget(self.add_branch_btn)
        self.remove_unit_btn = QPushButton("− Unit")
        self.remove_unit_btn.setProperty("role", "quiet")
        self.remove_unit_btn.setToolTip("Remove this behavior unit (the [[npc]] stays; "
                                        "Ctrl+Z undoes).")
        self.remove_unit_btn.clicked.connect(self._remove_unit)
        bh.addWidget(self.remove_unit_btn)
        self.edit_btn = QPushButton("✥ Stage edit")
        self.edit_btn.setProperty("role", "quiet")
        self.edit_btn.setCheckable(True)
        self.edit_btn.setToolTip(
            "Author on the stage: drag posts, route/refuge points, and centres; drag a "
            "ring's grip to resize its radius; right-click a route point to insert/delete. "
            "Every drop is one undo step (Ctrl+Z).")
        self.edit_btn.toggled.connect(self._toggle_stage_edit)
        bh.addWidget(self.edit_btn)
        self.sim_btn = QPushButton("▶ Simulate")
        self.sim_btn.setProperty("role", "quiet")
        self.sim_btn.setCheckable(True)
        self.sim_btn.setToolTip(
            "Step the tree offline: play/scrub a timeline, watch ▶ sweep the ladder rows "
            "and units move on the stage; click the stage to move the sim's player.\n"
            "AN APPROXIMATION, not in-game proof — walks are straight lines (no walkmesh), "
            "pooled units stay dormant, battle only logs. The strip lists every caveat.")
        self.sim_btn.toggled.connect(self._toggle_sim)
        bh.addWidget(self.sim_btn)
        cl.addWidget(bar)
        # rung E1: the tick-stepper strip (hidden until ▶ Simulate) — controls, the scrub
        # slider, and the honesty caption ON ITS FACE (offline ≠ in-game proof)
        self.sim_bar = QWidget()
        sv = QVBoxLayout(self.sim_bar)
        sv.setContentsMargins(10, 0, 10, 0)
        sv.setSpacing(2)
        srow = QHBoxLayout()
        srow.setSpacing(8)
        # Transport controls wear SVG icons (icons.py), never the unicode media glyphs —
        # U+23F1/U+23F8 fall back to the Windows emoji face and render as colour blobs
        # (snap-caught on the timer readout; owner's rule: no emoji, SVGs exist for this).
        self.sim_play = QPushButton()
        self.sim_play.setProperty("role", "quiet")
        self.sim_play.setCheckable(True)
        self.sim_play.setIcon(icons.icon("play", self.pal["text"]))
        self.sim_play.setAccessibleName("Play or pause the simulation")
        self.sim_play.setToolTip("Play / pause (30 ticks per second — the engine's own rate)")
        self.sim_play.toggled.connect(self._sim_play_toggled)
        srow.addWidget(self.sim_play)
        for glyph, n, tip in (("+1", 1, "Step one tick"),
                              ("+1 s", behaviorsim.TICKS_PER_SEC, "Step one second (30 ticks)")):
            b = QPushButton(glyph)
            b.setProperty("role", "quiet")
            b.setToolTip(tip)
            b.clicked.connect(lambda _=False, k=n: self._sim_show(self._sim_pos + k))
            srow.addWidget(b)
        self.sim_reset = QPushButton()
        self.sim_reset.setProperty("role", "quiet")
        self.sim_reset.setIcon(icons.icon("reset", self.pal["text"]))
        self.sim_reset.setAccessibleName("Back to tick 0")
        self.sim_reset.setToolTip("Back to tick 0 (boot)")
        self.sim_reset.clicked.connect(lambda: self._sim_show(0))
        srow.addWidget(self.sim_reset)
        self.sim_slider = QSlider(Qt.Orientation.Horizontal)
        self.sim_slider.setToolTip("Scrub the simulated timeline")
        self.sim_slider.valueChanged.connect(self._sim_scrub)
        # the scrub bar is the strip's central affordance: floor it so the labels can
        # never starve it to a sliver (snap-caught at 100 AND 150%)
        self.sim_slider.setMinimumWidth(int(120 * self._scale / 100))
        srow.addWidget(self.sim_slider, 1)
        self.sim_time = widgets.role_label("tick 0 · 0.0 s", "caption")
        self.sim_time.setProperty("mono", True)
        srow.addWidget(self.sim_time)
        sv.addLayout(srow)
        self.sim_event = widgets.ElideLabel("", mono=True)   # the latest event, its OWN line —
        sv.addWidget(self.sim_event)                         # never the slider's competitor
        self.sim_note = widgets.ElideLabel("")               # the honesty ledger's one-line face
        sv.addWidget(self.sim_note)
        self.sim_bar.hide()
        cl.addWidget(self.sim_bar)
        self._vsplit = QSplitter(Qt.Orientation.Vertical)
        self._vsplit.setChildrenCollapsible(False)
        self._ladder_actions = {
            "move": self._move_row, "edit": self._edit_branch, "delete": self._delete_row}
        self.ladder = LadderView(self.pal, actions=self._ladder_actions)
        lscroll = QScrollArea()
        lscroll.setWidgetResizable(True)
        lscroll.setWidget(self.ladder)             # h-bar stays as-needed: a denied width must
        lscroll.setFrameShape(QFrame.Shape.NoFrame)  # scroll, never clip (the round-13 law)
        self._vsplit.addWidget(lscroll)
        self.editor = BranchEditor(self.pal, on_apply=self._apply_branch,
                                   on_close=self._close_editor, check=self._check_branch)
        self.editor.hide()
        self._vsplit.addWidget(self.editor)
        self.canvas = StageCanvas(self.pal, scale=self._scale,
                                  on_move=self._on_stage_move,
                                  on_radius=self._on_stage_radius,
                                  on_insert=self._on_stage_insert,
                                  on_delete=self._on_stage_delete)
        self._vsplit.addWidget(self.canvas)
        k = self._scale / 100
        self._vsplit.setSizes([int(340 * k), 0, int(280 * k)])
        cl.addWidget(self._vsplit, 1)
        split.addWidget(center)
        split.setStretchFactor(1, 1)
        # Ask for LESS than the realistic ~700px budget at a 1280 window (snap-measured: a
        # request over the available width let Qt starve the CENTER pane while rails kept theirs).
        split.setSizes([int(170 * k), int(530 * k)])
        self._hsplit = split
        split.splitterMoved.connect(self._on_rail_drag)
        outer.addWidget(split, 1)
        return page

    def _build_instruments(self):
        """The Problems/Compile column. A PLAIN widget, no scroll wrapper of its own -- its
        host (the shell inspector) already scrolls, and its h-bar is off, so everything in
        here must wrap or scroll internally (the report box scrolls itself)."""
        col = QWidget()
        v = QVBoxLayout(col)
        v.setContentsMargins(0, 8, 0, 0)
        v.setSpacing(7)
        v.addWidget(widgets.role_label("PROBLEMS", "subtle"))
        self.problems_lbl = widgets.caption("")
        self.problems_lbl.setWordWrap(True)
        v.addWidget(self.problems_lbl)
        v.addWidget(widgets.role_label("WALKABILITY", "subtle"))
        srow = QHBoxLayout()
        srow.setSpacing(8)
        self.sweep_btn = QPushButton("Sweep routes")
        self.sweep_btn.setToolTip(
            "Sweep every route leg and pursuit family against the field's walkmesh — "
            "jams paint on the stage at the exact spot. Walkmesh from the SAVED file; "
            "geometry from the open document. After the first sweep, edits re-judge "
            "automatically.")
        self.sweep_btn.clicked.connect(lambda: self.sweep_now())
        srow.addWidget(self.sweep_btn)
        srow.addStretch(1)
        v.addLayout(srow)
        self.sweep_note = widgets.caption("")      # the summary + jam lines (error tier)
        self.sweep_note.setWordWrap(True)
        v.addWidget(self.sweep_note)
        self.sweep_warns = widgets.caption("")     # warnings + hints on their OWN tier -- one
        self.sweep_warns.setWordWrap(True)         # label would paint every hint jam-red
        v.addWidget(self.sweep_warns)
        v.addWidget(widgets.role_label("COMPILE", "subtle"))
        row = QHBoxLayout()
        row.setSpacing(8)
        self.compile_btn = QPushButton("Compile (dry)")
        self.compile_btn.setToolTip(
            "Dry-compile the SAVED field.toml through the real behavior compiler — the "
            "blackboard map, flag indices, and the byte histogram. Writes nothing.")
        self.compile_btn.clicked.connect(lambda: self.compile_now())
        row.addWidget(self.compile_btn)
        row.addStretch(1)
        v.addLayout(row)
        self.compile_note = widgets.caption("")
        self.compile_note.setWordWrap(True)
        v.addWidget(self.compile_note)
        self.flags_host = QWidget()
        self.flags_lay = QVBoxLayout(self.flags_host)
        self.flags_lay.setContentsMargins(0, 0, 0, 0)
        self.flags_lay.setSpacing(3)
        v.addWidget(self.flags_host)
        self.report_box = QPlainTextEdit()         # the app sheet makes any QPlainTextEdit the
        self.report_box.setReadOnly(True)          # mono well (log_bg + Cascadia)
        self.report_box.setAccessibleName("Compile report")
        self.report_box.setVisible(False)
        fm = QFontMetrics(self.report_box.font())
        self.report_box.setMinimumHeight(fm.lineSpacing() * 12)
        v.addWidget(self.report_box, 1)
        v.addStretch(0)
        return col

    # -- shell hooks --
    def crumb_label(self):
        return f"Behavior — {self._member}" if self._member else "Behavior"

    def set_scale(self, pct):
        self._scale = pct
        if hasattr(self, "canvas"):
            self.canvas.set_scale(pct)
            self.sim_slider.setMinimumWidth(int(120 * pct / 100))

    def retheme(self, pal):
        self.pal = pal
        if hasattr(self, "canvas"):
            self.canvas.retheme(pal)
            self.ladder.pal = pal
            self.sim_play.setIcon(icons.icon(
                "pause" if self.sim_play.isChecked() else "play", pal["text"]))
            self.sim_reset.setIcon(icons.icon("reset", pal["text"]))
        if self._stack.currentWidget() is self._guide_page:
            self._show_guide(self._guide_state)    # rebuild: the glyph pixmap is palette-tinted
        elif self._raw is not None and self._member:
            self._render()                         # chips/canvas repaint under the new palette

    # -- the feed (shell-pushed, in-memory, no file I/O) --
    def show_none(self):
        if self.sim_btn.isChecked():
            self.sim_btn.setChecked(False)
        self._member = self._path = self._raw = None
        self._set_result(None)                     # the docked inspector column must not keep a
        self.problems_lbl.setText("")              # dead project's report or problems
        widgets.set_state(self.problems_lbl, "")
        self._reset_sweep()
        self._show_guide("nofield")

    def show_field(self, member, raw, path=None, *, dirty=False):
        """Render the OPEN field's parsed dict. ``path`` (the saved file) feeds the Compile
        lane; ``dirty`` labels which truth the instruments would read."""
        same_field = member == self._member
        if not same_field and self.sim_btn.isChecked():
            self.sim_btn.setChecked(False)         # another field: the timeline is void
        self._member, self._raw, self._path, self._dirty = member, raw, path, dirty
        if not self._resolve_view():
            self._show_guide("nobehavior")
            return
        if not same_field:
            self._selected_unit = None
            self._set_result(None)                 # another field's report must not linger
            self._reset_sweep()                    # ...nor its walkmesh or painted verdicts
            self._rail_user = False                # a new field re-earns the rail auto-fit
        self._stack.setCurrentWidget(self._content)
        self._render(refit=not same_field)

    def _resolve_view(self):
        """What the projections render: the open dict, or a [siege] field's desugared copy
        (read-only). Sets the edit affordances to match; False = nothing renderable."""
        self._view, self._readonly = self._raw, False
        if not behaviorscan.has_behavior(self._raw):
            view = behaviorscan.siege_view(self._raw)
            if view is None:
                return False
            self._view, self._readonly = view, True
        why_off = ("This [siege] field's behavior is GENERATED, so the tab renders it "
                   "read-only. Edit the [siege] block in the Editor form — or delete it "
                   "there (or Ctrl+Z a fresh stamp) to author [behavior] by hand.")
        for b in (self.add_unit_btn, self.archetype_btn, self.add_branch_btn,
                  self.remove_unit_btn, self.edit_btn):
            b.setEnabled(not self._readonly)
            # a disabled button must SAY WHY (Qt shows tooltips on disabled widgets);
            # the live tooltip is stashed once and restored when editing returns
            if self._readonly:
                if b.property("livetip") is None:
                    b.setProperty("livetip", b.toolTip())
                b.setToolTip(why_off)
            elif b.property("livetip") is not None:
                b.setToolTip(b.property("livetip"))
        if self._readonly and self.edit_btn.isChecked():
            self.edit_btn.setChecked(False)        # stage edit writes; a view has no writes
        self.ladder.actions = {} if self._readonly else self._ladder_actions
        return True

    def _render(self, *, refit=False):
        raw = self._view if self._view is not None else self._raw
        cast = behaviorscan.cast_model(raw)
        names = [u["name"] for u in cast["units"]]
        if self._selected_unit not in names:
            self._selected_unit = names[0] if names else None
        self.head_title.setText(self._member or "Behavior")
        self.head_sum.setText(behaviorscan.summary(raw) + (
            "  ·  generated from [siege] — read-only (edit the [siege] block in the "
            "Editor form)" if self._readonly else ""))
        self._fill_cast(cast)
        if refit:
            self._fit_rail()                       # the rail asks for its own longest row
        self._fill_ladder(cast)
        self.canvas.set_model(
            behaviorscan.stage_model(raw), self._selected_unit, refit=refit,
            handles=behaviorscan.stage_handles(raw) if self.edit_btn.isChecked()
            and not self._readonly else None)
        problems = behaviorscan.validate_problems(raw)
        if problems:
            self.problems_lbl.setText("\n".join(f"• {p}" for p in problems))
            widgets.set_state(self.problems_lbl, "error")
        else:
            self.problems_lbl.setText("No structural problems.")
            widgets.set_state(self.problems_lbl, "")
        note = ("Compiled from the SAVED file — unsaved edits are not included. Save first "
                "for current numbers." if self._dirty else "")
        if not self._has_result():
            self.compile_note.setText(note or "Nothing compiled yet.")

    def _fill_cast(self, cast):
        self.cast.blockSignals(True)
        self.cast.clear()

        def sect(title):
            it = QTreeWidgetItem([title])
            it.setFlags(Qt.ItemFlag.ItemIsEnabled)   # a heading, not a choice
            self.cast.addTopLevelItem(it)
            return it

        selected_item = None
        units_it = sect("UNITS")
        for u in cast["units"]:
            bits = []
            if u.get("members"):
                bits.append(f"class ×{len(u['members'])}")
            if u["hp"] is not None:
                bits.append(f"{u['hp']} hp")
            if u["pooled"]:
                bits.append(f"pooled{' · ' + str(u['pool']) if u['pool'] else ''}")
            row = QTreeWidgetItem([u["name"] + ("   · " + " · ".join(bits) if bits else "")])
            tip = row.text(0)
            if u.get("members"):                   # the rail shows the count; hover names them
                tip += "\nmembers: " + ", ".join(u["members"])
            row.setToolTip(0, tip)                 # the rail elides; hover carries the full row
            row.setData(0, Qt.ItemDataRole.UserRole, ("unit", u["name"]))
            units_it.addChild(row)
            if u["name"] == self._selected_unit:
                selected_item = row
        for title, rows in (("GROUPS", [(g["name"], f"{len(g['members'])} members")
                                        for g in cast["groups"]]),
                            ("POOLS", [(p["name"], p["note"]) for p in cast["pools"]]),
                            ("DATA", [(d["name"], d["note"]) for d in cast["data"]])):
            if not rows:
                continue
            s = sect(title)
            for name, note in rows:
                it = QTreeWidgetItem([f"{name}   · {note}" if note else name])
                it.setToolTip(0, it.text(0))
                it.setData(0, Qt.ItemDataRole.UserRole, ("info", name))
                s.addChild(it)
        self.cast.expandAll()
        if selected_item is not None:
            self.cast.setCurrentItem(selected_item)
        self.cast.blockSignals(False)

    def _fill_ladder(self, cast):
        u = next((x for x in cast["units"] if x["name"] == self._selected_unit), None)
        stats = []
        if u:
            if u.get("members"):                   # a class: ONE program, every member runs it
                stats.append(f"one program shared by {len(u['members'])}")
            if u["hp"] is not None:
                stats.append(f"{u['hp']} hp")
            if u["speed"] is not None:
                stats.append(f"speed {u['speed']}")
            if u.get("speeds"):                    # per-member walk presets (class rows)
                stats.append("speeds " + "/".join(str(s) for s in u["speeds"]))
            n = u["branches"]
            stats.append(f"{n} branch{'es' if n != 1 else ''}")
            if u["pooled"]:
                stats.append("pooled")
        src = self._view if self._view is not None else self._raw
        rows = behaviorscan.ladder_model(src, self._selected_unit) \
            if self._selected_unit else []
        self.unit_title.setText(self._selected_unit or "—")
        self.unit_stats.setText(" · ".join(stats))
        self.ladder.set_rows(self._selected_unit, rows)

    # -- the cast rail's TAILOR: a pane denied its content's width elides every row --
    def _on_rail_drag(self, *_):
        if not self._rail_setting:
            self._rail_user = True                 # a DRAG (unlike a squeeze) is a preference

    def _fit_rail(self):
        """Ask the rail for its own longest row, capped: the 170px ctor default elided
        EVERY cast row's info bits at both CALIBRE rungs (snap-caught — "class ×3"
        rendered "class …", defeating the class-row face). Field switch only; a user
        drag holds until the next field."""
        if self._rail_user:
            return
        sizes = self._hsplit.sizes()
        total = sum(sizes)
        if total < 320:                            # never laid out yet: first show re-runs
            self._rail_pending = True              # (the Info Hub sidebar's allocation law)
            return
        self._rail_pending = False
        k = self._scale / 100
        want = (self.cast.sizeHintForColumn(0) + self.cast.indentation()
                + 2 * self.cast.frameWidth()
                + self.cast.verticalScrollBar().sizeHint().width() + 10)
        rail = max(int(150 * k), min(want, int(280 * k), total - int(430 * k)))
        if rail > 0 and abs(rail - sizes[0]) > 6:
            self._rail_setting = True
            try:
                self._hsplit.setSizes([rail, total - rail])
            finally:
                self._rail_setting = False

    def showEvent(self, ev):                       # noqa: N802 (Qt override)
        super().showEvent(ev)
        if self._rail_pending:                     # fed while hidden: fit on the real layout
            QTimer.singleShot(0, self._fit_rail)

    def _on_cast_select(self):
        items = self.cast.selectedItems()
        payload = items[0].data(0, Qt.ItemDataRole.UserRole) if items else None
        if payload and payload[0] == "unit" and payload[1] != self._selected_unit:
            self._selected_unit = payload[1]
            src = self._view if self._view is not None else self._raw
            self._fill_ladder(behaviorscan.cast_model(src))
            self.canvas.select_unit(payload[1])
            if self._sim is not None:              # re-mark ▶ on the fresh ladder rows
                self._sim_show(self._sim_pos)

    # -- rung B: edits (all through behaviorscan's pure ops; the shell checkpoints via on_edit) --
    def _after_edit(self, label):
        """One committed mutation of the open dict: re-render, then hand the shell its undo
        step. The doc renders FIRST so a standalone (shell-less) host still shows the edit."""
        if self.sim_btn.isChecked():               # an edited tree voids the sim's timeline
            self.sim_btn.setChecked(False)
        if not self._resolve_view():
            self._show_guide("nobehavior")         # the last unit was removed
        else:
            if self._stack.currentWidget() is self._guide_page:
                self._stack.setCurrentWidget(self._content)   # a [siege] stamp on a bare field
            self._render()
        if self.on_edit and self._member:
            self.on_edit(self._member, label)
        if self._sweep_armed and self._wmesh is not None:
            self._resweep_timer.start()            # the armed lane: re-judge on the warm mesh

    def _move_row(self, bi, delta):
        if not self._selected_unit:
            return
        self._close_editor()                       # indices shift under a structural edit
        behaviorscan.move_branch(self._raw, self._selected_unit, bi, delta)
        self._after_edit(f"reorder {self._selected_unit} branches")

    def _delete_row(self, bi):
        if not self._selected_unit:
            return
        self._close_editor()
        behaviorscan.delete_branch(self._raw, self._selected_unit, bi)
        self._after_edit(f"delete {self._selected_unit} branch {bi + 1}")

    def _ask_branch_dialog(self):
        """Prod's ＋ Branch mini-wizard (instance dialog, the modal-seam law); tests
        inject ``_ask_branch``. Returns ("blank"|key, target-or-None) or None."""
        dlg = BranchWizard(self.pal, self._raw, self._selected_unit, self)
        try:
            return dlg.picked() if dlg.exec() else None
        finally:
            dlg.deleteLater()

    def _add_branch(self):
        if not self._selected_unit:
            return
        picked = self._ask_branch()
        if not picked:
            return
        kind, target = picked
        if kind == "blank":
            at = behaviorscan.add_branch(self._raw, self._selected_unit)
            self._after_edit(f"add {self._selected_unit} branch")
            self._edit_branch(at)                  # a fresh branch opens ready to shape
        else:
            at = behaviorscan.stamp_branch(self._raw, self._selected_unit, kind, target)
            self._after_edit(f"stamp {kind} branch on {self._selected_unit}")

    def _edit_branch(self, bi):
        unit = self._selected_unit
        rows = behaviorscan.ladder_model(self._raw, unit) if unit else []
        if not unit or not 0 <= bi < len(rows):
            return
        branch = behaviorscan._unit_row(self._raw, unit)["branch"][bi]
        self.editor.open_branch(unit, bi, behaviorscan.branch_toml(branch))
        s = self._vsplit.sizes()                   # opening must not crush the stage to a sliver
        if s[1] < 120:                             # (snap-caught): take from the LADDER first,
            e = max(150, min(240, self.editor.sizeHint().height()))   # keep the canvas usable
            total = sum(s)
            canvas = max(140, min(s[2], total - e - 160))
            self._vsplit.setSizes([max(120, total - e - canvas), e, canvas])

    def _close_editor(self):
        self.editor.hide()
        self.editor.unit = self.editor.bi = None

    def _check_branch(self, text):
        """The editor's live readout: (branch, note, state) -- parse errors in red, doc-level
        validate() problems in the compiler's own words, else the quiet go-ahead."""
        branch, err = behaviorscan.parse_branch(text)
        if err:
            return None, err, "error"
        problems = behaviorscan.check_edit(self._raw, self.editor.unit, self.editor.bi, branch)
        if problems:
            return branch, "\n".join(f"• {p}" for p in problems), "warn"
        return branch, "Valid — Apply writes it into the open document.", ""

    def _apply_branch(self):
        unit, bi = self.editor.unit, self.editor.bi
        if unit is None:
            return
        branch, err = behaviorscan.parse_branch(self.editor.box.toPlainText())
        if err:
            self.editor.note.setText(err)
            widgets.set_state(self.editor.note, "error")
            return
        behaviorscan.set_branch(self._raw, unit, bi, branch)
        self._after_edit(f"edit {unit} branch {bi + 1}")

    def _ask_unit_dialog(self, names):
        """Prod's picker (an INSTANCE QInputDialog -- the static execs in C++ past every test
        patch); tests/snaps inject ``_ask_unit`` instead."""
        from PySide6.QtWidgets import QInputDialog
        dlg = QInputDialog(self)
        dlg.setWindowTitle("Add a behavior unit")
        dlg.setLabelText("Which [[npc]] gets a behavior tree?")
        dlg.setComboBoxItems(names)
        dlg.setOption(QInputDialog.InputDialogOption.UseListViewForComboBoxItems, True)
        return (dlg.textValue() if dlg.exec() else None)

    def _no_free_npcs_msg(self):
        """Why the npc picker is empty — playtest-caught: with ZERO npcs on the field the
        old all-taken wording ('Every named [[npc]] already has a behavior unit') described
        a cast that did not exist."""
        if any(n.get("name") for n in (self._raw.get("npc") or [])):
            return ("Every named [[npc]] already has a behavior unit — add another "
                    "[[npc]] first (the Editor tab's NPCs group).")
        return ("This field has no named [[npc]]s yet — behavior runs ON npcs. Add some "
                "in the Editor tab's NPCs group, then come back and stamp.")

    def _add_unit(self):
        if self._raw is None or self._readonly:
            return
        names = behaviorscan.npc_candidates(self._raw)
        if not names:
            self.problems_lbl.setText(self._no_free_npcs_msg())
            widgets.set_state(self.problems_lbl, "warn")
            return
        name = self._ask_unit(names)
        if not name:
            return
        behaviorscan.add_unit(self._raw, name)
        self._selected_unit = name
        if self._stack.currentWidget() is self._guide_page:   # first unit on a bare field
            self._stack.setCurrentWidget(self._content)
        self._after_edit(f"add behavior unit {name}")

    def _stamp_siege(self):
        """The [siege] authoring half: write the skeleton, render its read-only view the
        same tick (the Editor form's [siege] section is the editing surface from here)."""
        if self._raw is None or self._readonly:
            return
        try:
            label = behaviorscan.stamp_siege(self._raw)
        except ValueError as e:
            self.problems_lbl.setText(str(e))
            widgets.set_state(self.problems_lbl, "warn")
            return
        self._after_edit(label)

    def _remove_unit(self):
        unit = self._selected_unit
        if not unit:
            return
        self._close_editor()
        behaviorscan.delete_unit(self._raw, unit)
        self._selected_unit = None
        self._after_edit(f"remove behavior unit {unit}")

    # -- rung D: archetype stamps (whole proven trees through ONE pure op + one undo step) --
    def _ask_stamp_dialog(self):
        """Prod's wizard (an INSTANCE dialog — the modal-seam law; tests/snaps inject
        ``_ask_stamp``). Returns (key, npc, target-or-partner) or None. The wizard
        owns every in-dialog legality question (guard-without-an-enemy, pair-without-
        a-partner) with the teach on its face — only the zero-free-npc case refuses
        before the door opens (there is nothing to show)."""
        dlg = ArchetypeWizard(self.pal, self._raw, self)
        try:
            return dlg.picked() if dlg.exec() else None
        finally:
            dlg.deleteLater()

    def _stamp_archetype(self):
        if self._raw is None or self._readonly:
            return
        if not behaviorscan.npc_candidates(self._raw):
            self.problems_lbl.setText(self._no_free_npcs_msg())
            widgets.set_state(self.problems_lbl, "warn")
            return
        picked = self._ask_stamp()
        if not picked:
            return
        key, name, target = picked
        label = behaviorscan.stamp_archetype(self._raw, key, name, target)
        self._selected_unit = name
        if self._stack.currentWidget() is self._guide_page:   # first unit on a bare field
            self._stack.setCurrentWidget(self._content)
        self._after_edit(label)

    # -- rung E1: the offline tick-stepper. The Sim READS the doc and never writes it;
    # any edit exits sim mode (the timeline would be a lie about the new tree). --
    def _toggle_sim(self, on):
        if on:
            src = self._view if self._view is not None else self._raw
            if src is None or not behaviorscan.has_behavior(src):
                self.sim_btn.setChecked(False)
                return
            if self.edit_btn.isChecked():          # sim and stage-edit are exclusive modes
                self.edit_btn.setChecked(False)
            self._sim = behaviorsim.Sim(src)
            self._sim_pos = 0
            # the honesty ledger ON THE FACE, one line (the short tags), the full
            # sentences on hover — the 4-line wrap pushed the doc 140px wider
            self.sim_note.setFullText("offline approximation — "
                                      + " · ".join(self._sim.short)
                                      + " — hover for the full ledger")
            self.sim_note.setToolTip("\n".join(self._sim.notes))
            self.sim_event.setFullText("")
            self.sim_bar.show()
            self.canvas.set_sim_mode(True)
            self.canvas.on_sim_click = self._sim_move_player
            self._sim_show(0)
        else:
            self._sim_timer.stop()
            self.sim_play.setChecked(False)
            self._sim = None
            self.sim_bar.hide()
            self.canvas.set_sim_mode(False)
            self.canvas.on_sim_click = None
            self.ladder.set_sim_sel(None)

    def _sim_show(self, tick):
        if self._sim is None:
            return
        tick = max(0, int(tick))
        st = self._sim.at(tick)
        self._sim_pos = tick
        self.sim_slider.blockSignals(True)
        self.sim_slider.setMaximum(max(self.sim_slider.maximum(), self._sim.head,
                                       tick + behaviorsim.TICKS_PER_SEC))
        self.sim_slider.setValue(tick)
        self.sim_slider.blockSignals(False)
        t = f"tick {tick} · {tick / behaviorsim.TICKS_PER_SEC:.1f} s"
        if st["timer"] is not None:                # the word, not U+23F1 (emoji-face blob)
            t += f" · timer {st['timer']:.0f}s" + (" (frozen)" if st["timer_frozen"] else "")
        self.sim_time.setText(t)
        ev = self._sim.events[st["events"] - 1] if st["events"] else None
        self.sim_event.setFullText(
            f"{ev.tick / behaviorsim.TICKS_PER_SEC:.1f}s {ev.unit}: {ev.text}"
            if ev is not None else "")
        self.canvas.set_sim(st)
        sels = {u["sel"] for u in st["units"].values()
                if u["unit"] == self._selected_unit and u["sel"] >= 0}
        self.ladder.set_sim_sel(sels)

    def _sim_play_toggled(self, on):
        self.sim_play.setIcon(icons.icon("pause" if on else "play", self.pal["text"]))
        if on:
            self._sim_timer.start()
        else:
            self._sim_timer.stop()

    def _sim_scrub(self, v):
        if self._sim is not None:
            self._sim_show(v)

    def _sim_move_player(self, x, z):
        if self._sim is None:
            return
        self._sim.move_player(self._sim_pos, int(round(x)), int(round(z)))
        self._sim_show(self._sim_pos)

    # -- rung C: authoring on the stage (drops commit through behaviorscan's pure ops;
    # the canvas only reports — it never touches the raw dict) --
    def _toggle_stage_edit(self, on):
        if on and self.sim_btn.isChecked():        # the two stage modes are exclusive
            self.sim_btn.setChecked(False)
        self.canvas.set_edit(on)
        if self._raw is not None and behaviorscan.has_behavior(self._raw):
            self._render()                         # feed/clear the handle layer

    def _on_stage_move(self, hid, x, z):
        self._after_edit(behaviorscan.apply_move(self._raw, hid, x, z))

    def _on_stage_radius(self, rid, r):
        self._after_edit(behaviorscan.apply_radius(self._raw, rid, r))

    def _on_stage_insert(self, lid):
        self._after_edit(behaviorscan.insert_route_point(self._raw, lid))

    def _on_stage_delete(self, lid):
        try:
            label = behaviorscan.delete_route_point(self._raw, lid)
        except ValueError as e:                    # the 2-point floor: refuse and say why
            self.problems_lbl.setText(str(e))
            widgets.set_state(self.problems_lbl, "warn")
            return
        self._after_edit(label)

    # -- the Compile lane (the doc's only disk touch; user-invoked, worker thread) --
    def compile_now(self, *, sync=False):
        if self._busy or self._raw is None:
            return
        if not self._path:
            self.compile_note.setText("This document has no saved file yet — save it first, "
                                      "then compile.")
            return
        self._busy = True
        self.compile_btn.setEnabled(False)
        self.compile_btn.setText("Compiling…")
        if sync:                                   # the deterministic test/snap lane
            self._finish_compile(behaviorscan.dry_compile(self._path))
            return
        path = self._path
        threading.Thread(target=self._worker, args=(path,), daemon=True).start()

    def _worker(self, path):
        res = behaviorscan.dry_compile(path)
        try:
            self._compile_done.emit(res)           # RuntimeError-guarded: the doc may be dead
        except RuntimeError:
            pass

    def _finish_compile(self, res):
        self._busy = False
        self.compile_btn.setEnabled(True)
        self.compile_btn.setText("Compile (dry)")
        self._set_result(res)

    # -- the sweep lane (rung C): walkability verdicts painted in place. The FIRST press
    # is the doc's other user-invoked disk touch (the SAVED field's walkmesh); once armed,
    # every committed edit re-judges the OPEN geometry on the warm mesh, debounced, on a
    # worker -- the two-truths split, stated on the button.
    def sweep_now(self, *, sync=False):
        src = self._view if self._view is not None else self._raw
        if self._sweep_busy or src is None or not behaviorscan.has_behavior(src):
            return
        if self._wmesh is None and not self._path:
            self.sweep_note.setText("This document has no saved file yet — the walkmesh "
                                    "comes from disk, so save first, then sweep.")
            widgets.set_state(self.sweep_note, "warn")
            return
        self._sweep_busy = True
        self.sweep_btn.setEnabled(False)
        self.sweep_btn.setText("Sweeping…")
        import copy as _copy
        raw = _copy.deepcopy(src)                  # the worker must never race the GUI's dict;
        #                                            a [siege] view sweeps its GENERATED routes
        gen, path, wmesh = self._sweep_gen, self._path, self._wmesh
        if sync:                                   # the deterministic test/snap lane
            self._finish_sweep((gen, *self._sweep_work(path, raw, wmesh)))
            return
        threading.Thread(target=self._sweep_worker, args=(gen, path, raw, wmesh),
                         daemon=True).start()

    @staticmethod
    def _sweep_work(path, raw, wmesh):
        if wmesh is None:
            wmesh, err = behaviorscan.load_walkmesh(path)
            if wmesh is None:
                res = behaviorscan.SweepResult()
                res.error = f"no walkmesh resolved — {err}"
                return res, None
        return behaviorscan.sweep_geometry(raw, wmesh), wmesh

    def _sweep_worker(self, gen, path, raw, wmesh):
        res, mesh = self._sweep_work(path, raw, wmesh)
        try:
            self._sweep_done.emit((gen, res, mesh))    # RuntimeError-guarded: doc may be dead
        except RuntimeError:
            pass

    def _finish_sweep(self, payload):
        gen, res, wmesh = payload
        if gen != self._sweep_gen:
            return                                 # a stale field's verdicts never paint
        self._sweep_busy = False
        self.sweep_btn.setEnabled(True)
        self.sweep_btn.setText("Sweep routes")
        if wmesh is not None:
            self._wmesh = wmesh
        if not res.ok:
            self.sweep_note.setText(res.error or "Sweep failed.")
            widgets.set_state(self.sweep_note, "error")
            self.sweep_warns.setText("")
            self.canvas.set_verdicts(None)         # a failed sweep must not leave stale paint
            return
        self._sweep_armed = True
        self.canvas.set_verdicts(res)
        errs = [t for k, t in res.lines if k == "error"]
        rest = [t for k, t in res.lines if k != "error"]
        warns = sum(1 for k, _t in res.lines if k == "warn")
        bits = ([f"{len(errs)} jam{'s' if len(errs) != 1 else ''}"] if errs else []) \
            + ([f"{warns} warning{'s' if warns != 1 else ''}"] if warns else [])
        head = (" · ".join(bits) + " — painted on the stage.") if bits else ""
        self.sweep_note.setText("\n".join(([head] if head else [])
                                          + [f"• {t}" for t in errs]))
        widgets.set_state(self.sweep_note, "error" if errs else "")
        self.sweep_warns.setText("\n".join(f"• {t}" for t in rest))
        widgets.set_state(self.sweep_warns, "warn" if warns else "")

    def _resweep(self):
        if self._sweep_busy:
            self._resweep_timer.start()            # let the in-flight run land first
            return
        self.sweep_now()

    def _reset_sweep(self):
        """Field switch / project close: another field's mesh or verdicts must not linger."""
        self._sweep_gen += 1
        self._resweep_timer.stop()
        self._wmesh = None
        self._sweep_armed = False
        self._sweep_busy = False
        self.sweep_btn.setEnabled(True)
        self.sweep_btn.setText("Sweep routes")
        self.sweep_note.setText("")
        widgets.set_state(self.sweep_note, "")
        self.sweep_warns.setText("")
        widgets.set_state(self.sweep_warns, "")
        self.canvas.set_verdicts(None)

    def _has_result(self):
        return self._result is not None

    def _set_result(self, res):
        self._result = res
        while self.flags_lay.count():
            w = self.flags_lay.takeAt(0).widget()
            if w is not None:
                w.hide()                           # hide BEFORE the reparent -- see set_rows
                w.setParent(None)
                w.deleteLater()
        if res is None:
            self.report_box.setVisible(False)
            self.report_box.setPlainText("")
            self.compile_note.setText("Nothing compiled yet.")
            return
        if not res.ok:
            self.compile_note.setText("\n".join(f"• {p}" for p in res.problems)
                                      or "Compile failed.")
            widgets.set_state(self.compile_note, "error")
            self.report_box.setVisible(False)
            return
        widgets.set_state(self.compile_note, "")
        head = f"Compiles — {res.new_bytes:,} B of new bytecode" if res.new_bytes else "Compiles."
        if res.stable_hash:
            head += f" · hash {res.stable_hash[:8]}"
        if self._dirty:
            head += "\nRead from the SAVED file — unsaved edits not included."
        self.compile_note.setText(head)
        for name, idx in list(res.public_flags) + list(res.pool_flags):
            row = QWidget()
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(6)
            lab = widgets.role_label(f"{name} → {idx}", "caption")
            lab.setProperty("mono", True)
            h.addWidget(lab, 1)
            btn = QPushButton("Copy")              # short: the ~200px rail clipped the long form
            btn.setProperty("role", "quiet")
            btn.setToolTip(f"Copy `set_flag = [{idx}, 1]` — paste into a [[choice]] option row.")
            btn.clicked.connect(lambda _=False, i=idx:
                                QGuiApplication.clipboard().setText(f"set_flag = [{i}, 1]"))
            h.addWidget(btn)
            self.flags_lay.addWidget(row)
        text = res.report or ""
        if res.routed:
            text += "\n\nauto-routed legs:\n" + "\n".join(f"  {r}" for r in res.routed)
        if res.size_text:
            text += "\n\n" + res.size_text
        self.report_box.setPlainText(text.strip())
        self.report_box.setVisible(True)
