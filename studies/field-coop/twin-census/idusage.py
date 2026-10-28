"""READ-ONLY: per-ID op usage (first language block, like wf/finding2/census.py) of every Zidane class-7 source id and
every candidate twin id, plus a sample (field, export, line, op) per id -- the 'played in stock' evidence column."""
import os, re, json, collections
EXPORTS = r"C:\gd\FFIX\reference\test2"
MANIFEST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "reference", "field-manifest.tsv")
IDS = {
 # Zidane sources (class 7)
 106: "ZDN_JUMP", 206: "ZDN_JUMP", 179: "ZDN_JUMP1", 10446: "ZDN_JUMP_1", 10447: "ZDN_JUMP_1", 3519: "ZDN_JUMP_2", 3520: "ZDN_JUMP_2",
 10444: "ZDN_JUMP_3", 10445: "ZDN_JUMP_3", 10686: "ZDN_LADDER_1_1", 10687: "ZDN_LADDER_1_1", 10538: "ZDN_LADDER_1_2", 10539: "ZDN_LADDER_1_2",
 10684: "ZDN_LADDER_1_3", 10685: "ZDN_LADDER_1_3", 11454: "ZDN_LADDER_2_1", 11455: "ZDN_LADDER_2_1", 11452: "ZDN_LADDER_2_3", 11453: "ZDN_LADDER_2_3",
 # twins
 10280: "VIV_LADDER_1_1", 10281: "VIV_LADDER_1_1", 10276: "VIV_LADDER_1_2", 10277: "VIV_LADDER_1_2", 10278: "VIV_LADDER_1_3", 10279: "VIV_LADDER_1_3",
 10436: "VIV_LADDER_2_1", 10437: "VIV_LADDER_2_1", 10434: "VIV_LADDER_2_3", 10435: "VIV_LADDER_2_3",
 11670: "VIV_JUMP_1", 11671: "VIV_JUMP_1", 11672: "VIV_JUMP_2", 11673: "VIV_JUMP_2", 11674: "VIV_JUMP_3", 11675: "VIV_JUMP_3",
 178: "GRN_LADDER_1_1", 194: "GRN_LADDER_1_1", 157: "GRN_LADDER_1_2", 159: "GRN_LADDER_1_2", 165: "GRN_LADDER_1_3", 167: "GRN_LADDER_1_3",
 176: "GRN_LADDER_2_1", 177: "GRN_LADDER_2_1", 161: "GRN_LADDER_2_3", 163: "GRN_LADDER_2_3",
 10438: "GRN_JUMP_1", 10439: "GRN_JUMP_1", 10440: "GRN_JUMP_2", 10441: "GRN_JUMP_2", 10442: "GRN_JUMP_3", 10443: "GRN_JUMP_3",
 10744: "STN_LADDER_1_1", 10745: "STN_LADDER_1_1", 10740: "STN_LADDER_1_2", 10741: "STN_LADDER_1_2", 10742: "STN_LADDER_1_3", 10743: "STN_LADDER_1_3",
 480: "STN_LADDER_2_1", 481: "STN_LADDER_2_1", 406: "STN_LADDER_2_3", 432: "STN_LADDER_2_3",
 7241: "STN_JUMP", 7242: "STN_JUMP", 12034: "STN_JUMP_1", 12035: "STN_JUMP_1", 12030: "STN_JUMP_2", 12031: "STN_JUMP_2", 12032: "STN_JUMP_3", 12033: "STN_JUMP_3",
 12863: "FRJ_JUMP_1", 12864: "FRJ_JUMP_1", 12867: "FRJ_JUMP_2", 12868: "FRJ_JUMP_2", 12871: "FRJ_JUMP_3", 12872: "FRJ_JUMP_3",
 3935: "KUI_JUMP_1", 3937: "KUI_JUMP_1", 3939: "KUI_JUMP_2", 3942: "KUI_JUMP_2", 3943: "KUI_JUMP_3", 3945: "KUI_JUMP_3",
 3054: "EIK_JUMP_1", 3056: "EIK_JUMP_1", 3058: "EIK_JUMP_2", 3059: "EIK_JUMP_2", 3061: "EIK_JUMP_3", 3063: "EIK_JUMP_3",
 3031: "SLM_JUMP_1", 3033: "SLM_JUMP_1", 3035: "SLM_JUMP_2", 3037: "SLM_JUMP_2", 3039: "SLM_JUMP_3", 3041: "SLM_JUMP_3",
 2916: "MOG_JUMP", 2917: "MOG_JUMP", 6503: "MOG_SAVE_JUMP", 6504: "MOG_SAVE_JUMP", 4986: "MOG_GIZ_JUMP", 4987: "MOG_GIZ_JUMP",
 9888: "CNA_JUMP", 9889: "CNA_JUMP",
 12010: "MRC_JUMP_3", 12011: "MRC_JUMP_3", 12625: "MRC_LADDER_1_2", 12626: "MRC_LADDER_1_2", 12627: "MRC_LADDER_1_3", 12628: "MRC_LADDER_1_3", 12629: "MRC_LADDER_1_1", 12630: "MRC_LADDER_1_1",
 5040: "BLN_JUMP", 5041: "BLN_JUMP", 976: "BLN_SWORD_JUMP", 977: "BLN_SWORD_JUMP",
 8570: "BTX_JUMP_1", 8572: "BTX_JUMP_1", 8573: "BTX_JUMP_2", 8575: "BTX_JUMP_2", 8576: "BTX_JUMP_3", 8578: "BTX_JUMP_3", 8564: "BTX_ESCAPE_JUMP", 8566: "BTX_ESCAPE_JUMP",
}
manifest = {}
with open(MANIFEST, encoding="utf-8") as f:
    for line in f:
        p = line.rstrip("\n").split("\t")
        if len(p) >= 2 and p[1].isdigit():
            manifest[p[0]] = int(p[1])
op_pat = re.compile(r'\b(RunAnimationEx)\(\s*\d+\s*,\s*(\d+)|\b(SetJumpAnimation|RunAnimation|SetStandAnimation|SetWalkAnimation|SetRunAnimation|SetLeftAnimation|SetRightAnimation)\(\s*(\d+)')
use = collections.defaultdict(lambda: {"ops": collections.Counter(), "fields": set(), "ex": []})
for fn in sorted(os.listdir(EXPORTS)):
    if not (fn.startswith("test2_") and fn.endswith(".txt")):
        continue
    fid = manifest.get(fn)
    seen0 = 0
    with open(os.path.join(EXPORTS, fn), encoding="utf-8", errors="replace") as f:
        for ln, line in enumerate(f, 1):
            if line.startswith("#HW newentry 0"):
                seen0 += 1
                if seen0 > 1:
                    break
            for m in op_pat.finditer(line):
                op = m.group(1) or m.group(3)
                aid = int(m.group(2) or m.group(4))
                if aid in IDS:
                    u = use[aid]
                    u["ops"][op] += 1
                    u["fields"].add(fid)
                    if len(u["ex"]) < 3:
                        u["ex"].append("%s:%d f%s %s" % (fn, ln, fid, op))
out = {}
for aid in sorted(IDS, key=lambda i: (IDS[i], i)):
    u = use.get(aid)
    out[aid] = {"name": IDS[aid], "ops": dict(u["ops"]) if u else {}, "nfields": len(u["fields"]) if u else 0,
                "fields": sorted(x for x in u["fields"] if x is not None)[:12] if u else [], "ex": u["ex"] if u else []}
    print("%-16s %6d ops=%-45s nf=%-3d %s" % (IDS[aid], aid, out[aid]["ops"], out[aid]["nfields"], out[aid]["ex"][:1]))
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "idusage.json"), "w"), indent=1)
