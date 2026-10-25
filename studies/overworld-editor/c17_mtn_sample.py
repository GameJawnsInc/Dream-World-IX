"""A labelled sample of mountain checks: the real card, headless, in-process, a fresh draft of the live island; at
each check, the cheap features the card holds (the ghost's rim against the ground, the rim's distance to unloaded
borders, to non-plain ground, to soup weld splits) beside the gate's verdict. Writes sample.json."""
import json, math, os, random, sys, time
from pathlib import Path
import numpy as np
WT = Path(r"C:\gd\Dream-World-IX\.claude\worktrees\terrain-shaping-continue-4647b2\ff9mapkit")
sys.path.insert(0, str(WT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import ff9mapkit
assert ff9mapkit.__file__.startswith(str(WT))
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])
from ff9mapkit import cli
from ff9mapkit.editor.theme import pick_palette
from ff9mapkit.world import interior as IN
from ff9mapkit.workspace.worldmountain import MountainTool
from ff9mapkit.workspace.worldview3d import WorldView3DPanel
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
OUT = Path(sys.argv[1]); N = int(sys.argv[2]); SEED = int(sys.argv[3]) if len(sys.argv) > 3 else 1


class InProcess:
    def start(self, argv, cwd, done):
        done(cli.main([str(a) for a in argv[3:]]), "")

    def kill(self):
        pass

    def busy(self):
        return False


pal = pick_palette("dark")
tool = MountainTool(pal, WorldView3DPanel(pal), game_fn=lambda: GAME, source_fn=lambda: GAME / "FF9CustomMap-world",
                    drafts_root=OUT / "d", runner=InProcess(), sync=True, ask=lambda t, x: True)
tool.open_tool()
rng = random.Random(SEED)


def features(tool):
    ix = tool._ix
    tris, rim = tool._ghost
    rim = np.asarray(rim)
    gy = [ix.ground_y(float(x), float(z)) for x, _y, z in rim]
    dh = np.array([abs(r[1] - g) if g is not None else np.nan for r, g in zip(rim, gy)])
    pv = tool._preview or {}
    span = set(map(tuple, pv.get("span") or []))
    # distance from each rim point to the nearest border facing a NON-span block (the apron's taper)
    def border_d(x, z):
        bx, by = math.floor(x / 64.0), math.floor(-z / 64.0)
        d = 99.0
        if (bx - 1, by) not in span: d = min(d, x - 64.0 * bx)
        if (bx + 1, by) not in span: d = min(d, 64.0 * (bx + 1) - x)
        if (bx, by + 1) not in span: d = min(d, z + 64.0 * (by + 1))
        if (bx, by - 1) not in span: d = min(d, -64.0 * by - z)
        return d
    bd = np.array([border_d(float(x), float(z)) for x, _y, z in rim])
    return {"dh_max": float(np.nanmax(dh)), "dh_p90": float(np.nanpercentile(dh, 90)), "dh_nan": int(np.isnan(dh).sum()),
            "border_min": float(bd.min()), "dh_at_border": float(np.nanmax(np.where(bd < 6.0, dh, 0.0))),
            "rim_n": len(rim), "seat_y": float(np.nanmedian([g for g in gy if g is not None] or [np.nan]))}


out, tried, t0 = [], 0, time.time()
cents = tool._ix.cent
while len(out) < N and tried < 20000:
    tried += 1
    x, z = (float(v) for v in cents[rng.randrange(len(cents))])
    tool.donor_box.setCurrentIndex(rng.randrange(tool.donor_box.count()))
    tool.angle.setValue(rng.randrange(0, 360, 5))
    tool.spread.setValue(rng.uniform(tool.spread.minimum(), tool.spread.maximum()))
    tool.rock_height.setValue(rng.uniform(tool.rock_height.minimum(), tool.rock_height.maximum()))
    tool.place(x, z, 0.0)
    tool._timer.stop()
    if tool._preview is None or not tool._preview["ok"]:
        continue
    f = features(tool)
    tool._check()
    v = tool._current_verdict()
    if v is None:
        continue
    ref = v.get("refused") or {}
    rec = {"at": [x, z], "handles": list(tool.handles() or ())[3:], "ok": v["ok"], "gate": ref.get("gate"),
           "detail": ref.get("detail"), "where": ref.get("where"), "message": (ref.get("message") or "")[:200],
           "report": {k: (v.get("report") or {}).get(k) for k in ("apron_slope", "zip_rise", "zip_ny_min")},
           **f}
    out.append(rec)
    print(len(out), "ok" if v["ok"] else f"REFUSED {ref.get('gate')} {ref.get('detail') or ''}", json.dumps(f), flush=True)
    if len(out) % 10 == 0:
        (OUT / "sample.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
(OUT / "sample.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
print(f"== {len(out)} checked of {tried} tried in {time.time() - t0:.0f} s; {sum(r['ok'] for r in out)} pass")
