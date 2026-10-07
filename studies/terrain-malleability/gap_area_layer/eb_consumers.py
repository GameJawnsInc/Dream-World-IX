"""WORLD .eb AREA CONSUMERS -- every GET of sysvar 192 (area) or 207 (zone) in the 13 world dispatchers
(EventDB 9000-9012), stock (p0data) and LIVE (the stacked mod-folder overrides), with what each branch does.

READ-ONLY: dispatchers come from ff9mapkit.world.entrance.load_all_dispatchers (UnityPy over the user's install) and
from the live override files under <game>/<FolderNames>/StreamingAssets/.../eventbinary/world/us/ (opened for read).

For each instruction whose expression carries B_SYSVAR[192] or B_SYSVAR[207] it records the pretty expression and
the CONTROL SHAPE it feeds:
  * switch      -- the next instruction is a switch: every arm (selector value -> a short op summary of its block)
  * guard       -- the next instruction is JMP_IFNOT/JMP_IF: the guarded block's op summary
  * value       -- the read is assigned/used inline (summary of the statement only)

CALIBRATION (exit 1 on failure), both BEFORE any sysvar-192 count is trusted:
  * WORLD00 (stock, us) must carry exactly one 25-arm switch on B_SYSVAR[207] whose arms are all `X = const(N)`
    writes feeding a SetRandomBattleFrequency -- the ENCRATE ladder (world/encounter.py freq_writes agrees).
  * my own instruction walk must count exactly 18 RunWorldCode(26, imm) writes over all 13 stock dispatchers (us)
    and equal world/encounter.py rate_writes' count -- proves the walk covers every entry/function.

Rerun:  py studies/terrain-malleability/gap_area_layer/eb_consumers.py   -> out/eb_consumers.json
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
from ff9mapkit.world import entrance as EN          # noqa: E402
from ff9mapkit.world import encounter as ENC        # noqa: E402
from ff9mapkit.eb.model import EbScript             # noqa: E402
from ff9mapkit.eb import disasm as D                # noqa: E402
from ff9mapkit import config                        # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
B_SYSVAR = 0x7A
WATCH = (192, 207)
SUB = "StreamingAssets/assets/resources/commonasset/eventengine/eventbinary/world/us"
FOLDERS = ["FF9CustomMap", "FF9CustomMap-world", "MoguriMain", "MoguriVideo", "FF9CustomMap-schema", "FF9CustomMap-msgs"]


def summarize(data, ins_list, start, end, limit=14):
    """Short op summary of instructions in [start, end): names + key immediates."""
    out = []
    for i in ins_list:
        if i.off < start or i.off >= end:
            continue
        nm = i.name
        if i.op == 0x05:
            txt, _ = D.pretty_expr(data, i.off + 1)
            out.append("EXPR" + txt[:70])
        elif i.op == 0xC4:
            out.append(f"RunWorldCode({i.imm(0)},{i.imm(1) if len(i.args) > 1 else ''})")
        elif i.op in (0x2B, 0x2A, 0xB6):
            out.append(f"{nm}({','.join(str(a) for a in i.args)[:30]})")
        else:
            imms = [str(a) for a, e in zip(i.args, i.arg_is_expr) if not e][:3]
            out.append(f"{nm}({','.join(imms)})")
        if len(out) >= limit:
            out.append("...")
            break
    return out


def scan(data, name):
    s = EbScript(data)
    hits, rwc26 = [], 0
    for e in s.entries:
        for f in e.funcs:
            ins = list(D.iter_code(s.data, f.abs_start, f.abs_end))
            for k, i in enumerate(ins):
                if i.op == 0xC4 and i.imm(0) == 26 and len(i.arg_is_expr) >= 2 and not i.arg_is_expr[1]:
                    rwc26 += 1
                try:
                    toks = D.instr_expr_tokens(s.data, i)
                except Exception:                       # noqa: BLE001
                    continue
                vars_ = sorted({v for t in toks if t for (o, v) in t if o == B_SYSVAR and v in WATCH})
                if not vars_:
                    continue
                txt, _ = D.pretty_expr(s.data, i.off + 1) if i.op == 0x05 else (str(i), 0)
                rec = {"disp": name, "entry": e.index, "tag": f.tag, "off": i.off, "op": i.name, "sysvars": vars_,
                       "expr": txt[:200]}
                nxt = ins[k + 1] if k + 1 < len(ins) else None
                if nxt is not None and nxt.is_switch:
                    si = D.decode_switch(nxt)
                    arms = []
                    tgts = sorted({ed.target for ed in si.edges})
                    for ed in si.edges:
                        later = [t for t in tgts if t > ed.target]
                        end = later[0] if later else f.abs_end
                        arms.append({"value": ed.value, "default": ed.is_default,
                                     "ops": summarize(s.data, ins, ed.target, end, limit=6)})
                    rec["shape"] = "switch"
                    rec["arms"] = arms
                    rec["n_arms"] = sum(1 for a in arms if not a["default"])
                elif nxt is not None and nxt.op in (0x02, 0x03):
                    tgt = D.jump_target(nxt)
                    rec["shape"] = "guard"
                    rec["guarded_ops"] = summarize(s.data, ins, nxt.end, tgt if tgt else nxt.end, limit=16)
                else:
                    rec["shape"] = "value"
                hits.append(rec)
    return hits, rwc26


def main():
    OUT.mkdir(exist_ok=True)
    alld = EN.load_all_dispatchers()
    stock = {n: v["us"] for n, v in alld.items() if "us" in v}
    res = {"stock": {}, "live": {}, "live_sources": {}}
    total26 = 0
    kit26 = 0
    for n in sorted(stock):
        hits, c26 = scan(stock[n], n)
        res["stock"][n] = hits
        total26 += c26
        kit26 += sum(1 for _ in ENC.rate_writes(stock[n]))
    # live: first folder in FolderNames order that has the file wins
    game = config.find_game_path(None)
    names = sorted(set(stock) | {"evt_world_world13"})
    for n in names:
        for fo in FOLDERS:
            p = Path(game) / fo / SUB / (n.upper() + ".eb.bytes")
            if p.is_file():
                res["live_sources"][n] = str(p)
                res["live"][n], _ = scan(p.read_bytes(), n)
                break
    # ---------------- calibration ----------------
    w0 = res["stock"].get("evt_world_world00", [])
    ladders = [h for h in w0 if h["sysvars"] == [207] and h.get("shape") == "switch" and h.get("n_arms") == 25]
    lad_ok = len(ladders) == 1 and all(any("B_LET" in o or "=" in o for o in a["ops"][:1]) for a in ladders[0]["arms"]
                                       if not a["default"])
    kit_freq = [w for w in ENC.freq_writes(stock["evt_world_world00"]) if w["kind"] == "zone"]
    calib = {"world00_207_ladders_25arm": len(ladders), "ladder_arms_are_writes": lad_ok,
             "kit_freq_writes_world00_zone_arms": len(kit_freq), "rwc26_my_walk": total26, "rwc26_kit": kit26}
    ok = len(ladders) == 1 and lad_ok and len(kit_freq) == 25 and total26 == 18 and kit26 == 18
    # cross-check: the one sysvar-192 switch's arm set vs the engine's EMinigame.BeachData (parsed from source)
    import engine_consumers as EC
    beach = EC.parse_tables()["BeachData"]
    sw192 = [h for hs in res["stock"].values() for h in hs if 192 in h["sysvars"] and h["shape"] == "switch"]
    arms192 = sorted(a["value"] for h in sw192 for a in h["arms"] if not a["default"])
    bits = sorted({int(o.split("Bit[")[1].split("]")[0]) for h in sw192 for a in h["arms"] if not a["default"]
                   for o in a["ops"][:1] if "Global.Bit[" in o})
    calib["sysvar192_switches_stock"] = len(sw192)
    calib["sysvar192_arms_equal_BeachData"] = arms192 == sorted(beach)
    calib["sysvar192_arm_bits"] = [min(bits), max(bits), len(bits)] if bits else None
    res["calibration"] = calib
    res["calibration_ok"] = ok
    # ---------------- summary ----------------
    summ = {}
    for side in ("stock", "live"):
        c = Counter()
        for n, hits in res[side].items():
            for h in hits:
                for v in h["sysvars"]:
                    c[(n, v, h["shape"])] += 1
        summ[side] = {f"{n}|{v}|{sh}": k for (n, v, sh), k in sorted(c.items())}
    res["summary"] = summ
    (OUT / "eb_consumers.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("CALIBRATION", json.dumps(calib), "->", "PASS" if ok else "FAIL")
    for side in ("stock", "live"):
        print(f"\n=== {side}")
        for k, v in res["summary"][side].items():
            print("  ", k, v)
    print("\n=== stock sysvar-192 hits (detail)")
    for n, hits in res["stock"].items():
        for h in hits:
            if 192 in h["sysvars"]:
                print(f"  {n} e{h['entry']} t{h['tag']} @{h['off']} {h['shape']} {h['expr'][:110]}")
                if h["shape"] == "switch":
                    for a in h["arms"]:
                        print(f"      {'default' if a['default'] else a['value']}: {a['ops'][:5]}")
                elif h["shape"] == "guard":
                    print("      guarded:", h["guarded_ops"][:12])
    print("\n=== stock sysvar-207 non-ladder hits")
    for n, hits in res["stock"].items():
        for h in hits:
            if 207 in h["sysvars"] and not (h["shape"] == "switch" and h.get("n_arms") == 25):
                print(f"  {n} e{h['entry']} t{h['tag']} @{h['off']} {h['shape']} {h['expr'][:110]}")
                if h["shape"] == "guard":
                    print("      guarded:", h["guarded_ops"][:12])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
