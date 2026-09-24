"""The ``ff9mapkit motion <field.toml> [--csv OUT] [--ticks N]`` lane, driven end to end (sine kit rung 1).

The verb is a READER of ``content/motion.py`` and nothing else: the refusals are ``motion.problems`` (the texts
validate, lint and the build share), the report is ``motion.report_lines`` without uids, and the CSV is
``motion.csv_rows`` -> ``motion.pose`` (THE PREDICTOR IS THE ORACLE). Each test pins the CLI's output to the
module's own answer, so a CLI that re-derived any of it -- or dropped a refusal -- fails here. Pure: no build,
no templates, never skips.

THE CSV TICK CAP: a cycle is the lcm of a mover's periods; two coprime legal periods (8191, 8192) make it
~67 million ticks, so the default CSV stops at ``motion.PERIOD_MAX`` ticks (one whole period of every channel)
with a note -- the tick-cap test would hang without it.
"""

from __future__ import annotations

import csv
import tomllib

import pytest

from ff9mapkit import build, cli
from ff9mapkit.content import motion

_HEAD = """
[field]
id = 30946
name = "SINE1"
"""

# the spec's five examples (rung 0's A and B exactly, an odd-axis shuttle, a solid reverse spin, a swing) plus
# a STATIC prop the verb must not report
_MOVERS = """
[[prop]]
prop = "balloon"
pos = [0, -800]
collision = false
shadow = false
motion = { radius = 300, period = 128, height = 150, turn = "travel" }

[[prop]]
prop = "scroll"
pos = [-750, -1300]
face = 64

[[prop]]
prop = "cask"
pos = [0, -800]
collision = false
shadow = false
motion = { radius = 300, period = 128, phase = 0.5, height = 150, turn = "travel", bob = { amp = 60, period = 256 } }

[[prop]]
prop = "chest"
pos = [-1000, -1600]
collision = false
motion = { to = [-301, -1600], period = 150 }

[[prop]]
prop = "sword"
pos = [750, -350]
motion = { turn = "spin", period = 64, reverse = true }

[[prop]]
prop = "fish"
pos = [750, -1350]
face = 128
motion = { turn = "swing", swing = 40, period = 75, phase = 0.25 }
"""


def _write(tmp_path, body: str, name: str = "m.field.toml"):
    p = tmp_path / name
    p.write_text(_HEAD + body, encoding="utf-8")
    return p


def _specs(path) -> list:
    """The movers as the module parses them (TOML order, idx = the [[prop]] index) -- the test's oracle."""
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    return [s for i, p in enumerate(raw.get("prop") or []) for s in [motion.parse(p, i)] if s is not None]


def _read_csv(path) -> list:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.reader(fh))


def _by_prop(rows) -> dict:
    out: dict = {}
    for r in rows:
        out.setdefault(int(r[0]), []).append(r)
    return out


def _pose_row(spec, n: int, p) -> list:
    return [str(spec.idx), spec.label, str(n), str(p.x), str(p.height), str(p.z),
            "" if p.face is None else str(p.face)]


# ---- the report ----------------------------------------------------------------------------------

def test_stdout_is_the_modules_report_without_uids(tmp_path, capsys):
    f = _write(tmp_path, _MOVERS)
    rc = cli.main(["motion", str(f)])
    out = capsys.readouterr()
    assert rc == 0, out.err
    specs = _specs(f)
    assert [s.idx for s in specs] == [0, 2, 3, 4, 5]                 # the static prop (1) is no mover
    assert out.out.splitlines() == motion.report_lines([(s, None) for s in specs])
    assert " uid " not in out.out and "daemon entry" not in out.out    # slots bind at build, not here
    assert out.err == ""


def test_the_verb_is_pure_no_build_runs(tmp_path, capsys, monkeypatch):
    """No build, no templates: the lane must not reach the compile (a fresh worktree has no template cache)."""
    def boom(*_a, **_k):
        raise AssertionError("ff9mapkit motion ran the build")
    for name in ("build_field", "build_script", "validate", "lint_all"):
        monkeypatch.setattr(build, name, boom)
    rc = cli.main(["motion", str(_write(tmp_path, _MOVERS)), "--csv", str(tmp_path / "o.csv")])
    assert rc == 0, capsys.readouterr().err


# ---- the CSV -------------------------------------------------------------------------------------

def test_csv_rows_are_the_predictors_path_one_cycle_each(tmp_path, capsys):
    f = _write(tmp_path, _MOVERS)
    out_csv = tmp_path / "path.csv"
    rc = cli.main(["motion", str(f), "--csv", str(out_csv)])
    out = capsys.readouterr()
    assert rc == 0, out.err
    rows = _read_csv(out_csv)
    assert tuple(rows[0]) == ("prop", "label", "tick", "x", "height", "z", "face")
    got = _by_prop(rows[1:])
    specs = _specs(f)
    assert sorted(got) == [s.idx for s in specs]
    for s in specs:
        assert s.cycle <= motion.PERIOD_MAX                          # none capped: exactly one cycle each
        want = [_pose_row(s, n, p) for n, p in enumerate(motion.path(s))]
        assert got[s.idx] == want, s.label
    cask = next(s for s in specs if s.model == "cask")
    assert len(got[cask.idx]) == 256                                 # lcm(128, 256), not the orbit's 128
    fish = next(s for s in specs if s.model == "fish")
    assert got[fish.idx][0][6] == str(motion.pose(fish, 0).face)     # a turning mover carries its facing byte
    chest = next(s for s in specs if s.model == "chest")
    assert {r[6] for r in got[chest.idx]} == {""}                    # a non-turning one leaves it blank
    assert out.err == ""                                             # no cap, no note
    assert out.out.splitlines()[:-1] == motion.report_lines([(s, None) for s in specs])
    assert out.out.splitlines()[-1] == f"wrote {out_csv} ({len(rows) - 1} rows, {len(specs)} mover(s))"


def test_ticks_sets_every_movers_length(tmp_path, capsys):
    f = _write(tmp_path, _MOVERS)
    out_csv = tmp_path / "t.csv"
    rc = cli.main(["motion", str(f), "--csv", str(out_csv), "--ticks", "5"])
    assert rc == 0, capsys.readouterr().err
    got = _by_prop(_read_csv(out_csv)[1:])
    for s in _specs(f):
        assert got[s.idx] == [_pose_row(s, n, p) for n, p in enumerate(motion.path(s, 0, 5))]


def test_ticks_without_csv_or_below_one_is_refused(tmp_path, capsys):
    f = _write(tmp_path, _MOVERS)
    assert cli.main(["motion", str(f), "--ticks", "10"]) == 2        # a silently ignored flag is not acceptable
    assert "--csv" in capsys.readouterr().err
    assert cli.main(["motion", str(f), "--csv", str(tmp_path / "z.csv"), "--ticks", "0"]) == 2
    assert not (tmp_path / "z.csv").exists()


_COPRIME = """
[[prop]]
prop = "hand_bell"
pos = [0, -800]
collision = false
shadow = false
motion = { radius = 200, period = 8191, bob = { amp = 40, period = 8192 } }

[[prop]]
prop = "balloon"
pos = [0, -800]
collision = false
shadow = false
motion = { radius = 300, period = 128, height = 150, turn = "travel" }
"""


def test_csv_default_is_capped_at_the_longest_legal_period(tmp_path, capsys):
    """THE CSV TICK CAP: P 8191 with a bob of 8192 repeats every 67,100,672 ticks. The default CSV stops at
    PERIOD_MAX ticks for THAT mover only, with a note naming it; a short-cycle mover still gets its whole
    cycle; an explicit --ticks past the cap is honoured as given."""
    f = _write(tmp_path, _COPRIME)
    bell, balloon = _specs(f)
    assert bell.cycle == 8191 * 8192 > motion.PERIOD_MAX
    out_csv = tmp_path / "cap.csv"
    rc = cli.main(["motion", str(f), "--csv", str(out_csv)])
    out = capsys.readouterr()
    assert rc == 0, out.err
    got = _by_prop(_read_csv(out_csv)[1:])
    assert len(got[bell.idx]) == motion.PERIOD_MAX
    assert got[bell.idx][-1] == _pose_row(bell, motion.PERIOD_MAX - 1, motion.pose(bell, motion.PERIOD_MAX - 1))
    assert got[balloon.idx] == [_pose_row(balloon, n, p) for n, p in enumerate(motion.path(balloon))]
    notes = [ln for ln in out.err.splitlines() if ln.startswith("note:")]
    assert len(notes) == 1 and bell.label in notes[0] and str(bell.cycle) in notes[0], out.err
    assert balloon.label not in out.err

    rc = cli.main(["motion", str(f), "--csv", str(out_csv), "--ticks", str(motion.PERIOD_MAX + 3)])
    out = capsys.readouterr()
    assert rc == 0 and "note:" not in out.err, out.err
    assert len(_by_prop(_read_csv(out_csv)[1:])[bell.idx]) == motion.PERIOD_MAX + 3


def test_the_ticks_help_names_the_modules_cap():
    """The parser's help hard-codes the cap (it must not import the trig tables to build a parser); pin it to
    the one owner of the number."""
    import argparse
    sub = next(a for a in cli.build_parser()._actions if isinstance(a, argparse._SubParsersAction))
    ticks = next(a for a in sub.choices["motion"]._actions if "--ticks" in a.option_strings)
    assert f"{motion.PERIOD_MAX} ticks" in ticks.help


# ---- the refusals --------------------------------------------------------------------------------

# case -> (extra [field] lines, body)
_BAD = {
    "radius 0": ("", """
[[prop]]
prop = "balloon"
pos = [0, -800]
collision = false
shadow = false
motion = { radius = 0, period = 128, height = 150 }
"""),
    "a forked field": ("source_field = 100\n", """
[[prop]]
prop = "sword"
pos = [750, -350]
motion = { turn = "spin", period = 64 }
"""),
    "an npc with motion": ("", """
[[npc]]
name = "walker"
pos = [0, 0]
motion = { radius = 100, period = 64 }
"""),
    "a position mover left solid": ("", """
[[prop]]
prop = "chest"
pos = [-1000, -1600]
motion = { to = [-301, -1600], period = 150 }
"""),
    "an airborne mover with a shadow": ("", """
[[prop]]
prop = "cask"
pos = [0, -800]
collision = false
motion = { bob = { amp = 60, period = 256 } }
"""),
}


@pytest.mark.parametrize("case", sorted(_BAD))
def test_an_invalid_toml_exits_1_with_the_shared_refusals(tmp_path, capsys, case):
    extra, body = _BAD[case]
    f = tmp_path / "bad.field.toml"
    f.write_text(_HEAD + extra + body, encoding="utf-8")
    out_csv = tmp_path / "never.csv"
    rc = cli.main(["motion", str(f), "--csv", str(out_csv)])
    out = capsys.readouterr()
    assert rc == 1, (case, out.out, out.err)
    assert out.out == "" and not out_csv.exists()                    # no report, no CSV past a refusal
    raw = build.FieldProject.load(f).raw
    want = motion.problems(raw, donor=build.donor_field_id(raw))
    assert want, case                                                # the fixture really is refused
    assert out.err.splitlines() == [f"error: {p}" for p in want]     # the texts validate/lint/build print


def test_a_field_without_motion_says_so(tmp_path, capsys):
    f = _write(tmp_path, '\n[[prop]]\nprop = "scroll"\npos = [0, 0]\n')
    assert cli.main(["motion", str(f)]) == 2
    out = capsys.readouterr()
    assert out.out == "" and "no [[prop]] with a motion table" in out.err


def test_an_unreadable_toml_is_a_load_failure_not_a_traceback(tmp_path, capsys):
    f = tmp_path / "broken.field.toml"
    f.write_text("[[prop]\nprop = ", encoding="utf-8")
    assert cli.main(["motion", str(f)]) == 2
    assert "failed to load" in capsys.readouterr().err
