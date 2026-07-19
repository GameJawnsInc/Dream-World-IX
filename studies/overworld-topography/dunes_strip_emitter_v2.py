"""THE EMITTER COMPARISON, RE-RUN WITH THE CALIBRATION CONTROLS IN THE SHEET.

Round 3 (`dunes_strip_emitter.py`) rendered ONE stock window against ONE synth window and
called the difference a defect. `render_calibration.py` then showed that (a) pure unmodified
stock renders as a hard-edged square lattice at these settings anyway, and (b) real stock
desert|dunes seams vary against EACH OTHER from smooth-organic to distinctly boxy. So that
1-vs-1 comparison had no resolving power and its FALSIFIED verdict was retracted.

This is the comparison that should have been run. The fix is a proper NULL: instead of asking
"does synth look like this one stock window", ask **"is synth distinguishable from a REAL FF9
row sequence borrowed from somewhere else on the map?"**

THE TRANSPLANT NULL. The 195 desert|dunes strip cells sit in two geographic clusters -- one
around blocks (13-14,11-12), one around (18-20,3-4). The render window is in block (18,3). A
TRANSPLANT assignment takes the REAL stock rows from the OTHER cluster and lays them over the
window's cells (cycled, at several offsets). Every transplant is therefore 100% genuine FF9
row-placement -- just from the wrong place. If the emitter is as good as "real rows from
elsewhere", it is inside stock's own range and no look-test can fault it.

Panels rendered at the EXACT round-3 settings (24x24u, UNSHADED, sc=32):
    STOCK (this window's real rows) | TRANSPLANT A | TRANSPLANT B
    SYNTH (emitter seed 0)          | CONTROL all-row-0 | CONTROL iid-random

THE METRIC (because the eye already proved unreliable here): each of the 4 strip rows is a
painted coverage-density tile with its own mean brightness, so a row assignment's visible
"jumpiness" is the mean |delta mean-luminance| between lattice-adjacent strip cells. Stock is
the reference; the spread over many transplants is the NULL BAND; the question is whether
SYNTH lands inside it. That is a falsifiable, non-eyeball test.

Run from the repo root:  py studies/overworld-topography/dunes_strip_emitter_v2.py
"""
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))

SRC_P = Path(__file__).with_name("dunes_strip_emitter.py")
SRC = SRC_P.read_text(encoding="utf-8")
_lines = SRC.split("\n")
# exec round 3's analysis + render primitives, but STOP before its own rendering section
_cut = next(i for i, ln in enumerate(_lines)
            if ln.startswith("# ---- wide overview"))
NS = {"__file__": str(SRC_P), "__name__": "_r3"}
print("=" * 92)
print("re-running round 3's analysis (cell classification, emitter, atlas) ...")
print("=" * 92)
exec(compile("\n".join(_lines[:_cut]), str(SRC_P), "exec"), NS)

strip_cells = NS["strip_cells"]          # {cell: real stock row}
cellinfo = NS["cellinfo"]
ASSIGN = dict(NS["ASSIGNMENTS"])         # STOCK / SYNTH / both controls
render_plan, sheet, at_b = NS["render_plan"], NS["sheet"], NS["at_b"]
neighbors4 = NS["neighbors4"]
ROW_PITCH, DU, DV = NS["ROW_PITCH"], NS["DU"], NS["DV"]
U_LO, U_HI = NS["STRIP_U0"] + DU, NS["STRIP_U1"] + DU
ROW_V0 = NS["ROW0_V0"] + DV              # v of strip row 0 in the translated (desert|dunes) frame
OUTD = NS["OUTD"]
# the round-3 render window, redeclared here (it lives past the cut we exec'd)
ZBX, ZBY = 18, 3
ZBLOCKS = [(ZBX + dx, ZBY + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]

print("\n" + "=" * 92)
print("V2: the transplant null + the luminance-jumpiness metric")
print("=" * 92)

# ---- A. per-row painted brightness (what the eye actually sees change) -------------------------
print("\nA. mean painted brightness of each of the 4 strip rows (sampled from the real atlas)")
row_lum = {}
for r in range(4):
    v0 = ROW_V0 + r * ROW_PITCH
    acc, n = 0.0, 0
    for iu in range(32):
        for iv in range(16):
            u = U_LO + (U_HI - U_LO) * (iu + 0.5) / 32.0
            v = v0 + ROW_PITCH * (iv + 0.5) / 16.0
            _a, (rr, gg, bb) = at_b(u, v)
            acc += 0.299 * rr + 0.587 * gg + 0.114 * bb
            n += 1
    row_lum[r] = acc / n
    print(f"   row {r}: mean luminance {row_lum[r]:6.2f}")
print(f"   -> a 1-row step changes brightness by "
      f"{statistics.mean(abs(row_lum[i+1]-row_lum[i]) for i in range(3)):.2f} on average; "
      f"the full 0->3 span is {abs(row_lum[3]-row_lum[0]):.2f}")

# ---- B. the metric --------------------------------------------------------------------------
ADJ = [(a, b) for a in sorted(strip_cells) for b in neighbors4(a)
       if b in strip_cells and a < b]
print(f"\nB. metric = mean |delta luminance| over the {len(ADJ)} lattice-adjacent strip-cell pairs")


def jumpiness(assign):
    # round 3 uses row_override=None as the sentinel for "render the REAL stock rows"
    asn = strip_cells if assign is None else assign
    return statistics.mean(abs(row_lum[asn[a]] - row_lum[asn[b]]) for a, b in ADJ)


# ---- C. the TRANSPLANT null: real stock rows borrowed from the other cluster -------------------
WEST = sorted(c for c in strip_cells if cellinfo[c]["block"][0] < 16)
EAST = sorted(c for c in strip_cells if cellinfo[c]["block"][0] >= 16)
print(f"\nC. transplant null -- the 2 real clusters: west(13-14,11-12)={len(WEST)} cells, "
      f"east(18-20,3-4)={len(EAST)} cells")
targets = sorted(strip_cells)


def transplant(donor_cells, off):
    """Lay the donor cluster's REAL stock rows over every strip cell, cycled at `off`."""
    dr = [strip_cells[c] for c in donor_cells]
    return {c: dr[(i + off) % len(dr)] for i, c in enumerate(targets)}


NULL = {}
for off in range(0, len(WEST), max(1, len(WEST) // 14)):
    NULL[f"WEST+{off}"] = transplant(WEST, off)
for off in range(0, len(EAST), max(1, len(EAST) // 14)):
    NULL[f"EAST+{off}"] = transplant(EAST, off)
print(f"   built {len(NULL)} transplant samples (all 100% real FF9 row sequences)")

# ---- D. score everything ----------------------------------------------------------------------
print("\nD. jumpiness scores (lower = smoother density gradient between neighbouring cells)")
stock_j = jumpiness(ASSIGN["STOCK (real)"])
null_j = {k: jumpiness(v) for k, v in NULL.items()}
nvals = sorted(null_j.values())
lo, hi = nvals[0], nvals[-1]
print(f"   STOCK (this window's real rows) : {stock_j:6.2f}   <- the reference")
print(f"   TRANSPLANT null band            : {lo:6.2f} .. {hi:6.2f}   "
      f"(n={len(nvals)}, median {statistics.median(nvals):.2f})")
print("      ^ every one of these is REAL FF9 row placement, just from elsewhere on the map")
rows = []
for label, asn in ASSIGN.items():
    if label == "STOCK (real)":
        continue
    j = jumpiness(asn)
    inside = lo <= j <= hi
    rows.append((label, j, inside))
    print(f"   {label:32s}: {j:6.2f}   {'INSIDE the null band' if inside else 'OUTSIDE the null band'}")

# a fuller emitter picture across seeds
emit = NS["emit_strip_rows"]
seed_j = []
for s in range(20):
    try:
        a = emit(targets, NS["touch_of"], NS["TARGET_PMF"], NS["DELTA_P"], seed=s)
        seed_j.append(jumpiness(a))
    except Exception as e:                                    # noqa: BLE001
        print(f"   (emitter seed sweep unavailable: {e})")
        break
if seed_j:
    ins = sum(1 for j in seed_j if lo <= j <= hi)
    print(f"\n   EMITTER across {len(seed_j)} seeds: {min(seed_j):.2f}..{max(seed_j):.2f} "
          f"(mean {statistics.mean(seed_j):.2f}) -- {ins}/{len(seed_j)} seeds INSIDE the null band")

# ---- E. render the 6-panel sheet, controls INCLUDED --------------------------------------------
print("\nE. rendering the 6-panel comparison at the round-3 settings (24x24u, UNSHADED, sc=32)")
bsc = [c for c in strip_cells if cellinfo[c]["block"] == (ZBX, ZBY)]
tcx = (sum(c[0] for c in bsc) / len(bsc) + 0.5) * 4.0
tcz = (sum(c[1] for c in bsc) / len(bsc) + 0.5) * 4.0

nk = sorted(NULL)
PANELS = [
    (f"STOCK (real rows) -- j={stock_j:.2f}", ASSIGN["STOCK (real)"]),
    (f"STOCK-TRANSPLANT {nk[0]} (REAL rows, elsewhere) -- j={null_j[nk[0]]:.2f}", NULL[nk[0]]),
    (f"STOCK-TRANSPLANT {nk[len(nk)//2]} (REAL rows, elsewhere) -- j={null_j[nk[len(nk)//2]]:.2f}",
     NULL[nk[len(nk) // 2]]),
    (f"SYNTH (emitter seed0) -- j={jumpiness(ASSIGN['SYNTH (emitter seed0)']):.2f}",
     ASSIGN["SYNTH (emitter seed0)"]),
    (f"CONTROL all-row-0 -- j={jumpiness(ASSIGN['CONTROL all-row-0']):.2f}",
     ASSIGN["CONTROL all-row-0"]),
    (f"CONTROL iid-random -- j={jumpiness(ASSIGN['CONTROL iid-random']):.2f}",
     ASSIGN["CONTROL iid-random"]),
]
panels = []
for label, ov in PANELS:
    tex, _com, nread = render_plan(ZBLOCKS, tcx, tcz, 24, 24, sc=32, row_override=ov)
    print(f"   {label[:60]:62s} ({nread}/9 neighbours read)")
    panels.append((label, tex))

sheet(panels, cols=3, cell_w=700, cell_h=700,
      path=OUTD / "dunes_strip_emitter_v2_with_controls.png",
      title=f"EMITTER vs STOCK vs THE TRANSPLANT NULL ({tcx:.0f},{tcz:.0f}) 24x24u UNSHADED sc=32 -- "
            f"panels 2 and 3 are REAL FF9 rows borrowed from the other cluster: if SYNTH is not "
            f"clearly worse than THOSE, it is inside stock's own range")
print(f"\n   wrote {OUTD / 'dunes_strip_emitter_v2_with_controls.png'}")

print("\n" + "=" * 92)
print("READ IT LIKE THIS: panels 2-3 show how much REAL stock placement varies. If SYNTH (panel 4)")
print("is not clearly worse than panels 2-3, the look test cannot fault it -- which is the")
print("calibrated version of the judgment round 3 made uncalibrated.")
print("=" * 92)
