"""[ff9mapkit netsync s157] THE GHOST FRAME (studies/field-coop/GUEST-TRAVERSAL-TWO-PC.md Finding 1): battlewire's Python twins of
NetSyncVisitor's pure rules, held to the engine selftest's own literal rows and to the constants on the live patch stack, and the s157
patch's HarnessAgent tag law."""
from __future__ import annotations

import pathlib
import sys

from ._patchstack import msr, net_lines

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from harness import battlewire as BW                               # noqa: E402

GF_TAG = "[ff9mapkit netsync s157]"


def test_the_ghost_frame_twins_answer_the_engines_selftest_rows():
    O, W = BW.LOCO_OTHER, BW.LOCO_WALK
    why = BW.ghost_frame_why
    assert why(True, True, 12, O, True) == BW.GF_FOLLOW and why(False, True, 12, O, True) == BW.GF_WHY_LEVER
    assert why(True, False, 0, O, True) == BW.GF_WHY_NO_FRAME
    assert [why(True, True, n, O, True) for n in (0, 1, 255, 2, 254)] == [BW.GF_WHY_FRAME_N] * 3 + [BW.GF_FOLLOW] * 2
    assert [why(True, True, 12, lo, True) for lo in range(1, 6)] == [BW.GF_WHY_LOCO] * 5
    assert why(True, True, 12, O, False) == BW.GF_WHY_CLIP
    # why.foreign_walk: a body outside the rig table (658) sends Other for its walk, and its raw clip is followed (S157-review GF-5)
    assert BW.classify_loco(658, 25) == O and why(True, True, 12, BW.classify_loco(658, 25), True) == BW.GF_FOLLOW
    f = BW.follows_wire_anim
    assert f(10539, 10539, -1, O) and f(10539, 10539, 3, O) and f(10741, 10539, 3, O) and f(12034, 206, 3, O)
    assert not any((f(2001, 10539, 3, O), f(2002, 10539, 3, O), f(2001, 10539, -1, O), f(0, 10539, 3, O),
                    f(10741, 10539, 99, O), f(1996, 25, 3, W)))
    s = BW.ghost_frame_step
    D, R, X = BW.GF_STEP_DIRECT, BW.GF_STEP_WRAP, BW.GF_STEP_SNAP
    assert [s(3, 4, 12), s(4, 3, 12), s(3, 5, 12), s(11, 0, 12), s(0, 11, 12), s(11, 1, 12)] == [
        (D, 1), (D, -1), (D, 2), (R, 1), (R, -1), (R, 2)]
    assert [s(0, 3, 12)[0], s(1, 7, 8)[0], s(2, 10, 11)[0], s(3, 17, 28)[0], s(0, 1, 2)[0], s(12, 0, 12)[0]] == [X] * 6
    assert s(100, 130, 254) == (D, 30) and s(253, 2, 254) == (R, 3)
    # a short clip's direct +2 / +1 eases, its -3 snaps (S157-review GF-4: step.short_double / short_triple / short_n4)
    assert s(1, 3, 8) == (D, 2) and s(5, 2, 8)[0] == X and s(1, 2, 4) == (D, 1)


def test_the_step_rule_can_fail():
    """The capture's rule (the quarter bound on a DIRECT step too) misses the short-clip rows; the half bound misses the quarter row;
    a seam-blind rule misses the seam row -- each wrong rule fails one of the selftest's step rows."""
    D, R, X = BW.GF_STEP_DIRECT, BW.GF_STEP_WRAP, BW.GF_STEP_SNAP

    def bounded(direct, wrap):
        def step(last, nxt, n):
            if n < 2 or not 0 <= last < n or not 0 <= nxt < n:
                return X, 0
            d = nxt - last
            if direct(d, n):
                return D, d
            w = d - n if d > 0 else d + n
            return (R, w) if wrap(w, n) else (X, 0)
        return step

    rows = [((3, 4, 12), (D, 1)), ((11, 0, 12), (R, 1)), ((0, 3, 12), (X, 0)), ((1, 7, 8), (X, 0)), ((0, 1, 2), (X, 0)),
            ((1, 3, 8), (D, 2)), ((5, 2, 8), (X, 0)), ((1, 2, 4), (D, 1))]
    assert all(BW.ghost_frame_step(*a) == want for a, want in rows)
    quarter = bounded(lambda d, n: 4 * abs(d) < n, lambda w, n: 4 * abs(w) < n)
    half = bounded(lambda d, n: 2 * abs(d) < n, lambda w, n: 2 * abs(w) < n)
    no_seam = bounded(lambda d, n: 4 * abs(d) < n or (abs(d) <= 2 and 2 * abs(d) < n), lambda w, n: False)
    for wrong in (quarter, half, no_seam):
        assert any(wrong(*a) != want for a, want in rows)
    e, t = BW.ghost_frame_ease, BW.ghost_frame_time
    assert e(3.0, 3.0, 0.2) == 3.0 and abs(e(0.0, 1.0, 0.25) - 0.25) < 1e-9 and e(0.9995, 1.0, 0.5) == 1.0
    assert e(11.5, 13.0, 1.0) == 13.0 and abs(t(6.0, 12, 1.1) - 0.55) < 1e-9 and t(0.0, 12, 1.1) == 0.0


def test_the_twins_carry_the_engines_constants_and_names():
    vis = net_lines("NetSyncVisitor.cs", r".")
    assert ("public const Int32 GfFollow = 0, GfWhyLever = 1, GfWhyNoFrame = 2, GfWhyFrameN = 3, GfWhyLoco = 4, "
            "GfWhyClip = 5;") in vis
    assert "public const Int32 GfStepDirect = 0, GfStepWrap = 1, GfStepSnap = 2;" in vis
    assert (BW.GF_FOLLOW, BW.GF_WHY_CLIP, BW.GF_STEP_SNAP) == (0, 5, 2)
    for name in BW.GF_WHY_NAMES.values():
        assert any(ln.endswith(f'return "{name}";') for ln in vis), name
    assert "if (4 * Math.Abs(d) < n || (Math.Abs(d) <= 2 && 2 * Math.Abs(d) < n))" in vis    # the twin's direct bound (GF-4)
    assert "if (4 * Math.Abs(w) < n)" in vis                                                  # ...and the seam's quarter
    assert "return twinOn && peerHasFrame;" in vis and BW.ghost_twin_law(True, True) and not BW.ghost_twin_law(True, False)
    assert "return resolvedAnim != Rigs[dressRig].Idle && resolvedAnim != Rigs[dressRig].IdleAlias;" in vis


def test_every_s157_harnessagent_hunk_carries_the_tag():
    names = [n for n in msr.stack() if n.startswith("s157-") and n not in msr.DEAD]
    assert len(names) == 1, names
    hunks, cur = [], None
    for path, sec in msr.sections((msr.PATCHES / names[0]).read_bytes()):
        if not path or path.replace("\\", "/").rsplit("/", 1)[-1] != "HarnessAgent.cs":
            continue
        for ln in sec.decode("utf-8", "replace").splitlines():
            if ln.startswith("@@"):
                cur = []
                hunks.append(cur)
            elif cur is not None and ln.startswith("+") and not ln.startswith("+++"):
                cur.append(ln[1:])
    assert len(hunks) >= 5, len(hunks)
    for added in hunks:
        assert any(GF_TAG in ln for ln in added), added[:3]
        assert all(ln.isascii() for ln in added), [ln for ln in added if not ln.isascii()][:2]
