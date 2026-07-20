"""THE (8,17)+2x2 -> DESERT RETILE CARRY, ROUND 2 -- fixes both blockers the prior round's gate
refused on, and retargets to the site the user picked under the NEW reservation policy.

BLOCKER 1 (THE HATCHED NW-NOTCH ARTIFACT) -- FIXED. Full diagnosis in this round's report /
``artifact_diagnose.py`` + ``hatch_tight_zoom.py``: NOT the donor's B-strip "worn path" band (that
already renders clean through the stock PATH-STRIP RECOVER fallback -- a first hypothesis,
tested and retracted). The real cause: 3 of the donor's 23 SAND-band (topo 31) terrain tris
straddle two grass-side ``coastmorph.SAND_V_CAP_LAND`` sub-variant pins that both collapse onto
desert's ONE discrete cap_land row -- a real triangle degenerating to near-zero UV area, so the
renderer stretches one atlas texel-row across its whole world-space extent, and that row's fine
grain reads as bold regular diagonal bands. Fixed in-language via
``strip_aware_retile.DegenerateSandGuardRetile`` (composition/subclass over the shipped
``GroundRetile`` -- no shipped ff9mapkit/ file edited): a sand tri whose mapped (u,v) triple
degenerates is diverted to the SAME PATH-STRIP RECOVER treatment (real desert mains texture,
position-evaluated) GroundRetile already uses for genuinely unmeasured donor classes.

BLOCKER 2 (THE SITE-SELECTION LIE) -- FIXED. The prior round's ``band_candidates`` var was
computed and never used; ``TARGET`` was hand-set to (19,17) regardless. This round runs a REAL
exhaustive scan over every 2x2 anchor in the stated band (bx in [6,23), by in [15,20) -- wide
enough to cover the archipelago shelf both sides of the donor and every previously-claimed site),
6 checks per anchor, printed as a table, under the user's NEW reservation policy: pre-reset
content homes are NOT reserved -- only LIVE content blocks the map (comp20 (6-7,18-19) + the
plain desert islet (8,19), both already deployed and disc-mirrored). The user's final pick,
(11,18)+2x2 (world origin (704,-1152)), is asserted to be among the scan's PASSING candidates,
not merely asserted blind.

Offline only -- no deploys, no mint, no install writes (every actual filesystem write call is
intercepted; the only files this script itself creates are under ``out/``). Run from the repo
root: py studies/overworld-topography/donor_8_17_carry_prep_v2.py

2026-07-20 UPDATE: the degenerate-sand guard is FOLDED into the shipped ``GroundRetile``
(``strip_aware_retile`` is now a delegate shim), so this prep re-runs through the shipped code
path -- the bare CLI command printed at the end is no longer bugged. Stage 0's virgin-site scan
gained the shipped MOD-OVERWRITE GATE's own re-deploy exemption (a target cell whose Donor.txt
names this carry's own donor is OURS, not foreign) -- without it the scan could never re-run
once the deploy it green-lit had landed. A post-fold re-run was byte-compared IDENTICAL to the
deployed (11,18) files (all 24: 20 meshes + 4 Donor.txt). The fold also CORRECTED this round's
census: the shipped trigger (strict distinct-uv reduction) counts 1 diverted tri, not 3 -- only
the donor-(9,17) tri under the reported hatch pixels is a real mapping-collapsed triangle; the
other 2 were zero-area W-strip clip residues at the x=504 clip plane (source-degenerate,
census-only, never in written output -- the deployed bytes are identical under either count).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit import config as _cfg                       # noqa: E402
from ff9mapkit.world.island import _real_block_parts        # noqa: E402
from ff9mapkit.world import transplant as TR                # noqa: E402
from ff9mapkit.world import mesh as M                       # noqa: E402
from ff9mapkit.world import discmirror as DM                # noqa: E402
from ff9mapkit.world import placement as P                  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import strip_aware_retile as SAR                             # noqa: E402

OUTD = Path(__file__).with_name("out")
OUTD.mkdir(exist_ok=True)
out: dict = {}

MOD_FOLDER = "FF9CustomMap-world"
DONOR = (8, 17)
DONOR_SIZE = (2, 2)
DONOR_BLOCKS = [(8, 17), (9, 17), (9, 18)]                   # (8,18) carries no data
# THE NEW RESERVATION POLICY (the user's final call): pre-reset content homes are NOT reserved.
# Only LIVE content blocks the map -- comp20 (6-7,18-19) + the plain desert islet (8,19), both
# already deployed and disc-mirrored per the install-state note.
LIVE_MOD_SITES = [(6, 18), (7, 18), (6, 19), (7, 19), (8, 19)]
TARGET = (11, 18)
TSIZE = (2, 2)

# ==== stage 0: SITE SELECTION -- a REAL exhaustive scan, band_candidates actually wired ============
print("== stage 0: site selection (exhaustive scan) ==")
GP = Path(_cfg.find_game_path(None))


def block_free_of_mod(bx, by, disc, own_donor=None):
    """No mod overrides at the block -- OR (post-deploy re-runs, 2026-07-20) the block's
    overrides are THIS carry's own: its Donor.txt names exactly ``own_donor`` (the shipped
    MOD-OVERWRITE GATE's re-deploy exemption; without it stage 0 can never re-run once the
    deploy it green-lit has landed)."""
    rdir = GP / MOD_FOLDER / "FF9_Data" / "WorldMap" / f"Disc{disc}" / "0_1" / f"r{by}"
    if not rdir.is_dir():
        return True
    prefix = f"Block[{bx}][{by}] "
    if not any(p.name.startswith(prefix) for p in rdir.iterdir()):
        return True
    if own_donor is not None:
        dp = rdir / f"Block[{bx}][{by}] Donor.txt"
        if dp.is_file() and dp.read_text(encoding="utf-8").strip() == f"{own_donor[0]},{own_donor[1]}":
            return True
    return False


def clearance_ok(bx, by, min_gap=1):
    for (mx, my) in LIVE_MOD_SITES:
        if max(abs(bx - mx), abs(by - my)) <= min_gap:
            return False
    return True


# THE BAND (stated, not hand-picked post hoc): bx in [6,23), by in [15,20) -- covers the donor's
# own row/column neighbourhood plus the whole shelf either side, wide enough that the user's
# (11,18) pick and every previously-tried site ((19,17), (22,18), (17,18), (10,17)) all fall
# inside it.
BAND_BX = range(6, 23)
BAND_BY = range(15, 20)
band_candidates = [(bx, by) for by in BAND_BY for bx in BAND_BX]

grid = {}
for by in range(min(BAND_BY) - 1, max(BAND_BY) + 2):
    for bx in range(min(BAND_BX) - 1, max(BAND_BX) + 2):
        grid[(bx, by)] = bool(_real_block_parts((bx, by), disc=1))

DONOR_CELLS = {(DONOR[0] + i, DONOR[1] + j) for i in range(DONOR_SIZE[0]) for j in range(DONOR_SIZE[1])}


def scan_anchor(ax, ay):
    """The 6 checks, for the 2x2 anchored at (ax,ay). Returns (passed: bool, checks: dict)."""
    cells = [(ax + i, ay + j) for j in range(TSIZE[1]) for i in range(TSIZE[0])]
    # per-cell "our own re-deploy" donor (the same offset mapping the carry itself uses)
    own = {(ax + i, ay + j): (DONOR[0] + i, DONOR[1] + j)
           for j in range(TSIZE[1]) for i in range(TSIZE[0])}
    checks = {}
    checks["in_band"] = all((c[0] in BAND_BX and c[1] in BAND_BY) for c in cells)
    checks["all_true_open_ocean_stock"] = all(not grid.get(c, True) for c in cells)
    checks["free_of_mod_overrides_disc1"] = all(
        block_free_of_mod(*c, disc=1, own_donor=own[c]) for c in cells)
    checks["free_of_mod_overrides_disc4"] = all(
        block_free_of_mod(*c, disc=4, own_donor=own[c]) for c in cells)
    checks["clearance_from_live_mod_sites"] = all(clearance_ok(*c) for c in cells)
    checks["not_overlapping_donor_rect"] = not any(c in DONOR_CELLS for c in cells)
    return all(checks.values()), checks


rows = []
passing = []
for (ax, ay) in band_candidates:
    ok, checks = scan_anchor(ax, ay)
    rows.append((ax, ay, ok, checks))
    if ok:
        passing.append((ax, ay))

print(f"  scanned {len(band_candidates)} anchors in bx{list(BAND_BX)[0]}-{list(BAND_BX)[-1]} x "
      f"by{list(BAND_BY)[0]}-{list(BAND_BY)[-1]}; {len(passing)} pass all 6 checks")
print(f"  {'anchor':>10} {'ocean':>6} {'nomod1':>7} {'nomod4':>7} {'clear':>6} {'noover':>7} {'inband':>7} {'PASS':>5}")
for (ax, ay, ok, checks) in rows:
    if not ok and not (ax, ay) == TARGET:
        continue  # print every PASS + the chosen TARGET row even if (hypothetically) it failed
    print(f"  ({ax:>3},{ay:>3}) "
          f"{'Y' if checks['all_true_open_ocean_stock'] else 'n':>6} "
          f"{'Y' if checks['free_of_mod_overrides_disc1'] else 'n':>7} "
          f"{'Y' if checks['free_of_mod_overrides_disc4'] else 'n':>7} "
          f"{'Y' if checks['clearance_from_live_mod_sites'] else 'n':>6} "
          f"{'Y' if checks['not_overlapping_donor_rect'] else 'n':>7} "
          f"{'Y' if checks['in_band'] else 'n':>7} "
          f"{'PASS' if ok else 'FAIL':>5}")
print(f"  ... ({len(passing)} total passing anchors; full table in the json artifact)")

out["site_scan"] = {"band_bx": [min(BAND_BX), max(BAND_BX)], "band_by": [min(BAND_BY), max(BAND_BY)],
                    "n_scanned": len(band_candidates), "n_passing": len(passing),
                    "passing": passing,
                    "rows": [{"anchor": [ax, ay], "ok": ok, **checks} for (ax, ay, ok, checks) in rows]}

target_ok, target_checks = scan_anchor(*TARGET)
print(f"\n  TARGET {TARGET}+{TSIZE[0]}x{TSIZE[1]} = world origin "
      f"({64*TARGET[0]},{-64*TARGET[1]})  checks: {target_checks}")
assert target_ok, f"the user's picked site {TARGET} did NOT pass the real scan -- do not proceed"
assert TARGET in passing, "TARGET missing from the scan's own passing set (inconsistent gate)"
print(f"  TARGET is among the {len(passing)} scan-verified passing anchors -- confirmed, not asserted blind")
out["target"] = {"anchor": list(TARGET), "size": list(TSIZE), "world_origin": [64 * TARGET[0], -64 * TARGET[1]],
                 "checks": target_checks}

# ==== stage 1: DRY carry via the CLI-equivalent Python API, every write intercepted =================
print("\n== stage 1: dry carry at the NEW site, degenerate-sand-guard fix in effect, every write intercepted ==")
_captured_meshes: dict = {}
_calls: list = []


def _fake_deploy_override(bm, *, mod_folder, game=None, lod="0_1", part="Terrain"):
    p = str(_cfg.find_game_path(game) / mod_folder / M.override_relpath(bm.disc, bm.x, bm.y, lod, part))
    _captured_meshes[(bm.x, bm.y, part.lower())] = bm
    _calls.append(("override", p))
    return p


def _fake_deploy_donor_sidecar(dx, dy, *, mod_folder, disc, x, y, lod="0_1", game=None):
    p = str(_cfg.find_game_path(game) / mod_folder / M.donor_sidecar_relpath(disc, x, y, lod))
    _calls.append(("donor_sidecar", p, [dx, dy]))
    return p


_mirror_calls = []


def _fake_auto_mirror(paths, *, mod_folder, skip_mirror=False, game=None):
    _mirror_calls.append((list(paths), skip_mirror))
    return None


M.deploy_override = _fake_deploy_override
M.deploy_donor_sidecar = _fake_deploy_donor_sidecar
DM.auto_mirror = _fake_auto_mirror

gt = SAR.build(DONOR, "desert", size=DONOR_SIZE, strips="auto", extra=8.0, disc=1)
print(f"  retile grass->desert: sand anchors "
      f"{[f'{s:.4f}->{d:.4f}' for (s, d) in gt.sand_anchors]}")
print(f"  recover budget: {gt.recover_budget} tris over {len(gt.recover_cells)} cells "
      f"(unmeasured B-strip/D-meadow classes)")
print(f"  degenerate-sand guard budget: {gt.expected.get('sand_degenerate_recovered', 0)} tris "
      f"(the fix for BLOCKER 1)")

summary = TR.transplant_region(
    MOD_FOLDER, cell=TARGET, donor=DONOR, size=DONOR_SIZE, rot=0, shift=(0.0, 0.0),
    strips="auto", tweaks=[gt], extra=8.0, land_margin=0.0, disc=1, census_samples=24,
    dry_run=False)                                    # writes are intercepted above -- safe

print(f"\n  op={summary['op']}  donor={summary['donor']}+{summary['size']}  "
      f"cell={summary['cell']}+{summary['tsize']}  rot={summary['rot']}  shift={summary['shift']}")
print(f"  tongue strips: {summary['strips']}  coverage strips: {summary['coverage_strips']}")
print(f"  carried: {summary['carried']}")
for key, meta in summary["cells"].items():
    print(f"  cell {key}: donor prefab {meta['donor']}  {meta['carried']}"
          + (f"  blanked: {meta['blanked']}" if meta["blanked"] else ""))
print("  GATES:")
for g in summary["gates"]:
    detail = "  ".join(f"{k}={v}" for k, v in g.items() if k not in ("gate", "ok"))
    print(f"    {g['gate']}: {detail} -> {'ok' if g['ok'] else 'FAIL'}")
print(f"  CLEAN: {summary['clean']}")
assert summary["clean"], "the carry did not pass every gate -- do not report success"
out["dry_run_summary"] = summary

print(f"\n  would-write (Disc1): {sum(1 for c in _calls if c[0] == 'override')} overrides + "
      f"{sum(1 for c in _calls if c[0] == 'donor_sidecar')} Donor.txt = {len(_calls)} files")
out["would_write_disc1"] = [c[1] for c in _calls]

assert len(_mirror_calls) == 1, "expected exactly one auto_mirror call from a real (non-dry) deploy"
mirrored, skip_mirror = _mirror_calls[0]
print(f"  auto_mirror WAS invoked (skip_mirror={skip_mirror}) with {len(mirrored)} Disc1 paths "
      f"-- confirms a real deploy self-mirrors to Disc4")
out["auto_mirror_invoked"] = True
out["auto_mirror_input_count"] = len(mirrored)
out["would_write_disc4_mirrored"] = [p.replace("Disc1", "Disc4") for p in mirrored]
out["would_write_total_both_discs"] = len(_calls) + len(mirrored)

# ==== stage 2: teleport verification (off-lattice, placement-simulator HIT) =========================
print("\n== stage 2: teleport verification (LATTICE-EDGE-TELEPORT TRAP -- off-lattice, HIT-checked) ==")
ORDER = ["object", "terrain", "beach1", "beach2", "stream", "river", "riverjoint", "falls",
        "sea1", "sea2", "sea3", "sea4", "sea5", "sea6"]


def meshlist_for(bx, by):
    return [(p, _captured_meshes[(bx, by, p)]) for p in ORDER if (bx, by, p) in _captured_meshes]


def donor_meshlist_for(bx, by):
    out_ = []
    for p in ORDER:
        try:
            out_.append((p, __import__("ff9mapkit.world.extract", fromlist=["read_block"])
                         .read_block(bx, by, disc=1, part=p)))
        except ValueError:
            continue
    return out_


# OUR CARRY teleport, recomputed for the NEW site: reuse the same LOCAL (block-relative) offset
# the prior round proved HIT (block (20,17) local (10.5,-44.5) under TARGET=(19,17)) -- since the
# donor geometry is carried rot=0/shift=(0,0), the SAME local offset within the SAME relative
# donor block ((9,17) -> the 2nd column, 1st row of the 2x2) lands on the SAME desert-mains tri,
# just re-based onto the new target block (TARGET[0]+1, TARGET[1]).
carry_bx, carry_by = TARGET[0] + 1, TARGET[1]                 # local (bx,by,lx,lz)
lx, lz = 10.5, -44.5
wx, wz = 64.0 * carry_bx + lx, -64.0 * carry_by + lz
y, name, idall, topo = P.place(meshlist_for(carry_bx, carry_by), lx, lz, sky=True)
print(f"  OUR CARRY teleport: world ({wx},{wz})  -> y={y:.3f} mesh={name} topo={topo} "
      f"(desert mains topo 17 expected)")
assert name == "terrain" and topo == 17, "carry teleport point did not land on desert mains"
out["teleport_our_carry"] = dict(world=[wx, wz], y=round(y, 3), mesh=name, topo=topo)

# DONOR A/B teleport -- UNCHANGED from the prior round (the donor itself did not move):
# block (9,17) local (10.5,-44.5), already verified HIT on grass mains topo 0 at
# world (586.5,-1132.5) y=4.369.
dbx, dby, dlx, dlz = 9, 17, 10.5, -44.5
dwx, dwz = 64.0 * dbx + dlx, -64.0 * dby + dlz
dy_, dname, didall, dtopo = P.place(donor_meshlist_for(dbx, dby), dlx, dlz, sky=True)
print(f"  DONOR A/B teleport: world ({dwx},{dwz}) -> y={dy_:.3f} mesh={dname} topo={dtopo} "
      f"(grass mains topo 0 expected)")
assert dname == "terrain" and dtopo == 0, "donor A/B teleport point did not land on grass mains"
out["teleport_donor_ab"] = dict(world=[dwx, dwz], y=round(dy_, 3), mesh=dname, topo=dtopo)
assert abs(y - dy_) < 1e-6, "carry and donor teleport heights should be byte-identical (verbatim geometry)"

# ==== write artifact ==================================================================================
outp = OUTD / "donor_8_17_carry_prep_v2.json"
outp.write_text(json.dumps(out, indent=1, default=str))
print(f"\n-> {outp}")

deploy_cmd = "py studies/overworld-topography/deploy_donor_8_17_desert.py"
print(f"\nDEPLOY COMMAND (the deployed carry's exact record):\n  {deploy_cmd}\n"
      f"  (bare-CLI EQUIVALENT since the 2026-07-20 fold -- the degenerate-sand guard now ships "
      f"inside GroundRetile itself: py -m ff9mapkit world-transplant "
      f"--mod-folder {MOD_FOLDER} --cell {TARGET[0]},{TARGET[1]} --donor {DONOR[0]},{DONOR[1]} "
      f"--size 2x2 --ground desert --strips auto --shift 0,0 --land-margin 0)")
