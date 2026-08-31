"""Watch the exact moment walking out of 30820 stops the game.

`no state published` is the same symptom for three very different causes, and guessing between them
is how the last wrong diagnosis happened. This distinguishes them by reading the channel file
directly instead of through the driver's parser:

  * file MISSING            -> the agent never got to replace it
  * file STALE (frame flat) -> the Unity main thread is stuck; the agent is not being ticked
  * file UNPARSEABLE        -> a torn write
  * process gone            -> the game died outright

It walks north in small bursts, sampling raw file state every 100ms, and prints the last thing the
engine said about itself either side of the stop.

    py tools/play.py studies/test-harness/scenarios/gateway_forensics.py --field 30820
"""
import json
import time
from pathlib import Path

FIELD = 30820


def snap(path: Path) -> dict:
    """Raw channel read -- deliberately NOT Channel.state(), which hides which failure this is."""
    try:
        raw = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        return {"status": "MISSING"}
    except OSError as err:
        return {"status": f"IOERROR {err.__class__.__name__}"}
    try:
        doc = json.loads(raw)
    except ValueError:
        return {"status": "UNPARSEABLE", "bytes": len(raw)}
    return {"status": "ok", "frame": doc.get("frame"), "field": (doc.get("field") or {}).get("id"),
            "ui": doc.get("ui_state"), "fading": doc.get("fading"),
            "control": (doc.get("player") or {}).get("control"),
            "x": (doc.get("player") or {}).get("x"), "z": (doc.get("player") or {}).get("z")}


def run(g, field: int = FIELD):
    g.note("gateway_forensics")
    state_file = g.channel.dir / "state.json"

    g.newgame()
    g.warp(field)
    g.wait_frames(60)
    g.calibrate_axes()
    home = g.state
    print(f"[fx] home {home.pos} on {home.field_id}")

    # Drive north in short non-blocking bursts so the sampler keeps running THROUGH the transition,
    # rather than being blocked inside a walk verb when the interesting moment arrives.
    g.send("hold up 240", wait=False)

    last_ok = None
    stopped_at = None
    flat_for = 0
    deadline = time.time() + 25
    while time.time() < deadline:
        s = snap(state_file)
        if s["status"] != "ok":
            print(f"[fx] {s}")
            stopped_at = s
            break
        if last_ok and s["frame"] == last_ok["frame"]:
            flat_for += 1
            if flat_for == 12:            # ~1.2s with no new frame = the engine is not ticking
                print(f"[fx] FRAME STALLED at {s}")
                stopped_at = {"status": "STALE", **s}
                break
        else:
            flat_for = 0
            if last_ok is None or s["field"] != last_ok["field"] or s["ui"] != last_ok["ui"]:
                print(f"[fx] {s}")
            last_ok = s
        time.sleep(0.1)

    alive = g.proc is None or g.proc.poll() is None
    print(f"[fx] last good sample: {last_ok}")
    print(f"[fx] stop condition:   {stopped_at}")
    print(f"[fx] process alive:    {alive}")
    hint = g.diagnose()
    print(f"[fx] engine log says:  {hint}")
    print(f"[fx] engine log file:  {g.engine_log()}")

    g.check(stopped_at is None, "walking north out of the room did NOT stall the game",
            f"stopped with {stopped_at}; process alive={alive}")
