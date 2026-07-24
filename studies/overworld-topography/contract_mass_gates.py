"""THE MASS-ANATOMY CONTRACT round -- THE GATES, v4 (2026-07-24, post-RE-audit round 3).

v4 closes the TWO fresh beats the round-2 re-audit (contract_mass_reaudit2.py) found in v3 -- both
normal/malformed-pipeline probes that beat the v3 suite:
  ROUND-2 BEAT #1 P3_R3_TENDRIL_BACKING (SEVERE, SUITE): a grass-WRAPPED thin topo-16 ecotone skin that
    RETURNS TO GRASS (the ribbon fallacy) whose only 'backing' is a compact >=130-cell dune blob reached
    through a SINGLE 1-cell-wide topo-17 tendril passed ALL THREE gates. v3 R3 gated mere 8-conn
    REACHABILITY, which a thread satisfies (reachable 131). v4 gates the realized skin<->backing
    INTERFACE -- the 4-conn cell-adjacency count between the ecotone-reachable topo-16 skin and its
    reachable desert-family backing (stock 125 pairs; a thread has 1) -- plus an EROSION-ROBUSTNESS
    corroborator (after 1-cell morphological erosion the skin must still reach backing; a thread erodes
    to 0, stock survives with 129). A remote blob bridged by a thread no longer counts as 'backed onto'.
  ROUND-2 BEAT #2 P3_R1_DOUBLED_LAKE (R1): doubling the desert tris lining an INTERNAL ocean hole made
    their hole-facing edges 2-owner, ERASING the internal-lake coast from the single-owner silhouette
    (a FALSE PASS in the UNSAFE direction -- the standoff inflated 1.333u -> 81.333u). v4 DEDUPLICATES
    coincident triangles (canonical sorted rounded-vertex-position keys) before the single-owner-edge
    extraction. Dedup is a strict NO-OP on clean geometry (0 removed on stock/rung_e/rung_d/rung_c --
    verified + reported in gate_r1 diagnostics), so the prior matrix is bit-identical; it only rescues
    the coincident-tri false PASS (the beat now measures 1.333u == its control -> FAIL).
Every v4 fix is measured on stock + every control + all NINE probes (four v1 + three round-1 + two
round-2 + the two round-2 controls). Stock's interface (125) + erosion-survival (129) are pinned into
calibration bit-for-bit. NO gate was weakened and NO candidate special-cased (the round-2 controls
STILL fail).

Builds the three specified-not-built gates from the Rung E postmortem
(GROUND-FAMILY-DECODE-2026-07-19.md "## Rung E", "THE RIBBON FALLACY"). Each gate has a
STOCK-MEASURED ceiling/floor and judges a candidate build (staged loose-.ff9mesh mod tree, or the
stock ecotone site read as a candidate) PASS/FAIL. The three lanes measured stock and were each
independently falsified; where the falsifier CONFIRMED a number it is pinned here as the ceiling,
and where a falsifier CORRECTED a value THE CORRECTED VALUE WINS (documented per gate).

v2 closed the four holes the FIRST audit (contract_mass_audit_probe.py) found in v1. v3 closes the
THREE fresh beats the RE-audit (contract_mass_reaudit.py) then found in v2 -- v2 reproduced the matrix
and killed all four v1 probes but was BEATEN by three normal/malformed-pipeline probes:
  BEAT #1 P2_SUITE_FAKE_BACKING (SUITE, normal-pipeline): a grass-WRAPPED topo-16 ecotone patch that
    returns to grass (no dune backing behind the skin) + a DISJOINT 130-cell dune blob elsewhere passed
    ALL THREE gates. R3 counted backing PRESENCE in the region, never adjacency to the skin. v3 gates R3
    on the ecotone-REACHABLE backing (8-conn flood from the boundary-desert skin through the mass cells).
  BEAT #2 P2_R2_DEEP_TEETH (R2 arrangement, normal-pipeline): deep interdigitated grass teeth inflate
    BFS band-0 so a checkerboard comb that genuinely penetrates band-2..4 read fringe 0.667 (>=0.60) --
    the aggregate fringe ratio is blind to a BIMODAL depth distribution. v3 adds a PENETRATION ceiling
    (fraction of dressed tris at band>=2 <= 0.25; stock 0.1231).
  BEAT #3 P2_R2_XFAM_MISLABEL (R2 population, malformed-build): the v2 "label-blind" body hard-filtered
    `fam != 'desert'`, silently dropping cross-family UV-dressed tris (a gd-decal UV tagged topo-49/
    fam=None) and reporting 0 disagreements. v3 makes the body UV-DRIVEN + family-blind (only the legit
    gd-on-grass / dd-on-dunes opposite-side halves are excluded, and those are counted); every other
    UV-dressed tri lands in the body with its fam/topo disagreement COUNTED + reported.
Each v3 fix is measured on stock + every control + all seven probes (four v1 + the three fresh beats);
the corrected populations reproduce stock's ceilings BIT-FOR-BIT (measure_v2.json). NO gate was weakened
and NO candidate special-cased.

  GATE R1 -- REALIZED-BOUNDARY STANDOFF (floors; candidate must stand >= floor from ALL coasts).
             Lane A / falsifier A CONFIRMED to 3 decimals, two code-disjoint implementations:
             boundary-cell 39.953u / straddle-cell 44.635u / body-tri 42.968u (stock ecotone,
             13-15/11-12; floors UNCHANGED in v2). CONVENTION LAW (falsifier-confirmed): on a STAGED
             mint the sea-vertex convention is INVALID (Rung E's staged Sea4 is a full-block 64x64u
             backing plane -> false 0.612u) -- use the validated LAND-PERIMETER mesh-edge convention
             on staged bytes; on STOCK use the sea-vertex convention (== coastal-filtered mesh-edge
             to the mm), and NEVER raw mesh-edge without the 5u coastal filter (a bare topo-0
             internal seam fakes a 6.69u floor on stock).
             THE ALL-COASTS LAW (v2, written into gate_r1's docstring + spec): the standoff is
             measured to EVERY coast the loaded region owns -- INCLUDING the desert lobe's OWN coast,
             not just the grass lobe's. That IS the mass-thickness enforcement: a desert lobe too
             thin to be a real mass puts its own coastline near the ecotone waist, so its body-tri /
             boundary-cell standoff to that near coast falls below the floor and the gate rightly
             FAILS. The land-perimeter (single-owner terrain edge) silhouette and the stock
             sea-vertex scan are BOTH whole-region, so both already honour this; v2 makes it law.
             THE STAGED-UNDERLAP DETECTOR (v2, audit hole #4): if staged terrain near the measured
             boundary lies UNDER a staged full-block sea plane, the land-perimeter silhouette reports
             an inflated standoff while the visible waterline is close. gate_r1 now flags such a
             build CONVENTION-INVALID (a distinct FAILING status), NOT a PASS. It rescues only a
             FALSE PASS: a build whose land-perimeter already fails the floor stays a plain standoff
             FAIL (so Rung E -- perimeter 31.6u < 39.953u AND its ecotone underlaps a full-block Sea4
             -- fails on STANDOFF, its underlap merely REPORTED). Internal-seam contamination errs the
             land-perimeter SMALL (a false-FAIL, the safe direction) and is left as reported-not-fixed.
             THE COINCIDENT-TRI DEDUP (v4, round-2 audit BEAT #2): coincident-duplicate triangles are
             DEDUPLICATED (canonical sorted rounded-vertex-position keys) before the single-owner-edge
             silhouette, so doubled hole-lining tris cannot make an internal-lake coast 2-owner and
             erase it from the silhouette (a false PASS in the UNSAFE direction). No-op on clean
             geometry (0 removed on stock/rung_e/rung_d/rung_c -- reported in the R1 diagnostics).

  GATE R2 -- SATURATION + ARRANGEMENT (row-shape advisory, spine report-only). Lane B / falsifier B:
             the saturation ceiling is CONFIRMED to the byte -- grass-decal 0.5024 / any-decal 0.6351
             (Rung E 0.7569). v2 fixes two audit holes:
             (#2 LABEL-BLIND POPULATION, v3 round-2 BEAT #3) the body population + "dressed"
             classification are UV-DRIVEN + FAMILY-BLIND: a tri is counted iff its UV is a desert-mains
             rect OR a gd/dd decal rect, INDEPENDENT of its fam/topo -- the ONLY exclusions are the two
             legit OPPOSITE-side transition halves (gd-decal on fam==grass, dd-decal on fam==dunes),
             which are themselves counted + reported. topo/fam is a CROSS-CHECK column: every counted
             tri whose fam!=desert or topo!=16 is a DISAGREEMENT, COUNTED into the body + reported,
             never silently dropped (the v2 hole: it hard-filtered fam!=desert, dropping a gd-decal-UV
             tri tagged topo-49/fam=None with 0 disagreements reported). Recomputed on stock this
             reproduces 422 body / 0.5024 / 0.6351 BIT-FOR-BIT (0 disagreements, 180 grass-side gd + 60
             dunes-side dd excluded+reported) -- the ceilings do NOT move. P_R2B (96 UV-dressed tris
             tagged topo-17) and P2_R2_XFAM_MISLABEL (220 gd-decal tris tagged topo-49/fam=None) now
             land IN the body -> saturation ~0.92-0.98 -> FAIL.
             (#1 ARRANGEMENT GATE, the mandate's core; v3 adds PENETRATION) THREE stock-measured
             arrangement statistics gate a comb the aggregate cannot see: FRINGE CONCENTRATION (fraction
             of the dressed body tris at BFS band-0, hugging the grass|desert boundary) >= 0.60 -- stock
             0.8022, a boundary FRINGE that decays inland; a depth-uniform picket comb spreads dressing
             across bands and reads low. PENETRATION FRACTION (fraction of dressed body tris at BFS
             band>=2) <= 0.25 -- stock 0.1231; a BIMODAL comb (a big band-0 fringe hiding a detached
             band-2..4 checkerboard -- audit BEAT #2 P2_R2_DEEP_TEETH -- reads fringe 0.667 PASS yet 33%
             penetration) that fringe alone MISSES. These are NOT the demoted spine: BFS band-depth is
             convention-free, whereas the spine's "the plain cell directly behind" needed an unstable
             direction convention (which reversed under the falsifier's robust proxy). AND FLOATING
             COMPONENTS (dressed cells whose 8-conn component touches no boundary cell) == 0 -- stock 0
             over 9 components / 158 decal cells; a checkerboard comb strands inland patches. Row-shape
             (pooled both-family-sides row0) and the spine are COMPUTED + REPORTED but ADVISORY / not
             gated (per falsifier B).

  GATE R3 -- INLAND-BACKING EXTENT (topological, NOT shape). Lane C / falsifier C CONFIRMED: NO
             cell-shape metric (area/interior-fraction/inscribed-radius/grass-ecotone-fraction)
             separates the Rung E ribbon from stock (any_metric_separates=False) -- REPORTED, never
             gated. The discriminator is a desert-family MASS inland of the topo-16 skin. v2 fixed
             audit hole #3 (v1 fired on n>=1 -- ONE token inland cell passed): the inland desert-family
             backing must be a CONNECTED MASS of >= FLOOR cells, not a token. v3 (round-2 BEAT #1)
             adds ADJACENCY: the gate floods 8-conn from the boundary-desert skin THROUGH the mass
             cells {16,17,19,20,41} and verdicts on the largest ecotone-REACHABLE backing component,
             not mere presence in the region -- a DISJOINT dune blob dropped elsewhere (audit BEAT #1
             P2_SUITE_FAKE_BACKING) the skin does not reach no longer counts. FLOOR = 130 cells,
             anchored by TWO corroborating sources -- stock's realized backing is ONE 143-cell dunes
             component that IS reachable (stock reachable == whole-region == 143), and THE DUNES
             SIZE-CLASS LAW (stock's smallest real dunes component ~130 cells, no freckles). Backing
             grounds = topo in {17,19,20 plain desert/dirt, 41 dunes} (the desert-family interior MINUS
             the topo-16 ecotone skin). Rung E returns to grass (reachable backing 0 -> FAIL); P_R3's
             token topo-17 cell -> 1 -> FAIL; FAKE_BACKING's disjoint blob -> reachable 0 -> FAIL. n=1
             provenance is LOUD: the map has ONE grass|desert junction, a census not a sample; the
             floor leans on the WIDE margin (stock reachable 143 vs comb-token/disjoint) + the prior.
             THE SKIN<->BACKING INTERFACE (v4, round-2 audit BEAT #1): reachability alone is satisfied
             by a 1-cell-wide thread to a remote blob (P3_R3_TENDRIL_BACKING: a grass-wrapped skin
             bridged to a >=130 dune blob by ONE topo-17 tendril passed reachable 131). v4 ADDS: the
             ecotone-reachable topo-16 skin must meet the reachable backing across a BROAD 4-conn
             interface (>= 20 cell-adjacency pairs; stock 125, a thread 1) AND the connection must
             survive 1-cell morphological erosion (a thread erodes to 0, stock survives 129). The
             thread's interface 1 < 20 and erosion 0 -> R3 FAIL. Both are convention-free; the interface
             floor leans on the WIDE gap (thread ~1-2 vs stock 125), n=1 loud.

READ-ONLY vs the game install: X.read_block (stock disc-1 bytes) + reading STAGED (never deployed)
override bytes under out/rung_e|rung_d/FF9CustomMap-world and (read-only) the foreign worktree's
mixed_biome_mint/FF9CustomMap-world. ZERO writes to the game install, no deploy, no mirror, no
--apply, no git commits. Files this round writes: contract_mass_gates.py, contract_mass_probe_rerun.py,
and under out/contract_mass/: gates_selftest.json + annotations.json (+ the probe rerun's json).

THE FOUR CRITIC GAPS (also carried in out/contract_mass/annotations.json for a Rung-F reader):
  (i)   SPINE convention is CANONICALLY NONE -- three conventions (lane ray-march, falsifier
        graph-BFS, robust proxy) disagree in magnitude AND direction. Spine is REPORT-ONLY FOREVER.
  (ii)  EVERY primary ceiling is n=1 -- the map has EXACTLY ONE grass|desert site (verified,
        n_components=1 map-wide). No leave-one-site-out is possible; the gates are a CENSUS of the
        only lawful instance. Each gate leans on WIDE-margin signals, never a knife-edge on stock.
  (iii) sites.json `grass_adjacent` means 8-conn cell PROXIMITY, not mesh-edge sharing: the 777-cell
        topo-17 mass is "grass_adjacent" yet shares ZERO grass|desert MESH EDGES map-wide (critic.py:
        n_topo17_grass_shared_edges=0). A Rung-F reader must not be whipsawed -- topo-17 plain desert
        never MEETS grass; the topo-16 skin is the only thing that does.
  (iv)  THE ALL-COASTS LAW (see GATE R1) -- standoff is measured to all coasts, the desert lobe's own
        included; that is the mass-thickness enforcement.

Reuses seam_null_recon.py's proven FAM_OF/classify_tri/edge_index/cell_distance_bfs VERBATIM.
`mode` "warn" vs "enforce" mirrors world/orphangate.py + the wang-carry gate.

Run:  py contract_mass_gates.py   (cwd = studies/overworld-topography)
"""
from __future__ import annotations

import glob
import json
import math
import re
import sys
import time
from collections import Counter, defaultdict, deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

import seam_null_recon as SNR                        # noqa: E402  proven FAM_OF/classify_tri/edge_index/cell_distance_bfs
from ff9mapkit.world import extract as X             # noqa: E402
from ff9mapkit.world import mesh as M                # noqa: E402

CELL = 4.0
BLOCK = 64.0
OUT = HERE / "out" / "contract_mass" / "gates_selftest.json"
ANNOT = HERE / "out" / "contract_mass" / "annotations.json"

# ---- the map's ONE grass|desert ecotone site (scout census: n_components=1 map-wide) --------------
ECOTONE_CORE = sorted({(bx, by) for bx in (13, 14, 15) for by in (11, 12)})

SEA_PARTS = ("sea1", "sea2", "sea3", "sea4", "sea5", "beach1", "beach2")
SEA_PARTS_CAP = ("Sea1", "Sea2", "Sea3", "Sea4", "Sea5", "Beach1", "Beach2")

# label-blind desert-family topos (FAM_OF -> "desert"): the R2 body population keys on this SET, not
# on topo==16, so a UV-dressed tri mislabelled topo-17 (audit hole #2) still lands in the body.
DESERT_TOPOS = frozenset(t for t, f in SNR.FAM_OF.items() if f == "desert")   # {16,17,19,20}
# R3 backing grounds = the desert-family INTERIOR beyond the topo-16 ecotone skin: plain desert/dirt
# (17,19,20) + dunes (41). topo-16 is the skin itself and is deliberately EXCLUDED.
BACKING_TOPOS = frozenset({17, 19, 20, 41})
# R3 v3 ADJACENCY (audit BEAT #1): the mass through which the ecotone flood reaches its backing =
# the skin (16) + the backing interior (17,19,20,41). The flood seeds on the boundary-desert skin and
# walks 8-conn through these; a backing cell only counts if it is reachable = "backed onto".
MASS_TOPOS = frozenset({16, 17, 19, 20, 41})

# ====================================================================================================
# THE STOCK-MEASURED CEILINGS / FLOORS -- each with a one-line provenance. These are the confirmed
# (falsifier-CONFIRMED, or falsifier-CORRECTED-value-wins) numbers; main() ALSO re-measures them live
# from stock and asserts the live value matches (CALIBRATE THE INSTRUMENT), so the constants can never
# silently drift from the bytes.
# ====================================================================================================
GATE_CEILINGS = {
    # R1 floors (u) -- Lane A + falsifier A CONFIRMED, two code-disjoint impls to 3 decimals, r2-widen-stable
    "R1.boundary_cell_to_coast_floor_u": (39.953,
        "Lane A stock ecotone boundary-cell-centre -> nearest sea vertex; falsifier A CONFIRMED (two "
        "code-disjoint impls, radius-2 ring stable)."),
    "R1.straddle_cell_to_coast_floor_u": (44.635,
        "Lane A stock ecotone straddle-cell-centre -> coast; falsifier A CONFIRMED exactly."),
    "R1.body_tri_to_coast_floor_u": (42.968,
        "Lane A stock ecotone topo-16 body-tri-centroid -> coast; falsifier A CONFIRMED exactly."),
    # R2 ceilings -- Lane B + falsifier B CONFIRMED to the byte on the topo-16 body
    "R2.saturation_grass_decal_ceiling": (0.5024,
        "Lane B stock topo-16 body grass-decal saturation (apples-to-apples w/ Rung E's own 75.7% "
        "metric); falsifier B CONFIRMED exactly (212/422)."),
    "R2.saturation_any_decal_ceiling": (0.6351,
        "Lane B stock topo-16 body any-ecotone-decal saturation (the harder virgin-mains ceiling); "
        "falsifier B CONFIRMED exactly ((212+56)/422)."),
    # R2 ARRANGEMENT (v2, audit hole #1 -- the mandate's core) -------------------------------------
    "R2.fringe_concentration_floor": (0.60,
        "v2 ARRANGEMENT PRIMARY. Fraction of the label-blind dressed body tris sitting at BFS band-0 "
        "(cells touching the grass|desert boundary) must be >= 0.60. Stock live-measured 0.8022 (a "
        "boundary FRINGE that decays inland); Rung E 0.4093; the audit picket combs ~0.14-0.33. "
        "Floor 0.60 = margin 0.20 below stock, comfortably above every failing arrangement. "
        "CONVENTION-FREE (BFS depth), so NOT the demoted spine. n=1 -> leans on the wide gap."),
    "R2.penetration_ge2_fraction_ceiling": (0.25,
        "v3 ARRANGEMENT PENETRATION (round-2 audit BEAT #2). Fraction of the label-blind dressed body "
        "tris sitting at BFS band>=2 (>=8u inland, or unreachable) must be <= 0.25. Stock live-measured "
        "0.1231 (the fringe decays out by band-1: band hist 215/20/22/8/2/1); the audit's DEEP_TEETH "
        "bimodal comb reads ~0.33 (a big boundary fringe hiding a detached band-2..4 checkerboard, "
        "which FRINGE alone misses). Ceiling 0.25 = margin 0.13 above stock, comfortably below the "
        "penetrating comb. Lawful decaying/2-cell-hug fringes (organic variants, sawtooth) read 0.0. "
        "CONVENTION-FREE (BFS depth). n=1 -> leans on the wide gap between a decayed fringe and a "
        "penetrating comb, not a knife-edge on stock's exact 0.1231."),
    "R2.floating_components_max": (0,
        "v2 ARRANGEMENT COMPANION. Count of dressed-cell 8-conn components that touch NO boundary "
        "cell (within cheby<=1) must be <= 0. Stock 0 floating over 9 components / 158 decal cells "
        "(falsifier B / lane B CONFIRMED); a checkerboard comb strands inland patches. Clean stock "
        "invariant, n=1."),
    # R2 ROW-SHAPE (advisory, retained from v1) -----------------------------------------------------
    "R2.row0_fraction_stock_pooled": (0.199,
        "Lane B stock pooled BOTH-family-sides STRIPS row0 fraction (n=392); falsifier B reproduced "
        "0.199 exactly. ADVISORY only (falsifier B: MIXED verdict, per-side signal)."),
    "R2.row0_ratio_ceiling": (1.80,
        "ADVISORY secondary: candidate pooled-row0-fraction / stock's 0.199 must stay <= 1.80. "
        "Stock=1.00 passes; Rung E=2.70 fails. n=1 -> advisory, saturation+arrangement are PRIMARY."),
    "R2.row0_fraction_ceiling_abs": (0.35,
        "ADVISORY absolute companion: pooled row0 fraction <= 0.35 (stock 0.199 << 0.35 < 0.538 "
        "Rung E). Advisory midpoint, n=1. A row spike fails only if BOTH ratio AND abs are exceeded."),
    # R3 -- INLAND-BACKING EXTENT (v2, audit hole #3) ----------------------------------------------
    "R3.backing_mass_floor_cells": (130,
        "v2 R3 PRIMARY. The inland desert-family backing (topo {17,19,20,41} = plain desert/dirt + "
        "dunes, EXCLUDING the topo-16 skin) must form a connected 8-conn mass whose LARGEST component "
        ">= 130 cells. TWO corroborating sources: stock's realized backing is ONE 143-cell dunes "
        "component (== waist census dunes_lobe=143), and THE DUNES SIZE-CLASS LAW (smallest real "
        "dunes component ~130 cells). Floor 130 -> stock 143 passes (margin 13); probe token cell (1) "
        "+ Rung E (0) fail. n=1 site -> leans on the wide margin + the independent size-class prior."),
    "R3.stock_realized_backing_cells": (143,
        "Lane C + falsifier C CONFIRMED: stock's topo-16 band backs onto a single 143-cell dunes "
        "component (topo-41) inland; Rung E's band returns to grass on all sides (backing 0). REPORTED "
        "reference, not a ceiling."),
    # R3 v4 SKIN<->BACKING INTERFACE (round-2 audit BEAT #1 -- the anti-thread waist gate) -----------
    "R3.skin_backing_interface_floor_pairs": (20,
        "v4 R3 COMPANION (round-2 audit BEAT #1). The ecotone-reachable topo-16 skin must meet the "
        "ecotone-reachable desert-family backing across a BROAD 4-conn interface: the count of 4-conn "
        "cell-adjacency pairs between the two must be >= 20. Stock live-measured 125 pairs (73 skin "
        "cells touch backing over a 68-cell backing front). A 1-cell-wide tendril (audit BEAT #1 "
        "P3_R3_TENDRIL_BACKING, which satisfied v3's mere 8-conn reachability) has interface 1; the "
        "control has 0. Floor 20 = margin 6.25x below stock (125), >=10x above any thread -- an "
        "interface of 20 cells IS a genuine broad waist (the intent), so the floor cannot reject a "
        "lawful two-lobe mass. n=1 site -> leans on the WIDE gap between a thread (~1-2) and a front "
        "(125), never a knife-edge on stock's exact 125."),
    "R3.stock_skin_backing_interface_pairs": (125,
        "v4 live-measured stock reference: the topo-16 skin meets its topo-41 dunes backing across 125 "
        "4-conn cell-adjacency pairs (73 distinct skin cells / 68 distinct backing cells). Corroborates "
        "the falsifier-confirmed '151 dunes-neighbour tris' broad front. REPORTED reference; pinned in "
        "calibration so the constant cannot drift from the bytes."),
    "R3.stock_erosion_survive_backing_cells": (129,
        "v4 live-measured stock reference: after 1-cell morphological erosion of the mass, the skin "
        "still reaches 129 backing cells (the broad waist survives). The gate requires erosion-survival "
        "> 0 (scale-free anti-thread corroborator: a 1-cell tendril erodes to 0, stock survives). "
        "REPORTED reference; pinned in calibration."),
}


def ceil(key):
    return GATE_CEILINGS[key][0]


def log(m):
    print(m, flush=True)


# ====================================================================================================
# candidate loading -- a candidate is either the STOCK ecotone site (mod_dir=None, read stock bytes)
# or a STAGED loose-.ff9mesh mod tree (mod_dir=<FF9CustomMap-world>, override where staged else stock).
# ====================================================================================================
def detect_footprint(mod_dir):
    pat = re.compile(r"Block\[(\d+)\]\[(\d+)\] Terrain\.ff9mesh$")
    blocks = set()
    for f in glob.glob(str(Path(mod_dir) / "**" / "*Terrain.ff9mesh"), recursive=True):
        mm = pat.search(f.replace("\\", "/"))
        if mm:
            blocks.add((int(mm.group(1)), int(mm.group(2))))
    return sorted(blocks)


def _tris_from_blockmesh(bm, bx, by):
    ox, oz = X.block_world_origin(bx, by)
    out = []
    for tri in bm.tris:
        idall0 = int(round(bm.tangents[tri[0]][0]))
        topo = X.decode_id(idall0)["topograph"]
        fam = SNR.FAM_OF.get(topo)
        w = [(bm.verts[j][0] + ox, bm.verts[j][1], bm.verts[j][2] + oz) for j in tri]
        uv = [(float(bm.uvs[j][0]), float(bm.uvs[j][1])) for j in tri]
        cx = sum(p[0] for p in w) / 3.0
        cz = sum(p[2] for p in w) / 3.0
        cell = (math.floor(cx / CELL), math.floor(cz / CELL))
        out.append(dict(block=(bx, by), topo=topo, idall=idall0, fam=fam, w=w, uv=uv, cell=cell))
    return out


def load_region(blocks, mod_dir=None):
    """Override where a Terrain.ff9mesh exists under mod_dir (staged), else real stock disc-1 bytes.
    Mirrors seam_null_recon.load_tris(source='deployed') discipline but pointed at a STUDY-LOCAL
    (never the live game install) mod tree. mod_dir=None -> pure stock."""
    tris = []
    src = {}
    for (bx, by) in blocks:
        bm = None
        if mod_dir is not None:
            rel = M.override_relpath(1, bx, by, part="Terrain")
            p = Path(mod_dir) / rel
            if p.exists():
                bm = M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part="terrain")
                src[(bx, by)] = "staged"
        if bm is None:
            try:
                bm = X.read_block(bx, by, disc=1, part="terrain")
            except (ValueError, FileNotFoundError):
                continue
            src.setdefault((bx, by), "stock")
        tris.extend(_tris_from_blockmesh(bm, bx, by))
    for i, t in enumerate(tris):
        t["gid"] = i
    return tris, src


def scan_sea_vertices(blocks):
    """Real stock sea/beach vertices (x,z) over the given blocks (only the coastal ones return data)."""
    pts = []
    for (bx, by) in blocks:
        ox, oz = X.block_world_origin(bx, by)
        for part in SEA_PARTS:
            try:
                bm = X.read_block(bx, by, disc=1, part=part)
            except (ValueError, FileNotFoundError):
                continue
            for v in bm.verts:
                pts.append((v[0] + ox, v[2] + oz))
    return pts


def dedup_coincident_tris(tris, tol=1e-3):
    """v4 (round-2 audit BEAT #2, P3_R1_DOUBLED_LAKE). Drop coincident-duplicate triangles -- two tris
    occupying the SAME three vertex POSITIONS (winding-independent) -- keeping the first occurrence. A
    coincident duplicate makes every one of its edges 2-owner, which silently ERASES that edge from the
    single-owner land silhouette; an adversary doubling the tris lining an internal ocean hole thereby
    makes the hole's coast VANISH and inflates the standoff (a FALSE PASS, the unsafe direction). Dedup
    canonicalises on the sorted tuple of rounded (x,y,z) positions (tol=1e-3u). It is a strict NO-OP on
    clean geometry (stock/rung_e/rung_d/rung_c all remove 0 -- verified + reported in gate_r1
    diagnostics), so the prior matrix is unchanged; it only removes genuinely degenerate coincident
    copies (a plausible overlapping-carry mint artifact). Returns (deduped_list, n_removed)."""
    seen = set()
    out = []
    removed = 0
    for t in tris:
        key = tuple(sorted(tuple(round(c / tol) for c in p) for p in t["w"]))
        if key in seen:
            removed += 1
            continue
        seen.add(key)
        out.append(t)
    return out, removed


def single_owner_edges(tris):
    """Every tri edge owned by exactly ONE triangle over `tris` (position-welded, SNR.edge_index's own
    key convention) = the land silhouette. Returns [((x1,z1),(x2,z2)), ...] in world XZ.

    v4: coincident-duplicate tris are DEDUPLICATED first (dedup_coincident_tris) so a doubled hole-lining
    tri cannot drop its edges from the single-owner silhouette by making them 2-owner (audit BEAT #2).
    Dedup is a no-op on clean geometry, so the silhouette (hence every R1 measurement) is bit-identical
    on stock/rung_e/rung_d/rung_c; it only rescues the coincident-tri false PASS."""
    deduped, n_removed = dedup_coincident_tris(tris)
    single_owner_edges.last_n_removed = n_removed          # reported in gate_r1 diagnostics
    eo = SNR.edge_index(deduped)
    by_gid = {t["gid"]: t for t in deduped}
    segs = []
    for e, owners in eo.items():
        if len(owners) == 1:
            (p1, p2) = tuple(e)
            segs.append(((p1[0], p1[2]), (p2[0], p2[2])))
    return segs, by_gid


def moore_ring(blocks, radius):
    out = set()
    for (bx, by) in blocks:
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                if M.block_in_grid(bx + dx, by + dy):
                    out.add((bx + dx, by + dy))
    return sorted(out)


def load_candidate(name, mod_dir, core_blocks=None):
    """Returns the full candidate view used by all three gates."""
    is_staged = mod_dir is not None
    core = core_blocks if core_blocks is not None else detect_footprint(mod_dir)
    core_set = set(core)
    region_blocks = moore_ring(core, 2)                 # r2: coast reference / inland backing search
    tris, src = load_region(region_blocks, mod_dir=mod_dir)

    # boundary/straddle/body over the CORE (topo-16 body + grass|desert straddle live in the footprint)
    by_gid = {t["gid"]: t for t in tris}
    eo = SNR.edge_index(tris)
    boundary_cells = set()
    n_gd_edges = 0
    for e, owners in eo.items():
        fams = {by_gid[g]["fam"] for g in owners}
        if fams == {"grass", "desert"}:
            n_gd_edges += 1
            for g in owners:
                t = by_gid[g]
                if t["block"] in core_set:
                    boundary_cells.add(t["cell"])
    core_tris = [t for t in tris if t["block"] in core_set]
    cell_fams = defaultdict(set)
    for t in core_tris:
        if t["fam"]:
            cell_fams[t["cell"]].add(t["fam"])
    straddle_cells = {c for c, f in cell_fams.items() if f == {"grass", "desert"}}
    body_tris = [t for t in core_tris if t["topo"] == 16]

    return dict(
        name=name, is_staged=is_staged, mod_dir=str(mod_dir) if mod_dir else None,
        core_blocks=[list(b) for b in core], core_set=core_set,
        region_blocks=region_blocks, tris=tris, core_tris=core_tris, by_gid=by_gid,
        boundary_cells=boundary_cells, straddle_cells=straddle_cells, body_tris=body_tris,
        n_gd_edges=n_gd_edges, cell_fams=cell_fams, block_source={f"{k[0]},{k[1]}": v for k, v in src.items()},
    )


# ====================================================================================================
# distance primitives
# ====================================================================================================
def cell_center(c):
    return (c[0] * CELL + CELL / 2.0, c[1] * CELL + CELL / 2.0)


def tri_centroid_xz(t):
    return (sum(p[0] for p in t["w"]) / 3.0, sum(p[2] for p in t["w"]) / 3.0)


def min_dist_to_points(px, pz, pts):
    best = None
    for (sx, sz) in pts:
        d = math.hypot(px - sx, pz - sz)
        if best is None or d < best:
            best = d
    return best


def point_seg_dist(px, pz, seg):
    (x1, z1), (x2, z2) = seg
    dx, dz = x2 - x1, z2 - z1
    l2 = dx * dx + dz * dz
    if l2 < 1e-12:
        return math.hypot(px - x1, pz - z1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (pz - z1) * dz) / l2))
    return math.hypot(px - (x1 + t * dx), pz - (z1 + t * dz))


def min_dist_to_segs(px, pz, segs):
    best = None
    for seg in segs:
        d = point_seg_dist(px, pz, seg)
        if best is None or d < best:
            best = d
    return best


# ====================================================================================================
# LABEL-BLIND DESERT-SIDE BODY (v2, audit hole #2) -- the shared R1/R2 population.
# A body tri is a desert-FAMILY tri (topo in DESERT_TOPOS, via FAM_OF -> fam=="desert") whose UV
# classifies as a desert mains rect OR a gd/dd decal rect. The topo id is a CROSS-CHECK column only:
# a tri that is UV-dressed but tagged a non-16 desert topo (audit probe P_R2B) STILL lands in the
# body (it is fam=="desert"), so it cannot hide from the saturation ceiling. Disagreements between
# the label-blind population and the old topo==16 convention are COUNTED + reported, never resolved.
# ====================================================================================================
def label_blind_desert_body(core_tris):
    """v3 (round-2 fix, audit BEAT #3): the body is UV-DRIVEN and family-BLIND -- a tri lands in the
    desert body iff its UV classifies (INDEPENDENT of its fam/topo tag) as a grass|desert decal, a
    desert|dunes decal, or a desert-mains rect. The ONLY tris EXCLUDED are the two LEGITIMATE
    OPPOSITE-side transition halves -- a gd-decal on fam==grass (stock's grass-side transition tile,
    n=180) and a dd-decal on fam==dunes (stock's dunes-side tile, n=60) -- and those exclusions are
    themselves COUNTED + reported. Every other UV-dressed tri lands in the body even when its
    fam/topo says non-desert (audit probe P2_R2_XFAM_MISLABEL: gd-decal UV tagged topo-49/fam=None is
    NOT the grass side, so it is COUNTED, and the fam/topo disagreement is REPORTED, never silently
    dropped). Reproduces stock 422/0.5024/0.6351 BIT-FOR-BIT (0 topo!=16 + 0 fam!=desert disagreements,
    180 grass-side gd + 60 dunes-side dd excluded) because stock's own desert-body decals are all
    topo-16/fam-desert -- so the ceilings do NOT move (measure_v2.json). The v2 module claimed a
    label-blind body but hard-filtered `fam != 'desert'`, silently dropping cross-family UV-dressed
    tris (topo 41/49/58/59) and reporting 0 disagreements -- the overreach this v3 closes."""
    body = []
    n_topo16 = 0
    n_non16 = 0
    n_fam_not_desert = 0
    excluded_grass_side_gd = 0           # legit grass-side of a gd transition tile (reported)
    excluded_dunes_side_dd = 0           # legit dunes-side of a dd transition tile (reported)
    fam_disagreement = Counter()         # fam of every COUNTED tri whose fam != desert (the meta-law)
    for t in core_tris:
        k_gd = SNR.classify_strip_pair(t["uv"], SNR.GD_DU, SNR.GD_DV)
        k_dd = SNR.classify_strip_pair(t["uv"], SNR.DD_DU, SNR.DD_DV)
        if k_gd is not None:
            if t["fam"] == "grass":                 # legit grass side -> excluded, reported
                excluded_grass_side_gd += 1
                continue
            cls, detail = "strip_grass_desert", k_gd
        elif k_dd is not None:
            if t["fam"] == "dunes":                 # legit dunes side -> excluded, reported
                excluded_dunes_side_dd += 1
                continue
            cls, detail = "strip_desert_dunes", k_dd
        elif SNR.in_rect(t["uv"], SNR.RECTS["desert"]):
            cls, detail = "mains_own", "desert"
        else:
            continue
        body.append((t, cls, detail))
        if t["topo"] == 16:
            n_topo16 += 1
        else:
            n_non16 += 1
        if t["fam"] != "desert":
            n_fam_not_desert += 1
            fam_disagreement[str(t["fam"])] += 1
    xcheck = dict(
        n_body=len(body), n_topo16=n_topo16, n_topo_not16=n_non16,
        n_fam_not_desert=n_fam_not_desert, fam_disagreement=dict(fam_disagreement),
        excluded_grass_side_gd=excluded_grass_side_gd, excluded_dunes_side_dd=excluded_dunes_side_dd,
        topo_hist=dict(Counter(t["topo"] for (t, _c, _d) in body)),
        note="UV-DRIVEN, family-blind body: a tri is counted iff its UV is a gd/dd decal or desert-mains "
             "rect, EXCEPT the legit gd-on-grass + dd-on-dunes opposite-side halves (excluded + counted). "
             "n_topo_not16 / n_fam_not_desert = DISAGREEMENT counts (COUNTED into the body + reported, "
             "never silently dropped) -- e.g. a gd-decal UV tagged topo-49/fam=None lands here.")
    return body, xcheck


# ====================================================================================================
# GATE R1 -- REALIZED-BOUNDARY STANDOFF
# ====================================================================================================
def gate_r1(cand, *, mode="enforce", tol=1e-3):
    """Measure the candidate's three realized-boundary standoffs (boundary-cell / straddle-cell /
    body-tri -> coast) and judge each against the confirmed stock floor.

    THE ALL-COASTS LAW (v2): the standoff is measured to EVERY coast the loaded region owns -- the
    desert lobe's OWN coast included, not only the grass lobe's. On a staged mint the coast is the
    single-owner terrain-edge silhouette of the WHOLE region (every land edge, so the desert lobe's
    own shoreline is in it); on stock it is the sea-vertex scan over the whole coastal Moore ring.
    That is the mass-thickness enforcement: a desert lobe too thin to be a real mass has its own
    coast near the ecotone waist, so its body-tri / boundary-cell standoff to that near coast drops
    below the floor and the gate FAILS.

    CONVENTION: staged mint -> land-perimeter mesh-edge (sea meshes are synthetic full-block planes,
    invalid); stock -> sea vertices (== coastal-filtered mesh-edge to the mm). Never raw mesh-edge
    without the coastal restriction on stock. Floors are convention-independent on stock (falsifier
    A), so a staged mint measured by land-perimeter is directly comparable.

    THE STAGED-UNDERLAP DETECTOR (v2): if staged terrain near the measured boundary lies UNDER a
    staged full-block sea plane, the land-perimeter silhouette over-reports the standoff while the
    visible waterline is close. The gate flags CONVENTION-INVALID (a FAILING status) -- but ONLY to
    rescue a FALSE PASS: a build whose land-perimeter already fails the floor stays a plain standoff
    FAIL (Rung E). Internal-seam contamination errs the perimeter SMALL (a false-FAIL, the safe
    direction) and is left reported-not-fixed."""
    floors = dict(boundary_cell=ceil("R1.boundary_cell_to_coast_floor_u"),
                  straddle_cell=ceil("R1.straddle_cell_to_coast_floor_u"),
                  body_tri=ceil("R1.body_tri_to_coast_floor_u"))
    boundary_pts = [cell_center(c) for c in cand["boundary_cells"]]
    straddle_pts = [cell_center(c) for c in cand["straddle_cells"]]
    # v2: body points from the LABEL-BLIND desert body (fam==desert + UV), not the topo==16 slice.
    lb_body, _lb_x = label_blind_desert_body(cand["core_tris"])
    body_pts = [tri_centroid_xz(t) for (t, _c, _d) in lb_body]

    convention = "land_perimeter_mesh_edge" if cand["is_staged"] else "sea_vertex"
    convention_invalid = False
    diagnostics = {}
    if cand["is_staged"]:
        # land silhouette over the whole loaded region (ALL-COASTS: every land edge incl. the desert
        # lobe's own shoreline) -- single-owner terrain edges = the mint's coastline. Internal seams
        # do not bite because the measured objects are spatially separated from any internal seam
        # (Lane A + falsifier A validated this reproduces the falsifier's 34.98/34.45 on Rung E).
        segs, _ = single_owner_edges(cand["tris"])
        diagnostics["n_land_perimeter_segments"] = len(segs)
        diagnostics["n_coincident_tris_deduped"] = getattr(single_owner_edges, "last_n_removed", 0)
        diagnostics["dedup_note"] = ("v4 (audit BEAT #2): coincident-duplicate tris are dropped before "
                                     "the single-owner silhouette so doubled hole-lining tris cannot "
                                     "erase an internal-lake coast (a false PASS). No-op on clean "
                                     "geometry (0 removed on stock/rung_e/rung_d/rung_c).")
        diagnostics["all_coasts_law"] = ("standoff measured to the WHOLE-region land silhouette incl. "
                                         "the desert lobe's own coast (mass-thickness enforcement)")
        measured = dict(
            boundary_cell=_min_seg(boundary_pts, segs),
            straddle_cell=_min_seg(straddle_pts, segs),
            body_tri=_min_seg(body_pts, segs))
        # invalid-convention cross-check, reported LOUDLY (never used to judge): staged sea vertices
        staged_sea = _scan_staged_sea(cand)
        diagnostics["invalid_sea_vertex_convention_body_u"] = (
            round(_min_pts(body_pts, staged_sea), 3) if staged_sea else None)
        diagnostics["invalid_sea_vertex_note"] = (
            "REPORTED NOT JUDGED: staged sea meshes are full-block backing planes -> sea-vertex "
            "collapses to ~0u; the land-perimeter convention is the valid one for a mint.")
        # v2 UNDERLAP DETECTOR: does the ecotone boundary/body sit UNDER a full-block staged sea plane?
        underlap = _staged_sea_underlap(cand, boundary_pts + straddle_pts + body_pts)
        diagnostics["staged_sea_underlap"] = underlap
    else:
        # stock: sea vertices over the core's coastal Moore ring (radius 2, no-closer-vertex-missed).
        coastal = X.list_coastal_donors(disc=1, beach_only=False)
        coastal_set = set(coastal.keys()) if isinstance(coastal, dict) else set(coastal)
        coastal_ring = [b for b in cand["region_blocks"] if b in coastal_set]
        sea = scan_sea_vertices(coastal_ring)
        diagnostics["n_sea_vertices"] = len(sea)
        measured = dict(
            boundary_cell=_min_pts(boundary_pts, sea),
            straddle_cell=_min_pts(straddle_pts, sea),
            body_tri=_min_pts(body_pts, sea))
        # commensurability bridge: coastal-filtered land-perimeter must AGREE with sea-vertex (proves
        # the mint's land-perimeter measurement is comparable to this stock floor).
        segs, by_gid = single_owner_edges(cand["tris"])
        diagnostics["n_coincident_tris_deduped"] = getattr(single_owner_edges, "last_n_removed", 0)
        coastal_segs = _coastal_filter(cand["tris"], segs, sea, thresh=5.0)
        diagnostics["commensurability_bridge_coastal_filtered_boundary_u"] = (
            round(_min_seg(boundary_pts, coastal_segs), 3) if coastal_segs and boundary_pts else None)
        diagnostics["n_coastal_filtered_segments"] = len(coastal_segs)
        diagnostics["n_raw_land_perimeter_segments"] = len(segs)

    checks = {}
    for k in ("boundary_cell", "straddle_cell", "body_tri"):
        mv = measured[k]
        checks[k] = dict(measured_u=round(mv, 3) if mv is not None else None,
                         floor_u=floors[k],
                         passes=(mv is not None and mv >= floors[k] - tol))
    standoff_pass = all(c["passes"] for c in checks.values())
    failed = [k for k, c in checks.items() if not c["passes"]]
    # v2: CONVENTION-INVALID rescues a FALSE PASS only -- the land-perimeter says the standoff clears
    # the floor, but the ecotone underlaps a full-block staged sea plane, so the true waterline is
    # close and the measurement is not trustworthy. If the standoff already FAILS, it stays a plain
    # standoff FAIL (the underlap is merely reported) -- so Rung E fails on standoff, not convention.
    underlap_invalid = (cand["is_staged"] and standoff_pass
                        and diagnostics.get("staged_sea_underlap", {}).get("convention_invalid"))
    if underlap_invalid:
        verdict = "CONVENTION-INVALID"
        convention_invalid = True
    else:
        verdict = "PASS" if standoff_pass else "FAIL"
    return dict(
        gate="R1", title="realized-boundary standoff", mode=mode, verdict=verdict,
        enforce=(mode == "enforce"), convention=convention, convention_invalid=convention_invalid,
        standoff_pass=standoff_pass,
        n_boundary_cells=len(cand["boundary_cells"]), n_straddle_cells=len(cand["straddle_cells"]),
        n_body_tris=len(body_pts), floors=floors, checks=checks, failed_measures=failed,
        diagnostics=diagnostics,
        provenance={k: GATE_CEILINGS[k][1] for k in
                    ("R1.boundary_cell_to_coast_floor_u", "R1.straddle_cell_to_coast_floor_u",
                     "R1.body_tri_to_coast_floor_u")})


def _first_or_none(pts):
    return pts[0] if pts else (0, 0)


def _min_pts(objs, pts):
    if not objs or not pts:
        return None
    best = None
    for (px, pz) in objs:
        d = min_dist_to_points(px, pz, pts)
        if d is not None and (best is None or d < best):
            best = d
    return best


def _min_seg(objs, segs):
    if not objs or not segs:
        return None
    best = None
    for (px, pz) in objs:
        d = min_dist_to_segs(px, pz, segs)
        if d is not None and (best is None or d < best):
            best = d
    return best


def _scan_staged_sea(cand):
    if not cand["is_staged"]:
        return []
    pts = []
    for (bx, by) in [tuple(b) for b in cand["core_blocks"]]:
        ox, oz = X.block_world_origin(bx, by)
        for cap in SEA_PARTS_CAP:
            rel = M.override_relpath(1, bx, by, part=cap)
            p = Path(cand["mod_dir"]) / rel
            if p.exists():
                sbm = M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part=cap.lower())
                for v in sbm.verts:
                    pts.append((v[0] + ox, v[2] + oz))
    return pts


def _staged_sea_underlap(cand, measured_pts, block_cover=56.0, margin=1.0):
    """v2 audit hole #4. Detect whether the measured ecotone (boundary/straddle/body points) lies
    UNDER a staged FULL-BLOCK sea plane -- the pathology that inflates the land-perimeter standoff
    (the visible waterline is close but the terrain silhouette extends under the sea). Scans staged
    Sea* meshes over the region blocks; a mesh is a full-block plane if its XZ bbox spans >=
    `block_cover`u in BOTH axes (a ~64u block) and is near-planar in Y. `convention_invalid` is True
    iff ANY measured point falls inside such a plane's XZ footprint (sea directly over the terrain).
    Report-only fields are always returned; the FAIL decision is gated in gate_r1 on a false-PASS."""
    if not cand["is_staged"]:
        return dict(applicable=False, convention_invalid=False, n_full_block_planes=0,
                    n_points_under_full_block_sea=0)
    planes = []
    for (bx, by) in cand["region_blocks"]:
        ox, oz = X.block_world_origin(bx, by)
        for cap in SEA_PARTS_CAP:
            rel = M.override_relpath(1, bx, by, part=cap)
            p = Path(cand["mod_dir"]) / rel
            if not p.exists():
                continue
            try:
                sbm = M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part=cap.lower())
            except Exception:
                continue
            xs = [v[0] + ox for v in sbm.verts]
            zs = [v[2] + oz for v in sbm.verts]
            ys = [v[1] for v in sbm.verts]
            if not xs:
                continue
            wx, wz = (max(xs) - min(xs)), (max(zs) - min(zs))
            planar = (max(ys) - min(ys)) < 2.0
            if wx >= block_cover and wz >= block_cover and planar:
                planes.append((min(xs), min(zs), max(xs), max(zs), f"{bx},{by}:{cap}"))
    n_under = 0
    for (px, pz) in measured_pts:
        for (x0, z0, x1, z1, _n) in planes:
            if x0 - margin <= px <= x1 + margin and z0 - margin <= pz <= z1 + margin:
                n_under += 1
                break
    return dict(
        applicable=True, n_full_block_planes=len(planes),
        full_block_plane_names=[pl[4] for pl in planes[:12]],
        n_measured_points=len(measured_pts), n_points_under_full_block_sea=n_under,
        convention_invalid=(n_under > 0),
        note="convention_invalid means the ecotone sits under a full-block staged sea plane -> the "
             "land-perimeter standoff is untrustworthy; gate_r1 FAILS such a build as CONVENTION-"
             "INVALID only when it would otherwise be a FALSE PASS (else it is a plain standoff FAIL).")


def _coastal_filter(tris, segs, sea_pts, thresh=5.0):
    """Keep only single-owner edges whose midpoint sits within `thresh` of a real sea/beach vertex --
    the ONLY trustworthy mesh-edge convention on stock (removes internal-seam contamination, falsifier
    A confirmed 6.69u raw is spurious)."""
    out = []
    for seg in segs:
        (x1, z1), (x2, z2) = seg
        mx, mz = (x1 + x2) / 2.0, (z1 + z2) / 2.0
        if min_dist_to_points(mx, mz, sea_pts) is not None and min_dist_to_points(mx, mz, sea_pts) < thresh:
            out.append(seg)
    return out


# ====================================================================================================
# GATE R2 -- SATURATION + ROW-SHAPE (spine report-only)
# ====================================================================================================
def _classify_body(cand):
    """v2 LABEL-BLIND body classification over the core (fam==desert + UV, not topo==16). Returns
    (tally, total, xcheck) where xcheck is the topo cross-check (topo!=16 disagreement count)."""
    body, xcheck = label_blind_desert_body(cand["core_tris"])
    tally = Counter()
    for (_t, cls, _d) in body:
        tally[cls] += 1
    return tally, len(body), xcheck


def _arrangement_report(cand):
    """v3 ARRANGEMENT (audit hole #1 + round-2 BEAT #2). THREE convention-free, stock-measured
    statistics that a mechanical / penetrating comb cannot pass at stock's aggregate saturation:
      FRINGE CONCENTRATION -- fraction of the label-blind dressed body tris sitting at BFS band-0
        (cells touching the grass|desert boundary). Stock 0.8022 (a decaying fringe); a depth-uniform
        picket comb spreads dressing across bands and reads low. BFS depth is convention-free (NOT
        the demoted spine, which needed an unstable 'directly behind' direction convention).
      PENETRATION FRACTION (band>=2) -- fraction of dressed body tris sitting at BFS band-2-OR-DEEPER
        (or unreachable). Stock 0.1231 (the fringe decays out by band-1); the audit's DEEP_TEETH comb
        (deep interdigitated grass teeth that inflate band-0, then a checkerboard of dressing that
        genuinely penetrates band-2..4) reads ~0.33. FRINGE alone is aggregate-blind to a BIMODAL
        distribution (a big boundary fringe carries a detached deep comb: DEEP_TEETH fringe 0.667 >=
        0.60 yet 33% of the dressing is >=2 cells inland) -- this per-band penetration test sees it.
      FLOATING COMPONENTS -- dressed-cell 8-conn components touching no boundary cell (cheby<=1).
        Stock 0 over 9 components / 158 gd-decal cells; a checkerboard comb strands inland patches.
    ALL THREE use the SAME UV-driven label-blind body (label_blind_desert_body) as the saturation
    ceiling -- so a cross-family UV-dressed comb (BEAT #3) cannot hide from the arrangement graph either."""
    core = cand["core_tris"]
    boundary_cells = cand["boundary_cells"]
    # v3: the BFS desert graph + dressed set are the UV-DRIVEN label-blind body (family-blind), so the
    # arrangement is measured on exactly the tris the saturation ceiling scores (BEAT #3 consistency).
    lb_body, _lbx = label_blind_desert_body(core)
    desert_cells = {t["cell"] for (t, _c, _d) in lb_body}
    dist = SNR.cell_distance_bfs(desert_cells, boundary_cells)
    dressed = []
    gd_decal_cells = set()
    for (t, cls, _d) in lb_body:
        if cls in ("strip_grass_desert", "strip_desert_dunes"):
            dressed.append(t)
            if cls == "strip_grass_desert":
                gd_decal_cells.add(t["cell"])
    n_dressed = len(dressed)
    band0 = sum(1 for t in dressed if dist.get(t["cell"]) == 0)
    band_ge2 = sum(1 for t in dressed if (dist.get(t["cell"]) is None or dist.get(t["cell"]) >= 2))
    fringe = (band0 / n_dressed) if n_dressed else None
    penetration_ge2 = (band_ge2 / n_dressed) if n_dressed else None
    band_hist = Counter(("unreached" if dist.get(t["cell"]) is None else dist.get(t["cell"]))
                        for t in dressed)
    # 8-conn components of gd-decal cells + floating count (matches lane B's dressing_components)
    seen = set()
    comps = []
    for s in sorted(gd_decal_cells):
        if s in seen:
            continue
        comp = [s]
        seen.add(s)
        q = deque([s])
        while q:
            u = q.popleft()
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    n = (u[0] + dx, u[1] + dy)
                    if n in gd_decal_cells and n not in seen:
                        seen.add(n)
                        comp.append(n)
                        q.append(n)
        comps.append(comp)

    def cheby(a, b):
        return max(abs(a[0] - b[0]), abs(a[1] - b[1]))

    n_floating = sum(1 for c in comps
                     if not any(cheby(x, b) <= 1 for x in c for b in boundary_cells))
    # dressed-run-length ALONG the boundary -- REPORTED not gated (per the round: a depth-penetrating
    # comb's boundary row is a single clean run, so run-length does not discriminate it; the
    # discriminating statistic is the depth distribution = fringe concentration).
    dressed_band0_cells = {t["cell"] for t in dressed if dist.get(t["cell"]) == 0}
    band0_cells = {c for c in desert_cells if dist.get(c) == 0}
    run_lengths = _boundary_run_lengths(band0_cells, dressed_band0_cells)
    return dict(
        n_dressed_body_tris=n_dressed, band0_dressed_tris=band0, band_ge2_dressed_tris=band_ge2,
        fringe_concentration=round(fringe, 4) if fringe is not None else None,
        penetration_ge2_fraction=round(penetration_ge2, 4) if penetration_ge2 is not None else None,
        dressed_band_hist={str(k): v for k, v in sorted(band_hist.items(), key=lambda kv: str(kv[0]))},
        n_gd_decal_cells=len(gd_decal_cells), n_components=len(comps),
        n_floating_components=n_floating,
        mean_component_cells=round(len(gd_decal_cells) / len(comps), 2) if comps else None,
        dressed_run_lengths_along_boundary_reported=run_lengths,
        note="fringe_concentration + penetration_ge2_fraction + n_floating_components are GATED; "
             "run-lengths are REPORT-ONLY. fringe catches a depth-uniform comb (low band-0); "
             "penetration catches a BIMODAL comb (big fringe + detached deep teeth, which fringe alone "
             "misses); floating catches a stranded checkerboard.")


def _boundary_run_lengths(band0_cells, dressed_band0_cells):
    """Report-only. Order the boundary (BFS band-0) cells into 8-conn chains and return the dressed
    run-length histogram along them (stock organic = a few long runs; a checkerboard = many len-1)."""
    def cheby(a, b):
        return max(abs(a[0] - b[0]), abs(a[1] - b[1]))
    remaining = set(band0_cells)
    runs = Counter()
    max_run = 0
    while remaining:
        start = min(remaining)
        chain = [start]
        remaining.discard(start)
        # greedy walk both directions along 8-conn neighbours
        changed = True
        while changed:
            changed = False
            for end in (chain[0], chain[-1]):
                for nb in sorted(remaining):
                    if cheby(end, nb) == 1:
                        if end == chain[0]:
                            chain.insert(0, nb)
                        else:
                            chain.append(nb)
                        remaining.discard(nb)
                        changed = True
                        break
                if changed:
                    break
        cur = 0
        for c in chain:
            if c in dressed_band0_cells:
                cur += 1
                max_run = max(max_run, cur)
            else:
                if cur:
                    runs[cur] += 1
                cur = 0
        if cur:
            runs[cur] += 1
    return dict(run_length_hist={str(k): v for k, v in sorted(runs.items())}, max_dressed_run=max_run)


def _pooled_row_distribution(cand):
    """The BOTH-family-sides pooled STRIPS(grass,desert) row distribution over core grass+desert tris
    (falsifier B: the gate population -- the row0-spike lives on the grass side; pooled is the signal)."""
    rows = Counter()
    for t in cand["core_tris"]:
        if t["fam"] not in ("grass", "desert"):
            continue
        cls, detail = SNR.classify_tri(t["fam"], t["uv"])
        if cls == "strip_grass_desert":
            rows[detail] += 1
    total = sum(rows.values())
    frac = {k: (rows.get(k, 0) / total if total else 0.0) for k in range(4)}
    return rows, total, frac


def _spine_report(cand):
    """REPORT-ONLY (NOT gated). A robust graph proxy: desert cells, plain-desert cells (desert-family,
    no strip decal), boundary desert cells = depth 0; band1_plain_rate + zero-spine fraction. Two
    falsifier-confirmed conventions agree spine does NOT separate stock (~51%) from Rung E (~53%)."""
    cell_tris = defaultdict(list)
    for t in cand["core_tris"]:
        cell_tris[t["cell"]].append(t)
    desert_cells = set()
    plain_cells = set()
    for c, ts in cell_tris.items():
        has_desert = any(t["fam"] == "desert" for t in ts)
        if not has_desert:
            continue
        desert_cells.add(c)
        dressed = False
        for t in ts:
            if t["fam"] == "desert":
                cls, _d = SNR.classify_tri(t["fam"], t["uv"])
                if cls in ("strip_grass_desert", "strip_desert_dunes"):
                    dressed = True
                    break
        if not dressed:
            plain_cells.add(c)
    dist = SNR.cell_distance_bfs(desert_cells, cand["boundary_cells"])
    band1 = [c for c, d in dist.items() if d == 1]
    band1_plain = sum(1 for c in band1 if c in plain_cells)
    # zero-spine proxy: boundary cells whose immediate inland desert neighbour (band1) is dressed (no
    # plain spine directly behind) -- fraction of measurable boundary cells with zero plain band1 nbr
    n_meas = 0
    n_zero = 0
    for b in cand["boundary_cells"]:
        nbrs = [(b[0] + dx, b[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                if (dx or dy) and dist.get((b[0] + dx, b[1] + dy)) == 1]
        if not nbrs:
            continue
        n_meas += 1
        if not any(n in plain_cells for n in nbrs):
            n_zero += 1
    return dict(
        report_only=True, gated=False,
        n_desert_cells=len(desert_cells), n_plain_desert_cells=len(plain_cells),
        band1_cells=len(band1), band1_plain_rate=round(band1_plain / len(band1), 4) if band1 else None,
        zero_spine_fraction_proxy=round(n_zero / n_meas, 4) if n_meas else None,
        note="NOT gated -- falsifier B: two conventions agree spine does not separate stock from "
             "Rung E (zero-spine ~51% vs ~53%); the robust proxy even reverses direction.")


def gate_r2(cand, *, mode="enforce", tol=1e-3):
    """v2 PRIMARY (both must pass): SATURATION on the label-blind desert body (grass-decal <= 0.5024,
    any-decal <= 0.6351) AND ARRANGEMENT (fringe concentration >= 0.60, floating components <= 0).
    ADVISORY (n=1): pooled both-sides row0 shape (ratio vs 0.199 <= 1.80 AND abs <= 0.35). Spine
    COMPUTED + REPORTED but NOT gated. topo id is a CROSS-CHECK column, disagreements reported."""
    tally, total, xcheck = _classify_body(cand)
    n_gd = tally.get("strip_grass_desert", 0)
    n_dd = tally.get("strip_desert_dunes", 0)
    n_plain = tally.get("mains_own", 0)
    sat_grass = (n_gd / total) if total else None
    sat_any = ((n_gd + n_dd) / total) if total else None
    c_grass = ceil("R2.saturation_grass_decal_ceiling")
    c_any = ceil("R2.saturation_any_decal_ceiling")
    pass_grass = (sat_grass is not None and sat_grass <= c_grass + tol)
    pass_any = (sat_any is not None and sat_any <= c_any + tol)

    # ---- ARRANGEMENT (v2 audit hole #1 + v3 round-2 BEAT #2 penetration) --------------------------
    arr = _arrangement_report(cand)
    c_fringe = ceil("R2.fringe_concentration_floor")
    c_pen = ceil("R2.penetration_ge2_fraction_ceiling")
    c_float = ceil("R2.floating_components_max")
    fringe = arr["fringe_concentration"]
    penetration = arr["penetration_ge2_fraction"]
    n_float = arr["n_floating_components"]
    pass_fringe = (fringe is not None and fringe >= c_fringe - tol)
    pass_penetration = (penetration is not None and penetration <= c_pen + tol)
    pass_float = (n_float <= c_float)
    arrangement_pass = pass_fringe and pass_penetration and pass_float
    arr.update(fringe_concentration_floor=c_fringe, fringe_passes=pass_fringe,
               penetration_ge2_ceiling=c_pen, penetration_passes=pass_penetration,
               floating_components_max=c_float, floating_passes=pass_float,
               arrangement_pass=arrangement_pass)

    rows, row_total, frac = _pooled_row_distribution(cand)
    stock_row0 = ceil("R2.row0_fraction_stock_pooled")
    row0 = frac[0]
    row0_ratio = (row0 / stock_row0) if stock_row0 else None
    c_ratio = ceil("R2.row0_ratio_ceiling")
    c_abs = ceil("R2.row0_fraction_ceiling_abs")
    # advisory pass: fails only if BOTH the ratio AND the absolute ceiling are exceeded (a decisive
    # row0 spike like Rung E's), so a small-n wobble near stock does not trip it.
    row_spike = (row0_ratio is not None and row0_ratio > c_ratio) and (row0 > c_abs)
    pass_row = not row_spike

    spine = _spine_report(cand)

    primary_pass = pass_grass and pass_any and arrangement_pass
    verdict = "PASS" if (primary_pass and pass_row) else "FAIL"
    return dict(
        gate="R2", title="saturation + arrangement (row advisory, spine report-only)", mode=mode,
        verdict=verdict, enforce=(mode == "enforce"),
        body=dict(label_blind_total=total, n_dressed_grass=n_gd, n_dressed_dunes=n_dd,
                  n_plain_mains=n_plain, tally=dict(tally), topo_crosscheck=xcheck),
        saturation=dict(
            grass_decal=round(sat_grass, 4) if sat_grass is not None else None,
            grass_decal_ceiling=c_grass, grass_decal_passes=pass_grass,
            any_decal=round(sat_any, 4) if sat_any is not None else None,
            any_decal_ceiling=c_any, any_decal_passes=pass_any),
        arrangement=arr,
        row_shape=dict(
            population="pooled_both_family_sides_strip_grass_desert", n_pooled_tris=row_total,
            row_fractions={str(k): round(v, 4) for k, v in frac.items()},
            row_counts={str(k): rows.get(k, 0) for k in range(4)},
            stock_row0_fraction=stock_row0, candidate_row0_fraction=round(row0, 4),
            row0_ratio=round(row0_ratio, 4) if row0_ratio is not None else None,
            row0_ratio_ceiling=c_ratio, row0_abs_ceiling=c_abs,
            row0_spike_detected=row_spike, passes=pass_row, advisory=True),
        spine=spine,
        primary_saturation_pass=(pass_grass and pass_any),
        primary_arrangement_pass=arrangement_pass,
        primary_pass=primary_pass, secondary_row_pass=pass_row,
        provenance={k: GATE_CEILINGS[k][1] for k in
                    ("R2.saturation_grass_decal_ceiling", "R2.saturation_any_decal_ceiling",
                     "R2.fringe_concentration_floor", "R2.penetration_ge2_fraction_ceiling",
                     "R2.floating_components_max", "R2.row0_fraction_stock_pooled")})


# ====================================================================================================
# GATE R3 -- THE INLAND-BACKING DISCRIMINATOR (topological)
#
# n=1 PROVENANCE (LOUD): the whole 24x20 overworld grid has exactly ONE grass|desert junction (the
# scout's map-wide census, n_components=1). This gate's law -- "the topo-16 band backs onto a
# desert-family (dunes-or-plain-desert) interior before it peters out" -- is therefore a CENSUS OF THE
# ONLY INSTANCE, not a train/test-validated law; no leave-one-SITE-out is possible. It is nonetheless
# the definition of lawful, because that one instance is the only stock example a Rung-F build must
# match. Lane C + falsifier C CONFIRMED: stock dunes-backing at inland depth 1 (151 dunes-neighbour
# tris); topo-17 plain desert NEVER appears adjacent to grass anywhere (first_depth_with_topo17=None);
# Rung E's band returns to grass on all sides (first_depth_with_dunes=None). Cell-SHAPE metrics
# (area/interior-fraction/inscribed-radius/grass-ecotone-fraction) do NOT separate (any_metric_
# separates=False; stock itself spans interior-fraction 0.0-0.647) -- they are REPORTED, never gated.
# ====================================================================================================
def _cell_block(c):
    wx, wz = cell_center(c)
    return (math.floor(wx / BLOCK), math.floor(-wz / BLOCK))


def gate_r3(cand, *, mode="enforce"):
    """v3 INLAND-BACKING EXTENT (audit hole #3 + round-2 BEAT #1 ADJACENCY). The topo-16 ecotone skin
    must BACK ONTO -- i.e. be 8-conn CONNECTED (through the desert-family mass) to -- a desert-family
    interior MASS whose largest 8-conn component >= FLOOR cells. v1 fired on n>=1 (one token cell); v2
    required a real >=130 mass but counted ANY backing cell over the whole region regardless of whether
    the ecotone actually reaches it -- so a DISJOINT 130-cell dune blob dropped elsewhere satisfied it
    while the ecotone returned to grass on its own far side (BEAT #1 P2_SUITE_FAKE_BACKING passed all
    three gates). v3 closes it: flood 8-conn from the BOUNDARY-DESERT skin cells THROUGH the mass cells
    (topo {16,17,19,20,41} = skin + backing), and gate on the largest 8-conn component of the
    ecotone-REACHABLE backing cells (topo {17,19,20,41}). A backing mass the skin does not reach no
    longer counts. FLOOR=130 (stock realized dunes lobe 143 -- and it IS reachable: the whole stock
    desert mass is one component, reachable-backing==143 == whole-region-backing; measure_v2.json --
    + the dunes size-class law ~130). The whole-region backing is still REPORTED (for continuity) but
    the VERDICT keys on the reachable mass. Cell-SHAPE metrics do NOT separate (Lane C) -> reported
    only. n=1: the map has ONE grass|desert junction, a census; the floor leans on the wide margin.

    v4 (round-2 audit BEAT #1, P3_R3_TENDRIL_BACKING) closes the THREAD hole in v3's mere-reachability:
    a 1-cell-wide topo-17 tendril bridging a grass-wrapped skin to a remote >=130 dune blob satisfied
    8-conn reachability (reachable 131) though the skin never BACKS ONTO a mass. The v4 VERDICT is
    has_extent AND has_broad_interface AND erosion_survives:
      has_extent          -- reachable-backing largest 8-conn component >= 130 (as v3).
      has_broad_interface -- the 4-conn cell-adjacency count between the reachable topo-16 skin and the
                             reachable backing >= 20 (stock 125; a thread 1). The anti-thread waist gate.
      erosion_survives    -- after 1-cell morphological erosion of the mass the skin still reaches some
                             backing (stock 129; a thread 0). A scale-free corroborator; a thread dies.
    The three agree on stock (extent 143 / interface 125 / erosion 129) and on the beat (extent 131 but
    interface 1 + erosion 0 -> FAIL). n=1 -> the interface floor leans on the WIDE gap, never a knife-edge."""
    floor = ceil("R3.backing_mass_floor_cells")
    # boundary desert cells (desert side of a grass|desert edge) -- the skin, and the flood SEED
    eo = SNR.edge_index(cand["tris"])
    by_gid = cand["by_gid"]
    boundary_desert = set()
    for e, owners in eo.items():
        fams = {by_gid[g]["fam"] for g in owners}
        if "grass" in fams and "desert" in fams:
            for g in owners:
                t = by_gid[g]
                if t["fam"] == "desert" and t["block"] in cand["core_set"]:
                    boundary_desert.add(t["cell"])

    # backing grounds cells + mass cells (skin+backing) + skin cells over the WHOLE loaded region.
    backing_cells = set()
    backing_topo = Counter()
    mass_cells = set()
    skin_cells = set()                    # v4: topo-16 ecotone skin cells (for the interface measure)
    cell_fams = defaultdict(Counter)
    for t in cand["tris"]:
        if t["fam"]:
            cell_fams[t["cell"]][t["fam"]] += 1
        if t["topo"] in MASS_TOPOS:
            mass_cells.add(t["cell"])
        if t["topo"] == 16:
            skin_cells.add(t["cell"])
        if t["topo"] in BACKING_TOPOS:
            backing_cells.add(t["cell"])
            backing_topo[t["topo"]] += 1

    def largest_8conn(cellset):
        seen = set()
        best = 0
        sizes = []
        for s in cellset:
            if s in seen:
                continue
            comp = [s]
            seen.add(s)
            q = deque([s])
            while q:
                u = q.popleft()
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        n = (u[0] + dx, u[1] + dy)
                        if n in cellset and n not in seen:
                            seen.add(n)
                            comp.append(n)
                            q.append(n)
            sizes.append(len(comp))
        sizes.sort(reverse=True)
        return (sizes[0] if sizes else 0), sizes

    # v3 ADJACENCY: flood 8-conn from the skin (boundary_desert) through the mass cells; the backing
    # that the ecotone actually REACHES is reachable_mass INTERSECT backing_cells.
    seed = boundary_desert & mass_cells
    reachable_mass = set(seed)
    q = deque(seed)
    while q:
        u = q.popleft()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nb = (u[0] + dx, u[1] + dy)
                if nb in mass_cells and nb not in reachable_mass:
                    reachable_mass.add(nb)
                    q.append(nb)
    backing_reachable = reachable_mass & backing_cells
    skin_reachable = reachable_mass & skin_cells
    reachable_largest, reachable_sizes = largest_8conn(backing_reachable)
    whole_largest, whole_sizes = largest_8conn(backing_cells)
    has_extent = reachable_largest >= floor

    # v4 (round-2 audit BEAT #1, P3_R3_TENDRIL_BACKING) -- THE SKIN<->BACKING INTERFACE. v3 gated only
    # 8-conn REACHABILITY, which a 1-cell-wide thread satisfies: a grass-wrapped skin bridged to a
    # remote >=130 dune blob by ONE topo-17 tendril passed (reachable 131). The letter "8-conn connected
    # to a >=130 mass" was met, the INTENT "the skin BACKS ONTO a mass across a broad interior waist"
    # violated. v4 measures the realized INTERFACE = the count of 4-conn cell-adjacency pairs between the
    # ecotone-reachable topo-16 skin and the ecotone-reachable desert-family backing, and floors it. A
    # thread has interface ~1-2 (stock 125); the intent-satisfying broad-front waist has many.
    interface_pairs, iface_skin_cells, iface_backing_cells = _skin_backing_interface(
        skin_reachable, backing_reachable)
    iface_floor = ceil("R3.skin_backing_interface_floor_pairs")
    has_interface = interface_pairs >= iface_floor

    # v4 EROSION-ROBUSTNESS corroborator (scale-free): after 1-cell morphological erosion of the mass,
    # the skin must STILL reach some backing. A thread (waist <=2 cells) is fully eroded -> the skin is
    # severed from its remote blob -> 0 reachable; a broad-front waist survives (stock 129). Gated as a
    # companion so the two agree; both catch the thread, neither can be gamed without a genuine broad
    # waist (= the intent). REPORTED with the survivor count.
    erosion_survive_backing = _erosion_survives(mass_cells, backing_cells, boundary_desert)
    erosion_survives = erosion_survive_backing > 0

    has_backing = has_extent and has_interface and erosion_survives

    # REPORTED-NOT-GATED cell-shape metrics (Lane C: none separate; stock spans interior-fraction
    # 0.0-0.647).
    shape = _desert_shape_report(cell_fams)

    verdict = "PASS" if has_backing else "FAIL"
    return dict(
        gate="R3", title="inland-backing extent (ecotone-reachable topological mass)", mode=mode,
        verdict=verdict, enforce=(mode == "enforce"),
        n_boundary_desert_cells=len(boundary_desert),
        backing_mass_floor_cells=floor,
        # v3 GATED value = the ecotone-reachable backing largest component
        largest_backing_component_cells=reachable_largest,
        largest_reachable_backing_cells=reachable_largest,
        reachable_backing_component_sizes=reachable_sizes[:8],
        n_backing_reachable_cells=len(backing_reachable),
        n_reachable_mass_cells=len(reachable_mass),
        # v4 GATED: the skin<->backing INTERFACE (broad-front waist, anti-thread) + erosion survival
        has_extent=has_extent,
        skin_backing_interface_pairs=interface_pairs,
        skin_backing_interface_floor_pairs=iface_floor,
        has_broad_interface=has_interface,
        interface_skin_cells_touching_backing=iface_skin_cells,
        interface_backing_cells_touching_skin=iface_backing_cells,
        n_skin_reachable_cells=len(skin_reachable),
        erosion_survive_backing_cells=erosion_survive_backing,
        erosion_survives=erosion_survives,
        interface_note=("v4 (audit BEAT #1): a thread satisfies 8-conn reachability but has interface "
                        "~1-2; the VERDICT now requires the skin to meet the backing across a broad "
                        f"4-conn interface (>= {iface_floor} pairs; stock 125) AND the connection to "
                        "survive 1-cell erosion (a thread dies, stock survives with 129 backing cells)."),
        # whole-region backing (v2 behaviour) is REPORTED, no longer the verdict
        whole_region_largest_backing_cells=whole_largest,
        whole_region_backing_component_sizes=whole_sizes[:8],
        n_backing_ground_cells=len(backing_cells),
        n_backing_components=len(whole_sizes),
        backing_component_sizes=reachable_sizes[:8],
        backing_topo_tally=dict(backing_topo),
        has_desert_family_backing_mass=has_backing,
        adjacency_note=("v3: the VERDICT keys on the ecotone-REACHABLE backing (flood 8-conn from the "
                        "boundary-desert skin through mass cells {16,17,19,20,41}), NOT mere presence "
                        "in the region -- a disjoint backing mass the skin does not reach no longer "
                        "counts (audit BEAT #1)."),
        stock_realized_backing_cells=ceil("R3.stock_realized_backing_cells"),
        cell_shape_reported_not_gated=shape,
        n1_provenance=("CENSUS of the map's ONLY grass|desert junction (n_components=1 map-wide) -- "
                       "not train/test-validated; floor 130 leans on the WIDE margin (stock reachable "
                       "143 vs a token/disjoint mass) + the independent dunes size-class prior (~130)."),
        provenance={k: GATE_CEILINGS[k][1] for k in
                    ("R3.backing_mass_floor_cells", "R3.stock_realized_backing_cells")})


def _skin_backing_interface(skin_cells, backing_cells):
    """v4 (audit BEAT #1). The realized skin<->backing INTERFACE = the count of 4-conn cell-adjacency
    pairs between the ecotone-reachable topo-16 skin and the ecotone-reachable desert-family backing.
    Returns (n_pairs, n_distinct_skin_cells_touching_backing, n_distinct_backing_cells_touching_skin).
    Stock: 125 pairs / 73 skin cells / 68 backing cells (a broad front). A 1-cell tendril: 1 pair. This
    is the anti-thread discriminator that mere 8-conn reachability (v3) could not see."""
    pairs = 0
    skin_touch = set()
    backing_touch = set()
    for a in skin_cells:
        for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            b = (a[0] + dx, a[1] + dy)
            if b in backing_cells:
                pairs += 1
                skin_touch.add(a)
                backing_touch.add(b)
    return pairs, len(skin_touch), len(backing_touch)


def _erosion_survives(mass_cells, backing_cells, boundary_desert):
    """v4 (audit BEAT #1) erosion-robustness corroborator, scale-free. Erode the mass by removing every
    cell with any non-mass 4-conn neighbour (strict 1-cell morphological erosion), then re-flood 8-conn
    from the surviving boundary-desert skin seed and count the backing cells still reached. A thread
    (waist <=2 cells) erodes away completely -> the skin is severed from a remote blob -> 0; a broad-front
    waist survives (stock 129). Returns the count of ecotone-reachable backing cells AFTER erosion."""
    def eroded(cells):
        keep = set()
        for c in cells:
            if all((c[0] + dx, c[1] + dy) in cells for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                keep.add(c)
        return keep
    mass_e = eroded(mass_cells)
    seed = (boundary_desert & mass_e)
    if not seed:                          # the skin's own boundary cells eroded too -> seed on any
        seed = mass_e & boundary_desert   # remaining mass cell 8-conn-adjacent to a boundary-desert cell
        if not seed:
            near = set()
            for c in mass_e:
                if any((c[0] + dx, c[1] + dy) in boundary_desert
                       for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx or dy)):
                    near.add(c)
            seed = near
    reach = set(seed)
    q = deque(seed)
    while q:
        u = q.popleft()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nb = (u[0] + dx, u[1] + dy)
                if nb in mass_e and nb not in reach:
                    reach.add(nb)
                    q.append(nb)
    return len(reach & backing_cells)


def _desert_shape_report(cell_fams):
    desert_cells = {c for c, f in cell_fams.items() if f.get("desert", 0) > 0}
    if not desert_cells:
        return dict(n_desert_cells=0, largest_component_area_cells=0,
                    note="REPORTED NOT GATED (Lane C: no cell-shape metric separates)")
    seen = set()
    comps = []
    for s in desert_cells:
        if s in seen:
            continue
        comp = {s}
        seen.add(s)
        qq = deque([s])
        while qq:
            c = qq.popleft()
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if not (dx or dy):
                        continue
                    n = (c[0] + dx, c[1] + dy)
                    if n in desert_cells and n not in seen:
                        seen.add(n)
                        comp.add(n)
                        qq.append(n)
        comps.append(comp)
    largest = max(comps, key=len)
    return dict(n_desert_cells=len(desert_cells), n_components=len(comps),
                largest_component_area_cells=len(largest),
                note="REPORTED NOT GATED -- Lane C + falsifier C: any_metric_separates=False; stock "
                     "biome masses span interior-fraction 0.0-0.647, so shape cannot fail a candidate.")


# ====================================================================================================
# self-test
# ====================================================================================================
def run_matrix_on(cand, mode="enforce"):
    r1 = gate_r1(cand, mode=mode)
    r2 = gate_r2(cand, mode=mode)
    r3 = gate_r3(cand, mode=mode)
    overall = "PASS" if all(r["verdict"] == "PASS" for r in (r1, r2, r3)) else "FAIL"
    return dict(name=cand["name"], is_staged=cand["is_staged"], core_blocks=cand["core_blocks"],
                overall=overall, R1=r1, R2=r2, R3=r3)


def main():
    t0 = time.time()
    log(f"game root: {SNR.GAME_ROOT}")
    OUT.parent.mkdir(parents=True, exist_ok=True)

    results = []
    calibration = {}
    skipped = []

    # ---- STOCK ecotone site (TRAIN case: must PASS) -----------------------------------------------
    log("=" * 100)
    log("STOCK ecotone site (the definition of lawful -- must PASS all three gates)")
    log("=" * 100)
    stock = load_candidate("stock_ecotone_13-15_11-12", None, core_blocks=ECOTONE_CORE)
    log(f"  boundary_cells={len(stock['boundary_cells'])} straddle_cells={len(stock['straddle_cells'])} "
        f"body_tris={len(stock['body_tris'])} gd_edges={stock['n_gd_edges']}")
    stock_row = run_matrix_on(stock)
    results.append(stock_row)

    # CALIBRATE THE INSTRUMENT: the live stock measurement must match the pinned confirmed constants.
    r1s, r2s, r3s = stock_row["R1"], stock_row["R2"], stock_row["R3"]
    calibration = dict(
        stock_boundary_cell_u=r1s["checks"]["boundary_cell"]["measured_u"],
        stock_straddle_cell_u=r1s["checks"]["straddle_cell"]["measured_u"],
        stock_body_tri_u=r1s["checks"]["body_tri"]["measured_u"],
        stock_sat_grass=r2s["saturation"]["grass_decal"],
        stock_sat_any=r2s["saturation"]["any_decal"],
        stock_row0_pooled=r2s["row_shape"]["candidate_row0_fraction"],
        stock_body_total=r2s["body"]["label_blind_total"],
        stock_body_topo_disagreement=r2s["body"]["topo_crosscheck"]["n_topo_not16"],
        stock_fringe_concentration=r2s["arrangement"]["fringe_concentration"],
        stock_penetration_ge2=r2s["arrangement"]["penetration_ge2_fraction"],
        stock_floating_components=r2s["arrangement"]["n_floating_components"],
        stock_reachable_backing_cells=r3s["largest_reachable_backing_cells"],
        stock_wholeregion_backing_cells=r3s["whole_region_largest_backing_cells"],
        stock_skin_backing_interface_pairs=r3s["skin_backing_interface_pairs"],
        stock_erosion_survive_backing_cells=r3s["erosion_survive_backing_cells"],
        stock_body_fam_disagreement=r2s["body"]["topo_crosscheck"]["n_fam_not_desert"],
        stock_excluded_grass_side_gd=r2s["body"]["topo_crosscheck"]["excluded_grass_side_gd"],
        stock_excluded_dunes_side_dd=r2s["body"]["topo_crosscheck"]["excluded_dunes_side_dd"],
        matches_confirmed=dict(
            boundary_cell=(abs((r1s["checks"]["boundary_cell"]["measured_u"] or 0) - 39.953) < 0.01),
            straddle_cell=(abs((r1s["checks"]["straddle_cell"]["measured_u"] or 0) - 44.635) < 0.01),
            body_tri=(abs((r1s["checks"]["body_tri"]["measured_u"] or 0) - 42.968) < 0.01),
            body_total_422=(r2s["body"]["label_blind_total"] == 422),
            body_topo_disagreement_0=(r2s["body"]["topo_crosscheck"]["n_topo_not16"] == 0),
            body_fam_disagreement_0=(r2s["body"]["topo_crosscheck"]["n_fam_not_desert"] == 0),
            excluded_grass_side_gd_180=(r2s["body"]["topo_crosscheck"]["excluded_grass_side_gd"] == 180),
            excluded_dunes_side_dd_60=(r2s["body"]["topo_crosscheck"]["excluded_dunes_side_dd"] == 60),
            sat_grass=(abs((r2s["saturation"]["grass_decal"] or 0) - 0.5024) < 0.005),
            sat_any=(abs((r2s["saturation"]["any_decal"] or 0) - 0.6351) < 0.005),
            row0=(abs((r2s["row_shape"]["candidate_row0_fraction"] or 0) - 0.199) < 0.01),
            fringe_0p802=(abs((r2s["arrangement"]["fringe_concentration"] or 0) - 0.8022) < 0.01),
            penetration_0p1231=(abs((r2s["arrangement"]["penetration_ge2_fraction"] or 0) - 0.1231) < 0.01),
            floating_0=(r2s["arrangement"]["n_floating_components"] == 0),
            backing_reachable_143=(r3s["largest_reachable_backing_cells"] == 143),
            backing_wholeregion_143=(r3s["whole_region_largest_backing_cells"] == 143),
            skin_backing_interface_125=(r3s["skin_backing_interface_pairs"] == 125),
            erosion_survive_129=(r3s["erosion_survive_backing_cells"] == 129)),
    )
    calib_ok = all(calibration["matches_confirmed"].values())
    calibration["all_match"] = calib_ok
    log(f"  CALIBRATION vs confirmed constants: {calibration['matches_confirmed']} -> "
        f"{'PASS' if calib_ok else '*** MISMATCH -- ceiling may be wrong, reported loudly ***'}")
    log(f"  STOCK overall: {stock_row['overall']} (R1={stock_row['R1']['verdict']} "
        f"R2={stock_row['R2']['verdict']} R3={stock_row['R3']['verdict']})")
    if stock_row["overall"] != "PASS":
        log("  *** STOCK FAILED A GATE -- by the contract this means a CEILING is wrong (fix the "
            "ceiling, never special-case the site). Reported loudly, not hidden. ***")

    # ---- NEGATIVE CONTROLS: staged builds (must be REJECTED) --------------------------------------
    controls = [
        ("rung_e", HERE / "out" / "rung_e" / "FF9CustomMap-world", True),
        ("rung_d", HERE / "out" / "rung_d" / "FF9CustomMap-world", False),
        ("rung_c_foreign_mixed_biome_mint",
         Path(r"C:/gd/Dream-World-IX/.claude/worktrees/overworld-tools-performance-a36df4/"
              r"studies/overworld-topography/out/mixed_biome_mint/FF9CustomMap-world"), False),
    ]
    for name, mod_dir, required in controls:
        log("\n" + "=" * 100)
        log(f"NEGATIVE CONTROL: {name}  ({mod_dir})")
        log("=" * 100)
        if not Path(mod_dir).is_dir():
            msg = f"SKIPPED -- {mod_dir} does not exist (reported, not silently substituted)"
            log(f"  {msg}")
            skipped.append(dict(name=name, reason=msg))
            if required:
                log("  *** required control missing -- this weakens the negative-control coverage ***")
            continue
        fp = detect_footprint(mod_dir)
        if not fp:
            msg = f"SKIPPED -- no Terrain.ff9mesh overrides found under {mod_dir}"
            log(f"  {msg}")
            skipped.append(dict(name=name, reason=msg))
            continue
        cand = load_candidate(name, mod_dir)
        log(f"  footprint={fp}")
        log(f"  boundary_cells={len(cand['boundary_cells'])} straddle_cells={len(cand['straddle_cells'])} "
            f"body_tris={len(cand['body_tris'])} gd_edges={cand['n_gd_edges']}")
        row = run_matrix_on(cand)
        results.append(row)
        log(f"  {name} overall: {row['overall']}  R1={row['R1']['verdict']} R2={row['R2']['verdict']} "
            f"R3={row['R3']['verdict']}")
        if name == "rung_e":
            r1 = row["R1"]; r2 = row["R2"]; r3 = row["R3"]
            log(f"    R1 measured: boundary={r1['checks']['boundary_cell']['measured_u']}u "
                f"straddle={r1['checks']['straddle_cell']['measured_u']}u "
                f"body={r1['checks']['body_tri']['measured_u']}u (floors 39.953/44.635/42.968); "
                f"convention_invalid={r1['convention_invalid']}")
            log(f"    R2 saturation grass={r2['saturation']['grass_decal']} (ceil 0.5024) "
                f"any={r2['saturation']['any_decal']} (ceil 0.6351); "
                f"fringe={r2['arrangement']['fringe_concentration']} (floor 0.60) "
                f"floating={r2['arrangement']['n_floating_components']}; "
                f"row0={r2['row_shape']['candidate_row0_fraction']} spike={r2['row_shape']['row0_spike_detected']}")
            log(f"    R3 backing_component={r3['largest_backing_component_cells']} cells "
                f"(floor 130; stock 143; 0=ribbon returns to grass)")

    # ---- headline / matrix ------------------------------------------------------------------------
    log("\n" + "=" * 100)
    log("PASS/FAIL MATRIX")
    log("=" * 100)
    log(f"  {'candidate':42s} {'R1':>5s} {'R2':>5s} {'R3':>5s}  overall")
    for r in results:
        log(f"  {r['name']:42s} {r['R1']['verdict']:>5s} {r['R2']['verdict']:>5s} "
            f"{r['R3']['verdict']:>5s}  {r['overall']}")

    stock_pass = (stock_row["overall"] == "PASS")
    rung_e_row = next((r for r in results if r["name"] == "rung_e"), None)
    rung_e_reject = False
    rung_e_refutations = {}
    if rung_e_row:
        r1 = rung_e_row["R1"]; r2 = rung_e_row["R2"]; r3 = rung_e_row["R3"]
        r1_fail = (r1["verdict"] in ("FAIL", "CONVENTION-INVALID"))
        r2_sat_fail = not r2["primary_saturation_pass"]
        r2_arr_fail = not r2["primary_arrangement_pass"]
        r2_row_spike = r2["row_shape"]["row0_spike_detected"]
        r3_fail = (r3["verdict"] == "FAIL")
        rung_e_reject = (rung_e_row["overall"] == "FAIL")
        rung_e_refutations = dict(
            R1_standoff_below_floor=(r1["verdict"] == "FAIL"),
            R1_convention_invalid=bool(r1["convention_invalid"]),
            R2_saturation_above_ceiling=r2_sat_fail,
            R2_arrangement_below_floor=r2_arr_fail,
            R2_row0_spike_out_of_shape=bool(r2_row_spike),
            R3_no_desert_family_backing_mass=r3_fail,
            both_refutations_reproduced=(r1_fail and r2_sat_fail))

    # controls_reject: rung_c + rung_d + rung_e all FAIL overall (skips reported, not counted as pass)
    control_names = ("rung_e", "rung_d", "rung_c_foreign_mixed_biome_mint")
    control_rows = {r["name"]: r for r in results if r["name"] in control_names}
    controls_present = {n: (n in control_rows) for n in control_names}
    controls_reject = (all(control_rows.get(n, {}).get("overall") == "FAIL" for n in control_names)
                       and all(controls_present.values()))

    ceilings_out = {k: dict(value=v[0], provenance=v[1]) for k, v in GATE_CEILINGS.items()}
    annotations = write_annotations(calibration)
    summary = (
        f"Stock ecotone {'PASSES' if stock_pass else 'FAILS'} all three gates; "
        f"controls_reject={controls_reject} (rung_c/d/e all FAIL); "
        f"Rung E {'REJECTED' if rung_e_reject else 'NOT rejected'} "
        f"(R1 standoff-below-floor={rung_e_refutations.get('R1_standoff_below_floor')}, "
        f"R2 saturation={rung_e_refutations.get('R2_saturation_above_ceiling')} + "
        f"arrangement={rung_e_refutations.get('R2_arrangement_below_floor')}, "
        f"R3 no-backing-mass={rung_e_refutations.get('R3_no_desert_family_backing_mass')}); "
        f"skipped: {[s['name'] for s in skipped]}.")

    out = dict(
        meta=dict(script="contract_mass_gates.py", version="v4", generated=time.strftime("%Y-%m-%d %H:%M:%S"),
                  elapsed_s=round(time.time() - t0, 1), read_only=True, zero_game_writes=True,
                  zero_deploys=True,
                  note="Gates v4 for the Rung-F build (post-RE-audit round 3). Ceilings are stock-measured + "
                       "falsifier-CONFIRMED. n=1 stock ecotone map-wide -> the gates are a census of "
                       "the only lawful instance. See annotations.json for the four critic gaps."),
        gate_ceilings=ceilings_out,
        calibration=calibration,
        controls_present=controls_present,
        controls_reject=controls_reject,
        matrix=[dict(name=r["name"], R1=r["R1"]["verdict"], R2=r["R2"]["verdict"],
                     R3=r["R3"]["verdict"], overall=r["overall"]) for r in results],
        results=results,
        skipped=skipped,
        stock_pass=stock_pass,
        rung_e_reject=rung_e_reject,
        rung_e_refutations=rung_e_refutations,
        annotations=annotations,
        summary=summary,
    )
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    log(f"\nstock_pass={stock_pass}  controls_reject={controls_reject}  rung_e_reject={rung_e_reject}")
    log(f"refutations: {rung_e_refutations}")
    log(f"-> {OUT}")
    log(f"-> {ANNOT}")
    log(f"total elapsed: {round(time.time() - t0, 1)}s")
    return out


def write_annotations(calibration):
    """The four critic gaps a Rung-F reader must carry (also embedded in gates_selftest.json)."""
    ann = dict(
        meta=dict(script="contract_mass_gates.py", generated=time.strftime("%Y-%m-%d %H:%M:%S"),
                  purpose="The four critic gaps the mass-anatomy contract round must not let a Rung-F "
                          "reader be whipsawed by."),
        critic_gaps=dict(
            i_spine_convention_none=dict(
                canonical="NONE", gated=False, report_only_forever=True,
                detail="Three spine conventions disagree in magnitude AND direction (lane ray-march "
                       "stock 0.510/RungE 0.531; falsifier graph-BFS 0.611/0.758; robust proxy "
                       "reverses). Spine is COMPUTED + REPORTED but never gated."),
            ii_n1_hard_constraint=dict(
                n_grass_desert_sites_mapwide=1, verified="scout n_components=1; critic.py straddle "
                "cells map-wide = 4, all in one block cluster (13-15,11-12)",
                detail="EVERY primary ceiling (R1 floors, R2 saturation+fringe+floating, R3 backing) "
                       "is measured on the map's ONLY grass|desert junction. No leave-one-site-out is "
                       "possible; the gates are a CENSUS of the only lawful instance. Each gate leans "
                       "on WIDE-margin signals, never a knife-edge on stock."),
            iii_grass_adjacent_is_proximity_not_edge_sharing=dict(
                detail="sites.json `grass_adjacent` = 8-conn cell PROXIMITY, NOT mesh-edge sharing. "
                       "The 777-cell topo-17 mass is 'grass_adjacent' yet shares ZERO grass|desert "
                       "MESH EDGES map-wide (critic.py n_topo17_grass_shared_edges=0). topo-17 plain "
                       "desert NEVER meets grass; only the topo-16 skin does. A Rung-F reader must "
                       "not treat topo-17 proximity as an ecotone edge."),
            iv_all_coasts_law=dict(
                gate="R1",
                detail="The realized-boundary standoff is measured to EVERY coast the loaded region "
                       "owns -- the desert lobe's OWN coast included, not only the grass lobe's. That "
                       "is the mass-thickness enforcement: a desert lobe too thin puts its own coast "
                       "near the ecotone waist, dropping the body-tri/boundary-cell standoff below "
                       "the floor. Land-perimeter (staged) + sea-vertex (stock) are both whole-region "
                       "so both honour it; v2 makes it law + adds the staged-sea-underlap detector "
                       "(a full-block sea plane over the ecotone -> CONVENTION-INVALID, not a PASS)."),
        ),
        round3_beats_closed=dict(
            note="v4 closed the TWO fresh beats the round-2 re-audit (contract_mass_reaudit2.py) found "
                 "in v3. All NINE probes (four v1 + three round-1 + these two) now FAIL and both round-2 "
                 "CONTROLS still fail -- out/contract_mass/probe_rerun.json.",
            beat1_R3_skin_backing_interface=dict(
                probe="P3_R3_TENDRIL_BACKING", severity="SEVERE",
                was="PASS-ALL-THREE (normal-pipeline): a grass-wrapped skin bridged to a remote >=130 "
                    "dune blob by a 1-cell topo-17 tendril satisfied v3's mere 8-conn reachability "
                    "(reachable 131).",
                fix="gate_r3 now requires, beyond reachable-extent >= 130, that the ecotone-reachable "
                    "topo-16 skin meet the reachable desert-family backing across a BROAD 4-conn "
                    "interface (>= 20 cell-adjacency pairs; stock live-measured 125, a thread 1) AND "
                    "that the connection survive 1-cell morphological erosion (stock 129 backing cells; "
                    "a thread erodes to 0). Both pinned into calibration. TENDRIL beat: interface 1 < "
                    "20, erosion 0 -> R3 FAIL -> suite FAIL. The TENDRIL_CONTROL (no tendril) still "
                    "FAILs at reachable 0.",
                provenance="stock interface 125 pairs (73 skin cells / 68 backing cells) + erosion 129 "
                           "live-measured, calibration-pinned; corroborates falsifier C's '151 dunes-"
                           "neighbour tris' broad front. n=1 site -> the floor 20 leans on the WIDE gap "
                           "(thread ~1-2 vs stock 125), never a knife-edge."),
            beat2_R1_coincident_tri_dedup=dict(
                probe="P3_R1_DOUBLED_LAKE",
                was="PASS R1 (coincident-geometry, normal for overlapping carries): doubling the desert "
                    "tris lining an internal ocean hole made their hole-facing edges 2-owner, erasing "
                    "the internal-lake coast from the single-owner silhouette -> body-tri standoff "
                    "inflated 1.333u -> 81.333u -> false PASS (the UNSAFE direction).",
                fix="single_owner_edges now DEDUPLICATES coincident-duplicate triangles (canonical "
                    "sorted rounded-vertex-position keys, tol 1e-3u) before extracting the silhouette. "
                    "A strict NO-OP on clean geometry (0 removed on stock/rung_e/rung_d/rung_c -- "
                    "reported in gate_r1 diagnostics n_coincident_tris_deduped), so the prior matrix is "
                    "bit-identical; the beat dedups 40 tris, the lake coast reappears, body-tri "
                    "standoff -> 1.333u == its control -> FAIL."),
        ),
        round2_beats_closed=dict(
            note="v3 closed the three fresh beats the re-audit (contract_mass_reaudit.py) found in v2. "
                 "All seven probes (four v1 + these three) now FAIL -- out/contract_mass/probe_rerun.json.",
            beat1_R3_adjacency=dict(
                probe="P2_SUITE_FAKE_BACKING", was="PASS-ALL-THREE (normal-pipeline)",
                fix="gate_r3 now floods 8-conn from the boundary-desert skin through the mass cells "
                    "{16,17,19,20,41} and verdicts on the largest ecotone-REACHABLE backing component, "
                    "not mere presence in the region. A disjoint dune blob the skin does not reach no "
                    "longer counts. Stock reachable-backing == whole-region == 143 (measure_v2.json)."),
            beat2_R2_penetration=dict(
                probe="P2_R2_DEEP_TEETH", was="PASS R2 (normal-pipeline, bimodal comb)",
                fix="gate_r2 adds a PENETRATION ceiling: fraction of the dressed body tris at BFS "
                    "band>=2 must be <= 0.25 (stock 0.1231; DEEP_TEETH 0.3333). The aggregate fringe "
                    "ratio is blind to a bimodal depth distribution; the per-band penetration test is "
                    "not."),
            beat3_R2_label_blind_uv=dict(
                probe="P2_R2_XFAM_MISLABEL", was="PASS R2 (malformed-build, cross-family)",
                fix="label_blind_desert_body is now UV-DRIVEN + family-blind: a tri is counted iff its "
                    "UV is a gd/dd decal or desert-mains rect, EXCEPT the legit gd-on-grass / "
                    "dd-on-dunes opposite-side halves (excluded + counted). A gd-decal UV tagged "
                    "topo-49/fam=None lands IN the body with its fam/topo disagreement COUNTED + "
                    "reported -- the v2 fam!=desert hard-filter that silently dropped it is gone. "
                    "Reproduces stock 422/0.5024/0.6351 bit-for-bit (0 disagreements, 180 grass-side + "
                    "60 dunes-side decals excluded+reported)."),
        ),
        documented_residuals=dict(
            note="Known, bounded gaps carried honestly for a Rung-F reader -- none re-open a closed beat.",
            r1_staged_sea_underlap_sub_threshold=dict(
                status="reasoned-not-built (as in the original audit #4)",
                detail="THE STAGED-UNDERLAP DETECTOR flags a full-block sea plane (>= 56u in BOTH axes) "
                       "over the ecotone as CONVENTION-INVALID. A staged sea override SMALLER than a "
                       "full block (< 56u in either axis) sitting over the boundary would not trip the "
                       "full-block test and could still inflate the land-perimeter standoff. No stock or "
                       "control build exhibits it; a Rung-F mint that stages a sub-block sea over its "
                       "ecotone should be caught by eye. Bounded, not observed."),
            r2_penetration_n1_gray_zone=dict(
                status="acknowledged n=1 gray zone (OWNED, not a knife-edge)",
                detail="The penetration ceiling 0.25 sits between stock's decaying fringe (~0.12) and a "
                       "penetrating comb (~0.33). A connected-tongue comb tuned to ~0.14 penetration "
                       "with floating 0 (P3_R2_CONNECTED_TONGUES) lawfully PASSES -- it is stock-shaped "
                       "by every measured statistic, not a clean intent violation. The 0.25 cut is a "
                       "deliberate wide-margin judgment on the ONLY grass|desert site (n=1); a denser "
                       "penetrating comb (DEEP_TEETH 0.33) is caught."),
            spine_report_only_forever=dict(
                status="canonical NONE (critic gap i)",
                detail="Spine is computed + reported but never gated; three conventions disagree in "
                       "magnitude AND direction. See critic_gaps.i_spine_convention_none."),
        ),
        stock_calibration_snapshot=calibration,
    )
    ANNOT.parent.mkdir(parents=True, exist_ok=True)
    ANNOT.write_text(json.dumps(ann, indent=1), encoding="utf-8")
    return ann


if __name__ == "__main__":
    main()
