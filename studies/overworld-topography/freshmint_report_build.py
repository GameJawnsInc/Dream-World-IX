"""Assembles out/foldback/freshmint_report.json from the fresh-site runs + the site record."""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out" / "foldback"


def load(n):
    p = OUT / n
    return json.loads(p.read_text()) if p.exists() else None


def gate_table(r):
    return [dict(n=i + 1, name=g["name"], ok=g["ok"],
                 advisory=g["name"].startswith("ADVISORY"), detail=g.get("detail", "")[:400])
            for i, g in enumerate(r.get("gates", []))]


def main():
    site = load("freshmint_site.json")
    main_run = load("freshmint.json")
    probes = {k: load(f"freshmint_probe_{k}.json") for k in ("r112", "r118", "r121")}

    env = main_run["L7_gate_results"]["stock_envelope"]
    rep = dict(
        round="THE FRESH-SITE PROOF (the generator fold-back, part 2)",
        date="2026-07-25",
        discipline=dict(game_install_writes=0, deploys=0, git_commits=0,
                        install_access="read-only (X.read_block, island._real_block_parts, "
                                       "transplant.world_tris, a filename scan of FF9CustomMap-world)",
                        legacy_pipeline_files_edited=0,
                        rung_f_out_tree_touched=False),

        headline=dict(
            first_time_clean=False,
            gates_green=31, gates_total=32, iterations_of_the_PIPELINE=0,
            single_red="S0 OPEN-OCEAN TARGET (2 of the 20 written blocks are stock prefab-occupied)",
            attribution=("SITE CAPACITY, not a pipeline defect.  Every one of the 31 gates that "
                         "measures the BUILD passed on the first invocation at a never-before-composed "
                         "site, with zero manual patching and zero pipeline edits.  The one red is the "
                         "site gate, and it is TRUE: the world no longer contains a legal site for an "
                         "r132-class two-ground landmass."),
            world_capacity_finding=site["control_A_stock_only"]["verdict"]),

        site=site,

        mint=dict(
            command="py -X utf8 freshmint_run.py --cx 160 --cz -128 --radius 125 "
                    "--name freshmint --stage out/foldback/freshmint-tree",
            stage_dir=str(OUT / "freshmint-tree"),
            staged=main_run["stage"],
            seconds=main_run["meta"]["seconds"],
            all_green=main_run["all_green"],
            failed=main_run["failed"], advisory_failed=main_run["advisory_failed"],
            gates=gate_table(main_run),

            composite=dict(
                total_tris=main_run["L1_L2_L3"]["n_total_tris"],
                synthesized_tris=main_run["L1_L2_L3"]["n_synthesized_tris"],
                verbatim_carried_tris=main_run["carry"]["n_verbatim_tris"],
                fill_tris=main_run["carry"]["n_fill_tris"],
                placed_R_cells=main_run["carry"]["n_placed_R"],
                blocks=main_run["stage"]["n_blocks"],
                DY=main_run["carry"]["DY"],
                ecotone_floor_y=main_run["carry"]["ecotone_floor_y"],
                ground_tris_by_provenance=dict(
                    untouched_carried=env["carried"]["n"],
                    carried_shaved_by_L5a=env["carried_shaved"]["n"],
                    minted_frame=env["frame"]["n"],
                    synthesized=env["synth"]["n"] if "synth" in env else
                    main_run["L1_L2_L3"]["n_synthesized_tris"]),
                donor=main_run["carry"]["donor"]),

            L1_one_window=dict(window_source=main_run["L1_L2_L3"]["window_source"],
                               single_window=main_run["L7_gate_results"]
                               ["one_window_family_aware"]["single_window_reconstructed"],
                               multi_window=main_run["L7_gate_results"]
                               ["one_window_family_aware"]["multi_window_or_unreconstructed"]),
            L2_family_split=main_run["L1_L2_L3"]["synth_family_hist"],
            L2_family_field_ties=main_run["L1_L2_L3"]["family_field_ties"],
            L3_quad_ori_field=main_run["L1_L2_L3"]["quad_ori"],
            L4_basins=main_run["L4_basins"],
            L4_relax={k: v for k, v in main_run["L4_relax"].items() if k != "method"},
            L5a_spike=dict(pre_census_n=main_run["L5a_spike"]["pre_census_n"],
                           pre_verdicts=main_run["L5a_spike"]["pre_verdicts"],
                           chosen_w_spike=main_run["L5a_spike"]["chosen_w_spike"],
                           n_moved=main_run["L5a_spike"]["n_moved"],
                           guards=main_run["L5a_spike"]["guards"],
                           post_census_n=main_run["L5a_spike"]["post_census_n"],
                           basin_samples_excluded=main_run["L5a_spike"]["basin_samples_excluded"]),
            L5b_orphan=dict(n_uncatalogued_carried_pre=main_run["L5b_orphan"]
                            ["pre_census"]["n_uncatalogued_carried"],
                            n_orphaned_pre=main_run["L5b_orphan"]["pre_census"]["n_orphaned"],
                            n_re_clothed=main_run["L5b_orphan"]["n_re_clothed"],
                            families=main_run["L5b_orphan"]["families"],
                            n_orphaned_post=main_run["L5b_orphan"]["post_census"]["n_orphaned"],
                            n_uncatalogued_carried_post=main_run["L5b_orphan"]["post_census"]
                            ["n_uncatalogued_carried"]),
            L6_sea=main_run["L6_sea"],
            L7_stock_envelope=env,
            contract=dict(overall=main_run["contract"]["overall"],
                          stock_reference=main_run["contract"]["stock_overall"],
                          R1=main_run["contract"]["R1"]["measured"],
                          R1_verdict=main_run["contract"]["R1"]["verdict"],
                          R2=dict(grass_decal=main_run["contract"]["R2"]["saturation"]["grass_decal"],
                                  grass_decal_ceiling=main_run["contract"]["R2"]["saturation"]
                                  ["grass_decal_ceiling"],
                                  any_decal=main_run["contract"]["R2"]["saturation"]["any_decal"],
                                  fringe_concentration=main_run["contract"]["R2"]["arrangement"]
                                  ["fringe_concentration"],
                                  verdict=main_run["contract"]["R2"]["verdict"]),
                          R3=dict(**{k: v for k, v in main_run["contract"]["R3"].items()
                                     if k in ("verdict", "backing", "interface")})),
            L8_renders=main_run.get("L8_renders")),

        capacity_bisection=dict(
            purpose=("a FALSIFIER for the gate battery: does it CATCH an under-sized site, or does it "
                     "pass a broken two-ground composite?  Answer: it catches it, on three independent "
                     "gates, and the transition is sharp."),
            runs={k: dict(radius=float(k[1:]),
                          n_failed=len(v["failed"]), failed=v["failed"],
                          S0=("PASS" if not any("S0 OPEN-OCEAN" in f for f in v["failed"]) else "FAIL"))
                  for k, v in probes.items() if v},
            measured_pipeline_floor_u="118 < R* <= 121",
            reading=("R=112 and R=118 red on WELD-INTEGRITY (317 / 325 once-edges above the sea "
                     "skirt), WELD AUDIT, and CONTRACT R1 (0.137/2.0/0.943 against floors "
                     "39.953/44.635/42.968) -- the carried ecotone hangs past the coast and the "
                     "two-ground boundary standoff collapses.  R=121 is watertight again "
                     "(open_edges=0) and R1 recovers to 42.815/44.887/45.552, but the straddle floor "
                     "44.635 leaves only 0.252u of headroom -- so the pipeline's own floor sits at "
                     "R~121 and rung-F's shipped R=125 is the honest working value.")),

        why_no_legal_site=site["impossibility_proof"],

        concurrency_control=dict(
            observation=("a CONCURRENT session edited the kit inside this same worktree DURING this "
                         "round: ff9mapkit/world/island.py (build_landmass now returns mains_field; "
                         "verify_landmass now runs texgates.texture_sea_gates, WARN-by-default), "
                         "world/transplant.py, cli.py, and a new world/texgates.py.  Those files are "
                         "imported by junction_compose, so the fresh-site runs could have been "
                         "contaminated."),
            control=("re-ran junction_compose's ORIGINAL rung-F self-test under the edited kit, staged "
                     "to out/foldback/control-selftest-tree"),
            result=("all_green=True, 32/32 gates, 0 failed; the 13-row cross-check against the "
                    "recorded out/rung_f/rung_f_build.json is 13/13 MATCH (footprint 20, staged 180, "
                    "DY 0.1224, fill 1954, placed_R 1521, verbatim 1454, once-edges 0, weld 0, "
                    "down-facing 0/3, R1 46.826/48.882/49.547)."),
            verdict="UNCONTAMINATED -- the concurrent edits are additive and output-byte-neutral.",
            install_writes_seen=("8 files under FF9CustomMap-world carry a 13:02 mtime -- the round-8 "
                                 "deploy, BEFORE this session's first write at 14:05.  This round "
                                 "wrote 0 bytes to the install.")),

        next_lever=(
            "The blocking blocks (0,0) and (4,3) both carry a Terrain part, and the nearest stock LAND "
            "vertex is 130.60u away -- outside R=125.  So the r125 disc collides with a PREFAB, not "
            "with land.  The lawful way to use a partially-occupied block is not to weaken the "
            "OPEN-OCEAN TARGET LAW (a wholesale Terrain override there would delete the stock block's "
            "own coast) but to MERGE into it -- the shipped world-fuse / world-transplant path.  That "
            "is a separate lane with its own gates, one change per in-game test."),

        artifacts=dict(
            site_scan=str(HERE / "freshmint_site_scan.py"),
            runner=str(HERE / "freshmint_run.py"),
            finalizer=str(HERE / "freshmint_finalize.py"),
            site_record=str(OUT / "freshmint_site.json"),
            stock_grid_cache=str(OUT / "stock_grid.json"),
            fresh_mint_report=str(OUT / "freshmint.json"),
            fresh_mint_tree=str(OUT / "freshmint-tree"),
            probe_reports=[str(OUT / f"freshmint_probe_{k}.json") for k in probes if probes[k]],
            renders=("WITHHELD BY DESIGN.  THE FINAL-COMPOSITE RULE emits L8 only on an all-green "
                     "composite; every fresh-site run is red on S0, so junction_compose skipped the "
                     "render stage and recorded the skip.  That refusal is itself a verified gate "
                     "behaviour.  The existing eye channels are the self-test's, at "
                     + str(OUT / "renders-rung_f_original") +
                     " -- and they cover this composite's look, because the fresh-site composite is a "
                     "pure 1024u translation of the rung-F one (identical L1/L2/L3/L4/L5a/L5b counts, "
                     "and the basin disc re-derives at the same (127.14, z+1024) with the same "
                     "r=7.92u / enclosure 0.951 / 14 anomalous verts).")),
    )
    (OUT / "freshmint_report.json").write_text(json.dumps(rep, indent=1, default=str))
    print("wrote", OUT / "freshmint_report.json")
    print(json.dumps(rep["headline"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
