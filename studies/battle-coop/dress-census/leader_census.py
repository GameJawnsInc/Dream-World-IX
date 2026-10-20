"""THE LEADER CENSUS (battle co-op s143; owner decision 2026-10-19: "the guest never commands the host's leader") -- which
bodies name the character the HOST WALKS AS, for NetSyncBattle.LeaderCharForModel's census rows (PcVariantModels /
PcVariantChars) and NoteWorldLeader's world-map walker (WorldWalkerModel).

The engine reads the leader off this machine's own controlled field body: its genuine model -> NetSyncVisitor.RigForModel ->
RigToChar (the 13-row rig table), else a KNOWN PLAYABLE-CHARACTER VARIANT -> its character, else no character (the leader
latched before is KEPT -- NextLeader; none since the title = the positional rule). This census is where "known variant" comes
from: every model a PLAYER-defining entry (DefinePlayerCharacter) SetModels in the 817 field-script exports, named through
Memoria's open-source FF9BattleDB.GEO table; a variant is a GEO_MAIN_* / GEO_SUB_* body outside the rig table whose GEO
FAMILY (the name's last token) is a rig body's -- GEO_MAIN_F1_STN is Steiner's family STN -- or a `_ZD*` body (Zidane's ZDN /
ZDD). [review s143 field-2: the first census kept Zidane's variants only; `zidane_variants` stays, the Zidane subset.]

THE WORLD MAP (review s143 own-1: a world-map save loads with no field seen): its walker is the moving actor's STATUS
(WMUIData.StatusNo = ff9.w_moveActorPtr's index), named by ff9.cs's open-source k_moveCHRStatus_* constants; WMActor.cs builds
exactly two on-foot bodies, "Zidane" and "Dagger" -- Dagger (status 2) walks as Garnet, every other status (Zidane on foot, a
chocobo, a ship) is Zidane's party: Zidane. `world_leader` records that table.

READ-ONLY. Sources: the Hades Workshop exports (``--exports``, test2_N.txt, FIRST language block only -- the census convention,
parsed by rigs_8_11.parse_export) and the Memoria clone's FF9BattleDB.GEO.cs and ff9.cs (``--memoria``). Output: numbers and
open-source names only (zero game bytes) -> leader_census.json next to this file.

    py -X utf8 studies/battle-coop/dress-census/leader_census.py [--exports <dir>] [--memoria <clone>]
    py -X utf8 studies/battle-coop/dress-census/leader_census.py --check     # rebuild in memory, diff the frozen JSON
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import rigs_8_11 as R                                    # noqa: E402 - the census's own export parser and tables

OUT = HERE / "leader_census.json"
#: the rig table's bodies (NetSyncVisitor.Rigs' model column, rows 0-12) -> the rig row
RIG_MODELS = {98: 0, 8: 1, 185: 2, 5489: 3, 192: 4, 273: 5, 443: 6, 509: 7, 220: 8, 107: 9, 109: 10, 5467: 11, 204: 12}
#: NetSyncVisitor.RigToChar: rows 0-7 -> CharacterId 0-7, row 8 (the moogle) -> none, rows 9-12 -> 8-11
RIG_TO_CHAR = {**{r: r for r in range(8)}, 9: 8, 10: 9, 11: 10, 12: 11}
#: the k_moveCHRStatus_* constant whose walker is NOT Zidane's party (WMActor.cs's second on-foot body), -> its CharacterId
WORLD_NON_ZIDANE = {"Dagger": 2}


def _family(geo: str) -> str:
    return geo.rsplit("_", 1)[-1]


def build(exports: Path, memoria: Path) -> dict:
    geo = dict(R.source_table(memoria / "Assembly-CSharp" / "Global" / "ff9" / "Battle" / "FF9BattleDB.GEO.cs",
                              r'\{\s*(\d+)\s*,\s*"(GEO_[A-Z0-9_]+)"\s*\}'))
    man = R.manifest(R.MANIFEST)
    fields = collections.defaultdict(set)                 # model -> {field id} where a player-defining entry SetModels it
    entries = collections.Counter()                       # model -> player-defining entries that SetModel it
    files = sorted(exports.glob("test2_*.txt"), key=lambda p: int(p.stem.split("_")[1]))
    for f in files:
        fid = man.get(f.name, (None, None))[0]
        for e in R.parse_export(f):
            if not any(op == "DefinePlayerCharacter" for fn in e["funcs"] for op, _a, _c in fn["ops"]):
                continue
            models = {R.ival(args[0]) for fn in e["funcs"] for op, args, _c in fn["ops"]
                      if op == "SetModel" and args and R.ival(args[0]) is not None}
            for m in models:
                entries[m] += 1
                if fid is not None:
                    fields[m].add(fid)
    rows = [{"model": m, "geo": geo.get(m), "rig": RIG_MODELS.get(m), "entries": entries[m], "fields": sorted(fields[m])}
            for m in sorted(entries, key=lambda m: (-entries[m], m))]
    zid_geo = sorted((i, n) for i, n in geo.items() if "_ZD" in n)
    variants = [r["model"] for r in rows if r["geo"] and "_ZD" in r["geo"] and r["rig"] is None]
    # the playable-character variants: a main body's GEO family, outside the rig table (the moogle's row 8 names no one)
    family_char = {_family(geo[m]): RIG_TO_CHAR[r] for m, r in RIG_MODELS.items() if m in geo and r in RIG_TO_CHAR}
    pc = []
    for r in rows:
        name = r["geo"]
        if not name or r["rig"] is not None or not name.startswith(("GEO_MAIN_", "GEO_SUB_")):
            continue
        char = 0 if "_ZD" in name else family_char.get(_family(name))
        if char is not None:
            pc.append({"model": r["model"], "geo": name, "char": char, "entries": r["entries"], "fields": r["fields"]})
    # the world map's walker: ff9.cs's k_moveCHRStatus_* table (open source)
    ff9cs = (memoria / "Assembly-CSharp" / "Global" / "ff9" / "ff9.cs").read_text(encoding="utf-8", errors="replace")
    statuses = [(int(v), n) for n, v in re.findall(r"public const Int32 k_moveCHRStatus_(\w+) = (\d+);", ff9cs)]
    world = [{"status": s, "name": n, "leader": WORLD_NON_ZIDANE.get(n, 0)} for s, n in sorted(statuses) if s > 0]
    return {
        "source": {"exports": len(files), "convention": "first language block; a PLAYER entry = one with DefinePlayerCharacter",
                   "names": "FF9BattleDB.GEO.cs (open source)", "world": "ff9.cs k_moveCHRStatus_* (open source)"},
        "player_models": rows,
        "zidane_geo_table": [{"model": i, "geo": n} for i, n in zid_geo],
        "zidane_variants": variants,
        "zidane_unworn": [i for i, _n in zid_geo if i not in entries],
        "pc_variants": pc,
        "world_leader": world,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--exports", type=Path, default=R.DEFAULT_EXPORTS)
    ap.add_argument("--memoria", type=Path, default=R.DEFAULT_MEMORIA)
    ap.add_argument("--check", action="store_true", help="rebuild in memory and diff against the frozen JSON")
    a = ap.parse_args(argv)
    doc = build(a.exports, a.memoria)
    if a.check:
        frozen = json.loads(OUT.read_text(encoding="utf-8"))
        same = frozen == doc
        print("leader census: " + ("matches the frozen JSON" if same else "DIFFERS from the frozen JSON"))
        return 0 if same else 1
    OUT.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {OUT}: pc variants {[(v['model'], v['char']) for v in doc['pc_variants']]}; zidane variants "
          f"{doc['zidane_variants']} (unworn {doc['zidane_unworn']}); world {[(w['status'], w['leader']) for w in doc['world_leader']]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
