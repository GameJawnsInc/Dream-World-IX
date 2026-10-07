"""VERIFY C9's "inert in stock" over ALL 13 world dispatchers, not only WORLD00.

sea_event_quad.py checks the event-1 quad that sea4f carries in every IsSea cell (cell (2bx+1, 2by+1), event 1)
against EVT_WORLD_WORLD00's object-0 cell tags only. The engine routes WorldEvent to object 0 of whichever world
dispatcher is running (EventDB 9000..9012 = evt_world_world00..12). This script repeats the collision test for every
dispatcher, on both discs' IsSea sets (per-block prefab IsSea flags from out/consumption_census.json).

Read-only on the install. Rerun:  py studies/terrain-malleability/consumption/verify_sea_event_all_worlds.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
import UnityPy                                         # noqa: E402
from ff9mapkit.eb.model import EbScript                # noqa: E402
from ff9mapkit.world.entrance import unpack_cell_tag   # noqa: E402

HERE = Path(__file__).resolve().parent
SA = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\StreamingAssets")


def main():
    C = json.loads((HERE / "out" / "consumption_census.json").read_text(encoding="utf-8"))
    sea = {d: sorted(tuple(map(int, k.split("/")[1].split(","))) for k, p in C["prefabs"].items()
                     if k.startswith(f"d{d}/") and not k.endswith("f") and p["flags"].get("IsSea"))
           for d in (1, 4)}
    print({d: len(v) for d, v in sea.items()})
    env = UnityPy.load(str(SA / "p0data7.bin"))
    scripts = {}
    for k, o in env.container.items():
        kl = k.lower()
        if "eventbinary/world/us/evt_world_world" in kl and o.type.name == "TextAsset":
            m = o.read().m_Script
            scripts[kl.rsplit("/", 1)[1].split(".")[0]] = m.encode("utf-8", "surrogateescape") if isinstance(m, str) else bytes(m)
    out = {}
    calib = None
    for name in sorted(scripts):
        s = EbScript(scripts[name])
        tags = set()
        for f in s.entry(0).funcs:
            c = unpack_cell_tag(f.tag)
            if c is not None:
                tags.add(c)
        hits = {}
        for d in (1, 4):
            hits[d] = [((bx, by), (2 * bx + 1, 2 * by + 1)) for (bx, by) in sea[d] if (2 * bx + 1, 2 * by + 1, 1) in tags]
        if name.endswith("world00"):
            calib = len(tags)
        out[name] = {"cell_tags": len(tags), "event1_tags": sum(1 for t in tags if t[2] == 1),
                     "sea_quad_hits_d1": hits[1], "sea_quad_hits_d4": hits[4]}
        print(f"{name}: {len(tags)} cell tags ({out[name]['event1_tags']} event-1); "
              f"sea-quad collisions d1={hits[1]} d4={hits[4]}")
    ok = calib == 53                                   # WORLD00 must reproduce the lane's 53 cell tags
    print(f"CALIB WORLD00 cell tags = {calib} (lane: 53): {'OK' if ok else 'FAIL'}")
    (HERE / "out" / "verify_sea_event_all_worlds.json").write_text(json.dumps(
        {"calib_ok": ok, "sea_counts": {d: len(v) for d, v in sea.items()}, "worlds": out}, indent=1, default=str),
        encoding="utf-8")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
