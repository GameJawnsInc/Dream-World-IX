"""Replay the labelled sample's placements (from their handles) through the card's new preview: what it refuses, by
outcome, and how long a preview takes."""
import collections, json, os, sys, time
from pathlib import Path
WT = Path(r"C:\gd\Dream-World-IX\.claude\worktrees\terrain-shaping-continue-4647b2\ff9mapkit")
sys.path.insert(0, str(WT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])
from ff9mapkit.editor.theme import pick_palette
from ff9mapkit.workspace.worldmountain import MountainTool
from ff9mapkit.workspace.worldview3d import WorldView3DPanel
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
OUT = Path(sys.argv[1]); SAMPLE = json.load(open(sys.argv[2]))
pal = pick_palette("dark")
tool = MountainTool(pal, WorldView3DPanel(pal), game_fn=lambda: GAME, source_fn=lambda: GAME / "FF9CustomMap-world",
                    drafts_root=OUT / "d", runner=None, sync=True, ask=lambda t, x: True)
tool.open_tool()
out, times = collections.Counter(), []
for r in SAMPLE:
    h = r["handles"]
    arg = lambda f, d=None: h[h.index(f) + 1] if f in h else d
    tool.donor_box.setCurrentIndex(tool.donor_box.findData(arg("--donor")))
    tool.angle.setValue(int(round(float(arg("--rot", 0)))))
    tool.spread.setValue(float(arg("--spread", 1.0)))
    tool.rock_height.setValue(float(arg("--rock-height", 1.0)))
    x, z = r["at"]
    tool.place(x, z, 0.0)
    tool._timer.stop()
    assert tool.handles() is not None and list(tool.handles())[3:] == h, (h, list(tool.handles())[3:])
    t0 = time.perf_counter()
    tool._redraw()
    times.append(time.perf_counter() - t0)
    pv = tool._preview
    lab = "PASS" if r["ok"] else r["gate"]
    out[(lab, "refused " + str(pv.get("gate")) if not pv["ok"] else "offered")] += 1
for k in sorted(out):
    print(k, out[k])
times.sort()
print(f"redraw (ghost + preview) median {1000 * times[len(times) // 2]:.0f} ms, p90 {1000 * times[int(len(times) * 0.9)]:.0f} ms, max {1000 * times[-1]:.0f} ms")
