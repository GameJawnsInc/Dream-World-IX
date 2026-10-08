"""THE BIND ORACLE -- which loose world-mesh override files the engine ACTUALLY binds, cell by cell.

Models the patched engine's load path exactly (all STOCK unless marked; cite = current clone lines,
provenance via provenance.py):
  * WMWorld.LoadBlock(disc, block)            WMWorld.cs:516-544  (IsSea branch STOCK; divert s34/s74 PATCH)
      IsSea && LandDonorPrefab!=null && HasLandOverride(tag,x,y)   -> ResolveReclaimDonor   (s34/s74)
      IsSea otherwise                                              -> SeaBlockPrefab = Block[12][0]f (disc 1!)
      !IsSea                                                       -> own prefab WorldDisc{disc}/r{y}/Block[x][y]
    UpdateLoadBlocks (WMWorld.cs:1287-1303) mirrors it; LoadBlockAsync (:886-908) only for !IsSea.
  * HasLandOverride = File.Exists of 'Block[x][y] Terrain.ff9mesh' in ANY mod folder (WorldMeshOverride.cs:80-83, s34).
  * ResolveReclaimDonor (WMWorld.cs:549-569, s34/s74): first-priority 'Block[x][y] Donor.txt' -> that prefab
    (bad/missing -> Block[12][10]); no sidecar -> LandDonorPrefab = Block[12][10] of the CURRENT disc (:1210).
  * LoadBlock(prefab, block) (WMWorld.cs:582-810): registration order
      ObjectForm1, TerrainForm1, [bare-Object rule if !ObjectForm1 && TerrainForm1 (s34, render-only)],
      ObjectForm2, TerrainForm2, [block 219: Sea3,Sea4,Sea5,Sea3_2,Sea4_2,Sea5_2 then RETURN],
      VolcanoCrater1, VolcanoLava1, VolcanoCrater2, VolcanoLava2, Beach1, Beach2, Stream, River, RiverJoint,
      Falls, Sea1..Sea6.
  * RegisterBlockComponent (WMWorld.cs:812-858): TryLoad key = '... Block[x][y] ' + PREFAB CHILD NAME, under the
    hard-coded '0_1' directory (s34) -- so the bindable part names are the effective prefab's CHILD names
    (Terrain, Object, Terrain2, Object2, VolcanoCrater1, Sea3_2, ...), never the resource mesh names.
    TryLoadTexture ('.png') is consulted ONLY inside a successful mesh override (:835).
  * TryLoad / TryReadDonorPath take the HIGHEST-priority folder holding the file (Memoria.ini FolderNames order).

CALIBRATION (the money check): every '[WorldMeshOverride] loaded ...' line in a Memoria.log is an engine
receipt. For every block the log shows, the oracle's predicted ordered bind list must EQUAL the logged list
(blocks whose override files changed after the log's timestamp are excluded and reported). Then the
synthetic (11,19) pre-fix state must reproduce the 2026-07-20 receipt (only Sea4 bound; Sea3/Sea5 dead).

Usage:
  py bind_oracle.py [--log PATH] [--game PATH]
Writes out/bind_oracle.json (dead-file inventory + calibration record). Read-only on the install.
"""
import argparse
import json
import os
import re
import struct
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")

FILE_RE = re.compile(r"^Block\[(\d+)\]\[(\d+)\] (.+?)\.(ff9mesh|png|txt)$")
LOG_RE = re.compile(r"^(\d\d)\.(\d\d)\.(\d{4}) (\d\d):(\d\d):(\d\d) \|M\| \[WorldMeshOverride\] loaded "
                    r"'WorldMap/Disc(\d+)/0_1/r(\d+)/Block\[(\d+)\]\[(\d+)\] ([^']+)' from (\S+?)/")

SLOT_ORDER_PRE = ["ObjectForm1", "TerrainForm1", "__bare_object__", "ObjectForm2", "TerrainForm2"]
SLOT_219 = ["Sea3", "Sea4", "Sea5", "Sea3_2", "Sea4_2", "Sea5_2"]
SLOT_ORDER_POST = ["VolcanoCrater1", "VolcanoLava1", "VolcanoCrater2", "VolcanoLava2", "Beach1", "Beach2", "Stream",
                   "River", "RiverJoint", "Falls", "Sea1", "Sea2", "Sea3", "Sea4", "Sea5", "Sea6"]
WALK_SLOTS = {"ObjectForm1", "TerrainForm1", "ObjectForm2", "TerrainForm2", "VolcanoCrater1", "VolcanoLava1",
              "VolcanoCrater2", "VolcanoLava2", "Beach1", "Beach2", "Stream", "River", "RiverJoint", "Falls",
              "Sea1", "Sea2", "Sea3", "Sea4", "Sea5", "Sea6", "Sea3_2", "Sea4_2", "Sea5_2"}


def folder_names(game):
    ini = (game / "Memoria.ini").read_text(encoding="utf-8", errors="replace")
    m = re.search(r'^\s*FolderNames\s*=\s*(.+)$', ini, re.M)
    return re.findall(r'"([^"]*)"', m.group(1)) if m else []


def scan_overrides(game, folders):
    """{(ns_disc, x, y): {part_ext: [(folder_rank, folder, path, mtime)]}} for every loose override file."""
    files = defaultdict(lambda: defaultdict(list))
    for rank, f in enumerate(folders):
        root = game / f / "FF9_Data" / "WorldMap"
        if not root.is_dir():
            continue
        for dd in root.iterdir():
            m = re.match(r"Disc(\d+)$", dd.name)
            if not m or not (dd / "0_1").is_dir():
                continue
            for rdir in (dd / "0_1").iterdir():
                if not rdir.is_dir():
                    continue
                for p in rdir.iterdir():                       # literal iterdir -- NOT glob ('[' is a glob class)
                    fm = FILE_RE.match(p.name)
                    if fm:
                        x, y, part, ext = int(fm.group(1)), int(fm.group(2)), fm.group(3), fm.group(4)
                        if rdir.name != f"r{y}":
                            continue                           # engine key is r{InitialY}: a misfiled file never binds
                        files[(int(m.group(1)), x, y)][f"{part}.{ext}"].append((rank, f, p, p.stat().st_mtime))
    for v in files.values():
        for lst in v.values():
            lst.sort()
    return files


def ff9mesh_header(path):
    b = path.read_bytes()[:20]
    if len(b) < 20 or b[:4] != b"F9WM":
        return None
    ver, vc, ic, fl = struct.unpack("<iiii", b[4:20])
    return {"version": ver, "vcount": vc, "icount": ic, "flags": fl}


class Engine:
    def __init__(self, census):
        self.P = census["prefabs"]
        self.W = census["worlddisc"]

    def is_sea(self, ns, x, y):
        if ns in (1, 4):
            return bool(self.W[f"{x},{y}"]["IsSea"])
        return True                                            # s75 BLANK Path-D grid: all 480 cells IsSea

    def asset_disc(self, ns):
        return ns if ns in (1, 4) else 1                       # s74: sentinel namespace, currentDisc stays 1

    def number(self, ns, x, y):
        return y * 24 + x

    def effective(self, ns, x, y, cell_files):
        """(prefab_key, reason, donor_txt_status)."""
        ad = self.asset_disc(ns)
        if not self.is_sea(ns, x, y):
            return f"d{ad}/{x},{y}", "own prefab (IsSea=0)", "dead (cell is not IsSea)" if "Donor.txt" in cell_files else None
        if "Terrain.ff9mesh" not in cell_files:
            return "d1/12,0f", "SeaBlockPrefab (IsSea, no Terrain override -> divert un-armed)", \
                "dead (divert un-armed)" if "Donor.txt" in cell_files else None
        if "Donor.txt" in cell_files:
            txt = cell_files["Donor.txt"][0][2].read_text(encoding="utf-8", errors="replace").strip().split(",")
            try:
                dx, dy = int(txt[0]), int(txt[1])
                key = f"d{ad}/{dx},{dy}"
                if key in self.P:
                    return key, f"Donor.txt -> {dx},{dy}", "live"
                return f"d{ad}/12,10", f"Donor.txt -> {dx},{dy} MISSING prefab -> LandDonor 12,10", "live-but-fallback"
            except Exception:
                return f"d{ad}/12,10", "Donor.txt unparsable -> LandDonor 12,10", "bad"
        return f"d{ad}/12,10", "LandDonorPrefab 12,10 (no Donor.txt)", None

    def bind_list(self, ns, x, y, prefab_key, cell_files):
        """Ordered [(child_name, slot)] the engine registers, and the subset whose override exists."""
        pf = self.P[prefab_key]
        slots = pf.get("slots", {})
        order = []
        is219 = (self.number(ns, x, y) == 219) and ns in (1, 4)   # SuppressStockLandmarks only on Path D
        for s in SLOT_ORDER_PRE:
            if s == "__bare_object__":
                if "ObjectForm1" not in slots and "TerrainForm1" in slots:
                    order.append(("Object", "__bare_object__"))
                continue
            if s in slots:
                order.append((slots[s], s))
        tail = SLOT_219 if is219 else SLOT_ORDER_POST
        for s in tail:
            if s in slots:
                order.append((slots[s], s))
        bound = [(n, s) for (n, s) in order if f"{n}.ff9mesh" in cell_files]
        return order, bound


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default=None, help="Memoria.log snapshot (default: newest scratch snapshot or live)")
    ap.add_argument("--game", default=str(GAME))
    a = ap.parse_args(argv)
    game = Path(a.game)
    census = json.loads((OUT / "consumption_census.json").read_text(encoding="utf-8"))
    E = Engine(census)
    folders = folder_names(game)
    files = scan_overrides(game, folders)
    report = {"folders": folders, "cells": {}, "dead": Counter(), "contract": Counter()}
    predicted = {}
    for (ns, x, y), cf in sorted(files.items()):
        pkey, why, donor_state = E.effective(ns, x, y, cf)
        order, bound = E.bind_list(ns, x, y, pkey, cf)
        bound_names = {n for n, _ in bound}
        cell = {"effective": pkey, "why": why, "donor_txt": donor_state, "bound": [n for n, _ in bound],
                "stock_free_riders": [n for n, _s in order if _s != "__bare_object__" and f"{n}.ff9mesh" not in cf],
                "dead": {}, "shadowed": {}}
        for pe, lst in cf.items():
            part, ext = pe.rsplit(".", 1)
            if len(lst) > 1:
                cell["shadowed"][pe] = [f for _, f, _, _ in lst[1:]]
            if ext == "ff9mesh":
                if part not in bound_names:
                    if part == "Terrain" and E.is_sea(ns, x, y):
                        reason = "arms the s34 divert only (effective prefab has no TerrainForm1)"
                    else:
                        reason = f"effective prefab {pkey} has no '{part}' child"
                    cell["dead"][pe] = reason
                    report["dead"][f"{ext}:{'divert-arm-only' if 'arms' in reason else 'no-child'}"] += 1
                else:
                    h = ff9mesh_header(lst[0][2])
                    slot = dict(bound)[part]
                    if h is None:
                        report["contract"]["bad-header"] += 1
                    else:
                        if h["vcount"] != h["icount"]:
                            report["contract"]["vcount!=icount (FLAT-MESH INVARIANT)"] += 1
                        if h["icount"] % 3:
                            report["contract"]["icount%3!=0"] += 1
                        if slot in WALK_SLOTS and not (h["flags"] & 4):
                            report["contract"]["walk part WITHOUT tangents (raycast IndexOutOfRange)"] += 1
                        if not (h["flags"] & 2):
                            report["contract"]["no uv (renders texel 0,0)"] += 1
                        report["contract"]["bound-ok-checked"] += 1
            elif ext == "png":
                if part not in bound_names:
                    cell["dead"][pe] = "texture hook fires only inside a bound mesh override"
                    report["dead"]["png:no-mesh-override"] += 1
            elif ext == "txt" and part == "Donor":
                if donor_state and donor_state.startswith("dead"):
                    cell["dead"][pe] = donor_state
                    report["dead"]["Donor.txt:" + donor_state] += 1
        report["cells"][f"{ns}:{x},{y}"] = cell
        predicted[(ns, x, y)] = ([n for n, _ in bound], max(t for lst in cf.values() for _, _, _, t in lst[:1]))

    # ---- calibration 1: the engine's own receipts -------------------------------------------------------------
    logp = Path(a.log) if a.log else None
    if logp is None:
        snaps = sorted(Path(os.environ.get("TEMP", "")).glob("claude/*/*/scratchpad/Memoria.*.log"))
        logp = snaps[-1] if snaps else game / "Memoria.log"
    seqs = defaultdict(list)
    seq_folders = defaultdict(set)
    log_t = None
    for ln in logp.read_text(encoding="utf-8", errors="replace").splitlines():
        m = LOG_RE.match(ln)
        if m:
            dd, mo, yy, hh, mi, ss, ns, _r, x, y, part, folder = m.groups()
            t = datetime(int(yy), int(mo), int(dd), int(hh), int(mi), int(ss)).timestamp()
            log_t = t if log_t is None else min(log_t, t)
            seqs[(int(ns), int(x), int(y))].append(part)
            seq_folders[(int(ns), int(x), int(y))].add(folder)
    cal = {"log": str(logp), "blocks_in_log": len(seqs), "match": 0, "mismatch": [], "excluded_changed_after_log": [],
           "excluded_folder_gone": []}
    for key, seq in sorted(seqs.items()):
        # a receipt from a folder no longer in FolderNames (a removed scratch lab) is stale, not a miss: the
        # mtime test below cannot see files that were DELETED after the log
        gone = sorted(seq_folders[key] - set(folders))
        if gone:
            cal["excluded_folder_gone"].append(f"{key} from {gone}")
            continue
        pred = predicted.get(key, ([], 0))
        if pred[1] and log_t and pred[1] > log_t:
            cal["excluded_changed_after_log"].append(f"{key}")
            continue
        first = seq[:len(pred[0])] if pred[0] else seq
        # a block can stream in more than once: the log must be whole repetitions of the predicted list
        n = len(pred[0])
        ok = n > 0 and len(seq) % n == 0 and all(seq[i:i + n] == pred[0] for i in range(0, len(seq), n))
        if ok:
            cal["match"] += 1
        else:
            cal["mismatch"].append({"cell": f"{key}", "log": seq, "pred": pred[0]})
    # ---- calibration 2: the (11,19) 2026-07-20 receipt, replayed as a synthetic file set -----------------------
    fake = {"Sea3.ff9mesh": [(0, "x", None, 0)], "Sea4.ff9mesh": [(0, "x", None, 0)], "Sea5.ff9mesh": [(0, "x", None, 0)]}
    pk, why, _ = E.effective(1, 11, 19, fake)
    _o, b = E.bind_list(1, 11, 19, pk, fake)
    cal["case_11_19_prefix"] = {"effective": pk, "why": why, "bound": [n for n, _ in b],
                                "expect": ["Sea4"], "ok": [n for n, _ in b] == ["Sea4"]}
    # ---- the requested trace table: (land | coastal | water-only non-sea | sea) x (with | without Terrain override) --
    class _FakeTxt:
        def __init__(self, s):
            self.s = s

        def read_text(self, **_k):
            return self.s
    probe_parts = ["Object", "Terrain", "Terrain2", "Object2", "Beach1", "Beach2", "River", "Falls",
                   "Sea1", "Sea2", "Sea3", "Sea4", "Sea5", "Sea6"]
    cases = []
    for label, (cx, cy) in [("real PLAIN LAND block", (15, 13)), ("real TOWN/SWITCHABLE land block", (16, 14)), ("real COASTAL block", (8, 17)),
                            ("stock WATER-ONLY non-IsSea block", (8, 18)), ("SEA cell (IsSea)", (11, 19))]:
        for with_terrain in (False, True):
            for donor in (None, "8,17"):
                fs = {f"{p}.ff9mesh": [(0, "x", None, 0)] for p in probe_parts if p != "Terrain" or with_terrain}
                if donor:
                    fs["Donor.txt"] = [(0, "x", _FakeTxt(donor), 0)]
                pk, why, dstate = E.effective(1, cx, cy, fs)
                order, b = E.bind_list(1, cx, cy, pk, fs)
                cases.append({"case": label, "cell": f"{cx},{cy}", "IsSea": E.is_sea(1, cx, cy),
                              "terrain_override": with_terrain, "donor_txt": donor, "effective": pk, "route": why,
                              "donor_txt_state": dstate, "bound_in_order": [n for n, _ in b],
                              "walk_registered": [n for n, s in b if s != "__bare_object__"],
                              "render_only": [n for n, s in b if s == "__bare_object__"],
                              "stock_free_riders": [n for n, s in order if s != "__bare_object__" and f"{n}.ff9mesh" not in fs]})
    # `world-reclaim`'s deploy shape, no Donor.txt either way: PRE-FIX one Terrain override (defect 18, its Sea1/3/4/5
    # free-ride); FIXED = Terrain + hidden stubs for terrain.LAND_DONOR_WATER (12,10's water children)
    for label, (cx, cy), parts in [("world-reclaim pre-fix on SEA cell", (11, 19), ["Terrain"]),
                                   ("world-reclaim FIXED on SEA cell", (11, 19), ["Terrain", "Sea1", "Sea3", "Sea4", "Sea5"]),
                                   ("world-reclaim pre-fix on WATER-ONLY non-IsSea", (8, 4), ["Terrain"]),
                                   ("world-reclaim pre-fix on PLAIN LAND", (15, 13), ["Terrain"])]:
        fs = {f"{p}.ff9mesh": [(0, "x", None, 0)] for p in parts}
        pk, why, dstate = E.effective(1, cx, cy, fs)
        order, b = E.bind_list(1, cx, cy, pk, fs)
        cases.append({"case": label, "cell": f"{cx},{cy}", "IsSea": E.is_sea(1, cx, cy), "terrain_override": True,
                      "donor_txt": None, "effective": pk, "route": why, "donor_txt_state": dstate,
                      "bound_in_order": [n for n, _ in b], "walk_registered": [n for n, s in b if s != "__bare_object__"],
                      "render_only": [n for n, s in b if s == "__bare_object__"],
                      "stock_free_riders": [n for n, s in order if s != "__bare_object__" and f"{n}.ff9mesh" not in fs]})
    report["case_table"] = cases
    print("\nTRACE TABLE (every probe part offered as an override unless the label says otherwise; disc 1):")
    for c in cases:
        print(f"  {c['case']:<34} {c['cell']:<6} IsSea={int(c['IsSea'])} Terrain.ff9mesh={'Y' if c['terrain_override'] else 'n'} "
              f"Donor={c['donor_txt'] or '-':<5} -> {c['effective']:<10} bound={c['bound_in_order']} "
              f"render-only={c['render_only']} stock-free-riders={c['stock_free_riders']} donor.txt={c['donor_txt_state']}")
    report["calibration"] = cal
    ok = (not cal["mismatch"]) and cal["match"] > 0 and cal["case_11_19_prefix"]["ok"]
    report["calibration_ok"] = ok
    report["dead"] = dict(report["dead"])
    report["contract"] = dict(report["contract"])
    (OUT / "bind_oracle.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    print(f"folders: {folders}")
    print(f"override cells scanned: {len(files)}   log: {logp.name}  blocks in log: {len(seqs)}")
    print(f"CALIB engine receipts: match={cal['match']} mismatch={len(cal['mismatch'])} "
          f"excluded(changed after log)={len(cal['excluded_changed_after_log'])} "
          f"excluded(folder gone)={cal['excluded_folder_gone']}")
    for mm in cal["mismatch"][:10]:
        print("   MISMATCH", mm)
    print(f"CALIB (11,19) pre-fix replay: {cal['case_11_19_prefix']}")
    print(f"dead override files by class: {report['dead']}")
    print(f"bound-file contract audit: {report['contract']}")
    eff = Counter(c["why"].split(" (")[0].split(" ->")[0] for c in report["cells"].values())
    fr = Counter((c["effective"], tuple(c["stock_free_riders"])) for c in report["cells"].values())
    print(f"live cells by (effective prefab, STOCK children riding along un-overridden): {dict(fr.most_common(12))}")
    print(f"effective-prefab routes: {dict(eff)}")
    print(f"wrote {OUT / 'bind_oracle.json'}  calibration_ok={ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
