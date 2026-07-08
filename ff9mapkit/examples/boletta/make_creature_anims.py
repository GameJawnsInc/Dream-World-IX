"""Boletta's own animset: a 2-second idle bob authored from curves -- no donor clip, no Blender.

Run it AFTER deploying the field once (the mint's `3DModel` line must be registered so the clip can
resolve its folder), pointing at your mod folder:

    py examples/boletta/make_creature_anims.py "C:\\...\\FINAL FANTASY IX\\FF9CustomMap"

It writes `Animations/6300/<key>.anim` + the `3DModelAnimation` DictionaryPatch line and prints the
`anims = { stand = <key> }` value for the [[npc]] block. RELAUNCH to register a NEW key.

Two rules this file leans on (see the 12-creature-from-scratch tutorial):
  * FIELD anim keys are 16-bit end to end -- deploy_new_anim mints in the 60000-65535 band.
  * new_clip fills every unkeyed bone with a static rest-pose channel (real clips key ALL bones;
    an unkeyed neck lets the engine's head-focus offset accumulate into a spinning head).
  * pos curves REPLACE localPosition, so they carry the bone's rest offset (bone000's -130 below).

CAVEAT: `deploy_field` reverts the slot's prior deploy before re-applying, which rolls back
DictionaryPatch lines minted between deploys -- RE-RUN this script after each redeploy of the field.
"""
import math
import sys
from pathlib import Path

try:
    import ff9mapkit  # noqa: F401  (installed kit)
except ImportError:                 # repo checkout, script run directly: the kit root is two up
    sys.path.insert(0, str(Path(__file__).parents[2]))

from ff9mapkit.models import anim as manim

sys.path.insert(0, str(Path(__file__).parent))          # sibling import when run from elsewhere
from make_creature import BONES, GEO_ID, GEO_NAME       # noqa: E402

FRAMES, RATE = 60, 30.0                     # 2-second loop; sin() cycles end where they start


def _zrot(deg):
    h = math.radians(deg) / 2.0
    return (0.0, 0.0, math.sin(h), math.cos(h))


def _xrot(deg):
    h = math.radians(deg) / 2.0
    return (math.sin(h), 0.0, 0.0, math.cos(h))


def build_idle_clip() -> dict:
    """The idle: whole-body breathing bob (root), slow sway (stem), springy cap counter-bounce."""
    def curve(fn):
        return [(f / RATE, fn(f / FRAMES)) for f in range(FRAMES + 1)]

    curves = {
        0: {"pos": curve(lambda t: (0.0, -130.0 + 3.0 * math.sin(2 * math.pi * t), 0.0))},
        1: {"rot": curve(lambda t: _zrot(3.0 * math.sin(2 * math.pi * t)))},
        2: {"pos": curve(lambda t: (0.0, -48.0 - 4.0 * math.sin(4 * math.pi * t), 0.0)),
            "rot": curve(lambda t: _xrot(2.0 * math.sin(4 * math.pi * t + 0.6)))},
    }
    return manim.new_clip(BONES, curves, name="idle")


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    mod = Path(argv[1])
    dp = mod / "DictionaryPatch.txt"
    directive = f"3DModel {GEO_ID} {GEO_NAME}"          # idempotent with the field deploy's own append
    lines = dp.read_text(encoding="utf-8").splitlines() if dp.exists() else []
    if directive not in lines:
        lines.append(directive)
        dp.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        print(f"registered: {directive}")
    man = manim.deploy_new_anim(GEO_NAME, build_idle_clip(), mod, suffix="IDLE")
    print(f"clip {man['name']} key {man['key']} -> {man['path']}")
    print(f"[[npc]] anims = {{ stand = {man['key']} }}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
