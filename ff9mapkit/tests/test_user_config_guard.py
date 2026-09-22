"""The suite-wide per-user CONFIG guard (``ff9mapkit/conftest.py`` ``_isolate_user_config``).

Every per-user config file -- ``prefs.json``, ``update_check.json``, the Workspace's upgrade script --
resolves through ONE seam, ``provision._user_dir("config")``. The old guard (``tests/conftest.py``'s
``_isolate_prefs``) pinned ``prefs._path`` by name, so a Workspace test that reached the update-check
store wrote into the developer's real ``%LOCALAPPDATA%`` unless it remembered to fake ``is_installed``;
and it covered ``tests/`` only. These tests use NO local patching on purpose: what they see is what
every test in every tree under ``ff9mapkit/`` sees."""

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
