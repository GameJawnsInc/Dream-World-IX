r"""RX gates -- calibrate the managed-renderer port (raster.py) against what the GAME did.

    py -I rx_gates.py              # RX0-RX3: the prim stream and the batching, vs archived s48 probe logs
    py -I rx_gates.py --battery    # + RX4: the owner-verdict battery, pixel level (slow, ~15 min)

Exit 0 = every gate passed, 1 = a gate FAILED, 2 = an input is missing (never a silent skip).

Ground truth, all archived in SCRATCH by earlier owner casts (nothing here is re-cast):
* the s48 probe logs -- in game, per frame, every primitive ``SFX_GetPrim`` returned (PRIM/STATE
  rows) and every mesh ``SFXRender`` built from them (MESH rows: command-buffer index, key, tris);
* the W6b/U1 verdict casts -- an edited container, deployed, cast, and judged on screen by the owner.

RX0  the staged plugin is the pinned build.
RX1  INPUT: where the game and the headless host fed the renderer the same prim sequence (index +
     code), the first vertices agree up to Memoria's widescreen ``drOffsetX`` (+35, 0) -- the probe
     logs ``v + drOffset``; the headless screen is the 320-wide native one.
RX2  BATCHING: on every input-matched frame the ported FrameBuilder reproduces the in-game command
     buffer exactly (index, mesh key, triangle count).
RX3  FALSIFIER: the same comparison with the WRONG render order (Bahamut with Add drawn before Opa)
     must fail -- RX2 can tell a wrong port from a right one. (A wrong SUB order is NOT a falsifier
     here: the input-matched Bahamut frames carry no subtract meshes, so it cannot fail -- the first
     draft of this gate used it and passed nothing.)
RX4  PIXELS (``--battery``): each owner verdict cast, re-rendered against its pre-state, must show
     what the owner saw: drawn casts change the screen, refused ones leave it byte-identical.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
import raster as R                  # noqa: E402
import sfx_host as H                # noqa: E402

LOGS = H.SCRATCH
W6B = H.SCRATCH / "repaint-w6b"
#: (effect, archived probe log) -- every in-game capture with MESH rows for an effect the corpus has.
CAPTURES = [
    (227, LOGS / "repaint-w6" / "capture-logs" / "sfxmeshprobe.w6a-cast.2026-07-27.log"),
    (227, W6B / "capture-logs" / "sfxmeshprobe.pre-odin-cast.2026-07-28.log"),
    (211, W6B / "capture-logs" / "sfxmeshprobe.pre-odin-cast.2026-07-28.log"),
    (38, W6B / "capture-logs" / "sfxmeshprobe.s76-control-cast.log"),
]
WIDESCREEN_DX = 35                  # (PsxScreenWidth 390 - 320) / 2 on the owner's 16:9 install
RX1_MIN_EXACT = 0.75                # share of first vertices at exactly (+35, 0)
RX1_MIN_NEAR = 0.95                 # share within 2 px (the plugin's rand() jitter)

#: RX4 -- (name, effect, pre-state, cast container, frames, the owner's verdict: DRAWN or NOT_DRAWN)
DOME = R.RASTER_DIR / "dome-build" / "mod" / "FF9_Data" / "SpecialEffects" / "ef211"
BATTERY = [
    ("ef211 W6b-2 dome bands", 211, "stock", DOME, "1-484:6,230-290", "DRAWN"),
    # the W6b ef211 ladder (W6b-SCENERY.md, "THE CAST RECORD"): 1a/1b put wheels into (704,256), which the
    # owner never saw ("bound, never drawn"); 1c-1f banded or eroded the surfaces they named
    ("ef211 1a ink wheel (704,256)", 211, "stock", W6B / "ef211" / "mod" / "FF9_Data" / "SpecialEffects" / "ef211",
     "1-484:4", "NOT_DRAWN"),
    ("ef211 1b punch wheel (704,256)", 211, "stock", W6B / "ef211-punch" / "mod" / "FF9_Data" / "SpecialEffects" / "ef211",
     "1-484:4", "NOT_DRAWN"),
    ("ef211 1c striped cell census", 211, "stock", W6B / "ef211-cellprobe" / "ef211.cellprobe", "1-484:4", "DRAWN"),
    ("ef211 1d only (576,384)", 211, "stock", W6B / "ef211-cellprobe6" / "ef211.cellprobe", "1-484:4", "DRAWN"),
    ("ef211 1e only (576,256)", 211, "stock", W6B / "ef211-cellprobe5" / "ef211.cellprobe", "1-484:4", "DRAWN"),
    ("ef211 2b bold wheel", 211, "stock", W6B / "ef211-cast2" / "mod" / "FF9_Data" / "SpecialEffects" / "ef211",
     "1-484:4", "DRAWN"),
    ("ef211 1f pool wheels", 211, "stock", W6B / "ef211-pool" / "mod" / "FF9_Data" / "SpecialEffects" / "ef211",
     "1-484:4", "DRAWN"),
    ("ef424 channel-A cast A", 424, "stock", W6B / "ef424-channel-a" / "stage" / "backups" / "ef424.pre-20260729-213439",
     "1-151:2", "DRAWN"),
    ("ef446 cast B 15bpp bands", 446, "stock", W6B / "ef446-15bpp" / "cast-b" / "mod" / "FF9_Data" / "SpecialEffects" / "ef446",
     "1-258:2", "DRAWN"),
    ("ef251 cast 15 x512 bands", 251, W6B / "ef251-15bpp" / "cast-15" / "pre.ef251",
     W6B / "ef251-15bpp" / "cast-15" / "ef251.cast15", "1-590:3", "DRAWN"),
    ("ef251 x512 census probe", 251, "stock", W6B / "ef251-15bpp" / "probe-x512" / "ef251.cellprobe", "1-590:3", "DRAWN"),
    ("ef429 census probe", 429, "stock", W6B / "ef429-15bpp" / "probe" / "ef429.cellprobe", "1-146:2", "DRAWN"),
    ("ef429 cell-1 cover", 429, "stock", W6B / "ef429-15bpp" / "probe-only1" / "ef429.cellprobe", "1-146:2", "NOT_DRAWN"),
    ("ef429 cell-2 stripes", 429, "stock", W6B / "ef429-15bpp" / "probe-only2" / "ef429.cellprobe", "1-146:2", "NOT_DRAWN"),
    ("ef429 closing (448,384) cover", 429, W6B / "ef429-15bpp" / "probe-fullcover2" / "pre.ef429",
     W6B / "ef429-15bpp" / "probe-fullcover2" / "ef429.fullcover", "1-146:2", "NOT_DRAWN"),
]


class Missing(Exception):
    pass


def _need(path: Path) -> Path:
    if not Path(path).exists():
        raise Missing(str(path))
    return Path(path)


def _bin():
    bins = H.staged_bins()
    if not bins:
        raise Missing("a staged plugin (py -I sfx_host.py stage)")
    return bins[0]


def rx0() -> tuple:
    d, sha = _bin()
    ok = sha in H.PINNED_BUILDS
    return ok, "staged plugin %s… %s" % (sha[:12], "pinned" if ok else "NOT PINNED")


def _calibrate(effect: int, log: Path, settings_override=None) -> dict:
    """``raster.calibrate`` in a child process (the plugin is process-global state)."""
    code = ("import sys, json; sys.path.insert(0, %r); import raster as R, sfx_host as H; from pathlib import Path\n"
            "ov = json.loads(%r)\n"
            "if ov:\n"
            "    base = R.play_settings\n"
            "    R.play_settings = lambda e: dict(base(e), **ov)\n"
            "d, sha = H.staged_bins()[0]\n"
            "rep = R.calibrate(d, (H.CORPUS / ('ef%%03d.bytes' %% %d)).read_bytes(), %d, Path(%r), xy_detail=True)\n"
            "print('RXJSON ' + json.dumps(rep, default=str))"
            % (str(_HERE), json.dumps(settings_override or {}), effect, effect, str(log)))
    cp = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, timeout=1800)
    for line in cp.stdout.splitlines():
        if line.startswith("RXJSON "):
            return json.loads(line[7:])
    raise RuntimeError("calibrate child failed: " + cp.stderr[-800:])


def rx1_rx2(reports) -> tuple:
    exact = near = total = 0
    matched = agree = 0
    lines = []
    for (effect, log), rep in reports:
        for c in rep["casts"]:
            dx = Counter({tuple(json.loads(k)): v for k, v in c.get("xy_delta", {}).items()})
            exact += dx.get((WIDESCREEN_DX, 0), 0)
            near += sum(v for (x, y), v in dx.items() if abs(x - WIDESCREEN_DX) <= 2 and abs(y) <= 2)
            total += sum(dx.values())
            m = c["rx2"].get("match", 0)
            d = c["rx2"].get("differ", 0)
            matched += m + d
            agree += m
            lines.append("ef%03d %-44s cast %d: %3d/%3d input-matched frames, command buffer %d/%d"
                         % (effect, Path(log).name[:44], c["cast"], c["rx1"].get("match", 0), c["frames"], m, m + d))
    rx1 = total > 0 and exact / total >= RX1_MIN_EXACT and near / total >= RX1_MIN_NEAR
    rx1_msg = "%d first vertices on input-matched frames: %.1f%% at exactly (+%d,0), %.1f%% within 2 px" % (
        total, 100.0 * exact / max(1, total), WIDESCREEN_DX, 100.0 * near / max(1, total))
    rx2 = matched > 0 and agree == matched
    rx2_msg = "%d/%d input-matched frames reproduce the in-game command buffer exactly" % (agree, matched)
    return (rx1, rx1_msg), (rx2, rx2_msg), lines


def rx3() -> tuple:
    """RX2 fails on ONE wrong command buffer, so the falsifier passes when the wrong order makes any
    input-matched frame differ -- on both the Bahamut and the Phoenix capture."""
    parts, ok = [], True
    for effect, log in (CAPTURES[0], CAPTURES[2]):
        rep = _calibrate(effect, _need(log), {"add_order": 1})
        differ = sum(c["rx2"].get("differ", 0) for c in rep["casts"])
        total = differ + sum(c["rx2"].get("match", 0) for c in rep["casts"])
        ok = ok and differ > 0
        parts.append("ef%03d %d/%d" % (effect, differ, total))
    return ok, "Add drawn before Opa: input-matched frames that now differ -- " + ", ".join(parts)


def rx4() -> list:
    out = []
    for name, effect, pre, cast, frames, verdict in BATTERY:
        _need(cast)
        if pre != "stock":
            _need(pre)
        dest = R.RASTER_DIR / "rx4" / name.replace(" ", "_").replace("(", "").replace(")", "").replace(",", "")
        cmd = [sys.executable, "-I", str(_HERE / "raster.py"), "diff", "--ef", str(effect), "--a", str(pre),
               "--b", str(cast), "--frames", frames, "--out", str(dest)]
        cp = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        if cp.returncode != 0:
            out.append((False, "%s: render failed %s" % (name, cp.stderr[-300:])))
            continue
        doc = json.loads((dest / "diff.json").read_text(encoding="utf-8"))
        px = sum(r["changed_px"] for r in doc["frames"].values())
        drawn = px > 0
        ok = drawn == (verdict == "DRAWN")
        out.append((ok, "%-30s owner %-9s  port: %4d/%d frames changed, %8d px" % (
            name, verdict, doc["frames_changed"], len(doc["frames"]), px)))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--battery", action="store_true", help="also run RX4, the pixel-level verdict battery")
    a = ap.parse_args(argv)
    results = []
    try:
        results.append(("RX0",) + rx0())
        reports = [((e, l), _calibrate(e, _need(l))) for e, l in CAPTURES]
        (r1, m1), (r2, m2), lines = rx1_rx2(reports)
        results.append(("RX1", r1, m1))
        results.append(("RX2", r2, m2))
        results.append(("RX3",) + rx3())
        if a.battery:
            for i, (ok, msg) in enumerate(rx4(), 1):
                results.append(("RX4.%d" % i, ok, msg))
    except Missing as e:
        print("MISSING INPUT: %s" % e)
        return 2
    for line in lines:
        print("   " + line)
    for name, ok, msg in results:
        print("%-6s %s  %s" % (name, "PASS" if ok else "FAIL", msg))
    bad = [n for n, ok, _ in results if not ok]
    print("%d/%d gates pass" % (len(results) - len(bad), len(results)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
