"""Why does the game render at ~31 fps some of the time and ~60 the rest? One launch, the CPU loaded and unloaded.

    PYTHONUNBUFFERED=1 py tools/play.py studies/test-harness/render_rate_probe.py --label render-rate-probe

THE OBSERVATION. Under the harness the game renders at ~31 or ~60 fps, and rung-3 session 4 (`story-rung3d`) flipped
59.0 -> 31.4 -> 59.7 -> 31.8 inside ONE launch; both ~31 stretches overlapped heavy test / workflow load on the machine.

THE HYPOTHESIS (H), written before this ran: with `[Graphics] VSync = 1` (the install's setting), a frame that misses
its 16.7 ms vblank waits for the next one, so a machine loaded enough that frames keep missing presents every other
vblank: the rate HALVES to ~30, not a smooth slide. So:
  - idle, the field renders ~60 (54-66);
  - with every logical CPU busy, it drops to ~30 (26-34), quantized, not an in-between rate;
  - unloaded again, it returns to ~60.
A half load (half the logical CPUs busy) is measured too, with no prediction: it says where the threshold lies.
H is REFUTED if full load leaves it at ~60, or drops it to an in-between rate (35-53: plain contention, not the vblank),
or if it does not come back when the load goes. If the launch starts at ~31 with no load, H cannot be tested this way
(the baseline is the claim's premise) and the run says so -- VOID, not a verdict.

THE INSTRUMENT. Not the driver's tick clock (it smooths over its own window): the agent's own frame counter against the
state file's write times, `(frame, mtime)` sampled every ~0.25 s, fps = frames / seconds over each 5 s window --
exactly what "render rate" means. The load is `py -c "while True: pass"` processes at normal priority, killed in
`finally`. The player stands still in Lindblum 552 at SC 3115 (where rungs 0-2 ran), no input.

RR-CAP     the instrument works: every window has >= 8 distinct samples and a positive rate
RR-BASE    idle baseline is ~60 (54-66) -- else H is untestable here (VOID)
RR-LOAD    under full load the median window is ~30 (26-34)
RR-QUANT   every full-load window is ~30 or ~60 (26-34 or 54-66), none in between
RR-BACK    after each load goes, the rate returns to ~60 (median of the recovery phase 54-66)
"""
from __future__ import annotations

import os
import statistics
import subprocess
import sys
import time

FIELD, FIELD_SC = 552, 3115     # Lindblum at the beat rungs 0-2 ran it: a real field that plays at that SC
PHASES = (("baseline", 0, 40.0), ("full load", os.cpu_count() or 8, 60.0), ("recovery", 0, 40.0),
          ("half load", max(1, (os.cpu_count() or 8) // 2), 60.0), ("recovery 2", 0, 40.0))
WINDOW = 5.0
SAMPLE = 0.25
SIXTY, THIRTY = (54.0, 66.0), (26.0, 34.0)


def _within(v, band) -> bool:
    return band[0] <= v <= band[1]


def _burners(n: int) -> list:
    return [subprocess.Popen([sys.executable, "-c", "while True: pass"], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL) for _ in range(n)]


def _measure(g, seconds: float) -> list:
    """``[(fps, samples)]`` per WINDOW over ``seconds``, from the agent's frame counter and the state file's mtime."""
    out, window, end = [], [], time.monotonic() + seconds
    w_end = time.monotonic() + WINDOW
    while time.monotonic() < end:
        st = g.state
        if st.mtime is not None and st.frame >= 0 and (not window or window[-1] != (st.frame, st.mtime)):
            window.append((st.frame, st.mtime))
        if time.monotonic() >= w_end:
            if len(window) >= 2 and window[-1][1] > window[0][1]:
                out.append(((window[-1][0] - window[0][0]) / (window[-1][1] - window[0][1]), len(window)))
            else:
                out.append((0.0, len(window)))
            window, w_end = [], time.monotonic() + WINDOW
        time.sleep(SAMPLE)
    return out


def run(g) -> None:
    g.newgame()
    g.wait_frames(30)
    g.warp(FIELD, scenario=FIELD_SC)
    g.wait_frames(120)
    results = {}
    procs: list = []
    try:
        for name, n, seconds in PHASES:
            procs = _burners(n)
            time.sleep(2.0 if n else 0.0)                   # let the load bite before the first window
            windows = _measure(g, seconds)
            for p in procs:
                p.kill()
            for p in procs:
                p.wait(timeout=10)
            procs = []
            results[name] = windows
            fps = [round(f, 1) for f, _n in windows]
            g.note(f"{name} ({n} burner(s) on {os.cpu_count()} logical CPUs): windows {fps}, "
                   f"median {statistics.median(fps) if fps else 'n/a'}")
            print(f"[rate-probe] {name}: {n} burner(s): {fps}", flush=True)
    finally:
        for p in procs:
            p.kill()

    med = {name: statistics.median([f for f, _n in w]) for name, w in results.items() if w}
    g.check(all(n >= 8 and f > 0 for w in results.values() for f, n in w),
            "RR-CAP: every window has >= 8 distinct samples and a positive rate",
            str({k: [(round(f, 1), n) for f, n in w] for k, w in results.items()}))
    base_ok = _within(med.get("baseline", 0), SIXTY)
    g.check(base_ok, "RR-BASE: idle baseline ~60 (54-66) -- else H is untestable here (VOID)",
            f"baseline median {med.get('baseline')}")
    if not base_ok:
        g.note("VOID: the launch did not render ~60 idle; H's premise does not hold here, so the load says nothing")
        return
    full = [f for f, _n in results["full load"]]
    g.check(_within(med["full load"], THIRTY), "RR-LOAD: under full load the median window is ~30 (26-34)",
            f"full-load median {med['full load']}, windows {[round(f, 1) for f in full]}")
    g.check(all(_within(f, THIRTY) or _within(f, SIXTY) for f in full),
            "RR-QUANT: every full-load window is ~30 or ~60, none in between",
            f"{[round(f, 1) for f in full]}")
    g.check(_within(med["recovery"], SIXTY) and _within(med["recovery 2"], SIXTY),
            "RR-BACK: the rate returns to ~60 after each load goes",
            f"recovery {med['recovery']}, recovery 2 {med['recovery 2']}, half load {med.get('half load')}")
