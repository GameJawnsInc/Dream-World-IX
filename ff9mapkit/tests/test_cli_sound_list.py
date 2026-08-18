"""``music-list`` / ``sfx-list`` -- the two audio listing verbs that make ``audio-import --song <id>``
discoverable -- and the help text that cites them.

Nothing in the suite covered these. They are registered through an f-string loop --
``sub.add_parser(f"{_snd}-list", ...)`` -- so neither name exists as a literal anywhere in ``cli.py``: a
grep for ``music-list`` finds ONLY the ``audio-import --song`` help string that cites them, never the
call site that mints them. That reads exactly like a help string pointing at two verbs nobody ever
implemented, and it was filed as such. These tests make the registration falsifiable instead of
grep-invisible, so the next reader gets a red test rather than a plausible-looking bug report.

Two lanes, like ``test_cli_encounters.py``:
  * OFFLINE -- a synthetic manifest monkeypatched onto ``sound.read_manifest`` (the command re-imports
    the module per call, so the patch has to land on the module attribute to reach it).
  * GAME-GATED -- the documented anchor against the user's real install: sfx **108** is the item-get
    jingle that ``docs/BEHAVIOR.md``, ``docs/FORMAT.md`` and ``content/siege.py`` all hand the reader
    by number.
"""
from __future__ import annotations

import argparse
import re

import pytest

from ff9mapkit import cli
from ff9mapkit import sound as S

VERBS = {"music": "music-list", "sfx": "sfx-list"}


def _parse(argv):
    return cli.build_parser().parse_args(argv)


def _subparsers():
    parser = cli.build_parser()
    for a in parser._actions:
        if isinstance(a, argparse._SubParsersAction):
            return a.choices
    raise AssertionError("no subparsers action found")


_MUSIC = [
    {"id": 0, "resource_id": "Sounds01/BGM_/music006", "type": "Music"},
    {"id": 9, "resource_id": "Sounds01/BGM_/music008", "type": "Music"},
    {"id": 100, "resource_id": "Sounds01/BGM_/music072", "type": "Music"},
]
_SFX = [
    {"id": 108, "resource_id": "Sounds02/SE00/se000004", "type": "SoundEffect"},
    {"id": 324, "resource_id": "Sounds02/SE02/se020108", "type": "SoundEffect"},
]


@pytest.fixture
def fake_manifest(monkeypatch):
    """``_cmd_sound_list`` does ``from . import sound as S`` per call, so patching the module attribute
    is what reaches it -- there is no name captured in ``cli`` to patch instead."""
    def _read(kind="music", game=None, use_cache=True):
        return list(_MUSIC if kind == "music" else _SFX)
    monkeypatch.setattr(S, "read_manifest", _read)


# --------------------------------------------------------------------------------- (1) REGISTRATION ---
@pytest.mark.parametrize("kind,verb", sorted(VERBS.items()))
def test_both_list_verbs_are_registered(kind, verb):
    """The f-string loop is the only thing that mints these names; delete it and every citation of them
    -- the ``--song`` help, README, KNOWN_ISSUES, the tutorials index, the Workspace Import tab's
    ``_kit(["music-list"])`` buttons -- becomes a lie, silently."""
    a = _parse([verb])
    assert a.func is cli._cmd_sound_list
    assert a.kind == kind
    assert a.filter is None


def test_an_unregistered_verb_really_is_rejected():
    """Guard the guard: ``parse_args`` must reject a name that ISN'T registered, or the test above
    would pass no matter what ``build_parser`` did."""
    with pytest.raises(SystemExit):
        _parse(["music-listt"])


def test_audio_import_song_help_cites_only_REGISTERED_verbs():
    """The reported defect, generalized: every ``*-list`` verb the ``--song`` help names in backticks
    must resolve to a real subcommand."""
    song = next(a for a in _subparsers()["audio-import"]._actions if "--song" in a.option_strings)
    cited = set(re.findall(r"`([a-z0-9-]+-list)`", song.help))
    assert cited == {"music-list", "sfx-list"}          # the help still points the reader at both
    assert cited <= set(_subparsers())                  # ...and both are really there


# ------------------------------------------------------------------------ (2) THE ROOT --game FLAGS ---
@pytest.mark.parametrize("verb", sorted(VERBS.values()))
def test_the_ROOT_game_flag_SURVIVES_into_the_list_verbs(verb):
    """Both verbs declare ``--game`` with ``default=argparse.SUPPRESS`` precisely so a literal default
    cannot clobber what the root parser already parsed (the trap pinned in ``test_summon_reskin.py``).
    Naming it after the verb still wins."""
    assert _parse(["--game", "G:/FF9", verb]).game == "G:/FF9"
    assert _parse([verb, "--game", "H:/X"]).game == "H:/X"


@pytest.mark.parametrize("verb", sorted(VERBS.values()))
def test_game_defaults_to_None_rather_than_being_ABSENT(verb):
    """``_cmd_sound_list`` reads ``args.game`` directly, and that read sits INSIDE its try/except. If the
    root default ever went away, SUPPRESS would leave the attribute missing and every invocation would
    die as a misleading "could not read the music manifest: 'Namespace' object has no attribute 'game'"
    instead of an obvious crash."""
    assert _parse([verb]).game is None


# ---------------------------------------------------------------------------- (3) OFFLINE -- OUTPUT ---
def test_music_list_prints_ids_and_the_audio_import_hint(fake_manifest, capsys):
    rc = cli._cmd_sound_list(_parse(["music-list"]))
    out = capsys.readouterr().out
    assert rc == 0
    assert out.splitlines()[0] == "3 music track(s) (id -> ResourceID):"
    assert "      0  Sounds01/BGM_/music006" in out                  # id right-aligned in 5, 2-space gutter
    assert "    100  Sounds01/BGM_/music072" in out
    assert "ff9mapkit audio-import <in.wav> --song <id> --deploy <modfolder>" in out
    assert "--kind sfx" not in out                                   # music is the default kind


def test_sfx_list_hint_carries_kind_sfx(fake_manifest, capsys):
    """The hint has to be copy-pasteable: without ``--kind sfx`` it would resolve the id against the
    MUSIC manifest and override the wrong track."""
    rc = cli._cmd_sound_list(_parse(["sfx-list"]))
    out = capsys.readouterr().out
    assert rc == 0
    assert out.splitlines()[0] == "2 sfx track(s) (id -> ResourceID):"
    assert "    108  Sounds02/SE00/se000004" in out
    assert "--song <id> --kind sfx --deploy <modfolder>" in out


# ---------------------------------------------------------------------------- (4) OFFLINE -- FILTER ---
def test_filter_matches_a_resource_id_SUBSTRING(fake_manifest, capsys):
    cli._cmd_sound_list(_parse(["music-list", "--filter", "music00"]))
    out = capsys.readouterr().out
    assert out.splitlines()[0] == "2 music track(s) (id -> ResourceID):"   # music006 + music008, not 072
    assert "music072" not in out


def test_filter_matches_an_EXACT_id(fake_manifest, capsys):
    """``9`` is nowhere in any of the three ResourceIDs, so only the exact-id arm can match it."""
    cli._cmd_sound_list(_parse(["music-list", "--filter", "9"]))
    out = capsys.readouterr().out
    assert out.splitlines()[0] == "1 music track(s) (id -> ResourceID):"
    assert "Sounds01/BGM_/music008" in out


def test_filter_is_case_insensitive_and_stripped(fake_manifest, capsys):
    cli._cmd_sound_list(_parse(["music-list", "--filter", "  BGM_/MUSIC072 "]))
    assert capsys.readouterr().out.splitlines()[0] == "1 music track(s) (id -> ResourceID):"


def test_a_filter_matching_nothing_is_empty_not_an_error(fake_manifest, capsys):
    rc = cli._cmd_sound_list(_parse(["music-list", "--filter", "no-such-track"]))
    out = capsys.readouterr().out
    assert rc == 0
    assert out.splitlines()[0] == "0 music track(s) (id -> ResourceID):"
    assert "audio-import" in out                                     # the hint still prints


# ----------------------------------------------------------------------------- (5) OFFLINE -- ERROR ---
def test_unreadable_manifest_reports_on_stderr_and_exits_2(monkeypatch, capsys):
    def _boom(kind="music", game=None, use_cache=True):
        raise FileNotFoundError("resources.assets not found")
    monkeypatch.setattr(S, "read_manifest", _boom)
    rc = cli._cmd_sound_list(_parse(["music-list"]))
    cap = capsys.readouterr()
    assert rc == 2
    assert "could not read the music manifest" in cap.err
    assert "resources.assets not found" in cap.err                   # the cause survives, not just "failed"
    assert cap.out == ""                                             # nothing half-printed on stdout


# --------------------------------------------------------------------------------- (6) GAME-GATED -----
def _game_ready():
    try:
        import UnityPy  # noqa: F401
        S.resources_assets_path(None)
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy (resources.assets)")
def test_real_install_resolves_the_documented_sfx_anchor(capsys):
    """sfx **108** is the item-get jingle cited by number in ``docs/BEHAVIOR.md``, ``docs/FORMAT.md`` and
    ``content/siege.py``. If ``sfx-list`` stopped resolving it, all three citations would be unverifiable
    by the reader they were written for."""
    assert cli._cmd_sound_list(_parse(["sfx-list", "--filter", "108"])) == 0
    assert "108  Sounds02/SE00/se000004" in capsys.readouterr().out


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy (resources.assets)")
@pytest.mark.parametrize("kind,verb", sorted(VERBS.items()))
def test_real_install_lists_a_non_trivial_table(kind, verb, capsys):
    """Both manifests must actually extract -- an empty table would still print a well-formed header, so
    the count is what distinguishes "listed" from "silently found nothing"."""
    assert cli._cmd_sound_list(_parse([verb])) == 0
    out = capsys.readouterr().out
    n = int(out.splitlines()[0].split()[0])
    assert n > 50, f"{verb} listed only {n} tracks"
    assert ("Sounds01/BGM_/" if kind == "music" else "Sounds02/SE") in out
