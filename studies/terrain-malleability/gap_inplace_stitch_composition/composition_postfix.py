"""S3 RE-RUN AFTER THE FIX (terrain study defects 3-4, 2026-10-08): do successive in-place edits of a real block
compose now that the four writers stack on the deployed override?

Reuses ``composition_probe.py``'s scenarios unchanged (same block (17,11), same edits, same verdict rule, fresh
ABSOLUTE scratch folders under ``STITCH_SCRATCH``; the install is only read). Pre-fix that probe recorded 8/8
cross-writer pairs LAST-WRITER-WINS; the entrance positive control STACKED.

Registered predictions:
  * every pair STACKS, except reshape -> morph: the morph's VertexDisplace was built from a STOCK vertex position,
    which the reshape moved, so the morph refuses (the tweak finds nothing to touch) and nothing is written;
  * a kit island cell (a Terrain override on open-ocean (23,10)) now reshapes (pre-fix: skipped as sea);
  * ``fresh`` reads stock and names what it discards; over an entrance it REFUSES unless ``allow_overwrite``,
    and with it the entrance's event tiles are gone (the pre-fix behaviour, now explicit);
  * world-retarget ``--fresh`` hits the same refusal.
Added 2026-10-08 with defects 6 and 10-11 (the entrance guard, the morph stitch gate), and REVISED the same day
after in-game round 3 refuted the guard's rise rule (ingame/RESULTS.md section 16; the guard now refuses only a
dropped or re-cut entrance tile and reports a moved one):
  * entrance -> reshape: the +3 hill moves the new entrance's tiles; it STACKS, the tiles kept and reported
    (under the rise rule: refused unless allowed);
  * S8 re-run on stock entrance block (7,4): reshape, world-deploy and the in-place morph all ACCEPT the +3 hill and
    keep its tiles (pre-fix only world-deploy refused, under its whole-block rule; under the rise rule all three did);
  * S10 re-run: the morph that moved a Terrain vertex welded to Treno's Object by 1u is no longer clean (stitch).
Writes out/composition_postfix.json.
Run:  py C:/gd/Dream-World-IX/studies/terrain-malleability/gap_inplace_stitch_composition/composition_postfix.py
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import composition_probe as CP                         # noqa: E402

PRED = {"entrance_then_entrance": "STACKS", "reshape_then_reshape": "STACKS", "reshape_then_retarget": "STACKS",
        "retarget_then_reshape": "STACKS", "morph_then_reshape": "STACKS", "reshape_then_morph": "E2 REFUSED",
        "deploy_then_deploy": "STACKS", "entrance_then_reshape": "STACKS, moved tiles reported",
        "reshape_then_entrance": "STACKS", "entrance_then_retarget": "STACKS"}


def _events(mf, blk=CP.BLK):
    d = CP.KM.read_ff9mesh(CP.terrain_file(mf, blk))
    return sum(1 for i in range(0, len(d["indices"]), 3)
               if CP.X.decode_id(int(round(d["tangents"][d["indices"][i]][0])))["event"])


def main():
    res = {"block": list(CP.BLK), "scratch_root": str(CP.ROOT), "predictions": PRED}
    cellA = (2 * CP.BLK[0], 2 * CP.BLK[1])
    cellB = (2 * CP.BLK[0] + 1, 2 * CP.BLK[1] + 1)
    sc = {}
    CP.scenario("entrance_then_entrance", CP.E_entrance(cellA), CP.E_entrance(cellB), sc)
    CP.scenario("reshape_then_reshape", CP.E_reshape(CP.C1), CP.E_reshape(CP.C2), sc)
    CP.scenario("reshape_then_retarget", CP.E_reshape(CP.C1), CP.E_retarget(CP.C1), sc)
    CP.scenario("retarget_then_reshape", CP.E_retarget(CP.C1), CP.E_reshape(CP.C2), sc)
    CP.scenario("morph_then_reshape", CP.E_morph(CP.C1), CP.E_reshape(CP.C2), sc)
    # reshape -> morph: the morph must REFUSE (raise) and write nothing; run by hand, not via CP.scenario
    m1 = CP.fresh("reshape_then_morph__E1thenE2")
    CP.E_reshape(CP.C2)(m1)
    before = CP.terrain_file(m1).read_bytes()
    try:
        CP.E_morph(CP.C1)(m1)
        rm = None
    except ValueError as e:
        rm = str(e)[:200]
    sc["reshape_then_morph"] = {"compare": {"verdict": "E2 REFUSED" if rm and CP.terrain_file(m1).read_bytes()
                                            == before else "E2 NOT REFUSED"}, "E2_error": rm}
    print(f"  reshape_then_morph: {sc['reshape_then_morph']['compare']['verdict']} ({rm})")
    CP.scenario("deploy_then_deploy", CP.E_deploy(CP.C1), CP.E_deploy(CP.C2), sc)
    # entrance -> reshape: the hill moves the new entrance's tiles -- reported, never refused; the tiles stay
    m2 = CP.fresh("entrance_then_reshape__E1thenE2")
    CP.E_entrance(cellA)(m2)
    before, n_ev = CP.terrain_file(m2).read_bytes(), _events(m2)
    er, s2 = None, {}
    try:
        s2 = CP.TER.reshape(m2, at=CP.C2, radius=16.0, amount=3.0, game=CP.GAME, skip_mirror=True)
    except ValueError as e:
        er = str(e)[:240]
    hits = s2.get("entrances") or []
    reported = bool(hits) and all(h["tiles_moved"] and not h["refused"] for h in hits)
    stacked = er is None and CP.terrain_file(m2).read_bytes() != before and _events(m2) == n_ev
    sc["entrance_then_reshape"] = {"compare": {"verdict": ("STACKS, moved tiles reported" if stacked and reported
                                                           else f"error={er} stacked={stacked} reported={reported}")},
                                   "E2_error": er, "entrances": hits}
    print(f"  entrance_then_reshape: {sc['entrance_then_reshape']['compare']['verdict']}")
    CP.scenario("reshape_then_entrance", CP.E_reshape(CP.C2), CP.E_entrance(cellA), sc)
    CP.scenario("entrance_then_retarget", CP.E_entrance(cellA), CP.E_retarget(CP.C2), sc)
    res["scenarios"] = sc

    got = {}
    for name, out in sc.items():
        got[name] = out["compare"]["verdict"]
    res["verdicts"] = got
    res["all_as_predicted"] = got == PRED

    # a kit island on a real disc: pre-fix reshape skipped it as sea; now it stacks on it
    mfk = CP.fresh("kit_island_cell")
    import dataclasses as dc
    src = CP.X.read_block(CP.BLK[0], CP.BLK[1], disc=1, part="terrain", game=CP.GAME)
    CP.KM.deploy_override(dc.replace(src, x=23, y=10, name="Block[23][10] Terrain"), mod_folder=mfk, game=CP.GAME,
                          part="Terrain")
    before = CP.terrain_file(mfk, (23, 10)).read_bytes()
    rk = CP.TER.reshape(mfk, at=(23 * 64 + 32.0, -(10 * 64 + 32.0)), radius=16.0, amount=3.0, game=CP.GAME,
                        skip_mirror=True)
    res["kit_island"] = {"blocks": rk["blocks"], "skipped_sea": rk["skipped_sea"], "stacked_on": len(rk["stacked_on"]),
                         "file_changed": CP.terrain_file(mfk, (23, 10)).read_bytes() != before}

    # fresh over an entrance: refuses; allow_overwrite discards (named); retarget --fresh refuses the same way
    mfe = CP.fresh("fresh_over_entrance")
    CP.E_entrance(cellA)(mfe)
    n_ev = _events(mfe)
    try:
        CP.TER.reshape(mfe, at=CP.C2, radius=16.0, amount=3.0, game=CP.GAME, skip_mirror=True, fresh=True)
        refused = None
    except ValueError as e:
        refused = str(e)[:240]
    kept_after_refusal = _events(mfe)
    ra = CP.TER.reshape(mfe, at=CP.C2, radius=16.0, amount=3.0, game=CP.GAME, skip_mirror=True, fresh=True,
                        allow_overwrite=True)
    ns = argparse.Namespace(block=list(CP.BLK), disc=1, lod="0_1", game=CP.GAME, mod_folder=None, event=None,
                            area=None, topograph=17, center=list(CP.C1), radius=10.0, only_entrances=False,
                            skip_mirror=True, fresh=True, allow_overwrite=False)
    mfr = CP.fresh("fresh_retarget_over_entrance")
    CP.E_entrance(cellA)(mfr)
    ns.mod_folder = mfr
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as se:
        rc = CP.CLI._cmd_world_retarget(ns)
    res["fresh_gate"] = {"entrance_event_tris": n_ev, "reshape_refused": refused,
                         "event_tris_after_refusal": kept_after_refusal,
                         "allow_overwrite_discards": ra.get("fresh_discards"),
                         "allow_overwrite_lost": ra.get("fresh_lost_entrances"),
                         "event_tris_after_allow": _events(mfe),
                         "retarget_fresh_rc": rc, "retarget_fresh_stderr": se.getvalue()[:240]}

    # S8 re-run (defect 6): stock entrance block (7,4), +3 r12 centred on an event tri -- all three writers accept it
    # and keep the tiles (the rise rule they used to share is refuted in game)
    eb = (7, 4)
    st = CP.X.read_block(eb[0], eb[1], disc=1, part="terrain", game=CP.GAME)
    ev = [t for t in range(len(st.tris)) if CP.X.decode_id(int(round(st.tangents[st.tris[t][0]][0])))["event"]]
    cs = [st.verts[i] for i in st.tris[ev[0]]]
    at = (sum(c[0] for c in cs) / 3 + eb[0] * 64, sum(c[2] for c in cs) / 3 - eb[1] * 64)
    s8 = {}
    mf = CP.fresh("S8_reshape")
    try:
        r8 = CP.TER.reshape(mf, at=at, radius=12.0, amount=3.0, game=CP.GAME, skip_mirror=True)
        hit8 = r8.get("entrances") or []
        s8["reshape"] = ("ACCEPTED" if hit8 and all(h["tiles_moved"] and not h["refused"] for h in hit8)
                         else f"no moved-tile report: {hit8}")
    except ValueError as e:
        s8["reshape"] = str(e)[:160]
    d = CP.E_deploy(at, hill=3.0, radius=12.0, blk=eb)(CP.fresh("S8_deploy"))
    s8["world_deploy"] = ("ACCEPTED" if d["rc"] == 0 and "the trigger still fires" in d["stdout"]
                          else f"rc {d['rc']}: {(d['stderr'] or d['stdout'])[:160]}")
    pos = next((v[0] + eb[0] * 64, v[1], v[2] - eb[1] * 64) for v in st.verts
               if 4 < v[0] < 60 and -60 < v[2] < -4 and ((v[0] + eb[0] * 64 - at[0]) ** 2
                                                          + (v[2] - eb[1] * 64 - at[1]) ** 2) < 36)
    n = sum(1 for v in st.verts if (round(v[0] + eb[0] * 64, 4), round(v[1], 4), round(v[2] - eb[1] * 64, 4))
            == (round(pos[0], 4), round(pos[1], 4), round(pos[2], 4)))
    r3 = CP.TR.morph_in_place(CP.fresh("S8_morph"), cell=eb, game=CP.GAME, skip_mirror=True,
                              tweaks=[CP.TR.VertexDisplace(moves={pos: (0.0, 3.0, 0.0)}, expected=n)])
    g = next((g for g in r3["gates"] if g["gate"] == "entrance"), None)
    s8["morph_in_place"] = ("ACCEPTED" if g is None or g["ok"] else f"entrance gate failed: {g}")
    res["S8_morph_clean"] = r3["clean"]
    res["S8_entrance_block"] = s8
    # S10 re-run (defect 11): a Terrain vertex welded to Treno's gate Object, moved 1u by the in-place morph
    ob = (19, 14)
    terb = CP.X.read_block(ob[0], ob[1], disc=1, part="terrain", game=CP.GAME)
    objb = CP.X.read_block(ob[0], ob[1], disc=1, part="object", game=CP.GAME)
    okeys = {(round(v[0], 4), round(v[1], 4), round(v[2], 4)) for v in objb.verts}
    pick = next(v for v in terb.verts if (round(v[0], 4), round(v[1], 4), round(v[2], 4)) in okeys
                and 1 < v[0] < 63 and -63 < v[2] < -1)
    n_ter = sum(1 for v in terb.verts if (round(v[0], 4), round(v[1], 4), round(v[2], 4))
                == (round(pick[0], 4), round(pick[1], 4), round(pick[2], 4)))
    rv = CP.TR.morph_in_place(CP.fresh("S10_object_weld"), cell=ob, game=CP.GAME, skip_mirror=True, tweaks=[
        CP.TR.VertexDisplace(moves={(pick[0] + ob[0] * 64, pick[1], pick[2] - ob[1] * 64): (0.0, 1.0, 0.0)},
                             expected=n_ter)])
    sg = next(g for g in rv["gates"] if g["gate"] == "stitch")
    res["S10_object_weld"] = {"clean": rv["clean"], "stitch": {k: sg[k] for k in ("torn", "max_sep", "by_mesh")},
                              "deployed": rv["deployed"]}
    print("S8 entrance block:", s8)
    print("S10 object weld:", res["S10_object_weld"])

    ok = (res["all_as_predicted"] and res["kit_island"]["file_changed"] and not res["kit_island"]["skipped_sea"]
          and refused is not None and kept_after_refusal == n_ev > 0 and res["fresh_gate"]["event_tris_after_allow"] == 0
          and rc == 2 and "refusing --fresh" in res["fresh_gate"]["retarget_fresh_stderr"]
          and set(s8.values()) == {"ACCEPTED"} and not rv["clean"] and not rv["deployed"] and sg["torn"] >= 1)
    res["ok"] = ok
    (CP.S.OUT / "composition_postfix.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print("verdicts:", json.dumps(got, indent=1))
    print("kit island:", res["kit_island"])
    print("fresh gate:", {k: v for k, v in res["fresh_gate"].items() if k != "allow_overwrite_discards"})
    print("ALL AS PREDICTED" if ok else "MISMATCH -- see out/composition_postfix.json")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
