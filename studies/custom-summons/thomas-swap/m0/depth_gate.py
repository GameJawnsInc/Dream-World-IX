"""depth_gate.py -- M0 item (d): the effect-prim / creature depth-interleave gate (CALIBRATED).

WHAT THIS ANSWERS (TRANSPLANT.md sec 1.2/1.5/2.4/4-P4): on frames where the creature is actually
drawn and framed, is it depth-INTERLEAVED with the native effect primitives -- i.e. do effect prims
occupy the creature's own screen region at a NEARER depth (and/or straddle it front-and-behind), such
that the HYBRID transplant's WHOLESALE front/behind sort would visibly misorder content that should
wrap the body? If yes on a sustained fraction of framed frames, that summon needs the reserved NATIVE
(T2) path; if effects are cleanly one-sided (all behind) or absent from the silhouette, the hybrid
suffices. This is the only fidelity axis where the native slot beats the hybrid (TRANSPLANT sec 1.1).

=====================================================================================================
THE CALIBRATION (2026-07-24) -- this file WAS a placeholder that produced a saturated, non-
discriminating table (overlap==w/prims, near~=100%, rates >100%). It has been re-derived from one
full instrumented Bahamut cast (bench 30300, effect 227, frames 11..561, body UNHIDDEN --calibrate).
The findings, the discriminator, its validation, the constants, and the verdict live in DEPTH-GATE.md
(this directory). The four defects that saturated the old table, and their fixes:

  (1) STALENESS. After the creature stops drawing (~f413 for this cast) the summon slot's BONES AABB
      goes to arena garbage (bands in the BILLIONS). The old gate treated those frames as
      creature-present and reprojected garbage boxes. FIX: a frame is "creature present" only if the
      summon MODEL(kind=S) row is non-stale -- bones32 != 0 AND the composed world translation is
      within 5000 units of the draw anchor on every axis (flight_v9_solve.py's own reliability test).
      For this cast that is frames 82..415, matching the body-key MESH window 82..417 exactly. The
      body FT3 prim count validates it: 1008 at f410 -> 158 -> 7 -> 0 by f413.

  (2) BODY-PRIM POLLUTION. A --calibrate cast leaves the creature's OWN body visible, so its own
      primitives are in the PRIM lane, land inside its own silhouette at its own depth, and the old
      gate counted them as "nearer-overlapping effect" (~100% near, every phase). FIX -- a body
      discriminator that needs NO per-prim key attribution (PRIM rows carry no key, and the prim
      stream is one depth-sorted ordering table with body + effects interleaved by depth, so index
      ranges cannot be attributed to meshes): EXCLUDE the creature's whole reprojected depth BAND
      [zmin,zmax] (the 8 BONES-AABB corners) padded by a margin calibrated to contain the body. An
      effect prim is any inside-silhouette prim OUTSIDE that band. The decisive signal is then
      body-exclusion-robust BY CONSTRUCTION: FRONT effects (nearer than the whole body) and BEHIND
      effects (farther than the whole body) are, by definition, not body prims. "STRADDLE" (effects
      present on BOTH sides) = the creature is embedded in the effect depth field = NO wholesale sort
      can be right. Validation that the band tracks the real body: the in-band (body) population
      vanishes exactly at f413 when the body stops drawing (DEPTH-GATE.md sec 3).

  (3) PLACEHOLDER CONSTANTS. AABB_PAD_PX and the depth margin were guesses; the margin was ABSOLUTE
      (50) while raw otz spans ~230 (near) to ~35000 (far) across the 0.02->3.0x scale sweep, so a
      fixed 50 is meaningless at distance. FIX: AABB_PAD_PX = 8 (CAMERA-MATCH.md radial p95 7.65px);
      the depth margin is PROPORTIONAL to the frame's centroid depth (DEPTH_EPS_FRAC = 0.055, the p90
      of how far the body's own FT3 prims poke beyond the bone-cloud band, as a fraction of centroid
      depth) with an absolute floor DEPTH_EPS_FLOOR = 64 (otz is quantized to ~16; distinct-value
      spacing p90 = 48).

  (4) >100% RATES. The old numerator (frames_with_near_overlap) was counted on ALL creature-present
      frames while the denominator (frames_framed) counted only framed ones -> rates like 117/187/700%.
      FIX: every rate uses frames_framed as denominator and every numerator is gated on framed.

=====================================================================================================
THE OTZ POLARITY -- READ BEFORE TRUSTING ANY NUMBER (unchanged, still load-bearing)
=====================================================================================================

Two DIFFERENT quantities with OPPOSITE sign conventions:

  (1) THE RAW NATIVE OTZ -- the PSX ordering-table depth key, `ref Int32 otz` of the native
      SFX_GetPrim (Global/SFX/SFX.cs:753,827-830). Chased through source:
        * SFXRender.cs:83  `SFXMesh.GzDepth = -num;`  (num == raw native otz)
        * SFXMesh vertex Z is set to GzDepth for every primitive type (SFXMesh.cs ~:346).
        * SFXRender.Render() forces `camera.worldToCameraMatrix = Matrix4x4.identity` for the whole
          SFX draw walk (:127-135), so a mesh's own Z is fed as EYE-SPACE Z into the projection.
        * The projection is the textbook off-center frustum (PsxCamera.cs:122-149): eye looks down
          -Z, eye Z in [-far,-near], so Z near 0 == NEAREST, Z very negative == FARTHEST.
      => mesh Z = -otz_native; for that to sit in the near/far band, SMALL native otz == NEAR.
          >>> SMALLER raw native otz  =  NEARER the camera <<<
      (Matches PSX GTE: OT bucket from clamped SZ3, larger SZ3 == farther. FORMAT.md sec 1.2.)

  (2) THE LOGGED `PRIM` "otz" COLUMN (6th data field) is SFXMesh.GzDepth == -otz_native
      (SfxMeshProbe.cs:793-795, SFXRender.cs:83). Already negated once in the log:
          >>> LARGER (more positive) logged otz  =  NEARER ;  SMALLER (more negative)  =  FARTHER <<<

  This file recovers the raw native value FIRST (`raw = -otz_logged`, `_raw_native_otz`) and reasons
  ONLY in "raw native otz, smaller = nearer" terms thereafter.

  UNCONFIRMED (flagged, not blocking -- and it is the crux of whether NATIVE-NEEDED bites in-game):
  whether the Unity material assigned to these SFX draws enables hardware ZTest against our hidden-
  creature's Unity depth (per-pixel interleave) or composites by pure draw order (wholesale). The
  shaders are compiled Unity assets, not in this source tree. IF the effect Z (raw GzDepth, PSX
  units) and our hybrid mesh's Unity eye-space Z happened to share a ruler through the common
  projectionMatrix (CALIBRATION.md pins the PSX->Unity world scale at ~1), the Z-buffer could
  interleave them correctly and the hybrid would be fine DESPITE the interleaved content. TRANSPLANT
  sec 1.5 reads the source as a wholesale sort (identity view for the effects, Unity view for our
  mesh -> different Z origins). THIS GATE proves only that the CONTENT is interleaved (it is,
  pervasively, for Bahamut); whether the hybrid's compositing survives it is exactly what M1a's cast
  must confirm by eye. See DEPTH-GATE.md sec 6-7.

=====================================================================================================
COORDINATE-SPACE / WIDESCREEN (self-calibrated, unchanged mechanism)
=====================================================================================================

The creature's screen AABB is computed in RAW PSX screen space (center 160,120) from the native GTE
identity (reused from flight_v9_solve.py). A logged PRIM row's x,y are vertex0 + SFXMeshBase.drOffsetX/Y,
and drOffsetX = CalculateWidescreenOffsetX() is nonzero on a widescreen install. analyze() self-
calibrates a best-effort drOffsetX (median x-delta of framed, depth-and-y-matched creature-body prims)
and shifts PRIM x by it before the box test; below MIN_CALIB_SAMPLES matches it falls back to 0 with an
explicit UNCALIBRATED warning. (On a body-visible calibrate cast there are thousands of body prims at
the centroid depth+y, so the estimate is robust.)

=====================================================================================================
USAGE
=====================================================================================================

    py depth_gate.py                      # analyze the live install's log (auto-archives first)
    py depth_gate.py --log PATH           # analyze an arbitrary log (e.g. an archived snapshot)
    py depth_gate.py --verbose            # also print the full per-frame table
    py depth_gate.py --csv OUT.csv        # dump per-frame stats to CSV

Exit code is always 0 on a successful run (incl. graceful-degrade) -- an offline analysis tool, never
a build gate; non-zero is reserved for a genuinely malformed --log path argument.
"""
from __future__ import annotations

import argparse
import csv as csv_module
import statistics
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# --------------------------------------------------------------------------------------------------
# Constants (CALIBRATED 2026-07-24 -- derivations in DEPTH-GATE.md sec 4)
# --------------------------------------------------------------------------------------------------

DEFAULT_LOG = Path(
    r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\sfxmeshprobe.log"
)

# The ini block this script's happy path needs (printed in the graceful-degrade message).
REQUIRED_INI_ADD = (
    "[SfxProbe]\n"
    "Enabled = 1          ; already armed -- KEEP\n"
    "CaptureRoot = 1      ; already armed -- KEEP\n"
    "CaptureModels = 1    ; already armed -- KEEP (PSXCAM + BONES + MODEL need this)\n"
    "ModelsActiveOnly = 1 ; already armed -- KEEP\n"
    "ModelsCap = 120000   ; already armed -- KEEP\n"
    "ModelsBoneCount = 93 ; already armed -- KEEP (ef227/Bahamut's node count)\n"
    "CapturePrims = 1     ; ADD -- this is the one this gate needs\n"
    "PrimSummary = 0      ; ADD (or omit -- 0 is default) -- PRIMSUM rows have no x,y/otz, unusable here\n"
    "PrimCap = 3000000    ; ADD, raised from the 200000 default -- see CAST-PROTOCOL.md sec 3\n"
)

# Padding (raw PSX screen px) around the creature's reprojected corner-hull AABB. CAMERA-MATCH.md
# measured the native-GTE reprojection residual at p95 2.96px horizontal / 7.16px vertical / 7.65px
# radial (320x240 frame); 8 covers the radial p95.
AABB_PAD_PX = 8.0

# The body depth-band margin, PROPORTIONAL to the frame's centroid depth (raw native otz scales with
# distance across the 0.02->3.0x sweep, so a fixed absolute margin is meaningless). DEPTH_EPS_FRAC is
# the p90 of how far the body's own FT3 prims poke beyond the reprojected bone-cloud band, expressed
# as a fraction of centroid depth (body overshoot p50=0, p90~=0.055, p99~=0.19). A prim is "clearly
# nearer/farther than the whole body" only beyond this margin -> body-prim leakage into FRONT/BEHIND
# stays <10% and is symmetric noise, never a straddle-faker on its own (MIN_SIDE_PRIMS guards that).
DEPTH_EPS_FRAC = 0.055
# Absolute floor for the margin (otz is quantized to ~16; distinct-value spacing p90 = 48) -- guards
# the rare very-near frame where 0.055*depth would underflow the quantization noise.
DEPTH_EPS_FLOOR = 64.0

# A "side" (front or behind) counts only if it holds at least this many effect prims -- one stray
# body-margin prim leaking past the depth margin must not, by itself, manufacture a straddle. The real
# effect layers hold tens-to-hundreds of prims per side (DEPTH-GATE.md sec 5), so this is well clear.
MIN_SIDE_PRIMS = 3

# "Framed" gate: creature centroid NDC (native 320x240, OFX/OFY=160/120) within this many half-screens
# of center. Reuses flight_v9_solve.py's NDC_CLAMP=1.50 (a generous "on/near screen" gate).
FRAMED_NDC_MARGIN = 1.50

# Staleness (creature-present) test on the summon MODEL(kind=S) row -- flight_v9_solve.py's own test.
STALE_ANCHOR_TOL = 5000

# Self-calibration of the widescreen X offset.
CALIB_DEPTH_TOL_FRAC = 0.10
CALIB_Y_TOL_PX = 8.0
MIN_CALIB_SAMPLES = 8

# Verdict thresholds (TRANSPLANT sec 4-P4). A phase is NATIVE-NEEDED if the creature is embedded in the
# effect field on a sustained fraction of its framed frames -- either STRADDLED (effects both nearer
# AND farther, no wholesale order is right) or wearing sustained NEARER effects (the wholesale sort
# would push a foreground effect behind our opaque mesh -> visible). BEHIND-only is HYBRID-OK (sort
# them all behind). Print the raw rates always so a human can override. Sensitivity in DEPTH-GATE.md.
NATIVE_STRADDLE_RATE = 0.15
NATIVE_FRONT_RATE = 0.33
BORDERLINE_FRONT_RATE = 0.05
MIN_FRAMED_FOR_VERDICT = 5

# The cast's piece-boundary table (PROBE.md sec 8 -- the same Bahamut Cinema this log comes from).
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
    (417, 10 ** 9, "post-body / fire-column tail (creature undrawn -- excluded by staleness)"),
]


def _phase_for(frame: int) -> str:
    for lo, hi, label in PHASES:
        if lo <= frame < hi:
            return label
    return PHASES[-1][2]


def _sat16(v: int) -> int:
    return -32768 if v < -32768 else (32767 if v > 32767 else v)


def _project_point(R: List[int], T: List[int], H: int, v: Tuple[float, float, float]) -> Optional[Tuple[float, float, float]]:
    """Zero-free-parameter native GTE reprojection (FORMAT.md sec 1.2/1.4/5.4, identical to
    flight_v9_solve.py's parse_native_path): world point -> (screen_x, screen_y, raw_view_z). Returns
    None if behind the camera (pz<=0) or H==0. pz is the raw view-space Z (SZ3-analog, larger==farther),
    the SAME quantity a PRIM row's recovered raw native otz is compared against."""
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
    """Recover raw native otz from the logged 6th field (SFXRender.cs:83 negates once; undo here, ONE
    place, so every comparison below reasons in 'smaller raw = nearer' terms)."""
    return -otz_logged


# --------------------------------------------------------------------------------------------------
# Log parsing
# --------------------------------------------------------------------------------------------------

class CreatureFrame:
    __slots__ = ("frame", "aabb", "zmin", "zmax", "depth", "framed", "ndc_x", "ndc_y")

    def __init__(self, frame: int, aabb: Tuple[float, float, float, float], zmin: float, zmax: float,
                 depth: float, framed: bool, ndc_x: float, ndc_y: float) -> None:
        self.frame = frame
        self.aabb = aabb          # (xmin, xmax, ymin, ymax), padded
        self.zmin = zmin          # nearest reprojected BONES-AABB corner depth (raw native otz)
        self.zmax = zmax          # farthest ditto
        self.depth = depth        # centroid raw view-Z
        self.framed = framed
        self.ndc_x = ndc_x
        self.ndc_y = ndc_y

    def margin(self) -> float:
        return max(DEPTH_EPS_FLOOR, DEPTH_EPS_FRAC * self.depth)


def scan_pass1(path: Path):
    """One streaming pass: tag counts (graceful-degrade decision) + PSXCAM + BONES + summon MODEL(S).
    All three are O(1-2 rows)/frame -- cheap to hold in full."""
    counts: Dict[str, int] = {}
    psxcam: Dict[int, Tuple[List[int], List[int], int]] = {}
    bones: Dict[int, dict] = {}
    smodel: Dict[int, Tuple[str, int, int, int, int, int, int]] = {}
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line or line[0] == "#":
                continue
            p = line.rstrip("\n").split(",")
            tag = p[0]
            counts[tag] = counts.get(tag, 0) + 1
            try:
                if tag == "PSXCAM":
                    # PSXCAM,effectId,frame,m00..m22(9),tx,ty,tz,ofx,ofy,h,psxPtr
                    frame = int(p[2])
                    psxcam[frame] = ([int(x) for x in p[3:12]], [int(x) for x in p[12:15]], int(p[17]))
                elif tag == "BONES":
                    # BONES,effectId,frame,n,cx,cy,cz,minX,minY,minZ,maxX,maxY,maxZ
                    frame = int(p[2])
                    bones[frame] = dict(cx=float(p[4]), cy=float(p[5]), cz=float(p[6]),
                                        minX=float(p[7]), minY=float(p[8]), minZ=float(p[9]),
                                        maxX=float(p[10]), maxY=float(p[11]), maxZ=float(p[12]))
                elif tag == "MODEL" and len(p) > 26 and p[3] == "S":
                    # MODEL,effectId,frame,kind,slot,active,hasMotion,hasParent,aux0,aux1,aux2,
                    #   ax,ay,az,wx,wy,wz,m00..m22,bones32   -- bones32 at p[26]
                    frame = int(p[2])
                    smodel[frame] = (p[26], int(p[14]), int(p[15]), int(p[16]),
                                     int(p[11]), int(p[12]), int(p[13]))
            except (ValueError, IndexError):
                continue
    return counts, psxcam, bones, smodel


def reliable_frames(smodel: Dict[int, Tuple[str, int, int, int, int, int, int]]) -> set:
    """Creature-present frames: the summon slot drew AND its composed world transform is sane
    (flight_v9_solve.py's test -- bones32 != 0 and |world - anchor| <= STALE_ANCHOR_TOL every axis).
    Excludes the arena-garbage tail after the body stops drawing."""
    out = set()
    for f, (b32, wx, wy, wz, ax, ay, az) in smodel.items():
        if b32 == "00000000":
            continue
        if abs(wx - ax) > STALE_ANCHOR_TOL or abs(wy - ay) > STALE_ANCHOR_TOL or abs(wz - az) > STALE_ANCHOR_TOL:
            continue
        out.add(f)
    return out


def build_creature_frames(psxcam, bones, reliable: set) -> Dict[int, CreatureFrame]:
    """Per RELIABLE frame with both PSXCAM and BONES: the creature's padded screen AABB + reprojected
    depth band [zmin,zmax] + centroid depth + framed flag."""
    out: Dict[int, CreatureFrame] = {}
    for frame in reliable:
        cam = psxcam.get(frame)
        b = bones.get(frame)
        if cam is None or b is None:
            continue
        R, T, H = cam
        corners = [(x, y, z)
                   for x in (b["minX"], b["maxX"])
                   for y in (b["minY"], b["maxY"])
                   for z in (b["minZ"], b["maxZ"])]
        sxs: List[float] = []
        sys_: List[float] = []
        pzs: List[float] = []
        for c in corners:
            proj = _project_point(R, T, H, c)
            if proj is not None:
                sxs.append(proj[0]); sys_.append(proj[1]); pzs.append(proj[2])
        if not sxs:
            continue
        centroid = _project_point(R, T, H, (b["cx"], b["cy"], b["cz"]))
        if centroid is None:
            continue
        csx, csy, cpz = centroid
        aabb = (min(sxs) - AABB_PAD_PX, max(sxs) + AABB_PAD_PX,
                min(sys_) - AABB_PAD_PX, max(sys_) + AABB_PAD_PX)
        ndc_x = (csx - 160.0) / 160.0
        ndc_y = (120.0 - csy) / 120.0
        framed = abs(ndc_x) <= FRAMED_NDC_MARGIN and abs(ndc_y) <= FRAMED_NDC_MARGIN
        out[frame] = CreatureFrame(frame, aabb, min(pzs), max(pzs), cpz, framed, ndc_x, ndc_y)
    return out


def self_calibrate_offset_x(path: Path, creature: Dict[int, CreatureFrame]) -> Tuple[float, int]:
    """Best-effort widescreen drOffsetX: median x-delta of framed, depth-matched, y-close creature-body
    prims. Returns (estimate, n_samples); < MIN_CALIB_SAMPLES -> caller treats as 0/UNCALIBRATED."""
    deltas: List[float] = []
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line.startswith("PRIM,"):
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
                raw = _raw_native_otz(float(p[6]))
                x = float(p[7]); y = float(p[8])
            except (ValueError, IndexError):
                continue
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
    __slots__ = ("frames_present", "frames_framed", "frames_front", "frames_behind",
                 "frames_straddle", "frames_inband", "front_counts", "behind_counts", "inband_counts")

    def __init__(self) -> None:
        self.frames_present = 0
        self.frames_framed = 0
        self.frames_front = 0      # framed frames with >= MIN_SIDE_PRIMS effect prims NEARER than body
        self.frames_behind = 0     # ditto FARTHER than body
        self.frames_straddle = 0   # both (creature embedded -> no wholesale order is right)
        self.frames_inband = 0     # frames with any prim inside the body depth band (body + unresolved wrap)
        self.front_counts: List[int] = []
        self.behind_counts: List[int] = []
        self.inband_counts: List[int] = []


def analyze_prims(path: Path, creature: Dict[int, CreatureFrame], offset_x: float):
    """Second streaming pass: per (framed) frame classify inside-silhouette prims as FRONT / IN-BAND /
    BEHIND relative to the creature's own reprojected depth band (padded by the proportional margin);
    roll up per phase. FRONT/BEHIND are effects by construction (outside the body's own depth extent);
    IN-BAND is body + any unresolvable in-volume wrap (reported, does NOT drive the verdict)."""
    per_frame: Dict[int, List[int]] = {}       # frame -> [n_front, n_inband, n_behind]
    phases: Dict[str, PhaseStats] = {label: PhaseStats() for _, _, label in PHASES}
    otz_sample: List[float] = []
    OTZ_SAMPLE_CAP = 20000
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line.startswith("PRIM,"):
                continue
            p = line.rstrip("\n").split(",")
            try:
                frame = int(p[2])
                raw = _raw_native_otz(float(p[6]))
                x = float(p[7]); y = float(p[8])
            except (ValueError, IndexError):
                continue
            cf = creature.get(frame)
            if cf is None or not cf.framed:
                continue
            xmin, xmax, ymin, ymax = cf.aabb
            xc = x - offset_x
            if not (xmin <= xc <= xmax and ymin <= y <= ymax):
                continue
            if len(otz_sample) < OTZ_SAMPLE_CAP:
                otz_sample.append(raw)
            m = cf.margin()
            row = per_frame.setdefault(frame, [0, 0, 0])
            if raw < cf.zmin - m:
                row[0] += 1      # FRONT: nearer than the whole body
            elif raw > cf.zmax + m:
                row[2] += 1      # BEHIND: farther than the whole body
            else:
                row[1] += 1      # IN-BAND: at the body's depth
    for frame, cf in creature.items():
        if not cf.framed:
            continue
        ps = phases[_phase_for(frame)]
        ps.frames_present += 1
        ps.frames_framed += 1
        n_front, n_inband, n_behind = per_frame.get(frame, [0, 0, 0])
        front = n_front >= MIN_SIDE_PRIMS
        behind = n_behind >= MIN_SIDE_PRIMS
        if front:
            ps.frames_front += 1
        if behind:
            ps.frames_behind += 1
        if front and behind:
            ps.frames_straddle += 1
        if n_inband:
            ps.frames_inband += 1
        ps.front_counts.append(n_front)
        ps.behind_counts.append(n_behind)
        ps.inband_counts.append(n_inband)
    return {f: tuple(v) for f, v in per_frame.items()}, phases, otz_sample


def verdict_for_phase(ps: PhaseStats) -> str:
    if ps.frames_framed < MIN_FRAMED_FOR_VERDICT:
        return "INSUFFICIENT-DATA"
    straddle = ps.frames_straddle / ps.frames_framed
    front = ps.frames_front / ps.frames_framed
    if straddle > NATIVE_STRADDLE_RATE or front > NATIVE_FRONT_RATE:
        return "NATIVE-NEEDED"
    if front > BORDERLINE_FRONT_RATE or straddle > 0.0:
        return "BORDERLINE"
    return "HYBRID-OK"


_SEVERITY = {"NATIVE-NEEDED": 3, "BORDERLINE": 2, "HYBRID-OK": 1, "INSUFFICIENT-DATA": 0}


def overall_verdict(phase_verdicts: Dict[str, str]) -> str:
    real = [v for v in phase_verdicts.values() if v != "INSUFFICIENT-DATA"]
    if not real:
        return "INSUFFICIENT-DATA"
    worst = max(real, key=lambda v: _SEVERITY[v])
    n_native = sum(1 for v in real if v == "NATIVE-NEEDED")
    if worst == "NATIVE-NEEDED" and 0 < n_native < len(real):
        return "MIXED (NATIVE-NEEDED in some phases -- see table)"
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
    if counts.get("MODEL", 0) == 0:
        missing.append("MODEL (needs [SfxProbe] CaptureModels=1) -- the staleness/creature-present filter")
    if counts.get("PRIM", 0) == 0:
        missing.append("PRIM (needs [SfxProbe] CapturePrims=1) -- the primitives this gate scans")
    print("\nmissing row types this gate needs: " + (", ".join(missing) if missing else "(none -- but"
          " something else prevented analysis; check the log for parse errors)"))
    print("\nTo unblock: archive this log, then arm the FULL block below in Memoria.ini, relaunch, cast")
    print("Bahamut Cinema once, quit. Full protocol: m0/CAST-PROTOCOL.md (this directory).\n")
    print(REQUIRED_INI_ADD)


def _med(a: List[int]) -> float:
    return statistics.median(a) if a else 0.0


def print_full_report(counts, creature, per_frame, phases, otz_sample, offset_x, n_calib, verbose):
    print("=== depth_gate.py -- THE DEPTH GATE (calibrated) ===")
    print("row tallies: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    print(f"creature-present frames (non-stale summon slot, PSXCAM+BONES): {len(creature)}")
    if creature:
        print(f"  frame window: {min(creature)}..{max(creature)}")
    n_framed = sum(1 for cf in creature.values() if cf.framed)
    print(f"  of which 'framed' (|ndc|<={FRAMED_NDC_MARGIN}): {n_framed}")
    calib_note = "RELIABLE" if n_calib >= MIN_CALIB_SAMPLES else "UNCALIBRATED (too few samples -- treated as 0)"
    print(f"self-calibrated widescreen drOffsetX: {offset_x:+.2f} px (n={n_calib} matched -- {calib_note})")
    if otz_sample:
        otz_sample.sort()
        n = len(otz_sample)

        def pct(q: float) -> float:
            return otz_sample[min(n - 1, int(q * n))]

        print(f"raw native otz of inside-silhouette prims (sampled, n={n}): "
              f"p5={pct(.05):.0f} p50={pct(.5):.0f} p95={pct(.95):.0f} min={otz_sample[0]:.0f} max={otz_sample[-1]:.0f} "
              f"(smaller=nearer)")
    print(f"\nmargin: max({DEPTH_EPS_FLOOR:.0f}, {DEPTH_EPS_FRAC:.3f}*centroid_depth); AABB pad {AABB_PAD_PX:.0f}px; "
          f"a side counts at >= {MIN_SIDE_PRIMS} prims")
    print(f"\n{'phase':52s} {'frmd':>4} {'front':>5} {'strad':>5} {'behind':>6} {'medFr':>5} {'medBh':>5} "
          f"{'medIn':>5}  verdict")
    phase_verdicts: Dict[str, str] = {}
    for lo, hi, label in PHASES:
        ps = phases[label]
        v = verdict_for_phase(ps)
        phase_verdicts[label] = v
        if ps.frames_framed == 0 and ps.frames_present == 0:
            continue
        fr = ps.frames_front / ps.frames_framed if ps.frames_framed else 0.0
        st = ps.frames_straddle / ps.frames_framed if ps.frames_framed else 0.0
        bh = ps.frames_behind / ps.frames_framed if ps.frames_framed else 0.0
        short = label.split(" (")[0]
        print(f"{short:52s} {ps.frames_framed:4d} {fr:5.0%} {st:5.0%} {bh:6.0%} "
              f"{_med(ps.front_counts):5.0f} {_med(ps.behind_counts):5.0f} {_med(ps.inband_counts):5.0f}  {v}")

    if verbose:
        print("\n=== per-frame (--verbose): frame phase framed n_front n_inband n_behind ===")
        for frame in sorted(creature):
            cf = creature[frame]
            nf, ni, nb = per_frame.get(frame, (0, 0, 0))
            print(f"{frame:5d} {_phase_for(frame).split(' (')[0]:40s} {str(cf.framed):>5} {nf:6d} {ni:7d} {nb:6d}")

    ov = overall_verdict(phase_verdicts)
    print(f"\nVERDICT: {ov}")
    print("  FRONT = effect prims NEARER than the whole body inside its silhouette (the wholesale sort "
          "would push a\n  foreground effect BEHIND our opaque mesh). STRADDLE = effects both nearer AND "
          "farther (NO wholesale\n  order is right). BEHIND-only is HYBRID-OK. IN-BAND (medIn) = body prims + "
          "any in-volume wrap -- NOT\n  separable on a body-visible cast, reported not scored. Thresholds "
          f"(PLACEHOLDER-tunable): NATIVE if\n  straddle>{NATIVE_STRADDLE_RATE:.0%} or front>{NATIVE_FRONT_RATE:.0%}. "
          "Sensitivity + the in-game confirmation M1a owes: DEPTH-GATE.md.")
    return phase_verdicts


def write_csv(csv_path: Path, creature: Dict[int, CreatureFrame], per_frame) -> None:
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        w = csv_module.writer(fh)
        w.writerow(["frame", "phase", "framed", "ndc_x", "ndc_y", "creature_depth", "zmin", "zmax",
                    "margin", "n_front", "n_inband", "n_behind"])
        for frame in sorted(creature):
            cf = creature[frame]
            nf, ni, nb = per_frame.get(frame, (0, 0, 0))
            w.writerow([frame, _phase_for(frame).split(" (")[0], cf.framed, f"{cf.ndc_x:.4f}",
                        f"{cf.ndc_y:.4f}", f"{cf.depth:.1f}", f"{cf.zmin:.1f}", f"{cf.zmax:.1f}",
                        f"{cf.margin():.1f}", nf, ni, nb])


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
              "m0/CAST-PROTOCOL.md for the full protocol. Required ini block:\n")
        print(REQUIRED_INI_ADD)
        return 0

    # AUTO-ARCHIVE the live log before touching it (the archive-capture-logs-immediately rule: the
    # probe truncates with FileMode.Create on every launch, and the install is shared mutable state).
    # Snapshot to SCRATCH keyed by the log's own mtime, then analyze the SNAPSHOT.
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
        except OSError as exc:
            print(f"[WARN: could not archive the live log ({exc}) -- analyzing the live file]")

    counts, psxcam, bones, smodel = scan_pass1(args.log)

    if counts.get("PRIM", 0) == 0:
        print_graceful_degrade(args.log, counts)
        return 0

    reliable = reliable_frames(smodel)
    creature = build_creature_frames(psxcam, bones, reliable)
    if not creature:
        print("=== depth_gate.py -- PRIM rows exist, but no non-stale frame has BOTH PSXCAM and BONES ===")
        print("(every creature-AABB reprojection needs both, same frame, on a frame the summon slot is "
              "non-stale). Check CaptureModels=1 AND ModelsBoneCount>0 -- see m0/CAST-PROTOCOL.md.")
        print("row tallies: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
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
