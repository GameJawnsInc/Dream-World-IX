"""``[photo]`` THROUGH THE BUILD (photo mode rung 1): content/photo.py + its build.py hooks + the campaign guard, on
real built bytes.

  * THE DAEMON IS THE SPEC'S -- a built field carries exactly one entry equal to ``photo.entry_bytes`` over the hide
    targets' REAL slots and tags (read back off the built script: SetModel for the slots, the seated function bodies
    for the tags), in the same slot in every language -- the jp daemon tests the swapped Cancel bit, every other
    language's is the us one -- byte-identical on a rebuild, reporting once; THE ORDER LAW and the
    whole-script laws (CAMERA-OWNER, E-POLL) hold on the final bytes; and the SHIPPED daemon, run in
    ``_ebengine.FieldTickEngine`` with the SHIPPED hide/show functions, hides and exactly restores every target.
  * ONE REFUSAL TEXT -- a ``photo.problems`` refusal is in ``validate()``, in ``lint_all().errors`` and in
    ``build_field``'s BuildError.
  * BYTE IDENTITY -- a field without [photo] never reaches ``photo.arm`` (it is monkeypatched to raise) and the vivi-hut
    oracle still hashes to its manifest golden.
  * THE LAWS BITE on real bytes: a taken tag slides the pair, a planted EnableCameraServices(0) or a foreign poll of the
    open button is refused, a target the daemon would misaddress (another model, an InitObject uid) is refused, and a
    valid [photo] adds nothing to lint (it exits 1 on any note) while a raising lint hook is reported, not raised.
  * THE CAMPAIGN GUARD -- a FORKED member with [photo] is refused by ``lint_campaign`` (only the manifest can see it).

Template-gated (THE WORKTREE SKIP TRAP): without the extracted blank-field template these WARN and skip.
"""
from __future__ import annotations

import re
import warnings
from collections import Counter
from pathlib import Path

import pytest

from ff9mapkit import build, eblint, prop_archetypes
from ff9mapkit.config import LANGS, ModLayout
from ff9mapkit.content import motion, photo
from ff9mapkit.eb import EbScript, edit as eb_edit, exprasm, opcodes

from ._ebengine import CameraModel, FieldTickEngine

_HUT = Path(__file__).resolve().parents[1] / "examples" / "vivi-hut" / "hut_int.field.toml"


@pytest.fixture()
def templates():
    from ff9mapkit import provision
    if not provision.templates_present():
        warnings.warn(
            "[photo]'s BUILD path went UNVERIFIED in this run: the base templates are not extracted. This is the "
            "WORKTREE SKIP TRAP -- a green run here says nothing about the daemon the build ships. Re-run in the MAIN "
            "repo (C:/gd/Dream-World-IX/ff9mapkit), or `ff9mapkit extract-templates` first.", UserWarning)
        pytest.skip("base templates not extracted (run `ff9mapkit extract-templates`; see the warnings summary)")


_HEAD = """
[field]
id = 30991
name = "PHOTB"
area = 11

[camera]
pitch = 40
distance = 4500
fov = 42.2
range = [768, 448]
window_width = 384

[camera.scroll]
enabled = true

[walkmesh]
quad = [[-2122, -161], [2122, -161], [2122, -2043], [-2122, -2043]]
frame = "world"

[player]
spawn = [0, -1102]

[[prop]]
prop = "balloon"
name = "bl"
pos = [-1000, -1102]
collision = false
shadow = false

[[prop]]
prop = "save_point"
name = "sp"
pos = [0, -450]

[[prop]]
prop = "scroll"
pos = [800, -1500]

[[npc]]
name = "guard"
model = "GEO_NPC_F0_TCK"
pos = [600, -800]
"""
_PHOTO = '\n[photo]\nhide = ["bl", "sp", "guard", "player", "all"]\n'


def _load(tmp_path, text: str, name="f") -> build.FieldProject:
    d = tmp_path / name
    d.mkdir(parents=True, exist_ok=True)
    p = d / "f.field.toml"
    p.write_text(text, encoding="utf-8")
    return build.FieldProject.load(p)


def _build(tmp_path, text: str, name="f"):
    proj = _load(tmp_path, text, name)
    layout = ModLayout(tmp_path / name / "mod")
    res = build.build_field(proj, layout)
    return res, {lang: layout.eb_path(lang, f"EVT_{proj.name}.eb.bytes").read_bytes() for lang in LANGS}


def _slots_by_model(ebb: bytes) -> dict:
    s = EbScript.from_bytes(ebb)
    out: dict = {}
    for e in s.entries:
        f0 = None if e.empty else e.func_by_tag(0)
        for i in (s.instrs(f0) if f0 is not None else ()):
            if i.op == 0x2F:
                out.setdefault(i.args[0], []).append(e.index)
    return out


def _parts(raw: dict, ebb: bytes) -> list:
    """The hide parts, from the BUILT bytes: each target's slot by its SetModel (or DefinePlayerCharacter for the
    player), its tags by the seated bodies equal to flag_function(uid, show)."""
    spec = photo.parse(raw)
    by_model = _slots_by_model(ebb)
    s = EbScript.from_bytes(ebb)
    pl = photo.player_entry(ebb)
    out = []
    for t, step in enumerate(spec.steps):
        if step == "all":
            continue
        if step == "player":
            slots = [(pl, 250)]
        elif step == "guard":
            (slot,) = by_model[build.resolve_npc_model("GEO_NPC_F0_TCK")]
            slots = [(slot, slot)]
        else:
            p = next(q for q in raw["prop"] if q.get("name") == step)
            if prop_archetypes.is_composite(p["prop"]):
                models = [m for m, _pose, _dx, _dz in prop_archetypes.resolve_composite(p["prop"])]
            else:
                models = [prop_archetypes.resolve(p["prop"])[0]]
            slots = [(sl, sl) for m in models for sl in by_model[m]]
        for entry, uid in slots:
            e = s.entry(entry)
            tags = {}
            for f in e.funcs:
                body = ebb[f.abs_start:f.abs_end]
                for show in (False, True):
                    if body.startswith(photo.flag_function(uid, show)):
                        tags[show] = f.tag
            assert set(tags) == {False, True}, (step, entry, tags)
            out.append(photo.Part(step=t, uid=uid, entry=entry, hide_tag=tags[False], show_tag=tags[True]))
    return out


def _photo_entry(ebb: bytes, want: bytes) -> int:
    s = EbScript.from_bytes(ebb)
    hits = [e.index for e in s.entries if not e.empty and ebb[e.abs_start:e.abs_end] == want]
    assert len(hits) == 1, f"{len(hits)} entries equal photo.entry_bytes"
    return hits[0]


def _errors(ebb: bytes) -> Counter:
    return Counter((re.sub(r"\s*@\d+", "", i.where), i.message) for i in eblint.errors(eblint.lint_eb(ebb)))


# ================================================================ the build arms the spec's daemon
def test_build_arms_the_specs_daemon(tmp_path, templates):
    res, ebs = _build(tmp_path, _HEAD + _PHOTO)
    raw = _load(tmp_path, _HEAD + _PHOTO, "raw").raw
    us = ebs["us"]
    parts = _parts(raw, us)
    assert [p.step for p in parts] == [0, 1, 1, 2, 3]                  # the save point is two parts
    boxes = [b.viewport for b in photo.pan_boxes(raw)]
    spec = photo.parse(raw)
    want = photo.entry_bytes(spec, parts, boxes)
    dslot = _photo_entry(us, want)
    assert EbScript.from_bytes(us).entry(dslot).loc == photo.LOC
    slots = [photo.player_entry(us)] + [p.entry for p in parts if p.uid != 250]
    assert motion.arming_problems(us, dslot, slots, noun="hide target", why="x") == []
    assert photo._whole_script_laws(us, dslot, spec) == []

    # every language: its own daemon in the same slot, the same seated tags; only jp's differs (the Cancel swap)
    for lang, ebb in ebs.items():
        assert _parts(raw, ebb) == parts, lang
        assert _photo_entry(ebb, photo.entry_bytes(spec, parts, boxes, lang)) == dslot, lang
    assert "jp" in ebs and photo.entry_bytes(spec, parts, boxes, "jp") != want
    assert all(photo.entry_bytes(spec, parts, boxes, lang) == want for lang in ebs if lang != "jp")
    # a rebuild is byte-identical
    _r2, again = _build(tmp_path, _HEAD + _PHOTO, "again")
    assert again == ebs
    # eblint: no NEW error against the same field without [photo]
    _r3, plain = _build(tmp_path, _HEAD, "plain")
    for lang in LANGS:
        assert _errors(ebs[lang]) - _errors(plain[lang]) == Counter(), lang
    # the report, once each
    want_lines = photo.report_lines(spec, parts, boxes, dslot, len(want), raw)
    assert [w for w in res.warnings if w.startswith("[photo]")] == want_lines
    assert photo.box_lines(raw)[0] in want_lines

    # the SHIPPED daemon + the SHIPPED hide/show functions: open, hide every step, close -> an exact restore
    s = EbScript.from_bytes(us)
    fns = {}
    for p in parts:
        for tag in (p.hide_tag, p.show_tag):
            f = s.entry(p.entry).func_by_tag(tag)
            fns[(p.uid, tag)] = us[f.abs_start:f.abs_end]
    objects = {p.uid: 7 for p in parts} | {250: 15, 99: 7}
    cam = CameraModel(boxes[0], lambda: (384, 286))
    e = FieldTickEngine(photo.LOC, cam, objects=dict(objects), functions=fns)
    body = want[6:]

    def press(name):
        e.keys = photo.BUTTONS[name]
        e.run(body, 2)
        e.keys = 0
        e.run(body, 3)

    e.run(body, photo.SETTLE + 2)
    press("select")
    for _ in range(5):
        press("r1")
    assert all(v & 1 == 0 for v in e.objects.values()), e.objects
    press("cancel")
    e.run(body, 30)
    assert e.objects == objects and e.usercontrol == 1

    # the SHIPPED jp daemon closes on 0x20000 -- the bit the player's Cancel arrives as on that build
    jp = FieldTickEngine(photo.LOC, CameraModel(boxes[0], lambda: (384, 286)), objects=dict(objects), functions=fns)
    jbody = photo.entry_bytes(spec, parts, boxes, "jp")[6:]
    jp.run(jbody, photo.SETTLE + 2)
    for keys, n in ((photo.BUTTONS["select"], 2), (0, 3), (0x10000, 2), (0, 3)):
        jp.keys = keys
        jp.run(jbody, n)
    assert jp.usercontrol == 0, "the jp daemon closed on 0x10000 -- on that build it is the Confirm that talks"
    for keys, n in ((0x20000, 2), (0, 30)):
        jp.keys = keys
        jp.run(jbody, n)
    assert jp.usercontrol == 1 and jp.objects == objects


# ================================================================ one refusal text
def test_validate_lint_and_build_share_one_text(tmp_path, templates):
    text = _HEAD.replace('model = "GEO_NPC_F0_TCK"', 'model = "GEO_NPC_F0_TCK"\nrequires_flag = 8712') + \
        '\n[photo]\nhide = ["guard"]\n'
    proj = _load(tmp_path, text)
    probs = [p for p in build.validate(proj) if p.startswith("[photo]")]
    assert probs and "requires_flag" in probs[0]
    assert probs[0] in build.lint_all(proj).errors
    with pytest.raises(build.BuildError) as ei:
        build.build_field(proj, ModLayout(tmp_path / "out"))
    assert probs[0] in str(ei.value)


# ================================================================ byte identity
def test_no_photo_never_reaches_arm_and_the_oracle_is_byte_exact(tmp_path, monkeypatch, templates):
    """[photo code reached without [photo]]"""
    from ff9mapkit import provision

    def _boom(*_a, **_k):
        raise AssertionError("photo.arm ran on a field with no [photo] -- THE BYTE-IDENTITY guard is gone")

    monkeypatch.setattr(photo, "arm", _boom)
    build.build_mod([build.FieldProject.load(_HUT)], tmp_path / "hut", mod_name="FF9CustomMap")
    hut = ModLayout(tmp_path / "hut").eb_path("us", "EVT_HUT_INT.eb.bytes").read_bytes()
    assert provision.sha256(hut) == provision.load_manifest()["goldens"]["EVT_HUT_INT.eb.bytes/us"]
    res, _ebs = _build(tmp_path, _HEAD)
    assert not any(w.startswith("[photo]") for w in res.warnings)


# ================================================================ the laws bite on real bytes
def test_photo_and_motion_both_arm_in_order(tmp_path, templates):
    text = _HEAD.replace('name = "bl"\npos = [-1000, -1102]\ncollision = false\nshadow = false',
                         'name = "bl"\npos = [-1000, -1102]\ncollision = false\nshadow = false\n'
                         'motion = { radius = 200, period = 128, turn = "travel" }') + _PHOTO
    res, ebs = _build(tmp_path, text)
    assert any(w.startswith("[photo] daemon") for w in res.warnings)
    assert any("motion" in w for w in res.warnings)


def test_a_taken_tag_slides_the_pair(tmp_path, templates):
    _r, ebs = _build(tmp_path, _HEAD)
    ebb = ebs["us"]
    pl = photo.player_entry(ebb)
    assert photo._free_pair(ebb, pl) == (96, 97)
    ebb = eb_edit.add_function(ebb, pl, 96, opcodes.RETURN)
    assert photo._free_pair(ebb, pl) == (98, 99)


def _poll(mask_tok: str) -> bytes:
    return opcodes.encode(0x05, exprasm.assemble(f"{mask_tok} B_KEYON B_EXPR_END"), arg_flags=1) + opcodes.RETURN


def test_the_whole_script_laws_refuse_a_foreign_poll_or_camera_op(tmp_path, templates):
    """[close mask in E-POLL] [CAMERA-OWNER removed] A Cancel poll elsewhere (an [[event]] page's dismiss) is lawful;
    a poll of the OPEN button, a computed mask, or a planted EnableCameraServices(0) is refused."""
    _r, ebs = _build(tmp_path, _HEAD + _PHOTO)
    raw = _load(tmp_path, _HEAD + _PHOTO, "raw").raw
    spec = photo.parse(raw)
    ebb = ebs["us"]
    dslot = _photo_entry(ebb, photo.entry_bytes(spec, _parts(raw, ebb), [b.viewport for b in photo.pan_boxes(raw)]))
    host = photo.player_entry(ebb)
    ok = eb_edit.add_function(ebb, host, 120, _poll("const4(65536)"))
    assert photo._whole_script_laws(ok, dslot, spec) == []
    for bad, frag in ((_poll("const(1)"), "polls the open button"),
                      (_poll("Instance.Int16[0]"), "computed mask"),
                      (opcodes.encode(0x71, 0, 0, 0) + opcodes.RETURN, "EnableCameraServices"),
                      (opcodes.encode(0xEA) + opcodes.RETURN, "CAMERA-OWNER")):
        planted = eb_edit.add_function(ebb, host, 121, bad)
        assert any(frag in p for p in photo._whole_script_laws(planted, dslot, spec)), frag


def test_a_valid_photo_adds_nothing_to_lint(tmp_path):
    """[box lines as lint warnings] `ff9mapkit lint` exits 1 on any note: a valid [photo] must add none (its pan boxes
    are in the build report)."""
    plain = build.lint_all(_load(tmp_path, _HEAD, "plain"))
    with_photo = build.lint_all(_load(tmp_path, _HEAD + _PHOTO, "photo"))
    assert with_photo.tagged == plain.tagged and with_photo.ok == plain.ok
    assert not any("[photo]" in n for n in with_photo.tagged), with_photo.tagged


def test_a_raising_photo_lint_hook_is_reported_not_raised(tmp_path, monkeypatch):
    proj = _load(tmp_path, _HEAD + _PHOTO)

    def _boom(_raw):
        raise RuntimeError("boom")

    monkeypatch.setattr(photo, "lint_notes", _boom)
    rep = build.lint_all(proj)
    assert any("[photo] lint could not finish: RuntimeError: boom" in n for n in rep.logic)


def test_arm_refuses_a_target_it_would_misaddress(tmp_path, templates):
    """[SetModel compare dropped] [InitObject uid unchecked] On real bytes: a prop slot whose Init sets another model
    than the build seated there, or an InitObject that names another uid, would hide the wrong object or freeze."""
    _r, ebs = _build(tmp_path, _HEAD, "plain")
    ebb = ebs["us"]
    raw = _load(tmp_path, _HEAD + '\n[photo]\nhide = ["bl", "player"]\n', "raw").raw
    bl = next(q for q in raw["prop"] if q.get("name") == "bl")
    m = prop_archetypes.resolve("balloon")[0]
    (slot,) = _slots_by_model(ebb)[m]
    seats = [(bl, m, slot)]
    _out, dslot, lines = photo.arm(ebb, raw, prop_seats=seats, npc_slots={})
    assert dslot > slot and lines[0].startswith("[photo] daemon")
    with pytest.raises(photo.PhotoError, match="SLOT-MAP"):
        photo.arm(ebb, raw, prop_seats=[(bl, m + 1, slot)], npc_slots={})
    (off,) = [o for e, t, o in motion._calls(ebb, 0x09, slot) if (e, t) == (0, 0)]
    planted = bytearray(ebb)
    planted[off + 2] = 77
    with pytest.raises(photo.PhotoError, match="created with uid 77"):
        photo.arm(bytes(planted), raw, prop_seats=seats, npc_slots={})


# ================================================================ the campaign guard
def test_campaign_refuses_photo_on_a_forked_member(tmp_path):
    from ff9mapkit import campaign
    plan = campaign.new_campaign("PHC", "FF9CustomMap-phc", tmp_path, id_base=30100)
    campaign.add_field(plan, tmp_path, name="NOVEL")
    campaign.add_field(plan, tmp_path, name="FORKED")
    for m in plan.members:
        t = tmp_path / m.toml_rel
        t.write_text(t.read_text(encoding="utf-8") + "\n[photo]\n", encoding="utf-8", newline="\n")
    errs, _w = campaign.lint_campaign(plan, tmp_path)
    assert not [e for e in errs if "[photo]" in e], errs
    plan.members[1].real_id = 300
    campaign._save_plan(plan, tmp_path)
    plan = campaign.load_campaign(tmp_path / "campaign.toml")
    errs, _w = campaign.lint_campaign(plan, tmp_path)
    hits = [e for e in errs if "[photo]" in e]
    assert len(hits) == 1 and hits[0].startswith("member FORKED:") and "donor field 300" in hits[0], errs
