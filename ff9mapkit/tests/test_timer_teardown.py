"""THE COUNTDOWN EXIT LAW (fort-condor bench leak, 2026-07-28): a field whose [behavior] arms
`timer =` must DISARM the countdown HUD (RunTimer(0) + ShowTimer(0)) on every compiled exit.

ShowTimer/RunTimer write the SAVE-PERSISTED `_ff9.timerDisplay/timerControl` mirrors and the
engine re-stamps TimerUI from them on EVERY map load (EventEngine.StartEvents) — the countdown
is deliberately cross-field in stock (the Festival of the Hunt spans Lindblum). An exit without
the disarm carries a minigame clock onto the overworld and every later field, and through
save/load. Battle is exempt BY DESIGN (the clock-coupled battle law: battle AI reads
B_SYSVAR[17], and Main_Reinit returns to the same field).

These tests pin the wiring: the disarm pair lands before the transition in every declarative
exit the build emits, and a no-timer field builds with no disarm bytes at all.
"""

from __future__ import annotations

from ff9mapkit.build import FieldProject, build_mod, validate
from ff9mapkit.config import ModLayout
from ff9mapkit.content.behavior import TIMER_DISARM
from ff9mapkit.eb import EbScript, opcodes
from ff9mapkit.eb.disasm import iter_code

FIELD_OP, WORLDMAP_OP = 0x2B, 0xB6

HEAD = """
[field]
id = 4004
name = "CLOCKROOM"
area = 11
text_block = 1073

[camera]
pitch = 45

[walkmesh]
quad = [[-1200, -100], [1200, -100], [1200, -1400], [-1200, -1400]]

[player]
spawn = [0, -300]

[[npc]]
name = "guard"
preset = "vivi"
pos = [-500, -600]
dialogue = "Halt."
"""

TIMER = """
[behavior]
timer = 90

[[behavior.unit]]
npc = "guard"
hp = 5

  [[behavior.unit.branch]]
  when = [{ hp_le = 0 }]
  do = { die = true }

  [[behavior.unit.branch]]      # the compiler requires an unconditional fallback
  do = { hold = [-500, -600] }
"""

EXITS = """
[[gateway]]                     # the walk-out door
to = 4000
zone = [[-200, -1200], [200, -1200], [200, -1350], [-200, -1350]]

[[gateway]]                     # the walk-out to the overworld
to = "worldmap"
zone = [[900, -1200], [1100, -1200], [1100, -1350], [900, -1350]]

[[npc]]
name = "porter"
preset = "vivi"
pos = [500, -600]

[[choice]]                      # a menu exit on an NPC
npc = "porter"
prompt = "Leave?"

  [[choice.options]]
  text = "Go"
  warp = 4001

  [[choice.options]]
  text = "Stay"

[[choice]]                      # a menu exit on a zone lever
zone = [[-1100, -1200], [-900, -1200], [-900, -1350], [-1100, -1350]]
prompt = "Take the lift?"

  [[choice.options]]
  text = "Ride"
  warp = 4002

  [[choice.options]]
  text = "Not now"
"""


def _built_eb(tmp_path, toml_text: str) -> EbScript:
    p = tmp_path / "clock.field.toml"
    p.write_text(toml_text, encoding="utf-8")
    proj = FieldProject.load(p)
    assert validate(proj) == []
    out = tmp_path / "mod"
    build_mod([proj], out, mod_name="FF9CustomMap")
    return EbScript.from_bytes(ModLayout(out).eb_path("us", "EVT_CLOCKROOM.eb.bytes").read_bytes())


def _func_with_warp(eb: EbScript, op: int, dest: int | None):
    """The (func, warp_instr) whose body holds the ``op`` transition (to ``dest`` when given)."""
    for e in eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            for i in iter_code(eb.data, f.abs_start, f.abs_end):
                if i.op == op and (dest is None or i.imm(0) == dest):
                    return f, i
    raise AssertionError(f"no function carries op {op:#x} -> {dest}")


def _assert_disarm_precedes(eb: EbScript, f, warp_instr):
    body = eb.data[f.abs_start:f.abs_end]
    at = body.find(TIMER_DISARM)
    assert at != -1, "the exit body carries no RunTimer(0)+ShowTimer(0) disarm"
    assert f.abs_start + at < warp_instr.off, "the disarm must run BEFORE the transition"


def test_timer_field_disarms_every_compiled_exit(tmp_path):
    eb = _built_eb(tmp_path, HEAD + TIMER + EXITS)
    # sanity: Main_Init armed the countdown (the Hunt's exact start triplet)
    triplet = opcodes.encode(0x69, 90) + opcodes.encode(0x8D, 1) + opcodes.encode(0x7D, 1)
    assert triplet in eb.data
    # the field gateway, both menu exits: disarm before the Field() warp
    for dest in (4000, 4001, 4002):
        f, w = _func_with_warp(eb, FIELD_OP, dest)
        _assert_disarm_precedes(eb, f, w)
    # the worldmap walk-out: disarm before the (computed or literal) WorldMap transition —
    # the cascade ends the function, so "the disarm is present in that Range" is the contract
    for e in eb.entries:
        if e.empty or e.type != 1:
            continue
        rng = e.func_by_tag(2)
        if rng is None:
            continue
        body = eb.data[rng.abs_start:rng.abs_end]
        if any(i.op == WORLDMAP_OP for i in iter_code(eb.data, rng.abs_start, rng.abs_end)):
            assert TIMER_DISARM in body
            break
    else:
        raise AssertionError("no worldmap exit region found")


def test_no_timer_field_builds_without_disarm_bytes(tmp_path):
    # the same field minus `timer =`: no disarm pair anywhere (byte-parity guard — a
    # no-timer field's exits must not grow teardown ops it has nothing to tear down)
    eb = _built_eb(tmp_path, HEAD + EXITS)
    assert TIMER_DISARM not in eb.data
