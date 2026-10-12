"""``tools/harness`` and the co-op F3.2 dialogue contract (memoria-patch s96): the driver's ``netsync`` accessors and
verb, and the stand-in's model of the guest's dialogue LOCK.

Same contract as ``test_harness.py``: these pin the DRIVER and the stand-in, and say nothing about the engine -- the
solo benches (``studies/test-harness/scenarios``) against a live game are that proof. F3.2 keeps the harness at
protocol 5: the ``netsync`` block is ADDITIVE, ``dialogue`` = ``"authority"`` names the new contract, and the F3 keys
stay, pinned to "nothing". So two things matter here: an absent key reads as "this engine cannot" (None), never as
"nothing there"; and the stand-in's verbs, refusals and keys are the agent's -- read off the live patch stack
(``memoria-patches/``), not retyped, so a drift on either side turns a test red.
"""
import json
import pathlib
import re
import sys

import pytest

from ._patchstack import net_lines

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from harness import HarnessError, Session, State                   # noqa: E402
from harness import fakegame as FG                                 # noqa: E402
from harness.fakegame import FakeGame                              # noqa: E402

FIELD = 30810
#: The guest clock is whole milliseconds of the virtual one (`FakeGame._guest_now` truncates): one ms of slack.
MS = 0.001


@pytest.fixture
def game(tmp_path):
    (tmp_path / "x64").mkdir()
    (tmp_path / "x64" / "FF9.exe").write_bytes(b"MZ")
    (tmp_path / "x64" / "Memoria.log").write_text("fake log\n", encoding="utf-8")
    mod = tmp_path / "FF9CustomMap"
    mod.mkdir()
    (mod / "DictionaryPatch.txt").write_text(f"FieldScene {FIELD} 11 CHEST_ROOM CHEST_ROOM {FIELD}\n",
                                             encoding="utf-8")
    return tmp_path


def session(game_path, fake):
    return Session(game_path=game_path, run_dir=game_path / "run", save_dir=game_path / "player-saves",
                   pid_probe=lambda: [], launcher=lambda exe: fake.start(), boot_timeout=15.0,
                   verbose=False)


def on_bench(g, *, lock=True, hostscene=True):
    """New Game on the bench field, the selftest role forced, the field-gate bench on -- and, by default, the bench
    lock and the simulated host scene (the design's A-checks all run under ``lock 1`` + ``hostscene 1``)."""
    g.newgame(settle=0)
    g.warp(FIELD)
    g.netsync("selftest", 1)
    g.netsync("bench", 1)
    if hostscene:
        g.netsync("hostscene", 1)
    if lock:
        g.netsync("lock", 1)


def rt(st) -> float:
    """The stand-in's virtual clock, seconds -- the clock its guest tick runs on."""
    return float(st.raw["rt"])


def stays(g, predicate, *, frames: int, what: str):
    """Wait ``frames`` frames, then assert the predicate still holds -- a "nothing happened" check that waited."""
    g.wait_frames(frames)
    st = g.state
    assert predicate(st), f"{what}: {st.netsync!r} text={st.text!r}"
    return st


# --------------------------------------------------------------------------- the agent, read off the patch stack


def _literals(line: str) -> list[str]:
    return re.findall(r'"((?:[^"\\]|\\.)*)"', line)


def _agent_netsync_nothing() -> tuple[dict, dict]:
    """The agent's ``netsync`` block at its "nothing" sentinels (AppendNetsync's catch branch), and the F3 keys it
    pins plus the contract tag (``NetsyncF3Retired``) -- as the LIVE stack leaves HarnessAgent.cs."""
    catch = net_lines("HarnessAgent.cs", r'outer\.Append\("\\"netsync\\":\{\\"enabled')
    head = net_lines("HarnessAgent.cs", r'NetsyncF3Retired = "')
    tail = net_lines("HarnessAgent.cs", r'\+ "\\"align_win')   # the C# `+` continuation line
    assert len(catch) == 1 and len(head) == 1 and len(tail) == 1, (catch, head, tail)
    assert ".Append(NetsyncF3Retired)" in catch[0], catch[0]
    pinned = "".join(_literals(head[0]) + _literals(tail[0]))
    a, b = _literals(catch[0])
    unescape = lambda s: s.replace('\\"', '"')                          # noqa: E731 -- the only escape in them
    nothing = json.loads("{" + unescape(a + pinned + b) + "}")["netsync"]
    return nothing, json.loads("{" + unescape(pinned) + "}")


def _agent_subverbs() -> tuple[str, ...]:
    lines = net_lines("HarnessAgent.cs", r"netsync: unknown sub-verb")
    assert len(lines) == 1, lines
    m = re.search(r"\(([a-z0-9|-]+)\)\"\);", lines[0])
    assert m, lines[0]
    return tuple(m.group(1).split("|"))


def _agent_text(fragment: str) -> bool:
    pattern = re.escape(fragment)
    return bool(net_lines("HarnessAgent.cs", pattern) or net_lines("NetSyncClient.cs", pattern))


def test_the_patch_stack_reader_is_calibrated():
    """Read the instrument before trusting it: the stack's agent publishes the contract tag and every F3.2 key, and
    its sub-verb list carries the F3 ones too."""
    nothing, pinned = _agent_netsync_nothing()
    assert pinned["dialogue"] == "authority" and pinned["pending"] is None and pinned["wait_limit_ms"] == -1
    for key in ("lock", "stale", "lock_engaged", "unlocked", "suppress", "windows", "inbox", "host_settled_ms",
                "orphan_closes", "chip"):
        assert key in nothing, key
    assert nothing["inbox"] == {"count": 0, "heads": []} and nothing["chip"] is None
    assert {"selftest", "bench", "l1", "advance", "choice", "unmatched", "talk"} <= set(_agent_subverbs())
    assert not _agent_text("a refusal no engine has ever said")


def test_the_driver_and_the_stand_in_speak_the_agents_sub_verbs():
    """The driver refuses a sub-verb before spending a step, so its list IS a gate: it must be the agent's, in the
    agent's order -- and the F3.2-only ones are exactly what the F3 agent did not have."""
    agent = _agent_subverbs()
    assert Session.NETSYNC_SUBVERBS == agent == FG.NETSYNC_SUBVERBS
    assert set(Session.NETSYNC_AUTHORITY_SUBVERBS) == set(agent) - set(FG.NETSYNC_SUBVERBS_F3)


def test_the_stand_in_publishes_the_agents_netsync_keys(game):
    """An F3.2 stand-in publishes exactly the agent's keys -- the contract tag and the PINNED F3 keys included, at
    the agent's values -- and an F3 stand-in none of the F3.2 ones."""
    nothing, pinned = _agent_netsync_nothing()
    fake = FakeGame(game)
    doc = fake._netsync_doc()
    assert set(doc) == set(nothing), (set(doc) ^ set(nothing))
    assert {k: doc[k] for k in pinned} == pinned == FG.NETSYNC_F3_PINNED
    fake.netsync_dialogue = None
    old = fake._netsync_doc()
    assert "dialogue" not in old and not (set(old) & {"lock", "stale", "lock_engaged", "windows", "inbox", "chip",
                                                         "orphan_closes", "host_settled_ms", "unlocked"})
    assert old["wait_limit_ms"] == 8000                     # the F3 lockstep's live DialogWaitMs, not the pin


# (fragment the agent says, how to make the stand-in say it). Each fragment is ONE C# literal of the agent's.
REFUSALS = [
    ("netsync lock: needs the selftest role (netsync selftest 1)", lambda f: f._netsync(["lock", "1"])),
    ("netsync stale: needs the selftest role (netsync selftest 1)", lambda f: f._netsync(["stale", "1"])),
    (": needs the selftest role (netsync selftest 1)", lambda f: f._netsync(["hostscene", "1"])),
    ("no co-op client in this process", lambda f: f._netsync(["unlock"])),
    ("needs a live followed session (or the selftest field-gate bench)",
     lambda f: (f._netsync(["selftest", "1"]), f._netsync(["unlock"]))),
    (": no dialogue window is open", lambda f: f._netsync(["click"])),
    ("netsync click: [Control] DisableMouseForMenus is on -- a click never reaches the dialogue",
     lambda f: (setattr(f, "disable_mouse_for_menus", True), f.say("x"), f._netsync(["click"]))),
    ("needs a non-zero <dy> (|dy| > 50 moves a choice)", lambda f: (f.say("x"), f._netsync(["drag", "0"]))),
    ("netsync: no co-op client in this process (netsync selftest 1 first)", lambda f: f._netsync(["unmatched"])),
    ("netsync: the field-gate bench is OFF (netsync bench 1)",
     lambda f: (f._netsync(["selftest", "1"]), f._netsync(["unmatched"]))),
    ("netsync: the bench dialogue lock is OFF (netsync lock 1) -- host events feed the locked inbox",
     lambda f: (f._netsync(["selftest", "1"]), f._netsync(["bench", "1"]), f._netsync(["unmatched"]))),
]


@pytest.mark.parametrize("fragment,provoke", REFUSALS, ids=[r[0][:40] for r in REFUSALS])
def test_the_stand_in_refuses_in_the_agents_words(game, fragment, provoke):
    """Every F3.2 gate the stand-in models refuses with the agent's own words -- the text a scenario's
    ``pytest.raises(match=...)`` and a live run's error latch both carry."""
    assert _agent_text(fragment), f"the live agent no longer says {fragment!r} -- re-read HarnessAgent/NetSyncClient"
    fake = FakeGame(game)
    fake.field_id = FIELD
    with pytest.raises(RuntimeError) as err:
        provoke(fake)
    assert fragment in str(err.value), str(err.value)


def test_an_f3_engine_refuses_the_f32_sub_verbs_in_its_own_words(game):
    """The F3 agent (s84/s85) has no `lock`; its refusal lists the seven sub-verbs it does have."""
    fake = FakeGame(game)
    fake.netsync_dialogue = None
    with pytest.raises(RuntimeError, match=r"unknown sub-verb 'lock' \(selftest\|bench\|l1\|advance\|choice\|"
                                           r"unmatched\|talk\)"):
        fake._netsync(["lock", "1"])


def _agent_argument_refusals() -> dict:
    """The agent's ``throw new ArgumentOutOfRangeException("<param>", "<message>")`` lines in the netsync verb, as the
    LIVE stack leaves HarnessAgent.cs: param -> message."""
    out = {}
    for line in net_lines("HarnessAgent.cs", r'ArgumentOutOfRangeException\("netsync '):
        lit = _literals(line)
        out[lit[0]] = lit[1]
    return out


ARGUMENT_REFUSALS = [
    ("netsync drag", lambda f: (f.say("x"), f._netsync(["drag", "0"]))),
    ("netsync choice", lambda f: (f.say("x"), f._netsync(["choice"]))),
    ("netsync talk", lambda f: f._netsync(["talk"])),
]


@pytest.mark.parametrize("param,provoke", ARGUMENT_REFUSALS, ids=[r[0] for r in ARGUMENT_REFUSALS])
def test_an_argument_refusal_has_the_engines_whole_shape(game, param, provoke):
    """An ArgumentOutOfRangeException's Message under the game's (legacy) Mono is ``message + NewLine + "Parameter
    name: " + param`` -- the agent latches ``"netsync: " + that`` -- never ``"<param>: <message>"``. A stand-in that
    said the latter would let a scenario matching on "netsync drag:" pass here and fail on the engine, so the WHOLE
    text is pinned, both literals read off the stack."""
    agent = _agent_argument_refusals()
    assert param in agent, sorted(agent)
    fake = FakeGame(game)
    fake.field_id = FIELD
    with pytest.raises(RuntimeError) as err:
        provoke(fake)
    assert str(err.value) == f"{agent[param]}\r\nParameter name: {param}", repr(str(err.value))


def test_talk_refuses_a_missing_uid_before_its_gates_and_the_range_after_them(game):
    """The agent's order: Arg() -> -1 for a missing, negative, unparsable or Int32-overflowing uid, refused FIRST
    ("needs an object uid"); then HarnessInjectTalk's gates; then "uid N is outside 0..65535" for one above it."""
    assert _agent_text("needs an object uid") and _agent_text(" is outside 0..65535")
    fake = FakeGame(game)
    fake.field_id = FIELD
    for args in (["talk"], ["talk", "-3"], ["talk", "abc"], ["talk", "99999999999"]):
        with pytest.raises(RuntimeError) as err:
            fake._netsync(args)                             # no client yet: the uid is refused before the gates
        assert str(err.value) == "needs an object uid\r\nParameter name: netsync talk", (args, str(err.value))
    with pytest.raises(RuntimeError, match="no co-op client in this process"):
        fake._netsync(["talk", "70000"])                    # a parsable uid reaches the gates first
    fake._netsync(["selftest", "1"])
    fake._netsync(["bench", "1"])
    with pytest.raises(RuntimeError, match=r"^netsync talk: uid 70000 is outside 0\.\.65535$"):
        fake._netsync(["talk", "70000"])
    fake._netsync(["talk", "3"])
    assert fake.last_talk_uid == 3


def test_talk_publishes_nothing_the_engine_does_not(game):
    """`last_talk_uid` is the stand-in's own receipt: no AppendNetsync (F3 or F3.2) carries it, so it stays out of the
    published block -- the key set is still exactly the agent's after a talk."""
    nothing, _pinned = _agent_netsync_nothing()
    for contract in ("authority", None):
        fake = FakeGame(game)
        fake.netsync_dialogue = contract
        fake.field_id = FIELD
        fake._netsync(["selftest", "1"])
        fake._netsync(["bench", "1"])
        fake._netsync(["talk", "3"])
        doc = fake._netsync_doc()
        assert fake.last_talk_uid == 3 and "last_talk_uid" not in doc, contract
        if contract == "authority":
            assert set(doc) == set(nothing), (set(doc) ^ set(nothing))


# --------------------------------------------------------------------------- State: absent = cannot


F32_BLOCK = {"enabled": True, "role": "selftest", "instance": True, "selftest": True, "forced": True,
             "bench": True, "l1": True, "lock": True, "stale": False, "lock_engaged": True, "unlocked": False,
             "suppress": True, **FG.NETSYNC_F3_PINNED,
             "windows": [{"win": 0, "text": 41, "field": FIELD, "cls": "locked", "state": "CompleteAnimation",
                          "page": 1, "inh": False}],          # page = Dialog.CurrentPage: 1 on the first page
             "inbox": {"count": 1, "heads": [{"field": FIELD, "win": 15, "text": 65535, "kind": 0, "index": 255,
                                              "seq": 0, "scene": 1, "age_ms": 120, "tried": False}]},
             "host_settled_ms": -1, "orphan_closes": 0, "chip": None}


def test_state_reads_absent_f32_keys_as_cannot_never_as_nothing():
    """No block, and an F3 block without the keys, read None on every F3.2 accessor -- an F3 engine's missing
    `lock_engaged` read as False would make a lock assertion green against the wrong DLL."""
    none = State({"frame": 1})
    f3 = State({"frame": 1, "netsync": {"enabled": True, "selftest": True, "l1": True, "suppress": True,
                                        "pending": {"field": FIELD, "win": 15, "text": 65535, "kind": 0,
                                                    "index": 255, "seq": 1}}})
    for st, authority in ((none, None), (f3, False)):
        assert st.dialogue_authority is authority
        assert st.dialogue_lock_engaged is None and st.dialogue_unlocked is None
        assert st.dialogue_windows is None and st.dialogue_inbox is None and st.dialogue_inbox_count is None
        assert st.dialogue_host_settled_ms is None and st.dialogue_orphan_closes is None
        assert st.dialogue_chip is None
    assert none.dialogue_suppressed is None and none.lockstep_suppressed is False    # the F3 reading, kept
    assert f3.dialogue_suppressed is True and f3.lockstep_pending["win"] == 15        # the F3 keys, still read
    # a tag this driver does not know is a contract it cannot read -- neither F3 nor F3.2
    assert State({"frame": 1, "netsync": dict(F32_BLOCK, dialogue="authority2")}).dialogue_authority is None


def test_state_reads_the_f32_block():
    st = State({"frame": 1, "netsync": F32_BLOCK})
    assert st.dialogue_authority is True and st.dialogue_lock_engaged is True and st.dialogue_suppressed is True
    assert st.dialogue_unlocked is False and st.dialogue_host_settled_ms == -1 and st.dialogue_orphan_closes == 0
    assert st.dialogue_windows == F32_BLOCK["windows"] and st.dialogue_windows is not F32_BLOCK["windows"]
    assert st.dialogue_inbox_count == 1 and st.dialogue_inbox["heads"][0]["win"] == 15
    assert st.dialogue_chip == ""                           # published null: no chip drawn -- not "cannot"
    assert st.lockstep_pending is None                      # pinned null on an authority engine
    chip = State({"frame": 1, "netsync": dict(F32_BLOCK, chip="Co-op: following the host's conversation")})
    assert chip.dialogue_chip == "Co-op: following the host's conversation"
    # a bool is never a count, a count never a bool
    odd = State({"frame": 1, "netsync": dict(F32_BLOCK, orphan_closes=True, lock_engaged=1, inbox={"count": False})})
    assert odd.dialogue_orphan_closes is None and odd.dialogue_lock_engaged is None
    assert odd.dialogue_inbox_count is None


# --------------------------------------------------------------------------- the driver's verb


def test_netsync_refuses_an_unknown_sub_verb_before_spending_a_step(game):
    fake = FakeGame(game)
    with session(game, fake) as g:
        g.newgame(settle=0)
        seq = g.state.seq
        with pytest.raises(HarnessError, match=r"unknown sub-verb 'tap-record' \(selftest\|bench\|l1\|hostscene"):
            g.netsync("tap-record", 1)
        assert g.state.seq == seq and not any(s[:1] == ["netsync"] for s in fake.executed)


def test_netsync_refuses_an_f32_verb_on_an_f3_engine_before_spending_a_step(game):
    """An F3 engine answers `lock` "unknown sub-verb" only AFTER the step; the driver names the rebuild first --
    and the F3 verbs keep working against it."""
    fake = FakeGame(game)
    fake.netsync_dialogue = None
    with session(game, fake) as g:
        g.newgame(settle=0)
        st = g.netsync("selftest", 1)
        assert st.dialogue_authority is False and st.dialogue_lock_engaged is None
        for sub in Session.NETSYNC_AUTHORITY_SUBVERBS:
            with pytest.raises(HarnessError, match=rf"netsync {sub}: .*F3 lockstep.*s96"):
                g.netsync(sub, 1)
        assert not any(s[:2] in (["netsync", v] for v in Session.NETSYNC_AUTHORITY_SUBVERBS)
                       for s in fake.executed)
        st = g.netsync("l1", 1)
        assert st.netsync["l1"] and "lock" not in st.netsync


def test_the_injections_need_the_bench_lock_not_the_l1_flag(game):
    """F3.2: an injection feeds the guest's inbox, so it needs `lock 1`; the host-scene flag is no longer its gate."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_bench(g, lock=False, hostscene=True)
        fake.say("A line.")
        g.wait_for(lambda s: s.dialog_open, timeout=4.0, what="the line")
        with pytest.raises(HarnessError, match=r"bench dialogue lock is OFF \(netsync lock 1\)"):
            g.netsync("advance")
        g.netsync("hostscene", 0)
        g.netsync("lock", 1)
        st = g.netsync("unmatched")
        assert st.dialogue_inbox_count == 1 and st.dialogue_inbox["heads"][0]["win"] == 15
        assert st.netsync["pending"] is None and st.netsync["applied_seq"] == -1     # the F3 keys stay pinned


# --------------------------------------------------------------------------- the stand-in's lock


def test_a_line_is_locked_from_open_and_one_advance_turns_one_page(game):
    """A1: the window opens LOCKED -- Confirm, a click and a drag move nothing -- and one injected advance turns
    exactly one page; A1v: with the lock off the same click pages it."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_bench(g)
        fake.scene("Page one.", "Page two.", "Page three.")
        st = g.wait_for(lambda s: s.dialogue_windows, timeout=4.0, what="the line to be tracked")
        assert st.text == "Page one." and st.dialogue_suppressed and st.dialogue_lock_engaged
        assert st.dialogue_windows[0]["cls"] == "locked" and st.dialogue_chip == FG._GuestDialog.CHIP_FOLLOWING
        for _ in range(3):
            g.press("confirm", 4)
        g.netsync("click")
        g.netsync("drag", -80)
        st = stays(g, lambda s: s.text == "Page one." and s.dialogue_windows[0]["cls"] == "locked", frames=20,
                   what="local input paged a locked line")
        assert st.dialogue_orphan_closes == 0
        g.netsync("advance")
        st = g.wait_for(lambda s: s.text != "Page one.", timeout=4.0, what="the injected advance")
        assert st.text == "Page two." and st.dialogue_inbox_count == 0
        st = stays(g, lambda s: s.text == "Page two.", frames=40, what="one advance turned two pages")
        assert st.dialogue_windows[0]["cls"] == "locked"   # the next line opened locked too
        g.netsync("lock", 0)                                # A1v: the vanilla parity
        st = g.wait_for(lambda s: s.dialogue_lock_engaged is False, timeout=4.0, what="the lock off")
        assert not st.dialogue_suppressed and st.dialogue_windows == [] and st.dialogue_chip == ""
        g.netsync("click")
        g.wait_for(lambda s: s.text == "Page three.", timeout=4.0, what="the click to page the unlocked line")


def test_an_injection_waits_out_min_show_before_it_pages(game):
    """A host event never pages a line shown for less than MinShowMs -- injected the frame it opens, it waits."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_bench(g)
        fake.scene("First.", "Second.")
        opened = fake.rt                    # the guest tracks it no earlier than this, and MinShowMs runs from there
        st = g.netsync("advance")
        assert st.text == "First." and st.dialogue_inbox_count == 1      # injected a few frames in: it waits
        st = g.wait_for(lambda s: s.text == "Second.", timeout=4.0, what="the advance")
        assert rt(st) - opened >= FG._GuestDialog.MIN_SHOW_MS / 1000.0 - MS and st.dialogue_inbox_count == 0


def test_a_window_open_before_the_lock_stays_local(game):
    """The session rising marks what is ALREADY open Local (it predates the lock): the player's own Confirm pages
    it. The next line opens locked."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_bench(g, lock=False)
        fake.scene("Before the lock.", "After it.")
        g.wait_for(lambda s: s.dialog_open, timeout=4.0, what="the line")
        g.netsync("lock", 1)
        st = g.wait_for(lambda s: s.dialogue_windows, timeout=4.0, what="the line to be tracked")
        assert st.dialogue_windows[0]["cls"] == "local" and not st.dialogue_suppressed
        g.press("confirm", 4)
        st = g.wait_for(lambda s: s.text == "After it." and s.dialogue_windows, timeout=4.0,
                        what="the local Confirm to page the Local line")
        assert st.dialogue_windows[0]["cls"] == "locked" and st.dialogue_suppressed


def test_an_unmatched_event_blocks_nothing_and_the_orphan_rule_closes_the_line(game):
    """A3: a frame no window matches never hands the line back -- it stays locked, local Confirm ignored, for as
    long as the host is in its scene. With the scene down the line turns ORPHANED after OrphanGraceMs and closes at
    reading pace (AutoReadMs), one page at a time, counted in `orphan_closes`."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_bench(g)
        fake.scene("Is this on the host's screen?")
        g.wait_for(lambda s: s.dialogue_windows, timeout=4.0, what="the line to be tracked")
        st = g.netsync("unmatched")
        closes = st.dialogue_orphan_closes
        t0 = rt(st)
        g.press("confirm", 4)
        st = stays(g, lambda s: s.dialog_open and s.dialogue_windows[0]["cls"] == "locked", frames=300,
                   what="the unmatched frame or the local Confirm released the line")
        assert rt(st) - t0 > (FG._GuestDialog.ORPHAN_GRACE_MS + FG._GuestDialog.AUTO_READ_MS) / 1000.0
        assert st.dialogue_inbox_count == 1 and st.dialogue_host_settled_ms == -1
        t1 = rt(g.state)                                    # before the flag falls: the host settles after this
        g.netsync("hostscene", 0)
        st = g.wait_for(lambda s: s.dialogue_windows and s.dialogue_windows[0]["cls"] == "orphaned",
                        timeout=6.0, what="the line to turn orphaned")
        assert rt(st) - t1 >= FG._GuestDialog.ORPHAN_GRACE_MS / 1000.0 - MS
        assert st.dialogue_chip == FG._GuestDialog.CHIP_CLOSING and st.dialog_open
        assert st.dialogue_host_settled_ms >= FG._GuestDialog.ORPHAN_GRACE_MS
        st = g.wait_for(lambda s: not s.dialog_open, timeout=6.0, what="the orphan to auto-close")
        assert rt(st) - t1 >= (FG._GuestDialog.ORPHAN_GRACE_MS + FG._GuestDialog.AUTO_READ_MS) / 1000.0 - MS
        st = g.wait_for(lambda s: s.dialogue_orphan_closes == closes + 1, timeout=4.0, what="the close counted")
        assert st.dialogue_windows == []


def test_the_host_busy_again_takes_an_orphan_back(game):
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_bench(g, hostscene=False)
        fake.scene("A stray line.")
        g.wait_for(lambda s: s.dialogue_windows and s.dialogue_windows[0]["cls"] == "orphaned", timeout=6.0,
                   what="the line to turn orphaned")
        g.netsync("hostscene", 1)
        g.wait_for(lambda s: s.dialogue_windows and s.dialogue_windows[0]["cls"] == "locked", timeout=4.0,
                   what="the orphan back under the host")
        st = stays(g, lambda s: s.dialog_open, frames=400, what="a held line closed while the host was busy")
        assert st.dialogue_orphan_closes == 0 and st.dialogue_windows[0]["cls"] == "locked"


def test_a_dead_link_holds_the_line_for_link_grace_then_lets_go(game):
    """A6: `stale 1` -- the lock holds LinkGraceMs (the chip says why), then every line is the guest's again."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_bench(g)
        fake.scene("Hold on.", "Let go.")
        st = g.wait_for(lambda s: s.dialogue_windows, timeout=4.0, what="the line to be tracked")
        t0 = rt(st)                                         # the link last read live after this
        g.netsync("stale", 1)
        st = g.wait_for(lambda s: s.dialogue_chip == FG._GuestDialog.CHIP_HICCUP, timeout=4.0, what="the hiccup")
        assert st.dialogue_lock_engaged and st.dialogue_suppressed
        st = g.wait_for(lambda s: s.dialogue_lock_engaged is False, timeout=6.0, what="the lock to let go")
        assert rt(st) - t0 >= FG._GuestDialog.LINK_GRACE_MS / 1000.0 - MS
        assert not st.dialogue_suppressed and st.dialogue_windows == [] and st.dialogue_chip == ""
        g.press("confirm", 4)
        g.wait_for(lambda s: s.text == "Let go.", timeout=4.0, what="the local Confirm once the lock let go")


def test_the_panic_unlock_lasts_until_the_next_field_load(game):
    """A7: `unlock` -- this field's lines are the guest's (the host's taps discarded) until a field load, a reload of
    the same field included."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_bench(g)
        fake.scene("Stuck?")
        g.wait_for(lambda s: s.dialogue_windows, timeout=4.0, what="the line to be tracked")
        g.netsync("unmatched")
        g.netsync("unlock")
        st = g.wait_for(lambda s: s.dialogue_unlocked and s.dialogue_lock_engaged is False, timeout=4.0,
                        what="the unlock")
        assert st.dialogue_inbox_count == 0 and not st.dialogue_suppressed and st.dialogue_windows == []
        assert st.dialogue_chip == FG._GuestDialog.CHIP_HOST_SCENE         # the host is still in its scene
        g.press("confirm", 4)
        g.wait_for(lambda s: not s.dialog_open, timeout=4.0, what="the local Confirm on the unlocked field")
        g.warp(FIELD)                                       # a reload of the same field re-arms the lock
        fake.say("A new line.")
        st = g.wait_for(lambda s: s.dialogue_windows, timeout=4.0, what="the line after the reload")
        assert st.dialogue_unlocked is False and st.dialogue_lock_engaged
        assert st.dialogue_windows[0]["cls"] == "locked"


def test_a_choice_follows_the_host_and_never_the_guests_cursor(game):
    """A2: the guest's arrows and drag do not move a locked choice; an injected choice answers the host's index,
    and an out-of-range one the window's default (DLG-10)."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_bench(g)
        fake.scene({"options": ["Yes", "No", "Maybe"], "default": 1},
                   {"options": ["Red", "Blue"], "default": 0})
        g.wait_for(lambda s: s.menu_group == "Dialog.Choice" and s.dialogue_windows, timeout=4.0,
                   what="the choice ready")
        g.press("down", 4)
        g.netsync("drag", -80)
        stays(g, lambda s: s.choice["selected"] == 1, frames=10, what="the guest moved a locked choice")
        g.netsync("choice", 2)
        g.wait_for(lambda s: fake.answered == [2], timeout=4.0, what="the host's choice answered")
        g.wait_for(lambda s: s.menu_group == "Dialog.Choice" and s.choice["count"] == 2, timeout=4.0,
                   what="the second choice ready")
        g.netsync("choice", 40)
        g.wait_for(lambda s: fake.answered == [2, 0], timeout=4.0, what="the out-of-range choice on the default")


def test_a_script_polled_line_is_never_suppressed_nor_driven(game):
    """A8: a FlagButtonInh line ([NFOC], polled by its script) is excluded from `suppress`, a host event is never
    forced onto it, and the orphan rule hands it back rather than closing it."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_bench(g)
        fake.dialog_inh = True
        fake.say("Status: polled.")
        st = g.wait_for(lambda s: s.dialogue_windows, timeout=4.0, what="the line to be tracked")
        assert st.dialogue_windows[0]["inh"] and st.dialogue_windows[0]["cls"] == "locked"
        assert not st.dialogue_suppressed
        assert st.dialogue_chip == FG._GuestDialog.CHIP_HOST_SCENE        # a polled strip is no conversation
        g.netsync("advance")
        stays(g, lambda s: s.text == "Status: polled." and s.dialogue_inbox_count == 1, frames=60,
              what="a host event was forced onto an inh line")
        # the next polled page (another key: the event above still claims the first one until it ages out)
        fake.dialog_text_id = 1
        fake.say("Status: page two.")
        g.netsync("hostscene", 0)
        st = g.wait_for(lambda s: s.dialogue_windows and s.dialogue_windows[0]["cls"] == "local", timeout=6.0,
                        what="the inh line handed back")
        assert st.dialog_open and st.text == "Status: page two." and st.dialogue_orphan_closes == 0


def test_click_and_drag_are_stock_seams_with_no_role_gate(game):
    """A12-shaped: with co-op off a click pages a line and a drag moves a choice, as stock does."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(FIELD)
        fake.scene("One.", "Two.", {"options": ["A", "B", "C"], "default": 0})
        g.wait_for(lambda s: s.text == "One.", timeout=4.0, what="the line")
        st = g.netsync("click")
        assert st.netsync["enabled"] is False and st.dialogue_suppressed is False
        g.wait_for(lambda s: s.text == "Two.", timeout=4.0, what="the click to page it")
        g.netsync("click")
        g.wait_for(lambda s: s.menu_group == "Dialog.Choice", timeout=4.0, what="the choice ready")
        g.netsync("drag", -80)
        g.wait_for(lambda s: s.choice["selected"] == 1, timeout=4.0, what="the drag to move the cursor down")
        g.netsync("drag", 20)                               # |dy| <= 50 moves nothing
        stays(g, lambda s: s.choice["selected"] == 1, frames=10, what="a short drag moved the cursor")


def test_windows_page_is_current_page_counting_from_one(game):
    """windows[].page is Dialog.CurrentPage, which PrepareNextPage post-increments the moment the Phrase is set: the
    first visible page reads 1, each host page turn +1 -- an absolute page written against the stand-in must hold on
    the engine."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_bench(g)
        fake.say("One.", "Two.")
        st = g.wait_for(lambda s: s.dialogue_windows, timeout=4.0, what="the line to be tracked")
        assert st.dialogue_windows[0]["page"] == 1
        g.netsync("advance")
        st = g.wait_for(lambda s: s.text == "Two.", timeout=4.0, what="the host's page turn")
        st = g.wait_for(lambda s: s.dialogue_windows and s.dialogue_windows[0]["page"] == 2, timeout=4.0,
                        what="the tracker to read page 2")
        assert st.dialogue_windows[0]["cls"] == "locked"


def test_an_orphaned_choice_closes_on_its_cancel_row(game):
    """The orphan rule answers a choice the way the engine does -- NetSyncDialog.OrphanChoice(CancelChoice,
    DefaultChoice) -- and an untagged menu's CancelChoice is its LAST row (SetupChoose), not its default: a stand-in
    taking the default would land the opposite branch of every stock-shaped menu."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_bench(g, hostscene=False)                        # the host idle from the start: the line will orphan
        fake.scene({"options": ["Yes", "No", "Close"], "default": 0},
                   {"options": ["Red", "Blue", "Back"], "default": 1, "cancel": -1})
        g.wait_for(lambda s: fake.answered, timeout=10.0, what="the orphan to auto-close the first choice")
        assert fake.answered == [2]                         # the cancel row (count - 1), never the default 0
        g.wait_for(lambda s: len(fake.answered) == 2, timeout=10.0, what="the orphan to auto-close the second")
        assert fake.answered == [2, 1]                      # a tag's cancel of -1: none -- the default
        g.wait_for(lambda s: s.dialogue_orphan_closes == 2, timeout=4.0, what="both closes counted")


def test_choice_cancel_follows_setupchoose():
    assert FG.choice_cancel({"options": ["a", "b", "c"]}) == 2                       # untagged: the last row
    assert FG.choice_cancel({"options": ["a", "b", "c"], "cancel": 1}) == 1          # a tag names it
    assert FG.choice_cancel({"options": ["a", "b", "c"], "cancel": 7}) == 2          # clamped to the last row
    assert FG.choice_cancel({"options": ["a", "b", "c"], "cancel": -1}) == -1        # none: the orphan takes the default
    assert FG.choice_cancel({"options": ["a", "b", "c"], "disabled": [2]}) == 1      # disabled: the highest ACTIVE row
    assert FG.choice_cancel({"options": ["a", "b", "c"], "disabled": [0], "cancel": -1}) == 2


def test_a_battle_return_re_arms_the_panic_unlock(game):
    """The engine re-arms the panic unlock on EVERY field load (RearmDialogLockAtFieldLoad from ApplyStoryBeforeEvents
    in HonoluluFieldMain) -- the field's reload after a battle included, on the same field id."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_bench(g)
        fake.say("Stuck?")
        g.wait_for(lambda s: s.dialogue_windows, timeout=4.0, what="the line to be tracked")
        g.netsync("unlock")
        g.wait_for(lambda s: s.dialogue_unlocked and s.dialogue_lock_engaged is False, timeout=4.0, what="the unlock")
        fake.texts, fake.raw_texts = [], []                 # its script closes it
        fake.start_battle(105)
        g.wait_for(lambda s: s.dialogue_lock_engaged is False and fake.battle_active, timeout=4.0, what="the battle")
        fake.end_battle()
        st = g.wait_for(lambda s: s.dialogue_unlocked is False and s.dialogue_lock_engaged, timeout=4.0,
                        what="the battle's return to re-arm the lock")
        assert st.field_id == FIELD


def test_a_release_restarts_the_bench_host_seq(game):
    """HarnessSelfTest(false) resets _dialogSeq (ResetDialogLockstepState): the first event after a release carries
    seq 0 again -- in inbox.heads and the engine's 'host seq N' lines alike."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_bench(g)
        fake.say("A line.")
        g.wait_for(lambda s: s.dialogue_windows, timeout=4.0, what="the line to be tracked")
        g.netsync("unmatched")
        st = g.netsync("unmatched")                         # seq 0 and 1 (one key: the head is seq 0)
        assert st.dialogue_inbox_count == 2
        g.netsync("selftest", 0)
        for verb in ("selftest", "bench", "hostscene", "lock"):
            g.netsync(verb, 1)
        st = g.netsync("unmatched")
        assert st.dialogue_inbox_count == 1 and st.dialogue_inbox["heads"][0]["seq"] == 0


def test_an_unlocked_click_pages_a_plain_line_and_an_nfoc_one_ignores_it(game):
    """DialogManager.OnClick -> OnKeyConfirm: with nothing locking it, a click PAGES a plain say() line (a no-op
    click there would let A1v/A12 report a click that never landed) -- and an [NFOC] line ignores it (ignoreInputFlag)."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(FIELD)
        fake.say("One.", "Two.")                            # (the stand-in publishes the unread pages as boxes)
        g.wait_for(lambda s: s.texts[:1] == ["One."], timeout=4.0, what="the line")
        g.netsync("click")
        g.wait_for(lambda s: s.text == "Two.", timeout=4.0, what="the click to page it")
        g.netsync("click")
        g.wait_for(lambda s: not s.dialog_open, timeout=4.0, what="the click to close its last page")
        fake.dialog_inh = True
        fake.say("Polled.")
        g.wait_for(lambda s: s.text == "Polled.", timeout=4.0, what="the polled line")
        g.netsync("click")
        stays(g, lambda s: s.text == "Polled.", frames=20, what="a click paged an [NFOC] line")


def test_reset_releases_the_f32_levers(game):
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_bench(g)
        g.netsync("stale", 1)
        g.netsync("unlock")
        g.send("reset")
        st = g.wait_for(lambda s: s.netsync is not None and not s.netsync["forced"], timeout=5.0,
                        what="`reset` to release the override")
        ns = st.netsync
        assert not (ns["bench"] or ns["l1"] or ns["lock"] or ns["stale"])
        assert st.dialogue_lock_engaged is False and st.dialogue_unlocked is False and st.dialogue_inbox_count == 0
