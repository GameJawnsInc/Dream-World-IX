"""Regenerate ``_fieldtable.py`` (FBG field-folder -> event-script name) from a Memoria checkout.

This is a *maintainer* tool, not part of the runtime -- the table is baked into ``_fieldtable.py``
so the kit needs no Memoria source to map an imported field's background folder to its event ``.eb``.
Run it only when updating to a newer Memoria whose field registry changed:

    python -m ff9mapkit._regen_fieldtable --memoria "C:/path/to/Memoria"

It reads two base (vanilla) registries, both keyed by field id:
  * ``Global/Event/Engine/EventEngineUtils.cs``  -> ``eventIDToFBGID``  (id -> "FBG_N..")
  * ``Global/ff9/FF9DBAll.Events.cs``             -> ``EventDB``        (id -> "EVT_..")
and joins them on field id to emit ``FBG_TO_EVT = {fbg_lower: [field_id, "EVT_.."]}`` -- exactly the
mapping ``import`` needs (an imported field is named by its FBG background folder; its script is the
EVT_ event binary in p0data). EventDB also holds battle/world/startup events; the join on FBG ids
keeps only the field maps.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

_PAIR = re.compile(r'\{\s*(\d+)\s*,\s*"([^"]+)"\s*\}')


def _dict_block(src: str, name: str) -> str:
    """The text of a ``name = new Dictionary<Int32, String> { ... };`` literal (up to the first ``};``)."""
    m = re.search(re.escape(name) + r"\s*=\s*new\s+Dictionary<Int32,\s*String>\s*\{(.*?)\n\s*\};",
                  src, re.S)
    if not m:
        raise ValueError(f"could not find dictionary {name!r}")
    return m.group(1)


def parse_tables(memoria_root: Path):
    eng = (memoria_root / "Assembly-CSharp" / "Global" / "Event" / "Engine" / "EventEngineUtils.cs"
           ).read_text(encoding="utf-8", errors="replace")
    evt = (memoria_root / "Assembly-CSharp" / "Global" / "ff9" / "FF9DBAll.Events.cs"
           ).read_text(encoding="utf-8", errors="replace")
    id_to_fbg = {int(i): name for i, name in _PAIR.findall(_dict_block(eng, "eventIDToFBGID"))}
    id_to_evt = {int(i): name for i, name in _PAIR.findall(_dict_block(evt, "EventDB"))}
    table = {}
    by_id = {}
    for fid, fbg in id_to_fbg.items():
        evt_name = id_to_evt.get(fid)
        if evt_name:                                    # join on field id; skip ids with no event entry
            # FOLDER-keyed (lossy: several field ids can share ONE background folder -- the same room at
            # different story beats -- so the LAST wins; fine for the NAME-based `import` resolver).
            table[fbg.lower()] = [fid, evt_name]
            # ID-keyed (COMPLETE: every field id kept, so a shared-folder field like 52/3008 isn't dropped).
            # The chain walk + whole-zone fork key on this so they don't miss ~142 of the 818 real fields.
            by_id[fid] = [fbg.lower(), evt_name]
    return table, by_id, len(id_to_fbg), len(id_to_evt)


def render(table: dict, by_id: dict) -> str:
    header = ('"""Auto-generated FF9 field registry: background folder (FBG) <-> event-script name.\n\n'
              "DO NOT EDIT BY HAND. Regenerate with:  python -m ff9mapkit._regen_fieldtable\n"
              "Source (both keyed by field id, joined here on id):\n"
              "  Memoria  Assembly-CSharp/Global/Event/Engine/EventEngineUtils.cs  (eventIDToFBGID)\n"
              "           Assembly-CSharp/Global/ff9/FF9DBAll.Events.cs            (EventDB)\n\n"
              "  FBG_TO_EVT[fbg_folder_lowercase] = [field_id, 'EVT_<name>']   -- FOLDER-keyed (NAME import).\n"
              "  FIELD_BY_ID[field_id]            = [fbg_folder_lowercase, 'EVT_<name>']   -- ID-keyed, COMPLETE.\n\n"
              "Several field ids can share ONE FBG folder (the same room at different story beats), so the\n"
              "folder-keyed FBG_TO_EVT drops all but one -- the id-keyed FIELD_BY_ID keeps every field, which\n"
              "the chain walk + whole-zone fork need (else ~142 of the 818 real fields go missing + their\n"
              "warps leak to the live game).\n"
              '"""\n')
    lines = [header, "", "FBG_TO_EVT = {"]
    for fbg in sorted(table):
        fid, evt = table[fbg]
        lines.append(f'    {fbg!r}: [{fid}, {evt!r}],')
    lines += ["}", "", "FIELD_BY_ID = {"]
    for fid in sorted(by_id):
        fbg, evt = by_id[fid]
        lines.append(f'    {fid}: [{fbg!r}, {evt!r}],')
    lines.append("}")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Regenerate _fieldtable.py from Memoria source.")
    ap.add_argument("--memoria", required=True, help="path to a Memoria source checkout")
    args = ap.parse_args(argv)
    table, by_id, n_fbg, n_evt = parse_tables(Path(args.memoria))
    target = Path(__file__).with_name("_fieldtable.py")
    target.write_text(render(table, by_id), encoding="utf-8", newline="\n")
    print(f"wrote {target}  (eventIDToFBGID={n_fbg}, EventDB={n_evt}, folder maps={len(table)}, "
          f"id maps={len(by_id)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
