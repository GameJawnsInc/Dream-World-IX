"""The tk-FREE half of editor/feedback.py: the Verdict/Problem builders. No display, no tkinter
(like the other editor headless tests). The FeedbackPanel widget is verified by the human in the
running apps (can't drive a UI offline)."""

from __future__ import annotations

from ff9mapkit.editor import feedback as fb


def test_clean_is_ok_with_default_or_custom_headline():
    v = fb.classify([], [], subject="Check")
    assert v.level == fb.OK and "all clear" in v.headline and v.headline.startswith("Check")
    v2 = fb.classify([], [], clean_headline="Built and deployed", next_action="F6 -> Warp -> 4003")
    assert v2.level == fb.OK and v2.headline == "Built and deployed"
    assert v2.next_action == "F6 -> Warp -> 4003"


def test_warnings_only_passes_with_warnings():
    v = fb.classify([], ["w1", "w2"], subject="Build")
    assert v.level == fb.WARN
    assert "2 warnings" in v.headline and v.headline.startswith("Build")


def test_any_error_fails_and_counts_both():
    v = fb.classify(["e1", "e2", "e3"], ["w1"], subject="Check")
    assert v.level == fb.ERROR
    assert "3 problems" in v.headline and "1 warning" in v.headline


def test_singular_vs_plural():
    assert "1 warning" in fb.classify([], ["only"]).headline
    assert "1 problem" in fb.classify(["only"], []).headline
    assert "2 problems" in fb.classify(["a", "b"], []).headline


def test_from_returncode_ok_and_fail():
    ok = fb.from_returncode(0, subject="Import", ok_headline="Imported", ok_next="open it in Build")
    assert ok.level == fb.OK and ok.headline == "Imported" and ok.next_action == "open it in Build"
    bad = fb.from_returncode(2, subject="Import", fail_hint="needs UnityPy")
    assert bad.level == fb.ERROR and "exit 2" in bad.headline and bad.next_action == "needs UnityPy"


def test_from_returncode_defaults():
    assert fb.from_returncode(0).headline == "done"
    assert fb.from_returncode(1).next_action == "See the details below."


def test_problems_flattens_errors_then_warnings_with_severities():
    rows = fb.problems(["e1", "e2"], ["w1"])
    assert [r.severity for r in rows] == [fb.ERROR, fb.ERROR, fb.WARN]
    assert [r.message for r in rows] == ["e1", "e2", "w1"]
    assert all(r.where == "" for r in rows)


def test_problems_empty():
    assert fb.problems() == []
    assert fb.problems([], []) == []


def test_dataclasses_are_frozen():
    import dataclasses

    p = fb.Problem(fb.WARN, "msg")
    v = fb.Verdict(fb.OK, "head")
    for obj in (p, v):
        try:
            obj.message = "x"  # type: ignore[attr-defined]
        except (dataclasses.FrozenInstanceError, AttributeError):
            pass
        else:
            raise AssertionError("expected frozen dataclass")
