"""Regenerate ``_modelalias.py`` (the engine's model-name -> donor-prefab alias chain) from a Memoria
checkout.

A *maintainer* tool, not part of the runtime. Same provenance category as ``_modeldb.py`` /
``_animdb.py``: it transcribes Memoria's OPEN-SOURCE ``ModelFactory`` rename tables (Memoria's
reverse-engineered name->name interop labels for FF9's model resources), NOT extracted game data --
no model geometry is ever read or shipped.

    python -m ff9mapkit._regen_modelalias --memoria "C:/path/to/Memoria"

WHY the tables matter: ~103 of the 710 GEO catalog ids ship NO prefab under their own id (character
battle forms, boss/monster aliases, Zidane's alt outfits, three accessories, ...). The engine loads
their GEOMETRY from a donor prefab found by ``CheckUpscale`` -> ``GetRenameModelPath``
(``Global/Model/ModelFactory.cs``); :func:`ff9mapkit.models.extract.resolve_prefab` replays that
chain from these baked tables. Five pieces are captured:

  * ``UPSCALE``          -- ``ModelFactory.upscaleTable`` (requested name -> HD-rename space)
  * ``REVERT_UPSCALE``   -- ``ModelFactory.revertUpscaleTable`` (HD name -> the shipping prefab name)
  * ``DBALL_SWITCH``     -- the ``GetNameFromFF9DBALL`` switch (UP3/4/5 Zidane + UP4 Garnet cases)
  * ``GEOID_SPECIALS``   -- ``GetGEOID``'s hardcoded ids for two names ABSENT from the GEO table
  * ``SUB_TYPE_GEO_IDS`` -- ``GetRenameModelPath``'s ``geoId == 429 || 430 -> ModelType.sub`` override
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

_PAIR = re.compile(r'\{\s*"([^"]+)"\s*,\s*"([^"]+)"\s*\}')
_CASE = re.compile(r'case\s+"([^"]+)"\s*:\s*geoName\s*=\s*"([^"]+)"\s*;')
_SPECIAL = re.compile(r'\.Equals\("([^"]+)"\)\)\s*return\s+(\d+)\s*;')
_SUB_IDS = re.compile(r'if\s*\(geoId\s*==\s*(\d+)\s*\|\|\s*geoId\s*==\s*(\d+)\)\s*modelType\s*=\s*ModelType\.sub\s*;')


def _source(memoria_root: Path) -> str:
    return (memoria_root / "Assembly-CSharp" / "Global" / "Model" / "ModelFactory.cs"
            ).read_text(encoding="utf-8", errors="replace")


def _dict_block(src: str, marker: str) -> dict:
    """The string->string initializer pairs of the C# Dictionary declared at ``marker``."""
    i = src.index(marker)
    j = src.index("};", i)
    return dict(_PAIR.findall(src[i:j]))


def _method_body(src: str, marker: str) -> str:
    i = src.index(marker)
    j = src.find("public static", i + 1)
    return src[i:j if j != -1 else len(src)]


def parse_tables(memoria_root: Path) -> dict:
    src = _source(memoria_root)
    upscale = _dict_block(src, "upscaleTable = new Dictionary")
    revert = _dict_block(src, "revertUpscaleTable = new Dictionary")
    dball = dict(_CASE.findall(_method_body(src, "GetNameFromFF9DBALL(String modelName)")))
    specials = {name: int(gid) for name, gid in
                _SPECIAL.findall(re.sub(r"\s+", " ", _method_body(src, "GetGEOID(String modelName)")))}
    m = _SUB_IDS.search(re.sub(r"\s+", " ", _method_body(src, "GetRenameModelPath(String upscalePath)")))
    sub_ids = sorted(int(g) for g in m.groups()) if m else []
    for label, table, floor in (("upscaleTable", upscale, 100), ("revertUpscaleTable", revert, 80),
                                ("GetNameFromFF9DBALL switch", dball, 5), ("GetGEOID specials", specials, 2),
                                ("sub-type override ids", sub_ids, 2)):
        if len(table) < floor:
            raise ValueError(f"parsed only {len(table)} {label} entries (expected >= {floor}) -- "
                             f"ModelFactory.cs layout changed; update the parser")
    return {"UPSCALE": upscale, "REVERT_UPSCALE": revert, "DBALL_SWITCH": dball,
            "GEOID_SPECIALS": specials, "SUB_TYPE_GEO_IDS": sub_ids}


def render(t: dict) -> str:
    header = (
        '"""Auto-generated FF9 model-alias registry: the engine\'s model-name -> donor-prefab rename chain.\n'
        "\n"
        "DO NOT EDIT BY HAND. Regenerate with:  python -m ff9mapkit._regen_modelalias --memoria <path>\n"
        "Source: Memoria Assembly-CSharp/Global/Model/ModelFactory.cs (upscaleTable / revertUpscaleTable /\n"
        "GetNameFromFF9DBALL / GetGEOID / GetRenameModelPath, open-source) -- Memoria's reverse-engineered\n"
        "name->name interop labels; NOT extracted game data (see docs/PROVENANCE.md).\n"
        "\n"
        "~103 GEO catalog ids ship no prefab under their own id: a character BATTLE form's body is the\n"
        "same prefab its FIELD form loads (GEO_MAIN_B0_000 -> GEO_MAIN_UP0_ZDN -> GEO_MAIN_F0_ZDN = 98),\n"
        "bosses borrow character bodies, Zidane's alt outfits share 98, three accessories point at their\n"
        "F1 twin. The engine resolves a requested name UP into the HD-rename space (UPSCALE =\n"
        "CheckUpscale) then back DOWN to the shipping prefab (REVERT_UPSCALE, falling back to\n"
        "DBALL_SWITCH + a second revert = GetRenameModelPath/GetNameFromFF9DBALL); GEOID_SPECIALS pins\n"
        "two names the GEO table never lists; SUB_TYPE_GEO_IDS forces the two mask prefabs into\n"
        "models/5/. Sole reader: ff9mapkit.models.extract.resolve_prefab -- animations and identity keep\n"
        "the REQUESTED id (resolve_geo); only the GEOMETRY location goes through this chain.\n"
        '"""\n'
    )
    lines = [header]

    def dump(name: str, table: dict, comment: str):
        lines.append(f"# {comment}")
        lines.append(name + " = {")
        for k in sorted(table):
            lines.append(f"    {k!r}: {table[k]!r},")
        lines.append("}")
        lines.append("")

    dump("UPSCALE", t["UPSCALE"], "ModelFactory.upscaleTable -- requested name -> HD-rename space (CheckUpscale)")
    dump("REVERT_UPSCALE", t["REVERT_UPSCALE"],
         "ModelFactory.revertUpscaleTable -- HD name -> the name whose prefab ships (GetRenameModelPath)")
    dump("DBALL_SWITCH", t["DBALL_SWITCH"],
         "GetNameFromFF9DBALL's switch -- pre-revert renames for the UP3/4/5 Zidane + UP4 Garnet forms")
    dump("GEOID_SPECIALS", t["GEOID_SPECIALS"],
         "GetGEOID's hardcoded ids -- these two names are ABSENT from the GEO id<->name table entirely")
    lines.append("# GetRenameModelPath: these resolved GEO ids are forced to ModelType.sub (models/5/)")
    lines.append(f"SUB_TYPE_GEO_IDS = frozenset({t['SUB_TYPE_GEO_IDS']!r})")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Regenerate _modelalias.py from Memoria source.")
    ap.add_argument("--memoria", required=True, help="path to a Memoria source checkout")
    args = ap.parse_args(argv)
    tables = parse_tables(Path(args.memoria))
    target = Path(__file__).with_name("_modelalias.py")
    target.write_text(render(tables), encoding="utf-8", newline="\n")
    print(f"wrote {target}  (" + ", ".join(f"{k}={len(v)}" for k, v in tables.items()) + ")")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
