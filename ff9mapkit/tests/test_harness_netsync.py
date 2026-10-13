"""``tools/harness`` and the co-op F3.2 dialogue contract (memoria-patch s96): the driver's ``netsync`` accessors and
verb, and the stand-in's model of the guest's dialogue LOCK -- and [ff9mapkit netsync F3.3] the three additive
capabilities on top of it: s97's diorama WARM RETURN (``dioboot``/``dioleave``, ``netsync.diorama``), s98's dialogue
RING through state section 7 (the bench host ``host <op>``, ``wire``/``epoch``/``head_seq``/...), and s99's
SCRIPT-KEY RELAY + tap-record bench (``host key``, ``tap-record``/``replay``, ``key_hold``/``keys[]``/...).

Same contract as ``test_harness.py``: these pin the DRIVER and the stand-in, and say nothing about the engine -- the
solo benches (``studies/test-harness/scenarios``) against a live game are that proof. F3.2 keeps the harness at
protocol 5: the ``netsync`` block is ADDITIVE, ``dialogue`` = ``"authority"`` names the new contract, and the F3 keys
stay, pinned to "nothing". F3.3 keeps it at 5 too, and keeps the tag: each capability is its keys' PRESENCE. So two
things matter here: an absent key reads as "this engine cannot" (None), never as "nothing there"; and the stand-in's
verbs, refusals and keys are the agent's -- read off the live patch stack (``memoria-patches/``), each capability off
the patch that added it, not retyped, so a drift on either side turns a test red.
"""
import json
import pathlib
import re
import sys

import pytest

from ._patchstack import msr, net_lines

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
    assert not (set(old) & {k for keys in FG.NETSYNC_CAP_KEYS.values() for k in keys})   # nor any F3.3 key
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


def _armed(f, *, bench=True, lock=True):
    """The stand-in in the selftest role with the field-gate bench (and the bench lock) on -- the F3.3 benches' gates."""
    f._netsync(["selftest", "1"])
    if bench:
        f._netsync(["bench", "1"])
    if lock:
        f._netsync(["lock", "1"])
    return f


def _on_field(f):
    """The stand-in on a live field (FieldHUD) in the selftest role: `dioboot`'s gates."""
    f.ui_state = "FieldHUD"
    f._netsync(["selftest", "1"])
    return f


def _inh_line(f):
    f.dialog_inh = True
    f.say("Polled.")
    return f


def _open_windows(f, n):
    """`host open <win> 0` for n distinct windows -- the bench host's open set holds OpenCap (4)."""
    for win in range(n):
        f._netsync(["host", "open", str(win), "0"])
    return f


# [ff9mapkit netsync F3.3] the F3.3 verbs' gates and their ops' own refusals (s97 dioboot/dioleave, s98 host, s99
# tap-record/replay + LAW :1369 at the bench verbs). A literal the agent splices a value into is pinned piecewise.
REFUSALS += [
    ("netsync dioboot: needs the selftest role (netsync selftest 1)", lambda f: f._netsync(["dioboot", "4"])),
    ("netsync dioboot: boots from a live field only (the ~ menu offers it nowhere else)",
     lambda f: (f._netsync(["selftest", "1"]), f._netsync(["dioboot", "4"]))),     # (the stand-in boots at Title)
    ("netsync dioboot: a diorama is already booted",
     lambda f: (_on_field(f)._netsync(["dioboot", "4"]), f._netsync(["dioboot", "4"]))),
    ("netsync dioboot: refused (Memoria.log names why: [NetSync] diorama boot REFUSED)",
     lambda f: (setattr(f, "dio_boot_refusal", "a scene fade is in flight"), _on_field(f)._netsync(["dioboot", "4"]))),
    ("netsync dioleave: no diorama is booted", lambda f: f._netsync(["dioleave"])),
    ("netsync dioleave: deferred -- a scene fade is in flight; retry",
     lambda f: (_on_field(f)._netsync(["dioboot", "4"]), f._netsync(["dioleave"]))),     # mid-swirl
    ("netsync host: no co-op client in this process (netsync selftest 1 first)", lambda f: f._netsync(["host", "adv"])),
    ("' -- the bench host needs the selftest role",
     lambda f: (f._netsync(["selftest", "1"]), f._netsync(["selftest", "0"]), f._netsync(["host", "adv"]))),
    ("netsync host: the field-gate bench is OFF (netsync bench 1)",
     lambda f: _armed(f, bench=False, lock=False)._netsync(["host", "adv"])),
    ("netsync host: the bench dialogue lock is OFF (netsync lock 1) -- the bench host rides the locked lane",
     lambda f: _armed(f, lock=False)._netsync(["host", "adv"])),
    ("netsync host: unknown op '", lambda f: _armed(f)._netsync(["host", "bogus"])),
    ("' (open|shut|adv|choice|key|gap|epoch|freeze|menu|battle)", lambda f: _armed(f)._netsync(["host"])),
    ("netsync host open: no dialogue window is open (or name one: open <win> <text> [cursor])",
     lambda f: _armed(f)._netsync(["host", "open"])),
    ("netsync host open: win 0..255, text 0..65535, cursor 0..254 (or none)",
     lambda f: _armed(f)._netsync(["host", "open", "256", "0"])),
    ("netsync host open: win 0..255, text 0..65535, cursor 0..254 (or none)",
     lambda f: _armed(f)._netsync(["host", "open", "0", "0", "255"])),
    (" windows open (netsync host shut)", lambda f: _open_windows(_armed(f), 5)),
    ("netsync host choice: needs a choice index 0..254", lambda f: _armed(f)._netsync(["host", "choice"])),
    ("netsync host choice: needs a choice index 0..254", lambda f: _armed(f)._netsync(["host", "choice", "255"])),
    (": no dialogue window is open", lambda f: _armed(f)._netsync(["host", "adv"])),
    ("netsync host key: needs <uid 0..255> <bits 0..65535> [cursor 0..255]",
     lambda f: _armed(f)._netsync(["host", "key", "12"])),
    ("netsync host key: needs <uid 0..255> <bits 0..65535> [cursor 0..255]",
     lambda f: _armed(f)._netsync(["host", "key", "256", "64"])),
    ("netsync host key: needs <uid 0..255> <bits 0..65535> [cursor 0..255]",
     lambda f: _armed(f)._netsync(["host", "key", "12", "65536"])),
    ("netsync host gap: needs <n> 1..30000", lambda f: _armed(f)._netsync(["host", "gap", "0"])),
    ("netsync host gap: needs <n> 1..30000", lambda f: _armed(f)._netsync(["host", "gap", "30001"])),
    (" is input-inhibited ([NFOC]/[TIME]) -- no host ever emits a confirm for it ",
     lambda f: _inh_line(_armed(f))._netsync(["advance"])),
    ("(LAW :1369); drive its script's poll with `netsync host key <uid> <bits>` (the polling uid is `key_reader`)",
     lambda f: _inh_line(_armed(f))._netsync(["choice", "0"])),
    (" is input-inhibited ([NFOC]/[TIME]) -- no host ever emits a confirm for it ",
     lambda f: _inh_line(_armed(f))._netsync(["host", "adv"])),
    (" is input-inhibited ([NFOC]/[TIME]) -- no host ever emits a confirm for it ",
     lambda f: _inh_line(_armed(f))._netsync(["host", "choice", "0"])),
    ("netsync tap-record: no co-op client in this process (netsync selftest 1 first)",
     lambda f: f._netsync(["tap-record", "1"])),
    ("' -- the tap bench needs the selftest role",
     lambda f: (f._netsync(["selftest", "1"]), f._netsync(["selftest", "0"]), f._netsync(["tap-record", "1"]))),
    ("netsync tap-record: the field-gate bench is OFF (netsync bench 1)",
     lambda f: _armed(f, bench=False, lock=False)._netsync(["tap-record", "1"])),
    ("netsync replay: no co-op client in this process (netsync selftest 1 first)", lambda f: f._netsync(["replay"])),
    ("' -- the replay bench needs the selftest role",
     lambda f: (f._netsync(["selftest", "1"]), f._netsync(["selftest", "0"]), f._netsync(["replay"]))),
    ("netsync replay: the field-gate bench is OFF (netsync bench 1)",
     lambda f: _armed(f, bench=False, lock=False)._netsync(["replay"])),
    ("netsync replay: the bench dialogue lock is OFF (netsync lock 1) -- the replay feeds the bench host's lane",
     lambda f: _armed(f, lock=False)._netsync(["replay"])),
    ("netsync replay: the tape is empty (netsync tap-record 1, play the scene with the lock OFF, then tap-record 0)",
     lambda f: _armed(f)._netsync(["replay", "0"])),
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
    ("netsync dioboot", lambda f: _on_field(f)._netsync(["dioboot"])),          # [ff9mapkit netsync F3.3] s97
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
        with pytest.raises(HarnessError, match=r"unknown sub-verb 'tape' \(selftest\|bench\|l1\|hostscene.*"
                                               r"\|tap-record\|replay\)"):
            g.netsync("tape", 1)
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


@pytest.mark.parametrize("engine", ["s96", "s99"])
def test_a_script_polled_line_is_never_suppressed_nor_driven(game, engine):
    """A8: a FlagButtonInh line ([NFOC], polled by its script) is excluded from `suppress`, a host event is never
    forced onto it, and the orphan rule hands it back rather than closing it. On s96 the bench still FABRICATES the
    event (it ages out unapplied); [ff9mapkit netsync F3.3] on s99 the bench REFUSES it at the call site -- LAW :1369:
    no host ever emits a confirm for an input-inhibited window, its script's poll takes a KEY instead."""
    fake = FakeGame(game)
    if engine == "s96":
        fake.netsync_caps = frozenset()
    with session(game, fake) as g:
        on_bench(g)
        fake.dialog_inh = True
        fake.say("Status: polled.")
        st = g.wait_for(lambda s: s.dialogue_windows, timeout=4.0, what="the line to be tracked")
        assert st.dialogue_windows[0]["inh"] and st.dialogue_windows[0]["cls"] == "locked"
        assert not st.dialogue_suppressed
        assert st.dialogue_chip == FG._GuestDialog.CHIP_HOST_SCENE        # a polled strip is no conversation
        if engine == "s96":
            g.netsync("advance")
            stays(g, lambda s: s.text == "Status: polled." and s.dialogue_inbox_count == 1, frames=60,
                  what="a host event was forced onto an inh line")
        else:
            with pytest.raises(HarnessError, match=r"win 0 text 0 is input-inhibited .*LAW :1369.*netsync host key"):
                g.netsync("advance")
            stays(g, lambda s: s.text == "Status: polled." and s.dialogue_inbox_count == 0
                  and s.dialogue_head_seq == 0, frames=60, what="a refused event reached the ring or the line")
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


@pytest.mark.parametrize("engine", ["s96", "s99"])
def test_a_release_restarts_the_bench_host_seq(game, engine):
    """HarnessSelfTest(false) resets the bench host's seq (ResetDialogLockstepState): the first event after a release
    carries the FIRST seq again -- in inbox.heads and the engine's 'host seq N' lines alike. s96: the u8 _dialogSeq,
    from 0. [ff9mapkit netsync F3.3] s98+: the ring's u16 seq SKIPS 0, so from 1 -- under a NEW epoch (never the one
    before), and the guest's lane forgets the old one (epoch -1 until the lock rises again)."""
    fake = FakeGame(game)
    if engine == "s96":
        fake.netsync_caps = frozenset()
    first = 0 if engine == "s96" else 1
    with session(game, fake) as g:
        on_bench(g)
        fake.say("A line.")
        g.wait_for(lambda s: s.dialogue_windows, timeout=4.0, what="the line to be tracked")
        g.netsync("unmatched")
        st = g.netsync("unmatched")                         # two events, one key: the head is the first
        assert st.dialogue_inbox_count == 2 and st.dialogue_inbox["heads"][0]["seq"] == first
        epoch = st.dialogue_epoch
        st = g.netsync("selftest", 0)
        if engine == "s99":
            assert st.dialogue_epoch == -1 and st.dialogue_last_seen == -1 and st.dialogue_head_seq == -1
        for verb in ("selftest", "bench", "hostscene", "lock"):
            g.netsync(verb, 1)
        st = g.netsync("unmatched")
        assert st.dialogue_inbox_count == 1 and st.dialogue_inbox["heads"][0]["seq"] == first
        if engine == "s99":
            assert st.dialogue_epoch not in (-1, 0, epoch) and st.dialogue_head_seq == 1
        else:
            assert st.dialogue_epoch is None                # an s96 engine publishes no ring


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
        # [ff9mapkit netsync F3.3] ...and the bench host's levers and the tape (ResetDialogLockstepState)
        for op in ("freeze", "menu", "battle"):
            g.netsync("host", op, 1)
        g.netsync("lock", 0)
        g.netsync("tap-record", 1)
        g.netsync("lock", 1)
        st = g.state
        assert st.bench_host_frozen and st.bench_host_menu and st.bench_host_battle and st.bench_tap_record
        g.send("reset")
        st = g.wait_for(lambda s: s.netsync is not None and not s.netsync["forced"], timeout=5.0,
                        what="`reset` to release the override")
        ns = st.netsync
        assert not (ns["bench"] or ns["l1"] or ns["lock"] or ns["stale"])
        assert st.dialogue_lock_engaged is False and st.dialogue_unlocked is False and st.dialogue_inbox_count == 0
        # exact values: an ABSENT key reads None, and None is not "released" (this module's whole point)
        assert (st.bench_host_frozen, st.bench_host_menu, st.bench_host_battle, st.bench_tap_record) == (False,) * 4
        assert st.dialogue_epoch == -1 and st.dialogue_last_seen == -1 and st.dialogue_head_seq == -1
        assert st.bench_tape == 0 and st.bench_replay_left == 0 and st.script_key_hold is False


# =========================================================================== [ff9mapkit netsync F3.3] s97-s99
# Each capability is ADDITIVE under protocol 5 and the contract tag stays "authority", so everything below is pinned
# to the patch that added it: s97 (the diorama warm return), s98 (the section-7 ring + the bench host), s99 (the
# script-key relay + the tap-record bench).


def _patch_bytes(stem: str) -> bytes:
    """One live patch's bytes, by its number (``"s97"``) -- exactly one live patch carries it."""
    names = [n for n in msr.stack() if n.startswith(stem + "-") and n not in msr.DEAD]
    assert len(names) == 1, (stem, names)
    return (msr.PATCHES / names[0]).read_bytes()


def _subverbs_in(stem: str) -> tuple[str, ...]:
    """The sub-verb list ONE patch's agent prints (the "unknown sub-verb" line it adds)."""
    lines = net_lines("HarnessAgent.cs", r"netsync: unknown sub-verb", [_patch_bytes(stem)])
    assert len(lines) == 1, (stem, lines)
    m = re.search(r"\(([a-z0-9|-]+)\)\"\);", lines[0])
    assert m, lines[0]
    return tuple(m.group(1).split("|"))


def _f3_retired_text() -> str:
    head = net_lines("HarnessAgent.cs", r'NetsyncF3Retired = "')
    tail = net_lines("HarnessAgent.cs", r'\+ "\\"align_win')
    assert len(head) == 1 and len(tail) == 1, (head, tail)
    return "".join(_literals(head[0]) + _literals(tail[0]))


def _catch_doc_in(stem: str) -> dict:
    """The `netsync` "nothing" document ONE patch's AppendNetsync catch line publishes (its two literals around the
    F3 pin, which s96 introduced and no later patch touches)."""
    catch = net_lines("HarnessAgent.cs", r'outer\.Append\("\\"netsync\\":\{\\"enabled', [_patch_bytes(stem)])
    assert len(catch) == 1 and ".Append(NetsyncF3Retired)" in catch[0], (stem, catch)
    a, b = _literals(catch[0])
    unescape = lambda s: s.replace('\\"', '"')                          # noqa: E731 -- the only escape in them
    return json.loads("{" + unescape(a + _f3_retired_text() + b) + "}")["netsync"]


def _agent_host_ops() -> tuple[str, ...]:
    lines = net_lines("NetSyncClient.cs", r"netsync host: unknown op '")
    assert len(lines) == 1, lines
    m = re.search(r"\(([a-z|]+)\)\";", lines[0])
    assert m, lines[0]
    return tuple(m.group(1).split("|"))


def test_each_f33_patch_adds_its_own_sub_verbs_and_keys_in_order():
    """The stand-in's capability table IS the stack's: each F3.3 patch's agent prints the previous patch's sub-verb list
    with that capability's verbs APPENDED, and its catch line carries the previous keys plus exactly that capability's
    keys, in the agent's order -- and the driver names the same patch for every verb."""
    prev_verbs, prev_doc = _subverbs_in("s96"), _catch_doc_in("s96")
    assert prev_verbs == FG.NETSYNC_SUBVERBS_F32
    for cap, (patch, verbs) in FG.NETSYNC_F33_CAPS.items():
        verbs_now, doc_now = _subverbs_in(patch), _catch_doc_in(patch)
        assert verbs_now == prev_verbs + verbs, (patch, verbs_now)
        assert set(prev_doc) <= set(doc_now), (patch, set(prev_doc) - set(doc_now))
        assert [k for k in doc_now if k not in prev_doc] == list(FG.NETSYNC_CAP_KEYS[cap]), patch
        for verb in verbs:
            assert Session.NETSYNC_F33_SUBVERBS[verb][2] == patch, verb
        prev_verbs, prev_doc = verbs_now, doc_now
    assert prev_verbs == _agent_subverbs() == FG.NETSYNC_SUBVERBS
    assert set(Session.NETSYNC_F33_SUBVERBS) == {v for _p, vs in FG.NETSYNC_F33_CAPS.values() for v in vs}
    # each verb's capability accessor is the one that reads the key that patch added
    for verb, (attr, key, _patch, _what) in Session.NETSYNC_F33_SUBVERBS.items():
        cap = next(c for c, (_p, vs) in FG.NETSYNC_F33_CAPS.items() if verb in vs)
        assert key.startswith("netsync.") and key[len("netsync."):] in FG.NETSYNC_CAP_KEYS[cap], (verb, key)
        assert hasattr(State, attr), attr


def test_the_driver_and_the_stand_in_speak_the_bench_hosts_ops():
    """`host <op>`: the driver refuses an op before the step, so its list is a gate -- the engine's, in its order."""
    assert Session.NETSYNC_HOST_OPS == FG.NETSYNC_HOST_OPS == _agent_host_ops()


def test_a_fresh_stand_in_publishes_the_agents_f33_sentinels(game):
    """With no client, every F3.3 key sits at the agent's "nothing" sentinel -- except the two the agent reads off
    process STATICS that exist with no client: `wire` (NetSyncWire.Version, the live constant) and `key_tick`
    (NetSyncField.KeyTick, an Int32 static: 0 before the first key tick). The diorama block's keys are the agent's,
    in its order."""
    nothing, _pinned = _agent_netsync_nothing()
    doc = FakeGame(game)._netsync_doc()
    for keys in FG.NETSYNC_CAP_KEYS.values():
        for key in keys:
            if key not in ("wire", "key_tick"):
                assert doc[key] == nothing[key], (key, doc[key], nothing[key])
    wire = net_lines("NetSyncSocket.cs", r"public const Byte Version = \d+;")
    assert len(wire) == 1, wire
    assert doc["wire"] == int(re.search(r"Version = (\d+);", wire[0]).group(1)) == 14
    assert net_lines("NetSyncField.cs", r"public static Int32 KeyTick;") and doc["key_tick"] == 0
    assert list(doc["diorama"]) == list(nothing["diorama"])


@pytest.mark.parametrize("caps,stem", [((), "s96"), (("diorama",), "s97"), (("diorama", "ring"), "s98")])
def test_an_older_f33_stand_in_is_that_patchs_agent(game, caps, stem):
    """A stand-in with fewer capabilities is exactly an older patch's agent: its keys are that patch's catch line, and a
    later verb is an "unknown sub-verb" listing that patch's verbs."""
    fake = FakeGame(game)
    fake.netsync_caps = frozenset(caps)
    assert set(fake._netsync_doc()) == set(_catch_doc_in(stem))
    later = [v for c, (_p, vs) in FG.NETSYNC_F33_CAPS.items() if c not in caps for v in vs]
    known = "|".join(_subverbs_in(stem))
    for verb in later:
        with pytest.raises(RuntimeError) as err:
            fake._netsync([verb, "1"])
        assert str(err.value) == f"netsync: unknown sub-verb '{verb}' ({known})"


def test_a_non_integer_host_argument_and_a_bad_replay_have_the_engines_whole_shape(game):
    """The two argument refusals the agent SPLICES a value into, pinned piecewise: `host` refuses a non-Int32 argument
    before any gate (Int32.MinValue included -- Arg's own "failed" value), `replay` anything but `[[paced] 1|0]`."""
    host = net_lines("HarnessAgent.cs", r'ArgumentOutOfRangeException\("netsync host"')
    replay = net_lines("HarnessAgent.cs", r'ArgumentOutOfRangeException\("netsync replay"')
    join = net_lines("HarnessAgent.cs", r'\+ String\.Join\(" ", s\.Args, 1, s\.Args\.Length - 1\) \+ "')
    assert len(host) == 1 and len(replay) == 1 and len(join) == 1, (host, replay, join)
    h, r, j = _literals(host[0]), _literals(replay[0]), _literals(join[0])
    fake = FakeGame(game)                                    # no client: the parse is refused before the gates
    for raw in ("x", "1.5", "-2147483648", "99999999999"):
        with pytest.raises(RuntimeError) as err:
            fake._netsync(["host", "adv", raw])
        assert str(err.value) == f"{h[1]}{raw}{h[2]}\r\nParameter name: netsync host", repr(str(err.value))
    for args in (["2"], ["1", "1"], ["paced", "7"], ["x"], ["paced", "1", "0"]):
        with pytest.raises(RuntimeError) as err:
            fake._netsync(["replay", *args])
        assert str(err.value) == f"{r[1]}{' '.join(args)}{j[-1]}\r\nParameter name: netsync replay", repr(str(err.value))
    for args in ([], ["0"], ["1"], ["paced"], ["paced", "0"], ["PACED", "1"]):  # every legal form reaches the gates
        with pytest.raises(RuntimeError, match=r"^netsync replay: no co-op client in this process"):
            fake._netsync(["replay", *args])


def test_dioboot_refuses_a_scene_id_this_install_does_not_register(game):
    fake = _on_field(FakeGame(game))
    fake.field_id = FIELD
    fake.battle_scenes = frozenset({4})
    for scene in ("-1", "5", "x"):
        with pytest.raises(RuntimeError, match=r"^needs a battle scene id registered on this install\r\n"):
            fake._netsync(["dioboot", scene])
    fake._netsync(["dioboot", "4"])
    assert fake._dio["booted"] and fake._dio_by_harness


# --------------------------------------------------------------------------- State: F3.3, absent = cannot

F33_BLOCK = dict(
    F32_BLOCK, wire=14, epoch=4711, head_seq=9, last_seen=9, gaps=1, heartbeat=300, host_stalled=False,
    host_flags=0x0D, host_open=[{"win": 0, "text": 41, "cursor": 2, "page": 1, "flags": 3}], cursor=2,
    key_ignored=0, host_frozen=False, host_menu=True, host_battle=False,
    key_tick=1234, key_hold=True, key_reader=12,
    keys=[{"seq": 10, "field": FIELD, "uid": 12, "bits": 64, "cursor": -1, "age_ms": 40, "state": "stored"}],
    key_served=3, key_expired=1, key_gaveup=0, key_taps=0, tap_record=False, tape=0, replay_left=0,
    diorama={"booted": False, "boot": "warm", "boot_why": None, "boot_field": FIELD, "boot_x": 320.5, "boot_z": -410,
             "primed": False, "returns": 1, "last_return": "warm", "last_return_field": FIELD, "resuming": False})
RING_ACCESSORS = ("dialogue_wire", "dialogue_epoch", "dialogue_head_seq", "dialogue_last_seen", "dialogue_gaps",
                  "dialogue_heartbeat", "dialogue_host_stalled", "dialogue_host_flags", "dialogue_host_flag_set",
                  "dialogue_host_open", "dialogue_cursor", "dialogue_key_ignored", "bench_host_frozen",
                  "bench_host_menu", "bench_host_battle")
KEY_ACCESSORS = ("script_key_tick", "script_key_hold", "script_key_reader", "script_keys", "script_key_served",
                 "script_key_expired", "script_key_gaveup", "script_key_taps", "bench_tap_record", "bench_tape",
                 "bench_replay_left")
DIORAMA_ACCESSORS = ("diorama", "diorama_booted", "diorama_boot", "diorama_boot_why", "diorama_boot_field",
                     "diorama_boot_xz", "diorama_primed", "diorama_returns", "diorama_last_return",
                     "diorama_last_return_field", "diorama_resuming")


def test_the_f33_accessor_tables_cover_every_published_key():
    """Every key a capability publishes has an accessor here (a key with none is read raw by a scenario, and raw
    reads an absent key as a KeyError or a default -- the "nothing" this module exists to refuse)."""
    names = {**{k: "ring" for k in RING_ACCESSORS}, **{k: "keys" for k in KEY_ACCESSORS}}
    assert len(FG.NETSYNC_CAP_KEYS["ring"]) == len(RING_ACCESSORS) - 1          # + the decoded flag set
    assert len(FG.NETSYNC_CAP_KEYS["keys"]) == len(KEY_ACCESSORS)
    assert len(FG.NETSYNC_F33_CAPS) == 3 and all(hasattr(State, n) for n in [*names, *DIORAMA_ACCESSORS])
    assert set(F33_BLOCK["diorama"]) == {"booted", "boot", "boot_why", "boot_field", "boot_x", "boot_z", "primed",
                                         "returns", "last_return", "last_return_field", "resuming"}
    assert len(DIORAMA_ACCESSORS) == len(F33_BLOCK["diorama"])                  # boot_x + boot_z = one, + the block


def test_state_reads_absent_f33_keys_as_cannot_never_as_nothing():
    """No block reads None on every F3.3 accessor and capability; an s96 block (no `wire`, no `key_hold`, no `diorama`)
    reads False on the three capabilities and None on every accessor; an s98 block (the ring without the key relay or
    the diorama -- a stand-in fiction, kept to prove the three are read separately) reads exactly that."""
    none = State({"frame": 1})
    f32 = State({"frame": 1, "netsync": F32_BLOCK})
    for st, cap in ((none, None), (f32, False)):
        assert st.dialogue_ring is cap and st.script_key_relay is cap and st.diorama_warm_return is cap
        for name in RING_ACCESSORS + KEY_ACCESSORS + DIORAMA_ACCESSORS:
            assert getattr(st, name) is None, name
    ring_only = {k: v for k, v in F33_BLOCK.items()
                 if k not in FG.NETSYNC_CAP_KEYS["keys"] and k not in FG.NETSYNC_CAP_KEYS["diorama"]}
    s98 = State({"frame": 1, "netsync": ring_only})
    assert s98.dialogue_ring is True and s98.script_key_relay is False and s98.diorama_warm_return is False
    assert s98.dialogue_epoch == 4711 and all(getattr(s98, n) is None for n in KEY_ACCESSORS + DIORAMA_ACCESSORS)


def test_state_reads_the_f33_block():
    st = State({"frame": 1, "netsync": F33_BLOCK})
    assert st.dialogue_ring is True and st.script_key_relay is True and st.diorama_warm_return is True
    assert (st.dialogue_wire, st.dialogue_epoch, st.dialogue_head_seq, st.dialogue_last_seen) == (14, 4711, 9, 9)
    assert (st.dialogue_gaps, st.dialogue_heartbeat, st.dialogue_host_flags, st.dialogue_cursor) == (1, 300, 0x0D, 2)
    assert st.dialogue_host_flag_set == {"scene", "line", "on_field"}
    assert st.dialogue_host_stalled is False and st.dialogue_key_ignored == 0
    assert (st.bench_host_frozen, st.bench_host_menu, st.bench_host_battle) == (False, True, False)
    assert st.dialogue_host_open == F33_BLOCK["host_open"] and st.dialogue_host_open[0] is not F33_BLOCK["host_open"][0]
    assert (st.script_key_tick, st.script_key_hold, st.script_key_reader) == (1234, True, 12)
    assert st.script_keys == F33_BLOCK["keys"] and st.script_keys[0] is not F33_BLOCK["keys"][0]
    assert (st.script_key_served, st.script_key_expired, st.script_key_gaveup, st.script_key_taps) == (3, 1, 0, 0)
    assert (st.bench_tap_record, st.bench_tape, st.bench_replay_left) == (False, 0, 0)
    assert st.diorama == F33_BLOCK["diorama"] and st.diorama is not F33_BLOCK["diorama"]
    assert (st.diorama_booted, st.diorama_boot, st.diorama_boot_why) == (False, "warm", "")     # null why: ""
    assert st.diorama_boot_xz == (320.5, -410.0) and st.diorama_boot_field == FIELD
    assert (st.diorama_primed, st.diorama_returns, st.diorama_last_return) == (False, 1, "warm")
    assert st.diorama_last_return_field == FIELD and st.diorama_resuming is False
    # no section on the lane: no flags to name; a fresh diorama block: "" (no boot yet), never None ("cannot")
    assert State({"frame": 1, "netsync": dict(F33_BLOCK, host_flags=-1)}).dialogue_host_flag_set is None
    assert State({"frame": 1, "netsync": dict(F33_BLOCK, host_flags=0)}).dialogue_host_flag_set == frozenset()
    fresh = State({"frame": 1, "netsync": dict(F33_BLOCK, diorama=dict(F33_BLOCK["diorama"], boot=None, boot_x=None,
                                                                       boot_z=None, last_return=None))})
    assert fresh.diorama_boot == "" and fresh.diorama_last_return == "" and fresh.diorama_boot_xz is None
    # a bool is never a count, a count never a bool -- and a wrong-typed block is no block
    odd = State({"frame": 1, "netsync": dict(F33_BLOCK, host_stalled=1, gaps=True, key_hold=1, keys={}, epoch=1.5,
                                             diorama=dict(F33_BLOCK["diorama"], returns=True, booted=0, boot_x=True))})
    assert odd.dialogue_host_stalled is None and odd.dialogue_gaps is None and odd.script_key_hold is None
    assert odd.script_keys is None and odd.dialogue_epoch is None and odd.script_key_relay is False
    assert odd.diorama_returns is None and odd.diorama_booted is None and odd.diorama_boot_xz is None
    assert State({"frame": 1, "netsync": dict(F33_BLOCK, diorama=[])}).diorama_warm_return is False


# --------------------------------------------------------------------------- the driver: F3.3 capabilities


@pytest.mark.parametrize("missing", ["diorama", "ring", "keys"])
def test_netsync_refuses_an_f33_verb_its_engine_lacks_before_spending_a_step(game, missing):
    """An engine without a capability answers its verb "unknown sub-verb" only AFTER the step; the driver names the
    patch first. The capabilities the engine HAS still reach it (whose own gates may refuse them -- after the step)."""
    fake = FakeGame(game)
    gone = {"ring", "keys"} if missing == "ring" else {missing}     # the key relay rides the ring: no engine has it alone
    fake.netsync_caps = frozenset(FG.NETSYNC_F33_CAPS) - gone
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(FIELD)
        g.netsync("selftest", 1)
        for cap in gone:
            patch, verbs = FG.NETSYNC_F33_CAPS[cap]
            for verb in verbs:
                key = Session.NETSYNC_F33_SUBVERBS[verb][1]
                with pytest.raises(HarnessError, match=rf"^netsync {verb}: the deployed engine publishes no "
                                                       rf"`{re.escape(key)}` .*\(memoria-patch {patch}\)"):
                    g.netsync(verb, *(("adv",) if verb == "host" else ()))
        lacking = {v for cap in gone for v in FG.NETSYNC_F33_CAPS[cap][1]}
        assert not any(s[:1] == ["netsync"] and s[1:2] and s[1] in lacking for s in fake.executed)
        for cap in set(FG.NETSYNC_F33_CAPS) - gone:
            verb = FG.NETSYNC_F33_CAPS[cap][1][0]
            try:
                g.netsync(verb, *({"dioboot": (4,), "host": ("adv",), "tap-record": (1,)}[verb]))
            except HarnessError:
                pass                                        # the agent's own gate, after the step: fine
            assert any(s[:2] == ["netsync", verb] for s in fake.executed), verb


def test_netsync_refuses_an_unknown_host_op_before_spending_a_step_in_the_engines_words(game):
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_bench(g)
        n = len(fake.executed)
        for op in ("bogus", "", "opens"):
            with pytest.raises(HarnessError) as err:
                g.netsync("host", *((op,) if op else ()))
            with pytest.raises(RuntimeError) as agent:
                fake._netsync(["host", *((op,) if op else ())])      # what the engine would say after its gates
            assert str(err.value) == str(agent.value), (str(err.value), str(agent.value))
        assert len(fake.executed) == n
        st = g.netsync("host", "MENU", 1)                    # the agent lowercases the op; so does the driver
        assert st.bench_host_menu is True and fake.executed[-1] == ["netsync", "host", "MENU", "1"]


def test_an_f3_engine_refuses_the_f33_verbs_naming_the_patch(game):
    fake = FakeGame(game)
    fake.netsync_dialogue = None
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.netsync("selftest", 1)
        for verb, (_attr, _key, patch, _what) in Session.NETSYNC_F33_SUBVERBS.items():
            with pytest.raises(HarnessError, match=rf"netsync {verb}: .*F3 lockstep.*an F3\.3 verb .*memoria-patch "
                                                   rf"{patch}.*memoria-patch s96"):
                g.netsync(verb)


# --------------------------------------------------------------------------- the stand-in: the ring (s98)


def test_seq_helpers_follow_the_engines_skip_zero_u16():
    assert FG._seq_after(1, 0xFFFF) and not FG._seq_after(0xFFFF, 1) and not FG._seq_after(5, 5)
    assert FG._seq_steps(0xFFFF, 1) == 1 and FG._seq_steps(0, 1) == 1 and FG._seq_steps(10, 50) == 40
    assert FG._seq_steps(50, 10) == 0 and FG._seq_steps(0xFFF0, 5) == 20     # 0 is not a seq: 15 + 5
    ring = FG._BenchHost(__import__("random").Random(1))
    ring.ensure()
    ring.seq = 0xFFFE
    assert [ring.append(FG.KIND_ADV, 0, FIELD, 0, 0, 0, 0) for _ in range(3)] == [0xFFFF, 1, 2]
    for _ in range(40):
        ring.append(FG.KIND_ADV, 0, FIELD, 0, 0, 0, 0)
    assert len(ring.ring) == FG._BenchHost.RING_CAP and ring.ring[-1]["seq"] == ring.seq   # drop-oldest at 32


def test_a_new_epoch_is_never_zero_nor_either_of_the_last_two():
    class Rigged:                                           # draws 0, then the current, then the previous, then new
        def __init__(self):
            self.draws = [0, 7, 0, 7, 9, 0, 9, 7, 11]

        def randrange(self, lo, hi):
            return self.draws.pop(0)

    ring = FG._BenchHost(Rigged())
    ring.ensure()
    assert ring.epoch == 7                                  # 0 refused
    ring.reset()
    assert ring.epoch == 9 and ring.prev_epoch == 7        # 0 and the current refused
    ring.reset()
    assert ring.epoch == 11 and ring.prev_epoch == 9       # 0, the current AND the one before refused (C3RING-W1)


def test_the_ring_baselines_at_the_session_and_delivers_each_event_once(game):
    """R3: the session's first merge only BASELINES (at the host's head); every later event merges once although the
    bench re-sends the slot every tick -- one advance turns one page, never two; the heartbeat moves every tick."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_bench(g)
        st = g.wait_for(lambda s: s.dialogue_last_seen is not None and s.dialogue_last_seen >= 0, timeout=4.0,
                        what="the session's baseline")
        assert st.dialogue_ring is True and st.dialogue_wire == 14 and 1 <= st.dialogue_epoch <= 0xFFFF
        assert st.dialogue_last_seen == st.dialogue_head_seq == 0
        assert st.dialogue_host_flag_set == {"scene", "on_field"}            # hostscene 1: b0, not b1 control
        hb = st.dialogue_heartbeat
        g.wait_for(lambda s: s.dialogue_heartbeat > hb, timeout=4.0, what="the host heartbeat to move")
        fake.say("One.", "Two.", "Three.")
        g.wait_for(lambda s: s.dialogue_windows, timeout=4.0, what="the line to be tracked")
        st = g.netsync("advance")
        assert st.dialogue_head_seq == st.dialogue_last_seen == 1 and st.dialogue_inbox_count == 1
        st = g.wait_for(lambda s: s.text.startswith("Two."), timeout=4.0, what="the advance")
        st = stays(g, lambda s: s.text.startswith("Two.") and s.dialogue_inbox_count == 0, frames=60,
                   what="a re-sent event applied twice")
        assert st.dialogue_head_seq == st.dialogue_last_seen == 1 and st.dialogue_gaps == 0


def test_a_gap_counts_once_and_its_line_falls_to_the_orphan_rule(game):
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_bench(g)
        fake.say("A line whose page turn was lost.")
        st = g.wait_for(lambda s: s.dialogue_windows, timeout=4.0, what="the line to be tracked")
        gaps = st.dialogue_gaps
        g.netsync("host", "gap", 40)
        st = g.wait_for(lambda s: s.dialogue_gaps == gaps + 1, timeout=4.0, what="the gap")
        assert st.dialogue_head_seq == st.dialogue_last_seen == 40 and st.dialogue_inbox_count == 0
        stays(g, lambda s: s.dialogue_gaps == gaps + 1 and s.dialogue_windows[0]["cls"] == "locked", frames=40,
              what="one gap counted twice, or the line let go while the host is busy")
        g.netsync("hostscene", 0)
        g.wait_for(lambda s: s.dialogue_windows and s.dialogue_windows[0]["cls"] == "orphaned", timeout=8.0,
                   what="the line to fall to the orphan rule")


def test_a_host_epoch_change_clears_the_inbox_and_rebaselines_without_replay(game):
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_bench(g)
        fake.say("Before the relaunch.", "After it.")
        g.wait_for(lambda s: s.dialogue_windows, timeout=4.0, what="the line to be tracked")
        g.netsync("unmatched")
        st = g.netsync("unmatched")
        assert st.dialogue_inbox_count == 2 and st.dialogue_head_seq == 2
        epoch, resets = st.dialogue_epoch, fake._guest.epoch_resets
        g.netsync("host", "epoch")
        st = g.wait_for(lambda s: s.dialogue_epoch != epoch, timeout=4.0, what="the new epoch")
        assert st.dialogue_epoch not in (0, -1) and st.dialogue_inbox_count == 0
        assert st.dialogue_head_seq == st.dialogue_last_seen == 0 and fake._guest.epoch_resets == resets + 1
        g.netsync("advance")                                # the new host session's first event is MERGED, not baseline
        st = g.wait_for(lambda s: s.text == "After it.", timeout=4.0, what="the new session's advance")
        assert st.dialogue_head_seq == st.dialogue_last_seen == 1 and st.dialogue_inbox_count == 0


def test_a_frozen_host_reads_hung_after_host_stall_ms_and_lines_open_then_stay_local(game):
    """R6: `host freeze` -- the heartbeat stops (the slot keeps re-sending), and HostStallMs later the host reads HUNG
    and the lock lets go; `host freeze 0` -- it moves again, the lock re-arms, and what is open then stays Local."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_bench(g)
        fake.say("Is the host still there?")
        st = g.wait_for(lambda s: s.dialogue_windows, timeout=4.0, what="the line to be tracked")
        t0 = rt(st)                                         # the heartbeat last moved after this
        st = g.netsync("host", "freeze")
        assert st.bench_host_frozen and not st.dialogue_host_stalled and st.dialogue_lock_engaged
        hb = st.dialogue_heartbeat
        st = g.wait_for(lambda s: s.dialogue_host_stalled, timeout=20.0, what="the hung-host verdict")
        assert rt(st) - t0 >= FG._GuestDialog.HOST_STALL_MS / 1000.0 - MS and st.dialogue_heartbeat == hb
        st = g.wait_for(lambda s: s.dialogue_lock_engaged is False, timeout=4.0, what="the lock to let go")
        assert st.dialogue_windows == [] and not st.dialogue_suppressed
        g.netsync("host", "freeze", 0)
        st = g.wait_for(lambda s: not s.dialogue_host_stalled and s.dialogue_lock_engaged and s.dialogue_windows,
                        timeout=4.0, what="the lock to re-arm")
        assert st.dialogue_heartbeat != hb and st.dialogue_windows[0]["cls"] == "local" and not st.dialogue_suppressed


def test_the_cursor_mirror_follows_the_host_open_set_and_the_open_set_claims_the_window(game):
    """R4: `host open <cursor>` -- a locked, ready choice's cursor follows the host's (published `cursor`), the guest's
    arrows cannot move it, and the host holding the window open keeps it from orphaning; `host shut` lets it go."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_bench(g)
        fake.scene({"options": ["Yes", "No", "Maybe"], "default": 0})
        g.wait_for(lambda s: s.menu_group == "Dialog.Choice" and s.dialogue_windows, timeout=4.0,
                   what="the choice ready")
        g.netsync("host", "open", 2)
        st = g.wait_for(lambda s: s.dialogue_cursor == 2 and s.choice["selected"] == 2, timeout=4.0,
                        what="the cursor mirror")
        assert st.dialogue_host_open == [{"win": 0, "text": 0, "cursor": 2, "page": 1,
                                          "flags": FG.WF_CHOICE | FG.WF_COMPLETE}]
        assert "line" in st.dialogue_host_flag_set
        # a C2 REGRESSION GUARD, not the mirror's teeth: the arrow gate on a locked choice drops this press before the
        # mirror is involved (DialogManager.OnItemSelect / IsGuestLockedChoice). The mirror's teeth are the cursor
        # landing on the host's row above and following it below.
        g.press("up", 4)
        stays(g, lambda s: s.choice["selected"] == 2, frames=10, what="the guest's arrow moved a mirrored cursor")
        g.netsync("host", "open", 0, 0, 1)                  # the explicit form, same window: the cursor moves with it
        g.wait_for(lambda s: s.dialogue_cursor == 1 and s.choice["selected"] == 1, timeout=4.0,
                   what="the mirror to follow the host")
        g.netsync("hostscene", 0)
        st = stays(g, lambda s: s.dialogue_windows[0]["cls"] == "locked", frames=360,
                   what="a window the host holds open orphaned")
        assert st.dialogue_host_settled_ms == -1             # the host has an input line open: not settled
        g.netsync("host", "shut")
        g.wait_for(lambda s: s.dialogue_windows and s.dialogue_windows[0]["cls"] == "orphaned", timeout=8.0,
                   what="the shut window to orphan")


def test_the_closes_bit_pages_on_to_the_close_and_a_last_page_advance_is_a_no_op(game):
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_bench(g)
        fake.say("P1.", "P2.", "P3.")
        st = g.wait_for(lambda s: s.dialogue_windows, timeout=4.0, what="the line to be tracked")
        t0 = rt(st)
        g.netsync("host", "adv", 1)                         # the host's confirm CLOSED its window: page on to the close
        st = g.wait_for(lambda s: not s.dialog_open, timeout=6.0, what="the catch-up to close the window")
        assert rt(st) - t0 >= 2 * FG._GuestDialog.MIN_SHOW_MS / 1000.0 - MS        # each page shown MinShowMs
        assert st.dialogue_inbox_count == 0 and fake._guest.noop_pages == 0
        fake.say("The last page.")
        g.wait_for(lambda s: s.dialogue_windows, timeout=4.0, what="the next line")
        g.netsync("host", "adv", 0)                         # a page turn this copy does not have
        st = g.wait_for(lambda s: fake._guest.noop_pages == 1, timeout=4.0, what="the no-op")
        stays(g, lambda s: s.text == "The last page." and s.dialogue_inbox_count == 0, frames=30,
              what="a non-closing advance closed the last page")


def test_a_host_in_a_menu_or_a_battle_switches_the_chip(game):
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_bench(g)
        fake.say("Wait for me.")
        g.wait_for(lambda s: s.dialogue_chip == FG._GuestDialog.CHIP_FOLLOWING, timeout=4.0, what="the chip")
        st = g.netsync("host", "menu", 1)
        st = g.wait_for(lambda s: s.dialogue_chip == FG._GuestDialog.CHIP_HOST_MENU, timeout=4.0, what="R7 menu")
        assert st.bench_host_menu and {"menu", "on_field"} <= st.dialogue_host_flag_set
        g.netsync("host", "battle", 1)
        st = g.wait_for(lambda s: s.dialogue_chip == FG._GuestDialog.CHIP_HOST_BATTLE, timeout=4.0, what="R7 battle")
        assert {"battle", "menu"} <= st.dialogue_host_flag_set and "on_field" not in st.dialogue_host_flag_set
        g.netsync("host", "battle", 0)
        g.netsync("host", "menu", 0)
        g.wait_for(lambda s: s.dialogue_chip == FG._GuestDialog.CHIP_FOLLOWING, timeout=4.0, what="following again")


def test_the_ring_heals_a_dead_link_within_link_grace_but_never_replays_past_it(game):
    """WIRE-1: an event the host emits while the lane reads dead rides the ring; the link back inside LinkGraceMs
    delivers it. Past the grace the session dropped -- a re-risen session baselines at the head and replays nothing."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_bench(g)
        fake.say("A.", "B.", "C.")
        g.wait_for(lambda s: s.dialogue_windows, timeout=4.0, what="the line to be tracked")
        g.netsync("stale", 1)
        st = g.netsync("host", "adv")
        assert st.dialogue_head_seq == -1 and st.dialogue_inbox_count == 0          # no lane: nothing seen yet
        g.netsync("stale", 0)
        g.wait_for(lambda s: s.text.startswith("B."), timeout=4.0, what="the healed event")
        g.netsync("stale", 1)
        st = g.netsync("host", "adv")
        g.wait_for(lambda s: s.dialogue_lock_engaged is False, timeout=8.0, what="the grace to run out")
        st = g.netsync("stale", 0)
        st = g.wait_for(lambda s: s.dialogue_lock_engaged and s.dialogue_last_seen == s.dialogue_head_seq == 2,
                        timeout=4.0, what="the re-risen session's baseline")
        assert st.dialogue_windows[0]["cls"] == "local"
        stays(g, lambda s: s.text.startswith("B.") and s.dialogue_inbox_count == 0, frames=40,
              what="an event from before the session replayed")


@pytest.mark.parametrize("engine", ["s98", "s99"])
def test_a_key_without_a_relay_or_a_host_owned_bit_is_counted_and_ignored(game, engine):
    """s98 carries KEY and ignores it (R5 not built); s99 relays it -- unless it carries no host-owned button."""
    fake = FakeGame(game)
    if engine == "s98":
        fake.netsync_caps = frozenset({"diorama", "ring"})
    with session(game, fake) as g:
        on_bench(g)
        g.netsync("host", "key", 12, 64 if engine == "s98" else 1024)
        st = g.wait_for(lambda s: s.dialogue_key_ignored == 1, timeout=4.0, what="the KEY to be ignored")
        assert st.script_keys == ([] if engine == "s99" else None)
        assert st.script_key_relay is (engine == "s99")


# --------------------------------------------------------------------------- the stand-in: the key relay (s99)


def _polled(fake, *, uid=12, choice=None, control=False):
    """A talk's [NFOC] line its own script polls (B_KEYON Confirm, reader `uid`), control off as a talk holds it."""
    fake.control = control
    fake.dialog_inh = True
    fake.dialog_poll = {"uid": uid, "mask": 0x40}
    if choice is None:
        fake.say("Status: polled.", "Status: page two.")
    else:
        fake.offer(choice)


def test_a_polled_page_answers_the_hosts_key_never_the_guests_press(game):
    """R-B2: under the script-key lock the guest's own Confirm never reaches the poll (the reader is published), and
    `host key <uid> 64` -- compact b6, Confirm -- is served ONCE to that reader's poll: one page, by its own script."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_bench(g)
        _polled(fake)
        st = g.wait_for(lambda s: s.dialogue_windows, timeout=4.0, what="the polled line to be tracked")
        assert st.script_key_hold is True and st.dialogue_windows[0]["inh"] and not st.dialogue_suppressed
        for _ in range(3):
            g.press("confirm", 4)
        st = stays(g, lambda s: s.text.startswith("Status: polled."), frames=20, what="the guest's press was polled")
        assert st.script_key_reader == 12 and fake.script_poll_hits == []
        served = st.script_key_served
        g.netsync("host", "key", 12, 64)
        st = g.wait_for(lambda s: s.text == "Status: page two.", timeout=4.0, what="the relayed press")
        assert fake.script_poll_hits == [{"uid": 12, "bits": 64, "by": "host", "choice": None}]
        st = stays(g, lambda s: s.text == "Status: page two.", frames=20, what="one press served twice")
        assert st.script_key_served == served + 1 and st.script_keys == []


def test_a_key_for_another_reader_waits_then_expires_once_both_sides_idle(game):
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_bench(g)
        _polled(fake)
        g.wait_for(lambda s: s.dialogue_windows, timeout=4.0, what="the polled line to be tracked")
        st = g.netsync("host", "key", 13, 64)
        st = g.wait_for(lambda s: s.script_keys and s.script_keys[0]["state"] == "stored", timeout=4.0,
                        what="the KEY released (nothing ahead of it)")
        assert st.script_keys[0]["uid"] == 13 and st.script_keys[0]["field"] == FIELD
        expired = st.script_key_expired
        st = stays(g, lambda s: s.script_keys and s.dialog_open, frames=150, what="a busy host's KEY expired")
        assert st.script_key_expired == expired and fake.script_poll_hits == []
        t0 = rt(g.state)
        g.netsync("hostscene", 0)                           # both sides idle: the host's scene down, control back
        fake.control = True
        st = g.wait_for(lambda s: s.script_key_expired == expired + 1, timeout=6.0, what="the idle expiry")
        assert rt(st) - t0 >= FG._GuestDialog.KEY_IDLE_MS / 1000.0 - MS and st.script_keys == []
        assert fake.script_poll_hits == []                  # never served to uid 12's poll


def test_a_polled_choice_takes_the_hosts_cursor_before_its_press(game):
    """A polled choice (the save moogle's IsButton + GetDialogChoice): the guest's arrows are held off it under the
    hold, and the KEY's cursor lands on the window BEFORE its press is served -- the poll commits the host's row."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_bench(g)
        _polled(fake, choice=["Save", "Tent", "Cancel"])
        st = g.wait_for(lambda s: s.dialogue_windows, timeout=4.0, what="the polled choice to be tracked")
        assert st.dialogue_suppressed is True               # C3KEYS-2: a host-driven polled choice swallows the keys
        g.press("down", 4)
        g.press("confirm", 4)
        stays(g, lambda s: s.choice and s.choice["selected"] == 0, frames=20, what="the guest moved or polled it")
        assert fake.script_poll_hits == []
        g.netsync("host", "key", 12, 64, 1)
        g.wait_for(lambda s: not s.dialog_open, timeout=4.0, what="the relayed press with its cursor")
        assert fake.answered == [1] and fake.script_poll_hits == [{"uid": 12, "bits": 64, "by": "host", "choice": 1}]


@pytest.mark.parametrize("opening,gives_up", [(90, False), (900, True)])     # frames: 1.5 s < KeyGuardMs < 15 s
def test_a_key_waits_behind_an_earlier_host_event_for_its_open_line(game, opening, gives_up):
    """THE ORDERING GUARD: a KEY merged after a CHO that is still pending for the open, driven line stays PENDING until
    that CHO applies -- or, after KeyGuardMs, is released anyway with a give-up (the CHO never applied here)."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_bench(g)
        fake.scene({"options": ["A", "B"], "default": 0}, opening=opening)
        g.wait_for(lambda s: s.dialogue_windows, timeout=4.0, what="the choice window to be tracked")
        g.netsync("choice", 1)
        t0 = rt(g.state)
        st = g.netsync("host", "key", 12, 64)
        assert st.script_keys and st.script_keys[0]["state"] == "pending", st.script_keys
        gave = st.script_key_gaveup
        st = g.wait_for(lambda s: s.script_keys and s.script_keys[0]["state"] == "stored", timeout=10.0,
                        what="the KEY released")
        if gives_up:
            assert st.script_key_gaveup == gave + 1 and fake.answered == []
            assert rt(st) - t0 >= FG._GuestDialog.KEY_GUARD_MS / 1000.0 - MS
        else:
            assert st.script_key_gaveup == gave and fake.answered == [1]


def test_a_rerisen_session_leaves_an_open_polled_line_its_own_polls_until_the_host_presses(game):
    """C3KEYS-4: a session that rises over a Local polled line does not mask its polls (the press the outage hid was
    baselined away) -- the guest's own Confirm still drives it -- until a host press for this field arrives."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_bench(g, lock=False)
        _polled(fake)
        g.wait_for(lambda s: s.dialog_open, timeout=4.0, what="the polled line")
        g.netsync("lock", 1)
        st = g.wait_for(lambda s: s.dialogue_windows and s.dialogue_windows[0]["cls"] == "local", timeout=4.0,
                        what="the line to stay Local")
        assert st.script_key_hold is False                  # the host is busy, but this field's Local line owns it
        g.press("confirm", 4)
        g.wait_for(lambda s: s.text == "Status: page two.", timeout=4.0, what="its own poll to take the press")
        assert fake.script_poll_hits[-1]["by"] == "local"
        g.netsync("host", "key", 12, 64)
        g.wait_for(lambda s: not s.dialog_open, timeout=4.0, what="the host's press to take the polls back")
        assert fake.script_poll_hits[-1]["by"] == "host" and len(fake.script_poll_hits) == 2


def test_a_key_is_never_served_to_a_control_on_read(game):
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_bench(g)
        _polled(fake, control=True)                         # a free-walk loot poll, control ON
        g.wait_for(lambda s: s.dialogue_windows, timeout=4.0, what="the line to be tracked")
        g.netsync("host", "key", 12, 64)
        st = g.wait_for(lambda s: s.script_keys and s.script_keys[0]["state"] == "stored", timeout=4.0,
                        what="the KEY stored")
        served = st.script_key_served
        g.press("confirm", 4)                               # ...and the free-walk mask eats the guest's own press
        st = stays(g, lambda s: s.text.startswith("Status: polled."), frames=40, what="a control-on read polled")
        assert st.script_key_served == served and fake.script_poll_hits == []


def test_with_co_op_off_a_poll_reads_the_guests_own_press_and_the_key_tick_counts(game):
    """R-B7 vanilla: no selftest, no bench -- the filter returns the keys untouched (the stock cutscene-wait rule) and
    nothing taps; only `key_tick` counts."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(FIELD)
        _polled(fake)
        st = g.wait_for(lambda s: s.dialog_open, timeout=4.0, what="the polled line")
        tick = st.script_key_tick
        g.press("confirm", 4)
        st = g.wait_for(lambda s: s.text == "Status: page two.", timeout=4.0, what="the guest's own press")
        assert fake.script_poll_hits == [{"uid": 12, "bits": 64, "by": "local", "choice": None}]
        assert st.script_key_tick > tick and st.script_key_hold is False and st.script_key_reader == -1
        assert st.netsync["enabled"] is False and st.script_key_taps == 0 and st.bench_tape == 0


# --------------------------------------------------------------------------- the stand-in: tap-record / replay (R9)


def test_tap_record_tapes_local_confirms_and_replay_drives_the_locked_copy_through_the_ring(game):
    """R-B3: with the lock OFF the player's real confirms record onto the tape (an ADV each, closes bit set); with the
    lock ON `replay 0` feeds them all into the bench host's ring, and the re-opened lines close by the host's seqs."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_bench(g, lock=False, hostscene=False)
        st = g.netsync("tap-record", 1)
        assert st.bench_tap_record and st.bench_tape == 0
        fake.scene("One.", "Two.")
        g.wait_for(lambda s: s.text == "One.", timeout=4.0, what="the first line")
        g.press("confirm", 4)
        g.wait_for(lambda s: s.text == "Two.", timeout=4.0, what="the second line")
        g.press("confirm", 4)
        g.wait_for(lambda s: not s.dialog_open, timeout=4.0, what="the scene's end")
        st = g.netsync("tap-record", 0)
        assert st.bench_tape == 2 and not st.bench_tap_record
        assert [(t["kind"], t["c"] & 0x80) for t in fake._tape] == [(FG.KIND_ADV, 0x80)] * 2
        g.netsync("hostscene", 1)
        g.netsync("lock", 1)
        fake.scene("One.", "Two.")
        g.wait_for(lambda s: s.dialogue_windows and s.dialogue_windows[0]["cls"] == "locked", timeout=4.0,
                   what="the replayed line locked")
        g.press("confirm", 4)
        stays(g, lambda s: s.text == "One.", frames=20, what="the guest paged a locked line")
        st = g.netsync("replay", 0)
        assert st.bench_replay_left == 0 and not st.bench_tap_record
        st = g.wait_for(lambda s: not s.dialog_open, timeout=6.0, what="the replay to close both lines")
        assert st.dialogue_inbox_count == 0 and st.dialogue_head_seq == 2 and st.bench_tape == 2


def test_a_paced_replay_feeds_the_tape_at_the_recorded_intervals(game):
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_bench(g, lock=False, hostscene=False)
        g.netsync("tap-record", 1)
        fake.scene("One.", "Two.")
        g.wait_for(lambda s: s.text == "One.", timeout=4.0, what="the first line")
        g.press("confirm", 4)
        g.wait_for(lambda s: s.text == "Two.", timeout=4.0, what="the second line")
        g.wait_frames(90)                                   # 1.5 s between the two presses
        g.press("confirm", 4)
        g.wait_for(lambda s: not s.dialog_open, timeout=4.0, what="the scene's end")
        g.netsync("tap-record", 0)
        gap = fake._tape[1]["t"] - fake._tape[0]["t"]
        assert gap >= 1500
        g.netsync("hostscene", 1)
        g.netsync("lock", 1)
        t0 = rt(g.state)
        st = g.netsync("replay")                            # paced (the default)
        assert st.bench_replay_left == 1                    # the first is due at once, the second `gap` later
        st = g.wait_for(lambda s: s.bench_replay_left == 0, timeout=6.0, what="the paced second event")
        assert rt(st) - t0 >= gap / 1000.0 - MS and st.dialogue_head_seq == 2


def test_tap_record_tapes_a_polled_key_and_replay_serves_it_to_the_same_reader(game):
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_bench(g, lock=False, hostscene=False)
        g.netsync("tap-record", 1)
        _polled(fake)
        g.wait_for(lambda s: s.dialog_open, timeout=4.0, what="the polled line")
        g.press("confirm", 4)
        g.wait_for(lambda s: s.text == "Status: page two.", timeout=4.0, what="its own poll")
        st = g.netsync("tap-record", 0)
        assert st.bench_tape == 1 and st.script_key_taps == 1
        assert {k: fake._tape[0][k] for k in ("kind", "a", "b", "c")} == {"kind": FG.KIND_KEY, "a": 12, "b": 64, "c": 0xFF}
        g.netsync("hostscene", 1)
        g.netsync("lock", 1)
        _polled(fake)
        g.wait_for(lambda s: s.dialogue_windows and s.dialogue_windows[0]["cls"] == "locked", timeout=4.0,
                   what="the re-opened polled line")
        g.press("confirm", 4)
        stays(g, lambda s: s.text.startswith("Status: polled."), frames=20, what="the guest's own press was polled")
        g.netsync("replay", 0)
        g.wait_for(lambda s: s.text == "Status: page two.", timeout=4.0, what="the replayed press")
        assert [h["by"] for h in fake.script_poll_hits] == ["local", "host"]


def test_tap_record_never_records_under_the_lock(game):
    """TapRecording needs the bench lock OFF: the lock's own applied events must never record themselves."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_bench(g)
        g.netsync("tap-record", 1)
        fake.scene("One.")
        g.wait_for(lambda s: s.dialogue_windows, timeout=4.0, what="the line")
        g.netsync("advance")
        g.wait_for(lambda s: not s.dialog_open, timeout=4.0, what="the host's advance")
        st = stays(g, lambda s: s.bench_tape == 0, frames=10, what="a locked apply recorded itself")
        assert st.bench_tap_record is True


# --------------------------------------------------------------------------- the stand-in: the diorama (s97)


def _dio_bench(fake, *, spawn=(-100.0, 250.0)):
    fake.reinit_fields = {FIELD}
    fake.encounter_fields = {FIELD}
    fake.field_spawn = {FIELD: spawn}


def _stand(g, fake, x, z, *, control=True):
    fake.player = [float(x), 0.0, float(z)]
    fake.control = control
    return g.wait_for(lambda s: s.player_x == float(x) and s.player_z == float(z) and s.control == control,
                      timeout=4.0, what="the player placed")


def test_a_free_standing_dioboot_returns_warm_in_place(game):
    """DIO-1, the bench's steps 1-5: from a free-standing field `dioboot` primes the warm return (boot warm, primed,
    the actor's position), the scene is the debug battle; `dioleave` returns through Main_Reinit -- returns +1,
    last_return warm, primed gone -- and once control is back the player stands where he stood and nothing resumes."""
    fake = FakeGame(game)
    _dio_bench(fake)
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(FIELD)
        g.netsync("selftest", 1)
        st = _stand(g, fake, 320.0, -410.0)
        returns = st.diorama_returns
        assert st.diorama_warm_return is True and st.diorama_boot == "" and st.diorama_booted is False
        g.netsync("dioboot", 4)
        st = g.wait_for(lambda s: s.scene == "BattleMapDebug" and s.raw["battle"]["debug"], timeout=4.0,
                        what="the diorama")
        assert st.diorama_booted and st.diorama_boot == "warm" and st.diorama_boot_why == "" and st.diorama_primed
        assert st.diorama_boot_field == FIELD and st.diorama_boot_xz == (320.0, -410.0)
        g.wait_frames(fake.dio_swirl_frames)
        g.netsync("dioleave")
        st = g.wait_for(lambda s: s.diorama_returns == returns + 1, timeout=4.0, what="the return")
        assert st.diorama_last_return == "warm" and st.diorama_last_return_field == FIELD and not st.diorama_primed
        assert not st.diorama_booted
        st = g.wait_for(lambda s: s.control and s.ui_state == "FieldHUD", timeout=4.0, what="control back")
        assert st.diorama_resuming is False and (st.player_x, st.player_z) == (320.0, -410.0)
        assert st.scene == "FieldMap"


@pytest.mark.parametrize("hold,why", [
    ("control", "player control is off (a scene holds it)"),
    ("dialog", "a dialogue window is open"),
    ("menu", "a menu or transition is up"),
    ("no_reinit", f"field {FIELD} has no Main_Reinit (entry-0 tag 10) -- a reinit return would leave every object "
                  f"suspended"),
    ("no_encounters", "no random encounters are armed here -- its Main_Reinit (if any) answers a scripted fight, not "
                      "a random one"),
])
def test_a_dioboot_that_is_not_free_standing_returns_cold_to_main_init(game, hold, why):
    """DIO-1 step 6, the calibration: from a NOT free-standing state the boot keeps today's COLD return and names why
    (the agent's own reason text); the return re-enters through Main_Init and the player lands on its placement."""
    for text in why.split(" -- "):
        assert net_lines("NetSyncDiorama.cs", re.escape(text.split(f"field {FIELD} ")[-1])), text
    fake = FakeGame(game)
    _dio_bench(fake)
    if hold == "no_reinit":
        fake.reinit_fields = set()
    if hold == "no_encounters":
        fake.encounter_fields = set()
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(FIELD)
        g.netsync("selftest", 1)
        _stand(g, fake, 320.0, -410.0, control=hold != "control")
        if hold in ("control", "dialog"):
            fake.say("A line.")
        if hold == "menu":
            fake.open_menu(["Items", "Status"])
        st = g.netsync("dioboot", 4)
        assert st.diorama_boot == "cold" and st.diorama_boot_why == why and not st.diorama_primed
        assert st.diorama_boot_xz is None and st.diorama_booted
        g.wait_frames(fake.dio_swirl_frames)
        g.netsync("dioleave")
        st = g.wait_for(lambda s: s.diorama_last_return == "cold" and s.control, timeout=4.0, what="the cold return")
        assert (st.player_x, st.player_z) == (-100.0, 250.0) and st.diorama_resuming is False


def test_dioleave_mid_swirl_is_deferred_and_a_release_holds_the_role_until_the_teardown(game):
    """`dioleave` while the boot's fade is in flight is refused as deferred (retry); a `reset` with the harness's diorama
    up requests its Leave and HOLDS the selftest role until it tears down -- releasing it under the diorama would
    switch off the fences that end it."""
    fake = FakeGame(game)
    _dio_bench(fake)
    fake.dio_swirl_frames = 10 ** 6
    fake.dio_leave_frames = 240                             # a teardown slow enough to read the held role before it
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(FIELD)
        g.netsync("selftest", 1)
        _stand(g, fake, 10.0, 20.0)
        g.netsync("dioboot", 4)
        with pytest.raises(HarnessError, match=r"netsync dioleave: deferred -- a scene fade is in flight; retry"):
            g.netsync("dioleave")
        fake.dio_swirl_frames = 0
        g.send("reset")
        st = g.state
        assert st.netsync["forced"] and st.diorama_booted       # held: the teardown has not landed
        st = g.wait_for(lambda s: not s.diorama_booted, timeout=6.0, what="the diorama's teardown")
        st = g.wait_for(lambda s: not s.netsync["forced"], timeout=4.0, what="the deferred release")
        assert st.diorama_last_return == "warm" and not st.netsync["enabled"]


def test_a_fresh_boot_forgets_the_previous_leave_so_its_own_swirl_defers_a_dioleave(game):
    """[ff9mapkit netsync F3.3] Boot resets `_leaveTick` ("a fresh boot invalidates any old leave intent"): a second
    boot inside the first diorama's 5 s LeaveRequestedRecently window starts with NO leave intent, so a `dioleave` in
    its swirl is deferred like any other mid-swirl leave -- the old Leave must not read as this boot's."""
    assert net_lines("NetSyncDiorama.cs", r"_leaveTick = Environment\.TickCount - 3600000;.*a fresh boot invalidates")
    fake = FakeGame(game)
    _dio_bench(fake)
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(FIELD)
        g.netsync("selftest", 1)
        _stand(g, fake, 10.0, 20.0)
        g.netsync("dioboot", 4)
        g.wait_frames(fake.dio_swirl_frames)
        g.netsync("dioleave")
        left_rt = fake.rt
        g.wait_for(lambda s: s.control and not s.diorama_booted, timeout=4.0, what="the first return")
        fake.dio_swirl_frames = 10 ** 6                     # the second boot's swirl outlives this test
        g.netsync("dioboot", 4)
        assert fake.rt - left_rt < 5.0                      # still inside the first Leave's 5 s window
        with pytest.raises(HarnessError, match=r"netsync dioleave: deferred -- a scene fade is in flight; retry"):
            g.netsync("dioleave")


@pytest.mark.parametrize("hold", ["warm", "cold"])
def test_a_boot_while_a_returns_entry_script_runs_names_the_level_0_row(game, hold):
    """[ff9mapkit netsync F3.3] WarmVerdict tests `mainLevel <= 0` BEFORE `resuming` and control: while a return's entry
    script runs (Main_Reinit warm, Main_Init cold -- entry 0 at level 0) a boot names the level-0 reason on EITHER
    branch, never "still resuming" or "control is off". (`dioboot` is accepted there: gMode 1 + a live fieldmap.)"""
    why = ("the field's entry script is still running at level 0 (Main_Init/Main_Reinit) -- Main_Reinit could not be "
           "requested")
    assert net_lines("NetSyncDiorama.cs", re.escape(why)), why
    fake = FakeGame(game)
    _dio_bench(fake)
    fake.dio_resume_frames = 10 ** 6                        # the return's entry script outlives this test
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(FIELD)
        g.netsync("selftest", 1)
        _stand(g, fake, 320.0, -410.0, control=hold == "warm")
        g.netsync("dioboot", 4)
        g.wait_frames(fake.dio_swirl_frames)
        g.netsync("dioleave")
        st = g.wait_for(lambda s: s.diorama_last_return == hold and not s.diorama_booted, timeout=4.0,
                        what="the return, its entry script still running")
        assert not st.control and st.diorama_resuming is (hold == "warm")
        st = g.netsync("dioboot", 4)
        assert st.diorama_boot == "cold" and st.diorama_boot_why == why and not st.diorama_primed


def test_the_key_tick_keeps_counting_through_a_battle(game):
    """[ff9mapkit netsync F3.3] NetSyncField.KeyTick is bumped by EVERY EventEngine.ServiceEvents -- the field, a battle
    (battle.cs / HonoluluBattleMain) and the world map (WMScriptDirector) -- so it does not freeze through a battle."""
    assert net_lines("EventEngine.cs", r"NetSyncField\.KeyTick\+\+")
    fake = FakeGame(game)
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(FIELD)
        fake.start_battle(105)
        st = g.wait_for(lambda s: s.battle.get("active") is True, timeout=4.0, what="the battle")
        tick = st.script_key_tick
        st = g.wait_for(lambda s: s.script_key_tick is not None and s.script_key_tick > tick, timeout=4.0,
                        what="the key tick to move inside the battle")
        assert st.battle.get("active") is True
