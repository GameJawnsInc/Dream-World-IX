"""ROUND-3 DIRECTIVE step 1: THE CONTINUOUS-SHIFT SWEEP.

Resolve the seam blocker by MEASUREMENT. Round-2's restructure proved every WHOLE-BLOCK-shift
(64u lattice) center with R>=132 clearance wraps the x=0 seam (west edge x<0), and build_landmass
REFUSES col<0 (the GRID-BOUNDS gate). This drops the shift constraint to a 4u multiple (keeps the
donor cell lattice aligned) and sweeps CONTINUOUS 4u-aligned centers for an OFF-SEAM position with
R >= 132 plus real margin.

Achievable island centers = MEC(935.8,-767.3) + (4*i, 4*j)  [4u-aligned shift preserves the donor
4u cell lattice]. So cx == 3.8 (mod 4), cz == 0.7 (mod 4)  [i.e. cz in {..., -195.3, -191.3, ...}].

OFF-SEAM = the whole minted footprint [cx-R, cx+R] stays inside [0, 1536) (no col<0, no col>=24).
Rmax(center) = min( wrap-aware clearance to nearest stock+live LAND vert, dist to north edge z=0,
dist to south edge z=-1280 ).  A center is a candidate iff its off-seam-max-radius >= 132 with margin.

READ-ONLY: X.read_block (stock) + read live FF9CustomMap-world overrides. No writes to the install.
Writes only out/rung_f/fit_sweep2.json.
"""
import sys, math, json, glob, re
from pathlib import Path
import numpy as np
sys.path.insert(0, '../../ff9mapkit'); sys.path.insert(0, '.')
from ff9mapkit.world import extract as X
from ff9mapkit.world import mesh as M

HERE = Path(__file__).resolve().parent
LIVE = Path("C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX/FF9CustomMap-world")

MECX, MECZ = 935.8, -767.3            # union all-class ecotone MEC center (stock coords)
MEC_R = 71.4                          # binding (boundary-class) enclosing radius
FLOOR = 44.635                        # binding straddle floor
LAND_Y = 0.6

def gather_stock_land():
    land = []
    for by in range(0, 20):
        for bx in range(0, 24):
            try:
                bm = X.read_block(bx, by, disc=1, part='terrain')
            except Exception:
                continue
            ox, oz = X.block_world_origin(bx, by)
            for v in bm.verts:
                if v[1] > LAND_Y:
                    land.append((v[0] + ox, v[2] + oz))
    return land

def gather_live_land():
    land = []
    blocks = set()
    pat = re.compile(r"Block\[(\d+)\]\[(\d+)\] Terrain\.ff9mesh$")
    for f in glob.glob(str(LIVE / "**" / "*Terrain.ff9mesh"), recursive=True):
        mm = pat.search(f.replace("\\", "/"))
        if mm:
            blocks.add((int(mm.group(1)), int(mm.group(2))))
    for (bx, by) in sorted(blocks):
        try:
            rel = M.override_relpath(1, bx, by, part="Terrain")
            p = LIVE / rel
            bm = M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part="terrain")
        except Exception:
            continue
        ox, oz = X.block_world_origin(bx, by)
        for v in bm.verts:
            if v[1] > LAND_Y:
                land.append((v[0] + ox, v[2] + oz))
    return land, sorted(blocks)

def main():
    stock = gather_stock_land()
    live, live_blocks = gather_live_land()
    land = stock + live
    print(f"stock land verts {len(stock)}  live land verts {len(live)}  live blocks {len(live_blocks)}")

    # dedup land to unique 2u cells (clearance changes <2u; keeps numpy arrays small)
    uniq = set((round(lx/2.0)*2.0, round(lz/2.0)*2.0) for (lx, lz) in land)
    LX = np.array([p[0] for p in uniq]); LZ = np.array([p[1] for p in uniq])
    print(f"unique 2u land points {len(uniq)}")

    def clr_row(cx, cz_arr):
        # vectorized clearance for a fixed cx over an array of cz -> return array of clearances
        dx = cx - LX
        dx = dx - 1536.0 * np.round(dx / 1536.0)      # wrap to [-768,768]
        out = np.empty(len(cz_arr))
        for i, cz in enumerate(cz_arr):
            dz = cz - LZ
            out[i] = math.sqrt(float(np.min(dx*dx + dz*dz)))
        return out

    results = []
    best_offseam = None
    best_any = None
    cxs = np.arange(3.8, 1536.0, 4.0)
    cz_arr = np.arange(-3.3, -1280.0, -4.0)
    north = np.abs(cz_arr)              # to z=0
    south = np.abs(-1280.0 - cz_arr)    # to z=-1280
    edge_min = np.minimum(north, south)
    for cx in cxs:
        clr = clr_row(cx, cz_arr)
        rmax = np.minimum(clr, edge_min)
        offseam_cap = min(cx, 1536.0 - cx)
        offseam_r = np.minimum(rmax, offseam_cap)
        # best-any this row
        ia = int(np.argmax(rmax))
        if best_any is None or rmax[ia] > best_any[5]:
            best_any = (round(float(cx),1), round(float(cz_arr[ia]),1), round(float(clr[ia]),1),
                        round(float(north[ia]),1), round(float(south[ia]),1),
                        round(float(rmax[ia]),1), round(float(offseam_r[ia]),1))
        io = int(np.argmax(offseam_r))
        if best_offseam is None or offseam_r[io] > best_offseam[6]:
            best_offseam = (round(float(cx),1), round(float(cz_arr[io]),1), round(float(clr[io]),1),
                            round(float(north[io]),1), round(float(south[io]),1),
                            round(float(rmax[io]),1), round(float(offseam_r[io]),1))
        for j in np.where(offseam_r >= 128.0)[0]:
            results.append((round(float(cx),1), round(float(cz_arr[j]),1), round(float(clr[j]),1),
                            round(float(north[j]),1), round(float(south[j]),1),
                            round(float(rmax[j]),1), round(float(offseam_r[j]),1)))

    results.sort(key=lambda r: -r[6])
    out = dict(
        method="4u-aligned continuous-shift sweep of achievable island centers (MEC + 4*i,4*j); "
               "wrap-aware clearance to stock+live land; off-seam R = min(cx,1536-cx,Rmax).",
        mec=[MECX, MECZ], mec_binding_radius=MEC_R, binding_floor=FLOOR,
        target_realized=50.0, required_guide_R="MEC(71.4)+realized(50)+wander(~8)=~129 -> spec 132",
        n_stock_land=len(stock), n_live_land=len(live), live_blocks=[list(b) for b in live_blocks],
        best_any_center=dict(cx=best_any[0], cz=best_any[1], clearance=best_any[2],
                             north=best_any[3], south=best_any[4], Rmax=best_any[5], offseam_R=best_any[6]),
        best_offseam_center=dict(cx=best_offseam[0], cz=best_offseam[1], clearance=best_offseam[2],
                                 north=best_offseam[3], south=best_offseam[4], Rmax=best_offseam[5],
                                 offseam_R=best_offseam[6]),
        offseam_R132_exists=(best_offseam[6] >= 132.0),
        near_hits_offseamR_ge128=[dict(cx=r[0], cz=r[1], clearance=r[2], north=r[3], south=r[4],
                                       Rmax=r[5], offseam_R=r[6]) for r in results[:40]],
    )
    (HERE / "out" / "rung_f").mkdir(parents=True, exist_ok=True)
    (HERE / "out" / "rung_f" / "fit_sweep2.json").write_text(json.dumps(out, indent=1))
    print("BEST OFF-SEAM:", out["best_offseam_center"])
    print("BEST ANY (may wrap):", out["best_any_center"])
    print("OFF-SEAM R>=132 EXISTS:", out["offseam_R132_exists"])
    print("wrote out/rung_f/fit_sweep2.json")

if __name__ == "__main__":
    main()
