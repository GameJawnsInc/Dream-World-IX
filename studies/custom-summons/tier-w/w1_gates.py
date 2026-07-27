r"""TIER W rung 1 -- the gate runner.  `py w1_gates.py` prints W1a..W1e with numbers and PASS/FAIL.

W1a  NO REGRESSION: tier-r's r1/r2/r3 gate runners and all four test modules still pass, AND the
     kit's own battle-camera tests still pass -- because this rung reuses ``camera_codec`` UNCHANGED
W1b  THE ROUND-TRIP (the camera recon): decode -> re-encode every summon camera in the corpus and
     compare bytes.  N/N with the count, or an itemised failure list with root causes
W1c  THE ef227 TWO-CLOCKS REPRODUCTION: the merged timeline puts the three projection-distance
     changes 1, 1 and 0 ticks from a program phase boundary, from data+code only.  The archived
     capture is quoted afterwards as CONFIRMATION and is never an input to the derivation
W1d  THE CORPUS CENSUS: how many effects play cameras, how many shots, shot/keyframe distributions,
     which blocks are shared
W1e  PROVENANCE: no stock byte run from the corpus appears in any committable tier-W file, decoded
     dumps land under SCRATCH only, and the report's stock-value quote budget is respected

Reads the extracted corpus under ``C:\gd\SCRATCH\summon-format``.  Prints only structure -- names,
offsets, counts, sizes and frame numbers.
"""
from __future__ import annotations

import ast
import collections
import glob
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import summon_camera as W                                     # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
_STUDY = os.path.dirname(_HERE)
_REPO = os.path.dirname(os.path.dirname(_STUDY))
TIER_R = os.path.join(_STUDY, "tier-r")
KIT = os.path.join(_REPO, "ff9mapkit")
REPORT = os.path.join(_HERE, "W1-READOUT.md")
EF227 = 227

#: the report may quote stock VALUES (sizes, indices, H distances) -- never stock BYTES.  Budget per
#: the tier's provenance rule; W1e counts them.
QUOTE_BUDGET = 10

#: the committable files this rung adds; W1e scans them for stock byte runs.
#:
#: REPOINTED BY THE PROMOTION.  ``summon_camera.py`` is now a SHIM over
#: ``ff9mapkit/ff9mapkit/summons/camera.py`` -- the reader itself lives in the kit.  Scanning only the
#: shim would find zero byte literals and report a green provenance gate over ~40 lines of aliasing
#: while the 590 lines that actually decode stock containers went unexamined: a gate that passes
#: because it stopped looking.  Both are listed, so the scan follows the code.
#:
#: An entry containing "/" is REPO-relative; a bare name is relative to this directory.
COMMITTABLE = ("summon_camera.py", "test_summon_camera.py", "w1_gates.py", "W1-READOUT.md",
               "ff9mapkit/ff9mapkit/summons/camera.py")


def _committable_path(name: str) -> str:
    """Where a COMMITTABLE entry lives.  A missing one still FAILS the gate (see W1e)."""
    return os.path.join(_REPO, *name.split("/")) if "/" in name else os.path.join(_HERE, name)

RESULTS = []
FINDINGS = []


def gate(name: str, ok: bool, *lines: str) -> bool:
    RESULTS.append((name, ok))
    print("\n%s %s  %s" % ("[PASS]" if ok else "[FAIL]", name, "-" * max(2, 58 - len(name))))
    for ln in lines:
        print("   " + ln)
    return ok


def finding(text: str) -> None:
    FINDINGS.append(text)


def _pytest(path: str, cwd: str, extra=()) -> tuple:
    p = subprocess.run([sys.executable, "-m", "pytest", path, "-q", "--no-header", *extra],
                       capture_output=True, text=True, cwd=cwd)
    line = next((l for l in reversed(p.stdout.splitlines())
                 if " passed" in l or " failed" in l or " error" in l), "?")
    m = re.search(r"(\d+) passed", line)
    return p.returncode, int(m.group(1)) if m else 0, line.strip()


# --------------------------------------------------------------------------- W1a
def w1a_no_regression():
    lines, ok, total = [], True, 0
    for runner, want in (("r1_gates.py", "8/8"), ("r2_gates.py", "6/6"), ("r3_gates.py", "5/5")):
        p = subprocess.run([sys.executable, os.path.join(TIER_R, runner)],
                           capture_output=True, text=True, cwd=TIER_R)
        tail = [l for l in p.stdout.splitlines() if "gates pass" in l]
        got = tail[-1].strip() if tail else "(none)"
        good = p.returncode == 0 and got.startswith(want)
        ok = ok and good
        lines.append("%-12s exit=%d  %-18s expected %s  %s"
                     % (runner, p.returncode, got, want, "OK" if good else "MISMATCH"))
    lines.append("")
    for mod, cwd in (("test_tier_r_disasm.py", TIER_R), ("test_tier_r_annot.py", TIER_R),
                     ("test_summon_inspect.py", TIER_R), ("test_summon_camera.py", _HERE)):
        rc, n, line = _pytest(mod, cwd)
        total += n
        ok = ok and rc == 0
        lines.append("%-26s exit=%d  %s" % (mod, rc, line))
    lines.append("%d tests pass across tier-r + tier-w (tier-r's own 142 are unchanged)" % total)
    lines.append("")
    # the kit's own battle-camera tests -- W1 owns no camera GRAMMAR, so these must be green
    for mod in ("tests/test_battle.py", "tests/test_battle_scene_codec.py"):
        rc, n, line = _pytest(mod, KIT, extra=("-k", "camera"))
        ok = ok and rc == 0
        lines.append("kit %-30s exit=%d  %s (-k camera)" % (mod, rc, line))
    # REPOINTED BY THE PROMOTION.  The reader W1 built is now `summons/camera.py` and it decodes
    # through `summons/container.py`; `camera_codec.py` gained the public aliases both call.  All
    # three are listed so an uncommitted edit to the code this rung's verdict rests on is caught --
    # naming only the file the reader USED to live beside would leave the reader itself unwatched.
    _READERS = ("ff9mapkit/ff9mapkit/battle/camera_codec.py",
                "ff9mapkit/ff9mapkit/summons/camera.py",
                "ff9mapkit/ff9mapkit/summons/container.py")
    dirty = subprocess.run(["git", "status", "--porcelain", "--"] + list(_READERS),
                           capture_output=True, text=True, cwd=_REPO).stdout.strip()
    lines.append("kit reader working-tree status (%d files): %s"
                 % (len(_READERS), dirty or "UNMODIFIED"))
    ok = ok and not dirty
    return gate("W1a no regression (tier-r gates + tests, kit battle-camera tests)", ok, *lines)


# --------------------------------------------------------------------------- W1b
def w1b_roundtrip(rows):
    s = W.census_summary(rows)
    bad, skipped = s["roundtrip_bad"], s["skipped"]
    ok = s["shots"] > 0 and s["roundtrip_ok"] == s["shots"] and not bad
    lines = [
        "decode -> re-encode over the whole extracted corpus, with the BATTLE codec unchanged:",
        "",
        "   %d / %d camera blocks re-serialise BYTE-IDENTICAL, across %d / %d effects"
        % (s["roundtrip_ok"], s["shots"], s["effects_with_shots"], s["effects"]),
        "   %d bytes of stock summon camera data round-tripped in total" % s["bytes_total"],
        "",
        "   failures: %s" % (bad or "none"),
        "   named-but-unresolvable ops (NOT failures -- see below): %d dynamic (0x29 arg2 != 0), "
        "%d 'no camera' (0x23 arg1 = 0xFF)" % (s["dynamic"], s["setup_none"]),
        "   blocks the extractor refused to read: %d" % len(skipped),
    ]
    for k in skipped:
        lines.append("      %s" % k)
    lines += [
        "",
        "   WHY it is byte-exact and not merely structure-preserving, stated as invariants the",
        "   corpus satisfies %d/%d (each one is a test):" % (s["shots"], s["shots"]),
        "      1. the outer offset table's first entry == the table's own end (no gap, no padding)",
        "      2. the group offsets are STRICTLY increasing, so canonical order == physical order",
        "      3. the LAST group is never a sequence -- it is the selector (bit 3) or the anchors",
        "         (bits 4-7), both of which camera_codec carries verbatim, so the <=2 B alignment",
        "         pad at the block's end is preserved instead of being dropped by the frame-0 stop",
        "      4. no camera block is ever the last sub-file in its chunk, so its end is always a",
        "         real directory delta and never the id-2 region's sector padding",
    ]
    return gate("W1b THE ROUND-TRIP -- byte-exact decode/encode over every summon camera", ok, *lines)


# --------------------------------------------------------------------------- W1c
#: TIER R's archived capture (EF227-CHOREOGRAPHY sec 4a).  Used ONLY to print a confirmation column
#: after the derivation is complete -- never as an input to it.
CAPTURE_H = ((58, 256, 57), (153, 415, 152), (302, 512, 300))


def w1c_two_clocks():
    path = os.path.join(W.SCRATCH_CORPUS, "ef%03d.bytes" % EF227)
    if not os.path.isfile(path):
        return gate("W1c ef227 two-clocks reproduction", False, "corpus missing: %s" % path)
    with open(path, "rb") as fh:
        blob = fh.read()
    machines = W.recover_machines(blob, "ef%03d" % EF227)
    tl = W.merged_timeline(blob, "ef%03d" % EF227, machines)
    hrows = tl.h_changes()
    pairs = tl.pairs(hrows, window=6)

    lines = ["DERIVED, on the sequence clock -- nothing here is fitted:",
             "   a camera event sits at  op.seq_tick + local_frame - 1",
             "   a phase boundary sits at  the 0x80+N op's own seq_tick + R3's phase start_tick",
             "   program starts: " + ", ".join("c%d prog%d @%d" % (c, p, t)
                                               for (c, p), t in sorted(tl.program_starts.items())),
             "",
             "   %-8s %-24s %-8s %-14s %s" % ("cam@", "camera writes", "phase@", "phase", "offset")]
    got = []
    for c, p, d in pairs:
        got.append((c.seq_tick, c.h, p.seq_tick, d))
        lines.append("   %-8d H -> %-19d %-8d %-14s %+d" % (c.seq_tick, c.h, p.seq_tick, p.who, d))

    want = [(11, 256, 12, -1), (106, 415, 107, -1), (255, 512, 255, 0)]
    ok = got == want
    lines += ["",
              "   the three pairs, derived: %s" % (got,),
              "   expected                : %s" % (want,)]

    # ---- CONFIRMATION ONLY, printed after the fact
    cam_seq = [g[0] for g in got]
    ph_seq = [g[2] for g in got]
    cap_cam = [c[0] for c in CAPTURE_H]
    cap_ph = [c[2] for c in CAPTURE_H]
    d_cam = sorted({a - b for a, b in zip(cap_cam, cam_seq)})
    d_ph = sorted({a - b for a, b in zip(cap_ph, ph_seq)})
    same_h = [g[1] for g in got] == [c[1] for c in CAPTURE_H]
    same_spacing = ([b - a for a, b in zip(cam_seq, cam_seq[1:])] ==
                    [b - a for a, b in zip(cap_cam, cap_cam[1:])] and
                    [b - a for a, b in zip(ph_seq, ph_seq[1:])] ==
                    [b - a for a, b in zip(cap_ph, cap_ph[1:])])
    lines += [
        "",
        "   CONFIRMATION (the archived s53 capture, consulted only now):",
        "      capture camera frames %s vs derived seq ticks %s  -> constant origin %s"
        % (cap_cam, cam_seq, d_cam),
        "      capture phase  frames %s vs derived seq ticks %s  -> constant origin %s"
        % (cap_ph, ph_seq, d_ph),
        "      the H values match: %s;  the INTERVALS between the events match: %s"
        % (same_h, same_spacing),
    ]
    ok = ok and same_h and same_spacing and len(d_cam) == 1 and len(d_ph) == 1
    if len(d_cam) == 1 and len(d_ph) == 1:
        lines += [
            "      => ONE origin per clock, and the two differ by %d frames.  THAT %d-frame gap IS"
            % (d_cam[0] - d_ph[0], d_cam[0] - d_ph[0]),
            "         'the two clocks': in the AUTHORED data the cut leads the beat by 1, 1 and 0",
            "         ticks; at runtime the camera install lags by a constant %d, which is what the"
            % (d_cam[0] - d_ph[0]),
            "         capture reads as +1, +1, +2 AFTER the boundary.",
        ]
        finding("The camera clock's origin (%d) and the program clock's origin (%d) differ by a "
                "CONSTANT %d frames across all three ef227 pairs. TIER R's '1-2 frames after' is "
                "that constant plus an authored lead of 1, 1, 0 ticks -- so a retime (W3) must "
                "preserve the AUTHORED lead, and cannot change the %d."
                % (d_cam[0], d_ph[0], d_cam[0] - d_ph[0], d_cam[0] - d_ph[0]))

    # the corpus-wide shape of the same question, for free
    aligned = [(c.seq_tick, p.seq_tick, d) for c, p, d in tl.pairs()]
    lines += ["", "   beyond the three H changes: %d of ef227's %d camera events land within 4 ticks"
              % (len(aligned), len(tl.cameras())),
              "   of a phase boundary; offsets %s"
              % dict(sorted(collections.Counter(d for _a, _b, d in aligned).items()))]
    return gate("W1c ef227 two-clocks reproduction (data+code, capture as confirmation)", ok, *lines)


# --------------------------------------------------------------------------- W1d
def w1d_census(rows):
    s = W.census_summary(rows)
    per_shot_sizes = sorted(n for r in rows for n in r.shot_sizes)
    kfs = sorted(n for r in rows for n in r.keyframes)
    spans = sorted(n for r in rows for n in r.spans)

    def q(v, p):
        return v[int(len(v) * p)] if v else 0

    ok = s["effects"] > 0 and s["shots"] > 0
    lines = [
        "%d effects in the corpus; %d of them carry camera ops; %d resolve at least one shot"
        % (s["effects"], s["effects_with_camera_ops"], s["effects_with_shots"]),
        "%d camera-naming ops -> %d statically-resolved shots" % (s["camera_ops"], s["shots"]),
        "   %d PLAY_CAMERA ops pick their shot at RUNTIME (arg2 != 0) -- not decodable offline"
        % s["dynamic"],
        "   %d SETUP_CAMERA ops carry arg1 = 0xFF (no camera)" % s["setup_none"],
        "",
        "shots per effect: %s" % s["shots_per_effect"],
        "sequences per shot (alternate tracks the bit-3 selector chooses between): %s"
        % s["sequences_per_shot"],
        "",
        "block size:     min %d  p25 %d  median %d  p75 %d  max %d   (mean %.1f, %d B total)"
        % (s["size_min"], q(per_shot_sizes, .25), q(per_shot_sizes, .5), q(per_shot_sizes, .75),
           s["size_max"], s["size_mean"], s["bytes_total"]),
        "keyframes/shot: min %d  p25 %d  median %d  p75 %d  max %d   (%d keyframes total)"
        % (s["kf_min"], q(kfs, .25), q(kfs, .5), q(kfs, .75), s["kf_max"], s["kf_total"]),
        "shot length:    min %d  p25 %d  median %d  p75 %d  max %d local frames"
        % (s["span_min"], q(spans, .25), q(spans, .5), q(spans, .75), s["span_max"]),
        "",
        "SHARED CAMERA DATA: %d groups of byte-identical blocks covering %d references; %d of those"
        % (s["identical_groups"], s["identical_refs"], s["identical_cross_effect"]),
        "   groups span more than one effect -- so editing one effect's block cannot leak into",
        "   another's (each container owns its own bytes), but the SAME shot is authored many times.",
    ]
    biggest = sorted(rows, key=lambda r: -sum(r.shot_sizes))[:5]
    lines.append("")
    lines.append("the five effects with the most camera data: "
                 + ", ".join("%s %dB/%d shots" % (r.source, sum(r.shot_sizes), r.n_shots)
                             for r in biggest))
    return gate("W1d corpus census", ok, *lines)


# --------------------------------------------------------------------------- W1e
_BYTES_LIT = re.compile(rb"(?s)b(['\"])(.*?)(?<!\\)\1")


def _byte_literals(path: str, minlen: int = 6):
    """Every bytes literal of >= ``minlen`` bytes in a Python source file, decoded to real bytes."""
    out = []
    src = open(path, "r", encoding="utf-8").read()
    try:
        tree = ast.parse(src)
    except SyntaxError:                                        # pragma: no cover
        return out
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, bytes):
            if len(node.value) >= minlen and len(set(node.value)) > 1:
                out.append((node.lineno, node.value))
    return out


def w1e_provenance(rows):
    lines, ok = [], True
    lits = []
    for name in COMMITTABLE:
        p = _committable_path(name)
        if not os.path.isfile(p):
            lines.append("%-24s MISSING" % name)
            ok = False
            continue
        if name.endswith(".py"):
            for ln, b in _byte_literals(p):
                lits.append((name, ln, b))
    lines.append("byte literals of >= 6 non-uniform bytes in the committable tier-W sources: %d"
                 % len(lits))
    hits = []
    if lits:
        for path in W.corpus_paths():
            with open(path, "rb") as fh:
                blob = fh.read()
            for name, ln, b in lits:
                if b in blob:
                    hits.append((name, ln, os.path.basename(path), b.hex()))
    lines.append("   of those, appearing anywhere in the %d-file corpus: %d"
                 % (len(W.corpus_paths()), len(hits)))
    for h in hits:
        lines.append("      LEAK %s:%d found in %s (%s)" % h)
    ok = ok and not hits

    # dumps land outside the repo, and the guard actually refuses
    lines.append("")
    lines.append("dump target: %s" % W.SCRATCH_OUT)
    inside = os.path.commonpath([os.path.abspath(W.SCRATCH_OUT), os.path.abspath(_REPO)]) == \
        os.path.abspath(_REPO)
    lines.append("   inside the repo tree: %s" % inside)
    ok = ok and not inside
    try:
        W.dump_shots([], os.path.join(_HERE, "leak.csv"))
        lines.append("   GUARD FAILED: a repo-relative dump was accepted")
        ok = False
    except W.SummonCameraError:
        lines.append("   guard: a repo-relative dump path is refused")

    # the report's quote budget
    lines.append("")
    if os.path.isfile(REPORT):
        text = open(REPORT, "r", encoding="utf-8").read()
        hexruns = re.findall(r"\b(?:[0-9a-f]{2}[ ]){3,}[0-9a-f]{2}\b", text)
        # a decoded keyframe DUMP is the thing the tier's provenance rule keeps out of the repo
        posedump = re.findall(r"pitch\s*=?\s*\d+.{0,24}?distance\s*=?\s*\d+", text)
        # the report's own budget: every stock DATA value it names, tagged inline as [stock]
        quoted = re.findall(r"\[stock\]", text)
        lines.append("%s: %d hex byte runs (must be 0), %d decoded-keyframe rows (must be 0), "
                     "%d values tagged [stock] (budget %d)"
                     % (os.path.basename(REPORT), len(hexruns), len(posedump), len(quoted),
                        QUOTE_BUDGET))
        ok = ok and not hexruns and not posedump and len(quoted) <= QUOTE_BUDGET
    else:
        lines.append("%s has not been written" % os.path.basename(REPORT))
        ok = False
    return gate("W1e provenance (no stock bytes committable, dumps to SCRATCH)", ok, *lines)


# --------------------------------------------------------------------------- main
def main() -> int:
    print(__doc__.splitlines()[0])
    if not W.corpus_paths():
        print("\nFATAL: no ef###.bytes under %s -- extract the corpus first." % W.SCRATCH_CORPUS)
        return 2
    rows = W.census()
    w1a_no_regression()
    w1b_roundtrip(rows)
    w1c_two_clocks()
    w1d_census(rows)
    w1e_provenance(rows)

    print("\n" + "=" * 72)
    for name, ok in RESULTS:
        print("%-5s %s" % ("PASS" if ok else "FAIL", name))
    if FINDINGS:
        print("\nFINDINGS")
        for f in FINDINGS:
            print(" * " + f)
    passed = sum(1 for _n, ok in RESULTS if ok)
    print("=" * 72)
    print("%d/%d gates pass" % (passed, len(RESULTS)))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":                                    # pragma: no cover
    raise SystemExit(main())
