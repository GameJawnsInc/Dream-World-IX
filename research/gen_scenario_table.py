"""Generate the ScenarioCounter -> area progression table from the census, for BOTH the kit's
flags.py (Python) and the F6 debug menu (C#). Reproducible + census-grounded so the two stay in sync.

The table maps a ScenarioCounter value to the story AREA the game is in around then (the area of the
field that sets that value). Cleaning: drop the sub-1000 artifacts (a few disc-3 cutscene fields write
tiny values), map raw FBG zone codes to friendly names, and remove single-anchor "islands" (a brief
area sandwiched between two runs of another -- cutscene interleave like Iifa<->Blue Narciss).

Run: py research/gen_scenario_table.py   (prints the Python list + the C# arrays to paste).
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
r = json.load(open(os.path.join(HERE, "flag_census.json"), encoding="utf-8"))
pf, scn = r["per_field"], r["scenario_counter_writes"]

# FBG zone code (the n##_ZONE segment) -> friendly story-area name.
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


def area(fid):
    fb = pf.get(str(fid), {}).get("fbg", "").split("_")
    z = fb[2] if len(fb) > 2 else "?"
    return ZONE.get(z, z)


# 1) collapse to (threshold, area) runs, skipping the sub-1000 cutscene artifacts
vals = [v for v in sorted(int(x) for x in scn) if v >= 1000]
collapsed, last = [], None
for v in vals:
    a = area(scn[str(v)][0])
    if a != last:
        collapsed.append([v, a]); last = a

# 2) remove single-anchor islands (A B A -> A), then re-collapse adjacent duplicates; iterate to a fixpoint
changed = True
while changed:
    changed = False
    out = []
    i = 0
    while i < len(collapsed):
        if 0 < i < len(collapsed) - 1 and collapsed[i - 1][1] == collapsed[i + 1][1] \
                and collapsed[i][1] != collapsed[i - 1][1]:
            i += 1                                  # drop the island anchor
            changed = True
        else:
            out.append(collapsed[i]); i += 1
    merged, last = [], None
    for v, a in out:
        if a != last:
            merged.append([v, a]); last = a
    collapsed = merged

print(f"# {len(collapsed)} anchors (from {len(vals)} census values >= 1000)\n")
print("# ---- Python (flags.py SCENARIO_MILESTONES) ----")
print("SCENARIO_MILESTONES = {")
for v, a in collapsed:
    print(f'    {v}: "{a}",')
print("}\n")
print("# ---- C# (Ff9mkDebugMenu MsVal / MsName) ----")
print("    private static readonly Int32[] MsVal = { " + ", ".join(str(v) for v, _ in collapsed) + " };")
names = ", ".join('"' + a + '"' for _, a in collapsed)
print("    private static readonly String[] MsName = { " + names + " };")
# sanity: where does 7200 land?
beat = "(pre)"
for v, a in collapsed:
    if 7200 >= v:
        beat = a
print(f"\n# sanity: ScenarioCounter 7200 -> {beat}")
