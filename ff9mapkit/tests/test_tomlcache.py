"""Tests for tomlcache -- the mtime+size-keyed TOML parse cache behind the campaign/journey/GUI opens.

The contract under test: a cache hit returns a PRIVATE copy (consumers mutate parsed trees in place --
resolve_project_flags rewrites flag names to ints during lint); an on-disk edit is always re-parsed
(the GUI's F5 honesty); parse/IO errors propagate and are never cached -- not even OVER a previously
good parse. No game install needed."""

import os
import tomllib

import pytest

from ff9mapkit import campaign, tomlcache


@pytest.fixture(autouse=True)
def _clean_cache():
    tomlcache.clear()
    yield
    tomlcache.clear()


def _bump(p):
    """Force a DISTINCT mtime signature -- two writes inside one filesystem timestamp tick would
    otherwise be indistinguishable, making the re-parse assertions timer-dependent."""
    st = os.stat(p)
    os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))


def test_hit_returns_equal_private_copy(tmp_path):
    p = tmp_path / "a.toml"
    p.write_text('[field]\nname = "A"\n\n[[event]]\nrequires_flag = "gate"\ntags = [1, 2]\n',
                 encoding="utf-8")
    a = tomlcache.load_toml(p)
    b = tomlcache.load_toml(p)
    assert a == b and a is not b
    # deep mutation of one caller's copy (exactly what resolve_project_flags does) must not leak
    a["field"]["name"] = "MUTATED"
    a["event"][0]["requires_flag"] = 8712
    a["event"][0]["tags"].append(99)
    c = tomlcache.load_toml(p)
    assert c == b != a


def test_edit_reparses(tmp_path):
    p = tmp_path / "a.toml"
    p.write_text("[field]\nid = 1\n", encoding="utf-8")
    assert tomlcache.load_toml(p)["field"]["id"] == 1
    p.write_text("[field]\nid = 2\n", encoding="utf-8")
    _bump(p)
    assert tomlcache.load_toml(p)["field"]["id"] == 2


def test_same_size_edit_reparses(tmp_path):
    """Same byte length, different content -- the mtime half of the key must carry it alone."""
    p = tmp_path / "a.toml"
    p.write_text("[field]\nid = 1\n", encoding="utf-8")
    size1 = os.stat(p).st_size
    assert tomlcache.load_toml(p)["field"]["id"] == 1
    p.write_text("[field]\nid = 7\n", encoding="utf-8")   # identical size
    assert os.stat(p).st_size == size1
    _bump(p)
    assert tomlcache.load_toml(p)["field"]["id"] == 7


def test_errors_propagate_and_are_never_cached(tmp_path):
    p = tmp_path / "a.toml"
    p.write_text("[field\nbroken", encoding="utf-8")
    with pytest.raises(tomllib.TOMLDecodeError):
        tomlcache.load_toml(p)
    with pytest.raises(tomllib.TOMLDecodeError):          # still raises (no error-result caching)
        tomlcache.load_toml(p)
    p.write_text("[field]\nid = 3\n", encoding="utf-8")
    _bump(p)
    assert tomlcache.load_toml(p)["field"]["id"] == 3     # fixed file parses without a stale error
    # ...and a GOOD parse must never be served for a now-BROKEN file (stale-success is the worse bug)
    p.write_text("[field\nbroken again", encoding="utf-8")
    _bump(p)
    with pytest.raises(tomllib.TOMLDecodeError):
        tomlcache.load_toml(p)


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        tomlcache.load_toml(tmp_path / "nope.toml")


# ---- the cache is transparent under the real consumers -----------------------------------
def _mini_campaign(tmp_path):
    """A one-member campaign whose member gates on a NAMED flag -- the exact shape lint_campaign
    resolves IN PLACE (names -> ints), i.e. the poisoning hazard the private-copy contract guards."""
    (tmp_path / "ENT").mkdir()
    (tmp_path / "ENT" / "ENT.field.toml").write_text(
        '[field]\nname = "ENT"\nid = 6001\n\n'
        '[[event]]\nname = "door"\nrequires_flag = "switch_pulled"\n',
        encoding="utf-8")
    (tmp_path / "campaign.toml").write_text(
        '[campaign]\nname = "MINI"\nid_base = 6001\nflag_base = 8712\nflags_per_field = 64\n'
        'entry_field = "ENT"\nentry_entrance = 0\n\n'
        '[[field]]\nname = "ENT"\nsource = 300\nid = 6001\nmode = "borrow"\ntoml = "ENT/ENT.field.toml"\n\n'
        '[[flag]]\nname = "switch_pulled"\nindex = 8776\n',
        encoding="utf-8")
    return tmp_path / "campaign.toml"


def test_lint_campaign_twice_identical_and_cache_unpoisoned(tmp_path):
    cpath = _mini_campaign(tmp_path)
    plan = campaign.load_campaign(cpath)
    first = campaign.lint_campaign(plan, tmp_path)
    second = campaign.lint_campaign(campaign.load_campaign(cpath), tmp_path)
    assert first == second
    # lint resolved 'switch_pulled' -> 8776 in ITS copy; the cache must still hold the authored name
    raw = tomlcache.load_toml(tmp_path / "ENT" / "ENT.field.toml")
    assert raw["event"][0]["requires_flag"] == "switch_pulled"


def test_load_campaign_sees_on_disk_edit(tmp_path):
    cpath = _mini_campaign(tmp_path)
    assert campaign.load_campaign(cpath).members[0].new_id == 6001
    text = cpath.read_text(encoding="utf-8").replace("id = 6001", "id = 6002")
    cpath.write_text(text, encoding="utf-8")
    _bump(cpath)
    assert campaign.load_campaign(cpath).members[0].new_id == 6002
