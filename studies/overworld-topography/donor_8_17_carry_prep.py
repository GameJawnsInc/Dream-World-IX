"""THE (8,17)+2x2 -> DESERT RETILE CARRY -- full offline dry preparation, end-to-end, through the
SAME shipped machinery the (7,17) and (10,17)+2x2 in-game-proven builds used
(``transplant.GroundRetile.for_donor`` + ``transplant.transplant_region``), with the donor the
round-4 donor screen (``donor_retile_screen.py`` / ``out/donor_retile_screen.json``) named as the
top new pick: (8,17)+2x2, data blocks (8,17)/(9,17)/(9,18), a real 3-block sea-ringed beach
island; (8,18) itself carries no data (true open sea within the donor rect).

SITE SELECTION (this script's own stage 0): scans the live install's per-block occupancy
(``island._real_block_parts``, the SAME check ``transplant_region``'s own real-target gate uses)
across the archipelago band to find a target 2x2 window that is (a) TRUE open ocean on all 4
cells against STOCK data, (b) free of any existing mod override (checked directly against the
live ``FF9CustomMap-world`` tree -- the same directory ``THE MOD-OVERWRITE GATE`` itself reads),
(c) >=1 full empty block clear of the two live mod sites (comp20 @ (6-7,18-19); the plain desert
islet @ (8,19)), and (d) not one of the RESERVED pre-reset content footprints ((22,18)+2x2,
(17,18)+2x2, (4,19), (6,19), (10,19)).

Then: builds the retile + region transplant DRY (every gate the shipped pipeline runs, verbatim
lines), with EVERY WRITE INTERCEPTED (``ff9mapkit.world.mesh.deploy_override`` /
``deploy_donor_sidecar`` and ``ff9mapkit.world.discmirror.auto_mirror`` are monkeypatched to
RECORD their call args instead of touching the filesystem) to recover the exact would-write file
list (both the CLI ``--dry-run`` path -- which returns before ANY write -- and this direct-API
capture, which proves auto-mirroring fires on a real deploy without ever calling it for real).

Finally: placement-verifies two off-lattice teleport points (LATTICE-EDGE-TELEPORT TRAP: hand out
teleports OFF the 4u lattice) -- one on OUR carry's land, one on the real donor's own land (the
A/B anchor) -- using the shipped offline placement simulator (``world.placement.place``,
byte-exact to the engine's ground query).

Offline only -- no deploys, no mint, no install writes (every actual filesystem write call is
intercepted; the only files this script itself creates are under ``out/``). Run from the repo
root:  py studies/overworld-topography/donor_8_17_carry_prep.py
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

OUTD = Path(__file__).with_name("out")
OUTD.mkdir(exist_ok=True)
out: dict = {}

MOD_FOLDER = "FF9CustomMap-world"
DONOR = (8, 17)
DONOR_SIZE = (2, 2)
DONOR_BLOCKS = [(8, 17), (9, 17), (9, 18)]                   # (8,18) carries no data
RESERVED = {((22, 18), (2, 2)), ((17, 18), (2, 2)), ((4, 19), (1, 1)),
           ((6, 19), (1, 1)), ((10, 19), (1, 1))}
MOD_SITES = [(6, 18), (7, 18), (6, 19), (7, 19), (8, 19)]     # comp20 + the plain islet, live

# ==== stage 0: SITE SELECTION ========================================================================
print("== stage 0: site selection ==")
GP = Path(_cfg.find_game_path(None))


def block_free_of_mod(bx, by, disc):
    rdir = GP / MOD_FOLDER / "FF9_Data" / "WorldMap" / f"Disc{disc}" / "0_1" / f"r{by}"
    if not rdir.is_dir():
        return True
    prefix = f"Block[{bx}][{by}] "
    return not any(p.name.startswith(prefix) for p in rdir.iterdir())


def clearance_ok(bx, by, min_gap=1):
    for (mx, my) in MOD_SITES:
        if max(abs(bx - mx), abs(by - my)) <= min_gap:
            return False
    return True


band_candidates = [(bx, by) for by in (17, 18) for bx in range(11, 23)]
grid = {}
for by in (16, 17, 18, 19):
    for bx in range(6, 24):
        grid[(bx, by)] = bool(_real_block_parts((bx, by), disc=1))

TARGET = (19, 17)
TSIZE = (2, 2)
target_cells = [(TARGET[0] + i, TARGET[1] + j) for j in range(TSIZE[1]) for i in range(TSIZE[0])]
checks = {}
checks["all_true_open_ocean_stock"] = all(not grid[c] for c in target_cells)
checks["free_of_mod_overrides_disc1"] = all(block_free_of_mod(*c, disc=1) for c in target_cells)
checks["free_of_mod_overrides_disc4"] = all(block_free_of_mod(*c, disc=4) for c in target_cells)
checks["clearance_from_mod_sites"] = all(clearance_ok(*c) for c in target_cells)
checks["not_reserved_footprint"] = (TARGET, TSIZE) not in RESERVED
checks["not_overlapping_any_reserved_footprint"] = not any(
    (rx <= c[0] < rx + rnx and ry <= c[1] < ry + rny)
    for c in target_cells for ((rx, ry), (rnx, rny)) in RESERVED)
print(f"  target rect {TARGET}+{TSIZE[0]}x{TSIZE[1]} = cells {target_cells}")
for k, v in checks.items():
    print(f"  {k}: {'PASS' if v else 'FAIL'}")
out["site_checks"] = checks
assert all(checks.values()), "site selection failed a gate -- do not proceed"

# ==== stage 1: DRY carry via the CLI-equivalent Python API, every write intercepted =================
print("\n== stage 1: dry carry (every write intercepted -- zero filesystem writes) ==")
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

gt = TR.GroundRetile.for_donor(DONOR, "desert", size=DONOR_SIZE, strips="auto", extra=8.0, disc=1)
print(f"  retile grass->desert: sand anchors "
      f"{[f'{s:.4f}->{d:.4f}' for (s, d) in gt.sand_anchors]}")
print(f"  recover budget: {gt.recover_budget} tris over {len(gt.recover_cells)} cells")

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
      f"-- confirms a real deploy self-mirrors to Disc4 (discmirror.mirror(), never called for "
      f"real here); the CLI has no --skip-mirror in the exact command below, so a real run mirrors")
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


carry_pt = (20, 17, 10.5, -44.5)                              # local (bx,by,lx,lz)
bx, by, lx, lz = carry_pt
wx, wz = 64.0 * bx + lx, -64.0 * by + lz
y, name, idall, topo = P.place(meshlist_for(bx, by), lx, lz, sky=True)
print(f"  OUR CARRY teleport: world ({wx},{wz})  -> y={y:.3f} mesh={name} topo={topo} "
      f"(desert mains topo 17 expected)")
assert name == "terrain" and topo == 17, "carry teleport point did not land on desert mains"
out["teleport_our_carry"] = dict(world=[wx, wz], y=round(y, 3), mesh=name, topo=topo)

dbx, dby, dlx, dlz = 9, 17, 10.5, -44.5
dwx, dwz = 64.0 * dbx + dlx, -64.0 * dby + dlz
dy_, dname, didall, dtopo = P.place(donor_meshlist_for(dbx, dby), dlx, dlz, sky=True)
print(f"  DONOR A/B teleport: world ({dwx},{dwz}) -> y={dy_:.3f} mesh={dname} topo={dtopo} "
      f"(grass mains topo 0 expected)")
assert dname == "terrain" and dtopo == 0, "donor A/B teleport point did not land on grass mains"
out["teleport_donor_ab"] = dict(world=[dwx, dwz], y=round(dy_, 3), mesh=dname, topo=dtopo)
assert abs(y - dy_) < 1e-6, "carry and donor teleport heights should be byte-identical (verbatim geometry)"

# ==== write artifact ==================================================================================
outp = OUTD / "donor_8_17_carry_prep.json"
outp.write_text(json.dumps(out, indent=1, default=str))
print(f"\n-> {outp}")
