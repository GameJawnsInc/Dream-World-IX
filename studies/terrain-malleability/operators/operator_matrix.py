"""THE OPERATOR x AXIS MATRIX -- the hand-curated single source of truth for NOTES.md, with MECHANICAL
cross-checks so it cannot silently drift from the kit.

Rows = every `world-*` CLI verb (37) grouped into terrain EDITORS, derived-state editors, and READERS.
Columns (axes): V vertical reshape | H horizontal reshape | T retexture/retile (UV) | P re-topograph (IDALL
walkability/encounter-zone/event) | A add land | R remove land | C carry/transplant (verbatim donor bytes) |
W water parts (Sea*/Beach*) | O objects | S multi-block seams | D disc4 mirroring.
D-axis convention: ● when the operator's usual targets are OCEAN cells / kit islands (the mirror gate passes: destination real cell
absent); ○ when it edits REAL land or can (the gate blocks 189/260 real land blocks, disc_mirror_eligible.py); ✗ when it has no mirror.
Cell codes:  ● primary   ○ secondary / constrained / incidental   ✗ explicitly refused or structurally absent
             (blank) not an axis of this operator.

CROSS-CHECKS (exit 3 on any failure):
  X1  every verb in out/inventory_ast.json is covered by exactly one row (no verb forgotten, none invented)
  X2  D-axis: rows flagged `auto_mirror=True` must have auto_mirror in their module or handler; rows flagged False must
      not (out/writer_gate_census.json) -- so a verb that silently lacks the Disc-4 post-step is *found*, not remembered
  X3  READ SOURCE: rows flagged reads='stock' must show a stock reader and no stacked reader in their handler/module
      (the non-composing property); reads='stacked'/'deployed' the converse
  X4  BREAK-IT: flipping one auto_mirror expectation in a throwaway copy of the table must trip X2 (the check can fail)

Rerun order:  inventory_ast.py -> writer_gate_census.py -> operator_matrix.py
"""
import json, os, sys, copy
sys.stdout.reconfigure(encoding="utf-8")

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
inv = json.load(open(os.path.join(OUT, "inventory_ast.json"), encoding="utf-8"))
cen = json.load(open(os.path.join(OUT, "writer_gate_census.json"), encoding="utf-8"))
AX = ["V", "H", "T", "P", "A", "R", "C", "W", "O", "S", "D"]


def row(verb, kind, axes, mods=(), status="", reads="n/a", auto_mirror=None, gates="", limits="", extra=()):
    a = {k: "" for k in AX}
    a.update(axes)
    return dict(verb=verb, kind=kind, axes=a, mods=list(mods), status=status, reads=reads,
                auto_mirror=auto_mirror, gates=gates, limits=limits, covers=[verb, *extra])


ROWS = [
    # ------------------------------------------------------------------------------- terrain EDITORS
    row("world-deploy", "editor", dict(V="●", C="○", S="●", D="○"), mods=["mesh"], reads="stock", auto_mirror=True,
        status="IN-GAME (legacy path; lift/hill proven 2026-07-02)",
        gates="entrance-block refusal (--allow-entrances); grid bounds; ledger ownership refusal",
        limits="Terrain part only; reads pristine stock (re-run replaces, never stacks); no one-way-wall gate; "
               "recompute_normals is render-inert on WorldMap/Terrain"),
    row("world-terrain", "editor", dict(V="●", S="●", D="○"), mods=["terrain"], reads="stock", auto_mirror=True,
        status="IN-GAME (hill across (16,14)+(16,15), 2026-07-02)",
        gates="one-way-wall refusal (rise/run > tan 79.43 deg; --allow-steep); flank warn > 28.6 deg; off-grid SEAM NOTE; grid bounds",
        limits="Y-only on the Terrain part (coincident Beach1/Sea/Object verts NOT moved); ONE shape per call; same-disc reads "
               "PRISTINE stock so edits do not compose (probe_reshape_read_source.py); NO entrance-block guard (only world-deploy has it); "
               "not toroidal; Disc4 mirror skipped where the real Disc4 cell differs (179/260 blocks)"),
    row("world-retarget", "editor", dict(P="●", D="○"), mods=["mesh"], reads="stock", auto_mirror=True,
        status="IN-GAME (topograph -> walkability, 2026-07-01); event/area alone make NO entrance",
        gates="grid bounds; ledger ownership refusal",
        limits="IDALL per tri, circle region only on the CLI; Terrain only; reads pristine stock (replaces prior Terrain edits on the block); "
               "--area is NOT cosmetic: it keys the encounter zone (ff9.cs:9229-9237) and the location-name text (ff9.cs:3752-3759)"),
    row("world-reclaim", "editor", dict(A="●", V="○", H="○", T="○", P="○", S="○", D="●", W="✗"), mods=["terrain"], reads="n/a",
        auto_mirror=True, status="IN-GAME flat slab (2026-07-02); island/cliff profiles = superseded placeholders",
        gates="MOD-OVERWRITE gate; grid bounds; IsSea target (cell must be stock ocean)",
        limits="whole 64u cells only; ocean cells only; no water authored -> a sidecar-less cell free-rides Block (12,10)'s Sea4 plane + Sea1/3/5 patches "
               "(donor_part_exposure.py); lone cell = unreachable island"),
    row("world-coast", "editor", dict(A="●", C="●", W="○", O="○", D="●"), mods=["terrain"], reads="n/a", auto_mirror=True,
        status="IN-GAME (donor 18,15 real beach + foam, 2026-07-02)",
        gates="MOD-OVERWRITE gate; grid bounds",
        limits="Terrain + Donor.txt only: ALL water/beach/object parts free-ride the donor prefab UNROTATED (cannot be edited here); no placement census, "
               "no prefab-parts gate, no wang/tjunc gates (those live in world-transplant); donor 219 forbidden"),
    row("world-transplant", "editor", dict(C="●", A="●", W="●", S="●", D="●", H="○", V="○", T="○", P="○", R="○", O="○"),
        mods=["transplant", "coastmorph"], reads="stock", auto_mirror=True,
        status="IN-GAME (core 2026-07-08; grow/z-grow, cliff bump/headland/bay/lobes, beach rebuild/reshape/slide/mint r1+r2a, band-convert, "
               "virgin-mint+bank-lower [island B], --ground retile all played); excise partial",
        gates="open-ocean target; MOD-OVERWRITE; frame bounds; land-fit; tweak scope counts; weld audit; T-junction differential; placement census MISS==0; "
              "effective-prefab arm; object anchor; wang-carry/orphan-decal/texture gates are WARN-default",
        limits="PARTS = terrain,beach1,sea1-5 only (Object rides the prefab; beach2/sea6/stream/volcano free-ride); rot 90-multiples, shift 0 mod 4; "
               "beach verbs single-cell only; --ground not combinable with --in-place; wall-context law refuses canyon/scrub/brush/dunes retile of coastal walls; "
               "not x-seam aware (cells 0..23)"),
    row("world-transplant --in-place", "editor", dict(H="●", W="●", V="○", T="○", D="○"), mods=["transplant", "coastmorph"],
        reads="stock", auto_mirror=True, status="IN-GAME (cliff morphs 2026-07-09/10 on the live continent)",
        gates="IN-PLACE-FRAME (block-frame vert set byte-unchanged) + BOUNDS; every tweak's own gates",
        limits="reads pristine stock (successive morphs/terrain edits on a cell replace each other); only parts the real cell has; no Donor.txt, no census; "
               "Disc4 mirror skipped where the real cells differ"),
    row("world-fuse", "editor", dict(C="●", A="●", S="●", W="●", D="●", H="○"), mods=["fuse", "transplant"], reads="stock", auto_mirror=True,
        status="IN-GAME (THE FUSE LAW 2026-07-09; compose tiers [[island]]/[[mountain]]/[[forest]]/[[hill]]/[[coastnav]]/[[rim_retile]] smoke-tested)",
        gates="per-placement gates; rect-overlap; fuse border certification (row-by-row open water); existing-overrides; manifest-drift",
        limits="LAND never knits (coastlines are components; only WATER knits); not x-seam aware"),
    row("world-rim-retile", "editor", dict(T="●", W="●", C="○", S="○", D="✗"), mods=["rimretile"], reads="deployed", auto_mirror=False,
        status="IN-GAME (isthmus, owner-accepted)",
        gates="repartition_ok (geometry untouched, only shade); seam_report under==0; contradicting-edge + unpaintable-sliver reports",
        limits="NO Disc-4 mirror (writes in place via record_ledger_write; Disc4 copy stays the un-retiled sea until world-mirror); refuses seam-spanning input; "
               "a redeploy of the island discards the retile"),
    row("world-island", "editor", dict(A="●", H="●", T="●", S="●", D="●", V="○", P="○", R="○", W="○", O="○"), mods=["island", "grassland"],
        reads="n/a", auto_mirror=True,
        status="IN-GAME (2026-07-07; relief 2026-07-21; x-seam islet 2026-08-27; west-seam continent R1 playtest pending)",
        gates="verify_landmass (cracks, closed-surface once-edges, winding, grain<=8u, holes, UV bounds, placement census MISS 0); texgates WARN-default; "
              "OPEN-OCEAN target; MOD-OVERWRITE; wall-context law; coastnav stamp after deploy",
        limits="--ground mints ONLY grass/desert/snow (canyon/scrub/brush/dunes REFUSED; CLI help says otherwise); --beach arc FALSIFIED; "
               "r>=120 mints ~5% seed yield (grass_over_8u); flat unless --relief; Sea4 plane cut under land"),
    row("world-hill", "editor", dict(V="●", S="○", D="●"), mods=["interior"], reads="deployed", auto_mirror=True,
        status="IN-GAME (2026-07-12 'natural, walkable from all sides')",
        gates="pure-mains footprint; slope p99 28.6 deg; peak <= 8.6; no cracks; placement census; forest/stamp/rim clearances",
        limits="DEPLOYED kit islands only; GRASS-ground only (interior.py:922 requires topo-0 mains; desert=topo 17 is refused); "
               "not seam-spanning"),
    row("world-forest", "editor", dict(C="●", V="○", H="○", T="○", P="○", S="○", D="●"), mods=["interior"], reads="deployed", auto_mirror=True,
        status="IN-GAME (2026-07-12/13 re-home)",
        gates="canopy step law + perimeter walk-in simulation; carry weld; census",
        limits="deployed kit islands only; one topo-37 donor blob ((15,15)); grass annulus only"),
    row("world-mountain", "editor", dict(C="●", V="●", H="○", T="○", P="○", O="○", S="○", D="●"), mods=["interior"], reads="deployed", auto_mirror=True,
        status="IN-GAME (Uaho 2026-07-13; crag, horseshoe, comp20 donors qualified; R5c Uaho live, owner look pending)",
        gates="rock-rigid 0.035; weld-safe lift; apron slope 29.5; zip envelope ny>=0.83 (floor 0.5, <=2 banks); T-junction; census",
        limits="4 qualified donors (donors.toml); synthesis FALSIFIED (carry only); ground families per --ground; deployed islands only"),
    row("world-water", "editor", dict(W="●", T="●", S="●", A="○", P="○", D="●"), mods=["water"], reads="n/a", auto_mirror=True,
        status="IN-GAME (2026-07-05/06 marching-band ocean, 17/17 shape match)",
        gates="MOD-OVERWRITE gate over the whole cell list; sea3|sea4 adjacency == 0",
        limits="open-ocean grammar only (Sea3/4/5; Sea1/2 coast-only); shallows are shore-bound copy-only; NO --target-disc (cannot write the Path-D namespace)"),
    row("world-coastnav", "editor", dict(P="●", W="●", S="○", D="○"), mods=["coastnav"], reads="deployed", auto_mirror=False,
        status="IN-GAME (Southern Ring R5d/R5e, Path D bench)",
        gates="topograph bits only (mask 0xFC); geometry/UV/event/area byte-preserved; pre-write backups; ledger record",
        limits="mirror to Disc4 only with --mirror-disc (not automatic); policy land-anywhere vs cliffs-refuse"),
    row("world-entrance", "editor", dict(P="●", O="●", V="○", T="○", D="○"), mods=["entrance"], reads="stacked", auto_mirror=True,
        status="IN-GAME (entrances, buildings, nameplate surgery case 53 / virgin band 61-64)",
        gates="cell-openness note; trigger tiles excluded from footprint; per-language .eb patch; --fresh discard note",
        limits="Object override REPLACES the block's Object mesh (--keep-block to append); on a block that already has a stock Object the override becomes COLLISION; "
               "stacking compounds geometry on re-runs (use --fresh)"),
    row("world-mesh-build", "editor", dict(O="●", T="○", P="○", D="○"), mods=["blendio"], reads="stacked", auto_mirror=True,
        status="IN-GAME (buildings; terrain lane CLOSED by design)",
        gates="UNINDEXED contract; IDALL stamp (topo 59 or raw --idall 4078 render-only)",
        limits="Object part only; TERRAIN rebuild lane closed (OBJ round-trip cannot carry per-tri IDALL)"),
    row("world-mirror", "editor", dict(D="●", C="○"), mods=["discmirror"], reads="stock", auto_mirror=None,
        status="IN-GAME (the Disc-4 gap, 2026-07-13; auto-run since 2026-07-19)",
        gates="per-cell gate: destination real cell must be open ocean or byte-identical to the source disc; free-ride pin",
        limits="real Disc1/Disc4 only (synthetic namespaces refused); skips cells whose real Disc4 terrain differs (the common case on real land)"),
    row("world-atlas-reskin", "editor", dict(T="●"), status="OFFLINE (pipeline built; repaint is an art task)", limits="GLOBAL: one shared atlas for every block"),
    row("world-atlas-add-tile", "editor", dict(T="●"), status="OFFLINE (magenta-tile pipeline test only)",
        limits="GLOBAL; fills a free 32px region (124 terrain / 373 object cells)"),
    row("world-encounters", "editor", dict(P="●"), mods=["worldpack"], status="IN-GAME (non-uniform re-table, four scenes, 2026-07-22)",
        limits="rewrites discmr.img values in place (355 records); the key is (zone <- tile AREA) x topograph x fog (ff9.cs:9234-9262)"),
    # ------------------------------------------------------------------------------- derived-state editors
    row("world-encounter-frequency", "derived", dict(P="○"), mods=["encounter"], status="IN-GAME per CLAUDE.md s8", limits="per-zone rate ladder, sqrt law"),
    row("world-encounter-rate", "derived", {}, mods=["encounter"], status="Ragtime Mouse only (NOT ordinary encounters)", limits="misnomer"),
    row("world-environment", "derived", {}, mods=["environment"], status="weather/Environment.txt"),
    row("world-rename-markers", "derived", {}, mods=["navimap"], status="map labels"),
    row("world-minimap", "derived", {}, mods=["navimap"], status="draws deployed land onto the big map image; stale after any geometry edit"),
    # ------------------------------------------------------------------------------- READERS / instruments
    row("world-extract", "reader", {}), row("world-locate", "reader", {}), row("world-mesh-export", "reader", {}),
    row("world-mesh-trim", "reader", {}), row("world-texture-palette", "reader", {}), row("world-atlas-extract", "reader", {}),
    row("world-atlas-catalog", "reader", {}), row("world-morphs", "reader", {}, status="builders-are-the-oracle window scanner"),
    row("world-donors", "reader", {}), row("world-render", "reader", {}), row("world-readback", "reader", {}), row("world-ledger", "reader", {}),
]


def handler_of(verb):
    return inv["verbs"][verb]["handler"].lstrip("_cmd_world_") if False else inv["verbs"][verb]["handler"]


def checks(rows):
    fails = []

    # X1 coverage
    cli = set(inv["verbs"])
    covered = {}
    for r in rows:
        for v in r["covers"]:
            if v in cli:
                covered.setdefault(v, []).append(r["verb"])
    missing = sorted(cli - set(covered))
    dup = sorted(v for v, rs in covered.items() if len(rs) > 1)
    if missing or dup:
        fails.append(f"X1 coverage: missing={missing} dup={dup}")

    # X2 / X3 against the writer census
    for r in rows:
        v = r["verb"].split(" --")[0]
        if v not in cli:
            continue
        h = cen["handlers"].get(inv["verbs"][v]["handler"], {})
        mods = [cen["modules"][m] for m in r["mods"] if m in cen["modules"]]
        has_auto = bool(h.get("auto_mirror")) or any(m["auto_mirror"] for m in mods)
        if r["auto_mirror"] is not None and has_auto != r["auto_mirror"]:
            fails.append(f"X2 auto_mirror: {r['verb']} expected {r['auto_mirror']} census {has_auto}")
        has_stock = bool(h.get("reads_stock")) or any(m["reads_stock"] for m in mods)
        has_stack = bool(h.get("reads_stacked")) or any(m["reads_stacked"] for m in mods)
        if r["reads"] == "stock" and not (has_stock):
            fails.append(f"X3 reads: {r['verb']} declared stock but census sees no stock reader")
        if r["reads"] in ("stacked", "deployed") and not has_stack:
            fails.append(f"X3 reads: {r['verb']} declared {r['reads']} but census sees no stacked/deployed reader")
    return fails


fails = checks(ROWS)
print("X1/X2/X3:", "PASS" if not fails else "FAIL")
for f in fails:
    print("  ", f)

# X4 break-it: flip rim-retile's expectation; the check MUST trip
mut = copy.deepcopy(ROWS)
for r in mut:
    if r["verb"] == "world-rim-retile":
        r["auto_mirror"] = True
tripped = [f for f in checks(mut) if "world-rim-retile" in f and "X2" in f]
print("X4 break-it (flip rim-retile auto_mirror expectation -> X2 must trip):", "PASS" if tripped else "FAIL")
if not tripped:
    fails.append("X4: the cross-check cannot fail")

# ---- emit markdown + json ------------------------------------------------------------------------------
md = ["| operator (verb) | " + " | ".join(AX) + " | reads | status |", "|---|" + "---|" * len(AX) + "---|---|"]
for r in ROWS:
    if r["kind"] in ("editor", "derived"):
        md.append(f"| `{r['verb']}` | " + " | ".join(r["axes"][k] or " " for k in AX) + f" | {r['reads']} | {r['status']} |")
open(os.path.join(OUT, "operator_matrix.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
json.dump(ROWS, open(os.path.join(OUT, "operator_matrix.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("\n".join(md))
ed = [r for r in ROWS if r["kind"] == "editor"]
print(f"\n{len(ROWS)} rows | editors={len(ed)} derived={sum(r['kind']=='derived' for r in ROWS)} readers={sum(r['kind']=='reader' for r in ROWS)}")
for k in AX:
    print(f"axis {k}: primary(●)={sum(r['axes'][k]=='●' for r in ed)} secondary(○)={sum(r['axes'][k]=='○' for r in ed)} refused(✗)={sum(r['axes'][k]=='✗' for r in ed)}")
sys.exit(3 if fails else 0)
