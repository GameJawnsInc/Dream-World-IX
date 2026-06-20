"""Make the byte-level suite degrade to clean SKIPS when the FF9-derived assets aren't extracted.

ff9mapkit ships NO Square Enix game data (see ff9mapkit/provision.py + docs/PROVENANCE.md): the blank
field, the exit-region template, and several test fixtures are regenerated from the user's own FF9
install by ``ff9mapkit extract-templates``. Until that's run, the tests that read that data can't run.
This top-level conftest (covering BOTH the ``tests/`` and ``blender/tests/`` suites) makes a fresh public
clone get a clean, exit-0 run -- the game-data tests are skipped, not errored -- while the pure-logic
suite (camera math, the editor model/serializer, lint, the campaign/journey graph, the codecs) still
runs and verifies the package offline.

Two complementary mechanisms:

  1. ``pytest_ignore_collect`` -- a handful of modules read game data at MODULE TOP LEVEL (a constant like
     ``CLEAN = data.blank_field_bytes("us")``). Those raise at IMPORT, before any test runs, so a runtime
     skip can't save them -- we don't collect them at all. They're detected from the source (an unguarded
     column-0 data read), NOT a hand-maintained list: the previous hardcoded list silently went stale as
     the suite grew (~13 listed vs ~30+ reading game data) and made the documented ``pytest`` abort at
     collection on a fresh clone.

  2. ``pytest_runtest_setup`` / ``pytest_runtest_call`` (wrappers) -- every OTHER game-data read happens
     inside a fixture or a test body. We let those modules collect (so their pure-logic tests still run)
     and convert a data-absence ``FileNotFoundError`` into a clean skip. A module that mixes logic +
     build/fixture tests thus runs its logic tests and skips only the ones that actually need the install,
     keeping offline coverage maximal rather than dropping whole modules. (Both phases are wrapped because
     some tests do the build in a fixture -> a setup-phase error, not a call-phase one.)

Run ``ff9mapkit extract-templates`` (needs your FF9 install) to enable the full byte-level suite.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from ff9mapkit import provision

_SKIP_REASON = ("FF9 base templates/fixtures not extracted -- run `ff9mapkit extract-templates` "
                "(needs your FF9 install; see docs/PROVENANCE.md).")

# A column-0 assignment that does game-data I/O at import time -> the module can't be imported without the
# extracted assets, so it must be skipped at collection (a runtime skip can't save an import-time error).
# The ``exists()`` / comment checks below exclude lines that already cope with the data being absent.
_MODULE_LEVEL_IO = re.compile(
    r'^[A-Za-z_]\w*\s*=.*(?:blank_field_bytes\(|region_template\(|\.read_bytes\(\))', re.M)


def _imports_game_data(path: Path) -> bool:
    try:
        src = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    for m in _MODULE_LEVEL_IO.finditer(src):
        line = m.group(0)
        if "exists()" not in line and not line.lstrip().startswith("#"):
            return True
    return False


def _is_missing_game_data(exc: BaseException) -> bool:
    """True if a FileNotFoundError signals absent base templates / fixtures / extract cache."""
    msg = str(exc)
    # The base-template accessors raise FileNotFoundError(provision.MISSING_MSG) with NO .filename;
    # that message names the fix, so it's the most reliable marker.
    if "extract-templates" in msg:
        return True
    fn = str(getattr(exc, "filename", "") or "")
    s = (fn if fn else msg).replace("\\", "/").lower()
    if "blank_field" in s or "region_template" in s:
        return True
    if "/fixtures/" in s and s.rsplit(".", 1)[-1] in ("bytes", "bgx", "bgs"):
        return True
    for base in (provision.data_dir(), provision.cache_dir()):
        b = str(base).replace("\\", "/").lower()
        if b and b in s:
            return True
    return False


def _skip_if_missing_data(exc: FileNotFoundError) -> None:
    if not provision.templates_present() and _is_missing_game_data(exc):
        pytest.skip(_SKIP_REASON)


def pytest_ignore_collect(collection_path, config):
    """Skip collecting a module that reads game data at import time when the templates aren't present."""
    if provision.templates_present():
        return None
    p = Path(str(collection_path))
    if p.suffix == ".py" and p.name.startswith("test_") and _imports_game_data(p):
        return True
    return None


@pytest.hookimpl(wrapper=True)
def pytest_runtest_setup(item):
    """A fixture that reads absent game data -> skip the test (setup-phase), not error it."""
    try:
        return (yield)
    except FileNotFoundError as exc:
        _skip_if_missing_data(exc)
        raise


@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item):
    """A test body that reads absent game data -> skip the test (call-phase), not fail it."""
    try:
        return (yield)
    except FileNotFoundError as exc:
        _skip_if_missing_data(exc)
        raise


def pytest_configure(config):
    if not provision.templates_present():
        config.issue_config_time_warning(
            UserWarning("ff9mapkit: base templates not extracted -- byte-level tests are skipped. "
                        "Run `ff9mapkit extract-templates` (needs your FF9 install) to enable them."),
            stacklevel=2,
        )
