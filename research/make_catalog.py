"""Generate research/flag_catalog.toml — the named-flag REGISTRY SEED recommended by STORY_FLAGS.md §5(2).

Combines three tiers:
  (a) engine-grounded named vars + reserved regions + scenario milestones (curated, cited)
  (b) empirical region clusters auto-derived from the census (contiguous byte runs + sample writer fields)
  + the recommended provably-safe allocation bands.

This is a SEED for a future kit flag-registry, not a finished dictionary. Reproducible:
  py research/make_catalog.py   (re-derives the empirical clusters from flag_census.json)
"""
import json, os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
r = json.load(open(os.path.join(HERE, "flag_census.json"), encoding="utf-8"))
bf, pf, scn = r["bit_flags"], r["per_field"], r["scenario_counter_writes"]

# ---- (a) curated engine-grounded entries (name, location, type, meaning, tier, source) ----
NAMED = [
    ("ScenarioCounter", "bytes 0-1", "Global UInt16 @0 (0xDC)", "Master story-progress value (1..12000).", "a", "EventState.cs:16-24; EBin.cs:34"),
    ("FieldEntrance", "bytes 2-3", "Global Int16 @2 (0x2D8)", "Last entrance / arrival map index; read by all fields.", "a", "EventState.cs:26-34; EBin.cs:35"),
    ("TranceGaugeFlag", "byte 16", "Byte", "Trance gauge enable (0/1).", "a", "battle.cs:38; StatusUI.cs:291"),
    ("GarnetSummonAvailable", "bytes 17-18", "Byte", "Garnet summon depression/reserve state.", "a", "battle.cs:39-40"),
    ("ChocographFound", "byte 187+i", "Byte bitfield", "Chocograph treasure 'found' bits (UI ORs bytes <<i*8).", "a", "ChocographUI.cs:250-251"),
    ("ChocographOpened", "byte 184+i", "Byte bitfield", "Chocograph treasure 'opened' bits. NOTE: byte 184, NOT bit 184.", "a", "ChocographUI.cs:250-251"),
    ("ChocoDigLevel", "byte 191", "Byte", "Choco's dig ability level (set to 5 at milestones).", "a", "ChocographUI.cs:245; EMinigame.cs:454"),
    ("HuntFestivalScore", "bytes 314/316", "UInt16 (+=/-=)", "Festival of the Hunt running tally (n11 Lindblum).", "b", "census"),
]

# ---- engine/transient regions a mod MUST NOT allocate into ----
RESERVED = [
    ("_RESERVED_std_field_init", "bytes 8-14", "Per-field standard variable block; rewritten in every Main_Init.", "b", "census (676 fields)"),
    ("_RESERVED_field_menu_guard", "bit 184 (byte 23.0)", "Engine handshake: 'in-field menu/transition in progress'. Re-checked+cleared every Main_Init; forces FieldEntrance=10000 if set on load.", "a", "disassembly fields 50/100/300; engine grep=0"),
    ("_RESERVED_boot_scratch", "bit 191 (byte 23.7)", "Companion scratch bit, zeroed on every boot, never read.", "a", "disassembly"),
    ("_RESERVED_worldmap_unlocks", "bytes 92-102", "Worldmap/Navi cursor + location-unlock/first-visit; consumed by engine C# (mostly write-only on the field side).", "a", "ff9.cs:2259-2333; census"),
    ("_RESERVED_TH_double", "bytes 182-186", "Treasure-Hunter 'double' scoring region (world-map Choco chests, 2 pts/bit).", "a", "EventState.cs:69-70"),
    ("_RESERVED_TH_standard", "bytes 896-960", "Treasure-Hunter 'standard' scoring region (opened chests/searched icons, 1 pt/bit). Overlaps the dense story-flag heap.", "a", "EventState.cs:65-66"),
    ("_RESERVED_TH_extra", "bytes 966-975", "Treasure-Hunter 'extra' scoring region (1 pt/bit).", "a", "EventState.cs:67-68"),
    ("_RESERVED_chest_opened", "bits 8376-8511 (bytes 1047-1063)", "Treasure-chest field-script registry: a byte-identical 130-entry dispatch block in ~48 chest fields. The stock engine does NOT read it (the TH rank is scored from the SEPARATE _RESERVED_TH_* regions above). THE band the campaign allocator must clear.", "b", "census (byte-identical block in ~48 chest fields; NOT GetTreasureHunterPoints)"),
    ("_LEGACY_ability_usage", "bytes 1100-1291", "Legacy ability-usage counters (now in gAbilityUsage dict; bytes may be cleared).", "a", "JsonParser.cs:539"),
    ("_RESERVED_choice_scratch", "byte 2040 (bits 16320+)", "Choice-visibility mask scratch (kit MASK_SCRATCH_IDX); engine-reserved.", "a", "region.py:57"),
]

# ---- scenario milestones (value, beat, tier, source) ----
MILESTONES = [
    (1000, "Game start — Prima Vista / Cargo Room (field 50)", "b", "census + manifest"),
    (1150, "Alexandria / Shop (field 104)", "b", "census"),
    (1900, "Burmecia-area gate (field 206 choice)", "a", "EMinigame.cs:534; ETb.cs:424"),
    (4980, "Cleyra Cathedral (field 1109)", "a", "EMinigame.cs:246"),
    (6840, "Madain Sari Secret Room — dialog state (field 1608)", "a", "Dialog.cs:1613"),
    (9520, "Kuja sends team to Oeilvert (party>=4 enforced)", "a", "PartySettingUI.cs:557"),
    (9860, "IsEikoAbducted window START — Desert Palace (engine: 9860 <= SC < 9990)", "a", "EventState.cs:36"),
    (10300, "'Late game' threshold (field 2456, >=10300)", "a", "EMinigame.cs:114"),
    (11090, "Near-endgame threshold (field 455, <11090)", "a", "EMinigame.cs:233"),
    (12000, "Terminal value — Ending fields", "a", "census; EventState.cs"),
]

# ---- (b) empirical region clusters auto-derived from the census ----
bybyte = defaultdict(set)
for b, d in bf.items():
    bybyte[d["byte"]].add(int(b))
allbytes = sorted(bybyte)
runs = []
start = prev = allbytes[0]
for by in allbytes[1:]:
    if by == prev + 1:
        prev = by
    else:
        runs.append((start, prev)); start = prev = by
runs.append((start, prev))


def esc(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


L = []
def w(x=""):
    L.append(x)

w("# FF9 named-flag REGISTRY SEED  (research/flag_catalog.toml)")
w("#")
w("# Generated by research/make_catalog.py. A starter index<->name<->meaning table for a future kit flag")
w("# registry (STORY_FLAGS.md section 5 item 2). Tiers: a = engine/decompilation-grounded, b = corroborated")
w("# empirical, c = uncertain. Bit index N -> byte N>>3 bit N&7; Byte/Int16/UInt16 index = byte offset.")
w("# HW-naming trap: HW 'GlobBool' = engine Map (TRANSIENT); HW 'GenBool' = engine Global (PERSISTENT).")
w("# Do NOT label the persistent gEventGlobal space 'Glob'.")
w("")
w("[meta]")
w('source = "research/flag_census.json (676 fields) + Memoria Assembly-CSharp + Hades Workshop"')
w(f'real_bit_flag_max = {r["summary"]["bit_flag_max"]}   # max gEventGlobal BIT used by any real field')
w("")
w("# --- Recommended provably-safe custom-flag allocation bands (all clear of real-FF9 usage) ---")
w("[safe_bands]")
w("first_clear_bit = 8512        # byte 1064; first bit clear of ALL real usage (max real bit = 8511)")
w("campaign_flag_base = 8512     # recommend 8512 (round 8520/8600); was 8300 (collides w/ chest 8376-8511)")
w("flags_per_field = 64")
w("choice_scratch_floor = 16320  # byte 2040; reserve at/above this (engine/kit-owned)")
w("max_safe_fields = 122         # (16320 - 8512) // 64")
w("")
w("# === (a) Named engine variables ===")
for name, loc, typ, mean, tier, src in NAMED:
    w("[[named]]")
    w(f'name = "{name}"')
    w(f'location = "{loc}"')
    w(f'type = "{esc(typ)}"')
    w(f'meaning = "{esc(mean)}"')
    w(f'tier = "{tier}"')
    w(f'source = "{esc(src)}"')
    w("")
w("# === Reserved / do-not-allocate regions ===")
for name, loc, mean, tier, src in RESERVED:
    w("[[reserved]]")
    w(f'name = "{name}"')
    w(f'location = "{loc}"')
    w(f'meaning = "{esc(mean)}"')
    w(f'tier = "{tier}"')
    w(f'source = "{esc(src)}"')
    w("")
w("# === ScenarioCounter milestones (anchor points, not a continuous scale) ===")
for val, beat, tier, src in MILESTONES:
    w("[[scenario_milestone]]")
    w(f"value = {val}")
    w(f'beat = "{esc(beat)}"')
    w(f'tier = "{tier}"')
    w(f'source = "{esc(src)}"')
    w("")
w("# === (b) Empirical bit-flag region clusters (contiguous byte runs from the census) ===")
w("# Auto-derived: theme is INFERRED from a sample writing field — treat as a hint, not authoritative.")
for a, b in runs:
    bits = sorted(int(x) for x in bf if a <= bf[x]["byte"] <= b)
    nb = len(bits)
    # sample up to 3 distinct writer fields for a theme hint
    writers = []
    for bit in bits:
        for fid in bf[str(bit)]["writers"]:
            fb = pf.get(str(fid), {}).get("fbg", "")
            if fb and fb not in writers:
                writers.append(fb)
        if len(writers) >= 3:
            break
    w("[[region]]")
    w(f"bytes = [{a}, {b}]")
    w(f"bit_range = [{a*8}, {b*8+7}]")
    w(f"distinct_bits = {nb}")
    w("tier = \"b\"")
    w(f"sample_writer_fields = [{', '.join(chr(34)+esc(x)+chr(34) for x in writers[:3])}]")
    w("")

open(os.path.join(HERE, "flag_catalog.toml"), "w", encoding="utf-8").write("\n".join(L))
print(f"wrote flag_catalog.toml ({len(L)} lines, {len(runs)} empirical regions)")
