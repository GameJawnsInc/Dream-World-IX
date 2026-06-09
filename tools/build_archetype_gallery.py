#!/usr/bin/env python3
"""Build an in-game ARCHETYPE-ID GALLERY: place a batch of GEO_NPC_F0_<token> models in a row on the
GRGR test room's floor 0, each NPC saying its TOKEN when talked to -- so the human walks up, talks, and
reports what each one looks like. That turns FF9's cryptic NPC tokens into named archetypes.

Each model is placed by NAME (model = "GEO_NPC_F0_<token>") so its animations auto-resolve via the
catalog (the Info Hub pillar). Writes a field.toml next to GRGR's camera.bgx/walkmesh.bgi; deploy it
with tools/deploy_field.py.

Usage:
  py tools/build_archetype_gallery.py --batch 0        # the unnamed-token list, sliced 8 per batch
  py tools/build_archetype_gallery.py APF APM BBA ...   # explicit tokens (<= 8)
"""
import os
import sys
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit import archetypes as AR
from ff9mapkit import catalog as C
from ff9mapkit.scene import bgi

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model_field_usage as _mfu          # the model -> field-locations index (run --build once)

IHTEST = Path(os.environ.get("IHTEST", r"C:\Users\skaki\AppData\Local\Temp\ihtest"))
PER_BATCH = 8
ROW_Z = 150                  # floor-0 row (where the Black Mage test was proven walkable)
ROW_X = (-800, 800)          # on floor 0 (walkable x ~[-1050,1050] at this z)
SPAWN = [0, 500]             # player behind the row, looking at it
# Battle-MONSTER models are far bigger than field NPCs -> fewer per row + wider spacing so they don't
# overlap. Per-group overrides for the batch size + row width (default 8 across [-800, 800]).
GROUP_PER = {"MON": 4}
GROUP_ROW_X = {"MON": (-1000, 1000)}
SKIP = {"DDD"}               # field_only models that DON'T actually render outside battle (in-game-confirmed)


def unnamed_tokens(group="NPC"):
    """Field tokens in `group` (NPC / SUB / ...) with a full 5-slot anim set not yet an archetype."""
    slots = ("stand", "walk", "run", "left", "right")
    named = {C.model(mid).token for n in AR.names()
             if (mid := AR.resolve(n)[0]) is not None and C.model(mid).group == group}
    seen = {}
    for m in C.models(group=group, field_only=True):
        na = C.npc_anims(m.id)
        if na and set(na) == set(slots) and m.token not in named and m.token not in SKIP:
            if m.token not in seen or m.id < seen[m.token]:
                seen[m.token] = m.id
    return sorted(seen)


args = sys.argv[1:]
ARENA = "--arena" in args                 # stage on the big flat scrolling checkerboard (room for HUGE models)
args = [a for a in args if a != "--arena"]
GROUP = "NPC"
if args and args[0] == "--group":
    GROUP = args[1].upper()
    args = args[2:]
allt = unnamed_tokens(GROUP)
per = GROUP_PER.get(GROUP, PER_BATCH)
row_x = GROUP_ROW_X.get(GROUP, ROW_X)
if args and args[0] == "--batch":
    b = int(args[1])
    toks = allt[b * per:(b + 1) * per]
    label = f"batch {b}  (tokens {b * per}-{b * per + len(toks) - 1} of {len(allt)} unnamed)"
elif args:
    toks = [t.upper() for t in args][:per]
    label = "custom"
else:
    print("usage: --batch N  |  TOK1 TOK2 ...")
    sys.exit(1)
if not toks:
    print(f"no tokens (only {len(allt)} unnamed remain; batch out of range?)")
    sys.exit(1)

n = len(toks)
if ARENA:
    # Big flat SCROLLING checkerboard: build the wide arena (~1 screen per model so they never overlap),
    # spread the row across it, player behind. The checkerboard art auto-aligns to this camera.
    import build_debug_arena as _arena
    meta = _arena.build_arena(IHTEST / "art", screens=max(3, n))
    half, margin = meta["quad"][1][0], 700
    xs = [round(-(half - margin) + 2 * (half - margin) * i / max(1, n - 1)) for i in range(n)]
    zs = [z for _, z in meta["quad"]]
    z_lo, z_hi = min(zs), max(zs)
    row_z = z_lo + (z_hi - z_lo) // 4         # the row ~1/4 up from the far edge -- big models read at depth
    spawn_z = z_hi - 150                       # player just inside the near edge, behind the row
    lines = [
        "# Monster ARENA gallery -- HUGE models on a big flat scrolling checkerboard. Walk/scroll to each,",
        "# talk (it says its token + where it appears), and tell me what it is. Wide floor = no overlap.",
        "[field]", "id = 4003", 'name = "ARENA"', "area = 11", "text_block = 1073", "",
        "[camera]", f"pitch = {_arena.PITCH}", f"distance = {int(_arena.DIST)}", f"fov = {_arena.FOV}",
        f"range = [{meta['range_w']}, 448]", "window_width = 384", "", "[camera.scroll]", "enabled = true", "",
        "[walkmesh]", f"quad = {meta['quad']}", 'frame = "world"', "",
        "[[layers]]", 'image = "art/back.png"', "z = 4000",
        "[[layers]]", 'image = "art/floor.png"', "z = 3000", "",
        "[player]", f"spawn = [0, {spawn_z}]", "",
    ]
else:
    # GRGR borrowed BG: even row positions, verified on floor 0 of the real GRGR walkmesh.
    wm = bgi.BgiWalkmesh.from_bytes((IHTEST / "walkmesh.bgi").read_bytes())
    xs = [round(row_x[0] + (row_x[1] - row_x[0]) * i / max(1, n - 1)) for i in range(n)]
    off = [x for x in xs if wm.point_on_walkmesh(x, ROW_Z) is None]
    if off:
        print(f"WARNING: x={off} at z={ROW_Z} are off floor 0 -- adjust ROW_X/ROW_Z.")
    row_z = ROW_Z
    lines = [
        "# Archetype-ID gallery -- walk up to each NPC and TALK; it says its TOKEN. Tell me what each looks",
        "# like and I'll name the good ones. Each model is placed by NAME (anims auto-resolved).",
        "[field]", "id = 4003", 'name = "GRGR_FORK"', "area = 21",
        'borrow_bg = "GRGR_MAP420_GR_CEN_0"', "text_block = 1073", "",
        "[camera]", 'borrow = "camera.bgx"', "control_direction = 0", "",
        "[walkmesh]", 'reference = "walkmesh.bgi"', "",
        "[player]", f"spawn = [{SPAWN[0]}, {SPAWN[1]}]", "",
    ]
for tok, x in zip(toks, xs):
    m = C.model(f"GEO_{GROUP}_F0_{tok}")
    rows, total = _mfu.usage(m.id, limit=3) if m else ([], 0)
    fids = " ".join(str(f) for f, _ in rows)
    loc = (rows[0][1] if rows else "?").encode("ascii", "ignore").decode().strip()
    dlg = f"{tok}: warp {fids}  ({loc})" if fids else tok      # talk -> F6 Warp to see it in-story
    lines += ["[[npc]]", f'name = "{tok}"', f'model = "GEO_{GROUP}_F0_{tok}"',
              f"pos = [{x}, {row_z}]", f'dialogue = "{dlg}"', ""]

out = IHTEST / "gallery.field.toml"
out.write_text("\n".join(lines), encoding="utf-8")
print(f"GALLERY {label}\n")
for i, (tok, x) in enumerate(zip(toks, xs), 1):
    m = C.model(f"GEO_{GROUP}_F0_{tok}")
    rows, total = _mfu.usage(m.id, limit=4) if m else ([], 0)
    where = "; ".join(nm for _, nm in rows) or "(not in field scripts)"
    print(f"  {i}. {tok:5} (talk->{tok!r})  in {total} field(s): {where}")
print(f"\nwrote {out}")
print(f'deploy:  py tools/deploy_field.py "{out}"')
