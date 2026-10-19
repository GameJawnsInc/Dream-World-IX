"""THE LOCO-CLASS TABLE for the s140 self-dress (R3-FIELD-MODEL-AUDIT.md 2.3 amendment 3, D4; amendments 1, 4, 10).

Classifies every Zidane-player clip NAME (the GEO_MAIN_F0_ZDN folder: `ANH_MAIN_F0_ZDN_*`) in Memoria's open-source
AnimationDB (Assembly-CSharp/Global/ff9/FF9DBAll.Animation.cs) into the class the engine's NetSyncSelfDress.MapAnim
uses on a dressed body. Classify by NAME, never by id: every ZDN name carries two ids (200 and 324 are both
ANH_MAIN_F0_ZDN_IDLE; JUMP1 alone has one).

THE RULES (the whole table follows from them; every name no rule names is OTHER):
  1. the exact slot tokens IDLE -> IDLE, WALK -> WALK, RUN -> RUN, TURN_L -> TURN_L, TURN_R -> TURN_R;
  2. an ON-FOOT qualified variant `<Q>_<slot token>` for Q in COLD, SWORD, FRA, MBG, POT, TKE -> the same slot. EXACT
     match: FRA_WALK (8846/8847, the 2705 Pandemonium walk) is a walk; FRA_WALK_1 / FRA_WALK_3 (9181 / 9184, the
     RunAnimation'd start and stop around 2705's walk loop) are gestures, so they fall to OTHER with no exception list;
  3. BREAK1_* -> INACTIVE (the rig's inactive clip; a rig with none: the ASLEEP / AANIM_EX-5 slot gets 0 and a
     RunAnimation plays the idle alias);
  4. JUMP, JUMP1, JUMP_<n>, LADDER_<n>_<m> -> JUMP_LADDER (the idle alias in s140, amendment 10; its own class so
     s141's twin row -- s141 amendment 7, "the body rig's clip with the same suffix" -- can split it);
  5. everything else -> OTHER (the idle alias): CHO_* (a dressed chocobo rider STANDS, D4), GRG_*, the SIT_ / CAMP_ /
     TENJYOU_ idles, FRA_WALK_1/_3, STAND, every gesture.

THE ONE DELTA FROM THE AUDIT'S LITERAL ROWS: STAND. Amendment 3 lists "exact IDLE, STAND ..." as slot tokens, but
ANH_MAIN_F0_ZDN_STAND (11185 / 11187) is no idle: no stock script ever puts it in a slot, and its only use is field
2934's four windowed RunAnimations (SetAnimationInOut 0-24, 25-36, 37-95, 96-133 under WaitAnimation, with a sound and
a line timed between them): a >= 134-frame STAND-UP gesture. As a loco family it would run NATIVE (a 30-72 frame
idle), so ExecAnim's animFrame = inFrame 96 lands past frameN - 1 and the 37-95 / 96-133 windows collapse (the scene's
timing with them). As OTHER it plays the idle alias on the SOURCE timeline (KeepSourceTimeline) and every window holds.
The JSON's `audit_literal_delta` names it so a reviewer can overrule it in one line (STAND_IS_IDLE below).

LOCO FAMILIES (the B_FRAME law, amendment 1: NATIVE timeline, KeepSourceTimeline does not apply, B_FRAME(id) answers
the mapped clip's frames): IDLE, WALK, RUN, TURN_L, TURN_R, INACTIVE. GESTURE families (KeepSourceTimeline; B_FRAME
answers stock, i.e. the attached SOURCE clip): OTHER, JUMP_LADDER -- and INACTIVE on a rig with no inactive clip,
because its RunAnimation then plays the idle alias, which is the gesture path (amendment 4's own 186 BREAK1_LOOK on
Freya example: frameN stays the source's 70).

Inputs (all read-only):
  --memoria   the Memoria clone (default C:\\gd\\FFIX\\Memoria): FF9DBAll.Animation.cs, open source.
  --exports   OPTIONAL evidence: the 817 field-script exports (default C:\\gd\\FFIX\\reference\\test2, NOT in the
              repo). Only usage COUNTS, field ids and numeric frame windows reach the JSON -- never script text.
  the kit's ff9mapkit._animdb_all.ANIMATIONS (THIS worktree's package) is a cross-check: every ZDN id must agree.

Usage:
  py -X utf8 studies/battle-coop/dress-census/gen_loco_table.py            # (re)write loco_table.json
  py -X utf8 studies/battle-coop/dress-census/gen_loco_table.py --check    # regenerate in memory, diff, exit 1 on drift
The pure rule is classify_name() (the Python twin); the engine copy is the JSON's engine_map / engine_cs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import OrderedDict, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
KIT = os.path.join(REPO, "ff9mapkit")
DEFAULT_MEMORIA = r"C:\gd\FFIX\Memoria"
DEFAULT_EXPORTS = r"C:\gd\FFIX\reference\test2"
ANIM_DB_REL = "Assembly-CSharp/Global/ff9/FF9DBAll.Animation.cs"
OUT = os.path.join(HERE, "loco_table.json")

FOLDER = "GEO_MAIN_F0_ZDN"
PREFIX = "ANH_MAIN_F0_ZDN_"
EXPECT_NAMES = 401      # the audit's count (2.3 amendment 3)
EXPECT_IDS = 801        # every name has two ids except JUMP1 (179)

# --- the classes. Codes 0-5 EQUAL NetSyncVisitor.LocoOther..LocoTurnR (NetSyncVisitor.cs:34), so LocoAnim(rig, code)
# answers the slot clip for 1-5 directly; 6 and 7 are local to the self-dress (s140 adds no wire bytes; wire stays v14).
CLASSES = OrderedDict([
    ("OTHER",       dict(code=0, family="gesture", s140_target="IdleAlias", bframe_remap="never",
                         note="the rig's IdleAlias (amendment 4: never the slot id); KeepSourceTimeline; B_FRAME stock")),
    ("IDLE",        dict(code=1, family="loco", s140_target="Idle", bframe_remap="always",
                         note="rig.Idle; native timeline; B_FRAME answers the mapped clip")),
    ("WALK",        dict(code=2, family="loco", s140_target="Walk", bframe_remap="always",
                         note="rig.Walk; native timeline; B_FRAME answers the mapped clip (2705's GetAnimDuration(8847) "
                              "loop; 2802's TKE_WALK footstep frame)")),
    ("RUN",         dict(code=3, family="loco", s140_target="Run", bframe_remap="always",
                         note="rig.Run; native timeline; B_FRAME answers the mapped clip (1464/1554's MBG_RUN footstep "
                              "frame)")),
    ("TURN_L",      dict(code=4, family="loco", s140_target="TurnL", bframe_remap="always",
                         note="rig.TurnL; native timeline; B_FRAME answers the mapped clip")),
    ("TURN_R",      dict(code=5, family="loco", s140_target="TurnR", bframe_remap="always",
                         note="rig.TurnR; native timeline; B_FRAME answers the mapped clip")),
    ("INACTIVE",    dict(code=6, family="loco", s140_target="Inactive (0 -> slot 0 / RunAnimation IdleAlias)",
                         bframe_remap="iff rig.Inactive != 0",
                         note="rig.Inactive when != 0 (native, B_FRAME answers it); a rig with none (rig.Inactive == 0: "
                              "Freya, Quina, Amarant, the moogle, and rows 9-12 per their census): the ASLEEP / "
                              "AANIM_EX-5 slot gets 0 and a RunAnimation plays the "
                              "IdleAlias on the GESTURE path (KeepSourceTimeline, B_FRAME stock: 400/1602's "
                              "GetAnimDuration(185/186) then feed SetAnimationInOut on the source timeline)")),
    ("JUMP_LADDER", dict(code=7, family="gesture", s140_target="IdleAlias", bframe_remap="never",
                         note="the IdleAlias in s140 (amendment 10, frame-safe); s141 amendment 7 maps it to the body "
                              "rig's same-suffix clip when the AnimationDB has one")),
])

SLOT_TOKENS = OrderedDict([("IDLE", "IDLE"), ("WALK", "WALK"), ("RUN", "RUN"), ("TURN_L", "TURN_L"),
                           ("TURN_R", "TURN_R")])
STAND_IS_IDLE = False   # the audit's literal row says True; the census says STAND is a 134-frame stand-up gesture
QUALIFIERS = ("COLD", "SWORD", "FRA", "MBG", "POT", "TKE")
# names of the form <X>_<slot token> whose X is NOT an on-foot qualifier: OTHER BY DESIGN (the audit's D4 list). The
# generator fails if the AnimationDB grows another one, so a new qualified slot can never slip in or out unreviewed.
DELIBERATE_OTHER_QUALIFIED = ("CAMP_IDLE", "CHO_RUN", "CHO_WALK", "SIT_IDLE")
INACTIVE_PREFIX = "BREAK1_"
JUMP_LADDER_RE = re.compile(r"^(JUMP|JUMP1|JUMP_\d+|LADDER_\d+_\d+)$")

# hand-named rows the audit / brief call out: each must land where stated (the generator fails loudly otherwise)
SAMPLES = OrderedDict([
    ("CHO_WALK", "OTHER"), ("CHO_RUN", "OTHER"), ("CHO_RIDE_2", "OTHER"),
    ("FRA_WALK", "WALK"), ("FRA_IDLE", "IDLE"), ("FRA_WALK_1", "OTHER"), ("FRA_WALK_3", "OTHER"),
    ("BREAK1_FLEX", "INACTIVE"), ("BREAK1_FLEX2", "INACTIVE"), ("BREAK1_LOOK", "INACTIVE"), ("GRG_BREAK", "OTHER"),
    ("IDLE", "IDLE"), ("WALK", "WALK"), ("RUN", "RUN"), ("TURN_L", "TURN_L"), ("TURN_R", "TURN_R"),
    ("STAND", "IDLE" if STAND_IS_IDLE else "OTHER"), ("TIRED_TO_IDLE", "OTHER"),
    ("COLD_WALK", "WALK"), ("SWORD_RUN", "RUN"), ("MBG_RUN", "RUN"), ("POT_TURN_L", "TURN_L"), ("TKE_WALK", "WALK"),
    ("SIT_IDLE", "OTHER"), ("CAMP_IDLE", "OTHER"), ("TENJYOU_IDLE_1", "OTHER"), ("GRG_1", "OTHER"),
    ("LADDER_2_3", "JUMP_LADDER"), ("LADDER_1_2", "JUMP_LADDER"), ("JUMP_1", "JUMP_LADDER"), ("JUMP1", "JUMP_LADDER"),
    ("SWORD_JUMP", "OTHER"), ("JUMP_KICK_1", "OTHER"), ("LADDER_TOUCH", "OTHER"), ("CLIMB", "OTHER"),
    ("OPEN_DOOR2", "OTHER"), ("POT_2", "OTHER"),
])
ID_SAMPLES = OrderedDict([(200, "IDLE"), (324, "IDLE"), (8847, "WALK"), (12782, "OTHER"), (192, "INACTIVE"),
                          (25, "WALK"), (38, "RUN"), (40, "TURN_L"), (41, "TURN_R"), (57, "INACTIVE"),
                          (9181, "OTHER"), (9184, "OTHER"), (186, "INACTIVE"), (11187, "IDLE" if STAND_IS_IDLE else "OTHER"),
                          (11453, "JUMP_LADDER"), (7935, "RUN"), (8555, "WALK")])
# the DressSelfTest row's sampled set (amendment 3: "including CHO_WALK -> idle and FRA_WALK -> walk"): (id, class)
SELFTEST_ROWS = [(12782, "OTHER"), (8847, "WALK"), (192, "INACTIVE"), (200, "IDLE"), (324, "IDLE"), (9181, "OTHER"),
                 (11187, "IDLE" if STAND_IS_IDLE else "OTHER"), (11453, "JUMP_LADDER"), (2575, "WALK"), (7935, "RUN"),
                 (4041, "TURN_L"), (3516, "TURN_R"), (2556, "OTHER")]   # 2556 = ANH_MAIN_F0_FRJ_IDLE: a non-ZDN name

# the field-script ops that name a clip on an entry (the export spellings; the DoEventCode case beside each)
SLOT_OPS = OrderedDict([
    ("SetStandAnimation", "AIDLE"), ("SetWalkAnimation", "AWALK"), ("SetRunAnimation", "ARUN"),
    ("SetLeftAnimation", "ATURNL"), ("SetRightAnimation", "ATURNR"), ("SetInactiveAnimation", "ASLEEP"),
    ("SetJumpAnimation", "AJUMP"),
])
PLAY_OPS = OrderedDict([("RunAnimation", "ANIM"), ("RunAnimationEx", "ANIM_EX")])
OP_RE = re.compile(r"\b(SetStandAnimation|SetWalkAnimation|SetRunAnimation|SetLeftAnimation|SetRightAnimation|"
                   r"SetInactiveAnimation|SetJumpAnimation|RunAnimationEx|RunAnimation)\(\s*([^)]*)\)")
INOUT_RE = re.compile(r"\bSetAnimationInOut\(\s*(.+)\s*\)\s*$")     # matched on the line with its // comment cut
DUR_RE = re.compile(r"\bGetAnimDuration\(\s*(\d+)\s*\)")
ENTRY_RE = re.compile(r"^#HW newentry (\d+)")
FILEID_RE = re.compile(r"^#HW fileid (\d+)")
DB_RE = re.compile(r'\{\s*(\d+)\s*,\s*"([^"]+)"\s*\}')
INT_RE = re.compile(r"^\d+$")


# ======================================================================================================================
# the rule (pure: the Python twin a pytest pins against the engine copy)
# ======================================================================================================================
def slot_of_token(token: str):
    if token in SLOT_TOKENS:
        return SLOT_TOKENS[token]
    if STAND_IS_IDLE and token == "STAND":
        return "IDLE"
    return None


def classify_suffix(suffix: str) -> str:
    """The class of one ZDN clip by its NAME suffix (the part after ANH_MAIN_F0_ZDN_)."""
    slot = slot_of_token(suffix)
    if slot:
        return slot
    head, sep, tail = suffix.partition("_")
    if sep and head in QUALIFIERS:
        slot = slot_of_token(tail)
        if slot:
            return slot
    if suffix.startswith(INACTIVE_PREFIX):
        return "INACTIVE"
    if JUMP_LADDER_RE.match(suffix):
        return "JUMP_LADDER"
    return "OTHER"


def classify_name(name) -> str:
    """The class of any AnimationDB name; a non-ZDN name (another folder) or None is OTHER."""
    if not name or not name.startswith(PREFIX):
        return "OTHER"
    return classify_suffix(name[len(PREFIX):])


def design_suffix_reading(suffix: str) -> str:
    """R3-DESIGN.md 3.4.4's superseded rule, 'classified by name suffix: IDLE, WALK, RUN, TURN_L, TURN_R, BREAK*' --
    kept only to list what it would have mis-filed (amendment 3's 'why')."""
    for tok in ("TURN_L", "TURN_R", "IDLE", "WALK", "RUN"):
        if suffix == tok or suffix.endswith("_" + tok):
            return tok
    if suffix.split("_")[-1].startswith("BREAK"):
        return "INACTIVE"
    return "OTHER"


# ======================================================================================================================
# inputs
# ======================================================================================================================
def read_anim_db(memoria: str):
    path = os.path.join(memoria, *ANIM_DB_REL.split("/"))
    with open(path, "rb") as f:
        raw = f.read()
    text = raw.decode("utf-8-sig")
    by_id = {}
    for i, n in DB_RE.findall(text):
        i = int(i)
        if i in by_id:
            raise SystemExit("duplicate AnimationDB id %d" % i)
        by_id[i] = n
    rev = None
    try:
        rev = subprocess.run(["git", "-C", memoria, "log", "-1", "--format=%H", "--", ANIM_DB_REL],
                             capture_output=True, text=True, timeout=30).stdout.strip() or None
        if subprocess.run(["git", "-C", memoria, "status", "--porcelain", "--", ANIM_DB_REL],
                          capture_output=True, text=True, timeout=30).stdout.strip():
            rev = (rev or "?") + "+dirty"
    except Exception:
        pass
    return by_id, hashlib.sha256(raw).hexdigest(), rev


def kit_cross_check(zdn_ids: dict) -> str:
    if KIT not in sys.path:
        sys.path.insert(0, KIT)
    import ff9mapkit                                  # noqa: E402  (THIS worktree's package, asserted below)
    here = os.path.normcase(os.path.abspath(ff9mapkit.__file__))
    if not here.startswith(os.path.normcase(os.path.abspath(KIT)) + os.sep):
        raise SystemExit("imported the wrong ff9mapkit: %s (want %s)" % (ff9mapkit.__file__, KIT))
    from ff9mapkit._animdb_all import ANIMATIONS      # noqa: E402
    kit_zdn = {i: n for i, n in ANIMATIONS.items() if n.startswith(PREFIX)}
    if kit_zdn != zdn_ids:
        only_db = sorted(set(zdn_ids.items()) - set(kit_zdn.items()))[:10]
        only_kit = sorted(set(kit_zdn.items()) - set(zdn_ids.items()))[:10]
        raise SystemExit("kit _animdb_all disagrees with FF9DBAll on the ZDN ids: db-only %r kit-only %r"
                         % (only_db, only_kit))
    return "ff9mapkit._animdb_all.ANIMATIONS: %d of %d ZDN ids agree" % (len(kit_zdn), len(zdn_ids))


def _window(expr: str):
    """SetAnimationInOut's two args -> [in, out] ints, or 'expr' for a computed one (no script text leaves)."""
    depth, parts, cur = 0, [], ""
    for ch in expr:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    if len(parts) != 2:
        return None
    return [int(p.strip()) if INT_RE.match(p.strip()) else "expr" for p in parts]


def census_exports(exports: str, by_id: dict, zdn_ids: dict, table: dict):
    """Usage COUNTS of every ZDN clip id per op over the field-script exports (field ids only reach the JSON)."""
    if not exports or not os.path.isdir(exports):
        return None
    files = sorted((f for f in os.listdir(exports) if re.match(r"^test2_\d+\.txt$", f)),
                   key=lambda f: int(re.findall(r"\d+", f)[0]))
    use = defaultdict(lambda: defaultdict(lambda: {"fields": set(), "n": 0, "player_n": 0}))
    dur = defaultdict(lambda: {"fields": set(), "n": 0})
    windows = defaultdict(set)              # name -> {(field, in, out)} for a RunAnimation under a non-default window
    jumps = defaultdict(set)                # name -> {(jump0, jump1)} for SetJumpAnimation in a player entry
    jump_max_any = [0, None]                # the largest jump1 any SetJumpAnimation sets in a player entry, any folder
    foreign = defaultdict(int)              # folder -> ops naming a non-ZDN clip on a player entry itself
    nfiles = 0
    for fn in files:
        with open(os.path.join(exports, fn), "r", encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
        nfiles += 1
        field = None
        entries = defaultdict(list)
        cur = -1
        for ln in lines:
            m = FILEID_RE.match(ln)
            if m and field is None:
                field = int(m.group(1))
            m = ENTRY_RE.match(ln)
            if m:
                cur = int(m.group(1))
                continue
            entries[cur].append(ln)
        if field is None:
            continue
        # a PLAYER entry: SetModel( 98, ..) + DefinePlayerCharacter in the same entry (the 98+CC entry)
        player = set()
        for e, body in entries.items():
            joined = "\n".join(body)
            if re.search(r"\bSetModel\(\s*98\s*,", joined) and "DefinePlayerCharacter(" in joined:
                player.add(e)
        for e, body in entries.items():
            inout = None
            for ln in body:
                if ln.startswith("Function "):
                    inout = None
                m = INOUT_RE.search(ln.split("//")[0])
                if m:
                    inout = _window(m.group(1))
                for m in OP_RE.finditer(ln):
                    op, args = m.group(1), [a.strip() for a in m.group(2).split(",")]
                    try:
                        if op == "RunAnimationEx":
                            target, anim = int(args[0]), int(args[1])
                        else:
                            target, anim = e, int(args[0])
                    except (ValueError, IndexError):
                        continue
                    name = zdn_ids.get(anim)
                    if name is None:
                        if target == e and e in player and op != "RunAnimationEx":
                            other = by_id.get(anim)
                            tok = other.split("_") if other else []
                            foreign["GEO_%s_%s_%s" % tuple(tok[1:4]) if len(tok) >= 4 else "unknown"] += 1
                        if op == "SetJumpAnimation" and e in player and len(args) >= 3 and INT_RE.match(args[2]):
                            if int(args[2]) > jump_max_any[0]:
                                jump_max_any[:] = [int(args[2]), field]
                        continue
                    slot = use[name][op]
                    slot["fields"].add(field)
                    slot["n"] += 1
                    if target in player:
                        slot["player_n"] += 1
                    if op == "SetJumpAnimation" and e in player and len(args) >= 3:
                        if INT_RE.match(args[1]) and INT_RE.match(args[2]):
                            jumps[name].add((int(args[1]), int(args[2])))
                            if int(args[2]) > jump_max_any[0]:
                                jump_max_any[:] = [int(args[2]), field]
                    if op == "RunAnimation" and inout and inout != [0, 255]:
                        if table[name] != "OTHER" or name == PREFIX + "STAND":
                            windows[name].add((field, inout[0], inout[1]))
                for m in DUR_RE.finditer(ln):
                    anim = int(m.group(1))
                    if anim in zdn_ids:
                        dur[anim]["fields"].add(field)
                        dur[anim]["n"] += 1
    return dict(nfiles=nfiles, use=use, dur=dur, windows=windows, jumps=jumps, jump_max_any=jump_max_any,
                foreign=foreign)


# ======================================================================================================================
# the engine copy
# ======================================================================================================================
CS_CONST = {"OTHER": "LocoClassOther", "IDLE": "LocoClassIdle", "WALK": "LocoClassWalk", "RUN": "LocoClassRun",
            "TURN_L": "LocoClassTurnL", "TURN_R": "LocoClassTurnR", "INACTIVE": "LocoClassInactive",
            "JUMP_LADDER": "LocoClassJumpLadder"}


def engine_map_cs(by_class_names: dict, total: int):
    """THE ENGINE COPY: a static, closed name -> class map, written as one suffix row per class (row index == the class
    code) and expanded once into an ordinal Dictionary keyed on the FULL name. A pytest pins it by parsing the rows."""
    entries = sum(len(v) for c, v in by_class_names.items() if c != "OTHER")
    cs = ["// [ff9mapkit netsync s140] THE LOCO-CLASS TABLE (R3-FIELD-MODEL-AUDIT.md 2.3 amendment 3): generated by",
          "// studies/battle-coop/dress-census/gen_loco_table.py from FF9DBAll.Animation.cs -- the %d non-OTHER names of the" % entries,
          "// %d GEO_MAIN_F0_ZDN names, one row per class (row index == the class code; the suffix follows ANH_MAIN_F0_ZDN_)." % total,
          "// Any other name, every non-ZDN name included, is LocoClassOther (the rig's idle ALIAS). Classified by NAME: 200 and",
          "// 324 are both ANH_MAIN_F0_ZDN_IDLE. Codes 0-5 == NetSyncVisitor.LocoOther..LocoTurnR.",
          "internal const Byte LocoClassOther = 0, LocoClassIdle = 1, LocoClassWalk = 2, LocoClassRun = 3, LocoClassTurnL = 4,",
          "    LocoClassTurnR = 5, LocoClassInactive = 6, LocoClassJumpLadder = 7;",
          "private static readonly String[][] LocoClassSuffixes =",
          "{",
          "    new String[0],"]
    for c, names in by_class_names.items():
        if c == "OTHER":
            continue
        cs.append("    new String[] { %s },   // %d %s" % (", ".join('"%s"' % n[len(PREFIX):] for n in names),
                                                       CLASSES[c]["code"], CS_CONST[c][len("LocoClass"):]))
    cs += ["};",
           "private static readonly Dictionary<String, Byte> LocoClassByName = BuildLocoClassByName();",
           "private static Dictionary<String, Byte> BuildLocoClassByName()",
           "{",
           "    Dictionary<String, Byte> map = new Dictionary<String, Byte>(StringComparer.Ordinal);",
           "    for (Int32 c = 1; c < LocoClassSuffixes.Length; c++)",
           "        foreach (String s in LocoClassSuffixes[c])",
           "            map[\"ANH_MAIN_F0_ZDN_\" + s] = (Byte)c;   // indexer: type init never throws (amendment 9)",
           "    return map;",
           "}",
           "internal static Byte LocoClassOf(String name)   // pure; never throws (a null name -> Other)",
           "{",
           "    Byte c;",
           "    return name != null && LocoClassByName.TryGetValue(name, out c) ? c : LocoClassOther;",
           "}"]
    return cs


def rule_set_cs():
    """The compact alternative, written out only to SIZE it against the map (the map is what the engine carries)."""
    return [
        "private static readonly String[] LocoQualifiers = { \"COLD\", \"SWORD\", \"FRA\", \"MBG\", \"POT\", \"TKE\" };",
        "private static Byte LocoSlotToken(String t)",
        "{",
        "    switch (t) { case \"IDLE\": return 1; case \"WALK\": return 2; case \"RUN\": return 3;",
        "                 case \"TURN_L\": return 4; case \"TURN_R\": return 5; default: return 0; }",
        "}",
        "private static Boolean LocoDigits(String s, Int32 from, Int32 len)",
        "{",
        "    if (len <= 0 || from + len > s.Length) return false;",
        "    for (Int32 i = from; i < from + len; i++) if (s[i] < '0' || s[i] > '9') return false;",
        "    return true;",
        "}",
        "internal static Byte LocoClassOf(String name)",
        "{",
        "    if (name == null || !name.StartsWith(\"ANH_MAIN_F0_ZDN_\", StringComparison.Ordinal)) return 0;",
        "    String s = name.Substring(16);",
        "    Byte c = LocoSlotToken(s); if (c != 0) return c;",
        "    Int32 u = s.IndexOf('_');",
        "    if (u > 0 && Array.IndexOf(LocoQualifiers, s.Substring(0, u)) >= 0) { c = LocoSlotToken(s.Substring(u + 1)); if (c != 0) return c; }",
        "    if (s.StartsWith(\"BREAK1_\", StringComparison.Ordinal)) return 6;",
        "    if (s == \"JUMP\" || s == \"JUMP1\" || (s.StartsWith(\"JUMP_\", StringComparison.Ordinal) && LocoDigits(s, 5, s.Length - 5))) return 7;",
        "    if (s.StartsWith(\"LADDER_\", StringComparison.Ordinal)) { Int32 v = s.IndexOf('_', 7);",
        "        if (v > 7 && LocoDigits(s, 7, v - 7) && LocoDigits(s, v + 1, s.Length - v - 1)) return 7; }",
        "    return 0;",
        "}",
    ]


def _chars(lines):
    return sum(len(re.sub(r"\s+", "", ln)) for ln in lines if not ln.lstrip().startswith("//"))


# names NOT in the AnimationDB: the closed map answers OTHER, the open rule set may not (the reason the map is the law)
CS_PROBE_EXTRAS = ["ANH_MAIN_F0_FRJ_IDLE", "ANH_MAIN_F1_ZDN_WALK", "ANH_MAIN_F0_ZDD_WALK", "ANH_ACC_F0_GAS_F0_ZDN_WALK",
                   "ANH_NPC_F0_MOG_IDLE", "ANH_MAIN_F0_ZDN_", "ANH_MAIN_F0_ZDN_JUMP_", "ANH_MAIN_F0_ZDN_LADDER_1_",
                   "ANH_MAIN_F0_ZDN_LADDER__1", "ANH_MAIN_F0_ZDN_TKE_RUN", "ANH_MAIN_F0_ZDN_JUMP_12",
                   "ANH_MAIN_F0_ZDN_BREAK1_"]


def verify_cs(doc) -> int:
    """--verify-cs (Windows): compile BOTH C# forms in memory with PowerShell's Add-Type and run them on every ZDN name,
    null and CS_PROBE_EXTRAS; each DB name must answer the table's code in both forms. Touches nothing but a temp dir."""
    import tempfile
    tmp = tempfile.mkdtemp(prefix="loco_cs_")
    wrap = lambda cls, lines: "public static class %s\n{\n%s\n}\n" % (cls, "\n".join("    " + ln for ln in lines))
    src = ("using System;\nusing System.Collections.Generic;\n" + wrap("LocoMapForm", doc["engine_cs"])
           + wrap("LocoRuleForm", rule_set_cs())).replace("internal static Byte LocoClassOf", "public static Byte LocoClassOf")
    names = [PREFIX + s for s in doc["table"]]
    with open(os.path.join(tmp, "loco.cs"), "w", encoding="ascii", newline="\r\n") as f:
        f.write(src)
    with open(os.path.join(tmp, "names.txt"), "w", encoding="ascii", newline="\n") as f:
        f.write("\n".join(names + CS_PROBE_EXTRAS) + "\n")
    ps = ("$ErrorActionPreference = 'Stop'\n"
          "$d = '%s'\n"
          "Add-Type -TypeDefinition ([System.IO.File]::ReadAllText((Join-Path $d 'loco.cs'))) -Language CSharp\n"
          "$sb = New-Object System.Text.StringBuilder\n"
          "foreach ($n in [System.IO.File]::ReadAllLines((Join-Path $d 'names.txt'))) { if ($n -ne '') {\n"
          "  [void]$sb.Append($n + \"`t\" + [LocoMapForm]::LocoClassOf($n) + \"`t\" + [LocoRuleForm]::LocoClassOf($n) + \"`n\") } }\n"
          "[void]$sb.Append('<null>' + \"`t\" + [LocoMapForm]::LocoClassOf($null) + \"`t\" + [LocoRuleForm]::LocoClassOf($null) + \"`n\")\n"
          "[System.IO.File]::WriteAllText((Join-Path $d 'out.txt'), $sb.ToString(), (New-Object System.Text.ASCIIEncoding))\n"
          % tmp)
    with open(os.path.join(tmp, "run.ps1"), "w", encoding="ascii", newline="\r\n") as f:
        f.write(ps)
    r = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", os.path.join(tmp, "run.ps1")],
                       capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        print(r.stdout + r.stderr)
        return 1
    code = {c: d["code"] for c, d in CLASSES.items()}
    db = set(names)
    bad, n_db, open_diff = 0, 0, []
    for ln in open(os.path.join(tmp, "out.txt"), encoding="ascii").read().splitlines():
        name, a, b = ln.split("\t")
        want = code[doc["table"][name[len(PREFIX):]]] if name in db else code["OTHER"]
        if name in db or name == "<null>":
            n_db += name in db
            if int(a) != want or int(b) != want:
                bad += 1
                print("MISMATCH %s: map %s rule %s table %d" % (name, a, b, want))
        else:
            if int(a) != want:
                bad += 1
                print("MISMATCH %s: the closed map answered %s, not OTHER" % (name, a))
            if int(b) != int(a):
                open_diff.append("%s (rule %s)" % (name[len(PREFIX):] if name.startswith(PREFIX) else name, b))
    print("verify-cs: %d DB names + null: map and rule set %s; outside the DB the open rule set differs on: %s"
          % (n_db, "AGREE with the table" if not bad else "DISAGREE (%d)" % bad, ", ".join(open_diff) or "none"))
    return 1 if bad else 0


# ======================================================================================================================
# build
# ======================================================================================================================
def build(memoria: str, exports: str):
    by_id, sha, rev = read_anim_db(memoria)
    zdn_ids = {i: n for i, n in by_id.items() if n.startswith(PREFIX)}
    names = sorted(set(zdn_ids.values()))
    ids_of = defaultdict(list)
    for i, n in sorted(zdn_ids.items()):
        ids_of[n].append(i)
    if len(names) != EXPECT_NAMES or len(zdn_ids) != EXPECT_IDS:
        raise SystemExit("ZDN census moved: %d names / %d ids (expected %d / %d)"
                         % (len(names), len(zdn_ids), EXPECT_NAMES, EXPECT_IDS))
    cross = kit_cross_check(zdn_ids)

    table = OrderedDict((n, classify_name(n)) for n in names)
    suffixes = [n[len(PREFIX):] for n in names]

    # --- self-checks: each can fail (and says which row)
    for q in QUALIFIERS:   # a qualifier that reaches no slot name is a dead rule
        if not any(s.startswith(q + "_") and table[PREFIX + s] not in ("OTHER", "INACTIVE", "JUMP_LADDER")
                   for s in suffixes):
            raise SystemExit("qualifier %s matches no slot name" % q)
    qualified_other = sorted(s for s in suffixes
                             if "_" in s and s.partition("_")[0] not in QUALIFIERS and slot_of_token(s.partition("_")[2]))
    if tuple(qualified_other) != DELIBERATE_OTHER_QUALIFIED:
        raise SystemExit("unreviewed <X>_<slot> names: %r (reviewed: %r)" % (qualified_other, DELIBERATE_OTHER_QUALIFIED))
    for suffix, want in SAMPLES.items():
        got = table.get(PREFIX + suffix)
        if got != want:
            raise SystemExit("sample %s: %r, expected %r" % (suffix, got, want))
    for i, want in ID_SAMPLES.items():
        got = table[zdn_ids[i]]
        if got != want:
            raise SystemExit("id sample %d (%s): %r, expected %r" % (i, zdn_ids[i], got, want))
    if zdn_ids[200] != zdn_ids[324]:
        raise SystemExit("200 and 324 no longer share a name")

    by_class_names = OrderedDict((c, [n for n in names if table[n] == c]) for c in CLASSES)
    by_class_ids = OrderedDict((c, sorted(i for i, n in zdn_ids.items() if table[n] == c)) for c in CLASSES)

    # --- the ENGINE copy: the static name -> class map of the NON-OTHER names (default OTHER); proven equal on all 401
    engine_map = [[n, table[n], CLASSES[table[n]]["code"]] for n in names if table[n] != "OTHER"]
    em = {n: c for n, c, _ in engine_map}
    if any(em.get(n, "OTHER") != table[n] for n in names):
        raise SystemExit("engine map does not reproduce the table")
    cs_map = engine_map_cs(by_class_names, len(names))
    cs_rules = rule_set_cs()
    prefix_reading = []      # what a PREFIX reading of the brief ("FRA_ except FRA_WALK_1/_3") files differently
    for s in suffixes:
        head, sep, tail = s.partition("_")
        if sep and head in QUALIFIERS:
            for tok in list(SLOT_TOKENS) + ["STAND"]:
                if tail.startswith(tok + "_"):
                    prefix_reading.append(s)
                    break
    design_misfiles = OrderedDict((s, [design_suffix_reading(s), table[PREFIX + s]]) for s in suffixes
                                  if design_suffix_reading(s) != table[PREFIX + s]
                                  and table[PREFIX + s] != "JUMP_LADDER")

    loco_names = OrderedDict()
    for c in CLASSES:
        if c != "OTHER":
            loco_names[c] = [OrderedDict([("name", n[len(PREFIX):]), ("ids", ids_of[n])]) for n in by_class_names[c]]

    doc = OrderedDict()
    doc["schema"] = "ff9mapkit.dress-census.loco-table/1"
    doc["generator"] = "studies/battle-coop/dress-census/gen_loco_table.py"
    doc["audit"] = "studies/battle-coop/R3-FIELD-MODEL-AUDIT.md 2.3 amendment 3 (D4); amendments 1, 4, 10"
    doc["source"] = OrderedDict([("file", ANIM_DB_REL), ("sha256", sha), ("memoria_rev", rev), ("open_source", True),
                                 ("kit_cross_check", cross)])
    doc["folder"] = FOLDER
    doc["prefix"] = PREFIX
    doc["counts"] = OrderedDict([("names", len(names)), ("ids", len(zdn_ids)),
                                 ("names_by_class", OrderedDict((c, len(v)) for c, v in by_class_names.items())),
                                 ("ids_by_class", OrderedDict((c, len(v)) for c, v in by_class_ids.items()))])
    doc["classes"] = OrderedDict((c, OrderedDict([("code", d["code"]), ("family", d["family"]),
                                                  ("s140_target", d["s140_target"]), ("bframe_remap", d["bframe_remap"]),
                                                  ("note", d["note"])]))
                                 for c, d in CLASSES.items())
    doc["loco_families"] = [c for c, d in CLASSES.items() if d["family"] == "loco"]
    doc["gesture_families"] = [c for c, d in CLASSES.items() if d["family"] == "gesture"]
    doc["rules"] = OrderedDict([
        ("slot_tokens", OrderedDict(SLOT_TOKENS)),
        ("stand_is_idle", STAND_IS_IDLE),
        ("qualifiers", list(QUALIFIERS)),
        ("qualifier_match", "EXACT <Q>_<slot token>: FRA_WALK_1 / FRA_WALK_3 fall to OTHER with no exception list"),
        ("deliberate_other_qualified", list(DELIBERATE_OTHER_QUALIFIED)),
        ("inactive_prefix", INACTIVE_PREFIX),
        ("jump_ladder_pattern", JUMP_LADDER_RE.pattern),
        ("default", "OTHER"),
        ("non_zdn_name", "OTHER"),
        ("rig0_zidane", "every ZDN name is rig 0's OWN clip: MapAnim must pass it through (R3-DESIGN 3.4.4 'the dressed "
                        "character's own clips pass through'); the table applies to a body whose rig is not GEO_MAIN_F0_ZDN"),
    ])
    doc["audit_literal_delta"] = [] if STAND_IS_IDLE else [OrderedDict([
        ("name", "STAND"), ("ids", ids_of[PREFIX + "STAND"]), ("audit", "IDLE"), ("table", "OTHER"),
        ("why", "no stock slot ever holds it; its only use is field 2934's four windowed RunAnimations (in/out 0-24, "
                "25-36, 37-95, 96-133 under WaitAnimation): a >=134-frame stand-up gesture. Native (loco) would start "
                "the 96-133 window past frameN-1 and collapse the scene's timing; OTHER keeps the source timeline"),
        ("flip", "STAND_IS_IDLE = True in gen_loco_table.py")])]
    map_chars, rule_chars = _chars(cs_map), _chars(cs_rules)
    doc["engine_copy"] = OrderedDict([
        ("form", "a static, closed name -> class map of the NON-OTHER names, default OTHER: one suffix row per class "
                 "(LocoClassSuffixes, row index == code) expanded once into LocoClassByName; LocoClassOf(name)"),
        ("entries", len(engine_map)),
        ("map_chars", map_chars),
        ("rule_set_chars", rule_chars),
        ("smaller", "map" if map_chars <= rule_chars else "rule_set"),
        ("why", ("the map is the smaller source (%d vs %d non-blank chars) " % (map_chars, rule_chars)
                 if map_chars <= rule_chars else
                 "the rule set is %d chars smaller, but the map is kept " % (map_chars - rule_chars))
                + "AND it pins row for row: a pytest parses LocoClassSuffixes out of NetSyncSelfDress.cs and asserts it "
                  "equals engine_map, so it equals the table on all %d names (the rule set could only be pinned by "
                  "sampled rows); it is closed (a mod-added name never becomes a slot by accident) and does no string "
                  "parsing on the VM path" % len(names)),
        ("python_twin", "CLOSED, like the engine: a name is non-OTHER iff it is an engine_map row (battlewire can load "
                        "this JSON or copy the rows). classify_name() here is the GENERATING rule: it equals the map on "
                        "every AnimationDB name and differs only outside the DB (a mod-added TKE_RUN: rule RUN, map "
                        "OTHER), where the closed map is the law"),
        ("cs_verified", "--verify-cs compiles both C# forms in memory (PowerShell Add-Type) and runs them on all %d "
                        "names, null and %d non-DB probes" % (len(names), len(CS_PROBE_EXTRAS))),
        ("prefix_reading_misfiles", prefix_reading),
        ("design_suffix_rule_misfiles", design_misfiles),
        ("reproduces_table", "%d of %d names" % (len(names), len(names))),
    ])
    doc["engine_map"] = engine_map
    doc["engine_cs"] = cs_map
    doc["selftest_rows"] = [[i, by_id[i], c, CLASSES[c]["code"]] for i, c in SELFTEST_ROWS]
    for i, n, c, _ in doc["selftest_rows"]:
        if classify_name(n) != c:
            raise SystemExit("selftest row %d (%s): %r, expected %r" % (i, n, classify_name(n), c))
    doc["loco_names"] = loco_names
    doc["samples"] = OrderedDict([("CHO_WALK", table[PREFIX + "CHO_WALK"]), ("FRA_WALK", table[PREFIX + "FRA_WALK"]),
                                  ("BREAK1_FLEX", table[PREFIX + "BREAK1_FLEX"]), ("200", table[zdn_ids[200]]),
                                  ("324", table[zdn_ids[324]])])
    doc["table"] = OrderedDict((n[len(PREFIX):], c) for n, c in table.items())
    doc["by_id"] = OrderedDict((str(i), [zdn_ids[i][len(PREFIX):], table[zdn_ids[i]]]) for i in sorted(zdn_ids))

    cen = census_exports(exports, by_id, zdn_ids, table)
    doc["evidence"] = None if cen is None else evidence_doc(cen, names, ids_of, zdn_ids, table)
    return doc


def evidence_doc(cen, names, ids_of, zdn_ids, table):
    use, dur = cen["use"], cen["dur"]
    ev = OrderedDict()
    ev["source"] = ("the field-script exports (C:\\gd\\FFIX\\reference\\test2, not in the repo): counts, field ids and "
                    "numeric frame windows only")
    ev["files"] = cen["nfiles"]
    ev["ops"] = OrderedDict(list(SLOT_OPS.items()) + list(PLAY_OPS.items()))
    ev["player_entry"] = "SetModel( 98, ..) + DefinePlayerCharacter in one entry (RunAnimationEx: its target entry)"

    def opdoc(name):
        d = OrderedDict()
        for op in list(SLOT_OPS) + list(PLAY_OPS):
            if op in use.get(name, {}):
                s = use[name][op]
                d[op] = OrderedDict([("fields", len(s["fields"])), ("n", s["n"]), ("player_n", s["player_n"]),
                                     ("field_ids", sorted(s["fields"])[:40])])
        return d

    # 1. every name in a non-OTHER class, every qualifier-prefixed name and the deliberate OTHERs, with stock usage
    verify = OrderedDict()
    for n in names:
        s = n[len(PREFIX):]
        if table[n] != "OTHER" or s.split("_")[0] in QUALIFIERS or s in DELIBERATE_OTHER_QUALIFIED or s == "STAND":
            verify[s] = OrderedDict([("class", table[n]), ("ids", ids_of[n]), ("uses", opdoc(n))])
    ev["loco_and_qualified"] = verify
    # 2. OTHER names stock puts in a slot op: a dressed body plays its idle alias there (D4 accepts it; s141 input)
    other_in_slots = OrderedDict()
    for n in names:
        if table[n] != "OTHER":
            continue
        hit = OrderedDict()
        for op in SLOT_OPS:
            if op in use.get(n, {}):
                s = use[n][op]
                hit[op] = OrderedDict([("fields", len(s["fields"])), ("player_n", s["player_n"])])
        if hit:
            other_in_slots[n[len(PREFIX):]] = hit
    ev["other_names_in_slot_ops"] = other_in_slots
    # 3. the B_FRAME queries: every GetAnimDuration(<ZDN id>) site, by class (amendment 1's census input)
    bq = OrderedDict()
    for i in sorted(dur):
        n = zdn_ids[i]
        bq[str(i)] = OrderedDict([("name", n[len(PREFIX):]), ("class", table[n]), ("family", CLASSES[table[n]]["family"]),
                                  ("fields", sorted(dur[i]["fields"])), ("n", dur[i]["n"])])
    ev["get_anim_duration_zdn"] = bq
    ev["get_anim_duration_loco_family_ids"] = [int(k) for k, v in bq.items() if v["family"] == "loco"]
    # 4. RunAnimation of a loco/jump-class id (and STAND) under a non-default SetAnimationInOut window: on a NATIVE
    #    timeline a window past the rig clip's frameN - 1 collapses (ExecAnim's animFrame = inFrame; ProcessAnime caps out)
    ev["windowed_runs"] = OrderedDict(
        (n[len(PREFIX):], OrderedDict([("class", table[n]), ("windows", [list(w) for w in sorted(
            cen["windows"][n], key=lambda w: (w[0], str(w[1]), str(w[2])))])]))
        for n in names if n in cen["windows"])
    # 5. the jump windows (amendment 10's frame-safety bound): SetJumpAnimation(clip, jump0, jump1) in a player entry
    jw = OrderedDict()
    for n in names:
        if n in cen["jumps"]:
            jw[n[len(PREFIX):]] = OrderedDict([("class", table[n]), ("windows", [list(w) for w in sorted(cen["jumps"][n])])])
    zdn_max = max((w[1] for n in cen["jumps"] for w in cen["jumps"][n]), default=0)
    ev["jump_windows"] = OrderedDict([("by_name", jw), ("max_jump1_zdn", zdn_max),
                                      ("max_jump1_any_clip", cen["jump_max_any"][0]),
                                      ("max_jump1_any_clip_field", cen["jump_max_any"][1])])
    # 6. non-ZDN clips named on a player entry ITSELF (they classify OTHER -> the idle alias): folder -> op count
    ev["non_zdn_clips_on_player_entries"] = OrderedDict(sorted(cen["foreign"].items(), key=lambda kv: (-kv[1], kv[0])))
    # 7. names no export names at all
    ev["unused_names"] = [n[len(PREFIX):] for n in names
                          if n not in use and not any(zdn_ids[i] == n for i in dur)]
    return ev


def dumps(doc) -> str:
    return json.dumps(doc, indent=1, ensure_ascii=True) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--memoria", default=DEFAULT_MEMORIA)
    ap.add_argument("--exports", default=DEFAULT_EXPORTS, help="optional evidence dir ('' to skip)")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--check", action="store_true", help="regenerate in memory and diff against --out")
    ap.add_argument("--verify-cs", action="store_true",
                    help="Windows: also compile the engine C# (map and rule-set forms) in memory and run it on every name")
    a = ap.parse_args(argv)
    doc = build(a.memoria, a.exports)
    text = dumps(doc)
    if a.verify_cs and verify_cs(doc):
        return 1
    if a.check:
        with open(a.out, "r", encoding="utf-8") as f:
            old = json.load(f)
        new = json.loads(text)
        if old.get("evidence") is None or new.get("evidence") is None:   # evidence needs the exports: compare the rest
            old.pop("evidence", None)
            new.pop("evidence", None)
        if old != new:
            print("loco_table.json DRIFTED: %s" % ", ".join(k for k in sorted(set(old) | set(new))
                                                         if old.get(k) != new.get(k)))
            return 1
        print("loco_table.json matches (%d names, %d ids)" % (doc["counts"]["names"], doc["counts"]["ids"]))
        return 0
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    c = doc["counts"]["names_by_class"]
    print("wrote %s: %d names / %d ids; %s" % (a.out, doc["counts"]["names"], doc["counts"]["ids"],
                                                ", ".join("%s %d" % kv for kv in c.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
