"""Which refusals do carries meet in the editor, and where do they mark? Every donor the carry card lists (each at
rot 0 and 90), dry runs at targets its cheap laws pass, on a fresh draft of the live folder; in-process."""
import collections, json, random, sys
from pathlib import Path
WT = Path(r"C:\gd\Dream-World-IX\.claude\worktrees\terrain-shaping-continue-4647b2\ff9mapkit")
sys.path.insert(0, str(WT))
from ff9mapkit import cli
from ff9mapkit.world import draft as D, islandedit as IE, mesh as M, river as RV, transplantedit as TE
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
OUT = Path(sys.argv[1]); N = int(sys.argv[2])
d = D.ensure_draft(GAME / "FF9CustomMap-world", game=GAME, root=OUT / "d")
land = IE.stock_land(game=GAME)
stack = [str(d)] + [str(GAME / f) for f in RV.stack_folders(GAME) if f != "FF9CustomMap-world"]
occ = lambda bs: {tuple(b): ["x"] for b in bs if any(M.existing_overrides([tuple(b)], fo, disc=k, game=GAME)
                                                     for fo in stack for k in (1, 4))}
rng = random.Random(7)
res = []
for r in TE.donors():
    size = tuple(r.get("size") or (1, 1))
    dl = TE.donor_land(tuple(r["donor"]), size=size, game=GAME)
    for rot in (0, 90):
        cells = [(bx, by) for by in range(20) for bx in range(24)
                 if TE.preview((bx, by), land=land, occupied=occ, size=size, rot=rot, donor_tris=dl)["ok"]]
        for cell in rng.sample(cells, min(N, len(cells))):
            rep = OUT / "v.json"
            rc = cli.main(["--game", str(GAME)] + TE.command(d, cell, tuple(r["donor"]), rot=rot, size=size,
                                                            dry_run=True, report=rep))
            v = json.loads(rep.read_text())
            ref = v.get("refused") or {}
            bad = [g.get("gate") for g in v.get("gates") or [] if not g.get("ok")]
            res.append({"donor": r.get("name"), "rot": rot, "cell": cell, "ok": v.get("ok"), "gate": ref.get("gate"),
                        "bad": bad, "where": ref.get("where"), "message": (ref.get("message") or "")[:140]})
            print(r.get("name"), rot, cell, "ok" if v.get("ok") else f"REFUSED {ref.get('gate')} bad={bad} "
                  f"where={ref.get('where')} {(ref.get('message') or '')[:90]}", flush=True)
(OUT / "carries.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
c = collections.Counter((e["gate"], tuple(e["bad"])) for e in res if not e["ok"])
print(f"== {len(res)} checked, {sum(e['ok'] for e in res)} pass; refusals: {dict(c)}")
