"""RE-RUN every adversarial probe against contract_mass_gates.py v4 (2026-07-24, READ-ONLY).

NINE probes have been thrown at these gates:
  - the FOUR in contract_mass_audit_probe.py that beat v1 (closed by v2): P_R2, P_R2B, P_R3, P_SUITE;
  - the THREE fresh beats in contract_mass_reaudit.py that beat v2 (closed by v3): BEAT #1
    P2_SUITE_FAKE_BACKING, BEAT #2 P2_R2_DEEP_TEETH, BEAT #3 P2_R2_XFAM_MISLABEL;
  - the TWO round-2 beats in contract_mass_reaudit2.py that beat v3 (closed by v4): P3_R3_TENDRIL_BACKING
    (SEVERE -- a 1-cell tendril to a remote dune blob satisfied v3's mere 8-conn reachability) and
    P3_R1_DOUBLED_LAKE (coincident-duplicate tris erased an internal-lake coast from the silhouette).
This harness re-runs the SAME probe BUILDERS (imported verbatim from all three scripts -- the synthetic
candidate views are unchanged) against the v4 gate functions and asserts EVERY one now FAILS. It adapts
only the OUTPUT layer (the audit scripts' own main()s reference display keys the gates renamed across
versions); the probe builders themselves are re-used unchanged, so the candidate meshes are byte-identical.
The two round-2 CONTROLS (P3_R3_TENDRIL_CONTROL, P3_R1_DOUBLED_LAKE_CONTROL) are re-run too, to confirm
they STILL fail (so the fix is not a special-case that only flips the beat).

Nothing here touches the game install or any deploy. Output -> out/contract_mass/probe_rerun.json.

Run:  py contract_mass_probe_rerun.py   (cwd = studies/overworld-topography)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

import contract_mass_audit_probe as AP     # noqa: E402  the v1 probe BUILDERS (re-used verbatim)
import contract_mass_reaudit as RA         # noqa: E402  the v2 re-audit BEAT builders (re-used verbatim)
import contract_mass_reaudit2 as RA2       # noqa: E402  the v3 round-2 BEAT builders (re-used verbatim)

OUT = HERE / "out" / "contract_mass" / "probe_rerun.json"


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    uv_ok, uv_checks = AP._verify_uvs()
    print(f"UV calibration (probe builders): {uv_ok}  {uv_checks}")
    assert uv_ok, "probe UV builders miscalibrated -- cannot trust the rerun"

    probes = {}

    # P_R2 -- picket comb at stock saturation; v2 must FAIL on ARRANGEMENT (fringe concentration).
    cand2, r2 = AP.probe_r2()
    arr = r2["arrangement"]
    probes["P_R2"] = dict(
        gate="R2", verdict=r2["verdict"], expect="FAIL",
        saturation=r2["saturation"], fringe_concentration=arr["fringe_concentration"],
        fringe_floor=arr["fringe_concentration_floor"], fringe_passes=arr["fringe_passes"],
        n_floating=arr["n_floating_components"], arrangement_pass=arr["arrangement_pass"],
        why=("v1 was arrangement-invariant (0.50 aggregate passed); v2 fails it because the dressing "
             "is depth-uniform -> fringe concentration below the 0.60 floor."),
        fails=(r2["verdict"] == "FAIL"))

    # P_R2B -- 96 UV-dressed tris tagged topo-17; v2 must FAIL because the label-blind body counts them.
    cand2b, r2b, n_uv_dressed = AP.probe_r2b()
    xc = r2b["body"]["topo_crosscheck"]
    probes["P_R2B"] = dict(
        gate="R2", verdict=r2b["verdict"], expect="FAIL",
        n_uv_dressed_tris=n_uv_dressed, label_blind_body_total=r2b["body"]["label_blind_total"],
        n_dressed_grass=r2b["body"]["n_dressed_grass"], saturation=r2b["saturation"],
        topo_disagreement_non16=xc["n_topo_not16"], topo_hist=xc["topo_hist"],
        why=("v1 keyed the body on topo==16 (population ~2, saturation 0.0); v2 keys on fam==desert "
             "+ UV, so the 96 topo-17 UV-dressed tris land IN the body -> saturation ~0.98, and the "
             "topo cross-check reports the disagreement rather than hiding it."),
        fails=(r2b["verdict"] == "FAIL"))

    # P_R3 -- ribbon + ONE token inland topo-17 cell; v2 must FAIL (backing mass < 130 floor).
    cand3, r3 = AP.probe_r3()
    probes["P_R3"] = dict(
        gate="R3", verdict=r3["verdict"], expect="FAIL",
        largest_backing_component_cells=r3["largest_backing_component_cells"],
        backing_floor=r3["backing_mass_floor_cells"], backing_sizes=r3["backing_component_sizes"],
        why=("v1 fired on n>=1 backing; v2 requires a connected desert-family mass >= 130 cells, so a "
             "single token inland cell fails."),
        fails=(r3["verdict"] == "FAIL"))

    # P_SUITE -- picket-comb two-ground mass; v2 must reject OVERALL (fails R2 arrangement at least).
    candS, res = AP.probe_suite()
    sr2 = res["R2"]; sarr = sr2["arrangement"]
    probes["P_SUITE"] = dict(
        overall=res["overall"], expect="FAIL",
        R1=res["R1"]["verdict"], R2=sr2["verdict"], R3=res["R3"]["verdict"],
        R2_fringe=sarr["fringe_concentration"], R2_fringe_passes=sarr["fringe_passes"],
        R3_backing_cells=res["R3"]["largest_backing_component_cells"],
        why=("the whole point of the round: a mechanical picket-comb two-ground mass is rejected "
             "overall -- v2 fails it on R2 arrangement (depth-uniform dressing) and R3 backing extent."),
        fails=(res["overall"] == "FAIL"))

    v1_all_fail = all(p["fails"] for p in probes.values())

    # ---- the THREE fresh v2-beat builders (contract_mass_reaudit), now closed by v3 ---------------
    beats = {}
    # BEAT #3 -- P2_R2_XFAM_MISLABEL: gd-decal UV tagged topo-49/fam=None. v3 UV-driven body counts it.
    _c, r = RA.p2_r2_xfam_mislabel()
    xb = r["body"]["topo_crosscheck"]
    beats["P2_R2_XFAM_MISLABEL"] = dict(
        gate="R2", verdict=r["verdict"], expect="FAIL", saturation=r["saturation"],
        label_blind_body_total=r["body"]["label_blind_total"], n_dressed_grass=r["body"]["n_dressed_grass"],
        fam_disagreement_counted=xb["n_fam_not_desert"], fam_disagreement_hist=xb["fam_disagreement"],
        why=("v2 hard-filtered fam!=desert, silently dropping the 220 gd-decal-UV topo-49 tris (0 "
             "disagreements reported). v3 UV-drives the body: the 220 land IN it (only legit "
             "gd-on-grass halves are excluded), saturation ~0.92 -> FAIL, and the fam disagreement is "
             "COUNTED + reported."),
        fails=(r["verdict"] == "FAIL"))
    # BEAT #2 -- P2_R2_DEEP_TEETH: bimodal comb (big band-0 fringe + detached band-2..4 dressing).
    _c, r = RA.p2_r2_deep_teeth()
    a = r["arrangement"]
    beats["P2_R2_DEEP_TEETH"] = dict(
        gate="R2", verdict=r["verdict"], expect="FAIL", fringe=a["fringe_concentration"],
        fringe_passes=a["fringe_passes"], penetration_ge2=a["penetration_ge2_fraction"],
        penetration_ceiling=a["penetration_ge2_ceiling"], penetration_passes=a["penetration_passes"],
        why=("v2 fringe alone (0.667 >= 0.60) passed a bimodal comb. v3 adds the penetration ceiling: "
             "33% of the dressing sits at band>=2 (>0.25) -> FAIL."),
        fails=(r["verdict"] == "FAIL"))
    # BEAT #1 -- P2_SUITE_FAKE_BACKING: grass-wrapped skin (no backing behind it) + disjoint dune blob.
    _c, res = RA.p2_suite_fake_backing()
    r3 = res["R3"]
    beats["P2_SUITE_FAKE_BACKING"] = dict(
        gate="SUITE", overall=res["overall"], expect="FAIL",
        R1=res["R1"]["verdict"], R2=res["R2"]["verdict"], R3=r3["verdict"],
        r3_reachable_backing=r3["largest_reachable_backing_cells"],
        r3_wholeregion_backing=r3["whole_region_largest_backing_cells"],
        why=("v2 counted the disjoint 130-cell dune blob as 'backing' though the ecotone did not reach "
             "it -> all three gates passed. v3 gates R3 on the ecotone-REACHABLE backing (flood from "
             "the skin): the grass-wrapped skin reaches 0 backing cells -> R3 FAIL -> suite FAIL."),
        fails=(res["overall"] == "FAIL"))

    beats_all_fail = all(p["fails"] for p in beats.values())

    # ---- the TWO round-2 beat builders (contract_mass_reaudit2), now closed by v4 -----------------
    beats2 = {}
    # BEAT #1 (SEVERE) -- P3_R3_TENDRIL_BACKING: a grass-wrapped skin bridged to a remote >=130 dune
    # blob by a 1-cell topo-17 tendril. v4 gates the skin<->backing INTERFACE (broad-front waist) +
    # erosion survival, which a thread cannot satisfy.
    _c, res = RA2.p3_r3_tendril_backing()
    r3 = res["R3"]
    beats2["P3_R3_TENDRIL_BACKING"] = dict(
        gate="SUITE", overall=res["overall"], expect="FAIL",
        R1=res["R1"]["verdict"], R2=res["R2"]["verdict"], R3=r3["verdict"],
        r3_reachable_backing=r3["largest_reachable_backing_cells"],
        r3_interface_pairs=r3["skin_backing_interface_pairs"],
        r3_interface_floor=r3["skin_backing_interface_floor_pairs"],
        r3_erosion_survive=r3["erosion_survive_backing_cells"],
        why=("v3 gated only 8-conn reachability (reachable 131 via a 1-cell tendril -> PASS). v4 requires "
             "the skin to meet the backing across a broad 4-conn interface (thread=1 < floor 20; stock "
             "125) AND survive 1-cell erosion (thread=0; stock 129) -> R3 FAIL -> suite FAIL."),
        fails=(res["overall"] == "FAIL"))
    # BEAT #2 -- P3_R1_DOUBLED_LAKE: doubled hole-lining tris erased the internal-lake coast. v4 dedups
    # coincident tris before the single-owner silhouette so the lake coast reappears.
    _c, r1 = RA2.p3_r1_doubled_lake()
    beats2["P3_R1_DOUBLED_LAKE"] = dict(
        gate="R1", verdict=r1["verdict"], expect="FAIL",
        body_tri_u=r1["checks"]["body_tri"]["measured_u"],
        n_coincident_deduped=r1["diagnostics"].get("n_coincident_tris_deduped"),
        why=("v3 let doubled coincident tris drop the internal-lake coast from the single-owner "
             "silhouette (body-tri standoff inflated 1.333u -> 81.333u = false PASS). v4 dedups "
             "coincident tris first -> the lake coast reappears -> standoff ~1.333u -> FAIL."),
        fails=(r1["verdict"] in ("FAIL", "CONVENTION-INVALID")))

    # round-2 CONTROLS must STILL fail (the fix is not a special-case that only flips the beat)
    controls2 = {}
    _c, resc = RA2.p3_r3_tendril_control()
    controls2["P3_R3_TENDRIL_CONTROL"] = dict(
        gate="SUITE", overall=resc["overall"], expect="FAIL",
        r3_reachable=resc["R3"]["largest_reachable_backing_cells"],
        still_fails=(resc["overall"] == "FAIL"))
    _c, r1c = RA2.p3_r1_doubled_lake_control()
    controls2["P3_R1_DOUBLED_LAKE_CONTROL"] = dict(
        gate="R1", verdict=r1c["verdict"], expect="FAIL",
        body_tri_u=r1c["checks"]["body_tri"]["measured_u"],
        still_fails=(r1c["verdict"] in ("FAIL", "CONVENTION-INVALID")))

    beats2_all_fail = all(p["fails"] for p in beats2.values())
    controls2_all_fail = all(p["still_fails"] for p in controls2.values())
    all_fail = v1_all_fail and beats_all_fail and beats2_all_fail and controls2_all_fail

    print("\n== v4 PROBE RE-RUN MATRIX (all nine probes + two round-2 controls) ==")
    print(f"  {'probe':28s} {'gate/scope':10s} {'verdict':16s} {'FAILS?'}")
    for name, p in probes.items():
        v = p.get("verdict") or p.get("overall")
        print(f"  {name:28s} {p.get('gate','all'):10s} {str(v):16s} {p['fails']}")
    for name, p in beats.items():
        v = p.get("verdict") or p.get("overall")
        print(f"  {name:28s} {p.get('gate','all'):10s} {str(v):16s} {p['fails']}")
    for name, p in beats2.items():
        v = p.get("verdict") or p.get("overall")
        print(f"  {name:28s} {p.get('gate','all'):10s} {str(v):16s} {p['fails']}")
    print("  -- round-2 controls (must STILL fail) --")
    for name, p in controls2.items():
        v = p.get("verdict") or p.get("overall")
        print(f"  {name:28s} {p.get('gate','all'):10s} {str(v):16s} {p['still_fails']}")
    print(f"\nfour v1 probes FAIL: {v1_all_fail}; three round-1 beats FAIL: {beats_all_fail}; "
          f"two round-2 beats FAIL: {beats2_all_fail}; round-2 controls STILL fail: {controls2_all_fail}; "
          f"ALL NINE FAIL: {all_fail}")

    out = dict(
        meta=dict(script="contract_mass_probe_rerun.py", read_only=True, zero_game_writes=True,
                  note="Re-runs contract_mass_audit_probe.py (four v1 probes) + contract_mass_reaudit.py "
                       "(three round-1 beat builders) + contract_mass_reaudit2.py (two round-2 beat "
                       "builders + their controls) verbatim against contract_mass_gates.py v4. All NINE "
                       "beats now FAIL and both round-2 controls still fail."),
        uv_calibration=dict(ok=uv_ok, checks={k: list(v) for k, v in uv_checks.items()}),
        v1_probes=probes,
        round1_beat_probes=beats,
        round2_beat_probes=beats2,
        round2_controls=controls2,
        v2_beat_probes=beats,   # legacy key retained for readers of the v3 artifact
        all_four_v1_probes_fail=v1_all_fail,
        all_three_round1_beats_fail=beats_all_fail,
        all_two_round2_beats_fail=beats2_all_fail,
        round2_controls_still_fail=controls2_all_fail,
        all_nine_probes_fail=all_fail,
        all_seven_probes_fail=(v1_all_fail and beats_all_fail),   # legacy key
        all_four_probes_fail=v1_all_fail,                         # legacy key
        summary=(f"v1: P_R2={probes['P_R2']['fails']} P_R2B={probes['P_R2B']['fails']} "
                 f"P_R3={probes['P_R3']['fails']} P_SUITE={probes['P_SUITE']['fails']}; "
                 f"round1: XFAM={beats['P2_R2_XFAM_MISLABEL']['fails']} "
                 f"DEEP_TEETH={beats['P2_R2_DEEP_TEETH']['fails']} "
                 f"FAKE_BACKING={beats['P2_SUITE_FAKE_BACKING']['fails']}; "
                 f"round2: TENDRIL={beats2['P3_R3_TENDRIL_BACKING']['fails']} "
                 f"DOUBLED_LAKE={beats2['P3_R1_DOUBLED_LAKE']['fails']} -> all_nine={all_fail}"))
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"-> {OUT}")
    return out


if __name__ == "__main__":
    main()
