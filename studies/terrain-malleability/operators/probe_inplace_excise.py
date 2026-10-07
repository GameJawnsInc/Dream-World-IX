"""PROBE: can ANY kit operator remove (or sink) a REAL landmass in place?  The operator x axis matrix shows axis R
(remove land) has no PRIMARY operator.  The only land-removal tweak is `--excise` (transplant.excise_plan), documented
for CARRIES ("drop every landmass whose LAND crosses the donor rect frame and re-zip deep ocean over its footprint").
The CLI lets `--excise` and `--in-place` be combined (cli.py:4680 builds ex_tweaks before the in-place branch at
:4802), so the question is whether the IN-PLACE gates let it through.

INSTRUMENT: transplant.morph_in_place(dry_run=True) runs the full tweak pipeline + the in-place gates and writes
NOTHING (transplant.py:3367-3368 returns before any deploy; the scanner itself uses `morph_in_place("", dry_run=True)` as
its oracle, coastscan.py:213).  No mod folder is read or written; stock bytes only, via the kit reader.

CALIBRATION (both must hold or the refusal verdict is void):
  (a) POSITIVE CONTROL -- a scanner-certified cliff_bump on the real (7,17) cell must come back clean=True from the same
      morph_in_place dry-run, so 'clean=False' on the excise is a verdict about excise and not about this harness;
  (b) the excise plan must be NON-EMPTY (it must actually drop land), else the refusal is vacuous.  excise_plan's default
      keep_largest=True refuses a rect that would excise its own subject, so (b) forces keep_largest=False.

Rerun:  py studies/terrain-malleability/operators/probe_inplace_excise.py
"""
import sys
sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
from ff9mapkit.world import transplant as TR, coastmorph as CM, coastscan as CS

CELL = (7, 17)

# ---- (a) positive control ------------------------------------------------------------------------------------------
ctrl_ok = False
for w in CS.scan_block(*CELL, verbs=("cliff-bump",)):
    if w["kind"] != "cliff":
        continue
    pr = w["probes"].get("cliff-bump") or {}
    if pr.get("depth") is None:
        continue
    start, end = pr["window"]
    tw = CM.cliff_bump(CELL, start, end, pr["depth"])
    s = TR.morph_in_place("", cell=CELL, tweaks=list(tw), dry_run=True)
    print(f"(a) CONTROL cliff_bump{CELL} window {start}->{end} depth {pr['depth']}: clean={s['clean']} touched={s['touched']} "
          f"gates={[(g.get('gate'), g.get('ok', True)) for g in s['gates'] if 'frame' in str(g.get('gate'))]}")
    ctrl_ok = bool(s["clean"])
    break
else:
    print("(a) CONTROL: no certified cliff-bump window found on", CELL)

# ---- (b) find real cells where excise_plan is NON-EMPTY (default keep_largest=True: it drops a neighbouring crumb while
# keeping the subject), then ask the in-place gates about each ------------------------------------------------------------
import time
from ff9mapkit.world import extract as X
t0 = time.time()
cands = []
for blk in X.list_blocks(disc=1):
    if time.time() - t0 > 120:
        print("   (time cap reached while scanning)")
        break
    try:
        tw, rep = TR.excise_plan(blk, (1, 1), land_margin=0.0)
    except Exception:                                                    # noqa: BLE001
        continue
    if tw:
        cands.append((blk, tw, rep))
print(f"(b) {len(cands)} real 1x1 cells yield a NON-EMPTY excise plan (scanned in {time.time() - t0:.0f}s)")
non_empty = bool(cands)
fails = ok_ = 0
for blk, tw, rep in cands[:12]:
    try:
        s = TR.morph_in_place("", cell=blk, tweaks=list(tw), dry_run=True)
        bad = [(g.get("gate"), g.get("welds")) for g in s["gates"] if not g.get("ok", True)]
        print(f"    {blk}: tweaks={len(tw)} dropped={rep.get('dropped')} -> in-place clean={s['clean']} failing={bad}")
        ok_ += bool(s["clean"]); fails += (not s["clean"])
    except Exception as e:                                               # noqa: BLE001
        print(f"    {blk}: morph_in_place raised {type(e).__name__}: {str(e)[:100]}")
verdict = (f"in-place excise: {fails} refused / {ok_} pass of {min(len(cands), 12)} tested" if cands else "no real cell has a non-empty excise plan")
print("VERDICT:", verdict, "| control clean:", ctrl_ok, "| excise non-empty:", non_empty)
sys.exit(0 if (ctrl_ok and non_empty) else 3)
