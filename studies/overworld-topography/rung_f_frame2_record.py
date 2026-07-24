"""RUNG F -- FRAME BUILD attempt 2 recorder (read-only bookkeeping).

Attempt 2 tests the round's own guidance: since attempt 1 falsified the RECTANGULAR whole-pocket carry,
try carrying the stock SOUTH-WALL BAND as a true-mesh strip (the measured partial pocket: S-walled,
open N/E). Three new read-only measurements DECIDE it, zero playtest cost:
  rung_f_swall_probe.py  -> swall_probe.json : the S wall DOES terminate to a lowland foot (0% mid-massif)
  rung_f_swall_map.py    -> swall_map.txt    : but the ecotone is pinned against the continuous massif
  rung_f_swall_perim.py  -> swall_perim.json : the shaped (ecotone+S-band) footprint's EAST edge is a
                                               38% rock-cliff (max 34.5u) -- non-weldable; the massif is
                                               continuous S<->E so no keep-S/drop-E cut welds on all sides
=> the S-wall-inclusive true-mesh carry is FALSIFIED at this site (attempt-1's east-cliff finding, now
   proven for the SHAPED cut too). Per the guidance: stage OPTION (c) ALONE (already all-green on the
   gate stack, code-disjoint CONFIRMED), brief the eye with the stock-truth panel (rung_f_eye_brief.png),
   the eye owns F1.

This module injects the attempt_2 record into out/rung_f/rung_f_build.json (frame section) + rewrites
out/rung_f/frame_build.json's headline/all_green to the attempt-2 result. No build, no deploy.

Run: cd studies/overworld-topography && py rung_f_frame2_record.py
"""
from __future__ import annotations
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out" / "rung_f"
BUILD_JSON = OUT / "rung_f_build.json"
FRAME_JSON = OUT / "frame_build.json"


def main():
    be = json.loads((OUT / "basin_envelope.json").read_text(encoding="utf-8"))
    sp = json.loads((OUT / "swall_probe.json").read_text(encoding="utf-8"))
    pe = json.loads((OUT / "swall_perim.json").read_text(encoding="utf-8"))
    frame = json.loads(FRAME_JSON.read_text(encoding="utf-8"))
    oc = frame.get("option_c", {})

    attempt_2 = dict(
        step="RUNG F FRAME BUILD attempt 2 -- the S-WALL true-mesh carry, then option (c) alone",
        date="2026-07-24", read_only=True, zero_game_writes=True, zero_deploys=True,
        mechanism_tested="the guidance's target: carry the stock SOUTH-WALL BAND (the measured partial "
            "pocket, S-walled + open N/E) as a true-mesh strip, welding its lowland foot to minted grass "
            "+ dropping the N/E/W massif; composed with attempt-1's all-green option (c) silhouette.",
        measurements=dict(
            swall_probe=dict(
                script="rung_f_swall_probe.py", out="swall_probe.json",
                finding="the S wall DOES terminate lawfully: 0% MID_MASSIF, 82% of S rays reach a "
                    "lowland/ocean FOOT at depth 68-80u (the wall is a real ~30u ridge that comes back "
                    "down). W terminates too (foot 76-88u); N is deep massif (91% MID_MASSIF, no foot). "
                    "So a foot-weld is possible IN ISOLATION -- necessary but not sufficient.",
                per_side={k: dict(frac_lawful=v["frac_lawful_termination"], frac_mid_massif=v["frac_mid_massif"],
                                  foot_med_u=v["foot_depth_u_median"]) for k, v in sp["per_side"].items()}),
            swall_map=dict(
                script="rung_f_swall_map.py", out="swall_map.txt",
                finding="ASCII map of the donor region: the ecotone (desert/dunes) is embedded in the "
                    "continuous Daguerreo massif -- solid rock to its W and wrapping S->E. The SW ecotone "
                    "columns are already LOW (<8u, opening to ocean = the NO_WALL rays); there is no "
                    "discrete spanning south RIDGE, only the massif flank."),
            swall_perim=dict(
                script="rung_f_swall_perim.py", out="swall_perim.json",
                finding="THE DECISIVE GATE: the shaped (ecotone+S-band) keep footprint (x[216,248] "
                    "z[-192,-161], 132x128u) has a NON-WELDABLE east edge -- "
                    f"{int(pe['sides']['E']['edge_cliff_frac']*100)}% rock-cliff, p50 "
                    f"{pe['sides']['E']['edge_h_p50']}u max {pe['sides']['E']['edge_h_max']}u. N/S/W weld "
                    "(S foot p50 4.9u = lowland), but E cuts the massif's east flank. The massif is "
                    "CONTINUOUS S<->E, so no keep-S/drop-E cut exists without an internal cut face.",
                sides={k: dict(edge_cliff_frac=v["edge_cliff_frac"], edge_h_max=v["edge_h_max"],
                               weldable=v["weldable"]) for k, v in pe["sides"].items()},
                cliff_sides=pe["cliff_sides"], shaped_carry_weldable=pe["shaped_carry_weldable"])),
        s_wall_carry_verdict="FALSIFIED AT THIS SITE (measured bytes, zero playtest cost). The S wall "
            "terminates lawfully in isolation, but the ecotone is PINNED against the continuous massif: "
            "the shaped (ecotone+S-wall) footprint's EAST edge exposes a 34.5u cut rock face, and the "
            "massif is continuous S<->E so no lawful shaped cut exists. This is attempt-1's east-cliff "
            "finding proven for the SHAPED carry too -- the 448x384u massif cannot fit the 320x256u site, "
            "and the ecotone's own boundaries ARE the massif on the pinned E (and part-W) sides. F1 (the "
            "massif ENCLOSURE) is UNSOLVABLE at an isolated ocean island; it needs a CONTINENTAL FUSE "
            "beside the real massif -- a mechanism change beyond a frame design.",
        candidate="OPTION (c) ALONE -- the all-green verbatim ecotone carry (the two-ground CHARACTER "
            "ships by construction). Staged to out/rung_f/FF9CustomMap-world (180 files / 20 blocks).",
        gate_stack=dict(
            plumbing_green=oc.get("plumbing_green"),
            contract_green=oc.get("contract_green"),
            R1=oc.get("R1"),
            R2=oc.get("R2"), R3=oc.get("R3"),
            R2_R3_bit_identical_to_baseline=True,
            code_disjoint_falsifier="rung_f_falsify.py VERDICT=CONFIRMED (R1 46.826/48.882/49.547, "
                "R2 0.4976/0.6303 fringe 0.8008 pen 0.1241 float 0, R3 backing 143 iface 127 erosion 129 "
                "-- BIT-IDENTICAL to the all-green baseline, proving the core is untouched by the new coast)",
            once_edges_above_skirt=oc.get("once_edges_above_skirt"),
            weld_near_miss=oc.get("weld_near_miss"),
            f2_silhouette=oc.get("f2_silhouette"),
            f2_status="ADVISORY / cosmetic (NOT a plumbing or contract gate): med_turn 3.70 vs [8,35] is "
                "UNREACHABLE at R125 via the shipped island generator (rung_f_f2_ceiling proved every "
                "corner config throws the on-grain 8u gate; corners-off caps med_turn ~3.9). A med_turn "
                "8-35 coast needs a larger delivery or a bespoke outline -- a mechanism change, deferred."),
        eye_brief=dict(
            script="rung_f_eye_panel.py", render="renders/rung_f_eye_brief.png",
            purpose="the stock-truth panel the guidance requires: the eye judges the staged build against "
                "the MEASURED partial-pocket standard (S-walled, open N/E, ecotone pinned against the "
                "massif), NOT the first sitting's imagined full mountain ring.",
            standard="is the two-ground margin faithful at THIS achievable ocean-island site? The form "
                "answer (F1) is the eye's to own; the gate stack (R1/R2/R3 + plumbing) is green."),
        f1_status="UNSOLVED AT THIS SITE -- owned by the eye (the massif enclosure is physically "
            "impossible at an isolated 320x256u ocean site; a faithful enclosure needs a continental fuse).",
        all_green_gate_stack=bool(oc.get("plumbing_green") and oc.get("contract_green")),
        headline="attempt 2: the S-wall true-mesh carry (the measured partial pocket) is FALSIFIED by 3 "
            "read-only measurements -- the ecotone is pinned against the continuous massif (shaped-cut "
            "EAST edge = 34.5u rock-cliff), so no lawful shaped (ecotone+south-wall) cut exists at this "
            "site. Per the guidance, OPTION (c) is staged ALONE as the candidate: plumbing + contract GREEN "
            "(R1 46.8/48.9/49.5u, R2/R3 stock-identical, code-disjoint CONFIRMED), the eye briefed with "
            "the stock-truth panel to judge F1 against the measured partial pocket. ZERO deploy.")

    frame["attempt_2"] = attempt_2
    frame["all_green"] = attempt_2["all_green_gate_stack"]     # guidance: all_green = the gate stack green
    frame["headline"] = "RUNG F FRAME (attempt 2): S-wall carry FALSIFIED (ecotone pinned against the " \
        "continuous massif); OPTION (c) staged ALONE, gate stack GREEN, the eye owns F1 against the " \
        "measured partial-pocket standard."
    FRAME_JSON.write_text(json.dumps(frame, indent=1, default=str), encoding="utf-8")
    print(f"-> {FRAME_JSON}")

    doc = json.loads(BUILD_JSON.read_text(encoding="utf-8"))
    doc["frame"] = frame
    BUILD_JSON.write_text(json.dumps(doc, indent=1, default=str), encoding="utf-8")
    print(f"-> injected attempt_2 into {BUILD_JSON}")
    print(f"\nframe.all_green (gate stack) = {frame['all_green']}")
    print(f"s_wall_carry_verdict = FALSIFIED; candidate = OPTION (c) alone; F1 = eye-owned")
    return 0


if __name__ == "__main__":
    sys.exit(main())
