"""READ-ONLY generator of the s157 twin table (C# rows + Python rows) from this folder's variants.json / idusage.json.
Policy: (1) same-suffix twin when on disc AND stock plays it; (2) a JUMP whose twin is unplayed/absent -> the rig's
stock-played PLAIN jump (JUMP / JUMP_1 / JUMP_2 / JUMP_3) nearest in frame count (tie -> the lower suffix);
(3) else no row (s140's idle alias). Ladders: (1) or no row. Twin id = the id stock names most (tie -> the lower id)."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
V = json.load(open(os.path.join(HERE, "variants.json")))
U = {int(k): v for k, v in json.load(open(os.path.join(HERE, "idusage.json"))).items()}
RIGS = [(1, "Vivi", "VIV"), (2, "Garnet", "GRN"), (3, "Steiner", "STN"), (4, "Freya", "FRJ"), (5, "Quina", "KUI"),
        (6, "Eiko", "EIK"), (7, "Amarant", "SLM"), (8, "moogle", "MOG"), (9, "Cinna", "CNA"), (10, "Marcus", "MRC"),
        (11, "Blank", "BLN"), (12, "Beatrix", "BTX")]
SRC = [("LADDER_1_1", 10687, 10686), ("LADDER_1_2", 10539, 10538), ("LADDER_1_3", 10685, 10684),
       ("LADDER_2_1", 11455, 11454), ("LADDER_2_3", 11453, 11452),
       ("JUMP", 206, 106), ("JUMP_1", 10446, 10447), ("JUMP_2", 3519, 3520), ("JUMP_3", 10444, 10445)]
PLAIN = ("JUMP", "JUMP_1", "JUMP_2", "JUMP_3")
zfr = {r["suffix"]: r["frames"] for r in V["Zidane"]}
def ops(i): return sum(U.get(i, {}).get("ops", {}).values())
def fields(i): return U.get(i, {}).get("fields", [])
def nf(i): return U.get(i, {}).get("nfields", 0)
rows = []
for rig, who, tok in RIGS:
    have = {r["suffix"]: r for r in V[who]}
    def played(suf):
        r = have.get(suf)
        return r is not None and r["engine_on_disc"] and any(ops(i) for i in r["ids"])
    def best_id(suf):
        ids = have[suf]["ids"]
        return sorted(ids, key=lambda i: (-ops(i), i))[0]
    for suf, a, b in SRC:
        how = None
        if played(suf):
            tsuf, how = suf, "same"
        elif suf in PLAIN:
            cands = [s for s in PLAIN if played(s)]
            if cands:
                tsuf = sorted(cands, key=lambda s: (abs(have[s]["frames"] - zfr[suf]), PLAIN.index(s)))[0]
                how = "nearest"
        if how is None:
            continue
        t = best_id(tsuf)
        both = sorted(set(have[tsuf]["ids"]))
        ev = "; ".join(f"{i}: {U[i]['ops']} in {nf(i)} fields {fields(i)[:6]}" for i in both if ops(i))
        rows.append(dict(rig=rig, who=who, src=a, src2=b, suf=suf, twin=t, tsuf=tsuf, how=how,
                         fs=zfr[suf], ft=have[tsuf]["frames"], ev=ev, tok=tok))
print(len(rows), "rows")
cs = []
for r in rows:
    cs.append("            { %2d, %5d, %5d, %5d },   // %-8s ZDN_%-10s -> %s_%-10s %2d -> %2d  %s" % (
        r["rig"], r["src"], r["src2"], r["twin"], r["who"], r["suf"], r["tok"], r["tsuf"], r["fs"], r["ft"],
        "same suffix" if r["how"] == "same" else "nearest played jump"))
open(os.path.join(HERE, "twin_rows_cs.txt"), "w").write("\n".join(cs) + "\n")
py = []
for r in rows:
    py.append("    (%d, %d, %d, %d),   # %s ZDN_%s -> %s_%s, %d -> %d (%s)" % (r["rig"], r["src"], r["src2"], r["twin"], r["who"],
              r["suf"], r["tok"], r["tsuf"], r["fs"], r["ft"], r["how"]))
open(os.path.join(HERE, "twin_rows_py.txt"), "w").write("\n".join(py) + "\n")
md = ["| rig | Zidane source (ids) | twin id + name | frames src -> twin | rule | stock plays the twin (op counts; fields) |", "|---|---|---|---|---|---|"]
for r in rows:
    md.append(f"| {r['rig']} {r['who']} | ZDN_{r['suf']} ({r['src']}/{r['src2']}) | {r['twin']} {r['tok']}_{r['tsuf']} | {r['fs']} -> {r['ft']} | {r['how']} | {r['ev']} |")
open(os.path.join(HERE, "twin_rows.md"), "w").write("\n".join(md) + "\n")
json.dump(rows, open(os.path.join(HERE, "twin_rows.json"), "w"), indent=1)
print("\n".join(cs))
