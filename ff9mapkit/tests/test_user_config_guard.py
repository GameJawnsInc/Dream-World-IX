"""The suite-wide per-user CONFIG guard (``ff9mapkit/conftest.py`` ``_isolate_user_config``).

Every per-user config file -- ``prefs.json``, ``update_check.json``, the Workspace's upgrade script --
resolves through ONE seam, ``provision._user_dir("config")``. The old guard (``tests/conftest.py``'s
``_isolate_prefs``) pinned ``prefs._path`` by name, so a Workspace test that reached the update-check
store wrote into the developer's real ``%LOCALAPPDATA%`` unless it remembered to fake ``is_installed``;
and it covered ``tests/`` only. These tests use NO local patching on purpose: what they see is what
every test in every tree under ``ff9mapkit/`` sees."""

import pytest

from ff9mapkit import prefs, provision, update_check


def _under(p, root) -> bool:
    return root in p.parents


def test_every_config_seam_resolves_under_the_tests_tmp_dir(tmp_path):
    assert _under(prefs._path(), tmp_path), prefs._path()
    assert _under(update_check._state_path(), tmp_path), update_check._state_path()   # RED before the hoist
    assert _under(provision._user_dir("config") / "upgrade.ps1", tmp_path)


def test_data_and_cache_subs_pass_through_to_the_real_rule(tmp_path):
    """Only ``config`` is redirected: ``data`` / ``cache`` are live on an installed-wheel run
    (``provision.data_dir`` / ``cache_dir``) and must keep the platform rule's answer."""
    for sub in ("data", "cache"):
        p = provision._user_dir(sub)
        assert not _under(p, tmp_path), p
        assert p.parts[-2:] == ("ff9mapkit", sub), p


@pytest.fixture(scope="module")
def _module_scoped_store(tmp_path_factory):
    """Stands in for a module-scoped ``Workspace`` fixture: it reads the store at CONSTRUCTION, which pytest
    runs before any function-scoped pin exists, and writes at TEARDOWN, which runs after the last one
    unwound. Both ends are exactly where the a11y fixture read the owner's collapsed-pane layout."""
    base = tmp_path_factory.getbasetemp()
    built = prefs._path()
    yield built, base
    assert _under(prefs._path(), base), f"module teardown would write the REAL store: {prefs._path()}"


def test_a_module_scoped_fixture_never_sees_the_real_config_store(_module_scoped_store, tmp_path):
    built, base = _module_scoped_store
    assert _under(built, base), f"a module fixture was built against the REAL store: {built}"
    assert not _under(built, tmp_path), "the module store must be its own, not this test's"
