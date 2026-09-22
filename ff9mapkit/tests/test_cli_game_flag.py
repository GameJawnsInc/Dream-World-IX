"""A root-level ``--game`` must survive into EVERY subcommand.

``build_parser()`` defines ``--game`` on the root parser; a subparser that redefines it with
``default=None`` has argparse apply that default AFTER the root parse, so ``ff9mapkit --game /x <verb>``
silently landed ``game=None`` for that verb -- the install the user typed was discarded with no message.
The cure is ``default=argparse.SUPPRESS`` on the subparser's copy: it then contributes nothing unless the
flag is typed at the subcommand, and the root value carries through (``cli.py``'s summon-reskin lane
documents the same rule in its help text). Twenty subparsers already did this; five did not. The parser
walk below is the guard that catches the next one.
"""

from __future__ import annotations

import argparse

from ff9mapkit import cli


def _subparsers(p: argparse.ArgumentParser) -> dict:
    sub = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    seen, out = set(), {}
    for name, sp in sub.choices.items():               # an alias maps to the SAME parser object
        if id(sp) not in seen:
            seen.add(id(sp))
            out[name] = sp
    return out


def test_every_subcommand_game_flag_lets_the_root_value_through():
    clobber = sorted(
        name for name, sp in _subparsers(cli.build_parser()).items()
        for a in sp._actions
        if "--game" in a.option_strings and not a.required and a.default is not argparse.SUPPRESS)
    assert not clobber, (
        "these subcommands redefine --game with a real default, so a root-level --game is silently "
        "discarded; use default=argparse.SUPPRESS: " + ", ".join(clobber))


def test_root_game_reaches_a_verb_that_does_not_redefine_it():
    assert cli.build_parser().parse_args(["--game", "/x", "doctor"]).game == "/x"


def test_root_game_reaches_a_verb_that_redefines_it():
    a = cli.build_parser().parse_args(["--game", "/x", "world-coastnav", "--mod-folder", "M"])
    assert a.game == "/x"                              # was None


def test_the_subcommands_own_game_still_wins():
    a = cli.build_parser().parse_args(["world-coastnav", "--mod-folder", "M", "--game", "/y"])
    assert a.game == "/y"


def test_no_game_anywhere_is_the_root_default():
    a = cli.build_parser().parse_args(["world-coastnav", "--mod-folder", "M"])
    assert a.game is None
