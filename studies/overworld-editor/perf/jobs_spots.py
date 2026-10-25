"""Lane jobs, step 0: find ONE lawful spot per card verb on the CURRENT live folder (the lab spots of July-October
are partly built over by the labs' own promotes). Drives the REAL cards headless (offscreen: the cards need no GL),
sync, with an in-process runner (cli.main) -- the card's cheap laws pick the candidates, its own Check decides, and
the argv its runner receives is recorded with its Accept calls (_accept_calls). Everything targets the lane's draft
under out/perf/jobs/drafts (dry runs only here). Writes out/perf/jobs/spots.json.

    py studies/overworld-editor/perf/jobs_spots.py [verb ...]
"""
import json
import math
import os
import random
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jobs_common as J  # noqa: E402

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from ff9mapkit import provision  # noqa: E402

_CFG = Path(tempfile.mkdtemp(prefix="jobs_cfg_"))
_real_user_dir = provision._user_dir
provision._user_dir = lambda sub: _CFG if sub == "config" else _real_user_dir(sub)   # prefs pinned to a temp dir

from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication.instance() or QApplication([])
from ff9mapkit import cli  # noqa: E402
from ff9mapkit.editor.theme import pick_palette  # noqa: E402
from ff9mapkit.workspace.worldview3d import WorldView3DPanel  # noqa: E402

PAL = pick_palette("dark")
LANDING = (326.16, -569.09)


class InProcess:
    def __init__(self):
        self.argvs = []

    def start(self, argv, cwd, done):
        self.argvs.append([str(a) for a in argv])
        done(cli.main([str(a) for a in argv[3:]]), "")

    def kill(self):
        pass

    def busy(self):
        return False


def make(cls):
    r = InProcess()
    tool = cls(PAL, WorldView3DPanel(PAL), game_fn=lambda: J.GAME, source_fn=lambda: J.SOURCE, runner=r,
               drafts_root=J.DRAFTS, sync=True, ask=lambda t, x: True)
    tool.open_tool()
    return tool, r


def judge(tool, r, tries, budget_s=900):
    """Run the card's Check at each candidate setup until one passes; return the record."""
    t0 = time.time()
    n = 0
    for setup in tries:
        if time.time() - t0 > budget_s:
            break
        tool._verdict = None
        if setup() is False:
            continue
        tool._timer.stop()
        if tool._preview is None or not tool._preview.get("ok"):
            continue
        n += 1
        before = len(r.argvs)
        tool._check()
        v = tool._current_verdict()
        if v is None or len(r.argvs) == before:
            continue
        g = (v.get("refused") or {}).get("gate")
        print(f"   check {n}: ok={v.get('ok')} gate={g} {(v.get('refused') or {}).get('message', '')[:110]}",
              flush=True)
        if v.get("ok"):
            tmp = Path(tempfile.mkdtemp(prefix="jobs_acc_"))
            acc = tool._accept_calls(tool.draft(), tmp / "verdict.json", tmp / "verdict4.json")
            return {"check_argv": r.argvs[-1], "accept_calls": [[str(a) for a in c] for c in acc],
                    "row": tool.row() if hasattr(tool, "row") else None, "checks_tried": n,
                    "verdict_report": v.get("report"), "blocks": v.get("blocks")}
    return None


def hill():
    from ff9mapkit.workspace.worldhill import HillTool
    from ff9mapkit.world import hilledit as HE
    tool, r = make(HillTool)
    ix = tool._ix
    mains = ix.cent[HE._fam(ix) == "main"]
    cands = sorted({(round(x / 8) * 8.0, round(z / 8) * 8.0) for x, z in mains[::7]},
                   key=lambda c: (c[0] - LANDING[0]) ** 2 + (c[1] - LANDING[1]) ** 2)
    return judge(tool, r, (lambda c=c: tool.place(*c, 0.0) for c in cands))


def mountain():
    from ff9mapkit.workspace.worldmountain import MountainTool
    tool, r = make(MountainTool)
    rng = random.Random(3)
    cents = tool._ix.cent

    def tries():
        for _ in range(4000):
            x, z = (float(v) for v in cents[rng.randrange(len(cents))])

            def setup(x=x, z=z):
                tool.donor_box.setCurrentIndex(rng.randrange(tool.donor_box.count()))
                tool.angle.setValue(rng.randrange(0, 360, 5))
                tool.place(x, z, 0.0)
            yield setup
    return judge(tool, r, tries())


def island():
    from ff9mapkit.workspace.worldisland import IslandTool
    tool, r = make(IslandTool)
    cands = [(64.0 * bx + 32.0, -(64.0 * by + 32.0)) for by in range(20) for bx in range(24)]
    cands.sort(key=lambda c: (c[0] - LANDING[0]) ** 2 + (c[1] - LANDING[1]) ** 2)
    return judge(tool, r, (lambda c=c: tool.place(*c, 0.0) for c in cands))


def sink():
    from ff9mapkit.workspace.worldsink import ISLANDS, SinkTool
    tool, r = make(SinkTool)
    rows = tool._outlines.get(ISLANDS) or []
    rows = sorted(rows, key=lambda w: w.get("land_u2", 0))         # small islands first (cheap, and fewer neighbours)
    print(f"   {len(rows)} islands in the list")
    return judge(tool, r, (lambda w=w: tool.place(w["at"][0] + 1.0, w["at"][1] + 1.0, 3.0) for w in rows))


def coast():
    from ff9mapkit.workspace.worldcoast import CoastTool
    from ff9mapkit.world import coastedit as CE
    tool, r = make(CoastTool)
    cache = J.KIT / ".ff9mapkit-cache" / "world-coast"
    cells = [tuple(int(v) for v in p.stem.split("-")[-1].split("_")) for p in cache.glob("windows-disc1-*.json")]
    print(f"   cached coast-window blocks: {cells}")

    def tries():
        for cell in cells:
            for w in CE.windows(J.GAME, cell):
                for verb in CE.lawful(w):
                    def setup(w=w, verb=verb):
                        tool.place(*CE.anchor(w, verb), 3.0)
                        if tool._window is None:
                            return False
                        ix = tool.verb_box.findData(verb)
                        if ix < 0:
                            return False
                        tool.verb_box.setCurrentIndex(ix)
                        tool._handles_changed(at_once=True)
                    yield setup
    return judge(tool, r, tries())


def river():
    from ff9mapkit.workspace.worldriver import RiverTool
    tool, r = make(RiverTool)
    rs = tool._rs()
    held = tool._river[2]
    free = tool.FE.free_shifts(rs, river_at=tool.river_at(),
                               occupied=lambda cells: {c: sorted(held[c]) for c in cells if c in held})
    print(f"   river now at {tool.river_at()}, {len(free)} free placements: {free[:6]}")
    return judge(tool, r, (lambda s=s: tool.place(*tool.FE.centre(rs, s), 0.0) for s in free))


def forest():
    from ff9mapkit.workspace.worldforest import ForestTool
    tool, r = make(ForestTool)
    s = J.SPOTS["forest"]

    def setup():
        tool.donor_box.setCurrentIndex(tool.donor_box.findData("{},{}".format(*s["donor"])))
        tool.place(*s["center"], 3.2)
    return judge(tool, r, [setup])


def carry():
    from ff9mapkit.workspace.worldtransplant import TransplantTool
    tool, r = make(TransplantTool)
    s = J.SPOTS["carry"]
    ix = next(i for i in range(tool.donor_box.count()) if "7,17" in str(tool.donor_box.itemData(i)))

    def setup():
        tool.donor_box.setCurrentIndex(ix)
        tool.rot_box.setCurrentIndex(tool.rot_box.findData(90)) if hasattr(tool, "rot_box") else None
        tool.place(64.0 * s["cell"][0] + 10.0, -(64.0 * s["cell"][1] + 10.0), 0.0)
    return judge(tool, r, [setup])


def main():
    want = sys.argv[1:] or ["hill", "mountain", "island", "sink", "coast", "river"]
    path = J.OUT / "spots.json"
    res = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    J.draft()
    for verb in want:
        t = time.time()
        print(f"== {verb}", flush=True)
        try:
            rec = globals()[verb]()
        except Exception as e:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            rec = {"error": repr(e)}
        print(f"   -> {'FOUND' if rec and 'check_argv' in rec else 'none'} in {time.time() - t:.0f}s: "
              f"{(rec or {}).get('check_argv', '')}", flush=True)
        res[verb] = rec
        path.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
