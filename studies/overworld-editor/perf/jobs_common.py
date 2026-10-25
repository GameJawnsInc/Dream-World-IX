"""Lane "jobs" shared setup: the worktree package pinned, the draft this lane's probes run against, and the Check /
Accept argv each World-tab card builds, made by the SAME edit-module ``command()`` the card's ``_cmd`` calls, with the
handles a lab recorded the card using (out/c*_prep.json "argvs").

Nothing here writes under the install: the draft is made by world.draft.ensure_draft under out/perf/jobs/ (which
refuses a root inside the install), and every argv targets that draft.
"""
from __future__ import annotations

import sys
from pathlib import Path

WT = Path(r"C:\gd\Dream-World-IX\.claude\worktrees\terrain-shaping-continue-4647b2")
KIT = WT / "ff9mapkit"
if str(KIT) not in sys.path:
    sys.path.insert(0, str(KIT))
import ff9mapkit  # noqa: E402

assert Path(ff9mapkit.__file__).resolve().is_relative_to(KIT.resolve()), ff9mapkit.__file__

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
SOURCE = GAME / "FF9CustomMap-world"
OUT = WT / "studies" / "overworld-editor" / "out" / "perf" / "jobs"
DRAFTS = OUT / "drafts"
PERF = WT / "studies" / "overworld-editor" / "perf"


def draft(root=DRAFTS) -> Path:
    from ff9mapkit.world import draft as D
    return D.ensure_draft(SOURCE, game=GAME, root=root)


def kit_cwd() -> Path:
    """workspace/worldforest.kit_cwd, without importing Qt: the dir holding the package."""
    return Path(ff9mapkit.__file__).resolve().parents[1]


def prefix():
    """What CarryTool.argv / _run_job put before a card's _cmd."""
    return [sys.executable, "-m", "ff9mapkit", "--game", str(GAME)]


# The handles each lab drove its card with (the argv the card's runner captured: out/c*_prep.json).
SPOTS = {
    "forest": dict(center=(1400.0, -460.0), donor=(13, 15)),                      # c1_prep.json
    "mountain": dict(center=(190.0, -1228.0), donor="0,0", rot_deg=300, rock_height=1.5),   # c2_prep.json
    "hill": dict(center=(80.0, -472.0)),                                          # c6h_prep.json
    "island": dict(center=(288.0, -352.0), seed=5.0),                             # c5i_prep.json
    "carry": dict(cell=(3, 5), donor=(7, 17), rot=90),                            # c5t_prep.json
    "coast": dict(cell=(2, 7), verb="cliff-bump", spec="174.7695,-512.0000:179.5586,-448.0000:2.5"),  # c5c_prep
    "sink": dict(at=(249.556, -565.214)),                                         # c5_prep.json
    "river": dict(shift=None, at=(512, 192), move_from=(512, 128)),               # c5r_prep.json
}


def card_calls(verb, target, *, kind, report, report4=None, spot=None):
    """The list of argv tails (after ``python -m ff9mapkit --game G``) a card runs for ``kind`` (check|accept):
    Check = [_cmd(dry_run=True)], Accept = _accept_calls (two for the sink and the coast morph)."""
    from ff9mapkit.world import (coastedit as CE, forestedit as FE, hilledit as HE, islandedit as IE,
                                 mountainedit as ME, riveredit as RE, sinkedit as SE, transplantedit as TE)
    s = dict(SPOTS[verb] if spot is None else spot)
    dry = kind == "check"
    if verb == "forest":
        return [FE.command(target, s["center"], s["donor"], dry_run=dry, report=report)]
    if verb == "mountain":
        return [ME.command(target, s["center"], s["donor"], rot_deg=s.get("rot_deg", 0), rock_height=s.get(
            "rock_height", 1.0), ground=s.get("ground", "grass"), dry_run=dry, report=report)]
    if verb == "hill":
        return [HE.command(target, s["center"], dry_run=dry, report=report)]
    if verb == "island":
        return [IE.command(target, s["center"], seed=s["seed"], dry_run=dry, report=report)]
    if verb == "carry":
        return [TE.command(target, s["cell"], s["donor"], rot=s.get("rot", 0), size=s.get("size", (1, 1)),
                           dry_run=dry, report=report)]
    if verb == "coast":
        if dry:
            return [CE.command(target, s["cell"], s["verb"], s["spec"], dry_run=True, report=report)]
        return CE.commands(target, s["cell"], s["verb"], s["spec"], report=report, report4=report4)
    if verb == "sink":
        if dry:
            return [SE.command(target, s["at"], dry_run=True, report=report)]
        return SE.commands(target, s["at"], report=report, report4=report4)
    if verb == "river":
        # the card: RE.command(target, self._shift, move_from=self.river_at()) -- both are block shifts
        return [RE.command(target, RE.shift_of(s["at"]), move_from=RE.shift_of(s["move_from"]), dry_run=dry,
                           report=report)]
    raise KeyError(verb)


VERBS = list(SPOTS)


def _swap_report(argv, report, report4=None):
    out = [str(a) for a in argv]
    for i, a in enumerate(out):
        if a == "--report-json":
            out[i + 1] = str(report4 if out[i + 1].endswith("verdict4.json") and report4 else report)
    return out


def spots():
    import json
    p = OUT / "spots.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def check_argv(verb, target, report):
    """The full Check argv: the one the real card's runner received at the lane's lawful spot (jobs_spots.py), else
    the lab spot's (a refusal where the live folder has moved on)."""
    rec = spots().get(verb) or {}
    if rec.get("check_argv"):
        a = _swap_report(rec["check_argv"], report)
        assert str(target) in a, (target, a)
        return a
    return prefix() + card_calls(verb, target, kind="check", report=report)[0]


def accept_argvs(verb, target, report, report4):
    rec = spots().get(verb) or {}
    if rec.get("accept_calls"):
        return [prefix() + _swap_report(c, report, report4) for c in rec["accept_calls"]]
    return [prefix() + c for c in card_calls(verb, target, kind="accept", report=report, report4=report4)]


def lawful(verb) -> bool:
    return verb in ("forest", "carry") or bool((spots().get(verb) or {}).get("check_argv"))
