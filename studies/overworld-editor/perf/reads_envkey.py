"""reads_envkey: the per-call overhead every stock read pays before the env/decode memos answer: read_block ->
_worldmap_env -> _streaming_assets -> config.find_game_path (Path.resolve: two _getfinalpathname syscalls), and
discmirror._real_parts re-scanning the env's container with a regex on every call (147 calls in one sink scan).
    py studies/overworld-editor/perf/reads_envkey.py"""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from reads_common import GAME, dump, stat, timeit  # noqa: E402
from ff9mapkit import config  # noqa: E402
from ff9mapkit.world import discmirror as DM, extract as X  # noqa: E402
X._worldmap_env(1, GAME)
X.read_block(13, 15, disc=1, game=GAME)               # memo warm
res = {}
ts, _ = timeit(lambda: [config.find_game_path(GAME) for _ in range(1000)], 5, 1)
res["find_game_path_per_call_ms"] = round(min(ts), 4)   # 1000 calls -> ms each = s total
ts, _ = timeit(lambda: [X._worldmap_env(1, GAME) for _ in range(1000)], 5, 1)
res["worldmap_env_memo_hit_per_call_ms"] = round(min(ts), 4)
ts, _ = timeit(lambda: [X.read_block(13, 15, disc=1, game=GAME) for _ in range(100)], 5, 1)
res["read_block_memo_hit_per_call_ms"] = round(min(ts) * 10, 3)
ts, _ = timeit(lambda: DM._real_parts(1, "0_1", game=GAME), 7, 1)
res["real_parts_per_call"] = stat(ts)
print(res); dump("reads_envkey.json", res)
