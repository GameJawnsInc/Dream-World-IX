"""uvclass DEFORMATION ENVELOPES -- how far can each UV class be moved/stretched before it leaves STOCK's own range?

Two regimes (see NOTES.md):
  CARRIED uv (the kit's carry/transplant/de-tilt operators keep each vertex's uv): the texture strain of a deformation
     F is exactly the change of the per-tri texel jacobian. We measure each class's STOCK envelope (texel density
     px/u and anisotropy s1/s2 over the surface, p1..p99) and report what fraction of that class's tris stay INSIDE
     their class envelope after canonical deformations (uniform scale, plan-only scale, height scale, shears).
     A rotation about Y changes neither density nor anisotropy (always inside; but it rotates the painted texture).
  RE-DERIVED uv: P re-projects (pure-Y needs NO uv change at all: the plan jacobian is untouched), L re-decodes per
     cell (geometry must stay lattice-compatible), W.keyed re-keys per column/course. The limit is then the
     SHAPE envelope: P/L slope (beyond it the plan texture smears up the face), W.keyed column width + face height.

Also: THE CORNER-PIN ENVELOPE -- stock L cells whose 4 vertex uvs are a tile window's 4 corners while the cell's
plan corners sit OFF the 4u lattice: how far does stock itself move an L tile's corners with carried uv?

Outputs out/deform_envelopes.json. Rerun: py studies/terrain-malleability/uvclass/uvc_deform.py
"""
import json
import math
from collections import Counter, defaultdict

import numpy as np

import uvc_common as C
import uvc_classify as K

d = C.load(1, "terrain")
P, T, TOPO = d["P"], d["T"], d["TOPO"]
z = np.load(C.OUT / "features_terrain.npz")
pid = z["pid"]
cls = np.load(C.OUT / "classes_terrain.npz")
tcls, tsub = cls["cls"], cls["sub"]
J, sv, Jp = C.tri_jacobian(P, T)
dens = np.sqrt(sv[:, 0] * sv[:, 1])
aniso = sv[:, 0] / np.maximum(sv[:, 1], 1e-9)
slope = C.slope_deg(P)
nn, area = C.tri_normals(P)
ok = (area > 0.05) & np.isfinite(dens) & (sv[:, 1] > 1e-6)
res = {"n_tris_used": int(ok.sum())}

GROUPS = {"L.rule": ["L.rule"], "L.free": ["L.free"], "L.keyed": ["L.keyed"], "P": ["P.chart", "P.oblique",
          "P.unique", "P.unfit"], "W.keyed": ["W.keyed"], "W.proj/arc/obl": ["W.proj", "W.arc", "W.oblique"],
          "M.flow": ["M.flow"], "M.free/smooth/unique": ["M.free", "M.smooth", "M.unique"]}
gmask = {g: ok & np.isin(tsub, subs) for g, subs in GROUPS.items()}


def pct(a, qs=(1, 5, 50, 95, 99)):
    return {f"p{q}": round(float(np.percentile(a, q)), 3) for q in qs} if len(a) else None


# ---- 1. stock envelopes per class --------------------------------------------------------------------
env = {}
print("class            tris   density px/u p5/p50/p95     aniso p50/p95   slope p50/p90/p99")
for g, m in gmask.items():
    if m.sum() == 0:
        continue
    env[g] = dict(tris=int(m.sum()), density=pct(dens[m]), aniso=pct(aniso[m]), slope=pct(slope[m], (5, 50, 90, 99)))
    e = env[g]
    print(f"{g:16s} {m.sum():6d}   {e['density']['p5']:5.1f}/{e['density']['p50']:5.1f}/{e['density']['p95']:5.1f}"
          f"        {e['aniso']['p50']:.2f}/{e['aniso']['p95']:.2f}     "
          f"{e['slope']['p50']:5.1f}/{e['slope']['p90']:5.1f}/{e['slope']['p99']:5.1f}")
res["stock_envelopes"] = env

# ---- 2. carried-uv deformation survival ----------------------------------------------------------------
def deform(Pt, kind, a):
    Q = Pt.copy()
    if kind == "uniform":
        Q *= a
    elif kind == "plan":
        Q[..., 0] *= a; Q[..., 2] *= a
    elif kind == "height":
        Q[..., 1] *= a
    elif kind == "plan_shear":
        Q[..., 0] += a * Pt[..., 2]
    elif kind == "tilt":                                   # y += a*x  (a ground plane tilted atan(a))
        Q[..., 1] += a * Pt[..., 0]
    return Q


CASES = [("uniform", 0.8), ("uniform", 0.9), ("uniform", 1.1), ("uniform", 1.25), ("uniform", 1.5),
         ("plan", 1.1), ("plan", 1.25), ("plan", 1.5), ("height", 0.5), ("height", 0.75), ("height", 1.25),
         ("height", 1.5), ("height", 2.0), ("plan_shear", 0.1), ("plan_shear", 0.25), ("tilt", 0.05),
         ("tilt", 0.15)]
surv = {}
print("\nCARRIED-uv survival (% of class tris whose density AND anisotropy stay inside the class's stock p1..p99):")
print("case             " + " ".join(f"{g[:9]:>9s}" for g in gmask))
for kind, a in CASES:
    Q = deform(P, kind, a)
    Jq, svq, _ = C.tri_jacobian(Q, T)
    dq = np.sqrt(svq[:, 0] * svq[:, 1])
    aq = svq[:, 0] / np.maximum(svq[:, 1], 1e-9)
    row = {}
    for g, m in gmask.items():
        if g not in env:
            continue
        lo, hi = np.percentile(dens[m], 1), np.percentile(dens[m], 99)
        ahi = np.percentile(aniso[m], 99)
        inside = (dq[m] >= lo) & (dq[m] <= hi) & (aq[m] <= ahi)
        base = (dens[m] >= lo) & (dens[m] <= hi) & (aniso[m] <= ahi)       # ~97-98% by construction
        row[g] = round(100 * float(inside.mean()), 1)
        row[g + "_base"] = round(100 * float(base.mean()), 1)
    surv[f"{kind}x{a}"] = row
    print(f"{kind + ' ' + str(a):16s} " + " ".join(f"{row[g]:9.1f}" for g in gmask if g in env))
res["carried_survival_pct"] = surv

# ---- 3. RE-DERIVED regime: P/L under pure-Y -- the slope envelope ----------------------------------------
plan_law = gmask["L.rule"] | (ok & np.isin(tsub, ["P.chart"]))     # the DECODED plan-law content only
# (L.free carries the canopy's vertical rim curtains and is NOT plan-law -- measured separately below)
res["plan_law_slope_envelope"] = pct(slope[plan_law], (50, 90, 95, 99, 99.9))
print(f"\nplan-law (L+P) slope envelope: {res['plan_law_slope_envelope']}")
# fraction of plan-law tris above slope s: the stock never-above line for a pure-Y reshape
res["plan_law_frac_above"] = {str(s): round(100 * float((slope[plan_law] > s).mean()), 3) for s in (20, 30, 40, 50, 60)}
print(f"  % of plan-law tris steeper than s: {res['plan_law_frac_above']}")
res["L_free_slope_envelope"] = pct(slope[gmask["L.free"]], (50, 90, 95, 99))
print(f"  (L.free slope envelope, canopy curtains included: {res['L_free_slope_envelope']})")

# ---- 4. W.keyed course envelope: column width (along contour) x face height ---------------------------------
up = np.array([0.0, 1.0, 0.0])
nn_u = nn * np.sign(nn[:, 1:2] + 1e-12)
th = np.cross(nn_u, up)
thn = np.linalg.norm(th, axis=1)
th = th / np.where(thn[:, None] > 1e-9, thn[:, None], 1)
wk = gmask["W.keyed"] & (thn > 1e-3)
cw = np.array([np.ptp(P[t] @ th[t]) for t in np.nonzero(wk)[0]])
fh = np.ptp(P[wk][:, :, 1], axis=1)
lipk = wk & (TOPO == 58)
res["W_keyed_course"] = dict(all=dict(column_width=pct(cw), face_dy=pct(fh)),
                             lip58=dict(column_width=pct(np.array([np.ptp(P[t] @ th[t]) for t in np.nonzero(lipk)[0]])),
                                        face_dy=pct(np.ptp(P[lipk][:, :, 1], axis=1))))
print(f"\nW.keyed course envelope (per tri): column width {res['W_keyed_course']['all']['column_width']}"
      f"\n                                  face dy      {res['W_keyed_course']['all']['face_dy']}"
      f"\n  lip58 only: width {res['W_keyed_course']['lip58']['column_width']}  dy {res['W_keyed_course']['lip58']['face_dy']}")

# ---- 5. THE CORNER-PIN ENVELOPE (L cells keyed to a tile window's corners, plan corners off-lattice) -------
groups = defaultdict(list)
Lm = np.isin(tcls, ["L"]) & ok
for t in np.nonzero(Lm)[0]:
    groups[(int(pid[t]), math.floor(P[t, :, 0].mean() / 4), math.floor(P[t, :, 2].mean() / 4))].append(t)
offs, keyed, affine_cells, strain = [], 0, 0, []
by_sub = defaultdict(lambda: [0, 0, []])                   # sub -> [four-corner cells, on-lattice, offsets]
for (p, ci, cj), ts in groups.items():
    if len(ts) != 2:
        continue
    pts = {}
    for t in ts:
        for k in range(3):
            pts.setdefault(C.poskey(P[t, k]), (P[t, k], T[t, k]))
    if len(pts) != 4:
        continue
    Pp = np.array([v[0] for v in pts.values()])
    Tp = np.array([v[1] for v in pts.values()])
    us, vs = np.unique(np.round(Tp[:, 0])), np.unique(np.round(Tp[:, 1]))
    if len(us) != 2 or len(vs) != 2 or np.ptp(us) < 60 or np.ptp(vs) < 60:
        continue                                          # not a 4-corner tile window
    lat = np.array([[4 * ci, 4 * cj], [4 * ci + 4, 4 * cj], [4 * ci, 4 * cj + 4], [4 * ci + 4, 4 * cj + 4]], float)
    dmin = np.array([np.min(np.linalg.norm(lat - q, axis=1)) for q in Pp[:, [0, 2]]])
    keyed += 1
    bs = by_sub[str(tsub[ts[0]])]
    bs[0] += 1
    if dmin.max() < 0.02:
        affine_cells += 1
        bs[1] += 1
        continue
    offs.append(float(dmin.max()))
    bs[2].append(float(dmin.max()))
    # texel strain of the pinned tile vs the lattice square: plan density ratio extremes over the two tris
    for t in ts:
        jp = Jp[t]
        if np.all(np.isfinite(jp)):
            s = np.linalg.svd(jp, compute_uv=False)
            strain.append(float(s[0] / 31.0)); strain.append(float(s[1] / 31.0))
offs = np.array(offs)
res["corner_pin"] = dict(four_corner_cells=keyed, on_lattice=affine_cells, off_lattice=int(len(offs)),
                         max_corner_offset_u=pct(offs, (50, 90, 99, 100)) if len(offs) else None,
                         plan_texel_stretch_vs_31pxu=pct(np.array(strain), (1, 5, 50, 95, 99)) if strain else None)
print(f"\nCORNER-PIN: {keyed} two-tri cells carry a tile window's 4 corners; {affine_cells} sit exactly on the 4u "
      f"lattice, {len(offs)} are pinned OFF-lattice: max corner offset u {res['corner_pin']['max_corner_offset_u']}"
      f"\n  resulting plan texel stretch (x of 31 px/u): {res['corner_pin']['plan_texel_stretch_vs_31pxu']}")

# ---- 6. the coastal lip's along-shore u RATE vs the kit's constant-density rule ---------------------------
# terrain._apply_cliff_rock_uvs docstring: "UV density is tight ~0.0115-0.013 texels/u -- i.e. CONSTANT"; kit
# constants: terrain density=0.0125, meshedit.URATE=0.012643 (atlas u per world unit along the coast).
gh_u = np.abs(np.einsum("nj,nj->n", J[:, 0, :], th)) / C.AW          # raw atlas u per world unit along contour
lip = ok & (TOPO == 58) & (thn > 1e-3)
lip_rate = {}
for s in ("W.keyed", "M.flow", "W.proj"):
    mm = lip & (tsub == s)
    if mm.sum():
        lip_rate[s] = dict(tris=int(mm.sum()), **pct(gh_u[mm], (5, 25, 50, 75, 95)))
lip_rate["all"] = dict(tris=int(lip.sum()), **pct(gh_u[lip], (5, 25, 50, 75, 95)))
lip_rate["frac_in_0.0115_0.013"] = round(float(((gh_u[lip] >= 0.0115) & (gh_u[lip] <= 0.013)).mean()), 3)
res["lip58_contour_u_rate"] = lip_rate
print(f"\nlip58 along-shore u rate (atlas u / world u): {lip_rate}")

res["corner_pin_by_sub"] = {k: dict(four_corner_cells=v[0], on_lattice=v[1], off_lattice=len(v[2]),
                                   max_offset_u=pct(np.array(v[2]), (50, 90, 99)) if v[2] else None)
                            for k, v in by_sub.items()}
for k, v in res["corner_pin_by_sub"].items():
    print(f"  {k}: {v}")
(C.OUT / "deform_envelopes.json").write_text(json.dumps(res, indent=1))
print(f"\nwrote {C.OUT / 'deform_envelopes.json'}")
