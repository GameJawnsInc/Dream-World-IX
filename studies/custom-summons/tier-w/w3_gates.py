r"""TIER W rung 3 -- the gate runner.  `py w3_gates.py` prints X0..X7 with numbers and PASS/FAIL.

X0  NO REGRESSION: r1/r2/r3, w1_gates, w2_gates, and EVERY tier-r/tier-w test module still pass,
    at or ABOVE their W3 baselines (tier-r 142 + w1 34 + w2 34 + w3 46), and the readers W5 does
    NOT touch (summon_camera.py, camera_codec.py, w3_program_edits.py, w3_clock_emu.py,
    ef_container.py, the kit summons modules, the tier-r tools) are IMPORTED, never edited.
    RELAXED IN W5 -- see the long note on :func:`x0_no_regression`.
X1  BYTE ACCOUNTING: both artifacts, four domains (E1 program / E2 sequence / E3 camera / E4 text),
    every changed byte named down to the field, 0 unexplained, 0 in a duration field
X2  ROUND-TRIP: both containers re-parse strict, every camera block round-trips byte-exact through
    the UNMODIFIED codec, and W1's four block invariants hold on the edited block
X3  THE ALIGNMENT CHECKER: on the REAL ef227 build, every lock pair keeps its lead in ALIGNED and
    every c0 post-cut pair drifts by exactly N while every c1 pair stays put in MIS-RETIME; then,
    independently, the checker is shown FALSIFIABLE on ``test_retime.py``'s synthetic two-clock
    fixture (a clean retime passes, a deliberate 1-tick error fails it)
X4  THE EMULATOR INVARIANTS: ``w3_clock_emu.audit()``'s own battery (B0's proof) and
    ``retime.emulator_gate``'s battery (run against both staged containers), both 0 failures
X5  REVERT: tree-hash exact restore in BOTH the fresh-folder and the already-overridden-folder
    cases, actually exercised in a temp sandbox -- never the live install
X6  PROVENANCE: byte-literal scan of every new committable file against the target container and
    the corpus (W1e/W2 X5 style), staging confined to SCRATCH, the repo-path refusal fires
X7  THE TEXT CO-RETIME: the stock sha guard on ``Sequence.seq``, exactly one ``Wait`` line changed
    (by the retime's own delta), and the ``PlayerSequence.seq`` audit verdict recorded

Reads the user's own install for X1-X4 and X7 (their subject is the REAL ef227 retime); X0, X5 and
X6 need neither.  Prints only structure -- offsets, counts, sizes, and the small number of stock
scalar VALUES the self-check is already built around (thresholds, WAIT times, frame numbers).
"""
from __future__ import annotations

import ast
import hashlib
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import retime as T                                              # noqa: E402  (sets up sys.path)
import w3_clock_emu as EMU                                      # noqa: E402
import w3_program_edits as PE                                   # noqa: E402
import summon_camera as W                                       # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
_STUDY = os.path.dirname(_HERE)
_REPO = os.path.dirname(os.path.dirname(_STUDY))
TIER_R = os.path.join(_STUDY, "tier-r")
SPEC = os.path.join(_HERE, "bahamut_retime.toml")

#: the committable files THIS lane adds; X6 scans them for stock byte runs (W1e/W2-X5's own rule).
#: W5 EXTENDS the list with the retime lane's two new sources -- a file that is committable and NOT
#: scanned is exactly the hole this gate exists to close, and "it was added by a later rung" is not
#: a provenance exemption.
COMMITTABLE = ("retime.py", "w3_clock_emu.py", "w3_program_edits.py", "test_retime.py",
               "w3_gates.py", "bahamut_retime.toml", "retime_derive.py", "test_retime_derive.py")

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


def _has_install() -> bool:
    try:
        from ff9mapkit import config
        return bool(config.find_game_path(None))
    except Exception:
        return False


# --------------------------------------------------------------------------- X0
def _runner(name: str, cwd: str, floor: int):
    """Run a sibling gate runner and read its own ``N/M gates pass`` line.

    W3 pinned the WHOLE STRING (``got.startswith("6/6")``), which made a sibling lane ADDING a gate
    indistinguishable from a sibling lane BREAKING one.  W5 generalises w2_gates (6 -> 8 gates:
    the ``init`` scaffold and the dynamic-op disclosure each brought their own), so the string pin
    now fires on progress.  What is asserted instead is the pair of claims that are actually about
    regression: the runner exits 0 AND every one of its gates passed (``N == M``), with M held to
    the W3 baseline as a FLOOR so a gate that DISAPPEARS is still caught."""
    p = subprocess.run([sys.executable, os.path.join(cwd, name)],
                       capture_output=True, text=True, cwd=cwd)
    tail = [l for l in p.stdout.splitlines() if "gates pass" in l]
    got = tail[-1].strip() if tail else "(none)"
    m = re.match(r"(\d+)/(\d+) gates pass", got)
    good = bool(m) and p.returncode == 0 and m.group(1) == m.group(2) and int(m.group(2)) >= floor
    return good, "%-14s %s   (all must pass; W3 baseline %d gates -- a FLOOR)" % (name, got, floor)


def x0_no_regression():
    lines, ok, total = [], True, 0
    for runner, floor, cwd in (("r1_gates.py", 8, TIER_R), ("r2_gates.py", 6, TIER_R),
                               ("r3_gates.py", 5, TIER_R), ("w1_gates.py", 5, _HERE),
                               ("w2_gates.py", 6, _HERE)):
        good, line = _runner(runner, cwd, floor)
        ok = ok and good
        lines.append(line)
    counts = {}
    for mod, cwd, tag in (("test_tier_r_disasm.py", TIER_R, "tier-r"),
                          ("test_tier_r_annot.py", TIER_R, "tier-r"),
                          ("test_summon_inspect.py", TIER_R, "tier-r"),
                          ("test_summon_camera.py", _HERE, "w1"),
                          ("test_rescore.py", _HERE, "w2"),
                          ("test_retime.py", _HERE, "w3")):
        rc, n, line = _pytest(mod, cwd)
        ok = ok and rc == 0
        counts[tag] = counts.get(tag, 0) + n
        total += n
        lines.append("%-26s %s" % (mod, line))
    lines.append("")
    lines.append("tier-r %d + w1 %d + w2 %d + w3 %d = %d tests pass"
                 % (counts.get("tier-r", 0), counts.get("w1", 0), counts.get("w2", 0),
                    counts.get("w3", 0), total))
    # W5 RELAXATION -- exact counts became FLOORS.
    #
    # W3 pinned `w2 == 34` and `w1 == 34` because W3 was the only rung in flight and any movement in
    # a sibling's test count meant somebody had edited a file they did not own.  In W5 the camera
    # (rescore.py/test_rescore.py) and retime (retime.py/test_retime.py) lanes are BOTH being
    # generalised, by design, so their counts grow on purpose (both roughly doubled).  An equality
    # pin here turns a sibling's new test into a red gate on this lane, which is exactly the failure
    # mode that trains an agent to delete gates.  The live numbers are PRINTED below, not pinned --
    # per CLAUDE.md's rule that a test count has exactly one owner.
    #
    # It stays FALSIFIABLE, not a no-op: every module must still exit 0 (asserted per module above,
    # `ok = ok and rc == 0`), and each count is held to its W3 baseline as a FLOOR -- a test that
    # DISAPPEARS still fails this gate, which is the regression the pin was really guarding.
    baseline = {"tier-r": 142, "w1": 34, "w2": 34, "w3": 46}
    for tag in ("tier-r", "w1", "w2", "w3"):
        want, got = baseline[tag], counts.get(tag, 0)
        lines.append("   %-7s %3d  (W3 baseline %d, FLOOR: %s%s)"
                     % (tag, got, want, got >= want,
                        "" if got == want else "; %+d -- lane generalised in W5" % (got - want)))
        ok = ok and got >= want

    # The readers must be untouched -- but W5 SPLIT this check by ownership, for the same reason.
    #
    # HARD: the files W5 does not touch at all.  `git status --porcelain` over them must be empty.
    # This list now INCLUDES w3_program_edits.py and w3_clock_emu.py: in W3 they were B0's brand-new
    # uncommitted deliverables, so `??` said nothing about whether this rung had edited them and the
    # gate fell back to a write-pattern grep.  They have since been committed, so git has a real
    # baseline and the strong instrument applies.  The grep is KEPT as a second, independent
    # instrument (a source that writes to them at RUN time would not show in git status until after
    # the damage).  ef_container.py and the two kit summons modules join the list: reskin.py reads
    # both this rung and neither may be edited from tier-w.
    hard_readers = ["studies/custom-summons/tier-w/summon_camera.py",
                    "studies/custom-summons/tier-w/w3_program_edits.py",
                    "studies/custom-summons/tier-w/w3_clock_emu.py",
                    "ff9mapkit/ff9mapkit/battle/camera_codec.py",
                    "ff9mapkit/ff9mapkit/summons/texture.py",
                    "ff9mapkit/ff9mapkit/summons/container.py",
                    # the promotion moved summon_camera's implementation here; the tier-w file is a
                    # shim, so the ACTUAL reader must be watched or this check is fail-open (B7).
                    "ff9mapkit/ff9mapkit/summons/camera.py",
                    "studies/custom-summons/thomas-swap/disasm/ef_container.py",
                    "studies/custom-summons/tier-r/tier_r_disasm.py",
                    "studies/custom-summons/tier-r/tier_r_annot.py",
                    "studies/custom-summons/tier-r/summon_inspect.py"]
    # SIBLING-LANE: rescore.py and reskin.py are B2's and B1's OWN files this rung (and retime.py is
    # this lane's own tool, generalised by B3).  Their working-tree state is REPORTED, never gated --
    # w3_gates has no standing to call a modification to a file another lane owns a regression.  The
    # claim that their behaviour did not regress is carried by test_rescore/test_reskin/test_retime
    # and by w2_gates/w4_gates above, all of which are still hard-gated here.
    sibling_lane = ["studies/custom-summons/tier-w/rescore.py",
                    "studies/custom-summons/tier-w/reskin.py",
                    "studies/custom-summons/tier-w/retime.py"]
    p = subprocess.run(["git", "status", "--porcelain", "--"] + hard_readers,
                       capture_output=True, text=True, cwd=_REPO)
    dirty = [l for l in p.stdout.splitlines() if l.strip()]
    lines.append("HARD readers (kit + tier-r + ef_container + the frozen W3 record): %s"
                 % ("UNMODIFIED (%d files checked)" % len(hard_readers) if not dirty
                    else "MODIFIED -- " + "; ".join(dirty)))
    ok = ok and not dirty

    frozen_w3 = ["w3_program_edits.py", "w3_clock_emu.py"]
    new_sources = ("test_retime.py", "w3_gates.py", "retime_derive.py", "test_retime_derive.py")
    write_hits = []
    for name in frozen_w3:
        for src in new_sources:
            fp = os.path.join(_HERE, src)
            if not os.path.isfile(fp):
                continue
            text = open(fp, "r", encoding="utf-8").read()
            for pat in ("open(%r, \"w" % name, "open('%s', 'w" % name, name + '.write',
                       "Path(%r)" % name):
                if pat in text and ("write" in pat or "w\"" in pat or "w'" in pat):
                    write_hits.append("%s references %r near a write pattern" % (src, name))
    lines.append("no write-pattern hit against %s in this lane's own sources %s: %s"
                 % (frozen_w3, list(new_sources), not write_hits))
    ok = ok and not write_hits

    p2 = subprocess.run(["git", "status", "--porcelain", "--"] + sibling_lane,
                        capture_output=True, text=True, cwd=_REPO)
    sib = [l for l in p2.stdout.splitlines() if l.strip()]
    lines.append("SIBLING-LANE files (REPORTED, not gated -- W5's B1/B2/B3 own them this rung): %s"
                 % ("unmodified" if not sib else "; ".join(l.strip() for l in sib)))
    return gate("X0 no regression (r1/r2/r3 + w1/w2 gates, every tier test at or above its W3 "
               "floor, hard readers untouched)", ok, *lines)


# --------------------------------------------------------------------------- the shared real build
_BUILD = None
_BUILD_ERR = None


def build():
    global _BUILD, _BUILD_ERR
    if _BUILD is None and _BUILD_ERR is None:
        try:
            from ff9mapkit import config
            spec = T.load_spec(SPEC)
            game_root = config.find_game_path(None)
            b = T.build_containers(spec, SPEC)
            b.text = T.build_text_edit(spec, game_root)
            b.player = T.audit_player_sequence(spec, game_root)
            b.check = T.self_check(b)
            _BUILD = b
        except Exception as exc:                                # pragma: no cover - no install
            _BUILD_ERR = exc
    return _BUILD


# --------------------------------------------------------------------------- X1
def x1_byte_accounting():
    b = build()
    if b is None:
        return gate("X1 byte accounting (both artifacts, four domains)", False,
                   "no install: %s" % _BUILD_ERR)
    lines, ok = [], True
    for rep in (b.check.bytes_aligned, b.check.bytes_mis):
        lines.append("%s: %d byte(s) differ from stock in the whole %d B container"
                     % (rep.tag, len(rep.changed), len(b.orig)))
        for tag, offs in sorted(rep.by_domain.items()):
            if offs:
                lines.append("     %s: %d byte(s)" % (tag, len(offs)))
        lines.append("     unexplained: %d   in a duration field: %d"
                     % (len(rep.unexplained), len(rep.duration_hits)))
        ok = ok and rep.ok
    lines.append("ALIGNED minus MIS-RETIME == the program edit set: %s" % b.check.difference_ok)
    lines.append("   %s" % b.check.difference_detail)
    ok = ok and b.check.difference_ok
    if b.text:
        lines.append("E4 text (the fourth domain): stock sha %s -> edited sha %s, 1 Wait line "
                     "changed, %d downstream beats shift +%d"
                     % (b.text.stock_sha[:16], b.text.new_sha[:16], b.text.moved_beats,
                        b.text.delta))
        ok = ok and b.text.moved_beats > 0
    else:
        ok = False
        lines.append("E4 text: NOT BUILT (no install)")
    return gate("X1 byte accounting (both artifacts, four domains, every byte named)", ok, *lines)


# --------------------------------------------------------------------------- X2
def x2_roundtrip():
    b = build()
    if b is None:
        return gate("X2 round-trip + W1 invariants", False, "no install: %s" % _BUILD_ERR)
    lines, ok = [], True
    for tag, (good, cur, rt_ok, tot, inv) in sorted(b.check.roundtrip.items()):
        lines.append("%-11s strict re-parse cursor_end %#x == size %#x : %s"
                     % (tag, cur, len(b.aligned), cur == len(b.aligned)))
        lines.append("%-11s camera blocks byte-exact through the UNMODIFIED codec: %d/%d"
                     % ("", rt_ok, tot))
        for k, v in sorted(inv.items()):
            lines.append("%-11s %-42s %s" % ("", k, v))
        ok = ok and good
    return gate("X2 round-trip + W1's four invariants on both edited containers", ok, *lines)


# --------------------------------------------------------------------------- X3
def x3_alignment():
    b = build()
    if b is None:
        return gate("X3 the alignment checker", False, "no install: %s" % _BUILD_ERR)
    al = b.check.alignment
    lines, ok = [], al.ok
    for ok_, tag, detail in al.findings:
        lines.append("[%s] %-52s %s" % ("PASS" if ok_ else "FAIL", tag, detail))
    c0_post = [r for r in al.stock if r.ident.slot == 0 and r.cam >= al.cut_tick]
    c1_rows = [r for r in al.stock if r.ident.slot != 0]
    drift_ok = bool(c0_post) and all(al.misretime[r.ident].lead - r.lead == al.n for r in c0_post)
    c1_ok = bool(c1_rows) and all(al.misretime[r.ident].lead == r.lead for r in c1_rows)
    lines.append("")
    lines.append("c0 post-cut pairs drift by exactly N=%+d in MIS-RETIME: %s (%d pairs)"
                 % (al.n, drift_ok, len(c0_post)))
    lines.append("c1 pairs are UNCHANGED in MIS-RETIME: %s (%d pairs)" % (c1_ok, len(c1_rows)))
    ok = ok and drift_ok and c1_ok

    # THE FALSIFIABILITY PROOF -- imported from test_retime.py's synthetic fixture, not re-derived
    import test_retime as TT
    (stock, aligned, misretime, syn_n, cut_tick, cut_local, shot0,
     frame_edits) = TT._split_fixture_edits()
    al_good = T.check_alignment(stock, aligned, misretime, syn_n, cut_tick, cut_local,
                               (shot0.slot, shot0.index), "synth", stretched=("synth:c0", 0))
    bad_edit = frame_edits[0]
    bad_word = struct.pack("<H", bad_edit.new_word + 1)
    bad_aligned = T.apply_writes(aligned, [(bad_edit.site.file_off, bad_word, "1-tick error")])
    al_bad = T.check_alignment(stock, bad_aligned, misretime, syn_n, cut_tick, cut_local,
                              (shot0.slot, shot0.index), "synth", stretched=("synth:c0", 0))
    lines.append("")
    lines.append("FALSIFIABILITY (test_retime.py's synthetic two-clock fixture, N=%+d): a clean "
                 "retime .ok=%s; a deliberate 1-tick error .ok=%s" % (syn_n, al_good.ok, al_bad.ok))
    ok = ok and al_good.ok and not al_bad.ok
    return gate("X3 the alignment checker (aligned leads preserved / misretime drifts exactly "
               "%+d on c0 only)" % al.n, ok, *lines)


# --------------------------------------------------------------------------- X4
def x4_emulator():
    b = build()
    lines, ok = [], True
    audit = EMU.audit()                                          # B0's own standalone proof
    lines.append("w3_clock_emu.audit() (B0's own proof, standalone): %d checks, %d failures"
                 % (len(audit.findings), len(audit.failures)))
    for f in audit.failures:
        lines.append("   %s" % f)
    ok = ok and audit.ok
    if b is not None:
        fails = [f for f in b.check.emu if not f.ok]
        lines.append("retime.emulator_gate(build) (run against BOTH staged containers): %d "
                     "checks, %d failures" % (len(b.check.emu), len(fails)))
        for f in fails:
            lines.append("   %s" % f)
        ok = ok and not fails
    else:
        lines.append("retime.emulator_gate: SKIPPED (no install: %s)" % _BUILD_ERR)
        ok = False
    return gate("X4 the emulator invariants (B0 standalone + the build's own gate)", ok, *lines)


# --------------------------------------------------------------------------- X5
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


def x5_revert():
    import test_retime as TT
    lines, ok = [], True
    for case, seed_existing in (("fresh mod folder", False),
                                ("mod folder already carrying an override", True)):
        tmp = tempfile.mkdtemp(prefix="w3revert-")
        try:
            b = TT._minimal_synth_build()
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
            out = T.stage(b, root=os.path.join(tmp, "stage"), game_root=game_root)
            p1 = subprocess.run([sys.executable, out["scripts"]["deploy_aligned"]],
                                capture_output=True, text=True)
            staged = _manifest(mod)
            p2 = subprocess.run([sys.executable, out["scripts"]["revert"]],
                                capture_output=True, text=True)
            after = _manifest(mod)
            same = _manifest_hash(after) == _manifest_hash(before)
            good = p1.returncode == 0 and p2.returncode == 0 and same and \
                _manifest_hash(staged) != _manifest_hash(before)
            ok = ok and good
            lines.append("%-46s before %s / staged %s / after %s -> %s"
                         % (case, _manifest_hash(before)[:12], _manifest_hash(staged)[:12],
                            _manifest_hash(after)[:12], "EXACT RESTORE" if same else "DRIFT"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    lines.append("both cases exercised in a temp sandbox (tempfile.mkdtemp); the live install was "
                "never touched")
    return gate("X5 revert (tree-hash, fresh AND already-overridden, in a temp sandbox)", ok, *lines)


# --------------------------------------------------------------------------- X6
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


def x6_provenance():
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
    lines.append("byte literals of >= 6 non-uniform bytes in the committable W3 sources: %d"
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

    lines.append("staging root: %s" % T.SCRATCH_ROOT)
    ok = ok and _REPO.lower() not in os.path.abspath(T.SCRATCH_ROOT).lower()
    refused = False
    try:
        T.R._refuse_repo_path(os.path.join(_REPO, "studies", "x"))
    except T.R.RescoreError:
        refused = True
    lines.append("a repo-relative staging root is REFUSED: %s" % refused)
    ok = ok and refused

    refused_install = False
    try:
        import tempfile as _tf
        with _tf.TemporaryDirectory() as td:
            fake_game = os.path.join(td, "game")
            os.makedirs(os.path.join(fake_game, "FF9CustomMap"), exist_ok=True)
            T.R._refuse_install_path(os.path.join(fake_game, "FF9CustomMap"), fake_game)
    except T.R.RescoreError:
        refused_install = True
    lines.append("a staging root INSIDE a game install is REFUSED unless --live: %s"
                 % refused_install)
    ok = ok and refused_install

    p = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=_REPO)
    untracked = [l[3:] for l in p.stdout.splitlines() if l[:2] in ("??", " M", "M ", "A ")]
    big = [u for u in untracked if u.strip().endswith((".bytes", "ef227", "ef999"))]
    lines.append("stock-shaped files in the repo working tree: %d" % len(big))
    ok = ok and not big
    return gate("X6 provenance (no SE bytes committable, staging confined to SCRATCH, refusals "
               "fire)", ok, *lines)


# --------------------------------------------------------------------------- X7
def x7_text_co_retime():
    b = build()
    if b is None or b.text is None:
        return gate("X7 the text co-retime", False, "no install: %s" % _BUILD_ERR)
    t, lines, ok = b.text, [], True
    lines.append("stock sha256 guard on Sequence.seq: %s (matched, or build_text_edit itself "
                "would have refused)" % t.stock_sha[:16])
    lines.append("Wait #%d (file line %d): Time=%d -> %d  (spans outer tick %d -> %d, containing "
                "the boundary %d)" % (t.anchor.index, t.anchor.line_no + 1, t.anchor.time,
                                       t.new_time, t.anchor.start, t.anchor.end, t.boundary))
    plus = [l for l in t.diff.splitlines() if l.startswith("+") and not l.startswith("+++")]
    minus = [l for l in t.diff.splitlines() if l.startswith("-") and not l.startswith("---")]
    lines.append("unified diff: %d line(s) removed, %d line(s) added (must be exactly 1 and 1)"
                 % (len(minus), len(plus)))
    ok = ok and len(minus) == 1 and len(plus) == 1
    lines.append("%d downstream Wait beats shift by the retime's own delta (+%d); the file's own "
                "end moves %d -> %d" % (t.moved_beats, t.delta, t.stock_total, t.new_total))
    ok = ok and t.moved_beats > 0 and (t.new_total - t.stock_total == t.delta)
    if b.player:
        lines.append("")
        lines.append("PlayerSequence.seq audit verdict: %s" % b.player.verdict)
        # `.ok` (clean OR legitimately acknowledged), not `not needs_retime` -- V2's finding: the
        # bare form would fail X7 on a spec whose drift is stated via acknowledge_uncoretimed.
        ok = ok and b.player.ok
    else:
        ok = False
        lines.append("PlayerSequence.seq audit: NOT RUN")
    return gate("X7 the text co-retime (stock sha guard / exactly 1 Wait line changed / "
               "PlayerSequence verdict)", ok, *lines)


# --------------------------------------------------------------------------- main
def main() -> int:
    print(__doc__.splitlines()[0])
    if not _has_install():
        print("\nNOTE: no FF9 install resolvable in this environment -- X1/X2/X3/X4/X7 will FAIL "
             "loudly rather than silently pass; X0/X5/X6 do not need the install.")
    x0_no_regression()
    x1_byte_accounting()
    x2_roundtrip()
    x3_alignment()
    x4_emulator()
    x5_revert()
    x6_provenance()
    x7_text_co_retime()
    print("\n" + "=" * 72)
    for name, ok in RESULTS:
        print("%-5s %s" % ("PASS" if ok else "FAIL", name))
    passed = sum(1 for _n, ok in RESULTS if ok)
    print("=" * 72)
    print("%d/%d gates pass" % (passed, len(RESULTS)))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":                                       # pragma: no cover
    raise SystemExit(main())
