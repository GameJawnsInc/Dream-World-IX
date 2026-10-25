"""Lane chain: recipe.row_for builds the WHOLE CLI parser (cli.build_parser: every subcommand) for each row it reads,
on the GUI thread (a card's Accept done, edit_row's said-back check). Its cost warm, and a prototype that builds the
parser once and reuses it, compared on every row of the gold recipe.

    py studies/overworld-editor/perf/chain_parser.py [runs]
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chain_common as CC                                             # noqa: E402

from ff9mapkit import cli                                             # noqa: E402
from ff9mapkit.world import draft as D                                # noqa: E402
from ff9mapkit.world import recipe as RC                              # noqa: E402

ARGV = {"hill": ["world-hill", "--mod-folder", "X", "--center", "64,-512"],
        "island": ["world-island", "--mod-folder", "X", "--center", "224,-160", "--seed", "5"],
        "transplant": ["world-transplant", "--mod-folder", "X", "--cell", "4,2", "--donor", "7,17"],
        "sink": ["world-sink", "--mod-folder", "X", "--at", "679.033", "-386.717"],
        "forest": ["world-forest", "--mod-folder", "X", "--center", "1400,-460", "--donor", "13,15"]}


def main(runs=5):
    out = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "runs": runs}
    out["build_parser"], _ = CC.timeit(cli.build_parser, n=runs)
    out["row_for(hill)"], _ = CC.timeit(lambda: RC.row_for(ARGV["hill"]), n=runs)
    real = cli.build_parser
    once = real()

    def cached():
        return once
    base = {k: RC.row_for(a) for k, a in ARGV.items()}
    cli.build_parser = cached
    try:
        out["row_for(hill) with one parser"], _ = CC.timeit(lambda: RC.row_for(ARGV["hill"]), n=runs)
        fast = {k: RC.row_for(a) for k, a in ARGV.items()}
    finally:
        cli.build_parser = real
    out["identical rows"] = base == fast
    out["rows"] = base
    gold = D.history(D.draft_path(CC.SOURCE, root=CC.GOLD))["steps"]
    out["gold labels"] = [s["label"] for s in gold]
    print({k: (v["min"], v["median"]) if isinstance(v, dict) and "min" in v else v for k, v in out.items()
           if k != "rows"})
    CC.save("parser.json", out)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 5)
