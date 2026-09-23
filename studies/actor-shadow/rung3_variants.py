"""Stage rung 3's bench: the set-pieces bench (bench/set_pieces.field.toml, 30921's actors, floor and camera)
shipping a real donor MapConfigData -- field 1607's, the rung-1/2 donor -- so it is an MCF field.

    py studies/actor-shadow/rung3_variants.py

Writes studies/actor-shadow/imported/rung3/ (gitignored: the MCF is SE-derived, regenerated from your
install): the bench toml with `mapconfig = "mapconfig.bytes"` under [field], its art + walkmesh sidecars, and
the donor MCF. ON and CONTROL are the SAME toml; they differ in the code that builds it (rung3_deploy.py).
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "ff9mapkit"))
from ff9mapkit import extract  # noqa: E402

BENCH = HERE / "bench"
OUT = HERE / "imported" / "rung3"
DONOR = "1607"
SRC = BENCH / "set_pieces.field.toml"
FIELD_TAIL = 'title = "SHADOW 1"\n'


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    text = SRC.read_text(encoding="utf-8")
    assert text.count(FIELD_TAIL) == 1, "the bench's [field] no longer ends with its title line"
    text = text.replace(FIELD_TAIL, FIELD_TAIL + f'mapconfig = "mapconfig.bytes"   # field {DONOR}\'s MCF (rung 3)\n')
    (OUT / "set_pieces_mcf.field.toml").write_text(text, encoding="utf-8", newline="\n")
    for name in ("shadow0.walkmesh.obj", "shadow0.walkmesh.links.toml"):
        shutil.copyfile(BENCH / name, OUT / name)
    shutil.copytree(BENCH / "art", OUT / "art", dirs_exist_ok=True)
    mcf = extract.extract_mapconfig(DONOR)
    assert mcf, f"no MapConfigData for field {DONOR}"
    (OUT / "mapconfig.bytes").write_bytes(mcf)
    print(f"wrote {OUT} (MCF {len(mcf)} bytes from field {DONOR})")


if __name__ == "__main__":
    main()
