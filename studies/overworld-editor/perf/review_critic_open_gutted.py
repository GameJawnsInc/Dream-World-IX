"""Completeness critic probe (c658f78f), end to end through the real RecipeBar: Open... with the bar's StepWorker
asynchronous (the production lane) while one 3D-load-like pass reads the drawn draft (a draw-box switch: the box is
not locked while the bar holds). When the discard stops half way, what does the bar leave the tab with?
Hermetic (offscreen Qt, fake game root and drafts root under out/perf/review/critic/discard_race/)."""
from __future__ import annotations

import os
import random
import sys
import threading
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parent))
import review_critic_discard_race as R  # noqa: E402

from PySide6.QtWidgets import QApplication  # noqa: E402

from ff9mapkit.editor.theme import pick_palette  # noqa: E402
from ff9mapkit.workspace.worldrecipe import RecipeBar  # noqa: E402

D = R.D
app = QApplication.instance() or QApplication([])


class NeverRun:
    def start(self, argv, cwd, done):
        raise AssertionError("no row should run")

    def kill(self):
        pass

    def busy(self):
        return False


def trial(rng):
    game, src, d = R.setup()
    recipe = R.OUT / "one.toml"
    recipe.write_text('[[forest]]\nstep = 1\ncenter = [100.0, -100.0]\ndonor = "15,15"\n', encoding="utf-8")
    changed = []
    bar = RecipeBar(pick_palette("dark"), game_fn=lambda: game, source_fn=lambda: src, runner=NeverRun(),
                    drafts_root=R.OUT / "drafts", open_path_fn=lambda: str(recipe), ask=lambda *a: True,
                    on_changed=changed.append, sync=False)
    tree = d / "FF9_Data" / "WorldMap" / "Disc1" / "0_1"

    def load_pass():                                  # the 3D view's worker after a draw-box switch
        for by in range(20):
            for bx in range(24):
                for part in ("Terrain", "Object"):
                    try:
                        (tree / f"r{by}" / f"Block[{bx}][{by}] {part}.ff9mesh").read_bytes()
                    except OSError:
                        pass
    bar.open_btn.click()
    time.sleep(rng.uniform(0.0, 0.3))
    t = threading.Thread(target=load_pass, daemon=True)
    t.start()
    t0 = time.time()
    while bar._steps.busy() or bar.holding():
        if time.time() - t0 > 120:
            break
        app.processEvents()
        time.sleep(0.01)
    t.join()
    return bar, changed, d


if __name__ == "__main__":
    rng = random.Random(3)
    for i in range(12):
        bar, changed, d = trial(rng)
        text = bar.status_lbl.text()
        if text.startswith("Not opened"):
            print(f"trial {i}: BAR SAYS {text[:110]}...")
            print(f"  bar.draft(): {bar.draft()} | on_changed got: {changed[-1] if changed else None}")
            print(f"  D.edited_blocks (the card's draft line): {len(D.edited_blocks(d))} block(s); "
                  f"D.removals: {len(D.removals(d))} file(s)")
            break
        print(f"trial {i}: {text[:80]}")
