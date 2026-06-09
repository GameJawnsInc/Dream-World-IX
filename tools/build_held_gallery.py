#!/usr/bin/env python3
"""Build a HELD-ITEM gallery: every GEO_ACC prop that a character HOLDS in shipping fields (from the
AttachObject HELD_POSES catalog) but that isn't a named prop archetype yet -- placed held by its REAL
carrier on the arena, pose auto-resolved from HELD_POSES. The human walks/scrolls to each, talks, and IDs
the item (a weapon, a tool). Names the gap between the proven held items and the named prop archetypes.

Usage: py tools/build_held_gallery.py     # then deploy with tools/deploy_field.py
"""
import os
import sys
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit import archetypes as AR
from ff9mapkit import catalog as C
from ff9mapkit import prop_archetypes as PA
from ff9mapkit._held_poses import HELD_POSES

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_debug_arena as A


def unnamed_held():
    """[(carrier_archetype, prop_model_name, prop_token), ...] for unnamed held ACC props (deduped).

    Matched by TOKEN, not model id, so prop variants (BLL F1/F2/F3 = the named balloon) are excluded and
    carriers that appear as a non-F0 variant (e.g. an HUM/STN variant) still map to their archetype."""
    archetyped = {C.model(C.resolve_model(s["model"])).token for s in PA.PROP_ARCHETYPES.values()}
    carrier_by_token = {}                               # model TOKEN -> first archetype placing it
    for n in AR.names():
        mid = AR.resolve(n)[0]
        if mid is not None:
            carrier_by_token.setdefault(C.model(mid).token, n)
    out, seen = [], set()
    for (carrier, prop) in HELD_POSES:
        pm, cm = C.model(prop), C.model(carrier)
        if not pm or not cm or pm.group != "ACC":       # ACC props with a known carrier model
            continue
        if pm.token in archetyped or pm.token in seen:  # skip already-named props (any variant) + dups
            continue
        ca = carrier_by_token.get(cm.token)
        if not ca:                                      # need a named carrier to place the holder
            continue
        out.append((ca, pm.name, pm.token))
        seen.add(pm.token)
    return out


PER = 4                                             # each held item = 2 entries (carrier + prop); .eb caps at 10


def _arena_scene(meta, spawn_z):
    return ["[field]", "id = 4003", 'name = "ARENA"', "area = 11", "text_block = 1073", "",
            "[camera]", f"pitch = {A.PITCH}", f"distance = {int(A.DIST)}", f"fov = {A.FOV}",
            f"range = [{meta['range_w']}, 448]", "window_width = 384", "[camera.scroll]", "enabled = true", "",
            "[walkmesh]", f"quad = {meta['quad']}", 'frame = "world"', "",
            "[[layers]]", 'image = "art/back.png"', "z = 4000",
            "[[layers]]", 'image = "art/floor.png"', "z = 3000", "",
            "[player]", f"spawn = [0, {spawn_z}]", ""]


def spotlight(tok, allitems):
    """One carrier holding the item, slowly TURNING through 16 angles (a turntable) so the human can see
    an unclear item from every side. Uses the cutscene turn+wait steps (instant turns are safe on a
    player-cloned NPC). once=false -> replays each F6 reload."""
    item = next((it for it in allitems if it[2] == tok), None)
    if not item:
        print(f"{tok} is not an unnamed held item; nothing to spotlight.")
        return
    carrier, pname, _ = item
    meta = A.build_arena(A.IHTEST / "art", screens=3)
    zs = [z for _, z in meta["quad"]]
    z_lo, z_hi = min(zs), max(zs)
    holder_z, spawn_z = (z_lo + z_hi) // 2, z_hi - 120
    steps = "[" + ", ".join(f"{{turn = {a % 256}}}, {{wait = 40}}" for a in range(0, 512, 32)) + "]"
    L = ["# Spotlight turntable -- the carrier holds the item and slowly spins; watch it from every angle."]
    L += _arena_scene(meta, spawn_z)
    L += ["[[npc]]", f'archetype = "{carrier}"', 'name = "actor"', f"pos = [0, {holder_z}]",
          f'holds = "{pname}"', f'dialogue = "{tok}: what am I holding?"', "",
          "[cutscene]", 'actor = "actor"', "once = false", f"steps = {steps}"]
    (A.IHTEST / "gallery.field.toml").write_text("\n".join(L), encoding="utf-8")
    print(f"SPOTLIGHT: {carrier} holds {tok} ({pname}) + a 16-step turntable. Deploy + F6 reload.")


def main():
    allitems = unnamed_held()
    if not allitems:
        print("no unnamed held ACC props remain -- the held-item catalogue is complete.")
        return
    args = sys.argv[1:]
    if "--spotlight" in args:
        spotlight(args[args.index("--spotlight") + 1].upper(), allitems)
        return
    batch = int(args[args.index("--batch") + 1]) if "--batch" in args else 0
    items = allitems[batch * PER:(batch + 1) * PER]
    print(f"(batch {batch}: items {batch * PER}-{batch * PER + len(items) - 1} of {len(allitems)} unnamed)")
    meta = A.build_arena(A.IHTEST / "art", screens=max(3, len(items)))
    half, margin, n = meta["quad"][1][0], 700, len(items)
    xs = [round(-(half - margin) + 2 * (half - margin) * i / max(1, n - 1)) for i in range(n)]
    zs = [z for _, z in meta["quad"]]
    z_lo, z_hi = min(zs), max(zs)
    row_z, spawn_z = z_lo + (z_hi - z_lo) // 2, z_hi - 150
    L = ["# Held-item gallery -- each NPC HOLDS an unnamed prop (pose auto-resolved). Walk up, talk, tell",
         "# me what the item is and I'll name it.",
         "[field]", "id = 4003", 'name = "ARENA"', "area = 11", "text_block = 1073", "",
         "[camera]", f"pitch = {A.PITCH}", f"distance = {int(A.DIST)}", f"fov = {A.FOV}",
         f"range = [{meta['range_w']}, 448]", "window_width = 384", "[camera.scroll]", "enabled = true", "",
         "[walkmesh]", f"quad = {meta['quad']}", 'frame = "world"', "",
         "[[layers]]", 'image = "art/back.png"', "z = 4000",
         "[[layers]]", 'image = "art/floor.png"', "z = 3000", "",
         "[player]", f"spawn = [0, {spawn_z}]", ""]
    for (carrier, pname, tok), x in zip(items, xs):
        L += ["[[npc]]", f'archetype = "{carrier}"', f'name = "{carrier}_{tok}"', f"pos = [{x}, {row_z}]",
              f'holds = "{pname}"', f'dialogue = "{tok}: held by {carrier}"', ""]
    out = A.IHTEST / "gallery.field.toml"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"HELD-ITEM gallery ({len(items)} unnamed held props):")
    for carrier, pname, tok in items:
        print(f"  {tok:5} ({pname}) held by {carrier}")
    print(f"wrote {out}\ndeploy: py tools/deploy_field.py \"{out}\"")


if __name__ == "__main__":
    main()
