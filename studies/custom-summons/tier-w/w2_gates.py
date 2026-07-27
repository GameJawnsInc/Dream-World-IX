r"""TIER W rung 2 -- the gate runner.  `py w2_gates.py` prints X0..X7 with numbers and PASS/FAIL.

X0  NO REGRESSION: tier-r's r1/r2/r3 gate runners, tier-w's w1_gates, and every tier-r/tier-w test
    module still pass -- this rung adds a writer on top of W1's reader and changes neither
X1  THE UNCHANGED-EVERYTHING-ELSE PROOF: the rebuilt container diffed against the install's own
    bytes.  ONLY the intended bytes differ, and each one is named: which sub-block of which Code of
    which sequence of which sub-file.  Every duration byte identical, every other sub-file
    identical, the id-2 directory identical
X2  ROUND-TRIP: the patched camera block decodes and re-serialises byte-exact through the UNMODIFIED
    W1 path, and W1 section 0's four invariants still hold on the block we wrote
X3  THE THREE-SEQUENCE CHECK on the target block: alternates present?  handled how?
X4  REVERT: the generated revert script restores the mod folder to its exact prior state, proven by
    a hash manifest of the whole tree -- in both the fresh-file and the overwrite-a-prior-file cases
X5  PROVENANCE: no stock byte run in any committable file, the build reads the user's install at
    RUN TIME (never the repo, never a prior override), staged output lands under SCRATCH
X6  THE DYNAMIC-OP DISCLOSURE (W5): a container carrying a runtime-chosen (arg2=3) camera op is
    REFUSED until the spec acknowledges that the edited block's reachability is unverifiable
    offline -- and an acknowledgement of a risk the container does not carry is refused too
X7  THE SPEC REGISTRY (W5): every rescore spec beside this tool builds, and ef227's is pinned to
    its effect EXTERNALLY so a spec that changed its own `effect` would be caught here

X1/X2/X3 run over the whole registry, not just ef227.  Reads the user's own install.  Prints only
structure -- offsets, counts, sizes, and the small number of stock camera VALUES the delta is
expressed against.
"""
from __future__ import annotations

import ast
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rescore as R                                             # noqa: E402  (sets up sys.path)
import ef_container as EC                                       # noqa: E402
import summon_camera as W                                       # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
_STUDY = os.path.dirname(_HERE)
_REPO = os.path.dirname(os.path.dirname(_STUDY))
TIER_R = os.path.join(_STUDY, "tier-r")

#: THE SPEC REGISTRY -- ``[(toml, pinned effect or None)]``.  W5 turned this runner from "build the
#: one shipped spec" into "build every spec beside this tool": ef227's entry keeps an EXTERNAL
#: expectation (227) so a toml that changed its own ``effect`` is caught here rather than gated
#: against the wrong container; a discovered sibling is unpinned, because inventing an expectation
#: from a filename would be a guess.
SPECS = R.discover_specs(_HERE)
#: the ef227 spec specifically -- X4/X5's install-bound checks are still written against it
SPEC = SPECS[0][0] if SPECS else os.path.join(_HERE, "bahamut_rescore.toml")
REPORT = os.path.join(_HERE, "W2-RESCORE.md")

#: the committable files this rung adds; X5 scans them for stock byte runs.  The discovered specs
#: join the list so a new effect's toml is provenance-checked on the same terms as ef227's.
COMMITTABLE = ("rescore.py", "test_rescore.py", "w2_gates.py", "W2-RESCORE.md") + \
    tuple(os.path.basename(p) for p, _e in SPECS)
#: the report may quote stock VALUES (a pose byte, an H distance) -- never stock BYTES.
QUOTE_BUDGET = 12

RESULTS = []


def gate(name: str, ok: bool, *lines: str) -> bool:
    RESULTS.append((name, ok))
    print("\n%s %s  %s" % ("[PASS]" if ok else "[FAIL]", name, "-" * max(2, 58 - len(name))))
    for ln in lines:
        print("   " + ln)
    return ok


def _pytest(path: str, cwd: str) -> tuple:
    p = subprocess.run([sys.executable, "-m", "pytest", path, "-q", "--no-header"],
                       capture_output=True, text=True, cwd=cwd)
    line = next((l for l in reversed(p.stdout.splitlines())
                 if " passed" in l or " failed" in l or " error" in l), "?")
    m = re.search(r"(\d+) passed", line)
    return p.returncode, int(m.group(1)) if m else 0, line.strip()


# --------------------------------------------------------------------------- X0
def x0_no_regression():
    lines, ok, total = [], True, 0
    for runner, want, cwd in (("r1_gates.py", "8/8", TIER_R), ("r2_gates.py", "6/6", TIER_R),
                              ("r3_gates.py", "5/5", TIER_R), ("w1_gates.py", "5/5", _HERE)):
        p = subprocess.run([sys.executable, os.path.join(cwd, runner)],
                           capture_output=True, text=True, cwd=cwd)
        tail = [l for l in p.stdout.splitlines() if "gates pass" in l]
        got = tail[-1].strip() if tail else "(none)"
        good = p.returncode == 0 and got.startswith(want)
        ok = ok and good
        lines.append("%-14s %s   (want %s)" % (runner, got, want))
    for mod, cwd in (("test_tier_r_disasm.py", TIER_R), ("test_tier_r_annot.py", TIER_R),
                     ("test_summon_inspect.py", TIER_R),
                     ("test_summon_camera.py", _HERE), ("test_rescore.py", _HERE)):
        rc, n, line = _pytest(os.path.join(cwd, mod), cwd)
        ok = ok and rc == 0
        total += n
        lines.append("%-26s %s" % (mod, line))
    lines.append("tier-r + tier-w tests: %d passed" % total)
    # the reader this rung builds on must be untouched
    p = subprocess.run(["git", "status", "--porcelain", "--",
                        "studies/custom-summons/tier-w/summon_camera.py",
                        "ff9mapkit/ff9mapkit/battle/camera_codec.py"],
                       capture_output=True, text=True, cwd=_REPO)
    dirty = [l for l in p.stdout.splitlines() if l.strip()]
    lines.append("summon_camera.py + camera_codec.py working tree: %s"
                 % ("UNMODIFIED" if not dirty else "MODIFIED -- " + "; ".join(dirty)))
    ok = ok and not dirty
    return gate("X0 no regression (r1/r2/r3 + w1 gates, all tests, reader untouched)", ok, *lines)


# --------------------------------------------------------------------------- the shared builds
_BUILDS = {}


def build(path=None):
    """The build for one registry entry, memoised.  Defaults to ef227's so every gate written
    before the registry existed keeps meaning exactly what it meant."""
    path = path or SPEC
    if path not in _BUILDS:
        _BUILDS[path] = R.build_patched(R.load_spec(path), path)
    return _BUILDS[path]


# --------------------------------------------------------------------------- X1
def x1_unchanged_everything_else():
    ok = True
    lines = []
    for path, pinned in SPECS:
        lines.append("")
        lines.append("== %s (%s)" % (os.path.basename(path),
                                     "pinned to ef%03d" % pinned if pinned is not None
                                     else "discovered, unpinned"))
        ok = _x1_one(build(path), lines.append) and ok
    return gate("X1 the unchanged-everything-else proof (%d spec(s))" % len(SPECS), ok, *lines)


def _x1_one(b, out):
    ok = True
    changed = b.check.changed_offsets
    out("container ef%03d: %d B in, %d B out -- %d byte(s) differ in the WHOLE file"
        % (b.effect, len(b.orig), len(b.patched), len(changed)))
    ok = ok and len(b.orig) == len(b.patched)

    # every changed byte named: sub-file -> sequence -> Code -> sub-block -> field.  Keyed on the
    # ABSOLUTE file offset so a spec with several [[edit]]s across several blocks is covered too --
    # ef227 has exactly one splice, but the registry no longer promises that.
    ex = W.extract_shots(b.orig, "ef%03d" % b.effect)
    meaning = {}
    for sp in b.splices:
        shot = next(s for s in ex.shots if s.lo == sp.lo)
        for si, seq in enumerate(shot.camera["sequences"]):
            off = 0
            # the sequence group's own base inside the block
            for name, lo, hi in W.block_layout(shot.block):
                if name == "sequence%d" % si:
                    off = lo
            for ci, c in enumerate(seq):
                if not c.get("frame"):
                    break
                body = off + 4
                for fname, (fo, fsz) in R.code_field_offsets(c["flags"]).items():
                    for k in range(fsz):
                        meaning[sp.lo + body + fo + k] = (sp.lo, si, W.frame_number(c["frame"]),
                                                          ci, fname, k)
                off = body + len(c["block"])
    for o in changed:
        m = meaning.get(o)
        if m is None:
            ok = False
            out("  file %#x: UNEXPLAINED -- not inside any Code sub-block of an edited shot" % o)
            continue
        base, si, frame, ci, fname, k = m
        field = {("campos", 3): "orientation", ("campos", 4): "roll", ("campos", 2): "pitch",
                 ("campos", 5): "distance", ("campos", 0): "code", ("campos", 1): "flags",
                 ("focal", 2): "H (projection distance) lo", ("focal", 3): "H hi",
                 ("focal", 0): "duration", ("focal", 1): "flags"}.get((fname, k), "%s+%d" % (fname, k))
        out("  file %#x = block+%-3d  seq%d Code %d (local frame %d) %s -> %s"
            % (o, o - base, si, ci, frame, fname, field))
        if "duration" in field:
            ok = False
            out("    ^^ A DURATION CHANGED -- W2 forbids it")

    lines = []                                       # the rest of the gate, unchanged in substance
    ok = _x1_tail(b, ex, lines) and ok
    for ln in lines:
        out(ln)
    return ok


def _x1_tail(b, ex, lines):
    ok = True
    changed = b.check.changed_offsets
    # every duration byte identical
    after = W.extract_shots(b.patched, "ef%03d" % b.effect)
    n_dur, dur_ok, n_frames = 0, True, 0
    for a, c in zip(ex.shots, after.shots):
        for si in range(len(a.camera["sequences"])):
            ka, kc = W.keyframes(a.camera, si), W.keyframes(c.camera, si)
            dur_ok = dur_ok and [k.local_frame for k in ka] == [k.local_frame for k in kc]
            dur_ok = dur_ok and [k.marks for k in ka] == [k.marks for k in kc]
            n_frames += len(ka)
            for x, y in zip(ka, kc):
                for which in ("cammove", "tgtmove"):
                    mx, my = x.movement(which), y.movement(which)
                    if mx:
                        n_dur += 1
                        dur_ok = dur_ok and my and mx["duration"] == my["duration"]
                fx, fy = x.focal(), y.focal()
                if fx:
                    n_dur += 1
                    dur_ok = dur_ok and fy and fx["duration"] == fy["duration"]
    lines.append("durations + frame words: %d duration field(s) and %d frame word(s) across all "
                 "shots -- %s" % (n_dur, n_frames, "ALL IDENTICAL" if dur_ok else "DIVERGED"))
    ok = ok and dur_ok

    # every other sub-file identical, and the id-2 directory identical
    co = EC.parse_header(b.orig, strict=True)
    cp = EC.parse_header(b.patched, strict=True)
    n_sub, sub_ok, dir_ok, n_dir = 0, True, True, 0
    for slot in range(len(co.chunks)):
        a = W.id2_directory(b.orig, co, slot)
        c = W.id2_directory(b.patched, cp, slot)
        if a is None:
            continue
        n_dir += len(a.entries)
        dir_ok = dir_ok and (a.entries == c.entries and a.base == c.base and a.size == c.size)
        for i in range(len(a.entries)):
            try:
                lo, hi = a.bounds(i)
            except W.SummonCameraError:
                continue
            if any((lo, hi) == (sp.lo, sp.hi) for sp in b.splices):
                continue
            n_sub += 1
            sub_ok = sub_ok and b.orig[lo:hi] == b.patched[lo:hi]
    lines.append("other sub-files: %d compared across %d chunk archive(s) -- %s"
                 % (n_sub, len(co.chunks), "ALL IDENTICAL" if sub_ok else "DIVERGED"))
    lines.append("id-2 directory: %d entries over %d chunk(s) -- %s"
                 % (n_dir, len(co.chunks), "IDENTICAL" if dir_ok else "MOVED"))
    ok = ok and sub_ok and dir_ok

    # everything outside the id-2 archives (the sequence stream, the programs, the art) untouched
    outside = [o for o in changed
               if not any(sp.lo <= o < sp.hi for sp in b.splices)]
    lines.append("bytes outside the target block(s) (sequence stream, programs, art, headers): %d"
                 % len(outside))
    ok = ok and not outside
    return ok


# --------------------------------------------------------------------------- X2
def x2_roundtrip():
    ok, lines = True, []
    for path, _pinned in SPECS:
        b = build(path)
        c = b.check
        lines.append("")
        lines.append("== %s -- ef%03d" % (os.path.basename(path), b.effect))
        lines.append("container header re-parses STRICT: %s (native walker cursor_end %#x == "
                     "size %#x)" % (c.header_ok, c.cursor_end, c.size))
        lines.append("every camera block in the rebuilt container round-trips: %d/%d byte-exact "
                     "through the UNMODIFIED camera_codec" % (c.roundtrip_ok, c.roundtrip_total))
        for k, v in sorted(c.invariants.items()):
            lines.append("W1 invariant %-34s %s" % (k, v))
        # each edited block itself, decoded and re-encoded standalone
        block_ok = True
        for sp in b.splices:
            blk = bytes(b.patched[sp.lo:sp.hi])
            again = W.serialize_camera_block(W.parse_camera_block(blk))
            block_ok = block_ok and again == blk
            lines.append("the rescored block @%#x alone: %d B -> parse -> serialize -> %d B, %s"
                         % (sp.lo, len(blk), len(again),
                            "BYTE-EXACT" if again == blk else "DIVERGES"))
        ok = ok and c.header_ok and c.roundtrip_ok == c.roundtrip_total \
            and all(c.invariants.values()) and block_ok
    return gate("X2 round-trip + W1's four invariants on the block(s) we WROTE", ok, *lines)


# --------------------------------------------------------------------------- X3
def x3_three_sequence():
    lines, ok = [], True
    for path, _pinned in SPECS:
        b = build(path)
        for letter, v in b.verdicts:
            lines.append("%-24s ef%03d shot %s: %s"
                         % (os.path.basename(path), b.effect, letter, v.line()))
            ok = ok and v.safe
    lines.append("corpus context: 374 of 798 blocks declare three sequences and 332 of those carry "
                 "GENUINELY DIFFERENT alternates (W1 section 4.1) -- the check is not academic")
    # and prove the guard actually fires, on a synthetic block with differing alternates
    sys.path.insert(0, _HERE)
    from test_summon_camera import ESTABLISH, MOVE, TAIL, camera_block, code, synth
    a = [ESTABLISH, MOVE, TAIL]
    other = [code(1, 0x0809, b"\x2a\x40\x33\x0d\x77\x1f" + b"\x2a\x40\x07\x03\x01\x02"
                  + b"\x07\x03\x2c\x01"), MOVE, TAIL]
    blk = camera_block([a, other, list(other)], selector=b"\x02\x00\x00\x00")
    blob = synth([b"\xaa" * 32, blk, b"\xbb" * 48],
                 [(W.OP_WAIT, 0, 10), (W.OP_PLAY_CAMERA, 1, 0)])
    fired = False
    try:
        R.build_patched({"rescore": {"effect": 999}, "edit": [
            {"shot": "A", "frame": 1, "camera": {"roll": 200}}]}, "t", blob=blob)
    except R.RescoreError as e:
        fired = "THREE-SEQUENCE TRAP" in str(e)
    lines.append("the guard FIRES on a synthetic 3-track block with differing alternates: %s" % fired)
    ok = ok and fired
    return gate("X3 the three-sequence check on the target block", ok, *lines)


# --------------------------------------------------------------------------- X4
def _manifest(root) -> dict:
    out = {}
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            p = os.path.join(dirpath, f)
            with open(p, "rb") as fh:
                out[os.path.relpath(p, root).replace("\\", "/")] = \
                    hashlib.sha256(fh.read()).hexdigest()
    return out


def _manifest_hash(m: dict) -> str:
    return hashlib.sha256(
        "\n".join("%s %s" % (k, m[k]) for k in sorted(m)).encode()).hexdigest()


def x4_revert():
    b = build()
    lines, ok = [], True
    for case, seed in (("fresh mod folder", None),
                       ("mod folder already carrying an ef227 override", b"prior override bytes")):
        tmp = tempfile.mkdtemp(prefix="w2revert-")
        try:
            mod = os.path.join(tmp, "mod")
            dest = os.path.join(mod, *R.MOD_SUBPATH.split("/"), "ef%03d" % b.effect)
            if seed is not None:
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(dest, "wb") as fh:
                    fh.write(seed)
            os.makedirs(mod, exist_ok=True)
            before = _manifest(mod)
            out = R.stage(b, mod, tmp)
            staged = _manifest(mod)
            p = subprocess.run([sys.executable, out["revert_script"]],
                               capture_output=True, text=True)
            after = _manifest(mod)
            same = _manifest_hash(before) == _manifest_hash(after)
            ok = ok and p.returncode == 0 and same and _manifest_hash(staged) != _manifest_hash(before)
            lines.append("%-46s before %s / staged %s / after %s -> %s"
                         % (case, _manifest_hash(before)[:12], _manifest_hash(staged)[:12],
                            _manifest_hash(after)[:12], "EXACT RESTORE" if same else "DRIFT"))
            lines.append("   %d file(s) before, %d after staging, %d after revert"
                         % (len(before), len(staged), len(after)))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    lines.append("the revert script is stdlib-only and idempotent (test_rescore covers a double run)")
    return gate("X4 revert restores the mod folder exactly (proven by hash)", ok, *lines)


# --------------------------------------------------------------------------- X5
def _byte_literals(path: str, minlen: int = 6):
    """Every bytes literal of >= ``minlen`` NON-UNIFORM bytes in a source file -- W1e's own rule."""
    out = []
    try:
        tree = ast.parse(open(path, "r", encoding="utf-8").read())
    except SyntaxError:                                          # pragma: no cover
        return out
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, bytes):
            if len(node.value) >= minlen and len(set(node.value)) > 1:
                out.append((node.lineno, node.value))
    return out


def x5_provenance():
    b = build()
    lines, ok = [], True
    # (a) no stock byte run in a committable file -- W1e's rule, verbatim, so the two rungs cannot
    # drift apart: every bytes literal of >= 6 NON-UNIFORM bytes, searched across the whole corpus
    # AND the target container.  (A shorter or uniform run -- b"\x00\x00\x00\x00", b"\x01\x00\x00\x00"
    # -- occurs in essentially every binary and would make this gate noise, not evidence.)
    lits = []
    for name in COMMITTABLE:
        fp = os.path.join(_HERE, name)
        if not os.path.isfile(fp):
            lines.append("%s MISSING" % name)
            ok = False
            continue
        if name.endswith(".py"):
            lits.extend((name, ln, raw) for ln, raw in _byte_literals(fp))
    lines.append("byte literals of >= 6 non-uniform bytes in the committable rung-2 sources: %d"
                 % len(lits))
    hits = []
    if lits:
        blobs = [("ef%03d (the target, from the install)" % b.effect, b.orig)]
        for path in W.corpus_paths():
            with open(path, "rb") as fh:
                blobs.append((os.path.basename(path), fh.read()))
        for who, blob in blobs:
            for name, ln, raw in lits:
                if raw in blob:
                    hits.append("LEAK %s:%d found in %s" % (name, ln, who))
    lines.append("   of those, appearing in the target container or anywhere in the %d-file corpus: "
                 "%d" % (len(W.corpus_paths()), len(hits)))
    for h in hits:
        lines.append("      " + h)
    ok = ok and not hits

    # (b) EVERY registered spec reads the INSTALL at run time, not the repo and not a prior
    # override, and every one of them is GUARDED -- ef227 by the code-side constant, a generalised
    # spec by its own expect_sha256.  An unguarded spec is a spec that would splice its delta into
    # whatever bytes it found.
    for path, _pinned in SPECS:
        bb = build(path)
        lines.append("%-24s ef%03d source: %s" % (os.path.basename(path), bb.effect, bb.source))
        ok = ok and "resources.assets" in bb.source and _REPO not in bb.source
        own = R.load_spec(path)["rescore"].get("expect_sha256")
        guarded = (bb.sha_in == R.EXPECTED_STOCK_SHA.get(bb.effect)) or \
                  (own is not None and bb.sha_in == own)
        lines.append("%-24s drift guard: %s -- %s"
                     % ("", bb.guard, "GUARDED" if guarded else "UNGUARDED (refused here)"))
        ok = ok and guarded
    lines.append("ef227 specifically: install sha %s the registered constant"
                 % ("MATCHES" if b.sha_in == R.EXPECTED_STOCK_SHA.get(b.effect) else "DIFFERS from"))
    ok = ok and b.sha_in == R.EXPECTED_STOCK_SHA.get(b.effect)

    # (c) staged output lands under SCRATCH, and the repo is refused
    staged = os.path.join(R.SCRATCH_ROOT, "mod", *R.MOD_SUBPATH.split("/"), "ef%03d" % b.effect)
    lines.append("staged override: %s (%s)"
                 % (staged, "present" if os.path.isfile(staged) else "not staged yet"))
    refused = False
    try:
        R._refuse_repo_path(os.path.join(_REPO, "studies", "x"))
    except R.RescoreError:
        refused = True
    lines.append("a repo-relative staging root is REFUSED: %s" % refused)
    ok = ok and refused
    # nothing stock-derived committed
    p = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=_REPO)
    untracked = [l[3:] for l in p.stdout.splitlines() if l[:2] in ("??", " M", "M ", "A ")]
    big = [u for u in untracked if u.strip().endswith((".bytes", "ef227"))]
    lines.append("stock-shaped files in the repo working tree: %d" % len(big))
    ok = ok and not big

    # (c2) the spec tomls are a committable class of their own now that `init` GENERATES them.  A
    # generated spec may name the values its own declared edit writes; it must never become a
    # decoded stock listing, so it is held to the report's own two rules.
    for path, _pinned in SPECS:
        text = open(path, "r", encoding="utf-8").read()
        hexruns = re.findall(r"\b(?:[0-9a-f]{2}[ ]){3,}[0-9a-f]{2}\b", text)
        posedump = re.findall(r"pitch\s*=?\s*\d+.{0,24}?distance\s*=?\s*\d+", text)
        lines.append("%-24s %d hex byte run(s) (must be 0), %d decoded-keyframe row(s) (must be 0)"
                     % (os.path.basename(path), len(hexruns), len(posedump)))
        ok = ok and not hexruns and not posedump

    # (d) the report's quote budget
    if os.path.isfile(REPORT):
        text = open(REPORT, "r", encoding="utf-8").read()
        hexruns = re.findall(r"\b(?:[0-9a-f]{2}[ ]){3,}[0-9a-f]{2}\b", text)
        posedump = re.findall(r"pitch\s*=?\s*\d+.{0,24}?distance\s*=?\s*\d+", text)
        quoted = re.findall(r"\[stock\]", text)
        lines.append("%s: %d hex byte runs (must be 0), %d decoded-keyframe rows (must be 0), "
                     "%d values tagged [stock] (budget %d)"
                     % (os.path.basename(REPORT), len(hexruns), len(posedump), len(quoted),
                        QUOTE_BUDGET))
        ok = ok and not hexruns and not posedump and len(quoted) <= QUOTE_BUDGET
    else:
        lines.append("%s has not been written" % os.path.basename(REPORT))
        ok = False
    return gate("X5 provenance (no SE bytes committable, install read at run time, SCRATCH out)",
                ok, *lines)


# --------------------------------------------------------------------------- X6
def _synthetic_dynamic_container():
    """A container that runs BOTH a literal camera op and a runtime-chosen one -- ef227's shape plus
    the trap ef227 does not have."""
    from test_summon_camera import ESTABLISH, MOVE, TAIL, camera_block, synth
    blk = camera_block([[ESTABLISH, MOVE, TAIL]])
    return synth([b"\xaa" * 32, blk, b"\xbb" * 48],
                 [(W.OP_WAIT, 0, 10), (W.OP_PLAY_CAMERA, 1, W.ARG2_LITERAL),
                  (W.OP_WAIT, 0, 5), (W.OP_PLAY_CAMERA, 0, W.ARG2_TABLE)])


def x6_dynamic_disclosure():
    """W5's generalisation gate.  ef227 sidesteps this entirely -- which is exactly the problem: its
    offline completeness claim does not carry to the 300-of-342 scaffoldable corpus containers that
    DO run a runtime-chosen camera op."""
    sys.path.insert(0, _HERE)
    lines, ok = [], True

    # (a) the shipped ef227 spec is unaffected -- it carries no such op and declares no key
    b = build()
    lines.append("ef%03d (the shipped spec): %d runtime-chosen op(s), acknowledge key %s"
                 % (b.effect, len(b.dynamic), "declared" if b.acknowledged else "absent"))
    ok = ok and not b.dynamic and not b.acknowledged

    # (b) the gate FIRES on a container that has one
    blob = _synthetic_dynamic_container()
    ex = W.extract_shots(blob, "synthetic")
    lines.append("synthetic container: %d literal shot(s) + %d runtime-chosen op(s)"
                 % (len(ex.shots), len(R.dynamic_ops(ex))))
    edit = [{"shot": "A", "frame": 1, "focal": {"distance": 96}}]
    fired = ""
    try:
        R.build_patched({"rescore": {"effect": 998}, "edit": edit}, "t", blob=blob)
    except R.RescoreError as e:
        fired = str(e)
    lines.append("build WITHOUT acknowledge_dynamic_ops: %s"
                 % ("REFUSED -- " + fired.splitlines()[0][:88] if fired else "BUILT (WRONG)"))
    ok = ok and "THE DYNAMIC-OP DISCLOSURE" in fired

    # (c) and LIFTS when the spec acknowledges it
    lifted = R.build_patched({"rescore": {"effect": 998, "acknowledge_dynamic_ops": True},
                              "edit": edit}, "t", blob=blob)
    lines.append("build WITH acknowledge_dynamic_ops = true: built, %d byte(s) changed, self-check %s"
                 % (len(lifted.check.changed_offsets), lifted.check.ok))
    ok = ok and lifted.check.ok and lifted.acknowledged

    # (d) the converse: an acknowledgement of a risk this container does not carry is refused too
    stale = ""
    try:
        R.build_patched({"rescore": {"effect": b.effect, "acknowledge_dynamic_ops": True},
                         "edit": [{"shot": "A", "frame": 1, "camera": {"roll": 128}}]},
                        "t", blob=b.orig)
    except R.RescoreError as e:
        stale = str(e)
    lines.append("a STALE acknowledgement on ef%03d (0 dynamic ops): %s"
                 % (b.effect, "REFUSED" if "runs NO runtime-chosen" in stale else "ACCEPTED (WRONG)"))
    ok = ok and "runs NO runtime-chosen" in stale

    # (e) a truthy non-boolean must never satisfy a safety key
    typed = ""
    try:
        R.build_patched({"rescore": {"effect": 998, "acknowledge_dynamic_ops": "true"},
                         "edit": edit}, "t", blob=blob)
    except R.RescoreError as e:
        typed = str(e)
    lines.append("acknowledge_dynamic_ops = \"true\" (a STRING): %s"
                 % ("REFUSED" if "must be a BOOLEAN" in typed else "ACCEPTED (WRONG)"))
    ok = ok and "must be a BOOLEAN" in typed

    # (f) the real corpus fixture -- ef000 carries all three traps ef227 sidesteps
    try:
        real, _src = W._load(0)
    except Exception:
        lines.append("ef000 (the corpus fixture): not extracted here -- synthetic cover only")
    else:
        rex = W.extract_shots(real, "ef000")
        sc = R.scaffold(0, real, "ef000")
        lines.append("ef000: %d shot(s) all via %s, %d runtime-chosen op(s), alternates differ on "
                     "%d/%d shot(s)"
                     % (len(rex.shots), ", ".join(sorted({s.op.kind for s in rex.shots})),
                        len(R.dynamic_ops(rex)),
                        sum(1 for r in sc.shots if r.alternates_differ), len(sc.shots)))
        lines.append("ef000's generated scaffold pre-seeds the key FALSE: %s"
                     % ("acknowledge_dynamic_ops = false" in sc.text))
        ok = ok and len(R.dynamic_ops(rex)) >= 1 \
            and "acknowledge_dynamic_ops = false" in sc.text
        spec = _toml_loads(sc.text)
        spec["edit"][0]["focal"] = {"distance": 240}
        why = ""
        try:
            R.build_patched(spec, "ef000", blob=real)
        except R.RescoreError as e:
            why = str(e)
        spec["rescore"]["acknowledge_dynamic_ops"] = True
        got = R.build_patched(spec, "ef000", blob=real)
        lines.append("ef000 build: refused without the key (%s), built with it (%d byte(s) changed "
                     "across %d track(s))"
                     % ("THE DYNAMIC-OP DISCLOSURE" in why, len(got.check.changed_offsets),
                        got.verdicts[0][1].n_sequences))
        ok = ok and "THE DYNAMIC-OP DISCLOSURE" in why and got.check.ok
    lines.append("corpus context: 300 of the 342 scaffoldable containers carry at least one "
                 "runtime-chosen camera op -- ef227's silence about this is the OUTLIER, not the "
                 "rule, and no offline gate can close it (the table is battle-field-keyed runtime "
                 "data absent from the container)")
    return gate("X6 the dynamic-op disclosure gate (W5)", ok, *lines)


def _toml_loads(text: str) -> dict:
    try:
        import tomllib
    except ModuleNotFoundError:                                  # pragma: no cover
        import tomli as tomllib                                  # type: ignore
    return tomllib.loads(text)


# --------------------------------------------------------------------------- X7
def x7_spec_registry():
    """Every rescore spec beside this tool builds, and ef227's is pinned EXTERNALLY.

    Before W5 this runner only ever built ``bahamut_rescore.toml``: "it worked for Bahamut" was the
    whole acceptance suite.  A spec that changed its own ``effect`` would have been gated against a
    different container without a word."""
    lines, ok = [], True
    lines.append("registry: %d spec(s) discovered beside %s" % (len(SPECS), os.path.basename(_HERE)))
    for path, pinned in SPECS:
        name = os.path.basename(path)
        try:
            spec = R.load_spec(path)
            b = build(path)
        except Exception as e:
            lines.append("  %-26s FAILED: %s: %s" % (name, type(e).__name__, str(e).splitlines()[0]))
            ok = False
            continue
        agree = pinned is None or b.effect == pinned
        lines.append("  %-26s ef%03d  %s  %d edit(s), %d byte(s) changed, self-check %s"
                     % (name, b.effect,
                        "pinned %d %s" % (pinned, "OK" if agree else "MISMATCH")
                        if pinned is not None else "unpinned",
                        len(spec["edit"]), len(b.check.changed_offsets), b.check.ok))
        ok = ok and agree and b.check.ok
    # and the ergonomics refusal that replaced the silent ef227 default
    bare = ""
    try:
        R.resolve_spec(None, None)
    except R.RescoreError as e:
        bare = str(e)
    lines.append("a bare `py rescore.py plan` no longer defaults to Bahamut: %s"
                 % ("REFUSED, and lists the registry" if "no default any more" in bare
                    else "STILL DEFAULTS (WRONG)"))
    ok = ok and "no default any more" in bare
    # the scaffold verb, end to end, on the rung's second-proof target
    try:
        blob, _s = W._load(211)
    except Exception:
        lines.append("ef211 (the second-proof target): not extracted here -- skipped")
    else:
        sc = R.scaffold(211, blob, "ef211", W.recover_machines(blob, "ef211"))
        rebuilt = R.build_patched(_toml_loads(sc.text), "ef211", blob=blob)
        (row,) = sc.shots
        lines.append("`init --ef 211`: %d shot(s), shot %s = c%d idx%d, %d sequence(s), %d "
                     "keyframes, focal at %s, %d dynamic op(s)"
                     % (len(sc.shots), row.letter, row.slot, row.subfile, row.n_sequences,
                        row.n_keyframes, ", ".join("f%d" % f for f in row.focal_frames),
                        len(sc.dynamic)))
        lines.append("   the generated spec is an IDENTITY and rebuilds ef211 byte-identical: %s"
                     % (sc.target.identity and rebuilt.patched == rebuilt.orig))
        lines.append("   phase cross-ref: %d phase(s) span shot %s; reframe budget %s"
                     % (len(row.phases), row.letter,
                        "TIGHT (a phase draws effect models)" if row.draws_set else "looser"))
        ok = ok and sc.target.identity and rebuilt.patched == rebuilt.orig and row.phases
    return gate("X7 the spec registry + the `init` scaffold (W5)", ok, *lines)


# --------------------------------------------------------------------------- main
def main() -> int:
    print(__doc__.splitlines()[0])
    x0_no_regression()
    x1_unchanged_everything_else()
    x2_roundtrip()
    x3_three_sequence()
    x4_revert()
    x5_provenance()
    x6_dynamic_disclosure()
    x7_spec_registry()
    print("\n" + "=" * 72)
    for name, ok in RESULTS:
        print("%-5s %s" % ("PASS" if ok else "FAIL", name))
    passed = sum(1 for _n, ok in RESULTS if ok)
    print("=" * 72)
    print("%d/%d gates pass" % (passed, len(RESULTS)))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":                                       # pragma: no cover
    raise SystemExit(main())
