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
