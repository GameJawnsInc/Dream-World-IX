"""Rung-1 recon: dump WORLD11 (the bench dispatcher) + WORLD03's boat machinery as text.

WORLD11 = the benign foot-only state we bench on (no vehicle actors, idle nav arms) --
rung 1 authors a boat actor + board trigger INTO it. WORLD03 = a real boat-owning
dispatcher: its ENTRY 2/func tag=1 Map.Byte[37] state machine holds the genuine boarding
sequence and its obj/entry 6 is the real Blue Narciss actor -- the verbatim reference.

Run from the repo root: py studies/custom-vehicle/recon_dispatchers.py
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))

from ff9mapkit.world.entrance import load_world_dispatchers          # noqa: E402
from ff9mapkit.eb.model import EbScript                              # noqa: E402
from ff9mapkit.eb.cmdasm import disassemble_block                    # noqa: E402

HERE = pathlib.Path(__file__).parent


def dump(name: str, raw: bytes, out_path: pathlib.Path, full_entries=None) -> None:
    s = EbScript(raw)
    lines = [f"== {name}  ({len(raw)} bytes) ==\n"]
    for ei in range(len(s.entries)):
        try:
            e = s.entry(ei)
        except Exception:
            continue
        if not e.funcs:
            continue
        lines.append(f"\nENTRY {ei}:")
        for f in e.funcs:
            lines.append(f"  func tag={f.tag}  abs {f.abs_start}..{f.abs_end}  ({f.abs_end - f.abs_start} B)")
    for ei in (full_entries if full_entries is not None else range(len(s.entries))):
        try:
            e = s.entry(ei)
        except Exception:
            continue
        for f in e.funcs:
            lines.append(f"\n----- ENTRY {ei} tag={f.tag} -----")
            try:
                lines.append(disassemble_block(s.data, f.abs_start, f.abs_end))
            except Exception as ex:
                lines.append(f"  [disasm failed: {ex}]")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out_path}")


def main() -> None:
    disp = load_world_dispatchers()
    print("dispatchers:", ", ".join(sorted(disp)))
    dump("WORLD11", disp["evt_world_world11"], HERE / "recon_world11.txt")  # full dump -- it's small
    dump("WORLD03", disp["evt_world_world03"], HERE / "recon_world03.txt",
         full_entries=[0, 2, 6])                                            # Main_Init + board machine + boat actor


if __name__ == "__main__":
    main()
