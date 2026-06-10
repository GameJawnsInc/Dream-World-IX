"""Mine the census + field manifest into the UNDERSTAND layer: a field-granular ScenarioCounter->beat
dictionary, area-labeled story-flag clusters, and a chest-band identity probe. Deterministic join only --
no LLM guesswork: every row traces to a census writer field joined to its manifest room name.

Inputs:  research/flag_census.json (the 676-field census) + reference/field-manifest.tsv (field_id -> room).
Outputs: research/understand_layer.json (machine form) + a printed digest.
Run:     py research/gen_understand_layer.py
"""
import json
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

census = json.load(open(os.path.join(HERE, "flag_census.json"), encoding="utf-8"))
PF = census["per_field"]
SCN = census["scenario_counter_writes"]
BITS = census["bit_flags"]

# --- field_id -> manifest room name ("Alexandria/Shop"). One row per HW-index; field ids can repeat
#     (multiple index files -> same field), so keep the first, most-canonical name seen. ---
ROOM = {}
# the manifest carries cp1252 smart quotes (Chocobo's) -> read tolerantly
for ln in open(os.path.join(REPO, "reference", "field-manifest.tsv"), encoding="cp1252"):
    p = ln.rstrip("\n").split("\t")
    if len(p) >= 3 and p[1].strip().isdigit():
        ROOM.setdefault(int(p[1]), p[2].strip())

# Manifest area abbreviations -> full registry names (the manifest truncates for its own UI).
AREA_NORM = {
    "L. Castle": "Lindblum Castle", "A. Castle": "Alexandria Castle", "I. Castle": "Ipsen's Castle",
    "S. Gate": "South Gate", "N. Gate": "North Gate", "Mdn. Sari": "Madain Sari",
    "Mountain Path": "Conde Petie Mt. Path", "Gulug": "Mount Gulug", "Hilda Garde 3": "Hilda Garde",
    "Hilda Garde 1": "Hilda Garde", "Hilda Garde 2": "Hilda Garde", "last": "Crystal World (ending)",
    "Gizamaluke": "Gizamaluke's Grotto", "Marsh": "Qu's Marsh", "Palace": "Desert Palace",
    "Pand.": "Pandemonium",
}

# FBG zone code (n##_ZONE) -> friendly story area; mirrors gen_scenario_table.ZONE.
ZONE = {
    "tshp": "Prima Vista", "alxt": "Alexandria", "alxc": "Alexandria Castle", "bshp": "Cargo Ship",
    "evft": "Evil Forest", "iccv": "Ice Cavern", "vgdl": "Dali", "udft": "Dali (underground)",
    "airp": "Cargo Ship", "cshp": "Cargo Ship", "ldbm": "Lindblum", "lglo": "Lindblum",
    "gzml": "Gizamaluke's Grotto", "brmc": "Burmecia", "kuin": "Qu's Marsh", "qunh": "Qu's Marsh",
    "stgt": "South Gate", "gtre": "Cleyra", "clir": "Cleyra", "trno": "Treno", "ntgt": "North Gate",
    "pncl": "Pinnacle Rocks", "cdpt": "Conde Petie", "cpmp": "Conde Petie Mt. Path", "iftr": "Iifa Tree",
    "ifug": "Iifa Tree", "mdsr": "Madain Sari", "sdpl": "Desert Palace", "uuvl": "Oeilvert",
    "tera": "Terra", "pdmn": "Pandemonium", "ipsn": "Ipsen's Castle", "cysw": "Crystal World",
    "brnf": "Blue Narciss", "blnr": "Hilda Garde", "hlg1": "Hilda Garde", "hlg2": "Hilda Garde",
    "hlg3": "Hilda Garde", "invb": "Invincible", "grgr": "Gargan Roo", "bmvl": "Black Mage Village",
    "brbl": "Bran Bal", "rdrs": "Red Rose", "fnrl": "Madain Sari", "fslr": "Iifa Tree",
    "glgv": "Outer Continent", "emsh": "Earth Shrine",
}


def zone_of(fid):
    fb = (PF.get(str(fid), {}).get("fbg") or "").split("_")
    z = fb[2] if len(fb) > 2 else "?"
    return ZONE.get(z, z)


def area_of(fid):
    """Best human area label for a field: the manifest's top-level area (normalized), else the zone."""
    rm = ROOM.get(fid)
    if rm:
        a = rm.split("/")[0]
        return AREA_NORM.get(a, a)
    return zone_of(fid)


# ================= 1) field-granular ScenarioCounter dictionary =================
# value -> [(field_id, room, zone-area)], for every absolute set. Lowest field id first (the setter).
scenario_rows = []
for v in sorted(int(x) for x in SCN):
    fids = SCN[str(v)]
    setter = fids[0]
    scenario_rows.append({
        "value": v, "field": setter, "room": ROOM.get(setter, "?"),
        "area": area_of(setter), "zone": zone_of(setter), "all_fields": fids,
    })

# Two ANCHOR views of the same data (>=1000), keyed by AREA:
#   collapse_anchors  -- collapse consecutive same-area runs only (keeps brief beats: Oeilvert, Desert
#                        Palace). Denser, truest to the data.
#   island_anchors    -- additionally drop single-anchor islands A-B-A (cutscene interleave). Sparser.
vals = [r for r in scenario_rows if r["value"] >= 1000]
collapse_anchors, last = [], None
for r in vals:
    if r["area"] != last:
        collapse_anchors.append({"value": r["value"], "area": r["area"], "field": r["field"],
                                 "room": r["room"]})
        last = r["area"]

runs, last = [], None
for r in vals:
    if r["area"] != last:
        runs.append(r); last = r["area"]
changed = True
while changed:
    changed = False
    out, i = [], 0
    while i < len(runs):
        if 0 < i < len(runs) - 1 and runs[i - 1]["area"] == runs[i + 1]["area"] \
                and runs[i]["area"] != runs[i - 1]["area"]:
            i += 1; changed = True
        else:
            out.append(runs[i]); i += 1
    merged, last = [], None
    for r in out:
        if r["area"] != last:
            merged.append(r); last = r["area"]
    runs = merged
anchors = [{"value": r["value"], "area": r["area"], "field": r["field"], "room": r["room"]} for r in runs]

# ================= 2) area-labeled story-flag clusters =================
# Group every census bit-flag (skip the engine/reserved bands) into contiguous byte clusters, and label
# each by the dominant area of the fields that WRITE it. Reserved bands are listed but not "named story".
RESERVED = [(184, 191, "engine handshake (byte 23)"), (736, 823, "worldmap/Navi unlocks"),
            (8376, 8511, "treasure-chest opened block"), (16320, 16335, "choice scratch")]


def reserved_label(bit):
    for lo, hi, nm in RESERVED:
        if lo <= bit <= hi:
            return nm
    return None


# walk sorted bits, break a cluster when the byte gap to the next bit exceeds GAP bytes
GAP = 4
allbits = sorted(int(b) for b in BITS)
clusters = []
cur = []
for b in allbits:
    if reserved_label(b):
        continue
    if cur and (b >> 3) - (cur[-1] >> 3) > GAP:
        clusters.append(cur); cur = []
    cur.append(b)
if cur:
    clusters.append(cur)

cluster_rows = []
for cl in clusters:
    writers = set()
    for b in cl:
        writers |= set(BITS[str(b)]["writers"])
    area_hits = defaultdict(int)
    for fid in writers:
        area_hits[area_of(fid)] += 1
    top = sorted(area_hits.items(), key=lambda kv: -kv[1])[:3]
    cluster_rows.append({
        "bit_lo": cl[0], "bit_hi": cl[-1], "byte_lo": cl[0] >> 3, "byte_hi": cl[-1] >> 3,
        "n_bits": len(cl), "n_fields": len(writers),
        "areas": [f"{a} ({n})" for a, n in top],
    })

# ================= 3) chest-band identity probe =================
# Is each chest bit a per-chest unique flag (few writers) or a shared/computed field (many writers)?
chest_probe = []
for b in range(8376, 8512):
    e = BITS.get(str(b))
    if not e:
        continue
    chest_probe.append((b, e["n_write"]))
nw = [n for _, n in chest_probe]
chest_finding = {
    "bits_present": len(chest_probe),
    "writers_min": min(nw) if nw else 0, "writers_max": max(nw) if nw else 0,
    "writers_mean": round(sum(nw) / len(nw), 1) if nw else 0,
    "all48_writers_bits": sum(1 for _, n in chest_probe if n >= 40),
    "chest_field_rooms": {str(f): ROOM.get(f, "?") for f in sorted(set(
        w for b in range(8376, 8512) for w in (BITS.get(str(b), {}).get("writers") or [])))},
}

# ================= write + digest =================
out = {
    "scenario_dictionary": scenario_rows,
    "scenario_anchors_collapse": collapse_anchors,
    "scenario_anchors_island": anchors,
    "flag_clusters": cluster_rows,
    "chest_band_probe": chest_finding,
}
with open(os.path.join(HERE, "understand_layer.json"), "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=1)

# --- compact human candidate (the single small file the verification workflow reads) ---
cur = {
    1000: "Prima Vista", 1900: "Cargo Ship", 2300: "Evil Forest", 2500: "Ice Cavern", 2530: "Dali",
    2700: "Dali (underground)", 2800: "Cargo Ship", 3000: "Lindblum", 3710: "Gizamaluke's Grotto",
    3750: "South Gate", 4445: "Treno", 4500: "Gargan Roo", 4600: "Alexandria Castle", 4650: "Cleyra",
    4990: "Red Rose", 5030: "Alexandria Castle", 5510: "Pinnacle Rocks", 5660: "Lindblum",
    5900: "Iifa Tree", 6100: "Conde Petie", 6300: "Conde Petie Mt. Path", 6600: "Madain Sari",
    6900: "Iifa Tree", 7010: "Alexandria", 7200: "Alexandria Castle", 7550: "Treno", 8000: "Alexandria",
    8400: "Alexandria Castle", 9000: "Lindblum", 9400: "Hilda Garde", 9700: "Oeilvert",
    9800: "Desert Palace", 9910: "Hilda Garde", 9990: "Outer Continent", 10000: "Lindblum",
    10400: "Alexandria Castle", 10500: "Ipsen's Castle", 10600: "Hilda Garde", 10670: "Earth Shrine",
    10830: "Terra", 10900: "Bran Bal", 11100: "Invincible", 11610: "Crystal World",
}
ml = ["# UNDERSTAND-layer candidate (deterministic census x manifest join). Verify against FF9 knowledge.",
      "",
      "## A) Candidate ScenarioCounter -> area anchors (collapse view, field-grounded)",
      "Each row: VALUE  AREA  (setter field + manifest room). These are the area-entry transitions.",
      "Question to verify: is each (value, area) a sensible monotonic FF9 story beat? Flag mislabels,",
      "wrong areas, and cutscene-flicker islands that should be dropped vs real brief beats to keep.", ""]
for r in collapse_anchors:
    ml.append(f"  {r['value']:6d}  {r['area']:<24}  (field {r['field']}: {r['room']})")
ml += ["", "## B) Currently SHIPPED table (flags.py SCENARIO_MILESTONES, 43 anchors) -- for diff",
       "In-game validated points: 7200 -> Alexandria Castle (confirmed by playtest 2026-06-10).", ""]
for v in sorted(cur):
    ml.append(f"  {v:6d}  {cur[v]}")
ml += ["", "## C) Story-flag clusters (non-reserved bit bands, dominant writer areas)",
       "Question to verify: a defensible NAME + area + meaning for each? (skip the giant 7171-7775 mixed band)", ""]
for c in cluster_rows:
    ml.append(f"  bits {c['bit_lo']:5d}-{c['bit_hi']:<5d} (byte {c['byte_lo']}-{c['byte_hi']}) "
              f"{c['n_bits']} bits / {c['n_fields']} fields :: {', '.join(c['areas'])}")
ml += ["", "## D) Chest band 8376-8511: every bit has exactly 48 writers -> shared/computed-index,",
       "NOT per-chest-static. Per-chest identity is NOT recoverable from the static census (finding)."]
with open(os.path.join(HERE, "understand_candidate.md"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(ml))

print(f"=== ScenarioCounter dictionary: {len(scenario_rows)} absolute values | "
      f"{len(collapse_anchors)} collapse-anchors | {len(anchors)} island-cleaned anchors ===")
for r in collapse_anchors:
    print(f"  {r['value']:6d}  {r['area']:<22}  (field {r['field']}: {r['room']})")
print(f"\n=== disc-3 window 9000-12000 (raw per-value, to judge cleaning) ===")
for r in scenario_rows:
    if 9000 <= r["value"] <= 12000:
        print(f"  {r['value']:6d}  {r['area']:<22}  field {r['field']}: {r['room']}  "
              f"{'(+'+str(len(r['all_fields'])-1)+' more)' if len(r['all_fields'])>1 else ''}")
print(f"\n=== Story-flag clusters (non-reserved): {len(cluster_rows)} ===")
for c in cluster_rows:
    print(f"  bits {c['bit_lo']:5d}-{c['bit_hi']:<5d} (byte {c['byte_lo']:4d}-{c['byte_hi']:<4d}) "
          f"{c['n_bits']:3d} bits / {c['n_fields']:3d} fields  ::  {', '.join(c['areas'])}")
print(f"\n=== Chest band 8376-8511 probe ===")
print(f"  bits present: {chest_finding['bits_present']}  writers/bit min={chest_finding['writers_min']} "
      f"max={chest_finding['writers_max']} mean={chest_finding['writers_mean']}  "
      f"(bits written by >=40 fields: {chest_finding['all48_writers_bits']})")
print(f"  => {'SHARED/computed-index (NOT per-chest-static)' if chest_finding['writers_mean'] > 5 else 'per-chest-unique'}")
print(f"\n  wrote {os.path.join(HERE, 'understand_layer.json')}")
