"""Project a field's CONTENT onto the painted canvas for the paint template (Phase B).

The floor template (``guide.py``) shows where the FLOOR lands; this adds where each piece of CONTENT
lands -- NPCs, props, gateways, events, save points, ladders, jumps, dialogue-choice zones, cutscene
waypoints, camera zones, the player spawn -- as per-type marker geometry (a footprint + a height pole
for point content, a quad outline for zone content) plus a numbered legend pin. So the artist can see
exactly where each thing sits and how tall to paint around it.

Driven by a parsed ``field.toml`` (+ optional sibling ``scene.toml``), so it covers EVERY content type
regardless of what the Blender add-on can place spatially. bpy-free + stdlib-only (projects through
:mod:`ff9mapkit.scene.cam`); the rasterizer / CLI / Blender front-ends consume the geometry + legend
this returns. There is NO model-height metadata in the game data, so heights are an authored table
(:data:`HEIGHT_BY_NAME` / :data:`HEIGHT_BY_TYPE`, calibrated by screenshot inversion) that any block
overrides with ``height = N``.
"""

from __future__ import annotations

from . import cam as _cam

# --- height table (world units) -----------------------------------------------------------
# Calibrated 2026-06-16 by screenshot inversion in a known-camera scene: place a model on a known
# floor anchor, read its on-screen top, invert through the exact camera. ADVISORY (manual reads,
# ~±15%); every value is overridable per-block via ``height = N``. The human anchor (~560) is the
# reliable one -- two independent models agreed (Zidane 567 / townsman 558) and it matches the kit's
# earlier ~550 estimate. Heights are to the model's HIGHEST point (e.g. a moogle's pom, a tent's
# finial), which is what a paint pole should reserve.
HUMAN_HEIGHT = 560

HEIGHT_BY_NAME = {            # archetype / preset / prop name -> height (the most specific lookup)
    "moogle": 440, "mog": 440,
    "save_point": 440, "savepoint": 440,
    "chest": 300,
    "barrel": 400, "cask": 400,
    "tent": 680,
    "scroll": 150, "map": 150,
    "sign": 400,
    "feather": 200,
    "ladder": 700,
}

HEIGHT_BY_TYPE = {            # marker type -> fallback height (0 = a flat marker, no vertical pole)
    "npc": HUMAN_HEIGHT, "spawn": HUMAN_HEIGHT,
    "prop": 300, "savepoint": 440,
    "gateway": 0, "event": 0, "camzone": 0, "choice": 0, "waypoint": 0,
    "ladder": 0, "jump": 0,
}

# Footprint glyph per point type (the rasterizer interprets these); zone types draw an outline.
FOOTPRINT_SHAPE = {"npc": "circle", "prop": "square", "spawn": "star",
                   "waypoint": "cross", "savepoint": "circle"}


def resolve_height(item: dict) -> int:
    """World-unit height for a content item: explicit ``height`` > name (archetype/prop) > type."""
    if item.get("height") is not None:
        return int(item["height"])
    name = item.get("subtype")
    if name and str(name) in HEIGHT_BY_NAME:
        return HEIGHT_BY_NAME[str(name)]
    return HEIGHT_BY_TYPE.get(item["type"], 0)


# --- normalize a parsed field.toml (+ scene.toml) into a flat content list ----------------
def _xz(p):
    """A [x, z] (or [x, z, y]) point -> (int x, int z), dropping any height component."""
    return (int(round(p[0])), int(round(p[1])))


def _zone(z):
    """A list of [x, z] corners -> [(x, z), ...] ints (drops height); [] if not a point list."""
    if not isinstance(z, (list, tuple)):
        return []
    return [_xz(p) for p in z if isinstance(p, (list, tuple)) and len(p) >= 2]


def _merge_by_name(field_list, scene_list, key):
    """Yield (entry, spatial) pairs: each field entry joined to its scene.toml twin by ``name`` for the
    spatial ``key`` ('pos' or 'zone'). Scene-only entries (named, not in the field) are included too."""
    scene_list = scene_list or []
    by_name = {e.get("name"): e for e in scene_list if e.get("name")}
    seen = set()
    for e in field_list or []:
        sc = by_name.get(e.get("name"))
        spatial = e.get(key)
        if spatial is None and sc is not None:
            spatial = sc.get(key)
        seen.add(e.get("name"))
        yield e, spatial
    for e in scene_list:
        if e.get("name") not in seen:
            yield e, e.get(key)


def normalize_content(field_cfg: dict, scene_cfg: dict | None = None) -> list:
    """Flatten a parsed ``field.toml`` (+ optional ``scene.toml`` for the two-file split) into content
    items the projector understands. Each item:

        {type, footprint: "point"|"zone", pos|zone, height: int|None, subtype: str|None, label: str}

    ``subtype`` is the archetype/preset/prop name used for the height lookup; ``label`` is the display
    name for the legend. Positions are merged from the scene file by ``name`` (Godot-style split) when
    the field entry omits them. Order is stable so pin numbers are deterministic.
    """
    scene_cfg = scene_cfg or {}
    items: list = []

    for n, pos in _merge_by_name(field_cfg.get("npc", []), scene_cfg.get("npc", []), "pos"):
        if pos is None:
            continue
        sub = n.get("preset") or n.get("archetype") or n.get("model")
        items.append({"type": "npc", "footprint": "point", "pos": _xz(pos),
                      "height": n.get("height"), "subtype": sub,
                      "label": n.get("name") or (str(sub) if sub else "npc")})

    for pr, pos in _merge_by_name(field_cfg.get("prop", []), scene_cfg.get("prop", []), "pos"):
        if pos is None:
            continue
        sub = pr.get("prop") or pr.get("model")
        items.append({"type": "prop", "footprint": "point", "pos": _xz(pos),
                      "height": pr.get("height"), "subtype": sub,
                      "label": pr.get("name") or (str(sub) if sub else "prop")})

    for m, pos in _merge_by_name(field_cfg.get("marker", []), scene_cfg.get("marker", []), "pos"):
        if pos is None:
            continue
        items.append({"type": "waypoint", "footprint": "point", "pos": _xz(pos),
                      "height": m.get("height"), "subtype": None, "label": m.get("name") or "waypoint"})

    player = field_cfg.get("player") or scene_cfg.get("player")
    if isinstance(player, dict) and player.get("spawn") is not None:
        items.append({"type": "spawn", "footprint": "point", "pos": _xz(player["spawn"]),
                      "height": player.get("height"), "subtype": None, "label": "spawn"})

    for gw, zone in _merge_by_name(field_cfg.get("gateway", []), scene_cfg.get("gateway", []), "zone"):
        z = _zone(zone)
        if z:
            to = gw.get("to")
            items.append({"type": "gateway", "footprint": "zone", "zone": z, "height": None,
                          "subtype": None, "label": gw.get("name") or (f"-> {to}" if to is not None else "gateway")})

    for ev, zone in _merge_by_name(field_cfg.get("event", []), scene_cfg.get("event", []), "zone"):
        z = _zone(zone)
        if z:
            items.append({"type": "event", "footprint": "zone", "zone": z, "height": None,
                          "subtype": None, "label": ev.get("name") or "event"})

    for cz in field_cfg.get("camera_zone", []):
        z = _zone(cz.get("zone"))
        if z:
            items.append({"type": "camzone", "footprint": "zone", "zone": z, "height": None,
                          "subtype": None, "label": f"cam {cz.get('to_camera', '?')}"})

    for ch, zone in _merge_by_name(field_cfg.get("choice", []), scene_cfg.get("choice", []), "zone"):
        z = _zone(zone)
        if z:
            items.append({"type": "choice", "footprint": "zone", "zone": z, "height": None,
                          "subtype": None, "label": ch.get("name") or (f"choice @ {ch.get('npc')}" if ch.get("npc") else "choice")})

    for sp, zone in _merge_by_name(field_cfg.get("savepoint", []), scene_cfg.get("savepoint", []), "zone"):
        z = _zone(zone)
        if z:
            items.append({"type": "savepoint", "footprint": "zone", "zone": z,
                          "height": sp.get("height"), "subtype": "save_point", "label": sp.get("name") or "save point"})

    for la in field_cfg.get("ladder", []):
        z = _zone(la.get("zone"))
        climb = _xz(la["bottom"]) if isinstance(la.get("bottom"), (list, tuple)) else None
        climb_top = _xz(la["top"]) if isinstance(la.get("top"), (list, tuple)) else None
        if not z and climb is None:
            continue
        items.append({"type": "ladder", "footprint": "zone", "zone": z, "height": None,
                      "subtype": "ladder", "label": la.get("name") or "ladder",
                      "climb": climb, "climb_top": climb_top})

    for jp in field_cfg.get("jump", []):
        z = _zone(jp.get("zone"))
        if z:
            items.append({"type": "jump", "footprint": "zone", "zone": z, "height": None,
                          "subtype": None, "label": jp.get("name") or "jump"})

    return items


def markers_to_field_cfg(npcs=(), gateways=(), events=(), camzones=(), waypoints=(), spawn=None) -> dict:
    """Assemble the Blender add-on's collected marker dicts into a ``field_cfg`` that
    :func:`normalize_content` understands -- so the live modeling loop projects content the same way
    the field.toml-driven CLI does. The add-on can only place these 6 kinds; props/ladders/jumps/save
    points live only in the field.toml (and project via the CLI ``paint-template`` command)."""
    cfg = {"npc": list(npcs), "gateway": list(gateways), "event": list(events),
           "camera_zone": list(camzones), "marker": list(waypoints)}
    if spawn is not None:
        cfg["player"] = {"spawn": [int(spawn[0]), int(spawn[1])]}
    return cfg


# --- project the content list onto the canvas (px) ----------------------------------------
def _canvas_wh(cam: _cam.Cam, scale: int) -> tuple:
    w = int(cam.range[0]) if cam.range and cam.range[0] else 384
    h = int(cam.range[1]) if cam.range and cam.range[1] else 448
    return (w * scale, h * scale)


def _centroid(pts):
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def project_content(items: list, cam: _cam.Cam, scale: int = 4, *, footprint_px: int = 7) -> dict:
    """Project a normalized content list onto the canvas (top-left px, scaled). Returns::

        {"size": (W, H),
         "types": {type: {"footprints": [{shape, c:(cx,cy), r}],
                          "poles": [((cx0,cy0),(cx1,cy1))],
                          "zones": [[(cx,cy), ...]],   # closed outline (last connects to first)
                          "pins":  [{n, c:(cx,cy)}]}},
         "legend": [{pin, type, label, subtype, height, canvas:[cx,cy], off_canvas}]}

    Point content gets a footprint glyph + (if its resolved height > 0) a vertical pole projected from
    ``y=0`` to ``y=height`` -- foreshortened correctly at any pitch/yaw, the same machinery as the
    floor wall guides. Zone content gets a closed outline. Pins are numbered in list order. A pin whose
    anchor falls outside the canvas is flagged ``off_canvas`` (real for tunnels / off-screen content).
    """
    W, H = _canvas_wh(cam, scale)
    S = scale

    def px(x, y, z):
        cx, cy = _cam.to_canvas((x, y, z), cam)
        return (cx * S, cy * S)

    types: dict = {}
    legend: list = []

    def bucket(t):
        return types.setdefault(t, {"footprints": [], "poles": [], "zones": [], "pins": []})

    for n, item in enumerate(items, start=1):
        t = item["type"]
        b = bucket(t)
        h = resolve_height(item)
        if item["footprint"] == "point":
            x, z = item["pos"]
            feet = px(x, 0, z)
            b["footprints"].append({"shape": FOOTPRINT_SHAPE.get(t, "circle"), "c": feet,
                                    "r": footprint_px})
            if h > 0:
                b["poles"].append((feet, px(x, h, z)))
            anchor = feet
        else:  # zone
            zone = item["zone"]
            ring = [px(x, 0, z) for (x, z) in zone]
            if ring:
                b["zones"].append(ring)
            if zone:
                cx0, cz0 = _centroid(zone)
                anchor = px(cx0, 0, cz0)
                if t == "savepoint" and h > 0:            # the moogle stands in the save zone
                    b["poles"].append((anchor, px(cx0, h, cz0)))
            elif item.get("climb"):                       # a ladder with no trigger zone, just a climb
                anchor = px(item["climb"][0], 0, item["climb"][1])
            else:
                anchor = px(0, 0, 0)
            if t == "ladder" and item.get("climb") and item.get("climb_top"):
                bx, bz = item["climb"]
                tx, tz = item["climb_top"]
                b["poles"].append((px(bx, 0, bz), px(tx, 0, tz)))
        b["pins"].append({"n": n, "c": anchor})
        off = not (0 <= anchor[0] < W and 0 <= anchor[1] < H)
        legend.append({"pin": n, "type": t, "label": item.get("label", t),
                       "subtype": item.get("subtype"), "height": h,
                       "canvas": [round(anchor[0], 1), round(anchor[1], 1)], "off_canvas": off})

    return {"size": (W, H), "types": types, "legend": legend}


# --- rasterize the projected content to per-type PNGs (+ legend + manifest), pure stdlib --------
# Distinct color per content type (RGBA 0-255); zone colors match the Blender viewport where it has one
# (event amber, camera-zone blue) so the template reads the same as the add-on.
TYPE_COLOR = {
    "npc": (90, 210, 255, 255), "prop": (120, 220, 130, 255), "spawn": (90, 255, 120, 255),
    "waypoint": (160, 200, 255, 255), "gateway": (255, 100, 220, 255), "event": (255, 215, 40, 255),
    "camzone": (90, 160, 255, 255), "choice": (70, 220, 200, 255), "savepoint": (255, 230, 70, 255),
    "ladder": (255, 150, 40, 255), "jump": (255, 90, 40, 255),
}
TYPE_DESC = {
    "npc": "NPCs (footprint + height pole)", "prop": "Props (footprint + height pole)",
    "spawn": "Player spawn", "waypoint": "Cutscene waypoints", "gateway": "Gateway exit zones",
    "event": "Event trigger zones", "camzone": "Camera-switch zones", "choice": "Dialogue-choice zones",
    "savepoint": "Save points (zone + moogle pole)", "ladder": "Ladders (zone + climb)",
    "jump": "Jump take-off zones",
}
# draw order: flat zones underneath, point content on top, the player spawn topmost
CONTENT_ORDER = ["gateway", "event", "camzone", "choice", "jump", "ladder", "savepoint",
                 "prop", "waypoint", "npc", "spawn"]
# unit-circle offsets for a small octagon footprint (no math import needed)
_OCT = [(1.0, 0.0), (0.707, 0.707), (0.0, 1.0), (-0.707, 0.707), (-1.0, 0.0),
        (-0.707, -0.707), (0.0, -1.0), (0.707, -0.707)]


def _draw_footprint(buf, W, H, shape, c, r, color):
    """Draw a small OUTLINE footprint glyph (so the artist still sees the art under it)."""
    from . import placeholder as _ph
    cx, cy = c
    if shape == "square":
        p = [(cx - r, cy - r), (cx + r, cy - r), (cx + r, cy + r), (cx - r, cy + r)]
        for i in range(4):
            _ph.draw_line(buf, W, H, p[i], p[(i + 1) % 4], color, 2)
    elif shape in ("cross", "star"):
        _ph.draw_line(buf, W, H, (cx - r, cy), (cx + r, cy), color, 2)
        _ph.draw_line(buf, W, H, (cx, cy - r), (cx, cy + r), color, 2)
        if shape == "star":                                   # spawn: add the diagonals
            _ph.draw_line(buf, W, H, (cx - r, cy - r), (cx + r, cy + r), color, 2)
            _ph.draw_line(buf, W, H, (cx - r, cy + r), (cx + r, cy - r), color, 2)
    else:                                                     # circle (octagon outline)
        ring = [(cx + r * ox, cy + r * oy) for ox, oy in _OCT]
        for i in range(len(ring)):
            _ph.draw_line(buf, W, H, ring[i], ring[(i + 1) % len(ring)], color, 2)


def _rasterize_type(d: dict, color, W: int, H: int) -> bytearray:
    """One transparent buffer with a content type's geometry: zone outlines, height poles, footprints,
    and a small locator cross at each zone pin (point content already has a footprint there)."""
    from . import placeholder as _ph
    buf = bytearray(W * H * 4)
    for ring in d["zones"]:
        for i in range(len(ring)):
            _ph.draw_line(buf, W, H, ring[i], ring[(i + 1) % len(ring)], color, 2)
    for p0, p1 in d["poles"]:
        _ph.draw_line(buf, W, H, p0, p1, color, 2)
    for f in d["footprints"]:
        _draw_footprint(buf, W, H, f["shape"], f["c"], f["r"], color)
    if not d["footprints"]:                                   # zone type: mark its pin (centroid)
        for pin in d["pins"]:
            _draw_footprint(buf, W, H, "cross", pin["c"], 4, color)
    return buf


WALKMESH_RGBA = (235, 235, 245, 255)    # the REAL walkable-floor boundary (neutral, distinct from content)


def walkmesh_outline_segments(ff9_verts, tris, cam: _cam.Cam, scale: int) -> list:
    """Boundary edges of a walkmesh (its real floor OUTLINE) projected to canvas px. ``ff9_verts`` are
    world (x, y, z) points in the FF9 frame; ``tris`` are (a, b, c) vertex-index triples. The boundary =
    edges belonging to exactly one triangle (the perimeter + any holes / disjoint-floor outlines), so an
    arbitrary forked or hand-modeled walkmesh draws as its true shape, not a synthesized rectangle. The
    interior triangulation (shared edges) is dropped. bpy-free."""
    count: dict = {}
    for tri in tris:
        if len(tri) < 3:
            continue
        a, b, cc = int(tri[0]), int(tri[1]), int(tri[2])
        for u, v in ((a, b), (b, cc), (cc, a)):
            if u == v:
                continue                                  # doubled vertex (degenerate fan edge)
            key = (v, u) if u > v else (u, v)
            count[key] = count.get(key, 0) + 1

    def px(i):
        x, y, z = ff9_verts[i][0], ff9_verts[i][1], ff9_verts[i][2]
        cx, cy = _cam.to_canvas((x, y, z), cam)
        return (cx * scale, cy * scale)

    n = len(ff9_verts)
    return [(px(a), px(b)) for (a, b), c in count.items()
            if c == 1 and 0 <= a < n and 0 <= b < n]


_PS_JSX_TEMPLATE = '''\
// FF9 Map Kit -- paint-template layer importer for Adobe Photoshop (auto-generated).
// In Photoshop: File > Scripts > Browse... and pick this file. It builds ONE layered document from
// the PNGs beside it -- correct bottom-to-top order, each layer's opacity + name, already aligned --
// so you don't drag each PNG or reorder by hand. (Photoshop can't read the manifest.json directly;
// this script is the bridge.)
#target photoshop
(function () {
  var here = new File($.fileName).parent;
  var W = %(W)d, H = %(H)d;
  var L = [
%(rows)s
  ];
  var ru = app.preferences.rulerUnits;
  app.preferences.rulerUnits = Units.PIXELS;
  try {
    var doc = app.documents.add(W, H, 72, "%(base)s", NewDocumentMode.RGB, DocumentFill.TRANSPARENT);
    var starter = doc.artLayers[0];
    for (var i = 0; i < L.length; i++) {
      var f = new File(here + "/" + L[i].file);
      if (!f.exists) { continue; }
      var src = app.open(f);
      src.selection.selectAll();
      src.selection.copy();
      src.close(SaveOptions.DONOTSAVECHANGES);
      app.activeDocument = doc;
      doc.paste();                                  // same size as the doc -> pastes aligned at 0,0
      doc.activeLayer.name = L[i].name;
      doc.activeLayer.opacity = L[i].opacity;
    }
    // remove the initial blank layer -- but ONLY if it's still empty. Some Photoshop versions paste
    // the FIRST layer ONTO the empty starter (no new layer), so a blind remove would delete it.
    try {
      var bb = starter.bounds;
      if (String(bb[0]) == String(bb[2]) || String(bb[1]) == String(bb[3])) { starter.remove(); }
    } catch (e) {}
  } finally {
    app.preferences.rulerUnits = ru;
  }
})();
'''


def _photoshop_jsx(basename: str, W: int, H: int, entries: list) -> str:
    """An Adobe Photoshop ExtendScript that rebuilds the layered template from the per-layer PNGs beside
    it (bottom-to-top order + opacity + names, pre-aligned). The bridge from the generic manifest to a
    one-click 'File > Scripts > Browse...' import."""
    rows = ",\n".join(
        '    {file:"%s", name:"%s", opacity:%d}' % (e["file"], e["type"], int(round(e["opacity"] * 100)))
        for e in entries)
    return _PS_JSX_TEMPLATE % {"W": W, "H": H, "base": basename, "rows": rows}


def render_full_template(cam: _cam.Cam, frame, items: list, out_dir, *, basename: str = "paint_template",
                         scale: int = 4, nx: int = 8, nz: int = 8, walkmesh=None, base_image=None) -> list:
    """Write the FULL paint template for a field: the floor layers (grid / outline / height -- only when
    a ``frame`` is given, i.e. a synth field or a borrow with ``[camera.frame]``); the REAL walkmesh
    outline if ``walkmesh=(ff9_verts, tris)`` is passed (a fork's / modeled floor's true shape, not the
    synthesized rectangle); PLUS one transparent PNG per content type present (npcs/props/gateways/...),
    a ``<basename>.legend.json`` (pin -> name / height / canvas px / off-canvas), and ONE
    ``<basename>.manifest.json`` listing every layer bottom-to-top with its opacity. Returns the written
    paths (legend + manifest last). bpy-free + stdlib."""
    import json
    import os

    from . import guide as _guide
    from . import placeholder as _ph

    W, H = _canvas_wh(cam, scale)
    os.makedirs(out_dir, exist_ok=True)
    written, entries = [], []

    def _write_png(fn, buf):
        path = os.path.join(out_dir, fn)
        with open(path, "wb") as fh:
            fh.write(_ph._png_rgba(W, H, buf))
        written.append(path)

    if frame is not None:                                     # floor layers (single-source the drawing)
        wall_h = abs(frame.zb - frame.zf)
        for layer, opacity, desc in _guide.PAINT_TEMPLATE_LAYERS:
            buf = bytearray(W * H * 4)
            _guide._draw_template_layer(buf, W, H, layer, cam, frame, scale, nx, nz, wall_h)
            fn = f"{basename}_{layer}.png"
            _write_png(fn, buf)
            entries.append({"file": fn, "type": layer, "opacity": opacity, "blend": "normal",
                            "description": desc})

    if walkmesh is not None:                                  # the REAL walkmesh outline (forks / modeled)
        wm_verts, wm_tris = walkmesh
        segs = walkmesh_outline_segments(wm_verts, wm_tris, cam, scale)
        if segs:
            buf = bytearray(W * H * 4)
            for p0, p1 in segs:
                _ph.draw_line(buf, W, H, p0, p1, WALKMESH_RGBA, 2)
            _write_png(f"{basename}_walkmesh.png", buf)
            entries.append({"file": f"{basename}_walkmesh.png", "type": "walkmesh", "opacity": 0.9,
                            "blend": "normal", "description": "Walkable floor boundary (the real walkmesh)"})

    proj = project_content(items, cam, scale)                 # content layers, one PNG per present type
    for t in CONTENT_ORDER:
        d = proj["types"].get(t)
        if not d:
            continue
        _write_png(f"{basename}_{t}.png", _rasterize_type(d, TYPE_COLOR[t], W, H))
        entries.append({"file": f"{basename}_{t}.png", "type": t, "opacity": 1.0, "blend": "normal",
                        "description": TYPE_DESC.get(t, t)})

    legend = {"version": 1, "canvas_size": [W, H], "items": proj["legend"]}
    lfn = f"{basename}.legend.json"
    with open(os.path.join(out_dir, lfn), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(legend, fh, indent=2)
        fh.write("\n")
    written.append(os.path.join(out_dir, lfn))

    if base_image and os.path.isfile(os.path.join(out_dir, base_image)):   # the REAL art, as the base layer
        entries.insert(0, {"file": base_image, "type": "background", "opacity": 1.0, "blend": "normal",
                           "description": "the field's real background art -- paint/trace over it"})

    jfn = f"{basename}.import.jsx"                             # one-click Photoshop layered import
    with open(os.path.join(out_dir, jfn), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(_photoshop_jsx(basename, W, H, entries))
    written.append(os.path.join(out_dir, jfn))

    manifest = {"version": 1, "canvas_size": [W, H], "scale": scale, "layers": entries,
                "legend": lfn, "importer": jfn}
    mfn = f"{basename}.manifest.json"
    with open(os.path.join(out_dir, mfn), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(manifest, fh, indent=2)
        fh.write("\n")
    written.append(os.path.join(out_dir, mfn))
    return written
