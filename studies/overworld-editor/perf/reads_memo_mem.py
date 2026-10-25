"""reads_memo_mem: the memory a process-wide soup memo (reads_soup.SoupMemo: per-file parse + per-block fragment, both
frames) would hold, by tracemalloc, against one plain SoupIndex (what a card holds today per frame).
    py studies/overworld-editor/perf/reads_memo_mem.py"""
import gc, sys, tracemalloc
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from reads_common import dump, lane_draft  # noqa: E402
import reads_soup as RS  # noqa: E402
d = lane_draft()
RS.card_read(d, False)          # imports warm
gc.collect(); tracemalloc.start()
ix = RS.card_read(d, False)
one_ix = tracemalloc.get_traced_memory()[0]
del ix; gc.collect(); tracemalloc.stop(); tracemalloc.start()
m = RS.SoupMemo()
ixe, se = m.soup(d, False); ixs, ss = m.soup(d, True)
del se, ss; gc.collect()
memo_plus_two_ix = tracemalloc.get_traced_memory()[0]
del ixe, ixs; gc.collect()
memo_only = tracemalloc.get_traced_memory()[0]
res = {"one_SoupIndex_MB": round(one_ix / 1e6, 1), "memo_both_frames_plus_two_ix_MB": round(memo_plus_two_ix / 1e6, 1),
       "memo_alone_MB": round(memo_only / 1e6, 1), "parse_entries": len(m.parse), "fragment_entries": len(m.frag)}
print(res); dump("reads_memo_mem.json", res)
