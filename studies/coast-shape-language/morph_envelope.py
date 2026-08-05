"""THE MORPH ENVELOPE -- which shape dials does each palette mass actually have?

Region-capable cliff verbs (#17) gave every palette mass a morph surface for the first
time; the design menu's scan predates that and found windows on exactly one block. This
sweep charts the real envelope:

  1. `coastscan.scan_block` over every block of every palette rect -- windows + the
     scanner's own per-verb ceiling probes, WITH the named binding constraint per refusal
     (the binding reasons are the finding: e.g. "no grass mains -- painted-mural family"
     means headland/bay have no fill language on that top).
  2. For scanner-CLEAN cliff windows, VERIFY with a real `transplant_region --dry-run`
     ladder (headland then bay, escalating depth) -- a gate suite is a regression
     harness, not an oracle, and the scanner is not the gate suite.

  py studies/coast-shape-language/morph_envelope.py            # full sweep, ~minutes
  py studies/coast-shape-language/morph_envelope.py --no-verify  # scan only

Read-only. Writes MORPH-ENVELOPE.tsv next to itself.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
from ff9mapkit.world import coastscan as CS                  # noqa: E402
from ff9mapkit.world import coastmorph as CM                 # noqa: E402
from ff9mapkit.world import transplant as TR                 # noqa: E402

#: the guarded palette (PALETTE.md) -- donor, size, excise, label
PALETTE = [
    ((9, 5),   (2, 3), False, "comma"),
    ((6, 6),   (2, 2), True,  "isthmus"),
    ((6, 4),   (2, 2), False, "reef"),
    ((0, 0),   (1, 1), False, "corner"),
    ((7, 17),  (4, 2), False, "chain"),
    ((6, 4),   (1, 2), False, "reef-frag"),
    ((17, 16), (2, 1), False, "small"),
    ((14, 1),  (4, 2), True,  "crescent"),
]
#: a stock-empty target able to hold every rect above (verified this session)
TARGET = (19, 0)
CLIFF_VERBS = ("cliff-bump", "cliff-headland", "cliff-bay")


def scan_mass(donor, size):
    dx, dy = donor
    nx, ny = size
    out = []
    for j in range(ny):
        for i in range(nx):
            try:
                out += CS.scan_block(dx + i, dy + j, disc=1)
            except Exception as e:
                print(f"   scan ({dx+i},{dy+j}) error: {e}", file=sys.stderr)
    return out


def verify_ladder(donor, size, excise, verb, w0, w1, depths):
    """Real dry-runs at escalating depth; returns [(depth, 'CLEAN'|'gate:<name>'|'refused:<msg>')]."""
    fn = {"cliff-headland": CM.cliff_headland, "cliff-bay": CM.cliff_bay,
          "cliff-bump": CM.cliff_bump}[verb]
    base = []
    if excise:
        base, rep = TR.excise_plan(donor, size, disc=1)
        if rep.get("refused"):
            return [(None, f"excise-refused:{rep['refused'][:60]}")]
    rows = []
    for d in depths:
        try:
            tweaks = list(base) + fn(donor, w0, w1, float(d), size=size, disc=1)
        except Exception as e:
            rows.append((d, f"refused:{str(e)[:90]}"))
            break
        try:
            s = TR.transplant_region("FF9CustomMap-world", cell=TARGET, donor=donor,
                                     size=size, tweaks=tweaks, dry_run=True,
                                     target_disc=9, shift=(0.0, 0.0))
        except Exception as e:
            rows.append((d, f"refused:{str(e)[:90]}"))
            break
        if s["clean"]:
            rows.append((d, "CLEAN"))
        else:
            bad = [g["gate"] for g in s["gates"] if not g["ok"]]
            rows.append((d, "gate:" + ",".join(bad)))
            break
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-verify", action="store_true")
    args = ap.parse_args()

    tsv = Path(__file__).with_name("MORPH-ENVELOPE.tsv")
    lines = ["mass\tblock\tkind\tL\tverb\tscanner\tbinding\tverified"]
    for donor, size, excise, label in PALETTE:
        print(f"== {label} {donor}+{size[0]}x{size[1]}{' (excise)' if excise else ''}")
        wins = scan_mass(donor, size)
        if not wins:
            print("   no windows at all")
            lines.append(f"{label}\t-\t-\t0\t-\tno-windows\t\t")
            continue
        for w in wins:
            cell, kind, L = w["cell"], w["kind"], w["L"]
            for verb, probe in w.get("probes", {}).items():
                depth = probe.get("depth", probe.get("seaward"))
                binding = (probe.get("binding") or probe.get("seaward_binding") or "")
                verified = ""
                if (not args.no_verify and kind == "cliff" and depth is not None
                        and verb in ("cliff-headland", "cliff-bay") and probe.get("window")):
                    w0, w1 = probe["window"]
                    depths = [depth, depth + 4, depth + 8]
                    got = verify_ladder(donor, size, excise, verb, w0, w1, depths)
                    verified = " ".join(f"{d}:{v}" for d, v in got)
                lines.append(f"{label}\t{cell}\t{kind}\t{L:.1f}\t{verb}\t"
                             f"{depth}\t{binding[:110]}\t{verified}")
                mark = f"depth {depth}" if depth is not None else "REFUSED"
                print(f"   {cell} {kind:6s} L={L:5.1f}  {verb:15s} {mark}"
                      + (f"  [{binding[:80]}]" if binding else "")
                      + (f"  verify: {verified}" if verified else ""))
    tsv.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nwrote {tsv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
