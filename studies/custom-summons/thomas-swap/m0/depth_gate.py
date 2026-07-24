"""depth_gate.py -- M0 item (d) PREP: the effect-prim/creature depth-interleave gate.

WHAT THIS ANSWERS (TRANSPLANT.md sec 1.1/1.3/2.4/4 P4): does any native effect PRIM occupy the
CREATURE's own screen region at a NEARER depth, on a frame where the creature is actually framed?
If yes for a meaningful fraction of frames, that summon's effect physically interleaves with the
creature body and the HYBRID transplant (our mesh, ordinary Unity depth) will composite it wrong
(SFXRender.Render() sorts the effect prims in their OWN screen-space regime, TRANSPLANT.md sec 1.2/1.5)
-- that summon needs the reserved NATIVE (T2) path instead. If no/rare, HYBRID suffices.

THE LOG DOES NOT HAVE PRIM ROWS YET. CapturePrims was never armed on the existing capture (PROBE.md
sec 11 / sec 8 -- the current sfxmeshprobe.log has PSXCAM/MODEL/BONES rows from the s53 build, zero
PRIM/STATE rows). This script is written to run correctly THE MOMENT a PRIM-bearing log exists; run
today it prints exactly what to arm (see CAST-PROTOCOL.md, this directory) and exits 0 -- never
crashes, never demands data that isn't there yet. This was verified by actually running it against
the live install's current log (see the run transcript this round's findings cite).

=====================================================================================================
THE OTZ POLARITY -- READ THIS BEFORE TRUSTING ANY NUMBER BELOW (M0 item (d), part 2 of the brief)
=====================================================================================================

Two DIFFERENT quantities are in play and they have OPPOSITE sign conventions. Getting this backwards
silently inverts every near/far verdict this script produces.

  (1) THE RAW NATIVE OTZ -- the PSX ordering-table depth key, the `ref Int32 otz` out-parameter of
      the native import  `SFX_GetPrim(ref Int32 otz)`
      (C:/gd/FFIX/Memoria/Assembly-CSharp/Global/SFX/SFX.cs:753,827-830 -- the managed P/Invoke
      literally names the parameter `otz`). Every drawable PSX primitive the plugin decodes surfaces
      through this call once (SFXRender.cs Update(), :77-86).

      POLARITY, established from source (not assumed):
        * SFXRender.cs:83  `SFXMesh.GzDepth = -num;`             (num == the raw native otz)
        * SFXMesh.cs (e.g. :346) `__gPos[..].Set(x, y, GzDepth)` -- GzDepth becomes the mesh's own
          vertex Z, literally, for every primitive type (PolyF3/Ft3/.../Tile/Sprt all do this).
        * SFXRender.cs:127,130,135 -- `Render()` sets `camera.worldToCameraMatrix = Matrix4x4.identity`
          for the WHOLE SFX draw walk (`commandBuffer[i].Render(i)`), restoring the real matrix only
          after. So a mesh's own (object-space) Z IS fed directly as EYE-SPACE Z into whatever
          `camera.projectionMatrix` is currently installed -- no view transform intervenes.
        * The codebase's projection matrices are the textbook OpenGL/Unity off-center-frustum form
          (`PerspectiveOffCenter`, C:/gd/FFIX/Memoria/Assembly-CSharp/Global/PSX/PsxCamera.cs:122-149:
          row2 = `-(far+near)/(far-near)`, row2col3 = `-2*far*near/(far-near)`, row3 = `-1`) -- the
          universal Unity/OpenGL eye-space convention: the camera looks down -Z, eye-space Z sits in
          `[-far, -near]`, so Z NEAR ZERO (small magnitude, e.g. -near) is NEAREST and Z FAR NEGATIVE
          (large magnitude, e.g. -far) is FARTHEST. (Independently re-affirmed for this exact study's
          own managed VIEW track: matrix_solve.py's docstring, "camera looks down -Z ... on-screen iff
          view.z < 0 (in front)" -- the same sign law, a second citation.)

      Chase the sign through: mesh Z = -otz_native. For that Z to land in the near/far eye-space band
      (near 0 == NEAR, very negative == FAR), a SMALL native otz must map to a Z near zero (NEAR) and a
      LARGE native otz must map to a very negative Z (FAR). THEREFORE:

          >>> SMALLER raw native otz  =  NEARER the camera <<<
          >>> LARGER  raw native otz  =  FARTHER              <<<

      This also matches the standard PSX/PSY-Q GTE convention independently (AVSZ derives the OT
      bucket from the same clamped, always-non-negative `SZ3` the perspective divide itself uses --
      FORMAT.md sec 1.2's `SZ3 = clamp(MAC3, 0, 0xFFFF)`; larger SZ3 == farther by construction of the
      perspective-divide itself, `q = (H<<16)/SZ3` shrinks as SZ3 grows).

  (2) THE LOGGED `PRIM` ROW'S OWN "otz" COLUMN -- what SfxMeshProbe.cs actually writes.
      Writer: C:/gd/FFIX/Memoria/Assembly-CSharp/Memoria/Battle/SFX/SfxMeshProbe.cs:793-795
        `w.WriteLine(... "PRIM,{0},{1},{2},{3},{4},{5:F4},{6},{7}", effectId, frame, index, code,
         label, SFXMesh.GzDepth, x, y)`
      -- the 6th data field (this script's `otz_logged`) IS `SFXMesh.GzDepth`, i.e. `-otz_native`
      (SFXRender.cs:83, see above). NOT the raw native otz. It is already negated once, in the log.

      THEREFORE THE LOGGED COLUMN HAS THE OPPOSITE-SIGNED READING FROM THE RAW NATIVE VALUE:

          >>> LARGER  (closer to zero / more positive) logged otz  =  NEARER <<<
          >>> SMALLER (more negative) logged otz                  =  FARTHER <<<

  THIS SCRIPT ALWAYS RECOVERS THE RAW NATIVE VALUE FIRST (`raw = -otz_logged`, undoing the log's own
  negation) before comparing anything, and reasons ONLY in "raw native otz, smaller = nearer" terms
  from that point on (see `_raw_native_otz()`). Freshness note: `GzDepth` is a single static field
  overwritten immediately before EVERY `SFXRender.Add(ptr)` call (SFXRender.cs:79-84, single-threaded,
  synchronous) and `LogPrim` is the first statement inside `Add()` (SFXRender.cs:215-216) -- so the
  value logged for a given PRIM row is guaranteed fresh for THAT primitive, never a stale carry-over
  from the previous one.

  UNCONFIRMED (flagged, not blocking): whether the Unity material/shader assigned to these SFXMesh
  draws actually enables hardware ZTest (so GzDepth genuinely gates per-pixel occlusion against our
  hidden creature's own depth) or whether on-screen compositing is closer to pure draw-order (painter's
  algorithm via commandBuffer/PushCommandBufferOpa/Add/Sub insertion order, SFXRender.cs:476-564) with
  GzDepth mattering only WITHIN one already-batched SFXMesh. The shaders (`SFX_OPA_GT` etc.,
  SFXMesh.cs:979-983) are compiled Unity assets, not present in this C# source tree, so ZTest state
  could not be read from source this round. Either way, GzDepth expresses the plugin's OWN intended
  PSX depth-ordering for that primitive (it is derived from the same per-vertex SZ3 GTE math that
  produces the primitive's screen position), which is the thing this gate needs to reason about
  ("does this effect want to be in front of or behind the creature") -- flag, don't block.

=====================================================================================================
COORDINATE-SPACE CAVEAT (also flagged, self-calibrated best-effort, not fully closed this round)
=====================================================================================================

The creature's own screen AABB (computed here from BONES + PSXCAM via the M0-proven zero-free-
parameter native GTE identity, disasm/FORMAT.md sec 1.4/5.4, reused verbatim from flight_v9_solve.py's
`parse_native_path`) comes out in RAW PSX SCREEN SPACE, centered at (OFX,OFY)=(160,120), no widescreen
adjustment. But a logged `PRIM` row's `x,y` are `vertex0 + SFXMeshBase.drOffsetX/Y`
(SfxMeshProbe.cs:764-769) -- and `drOffsetX = CalculateWidescreenOffsetX() = (FieldMap.PsxScreenWidth -
FieldMap.PsxScreenWidthNative) / 2` (SFXRender.cs:791-794), which is NONZERO whenever the capture runs
at other than the native 4:3 (the common case on a modern widescreen Steam install). This is exactly
TRANSPLANT.md sec 1.1's flagged-open "horizontal/widescreen pixel-equality is measured at Milestone 0,
not free" residual, now hit directly by this gate.

Rather than block on it, `analyze()` SELF-CALIBRATES a best-effort `drOffsetX` estimate per run: among
"framed" frames (creature's own reprojected NDC within FRAMED_NDC_MARGIN, matching flight_v9_solve.py's
own NDC_CLAMP=1.5 convention) it looks for a PRIM whose recovered raw depth is within
CALIB_DEPTH_TOL_FRAC of the creature's own centroid depth AND whose y is within CALIB_Y_TOL of the
creature centroid's projected y (the offset is X-ONLY per CalculateWidescreenOffsetX's own definition,
so a close Y match is a strong "this IS a creature-body primitive" signal, needing no X assumption to
find it) -- the median x-delta over >= MIN_CALIB_SAMPLES such matches is the estimate; below that,
falls back to 0 with an explicit "UNCALIBRATED" warning in the report (never silently wrong). This is
an operational re-derivation of FORMAT.md sec 5.4 step 5's own falsifiable prediction, reused as a
calibration tool rather than a pass/fail check -- treat its output as informational until a human/agent
cross-checks it against a captured video frame.

=====================================================================================================
USAGE
=====================================================================================================

    py depth_gate.py                      # analyze the live install's log (or degrade gracefully)
    py depth_gate.py --log PATH           # analyze an arbitrary log (e.g. an archived one)
    py depth_gate.py --verbose            # also print the full per-frame table (can be long)
    py depth_gate.py --csv OUT.csv        # dump the per-frame stats to a CSV alongside stdout

Exit code is always 0 on a successful run (including the graceful-degrade path) -- this is an offline
analysis tool, never a build gate; a non-zero exit is reserved for a genuinely malformed --log path
argument (not "the data isn't captured yet").
"""
from __future__ import annotations

import argparse
import csv as csv_module
import statistics
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# --------------------------------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------------------------------

DEFAULT_LOG = Path(
    r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\sfxmeshprobe.log"
)

# The ini block this script's happy path needs, on top of what's ALREADY armed on this install
# (Enabled/CaptureRoot/CaptureModels/ModelsActiveOnly/ModelsCap/ModelsBoneCount -- verified live
# 2026-07-23, see CAST-PROTOCOL.md). Printed verbatim in the graceful-degrade message.
REQUIRED_INI_ADD = (
    "[SfxProbe]\n"
    "Enabled = 1          ; already armed -- KEEP\n"
    "CaptureRoot = 1      ; already armed -- KEEP\n"
    "CaptureModels = 1    ; already armed -- KEEP (PSXCAM + BONES need this)\n"
    "ModelsActiveOnly = 1 ; already armed -- KEEP\n"
    "ModelsCap = 120000   ; already armed -- KEEP\n"
    "ModelsBoneCount = 93 ; already armed -- KEEP (ef227/Bahamut's node count)\n"
    "CapturePrims = 1     ; ADD -- this is the one this script needs\n"
    "PrimSummary = 0      ; ADD (or omit -- 0 is default) -- PRIMSUM rows have no x,y/otz, unusable here\n"
    "PrimCap = 3000000    ; ADD, raised from the 200000 default -- see CAST-PROTOCOL.md sec 2\n"
)

# Padding (raw PSX screen pixels) added around the creature's reprojected corner-hull AABB, to absorb
# sub-pixel/quantization slop in the 8-corner reprojection. PLACEHOLDER -- retune once real PRIM data
# exists and the true pixel footprint of a body-wrapping effect is visible (CAST-PROTOCOL.md sec 4).
AABB_PAD_PX = 6.0

# "Nearer than the creature" comparison margin, in the SAME raw units as native otz (proportional to
# the clamped SZ3 view-space Z, FORMAT.md sec 1.2/1.4). PLACEHOLDER -- this round has ZERO real PRIM
# otz values to calibrate against; retune from the first real cast's own otz distribution (this script
# prints percentiles for exactly that purpose once PRIM data exists).
DEPTH_EPS = 50.0

# "Framed" gate: creature's own centroid NDC (native 320x240 space, OFX/OFY=160/120) within this many
# half-screens of center. Reuses flight_v9_solve.py's own NDC_CLAMP=1.50 convention verbatim (a
# generous "roughly on/near screen" gate, not a strict on-screen test) -- so verdicts are computed only
# over frames where "is this effect near the creature" is a meaningful question at all.
FRAMED_NDC_MARGIN = 1.50

# Self-calibration of the widescreen X offset (see the coordinate-space caveat above).
CALIB_DEPTH_TOL_FRAC = 0.10   # relative tolerance vs the creature's own centroid depth
CALIB_Y_TOL_PX = 8.0          # absolute Y tolerance (Y needs no shift -- CalculateWidescreenOffsetX is X-only)
MIN_CALIB_SAMPLES = 8

# Hybrid-vs-native verdict heuristic (TRANSPLANT.md sec 4 P4 / sec 2.4 M0 item (d)): a phase is flagged
# NATIVE if MORE THAN this fraction of its FRAMED frames show >=1 nearer-overlapping PRIM. Rationale:
# TRANSPLANT.md explicitly scopes the depth residual to effects that "physically wrap" the creature --
# a single stray triangle on one frame (quantization noise, a thin sliver clipped by AABB_PAD_PX) is not
# that; a sustained several-percent-of-frames pattern is. PLACEHOLDER threshold pending real data --
# print the raw rate per phase regardless so a human can override this call from the printed numbers.
NATIVE_FRAME_FRACTION_THRESHOLD = 0.05
MIN_FRAMED_FOR_VERDICT = 5   # below this many framed frames in a phase, call it INSUFFICIENT-DATA

# The cast's own piece-boundary table (PROBE.md sec 8 "The trajectory reconstruction method" / "The
# measured trajectory" table -- the SAME Bahamut Cinema cinematic this script's log comes from). Frame
# ranges bucket the per-frame stats into named cinematic beats for the per-phase table.
PHASES: List[Tuple[int, int, str]] = [
    (0, 82, "pre-P1 (entrance lead-in, unmeasured in the round-1 capture)"),
    (82, 144, "P1->P2 rise-to-far"),
    (144, 157, "P2->P3 far-dip"),
    (157, 172, "P3->P4 far-deep hold (PROBE.md flags this window as sparse/low-n)"),
    (172, 179, "P4->P5 return-cut"),
    (179, 204, "P5->P6 2nd-approach"),
    (204, 207, "P6->P7 charge-cut"),
    (207, 250, "P7->P8 charge-hold"),
    (250, 414, "P8->P9 ground-reign"),
    (414, 417, "P9->P10 exit-edge"),
    (417, 10 ** 9, "post-body / fire-column tail (creature typically undrawn)"),
]


def _phase_for(frame: int) -> str:
    for lo, hi, label in PHASES:
        if lo <= frame < hi:
            return label
    return PHASES[-1][2]


def _sat16(v: int) -> int:
    """Same clamp flight_v9_solve.py's own `_sat16` applies to IR1/IR2 before the projection divide
    (disasm/FORMAT.md sec 1.2's GTE RTPS: `IR1 = sat16(MAC1)`)."""
    return -32768 if v < -32768 else (32767 if v > 32767 else v)


def _project_point(R: List[int], T: List[int], H: int, v: Tuple[float, float, float]) -> Optional[Tuple[float, float, float]]:
    """The zero-free-parameter native GTE reprojection (disasm/FORMAT.md sec 1.2/1.4/5.4, identical
    arithmetic to flight_v9_solve.py's `parse_native_path`): world point -> (screen_x, screen_y,
    raw_view_z). Returns None if the point is behind the camera (pz<=0 -- genuinely off this frame, not
    a bug) or if H==0 (would divide-by-H<<16 by zero; the camera stepper never emits H=0 in practice,
    but guard it since this is untested territory).

        pz = raw view-space Z (the SZ3-analog: always >=0 once clamped, larger==farther -- the SAME
             quantity the native `otz` is (per the polarity section above) an AVSZ-scaled function of).
             This is what `raw_native_otz` (recovered from a PRIM row) is compared against.
    """
    vx, vy, vz = int(v[0]), int(v[1]), int(v[2])
    px = ((R[0] * vx + R[1] * vy + R[2] * vz) >> 12) + T[0]
    py = ((R[3] * vx + R[4] * vy + R[5] * vz) >> 12) + T[1]
    pz = ((R[6] * vx + R[7] * vy + R[8] * vz) >> 12) + T[2]
    if pz <= 0 or H == 0:
        return None
    sz = min(65535, pz)
    q = (H << 16) // sz
    sx = 160 + ((_sat16(int(px)) * q) >> 16)
    sy = 120 + ((_sat16(int(py)) * q) >> 16)
    return (float(sx), float(sy), float(pz))


def _raw_native_otz(otz_logged: float) -> float:
    """Recover the raw native `SFX_GetPrim(ref Int32 otz)` value from a logged PRIM row's 6th field.
    SFXRender.cs:83 negates it once on the way into the log (`SFXMesh.GzDepth = -num`); undo that here,
    ONE place, so every downstream comparison in this file reasons in "smaller raw = nearer" terms
    (see the OTZ POLARITY section in this module's docstring)."""
    return -otz_logged


# --------------------------------------------------------------------------------------------------
# Log parsing (two cheap passes: pass 1 is O(1) memory per frame -- PSXCAM/BONES/tag tallies only;
# pass 2, only entered if PRIM rows exist at all, streams PRIM rows against the pass-1 creature data
# and keeps ONLY small per-frame/per-phase aggregates -- never buffers the (potentially huge,
# FORMAT.md warns 10-100x the ~19,456 MESH-row count) raw PRIM stream in memory.)
# --------------------------------------------------------------------------------------------------

class CreatureFrame:
    __slots__ = ("frame", "aabb", "depth", "framed", "ndc_x", "ndc_y")

    def __init__(self, frame: int, aabb: Tuple[float, float, float, float], depth: float,
                 framed: bool, ndc_x: float, ndc_y: float) -> None:
        self.frame = frame
        self.aabb = aabb  # (xmin, xmax, ymin, ymax), padded
        self.depth = depth  # creature centroid raw view-Z (BONES cx,cy,cz reprojected)
        self.framed = framed
        self.ndc_x = ndc_x
        self.ndc_y = ndc_y


def scan_pass1(path: Path) -> Tuple[Dict[str, int], Dict[int, Tuple[List[int], List[int], int]], Dict[int, dict]]:
    """One streaming pass: tag counts (for the graceful-degrade decision) + PSXCAM rows + BONES rows.
    Both PSXCAM and BONES are O(1-2 rows)/frame regardless of cast length -- cheap to hold in full."""
    counts: Dict[str, int] = {}
    psxcam: Dict[int, Tuple[List[int], List[int], int]] = {}
    bones: Dict[int, dict] = {}
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line or line[0] == "#":
                continue
            p = line.rstrip("\n").split(",")
            tag = p[0]
            counts[tag] = counts.get(tag, 0) + 1
            if tag == "PSXCAM":
                # PSXCAM,effectId,frame,m00..m22(9),tx,ty,tz,ofx,ofy,h,psxPtr(hex)
                try:
                    frame = int(p[2])
                    R = [int(x) for x in p[3:12]]
                    T = [int(x) for x in p[12:15]]
                    h = int(p[17])
                except (ValueError, IndexError):
                    continue
                psxcam[frame] = (R, T, h)
            elif tag == "BONES":
                # BONES,effectId,frame,n,cx,cy,cz,minX,minY,minZ,maxX,maxY,maxZ
                try:
                    frame = int(p[2])
                    n = int(p[3])
                    cx, cy, cz = float(p[4]), float(p[5]), float(p[6])
                    minX, minY, minZ = float(p[7]), float(p[8]), float(p[9])
                    maxX, maxY, maxZ = float(p[10]), float(p[11]), float(p[12])
                except (ValueError, IndexError):
                    continue
                bones[frame] = dict(n=n, cx=cx, cy=cy, cz=cz, minX=minX, minY=minY, minZ=minZ,
                                     maxX=maxX, maxY=maxY, maxZ=maxZ)
    return counts, psxcam, bones


def build_creature_frames(psxcam: Dict[int, Tuple[List[int], List[int], int]],
                           bones: Dict[int, dict]) -> Dict[int, CreatureFrame]:
    """Per frame present in BOTH streams: the creature's screen AABB (native-GTE reprojection of the 8
    BONES-AABB corners, TRANSPLANT.md sec 2.4 M0 item (d)'s own spec) + centroid depth + framed flag."""
    out: Dict[int, CreatureFrame] = {}
    for frame, b in bones.items():
        cam = psxcam.get(frame)
        if cam is None:
            continue
        R, T, H = cam
        corners = [
            (x, y, z)
            for x in (b["minX"], b["maxX"])
            for y in (b["minY"], b["maxY"])
            for z in (b["minZ"], b["maxZ"])
        ]
        sxs: List[float] = []
        sys_: List[float] = []
        for c in corners:
            proj = _project_point(R, T, H, c)
            if proj is not None:
                sxs.append(proj[0])
                sys_.append(proj[1])
        if not sxs:
            continue  # entire AABB behind the camera this frame -- not on screen, skip
        centroid_proj = _project_point(R, T, H, (b["cx"], b["cy"], b["cz"]))
        if centroid_proj is None:
            continue  # centroid itself behind camera -- no depth reference this frame
        csx, csy, cpz = centroid_proj
        aabb = (min(sxs) - AABB_PAD_PX, max(sxs) + AABB_PAD_PX,
                min(sys_) - AABB_PAD_PX, max(sys_) + AABB_PAD_PX)
        ndc_x = (csx - 160.0) / 160.0
        ndc_y = (120.0 - csy) / 120.0
        framed = abs(ndc_x) <= FRAMED_NDC_MARGIN and abs(ndc_y) <= FRAMED_NDC_MARGIN
        out[frame] = CreatureFrame(frame, aabb, cpz, framed, ndc_x, ndc_y)
    return out


def self_calibrate_offset_x(path: Path, creature: Dict[int, CreatureFrame]) -> Tuple[float, int]:
    """Best-effort widescreen drOffsetX estimate (see the coordinate-space caveat in the module
    docstring). Streams PRIM rows once, collecting x-deltas at (framed frame, depth-matched, y-close)
    candidates; returns (estimate, n_samples). n_samples < MIN_CALIB_SAMPLES -> caller must treat the
    estimate as unreliable (this function still returns its best guess; the caller decides whether to
    apply it, and the report always prints n_samples so the reader can judge)."""
    deltas: List[float] = []
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line or line[0] != "P" or not line.startswith("PRIM,"):
                continue
            p = line.rstrip("\n").split(",")
            try:
                frame = int(p[2])
            except (ValueError, IndexError):
                continue
            cf = creature.get(frame)
            if cf is None or not cf.framed:
                continue
            try:
                otz_logged = float(p[6])
                x = float(p[7])
                y = float(p[8])
            except (ValueError, IndexError):
                continue
            raw = _raw_native_otz(otz_logged)
            # creature's own centroid screen y (un-padded) for the y-closeness test
            csy = 120.0 - cf.ndc_y * 120.0
            if abs(y - csy) > CALIB_Y_TOL_PX:
                continue
            if abs(raw - cf.depth) > CALIB_DEPTH_TOL_FRAC * max(1.0, cf.depth):
                continue
            csx = cf.ndc_x * 160.0 + 160.0
            deltas.append(x - csx)
    if len(deltas) >= MIN_CALIB_SAMPLES:
        return statistics.median(deltas), len(deltas)
    return 0.0, len(deltas)


class PhaseStats:
    __slots__ = ("frames_creature_present", "frames_framed", "frames_with_prims",
                 "frames_with_aabb_overlap", "frames_with_near_overlap",
                 "total_prims_examined", "total_inside_aabb", "total_near_overlap")

    def __init__(self) -> None:
        self.frames_creature_present = 0
        self.frames_framed = 0
        self.frames_with_prims = 0
        self.frames_with_aabb_overlap = 0
        self.frames_with_near_overlap = 0
        self.total_prims_examined = 0
        self.total_inside_aabb = 0
        self.total_near_overlap = 0


def analyze_prims(path: Path, creature: Dict[int, CreatureFrame], offset_x: float
                   ) -> Tuple[Dict[int, Tuple[int, int, int]], Dict[str, PhaseStats], List[float]]:
    """Second streaming pass: per-frame (n_examined, n_inside_aabb, n_near_overlap) aggregates (O(1)
    memory per unique frame, never buffers individual PRIM rows), the same rolled up per PHASE, and a
    sample of raw native otz values (capped) for the percentile printout that helps retune DEPTH_EPS."""
    per_frame: Dict[int, List[int]] = {}
    phases: Dict[str, PhaseStats] = {label: PhaseStats() for _, _, label in PHASES}
    otz_sample: List[float] = []
    OTZ_SAMPLE_CAP = 20000
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line or not line.startswith("PRIM,"):
                continue
            p = line.rstrip("\n").split(",")
            try:
                frame = int(p[2])
                otz_logged = float(p[6])
                x = float(p[7])
                y = float(p[8])
            except (ValueError, IndexError):
                continue
            cf = creature.get(frame)
            if cf is None:
                continue
            raw = _raw_native_otz(otz_logged)
            if len(otz_sample) < OTZ_SAMPLE_CAP:
                otz_sample.append(raw)
            xmin, xmax, ymin, ymax = cf.aabb
            xc = x - offset_x
            inside = xmin <= xc <= xmax and ymin <= y <= ymax
            near = inside and (raw < cf.depth - DEPTH_EPS)
            row = per_frame.setdefault(frame, [0, 0, 0])
            row[0] += 1
            if inside:
                row[1] += 1
            if near:
                row[2] += 1
    # roll per-frame into per-phase (including frames with zero PRIM rows, so the denominator for
    # "rate" reflects ALL framed frames, not just the ones lucky enough to have a prim recorded)
    for frame, cf in creature.items():
        label = _phase_for(frame)
        ps = phases[label]
        ps.frames_creature_present += 1
        if cf.framed:
            ps.frames_framed += 1
        n_examined, n_inside, n_near = per_frame.get(frame, [0, 0, 0])
        if n_examined:
            ps.frames_with_prims += 1
        if n_inside:
            ps.frames_with_aabb_overlap += 1
        if n_near:
            ps.frames_with_near_overlap += 1
        ps.total_prims_examined += n_examined
        ps.total_inside_aabb += n_inside
        ps.total_near_overlap += n_near
    return {f: tuple(v) for f, v in per_frame.items()}, phases, otz_sample


def verdict_for_phase(ps: PhaseStats) -> str:
    """The one-line hybrid-vs-native heuristic (TRANSPLANT.md sec 4 P4). See
    NATIVE_FRAME_FRACTION_THRESHOLD's docstring above for the rationale; PLACEHOLDER threshold, print
    the raw rate always so a human can override."""
    if ps.frames_framed < MIN_FRAMED_FOR_VERDICT:
        return "INSUFFICIENT-DATA"
    rate = ps.frames_with_near_overlap / ps.frames_framed
    if rate > NATIVE_FRAME_FRACTION_THRESHOLD:
        return "NATIVE"
    if rate > 0.0:
        return "BORDERLINE"
    return "HYBRID-OK"


_SEVERITY = {"NATIVE": 3, "BORDERLINE": 2, "HYBRID-OK": 1, "INSUFFICIENT-DATA": 0}


def overall_verdict(phase_verdicts: Dict[str, str]) -> str:
    real = [v for v in phase_verdicts.values() if v != "INSUFFICIENT-DATA"]
    if not real:
        return "INSUFFICIENT-DATA"
    worst = max(real, key=lambda v: _SEVERITY[v])
    return worst


# --------------------------------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------------------------------

def print_graceful_degrade(path: Path, counts: Dict[str, int]) -> None:
    print("=== depth_gate.py -- CANNOT RUN THE DEPTH GATE YET ===")
    print(f"log: {path}")
    if counts:
        print("row-type tallies found in this log:")
        for tag in sorted(counts):
            print(f"  {tag:10s} {counts[tag]:>10d}")
    else:
        print("(log is empty or unreadable)")
    missing = []
    if counts.get("PSXCAM", 0) == 0:
        missing.append("PSXCAM (needs [SfxProbe] CaptureModels=1, x64 only)")
    if counts.get("BONES", 0) == 0:
        missing.append("BONES (needs [SfxProbe] CaptureModels=1 AND ModelsBoneCount>0)")
    if counts.get("PRIM", 0) == 0:
        missing.append("PRIM (needs [SfxProbe] CapturePrims=1) -- THE MISSING PIECE THIS ROUND")
    print("\nmissing row types this gate needs: " + (", ".join(missing) if missing else "(none -- but"
          " something else prevented analysis; check the log for parse errors)"))
    print("\nTo unblock: archive this log, then arm the FULL block below in Memoria.ini, relaunch, cast")
    print("Bahamut Cinema once, quit. Full protocol: m0/CAST-PROTOCOL.md (this directory).\n")
    print(REQUIRED_INI_ADD)


def print_full_report(counts: Dict[str, int], creature: Dict[int, CreatureFrame],
                       per_frame: Dict[int, Tuple[int, int, int]], phases: Dict[str, PhaseStats],
                       otz_sample: List[float], offset_x: float, n_calib_samples: int,
                       verbose: bool) -> Dict[str, str]:
    print("=== depth_gate.py -- THE DEPTH GATE ===")
    print(f"row tallies: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    print(f"creature-reliable frames (PSXCAM+BONES both present): {len(creature)}")
    n_framed = sum(1 for cf in creature.values() if cf.framed)
    print(f"  of which 'framed' (|ndc|<={FRAMED_NDC_MARGIN}): {n_framed}")
    calib_note = "RELIABLE" if n_calib_samples >= MIN_CALIB_SAMPLES else "UNRELIABLE/UNCALIBRATED (too few samples -- treated as 0)"
    print(f"self-calibrated widescreen drOffsetX estimate: {offset_x:+.2f} px "
          f"(n={n_calib_samples} matched samples -- {calib_note})")
    if otz_sample:
        otz_sample.sort()
        n = len(otz_sample)

        def pct(p: float) -> float:
            return otz_sample[min(n - 1, int(p * n))]

        print(f"raw native otz distribution (sampled, n={n}): "
              f"p5={pct(0.05):.0f} p50={pct(0.50):.0f} p95={pct(0.95):.0f} "
              f"min={otz_sample[0]:.0f} max={otz_sample[-1]:.0f}  "
              f"(use this to retune DEPTH_EPS={DEPTH_EPS:.0f}, currently a placeholder)")

    print(f"\n{'phase':60s} {'present':>7} {'framed':>7} {'w/prims':>8} {'overlap':>8} {'near':>6} "
          f"{'rate':>7}  verdict")
    phase_verdicts: Dict[str, str] = {}
    for lo, hi, label in PHASES:
        ps = phases[label]
        rate = (ps.frames_with_near_overlap / ps.frames_framed) if ps.frames_framed else 0.0
        v = verdict_for_phase(ps)
        phase_verdicts[label] = v
        print(f"{label:60s} {ps.frames_creature_present:7d} {ps.frames_framed:7d} "
              f"{ps.frames_with_prims:8d} {ps.frames_with_aabb_overlap:8d} "
              f"{ps.frames_with_near_overlap:6d} {rate:6.1%}  {v}")

    if verbose:
        print("\n=== per-frame overlap stats (--verbose) ===")
        print(f"{'frame':>6} {'phase':40s} {'framed':>6} {'n_prims':>8} {'inside':>7} {'near':>5}")
        for frame in sorted(creature):
            cf = creature[frame]
            n_examined, n_inside, n_near = per_frame.get(frame, (0, 0, 0))
            print(f"{frame:6d} {_phase_for(frame):40s} {str(cf.framed):>6} "
                  f"{n_examined:8d} {n_inside:7d} {n_near:5d}")

    ov = overall_verdict(phase_verdicts)
    worst_phase = max(phase_verdicts, key=lambda k: _SEVERITY[phase_verdicts[k]]) if phase_verdicts else "(none)"
    print(f"\nVERDICT: {ov} -- worst phase '{worst_phase}' "
          f"(threshold: >{NATIVE_FRAME_FRACTION_THRESHOLD:.0%} of a phase's framed frames showing a "
          f"nearer-overlapping PRIM => NATIVE; else HYBRID-OK; PLACEHOLDER threshold, see NATIVE_FRAME_"
          f"FRACTION_THRESHOLD's docstring -- re-derive DEPTH_EPS/AABB_PAD_PX from the printed otz "
          f"percentiles + a captured video frame before trusting this call for real.)")
    return phase_verdicts


def write_csv(csv_path: Path, creature: Dict[int, CreatureFrame],
              per_frame: Dict[int, Tuple[int, int, int]]) -> None:
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        w = csv_module.writer(fh)
        w.writerow(["frame", "phase", "framed", "ndc_x", "ndc_y", "creature_depth",
                    "n_prims_examined", "n_inside_aabb", "n_near_overlap"])
        for frame in sorted(creature):
            cf = creature[frame]
            n_examined, n_inside, n_near = per_frame.get(frame, (0, 0, 0))
            w.writerow([frame, _phase_for(frame), cf.framed, f"{cf.ndc_x:.4f}", f"{cf.ndc_y:.4f}",
                        f"{cf.depth:.1f}", n_examined, n_inside, n_near])


# --------------------------------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--log", type=Path, default=DEFAULT_LOG, help="probe log path")
    ap.add_argument("--verbose", action="store_true", help="also print the full per-frame table")
    ap.add_argument("--csv", type=Path, default=None, help="write per-frame stats to this CSV")
    args = ap.parse_args(argv)

    if not args.log.is_file():
        print(f"=== depth_gate.py -- log not found: {args.log} ===")
        print("Nothing captured yet. Arm the probe and take one instrumented cast -- see "
              "m0/CAST-PROTOCOL.md (this directory) for the full protocol, or PROBE.md sec 2 for the "
              "general arming steps. Required ini block:\n")
        print(REQUIRED_INI_ADD)
        return 0

    # AUTO-ARCHIVE THE LIVE LOG BEFORE TOUCHING IT (the archive-capture-logs-immediately rule,
    # 2026-07-23: the 5-cast M0 dataset was destroyed by a concurrent relaunch before anyone
    # snapshotted it -- the probe truncates with FileMode.Create on every launch, and the install
    # is shared mutable state across concurrent sessions). Reading the LIVE path snapshots it to
    # SCRATCH keyed by the log's own mtime (re-runs against an unchanged log reuse the snapshot),
    # then analyzes the SNAPSHOT, so the printed report cites a path that survives the next launch.
    if args.log == DEFAULT_LOG:
        import shutil, time as _time
        arch_dir = Path(r"C:\gd\SCRATCH\summon-transplant\logs")
        stamp = _time.strftime("%Y%m%d-%H%M%S", _time.localtime(args.log.stat().st_mtime))
        arch = arch_dir / f"sfxmeshprobe.{stamp}.log"
        try:
            if not arch.is_file():
                arch_dir.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(args.log, arch)
                print(f"[archived live log -> {arch}]")
            else:
                print(f"[live log already archived: {arch}]")
            args.log = arch
        except OSError as exc:  # never let archiving block the analysis
            print(f"[WARN: could not archive the live log ({exc}) -- analyzing the live file]")

    counts, psxcam, bones = scan_pass1(args.log)

    if counts.get("PRIM", 0) == 0:
        # THE graceful-degrade path this round's log actually takes -- proven by running this script
        # against the live install's current sfxmeshprobe.log (see this round's findings for the
        # transcript). Never crashes, never demands data that isn't captured, always exits 0.
        print_graceful_degrade(args.log, counts)
        return 0

    creature = build_creature_frames(psxcam, bones)
    if not creature:
        print("=== depth_gate.py -- PRIM rows exist, but no frame has BOTH a PSXCAM and a BONES row ===")
        print("(every creature-AABB reprojection needs both, same frame). Check that CaptureModels=1 "
              "AND ModelsBoneCount>0 were armed for this capture -- see m0/CAST-PROTOCOL.md.")
        print(f"row tallies: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
        return 0

    offset_x, n_calib = self_calibrate_offset_x(args.log, creature)
    per_frame, phases, otz_sample = analyze_prims(args.log, creature, offset_x)
    print_full_report(counts, creature, per_frame, phases, otz_sample, offset_x, n_calib, args.verbose)

    if args.csv is not None:
        write_csv(args.csv, creature, per_frame)
        print(f"\nper-frame CSV written: {args.csv}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
