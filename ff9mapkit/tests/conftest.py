"""Skip the byte-level suite when the FF9-derived base assets haven't been extracted.

ff9mapkit ships NO Square Enix game data (see ff9mapkit/provision.py + docs/PROVENANCE.md): the blank
field, the exit-region template, and several test fixtures are regenerated from the user's own FF9
install by ``ff9mapkit extract-templates``. Until that's run, the tests that read that data can't run,
so we skip those whole modules cleanly (avoiding import-time failures from module-level loads). The
pure-logic suite -- camera math, the editor forms/model, the CLI entrypoint, area handling -- still
runs with no install, so a fresh clone can verify the package imports + core logic offline.
"""
from __future__ import annotations

from ff9mapkit import provision

# Modules that read FF9-derived data (a built field needs the blank; others read a regenerated fixture).
_NEEDS_GAME_DATA = {
    "test_bgs", "test_build", "test_content", "test_eb", "test_editor_integration",
    "test_eventscan", "test_export", "test_import_borrow", "test_pack", "test_scene",
    "test_scroll", "test_showcase", "test_yaw_movement",
}


def pytest_ignore_collect(collection_path, config):
    """Don't even import a game-data module when the templates aren't present."""
    if provision.templates_present():
        return None
    return True if collection_path.stem in _NEEDS_GAME_DATA else None


def pytest_configure(config):
    if not provision.templates_present():
        config.issue_config_time_warning(
            UserWarning("ff9mapkit: base templates not extracted -- the byte-level suite is skipped. "
                        "Run `ff9mapkit extract-templates` (needs your FF9 install) to enable it."),
            stacklevel=2,
        )
