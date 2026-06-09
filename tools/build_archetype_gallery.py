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


def unnamed_tokens(group="NPC"):
    """Field tokens in `group` (NPC / SUB / ...) with a full 5-slot anim set not yet an archetype."""
    slots = ("stand", "walk", "run", "left", "right")
    named = {C.model(mid).token for n in AR.names()
             if (mid := AR.resolve(n)[0]) is not None and C.model(mid).group == group}
    seen = {}
    for m in C.models(group=group, field_only=True):
        na = C.npc_anims(m.id)
        if na and set(na) == set(slots) and m.token not in named:
            if m.token not in seen or m.id < seen[m.token]:
                seen[m.token] = m.id
    return sorted(seen)


args = sys.argv[1:]
GROUP = "NPC"
if args and args[0] == "--group":
    GROUP = args[1].upper()
    args = args[2:]
allt = unnamed_tokens(GROUP)
if args and args[0] == "--batch":
    b = int(args[1])
    toks = allt[b * PER_BATCH:(b + 1) * PER_BATCH]
    label = f"batch {b}  (tokens {b * PER_BATCH}-{b * PER_BATCH + len(toks) - 1} of {len(allt)} unnamed)"
elif args:
    toks = [t.upper() for t in args][:PER_BATCH]
    label = "custom"
else:
    print("usage: --batch N  |  TOK1 TOK2 ...")
    sys.exit(1)
if not toks:
    print(f"no tokens (only {len(allt)} unnamed remain; batch out of range?)")
    sys.exit(1)

# even row positions; verify each is on floor 0 of the real GRGR walkmesh
wm = bgi.BgiWalkmesh.from_bytes((IHTEST / "walkmesh.bgi").read_bytes())
n = len(toks)
xs = [round(ROW_X[0] + (ROW_X[1] - ROW_X[0]) * i / max(1, n - 1)) for i in range(n)]
off = [x for x in xs if wm.point_on_walkmesh(x, ROW_Z) is None]
if off:
    print(f"WARNING: x={off} at z={ROW_Z} are off floor 0 -- adjust ROW_X/ROW_Z.")

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
              f"pos = [{x}, {ROW_Z}]", f'dialogue = "{dlg}"', ""]

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
