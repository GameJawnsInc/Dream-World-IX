"""Hidden-enemy battle census: scan EVERY stock battle scene's AI .eb for SetCharacterData
function-code 32 (AddCharacter / APPEAR) and 33 (DelCharacter / SUBMERGE-HIDE) invocations.

Calling convention (cited from the live Memoria tree, read-only):
  - EBin expression writes to VariableSource.Member route through EventEngine.putvobj ->
    SetBattleCharData -> btl_scrp.SetCharacterData(btl, kind, val)  (EBin.cs:1981, EventEngine.cs:1045-1058).
  - In .eb bytecode a Member write is the RPN token B_MEMBER (=41, byte 0x29) + 1 selector byte,
    then a value expression, then a LET-family operator (EBin.cs:866-872 pushes the varcode;
    _membertable.py: "B_MEMBER(N) <expr> B_LET_A WRITES it").
  - So the raw byte pattern is \x29\x20 (code 32) / \x29\x21 (code 33) INSIDE an expression operand.
    We scan EXPRESSION-AWARE (the kit's exact engine-mirroring decoder), not raw-grep, because 0x29
    is also a command opcode and 0x20/0x21 occur freely in immediates.

Enumerates all battle .eb via p0data7.bin (eventbinary/battle/us/evt_battle_*.eb.bytes),
maps scene name -> battle id via p0data2.bin raw17 containers, and enemy-type names via the
battle <id>.mes (ResourceManager index in mainData/resources.assets), exactly like the kit does.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

KIT = r"C:\gd\Dream-World-IX\.claude\worktrees\multiplayer-plan-execution-d30b02\ff9mapkit"
sys.path.insert(0, KIT)

from ff9mapkit import config                                   # noqa: E402
from ff9mapkit.eb.model import EbScript                        # noqa: E402
from ff9mapkit.battle.battleai import _decode_func_pretty, _tag_role  # noqa: E402
from ff9mapkit.battle import scene_codec                       # noqa: E402
from ff9mapkit.workspace.battledoc import _mes_strings         # noqa: E402

import UnityPy                                                 # noqa: E402

OUT_DIR = Path(__file__).parent
GAME = config.find_game_path(None)
SA = GAME / "StreamingAssets"

RE32 = re.compile(r"B_MEMBER\(32\)")
RE33 = re.compile(r"B_MEMBER\(33\)")
RE53 = re.compile(r"B_MEMBER\(53\)")   # secondary: 'disappear' render-only vanish writes


def _raw_bytes(d):
    from ff9mapkit.extract import _raw_bytes as rb
    return rb(d)


def load_battle_ebs():
    """{scene_name: eb_bytes} for the 'us' battle event binaries in p0data7.bin."""
    env = UnityPy.load(str(SA / "p0data7.bin"))
    rx = re.compile(r"eventbinary/battle/us/evt_battle_([^/]+)\.eb\.bytes$", re.I)
    out = {}
    for o in env.objects:
        if o.type.name != "TextAsset":
            continue
        c = (getattr(o, "container", None) or "").lower()
        m = rx.search(c)
        if m:
            out[m.group(1).upper()] = _raw_bytes(o.read())
    return out


def load_scene_meta():
    """{scene_name: (battle_id, raw16_bytes)} from p0data2.bin battlescene containers."""
    env = UnityPy.load(str(SA / "p0data2.bin"))
    rx17 = re.compile(r"battlescene/evt_battle_([^/]+)/(\d+)\.raw17\.bytes$", re.I)
    rx16 = re.compile(r"battlescene/evt_battle_([^/]+)/dbfile0000\.raw16\.bytes$", re.I)
    ids, raw16 = {}, {}
    for o in env.objects:
        if o.type.name != "TextAsset":
            continue
        c = (getattr(o, "container", None) or "").lower()
        m = rx17.search(c)
        if m:
            ids[m.group(1).upper()] = int(m.group(2))
            continue
        m = rx16.search(c)
        if m:
            raw16[m.group(1).upper()] = _raw_bytes(o.read())
    return {n: (ids.get(n), raw16.get(n)) for n in set(ids) | set(raw16)}


def load_mes_index():
    """battle_id -> us .mes bytes, via the ResourceManager m_Container index (the faithful path)."""
    data_dir = GAME / "x64" / "FF9_Data"
    if not (data_dir / "resources.assets").exists():
        data_dir = GAME / "FF9_Data"
    env = UnityPy.load(str(data_dir / "mainData"), str(data_dir / "resources.assets"))
    rm = next((o.read() for o in env.objects
               if getattr(getattr(o, "type", None), "name", "") == "ResourceManager"), None)
    if rm is None:
        raise LookupError("no ResourceManager in mainData")
    rx = re.compile(r"^embeddedasset/text/us/battle/(\d+)\.mes$", re.I)
    out = {}
    for path, ptr in rm.m_Container:
        m = rx.match(str(path).lower())
        if m:
            try:
                out[int(m.group(1))] = _raw_bytes(ptr.read())
            except Exception:
                pass
    return out


def main():
    ebs = load_battle_ebs()
    meta = load_scene_meta()
    mes_by_id = load_mes_index()
    print(f"battle .eb (us): {len(ebs)} scenes; scene meta: {len(meta)}; mes ids: {len(mes_by_id)}")

    hits = []      # per-scene records
    n53_only = []
    decode_fail = []
    for name in sorted(ebs):
        eb_bytes = ebs[name]
        battle_id, raw16 = meta.get(name, (None, None))
        typ_count = None
        type_names = []
        if raw16:
            try:
                sc = scene_codec.parse_scene(raw16)
                typ_count = sc.typ_count
            except Exception:
                pass
        if battle_id is not None and battle_id in mes_by_id:
            strings = _mes_strings(mes_by_id[battle_id])
            type_names = strings[:typ_count] if typ_count else strings
        try:
            eb = EbScript.from_bytes(eb_bytes)
        except Exception as ex:
            decode_fail.append((name, repr(ex)))
            continue
        scene_hits = []
        has53 = False
        for e in eb.entries:
            if e.empty:
                continue
            etype_name = None
            if e.index >= 1 and e.index - 1 < len(type_names):
                etype_name = type_names[e.index - 1]
            for f in e.funcs:
                end = min(f.abs_end, len(eb.data))
                try:
                    for off, mn, operands in _decode_func_pretty(eb.data, f.abs_start, end):
                        text = f"{mn}({', '.join(operands)})"
                        c32 = len(RE32.findall(text))
                        c33 = len(RE33.findall(text))
                        if RE53.search(text):
                            has53 = True
                        if c32 or c33:
                            scene_hits.append({
                                "entry": e.index, "entry_role": ("Main_Init" if e.index == 0
                                                                 else f"type{e.index - 1}"),
                                "enemy_type_name": etype_name,
                                "tag": f.tag, "tag_role": _tag_role(f.tag),
                                "off": off, "code32": c32, "code33": c33,
                                "instr": text,
                            })
                except IndexError:
                    pass
        if scene_hits:
            hits.append({
                "scene": name, "battle_id": battle_id, "typ_count": typ_count,
                "enemy_names": type_names, "hits": scene_hits,
                "n32": sum(h["code32"] for h in scene_hits),
                "n33": sum(h["code33"] for h in scene_hits),
            })
        elif has53:
            n53_only.append({"scene": name, "battle_id": battle_id, "enemy_names": type_names})

    (OUT_DIR / "hidden-enemy-census.json").write_text(
        json.dumps({"hits": hits, "disappear53_only": n53_only, "decode_fail": decode_fail},
                   indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"scenes with code-32/33 AI writes: {len(hits)}")
    print(f"scenes with only member-53 (disappear) writes: {len(n53_only)}")
    print(f"decode failures: {len(decode_fail)}")
    for h in hits:
        nm = ", ".join(dict.fromkeys(n for n in h["enemy_names"])) or "?"
        print(f"  {h['scene']:<12} id={h['battle_id']:<4} 32x{h['n32']} 33x{h['n33']}  [{nm}]")


if __name__ == "__main__":
    main()
