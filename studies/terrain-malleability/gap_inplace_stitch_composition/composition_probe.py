"""METHOD C + D -- do successive in-place edits of a REAL block COMPOSE, and which gates does each writer run?

Every write goes to an ABSOLUTE scratch mod folder under the session scratchpad (``STITCH_SCRATCH``); the game
install is passed explicitly as ``game=`` and is only READ (p0data via extract, the world dispatchers via
entrance.load_all_dispatchers). No .ff9deploy.toml is consulted (library calls take ``mod_folder``/``game``
explicitly; the two CLI handlers get an explicit argparse.Namespace). ``skip_mirror=True`` everywhere (with an
absolute mod folder auto_mirror would only log NOT RUN; its CALL is still traced). world-entrance's dispatcher
backup dir is pinned into scratch (its default is ``Path.cwd()/backups/world-entrance``, entrance.py:953).

Design: for each pair (E1 then E2) on one real block, run E1 alone, E2 alone and E1->E2, each in a FRESH folder,
then diff the final Terrain against stock, against single(E1) and single(E2):
  LAST-WRITER-WINS  final == single(E2) exactly and E1's own effect (single(E1) - stock) is absent
  STACKS            final carries BOTH effects
Positive control: world-entrance twice (two cells of one block) must STACK via read_block_stacked ->
blockmesh_from_ff9mesh; if it does not, the harness cannot falsify F2.
Also: F3 measured on the REAL writer's output (reshape on (7,17): which parts are written, and the torn stock
welds counted from the deployed bytes vs tear_sweep.py's model for the same edit); F4 behaviourally (reshape vs
world-deploy on a real entrance block); a sys.setprofile call trace of every writer for the gate table (D), with
transplant(dry_run=True) as the positive control that the tracer sees weld_audit/_tjunc_gate/census/
_mod_overwrite_gate when they run.
Writes out/composition_probe.json.
Run:  py C:/gd/Dream-World-IX/studies/terrain-malleability/gap_inplace_stitch_composition/composition_probe.py
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import math
import shutil
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stitchlib as S                                  # noqa: E402
from ff9mapkit.world import extract as X               # noqa: E402
from ff9mapkit.world import mesh as KM                 # noqa: E402
from ff9mapkit.world import terrain as TER             # noqa: E402
from ff9mapkit.world import transplant as TR           # noqa: E402
from ff9mapkit.world import entrance as ENT            # noqa: E402
from ff9mapkit import cli as CLI                       # noqa: E402

GAME = S.GAME
ROOT = S.SCRATCH / "compose"
BLK = (17, 11)                      # interior land: Terrain only, no Object/water/event tris, 4 land neighbours
CX, CZ = BLK[0] * 64 + 32.0, -(BLK[1] * 64 + 32.0)
C1, C2 = (CX - 4.0, CZ), (CX + 4.0, CZ)
GATES = {
    "MOD-OVERWRITE": {"mod_overwrite_gate", "_mod_overwrite_gate", "existing_overrides", "fresh_discard_note"},
    "weld_audit": {"weld_audit"},
    "T-junction": {"_tjunc_gate"},
    "placement census": {"census"},
    "one-way-wall gate": {"_walk_gate"},
    "in-place-frame gate": {"_frame_set"},
    "ledger refusal": {"_ledger_shas"},
    "auto_mirror": {"auto_mirror"},
    "stacked read": {"read_block_stacked", "blockmesh_from_ff9mesh", "read_deployed_blocks"},
    "pristine read": {"read_block", "world_tris"},
}


def f32(v):
    return struct.unpack("<f", struct.pack("<f", v))[0]


def fresh(name):
    d = ROOT / name
    if d.exists():
        shutil.rmtree(d)
    mf = d / "FF9CustomMap-probe"
    mf.mkdir(parents=True)
    return str(mf)


class Tracer:
    def __init__(self):
        self.calls = Counter()

    def __call__(self, frame, event, arg):
        if event == "call":
            co = frame.f_code
            fn = co.co_filename.replace("\\", "/")
            if "/ff9mapkit/ff9mapkit/" in fn:
                self.calls[(fn.rsplit("/ff9mapkit/ff9mapkit/", 1)[1], co.co_name)] += 1

    def __enter__(self):
        sys.setprofile(self)
        return self

    def __exit__(self, *a):
        sys.setprofile(None)

    def gates(self):
        names = {n for (_f, n) in self.calls}
        return {g: sorted(names & fs) for g, fs in GATES.items() if names & fs}


def terrain_file(mf, blk=BLK):
    return Path(mf) / KM.override_relpath(1, blk[0], blk[1], "0_1", "Terrain")


def read_final(mf, blk=BLK):
    p = terrain_file(mf, blk)
    if not p.is_file():
        return None
    d = KM.read_ff9mesh(p)
    V, Tn, I = d["verts"], d["tangents"], d["indices"]
    # CORNER order (vertex = verts[indices[c]]): stock's vertex array is a permutation of its corner order,
    # and morph_in_place re-emits a soup in corner order -- compare corners, not raw vertex slots
    return {"y": [V[i][1] for i in I], "xz": [(V[i][0], V[i][2]) for i in I],
            "id": [int(round(Tn[i][0])) for i in I], "n": len(I)}


def stock(blk=BLK):
    bm = X.read_block(blk[0], blk[1], disc=1, part="terrain", game=GAME)
    V, Tn, I = bm.verts, bm.tangents, bm.flat_index
    return {"y": [f32(V[i][1]) for i in I], "xz": [(f32(V[i][0]), f32(V[i][2])) for i in I],
            "id": [int(round(Tn[i][0])) for i in I], "n": len(I)}


def delta(a, b):
    """per-vertex y delta + idall-change set of b relative to a (1:1 vertex order; asserts alignment)."""
    assert a["n"] == b["n"], (a["n"], b["n"])
    assert all(abs(p[0] - q[0]) < 1e-6 and abs(p[1] - q[1]) < 1e-6 for p, q in zip(a["xz"], b["xz"])), "xz moved"
    dy = [q - p for p, q in zip(a["y"], b["y"])]
    did = {i for i, (p, q) in enumerate(zip(a["id"], b["id"])) if p != q}
    return dy, did


def compare(name, st, s1, s2, fin):
    d1, i1 = delta(st, s1)
    d2, i2 = delta(st, s2)
    df, ifn = delta(st, fin)
    e1_y = [i for i, d in enumerate(d1) if abs(d) > 1e-4]
    e1_y_kept = sum(1 for i in e1_y if abs(df[i] - (d1[i] + d2[i])) < 1e-3)
    e1_y_lost = sum(1 for i in e1_y if abs(df[i] - d2[i]) < 1e-4 and abs(d1[i]) > 1e-4)
    e1_id_kept = sum(1 for i in i1 if fin["id"][i] == s1["id"][i])
    eq_s2 = all(abs(p - q) < 1e-5 for p, q in zip(fin["y"], s2["y"])) and fin["id"] == s2["id"]
    eq_st = all(abs(p - q) < 1e-5 for p, q in zip(fin["y"], st["y"])) and fin["id"] == st["id"]
    r = {"E1_y_verts": len(e1_y), "E1_y_kept_in_final": e1_y_kept, "E1_y_lost": e1_y_lost,
         "E1_idall_verts": len(i1), "E1_idall_kept_in_final": e1_id_kept,
         "E2_y_verts": sum(1 for d in d2 if abs(d) > 1e-4), "E2_idall_verts": len(i2),
         "final_equals_single_E2": eq_s2, "final_equals_stock": eq_st,
         "final_max_abs_dy_vs_stock": round(max((abs(d) for d in df), default=0.0), 4)}
    stacked = (e1_y_kept == len(e1_y)) and (e1_id_kept == len(i1)) and (len(e1_y) + len(i1) > 0)
    lost = (len(e1_y) + len(i1) > 0) and e1_y_kept == 0 and e1_id_kept == 0 and eq_s2
    r["verdict"] = "STACKS" if stacked else ("LAST-WRITER-WINS (E1 erased)" if lost else "PARTIAL/OTHER")
    print(f"  {name}: {r['verdict']}  E1 y-verts {len(e1_y)} kept {e1_y_kept}; E1 idall-verts {len(i1)} kept "
          f"{e1_id_kept}; final==single(E2) {eq_s2}")
    return r


def inventory(mf):
    root = Path(mf)
    files = sorted(str(p.relative_to(root)).replace("\\", "/") for p in root.rglob("*") if p.is_file())
    baks = [f for f in files if ".bak-" in f]
    led = root / KM.LEDGER_NAME
    nled = len(led.read_text(encoding="utf-8").splitlines()) if led.is_file() else 0
    return {"files": files, "bak": baks, "ledger_lines": nled}


# ------------------------------------------------------------------ the edits (each a closure on a folder) ----
def E_reshape(at, amount=3.0, radius=16.0):
    def run(mf):
        return TER.reshape(mf, at=at, radius=radius, amount=amount, game=GAME, skip_mirror=True)
    return run


def E_retarget(at, radius=10.0, topograph=17, blk=BLK):
    def run(mf):
        ns = argparse.Namespace(block=list(blk), disc=1, lod="0_1", game=GAME, mod_folder=mf, event=None,
                                area=None, topograph=topograph, center=list(at), radius=radius,
                                only_entrances=False, skip_mirror=True, fresh=False,
                                allow_overwrite=False)
        with contextlib.redirect_stdout(io.StringIO()) as so, contextlib.redirect_stderr(io.StringIO()) as se:
            rc = CLI._cmd_world_retarget(ns)
        return {"rc": rc, "stdout": so.getvalue()[-400:], "stderr": se.getvalue()[-400:]}
    return run


def E_deploy(center, hill=3.0, radius=16.0, blk=BLK, allow_entrances=False):
    def run(mf):
        ns = argparse.Namespace(block=list(blk), cluster=None, disc=1, lod="0_1", mod_folder=mf, hill=hill,
                                crater=0.0, flatten=False, height=None, radius=radius, center=list(center),
                                falloff="smooth", no_normals=False, allow_entrances=allow_entrances, spike=0.0,
                                lift=0.0, skip_mirror=True, game=GAME, fresh=False,
                                allow_overwrite=False)
        with contextlib.redirect_stdout(io.StringIO()) as so, contextlib.redirect_stderr(io.StringIO()) as se:
            rc = CLI._cmd_world_deploy(ns)
        return {"rc": rc, "stdout": so.getvalue()[-4000:], "stderr": se.getvalue()[-600:]}
    return run


def _interior_vertex(near):
    st = X.read_block(BLK[0], BLK[1], disc=1, part="terrain", game=GAME)
    best = None
    for v in st.verts:
        wx, wz = v[0] + BLK[0] * 64, v[2] - BLK[1] * 64
        if 4 < v[0] < 60 and -60 < v[2] < -4:
            d = math.hypot(wx - near[0], wz - near[1])
            if best is None or d < best[0]:
                best = (d, (wx, v[1], wz))
    pos = best[1]
    n = sum(1 for v in st.verts if (round(v[0] + BLK[0] * 64, 4), round(v[1], 4), round(v[2] - BLK[1] * 64, 4))
            == (round(pos[0], 4), round(pos[1], 4), round(pos[2], 4)))
    return pos, n


def E_morph(near, dy=1.0):
    def run(mf):
        pos, n = _interior_vertex(near)
        tw = TR.VertexDisplace(moves={pos: (0.0, dy, 0.0)}, expected=n, part=None)
        return TR.morph_in_place(mf, cell=BLK, tweaks=[tw], game=GAME, skip_mirror=True)
    return run


def E_entrance(cell, field=30999):
    def run(mf):
        bk = Path(mf).parent / "eb-backups"
        with contextlib.redirect_stdout(io.StringIO()):
            return ENT.author_entrance(cell=cell, mod_folder=mf, direct_field=field, game=GAME,
                                       backup_dir=str(bk), skip_mirror=True)
    return run


def scenario(name, e1, e2, res):
    st = stock()
    out = {}
    m1 = fresh(f"{name}__E1only")
    with Tracer() as t1:
        out["E1_result"] = _short(e1(m1))
    m2 = fresh(f"{name}__E2only")
    with Tracer() as t2:
        out["E2_result"] = _short(e2(m2))
    mc = fresh(f"{name}__E1thenE2")
    e1(mc)
    with Tracer() as tc:
        e2(mc)
    s1, s2, fin = read_final(m1), read_final(m2), read_final(mc)
    out["inventory_composed"] = inventory(mc)
    out["compare"] = compare(name, st, s1, s2, fin)
    out["gates_E1"] = t1.gates()
    out["gates_E2"] = t2.gates()
    out["gates_E2_after_E1"] = tc.gates()
    res[name] = out


def _short(r):
    if isinstance(r, dict):
        keep = {}
        for k, v in r.items():
            if k in ("rc", "stderr", "stdout", "blocks", "deployed", "touched", "gates", "clean", "tiles_set",
                     "terrain_override", "skipped_sea", "walkability", "dispatchers_written", "backups"):
                keep[k] = v if not isinstance(v, list) or len(v) < 30 else v[:30]
        return keep
    return str(r)[:300]


def main():
    res = {"block": list(BLK), "C1": C1, "C2": C2, "scratch_root": str(ROOT)}
    print(f"composition block {BLK}, centres C1 {C1} C2 {C2}; scratch {ROOT}")
    cellA = (2 * BLK[0], 2 * BLK[1])
    cellB = (2 * BLK[0] + 1, 2 * BLK[1] + 1)
    sc = {}
    # positive control first: the harness must see stacking where the code stacks
    scenario("entrance_then_entrance", E_entrance(cellA), E_entrance(cellB), sc)
    scenario("reshape_then_reshape", E_reshape(C1), E_reshape(C2), sc)
    scenario("reshape_then_retarget", E_reshape(C1), E_retarget(C1), sc)
    scenario("retarget_then_reshape", E_retarget(C1), E_reshape(C2), sc)
    scenario("morph_then_reshape", E_morph(C1), E_reshape(C2), sc)
    scenario("reshape_then_morph", E_reshape(C2), E_morph(C1), sc)
    scenario("deploy_then_deploy", E_deploy(C1), E_deploy(C2), sc)
    scenario("entrance_then_reshape", E_entrance(cellA), E_reshape(C2), sc)
    scenario("reshape_then_entrance", E_reshape(C2), E_entrance(cellA), sc)
    scenario("entrance_then_retarget", E_entrance(cellA), E_retarget(C2), sc)
    res["scenarios"] = sc

    # ---- .bak parking: two differing writes to one file inside one second -----------------------------------
    # deploy_override (mesh.py:501) names a park `.bak-%Y%m%d-%H%M%S`: 1 s resolution. Timing-dependent, so run
    # 5 trials of 3 back-to-back differing writes and report how many trials lost a park (same-second name).
    import time as _t
    ref = {}
    for amt in (1.0, 2.0):
        mr = fresh(f"bak_ref_{amt:g}")
        TER.reshape(mr, at=C1, radius=16.0, amount=amt, game=GAME, skip_mirror=True)
        ref[amt] = terrain_file(mr).read_bytes()
    trials = []
    for k in range(5):
        mf = fresh(f"bak_same_second_{k}")
        stamps = []
        for amt in (1.0, 2.0, 3.0):
            TER.reshape(mf, at=C1, radius=16.0, amount=amt, game=GAME, skip_mirror=True)
            stamps.append(_t.strftime("%H%M%S"))
        inv = inventory(mf)
        held = sorted(a for a, b in ref.items() for f in inv["bak"] if (Path(mf) / f).read_bytes() == b)
        trials.append({"bak_files": len(inv["bak"]), "parks_expected": 2, "bytes_held_of_amount": held,
                       "write_seconds": stamps})
    lost = [t for t in trials if t["bak_files"] < 2]
    mfc = fresh("bak_control_spaced")
    for amt in (1.0, 2.0, 3.0):
        TER.reshape(mfc, at=C1, radius=16.0, amount=amt, game=GAME, skip_mirror=True)
        _t.sleep(1.2)
    invc = inventory(mfc)
    res["bak_parking"] = {"trials": trials, "trials_that_lost_a_park": len(lost),
                          "control_spaced_writes_bak_files": invc["bak"],
                          "note": "two parks inside one wall-clock second share a name; shutil.copyfile overwrites "
                                  "the earlier park, so that write's bytes are unrecoverable"}
    print(f"bak parking: {len(lost)}/5 trials of 3 back-to-back writes lost a park "
          f"({[t['bak_files'] for t in trials]} .bak files per trial, 2 expected); "
          f"control 1.2 s apart -> {len(invc['bak'])} .bak files")

    # ---- a KIT island on a real disc: reshape skips it as sea (pristine read), entrance stacks on it ----------
    mfk = fresh("kit_island_cell")
    src_bm = X.read_block(BLK[0], BLK[1], disc=1, part="terrain", game=GAME)
    import dataclasses as _dc
    kit = _dc.replace(src_bm, x=23, y=10, name="Block[23][10] Terrain")
    KM.deploy_override(kit, mod_folder=mfk, game=GAME, part="Terrain")
    before = terrain_file(mfk, (23, 10)).read_bytes()
    rk = TER.reshape(mfk, at=(23 * 64 + 32.0, -(10 * 64 + 32.0)), radius=16.0, amount=3.0, game=GAME,
                     skip_mirror=True)
    after = terrain_file(mfk, (23, 10)).read_bytes()
    ek = E_entrance((46, 20))(mfk)
    after_e = terrain_file(mfk, (23, 10)).read_bytes()
    ke = KM.read_ff9mesh(terrain_file(mfk, (23, 10)))
    n_ev = sum(1 for i in range(0, len(ke["indices"]), 3)
               if X.decode_id(int(round(ke["tangents"][ke["indices"][i]][0])))["event"])
    res["kit_island_on_real_disc"] = {"reshape_blocks": rk["blocks"], "reshape_skipped_sea": rk["skipped_sea"],
                                      "reshape_changed_file": before != after,
                                      "entrance_changed_file": after != after_e, "event_tris_after_entrance": n_ev}
    print(f"kit island (23,10) on disc 1: reshape blocks {rk['blocks']} skipped_sea {rk['skipped_sea']} "
          f"(file changed {before != after}); entrance changed file {after != after_e}, event tris {n_ev}")

    # ---- F3 on the REAL writer: reshape a beach seam on (7,17) and count torn welds from the deployed bytes ----
    mf = fresh("F3_beach_reshape")
    with Tracer() as tf3:
        summ = TER.reshape(mf, at=(480.0, -1120.0), radius=16.0, amount=3.0, game=GAME, skip_mirror=True)
    inv = inventory(mf)
    written_parts = sorted({f.rsplit("] ", 1)[1].split(".")[0] for f in inv["files"] if f.endswith(".ff9mesh")})
    M = S.load_disc(1)
    torn = Counter()
    torn_pos = 0
    for blk in [tuple(b["block"]) for b in summ["blocks"]]:
        dep = KM.read_ff9mesh(terrain_file(mf, blk))
        ter = M[(blk[0], blk[1], "terrain")]
        assert dep["vcount"] == len(ter.lv) and all(abs(a[0] - b[0]) < 1e-6 and abs(a[2] - b[2]) < 1e-6
                                                    for a, b in zip(ter.lv, dep["verts"])), "reshape slot order"
        partners = defaultdict(set)
        for (x, y, p), m in M.items():
            if p == "terrain" or abs(x - blk[0]) > 1 or abs(y - blk[1]) > 1:
                continue
            for wp in m.wv:
                partners[S.wrap_key(wp)].add(p)
        seen = set()
        for lv0, dv in zip(ter.lv, dep["verts"]):
            if lv0 in seen:
                continue
            seen.add(lv0)
            wp = (lv0[0] + blk[0] * 64, lv0[1], lv0[2] - blk[1] * 64)
            ps = partners.get(S.wrap_key(wp))
            if ps and abs(dv[1] - lv0[1]) > S.TOL:
                torn_pos += 1
                for p in ps:
                    torn[p] += 1
    model = [r for r in json.loads((S.OUT / "tear_sweep.json").read_text(encoding="utf-8"))["rows"]
             if r["block"] == [7, 17] and r["centre"] == [480.0, -1120.0] and r["amount"] == 3.0
             and r["radius"] == 16.0]
    res["F3_real_writer"] = {"written_parts": written_parts, "files": inv["files"], "torn_positions": torn_pos,
                             "torn_by_partner": dict(torn),
                             "model_torn_positions": model[0]["torn_positions"] if model else None,
                             "model_torn_by_partner": model[0]["torn"] if model else None,
                             "gates": tf3.gates()}
    print(f"F3 real reshape (7,17) +3 r16 at (480,-1120): wrote parts {written_parts}; torn stock welds "
          f"{torn_pos} {dict(torn)}; tear_sweep model {model[0]['torn_positions'] if model else None}")

    # ---- F4: an entrance block -- does terrain.reshape refuse? does world-deploy? ----------------------------
    eb = (7, 4)
    st = X.read_block(eb[0], eb[1], disc=1, part="terrain", game=GAME)
    ev = [t for t in range(len(st.tris)) if X.decode_id(int(round(st.tangents[st.tris[t][0]][0])))["event"]]
    cs = [st.verts[i] for i in st.tris[ev[0]]]
    at = (sum(c[0] for c in cs) / 3 + eb[0] * 64, sum(c[2] for c in cs) / 3 - eb[1] * 64)
    mf = fresh("F4_entrance_block")
    try:
        r = TER.reshape(mf, at=at, radius=12.0, amount=3.0, game=GAME, skip_mirror=True)
        f4_reshape = {"refused": False, "blocks": r["blocks"], "written": inventory(mf)["files"]}
    except ValueError as e:
        f4_reshape = {"refused": True, "error": str(e)[:300]}
    mf2 = fresh("F4_entrance_block_deploy")
    d = E_deploy(at, hill=3.0, radius=12.0, blk=eb)(mf2)
    f4_deploy = {"rc": d["rc"], "refused": d["rc"] == 2 and "REFUSED" in d["stderr"], "stderr": d["stderr"][:300],
                 "written": inventory(mf2)["files"]}
    mf3 = fresh("F4_entrance_block_morph")
    try:
        pos = None
        for v in st.verts:
            if 4 < v[0] < 60 and -60 < v[2] < -4 and math.hypot(v[0] + eb[0] * 64 - at[0], v[2] - eb[1] * 64 - at[1]) < 6:
                pos = (v[0] + eb[0] * 64, v[1], v[2] - eb[1] * 64)
                break
        n = sum(1 for v in st.verts if (round(v[0] + eb[0] * 64, 4), round(v[1], 4), round(v[2] - eb[1] * 64, 4))
                == (round(pos[0], 4), round(pos[1], 4), round(pos[2], 4)))
        r3 = TR.morph_in_place(mf3, cell=eb, tweaks=[TR.VertexDisplace(moves={pos: (0.0, 3.0, 0.0)}, expected=n)],
                               game=GAME, skip_mirror=True)
        f4_morph = {"refused": False, "clean": r3["clean"], "written": inventory(mf3)["files"]}
    except ValueError as e:
        f4_morph = {"refused": True, "error": str(e)[:300]}
    res["F4"] = {"block": list(eb), "event_tris": len(ev), "at": at, "reshape": f4_reshape, "world_deploy": f4_deploy,
                 "morph_in_place": f4_morph}
    print(f"F4 entrance block {eb} ({len(ev)} event tris): reshape refused={f4_reshape['refused']}; "
          f"world-deploy refused={f4_deploy['refused']} rc={f4_deploy['rc']}; morph_in_place refused="
          f"{f4_morph['refused']}")

    # ---- VertexDisplace reach: morph_in_place on a Terrain vertex welded to an OBJECT (outside PARTS) --------
    ob = (19, 14)                                                # Treno gate (world-locate case 6)
    terb = X.read_block(ob[0], ob[1], disc=1, part="terrain", game=GAME)
    objb = X.read_block(ob[0], ob[1], disc=1, part="object", game=GAME)
    okeys = {(round(v[0], 4), round(v[1], 4), round(v[2], 4)) for v in objb.verts}
    pick = None
    for v in terb.verts:
        k = (round(v[0], 4), round(v[1], 4), round(v[2], 4))
        if k in okeys and 1 < v[0] < 63 and -63 < v[2] < -1:
            pick = v
            break
    wpos = (pick[0] + ob[0] * 64, pick[1], pick[2] - ob[1] * 64)
    n_ter = sum(1 for v in terb.verts if (round(v[0], 4), round(v[1], 4), round(v[2], 4)) ==
                (round(pick[0], 4), round(pick[1], 4), round(pick[2], 4)))
    n_obj = sum(1 for v in objb.verts if (round(v[0], 4), round(v[1], 4), round(v[2], 4)) ==
                (round(pick[0], 4), round(pick[1], 4), round(pick[2], 4)))
    mfv = fresh("vertexdisplace_object_weld")
    rv = TR.morph_in_place(mfv, cell=ob, tweaks=[TR.VertexDisplace(moves={wpos: (0.0, 1.0, 0.0)}, expected=n_ter)],
                           game=GAME, skip_mirror=True)
    invv = inventory(mfv)
    res["vertexdisplace_object_weld"] = {"block": list(ob), "vertex_world": wpos, "terrain_instances": n_ter,
                                         "object_instances_at_same_pos": n_obj, "clean": rv["clean"],
                                         "gates": rv["gates"], "touched": rv["touched"],
                                         "written": [f for f in invv["files"] if f.endswith(".ff9mesh")]}
    print(f"VertexDisplace on a Terrain|Object weld at {ob}: gates clean={rv['clean']}, touched {rv['touched']}, "
          f"wrote {res['vertexdisplace_object_weld']['written']}; the {n_obj} Object instance(s) stay put -> torn by 1.0u")

    # ---- D positive control: the tracer must see transplant's gates when they run (dry run, open ocean) ------
    mf = fresh("D_control_transplant_dry")
    with Tracer() as tt:
        try:
            r = TR.transplant(mf, cell=(23, 10), donor=(7, 17), game=GAME, dry_run=True)
            ctl = {"clean": r.get("clean"), "gates_reported": [g.get("gate") for g in r.get("gates", [])][:40]}
        except Exception as e:                                              # noqa: BLE001
            ctl = {"error": f"{type(e).__name__}: {str(e)[:300]}"}
    ctl["traced_gates"] = tt.gates()
    ctl["wrote"] = inventory(mf)["files"]
    res["D_control_transplant_dry_run"] = ctl
    print(f"D control transplant dry-run: traced {ctl['traced_gates'].keys()} wrote {ctl['wrote']}")
    p = S.save_json("composition_probe.json", res)
    print("->", p)


if __name__ == "__main__":
    main()
