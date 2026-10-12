"""THE MAP ERASE ON A DEPLOYED FOLDER (2026-10-12): before/after crops of each erased site, both charts.

Renders `world-minimap` for MOD_FOLDER without writing anything (`navimap.render_world_maps`), prints each site's
report (shift, overlap, pixels repainted, or why it was skipped) and writes, per site, the active chart's crop beside
the render's (3x, nearest) to out/<folder>_<chart>_<n>.png. The study's lab: six islands sunk with `world-sink` into a
folder NOT in FolderNames (the game never loads it): (679.033, -386.717) deep water; (553.065, -1127.103) the lagoon
island; (9.909, -22.582) the corner island; (1325.281, -227.083) and (425.098, -1020.0) (Daguerreo) by footprint;
(1446.75, -862.643) small, on the Mist chart too.
Run (from C:\\gd\\Dream-World-IX):  py studies/terrain-malleability/mapchart/before_after.py FF9CustomMap-wmlab
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
KIT = HERE.parents[2] / "ff9mapkit"
sys.path.insert(0, str(KIT))


def main(mod_folder):
    from PIL import Image
    import ff9mapkit
    assert Path(ff9mapkit.__file__).resolve().is_relative_to(KIT.resolve()), ff9mapkit.__file__
    from ff9mapkit.world import navimap as NM
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    summary, im, mim = NM.render_world_maps(mod_folder, verbose=False)
    charts = [("all", summary["erased"], NM.MAP_SPRITE_REL, im)]
    if summary["mist"]:
        charts.append(("mist", summary["mist"]["erased"], NM.MIST_SPRITE_REL, mim))
    for chart, sites, rel, after in charts:
        before, src = NM._load_active_world_map(mod_folder, sprite_rel=rel)
        print(f"{chart}: base {src}")
        for n, r in enumerate(sites):
            print(f"  {n}: {r}")
            a, b = before.crop(r["window"]), after.crop(r["window"])
            z = 3
            pair = Image.new("RGB", (a.width * z * 2 + 6, a.height * z))
            pair.paste(a.resize((a.width * z, a.height * z), Image.NEAREST), (0, 0))
            pair.paste(b.resize((b.width * z, b.height * z), Image.NEAREST), (a.width * z + 6, 0))
            pair.save(out / f"{mod_folder}_{chart}_{n}.png")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "FF9CustomMap-wmlab")
