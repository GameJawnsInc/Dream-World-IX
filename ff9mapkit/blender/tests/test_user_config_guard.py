"""The per-user config guard reaches THIS tree too: ``ff9mapkit/conftest.py`` sits above both
``tests/`` and ``blender/tests/``, so a Blender-bridge test that (someday) touches prefs can neither read
nor write the developer's real store. No local patching -- that is the point."""

from ff9mapkit import prefs


def test_prefs_resolve_under_the_tests_tmp_dir(tmp_path):
    assert tmp_path in prefs._path().parents, prefs._path()      # RED before the hoist: the real config dir
