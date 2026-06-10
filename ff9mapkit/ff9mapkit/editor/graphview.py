"""A visual node-link MAP of a campaign's field graph -- a tk Canvas view + a tk-free layout core.

The Campaign Editor's left navigator shows the chain as a TREE; this is the same connectivity as a
MAP: members are nodes, live gateways are arrows (dashed when story-gated), onward seams are dashed
stubs, with the same entry / unreachable / dead-end / needs-art cues as the tree. :func:`compute_layout`
is PURE over a :class:`campaign.CampaignGraph` (no tk) so the placement is unit-testable headless;
:class:`GraphView` wraps a scrollable Canvas that draws a layout and turns clicks into open-member
calls. Nothing here that isn't already derivable from the plan via ``campaign.campaign_graph``.

Layout: top-down BFS levels from the entry (depth 0 at the top), each level centred horizontally;
unreachable members are packed into a row below the reachable band. Edge endpoints are clipped to the
node borders so an arrow touches the rectangle regardless of the two nodes' relative positions.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LaidNode:
    name: str
    new_id: int
    mode: str
    x: float                # top-left
    y: float
    w: float
    h: float
    is_entry: bool
    reachable: bool
    dead_end: bool
    needs_export: bool

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2


@dataclass
class LaidEdge:
    frm: str
    to: str
    gated: bool
    entrance: int
    x1: float               # on the frm border
    y1: float
    x2: float               # on the to border
    y2: float


@dataclass
class LaidSeam:
    frm: str
    label: str
    nx: float               # stub start (the member's right edge)
    ny: float
    x: float                # label anchor
    y: float


@dataclass
class GraphLayout:
    nodes: list             # list[LaidNode]
    edges: list             # list[LaidEdge]
    seams: list             # list[LaidSeam]
    width: float
    height: float

    @property
    def by_name(self) -> dict:
        return {n.name: n for n in self.nodes}


def _clip(cx, cy, hw, hh, tx, ty):
    """The point on the border of the rect (centre cx,cy; half-extents hw,hh) along the ray toward (tx,ty)."""
    dx, dy = tx - cx, ty - cy
    if dx == 0 and dy == 0:
        return cx, cy + hh
    sx = hw / abs(dx) if dx else float("inf")
    sy = hh / abs(dy) if dy else float("inf")
    t = min(sx, sy)
    return cx + dx * t, cy + dy * t


def compute_layout(graph, *, node_w=160, node_h=50, hgap=38, vgap=72, margin=30, seam_gap=24):
    """Lay a CampaignGraph out top-down in BFS levels from the entry; unreachable members go in a row
    below. PURE -- returns a GraphLayout of absolute coords (y by depth, each level centred). An empty
    campaign yields a small empty canvas."""
    nodes_by_name = {n.name: n for n in graph.nodes}
    order = [n.name for n in graph.nodes]                 # member/id order == deterministic tie-break
    if not order:
        return GraphLayout([], [], [], width=margin * 2 + node_w, height=margin * 2 + node_h)

    out_by = {n.name: [oe["to"] for oe in n.out_edges] for n in graph.nodes}
    depth = {}                                            # BFS depth from the entry over live edges
    if graph.entry in nodes_by_name:
        depth[graph.entry] = 0
        queue = [graph.entry]
        while queue:
            cur = queue.pop(0)
            for nxt in out_by.get(cur, []):
                if nxt not in depth:
                    depth[nxt] = depth[cur] + 1
                    queue.append(nxt)
    max_reach = max(depth.values(), default=-1)
    for nm in order:                                      # unreachable -> a row below the reachable band
        depth.setdefault(nm, max_reach + 1)

    levels = {}
    for nm in order:                                      # group by depth, preserving member order in-row
        levels.setdefault(depth[nm], []).append(nm)
    widest = max(len(v) for v in levels.values())
    total_w = widest * node_w + (widest - 1) * hgap

    laid = {}
    for d in sorted(levels):
        row = levels[d]
        row_w = len(row) * node_w + (len(row) - 1) * hgap
        start_x = margin + (total_w - row_w) / 2
        y = margin + d * (node_h + vgap)
        for i, nm in enumerate(row):
            src = nodes_by_name[nm]
            laid[nm] = LaidNode(name=nm, new_id=src.new_id, mode=src.mode,
                                x=start_x + i * (node_w + hgap), y=y, w=node_w, h=node_h,
                                is_entry=src.is_entry, reachable=src.reachable,
                                dead_end=src.dead_end, needs_export=src.needs_export)

    edges = []
    for n in graph.nodes:
        a = laid[n.name]
        for oe in n.out_edges:
            b = laid.get(oe["to"])
            if b is None:
                continue
            x1, y1 = _clip(a.cx, a.cy, a.w / 2, a.h / 2, b.cx, b.cy)
            x2, y2 = _clip(b.cx, b.cy, b.w / 2, b.h / 2, a.cx, a.cy)
            edges.append(LaidEdge(frm=n.name, to=oe["to"], gated=oe["gated"],
                                  entrance=oe["entrance"], x1=x1, y1=y1, x2=x2, y2=y2))

    seams = []
    for n in graph.nodes:
        a = laid[n.name]
        for i, s in enumerate(n.seams):
            tgt = s.get("to_member") or ("WORLDMAP" if s.get("to_real") == "WORLDMAP" else s.get("to_real"))
            sy = a.cy + (i - (len(n.seams) - 1) / 2) * 18
            seams.append(LaidSeam(frm=n.name, label=f"{s.get('kind')} -> {tgt}",
                                  nx=a.x + a.w, ny=sy, x=a.x + a.w + seam_gap, y=sy))

    nlev = max(levels) + 1
    width = margin * 2 + total_w
    if seams:
        width = max(width, max(s.x for s in seams) + 180)
    height = margin * 2 + nlev * node_h + (nlev - 1) * vgap
    return GraphLayout(nodes=list(laid.values()), edges=edges, seams=seams, width=width, height=height)


def _round_rect(canvas, x1, y1, x2, y2, r, **kw):
    """A rounded rectangle as a smoothed polygon (Tk has no native rounded rect)."""
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return canvas.create_polygon(pts, smooth=True, **kw)


class GraphView:
    """A scrollable Canvas rendering a campaign's node-link map. Single-click a node to highlight it
    (+ a status line); double-click to open it (``on_open(name)``). Wheel / drag (middle button) pan."""

    def __init__(self, parent, palette, *, on_open=None):
        import tkinter as tk
        from tkinter import ttk

        self.pal = palette
        self.on_open = on_open
        self._layout = None
        self._graph = None
        self._current = None

        wrap = ttk.Frame(parent)
        wrap.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(wrap, background=palette["surface"], highlightthickness=0)
        vs = ttk.Scrollbar(wrap, orient="vertical", command=self.canvas.yview)
        hs = ttk.Scrollbar(wrap, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        vs.grid(row=0, column=1, sticky="ns")
        hs.grid(row=1, column=0, sticky="we")
        wrap.rowconfigure(0, weight=1)
        wrap.columnconfigure(0, weight=1)

        self.status = ttk.Label(parent, anchor="w", padding=(8, 4), foreground=palette["muted"],
                                text="Open a campaign to see its map.  "
                                     "green=entry · red=unreachable · amber=needs art · dashed=gated/seam")
        self.status.pack(fill="x")

        self.canvas.bind("<Button-1>", self._click)
        self.canvas.bind("<Double-Button-1>", self._double)
        self.canvas.bind("<ButtonPress-2>", lambda e: self.canvas.scan_mark(e.x, e.y))
        self.canvas.bind("<B2-Motion>", lambda e: self.canvas.scan_dragto(e.x, e.y, gain=1))
        self.canvas.bind("<MouseWheel>",
                         lambda e: self.canvas.yview_scroll(-1 if e.delta > 0 else 1, "units"))
        self.canvas.bind("<Shift-MouseWheel>",
                         lambda e: self.canvas.xview_scroll(-1 if e.delta > 0 else 1, "units"))

    # ------------------------------------------------------------------ public
    def render(self, graph, current=None):
        """Lay out + draw a CampaignGraph; ``current`` highlights the open member."""
        self._graph = graph
        self._current = current
        self._layout = compute_layout(graph)
        self._draw()

    def highlight(self, name):
        """Mark ``name`` as the open member (re-draws; campaigns are small)."""
        if self._layout is None:
            return
        self._current = name
        self._draw()
        self._set_status(name)

    def clear(self):
        self._graph = self._layout = self._current = None
        self.canvas.delete("all")

    # ------------------------------------------------------------------ drawing
    def _draw(self):
        c, pal, lay = self.canvas, self.pal, self._layout
        c.delete("all")
        if lay is None:
            return
        c.configure(scrollregion=(0, 0, lay.width, lay.height))
        for e in lay.edges:                               # edges under nodes
            kw = dict(fill=pal["muted"], width=2, arrow="last", arrowshape=(11, 13, 5))
            if e.gated:
                kw["dash"] = (5, 3)
            c.create_line(e.x1, e.y1, e.x2, e.y2, **kw)
        for s in lay.seams:
            c.create_line(s.nx, s.ny, s.x, s.y, fill=pal["muted"], dash=(2, 3))
            c.create_text(s.x + 4, s.y, text="~ " + s.label, anchor="w",
                          fill=pal["muted"], font=("Segoe UI", 9))
        for n in lay.nodes:
            self._node(n)

    def _node(self, n):
        c, pal = self.canvas, self.pal
        if not n.reachable:
            outline, width = pal["error"], 2
        elif n.needs_export:
            outline, width = pal["warn"], 2
        elif n.is_entry:
            outline, width = pal["success"], 2
        else:
            outline, width = pal["border"], 1
        current = (n.name == self._current)
        fill = pal["accent"] if current else pal["surface_btn"]
        tcol = pal["accent_fg"] if current else pal["text"]
        tag = f"node::{n.name}"
        _round_rect(c, n.x, n.y, n.x + n.w, n.y + n.h, r=11, fill=fill,
                    outline=outline, width=width, tags=("node", tag))
        c.create_text(n.cx, n.y + 17, text=n.name, fill=tcol,
                      font=("Segoe UI", 10, "bold"), tags=("node", tag))
        sub = f"id {n.new_id}" + ("" if n.mode == "borrow" else f" · {n.mode}")
        sub_col = pal["accent_fg"] if current else pal["muted"]
        c.create_text(n.cx, n.y + 34, text=sub, fill=sub_col, font=("Segoe UI", 9), tags=("node", tag))

    # ------------------------------------------------------------------ interaction
    def _node_at(self, ev):
        x, y = self.canvas.canvasx(ev.x), self.canvas.canvasy(ev.y)
        for item in self.canvas.find_overlapping(x - 1, y - 1, x + 1, y + 1):
            for t in self.canvas.gettags(item):
                if t.startswith("node::"):
                    return t[len("node::"):]
        return None

    def _click(self, ev):
        name = self._node_at(ev)
        if name:
            self.highlight(name)

    def _double(self, ev):
        name = self._node_at(ev)
        if name and self.on_open:
            self.on_open(name)

    def _set_status(self, name):
        node = (self._graph.by_name.get(name) if self._graph else None)
        if node is None:
            return
        flags = []
        if node.is_entry:
            flags.append("entry")
        if not node.reachable:
            flags.append("UNREACHABLE")
        elif node.dead_end:
            flags.append("dead-end")
        if node.needs_export:
            flags.append("needs art")
        tail = ("  ·  " + ", ".join(flags)) if flags else ""
        self.status.configure(
            text=f"{node.name}  ·  id {node.new_id} ({node.mode})  ·  "
                 f"{len(node.out_edges)} out / {len(node.in_edges)} in / {len(node.seams)} seam(s)"
                 f"{tail}   — double-click to edit")


def _smoke():
    """Headless-ish self-test: pure layout asserts (no display) + a Tk render+click if a display exists."""
    from .. import campaign
    M = campaign.Member
    members = [M(300, 30100, "ENT", "borrow", 11, "", "ENT/ent.field.toml", False),
               M(301, 30101, "COR", "borrow", 11, "", "COR/cor.field.toml", False),
               M(302, 30102, "LOST", "borrow", 11, "", "LOST/lost.field.toml", False)]
    plan = campaign.CampaignPlan(name="ICE", mod_folder="M", id_base=30100,
                                 flag_base=campaign.FIRST_SAFE_FLAG, flags_per_field=64,
                                 entry_name="ENT", entry_entrance=0, members=members,
                                 edges=[{"frm": "ENT", "to": "COR", "entrance": 2}],
                                 seams=[{"frm": "COR", "to_real": "WORLDMAP", "kind": "overworld",
                                         "note": "", "to_member": None}])
    g = campaign.campaign_graph(plan)
    lay = compute_layout(g)
    by = lay.by_name
    assert by["ENT"].y < by["COR"].y, "entry above its child"
    assert by["LOST"].y > by["COR"].y, "unreachable below the reachable band"
    assert len(lay.edges) == 1 and len(lay.seams) == 1
    print(f"graphview pure smoke ok: {len(lay.nodes)} nodes, {len(lay.edges)} edge(s), "
          f"{len(lay.seams)} seam(s), canvas {lay.width:.0f}x{lay.height:.0f}")

    import tkinter as tk
    from .theme import apply_theme
    root = tk.Tk()
    root.withdraw()
    pal = apply_theme(root)
    opened = []
    gv = GraphView(root, pal, on_open=opened.append)
    gv.render(g, current="ENT")
    items = gv.canvas.find_withtag("node::COR")
    assert items, "COR drawn"
    gv.highlight("COR")
    assert gv._current == "COR"
    gv._double(type("E", (), {"x": 0, "y": 0})())          # no node at (0,0) -> no open
    assert opened == []
    print("graphview tk smoke ok: rendered + highlighted")
    root.destroy()


if __name__ == "__main__":
    import sys
    if "--smoke" in sys.argv:
        _smoke()
