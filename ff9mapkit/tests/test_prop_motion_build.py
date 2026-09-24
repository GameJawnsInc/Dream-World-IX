"""``[[prop]] motion`` THROUGH THE BUILD (sine kit rung 1): content/motion.py + its five build.py hooks + the
campaign guard, on real built bytes.

  * THE DAEMON IS THE PREDICTOR'S -- a built field carries exactly one entry equal to ``motion.entry_bytes`` over
    the movers' REAL slots (read back off the built script by SetModel, never from the build's own bookkeeping),
    identical in every language, byte-identical on a rebuild, reporting once, aiming at movers only.
  * THE ORDER LAW ON THE FINAL BYTES -- ``arming_problems`` is empty on a content-rich field (five NPCs past the two
    Wait fillers, doors, events, an encounter's Main_Reinit), and the activate_block mutant (the daemon armed at
    Main_Init offset 0) is refused, both by the build and on the bytes.
  * ONE REFUSAL TEXT -- every ``motion.problems`` refusal is in ``validate()``, in ``lint_all().errors`` and in
    ``build_field``'s BuildError (THE NOVEL-FIELD / NULL-TARGET laws, the co-rules, the caps).
  * BYTE IDENTITY -- a field without motion never reaches ``motion.arm`` (it is monkeypatched to raise) and the
    vivi-hut oracle still hashes to its manifest golden.
  * THE CAMPAIGN GUARD -- a FORKED member (manifest ``source`` != its id) with motion is refused by
    ``lint_campaign`` and so by ``build_campaign``: the one refusal only the manifest can see.

Template-gated: a build reads the extracted blank-field template, so without it these tests WARN and skip (THE
WORKTREE SKIP TRAP -- a green run there proves nothing about the shipped daemon; run in the MAIN repo). The
campaign guard refuses before anything is built, so that test runs everywhere.
"""

from __future__ import annotations

import re
import warnings
from collections import Counter
from pathlib import Path

import pytest

from ff9mapkit import build, eblint, prop_archetypes
from ff9mapkit.config import LANGS, ModLayout
from ff9mapkit.content import motion
from ff9mapkit.eb import EbScript, edit as eb_edit, opcodes

from ._ebengine import MotionEngine

_HUT = Path(__file__).resolve().parents[1] / "examples" / "vivi-hut" / "hut_int.field.toml"
_ZIDANE = 98                                               # the template player's SetModel


@pytest.fixture()
def templates():
    from ff9mapkit import provision
    if not provision.templates_present():
        warnings.warn(
            "[[prop]] motion's BUILD path went UNVERIFIED in this run: the base templates are not extracted. "
            "This is the WORKTREE SKIP TRAP -- a green run here says nothing about the daemon the build ships. "
            "Re-run in the MAIN repo (C:/gd/Dream-World-IX/ff9mapkit), or `ff9mapkit extract-templates` first.",
            UserWarning)
        pytest.skip("base templates not extracted (run `ff9mapkit extract-templates`; see the warnings summary)")


# ================================================================ fixtures: a novel field, authored as text
_HEAD = """
[field]
id = 30990
name = "MOTB"
area = 11

[camera]
pitch = 45

[walkmesh]
quad = [[-1400, -100], [1400, -100], [1400, -2000], [-1400, -2000]]

[player]
spawn = [0, -1600]
"""


def _prop(prop, pos, extra="", mo=None) -> str:
    return (f'\n[[prop]]\nprop = "{prop}"\npos = [{pos[0]}, {pos[1]}]\n' + (extra + "\n" if extra else "")
            + (f"motion = {mo}\n" if mo else ""))


# 3 movers + 1 STATIC prop seated BETWEEN them (a slot-order slip would aim at it). Every model is unique, so the
# built script's SetModel scan names each object; the balloon and the chest share period 128 (one clock).
_PROPS = [
    ("balloon", (0, -800), "collision = false\nshadow = false",
     '{ radius = 300, period = 128, height = 150, turn = "travel" }'),
    ("scroll", (-750, -1300), "face = 64", None),
    ("letter", (-750, -450), "face = 32\ncollision = false\nshadow = false",
     '{ radius = 250, period = 90, reverse = true, height = 80, turn = "travel", bob = { amp = 60, period = 256 } }'),
    ("chest", (-1000, -1600), "collision = false", "{ to = [-301, -1600], period = 128 }"),
]


def _toml(props=_PROPS, *, motion_on=True, head=_HEAD, extra="") -> str:
    return head + extra + "".join(_prop(n, p, x, mo if motion_on else None) for n, p, x, mo in props)


def _load(tmp_path, text: str, name="f") -> build.FieldProject:
    d = tmp_path / name
    d.mkdir(parents=True, exist_ok=True)
    p = d / "f.field.toml"
    p.write_text(text, encoding="utf-8")
    return build.FieldProject.load(p)


def _build(tmp_path, text: str, name="f"):
    """(FieldResult, {lang: .eb bytes}) of a fresh build_field into its own tmp ModLayout."""
    proj = _load(tmp_path, text, name)
    layout = ModLayout(tmp_path / name / "mod")
    res = build.build_field(proj, layout)
    return res, {lang: layout.eb_path(lang, f"EVT_{proj.name}.eb.bytes").read_bytes() for lang in LANGS}


def _slots_by_model(ebb: bytes) -> dict:
    """model id -> [every entry whose Init runs a SetModel of it] -- the built script's own answer."""
    s = EbScript.from_bytes(ebb)
    out: dict = {}
    for e in s.entries:
        f0 = None if e.empty else e.func_by_tag(0)
        for i in (s.instrs(f0) if f0 is not None else ()):
            if i.op == 0x2F:
                out.setdefault(i.args[0], []).append(e.index)
    return out


def _movers(raw: dict, ebb: bytes) -> list:
    """[(spec, slot)] in TOML order, each slot found by its model in the BUILT bytes (unique by construction)."""
    by_model = _slots_by_model(ebb)
    out = []
    for i, p in enumerate(raw["prop"]):
        spec = motion.parse(p, i)
        if spec is not None:
            (slot,) = by_model[prop_archetypes.resolve(p["prop"])[0]]
            out.append((spec, slot))
    return out


def _daemon(ebb: bytes, movers) -> tuple:
    """(the ONE entry equal to entry_bytes(movers), its bytes, loc) -- asserts it is exactly one, with that loc."""
    want, loc = motion.entry_bytes(movers)
    s = EbScript.from_bytes(ebb)
    hits = [e for e in s.entries if not e.empty and ebb[e.abs_start:e.abs_end] == want]
    assert len(hits) == 1, f"{len(hits)} entries equal the predictor's daemon"
    assert hits[0].loc == loc
    return hits[0].index, want, loc


def _targets(ebb: bytes) -> list:
    """(entry, op, uid) for every 0xAD MoveInstantXZYEx / 0x87 TurnInstantEx anywhere in the script."""
    s = EbScript.from_bytes(ebb)
    return [(e.index, i.op, ebb[i.off + 2]) for e in s.entries if not e.empty for f in e.funcs
            for i in s.instrs(f) if i.op in (motion.MOVE_EX, motion.TURN_EX)]


def _errors(ebb: bytes) -> Counter:
    """eblint ERRORS as (where without its byte offset, message): an insert shifts every offset after it."""
    return Counter((re.sub(r"\s*@\d+", "", i.where), i.message) for i in eblint.errors(eblint.lint_eb(ebb)))


# ================================================================ 20: the build arms the predictor's daemon
def test_build_arms_the_predictors_daemon(tmp_path, templates):
    res, ebs = _build(tmp_path, _toml())
    raw = _load(tmp_path, _toml(), "raw").raw
    us = ebs["us"]
    movers = _movers(raw, us)
    assert [s.model for s, _u in movers] == ["balloon", "letter", "chest"]
    dslot, want, loc = _daemon(us, movers)
    assert loc == 2 * 3                                    # clocks 128 (balloon + chest share it), 90, 256
    mover_slots = [u for _s, u in movers]
    assert motion.arming_problems(us, dslot, mover_slots) == []

    # the static scroll is never an 0xAD/0x87 target -- nothing anywhere in the script aims at anything but a
    # mover, and only the daemon aims at all
    (static,) = _slots_by_model(us)[prop_archetypes.resolve("scroll")[0]]
    tg = _targets(us)
    assert {e for e, _op, _u in tg} == {dslot}
    assert {u for _e, _op, u in tg} == set(mover_slots) and static not in {u for _e, _op, u in tg}
    assert [(op, u) for _e, op, u in tg] == [(op, u) for s, u in movers
                                            for op in ((motion.MOVE_EX,) if s.moves else ())
                                            + ((motion.TURN_EX,) if s.turns else ())]

    # the SHIPPED daemon runs the predictor: every captured operand over a full bob period (every clock wraps)
    ticks = MotionEngine(loc).ticks(want[6:], 257)
    for n, got in enumerate(ticks):
        exp = []
        for s, u in movers:
            p = motion.pose(s, n)
            if s.moves:
                exp.append((motion.MOVE_EX, u, (p.x, p.b, p.z)))
            if s.turns:
                exp.append((motion.TURN_EX, u, p.face))
        assert [(op, u, v if op == motion.MOVE_EX else v[0] & 0xFF) for op, u, v in got] == exp, n

    # every language carries the same daemon in the same slot, armed at the same Main_Init offset
    for lang, ebb in ebs.items():
        assert _daemon(ebb, _movers(raw, ebb))[:2] == (dslot, want), lang
        assert motion.arming_problems(ebb, dslot, mover_slots) == [], lang

    # a rebuild is byte-identical, every language
    _res2, ebs2 = _build(tmp_path, _toml(), "again")
    assert ebs2 == ebs

    # eblint: no NEW error against the same field without motion (the template carries its own, e.g. the empty
    # Main tag-1 body -- those must stay exactly what they were)
    _r, plain = _build(tmp_path, _toml(motion_on=False), "plain")
    for lang in LANGS:
        assert _errors(ebs[lang]) - _errors(plain[lang]) == Counter(), lang

    # the report: the predictor's own lines, once each after seven language builds, in order, nothing else
    want_lines = motion.report_lines(movers, dslot, loc)
    assert [w for w in res.warnings if w in want_lines] == want_lines
    assert [w for w in res.warnings if w.startswith("[[prop]] motion:") or " motion uid " in w] == want_lines


# ================================================================ 21: no motion -> the motion code never runs
def test_no_motion_never_reaches_arm_and_the_oracle_is_byte_exact(tmp_path, monkeypatch, templates):
    from ff9mapkit import provision

    def _boom(*_a, **_k):
        raise AssertionError("motion.arm ran on a field with no motion -- THE BYTE-IDENTITY guard is gone")

    monkeypatch.setattr(motion, "arm", _boom)
    # the vivi-hut oracle (no props) still hashes to its manifest golden
    build.build_mod([build.FieldProject.load(_HUT)], tmp_path / "hut", mod_name="FF9CustomMap")
    hut = ModLayout(tmp_path / "hut").eb_path("us", "EVT_HUT_INT.eb.bytes").read_bytes()
    assert provision.sha256(hut) == provision.load_manifest()["goldens"]["EVT_HUT_INT.eb.bytes/us"]
    # a prop-bearing field -- every static-prop key a mover would also carry -- builds, and nothing moves
    static = [("balloon", (0, -800), "collision = false\nshadow = false", None),
              ("letter", (-750, -450), "face = 32\nshadow = true", None),
              ("scroll", (-750, -1300), "face = 64", None)]
    res, ebs = _build(tmp_path, _toml(static))
    for ebb in ebs.values():
        assert _targets(ebb) == []
    assert not any("motion" in w for w in res.warnings)


# ================================================================ 22: validate, lint and build agree
def _mover(x, z, extra="collision = false", mo='{ radius = 200, period = 128, turn = "travel" }', prop="balloon"):
    return _prop(prop, (x, z), extra, mo)


_NPC = '\n[[npc]]\nname = "Vivi"\npreset = "vivi"\npos = [300, -600]\n'
_HEAD_WITH = lambda line: _HEAD.replace('area = 11\n', f"area = 11\n{line}\n")   # noqa: E731

# (id, field text, a substring the refusal must carry -- so a problems() that returned some OTHER text fails too)
_REFUSALS = [
    ("unknown-key", _HEAD + _mover(0, -800, mo="{ raduis = 300, period = 128 }"), "unknown key(s) raduis"),
    ("collision", _HEAD + _mover(0, -800, extra=""), "collision = false"),
    ("shadow", _HEAD + _mover(0, -800, mo="{ radius = 200, period = 128, height = 100 }"), "shadow = false"),
    ("requires-flag", _HEAD + _mover(0, -800, "collision = false\nrequires_flag = 8712"), "NULL-TARGET"),
    ("attach-to", _HEAD + _NPC + _mover(0, -800, 'collision = false\nattach_to = "Vivi"'), "NULL-TARGET"),
    ("composite", _HEAD + _mover(0, -800, "", '{ turn = "spin", period = 64 }', prop="save_point"), "composite"),
    ("npc-motion", _HEAD + _NPC + 'motion = { turn = "spin", period = 64 }\n', "[[npc]] 'Vivi' motion"),
    ("source-field", _HEAD_WITH("source_field = 300") + _mover(0, -800), "NOVEL-FIELD"),
    ("verbatim-eb", _HEAD + _mover(0, -800) + "\n[verbatim_eb]\ndonor = 300\n", "[verbatim_eb]"),
    ("mapconfig", _HEAD_WITH('mapconfig = "x.mcf"')
     + _mover(0, -800, "collision = false\nshadow = false", "{ radius = 200, period = 128, height = 100 }"),
     "MapConfigData"),
    ("17-movers", _HEAD + "".join(_mover(-1200 + 150 * i, -1000) for i in range(17)), "at most 16"),
    ("9-clocks", _HEAD + "".join(_mover(-1200 + 250 * i, -1000, mo=f"{{ radius = 100, period = {10 + i} }}")
                                 for i in range(9)), "at most 8 distinct periods"),
]


@pytest.mark.parametrize("text,needle", [r[1:] for r in _REFUSALS], ids=[r[0] for r in _REFUSALS])
def test_validate_lint_and_build_refuse_with_one_text(tmp_path, text, needle, templates):
    proj = _load(tmp_path, text)
    mine = motion.problems(proj.raw, donor=build.donor_field_id(proj.raw))
    assert mine and any(needle in m for m in mine), mine
    v = build.validate(proj)
    lint = build.lint_all(proj).errors
    with pytest.raises(build.BuildError) as ei:
        build.build_field(proj, ModLayout(tmp_path / "mod"))
    for m in mine:
        assert m in v and m in lint and m in str(ei.value), m


# ================================================================ 23: THE ORDER LAW on a content-rich field
_RICH = _HEAD + """
[encounter]
scene = 67
freq = 200

[[gateway]]
to = 30991
entrance = 0
zone = [[-400, -1850], [400, -1850], [400, -2000], [-400, -2000]]

[[gateway]]
to = 30992
entrance = 0
zone = [[-1400, -900], [-1250, -900], [-1250, -1200], [-1400, -1200]]

[[event]]
name = "note"
zone = [[900, -1500], [1100, -1500], [1100, -1700], [900, -1700]]
message = "A note."
once = true

[[event]]
name = "coin"
zone = [[900, -300], [1100, -300], [1100, -500], [900, -500]]
message = "A coin."
gil = 10
once = true
""" + "".join(f'\n[[npc]]\nname = "N{i}"\npreset = "vivi"\npos = [{-1000 + 450 * i}, -250]\ndialogue = "Hi {i}."\n'
              for i in range(5)) + "".join(_prop(n, p, x, mo) for n, p, x, mo in (
    ("balloon", (0, -800), "collision = false\nshadow = false",
     '{ radius = 300, period = 128, height = 150, turn = "travel" }'),
    ("chest", (-1000, -1600), "collision = false", "{ to = [-301, -1600], period = 150 }"),
    ("fish", (750, -1100), "face = 128", '{ turn = "swing", swing = 40, period = 75, phase = 0.25 }')))


class _PrependEdit:
    """``content.motion``'s view of eb.edit with every insert forced to Main_Init offset 0 -- the activate_block
    shape (a prepend) THE ORDER LAW exists to refuse. It swaps the NAME motion reads, never the eb.edit module
    every other build pass shares."""

    def __getattr__(self, name):
        return getattr(eb_edit, name)

    @staticmethod
    def insert_in_function(data, entry_index, func_tag, rel_off, ins):
        return eb_edit.insert_in_function(data, entry_index, func_tag, 0, ins)


def test_order_law_holds_on_a_content_rich_field_and_refuses_the_prepend(tmp_path, monkeypatch, templates):
    _res, ebs = _build(tmp_path, _RICH)
    raw = _load(tmp_path, _RICH, "raw").raw
    us = ebs["us"]
    movers = _movers(raw, us)
    slots = [u for _s, u in movers]
    dslot, _want, _loc = _daemon(us, movers)
    assert motion.arming_problems(us, dslot, slots) == []

    # the content really crowds Main_Init: the NPCs, doors and events outrun the two Wait fillers, so the movers'
    # InitObjects are PREPENDED -- ahead of the player's own (an "after the player" arming would come too early)
    # -- and the encounter ships a tag-10 Main_Reinit
    s = EbScript.from_bytes(us)
    mi = s.entry(0).func_by_tag(0)
    body = list(s.instrs(mi))
    assert sum(i.op == 0x09 for i in body) >= 9 and s.entry(0).func_by_tag(10) is not None
    (player,) = _slots_by_model(us)[_ZIDANE]
    objs = {i.args[0]: i.off for i in body if i.op == 0x09}
    assert max(objs[u] for u in slots) < objs[player]
    (ic,) = [i for i in body if i.op == 0x07 and i.args[0] == dslot]
    assert ic.off > max(objs[u] for u in slots)

    # the mutant ON THE BYTES: the InitCode neutralised in place (a JMP, no yield) and re-armed at offset 0
    mut = eb_edit.skip_range(us, ic.off, ic.end - ic.off)
    mut = eb_edit.insert_in_function(mut, 0, 0, 0, opcodes.init_code(dslot, 0))
    bad = motion.arming_problems(mut, dslot, slots)
    assert bad and all("ORDER LAW" in b for b in bad) and len(bad) == len(slots), bad

    # the mutant IN THE BUILD: arm()'s own insert forced to a prepend -> the build refuses, never ships it
    monkeypatch.setattr(motion, "eb_edit", _PrependEdit())
    with pytest.raises(build.BuildError, match="ORDER LAW"):
        _build(tmp_path, _RICH, "mutant")


# ================================================================ 24: the campaign guard (no templates needed)
_MOVER_TOML = ('\n[[prop]]\nprop = "balloon"\npos = [0, -800]\ncollision = false\nshadow = false\n'
               'motion = { radius = 200, period = 128, height = 100, turn = "travel" }\n')


def test_campaign_refuses_motion_on_a_forked_member(tmp_path):
    from ff9mapkit import campaign
    plan = campaign.new_campaign("MOC", "FF9CustomMap-moc", tmp_path, id_base=30100)
    campaign.add_field(plan, tmp_path, name="NOVEL")               # blank rooms, fully offline
    campaign.add_field(plan, tmp_path, name="FORKED")
    for m in plan.members:
        t = tmp_path / m.toml_rel
        t.write_text(t.read_text(encoding="utf-8") + _MOVER_TOML, encoding="utf-8", newline="\n")
    errs, _w = campaign.lint_campaign(plan, tmp_path)
    assert not [e for e in errs if "motion" in e], errs            # a novel member (source 0) may move props

    # the manifest records FORKED as a fork of 300, which its toml does not (a toml written before source_field
    # was): validate cannot see the donor, so the manifest is the only witness
    plan.members[1].real_id = 300
    campaign._save_plan(plan, tmp_path)
    plan = campaign.load_campaign(tmp_path / "campaign.toml")
    fraw = build.FieldProject.load(tmp_path / plan.members[1].toml_rel).raw
    assert build.donor_field_id(fraw) is None and motion.problems(fraw, donor=None) == []
    errs, _w = campaign.lint_campaign(plan, tmp_path)
    hits = [e for e in errs if "motion" in e]
    assert len(hits) == 1 and hits[0].startswith("member FORKED:"), errs
    assert "donor field 300" in hits[0] and "NOVEL-FIELD LAW" in hits[0]

    # build-all runs that lint first: refused with the same text, before a byte is written
    with pytest.raises(campaign.CampaignError) as ei:
        campaign.build_campaign(tmp_path / "campaign.toml", out=tmp_path / "dist")
    assert hits[0] in str(ei.value)
    assert not (tmp_path / "dist").exists()


# ================================================================ the raised-floor advisory
_RAISED_OBJ = ("v -1400 -600 -100\nv 1400 -600 -100\nv 1400 -600 -2000\nv -1400 -600 -2000\n"
               "f 1 2 3\nf 1 3 4\n")


def test_lint_warns_a_mover_over_a_floor_not_at_y0(tmp_path):
    """[the critic's raised-floor gap] motion height is ABSOLUTE (0 = the y-0 plane, the only floor proven
    in-game): a position mover whose path runs over walkmesh at another y gets a lint advisory; the same mover on
    the flat y-0 quad gets none, and a turn-only mover (no 0xAD) is never flagged."""
    mover = [("balloon", (0, -800), "collision = false\nshadow = false",
              '{ radius = 300, period = 128, height = 150, turn = "travel" }'),
             ("sword", (600, -1300), "", '{ turn = "spin", period = 64 }')]
    raised = _HEAD.replace('quad = [[-1400, -100], [1400, -100], [1400, -2000], [-1400, -2000]]',
                           'obj = "raised.obj"\nframe = "world"')
    proj = _load(tmp_path, _toml(mover, head=raised), "raised")
    (tmp_path / "raised" / "raised.obj").write_text(_RAISED_OBJ, encoding="utf-8")
    notes = [n for n in build.lint_all(proj).logic if "runs over walkmesh at y" in n]
    assert len(notes) == 1 and "'balloon'" in notes[0] and "-600" in notes[0], notes
    flat = _load(tmp_path, _toml(mover), "flat")
    assert not [n for n in build.lint_all(flat).logic if "runs over walkmesh at y" in n]
