# PATH B — the COMPILED ROADMAP (offline study, ★ FALSIFIED 2026-07-24)

The scripts behind the PLAN.md rung "PATH B — THE COMPILED ROADMAP (★ FALSIFIED)".
All read-only + offline; nothing here deploys, and no playtest was spent.

| file | what it does |
|---|---|
| `extract_all_bgi.py` | pulls all 674 real fields' `.bgi` out of `p0data*.bin` into a scratch `bgi/` dir (~3s, read-only on the install) |
| `roadmap.py` | THE DECOMPOSITION — straight-walk-safe regions over the engine's own triangle-neighbour graph, portals, all-pairs next hop, the XZ floor-overlap test |
| `emit.py` | emits the lookup as REAL `.eb` bytes through the shipped emitters (`behavior._stmt`, `eb.labelasm.asm`) — every byte count in the rung is measured, not estimated |
| `census.py` | region-count + emitted-size census over a random sample of real fields → `census.json` |
| `worked_559.py` | the worked example (field 559, the benches' own donut arena): sizes, per-tick cost, and the quality comparison against the kit's A* |

Reproduce: run `extract_all_bgi.py` first (it writes `bgi/` and `559.bgi` next to these
scripts — or copy `C:/gd/_btroute_bench/walkmesh.bgi` as `559.bgi`), then `census.py 100`
and `worked_559.py`. The decomposition is cached to `559_decomp.pkl` (it takes ~30s).

The one-line result: the decomposition, the table compression and the routing QUALITY all
work; what has no sound implementation is the *entry point* — resolving a live (x,z) to a
region inside the 26-bit CalcStack. See PLAN.md for the numbers and the verdict.
