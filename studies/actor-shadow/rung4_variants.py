"""Stage rung 4's bench: the set-pieces bench (30921's floor, camera and actors) shipping field 1607's MCF,
with `shadow = false` on the player, the chest, the instant save point and the holder NPC, plus one player
[[jump]] -- so a single MCF field exercises every actor kind's OFF lever and the player's post-jump re-disable.

    py studies/actor-shadow/rung4_variants.py

Writes studies/actor-shadow/imported/rung4/ (gitignored: the MCF is SE-derived, regenerated from your
install). The cask prop, the cactus_on and the barrel_pop save point keep their defaults: in-frame actors this
change must leave alone. ON / INIT-ONLY / CONTROL are the SAME toml built three ways (rung4_deploy.py).
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "ff9mapkit"))
from ff9mapkit import extract  # noqa: E402

BENCH = HERE / "bench"
OUT = HERE / "imported" / "rung4"
DONOR = "1607"
SRC = BENCH / "set_pieces.field.toml"
NAME = "SHD4F"
# the player's jump: a tread zone NORTH-EAST of the spawn, clear of both its x and z bands and 90u inside the
# mesh's east edge (x 1200; the player centre stays 80u off it), landing back in the spawn row
JUMP = ('\n# ---- rung 4: the player jumps (a tread zone north-east of the spawn) -- the landing must not bring back\n'
        '# the shadow `[player] shadow = false` switched off (the engine\'s FinishJump re-enables a jumper\'s)\n'
        '[[jump]]\nzone = [[1000, -300], [1110, -300], [1110, -150], [1000, -150]]\nto = [650, -600]\n'
        'trigger = "tread"\n')


def _set_false(text: str, header_line: str) -> str:
    """Add `shadow = false` right after the one line ``header_line`` (the block's first key)."""
    assert text.count(header_line) == 1, header_line
    return text.replace(header_line, header_line + "shadow = false\n")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    text = SRC.read_text(encoding="utf-8")
    tail = 'title = "SHADOW 1"\n'
    assert text.count(tail) == 1
    text = text.replace(tail, tail + f'mapconfig = "mapconfig.bytes"   # field {DONOR}\'s MCF (rung 4)\n')
    text = text.replace('name = "SHD1"', f'name = "{NAME}"')
    text = _set_false(text, "spawn = [900, -600]\n")                     # [player]
    text = _set_false(text, "pos = [450, -250]\n")                       # [[chest]]
    text = _set_false(text, "pos = [-800, -950]\n")                      # the instant [[savepoint]]
    text = _set_false(text, 'model = "GEO_NPC_F0_CSO"\n')                # the holder [[npc]]
    (OUT / "shadow_off.field.toml").write_text(text + JUMP, encoding="utf-8", newline="\n")
    for name in ("shadow0.walkmesh.obj", "shadow0.walkmesh.links.toml"):
        shutil.copyfile(BENCH / name, OUT / name)
    shutil.copytree(BENCH / "art", OUT / "art", dirs_exist_ok=True)
    mcf = extract.extract_mapconfig(DONOR)
    assert mcf, f"no MapConfigData for field {DONOR}"
    (OUT / "mapconfig.bytes").write_bytes(mcf)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
