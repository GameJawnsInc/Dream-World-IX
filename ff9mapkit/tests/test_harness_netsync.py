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
        out.setdefault(lit[0], lit[1])                   # [ff9mapkit netsync R3 s111] the first (stack order) per param
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
                                               r"\|tap-record\|replay\|.*\|bmenu\|bbench\|endbench\)"):
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
    # [ff9mapkit netsync B4] the F3.3 ladder ends at s99; the battle ladder (s100-s105) continues it to the live agent
    # (test_each_battle_patch_adds_its_own_sub_verbs_and_keys_in_order)
    assert prev_verbs == FG.NETSYNC_SUBVERBS_F32 + tuple(v for _p, vs in FG.NETSYNC_F33_CAPS.values() for v in vs)
    assert _agent_subverbs()[:len(prev_verbs)] == prev_verbs == FG.NETSYNC_SUBVERBS[:len(prev_verbs)]
    assert set(Session.NETSYNC_F33_SUBVERBS) == {v for _p, vs in FG.NETSYNC_F33_CAPS.values() for v in vs}
    # each verb's capability accessor is the one that reads the key that patch added
    for verb, (attr, key, _patch, _what) in Session.NETSYNC_F33_SUBVERBS.items():
        cap = next(c for c, (_p, vs) in FG.NETSYNC_F33_CAPS.items() if verb in vs)
        assert key.startswith("netsync.") and key[len("netsync."):] in FG.NETSYNC_CAP_KEYS[cap], (verb, key)
        assert hasattr(State, attr), attr


def test_the_driver_and_the_stand_in_speak_the_bench_hosts_ops():
    """`host <op>`: the driver refuses an op before the step, so its list is a gate -- the engine's, in its order."""
    assert Session.NETSYNC_HOST_OPS == FG.NETSYNC_HOST_OPS == _agent_host_ops()


def _dio_leaves(block: dict, prefix: str = "") -> dict:
    """[ff9mapkit netsync R3] ``netsync.diorama``'s R3 sub-blocks (`intro`, `intro.swirl_clamp`, `live`) as path -> value."""
    out = {}
    for k, v in block.items():
        if isinstance(v, dict) and (prefix or k in ("intro", "live")):
            out.update(_dio_leaves(v, prefix + k + "."))
        elif prefix:
            out[prefix + k] = v
    return out


def test_a_fresh_stand_in_publishes_the_agents_f33_sentinels(game):
    """With no client, every F3.3 key sits at the agent's "nothing" sentinel -- except the two the agent reads off
    process STATICS that exist with no client: `wire` (NetSyncWire.Version, the live constant) and `key_tick`
    (NetSyncField.KeyTick, an Int32 static: 0 before the first key tick). The diorama block's keys are the agent's,
    in its order."""
    nothing, _pinned = _agent_netsync_nothing()
    doc = FakeGame(game)._netsync_doc()
    for keys in FG.NETSYNC_CAP_KEYS.values():
        for key in keys:
            if key not in ("wire", "key_tick", "diorama"):
                assert doc[key] == nothing[key], (key, doc[key], nothing[key])
    # (the diorama block: its F3.3 keys here, [ff9mapkit netsync R3] its R3 sub-blocks below -- four of them LIVE reads)
    assert {k: v for k, v in doc["diorama"].items() if not isinstance(v, dict)} == \
        {k: v for k, v in nothing["diorama"].items() if not isinstance(v, dict)}
    wire = net_lines("NetSyncSocket.cs", r"public const Byte Version = \d+;")
    assert len(wire) == 1, wire
    assert doc["wire"] == int(re.search(r"Version = (\d+);", wire[0]).group(1)) == 14
    assert net_lines("NetSyncField.cs", r"public static Int32 KeyTick;") and doc["key_tick"] == 0
    assert list(doc["diorama"]) == list(nothing["diorama"])
    # [ff9mapkit netsync R3 s111/s112] ...the diorama block's nested R3 keys at the agent's sentinels, except the four the
    # agent reads LIVE off config with no client (each a live read in the agent, never the sentinel)
    live = {"intro.swirl_frames": "HarnessSwirlFrames", "intro.swirl_clamp.ini": "HarnessSwirlClampIni",
            "intro.swirl_clamp.clamp": "HarnessSwirlClamp", "intro.swirl_clamp.src": "HarnessSwirlClampSrc"}
    got, want = _dio_leaves(doc["diorama"]), _dio_leaves(nothing["diorama"])
    assert list(got) == list(want)
    for path, value in want.items():
        if path not in live:
            assert got[path] == value, (path, got[path], value)
    for getter in live.values():
        assert any("Netsync.NetSyncDiorama." + getter in ln for ln in _stack_text("HarnessAgent.cs")), getter


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


# =========================================================================== [ff9mapkit netsync B4/B5] s100-s110
# The battle co-op lane (studies/battle-coop/B4-B5-DESIGN.md, stages 1-11), additive under protocol 5 like F3.3: each stage
# is told by a key's PRESENCE inside the one `netsync.battle` block, so everything below is pinned to the patch that added
# it, NESTED one level deeper than F3.3 -- s100 adds the block (host / peer / menu), s101-s103 grow its sub-objects, s104
# adds `end`, s105 grows it (`exit_mode`, `end_leave`, `declined`), s106-s107 grow `menu` (the content keys; the ready
# mirror's, `content_hits` / `mirror` fixed sub-objects), s108 `host` / `peer` (the manifest), s109 `end` (`replay`), s110
# `host` (`handback`). The Python codec (tools/harness/battlewire.py) is pinned to NetSyncEnd's constants and to the
# engine SelfTest's own rows.

from functools import lru_cache                                        # noqa: E402

from harness import battlewire as BW                                   # noqa: E402

BATTLE_FILES = ("HarnessAgent.cs", "NetSyncBattle.cs", "NetSyncBattle.StockMenu.cs", "NetSyncEnd.cs",
                "NetSyncDiorama.cs", "NetSyncClient.cs", "BattleHUD.Scene.cs")
#: A bench party for the stand-in's own battles: two players who can act (the default units' slot 1 is KO) and one
#: enemy in btl slot 4 (id 0x10) with HP to spare.
BENCH_UNITS = [
    {"slot": 0, "id": 1, "player": True, "name": "Zidane", "hp": 420, "hp_max": 600, "hp_raw": 420, "hp_max_raw": 600,
     "mp": 30, "mp_max": 40, "atb": 0, "atb_max": 6000, "can_act": True, "alive": True, "targetable": True,
     "level": 5, "status": "0"},
    {"slot": 1, "id": 2, "player": True, "name": "Vivi", "hp": 380, "hp_max": 380, "hp_raw": 380, "hp_max_raw": 380,
     "mp": 12, "mp_max": 20, "atb": 0, "atb_max": 6000, "can_act": True, "alive": True, "targetable": True,
     "level": 4, "status": "0"},
    {"slot": 4, "id": 16, "player": False, "name": "Goblin", "hp": 3300, "hp_max": 3300, "hp_raw": 3300,
     "hp_max_raw": 3300, "mp": 0, "mp_max": 0, "atb": 0, "atb_max": 6000, "can_act": True, "alive": True,
     "targetable": True, "level": 3, "status": "0"},
]


def _bench_battle(fake, *, intro: int = 30):
    """An own battle on the stand-in with :data:`BENCH_UNITS` (fresh copies), gauges full every frame, no enemy damage,
    commands that never resolve -- so a Ready bit holds still while a test reads it."""
    fake.atb_gain = 6000
    fake.enemy_hit = 0
    fake.cmd_resolve_frames = 10 ** 6
    fake.battle_intro_frames = intro
    fake.start_battle(67, units=[dict(u) for u in BENCH_UNITS])


@lru_cache(maxsize=None)
def _stack_text(file_name: str) -> tuple:
    """Every line the LIVE stack leaves added in ``file_name`` (net of removals), read once per run."""
    return tuple(net_lines(file_name, r"."))


def _battle_text(fragment: str) -> bool:
    """The live stack's agent (or the netsync file behind a Harness* entry point) carries ``fragment`` in one line."""
    return any(fragment in line for f in BATTLE_FILES for line in _stack_text(f))


def _battle_of(doc: dict) -> dict:
    b = doc.get("battle")
    assert isinstance(b, dict), sorted(doc)
    return b


#: The FIXED sub-objects below host / peer / menu / end (always published whole): their keys are leaves of their own. Every
#: other record (``host.end``, ``peer.end``, ``menu.captured``, s106-s110's ``menu.roster`` / ``bench_roster`` /
#: ``pending`` / ``feed``, ``host.manifest``, ``handback.last``, ``replay.screen`` / ``fp``) may be null: one leaf.
FIXED_SUBOBJECTS = ("end_leave", "declined", "content_hits", "mirror", "handback", "lapse", "replay",
                    # [ff9mapkit netsync R3] s111-s115
                    "cfg", "intro", "wait", "ctl", "start_hold", "released", "guest", "flee")
#: ...and their paths (the accessor table holds a whole-block accessor for each as well as one per key)
BATTLE_CONTAINERS = {"end.end_leave": "s105", "end.declined": "s105", "menu.content_hits": "s106", "menu.mirror": "s107",
                     "end.replay": "s109", "host.handback": "s110", "host.handback.lapse": "s110",
                     "host.cfg": "s111", "host.intro": "s111", "host.wait": "s113", "menu.ctl": "s113",
                     "host.start_hold": "s114", "host.start_hold.released": "s114", "host.start_hold.guest": "s114",
                     "end.flee": "s115"}
#: The records that may be published null (an accessor reads None for them either way).
BATTLE_NULLABLE = ("host.end", "peer.end", "menu.captured", "menu.roster", "menu.bench_roster", "menu.pending",
                   "menu.feed", "host.manifest", "host.handback.last", "end.replay.screen", "end.replay.fp")


def _leaves(block: dict, prefix: str = "") -> dict:
    """``netsync.battle``'s key paths -> values, descending only into the FIXED sub-objects (host / peer / menu / end and
    :data:`FIXED_SUBOBJECTS`); a record that may be null is one leaf."""
    out = {}
    for k, v in block.items():
        path = prefix + k
        if isinstance(v, dict) and (prefix == "" or k in FIXED_SUBOBJECTS):
            out.update(_leaves(v, path + "."))
        else:
            out[path] = v
    return out


def _all_caps_through(cap: str) -> frozenset:
    """The stand-in capability set of the engine at battle capability ``cap`` (every F3.3 cap + the ladder up to it)."""
    names = list(FG.NETSYNC_BATTLE_CAPS)
    return frozenset(FG.NETSYNC_F33_CAPS) | frozenset(names[:names.index(cap) + 1])


def _prefix(level: str) -> list:
    """[ff9mapkit netsync R3] The live stack's patches UP TO AND INCLUDING ``level``, in stack order -- the agent AT that
    patch (net_lines over a prefix nets every rewrite before it)."""
    out = []
    for n in msr.stack():
        if n in msr.DEAD:
            continue
        out.append((msr.PATCHES / n).read_bytes())
        if n.startswith(level + "-"):
            return out
    raise AssertionError(f"no live patch {level}")


def _agent_endbench_ops(patches=None) -> tuple:
    """`endbench`'s "unknown op" list as the stack (or a prefix of it, or one patch that writes it whole) leaves
    NetSyncEnd.cs: the head line (`... unknown op '" + op + "' (victory|...|`) plus its `+ "...|"` continuation(s) and
    the terminal `+ "...)";` one -- s103-s116 wrote one continuation, s117 two."""
    head = net_lines("NetSyncEnd.cs", r"netsync endbench: unknown op '\" \+ op \+ \"' \(victory", patches)
    conts = [_literals(ln)[0] for ln in net_lines("NetSyncEnd.cs", r'^[-+]\s*\+ "[a-z|-]+(\|"|\)";)', patches)]
    assert len(head) == 1, head
    tail = [c for c in conts if c.endswith(")")]
    middle = [c for c in conts if c.endswith("|")]
    assert len(tail) == 1 and len(middle) <= 1, conts
    text = _literals(head[0])[-1] + "".join(middle) + tail[0]
    m = re.match(r"' \(([a-z|-]+)\)$", text)
    assert m, text
    return tuple(m.group(1).split("|"))


#: The patches that rewrite `endbench`'s "unknown op" list (s103 wrote it; s106, s107, s110-s115 leave it alone;
#: [ff9mapkit netsync R3] s116 adds `fleegil`, s117 rewrites it whole: `phase-defeat`, `kill`).
ENDBENCH_OP_PATCHES = ("s103", "s104", "s105", "s108", "s109", "s116", "s117")


def _endbench_ops_at(level: str) -> tuple:
    """`endbench`'s ops as the agent at patch ``level`` prints them (the stack up to it; () before s103)."""
    return _agent_endbench_ops(_prefix(level)) if int(level[1:]) >= 103 else ()


def _agent_bbench_unknown(patches=None) -> str:
    """`bbench`'s "unknown op" list as the stack (or one patch) leaves NetSyncBattle.StockMenu.cs, verbatim."""
    lines = net_lines("NetSyncBattle.StockMenu.cs", r"netsync bbench: unknown op '", patches)
    assert len(lines) == 1, lines
    m = re.search(r"\(([^()]+)\)\";", lines[0])
    assert m, lines[0]
    return m.group(1)


def _caps_at(level: str) -> frozenset:
    """The stand-in capability set of the engine at patch ``level`` (s99 = no battle lane)."""
    return frozenset(FG.NETSYNC_F33_CAPS) | frozenset(
        c for c, (p, _vs) in FG.NETSYNC_BATTLE_CAPS.items() if int(p[1:]) <= int(level[1:]))


def _at(block: dict, path: str):
    node = block
    for part in path.split("."):
        node = node[part]
    return node


def _leaves_paths(battle: dict) -> set:
    """Every fixed sub-object path present in a `netsync.battle` block (BATTLE_CONTAINERS that resolve)."""
    out = set()
    for path in BATTLE_CONTAINERS:
        try:
            if isinstance(_at(battle, path), dict):
                out.add(path)
        except (KeyError, TypeError):
            pass
    return out


def _key_is_the_patchs(key: str, cap: str) -> bool:
    """[ff9mapkit netsync R3] A capability key (dotted from `netsync.`) is one the capability ``cap`` ADDED: a
    `netsync.battle.<sub>.<leaf>` sub-level key, a key inside an older fixed sub-object (FG.NETSYNC_BATTLE_NESTED_KEYS),
    a whole new block below one of those, or a `netsync.diorama` key / nested key."""
    if key.startswith("netsync.diorama."):
        rest = key[len("netsync.diorama."):].split(".")
        if len(rest) == 1:
            return rest[0] in FG.NETSYNC_DIORAMA_CAP_KEYS.get(cap, ())
        return rest[-1] in FG.NETSYNC_DIORAMA_NESTED_KEYS.get(cap, {}).get(".".join(rest[:-1]), ())
    path = key[len("netsync.battle."):]
    sub, leaf = path.split(".", 1)
    if leaf in FG.NETSYNC_BATTLE_CAP_KEYS[cap].get(sub, ()):
        return True
    parent, _, last = path.rpartition(".")
    return last in FG.NETSYNC_BATTLE_NESTED_KEYS.get(cap, {}).get(parent, ())


def test_each_battle_patch_adds_its_own_sub_verbs_and_keys_in_order():
    """THE BATTLE LADDER, patch by patch: each of s100-s110's agent prints the previous sub-verb list with that stage's
    verbs ADDED and the earlier ones' order kept (s100-s103 append; s106 INSERTS `bbench` before `endbench` -- the
    stand-in's FG.netsync_subverbs; the others add none and leave the line alone), and its catch line carries the
    previous `netsync` keys plus exactly that stage's NESTED keys, in the agent's order -- s100 the one top-level
    `battle`, every later stage keys INSIDE it. The stand-in's tables (FG.NETSYNC_BATTLE_CAPS /
    NETSYNC_BATTLE_CAP_KEYS) are those diffs."""
    prev_verbs, prev_doc = _subverbs_in("s99"), _catch_doc_in("s99")
    assert "battle" not in prev_doc
    for cap, (patch, verbs) in FG.NETSYNC_BATTLE_CAPS.items():
        lines = net_lines("HarnessAgent.cs", r"netsync: unknown sub-verb", [_patch_bytes(patch)])
        verbs_now = _subverbs_in(patch) if lines else prev_verbs
        assert verbs_now == FG.netsync_subverbs(_caps_at(patch)), (patch, verbs_now)
        assert set(verbs_now) - set(prev_verbs) == set(verbs), (patch, verbs_now)
        assert [v for v in verbs_now if v in prev_verbs] == list(prev_verbs), (patch, verbs_now)
        doc_now = _catch_doc_in(patch)
        new_top = [k for k in doc_now if k not in prev_doc]
        assert new_top == (["battle"] if cap == "gates" else []), (patch, new_top)
        was, now = prev_doc.get("battle", {}), _battle_of(doc_now)
        added = {}
        for sub, keys in now.items():
            fresh = [k for k in keys if k not in was.get(sub, {})]
            if fresh:
                added[sub] = tuple(fresh)
        assert added == FG.NETSYNC_BATTLE_CAP_KEYS[cap], (patch, added)
        for sub, keys in was.items():                   # nothing the previous stage published is lost
            assert set(keys) <= set(now[sub]), (patch, sub, set(keys) - set(now[sub]))
        for verb in verbs:
            assert Session.NETSYNC_BATTLE_SUBVERBS[verb][2] == patch, verb
        # [ff9mapkit netsync R3] the keys added INSIDE an older fixed sub-object, and to / inside `netsync.diorama`
        nested = {}
        for path in [c for c in BATTLE_CONTAINERS if c in _leaves_paths(was)]:
            node_w, node_n = _at(was, path), _at(now, path)
            fresh = tuple(k for k in node_n if k not in node_w)
            if fresh:
                nested[path] = fresh
        assert nested == FG.NETSYNC_BATTLE_NESTED_KEYS.get(cap, {}), (patch, nested)
        dio_w, dio_n = prev_doc["diorama"], doc_now["diorama"]
        assert tuple(k for k in dio_n if k not in dio_w) == FG.NETSYNC_DIORAMA_CAP_KEYS.get(cap, ()), patch
        dio_nested = {k: tuple(x for x in dio_n[k] if x not in dio_w[k]) for k in dio_w
                      if isinstance(dio_w[k], dict) and set(dio_n[k]) - set(dio_w[k])}
        assert dio_nested == FG.NETSYNC_DIORAMA_NESTED_KEYS.get(cap, {}), (patch, dio_nested)
        prev_verbs, prev_doc = verbs_now, doc_now
    assert prev_verbs == _agent_subverbs() == FG.NETSYNC_SUBVERBS == Session.NETSYNC_SUBVERBS
    battle = _battle_of(prev_doc)
    end = battle["end"]
    assert tuple(end["end_leave"]) == FG.NETSYNC_BATTLE_END_LEAVE_KEYS
    assert tuple(end["declined"]) == FG.NETSYNC_BATTLE_DECLINED_KEYS
    # [ff9mapkit netsync B4/B5] s106-s110's fixed sub-objects, in the agent's order
    assert tuple(battle["menu"]["content_hits"]) == FG.NETSYNC_BATTLE_CONTENT_HIT_KEYS == BW.CONTENT_NAMES
    assert tuple(battle["menu"]["mirror"]) == FG.NETSYNC_BATTLE_MIRROR_KEYS
    assert tuple(end["replay"]) == FG.NETSYNC_BATTLE_REPLAY_KEYS
    assert tuple(battle["host"]["handback"]) == FG.NETSYNC_BATTLE_HANDBACK_KEYS
    assert tuple(battle["host"]["handback"]["lapse"]) == FG.NETSYNC_BATTLE_LAPSE_KEYS
    # [ff9mapkit netsync R3] s111-s117's fixed sub-objects, in the agent's order
    host = battle["host"]
    assert tuple(host["cfg"]) == FG.NETSYNC_BATTLE_CFG_KEYS and tuple(host["intro"]) == FG.NETSYNC_BATTLE_HOST_INTRO_KEYS
    assert tuple(host["wait"]) == FG.NETSYNC_BATTLE_WAIT_KEYS and tuple(battle["menu"]["ctl"]) == FG.NETSYNC_BATTLE_CTL_KEYS
    assert tuple(host["start_hold"]) == FG.NETSYNC_BATTLE_START_HOLD_KEYS
    assert tuple(host["start_hold"]["released"]) == FG.NETSYNC_BATTLE_RELEASED_KEYS == tuple(BW.HOLD_RELEASED_KEYS.values())
    assert tuple(host["start_hold"]["guest"]) == FG.NETSYNC_BATTLE_HOLD_GUEST_KEYS
    assert tuple(end["flee"]) == FG.NETSYNC_BATTLE_FLEE_KEYS
    dio = prev_doc["diorama"]
    assert tuple(dio["intro"]) == FG.NETSYNC_DIORAMA_INTRO_KEYS
    assert tuple(dio["intro"]["swirl_clamp"]) == FG.NETSYNC_DIORAMA_SWIRL_KEYS
    assert tuple(dio["live"]) == FG.NETSYNC_DIORAMA_LIVE_KEYS
    assert set(Session.NETSYNC_BATTLE_SUBVERBS) == {v for _p, vs in FG.NETSYNC_BATTLE_CAPS.values() for v in vs}


def test_each_battle_verbs_capability_key_is_one_its_patch_added():
    """The driver tells each B4/B5 verb's engine apart by ONE key: it must be a key THAT patch added (s100: the block
    itself), read by the State accessor it names -- and an accessor that reads the key, not a neighbour."""
    for verb, (attr, key, patch, _what) in Session.NETSYNC_BATTLE_SUBVERBS.items():
        cap = next(c for c, (p, _vs) in FG.NETSYNC_BATTLE_CAPS.items() if p == patch)
        assert key.startswith("netsync.battle"), key
        path = key[len("netsync.battle."):] if key != "netsync.battle" else ""
        if path:
            sub, leaf = path.split(".", 1)
            assert leaf in FG.NETSYNC_BATTLE_CAP_KEYS[cap][sub], (verb, key)
        else:
            assert cap == "gates", verb
        assert isinstance(getattr(State, attr), property), attr
        full = {"frame": 1, "netsync": {"enabled": True, "battle": {"host": {}, "peer": {}, "menu": {}, "end": {}}}}
        assert getattr(State(full), attr) is (cap == "gates"), (verb, attr)  # an empty block has only s100's key
    names = list(FG.NETSYNC_BATTLE_CAPS)
    for op, (attr, key, patch, _what) in Session.NETSYNC_ENDBENCH_OP_CAPS.items():
        cap = next(c for c, (p, _vs) in FG.NETSYNC_BATTLE_CAPS.items() if p == patch)
        assert _key_is_the_patchs(key, cap), (op, key)
        assert isinstance(getattr(State, attr), property), attr
        assert op in FG.endbench_ops(_all_caps_through(cap)) and op not in FG.endbench_ops(
            _all_caps_through(names[names.index(cap) - 1])), op
        assert op in _endbench_ops_at(patch) and op not in _endbench_ops_at(f"s{int(patch[1:]) - 1}"), op
    # [ff9mapkit netsync B4] the `bbench` feed ops (s107) and the `bench` named ops (s110; [ff9mapkit netsync R3] s111-s114),
    # told the same way
    for table, ops_of in ((Session.NETSYNC_BBENCH_OP_CAPS, FG.bbench_ops), (Session.NETSYNC_BENCH_OPS, None)):
        for op, (attr, key, patch, _what) in table.items():
            cap = next(c for c, (p, _vs) in FG.NETSYNC_BATTLE_CAPS.items() if p == patch)
            assert _key_is_the_patchs(key, cap), (op, key)
            assert isinstance(getattr(State, attr), property), attr
            if ops_of is not None:
                assert op in ops_of(_all_caps_through(cap)) and op not in ops_of(
                    _all_caps_through(names[names.index(cap) - 1])), op
    assert set(Session.NETSYNC_BBENCH_OP_CAPS) == set(Session.NETSYNC_BBENCH_OPS) - set(FG.NETSYNC_BBENCH_OPS_S106)
    # [ff9mapkit netsync R3 s115] a later VALUE of an older op (`endbench guest hold|nor9b`), its old answer the engine's
    for (op, value), (attr, key, patch, _what, old) in Session.NETSYNC_ENDBENCH_VALUE_CAPS.items():
        cap = next(c for c, (p, _vs) in FG.NETSYNC_BATTLE_CAPS.items() if p == patch)
        assert _key_is_the_patchs(key, cap) and isinstance(getattr(State, attr), property), (op, value, key)
        prior = names[names.index(cap) - 1]
        assert any(old in _literals(ln) for ln in net_lines("NetSyncEnd.cs", re.escape(old), _prefix(f"s{int(patch[1:]) - 1}")))
        assert not _battle_text(old + '"'), old                    # gone from the live stack (it grew `|hold|nor9b`)
        assert prior in FG.NETSYNC_BATTLE_CAPS


def test_the_bmenu_and_endbench_ops_are_the_agents_patch_by_patch():
    """`bmenu <op>`, `bbench <op>` and `endbench <op>` are refused by the driver before the step, so their lists are
    gates: the engine's, in its order, at every patch -- s104 inserts `guest`, s105 `exit` (after `host`), s108 `manifest`
    (after `afterevent`), s109 `fieldsong` before it and `replay|quit` after `exit`; `bbench` prints s106's two ops with a
    note naming stage 8's, then s107's ten."""
    bmenu = net_lines("NetSyncBattle.StockMenu.cs", r"netsync bmenu: unknown op '")
    assert len(bmenu) == 1, bmenu
    m = re.search(r"\(([a-z|]+)\)\";", bmenu[0])
    assert m and tuple(m.group(1).split("|")) == Session.NETSYNC_BMENU_OPS == FG.NETSYNC_BMENU_OPS, bmenu
    assert _agent_endbench_ops() == Session.NETSYNC_ENDBENCH_OPS == FG.endbench_ops(_all_caps_through("defeat"))
    assert _agent_endbench_ops([_patch_bytes("s103")]) == FG.NETSYNC_ENDBENCH_OPS_S103 \
        == FG.endbench_ops(_all_caps_through("endblock"))
    for level, cap in (("s104", "present"), ("s105", "exit"), ("s108", "manifest"), ("s109", "replay"),
                       ("s116", "fleegil"), ("s117", "defeat")):
        assert _agent_endbench_ops(_prefix(level)) == FG.endbench_ops(_all_caps_through(cap)), level
    for level in ("s106", "s107", "s110", "s111", "s112", "s113", "s114", "s115"):   # these leave the list alone
        assert not net_lines("NetSyncEnd.cs", r'netsync endbench: unknown op|^[-+]\s*\+ "[a-z|-]+(\|"|\)";)',
                             [_patch_bytes(level)]), level
        assert _endbench_ops_at(level) == _endbench_ops_at(f"s{int(level[1:]) - 1}"), level
    # `manifest` is LISTED from s108 -- nothing is unlisted any more; before it the engine knew it and refused it (the
    # driver quotes that answer when it refuses `endbench manifest` on such an engine)
    assert Session.NETSYNC_ENDBENCH_UNLISTED == () and "manifest" in Session.NETSYNC_ENDBENCH_OPS
    old = Session.NETSYNC_ENDBENCH_OLD_ANSWERS["manifest"]
    assert any(old in _literals(ln) for ln in net_lines("NetSyncEnd.cs", r"the result manifest is stage 9",
                                                        [_patch_bytes("s103")])), old
    assert not _battle_text("the result manifest is stage 9")      # gone from the live stack
    # `bbench` (NetSyncBattle.StockMenu.HarnessStockBench): s106's note, then s107's list
    assert _agent_bbench_unknown([_patch_bytes("s106")]) == FG.NETSYNC_BBENCH_UNKNOWN_S106 \
        == Session.NETSYNC_BBENCH_S106_LIST
    assert tuple(_agent_bbench_unknown().split("|")) == Session.NETSYNC_BBENCH_OPS == FG.NETSYNC_BBENCH_OPS \
        == FG.bbench_ops(_all_caps_through("mirror"))
    assert FG.bbench_ops(_all_caps_through("content")) == FG.NETSYNC_BBENCH_OPS_S106 \
        == tuple(FG.NETSYNC_BBENCH_UNKNOWN_S106.split(";")[0].split("|"))


def test_every_battle_key_has_an_accessor_and_every_accessor_a_key():
    """Every key the live agent publishes under `netsync.battle` has a State accessor (a key read raw reads absence as a
    KeyError or a default -- the "nothing" this module refuses), and every accessor's path is a key the agent publishes;
    each accessor's reading matches its sentinel's type (null = a string or a record)."""
    nothing, _ = _agent_netsync_nothing()
    leaves = _leaves(_battle_of(nothing))
    table = State.NETSYNC_BATTLE_ACCESSORS
    assert set(leaves) <= set(table), sorted(set(leaves) - set(table))
    containers = set(BATTLE_CONTAINERS)
    assert set(table) - set(leaves) == containers, sorted(set(table) - set(leaves))

    def at(path):
        node = _battle_of(nothing)
        for part in path.split("."):
            node = node[part]
        return node

    for path, name in table.items():
        prop = getattr(State, name)
        got = prop.fget(State({"frame": 1, "netsync": nothing}))
        sentinel = leaves[path] if path in leaves else at(path)
        if sentinel is None:
            assert got in ("", None), (path, got)            # a null string reads "", a null record None
        elif isinstance(sentinel, (dict, list)):
            assert got == sentinel and got is not sentinel, (path, got)
        else:
            assert got == sentinel and type(got) is type(sentinel), (path, got, sentinel)


def test_a_fresh_stand_in_publishes_the_agents_battle_sentinels(game):
    """With no client, the stand-in's `netsync.battle` IS the agent's catch-line block -- same keys, same order, same
    sentinels -- except the six values the agent reads LIVE off process statics that exist with no client: the three
    calibration levers' names (`on` at rest; the catch line's null is "the block failed to build") and the engine's
    music id, raw btl_flag and battle-achievement counter."""
    nothing, _ = _agent_netsync_nothing()
    want = _battle_of(nothing)
    got = _battle_of(FakeGame(game)._netsync_doc())
    live = {"host.end_mode": "HarnessHostMode", "end.guest_mode": "HarnessGuestMode", "end.exit_mode": "HarnessExitMode",
            "end.music": "HarnessMusicId", "end.btl_flag": "HarnessBtlFlag", "end.ach_enemy_no": "HarnessAchEnemyNo",
            # [ff9mapkit netsync B4/B5] s107-s109: the levers' names and the ownership read off statics / the ini, and the
            # write guard's fingerprint (computed every tick, off the save itself)
            "menu.knob": "HarnessKnob", "menu.why": "HarnessStockWhy", "host.manifest_mode": "HarnessManifestMode",
            "end.replay.mode": "HarnessReplayMode", "end.replay.fp": "NetFingerprint",
            # [ff9mapkit netsync R3] s111's cfg reads, s114's cap and state ("idle" with no own battle), s115's party gil
            "host.cfg.atb": "HarnessCfgAtb", "host.cfg.skip_btl_camera": "HarnessCfgSkipCam",
            "host.cfg.speed": "HarnessCfgSpeed", "host.cfg.swirl_frames": "HarnessSwirlFrames",
            "host.start_hold.cap_ms": "HarnessStartHoldCapMs", "host.start_hold.state": "HarnessStartHoldState",
            "end.flee.gil_now": "HarnessGilNow"}
    for sub in want:
        assert list(got[sub]) == list(want[sub]), (sub, list(got[sub]), list(want[sub]))
    for path in BATTLE_CONTAINERS:                       # the fixed sub-objects keep the agent's key order too
        node_w, node_g = want, got
        for part in path.split("."):
            node_w, node_g = node_w[part], node_g[part]
        assert list(node_g) == list(node_w), (path, list(node_g), list(node_w))
    for path, value in _leaves(want).items():
        if path in live:
            continue
        assert _leaves(got)[path] == value, (path, _leaves(got)[path], value)
    for path, getter in live.items():                    # ...each one a live read in the agent, never the sentinel
        assert any(("Netsync.NetSync" in ln or "BattleResultUI." in ln) and getter in ln
                   for ln in _stack_text("HarnessAgent.cs")), getter
    assert (_leaves(got)["host.start_hold.state"], _leaves(got)["host.start_hold.cap_ms"]) == ("idle", BW.START_HOLD_MS)
    assert {k: _leaves(got)[k] for k in ("host.end_mode", "end.guest_mode", "end.exit_mode", "host.manifest_mode",
                                         "end.replay.mode")} == \
        {"host.end_mode": "on", "end.guest_mode": "on", "end.exit_mode": "on", "host.manifest_mode": "on",
         "end.replay.mode": "on"}
    # with no client: the ini's GuestStockMenu (default 1), no diorama to own, and a fingerprint of the save
    assert _leaves(got)["menu.knob"] == 1 and _leaves(got)["menu.why"] == "no live battle diorama"
    assert _battle_text('why = "no live battle diorama";')
    fp = _leaves(got)["end.replay.fp"]
    assert list(fp) == ["hash", "gil", "items", "item_sum", "players", "level_sum", "exp_sum", "pa_sum", "cards",
                        "abilities", "passive"] and re.fullmatch(r"0x[0-9A-F]{16}", fp["hash"])
    for k in list(fp)[1:]:                               # each a field of the agent's own NetFp, in this order
        assert net_lines("HarnessAgent.cs", rf'Num\(sb, "{k}", p\.'), k


BATTLE_LEVELS = ["s99", "s100", "s101", "s102", "s103", "s104", "s105", "s106", "s107", "s108", "s109", "s110",
                 "s111", "s112", "s113", "s114", "s115", "s116", "s117"]


@pytest.mark.parametrize("level", BATTLE_LEVELS)
def test_an_older_battle_stand_in_is_that_patchs_agent(game, level):
    """A stand-in at battle capability level sNNN is exactly that patch's agent: its keys (top-level and NESTED, the
    fixed sub-objects' included) are that patch's catch line, a later verb is an "unknown sub-verb" listing that patch's
    verbs, and `endbench`'s / `bbench`'s ops are that patch's."""
    fake = FakeGame(game)
    names = list(FG.NETSYNC_BATTLE_CAPS)
    have = [c for c in names if int(FG.NETSYNC_BATTLE_CAPS[c][0][1:]) <= int(level[1:])]
    fake.netsync_caps = frozenset(FG.NETSYNC_F33_CAPS) | frozenset(have)
    doc, want = fake._netsync_doc(), _catch_doc_in(level)
    assert set(doc) == set(want), set(doc) ^ set(want)
    assert set(_dio_leaves(doc["diorama"])) == set(_dio_leaves(want["diorama"])), level   # [ff9mapkit netsync R3]
    assert list(doc["diorama"]) == list(want["diorama"]), level
    if "battle" in want:
        assert set(_leaves(_battle_of(doc))) == set(_leaves(_battle_of(want))), \
            set(_leaves(_battle_of(doc))) ^ set(_leaves(_battle_of(want)))
        for sub in _battle_of(want):                     # ...in the agent's order
            assert list(_battle_of(doc)[sub]) == list(_battle_of(want)[sub]), (level, sub)
    lines = [p for p in ("s100", "s101", "s102", "s103", "s106") if int(p[1:]) <= int(level[1:])]
    known = "|".join(_subverbs_in(lines[-1] if lines else "s99"))
    assert fake._netsync_subverbs() == tuple(known.split("|"))
    for cap in names[len(have):]:
        for verb in FG.NETSYNC_BATTLE_CAPS[cap][1]:
            with pytest.raises(RuntimeError) as err:
                fake._netsync([verb, "1"])
            assert str(err.value) == f"netsync: unknown sub-verb '{verb}' ({known})"
    if "endblock" in have:
        fake._netsync(["selftest", "1"])
        with pytest.raises(RuntimeError) as err:
            fake._netsync(["endbench", "bogus"])
        assert str(err.value) == "netsync endbench: unknown op 'bogus' (" + "|".join(_endbench_ops_at(level)) + ")"
    if "content" in have:
        with pytest.raises(RuntimeError) as err:
            fake._netsync(["bbench", "bogus"])
        at = "s107" if "mirror" in have else "s106"
        assert str(err.value) == f"netsync bbench: unknown op 'bogus' ({_agent_bbench_unknown([_patch_bytes(at)])})"


# (fragment the agent says -- ONE C# literal of the stack, or a piece of one -- how to make the stand-in say it)
def _selftest(f):
    f._netsync(["selftest", "1"])
    return f


def _bcmd_flood(f):
    _selftest(f)
    for _ in range(16):
        f._netsync(["bcmd", "01", "01", "00", "00", "00", "00", "10", "00", "00"])
    f._netsync(["bcmd", "01"])


def _dio_fake(f, *, units=None):
    """The stand-in (no loop running) in a live selftest diorama in its steady command phase -- by hand: `dioboot` from a
    field, the opening camera skipped, the HUD's command menu enabled."""
    f.ui_state, f.field_id, f.control = "FieldHUD", FIELD, True
    f.battle_intro_frames = 0
    if units is not None:
        f.dio_units = units
    _selftest(f)._netsync(["dioboot", "67"])
    f.commands_enabled = True
    return f


def _fed(f):
    """...and the s107 bench feed started (wire slot 0 offered)."""
    _dio_fake(f)._netsync(["bbench", "start", "1"])
    return f


def _quit_while_loading(f):
    """`endbench quit on` while the replay's screen is Loading (BattleResultUI refuses Quit then) -- the screen poked."""
    _selftest(f)
    f.ui_state = "BattleResult"
    f._nb.screen = {"loading": True, "state": BW.RES_START_GIL}
    f._netsync(["endbench", "quit", "on"])


BATTLE_REFUSALS = [
    ("netsync guestslots: needs the selftest role (netsync selftest 1)", lambda f: f._netsync(["guestslots", "2"])),
    ("netsync bcmd: needs the selftest role (netsync selftest 1)", lambda f: f._netsync(["bcmd", "01"])),
    ("netsync bcmd: needs 1..64 bytes of hex (a v1 command frame is 9: ver slot action menu idLo idHi maskLo maskHi "
     "cursor)", lambda f: _selftest(f)._netsync(["bcmd", "00" * 65])),
    ("netsync bcmd: 16 frames already wait on the loopback (no own battle is draining them)", _bcmd_flood),
    ("netsync hostgates: needs the selftest role (netsync selftest 1)", lambda f: f._netsync(["hostgates", "0"])),
    ("netsync containment: needs the selftest role (netsync selftest 1)", lambda f: f._netsync(["containment", "0"])),
    ("netsync bctl: needs the selftest role (netsync selftest 1)", lambda f: f._netsync(["bctl", "00", "00"])),
    ("netsync bctl: needs 1..64 bytes of hex (a control frame is 2: 00 <menu 0 shut|1 legacy|2 root|3 deep>, ",
     lambda f: _selftest(f)._netsync(["bctl", "00" * 65])),
    ("or 5 with the start-hold trailer: ... 01 <host battle nonce> <boot 0-4>)",          # [ff9mapkit netsync R3 s114]
     lambda f: _selftest(f)._netsync(["bctl", "00" * 65])),
    ("netsync bmenu: needs the selftest role (netsync selftest 1)", lambda f: f._netsync(["bmenu", "closeall"])),
    ("netsync bmenu: unknown op '", lambda f: _selftest(f)._netsync(["bmenu", "bogus"])),
    ("' (open|close|closeall|capture|mainmenu)", lambda f: _selftest(f)._netsync(["bmenu"])),
    ("needs a live diorama (netsync dioboot <scene>, then wait for battle.turn.enabled)",
     lambda f: _selftest(f)._netsync(["bmenu", "open", "0"])),
    ("netsync bmenu close: needs a live diorama", lambda f: _selftest(f)._netsync(["bmenu", "close", "0"])),
    ("netsync bmenu mainmenu: needs a live diorama (a real battle's main menu is stock and is never probed)",
     lambda f: _selftest(f)._netsync(["bmenu", "mainmenu"])),
    ("netsync endbench: needs the selftest role (netsync selftest 1)", lambda f: f._netsync(["endbench", "victory"])),
    ("netsync endbench: unknown op '", lambda f: _selftest(f)._netsync(["endbench", "bogus"])),
    ("' (victory|pending|nopose|other|defeat|phase-defeat|escape|event|", lambda f: _selftest(f)._netsync(["endbench"])),
    ("fight|ui|state|overflow|afterevent|fieldsong|manifest|fleegil|kill|cmd|host|guest|exit|replay|quit|",
     lambda f: _selftest(f)._netsync(["endbench"])),
    ("selftest|clear)", lambda f: _selftest(f)._netsync(["endbench"])),
    ("netsync endbench other: needs a btl_result 0-255 (5 interruption, 7 enemy flee, ...)",
     lambda f: _selftest(f)._netsync(["endbench", "other", "300"])),
    ("netsync endbench ui: needs 0 (battle/other), 1 (BattleResult), 2 (GameOver) or 3 (Title)",
     lambda f: _selftest(f)._netsync(["endbench", "ui", "4"])),
    ("netsync endbench state: needs a ResultState 0-8 (0 Start .. 6 End, 7 Hide, 8 None) [loading]",
     lambda f: _selftest(f)._netsync(["endbench", "state", "9"])),
    (": needs 0|1", lambda f: _selftest(f)._netsync(["endbench", "overflow", "2"])),
    ("netsync endbench cmd: needs 1..64 bytes of hex (a v1 command frame is 9)",
     lambda f: _selftest(f)._netsync(["endbench", "cmd", "00" * 65])),
    ("netsync endbench host: needs on|cadence|off", lambda f: _selftest(f)._netsync(["endbench", "host", "x"])),
    ("netsync endbench guest: needs on|off|settle|hold|nor9b", lambda f: _selftest(f)._netsync(["endbench", "guest", "x"])),
    ("netsync endbench exit: needs on|off", lambda f: _selftest(f)._netsync(["endbench", "exit"])),
    # [ff9mapkit netsync B5] s108 / s109
    ("netsync endbench manifest: needs 0 (none), 1 (two-marker), 2 (escape with gil), 3 (foreign charIds) or `host on|off`",
     lambda f: _selftest(f)._netsync(["endbench", "manifest", "4"])),
    ("netsync endbench manifest host: needs on|off", lambda f: _selftest(f)._netsync(["endbench", "manifest", "host",
                                                                                     "maybe"])),
    ("netsync endbench manifest ", lambda f: (_selftest(f), setattr(f, "save_party", [None] * 4),
                                              f._netsync(["endbench", "manifest", "1"]))),
    ("no seated party member to build rows from", lambda f: (_selftest(f), setattr(f, "save_party", [None] * 4),
                                                             f._netsync(["endbench", "manifest", "1"]))),
    ("netsync endbench replay: needs on|off|local", lambda f: _selftest(f)._netsync(["endbench", "replay", "maybe"])),
    ("netsync endbench quit: needs on|off", lambda f: _selftest(f)._netsync(["endbench", "quit"])),
    ("netsync endbench quit on: the quit prompt did not open (the UI is Loading, or the current scene refuses ",
     lambda f: _quit_while_loading(f)),
    ("Quit -- BattleResultUI refuses it at Hide and while Loading)", lambda f: _quit_while_loading(f)),
    # [ff9mapkit netsync B4] s106 / s107 -- `bbench`
    ("netsync bbench: needs the selftest role (netsync selftest 1)", lambda f: f._netsync(["bbench", "content", "on"])),
    ("netsync bbench: unknown op '", lambda f: _selftest(f)._netsync(["bbench", "bogus"])),
    ("netsync bbench content: on|off|<mask 0-127> (the hooks left ON: 1 command, 2 grey, 4 ability, 8 bag, 16 count, ",
     lambda f: _selftest(f)._netsync(["bbench", "content", "128"])),
    ("netsync bbench roster: needs hex bytes (a v1 type-4 roster), `auto <L> [dbl] [grey] [mp=<n>] [count=<n>]` or "
     "`clear`", lambda f: _selftest(f)._netsync(["bbench", "roster"])),
    ("netsync bbench roster: the REAL ParseRoster refused those ", lambda f: _selftest(f)._netsync(["bbench", "roster",
                                                                                                    "02", "00"])),
    (" bytes (not a v1 roster -- the log names the fault)", lambda f: _selftest(f)._netsync(["bbench", "roster", "01"])),
    ("netsync bbench roster auto: needs a local party slot 0-3", lambda f: _selftest(f)._netsync(["bbench", "roster",
                                                                                                  "auto", "4"])),
    ("netsync bbench roster auto: unknown option '", lambda f: _selftest(f)._netsync(["bbench", "roster", "auto", "0",
                                                                                      "triple"])),
    ("' (dbl | grey | mp=<0-255> | count=<1-255>)", lambda f: _selftest(f)._netsync(["bbench", "roster", "auto", "0",
                                                                                     "mp=300"])),
    ("netsync bbench roster auto: ", lambda f: _dio_fake(f)._netsync(["bbench", "roster", "auto", "2"])),
    (" holds no party member in this battle", lambda f: _dio_fake(f)._netsync(["bbench", "roster", "auto", "2"])),
    ("netsync bbench roster auto: ", lambda f: _selftest(f)._netsync(["bbench", "roster", "auto", "0"])),
    ("netsync bbench start: needs the host's guest-slot offer, a WIRE slot mask 1-15 (decimal or 0x hex)",
     lambda f: _selftest(f)._netsync(["bbench", "start", "0"])),
    ("netsync bbench start: needs a live diorama (netsync dioboot <scene>)",
     lambda f: _selftest(f)._netsync(["bbench", "start", "1"])),
    ("netsync bbench knob: 0|1|ini (force GuestStockMenu off/on for this process, or back to the ini's value)",
     lambda f: _selftest(f)._netsync(["bbench", "knob", "2"])),
    (": no bench feed is running (`bbench start <mask>` inside a live diorama first)",
     lambda f: _selftest(f)._netsync(["bbench", "ready", "1"])),
    ("netsync bbench ready: needs a WIRE slot mask 0-15 (decimal or 0x hex)",
     lambda f: _fed(f)._netsync(["bbench", "ready", "16"])),
    ("netsync bbench caps: needs the header flags byte 0-255 (bit 1 = a command-phase-gated host)",
     lambda f: _fed(f)._netsync(["bbench", "caps", "256"])),
    ("netsync bbench mode: accept|refuse|freeze", lambda f: _fed(f)._netsync(["bbench", "mode", "ignore"])),
    ("netsync bbench freeze: 1|0", lambda f: _fed(f)._netsync(["bbench", "freeze", "2"])),
    ("netsync bbench unmap: a WIRE slot 0-3, or none", lambda f: _fed(f)._netsync(["bbench", "unmap", "4"])),
    # [ff9mapkit netsync B4] s110 -- the `bench` named ops
    ("netsync bench: needs the selftest role (netsync selftest 1)", lambda f: f._netsync(["bench", "lapse", "hold"])),
]


@pytest.mark.parametrize("fragment,provoke", BATTLE_REFUSALS, ids=[r[0][:40] for r in BATTLE_REFUSALS])
def test_the_stand_in_refuses_the_battle_verbs_in_the_agents_words(game, fragment, provoke):
    """Every B4/B5 gate the stand-in models refuses with the agent's own words -- the text a scenario's refusal match and
    a live run's error latch both carry."""
    assert _battle_text(fragment), f"the live stack no longer says {fragment!r}"
    fake = FakeGame(game)
    fake.field_id = FIELD
    with pytest.raises(RuntimeError) as err:
        provoke(fake)
    assert fragment in str(err.value), str(err.value)


BATTLE_ARGUMENT_REFUSALS = [
    ("netsync guestslots", None, lambda f: f._netsync(["guestslots", "16"])),
    ("netsync guestslots", None, lambda f: f._netsync(["guestslots", "0x1g"])),
    ("netsync guestslots", None, lambda f: f._netsync(["guestslots"])),
    ("netsync bcmd", None, lambda f: f._netsync(["bcmd", "0"])),                   # an odd digit count
    ("netsync bcmd", None, lambda f: f._netsync(["bcmd", "zz"])),
    ("netsync bctl", None, lambda f: f._netsync(["bctl"])),
    ("netsync bmenu capture", None, lambda f: f._netsync(["bmenu", "capture", "maybe"])),
    ("netsync bmenu ", "netsync bmenu open", lambda f: f._netsync(["bmenu", "open", "4"])),
    ("netsync bmenu ", "netsync bmenu close", lambda f: f._netsync(["bmenu", "close"])),
    ("netsync endbench ", "netsync endbench ui", lambda f: f._netsync(["endbench", "ui"])),
    ("netsync endbench ", "netsync endbench other", lambda f: f._netsync(["endbench", "other", "-1"])),
    ("netsync endbench state", None, lambda f: f._netsync(["endbench", "state", "2", "fading"])),
    ("netsync endbench cmd", None, lambda f: f._netsync(["endbench", "cmd", "0x0"])),
    # [ff9mapkit netsync B4/B5] s106-s110
    ("netsync bbench roster", None, lambda f: f._netsync(["bbench", "roster", "zz"])),
    ("netsync bbench roster", None, lambda f: f._netsync(["bbench", "roster", "0"])),        # an odd digit count
    ("netsync endbench manifest", None, lambda f: f._netsync(["endbench", "manifest", "x"])),
    ("netsync endbench manifest", None, lambda f: f._netsync(["endbench", "manifest", "1", "2"])),
    ("netsync endbench manifest", None, lambda f: f._netsync(["endbench", "manifest"])),
    ("netsync endbench manifest host", None, lambda f: f._netsync(["endbench", "manifest", "host"])),
    ("netsync endbench ", "netsync endbench fieldsong", lambda f: f._netsync(["endbench", "fieldsong"])),
    # (the `bench` named ops parse AFTER `bench`'s own role gate -- the selftest role first)
    ("netsync bench lapse", None, lambda f: _selftest(f)._netsync(["bench", "lapse"])),
    ("netsync bench lapse", None, lambda f: _selftest(f)._netsync(["bench", "lapse", "600001"])),
    ("netsync bench lapse", None, lambda f: _selftest(f)._netsync(["bench", "lapse", "-5"])),
    ("netsync bench lapse", None, lambda f: _selftest(f)._netsync(["bench", "lapse", "hold", "1"])),
    ("netsync bench lapse", None, lambda f: _selftest(f)._netsync(["bench", "lapse", "soon"])),
    ("netsync bench handback", None, lambda f: _selftest(f)._netsync(["bench", "handback", "2"])),
    ("netsync bench handback", None, lambda f: _selftest(f)._netsync(["bench", "handback"])),
]


@pytest.mark.parametrize("literal,param,provoke", BATTLE_ARGUMENT_REFUSALS,
                         ids=[f"{r[1] or r[0]}-{i}" for i, r in enumerate(BATTLE_ARGUMENT_REFUSALS)])
def test_a_battle_argument_refusal_has_the_engines_whole_shape_before_any_gate(game, literal, param, provoke):
    """The B4/B5 argument parses run BEFORE the role gate (no client here), as ArgumentOutOfRangeExceptions: Mono's
    ``message + CRLF + "Parameter name: " + param``, both read off the stack (a param the agent SPLICES -- ``"netsync bmenu
    " + bop`` -- read as its literal head). s110's `bench lapse` / `bench handback` parse after `bench`'s own role gate."""
    agent = _agent_argument_refusals()
    assert literal in agent, sorted(agent)
    fake = FakeGame(game)
    with pytest.raises(RuntimeError) as err:
        provoke(fake)
    assert str(err.value) == f"{agent[literal]}\r\nParameter name: {param or literal}", repr(str(err.value))


# --------------------------------------------------------------------------- State: B4/B5, absent = cannot

def _battle_block(level: str) -> dict:
    """The agent's own sentinel block at patch ``level`` (its catch line), as a published `netsync` document."""
    return _catch_doc_in(level)


def test_state_reads_absent_battle_keys_as_cannot_never_as_nothing():
    """No `netsync` block: every B4/B5 capability and accessor None. A block without `battle` (s99): the capabilities
    False, every accessor None. Each patch's own block: its capabilities True, every LATER stage's capability False and
    its accessors None -- a stage-1 engine's missing `r9_refused` read as 0 would make a containment assertion green
    against the wrong DLL."""
    caps = ("coop_host_gates", "coop_containment", "coop_stock_menu", "coop_end_trailer", "coop_presentation",
            "coop_exit_with_host", "coop_menu_content", "coop_ready_mirror", "coop_result_manifest", "coop_result_replay",
            "coop_slot_handback", "coop_intro_mirror", "coop_swirl_clamp", "coop_wait_parity", "coop_start_hold",
            "coop_flee", "coop_flee_gil", "coop_defeat")
    table = State.NETSYNC_BATTLE_ACCESSORS
    none = State({"frame": 1})
    assert all(getattr(none, c) is None for c in caps) and all(getattr(none, n) is None for n in table.values())
    assert none.coop_battle is None and none.coop_peer_end_manifest is None
    s99 = State({"frame": 1, "netsync": _battle_block("s99")})
    assert all(getattr(s99, c) is False for c in caps) and all(getattr(s99, n) is None for n in table.values())
    for i, level in enumerate(BATTLE_LEVELS[1:]):
        st = State({"frame": 1, "netsync": _battle_block(level)})
        assert [getattr(st, c) for c in caps] == [True] * (i + 1) + [False] * (len(caps) - i - 1), level
        published = set(_leaves(_battle_of(_battle_block(level)))) | {
            p for p, at in BATTLE_CONTAINERS.items() if int(at[1:]) <= int(level[1:])}
        for path, name in table.items():
            if path in published:
                assert getattr(st, name) is not None or path in BATTLE_NULLABLE, (level, path)
            else:
                assert getattr(st, name) is None, (level, path)


BATTLE_BLOCK = {
    "host": {"gates_off": False, "guest_slots": 2, "cmd_phase": True, "caps": 2, "ready_mask": 3, "cmd_refused": 4,
             "cmd_dropped": 1, "cmd_queued": 7, "refused_why": "the battle intro", "dropped_why": None,
             "roster_lag": 1, "loop_cmds": 0,
             "end": {"kind": 2, "kind_name": "victory", "phase": 6, "seq": 0, "result": 1, "ui": 1, "res_state": 2,
                     "loading": True, "flags": 0, "win_pose": 15, "manifest_len": 0},
             "end_trail": ["0/0/-", "2/1/2L"], "end_edges": 3, "end_changes": 4, "end_mode": "on", "end_cmd": None},
    "peer": {"live": True, "seq": 99, "nonce": 4, "caps": 3, "ready_mask": 2, "end": None, "end_trail": [],
             "trailer_bad": 0, "trailer_skipped": 0, "trailer_why": None},
    "menu": {"roster_slots": [1], "r9_refused": 2, "r9_total": 5, "r9_cmd": 1,
             "r9_site": "BattleHUD.SendNetCommand < HarnessAgent.Execute", "guest_owned": 0, "contained": True,
             "containment_off": False, "captures": 1, "capture_refused": 0, "capture_why": None, "capture_off": False,
             "outbox": 1, "bench_open": 1, "side_refused": 0, "side_why": None,
             "captured": {"slot": 0, "action": 0, "menu": 0, "id": 0, "mask": 16, "cursor": 0, "local_slot": 0, "cmd": 1,
                          "site": "SendCommand", "hex": "01 00 00 00 00 00 10 00 00", "action_name": "Attack"}},
    "end": {"injected": True, "held": False, "kind": 2, "kind_name": "victory", "action": "victory", "inject_phase": 5,
            "inject_seq": 4, "inject_ms": 1200, "r8_hits": 30, "r8_first_ms": 900, "w1_armed": True, "watchdog": None,
            "blocker": None, "why": None, "faulted": False, "hud_reasserts": 0, "guest_mode": "on", "ach_held": 0,
            "ach_enemy_no": 12, "music": 5, "btl_flag": 96, "exit_mode": "on",
            "end_leave": {"trigger": "result-hide", "latched_ms": 40, "tries": 1, "deferred": 0, "requested": True,
                          "request_ms": 0, "why": None, "settled": True, "via": "end-leave", "stamp": 1, "stamp_host": 1,
                          "stamped": -1, "stamped_was": -1, "music_shut": True, "music_why": None, "wipe_lifted": False},
            "declined": {"count": 0, "nonce": -1, "why": None}},
}


def test_state_reads_the_battle_block():
    st = State({"frame": 1, "netsync": dict(F33_BLOCK, battle=BATTLE_BLOCK)})
    assert (st.coop_host_gates, st.coop_containment, st.coop_stock_menu, st.coop_end_trailer, st.coop_presentation,
            st.coop_exit_with_host) == (True,) * 6
    assert (st.coop_host_caps, st.coop_host_ready_mask, st.coop_host_guest_slots, st.coop_host_roster_lag) == (2, 3, 2, 1)
    assert (st.coop_host_cmd_refused, st.coop_host_cmd_dropped, st.coop_host_cmd_queued) == (4, 1, 7)
    assert st.coop_host_refused_why == "the battle intro" and st.coop_host_dropped_why == ""   # null: none yet
    assert st.coop_host_gates_off is False and st.coop_host_cmd_phase is True
    assert st.coop_host_end == BATTLE_BLOCK["host"]["end"] and st.coop_host_end is not BATTLE_BLOCK["host"]["end"]
    assert st.coop_host_end_trail == ["0/0/-", "2/1/2L"] and st.coop_host_end_cmd == "" and st.coop_host_end_mode == "on"
    assert (st.coop_peer_live, st.coop_peer_seq, st.coop_peer_caps, st.coop_peer_ready_mask) == (True, 99, 3, 2)
    assert st.coop_peer_end is None and st.coop_peer_trailer_why == ""                        # a null record: None
    assert st.coop_menu_roster_slots == [1] and st.coop_menu_r9_site.startswith("BattleHUD.SendNetCommand")
    assert (st.coop_menu_r9_refused, st.coop_menu_r9_total, st.coop_menu_r9_cmd) == (2, 5, 1)
    assert st.coop_menu_contained is True and st.coop_menu_guest_owned == 0
    assert st.coop_menu_captured["mask"] == 16 and st.coop_menu_captured is not BATTLE_BLOCK["menu"]["captured"]
    assert (st.coop_present_injected, st.coop_present_inject_phase, st.coop_present_inject_seq) == (True, 5, 4)
    assert st.coop_present_watchdog == "" and st.coop_present_why == "" and st.coop_present_r8_hits == 30
    assert (st.coop_exit_trigger, st.coop_exit_via, st.coop_exit_stamp, st.coop_exit_stamped) == \
        ("result-hide", "end-leave", 1, -1)
    assert st.coop_exit_why == "" and st.coop_exit_music_shut is True and st.coop_exit_mode == "on"
    assert st.coop_end_leave == BATTLE_BLOCK["end"]["end_leave"] and st.coop_declined_nonce == -1
    whole = st.coop_battle
    assert whole["menu"] == BATTLE_BLOCK["menu"] and whole["menu"] is not BATTLE_BLOCK["menu"]
    # a bool is never a count, a count never a bool, a string never a number -- and a wrong-typed block is no block
    odd = State({"frame": 1, "netsync": dict(F33_BLOCK, battle=dict(
        BATTLE_BLOCK, host=dict(BATTLE_BLOCK["host"], caps=True, cmd_phase=1, refused_why=7, end_trail={}),
        menu=dict(BATTLE_BLOCK["menu"], captured=[], r9_refused=1.0)))})
    assert odd.coop_host_caps is None and odd.coop_host_cmd_phase is None and odd.coop_host_refused_why is None
    assert odd.coop_host_end_trail is None and odd.coop_menu_captured is None and odd.coop_menu_r9_refused is None
    assert odd.coop_containment is False                    # its key is there, but not a count
    flat = State({"frame": 1, "netsync": dict(F33_BLOCK, battle=[])})
    assert flat.coop_host_gates is False and flat.coop_host_caps is None


def test_state_reads_the_b4_battle_doc_keys():
    """`battle.seq` / `battle.hud` (s102), `battle.result_ui` (s103), `units[].cmd_busy` (s101): absent = None."""
    old = State({"frame": 1, "battle": {"active": True, "phase": 4, "units": [{"slot": 0, "player": True}]}})
    assert old.battle_seq is None and old.battle_hud is None and old.battle_result_ui is None
    assert old.unit_cmd_busy(0) is None and old.unit_cmd_busy(4) is None
    hud = {"group": "Battle.Command", "panel": "command", "shown": True, "slot": 0,
           "commands": [{"menu": 0, "id": 1, "label": "Attack", "state": 2, "raw": 2}], "rows": []}
    new = State({"frame": 1, "battle": {"active": True, "phase": 6, "seq": 2, "hud": hud,
                                        "result_ui": {"state": 7, "loading": True, "paused": False},
                                        "units": [{"slot": 0, "player": True, "cmd_busy": 1},
                                                  {"slot": 4, "player": False, "cmd_busy": True}]}})
    assert new.battle_seq == 2 and new.battle_hud == hud and new.battle_hud["commands"][0] is not hud["commands"][0]
    assert new.battle_result_ui == {"state": 7, "loading": True, "paused": False}
    assert new.unit_cmd_busy(0) == 1 and new.unit_cmd_busy(4) is None          # a bool is not a mask
    assert State({"frame": 1, "battle": {"seq": True}}).battle_seq is None
    # [ff9mapkit netsync B4/B5] s106 `battle.hud.mirrored`, s109 `battle.result_ui.replay` -- absent = None; copied DEEP
    assert old.battle_hud_mirrored is None and old.battle_result_replay is None and new.battle_hud_mirrored is None
    deep = State({"frame": 1, "battle": {"hud": dict(hud, mirrored=True), "result_ui": {
        "state": 0, "loading": False, "paused": False, "replay": True, "rows": [{"slot": 0, "level": "5"}],
        "model": {"party_gil": 500}}}})
    assert deep.battle_hud_mirrored is True and deep.battle_result_replay is True
    ui = deep.battle_result_ui
    ui["rows"][0]["level"] = "99"
    ui["model"]["party_gil"] = 0
    assert deep.battle_result_ui["rows"][0]["level"] == "5" and deep.battle_result_ui["model"]["party_gil"] == 500
    assert State({"frame": 1, "battle": {"hud": dict(hud, mirrored=1)}}).battle_hud_mirrored is None


#: s106-s110's keys at values a live engine could publish (every fixed sub-object whole, every nullable record filled).
LATE_BLOCK = {
    "host": {"manifest": {"row_mask": 1, "rows": [{"slot": 0, "char": 0, "flags": 7, "need_exp": True, "need_ap": True,
                                                   "draw": True, "lv_before": 5, "lv_after": 7, "exp_before": 1700,
                                                   "exp_gain": 1900, "ap_gain": 5, "status": "0x0000000000010000",
                                                   "learns": [{"abil": 31, "ap_at": 3}]}],
                          "default_exp": 1900, "default_ap": 5, "gil_gain": 4321, "gil_before": 1234567,
                          "items": [{"id": 238, "count": 7}], "card": 0, "learn_count": 1, "truncated": 0,
                          "learn_capped": False},
             "manifest_bytes": 0, "manifest_captures": 3, "manifest_skipped": 1, "manifest_why": None,
             "manifest_mode": "off", "overflow": True, "learned": [{"slot": 0, "abil": 31, "ap_at": 3}],
             "handback": {"off": False, "held": 1, "held_ms": 2600, "owed": True, "g6_mask": 2, "captures": 4,
                          "returns": 3, "deferred": 1, "faults": 0,
                          "last": {"slot": 1, "frame": 900, "held_ms": 1200, "why": "handed back"},
                          "lapse": {"active": True, "hold": True, "left_ms": -1, "count": 2, "end_frame": 880}}},
    "peer": {"manifest_bad": 1, "manifest_bad_why": "row mask 0xE0 names a slot past 3", "manifest_nonce": 7,
             "manifest_rx": 2, "bench_manifest": 1, "bench_manifest_note": None},
    "menu": {"mirrored": [0], "roster_src": "bench", "roster_sig": "0x0123456789ABCDEF", "roster_gen": 4,
             "roster_painted": 4, "content_off": 64,
             "content_hits": {"command": 2, "grey": 2, "ability": 4, "bag": 1, "count": 30, "cast": 0, "refresh": 1},
             "content_faults": 0, "content_why": None, "mute_held": True,
             "roster": {"slots": [{"wire": 0, "cmds": [{"menu": 2, "cmd": 17, "type": 1, "abils": 2, "on": 1}]}],
                        "items": [{"id": 238, "count": 77}]},
             "bench_roster": {"src": "auto", "bytes": 33, "slot": 0, "wire": 0, "marker_menu": 2, "marker_cmd": 17,
                              "marker_shown": 6, "marker_grey": 7, "marker_local_mp": 6, "uk_menu": 3, "uk_cmd": 5,
                              "unlearned": 31, "unlearned_local_mp": 4, "learned": 30, "item": 238, "count": 77,
                              "mp": 1, "dbl": False, "grey": False, "note": None},
             "stock_owns": True, "why": None, "knob": 1, "knob_bench": -1, "assist_slot": -1, "stranded": [1],
             "pending": {"slot": 0, "wire": 0, "ms": 1500, "seqs": 9}, "pending_mask": 1, "refused": 1, "sent": 3,
             "mirror": {"serving": True, "open": 1, "fed": 3, "accepted": 1, "obsolete": 0, "closed": 1, "no_roster": 0,
                        "faulted": False, "fault_why": None},
             "feed": {"guest_slots": 3, "ready": 1, "caps": 2, "mode": "accept", "frozen": False, "unmap": -1,
                      "nonce": 1, "seq": 40, "live": True, "menu_open": True, "frames": 40, "taken": 2,
                      "accepted": 1, "refused": 1, "bad": 0, "last": "[01 00 00 00 00 00 10 00 00] ACCEPTED"}},
    "end": {"replay": {"mode": "local", "armed": True, "pending": False, "opened": True, "live": True, "closed": False,
                       "aborted": False, "abort_why": None, "refused": False, "verdict": 0, "why": None, "row_mask": 1,
                       "seated_mask": 3, "manifest_rows": 2, "host_state_at_arm": 0, "bench": True, "arm_ms": 2100,
                       "open_ms": 300, "close_ms": -1, "exit_waited": False, "exit_wait_ms": -1,
                       "screen": {"state": 1, "steps": 1, "writes": 0}, "fp": {"hash": "0x00000000DEADBEEF", "gil": 500}}},
}


def _late_doc() -> dict:
    """The live agent's sentinel block with :data:`LATE_BLOCK` laid over it -- every s100-s110 key present."""
    nothing, _ = _agent_netsync_nothing()
    battle = _battle_of(nothing)
    for sub, keys in LATE_BLOCK.items():
        battle[sub].update(keys)
    return nothing


def test_state_reads_the_s106_s110_keys():
    """Every s106-s110 accessor reads its key (a null string ""; a record copied deep), and the five capabilities are
    True on the live agent's keys -- a bool is never a count, a count never a bool, a string never a number."""
    st = State({"frame": 1, "netsync": _late_doc()})
    assert (st.coop_menu_content, st.coop_ready_mirror, st.coop_result_manifest, st.coop_result_replay,
            st.coop_slot_handback) == (True,) * 5
    assert st.coop_menu_mirrored == [0] and st.coop_menu_roster_src == "bench" and st.coop_menu_content_why == ""
    assert (st.coop_content_hits_command, st.coop_content_hits_count, st.coop_content_hits_refresh) == (2, 30, 1)
    assert st.coop_content_hits == LATE_BLOCK["menu"]["content_hits"] and st.coop_menu_mute_held is True
    assert st.coop_menu_roster["slots"][0]["cmds"][0]["cmd"] == 17 and st.coop_menu_bench_roster["marker_cmd"] == 17
    assert (st.coop_stock_owns, st.coop_stock_why, st.coop_stock_knob, st.coop_stock_knob_bench) == (True, "", 1, -1)
    assert st.coop_stranded == [1] and st.coop_pending == {"slot": 0, "wire": 0, "ms": 1500, "seqs": 9}
    assert (st.coop_mirror_open, st.coop_mirror_fed, st.coop_mirror_refused, st.coop_stock_sent) == (1, 3, 1, 3)
    assert st.coop_mirror_serving is True and st.coop_mirror_fault_why == "" and st.coop_feed["seq"] == 40
    assert st.coop_host_manifest["rows"][0]["learns"] == [{"abil": 31, "ap_at": 3}]
    assert (st.coop_host_manifest_captures, st.coop_host_manifest_mode, st.coop_host_overflow) == (3, "off", True)
    assert st.coop_host_learned == [{"slot": 0, "abil": 31, "ap_at": 3}] and st.coop_host_manifest_why == ""
    assert (st.coop_peer_manifest_bad, st.coop_peer_manifest_nonce, st.coop_peer_bench_manifest) == (1, 7, 1)
    assert st.coop_peer_bench_manifest_note == "" and st.coop_peer_manifest_bad_why.startswith("row mask 0xE0")
    assert (st.coop_replay_mode, st.coop_replay_armed, st.coop_replay_verdict, st.coop_replay_why) == ("local", True, 0, "")
    assert st.coop_replay_screen == {"state": 1, "steps": 1, "writes": 0} and st.coop_replay_fp["gil"] == 500
    assert (st.coop_replay_exit_wait_ms, st.coop_replay_close_ms, st.coop_replay_row_mask) == (-1, -1, 1)
    assert (st.coop_handback_held, st.coop_handback_g6_mask, st.coop_handback_returns) == (1, 2, 3)
    assert st.coop_handback_last["why"] == "handed back" and st.coop_handback_owed is True
    assert (st.coop_lapse_active, st.coop_lapse_hold, st.coop_lapse_left_ms, st.coop_lapse_end_frame) == \
        (True, True, -1, 880)
    assert st.coop_handback["lapse"] == st.coop_handback_lapse == LATE_BLOCK["host"]["handback"]["lapse"]
    # deep copies: mutating what an accessor hands out never reaches the doc
    m = st.coop_host_manifest
    m["rows"][0]["learns"].clear()
    assert st.coop_host_manifest["rows"][0]["learns"] == [{"abil": 31, "ap_at": 3}]
    # the peer end's decoded manifest (a plain property beside the table)
    pe = State({"frame": 1, "netsync": dict(_late_doc(), battle=dict(_battle_of(_late_doc()), peer=dict(
        _battle_of(_late_doc())["peer"], end={"kind": 2, "manifest": LATE_BLOCK["host"]["manifest"]})))})
    assert pe.coop_peer_end_manifest == LATE_BLOCK["host"]["manifest"]
    # a bool is never a count, a count never a bool, a string never a number -- and a wrong-typed block is no block
    doc = _late_doc()
    b = _battle_of(doc)
    b["menu"].update(stock_owns=1, mirrored={}, content_hits=[])
    b["host"].update(manifest_captures=True, handback=dict(b["host"]["handback"], held=1.0, lapse=None))
    b["end"].update(replay=dict(b["end"]["replay"], verdict="0"))
    odd = State({"frame": 1, "netsync": doc})
    assert odd.coop_ready_mirror is False and odd.coop_stock_owns is None and odd.coop_menu_mirrored is None
    assert odd.coop_menu_content is False and odd.coop_content_hits_command is None
    assert odd.coop_result_manifest is False and odd.coop_host_manifest_captures is None
    assert odd.coop_handback_held is None and odd.coop_lapse_active is None and odd.coop_handback_lapse is None
    assert odd.coop_replay_verdict is None and odd.coop_slot_handback is True


# --------------------------------------------------------------------------- the driver: B4/B5 capabilities

@pytest.mark.parametrize("level", ["s99", "s100", "s101", "s102", "s103", "s105"])
def test_netsync_refuses_a_battle_verb_its_engine_lacks_before_spending_a_step(game, level):
    """An engine without a stage answers its verb "unknown sub-verb" only AFTER the step; the driver names the patch and
    the key first -- and quotes the engine's would-be refusal, so a scenario's "unknown sub-verb" match still reads it.
    The verbs the engine HAS still reach it (whose own gates may refuse them -- after the step)."""
    fake = FakeGame(game)
    names = list(FG.NETSYNC_BATTLE_CAPS)
    have = [c for c in names if int(FG.NETSYNC_BATTLE_CAPS[c][0][1:]) <= int(level[1:])]
    fake.netsync_caps = frozenset(FG.NETSYNC_F33_CAPS) | frozenset(have)
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(FIELD)
        g.netsync("selftest", 1)
        lacking = [v for c in names if c not in have for v in FG.NETSYNC_BATTLE_CAPS[c][1]]
        for verb in lacking:
            _attr, key, patch, _what = Session.NETSYNC_BATTLE_SUBVERBS[verb]
            with pytest.raises(HarnessError, match=rf"^netsync {verb}: the deployed engine publishes no "
                                                   rf"`{re.escape(key)}` .*\(memoria-patch {patch}\); it would answer "
                                                   rf"\"netsync: unknown sub-verb '{verb}'\" only after the step"):
                g.netsync(verb, *(("victory",) if verb == "endbench" else ("closeall",) if verb == "bmenu"
                                  else ("content", "on") if verb == "bbench" else ()))
        assert not any(s[:1] == ["netsync"] and s[1:2] and s[1] in lacking for s in fake.executed)
        for verb in [v for c in have for v in FG.NETSYNC_BATTLE_CAPS[c][1]]:
            try:
                g.netsync(verb, *({"guestslots": (2,), "bcmd": ("01",), "hostgates": (1,), "containment": (1,),
                                   "bctl": ("00", "00"), "bmenu": ("closeall",), "bbench": ("content", "on"),
                                   "endbench": ("clear",)}[verb]))
            except HarnessError:
                pass                                        # the agent's own gate, after the step: fine
            assert any(s[:2] == ["netsync", verb] for s in fake.executed), verb


@pytest.mark.parametrize("level,op", [("s103", "guest"), ("s103", "exit"), ("s104", "exit"), ("s107", "manifest"),
                                      ("s103", "manifest"), ("s108", "fieldsong"), ("s108", "replay"), ("s108", "quit")])
def test_netsync_refuses_an_endbench_op_a_later_patch_added_before_spending_a_step(game, level, op):
    """`endbench guest` (s104), `exit` (s105), `manifest` (s108) and `fieldsong` / `replay` / `quit` (s109) ride a verb an
    older engine HAS: that engine refuses the op only after the step ("unknown op" -- an s103-s107 engine's `manifest`
    "is stage 9"); the driver names the patch, the key and that answer first. Its other ops still reach it."""
    fake = FakeGame(game)
    fake.netsync_caps = _caps_at(level)
    answer = Session.NETSYNC_ENDBENCH_OLD_ANSWERS.get(op, f"netsync endbench: unknown op '{op}'")
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.netsync("selftest", 1)
        _attr, key, patch, _what = Session.NETSYNC_ENDBENCH_OP_CAPS[op]
        n = len(fake.executed)
        with pytest.raises(HarnessError, match=rf"^netsync endbench {op}: the deployed engine publishes no "
                                               rf"`{re.escape(key)}` .*\(memoria-patch {patch}\); it would answer "
                                               rf"\"{re.escape(answer)}"):
            g.netsync("endbench", op, "off")
        assert len(fake.executed) == n
        with pytest.raises(RuntimeError, match=rf"^{re.escape(answer)}"):
            fake._netsync(["endbench", op, "off"])         # ...what the engine itself says, after the step
        st = g.netsync("endbench", "victory")
        assert st.coop_peer_end["kind"] == BW.K_VICTORY and fake.executed[-1] == ["netsync", "endbench", "victory"]


@pytest.mark.parametrize("level,args", [("s106", ("start", "1")), ("s106", ("knob", "0")), ("s106", ("ready", "1"))])
def test_netsync_refuses_a_bbench_feed_op_on_an_s106_engine_before_spending_a_step(game, level, args):
    """`bbench`'s feed ops (s107) ride a verb an s106 engine HAS: it refuses them only after the step, in ITS words (the
    note naming stage 8's ops); the driver names s107 and quotes that answer first. `roster` / `content` still reach it."""
    fake = FakeGame(game)
    fake.netsync_caps = _caps_at(level)
    op = args[0]
    answer = f"netsync bbench: unknown op '{op}' ({_agent_bbench_unknown([_patch_bytes('s106')])})"
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.netsync("selftest", 1)
        n = len(fake.executed)
        with pytest.raises(HarnessError, match=rf"^netsync bbench {op}: the deployed engine publishes no "
                                               rf"`netsync\.battle\.menu\.stock_owns` .*\(memoria-patch s107\); it would "
                                               rf"answer \"{re.escape(answer)}\" only after the step"):
            g.netsync("bbench", *args)
        assert len(fake.executed) == n
        with pytest.raises(RuntimeError) as err:
            fake._netsync(["bbench", *args])                # ...what the engine itself says, after the step
        assert str(err.value) == answer
        st = g.netsync("bbench", "content", "0x3F")
        assert st.coop_menu_content_off == 64 and fake.executed[-1] == ["netsync", "bbench", "content", "0x3F"]
        assert st.coop_ready_mirror is False and st.coop_stock_owns is None


@pytest.mark.parametrize("op,arg", [("lapse", "hold"), ("handback", "0"), ("LAPSE", "end")])
def test_bench_lapse_and_handback_are_never_sent_to_an_engine_that_reads_them_as_bench_1(game, op, arg):
    """s110 THE HAZARD: an engine before it parses `bench lapse` / `bench handback` with Arg()'s fallback as `bench 1`
    and turns the FIELD-GATE bench ON -- no refusal, a wrong action. The driver probes `netsync.battle.host.handback`
    first and never sends them without it (the s109 stand-in reproduces the hazard); the plain `bench 1|0` still goes."""
    fake = FakeGame(game)
    fake.netsync_caps = _caps_at("s109")
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.netsync("selftest", 1)
        assert g.state.coop_slot_handback is False and g.state.netsync["bench"] is False
        n = len(fake.executed)
        with pytest.raises(HarnessError, match=rf"^netsync bench {op.lower()}: the deployed engine publishes no "
                                               r"`netsync\.battle\.host\.handback` .*\(memoria-patch s110\); an engine "
                                               r"before it reads .* as `bench 1` and turns the FIELD-GATE bench ON"):
            g.netsync("bench", op, arg)
        assert len(fake.executed) == n and g.state.netsync["bench"] is False
        fake._netsync(["bench", op, arg])                   # what the old engine would DO with it: the bench ON
        assert fake.netsync["bench"] is True
        st = g.netsync("bench", 0)
        assert st.netsync["bench"] is False
    fake = FakeGame(game)                                   # ...and the live stack's agent takes them
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.netsync("selftest", 1)
        st = g.netsync("bench", op, arg)
        assert fake.executed[-1] == ["netsync", "bench", op, arg] and st.netsync["bench"] is False
        assert st.coop_handback_off is (op == "handback") and st.coop_lapse_hold is (op == "lapse")


def test_netsync_refuses_an_unknown_bmenu_or_endbench_op_before_spending_a_step_in_the_engines_words(game):
    fake = FakeGame(game)
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.netsync("selftest", 1)
        n = len(fake.executed)
        for sub, op in (("bmenu", "bogus"), ("bmenu", ""), ("endbench", "victorious"), ("endbench", ""),
                        ("bbench", "rosters"), ("bbench", "")):
            with pytest.raises(HarnessError) as err:
                g.netsync(sub, *((op,) if op else ()))
            with pytest.raises(RuntimeError) as agent:
                fake._netsync([sub, *((op,) if op else ())])     # what the engine would say after its gates
            assert str(err.value) == str(agent.value), (str(err.value), str(agent.value))
        assert len(fake.executed) == n
        with pytest.raises(HarnessError, match=r"expected `manifest 0\|none\|1\|2\|3` or `manifest host on\|off`"):
            g.netsync("endbench", "manifest")              # (a listed op since s108: sent, its argument refused there)
        assert fake.executed[-1] == ["netsync", "endbench", "manifest"]
        st = g.netsync("bmenu", "CAPTURE", "off")               # the agent lowercases the op; so does the driver
        assert st.coop_menu_capture_off is True and fake.executed[-1] == ["netsync", "bmenu", "CAPTURE", "off"]
        st = g.netsync("bbench", "CONTENT", "off")
        assert st.coop_menu_content_off == BW.CONTENT_ALL and fake.executed[-1] == ["netsync", "bbench", "CONTENT", "off"]


def test_an_f3_engine_refuses_the_battle_verbs_naming_the_patch(game):
    fake = FakeGame(game)
    fake.netsync_dialogue = None
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.netsync("selftest", 1)
        for verb, (_attr, _key, patch, _what) in Session.NETSYNC_BATTLE_SUBVERBS.items():
            with pytest.raises(HarnessError, match=rf"netsync {verb}: .*F3 lockstep.*a B4/B5 battle co-op verb .*"
                                                   rf"memoria-patch {patch}.*memoria-patch s96"):
                g.netsync(verb)


def test_reset_releases_every_battle_lever_and_the_bench_end(game):
    """Every B4/B5 lever, the parked `bcmd` frames, the `bctl` stamp, a `guestslots` override, the bench end and the
    `endbench cmd` one-shot go back to rest on `reset` (HarnessSelfTest(false) -> HarnessReleaseBench) -- read again
    UNDER a fresh selftest role, so a lever the role merely masks cannot pass for released."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(FIELD)
        g.netsync("selftest", 1)
        roster = BW.encode_roster({"slots": {0: [BW.roster_cmd(2, 17, abils=[(6, 1, True)])]},
                                   "items": [{"id": 238, "count": 77, "target": 1, "for_dead": False}]})
        for args in (("guestslots", "0x3"), ("hostgates", 0), ("containment", 0), ("bctl", "00 01"),
                     ("bmenu", "capture", "off"), ("endbench", "host", "cadence"), ("endbench", "guest", "settle"),
                     ("endbench", "exit", "off"), ("endbench", "victory"), ("endbench", "cmd"),
                     ("bcmd", BW.command_hex(1, BW.ACT_ATTACK, mask=0x10))):
            g.netsync(*args)
        st = g.state                                        # (the `bctl` stamp is fresh for 2.5 s: read it now)
        assert (st.coop_host_gates_off, st.coop_menu_containment_off, st.coop_menu_capture_off) == (True,) * 3
        assert st.coop_host_guest_slots == 3 and st.coop_host_loop_cmds == 1 and st.coop_menu_guest_owned == 3
        for args in (("bbench", "content", "0"), ("bbench", "roster", BW.hex_bytes(roster)), ("bbench", "knob", "0"),
                     ("endbench", "manifest", "host", "off"), ("endbench", "manifest", "1"), ("endbench", "fieldsong", 1),
                     ("endbench", "replay", "local"), ("endbench", "quit", "on"), ("bench", "handback", 0),
                     ("bench", "lapse", "hold")):           # [ff9mapkit netsync B4/B5] s106-s110's levers and benches
            g.netsync(*args)
        g.press("cancel")                                   # (the quit prompt takes Cancel -- never Confirm)
        assert not fake.quit_prompt
        g.netsync("endbench", "quit", "on")
        st = g.state
        assert (st.coop_host_end_mode, st.coop_present_guest_mode, st.coop_exit_mode) == ("cadence", "settle", "off")
        assert st.coop_peer_end["bench"] is True and st.coop_host_end_cmd == "armed"
        assert st.coop_menu_content_off == BW.CONTENT_ALL and st.coop_menu_bench_roster["src"] == "hex"
        assert (st.coop_stock_knob, st.coop_stock_knob_bench) == (0, 0)
        assert (st.coop_host_manifest_mode, st.coop_replay_mode) == ("off", "local")
        assert st.coop_peer_bench_manifest == 1 and st.coop_peer_end["flags"] & (BW.FLAG_MANIFEST | BW.FLAG_FIELD_SONG)
        assert st.coop_handback_off is True and st.coop_lapse_hold is True and fake.quit_prompt
        g.send("reset")
        g.wait_for(lambda s: s.netsync is not None and not s.netsync["forced"], timeout=5.0, what="the release")
        st = g.netsync("selftest", 1)
        assert (st.coop_host_gates_off, st.coop_menu_containment_off, st.coop_menu_capture_off) == (False,) * 3
        assert (st.coop_host_guest_slots, st.coop_host_loop_cmds, st.coop_menu_guest_owned) == (0, 0, 0)
        assert (st.coop_host_end_mode, st.coop_present_guest_mode, st.coop_exit_mode) == ("on", "on", "on")
        assert st.coop_peer_end is None and st.coop_host_end_cmd == ""
        assert st.coop_menu_content_off == 0 and st.coop_menu_bench_roster is None and st.coop_menu_roster_src == ""
        assert (st.coop_stock_knob, st.coop_stock_knob_bench) == (1, -1)
        assert (st.coop_host_manifest_mode, st.coop_replay_mode, st.coop_peer_bench_manifest) == ("on", "on", 0)
        assert st.coop_handback_off is False and st.coop_lapse_active is False and st.coop_lapse_end_frame >= 0
        assert not fake.quit_prompt                         # the bench's own quit prompt is hidden with the release


def test_selftest_0_releases_the_battle_bench_on_an_unforced_role_too(game):
    """HarnessSelfTest(false) releases the B4 bench ABOVE its forced-role early return (an ini-configured selftest
    satisfies every B4 verb's gate): the stand-in's `_selftest_release` must too."""
    assert _battle_text("the B4 bench state is released on EVERY path, ABOVE the forced-role early")
    fake = _selftest(FakeGame(game))
    fake._netsync(["hostgates", "0"])
    fake.netsync["forced"] = False                      # as if the role came from the ini
    fake._netsync(["selftest", "0"])
    assert fake._nb.gates_off_lever is False


# --------------------------------------------------------------------------- the stand-in: the B4/B5 behaviour core

def _armed_selftest(g, fake, *, battle=False):
    g.newgame(settle=0)
    g.warp(FIELD)
    g.netsync("selftest", 1)
    if battle:
        _bench_battle(fake)
        g.wait_for(lambda s: s.coop_peer_live, timeout=4.0, what="the own battle's loopback lane")


def test_an_own_battles_intro_refuses_a_parked_command_and_its_opening_takes_it(game):
    """Stage 1 on the stand-in (design 8.2 `coop_battle_host_gates`): a `bcmd` parked on the field waits on the loopback
    (only an own battle drains it); the intro drains it REFUSED (`the battle intro`, cmd_refused +1, no queue); the
    command phase opens with the caps bit, the roster within the opening frame, slot 1 skipped by the local HUD -- and the
    same frame then lands (cmd_queued +1, slot 1 done)."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        _armed_selftest(g, fake)
        g.netsync("guestslots", 2)
        frame = BW.command_hex(1, BW.ACT_ATTACK, mask=0x10)
        st = g.netsync("bcmd", frame)
        assert st.coop_host_loop_cmds == 1 and st.coop_peer_live is False and st.coop_host_caps == -1
        refused = st.coop_host_cmd_refused
        _bench_battle(fake, intro=240)
        st = g.wait_for(lambda s: s.coop_host_loop_cmds == 0, timeout=4.0, what="the intro drain")
        assert st.coop_host_cmd_refused == refused + 1 and st.coop_host_refused_why == "the battle intro"
        assert st.coop_host_cmd_queued == 0 and st.battle_phase == BW.PHASE_ENTER and not st.commands_enabled
        st = g.wait_for(lambda s: s.commands_enabled and s.coop_peer_ready_mask, timeout=4.0, what="the opening")
        assert st.coop_host_caps & BW.CAP_COMMAND_PHASE_GATED and st.coop_peer_caps == st.coop_host_caps
        assert st.coop_host_cmd_phase and 0 <= st.coop_host_roster_lag <= 2 and st.coop_menu_roster_slots == [1]
        assert st.coop_peer_ready_mask & 2 and st.turn_slot != 1                      # the local HUD skips slot 1
        queued = st.coop_host_cmd_queued
        g.netsync("bcmd", frame)
        st = g.wait_for(lambda s: s.coop_host_cmd_queued == queued + 1, timeout=4.0, what="the command to land")
        assert 1 in st.battle["turn"]["done"] and not st.coop_peer_ready_mask & 2


def test_hostgates_0_reverts_the_stage_to_the_pre_stage_host(game):
    """The calibration lever: no caps bit 1, no intake guard (the intro frame is NOT refused -- it reaches the
    ownership/ready checks), and the Ready bit follows the HUD's queues whatever the phase."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        _armed_selftest(g, fake)
        g.netsync("guestslots", 2)
        st = g.netsync("hostgates", 0)
        assert st.coop_host_gates_off is True
        refused, dropped = st.coop_host_cmd_refused, st.coop_host_cmd_dropped
        g.netsync("bcmd", BW.command_hex(1, BW.ACT_ATTACK, mask=0x10))
        _bench_battle(fake, intro=240)
        st = g.wait_for(lambda s: s.coop_host_loop_cmds == 0 and s.coop_peer_live, timeout=4.0, what="the drain")
        # [ff9mapkit netsync R3 s111] bits 2-5 are the R3 bits (the intro mirror, the hold) -- the stage's bit 1 is clear
        assert (st.coop_host_caps & ~0x3C) == 0 and (st.coop_peer_caps & ~0x3C) == 0
        assert st.coop_host_caps & BW.CAP_INTRO_MIRROR and st.coop_peer_caps == st.coop_host_caps
        assert st.coop_host_cmd_refused == refused and st.coop_host_cmd_dropped == dropped + 1
        assert st.coop_host_dropped_why == "slot 1 not awaiting input"


@pytest.mark.parametrize("frame,why,literals", [
    ("01 01 00 00 00 00 10 00", "malformed command frame: len 8, ver 1 (want 9 bytes, ver 1)",
     ("malformed command frame: ", "len ", ", ver ", " (want 9 bytes, ver 1)")),
    ("02 01 00 00 00 00 10 00 00", "malformed command frame: len 9, ver 2 (want 9 bytes, ver 1)",
     ("malformed command frame: ", " (want 9 bytes, ver 1)")),
    ("01 01 00 00 00 00 00 00 00", "slot 1 Attack: empty target mask", (": empty target mask", 'case ActAttack: return "Attack";')),
    ("01 02 00 00 00 00 10 00 00", "slot 2 is not a guest slot", (" is not a guest slot",)),
    ("01 01 07 00 00 00 10 00 00", "slot 1: unknown action 7 (v1 knows 0-4)", (": unknown action ", " (v1 knows 0-4)")),
])
def test_a_command_frame_the_host_declines_names_itself(game, frame, why, literals):
    """Every decline past the intake guard names itself (design 3.8 item 4): `cmd_dropped` +1 and `dropped_why` the
    engine's reason (the literals HandleCommandPayload splices it from, each read off the stack)."""
    for piece in literals:
        assert _battle_text(piece), piece
    fake = FakeGame(game)
    with session(game, fake) as g:
        _armed_selftest(g, fake, battle=True)
        g.netsync("guestslots", 2)
        st = g.wait_for(lambda s: s.coop_peer_ready_mask and s.coop_peer_ready_mask & 2, timeout=4.0, what="slot 1")
        dropped = st.coop_host_cmd_dropped
        g.netsync("bcmd", frame)
        st = g.wait_for(lambda s: s.coop_host_cmd_dropped == dropped + 1, timeout=4.0, what="the drop")
        assert st.coop_host_dropped_why == why and st.coop_host_cmd_queued == 0


def _dio(g, fake, *, fresh: bool = True):
    """A selftest diorama in its steady command phase (the containment / stock-menu / end benches' start)."""
    fake.reinit_fields = {FIELD}
    fake.encounter_fields = {FIELD}
    if fresh:
        g.newgame(settle=0)
    g.warp(FIELD)
    g.netsync("selftest", 1)
    fake.player = [10.0, 0.0, 20.0]
    fake.control = True
    g.netsync("dioboot", 67)
    return g.wait_for(lambda s: s.coop_menu_contained and s.commands_enabled and s.battle_phase == BW.PHASE_NORMAL,
                      timeout=4.0, what="the diorama's steady phase")


def test_r9_refuses_a_local_enqueue_inside_the_diorama_and_containment_0_lets_it_swing(game):
    """Stage 2 on the stand-in: `battlecmd` inside the diorama ACKS (SendNetCommand's bookkeeping runs) but R9 refuses
    the enqueue -- `r9_refused` +1 this boot, `r9_cmd` 1, the site SendNetCommand's, `cmd_busy` never set, the enemy's
    HP untouched. `containment 0` = the pre-stage guest: the Attack queues and swings."""
    fake = FakeGame(game)
    fake.cmd_resolve_frames = 20
    with session(game, fake) as g:
        st = _dio(g, fake)
        assert (st.coop_menu_r9_refused, st.coop_menu_r9_cmd) == (0, -1)
        total = st.coop_menu_r9_total
        hp = st.unit("Masked Man")["hp_raw"]
        g.battle_command(0, 1, sub=176, target=16)       # `battlecmd 0 1 176 16 0` (SendNetCommand)
        st = stays(g, lambda s: s.unit_cmd_busy(0) == 0, frames=30, what="R9 let the enqueue through")
        assert (st.coop_menu_r9_refused, st.coop_menu_r9_total, st.coop_menu_r9_cmd) == (1, total + 1, 1)
        assert st.coop_menu_r9_site.startswith("BattleHUD.SendNetCommand") and st.unit("Masked Man")["hp_raw"] == hp
        g.netsync("bmenu", "close", 0)                       # the refused slot is done: free it for the red leg
        g.netsync("containment", 0)
        g.battle_command(0, 1, sub=176, target=16)
        g.wait_for(lambda s: s.unit_cmd_busy(0) == 1, timeout=4.0, what="the local enqueue (the pre-stage red)")
        st = g.wait_for(lambda s: s.unit("Masked Man")["hp_raw"] < hp, timeout=4.0, what="the local swing")
        assert st.coop_menu_r9_refused == 1


def test_bctl_owns_a_guest_slot_on_the_field_and_g2_never_inside_the_diorama(game):
    fake = FakeGame(game)
    with session(game, fake) as g:
        _armed_selftest(g, fake)
        g.netsync("guestslots", 1)
        st = g.netsync("bctl", BW.control_hex(False))
        assert st.coop_menu_guest_owned == 1 and st.coop_menu_contained is False
        st = g.netsync("bctl", "01")                         # one byte: ParseControl refuses it, nothing stamped
        assert st.coop_menu_guest_owned == 1                 # (the earlier stamp is still fresh)
        g.send("reset")
        st = _dio(g, fake, fresh=False)
        g.netsync("guestslots", 1)
        st = g.netsync("bctl", "00 00")
        assert st.coop_menu_guest_owned == 0 and st.coop_menu_contained is True        # G2
        st = g.netsync("containment", 0)
        assert st.coop_menu_guest_owned == 1                 # the lever: the pre-stage guest follows the lane


def test_the_bench_opener_opens_the_stock_panel_and_a_commit_is_captured_not_enqueued(game):
    """Stage 3 on the stand-in: `bmenu open 0` puts slot 0 on the ReadyQueue -- the command panel opens (`battle.hud`);
    Attack + its target commit is CAPTURED as the v1 frame `01 00 00 00 00 00 10 00 00` (the host decodes slot 0 Attack
    -> 0x10), the slot done, nothing queued; `capture off` sends the same commit into R9 (site SendCommand); Change is
    refused outside the v1 scope; `mainmenu` fires the side gate."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        _dio(g, fake)
        st = g.netsync("bmenu", "open", 0)
        st = g.wait_for(lambda s: s.turn_slot == 0 and s.battle_hud and s.battle_hud["panel"] == "command",
                        timeout=4.0, what="the stock command panel")
        assert st.coop_menu_bench_open == 1 and st.battle_hud["group"] == "Battle.Command"
        assert [c["label"] for c in st.battle_hud["commands"]][:2] == ["Attack", "Defend"]
        captures = st.coop_menu_captures
        g.press("confirm", 4)
        g.wait_for(lambda s: s.battle_hud["panel"] == "target", timeout=4.0, what="the target panel")
        g.press("confirm", 4)
        st = g.wait_for(lambda s: s.coop_menu_captures == captures + 1, timeout=4.0, what="the capture")
        cap = st.coop_menu_captured
        assert {k: cap[k] for k in ("slot", "action", "menu", "id", "mask", "cursor", "local_slot", "site")} == \
            {"slot": 0, "action": 0, "menu": 0, "id": 0, "mask": 16, "cursor": 0, "local_slot": 0, "site": "SendCommand"}
        assert cap["hex"] == "01 00 00 00 00 00 10 00 00" == BW.command_hex(0, BW.ACT_ATTACK, mask=16)
        assert BW.decode_command(bytes.fromhex(cap["hex"])) == {"slot": 0, "action": 0, "menu": 0, "id": 0, "mask": 16,
                                                                "cursor": 0}
        assert 0 in st.battle["turn"]["done"] and st.unit_cmd_busy(0) == 0 and st.coop_menu_r9_refused == 0
        assert st.coop_menu_outbox == 1 and st.battle_hud["panel"] == "none"
        g.netsync("bmenu", "capture", "off")
        g.netsync("bmenu", "close", 0)
        g.netsync("bmenu", "open", 0)
        g.wait_for(lambda s: s.turn_slot == 0, timeout=4.0, what="the reopened panel")
        g.press("confirm", 4)
        g.press("confirm", 4)
        st = g.wait_for(lambda s: s.coop_menu_r9_refused == 1, timeout=4.0, what="R9 behind the lever")
        assert st.coop_menu_r9_site.startswith("BattleHUD.SendCommand") and st.coop_menu_captures == captures + 1
        side = st.coop_menu_side_refused
        st = g.netsync("bmenu", "mainmenu")
        assert st.coop_menu_side_refused == side + 1
        assert st.coop_menu_side_why == "the in-battle main menu (AccessMenu / OnKeyMenu)"
        assert _battle_text(st.coop_menu_side_why)


def test_endbench_fabricates_each_kind_through_the_codec(game):
    """Stage 4's leg A on the stand-in: each template op's kind comes out of ClassifyEnd (incl. var 32's Event and CLOSE +
    DEFEAT), the block rides the trailer codec, `peer.end` serves it as the BENCH end (nonce 181), each fabricate
    advances its wire seq; `clear` disarms it."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        _armed_selftest(g, fake)
        st = g.netsync("endbench", "victory")
        e = st.coop_peer_end
        assert e == {"kind": 2, "kind_name": "victory", "phase": 6, "seq": 0, "result": 1, "ui": 0, "res_state": -1,
                     "loading": False, "flags": 0, "win_pose": 15, "manifest_len": 0, "flee_gil": -1, "rows": 0,
                     "bench": True, "nonce": 181, "wire_seq": e["wire_seq"], "manifest": None, "manifest_why": None}
        seq = e["wire_seq"]
        for op, kind in (("pending", 1), ("nopose", 3), ("defeat", 4), ("escape", 5), ("event", 7), ("fight", 0)):
            st = g.netsync("endbench", op)
            assert st.coop_peer_end["kind"] == kind, op
        for args, kind in ((("other", 5), 6), (("other", 3), 4)):
            assert g.netsync("endbench", *args).coop_peer_end["kind"] == kind, args
        st = g.netsync("endbench", "ui", 1)
        assert st.coop_peer_end["res_state"] == 0 and st.coop_peer_end["wire_seq"] == seq + 9
        st = g.netsync("endbench", "state", 2, "loading")
        assert (st.coop_peer_end["res_state"], st.coop_peer_end["loading"]) == (2, True)
        assert g.netsync("endbench", "afterevent", 1).coop_peer_end["flags"] == 1
        assert g.netsync("endbench", "overflow", 1).coop_peer_end["flags"] == 5
        st = g.netsync("endbench", "clear")
        assert st.coop_peer_end is None


def test_a_presented_victory_holds_at_r8_and_the_host_s_result_hide_takes_the_guest_home(game):
    """Stages 5-6 on the stand-in: `endbench victory` in a diorama injects MENU_OFF + _WITH_ENEMY (the stock tail: VICTORY,
    btl_flag 32|64, phase 6 to its WAIT seq), R8 then counts; `ui 1` + `state 7` latches the host's result-hide, the
    end-leave settles the return (`btl_result` stamped 1, the end fade lifted) and the field reads `battle.result` 1."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        st = _dio(g, fake)
        returns = st.diorama_returns
        assert st.coop_exit_why == BW.exit_why(BW.EXIT_NOT_LATCHED) and st.coop_exit_trigger == ""
        assert st.coop_present_injected is False and st.coop_exit_mode == "on"
        st = g.netsync("endbench", "victory")
        st = g.wait_for(lambda s: s.coop_present_injected, timeout=4.0, what="the injection")
        assert (st.coop_present_action, st.coop_present_inject_phase, st.coop_present_inject_seq) == ("victory", 5, 4)
        assert not st.commands_enabled and st.turn_slot == -1
        st = g.wait_for(lambda s: s.coop_present_r8_hits > 0, timeout=10.0, what="R8")
        assert st.battle_phase == BW.PHASE_VICTORY and st.battle_seq == BW.SEQ_VICTORY_WAIT and st.battle_result == 1
        assert st.coop_present_btl_flag & (BW.BTL_PLAY_END_SONG | BW.BTL_END_LOAD) == 96 and st.coop_present_r8_first_ms >= 0
        g.netsync("endbench", "ui", 1)
        st = g.netsync("endbench", "state", 6)
        assert st.coop_exit_trigger == ""                    # End is not Hide
        fake.dio_leave_frames = 120                         # a teardown slow enough to read the Leave-time settle first
        g.netsync("endbench", "state", 7)
        st = g.wait_for(lambda s: s.coop_exit_requested, timeout=4.0, what="the end-leave")
        assert st.diorama_booted and (st.coop_exit_settled, st.coop_exit_via) == (True, "end-leave")
        assert (st.coop_exit_stamp, st.coop_exit_stamp_host, st.coop_exit_stamped) == (1, 1, -1)   # decided, not written
        assert st.coop_exit_music_shut and not st.coop_exit_wipe_lifted and 0 <= st.coop_exit_request_ms <= 100
        st = g.wait_for(lambda s: s.diorama_returns == returns + 1, timeout=6.0, what="the end-leave's return")
        assert (st.coop_exit_trigger, st.coop_exit_tries, st.coop_exit_requested, st.coop_exit_via) == \
            ("result-hide", 1, True, "end-leave")
        assert (st.coop_exit_stamp, st.coop_exit_stamp_host, st.coop_exit_stamped) == (1, 1, 1)
        assert st.coop_exit_wipe_lifted and st.coop_exit_music_shut and st.battle_result == 1
        assert st.diorama_last_return == "warm" and not st.diorama_booted
        # EndHudOff is keyed on Active: the next REAL battle (the receipts kept) asks for commands as ever
        g.wait_for(lambda s: s.control, timeout=4.0, what="control back")
        g.send("battle 67")
        st = g.wait_for(lambda s: s.in_battle and s.commands_enabled, timeout=6.0, what="the next battle's menu")
        assert st.coop_present_injected is True and st.battle_phase == BW.PHASE_NORMAL


def test_exit_off_latches_the_hosts_exit_but_never_leaves(game):
    """Stage 6's red inside its own DLL: `endbench exit off` -- the trigger still latches, no end-leave (tries 0, not
    requested, why the lever); a manual `dioleave` then settles nothing (no stamp, no lift)."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        _dio(g, fake)
        g.netsync("endbench", "exit", "off")
        g.netsync("endbench", "nopose")
        g.netsync("endbench", "ui", 1)
        g.netsync("endbench", "state", 7)
        st = g.wait_for(lambda s: s.coop_exit_trigger == "result-hide", timeout=4.0, what="the latch")
        st = stays(g, lambda s: s.diorama_booted, frames=90, what="the lever let the guest leave")
        assert (st.coop_exit_mode, st.coop_exit_tries, st.coop_exit_requested) == ("off", 0, False)
        assert st.coop_exit_why == BW.exit_why(BW.EXIT_HELD_BY_LEVER) and _battle_text(st.coop_exit_why)
        g.netsync("dioleave")
        st = g.wait_for(lambda s: not s.diorama_booted, timeout=6.0, what="the manual leave")
        assert (st.coop_exit_settled, st.coop_exit_music_shut, st.coop_exit_wipe_lifted) == (False, False, False)
        assert st.battle_result == BW.BTL_RESULT_VICTORY_NO_POSE     # the CLOSE fold, never stamped back to 1


def test_guest_off_presents_nothing_and_says_why(game):
    fake = FakeGame(game)
    with session(game, fake) as g:
        _dio(g, fake)
        g.netsync("endbench", "guest", "off")
        g.netsync("endbench", "victory")
        st = stays(g, lambda s: not s.coop_present_injected and s.battle_phase == BW.PHASE_NORMAL, frames=30,
                   what="the off lever presented the end")
        assert st.coop_present_why == ("the host's victory waits: "
                                       + BW.inject_verdict(BW.GUEST_OFF, True, BW.PHASE_NORMAL, True))
        assert st.coop_present_guest_mode == "off" and st.coop_present_r8_hits == 0 and st.commands_enabled


def test_w2_names_the_settle_seqs_blocker(game):
    """`endbench guest settle` injects SEQ_MENU_OFF_VICTORY, whose per-unit settle never completes in a bench diorama:
    phase 5 holds until W2 (8 s after the injection), which names the unsettled enemy and forces the no-pose half."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        _dio(g, fake)
        g.netsync("endbench", "guest", "settle")
        g.netsync("endbench", "victory")
        st = g.wait_for(lambda s: s.coop_present_injected, timeout=4.0, what="the injection")
        assert st.coop_present_inject_seq == BW.SEQ_MENU_OFF_VICTORY
        st = stays(g, lambda s: s.battle_phase == BW.PHASE_MENU_OFF, frames=60, what="the settle seq moved on")
        fake._nb.inject_rt -= 9.0                            # 8 s of stall, without spending them
        st = g.wait_for(lambda s: s.coop_present_watchdog == "W2", timeout=4.0, what="W2")
        assert st.coop_present_blocker.startswith("1 unsettled unit(s)") and _battle_text("unsettled unit(s) (SEQ_MENU")
        g.wait_for(lambda s: s.battle_phase == BW.PHASE_VICTORY and s.coop_present_r8_hits > 0, timeout=6.0,
                   what="the forced no-pose half to reach R8")


# --------------------------------------------------------------------------- battlewire: pinned to the engine

def _cs_int_consts(file_name: str) -> dict:
    """Every `const Byte|Int32 Name = <integer literal>` (several per line too) the live stack leaves in ``file_name``,
    with whether it is public."""
    out = {}
    for line in _stack_text(file_name):
        m = re.match(r"(public |private |internal )?const (?:Byte|Int32) (.*);", line)
        if not m:
            continue
        for decl in m.group(2).split(","):
            d = re.match(r"\s*(\w+) = (0x[0-9A-Fa-f]+|-?\d+)\s*$", decl)
            if d:
                out[d.group(1)] = (int(d.group(2), 0), (m.group(1) or "").strip() == "public")
    return out


def test_battlewire_constants_are_netsyncends():
    """Every integer constant the codec mirrors is NetSyncEnd's (by its C# name), and every PUBLIC integer constant
    NetSyncEnd declares is mirrored -- a constant added on either side turns this red."""
    cs = _cs_int_consts("NetSyncEnd.cs")
    for name, value in BW.CS_CONSTANTS.items():
        assert name in cs, name
        assert cs[name][0] == value, (name, cs[name][0], value)
    public = {n for n, (_v, pub) in cs.items() if pub}
    assert public <= set(BW.CS_CONSTANTS), sorted(public - set(BW.CS_CONSTANTS))
    acts = _cs_int_consts("NetSyncBattle.cs")
    assert {n: acts[n][0] for n in ("ActAttack", "ActDefend", "ActAbility", "ActItem", "ActInstant")} == \
        {"ActAttack": BW.ACT_ATTACK, "ActDefend": BW.ACT_DEFEND, "ActAbility": BW.ACT_ABILITY, "ActItem": BW.ACT_ITEM,
         "ActInstant": BW.ACT_INSTANT}
    assert acts["CapCommandPhaseGated"][0] == BW.CAP_COMMAND_PHASE_GATED
    # [ff9mapkit netsync R3 s111-s114] every NetSyncBattle constant battlewire mirrors, by name
    for name, value in BW.CS_BATTLE_CONSTANTS.items():
        if name in acts:
            assert acts[name][0] == value, (name, acts[name], value)
        else:                                               # (a declaration continued over lines: StartHoldStep's verdicts)
            assert any(re.search(rf"\b{name} = {value}[,;]", ln) for ln in _stack_text("NetSyncBattle.cs")), (name, value)
    assert _battle_text("public const Int32 FleeMsgShow = 0;")    # (its comment's `;` hides it from _cs_int_consts)


#: The stock constants the engine's SelfTest rows name (FF9StateBattleSystem / FF9StateGlobal) -> battlewire's.
_STOCK = {f"FF9StateBattleSystem.{n}": getattr(BW, n) for n in dir(BW) if n.startswith(("PHASE_", "SEQ_"))}
_STOCK.update({f"FF9StateGlobal.{n}": getattr(BW, n) for n in dir(BW) if n.startswith("BTL_RESULT_")})


def _cs_value(token: str) -> int:
    token = token.strip()
    if token in _STOCK:
        return _STOCK[token]
    if token in BW.CS_CONSTANTS:
        return BW.CS_CONSTANTS[token]
    return int(token, 0)


def test_classify_end_agrees_with_every_row_of_the_engines_selftest():
    """ClassifyEnd's Python twin against NetSyncEnd.SelfTest's OWN rows, read off the stack: every literal ExpectKind line,
    plus the two loops (the four fighting phases; victory seq 0..2) -- 23 rows, the engine's `classify 23`."""
    rows = []
    for line in _stack_text("NetSyncEnd.cs"):
        m = re.match(r"ExpectKind\(fails, ref classify, (.*)\);$", line)
        if m:
            rows.append([a.strip() for a in m.group(1).split(",")[:4]])   # phase, seq, result, want: no commas in them
    fighting = next(ln for ln in _stack_text("NetSyncEnd.cs") if ln.startswith("Byte[] fighting = {"))
    phases = [_cs_value(t) for t in re.search(r"\{(.*)\}", fighting).group(1).split(",")]
    assert any(ln == "for (Byte s = 0; s <= 2; s++)" for ln in _stack_text("NetSyncEnd.cs"))
    checked = 0
    for phase, seq, result, want in rows:
        if phase == "ph":
            for ph in phases:
                assert BW.classify_end(ph, _cs_value(seq), _cs_value(result)) == _cs_value(want), (ph, want)
                checked += 1
        elif seq == "s":
            for s in range(3):
                assert BW.classify_end(_cs_value(phase), s, _cs_value(result)) == _cs_value(want), (phase, s)
                checked += 1
        else:
            assert BW.classify_end(_cs_value(phase), _cs_value(seq), _cs_value(result)) == _cs_value(want), \
                (phase, seq, result, want)
            checked += 1
    assert checked == 23 == len(phases) + 3 + (len(rows) - 2), (checked, rows)


def test_present_action_agrees_with_the_engines_want_table():
    line = next(ln for ln in _stack_text("NetSyncEnd.cs") if ln.startswith("Int32[] wantAction = {"))
    want = [_cs_value(t) for t in re.search(r"\{(.*)\}", line).group(1).split(",")]
    assert [BW.present_action(k) for k in range(BW.K_FIGHTING, BW.K_EVENT + 1)] == want
    assert all(BW.present_action(k) == BW.PRESENT_NONE for k in (-1, 8, 255))
    assert all((BW.present_action(k) != BW.PRESENT_NONE) == BW.is_end_kind(k) for k in range(8))


def test_the_pure_decisions_hold_the_engines_pins():
    """The s103-s105 SelfTest PINS, restated against the Python twins (each pin's name is the engine's)."""
    # ChaseStep: none-is-never-chased, no-step-at-natural-EndEXPAndAP, the-host-fade-steps-the-tick-pages, end-steps-only-
    # to-hide, out of range
    assert not any(BW.chase_step(l, BW.RES_NONE, ld) for l in range(9) for ld in (False, True))
    assert not BW.chase_step(BW.RES_END_EXP, BW.RES_END_EXP, False) and not BW.chase_step(BW.RES_EXP_TICK, BW.RES_END_EXP, False)
    assert BW.chase_step(BW.RES_EXP_TICK, BW.RES_END_EXP, True) and BW.chase_step(BW.RES_END_EXP, BW.RES_END_EXP, True)
    assert BW.chase_step(BW.RES_END, BW.RES_HIDE, False) and not BW.chase_step(BW.RES_END, BW.RES_END, False)
    assert not BW.chase_step(BW.RES_HIDE, BW.RES_HIDE, False)
    assert not (BW.chase_step(0, -1, False) or BW.chase_step(0, 9, False) or BW.chase_step(-1, BW.RES_HIDE, False))
    assert sum(1 for l in range(9) for h in range(9) for ld in (0, 1) if BW.chase_step(l, h, bool(ld))) > 0
    for name in ("PIN none-is-never-chased", "PIN no-step-at-natural-EndEXPAndAP", "PIN end-steps-only-to-hide"):
        assert _battle_text(name), name
    # s104
    assert BW.close_result(BW.BTL_RESULT_VICTORY) == BW.BTL_RESULT_VICTORY_NO_POSE
    assert all(BW.close_result(r) == r for r in (0, 2, 4, 5, 7))
    assert BW.victory_seq(BW.GUEST_ON) == BW.victory_seq(BW.GUEST_OFF) == BW.SEQ_MENU_OFF_VICTORY_WITH_ENEMY
    assert BW.victory_seq(BW.GUEST_SETTLE) == BW.SEQ_MENU_OFF_VICTORY
    assert BW.inject_verdict(BW.GUEST_ON, True, BW.PHASE_NORMAL, True) is None
    assert all(BW.inject_verdict(BW.GUEST_ON, True, ph, True) for ph in (0, 1, 2, 3, 5, 6, 7, 8))
    assert BW.w1_due(6, 0, True, BW.W1_MS + 1) and not BW.w1_due(6, 0, True, BW.W1_MS) and not BW.w1_due(6, 0, False, 10 ** 6)
    assert BW.w2_due(5, BW.W2_MS + 1) and not BW.w2_due(5, BW.W2_MS) and not BW.w2_due(6, 10 ** 6)
    # s105
    for ui in range(5):
        for rs in range(19):
            res = BW.RES_NO_SCREEN if rs == 18 else (rs if rs < 9 else (rs - 9) | BW.RES_LOADING_BIT)
            want = ((BW.TRIGGER_RESULT_HIDE if res != BW.RES_NO_SCREEN and res & 0x7F == BW.RES_HIDE else 0)
                    if ui == 1 else BW.TRIGGER_GAME_OVER if ui == 2 else BW.TRIGGER_TITLE if ui == 3 else 0)
            assert BW.host_exit_trigger(ui, res) == want, (ui, res)
    for r in range(256):
        want = 1 if r in (1, 2) else r if r in (3, 4, 5, 7) else -1
        assert BW.stamp_result(r) == want and BW.stamp_for(r, True) == want
        assert BW.stamp_for(r, False) == (-1 if r == BW.BTL_RESULT_DEFEAT else want)
    for k in range(8):
        for ui in range(5):
            term = BW.is_end_kind(k) or 1 <= ui <= 3
            assert BW.is_terminal(k, ui) == term == BW.decline_late_join(k, ui, 9, 9, False)
            assert not BW.decline_late_join(k, ui, 9, 9, True) and not BW.decline_late_join(k, ui, 8, 9, False)
    assert BW.exit_verdict(0, True, False, False, BW.EXIT_RETRY_MS) == BW.EXIT_GO
    assert BW.exit_verdict(1, False, True, True, 0) == BW.EXIT_HELD_BY_LEVER
    assert BW.exit_verdict(0, True, True, True, 0) == BW.EXIT_IN_FLIGHT
    assert BW.exit_verdict(0, True, False, True, 0) == BW.EXIT_RATE_LIMITED
    assert BW.exit_verdict(0, True, False, True, BW.EXIT_RETRY_MS) == BW.EXIT_FADE_DEFER


def test_the_twins_say_the_engines_words():
    """Every reason a twin returns is a literal the stack carries (a spliced one, piece by piece)."""
    for v in range(6):
        if BW.exit_why(v) is not None:
            assert _battle_text(BW.exit_why(v)), v
    for ph in range(9):
        if ph != BW.PHASE_NORMAL:
            assert _battle_text(BW.phase_why(ph)), ph
    assert _battle_text(BW.MENU_DISABLED_WHY)
    for v in (BW.inject_verdict(BW.GUEST_OFF, True, 4, True), BW.inject_verdict(BW.GUEST_ON, False, 4, True),
              BW.inject_verdict(BW.GUEST_ON, True, 4, False)):
        assert _battle_text(v), v
    assert _battle_text("the diorama is in phase ") and _battle_text(", not its steady phase (")
    assert all(_battle_text(f'case {k}: return "{n}";') or _battle_text(f'return "{n}";')
               for k, n in BW.KIND_NAMES.items())
    for name in list(BW.TRIGGER_NAMES.values()) + list(BW.PRESENT_NAMES.values()):
        assert _battle_text(f'return "{name}";'), name


def test_the_trailer_codec_matches_the_engines_selftest_cases():
    """NetSyncEnd.ReadTrailer's Python twin over the SelfTest's codec cases: a full record round-trips; EVERY truncated
    prefix refuses the block (with the engine's reason); an unknown fmt is skipped by its len; foreign bytes and a short
    block refuse; a manifest is skipped by its len (flags b1); no trailer is (None, None)."""
    m = BW.make_block(BW.PHASE_CLOSE, 1, BW.BTL_RESULT_VICTORY_NO_POSE, ui=BW.UI_RESULT, state=BW.RES_START_GIL,
                      loading=True, flags=BW.FLAG_AFTER_EVENT | BW.FLAG_ESCAPE_GIL | BW.FLAG_FIELD_SONG, win_pose=0x0B)
    t = BW.encode_trailer(m)
    got, why, skipped = BW.read_trailer(t)
    assert {k: got[k] for k in m} == m and why is None and skipped == 0
    assert BW.read_trailer(b"") == (None, None, 0)
    for cut in range(1, len(t)):
        got, why, _ = BW.read_trailer(t[:cut])
        assert got is None and why and _battle_text(re.sub(r" \(.*$", "", why).replace("fmt-1 body", "fmt-")), (cut, why)
    # an UNKNOWN fmt is 0x7F, as the engine's own SelfTest row since s116 (fmt 2 is the flee record now: review R3H-5)
    unknown = bytes([BW.TRAILER_MAGIC, 0x7F, 0x03, 0x00, 0xAA, 0xBB, 0xCC])
    got, why, skipped = BW.read_trailer(unknown + t)
    assert got is not None and why is None and skipped == 1 and got["flee_gil"] == -1
    assert BW.read_trailer(unknown) == (None, None, 1)
    # ...and the old 0x02 bytes are a SHORT fmt-2 flee record (3 of 5 bytes): skipped and counted, the block kept
    short_flee = bytes([BW.TRAILER_MAGIC, BW.FMT_FLEE, 0x03, 0x00, 0xAA, 0xBB, 0xCC])
    got, why, skipped = BW.read_trailer(short_flee + t)
    assert got is not None and why is None and skipped == 1 and (got["flee_flags"], got["flee_gil"]) == (-1, -1)
    assert BW.read_trailer(bytes([0, 1, 2, 3, 4]))[1].startswith("foreign trailing bytes (0x00")
    assert BW.read_trailer(bytes([BW.TRAILER_MAGIC, BW.FMT_END, 5, 0, 1, 2, 3, 4, 5]))[1] == "short end block (5 of 8 byte(s))"
    manifest = bytes(0xE0 + i for i in range(13))
    got, why, _ = BW.read_trailer(BW.encode_trailer(m, manifest))
    assert got["flags"] & BW.FLAG_MANIFEST and got["manifest_len"] == 13 and why is None
    grown = bytearray(t) + b"\x77\x77"
    grown[2] = BW.END_BLOCK_LEN + 2                      # a later fmt-1 growth WITHOUT b1: skipped, block kept
    got, why, _ = BW.read_trailer(bytes(grown))
    assert got is not None and got["manifest_len"] == 0 and why is None
    assert BW.trail_entry(m) == "3/1/3L" and BW.block_text(m) == \
        "victory-no-pose (phase 8 seq 1 result 2; ui 1, res 3L, flags 0x19, pose 0x0B)"


def test_the_command_codec_and_the_bench_parsers_are_the_agents():
    """The v1 frame is EncodeCommand's (the engine's own default `endbench cmd` frame is slot 1 Attack at 0x10); the
    decoder refuses what TryDecodeCommand refuses; ArgHex / ArgMask accept and refuse what the agent does."""
    line = next(ln for ln in _stack_text("NetSyncEnd.cs") if "DefaultCmdFrame = {" in ln)
    default = bytes(int(t, 16) for t in re.search(r"\{(.*)\}", line).group(1).split(","))
    assert BW.encode_command(1, BW.ACT_ATTACK, mask=0x10) == default
    assert BW.command_hex(1, BW.ACT_ATTACK, mask=0x10) == "01 01 00 00 00 00 10 00 00"
    assert BW.decode_command(BW.encode_command(2, BW.ACT_ITEM, 4, 236, 0x0101, 1)) == \
        {"slot": 2, "action": 3, "menu": 4, "id": 236, "mask": 0x0101, "cursor": 1}
    assert BW.decode_command(default[:8]) is None and BW.decode_command(b"\x02" + default[1:]) is None
    assert BW.decode_command(default + b"\xff") == BW.decode_command(default)   # bytes past the ninth are ignored
    assert BW.control_hex(True) == "00 01" and BW.control_valid(b"\x00\x00") and not BW.control_valid(b"\x01\x00")
    assert not BW.control_valid(b"\x00")
    assert BW.parse_hex(["01", "0x02", "0304"]) == b"\x01\x02\x03\x04" and BW.parse_hex("01 01") == b"\x01\x01"
    for bad in ([], ["0"], ["zz"], ["0x"], ["01", "0"], ["1_0"]):
        assert BW.parse_hex(bad) is None, bad
    for text, want in (("2", 2), ("0x0F", 15), ("0XA", 10), ("+3", 3), ("15", 15), ("16", -1), ("-1", -1),
                       ("0x10", -1), ("x", -1), (None, -1), ("1.0", -1), ("0x", -1), ("0x-1", -1)):
        assert BW.parse_mask(text) == want, text


def test_the_stock_constants_are_the_engines_when_the_clone_is_here():
    """The stock phase/seq/result constants are not in the patch stack: read them off the shared Memoria clone when this
    machine has it (C:\\gd\\FFIX\\Memoria); elsewhere this pin is skipped, and the SelfTest-row test above still holds
    the kinds."""
    root = pathlib.Path(r"C:\gd\FFIX\Memoria\Assembly-CSharp\Global\ff9\State")
    files = [root / "Battle" / "FF9StateBattleSystem.cs", root / "FF9StateGlobal.cs"]
    if not all(f.is_file() for f in files):
        pytest.skip("the shared Memoria clone is not on this machine")
    text = "\n".join(f.read_text(encoding="utf-8-sig", errors="replace") for f in files)
    for name in [n for n in dir(BW) if n.startswith(("PHASE_", "SEQ_", "BTL_RESULT_"))]:
        m = re.search(rf"public const Byte {name} = (\d+);", text)
        assert m and int(m.group(1)) == getattr(BW, name), name


# =========================================================================== [ff9mapkit netsync B4/B5] s106-s110: battlewire
# The stages 7-11 codecs and pure decisions, pinned to the engine's own SelfTest lines (read off the stack and EVALUATED
# against the Python twins -- a mutant on either side turns a row red) and to the agent's words.

_CS_NAMES = dict(BW.CS_CONSTANTS, ResStart=BW.RES_START, ResExpTick=BW.RES_EXP_TICK, ResEndExp=BW.RES_END_EXP,
                 ResStartGil=BW.RES_START_GIL, ResItemFull=BW.RES_ITEM_FULL, ResGilTick=BW.RES_GIL_TICK, ResEnd=BW.RES_END,
                 ResHide=BW.RES_HIDE, ResNone=BW.RES_NONE, ok=BW.FLAG_MANIFEST, ExpCap=BW.EXP_CAP,
                 # [ff9mapkit netsync R3 s115-s117] the SelfTest sections' locals (SelfTestReplay's `won`, SelfTestFlee's /
                 # SelfTestDefeat's `esc`/`dft`/`gov`/`vic`/`ae`/`menuOff`/`pdef`/`close`/`fade`) and the stock names they use
                 won=BW.BTL_RESULT_VICTORY, esc=BW.BTL_RESULT_ESCAPE, dft=BW.BTL_RESULT_DEFEAT, gov=BW.BTL_RESULT_GAMEOVER,
                 vic=BW.BTL_RESULT_VICTORY, ae=BW.FLAG_MANIFEST | BW.FLAG_AFTER_EVENT | BW.FLAG_ESCAPE_GIL,
                 menuOff=BW.PHASE_MENU_OFF, pdef=BW.PHASE_DEFEAT, close=BW.PHASE_CLOSE, fade=BW.BTL_SONG_FADEOUT,
                 FleeMsgShow=BW.FLEE_MSG_SHOW, **_STOCK,
                 **{"UInt32.MaxValue": 2 ** 32 - 1, "Int32.MaxValue": 2 ** 31 - 1,
                    "battle.BTL_SONG_FADEOUT": BW.BTL_SONG_FADEOUT, "battle.BTL_PLAY_END_SONG": BW.BTL_PLAY_END_SONG,
                    "battle.BTL_END_LOAD": BW.BTL_END_LOAD})


def _t100(lv: int) -> int:
    """SelfTestManifest's / SelfTestReplay's synthetic level table: level L becomes L + 1 at 100 * L."""
    return 100 * lv


_TWINS = {"LevelAfter": BW.level_after, "ReplayLevel": BW.replay_level, "ArmVerdict": BW.arm_verdict,
          "FollowVerdict": BW.follow_verdict, "ExitWaitsForReplay": BW.exit_waits_for_replay,
          "SongVerdict": BW.song_verdict, "ReplayOverflow": BW.replay_overflow,
          # [ff9mapkit netsync R3 s115-s117]
          "PresentFor": BW.present_for, "NoLeakResult": BW.no_leak_result, "AnnihilateSettles": BW.annihilate_settles,
          "DefeatSongShuts": BW.defeat_song_shuts, "AllDown": BW.all_down, "FleeMsgVerdict": BW.flee_msg_verdict,
          "StampFor": BW.stamp_for}


def _cs_split(text: str) -> list:
    """A C# argument list split at its top-level commas."""
    out, depth, cur = [], 0, ""
    for ch in text:
        if ch == "," and depth == 0:
            out.append(cur)
            cur = ""
            continue
        depth += ch == "("
        depth -= ch == ")"
        cur += ch
    return out + [cur] if cur.strip() else out


def _cs_eval(tok: str):
    """One C# argument the SelfTest passes: a literal, a constant by name, `(Byte)(a | b)`, `Name - 1`, `t100`. KeyError
    = a token the twin cannot read (a loop variable): the row is skipped, never guessed."""
    tok = re.sub(r"^\(Byte\)", "", tok.strip()).strip()
    if tok.startswith("(") and tok.endswith(")"):
        tok = tok[1:-1].strip()
    if "|" in tok:
        v = 0
        for part in tok.split("|"):
            v |= _cs_eval(part)
        return v
    m = re.fullmatch(r"([\w.]+) - (\d+)", tok)
    if m:
        return _cs_eval(m.group(1)) - int(m.group(2))
    if tok in ("true", "false"):
        return tok == "true"
    if tok == "t100":
        return _t100
    if re.fullmatch(r"-?(0x[0-9A-Fa-f]+|\d+)u?", tok):
        return int(tok.rstrip("u"), 0)
    return _CS_NAMES[tok]


def _selftest_calls(name: str) -> list:
    """Every ``[!]Name(args)[ == want]`` in the stack's SelfTest assertions (lines that open an ``Expect(`` or continue one
    with ``&&``) -> ``(args text, want text | None, negated)``."""
    rows = []
    for line in _stack_text("NetSyncEnd.cs"):
        if not line.startswith(("Expect(fails, ref", "&& ")):
            continue
        for m in re.finditer(rf"(!?)\b{name}\(", line):
            depth, i = 1, m.end()
            while depth:
                depth += {"(": 1, ")": -1}.get(line[i], 0)
                i += 1
            want = re.match(r"\s*== ([\w.]+|-?\d+|0x[0-9A-Fa-f]+)", line[i:])
            rows.append((line[m.end():i - 1], want.group(1) if want else None, m.group(1) == "!"))
    return rows


@pytest.mark.parametrize("name,least", [("LevelAfter", 9), ("ReplayLevel", 7), ("ArmVerdict", 26), ("FollowVerdict", 14),
                                        ("ExitWaitsForReplay", 6), ("SongVerdict", 5), ("ReplayOverflow", 4),
                                        # [ff9mapkit netsync R3 s115-s117]
                                        ("PresentFor", 29), ("NoLeakResult", 18), ("AnnihilateSettles", 7),
                                        ("DefeatSongShuts", 9), ("AllDown", 5), ("FleeMsgVerdict", 11),
                                        ("StampFor", 6)])
def test_the_late_pure_decisions_agree_with_every_selftest_row(name, least):
    """s108/s109's pure halves -- LevelAfter, ReplayLevel, ArmVerdict, FollowVerdict, ExitWaitsForReplay, SongVerdict,
    ReplayOverflow -- against the engine SelfTest's OWN rows, evaluated (a row naming a loop variable is skipped; at
    least ``least`` are checked, so a stack that drops its pins cannot pass by checking nothing)."""
    twin, checked = _TWINS[name], 0
    for args, want, negated in _selftest_calls(name):
        try:
            vals = [_cs_eval(a) for a in _cs_split(args)]
            expected = _cs_eval(want) if want is not None else not negated
        except KeyError:
            continue
        assert twin(*vals) == expected, (name, args, want, negated)
        checked += 1
    assert checked >= least, (name, checked)


def test_level_after_holds_the_two_lambda_pins():
    """The two LevelAfter pins whose threshold is not t100 (restated: the cap bounds the final exp; the Byte guard)."""
    assert _battle_text("LevelAfter(1, 0, UInt32.MaxValue, 99, lv => lv < 3 ? 100u : ExpCap + 1) == 3")
    assert BW.level_after(1, 0, 2 ** 32 - 1, 99, lambda lv: 100 if lv < 3 else BW.EXP_CAP + 1) == 3
    assert _battle_text("LevelAfter(1, 0, 1000, 300, lv => 0u) == 255")
    assert BW.level_after(1, 0, 1000, 300, lambda lv: 0) == 255


def test_learn_schedule_agrees_with_every_expect_learns_row():
    """LearnSchedule's twin against each ExpectLearns row of SelfTestManifest (the pa[] it is given, the Slots triples,
    the gain, the capped flag and the (abil, apAt) pairs) -- and it never writes the pa[] it is given."""
    text = "\n".join(_stack_text("NetSyncEnd.cs"))
    rows = re.findall(r'ExpectLearns\(fails, ref n, "([^"]*)",\s*LearnSchedule\((pa|new Int32\[\] \{[^}]*\}), '
                      r'Slots\(([^)]*)\), (\d+), out cap\), cap, (true|false)((?:, -?\d+)*)\);', text)
    assert len(rows) == 13, len(rows)
    assert _battle_text("Int32[] pa = { 0, 0, 0 };")
    for name, pa_text, slots_text, gain, capped, pairs in rows:
        pa = [0, 0, 0] if pa_text == "pa" else [int(t) for t in re.search(r"\{([^}]*)\}", pa_text).group(1).split(",")]
        flat = [int(t) for t in slots_text.split(",")]
        slots = [tuple(flat[i:i + 3]) for i in range(0, len(flat), 3)]
        want = [int(t) for t in pairs.split(",")[1:]] if pairs else []
        before = list(pa)
        learns, cap = BW.learn_schedule(pa, slots, int(gain))
        assert [v for x in learns for v in (x["abil"], x["ap_at"])] == want and cap == (capped == "true"), name
        assert pa == before, name


def _full_manifest() -> dict:
    """SelfTestManifest's FULL manifest (every row 8 learns, 6 items -- exactly ManifestMaxBytes)."""
    rows = []
    for i in range(4):
        rows.append(BW.manifest_row(i * 3 + 1, flags=BW.ROW_NEED_EXP if i == 2 else BW.ROW_NEED_EXP | BW.ROW_NEED_AP
                                    | BW.ROW_DRAW, lv_before=10 + i, lv_after=12 + i, exp_before=0xFFFFFFF0 - i,
                                    exp_gain=0x80000001 + i, ap_gain=0xFFFE - i, status=0x8000000000000001 | (i << 20),
                                    learns=[(-7 if k == 0 else 100 + 10 * i + k, 0xFFFF if k == 7 else k + 1)
                                            for k in range(8)]))
    return BW.make_manifest(rows, default_exp=0xFFFFFFFF, default_ap=0xABCD, gil_gain=9999999, gil_before=0x01020304,
                            items=[(-1 if k == 0 else 200 + k, 255 if k == 5 else k + 1) for k in range(6)], card=99)


def _small_manifest() -> dict:
    """SelfTestManifest's SMALL manifest (the malformations are cut from it)."""
    return BW.make_manifest([BW.manifest_row(4, lv_before=7, lv_after=9, exp_gain=50, ap_gain=3, learns=[(12, 2)])],
                            items=[(236, 2)], card=5)


def test_the_manifest_codec_holds_the_engines_selftest_cases():
    """EncodeManifest / DecodeManifest's twins over SelfTestManifest's cases: the full manifest is exactly
    ManifestMaxBytes and round-trips; sparse rows keep their RAW slot; EVERY internal truncation drops the manifest and
    never the end block (`PIN a bad manifest never nulls the end block`); each malformation the encoder never writes is
    refused with the engine's reason; later growth is skipped; the encoder's caps; CapLearns keeps the earliest 8."""
    full = _full_manifest()
    fb = BW.encode_manifest(full)
    assert len(fb) == BW.MANIFEST_MAX_BYTES == 334
    assert _battle_text("+ ManifestTotalsLen + 1 + ManifestMaxItems * ManifestItemLen + 4;   // 334")
    got, why = BW.decode_manifest(fb)
    assert why is None and BW.same_manifest(got, full) and BW.encode_manifest(got) == fb
    blk = BW.make_block(BW.PHASE_VICTORY, 1, BW.BTL_RESULT_VICTORY, ui=BW.UI_RESULT, state=BW.RES_START,
                        flags=BW.FLAG_FIELD_SONG, win_pose=0x03)
    b, why, _ = BW.read_trailer(BW.encode_trailer(blk, fb))
    assert why is None and b["flags"] == BW.FLAG_FIELD_SONG | BW.FLAG_MANIFEST and b["manifest_len"] == 334
    assert BW.same_manifest(b["manifest"], full) and b["manifest_why"] is None
    sparse = BW.make_manifest({1: full["rows"][1], 3: full["rows"][2]}, gil_gain=5)
    got, _ = BW.decode_manifest(BW.encode_manifest(sparse))
    assert [r is not None for r in got["rows"]] == [False, True, False, True] and BW.manifest_row_mask(got) == 0x0A
    assert _battle_text('"PIN rows keep their RAW party slot (mask 0x0A)");')
    empty = BW.make_manifest([])
    assert BW.same_manifest(BW.decode_manifest(BW.encode_manifest(empty))[0], empty)
    kept = 0
    for cut in range(1, len(fb)):                           # every INTERNAL truncation: the block stands, the manifest goes
        b, why, _ = BW.read_trailer(BW.encode_trailer(blk, fb[:cut]))
        if b is not None and why is None and b["manifest"] is None and b["manifest_why"] and b["manifest_len"] == cut:
            kept += 1
    assert kept == len(fb) - 1 and _battle_text("PIN a bad manifest never nulls the end block (")
    frame = BW.encode_trailer(blk, fb)                      # every FRAME prefix cut inside it: the record overruns -- refused
    assert all(BW.read_trailer(frame[:cut])[0] is None for cut in range(len(frame) - len(fb), len(frame)))
    smb = BW.encode_manifest(_small_manifest())
    for at, value, reason in ((0, 0x11, "row mask 0x11 names a slot past 3"), (1 + 22, 9, "row 0 carries 9 learns (max 8)"),
                              (1 + 3, 6, "row 0's level goes down (7 -> 6)"),
                              (1 + BW.MANIFEST_ROW_LEN + BW.MANIFEST_LEARN_LEN + BW.MANIFEST_TOTALS_LEN, 7,
                               "7 items (max 6)")):
        bad = bytearray(smb) + bytearray(60)
        bad[at] = value
        got, why = BW.decode_manifest(bytes(bad))
        assert got is None and why == reason, (why, reason)
    assert BW.decode_manifest(b"") == (None, "flags b1 without a manifest body")
    assert BW.decode_manifest(smb[:5])[1] == "truncated row 0 (4 of 23 byte(s))"
    assert BW.decode_manifest(smb, 0, len(smb) + 1)[1] == "manifest range outside the frame"
    no_body = bytearray(BW.encode_trailer(blk))
    no_body[BW.RECORD_HEADER_LEN + 6] |= BW.FLAG_MANIFEST
    b, why, _ = BW.read_trailer(bytes(no_body))
    assert b is not None and b["manifest"] is None and b["manifest_why"] == "flags b1 without a manifest body"
    got, why = BW.decode_manifest(smb + b"\xEE" * 5)        # later growth past the card: skipped
    assert why is None and BW.same_manifest(got, _small_manifest())
    for literal in ("manifest range outside the frame", "flags b1 without a manifest body", " names a slot past 3",
                    "truncated row ", " of ", "'s level goes down (", " learns (max ", "truncated learns of row ",
                    "truncated totals (", " items (max ", "truncated items / card"):
        assert _battle_text(literal), literal
    too_many = BW.make_manifest([BW.manifest_row(1, learns=[(k + 1, 1) for k in range(9)])])
    with pytest.raises(ValueError, match="at most 8 learns"):
        BW.encode_manifest(too_many)
    with pytest.raises(ValueError, match="at most 6 items"):
        BW.encode_manifest(BW.make_manifest([], items=[(k, 1) for k in range(7)]))
    kept8, dropped = BW.cap_learns([{"abil": 50 + k, "ap_at": k + 1} for k in range(10)])
    assert dropped == 2 and len(kept8) == 8 and kept8[0]["abil"] == 50 and kept8[7]["abil"] == 57
    # the published shape round-trips (what a bench reads off host.manifest / peer.end.manifest)
    pub = BW.published_manifest(full)
    assert pub["row_mask"] == 0x0F and pub["rows"][0]["status"] == "0x8000000000000001" and pub["learn_count"] == 32
    assert BW.encode_manifest(BW.manifest_from_published(pub)) == fb
    assert list(pub) == ["row_mask", "rows", "default_exp", "default_ap", "gil_gain", "gil_before", "items", "card",
                         "learn_count", "truncated", "learn_capped"]
    for k in ("row_mask", "default_exp", "default_ap", "gil_gain", "gil_before", "card", "learn_count", "truncated"):
        assert net_lines("HarnessAgent.cs", rf'Num\(sb, "{k}", m\.'), k


def test_valid_row_mask_learns_due_and_the_fingerprint_hold_their_pins():
    """ValidRowMask (the SAME raw slot), LearnsDue (the (old, new] window; same-apAt learns in the row's order; each learn
    once across 1-AP steps) and FpMix (every single-bit change moves the hash; order-sensitive; zeros count) -- the
    SelfTestReplay pins restated, each pin's name read off the stack."""
    vm = BW.make_manifest({0: BW.manifest_row(0), 1: BW.manifest_row(7), 3: BW.manifest_row(2)})
    for seated, want in (([0, 7, 5, 2], "0x0B"), ([0, 1, 7, -1], "0x01"), ([-1, -1, -1, -1], "0")):
        assert _battle_text(f"ValidRowMask(vm, new Int32[] {{ {', '.join(map(str, seated))} }}) == {want}"), seated
        assert BW.valid_row_mask(vm, seated) == int(want, 0)
    assert BW.valid_row_mask(None, [0, 7, 5, 2]) == 0 and BW.valid_row_mask(vm, None) == 0
    assert BW.valid_row_mask(vm, [0]) == 0x01
    lr = BW.manifest_row(0, learns=[(31, 3), (32, 3), (33, 5)])
    assert BW.learns_due(lr, 0, 2) == [] and BW.learns_due(lr, 2, 3) == [31, 32]
    assert BW.learns_due(lr, 3, 3) == [] and BW.learns_due(lr, 3, 2) == [] and BW.learns_due(lr, 0, 5) == [31, 32, 33]
    assert sum(len(BW.learns_due(lr, ap, ap + 1)) for ap in range(8)) == 3 and BW.learns_due(None, 0, 9) == []
    base = BW.fp_mix(BW.fp_mix(BW.FP_SEED, 1234567), 0x0102030405060708)
    assert all(BW.fp_mix(BW.fp_mix(BW.FP_SEED, 1234567), 0x0102030405060708 ^ (1 << b)) != base for b in range(64))
    assert BW.fp_mix(BW.fp_mix(BW.FP_SEED, 7), 9) != BW.fp_mix(BW.fp_mix(BW.FP_SEED, 9), 7)
    assert BW.fp_mix(BW.FP_SEED, 0) != BW.FP_SEED and BW.fp_mix(BW.fp_mix(BW.FP_SEED, 0), 0) != BW.fp_mix(BW.FP_SEED, 0)
    assert _battle_text("public const UInt64 FpSeed = 14695981039346656037UL;") and BW.FP_SEED == 14695981039346656037
    assert _battle_text("private const UInt64 FpPrime = 1099511628211UL;") and BW.FP_PRIME == 1099511628211
    for pin in ("PIN the charId must match the SAME raw slot", "PIN same-apAt learns fire in the row's order",
                "PIN each learn fires exactly once across 1-AP steps", "PIN the fingerprint sees every single-bit change",
                "PIN the fingerprint is order-sensitive", "PIN zeros still count"):
        assert _battle_text(pin), pin


def test_the_replay_twins_say_the_engines_words():
    """Every reason arm_why / follow_why / song_why returns is the engine's literal (FollowRateLimited's spliced)."""
    for v in range(BW.ARM_GO, BW.ARM_NO_VALID_ROW + 1):
        why = BW.arm_why(v)
        assert (why is None) == (v == BW.ARM_GO) and (why is None or _battle_text(f'return "{why}";')), v
    for v in range(BW.FOLLOW_STEP, BW.FOLLOW_RATE_LIMITED + 1):
        why = BW.follow_why(v)
        if v == BW.FOLLOW_RATE_LIMITED:
            assert why == "this local state stepped less than 1500 ms ago"
            assert _battle_text('return "this local state stepped less than " + ReplayStepMs + " ms ago";')
        else:
            assert (why is None) == (v == BW.FOLLOW_STEP) and (why is None or _battle_text(f'return "{why}";')), v
    for v in (BW.SONG_HOST_KEEPS, BW.SONG_LOCAL_KEEPS):
        assert _battle_text(f'return "{BW.song_why(v)}";'), v
    assert BW.song_why(BW.SONG_SHUT) is None
    assert _battle_text("the replay's own hide tail already shut the songs (stage 10): nothing shut down twice")
    assert _battle_text("\" -- the replay's own hide tail kept it too (stage 10)\";")
    assert _battle_text("private const String ReplayExitWaitWhy = \"waiting for the result-screen replay to reach Hide "
                        "(its own hide tail; up to 5 s)\";")


def test_the_roster_codec_and_the_content_bits_are_the_engines():
    """The v1 type-4 roster's twin (ParseRoster / EncodeRoster / RosterSignature): the stage-7 bench note's raw-hex roster
    parses to Attack + Ability1 = WhiteMagicGarnet listing only Cure + a bag of M x77 and re-encodes byte for byte; the
    signature is stable across the round trip and moved by each field mutant; a version other than 1 and a truncation
    are refused, a trailing byte ignored. The content-hook bits, their names and the timing constants are the engine's."""
    raw = bytes.fromhex("01 01 00 02 00 01 00 00 00 00 02 11 00 01 00 01 01 00 01 01 01 01 00 EE 00 4D 01 00")
    r = BW.parse_roster(raw)
    assert r == {"slots": {0: [{"menu": 0, "cmd": 1, "type": 0, "target": 0, "abils": []},
                               {"menu": 2, "cmd": 17, "type": 1, "target": 0,
                                "abils": [{"id": 1, "mp": 1, "enabled": True, "for_dead": False, "target": 1}]}]},
                 "items": [{"id": 238, "count": 77, "target": 1, "for_dead": False}]}
    assert BW.encode_roster(r) == raw and BW.parse_roster(raw + b"\x99") == r
    sig = BW.roster_signature(r)
    assert sig == BW.roster_signature(BW.parse_roster(BW.encode_roster(r))) and sig != 0
    assert BW.roster_sig_text(r) == f"0x{sig:016X}" and BW.roster_sig_text(None) is None
    mutants = []
    for path, value in ((("slots", 0, 1, "cmd"), 22), (("slots", 0, 1, "menu"), 3), (("slots", 0, 1, "abils", 0, "mp"), 9),
                        (("slots", 0, 1, "abils", 0, "enabled"), False), (("items", 0, "count"), 76),
                        (("items", 0, "id"), 239)):
        m = BW.parse_roster(raw)
        node = m
        for k in path[:-1]:
            node = node[k]
        node[path[-1]] = value
        mutants.append(BW.roster_signature(m))
    assert sig not in mutants and len(set(mutants)) == len(mutants)
    assert BW.parse_roster(b"\x02" + raw[1:]) is None
    assert all(BW.parse_roster(raw[:c]) is None for c in range(1, len(raw)))
    assert BW.published_roster(r) == {
        "slots": [{"wire": 0, "cmds": [{"menu": 0, "cmd": 1, "type": 0, "abils": 0, "on": 0},
                                       {"menu": 2, "cmd": 17, "type": 1, "abils": 1, "on": 1}]}],
        "items": [{"id": 238, "count": 77}]}
    text = "\n".join(_stack_text("NetSyncBattle.StockMenu.cs"))
    m = re.search(r"public const Int32 ContentCommand = (\d+), ContentGrey = (\d+), ContentAbility = (\d+), ContentBag = "
                  r"(\d+), ContentCount = (\d+),\s*ContentCast = (\d+), ContentRefresh = (\d+), ContentAll = (\d+);", text)
    assert m and [int(v) for v in m.groups()] == [BW.CONTENT_COMMAND, BW.CONTENT_GREY, BW.CONTENT_ABILITY, BW.CONTENT_BAG,
                                                  BW.CONTENT_COUNT, BW.CONTENT_CAST, BW.CONTENT_REFRESH, BW.CONTENT_ALL]
    names = re.search(r"ContentNames = \{ ([^}]*) \};", text)
    assert names and tuple(re.findall(r'"(\w+)"', names.group(1))) == BW.CONTENT_NAMES
    consts = {**_cs_int_consts("NetSyncBattle.cs"), **_cs_int_consts("NetSyncBattle.StockMenu.cs")}
    for name, value in (("SampleMs", BW.SAMPLE_MS), ("StaleMs", BW.STALE_MS), ("MenuStaleMs", BW.MENU_STALE_MS),
                        ("MirrorRefuseMs", BW.MIRROR_REFUSE_MS), ("MirrorRefuseSeqs", BW.MIRROR_REFUSE_SEQS),
                        ("MirrorNoRosterMs", BW.MIRROR_NO_ROSTER_MS)):
        assert consts[name][0] == value, name
    assert BW.parse_content_mask("on") == 127 and BW.parse_content_mask("OFF") == 0 and BW.parse_content_mask("0x3F") == 63
    assert [BW.parse_content_mask(t) for t in ("128", "-1", "x", "", "0x", "0x80")] == [-1] * 6
    assert [BW.parse_bench_int(t, 15) for t in ("0x01", "3", "16", "", "0x", "-1")] == [1, 3, -1, -1, -1, -1]


# =========================================================================== [ff9mapkit netsync B4/B5] s106-s110: the stand-in
# The stages 7-11 behaviour cores on the stand-in, driven through the DRIVER: each leg of the solo benches the scenarios
# will run (studies/battle-coop/B4-B5-DESIGN.md 8.2), with its calibration lever's red. Not the engine: the solo benches
# against a live game are that proof.

def _root(g, slot: int = 0):
    """`bmenu open <slot>` and the stock command panel up for it."""
    g.netsync("bmenu", "open", slot)
    return g.wait_for(lambda s: s.turn_slot == slot and s.battle_hud and s.battle_hud["panel"] == "command", timeout=8.0,
                      what=f"the command panel for slot {slot}")


def _panel(g, panel: str):
    return g.wait_for(lambda s: s.battle_hud and s.battle_hud["panel"] == panel, timeout=8.0, what=f"the {panel} panel")


def _rows(st) -> dict:
    return {r["id"]: r for r in st.battle_hud["rows"]}


def _cmds(st) -> dict:
    return {c["menu"]: c for c in st.battle_hud["commands"]}


def _hits(st) -> dict:
    return dict(st.coop_content_hits)


def _delta(st, before: dict) -> dict:
    return {k: v - before[k] for k, v in st.coop_content_hits.items()}


def test_the_roster_fed_panels_draw_the_hosts_content(game):
    """s106 legs A-D and H on the stand-in: `bbench roster auto 0` fabricates the two markers (a command OUTSIDE the
    stand-in's preset in Ability1, its own Ability2 listing only an UNLEARNED entry, a bag of one item it owns 0 of); the
    mirrored slot's panels draw them -- the marker command, Change grey, the host's rows and MP, the host's bag and count
    -- and the commit forwards the host's item, never touching the guest's own bag; `roster clear` gives stock back."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        _dio(g, fake)
        st = g.netsync("bbench", "roster", "auto", 0)
        br = st.coop_menu_bench_roster
        assert (br["src"], br["slot"], br["wire"], br["marker_menu"], br["uk_menu"]) == ("auto", 0, 0, 2, 3)
        assert br["marker_cmd"] not in FakeGame.FAKE_PRESET and br["uk_cmd"] == FakeGame.FAKE_PRESET[3]
        assert br["marker_local_mp"] != 1 and br["count"] == 77 and br["note"] is None and fake.save_bag.get(br["item"], 0) == 0
        assert st.coop_menu_mirrored == [0] and st.coop_menu_roster_src == "bench"
        assert re.fullmatch(r"0x[0-9A-F]{16}", st.coop_menu_roster_sig) and st.coop_menu_roster["items"] == \
            [{"id": br["item"], "count": 77}]
        bag0, before = dict(fake.save_bag), _hits(st)
        st = _root(g)
        assert st.battle_hud_mirrored is True
        cmds = _cmds(st)
        assert (cmds[2]["id"], cmds[2]["label"], cmds[2]["state"]) == (br["marker_cmd"], "White Magic", 2)
        assert (cmds[5]["label"], cmds[5]["state"], cmds[5]["raw"]) == ("Change", 1, 1)
        assert _delta(st, before)["command"] > 0 and _delta(st, before)["grey"] > 0
        g.press("down", 4)
        g.press("confirm", 4)
        rows = _rows(_panel(g, "ability"))
        assert (rows[br["marker_shown"]]["state"], rows[br["marker_shown"]]["number"]) == (2, "1")
        assert rows[br["marker_grey"]]["state"] == 1
        assert all(r["state"] == 0 for i, r in rows.items() if i not in (br["marker_shown"], br["marker_grey"]))
        g.press("cancel", 4)
        g.press("right", 4)
        g.press("confirm", 4)
        st = g.wait_for(lambda s: s.battle_hud["panel"] == "ability" and br["unlearned"] in _rows(s), timeout=8.0,
                        what="the own command's list")
        rows = _rows(st)
        assert (rows[br["unlearned"]]["state"], rows[br["unlearned"]]["number"]) == (2, "1")
        assert rows[br["learned"]]["state"] == 0 and _delta(st, before)["ability"] > 0
        g.press("cancel", 4)
        g.press("down", 4)
        g.press("left", 4)
        g.press("confirm", 4)
        st = _panel(g, "item")
        assert [(r["id"], r["number"], r["state"]) for r in st.battle_hud["rows"]] == [(br["item"], "77", 2)]
        captures = st.coop_menu_captures
        g.press("confirm", 4)
        _panel(g, "target")
        stays(g, lambda s: s.battle_hud["panel"] == "target", frames=30, what="the target bounced (the count hook)")
        g.press("confirm", 4)
        st = g.wait_for(lambda s: s.coop_menu_captures == captures + 1, timeout=8.0, what="the capture")
        cap = st.coop_menu_captured
        assert {k: cap[k] for k in ("action", "id", "local_slot", "site")} == \
            {"action": BW.ACT_ITEM, "id": br["item"], "local_slot": 0, "site": "SendCommand"}
        assert st.coop_menu_r9_refused == 0 and fake.save_bag == bag0
        assert _delta(st, before)["bag"] > 0 and _delta(st, before)["count"] > 0
        # H: the roster cleared -- no mirrored slot, stock content on the reopened panel
        g.netsync("bmenu", "close", 0)
        st = g.netsync("bbench", "roster", "clear")
        assert st.coop_menu_mirrored == [] and st.coop_menu_roster_src == "" and st.coop_menu_bench_roster is None
        st = _root(g)
        assert st.battle_hud_mirrored is False and _cmds(st)[2]["label"] == "Steal" and _cmds(st)[5]["state"] == 2


@pytest.mark.parametrize("on_mask", [0, 126, 125, 123, 119, 111])
def test_each_content_lever_turns_its_own_hook_red(game, on_mask):
    """The stage-7 calibration lever (`bbench content <the hooks left ON>`): each mask turns exactly its hook's panel back
    to the stand-in's own -- 0 all of them (and no hook counts), 126 the marker command, 125 Change's grey, 123 the rows
    and the MP column, 119 the bag, 111 the count (picking the host's item bounces: the guest owns none)."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        _dio(g, fake)
        br = g.netsync("bbench", "roster", "auto", 0).coop_menu_bench_roster
        st = g.netsync("bbench", "content", on_mask)
        assert st.coop_menu_content_off == BW.CONTENT_ALL & ~on_mask
        before = _hits(st)
        st = _root(g)
        cmds = _cmds(st)
        assert (cmds[2]["id"] == br["marker_cmd"]) is bool(on_mask & BW.CONTENT_COMMAND)
        assert (cmds[5]["state"] == 1) is bool(on_mask & BW.CONTENT_GREY)
        g.press("down", 4)
        g.press("right", 4)
        g.press("confirm", 4)                               # the slot's OWN Ability2 (Skill): U / K
        st = g.wait_for(lambda s: s.battle_hud["panel"] == "ability", timeout=8.0, what="the own list")
        rows = _rows(st)
        if on_mask & BW.CONTENT_ABILITY:
            assert rows[br["unlearned"]]["state"] == 2 and rows[br["learned"]]["state"] == 0
        else:
            assert rows[br["unlearned"]]["state"] == 0 and rows[br["learned"]]["state"] == 2
        g.press("cancel", 4)
        g.press("down", 4)
        g.press("left", 4)
        g.press("confirm", 4)
        st = _panel(g, "item")
        ids = [r["id"] for r in st.battle_hud["rows"]]
        assert (ids == [br["item"]]) is bool(on_mask & BW.CONTENT_BAG) and (236 in ids) is not bool(on_mask & BW.CONTENT_BAG)
        if on_mask & BW.CONTENT_BAG:
            captures = st.coop_menu_captures
            g.press("confirm", 4)
            if on_mask & BW.CONTENT_COUNT:
                stays(g, lambda s: s.battle_hud["panel"] == "target", frames=30, what="a count bounce")
            else:
                g.wait_for(lambda s: s.battle_hud["panel"] == "item", timeout=8.0, what="the count bounce (the red)")
                g.press("confirm", 4)
                stays(g, lambda s: s.coop_menu_captures == captures, frames=20, what="a capture past the bounce")
        if on_mask == 0:
            assert all(v == 0 for v in _delta(g.state, before).values()), _delta(g.state, before)


def test_a_mirrored_double_cast_makes_one_pick_and_a_roster_change_repaints_the_open_panel(game):
    """s106 legs E and F, with the cast (95) and refresh (63) levers' reds: a double-cast marker on a mirrored slot is
    ONE pick -> one v1 frame (`double_cast` stays 0) -- the hook off, the second pick first; a roster change with the
    marker list open repaints its rows in place (number 9, greyed), one refresh, the generation painted -- the hook off,
    the open list keeps its old content until reopened."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        _dio(g, fake)
        br = g.netsync("bbench", "roster", "auto", 0, "dbl").coop_menu_bench_roster
        assert br["dbl"] is True and br["marker_cmd"] in FakeGame.FAKE_DOUBLE_CAST
        before = _hits(g.state)
        _root(g)
        g.press("down", 4)
        g.press("confirm", 4)
        _panel(g, "ability")
        captures = g.state.coop_menu_captures
        g.press("confirm", 4)
        _panel(g, "target")
        g.press("confirm", 4)
        st = g.wait_for(lambda s: s.coop_menu_captures == captures + 1, timeout=8.0, what="the single-cast capture")
        cap = st.coop_menu_captured
        assert (cap["action"], cap["menu"], cap["id"]) == (BW.ACT_ABILITY, br["marker_menu"], br["marker_shown"])
        assert _delta(st, before)["cast"] == 1
        # the cast lever (95): the stock second pick first
        g.netsync("bmenu", "close", 0)
        g.netsync("bbench", "content", 95)
        _root(g)
        g.press("down", 4)
        g.press("confirm", 4)
        _panel(g, "ability")
        g.press("confirm", 4)
        _panel(g, "target")
        g.press("confirm", 4)
        st = g.wait_for(lambda s: s.battle_hud["panel"] == "ability", timeout=8.0, what="the second pick (the red)")
        assert st.battle_hud["double_cast"] == 2 and st.coop_menu_captures == captures + 1
        g.press("confirm", 4)
        _panel(g, "target")
        g.press("confirm", 4)
        g.wait_for(lambda s: s.coop_menu_captures == captures + 2, timeout=8.0, what="the double-cast capture")
        # F: the repaint (bench change: close, a fresh roster, reopen, the marker list open)
        for refresh_on in (True, False):
            g.netsync("bmenu", "close", 0)
            g.netsync("bbench", "content", "on" if refresh_on else 63)
            g.netsync("bbench", "roster", "auto", 0)
            _root(g)
            g.press("down", 4)
            g.press("confirm", 4)
            st = _panel(g, "ability")
            assert _rows(st)[6]["number"] == "1"            # (the plain roster: White Magic's Cure)
            gen, refresh = st.coop_menu_roster_gen, st.coop_content_hits_refresh
            g.netsync("bbench", "roster", "auto", 0, "mp=9", "grey")
            st = g.wait_for(lambda s: s.coop_menu_roster_gen == gen + 1, timeout=8.0, what="the generation")
            st = stays(g, lambda s: s.battle_hud["panel"] == "ability", frames=6, what="the repaint moved the panel")
            row = _rows(st)[6]
            if refresh_on:
                assert (row["number"], row["state"]) == ("9", 1) and st.coop_content_hits_refresh == refresh + 1
            else:
                assert (row["number"], row["state"]) == ("1", 2) and st.coop_content_hits_refresh == refresh
            assert st.coop_menu_roster_painted == st.coop_menu_roster_gen and st.coop_menu_mute_held is False


def _fed_dio(g, fake, *, roster: int = 0, offer: str = "0x01"):
    """A diorama seating two live players, the bench roster for local slot ``roster`` and the s107 bench feed offering
    ``offer`` (wire slots) -- the lane live, nothing Ready yet."""
    fake.dio_units = [dict(u) for u in BENCH_UNITS]
    _dio(g, fake)
    g.netsync("bbench", "roster", "auto", roster)
    g.netsync("bbench", "start", offer)
    return g.wait_for(lambda s: s.coop_peer_live, timeout=8.0, what="the feed's lane")


def test_the_ready_mirror_opens_the_stock_menu_on_the_wire_bit_and_the_bench_host_answers(game):
    """s107 legs A-D on the stand-in: a wire Ready bit opens the STOCK command menu on its local seat (the digit panel
    stays off it); an accepted commit drops the bit and the mirror closes the slot; a refused one is reopened at the root
    after 2.5 s and 3 samples; the bit falling with the target panel open closes it, capturing nothing."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        st = _fed_dio(g, fake)
        assert (st.coop_peer_caps, st.coop_peer_ready_mask, st.coop_stock_owns, st.coop_stock_why) == (2, 0, True, "")
        assert st.coop_mirror_serving and st.turn_slot == -1 and st.coop_assist_slot == -1
        assert st.coop_feed["menu_open"] is False and st.coop_feed["live"] is True
        fed = st.coop_mirror_fed
        g.netsync("bbench", "ready", "0x01")
        st = g.wait_for(lambda s: s.turn_slot == 0, timeout=8.0, what="A: the stock menu on the wire bit")
        assert st.coop_peer_ready_mask == 1 and 0 in st.battle["turn"]["ready"] and st.battle_hud["panel"] == "command"
        assert st.coop_mirror_open == 1 and st.coop_mirror_fed == fed + 1 and st.coop_assist_slot == -1
        assert st.coop_feed["menu_open"] is True
        sent, accepted = st.coop_stock_sent, st.coop_mirror_accepted
        g.press("confirm", 4)
        g.press("confirm", 4)
        st = g.wait_for(lambda s: s.coop_mirror_accepted == accepted + 1, timeout=8.0, what="B: accepted")
        assert {k: st.coop_menu_captured[k] for k in ("slot", "action", "mask")} == {"slot": 0, "action": 0, "mask": 0x10}
        assert st.coop_stock_sent == sent + 1 and st.coop_feed["accepted"] == 1 and st.coop_feed["ready"] == 0
        assert st.coop_peer_ready_mask == 0 and st.coop_pending is None and st.turn_slot == -1
        assert 0 not in st.battle["turn"]["ready"] and 0 not in st.battle["turn"]["done"]
        stays(g, lambda s: s.turn_slot == -1, frames=60, what="B: reopened with the bit down")
        g.netsync("bbench", "ready", "0x01")
        g.wait_for(lambda s: s.turn_slot == 0, timeout=8.0, what="B: reopened")
        # C: refused -- pending, then the buzzer and the root again
        g.netsync("bbench", "mode", "refuse")
        refused = g.state.coop_mirror_refused
        g.press("confirm", 4)
        g.press("confirm", 4)
        st = g.wait_for(lambda s: s.coop_pending is not None, timeout=8.0, what="C: pending")
        assert st.coop_pending["slot"] == 0 and st.coop_pending["ms"] < 2500 and st.turn_slot == -1
        assert st.coop_mirror_refused == refused
        st = g.wait_for(lambda s: s.coop_mirror_refused == refused + 1, timeout=15.0, what="C: refused")
        st = g.wait_for(lambda s: s.turn_slot == 0, timeout=8.0, what="C: the root again")
        assert st.coop_pending is None and st.coop_feed["refused"] == 1
        # D: the bit falls with the target panel open
        g.netsync("bbench", "mode", "accept")
        captures, closed = st.coop_menu_captures, st.coop_mirror_closed
        g.press("confirm", 4)
        _panel(g, "target")
        g.netsync("bbench", "ready", 0)
        st = g.wait_for(lambda s: s.turn_slot == -1, timeout=8.0, what="D: closed")
        assert st.battle_hud["panel"] == "none" and 0 not in st.battle["turn"]["ready"]
        assert st.coop_mirror_closed == closed + 1 and st.coop_menu_captures == captures


def test_the_ready_mirror_stands_down_strands_and_follows_the_end(game):
    """s107 legs E-K on the stand-in (and the `knob 0` red): a frozen lane goes stale and the mirror closes everything
    (the bench roster rides the lane: `mirrored` empties); caps without bit 1 hand the slot to the digit panel; a Ready
    slot the roster does not carry waits; an unseated one is stranded; the knob off is the pre-stage guest; the host's
    victory closes the menu for good; the feed ends with its diorama."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        _fed_dio(g, fake)
        g.netsync("bbench", "ready", 1)
        g.wait_for(lambda s: s.turn_slot == 0, timeout=8.0, what="open")
        g.netsync("bbench", "freeze", 1)
        stays(g, lambda s: s.turn_slot == 0, frames=30, what="E: closed before the lane went stale")
        st = g.wait_for(lambda s: s.coop_peer_live is False, timeout=15.0, what="E: stale")
        st = g.wait_for(lambda s: s.turn_slot == -1, timeout=8.0, what="E: closed all")
        assert st.coop_feed["live"] is False and st.coop_menu_mirrored == [] and st.coop_stock_owns is False
        assert st.coop_stock_why == "no live peer battle lane" and _battle_text('why = "no live peer battle lane";')
        g.netsync("bbench", "freeze", 0)
        g.wait_for(lambda s: s.turn_slot == 0, timeout=8.0, what="E: thawed")
        g.netsync("bbench", "caps", 0)
        st = g.wait_for(lambda s: s.turn_slot == -1, timeout=8.0, what="F: caps 0")
        assert (st.coop_stock_owns, st.coop_stock_why, st.coop_assist_slot) == \
            (False, "host predates the command-phase gates", 0)
        g.netsync("bbench", "caps", 2)
        g.wait_for(lambda s: s.turn_slot == 0, timeout=8.0, what="F: caps 2")
        # G: the roster carries only wire slot 1
        g.netsync("bbench", "roster", "auto", 1)
        g.netsync("bbench", "start", "0x03")
        g.netsync("bbench", "ready", "0x01")
        st = g.wait_for(lambda s: s.coop_mirror_no_roster == 1, timeout=8.0, what="G: waiting for the roster")
        assert st.turn_slot == -1 and st.coop_assist_slot == -1
        # (AssistSlot runs BEFORE StockMenuTick, so the digit panel takes a stranded slot a frame later -- as the engine)
        g.wait_for(lambda s: s.coop_stranded == [0] and s.coop_assist_slot == 0, timeout=15.0,
                   what="G2: stranded after 2.5 s, the digit panel's")
        g.netsync("bbench", "ready", "0x02")
        st = g.wait_for(lambda s: s.turn_slot == 1, timeout=8.0, what="G: the right slot")
        assert st.coop_mirror_open == 2
        closed = st.coop_mirror_closed
        g.netsync("bbench", "unmap", 1)
        st = g.wait_for(lambda s: s.turn_slot == -1 and s.coop_assist_slot == 1, timeout=8.0, what="H: unmapped")
        assert st.coop_stranded == [1] and st.coop_mirror_closed == closed + 1
        g.netsync("bbench", "unmap", "none")
        g.wait_for(lambda s: s.turn_slot == 1, timeout=8.0, what="H: unmapped none")
        st = g.netsync("bbench", "knob", 0)
        st = g.wait_for(lambda s: s.turn_slot == -1, timeout=8.0, what="I: knob 0")
        assert st.coop_stock_owns is False and st.coop_assist_slot == 1 and st.coop_stock_knob == 0
        assert st.coop_stock_why == "the knob is off ([Netsync] GuestStockMenu=0, the bench override)"
        assert st.coop_stock_knob_bench == 0
        g.netsync("bbench", "knob", "ini")
        g.wait_for(lambda s: s.turn_slot == 1, timeout=8.0, what="I: knob ini")
        g.netsync("endbench", "victory")
        st = g.wait_for(lambda s: s.coop_present_injected, timeout=8.0, what="J: the injection")
        st = stays(g, lambda s: s.turn_slot == -1, frames=60, what="J: reopened after the end")
        assert st.coop_stock_why.startswith("waiting: the diorama is in phase") and st.coop_mirror_open == 0
        g.netsync("endbench", "clear")
        g.netsync("dioleave")
        st = g.wait_for(lambda s: not s.diorama_booted, timeout=15.0, what="K: the teardown")
        assert st.coop_feed is None and st.coop_peer_live is False


def test_knob_0_is_the_pre_stage_guest(game):
    """s107's calibration: `bbench knob 0` is exactly the pre-stage-8 guest -- the wire bit opens nothing, the digit
    panel serves the slot, the mirror never feeds; `knob ini` and the bit opens the stock menu."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        _fed_dio(g, fake)
        g.netsync("bbench", "knob", 0)
        fed = g.state.coop_mirror_fed
        g.netsync("bbench", "ready", 1)
        st = stays(g, lambda s: s.turn_slot == -1, frames=60, what="the knob-off guest opened the stock menu")
        assert st.coop_assist_slot == 0 and st.coop_mirror_fed == fed and st.coop_menu_captures == 0
        g.netsync("bbench", "knob", "ini")
        g.wait_for(lambda s: s.turn_slot == 0, timeout=8.0, what="the knob back")


def test_endbench_manifest_presets_ride_the_bench_end_through_the_codec(game):
    """s108 leg B on the stand-in: preset 1 is the TWO-MARKER manifest built from the seated party (gil 1234567 + 4321,
    an item and a card the save holds 0 of, row 0 two level-ups + Poison + one learn at apAt 3, apGain 5 everywhere);
    3 the same with every char id foreign; 2 escape with gil (flags b3); 0 none; 4 refused. The bench writes nothing."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(FIELD)
        g.netsync("selftest", 1)
        save0 = (fake.save_gil, dict(fake.save_bag), dict(fake.save_cards), [dict(p) if p else None for p in fake.save_party])
        fp0 = g.state.coop_replay_fp
        g.netsync("endbench", "manifest", 1)
        g.netsync("endbench", "ui", 1)
        st = g.netsync("endbench", "state", 0)
        e, m = st.coop_peer_end, st.coop_peer_end_manifest
        seated = [p for p in fake.save_party if p]
        assert e["bench"] is True and e["flags"] & BW.FLAG_MANIFEST and e["manifest_len"] > 0 and e["manifest_why"] is None
        assert e["rows"] == len(seated) == len(m["rows"]) and st.coop_peer_bench_manifest == 1
        assert st.coop_peer_bench_manifest_note == ""
        assert (m["gil_before"], m["gil_gain"]) == (1234567, 4321)
        assert len(m["items"]) == 1 and m["items"][0]["count"] == 7 and fake.save_bag.get(m["items"][0]["id"], 0) == 0
        assert fake.save_cards.get(m["card"], 0) == 0 and m["card"] != BW.CARD_NONE
        r0 = m["rows"][0]
        assert r0["lv_after"] == r0["lv_before"] + 2 and int(r0["status"], 16) & BW.STATUS_POISON
        assert r0["learns"] == [{"abil": 31, "ap_at": 3}] and all(r["ap_gain"] == 5 for r in m["rows"])
        assert [(r["char"], r["exp_before"], r["lv_before"]) for r in m["rows"]] == \
            [(p["char"], p["exp"], p["level"]) for p in seated]
        assert e["manifest_len"] == len(BW.encode_manifest(BW.manifest_from_published(m)))
        st = g.netsync("endbench", "manifest", 3)
        assert all(r["char"] not in {p["char"] for p in seated} for r in st.coop_peer_end_manifest["rows"])
        st = g.netsync("endbench", "manifest", 2)
        m = st.coop_peer_end_manifest
        assert st.coop_peer_end["flags"] & BW.FLAG_ESCAPE_GIL and m["gil_gain"] == 321 and m["items"] == []
        assert m["card"] == BW.CARD_NONE and all(r["exp_gain"] == 0 and r["ap_gain"] == 0 for r in m["rows"])
        st = g.netsync("endbench", "manifest", "none")
        assert st.coop_peer_end_manifest is None and not st.coop_peer_end["flags"] & BW.FLAG_MANIFEST
        assert st.coop_peer_end["manifest_len"] == 0 and st.coop_peer_end["rows"] == 0
        assert not st.coop_peer_end["flags"] & BW.FLAG_ESCAPE_GIL and st.coop_peer_bench_manifest == 0
        with pytest.raises(HarnessError, match=r"needs 0 \(none\), 1 \(two-marker\)"):
            g.netsync("endbench", "manifest", 4)
        st = g.netsync("endbench", "clear")
        assert st.coop_peer_end is None and st.coop_replay_fp == fp0
        assert save0 == (fake.save_gil, dict(fake.save_bag), dict(fake.save_cards), [dict(p) if p else None for p in fake.save_party])
        # the lever: off reads back, the stand-in's host captures nothing either way (no reward screen of its own)
        st = g.netsync("endbench", "manifest", "host", "off")
        assert st.coop_host_manifest_mode == "off" and st.coop_host_manifest is None and st.coop_host_manifest_captures == 0


def _replay_ready(g, fake, *, preset=1, fresh=True):
    """R1 steps 1-4: a diorama, the preset's manifest, the host's victory presented and R8 holding -- not armed yet."""
    _dio(g, fake, fresh=fresh)
    g.netsync("endbench", "manifest", preset)
    g.netsync("endbench", "victory")
    return g.wait_for(lambda s: s.coop_present_injected and s.coop_present_r8_hits > 0, timeout=15.0, what="R8")


def test_the_result_replay_follows_the_host_and_writes_nothing(game):
    """s109 leg R1 on the stand-in: armed only once the host is on its result screen (verdict 5 before); the stock screen
    opens on the HOST's manifest, ignores the guest's own Confirm, steps only when the host's state moves (the trail),
    runs the level-ups and the scheduled learn, the gil page, the host's overflow, and closes through its OWN hide tail
    while the end-leave waits -- the fingerprint never moves, in the diorama or after the warm return."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(FIELD)
        fp0 = g.state.coop_replay_fp
        _replay_ready(g, fake, fresh=False)
        st = g.wait_for(lambda s: s.coop_replay_verdict == BW.ARM_NOT_ON_SCREEN, timeout=8.0, what="R1.4: verdict 5")
        fp1 = st.coop_replay_fp
        assert fp1 == fp0 and st.coop_replay_armed is False
        assert st.coop_replay_why == BW.arm_why(BW.ARM_NOT_ON_SCREEN)
        m = st.coop_peer_end_manifest
        g.netsync("endbench", "ui", 1)
        st = g.wait_for(lambda s: s.coop_replay_opened, timeout=8.0, what="R1.5: opened")
        assert (st.coop_replay_verdict, st.coop_replay_host_state_at_arm, st.coop_replay_bench) == (BW.ARM_GO, 0, True)
        assert st.coop_replay_row_mask == st.coop_replay_seated_mask and st.coop_replay_manifest_rows == len(m["rows"])
        ui = st.battle_result_ui
        assert st.battle_result_replay is True and ui["state"] == 0
        assert ui["labels"]["exp"] == str(m["default_exp"]) and ui["labels"]["ap"] == str(m["default_ap"])
        for r in m["rows"]:
            row = ui["rows"][r["slot"]]
            assert row["shown"] and row["level"] == str(r["lv_before"]) and row["exp"] == str(r["exp_before"])
            assert row["dim"] is (not r["draw"])
        for _ in range(3):
            g.press("confirm", 4)
        st = stays(g, lambda s: s.coop_replay_screen["state"] == 0, frames=60, what="R1.6: a local Confirm stepped it")
        assert st.coop_replay_screen["steps"] == 0 and st.coop_replay_screen["local_confirms"] >= 3
        g.netsync("endbench", "state", 1)
        st = g.wait_for(lambda s: s.coop_replay_screen["state"] == BW.RES_END_EXP, timeout=8.0, what="R1.7: the tick")
        sc, k = st.coop_replay_screen, m["rows"][0]["slot"]
        assert sc["steps"] == 1 and sc["trail"] == ["0>1"]
        assert next(r for r in sc["rows"] if r["slot"] == k)["level"] == m["rows"][0]["lv_after"]
        assert st.battle_result_ui["rows"][k]["level_ups"] == 2
        assert sc["learned"] == [{"slot": k, "abil": m["rows"][0]["learns"][0]["abil"], "ap": 3}]
        g.netsync("endbench", "state", 2)
        st = stays(g, lambda s: s.coop_replay_screen["steps"] == 1, frames=30, what="R1.8: stepped at a natural end")
        assert st.coop_replay_screen["follow"] == BW.FOLLOW_IN_STEP
        g.netsync("endbench", "state", 2, "loading")
        st = g.wait_for(lambda s: s.coop_replay_screen["state"] == BW.RES_START_GIL and not s.battle_result_ui["loading"],
                        timeout=8.0, what="R1.9: page 2")
        ui, sc = st.battle_result_ui, st.coop_replay_screen
        assert sc["steps"] == 2 and sc["trail"][1] == "2>2L"
        assert (ui["labels"]["gil_receive"], ui["labels"]["gil_current"]) == ("4321", "1234567")
        assert [(i["id"], i["count"], i["shown"]) for i in ui["items"]] == [(m["items"][0]["id"], 7, True)]
        assert ui["card_shown"] is True and sc["gil"] == 1234567 and ui["model"]["party_gil"] == fp0["gil"]
        g.netsync("endbench", "overflow", 1)
        g.netsync("endbench", "state", 4)
        st = g.wait_for(lambda s: s.coop_replay_screen["state"] == BW.RES_ITEM_FULL, timeout=8.0, what="R1.10")
        assert st.coop_replay_screen["overflow_shown"] and st.coop_replay_screen["steps"] == 3
        g.netsync("endbench", "state", 5)
        g.wait_for(lambda s: s.coop_replay_screen["state"] >= BW.RES_GIL_TICK, timeout=8.0, what="R1.11")
        g.netsync("endbench", "state", 6)
        st = g.wait_for(lambda s: s.coop_replay_screen["state"] == BW.RES_END, timeout=8.0, what="R1.12")
        assert st.coop_replay_screen["gil"] == 1238888
        assert st.coop_replay_fp["hash"] == fp1["hash"] and st.coop_replay_screen["writes"] == 0   # R1.14, in-diorama
        returns = st.diorama_returns
        g.netsync("endbench", "state", 7)
        st = g.wait_for(lambda s: s.diorama_returns == returns + 1, timeout=15.0, what="R1.13: the warm return")
        assert st.coop_exit_trigger == "result-hide" and st.coop_replay_closed and not st.coop_replay_aborted
        assert st.coop_replay_screen["trail"][-1] == "6>7" and st.coop_replay_exit_waited
        assert 0 <= st.coop_replay_exit_wait_ms < BW.REPLAY_EXIT_WAIT_MS
        assert st.coop_exit_music_why.startswith("the replay's own hide tail already shut the songs")
        assert st.coop_exit_wipe_lifted is False and st.coop_exit_music_shut is False and st.battle_result == 1
        assert st.coop_replay_fp == fp0 and st.coop_replay_screen["writes"] == 0


def test_the_replay_quit_guard_refusal_abort_and_negatives(game):
    """s109 legs R2-R5 on the stand-in: the guest's own quit prompt holds every host step (follow 3) until Cancel closes
    it; a manifest no seated member matches is REFUSED (verdict 10, no screen); a leave mid-tick aborts the replay (the
    settle then shuts the song and the teardown lifts the fade); AfterEvent (7) and no manifest (8) never arm."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        _replay_ready(g, fake)
        g.netsync("endbench", "ui", 1)
        g.wait_for(lambda s: s.coop_replay_opened, timeout=8.0, what="R2: opened")
        g.netsync("endbench", "quit", "on")
        g.netsync("endbench", "state", 1)
        st = stays(g, lambda s: s.coop_replay_screen["state"] == 0 and s.coop_replay_screen["steps"] == 0, frames=120,
                   what="R2: a host step answered the quit prompt")
        assert st.coop_replay_screen["follow"] == BW.FOLLOW_QUIT and st.battle_result_ui["paused"] is True
        g.press("cancel", 4)                                # NEVER Confirm: its Yes quits
        g.wait_for(lambda s: s.coop_replay_screen["steps"] == 1, timeout=8.0, what="R2: stepped once the prompt closed")
        # R4: a leave mid-tick
        g.netsync("dioleave")
        st = g.wait_for(lambda s: not s.diorama_booted, timeout=15.0, what="R4: the teardown")
        assert st.coop_replay_aborted and st.coop_replay_abort_why == "a leave of the diorama"
        assert st.coop_replay_screen["aborted"] and st.coop_exit_music_shut and st.coop_exit_wipe_lifted
        g.wait_for(lambda s: s.control, timeout=8.0, what="control back")
        # R3: foreign char ids -- refused
        g.netsync("endbench", "clear")
        _dio(g, fake, fresh=False)
        g.netsync("endbench", "manifest", 3)
        g.netsync("endbench", "victory")
        g.wait_for(lambda s: s.coop_present_r8_hits > 0, timeout=15.0, what="R3: R8")
        g.netsync("endbench", "ui", 1)
        st = g.wait_for(lambda s: s.coop_replay_refused, timeout=8.0, what="R3: refused")
        assert st.coop_replay_verdict == BW.ARM_NO_VALID_ROW and not st.coop_replay_opened
        assert st.battle_result_ui is None
        returns = st.diorama_returns
        g.netsync("endbench", "state", 7)
        g.wait_for(lambda s: s.diorama_returns == returns + 1, timeout=15.0, what="R3: the clean leave")


@pytest.mark.parametrize("lever,verdict", [(("afterevent", 1), BW.ARM_AFTER_EVENT), (("manifest", 0), BW.ARM_NO_MANIFEST),
                                           (("replay", "off"), BW.ARM_HELD_BY_LEVER)])
def test_a_replay_negative_never_arms(game, lever, verdict):
    """s109 R5 and the `replay off` red: AfterEvent (7), no manifest (8) and the lever (1) leave the guest black at R8 --
    nothing arms, no result screen."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        _replay_ready(g, fake)
        g.netsync("endbench", *lever)
        g.netsync("endbench", "ui", 1)
        st = g.wait_for(lambda s: s.coop_replay_verdict == verdict, timeout=8.0, what="the verdict")
        st = stays(g, lambda s: not s.coop_replay_armed and s.battle_result_ui is None, frames=60,
                   what="a negative armed the replay")
        assert st.coop_replay_why == BW.arm_why(verdict)


def test_replay_local_is_the_seam_c_red_and_still_writes_nothing(game):
    """`endbench replay local`: the guest's OWN Confirm steps the replay (local_steps), the host-step counter stays 0 --
    and every reward writer stays closed (writes 0, the fingerprint unchanged)."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(FIELD)
        fp0 = g.state.coop_replay_fp
        _replay_ready(g, fake, fresh=False)
        g.netsync("endbench", "replay", "local")
        g.netsync("endbench", "ui", 1)
        g.wait_for(lambda s: s.coop_replay_opened, timeout=8.0, what="opened")
        g.press("confirm", 4)
        st = g.wait_for(lambda s: s.coop_replay_screen["local_steps"] == 1, timeout=8.0, what="the local step")
        assert st.coop_replay_screen["steps"] == 0 and st.coop_replay_screen["state"] >= BW.RES_EXP_TICK
        assert st.coop_replay_screen["writes"] == 0 and st.coop_replay_fp == fp0


def _own_battle_two(g, fake):
    """A selftest OWN battle (two players, gauges full, nothing resolves), slot 1 the loopback guest's (`guestslots 2`),
    slot 0 committed (Defend) so the host's window is free -- slot 1 Ready on the wire."""
    g.newgame(settle=0)
    g.warp(FIELD)
    g.netsync("selftest", 1)
    g.netsync("guestslots", 2)
    _bench_battle(fake)
    st = g.wait_for(lambda s: s.commands_enabled and s.coop_peer_ready_mask is not None and s.coop_peer_ready_mask & 2,
                    timeout=8.0, what="slot 1 Ready")
    if st.turn_slot == 0:
        g.press("right", 4)
        g.press("confirm", 4)                               # Defend
    return g.wait_for(lambda s: s.turn_slot == -1 and 1 in s.battle["turn"]["ready"], timeout=8.0, what="the idle HUD")


def test_a_stalled_guest_slot_is_handed_back_at_the_root_and_waits_in_a_submenu(game):
    """s110 legs A-C on the stand-in: `bench lapse hold` silences the loopback guest -- after MenuStaleMs the host's own
    window captures slot 1 and G6 withholds its Ready bit; `bench lapse end` hands it back at the command root within a
    frame or so (it stays Ready, not done); with the window in a submenu the hand-back WAITS (counted once) and the host's
    own pick commits; C2: a Cancel back to the root hands back at once."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        st = _own_battle_two(g, fake)
        assert st.coop_slot_handback is True and st.coop_handback_held == -1 and st.coop_handback_off is False
        captures = st.coop_handback_captures
        st = g.netsync("bench", "lapse", "hold")
        assert st.coop_lapse_active and st.coop_lapse_hold and st.coop_lapse_left_ms == -1
        st = g.wait_for(lambda s: s.turn_slot == 1, timeout=15.0, what="A: the capture")
        assert st.coop_handback_held == 1 and st.coop_handback_captures == captures + 1 and st.coop_handback_owed is False
        assert not st.coop_host_ready_mask & 2 and st.coop_handback_g6_mask & 2 and not st.coop_peer_ready_mask & 2
        returns = st.coop_handback_returns
        st = g.netsync("bench", "lapse", "end")
        st = g.wait_for(lambda s: s.coop_handback_returns == returns + 1, timeout=8.0, what="B: the hand-back")
        last = st.coop_handback_last
        assert (last["slot"], last["why"]) == (1, "handed back") and 0 <= last["frame"] - st.coop_lapse_end_frame <= 3
        st = stays(g, lambda s: s.turn_slot != 1, frames=3, what="B: the window reopened on slot 1")
        assert 1 in st.battle["turn"]["ready"] and 1 not in st.battle["turn"]["done"] and st.coop_handback_held == -1
        st = g.wait_for(lambda s: s.coop_host_ready_mask & 2, timeout=8.0, what="B: the bit back")
        # C: the window in a submenu -- the hand-back waits, the host's own pick commits
        g.netsync("bench", "lapse", "hold")
        g.wait_for(lambda s: s.turn_slot == 1, timeout=15.0, what="C: the capture")
        g.press("down", 4)
        g.press("right", 4)
        g.press("confirm", 4)                               # Skill -> the ability list
        _panel(g, "ability")
        deferred, returns = g.state.coop_handback_deferred, g.state.coop_handback_returns
        g.netsync("bench", "lapse", "end")
        st = stays(g, lambda s: s.turn_slot == 1 and s.coop_handback_returns == returns, frames=30,
                   what="C: handed back from a submenu")
        assert st.coop_handback_deferred == deferred + 1 and st.coop_handback_owed is True
        assert st.coop_handback_last["why"] == "deferred: the host's window is in a submenu (Battle.Ability)"
        assert _battle_text('return "the host\'s window is in a submenu (" + group + ")";')
        g.press("confirm", 4)
        _panel(g, "target")
        g.press("confirm", 4)
        st = g.wait_for(lambda s: 1 in s.battle["turn"]["done"], timeout=8.0, what="C: the host's own pick")
        assert st.turn_slot != 1 and st.coop_handback_returns == returns and st.coop_handback_deferred == deferred + 1


def test_the_handback_lever_and_the_guestslots_change(game):
    """s110 leg D (the `bench handback 0` red: the capture still counts, but G6 never withholds and nothing hands back --
    `owed` stays true; `bench handback 1` hands back on the next tick) and the stand-in leg both DLLs share: the host's
    window holding slot 1 while it is NOT a guest slot, then `guestslots 2` -- a hold by "a GuestSlots change", handed
    back at once."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        _own_battle_two(g, fake)
        st = g.netsync("bench", "handback", 0)
        assert st.coop_handback_off is True
        captures, returns = st.coop_handback_captures, st.coop_handback_returns
        g.netsync("bench", "lapse", "hold")
        st = g.wait_for(lambda s: s.turn_slot == 1, timeout=15.0, what="D: the capture")
        assert st.coop_handback_captures == captures + 1 and st.coop_host_ready_mask & 2 and st.coop_handback_g6_mask == 0
        g.netsync("bench", "lapse", "end")
        st = stays(g, lambda s: s.turn_slot == 1 and s.coop_handback_returns == returns, frames=30,
                   what="D: handed back under the lever")
        assert st.coop_handback_owed is True
        g.netsync("bench", "handback", 1)
        st = g.wait_for(lambda s: s.coop_handback_returns == returns + 1, timeout=8.0, what="D: the lever back")
        assert st.turn_slot != 1
    fake = FakeGame(game)
    with session(game, fake) as g:
        _own_battle_two(g, fake)
        g.netsync("guestslots", 0)
        st = g.wait_for(lambda s: s.turn_slot == 1, timeout=8.0, what="the host's window on slot 1")
        assert not st.coop_host_ready_mask & 2                  # G6: whichever unit the host's window holds
        captures, returns = st.coop_handback_captures, st.coop_handback_returns
        g.netsync("guestslots", 2)
        st = g.wait_for(lambda s: s.coop_handback_returns == returns + 1, timeout=8.0, what="the hand-back")
        assert st.coop_handback_captures == captures + 1 and st.turn_slot != 1
        assert _battle_text("(a GuestSlots change)")


@pytest.mark.parametrize("level", ["s105", "s106", "s108", "s109"])
def test_the_stand_ins_battle_doc_grows_as_the_agents_does(game, level):
    """`battle.hud` gains `mirrored` right after `shown` at s106 (AppendBattleHud), `battle.result_ui` the screen's own
    view (labels, card_shown, model, rows, items) at s108 and `replay` right after `paused` at s109 (AppendResultUi) --
    the stand-in publishes each exactly from its patch on, in the agent's order (each line read off its patch)."""
    assert net_lines("HarnessAgent.cs", r'Bool\(sb, "mirrored", v\.Mirrored\)', [_patch_bytes("s106")])
    assert net_lines("HarnessAgent.cs", r'sb\.Append\(",\\"labels\\":\{"\);', [_patch_bytes("s108")])
    assert net_lines("HarnessAgent.cs", r'Bool\(sb, "replay", Try\(\(\) => r\.NetIsReplay, false\)\);',
                     [_patch_bytes("s109")])
    fake = FakeGame(game)
    fake.netsync_caps = _caps_at(level)
    fake.start_battle(67, debug=True)
    fake.commands_enabled = True
    hud = list(fake._battle_doc()["hud"])
    stock = ["group", "panel", "shown", "slot", "menu", "cmd", "sub", "double_cast", "cursor_type", "target_cursor",
             "trance_menu", "manual_trance", "auto", "hiding", "main_menu", "can_force_next", "force_next", "caption",
             "commands", "rows"]
    assert hud == (stock[:3] + ["mirrored"] + stock[3:] if int(level[1:]) >= 106 else stock), hud
    for key in stock + ["mirrored"]:                         # each one a key the agent's AppendBattleHud writes
        assert net_lines("HarnessAgent.cs", rf'\(sb, "{key}", ') or key in ("commands", "rows"), key
    fake.ui_state = "BattleResult"
    ui = list(fake._battle_doc()["result_ui"])
    want = ["state", "loading", "paused"] + (["replay"] if int(level[1:]) >= 109 else []) \
        + (["labels", "card_shown", "model", "rows", "items"] if int(level[1:]) >= 108 else [])
    assert ui == want, ui


# =========================================================================== [ff9mapkit netsync R3] s111-s117
# Battle co-op round 3 (studies/battle-coop/R3-DESIGN.md 5.2): the driver's gates for the new `bench` named ops, the
# `dioboot` tokens, `battle ... rand` and the new `endbench` ops / values; battlewire's control codec, the guest's report,
# the host's hold decision and the flee / defeat decisions, pinned to the engine's own SelfTest rows and words; and the
# stand-in's behaviour core for each stage (the solo benches against a live game are the engine's proof).

R3_BENCH_OPS = [("intro", ("0",), "s111"), ("cfg", ("skipcam", "0"), "s111"), ("swirl", ("clamp", "-1"), "s112"),
                ("waitparity", ("0",), "s113"), ("ctl", ("deep",), "s113"), ("boot", ("booting",), "s114"),
                ("starthold", ("0",), "s114")]


@pytest.mark.parametrize("op,args,patch", R3_BENCH_OPS, ids=[r[0] for r in R3_BENCH_OPS])
def test_an_r3_bench_op_is_never_sent_to_an_engine_that_reads_it_as_bench_1(game, op, args, patch):
    """THE HAZARD, once per R3 named op: the engine before its patch parses `bench <op> ...` as `bench 1` (Arg's fallback)
    and turns the FIELD-GATE bench ON. The driver probes the op's key first and refuses before the step; the stand-in at
    that older level reproduces the hazard; the patch's own engine takes it."""
    _attr, key, at, _what = Session.NETSYNC_BENCH_OPS[op]
    assert at == patch
    before = f"s{int(patch[1:]) - 1}"
    fake = FakeGame(game)
    fake.netsync_caps = _caps_at(before)
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.netsync("selftest", 1)
        n = len(fake.executed)
        with pytest.raises(HarnessError, match=rf"^netsync bench {op}: the deployed engine publishes no "
                                               rf"`{re.escape(key)}` .*\(memoria-patch {patch}\); an engine before it "
                                               rf"reads `bench {op}` as `bench 1`"):
            g.netsync("bench", op, *args)
        assert len(fake.executed) == n and g.state.netsync["bench"] is False
        fake._netsync(["bench", op, *args])                 # what that engine would DO with it
        assert fake.netsync["bench"] is True
    fake = FakeGame(game)
    fake.netsync_caps = _caps_at(patch)
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.netsync("selftest", 1)
        st = g.netsync("bench", op, *args)
        assert fake.executed[-1] == ["netsync", "bench", op, *args] and st.netsync["bench"] is False


def test_dioboot_tokens_and_battle_rand_are_refused_on_an_engine_that_ignores_them(game):
    """s111: an engine before it IGNORES `dioboot`'s trailing tokens (a manual boot, its own intro) and `battle`'s third
    argument (a non-random battle) -- a silent wrong action. The driver refuses both before the step; a plain `dioboot
    <scene> [pattern]` and a non-random `start_battle` still go."""
    fake = FakeGame(game)
    fake.netsync_caps = _caps_at("s110")
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(FIELD)
        g.netsync("selftest", 1)
        n = len(fake.executed)
        for args in ((67, 0, "skip"), (67, "play"), (67, 0, "wire"), (67, "rand")):
            with pytest.raises(HarnessError, match=r"^netsync dioboot: the deployed engine publishes no "
                                                   r"`netsync\.diorama\.intro` -- the tokens .*memoria-patch s111"):
                g.netsync("dioboot", *args)
        with pytest.raises(HarnessError, match=r"^start_battle\(rand=True\): the deployed engine publishes no "
                                               r"`netsync\.diorama\.intro`"):
            g.start_battle(67, rand=True)
        assert len(fake.executed) == n
        fake._netsync(["dioboot", "67", "0", "skip"])       # what the s110 engine does: a manual boot, its own intro
        assert fake._nb.d_wire == -1 and "intro" not in fake._diorama_doc()


def test_an_r3_endbench_value_or_op_is_refused_before_the_step_on_an_older_engine(game):
    """`endbench guest hold|nor9b` (s115) rides an op s104 already had: an s114 engine answers "needs on|off|settle"
    after the step; `fleegil` (s116) and `kill` / `phase-defeat` (s117) are "unknown op" there. The driver names each
    patch, key and answer first."""
    for level, args, patch, answer in (
            ("s114", ("guest", "hold"), "s115", "netsync endbench guest: needs on|off|settle"),
            ("s114", ("guest", "nor9b"), "s115", "netsync endbench guest: needs on|off|settle"),
            ("s115", ("fleegil", "77"), "s116", "netsync endbench: unknown op 'fleegil'"),
            ("s116", ("kill",), "s117", "netsync endbench: unknown op 'kill'"),
            ("s116", ("phase-defeat",), "s117", "netsync endbench: unknown op 'phase-defeat'")):
        fake = FakeGame(game)
        fake.netsync_caps = _caps_at(level)
        with session(game, fake) as g:
            g.newgame(settle=0)
            g.netsync("selftest", 1)
            n = len(fake.executed)
            with pytest.raises(HarnessError, match=rf"^netsync endbench {args[0]}.*\(memoria-patch {patch}\); it would "
                                                   rf"answer \"{re.escape(answer)}"):
                g.netsync("endbench", *args)
            assert len(fake.executed) == n, (level, args)
            with pytest.raises(RuntimeError, match=rf"^{re.escape(answer)}"):
                fake._netsync(["endbench", *args])          # ...what that engine itself says
            st = g.netsync("endbench", "guest", "settle")   # an older value still goes
            assert st.coop_present_guest_mode == "settle"


R3_REFUSALS = [
    ("netsync bench cfg skipcam: expected 0|1|restore (0 = skip the intro camera on a random encounter)",
     ["bench", "cfg", "skipcam", "2"], "selftest"),
    ("netsync bench cfg atb: expected wait|active|restore (the per-save ATB mode: Wait = 1, Active = 0)",
     ["bench", "cfg", "atb", "turbo"], "selftest"),
    ("netsync bench cfg: unknown setting '", ["bench", "cfg", "speed", "5"], "selftest"),
    ("netsync bench swirl local: expected <0-", ["bench", "swirl", "local", "1801"], "selftest"),
    ("netsync bench swirl clamp: expected <0-", ["bench", "swirl", "clamp", "-2"], "selftest"),
    ("netsync bench swirl: unknown setting '", ["bench", "swirl", "own", "0"], "selftest"),
    ("netsync bench ctl: expected auto|shut|legacy|root|deep (the control byte 1 a Ready loopback / feed guest sends)",
     ["bench", "ctl", "half"], "selftest"),
    ("netsync bench boot: expected auto|none|booting|live|declined|busy|stale|silent|late <ms>",
     ["bench", "boot", "soon"], "selftest"),
    ("netsync bench boot late: needs <ms> 0-600000 (no control frame until that long after the host's command ",
     ["bench", "boot", "late", "x"], "selftest"),
    ("netsync bench boot ", ["bench", "boot", "live", "5"], "selftest"),
    (": takes no argument", ["bench", "boot", "live", "5"], "selftest"),
    ("netsync bench starthold cap: expected 0-600000 ms, or ini (back to [Netsync] StartHoldMs = ",
     ["bench", "starthold", "cap", "600001"], "selftest"),
    ("netsync bench starthold: expected 1|0|cap <ms>|cap ini", ["bench", "starthold", "2"], "selftest"),
    ("netsync bench lapse: `reserve` has no loopback control frame to re-serve -- arm it inside an own battle ",
     ["bench", "lapse", "hold", "reserve"], "selftest"),
    ("netsync endbench guest: needs on|off|settle|hold|nor9b", ["endbench", "guest", "x"], "selftest"),
    ("netsync endbench kill: needs a booted battle diorama (`netsync dioboot <scene>`)", ["endbench", "kill"], "selftest"),
    ("netsync endbench kill: needs the diorama in PHASE_NORMAL (phase ", ["endbench", "kill", "1"], "intro"),
    ("netsync endbench kill: no linked player's btl_id is in mask 0x", ["endbench", "kill", "8"], "dio"),
]


@pytest.mark.parametrize("fragment,args,where", R3_REFUSALS, ids=[r[0][:40] for r in R3_REFUSALS])
def test_the_stand_in_refuses_the_r3_ops_in_the_agents_words(game, fragment, args, where):
    """Every R3 gate the stand-in models refuses with the agent's own words (each fragment one literal of the stack)."""
    assert _battle_text(fragment), f"the live stack no longer says {fragment!r}"
    fake = FakeGame(game)
    fake.field_id = FIELD
    if where == "selftest":
        _selftest(fake)
    elif where == "dio":
        _dio_fake(fake)
    elif where == "intro":
        _dio_fake(fake)
        fake.commands_enabled = False
        fake._intro_until = fake.frame + 1000               # the diorama still in its opening camera (PHASE_ENTER)
    with pytest.raises(RuntimeError) as err:
        fake._netsync(args)
    assert fragment in str(err.value), str(err.value)


R3_ARGUMENT_REFUSALS = [
    ("netsync bench intro", ["bench", "intro", "2"]), ("netsync bench intro", ["bench", "intro"]),
    ("netsync bench cfg", ["bench", "cfg", "skipcam"]), ("netsync bench waitparity", ["bench", "waitparity", "x"]),
    ("netsync bench ctl", ["bench", "ctl"]), ("netsync bench boot", ["bench", "boot"]),
    ("netsync bench starthold", ["bench", "starthold"]), ("netsync bench swirl", ["bench", "swirl", "local"]),
    ("netsync bench lapse", ["bench", "lapse", "end", "reserve"]), ("netsync bench lapse", ["bench", "lapse", "5", "x"]),
    ("netsync endbench fleegil", ["endbench", "fleegil", "-1"]), ("netsync endbench fleegil", ["endbench", "fleegil"]),
    ("netsync endbench kill", ["endbench", "kill", "16"]), ("netsync endbench kill", ["endbench", "kill", "0"]),
    ("netsync endbench phase-defeat", ["endbench", "phase-defeat", "1"]),
]


@pytest.mark.parametrize("param,args", R3_ARGUMENT_REFUSALS, ids=[f"{r[0]}-{i}" for i, r in enumerate(R3_ARGUMENT_REFUSALS)])
def test_an_r3_argument_refusal_has_the_engines_whole_shape(game, param, args):
    """The R3 argument parses are ArgumentOutOfRangeExceptions with Mono's whole shape (``message CRLF Parameter name:
    param``): the `bench` ops parse after `bench`'s role gate, `endbench`'s before any gate."""
    agent = {}
    for line in net_lines("HarnessAgent.cs", r'ArgumentOutOfRangeException\("netsync (bench|endbench) '):
        lit = _literals(line)
        agent.setdefault(lit[0], lit[1])
    assert param in agent, sorted(agent)
    fake = FakeGame(game)
    if args[0] == "bench":
        _selftest(fake)
    with pytest.raises(RuntimeError) as err:
        fake._netsync(args)
    assert str(err.value) == f"{agent[param]}\r\nParameter name: {param}", repr(str(err.value))


def test_dioboot_and_battle_refuse_a_bad_token_in_the_agents_shape(game):
    """s111's spliced refusals: `dioboot`'s unknown token (after the scene check), `wire rand`, and `battle`'s third
    argument -- each the agent's literals around the token."""
    tok = net_lines("HarnessAgent.cs", r'expected `netsync dioboot <scene> \[pattern\] \[wire\] \[skip\|play\|own\] \[rand\]`, got')
    wire = net_lines("HarnessAgent.cs", r"`wire` boots the wire bench, whose header is always a random encounter")
    bat = net_lines("HarnessAgent.cs", r'expected `battle <scene> \[group\] \[rand\|1\|0\]`, got')
    assert len(tok) == 1 and len(wire) == 1 and len(bat) == 1, (tok, wire, bat)
    fake = _on_field(FakeGame(game))
    fake.field_id = FIELD
    _selftest(fake)
    with pytest.raises(RuntimeError) as err:
        fake._netsync(["dioboot", "67", "0", "later"])
    assert str(err.value) == f"{_literals(tok[0])[1]}later'\r\nParameter name: netsync dioboot"
    with pytest.raises(RuntimeError) as err:
        fake._netsync(["dioboot", "67", "wire", "rand"])
    assert str(err.value) == f"{_literals(wire[0])[1]}\r\nParameter name: netsync dioboot"
    with pytest.raises(RuntimeError) as err:
        fake._execute(["battle", "67", "-1", "random"])
    assert str(err.value) == f"{_literals(bat[0])[1]}67 -1 random'\r\nParameter name: battle"


# ---- battlewire, pinned to the engine

def _control_selftest_rows(fn: str) -> list:
    """NetSyncBattle.ControlSelfTest's `Row(<fn>(...) == <want>, ...)` lines, read off the stack."""
    rows = []
    for line in _stack_text("NetSyncBattle.cs"):
        m = re.match(rf"Row\({fn}\((.*?)\) == (\w+), \"([^\"]+)\"", line)
        if m:
            rows.append((m.group(1), m.group(2), m.group(3)))
    return rows


def test_guest_boot_state_agrees_with_every_control_selftest_row():
    """GuestBootState's twin against ControlSelfTest's OWN rows (nonce N = 0x41), evaluated -- the BUSY row included."""
    names = dict(BW.CS_BATTLE_CONSTANTS, N=0x41, true=True, false=False)

    def val(tok):
        tok = tok.strip()
        m = re.fullmatch(r"(\w+) - (\d+)", tok)
        if m:
            return names[m.group(1)] - int(m.group(2))
        return names[tok] if tok in names else int(tok)

    rows = _control_selftest_rows("GuestBootState")
    assert len(rows) == 9, rows
    for args, want, name in rows:
        assert BW.guest_boot_state(*[val(a) for a in args.split(",")]) == names[want], name
    assert {r[2] for r in rows} >= {"boot busy", "boot skip", "boot manual", "boot older+watching"}


def test_the_control_codec_and_its_nonce_gate_hold_the_engines_pins():
    """BuildControl / DecodeControl (ControlSelfTest's codec rows, restated): the 5-byte report, the byte-1 nonce gate (a
    report about ANOTHER battle reads shut), a 2-byte frame (no trailer, byte 1 ungated), an unknown fmt and a short
    trailer (trailer-less), malformed frames; and the pre-R3 bool shape `control_hex(True)` = "00 01"."""
    n = 0x41
    f = BW.encode_control(BW.CTL_DEEP, n, BW.BOOT_LIVE)
    assert f == bytes([0, 3, 1, 0x41, 2]) and BW.control_hex(BW.CTL_DEEP, n, BW.BOOT_LIVE) == "00 03 01 41 02"
    assert BW.decode_control(f, n) == {"menu": 3, "trailer": True, "nonce": n, "boot": BW.BOOT_LIVE}
    assert BW.decode_control(BW.encode_control(BW.CTL_DEEP, n - 1, BW.BOOT_LIVE), n) == \
        {"menu": BW.CTL_SHUT, "trailer": True, "nonce": n - 1, "boot": BW.BOOT_LIVE}            # the nonce gate
    assert BW.decode_control(bytes([0, 2]), n) == {"menu": 2, "trailer": False, "nonce": -1, "boot": -1}
    assert BW.decode_control(bytes([0, 3, 9, n - 1, 2]), n)["menu"] == 3                         # unknown fmt
    assert BW.decode_control(bytes([0, 3, 1, n - 1]), n) == {"menu": 3, "trailer": False, "nonce": -1, "boot": -1}
    assert BW.decode_control(bytes([1, 2]), n) is None and BW.decode_control(None, n) is None
    assert BW.decode_control(bytes([0]), n) is None
    assert BW.control_hex(True) == "00 01" and BW.control_hex(False) == "00 00" and BW.control_hex(2) == "00 02"
    with pytest.raises(ValueError):
        BW.encode_control(2, nonce=5)
    for name in ("encode", "decode", "nonce gate", "2-byte frame", "unknown fmt ignored", "short trailer", "malformed"):
        assert _battle_text(f'"{name}", ref rows, ref fail'), name
    # the wire intro and the own battle's caps (s111/s114)
    assert [BW.wire_intro(f) for f in (0, 1, 2, 3, 4, 8, 9, 0x0C, 0x0D, 0x0E, 0x1E)] == [-1, -1, -1, -1, -1, 0, 0, 1, 1, 1, 1]
    assert BW.own_battle_caps(True, True, skipped=True) == 0x0F and BW.own_battle_caps(True, False) == 0x0A
    assert BW.own_battle_caps(True, True, intro_on=False) == 0x03 and BW.own_battle_caps(False, False, holding=True) == 0x18
    assert BW.own_intro_skipped(0, True) and not BW.own_intro_skipped(1, True) and not BW.own_intro_skipped(0, False)
    assert BW.remote_menu_deep(True, BW.CTL_DEEP) and BW.remote_menu_deep(True, BW.CTL_LEGACY)
    assert BW.remote_menu_deep(True, 9) and not BW.remote_menu_deep(True, BW.CTL_ROOT)
    assert BW.remote_menu_deep(True, BW.CTL_ROOT, parity_on=False) and not BW.remote_menu_deep(False, BW.CTL_DEEP)
    assert BW.swirl_frames(115, True, 0) == 0 and BW.swirl_frames(115, True, -1) == 115
    assert BW.swirl_frames(115, False, 0) == 115 and BW.swirl_frames(30, True, 60) == 30


def _hold(steps) -> list:
    """Run StartHoldStep over ``steps`` (now, on, cap, phaseOpen, rptThis, rptBoot, nullSeen, legacyLast) from a fresh
    state; the verdicts."""
    h = BW.new_hold_state()
    return [BW.start_hold_step(h, *s) for s in steps], h


def test_start_hold_step_holds_every_control_selftest_row():
    """StartHoldStep / HoldGate restated row by row from ControlSelfTest (each row's name is the engine's): arm at the
    opening, live releases, released-then-paused is final, the stale-nonce LIVE releases only by the cap, a 2-byte frame
    never holds, silence never primes, a late arm, busy / link / old-guest releases, the intro follows the report, off
    never holds / releases, and the spent cap never re-holds."""
    B, L, D, BU = BW.BOOT_BOOTING, BW.BOOT_LIVE, BW.BOOT_DECLINED, BW.BOOT_BUSY
    v, h = _hold([(0, True, 8000, False, True, B, False, False), (100, True, 8000, True, True, B, False, False)])
    assert v == [BW.HOLD_PRIMED, BW.HOLD_ARMED] and h["started"] and h["since_tick"] == 100
    assert BW.start_hold_step(h, 1200, True, 8000, True, True, L, False, False) == BW.HOLD_REL_LIVE and h["released"]
    assert BW.start_hold_step(h, 1300, True, 8000, False, True, B, False, False) == BW.HOLD_NOTHING
    assert BW.start_hold_step(h, 1400, True, 8000, True, True, B, False, False) == BW.HOLD_NOTHING and h["released"]
    v, h = _hold([(0, True, 3000, True, True, B, False, False), (1000, True, 3000, True, False, L, False, False),
                  (2999, True, 3000, True, False, L, False, False), (3000, True, 3000, True, False, L, False, False)])
    assert v == [BW.HOLD_ARMED, BW.HOLD_NOTHING, BW.HOLD_NOTHING, BW.HOLD_REL_CAP]
    v, h = _hold([(0, True, 8000, False, False, -1, False, True), (100, True, 8000, True, False, -1, False, True),
                  (1099, True, 8000, True, False, -1, False, True), (1100, True, 8000, True, False, -1, False, True)])
    assert v == [BW.HOLD_NOTHING, BW.HOLD_NOT_ARMED, BW.HOLD_NOTHING, BW.HOLD_LATE_PASSED]
    assert not h["armed"] and h["released"]
    v, h = _hold([(0, True, 8000, False, False, -1, False, False), (100, True, 8000, True, False, -1, False, False),
                  (400, True, 8000, True, True, B, False, False)])
    assert v == [BW.HOLD_NOTHING, BW.HOLD_NOT_ARMED, BW.HOLD_LATE_ARMED] and h["late_ms"] == 300 and h["since_tick"] == 400
    for rpt_this, boot, null, legacy, want in ((True, BU, False, False, BW.HOLD_REL_DECLINED),
                                                (True, D, False, False, BW.HOLD_REL_DECLINED),
                                                (True, B, True, False, BW.HOLD_REL_LINK),
                                                (False, -1, False, True, BW.HOLD_REL_OLD)):
        v, h = _hold([(0, True, 8000, True, True, B, False, False), (500, True, 8000, True, rpt_this, boot, null, legacy)])
        assert v == [BW.HOLD_ARMED, want], (boot, null, legacy)
    v, h = _hold([(0, True, 8000, False, True, B, False, False), (50, True, 8000, False, True, L, False, False),
                  (100, True, 8000, True, True, L, False, False)])
    assert v == [BW.HOLD_PRIMED, BW.HOLD_UNPRIMED, BW.HOLD_NOT_ARMED]
    v, h = _hold([(0, True, 8000, False, True, B, False, False), (50, True, 8000, False, True, B, True, False)])
    assert v == [BW.HOLD_PRIMED, BW.HOLD_UNPRIMED]
    v, h = _hold([(0, False, 8000, False, True, B, False, False), (100, True, 8000, True, True, B, False, False)])
    assert v == [BW.HOLD_NOTHING, BW.HOLD_NOTHING] and h["released"] and not h["armed"]
    v, h = _hold([(0, True, 8000, True, True, B, False, False), (500, True, 0, True, True, B, False, False)])
    assert v == [BW.HOLD_ARMED, BW.HOLD_REL_OFF]
    h = BW.new_hold_state()
    assert not BW.hold_gate(h, 0, 8000) and not h["started"]
    BW.start_hold_step(h, 0, True, 3000, True, True, B, False, False)
    assert BW.hold_gate(h, 2999, 3000) and not BW.hold_gate(h, 3000, 3000) and h["cap_spent"]
    assert not BW.hold_gate(h, 3100, 600000) and not h["released"]
    assert BW.start_hold_step(h, 3200, True, 600000, True, True, B, False, False) == BW.HOLD_REL_CAP and h["released"]
    assert BW.start_hold_verdict is BW.start_hold_step
    for name in ("arm at the opening", "live releases", "released then paused: final", "stale-nonce LIVE: the cap",
                 "2-byte frame: no hold", "silence never primes", "late arm", "busy releases", "link releases",
                 "old guest releases", "the intro follows the report", "silence in the intro unprimes", "off never holds",
                 "off releases", "gate: unprimed never holds", "gate: a spent cap never re-holds",
                 "gate: the spent cap releases as cap"):
        assert _battle_text(f'"{name}"'), name


#: ControlSelfTest's StartHoldStep / HoldGate rows (s114), by name: the evaluator below must meet exactly these.
HOLD_SELFTEST_ROWS = ("arm at the opening", "live releases", "released then paused: final", "stale-nonce LIVE: the cap",
                      "2-byte frame: no hold", "silence never primes", "late arm", "busy releases", "link releases",
                      "old guest releases", "the intro follows the report", "silence in the intro unprimes",
                      "off never holds", "off releases", "gate: unprimed never holds", "gate: a spent cap never re-holds",
                      "gate: the spent cap releases as cap")


def _hold_selftest_statements() -> list:
    """ControlSelfTest's host-decision block IN ORDER, as C# statements -- from its `StartHoldState h =
    default(StartHoldState);` to the method's `catch`. The rows are STATEFUL (each step advances `h`, and `h` is reset
    between rows), so they are read from the ordered added lines of the LAST live patch carrying the block -- _stack_text's
    net count folds repeated lines such as the resets together -- and every line is asserted still net-present in the
    stack (a later patch that removed one would leave this read stale)."""
    start = "StartHoldState h = default(StartHoldState);"
    block = None
    for name in msr.stack():
        if name in msr.DEAD:
            continue
        for path, sec in msr.sections((msr.PATCHES / name).read_bytes()):
            if not path or path.replace("\\", "/").rsplit("/", 1)[-1] != "NetSyncBattle.cs":
                continue
            added = [ln[1:].strip() for ln in sec.decode("utf-8", "replace").splitlines()
                     if ln.startswith("+") and not ln.startswith("+++")]
            if start in added:
                i = added.index(start)
                j = added.index("catch (Exception err)", i)
                block = added[i:j - 1]                       # the try block's own closing brace dropped
    assert block, "ControlSelfTest's StartHoldState block is not on the live stack"
    live = {}
    for text in _stack_text("NetSyncBattle.cs"):
        live[text] = live.get(text, 0) + 1
    assert all(live.get(text, 0) > 0 for text in block if text), [t for t in block if t and not live.get(t)]
    code = " ".join(text for text in block if text and not text.startswith("//"))
    return [st.strip() for st in code.split(";") if st.strip()]


def test_start_hold_twins_evaluate_every_control_selftest_row_off_the_stack():
    """StartHoldStep / HoldGate's twins against ControlSelfTest's OWN rows, PARSED and EVALUATED in order (review R3H-6):
    each `h = default(...)` is a fresh :func:`BW.new_hold_state`, each bare step advances it, and every `&&` clause of a
    Row -- a step's verdict, a HoldGate answer, an `h.Field` -- must hold for the twin as it holds for the engine. A row's
    arguments, its expected verdict or its order changed on either side turns this red (the restated test above only
    reads the row NAMES off the stack)."""
    names = dict(BW.CS_BATTLE_CONSTANTS, true=True, false=False)

    def val(tok):
        tok = tok.strip()
        if tok in names:
            return names[tok]
        assert re.fullmatch(r"-?\d+", tok), tok
        return int(tok)

    def field(h, camel):
        key = re.sub(r"(?<!^)(?=[A-Z])", "_", camel).lower()     # SinceTick -> since_tick
        assert key in h, (camel, sorted(h))
        return h[key]

    def clause(h, c):
        c = " ".join(c.split())
        m = re.fullmatch(r"StartHoldStep\(ref h, (.*)\) == (\w+)", c)
        if m:
            return BW.start_hold_step(h, *[val(a) for a in m.group(1).split(",")]) == names[m.group(2)]
        m = re.fullmatch(r"(!?)HoldGate\(ref h, (.*)\)", c)
        if m:
            return bool(BW.hold_gate(h, *[val(a) for a in m.group(2).split(",")])) != bool(m.group(1))
        m = re.fullmatch(r"h\.(\w+) == (-?\d+)", c)
        if m:
            return field(h, m.group(1)) == int(m.group(2))
        m = re.fullmatch(r"(!?)h\.(\w+)", c)
        if m:
            return bool(field(h, m.group(2))) != bool(m.group(1))
        raise AssertionError(f"an unparsed ControlSelfTest clause: {c!r}")

    h, seen = None, []
    for st in _hold_selftest_statements():
        st = " ".join(st.split())
        if re.fullmatch(r"(?:StartHoldState )?h = default\(StartHoldState\)", st):
            h = BW.new_hold_state()
            continue
        m = re.fullmatch(r"StartHoldStep\(ref h, (.*)\)", st)
        if m:
            BW.start_hold_step(h, *[val(a) for a in m.group(1).split(",")])
            continue
        m = re.fullmatch(r'Row\((.*), "([^"]+)", ref rows, ref fail\)', st)
        assert m, f"an unparsed ControlSelfTest statement: {st!r}"
        expr, name = m.group(1), m.group(2)
        for i, c in enumerate(expr.split("&&")):             # in order: the engine's && short-circuits, the steps mutate h
            assert clause(h, c), f"row {name!r}: clause {i} ({' '.join(c.split())}) is false for the twin"
        seen.append(name)
    assert tuple(seen) == HOLD_SELFTEST_ROWS, seen


def test_the_r3_twins_say_the_engines_words():
    """Every name / reason an R3 twin returns is a literal the stack carries: the boot names, the release reasons, the
    hold states, the control-byte names, W2ForceWhy's rows, the follow-message names; and W2Force's rows restated."""
    for boot, name in BW.BOOT_NAMES.items():
        assert _battle_text(f'return "{name}";'), name
    for name in BW.HOLD_RELEASE_NAMES.values():
        assert _battle_text(f'why = "{name}";'), name
    for state in BW.HOLD_STATES:
        assert _battle_text(f'"{state}"'), state
    for name in BW.CTL_NAMES.values():
        assert _battle_text(f'return "{name}";'), name
    for a in (BW.PRESENT_FLEE, BW.PRESENT_ANNIHILATE, BW.PRESENT_VICTORY):
        why = BW.w2_force_why(a)                           # (split over C# literals: its head and its tail are each one)
        assert _battle_text(why[:60]) and _battle_text(why[-30:]), why
    assert _battle_text('"annihilated"') and _battle_text('_followMsg = "dropped-gil";')
    assert BW.w2_force(BW.PRESENT_FLEE) == (BW.PHASE_CLOSE, BW.SEQ_DEFEATCLOSE_FADEOUT, BW.BTL_RESULT_ESCAPE)
    for a in (BW.PRESENT_ANNIHILATE, BW.PRESENT_DEFEAT):
        assert BW.w2_force(a) == (BW.PHASE_DEFEAT, BW.SEQ_DEFEATCLOSE_FADEOUT, BW.BTL_RESULT_DEFEAT)
    for a in (BW.PRESENT_VICTORY, BW.PRESENT_CLOSE, BW.PRESENT_HOLD, BW.PRESENT_NONE, 99):
        assert BW.w2_force(a) == (BW.PHASE_VICTORY, BW.SEQ_VICTORY_FADEOUT, BW.BTL_RESULT_VICTORY)
    assert BW.GUEST_MODE_NAMES[BW.GUEST_HOLD] == "hold" and BW.GUEST_MODE_NAMES[BW.GUEST_NOR9B] == "nor9b"
    assert _battle_text('case GuestHold: return "hold";') and _battle_text('case GuestNoR9b: return "nor9b";')


def test_the_flee_record_codec_matches_the_engines_selftest_cases():
    """s116's fmt-2 record: EncodeFleeRecord's bytes (B5 02 05 00 01 78 56 34 12), its round trip beside the block in
    either order (the last one wins), a SHORT body skipped and counted with the block KEPT, growth skipped by len, a
    record with no block dropped with it, an unknown fmt beside it still counted."""
    rec = BW.encode_flee_record(BW.FLEE_GIL_DROP, 0x12345678)
    assert rec == bytes([0xB5, 0x02, 0x05, 0x00, 0x01, 0x78, 0x56, 0x34, 0x12])
    assert _battle_text("fleegil encode: [B5 02 05 00 01 78 56 34 12] (")
    m = BW.make_block(BW.PHASE_CLOSE, 0, BW.BTL_RESULT_ESCAPE)
    block = BW.encode_trailer(m)
    for data in (block + rec, rec + block):
        got, why, skipped = BW.read_trailer(data)
        assert why is None and skipped == 0 and (got["flee_flags"], got["flee_gil"]) == (1, 0x12345678)
    got, why, skipped = BW.read_trailer(block)
    assert (got["flee_flags"], got["flee_gil"]) == (-1, -1)
    got, _w, _s = BW.read_trailer(rec + block + BW.encode_flee_record(1, 77))
    assert got["flee_gil"] == 77                                         # the last record wins
    got, _w, _s = BW.read_trailer(block + bytes([0xB5, 0x02, 0x07, 0x00, 0x01, 0x4D, 0, 0, 0, 0xEE, 0xEE]))
    assert got["flee_gil"] == 77                                         # growth skipped by len
    for length in range(BW.FLEE_RECORD_LEN):
        short = bytes([0xB5, 0x02, length, 0x00]) + b"\x01" * length
        got, why, skipped = BW.read_trailer(short + block)
        assert got is not None and why is None and skipped == 1 and got["flee_flags"] == -1, length
    assert BW.read_trailer(rec) == (None, None, 0)                       # a flee record with no block: nothing
    got, _w, skipped = BW.read_trailer(block + rec + bytes([0xB5, 0x7F, 0x01, 0x00, 0x00]))
    assert skipped == 1 and got["flee_gil"] == 0x12345678
    pub = BW.published_end(got, with_flee=True)
    assert list(pub)[-2:] == ["manifest_len", "flee_gil"] and pub["flee_gil"] == 0x12345678
    assert "flee_gil" not in BW.published_end(got)


# ---- the stand-in: s111 the intro mirror, s112 the swirl clamp

def _r3_own(g, fake, *, atb_gain: int = 10, intro: int = 30, rand: bool = False, guest: bool = False):
    """A selftest OWN battle on the stand-in whose gauges RISE (atb_gain per frame, enemies never hit) -- slot 1 starts
    full (Ready at the opening); ``guest`` = slot 1 the loopback guest's (`guestslots 2`)."""
    fake.atb_gain = atb_gain
    fake.enemy_hit = 0
    fake.cmd_resolve_frames = 10 ** 6
    fake.battle_intro_frames = intro
    if guest:
        g.netsync("guestslots", 2)
    units = [dict(u) for u in BENCH_UNITS]
    units[1]["atb"] = units[1]["atb_max"]
    fake.start_battle(67, units=units, rand=rand)


def _r3_end(g, fake):
    """End the stand-in's own battle and wait for the pump's falling edge (`host.caps` -1)."""
    fake.end_battle(1)
    g.wait_for(lambda s: s.coop_host_caps == -1, timeout=4.0, what="the own battle's end")


def _enemy_atb(st) -> int:
    return next(u["atb"] for u in st.units() if not u.get("player"))


def test_an_own_battle_publishes_its_intro_and_the_lever_strips_it(game):
    """s111 host half: a random encounter under `bench cfg skipcam 0` skips its intro -- caps & 0x0C == 0x0C, published 1,
    own_skip 1 -- and its opening comes sooner than a scripted battle's (caps 0x0A: bit 3 alone, published 0); `bench
    intro 0` strips both bits (the pre-stage host); `bench cfg skipcam restore` / the release put the save's value back."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(FIELD)
        g.netsync("selftest", 1)
        st = g.netsync("bench", "cfg", "skipcam", "0")
        assert st.coop_cfg_skip_btl_camera == 0 and st.coop_cfg_atb == 1 and st.coop_intro_published == -1
        f0 = fake.frame
        _r3_own(g, fake, intro=60, rand=True)
        st = g.wait_for(lambda s: s.commands_enabled and s.coop_host_caps not in (None, -1), timeout=6.0, what="opening")
        skip_frames = st.frame - f0
        assert st.coop_host_caps & 0x0F == 0x0F and st.coop_intro_published == 1 and st.coop_intro_own_skip == 1
        fake.end_battle(1)
        g.wait_for(lambda s: s.coop_host_caps == -1, timeout=4.0, what="the battle's end")
        f0 = fake.frame
        _r3_own(g, fake, intro=60)
        st = g.wait_for(lambda s: s.commands_enabled and s.coop_host_caps not in (None, -1), timeout=6.0, what="opening")
        assert st.coop_host_caps & 0x0F == 0x0A and st.coop_intro_published == 0 and st.coop_intro_own_skip == 0
        assert st.frame - f0 >= skip_frames + 30                          # the played intro is the longer one
        st = g.netsync("bench", "intro", "0")
        st = g.wait_for(lambda s: s.coop_host_caps & 0x0C == 0, timeout=4.0, what="the lever")
        assert st.coop_intro_off is True and st.coop_intro_published == -1 and st.diorama_intro_off is True
        fake.end_battle(1)
        st = g.netsync("bench", "cfg", "skipcam", "restore")
        assert st.coop_cfg_skip_btl_camera == 1
        g.netsync("bench", "cfg", "skipcam", "0")
        g.send("reset")
        st = g.wait_for(lambda s: s.netsync is not None and not s.netsync["forced"], timeout=5.0, what="the release")
        assert st.coop_cfg_skip_btl_camera == 1 and st.coop_intro_off is False


def _r3_leave(g):
    """`dioleave` once the boot's swirl is over (its steady command phase: a leave mid-swirl is deferred), then the
    return."""
    g.wait_for(lambda s: s.commands_enabled, timeout=6.0, what="the steady phase")
    g.netsync("dioleave")
    g.wait_for(lambda s: not s.diorama_booted and s.control, timeout=8.0, what="the return")


def test_a_diorama_plays_the_hosts_intro_and_the_lever_its_own(game):
    """s111 guest half: `dioboot 67 0 skip|play [rand]` stamps the boot's wire intro; the diorama plays the HOST's choice
    (applied) over its own (own), `calls` counts the host's decisions, `normal_ms` the boot -> steady span; `bench intro 0`
    = its own setting (calls 0); a `wire` boot parses the bench header (`wire` alone: no intro bits -> wire -1)."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        fake.reinit_fields = fake.encounter_fields = {FIELD}
        g.newgame(settle=0)
        g.warp(FIELD)
        g.netsync("selftest", 1)
        fake.control = True
        st = g.netsync("dioboot", 67, 0, "skip")
        assert (st.diorama_intro_wire, st.diorama_intro_applied, st.diorama_intro_own) == (1, "skip", "play")
        assert st.diorama_intro_calls >= 1 and st.diorama_intro_off is False
        st = g.wait_for(lambda s: s.diorama_intro_normal_ms is not None and s.diorama_intro_normal_ms >= 0, timeout=6.0,
                        what="the steady frame")
        skip_ms = st.diorama_intro_normal_ms
        _r3_leave(g)
        st = g.netsync("dioboot", 67, "play")
        assert (st.diorama_intro_wire, st.diorama_intro_applied) == (0, "play")
        st = g.wait_for(lambda s: s.diorama_intro_normal_ms >= 0, timeout=6.0, what="the steady frame")
        assert st.diorama_intro_normal_ms > skip_ms
        _r3_leave(g)
        g.netsync("bench", "intro", "0")
        g.netsync("bench", "cfg", "skipcam", "0")
        st = g.netsync("dioboot", 67, 0, "play", "rand")
        assert (st.diorama_intro_wire, st.diorama_intro_applied, st.diorama_intro_own, st.diorama_intro_calls) == \
            (0, "skip", "skip", 0)                         # the lever: its own (a random boot under skipcam 0 skips)
        _r3_leave(g)
        g.netsync("bench", "intro", "1")
        st = g.netsync("dioboot", 67, 0, "wire")
        assert st.diorama_intro_wire == -1 and st.diorama_intro_calls == 0
        _r3_leave(g)
        st = g.netsync("dioboot", 67, 0, "wire", "play")
        assert st.diorama_intro_wire == 0 and st.diorama_intro_applied == "play" and st.diorama_intro_calls >= 1


def test_the_swirl_clamp_shortens_a_diorama_swirl_and_keeps_a_real_battles(game):
    """s112: with the laptop stand-in `bench swirl local 115` a diorama's swirl plays min(115, clamp 0) = 0 frames
    (clamped), a real battle's keeps 115; `bench swirl clamp -1` is the pre-stage diorama (115); the release puts both back."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        fake.reinit_fields = fake.encounter_fields = {FIELD}
        g.newgame(settle=0)
        g.warp(FIELD)
        g.netsync("selftest", 1)
        fake.control = True
        st = g.netsync("bench", "swirl", "local", "115")
        assert (st.diorama_swirl_bench_local, st.diorama_intro_swirl_frames, st.diorama_swirl_clamp_now) == (115, 115, 0)
        swirls = st.diorama_swirl_swirls
        st = g.netsync("dioboot", 67)
        assert (st.diorama_swirl_diorama, st.diorama_swirl_own, st.diorama_swirl_used) == (True, 115, 0)
        assert st.diorama_swirl_clamped is True and st.diorama_swirl_dwell_ms == 0 and st.diorama_swirl_swirls == swirls + 1
        g.wait_for(lambda s: s.commands_enabled, timeout=6.0, what="the steady phase")
        g.netsync("dioleave")
        g.wait_for(lambda s: not s.diorama_booted and s.control, timeout=8.0, what="the return")
        st = g.netsync("bench", "swirl", "clamp", "-1")
        assert (st.diorama_swirl_clamp_now, st.diorama_swirl_src) == (-1, "bench")
        st = g.netsync("dioboot", 67)
        assert (st.diorama_swirl_used, st.diorama_swirl_clamped, st.diorama_swirl_dwell_ms) == (115, False, 3833)
        g.wait_for(lambda s: s.commands_enabled, timeout=6.0, what="the steady phase")
        g.netsync("dioleave")
        g.wait_for(lambda s: not s.diorama_booted and s.control, timeout=8.0, what="the return")
        g.netsync("bench", "swirl", "clamp", "ini")
        g.send("battle 67")
        st = g.wait_for(lambda s: s.in_battle, timeout=6.0, what="a real battle")
        assert (st.diorama_swirl_diorama, st.diorama_swirl_used, st.diorama_swirl_clamped) == (False, 115, False)
        g.send("reset")
        st = g.wait_for(lambda s: s.netsync is not None and not s.netsync["forced"], timeout=5.0, what="the release")
        assert (st.diorama_swirl_bench_local, st.diorama_swirl_src) == (-1, "ini")


# ---- s113 Wait parity, s114 the start hold

def test_wait_parity_freezes_the_hosts_wait_gauges_below_the_root_only(game):
    """s113 on the stand-in's own battle (cfg.atb 1 = Wait, slot 1 the loopback guest's): the loopback at its command root
    sends 2 -- the enemy's gauge RUNS; `bench ctl deep` (3) and `legacy` (1) freeze it; `bench waitparity 0` freezes the
    root too (the pre-stage host); `bench cfg atb active` runs both. `host.wait` / `menu.ctl` read each frame back."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(FIELD)
        g.netsync("selftest", 1)
        _r3_own(g, fake, guest=True)
        st = g.wait_for(lambda s: s.commands_enabled and s.coop_peer_ready_mask and s.coop_peer_ready_mask & 2,
                        timeout=8.0, what="slot 1 Ready")
        st = g.wait_for(lambda s: s.coop_wait_menu == BW.CTL_ROOT, timeout=4.0, what="the root byte")
        assert (st.coop_ctl_menu, st.coop_ctl_src, st.coop_wait_deep, st.coop_wait_open) == (2, "root", False, True)
        assert st.coop_ctl_hex == BW.control_hex(2, st.coop_peer_nonce, BW.BOOT_NONE)
        assert g.ctl_byte() == 2
        flat, _ = g.atb_flat(0.3, player=False)
        assert not flat, "the root froze the Wait gauges"
        for ctl, want in (("deep", 3), ("legacy", 1)):
            st = g.netsync("bench", "ctl", ctl)
            st = g.wait_for(lambda s: s.coop_wait_menu == want, timeout=4.0, what=ctl)
            assert st.coop_wait_deep is True and st.coop_ctl_src == "bench"
            flat, _ = g.atb_flat(0.3, player=False)
            assert flat, ctl
        st = g.netsync("bench", "ctl", "auto")
        g.wait_for(lambda s: s.coop_wait_menu == 2, timeout=4.0, what="auto")
        st = g.netsync("bench", "waitparity", "0")
        st = g.wait_for(lambda s: s.coop_wait_deep, timeout=4.0, what="the lever")
        assert st.coop_wait_parity_off is True and st.coop_wait_menu == 2
        flat, _ = g.atb_flat(0.3, player=False)
        assert flat, "the lever's root did not freeze"
        st = g.netsync("bench", "cfg", "atb", "active")
        assert st.coop_cfg_atb == 0
        flat, _ = g.atb_flat(0.3, player=False)
        assert not flat, "Active froze"
        g.send("reset")
        st = g.wait_for(lambda s: s.netsync is not None and not s.netsync["forced"], timeout=5.0, what="the release")
        assert st.coop_cfg_atb == 1 and st.coop_wait_parity_off is False


def test_the_start_hold_arms_on_a_booting_report_and_releases_on_live(game):
    """s114 on the stand-in: `bench boot booting` before `battle` -> the intro primes, the opening ARMS (state holding,
    caps bit 4, every gauge flat); `bench boot live` releases it ("live", count +1, the gauges run); a second battle with
    the report at NONE is "not armed" (why "none"); `bench starthold 0` = no hold whatever the report; a short cap
    releases as "cap"."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(FIELD)
        g.netsync("selftest", 1)
        st = g.netsync("bench", "boot", "booting")
        count = st.coop_hold_count
        _r3_own(g, fake)
        st = g.wait_for(lambda s: s.commands_enabled and s.coop_hold_state == "holding", timeout=6.0, what="the arm")
        assert st.coop_hold_count == count + 1 and st.coop_hold_why == "booting" and st.coop_host_caps & BW.FLAG_START_HOLD
        assert st.coop_ctl_boot == BW.BOOT_BOOTING and st.coop_ctl_boot_name == "booting"
        assert st.coop_hold_guest_boot_name == "booting" and st.coop_hold_guest_r3 is True and st.coop_hold_guest_fmt == 1
        assert g.hold_window()["state"] == "holding"
        flat, _ = g.atb_flat(0.3)
        assert flat, "the hold let a gauge move"
        live = st.coop_hold_released_live
        st = g.netsync("bench", "boot", "live")
        st = g.wait_for(lambda s: s.coop_hold_release == "live", timeout=4.0, what="the release")
        assert st.coop_hold_state == "released" and st.coop_hold_released_live == live + 1 and st.coop_hold_held_ms >= 0
        assert not st.coop_host_caps & BW.FLAG_START_HOLD
        flat, _ = g.atb_flat(0.3)
        assert not flat, "released, yet the gauges stay flat"
        _r3_end(g, fake)
        g.netsync("bench", "boot", "none")
        _r3_own(g, fake)
        st = g.wait_for(lambda s: s.commands_enabled and s.coop_hold_why == "none", timeout=6.0, what="not armed")
        assert st.coop_hold_state == "late" and st.coop_hold_count == count + 1       # inside the late-arm window...
        st = g.wait_for(lambda s: s.coop_hold_state == "not_armed", timeout=6.0, what="the late window's end")
        _r3_end(g, fake)
        g.netsync("bench", "boot", "booting")
        g.netsync("bench", "starthold", "0")
        _r3_own(g, fake)
        st = g.wait_for(lambda s: s.commands_enabled and s.coop_hold_state == "off", timeout=6.0, what="the lever")
        assert st.coop_hold_off is True and st.coop_hold_cap_ms == 0 and st.coop_hold_count == count + 1
        flat, _ = g.atb_flat(0.3)
        assert not flat
        _r3_end(g, fake)
        g.netsync("bench", "starthold", "1")
        st = g.netsync("bench", "starthold", "cap", "300")
        assert st.coop_hold_cap_ms == 300
        cap = st.coop_hold_released_cap
        _r3_own(g, fake)
        st = g.wait_for(lambda s: s.coop_hold_release == "cap", timeout=8.0, what="the cap")
        assert st.coop_hold_released_cap == cap + 1 and st.coop_hold_count == count + 2


def test_a_dioramas_report_turns_live_with_its_steady_frame(game):
    """s114 guest half on the stand-in: a diorama with the bench feed reports BOOTING for the feed's nonce until its steady
    frame with a live view, then LIVE (`netsync.diorama.live` latched, ms, nonce); the feed's `ctl` carries the report."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        _dio(g, fake)
        st = g.netsync("bbench", "start", "1")
        st = g.wait_for(lambda s: s.diorama_live_latched, timeout=6.0, what="the LIVE latch")
        feed = st.coop_feed
        assert st.diorama_live_nonce == feed["nonce"] and st.diorama_live_ms >= 0
        st = g.wait_for(lambda s: s.coop_ctl_boot == BW.BOOT_LIVE, timeout=4.0, what="the LIVE report")
        assert st.coop_ctl_nonce == feed["nonce"] and st.coop_feed["ctl"] == st.coop_ctl_hex
        assert st.coop_feed["ctl_menu"] == st.coop_ctl_menu


# ---- s115 flee, s116 the flee gil, s117 defeat

def test_a_presented_escape_runs_away_and_r9b_skips_its_state_half(game):
    """s115 on the stand-in: `endbench escape` in a diorama -> action "flee" (5/3), the living player turns and runs (mot
    17, z falling, then disappear 5), the escape tail (phase 8, result 4, btl_flag 64), R9b counted, R8; `guest hold` =
    the pre-s115 guest (HELD); `guest nor9b` = the stock penalty in the diorama (ability_flag, gil down WHILE booted, back
    after the teardown; the flag itself outlives the teardown until the next battle's InitBattle, as the engine's live
    btl_flag read does)."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        _dio(g, fake)
        gil = g.state.coop_flee_gil_now
        st = g.netsync("endbench", "escape")
        st = g.wait_for(lambda s: s.coop_present_injected, timeout=4.0, what="the run-away")
        assert (st.coop_present_action, st.coop_present_inject_phase, st.coop_present_inject_seq) == ("flee", 5, 3)
        st = g.wait_for(lambda s: s.unit_mot(0) == BW.MP_ESCAPE, timeout=4.0, what="MP_ESCAPE")
        z0 = st.unit_z(0)
        st = g.wait_for(lambda s: s.unit_z(0) < z0, timeout=4.0, what="the run")
        st = g.wait_for(lambda s: s.unit_disappear(0) == BW.DISAPPEAR_DONE, timeout=4.0, what="the escape fade")
        st = g.wait_for(lambda s: s.coop_present_r8_hits > 0, timeout=8.0, what="R8")
        assert (st.battle_phase, st.battle_result, st.coop_flee_r9b, st.coop_flee_bypassed) == (8, 4, 1, 0)
        assert st.coop_present_btl_flag & BW.BTL_END_LOAD and st.coop_flee_ability_flag is False
        assert st.coop_flee_gil_now == gil and st.coop_flee_penalty >= 0
        assert st.unit_mot(1) != BW.MP_ESCAPE                 # Vivi (0 HP) never runs
    fake = FakeGame(game)
    with session(game, fake) as g:
        _dio(g, fake)
        g.netsync("endbench", "guest", "hold")
        st = g.netsync("endbench", "escape")
        st = g.wait_for(lambda s: s.coop_present_held, timeout=4.0, what="the hold")
        assert st.coop_present_action == "hold" and st.coop_present_injected is False and st.battle_phase == 4
    fake = FakeGame(game)
    with session(game, fake) as g:
        _dio(g, fake)
        gil = g.state.coop_flee_gil_now
        g.netsync("endbench", "guest", "nor9b")
        g.netsync("endbench", "escape")
        st = g.wait_for(lambda s: s.coop_flee_bypassed == 1, timeout=8.0, what="the stock tail")
        assert st.coop_flee_r9b == 0 and st.coop_flee_ability_flag is True
        assert st.coop_flee_gil_now == gil - st.coop_flee_penalty and st.coop_flee_penalty > 0
        g.netsync("dioleave")
        st = g.wait_for(lambda s: not s.diorama_booted, timeout=8.0, what="the teardown")
        assert st.coop_flee_gil_now == gil
        # the flag is the LIVE btl_flag bit (HarnessFleeAbilityFlag, no booted gate): the teardown leaves it set, and
        # only the next battle's InitBattle clears it (review R3H-7)
        assert st.coop_flee_ability_flag is True
        g.netsync("endbench", "guest", "on")
        g.netsync("endbench", "clear")                      # a fabricated end stays armed across a dioboot
        st = _dio(g, fake, fresh=False)
        assert st.coop_flee_ability_flag is False


def test_the_hosts_flee_gil_shows_after_r9b_and_rides_the_peer_end(game):
    """s116 on the stand-in: `endbench fleegil 77` sets the template's record (peer.end.flee_gil 77, through the codec);
    a run-away past R9b shows it (msg_gil 77, follow_msg "dropped-gil"), the guest's gil untouched; `fleegil none` -> -1."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        _dio(g, fake)
        gil = g.state.coop_flee_gil_now
        st = g.netsync("endbench", "fleegil", 77)
        assert st.coop_peer_end["flee_gil"] == 77 and st.coop_host_flee_gil == -1
        g.netsync("endbench", "escape")
        st = g.wait_for(lambda s: s.coop_flee_msg_gil == 77, timeout=8.0, what="the host's figure")
        assert st.coop_follow_msg == "dropped-gil" and st.coop_flee_gil_now == gil and st.coop_present_r8_hits == 0
        st = g.netsync("endbench", "fleegil", "none")
        assert st.coop_peer_end["flee_gil"] == -1


def test_an_annihilation_settles_into_phase_defeat_and_a_game_over_return_reverts_the_local_defeat(game):
    """s117 on the stand-in: `kill 15` (every seated player down: mot 4) then `defeat` -> "annihilate" (5/1, "Annihilated"),
    the settle -> phase 7, result 3, song 6 (btl_flag 32) in this Game-Over scene, R8; `ui 2` (Game Over) takes the guest
    to its OWN field: no stamp, the local DEFEAT reverted (reverted 3, field result 0)."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        _dio(g, fake)
        st = g.netsync("endbench", "kill")
        assert st.unit_mot(0) == BW.MP_DISABLE and st.unit_mot(1) == BW.MP_DISABLE
        g.netsync("endbench", "defeat")
        st = g.wait_for(lambda s: s.coop_present_injected, timeout=4.0, what="the annihilation")
        assert (st.coop_present_action, st.coop_present_inject_phase, st.coop_present_inject_seq) == ("annihilate", 5, 1)
        assert st.coop_follow_msg == "annihilated"
        st = g.wait_for(lambda s: s.coop_present_r8_hits > 0, timeout=8.0, what="R8")
        assert (st.battle_phase, st.battle_seq, st.battle_result) == (7, 1, 3) and st.coop_present_btl_flag & 32
        assert st.coop_present_watchdog == ""
        fake.dio_leave_frames = 60
        g.netsync("endbench", "ui", 2)
        st = g.wait_for(lambda s: not s.diorama_booted, timeout=8.0, what="the Game-Over exit")
        assert st.coop_exit_trigger == "game-over" and st.coop_exit_stamped == -1
        assert st.coop_exit_reverted == 3 and st.battle_result == 0


def test_a_standing_party_takes_the_defeat_tail_and_var_34_needs_the_hosts_event_phase(game):
    """s117 fix pass: `defeat` with the party standing -> the annihilation's tail at once (7/0, "Annihilated"); `guest
    settle` keeps the stock settle, which a standing party stalls until W2's DEFEAT row ("N player(s) not down", never
    VICTORY); `event` then `phase-defeat` with the party standing is var 34's "defeat" (7/0, no message); a NoGameOver
    scene plays no song 6."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        _dio(g, fake)
        g.netsync("endbench", "defeat")
        st = g.wait_for(lambda s: s.coop_present_injected, timeout=4.0, what="the injection")
        assert (st.coop_present_action, st.coop_present_inject_phase, st.coop_present_inject_seq) == ("annihilate", 7, 0)
        assert st.coop_follow_msg == "annihilated" and st.battle_result == 3
    fake = FakeGame(game)
    with session(game, fake) as g:
        _dio(g, fake)
        g.netsync("endbench", "guest", "settle")
        g.netsync("endbench", "defeat")
        st = g.wait_for(lambda s: s.coop_present_injected, timeout=4.0, what="the injection")
        assert (st.coop_present_inject_phase, st.coop_present_inject_seq) == (5, 1)
        stays(g, lambda s: s.battle_phase == BW.PHASE_MENU_OFF, frames=40, what="the settle moved on")
        fake._nb.inject_rt -= 9.0
        st = g.wait_for(lambda s: s.coop_present_watchdog == "W2", timeout=4.0, what="W2")
        assert re.match(r"\d player\(s\) not down \(the defeat tail waits", st.coop_present_blocker), st.coop_present_blocker
        assert _battle_text(" player(s) not down (the defeat tail waits for every player's MP_DISABLE or a BattleEnd status)")
        st = g.wait_for(lambda s: s.battle_phase == BW.PHASE_DEFEAT, timeout=4.0, what="the forced defeat row")
        assert st.battle_result == BW.BTL_RESULT_DEFEAT
    fake = FakeGame(game)
    with session(game, fake) as g:
        fake.scene_no_gameover = True
        _dio(g, fake)
        g.netsync("endbench", "event")
        g.wait_frames(5)
        g.netsync("endbench", "phase-defeat")
        st = g.wait_for(lambda s: s.coop_present_injected, timeout=4.0, what="var 34")
        assert (st.coop_present_action, st.coop_present_inject_phase, st.coop_present_inject_seq) == ("defeat", 7, 0)
        assert st.coop_follow_msg == "" and st.battle_result == 3
        st = g.wait_for(lambda s: s.coop_present_r8_hits > 0, timeout=8.0, what="R8")
        assert not st.coop_present_btl_flag & BW.BTL_PLAY_END_SONG      # a NoGameOver scene: no song 6


def test_a_close_defeat_is_the_close_fade_and_the_hold_lever_holds_a_defeat(game):
    """s117: CLOSE + GAMEOVER (`other 6`) is the CLOSE fade (8/0, local 6) and a Game-Over return reverts it (reverted 6,
    field 0 -- S6-D1 strengthened); `guest hold` holds a defeat (the pre-s117 guest)."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        _dio(g, fake)
        g.netsync("endbench", "other", 6)
        st = g.wait_for(lambda s: s.coop_present_injected and s.battle_result == 6, timeout=4.0, what="the close")
        assert (st.coop_present_action, st.coop_present_inject_phase, st.coop_present_inject_seq) == ("close", 8, 0)
        g.netsync("endbench", "ui", 2)
        st = g.wait_for(lambda s: not s.diorama_booted, timeout=8.0, what="the exit")
        assert st.coop_exit_reverted == 6 and st.battle_result == 0
    fake = FakeGame(game)
    with session(game, fake) as g:
        _dio(g, fake)
        g.netsync("endbench", "guest", "hold")
        g.netsync("endbench", "kill")
        g.netsync("endbench", "defeat")
        st = g.wait_for(lambda s: s.coop_present_held, timeout=4.0, what="the hold")
        assert st.coop_present_injected is False and st.coop_follow_msg == ""


def test_a_pre_s117_guest_holds_a_defeat_and_a_pre_s115_guest_an_escape(game):
    """The stand-in at s116 holds the host's defeat (PresentFor's last line), at s114 its escape too -- the v1 table."""
    for level, op in (("s116", "defeat"), ("s114", "escape"), ("s114", "defeat")):
        fake = FakeGame(game)
        fake.netsync_caps = _caps_at(level)
        with session(game, fake) as g:
            _dio(g, fake)
            g.netsync("endbench", op)
            st = g.wait_for(lambda s: s.coop_present_held, timeout=4.0, what=f"{level} holds {op}")
            assert st.coop_present_action == "hold" and st.coop_present_injected is False, (level, op)


def test_reset_releases_every_r3_lever(game):
    """HarnessReleaseBench over the R3 levers: `bench intro|waitparity|ctl|boot|starthold|swirl|cfg` and `endbench guest
    hold` all back to rest on `reset` (read again under a fresh selftest role)."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(FIELD)
        g.netsync("selftest", 1)
        for args in (("bench", "intro", "0"), ("bench", "waitparity", "0"), ("bench", "ctl", "deep"),
                     ("bench", "boot", "busy"), ("bench", "starthold", "0"), ("bench", "swirl", "local", "90"),
                     ("bench", "swirl", "clamp", "-1"), ("bench", "cfg", "skipcam", "0"), ("bench", "cfg", "atb", "active"),
                     ("endbench", "guest", "hold")):
            g.netsync(*args)
        st = g.state
        assert (st.coop_intro_off, st.coop_wait_parity_off, st.coop_hold_off) == (True, True, True)
        assert (st.diorama_swirl_bench_local, st.diorama_swirl_clamp_now) == (90, -1)
        assert (st.coop_cfg_skip_btl_camera, st.coop_cfg_atb, st.coop_present_guest_mode) == (0, 0, "hold")
        g.send("reset")
        g.wait_for(lambda s: s.netsync is not None and not s.netsync["forced"], timeout=5.0, what="the release")
        st = g.netsync("selftest", 1)
        assert (st.coop_intro_off, st.coop_wait_parity_off, st.coop_hold_off) == (False, False, False)
        assert (st.diorama_swirl_bench_local, st.diorama_swirl_clamp_now) == (-1, 0)
        assert (st.coop_cfg_skip_btl_camera, st.coop_cfg_atb, st.coop_present_guest_mode) == (1, 1, "on")
        assert fake._nb.bench_ctl == -1 and fake._nb.bench_boot == -1


def test_state_reads_the_r3_keys_absent_as_cannot():
    """The R3 accessors on the s110 catch block are None (cannot) -- never 0 / False / "" -- and on the live block they
    read their sentinels; the units' `mot` / `disappear` / `z` read None without the keys."""
    old = State({"frame": 1, "netsync": _catch_doc_in("s110")})
    live = State({"frame": 1, "netsync": _agent_netsync_nothing()[0]})
    for name in State.NETSYNC_DIORAMA_ACCESSORS.values():
        assert getattr(old, name) is None, name
        assert getattr(live, name) is not None, name
    assert (old.coop_intro_mirror, old.coop_swirl_clamp, old.coop_wait_parity, old.coop_start_hold, old.coop_flee,
            old.coop_flee_gil, old.coop_defeat) == (False,) * 7
    assert (live.coop_intro_mirror, live.coop_swirl_clamp, live.coop_wait_parity, live.coop_start_hold, live.coop_flee,
            live.coop_flee_gil, live.coop_defeat) == (True,) * 7
    assert live.coop_follow_msg == "" and live.coop_hold_state == "" and live.coop_wait_menu == -1
    assert State({"frame": 1}).coop_intro_mirror is None
    unit = State({"frame": 1, "battle": {"units": [{"slot": 0, "mot": 17, "disappear": 5, "z": -900.5},
                                                   {"slot": 1, "mot": True}]}})
    assert (unit.unit_mot(0), unit.unit_disappear(0), unit.unit_z(0)) == (17, 5, -900.5)
    assert unit.unit_mot(1) is None and unit.unit_mot(4) is None and unit.unit_z(1) is None


def test_every_diorama_r3_key_has_an_accessor_and_every_accessor_a_key():
    """The `netsync.diorama` R3 keys (s111 intro, s112 swirl_clamp, s114 live) the live agent publishes are exactly the
    accessor table's paths (+ the three whole-block accessors)."""
    nothing, _ = _agent_netsync_nothing()
    leaves = set(_dio_leaves(nothing["diorama"]))
    table = State.NETSYNC_DIORAMA_ACCESSORS
    assert set(table) - leaves == {"intro", "intro.swirl_clamp", "live"}, sorted(set(table) ^ leaves)
    assert leaves <= set(table)


@pytest.mark.parametrize("level", ["s112", "s113", "s114", "s115"])
def test_the_stand_ins_units_and_feed_grow_as_the_agents_do(game, level):
    """[ff9mapkit netsync R3] `battle.units[]` gains `mot` / `disappear` / `z` at s115 (after `cmd_busy`, before `status`:
    AppendBattleUnits) and the bench feed gains `ctl` / `ctl_menu` right after `menu_open` at s113 (AppendStockMirror) --
    the stand-in publishes each exactly from its patch on (each line read off its patch)."""
    for key in ("mot", "disappear", "z"):
        assert net_lines("HarnessAgent.cs", rf'Num\(sb, "{key}", Try\(\(\) => ', [_patch_bytes("s115")]), key
    assert net_lines("HarnessAgent.cs", r'Str\(sb, "ctl", f\.Ctl\);', [_patch_bytes("s113")])
    assert net_lines("HarnessAgent.cs", r'Num\(sb, "ctl_menu", f\.CtlMenu\);', [_patch_bytes("s113")])
    fake = _dio_fake(FakeGame(game))
    fake.netsync_caps = _caps_at(level)
    unit = fake._battle_doc()["units"][0]
    tail = list(unit)[list(unit).index("cmd_busy") + 1:]
    assert tail == (["mot", "disappear", "z", "status"] if int(level[1:]) >= 115 else ["status"]), tail
    fake._netsync(["bbench", "start", "1"])
    fake._nb_feed_tick()
    feed = list(fake._nb_feed_doc())
    at = feed.index("menu_open") + 1
    assert feed[at:at + 2] == (["ctl", "ctl_menu"] if int(level[1:]) >= 113 else ["frames", "taken"]), feed


def test_the_start_hold_arms_late_ignores_a_stale_live_and_releases_on_the_link(game):
    """s114 on the stand-in, the remaining report levers: `bench boot late 300` (no frame until 300 ms after the opening,
    then BOOTING) arms LATE (why "late", late_ms about 300); `stale` (a LIVE naming the previous nonce) releases nothing --
    the cap does; `silent` (no frame at all, a first battle) never arms ("no word yet"); a `bench lapse ... reserve` while holding
    re-serves the BOOTING frame for 2000 ms, then the transport's silence releases it as "link"."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(FIELD)
        g.netsync("selftest", 1)
        g.netsync("bench", "boot", "silent")              # (first: no report of an earlier battle is still fresh)
        _r3_own(g, fake)
        st = g.wait_for(lambda s: s.coop_hold_why == "no word yet", timeout=6.0, what="silence never arms")
        count = st.coop_hold_count
        st = g.wait_for(lambda s: s.coop_hold_state == "not_armed", timeout=6.0, what="the late window's end")
        assert st.coop_hold_count == count and st.coop_hold_guest_fmt == -1
        _r3_end(g, fake)
        g.netsync("bench", "boot", "late", "300")
        _r3_own(g, fake)
        st = g.wait_for(lambda s: s.coop_hold_why == "late" and s.coop_hold_state == "holding", timeout=6.0,
                        what="the late arm")
        assert 250 <= st.coop_hold_late_ms < BW.LATE_ARM_MS, st.coop_hold_late_ms
        _r3_end(g, fake)
        g.netsync("bench", "starthold", "cap", "1500")
        g.netsync("bench", "boot", "booting")
        _r3_own(g, fake)
        g.wait_for(lambda s: s.coop_hold_state == "holding", timeout=6.0, what="the arm")
        g.netsync("bench", "boot", "stale")
        st = stays(g, lambda s: s.coop_hold_state == "holding", frames=10, what="a stale LIVE released it")
        assert st.coop_ctl_boot == BW.BOOT_LIVE and st.coop_ctl_nonce == (st.coop_hold_nonce - 1) & 0xFF
        st = g.wait_for(lambda s: s.coop_hold_release is not None and s.coop_hold_release != "", timeout=6.0,
                        what="the cap")
        assert st.coop_hold_release == "cap", st.coop_hold_release
        _r3_end(g, fake)
        g.netsync("bench", "starthold", "cap", "ini")
        _r3_end(g, fake)
        g.netsync("bench", "boot", "booting")
        _r3_own(g, fake)
        g.wait_for(lambda s: s.coop_hold_state == "holding", timeout=6.0, what="the arm")
        link = g.state.coop_hold_released_link
        st = g.netsync("bench", "lapse", "hold", "reserve")
        assert st.coop_lapse_reserve is True
        st = stays(g, lambda s: s.coop_hold_state == "holding", frames=30, what="the reserve's re-served BOOTING frame")
        st = g.wait_for(lambda s: s.coop_hold_release == "link", timeout=8.0, what="the link release")
        assert st.coop_hold_released_link == link + 1
        g.netsync("bench", "lapse", "end")
