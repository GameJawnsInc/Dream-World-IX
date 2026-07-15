"""The plain-language error layer (editor.feedback.humanize) -- tk-free, maps raw newcomer-facing errors
to a friendly sentence + a next step. Additive: an unmatched message returns None (the raw row still shows)."""

from __future__ import annotations

from ff9mapkit.editor import feedback as fb


def test_humanize_rewrites_common_newcomer_errors():
    # a representative raw error from each of a few emit sites -> a plain sentence + a concrete next step
    cases = {
        "area must be >= 10 (got 4)": ("area", "10"),
        "ID COLLISION: id 4003 is already registered by another mod folder -> null .eb": ("id", "4000"),
        "extraction needs UnityPy (reads FF9's p0data assetbundles)": ("UnityPy", "pip install UnityPy"),
        "gil must be in [0, 9,999,999] (the in-game cap); got 99999999": ("Gil", "9,999,999"),
        "flag 100 is in the reserved region": ("flag", "8512"),
    }
    for raw, (in_friendly, in_step) in cases.items():
        got = fb.humanize(raw)
        assert got is not None, raw
        friendly, step = got
        assert in_friendly.lower() in friendly.lower(), (raw, friendly)
        assert in_step.lower() in step.lower(), (raw, step)


def test_humanize_is_case_insensitive_and_additive():
    assert fb.humanize("TOMLDecodeError: Expected '=' after a key") is not None      # any case
    assert fb.humanize("some internal error we have no rewrite for") is None          # additive: no match -> None
    assert fb.humanize("") is None and fb.humanize(None) is None                      # never raises


def test_every_rewrite_is_well_formed():
    seen = set()
    for match, friendly, step in fb._REWRITES:
        assert match == match.lower() and match not in seen, match     # lowercase + unique match keys
        seen.add(match)
        assert friendly.rstrip(")").endswith((".", "!")) and step.rstrip(")").endswith((".", "!")), match
        assert len(friendly) > 30 and len(step) > 10, match            # a real sentence + a real action
