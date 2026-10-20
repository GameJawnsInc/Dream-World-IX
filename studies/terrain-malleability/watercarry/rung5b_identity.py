"""RUNG5.md 5b's accept, offline, into scratch folders OUTSIDE the install (nothing in the game is written):

  1. RECIPE = CLI BYTES: `world-river --at 512,128` into scratch A and a one-row `[[river]]` recipe through `world-fuse`
     into scratch B write the same WorldMap tree byte for byte (disc 1 and the disc-4 mirror; the ledger, the manifest
     and backups aside).
  2. THE REMOVAL OWNS A FUSED RIVER: every file the recipe wrote is world-river's at (8,-2) by the ledger's pipeline
     tag, though world-fuse wrote it -- so `world-river --remove` can take it out.
  3. A RELIEF ROW ON THE RIVER ISLAND: `[[river]]` + `[[forest]]` (on the island's open lawn) into scratch C composes
     clean, the forest reading the river island the base tier just deployed.

THE STACK READ is narrowed to the target folder for this run only (`river.stack_folders` -> []): the live
FF9CustomMap-world holds the live river at 512,128, so the stack gate refuses every placement there -- it is a
refusal gate, and it never shapes a byte. Everything else is the shipped path (`cli.main`).
RUN:  py studies/terrain-malleability/watercarry/rung5b_identity.py [SCRATCH_DIR]   (-> out/rung5b.json)
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
import ff9mapkit  # noqa: E402
assert Path(ff9mapkit.__file__).resolve().is_relative_to(ROOT), ff9mapkit.__file__
from ff9mapkit import cli, config  # noqa: E402
from ff9mapkit.world import mesh as M, river as R  # noqa: E402

AT = (512.0, 128.0)
SHIFT = (8, -2)
FOREST_NEAR = (49.0, -824.0)            # the river island's roomiest open lawn (the rung-5 recon's r~28 disc)
#: the relief verbs are not seam-aware (their read window must stay inside one wrapped span), and the river island
#: straddles the world's x seam: the default 96u reach from x 49 crosses x = 0, so the row keeps its window east of it
FOREST_REACH = 40.0
SKIP = (".bak-", ".prerim")


def tree(root: Path) -> dict:
    wm = root / "FF9_Data" / "WorldMap"
    out = {}
    for p in sorted(wm.rglob("*")) if wm.is_dir() else ():
        if p.is_file() and p.name not in (M.LEDGER_NAME, "world_manifest.json") and not any(s in p.name for s in SKIP):
            out[p.relative_to(root).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def main():
    scratch = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp(prefix="ff9-rung5b-"))
    game = config.find_game_path(None)
    assert not scratch.resolve().is_relative_to(game.resolve()), "scratch must sit outside the install"
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True)
    A, B, C = scratch / "cli", scratch / "fuse", scratch / "fuse_forest"
    R.stack_folders = lambda game=None: []                       # the stack gate narrowed (docstring)
    rep = {"scratch": str(scratch), "at": AT}

    from ff9mapkit.world import discmirror as DM
    rc = cli.main(["world-river", "--mod-folder", str(A), "--at", f"{AT[0]:g},{AT[1]:g}"])
    rep["cli_rc"] = rc
    # the auto-mirror cannot run on an absolute scratch folder (its parent holds no install to compare against);
    # mirror each explicitly against the real install's stock (read-only), the fused one under the tag a live run uses
    cells_a = sorted({(int(m[1]), int(m[2])) for k in tree(A) for m in [R._STAGED.search(k)] if m})
    rep["mirror_cli"] = {k: v for k, v in DM.mirror(str(A), cells=set(cells_a), atomic=True,
                                                     log=lambda *a: None).items() if isinstance(v, (int, str))}
    recipe = scratch / "river.toml"
    recipe.write_text(f"[[river]]\ndonor = \"cluster-c\"\nat = [{AT[0]:g}, {AT[1]:g}]\n", encoding="utf-8")
    rep["fuse_rc"] = cli.main(["world-fuse", str(recipe), "--mod-folder", str(B)])
    with M.ledger_pipeline(R.REMOVE_VERB, at=list(AT), donor="cluster-c"):
        rep["mirror_fuse"] = {k: v for k, v in DM.mirror(str(B), cells=set(cells_a), atomic=True,
                                                          log=lambda *a: None).items() if isinstance(v, (int, str))}
    ta, tb = tree(A), tree(B)
    rep["identity"] = {"cli_files": len(ta), "fuse_files": len(tb),
                       "by_disc": {d: sum(1 for k in ta if f"/Disc{d}/" in k) for d in (1, 4)},
                       "only_cli": sorted(set(ta) - set(tb))[:8], "only_fuse": sorted(set(tb) - set(ta))[:8],
                       "differ": sorted(k for k in set(ta) & set(tb) if ta[k] != tb[k])[:8]}
    rep["identity"]["ok"] = bool(ta) and ta == tb

    cells = sorted({(int(m[1]), int(m[2])) for k in tb for m in [R._STAGED.search(k)] if m})
    own = R.deploy_ownership(cells, str(B), shift=SHIFT, discs=(1, 4))
    rows = M.read_ledger(B)
    rep["ownership"] = {"cells": len(cells), "owned": len(own["owned"]), "foreign": [(str(p), why) for p, _d, why
                                                                                     in own["foreign"][:4]],
                        "ledger_rows": len(rows),
                        "tagged": sum(1 for r in rows if (r.get("pipeline") or {}).get("verb") == R.REMOVE_VERB),
                        "argv_verb": sorted({str(M.ledger_verb(r.get("argv"))) for r in rows})}
    rep["ownership"]["ok"] = len(own["owned"]) == len(tb) and not own["foreign"]

    recipe2 = scratch / "river_forest.toml"
    recipe2.write_text(f"[[river]]\nat = [{AT[0]:g}, {AT[1]:g}]\n\n[[forest]]\nnear = [{FOREST_NEAR[0]:g}, "
                       f"{FOREST_NEAR[1]:g}]\nreach = {FOREST_REACH:g}\n", encoding="utf-8")
    rep["forest_rc"] = cli.main(["world-fuse", str(recipe2), "--mod-folder", str(C)])
    man = C / "FF9_Data" / "WorldMap" / "world_manifest.json"
    entries = json.loads(man.read_text(encoding="utf-8"))["entries"] if man.is_file() else []
    rep["forest"] = {"steps": [(e["table"], len(e["files"])) for e in entries], "ok": rep["forest_rc"] == 0}

    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / "rung5b.json").write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: rep[k] for k in ("cli_rc", "fuse_rc", "identity", "ownership", "forest_rc", "forest")},
                     indent=1, default=str))


if __name__ == "__main__":
    main()
