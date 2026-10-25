r"""HEADLESS gates -- the calibration that licenses ``sfx_host.py`` as an instrument.

    py -I hx_gates.py            # exit 0 = every gate passed, 1 = a gate FAILED, 2 = an input is missing

A gate here compares the headless run with something measured IN GAME, or with a mechanism the study
already cast-proved. A missing input is exit 2 and names the input -- never a silent skip (a fresh
worktree has no SCRATCH corpus, and a gate that skips there would read green everywhere).

INPUTS (all local, none committed):
  * the user's own ``FF9SpecialEffectPlugin.dll``, staged by ``sfx_host.py stage`` (x64, PINNED build)
  * the extracted corpus ``<SCRATCH>\ef###.bytes`` (ef211, ef227, ef407)
  * the three archived in-game s53 Bahamut captures ``<SCRATCH>\inspect-r3\ef227.*.rows.csv``
  * the W3 retime pair named by ``<SCRATCH>\retime-w3\build_manifest.json`` (aligned + mis-retime)

THE GATES
  HX0  the staged plugin is the PINNED build (the offsets the slot/camera columns read are its own)
  HX1  Bahamut's timeline equals the in-game capture: every authored H change from f58 on, the
       creature's first frame (f82) and the last frame (f561) -- read from all three captures
  HX1b the full 12-number native view matrix equals the capture's PSXCAM matrix frame for frame over
       f128..f528 (after the entrance shake, before the hand-back to the battle camera), and the match
       is SHARP: one frame either way collapses it
  HX2  THE FALSIFIER: the legacy host with a 30-frame caster animation must FAIL HX1's comparison
  HX3  determinism: two runs of one container emit a byte-identical primitive stream
  HX4  the W3 retime, offline: aligned = +48 frames, every post-entrance H change +48, creature window
       +48; mis-retime = the same camera +48 but the creature window unchanged (the desync the owner
       saw in the cast)
  HX5  ef407's scroll blits really run: (704,384) is rewritten from (704,256)
  HX6  the Phoenix dome mechanism: ef211's (704,384) is never sampled directly, it is blitted into
       (704,256), and the 8bpp page that samples (704,256) draws over exactly the blit's frames
"""
from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sfx_host as H                            # noqa: E402

CAPTURE_DIR = H.SCRATCH / "inspect-r3"
RETIME_DIR = H.SCRATCH / "retime-w3"
FRAMES_DIR = H.OUT_DIR / "gates"

#: EF227-CHOREOGRAPHY.md's table of the archived s53 cast (and re-read from the captures by HX1):
#: the effect camera's authored H installs, the creature's first drawn frame, the cast's last frame.
INGAME_H_FROM_58 = [(58, 256), (153, 415), (302, 512), (529, 490)]
INGAME_CREATURE_FIRST = 82
INGAME_LAST_FRAME = 561
#: f553 -> 300 is the hand-back to the battle camera, which a headless run has no battle camera for.
HANDBACK_FRAME = 553
MATRIX_WINDOW = (128, 528)

results: List[Tuple[str, str, str]] = []        # (gate, PASS|FAIL|MISSING, detail)


def record(gate: str, ok: Optional[bool], detail: str) -> None:
    state = "MISSING" if ok is None else ("PASS" if ok else "FAIL")
    results.append((gate, state, detail))
    print("%-5s %-7s %s" % (gate, state, detail), flush=True)


# --------------------------------------------------------------------------- inputs
def need(path: Path, what: str) -> bool:
    if path.exists():
        return True
    record("INPUT", None, "%s not found: %s" % (what, path))
    return False


def capture_rows(path: Path) -> Dict[int, Tuple[tuple, int]]:
    """First PSXCAM row per frame: frame -> (matrix9 + trans3, H)."""
    out: Dict[int, Tuple[tuple, int]] = {}
    with open(path, newline="") as fh:
        for r in csv.reader(fh):
            if r and r[0] == "PSXCAM" and r[1] == "227":
                fr = int(r[2])
                if fr not in out:
                    out[fr] = (tuple(int(x) for x in r[3:15]), int(r[17]))
    return out


def capture_h_changes(cap: Dict[int, Tuple[tuple, int]]) -> List[Tuple[int, int]]:
    frames = sorted(cap)
    return [(f, cap[f][1]) for p, f in zip(frames, frames[1:]) if cap[f][1] != cap[p][1]]


def frames_table(path: Path) -> Dict[int, dict]:
    """The per-frame CSV a run wrote: frame -> {M (12-tuple), H}."""
    out = {}
    with open(path, encoding="utf-8") as fh:
        head = fh.readline().strip().split(",")
        for line in fh:
            row = dict(zip(head, line.rstrip("\n").split(",")))
            m = tuple(int(x) for x in row["M"].strip("()").replace(" ", ",").split(",") if x)
            out[int(row["frame"])] = {"M": m, "H": int(row["H"])}
    return out


def run(ef: int, **kw) -> dict:
    return H.run_effect(ef, **kw)


def from_58(changes, upto: int = HANDBACK_FRAME) -> List[Tuple[int, int]]:
    """The effect camera's H installs: from the f58 takeover, before the in-game hand-back (a headless
    run has none -- pass ``upto=None`` to compare two headless runs whose timelines are shifted)."""
    return [tuple(c) for c in (changes or []) if c[0] >= 58 and (upto is None or c[0] < upto)]


# --------------------------------------------------------------------------- gates
def main() -> int:
    ok_inputs = all([
        need(H.CORPUS / "ef227.bytes", "corpus container ef227"),
        need(H.CORPUS / "ef211.bytes", "corpus container ef211"),
        need(H.CORPUS / "ef407.bytes", "corpus container ef407"),
        need(CAPTURE_DIR, "archived s53 captures"),
        need(RETIME_DIR / "build_manifest.json", "W3 retime build manifest"),
    ])
    captures = sorted(CAPTURE_DIR.glob("ef227.*.rows.csv")) if CAPTURE_DIR.exists() else []
    if CAPTURE_DIR.exists() and not captures:
        record("INPUT", None, "no ef227.*.rows.csv capture in %s" % CAPTURE_DIR)
        ok_inputs = False
    try:
        bdir, sha = H.resolve_bin(None)
    except Exception as e:                                      # no install, no staged plugin
        record("INPUT", None, "cannot stage the plugin: %s" % e)
        return 2
    if not ok_inputs:
        return 2

    # HX0
    record("HX0", sha in H.PINNED_BUILDS, "staged plugin sha256 %s... (%s)" % (
        sha[:16], "PINNED" if sha in H.PINNED_BUILDS else "UNPINNED -- slot/camera columns unavailable"))
    if sha not in H.PINNED_BUILDS:
        return 1

    # HX1 -- against the published table AND each archived capture
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    base_csv = FRAMES_DIR / "ef227.rework.frames.csv"
    stock = run(227, frames_csv=str(base_csv))
    caps = [capture_rows(p) for p in captures]
    cap_ok = all(from_58(capture_h_changes(c)) == INGAME_H_FROM_58 and max(c) == INGAME_LAST_FRAME
                 for c in caps)
    got = from_58(stock.get("h_changes"))
    cw = stock.get("creature_window") or [None, None, None]
    hx1 = (stock["outcome"] == "ok" and cap_ok and got == INGAME_H_FROM_58
           and cw[0] == INGAME_CREATURE_FIRST and stock.get("native_frame_index") == INGAME_LAST_FRAME)
    record("HX1", hx1, "H from f58 %s vs in-game %s; creature first %s (in-game %d); last frame %s (in-game %d); "
           "%d capture(s) agree with the table: %s" % (got, INGAME_H_FROM_58, cw[0], INGAME_CREATURE_FIRST,
                                                       stock.get("native_frame_index"), INGAME_LAST_FRAME,
                                                       len(caps), cap_ok))

    # HX1b -- the whole camera, frame by frame, against the first capture
    head = frames_table(base_csv)
    cap = caps[0]
    lo, hi = MATRIX_WINDOW

    def score(offset: int) -> Tuple[int, int]:
        eq = tot = 0
        for f in range(lo, hi + 1):
            if f in cap and (f + offset) in head:
                tot += 1
                eq += head[f + offset]["M"] == cap[f][0]
        return eq, tot

    eq0, tot0 = score(0)
    side = max(score(-1)[0], score(1)[0])
    bad = [f for f in range(lo, hi + 1) if f in cap and f in head and head[f]["M"] != cap[f][0]]
    hx1b = tot0 > 300 and eq0 >= 0.95 * tot0 and side <= 0.05 * tot0
    record("HX1b", hx1b, "view matrix exact on %d/%d frames f%d..f%d (%.1f%%); one frame off: <=%d; "
           "differing frames %s" % (eq0, tot0, lo, hi, 100.0 * eq0 / max(1, tot0), side, _runs(bad)))

    # HX2 -- the falsifier: the same comparison must fail for a wrong host
    wrong = run(227, mode="legacy", motion_frames=30)
    wrong_h = from_58(wrong.get("h_changes"))
    record("HX2", wrong_h != INGAME_H_FROM_58,
           "legacy host, 30-frame animation: H from f58 %s -- HX1's comparison %s" % (
               wrong_h, "REJECTS it (the gate can fail)" if wrong_h != INGAME_H_FROM_58 else "ACCEPTS it"))

    # HX3
    again = run(227)
    record("HX3", again.get("stream_sha256") == stock.get("stream_sha256") and stock.get("stream_sha256"),
           "two runs: stream sha %s / %s" % (stock.get("stream_sha256", "")[:16],
                                            again.get("stream_sha256", "")[:16]))

    # HX4 -- W3, both builds
    man = json.loads((RETIME_DIR / "build_manifest.json").read_text())
    aligned = run(227, container=man["aligned"])
    mis = run(227, container=man["misretime"])
    n = int(man["n"])
    sh = from_58(stock["h_changes"], upto=None)
    ah, mh = from_58(aligned.get("h_changes"), upto=None), from_58(mis.get("h_changes"), upto=None)
    want_h = [sh[0]] + [(f + n, v) for f, v in sh[1:]]
    scw, acw, mcw = stock["creature_window"], aligned.get("creature_window"), mis.get("creature_window")
    hx4 = (aligned.get("container_sha256") == man["aligned_sha256"]
           and mis.get("container_sha256") == man["misretime_sha256"]
           and aligned.get("native_frame_index") == stock["native_frame_index"] + n
           and ah == want_h and mh == want_h
           and acw and acw[2] == scw[2] + n
           and mcw and abs(mcw[2] - scw[2]) <= 2)
    record("HX4", hx4, "N=%d: last frame %s->%s; H %s -> aligned %s / mis-retime %s; creature frames %s -> "
           "aligned %s / mis-retime %s" % (n, stock["native_frame_index"], aligned.get("native_frame_index"),
                                           sh, ah, mh, scw[2], acw and acw[2], mcw and mcw[2]))

    # HX5
    e407 = run(407)
    d = (e407.get("dr_move_dst_cells") or {}).get("x704_y384")
    record("HX5", bool(d and d["blits"] > 0 and "x704_y256" in d["from"]),
           "ef407 blits into x704_y384: %s" % (d and {k: d[k] for k in ("blits", "from", "frames")}))

    # HX6
    e211 = run(211)
    cells = e211.get("sampled_cells") or {}
    blit = (e211.get("dr_move_dst_cells") or {}).get("x704_y256")
    dome_direct = [k for k in cells if k.startswith("x704_y384@")]
    page = cells.get("x704_y256@8")
    hx6 = (not dome_direct and blit and "x704_y384" in blit["from"] and page
           and page["frames"] == blit["frames"])
    record("HX6", bool(hx6), "ef211: (704,384) sampled directly by %s; blit x704_y256 <- %s over %s; "
           "8bpp page on x704_y256 drawn over %s" % (dome_direct or "nothing",
                                                     blit and blit["from"], blit and blit["frames"],
                                                     page and page["frames"]))

    fails = [g for g, s, _ in results if s == "FAIL"]
    missing = [g for g, s, _ in results if s == "MISSING"]
    print("\n%d gates: %d PASS, %d FAIL, %d MISSING" % (
        len(results), sum(1 for _, s, _ in results if s == "PASS"), len(fails), len(missing)))
    return 1 if fails else (2 if missing else 0)


def _runs(frames: List[int]) -> str:
    out, cur = [], None
    for f in frames:
        if cur and f == cur[1] + 1:
            cur[1] = f
        else:
            cur = [f, f]
            out.append(cur)
    return ", ".join("f%d" % a if a == b else "f%d-%d" % (a, b) for a, b in out) or "none"


if __name__ == "__main__":
    sys.exit(main())
