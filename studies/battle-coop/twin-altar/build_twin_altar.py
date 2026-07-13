"""THE TWIN ALTAR -- a co-op puzzle room you can READ without debug info (V2 [[coop]] showcase).

A native fork of field 2301 (Esto Gaza / Altar -- the glowing temple room; the altar_stone prop
is native to this dungeon) with the puzzle authored on top. Everything is visible in-game:

  * TWO ALTAR STONES west of spawn mark the twin plates; a MOOGLE by the spawn explains the rule
    in dialogue ("they sing only when TWO stand upon them").
  * Fire the twin-stones gate -> "The twin stones sing in harmony!" and the WARDEN appears LIVE
    between the stones (a flag-gated NPC + the [[coop]] reveal) -- she explains the second half:
    the anchor stone by the eastern arch.
  * The ANCHOR STONE stands in the eastern archway (the room's REAL east exit, retargeted): the
    arch is a flag-gated gateway consuming a mode="hold" level flag -- open only WHILE someone
    stands at the anchor. Passing through lands in the co-op hangout room (30003).
  * The north + northwest exits stay LIVE (they walk into real Esto Gaza 2300/2304 -- F6 back).

SOLO (Role=selftest): the mirror ghost stands exactly +250 x from you. Plate B = plate A + 250,
and the anchor plate sits 250 east of the arch's approach lane -- so the whole quest solves solo:
stand on the WEST stone (the mirror lands on the east one), then just walk into the east arch
(the mirror holds the anchor as you pass). On two machines each mechanic is the real thing.

PROVENANCE: the extraction contains Square-Enix bytes (atlas/scene/walkmesh), so the output dir
is GITIGNORED -- this script is the committable source of truth and regenerates everything from
the local install. Run it from anywhere:

    py studies/battle-coop/twin-altar/build_twin_altar.py
    py tools/deploy_field.py studies/battle-coop/twin-altar/out/TWIN_ALTAR.field.toml
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]                      # <repo>/studies/battle-coop/twin-altar -> <repo>
KIT = REPO / "ff9mapkit"
OUT = HERE / "out"
DONOR = "2301"                              # Esto Gaza / Altar
NAME = "TWIN_ALTAR"

# The puzzle content, appended to the extracted field.toml. Geometry (donor walkmesh, world
# coords, all flat y=0): spawn (-359,-432) on the main floor x[-1850,900] z[-970,699]; the east
# arch chunk x[860,2291] z[-637,186]; the east gateway quad's inner edge ~x1283 at z=-250.
# Plate B = plate A translated EXACTLY +250 x (the selftest mirror offset); the anchor plate is
# centered 250 east of the arch's approach lane, INSIDE the (retargeted) east gateway quad.
AUTHORED = """
# ================= THE TWIN ALTAR -- the co-op puzzle (authored) =================

[[prop]]                     # twin stone WEST -- plate A's marker. collision=false: the marker
prop = "altar_stone"         # IS the plate -- stand right on the stone (walk-through scenery)
pos = [-800, -400]
collision = false

[[prop]]                     # twin stone EAST -- plate B's marker (exactly +250 x)
prop = "altar_stone"
pos = [-550, -400]
collision = false

[[prop]]                     # the ANCHOR stone: a marker BESIDE the held lane, not on it (props
prop = "altar_stone"         # carry mild collision -- standing ON one fights the mechanic). The
pos = [1447, 13]             # hold plate below covers the arch's approach lane; the stone flags it.

[[npc]]                      # the tutorial, in-world: no debug knowledge needed.
name = "Mogri"               # (All NPC/prop spots hand-tuned IN-GAME 2026-07-12 -- the camera
preset = "moogle"            # bounds/occlusion aren't offline-derivable; the first pass parked
pos = [-1416, 215]           # the moogle behind the central column.)
face = 192
dialogue = "Kupo! See the twin stones to the west? They sing only when TWO stand upon them -- one soul on each, kupo!"

[[npc]]                      # the payoff + the second hint: appears LIVE when the stones fire
name = "Warden"
preset = "sand_oracle"
pos = [-841, -1164]
requires_flag = 8620
dialogue = "You who walk as two... The anchor stone waits in the eastern arch. While one of you HOLDS it, the arch stands open. Alone, it will not yield."

[[coop]]                     # the twin stones: fire once when both are stood upon
name = "twin-stones"
plate_a = [-880, -480, -720, -320]
plate_b = [-630, -480, -470, -320]
set_flag = 8620
text = "The twin stones sing in harmony!"

[[coop]]                     # the anchor: held-open level flag consumed by the east arch.
name = "anchor-stone"        # WIDE plate (450) = a generous "stone area": held while the walker
mode = "hold"                # is anywhere x[1200,1650] in the approach lane (mirror = +250), so
plate = [1450, -330, 1900, -170]   # the arch is open the whole way through its trigger zone.
set_flag = 8622
"""


def main() -> int:
    env = dict(os.environ)
    data = KIT / "ff9mapkit" / "data" / "blank_field"
    if not data.exists():                   # worktree checkouts lack the gitignored template data
        main_data = Path(r"C:\gd\Dream-World-IX\ff9mapkit\ff9mapkit\data")
        if (main_data / "blank_field").exists():
            env["FF9MAPKIT_DATA"] = str(main_data)

    OUT.mkdir(exist_ok=True)
    (HERE / ".gitignore").write_text("out/\n", encoding="utf-8")

    print(f"extracting the native fork of {DONOR} (Esto Gaza / Altar)...")
    # --carry-text: the donor's one carried NPC keeps its REAL lines (else it renders wrong text)
    r = subprocess.run([sys.executable, "-m", "ff9mapkit", "import", DONOR, "--native",
                        "--carry-text", "--out", str(OUT)], cwd=KIT, env=env)
    if r.returncode != 0:
        return r.returncode

    tomls = sorted(OUT.glob("*.field.toml"))
    src = next(t for t in tomls if "TWIN_ALTAR" not in t.name) if any(
        "TWIN_ALTAR" not in t.name for t in tomls) else tomls[0]
    text = src.read_text(encoding="utf-8")

    # our field name (the extractor derives one from the donor fbg)
    text = re.sub(r'(?m)^name = "\w+"', f'name = "{NAME}"', text, count=1)

    # (the donor spawn (-359,-432) sits on its own door threshold -- lint flags it as edge-close,
    # but that IS the real field's entry placement and the engine's inward shove handles it; the
    # obvious "pull it interior" fix lands in a walkmesh HOLE -- the room has interior structure.)

    # THE EAST ARCH: retarget the real exit (to 2303, Esto Gaza's shop) into the co-op door --
    # destination = the co-op hangout room, gated on the anchor's hold flag. The zone (the real
    # archway quad) is kept verbatim.
    east = re.search(r'\[\[gateway\]\]\nto = 2303\nentrance = \d+\n', text)
    if not east:
        print("ERROR: the east gateway (to 2303) not found in the extracted toml -- "
              "the donor layout changed? Inspect", src)
        return 2
    text = text.replace(east.group(0),
                        '[[gateway]]\nto = 30003            # the co-op hangout room\n'
                        'entrance = 0\nrequires_flag = 8622  # open only while the ANCHOR is held\n')

    text += AUTHORED
    dst = src if src.name.startswith(NAME) else src.with_name(f"{NAME}.field.toml")
    dst.write_text(text, encoding="utf-8")
    if dst != src:
        src.unlink()

    print(f"authored -> {dst}")
    print("lint...")
    r = subprocess.run([sys.executable, "-m", "ff9mapkit", "lint", str(dst)], cwd=KIT, env=env)
    if r.returncode != 0:
        return r.returncode
    print(f"\nnext:  py tools/deploy_field.py {dst.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
