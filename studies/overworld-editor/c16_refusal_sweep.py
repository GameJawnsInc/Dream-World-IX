"""Which refusals do the relief cards meet, and do they say where? The real forest / mountain / hill cards, headless
and synchronous, an in-process runner (cli.main), random handles at random lawn spots of the live island, Check only
where the card's own cheap laws pass. Writes refusals.json."""
import json, os, random, sys, time, collections
from pathlib import Path
WT = Path(r"C:\gd\Dream-World-IX\.claude\worktrees\terrain-shaping-continue-4647b2\ff9mapkit")
sys.path.insert(0, str(WT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import ff9mapkit
assert ff9mapkit.__file__.startswith(str(WT))
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])
from ff9mapkit import cli
from ff9mapkit.editor.theme import pick_palette
from ff9mapkit.workspace.worldforest import ForestTool
from ff9mapkit.workspace.worldhill import HillTool
from ff9mapkit.workspace.worldmountain import MountainTool
from ff9mapkit.workspace.worldview3d import WorldView3DPanel
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
OUT = Path(sys.argv[1]); N = int(sys.argv[2]); only = sys.argv[3:] or ["hill", "forest", "mountain"]
rng = random.Random(1024)


class InProcess:
    def start(self, argv, cwd, done):
        done(cli.main([str(a) for a in argv[3:]]), "")

    def kill(self):
        pass

    def busy(self):
        return False


pal = pick_palette("dark")
res = {}
for name, cls in (("hill", HillTool), ("forest", ForestTool), ("mountain", MountainTool)):
    if name not in only:
        continue
    tool = cls(pal, WorldView3DPanel(pal), game_fn=lambda: GAME, source_fn=lambda: GAME / "FF9CustomMap-world",
               drafts_root=OUT / name, runner=InProcess(), sync=True, ask=lambda t, x: True)
    tool.open_tool()
    ix = tool._ix
    cents = ix.cent
    out, tried, t0 = [], 0, time.time()
    while len(out) < N and tried < 4000:
        tried += 1
        x, z = (float(v) for v in cents[rng.randrange(len(cents))])
        if name == "hill":
            tool.height_spin.setValue(rng.uniform(tool.height_spin.minimum(), tool.height_spin.maximum()))
            tool.radius_spin.setValue(rng.uniform(tool.radius_spin.minimum(), tool.radius_spin.maximum()))
        else:
            tool.donor_box.setCurrentIndex(rng.randrange(tool.donor_box.count()))
            tool.angle.setValue(rng.randrange(0, 360, 5))
            tool.spread.setValue(rng.uniform(tool.spread.minimum(), tool.spread.maximum()))
            if name == "mountain":
                tool.rock_height.setValue(rng.uniform(tool.rock_height.minimum(), tool.rock_height.maximum()))
        tool.place(x, z, 0.0)
        tool._timer.stop()
        if tool._preview is None or not tool._preview["ok"]:
            continue
        tool._check()
        v = tool._current_verdict()
        if v is None:
            continue
        ref = v.get("refused") or {}
        out.append({"at": [x, z], "handles": list(tool.handles() or ())[3:], "ok": v["ok"], "gate": ref.get("gate"),
                    "where": len(ref.get("where") or []), "message": (ref.get("message") or "")[:160]})
        print(name, len(out), "ok" if v["ok"] else f"REFUSED {ref.get('gate')} where={len(ref.get('where') or [])}: "
              f"{(ref.get('message') or '')[:100]}", flush=True)
    res[name] = {"tried": tried, "checked": out, "s": round(time.time() - t0, 1)}
    tool.close_tool()
    (OUT / "refusals.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
for name, r in res.items():
    c = collections.Counter((e["gate"], e["where"] > 0) for e in r["checked"] if not e["ok"])
    print(f"== {name}: {len(r['checked'])} checked of {r['tried']} tried, {sum(e['ok'] for e in r['checked'])} pass; "
          f"refusals by (gate, located): {dict(c)}")
