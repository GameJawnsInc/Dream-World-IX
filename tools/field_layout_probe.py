#!/usr/bin/env python3
"""Offline spatial-layout probe for a field.toml -- the agent's EYES for field layout.

Renders what a field's authored content actually looks like, before any deploy:

  topdown.png   -- the world X/Z plane seen from above (+Z/north UP, +X/east RIGHT): walkmesh floors,
                   true-scale collision footprints (48u controller / 96u object radius), facing arrows,
                   zone quads, the camera's position + look direction, a compass rose that ALSO shows
                   which way "screen-up" points for this camera.
  camview.png   -- the painted-canvas view through the exact engine projection (cam.to_canvas):
                   walkmesh outline, zone quads, each point marker with its projected HEIGHT pole
                   (so you see how big a model renders at its depth), labels.
  report.txt    -- the compass table (world cardinal -> on-screen direction), per-item world+canvas
                   positions with facing, and spacing/containment warnings (colliding actors, actors
                   hugging walls, off-mesh / off-canvas content, spawn inside a trigger zone).

WHY: FF9's frame trips up spatial reasoning -- the camera sits at NEGATIVE z looking toward +z, so
FRONT of a room = -z = DOWN-screen, north (+z, face byte 128) = up-screen ONLY at yaw 0, and real
cameras ship yaws up to +/-169 degrees. Never narrate a cardinal or eyeball spacing from raw
coordinates: run this, Read the PNGs, quote the compass.

Usage:  py tools/field_layout_probe.py <field.toml> [--out DIR] [--camera N] [--scale N]
"""
from __future__ import annotations

import argparse
import math
import os
import sys

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)

from ff9mapkit import build  # noqa: E402
from ff9mapkit.scene import bgi, cam as C, paint  # noqa: E402
from ff9mapkit.scene import routes as R  # noqa: E402  (the shared sweep core)

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover
    print("error: this probe needs Pillow (py -m pip install Pillow)", file=sys.stderr)
    sys.exit(2)

# --- the FF9 spatial conventions this tool exists to make visible --------------------------
# World frame: +x = east (right at yaw 0), -x = west; +z = north = the BACK of the room (away from
# the camera), -z = south = the FRONT (toward the camera/viewer). y = up.
# Facing byte (TurnInstant / [player] face / [[npc]] face): 0=south, 64=west, 128=north, 192=east.
CARDINAL_OF_FACE = {0: "south", 64: "west", 128: "north", 192: "east"}
CHAR_WIDTH_W = 100.0          # visual character width, world units (~2x collRad 48; label sizing only)

WORLD_CARDINALS = [           # name, unit (dx, dz)
    ("north (+z, back)", (0.0, 1.0)), ("east (+x)", (1.0, 0.0)),
    ("south (-z, front)", (0.0, -1.0)), ("west (-x)", (-1.0, 0.0)),
]


def face_to_dir(face: int) -> tuple:
    """Facing byte -> world-unit (dx, dz). 0=south (0,-1); 64=west (-1,0); 128=north (0,1); 192=east (1,0)."""
    th = face / 256.0 * 2.0 * math.pi
    return (-math.sin(th), -math.cos(th))


def face_name(face) -> str:
    if face is None:
        return "unset"
    f = int(face) % 256
    if f in CARDINAL_OF_FACE:
        return CARDINAL_OF_FACE[f]
    lo = (f // 64) * 64
    hi = (lo + 64) % 256
    return f"{CARDINAL_OF_FACE[lo]}-{CARDINAL_OF_FACE[hi]}"


def screen_angle(vec) -> float:
    """Canvas-space vector (x right, y DOWN) -> screen bearing degrees: 0=up, 90=right, 180=down, 270=left."""
    return math.degrees(math.atan2(vec[0], -vec[1])) % 360.0


def bearing_name(deg: float) -> str:
    names = ["up", "up-right", "right", "down-right", "down", "down-left", "left", "up-left"]
    return names[int((deg + 22.5) // 45) % 8]


# --- content + faces -----------------------------------------------------------------------
def face_queues(field_cfg: dict, scene_cfg: dict | None) -> dict:
    """Per-type queues of authored ``face`` bytes, in the SAME order paint.normalize_content emits its
    point markers (both iterate the raw lists identically), so faces zip onto markers positionally."""
    scene_cfg = scene_cfg or {}
    q = {"npc": [], "prop": [], "spawn": [], "arrival": []}
    for n, pos in paint._merge_by_name(field_cfg.get("npc", []), scene_cfg.get("npc", []), "pos"):
        if pos is not None:
            q["npc"].append(n.get("face"))
    for p, pos in paint._merge_by_name(field_cfg.get("prop", []), scene_cfg.get("prop", []), "pos"):
        if pos is not None:
            q["prop"].append(p.get("face"))
    player = field_cfg.get("player", {}) or {}
    if player.get("spawn") is not None or (scene_cfg.get("player", {}) or {}).get("spawn") is not None:
        q["spawn"].append(player.get("face"))
    for a in player.get("arrival", []) or []:
        q["arrival"].append(a.get("face"))
    return q


def attach_faces(items: list, queues: dict) -> None:
    used = {t: 0 for t in queues}
    for it in items:
        t = it["type"]
        if t in queues and it.get("footprint") == "point" and used[t] < len(queues[t]):
            it["face"] = queues[t][used[t]]
            used[t] += 1


# --- geometry helpers ----------------------------------------------------------------------
def point_in_poly(x, z, poly) -> bool:
    inside = False
    n = len(poly)
    for i in range(n):
        x1, z1 = poly[i]
        x2, z2 = poly[(i + 1) % n]
        if (z1 > z) != (z2 > z):
            xin = (x2 - x1) * (z - z1) / (z2 - z1) + x1
            if x < xin:
                inside = not inside
    return inside


seg_dist = R.seg_dist_xz               # shared package core (ff9mapkit.scene.routes)
boundary_edges_xz = R.boundary_edges_xz


# --- routes (a [[marker]] with `path`): scripted-walk polylines, swept for walkability ------
ROUTE_COLORS = [(255, 170, 60), (90, 200, 255), (190, 120, 255), (120, 230, 140),
                (255, 120, 160), (230, 220, 90)]


def collect_routes(field_cfg: dict, scene_cfg: dict | None) -> list:
    """[[marker]] entries carrying ``path = [[x,z], ...]`` (optional ``closed = true`` for a
    patrol ring) -- the polylines a scripted walker (Patrol ring, march, flee line) will
    actually walk. Build-inert like all markers; the probe draws + SWEEPS them."""
    routes = []
    for src in (field_cfg.get("marker", []) or [], (scene_cfg or {}).get("marker", []) or []):
        for m in src:
            path = m.get("path")
            if not path or len(path) < 2:
                continue
            routes.append({"name": m.get("name") or f"route{len(routes)}",
                           "path": [(float(p[0]), float(p[1])) for p in path],
                           "closed": bool(m.get("closed", False)),
                           "color": ROUTE_COLORS[len(routes) % len(ROUTE_COLORS)]})
    return routes


def sweep_route(route: dict, wmesh, bedges, step: float = 40.0) -> list:
    """Sweep one route dict's legs — thin wrapper over the shared package core
    (:func:`ff9mapkit.scene.routes.sweep_polyline`, which behavior lint also runs)."""
    return R.sweep_polyline(route["path"], wmesh, bedges, closed=route["closed"], step=step)


def analyze_routes(routes: list, wmesh, bedges) -> tuple:
    """(per-route legs, warnings). The sweep is the stuck-walker catcher: a Patrol/march
    leg with an off-mesh span WILL stall its unit against the boundary in-game."""
    swept, warns = {}, []
    for rt in routes:
        legs = sweep_route(rt, wmesh, bedges)
        swept[rt["name"]] = legs
        warns += R.describe_leg_problems(rt["name"], legs,
                                         wall_clearance=C.COLLISION_RADIUS_W)
    return swept, warns


# --- the compass (EMPIRICAL: measured through to_canvas, so borrowed .bgx cameras are exact) --
def compass(camera, ref_xz) -> dict:
    rx, rz = ref_xz
    base = C.to_canvas((rx, 0.0, rz), camera)
    rows = []
    for name, (dx, dz) in WORLD_CARDINALS:
        p = C.to_canvas((rx + dx * 300.0, 0.0, rz + dz * 300.0), camera)
        vec = (p[0] - base[0], p[1] - base[1])
        rows.append({"world": name, "vec": vec, "screen_deg": screen_angle(vec),
                     "screen": bearing_name(screen_angle(vec))})
    # which WORLD direction is exactly up-screen (sampled; local linearization is plenty here)
    best = None
    for d in range(0, 3600):
        th = math.radians(d / 10.0)
        dx, dz = math.sin(th), math.cos(th)          # th=0 -> +z (north), th=90 -> +x (east)
        p = C.to_canvas((rx + dx * 300.0, 0.0, rz + dz * 300.0), camera)
        up = base[1] - p[1]
        side = abs(p[0] - base[0])
        if up > 0 and (best is None or side / max(up, 1e-9) < best[0]):
            best = (side / max(up, 1e-9), d / 10.0)
    up_deg = (best[1] if best else 0.0) % 360.0      # world bearing: 0=north(+z), 90=east(+x)
    if up_deg >= 359.75:
        up_deg = 0.0
    wnames = ["north", "north-east", "east", "south-east", "south", "south-west", "west", "north-west"]
    return {"rows": rows, "screen_up_world_deg": up_deg,
            "screen_up_world": wnames[int((up_deg + 22.5) // 45) % 8]}


# --- analysis ------------------------------------------------------------------------------
def analyze(items, camera, wmesh, cw, ch, scrolling=False) -> tuple:
    """Per-item records + warnings. Returns (records, warnings). ``scrolling``: the
    canvas pans across a larger painting, so off-canvas content is NORMAL (the
    OFF-CANVAS check would flag everything beyond one static screen -- skip it)."""
    recs, warns = [], []
    bedges = []
    if wmesh is not None:
        wv = wmesh.world_verts()
        bedges = boundary_edges_xz(wv, [tuple(t.vtx) for t in wmesh.tris])
    zones = [(it["type"], it.get("label", it["type"]), it["zone"])
             for it in items if it.get("footprint") == "zone" and it.get("zone")]
    pts = [it for it in items if it.get("footprint") == "point" and it.get("pos")]

    for it in pts:
        x, z = it["pos"]
        cx, cy = C.to_canvas((x, 0.0, z), camera)
        _, _, depth = C.project((x, 0.0, z), camera)
        r = {"item": it, "canvas": (cx, cy), "depth": abs(depth), "flags": []}
        if not scrolling and not (0 <= cx < cw and 0 <= cy < ch):
            r["flags"].append("OFF-CANVAS")
            warns.append(f"{it['label']}: anchor projects OFF the canvas at ({cx:.0f},{cy:.0f})")
        if wmesh is not None:
            if wmesh.point_on_walkmesh(x, z) is None:
                r["flags"].append("OFF-MESH")
                if it["type"] in ("spawn", "arrival"):
                    warns.append(f"{it['label']}: ({x},{z}) is OFF the walkmesh -- the PLAYER lands "
                                 "here; spawning off-mesh strands/bricks (fix before deploying)")
                else:
                    warns.append(f"{it['label']}: ({x},{z}) is off the walkable floor -- fine for "
                                 "set dressing / against-the-wall NPCs (they still render + talk); "
                                 "the player can never walk closer than the mesh edge")
            elif bedges:
                d = min(seg_dist(x, z, a, b) for a, b in bedges)
                if d < C.COLLISION_RADIUS_W:
                    r["flags"].append("HUGS-WALL")
                    warns.append(f"{it['label']}: {d:.0f}u from a walkmesh edge -- the centre can't get "
                                 f"within ~{C.COLLISION_RADIUS_W:.0f}u of a wall (will be shoved inward)")
        for zt, zl, zpoly in zones:
            if it["type"] in ("spawn", "arrival", "npc") and zt in ("gateway", "event") \
                    and point_in_poly(x, z, zpoly):
                warns.append(f"{it['label']}: sits INSIDE {zt} zone '{zl}' -- will trigger it on contact"
                             + (" (instant warp on spawn!)" if it["type"] in ("spawn", "arrival") else ""))
        recs.append(r)

    for i in range(len(recs)):
        for j in range(i + 1, len(recs)):
            a, b = recs[i], recs[j]
            solid_a = a["item"]["type"] in ("npc", "prop", "spawn", "arrival")
            solid_b = b["item"]["type"] in ("npc", "prop", "spawn", "arrival")
            if not (solid_a and solid_b):
                continue
            d = math.hypot(a["item"]["pos"][0] - b["item"]["pos"][0],
                           a["item"]["pos"][1] - b["item"]["pos"][1])
            la, lb = a["item"]["label"], b["item"]["label"]
            if d < 2 * C.OBJECT_COLLISION_W:
                warns.append(f"{la} <-> {lb}: {d:.0f}u apart -- COLLIDING (object collision blocks at "
                             f"~{2 * C.OBJECT_COLLISION_W:.0f}u centre distance); they will jam/shove")
            elif d < 300:
                warns.append(f"{la} <-> {lb}: {d:.0f}u apart -- tight (walkable but cramped; real fields "
                             "space standing NPCs 300u+)")
            # screen overlap: spaced in world but stacked on screen (depth foreshortening)
            ga = math.hypot(a["canvas"][0] - b["canvas"][0], a["canvas"][1] - b["canvas"][1])
            wa = CHAR_WIDTH_W * camera.proj / max(a["depth"], 1e-6)
            wb = CHAR_WIDTH_W * camera.proj / max(b["depth"], 1e-6)
            if d >= 2 * C.OBJECT_COLLISION_W and ga < (wa + wb) / 2:
                warns.append(f"{la} <-> {lb}: {d:.0f}u apart in world but only {ga:.0f}px apart on screen "
                             "-- they visually overlap (one hides the other at this camera)")
    return recs, warns


# --- top-down render -----------------------------------------------------------------------
def render_topdown(path, items, camera, wmesh, comp, routes=(), swept=None):
    xs, zs = [], []
    wv = wmesh.world_verts() if wmesh is not None else []
    for v in wv:
        xs.append(v[0]); zs.append(v[2])
    for it in items:
        if it.get("footprint") == "point" and it.get("pos"):
            xs.append(it["pos"][0]); zs.append(it["pos"][1])
        for p in it.get("zone") or []:
            xs.append(p[0]); zs.append(p[1])
    for rt in routes:
        for p in rt["path"]:
            xs.append(p[0]); zs.append(p[1])
    if not xs:
        xs, zs = [-1000, 1000], [-1000, 1000]
    margin = 260.0
    x0, x1 = min(xs) - margin, max(xs) + margin
    z0, z1 = min(zs) - margin, max(zs) + margin
    scale = min(1100.0 / max(x1 - x0, 1), 1100.0 / max(z1 - z0, 1))
    W, H = int((x1 - x0) * scale) + 1, int((z1 - z0) * scale) + 1
    im = Image.new("RGB", (W, H + 26), (22, 24, 30))
    dr = ImageDraw.Draw(im, "RGBA")
    font = ImageFont.load_default()

    def px(x, z):                                       # +z UP on the image (matches yaw-0 screen)
        return ((x - x0) * scale, (z1 - z) * scale)

    g0 = int(math.floor(x0 / 500.0)) * 500
    for gx in range(g0, int(x1) + 500, 500):
        dr.line([px(gx, z0), px(gx, z1)], fill=(50, 54, 64), width=1)
        dr.text((px(gx, z1)[0] + 2, 2), str(gx), fill=(110, 115, 130), font=font)
    g0 = int(math.floor(z0 / 500.0)) * 500
    for gz in range(g0, int(z1) + 500, 500):
        dr.line([px(x0, gz), px(x1, gz)], fill=(50, 54, 64), width=1)
        dr.text((2, px(x0, gz)[1] + 2), str(gz), fill=(110, 115, 130), font=font)

    if wmesh is not None:
        tris = [tuple(t.vtx) for t in wmesh.tris]
        for t in tris:
            poly = [px(wv[i][0], wv[i][2]) for i in t[:3]]
            dr.polygon(poly, fill=(58, 66, 84, 120))
        for a, b in boundary_edges_xz(wv, tris):
            dr.line([px(*a), px(*b)], fill=(200, 205, 220), width=2)

    for it in items:                                    # zones under points
        zone = it.get("zone")
        if not zone:
            continue
        col = paint.TYPE_COLOR.get(it["type"], (255, 255, 255, 255))
        ring = [px(x, z) for x, z in zone]
        dr.polygon(ring, outline=tuple(col[:3]), fill=tuple(col[:3]) + (36,))
        cx = sum(p[0] for p in ring) / len(ring); cy = sum(p[1] for p in ring) / len(ring)
        dr.text((cx + 3, cy - 6), f"{it['label']} [{it['type']}]", fill=tuple(col[:3]), font=font)

    for rt in routes:                                   # routes under points, over zones
        col = rt["color"]
        legs = (swept or {}).get(rt["name"], [])
        pts = list(rt["path"]) + ([rt["path"][0]] if rt["closed"] else [])
        for i in range(len(pts) - 1):
            a, b = px(*pts[i]), px(*pts[i + 1])
            dr.line([a, b], fill=col + (200,), width=3)
            mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2   # arrowhead at mid-leg
            ang = math.atan2(b[1] - a[1], b[0] - a[0])
            for s in (0.5, -0.5):
                dr.line([(mx, my), (mx - 11 * math.cos(ang - s), my - 11 * math.sin(ang - s))],
                        fill=col, width=3)
            if i < len(legs):                           # off-mesh spans over-drawn in red
                (ax, az), (bx, bz) = legs[i]["a"], legs[i]["b"]
                for t0, t1 in legs[i]["spans"]:
                    p0 = px(ax + (bx - ax) * t0, az + (bz - az) * t0)
                    p1 = px(ax + (bx - ax) * t1, az + (bz - az) * t1)
                    dr.line([p0, p1], fill=(255, 70, 70), width=6)
        lp = px(*rt["path"][0])
        dr.text((lp[0] + 5, lp[1] + 5), f"~{rt['name']}", fill=col, font=font)

    for it in items:
        if it.get("footprint") != "point" or not it.get("pos"):
            continue
        x, z = it["pos"]
        col = tuple(paint.TYPE_COLOR.get(it["type"], (255, 255, 255, 255))[:3])
        c = px(x, z)
        ro = C.OBJECT_COLLISION_W * scale                # object-collision ring (96u)
        ri = C.COLLISION_RADIUS_W * scale                # controller radius (48u)
        dr.ellipse([c[0] - ro, c[1] - ro, c[0] + ro, c[1] + ro], outline=col + (110,), width=1)
        dr.ellipse([c[0] - ri, c[1] - ri, c[0] + ri, c[1] + ri], outline=col, fill=col + (70,), width=2)
        face = it.get("face")
        if face is not None:
            dx, dz = face_to_dir(int(face))
            tip = px(x + dx * 170, z + dz * 170)
            dr.line([c, tip], fill=col, width=3)
            ang = math.atan2(tip[1] - c[1], tip[0] - c[0])
            for s in (0.6, -0.6):
                dr.line([tip, (tip[0] - 9 * math.cos(ang - s), tip[1] - 9 * math.sin(ang - s))],
                        fill=col, width=3)
        label = it["label"] + (f"  face={face} ({face_name(face)})" if face is not None else "")
        dr.text((c[0] + ri + 3, c[1] - 12), label, fill=col, font=font)

    try:                                                # the camera / viewer
        cpos = C.decompose(camera)["C"]
        cx, cz = cpos[0], cpos[2]
        cc = px(max(x0, min(x1, cx)), max(z0, min(z1, cz)))
        aim = px((x0 + x1) / 2, (z0 + z1) / 2)
        dr.line([cc, aim], fill=(255, 200, 90, 150), width=1)
        dr.polygon([(cc[0] - 7, cc[1] + 7), (cc[0] + 7, cc[1] + 7), (cc[0], cc[1] - 8)],
                   outline=(255, 200, 90), fill=(255, 200, 90, 90))
        dr.text((cc[0] + 9, cc[1] - 6), f"CAMERA y={cpos[1]:.0f}", fill=(255, 200, 90), font=font)
    except Exception:
        pass

    rx, ry, rr = W - 76, 66, 42                          # compass rose: world axes + screen-up
    for name, (dx, dz) in WORLD_CARDINALS:
        tip = (rx + dx * rr, ry - dz * rr)
        dr.line([(rx, ry), tip], fill=(160, 165, 180), width=2)
        dr.text((tip[0] - 5, tip[1] - 12 if dz > 0 else tip[1] + 2), name[0].upper(),
                fill=(220, 225, 240), font=font)
    ud = math.radians(comp["screen_up_world_deg"])
    tip = (rx + math.sin(ud) * (rr + 12), ry - math.cos(ud) * (rr + 12))
    dr.line([(rx, ry), tip], fill=(120, 255, 140), width=3)
    dr.text((rx - 34, ry + rr + 6), "screen-up", fill=(120, 255, 140), font=font)

    dr.text((6, H + 6), "TOP-DOWN  world frame: +Z=north=BACK (up)  -Z=south=FRONT/camera (down)  "
            "+X=east (right)  |  green arrow = which world way is UP-SCREEN for this camera  |  "
            "grid 500u  |  rings: 48u controller / 96u object", fill=(150, 155, 170), font=font)
    im.save(path)


# --- camera-view render --------------------------------------------------------------------
def render_camview(path, items, camera, wmesh, comp, scale=2, routes=()):
    cw = int(camera.range[0]) or 384
    ch = int(camera.range[1]) or 448
    W, H = cw * scale, ch * scale
    im = Image.new("RGB", (W, H + 26), (16, 18, 24))
    dr = ImageDraw.Draw(im, "RGBA")
    font = ImageFont.load_default()

    if wmesh is not None:
        wv = wmesh.world_verts()
        tris = [tuple(t.vtx) for t in wmesh.tris]
        for a, b in paint.walkmesh_outline_segments(wv, tris, camera, scale):
            dr.line([a, b], fill=(190, 195, 215), width=2)

    def cvs(x, y, z):
        cx, cy = C.to_canvas((x, y, z), camera)
        return (cx * scale, cy * scale)

    for it in items:
        zone = it.get("zone")
        if not zone:
            continue
        col = tuple(paint.TYPE_COLOR.get(it["type"], (255, 255, 255, 255))[:3])
        ring = [cvs(x, 0, z) for x, z in zone]
        dr.polygon(ring, outline=col, fill=col + (30,))
        cx = sum(p[0] for p in ring) / len(ring); cy = sum(p[1] for p in ring) / len(ring)
        dr.text((cx + 2, cy - 6), it["label"], fill=col, font=font)

    for rt in routes:
        col = rt["color"]
        pts = list(rt["path"]) + ([rt["path"][0]] if rt["closed"] else [])
        proj = [cvs(x, 0, z) for x, z in pts]
        for i in range(len(proj) - 1):
            dr.line([proj[i], proj[i + 1]], fill=col + (180,), width=2)
        dr.text((proj[0][0] + 4, proj[0][1] + 4), f"~{rt['name']}", fill=col, font=font)

    for it in items:
        if it.get("footprint") != "point" or not it.get("pos"):
            continue
        x, z = it["pos"]
        col = tuple(paint.TYPE_COLOR.get(it["type"], (255, 255, 255, 255))[:3])
        feet = cvs(x, 0, z)
        h = paint.resolve_height(it)
        if h > 0:                                        # projected height pole = on-screen model size
            head = cvs(x, h, z)
            dr.line([feet, head], fill=col, width=2)
            dr.line([(head[0] - 5, head[1]), (head[0] + 5, head[1])], fill=col, width=2)
        dr.ellipse([feet[0] - 4, feet[1] - 4, feet[0] + 4, feet[1] + 4], outline=col, width=2)
        face = it.get("face")
        if face is not None:                             # facing, as it reads ON SCREEN
            dx, dz = face_to_dir(int(face))
            tip = cvs(x + dx * 150, 0, z + dz * 150)
            dr.line([feet, tip], fill=col, width=2)
        dr.text((feet[0] + 6, feet[1] + 2), it["label"], fill=col, font=font)

    dr.rectangle([0, 0, W - 1, H - 1], outline=(90, 95, 115), width=1)
    dr.text((6, H + 6), f"CAMERA VIEW {cw}x{ch} (x{scale})  |  screen-up = world "
            f"{comp['screen_up_world']} ({comp['screen_up_world_deg']:.0f} deg)  |  pole = model height "
            "at that depth  |  I-beam top = head", fill=(150, 155, 170), font=font)
    im.save(path)


# --- report --------------------------------------------------------------------------------
def write_report(path, field, camera, cam_idx, ncams, comp, recs, warns, wmesh, items_all,
                 routes=(), swept=None):
    L = []
    L.append(f"FIELD LAYOUT PROBE -- {field}")
    L.append(f"camera {cam_idx}/{ncams}: pitch {C.pitch_deg(camera):.1f} deg, yaw {C.yaw_deg(camera):.1f} deg, "
             f"H={camera.proj}, canvas {int(camera.range[0])}x{int(camera.range[1])}")
    try:
        cpos = C.decompose(camera)["C"]
        L.append(f"camera position C=({cpos[0]:.0f}, {cpos[1]:.0f}, {cpos[2]:.0f})  "
                 "(the VIEWER stands here; the room edge nearest it is the FRONT)")
    except Exception:
        pass
    L.append("")
    L.append("COMPASS (world direction -> where it points ON SCREEN):")
    for r in comp["rows"]:
        L.append(f"  {r['world']:<20} -> {r['screen']:<10} ({r['screen_deg']:.0f} deg)")
    L.append(f"  screen-UP corresponds to world {comp['screen_up_world']} "
             f"({comp['screen_up_world_deg']:.0f} deg from +Z toward +X)")
    yaw = C.yaw_deg(camera)
    if abs(yaw) > 10:
        L.append(f"  !! yawed camera ({yaw:.0f} deg): world cardinals do NOT align with screen "
                 "edges -- narrate directions from this table, not from coordinates")
    L.append("")
    L.append("CONTENT (world -> canvas):")
    for r in recs:
        it = r["item"]
        f = it.get("face")
        ftxt = f"  face={f} ({face_name(f)})" if f is not None else ""
        flags = ("  [" + ", ".join(r["flags"]) + "]") if r["flags"] else ""
        L.append(f"  {it['label']:<20} {it['type']:<9} world({it['pos'][0]:>6},{it['pos'][1]:>6})"
                 f" -> canvas({r['canvas'][0]:6.1f},{r['canvas'][1]:6.1f}){ftxt}{flags}")
    zones = [it for it in items_all if it.get("footprint") == "zone" and it.get("zone")]
    if zones:
        L.append("")
        L.append("ZONES:")
        for it in zones:
            zz = it["zone"]
            xs = [p[0] for p in zz]; zs = [p[1] for p in zz]
            cx, cz = sum(xs) / len(xs), sum(zs) / len(zs)
            cvx, cvy = C.to_canvas((cx, 0.0, cz), camera)
            L.append(f"  {it['label']:<20} {it['type']:<9} world x[{min(xs)},{max(xs)}] "
                     f"z[{min(zs)},{max(zs)}] -> canvas centre ({cvx:.0f},{cvy:.0f})")
    if routes:
        L.append("")
        L.append("ROUTES (markers with `path` -- swept for straight-walk legality):")
        for rt in routes:
            legs = (swept or {}).get(rt["name"], [])
            total = sum(lg["len"] for lg in legs)
            bad = sum(1 for lg in legs for _ in lg["spans"])
            status = "ALL LEGS ON-MESH" if not bad else f"{bad} OFF-MESH SPAN(S) -- see warnings"
            shape = "closed ring" if rt["closed"] else "open path"
            L.append(f"  ~{rt['name']:<18} {shape}, {len(legs)} legs, {total:.0f}u total -- {status}")
    if wmesh is None:
        L.append("  (no walkmesh resolved -- off-mesh / wall checks skipped)")
    L.append("")
    if warns:
        L.append(f"WARNINGS ({len(warns)}):")
        L.extend(f"  ! {w}" for w in warns)
    else:
        L.append("WARNINGS: none")
    L.append("")
    L.append("Reminders: FRONT of a room = -z (toward camera) = down-screen at yaw 0. Facing byte: "
             "0=south(front) 64=west 128=north(back) 192=east. Actors jam under ~192u centre distance; "
             "real fields keep standing NPCs 300u+ apart; the player centre stays 48u off walls.")
    txt = "\n".join(L) + "\n"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(txt)
    return txt


def main() -> int:
    ap = argparse.ArgumentParser(description="Render a field.toml's spatial layout offline: top-down map, "
                                             "camera view, compass + spacing report.")
    ap.add_argument("field", help="path to the field.toml")
    ap.add_argument("--out", default=None, help="output dir (default tools/scroll_out/layout_probe/<name>)")
    ap.add_argument("--camera", type=int, default=0, help="camera index for the view/compass (default 0)")
    ap.add_argument("--scale", type=int, default=2, help="camera-view pixel scale (default 2)")
    args = ap.parse_args()

    project = build.FieldProject.load(args.field)
    cams = build.resolve_cameras(project)
    if not cams:
        print("error: [camera] section is required", file=sys.stderr)
        return 2
    if not 0 <= args.camera < len(cams):
        print(f"error: --camera {args.camera} out of range (field has {len(cams)})", file=sys.stderr)
        return 2
    camera = cams[args.camera]

    scene_cfg = None
    if args.field.endswith(".field.toml"):
        spath = args.field[: -len(".field.toml")] + ".scene.toml"
        if os.path.isfile(spath):
            import tomllib
            with open(spath, "rb") as fh:
                scene_cfg = tomllib.load(fh)
    items = paint.normalize_content(project.raw, scene_cfg)
    attach_faces(items, face_queues(project.raw, scene_cfg))

    wmesh = None
    try:
        wm_cfg = project.raw.get("walkmesh", {}) or {}
        ref = wm_cfg.get("bgi") or wm_cfg.get("reference")
        wm_bytes = project.path(ref).read_bytes() if ref else build.resolve_walkmesh(project, camera)
        wmesh = bgi.BgiWalkmesh.from_bytes(wm_bytes)
    except Exception as e:
        print(f"note: no walkmesh resolved ({e})", file=sys.stderr)

    name = os.path.basename(args.field).split(".")[0]
    out = args.out or os.path.join(os.path.dirname(os.path.abspath(__file__)), "scroll_out",
                                   "layout_probe", name)
    os.makedirs(out, exist_ok=True)

    ref_xz = (0.0, 0.0)
    if wmesh is not None:
        wv = wmesh.world_verts()
        if wv:
            ref_xz = (sum(v[0] for v in wv) / len(wv), sum(v[2] for v in wv) / len(wv))
    comp = compass(camera, ref_xz)
    cw = int(camera.range[0]) or 384
    ch = int(camera.range[1]) or 448
    scrolling = build.is_scrolling(project)
    recs, warns = analyze(items, camera, wmesh, cw, ch, scrolling=scrolling)
    if scrolling:
        print("note: scrolling field -- OFF-CANVAS checks skipped (the viewport pans)",
              file=sys.stderr)

    routes = collect_routes(project.raw, scene_cfg)
    bedges = []
    if wmesh is not None:
        wv = wmesh.world_verts()
        bedges = boundary_edges_xz(wv, [tuple(t.vtx) for t in wmesh.tris])
    swept, route_warns = analyze_routes(routes, wmesh, bedges)
    warns += route_warns

    render_topdown(os.path.join(out, "topdown.png"), items, camera, wmesh, comp,
                   routes=routes, swept=swept)
    render_camview(os.path.join(out, "camview.png"), items, camera, wmesh, comp,
                   scale=args.scale, routes=routes)
    txt = write_report(os.path.join(out, "report.txt"), args.field, camera, args.camera, len(cams),
                       comp, recs, warns, wmesh, items, routes=routes, swept=swept)
    print(txt)
    print(f"wrote: {out}\\topdown.png  {out}\\camview.png  {out}\\report.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
