"""root_reproject.py -- the offline faithfulness check + trajectory extractor for the s52 ROOT probe.

The s52 engine patch (memoria-patches/s52-sfx-summon-root.patch) logs a new ROOT row per frame while
[SfxProbe] Enabled=1 + CaptureRoot=1: the summoned creature's TRUE per-frame WORLD transform, read
straight off FF9SpecialEffectPlugin.dll's own runtime SummonData block (root world MATRIX -- 3x3 s16
rotation /4096 + s32 world translation). This is the datum the 2026-07-22 disasm round proved is the
only faithful source of the creature's staging -- see studies/custom-summons/thomas-swap/disasm/FINDINGS.md
and PROBE.md sec 10 for the arming + read-out procedure.

This script does three things over one instrumented cast's sfxmeshprobe.log:

  1. EXTRACT  -- the ROOT world trajectory (frame -> tx,ty,tz + an approximate heading yaw). This is the
     deliverable FLIGHT re-stages Thomas on: real metric positions, not v7's constructed NDC coverage.
  2. VALIDATE -- project each ROOT translation through the SAME frame's VIEW*PROJ (the s50 camera rows)
     using matrix_solve's proven projection primitives, and report on-screen coverage + the NDC path.
     A coherent, mostly-on-screen projection (with jumps only at the ~15 known camera hard-cuts) is the
     built-in faithfulness validator the s52 patch's own doc comment promises: it confirms the world read
     + the fixed-point/sign conventions are right, turning a v7-style constructed flight into a measured one.
  3. CROSS-CHECK -- how far the OLD proxy (matrix_solve's MESH body-bounds median, the method every prior
     FLIGHT used) sat from the true ROOT each frame. Quantifies the pool pollution the disasm diagnosed
     (FINDINGS sec 4): the MESH bounds are anchored to the SFX vertex pool's origin, not the creature.

Provenance: pure analysis over the user's own probe log. No game bytes are read or written; it only
interprets the raw fixed-point ROOT columns the s52 patch already logs.

Usage:
  py root_reproject.py                     # default log path; prints extract + validate + cross-check
  py root_reproject.py --log PATH          # a probe log elsewhere
  py root_reproject.py --csv roots.csv     # also write the per-frame trajectory as CSV for build_thomas
  py root_reproject.py --step 12           # sub-sample the printed trajectory table (every Nth frame)
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

import matrix_solve as ms  # project_world_to_ndc / is_on_screen / ProbeLog / BODY_KEYS / DEFAULT_LOG

FIXED = 4096.0  # PSX 1/4096 fixed-point (the root MATRIX rotation scale; identity diagonal = 0x1000)


class RootTrack:
    """Parsed ROOT rows: frame -> (rotation 3x3 float, translation (tx,ty,tz) world units, active byte)."""

    def __init__(self) -> None:
        self.rot: Dict[int, np.ndarray] = {}
        self.pos: Dict[int, Tuple[float, float, float]] = {}
        self.active: Dict[int, int] = {}
        self.effect_id: Optional[int] = None

    @classmethod
    def parse(cls, path: Path) -> "RootTrack":
        self = cls()
        # ROOT,effectId,frame,active,m00,m01,m02,m10,m11,m12,m20,m21,m22,tx,ty,tz  (16 fields after tag=17 cols)
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not line or line[0] == "#" or not line.startswith("ROOT,"):
                    continue
                p = line.rstrip("\n").split(",")
                if len(p) < 17:
                    continue
                try:
                    eff = int(p[1]); frame = int(p[2]); active = int(p[3])
                    m = [int(x) for x in p[4:13]]           # m00..m22, raw fixed
                    tx, ty, tz = (int(p[13]), int(p[14]), int(p[15]))
                except ValueError:
                    continue
                if self.effect_id is None:
                    self.effect_id = eff
                # last write wins per frame (one ROOT row per SFX.frameIndex by construction)
                self.rot[frame] = np.array(m, dtype=np.float64).reshape(3, 3) / FIXED
                self.pos[frame] = (float(tx), float(ty), float(tz))
                self.active[frame] = active
        return self

    def frames(self) -> List[int]:
        return sorted(self.pos.keys())


def heading_yaw_deg(rot: np.ndarray) -> float:
    """Approximate world heading (deg) from the root rotation matrix. CONVENTION-DEPENDENT -- reported as
    a rough facing indicator only (the exact PSX euler order was not needed to recover position). Uses the
    forward-vector heading in the XZ plane: atan2(R[0,2], R[2,2])."""
    return math.degrees(math.atan2(rot[0, 2], rot[2, 2]))


def body_proxy_world(log: ms.ProbeLog, frame: int) -> Optional[Tuple[float, float, float]]:
    """The OLD proxy every prior FLIGHT used: median across the 7 body MESH keys of (cx, cy, far-corner cz),
    pool-rows filtered exactly as matrix_solve does. Returns None if no body MESH rows that frame. Used only
    for the cross-check that quantifies how wrong the proxy was vs the true ROOT."""
    per = getattr(log, "_body", {}).get(frame)
    if not per:
        return None
    xs: List[float] = []
    ys: List[float] = []
    zs: List[float] = []
    for _key, rows in per.items():
        for (cx, cy, cz, ex, ey, ez) in rows:
            if ms.ProbeLog._is_pool_row(cx, cy, ex, ey):
                continue
            xs.append(cx); ys.append(cy)
            zs.append(ms.ProbeLog._far_corner_z(cz, ez))
    if not xs:
        return None
    return (float(np.median(xs)), float(np.median(ys)), float(np.median(zs)))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--log", type=Path, default=ms.DEFAULT_LOG, help="path to sfxmeshprobe.log")
    ap.add_argument("--csv", type=Path, default=None, help="write the per-frame ROOT trajectory as CSV")
    ap.add_argument("--step", type=int, default=10, help="print every Nth frame in the trajectory table")
    args = ap.parse_args()

    if not Path(args.log).is_file():
        print(f"probe log not found: {args.log}\n"
              "Arm the s52 ROOT probe ([SfxProbe] Enabled=1 AND CaptureRoot=1 in Memoria.ini -- and the\n"
              "engine must have the s52 patch BUILT), relaunch, cast a summon, let it play through.")
        return 2

    roots = RootTrack.parse(args.log)
    frames = roots.frames()
    if not frames:
        print("No ROOT rows in the log. Confirm [SfxProbe] CaptureRoot=1 AND that the s52 patch is built\n"
              "into the running engine, then recast a SUMMON (a non-summon effect logs no ROOT rows).")
        return 1

    cam = ms.ProbeLog.parse(args.log)  # VIEW/PROJ (+ MESH body for the cross-check)

    print(f"# ROOT trajectory: {len(frames)} frames [{frames[0]}..{frames[-1]}], effectId={roots.effect_id}")
    print(f"# columns: frame  tx  ty  tz  yaw_deg~  ndc_x  ndc_y  on_screen  view_z  proxy_dxyz")
    on = 0
    have_cam = 0
    proxy_err: List[float] = []
    csv_rows: List[str] = []
    for i, f in enumerate(frames):
        tx, ty, tz = roots.pos[f]
        yaw = heading_yaw_deg(roots.rot[f])
        ndc_s = "   --      --   "
        onscr = "?"
        vz = float("nan")
        if cam.has_camera(f):
            have_cam += 1
            nx, ny, nz, vz = ms.project_world_to_ndc(cam.view(f), cam.proj(f), (tx, ty, tz))
            is_on = ms.is_on_screen(nx, ny, vz)
            on += 1 if is_on else 0
            onscr = "Y" if is_on else "n"
            ndc_s = f"{nx:+.3f} {ny:+.3f}"
        # cross-check vs the old pooled proxy
        proxy = body_proxy_world(cam, f)
        pd = ""
        if proxy is not None:
            d = math.sqrt(sum((a - b) ** 2 for a, b in zip((tx, ty, tz), proxy)))
            proxy_err.append(d)
            pd = f"d={d:8.1f}"
        csv_rows.append(f"{f},{tx:.1f},{ty:.1f},{tz:.1f},{yaw:.2f},{vz:.1f}")
        if i % max(1, args.step) == 0:
            print(f"{f:5d}  {tx:9.1f} {ty:8.1f} {tz:10.1f}  {yaw:+7.1f}  {ndc_s}   {onscr}   {vz:10.1f}  {pd}")

    print()
    print(f"# VALIDATE: {have_cam}/{len(frames)} frames had a logged camera; "
          f"{on}/{have_cam if have_cam else 1} of those project ON-SCREEN "
          f"({100.0 * on / (have_cam if have_cam else 1):.1f}%).")
    print("#   (the real cinematic deliberately swoops the creature off-screen at points, so <100% is")
    print("#    expected and faithful -- a COHERENT path with jumps only at the ~15 camera hard-cuts is")
    print("#    the pass condition, not universal on-screen. Overlay a video of the same cast to confirm.)")
    if proxy_err:
        pe = np.array(proxy_err)
        print(f"# CROSS-CHECK: old MESH-bounds proxy vs true ROOT over {len(pe)} shared frames -- "
              f"median off by {np.median(pe):.0f} world units, p90 {np.percentile(pe, 90):.0f}, max {pe.max():.0f}.")
        print("#   (large = the disasm-diagnosed pool pollution: MESH bounds anchor to the SFX vertex-pool")
        print("#    origin, not the creature. This is WHY every prior FLIGHT built on those bounds scattered.)")

    if args.csv:
        Path(args.csv).write_text(
            "frame,tx,ty,tz,yaw_deg,view_z\n" + "\n".join(csv_rows) + "\n", encoding="utf-8")
        print(f"\n# wrote {len(csv_rows)} rows -> {args.csv}  (feed to build_thomas.py / flight_v7_solve.py)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
