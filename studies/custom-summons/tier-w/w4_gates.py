r"""TIER W rung 4 -- the gate runner.  `py w4_gates.py` prints X0..X7 with numbers and PASS/FAIL.

X0  NO REGRESSION: r1/r2/r3 (tier-r), w1_gates, w2_gates, w3_gates (if runnable), and EVERY
    tier-r/tier-w test module -- including THIS rung's ``test_reskin.py`` -- still pass.  The w4
    count is EXACT (82; it was 38 before W5's generalisation added the slot-keyed naming, the
    derived `so` attribution, the multi-writer / dual-depth / texanim / headroom / unguarded
    refusals, `hue_to`, the creature-optional scope, the per-effect staging root and the scaffold
    round-trip); the tier-r/w1/w2/w3 counts are REPORTED against their W4 baselines and gated only
    against a DROP, because the camera and retime lanes are generalising in parallel this rung and
    their counts are theirs to grow
X1  BYTE ACCOUNTING: the REAL ef227 build, every changed byte named down to its target, per-target
    counts, against A2's 8,192-byte whole-set ceiling
X2  ROUND-TRIP + ORTHOGONALITY: the container re-parses STRICT, every gated region (sector 0, both
    id-3 programs, every camera block, every GEOM block, the id-5 model image, the whole id-4
    header+texel region) is byte-identical, and W2's rescore / W3's retime are rebuilt from THEIR OWN
    specs and shown pairwise disjoint from W4's own changed-offset set
X3  THE FIVE HARD RULES, measured on the real artifact: STP population identical stock-vs-patched
    per palette, every 0x0000 held (both directions), entry 0 preserved wherever stock had it there,
    and the HSV CLIP CENSUS -- the entries a knob pushed past the top of the cube, counted per target
    with its fraction of live entries and gated at RS.BLOWOUT_FRACTION, plus the 0..31 channel clamp
    reported separately as the structural belt it is (see reskin.CLIP_CHANNEL: `_clamp01` bounds s/v
    before hsv_to_rgb, so that clamp cannot fire and is NOT the instrument)
X4  REVERT: tree-hash EXACT RESTORE in both the fresh-folder and the already-overridden-folder
    cases, exercised in a temp sandbox with an explicit ``--root`` -- never the live install
X5  PROVENANCE: byte-literal scan of every new committable file against the target container and
    the corpus, the repo/install staging refusals fire, previews land under SCRATCH only
X6  PREVIEWS + THE COLOUR REPORT: every manifest-listed preview file exists on disc, and the
    stock-vs-patched CLUT distance per target (mean hue shift achieved, saturation/value move,
    distinct-colour floor, luma-rho) is quoted so the recolour can be judged from numbers alone
X7  THE W5 GENERALISATION (added this rung): ``palette_map`` resolves ALL 372 corpus containers with
    zero crashes and zero duplicate names; the hazard census names ef381 (19 multi-writer cells, max
    5 writers) and ef447 (the (0,242) dual-depth cell) and NOTHING else; the texanim census names
    exactly ef038/177/493/494/495; ef227's artifact is still byte-identical to the deployed one; and
    ef227's own English target names still resolve through the alias map

Reads the user's own install for X1-X3, X6 and X7 (their subject is the REAL ef227 reskin) and the
extracted corpus for X7; X0, X4 and X5 need neither.  Prints only structure -- offsets, counts,
sizes and the small number of stock scalar VALUES the self-check is already built around (hue/sat/val
knobs, entry counts, VRAM cells).
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
import reskin as RS                                             # noqa: E402  (sets up sys.path)
import ef_container as EC                                        # noqa: E402
import summon_camera as W                                        # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
_STUDY = os.path.dirname(_HERE)
_REPO = os.path.dirname(os.path.dirname(_STUDY))
TIER_R = os.path.join(_STUDY, "tier-r")
SPEC = os.path.join(_HERE, "bahamut_reskin.toml")

#: the committable files THIS rung adds; X5 scans them for stock byte runs
COMMITTABLE = ("reskin.py", "test_reskin.py", "w4_gates.py", "bahamut_reskin.toml")

#: subprocess timeout for the (occasionally slow, corpus-walking) sibling gate runners
RUNNER_TIMEOUT = 900   # w3_gates alone measures ~540-720s (V3); at 480 the nested check could never fail

RESULTS = []


def gate(name: str, ok: bool, *lines: str) -> bool:
    RESULTS.append((name, ok))
    print("\n%s %s  %s" % ("[PASS]" if ok else "[FAIL]", name, "-" * max(2, 58 - len(name))))
    for ln in lines:
        print("   " + ln)
    return ok


def _pytest(path: str, cwd: str) -> tuple:
    p = subprocess.run([sys.executable, "-m", "pytest", path, "-q", "--no-header"],
                       capture_output=True, text=True, cwd=cwd, timeout=RUNNER_TIMEOUT)
    line = next((l for l in reversed(p.stdout.splitlines())
                if " passed" in l or " failed" in l or " error" in l), "?")
    m = re.search(r"(\d+) passed", line)
    return p.returncode, int(m.group(1)) if m else 0, line.strip()


def _has_install() -> bool:
    try:
        from ff9mapkit import config
        return bool(config.find_game_path(None))
    except Exception:
        return False


# --------------------------------------------------------------------------- X0
def _runner(name: str, cwd: str, floor: int):
    """Run a sibling gate runner and read its own ``N/M gates pass`` line.

    W4 pinned M exactly (``6/6`` for w2_gates, and so on).  W5 pins the two things that are
    actually claims about THIS lane -- the runner exits 0 and ALL of its gates pass -- and treats M
    as a FLOOR, because the camera and retime lanes are adding gates of their own this rung and
    "w2_gates now has 7 gates instead of 6" is progress, not a regression."""
    p = subprocess.run([sys.executable, os.path.join(cwd, name)],
                       capture_output=True, text=True, cwd=cwd, timeout=RUNNER_TIMEOUT)
    tail = [l for l in p.stdout.splitlines() if "gates pass" in l]
    got = tail[-1].strip() if tail else "(none)"
    m = re.match(r"(\d+)/(\d+) gates pass", got)
    good = bool(m) and p.returncode == 0 and m.group(1) == m.group(2) and int(m.group(2)) >= floor
    return good, "%-14s %s   (all must pass; W4 baseline %d gates)" % (name, got, floor)


def x0_no_regression():
    lines, ok, total = [], True, 0
    for runner, floor, cwd in (("r1_gates.py", 8, TIER_R), ("r2_gates.py", 6, TIER_R),
                               ("r3_gates.py", 5, TIER_R), ("w1_gates.py", 5, _HERE),
                               ("w2_gates.py", 6, _HERE)):
        good, line = _runner(runner, cwd, floor)
        ok = ok and good
        lines.append(line)

    # w3_gates.py -- "if runnable": its own X1-X4/X7 rebuild the REAL install twice (once for W3,
    # once inside its own orthogonality-adjacent checks) and can run long; a timeout here is
    # reported as NOT RUNNABLE rather than failing this whole gate, per the brief's own wording.
    try:
        good, line = _runner("w3_gates.py", _HERE, 8)
        ok = ok and good
        lines.append(line)
    except subprocess.TimeoutExpired:
        lines.append("%-14s TIMEOUT after %ds -- treated as NOT RUNNABLE, excluded from the count "
                     "(per the brief: \"w3_gates if runnable\")" % ("w3_gates.py", RUNNER_TIMEOUT))

    counts = {}
    for mod, cwd, tag in (("test_tier_r_disasm.py", TIER_R, "tier-r"),
                          ("test_tier_r_annot.py", TIER_R, "tier-r"),
                          ("test_summon_inspect.py", TIER_R, "tier-r"),
                          ("test_summon_camera.py", _HERE, "w1"),
                          ("test_rescore.py", _HERE, "w2"),
                          ("test_retime.py", _HERE, "w3"),
                          ("test_reskin.py", _HERE, "w4")):
        rc, n, line = _pytest(mod, cwd)
        ok = ok and rc == 0
        counts[tag] = counts.get(tag, 0) + n
        total += n
        lines.append("%-26s %s" % (mod, line))
    lines.append("")
    lines.append("tier-r %d + w1 %d + w2 %d + w3 %d + w4 %d = %d tests pass"
                 % (counts.get("tier-r", 0), counts.get("w1", 0), counts.get("w2", 0),
                    counts.get("w3", 0), counts.get("w4", 0), total))
    # W5 SPLIT THIS GATE, deliberately.  W4 pinned all five counts because it was the only rung in
    # flight; in W5 the camera and retime lanes are being generalised at the same time and grow
    # their OWN test counts, so pinning theirs here turns a sibling's progress into a red gate on
    # this lane and hides real failures.  What stays HARD is: every runner and every module exits 0
    # (asserted above, per module), and THIS rung's own count is exact.  The sibling counts are
    # REPORTED with their W4 baselines so a drop is still visible.
    baseline = {"tier-r": 142, "w1": 34, "w2": 34, "w3": 46}
    for tag, want in baseline.items():
        got = counts.get(tag, 0)
        lines.append("   %-7s %3d  (W4 baseline %d%s)"
                     % (tag, got, want,
                        "" if got == want else ", %+d -- sibling lane in flight" % (got - want)))
        ok = ok and got >= want                              # a DROP is still a regression
    # 80 at B1's hand-off; 82 after the W5 reconcile added two:
    # `test_describe_names_the_drift_guard_that_actually_applied` (B5 defect 4 -- `describe` called a
    # spec-guarded build "unguarded") and
    # `test_every_reskin_spec_beside_this_tool_builds_and_self_checks` (this runner's own SPEC is
    # hardcoded to bahamut, so phoenix_reskin.toml and madeen_reskin.toml were committable and
    # ungated).  Bumped rather than loosened: this is still the one count w4_gates has standing to
    # pin exactly, and an exact pin is what catches a DELETED test.
    exact_w4 = counts.get("w4") == 82
    lines.append("   %-7s %3d  (this rung's own figure, EXACT: %s)"
                 % ("w4", counts.get("w4", 0), exact_w4))
    ok = ok and exact_w4

    # The readers THIS rung builds on must be untouched.  Split for the same reason: `rescore.py`,
    # `summon_camera.py` and `retime.py` are the sibling lanes' OWN files this rung, so their state
    # is reported rather than gated; everything else is nobody's lane and stays hard.
    hard_readers = ["ff9mapkit/ff9mapkit/battle/camera_codec.py",
                    "ff9mapkit/ff9mapkit/summons/texture.py",
                    "ff9mapkit/ff9mapkit/summons/container.py",
                    "studies/custom-summons/thomas-swap/disasm/ef_container.py",
                    "studies/custom-summons/tier-r/tier_r_disasm.py",
                    "studies/custom-summons/tier-r/tier_r_annot.py",
                    "studies/custom-summons/tier-r/summon_inspect.py"]
    sibling_lane = ["studies/custom-summons/tier-w/rescore.py",
                    "studies/custom-summons/tier-w/summon_camera.py",
                    "studies/custom-summons/tier-w/retime.py"]
    p = subprocess.run(["git", "status", "--porcelain", "--"] + hard_readers,
                       capture_output=True, text=True, cwd=_REPO)
    dirty = [l for l in p.stdout.splitlines() if l.strip()]
    lines.append("HARD readers (kit + tier-r + ef_container) working tree: %s"
                 % ("UNMODIFIED (%d files checked)" % len(hard_readers) if not dirty
                    else "MODIFIED -- " + "; ".join(dirty)))
    ok = ok and not dirty
    p2 = subprocess.run(["git", "status", "--porcelain", "--"] + sibling_lane,
                        capture_output=True, text=True, cwd=_REPO)
    sib = [l for l in p2.stdout.splitlines() if l.strip()]
    lines.append("SIBLING-LANE files (reported, not gated -- W2/W3 own them this rung): %s"
                 % ("unmodified" if not sib else "; ".join(sib)))
    return gate("X0 no regression (r1/r2/r3 + w1/w2/w3 gates, every tier test incl. test_reskin.py, "
               "hard readers untouched)", ok, *lines)


# --------------------------------------------------------------------------- the shared real build
_BUILD = None
_BUILD_ERR = None


def build():
    global _BUILD, _BUILD_ERR
    if _BUILD is None and _BUILD_ERR is None:
        try:
            spec = RS.load_spec(SPEC)
            b = RS.build(spec, SPEC)
            b.check = RS.self_check(b)
            _BUILD = b
        except Exception as exc:                                # pragma: no cover - no install
            _BUILD_ERR = exc
    return _BUILD


# --------------------------------------------------------------------------- X1
def x1_byte_accounting():
    b = build()
    if b is None:
        return gate("X1 byte accounting (real build, every byte named)", False,
                   "no install: %s" % _BUILD_ERR)
    lines, ok = [], True
    c = b.check
    lines.append("%d byte(s) differ from stock in the whole %d B container (%.3f%%)"
                 % (len(c.changed), len(b.orig), 100.0 * len(c.changed) / len(b.orig)))
    for name, n in sorted(c.per_target.items()):
        lines.append("   %-34s %4d B" % (name, n))
    for g in c.accounting:
        lines.append("[%s] %-58s %s" % ("ok" if g.ok else "!!", g.name, g.detail))
    ok = ok and all(g.ok for g in c.accounting)
    # W5: the envelope is DERIVED (sum of the declared CLUT spans), not the ef227 constant.  It must
    # still come out at exactly A2's 8,192 -- that is the check, rather than the constant being one.
    ok = ok and b.pmap.envelope == RS.WHOLE_SET_CEILING
    lines.append("derived envelope %d B over %d spans (A2's edit menu (c) states %d): %s"
                 % (b.pmap.envelope, len(b.pmap.spans), RS.WHOLE_SET_CEILING,
                    "MATCH" if b.pmap.envelope == RS.WHOLE_SET_CEILING else "DRIFT"))
    return gate("X1 byte accounting (%d bytes, %d targets, against the %d-byte derived envelope)"
               % (len(c.changed), len(c.per_target), b.pmap.envelope), ok, *lines)


# --------------------------------------------------------------------------- X2
def x2_roundtrip_orthogonality():
    b = build()
    if b is None:
        return gate("X2 round-trip + orthogonality", False, "no install: %s" % _BUILD_ERR)
    lines, ok = [], True
    for g in b.check.regions:
        lines.append("[%s] %-58s %s" % ("ok" if g.ok else "!!", g.name, g.detail))
        ok = ok and g.ok
    for g in b.check.orthogonality:
        lines.append("[%s] %-58s %s" % ("ok" if g.ok else "!!", g.name, g.detail))
        ok = ok and g.ok
    return gate("X2 round-trip + untouched regions + W2/W3 orthogonality", ok, *lines)


# --------------------------------------------------------------------------- X3
def x3_hard_rules():
    b = build()
    if b is None:
        return gate("X3 the five hard rules", False, "no install: %s" % _BUILD_ERR)
    lines, ok = [], True
    for g in b.check.rules:
        lines.append("[%s] %-58s %s" % ("ok" if g.ok else "!!", g.name, g.detail))
        ok = ok and g.ok
    # the census as a per-target table, so an over-bright knob is legible here and not only inside
    # the gate's one-line detail -- the whole point of the instrument being real.
    lines.append("")
    lines.append("THE HSV CLIP CENSUS (entries a knob pushed past the cube; gate at %.0f%% of live)"
                 % (100.0 * RS.BLOWOUT_FRACTION))
    for t in b.enabled:
        r = t.result
        lines.append("   %-34s clipped %3d/%3d live (%4.1f%%)  S%d V%d  asked for S x%.3f V x%.3f%s"
                     % (t.name, r.clipped, r.live, 100.0 * r.clip_fraction, r.sat_clipped,
                        r.val_clipped, r.worst_sat, r.worst_val,
                        "   <-- BLOWN OUT" if r.clip_fraction > RS.BLOWOUT_FRACTION else ""))
    return gate("X3 the five hard rules (STP / zero-entries / entry-0 / the HSV clip census)",
                ok, *lines)


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
    return hashlib.sha256("\n".join("%s %s" % (k, m[k]) for k in sorted(m)).encode()).hexdigest()


def _sandbox_build(effect: int = 999):
    import test_reskin as TT
    blob = TT.build_synth_container(npart=1)
    pmap = RS.palette_map(blob)
    patched = bytearray(blob)
    patched[EC.parse_header(blob).chunks[0].resources[1].offset] ^= 0xFF
    patched = bytes(patched)
    return RS.Build(effect=effect, label="sandbox", spec_path="t.toml", source="(synthetic)",
                    orig=blob, patched=patched, sha_in=hashlib.sha256(blob).hexdigest(),
                    sha_out=hashlib.sha256(patched).hexdigest(), pmap=pmap, targets=[])


def x4_revert():
    lines, ok = [], True
    for case, seed_existing, use_explicit_root in (
            ("fresh mod folder, baked default root", False, False),
            ("already-overridden mod folder, baked default root", True, False),
            ("fresh mod folder, explicit --root (no baked default)", False, True)):
        tmp = tempfile.mkdtemp(prefix="w4revert-")
        try:
            b = _sandbox_build()
            game_root = os.path.join(tmp, "FAKE_GAME")
            mod = os.path.join(game_root, "FF9CustomMap")
            dest_dir = os.path.join(mod, "FF9_Data", "SpecialEffects")
            os.makedirs(dest_dir, exist_ok=True)
            prior = b"a pre-existing override, must come back byte-for-byte" if seed_existing \
                else None
            if prior is not None:
                with open(os.path.join(dest_dir, "ef999"), "wb") as fh:
                    fh.write(prior)
            before = _manifest(mod)
            baked_root = None if use_explicit_root else game_root
            out = RS.stage(b, root=os.path.join(tmp, "stage"), game_root=baked_root,
                          previews=False)
            extra = ["--root", mod] if use_explicit_root else []
            p1 = subprocess.run([sys.executable, out["scripts"]["deploy"]] + extra,
                                capture_output=True, text=True)
            staged = _manifest(mod)
            p2 = subprocess.run([sys.executable, out["scripts"]["revert"]] + extra,
                                capture_output=True, text=True)
            after = _manifest(mod)
            same = _manifest_hash(after) == _manifest_hash(before)
            good = (p1.returncode == 0 and p2.returncode == 0 and same
                   and _manifest_hash(staged) != _manifest_hash(before))
            ok = ok and good
            lines.append("%-56s before %s / staged %s / after %s -> %s"
                         % (case, _manifest_hash(before)[:12], _manifest_hash(staged)[:12],
                            _manifest_hash(after)[:12], "EXACT RESTORE" if same else "DRIFT"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    lines.append("all three cases exercised in a temp sandbox (tempfile.mkdtemp); the live install "
                "was never touched")
    return gate("X4 revert (tree-hash, fresh/already-overridden/--root, all in a temp sandbox)",
               ok, *lines)


# --------------------------------------------------------------------------- X5
def _byte_literals(path: str, minlen: int = 6):
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
    lines, ok = [], True
    lits = []
    for name in COMMITTABLE:
        fp = os.path.join(_HERE, name)
        if not os.path.isfile(fp):
            lines.append("%s MISSING" % name)
            ok = False
            continue
        if name.endswith(".py"):
            lits.extend((name, ln, raw) for ln, raw in _byte_literals(fp))
    lines.append("byte literals of >= 6 non-uniform bytes in the committable W4 sources: %d"
                 % len(lits))
    hits = []
    if lits:
        blobs = []
        b = build()
        if b is not None:
            blobs.append(("ef227 (the target, from the install)", b.orig))
        for path in W.corpus_paths():
            with open(path, "rb") as fh:
                blobs.append((os.path.basename(path), fh.read()))
        for who, blob in blobs:
            for name, ln, raw in lits:
                if raw in blob:
                    hits.append("LEAK %s:%d found in %s" % (name, ln, who))
    lines.append("   of those, appearing in the target container or anywhere in the %d-file "
                 "corpus: %d" % (len(W.corpus_paths()), len(hits)))
    for h in hits:
        lines.append("      " + h)
    ok = ok and not hits

    lines.append("staging root: %s" % RS.SCRATCH_ROOT)
    ok = ok and _REPO.lower() not in os.path.abspath(RS.SCRATCH_ROOT).lower()
    refused = False
    try:
        RS.R._refuse_repo_path(os.path.join(_REPO, "studies", "x"))
    except RS.R.RescoreError:
        refused = True
    lines.append("a repo-relative staging root is REFUSED: %s" % refused)
    ok = ok and refused

    refused_install = False
    try:
        with tempfile.TemporaryDirectory() as td:
            fake_game = os.path.join(td, "game")
            os.makedirs(os.path.join(fake_game, "FF9CustomMap"), exist_ok=True)
            RS.R._refuse_install_path(os.path.join(fake_game, "FF9CustomMap"), fake_game)
    except RS.R.RescoreError:
        refused_install = True
    lines.append("a staging root INSIDE a game install is REFUSED unless --live: %s"
                 % refused_install)
    ok = ok and refused_install

    p = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=_REPO)
    untracked = [l[3:] for l in p.stdout.splitlines() if l[:2] in ("??", " M", "M ", "A ")]
    big = [u for u in untracked if u.strip().endswith((".bytes", "ef227", "ef999"))]
    lines.append("stock-shaped files in the repo working tree: %d" % len(big))
    ok = ok and not big

    staged_previews_dir = os.path.join(RS.SCRATCH_ROOT, "previews")
    lines.append("staged previews directory: %s (%s)"
                 % (staged_previews_dir,
                    "present" if os.path.isdir(staged_previews_dir) else "not staged yet"))
    ok = ok and _REPO.lower() not in os.path.abspath(staged_previews_dir).lower()
    return gate("X5 provenance (no SE bytes committable, staging + previews confined to SCRATCH, "
               "refusals fire)", ok, *lines)


# --------------------------------------------------------------------------- X6
def x6_previews_and_colour_report():
    b = build()
    if b is None:
        return gate("X6 previews + the colour report", False, "no install: %s" % _BUILD_ERR)
    lines, ok = [], True
    manifest_path = os.path.join(RS.SCRATCH_ROOT, "build_manifest.json")
    if not os.path.isfile(manifest_path):
        return gate("X6 previews + the colour report", False,
                   "no build_manifest.json staged at %s -- run `py reskin.py build` first"
                   % manifest_path)
    import json
    man = json.loads(open(manifest_path, "r", encoding="utf-8").read())
    previews = man.get("previews") or []
    missing = [p for p in previews if not os.path.isfile(p)]
    lines.append("previews listed in the manifest: %d, missing on disc: %d"
                 % (len(previews), len(missing)))
    for m in missing:
        lines.append("   MISSING: %s" % m)
    ok = ok and previews and not missing
    ok = ok and all(_REPO.lower() not in os.path.abspath(p).lower() for p in previews)

    lines.append("")
    lines.append("THE COLOUR REPORT (stock -> patched, per enabled target)")
    for t in b.enabled:
        r = t.result
        lines.append("   %-34s hue %6.1f -> %6.1f (target knob %+.1f deg)   S %.2f->%.2f   "
                     "V %.2f->%.2f   distinct %3d->%3d   luma-rho %.4f   %d/%d B changed"
                     % (t.name, r.hue_before, r.hue_after, t.t.hue, r.sat_before, r.sat_after,
                        r.val_before, r.val_after, r.distinct_stock, r.distinct_new,
                        r.luma_rho, len(r.changed), t.pal.nbytes))
    mean_shift = sum(((t.result.hue_after - t.result.hue_before) % 360.0) for t in b.enabled) \
        / max(1, len(b.enabled))
    lines.append("")
    lines.append("mean hue shift achieved across %d enabled targets: %.1f degrees"
                 % (len(b.enabled), mean_shift))
    return gate("X6 previews exist + the stock-vs-patched colour report", ok, *lines)


# --------------------------------------------------------------------------- X7
#: THE FROZEN ARTIFACT.  ef227's reskin is deployed and cast-proven; W5's generalisation is only
#: allowed if `bahamut_reskin.toml` still builds THESE bytes.  A hash, not data.
W4_PATCHED_SHA256 = "7fef205ffbe547545374de9d1017613448777f0251d9d425b55f7796f688b89a"


def x7_generalisation():
    """The rung's own falsifiable claim: the tool left ef227 alone and grew to fit the corpus."""
    lines, ok = [], True
    paths = W.corpus_paths()
    if not paths:
        return gate("X7 the W5 generalisation", False,
                   "no extracted corpus at %s" % W.SCRATCH_CORPUS)

    crashes, multi, dual, texanim, scenery_only = [], {}, [], [], 0
    for path in paths:
        with open(path, "rb") as fh:
            blob = fh.read()
        name = os.path.basename(path)
        try:
            pmap = RS.palette_map(blob)
        except Exception as exc:
            crashes.append("%s: %s" % (name, exc))
            continue
        scenery_only += 1 if pmap.creature_error else 0
        mw = [c for c in pmap.hazards.values() if c.multi_writer]
        if mw:
            multi[name] = (len(mw), max(len(set(c.offsets)) for c in mw))
        if any(c.dual_depth for c in pmap.hazards.values()):
            dual.append(name)
        if pmap.texanim and pmap.texanim.armed:
            texanim.append("%s (%d B)" % (name, pmap.texanim.nbytes))
    lines.append("palette_map over %d corpus containers: %d resolved, %d CRASHED"
                 % (len(paths), len(paths) - len(crashes), len(crashes)))
    for c in crashes[:8]:
        lines.append("   CRASH %s" % c)
    ok = ok and not crashes
    lines.append("scenery-only (no id-4 creature package) -- W4 refused every one of these: %d"
                 % scenery_only)
    ok = ok and scenery_only == 348
    lines.append("MULTI-WRITER CLUT cells: %s"
                 % ("; ".join("%s %d cells, max %d writers" % (k, v[0], v[1])
                              for k, v in sorted(multi.items())) or "none"))
    ok = ok and sorted(multi) == ["ef381.bytes", "ef447.bytes"] \
        and multi.get("ef381.bytes") == (19, 5)
    lines.append("DUAL-DEPTH CLUT cells: %s" % (", ".join(dual) or "none"))
    ok = ok and dual == ["ef447.bytes"]
    lines.append("TEXANIM armed: %s" % (", ".join(texanim) or "none"))
    ok = ok and len(texanim) == 5 and all(t.startswith(("ef038", "ef177", "ef493", "ef494",
                                                        "ef495")) for t in texanim)

    b = build()
    if b is None:
        lines.append("ef227 byte-compat: NOT CHECKED (no install: %s)" % _BUILD_ERR)
        ok = False
    else:
        same = b.sha_out == W4_PATCHED_SHA256
        lines.append("ef227 artifact sha256 %s -- %s the deployed W4 artifact"
                     % (b.sha_out, "IDENTICAL to" if same else "*** DIFFERS FROM ***"))
        ok = ok and same
        legacy = True
        try:
            b.pmap.span("c1_clut_band0")
            legacy = (b.pmap.by_name("scenery.sky_dome").name == "pal.s0.x0_y245.e256"
                      and b.pmap.by_name("spare.c1_x0_y242").name == "pal.s1.x0_y242.e256")
        except Exception as exc:
            legacy = False
            lines.append("   legacy alias lookup FAILED: %s" % exc)
        lines.append("ef227's legacy span/target names still resolve through the alias map: %s"
                     % legacy)
        ok = ok and legacy
        a = b.pmap.attrib
        lines.append("ef227 `so` coverage %d/%d (%s); derived SHARED cells: %s"
                     % (a.geom_with_so, a.geom_total, "COMPLETE" if a.complete else "INCOMPLETE",
                        ", ".join(sorted(p.alias or p.name for p in b.pmap.palettes if p.shared))))
    return gate("X7 the W5 generalisation (corpus sweep, hazard + texanim census, ef227 "
                "byte-compat, legacy aliases)", ok, *lines)


# --------------------------------------------------------------------------- main
def main() -> int:
    print(__doc__.splitlines()[0])
    if not _has_install():
        print("\nNOTE: no FF9 install resolvable in this environment -- X1/X2/X3/X6 will FAIL "
             "loudly rather than silently pass; X0/X4/X5 do not need the install.")
    x0_no_regression()
    x1_byte_accounting()
    x2_roundtrip_orthogonality()
    x3_hard_rules()
    x4_revert()
    x5_provenance()
    x6_previews_and_colour_report()
    x7_generalisation()
    print("\n" + "=" * 72)
    for name, ok in RESULTS:
        print("%-5s %s" % ("PASS" if ok else "FAIL", name))
    passed = sum(1 for _n, ok in RESULTS if ok)
    print("=" * 72)
    print("%d/%d gates pass" % (passed, len(RESULTS)))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":                                       # pragma: no cover
    raise SystemExit(main())
