"""Write rung 2's variant tomls next to the imported bench (see rung2_borrow_mcf.py).

    py studies/actor-shadow/rung2_variants.py

control   the import minus its `[field] mapconfig` line (what every plain `import` shipped before the fix)
empty     control minus the carried-objects section (every [[object]] + the refused [[prop]] stub), so its
          frame is the background the others are masked against

`on` is the import itself (MCF_KTB.field.toml). No reshape variants: a BG-borrow ships no walkmesh, the
engine runs it on the donor's own .bgi, so the MCF's per-floor lights key exactly by construction.
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE / "imported" / "rung2"
SRC = BENCH / "MCF_KTB.field.toml"
OBJECTS_BANNER = "# --- OBJECTS imported from the real field"


def main() -> None:
    text = SRC.read_text(encoding="utf-8")
    assert 'borrow_bg = "MDSR_MAP579_MS_KTN_0"' in text, "not the BG-borrow import of 1607"
    lines = text.splitlines(keepends=True)
    control = [ln for ln in lines if not ln.startswith("mapconfig = ")]
    assert len(control) == len(lines) - 1, "the import has no single `mapconfig =` line"
    cut = next(i for i, ln in enumerate(control) if ln.startswith(OBJECTS_BANNER))
    empty = control[:cut]
    assert "[[object]]" not in "".join(empty) and "[[prop]]" not in "".join(empty)
    for name, body in {"control": "".join(control), "empty": "".join(empty)}.items():
        (BENCH / f"MCF_KTB.{name}.field.toml").write_text(body, encoding="utf-8", newline="\n")
    print(f"wrote control, empty in {BENCH}")


if __name__ == "__main__":
    main()
