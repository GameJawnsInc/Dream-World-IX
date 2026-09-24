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
    notes = [n for n in build.lint_all(proj).logic if "runs over walkmesh at height" in n]
    # the walkmesh y is up-NEGATIVE: y -600 is 600 up, the height = 600 an author would write (the [[jump]] rule)
    assert len(notes) == 1 and "'balloon'" in notes[0] and "height [600]" in notes[0], notes
    assert "-600" not in notes[0]
    flat = _load(tmp_path, _toml(mover), "flat")
    assert not [n for n in build.lint_all(flat).logic if "runs over walkmesh at height" in n]


# a y-0 floor with a small platform 200 up (y -200) over the orbit's centre -- the orbit (r 300) never crosses it
_RING_OBJ = ("v -1400 0 -100\nv 1400 0 -100\nv 1400 0 -2000\nv -1400 0 -2000\n"
             "v -100 -200 -700\nv 100 -200 -700\nv 100 -200 -900\nv -100 -200 -900\n"
             "f 1 2 3\nf 1 3 4\nf 5 6 7\nf 5 7 8\n")


def test_lint_floor_note_skips_an_orbits_centre(tmp_path):
    """[review: the orbit centre is not on the path] An orbit around a raised centre, whose whole path is over the
    height-0 floor, gets no advisory; a bob-only mover standing ON the platform (its anchor is its spot) does."""
    ring = _HEAD.replace('quad = [[-1400, -100], [1400, -100], [1400, -2000], [-1400, -2000]]',
                         'obj = "ring.obj"\nframe = "world"')
    orbit = [("balloon", (0, -800), "collision = false\nshadow = false",
              '{ radius = 300, period = 128, height = 150, turn = "travel" }')]
    proj = _load(tmp_path, _toml(orbit, head=ring), "orbit")
    (tmp_path / "orbit" / "ring.obj").write_text(_RING_OBJ, encoding="utf-8")
    assert not [n for n in build.lint_all(proj).logic if "runs over walkmesh" in n]
    spot = [("balloon", (0, -800), "collision = false\nshadow = false", '{ height = 250, bob = { amp = 20, period = 60 } }')]
    proj2 = _load(tmp_path, _toml(spot, head=ring), "spot")
    (tmp_path / "spot" / "ring.obj").write_text(_RING_OBJ, encoding="utf-8")
    notes = [n for n in build.lint_all(proj2).logic if "runs over walkmesh" in n]
    assert len(notes) == 1 and "200" in notes[0], notes


def test_lint_reports_a_malformed_prop_key_instead_of_raising(tmp_path):
    """[review: lint's never-raise contract] A mover with a non-integer ``face`` used to escape parse() as a bare
    ValueError, so lint_all (and every deploy's lint) died with a traceback. It is now one refusal, reported."""
    bad = [("balloon", (0, -800), 'collision = false\nshadow = false\nface = "north"',
            '{ radius = 300, period = 128, height = 150, turn = "travel" }')]
    proj = _load(tmp_path, _toml(bad), "bad")
    rep = build.lint_all(proj)                                   # must not raise
    hits = [n for n in [*rep.errors, *rep.logic] if "face must be an integer" in n]
    assert hits, (rep.errors, rep.logic)
    assert not [n for n in rep.logic if "could not finish" in n]


def test_lint_projects_each_bob_through_the_fields_camera(tmp_path):
    """[owner: "I don't see the cask bobbing"] lint projects every bob through the field's own camera: the bench
    cask's slow bob (+-60 / 256 on a 128-tick orbit) is flagged, the same orbit with a 4x faster bob is not."""
    slow = [("cask", (0, -800), "collision = false\nshadow = false",
             '{ radius = 300, period = 128, phase = 0.5, height = 150, turn = "travel", bob = { amp = 60, period = 256 } }')]
    fast = [("cask", (0, -800), "collision = false\nshadow = false",
             '{ radius = 300, period = 128, height = 150, turn = "travel", bob = { amp = 120, period = 32 } }')]
    notes = [n for n in build.lint_all(_load(tmp_path, _toml(slow), "slow")).logic if "bob (" in n]
    assert len(notes) == 1 and "folds into the path" in notes[0], notes
    assert not [n for n in build.lint_all(_load(tmp_path, _toml(fast), "fast")).logic if "bob (" in n]


_TWO_CAMERAS = """
[field]
id = 30990
name = "MOTB"
area = 11

[[camera]]
pitch = 48
yaw = {yaw0}
[[camera]]
pitch = 48
yaw = {yaw1}

[[camera_zone]]
to_camera = 1
zone = [[500, -150], [900, -150], [900, -550], [500, -550]]
[[camera_zone]]
to_camera = 0
zone = [[-900, -150], [-500, -150], [-500, -550], [-900, -550]]

[walkmesh]
quad = [[-1400, -100], [1400, -100], [1400, -2000], [-1400, -2000]]

[player]
spawn = [0, -1600]
"""


_SHUTTLE_X = [("balloon", (-600, -900), "collision = false\nshadow = false",
               "{ to = [600, -900], period = 128, height = 150, bob = { amp = 100, period = 64 } }")]


def _two(tmp_path, yaw0, yaw1, name="two"):
    return _load(tmp_path, _toml(_SHUTTLE_X, head=_TWO_CAMERAS.format(yaw0=yaw0, yaw1=yaw1)), name)


@pytest.mark.parametrize("yaws, bad", [((0, 90), 1), ((90, 0), 0)], ids=["fails_on_1", "fails_on_0"])
def test_lint_judges_a_bob_through_every_camera(tmp_path, yaws, bad):
    """[review: camera 0 only; then claims-3: the test passed with the LAST camera only] An x-shuttle with a +-100
    bob is sideways to a yaw-0 camera (the bob reads) but runs toward a yaw-90 one (the shuttle is depth there, and
    the bob folds into it). Whichever index the yaw-90 camera has, lint names it, and only it, in ONE note."""
    notes = [n for n in build.lint_all(_two(tmp_path, *yaws)).logic if "bob (" in n]
    assert len(notes) == 1 and f"on camera {bad}:" in notes[0], notes


def test_an_unresolvable_camera_does_not_silence_the_others(tmp_path, monkeypatch):
    """[review claims-4: the per-camera guard was untested] Camera 0 fails to resolve (as an unextracted borrow .bgx
    does); camera 1's note still comes out, and nothing says the lint could not finish."""
    real = build._resolve_one_camera

    def flaky(project, c, scrolling):
        if c.get("yaw") == 0:
            raise FileNotFoundError("borrow .bgx not extracted")
        return real(project, c, scrolling)
    monkeypatch.setattr(build, "_resolve_one_camera", flaky)
    logic = build.lint_all(_two(tmp_path, 0, 90)).logic
    assert [n for n in logic if "bob (" in n and "on camera 1:" in n], logic
    assert not [n for n in logic if "could not finish" in n], logic


def test_a_failing_motion_hook_does_not_hide_the_bob_note(tmp_path, monkeypatch):
    """[review claims-4: the hook isolation was untested] The floor advisory raising is reported as its own note,
    and the bob advisory after it still runs."""
    def boom(project):
        raise RuntimeError("floor index exploded")
    monkeypatch.setattr(build, "_motion_floor_notes", boom)
    logic = build.lint_all(_two(tmp_path, 0, 90)).logic
    assert [n for n in logic if "could not finish: RuntimeError: floor index exploded" in n], logic
    assert [n for n in logic if "bob (" in n and "on camera 1:" in n], logic


_ORBIT = [("balloon", (0, -900), "collision = false\nshadow = false",
           "{ radius = 300, period = 128, height = 150, bob = { amp = 60, period = 256 } }")]


def test_a_bob_failing_on_two_cameras_gets_one_note_whose_fix_clears_both(tmp_path):
    """[review 3 claims-5: one-note-per-prop was pinned only in motion.bob_note, so the build hook could regress to a
    note per camera with every test green] An orbit folds its slow bob on BOTH cameras: lint_all prints ONE note
    naming both, and applying the amp it names to the toml clears the note on both."""
    head = _TWO_CAMERAS.format(yaw0=0, yaw1=90)
    notes = [n for n in build.lint_all(_load(tmp_path, _toml(_ORBIT, head=head), "both")).logic if "bob (" in n]
    assert len(notes) == 1 and "on camera 0 and camera 1:" in notes[0], notes
    amp, h = re.search(r"an amp of (\d+) with height (\d+)", notes[0]).groups()
    fixed = [(_ORBIT[0][0], _ORBIT[0][1], _ORBIT[0][2],
              f"{{ radius = 300, period = 128, height = {h}, bob = {{ amp = {amp}, period = 256 }} }}")]
    after = build.lint_all(_load(tmp_path, _toml(fixed, head=head), "fixed")).logic
    assert not [n for n in after if "bob (" in n or "SNAP" in n], after


def test_the_fast_projector_is_to_canvas_bit_for_bit(tmp_path):
    """The bob lint projects through cam.canvas_projector; it must be cam.to_canvas exactly (same float operations
    in the same order), or a threshold verdict could differ from the map every other tool uses."""
    import random
    from ff9mapkit.scene import cam as C
    proj = _two(tmp_path, 30, 135)
    cams = [build._resolve_one_camera(proj, c, build.is_scrolling(proj)) for c in build.camera_cfgs(proj)]
    cams.append(build.resolve_camera(_load(tmp_path, _toml([]), "one")))
    shifted = build.resolve_camera(_load(tmp_path, _toml([]), "shifted"))     # [review 3 claims-8] a real imported
    shifted.centerOffset, shifted.t = [26, 400], [137, -58, 4321]              # camera carries both
    cams.append(shifted)
    rnd = random.Random(1)
    for c in cams:
        f = C.canvas_projector(c)
        for _ in range(3000):
            x, y, z = rnd.randint(-9000, 9000), rnd.randint(-16383, 16383), rnd.randint(-9000, 9000)
            try:
                want = C.to_canvas((x, y, z), c)
            except ZeroDivisionError:
                continue
            assert f(x, y, z) == want, (x, y, z)
            got = C.canvas_projector(c, depth=True)(x, y, z)
            assert got[:2] == want and got[2] == C.project((x, y, z), c)[2]       # [review 4 claims-4] SIGNED depth


# ================================================================ a height alone is a HOLD -- the zero-clock daemon
_HOLD = ("balloon", (0, -900), "collision = false\nshadow = false", "{ height = 300 }")
_BOBBER = ("letter", (600, -900), "collision = false\nshadow = false",
           "{ height = 150, bob = { amp = 150, period = 60 } }")


@pytest.mark.parametrize("props, loc", [([_HOLD], 0), ([_HOLD, _BOBBER], 2)], ids=["hold_only", "hold_and_bob"])
def test_a_hold_builds_and_its_daemon_re_places_it_every_tick(tmp_path, props, loc, templates):
    """[review: `height` alone was refused, so a held prop had to be an amp-1 bob that lint flags] A hold is a
    mover with no clock. Alone on a field its daemon has NO locals (loc 0: no prelude, no advance -- just the 0xAD,
    Wait(1) and the JMP, a shape no clocked field builds); beside a clocked mover it shares that mover's daemon.
    Either way the shipped bytes run the predictor: the hold's pose is the same (x, -300, z) every tick."""
    text = _toml(props)
    res, ebs = _build(tmp_path, text)
    raw = _load(tmp_path, text, "raw").raw
    us = ebs["us"]
    movers = _movers(raw, us)
    dslot, want, got_loc = _daemon(us, movers)
    assert got_loc == loc
    assert motion.arming_problems(us, dslot, [u for _s, u in movers]) == []
    ticks = MotionEngine(loc).ticks(want[6:], 121)
    hold_uid = movers[0][1]
    for n, got in enumerate(ticks):
        assert [(op, u, v) for op, u, v in got] == [(motion.MOVE_EX, u, motion.pose(s, n)[:3]) for s, u in movers], n
        assert got[0] == (motion.MOVE_EX, hold_uid, (0, -300, -900)), n
    _r, plain = _build(tmp_path, _toml(props, motion_on=False), "plain")
    for lang in LANGS:
        assert _errors(ebs[lang]) - _errors(plain[lang]) == Counter(), lang
    head = motion.report_lines(movers, dslot, loc)[0]
    assert head in res.warnings and (("all holds" in head) == (loc == 0)), head


def test_lint_has_nothing_to_say_about_a_hold(tmp_path):
    """The hold replaces the amp-1 bob bench 30948 used to pin a height: that bob draws the 'too small to see'
    note, the hold draws no motion note at all."""
    amp1 = [("balloon", (0, -900), "collision = false\nshadow = false",
             "{ height = 300, bob = { amp = 1, period = 60 } }")]
    notes = [n for n in build.lint_all(_load(tmp_path, _toml(amp1), "amp1")).logic if "motion" in n]
    assert len(notes) == 1 and "too small to see" in notes[0], notes
    rep = build.lint_all(_load(tmp_path, _toml([_HOLD]), "hold"))
    assert not [n for n in rep.logic + rep.errors if "motion" in n], (rep.logic, rep.errors)


def test_lint_names_a_clock_the_field_already_runs_when_it_is_full(tmp_path):
    """[review 3 advice-1: the named period could be a 9th clock, and the field then failed validate] The field is
    at CLOCKS_MAX (8): seven spinning props hold 16, 200, 300, 400, 500, 600 and 256, and the cask orbits on 128
    with a +-60 bob on 256. A new period for the bob would be a 9th clock, so lint names the field's own 16 -- and
    the toml with it applied still validates and lints clean of bob notes."""
    spins = [(n, (-1000 + 280 * i, -300), "", f'{{ turn = "spin", period = {per} }}')
             for i, (n, per) in enumerate(zip(("scroll", "letter", "chest", "sword", "fish", "book", "feather"),
                                              (16, 200, 300, 400, 500, 600, 256)))]
    cask = [("cask", (0, -1100), "collision = false\nshadow = false",
             "{ radius = 300, period = 128, height = 150, bob = { amp = 60, period = BP } }")]

    def field(bp, name):
        mo = [(n, p, x, m.replace("BP", str(bp))) for n, p, x, m in cask]
        return _load(tmp_path, _toml(spins + mo), name)
    assert len(motion.clocks([motion.parse(p, i) for i, p in enumerate(field(256, "full").raw["prop"])])) == 8
    notes = [n for n in build.lint_all(field(256, "full")).logic if "bob (" in n]
    assert len(notes) == 1 and "a bob period of 16 (same amp; a clock the field already runs)" in notes[0], notes
    fixed = build.lint_all(field(16, "fixed"))
    assert not [n for n in fixed.logic + fixed.errors if "bob (" in n or "distinct periods" in n], fixed


_CAMS3 = """
[field]
id = 30990
name = "MOTB"
area = 11

[[camera]]
pitch = 48
yaw = 0
[[camera]]
pitch = 70
yaw = 0
center_offset = [0, {cy}]

[[camera_zone]]
to_camera = 1
zone = [[0, -150], [1400, -150], [1400, -2000], [0, -2000]]
[[camera_zone]]
to_camera = 0
zone = [[-1400, -150], [0, -150], [0, -2000], [-1400, -2000]]

[walkmesh]
quad = [[-1400, -100], [1400, -100], [1400, -2000], [-1400, -2000]]

[player]
spawn = [0, -1600]
"""


def _apply_notes(props, notes):
    """The toml's movers with every fix the notes name applied (a period, else an amp with its height)."""
    out = []
    for (n, pos, extra, mo), note in zip(props, notes):
        m = re.search(r"a (?:bob|motion) period of (\d+)", note or "")
        if m:
            mo = re.sub(r"bob = \{ amp = (\d+), period = \d+ \}", rf"bob = {{ amp = \1, period = {m.group(1)} }}", mo)
        out.append((n, pos, extra, mo))
    return out


@pytest.mark.parametrize("cy", [178, 181, 184])
def test_a_named_amp_holds_on_a_camera_the_raised_path_enters(tmp_path, cy):
    """[review 4 law-amp-fix-unjudged-camera: the amp fix was checked only on cameras that showed the path at the
    AUTHOR's height, so raising it onto camera 1's canvas produced a fresh note there] Every fix the note names,
    written into the toml, lints clean on both cameras."""
    head = _CAMS3.format(cy=cy)
    notes = [n for n in build.lint_all(_load(tmp_path, _toml(_ORBIT, head=head), f"c{cy}")).logic if "bob (" in n]
    assert len(notes) == 1, notes
    for bp, amp, h in re.findall(r"a bob period of (\d+)|an amp of (\d+)(?: with height (\d+))?", notes[0]):
        mo = (f"{{ radius = 300, period = 128, height = 150, bob = {{ amp = 60, period = {bp} }} }}" if bp else
              f"{{ radius = 300, period = 128, height = {h or 150}, bob = {{ amp = {amp}, period = 256 }} }}")
        fixed = [(_ORBIT[0][0], _ORBIT[0][1], _ORBIT[0][2], mo)]
        after = build.lint_all(_load(tmp_path, _toml(fixed, head=head), f"f{cy}{bp}{amp}")).logic
        assert not [n for n in after if "bob (" in n], (notes[0], after)


def test_two_notes_applied_together_stay_within_the_clocks(tmp_path):
    """[review 4 law-two-notes-ninth-clock: each note was checked against CLOCKS_MAX alone, so applying two made a 9th
    clock] Five spinning props and two folding casks fill 7 clocks; the two notes name ONE new period between them,
    and the toml with both applied validates and lints clean of bob notes."""
    spins = [(n, (-1000 + 280 * i, -300), "", f'{{ turn = "spin", period = {per} }}')
             for i, (n, per) in enumerate(zip(("scroll", "letter", "chest", "sword", "fish"), (200, 300, 400, 500, 600)))]
    casks = [(n, pos, "collision = false\nshadow = false",
              "{ radius = 300, period = 128, height = 150, bob = { amp = 60, period = 256 } }")
             for n, pos in (("cask", (-600, -1100)), ("balloon", (600, -1100)))]
    props = spins + casks
    proj = _load(tmp_path, _toml(props), "two")
    assert len(motion.clocks([motion.parse(p, i) for i, p in enumerate(proj.raw["prop"])])) == 7
    notes = [n for n in build.lint_all(proj).logic if "bob (" in n]
    assert len(notes) == 2 and "share a clock" in notes[1], notes
    fixed = _apply_notes(casks, notes)
    after = build.lint_all(_load(tmp_path, _toml(spins + fixed), "applied"))
    assert not [n for n in after.logic + after.errors if "bob (" in n or "distinct periods" in n], after


def test_a_camera_whose_canvas_the_mover_never_enters_is_not_judged(tmp_path):
    """[review 4 claims-5: the build's canvas-size wiring was untested -- without it an off-screen mover was judged]
    Camera 1's canvas is pushed far off the orbit by its center_offset; the folding bob is noted on camera 0 only."""
    head = _CAMS3.format(cy=4000)
    notes = [n for n in build.lint_all(_load(tmp_path, _toml(_ORBIT, head=head), "off")).logic if "bob (" in n]
    assert len(notes) == 1 and "on camera 0:" in notes[0], notes


_BENCH_CAM = """
[field]
id = 30990
name = "MOTB"
area = 11

[camera]
pitch = 48.0
distance = 4500
fov = 42.2
[camera.frame]
back = 205
front = 432

[walkmesh]
quad = [[-1220, 257], [1220, 257], [1220, -1931], [-1220, -1931]]

[player]
spawn = [-750, -1750]
"""


def test_lint_judges_a_path_through_the_camera_plane_on_what_it_shows(tmp_path):
    """[review 4 claims-4: the build could drop depth=True and every test stayed green] A shuttle running out through
    the bench camera's plane: lint_all's note is the one the depth-aware reading gives -- judged on the arc in front
    -- and the same whether the off-screen far end is at -6720 or -6740. Run far behind the camera (-12000), an amp
    fix would carry more of the path behind the plane: without the depth the build passes, lint named one."""
    from ff9mapkit.scene import cam as C
    notes = []
    for far in (-6720, -6740, -12000):
        mover = [("cask", (0, -1000), "collision = false\nshadow = false",
                  f"{{ to = [0, {far}], period = 256, height = 150, bob = {{ amp = 60, period = 256 }} }}")]
        proj = _load(tmp_path, _toml(mover, head=_BENCH_CAM), f"p{-far}")
        got = [n for n in build.lint_all(proj).logic if "bob (" in n]
        c = build.resolve_camera(proj)
        view = motion.View("", C.canvas_projector(c, depth=True), (float(c.range[0]), float(c.range[1])))
        assert got == [motion.bob_note(motion.parse(proj.raw["prop"][0], 0), view, clocks=[256])], got
        notes.append(re.sub(r"\d+(?:\.\d+)?", "N", got[0]))
    assert notes[0] == notes[1] and "an amp of" not in notes[2], notes
