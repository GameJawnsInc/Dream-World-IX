"""THE 8-11 RIG CENSUS (battle co-op s140; owner decision 2026-10-17: Blank, Marcus, Cinna and Beatrix wear "their own
models") -- rig rows 9-12 of NetSyncVisitor.Rig for CharacterId 8 Cinna, 9 Marcus, 10 Blank, 11 Beatrix (orchestrator O1:
rig 9-12 = CharacterId 8-11 in CharacterId order), every column read off the install the way s139 filled rows 0-8
("every value checked against all 817 field-script exports and the clips in p0data5"), plus the 13-row frame-count table.

READ-ONLY. Sources, each named in the output:
  * the 817 Hades Workshop field-script exports (``--exports``, test2_N.txt; N = HW index, NOT a field id -- the repo's
    reference/field-manifest.tsv maps it), FIRST language block only (the audit's census convention);
  * the install's p0data4 (model prefabs: ff9mapkit.models.extract.read_model / bone_labels.read_skeleton) and p0data5
    (clips: ff9mapkit.models._gltf_io.anim_disc_map / read_clip at the folder ff9mapkit.catalog.locate_animation
    resolves), loaded by UnityPy, which writes nothing;
  * the open-source Memoria tables (``--memoria``: FF9DBAll.Animation.cs and FF9BattleDB.GEO.cs, read in SOURCE ORDER --
    TwoWayDictionary(true) keeps the FIRST id per name as the reverse key, which is the key
    AnimationFactory.GetRenameAnimationPath loads a clip NAME from) and the kit's copies of them (_animdb_all, _modeldb);
  * every active mod folder's DictionaryPatch.txt (a `3DModel` / `3DModelAnimation` remap of a census id is named).

THE METHOD IS CALIBRATED FIRST: the same census run over rows 0-8 (the s139 table, quoted below as literals) must
reproduce every column s139 shipped -- a column it cannot reproduce is reported, and its 9-12 value is then flagged.

Output: numbers and open-source names only (zero game bytes) -> rigs_8_11.json next to this file.

    py -X utf8 studies/battle-coop/dress-census/rigs_8_11.py [--game <FF9 root>] [--exports <dir>] [--memoria <clone>]
    py -X utf8 studies/battle-coop/dress-census/rigs_8_11.py --check     # rebuild in memory, diff rows + frames_13
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]                                   # studies/battle-coop/dress-census -> the repo (this worktree)
PKG = REPO / "ff9mapkit"
if str(PKG) not in sys.path:
    sys.path.insert(0, str(PKG))
import ff9mapkit                                         # noqa: E402 - path pinned above
_KIT_AT = Path(ff9mapkit.__file__).resolve()
assert _KIT_AT.is_relative_to(PKG.resolve()), f"ff9mapkit resolved to {_KIT_AT}, not this tree's {PKG}"

DEFAULT_EXPORTS = Path(r"C:\gd\FFIX\reference\test2")
DEFAULT_MEMORIA = Path(r"C:\gd\FFIX\Memoria")
MANIFEST = REPO / "reference" / "field-manifest.tsv"
OUT = HERE / "rigs_8_11.json"

# ------------------------------------------------------------------------------------------------ the s139 table (rows 0-8)
#: NetSyncVisitor.Rigs as s139 shipped them (memoria-patches/s139-netsync-dress-host-rule.patch; the repo twin
#: tools/harness/battlewire.RIGS) -- the CALIBRATION the census must reproduce before its 9-12 answers are trusted.
COLUMNS = ("model", "idle", "walk", "run", "turn_l", "turn_r", "eye", "inactive", "walk_step_a", "walk_step_b",
           "run_step_a", "run_step_b", "step_sound", "idle_alias", "hand_bone", "hand_bone_end")
S139_ROWS = (
    (98, 200, 25, 38, 40, 41, 93, 57, 4, 13, 0, 8, 0, 324, 12, 13),                 # 0 Zidane
    (8, 148, 571, 419, 917, 918, 61, 912, 4, 14, 0, 9, 0, 573, 16, 17),             # 1 Vivi
    (185, 2089, 2086, 2091, 2088, 2084, 91, 3160, 4, 15, 0, 9, 0, 2090, 14, 15),    # 2 Garnet
    (5489, 2001, 1996, 2005, 1986, 2010, 104, 119, 4, 14, 0, 9, 925, 2002, 14, 15),  # 3 Steiner
    (192, 2556, 2553, 2558, 2555, 2551, 94, 0, 4, 16, 0, 9, 0, 2557, 12, 12),        # 4 Freya
    (273, 3228, 3237, 3230, 3235, 3227, 92, 0, -1, -1, -1, -1, 0, 3229, 13, 14),     # 5 Quina
    (443, 7503, 7518, 7506, 7516, 7514, 63, 9590, 1, 13, 0, 9, 0, 7504, 14, 15),     # 6 Eiko
    (509, 8307, 8316, 8312, 8310, 8314, 122, 0, 6, 23, 10, 21, 0, 8308, 15, 16),     # 7 Amarant
    (220, 2904, 2927, 2907, 2923, 2911, 50, 0, -1, -1, -1, -1, 0, 2905, 19, 19),     # 8 the MOOGLE
)
S139_NAMES = ("zidane", "vivi", "garnet", "steiner", "freya", "quina", "eiko", "amarant", "moogle")
#: calibration diffs that are KNOWN and do not bear on rows 9-12 (each says why)
CAL_EXPLAINED = {
    (0, "inactive"): "Zidane sets several break clips in stock (SetInactiveAnimation after SetModel(98): 54 x269, 55 x198, "
                     "57 x187, 56 x25, 59 x21); s139 took 57 from the kit's home-field extraction (playerswap.CHARACTERS) "
                     "and the audit calls it moot (a Zidane dress disarms). The modal rule picks 54. Rows 9-12 have NO "
                     "SetInactiveAnimation at all, so the ambiguity cannot reach them.",
}
S139_IDLE_FRAMES = [60, 45, 30, 60, 50, 40, 30, 45, 72]                            # audit 2.2 amendment 7 / leg G6
#: audit 2.3 amendment 12's offline frame table (idle, walk, run, turn_l, turn_r), keyed by rig
AUDIT_FRAMES = {"zidane": (60, 20, 18, 20, 20), "freya": (50, 24, 18, 20, 20), "vivi": (45, 20, 18, 20, 20),
                "garnet": (30, 20, 18, 20, 20), "steiner": (60, 20, 18, 20, 20), "quina": (40, 26, 22, 20, 20),
                "eiko": (30, 24, 20, 20, 20), "amarant": (45, 32, 24, 20, 20), "moogle": (72, 16, 10, 20, 20)}

# ------------------------------------------------------------------------------------------------ the 8-11 characters
#: CharacterId -> (rig index per O1, name, CharacterOldIndex -- the HW export's AddParty/IsInParty argument --, the
#: open-source name token, the candidate field models of that token: every GEO_* the kit's table holds for it)
CHARS = (
    (8, 9, "cinna", 9, "CNA"),
    (9, 10, "marcus", 10, "MRC"),
    (10, 11, "blank", 11, "BLN"),
    (11, 12, "beatrix", 8, "BTX"),
)
#: the party stretches the orchestrator names for the model pick (field-name prefixes, plus the opening's id band)
PARTY_STRETCH = {"cinna": "the disc-1 opening (Prima Vista, fields 50-69)",
                 "marcus": "the disc-1 opening + the disc-2 South Gate / Treno / Gargan Roo stretch",
                 "blank": "the disc-1 opening + Evil Forest",
                 "beatrix": "the disc-3 Alexandria defence (A. Castle / Alexandria)"}

LOCO_OPS = {"SetStandAnimation": "idle", "SetWalkAnimation": "walk", "SetRunAnimation": "run",
            "SetLeftAnimation": "turn_l", "SetRightAnimation": "turn_r", "SetInactiveAnimation": "inactive"}
SLOT_SUFFIX = {"idle": ("_IDLE",), "walk": ("_WALK",), "run": ("_RUN",), "turn_l": ("_TURN_L",), "turn_r": ("_TURN_R",)}
OP_RE = re.compile(r"^\s*(SetModel|SetStandAnimation|SetWalkAnimation|SetRunAnimation|SetLeftAnimation|SetRightAnimation|"
                   r"SetInactiveAnimation|RunModelCode|AddParty|IsInParty)\(\s*(.*?)\s*\)")
PARTY_RE = re.compile(r"\b(AddParty|IsInParty)\((\d+)\)")
LANG_RE = re.compile(r"^#HW language \S+\s*$")
ENTRY_RE = re.compile(r"^#HW newentry (\d+)")
FUNC_RE = re.compile(r"^Function (\S+)")
INT_RE = re.compile(r"^-?\d+$")


# ------------------------------------------------------------------------------------------------ the open-source tables
def source_table(path: Path, pattern: str) -> list:
    """[(id, name)] in SOURCE order -- the order TwoWayDictionary.Add sees them (the reverse key = the FIRST id)."""
    rx = re.compile(pattern)
    return [(int(m.group(1)), m.group(2)) for m in rx.finditer(path.read_text(encoding="utf-8-sig", errors="replace"))]


def load_tables(memoria: Path) -> dict:
    anim_src = source_table(memoria / "Assembly-CSharp" / "Global" / "ff9" / "FF9DBAll.Animation.cs",
                            r'\{\s*(\d+)\s*,\s*"(ANH_[A-Z0-9_]+)"\s*\}')
    geo_src = source_table(memoria / "Assembly-CSharp" / "Global" / "ff9" / "Battle" / "FF9BattleDB.GEO.cs",
                           r'\{\s*(\d+)\s*,\s*"(GEO_[A-Z0-9_]+)"\s*\}')
    anim, anim_first, anim_ids = {}, {}, collections.defaultdict(list)
    for i, n in anim_src:
        anim[i] = n
        anim_first.setdefault(n, i)
        anim_ids[n].append(i)
    geo, geo_first = {}, {}
    for i, n in geo_src:
        geo[i] = n
        geo_first.setdefault(n, i)
    from ff9mapkit._animdb_all import ANIMATIONS
    from ff9mapkit._modeldb import MODELS
    kit_mismatch = sorted(i for i in set(anim) | set(ANIMATIONS) if anim.get(i) != ANIMATIONS.get(i))
    geo_mismatch = sorted(i for i in set(geo) | set(MODELS) if geo.get(i) != MODELS.get(i))
    mf = (memoria / "Assembly-CSharp" / "Global" / "Model" / "ModelFactory.cs").read_text(encoding="utf-8-sig",
                                                                                          errors="replace")
    pair = re.compile(r'\{\s*"([A-Z0-9_]+)"\s*,\s*"([A-Z0-9_]+)"\s*\}')

    def str_table(name):
        m = re.search(name + r"\s*=\s*new Dictionary<String, String>\s*\{(.*?)\};", mf, re.S)
        return dict(pair.findall(m.group(1))) if m else {}

    return {"anim": anim, "anim_first": anim_first, "anim_ids": dict(anim_ids), "geo": geo, "geo_first": geo_first,
            "upscale": str_table("upscaleTable"), "revert_upscale": str_table("revertUpscaleTable"),
            "kit_anim_mismatch": kit_mismatch[:20], "kit_anim_mismatch_n": len(kit_mismatch),
            "kit_geo_mismatch": geo_mismatch[:20], "kit_geo_mismatch_n": len(geo_mismatch)}


def folder_of(clip: str | None) -> str | None:
    """NetSyncVisitor.FolderOf (s138), case for case: "GEO_" + tokens 1-3 of the '_'-split clip name."""
    if not clip:
        return None
    t = clip.split("_")
    return None if len(t) < 4 else f"GEO_{t[1]}_{t[2]}_{t[3]}"


# ------------------------------------------------------------------------------------------------ the exports
def manifest(path: Path) -> dict:
    out = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        p = line.split("\t")
        if len(p) >= 3 and p[0].startswith("test2_"):
            out[p[0]] = (int(p[1]), p[2])
    return out


def first_block(lines: list) -> list:
    """The export's FIRST language block: up to (not including) the second `#HW language <code>` header."""
    seen = 0
    for i, line in enumerate(lines):
        if LANG_RE.match(line):
            seen += 1
            if seen == 2:
                return lines[:i]
    return lines


def parse_export(path: Path) -> list:
    """[entry] for one export's first language block: {idx, funcs: [{name, ops: [(op, args, comment)]}]}."""
    lines = first_block(path.read_text(encoding="utf-8", errors="replace").splitlines())
    entries, cur, fn = [], None, None
    for line in lines:
        m = ENTRY_RE.match(line)
        if m:
            cur = {"idx": int(m.group(1)), "funcs": []}
            entries.append(cur)
            fn = None
            continue
        m = FUNC_RE.match(line)
        if m and cur is not None:
            fn = {"name": m.group(1), "ops": []}
            cur["funcs"].append(fn)
            continue
        if fn is None:
            continue
        body, _, comment = line.partition("//")
        if "DefinePlayerCharacter(" in body:
            fn["ops"].append(("DefinePlayerCharacter", [], ""))
        for pm in PARTY_RE.finditer(body):
            fn["ops"].append((pm.group(1), [pm.group(2)], ""))
        m = OP_RE.match(body)
        if m and m.group(1) not in ("AddParty", "IsInParty"):
            args = [a.strip() for a in m.group(2).split(",")] if m.group(2).strip() else []
            fn["ops"].append((m.group(1), args, comment.strip()))
    return entries


def ival(s):
    return int(s) if isinstance(s, str) and INT_RE.match(s) else None


def census_exports(exports: Path, man: dict) -> dict:
    """One pass over every export: per model the SetModel eyes + HW names + fields, the loco setters attributed to it,
    the footstep registrations per clip id, and the party ops per field."""
    files = sorted(exports.glob("test2_*.txt"), key=lambda p: int(p.stem.split("_")[1]))
    setmodel = collections.defaultdict(collections.Counter)       # model -> Counter(eye)
    hwname = collections.defaultdict(collections.Counter)         # model -> Counter(HW comment)
    fields = collections.defaultdict(collections.Counter)         # model -> Counter(field id)
    loco_init = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))   # model -> slot -> ids
    loco_any = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    entries_n = collections.Counter()                              # model -> entries that SetModel it
    steps = collections.defaultdict(list)                          # clip id -> [(code, frame, sound, field)]
    party = collections.defaultdict(lambda: collections.defaultdict(set))   # old idx -> op -> {field}
    player = collections.defaultdict(set)                          # model -> {field} where its entry is the PLAYER
    field_names = {}
    for f in files:
        fid, fname = man.get(f.name, (None, None))
        field_names[fid] = fname
        for e in parse_export(f):
            models_in_entry = set()
            for fn in e["funcs"]:
                for op, args, _c in fn["ops"]:
                    if op == "SetModel" and args and ival(args[0]) is not None:
                        models_in_entry.add(ival(args[0]))
            for m in models_in_entry:
                entries_n[m] += 1
            if any(op == "DefinePlayerCharacter" for fn in e["funcs"] for op, _a, _c in fn["ops"]):
                for m in models_in_entry:
                    player[m].add(fid)
            sole = next(iter(models_in_entry)) if len(models_in_entry) == 1 else None
            for fn in e["funcs"]:
                cur = None                                         # the most recent SetModel in THIS function
                for op, args, comment in fn["ops"]:
                    if op in ("AddParty", "IsInParty"):
                        party[int(args[0])][op].add(fid)
                        continue
                    if op == "SetModel":
                        m, eye = (ival(args[0]), ival(args[1])) if len(args) >= 2 else (None, None)
                        if m is not None:
                            setmodel[m][eye] += 1
                            hwname[m][comment] += 1
                            fields[m][fid] += 1
                            cur = m
                        continue
                    if op in LOCO_OPS:
                        a = ival(args[0]) if args else None
                        if a is None:
                            continue
                        slot = LOCO_OPS[op]
                        if cur is not None:
                            loco_init[cur][slot][a] += 1
                        owner = cur if cur is not None else sole
                        if owner is not None:
                            loco_any[owner][slot][a] += 1
                        continue
                    if op == "RunModelCode" and len(args) >= 4 and args[0] in ("16", "17"):
                        clip, frame, sound = ival(args[1]), ival(args[2]), ival(args[3])
                        if clip is not None:
                            steps[clip].append((int(args[0]), frame, sound, fid))
    return {"files": len(files), "setmodel": setmodel, "hwname": hwname, "fields": fields, "loco_init": loco_init,
            "loco_any": loco_any, "entries_n": entries_n, "steps": steps, "party": party, "player": player,
            "field_names": field_names}


# ------------------------------------------------------------------------------------------------ the derivations
def modal(counter: collections.Counter):
    return counter.most_common(1)[0][0] if counter else None


def clip_ids_by_name(tables: dict, name: str | None) -> list:
    return list(tables["anim_ids"].get(name, [])) if name else []


def step_census(cen: dict, tables: dict, clip_id: int | None) -> dict:
    """The footfall frames + sounds registered (RunModelCode 16/17) for a clip, over EVERY id naming it (the engine
    plays clips by name). frames16 = the RunModelCode(16) frame census (the footfall frames), frames17 the secondary."""
    name = tables["anim"].get(clip_id) if clip_id is not None else None
    ids = clip_ids_by_name(tables, name) or ([clip_id] if clip_id is not None else [])
    f16, f17, snd, by_id, fields = (collections.Counter(), collections.Counter(), collections.Counter(),
                                    collections.Counter(), set())
    for i in ids:
        for code, frame, sound, fid in cen["steps"].get(i, []):
            (f16 if code == 16 else f17)[frame] += 1
            snd[sound] += 1
            by_id[i] += 1
            fields.add(fid)
    return {"clip": clip_id, "name": name, "ids": ids, "frames16": dict(f16.most_common()),
            "frames17": dict(f17.most_common()), "sounds": dict(snd.most_common()), "by_id": dict(by_id),
            "fields": len(fields), "field_ids": sorted(f for f in fields if f is not None)}


def two_footfalls(sc: dict, frames_n: int | None) -> tuple:
    """(a, b, why): the two modal RunModelCode(16) frames, ascending, each inside the clip -- (-1, -1) when the clip
    registers none. The census rule: exactly two per clip; a third frame is an outlier (a computed-frame cutscene)."""
    c = collections.Counter({int(k): v for k, v in sc["frames16"].items() if k is not None})
    if not c:
        return -1, -1, "no RunModelCode(16) registration for any id of this clip"
    top = c.most_common()
    if len(top) == 1:
        return -1, -1, f"only ONE footfall frame registered ({top}) -- not the two-per-clip shape"
    a, b = sorted((top[0][0], top[1][0]))
    third = top[2][1] if len(top) > 2 else 0
    why = f"modal two of {top[:6]}"
    if third and third * 4 > top[1][1]:
        why += " -- WARNING: the third frame is not a clear outlier"
    if frames_n is not None and not (0 <= a < b < frames_n):
        why += f" -- WARNING: outside the clip's {frames_n} frames"
    return a, b, why


def step_sound(walk_sc: dict, run_sc: dict) -> tuple:
    """(override, why): the single sound id when EVERY registration (16 and 17, walk and run) uses one id (Steiner 925),
    else 0 (keep the source key's id)."""
    snd = collections.Counter(walk_sc["sounds"]) + collections.Counter(run_sc["sounds"])
    if not snd:
        return 0, "no footstep registration"
    if len(snd) == 1:
        (s, n), = snd.items()
        return int(s), f"every registration ({n}) uses {s}"
    return 0, f"{len(snd)} distinct sound ids {snd.most_common(6)}"


def alias_of(tables: dict, idle_id: int) -> tuple:
    """(alias, why): the OTHER AnimationDB id naming the idle's clip (lowest such id); 0 when there is none."""
    name = tables["anim"].get(idle_id)
    others = [i for i in clip_ids_by_name(tables, name) if i != idle_id]
    if not others:
        return 0, f"NO alias: {name} has only id {idle_id} -- amendment 4 needs a second id"
    return min(others), f"{name} ids {clip_ids_by_name(tables, name)}"


# ------------------------------------------------------------------------------------------------ the install
class Install:
    def __init__(self, game: Path):
        from ff9mapkit import extract as X
        from ff9mapkit.models import _gltf_io
        self.game = game
        self.X = X
        self.gl = _gltf_io
        self.p5 = X._unitypy().load(str(game / "StreamingAssets" / "p0data5.bin"))
        self.disc = _gltf_io.anim_disc_map(self.p5)
        self._skel_bundle = None

    def frames(self, model: int, anim_id: int | None) -> dict:
        """The clip a body of ``model`` plays for ``anim_id``: where it physically is (locate_animation: own folder, then
        the name-token folder, over every same-name id) and its frame count by GetCharAnimFrame's formula
        round(length x rate) + 1; plus the ENGINE PATH the dress uses (AddAnimWithAnimatioName / MeasureRigIdleFrames:
        Animations/<GEO.TryGetKey(FolderOf(name))>/<AnimationDB.TryGetKey(name)>) and whether that file exists."""
        from ff9mapkit import catalog
        if not anim_id:
            return {"id": anim_id, "frames": None}
        loc = catalog.locate_animation(anim_id, model, self.disc)
        out = {"id": anim_id, "located": list(loc) if loc else None, "frames": None}
        if loc:
            clip = self.gl.read_clip(self.p5, loc[1], loc[0])
            if clip is not None:
                out["frames"] = int(round(float(clip["length"]) * float(clip["sample_rate"] or 30.0))) + 1
                out["sample_rate"] = clip["sample_rate"]
        return out

    def engine_path(self, tables: dict, anim_id: int) -> dict:
        name = tables["anim"].get(anim_id)
        folder = folder_of(name)
        gid = tables["geo_first"].get(folder) if folder else None
        key = tables["anim_first"].get(name) if name else None
        present = gid is not None and key is not None and key in self.disc.get(gid, ())
        return {"name": name, "folder": folder, "folder_id": gid, "key": key, "on_disc": bool(present)}

    def skeleton(self, model: int) -> dict:
        """R_hand / R_hand_end off the prefab's skeleton. The labels are labels_for's (the baked family consensus + the
        per-prefab diffs) -- UNLESS that set names no R_hand, in which case the kit's live heuristic (label_skeleton, the
        rule labels_for itself falls back to for an unknown topology) answers, and the swap is recorded. A model with no
        R_hand_end label uses R_hand for both (the s139 Freya 12/12 and moogle 19/19 precedent). Each answer is checked
        against the geometry: R_hand sits on the +x side (Zidane's R_hand rests at x = +152.6), its parent is labelled
        R_forearm, and R_hand_end (when labelled) is R_hand's child."""
        from ff9mapkit.models import bone_labels as BL
        sk = BL.read_skeleton(str(int(model)), game=self.game, bundle=self._skel_bundle)
        self._skel_bundle = sk.get("bundle")
        bones = sk["bones"]
        consensus = BL.labels_for(bones, prefab_id=sk.get("prefab_id"), geo=sk.get("geo"))
        grp = str(sk.get("geo") or "").split("_")[1].lower() if "_" in str(sk.get("geo") or "") else None
        heuristic = BL.label_skeleton(bones, group=grp)
        source, labels = "labels_for", consensus
        if not any(lab == "R_hand" for lab in consensus.values()):
            source, labels = "label_skeleton (labels_for names no R_hand)", heuristic
        rh = sorted(n for n, lab in labels.items() if lab == "R_hand")
        rhe = sorted(n for n, lab in labels.items() if lab == "R_hand_end")
        parent = {BL.bone_num_lenient(b["name"]): BL.bone_num_lenient(b["parent"]) if b["parent"] else None
                  for b in bones}
        world = BL.rest_world(bones)
        hb = rh[0] if rh else None
        he = rhe[0] if rhe else hb
        geom = None
        if hb is not None:
            geom = (world.get(hb, (0.0,))[0] > 0 and labels.get(parent.get(hb)) == "R_forearm"
                    and (not rhe or parent.get(he) == hb))
        mesh_named = sorted({lab for lab in consensus.values() if re.match(r"^(hi|mesh|field_model)", str(lab))})
        return {"geo": sk.get("geo"), "prefab_id": sk.get("prefab_id"), "bones": len(bones), "labels_source": source,
                "R_hand": rh, "R_hand_end": rhe, "hand_bone": hb, "hand_bone_end": he, "end_fallback": not rhe,
                "geometry_ok": geom, "hand_world": [round(v, 1) for v in world.get(hb, ())] if hb is not None else None,
                "consensus_mesh_named_labels": mesh_named,
                "heuristic_hands": [sorted(n for n, lab in heuristic.items() if lab == "R_hand"),
                                    sorted(n for n, lab in heuristic.items() if lab == "R_hand_end")]}

    def model(self, model: int) -> dict:
        """GEO + texture stems (read_model) and the prefab's renderer tree (ModelFactory's field-mode hides)."""
        from ff9mapkit.models import extract as ME
        m = ME.read_model(str(int(model)), game=self.game)
        stems = sorted({str(x.get("texture")).split("_")[0] for x in m.get("materials", []) if x.get("texture")})
        geo, _gid, _tint, pgeo, pgid, _pt, b, root_pid = ME._open_prefab(str(int(model)), self.game)
        rends, subtrees = [], []

        def walk(tr_tt, path):
            if not tr_tt:
                return
            go = b.tt(ME._pid(tr_tt.get("m_GameObject", {})))
            if go and any(tn in ("SkinnedMeshRenderer", "MeshRenderer") for tn, _p in b.components(go)):
                rends.append(path)
            for ch in tr_tt.get("m_Children", []):
                ctt = b.tt(ME._pid(ch))
                cgo = b.tt(ME._pid(ctt.get("m_GameObject", {}))) if ctt else None
                nm = str(cgo.get("m_Name")) if cgo else "?"
                if nm in ("battle_model", "field_model", "long_hair", "short_hair"):
                    subtrees.append(nm)
                walk(ctt, f"{path}/{nm}" if path else nm)

        _tp, root_tr = b.transform_of(b.tt(root_pid))
        walk(root_tr, "")
        return {"geo": m.get("geo"), "prefab_geo": pgeo, "prefab_id": pgid, "texture_stems": stems,
                "renderers": rends, "mode_subtrees": sorted(set(subtrees))}

    def remaps(self, models, anims) -> list:
        out = []
        for folder in self.X._mod_folders(self.game):
            p = self.game / folder / "DictionaryPatch.txt"
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for line in text.splitlines():
                tok = line.split()
                if len(tok) < 3 or tok[0] not in ("3DModel", "3DModelAnimation"):
                    continue
                try:
                    ids = {int(t) for t in tok[1:-1]}
                except ValueError:
                    continue
                if ids & (models if tok[0] == "3DModel" else anims):
                    out.append([folder, line.strip()])
        return out


# ------------------------------------------------------------------------------------------------ a row
def derive_row(model: int, cen: dict, tables: dict, inst: Install) -> dict:
    """Every Rig column for ``model`` by the census rules, with the evidence behind each."""
    ev, row = {}, {"model": model}
    eyes = cen["setmodel"].get(model, collections.Counter())
    row["eye"] = modal(eyes)
    ev["eye"] = {"setmodel_n": sum(eyes.values()), "eyes": dict(eyes.most_common())}
    li, la = cen["loco_init"].get(model, {}), cen["loco_any"].get(model, {})
    names_ok = {}
    for slot in ("idle", "walk", "run", "turn_l", "turn_r"):
        c = li.get(slot) or collections.Counter()
        pick = modal(c)
        name = tables["anim"].get(pick) if pick is not None else None
        ok = bool(name) and name.endswith(SLOT_SUFFIX[slot]) and folder_of(name) == tables["geo"].get(model)
        row[slot] = pick
        names_ok[slot] = ok
        ev[slot] = {"init": dict(c.most_common(8)), "any_function": dict((la.get(slot) or {}).most_common(8))
                    if la.get(slot) else {}, "name": name, "name_ok": ok}
    inc = li.get("inactive") or collections.Counter()
    row["inactive"] = modal(inc) or 0
    ev["inactive"] = {"init": dict(inc.most_common(8)),
                      "any_function": dict((la.get("inactive") or collections.Counter()).most_common(8)),
                      "name": tables["anim"].get(row["inactive"]) if row["inactive"] else None}
    alias, why = alias_of(tables, row["idle"]) if row["idle"] is not None else (0, "no idle")
    row["idle_alias"] = alias
    ev["idle_alias"] = why
    fr = {s: inst.frames(model, row[s]) for s in ("idle", "walk", "run", "turn_l", "turn_r")}
    fr["inactive"] = inst.frames(model, row["inactive"]) if row["inactive"] else {"id": 0, "frames": None}
    fr["idle_alias"] = inst.frames(model, alias) if alias else {"id": 0, "frames": None}
    ws, rs = step_census(cen, tables, row["walk"]), step_census(cen, tables, row["run"])
    row["walk_step_a"], row["walk_step_b"], ev["walk_steps"] = two_footfalls(ws, fr["walk"]["frames"])
    row["run_step_a"], row["run_step_b"], ev["run_steps"] = two_footfalls(rs, fr["run"]["frames"])
    ev["walk_step_census"], ev["run_step_census"] = ws, rs
    row["step_sound"], ev["step_sound"] = step_sound(ws, rs)
    sk = inst.skeleton(model)
    row["hand_bone"], row["hand_bone_end"] = sk["hand_bone"], sk["hand_bone_end"]
    ev["skeleton"] = sk
    ev["frames"] = fr
    ev["engine_paths"] = {s: inst.engine_path(tables, row[s]) for s in ("idle", "walk", "run", "turn_l", "turn_r")
                          if row[s]}
    for extra in ("inactive", "idle_alias"):
        if row[extra]:
            ev["engine_paths"][extra] = inst.engine_path(tables, row[extra])
    ev["names_ok"] = names_ok
    ev["entries"] = cen["entries_n"].get(model, 0)
    ev["hw_names"] = dict(cen["hwname"].get(model, collections.Counter()).most_common(6))
    return {"row": [row[c] for c in COLUMNS], "cols": row, "evidence": ev}


def engine_create(model: int, cols: dict, tables: dict, inst: Install, facts: dict | None = None) -> dict:
    """Can the dress build this body in ANY field the way s139's ghost builds the moogle? ModelFactory.CreateModel(GEO):
    CheckUpscale (upscaleTable) then GetRenameModelPath (revertUpscaleTable, else the GEO name) -> GetGEOID ->
    Models/<type>/<id>/<id>, which must be the model's own shipped prefab; then every slot clip attached BY NAME
    (AddAnimWithAnimatioName: Animations/<GEO.TryGetKey(FolderOf(name))>/<AnimationDB.TryGetKey(name)>) must load off
    p0data5 -- with NO field EventAnimation list (an arbitrary field lists none of this model's clips). And
    ModelFactory's field-mode hide (battle_model) is what EnsureGhost's force-enable would undo (s139's rest mask)."""
    facts = facts or inst.model(model)
    geo = tables["geo"].get(model)
    up = tables["upscale"].get(geo, geo)
    back = tables["revert_upscale"].get(up, up)
    slots = ("idle", "walk", "run", "turn_l", "turn_r", "inactive", "idle_alias")
    paths = {s: inst.engine_path(tables, cols[s]) for s in slots if cols.get(s)}
    return {"geo": geo, "check_upscale": up, "rename_back": back, "rename_id": tables["geo_first"].get(back),
            "round_trip_same_id": tables["geo_first"].get(back) == model,
            "prefab": facts.get("prefab_geo"), "prefab_is_own": facts.get("prefab_id") == model,
            "texture_stems": facts.get("texture_stems"),
            "clip_folders": sorted({p["folder_id"] for p in paths.values()}),
            "every_clip_in_own_folder": all(p["folder_id"] == model for p in paths.values()),
            "every_clip_on_disc": all(p["on_disc"] for p in paths.values()),
            "missing": {s: f"Animations/{p['folder_id']}/{p['key']}" for s, p in paths.items() if not p["on_disc"]},
            "field_mode_hides_battle_model": "battle_model" in (facts.get("mode_subtrees") or []),
            "mode_subtrees": facts.get("mode_subtrees"), "renderers": facts.get("renderers")}


def area_histogram(cen: dict, model: int) -> dict:
    h = collections.Counter()
    for fid, n in cen["fields"].get(model, {}).items():
        nm = cen["field_names"].get(fid) or "?"
        h[nm.split("/")[0]] += n
    return dict(h.most_common())


def party_fields(cen: dict, old_idx: int) -> list:
    return sorted(f for f in cen["party"].get(old_idx, {}).get("AddParty", set()) if f is not None)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--game", default=None, help="the FF9 root (default: the kit's resolution)")
    ap.add_argument("--exports", default=str(DEFAULT_EXPORTS))
    ap.add_argument("--memoria", default=str(DEFAULT_MEMORIA))
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--check", action="store_true",
                    help="rebuild in memory and diff `rows` and `frames_13` against the frozen JSON (exit 1 on drift); "
                         "writes nothing")
    a = ap.parse_args(argv)
    from ff9mapkit import config
    game = config.find_game_path(a.game)
    tables = load_tables(Path(a.memoria))
    cen = census_exports(Path(a.exports), manifest(MANIFEST))
    inst = Install(game)
    out = {"tool": "studies/battle-coop/dress-census/rigs_8_11.py", "columns": list(COLUMNS),
           "sources": {"exports": f"{cen['files']} HW exports, first language block", "game": str(game),
                       "memoria_tables": "FF9DBAll.Animation.cs + FF9BattleDB.GEO.cs (source order)",
                       "kit": str(_KIT_AT.parent),
                       "kit_vs_memoria_anim_table": f"{tables['kit_anim_mismatch_n']} differing ids "
                                                    f"{tables['kit_anim_mismatch']}",
                       "kit_vs_memoria_geo_table": f"{tables['kit_geo_mismatch_n']} differing ids "
                                                   f"{tables['kit_geo_mismatch']}"},
           "rules": {"eye": "SetModel's modal eye byte over every SetModel of the model (po.eye = -4 * eye)",
                     "loco": "the modal SetStand/Walk/Run/Left/RightAnimation id among the setters that FOLLOW a "
                             "SetModel(model) in the same function; name-checked (_IDLE/_WALK/_RUN/_TURN_L/_TURN_R, "
                             "FolderOf == the model's GEO)",
                     "inactive": "the modal SetInactiveAnimation in those same blocks; 0 = none (p.sleep == 0)",
                     "footfalls": "the two modal RunModelCode(16, clip, frame) frames over every id naming the "
                                  "walk / run clip; -1/-1 when none",
                     "step_sound": "the single sound id when every 16/17 registration of the walk+run clips uses "
                                   "one id, else 0",
                     "idle_alias": "the lowest OTHER AnimationDB id naming the idle's clip",
                     "hands": "bone_labels.labels_for: R_hand; R_hand_end, or R_hand when the skeleton has none "
                              "labelled",
                     "frames": "p0data5 clip at catalog.locate_animation's folder, round(length x rate) + 1"},
           "calibration": {}, "candidates": {}, "rows": {}, "frames_13": {}, "open_issues": []}

    # ---- 1. calibrate on rows 0-8: the census rules must reproduce s139's table
    cal_ok = True
    for i, ref in enumerate(S139_ROWS):
        d = derive_row(ref[0], cen, tables, inst)
        diffs = {c: {"s139": ref[k], "census": d["row"][k]} for k, c in enumerate(COLUMNS) if ref[k] != d["row"][k]}
        sk = d["evidence"]["skeleton"]
        out["calibration"][f"{i} {S139_NAMES[i]}"] = {
            "diffs": diffs,
            "explained": {c: CAL_EXPLAINED[(i, c)] for c in diffs if (i, c) in CAL_EXPLAINED},
            "evidence": {s: d["evidence"][s] for s in ("idle", "walk", "run", "turn_l", "turn_r", "inactive")
                         if s in diffs},
            "hands": {"labels_source": sk["labels_source"], "geometry_ok": sk["geometry_ok"],
                      "heuristic_hands": sk["heuristic_hands"]},
            "frames": {s: d["evidence"]["frames"][s]["frames"] for s in ("idle", "walk", "run", "turn_l", "turn_r")}}
        if any((i, c) not in CAL_EXPLAINED for c in diffs):
            cal_ok = False
    out["calibration_reproduces_s139"] = cal_ok
    out["calibration_note"] = ("every column of rows 0-8 reproduced by the rules above except the explained diffs "
                               "(CAL_EXPLAINED); none of them bears on rows 9-12")

    # ---- 2. the 8-11 candidates and the pick
    for char_id, rig, name, old, token in CHARS:
        cands = sorted(m for m, g in tables["geo"].items() if g.split("_")[1:2] == ["SUB"] and g.endswith("_" + token)
                       and g.split("_")[2].startswith("F"))
        pf = party_fields(cen, old)
        info = {}
        for m in cands:
            g = tables["geo"][m]
            loco_names = {s: sorted(i for n, ids in tables["anim_ids"].items() if n == f"ANH_{g[4:]}{suf[0]}"
                                    for i in ids) for s, suf in SLOT_SUFFIX.items()}
            info[str(m)] = {"geo": g, "setmodel_n": sum(cen["setmodel"].get(m, {}).values()),
                            "eyes": dict(cen["setmodel"].get(m, collections.Counter()).most_common()),
                            "entries": cen["entries_n"].get(m, 0),
                            "fields_n": len(cen["fields"].get(m, {})),
                            "areas": area_histogram(cen, m),
                            "hw_names": dict(cen["hwname"].get(m, collections.Counter()).most_common(4)),
                            "party_fields_worn": sorted(f for f in pf if f in cen["fields"].get(m, {})),
                            "opening_50_69_worn": sorted(f for f in cen["fields"].get(m, {}) if f and 50 <= f <= 69),
                            "player_entry_fields": sorted(f for f in cen["player"].get(m, set()) if f is not None),
                            "full_loco_set_in_animdb": all(loco_names.values()),
                            "loco_ids_by_name": loco_names}
        out["candidates"][name] = {"char_id": char_id, "rig": rig, "old_index": old, "token": token,
                                   "add_party_fields": pf, "stretch": PARTY_STRETCH[name], "models": info}

    picks = {}
    for char_id, rig, name, old, token in CHARS:
        info = out["candidates"][name]["models"]
        full = {m: v for m, v in info.items() if v["full_loco_set_in_animdb"]}
        # the pick: a full loco set, then the most party fields worn, then the most SetModels
        best = max(full, key=lambda m: (len(full[m]["party_fields_worn"]), full[m]["setmodel_n"])) if full else None
        picks[name] = int(best) if best else None
        out["candidates"][name]["pick"] = picks[name]
        why = []
        for mm, v in sorted(info.items(), key=lambda kv: -kv[1]["setmodel_n"]):
            why.append(f"{mm} {v['geo']} ({'/'.join(v['hw_names'])}): {v['setmodel_n']} SetModels in {v['fields_n']} "
                       f"fields, worn in AddParty fields {v['party_fields_worn']}, full loco set "
                       f"{v['full_loco_set_in_animdb']}")
        out["candidates"][name]["pick_why"] = (f"pick {picks[name]}: a full loco set, then the most AddParty fields "
                                               f"worn, then the most SetModels -- " + "; ".join(why))
        if best is None:
            out["open_issues"].append(f"{name}: no candidate model has a full loco set")

    # ---- 3. the rows
    for char_id, rig, name, old, token in CHARS:
        m = picks[name]
        if m is None:
            continue
        d = derive_row(m, cen, tables, inst)
        ev = d["evidence"]
        fb = []
        for slot in ("idle", "walk", "run", "turn_l", "turn_r"):
            if d["cols"][slot] is None:
                fb.append(f"{slot}: NO stock setter -- needs a documented fallback")
            elif not ev["names_ok"][slot]:
                fb.append(f"{slot}: {d['cols'][slot]} is named {ev[slot]['name']!r} (not the slot's name)")
        for slot, p in ev["engine_paths"].items():
            if not p["on_disc"]:
                fb.append(f"{slot}: the engine's load path Animations/{p['folder_id']}/{p['key']} is NOT on disc")
        for slot in ("idle", "walk", "run", "turn_l", "turn_r"):
            if ev["frames"][slot]["frames"] is None:
                fb.append(f"{slot}: no frame count (clip not located in p0data5)")
        if not d["cols"]["idle_alias"]:
            fb.append("idle_alias: NONE -- amendment 4 needs an alias id")
        sk = ev["skeleton"]
        notes = []
        if sk["hand_bone"] is None:
            fb.append("hand_bone: no R_hand found by either label source")
        elif not sk["geometry_ok"]:
            fb.append(f"hand bones {sk['hand_bone']}/{sk['hand_bone_end']} fail the geometry check")
        if sk["end_fallback"]:
            notes.append("hand_bone_end: no R_hand_end label -- R_hand used (the Freya / moogle precedent)")
        if sk["labels_source"] != "labels_for":
            notes.append(f"hands from the kit's live heuristic: labels_for (the baked family consensus) names no R_hand "
                         f"for this topology and carries mesh-node names as bone labels {sk['consensus_mesh_named_labels']}"
                         f" -- a kit _bonelabeldb defect; geometry_ok={sk['geometry_ok']}, R_hand at {sk['hand_world']}")
        if d["cols"]["walk_step_a"] < 0 and d["cols"]["run_step_a"] < 0:
            notes.append("no stock footstep registration for its walk or run clip (the Quina / moogle precedent): -1/-1")
        fr = ev["frames"]
        if fr["idle"]["frames"] is not None:
            notes.append(f"idle {fr['idle']['frames']} frames: {'a SHORT idle (< 58, wedges without KeepSourceTimeline)' if fr['idle']['frames'] < 58 else 'not short'}"
                         f"; above ZDN jump1 24 (amendment 10's frame-safety holds: {fr['idle']['frames'] > 24})")
        if fr["walk"]["frames"] is not None:
            notes.append(f"walk {fr['walk']['frames']} frames: 2705's GetAnimDuration(8847) - 1 = 39 is "
                         f"{'REACHABLE' if fr['walk']['frames'] - 1 >= 39 else 'unreachable'} natively (the B_FRAME law)")
        facts = inst.model(m)
        ec = engine_create(m, d["cols"], tables, inst, facts)
        if not (ec["round_trip_same_id"] and ec["prefab_is_own"] and ec["every_clip_on_disc"]):
            fb.append(f"engine create path: {ec}")
        if ec["field_mode_hides_battle_model"]:
            notes.append("the prefab has a battle_model subtree ModelFactory hides in field mode: s139's rest mask matters")
        out["rows"][str(rig)] = {"char_id": char_id, "name": name, "row": d["row"], "cols": d["cols"],
                                 "model_facts": facts, "engine_create": ec, "evidence": ev, "issues": fb,
                                 "notes": notes}
        out["open_issues"] += [f"rig {rig} {name}: {x}" for x in fb]

    # ---- 4. the 13-row frame table (rows 0-8 from s139's ids, 9-12 from the census)
    rows13 = [(i, S139_NAMES[i], r) for i, r in enumerate(S139_ROWS)]
    rows13 += [(int(k), v["name"], v["row"]) for k, v in sorted(out["rows"].items(), key=lambda kv: int(kv[0]))]
    for i, nm, r in rows13:
        model = r[0]
        cols = dict(zip(COLUMNS, r))
        fr = {s: inst.frames(model, cols[s])["frames"] for s in ("idle", "walk", "run", "turn_l", "turn_r")}
        fr["inactive"] = inst.frames(model, cols["inactive"])["frames"] if cols["inactive"] else None
        fr["idle_alias"] = inst.frames(model, cols["idle_alias"])["frames"] if cols["idle_alias"] else None
        out["frames_13"][str(i)] = {"name": nm, **fr}
        if i < 9:                                          # the reference rows: the same create-path check
            ec = engine_create(model, cols, tables, inst)
            out.setdefault("engine_create_0_8", {})[str(i)] = {k: ec[k] for k in (
                "geo", "round_trip_same_id", "prefab_is_own", "every_clip_in_own_folder", "every_clip_on_disc",
                "missing", "field_mode_hides_battle_model", "mode_subtrees")}
    idle9 = [out["frames_13"][str(i)]["idle"] for i in range(9)]
    out["frames_check"] = {"rig_idle_frames_0_8": idle9, "s139_oracle": S139_IDLE_FRAMES,
                           "match": idle9 == S139_IDLE_FRAMES,
                           "audit_table_diffs": {nm: {"audit": AUDIT_FRAMES[nm], "census": tuple(
                               out["frames_13"][str(i)][s] for s in ("idle", "walk", "run", "turn_l", "turn_r"))}
                               for i, nm in enumerate(S139_NAMES) if AUDIT_FRAMES[nm] != tuple(
                               out["frames_13"][str(i)][s] for s in ("idle", "walk", "run", "turn_l", "turn_r"))},
                           "rig_idle_frames_13": [out["frames_13"][str(i)]["idle"] for i in range(len(rows13))]}
    if not out["frames_check"]["match"]:
        out["open_issues"].append(f"rows 0-8 idle frames {idle9} != s139's oracle {S139_IDLE_FRAMES}")
    if out["frames_check"]["audit_table_diffs"]:
        out["open_issues"].append(f"amendment 12's table differs: {out['frames_check']['audit_table_diffs']}")
    # the frame-safety claims s140 leans on (audit 2.3 amendments 1, 7, 10) for the new rows
    for k, v in sorted(out["rows"].items(), key=lambda kv: int(kv[0])):
        f = out["frames_13"][k]
        if f["idle"] is not None and f["idle"] <= 24:
            out["open_issues"].append(f"rig {k} {v['name']}: idle {f['idle']} frames <= ZDN jump1 24 (amendment 10's "
                                      f"frame-safety claim fails)")
    all_loco = {r[s] for _i, _n, r in rows13 for s in (1, 2, 3, 4, 5, 7, 13) if r[s]}
    all_models = {r[0] for _i, _n, r in rows13}
    out["remaps"] = inst.remaps(all_models, all_loco)
    if out["remaps"]:
        out["open_issues"].append(f"DictionaryPatch remaps touch a rig model / clip: {out['remaps']}")
    if a.check:
        frozen = json.loads(Path(a.out).read_text(encoding="utf-8"))
        fresh = json.loads(json.dumps(out, default=str))              # the JSON form the file holds
        drift = [k for k in ("rows", "frames_13") if fresh.get(k) != frozen.get(k)]
        for k in drift:
            print(f"DRIFT {k}: frozen {json.dumps(frozen.get(k))[:600]}")
            print(f"      fresh  {json.dumps(fresh.get(k))[:600]}")
        if drift:
            return 1
        print(f"OK: rows 9-12 and frames_13 regenerate exactly from the install ({Path(a.out).name})")
        return 0
    Path(a.out).write_text(json.dumps(out, indent=1, sort_keys=False, default=str) + "\n", encoding="utf-8")
    # a terse summary
    print(f"exports: {cen['files']}; calibration reproduces s139: {cal_ok}")
    for k, v in out["calibration"].items():
        if v["diffs"]:
            print(f"  CAL {k}: {v['diffs']}")
    for name, c in out["candidates"].items():
        print(f"{name}: pick {c['pick']}; " + "; ".join(f"{m} {v['geo']} n={v['setmodel_n']} party={v['party_fields_worn']}"
                                                      for m, v in c["models"].items()))
    for k, v in sorted(out["rows"].items(), key=lambda kv: int(kv[0])):
        print(f"rig {k} {v['name']}: {v['row']}")
        for n in v["notes"]:
            print("   note:", n)
    print("frames_13:", json.dumps(out["frames_13"]))
    print("frames_check:", json.dumps(out["frames_check"]))
    for x in out["open_issues"]:
        print("ISSUE:", x)
    print("wrote", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
