"""LEG F's OFFLINE ORACLE CENSUS for s141, THE DRESS POLISH (R3-FIELD-MODEL-AUDIT.md 2.4 amendments 1-6, section 4.5).

Re-derives -- never trusts -- every number the audit gives for s141 and writes the oracle leg F judges against:

  (a) FIELD 250's footsteps: the player entry's CHRFX 16-19 ops at a load (Zidane_Init) and at Main_Reinit
      (RunScriptAsync(0, 250, 13) -> Zidane_13), and, through MapFootstep's Python twin (orchestrator O4) over the
      LIVE rig table (NetSyncVisitor.Rigs, all 13 rows, parsed out of the Memoria clone), the expected
      `netsync.dress.self.steps` triples and steps_dropped / steps_passed per field load for EVERY rig.
  (b) THE RIG STEP COLUMNS against stock: the RunModelCode(16/17) census over all 817 exports (first language block)
      per rig walk/run clip id -- frames, field counts, sound ids -- and Zidane's per-field sound-id reuse.
  (c) CINNA (O1): no CHRFX 16-19 registration on any CNA body; Marcus / Blank / Beatrix registrations (rows 10-12).
  (d) LIGHTING: field 250's MapConfigData rows and lights through ff9mapkit.mapconfig.parse, the `_Color` oracle per
      floor under the 98 row (the s141 fallback) and the default row (s140 / polish off) as PURE functions the bench
      imports (light_color / ghost_light_color), and the fallback's reach over all 818 MCFs per rig model.
  (e) HAND BONES: per rig, the table's HandBone / HandBoneEnd as the engine's bone NAMES ("bone%03d"), the skeleton's
      bone count (models.bone_labels.read_skeleton), labels_for's R_hand / R_hand_end, and what bones 12 / 13 are.
  (f) THE ATTACH CENSUS: every AttachObject (0x4C) whose CARRYING object is a Zidane player entry (SetModel 98 +
      DefinePlayerCharacter) or 250.
  (g) THE MESH-OP CENSUS: every ShowObject / HideObject (0x39 / 0x3A) whose target is a player entry's object or 250.

READ-ONLY. Sources: the 817 Hades Workshop exports (``--exports``; test2_N.txt, N = HW index; the repo's
reference/field-manifest.tsv maps it to the field id), first language block only; the Memoria clone (``--memoria``:
NetSyncVisitor.cs for the rig table, FF9DBAll.Animation.cs / FF9BattleDB.GEO.cs for open-source names); the install
through THIS worktree's kit readers (mapconfig.parse over the event bundle's MapConfigData; bone_labels.read_skeleton
/ labels_for / label_skeleton over p0data4). The output holds numbers and open-source names only -- zero game bytes,
no script text.

    py -X utf8 studies/battle-coop/dress-census/polish_census.py            # (re)write polish.json
    py -X utf8 studies/battle-coop/dress-census/polish_census.py --check    # rebuild in memory, diff the oracle keys

THE PURE TWINS (importable; no install needed): map_footstep, expected_steps, remap_attach_bone, light_color,
ghost_light_color, parse_rigs. ``load_mcf(field_id)`` reads one field's MCF through the kit for the bench's F4.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
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
# THIS tree's kit, wherever the tree is (a worktree, the main repo, the nightly gate): the census tests import the pure twins
# from it (ff9mapkit/tests/test_dress_polish_census.py), so the pin is the tree, never a worktree path (rigs_8_11.py's form)
assert _KIT_AT.is_relative_to(PKG.resolve()), f"ff9mapkit resolved to {_KIT_AT}, not this tree's {PKG}"

DEFAULT_EXPORTS = Path(r"C:\gd\FFIX\reference\test2")
DEFAULT_MEMORIA = Path(r"C:\gd\FFIX\Memoria")
MANIFEST = REPO / "reference" / "field-manifest.tsv"
OUT = HERE / "polish.json"
VISITOR = Path("Assembly-CSharp") / "Memoria" / "Netsync" / "NetSyncVisitor.cs"

COLUMNS = ("model", "idle", "walk", "run", "turn_l", "turn_r", "eye", "inactive", "walk_step_a", "walk_step_b",
           "run_step_a", "run_step_b", "step_sound", "idle_alias", "hand_bone", "hand_bone_end")
RIG_NAMES = ("zidane", "vivi", "garnet", "steiner", "freya", "quina", "eiko", "amarant", "moogle",
             "cinna", "marcus", "blank", "beatrix")
DEFAULT_ROW = 0xFFFF                                    # the MCF's default DMSMapChar row (65535)
DRESS_SRC = 98                                          # PosObj.netDressSrc on a dressed body (s140)
FOOTSTEP_CODES = (16, 17, 18, 19)
PLAYER_UID = 250                                        # "Player Character" (GetObjUID -> the control char)
THIS_UID = 255                                          # "This" (the executing object)


# ================================================================================================ the live rig table
def parse_rigs(memoria: Path = DEFAULT_MEMORIA) -> list:
    """NetSyncVisitor.Rigs out of the clone, row for row (13 rows on s140): [{col: int}] in table order."""
    text = (Path(memoria) / VISITOR).read_text(encoding="utf-8-sig", errors="replace")
    m = re.search(r"private static readonly Rig\[\] Rigs\s*=\s*\{(.*?)\n\s*\};", text, re.S)
    if not m:
        raise SystemExit(f"no `Rigs` table in {Path(memoria) / VISITOR}")
    rows = []
    for rm in re.finditer(r"new Rig\(([^)]*)\)", m.group(1)):
        vals = [int(v) for v in rm.group(1).split(",")]
        if len(vals) != len(COLUMNS):
            raise SystemExit(f"a Rig row has {len(vals)} values, not {len(COLUMNS)}: {rm.group(0)}")
        rows.append(dict(zip(COLUMNS, vals)))
    return rows


def visitor_sha(memoria: Path = DEFAULT_MEMORIA) -> str:
    return hashlib.sha256((Path(memoria) / VISITOR).read_bytes()).hexdigest()[:16]


# ================================================================================================ (a) MapFootstep's twin
def map_footstep(rig: dict, code: int, anim: int, frame: int, arg4: int, zidane: dict | None = None) -> tuple:
    """Orchestrator O4, the pure rule: (verdict, anim', frame', arg4') for one CHRFX op on a DRESSED body.

    verdict is "untouched" (a code other than 16-19: never mapped), "pass" (16-19 on any anim other than Zidane's walk
    25 / run 38, or a frame outside Zidane's pair -- counted steps_passed, sent through unchanged), "drop" (a Zidane
    walk/run key at a pair frame on a rig whose pair for that slot is -1 -- the moogle, Quina, Cinna -- counted
    steps_dropped, codes 16, 17, 18 AND 19 alike), or "map" (the same ordinal in the rig's pair, anim -> rig.walk /
    rig.run). The sound arg on a map: rig.step_sound when non-zero, ON CODES 16 AND 17 ONLY (sndEffectID[0] / [1], the
    "both slots"); code 18's Arg4 is the random-pitch FLAG (fldchar.cs: pitchRand = Arg4 == 0 ? 0 : 1) and 19's Arg4
    is unused, so both keep the source's Arg4 (see the JSON's open_issues: O4's wording does not say this)."""
    z = zidane or {"walk": 25, "run": 38, "walk_step_a": 4, "walk_step_b": 13, "run_step_a": 0, "run_step_b": 8}
    if code not in FOOTSTEP_CODES:
        return ("untouched", anim, frame, arg4)
    if anim == z["walk"]:
        src, dst_anim, dst = (z["walk_step_a"], z["walk_step_b"]), rig["walk"], (rig["walk_step_a"], rig["walk_step_b"])
    elif anim == z["run"]:
        src, dst_anim, dst = (z["run_step_a"], z["run_step_b"]), rig["run"], (rig["run_step_a"], rig["run_step_b"])
    else:
        return ("pass", anim, frame, arg4)
    if frame not in src:
        return ("pass", anim, frame, arg4)
    if dst[0] < 0 or dst[1] < 0:
        return ("drop", anim, frame, arg4)
    snd = rig["step_sound"] if (rig["step_sound"] and code in (16, 17)) else arg4
    return ("map", dst_anim, dst[src.index(frame)], snd)


def expected_steps(rig: dict, ops: list, polish: bool = True, dressed: bool = True, zidane: dict | None = None) -> dict:
    """Replay one field load's CHRFX ops (code, anim, frame, arg4 -- in script order) on ONE body through stock's
    FF9Snd table semantics (fldchar.cs:123-149 + FF9Snd.cs GetChar/NewChar/DeleteChar), after MapFootstep when the
    body is dressed and the polish lever is on. Returns the table rows in insertion order ([anim, frame, snd0, snd1,
    pitch]), the published `steps` triples ([anim, frame, sndEffectID[0]]) and the per-load counters."""
    table, dropped, passed, faults = [], 0, 0, []
    for code, anim, frame, arg4 in ops:
        if code not in FOOTSTEP_CODES:
            continue
        if dressed and polish:
            verdict, anim, frame, arg4 = map_footstep(rig, code, anim, frame, arg4, zidane)
            if verdict == "drop":
                dropped += 1
                continue
            if verdict == "pass":
                passed += 1
        rec = next((r for r in reversed(table) if r[0] == anim and r[1] == frame), None)
        if code == 19:
            if not table:
                faults.append(f"code 19 on ({anim}, {frame}) with an EMPTY table: stock DeleteChar indexes "
                              f"charSoundArray[-1] and throws")
            else:
                # engine-exact: DeleteChar only does charSoundUse-- per matching record (it never moves one), so the
                # TOP records leave the live range whichever record matched
                hits = sum(1 for r in table if r[0] == anim and r[1] == frame)
                if hits:
                    del table[len(table) - hits:]
            continue
        if rec is None:
            rec = [anim, frame, 0, 0, 0]
            table.append(rec)
        if code == 16:
            rec[2] = arg4 & 0xFFFF
        elif code == 17:
            rec[3] = arg4 & 0xFFFF
        else:
            rec[4] = 0 if arg4 == 0 else 1
    return {"steps": [[r[0], r[1], r[2]] for r in table], "table": [list(r) for r in table],
            "steps_dropped": dropped, "steps_passed": passed, "faults": faults}


def remap_attach_bone(rig: dict, bone: int, polish: bool = True) -> tuple:
    """Orchestrator O6, the pure rule on a DRESSED carrier: (bone', verdict) -- 12 -> rig.hand_bone and
    13 -> rig.hand_bone_end ("remap", counted attach_remaps), any other bone unchanged ("note", attach_notes);
    the polish lever off bypasses it ("bypass")."""
    if not polish:
        return (bone, "bypass")
    if bone == 12:
        return (rig["hand_bone"], "remap")
    if bone == 13:
        return (rig["hand_bone_end"], "remap")
    return (bone, "note")


# ================================================================================================ (d) the lighting twins
def _char_row(mcf, model: int):
    return mcf.char(model)


def _floor_light(mcf, floor: int):
    """ff9fieldMCFGetLightByCharFloor: None when lightUse == 0 or floor & 255 == 255; else the HIGHEST-index type-0
    light (within lightUse) one of whose four floor bytes (& 255) names the floor."""
    if mcf.light_use == 0 or (floor & 255) == 255:
        return None
    for lt in reversed(mcf.lights[:mcf.light_use]):
        if lt.type == 0 and any((f & 255) == (floor & 255) for f in reversed(lt.floor)):
            return lt
    return None


def _rgb(char_clr, light_clr) -> list:
    """fldmcf.cs: (Byte)((Int32)clr[i] + (Int32)light[i] << 3) -- '+' binds before '<<', then an unchecked Byte cast."""
    return [((int(char_clr[i]) + int(light_clr[i])) << 3) & 0xFF for i in range(3)]


def light_color(mcf, model: int, floor: int, dress_src: int = 0, polish: bool = True, ladder: bool = False) -> dict:
    """fldmcf.ff9fieldMCFService for ONE actor, plus s141's fallback (O8): the actor's own po.model row; when missing
    and the body is dressed (dress_src != 0, the lever on) the dress_src (98) row; else the default 0xFFFF row. The
    light: the ladder light when the actor is on a ladder (attr & 4) and one exists, else its floor's light, else the
    type-1 default light, else zeros. Returns {row, rgb, light} -- row = the model id of the row used (65535 = the
    default row), rgb = the [r, g, b] ints fldchar.cs writes into every material's `_Color`."""
    if mcf is None:
        return {"row": -1, "rgb": None, "light": None}               # a kit field: the service returns at its top
    row, used = _char_row(mcf, model), model & 0xFFFF
    if row is None and polish and dress_src:
        row, used = _char_row(mcf, dress_src), dress_src
    if row is None:
        row, used = _char_row(mcf, DEFAULT_ROW), DEFAULT_ROW
    if row is None:
        return {"row": None, "rgb": None, "light": None}             # stock would throw (no shipping MCF lacks it)
    ladder_lt = next((lt for lt in mcf.lights[:mcf.light_use] if lt.type == 2), None) if ladder else None
    lt = ladder_lt or _floor_light(mcf, floor) or mcf.default_light()
    lclr = lt.clr if lt is not None else (0, 0, 0, 0)
    kind = None if lt is None else ("ladder" if lt is ladder_lt else ("floor" if lt.type == 0 else "default"))
    return {"row": used, "rgb": _rgb(row.clr, lclr), "light": kind, "char_clr": list(row.clr[:3]),
            "light_clr": list(lclr[:3])}


def ghost_light_color(mcf, ghost_model: int, lp_model: int, lp_floor: int, lp_dress_src: int = 0,
                      polish: bool = True) -> dict:
    """NetSyncClient.ApplyGhostLighting with s141's fallback (O8): the GHOST model's row, else the LOCAL player's row
    -- (lp.netDressSrc != 0 ? lp.netDressSrc : lp.model) on s141, lp.model on s140 / polish off --, else the default
    row; the light = the local player's floor light, else the default light (no ladder case). {row, rgb}."""
    if mcf is None:
        return {"row": -1, "rgb": None}
    row, used = _char_row(mcf, ghost_model), ghost_model & 0xFFFF
    if row is None:
        lp_row = lp_dress_src if (polish and lp_dress_src) else lp_model
        row, used = _char_row(mcf, lp_row), lp_row & 0xFFFF
    if row is None:
        row, used = _char_row(mcf, DEFAULT_ROW), DEFAULT_ROW
    if row is None:
        return {"row": None, "rgb": None}
    lt = _floor_light(mcf, lp_floor) or mcf.default_light()
    return {"row": used, "rgb": _rgb(row.clr, lt.clr if lt is not None else (0, 0, 0, 0))}


def mcf_index(game=None) -> dict:
    """{EVT_name_lower: MCF bytes} straight out of the field event bundle (the kit's _regen_shadowparams reader)."""
    from ff9mapkit import extract
    env = extract._load_env(extract._streaming_assets(game) / extract._events_bundle(game))
    marker = "commonasset/mapconfigdata/"
    out = {}
    for k, obj in env.container.items():
        kl = k.lower()
        i = kl.find(marker)
        if i >= 0 and kl.endswith(".bytes"):
            out[kl[i + len(marker):-len(".bytes")]] = extract._raw_bytes(obj.read())
    return out


def load_mcf(field_id: int, game=None, index: dict | None = None):
    """One field's parsed MapConfigData (ff9mapkit.mapconfig.MapConfig), or None (a kit field / no MCF)."""
    from ff9mapkit import extract, mapconfig
    evt = extract.ID_TO_EVT.get(int(field_id))
    if not evt:
        return None
    idx = index if index is not None else mcf_index(game)
    data = idx.get(str(evt).lower())
    return mapconfig.parse(data) if data else None


# ================================================================================================ the exports
OP_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\(\s*(.*?)\s*\)\s*(?://\s*(.*))?$")
LANG_RE = re.compile(r"^#HW language \S+\s*$")
ENTRY_RE = re.compile(r"^#HW newentry (\d+)")
NEWFUNC_RE = re.compile(r"^#HW newfunction (\d+)")
FUNC_RE = re.compile(r"^Function (\S+)")
INT_RE = re.compile(r"^-?\d+$")
KEEP_OPS = {"SetModel", "DefinePlayerCharacter", "InitObject", "RunModelCode", "AttachObject", "ShowObject",
            "HideObject", "RunScript", "RunScriptAsync", "RunScriptSync", "DetachObject"}


def ival(s):
    return int(s) if isinstance(s, str) and INT_RE.match(s.strip()) else None


def split_args(s: str) -> list:
    out, depth, cur = [], 0, []
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            out.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    if "".join(cur).strip():
        out.append("".join(cur).strip())
    return out


def manifest(path: Path = MANIFEST) -> dict:
    out = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        p = line.split("\t")
        if len(p) >= 3 and p[0].startswith("test2_"):
            out[p[0]] = (int(p[1]), p[2])
    return out


def first_block(lines: list) -> list:
    seen = 0
    for i, line in enumerate(lines):
        if LANG_RE.match(line):
            seen += 1
            if seen == 2:
                return lines[:i]
    return lines


def parse_export(path: Path) -> list:
    """[entry] of one export's first language block: {idx, funcs: [{name, tag, ops: [(op, args, comment, line)]}]}."""
    lines = first_block(path.read_text(encoding="utf-8", errors="replace").splitlines())
    entries, cur, fn, tag = [], None, None, None
    for n, line in enumerate(lines, 1):
        m = ENTRY_RE.match(line)
        if m:
            cur = {"idx": int(m.group(1)), "funcs": []}
            entries.append(cur)
            fn = tag = None
            continue
        m = NEWFUNC_RE.match(line)
        if m:
            tag = int(m.group(1))
            continue
        m = FUNC_RE.match(line)
        if m and cur is not None:
            fn = {"name": m.group(1), "tag": tag, "ops": []}
            cur["funcs"].append(fn)
            continue
        if fn is None:
            continue
        m = OP_RE.match(line)
        if m and m.group(1) in KEEP_OPS:
            fn["ops"].append((m.group(1), split_args(m.group(2)), (m.group(3) or "").strip(), n))
    return entries


class Export:
    """One parsed export with its entry facts: models per entry, the player-defining entries, the uid map."""

    def __init__(self, path: Path, fid, fname):
        self.path, self.fid, self.fname = path, fid, fname
        self.entries = parse_export(path)
        self.by_idx = {e["idx"]: e for e in self.entries}
        self.models, self.dpc = {}, set()
        self.uid_entries = collections.defaultdict(set)
        for e in self.entries:
            ms = set()
            for f in e["funcs"]:
                for op, args, _c, _n in f["ops"]:
                    if op == "SetModel" and args and ival(args[0]) is not None:
                        ms.add(ival(args[0]))
                    elif op == "DefinePlayerCharacter":
                        self.dpc.add(e["idx"])
                    elif op == "InitObject" and len(args) >= 2 and ival(args[0]) is not None:
                        u = ival(args[1])
                        self.uid_entries[u if u else ival(args[0])].add(ival(args[0]))
            self.models[e["idx"]] = ms
        self.zidane_players = {i for i in self.dpc if 98 in self.models.get(i, set())}

    def resolve(self, arg: str, this_entry: int) -> tuple:
        """(kind, entries) for an object arg: 'player' (250), 'this' (255 -> the executing entry), 'uid' (InitObject's
        uid, else the entry of that index), 'expr' (a computed arg -- unresolvable offline)."""
        v = ival(arg)
        if v is None:
            return ("expr", set())
        if v == PLAYER_UID:
            return ("player", set(self.dpc))
        if v == THIS_UID:
            return ("this", {this_entry})
        ents = set(self.uid_entries.get(v, set()))
        if not ents and v in self.by_idx:
            ents = {v}
        return ("uid", ents)


def load_exports(exports: Path, man: dict) -> list:
    files = sorted(exports.glob("test2_*.txt"), key=lambda p: int(p.stem.split("_")[1]))
    return [Export(f, *man.get(f.name, (None, None))) for f in files]


def chrfx_ops(ex: Export, entry: dict, func: dict) -> list:
    out = []
    for op, args, c, n in func["ops"]:
        if op == "RunModelCode" and len(args) >= 4 and ival(args[0]) is not None:
            out.append({"code": ival(args[0]), "anim": ival(args[1]), "frame": ival(args[2]), "arg4": ival(args[3]),
                        "frame_expr": None if ival(args[2]) is not None else "computed", "line": n,
                        "func": func["name"], "tag": func["tag"], "entry": entry["idx"]})
    return out


# ================================================================================================ the open-source tables
def load_tables(memoria: Path) -> dict:
    def src(path, pat):
        return [(int(m.group(1)), m.group(2)) for m in re.finditer(pat, path.read_text(encoding="utf-8-sig",
                                                                                         errors="replace"))]
    anim = src(memoria / "Assembly-CSharp" / "Global" / "ff9" / "FF9DBAll.Animation.cs",
               r'\{\s*(\d+)\s*,\s*"(ANH_[A-Z0-9_]+)"\s*\}')
    geo = src(memoria / "Assembly-CSharp" / "Global" / "ff9" / "Battle" / "FF9BattleDB.GEO.cs",
              r'\{\s*(\d+)\s*,\s*"(GEO_[A-Z0-9_]+)"\s*\}')
    ids = collections.defaultdict(list)
    for i, n in anim:
        ids[n].append(i)
    return {"anim": dict(anim), "anim_ids": dict(ids), "geo": dict(geo)}


def folder_of(clip):
    t = (clip or "").split("_")
    return None if len(t) < 4 else f"GEO_{t[1]}_{t[2]}_{t[3]}"


def _loco_classes() -> dict:
    """{ZDN anim id: s140's loco class} from the sibling loco_table.json (gen_loco_table.py's output, read-only)."""
    try:
        d = json.loads((HERE / "loco_table.json").read_text(encoding="utf-8"))
        return {int(k): v[1] for k, v in d.get("by_id", {}).items()}
    except (OSError, ValueError):
        return {}


def _frames13() -> dict:
    """{rig: {walk, run, ...frame counts}} from the sibling rigs_8_11.json (the install's clip frame counts)."""
    try:
        d = json.loads((HERE / "rigs_8_11.json").read_text(encoding="utf-8"))
        return {int(k): v for k, v in d.get("frames_13", {}).items()}
    except (OSError, ValueError):
        return {}


# ================================================================================================ (a) field 250
def census_field250(exs: dict, rigs: list, tables: dict) -> dict:
    ex = exs[250]
    players = sorted(ex.zidane_players)
    assert players == [10], f"field 250's Zidane player entries {players} (expected [10])"
    pe = ex.by_idx[10]
    funcs = {f["name"]: f for f in pe["funcs"]}
    init = [o for o in chrfx_ops(ex, pe, funcs["Zidane_Init"]) if o["code"] in FOOTSTEP_CODES]
    # Main_Reinit -> RunScript*(level, 250 | 10, tag): the player-entry functions a warm return runs
    reinit_calls, reinit = [], []
    main = ex.by_idx[0]
    for f in main["funcs"]:
        if f["name"] != "Main_Reinit":
            continue
        for op, args, c, n in f["ops"]:
            if op.startswith("RunScript") and len(args) >= 3 and ival(args[1]) in (PLAYER_UID, 10):
                tag = ival(args[2])
                tf = next((g for g in pe["funcs"] if g["tag"] == tag), None)
                reinit_calls.append({"op": op, "uid": ival(args[1]), "tag": tag, "line": n,
                                     "func": tf["name"] if tf else None})
                if tf:
                    reinit += [o for o in chrfx_ops(ex, pe, tf) if o["code"] in FOOTSTEP_CODES]
    every = []
    for f in pe["funcs"]:
        for o in chrfx_ops(ex, pe, f):
            every.append({k: o[k] for k in ("func", "tag", "code", "anim", "frame", "arg4", "line")})
    # other entries' CHRFX on the player object: only through a RunScript on 250 / 10 (handled above) -- list any
    # RunScript on the player from elsewhere, to show which player functions can run besides Init / Main_Reinit's
    other_calls = []
    for e in ex.entries:
        for f in e["funcs"]:
            for op, args, c, n in f["ops"]:
                if op.startswith("RunScript") and len(args) >= 3 and ival(args[1]) in (PLAYER_UID, 10):
                    tf = next((g for g in pe["funcs"] if g["tag"] == ival(args[2])), None)
                    other_calls.append({"from": f"{e['idx']}:{f['name']}", "op": op, "tag": ival(args[2]), "line": n,
                                        "func": tf["name"] if tf else None,
                                        "footstep_ops": len([o for o in chrfx_ops(ex, pe, tf)
                                                             if o["code"] in FOOTSTEP_CODES]) if tf else 0})
    keys = [[o["code"], o["anim"], o["frame"], o["arg4"]] for o in init]
    rkeys = [[o["code"], o["anim"], o["frame"], o["arg4"]] for o in reinit]
    z = rigs[0]
    not_pair = [k for k in keys + rkeys if not (
        (k[1] == z["walk"] and k[2] in (z["walk_step_a"], z["walk_step_b"])) or
        (k[1] == z["run"] and k[2] in (z["run_step_a"], z["run_step_b"])))]
    per_rig = {}
    for i, rig in enumerate(rigs):
        name = RIG_NAMES[i] if i < len(RIG_NAMES) else f"rig{i}"
        on = expected_steps(rig, [tuple(k) for k in keys], polish=True, dressed=(i != 0), zidane=z)
        warm = expected_steps(rig, [tuple(k) for k in rkeys], polish=True, dressed=(i != 0), zidane=z)
        off = expected_steps(rig, [tuple(k) for k in keys], polish=False, dressed=(i != 0), zidane=z)
        verdicts = collections.Counter(map_footstep(rig, *k, zidane=z)[0] for k in keys)
        # each mapped frame must fall inside the rig's clip (frames from rigs_8_11.json's frames_13)
        per_rig[f"{i} {name}"] = {
            "rig": i, "model": rig["model"], "walk": rig["walk"], "run": rig["run"],
            "pairs": {"walk": [rig["walk_step_a"], rig["walk_step_b"]], "run": [rig["run_step_a"], rig["run_step_b"]]},
            "step_sound": rig["step_sound"], "rule_verdicts": dict(verdicts),
            "s141": {k: on[k] for k in ("steps", "steps_dropped", "steps_passed", "faults")},
            "s141_table": on["table"],
            "s141_warm_return": {k: warm[k] for k in ("steps", "steps_dropped", "steps_passed", "faults")},
            "s141_polish_off": {k: off[k] for k in ("steps", "steps_dropped", "steps_passed", "faults")},
            "note": ("the F3 CONTROL: a Zidane dress disarms (netSelfDress stays 0), so MapFootstep never runs on it; "
                     "steps_fired_player counts its footfalls") if i == 0 else None}
    return {"field": 250, "export": ex.path.name, "name": ex.fname, "player_entry": 10, "player_uid_default": 10,
            "load_ops": [{k: o[k] for k in ("func", "code", "anim", "frame", "arg4", "line")} for o in init],
            "load_ops_n": len(init), "reinit_calls": reinit_calls,
            "reinit_ops": [{k: o[k] for k in ("func", "code", "anim", "frame", "arg4", "line")} for o in reinit],
            "reinit_ops_n": len(reinit), "load_equals_reinit": keys == rkeys,
            "player_entry_chrfx_all": every, "runscript_on_player": other_calls,
            "source_keys": sorted({(k[1], k[2]) for k in keys}),
            "not_a_zidane_pair_key": not_pair,
            "per_load_reset": ("FF9StateFieldMap.ff9ResetStateFieldMap (FF9StateFieldMap.cs:14-27) clears charSoundArray and "
                               "charSoundUse; HonoluluFieldMain.ff9InitStateFieldMap (:78) calls it on every field scene's "
                               "first frame, cold load and warm return alike (AllSoundDispatchPlayer.StopAllSounds also "
                               "clears it, :1207-1213). So the TABLE is per load in stock; s141's counters must reset at "
                               "the same site (O5) or a warm return reads 24 drops for 12."),
            "steps_sound_field": "sound = the record's sndEffectID[0] (code 16's Arg4); s141_table = [anim, frame, "
                                 "sndEffectID[0], sndEffectID[1], pitchRand]",
            "per_rig": per_rig}


# ================================================================================================ (b) step columns
def census_steps(exl: list, rigs: list, tables: dict) -> dict:
    """Every CHRFX 16-19 in the 817 exports (first block), grouped by anim id."""
    regs = collections.defaultdict(list)                    # anim id -> [(code, frame, arg4, fid, func_key, models)]
    funcs_zdn = set()
    zdn_frames = collections.defaultdict(collections.Counter)
    player_regs = []                                        # CHRFX 16-19 run by a ZIDANE PLAYER entry's own functions
    for ex in exl:
        for e in ex.entries:
            for f in e["funcs"]:
                fkey = (ex.path.name, e["idx"], f["name"])
                for o in chrfx_ops(ex, e, f):
                    if o["code"] not in FOOTSTEP_CODES or o["anim"] is None:
                        continue
                    regs[o["anim"]].append((o["code"], o["frame"], o["arg4"], ex.fid, fkey,
                                            tuple(sorted(ex.models.get(e["idx"], ())))))
                    if o["anim"] in (25, 38):
                        funcs_zdn.add(fkey)
                        zdn_frames[o["anim"]][o["frame"] if o["frame"] is not None else "computed"] += 1
                    if e["idx"] in ex.zidane_players:
                        player_regs.append((ex.fid, o))
    out = {"rigs": {}, "zidane_functions": {}, "sound_reuse": {}, "zidane_player_registrations": {}}
    z = rigs[0]
    out["zidane_functions"] = {"functions_registering_25_or_38": len(funcs_zdn),
                               "frames_by_anim": {str(a): dict(c) for a, c in sorted(zdn_frames.items())},
                               "only_pair_frames": (set(zdn_frames[25]) <= {z["walk_step_a"], z["walk_step_b"]} and
                                                    set(zdn_frames[38]) <= {z["run_step_a"], z["run_step_b"]})}

    def clip_census(anim_id):
        rs = regs.get(anim_id, [])
        f16 = collections.Counter(r[1] for r in rs if r[0] == 16)
        f16_fields = {fr: len({r[3] for r in rs if r[0] == 16 and r[1] == fr}) for fr in f16}
        by_code = collections.Counter(r[0] for r in rs)
        snd16 = collections.Counter(r[2] for r in rs if r[0] == 16)
        snd17 = collections.Counter(r[2] for r in rs if r[0] == 17)
        a18 = collections.Counter(r[2] for r in rs if r[0] == 18)
        return {"id": anim_id, "name": tables["anim"].get(anim_id), "registrations_by_code": dict(sorted(by_code.items())),
                "regs_16_17": by_code.get(16, 0) + by_code.get(17, 0),
                "frames16": {str(k): v for k, v in f16.most_common()},
                "frames16_fields": {str(k): v for k, v in sorted(f16_fields.items(), key=lambda kv: -kv[1])},
                "fields": len({r[3] for r in rs}), "functions": len({r[4] for r in rs}),
                "sounds16": {str(k): v for k, v in snd16.most_common(8)},
                "sounds17": {str(k): v for k, v in snd17.most_common(8)}, "code18_arg4": dict(a18),
                "distinct_sounds_16_17": len(set(snd16) | set(snd17)),
                "on_models": dict(collections.Counter(m for r in rs for m in r[5]).most_common(6))}

    disagreements = []
    frames13 = _frames13()
    for i, rig in enumerate(rigs):
        name = RIG_NAMES[i]
        w, r = clip_census(rig["walk"]), clip_census(rig["run"])
        alias = {}
        for slot, aid in (("walk", rig["walk"]), ("run", rig["run"])):
            nm = tables["anim"].get(aid)
            others = [x for x in tables["anim_ids"].get(nm, []) if x != aid]
            alias[slot] = {str(x): clip_census(x) for x in others if regs.get(x)}

        def modal_pair(c):
            top = sorted(((int(k), v) for k, v in c["frames16"].items() if k not in ("None", "computed")),
                         key=lambda kv: -kv[1])
            return sorted(k for k, _v in top[:2]) if len(top) >= 2 else ([-1, -1] if not top else None)
        cw, cr = modal_pair(w), modal_pair(r)
        snds = (set(map(int, w["sounds16"])) | set(map(int, w["sounds17"])) | set(map(int, r["sounds16"])) |
                set(map(int, r["sounds17"])))
        all16_17 = sum(int(v) for c in (w, r) for d in ("sounds16", "sounds17") for v in c[d].values())
        cs_sound = (next(iter(snds)) if len(snds) == 1 else 0) if snds else 0
        table = {"walk_pair": [rig["walk_step_a"], rig["walk_step_b"]], "run_pair": [rig["run_step_a"], rig["run_step_b"]],
                 "step_sound": rig["step_sound"]}
        census = {"walk_pair": cw, "run_pair": cr, "step_sound": cs_sound}
        agree = {k: table[k] == census[k] for k in table}
        fr = frames13.get(i, {})
        in_clip = {"walk_frames": fr.get("walk"), "run_frames": fr.get("run"),
                   "walk_pair_inside": None if rig["walk_step_a"] < 0 or not fr.get("walk") else
                   0 <= rig["walk_step_a"] < rig["walk_step_b"] < fr["walk"],
                   "run_pair_inside": None if rig["run_step_a"] < 0 or not fr.get("run") else
                   0 <= rig["run_step_a"] < rig["run_step_b"] < fr["run"]}
        out["rigs"][f"{i} {name}"] = {"walk": w, "run": r, "alias_ids_with_registrations": alias, "table": table,
                                      "census": census, "agree": agree, "regs_16_17_total": all16_17,
                                      "pair_inside_clip": in_clip}
        if False in (in_clip["walk_pair_inside"], in_clip["run_pair_inside"]):
            disagreements.append(f"rig {i} {name}: a footfall frame lies outside its clip {in_clip}")
        for k, ok in agree.items():
            if not ok:
                disagreements.append(f"rig {i} {name}: {k} table {table[k]} vs census {census[k]}")
    # Zidane's per-field sound ids vs each rig's (the audit: Garnet 70/70, Vivi 79/79, Freya 40/40, Eiko 47/47,
    # Amarant 10/10 use Zidane's exact ids; Steiner shares them in none of 59) -- in TWO scopes, because the audit does
    # not say which it used: every 25/38 registration in the field, or only the Zidane PLAYER entry's
    def per_field(anims, player_only=False):
        d = collections.defaultdict(lambda: {16: set(), 17: set()})
        for a in anims:
            for code, _fr, arg4, fid, k, _m in regs.get(a, []):
                if code in (16, 17) and (not player_only or k[1] in zp_entries.get(k[0], ())):
                    d[fid][code].add(arg4)
        return d
    zp_entries = {ex.path.name: ex.zidane_players for ex in exl}
    audit_reuse = {"vivi": 79, "garnet": 70, "steiner": 59, "freya": 40, "eiko": 47, "amarant": 10}
    for scope, zf in (("all_25_38", per_field((z["walk"], z["run"]))),
                      ("zidane_player_entry", per_field((z["walk"], z["run"]), player_only=True))):
        for i, rig in enumerate(rigs[1:], 1):
            rf = per_field((rig["walk"], rig["run"]))
            both = sorted(set(zf) & set(rf), key=lambda x: (x is None, x))
            eq = [f for f in both if rf[f][16] == zf[f][16] and rf[f][17] == zf[f][17]]
            share_any = [f for f in both if (rf[f][16] | rf[f][17]) & (zf[f][16] | zf[f][17])]
            out["sound_reuse"].setdefault(f"{i} {RIG_NAMES[i]}", {"audit_fields": audit_reuse.get(RIG_NAMES[i])})[scope] = {
                "fields_both_register": len(both), "rig_fields": len(rf), "exact_equal": len(eq),
                "share_any_id": len(share_any), "not_equal_fields": [f for f in both if f not in eq][:12]}
    # what MapFootstep (O4) does to every stock registration a ZIDANE PLAYER entry makes
    loco = _loco_classes()
    cls = collections.Counter()
    off_pair = collections.defaultdict(lambda: {"fields": collections.Counter(), "codes": collections.Counter(),
                                                "frames16": collections.Counter()})
    for fid, o in player_regs:
        v = map_footstep(rigs[4], o["code"], o["anim"], o["frame"] if o["frame"] is not None else -999,
                         o["arg4"] or 0, zidane=z)[0]
        cls[v] += 1
        if v == "pass":
            d = off_pair[o["anim"]]
            d["fields"][fid] += 1
            d["codes"][o["code"]] += 1
            if o["code"] == 16:
                d["frames16"][o["frame"] if o["frame"] is not None else "computed"] += 1
    out["zidane_player_registrations"] = {
        "ops": len(player_regs), "verdicts_on_a_mapping_rig": dict(cls),
        "pass_by_anim": {f"{a} {tables['anim'].get(a)}": {
            "loco_class": loco.get(a), "fields": sorted(d["fields"], key=lambda x: (x is None, x)),
            "ops": sum(d["fields"].values()), "codes": dict(sorted(d["codes"].items())),
            "frames16": {str(k): n for k, n in d["frames16"].most_common()}} for a, d in sorted(off_pair.items())},
        "note": "O4 matches anim by ID (25 / 38). A WALK/RUN-class key on another id (190 / 203 = the second ids naming "
                "ANH_MAIN_F0_ZDN_WALK / _RUN; the qualified COLD_/SWORD_/POT_/MBG_/TKE_/FRA_ variants) PASSES unmapped, "
                "while s140's MapAnim maps those clips by NAME class to rig.walk / rig.run (loco_table.json), so the "
                "dressed body's evt.anim is never that id and the key can never fire: a dressed body walks SILENTLY "
                "there (cosmetic, no fault) -- except code 19, see open_issues (the empty-table throw)"}
    out["code19"] = [{"field": fid, "anim": a, "anim_name": tables["anim"].get(a), "frame": fr, "func": k[2],
                      "entry": k[1], "models": list(m), "zidane_player": None}
                     for a, rs in sorted(regs.items()) for (c, fr, _a4, fid, k, m) in rs if c == 19]
    # THE EMPTY-TABLE HAZARD: replay every Zidane-player function that runs a code 19 through expected_steps on each rig,
    # from an EMPTY table (the lower bound: no other body has registered yet when it runs). Stock never faults there
    # (its own 16s fill the table first); a dressed body whose 16s are DROPPED and whose 19 PASSES (an id O4 does not
    # map) reaches stock DeleteChar with charSoundUse == 0 -> charSoundArray[-1] -> IndexOutOfRangeException in the VM.
    hz = []
    for ex in exl:
        for e in ex.entries:
            if e["idx"] not in ex.zidane_players:
                continue
            for f in e["funcs"]:
                ops = [o for o in chrfx_ops(ex, e, f) if o["code"] in FOOTSTEP_CODES]
                if not any(o["code"] == 19 for o in ops):
                    continue
                seq = [(o["code"], o["anim"], o["frame"] if o["frame"] is not None else -999, o["arg4"] or 0)
                       for o in ops]
                stock = expected_steps(rigs[0], seq, dressed=False)
                per = {}
                for i, rig in enumerate(rigs[1:], 1):
                    r = expected_steps(rig, seq, polish=True, dressed=True, zidane=z)
                    if r["faults"]:
                        per[f"{i} {RIG_NAMES[i]}"] = r["faults"]
                hz.append({"field": ex.fid, "export": ex.path.name, "entry": e["idx"], "func": f["name"],
                           "ops": len(seq), "stock_faults": stock["faults"], "s141_faults_by_rig": per,
                           "init_order": [ival(a[0]) for fn in ex.by_idx[0]["funcs"] if fn["tag"] == 0
                                          for op, a, _c, _n in fn["ops"] if op == "InitObject"][:12]
                           if 0 in ex.by_idx else None})
    out["code19_empty_table_hazard"] = hz
    out["table_disagreements"] = disagreements
    return out, regs


# ================================================================================================ (c) Cinna and rows 10-12
def census_subs(exl: list, regs: dict, rigs: list, tables: dict) -> dict:
    out = {}
    for token, rig_i in (("CNA", 9), ("MRC", 10), ("BLN", 11), ("BTX", 12)):
        models = sorted(m for m, g in tables["geo"].items() if g.endswith("_" + token) and "_SUB_" in g)
        folders = {tables["geo"][m] for m in models}
        anims = sorted(a for a, n in tables["anim"].items() if folder_of(n) in folders)
        hits = []
        for a in anims:
            for code, fr, arg4, fid, k, m in regs.get(a, []):
                hits.append({"field": fid, "anim": a, "name": tables["anim"][a], "code": code, "frame": fr,
                             "arg4": arg4, "entry": k[1], "func": k[2]})
        # any CHRFX 16-19 run by an entry that wears one of these models, whatever the anim
        body_hits = []
        for ex in exl:
            for e in ex.entries:
                if not (ex.models.get(e["idx"], set()) & set(models)):
                    continue
                for f in e["funcs"]:
                    for o in chrfx_ops(ex, e, f):
                        if o["code"] in FOOTSTEP_CODES:
                            body_hits.append({"field": ex.fid, "entry": e["idx"], "func": f["name"], "code": o["code"],
                                              "anim": o["anim"], "frame": o["frame"], "arg4": o["arg4"],
                                              "anim_name": tables["anim"].get(o["anim"])})
        rig = rigs[rig_i]
        wr = [h for h in hits if h["anim"] in (rig["walk"], rig["run"])]
        out[token] = {"rig": rig_i, "name": RIG_NAMES[rig_i], "models": {str(m): tables["geo"][m] for m in models},
                      "anim_ids_in_family": len(anims), "registrations_on_family_anims": len(hits),
                      "registrations_by_family_body": len(body_hits),
                      "rig_walk_run_registrations": {
                          "n": len(wr), "fields": sorted({h["field"] for h in wr}, key=lambda x: (x is None, x)),
                          "frames16": dict(collections.Counter(f"{h['anim']}@{h['frame']}" for h in wr
                                                               if h["code"] == 16).most_common()),
                          "sounds": dict(collections.Counter(h["arg4"] for h in wr if h["code"] in (16, 17)).most_common(6))},
                      "other_family_registrations": [h for h in hits if h["anim"] not in (rig["walk"], rig["run"])][:20],
                      "body_hits_not_family_anim": [h for h in body_hits if h["anim"] not in set(anims)][:20]}
    out["CNA"]["verdict"] = ("NO CHRFX 16-19 registration on any Cinna body or Cinna clip in any field: her row's -1 "
                             "footfalls are stock-faithful (O1: she walks silently, 12 drops per load on 250)"
                             if out["CNA"]["registrations_on_family_anims"] == 0
                             and out["CNA"]["registrations_by_family_body"] == 0 else
                             "Cinna HAS stock footstep registrations -- O1's premise fails (see the hits)")
    return out


# ================================================================================================ (d) lighting
def census_lighting(exl: list, rigs: list, game) -> tuple:
    from ff9mapkit import extract, mapconfig
    idx = mcf_index(game)
    evt_to_fid = {str(evt).lower(): fid for fid, evt in extract.ID_TO_EVT.items()}
    parsed = {}
    for evt, data in idx.items():
        try:
            parsed[evt] = mapconfig.parse(data)
        except Exception as err:                              # noqa: BLE001 - reported, never fatal
            parsed[evt] = err
    bad = sorted(k for k, v in parsed.items() if isinstance(v, Exception))
    ok = {k: v for k, v in parsed.items() if not isinstance(v, Exception)}
    m250 = load_mcf(250, game, idx)
    lights250 = [{"i": n, "type": lt.type, "no": lt.no, "shadowI": lt.shadow_i, "shadowR": lt.shadow_r,
                  "clr": list(lt.clr[:3]), "floor": [f for f in lt.floor]}
                 for n, lt in enumerate(m250.lights[:m250.light_use])]
    chars250 = [{"geo": c.geo, "shadowI": c.shadow_i, "shadowR": c.shadow_r, "clr": list(c.clr)}
                for c in m250.chars[:m250.char_use]]
    floors = {}
    for fl in range(4):
        lt = _floor_light(m250, fl)
        floors[str(fl)] = {"floor_light_clr": list(lt.clr[:3]) if lt else None,
                           "light_used": "floor" if lt else "default",
                           "dressed_98_row": light_color(m250, 192, fl, dress_src=DRESS_SRC, polish=True),
                           "default_row": light_color(m250, 192, fl, dress_src=DRESS_SRC, polish=False),
                           "zidane_own_98": light_color(m250, 98, fl)}
    # per rig, on 250 floor 0: s141 vs polish off, and the ghost (the selftest mirror wears the dressed model)
    rig250 = {}
    for i, rig in enumerate(rigs):
        m = rig["model"]
        rig250[f"{i} {RIG_NAMES[i]}"] = {
            "model": m, "own_row_on_250": m250.char(m) is not None,
            "s141": light_color(m250, m, 0, dress_src=DRESS_SRC if i else 0, polish=True),
            "polish_off": light_color(m250, m, 0, dress_src=DRESS_SRC if i else 0, polish=False),
            "ghost_s141": ghost_light_color(m250, m, m, 0, lp_dress_src=DRESS_SRC if i else 0, polish=True),
            "ghost_polish_off": ghost_light_color(m250, m, m, 0, lp_dress_src=DRESS_SRC if i else 0, polish=False)}
    # the reach over every MCF, per rig model
    zid_fields = {ex.fid for ex in exl if ex.zidane_players and ex.fid is not None}
    have_default = sum(1 for v in ok.values() if v.char(DEFAULT_ROW) is not None)
    have_98 = sum(1 for v in ok.values() if v.char(98) is not None)
    reach = {}
    for i, rig in enumerate(rigs):
        m = rig["model"]
        own = fb = fb_visible = neither = 0
        own_z = fb_z = fbv_z = neither_z = 0
        for evt, mc in ok.items():
            fid = evt_to_fid.get(evt)
            zf = fid in zid_fields
            if mc.char(m) is not None:
                own += 1
                own_z += zf
            elif mc.char(98) is not None:
                fb += 1
                fb_z += zf
                d = mc.char(DEFAULT_ROW)
                vis = d is None or tuple(mc.char(98).clr) != tuple(d.clr)
                fb_visible += vis
                fbv_z += (vis and zf)
            else:
                neither += 1
                neither_z += zf
        reach[f"{i} {RIG_NAMES[i]}"] = {
            "model": m, "all_mcfs": {"own_row": own, "fallback_98_fires": fb, "fallback_changes_clr": fb_visible,
                                     "neither_default_row": neither},
            "zidane_player_fields": {"own_row": own_z, "fallback_98_fires": fb_z, "fallback_changes_clr": fbv_z,
                                     "neither_default_row": neither_z}}
    out = {"field250": {"evt": extract.ID_TO_EVT.get(250), "light_use": m250.light_use, "char_use": m250.char_use,
                        "lights": lights250, "chars": chars250, "floors": floors, "per_rig_floor0": rig250},
           "mcfs": {"total": len(idx), "parsed": len(ok), "unparsed": bad, "with_default_row": have_default,
                    "with_98_row": have_98, "lacking_98_row": len(ok) - have_98,
                    "mapped_to_field_ids": sum(1 for e in ok if e in evt_to_fid),
                    "zidane_player_fields_in_exports": len(zid_fields)},
           "reach": reach,
           "arithmetic": "fldmcf.cs: row = GetCharByID(po.model) else GetCharByID(-1 -> 0xFFFF); light = ladder (attr&4) "
                         "else GetLightByCharFloor (the highest-index type-0 light naming the floor) else the type-1 "
                         "default; clr_i = (Byte)((row.clr_i + light.clr_i) << 3); fldchar.cs:217-235 writes it as "
                         "Color32 rgb into every material's _Color (alpha kept). s141 inserts the netDressSrc (98) row "
                         "between the own row and the default row."}
    return out, idx


# ================================================================================================ (e) hand bones
def census_hands(rigs: list, game) -> dict:
    from ff9mapkit.models import bone_labels as BL
    out, bundle = {}, None
    for i, rig in enumerate(rigs):
        m = rig["model"]
        sk = BL.read_skeleton(str(int(m)), game=game, bundle=bundle)
        bundle = sk.get("bundle")
        bones = sk["bones"]
        nums = sorted(BL.bone_num_lenient(b["name"]) for b in bones)
        names = {BL.bone_num_lenient(b["name"]): b["name"] for b in bones}
        parent = {BL.bone_num_lenient(b["name"]): (BL.bone_num_lenient(b["parent"]) if b["parent"] else None)
                  for b in bones}
        children = collections.defaultdict(list)
        for c, p in parent.items():
            if p is not None:
                children[p].append(c)
        lab = BL.labels_for(bones, prefab_id=sk.get("prefab_id"), geo=sk.get("geo"))
        grp = str(sk.get("geo") or "").split("_")[1].lower() if "_" in str(sk.get("geo") or "") else None
        heur = BL.label_skeleton(bones, group=grp)
        lf_rh = sorted(n for n, x in lab.items() if x == "R_hand")
        lf_rhe = sorted(n for n, x in lab.items() if x == "R_hand_end")
        hb, he = rig["hand_bone"], rig["hand_bone_end"]
        lf_has_hand = bool(lf_rh)
        src = lab if lf_has_hand else heur
        exp_hb = (lf_rh or sorted(n for n, x in heur.items() if x == "R_hand") or [None])[0]
        exp_he_l = lf_rhe if lf_has_hand else sorted(n for n, x in heur.items() if x == "R_hand_end")
        exp_he = exp_he_l[0] if exp_he_l else exp_hb

        def part(n, deep=True):
            a, b = lab.get(n), heur.get(n)
            meshy = bool(a) and bool(re.match(r"^(hi|mesh|field_model)", str(a)))
            out_ = {"labels_for": a, "label_skeleton": b, "use": b if (meshy or not a) else a}
            if deep:
                p = parent.get(n)
                out_["parent"] = p
                out_["parent_use"] = part(p, False)["use"] if p is not None else None
                out_["children"] = sorted(children.get(n, []))
                if out_["use"] is None and out_["children"]:          # an unlabelled zero-length pivot: name its subtree
                    out_["use"] = "pivot of " + "+".join(str(part(c, False)["use"]) for c in out_["children"])
            return out_
        out[f"{i} {RIG_NAMES[i]}"] = {
            "model": m, "geo": sk.get("geo"), "bones": len(bones), "max_bone": max(nums) if nums else None,
            "name_format_ok": all(names[n] == f"bone{n:03d}" for n in nums),
            "hand_bone": hb, "hand_bone_end": he,
            "hand_bone_name": f"bone{hb:03d}", "hand_bone_end_name": f"bone{he:03d}",
            "hand_bones_exist": hb in names and he in names,
            "labels_source": "labels_for" if lf_has_hand else "label_skeleton (labels_for names no R_hand)",
            "labels_for_R_hand": lf_rh, "labels_for_R_hand_end": lf_rhe,
            "heuristic_R_hand": sorted(n for n, x in heur.items() if x == "R_hand"),
            "heuristic_R_hand_end": sorted(n for n, x in heur.items() if x == "R_hand_end"),
            "expected": [exp_hb, exp_he], "agree": [hb, he] == [exp_hb, exp_he],
            "hand_children": sorted(children.get(hb, [])), "hand_parent": parent.get(hb),
            "hand_parent_label": part(parent.get(hb), False)["use"] if parent.get(hb) is not None else None,
            "end_is_hand": hb == he,
            "why_end_is_hand": (f"bone{hb:03d} (R_hand) is a LEAF -- no child bone, so no R_hand_end exists to label; "
                                f"the table uses R_hand for both (bone 12 and 13 both land on bone{hb:03d})")
            if hb == he and not children.get(hb) else None,
            "bone12": part(12) if 12 in names else None, "bone13": part(13) if 13 in names else None,
            "bone12_exists": 12 in names, "bone13_exists": 13 in names,
            "f8_parent_bone13_s141": f"bone{he:03d}", "f8_parent_bone13_polish_off": "bone013" if 13 in names else None,
            "f8_parent_bone12_s141": f"bone{hb:03d}", "f8_parent_bone12_polish_off": "bone012" if 12 in names else None}
    return out


# ================================================================================================ (f) + (g) the op censuses
def census_attach_mesh(exl: list, tables: dict) -> dict:
    att, mesh, att_any_player, mesh_any_player, unresolved = [], [], [], [], collections.Counter()
    for ex in exl:
        for e in ex.entries:
            for f in e["funcs"]:
                for op, args, c, n in f["ops"]:
                    if op == "AttachObject" and len(args) >= 3:
                        kind, ents = ex.resolve(args[1], e["idx"])
                        if kind == "expr":
                            unresolved["AttachObject"] += 1
                        carried_kind, carried = ex.resolve(args[0], e["idx"])
                        carried_models = sorted({mm for x in carried for mm in ex.models.get(x, set())})
                        row = {"field": ex.fid, "export": ex.path.name, "line": n, "entry": e["idx"], "func": f["name"],
                               "carried": ival(args[0]), "carried_models": carried_models,
                               "carrier": ival(args[1]), "carrier_kind": kind, "carrier_entries": sorted(ents),
                               "bone": ival(args[2]) if ival(args[2]) is not None else args[2]}
                        zid = kind == "player" or bool(ents & ex.zidane_players)
                        anyp = kind == "player" or bool(ents & ex.dpc)
                        if kind == "player":
                            row["field_player_models"] = sorted({mm for x in ex.dpc for mm in ex.models.get(x, set())})
                        if zid:
                            att.append(row)
                        elif anyp:
                            att_any_player.append(row)
                    elif op in ("ShowObject", "HideObject") and len(args) >= 2:
                        kind, ents = ex.resolve(args[0], e["idx"])
                        if kind == "expr":
                            unresolved[op] += 1
                        row = {"field": ex.fid, "export": ex.path.name, "line": n, "op": op, "entry": e["idx"],
                               "func": f["name"], "target": ival(args[0]), "target_kind": kind,
                               "target_entries": sorted(ents), "mesh": args[1]}
                        if kind == "player" or ents & ex.zidane_players:
                            mesh.append(row)
                        elif ents & ex.dpc:
                            mesh_any_player.append(row)
    bones = collections.Counter(r["bone"] for r in att)
    by_bone_fields = {str(b): sorted({r["field"] for r in att if r["bone"] == b}, key=lambda x: (x is None, x))
                      for b in bones}
    b1213 = [r for r in att if r["bone"] in (12, 13)]
    return {
        "attach": {"ops": len(att), "fields": len({r["field"] for r in att}),
                   "by_bone": {str(k): v for k, v in sorted(bones.items(), key=lambda kv: str(kv[0]))},
                   "bone_12_13_ops": len(b1213), "bone_12_13_fields": len({r["field"] for r in b1213}),
                   "by_bone_fields": by_bone_fields,
                   "by_carrier_kind": dict(collections.Counter(r["carrier_kind"] for r in att)),
                   "other_bones": [r for r in att if r["bone"] not in (12, 13)],
                   "rows": att,
                   "carried_model_names": {str(m): tables["geo"].get(m) for r in att for m in r["carried_models"]},
                   "non_zidane_player_carriers": {"ops": len(att_any_player),
                                                  "by_bone": dict(collections.Counter(r["bone"] for r in att_any_player))}},
        "mesh": {"ops_on_zidane_player_or_250": len(mesh), "rows": mesh,
                 "ops_on_other_player_entries": len(mesh_any_player),
                 "other_player_entries_by_model": dict(collections.Counter(
                     f"{m} {tables['geo'].get(m)}" for r in mesh_any_player
                     for m in sorted({mm for x in r["target_entries"]
                                      for mm in next(ex for ex in exl if ex.path.name == r["export"]).models.get(x, ())}))
                     .most_common()),
                 "other_player_fields": sorted({r["field"] for r in mesh_any_player}, key=lambda x: (x is None, x)),
                 "exports": len(exl)},
        "unresolved_computed_args": dict(unresolved)}


# ================================================================================================ main
def build(exports: Path, memoria: Path, game) -> dict:
    rigs = parse_rigs(memoria)
    tables = load_tables(memoria)
    man = manifest(MANIFEST)
    exl = load_exports(exports, man)
    exs = {ex.fid: ex for ex in exl if ex.fid is not None}
    out = {"schema": "ff9mapkit.dress-census.polish/1", "tool": "studies/battle-coop/dress-census/polish_census.py",
           "audit": "R3-FIELD-MODEL-AUDIT.md 2.4 amendments 1-6, section 4.5 (leg F); orchestrator O1, O4-O8",
           "sources": {"exports": f"{len(exl)} HW exports, first language block", "game": str(game),
                       "rig_table": f"{VISITOR.as_posix()} sha256/16 {visitor_sha(memoria)} ({len(rigs)} rows)",
                       "kit": str(_KIT_AT.parent)},
           "rigs": [dict(r, rig=i, name=RIG_NAMES[i]) for i, r in enumerate(rigs)]}
    out["a_field250"] = census_field250(exs, rigs, tables)
    steps, regs = census_steps(exl, rigs, tables)
    for row in steps["code19"]:
        ex = exs.get(row["field"])
        row["zidane_player"] = bool(ex and row["entry"] in ex.zidane_players)
    out["b_steps"] = steps
    out["c_subs"] = census_subs(exl, regs, rigs, tables)
    light, _idx = census_lighting(exl, rigs, game)
    out["d_lighting"] = light
    out["e_hands"] = census_hands(rigs, game)
    try:                                                       # rigs_8_11.json's heuristic evidence for rows 9-10
        r811 = json.loads((HERE / "rigs_8_11.json").read_text(encoding="utf-8"))["rows"]
        for i in (9, 10):
            sk = r811[str(i)]["evidence"]["skeleton"]
            out["e_hands"][f"{i} {RIG_NAMES[i]}"]["rigs_8_11_evidence"] = {
                "labels_source": sk["labels_source"], "heuristic_hands": sk["heuristic_hands"],
                "geometry_ok": sk["geometry_ok"], "hand_world": sk["hand_world"],
                "consensus_mesh_named_labels_n": len(sk["consensus_mesh_named_labels"])}
    except (OSError, KeyError, ValueError) as err:
        out["e_hands"]["rigs_8_11_evidence_error"] = str(err)
    out["fg_ops"] = census_attach_mesh(exl, tables)
    out["o6_other_sites"] = other_attach_sites(exs, tables)
    out["twin_selftest"] = twin_selftest(rigs, out)
    out["bench"] = bench_expectations(out, rigs)
    out["table_disagreements"] = list(steps["table_disagreements"]) + [
        f"rig {k}: hand bones table {[v['hand_bone'], v['hand_bone_end']]} vs labels {v['expected']}"
        for k, v in out["e_hands"].items() if not v["agree"]]
    out["open_issues"] = open_issues(out, rigs)
    return out


def twin_selftest(rigs: list, out: dict | None = None) -> dict:
    """The Python twins' own rows (every rig: MapFootstep on the four 250 keys + a 19, the bone remap on 12/13/0, the
    lever) and MUTANTS, each of which some row must catch -- a twin that cannot fail proves nothing."""
    z = rigs[0]
    keys = [(16, 25, 4, 919), (17, 25, 13, 914), (18, 38, 0, 1), (19, 38, 8, 0), (16, 200, 4, 919), (16, 25, 7, 919)]
    rows = []
    for i, rig in enumerate(rigs):
        for k in keys:
            rows.append(("foot", i, k, map_footstep(rig, *k, zidane=z)))
        for b in (12, 13, 0):
            rows.append(("bone", i, b, remap_attach_bone(rig, b)))
        rows.append(("bone_off", i, 13, remap_attach_bone(rig, 13, polish=False)))
    expect = {"foot": lambda i, k, got: (
                  got[0] == ("pass" if k[1] == 200 or k[2] == 7 else
                             "drop" if rigs[i]["walk_step_a"] < 0 else "map")
                  and (got[0] != "map" or got[2] == ((rigs[i]["walk_step_a"], rigs[i]["walk_step_b"])
                                                     if k[1] == 25 else
                                                     (rigs[i]["run_step_a"], rigs[i]["run_step_b"]))[
                      ((4, 13) if k[1] == 25 else (0, 8)).index(k[2])])
                  and (got[0] != "map" or got[3] == (rigs[i]["step_sound"] if rigs[i]["step_sound"] and k[0] in (16, 17)
                                                      else k[3]))),
              "bone": lambda i, b, got: got == ((rigs[i]["hand_bone"], "remap") if b == 12 else
                                               (rigs[i]["hand_bone_end"], "remap") if b == 13 else (b, "note")),
              "bone_off": lambda i, b, got: got == (13, "bypass")}
    fails = [r for r in rows if not expect[r[0]](r[1], r[2], r[3])]

    def run_with(fn_foot, fn_bone) -> int:
        """How many rows a mutant gets WRONG (it must be > 0: caught)."""
        bad = 0
        for kind, i, k, _got in rows:
            got = fn_foot(rigs[i], *k) if kind == "foot" else fn_bone(rigs[i], k, kind != "bone_off")
            bad += not expect[kind](i, k, got)
        return bad
    good_bone = lambda rig, b, pol: remap_attach_bone(rig, b, pol)   # noqa: E731
    good_foot = lambda rig, *k: map_footstep(rig, *k, zidane=z)      # noqa: E731

    def m_ordinal(rig, code, anim, frame, arg4):                    # swaps the ordinal (A <-> B)
        v = map_footstep(rig, code, anim, frame, arg4, zidane=z)
        if v[0] != "map":
            return v
        pair = (rig["walk_step_a"], rig["walk_step_b"]) if anim == 25 else (rig["run_step_a"], rig["run_step_b"])
        return (v[0], v[1], pair[1 - pair.index(v[2])] if v[2] in pair else v[2], v[3])

    def m_keep19(rig, code, anim, frame, arg4):                     # "19 is harmless": passes 19 on a drop rig
        v = map_footstep(rig, code, anim, frame, arg4, zidane=z)
        return ("pass", anim, frame, arg4) if (v[0] == "drop" and code == 19) else v

    def m_sound18(rig, code, anim, frame, arg4):                    # the override also on code 18 / 19
        v = map_footstep(rig, code, anim, frame, arg4, zidane=z)
        return (v[0], v[1], v[2], rig["step_sound"]) if (v[0] == "map" and rig["step_sound"]) else v

    def m_byframe(rig, code, anim, frame, arg4):                    # maps any frame (no pair check)
        if code in FOOTSTEP_CODES and anim in (25, 38) and frame not in ((4, 13) if anim == 25 else (0, 8)):
            return ("map", rig["walk"] if anim == 25 else rig["run"], frame, arg4)
        return map_footstep(rig, code, anim, frame, arg4, zidane=z)

    def m_bone_swap(rig, b, pol):                                    # 12 -> R_hand_end, 13 -> R_hand
        if pol and b in (12, 13):
            return (rig["hand_bone_end"] if b == 12 else rig["hand_bone"], "remap")
        return remap_attach_bone(rig, b, pol)

    def m_bone_any(rig, b, pol):                                     # remaps every bone
        return (rig["hand_bone"], "remap") if pol else (b, "bypass")
    mutants = {"ordinal_swap": run_with(m_ordinal, good_bone), "nineteen_harmless": run_with(m_keep19, good_bone),
               "sound_on_18": run_with(m_sound18, good_bone), "any_frame_maps": run_with(m_byframe, good_bone),
               "bone_swap": run_with(good_foot, m_bone_swap), "bone_any": run_with(good_foot, m_bone_any)}
    light = {}
    if out is not None and "d_lighting" in out:
        f0 = out["d_lighting"]["field250"]["floors"]["0"]
        light = {"98_row_floor0": f0["dressed_98_row"]["rgb"] == [80, 96, 120] and f0["dressed_98_row"]["row"] == 98,
                 "default_row_floor0": f0["default_row"]["rgb"] == [128, 128, 128] and f0["default_row"]["row"] == DEFAULT_ROW,
                 "mutant_default_first_caught": f0["default_row"]["rgb"] != f0["dressed_98_row"]["rgb"]}
    return {"rows": len(rows), "fails": [str(r) for r in fails], "mutants_rows_wrong": mutants,
            "every_mutant_caught": all(v > 0 for v in mutants.values()), "light_rows": light,
            "ok": not fails and all(v > 0 for v in mutants.values()) and all(light.values())}


def bench_expectations(out: dict, rigs: list) -> dict:
    """The leg F oracle rows, keyed by stage (s141 / s141 polish off / s140), from the census above."""
    a, d, e = out["a_field250"]["per_rig"], out["d_lighting"]["field250"], out["e_hands"]
    def st(key):
        return a[key]["s141"]
    fl0 = d["floors"]["0"]
    return {
        "F1 freya": {"s141": st("4 freya"), "s141_polish_off": a["4 freya"]["s141_polish_off"], "s140": "no key"},
        "F2 moogle": {"s141": st("8 moogle"), "s141_polish_off": a["8 moogle"]["s141_polish_off"], "s140": "no key"},
        "F2c cinna": {"s141": st("9 cinna"), "s141_polish_off": a["9 cinna"]["s141_polish_off"], "s140": "no key"},
        "F3 zidane control": {"any_stage": st("0 zidane"),
                              "s140": "steps is an s141 key: absent on s140 (only player.anim / clip and the s138 "
                                      "witnesses can be read there; the triples and steps_fired_player cannot)"},
        "F7 steiner": {"s141": st("3 steiner"), "s141_polish_off": a["3 steiner"]["s141_polish_off"], "s140": "no key"},
        "F6 freya warm return": {"s141": a["4 freya"]["s141_warm_return"],
                                 "note": "Main_Reinit re-runs Zidane_13's 12 ops into a table the load reset cleared: "
                                         "the same 4 triples, no duplicates; counters per load (O5)"},
        "F4 light floor0": {"s141": {"light_row": fl0["dressed_98_row"]["row"], "light_rgb": fl0["dressed_98_row"]["rgb"]},
                            "s141_polish_off": {"light_row": fl0["default_row"]["row"],
                                                "light_rgb": fl0["default_row"]["rgb"]},
                            "per_floor_s141": {k: v["dressed_98_row"]["rgb"] for k, v in d["floors"].items()},
                            "per_floor_polish_off": {k: v["default_row"]["rgb"] for k, v in d["floors"].items()},
                            "zidane_own_row_per_floor": {k: v["zidane_own_98"]["rgb"] for k, v in d["floors"].items()},
                            "note": "judge on the PUBLISHED player.floor through light_color(); a dressed rig with its "
                                    "OWN row on 250 would read that row (none of the 12 non-Zidane rigs has one)"},
        "F4g ghost light_row": {k: {"s141": v["ghost_s141"], "polish_off": v["ghost_polish_off"]}
                                for k, v in d["per_rig_floor0"].items() if not k.startswith("0 ")},
        "F8 attach parent": {k: {"bone13_s141": v["f8_parent_bone13_s141"],
                                 "bone13_polish_off": v["f8_parent_bone13_polish_off"],
                                 "bone12_s141": v["f8_parent_bone12_s141"],
                                 "bone12_polish_off": v["f8_parent_bone12_polish_off"]} for k, v in e.items()},
    }


def other_attach_sites(exs: dict, tables: dict) -> dict:
    """O6: the stock geoAttach sites with a HARD-CODED bone or carrier (EventEngine.DoEventCode.cs), and whether a
    dressed Zidane player can be the carrier: field 112's glasses (carrier uid 2 at :1560, uid 4 at :3295) and the
    62 / 3010 bone-19 override (gCur.sid 8 on 62, sid 2 on 3010)."""
    def who(fid, uid):
        ex = exs.get(fid)
        if ex is None:
            return None
        ents = sorted(ex.uid_entries.get(uid, set()) or ({uid} if uid in ex.by_idx else set()))
        return {"uid": uid, "entries": ents,
                "models": {str(e): [f"{m} {tables['geo'].get(m)}" for m in sorted(ex.models.get(e, ()))] for e in ents},
                "is_player_entry": any(e in ex.dpc for e in ents),
                "is_zidane_player": any(e in ex.zidane_players for e in ents),
                "field_player_entries": {str(e): sorted(ex.models.get(e, ())) for e in sorted(ex.dpc)}}
    return {"112 glasses :1560 (carrier uid 2)": who(112, 2), "112 glasses :3295 (carrier uid 4)": who(112, 4),
            "62 bone-19 override (gCur.sid 8)": who(62, 8), "3010 bone-19 override (gCur.sid 2)": who(3010, 2)}


def open_issues(out: dict, rigs: list) -> list:
    iss = []
    zp = out["b_steps"]["zidane_player_registrations"]
    walkrun = {k: v for k, v in zp["pass_by_anim"].items() if v["loco_class"] in ("WALK", "RUN")}
    gest = {k: v for k, v in zp["pass_by_anim"].items() if v["loco_class"] not in ("WALK", "RUN")}
    if walkrun:
        iss.append("O4 MATCHES BY ID, s140's MapAnim BY NAME: a Zidane player entry registers CHRFX 16-19 on WALK/RUN-class "
                   "ids other than 25/38 -- " + "; ".join(
                       f"{k} ({v['ops']} ops, codes {v['codes']}, frames16 {v['frames16']}, fields {v['fields']})"
                       for k, v in walkrun.items()) +
                   ". Each PASSES unmapped while the dressed body plays rig.walk/run (evt.anim = the rig id), so the "
                   "dressed body walks SILENTLY in those fields (incl. the disc-1 opening 62-64, SWORD_WALK/RUN). "
                   "Cosmetic; extending O4 to the loco CLASS would need each variant's own frame pair (listed) -> the "
                   "rig's pair. Recommend KNOWN in the README unless the engine stage widens the key.")
    if gest:
        iss.append("gesture-class footstep keys on Zidane players pass as designed (steps_passed): " + "; ".join(
            f"{k} ({v['ops']} ops, fields {v['fields']})" for k, v in gest.items()))
    hz = [h for h in out["b_steps"].get("code19_empty_table_hazard", []) if h["s141_faults_by_rig"]]
    for h in hz:
        iss.append(f"EMPTY-TABLE THROW (O4 as written): field {h['field']} {h['func']} (entry {h['entry']}, first in "
                   f"Main_Init's InitObject order {h['init_order']}) registers 16-18 on 25/38 then runs code 19 on the "
                   f"ALIAS ids 190/203 (a stock no-op: no record has those ids). On a DROP rig "
                   f"({', '.join(h['s141_faults_by_rig'])}) the 16-18 are dropped and the 19s PASS, so if no other body "
                   f"has registered yet stock DeleteChar indexes charSoundArray[-1] (FF9Snd.cs DeleteChar) and throws "
                   f"inside the VM -- stock itself never faults there ({h['stock_faults'] or 'no fault'}). Fix that keeps "
                   f"stock semantics: MapFootstep DROPS (counts) a code 19 whose (anim', frame') has NO record in the "
                   f"table -- stock's DeleteChar is a no-op then except for that throw. (Init order across entries is a "
                   f"runtime fact: PLAUSIBLE, not proven.)")
    n19 = [o for o in out["a_field250"]["player_entry_chrfx_all"] if o["code"] == 19]
    if not n19:
        iss.append("F2 / F2c's 'no code-19 fault' CANNOT FAIL on field 250: its player entry runs no code 19 at all (only "
                   "16/17/18 x4 keys, at load and at Main_Reinit). To make the 19-drop checkable, the bench needs a "
                   "synthetic RunModelCode(19, 25, 4, 0) on the dressed drop-rig body (e.g. the 30606 caller after the "
                   "dress): s141 drops it (steps_dropped 12 -> 13, steps stays [], no fault); under `polish off` the "
                   "table holds the 4 UNMAPPED Zidane records, so the 19 matches (25, 4) and stock DeleteChar's "
                   "charSoundUse-- drops the TOP record (steps 4 -> 3 rows, steps_dropped 0) -- the calibration red. "
                   "Only an EMPTY table makes a passed 19 throw (see the field-2930 row).")
    iss.append("O4's sound override must touch codes 16 and 17 only (sndEffectID[0]/[1], the 'both slots'); code 18's "
               "Arg4 is the random-pitch FLAG (fldchar.cs: pitchRand = Arg4 == 0 ? 0 : 1) and 19 ignores Arg4. Every "
               "stock code-18 Arg4 on 25/38 and on Steiner's 1996/2005 is 1, so the difference is invisible in stock "
               "data; the twin (map_footstep) and its 'sound_on_18' mutant pin the 16/17-only reading.")
    sr = out["b_steps"]["sound_reuse"]
    iss.append("AUDIT COUNTS that do not reproduce exactly (the verdicts do): Freya's keys register in "
               f"{out['b_steps']['rigs']['4 freya']['walk']['fields']} / {out['b_steps']['rigs']['4 freya']['run']['fields']} "
               "fields (2553 / 2558; the audit says 54 / 44) with frames {4,16} / {0,9} as the audit says; Zidane's "
               "per-field sound-id reuse (exact in EVERY co-registering field, Steiner in none) counts "
               + ", ".join(f"{k.split()[1]} {v['all_25_38']['exact_equal']}/{v['all_25_38']['fields_both_register']} "
                           f"(player-entry scope {v['zidane_player_entry']['exact_equal']}/"
                           f"{v['zidane_player_entry']['fields_both_register']}; audit {v['audit_fields']})"
                           for k, v in sr.items() if v.get("audit_fields") is not None)
               + ". Steiner's 59 reproduces in the player-entry scope only; no single scope reproduces all six.")
    att = out["fg_ops"]["attach"]
    iss.append(f"ATTACH: the audit's bone 13 x{att['by_bone'].get('13')} / 12 x{att['by_bone'].get('12')} in "
               f"{att['bone_12_13_fields']} fields reproduces; the only OTHER bone a Zidane player / 250 carries is bone 0 "
               f"x{att['by_bone'].get('0', 0)} (fields {att['by_bone_fields'].get('0')}: Qu's Marsh frogs, "
               "AttachObject(255, 250, 0) in Frog_*_SpeakBTN, carrier 250 on fields whose player entries are Zidane 98 "
               "and Quina 273) -> attach_notes, left alone (bone000 is every rig's root).")
    oth = out.get("o6_other_sites", {})
    reach = [k for k, v in oth.items() if v and (v["is_zidane_player"])]
    iss.append("O6 OTHER geoAttach SITES: " + "; ".join(
        f"{k}: entries {v['entries']} {v['models']} player={v['is_player_entry']}" for k, v in oth.items() if v)
        + (f" -- REACHABLE by a dressed Zidane player: {reach}" if reach else
           " -- none carries on a Zidane player entry, so no dressed body reaches them (FieldMap.cs:535's "
           "RestoreAttachModel re-uses attachTargetBoneIndex, which the remap already wrote)."))
    mesh = out["fg_ops"]["mesh"]
    iss.append(f"MESH: 0 of {mesh['exports']} exports show/hide a Zidane player entry's object or 250 (the audit's 0 of "
               f"817 reproduces). {mesh['ops_on_other_player_entries']} mesh ops DO target NON-Zidane player-defining "
               f"entries ({mesh['other_player_entries_by_model']}) -- rideable / vehicle bodies, never dressed, so "
               "O7's netSelfDress gate never sees them.")
    l = out["d_lighting"]["mcfs"]
    iss.append(f"LIGHT: {l['total']} MCFs, every one with the 0xFFFF row, {l['lacking_98_row']} lack a 98 row (the "
               "audit's 818 / 344 reproduce). On those 344 the fallback cannot fire and a dressed body keeps the default "
               "row on s141 too; kit fields (30606) carry no MCF, so light_row reads -1 there.")
    iss.append("F3 on s140: `steps`, `steps_fired_player` and every s141 key are ABSENT on s140, so F3's assertions read "
               "NOT REACHED there, not green; only the s138 instrument (player.model 98, anim 25/38 while moving) is "
               "readable. On s141 under `polish off`: F1, F1b, F2, F2c, F4, F4g, F5, F6, F7, F8 red and F3 green "
               "(bench.* below holds both stages).")
    return iss


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--game", default=None)
    ap.add_argument("--exports", default=str(DEFAULT_EXPORTS))
    ap.add_argument("--memoria", default=str(DEFAULT_MEMORIA))
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--check", action="store_true", help="rebuild in memory and diff the oracle keys (exit 1 on drift)")
    a = ap.parse_args(argv)
    from ff9mapkit import config
    game = config.find_game_path(a.game)
    out = build(Path(a.exports), Path(a.memoria), game)
    fresh = json.loads(json.dumps(out, default=str))
    if a.check:
        frozen = json.loads(Path(a.out).read_text(encoding="utf-8"))
        keys = ("rigs", "a_field250", "b_steps", "c_subs", "d_lighting", "e_hands", "fg_ops", "o6_other_sites",
                "twin_selftest", "bench", "table_disagreements")
        drift = [k for k in keys if fresh.get(k) != frozen.get(k)]
        for k in drift:
            print(f"DRIFT {k}")
        if drift:
            return 1
        print(f"OK: {Path(a.out).name} regenerates exactly")
        return 0
    Path(a.out).write_text(json.dumps(fresh, indent=1) + "\n", encoding="utf-8")
    print("wrote", a.out)
    for x in out["table_disagreements"]:
        print("DISAGREE:", x)
    for x in out["open_issues"]:
        print("ISSUE:", x)
    return 0


if __name__ == "__main__":
    sys.exit(main())
