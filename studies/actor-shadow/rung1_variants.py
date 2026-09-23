"""Write rung 1's variant tomls next to the imported bench (see rung1_editable_mcf.py).

    py studies/actor-shadow/rung1_variants.py

control        the import minus its `[field] mapconfig` line (what every editable fork shipped before the fix)
empty          control minus the carried-objects section (every [[object]] + the refused [[prop]] stub), so
               its frame is the background the others are masked against
probe          the import with the player spawned at PROBE -- in view, on donor floor 0 ONLY (no other floor
               under it, outside both live gateway zones) -- the reference for the two reshapes. The player is
               the probe: floor 0's light (clr -1, shadowI -3) differs from floor 3's (clr -3, shadowI -5), and
               no carried object in view stands on a floor with its own light
reshape        probe with its walkmesh RESHAPED through walkmesh.obj, the `o floor_N` blocks written in the
               order SWAP -- the rebuild renumbers donor floors 0 <-> 3, so the build must re-key the MCF's
               per-floor lights (build.mapconfig_bytes) for the player to keep floor 0's light
reshape-nokey  the same reshape with the re-key CANCELLED: `mapconfig` points at the donor MCF pre-keyed by
               the inverse swap, so what ships is the donor MCF verbatim on the renumbered walkmesh -- the
               failure the re-key prevents, i.e. the instrument's negative control (floor 3's light on him)
"""
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "ff9mapkit"))
from ff9mapkit import mapconfig  # noqa: E402

BENCH = HERE / "imported" / "rung1"
SRC = BENCH / "MCF_KTN.field.toml"
OBJECTS_BANNER = "# --- OBJECTS imported from the real field"
SWAP = [3, 1, 2, 0, 4, 5, 6, 7]         # donor floor written k-th -> built floor k
PROBE = (-72, 571)                      # the player spawn for probe / reshape / reshape-nokey
SPAWN_LINE = "spawn = [917, 552]"
BGI_LINE = 'bgi = "walkmesh.bgi"'


def _reordered_obj(text: str) -> str:
    """walkmesh.obj with its `o floor_N` blocks re-emitted in SWAP order (verts untouched)."""
    head, blocks, cur = [], {}, None
    for ln in text.splitlines():
        m = re.match(r"o floor_(\d+)$", ln)
        if m:
            cur = int(m.group(1))
            blocks[cur] = [ln]
        elif cur is None:
            head.append(ln)
        else:
            blocks[cur].append(ln)
    assert sorted(blocks) == sorted(SWAP), sorted(blocks)
    return "\n".join(head + [ln for k in SWAP for ln in blocks[k]]) + "\n"


def main() -> None:
    text = SRC.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    control = [ln for ln in lines if not ln.startswith("mapconfig = ")]
    assert len(control) == len(lines) - 1, "the import has no single `mapconfig =` line"
    cut = next(i for i, ln in enumerate(control) if ln.startswith(OBJECTS_BANNER))
    empty = control[:cut]
    assert "[[object]]" not in "".join(empty) and "[[prop]]" not in "".join(empty)
    out = {"control": "".join(control), "empty": "".join(empty)}

    assert text.count(SPAWN_LINE) == 1
    text = text.replace(SPAWN_LINE, f"spawn = [{PROBE[0]}, {PROBE[1]}]   # rung-1 probe spot (was {SPAWN_LINE})")
    out["probe"] = text
    (BENCH / "walkmesh.reordered.obj").write_text(_reordered_obj((BENCH / "walkmesh.obj").read_text("utf-8")),
                                                  encoding="utf-8", newline="\n")
    assert text.count(BGI_LINE) == 1
    reshaped = text.replace(BGI_LINE, 'obj = "walkmesh.reordered.obj"\nlinks = "walkmesh.links.toml"\n'
                                      'frame = "world"\n# was: ' + BGI_LINE)
    out["reshape"] = reshaped
    inverse = {built: donor for built, donor in enumerate(SWAP)}      # SWAP is its own inverse, spelled out
    (BENCH / "mapconfig.prekeyed.bytes").write_bytes(
        mapconfig.remap_light_floors((BENCH / "mapconfig.bytes").read_bytes(), inverse))
    out["reshape-nokey"] = reshaped.replace('mapconfig = "mapconfig.bytes"', 'mapconfig = "mapconfig.prekeyed.bytes"')
    assert out["reshape-nokey"] != reshaped
    for name, body in out.items():
        (BENCH / f"MCF_KTN.{name}.field.toml").write_text(body, encoding="utf-8", newline="\n")
    print(f"wrote {', '.join(out)} in {BENCH}")


if __name__ == "__main__":
    main()
