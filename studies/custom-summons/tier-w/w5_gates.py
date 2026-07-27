r"""TIER W rung 5 -- THE RUNG'S OWN GATE RUNNER.  `py w5_gates.py` prints G1..G9 with PASS/FAIL.

Where B1/B2/B3's own ``w4_gates.py`` / ``w2_gates.py`` / ``w3_gates.py`` prove ONE lane still holds
ef227, this runner proves the RUNG's own falsifiable claim: the three generalised lanes hold together
on the SECOND effect (Phoenix, ef211) and the corpus at large, without moving one of ef227's bytes.
Nine gates, each named in the brief:

G1  CORPUS NO-CRASH SWEEP: ``w_survey.corpus_sweep`` resolves all 372 extracted containers with zero
    exceptions (every detector this rung's survey calls -- ``reskin.palette_map``, the op-25 census,
    ``summon_camera.extract_shots``, the twin-texture hash -- runs clean corpus-wide)
G2  EF227 BYTE-COMPAT ACROSS LANES: rebuilding ``bahamut_reskin.toml`` still produces the exact
    deployed, cast-proven artifact (a pinned sha256); rebuilding ``bahamut_rescore.toml`` and
    ``bahamut_retime.toml`` still pass THEIR OWN self-checks against the real install
G3' THE FIVE TEXANIM LIFTS (was `THE FIVE TEXANIM REFUSALS` -- INVERTED at W7, see `W7-TEXANIM.md`):
    enabling a CREATURE target on each of ef038/177/493/494/495 now BUILDS, and the texanim region
    comes back BYTE-IDENTICAL with `firstBlock` / `min(motionOffsets)` unmoved (THE REGION INVARIANT)
G4  EF381 / EF447 REFUSALS: enabling one (of several) MULTI-WRITER cell writers on ef381 refuses
    naming the missing writers; enabling the DUAL-DEPTH cell on ef447 refuses outright, no key
G5  HEADROOM REFUSAL: a `value > 1.0` on any of ef211's six zero-headroom creature rows refuses
    without `acknowledge_headroom`
G6  EF000 CAMERA REFUSAL: the dynamic-op disclosure gate fires on the real ef000 (all three W2/W5
    traps) without `acknowledge_dynamic_ops`, and the SAME edit builds clean with it
G7  EF211 SCAFFOLD + BUILD CLEAN: `reskin.scaffold(211, ...)` emits a spec that builds with ZERO
    changed bytes (every knob starts at identity) and passes its own self-check
G8  RETIME IDENTITY GATE ON ef211:c0: for every state `retime_derive.analyse_target` recovers as
    DERIVABLE, `assert_identity` (build_edits at N=0) reproduces the container's own stock bytes;
    every REFUSED state is reported by name, never silently dropped
G9  SURVEY SELF-CHECK: ``w_survey.self_check`` -- the texanim class, the two hazard classes, the
    op-25-drawn/never-drawn split and the three twin-texture groups all still match the corpus

Reads the user's own install for G2 (its subject is the REAL ef227 artifacts) and the extracted
corpus for everything else.  NO deploy, NO install write, NO git commit -- offline gates only.
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import w_survey as SV                                             # noqa: E402  (sets up sys.path)
import reskin as RS                                                # noqa: E402
import rescore as R                                                # noqa: E402
import retime as RT                                                # noqa: E402
import retime_derive as RD                                         # noqa: E402
import summon_camera as W                                          # noqa: E402
from ff9mapkit.summons import texanim as TA                        # noqa: E402

try:                                                               # py3.11+ stdlib, else the backport
    import tomllib as _toml
except ModuleNotFoundError:                                        # pragma: no cover
    import tomli as _toml                                          # type: ignore

RESKIN_SPEC = os.path.join(_HERE, "bahamut_reskin.toml")
RESCORE_SPEC = os.path.join(_HERE, "bahamut_rescore.toml")
RETIME_SPEC = os.path.join(_HERE, "bahamut_retime.toml")
CORPUS = W.SCRATCH_CORPUS

#: THE FROZEN ARTIFACT -- ef227's reskin is deployed and cast-proven; this rung's generalisation is
#: only allowed if `bahamut_reskin.toml` still builds THESE bytes.  A hash, not data (mirrors
#: w4_gates.py's own W4_PATCHED_SHA256 -- kept as a literal here too, deliberately: this runner must
#: stand on its own without importing a sibling lane's gate-runner module).
W4_PATCHED_SHA256 = "7fef205ffbe547545374de9d1017613448777f0251d9d425b55f7796f688b89a"

RESULTS = []


def gate(name: str, ok: bool, *lines: str) -> bool:
    RESULTS.append((name, ok))
    print("\n%s %s  %s" % ("[PASS]" if ok else "[FAIL]", name, "-" * max(2, 58 - len(name))))
    for ln in lines:
        print("   " + ln)
    return ok


def _has_install() -> bool:
    try:
        from ff9mapkit import config
        return bool(config.find_game_path(None))
    except Exception:
        return False


def _toml_loads(text: str) -> dict:
    return _toml.loads(text)


def _load_corpus(effect: int) -> bytes:
    path = os.path.join(CORPUS, "ef%03d.bytes" % effect)
    with open(path, "rb") as fh:
        return fh.read()


def _have_corpus() -> bool:
    return bool(W.corpus_paths(CORPUS))


# --------------------------------------------------------------------------- G1
def g1_corpus_no_crash_sweep():
    if not _have_corpus():
        return gate("G1 corpus no-crash sweep", False, "no extracted corpus at %s" % CORPUS)
    sw = SV.corpus_sweep(CORPUS)
    lines = ["survey_effect over %d containers: %d CRASHED"
            % (len(sw.rows) + len(sw.crashes), len(sw.crashes))]
    for c in sw.crashes[:10]:
        lines.append("   CRASH %s" % c)
    ok = not sw.crashes and len(sw.rows) == len(W.corpus_paths(CORPUS))
    lines.append("resolved: %d / %d corpus files" % (len(sw.rows), len(W.corpus_paths(CORPUS))))
    return gate("G1 corpus no-crash sweep (w_survey.corpus_sweep, all 372 containers)", ok, *lines)


# --------------------------------------------------------------------------- G2
def g2_ef227_byte_compat_across_lanes():
    lines, ok = [], True
    if not _has_install():
        return gate("G2 ef227 byte-compat across lanes", False, "no FF9 install resolvable")

    # -- reskin: the pinned, cast-proven artifact hash
    try:
        rb = RS.build(RS.load_spec(RESKIN_SPEC), RESKIN_SPEC)
        same = rb.sha_out == W4_PATCHED_SHA256
        lines.append("reskin  ef%03d sha_out %s -- %s the deployed W4 artifact"
                     % (rb.effect, rb.sha_out, "IDENTICAL to" if same else "*** DIFFERS FROM ***"))
        ok = ok and same
    except Exception as exc:
        lines.append("reskin  FAILED to rebuild: %s: %s" % (type(exc).__name__, exc))
        ok = False

    # -- rescore: its own self-check (round-trip / three-sequence / stock drift guard) still holds
    try:
        cb = R.build_patched(R.load_spec(RESCORE_SPEC), RESCORE_SPEC)
        # `cb.guard` names the guard that ACTUALLY applied.  Deriving it here from
        # `effect in EXPECTED_STOCK_SHA` alone was the same defect B5 found in `reskin.describe`:
        # true for ef227, but it calls any spec-guarded generalised effect "unguarded".
        lines.append("rescore ef%03d self-check: %s (sha_in %s, drift guard %s)"
                     % (cb.effect, cb.check.ok, cb.sha_in, cb.guard))
        ok = ok and cb.check.ok and cb.sha_in == R.EXPECTED_STOCK_SHA.get(cb.effect)
    except Exception as exc:
        lines.append("rescore FAILED to rebuild: %s: %s" % (type(exc).__name__, exc))
        ok = False

    # -- retime: its own self-check (byte accounting / round-trip / emulator invariants)
    try:
        tb = RT.build_containers(RT.load_spec(RETIME_SPEC), RETIME_SPEC)
        tb.check = RT.self_check(tb)
        lines.append("retime  ef%03d self-check: %s (sha_in %s)"
                     % (tb.effect, tb.check.ok, tb.sha_in))
        ok = ok and tb.check.ok and tb.sha_in == R.EXPECTED_STOCK_SHA.get(tb.effect)
    except Exception as exc:
        lines.append("retime  FAILED to rebuild: %s: %s" % (type(exc).__name__, exc))
        ok = False

    return gate("G2 ef227 byte-compat across lanes (reskin sha256 pin + rescore/retime self-checks)",
               ok, *lines)


# --------------------------------------------------------------------------- G3
def _refuse_via_scaffold(effect: int, pick, mutate=None):
    """Scaffold ``effect``, flip ONE target (chosen by ``pick(name) -> bool``) to enabled, apply
    ``mutate`` (a dict of extra knob overrides) and try to build.  Returns the ReskinError message,
    or ``None`` if the build did NOT refuse."""
    blob = _load_corpus(effect)
    text, _pmap = RS.scaffold(effect, blob)
    spec = _toml_loads(text)
    rows = spec["reskin"]["target"]
    row = next(r for r in rows if pick(r["name"]))
    row["enabled"] = True
    if mutate:
        row.update(mutate)
    try:
        RS.build(spec, "ef%03d-gate-probe" % effect, blob=blob)
        return None
    except RS.ReskinError as exc:
        return str(exc)


def _build_via_scaffold(effect: int, pick, mutate=None):
    """The mirror of :func:`_refuse_via_scaffold`: scaffold, flip ONE target on, and BUILD.

    Returns ``(build, None)`` or ``(None, message)``.  Deliberately routed through the scaffold rather
    than a hand-written spec, exactly as the refusal probe is -- a lift that only works on a spec an
    agent typed by hand is not a lift an author can reach.
    """
    blob = _load_corpus(effect)
    text, _pmap = RS.scaffold(effect, blob)
    spec = _toml_loads(text)
    rows = spec["reskin"]["target"]
    row = next(r for r in rows if pick(r["name"]))
    row["enabled"] = True
    if mutate:
        row.update(mutate)
    try:
        return RS.build(spec, "ef%03d-gate-probe" % effect, blob=blob), None
    except RS.ReskinError as exc:
        return None, str(exc)


def g3_five_texanim_lifts():
    """G3', W7.  This gate was `THE FIVE TEXANIM REFUSALS` and is now `THE FIVE TEXANIM LIFTS` --
    inverted, in lockstep with the kit's own pins, because W7 READ the table.

    What changed: the region is a texel-blit clip table that copies 8-bit palette INDICES inside ONE
    creature part's own 128x128 page.  It binds no CLUT word and writes no CLUT contents (no ``u16``
    anywhere in the five tables is a TPAGE or CLUT word; the rects cannot reach the CLUT strip), so a
    recolour survives it by construction -- and on the PC port nothing ticks it at all.  The refusal
    W5 shipped was correct FOR ITS EVIDENCE and is wrong for W7's.

    What this gate pins in its place is the stronger claim: on each of the five real armed packages a
    creature recolour BUILDS **and the texanim region comes back byte-identical**, with ``firstBlock``
    and ``min(motionOffsets)`` unmoved -- THE REGION INVARIANT (W7 R1), which is the one thing that
    must never move and the only rule the lift adds.
    """
    if not _have_corpus():
        return gate("G3' the five texanim lifts", False, "no extracted corpus at %s" % CORPUS)
    lines, ok = [], True
    for effect in SV.TEXANIM_CLASS:
        blob = _load_corpus(effect)
        res = TA.read(blob)
        ta = RS.texanim_region(blob)
        if not res.parsed:                                        # pragma: no cover - corpus drift
            ok = False
            lines.append("ef%03d region does NOT decode (%s) -- the lift is not available here"
                         % (effect, (res.error or "")[:70]))
            continue
        part = res.table.parts[0]
        b, msg = _build_via_scaffold(effect, lambda n, p=part: n == "creature.part%d" % p,
                                     mutate={"hue_rotate": 30.0})
        if b is None:
            ok = False
            lines.append("ef%03d creature recolour: REFUSED (%s)" % (effect, (msg or "")[:80]))
            continue
        n = sum(1 for i in range(len(blob)) if blob[i] != b.patched[i])
        same = b.patched[ta.lo:ta.hi] == blob[ta.lo:ta.hi]
        ok = ok and n > 0 and same and "byte-identical" in b.region_invariant
        lines.append("ef%03d  %d clip(s) part %d, region %d B  ->  BUILT, %d CLUT byte(s) changed, "
                     "region %s"
                     % (effect, res.table.count, part, ta.nbytes, n,
                        "BYTE-IDENTICAL" if same else "*** REWRITTEN ***"))
    lines.append("THE REGION INVARIANT is what replaced the refusal: %s" % TA.REGION_RULE)
    return gate("G3' the five texanim lifts (ef038/177/493/494/495, creature scope, region pinned)",
                ok, *lines)


# --------------------------------------------------------------------------- G4
def g4_ef381_ef447_refusals():
    if not _have_corpus():
        return gate("G4 ef381/ef447 refusals", False, "no extracted corpus at %s" % CORPUS)
    lines, ok = [], True

    blob381 = _load_corpus(381)
    _text, pmap381 = RS.scaffold(381, blob381)
    cell381 = next((c for c in pmap381.hazards.values() if c.multi_writer and not c.dual_depth),
                   None)
    if cell381 is None:                                          # pragma: no cover - corpus drift
        lines.append("ef381: no pure multi-writer cell found -- cannot probe")
        ok = False
    else:
        one_writer = cell381.names[0]
        msg = _refuse_via_scaffold(381, lambda n, w=one_writer: n == w,
                                   mutate={"hue_rotate": 30.0})
        fired = bool(msg) and "MULTI-WRITER" in msg
        ok = ok and fired
        lines.append("ef381 VRAM %s: naming only %r of %d writers -> %s"
                     % (cell381.vram, one_writer, len(cell381.names),
                        "REFUSED (MULTI-WRITER)" if fired else ("%r" % msg)))

    blob447 = _load_corpus(447)
    _text2, pmap447 = RS.scaffold(447, blob447)
    cell447 = pmap447.hazards.get((0, 242))
    if cell447 is None or not cell447.dual_depth:                # pragma: no cover - corpus drift
        lines.append("ef447: (0,242) is not dual-depth in this build -- cannot probe")
        ok = False
    else:
        name = cell447.names[0]
        msg = _refuse_via_scaffold(447, lambda n, w=name: n == w, mutate={"hue_rotate": 30.0})
        fired = bool(msg) and "DUAL-DEPTH" in msg
        ok = ok and fired
        lines.append("ef447 VRAM (0,242) dual-depth cell %r enabled -> %s"
                     % (name, "REFUSED (DUAL-DEPTH)" if fired else ("%r" % msg)))

    return gate("G4 ef381 (multi-writer, missing-writer refusal) / ef447 (dual-depth, outright)",
               ok, *lines)


# --------------------------------------------------------------------------- G5
def g5_headroom_refusal():
    if not _have_corpus():
        return gate("G5 headroom refusal", False, "no extracted corpus at %s" % CORPUS)
    msg = _refuse_via_scaffold(211, lambda n: n.startswith("creature."), mutate={"value": 1.1})
    fired = bool(msg) and "ZERO HEADROOM" in msg
    return gate("G5 headroom refusal (ef211, all six creature rows peak at 31/31)", fired,
               "ef211 creature target, value=1.1, no acknowledge_headroom: %s"
               % ("REFUSED (ZERO HEADROOM)" if fired else ("%r" % msg)))


# --------------------------------------------------------------------------- G6
def g6_ef000_camera_refusal():
    if not _have_corpus():
        return gate("G6 ef000 camera refusal", False, "no extracted corpus at %s" % CORPUS)
    lines, ok = [], True
    real = _load_corpus(0)
    rex = W.extract_shots(real, "ef000")
    dyn = R.dynamic_ops(rex)
    lines.append("ef000: %d shot(s), %d runtime-chosen camera op(s)" % (len(rex.shots), len(dyn)))
    ok = ok and len(dyn) >= 1

    sc = R.scaffold(0, real, "ef000")
    spec = _toml_loads(sc.text)
    lines.append("scaffold pre-seeds the key FALSE: %s"
                 % ("acknowledge_dynamic_ops = false" in sc.text))
    ok = ok and "acknowledge_dynamic_ops = false" in sc.text
    spec["edit"][0]["focal"] = {"distance": 240}

    why = ""
    try:
        R.build_patched(spec, "ef000", blob=real)
    except R.RescoreError as exc:
        why = str(exc)
    fired = "THE DYNAMIC-OP DISCLOSURE" in why
    lines.append("build WITHOUT acknowledge_dynamic_ops: %s"
                 % ("REFUSED" if fired else "BUILT (WRONG)"))
    ok = ok and fired

    spec["rescore"]["acknowledge_dynamic_ops"] = True
    got = R.build_patched(spec, "ef000", blob=real)
    lines.append("build WITH acknowledge_dynamic_ops = true: built, self-check %s, %d byte(s) changed"
                 % (got.check.ok, len(got.check.changed_offsets)))
    ok = ok and got.check.ok

    return gate("G6 ef000 camera refusal (the dynamic-op disclosure gate, real corpus fixture)",
               ok, *lines)


# --------------------------------------------------------------------------- G7
def g7_ef211_scaffold_build_clean():
    if not _have_corpus():
        return gate("G7 ef211 scaffold+build clean", False, "no extracted corpus at %s" % CORPUS)
    lines, ok = [], True
    blob = _load_corpus(211)
    text, pmap = RS.scaffold(211, blob)
    lines.append("scaffold: %d declared palette(s), envelope %d B" % (len(pmap.palettes),
                                                                       pmap.envelope))
    spec = _toml_loads(text)
    b = RS.build(spec, "ef211-scaffold", blob=blob)
    b.check = RS.self_check(b)
    n_changed = len(b.check.changed)
    lines.append("build: %d byte(s) changed (every knob at identity)" % n_changed)
    ok = ok and n_changed == 0
    lines.append("self-check: %d/%d gates pass" % (sum(1 for g in b.check.gates if g.ok),
                                                    len(b.check.gates)))
    for g in b.check.gates:
        if not g.ok:
            lines.append("   [!!] %s -- %s" % (g.name, g.detail))
    ok = ok and b.check.ok
    return gate("G7 ef211 scaffold + build clean (identity knobs, zero changed bytes)", ok, *lines)


# --------------------------------------------------------------------------- G8
def g8_retime_identity_gate_ef211_c0():
    if not _have_corpus():
        return gate("G8 retime identity gate on ef211:c0", False, "no extracted corpus at %s" % CORPUS)
    lines, ok = [], True
    blob = _load_corpus(211)
    sm, _base = RD.recover_machine(blob, "ef211", "ef211:c0")
    n_derivable = n_ok = n_refused = 0
    for ph in sm.phases:
        try:
            t = RD.analyse_target(blob, 211, "ef211:c0", ph.state)
        except RD.DeriveRefusal as exc:
            n_refused += 1
            lines.append("   s%d REFUSED (at analysis): %s" % (ph.state,
                                                               str(exc).splitlines()[0][:90]))
            continue
        if not t.derivable:
            # analyse_target did not raise, but it ACCUMULATED refusals on the target itself (the
            # documented posture: a bad reciprocal or an undecidable gate is collected, not thrown,
            # so every one of them is named rather than only the first).  build_edits/assert_identity
            # would raise the SAME thing, so treat this as the refusal it is, not an identity failure.
            n_refused += 1
            lines.append("   s%d REFUSED (%d reason(s)): %s"
                         % (ph.state, len(t.refusals), t.refusals[0].splitlines()[0][:90]))
            continue
        n_derivable += 1
        try:
            edits = RD.assert_identity(t, blob)
            n_ok += 1
            lines.append("   s%d DERIVABLE, N=0 identity gate holds (%d site(s))" % (ph.state,
                                                                                     len(edits)))
        except RD.DeriveRefusal as exc:
            lines.append("   s%d DERIVABLE but the N=0 IDENTITY GATE ITSELF FAILED (a genuine byte "
                         "mismatch -- this would be a real defect): %s"
                         % (ph.state, str(exc).splitlines()[0][:90]))
    lines.insert(0, "ef211:c0 (%d phases): %d derivable, %d of those pass N=0 identity, %d refused"
                % (len(sm.phases), n_derivable, n_ok, n_refused))
    ok = n_derivable >= 1 and n_ok == n_derivable
    return gate("G8 retime identity gate on ef211:c0 (build_edits(0) == stock, every derivable state)",
               ok, *lines)


# --------------------------------------------------------------------------- G9
def g9_survey_self_check():
    sc = SV.self_check(CORPUS)
    return gate("G9 survey self-check (texanim/hazard/op-25/twin-texture classes vs. the corpus)",
               sc.ok, *sc.lines)


# --------------------------------------------------------------------------- main
def main() -> int:
    print(__doc__.splitlines()[0])
    if not _has_install():
        print("\nNOTE: no FF9 install resolvable in this environment -- G2 will FAIL loudly rather "
             "than silently pass; every other gate reads the extracted corpus only.")
    if not _have_corpus():
        print("\nNOTE: no extracted corpus at %s -- G1/G3/G4/G5/G6/G7/G8/G9 will all FAIL loudly."
             % CORPUS)
    g1_corpus_no_crash_sweep()
    g2_ef227_byte_compat_across_lanes()
    g3_five_texanim_lifts()
    g4_ef381_ef447_refusals()
    g5_headroom_refusal()
    g6_ef000_camera_refusal()
    g7_ef211_scaffold_build_clean()
    g8_retime_identity_gate_ef211_c0()
    g9_survey_self_check()
    print("\n" + "=" * 72)
    for name, ok in RESULTS:
        print("%-5s %s" % ("PASS" if ok else "FAIL", name))
    passed = sum(1 for _n, ok in RESULTS if ok)
    print("=" * 72)
    print("%d/%d gates pass" % (passed, len(RESULTS)))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":                                        # pragma: no cover
    raise SystemExit(main())
