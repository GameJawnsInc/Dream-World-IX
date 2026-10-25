"""reads_gui_sync: the reads the cards make SYNCHRONOUSLY on the GUI thread (the window freezes for them): the coast
card's _edited (who holds the clicked block: the draft + every FolderNames folder, discs 1 and 4; run on every open
and every island_changed), the island card's _occupied (per footprint block, first ask), and draft() (draft.json
parsed: read_meta), against the real install READ ONLY and the lane's draft.

    py studies/overworld-editor/perf/reads_gui_sync.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reads_common import DRAFTS, GAME, SOURCE, dump, lane_draft, stat, timeit  # noqa: E402


class StubPanel:
    def set_overlays(self, o):
        pass

    def set_ghost(self, g):
        pass


def main():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from ff9mapkit import provision
    cfg = Path(tempfile.mkdtemp(prefix="reads_cfg_"))
    real = provision._user_dir
    provision._user_dir = lambda sub: cfg if sub == "config" else real(sub)
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])  # noqa: F841
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.worldcoast import CoastTool
    from ff9mapkit.workspace.worldisland import IslandTool
    from ff9mapkit.world import draft as D
    d = lane_draft()
    pal = pick_palette("dark")
    kw = dict(game_fn=lambda: GAME, source_fn=lambda: SOURCE, drafts_root=DRAFTS)
    coast = CoastTool(pal, StubPanel(), outline_fn=lambda c: [], **kw)
    island = IslandTool(pal, StubPanel(), outline_fn=lambda c: set(), **kw)
    res = {"cmd": "py studies/overworld-editor/perf/reads_gui_sync.py", "stack": [str(f) for f in coast._live_stack()]}
    ts, who = timeit(lambda: coast._edited((14, 1)), 7, 1)
    res["coast_edited_14_1"] = stat(ts)
    res["coast_edited_14_1_who"] = who
    ts, who = timeit(lambda: coast._edited((20, 11)), 7, 1)
    res["coast_edited_20_11"] = stat(ts)
    ts, _ = timeit(lambda: coast._live_stack(), 7, 1)
    res["live_stack_read"] = stat(ts)

    def occ():
        island.__dict__.pop("_occ", None)
        return island._occupied([(5, 10), (6, 10), (5, 11), (6, 11)])
    ts, _ = timeit(occ, 7, 1)
    res["island_occupied_4_blocks_uncached"] = stat(ts)
    ts, _ = timeit(lambda: island._occupied([(5, 10), (6, 10), (5, 11), (6, 11)]), 7, 1)
    res["island_occupied_4_blocks_cached"] = stat(ts)
    ts, _ = timeit(lambda: D.read_meta(d), 9, 1)
    res["read_meta_draft_json"] = stat(ts)
    res["draft_json_bytes"] = (d / D.DRAFT_FILE).stat().st_size
    ts, _ = timeit(lambda: (d / D.DRAFT_FILE).stat(), 9, 1)
    res["stat_draft_json"] = stat(ts)
    dump("reads_gui_sync.json", res)
    for k, v in res.items():
        print(k, v)


if __name__ == "__main__":
    main()
