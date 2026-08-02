"""THE TERRAIN GATE — one command over any terrain change.

WHY. The gates that finally closed the V-shore corner were eight separate
scripts run by hand in an order held in one head. That is how three of the last
four playtest failures happened: the root cause was visible in a gate that
either did not exist yet, or existed but was not wired into the path it was
written for (the uv-footprint dilation lived in a helper the ear loop never
called — a fix that never once ran). A gate suite you have to remember to run
is not a gate suite.

WHAT IT RUNS (each fails LOUD and names the offender):
  walk      hug traverses both directions, latent hard-lock sweep, statics,
            no walker owning ring 0                         [flow axis]
  weld      near-miss vertex pairs at the joints                 (stage 1)
  cover     nothing lost or gained off-strip                     (stage 1)
  sea       hidden-cut + boat navigability                       (stage 1)
  flow-uv   constant-uv smears, stretches, mirrored faces        [look axis]
  blank     unpainted atlas texels reaching the screen           [look axis]
  tjunc     cracks minted vs the baseline's own count            [look axis]
  peer      does it read like shore the owner already accepted?  [look axis]

THE TWO RULES THIS ENCODES
  * Compare against the NEIGHBOUR, not the marginal. Every gate that scored an
    element in isolation passed a defect the owner then found; `peer` and
    `tjunc` are both differential by construction.
  * Calibrate before judging. `blank` counts EXACT blank paint (255) because at
    a looser threshold it scored the owner-approved island itself as defective.

Usage:
  py terrain_gate.py [staged|live] [--quick]
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

REPORT = HERE / "out" / "terrain_gate_report.json"


def _fmt(ok):
    return "PASS" if ok else "FAIL"


def run(state="staged", quick=False):
    import render_gate as RG
    import vcorner_transplant as VT
    import probe_tjunction as TJ
    import probe_blank_paint as BP
    import probe_peer_compare as PC

    results, t0 = [], time.time()

    def add(name, ok, detail, axis):
        results.append(dict(gate=name, ok=bool(ok), detail=detail, axis=axis))
        print(f"  {_fmt(ok):4s}  {name:9s} {detail}")

    print(f"=== THE TERRAIN GATE [{state}] ===")

    # ---- the build's own gates (stage 1 + 2), read from their ledgers -------
    g1 = HERE / "out" / "vcorner_transplant" / "gates_stage1.json"
    g2 = HERE / "out" / "vcorner_transplant" / "gates_stage2.json"
    if g1.is_file():
        gates = json.loads(g1.read_text()).get("gates", {})
        add("weld", gates.get("g_weld"), "near-miss vertex pairs at the joints", "build")
        add("cover", gates.get("g_coverage"), "walkable coverage on/off strip", "build")
        add("sea", gates.get("g_sea"), "hidden-cut + boat navigability", "build")
        add("walk", gates.get("g_hug") and gates.get("g_no_own0")
            and gates.get("g_statics"), "hug both directions / statics / ring-0", "flow")
    else:
        add("build", False, f"no stage-1 ledger at {g1.name} — run the build first", "build")
    if g2.is_file():
        add("latent", json.loads(g2.read_text()).get("g_latent_zero"),
            "no hidden hard-lock sliver", "flow")
    else:
        add("latent", False, "no stage-2 ledger — run stage2", "flow")

    if quick:
        return _finish(results, t0)

    # ---- the look axis -----------------------------------------------------
    src = dict(VT.staged_src()) if state == "staged" else {}
    RG.state_src = (lambda o: (lambda t: src if t == state else o(t)))(RG.state_src)

    flow = RG.cmd_flow(state)
    bad = flow["smears"] + flow["stretch"] + flow["flips"]
    add("flow-uv", bad == 0,
        f"{flow['smears']} smear / {flow['stretch']} stretched / "
        f"{flow['flips']} mirrored / {flow['rotated']} rotated faces", "look")

    bp = _call(BP, state)
    add("blank", bp["ok"], f"{bp['white_px']} blank-paint px"
        + (f" worst={bp['worst'][1]}" if bp.get("worst") else ""), "look")
    add("holes", bp["holes_ok"], f"{bp['holes']} enclosed background px (cracks)",
        "look")

    n_new = TJ.diff()
    add("tjunc", n_new == 0, f"{n_new} T-junctions minted vs baseline", "look")

    pc = _call(PC, state)
    add("peer", pc["ok"], f"band {pc['band_ratio']}x peers, "
        f"irregularity {pc['irregularity_ratio']}x peers", "look")

    return _finish(results, t0)


def _call(mod, state):
    argv = sys.argv
    sys.argv = [mod.__name__, state]
    try:
        return mod.main()
    finally:
        sys.argv = argv


def _finish(results, t0):
    bad = [r for r in results if not r["ok"]]
    print(f"\n{'ALL GREEN' if not bad else str(len(bad)) + ' GATE(S) RED'} "
          f"({len(results)} gates, {time.time() - t0:.0f}s)")
    for r in bad:
        print(f"   RED  {r['gate']} [{r['axis']}]: {r['detail']}")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(dict(ok=not bad, gates=results), indent=1))
    print(f"report -> {REPORT.relative_to(HERE)}")
    return not bad


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    sys.exit(0 if run(args[0] if args else "staged",
                      quick="--quick" in sys.argv) else 1)
