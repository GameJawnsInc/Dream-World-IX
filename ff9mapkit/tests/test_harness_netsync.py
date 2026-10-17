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
                                               r"\|tap-record\|replay\|.*\|bmenu\|bbench\|endbench\|actbench\)"):
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
    F3 pin, which s96 introduced and no later patch touches). [ff9mapkit netsync s132] A patch that leaves the catch line
    alone (s132 adds no key) publishes the newest earlier patch's -- so the agent AT that patch is still read exactly."""
    pattern = r'outer\.Append\("\\"netsync\\":\{\\"enabled'
    catch = []
    for patch in reversed(_prefix(stem)):
        catch = net_lines("HarnessAgent.cs", pattern, [patch])
        if catch:
            break
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
    """[ff9mapkit netsync R3] ``netsync.diorama``'s R3 sub-blocks (`intro`, `intro.swirl_clamp`, `live`; [ff9mapkit netsync
    R3 s119] `hold`) as path -> value."""
    out = {}
    for k, v in block.items():
        if isinstance(v, dict) and (prefix or k in ("intro", "live", "hold")):
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
    # agent reads LIVE off config with no client (each a live read in the agent, never the sentinel) -- [ff9mapkit netsync
    # R3 s119/s120] and s119's hold cap and settle, read off NetSyncClient's statics (the cap = s120's session grace)
    live = {"intro.swirl_frames": "NetSyncDiorama.HarnessSwirlFrames",
            "intro.swirl_clamp.ini": "NetSyncDiorama.HarnessSwirlClampIni",
            "intro.swirl_clamp.clamp": "NetSyncDiorama.HarnessSwirlClamp",
            "intro.swirl_clamp.src": "NetSyncDiorama.HarnessSwirlClampSrc",
            "hold.cap_ms": "NetSyncClient.HarnessHoldCapMs", "hold.settle_ms": "NetSyncClient.HarnessHoldSettleMs"}
    got, want = _dio_leaves(doc["diorama"]), _dio_leaves(nothing["diorama"])
    assert list(got) == list(want)
    for path, value in want.items():
        if path not in live:
            assert got[path] == value, (path, got[path], value)
    for getter in live.values():
        assert any("Netsync." + getter in ln for ln in _stack_text("HarnessAgent.cs")), getter
    assert (got["hold.cap_ms"], got["hold.settle_ms"]) == (BW.SESSION_GRACE_DEFAULT_MS, BW.DIORAMA_SETTLE_MS)


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
                "NetSyncDiorama.cs", "NetSyncClient.cs", "BattleHUD.Scene.cs",
                "NetSyncDiorama.Replay.cs")                     # [ff9mapkit netsync s134] the guest action replay
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


#: The FIXED sub-objects below host / peer / menu / end / act (always published whole), BY PATH: their keys are leaves of
#: their own (the accessor table holds a whole-block accessor for each as well as one per key). Every other record
#: (``host.end``, ``peer.end``, ``menu.captured``, s106-s110's ``menu.roster`` / ``bench_roster`` / ``pending`` / ``feed``,
#: ``host.manifest``, ``handback.last``, ``replay.screen`` / ``fp``) may be null: one leaf. [ff9mapkit netsync s133] The
#: descent is keyed on the PATH, never a bare name (audit 4.2: `act.host` is a container where a bare "host" is one only at
#: the top) -- a new container goes HERE, or :func:`_leaves` never sees inside it.
BATTLE_CONTAINERS = {"end.end_leave": "s105", "end.declined": "s105", "menu.content_hits": "s106", "menu.mirror": "s107",
                     "end.replay": "s109", "host.handback": "s110", "host.handback.lapse": "s110",
                     "host.cfg": "s111", "host.intro": "s111", "host.wait": "s113", "menu.ctl": "s113",
                     "host.start_hold": "s114", "host.start_hold.released": "s114", "host.start_hold.guest": "s114",
                     "end.flee": "s115", "peer.expired": "s131",
                     # [ff9mapkit netsync s133] the fifth sub-object's `host` half and its fixed sub-objects
                     "act.host": "s133", "act.host.kinds": "s133", "act.host.vfx": "s133", "act.host.loop": "s133",
                     "act.host.tape": "s133",
                     # [ff9mapkit netsync s134] its `guest` half and that half's fixed sub-objects
                     "act.guest": "s134", "act.guest.levers": "s134", "act.guest.grace": "s134",
                     "act.guest.window": "s134", "act.guest.aborts": "s134", "act.guest.discarded": "s134",
                     # [ff9mapkit netsync s135] the replay hit hold (after `last`), and its `lag`
                     "act.guest.hold": "s135", "act.guest.hold.lag": "s135",
                     # [ff9mapkit netsync s136] fallback A, the LAST key of `act.guest`
                     "act.guest.fallback": "s136"}
#: The records that may be published null (an accessor reads None for them either way).
BATTLE_NULLABLE = ("host.end", "peer.end", "menu.captured", "menu.roster", "menu.bench_roster", "menu.pending",
                   "menu.feed", "host.manifest", "host.handback.last", "end.replay.screen", "end.replay.fp",
                   # [ff9mapkit netsync s133]
                   "act.host.last", "act.host.tape.page",
                   # [ff9mapkit netsync s134]
                   "act.guest.last",
                   # [ff9mapkit netsync s136]
                   "act.guest.fallback.last")


def _leaves(block: dict, prefix: str = "") -> dict:
    """``netsync.battle``'s key paths -> values, descending only into the FIXED sub-objects (host / peer / menu / end / act
    and :data:`BATTLE_CONTAINERS`, BY PATH -- [ff9mapkit netsync s133] audit 4.2: `act.host` is a container where a bare
    "host" is one only at the top); a record that may be null is one leaf."""
    out = {}
    for k, v in block.items():
        path = prefix + k
        if isinstance(v, dict) and (prefix == "" or path in BATTLE_CONTAINERS):
            out.update(_leaves(v, path + "."))
        else:
            out[path] = v
    return out


def _all_caps_through(cap: str) -> frozenset:
    """The stand-in capability set of the engine at battle capability ``cap`` (every F3.3 cap + the ladder up to it):
    :func:`harness.fakegame.caps_through`, the one place a calibration engine is built (a ladder PREFIX, never a subtraction)."""
    return FG.caps_through(cap)


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
        # [ff9mapkit netsync R3 s120/s121] two top-level blocks join `battle`: `session`, then `menu_refusal`
        assert new_top == (["battle"] if cap == "gates" else list(FG.NETSYNC_TOP_CAP_KEYS.get(cap, ()))), (patch, new_top)
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
    # [ff9mapkit netsync R3 s119-s121] the round's fixed blocks, in the agent's order, and the top-level order: `session` and
    # `menu_refusal` sit between `diorama` and `battle` (AppendNetsync's own order)
    assert tuple(dio["hold"]) == FG.NETSYNC_DIORAMA_HOLD_KEYS
    assert tuple(prev_doc["session"]) == FG.NETSYNC_SESSION_KEYS
    assert tuple(prev_doc["menu_refusal"]) == FG.NETSYNC_MENU_REFUSAL_KEYS
    # [ff9mapkit netsync s131] `peer.expired`, the last key of `peer`
    assert tuple(battle["peer"]["expired"]) == FG.NETSYNC_PEER_EXPIRED_KEYS and list(battle["peer"])[-1] == "expired"
    # [ff9mapkit netsync s133] `act`, the FIFTH sub-object (after `end`), its `host` half and that half's fixed sub-objects
    act = battle["act"]["host"]
    assert list(battle) == ["host", "peer", "menu", "end", "act"] and list(battle["act"]) == ["host", "guest"]
    assert tuple(act) == FG.NETSYNC_ACT_HOST_KEYS and tuple(act["kinds"]) == FG.NETSYNC_ACT_KINDS_KEYS
    assert tuple(act["vfx"]) == FG.NETSYNC_ACT_VFX_KEYS and tuple(act["loop"]) == FG.NETSYNC_ACT_LOOP_KEYS
    assert tuple(act["tape"]) == FG.NETSYNC_ACT_TAPE_KEYS
    # [ff9mapkit netsync s134] `act.guest`, after `host`, and its fixed sub-objects
    guest = battle["act"]["guest"]
    assert tuple(guest) == FG.NETSYNC_ACT_GUEST_KEYS and tuple(guest["levers"]) == FG.NETSYNC_ACT_GUEST_LEVERS_KEYS
    assert tuple(guest["grace"]) == FG.NETSYNC_ACT_GUEST_GRACE_KEYS
    assert tuple(guest["window"]) == FG.NETSYNC_ACT_GUEST_WINDOW_KEYS
    assert tuple(guest["aborts"]) == FG.NETSYNC_ACT_GUEST_ABORTS_KEYS == BW.ACT_ABORTS_KEYS
    assert tuple(guest["discarded"]) == FG.NETSYNC_ACT_GUEST_DISCARDED_KEYS == ("pending", "running")
    # [ff9mapkit netsync s135] `act.guest.hold`, after `last`, and its fixed `lag`; [ff9mapkit netsync s136] then
    # `act.guest.fallback`, the LAST key of `act.guest`
    assert list(guest)[-3:] == ["last", "hold", "fallback"] and tuple(guest["hold"]) == FG.NETSYNC_ACT_GUEST_HOLD_KEYS
    assert tuple(guest["hold"]["lag"]) == FG.NETSYNC_ACT_GUEST_HOLD_LAG_KEYS == BW.ACT_HOLD_LAG_KEYS
    assert tuple(guest["fallback"]) == FG.NETSYNC_ACT_GUEST_FALLBACK_KEYS
    top = list(prev_doc)
    assert top[top.index("diorama"):top.index("battle") + 1] == ["diorama", "session", "menu_refusal", "battle"], top
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
    # [ff9mapkit netsync s133] ...and `actbench`'s later ops (s134+: empty at s133 -- both of its ops came with the verb)
    for table, ops_of in ((Session.NETSYNC_BBENCH_OP_CAPS, FG.bbench_ops), (Session.NETSYNC_BENCH_OPS, None),
                          (Session.NETSYNC_ACTBENCH_OP_CAPS, FG.actbench_ops)):
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
            "end.flee.gil_now": "HarnessGilNow",
            # [ff9mapkit netsync s133] the action tape's state ("off" at rest; the catch line's null is "failed to build")
            "act.host.tape.state": "HarnessActTapeState",
            # [ff9mapkit netsync s134] the replay's levers at rest: the ini's ActionReplay (1) and this machine's SFXRework
            # -- `on` true, `rework` true, `knob` 1 (the catch line's false / false / -1 is "the block failed to build")
            "act.guest.on": "HarnessActGuestOn", "act.guest.rework": "HarnessActGuestRework",
            "act.guest.knob": "HarnessActGuestKnob",
            # [ff9mapkit netsync s135] the hold's levers at rest (`on` / `lifeskip` true; the catch line's false = "failed")
            "act.guest.hold.on": "HarnessHoldOn", "act.guest.hold.lifeskip": "HarnessHoldLifeSkip",
            # [ff9mapkit netsync s136] fallback A's lever at rest (`on` true; the catch line's false = "failed")
            "act.guest.fallback.on": "HarnessFallbackOn"}
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
                 "s111", "s112", "s113", "s114", "s115", "s116", "s117", "s118", "s119", "s120", "s121",
                 "s131", "s132",                              # [ff9mapkit netsync s131] (s122-s130 unused: group 2 is s133-s141)
                 "s133",                                      # [ff9mapkit netsync s133] group 2's first
                 "s134",                                      # [ff9mapkit netsync s134] the guest action replay
                 "s135",                                      # [ff9mapkit netsync s135] the replay hit hold
                 "s136"]                                      # [ff9mapkit netsync s136] fallback A
#: [ff9mapkit netsync s132] the stages that add NO harness key (the agent is the previous stage's; no State accessor
#: tells them -- s132 changed only an absent SessionGraceMs's default)
BATTLE_KEYLESS_LEVELS = ("s132",)


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
    # [ff9mapkit netsync R3 s120/s121] ...and the blocks from `diorama` on in the agent's order (`session`, `menu_refusal`)
    tail = [k for k in want if k in ("diorama", "session", "menu_refusal", "battle")]
    assert [k for k in doc if k in tail] == tail, (level, list(doc))
    for block in ("session", "menu_refusal"):
        if block in want:
            assert list(doc[block]) == list(want[block]), (level, block)
    if "battle" in want:
        assert set(_leaves(_battle_of(doc))) == set(_leaves(_battle_of(want))), \
            set(_leaves(_battle_of(doc))) ^ set(_leaves(_battle_of(want)))
        for sub in _battle_of(want):                     # ...in the agent's order
            assert list(_battle_of(doc)[sub]) == list(_battle_of(want)[sub]), (level, sub)
    # (the patches that rewrite the "unknown sub-verb" line: s100-s103 and s106 -- [ff9mapkit netsync s133] and s133)
    lines = [p for p in ("s100", "s101", "s102", "s103", "s106", "s133") if int(p[1:]) <= int(level[1:])]
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
            "coop_flee", "coop_flee_gil", "coop_defeat",
            # [ff9mapkit netsync R3 s118-s121] the sitting-A round, one per patch
            "coop_handback_report", "coop_diorama_hold", "coop_session_grace", "coop_menu_refusal",
            # [ff9mapkit netsync s131] the expired seq
            "coop_peer_adopt",
            # [ff9mapkit netsync s133] the host action-start lane
            "coop_act_host",
            # [ff9mapkit netsync s134] the guest action replay
            "coop_act_guest",
            # [ff9mapkit netsync s135] the replay hit hold
            "coop_act_hold",
            # [ff9mapkit netsync s136] fallback A
            "coop_act_fallback")
    keyed = [lv for lv in BATTLE_LEVELS if lv not in BATTLE_KEYLESS_LEVELS]
    assert len(caps) == len(keyed) - 1
    table = State.NETSYNC_BATTLE_ACCESSORS
    none = State({"frame": 1})
    assert all(getattr(none, c) is None for c in caps) and all(getattr(none, n) is None for n in table.values())
    assert none.coop_battle is None and none.coop_peer_end_manifest is None
    s99 = State({"frame": 1, "netsync": _battle_block("s99")})
    assert all(getattr(s99, c) is False for c in caps) and all(getattr(s99, n) is None for n in table.values())
    # [ff9mapkit netsync s132] a keyless stage publishes the previous one's block, so it reads every capability True
    for level in BATTLE_KEYLESS_LEVELS:
        assert _battle_block(level) == _battle_block(BATTLE_LEVELS[BATTLE_LEVELS.index(level) - 1]), level
    for i, level in enumerate(keyed[1:]):
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
    """The `netsync.diorama` R3 keys (s111 intro, s112 swirl_clamp, s114 live; [ff9mapkit netsync R3 s119] hold) the live
    agent publishes are exactly the accessor table's paths (+ the four whole-block accessors)."""
    nothing, _ = _agent_netsync_nothing()
    leaves = set(_dio_leaves(nothing["diorama"]))
    table = State.NETSYNC_DIORAMA_ACCESSORS
    assert set(table) - leaves == {"intro", "intro.swirl_clamp", "live", "hold"}, sorted(set(table) ^ leaves)
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


# =========================================================================== [ff9mapkit netsync R3 s118-s121]
# THE SITTING-A FIX ROUND (studies/battle-coop/R3-SITTING-A-FIXES.md): s118 the hand-back needs a live guest (HOST), s119
# the diorama hold keyed on the PEER, s120 the session grace, s121 the audible menu refusal (GUEST). No new verb or op; the
# harness stays at protocol 5 (additive keys, each capability told by its PRESENCE). Every pure decision's twin
# (battlewire) EVALUATES the engine's OWN selftest rows, read off the stack in order (_cs_block + _run_cs_rows), so a
# row's arguments, its verdict or its order changed on either side turns a test red; the deployed s117 is the stand-in with
# FG.NETSYNC_SITTING_A_CAPS removed (S117_CAPS: the calibration's red). [ff9mapkit netsync s131] ...and s131's cap with
# them (the ladder has no gaps); the DEPLOYED s121 -- s131's calibration red -- is the stand-in without FG.NETSYNC_S131_CAPS.
# [ff9mapkit netsync s132] ...and every older stage drops s132's cap too; s131 -- s132's calibration red -- is the stand-in
# without FG.NETSYNC_S132_CAPS. [ff9mapkit netsync s133] THE STAND-INS ARE LADDER PREFIXES now (audit 3.1 / 4.1: a
# subtraction would silently take in every later cap -- s133's `actstart` included): each is every cap through its own
# rung, and S132_CAPS -- s133's calibration red -- joins them.

import inspect                                                          # noqa: E402

S117_CAPS = _all_caps_through("defeat")
S121_CAPS = _all_caps_through("menurefusal")
S131_CAPS = _all_caps_through("expiredseq")
S132_CAPS = _all_caps_through("grace40")
S133_CAPS = _all_caps_through("actstart")                              # [ff9mapkit netsync s134] s134's calibration red
S134_CAPS = _all_caps_through("actreplay")                             # [ff9mapkit netsync s135] s135's calibration red
S135_CAPS = _all_caps_through("acthold")                               # [ff9mapkit netsync s136] s136's calibration red
_CS_STRING = re.compile(r'"((?:[^"\\]|\\.)*)"')


def _new_side(file_name: str, patch_bytes: bytes) -> list:
    """One patch's sections for ``file_name`` as NEW-side lines: ``(hunk, kind, stripped text)`` -- kind "+" (added) or
    " " (context); removed lines dropped."""
    out, hunk = [], 0
    for path, sec in msr.sections(patch_bytes):
        if not path or path.replace("\\", "/").rsplit("/", 1)[-1] != file_name:
            continue
        for ln in sec.decode("utf-8", "replace").splitlines():
            if ln.startswith("@@"):
                hunk += 1
            elif ln[:1] in (" ", "+") and not ln.startswith("+++"):
                out.append((hunk, ln[:1], ln[1:].strip()))
    return out


def _cs_block(file_name: str, start: str, stop: str = "catch (Exception err)") -> list:
    """The NEW-side lines (stripped) of one block as the LAST live patch whose hunk holds ALL of it writes it: from a line
    starting with ``start`` up to the first line equal to ``stop``, context and added lines in order, inside ONE hunk.
    Then every line is checked against the live stack: an added line must be net-present and no line may be net-REMOVED
    (a later patch that rewrote one, in a hunk that did not hold the whole block, leaves this read stale -- and red)."""
    block = None
    for name in msr.stack():
        if name in msr.DEAD:
            continue
        new = _new_side(file_name, (msr.PATCHES / name).read_bytes())
        for i, (hunk, _kind, text) in enumerate(new):
            if not text.startswith(start):
                continue
            j = next((k for k in range(i, len(new)) if new[k][2] == stop and new[k][0] == hunk), None)
            if j is not None and all(h == hunk for h, _k, _t in new[i:j]):
                block = [(k, t) for _h, k, t in new[i:j]]
    assert block, (file_name, start)
    net = {}
    for sign, text in _changed_lines(file_name):
        net[text] = net.get(text, 0) + sign
    # (a generic short line -- a brace, `ref rows, ref fail);` -- says nothing about WHICH block it sits in: skipped)
    stale = [t for k, t in block if len(t) > 24 and (net.get(t, 0) < 0 or (k == "+" and net.get(t, 0) <= 0))]
    assert not stale, stale
    return [t for _k, t in block]


def _changed_lines(file_name: str):
    """Every (+1 | -1, stripped text) the live stack adds to / removes from ``file_name`` (removed lines included)."""
    from ._patchstack import _changed
    return _changed(file_name, r".", None)


def _added_after(patch: str, file_name: str, before: str, mine: str) -> bool:
    """In ONE patch's hunk, the line it ADDS containing ``mine`` comes after a line containing ``before`` (the patch put
    its line right behind the earlier one: file order, read off the patch itself)."""
    new = _new_side(file_name, _patch_bytes(patch))
    for i, (hunk, kind, text) in enumerate(new):
        if kind == "+" and mine in text:
            return any(h == hunk and before in t for h, _k, t in new[:i])
    return False


def _strip_comment(line: str) -> str:
    """A C# line without its trailing ``//`` comment (string literals kept whole)."""
    out, i, quoted = [], 0, False
    while i < len(line):
        c = line[i]
        if quoted:
            out.append(c)
            if c == "\\" and i + 1 < len(line):
                out.append(line[i + 1])
                i += 1
            elif c == '"':
                quoted = False
        elif c == '"':
            quoted = True
            out.append(c)
        elif line.startswith("//", i):
            break
        else:
            out.append(c)
        i += 1
    return "".join(out).strip()


def _split_statements(code: str) -> list:
    """``code`` split on its top-level ``;`` (string literals kept whole)."""
    out, cur, quoted, i = [], [], False, 0
    while i < len(code):
        c = code[i]
        cur.append(c)
        if quoted:
            if c == "\\" and i + 1 < len(code):
                cur.append(code[i + 1])
                i += 1
            elif c == '"':
                quoted = False
        elif c == '"':
            quoted = True
        elif c == ";":
            cur.pop()
            out.append("".join(cur).strip())
            cur = []
        i += 1
    if "".join(cur).strip():
        out.append("".join(cur).strip())
    return [s for s in out if s]


def _balanced(text: str, at: int) -> int:
    """The index just past the parenthesised group opening at ``text[at]`` (string literals already masked)."""
    depth = 0
    for k in range(at, len(text)):
        depth += {"(": 1, ")": -1}.get(text[k], 0)
        if depth == 0:
            return k + 1
    raise AssertionError(f"unbalanced: {text!r}")


def _cs_expr(expr: str, out_names: bool = False) -> str:
    """One C# boolean / arithmetic expression of a selftest row as Python: string literals kept (C# escapes decoded),
    ``ref``/``out`` arguments dropped (the twins' wrappers read and write them in the namespace), ``UIManager.UIState.X``
    -> "X", ``new Byte[] { .. }`` -> bytes, an array initialiser -> a list, ``x.Length`` -> len(x), true/false/null, the
    local const ``None`` -> ``NONE_``, && / || / ! (each ``!`` around its whole operand). [ff9mapkit netsync s131] A sole
    ``ref`` argument drops too (``F(ref m)`` -> ``F()``), ``default(T)`` -> ``T()``, and with ``out_names`` each ``out x``
    is passed BY NAME (the string ``'x'``: the wrapper writes ``ns['x']``) -- for a selftest whose out locals vary by call."""
    strings = []

    def keep(m):
        strings.append(repr(m.group(1).replace('\\"', '"').replace("\\\\", "\\")))
        return f"__S{len(strings) - 1}__"

    def keep_name(m):
        strings.append(repr(m.group(1)))
        return f"__S{len(strings) - 1}__"

    code = _CS_STRING.sub(keep, expr)
    code = re.sub(r"\bUIManager\.UIState\.(\w+)", lambda m: repr(m.group(1)), code)
    code = re.sub(r"\bnew Byte\[\]\s*\{([^{}]*)\}", r"bytes([\1])", code)
    code = re.sub(r"^\{([^{}]*)\}$", r"[\1]", code.strip())
    code = re.sub(r"\b(\w+)\.Length\b", r"len(\1)", code)
    code = re.sub(r"\bref \w+,\s*", "", code)
    code = re.sub(r"\(ref \w+\)", "()", code)                           # [ff9mapkit netsync s131] PeerLaneForget(ref m)
    code = re.sub(r"\bout (\w+)", keep_name, code) if out_names else re.sub(r",\s*out \w+", "", code)
    code = re.sub(r"\bdefault\((\w+)\)", r"\1()", code)                 # [ff9mapkit netsync s131] default(PeerLaneMemo)
    code = re.sub(r"\bNone\b", "NONE_", code)
    code = re.sub(r"\btrue\b", "True", code)
    code = re.sub(r"\bfalse\b", "False", code)
    code = re.sub(r"\bnull\b", "None", code)
    code = code.replace("&&", " and ").replace("||", " or ")
    while True:
        m = re.search(r"!(?!=)", code)
        if not m:
            break
        k = m.end()
        while code[k] == " ":
            k += 1
        if code[k] == "(":
            end = _balanced(code, k)
        else:
            w = re.match(r"[\w.]+", code[k:])
            assert w, code
            end = k + w.end()
            if end < len(code) and code[end] == "(":
                end = _balanced(code, end)
        code = code[:m.start()] + "(not " + code[k:end] + ")" + code[end:]
    for i, s in enumerate(strings):
        code = code.replace(f"__S{i}__", s)
    return code


_DECL = re.compile(r"^(?:const )?(?:Int32|Boolean|String|Byte|UIManager\.UIState|PeerLaneMemo)(?:\[\])? (\w+)"
                   r"(?: = (.+))?$")
_ROW = re.compile(r'^(?:Row|WatchRow|MenuRow)\((.*), "((?:[^"\\]|\\.)*)", ref rows, ref fail\)$', re.S)
#: [ff9mapkit netsync s131] several locals declared at once, uninitialised (``Int32 staleAt, reopenAt, refused``), and a
#: bare call statement (its result dropped: its ref / out arguments are its effect -- ``PeerExpireStep(ref m, 5, N)``)
_DECLS = re.compile(r"(?:Int32|Boolean|String|Byte) (\w+(?:, \w+)+)")
_CALL = re.compile(r"\w+\(.*\)", re.S)


def _cs_program(lines: list) -> list:
    """A selftest block's lines -> an ordered list of statements and ``("for", var, array, body)`` loops (the one loop
    shape the selftests use: ``for (Int32 k = 0; k < arr.Length; k++) { .. }``). Comments, braces and ``try`` drop out."""
    out, buf, i = [], [], 0
    lines = [_strip_comment(ln) for ln in lines
             if not re.match(r"(?:internal|private|public) static ", ln)]       # the method's own signature

    def flush():
        if buf:
            out.extend(_split_statements(" ".join(buf)))
            buf.clear()
    while i < len(lines):
        ln = lines[i]
        m = re.fullmatch(r"for \(Int32 (\w+) = 0; \1 < (\w+)\.Length; \1\+\+\)", ln)
        if m:
            flush()
            assert lines[i + 1] == "{", lines[i:i + 2]
            depth, j = 1, i + 2
            while depth:
                depth += {"{": 1, "}": -1}.get(lines[j], 0)
                j += 1
            out.append(("for", m.group(1), m.group(2), _cs_program(lines[i + 2:j - 1])))
            i = j
            continue
        if ln and ln not in ("{", "}", "try"):
            buf.append(ln)
        i += 1
    flush()
    return out


def _run_cs_rows(program: list, ns: dict) -> list:
    """Run a selftest program in ``ns`` (the twins and constants by their C# names): declarations and assignments
    evaluate, each Row asserts its expression true for the twins; ``if (c) x = v`` and the one loop shape run as C#
    would. Returns the row names in order. [ff9mapkit netsync s131] ``ns["__out_names__"]`` true passes every ``out x``
    by name (:func:`_cs_expr`); a multi-local declaration and a bare call statement run too."""
    names = []
    outs = bool(ns.get("__out_names__"))
    for item in program:
        if isinstance(item, tuple):
            _tag, var, arr, body = item
            for k in range(len(ns[arr])):
                ns[var] = k
                names += _run_cs_rows(body, ns)
            continue
        st = " ".join(item.split())
        m = _ROW.match(st)
        if m:
            got = eval(_cs_expr(m.group(1), outs), ns)                 # noqa: S307 -- the stack's own selftest rows
            assert got is True, f"row {m.group(2)!r} ({' '.join(m.group(1).split())}) is {got!r} for the twin"
            names.append(m.group(2))
            continue
        m = re.fullmatch(r"if \((.*)\) (\w+) = (.+)", st)
        if m and _balanced(st, 3) == len("if (" + m.group(1) + ")"):
            if eval(_cs_expr(m.group(1), outs), ns):                    # noqa: S307
                ns[m.group(2)] = eval(_cs_expr(m.group(3), outs), ns)   # noqa: S307
            continue
        m = _DECLS.fullmatch(st)
        if m:                                                           # [ff9mapkit netsync s131] Int32 a, b, c
            ns.update({name: None for name in m.group(1).split(", ")})
            continue
        if _CALL.fullmatch(st) and _balanced(st, st.index("(")) == len(st):
            eval(_cs_expr(st, outs), ns)                                # noqa: S307 -- [ff9mapkit netsync s131] a bare call
            continue
        m = _DECL.match(st) or re.fullmatch(r"(\w+) = (.+)", st)
        assert m, f"an unparsed selftest statement: {st!r}"
        name = "NONE_" if m.group(1) == "None" else m.group(1)          # (the C# local const `None`, as _cs_expr spells it)
        ns[name] = None if m.group(2) is None else eval(_cs_expr(m.group(2), outs), ns)   # noqa: S307
    return names


def _cs_params(file_name: str, method: str) -> list:
    """A C# method's parameter names (``ref`` / ``out`` ones marked), read off its signature in the stack."""
    sig = _cs_block(file_name, f"internal static {method}(", "{")
    text = " ".join(sig)
    inner = text[text.index("(") + 1:text.rindex(")")]
    return [" ".join(p.split()[:-2] + [p.split()[-1]]) if p.split()[0] in ("ref", "out") else p.split()[-1]
            for p in inner.split(",")]


def _snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def _twin_params(fn) -> list:
    return [p.rstrip("_") for p in inspect.signature(fn).parameters]


def test_the_sitting_a_twins_take_the_engines_parameters_in_its_order():
    """Each twin's parameters ARE its C# method's, in order (camelCase -> snake_case; `ref seen` is the latch dict; an
    `out` result is the twin's return): a parameter added or moved on either side turns this red."""
    for file_name, method, fn, fix in (
            ("NetSyncBattle.cs", "Boolean GuestOwnsFromReport", BW.guest_owns_from_report, {}),
            ("NetSyncBattle.cs", "Boolean GuestOwnsStep", BW.guest_owns_step, {"ref seen": "latch"}),
            ("NetSyncClient.cs", "Int32 DioramaWatchStep", BW.diorama_watch_step, {}),
            ("NetSyncClient.cs", "Int32 SessionGraceStep", BW.session_grace_step, {}),
            ("NetSyncClient.cs", "Boolean SessionRampArms", BW.session_ramp_arms, {}),
            ("NetSyncClient.cs", "Int32 ParseSessionGrace", BW.parse_session_grace, {}),
            ("NetSyncField.cs", "Int32 MenuKeyStep", BW.menu_key_step, {}),
            ("NetSyncField.cs", "Int32 MenuKeyRoute", BW.menu_key_route, {}),
            # [ff9mapkit netsync s131] the expired seq: `ref m` is the memo dict
            ("NetSyncBattle.cs", "Int32 PeerAdoptStep", BW.peer_adopt_step, {"ref m": "m"}),
            ("NetSyncBattle.cs", "Boolean PeerExpireStep", BW.peer_expire_step, {"ref m": "m"}),
            ("NetSyncBattle.cs", "void PeerLaneForget", BW.peer_lane_forget, {"ref m": "m"})):
        cs = [fix.get(p, fix.get(_snake(p), _snake(p))) for p in _cs_params(file_name, method)
              if not p.startswith("out ")]
        assert cs == _twin_params(fn), (method, cs, _twin_params(fn))


# ---- s118: the ownership rule
def test_guest_owns_twins_evaluate_every_s118_control_selftest_row_off_the_stack():
    """GuestOwnsFromReport / GuestOwnsStep's twins against ControlSelfTest's OWN s118 block, EVALUATED in order: the 13
    `own:` rows (the decoded-report rows through the codec twins) and the 7 `step:` sequences over the per-battle latch --
    and the whole selftest is 53 rows (33 before s118), the proof line's count."""
    assert _battle_text("const Byte N = 0x41;")
    ns = dict(BW.CS_BATTLE_CONSTANTS, N=0x41, m=None, t=None, n=None, b=None, seen=False)

    def owns_step(trailer, nonce, boot, battle):                     # GuestOwnsStep(ref seen, ...)
        latch = {"seen": ns["seen"]}
        out = BW.guest_owns_step(latch, trailer, nonce, boot, battle)
        ns["seen"] = latch["seen"]
        return out

    def decode(frame, battle):                                       # DecodeControl(.., out m, out t, out n, out b)
        d = BW.decode_control(frame, battle)
        if d is None:
            return False
        ns.update(m=d["menu"], t=d["trailer"], n=d["nonce"], b=d["boot"])
        return True

    ns.update(GuestOwnsFromReport=BW.guest_owns_from_report, GuestOwnsStep=owns_step, DecodeControl=decode,
              BuildControl=BW.encode_control)
    names = _run_cs_rows(_cs_program(_cs_block("NetSyncBattle.cs", "// --- [ff9mapkit netsync R3 s118] the ownership rule")),
                         ns)
    assert len(names) == BW.CONTROL_SELFTEST_ROWS - BW.CONTROL_SELFTEST_ROWS_S114 == 20, names
    assert sum(n.startswith("own: ") for n in names) == 13 and sum(n.startswith("step: ") for n in names) == 7
    assert "step: declined latches (the sitting-A shape)" in names
    # [ff9mapkit netsync s131] NetSyncBattle.cs carries a second selftest from s131 (PeerAdoptSelfTest, its 20 rows)
    rows = sum("ref rows, ref fail);" in ln for ln in net_lines("NetSyncBattle.cs", r".", _prefix("s121")))
    assert rows == BW.CONTROL_SELFTEST_ROWS == 53, rows
    assert sum("ref rows, ref fail);" in ln for ln in net_lines("NetSyncBattle.cs", r".", _prefix("s132"))) == \
        BW.CONTROL_SELFTEST_ROWS + BW.ADOPT_SELFTEST_ROWS == 73
    # [ff9mapkit netsync s133] ...and a third (ActionSelfTest, its 30 rows)
    assert sum("ref rows, ref fail);" in ln for ln in _stack_text("NetSyncBattle.cs")) == \
        BW.CONTROL_SELFTEST_ROWS + BW.ADOPT_SELFTEST_ROWS + BW.ACTION_SELFTEST_ROWS == 103
    assert sum("ref rows, ref fail);" in ln for ln in net_lines("NetSyncBattle.cs", r".", _prefix("s117"))) == \
        BW.CONTROL_SELFTEST_ROWS_S114 == 33


def test_the_ownership_rule_keeps_a_refused_frames_byte_one_shut():
    """ParseControl's s118 half (parse_control_owned): an owning frame keeps its byte 1; a refused one (DECLINED, BUSY,
    NONE after the latch, another battle) reads SHUT -- no Wait freeze from a guest that commands nothing -- and the
    loopback under `bench boot auto` owns whatever it reports (its latch still moves); a 2-byte frame owns (an older
    guest); a malformed frame is None and moves nothing."""
    n = 0x41
    latch = BW.new_own_latch()
    d = BW.parse_control_owned(BW.encode_control(BW.CTL_DEEP, n, BW.BOOT_LIVE), n, latch)
    assert d["owns"] and d["menu"] == BW.CTL_DEEP and latch["seen"]
    d = BW.parse_control_owned(BW.encode_control(BW.CTL_DEEP, n, BW.BOOT_DECLINED), n, latch)
    assert not d["owns"] and d["menu"] == BW.CTL_SHUT and d["boot"] == BW.BOOT_DECLINED
    d = BW.parse_control_owned(BW.encode_control(BW.CTL_ROOT, n, BW.BOOT_NONE), n, latch)
    assert not d["owns"] and d["menu"] == BW.CTL_SHUT                     # NONE after the latch
    fresh = BW.new_own_latch()
    assert BW.parse_control_owned(BW.encode_control(BW.CTL_ROOT, n, BW.BOOT_NONE), n, fresh)["owns"]   # the panel-only guest
    d = BW.parse_control_owned(BW.encode_control(BW.CTL_ROOT, n, BW.BOOT_BUSY), n, fresh, loopback_auto=True)
    assert d["owns"] and d["menu"] == BW.CTL_ROOT and fresh["seen"]        # the loopback owns; the latch still rose
    assert BW.parse_control_owned(bytes([0, 2]), n, BW.new_own_latch())["owns"]
    other = BW.new_own_latch()
    d = BW.parse_control_owned(BW.encode_control(BW.CTL_ROOT, n - 1, BW.BOOT_LIVE), n, other)
    assert not d["owns"] and not other["seen"]                            # another battle never latches
    assert BW.parse_control_owned(bytes([1, 2]), n, other) is None and not other["seen"]
    assert BW.refused_report_phrase(n, BW.BOOT_DECLINED, n) == "it reports declined for this battle"
    assert BW.refused_report_phrase(n, BW.BOOT_NONE, n) == \
        "it reports none for this battle after reporting a diorama of it"
    assert BW.refused_report_phrase(n - 1, BW.BOOT_LIVE, n) == "its report names another battle (nonce 64, live)"
    for piece in ('return "it reports " + boot + " for this battle" + (_rptBoot == BootNone ? " after reporting a diorama of '
                  'it" : "");', 'return "its report names another battle (nonce " + _rptNonce + ", " + boot + ")";'):
        assert _battle_text(piece), piece


def test_parse_controls_s118_half_is_the_engines_statement_for_statement():
    """[ff9mapkit netsync R3 s118] The ENGINE half the twin above mirrors -- the row evaluator covers GuestOwnsStep /
    GuestOwnsFromReport only, so ParseControl's own s118 statements are pinned here, in order: the step's verdict OR the
    loopback exemption, the lane stamp on every valid frame, the ownership stamp on an owning one only, byte 1 SHUT on a
    refused one. And the exemption is the selftest pump's alone, under `bench boot auto` (BenchBoot < 0; an explicit
    `bench boot none` meets the rule): a real peer's frame and a `bctl` stamp pass none -- the stand-in's loopback reads the
    same test. Dropping `else menuRead = CtlShut;`, or moving the exemption's bound, turns this red."""
    block = [ln.split("//")[0].strip() for ln in _cs_block("NetSyncBattle.cs", "Boolean owns = GuestOwnsStep(",
                                                          "_ctlTrailer = trailer;")]
    assert [ln for ln in block if ln] == [
        "Boolean owns = GuestOwnsStep(ref _rptDioramaSeen, trailer, rptNonce, rptBoot, _battleNonce) || loopbackAuto;",
        "_ctlLaneTick = now;", "if (owns)", "_assistTick = now;", "else", "menuRead = CtlShut;"], block
    assert _battle_text("private static void ParseControl(Byte[] payload, Boolean loopbackAuto = false)")
    calls = sorted({ln.split("//")[0].strip() for ln in _stack_text("NetSyncBattle.cs")
                    if re.match(r"\s*ParseControl\(", ln.split("//")[0])})
    assert calls == ["ParseControl(BenchLapseFrame(BenchBootFrame(GuestControl(_peerView))), BenchBoot < 0);",
                     "ParseControl(frame);", "ParseControl(socket.GetRemoteControl());"], calls
    assert BW.BENCH_BOOT["auto"] < 0 <= min(v for k, v in BW.BENCH_BOOT.items() if k != "auto")
    assert "auto = nb.bench_boot < 0" in inspect.getsource(FakeGame._nb_loopback_control)


# ---- s119: the diorama hold keyed on the peer
def _watch_ns() -> dict:
    """The namespace DioramaWatchSelfTest / SessionGraceSelfTest run in: the constants, and the twins under their C# names
    -- WatchAt built from ITS OWN body on the stack (its parameters mapped onto DioramaWatchStep's arguments)."""
    ns = dict(BW.CS_CLIENT_CONSTANTS, w=None, note=None)
    head = " ".join(_cs_block("NetSyncClient.cs", "private static Int32 WatchAt(", "}"))
    params = re.search(r"WatchAt\((.*?)\)\s*\{", head).group(1)
    names = [p.split()[-1] for p in params.split(",") if not p.split()[0] == "out"]
    call = re.search(r"return DioramaWatchStep\((.*), out why\);", head).group(1)
    args = [a.strip() for a in call.split(",")]

    def watch_step(*a):                                               # DioramaWatchStep(.., out w)
        v, why = BW.diorama_watch_step(*a)
        ns["w"] = why
        return v

    def watch_at(*vals):                                              # WatchAt(.., out w)
        env = dict(BW.CS_CLIENT_CONSTANTS, **dict(zip(names, vals)))
        return watch_step(*[eval(_cs_expr(x), env) for x in args])     # noqa: S307

    def parse(raw):                                                   # ParseSessionGrace(raw, out note)
        v, ns["note"] = BW.parse_session_grace(raw)
        return v

    ns.update(DioramaWatchStep=watch_step, WatchAt=watch_at, SessionGraceStep=BW.session_grace_step,
              SessionRampArms=BW.session_ramp_arms, ParseSessionGrace=parse)
    return ns


def test_diorama_watch_step_evaluates_every_watcher_selftest_row_off_the_stack():
    """DioramaWatchStep's twin against DioramaWatchSelfTest's OWN rows, EVALUATED in order through WatchAt (itself read off
    the stack: from s120 it passes the stall cap = the cap, so the s119 rows read as before) -- sitting A's cut holds,
    the cap's boundary, the stalled lane, the genuinely-over pair and its fences, the settle, a decided leave, live
    wins, and the four sequences: 24 rows, the proof line's count."""
    names = _run_cs_rows(_cs_program(_cs_block("NetSyncClient.cs", "internal static Boolean DioramaWatchSelfTest(")),
                         _watch_ns())
    assert len(names) == BW.WATCH_SELFTEST_ROWS == 24, names
    assert names[3] == "sitting A: a cut holds" and len(set(names)) == len(names)


def test_the_sitting_a_row_left_on_s56_and_holds_on_s119():
    """THE CALIBRATING ROW (R3-SITTING-A-FIXES.md s119): IsConnected=1 (the local bridge's hop), the position lane stale
    (GetRemote invalid: PEER-ALIVE false), the battle lane stale, host field 0, nothing terminal. The s56 predicate (stale
    + link UP = over) LEAVES at once -- sitting A's ~2 s leave and stamped skip; the s119 step HOLDS, and keeps holding
    to the cap (s119: 8 s; s120: the 30 s grace), then leaves on the cap. The genuine end -- the peer alive on its field
    for the settle -- leaves on both."""
    n, alive = 0x41, BW.peer_alive(True, False)
    assert alive is False and BW.peer_alive(True, True) and not BW.peer_alive(False, True)
    assert BW.s56_watch_step(False, 0, n, True, 0) == BW.WATCH_LEAVE_FINAL
    s, c119, grace = BW.DIORAMA_SETTLE_MS, BW.hold_cap_ms(None), BW.hold_cap_ms(BW.SESSION_GRACE_DEFAULT_MS)
    assert (c119, grace) == (8000, 40000)                              # [ff9mapkit netsync s132] the default grace
    for cap in (c119, grace):
        step = lambda stale: BW.diorama_watch_step(False, 0, n, alive, -1, False, stale, 0, s, cap,    # noqa: E731
                                                   BW.DIORAMA_STALL_CAP_MS, BW.WATCH_WHY_NONE)
        assert step(0) == (BW.WATCH_HOLD, BW.WATCH_WHY_NONE) and step(6000) == (BW.WATCH_HOLD, BW.WATCH_WHY_NONE)
        assert step(cap) == (BW.WATCH_HOLD, BW.WATCH_WHY_NONE)
        assert step(cap + 1) == (BW.WATCH_LEAVE_FINAL, BW.WATCH_WHY_HOLD_CAP)
    # the s56 predicate held only with the hop DOWN (to its 8 s), which behind the bridge never happens under a cut
    assert BW.s56_watch_step(False, 0, n, False, 8000) == BW.WATCH_HOLD
    assert BW.s56_watch_step(False, 0, n, False, 8001) == BW.WATCH_LEAVE_FINAL
    assert BW.s56_watch_step(True, n, n, True, 0) == BW.WATCH_NOTHING and BW.s56_watch_step(True, 7, n, True, 0) == 2
    assert BW.diorama_watch_step(False, 0, n, True, 250, False, s, s, s, grace, BW.DIORAMA_STALL_CAP_MS, 0) == \
        (BW.WATCH_LEAVE_FINAL, BW.WATCH_WHY_HOST_FIELD)
    # the s56 lines are gone from the live stack, the s119 predicate replaced them (read off the s119 patch)
    assert net_lines("NetSyncClient.cs", re.escape("Boolean transportUp = _socket != null && _socket.IsConnected;"),
                     _prefix("s118")) and not _battle_text("Boolean transportUp = _socket != null && _socket.IsConnected;")
    assert not _battle_text(BW.LOG_S56_BLIP_HOLD)
    assert any(BW.LOG_S56_BLIP_HOLD in ln for ln in net_lines("NetSyncClient.cs", r"mid-battle link blip", _prefix("s118")))


# ---- s120: the session grace
#: SessionGraceSelfTest's rows (s120: 25 + the six stall-cap rows of its review fix) -- the first and the last of each part
GRACE_ROW_MARKS = ("the peer alive is live (seen or not)", "past the grace: ended", "mirroring + ended: the ramp arms",
                   "FollowHost off mid-mirror arms at once", "30000", "absent keeps the default, quietly",
                   "seq: sitting A's ~20 s restore keeps the session",
                   "the diorama holds exactly as long as the session lives",
                   "the peer alive on field 0 past the stall cap leaves, inside the grace",
                   "seq: a 25 s cut whose fight ended unseen leaves at the settle once the peer is back")


def test_session_grace_twins_evaluate_every_grace_selftest_row_off_the_stack():
    """SessionGraceStep / SessionRampArms / ParseSessionGrace / DioramaWatchStep's twins against SessionGraceSelfTest's
    OWN rows, EVALUATED in order -- the step, the ramp, the ini clamp, the two bench-leg sequences, THE ONE-VALUE LAW (its
    loop run as C# runs it) and the stall cap's six rows: 31 rows (the corrected count -- NOT the implementer's 25)."""
    names = _run_cs_rows(_cs_program(_cs_block("NetSyncClient.cs", "internal static Boolean SessionGraceSelfTest(")),
                         _watch_ns())
    assert len(names) == BW.GRACE_SELFTEST_ROWS == 31, names
    assert all(mark in names for mark in GRACE_ROW_MARKS), set(GRACE_ROW_MARKS) - set(names)
    # the proof block's two NetSyncClient selftests are every `ref rows, ref fail` row the file carries
    assert sum("ref rows, ref fail);" in ln for ln in _stack_text("NetSyncClient.cs")) == \
        BW.WATCH_SELFTEST_ROWS + BW.GRACE_SELFTEST_ROWS


def test_the_session_grace_twins_hold_the_bench_legs():
    """The s120 bench legs as the twins read them (R3-SITTING-A-FIXES.md s120): a 20 s blackhole is GRACE throughout and
    arms no ramp (the old 3 s debounce's moment included), the peer back is LIVE; a 40 s blackhole ENDS just past the
    grace and arms the ramp once; FollowHost dropped mid-mirror arms at once; the countdown and the overlay's seconds."""
    g = BW.SESSION_GRACE_DEFAULT_MS
    for out_ms in (0, BW.EXIT_RAMP_DEBOUNCE_S117_MS + 1, 20000, g):
        st = BW.session_grace_step(False, True, out_ms, g)
        assert st == BW.SESSION_GRACE and not BW.session_ramp_arms(True, False, True, st), out_ms
    assert BW.session_grace_step(True, True, 20000, g) == BW.SESSION_LIVE
    assert BW.session_grace_step(False, False, 0, g) == BW.SESSION_NONE
    ended = BW.session_grace_step(False, True, g + 1, g)
    assert ended == BW.SESSION_ENDED and BW.session_ramp_arms(True, False, True, ended)
    assert not BW.session_ramp_arms(True, True, True, ended) and not BW.session_ramp_arms(False, False, True, ended)
    assert BW.session_ramp_arms(True, False, False, BW.SESSION_LIVE)
    assert BW.session_left_ms(BW.SESSION_GRACE, 2000, g) == g - 2000 and BW.session_left_ms(BW.SESSION_LIVE, 0, g) == -1
    assert BW.session_left_ms(BW.SESSION_GRACE, g + 5, g) == 0
    assert (BW.overlay_left_sec(28000), BW.overlay_left_sec(27001), BW.overlay_left_sec(0)) == (28, 28, 0)
    assert [BW.session_state_name(s) for s in range(5)] == ["none", "live", "grace", "ended", None]
    assert [BW.ramp_cause_name(c) for c in range(4)] == [None, "grace", "config", "unfollow"]


def test_parse_session_grace_says_the_engines_words():
    """ParseSessionGrace's notes ARE the engine's (its two literals, spliced): malformed keeps the default, outside
    5000-40000 clamps with the reason; quotes are accepted, empty / absent is quiet; an Int32 overflow is malformed."""
    assert BW.parse_session_grace("12345") == (12345, None)
    assert BW.parse_session_grace(' "20000" ') == (20000, None)
    v, note = BW.parse_session_grace("thirty")
    assert v == 40000 and note == "SessionGraceMs 'thirty' malformed (want ms, 5000-40000) -- keeping 40000"
    v, note = BW.parse_session_grace_s120("thirty")                     # an s120-s131 engine's default
    assert v == 30000 and note == "SessionGraceMs 'thirty' malformed (want ms, 5000-40000) -- keeping 30000"
    v, note = BW.parse_session_grace("0")
    assert v == 5000 and note == ("SessionGraceMs 0 is outside 5000-40000 -- clamped to 5000 ms (a shorter grace ends "
                                  "the session on an ordinary Wi-Fi re-association)")
    v, note = BW.parse_session_grace("99999")
    assert v == 40000 and note.endswith("clamped to 40000 ms (the bridge gives up on its upstream at 45 s, the relay at "
                                        "60 s)")
    assert BW.parse_session_grace("99999999999")[0] == 40000 and BW.parse_session_grace("1_000")[0] == 40000
    assert BW.parse_session_grace("") == (40000, None) and BW.parse_session_grace(None) == (40000, None)
    assert BW.parse_session_grace_s120(None) == (30000, None) and BW.parse_session_grace_s120("99999")[0] == 40000
    for piece in ('note = "SessionGraceMs \'" + s + "\' malformed (want ms, " + SessionGraceMinMs + "-" + SessionGraceMaxMs '
                  '+ ") -- keeping "',
                  'note = "SessionGraceMs " + n + " is outside " + SessionGraceMinMs + "-" + SessionGraceMaxMs + " -- '
                  'clamped to " + c + " ms ("',
                  '+ (n < SessionGraceMinMs ? "a shorter grace ends the session on an ordinary Wi-Fi re-association"',
                  ': "the bridge gives up on its upstream at 45 s, the relay at 60 s") + ")";'):
        assert _battle_text(piece), piece


# ---- s121: the audible menu refusal
def test_menu_key_twins_evaluate_every_menu_refusal_selftest_row_off_the_stack():
    """MenuKeyStep / MenuKeyRoute / MenuKeyName's twins against MenuRefusalSelfTest's OWN rows, EVALUATED in order (the
    UIState constants by name): the step's truth table, the names, the four route rows -- 14 rows (NOT the implementer's
    10)."""
    ns = dict(BW.CS_FIELD_CONSTANTS, MenuKeyStep=BW.menu_key_step, MenuKeyRoute=BW.menu_key_route,
              MenuKeyName=BW.menu_key_name)
    names = _run_cs_rows(_cs_program(_cs_block("NetSyncField.cs", "internal static Boolean MenuRefusalSelfTest(")), ns)
    assert len(names) == BW.MENU_SELFTEST_ROWS == 14, names
    assert sum("ref rows, ref fail);" in ln for ln in net_lines("NetSyncField.cs", r".")) == 14
    assert "a dialogue window up: the dialogue path" in names


def test_menu_key_now_reads_the_route_the_press_takes():
    """HarnessMenuKeyNow on the twin: "audible" on FieldHUD / WorldHUD for a mirroring guest, "silent" on the diorama's
    BattleHUD and on Pause, "dialog" under a dialogue window (not paused) or with no scene for the state, "off" under a
    scene's MENUOFF, "open" with no mirror; the place is wldMapNo on WorldHUD (review S121-R2) and the latch is its own
    class there."""
    now = BW.menu_key_now
    assert now(True, True, "FieldHUD", False, False) == "audible" and now(True, True, "WorldHUD", False, False) == "audible"
    assert now(True, True, "BattleHUD", False, False) == "silent" and now(True, True, "Pause", True, True) == "silent"
    assert now(True, True, "FieldHUD", True, False) == "dialog" and now(True, True, "Initial", False, False) == "dialog"
    assert now(True, False, "FieldHUD", True, False) == "dialog" and now(True, False, "Quit", False, False) == "dialog"
    assert now(False, True, "FieldHUD", False, False) == "off" and now(True, False, "FieldHUD", False, False) == "open"
    assert now(True, True, "FieldHUD", False, False, has_scene=False) == "dialog"
    assert BW.menu_refusal_place("WorldHUD", 250, 9000) == 9000 and BW.menu_refusal_place("FieldHUD", 250, 9000) == 250
    assert BW.menu_refusal_line("FieldHUD", 250) == "[NetSync] main menu suppressed (following guest) on field 250"
    assert BW.menu_refusal_line("WorldHUD", 9000).endswith("on world map 9000")
    assert BW.menu_refusal_latch("WorldHUD") != BW.menu_refusal_latch("FieldHUD") == "main menu"
    # the pieces the engine splices the line from, and the scene table (UIManager.GetSceneFromState is stock code)
    assert _battle_text('Log.Message("[NetSync] " + what + " suppressed (following guest) on " + where);') or \
        net_lines("NetSyncField.cs", re.escape('Log.Message("[NetSync] " + what + " suppressed (following guest) on " + '
                                               'where);'))
    assert net_lines("NetSyncField.cs", re.escape('DeclineOnceAt("main menu (world map)", "main menu", place, "world '
                                                  'map " + place)'))
    assert net_lines("NetSyncField.cs", re.escape('return DeclineOnceAt(what, what, fld, "field " + fld);'))
    assert {"FieldHUD", "WorldHUD", "BattleHUD", "Pause"} <= BW.UI_SCENE_STATES
    assert not {"Initial", "QuadMistBattle", "Quit", "PreEnding"} & BW.UI_SCENE_STATES


def test_the_sitting_a_constants_and_names_are_the_stacks():
    """Every constant the round's twins mirror is the stack's by its C# name (NetSyncBattle / NetSyncClient /
    NetSyncField), and every name a twin returns is a literal the stack returns -- the watch states and whys, the session
    states, the ramp causes, the overlays, the menu key's names; the hold cap's seam reads the grace from s120 (8000
    before it); the proof block's four R3 lines are logged in this order."""
    for file_name, table in (("NetSyncBattle.cs", BW.CS_OWN_CONSTANTS), ("NetSyncClient.cs", BW.CS_CLIENT_CONSTANTS),
                             ("NetSyncField.cs", BW.CS_FIELD_CONSTANTS)):
        cs = _cs_int_consts(file_name)
        for name, value in table.items():
            if name in cs:
                assert cs[name][0] == value, (file_name, name, cs[name], value)
            else:                                           # (a declaration whose comment carries a `;`)
                assert any(re.search(rf"\b{name} = {value}[,;]", ln) for ln in _stack_text(file_name)), (name, value)
    groups = {"state": ("WatchNothing", "WatchHold", "WatchLeaveFinal"),
              "why": ("WatchWhyNewNonce", "WatchWhyTerminal", "WatchWhyHostField", "WatchWhyHoldCap", "WatchWhyStallCap"),
              "session": ("SessionNone", "SessionLive", "SessionGrace", "SessionEnded"),
              "ramp": ("RampCauseGrace", "RampCauseConfig", "RampCauseUnfollow")}
    for table, group in ((BW.WATCH_STATE_NAMES, "state"), (BW.WATCH_WHY_NAMES, "why"),
                         (BW.SESSION_STATE_NAMES, "session"), (BW.RAMP_CAUSE_NAMES, "ramp")):
        consts = {BW.CS_CLIENT_CONSTANTS[k]: k for k in groups[group]}
        assert set(consts) == set(table), group
        for value, name in table.items():
            assert any(re.match(rf'case {re.escape(consts[value])}: return "{re.escape(name)}";', ln)
                       for ln in _stack_text("NetSyncClient.cs")), (group, value, name)
    assert {re.match(r'case Ovl\w+: return "(\w+)";', ln).group(1) for ln in _stack_text("NetSyncClient.cs")
            if re.match(r'case Ovl\w+: return "(\w+)";', ln)} == set(BW.OVERLAY_NAMES)
    field = {v: k for k, v in BW.CS_FIELD_CONSTANTS.items()}
    for value, name in BW.MENU_KEY_NAMES.items():
        assert net_lines("NetSyncField.cs", re.escape(f'case {field[value]}: return "{name}";')), name
    assert _battle_text("private static Int32 DioramaHoldCapMs { get { return _sessionGraceMs; } }")
    assert net_lines("NetSyncClient.cs", re.escape("private static Int32 DioramaHoldCapMs { get { return DioramaBlipHoldMs; "
                                                   "} }"), _prefix("s119"))
    assert _battle_text("FF9Sfx.FF9SFX_Play(102);") or net_lines("NetSyncField.cs", re.escape("FF9Sfx.FF9SFX_Play(102);"))
    # the proof block's order: each round patch put its line right behind the previous one (read off its own hunk)
    for patch, before, mine in (("s119", BW.PROOF_CONTROL, BW.PROOF_WATCH), ("s120", BW.PROOF_WATCH, BW.PROOF_GRACE),
                                ("s121", BW.PROOF_GRACE, BW.PROOF_MENU)):
        assert _added_after(patch, "NetSyncClient.cs", f'"[NetSync] {before}"', f'"[NetSync] {mine}"'), patch


def test_the_rounds_log_needles_are_the_stacks_words():
    """Each needle a bench greps is a literal head of a stack line (the s110 hand-back lines, s118's refusal line, s119's
    hold / resume / give-up lines, s120's outage / resume / give-up lines); the s117 RED markers are still the stack's
    (the same lines fire on a genuine end). Their order in the archived sitting-A log is the test below."""
    for needle in (BW.LOG_HANDBACK_CAPTURE, BW.LOG_HANDBACK_HANDED, BW.LOG_HANDBACK_REFUSED, BW.LOG_DIORAMA_HOLD_CUT,
                   BW.LOG_DIORAMA_HOLD_STALL, BW.LOG_DIORAMA_RESUME, BW.LOG_DIORAMA_GAVE_UP, BW.LOG_SESSION_OUTAGE,
                   BW.LOG_SESSION_BACK, BW.LOG_SESSION_GAVE_UP, BW.LOG_RED_LEAVE_REQUESTED, BW.LOG_RED_WATCHER_SETTLED):
        assert any(needle in lit for f in BATTLE_FILES for ln in _stack_text(f) for lit in _literals(ln)), needle
    assert any(BW.LOG_RED_SESSION_ENDED in ln for ln in net_lines("NetSyncState.cs", r"session ended"))


#: [ff9mapkit netsync R3] the archived sitting-A guest log -- the s117 engine's real output, the calibration source. It
#: lives under the gitignored /.harness-runs/ (the coop-battle-r3 worktree's), so a fresh checkout, the main repo and the
#: nightly gate do not have it: the test below SKIPS there, visibly, rather than passing on nothing.
SITTING_A_GUEST_LOG = REPO / ".harness-runs" / "sittingA-20261014" / "laptop-Memoria.log"


def test_the_sitting_a_guest_log_reads_the_red_markers_in_the_cuts_order():
    """The calibration half of the needles above: in the archived sitting-A guest log the cut's episode is the one the
    WATCHER settled (a LEAVE request also ends every genuine fight -- :155-166): a LEAVE request within the 6 lines before
    the watcher-leave, the session-end reload within the 10 after it, and the s56 hold line nowhere (it never ran behind
    the bridge)."""
    if not SITTING_A_GUEST_LOG.exists():
        pytest.skip(f"the archived sitting-A guest log is not in this checkout ({SITTING_A_GUEST_LOG}: /.harness-runs/ is "
                    "gitignored) -- the s117 calibration of the round's log needles did NOT run")
    lines = SITTING_A_GUEST_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
    w = next(i for i, ln in enumerate(lines) if BW.LOG_RED_WATCHER_SETTLED in ln)
    assert any(BW.LOG_RED_LEAVE_REQUESTED in ln for ln in lines[max(0, w - 6):w]), lines[w - 6:w + 1]
    assert any(BW.LOG_RED_SESSION_ENDED in ln for ln in lines[w:w + 10]), lines[w:w + 10]
    assert not any(BW.LOG_S56_BLIP_HOLD in ln for ln in lines)           # the s56 hold never ran behind the bridge


# ---- the accessors and the stand-in's blocks
def _top_leaves(doc: dict) -> dict:
    """``netsync.session`` / ``netsync.menu_refusal`` as path -> value (the s120 / s121 top-level blocks)."""
    return {f"{b}.{k}": v for b in ("session", "menu_refusal") if isinstance(doc.get(b), dict) for k, v in doc[b].items()}


def test_every_top_r3_key_has_an_accessor_and_every_accessor_a_key():
    """The s120 `session` and s121 `menu_refusal` keys the live agent publishes are exactly the accessor table's paths (+
    the two whole-block accessors), and each accessor reads its sentinel's type (null = a string reads "")."""
    nothing, _ = _agent_netsync_nothing()
    leaves = _top_leaves(nothing)
    table = State.NETSYNC_TOP_ACCESSORS
    assert set(table) - set(leaves) == {"session", "menu_refusal"}, sorted(set(table) ^ set(leaves))
    assert set(leaves) <= set(table)
    st = State({"frame": 1, "netsync": nothing})
    for path, name in table.items():
        got = getattr(st, name)
        sentinel = leaves.get(path, nothing.get(path))
        if sentinel is None:
            assert got == "", (path, got)
        elif isinstance(sentinel, dict):
            assert got == sentinel and got is not sentinel, path
        else:
            assert got == sentinel and type(got) is type(sentinel), (path, got, sentinel)


def test_state_reads_the_sitting_a_keys_absent_as_cannot():
    """On the deployed s117's catch block every s118-s121 accessor reads None ("this engine cannot") and each capability
    False; on the live block they read their sentinels and True; no `netsync` block at all reads None."""
    old = State({"frame": 1, "netsync": _catch_doc_in("s117")})
    live = State({"frame": 1, "netsync": _agent_netsync_nothing()[0]})
    caps = ("coop_handback_report", "coop_diorama_hold", "coop_session_grace", "coop_menu_refusal")
    assert [getattr(old, c) for c in caps] == [False] * 4 and [getattr(live, c) for c in caps] == [True] * 4
    assert [getattr(State({"frame": 1}), c) for c in caps] == [None] * 4
    new = list(State.NETSYNC_TOP_ACCESSORS.values()) + [n for p, n in State.NETSYNC_DIORAMA_ACCESSORS.items()
                                                        if p.startswith("hold")] + \
        ["coop_handback_refused_report", "coop_handback_refused_now", "coop_handback_diorama_seen"]
    for name in new:
        assert getattr(old, name) is None, name
        assert getattr(live, name) is not None, name
    assert (live.coop_handback_refused_report, live.coop_handback_refused_now, live.diorama_hold_cap_ms,
            live.session_grace_ms, live.menu_refusal_now) == (0, False, -1, -1, "")


def test_a_fresh_stand_in_publishes_the_agents_session_and_menu_refusal_sentinels(game):
    """With no client the stand-in's `session` and `menu_refusal` ARE the agent's catch-line blocks -- same keys, same
    order, same sentinels -- except the two LIVE reads: `session.grace_ms` (the committed SessionGraceMs, a static) and
    `menu_refusal.now` (the UIManager's answer for a Menu press now)."""
    nothing, _ = _agent_netsync_nothing()
    doc = FakeGame(game)._netsync_doc()
    live = {"session.grace_ms": "NetSyncClient.HarnessSessionGraceMs", "menu_refusal.now": "NetSyncField.HarnessMenuKeyNow"}
    for block in ("session", "menu_refusal"):
        assert list(doc[block]) == list(nothing[block]), block
    got, want = _top_leaves(doc), _top_leaves(nothing)
    for path, value in want.items():
        if path not in live:
            assert got[path] == value, (path, got[path], value)
    for getter in live.values():
        assert any("Netsync." + getter in ln for ln in _stack_text("HarnessAgent.cs")), getter
    assert got["session.grace_ms"] == BW.SESSION_GRACE_DEFAULT_MS and got["menu_refusal.now"] in BW.MENU_KEY_NAMES.values()
    assert tuple(nothing["session"]) == FG.NETSYNC_SESSION_KEYS
    assert tuple(nothing["menu_refusal"]) == FG.NETSYNC_MENU_REFUSAL_KEYS
    assert tuple(nothing["diorama"]["hold"]) == FG.NETSYNC_DIORAMA_HOLD_KEYS
    assert list(nothing["battle"]["host"]["handback"])[-3:] == ["refused_report", "refused_now", "diorama_seen"]


@pytest.mark.parametrize("level,cap", [("s119", BW.DIORAMA_HOLD_CAP_S119_MS), ("s120", BW.SESSION_GRACE_DEFAULT_S120_MS),
                                       ("s121", BW.SESSION_GRACE_DEFAULT_S120_MS),
                                       ("s131", BW.SESSION_GRACE_DEFAULT_S120_MS), ("s132", BW.SESSION_GRACE_DEFAULT_MS)])
def test_the_hold_cap_reads_8000_on_s119_and_the_grace_from_s120(game, level, cap):
    """`netsync.diorama.hold.cap_ms` is the ONE seam's reading: s119's 8000, from s120 the session grace (by default
    30000 on s120-s131, [ff9mapkit netsync s132] 40000 from s132; the ini's value through the engine's clamp);
    `settle_ms` 500 on both."""
    fake = FakeGame(game)
    fake.netsync_caps = _caps_at(level)
    hold = fake._netsync_doc()["diorama"]["hold"]
    assert (hold["cap_ms"], hold["settle_ms"]) == (cap, BW.DIORAMA_SETTLE_MS)
    if level != "s119":
        for raw, want in (("20000", 20000), (' "12000" ', 12000), ("0", 5000), ("99999", 40000), ("thirty", cap)):
            fake.ini_session_grace_ms = raw
            doc = fake._netsync_doc()
            assert doc["diorama"]["hold"]["cap_ms"] == doc["session"]["grace_ms"] == want, raw


def test_the_session_block_sits_at_rest_on_the_selftest_role(game):
    """s120 on the stand-in: the outage clock runs only on a GUEST with a transport, so the block sits at rest -- `state`
    null with no client, "none" once the selftest role is up; the selftest tick composes the overlay "off" (detail 0) and
    spawns the mirror beside the player on a field (`ghost`); `mirroring` is the stand-in's story-mirror knob; no outage,
    no ramp, the counters 0."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(FIELD)
        st = g.state
        assert (st.session_state, st.session_overlay, st.session_overlay_detail, st.session_ghost) == ("", "", -1, False)
        st = g.netsync("selftest", 1)
        st = g.wait_for(lambda s: s.session_overlay == "off", timeout=4.0, what="the selftest overlay")
        assert (st.session_state, st.session_overlay_detail, st.session_ghost, st.session_ghost_held) == ("none", 0, True,
                                                                                                        False)
        assert (st.session_left_ms, st.session_out_ms, st.session_outages, st.session_resumes, st.session_gaveup,
                st.session_last_ms) == (-1, -1, 0, 0, 0, -1)
        assert (st.session_peer_alive, st.session_seen_live, st.session_ramp_pending, st.session_ramp_cause) == \
            (False, False, False, "")
        assert st.session_mirroring is False and st.coop_session_grace is True
        fake.story_mirroring = True
        st = g.wait_for(lambda s: s.session_mirroring is True, timeout=4.0, what="the mirror knob")
        assert st.diorama_hold_state == "" and st.diorama_hold_holds == 0 and \
            st.diorama_hold_cap_ms == BW.SESSION_GRACE_DEFAULT_MS == 40000


def test_s132_the_grace_default_is_its_maximum_and_s131_reads_30000(game):
    """[ff9mapkit netsync s132] An ABSENT [Netsync] SessionGraceMs reads 40000 = SessionGraceMaxMs on the s132 stack and
    30000 on s131 (the calibration red: the stand-in without FG.NETSYNC_S132_CAPS); an explicit value reads the same on
    both, and a malformed one keeps THAT engine's default. Off the stack: the constant and the absent-key read (no
    "30000" literal left), the default never above the max (ParseSessionGrace returns it unclamped)."""
    const = "internal const Int32 SessionGraceDefaultMs = "
    now = [ln for ln in _stack_text("NetSyncClient.cs") if ln.startswith(const)]
    then = [ln for ln in net_lines("NetSyncClient.cs", re.escape(const), _prefix("s131")) if ln.startswith(const)]
    assert now == [const + "40000;"] and then == [const + "30000;"], (now, then)
    assert any(ln == "internal const Int32 SessionGraceMaxMs = 40000;  // under the bridge's 45 s redial hard cap (and the "
               "relay's 60 s rejoin grace)" for ln in _stack_text("NetSyncClient.cs"))
    assert BW.SESSION_GRACE_DEFAULT_MS == BW.SESSION_GRACE_MAX_MS == 40000 and BW.SESSION_GRACE_DEFAULT_S120_MS == 30000
    assert _battle_text('ini.GetSetting("Netsync", "SessionGraceMs", SessionGraceDefaultMs.ToString())')
    assert not _battle_text('"SessionGraceMs", "30000"')
    for caps, want in ((None, 40000), (S131_CAPS, 30000)):
        fake = FakeGame(game)
        if caps is not None:
            fake.netsync_caps = caps
        for raw, got_want in ((None, want), ("30000", 30000), ("40000", 40000), ("thirty", want), ("99999", 40000)):
            fake.ini_session_grace_ms = raw
            doc = fake._netsync_doc()
            assert doc["session"]["grace_ms"] == doc["diorama"]["hold"]["cap_ms"] == got_want, (caps, raw)


def _proof_lines(fake) -> list:
    if not fake.memoria_log.exists():
        return []
    return [ln for ln in fake.memoria_log.read_text(encoding="utf-8").splitlines() if "selftest: " in ln]


@pytest.mark.parametrize("caps,want", [
    ("live", [BW.proof_ok(BW.PROOF_CONTROL, 53), BW.proof_ok(BW.PROOF_WATCH, 24), BW.proof_ok(BW.PROOF_GRACE, 31),
              BW.proof_ok(BW.PROOF_MENU, 14), BW.proof_ok(BW.PROOF_ADOPT, 20), BW.proof_ok(BW.PROOF_ACTION, 30),
              BW.proof_ok(BW.PROOF_REPLAY, 34), BW.proof_ok(BW.PROOF_HOLD, 28), BW.proof_ok(BW.PROOF_FALLBACK, 30)]),
    # [ff9mapkit netsync s136] s135 (s136's calibration red): no 'action fallback' line
    ("s135", [BW.proof_ok(BW.PROOF_CONTROL, 53), BW.proof_ok(BW.PROOF_WATCH, 24), BW.proof_ok(BW.PROOF_GRACE, 31),
              BW.proof_ok(BW.PROOF_MENU, 14), BW.proof_ok(BW.PROOF_ADOPT, 20), BW.proof_ok(BW.PROOF_ACTION, 30),
              BW.proof_ok(BW.PROOF_REPLAY, 34), BW.proof_ok(BW.PROOF_HOLD, 28)]),
    # [ff9mapkit netsync s135] s134 (s135's calibration red): no 'action hold' line
    ("s134", [BW.proof_ok(BW.PROOF_CONTROL, 53), BW.proof_ok(BW.PROOF_WATCH, 24), BW.proof_ok(BW.PROOF_GRACE, 31),
              BW.proof_ok(BW.PROOF_MENU, 14), BW.proof_ok(BW.PROOF_ADOPT, 20), BW.proof_ok(BW.PROOF_ACTION, 30),
              BW.proof_ok(BW.PROOF_REPLAY, 34)]),
    # [ff9mapkit netsync s134] s133 (s134's calibration red): no 'action replay' line
    ("s133", [BW.proof_ok(BW.PROOF_CONTROL, 53), BW.proof_ok(BW.PROOF_WATCH, 24), BW.proof_ok(BW.PROOF_GRACE, 31),
              BW.proof_ok(BW.PROOF_MENU, 14), BW.proof_ok(BW.PROOF_ADOPT, 20), BW.proof_ok(BW.PROOF_ACTION, 30)]),
    # [ff9mapkit netsync s133] s132 (s133's calibration red): no 'action lane' line
    ("s132", [BW.proof_ok(BW.PROOF_CONTROL, 53), BW.proof_ok(BW.PROOF_WATCH, 24), BW.proof_ok(BW.PROOF_GRACE, 31),
              BW.proof_ok(BW.PROOF_MENU, 14), BW.proof_ok(BW.PROOF_ADOPT, 20)]),
    ("s121", [BW.proof_ok(BW.PROOF_CONTROL, 53), BW.proof_ok(BW.PROOF_WATCH, 24), BW.proof_ok(BW.PROOF_GRACE, 31),
              BW.proof_ok(BW.PROOF_MENU, 14)]),
    ("s119", [BW.proof_ok(BW.PROOF_CONTROL, 53), BW.proof_ok(BW.PROOF_WATCH, 24)]),
    ("s117", [BW.proof_ok(BW.PROOF_CONTROL, 33)]),
    ("s113", [])])
def test_the_proof_block_carries_the_rounds_lines_per_engine(game, caps, want):
    """The stand-in's selftest proof block: once per PROCESS, on the first selftest tick on a field, the R3 lines its
    engine carries, in the engine's order and in Memoria's line shape -- the deployed s117 logs only 'battle control
    selftest: OK (33 rows)' (S14-B2 green, S18-PROOF red there); the s121 stack 53 / 24 / 31 / 14 ([ff9mapkit netsync
    s131] the DEPLOYED s121: no 'peer adopt' line); the s131 stack adds 20 after them; an s113 engine none. A second
    selftest role in the same process logs nothing more. [s131 fix] This pins the STAND-IN against its own caps: no
    in-game bench reads the s119-s131 lines (S18-PROOF and S14-B2 read the control line alone, and coop_cut_hold's guest
    never runs the selftest role), so the s121 'no peer adopt line' red is the stand-in's, never yet observed in game."""
    fake = FakeGame(game)
    fake.netsync_caps = {"live": fake.netsync_caps, "s117": S117_CAPS, "s121": S121_CAPS,
                         "s132": S132_CAPS, "s133": S133_CAPS, "s134": S134_CAPS,
                         "s135": S135_CAPS}.get(caps) or _caps_at(caps)
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(FIELD)
        g.netsync("selftest", 1)
        g.wait_frames(10)
        lines = _proof_lines(fake)
        assert [ln.split("[NetSync] ", 1)[1] for ln in lines] == want, lines
        assert all(re.match(r"^\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}:\d{2} \|M\| \[NetSync\] ", ln) for ln in lines)
        g.netsync("selftest", 0)
        g.netsync("selftest", 1)
        g.wait_frames(10)
        assert len(_proof_lines(fake)) == len(want)
    assert all(_battle_text(f'Log.Message("[NetSync] {h}"') for h in (BW.PROOF_CONTROL, BW.PROOF_WATCH, BW.PROOF_GRACE,
                                                                      BW.PROOF_ADOPT, BW.PROOF_ACTION,
                                                                      BW.PROOF_REPLAY, BW.PROOF_HOLD,
                                                                      BW.PROOF_FALLBACK)) \
        and net_lines("NetSyncClient.cs", re.escape(f'Log.Message("[NetSync] {BW.PROOF_MENU}"'))


def _mlog_lines(fake, needle: str) -> list:
    if not fake.memoria_log.exists():
        return []
    return [ln for ln in fake.memoria_log.read_text(encoding="utf-8").splitlines() if needle in ln]


def _spliced(line: str, *pieces: str) -> bool:
    """The stand-in's ``line`` carries each of the engine's C# literals ``pieces`` IN ORDER -- every piece one literal of
    the live stack (so a reworded engine line turns the stand-in's red)."""
    at = 0
    for piece in pieces:
        assert _battle_text(f'"{piece}"'), piece
        at = line.find(piece, at)
        if at < 0:
            return False
        at += len(piece)
    return True


def _declined_leg(g, fake, refusal: str):
    """`bench boot live` (the latch rises), `bench lapse hold` -> the host's window captures slot 1, then `bench boot
    <refusal>` and `bench lapse end`: the state 60 frames on, and the returns / refused_report before it."""
    g.netsync("bench", "boot", "live")
    g.wait_for(lambda s: s.coop_handback_diorama_seen is not False, timeout=4.0, what="the latch (or no key)")
    g.netsync("bench", "lapse", "hold")
    st = g.wait_for(lambda s: s.turn_slot == 1, timeout=15.0, what="the capture")
    returns, rr0 = st.coop_handback_returns, st.coop_handback_refused_report
    g.netsync("bench", "boot", refusal)
    g.netsync("bench", "lapse", "end")
    g.wait_frames(60)
    return g.state, returns, rr0


@pytest.mark.parametrize("refusal,phrase", [("declined", "it reports declined for this battle"),
                                            ("busy", "it reports busy for this battle"),
                                            ("none", "it reports none for this battle after reporting a diorama of it"),
                                            ("stale", "its report names another battle (nonce ")])
def test_s118_a_guest_whose_diorama_is_not_live_keeps_its_slot_with_the_host(game, refusal, phrase):
    """s118 on the stand-in (the S18 legs): after a LIVE report raised the latch, a stall captures slot 1; the guest comes
    back reporting DECLINED (the sitting-A shape) / BUSY / NONE after the latch / a LIVE about another battle -- the host's
    window KEEPS the slot (no hand-back, `owed` false), `refused_now` true, `refused_report` +1 and ONE 'its slots stay'
    line naming the report; then `bench boot live` hands it back at the root, once. (Byte 1 is NOT judged here: while the
    host's window holds slot 1, G6 withholds its Ready bit and the loopback guest sends 0 under either rule -- the shut
    byte is read where it discriminates, in the test below.)"""
    fake = FakeGame(game)
    with session(game, fake) as g:
        st = _own_battle_two(g, fake)
        assert st.coop_handback_report is True and st.coop_handback_diorama_seen is False
        st, returns, rr0 = _declined_leg(g, fake, refusal)
        assert st.turn_slot == 1 and st.coop_handback_returns == returns and st.coop_handback_owed is False, refusal
        assert st.coop_handback_refused_now is True and st.coop_handback_refused_report == rr0 + 1
        assert st.coop_handback_diorama_seen is True
        stays = _mlog_lines(fake, BW.LOG_HANDBACK_REFUSED)
        assert len(stays) == 1 and phrase in stays[0], stays
        assert _spliced(stays[0], BW.LOG_HANDBACK_REFUSED, " -- its slots stay ",
                        "with the host's window (the host's ready loop commands them; G3 hands them back at the command "
                        "root once ", "it reports live or booting on this battle; logged once per own battle), "
                        "refused_report="), stays[0]
        cap = _mlog_lines(fake, BW.LOG_HANDBACK_CAPTURE)
        assert len(cap) == 1 and _spliced(cap[0], BW.LOG_HANDBACK_CAPTURE, " -- ", "the guest's control lane has been silent ",
                                           " ms (a stall)", "; its Ready bit is withheld while the host holds it (G6), and "
                                           "it is handed back at the command ", "root once the guest is live again (G3)",
                                           "; captures="), cap
        g.netsync("bench", "boot", "live")
        st = g.wait_for(lambda s: s.coop_handback_returns == returns + 1, timeout=8.0, what="LIVE hands it back")
        assert st.turn_slot != 1 and st.coop_handback_last["why"] == "handed back" and st.coop_handback_refused_now is False
        handed = _mlog_lines(fake, BW.LOG_HANDBACK_HANDED)
        assert len(handed) == 1 and len(_mlog_lines(fake, BW.LOG_HANDBACK_REFUSED)) == 1, handed
        assert _spliced(handed[0], "[NetSync] hand-back: guest slot ", " handed BACK to the guest -- its control lane is "
                        "live again ", "and the host's window sat at the command root (held ", " ms); the host's window "
                        "closed, the ", "slot's Ready bit returns (BTL-1), returns="), handed


def test_s118_a_refused_frame_reads_byte_one_shut_where_slot_one_stands_ready(game):
    """[ff9mapkit netsync R3 s118] ParseControl's shut byte, read where it DISCRIMINATES (coop_handback_live's L1 shape):
    a LIVE report raises the latch and OWNS, with slot 1 Ready and unheld -- `host.wait.menu` reads the loopback guest's
    own byte 2 (the root); then `bench boot none` with NO lapse (the lane stays live) is refused, and every publish from
    the first that shows the NONE parsed (`start_hold.guest.boot` 0) up to the host's capture reads byte 1 SHUT: slot 1
    is still Ready there, so the guest's own byte is still 2 and only the refusal shuts it. A stand-in that kept a
    refused frame's byte (the pre-s118 byte rule) reads 2 there and turns this red."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        _own_battle_two(g, fake)
        g.netsync("bench", "boot", "live")
        st = g.wait_for(lambda s: s.coop_handback_diorama_seen is True and s.coop_hold_guest_boot == BW.BOOT_LIVE
                        and s.coop_wait_menu == BW.CTL_ROOT, timeout=4.0, what="LIVE owns: the guest's own byte 2")
        assert st.turn_slot != 1 and st.coop_handback_held == -1 and st.coop_handback_refused_now is False
        g.netsync("bench", "boot", "none")
        samples = []
        for _ in range(120):                                # MenuStaleMs (2.5 s) to the capture; 6 s of frames
            g.wait_frames(3)
            st = g.state
            samples.append(st)
            if st.turn_slot == 1:
                break
        assert st.turn_slot == 1 and st.coop_handback_held == 1, "no capture after the refused NONE"
        parsed = [s for s in samples if s.coop_hold_guest_boot == BW.BOOT_NONE and s.coop_handback_held != 1]
        assert parsed, [(s.coop_hold_guest_boot, s.coop_handback_held) for s in samples[:6]]
        assert all(s.coop_wait_menu == BW.CTL_SHUT for s in parsed), [s.coop_wait_menu for s in parsed]
        assert st.coop_handback_refused_now is True and _mlog_lines(fake, BW.LOG_HANDBACK_REFUSED)


def test_s118_none_from_the_start_owns_and_the_deployed_s117_hands_a_declined_guest_back(game):
    """The two controls: `bench boot none` from the battle's start (no diorama report on it: the panel-only guest, review
    S118-NONE-PANEL) still owns -- the stall's hand-back fires, `diorama_seen` stays false, nothing refused; and the
    deployed s117 (the stand-in without the sitting-A caps) hands a DECLINED guest its slot back within a few frames of
    the stall's end -- THE CALIBRATION RED -- publishing none of the s118 keys."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        _own_battle_two(g, fake)                            # (`bench boot auto`: the stand-in NONE never raises the latch)
        st = g.netsync("bench", "boot", "none")
        assert st.coop_handback_diorama_seen is False
        g.netsync("bench", "lapse", "hold")
        st = g.wait_for(lambda s: s.turn_slot == 1, timeout=15.0, what="the capture")
        returns, rr0 = st.coop_handback_returns, st.coop_handback_refused_report
        g.netsync("bench", "lapse", "end")
        st = g.wait_for(lambda s: s.coop_handback_returns == returns + 1, timeout=8.0, what="NONE owns: handed back")
        assert st.coop_handback_diorama_seen is False and st.coop_handback_refused_report == rr0
        assert st.coop_handback_refused_now is False and not _mlog_lines(fake, BW.LOG_HANDBACK_REFUSED)
    fake = FakeGame(game)
    fake.netsync_caps = S117_CAPS
    with session(game, fake) as g:
        _own_battle_two(g, fake)
        st, returns, _rr0 = _declined_leg(g, fake, "declined")
        assert st.coop_handback_returns == returns + 1 and st.turn_slot != 1, "s117 kept a declined guest's slot"
        assert st.coop_handback_report is False and st.coop_handback_refused_report is None
        assert not _mlog_lines(fake, BW.LOG_HANDBACK_REFUSED) and _mlog_lines(fake, " handed BACK to the guest -- ")


def test_s118_a_release_forgets_the_latch_the_lever_raised(game):
    """The latch belongs to the reports that raised it: `bench boot declined` raises it (`diorama_seen` true), and the
    harness release that puts the lever back to auto forgets it (HarnessReleaseBench: `bench boot` back to auto in the
    selftest role)."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        _own_battle_two(g, fake)
        g.netsync("bench", "boot", "declined")
        g.wait_for(lambda s: s.coop_handback_diorama_seen is True, timeout=4.0, what="the latch")
        g.send("reset")
        st = g.wait_for(lambda s: s.netsync is not None and not s.netsync["forced"], timeout=5.0, what="the release")
        assert st.coop_handback_diorama_seen is False
        assert fake._nb.own_latch["seen"] is False and fake._nb.bench_boot == -1
    assert _battle_text("the lever's reports are forgotten with it (the latch;")


def test_a_mirroring_guests_menu_key_is_refused_audibly_once_per_place(game):
    """s121 on the stand-in (the T2 leg's shape): a guest whose story mirror is armed (the knob) on FieldHUD reads `now`
    "audible"; `press menu` buzzes -- count +1, lines +1, ONE 'main menu suppressed (following guest) on field N' line,
    ui_state stays FieldHUD; a second press on the same field: count +1, lines +0; under a dialogue window `now` reads
    "dialog" and the press is counted nowhere; the control row (no mirror) reads "open"; a scene's MENUOFF reads "off"."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(FIELD)
        st = g.state
        assert st.menu_refusal_now == "open" and st.coop_menu_refusal is True
        fake.story_mirroring = True
        st = g.wait_for(lambda s: s.menu_refusal_now == "audible", timeout=4.0, what="audible")
        c0, l0 = st.menu_refusal_count, st.menu_refusal_lines
        st = g.press("menu", 2)
        st = g.wait_for(lambda s: s.menu_refusal_count == c0 + 1, timeout=4.0, what="the refusal")
        assert st.menu_refusal_lines == l0 + 1 and st.ui_state == "FieldHUD" and st.menu_refusal_last_state == "FieldHUD"
        assert st.menu_refusal_last_field == FIELD and st.menu_refusal_age_ms >= 0 and st.menu_refusal_muted is False
        g.press("menu", 2)
        st = g.wait_for(lambda s: s.menu_refusal_count == c0 + 2, timeout=4.0, what="the second refusal")
        assert st.menu_refusal_lines == l0 + 1 and st.menu_refusal_silent == 0
        lines = _mlog_lines(fake, BW.LOG_MENU_SUPPRESSED)
        assert len(lines) == 1 and lines[0].endswith("|M| " + BW.menu_refusal_line("FieldHUD", FIELD)), lines
        assert fake._menu_refusal.buzzes == 2
        fake.say("A line the host's script opened.")
        st = g.wait_for(lambda s: s.menu_refusal_now == "dialog", timeout=4.0, what="dialog")
        g.press("menu", 2)
        st = stays(g, lambda s: s.menu_refusal_count == c0 + 2 and s.menu_refusal_silent == 0, frames=10,
                   what="a press under a window counted")
        fake.texts = []
        fake.menu_control_enable = False
        g.wait_for(lambda s: s.menu_refusal_now == "off", timeout=4.0, what="MENUOFF")
        fake.menu_control_enable, fake.story_mirroring = True, False
        g.wait_for(lambda s: s.menu_refusal_now == "open", timeout=4.0, what="the control row")


def test_the_deployed_s117_drops_a_mirroring_guests_menu_key_silently(game):
    """The s121 calibration red on the stand-in: without "menurefusal" no `menu_refusal` block is published and a
    mirroring guest's Menu press is dropped -- no line, nothing counted; ui_state stays FieldHUD."""
    fake = FakeGame(game)
    fake.netsync_caps = S117_CAPS
    fake.story_mirroring = True
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(FIELD)
        st = g.press("menu", 2)
        st = stays(g, lambda s: s.ui_state == "FieldHUD", frames=10, what="the menu stayed shut")
        assert st.coop_menu_refusal is False and st.menu_refusal_count is None and st.menu_refusal_now is None
        assert not _mlog_lines(fake, BW.LOG_MENU_SUPPRESSED)
        assert fake._menu_refusal.count == 0 and fake._menu_refusal.buzzes == 0


# =========================================================================== [ff9mapkit netsync s131]
# THE EXPIRED SEQ (studies/battle-coop/R3-SITTING-A-FIXES.md, "The hold-onset variance: the Pump null RE-ADOPT"): once the
# host's battle view runs out of freshness, the guest's Pump refuses the transport's repeats of that (nonce, seq). No new
# verb or op, wire v14, harness protocol 5: one additive key, `netsync.battle.peer.expired`, and one proof line. The twins
# (battlewire) EVALUATE PeerAdoptSelfTest's OWN rows off the stack, each rule's mutant fails a row, and the DEPLOYED s121
# -- s131's calibration red -- is the stand-in without FG.NETSYNC_S131_CAPS (S121_CAPS): every check below that reads the
# key or the proof line reads "cannot" / nothing there.

#: PeerAdoptSelfTest's rows the owner's fix shape names, the review's two re-written rows (S131-R1; their names are the
#: harness brief's, verbatim -- row 2 and row 13 of 20) and the calibration row
ADOPT_ROW_MARKS = ("a repeat of the expired seq after the null is NOT adopted",
                   "a new seq after it IS adopted, and clears the memo",
                   "a new nonce IS adopted (the same seq)",
                   "the first view ever IS adopted (seq 0 of nonce 0 too: an empty memo matches no frame)",
                   "Reset clears the memo",
                   "the memo bites only with nothing in hand (seq 6 in hand: the expired 5 IS news, as any other seq)",
                   "seq: a tail-67 cut re-opened the lane under the pre-s131 step (calibration)",
                   "seq: a stalled host re-sending one seq stays stale 9 s on (the stall cap's case; was re-adopted)")


class _CsStruct:
    """A twin's dict read through its C# struct's field names (``m.Armed`` -> ``d["armed"]``) -- PeerLaneMemo as the
    selftest's rows spell it."""

    def __init__(self, d: dict) -> None:
        self.d = d

    def __getattr__(self, name):
        try:
            return self.d[_snake(name)]
        except KeyError:
            raise AttributeError(name) from None


def _adopt_ns(step=BW.peer_adopt_step, expire=BW.peer_expire_step, forget=BW.peer_lane_forget) -> dict:
    """The namespace PeerAdoptSelfTest runs in: the constants by C# name, PeerLaneMemo (``default(PeerLaneMemo)``) as a
    fresh twin memo, and the twins under their C# names -- each ``ref m`` the local ``m`` (the test below checks it is the
    only one), each ``out`` local passed by name (AdoptReplay's vary by call)."""
    ns = dict(BW.CS_ADOPT_CONSTANTS, __out_names__=True, m=None)
    ns["PeerLaneMemo"] = lambda: _CsStruct(BW.new_peer_lane_memo())

    def replay(served, memo, stale_name, reopen_name):            # AdoptReplay(served, memo, out stale, out reopen)
        refused, ns[stale_name], ns[reopen_name] = BW.adopt_replay(served, memo)
        return refused

    ns.update(PeerAdoptStep=lambda seq, nonce, cur: step(ns["m"].d, seq, nonce, cur),
              PeerExpireStep=lambda cur, nonce: expire(ns["m"].d, cur, nonce),
              PeerLaneForget=lambda: forget(ns["m"].d), AdoptReplay=replay, CutScript=BW.cut_script)
    return ns


def _adopt_program() -> list:
    block = _cs_block("NetSyncBattle.cs", "internal static Boolean PeerAdoptSelfTest(")
    refs = set(re.findall(r"\bref (\w+)", " ".join(_strip_comment(ln) for ln in block)))
    assert refs == {"m", "rows", "fail"}, refs                          # (the wrappers bind `ref m` to the local `m`)
    return _cs_program(block)


def test_peer_adopt_twins_evaluate_every_adopt_selftest_row_off_the_stack():
    """PeerAdoptStep / PeerExpireStep / PeerLaneForget / AdoptReplay / CutScript's twins against PeerAdoptSelfTest's OWN
    rows, EVALUATED in order: the 15 step rows (the fix shape's 'a repeat of the expired seq after the null is NOT
    adopted', 'a new seq after it IS', 'a new nonce IS', 'the first view ever IS', 'Reset clears' among them) and the 5
    rows of Pump's lane order over served-frame scripts (tail 0, the tail-67 calibration under the pre-s131 step, tail 67,
    the host back, a stalled writer) -- 20 rows, the proof line's count. Rows 2 and 13 are the review's re-written ones."""
    names = _run_cs_rows(_adopt_program(), _adopt_ns())
    assert len(names) == BW.ADOPT_SELFTEST_ROWS == 20, names
    assert len(set(names)) == len(names) and all(mark in names for mark in ADOPT_ROW_MARKS), \
        set(ADOPT_ROW_MARKS) - set(names)
    assert names[1] == ADOPT_ROW_MARKS[3] and names[12] == ADOPT_ROW_MARKS[5], (names[1], names[12])
    assert sum(not n.startswith("seq: ") for n in names) == 15 and sum(n.startswith("seq: ") for n in names) == 5
    assert sum("ref rows, ref fail);" in ln for ln in net_lines("NetSyncBattle.cs", r".", [_patch_bytes("s131")])) == 20


def _mutant_step(rule: str):
    """PeerAdoptStep with ONE rule broken (the twin's own body otherwise)."""
    def step(m, seq, nonce, cur):
        if seq < 0:
            return BW.ADOPT_NONE
        if cur >= 0 and seq == cur:
            return BW.ADOPT_REPEAT
        hit = {"no_in_hand_guard": m["armed"] and seq == m["seq"] and nonce == m["nonce"],
               "no_armed": cur < 0 and seq == m["seq"] and nonce == m["nonce"],
               "no_nonce": cur < 0 and m["armed"] and seq == m["seq"],
               "no_seq": cur < 0 and m["armed"] and nonce == m["nonce"],
               "pre_s131": False}.get(rule, cur < 0 and m["armed"] and seq == m["seq"] and nonce == m["nonce"])
        if hit:
            if rule != "no_count":
                m["refused"] += 1
            return BW.ADOPT_REFUSED
        if rule != "no_clear":
            BW.peer_lane_forget(m)
        return BW.ADOPT_NEW
    return step


def _mutant_expire(m, cur_seq, cur_nonce):                            # a run-out that keeps the episode's count
    if cur_seq < 0:
        return False
    m.update(armed=True, seq=cur_seq, nonce=cur_nonce)
    return True


def _mutant_expire_unguarded(m, cur_seq, cur_nonce):                  # a run-out that arms with nothing in hand
    m.update(armed=True, seq=cur_seq, nonce=cur_nonce, refused=0)
    return cur_seq >= 0


@pytest.mark.parametrize("twins", [
    {"step": _mutant_step("no_in_hand_guard")}, {"step": _mutant_step("no_armed")}, {"step": _mutant_step("no_nonce")},
    {"step": _mutant_step("no_seq")}, {"step": _mutant_step("pre_s131")}, {"step": _mutant_step("no_clear")},
    {"step": _mutant_step("no_count")}, {"expire": _mutant_expire}, {"expire": _mutant_expire_unguarded},
    {"forget": lambda m: None}],
    ids=["no-in-hand-guard", "no-armed", "no-nonce", "no-seq", "pre-s131", "no-clear", "no-count", "expire-keeps-count",
         "expire-unguarded", "forget-no-op"])
def test_each_adopt_rule_mutant_fails_a_selftest_row(twins):
    """A CHECK THAT CANNOT FAIL is no check: each rule of the step / the run-out / Reset's forget, broken alone, fails one
    of the engine's own rows (S131-R1's row catches the dropped in-hand guard, row 2 the dropped Armed test)."""
    program = _adopt_program()                                          # (its own asserts outside the raises)
    with pytest.raises(AssertionError, match=r"^row ['\"]"):
        _run_cs_rows(program, _adopt_ns(**twins))


def test_the_adopt_constants_proof_line_and_pump_statements_are_the_stacks():
    """NetSyncBattle's s131 constants by C# name; the proof line logged RIGHT AFTER the menu refusal's (read off s131's own
    hunk) in the selftest proof block's shape; and Pump's s131 statements in order -- the adopt through the step (a NEW
    frame restamps, a REFUSED one is noted), and the run-out BEFORE the null (counted, its tick stamped) -- with the
    getters each reading its static, the memo's only while armed."""
    cs = _cs_int_consts("NetSyncBattle.cs")
    for name, value in BW.CS_ADOPT_CONSTANTS.items():
        assert name in cs and cs[name][0] == value, (name, cs.get(name), value)
    assert _added_after("s131", "NetSyncClient.cs", f'"[NetSync] {BW.PROOF_MENU}"', f'"[NetSync] {BW.PROOF_ADOPT}"')
    assert net_lines("NetSyncClient.cs", re.escape(f'Log.Message("[NetSync] {BW.PROOF_ADOPT}"'))
    assert net_lines("NetSyncClient.cs", re.escape('+ (adoptOk ? "OK (" + adoptDetail + ")" : "FAIL (" + adoptDetail + ")"));'))
    assert _battle_text('detail = fail == null ? rows + " rows" : "row \'" + fail + "\' failed (" + rows + " rows run)";')
    adopt = [ln.split("//")[0].strip() for ln in _cs_block("NetSyncBattle.cs", "Int32 adopt = PeerAdoptStep(",
                                                             "Byte[] peerRoster = socket.GetRemoteRoster();")]
    assert [ln for ln in adopt if ln] == [
        "Int32 adopt = PeerAdoptStep(ref _peerLane, view != null ? view.Seq : -1, view != null ? view.Nonce : -1,",
        "_peerView != null ? _peerView.Seq : -1);", "if (adopt == AdoptNew)", "{", "_peerView = view;",
        "_peerViewTick = Environment.TickCount;", "NetSyncEnd.NotePeer(view.Nonce, view.End);", "}",
        "else if (adopt == AdoptRefused)", "NoteRefusedReadopt();", "}"], adopt
    runout = [ln.split("//")[0].strip() for ln in _cs_block("NetSyncBattle.cs", "if (!live)", "ResetUi();")]
    assert [ln for ln in runout if ln] == [
        "if (!live)", "{", "if (_peerView != null && PeerExpireStep(ref _peerLane, _peerView.Seq, _peerView.Nonce))", "{",
        "_peerExpiries++;", "_peerExpiryTick = Environment.TickCount;", "}", "_peerView = null;", "_peerRoster = null;"], runout
    note = [ln.split("//")[0].strip() for ln in _cs_block("NetSyncBattle.cs", "private static void NoteRefusedReadopt()",
                                                            "_readoptLogged++;")]
    assert [ln for ln in note if ln] == [
        "private static void NoteRefusedReadopt()", "{", "_readoptFrames++;",
        "_readoptMs = Environment.TickCount - _peerExpiryTick;", "if (_peerLane.Refused != 1)", "return;",
        "_readoptEpisodes++;", "if (_peerLane.Nonce != _readoptLogNonce)", "{", "_readoptLogNonce = _peerLane.Nonce;",
        "_readoptLogged = 0;", "}"], note
    for piece in ("if (_readoptLogged <= ReadoptLogMax)", "else if (_readoptLogged == ReadoptLogMax + 1)",
                  "PeerLaneForget(ref _peerLane);", "_readoptLogNonce = -1;",
                  "public static Int32 HarnessPeerExpiredSeq { get { return _peerLane.Armed ? _peerLane.Seq : -1; } }",
                  "public static Int32 HarnessPeerExpiredNonce { get { return _peerLane.Armed ? _peerLane.Nonce : -1; } }",
                  "public static Int32 HarnessPeerExpiries { get { return _peerExpiries; } }",
                  "public static Int32 HarnessPeerReadoptsRefused { get { return _readoptEpisodes; } }",
                  "public static Int32 HarnessPeerReadoptFrames { get { return _readoptFrames; } }",
                  "public static Int32 HarnessPeerReadoptMs { get { return _readoptMs; } }",
                  "private static Int32 _readoptMs = -1;",
                  "private static Int32 _peerExpiryTick = Environment.TickCount - 60000;"):
        assert _battle_text(piece), piece
    # Reset() forgets the memo and re-arms the budget -- and adds nothing else (the counters are per process)
    new = _new_side("NetSyncBattle.cs", _patch_bytes("s131"))
    hunk = next(h for h, _k, t in new if t == "public static void Reset()")
    assert [t.split("//")[0].strip() for h, k, t in new if h == hunk and k == "+"] == \
        ["PeerLaneForget(ref _peerLane);", "_readoptLogNonce = -1;", "_readoptLogged = 0;"]


def test_the_pre_s131_test_is_the_line_s131_removed():
    """THE CALIBRATION: the one line s131 removed is s37's null-reset under s40's seq guard -- net-present through s121,
    gone from the live stack -- and :func:`BW.pre_s131_adopts` IS that test: with a fresh memo the s131 step adopts
    exactly where it did (the defect needs the memo to show), and with the memo armed only the expired frame's repeat
    with nothing in hand reads differently."""
    old = "if (view != null && (_peerView == null || view.Seq != _peerView.Seq))"
    assert net_lines("NetSyncBattle.cs", re.escape(old), _prefix("s121")) and not _battle_text(old)
    assert any(ln.startswith("-") and old in ln for ln in _patch_bytes("s131").decode("utf-8").splitlines())
    n = 0x41
    for seq in (-1, 0, 4, 5, 6):
        for cur in (-1, 0, 5, 6):
            assert BW.pre_s131_adopts(seq, cur) == (BW.peer_adopt_step(BW.new_peer_lane_memo(), seq, n, cur)
                                                    == BW.ADOPT_NEW), (seq, cur)
            for nonce in (n, n + 1):
                m = BW.new_peer_lane_memo()
                BW.peer_expire_step(m, 5, n)
                differs = BW.pre_s131_adopts(seq, cur) != (BW.peer_adopt_step(m, seq, nonce, cur) == BW.ADOPT_NEW)
                assert differs == (seq == 5 and nonce == n and cur < 0), (seq, cur, nonce)


def test_the_peer_lane_model_holds_the_bench_expectations():
    """battlewire.PeerLane -- Pump's lane with s131's statics -- on the selftest's scripts (10 ms Updates): a tail-67 cut
    reads count +1, refused +1, ms ~ the tail (less up to two Updates), one episode line, and the lane stays stale where
    the pre-s131 lane re-opened for a phantom 2000 ms; a tail-0 cut reads count +1, refused +0 and no line; the host back
    re-opens the lane at its first new seq (the memo cleared, the counters kept); a new nonce is news; a stalled writer
    stays stale -- and only then does the diorama reach s120's stall cap (THE OWNER-ACCEPTED SIDE EFFECT)."""
    n, f = BW.ADOPT_TEST_NONCE, BW.ADOPT_TEST_FRAME_MS
    lane = BW.PeerLane()
    live = lane.run(BW.cut_script(3000, 67, -1, 9000))
    edges = [i * f for i in range(1, len(live)) if live[i] != live[i - 1]]
    assert live[0] and edges == [5000], edges                          # live from the first frame, stale ONCE at 5000
    assert lane.doc() == {"seq": 3000 // BW.ADOPT_TEST_SAMPLE_MS, "nonce": n, "count": 1, "refused": 1, "frames": 6,
                          "ms": 60}
    assert 67 - 2 * f <= lane.doc()["ms"] <= 67
    assert lane.lines == [BW.readopt_line(n, 20, 1)] and lane.lines[0].startswith(BW.LOG_READOPT_REFUSED)
    old = BW.PeerLane(memo=False)
    phantom = old.run(BW.cut_script(3000, 67, -1, 9000))
    assert phantom[501] is True and sum(phantom[501:]) == 200 and not old.lines   # 5010..6999 ms: the phantom 2000 ms
    zero = BW.PeerLane()
    assert sum(zero.run(BW.cut_script(3000, 0, -1, 9000))[501:]) == 0
    assert (zero.doc()["count"], zero.doc()["refused"], zero.doc()["frames"], zero.doc()["ms"], zero.lines) == (1, 0, 0, -1, [])
    back = BW.PeerLane()
    flags = back.run(BW.cut_script(3000, 67, 9000, 12000))
    assert flags.index(True, 501) == 900 and back.doc() == {"seq": -1, "nonce": -1, "count": 1, "refused": 1, "frames": 6,
                                                             "ms": 60}
    other = BW.PeerLane()
    other.run(BW.cut_script(3000, 67, -1, 5020))                       # stale, the expired seq refused...
    assert other.pump(5030, (20, n + 1)) is True and other.doc()["seq"] == -1   # ...but a new nonce IS news
    stall = BW.PeerLane()
    flags = stall.run(BW.cut_script(3000, -1, -1, 14000))
    assert sum(flags[501:]) == 0 and stall.doc()["refused"] == 1 and stall.doc()["frames"] == 900
    assert stall.doc()["ms"] == 14000 - 5000 and len(stall.lines) == 1
    settle, cap, grace = BW.DIORAMA_SETTLE_MS, BW.DIORAMA_STALL_CAP_MS, BW.SESSION_GRACE_DEFAULT_MS

    def watch(stale_ms):        # the stalled host: peer alive (its writer re-sends), still in its battle (field 0)
        return BW.diorama_watch_step(False, 0, n, True, 0, False, stale_ms, settle, settle, grace, cap, BW.WATCH_WHY_NONE)
    assert watch(cap) == (BW.WATCH_HOLD, BW.WATCH_WHY_NONE)
    assert watch(cap + 1) == (BW.WATCH_LEAVE_FINAL, BW.WATCH_WHY_STALL_CAP)
    stale = [i for i, x in enumerate(flags) if not x and i > 0]
    assert (stale[-1] - stale[0]) * f > cap                            # s131: one unbroken stale stretch past the cap
    pre = BW.PeerLane(memo=False).run(BW.cut_script(3000, -1, -1, 14000))
    runs, run = [], 0
    for x in pre[1:]:
        run = 0 if x else run + 1
        runs.append(run)
    assert max(runs) * f < settle                                      # pre-s131: re-adopted every ~2 s, never settled


def test_the_readopt_log_budget_is_three_episodes_per_host_battle():
    """NoteRefusedReadopt's budget (review S131-R2): one line per EPISODE (its first refused repeat, never per frame), the
    first READOPT_LOG_MAX of a host battle (its nonce), then ONE 'further ones ... counted, not logged' line, then nothing
    -- the counters never stop; a new nonce opens a new budget, and Reset() re-arms it without touching the counters."""
    n = BW.ADOPT_TEST_NONCE
    lane = BW.PeerLane()
    t = 0

    def episode(seq, nonce, repeats=3):
        nonlocal t
        lane.pump(t, (seq, nonce))
        t += BW.STALE_MS
        assert lane.pump(t, None) is False                              # the run-out
        for _ in range(repeats):
            t += 10
            assert lane.pump(t, (seq, nonce)) is False                  # refused, the lane stays stale
        t += 10
    for k in range(5):
        episode(10 * k, n)
    assert lane.doc()["refused"] == 5 and lane.doc()["frames"] == 15 and lane.doc()["count"] == 5
    assert lane.lines == [BW.readopt_line(n, 0, 1), BW.readopt_line(n, 10, 2), BW.readopt_line(n, 20, 3),
                          BW.readopt_muted_line(BW.READOPT_LOG_MAX + 1, n, 4)], lane.lines
    episode(7, n + 1)
    assert lane.lines[-1] == BW.readopt_line(n + 1, 7, 6)              # a new host battle: a new budget
    lane.reset()
    assert lane.doc()["seq"] == -1 and lane.doc()["refused"] == 6 and lane.doc()["count"] == 6
    episode(50, n + 1)
    assert lane.lines[-1] == BW.readopt_line(n + 1, 50, 7) and len(lane.lines) == 6


def test_the_readopt_lines_are_the_engines_words():
    """The episode line and the budget's line ARE the engine's: each C# literal of the stack, spliced in order around the
    values (nonce, seq, the episode count; the episode number) -- the needles a bench greps are their heads."""
    line = BW.readopt_line(65, 20, 1)
    assert line == ("[NetSync] battle lane: the host's last frame (nonce 65, seq 20) ran out of freshness and the transport "
                    "served it again -- not re-adopted: a repeat is never news, the lane stays stale until a new frame (a "
                    "fight's end, a cut or a stalled host); refused=1")
    assert _spliced(line, BW.LOG_READOPT_REFUSED, ", seq ", ") ran out of ",
                    "freshness and the transport served it again -- not re-adopted: a repeat is never news, the lane "
                    "stays stale ", "until a new frame (a fight's end, a cut or a stalled host); refused="), line
    muted = BW.readopt_muted_line(4, 65, 4)
    assert muted == ("[NetSync] battle lane: refused re-adopt 4 on the host's battle (nonce 65) -- further ones on it are "
                     "counted, not logged (netsync.battle.peer.expired); refused=4")
    assert _spliced(muted, BW.LOG_READOPT_MUTED, " on the host's battle (nonce ",
                    ") -- further ones on it are counted, not logged (netsync.battle.peer.expired); refused="), muted
    assert sum(BW.LOG_READOPT_REFUSED in lit for f in BATTLE_FILES for ln in _stack_text(f) for lit in _literals(ln)) == 1


def test_the_expired_block_is_peers_last_key_at_the_catch_lines_sentinels():
    """THE CATCH-LITERAL RE-PIN: `expired` sits in AppendNetsync's SECOND catch literal, right after `bench_manifest_note`
    and before `menu`, at its sentinels; the live block's `peer` ends with it, in AppendPeerExpired's key order, each key
    read through its getter; the harness protocol stays 5 (additive) and the wire v14."""
    catch = net_lines("HarnessAgent.cs", r'outer\.Append\("\\"netsync\\":\{\\"enabled')
    assert len(catch) == 1, catch
    a, b = _literals(catch[0])
    want = ('\\"bench_manifest_note\\":null,\\"expired\\":{\\"seq\\":-1,\\"nonce\\":-1,\\"count\\":0,\\"refused\\":0,'
            '\\"frames\\":0,\\"ms\\":-1}},\\"menu\\":{')
    assert want in b and "expired" not in a
    peer = _battle_of(_agent_netsync_nothing()[0])["peer"]
    assert list(peer)[-2:] == ["bench_manifest_note", "expired"] and peer["expired"] == BW.PEER_EXPIRED_SENTINELS
    assert tuple(peer["expired"]) == FG.NETSYNC_PEER_EXPIRED_KEYS == ("seq", "nonce", "count", "refused", "frames", "ms")
    body = _cs_block("HarnessAgent.cs", "private static void AppendPeerExpired(", "}")
    nums = [re.match(r'Num\(sb, "(\w+)", Memoria\.Netsync\.NetSyncBattle\.(\w+)\);', ln) for ln in body]
    assert [(m.group(1), m.group(2)) for m in nums if m] == [
        ("seq", "HarnessPeerExpiredSeq"), ("nonce", "HarnessPeerExpiredNonce"), ("count", "HarnessPeerExpiries"),
        ("refused", "HarnessPeerReadoptsRefused"), ("frames", "HarnessPeerReadoptFrames"), ("ms", "HarnessPeerReadoptMs")]
    assert _added_after("s131", "HarnessAgent.cs", 'Str(sb, "bench_manifest_note"', "AppendPeerExpired(sb);")
    assert net_lines("HarnessAgent.cs", r"public const Int32 ProtocolVersion = ") == ["public const Int32 ProtocolVersion = 5;"]
    # s131 wrote the catch line whole; s132 left it alone; [ff9mapkit netsync s133] s133 added `act` after `end` and
    # nothing else -- so the live line is s131's plus that one sub-object
    live = _agent_netsync_nothing()[0]
    assert _catch_doc_in("s131") == _catch_doc_in("s132") == {**live, "battle": {
        k: v for k, v in live["battle"].items() if k != "act"}}


def test_state_reads_the_expired_block_absent_on_s121_as_cannot():
    """On the deployed s121's catch block every `peer.expired` accessor reads None ("this engine cannot") and
    `coop_peer_adopt` False; on the live block they read the sentinels and True; no `netsync` block reads None; a
    published block reads its values (deltas are the caller's), a mistyped value None."""
    old = State({"frame": 1, "netsync": _catch_doc_in("s121")})
    live = State({"frame": 1, "netsync": _agent_netsync_nothing()[0]})
    names = [n for p, n in State.NETSYNC_BATTLE_ACCESSORS.items() if p.startswith("peer.expired")]
    assert sorted(names) == sorted(["coop_peer_expired"] + [f"coop_peer_expired_{k}" for k in FG.NETSYNC_PEER_EXPIRED_KEYS])
    assert (State({"frame": 1}).coop_peer_adopt, old.coop_peer_adopt, live.coop_peer_adopt) == (None, False, True)
    assert all(getattr(old, n) is None for n in names) and all(getattr(live, n) is not None for n in names)
    assert (live.coop_peer_expired_seq, live.coop_peer_expired_nonce, live.coop_peer_expired_count,
            live.coop_peer_expired_refused, live.coop_peer_expired_frames, live.coop_peer_expired_ms) == (-1, -1, 0, 0, 0, -1)
    doc = _agent_netsync_nothing()[0]
    doc["battle"]["peer"]["expired"] = {"seq": 20, "nonce": 65, "count": 3, "refused": 2, "frames": 9, "ms": True}
    st = State({"frame": 1, "netsync": doc})
    assert (st.coop_peer_expired_seq, st.coop_peer_expired_count, st.coop_peer_expired_refused, st.coop_peer_expired_ms) \
        == (20, 3, 2, None)                                            # (a bool is never an int)
    got = st.coop_peer_expired
    got["seq"] = 0
    assert st.coop_peer_expired["seq"] == 20                           # a copy


def test_a_fresh_stand_in_publishes_the_expired_sentinels_and_the_deployed_s121_none(game):
    """The default stand-in (s131) publishes `peer.expired` at the agent's sentinels and keeps them through a selftest own
    battle (the loopback writes the view directly: nothing runs out), its lane pumped by hand reads through the accessors;
    the deployed s121 (S121_CAPS) publishes no key and no proof line -- the calibration's red for every check that reads
    them."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        st = _own_battle_two(g, fake)
        assert st.coop_peer_adopt is True and st.coop_peer_live is True
        assert st.coop_peer_expired == BW.PEER_EXPIRED_SENTINELS
        g.send("reset")
        st = g.wait_for(lambda s: s.netsync is not None and not s.netsync["forced"], timeout=5.0, what="the release")
        assert st.coop_peer_expired == BW.PEER_EXPIRED_SENTINELS
    fake._peer_lane.run(BW.cut_script(3000, 67, -1, 9000))
    st = State({"frame": 1, "netsync": fake._netsync_doc()})
    assert (st.coop_peer_expired_count, st.coop_peer_expired_refused, st.coop_peer_expired_frames, st.coop_peer_expired_ms,
            st.coop_peer_expired_seq, st.coop_peer_expired_nonce) == (1, 1, 6, 60, 20, BW.ADOPT_TEST_NONCE)
    old = FakeGame(game)
    old.netsync_caps = S121_CAPS
    st = State({"frame": 1, "netsync": old._netsync_doc()})
    assert st.coop_peer_adopt is False and st.coop_peer_expired is None and st.coop_peer_expired_refused is None
    assert st.coop_menu_refusal is True and "expired" not in _battle_of(old._netsync_doc())["peer"]
    assert set(_leaves(_battle_of(old._netsync_doc()))) == set(_leaves(_battle_of(_catch_doc_in("s121"))))


# =========================================================================== [ff9mapkit netsync s133]
# THE HOST ACTION-START LANE (studies/battle-coop/R3-DESIGN.md 3.3.2 as amended by R3-ACTION-REPLAY-AUDIT.md 2.1 -- the
# design's "s122"; group 2 renumbered s133-s141). Host only, wire v14, harness protocol 5: one additive sub-object
# (`netsync.battle.act.host`), one sub-verb (`actbench`), one proof line, type-1 caps bit 5. The codec's and the books'
# twins (battlewire) EVALUATE ActionSelfTest's OWN 30 rows off the stack -- translated statement by statement, so a row's
# arguments, verdict or order changed on either side turns a test red -- each rule's mutant fails a row, the constants are
# pinned by name both ways (audit amendment 11), and s132 -- s133's calibration red -- is the ladder prefix through
# `grace40` (S132_CAPS = FG.caps_through("grace40")): every check below that reads the key, the verb or the proof line reads
# "cannot" there.

#: ActionSelfTest's own helpers' bodies, pinned (the Python wrappers below implement exactly these)
ACT_HELPER_LINES = (
    "return EncodeActionStart(ActTestNonce, 1, id, actor, actorFlags, 1, 176, 0x10, 0, 0, 0, VfxKindSpecial, 100, -1, 5);",
    "return new ActRecord { Id = id, Actor = 5, CmdNo = 1, SubNo = 176, Scripted = scripted };",
    "return r != null ? r.Id : -1;",
    "book.Feed(ref a, ReadActionExt(frame, ref a));",
    "return TryParseAction(frame, out a) && ReadActionExt(frame, ref a) == ActExtReadBad && !a.HasExt;",
    "return TryParseAction(cut, out a) && SameLegacy(ref a, ref whole) && ReadActionExt(cut, ref a) != ActExtReadOk && "
    "!a.HasExt;",
    "if (a == null || b == null || ao + n > a.Length || bo + n > b.Length)",
)
#: ActTestImpact's writes, in order (QueueActionFrame's 46-byte layout; every field a marker)
ACT_TEST_IMPACT_WRITES = ["nonce", "seq", "caster", "target", "(UInt16)0x0011", "-123", "7", "(UInt16)0x0022", "45", "-6",
                          "900u", "80u", "1200u", "60u", "flags", "(UInt16)1", "(UInt16)176"]
#: SameLegacy compares exactly the 46-byte fields (PeerAction's names), every one
ACT_SAME_LEGACY = ("Nonce", "SeqHorizon", "CasterSlot", "TargetSlot", "FigInfoT", "FigHpT", "FigMpT", "FigInfoC", "FigHpC",
                   "FigMpC", "TgtHpRaw", "TgtMpRaw", "CastHpRaw", "CastMpRaw", "Flags", "CmdNo", "SubNo")
_ACT_TYPES = ("Int32", "String", "Byte", "Byte[]", "Boolean", "UInt16", "PeerAction", "ActRecord", "ActLoopBook",
              "Dictionary<System.Object, ActRecord>", "System.Object")
_ACT_DECL = re.compile(r"^(?:const\s+)?(" + "|".join(re.escape(t) for t in _ACT_TYPES) + r")\s+([A-Za-z_]\w*\s*(?:=.*|,.*)?)$",
                       re.S)


def _act_region(start: str, stop: str, file_name: str = "NetSyncBattle.cs") -> list:
    """s133's own hunks of ``file_name``: the code lines (comments stripped, blanks dropped) from the line starting with
    ``start`` up to (not including) the next starting with ``stop`` -- s133's text, which no later patch rewrites."""
    new = [t for _h, _k, t in _new_side(file_name, _patch_bytes("s133"))]
    i = next(k for k, t in enumerate(new) if t.startswith(start))
    j = next(k for k in range(i + 1, len(new)) if new[k].startswith(stop))
    return [c for c in (_strip_comment(t) for t in new[i:j]) if c]


def _act_scan(code: str, i: int, stop: str) -> int:
    """The index of the first ``stop`` character at paren / brace depth 0 from ``i`` (string literals skipped)."""
    depth, quoted = 0, False
    while i < len(code):
        c = code[i]
        if quoted:
            if c == "\\":
                i += 1
            elif c == '"':
                quoted = False
        elif c == '"':
            quoted = True
        elif depth == 0 and c == stop:
            return i
        elif c in "({":
            depth += 1
        elif c in ")}":
            depth -= 1
        i += 1
    raise AssertionError(f"no {stop!r} at depth 0 in {code[i - 80:i]!r}")


def _act_statements(code: str) -> list:
    """C# statements -> [text | (``for`` | ``foreach``, header, body)]: `try` and bare block braces flattened, a loop's body a
    braced block or its one statement."""
    out, i = [], 0
    while i < len(code):
        while i < len(code) and code[i] in " \t\r\n{}":
            i += 1
        if i >= len(code):
            break
        if re.match(r"try\b", code[i:]):
            i += 3
            continue
        m = re.match(r"(for|foreach)\s*\(", code[i:])
        if m:
            at = i + m.end() - 1
            end = _balanced(code, at)
            header = code[at + 1:end - 1].strip()
            j = end
            while code[j] in " \t\r\n":
                j += 1
            if code[j] == "{":
                close = _act_scan(code, j + 1, "}")
                body, i = _act_statements(code[j + 1:close]), close + 1
            else:
                semi = _act_scan(code, j, ";")
                body, i = _act_statements(code[j:semi + 1]), semi + 1
            out.append((m.group(1), header, body))
            continue
        semi = _act_scan(code, i, ";")
        out.append(" ".join(code[i:semi].split()))
        i = semi + 1
    return out


def _act_not(code: str) -> str:
    """C#'s ``!`` -> ``(not ..)`` around its whole operand (``!=`` left alone)."""
    while True:
        m = re.search(r"!(?!=)", code)
        if not m:
            return code
        k = m.end()
        while code[k] == " ":
            k += 1
        if code[k] == "(":
            end = _balanced(code, k)
        else:
            w = re.match(r"[\w.]+", code[k:])
            assert w, code
            end = k + w.end()
            if end < len(code) and code[end] == "(":
                end = _balanced(code, end)
        code = code[:m.start()] + "(not " + code[k:end] + ")" + code[end:]


def _act_expr(expr: str) -> str:
    """One C# expression of ActionSelfTest as Python: string literals kept, ``new Byte[] {..}`` / ``new Byte[n]`` /
    ``(Byte[])x.Clone()`` -> bytearray, ``new System.Object()`` / ``new Dictionary<..>()`` / ``new[] {..}`` / ``new T()``,
    ``x.Length`` -> len, ``x.ContainsKey(k)`` -> ``k in x``, every ``ref`` / ``out`` argument BY NAME (the wrappers read
    and write the namespace), ``local.Member`` -> ``__m(local, 'Member')`` (a twin's snake_case key or attribute),
    true/false/null, && / || / !."""
    strings = []

    def keep(m):
        strings.append(repr(m.group(1).replace('\\"', '"').replace("\\\\", "\\")))
        return f"__S{len(strings) - 1}__"

    code = _CS_STRING.sub(keep, expr)
    code = re.sub(r"\bnew Byte\[\]\s*\{([^{}]*)\}", r"bytearray([\1])", code)
    code = re.sub(r"\bnew Byte\[([^\[\]]+)\]", r"bytearray(\1)", code)
    code = re.sub(r"\(Byte\[\]\)(\w+)\.Clone\(\)", r"bytearray(\1)", code)
    code = re.sub(r"\bnew System\.Object\(\)", "object()", code)
    code = re.sub(r"\bnew Dictionary<[^<>]*>\(\)", "{}", code)
    code = re.sub(r"\bnew\[\]\s*\{([^{}]*)\}", r"[\1]", code)
    code = re.sub(r"\bnew (\w+)\(\)", r"\1()", code)
    code = re.sub(r"\bBuffer\.BlockCopy\(", "BlockCopy(", code)
    code = re.sub(r"\b(\w+)\.Length\b", r"len(\1)", code)
    code = re.sub(r"\b(\w+)\.ContainsKey\(", r"__contains(\1, ", code)
    code = re.sub(r"\b(?:ref|out) (\w+)", r"'\1'", code)
    code = re.sub(r"\b([a-z]\w*)\.([A-Z]\w*)", r"__m(\1, '\2')", code)
    code = re.sub(r"\btrue\b", "True", code)
    code = re.sub(r"\bfalse\b", "False", code)
    code = re.sub(r"\bnull\b", "None", code)
    code = _act_not(code.replace("&&", " and ").replace("||", " or "))
    for i, s in enumerate(strings):
        code = code.replace(f"__S{i}__", s)
    return code


def _act_python(stmts: list, pad: str = "") -> list:
    """ActionSelfTest's statements as Python source lines: a Row -> ``__row(expr, name)``; a declaration -> its
    assignments (an uninitialised local -> None); a ``for (Int32 n = a; cond; n++)`` -> a while loop; a ``foreach (T x in
    xs)`` -> a for loop; anything else (an assignment, ``|=``, a call) as itself."""
    out = []
    for s in stmts:
        if isinstance(s, tuple):
            kind, header, body = s
            if kind == "for":
                init, cond, step = (p.strip() for p in header.split(";"))
                m = re.fullmatch(r"Int32 (\w+) = (.+)", init)
                assert m and step == m.group(1) + "++", header
                out.append(f"{pad}{m.group(1)} = {_act_expr(m.group(2))}")
                out.append(f"{pad}while {_act_expr(cond)}:")
                out += _act_python(body, pad + "    ")
                out.append(f"{pad}    {m.group(1)} += 1")
            else:
                m = re.fullmatch(r"\w+ (\w+) in (.+)", header)
                assert m, header
                out.append(f"{pad}for {m.group(1)} in {_act_expr(m.group(2))}:")
                out += _act_python(body, pad + "    ")
            continue
        m = _ROW.match(s)
        if m:
            out.append(f"{pad}__row({_act_expr(m.group(1))}, {m.group(2)!r})")
            continue
        m = _ACT_DECL.match(s)
        if m:
            rest = re.sub(r"\bnew Dictionary<[^<>]*>\(\)", "{}", m.group(2))      # (its comma is no declarator's)
            decls, at = [], 0
            while at < len(rest):
                try:
                    comma = _act_scan(rest, at, ",")
                except AssertionError:
                    comma = len(rest)
                decls.append(rest[at:comma].strip())
                at = comma + 1
            for d in decls:
                name, _, value = d.partition("=")
                out.append(f"{pad}{name.strip()} = {_act_expr(value.strip()) if value else 'None'}")
            continue
        out.append(pad + _act_expr(s))
    return out


def _act_program() -> str:
    """ActionSelfTest, read off the stack (the hunk that holds it whole), as one Python program."""
    block = _cs_block("NetSyncBattle.cs", "internal static Boolean ActionSelfTest(")
    code = " ".join(_strip_comment(ln) for ln in block if not re.match(r"(?:internal|private|public) static ", ln))
    return "\n".join(_act_python(_act_statements(code)))


def _act_struct_default() -> dict:
    """``default(PeerAction)``: every field zero (the extension's cleared)."""
    return BW.clear_action_ext(BW._act_flag_props({f: 0 for f in BW.ACT_LEGACY_FIELDS}))


def _act_ns(**twins) -> dict:
    """The namespace ActionSelfTest runs in: the constants by C# name, the twins under their C# names (``twins`` replaces
    one -- a mutant), its own helpers (the pinned bodies of ACT_HELPER_LINES / ACT_TEST_IMPACT_WRITES), each ``ref`` /
    ``out`` local passed by NAME, and ``__row`` asserting each row."""
    tw = dict(parse=BW.parse_action, read=BW.read_action_ext, ext=BW.with_impact_ext, start=BW.encode_action_start,
              end=BW.encode_action_end, next_id=BW.act_next_id, step=BW.act_start_step, end_step=BW.act_end_step,
              id_of=BW.act_id_of, verdict=BW.act_vfx_verdict, book=BW.ActLoopBook)
    tw.update(twins)
    ns = dict(BW.CS_ACTION_CONSTANTS)
    names: list = []

    def row(ok, name):
        if ok is not True:
            raise AssertionError(f"row {name!r} is {ok!r} for the twins")
        names.append(name)

    def member(obj, name):
        return obj[_snake(name)] if isinstance(obj, dict) else getattr(obj, _snake(name))

    def try_parse(frame, out):                                         # TryParseAction(p, out a)
        a = tw["parse"](frame)
        ns[out] = a if a is not None else _act_struct_default()
        return a is not None

    def read_ext(frame, ref):                                          # ReadActionExt(p, ref a)
        return tw["read"](frame, ns[ref])

    def same_legacy(x, y):                                             # SameLegacy(ref a, ref b)
        return all(ns[x][_snake(f)] == ns[y][_snake(f)] for f in ACT_SAME_LEGACY)

    def same_bytes(a, ao, b, bo, n):
        if a is None or b is None or ao + n > len(a) or bo + n > len(b):
            return False
        return bytes(a[ao:ao + n]) == bytes(b[bo:bo + n])

    def block_copy(src, so, dst, do, n):
        dst[do:do + n] = bytes(src[so:so + n])

    def cut_reads_no_ext(full, n, whole):                              # ActCutReadsNoExt(full, n, ref whole)
        cut = bytes(full[:n])
        a = tw["parse"](cut)
        if a is None:
            return False
        ns["__cut"] = a
        return same_legacy("__cut", whole) and tw["read"](cut, a) != BW.ACT_EXT_READ_OK and not a["has_ext"]

    def bad_ext(frame):                                                # ActBadExt(frame)
        a = tw["parse"](frame)
        return a is not None and tw["read"](frame, a) == BW.ACT_EXT_READ_BAD and not a["has_ext"]

    def next_id(ref):                                                  # ActNextId(ref last)
        ns[ref] = tw["next_id"](ns[ref])
        return ns[ref]

    def start_step(live, scr, key, fresh, running, out):             # ActStartStep(.., out displaced)
        verdict, ns[out] = tw["step"](live, scr, key, fresh, running)
        return verdict

    def test_impact(nonce, seq, caster, target, flags):              # ActTestImpact (ACT_TEST_IMPACT_WRITES)
        return BW.encode_action_impact(nonce, seq, caster, target, fig_t=(0x0011, -123, 7), fig_c=(0x0022, 45, -6),
                                       raws=(900, 80, 1200, 60), flags=flags, cmd_no=1, sub_no=176)

    def test_feed(book, frame):                                        # ActTestFeed(book, frame)
        a = tw["parse"](frame)
        if a is not None:
            book.feed(a, tw["read"](frame, a))

    def test_end(live, key):                                           # ActTestEnd(live, key)
        r = tw["end_step"](live, key)
        return r["id"] if r is not None else -1

    ns.update(__row=row, __m=member, __contains=lambda d, k: k in d, TryParseAction=try_parse, ReadActionExt=read_ext,
              SameLegacy=same_legacy, SameBytes=same_bytes,
              AllZero=lambda a, o, n: all(x == 0 for x in a[o:o + n]), BlockCopy=block_copy,
              ActCutReadsNoExt=cut_reads_no_ext, ActBadExt=bad_ext, WithImpactExt=tw["ext"],
              EncodeActionStart=tw["start"], EncodeActionEnd=tw["end"], ActNextId=next_id, ActStartStep=start_step,
              ActEndStep=tw["end_step"], ActIdOf=tw["id_of"], ActVfxVerdict=tw["verdict"], ActLoopBook=tw["book"],
              ActTestImpact=test_impact, ActTestFeed=test_feed, ActTestEnd=test_end,
              ActTestStart=lambda i, actor, fl: tw["start"](BW.ACT_TEST_NONCE, 1, i, actor, fl, 1, 176, 0x10, 0, 0, 0,
                                                             BW.VFX_KIND_SPECIAL, 100, -1, 5),
              ActTestRec=lambda i, scripted: BW.new_act_record(i, 5, 1, 176, scripted),
              __names__=names)
    return ns


def _run_act_selftest(**twins) -> list:
    ns = _act_ns(**twins)
    exec(compile(_act_program(), "<ActionSelfTest>", "exec"), ns)           # noqa: S102 -- the stack's own selftest rows
    return ns["__names__"]


#: ActionSelfTest's rows the audit's amendments name (their names are the engine's, verbatim)
ACT_ROW_MARKS = ("impact: the 46 bytes unchanged, then A6 01 03 01 and the id (LE)",
                 "START: 76 bytes at the design's offsets (hand-checked)",
                 "START through the s110-s132 reader: slots 0xFF/0xFF, flags 0x04 only, no figures, the legacy identity",
                 "every truncated START prefix (47..75 bytes) reads no extension, its 46 bytes intact",
                 "an unknown fmt is skipped, never failing the frame",
                 "book: StartBtlSeq over an open cmd[0] displaces its id for an END first; the sequence is never ENDed",
                 "loop: a scripted START owes no END; an open CommandEngine START is no_end at a normal close, cut at a "
                 "reset",
                 "loop: a stat tick is never an impact; an id-0 impact is extended but no orphan; a 46-byte one is neither",
                 "vfx: a CSV .seq's first use (special described, a text sequence ran) is drift; unknown always drifts")


def test_the_action_twins_evaluate_every_action_selftest_row_off_the_stack():
    """battlewire's s133 twins (the codec, the id books, the loopback audit, the describe verdict) against ActionSelfTest's
    OWN rows, EVALUATED in order: 13 codec rows, 8 id-book rows, 6 loopback-audit rows, 3 describe-verdict rows -- 30, the
    proof line's count. Its helpers are the pinned bodies (ACT_HELPER_LINES, ACT_TEST_IMPACT_WRITES, ACT_SAME_LEGACY)."""
    names = _run_act_selftest()
    assert len(names) == BW.ACTION_SELFTEST_ROWS == 30 and len(set(names)) == 30, names
    assert all(mark in names for mark in ACT_ROW_MARKS), set(ACT_ROW_MARKS) - set(names)
    prefix = lambda n: n.split(":", 1)[0]                                # noqa: E731
    assert [sum(prefix(n) == p for n in names) for p in ("book", "loop", "vfx", "ids")] == [7, 6, 3, 1], names
    assert sum("ref rows, ref fail);" in ln for ln in net_lines("NetSyncBattle.cs", r".", [_patch_bytes("s133")])) == 30
    for line in ACT_HELPER_LINES:
        assert _battle_text(line), line
    writes = [re.fullmatch(r"bw\.Write\((.+)\);", ln) for ln in _act_region("private static Byte[] ActTestImpact(",
                                                                           "private static Byte[] ActTestStart(")]
    assert [m.group(1) for m in writes if m] == ACT_TEST_IMPACT_WRITES
    same = " ".join(_act_region("private static Boolean SameLegacy(", "private static Boolean SameBytes("))
    assert re.findall(r"a\.(\w+) == b\.\1", same) == list(ACT_SAME_LEGACY), same


def _mutant_read(rule: str):
    """ReadActionExt with ONE rule broken (the twin's own body otherwise)."""
    def read(payload, a):
        p = bytes(payload)
        if rule == "no_flag_agreement" and len(p) >= 52 and p[46] == BW.ACT_EXT_TAG and p[49] in (1, 2, 3):
            fl = a["flags"]
            a["flags"] = (fl & ~(BW.ACT_FLAG_START | BW.ACT_FLAG_END)) | {1: 0, 2: BW.ACT_FLAG_START,
                                                                         3: BW.ACT_FLAG_END}[p[49]]
            r = BW.read_action_ext(p, a)
            a["flags"] = fl
            return r
        if rule == "short_ok" and 46 < len(p) < 52 and p[46] == BW.ACT_EXT_TAG:
            BW.clear_action_ext(a)
            a.update(has_ext=True, ext_kind=BW.ACT_EXT_IMPACT)
            return BW.ACT_EXT_READ_OK
        if rule == "fmt_bad" and len(p) >= 52 and p[46] == BW.ACT_EXT_TAG and p[47] != BW.ACT_EXT_FMT1:
            BW.clear_action_ext(a)
            return BW.ACT_EXT_READ_BAD
        if rule == "id0_ok" and len(p) >= 52 and p[46] == BW.ACT_EXT_TAG and p[50] == p[51] == 0 and p[49] in (2, 3):
            q = bytearray(p)
            q[50] = 1
            r = BW.read_action_ext(bytes(q), a)
            if r == BW.ACT_EXT_READ_OK:
                a["act_id"] = 0
            return r
        return BW.read_action_ext(p, a)
    return read


def _mutant_step(rule: str):
    def step(live, scr, key, fresh, running):
        if rule == "no_displace" and key in live:
            live.pop(key)
            (scr if fresh["scripted"] else live)[key] = fresh
            return BW.ACT_STEP_NEW, None
        if rule == "no_reentry":
            return BW.act_start_step(live, scr, key, fresh, False)
        if rule == "scripted_live" and fresh["scripted"]:
            v, d = BW.act_start_step(live, scr, key, dict(fresh, scripted=False), running)
            return (BW.ACT_STEP_TAKEOVER if v == BW.ACT_STEP_RESTART else v), d
        return BW.act_start_step(live, scr, key, fresh, running)
    return step


class _BookStatAsImpact(BW.ActLoopBook):
    def feed(self, a, ext_read):                                       # a stat tick counted as an impact
        super().feed(dict(a, flags=a["flags"] & ~BW.ACT_FLAG_STAT_TICK), ext_read)


class _BookNoCasterCheck(BW.ActLoopBook):
    def feed(self, a, ext_read):
        super().feed(dict(a, caster_slot=0xFF) if not a["is_start"] else a, ext_read)


class _BookScriptedOwes(BW.ActLoopBook):
    def feed(self, a, ext_read):
        super().feed(dict(a, actor_flags=a["actor_flags"] & ~BW.ACTOR_SCRIPTED) if a["is_start"] else a, ext_read)


@pytest.mark.parametrize("twins", [
    {"read": _mutant_read("no_flag_agreement")}, {"read": _mutant_read("short_ok")}, {"read": _mutant_read("fmt_bad")},
    {"read": _mutant_read("id0_ok")},
    {"ext": lambda legacy, i: BW.with_impact_ext(legacy, i)[:49] + bytes([BW.ACT_EXT_END]) + BW.with_impact_ext(legacy, i)[50:]},
    {"start": lambda *a: BW.encode_action_start(*a[:7], a[7], 0, *a[9:]) if a[8] else BW.encode_action_start(*a)},
    {"end": lambda n, s, i, c, sub: BW.encode_action_end(n, s, i, c, sub)[:41] + bytes([0x0C])
     + BW.encode_action_end(n, s, i, c, sub)[42:]},
    {"next_id": lambda last: (last + 1) & 0xFFFF}, {"step": _mutant_step("no_displace")},
    {"step": _mutant_step("no_reentry")}, {"step": _mutant_step("scripted_live")},
    {"end_step": lambda live, key: live.get(key)}, {"id_of": lambda live, scr, key: (live.get(key) or {"id": 0})["id"]},
    {"verdict": lambda kind, num, added, enemy, eff: added if kind != BW.VFX_KIND_NONE else not added},
    {"verdict": lambda kind, num, added, enemy, eff: BW.act_vfx_verdict(kind, num, added, enemy, eff)
     or (kind == BW.VFX_KIND_UNKNOWN and added)},
    {"book": _BookStatAsImpact}, {"book": _BookNoCasterCheck}, {"book": _BookScriptedOwes}],
    ids=["read-flag-agreement", "read-short-ok", "read-fmt-bad", "read-id0-ok", "ext-kind", "start-cursor", "end-flags",
         "next-id-zero", "step-no-displace", "step-no-reentry", "step-scripted-live", "end-step-keeps", "id-of-live-only",
         "verdict-kind-blind", "verdict-unknown-ok", "book-stat-impact", "book-no-caster", "book-scripted-owes"])
def test_each_action_rule_mutant_fails_a_selftest_row(twins):
    """A CHECK THAT CANNOT FAIL is no check: each rule of the codec, the books, the audit and the verdict, broken alone in
    its twin, fails one of the engine's own rows."""
    _act_program()                                                      # (its own parse outside the raises)
    with pytest.raises(AssertionError, match=r"^row ['\"]"):
        _run_act_selftest(**twins)


def _cs_signature(file_name: str, start: str) -> list:
    """A C# method's parameter names, read off its signature in the stack (generic-aware: a comma inside ``<..>`` does
    not split); ``ref`` / ``out`` kept as a prefix."""
    sig = " ".join(_cs_block(file_name, start, "{"))
    inner = sig[sig.index("(") + 1:sig.rindex(")")]
    params, depth, cur = [], 0, ""
    for c in inner:
        depth += {"<": 1, ">": -1}.get(c, 0)
        if c == "," and depth == 0:
            params.append(cur.strip())
            cur = ""
        else:
            cur += c
    params.append(cur.strip())
    return [(p.split()[0] + " " if p.split()[0] in ("ref", "out") else "") + p.split()[-1] for p in params if p]


def test_the_action_twins_take_the_engines_parameters_in_its_order():
    """Each s133 twin's parameters ARE its C# method's, in order (camelCase -> snake_case; ``ref a`` is the struct dict, ``ref
    last`` the value the caller stores back, an ``out`` the twin's (second) result)."""
    for start, fn, fix in (
            ("internal static Byte[] EncodeActionStart(", BW.encode_action_start, {}),
            ("internal static Byte[] EncodeActionEnd(", BW.encode_action_end, {}),
            ("internal static Byte[] WithImpactExt(", BW.with_impact_ext, {}),
            ("internal static Int32 ReadActionExt(", BW.read_action_ext, {"ref a": "a", "p": "payload"}),
            ("internal static UInt16 ActNextId(", BW.act_next_id, {"ref last": "last"}),
            ("internal static Int32 ActStartStep(", BW.act_start_step, {}),
            ("internal static ActRecord ActEndStep(", BW.act_end_step, {}),
            ("internal static UInt16 ActIdOf(", BW.act_id_of, {}),
            ("internal static Boolean ActVfxVerdict(", BW.act_vfx_verdict, {})):
        cs = [fix.get(p, fix.get(_snake(p), _snake(p))) for p in _cs_signature("NetSyncBattle.cs", start)
              if not p.startswith("out ")]
        assert cs == _twin_params(fn), (start, cs, _twin_params(fn))


def test_the_action_constants_are_the_stacks_both_ways():
    """THE PIN (audit amendment 11): every CS_ACTION_CONSTANTS entry is NetSyncBattle's constant of that name and value,
    and every integer constant s133's own hunk declares is in the table -- a constant added, renamed or retuned on either
    side turns this red. ActionBufferCap (its comment hides it from the parser) stays 64 (audit D4)."""
    cs = _cs_int_consts("NetSyncBattle.cs")
    for name, value in BW.CS_ACTION_CONSTANTS.items():
        assert name in cs and cs[name][0] == value, (name, cs.get(name), value)
    mine = set()
    for line in net_lines("NetSyncBattle.cs", r"const (?:Byte|Int32) ", [_patch_bytes("s133")]):
        m = re.match(r"(?:public |private |internal )?const (?:Byte|Int32) (.*);", line)
        mine |= {d.group(1) for d in (re.match(r"\s*(\w+) = (?:0x[0-9A-Fa-f]+|-?\d+)\s*$", x) for x in m.group(1).split(","))
                 if d}                                               # (the selftest's local `const Byte N = ActTestNonce`: no)
    assert mine == set(BW.CS_ACTION_CONSTANTS), sorted(mine ^ set(BW.CS_ACTION_CONSTANTS))
    assert _battle_text("private const Int32 ActionBufferCap = 64;") and BW.ACTION_BUFFER_CAP == 64
    assert (BW.CAP_ACTION_STARTS, BW.FLAG_START_HOLD, BW.CAP_INTRO_MIRROR, BW.FLAG_INTRO_SKIPPED) == (0x20, 0x10, 8, 4)
    assert BW.CAP_ACTION_STARTS & 0x3C and not BW.CAP_ACTION_STARTS & ~0x3C      # the hostgates re-pin's mask covers it


def test_the_action_codec_matches_the_designs_bytes_by_hand():
    """The wire, checked by hand against design 3.3.2's offsets: an IMPACT is the unchanged 46 bytes + A6 01 03 01 id; a
    START 76 bytes whose s110-s132 parse is slots 0xFF/0xFF, flags 0x04, no figures; an END 52 bytes, flags 0x08; every
    truncated extension prefix reads no extension with its 46 bytes intact; an unknown fmt is skipped; a stat tick stays
    46 bytes; the tape's hex reads back."""
    legacy = BW.encode_action_impact(7, 0x1234, 1, 4, fig_t=(0, 33, 0), raws=(0, 0, 500, 0), flags=1 | 64, cmd_no=1,
                                     sub_no=176)
    impact = BW.encode_action_impact(7, 0x1234, 1, 4, fig_t=(0, 33, 0), raws=(0, 0, 500, 0), flags=1 | 64, cmd_no=1,
                                     sub_no=176, act_id=0x0203)
    assert len(legacy) == 46 and len(impact) == 52 and impact[:46] == legacy
    assert impact[46:] == bytes([0xA6, 0x01, 0x03, 0x01, 0x03, 0x02])
    assert BW.decode_action_legacy(impact) == BW.decode_action_legacy(legacy)
    a = BW.decode_action(impact)
    assert BW.classify_action(a) == "impact" and a["act_id"] == 0x0203 and a["caster_slot"] == 1 and a["fig_hp_t"] == 33
    st = BW.encode_action_start(9, 0x0BCD, 0x0007, 2, BW.ACTOR_IS_PLAYER | BW.ACTOR_HOST_REWORK, 22, 0x00000011, 0x30, 2,
                                BW.ACT_INFO_COVER, 0x0004, BW.VFX_KIND_SPECIAL, 0x0100, -1, 5)
    assert len(st) == 76 and st[0] == 9 and st[1:3] == bytes([0xCD, 0x0B]) and st[3:5] == b"\xFF\xFF"
    assert st[5:41] == bytes(36) and st[41] == 0x04 and st[42:46] == bytes([22, 0, 0x11, 0])
    assert st[46:50] == bytes([0xA6, 1, 27, 2]) and st[50:52] == bytes([7, 0]) and st[52] == 2 and st[53] == 0x03
    assert st[54:56] == bytes([22, 0]) and st[56:60] == bytes([0x11, 0, 0, 0]) and st[60:62] == bytes([0x30, 0])
    assert st[62] == 2 and st[63] == 0x04 and st[64:66] == bytes([4, 0]) and st[66] == 3
    assert st[67:71] == bytes([0, 1, 0, 0]) and st[71:75] == b"\xFF\xFF\xFF\xFF" and st[75] == 5
    old = BW.decode_action_legacy(st)
    assert (old["caster_slot"], old["target_slot"], old["flags"], old["fig_hp_t"], old["cmd_no"], old["sub_no"]) == \
        (0xFF, 0xFF, BW.ACT_FLAG_START, 0, 22, 0x11)
    s = BW.decode_action(st)
    assert BW.classify_action(s) == "start" and (s["act_id"], s["actor_slot"], s["act_tar_id"], s["vfx_num"],
                                                 s["act_patched_vfx"]) == (7, 2, 0x30, 0x100, -1)
    en = BW.encode_action_end(9, 0x0BCE, 7, 22, 0x11)
    assert len(en) == 52 and en[41] == 0x08 and en[46:] == bytes([0xA6, 1, 3, 3, 7, 0])
    assert BW.classify_action(BW.decode_action(en)) == "end" and BW.decode_action_legacy(en)["caster_slot"] == 0xFF
    for frame, n in ((st, 76), (impact, 52), (en, 52)):
        whole = BW.decode_action_legacy(frame)
        for k in range(47, n):
            cut = BW.decode_action(frame[:k])
            assert not cut["has_ext"] and cut["ext_read"] != BW.ACT_EXT_READ_OK, (n, k)
            assert {f: cut[f] for f in BW.ACT_LEGACY_FIELDS} == {f: whole[f] for f in BW.ACT_LEGACY_FIELDS}, (n, k)
    fmt2 = bytearray(st)
    fmt2[47] = 2
    assert BW.decode_action(bytes(fmt2))["ext_read"] == BW.ACT_EXT_READ_FMT
    tick = BW.encode_action_impact(7, 1, 0xFF, 4, fig_t=(0, 12, 0), flags=BW.ACT_FLAG_STAT_TICK)
    assert len(tick) == 46 and BW.classify_action(BW.decode_action(tick)) == "stat"
    assert bytes.fromhex(BW.action_hex(st)) == st and BW.action_hex(en) == en.hex().upper()
    imp7 = BW.with_impact_ext(bytes([9]) + legacy[1:], 7)                # the START's nonce: a lifecycle is (nonce, id)
    assert BW.act_order_violations([st, imp7, en]) == []
    assert BW.act_order_violations([st, BW.with_impact_ext(legacy, 7), en])                 # nonce 7's id 7: no START
    assert BW.act_order_violations([imp7, st, en]) and BW.act_order_violations([st, en, imp7])
    assert BW.action_text(st).startswith("START id 7 actor 2") and BW.action_text(legacy).endswith("a pre-s133 host)")


#: DescribeCommandVfx, statement for statement (the s133 hunk of btl_vfx.cs): the twin's branches in the same order
ACT_DESCRIBE_LINES = [
    "public static Byte DescribeCommandVfx(CMD_DATA cmd, out Int32 num)", "{", "num = 0;", "try", "{",
    "BTL_DATA regist = cmd.regist;", "if (Configuration.Battle.SFXRework)", "{",
    "if (cmd.cmd_no != BattleCommandId.MagicCounter)", "{",
    "Boolean beatrixFix = cmd.aa.Info.SequenceFile == null && regist != null && regist.bi.player == 0",
    "&& regist.dms_geo_id == 427 && cmd.aa.Info.VfxIndex == 457;", "if (cmd.aa.Info.VfxAction != null || beatrixFix)",
    "{", "num = cmd.aa.Info.VfxIndex;", "return Memoria.Netsync.NetSyncBattle.VfxKindSeq;", "}",
    "if (regist != null && regist.bi.player == 0 && cmd.cmd_no != BattleCommandId.SysTrans)", "{", "num = cmd.sub_no;",
    "return Memoria.Netsync.NetSyncBattle.VfxKindEnemy;", "}", "}", "}", "else", "{", "switch (cmd.cmd_no)", "{",
    "case BattleCommandId.EnemyAtk:", "case BattleCommandId.EnemyCounter:", "case BattleCommandId.EnemyDying:",
    "case BattleCommandId.EnemyReaction:", "num = cmd.sub_no;", "return Memoria.Netsync.NetSyncBattle.VfxKindEnemy;", "}",
    "}", "SpecialEffect sfxNum = GetPlayerCommandSFX(cmd);", "if (sfxNum != SpecialEffect.Special_No_Effect)", "{",
    "num = (Int32)sfxNum;", "return Memoria.Netsync.NetSyncBattle.VfxKindSpecial;", "}",
    "if (cmd.cmd_no == BattleCommandId.Change || cmd.cmd_no == BattleCommandId.Defend)", "{", "num = (Int32)cmd.cmd_no;",
    "return Memoria.Netsync.NetSyncBattle.VfxKindCommon;", "}", "return Memoria.Netsync.NetSyncBattle.VfxKindNone;", "}"]


def test_describe_command_vfx_is_the_engines_mirror_and_its_hook_sites_are_the_audits():
    """btl_vfx.DescribeCommandVfx (audit amendment 10: kind 1 keyed on VfxAction or the EVALUATED Beatrix predicate, never on
    SequenceFile alone) read off the stack statement for statement, and its twin on every branch; the hook sites (D1: the
    START right BEFORE SelectCommandVfx, the D2 check right after it; the END the first line of FinishCommand; the scripted
    START in StartBtlSeq after IsShortRange) are the patch's lines, in that order."""
    body = [c for c in (_strip_comment(ln) for ln in _cs_block("btl_vfx.cs", "public static Byte DescribeCommandVfx(",
                                                               "catch")) if c]
    assert body == ACT_DESCRIBE_LINES, body
    d = BW.describe_command_vfx
    assert d(rework=True, cmd_no=22, sub_no=1, player=True, vfx_action=True, vfx_index=55) == (BW.VFX_KIND_SEQ, 55)
    assert d(rework=True, cmd_no=47, sub_no=9, player=False, beatrix=True, vfx_index=457) == (BW.VFX_KIND_SEQ, 457)
    assert d(rework=True, cmd_no=47, sub_no=9, player=False) == (BW.VFX_KIND_ENEMY, 9)
    assert d(rework=True, cmd_no=BW.CMD_SYS_TRANS, sub_no=9, player=False, special=600) == (BW.VFX_KIND_SPECIAL, 600)
    assert d(rework=True, cmd_no=BW.CMD_MAGIC_COUNTER, sub_no=9, player=False, vfx_action=True,
             special=7) == (BW.VFX_KIND_SPECIAL, 7)
    assert d(rework=True, cmd_no=1, sub_no=176, player=True, special=19) == (BW.VFX_KIND_SPECIAL, 19)
    assert d(rework=True, cmd_no=BW.CMD_DEFEND_ID, sub_no=0, player=True) == (BW.VFX_KIND_COMMON, BW.CMD_DEFEND_ID)
    assert d(rework=True, cmd_no=BW.CMD_CHANGE_ID, sub_no=0, player=True) == (BW.VFX_KIND_COMMON, BW.CMD_CHANGE_ID)
    assert d(rework=True, cmd_no=BW.CMD_ITEM_ID, sub_no=236, player=True) == (BW.VFX_KIND_NONE, 0)
    assert d(rework=True, cmd_no=1, sub_no=0, player=None) == (BW.VFX_KIND_NONE, 0)       # no regist: never "enemy"
    assert d(rework=False, cmd_no=47, sub_no=4, player=False, vfx_action=True) == (BW.VFX_KIND_ENEMY, 4)
    assert d(rework=False, cmd_no=22, sub_no=4, player=True, vfx_action=True, special=31) == (BW.VFX_KIND_SPECIAL, 31)
    assert d(rework=True, cmd_no=1, sub_no=0, player=True, throws=True) == (BW.VFX_KIND_UNKNOWN, 0)
    cmd = [t for _h, _k, t in _new_side("btl_cmd.cs", _patch_bytes("s133"))]
    i = cmd.index("Memoria.Netsync.NetSyncBattle.QueueActionStart(cmd, false);")
    assert cmd[i + 1:i + 3] == ["btl_vfx.SelectCommandVfx(cmd);", "Memoria.Netsync.NetSyncBattle.CheckActionVfx(cmd);"]
    assert "BattleVoice.TriggerOnBattleAct(caster, BattleVoice.BattleMoment.CommandPerform, cmd);" in cmd[i - 4:i]
    j = cmd.index("public static void FinishCommand(FF9StateBattleSystem btlsys, CMD_DATA cmd)")
    assert [t for t in cmd[j + 2:j + 6] if not t.startswith("//")][0] == "Memoria.Netsync.NetSyncBattle.QueueActionEnd(cmd);"
    # the scripted START (review engine-1): on SFXRework right before Execute (which always registers the action); on the
    # old engine only once EntrySequence took a slot -- with all four busy the sequence never runs, so it never STARTs
    seq = [t for _h, _k, t in _new_side("btlseq.cs", _patch_bytes("s133")) if not t.startswith("//")]
    sites = [k for k, t in enumerate(seq) if t == "Memoria.Netsync.NetSyncBattle.QueueActionStart(cmd_DATA, true);"]
    assert len(sites) == 2 == len(net_lines("btlseq.cs", r"QueueActionStart\(cmd_DATA, true\);")), seq
    assert seq[sites[0] - 1].startswith("UnifiedBattleSequencer.BattleAction action = new UnifiedBattleSequencer.")
    assert seq[sites[0] + 1] == "action.Execute(cmd_DATA);"
    assert seq[sites[1] - 2:sites[1]] == ["if ((seq_WORK = btlseq.EntrySequence(cmd_DATA)) == null)", "return;"]
    assert seq[sites[1] + 1] == "seq_WORK.Flags.EventMode = true;"
    for gate in ("if (!Enabled)", "if (!Enabled || _actIds.Count == 0)", "if (_actCheckCmd == null)"):
        assert _battle_text(gate), gate                                  # one static read each when netsync is off


def test_the_action_lane_lines_and_the_proof_line_are_the_stacks():
    """The lane's log words (battlewire's LOG_ACT_*: each a C# literal of the stack, or its head) and the proof line logged
    RIGHT AFTER the peer adopt's in the selftest proof block's shape."""
    for head in (BW.LOG_ACT_CLOSED, BW.LOG_ACT_DRIFT, BW.LOG_ACT_CODEC_DRIFT, BW.LOG_ACT_DROP, BW.LOG_ACT_TAPE_REC,
                 BW.LOG_ACT_TAPE_STOPPED, BW.LOG_ACT_TAPE_CLEARED, BW.LOG_ACT_TAPE_FULL, BW.LOG_ACT_TAPE_INFO,
                 BW.LOG_ACT_TAPE_PAGE, BW.LOG_ACT_LEVER_RELEASED):
        assert _battle_text('"' + head), head
    for piece in (BW.LOG_ACT_NEVER_ENDED, BW.LOG_ACT_UNRESOLVED, BW.LOG_ACT_EDGE, "OFF -- CALIBRATION: the pre-s133 host "
                  "(no START/END records, no impact ids, no caps bit 5)", '"[NetSync] harness: action STARTs "'):
        assert _battle_text(piece), piece
    assert BW.LOG_ACT_LEVER_OFF.startswith("[NetSync] harness: action STARTs ") and BW.LOG_ACT_LEVER_ON.endswith("ON")
    assert _added_after("s133", "NetSyncClient.cs", f'"[NetSync] {BW.PROOF_ADOPT}"', f'"[NetSync] {BW.PROOF_ACTION}"')
    assert net_lines("NetSyncClient.cs", re.escape('+ (actOk ? "OK (" + actDetail + ")" : "FAIL (" + actDetail + ")"));'))
    lane = BW.ActHostLane()
    lane.lines.clear()
    lane.battle_start(4)
    lane.start("k", scripted=False, actor_slot=0, actor_flags=1, cmd_no=1, sub_no=176, tar_id=16, nonce=4, seq=1,
               enabled=True, selftest_role=True, vfx=(BW.VFX_KIND_SPECIAL, 100))
    lane.check_vfx("k", added=None)
    lane.close_battle(False)
    drift, never, closed = lane.lines
    assert _spliced(drift, "[NetSync] action lane: describe drift -- ", " (drift=", "; logged once per battle)")
    assert _spliced(never, "[NetSync] action lane: ", " START(s) never ENDed at the own battle's ", "end -- no_end=",
                    " (a normal end cannot orphan one: a defect)", "; ids ")
    assert _spliced(closed, BW.LOG_ACT_CLOSED, ") closed -- ", " START(s) (", " scripted), ", " END(s), ",
                    " impact(s) with an id (", " of them 0), dropped ", ", describe drift ")


def test_the_act_block_is_the_fifth_sub_object_at_the_catch_lines_sentinels():
    """THE CATCH-LITERAL RE-PIN (audit amendment 12): `act` sits in AppendNetsync's SECOND catch literal, right after
    `end`'s close, at its sentinels; the line stays ONE line of exactly two literals around `.Append(NetsyncF3Retired)`;
    AppendAct writes the keys in the catch line's order, each read through its NetSyncBattle getter; protocol stays 5."""
    catch = net_lines("HarnessAgent.cs", r'outer\.Append\("\\"netsync\\":\{\\"enabled')
    assert len(catch) == 1 and catch[0].count(".Append(") == 3 and ".Append(NetsyncF3Retired)" in catch[0], catch
    a, b = _literals(catch[0])
    assert '\\"follow_msg\\":null},\\"act\\":{\\"host\\":{\\"on\\":false,' in b and "act" not in a
    nothing = _agent_netsync_nothing()[0]
    assert _battle_of(nothing)["act"]["host"] == BW.ACT_HOST_SENTINELS
    # s133 wrote the catch line whole; [ff9mapkit netsync s134] s134 added `act.guest` after `act.host` and nothing else
    assert _catch_doc_in("s133") == {**nothing, "battle": {**nothing["battle"], "act": {"host": BW.ACT_HOST_SENTINELS}}}
    body = " ".join(_act_region("private static void AppendAct(", "// [ff9mapkit netsync B5] stage 5:", "HarnessAgent.cs"))
    names = re.findall(r'(?:Bool|Num|Str)\(sb, "(\w+)"', body)
    host = BW.ACT_HOST_SENTINELS
    flat = [k for k in host if not isinstance(host[k], dict) and k != "last"]
    assert len(flat) == 18 and flat[9:11] == ["dropped", "wire_dropped"], flat
    want = (flat + list(host["kinds"]) + list(host["vfx"]) + list(BW.ACT_LAST_FIELDS) + list(host["loop"])
            + [k for k in host["tape"] if k != "page"] + list(BW.ACT_PAGE_KEYS[:3]) + list(BW.ACT_PAGE_FRAME_KEYS))
    assert names == want, (names, want)
    for key, getter in (("on", "HarnessActOn"), ("dropped", "HarnessActDropped"), ("wire_dropped", "HarnessActWireDropped"),
                        ("edge_declined", "HarnessActEdgeDeclined"),
                        ("state", "HarnessActTapeState"), ("why", "HarnessActVfxWhy")):
        assert re.search(rf'(?:Bool|Num|Str)\(sb, "{key}", Memoria\.Netsync\.NetSyncBattle\.{getter}\)', body), key
    assert _added_after("s133", "HarnessAgent.cs", "AppendBattleEnd(sb);", "AppendAct(sb);")
    assert net_lines("HarnessAgent.cs", r"public const Int32 ProtocolVersion = ") == ["public const Int32 ProtocolVersion = 5;"]
    assert _battle_text("public static Boolean HarnessActOn { get { return Enabled && ActStartsOn; } }")
    assert not _battle_text("IsSelfTestRole ? _act")                     # audit 3.6: published in EVERY role


def test_state_reads_the_act_block_absent_on_s132_as_cannot():
    """On s132's catch block (s133's calibration red) every `act.host` accessor reads None and `coop_act_host` False; on the
    live block they read the sentinels and True; no `netsync` block reads None; a published block reads its values, a
    mistyped one None, and the nullable records (`last`, `tape.page`) read None at null."""
    old = State({"frame": 1, "netsync": _catch_doc_in("s132")})
    live = State({"frame": 1, "netsync": _agent_netsync_nothing()[0]})
    names = [n for p, n in State.NETSYNC_BATTLE_ACCESSORS.items() if p.startswith("act.host")]   # (s134: `act.guest`)
    assert len(names) == len(_leaves({"act": {"host": BW.ACT_HOST_SENTINELS}})) + 5 == 51, names   # + 5 whole blocks
    assert (State({"frame": 1}).coop_act_host, old.coop_act_host, live.coop_act_host) == (None, False, True)
    assert all(getattr(old, n) is None for n in names)
    assert all(getattr(live, n) is not None for p, n in State.NETSYNC_BATTLE_ACCESSORS.items()
               if p.startswith("act.host") and p not in BATTLE_NULLABLE)
    assert (live.coop_act_host_last, live.coop_act_host_tape_page, live.coop_act_host_tape_state) == (None, None, "")
    doc = _agent_netsync_nothing()[0]
    doc["battle"]["act"]["host"].update(starts=6, ends=6, on=True, nonce=3,
                                        last={"id": 6, "actor": 4, "kind": 2, "num": 3, "sub": 3},
                                        tape=dict(BW.ACT_HOST_SENTINELS["tape"], state="stopped", frames=True))
    st = State({"frame": 1, "netsync": doc})
    assert (st.coop_act_host_starts, st.coop_act_host_on, st.coop_act_host_nonce, st.coop_act_host_tape_state) == \
        (6, True, 3, "stopped")
    assert st.coop_act_host_tape_frames is None and st.coop_act_host_last["kind"] == 2   # (a bool is never an int)
    got = st.coop_act_host_last
    got["kind"] = 0
    assert st.coop_act_host_last["kind"] == 2                            # a copy


def test_a_fresh_stand_in_publishes_the_act_sentinels_and_s132_none(game):
    """The default stand-in (s133) publishes `act.host` at the agent's sentinels with no client (the tape's state the live
    "off"); the stand-in at s132 publishes no `act`, no `actbench` and no 'action lane' proof line, and answers `actbench`
    "unknown sub-verb" in s132's words."""
    want = dict(BW.ACT_HOST_SENTINELS, tape=dict(BW.ACT_HOST_SENTINELS["tape"], state="off"))
    assert _battle_of(FakeGame(game)._netsync_doc())["act"]["host"] == want      # ([ff9mapkit netsync s134] + `guest`)
    old = FakeGame(game)
    old.netsync_caps = S132_CAPS
    assert "act" not in _battle_of(old._netsync_doc()) and "actbench" not in old._netsync_subverbs()
    assert set(_leaves(_battle_of(old._netsync_doc()))) == set(_leaves(_battle_of(_catch_doc_in("s132"))))
    with pytest.raises(RuntimeError) as err:
        old._netsync(["actbench", "tape", "rec"])
    assert str(err.value) == f"netsync: unknown sub-verb 'actbench' ({'|'.join(_subverbs_in('s106'))})"


#: (fragment the agent says -- ONE C# literal of the stack, or a piece of one -- the args, where)
ACT_REFUSALS = [
    ("netsync actbench: needs the selftest role (netsync selftest 1)", ["actbench", "tape", "rec"], None),
    ("netsync actbench hoststarts: expected `hoststarts on|off`", ["actbench", "hoststarts", "maybe"], "selftest"),
    ("netsync actbench: unknown op '", ["actbench", "tapes", "rec"], "selftest"),
    ("' (tape|hoststarts)", ["actbench", "tapes", "rec"], "selftest"),
    ("netsync actbench tape: expected `tape rec|stop|clear|info` or `tape dump <from> <count>`",
     ["actbench", "tape", "bogus"], "selftest"),               # ([ff9mapkit netsync s134] `tape play` is the guest's now)
    ("netsync actbench tape dump: the tape is empty (`actbench tape rec` first)", ["actbench", "tape", "dump", "0", "4"],
     "selftest"),
    ("netsync actbench tape dump: from ", ["actbench", "tape", "dump", "9", "4"], "tape"),
    (" is past the tape's last frame (", ["actbench", "tape", "dump", "9", "4"], "tape"),
]


def _act_taped(fake, frames: int = 3):
    """A selftest stand-in whose action tape holds ``frames`` frames (fed through the lane's loopback by hand)."""
    _selftest(fake)._netsync(["actbench", "tape", "rec"])
    for i in range(frames):
        fake._act_lane.enqueue(BW.encode_action_impact(1, i, 0, 4))
    fake._act_lane.loop_actions(1000)
    return fake


@pytest.mark.parametrize("fragment,args,where", ACT_REFUSALS, ids=[f"{r[0][:36]}-{i}" for i, r in enumerate(ACT_REFUSALS)])
def test_the_stand_in_refuses_actbench_in_the_agents_words(game, fragment, args, where):
    """Every `actbench` gate the stand-in models refuses with the engine's own words (each fragment a literal of the stack)."""
    assert _battle_text(fragment), f"the live stack no longer says {fragment!r}"
    fake = FakeGame(game)
    if where == "selftest":
        _selftest(fake)
    elif where == "tape":
        _act_taped(fake)
    with pytest.raises(RuntimeError) as err:
        fake._netsync(args)
    assert fragment in str(err.value), str(err.value)


@pytest.mark.parametrize("args,param", [(["actbench"], "netsync actbench"), (["actbench", "tape"], "netsync actbench"),
                                        (["actbench", "tape", "rec", "x"], "netsync actbench"),
                                        (["actbench", "tape", "dump", "0"], "netsync actbench tape dump"),
                                        (["actbench", "tape", "dump", "-1", "4"], "netsync actbench tape dump"),
                                        (["actbench", "tape", "dump", "0", "17"], "netsync actbench tape dump"),
                                        (["actbench", "tape", "dump", "0", "0"], "netsync actbench tape dump")])
def test_an_actbench_argument_refusal_has_the_engines_whole_shape_before_any_gate(game, args, param):
    """The agent's `actbench` argument parse runs BEFORE HarnessActBench's role gate, as an ArgumentOutOfRangeException in
    Mono's whole shape -- `tape dump`'s message the agent's two literals around ActTapePageMax."""
    lines = net_lines("HarnessAgent.cs", r'ArgumentOutOfRangeException\("netsync actbench')
    agent = {_literals(ln)[0]: _literals(ln)[1] for ln in lines}
    assert set(agent) == {"netsync actbench", "netsync actbench tape dump"}, agent
    assert net_lines("HarnessAgent.cs", r'\+ Memoria\.Netsync\.NetSyncBattle\.ActTapePageMax \+ "\)"\);')
    message = agent[param] + (str(BW.ACT_TAPE_PAGE_MAX) + ")" if param.endswith("dump") else "")
    with pytest.raises(RuntimeError) as err:
        FakeGame(game)._netsync(args)                                   # no selftest role: the parse comes first
    assert str(err.value) == f"{message}\r\nParameter name: {param}", repr(str(err.value))


def test_the_actbench_ops_are_the_agents_and_the_driver_gates_them_before_the_step(game):
    """`actbench <op>`: the driver's op list and tape values are the engine's (its refusals' own lists), the sub-verb's
    capability key is `act.host` (audit amendment 13), and the driver refuses an unknown op / value before the step in the
    engine's words -- on s132 it refuses the whole sub-verb naming s133 and the engine's would-be answer. [ff9mapkit
    netsync s134] The guest ops (Session.NETSYNC_ACTBENCH_OP_CAPS) leave s133's "unknown op" list alone, and s134 REWROTE
    the agent's usage line: each engine's words are judged against a stand-in at THAT engine (s133's off s133's own
    patch), the guest forms by the s134 tests below. [ff9mapkit netsync s135] s135 rewrote the usage line again (the hold
    ops): s134's is read off s134's own patch; the hold forms by the s135 tests below. [ff9mapkit netsync s136] ...and s136
    once more (`fallback`): s135's off s135's own patch; the fallback form by the s136 tests below."""
    ops = net_lines("NetSyncBattle.cs", r"netsync actbench: unknown op '")
    assert len(ops) == 1 and tuple(re.search(r"\(([a-z|]+)\)\";", ops[0]).group(1).split("|")) == \
        Session.NETSYNC_ACTBENCH_OPS == FG.NETSYNC_ACTBENCH_OPS == FG.actbench_ops(_all_caps_through("actstart"))
    assert FG.actbench_ops(_all_caps_through("grace40")) == ()
    # (each later patch's ops by their own patch: [ff9mapkit netsync s135] the hold's `hold|lifeskip|unit` after s134's)
    later = {}
    for op, (_attr, _key, patch, _what) in Session.NETSYNC_ACTBENCH_OP_CAPS.items():
        later.setdefault(patch, []).append(op)
    assert tuple(later["s134"]) == FG.NETSYNC_ACTBENCH_GUEST_OPS == BW.ACT_GUEST_BENCH_OPS
    assert tuple(later["s135"]) == FG.NETSYNC_ACTBENCH_HOLD_OPS == BW.ACT_HOLD_BENCH_OPS
    assert tuple(later["s136"]) == FG.NETSYNC_ACTBENCH_FALLBACK_OPS == BW.ACT_FALLBACK_BENCH_OPS
    assert set(later) == {"s134", "s135", "s136"}
    tape = net_lines("NetSyncBattle.cs", r"netsync actbench tape: expected `tape ")
    m = re.search(r"`tape ([a-z|]+)` or `tape dump <from> <count>`", tape[0]) if len(tape) == 1 else None
    assert m and Session.NETSYNC_ACTBENCH_TAPE_OPS == FG.NETSYNC_ACTBENCH_TAPE_OPS == tuple(m.group(1).split("|")) + (
        "dump",), tape
    assert Session.NETSYNC_ACTBENCH_PAGE_MAX == BW.ACT_TAPE_PAGE_MAX
    assert Session.NETSYNC_BATTLE_SUBVERBS["actbench"][:3] == ("coop_act_host", "netsync.battle.act.host", "s133")
    # the agent's usage line, per engine: s133's off its own patch (the line s134 removed), s134's off the live stack
    s133_usage = [_literals(ln)[1] for ln in net_lines("HarnessAgent.cs", r'ArgumentOutOfRangeException\("netsync actbench", ',
                                                        [_patch_bytes("s133")])]
    assert s133_usage == [Session.NETSYNC_ACTBENCH_USAGE] == [FG.NETSYNC_ACTBENCH_USAGE_S133]
    # [ff9mapkit netsync s135] s134's usage off its own patch (the line s135 rewrote), s135's off the live stack
    s134_usage = [_literals(ln)[1] for ln in net_lines("HarnessAgent.cs", r'ArgumentOutOfRangeException\("netsync actbench", ',
                                                        [_patch_bytes("s134")])]
    assert s134_usage == [Session.NETSYNC_ACTBENCH_USAGE_S134] == [FG.NETSYNC_ACTBENCH_USAGE_S134]
    # [ff9mapkit netsync s136] s135's usage off its own patch (the line s136 rewrote), s136's off the live stack
    s135_usage = [_literals(ln)[1] for ln in net_lines("HarnessAgent.cs", r'ArgumentOutOfRangeException\("netsync actbench", ',
                                                        [_patch_bytes("s135")])]
    assert s135_usage == [Session.NETSYNC_ACTBENCH_USAGE_S135] == [FG.NETSYNC_ACTBENCH_USAGE_S135]
    assert _battle_text(f'"netsync actbench", "{Session.NETSYNC_ACTBENCH_USAGE_S136}");')
    assert Session.NETSYNC_ACTBENCH_USAGE_S136 == FG.NETSYNC_ACTBENCH_USAGE_S136
    for old in (Session.NETSYNC_ACTBENCH_USAGE, Session.NETSYNC_ACTBENCH_USAGE_S134,
                Session.NETSYNC_ACTBENCH_USAGE_S135):                    # s134, s135, then s136 rewrote it
        assert not _battle_text(f'"netsync actbench", "{old}");')
    tape_words = "netsync actbench tape: expected `tape rec|stop|clear|info` or `tape dump <from> <count>`"
    for caps, text in ((S133_CAPS, Session.NETSYNC_ACTBENCH_USAGE), (S134_CAPS, Session.NETSYNC_ACTBENCH_USAGE_S134),
                       (S135_CAPS, Session.NETSYNC_ACTBENCH_USAGE_S135), (None, Session.NETSYNC_ACTBENCH_USAGE_S136)):
        fake = FakeGame(game)
        if caps is not None:
            fake.netsync_caps = caps
        with session(game, fake) as g:
            g.newgame(settle=0)
            g.netsync("selftest", 1)
            n = len(fake.executed)
            usage = f"{text}\r\nParameter name: netsync actbench"
            for args, words in ((("tapes", "rec"), "netsync actbench: unknown op 'tapes' (tape|hoststarts)"),
                                (("tape", "bogus"), tape_words),
                                # [review harness-10] the hoststarts value, and the agent's argument parse (it runs FIRST)
                                (("hoststarts", "maybe"), "netsync actbench hoststarts: expected `hoststarts on|off`"),
                                ((), usage), (("tapes",), usage), (("hoststarts",), usage),
                                (("tape", "rec", "now"), usage)):
                with pytest.raises(HarnessError) as err:
                    g.netsync("actbench", *args)
                with pytest.raises(RuntimeError) as agent:
                    fake._netsync(["actbench", *args])
                assert str(err.value) == str(agent.value) == words, (caps is None, args)
            assert len(fake.executed) == n
            st = g.actbench("TAPE", "Rec")                              # the agent lowercases both; so does the driver
            assert st.coop_act_host_tape_state == "rec" and fake.executed[-1] == ["netsync", "actbench", "TAPE", "Rec"]
    fake = FakeGame(game)
    fake.netsync_caps = S132_CAPS
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.netsync("selftest", 1)
        n = len(fake.executed)
        with pytest.raises(HarnessError, match=r"^netsync actbench: the deployed engine publishes no "
                                               r"`netsync\.battle\.act\.host` .*\(memoria-patch s133\); it would answer "
                                               r"\"netsync: unknown sub-verb 'actbench'\" only after the step"):
            g.actbench("tape", "rec")
        assert len(fake.executed) == n and g.state.coop_act_host is False


def _act_own(g, fake, *, intro: int = 10):
    """A selftest OWN battle on the stand-in that FIGHTS: two players and one enemy filling their gauges in 30 frames, the
    enemy hitting for 5, each command resolving 5 frames after it is committed."""
    fake.atb_gain = 200
    fake.enemy_hit = 5
    fake.cmd_resolve_frames = 5
    fake.battle_intro_frames = intro
    fake.start_battle(306, group=4, units=[dict(u) for u in BENCH_UNITS])
    return g.wait_for(lambda s: s.commands_enabled and s.coop_act_host_nonce not in (None, -1), timeout=8.0,
                      what="the own battle's rising edge")


def test_an_own_battle_ships_starts_ends_and_impact_ids_through_the_loopback(game):
    """The stand-in's model of the s133 host (battlewire.ActHostLane through its own battles): with `tape rec` armed, each
    command's START precedes its impacts (each carrying its id) and its END follows them on the FIFO, the enemy's EnemyAtk
    START is kind 2 with num == its sub, the loopback audit pairs every END (no orphan, no caster mismatch), caps bit 5 is
    set, and the paged tape dump carries the bytes out -- the checks coop_action_host.py makes in game."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(FIELD)
        g.netsync("selftest", 1)
        st = g.actbench("tape", "rec")
        assert st.coop_act_host_tape_state == "rec" and st.coop_act_host_on is True
        st = _act_own(g, fake)
        assert st.coop_host_caps & BW.CAP_ACTION_STARTS and st.coop_peer_caps & BW.CAP_ACTION_STARTS
        for _ in range(2):
            slot = g.wait_turn()
            g.battle_command(slot, 1, sub=176, target=16)
        g.wait_for(lambda s: (s.coop_act_host_kinds_special or 0) >= 2 and s.coop_act_host_kinds_enemy
                   and s.coop_act_host_open == 0, timeout=8.0, what="two Attacks and an enemy action ENDed")
        fake.atb_gain = 0                                               # nothing more acts: the counts hold still
        g.wait_frames(10)
        st = g.state
        assert st.coop_act_host_starts == st.coop_act_host_loop_starts and st.coop_act_host_ends == st.coop_act_host_loop_ends
        assert (st.coop_act_host_loop_orphans, st.coop_act_host_loop_caster_mismatch, st.coop_act_host_noid_impacts,
                st.coop_act_host_open, st.coop_act_host_vfx_drift, st.coop_act_host_dropped) == (0, 0, 0, 0, 0, 0)
        assert st.coop_act_host_loop_paired == st.coop_act_host_ends and st.coop_act_host_vfx_checked == st.coop_act_host_starts
        st = g.actbench("tape", "stop")
        frames = g.act_tape_frames(page=5)
        assert [i for i, _ms, _b in frames] == list(range(st.coop_act_host_tape_frames)) and len(frames) > 5
        tape = [b for _i, _ms, b in frames]
        assert BW.act_order_violations(tape) == []
        starts = [BW.decode_action(b) for b in tape if BW.classify_action(BW.decode_action(b)) == "start"]
        assert len(starts) == st.coop_act_host_tape_starts == st.coop_act_host_starts
        assert all(BW.decode_action_legacy(b)["caster_slot"] == 0xFF and BW.decode_action_legacy(b)["flags"] == 0x04
                   for b in tape if len(b) == 76)
        impacts = [b for b in tape if BW.classify_action(BW.decode_action(b)) == "impact"]
        assert impacts and all(len(b) == 52 for b in impacts)
        # [review wire-3 / harness-1 / wire-4] the offline judges S133-TAPE reads: clean here, red on one corrupted frame
        assert BW.act_identity_violations(tape) == [] and BW.act_horizon_violations(tape) == []
        assert all(BW.act_inert_head(BW.decode_action_legacy(b)) for b in tape if len(b) == 76 or b[41] & 0x08)
        i = next(k for k, b in enumerate(tape) if BW.classify_action(BW.decode_action(b)) == "impact")
        bad = list(tape)
        bad[i] = tape[i][:42] + bytes([tape[i][42] ^ 0x01]) + tape[i][43:]
        assert any("legacy cmd/sub" in v for v in BW.act_identity_violations(bad))
        # [review harness-6] each impact CONSUMED the sample clock: the next sample is past every impact's horizon
        horizons = [BW.decode_action_legacy(b)["seq_horizon"] for b in impacts]
        assert len(set(horizons)) == len(horizons) and st.coop_peer_seq > max(horizons), (horizons, st.coop_peer_seq)
        enemy = [s for s in starts if not s["actor_flags"] & BW.ACTOR_IS_PLAYER]
        assert enemy and all(s["vfx_kind"] == BW.VFX_KIND_ENEMY and s["vfx_num"] == s["act_sub_no"] for s in enemy)
        attacks = [s for s in starts if s["act_cmd_no"] == 1]
        assert len({s["vfx_num"] for s in attacks if s["actor_slot"] == attacks[0]["actor_slot"]}) == 1
        assert st.coop_act_host_last is not None and st.coop_act_host_last["id"] == starts[-1]["act_id"]
        fake.end_battle(1)
        st = g.wait_for(lambda s: s.coop_host_caps == -1, timeout=4.0, what="the falling edge")
        assert st.coop_act_host_no_end == 0 and st.coop_act_host_nonce == starts[0]["nonce"]
    assert _mlog_lines(fake, BW.LOG_ACT_CLOSED) and not _mlog_lines(fake, BW.LOG_ACT_CODEC_DRIFT)


def test_hoststarts_off_is_the_pre_s133_host(game):
    """THE CALIBRATION LEVER: `actbench hoststarts off` (the CALIBRATION line) -> no START or END, no impact id (every tape
    impact 46 bytes), caps bit 5 clear, `on` false, `lever_off` true -- the s132 host on the s133 DLL; `on` again restores."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(FIELD)
        g.netsync("selftest", 1)
        g.actbench("hoststarts", "off")
        st = g.actbench("tape", "rec")
        assert (st.coop_act_host_on, st.coop_act_host_lever_off) == (False, True)
        _act_own(g, fake)
        g.battle_command(g.wait_turn(), 1, sub=176, target=16)
        st = g.wait_for(lambda s: (s.coop_act_host_loop_impacts or 0) >= 2, timeout=8.0, what="impacts")
        fake.atb_gain = 0
        g.wait_frames(10)
        g.actbench("tape", "stop")
        assert (st.coop_act_host_starts, st.coop_act_host_ends, st.coop_act_host_ext_impacts) == (0, 0, 0)
        assert not st.coop_host_caps & BW.CAP_ACTION_STARTS and st.coop_act_host_loop_impacts_ext == 0
        tape = [b for _i, _ms, b in g.act_tape_frames()]
        assert tape and all(len(b) == 46 for b in tape)
        st = g.actbench("hoststarts", "on")
        assert (st.coop_act_host_on, st.coop_act_host_lever_off) == (True, False)
    assert _mlog_lines(fake, BW.LOG_ACT_LEVER_OFF) and _mlog_lines(fake, BW.LOG_ACT_LEVER_ON)


def test_reset_releases_the_actbench_lever_and_the_tape(game):
    """HarnessReleaseBench's s133 half (audit 4.5): `hoststarts off` and a recording tape left set, `reset` -> the two
    'released with the harness' lines, and re-read WITH a fresh selftest role: lever_off false, tape off, 0 frames, no
    page."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.netsync("selftest", 1)
        g.actbench("hoststarts", "off")
        g.actbench("tape", "rec")
        fake._act_lane.enqueue(BW.encode_action_impact(1, 1, 0, 4))
        fake._act_lane.loop_actions(500)
        g.actbench("tape", "dump", 0, 1)
        st = g.wait_for(lambda s: s.coop_act_host_tape_page is not None, timeout=4.0, what="the page")
        assert st.coop_act_host_tape_frames == 1 and st.coop_act_host_lever_off is True
        g.send("reset")
        g.wait_for(lambda s: s.netsync is not None and not s.netsync["forced"], timeout=5.0, what="the release")
        st = g.netsync("selftest", 1)
        assert (st.coop_act_host_lever_off, st.coop_act_host_tape_state, st.coop_act_host_tape_frames,
                st.coop_act_host_tape_page) == (False, "off", 0, None)
    assert len(_mlog_lines(fake, BW.LOG_ACT_LEVER_RELEASED)) == 1
    assert len(_mlog_lines(fake, "frame(s); released with the harness)")) == 1


def test_the_action_lane_model_holds_the_engines_book_rules():
    """battlewire.ActHostLane -- the stand-in's model of QueueActionStart / QueueActionEnd / the impact tail / the close --
    on the rules the selftest rows cannot reach: the rising-edge decline (monotonic, logged once per process), an
    unresolved actor (no START, no id, no END), a scripted takeover ENDing the displaced id first, the END sent even with
    the lever pulled after the START, no_end vs cut, the 64-frame budget's drops, the 1024-frame tape's overflow, and the
    paged dump's clipping and refusals."""
    lane = BW.ActHostLane()
    kw = dict(nonce=1, seq=7, enabled=True, selftest_role=True)
    assert lane.start("k", scripted=False, actor_slot=0, actor_flags=1, cmd_no=1, sub_no=176, tar_id=16,
                      was_in_battle=False, **kw) == 0
    assert lane.start("k", scripted=True, actor_slot=4, actor_flags=0, cmd_no=47, sub_no=3, tar_id=1,
                      was_in_battle=False, **kw) == 0
    assert lane.edge_declined == 2 and sum(BW.LOG_ACT_EDGE in ln for ln in lane.lines) == 1
    lane.battle_start(1)
    assert lane.edge_declined == 2                                       # monotonic per process
    assert lane.start("u", scripted=False, actor_slot=0xFF, actor_flags=0, cmd_no=1, sub_no=0, tar_id=0, **kw) == 0
    assert (lane.unresolved, lane.starts, lane.ids) == (1, 0, {})
    a = lane.start("k", scripted=False, actor_slot=4, actor_flags=0, cmd_no=47, sub_no=3, tar_id=1,
                   vfx=(BW.VFX_KIND_ENEMY, 3), **kw)
    b = lane.start("k", scripted=True, actor_slot=4, actor_flags=0, cmd_no=47, sub_no=9, tar_id=1, **kw)
    assert (a, b, lane.takeovers, lane.ends, lane.scripted_starts) == (1, 2, 1, 1, 1)
    kinds = [BW.classify_action(BW.decode_action(f)) for f in lane.out]
    assert kinds == ["start", "end", "start"]                            # the displaced id's END goes FIRST
    assert BW.decode_action(lane.out[1])["act_id"] == 1 and lane.end("k", nonce=1, seq=7, enabled=True) == 0
    c = lane.start("p", scripted=False, actor_slot=0, actor_flags=1, cmd_no=1, sub_no=176, tar_id=16, **kw)
    lane.lever_off = True
    assert lane.impact("p", BW.encode_action_impact(1, 7, 0, 4), enabled=True, selftest_role=True) == \
        BW.encode_action_impact(1, 7, 0, 4)                              # the lever: 46 bytes, no id
    assert lane.end("p", nonce=1, seq=7, enabled=True) == c              # ...yet its START's END still goes
    lane.lever_off = False
    lane.start("q", scripted=False, actor_slot=1, actor_flags=1, cmd_no=1, sub_no=176, tar_id=16, **kw)
    lane.loop_actions(100)
    assert lane.loop.starts == 4 and lane.loop.ends == 2 and lane.loop.orphans == 0
    lane.close_battle(False)
    assert (lane.no_end, lane.cut, lane.loop.no_end) == (1, 0, 1) and lane.ids == {}
    lane.close_battle(True)
    assert lane.cut == 0                                                 # idempotent
    lane.battle_start(2)
    lane.start("r", scripted=False, actor_slot=1, actor_flags=1, cmd_no=1, sub_no=176, tar_id=16, **kw)
    lane.close_battle(True)
    assert (lane.no_end, lane.cut) == (0, 1)
    lane.loop_actions(50)                                                # (Reset would clear the queue: drained here)
    lane.battle_start(3)
    for i in range(BW.ACTION_BUFFER_CAP + 3):
        lane.impact("x", BW.encode_action_impact(3, i, 0, 4), enabled=True, selftest_role=True)
    assert lane.dropped == 3 and len(lane.out) == BW.ACTION_BUFFER_CAP and lane.noid_impacts == BW.ACTION_BUFFER_CAP + 3
    assert sum(BW.LOG_ACT_DROP in ln for ln in lane.lines) == 1
    assert lane.bench("tape", "dump", 0, 1, selftest_role=True, now_ms=0) == (
        False, "netsync actbench tape dump: the tape is empty (`actbench tape rec` first)")
    lane.bench("tape", "rec", -1, -1, selftest_role=True, now_ms=1000)
    lane.loop_actions(1500)                                              # the 64 queued frames reach the tape
    assert len(lane.tape) == BW.ACTION_BUFFER_CAP and lane.tape[0][0] == 500 and lane.tape_overflow == 0
    lane.tape = [(0, b"x")] * BW.ACT_TAPE_CAP                            # full, by hand
    lane.enqueue(BW.encode_action_impact(3, 1, 0, 4))
    lane.enqueue(BW.encode_action_impact(3, 2, 0, 4))
    lane.loop_actions(2000)
    assert (len(lane.tape), lane.tape_overflow) == (BW.ACT_TAPE_CAP, 2)
    assert sum(BW.LOG_ACT_TAPE_FULL in ln for ln in lane.lines) == 1
    lane.tape = lane.tape[:20]
    ok, _ = lane.bench("tape", "dump", 16, 16, selftest_role=True, now_ms=0)
    assert ok and (lane.tape_page["from"], lane.tape_page["count"], lane.tape_page["total"]) == (16, 4, 20)
    assert lane.bench("tape", "dump", 20, 1, selftest_role=True, now_ms=0)[1] == (
        "netsync actbench tape dump: from 20 is past the tape's last frame (20 frame(s))")
    lane.release()
    assert (lane.tape_state, lane.tape_page, lane.lever_off) == ("off", None, False)


def _seq_law(patches) -> tuple:
    """(the consuming `_seq` writes, the production START/END encoder calls) NetSyncBattle.cs carries over ``patches``."""
    consuming = [_strip_comment(ln) for ln in net_lines("NetSyncBattle.cs", r"_seq\s*(?:\+\+|\+=|-=)|\+\+\s*_seq", patches)]
    calls = [ln for ln in net_lines("NetSyncBattle.cs", r"EncodeAction(?:Start|End)\(_battleNonce\b", patches)]
    return consuming, calls


def test_a_start_or_end_stamps_the_sample_clock_without_consuming_it():
    """THE STATE-WRITE<=>HORIZON LAW at its call sites (review wire-2): on the live stack exactly three writes CONSUME the
    shared sample clock -- `bw.Write(_seq++)` in SampleOwnBattle, QueueActionFrame and QueueStatFrame -- and every production
    EncodeActionStart / EncodeActionEnd call (the START, the displaced END, FinishCommand's END) passes the bare
    `(_battleNonce, _seq, ` -- written, never consumed (ActionSelfTest's literal seqs are its own). The pin can fail: a
    `_seq++` at the START site turns it red."""
    def holds(patches):
        consuming, calls = _seq_law(patches)
        return (consuming == ["bw.Write(_seq++);"] * 3 and len(calls) == 3
                and all(re.search(r"EncodeAction(?:Start|End)\(_battleNonce, _seq, ", ln) for ln in calls))

    live = [(msr.PATCHES / n).read_bytes() for n in msr.stack() if n not in msr.DEAD]
    assert holds(live), _seq_law(live)
    s133 = _patch_bytes("s133")
    assert s133.count(b"EncodeActionStart(_battleNonce, _seq, ") == 1 and s133.count(b"EncodeActionEnd(_battleNonce, _seq, ") == 2
    for old, new in ((b"EncodeActionStart(_battleNonce, _seq, ", b"EncodeActionStart(_battleNonce, _seq++, "),
                     (b"EncodeActionEnd(_battleNonce, _seq, rec.Id", b"EncodeActionEnd(_battleNonce, (UInt16)(_seq + 1), rec.Id")):
        mutant = [s133.replace(old, new) if p == s133 else p for p in live]
        assert not holds(mutant), new


def _act_tape_model() -> list:
    """A tape the lane model writes by the engine's own seq law: a Zidane Attack on two targets (START at the live clock,
    each impact consuming it, the END at the clock after them), a sample tick in between, then an enemy EnemyAtk."""
    lane, seq = BW.ActHostLane(), 10
    lane.battle_start(7)
    kw = dict(nonce=7, enabled=True, selftest_role=True)
    lane.start("z", scripted=False, actor_slot=0, actor_flags=1, cmd_no=1, sub_no=176, tar_id=0x30, seq=seq,
               vfx=(BW.VFX_KIND_SPECIAL, 100), **kw)
    for tgt in (4, 5):
        lane.impact("z", BW.encode_action_impact(7, seq, 0, tgt, cmd_no=1, sub_no=176), enabled=True, selftest_role=True)
        seq += 1
    lane.end("z", nonce=7, seq=seq, enabled=True)
    seq += 1                                                             # a type-1 sample consumed one
    lane.start("e", scripted=False, actor_slot=4, actor_flags=0, cmd_no=47, sub_no=3, tar_id=1, seq=seq,
               vfx=(BW.VFX_KIND_ENEMY, 3), **kw)
    lane.impact("e", BW.encode_action_impact(7, seq, 4, 0, cmd_no=47, sub_no=3), enabled=True, selftest_role=True)
    lane.end("e", nonce=7, seq=seq + 1, enabled=True)
    return list(lane.out)


def _patched(frame: bytes, at: int, value: bytes) -> bytes:
    return frame[:at] + value + frame[at + len(value):]


def test_the_tape_judges_hold_on_the_lanes_tape_and_each_can_fail():
    """The offline judges S133-TAPE reads (review wire-3, harness-1, wire-4): on a tape written by the engine's rules, no
    identity, horizon or order violation and every START / END head INERT; then one corruption each -- every one a
    violation naming itself (the old clause compared the 46-byte reader with itself and could never fail)."""
    tape = _act_tape_model()
    kinds = [BW.classify_action(BW.decode_action(b)) for b in tape]
    assert kinds == ["start", "impact", "impact", "end", "start", "impact", "end"], kinds
    assert (BW.act_identity_violations(tape), BW.act_horizon_violations(tape), BW.act_order_violations(tape)) == ([], [], [])
    assert all(BW.act_inert_head(BW.decode_action_legacy(tape[i])) for i in (0, 3, 4, 6))
    assert not BW.act_inert_head(BW.decode_action_legacy(tape[1])) and not BW.act_inert_head(None)

    def ident(i, at, value, **kw):
        t = list(tape)
        t[i] = _patched(t[i], at, value)
        return BW.act_identity_violations(t, **kw)

    def horizon(i, seq):
        t = list(tape)
        t[i] = _patched(t[i], 1, seq.to_bytes(2, "little"))
        return BW.act_horizon_violations(t)

    assert any("legacy cmd/sub 2/176" in v for v in ident(1, 42, b"\x02\x00"))          # the impact's cmd_no
    assert any("legacy cmd/sub 1/177" in v for v in ident(2, 44, b"\xB1\x00"))          # ...its sub_no
    assert any("caster slot 2 != its START's actor 0" in v for v in ident(1, 3, b"\x02"))
    assert any("no START on the tape carries it" in v for v in ident(5, 50, b"\x09\x00"))
    assert any("id 0" in v for v in ident(5, 50, b"\x00\x00")) and ident(5, 50, b"\x00\x00", require_id=False) == []
    assert any("slots 255/255" in v for v in ident(1, 3, b"\xFF\xFF"))                  # nothing a guest could apply
    assert any("slots 9/4" in v for v in ident(1, 3, b"\x09"))
    assert any(v.startswith("END 1 at frame 3: legacy cmd/sub") for v in ident(3, 42, b"\x05\x00"))
    assert ident(1, 3, b"\xFF") == []                                                   # caster 0xFF: the target's own
    assert any("consumes seq 10, not after" in v for v in horizon(2, 10))                 # a repeated horizon
    assert any("START at frame 4 (nonce 7) stamps seq 0, not after" in v for v in horizon(4, 0))   # zeroed / stale
    assert horizon(4, 13) == []                                          # the enemy START at the live clock: 13
    assert any("START at frame 4 (nonce 7) stamps seq 14, past the next consumed 13" in v for v in horizon(4, 14))
    assert any("END at frame 3 (nonce 7) stamps seq 11, not after" in v for v in horizon(3, 11))
    assert horizon(0, 9) == [] and horizon(6, 40) == []                 # no consuming frame before / after: unbounded
    wrap = [_patched(b, 1, ((BW.decode_action_legacy(b)["seq_horizon"] + 0xFFF0) & 0xFFFF).to_bytes(2, "little"))
            for b in tape]
    assert BW.act_horizon_violations(wrap) == []                         # wrap-aware across 0xFFFF -> 0
    end = BW.decode_action_legacy(_patched(tape[3], 4, b"\x04"))
    assert not BW.act_inert_head(end)                                    # an END a pre-s134 guest would apply as lethal
    assert not BW.act_inert_head(BW.decode_action_legacy(_patched(tape[0], 25, b"\x01")))   # a raw on a START


def test_lifecycles_are_keyed_by_nonce_and_id_across_battles():
    """act_order_violations keys a lifecycle by (nonce, id) (review wire-6): ids restart at 1 every own battle, so a tape
    or a recording that spans two battles is clean -- and a second START of one (nonce, id) is a violation."""
    one = _act_tape_model()
    two = [_patched(b, 0, b"\x08") for b in one]                       # battle 2: the same ids under nonce 8
    assert BW.act_order_violations(one + two) == [] and BW.act_identity_violations(one + two) == []
    assert BW.act_horizon_violations(one + two) == []                    # per nonce
    again = BW.act_order_violations(one + [one[0]])
    assert again and "START 1 (nonce 7) at frame 7 again (first at frame 0)" in again[0]
    late = BW.act_order_violations(one + [one[1]])
    assert late and "impact id 1 (nonce 7) at frame 7 after its END" in late[0]


def test_the_tape_summary_counts_a_flagged_record_with_no_extension_as_bad():
    """`tape info`'s buckets (ActTapeSummary and its twin) now sum to the frames (review wire-5): a frame flagged START or
    END with NO extension at all is `bad` -- as ActLoopBook counts it `ext_bad` -- not in no bucket."""
    bare = BW.encode_action_impact(7, 1, 0xFF, 0xFF, flags=BW.ACT_FLAG_END)            # 46 bytes, END flag, no extension
    s = BW.act_tape_summary(_act_tape_model() + [bare])
    assert (s["frames"], s["starts"], s["ends"], s["impacts"], s["stat"], s["bad"]) == (8, 2, 2, 3, 0, 1)
    assert s["starts"] + s["ends"] + s["impacts"] + s["stat"] + s["bad"] == s["frames"]
    book = BW.ActLoopBook()
    a = BW.parse_action(bare)
    book.feed(a, BW.read_action_ext(bare, a))
    assert book.ext_bad == 1
    body = " ".join(_act_region("private static String ActTapeSummary()", "return \"[NetSync] action tape: \""))
    assert "else if (r == ActExtReadNone) bad++;" in body, body


def test_wire_dropped_is_the_transports_drop_count_per_own_battle():
    """`act.host.wire_dropped` (review engine-2 / wire-1): the drop-oldest point that fills on a stalled link is the
    TRANSPORT's out-queue (NetSyncFrames.EnqueueAction, shared by NetSyncSocket and NetSyncRelay), so it counts there, under
    its lock; INetTransport exposes it (and re-arms the once-per-link drop line); Pump takes the baseline at its own battle's
    rising edge (right after NoteOwnBattleStart, whose ActBattleStart zeroes the count) and adds each flush's cost --
    `dropped` stays _actionsOut's per-tick burst budget. The lane model and the sentinels carry it (0: no transport)."""
    sock = net_lines("NetSyncSocket.cs", r".")
    for line in ("Int32 ActionsDropped { get; }", "void RearmActionDropLog();",
                 "_actionsDropped++;          // [ff9mapkit netsync s133] counted under the lock (`act.host.wire_dropped`)",
                 "public Int32 ActionsDropped { get { lock (_lock) { return _actionsDropped; } } }",
                 "public void RearmActionDropLog() { lock (_lock) { _actionDropLogged = false; } }"):
        assert line in sock, line
    for f in ("NetSyncSocket.cs", "NetSyncRelay.cs"):
        assert "public Int32 ActionsDropped { get { return _frames.ActionsDropped; } }      // [ff9mapkit netsync s133]" in \
            net_lines(f, r"ActionsDropped"), f
    enq = _new_side("NetSyncSocket.cs", _patch_bytes("s133"))
    k = next(i for i, (_h, _k, t) in enumerate(enq) if t.startswith("_actionsDropped++;"))
    assert [t for _h, _k, t in enq[k - 2:k]] == ["{", "_outActions.Dequeue();"]
    assert _added_after("s133", "NetSyncBattle.cs", "NoteOwnBattleStart();      // [ff9mapkit netsync B4] stage 1",
                        "ActWireBattleStart(socket);")
    assert _added_after("s133", "NetSyncBattle.cs", "socket.SendAction(_actionsOut[i]);", "ActWireNote(socket);")
    assert _battle_text("_actWireDropped = 0;") and _battle_text("_actWireDropped += now - _actWireSeen;")
    assert _battle_text("public static Int32 HarnessActWireDropped { get { return _actWireDropped; } }")
    assert BW.ACT_HOST_SENTINELS["wire_dropped"] == 0 and BW.ActHostLane().doc(enabled=True, selftest_role=True)[
        "wire_dropped"] == 0


def test_the_selftest_falling_edge_discards_what_pump_discards(game):
    """The loopback models the wire at the falling edge too (review engine-3): Pump clears _actionsOut there without
    sending, so SelfTestPump's falling edge no longer loops it -- LoopActions runs only on in-battle ticks, and the stand-in
    drops a frame left in the buffer at the edge (it never reaches the audit or the tape)."""
    calls = [ln for ln in net_lines("NetSyncBattle.cs", r"\bLoopActions\(\);") if not ln.startswith("private static")]
    assert len(calls) == 1 and calls[0].startswith("LoopActions();"), calls
    assert _added_after("s133", "NetSyncBattle.cs", "if (_wasInBattle)", "ActCloseBattle(false);             // [ff9mapkit")
    fake = _selftest(FakeGame(game))
    fake._netsync(["actbench", "tape", "rec"])
    fake._act_lane.battle_start(3)
    fake._act_lane.enqueue(BW.encode_action_impact(3, 1, 0, 4))           # buffered after the last in-battle tick
    fake._nb_own_end()
    assert (fake._act_lane.out, fake._act_lane.tape, fake._act_lane.loop.impacts) == ([], [], 0)


def test_the_reentry_test_matches_the_scripted_sequence_not_the_displaced_action():
    """ScriptedSequenceRunning (review engine-7): the displaced CommandEngine action keeps the same CMD_DATA until it is
    released, so the re-entry test matches the SCRIPTED sequence itself -- on SFXRework an EnemySequence of the scripted
    record's number, on the old engine an EventMode slot (only StartBtlSeq sets EventMode)."""
    assert _battle_text("Boolean seqRunning = !scripted && _actScripted.TryGetValue(cmd, out scr) && "
                        "ScriptedSequenceRunning(btlsys, cmd, scr.SubNo);")
    body = " ".join(_act_region("private static Boolean ScriptedSequenceRunning(", "catch"))
    for piece in ("ReferenceEquals(a.cmd, cmd) && a.effectType == UnifiedBattleSequencer.EffectType.EnemySequence",
                  "&& a.effectNum == seqNo", "ReferenceEquals(work[i].CmdPtr, cmd) && work[i].Flags.EventMode"):
        assert piece in body, piece


def test_the_describe_drift_and_the_lane_lines_name_the_command_by_number():
    """The engine names a command by its NUMBER in `vfx.why` and the lane's lines (review harness-7: an enum concatenated
    prints its name -- 'Attack sub 176' -- where the twin prints '1 sub 176'): every s133 concatenation casts, and one drift
    `why` from the lane model reads exactly the engine's shape."""
    s133 = [_patch_bytes("s133")]
    assert net_lines("NetSyncBattle.cs", r"\+ cmd\.cmd_no \+", s133) == []
    assert len(net_lines("NetSyncBattle.cs", r"\+ \(Int32\)cmd\.cmd_no \+", s133)) == 3
    lane = BW.ActHostLane()
    lane.battle_start(4)
    lane.start("k", scripted=False, actor_slot=0, actor_flags=1, cmd_no=1, sub_no=176, tar_id=16, nonce=4, seq=1,
               enabled=True, selftest_role=True, vfx=(BW.VFX_KIND_SPECIAL, 100))
    lane.check_vfx("k", added=(False, 19))
    assert lane.vfx_why == "id 1 slot 0 1 sub 176: described special 100, SelectCommandVfx added a SpecialEffect 19"
    assert _battle_text('_actVfxWhy = "id " + _actCheckId + " slot " + _actCheckActor + " " + (Int32)cmd.cmd_no + " sub "')


def test_the_stock_ids_the_lane_and_its_bench_name_are_the_engines_when_the_clone_is_here():
    """battlewire's stock ids (CS_STOCK_IDS: BattleCommandId, BattleAbilityId.Attack, RegularItem.Potion,
    SpecialEffect.Special_No_Effect) are not in the patch stack: read them off the shared Memoria clone when this machine has
    it (review harness-8) -- a wrong id would leave the twin's branch tests green and the in-game checks red. The s133 bench
    takes them from battlewire, never its own copies."""
    root = pathlib.Path(r"C:\gd\FFIX\Memoria\Assembly-CSharp\Memoria\Data\Battle")
    if not root.is_dir():
        pytest.skip("the shared Memoria clone is not on this machine")
    for name, value in BW.CS_STOCK_IDS.items():
        enum, member = name.split(".")
        text = (root / f"{enum}.cs").read_text(encoding="utf-8-sig", errors="replace")
        m = re.search(rf"^\s*{member}\s*=\s*(-?\d+)\s*,?", text, re.M)
        assert m and int(m.group(1)) == value, name
    bench = (SCENARIOS / "coop_action_host.py").read_text(encoding="utf-8")
    assert "CMD_ATTACK, ATTACK_SUB = BW.CMD_ATTACK_ID, BW.ABILITY_ATTACK_ID" in bench
    assert "CMD_ITEM, POTION = BW.CMD_ITEM_ID, BW.ITEM_POTION_ID" in bench


# =========================================================================== [ff9mapkit netsync s134]
# THE GUEST ACTION REPLAY (studies/battle-coop/R3-DESIGN.md 3.3.3 as amended by R3-ACTION-REPLAY-AUDIT.md 2.2 and section 3
# -- the audit's "s123"; group 2 renumbered s133-s141). Guest only, wire v14, harness protocol 5: one additive sub-object
# (`netsync.battle.act.guest`), seven unit keys, the `actbench` guest ops (no new sub-verb), one proof line, the
# [Netsync] ActionReplay behaviour key. battlewire's twins of the PURE decisions (NetSyncDiorama.Replay.cs) EVALUATE
# ActReplaySelfTest's OWN 30 rows off the stack -- translated statement by statement (its lambdas, its book, its ternary
# mask resolver included), so a row's arguments, verdict or order changed on either side turns a test red -- each rule's
# mutant fails a row, the constants are pinned by name both ways, and s133 -- s134's calibration red -- is the ladder
# prefix through `actstart` (S133_CAPS): every check below that reads the key, the ops or the proof line reads "cannot"
# there.
from types import SimpleNamespace                                       # noqa: E402

REPLAY_FILE = "NetSyncDiorama.Replay.cs"
#: ActReplaySelfTest's own helpers' bodies, pinned (the namespace below implements exactly these)
REP_HELPER_BLOCKS = {
    "private static ActDecideIn ActTestDecideBase()": [
        "ActDecideIn d = new ActDecideIn();", "d.ActorLinked = true;", "d.CmdNo = (Int32)BattleCommandId.Attack;",
        "d.Kind = NetSyncBattle.VfxKindSpecial;", "d.MappedTar = 0x10;", "return d;"],
    "private static Int32 ActTestDecide(ActTestEditBoxed edit)": [
        "ActDecideIn d = ActTestDecideBase();", "ActDecideBox box = new ActDecideBox { D = d };", "edit(box);",
        "d = box.D;", "return ActDecide(ref d);"],
    "private static ActRec ActTestRec(UInt16 id, Byte actor)": [
        "return new ActRec", "{",
        "Key = ActBook.KeyOf(ActTestNonce, id), Id = id, Nonce = ActTestNonce, ActorSlot = actor, ActorFlags = "
        "NetSyncBattle.ActorIsPlayer,", "CmdNo = (UInt16)BattleCommandId.Attack, VfxKind = NetSyncBattle.VfxKindSpecial, "
                                        "State = ActStRegistered", "};"],
}


def _rep_mask(code: str) -> tuple:
    """C# string literals -> ``__S<n>__`` placeholders (their Python reprs kept aside)."""
    strings = []

    def keep(m):
        strings.append(repr(m.group(1).replace('\\"', '"').replace("\\\\", "\\")))
        return f"__S{len(strings) - 1}__"
    return _CS_STRING.sub(keep, code), strings


def _rep_split(code: str, sep: str) -> list:
    """``code`` (strings masked) split at its depth-0 ``sep``."""
    out, depth, cur = [], 0, ""
    for c in code:
        if c in "({[":
            depth += 1
        elif c in ")}]":
            depth -= 1
        if c == sep and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += c
    out.append(cur.strip())
    return out


def _rep_close(code: str, at: int, opener: str, closer: str) -> int:
    """The index of the ``closer`` matching ``code[at] == opener``."""
    depth = 0
    for k in range(at, len(code)):
        depth += 1 if code[k] == opener else -1 if code[k] == closer else 0
        if depth == 0:
            return k
    raise AssertionError(f"unbalanced {opener}: {code!r}")


def _rep_tern(code: str) -> str:
    """C#'s right-associative ``c ? a : b`` (depth 0) -> Python's ``(a if c else b)``."""
    depth, q = 0, -1
    for k, c in enumerate(code):
        depth += 1 if c in "([" else -1 if c in ")]" else 0
        if c == "?" and depth == 0:
            q = k
            break
    if q < 0:
        return code
    depth, nest = 0, 0
    for k in range(q + 1, len(code)):
        c = code[k]
        depth += 1 if c in "([" else -1 if c in ")]" else 0
        if depth:
            continue
        if c == "?":
            nest += 1
        elif c == ":":
            if nest == 0:
                return (f"(({_rep_tern(code[q + 1:k].strip())}) if ({code[:q].strip()}) else "
                        f"({_rep_tern(code[k + 1:].strip())}))")
            nest -= 1
    raise AssertionError(f"a ? with no : in {code!r}")


def _rep_not(code: str) -> str:
    """C#'s ``!`` (never ``!=``) -> ``(not <operand>)``: an identifier chain with its calls and member reads, or a
    parenthesised group."""
    while True:
        m = re.search(r"!(?!=)", code)
        if not m:
            return code
        k = m.end()
        while code[k] == " ":
            k += 1
        if code[k] == "(":
            end = _rep_close(code, k, "(", ")") + 1
        else:
            w = re.match(r"[\w.]+", code[k:])
            assert w, code
            end = k + w.end()
        while end < len(code) and code[end] in "(.":
            if code[end] == "(":
                end = _rep_close(code, end, "(", ")") + 1
            else:
                w = re.match(r"\.[\w]+", code[end:])
                end += w.end()
        code = code[:m.start()] + "(not " + code[k:end] + ")" + code[end:]


def _rep_expr(expr: str, strings: list | None = None) -> str:
    """One C# expression of ActReplaySelfTest as Python: lambdas (``d => d.X = v`` / ``d => { d.X = v; ... }`` -> a
    Python lambda that sets the snake_cased fields; ``i => <expr>`` -> a lambda), right-associative ternaries, casts
    dropped, ``ref`` / ``out`` locals by NAME, ``new T()`` -> ``T()``, ``local.Member`` -> ``__m(local, 'Member')``,
    true/false/null, && / || / !. ``strings`` = the caller's masked literals (else masked here)."""
    own = strings is None
    if own:
        expr, strings = _rep_mask(expr)
    lambdas: list = []
    while True:
        m = re.search(r"\b([a-z]\w*) => ", expr)
        if not m:
            break
        var, j = m.group(1), m.end()
        if expr[j] == "{":
            close = _rep_close(expr, j, "{", "}")
            sets = []
            for st in [s for s in _rep_split(expr[j + 1:close], ";") if s]:
                a = re.fullmatch(rf"{var}\.(\w+) = (.+)", st, re.S)
                assert a, st
                sets.append(f"__set({var}, {a.group(1)!r}, {_rep_expr(a.group(2), strings)})")
            py, stop = f"(lambda {var}: [{', '.join(sets)}])", close + 1
        else:
            depth, stop = 0, len(expr)
            for k in range(j, len(expr)):
                depth += 1 if expr[k] in "([" else -1 if expr[k] in ")]" else 0
                if depth < 0 or (depth == 0 and expr[k] == ","):
                    stop = k
                    break
            body = expr[j:stop].strip()
            a = re.fullmatch(rf"{var}\.(\w+) = (.+)", body, re.S)
            py = (f"(lambda {var}: [__set({var}, {a.group(1)!r}, {_rep_expr(a.group(2), strings)})])" if a else
                  f"(lambda {var}: {_rep_expr(body, strings)})")
        lambdas.append(py)
        expr = expr[:m.start()] + f"__L{len(lambdas) - 1}__" + expr[stop:]
    code = _rep_tern(expr)
    code = re.sub(r"\((?:Int32|UInt16|Byte|UInt32|Int64)\)", "", code)
    code = re.sub(r"\b(?:ref|out) (\w+)", r"'\1'", code)
    code = re.sub(r"\bnew (\w+)\(\)", r"\1()", code)
    code = re.sub(r"\b([a-z]\w*)\.([A-Z]\w*)", r"__m(\1, '\2')", code)
    code = re.sub(r"\btrue\b", "True", code)
    code = re.sub(r"\bfalse\b", "False", code)
    code = re.sub(r"\bnull\b", "None", code)
    code = _rep_not(code.replace("&&", " and ").replace("||", " or "))
    for i, py in enumerate(lambdas):
        code = code.replace(f"__L{i}__", py)
    if own:
        for i, s in enumerate(strings):
            code = code.replace(f"__S{i}__", s)
    return code


_REP_DECL = re.compile(r"(?:ActDecideIn|ActBook|ActRec|Int32|String|Boolean) (\w+ = .+)", re.S)


def _rep_python(stmts: list) -> list:
    """ActReplaySelfTest's statements as Python source lines: a Row -> ``__row(expr, name)`` (its name a C# concatenation,
    evaluated); a declaration (several declarators too) -> its assignments; ``local.Member = v`` -> ``__set``; anything
    else (a call) as itself."""
    out = []
    for s in stmts:
        assert isinstance(s, str), s                                   # (no loop in this selftest)
        masked, strings = _rep_mask(s)

        def back(code):
            for i, lit in enumerate(strings):
                code = code.replace(f"__S{i}__", lit)
            return code
        m = re.fullmatch(r"Row\((.*)\)", masked, re.S)
        if m:
            args = _rep_split(m.group(1), ",")
            assert len(args) == 4 and args[2:] == ["ref rows", "ref fail"], args
            name = " + ".join(f"str({_rep_expr(part, strings)})" for part in _rep_split(args[1], "+"))
            out.append(back(f"__row({_rep_expr(args[0], strings)}, {name})"))
            continue
        m = _REP_DECL.fullmatch(masked)
        if m:
            for d in _rep_split(m.group(1), ","):
                name, _, value = d.partition("=")
                out.append(back(f"{name.strip()} = {_rep_expr(value.strip(), strings)}"))
            continue
        m = re.fullmatch(r"([a-z]\w*)\.([A-Z]\w*) = (.+)", masked, re.S)
        if m:
            out.append(back(f"__set({m.group(1)}, {m.group(2)!r}, {_rep_expr(m.group(3), strings)})"))
            continue
        out.append(back(_rep_expr(masked, strings)))
    return out


def _rep_program() -> str:
    """ActReplaySelfTest, read off the stack (the hunk that holds it whole), as one Python program."""
    block = _cs_block(REPLAY_FILE, "internal static Boolean ActReplaySelfTest(")
    code = " ".join(_strip_comment(ln) for ln in block if not re.match(r"(?:internal|private|public) static ", ln))
    return "\n".join(_rep_python(_act_statements(code)))


def _rep_ns(**twins) -> dict:
    """The namespace ActReplaySelfTest runs in: the constants by C# name (NetSyncBattle's and BattleCommandId's as
    attribute holders), the twins under their C# names (``twins`` replaces one -- a mutant), its own helpers (the pinned
    bodies of REP_HELPER_BLOCKS), ``ref`` locals by NAME, and ``__row`` asserting each row."""
    tw = dict(decide=BW.act_decide, dead=BW.act_dead_may_run, stance=BW.act_stance_gate, motion=BW.act_cmd_motion_filter,
              pending=BW.act_pending_abort_due, transport=BW.act_backlog_transport, bench=BW.act_backlog_bench,
              delta=BW.act_battle_delta, abort=BW.act_abort_why, restore=BW.act_restore_scope, hold=BW.act_end_hold_step,
              grace=BW.act_grace_arms, status=BW.act_cmd_status_for, masks=BW.act_map_mask_with, book=BW.ActBook,
              cursor=BW.act_cursor_bit_after, disappear=BW.act_restores_disappear, preinject=BW.act_pre_inject_mask,
              holdbreak=BW.act_end_hold_breaks, sfx=BW.act_sfx_drop_plan)
    tw.update(twins)
    ns = dict(BW.CS_REPLAY_CONSTANTS)
    names: list = []

    def row(ok, name):
        if ok is not True:
            raise AssertionError(f"row {name!r} is {ok!r} for the twins")
        names.append(name)

    def member(obj, name):
        return obj[_snake(name)] if isinstance(obj, dict) else getattr(obj, _snake(name))

    def set_member(obj, name, value):
        if isinstance(obj, dict):
            assert _snake(name) in obj, name
            obj[_snake(name)] = value
        else:
            setattr(obj, _snake(name), value)

    book_cls = tw["book"]

    class _Book:                                                       # `new ActBook()` and `ActBook.KeyOf(..)`
        KeyOf = staticmethod(book_cls.key_of)

        def __new__(cls):
            return book_cls()

    def decide_base():                                                 # ActTestDecideBase
        return BW.act_decide_in(actor_linked=True, cmd_no=BW.CMD_ATTACK_ID, kind=BW.VFX_KIND_SPECIAL, mapped_tar=0x10)

    def test_decide(edit):                                             # ActTestDecide(edit)
        d = decide_base()
        edit(d)
        return tw["decide"](d)

    ns.update(__row=row, __m=member, __set=set_member, __names__=names,
              NetSyncBattle=SimpleNamespace(**BW.CS_ACTION_CONSTANTS),
              BattleCommandId=SimpleNamespace(**{k.split(".", 1)[1]: v for k, v in BW.CS_STOCK_IDS.items()
                                                 if k.startswith("BattleCommandId.")}),
              ActTestNonce=BW.ACT_REPLAY_TEST_NONCE, ActBook=_Book, ReferenceEquals=lambda a, b: a is b,
              ActDecide=lambda name: tw["decide"](ns[name]), ActDeadMayRun=tw["dead"], ActStanceGate=tw["stance"],
              ActCmdMotionFilter=tw["motion"], ActPendingAbortDue=tw["pending"], ActBacklogTransport=tw["transport"],
              ActBacklogBench=tw["bench"], ActBattleDelta=tw["delta"], ActAbortWhy=tw["abort"],
              ActRestoreScope=tw["restore"], ActEndHoldStep=tw["hold"], ActGraceArms=tw["grace"],
              ActCmdStatusFor=tw["status"], ActMapMaskWith=tw["masks"], ActCursorBitAfter=tw["cursor"],
              ActRestoresDisappear=tw["disappear"], ActPreInjectMask=tw["preinject"], ActEndHoldBreaks=tw["holdbreak"],
              ActSfxDropPlan=tw["sfx"], ActTestDecideBase=decide_base,
              ActTestDecide=test_decide,
              ActTestRec=lambda i, actor: BW.ActRec(i, BW.ACT_REPLAY_TEST_NONCE, actor, BW.ACTOR_IS_PLAYER,
                                                    cmd_no=BW.CMD_ATTACK_ID, vfx_kind=BW.VFX_KIND_SPECIAL,
                                                    state=BW.ACT_ST_REGISTERED))
    return ns


def _run_rep_selftest(**twins) -> list:
    ns = _rep_ns(**twins)
    exec(compile(_rep_program(), "<ActReplaySelfTest>", "exec"), ns)           # noqa: S102 -- the stack's own rows
    return ns["__names__"]


#: ActReplaySelfTest's rows the audit's amendments name (their names are the engine's, verbatim)
REP_ROW_MARKS = ("decide: an END before the launch declines `stale`, ahead of `backlog`",
                 "decide: a dying caster's EnemyDying runs while die_seq < 5 and linked (review F3)",
                 "stance: MP_IDLE_CMD for a player's <= RushAttack or > 99 command only (no Sys*, no enemy, no transform)",
                 "motion: the stock filter -- a Sys* replay holds no command motion unless includeSysCmd",
                 "drain: a START and its END in one drain -> stale; a START without its END is not",
                 "backlog: before LIVE, on a stale lane, or at its stale->live edge; never in a steady live lane",
                 "clock: battle time skips only a span between two paused reads; a negative delta counts nothing",
                 "restore: nothing after a natural end; the full restore after an abort; the shared lanes only after an "
                 "injection",
                 "grace: bit 5, a replaying guest, a player caster's lethal hit on a living AttackOnDeath enemy -- nothing "
                 "less",
                 "setvariable: a replay's cmd_status changes bit 1 only (the high byte kept)",
                 # [s134 review] contain-restore-gaps / timing-02 / timing-01 / contain-abort-sfx-loader-lock / harness-5
                 "restore: the full restore puts the cursor bit back (the limited one leaves InjectEnd's); a dead enemy stays "
                 "faded, a dead player shows",
                 "restore: right before an injection, the units of replays aborted before it that no running replay acts with",
                 "end: a hold the host's block moved past, or whose lane went stale, injects what it held at once",
                 "abort: an unplayed SFX is cancelled, a camera load holding the loader unlocked too; a playing one is the "
                 "release's",
                 "decide: the replay lever declines `lever`, ahead of `rework` and `backlog`")


def test_the_replay_twins_evaluate_every_replay_selftest_row_off_the_stack():
    """battlewire's s134 twins (the decision, the book, the backlog verdicts, the clock, the abort / restore / end-hold /
    grace rules, the cmd_status filter, the mask mapping; the review's cursor-bit / disappear / pre-injection restore, hold
    break and SFX drop) against ActReplaySelfTest's OWN rows, EVALUATED in order: 34, the proof line's count. Its helpers
    are the pinned bodies (REP_HELPER_BLOCKS)."""
    names = _run_rep_selftest()
    assert len(names) == BW.REPLAY_SELFTEST_ROWS == 34 and len(set(names)) == 34, names
    assert all(mark in names for mark in REP_ROW_MARKS), set(REP_ROW_MARKS) - set(names)
    prefix = lambda n: n.split(":", 1)[0]                                # noqa: E731
    assert [sum(prefix(n) == p for n in names) for p in ("decide", "drain", "pending", "backlog", "backlog (bench)")] \
        == [14, 3, 2, 1, 1], names
    assert sum("ref rows, ref fail);" in ln for ln in net_lines(REPLAY_FILE, r".", [_patch_bytes("s134")])) == 34
    for start, body in REP_HELPER_BLOCKS.items():
        got = [c for c in (_strip_comment(t) for t in _cs_block(REPLAY_FILE, start, "}")) if c][2:]
        assert got[:len(body)] == body, (start, got)
    assert _battle_text("private const Byte ActTestNonce = 0x5B;") and BW.ACT_REPLAY_TEST_NONCE == 0x5B


class _BookStaleOnlyRegistered(BW.ActBook):
    def host_end(self, key, now):                                       # a PARKED record never turns stale
        r = self.by_id.get(key)
        if r is not None and r.state == BW.ACT_ST_WAITING:
            r.host_ended, r.host_end_ms = True, now
            return r
        return super().host_end(key, now)


class _BookStaleRunning(BW.ActBook):
    def host_end(self, key, now):                                       # a RUNNING record turns stale too
        r = super().host_end(key, now)
        if r is not None:
            r.stale = True
        return r


class _BookDuplicates(BW.ActBook):
    def register_start(self, r):                                        # a duplicate key registers again
        self.by_id[r.key] = r
        self.queue.append(r)
        return True


class _BookKeyNoShift(BW.ActBook):
    @staticmethod
    def key_of(nonce, act_id):                                          # the nonce OR'd in, not shifted
        return (nonce & 0xFF) | (act_id & 0xFFFF)


class _BookNoSupersede(BW.ActBook):
    def park(self, r, now):
        super().park(r, now)
        return None


class _BookAnyActor(BW.ActBook):
    def park(self, r, now):                                             # any waiting record is superseded
        older = next((q for q in self.queue if q is not r and q.state == BW.ACT_ST_WAITING), None)
        r.state, r.wait_since_ms = BW.ACT_ST_WAITING, now
        return older


#: ActDecide's reasons before `stale` in its order (an order mutant moves `stale` / `backlog` ahead of some of them)
_EARLY = ("knob_off", "lever_off", "no_rework", "end_presented")


def _decide_with(**changes):
    """ActDecide with ONE rule broken (the twin's own body otherwise)."""
    def decide(d):
        if changes.get("backlog_first") and d["backlog"] and not any(d[k] for k in _EARLY + ("leaving",)):
            return BW.ACT_WHY_BACKLOG                                   # backlog ahead of stale
        if changes.get("stale_first") and d["stale"]:
            return BW.ACT_WHY_STALE                                     # stale ahead of every reason (knob too)
        if changes.get("stale_before_leave") and d["stale"] and not any(d[k] for k in _EARLY):
            return BW.ACT_WHY_STALE                                     # stale ahead of leave
        if changes.get("busy_gt") and d["running"] == BW.ACT_MAX_RUNNING and d["kind"] != BW.VFX_KIND_NONE:
            return BW.act_decide(dict(d, running=0))                    # `>` for `>=` at the running cap
        if changes.get("noop_first") and d["kind"] == BW.VFX_KIND_NONE and not d["knob_off"]:
            return BW.ACT_NOOP                                          # noop ahead of target
        if changes.get("busy_before_noop") and d["kind"] == BW.VFX_KIND_NONE and d["running"] >= BW.ACT_MAX_RUNNING:
            return BW.ACT_WHY_BUSY                                      # the running cap ahead of noop
        if changes.get("lever_before_knob") and d["lever_off"]:
            return BW.ACT_WHY_LEVER                                     # lever ahead of knob (S134-I's premise)
        if changes.get("rework_before_lever") and d["no_rework"] and not d["knob_off"]:
            return BW.ACT_WHY_REWORK                                    # rework ahead of lever
        if changes.get("backlog_before_lever") and d["backlog"] and not d["knob_off"]:
            return BW.ACT_WHY_BACKLOG                                   # backlog ahead of lever (J / BL / H's premise)
        return BW.act_decide(d)
    return decide


@pytest.mark.parametrize("twins", [
    {"decide": _decide_with(backlog_first=True)}, {"decide": _decide_with(stale_first=True)},
    {"decide": _decide_with(stale_before_leave=True)}, {"decide": _decide_with(busy_gt=True)},
    {"decide": _decide_with(noop_first=True)}, {"decide": _decide_with(busy_before_noop=True)},
    {"decide": lambda d: BW.act_decide(dict(d, die_seq=0))},
    {"decide": lambda d: BW.act_decide(dict(d, actor_linked=True))},
    {"decide": lambda d: BW.ACT_GO if d["dead_or_dying"] and d["cmd_no"] == BW.CMD_ENEMY_COUNTER and not any(
        d[k] for k in ("knob_off", "lever_off", "no_rework", "end_presented", "leaving", "stale", "backlog")) else
        BW.act_decide(d)},
    {"stance": lambda p, mt, c: bool(p) and not mt and (c <= BW.CMD_SYS_TRANS or c > BW.CMD_BOUNDARY_UPPER_CHECK)},
    {"stance": lambda p, mt, c: bool(p) and (c <= BW.CMD_RUSH_ATTACK or c > BW.CMD_BOUNDARY_UPPER_CHECK)},
    {"motion": lambda inc, c: c <= BW.CMD_ENEMY_REACTION or c >= BW.CMD_SCRIPT_COUNTER1},
    {"book": _BookStaleOnlyRegistered}, {"book": _BookStaleRunning}, {"book": _BookDuplicates},
    {"book": _BookKeyNoShift}, {"book": _BookNoSupersede}, {"book": _BookAnyActor},
    {"pending": lambda since, now: now - since > BW.ACT_PENDING_ABORT_MS},
    {"transport": lambda live, now, prev: not live or not now},
    {"bench": lambda normal, live, edge: not normal and not live},
    {"bench": lambda normal, live, edge: not normal or not live or edge},
    {"delta": lambda delta, prev, now: max(0, delta)},
    {"delta": lambda delta, prev, now: 0 if delta <= 0 or prev or now else delta},
    {"abort": lambda gone, ended, end_ms, now, wall: "actor" if gone else "host-end" if ended and now - end_ms >=
        BW.ACT_HOST_END_ABORT_MS else "cap" if wall > BW.ACT_WALL_CAP_MS else None},
    {"restore": lambda aborted, injected: BW.ACT_RESTORE_FULL if aborted else BW.ACT_RESTORE_NONE},
    {"hold": lambda kind, acting, held: BW.ACT_END_HOLD if kind and acting else BW.ACT_END_NO_HOLD},
    {"grace": lambda bit5, can, caster, tgt, die, dead: bool(bit5 and can and not tgt and die and not dead)},
    {"status": lambda cur, want: want & 0xFFFF},
    {"status": lambda cur, want: ((cur & ~2) | (want & 2)) & 0xFF},
    {"masks": lambda wire, resolve: wire & 0xFFFF},
    {"decide": _decide_with(lever_before_knob=True)}, {"decide": _decide_with(rework_before_lever=True)},
    {"decide": _decide_with(backlog_before_lever=True)},
    {"cursor": lambda cur, snap, limited: ((cur & ~2) | (snap & 2)) & 0xFFFF},
    {"cursor": lambda cur, snap, limited: cur & 0xFFFF},
    {"disappear": lambda player, dead: not dead},
    {"disappear": lambda player, dead: True},
    {"preinject": lambda aborted, running: aborted},
    {"holdbreak": lambda holding, block, kind: bool(holding) and not kind},
    {"holdbreak": lambda holding, block, kind: bool(holding) and not block},
    {"sfx": lambda running, cur, cam, ended: BW.ACT_SFX_CANCEL if running == 0 else BW.ACT_SFX_KEEP},
    {"sfx": lambda running, cur, cam, ended: BW.ACT_SFX_CANCEL | (BW.ACT_SFX_UNLOCK if cur and cam and ended else 0)},
    {"sfx": lambda running, cur, cam, ended: 0 if running else BW.ACT_SFX_CANCEL | (BW.ACT_SFX_UNLOCK if cur and cam
                                                                                   else 0)}],
    ids=["decide-backlog-first", "decide-stale-before-knob", "decide-stale-before-leave", "decide-busy-gt",
         "decide-noop-first", "decide-busy-before-noop", "dead-no-dieseq", "dead-no-link", "dead-enemycounter",
         "stance-sys", "stance-transform", "motion-ignores-include", "book-park-not-stale", "book-running-stale",
         "book-duplicates", "book-key-no-shift", "book-no-supersede", "book-any-actor", "pending-gt",
         "transport-no-prev", "bench-no-edge", "bench-either-latch", "delta-counts-pause", "delta-one-paused",
         "abort-host-end-ge", "restore-full-after-inject", "hold-no-w3", "grace-no-caster", "status-every-bit",
         "status-high-byte", "masks-no-resolve", "decide-lever-before-knob", "decide-rework-before-lever",
         "decide-backlog-before-lever", "cursor-limited-too", "cursor-never", "disappear-dead-player-hidden",
         "disappear-always", "preinject-running-too", "holdbreak-no-stale", "holdbreak-no-move-on", "sfx-no-unlock",
         "sfx-playing-cancelled", "sfx-unlock-unloaded"])
def test_each_replay_rule_mutant_fails_a_selftest_row(twins):
    """A CHECK THAT CANNOT FAIL is no check: each rule of the decision, the book, the verdicts, the clock and the rules,
    broken alone in its twin, fails one of the engine's own rows."""
    _rep_program()                                                      # (its own parse outside the raises)
    with pytest.raises(AssertionError, match=r"^row ['\"]"):
        _run_rep_selftest(**twins)


def test_the_replay_twins_take_the_engines_parameters_in_its_order():
    """Each s134 twin's parameters ARE its C# method's, in order (camelCase -> snake_case; ``ref d`` is the ActDecideIn
    dict)."""
    for start, fn, fix in (
            ("internal static Int32 ActBattleDelta(", BW.act_battle_delta, {}),
            ("internal static Boolean ActBacklogTransport(", BW.act_backlog_transport, {}),
            ("internal static Boolean ActBacklogBench(", BW.act_backlog_bench, {}),
            ("internal static Int32 ActDecide(", BW.act_decide, {"ref d": "d"}),
            ("internal static Boolean ActDeadMayRun(", BW.act_dead_may_run, {}),
            ("internal static Boolean ActStanceGate(", BW.act_stance_gate, {}),
            ("internal static Boolean ActCmdMotionFilter(", BW.act_cmd_motion_filter, {}),
            ("internal static String ActAbortWhy(", BW.act_abort_why, {}),
            ("internal static Boolean ActPendingAbortDue(", BW.act_pending_abort_due, {}),
            ("internal static Int32 ActRestoreScope(", BW.act_restore_scope, {}),
            ("internal static Int32 ActEndHoldStep(", BW.act_end_hold_step, {}),
            ("internal static Boolean ActGraceArms(", BW.act_grace_arms, {}),
            ("internal static UInt16 ActCmdStatusFor(", BW.act_cmd_status_for, {}),
            ("internal static UInt16 ActMapMaskWith(", BW.act_map_mask_with, {}),
            ("internal static UInt16 ActCursorBitAfter(", BW.act_cursor_bit_after, {}),
            ("internal static Boolean ActRestoresDisappear(", BW.act_restores_disappear, {}),
            ("internal static Int32 ActPreInjectMask(", BW.act_pre_inject_mask, {}),
            ("internal static Boolean ActEndHoldBreaks(", BW.act_end_hold_breaks, {}),
            ("internal static Int32 ActSfxDropPlan(", BW.act_sfx_drop_plan, {})):
        cs = [fix.get(p, fix.get(_snake(p), _snake(p))) for p in _cs_signature(REPLAY_FILE, start)]
        assert cs == _twin_params(fn), (start, cs, _twin_params(fn))
    # ActDecideIn's fields, in the struct's order (the twin's dict keys)
    struct = " ".join(_cs_block(REPLAY_FILE, "internal struct ActDecideIn", "}"))
    fields = [f for decl in re.findall(r"public (?:Boolean|Int32) ([^;]+);", struct) for f in decl.replace(" ", "").split(",")]
    assert [_snake(f) for f in fields] == list(BW.ACT_DECIDE_FIELDS), fields


def _replay_int_consts() -> dict:
    """Every `internal const Int32` the s134 file declares (comments stripped: ActW3Ms's carries a `;`) -> its value."""
    out = {}
    for line in net_lines(REPLAY_FILE, r"internal const Int32 ", [_patch_bytes("s134")]):
        m = re.fullmatch(r"internal const Int32 (.*);", _strip_comment(line))
        assert m, line
        for decl in m.group(1).split(","):
            d = re.fullmatch(r"\s*(\w+) = (0x[0-9A-Fa-f]+|-?\d+)\s*", decl)
            assert d, decl
            out[d.group(1)] = int(d.group(2), 0)
    return out


def test_the_replay_constants_are_the_stacks_both_ways():
    """THE PIN: every CS_REPLAY_CONSTANTS entry is NetSyncDiorama.Replay.cs's constant of that name and value, and every
    `internal const Int32` the s134 file declares is in the table -- a constant added, renamed or retuned on either side
    turns this red. ActW3Ms (its comment carries a `;`) is read like every other."""
    cs = _replay_int_consts()
    assert cs == BW.CS_REPLAY_CONSTANTS, sorted(set(cs.items()) ^ set(BW.CS_REPLAY_CONSTANTS.items()))
    assert cs["ActW3Ms"] == BW.ACT_W3_MS == 4000 and cs["ActMaxRunning"] == 6
    assert len(BW.ACT_DECLINE_REASONS) == len(set(BW.ACT_DECLINE_REASONS))
    assert {BW.act_why_name(v) for k, v in BW.CS_REPLAY_CONSTANTS.items() if k.startswith("ActWhy")} <= \
        set(BW.ACT_DECLINE_REASONS)
    for why, name in BW.ACT_WHY_NAMES.items():                         # ActWhyName, case by case
        const = next(k for k, v in BW.CS_REPLAY_CONSTANTS.items() if v == why and (k.startswith("ActWhy") or k == "ActNoop"))
        assert _battle_text(f'case {const}: return "{name}";'), (const, name)
    for why, detail in BW.ACT_WHY_DETAILS.items():                     # ActWhyDetail's words (the busy one splices)
        const = next(k for k, v in BW.CS_REPLAY_CONSTANTS.items() if v == why and k.startswith("ActWhy"))
        if why == BW.ACT_WHY_BUSY:
            assert _battle_text(f'case {const}: return ActMaxRunning + " replays are already running";')
        else:
            assert _battle_text(f'case {const}: return "{detail}";'), const


def test_the_act_guest_block_sits_after_host_at_the_catch_lines_sentinels():
    """THE CATCH-LITERAL RE-PIN for s134: `act.guest` in AppendNetsync's SECOND catch literal, right after `act.host`'s
    close, at its sentinels; the line stays ONE line of two literals; AppendActGuest writes the keys in the catch line's
    order, each through its NetSyncDiorama getter (the `last` record's fields in ACT_GUEST_LAST_KEYS' order); AppendAct
    closes `host` and calls it; published in every role; protocol stays 5."""
    catch = net_lines("HarnessAgent.cs", r'outer\.Append\("\\"netsync\\":\{\\"enabled')
    assert len(catch) == 1 and catch[0].count(".Append(") == 3 and ".Append(NetsyncF3Retired)" in catch[0], catch
    a, b = _literals(catch[0])
    assert '\\"page\\":null}},\\"guest\\":{\\"on\\":false,' in b and "guest" not in a.split("diorama")[0]
    nothing = _agent_netsync_nothing()[0]
    assert _battle_of(nothing)["act"] == {"host": BW.ACT_HOST_SENTINELS, "guest": BW.ACT_GUEST_SENTINELS}
    # s134 wrote the catch line whole; [ff9mapkit netsync s135] s135 added `act.guest.hold` (after `last`) and nothing else;
    # [ff9mapkit netsync s136] s136 `act.guest.fallback` (the last key) and nothing else
    s134_guest = {k: v for k, v in BW.ACT_GUEST_SENTINELS.items() if k not in ("hold", "fallback")}
    assert _catch_doc_in("s134") == {**nothing, "battle": {**nothing["battle"], "act": {
        "host": BW.ACT_HOST_SENTINELS, "guest": s134_guest}}}
    new = [t for _h, _k, t in _new_side("HarnessAgent.cs", _patch_bytes("s134"))]
    i = next(k for k, t in enumerate(new) if t.startswith("private static void AppendActGuest("))
    j = next(k for k in range(i, len(new)) if new[k].startswith("// [ff9mapkit netsync B5] stage 5:"))
    body = " ".join(_strip_comment(t) for t in new[i:j])
    names = re.findall(r'(?:Bool|Num|Str)\(sb, "(\w+)"', body)
    g = s134_guest                                                      # (`hold` / `fallback`: their own tests)
    want = []
    for k, v in g.items():
        if k == "last":
            want += list(BW.ACT_GUEST_LAST_KEYS)
        elif isinstance(v, dict):
            want += list(v)
        else:
            want.append(k)
    assert names == want, (names, want)
    for k in [k for k in g if not isinstance(g[k], dict) and k != "last"]:
        assert re.search(rf'(?:Bool|Num|Str)\(sb, "{k}", Memoria\.Netsync\.NetSyncDiorama\.HarnessAct\w+\)', body), k
    assert _added_after("s134", "HarnessAgent.cs", 'sb.Append("}},");', "AppendActGuest(sb);")
    assert net_lines("HarnessAgent.cs", r"public const Int32 ProtocolVersion = ") == ["public const Int32 ProtocolVersion = 5;"]
    assert not _battle_text("IsSelfTestRole ? _act")                     # audit 3.6: published in EVERY role
    assert _battle_text("internal static Boolean HarnessActGuestOn { get { return ActCanReplay; } }")
    assert _battle_text("internal static Int32 HarnessActBattleMs { get { return _booted ? _actNowMs : -1; } }")


def test_state_reads_the_act_guest_block_absent_on_s133_as_cannot():
    """On s133's catch block (s134's calibration red) every `act.guest` accessor reads None and `coop_act_guest` False; on
    the live block they read the sentinels and True; a published block reads its values, a mistyped one None, `last`
    None at null, and the unit accessors read the seven keys (None without them)."""
    old = State({"frame": 1, "netsync": _catch_doc_in("s133")})
    live = State({"frame": 1, "netsync": _agent_netsync_nothing()[0]})
    # ([ff9mapkit netsync s135] `act.guest.hold` is s135's, [ff9mapkit netsync s136] `act.guest.fallback` s136's: their own
    # tests below)
    names = [n for p, n in State.NETSYNC_BATTLE_ACCESSORS.items()
             if p.startswith("act.guest") and p.split(".")[2:3] not in (["hold"], ["fallback"])]
    s134_guest = {k: v for k, v in BW.ACT_GUEST_SENTINELS.items() if k not in ("hold", "fallback")}
    assert len(names) == len(_leaves({"act": {"guest": s134_guest}})) + 6 == 63, names   # + 6 whole blocks
    assert (State({"frame": 1}).coop_act_guest, old.coop_act_guest, live.coop_act_guest) == (None, False, True)
    assert old.coop_act_host is True                                    # (s133's own block is there)
    assert all(getattr(old, n) is None for n in names)
    assert all(getattr(live, n) is not None for p, n in State.NETSYNC_BATTLE_ACCESSORS.items()
               if p.startswith("act.guest") and p not in BATTLE_NULLABLE)
    assert (live.coop_act_guest_last, live.coop_act_guest_why, live.coop_act_guest_rx_dropped) == (None, "", -1)
    doc = _agent_netsync_nothing()[0]
    doc["battle"]["act"]["guest"].update(started=3, running=True, declined_why="stale",
                                         last={"id": 7, "state": "running", "first_hit_ms": 412})
    st = State({"frame": 1, "netsync": doc})
    assert (st.coop_act_guest_started, st.coop_act_guest_running, st.coop_act_guest_declined_why) == (3, None, "stale")
    got = st.coop_act_guest_last
    got["id"] = 0
    assert st.coop_act_guest_last["id"] == 7                            # a copy
    unit = State({"frame": 1, "battle": {"units": [
        {"slot": 0, "anim": "ANH_MAIN_B0_011", "anim_frame": 4, "away": 512.5, "rot_y": 180, "acting": True, "die_seq": 0,
         "row": 1}, {"slot": 4, "anim": None, "acting": 1}]}})
    assert (unit.unit_anim(0), unit.unit_anim_frame(0), unit.unit_away(0), unit.unit_rot_y(0), unit.unit_acting(0),
            unit.unit_die_seq(0), unit.unit_row(0)) == ("ANH_MAIN_B0_011", 4, 512.5, 180.0, True, 0, 1)
    assert (unit.unit_anim(4), unit.unit_acting(4), unit.unit_away(4), unit.unit_anim(2)) == ("", None, None, None)


def test_a_fresh_stand_in_publishes_the_act_guest_block_and_s133_none(game):
    """The default stand-in (s134) publishes `act.guest` at the agent's sentinels with no client -- but `on` / `rework`
    / `knob` the live reads at rest (true / true / 1); the stand-in at s133 publishes no `act.guest`, no 'action replay'
    proof line, and answers the guest forms in s133's words."""
    want = dict(BW.ACT_GUEST_SENTINELS, on=True, rework=True, knob=1,       # ([ff9mapkit netsync s135] + `hold`, its two
                hold=dict(BW.ACT_GUEST_HOLD_SENTINELS, on=True, lifeskip=True),   # levers the live reads at rest;
                fallback=dict(BW.ACT_GUEST_FALLBACK_SENTINELS, on=True))   # [ff9mapkit netsync s136] + `fallback`, its lever)
    assert _battle_of(FakeGame(game)._netsync_doc())["act"]["guest"] == want
    old = _selftest(FakeGame(game))
    old.netsync_caps = S133_CAPS
    assert list(_battle_of(old._netsync_doc())["act"]) == ["host"]
    assert set(_leaves(_battle_of(old._netsync_doc()))) == set(_leaves(_battle_of(_catch_doc_in("s133"))))
    start = BW.act_feed_arg([_rep_start(1)])
    for args, words in ((["actbench", "feed", start], "netsync actbench: unknown op 'feed' (tape|hoststarts)"),
                        (["actbench", "replay", "off"], "netsync actbench: unknown op 'replay' (tape|hoststarts)"),
                        (["actbench", "tape", "play"], "netsync actbench tape: expected `tape rec|stop|clear|info` or "
                                                       "`tape dump <from> <count>`"),
                        (["actbench", "clear"], f"{FG.NETSYNC_ACTBENCH_USAGE_S133}\r\nParameter name: netsync actbench"),
                        (["actbench", "feedat", "10", start],
                         f"{FG.NETSYNC_ACTBENCH_USAGE_S133}\r\nParameter name: netsync actbench")):
        with pytest.raises(RuntimeError) as err:
            old._netsync(args)
        assert str(err.value) == words, args


@pytest.mark.parametrize("level", ["s133", "s134"])
def test_the_stand_ins_units_grow_the_replay_keys_after_z_at_s134(game, level):
    """`battle.units[]` gains `anim`, `anim_frame`, `away`, `rot_y`, `acting`, `die_seq`, `row` at s134 -- after s115's
    `z`, before `status` (AppendBattleUnits; audit amendment 18), each line read off s134's patch, in that order; the
    stand-in publishes them exactly from s134 on."""
    s134 = [t for _h, _k, t in _new_side("HarnessAgent.cs", _patch_bytes("s134"))]
    z = s134.index('Num(sb, "z", Try(() => unit.Data.pos.z, Single.NaN)); sb.Append(",");')
    keys = [re.match(r'(?:Num|Str|Bool)\(sb, "(\w+)", Try\(\(\) => ', t) for t in s134[z + 1:z + 30]]
    keys = [m.group(1) for m in keys if m]
    assert keys[:len(BW.UNIT_ACT_KEYS) + 1] == list(BW.UNIT_ACT_KEYS) + ["status"], keys
    fake = _dio_fake(FakeGame(game))
    fake.netsync_caps = S133_CAPS if level == "s133" else fake.netsync_caps
    unit = fake._battle_doc()["units"][0]
    tail = list(unit)[list(unit).index("cmd_busy") + 1:]
    assert tail == ["mot", "disappear", "z"] + (list(BW.UNIT_ACT_KEYS) if level == "s134" else []) + ["status"], tail


def _rep_start(act_id: int, *, actor: int = 0, player: bool = True, cmd: int = BW.CMD_ATTACK_ID,
               sub: int = BW.ABILITY_ATTACK_ID, tar: int = 0x10, kind: int = BW.VFX_KIND_SPECIAL, num: int = 100,
               nonce: int = 0x77) -> bytes:
    """A bench START (s133's 76-byte record): by default Zidane's (wire 0) Attack on the enemy in wire slot 4."""
    flags = (BW.ACTOR_IS_PLAYER if player else 0) | BW.ACTOR_HOST_REWORK
    return BW.encode_action_start(nonce, 1, act_id, actor, flags, cmd, sub, tar, 0, 0, 0, kind, num, -1, 5)


ACT_GUEST_REFUSALS = [
    # (a fragment the agent says -- ONE C# literal of the stack, or a piece --, the args, where: None / selftest / dio)
    ("netsync actbench: needs the selftest role (netsync selftest 1)", ["actbench", "feed", "00" * 46], None),
    ("netsync actbench feed: expected `feed <hex[,hex...]>`", ["actbench", "feed"], "selftest"),
    ("netsync actbench feedat: expected `feedat <ms 0-600000> <hex[,hex...]>`", ["actbench", "feedat", "600001", "00" * 46],
     "selftest"),
    (": needs a booted battle diorama (`netsync dioboot <scene>`)", ["actbench", "feed", "00" * 46], "selftest"),
    ("netsync actbench feed: each frame is an even run of 92-8192 hex digits (46-4096 bytes)", ["actbench", "feed", "00"],
     "dio"),
    ("netsync actbench feed: '", ["actbench", "feed", "zz" * 46], "dio"),
    ("' is not hex", ["actbench", "feed", "zz" * 46], "dio"),
    ("netsync actbench tape play: expected `tape play [pct 1-1000]`", ["actbench", "tape", "play", "0"], "selftest"),
    ("netsync actbench tape play: needs a booted battle diorama (`netsync dioboot <scene>`)", ["actbench", "tape", "play"],
     "selftest"),
    ("netsync actbench tape play: the tape is empty (`actbench tape rec` during an own battle first)",
     ["actbench", "tape", "play", "50"], "dio"),
    (": expected `", ["actbench", "shortcircuit", "maybe"], "selftest"),
    (" on|off`", ["actbench", "rework"], "selftest"),
    ("netsync actbench knob: expected `knob 0|1|ini`", ["actbench", "knob", "2"], "selftest"),
    (": takes no argument", ["actbench", "teardown", "now"], "selftest"),
    (": needs a booted battle diorama", ["actbench", "clear"], "selftest"),
    (": the bench inbox holds at most ", ["actbench", "feed", ",".join(["00" * 46] * (BW.ACT_INBOX_CAP + 1))], "dio"),
]


@pytest.mark.parametrize("fragment,args,where", ACT_GUEST_REFUSALS,
                         ids=[f"{r[0][:36]}-{i}" for i, r in enumerate(ACT_GUEST_REFUSALS)])
def test_the_stand_in_refuses_the_guest_actbench_ops_in_the_agents_words(game, fragment, args, where):
    """Every guest `actbench` gate the stand-in models refuses with the engine's own words (each fragment a literal of
    the stack: HarnessActGuestBench / ActParseHexFrames)."""
    assert _battle_text(fragment), f"the live stack no longer says {fragment!r}"
    fake = FakeGame(game)
    if where == "selftest":
        _selftest(fake)
    elif where == "dio":
        _dio_fake(fake)
    with pytest.raises(RuntimeError) as err:
        fake._netsync(args)
    assert fragment in str(err.value), str(err.value)


def test_the_guest_ops_are_the_agents_and_the_driver_gates_them_by_act_guest(game):
    """The guest ops are IsActGuestBenchOp's (case by case) and HarnessActGuestBench's; the driver keys each on
    `act.guest` (s134), refuses a malformed form before the step in HarnessActGuestBench's words, and on an s133 engine
    refuses every guest form naming s134 and what s133 would answer (its usage, its unknown op, its `tape` refusal)."""
    body = " ".join(_cs_block(REPLAY_FILE, "internal static Boolean IsActGuestBenchOp(", "}"))
    cases = re.findall(r'case "(\w+)":', " ".join(_cs_block(REPLAY_FILE, "internal static Boolean IsActGuestBenchOp(",
                                                           "default:")))
    assert tuple(c for c in cases if c != "tape") == BW.ACT_GUEST_BENCH_OPS and "tape" in cases, (cases, body)
    assert _battle_text('return value == "play";')
    assert _added_after("s134", "HarnessAgent.cs", 'String aval = s.Args.Length > 2 ? s.Args[2].ToLowerInvariant() : "";',
                        "if (Memoria.Netsync.NetSyncDiorama.IsActGuestBenchOp(aop, aval))")
    for op, (attr, key, patch, _what) in Session.NETSYNC_ACTBENCH_OP_CAPS.items():
        if op in BW.ACT_HOLD_BENCH_OPS + BW.ACT_FALLBACK_BENCH_OPS:     # (the hold's / fallback's: their own tests)
            continue
        assert (attr, key, patch) == ("coop_act_guest", "netsync.battle.act.guest", "s134"), op
    for op, words in Session.NETSYNC_ACTBENCH_GUEST_USAGE.items():
        assert _battle_text(words) or (op in ("replay", "rework", "shortcircuit") and _battle_text(": expected `")) \
            or (op in ("clear", "teardown") and _battle_text(": takes no argument")), (op, words)
    fake = FakeGame(game)
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.netsync("selftest", 1)
        n = len(fake.executed)
        for args in (("feed",), ("feedat", "x", "00"), ("feedat", "600001", "00"), ("tape", "play", "0"),
                     ("tape", "play", "5", "6"), ("replay", "maybe"), ("rework",), ("shortcircuit", "on", "x"),
                     ("knob", "2"), ("clear", "x"), ("teardown", "now")):
            with pytest.raises(HarnessError) as err:
                g.netsync("actbench", *args)
            with pytest.raises(RuntimeError) as agent:
                fake._netsync(["actbench", *args])
            assert str(err.value) == str(agent.value), (args, str(err.value), str(agent.value))
        assert len(fake.executed) == n
        st = g.actbench("replay", "off")                                # a well-made form goes to the engine
        assert st.coop_act_guest_lever_replay_off is True and st.coop_act_guest_why == "lever"
        g.actbench("replay", "on")
        # (audit 4.3) the two `clear`s stay distinct: `tape clear` is s133's value, top-level `clear` the guest op
        g.actbench("tape", "rec")
        st = g.actbench("tape", "clear")
        assert st.coop_act_host_tape_state == "off" and fake.executed[-1] == ["netsync", "actbench", "tape", "clear"]
        with pytest.raises(HarnessError, match=r"netsync actbench clear: needs a booted battle diorama \(steps="):
            g.actbench("clear")                                         # (the guest op, sent: the AGENT refuses it)
    fake = FakeGame(game)
    fake.netsync_caps = S133_CAPS
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.netsync("selftest", 1)
        n = len(fake.executed)
        start = BW.act_feed_arg([_rep_start(1)])
        for args in (("feed", start), ("clear",), ("tape", "play"), ("knob", "0"), ("feedat", "10", start)):
            with pytest.raises(HarnessError) as err:
                g.netsync("actbench", *args)
            with pytest.raises(RuntimeError) as agent:
                fake._netsync(["actbench", *args])
            form = f"{args[0]} {args[1]}" if args[0] == "tape" else args[0]
            assert str(err.value).startswith(f"netsync actbench {form}: the deployed engine publishes no "
                                             f"`netsync.battle.act.guest`"), str(err.value)
            assert f"(memoria-patch s134); it would answer \"{agent.value}\" only after the step" in str(err.value), \
                (args, str(err.value), str(agent.value))
        assert len(fake.executed) == n and g.state.coop_act_guest is False


def _rep_dio(game, *, caps=None, intro: int = 0):
    """A stand-in + session in a steady selftest diorama (scene 67: Zidane wire 0, the enemy in wire slot 4 / id 0x10)."""
    fake = FakeGame(game)
    if caps is not None:
        fake.netsync_caps = caps
    fake.battle_intro_frames = intro
    return fake


def _rep_until(g, pred, what: str, timeout: float = 6.0):
    return g.wait_for(pred, timeout=timeout, what=what)


def test_a_fed_start_replays_as_presentation_only_and_ends(game):
    """The stand-in's model of the s134 guest: a START fed into a steady selftest diorama registers, launches (ActDecide
    go), ACTS (its actor's `acting`, `anim` off idle, `away` up and back), hits its mapped target once (hits / credits),
    ENDS naturally -- `last.state` "ended", running 0, the book's identity, the TRIPWIRE 0, no HP touched -- and the
    'started id' line lands; a second START of the same actor while it runs PARKS (waiting) and a third SUPERSEDES it.
    The park is the STAND-IN'S SHAPE of the engine rule (ActGuestLane._motion_holder: any running replay of the actor holds
    it -- the engine parks only while the replay still holds its command motion, released at its sequence's Anim Idle);
    the supersede rule itself (one pending START per actor) is the engine's, pinned by ActReplaySelfTest's pending rows."""
    fake = _rep_dio(game)
    with session(game, fake) as g:
        st = _dio(g, fake)
        hp = [(u["slot"], u["hp_raw"]) for u in st.units()]
        st = g.act_feed(_rep_start(1))
        assert st.coop_act_guest_inbox in (0, 1)
        st = _rep_until(g, lambda s: s.coop_act_guest_running == 1 and s.unit_acting(0), "the replay acting")
        assert st.coop_act_guest_started == 1 and st.unit_anim(0).startswith("ACT_3_100") and not st.unit_acting(4)
        peak = _rep_until(g, lambda s: (s.unit_away(0) or 0) > 300, "the run out").unit_away(0)
        st = _rep_until(g, lambda s: s.coop_act_guest_ended == 1, "the natural end")
        assert (st.coop_act_guest_hits, st.coop_act_guest_credits, st.coop_act_guest_running) == (1, 1, 0)
        assert st.coop_act_guest_last["state"] == "ended" and st.coop_act_guest_last["first_hit_ms"] >= 0 and peak > 300
        assert st.unit_away(0) == 0 and st.unit_anim(0) == "IDLE" and st.coop_act_guest_calc_while_booted == 0
        assert BW.act_guest_invariant(st.coop_act_guest_block)
        assert [(u["slot"], u["hp_raw"]) for u in st.units()] == hp       # presentation only
        g.act_feed(_rep_start(2))
        _rep_until(g, lambda s: s.coop_act_guest_running == 1, "the second replay")
        g.act_feed(_rep_start(3))
        st = _rep_until(g, lambda s: s.coop_act_guest_waiting == 1, "the third START parked")
        g.act_feed(_rep_start(4))
        st = _rep_until(g, lambda s: s.coop_act_guest_superseded == 1, "the fourth START superseding the third")
        assert st.coop_act_guest_declined_why == "superseded" and st.coop_act_guest_waiting == 1
        st = _rep_until(g, lambda s: s.coop_act_guest_started == 3 and s.coop_act_guest_running == 0, "both ended")
        assert BW.act_guest_invariant(st.coop_act_guest_block) and st.coop_act_guest_ended == 3
    assert _mlog_lines(fake, BW.LOG_REPLAY_STARTED) and _mlog_lines(fake, "declined superseded -- id 3")


@pytest.mark.parametrize("lever,args,why", [("replay", ("replay", "off"), "lever"), ("rework", ("rework", "off"), "rework"),
                                           ("knob", ("knob", "0"), "knob")])
def test_each_replay_lever_declines_its_reason_and_releases(game, lever, args, why):
    """The calibration levers, each alone: `replay off` -> every START declines `lever` (the pre-s134 guest), `rework off`
    -> `rework`, `knob 0` -> `knob` (Memoria.ini untouched); each logged, `on` / `why` say so, and back on a START
    launches again."""
    fake = _rep_dio(game)
    with session(game, fake) as g:
        _dio(g, fake)
        st = g.actbench(*args)
        assert st.coop_act_guest_on is False and st.coop_act_guest_why == why
        st = g.act_feed(_rep_start(1))
        st = _rep_until(g, lambda s: s.coop_act_guest_declined == 1, f"the {why} decline")
        assert st.coop_act_guest_declined_why == why and st.coop_act_guest_started == 0 and not st.unit_acting(0)
        g.actbench(args[0], "ini" if lever == "knob" else "on")
        g.act_feed(_rep_start(2))
        st = _rep_until(g, lambda s: s.coop_act_guest_started == 1, "a launch after the lever")
    words = {"replay": BW.LOG_REPLAY_OFF, "rework": BW.LOG_REPLAY_REWORK_OFF, "knob": BW.LOG_REPLAY_KNOB + "0 for this "
             "process (Memoria.ini untouched)"}[lever]
    assert _mlog_lines(fake, words) and _mlog_lines(fake, f"declined {why} -- id 1")


def test_a_start_and_its_end_in_one_feed_is_stale_and_a_boot_backlog_declines(game):
    """THE TWO-STEP DRAIN (audit amendment 4): a START and its END in ONE feed -> the record turns stale before ActTick
    decides -> declined `stale` (stale 1, started 0). THE BOOT BACKLOG (amendment 5): a START fed during the boot's intro
    is drained on the first steady frame, before the steady latch -> declined `backlog`."""
    fake = _rep_dio(game)
    with session(game, fake) as g:
        _dio(g, fake)
        st = g.act_feed([_rep_start(1), BW.encode_action_end(0x77, 2, 1, BW.CMD_ATTACK_ID, BW.ABILITY_ATTACK_ID)])
        st = _rep_until(g, lambda s: s.coop_act_guest_stale == 1, "the stale decline")
        assert (st.coop_act_guest_started, st.coop_act_guest_ends_rx, st.coop_act_guest_declined_why) == (0, 1, "stale")
    fake = _rep_dio(game, intro=90)
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(FIELD)
        g.netsync("selftest", 1)
        fake.player, fake.control = [10.0, 0.0, 20.0], True
        g.netsync("dioboot", 67)
        st = g.act_feed(_rep_start(1))
        assert st.battle_phase != BW.PHASE_NORMAL, "fed after the intro: no backlog to see"
        st = _rep_until(g, lambda s: s.coop_act_guest_declined == 1, "the backlog decline")
        assert st.coop_act_guest_backlog == 1 and st.coop_act_guest_declined_why == "backlog"


def test_shortcircuit_off_reds_the_tripwire_and_clear_and_teardown_drop_replays(game):
    """`shortcircuit off` (one-shot): the NEXT replay's hit falls through -> calc_while_booted 1, the TRIPWIRE line, the
    CALIBRATION line; the lever re-reads off. `clear` aborts a running replay (`clear`, the window's full restore);
    `teardown` discards one (ActDiscardAll, nothing restored, nothing counted aborted); a noop START (kind none) declines
    `noop`."""
    fake = _rep_dio(game)
    with session(game, fake) as g:
        _dio(g, fake)
        g.actbench("shortcircuit", "off")
        g.act_feed(_rep_start(1))
        st = _rep_until(g, lambda s: s.coop_act_guest_ended == 1, "the fall-through replay's end")
        assert st.coop_act_guest_calc_while_booted == 1 and st.coop_act_guest_lever_shortcircuit_off is False
        g.act_feed(_rep_start(2))
        _rep_until(g, lambda s: s.coop_act_guest_running == 1, "a replay to clear")
        st = g.actbench("clear")
        st = _rep_until(g, lambda s: s.coop_act_guest_aborted == 1, "the clear")
        assert st.coop_act_guest_abort_why == "clear" and st.coop_act_guest_window_restores == 1
        g.act_feed(_rep_start(3))
        _rep_until(g, lambda s: s.coop_act_guest_running == 1, "a replay to tear down")
        st = g.actbench("teardown")
        st = _rep_until(g, lambda s: s.coop_act_guest_running == 0, "the teardown")
        assert st.coop_act_guest_aborted == 1 and not st.unit_acting(0)
        g.act_feed(_rep_start(4, kind=BW.VFX_KIND_NONE, num=0))
        st = _rep_until(g, lambda s: s.coop_act_guest_noop == 1, "the noop")
        assert st.coop_act_guest_declined_why == "noop"
    for line in (BW.LOG_REPLAY_TRIPWIRE, BW.LOG_REPLAY_NO_SHORT, BW.LOG_REPLAY_SHORT_OFF, BW.LOG_REPLAY_CLEARED,
                 BW.LOG_REPLAY_DISCARD + "teardown (bench)) -- 1 running replay(s)", BW.LOG_REPLAY_WINDOW,
                 BW.LOG_REPLAY_NOOP):
        assert _mlog_lines(fake, line), line


@pytest.mark.parametrize("level", ["s135", "s136"])
def test_a_paired_impact_skips_the_swing_and_an_old_hosts_impact_swings(game, level):
    """ApplyActionFrame's s134 half: an impact naming a running replay's id pairs (`paired` 1) and its player swing is
    SKIPPED (`swing_skipped` 1: the replay is the clip); a 46-byte impact (no 0xA6 extension) is an old host's -- `old_host`
    true, the line once, and the legacy MP_ATTACK swing shows on the caster. [ff9mapkit netsync s136] The old host's impact
    is fed once the replay ENDED: from s136 its Attack plays fallback A's attack clip (MP_ATTACK too, keyed by caster) --
    and while its caster still ACTS in a replay fallback A refuses it (`guarded`: a clip would cut the replay's own),
    where the s110 swing (s135) played over the replay."""
    fake = _rep_dio(game, caps=S135_CAPS if level == "s135" else None)
    with session(game, fake) as g:
        _dio(g, fake)
        g.act_feed(_rep_start(1))
        _rep_until(g, lambda s: s.coop_act_guest_running == 1, "the replay")
        impact = BW.encode_action_impact(0x77, 3, 0, 4, fig_t=(0, 4321, 0), raws=(11200, 0, 420, 30),
                                         flags=1 | 64, cmd_no=1, sub_no=176, act_id=1)
        st = g.act_feed(impact)
        st = _rep_until(g, lambda s: s.coop_act_guest_paired == 1, "the pairing")
        assert st.coop_act_guest_swing_skipped == 1 and st.coop_act_guest_old_host is False
        old = BW.encode_action_impact(0x77, 4, 0, 4, fig_t=(0, 4321, 0), raws=(11200, 0, 420, 30), flags=1 | 64,
                                      cmd_no=1, sub_no=176)
        st = g.act_feed(old)                                            # (the caster acts: s135 swings, s136 guards)
        st = _rep_until(g, lambda s: s.coop_act_guest_old_host is True, "the old host's frame")
        if level == "s136":
            assert st.coop_act_fallback_guarded == 1 and st.coop_act_fallback_clips == 0
        _rep_until(g, lambda s: s.coop_act_guest_running == 0 and s.unit_mot(0) != BW.MP_ATTACK, "the replay's end")
        g.act_feed(BW.encode_action_impact(0x77, 5, 0, 4, fig_t=(0, 4321, 0), raws=(11200, 0, 420, 30), flags=1 | 64,
                                           cmd_no=1, sub_no=176))
        st = _rep_until(g, lambda s: s.unit_mot(0) == BW.MP_ATTACK, "the old host's legacy swing")
        assert st.coop_act_guest_swing_skipped == 1
        if level == "s136":
            assert st.coop_act_fallback_clips == 1 and st.coop_act_fallback_last["keyed_by"] == "caster"
        else:
            assert st.coop_act_fallback is False
    assert len(_mlog_lines(fake, BW.LOG_REPLAY_OLD_HOST)) == 1


def test_feedat_and_tape_play_ride_the_battle_clock_and_a_pause_launches_nothing(game):
    """`feedat <ms>` is due after that much BATTLE time; while paused nothing launches and the clock skips the span
    (`paused_ms` grows, `battle_ms` does not); `tape play` puts s133's own loopback tape into the inbox at its offsets --
    every taped START received."""
    fake = _rep_dio(game)
    with session(game, fake) as g:
        st = _dio(g, fake)
        t0 = g.state.coop_act_guest_battle_ms
        g.act_feed(_rep_start(1), at_ms=500)
        st = _rep_until(g, lambda s: s.coop_act_guest_starts_rx == 1, "the feedat frame due")
        assert st.coop_act_guest_battle_ms - t0 >= 500
        fake.battle_paused = True
        g.act_feed(_rep_start(2, actor=1))
        g.wait_frames(40)
        st = g.state
        assert st.coop_act_guest_paused_ms > 0 and st.coop_act_guest_started <= 1 and not st.unit_acting(1)
        frozen = st.coop_act_guest_battle_ms
        g.wait_frames(10)
        assert g.state.coop_act_guest_battle_ms == frozen
        fake.battle_paused = False
        st = _rep_until(g, lambda s: s.coop_act_guest_started == 2, "the launch after the unpause")
    fake = FakeGame(game)
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(FIELD)
        g.netsync("selftest", 1)
        g.actbench("tape", "rec")
        _act_own(g, fake)
        g.battle_command(g.wait_turn(), 1, sub=176, target=16)
        g.wait_for(lambda s: (s.coop_act_host_ends or 0) >= 1, timeout=8.0, what="a command ENDed")
        fake.atb_gain = 0
        g.wait_frames(10)
        st = g.actbench("tape", "stop")
        starts = st.coop_act_host_tape_starts
        fake.end_battle(1)
        g.wait_for(lambda s: s.coop_host_caps == -1, timeout=4.0, what="the falling edge")
        fake.battle_intro_frames = 0
        _dio(g, fake, fresh=False)
        st = g.act_tape_play(200)
        st = _rep_until(g, lambda s: s.coop_act_guest_starts_rx == starts and s.coop_act_guest_inbox == 0,
                        "the whole tape drained")
        assert starts >= 1 and st.coop_act_guest_paired >= 1
    assert _mlog_lines(fake, "plays into the inbox at 200% speed")


def test_a_leave_aborts_a_running_replay_and_the_next_boot_starts_clean(game):
    """LeaveFrom past its fade check runs ActAbortAll("leave") (aborted 1, `leave`), ForceDisarm's ActDiscardAll drops
    what is left, and the next boot reads every per-boot counter at rest (the levers are harness-scoped)."""
    fake = _rep_dio(game)
    with session(game, fake) as g:
        _dio(g, fake)
        g.act_feed(_rep_start(1))
        _rep_until(g, lambda s: s.coop_act_guest_running == 1, "the replay")
        g.netsync("dioleave")
        st = _rep_until(g, lambda s: s.coop_act_guest_aborted == 1, "the leave's abort")
        assert st.coop_act_guest_abort_why == "leave"
        _rep_until(g, lambda s: not (s.diorama or {}).get("booted"), "the teardown", timeout=10.0)
        st = _dio(g, fake, fresh=False)
        assert (st.coop_act_guest_aborted, st.coop_act_guest_starts_rx, st.coop_act_guest_last) == (0, 0, None)


def test_reset_releases_every_replay_lever_and_the_inbox(game):
    """HarnessReleaseBench's s134 half (audit 4.5): `replay off`, `rework off`, `shortcircuit off`, `knob 0` and an inbox
    frame left set -- with s133's `hoststarts off` and a recording tape -- then `reset`: the 'levers back' line once, the
    inbox emptied (by the release, or -- the harness's diorama leaving first -- by the teardown's ActDiscardAll, which names
    it), and re-read WITH a fresh selftest role every lever at rest."""
    fake = _rep_dio(game, intro=200)
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(FIELD)
        g.netsync("selftest", 1)
        for args in (("replay", "off"), ("rework", "off"), ("shortcircuit", "off"), ("knob", "0"), ("hoststarts", "off"),
                     ("tape", "rec")):
            g.actbench(*args)
        fake.player, fake.control = [10.0, 0.0, 20.0], True
        g.netsync("dioboot", 67)
        st = g.act_feed(_rep_start(1), at_ms=600000)
        assert st.coop_act_guest_inbox == 1 and st.coop_act_guest_levers == {"replay_off": True, "rework_off": True,
                                                                             "shortcircuit_off": True, "knob": 0}
        g.send("reset")
        g.wait_for(lambda s: s.netsync is not None and not s.netsync["forced"] and not (s.diorama or {}).get("booted"),
                   timeout=10.0, what="the release")
        st = g.netsync("selftest", 1)
        assert st.coop_act_guest_levers == {"replay_off": False, "rework_off": False, "shortcircuit_off": False, "knob": -1}
        assert (st.coop_act_guest_on, st.coop_act_guest_inbox, st.coop_act_host_lever_off) == (True, 0, False)
    assert len(_mlog_lines(fake, BW.LOG_REPLAY_LEVERS_BACK)) == 1
    assert len(_mlog_lines(fake, BW.LOG_REPLAY_INBOX_EMPTIED)) + len(
        _mlog_lines(fake, "parked START(s) and 1 inbox frame(s) dropped")) == 1


def _lane_units() -> list:
    """Eight units, one per wire slot: players in btl slots 0-3, enemies in 4-7 (ids 1 << slot)."""
    return [{"slot": s, "id": 1 << s, "player": s < 4, "alive": True} for s in range(8)]


class _LaneRig:
    """A battlewire.ActGuestLane driven off the game: its bench feed and the stand-in's tick order (drain, then tick)."""

    def __init__(self, units=None, frames: int = 10 ** 6):
        self.lane = BW.ActGuestLane()
        self.lane.REPLAY_FRAMES = frames
        self.units = units if units is not None else _lane_units()
        self.ms = 0

    def ctx(self, **kw) -> dict:
        c = {"booted": True, "role": True, "steady": True, "normal_latched": True, "live_latched": False, "paused": False,
             "now_ms": self.ms, "wall_ms": self.ms, "end_injected": False, "r8_hits": 0, "end_presented": False,
             "leaving": False, "hidden_mask": 0, "units": self.units,
             "resolve": lambda i, p: next((u for u in self.units if u["slot"] == i and u["player"] == p), None),
             "linked": lambda u: any(u is x for x in self.units)}
        c.update(kw)
        return c

    def step(self, n: int = 1, **kw) -> None:
        for _ in range(n):
            self.ms += 33
            self.lane.drain_bench(self.ctx(**kw))
            self.lane.tick(self.ctx(**kw))

    def feed(self, *frames) -> None:
        ok, why = self.lane.bench(["actbench", "feed", BW.act_feed_arg(frames)], booted=True, role=True)
        assert ok, why


def test_the_replay_lane_model_holds_the_engines_rules_off_the_game():
    """battlewire.ActGuestLane on the rules no stand-in battle reaches: the host's END + 6 s abort (battle time) and its
    full restore, a pending START's 1500 ms hard abort of its actor's replay, the 6 s parked timeout (no steady frame), an
    unknown actor, an unmapped target, a duplicate id, the running cap (`busy`), the R8 abort after an injection (the
    LIMITED restore), the 90 s WALL cap, the bit-5 latch (never cleared by a null view; reset per boot) and ActDiscardAll
    keeping the counters."""
    rig = _LaneRig()
    lane = rig.lane
    rig.step()
    rig.feed(_rep_start(1))
    rig.step()
    assert lane.started == 1 and lane.running
    rig.feed(BW.encode_action_end(0x77, 2, 1, BW.CMD_ATTACK_ID, BW.ABILITY_ATTACK_ID))
    rig.step(2)
    assert lane.running and lane.running[0].host_ended and lane.ends_rx == 1
    rig.step(BW.ACT_HOST_END_ABORT_MS // 33 + 2)
    assert (lane.aborted, lane.abort_why, lane.restores, lane.running) == (1, "host-end", 1, [])
    rig.feed(_rep_start(2))
    rig.step()
    rig.feed(_rep_start(3))                                              # the same actor: it parks behind replay 2
    rig.step()
    assert lane.book.queue and lane.book.queue[0].state == BW.ACT_ST_WAITING
    rig.step(BW.ACT_PENDING_ABORT_MS // 33 + 2)
    assert lane.abort_why == "pending" and lane.started == 3 and [r.id for r in lane.running] == [3]
    rig.feed(_rep_start(4))                                              # parks behind 3 -- and no steady frame comes
    rig.step()
    rig.step(BW.ACT_WAIT_MAX_MS // 33 + 2, steady=False)
    assert lane.declined_why == "timeout" and [r.id for r in lane.running] == [3]
    lane.abort_all("clear", ctx=rig.ctx())
    for start, why in ((_rep_start(5, actor=3, tar=0x10), "actor"),     # (wire 3 is a player slot with no unit here)
                       (_rep_start(6, tar=0x00), "target"), (_rep_start(6), "duplicate")):
        rig.units[:] = [u for u in rig.units if u["slot"] != 3] if why == "actor" else rig.units
        rig.feed(start)
        rig.step()
        assert lane.declined_why == why, (why, lane.declined_why)
    busy = _LaneRig()
    for k in range(BW.ACT_MAX_RUNNING + 1):                              # seven actors at once: the running cap
        busy.feed(_rep_start(10 + k, actor=k, player=k < 4, tar=0x01))
    busy.step()
    assert len(busy.lane.running) == BW.ACT_MAX_RUNNING and busy.lane.declined_why == "busy"
    busy.step(1, r8_hits=1, end_injected=True)
    assert busy.lane.abort_why == "r8" and not busy.lane.running and busy.lane.restores_limited == 1
    busy.lane.latch_caps(0x22, True)
    busy.lane.lane_tick(False, True)                                     # a null view clears nothing
    assert busy.lane.bit5 and busy.lane.host_caps == 0x22
    busy.lane.reset_for_boot(True)
    assert not busy.lane.bit5 and busy.lane.started == 0
    lane.discard_all("teardown")
    assert lane.started == 3 and lane.running == [] and lane.book.queue == [] and lane.aborted == 3
    wall = _LaneRig()
    wall.feed(_rep_start(1))
    wall.step()
    wall.lane.tick(wall.ctx(wall_ms=wall.ms + BW.ACT_WALL_CAP_MS + 1))
    assert wall.lane.abort_why == "cap"


#: the stock hook sites s134 adds (a file, then the lines in order inside ONE patch's new side) -- audit 2.2's live map
REP_HOOKS = {
    "btl_cmd.cs": [("public static void ExecVfxCommand(BTL_DATA target, CMD_DATA cmd = null, BattleActionThread sfxThread = "
                    "null)", "{", "if (Memoria.Netsync.NetSyncDiorama.ActLive && Memoria.Netsync.NetSyncDiorama.ActOnHit("
                                  "target, cmd, sfxThread))", "return;", "if (cmd == null)"),
                   ("case BattleCommandId.SysTrans:", "{", "if (Memoria.Netsync.NetSyncDiorama.Booted)",
                    "Memoria.Netsync.NetSyncDiorama.NoteCalcWhileBooted();")],
    "SBattleCalculator.cs": [("public static void CalcMain(BTL_DATA caster, BTL_DATA target, BattleCommand command, Int32 "
                              "scriptId, BattleActionThread sfxThread)", "{", "if (Memoria.Netsync.NetSyncDiorama.Booted)",
                              "Memoria.Netsync.NetSyncDiorama.NoteCalcWhileBooted();", "try")],
    "btl_util.cs": [("if (cmdUsed == null && Memoria.Netsync.NetSyncDiorama.ActLive)",
                     "cmdUsed = Memoria.Netsync.NetSyncDiorama.ActCommandMotionOf(btl, includeSysCmd);",
                     "return cmdUsed != null;"),
                    ("if (Memoria.Netsync.NetSyncDiorama.ActBusy && Memoria.Netsync.NetSyncDiorama.ActIsBusy(btl, "
                     "(Int32)mode))", "return true;", "return false;")],
    "UnifiedBattleSequencer.cs": [("if (Memoria.Netsync.NetSyncDiorama.ActLive ? Memoria.Netsync.NetSyncDiorama."
                                   "ActExecuteLoop(runningActions[i]) : runningActions[i].ExecuteLoop())",),
                                  ("code.TrySetVariable(extraVar, cmd);",)],
    "NetSyncDiorama.cs": [("AbortReplay(\"the diorama tore down\");", "try { ActDiscardAll(\"teardown\"); }",
                           "catch { }", "Disarm();"),
                          ("Boot(battleMapIndex, patternIndex, start, isRandomEncounter);", "ActLatchCaps(hostCaps);"),
                          ("try { ActAbortAll(\"leave\"); }", "catch { }")],
    "NetSyncClient.cs": [("NetSyncBattle.SelfTestPump(ee);", "NetSyncDiorama.ActionTickBench();", "NetSyncDiorama.ActTick();"),
                         ("NetSyncDiorama.ActionTick(_socket);", "NetSyncDiorama.ActTick();")],
}
# [s134 review] contain-abort-sfx-loader-lock (LoadLoop's guard, both halves), timing-01 (EndTick's stale-lane break and the
# hold's refs), timing-06 (no grace in a backlog drain), stock-05 (the stock TrySetVariable signature kept, forwarding)
REP_HOOKS["SFXData.cs"] = [("if (LoadCur.useCamera)", "{", "if (LoadCur.replayDropped)", "{", "LoadCur.loadHasEnded = true;",
                            "LoadCur = null;", "continue;", "}",
                            "if (SFXDataMesh.Raw.RenderingCount > 0 || SFXData.sfxLoadedNotPlayed.Count > 0)"),
                           ("LoadCur.loadHasEnded = true;", "if (!LoadCur.replayDropped)",
                            "SFXData.sfxLoadedNotPlayed.Add(LoadCur);", "LoadCur = null;")]
REP_HOOKS["NetSyncDiorama.cs"] = REP_HOOKS["NetSyncDiorama.cs"] + [
    ("if (!any)", "{", "if (ActEndHoldStaleInject(b))", "return;"),
    ("String actHold = ActEndHoldWhy(ref e, ref action, ref allDown);",),
    ("if (dT != null && lethalT && a.CasterIsPlayer && !a.TargetIsPlayer && !backlog)", 'ActArmDeathGrace(dT, true, "impact");')]
REP_HOOKS["BattleActionCode.cs"] = [("public Boolean TrySetVariable(Dictionary<String, Int32> extraVar)", "{",
                                     "return TrySetVariable(extraVar, null);", "}",
                                     "public Boolean TrySetVariable(Dictionary<String, Int32> extraVar, CMD_DATA cmd)")]


def test_the_replay_hooks_sit_at_the_audits_sites():
    """Each s134 hook at its audited site, read off s134's own patch (code lines, comments dropped, in order): the hit
    short-circuit is ExecVfxCommand's FIRST statement and the tripwire heads CalcMain and the SysTrans case (each behind one
    static read); the command-motion hook rides the OUT overload after the stock Find (D01); IsBtlBusy's before its `return
    false`; the guarded loop; SetVariable's command; ForceDisarm's discard between AbortReplay and Disarm; BootFromWire's
    latch right after Boot; LeaveFrom's abort; ActTick right after both drains. The new file is compiled (csproj)."""
    for file_name, sites in REP_HOOKS.items():
        new = [c for c in (_strip_comment(t) for _h, _k, t in _new_side(file_name, _patch_bytes("s134"))) if c]
        for site in sites:
            at = next((k for k in range(len(new)) if new[k:k + len(site)] == list(site)), None)
            assert at is not None, (file_name, site[0])
    assert _added_after("s134", "NetSyncDiorama.cs", 'AbortReplay(via == "end-leave"', 'try { ActAbortAll("leave"); }')
    proj = [t for _h, k, t in _new_side("Assembly-CSharp.csproj", _patch_bytes("s134")) if k == "+"]
    assert proj == ['<Compile Include="Memoria\\Netsync\\NetSyncDiorama.Replay.cs" />'], proj
    assert "Assembly-CSharp/Memoria/Netsync/NetSyncDiorama.Replay.cs" in msr.DEFAULT_FILES
    assert _battle_text("internal static void ReleaseRunningAction(Int32 index)") or any(
        "internal static void ReleaseRunningAction(Int32 index)" in t for _h, _k, t in
        _new_side("UnifiedBattleSequencer.cs", _patch_bytes("s134")))


#: ActDecide's conditions (C#, as its if-chain writes them) -> the ActDecideIn edit that sets exactly that reason on the
#: base START (an Attack, kind 3, a mapped target): a condition the chain gains or rewrites turns the test below red until it
#: is named here
REP_DECIDE_EDITS = {
    "d.KnobOff": {"knob_off": True}, "d.LeverOff": {"lever_off": True}, "d.NoRework": {"no_rework": True},
    "d.EndPresented": {"end_presented": True}, "d.Leaving": {"leaving": True}, "d.Stale": {"stale": True},
    "d.Backlog": {"backlog": True}, "d.ActorMissing": {"actor_missing": True}, "d.ActorHidden": {"actor_hidden": True},
    "d.DeadOrDying && !ActDeadMayRun(d.CmdNo, d.DieSeq, d.ActorLinked)": {"dead_or_dying": True},
    "d.Kind > NetSyncBattle.VfxKindCommon": {"kind": BW.VFX_KIND_UNKNOWN},
    "d.MonsterTransform": {"monster_transform": True}, "d.MappedTar == 0": {"mapped_tar": 0},
    "d.Kind == NetSyncBattle.VfxKindNone": {"kind": BW.VFX_KIND_NONE},
    "d.Running >= ActMaxRunning": {"running": BW.ACT_MAX_RUNNING}}


def _rep_decide_chain() -> list:
    """ActDecide's if-chain off the stack, in order: [(condition, the verdict's C# name)]."""
    body = " ".join(_strip_comment(t) for t in _cs_block(REPLAY_FILE, "internal static Int32 ActDecide(", "}"))
    return re.findall(r"if \((.+?)\) return (\w+);", body)


def _rep_chain_violations(decide) -> list:
    """Every single reason and every PAIR of reasons set together (on different fields) that ``decide`` answers otherwise
    than the C# chain: the earlier condition's verdict wins."""
    chain = _rep_decide_chain()
    base = dict(actor_linked=True, cmd_no=BW.CMD_ATTACK_ID, kind=BW.VFX_KIND_SPECIAL, mapped_tar=0x10)
    bad = [("base", decide(BW.act_decide_in(**base)))] if decide(BW.act_decide_in(**base)) != BW.ACT_GO else []
    for i, (ci, wi) in enumerate(chain):
        want = BW.CS_REPLAY_CONSTANTS[wi]
        got = decide(BW.act_decide_in(**dict(base, **REP_DECIDE_EDITS[ci])))
        if got != want:
            bad.append((ci, got))
        for cj, _wj in chain[i + 1:]:
            if set(REP_DECIDE_EDITS[ci]) & set(REP_DECIDE_EDITS[cj]):
                continue                                                # (one field: never set together)
            got = decide(BW.act_decide_in(**dict(base, **REP_DECIDE_EDITS[ci], **REP_DECIDE_EDITS[cj])))
            if got != want:
                bad.append((ci, cj, got))
    return bad


def test_the_decide_twins_order_is_the_engines_if_chain_pair_by_pair():
    """[s134 review harness-5] The bench's calibration table rests on ActDecide's ORDER (I green under `replay off` because
    knob is ahead of the lever; J / BL / H red because they decline `lever` first). The chain is read off the stack, every
    condition is a known one, and for every PAIR of reasons set together the twin answers the earlier one -- and a twin with
    two reasons swapped is caught (a check that cannot fail is no check)."""
    chain = _rep_decide_chain()
    assert [c for c, _w in chain] == list(REP_DECIDE_EDITS), chain
    assert chain[-1] == ("d.Running >= ActMaxRunning", "ActWhyBusy")
    assert not _rep_chain_violations(BW.act_decide)
    for swapped in ({"lever_before_knob": True}, {"rework_before_lever": True}, {"backlog_before_lever": True},
                    {"stale_before_leave": True}, {"noop_first": True}):
        assert _rep_chain_violations(_decide_with(**swapped)), swapped
    hidden_first = lambda d: BW.ACT_WHY_HIDDEN if d["actor_hidden"] else BW.act_decide(d)    # noqa: E731
    transform_first = lambda d: BW.ACT_WHY_TRANSFORM if d["monster_transform"] else BW.act_decide(d)   # noqa: E731
    end_after_leave = lambda d: BW.ACT_WHY_LEAVE if d["leaving"] and not any(                 # noqa: E731
        d[k] for k in ("knob_off", "lever_off", "no_rework")) else BW.act_decide(d)
    for mutant in (hidden_first, transform_first, end_after_leave):
        assert _rep_chain_violations(mutant)


def test_the_review_pass_keeps_every_replay_contained_and_restored():
    """[s134 review] the fixes, at their lines on the live stack: an abort drops the replay's unplayed SFX (camera loads
    unlocked) and unregisters it only once the sequencer let go -- else a ZOMBIE stays short-circuited and ActLive; the
    busy window snapshots and restores the weapons and the cursor bit, the disappear restore spares only a dead ENEMY;
    the units of a replay aborted before an end injection are restored right before it; a nosequence launch leaves no
    command stance; the counters every abort / drop / discard by its reason."""
    for line in ("Boolean outOfLoop = ActReleaseHard(r.Action, release);", "if (!outOfLoop)", "ActZombie(r);",
                 "UnifiedBattleSequencer.runningActions.Remove(a);",
                 "return _actZombies.Count > 0 && _actZombies.ContainsKey(cmd);",
                 "ActLive = _actByCmd.Count > 0 || _actZombies.Count > 0;",
                 "s.DropForReplay((plan & ActSfxUnlock) != 0);", "WeaponMeshFlags = n.weaponMeshFlags,",
                 "d.weaponMeshFlags = s.WeaponMeshFlags;", "_actWindowCursorBit = b.cmd_status & 2;",
                 "b.cmd_status = ActCursorBitAfter(b.cmd_status, _actWindowCursorBit, limited);",
                 "if (ActRestoresDisappear(d.bi.player != 0, dead) && d.bi.disappear != s.Disappear)",
                 "_actWindowAbortMask |= ActUnitsOf(r);", "Int32 mask = ActPreInjectMask(aborted, running);",
                 "try { btl_mot.SetDefaultIdle(actor); }", "_actAbortsBy[k]++;", "_actDropped++;",
                 "_actDiscardedPending += queued;", "_actDiscardedRunning += running;",
                 "InjectEnd(b, _actHeldEnd, _actHeldAction, _actHeldAllDown);"):
        assert _battle_text(line), line
    assert any("internal void DropForReplay(Boolean unlock)" in t for _h, _k, t in _new_side("SFXData.cs", _patch_bytes("s134")))
    assert tuple(BW.ACT_ABORT_REASONS) == tuple(re.findall(r'"([\w-]+)"', next(
        ln for ln in _stack_text(REPLAY_FILE) if "internal static readonly String[] ActAbortReasons" in ln)))
    # every ActAbort reason is published under its key, in that order
    body = " ".join(t for _h, _k, t in _new_side("HarnessAgent.cs", _patch_bytes("s134")))
    got = re.findall(r'Num\(sb, "(\w+)", Memoria\.Netsync\.NetSyncDiorama\.HarnessActAbortsBy\("([\w-]+)"\)\)', body)
    assert got == list(zip(BW.ACT_ABORTS_KEYS, BW.ACT_ABORT_REASONS)), got


def test_the_replay_lane_counts_every_abort_drop_and_discard_by_reason():
    """[s134 review timing-04 / harness-9 / timing-08 / harness-12] the stand-in's counters: an abort under its reason
    (`aborts`), a parked START an abort-all declines (`dropped`), a teardown's drops apart from started / declined /
    aborted (`discarded`) -- both identities hold after it; the aborts are judged while PAUSED too (the wall cap), the
    sequencer frame is not; a teardown keeps a Change replay's row (the engine never touches a unit row there)."""
    rig = _LaneRig()
    lane = rig.lane
    rig.step()
    rig.feed(_rep_start(1))
    rig.step()
    rig.feed(_rep_start(2))                                              # parks behind 1
    rig.step()
    rig.step(BW.ACT_PENDING_ABORT_MS // 33 + 2)
    assert lane.aborts_by["pending"] == 1 and lane.abort_why == "pending"
    rig.feed(_rep_start(3))                                              # parks behind 2
    rig.step()
    lane.abort_all("r8", ctx=rig.ctx())
    doc = lane.doc(role=True, booted=True)
    assert doc["aborts"] == dict(dict.fromkeys(BW.ACT_ABORTS_KEYS, 0), pending=1, r8=1) and doc["dropped"] == 1
    assert doc["declined"] == doc["dropped"] and BW.act_guest_invariant(doc) and BW.act_guest_ends_balance(doc)
    rig.feed(_rep_start(4))
    rig.step()
    rig.feed(_rep_start(5))                                              # parks behind 4
    rig.step()
    lane.rows[0] = 0                                                     # (a Change replay's flipped row)
    lane.discard_all("teardown (bench)")
    doc = lane.doc(role=True, booted=True)
    assert doc["discarded"] == {"pending": 1, "running": 1} and doc["aborted"] == 2 and lane.rows == {0: 0}
    assert BW.act_guest_invariant(doc) and BW.act_guest_ends_balance(doc)
    assert not BW.act_guest_invariant(dict(doc, discarded={"pending": 0, "running": 1}))
    assert not BW.act_guest_ends_balance(dict(doc, discarded={"pending": 1, "running": 0}))
    paused = _LaneRig()
    paused.feed(_rep_start(1))
    paused.step(3)
    rec = paused.lane.running[0]
    f0 = rec.frames
    paused.lane.tick(paused.ctx(paused=True))                            # paused: no sequencer frame
    assert rec.frames == f0 >= 1 and paused.lane.running == [rec]
    paused.lane.tick(paused.ctx(paused=True, wall_ms=paused.ms + BW.ACT_WALL_CAP_MS + 1))
    assert paused.lane.abort_why == "cap" and paused.lane.aborts_by["cap"] == 1 and rec.frames == f0


def test_the_action_replay_knob_is_a_behaviour_key_and_its_config_suffix_parses():
    """[Netsync] ActionReplay (default 1, quotes accepted) joins the behaviour signature (bsig) and the config line names
    ' actionReplay=0' only when off -- and the T2 benches' config matcher still reads such a line."""
    for piece in ('String arRaw = ini.GetSetting("Netsync", "ActionReplay", "1").Trim();', 'Boolean actionReplay = arRaw != "0";',
                  '"|" + (actionReplay ? "1" : "0");', 'NetSyncDiorama.ActionReplay = actionReplay;',
                  '(!actionReplay ? " actionReplay=0" : "") +'):
        assert any(piece in ln for ln in _stack_text("NetSyncClient.cs")), piece
    pb = _peer_bench()
    line = ("[NetSync] config enabled=True role=client field=0 actionReplay=0 relay=ws://127.0.0.1:49201 "
            "code=ff9-T2BENCH1")
    m = pb.MATCHERS["config"].match(line)
    assert m and m.group(2) == "client" and m.group(6) == "ff9-T2BENCH1" and "actionReplay=0" in m.group(4)


# =========================================================================== [ff9mapkit netsync s135]
# THE REPLAY HIT HOLD (studies/battle-coop/R3-DESIGN.md 3.3.4 as amended by R3-ACTION-REPLAY-AUDIT.md 2.3 -- amendments 1-15,
# decisions D01-D12; the audit's "s124"). Guest only, wire v14, harness protocol 5: one additive sub-object
# (`netsync.battle.act.guest.hold`, the LAST key of `act.guest`), the `actbench` hold ops (no new sub-verb), one proof
# line. battlewire's twins of the PURE rules (ActHoldVerdict ... ActCreditTake) EVALUATE ActHoldSelfTest's OWN 28 rows
# off the stack -- translated statement by statement (its initializers, its for loop, its ternaries) -- each rule's mutant
# fails a row, the constants are pinned by name both ways, and s134 -- s135's calibration red -- is the ladder prefix
# through `actreplay` (S134_CAPS): every check below that reads the key, the ops or the proof line reads "cannot" there.
HOLD_ROW_MARKS = ("verdict: `hold off` is the pre-s135 guest -- every frame applies on arrival",
                  "superseded: a deferred lane applies only if newer than the slot's last applied frame (wrap-safe)",
                  "revive: decided at release -- not lethal, and dead here NOW",
                  "reconciler: a masked slot's whole record skips -- the `lifeskip off` lever lets it through",
                  "release: a replaced START's impacts go `replaced`, an abort-all's `abort`, any other decline `declined`",
                  "hit: the oldest HELD impact of that replay (by reference) on that master target; never a queued one; none "
                  "= a credit",
                  "credits: bounded per replay (32)",
                  # [s135 fix pass] the five rows the review's findings added
                  "deferred: a queued lane applies only if newer than the slot's last applied state (a reconciler sample "
                  "stamps too) -- and never revives through a lane that was no life lane when it queued",
                  "queue: a hit inside EffectPoint's bracket defers the drain to the next tick; outside it the queue drains "
                  "at once",
                  "catch-up: a skipped record re-applies once its slot leaves the life mask; a still-masked slot's waits",
                  "figure: a hit figure its Figure point never showed is shown at once when the replay is cut -- never at "
                  "its natural end",
                  "grace: a player's released kill on an enemy arms the death-attack grace -- never from a backlog, at the "
                  "end injection, or once no replay can follow")


class _CsList(list):
    """A C# List<T> as ActHoldSelfTest reads one (``.Count``)."""

    @property
    def Count(self):                                                    # noqa: N802 -- C#'s name
        return len(self)


class _CsArray(tuple):
    """A C# array as ActHoldSelfTest reads one (``.Length``, ``[i]``)."""

    @property
    def Length(self):                                                   # noqa: N802 -- C#'s name
        return len(self)


def _hold_init(code: str) -> str:
    """C#'s initializers (strings masked) -> Python: ``new List<T>()`` -> ``[]``, ``new List<T> { a, b }`` -> ``[a, b]``,
    ``new T { A = x, B = y }`` -> ``T(A=x, B=y)`` (nested, inner first)."""
    code = re.sub(r"\bnew List<\w+>\(\)", "[]", code)
    while True:
        m = re.search(r"\bnew (List<\w+>|\w+)\s*\{", code)
        if not m:
            return code
        at = m.end() - 1
        close = _rep_close(code, at, "{", "}")
        inner = _hold_init(code[at + 1:close])
        if m.group(1).startswith("List<"):
            rep = "[" + inner + "]"
        else:
            parts = [p for p in _rep_split(inner, ",") if p]
            kws = []
            for p in parts:
                k, eq, v = p.partition("=")
                assert eq and re.fullmatch(r"\s*[A-Z]\w*\s*", k), p
                kws.append(f"{k.strip()}={v.strip()}")
            rep = f"{m.group(1)}(" + ", ".join(kws) + ")"
        code = code[:m.start()] + rep + code[close + 1:]


_HOLD_DECL = re.compile(r"(?:ActRec|Int32|String|Boolean|List<\w+>) (\w+ = .+)", re.S)
_HOLD_FOR = re.compile(r"Int32 (\w+) = (.+?); \1 < (.+?); \1\+\+")


def _hold_python(stmts: list, indent: str = "") -> list:
    """ActHoldSelfTest's statements as Python source lines: a Row -> ``__row(expr, name)``; a declaration (several
    declarators too, initializers translated) -> assignments; a ``for (Int32 i = a; i < b; i++)`` -> ``for i in range``;
    anything else (a call) as itself."""
    out = []
    for s in stmts:
        if not isinstance(s, str):
            kind, header, body = s
            m = _HOLD_FOR.fullmatch(header)
            assert kind == "for" and m, s
            out.append(f"{indent}for {m.group(1)} in range({_rep_expr(m.group(2))}, {_rep_expr(m.group(3))}):")
            out += _hold_python(body, indent + "    ")
            continue
        masked, strings = _rep_mask(s)
        masked = _hold_init(masked)

        def back(code):
            for i, lit in enumerate(strings):
                code = code.replace(f"__S{i}__", lit)
            return code
        m = re.fullmatch(r"Row\((.*)\)", masked, re.S)
        if m:
            args = _rep_split(m.group(1), ",")
            assert len(args) == 4 and args[2:] == ["ref rows", "ref fail"], args
            name = " + ".join(f"str({_rep_expr(part, strings)})" for part in _rep_split(args[1], "+"))
            out.append(indent + back(f"__row({_rep_expr(args[0], strings)}, {name})"))
            continue
        m = _HOLD_DECL.fullmatch(masked)
        if m:
            for d in _rep_split(m.group(1), ","):
                name, _, value = d.partition("=")
                out.append(indent + back(f"{name.strip()} = {_rep_expr(value.strip(), strings)}"))
            continue
        out.append(indent + back(_rep_expr(masked, strings)))
    return out


def _hold_program() -> str:
    """ActHoldSelfTest, read off the stack (the hunk that holds it whole), as one Python program."""
    block = _cs_block(REPLAY_FILE, "internal static Boolean ActHoldSelfTest(")
    code = " ".join(_strip_comment(ln) for ln in block if not re.match(r"(?:internal|private|public) static ", ln))
    return "\n".join(_hold_python(_act_statements(code)))


def _hold_ns(**twins) -> dict:
    """The namespace ActHoldSelfTest runs in: the constants by C# name (s134's and s135's; NetSyncEnd's kinds as an
    attribute holder), the twins under their C# names (``twins`` replaces one -- a mutant), ActTestRec (s134's pinned
    helper), ``new ActHeld {..}`` as BW.ActHeld, C#'s List / array reads, and ``__row`` asserting each row."""
    tw = dict(verdict=BW.act_hold_verdict, life=BW.act_lane_is_life, applies=BW.act_held_applies,
              revive=BW.act_revive_at_release, timer=BW.act_held_timer_why, blocked=BW.act_queue_blocked,
              lifemask=BW.act_life_mask_of, busymask=BW.act_busy_mask_of, skips=BW.act_life_skips, via=BW.act_decline_via,
              flushes=BW.act_end_inject_flushes, figpath=BW.act_hit_fig_path, flinch=BW.act_release_flinches,
              figvalue=BW.act_fig_value, p50=BW.act_lag_p50, pick=BW.act_pick_oldest, cadd=BW.act_credit_add,
              cfind=BW.act_credit_find, ctake=BW.act_credit_take, vias=BW.ACT_HOLD_VIAS,
              deferred=BW.act_deferred_applies, catchup=BW.act_catch_up_slots, drains=BW.act_drains_at_hit,
              pending=BW.act_shows_pending_at, grace=BW.act_release_arms_grace)
    tw.update(twins)
    ns = dict(BW.CS_REPLAY_CONSTANTS)
    ns.update(BW.CS_HOLD_CONSTANTS)
    names: list = []

    def row(ok, name):
        if ok is not True:
            raise AssertionError(f"row {name!r} is {ok!r} for the twins")
        names.append(name)

    def member(obj, name):
        v = obj[_snake(name)] if isinstance(obj, dict) else getattr(obj, _snake(name))
        return _CsList(v) if isinstance(v, list) else v

    def held(**kw):                                                     # `new ActHeld { Ord = .., Rec = .. }`
        return BW.ActHeld(**{_snake(k): v for k, v in kw.items()})

    ns.update(__row=row, __m=member, __names__=names,
              NetSyncEnd=SimpleNamespace(**{k: v for k, v in BW.CS_CONSTANTS.items() if re.fullmatch(r"K[A-Z]\w*", k)}),
              Array=SimpleNamespace(IndexOf=lambda arr, x: list(arr).index(x) if x in arr else -1),
              ActHeld=held, ActHoldVias=_CsArray(tw["vias"]),
              ActHoldVerdict=tw["verdict"], ActLaneIsLife=tw["life"], ActHeldApplies=tw["applies"],
              ActReviveAtRelease=tw["revive"], ActHeldTimerWhy=tw["timer"], ActQueueBlocked=tw["blocked"],
              ActLifeMaskOf=tw["lifemask"], ActBusyMaskOf=tw["busymask"], ActLifeSkips=tw["skips"],
              ActDeclineVia=tw["via"], ActEndInjectFlushes=tw["flushes"], ActHitFigPath=tw["figpath"],
              ActReleaseFlinches=tw["flinch"], ActFigValue=tw["figvalue"], ActLagP50=tw["p50"],
              ActPickOldest=tw["pick"], ActCreditAdd=tw["cadd"], ActCreditFind=tw["cfind"], ActCreditTake=tw["ctake"],
              ActDeferredApplies=tw["deferred"], ActCatchUpSlots=tw["catchup"], ActDrainsAtHit=tw["drains"],
              ActShowsPendingAt=tw["pending"], ActReleaseArmsGrace=tw["grace"],
              ActTestRec=lambda i, actor: BW.ActRec(i, BW.ACT_REPLAY_TEST_NONCE, actor, BW.ACTOR_IS_PLAYER,
                                                    cmd_no=BW.CMD_ATTACK_ID, vfx_kind=BW.VFX_KIND_SPECIAL,
                                                    state=BW.ACT_ST_REGISTERED))
    return ns


def _run_hold_selftest(**twins) -> list:
    ns = _hold_ns(**twins)
    exec(compile(_hold_program(), "<ActHoldSelfTest>", "exec"), ns)              # noqa: S102 -- the stack's own rows
    return ns["__names__"]


def test_the_hold_twins_evaluate_every_hold_selftest_row_off_the_stack():
    """battlewire's s135 twins (the verdict, the lanes, the superseded guard, the revive, the clocks, the queue, the masks,
    the reconciler's skip, the release mapping, the end-inject trigger, the figure path, the flinch, the value, the median,
    the pick, the credits -- and the fix pass's queued-lane release, deferred drain, catch-up, cut figure and grace)
    against ActHoldSelfTest's OWN rows, EVALUATED in order: 28, the proof line's count. Its helper ActTestRec is s134's
    pinned body (REP_HELPER_BLOCKS)."""
    names = _run_hold_selftest()
    assert len(names) == BW.HOLD_SELFTEST_ROWS == 28 and len(set(names)) == 28, names
    assert all(mark in names for mark in HOLD_ROW_MARKS), set(HOLD_ROW_MARKS) - set(names)
    prefix = lambda n: n.split(":", 1)[0]                                # noqa: E731
    assert [sum(prefix(n) == p for n in names) for p in ("verdict", "release", "credits", "figure", "lag", "queue",
                                                         "deferred", "catch-up", "grace")] \
        == [6, 3, 2, 2, 1, 2, 1, 1, 1], names
    assert sum("ref rows, ref fail);" in ln for ln in net_lines(REPLAY_FILE, r".", [_patch_bytes("s135")])) == 28
    body = REP_HELPER_BLOCKS["private static ActRec ActTestRec(UInt16 id, Byte actor)"]
    got = [c for c in (_strip_comment(t) for t in _cs_block(REPLAY_FILE, "private static ActRec ActTestRec(", "}")) if c][2:]
    assert got[:len(body)] == body, got


def _verdict_with(**changes):
    """ActHoldVerdict with ONE rule broken (the twin's own body otherwise)."""
    def verdict(hold_on, stat_tick, paired_state, target_resolved, credit, masked, room):
        if changes.get("stat_ticks_pair") and hold_on and stat_tick and paired_state == BW.ACT_ST_RUNNING and room:
            return BW.ACT_HOLD_HOLD                                     # a stat tick held for a hit it never gets
        if changes.get("ended_holds") and hold_on and paired_state == BW.ACT_ST_ENDED and not credit and room:
            return BW.ACT_HOLD_HOLD                                     # an ended replay holds (it will never hit)
        if changes.get("credit_never_queues") and hold_on and credit and masked and room:
            return BW.ACT_HOLD_LATE                                     # a late frame jumps an older change
        if changes.get("full_drops") and hold_on and not room:
            return BW.ACT_HOLD_QUEUE                                    # a full list keeps more (the cap ignored)
        if changes.get("unpaired_ignores_busy") and hold_on and paired_state < 0 and masked:
            return BW.ACT_HOLD_APPLY                                    # amendment 5 dropped
        if changes.get("declined_holds") and hold_on and paired_state == BW.ACT_ST_DECLINED and target_resolved and room:
            return BW.ACT_HOLD_HOLD
        return BW.act_hold_verdict(hold_on, stat_tick, paired_state, target_resolved, credit, masked, room)
    return verdict


@pytest.mark.parametrize("twins", [
    {"verdict": lambda *a: BW.act_hold_verdict(True, *a[1:])},
    {"verdict": _verdict_with(stat_ticks_pair=True)}, {"verdict": _verdict_with(ended_holds=True)},
    {"verdict": _verdict_with(credit_never_queues=True)}, {"verdict": _verdict_with(full_drops=True)},
    {"verdict": _verdict_with(unpaired_ignores_busy=True)}, {"verdict": _verdict_with(declined_holds=True)},
    {"life": lambda lethal, dead, busy: bool(lethal or dead)},
    {"applies": lambda seq, seen, stamp: not seen or seq > stamp},
    {"applies": lambda seq, seen, stamp: not seen or BW._i16(seq - stamp) >= 0},
    {"revive": lambda lethal, dead: bool(dead)},
    {"timer": lambda ended, end_ms, arrive, now: "timeout" if now - arrive >= BW.ACT_HOLD_TIMEOUT_MS else
        "hostdone" if ended and now - end_ms >= BW.ACT_HOLD_HOST_DONE_MS else None},
    {"timer": lambda ended, end_ms, arrive, now: "hostdone" if ended and now - end_ms > BW.ACT_HOLD_HOST_DONE_MS else
        "timeout" if now - arrive > BW.ACT_HOLD_TIMEOUT_MS else None},
    {"blocked": lambda slots, held, queued: (slots & held) != 0},
    {"lifemask": lambda held, queued: BW.act_life_mask_of(held, [])},
    {"busymask": lambda held, queued: BW.act_life_mask_of(held, queued)},
    {"skips": lambda mask, index, on: 0 <= index < 8 and (mask & (1 << index)) != 0},
    {"via": lambda why: "abort" if why in ("r8", "w3", "leave", "clear", "superseded") else "declined"},
    {"via": lambda why: "replaced" if why == "superseded" else "declined"},
    {"flushes": lambda ours, kind: bool(ours) and kind != BW.K_FIGHTING},
    {"flushes": lambda ours, kind: BW.is_end_kind(kind)},
    {"figpath": lambda hidden, bracket: BW.ACT_FIG_BRACKET if bracket else BW.ACT_FIG_DIRECT},
    {"flinch": lambda dmg, lethal, revive, hidden, can: bool(dmg) and not lethal and not hidden and bool(can)},
    {"figvalue": lambda hp, mp: hp},
    {"p50": lambda s: sorted(s)[len(s) // 2] if s else -1},
    {"pick": lambda held, rec, unit: next((i for i, h in enumerate(held) if h.rec is rec and h.unit_id == unit), -1)},
    {"pick": lambda held, rec, unit: min((i for i, h in enumerate(held) if h.rec is rec and h.unit_id == unit),
                                         key=lambda i: held[i].ord, default=-1)},
    {"cfind": lambda r, unit: (len(r.hold_credit_units) - 1 - r.hold_credit_units[::-1].index(unit))
        if r.hold_credit_units and unit in r.hold_credit_units else -1},
    {"cadd": lambda r, unit, ms: (setattr(r, "hold_credit_units", (r.hold_credit_units or []) + [unit]),
                                 setattr(r, "hold_credit_ms", (r.hold_credit_ms or []) + [ms]))},
    {"vias": ("hit", "late", "end", "hostdone", "timeout", "abort", "declined", "replaced", "end-inject")},
    {"deferred": lambda d, rv, life, seq, seen, stamp: not d or BW.act_held_applies(seq, seen, stamp)},
    {"deferred": lambda d, rv, life, seq, seen, stamp: not (rv and not life) and (not d or BW.act_held_applies(seq, seen,
                                                                                                             stamp))},
    {"deferred": lambda d, rv, life, seq, seen, stamp: not d or (not (rv and not life))},
    {"catchup": lambda skipped, mask: skipped},
    {"drains": lambda bracket: True},
    {"pending": lambda via: True}, {"pending": lambda via: via == "abort"},
    {"grace": lambda lethal, cp, tp, backlog, via, no_replay: bool(lethal) and bool(cp) and not tp and not backlog},
    {"grace": lambda lethal, cp, tp, backlog, via, no_replay: bool(lethal) and bool(cp) and not tp and not backlog
        and via != "end-inject"}],
    ids=["verdict-no-lever", "verdict-stat-tick-pairs", "verdict-ended-holds", "verdict-credit-jumps-queue",
         "verdict-full-keeps", "verdict-unpaired-ignores-busy", "verdict-declined-holds", "life-busy-ignored",
         "applies-no-wrap", "applies-equal-applies", "revive-lethal-revives", "timer-timeout-first",
         "timer-strict-gt", "blocked-older-queued-ignored", "lifemask-queued-ignored", "busymask-life-only",
         "skips-no-lever", "via-superseded-aborts", "via-abort-all-declines", "flushes-event-too",
         "flushes-not-ours", "figpath-hidden-shows", "flinch-revive-flinches", "figvalue-hp-only", "p50-upper-median",
         "pick-first-not-oldest", "pick-queued-picked", "credit-newest-first", "credit-uncapped", "vias-order",
         "deferred-revives-a-free-lane", "deferred-guards-the-arrival", "deferred-ignores-the-stamp", "catchup-masked-too",
         "drains-inside-the-bracket", "pending-at-a-natural-end", "pending-abort-only", "grace-at-the-end-inject",
         "grace-with-no-replay"])
def test_each_hold_rule_mutant_fails_a_selftest_row(twins):
    """A CHECK THAT CANNOT FAIL is no check: each rule of the verdict, the lanes, the guard, the clocks, the queue, the
    masks, the release mapping, the figures and the credits, broken alone in its twin, fails one of the engine's own rows."""
    _hold_program()                                                     # (its own parse outside the raises)
    with pytest.raises(AssertionError, match=r"^row ['\"]"):
        _run_hold_selftest(**twins)


def test_the_hold_twins_take_the_engines_parameters_in_its_order():
    """Each s135 twin's parameters ARE its C# method's, in order (camelCase -> snake_case)."""
    for start, fn in (("internal static Int32 ActHoldVerdict(", BW.act_hold_verdict),
                      ("internal static Boolean ActLaneIsLife(", BW.act_lane_is_life),
                      ("internal static Boolean ActHeldApplies(", BW.act_held_applies),
                      ("internal static Boolean ActReviveAtRelease(", BW.act_revive_at_release),
                      ("internal static String ActHeldTimerWhy(", BW.act_held_timer_why),
                      ("internal static Boolean ActQueueBlocked(", BW.act_queue_blocked),
                      ("internal static Boolean ActLifeSkips(", BW.act_life_skips),
                      ("internal static String ActDeclineVia(", BW.act_decline_via),
                      ("internal static Boolean ActEndInjectFlushes(", BW.act_end_inject_flushes),
                      ("internal static Int32 ActHitFigPath(", BW.act_hit_fig_path),
                      ("internal static Boolean ActReleaseFlinches(", BW.act_release_flinches),
                      ("internal static Int32 ActFigValue(", BW.act_fig_value),
                      ("internal static Int32 ActLagP50(", BW.act_lag_p50),
                      ("internal static Int32 ActPickOldest(", BW.act_pick_oldest),
                      ("internal static void ActCreditAdd(", BW.act_credit_add),
                      ("internal static Int32 ActCreditFind(", BW.act_credit_find),
                      ("internal static Int32 ActCreditTake(", BW.act_credit_take),
                      ("internal static Int32 ActBusyMaskOf(", BW.act_busy_mask_of),
                      ("internal static Int32 ActLifeMaskOf(", BW.act_life_mask_of),
                      ("internal static Boolean ActDeferredApplies(", BW.act_deferred_applies),
                      ("internal static Int32 ActCatchUpSlots(", BW.act_catch_up_slots),
                      ("internal static Boolean ActDrainsAtHit(", BW.act_drains_at_hit),
                      ("internal static Boolean ActShowsPendingAt(", BW.act_shows_pending_at),
                      ("internal static Boolean ActReleaseArmsGrace(", BW.act_release_arms_grace)):
        cs = [_snake(p) for p in _cs_signature(REPLAY_FILE, start)]
        assert cs == _twin_params(fn), (start, cs, _twin_params(fn))
    # ActHeld's fields, in the class's order (the twin's constructor parameters; `A` is the frame, `a`)
    cls = " ".join(_cs_block(REPLAY_FILE, "internal sealed class ActHeld", "}"))
    fields = [f for decl in re.findall(r"public [\w.]+ ([^;=]+)(?:=[^;]*)?;", cls) for f in decl.replace(" ", "").split(",")]
    assert [_snake(f) for f in fields] == _twin_params(BW.ActHeld.__init__)[1:], fields


def _hold_consts() -> dict:
    """Every `internal const Int32` the s135 patch declares (comments stripped) -> its value."""
    out = {}
    for line in net_lines(REPLAY_FILE, r"internal const Int32 ", [_patch_bytes("s135")]):
        m = re.fullmatch(r"internal const Int32 (.*);", _strip_comment(line))
        assert m, line
        for decl in m.group(1).split(","):
            d = re.fullmatch(r"\s*(\w+) = (0x[0-9A-Fa-f]+|-?\d+)\s*", decl)
            assert d, decl
            out[d.group(1)] = int(d.group(2), 0)
    return out


def test_the_hold_constants_are_the_stacks_both_ways():
    """THE PIN: every CS_HOLD_CONSTANTS entry is NetSyncDiorama.Replay.cs's constant of that name and value, and every
    `internal const Int32` the s135 patch declares is in the table -- a constant added, renamed or retuned on either side
    turns this red. ActViaArrival and the nine ActHoldVias are pinned by value, in the `rel_*` order."""
    cs = _hold_consts()
    assert cs == BW.CS_HOLD_CONSTANTS, sorted(set(cs.items()) ^ set(BW.CS_HOLD_CONSTANTS.items()))
    assert (cs["ActHoldTimeoutMs"], cs["ActHoldHostDoneMs"], cs["ActHoldCap"]) == (2500, 1500, 64)
    assert _battle_text(f'internal const String ActViaArrival = "{BW.ACT_VIA_ARRIVAL}";')
    vias = next(ln for ln in _stack_text(REPLAY_FILE) if "internal static readonly String[] ActHoldVias" in ln)
    assert tuple(re.findall(r'"([\w-]+)"', vias)) == BW.ACT_HOLD_VIAS
    assert BW.ACT_HOLD_REL_KEYS == tuple("rel_" + v.replace("-", "_") for v in BW.ACT_HOLD_VIAS)
    assert set(BW.ACT_FIG_VIAS) == {BW.ACT_VIA_ARRIVAL, "queued", *BW.ACT_HOLD_VIAS}


def test_the_hold_block_is_act_guests_last_key_at_the_catch_lines_sentinels():
    """THE CATCH-LITERAL RE-PIN for s135: `act.guest.hold` in AppendNetsync's SECOND catch literal, right after `last`,
    at its sentinels; the line stays ONE line of two literals; AppendActGuestHold writes the keys in the catch line's order
    (the lag's, then one figs entry's), each through its NetSyncDiorama getter (`rel_<via>` through HarnessHoldRelBy of
    that via); AppendActGuest calls it after `last`; published in every role; protocol stays 5. It was the LAST key at s135
    -- [ff9mapkit netsync s136] s136 appended `fallback` after it (s136's own pin below) and changed nothing else."""
    catch = net_lines("HarnessAgent.cs", r'outer\.Append\("\\"netsync\\":\{\\"enabled')
    assert len(catch) == 1 and catch[0].count(".Append(") == 3 and ".Append(NetsyncF3Retired)" in catch[0], catch
    a, b = _literals(catch[0])
    assert '\\"last\\":null,\\"hold\\":{\\"on\\":false,\\"lifeskip\\":false,' in b and "lifeskip" not in a
    nothing = _agent_netsync_nothing()[0]
    assert _battle_of(nothing)["act"]["guest"]["hold"] == BW.ACT_GUEST_HOLD_SENTINELS
    assert list(_battle_of(nothing)["act"]["guest"])[-3:-1] == ["last", "hold"]
    s135_guest = {k: v for k, v in BW.ACT_GUEST_SENTINELS.items() if k != "fallback"}
    assert list(_battle_of(_catch_doc_in("s135"))["act"]["guest"])[-2:] == ["last", "hold"]   # the last key AT s135
    assert _catch_doc_in("s135") == {**nothing, "battle": {**nothing["battle"], "act": {    # s135 wrote that line whole
        "host": BW.ACT_HOST_SENTINELS, "guest": s135_guest}}}
    new = [t for _h, _k, t in _new_side("HarnessAgent.cs", _patch_bytes("s135"))]
    i = next(k for k, t in enumerate(new) if t.startswith("private static void AppendActGuestHold("))
    j = next(k for k in range(i, len(new)) if new[k].startswith("// [ff9mapkit netsync B5] stage 5:"))
    body = " ".join(_strip_comment(t) for t in new[i:j])
    names = re.findall(r'(?:Bool|Num|Str)\(sb, "(\w+)"', body)
    top = [k for k in BW.ACT_GUEST_HOLD_SENTINELS if k not in ("lag", "figs")]
    assert names == top + list(BW.ACT_HOLD_LAG_KEYS) + list(BW.ACT_HOLD_FIG_KEYS), names
    rel = re.findall(r'Num\(sb, "(\w+)", Memoria\.Netsync\.NetSyncDiorama\.HarnessHoldRelBy\("([\w-]+)"\)\)', body)
    assert rel == list(zip(BW.ACT_HOLD_REL_KEYS, BW.ACT_HOLD_VIAS)), rel
    for k in [k for k in top if k not in BW.ACT_HOLD_REL_KEYS]:
        assert re.search(rf'(?:Bool|Num)\(sb, "{k}", Memoria\.Netsync\.NetSyncDiorama\.HarnessHold\w+\)', body), k
    assert '"lag":{' in body.replace("\\", "") and '"figs":[' in body.replace("\\", "")
    assert _added_after("s135", "HarnessAgent.cs", 'Num(sb, "hits", lhits);', "AppendActGuestHold(sb);")
    assert net_lines("HarnessAgent.cs", r"public const Int32 ProtocolVersion = ") == ["public const Int32 ProtocolVersion = 5;"]
    assert not _battle_text("IsSelfTestRole ? _hold") and not _battle_text("IsSelfTestRole ? _actLifeMask")
    assert _battle_text("internal static Boolean HarnessHoldOn { get { return ActHoldOn; } }")
    assert _battle_text("internal static Int32 HarnessHoldLifeMask { get { return _actLifeMask; } }")


def test_state_reads_the_hold_block_absent_on_s134_as_cannot():
    """On s134's catch block (s135's calibration red) every `act.guest.hold` accessor reads None and `coop_act_hold`
    False; on the live block they read the sentinels and True; a published block reads its values (a copy), a mistyped one
    None, and `figs` a list of copies."""
    old = State({"frame": 1, "netsync": _catch_doc_in("s134")})
    live = State({"frame": 1, "netsync": _agent_netsync_nothing()[0]})
    names = [n for p, n in State.NETSYNC_BATTLE_ACCESSORS.items() if p == "act.guest.hold" or p.startswith("act.guest.hold.")]
    assert len(names) == len(_leaves({"act": {"guest": {"hold": BW.ACT_GUEST_HOLD_SENTINELS}}})) + 2 == 27, names
    assert (State({"frame": 1}).coop_act_hold, old.coop_act_hold, live.coop_act_hold) == (None, False, True)
    assert old.coop_act_guest is True                                   # (s134's own block is there)
    assert all(getattr(old, n) is None for n in names)
    assert all(getattr(live, n) is not None for n in names)
    assert (live.coop_act_hold_figs, live.coop_act_hold_lag_p50, live.coop_act_hold_on) == ([], -1, False)
    doc = _agent_netsync_nothing()[0]
    doc["battle"]["act"]["guest"]["hold"].update(
        held=3, rel_hit=2, life_mask="16", on=True,
        figs=[{"slot": 4, "value": 4321, "via": "hit", "arrival_ms": 100, "release_ms": 612}],
        lag={"n": 2, "min": -40, "p50": -40, "max": 512})
    st = State({"frame": 1, "netsync": doc})
    assert (st.coop_act_hold_held, st.coop_act_hold_rel_hit, st.coop_act_hold_life_mask, st.coop_act_hold_on) == \
        (3, 2, None, True)
    assert (st.coop_act_hold_lag_n, st.coop_act_hold_lag_min, st.coop_act_hold_lag_max) == (2, -40, 512)
    figs = st.coop_act_hold_figs
    figs[0]["value"] = 0
    assert st.coop_act_hold_figs[0]["value"] == 4321                    # a copy
    assert BW.act_hold_released(doc["battle"]["act"]["guest"]["hold"]) == 2 and BW.act_hold_released(None) is None


def test_a_fresh_stand_in_publishes_the_hold_block_and_s134_none(game):
    """The default stand-in (s135) publishes `act.guest.hold` at the agent's sentinels with no client -- but `on` /
    `lifeskip` the live reads at rest (true / true); the stand-in at s134 publishes no `hold`, no 'action hold' proof
    line, and answers the hold forms in s134's words (its usage for a 4-word form, its "unknown op" for a 3-word one)."""
    want = dict(BW.ACT_GUEST_HOLD_SENTINELS, on=True, lifeskip=True)
    assert _battle_of(FakeGame(game)._netsync_doc())["act"]["guest"]["hold"] == want
    old = _selftest(FakeGame(game))
    old.netsync_caps = S134_CAPS
    assert "hold" not in _battle_of(old._netsync_doc())["act"]["guest"]
    assert set(_leaves(_battle_of(old._netsync_doc()))) == set(_leaves(_battle_of(_catch_doc_in("s134"))))
    usage = f"{FG.NETSYNC_ACTBENCH_USAGE_S134}\r\nParameter name: netsync actbench"
    for args, words in ((["actbench", "hold", "off"], "netsync actbench: unknown op 'hold' (tape|hoststarts)"),
                        (["actbench", "lifeskip", "on"], "netsync actbench: unknown op 'lifeskip' (tape|hoststarts)"),
                        (["actbench", "unit", "4", "dead"], usage), (["actbench", "hold"], usage)):
        with pytest.raises(RuntimeError) as err:
            old._netsync(args)
        assert str(err.value) == words, args


HOLD_REFUSALS = [
    # (a fragment the agent says -- ONE C# literal of the stack, or a piece --, the args, where: None / selftest / dio)
    ("netsync actbench: needs the selftest role (netsync selftest 1)", ["actbench", "hold", "off"], None),
    (": expected `", ["actbench", "hold", "maybe"], "selftest"),
    (" on|off`", ["actbench", "lifeskip"], "selftest"),
    (BW.HOLD_UNIT_USAGE, ["actbench", "unit", "8", "dead"], "selftest"),
    (BW.HOLD_UNIT_USAGE, ["actbench", "unit", "x", "dead"], "selftest"),
    (BW.HOLD_UNIT_USAGE, ["actbench", "unit", "4", "undead"], "selftest"),
    (BW.HOLD_UNIT_USAGE, ["actbench", "unit", "4"], "selftest"),
    (BW.HOLD_UNIT_STEADY, ["actbench", "unit", "4", "dead"], "selftest"),
    (BW.HOLD_UNIT_NO_UNIT, ["actbench", "unit", "6", "dead"], "dio"),
    (" has no local unit", ["actbench", "unit", "6", "dead"], "dio"),
]


@pytest.mark.parametrize("fragment,args,where", HOLD_REFUSALS, ids=[f"{r[0][:30]}-{i}" for i, r in enumerate(HOLD_REFUSALS)])
def test_the_stand_in_refuses_the_hold_ops_in_the_agents_words(game, fragment, args, where):
    """Every hold `actbench` gate the stand-in models refuses with the engine's own words (each fragment a literal of the
    stack: HarnessActGuestBench's role gate, HarnessActHoldBench's parse, its steady gate, its resolve)."""
    assert _battle_text(fragment), f"the live stack no longer says {fragment!r}"
    fake = FakeGame(game)
    if where == "selftest":
        _selftest(fake)
    elif where == "dio":
        _dio_fake(fake)
    with pytest.raises(RuntimeError) as err:
        fake._netsync(args)
    assert fragment in str(err.value), str(err.value)
    if args[1] in ("hold", "lifeskip") and where == "selftest":
        # the spliced refusal, WHOLE (the fragment alone would pass a stand-in that answered another op's refusal)
        assert str(err.value) == f"netsync actbench {args[1]}: expected `{args[1]} on|off`", str(err.value)


def test_the_hold_ops_are_the_agents_and_the_driver_gates_them_by_act_guest_hold(game):
    """The hold ops are IsActGuestBenchOp's (case by case) and HarnessActGuestBench's (routed to HarnessActHoldBench); the
    driver keys each on `act.guest.hold` (s135), refuses a malformed form before the step in the engine's words (`hold` /
    `lifeskip` splice their op), and on an s134 engine refuses every hold form naming s135 and what s134 would answer."""
    # (s135's hunks add three cases to s134's switches: read off s135's own patch, in order)
    new = [c for c in (_strip_comment(t) for _h, _k, t in _new_side(REPLAY_FILE, _patch_bytes("s135"))) if c]
    for site in (['case "teardown":', *(f'case "{op}":' for op in BW.ACT_HOLD_BENCH_OPS), "return true;", 'case "tape":',
                  'return value == "play";'],
                 [*(f'case "{op}":' for op in BW.ACT_HOLD_BENCH_OPS), "return HarnessActHoldBench(args, op, val, out why);",
                  "default:"]):
        assert any(new[k:k + len(site)] == site for k in range(len(new))), site
    for op in BW.ACT_HOLD_BENCH_OPS:
        attr, key, patch, _what = Session.NETSYNC_ACTBENCH_OP_CAPS[op]
        assert (attr, key, patch) == ("coop_act_hold", "netsync.battle.act.guest.hold", "s135"), op
    assert _battle_text('why = "netsync actbench " + op + ": expected `" + op + " on|off`";')
    assert Session.NETSYNC_ACTBENCH_HOLD_USAGE["unit"] == BW.HOLD_UNIT_USAGE and _battle_text(BW.HOLD_UNIT_USAGE)
    assert Session.NETSYNC_ACTBENCH_UNIT_STATES == BW.ACT_HOLD_UNIT_STATES
    fake = FakeGame(game)
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.netsync("selftest", 1)
        n = len(fake.executed)
        for args in (("hold",), ("hold", "maybe"), ("lifeskip", "on", "x"), ("unit", "4"), ("unit", "9", "dead"),
                     ("unit", "x", "dead"), ("unit", "4", "zombie"), ("unit", "4", "dead", "now")):
            with pytest.raises(HarnessError) as err:
                g.netsync("actbench", *args)
            with pytest.raises(RuntimeError) as agent:
                fake._netsync(["actbench", *args])
            assert str(err.value) == str(agent.value), (args, str(err.value), str(agent.value))
        assert len(fake.executed) == n
        st = g.act_hold(False)                                          # a well-made form goes to the engine
        assert st.coop_act_hold_on is False and st.coop_act_hold_lifeskip is True
        st = g.actbench("LIFESKIP", "Off")                              # the agent lowercases both; so does the driver
        assert st.coop_act_hold_lifeskip is False and fake.executed[-1] == ["netsync", "actbench", "LIFESKIP", "Off"]
        with pytest.raises(HarnessError, match=r"in its steady state \(PHASE_NORMAL, the units latched\) \(steps="):
            g.act_unit(4, "dead")                                       # (sent: the AGENT refuses it -- no diorama)
    fake = FakeGame(game)
    fake.netsync_caps = S134_CAPS
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.netsync("selftest", 1)
        n = len(fake.executed)
        for args in (("hold", "off"), ("lifeskip", "on"), ("unit", 4, "dead")):
            with pytest.raises(HarnessError) as err:
                g.netsync("actbench", *args)
            with pytest.raises(RuntimeError) as agent:
                fake._netsync(["actbench", *(str(a) for a in args)])
            assert str(err.value).startswith(f"netsync actbench {args[0]}: the deployed engine publishes no "
                                             f"`netsync.battle.act.guest.hold`"), str(err.value)
            assert f"(memoria-patch s135); it would answer \"{agent.value}\" only after the step" in str(err.value), \
                (args, str(err.value), str(agent.value))
        assert len(fake.executed) == n and g.state.coop_act_hold is False and g.state.coop_act_guest is True


def test_the_hold_log_lines_are_the_engines():
    """Every LOG_HOLD_* the stand-in writes and the bench reads is the stack's own words (one C# literal, or a piece the
    engine splices): a reworded engine line turns this red before a bench silently stops matching it."""
    for whole in (BW.LOG_HOLD_FURTHER, BW.LOG_HOLD_LEVERS_BACK, BW.HOLD_UNIT_USAGE, BW.HOLD_UNIT_STEADY,
                  BW.LOG_HOLD_UNIT_SKIPPED, BW.LOG_HOLD_UNIT_APPLIED, BW.LOG_HOLD_HIT_FIRST, BW.LOG_HOLD_SUPERSEDED,
                  BW.LOG_HOLD_RELEASED_VIA, BW.LOG_HOLD_DISCARDED, BW.LOG_HOLD_FAULTED, BW.HOLD_UNIT_NO_UNIT,
                  BW.LOG_HOLD_MASK_SKIP, BW.LOG_HOLD_FLUSH, BW.LOG_HOLD_CATCH_UP, BW.LOG_HOLD_CATCH_UP_PIECE,
                  BW.LOG_HOLD_CATCH_UP_TAIL.split(" -- ", 1)[1]):
        assert _battle_text(whole), whole
    # the spliced words, pinned as the C# EXPRESSION that writes them -- a bare 'held impact' is in ~20 comment lines of
    # the patch, so a reworded literal would never turn a bare-word pin red (fix pass: harness-8)
    head = lambda c: c.split("hold: ")[1]                               # noqa: E731
    for quoted in (f'(queued ? "{head(BW.LOG_HOLD_QUEUED_FRAME)}" : "{head(BW.LOG_HOLD_HELD_IMPACT)}")',
                   f'+ "{BW.LOG_HOLD_RELEASED_VIA}" + via +',
                   f'(h.Queued ? "{head(BW.LOG_HOLD_FIRST_QUEUED)}" : "{head(BW.LOG_HOLD_FIRST_HELD)}")',
                   f'(superseded ? "{BW.LOG_HOLD_SUPERSEDED}" : "")',
                   f'+ "{BW.LOG_HOLD_CATCH_UP_PIECE}" + _actSkippedSeq[i] + ") re-applied at "',
                   # [fix pass: rtiming-1] the release line battlewire.parse_hold_release reads, piece by piece in order
                   '(r != null ? " of id " + r.Id : "")',
                   f'+ " on wire slot " + slot + "{BW.LOG_HOLD_RELEASED_VIA}" + via + " after " + heldMs + " ms of battle '
                   f'time"',
                   '+ (lag != Int32.MinValue ? " (lag " + lag + " ms"'):
        assert _battle_text(quoted), quoted
    # ...and the parser reads the line exactly as the engine (and the stand-in's twin) writes it, Memoria.log prefix kept
    line = (f"16.10.2026 12:00:00 |M| {BW.LOG_HOLD_HELD_IMPACT} of id 12 on wire slot 5{BW.LOG_HOLD_RELEASED_VIA}timeout "
            f"after 2516 ms of battle time{BW.LOG_HOLD_SUPERSEDED}")
    assert BW.parse_hold_release(line) == {"queued": False, "id": 12, "slot": 5, "via": "timeout", "held_ms": 2516,
                                           "lag": None, "superseded": True}
    assert BW.parse_hold_release(f"{BW.LOG_HOLD_QUEUED_FRAME} on wire slot 0{BW.LOG_HOLD_RELEASED_VIA}end-inject after 0 ms "
                                 f"of battle time") == {"queued": True, "id": None, "slot": 0, "via": "end-inject",
                                                        "held_ms": 0, "lag": None, "superseded": False}
    assert BW.parse_hold_release(f"{BW.LOG_HOLD_HELD_IMPACT} of id 3 on wire slot 4{BW.LOG_HOLD_RELEASED_VIA}late after 0 "
                                 f"ms of battle time (lag -40 ms{BW.LOG_HOLD_HIT_FIRST})")["lag"] == -40
    assert BW.parse_hold_release(BW.LOG_HOLD_FLUSH + "1 held impact(s)") is None and BW.parse_hold_release("") is None
    # the spliced ones: each piece one literal (the engine's own line breaks)
    for pieces in (("OFF -- CALIBRATION: the pre-s135 guest (numbers, the flinch and ", "deaths land when the host's "
                    "impact ARRIVES)"),
                   ("[NetSync] harness: action replay life-mask skip ", "OFF -- CALIBRATION: the reconciler applies a held "),
                   (BW.LOG_HOLD_FIRST_TAIL[:BW.LOG_HOLD_FIRST_TAIL.index(" the bars")],),
                   ("frame(s) at once (the legacy path: every kill lands before the end presentation reads the party; "
                    "logged once per boot)",)):
        for piece in pieces:
            assert _battle_text(piece), piece
    assert _battle_text('"[NetSync] harness: action replay hold " + (off ? "OFF -- CALIBRATION: the pre-s135 guest ('
                        'numbers, the flinch and "')
    assert BW.LOG_HOLD_ON.endswith("hold ON") and BW.LOG_LIFESKIP_ON.endswith("skip ON")


#: the s135 hook sites (a file, then the lines in order inside s135's own patch: code lines, comments dropped)
HOLD_HOOKS = {
    "UnifiedBattleSequencer.cs": [("if (!btl2dParam.TryGetValue(btl, out Btl2dParam figParam))", "continue;",
                                   "if (Memoria.Netsync.NetSyncDiorama.ActLive)",
                                   "Memoria.Netsync.NetSyncDiorama.ActNoteFigure(cmd, btl, figParam);",
                                   "btl2d.Btl2dReq(btl, figParam);")],
    "NetSyncDiorama.cs": [
        ("Array.Clear(_gateSeq, 0, _gateSeq.Length);", "ActHoldClear();", "ActHoldResetCounters();"),
        ("Array.Clear(_gateSeq, 0, _gateSeq.Length);", "ActHoldClear();", "BootedWireNonce = -1;"),
        ("Array.Clear(_gateSeq, 0, _gateSeq.Length);", "ActHoldClearSeq();"),
        ("_gated[u.Index] = false;", "}", "if (_actLifeMask != 0 && ActLifeSkipNow(ref u, seq))", "return;",
         "BTL_DATA d = ResolveWireUnit(b, u.Index, u.IsPlayer);"),
        ('LogUnresolvedWireUnit(u.Index, "reconcile");', "return;", "}", "ActSampleApplied(u.Index, seq);",
         "Boolean hasDeath = (d.stat.cur & BattleStatus.Death) != 0;"),
        ("Boolean covered = paired != null && paired.CoversSwing;", "if (paired != null)", "{", "_actPaired++;"),
        ("if (ActHoldIntake(b, ref a, dT, dC, selfCast, paired, backlog))", "return;",
         "ApplyActionFrameNow(b, ref a, dT, dC, selfCast, covered, backlog, ActViaArrival, _actNowMs, false, 0);", "}"),
        ("if (ActEndInjectFlushes(ours, e.Kind))", 'ActHoldFlush("end-inject");',
         "Boolean allDown = e.Kind == NetSyncEnd.KDefeat && AllPlayersDown(b);"),
        ("private static void InjectEnd(FF9StateBattleSystem b, NetSyncBattle.PeerEnd e, Int32 action, Boolean allDown)",
         "{", 'ActHoldFlush("end-inject");'),
        ("if (applyT && ActReleaseArmsGrace(lethalT, a.CasterIsPlayer, a.TargetIsPlayer, backlog, via,",
         "deferred && (EndHudOff || LeaveRequestedRecently)))", 'ActArmDeathGrace(dT, true, "impact");')],
    "NetSyncDiorama.Replay.cs": [
        ('Log.Error("[NetSync] action replay tick failed (logged once per boot; the teardown still discards every '
         'replay): " + ex);', "}", "}", "ActHoldTick();", "}"),
        ("ActRecomputeLive();", 'ActHoldReleaseRec(r, "end");'),
        ("ActHoldReleaseRec(r, ActDeclineVia(why));",),
        ('ActHoldReleaseRec(r, "declined");',),
        ("ActRecomputeLive();", 'ActHoldReleaseRec(r, "abort");', "_actAborted++;"),
        ("internal static void ActDiscardAll(String why)", "{", "ActHoldDiscardAll(why);"),
        ("if (master != null)", "ActHoldOnHit(r, master, target, sfxThread != null && !r.NoShortCircuit);",
         "return !r.NoShortCircuit;"),
        ("_benchHoldOff = false;", "_benchLifeSkipOff = false;")],
    "NetSyncClient.cs": [("Boolean holdOk = NetSyncDiorama.ActHoldSelfTest(out holdDetail);",)],
}


def test_the_hold_hooks_sit_at_the_audits_sites():
    """Each s135 hook at its audited site, read off s135's own patch (code lines, comments dropped, in order): the one
    stock edit -- EffectPoint's Figure tap, read-only behind ActLive, right before the stock Btl2dReq -- and nothing else
    in a stock file; the three B3.5 reset sites (the boot block with the counters, Boot's catch, ForceDisarm's seqs);
    ApplyUnit's life-mask skip AFTER the horizon gate and BEFORE the resolve (the whole record, D04); the paired accounting
    BEFORE the intake; EndTick's flush at the injection branch's head BEFORE AllPlayersDown (amendment 2) and InjectEnd's
    head; the death grace only for an APPLIED lane (and only while a replay can follow: the fix pass); ActTick's hold step
    LAST and OUTSIDE its try (the fix pass); ApplyUnit's stamp right after the resolve (the fix pass); the record releases;
    the teardown's discard FIRST; the hit release inside ActOnHit's own short-circuit; the levers in ActBenchRelease; the
    proof line."""
    s135 = _patch_bytes("s135")
    for file_name, sites in HOLD_HOOKS.items():
        new = [c for c in (_strip_comment(t) for _h, _k, t in _new_side(file_name, s135)) if c]
        for site in sites:
            at = next((k for k in range(len(new)) if new[k:k + len(site)] == list(site)), None)
            assert at is not None, (file_name, site[0])
    files = {p.replace("\\", "/").rsplit("/", 1)[-1] for p, _sec in msr.sections(s135) if p}
    assert files == {"UnifiedBattleSequencer.cs", "HarnessAgent.cs", "NetSyncClient.cs", "NetSyncDiorama.Replay.cs",
                     "NetSyncDiorama.cs"}, files
    ubs = [c for c in (_strip_comment(t) for _h, k, t in _new_side("UnifiedBattleSequencer.cs", s135) if k == "+") if c]
    assert ubs == ["if (Memoria.Netsync.NetSyncDiorama.ActLive)",
                   "Memoria.Netsync.NetSyncDiorama.ActNoteFigure(cmd, btl, figParam);"], ubs
    assert all(any(d.endswith("/" + f) for d in msr.DEFAULT_FILES) for f in files), files   # (no new file to replay)
    # D01: the per-slot array is _actAppliedSeq (never the reconciler's scalar _lastAppliedSeq, which it would collide with)
    assert _battle_text("private static readonly UInt16[] _actAppliedSeq = new UInt16[8];")
    assert not any("_lastAppliedSeq[" in ln for ln in _stack_text(REPLAY_FILE) + _stack_text("NetSyncDiorama.cs"))
    # amendment 12: the mask is cleared FIRST in the discard (before any list is touched)
    disc = _cs_block(REPLAY_FILE, "private static void ActHoldDiscardAll(", "}")
    assert [c for c in (_strip_comment(t) for t in disc) if c][2] == "_actLifeMask = 0;", disc


# ---- [ff9mapkit netsync s135] the hold's model: the stand-in end to end through the driver, then battlewire.ActHoldLane on
# the rules no stand-in battle reaches (a lane rig: eight units, the bench feed, the stand-in's tick order)
def _hold_impact(act_id, *, caster: int = 0, target: int = 4, fig: int = 4321, hp: int = 300, mp: int = 0,
                 cast_hp: int = 420, cast_mp: int = 30, player_caster: bool = True, player_target: bool = False,
                 dmg: bool = True, seq: int = 5, fig_c: int = 0, stat_tick: bool = False, nonce: int = 0x77) -> bytes:
    """An impact naming ``act_id`` (None = a 46-byte old-host one): an HP figure with its info bit (EffectPoint collects
    info != 0 only), the host's raws, DmgMot when ``dmg``."""
    flags = (1 if dmg else 0) | (32 if player_target else 0) | (64 if player_caster else 0) | (
        BW.ACT_FLAG_STAT_TICK if stat_tick else 0)
    return BW.encode_action_impact(nonce, seq, caster, target, fig_t=(1 if fig else 0, fig, 0),
                                   fig_c=(1 if fig_c else 0, fig_c, 0), raws=(hp, mp, cast_hp, cast_mp), flags=flags,
                                   cmd_no=BW.CMD_ATTACK_ID, sub_no=BW.ABILITY_ATTACK_ID, act_id=act_id)


def _hold_dio(game):
    """A stand-in for the hold's end-to-end tests: s134's diorama rig with the replay's hit LATER (60 of 90 frames -- the
    lane's frames are the stand-in's shapes), so the driver reads the held state before the hit."""
    fake = _rep_dio(game)
    fake._act_guest.HIT_FRAME, fake._act_guest.REPLAY_FRAMES = 60, 90
    return fake


def test_the_stand_in_holds_an_impacts_figure_and_flinch_for_its_replays_hit(game):
    """Leg 1 on the stand-in: a START and a non-lethal impact naming it in ONE feed -- the target's raw HP follows the
    host at once (the owner's rule: the bars), the impact HELD (held_now 1), NO figure and no flinch until the replay's
    hit; at the hit it releases `hit` (lag >= 0), the figure shown at the Figure point (figs[] via "hit", at the display),
    the flinch after; `hold off` = the pre-s135 guest (the figure via "arrival" and the flinch at once)."""
    fake = _hold_dio(game)
    with session(game, fake) as g:
        st = _dio(g, fake)
        assert st.coop_act_hold_on is True and st.coop_act_hold_held_now == 0
        st = g.act_feed([_rep_start(1), _hold_impact(1, hp=300)])
        st = _rep_until(g, lambda s: s.coop_act_hold_held_now == 1, "the impact held")
        assert st.unit("Masked Man")["hp_raw"] == 300 and st.coop_act_hold_figs == [] and st.unit_mot(4) != BW.MP_DAMAGE1
        assert st.coop_act_guest_last["first_hit_ms"] < 0 and st.coop_act_hold_life_mask == 0
        st = _rep_until(g, lambda s: s.coop_act_hold_rel_hit == 1, "the hit release")
        hit_ms = st.coop_act_guest_last["first_hit_ms"]
        assert hit_ms >= 0 and st.coop_act_hold_held_now == 0 and st.coop_act_hold_lag_n == 1
        assert st.coop_act_hold_lag_min >= 0 and st.unit_mot(4) == BW.MP_DAMAGE1             # the flinch: AFTER the hit
        st = _rep_until(g, lambda s: s.coop_act_hold_figs, "the Figure point")
        (fig,) = st.coop_act_hold_figs
        assert (fig["slot"], fig["value"], fig["via"]) == (4, 4321, "hit") and fig["release_ms"] >= hit_ms
        assert BW.act_hold_at_rest(_rep_until(g, lambda s: s.coop_act_guest_running == 0, "the end").coop_act_hold_block)
        g.act_hold(False)
        g.act_feed([_rep_start(2), _hold_impact(2, hp=250, fig=5135)])
        st = _rep_until(g, lambda s: len(s.coop_act_hold_figs) == 2, "the arrival figure")
        assert st.coop_act_hold_figs[-1]["via"] == BW.ACT_VIA_ARRIVAL and st.coop_act_guest_last["first_hit_ms"] < 0
        assert st.coop_act_hold_held == 1 and st.unit_mot(4) == BW.MP_DAMAGE1                # at ARRIVAL: the red
    assert _mlog_lines(fake, BW.LOG_HOLD_FIRST_HELD) and _mlog_lines(fake, f"{BW.LOG_HOLD_RELEASED_VIA}hit after ")
    assert _mlog_lines(fake, BW.LOG_HOLD_OFF)


def test_the_stand_in_masks_a_held_kill_from_the_reconciler_until_the_hit(game):
    """Leg 2 on the stand-in: a held LETHAL impact sets the life mask; `unit 4 dead` (a post-horizon type-1 record through
    ApplyUnit) is SKIPPED -- alive until the hit, then dead, the mask 0; with `lifeskip off` the same record kills AT THE
    OP (the life-skip's own red), while the impact is still held."""
    for lifeskip in (True, False):
        fake = _hold_dio(game)
        with session(game, fake) as g:
            _dio(g, fake)
            if not lifeskip:
                g.actbench("lifeskip", "off")
            g.act_feed([_rep_start(1), _hold_impact(1, hp=0)])
            st = _rep_until(g, lambda s: s.coop_act_hold_life_mask == 0x10, "the held kill")
            assert st.unit("Masked Man")["alive"] is True and st.coop_act_hold_held_now == 1
            st = g.act_unit(4, "dead")
            if lifeskip:
                assert st.unit("Masked Man")["alive"] is True and st.coop_act_hold_mask_skips == 1
                st = _rep_until(g, lambda s: s.coop_act_hold_rel_hit == 1, "the hit")
                assert st.unit("Masked Man")["alive"] is False and st.unit_die_seq(4) == 5 and st.coop_act_hold_life_mask == 0
            else:
                assert st.unit("Masked Man")["alive"] is False and st.coop_act_hold_mask_skips == 0
                assert st.coop_act_hold_held_now == 1 and st.coop_act_guest_last["first_hit_ms"] < 0
        words = BW.LOG_HOLD_UNIT_SKIPPED if lifeskip else BW.LOG_HOLD_UNIT_APPLIED
        assert _mlog_lines(fake, words), lifeskip
    assert _mlog_lines(fake, BW.LOG_LIFESKIP_OFF)


def test_the_end_injection_releases_a_held_kill_before_the_party_is_read(game):
    """Amendment 2 on the stand-in, the VICTORY half: a held lethal impact on the diorama's ENEMY, then the host's
    victory: EndTick's injection branch releases it `end-inject` (rel_end_inject 1, the 'end injection released' line)
    before the injection -- nothing held survives it, the mask 0. (A victory never reads AllPlayersDown, so this test
    cannot see the flush's ORDER: the defeat test below pins it -- review rharness-1.)"""
    fake = _hold_dio(game)
    with session(game, fake) as g:
        _dio(g, fake)
        g.act_feed([_rep_start(1), _hold_impact(1, hp=0)])
        _rep_until(g, lambda s: s.coop_act_hold_life_mask == 0x10, "the held kill")
        g.netsync("endbench", "victory")
        st = _rep_until(g, lambda s: s.coop_act_hold_rel_end_inject == 1, "the end-inject release")
        assert st.unit("Masked Man")["alive"] is False and st.coop_act_hold_life_mask == 0
        assert st.coop_act_hold_held_now == 0
    assert len(_mlog_lines(fake, BW.LOG_HOLD_FLUSH)) == 1


def _hold_defeat_run(game, *, hold: bool = True) -> tuple:
    """The stand-in's DEF shape (review rharness-1): Vivi down on ARRIVAL (an impact naming NO START -- nothing held, the
    arrival path), then the enemy's replay on Zidane -- the LAST player standing -- with a LETHAL impact (held while the
    hold is on: the mask has his bit, he still stands), then `endbench phase-defeat` (the host's PHASE_DEFEAT). -> (the
    injected state, the Memoria.log lines THIS run wrote -- the log is the game dir's, shared by every run here)."""
    fake = _hold_dio(game)
    log = lambda: fake.memoria_log.read_text(encoding="utf-8").splitlines() if fake.memoria_log.exists() else []  # noqa: E731
    before = len(log())
    with session(game, fake) as g:
        _dio(g, fake)
        if not hold:
            g.act_hold(False)
        g.act_feed(_hold_impact(99, caster=4, target=1, fig=0, hp=0, mp=0, cast_hp=11200, cast_mp=0, player_caster=False,
                                player_target=True, seq=5))
        st = _rep_until(g, lambda s: s.unit("Vivi")["alive"] is False, "Vivi down on arrival")
        assert (st.coop_act_hold_held, st.coop_act_hold_queued, st.unit("Zidane")["alive"]) == (0, 0, True)
        g.act_feed([_rep_start(1, actor=4, player=False, tar=0x01),
                    _hold_impact(1, caster=4, target=0, fig=5149, hp=0, mp=0, cast_hp=11200, cast_mp=0,
                                 player_caster=False, player_target=True, seq=6)])
        if hold:
            st = _rep_until(g, lambda s: s.coop_act_hold_life_mask == 0x01, "the held kill on the last player")
            assert st.unit("Zidane")["alive"] is True and st.coop_act_hold_held_now == 1
            assert st.coop_act_guest_last["first_hit_ms"] < 0              # (the replay's hit is 60 frames out)
        else:
            st = _rep_until(g, lambda s: s.unit("Zidane")["alive"] is False, "the kill at ARRIVAL")
        g.netsync("endbench", "phase-defeat")
        st = g.wait_for(lambda s: s.coop_present_injected, timeout=4.0, what="the injection")
    lines = log()
    return st, (lines[before:] if len(lines) >= before else lines)


def test_the_end_inject_flush_lands_a_held_kill_before_all_players_down_is_read(game, monkeypatch):
    """Amendment 2's ORDER on the stand-in (review rharness-1; the bench's DEF). A held kill on the last player standing,
    then the host's PHASE_DEFEAT: EndTick's flush releases it `end-inject` BEFORE AllPlayersDown reads the party, so the
    party reads DOWN -- "annihilate" WITH the stock settle (MENU_OFF / SEQ_MENU_OFF_DEFEAT), rel_end_inject 1, Zidane dead,
    nothing held. It CAN fail: with EndTick's flush gone -- the flush moved below the AllPlayersDown read, InjectEnd's head
    then the ONLY flush (an InjectEnd-only path: it still releases the kill `end-inject`, the party dead after it) -- EndTick
    read Zidane STANDING and passed that to InjectEnd, so the same run injects the defeat TAIL (PHASE_DEFEAT / SEQ_DEFEAT
    CLOSE_FADEOUT: the settle skipped); and under `hold off` the kill lands at arrival (the settle again, but held 0 and
    rel_end_inject 0: a different red)."""
    flushes = lambda lines: [ln for ln in lines if BW.LOG_HOLD_FLUSH in ln]          # noqa: E731
    st, lines = _hold_defeat_run(game)
    assert (st.coop_present_action, st.coop_present_inject_phase, st.coop_present_inject_seq) == (
        "annihilate", BW.PHASE_MENU_OFF, BW.SEQ_MENU_OFF_DEFEAT)
    assert (st.coop_act_hold_held, st.coop_act_hold_rel_end_inject, st.coop_act_hold_held_now,
            st.coop_act_hold_life_mask) == (1, 1, 0, 0)
    assert st.unit("Zidane")["alive"] is False and st.unit("Vivi")["alive"] is False
    assert st.coop_act_hold_rel_hit == 0 and st.coop_act_guest_last["first_hit_ms"] < 0   # released BY the injection
    released = [p for p in map(BW.parse_hold_release, lines) if p is not None]
    assert len(flushes(lines)) == 1 and [(p["id"], p["slot"], p["via"], p["queued"]) for p in released] == [
        (1, 0, "end-inject", False)], released
    # THE MUTANT: the flush below the AllPlayersDown read (EndTick's gone; InjectEnd's head the only flush)
    with monkeypatch.context() as m:
        m.setattr(BW, "act_end_inject_flushes", lambda ours, kind: False)
        st, lines = _hold_defeat_run(game)
    assert (st.coop_present_action, st.coop_present_inject_phase, st.coop_present_inject_seq) == (
        "annihilate", BW.PHASE_DEFEAT, BW.SEQ_DEFEATCLOSE_FADEOUT), "the order red never came"
    assert (st.coop_act_hold_held, st.coop_act_hold_rel_end_inject, st.coop_act_hold_held_now,
            st.coop_act_hold_life_mask) == (1, 1, 0, 0)                # InjectEnd's own flush released it
    assert st.unit("Zidane")["alive"] is False and len(flushes(lines)) == 1
    # `hold off`: the pre-s135 guest -- the kill at arrival (the settle), nothing held, nothing released at the end
    st, lines = _hold_defeat_run(game, hold=False)
    assert (st.coop_present_action, st.coop_present_inject_phase, st.coop_present_inject_seq) == (
        "annihilate", BW.PHASE_MENU_OFF, BW.SEQ_MENU_OFF_DEFEAT)
    assert (st.coop_act_hold_held, st.coop_act_hold_rel_end_inject) == (0, 0) and not flushes(lines)


def test_reset_releases_the_hold_levers(game):
    """HarnessReleaseBench's s135 half (audit 4.5): `hold off` and `lifeskip off` left set, then `reset`: the 'hold levers
    back' line once, and re-read WITH a fresh selftest role both levers at rest -- while s134's levers come back too."""
    fake = _rep_dio(game)
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(FIELD)
        g.netsync("selftest", 1)
        for args in (("hold", "off"), ("lifeskip", "off"), ("replay", "off")):
            g.actbench(*args)
        st = g.state
        assert (st.coop_act_hold_on, st.coop_act_hold_lifeskip, st.coop_act_guest_why) == (False, False, "lever")
        g.send("reset")
        g.wait_for(lambda s: s.netsync is not None and not s.netsync["forced"], timeout=10.0, what="the release")
        st = g.netsync("selftest", 1)
        assert (st.coop_act_hold_on, st.coop_act_hold_lifeskip, st.coop_act_guest_on) == (True, True, True)
    assert len(_mlog_lines(fake, BW.LOG_HOLD_LEVERS_BACK)) == 1 and len(_mlog_lines(fake, BW.LOG_REPLAY_LEVERS_BACK)) == 1


class _HoldRig(_LaneRig):
    """s134's lane rig with the hold on (an s135 lane) and units that carry raw HP / MP."""

    def __init__(self, frames: int = 10 ** 6):
        units = [dict(u, hp_raw=500, hp=500, hp_max=600, hp_max_raw=600, mp=10) for u in _lane_units()]
        super().__init__(units, frames)
        self.lane.with_hold_fn = True

    @property
    def hold(self) -> dict:
        return self.lane.doc(role=True, booted=True)["hold"]

    def unit(self, slot: int) -> dict:
        return next(u for u in self.units if u["slot"] == slot)


def test_the_hold_lane_releases_each_impact_by_one_reason():
    """battlewire.ActHoldLane on the releases no stand-in battle reaches, each through the engine's own path: `end` (the
    replay ended without hitting that target), `timeout` (2500 ms), `hostdone` (the END + 1500 ms, first), `late` (the
    replay's credit: at once, a negative lag), `abort` (an abort-all), `replaced` (a newer START superseded the parked one,
    amendment 9), `declined` (a NOOP START); every held impact counted once (act_hold_at_rest)."""
    rig = _HoldRig(frames=30)                                           # ends: the replay hits its caster only
    rig.step()
    rig.feed(_rep_start(1, tar=0x01), _hold_impact(1, fig=11))
    rig.step(40)
    h = rig.hold
    assert (h["rel_end"], h["figs"][-1]["via"], h["figs"][-1]["value"]) == (1, "end", 11) and BW.act_hold_at_rest(h)
    rig = _HoldRig()                                                    # never ends: the timeout
    rig.step()
    rig.feed(_rep_start(1, tar=0x01), _hold_impact(1, fig=12))
    rig.step(BW.ACT_HOLD_TIMEOUT_MS // 33)
    assert rig.hold["held_now"] == 1
    rig.step(2)
    f = rig.hold["figs"][-1]
    assert rig.hold["rel_timeout"] == 1 and f["via"] == "timeout" and BW.ACT_HOLD_TIMEOUT_MS <= f["release_ms"] - \
        f["arrival_ms"] <= BW.ACT_HOLD_TIMEOUT_MS + 33
    rig = _HoldRig()                                                    # the host's END first: host-done
    rig.step()
    rig.feed(_rep_start(1, tar=0x01), _hold_impact(1, fig=13))
    rig.step(3)
    rig.feed(BW.encode_action_end(0x77, 9, 1, BW.CMD_ATTACK_ID, BW.ABILITY_ATTACK_ID))
    rig.step(BW.ACT_HOLD_HOST_DONE_MS // 33 + 2)
    f = rig.hold["figs"][-1]
    assert rig.hold["rel_hostdone"] == 1 and f["via"] == "hostdone" and f["release_ms"] - f["arrival_ms"] < 1700
    rig = _HoldRig()                                                    # late: the hit first, then the impact
    rig.step()
    rig.feed(_rep_start(1))
    rig.step(20)
    assert rig.lane.hits == 1
    rig.feed(_hold_impact(1, fig=14))
    rig.step()
    h = rig.hold
    assert (h["rel_late"], h["held"], h["figs"][-1]["via"]) == (1, 1, "late") and h["lag"]["min"] < 0
    rig.lane.abort_all("clear", ctx=rig.ctx())
    rig.feed(_rep_start(2), _hold_impact(2, fig=15, hp=0, seq=6))      # abort: an abort-all hard-releases (a NEWER seq)
    rig.step()
    assert rig.hold["life_mask"] == 0x10
    rig.lane.abort_all("leave", ctx=rig.ctx())
    h = rig.hold
    assert (h["rel_abort"], h["life_mask"], rig.unit(4)["alive"]) == (1, 0, False) and h["figs"][-1]["via"] == "abort"
    rig = _HoldRig()                                                    # replaced: A runs, B parks, C supersedes B
    rig.step()
    rig.feed(_rep_start(1))
    rig.step()
    rig.feed(_rep_start(2), _hold_impact(2, target=5, fig=16))
    rig.step()
    assert rig.hold["held_now"] == 1 and rig.lane.book.queue[0].state == BW.ACT_ST_WAITING
    rig.feed(_rep_start(3))
    rig.step()
    h = rig.hold
    assert (h["rel_replaced"], h["held_now"], h["figs"][-1]["via"], rig.lane.superseded) == (1, 0, "replaced", 1)
    rig = _HoldRig()                                                    # declined: a NOOP START's impacts apply now
    rig.step()
    rig.feed(_rep_start(1, kind=BW.VFX_KIND_NONE, num=0), _hold_impact(1, fig=17))
    rig.step()
    h = rig.hold
    assert (h["rel_declined"], rig.lane.noop, h["figs"][-1]["via"]) == (1, 1, "declined") and BW.act_hold_at_rest(h)


def test_the_hold_lane_supersedes_an_older_kill_and_queues_behind_a_held_change():
    """THE SUPERSEDED GUARD as amendment 6 rewrote Leg 8: an older held kill and a newer held change on one slot; the newer
    replay hits first (stamping the slot), so the kill's later timeout release is SKIPPED (superseded 1, its figure
    shown, the unit alive). AMENDMENT 5: a stat tick and an unpaired impact on a slot with a held life change QUEUE behind
    it (FIFO; an unrelated slot applies at once) and release after the hit, `queued`; the teardown DISCARDS what is held."""
    rig = _HoldRig()
    rig.step()
    rig.feed(_rep_start(1, actor=1, tar=0x20), _rep_start(2, tar=0x10),
             _hold_impact(1, caster=1, fig=21, hp=0, seq=10), _hold_impact(2, fig=22, hp=333, seq=11, dmg=False))
    rig.step()
    h = rig.hold
    assert (h["held_now"], h["life_mask"]) == (2, 0x10)                 # the newer change waits too: its slot is busy
    rig.step(20)                                                        # replay 2's hit on 4 (replay 1 hits 5 only)
    assert rig.hold["rel_hit"] == 1 and rig.unit(4)["hp_raw"] == 333 and rig.unit(4)["alive"]
    rig.step(BW.ACT_HOLD_TIMEOUT_MS // 33)
    h = rig.hold
    assert (h["rel_timeout"], h["superseded"], rig.unit(4)["alive"]) == (1, 1, True)
    assert [f["via"] for f in h["figs"] if f["value"] in (21, 22)] == ["hit", "timeout"]
    rig = _HoldRig()
    rig.step()
    tick = BW.encode_action_impact(0x77, 13, 0xFF, 4, fig_t=(1, 7, 0), raws=(480, 0, 0, 0), flags=BW.ACT_FLAG_STAT_TICK)
    rig.feed(_rep_start(1), _hold_impact(1, fig=31, hp=0, seq=12), tick,
             _hold_impact(99, target=5, fig=32, hp=444, seq=14), _hold_impact(98, target=4, fig=33, hp=470, seq=15))
    rig.step()
    h = rig.hold
    assert (h["held_now"], h["queued_now"], h["queued"], rig.unit(5)["hp_raw"]) == (1, 2, 2, 444)
    assert [f["value"] for f in h["figs"]] == [32] and h["life_mask"] == 0x10
    rig.step(20)
    h = rig.hold
    assert (h["rel_hit"], h["rel_queued"], h["queued_now"]) == (1, 2, 0) and BW.act_hold_at_rest(h)
    # the kill at the hit (its figure at the Figure point, four frames on), then the queue in arrival order: the tick (a
    # newer frame: it applies -- standing the unit up at 480) and the impact behind it (newer still: 470)
    assert [(f["value"], f["via"]) for f in h["figs"]] == [(32, "arrival"), (7, "queued"), (33, "queued"), (31, "hit")]
    assert rig.unit(4)["hp_raw"] == 470 and rig.unit(4)["alive"] is True and h["superseded"] == 0
    rig = _HoldRig()
    rig.step()
    rig.feed(_rep_start(1), _hold_impact(1, fig=41, hp=0), _hold_impact(97, fig=42, hp=10, seq=30))
    rig.step()
    rig.lane.discard_all("teardown (bench)")
    h = rig.hold
    assert (h["discarded"], h["life_mask"], h["held_now"], h["queued_now"], rig.unit(4)["alive"]) == (2, 0, 0, 0, True)
    assert not [f for f in h["figs"] if f["value"] in (41, 42)]


def test_the_hold_lane_keeps_its_caps_and_the_full_list_applies():
    """The caps: a full hold list (ACT_HOLD_CAP) applies a frame on arrival (never dropped); figs[] keeps the last 16;
    the release lines stop at ACT_HOLD_LOG_MAX with one 'further releases' line; the credits cap per replay; the first
    hold logs once per boot."""
    rig = _HoldRig()
    rig.step()
    for k in range(BW.ACT_HOLD_CAP + 3):                                # one record: 67 impacts on it
        rig.feed(*([_rep_start(1)] if k == 0 else []), _hold_impact(1, target=4 + k % 4, fig=100 + k, dmg=False))
    rig.step()
    h = rig.hold
    over = list(range(100 + BW.ACT_HOLD_CAP, 100 + BW.ACT_HOLD_CAP + 3))      # past the cap: applied on ARRIVAL
    assert h["held_now"] == BW.ACT_HOLD_CAP and [(f["value"], f["via"]) for f in h["figs"]] == [
        (v, BW.ACT_VIA_ARRIVAL) for v in over]
    rig.lane.abort_all("clear", ctx=rig.ctx())
    h = rig.hold
    assert h["rel_abort"] == BW.ACT_HOLD_CAP and BW.act_hold_at_rest(h) and len(h["figs"]) == BW.ACT_HOLD_FIGS_MAX == 16
    assert [f["value"] for f in h["figs"]] == list(range(100 + BW.ACT_HOLD_CAP - 16, 100 + BW.ACT_HOLD_CAP))
    lines = [ln for ln in rig.lane.lines if ln.startswith(BW.LOG_HOLD)]
    assert sum(BW.LOG_HOLD_RELEASED_VIA in ln for ln in lines) == BW.ACT_HOLD_LOG_MAX
    assert sum(ln == BW.LOG_HOLD_FURTHER for ln in lines) == 1
    assert sum(ln.startswith(BW.LOG_HOLD_FIRST_HELD) for ln in lines) == 1
    r = BW.ActRec(1, 0x77, 0)
    for i in range(BW.ACT_HOLD_CREDIT_CAP + 5):
        BW.act_credit_add(r, 0x10, i)
    assert len(r.hold_credit_units) == BW.ACT_HOLD_CREDIT_CAP and BW.act_credit_take(r, BW.act_credit_find(r, 0x10)) == 0
    assert BW.act_lag_p50([9, -3, 4, 120]) == 4 and BW.act_lag_p50([]) == -1


def test_the_hold_lane_s134_shape_is_untouched_without_the_rung():
    """An s134 lane (with_hold False, the stand-in below `acthold`) keeps s134's model exactly: no `hold` key, nothing
    held, no state write, no figure -- the calibration engine is never the new one minus a key."""
    rig = _HoldRig()
    rig.lane.with_hold_fn = False
    rig.step()
    rig.feed(_rep_start(1), _hold_impact(1, hp=0))
    rig.step(20)
    doc = rig.lane.doc(role=True, booted=True)
    assert "hold" not in doc and rig.unit(4)["alive"] is True and rig.unit(4)["hp_raw"] == 500
    assert doc["paired"] == 1 and doc["swing_skipped"] == 1 and rig.lane.hold.held == []


def _unit_op(rig, slot: int, state: str) -> None:
    ok, why = rig.lane.bench(["actbench", "unit", str(slot), state], booted=True, role=True, ctx=rig.ctx())
    assert ok, why


def test_the_hold_lane_fix_pass_never_stands_up_a_corpse_and_catches_up_on_what_the_mask_skipped():
    """[s135 fix pass] battlewire.ActHoldLane on the review's findings. LIFE-1 / TIMING-2: a QUEUED frame's free caster lane
    whose unit a post-horizon record killed while it waited (`unit 1 dead`: not masked -- it STAMPS the slot) is
    SUPERSEDED at the drain: the unit stays dead, the queued release's line says so. STOCK-1: a hit inside EffectPoint's
    bracket leaves the queue for the next tick (the drain is due). LIFE-2: a held revive's dead record is SKIPPED and
    CACHED -- the end-inject flush revives, then re-applies it (dead before the party is read); a slot that leaves the mask
    by its hit catches up in the same steady tick. TIMING-1: a replay cut between its hit and its Figure point shows the
    collected figure at once (via `abort`)."""
    rig = _HoldRig()
    rig.step()
    rig.feed(_rep_start(1), _hold_impact(1, fig=51, hp=0, seq=10),
             _hold_impact(77, caster=1, fig=0, hp=0, cast_hp=444, seq=11, dmg=False))
    rig.step()
    h, hold = rig.hold, rig.lane.hold
    assert (h["held_now"], h["queued_now"], h["life_mask"]) == (1, 1, 0x10)     # the caster's slot 1: no life lane
    _unit_op(rig, 1, "dead")                                            # not masked: it kills AND stamps slot 1
    assert rig.unit(1)["alive"] is False and rig.hold["mask_skips"] == 0
    hold.on_hit(hold.held[0].rec, rig.unit(4), True)                    # the hit, INSIDE the bracket
    assert rig.hold["queued_now"] == 1 and hold.drain_due and rig.unit(4)["alive"] is False
    hold.tick(rig.ctx())                                                # the next tick: the drain
    h = rig.hold
    assert (h["queued_now"], h["rel_queued"], h["superseded"], rig.unit(1)["alive"]) == (0, 1, 1, False), h
    assert any(ln.startswith(BW.LOG_HOLD_QUEUED_FRAME) and ln.endswith(BW.LOG_HOLD_SUPERSEDED) for ln in rig.lane.lines)
    # LIFE-2 at the flush: dead player 2, a held revive (an enemy's START on her), her dead record skipped and cached
    for at_flush in (True, False):
        rig = _HoldRig()
        rig.unit(2).update(alive=False, hp_raw=0, hp=0)
        rig.step()
        rig.feed(_rep_start(1, actor=4, player=False, tar=0x04),
                 _hold_impact(1, caster=4, target=2, player_caster=False, player_target=True, hp=300, fig=61, dmg=False))
        rig.step()
        assert rig.hold["life_mask"] == 0x04 and rig.unit(2)["alive"] is False
        _unit_op(rig, 2, "dead")
        assert rig.hold["mask_skips"] == 1 and rig.lane.hold.skipped == {2: ("dead", 6)}
        if at_flush:
            rig.lane.hold.flush("end-inject", rig.ctx())
            why = "the end injection"
            assert rig.hold["rel_end_inject"] == 1
        else:
            for _ in range(40):
                rig.step()
                if rig.hold["rel_hit"]:
                    break
            why = "its release"
            assert rig.hold["rel_hit"] == 1
        assert rig.unit(2)["alive"] is False and rig.lane.hold.skipped == {} and rig.hold["life_mask"] == 0, why
        caught = [ln for ln in rig.lane.lines if ln.startswith(BW.LOG_HOLD_CATCH_UP) and BW.LOG_HOLD_CATCH_UP_PIECE in ln]
        assert caught == [f"{BW.LOG_HOLD_CATCH_UP}2{BW.LOG_HOLD_CATCH_UP_PIECE}6) re-applied at {why}"
                          f"{BW.LOG_HOLD_CATCH_UP_TAIL}"], caught
    # TIMING-1: a hit's figure collected, then the replay CUT before its Figure point -- shown at once, via `abort`
    rig = _HoldRig()
    rig.step()
    rig.feed(_rep_start(1), _hold_impact(1, fig=71, hp=480))
    for _ in range(40):
        rig.step()
        if rig.lane.hits:
            break
    assert rig.hold["rel_hit"] == 1 and rig.lane.hold.fig_pending and rig.hold["figs"] == []
    rig.lane.abort_all("clear", ctx=rig.ctx())
    assert [(f["value"], f["via"]) for f in rig.hold["figs"]] == [(71, "abort")] and not rig.lane.hold.fig_pending


# ---- [ff9mapkit netsync R3 fix round 2] the R3 benches' own logic, off the game: the T2 helper's self-check and the
# scenarios' calibration tables. Both ran only by hand (`py _coop_peer_bench.py`, a bench day), so an engine rewording
# that broke a matcher, or a predicted-red table that drifted from its docstring, waited for the owner's next launch.
# Collected here they run with the domain set and the nightly gate -- and still say nothing about the engine.
import importlib.util                                                   # noqa: E402
import os                                                               # noqa: E402
import subprocess                                                       # noqa: E402

SCENARIOS = REPO / "studies" / "test-harness" / "scenarios"


@lru_cache(maxsize=None)
def _peer_bench():
    """studies/test-harness/scenarios/_coop_peer_bench.py, loaded from its file under a private name -- never by putting
    the scenarios dir on this process's sys.path (~40 modules there a bare import could resolve to)."""
    spec = importlib.util.spec_from_file_location("_coop_peer_bench_under_test", SCENARIOS / "_coop_peer_bench.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_the_t2_bench_helpers_self_check_reads_no_red_row(monkeypatch, tmp_path):
    """The helper's own self-check, row by row: the ini guard, the matchers against the archived sitting-A guest log
    (where this checkout has it), the windows, the knobs, the tape facts and the leg plans on synthetic tapes. MEMORIA_SRC
    points NOWHERE: the shared clone moves with every session's in-flight engine work, so its wording rows would judge
    this branch by someone else's edits -- the stack twin below pins the same fragments off memoria-patches/. A missing
    source SKIPS its block as ONE row (never a pass of it, never a red here); every other row must run, and pass."""
    pb = _peer_bench()
    monkeypatch.setenv("MEMORIA_SRC", str(tmp_path / "no-clone"))
    monkeypatch.delenv("COOP_TAPE", raising=False)
    rows = pb._self_rows()
    bad = [w for ok, w in rows if ok is False]
    skipped = [w for ok, w in rows if ok is None]
    assert not bad, bad
    assert any("Memoria clone" in w for w in skipped), skipped           # the lever above took
    assert len(skipped) == 1 + (not SITTING_A_GUEST_LOG.exists()), skipped
    assert len(rows) - len(skipped) >= 50, f"only {len(rows) - len(skipped)} rows ran"   # 50 = neither source present


def test_the_t2_bench_helpers_engine_fragments_are_the_stacks_words():
    """Every GREEN matcher's literal pieces (_coop_peer_bench.FRAGMENTS, by C# file) are in a line the LIVE stack leaves
    in that file -- the self-check's clone rows, read off memoria-patches/ instead -- and every GREEN-only matcher has
    its pieces listed (a matcher with none could match words the engine no longer writes)."""
    pb = _peer_bench()
    assert set(pb.GREEN_ONLY) <= set(pb.FRAGMENTS) <= set(pb.MATCHERS), sorted(set(pb.GREEN_ONLY) ^ set(pb.FRAGMENTS))
    missing = {name: [f for f in frags if not any(f in ln for ln in _stack_text(fname))]
               for name, (fname, frags) in pb.FRAGMENTS.items()}
    assert not any(missing.values()), {k: v for k, v in missing.items() if v}


#: Run in a CHILD: each scenario puts its own dir on sys.path and reads its COOP_* knobs at import (a process-wide edit
#: this suite must not inherit). Prints the tables as JSON.
_SCENARIO_TABLES = r'''
import importlib.util, json, os, sys
scen, tools = sys.argv[1], sys.argv[2]
sys.path.insert(0, tools)
def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(scen, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m
hl, ch, sh, tr, ah, ar, hd, fb = (load(n) for n in ("coop_handback_live", "coop_cut_hold", "coop_battle_start_hold",
                                                      "coop_tape_record", "coop_action_host", "coop_action_replay",
                                                      "coop_action_hold", "coop_action_fallback"))
print(json.dumps({
    "hl": {"catalog": sorted(hl._catalog(True)), "old": sorted(hl.OLD_PREDICTED), "capture_s": hl.CAPTURE_S},
    "cut": {leg: {"catalog": sorted(ch._catalog(leg, True)),
                  "pred": {str(s): [sorted(x) for x in ch._predicted(leg, s)]
                           for s in (0, 117, 119, 120, 121, 131)},
                  "tail": {str(s): {str(tl): [sorted(x) for x in ch._predicted(leg, s, tl)] for tl in (0.0, 33.0, 67.0)}
                           for s in (119, 120, 121, 131)}}
            for leg in ch.PFX},
    "span_stall": {str(s): {str(tl): [sorted(x) for x in ch._predicted("span", s, tl, why="stall_cap")]
                            for tl in (0.0, 33.0, 67.0)} for s in (119, 120, 121, 131)},
    "hold_check": ch.HOLD_CHECK,
    "sh": {"catalog": sorted(sh._catalog(True)), "old": sorted(sh.OLD_PREDICTED), "lever": sorted(sh.LEVER_PREDICTED)},
    "tr": sorted(tr.CATALOG),
    "ah": {"catalog": sorted(ah._catalog(True)), "plain": sorted(ah._catalog(False)), "old": sorted(ah.OLD_PREDICTED),
           "lever": sorted(ah.LEVER_PREDICTED), "lane": sorted(ah.LANE_CHECKS), "probe": ah.PROBE, "scene": ah.SCENE,
           "group": ah.GROUP, "proof": ah.PROOF_OK, "doc": " ".join((ah.__doc__ or "").split())},
    "ar": {"catalog": sorted(ar._solo_catalog(True)), "plain": sorted(ar._solo_catalog(False)),
           "old": sorted(ar.OLD_PREDICTED), "lever": sorted(ar.LEVER_PREDICTED), "maybe": sorted(ar.LEVER_MAYBE),
           "guest": sorted(ar.GUEST_CHECKS), "probe": ar.PROBE, "host_probe": ar.HOST_PROBE, "scene": ar.SCENE,
           "group": ar.GROUP, "proof": ar.PROOF_OK, "leg": ar.LEG, "legs": list(ar.LEGS),
           "tape": sorted(ar._tape_catalog(True)), "tape_plain": sorted(ar._tape_catalog(False)),
           "tape_act": sorted(ar.TAPE_ACT), "tape_old": sorted(ar._tape_predicted(False)),
           "tape_knob": sorted(ar._tape_predicted(True)), "tape_dir": str(ar.act_tape_dir()),
           "values": ar.GUEST_VALUES, "doc": " ".join((ar.__doc__ or "").split())},
    "hd": {"catalog": sorted(hd._solo_catalog(True)), "plain": sorted(hd._solo_catalog(False)),
           "old": sorted(hd.OLD_PREDICTED), "lever": sorted(hd.LEVER_PREDICTED), "maybe": sorted(hd.LEVER_MAYBE),
           "hold": sorted(hd.HOLD_CHECKS), "probe": hd.PROBE, "guest_probe": hd.GUEST_PROBE, "scene": hd.SCENE,
           "group": hd.GROUP, "proof": hd.PROOF_OK, "leg": hd.LEG, "legs": list(hd.LEGS), "nonce": hd.NONCE,
           "replay_nonce": ar.NONCE, "figs": sorted(hd.FIG.values()), "boot1": list(hd.BOOT_1_LEGS),
           "tape": sorted(hd._tape_catalog(True)), "tape_plain": sorted(hd._tape_catalog(False)),
           "tape_hold": sorted(hd.TAPE_HOLD), "tape_old": sorted(hd._tape_predicted(False)),
           "tape_knob": sorted(hd._tape_predicted(True)), "doc": " ".join((hd.__doc__ or "").split())},
    "fb": {"catalog": sorted(fb._solo_catalog(True)), "plain": sorted(fb._solo_catalog(False)),
           "old": sorted(fb.OLD_PREDICTED), "lever": sorted(fb.LEVER_PREDICTED), "maybe": sorted(fb.LEVER_MAYBE),
           "fallback": sorted(fb.FALLBACK_CHECKS), "probe": fb.PROBE, "scene": fb.SCENE, "group": fb.GROUP,
           "proof": fb.PROOF_OK, "leg": fb.LEG, "legs": list(fb.LEGS), "nonce": fb.NONCE, "replay_nonce": ar.NONCE,
           "hold_nonce": hd.NONCE, "figs": sorted(fb.FIG.values()), "boot1": list(fb.BOOT_1_LEGS),
           "tape": sorted(fb._tape_catalog(True)), "tape_plain": sorted(fb._tape_catalog(False)),
           "tape_fb": sorted(fb.TAPE_FALLBACK), "tape_old": sorted(fb._tape_predicted(False)[0]),
           "tape_old_maybe": sorted(fb._tape_predicted(False)[1]), "tape_replay": sorted(fb._tape_predicted(True)[0]),
           "tape_replay_maybe": sorted(fb._tape_predicted(True)[1]), "doc": " ".join((fb.__doc__ or "").split()),
           "arc": sorted(fb._arc_catalog(True)), "arc_plain": sorted(fb._arc_catalog(False)),
           "arc_fb": sorted(fb.ARC_FALLBACK), "arc_old": sorted(fb._arc_predicted(False)[0]),
           "arc_new": sorted(fb._arc_predicted(True)[0]), "arc_maybe": sorted(fb._arc_predicted(False)[1]
                                                                             + fb._arc_predicted(True)[1]),
           "arc_tape": fb.ARC_TAPE_NAME, "arc_name": fb.pb.ARC_TAPE_NAME}}))
'''


@lru_cache(maxsize=None)
def _scenario_tables() -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("COOP_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    out = subprocess.run([sys.executable, "-c", _SCENARIO_TABLES, str(SCENARIOS), str(REPO / "tools")], env=env,
                         capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-2000:]
    return json.loads(out.stdout.strip().splitlines()[-1])


def test_the_r3_benches_predicted_reds_are_their_docstrings_and_their_own_checks():
    """The calibration tables COOP_CALIBRATE=1 judges against, pinned to what each docstring promises: coop_handback_live's
    s117 red set (P0 PROOF N2 D1-D3 L1 L2 B1 B2 S1 S2; S0/P1/P2/PRE/N1/T1 green), coop_cut_hold's per-leg, per-engine
    table, coop_battle_start_hold's two sets -- every predicted id one the leg's own catalog defines (a typo'd id is a
    red that can never come, so the -CAL verdict would read it "unseen" forever). All four modules import with no knob.
    [ff9mapkit netsync s131] coop_cut_hold's table now runs to s131 (RED only on every leg there: every G/K/X check
    passes only with s131), gains the `readopt` leg (the deployed s121 reds its G3 and X) and THE TAIL ADDS paragraph,
    whose one exception -- a stall_cap span's SPAN-G2, a maybe at any tail -- is pinned by hand [s131 fix]. [s131 cal] A
    TAIL-0 cut is a maybe too, not a green: the one-Update knife edge re-adopted in game (s119 @81.59 on s121: hold 2031
    vs outage 4015), so on s120/s121 (and s119 for the s119 leg) every leg's hold check is a maybe at tail 0."""
    t = _scenario_tables()
    hl = t["hl"]
    assert set(hl["old"]) == {f"S18-{c}" for c in ("P0", "PROOF", "N2", "D1", "D2", "D3", "L1", "L2", "B1", "B2", "S1",
                                                    "S2")}, hl["old"]
    assert set(hl["old"]) < set(hl["catalog"]) and set(hl["catalog"]) - set(hl["old"]) == {
        f"S18-{c}" for c in ("S0", "P1", "P2", "PRE", "N1", "T1", "CAL")}
    assert hl["capture_s"] >= 9.0                                        # a loaded machine stretched 6 s (review F6)

    def g(p, *n):
        return sorted(f"{p}-{x}" for x in n)

    want = {   # leg -> (the s117 reds, the s119 (reds, maybe)) -- s120/s121 read <P>-RED only (s121: from 121 on)
        "s119": (g("S119", "G1", "G2", "G3", "G4", "G5", "K"), (g("S119", "RED"), g("S119", "G3"))),   # [s131 cal] G3
        "s120-battle": (g("S120B", "G1", "G2", "G3", "G4", "G5", "K"),
                        (g("S120B", "G1", "G2", "G3", "G4", "G5", "K"), g("S120B", "RED"))),
        "s120-long": (g("S120L", "G1", "G2", "G3", "K"), (g("S120L", "G1", "G2", "G3", "K"), [])),
        "s120-roam": (g("S120R", "G1", "G2", "G3", "G4", "G5"), (g("S120R", "G1", "G2", "G3", "G4", "G5"), [])),
        "span": (g("SPAN", "G1", "G2", "K"), (g("SPAN", "G1", "G2", "K"), g("SPAN", "RED"))),
        "s121": (g("S121", "G0", "G1", "G2", "G4", "G5"), (g("S121", "G0", "G1", "G2", "G4", "G5"), [])),
        # [ff9mapkit netsync s131] the s119 cut moved to a tail >= 66 placement: s117 reds all of it (X and RED too: no
        # outage line, no key); s119 G3, X and RED (G2 maybe); s120/s121 G3 and X (G2 maybe) -- RED GREEN there (the
        # re-adopt reproduced: s121's defect); s131 RED only
        "readopt": (g("READOPT", "G1", "G2", "G3", "G4", "G5", "K", "X", "RED"),
                    (g("READOPT", "G3", "X", "RED"), g("READOPT", "G2"))),
    }
    cut = t["cut"]
    assert set(cut) == set(want) | {"cal"}, sorted(cut)
    assert all(cut["cal"]["pred"][s] == [[], []] for s in cut["cal"]["pred"]), cut["cal"]["pred"]
    for leg, (old, s119) in want.items():
        pred, catalog, p = cut[leg]["pred"], set(cut[leg]["catalog"]), old[0].split("-")[0]
        assert pred["0"] == pred["117"] == [old, []], (leg, pred)
        assert pred["119"] == [s119[0], s119[1]], (leg, pred["119"])
        if leg == "readopt":
            assert pred["120"] == pred["121"] == [g(p, "G3", "X"), g(p, "G2")], (leg, pred["120"], pred["121"])
        else:
            # [s131 cal] the tail-0 row (the default) carries the leg's hold check as a MAYBE on s120/s121
            hc0 = {"s119": "S119-G3", "s120-battle": "S120B-G4", "span": "SPAN-G2"}.get(leg)
            m0 = [hc0] if hc0 else []
            assert pred["121"] == [g(p, "RED"), m0], (leg, pred["121"])
            assert pred["120"] == ([g(p, "RED"), m0] if leg != "s121" else [old, []]), (leg, pred["120"])
        assert pred["131"] == [g(p, "RED"), []], (leg, pred["131"])    # [ff9mapkit netsync s131] RED only there too
        for reds, maybe in pred.values():
            assert set(reds) | set(maybe) <= catalog, (leg, sorted(set(reds) | set(maybe) - catalog))
    # [ff9mapkit netsync s131] THE TAIL ADDS (the docstring's paragraph): on s120 / s121 -- and on s119 for the s119 leg --
    # a cut with tail >= 66 adds the leg's hold check to its reds, a tail below 66 -- 0 included [s131 cal: the knife
    # edge] -- adds it as a maybe; s131 never; a check already red stays as it was (readopt's G3, s119's gk)
    assert t["hold_check"] == {"s119": "S119-G3", "readopt": "READOPT-G3", "s120-battle": "S120B-G4", "span": "SPAN-G2"}
    for leg, body in cut.items():
        hc = t["hold_check"].get(leg)
        for s, by_tail in body["tail"].items():
            base = by_tail["0.0"]
            assert base == body["pred"][s], (leg, s)
            adds = hc is not None and hc not in base[0] and (s in ("120", "121") or (s == "119" and leg == "s119"))
            if adds:
                reds, maybe = base[0], sorted(set(base[1]) - {hc})
                assert base == [reds, sorted(set(maybe) | {hc})], (leg, s, base)     # [s131 cal] tail 0: a maybe
                assert by_tail["33.0"] == [reds, sorted(set(maybe) | {hc})], (leg, s, by_tail)
                assert by_tail["67.0"] == [sorted(reds + [hc]), maybe], (leg, s, by_tail)
            else:
                assert by_tail["33.0"] == by_tail["67.0"] == base, (leg, s, by_tail)
    # [ff9mapkit netsync s131 fix] THE TAIL ADDS' one exception, pinned by hand (not by restating _predicted's condition):
    # a stall_cap span (s120-world) prints no hold ms and leaves at the resume + the settle on either engine, so SPAN-G2
    # reads the re-adopt only through the Ready-gated second close -- s120/s121 add it as a MAYBE at 33 AND 67, never a
    # red; s119 already reds it (8 s cap), s131 adds nothing, tail 0 is the host_field row
    span, tails = cut["span"]["pred"], ("0.0", "33.0", "67.0")
    maybe_g2 = [g("SPAN", "RED"), g("SPAN", "G2")]
    assert t["span_stall"] == {
        "119": {tl: span["119"] for tl in tails},
        "120": {"0.0": span["120"], "33.0": maybe_g2, "67.0": maybe_g2},
        "121": {"0.0": span["121"], "33.0": maybe_g2, "67.0": maybe_g2},
        "131": {tl: [g("SPAN", "RED"), []] for tl in tails},
    }, t["span_stall"]
    assert cut["span"]["tail"]["121"]["67.0"] == [g("SPAN", "G2", "RED"), []]     # host_field (the default): a red
    # ...and the ONE call site (run()'s calibration verdict; no stand-in drives this scenario) hands it the plan's verdict
    src = (SCENARIOS / "coop_cut_hold.py").read_text(encoding="utf-8")
    assert re.findall(r"= _predicted\(([^)]*)\)", src) == ["leg, ctx.stage, tail, why"], re.findall(r"_predicted\(.*", src)
    assert 'why = ((ctx.plan or {}).get("expect") or {}).get("why")' in src
    # [ff9mapkit netsync s131] whatever legs the table grows: on the s131 engine a leg predicts at most its own <P>-RED (the
    # s117-defect reproduction, red on every fixed engine) and nothing maybe -- every G/K check passes only with s131
    for leg, body in cut.items():
        reds, maybe = body["pred"]["131"]
        assert all(r.endswith("-RED") and r in body["catalog"] for r in reds) and len(reds) <= 1 and not maybe, (leg, reds)
    sh = t["sh"]
    assert set(sh["old"]) < set(sh["catalog"]) and set(sh["lever"]) < set(sh["catalog"])
    assert set(sh["catalog"]) - set(sh["old"]) == {"S14-S0", "S14-P1", "S14-A0", "S14-CAL"}
    assert {"REC-INI", "REC-B", "REC-F1", "REC-F5"} <= set(t["tr"]), t["tr"]


def test_the_s133_bench_predicts_its_reds_as_its_docstring_says():
    """[ff9mapkit netsync s133] coop_action_host.py's calibration tables, pinned to its docstring: on s132 (and older) every
    check is red but INI / S0 / PRE / B0 (the act probe fails closed: `actbench` never sent), 4 of 20 green; under its own
    lever (`actbench hoststarts off` before battle 1) exactly ON, AT, EN, MT, POT, VFX, PAIR, TAPE, ORDER -- every id one
    its catalog defines (a typo'd id is a red that never comes). Its probe is the driver's `actbench` key (audit amendment
    13), its scene the multi-enemy 306 (amendment 15), its proof line the engine's."""
    ah = _scenario_tables()["ah"]
    g = lambda *n: sorted(f"S133-{x}" for x in n)                     # noqa: E731
    assert set(ah["catalog"]) == set(ah["plain"]) | {"S133-CAL"} and len(ah["plain"]) == 20
    assert ah["old"] == sorted(set(ah["plain"]) - set(g("INI", "S0", "PRE", "B0")))
    assert ah["lever"] == g("ON", "AT", "EN", "MT", "POT", "VFX", "PAIR", "TAPE", "ORDER")
    assert set(ah["lever"]) < set(ah["old"]) and set(ah["lane"]) <= set(ah["old"])
    for piece in ("GREEN there, exactly: INI, S0, PRE, B0 -- 4 of 20.",
                  "predicted reds, exactly: ON, AT, EN, MT, POT, VFX, PAIR, TAPE, ORDER (",
                  "RED, exactly: P0, PROOF (no 'action lane' line), P1 (never sent), ON (no key; caps bit 5 never set), AT, "
                  "EN, MT, POT, VFX, PAIR, TAPE, ORDER, DUMP, STOP, L1, R (not reached).",
                  "Memoria.ini [Netsync] Enabled = 0 (or absent)"):
        assert piece in ah["doc"], piece
    assert ah["probe"] == Session.NETSYNC_BATTLE_SUBVERBS["actbench"][1] == "netsync.battle.act.host"
    assert ah["scene"] == 306 and ah["group"] in (2, 4)
    assert ah["proof"] == BW.proof_ok(BW.PROOF_ACTION, BW.ACTION_SELFTEST_ROWS)


def test_the_s134_bench_predicts_its_reds_as_its_docstring_says():
    """[ff9mapkit netsync s134] coop_action_replay.py's calibration tables, pinned to its docstring: on s133 (and older)
    every check is red but INI / S0 / PRE / TAPE / INV (the act.guest probe fails closed: no guest op ever sent); under its
    own lever (`actbench replay off` before boot 1) exactly the LEVER set, K green (its expectation pinned per scene: no
    grace on scene 306 either way -- the review pass) -- every id one its catalog defines.
    Its tape leg (COOP_ACT_LEG=tape): on an s133 guest every act check, under ActionReplay=0 exactly RUN / ACT / PAIR /
    DECL / END / LOG. Its probe is the s134 key, its scene the s133 bench's, its proof line the engine's, its tape dir
    beside coop-tapes/ (never moving coop_cut_hold's latest.json), and the default leg the solo one."""
    ar = _scenario_tables()["ar"]
    g = lambda *n: sorted(f"S134-{x}" for x in n)                     # noqa: E731
    assert set(ar["catalog"]) == set(ar["plain"]) | {"S134-CAL"} and len(ar["plain"]) == 35
    assert ar["old"] == sorted(set(ar["plain"]) - set(g("INI", "S0", "PRE", "TAPE", "INV")))
    assert ar["lever"] == g("A1", "A2", "A3", "M", "AH", "B", "F", "J", "L", "H", "PAUSE", "TRIP", "TRIPST", "D2", "BL",
                            "D", "E1", "E2", "E3", "E4", "C")
    assert ar["maybe"] == [] and "MAYBE" not in ar["doc"]
    assert set(ar["lever"]) < set(ar["old"]) and set(ar["guest"]) <= set(ar["plain"])
    assert set(ar["plain"]) - set(ar["lever"]) == set(g("INI", "S0", "P0", "PROOF", "PRE", "TAPE", "BOOT", "A4", "G", "I",
                                                         "D0", "K", "INV", "R"))
    for piece in ("RED, exactly: every check but INI, S0, PRE, TAPE, INV (nothing booted, nothing to change)",
                  "Predicted reds, exactly: A1, A2, A3, M, AH, B, F, J, L, H, PAUSE, TRIP, TRIPST, D2, BL, D, E1, E2, E3, "
                  "E4, C (", "GREEN: INI, S0, P0, PROOF, PRE, TAPE, BOOT, A4, G, I (knob is ahead of the lever), D0, K "
                  "(scene 306: no AttackOnDeath, no grace either way), INV, R.", "Memoria.ini [Netsync] Enabled = 0 (or absent)",
                  "a SMOKE check of the deferred Leave", "amendment 12 is not benched",
                  "RED exactly P0, B5, RX, RUN, ACT, PAIR, DECL, END, TRIP, LOG (fails closed)",
                  "RED exactly RUN, ACT, PAIR, DECL, END, LOG (every START declines `knob`)",
                  "the leg refuses cleanly (\"no s133 tape\""):
        assert piece in ar["doc"], piece
    assert ar["probe"] == "netsync.battle.act.guest" == Session.NETSYNC_ACTBENCH_OP_CAPS["feed"][1]
    assert ar["host_probe"] == Session.NETSYNC_BATTLE_SUBVERBS["actbench"][1]
    assert ar["scene"] == 306 and ar["group"] in (2, 4) and ar["leg"] == "solo" and ar["legs"] == ["solo", "tape"]
    assert ar["proof"] == BW.proof_ok(BW.PROOF_REPLAY, BW.REPLAY_SELFTEST_ROWS)
    t = lambda *n: sorted(f"S134T-{x}" for x in n)                    # noqa: E731
    assert set(ar["tape"]) == set(ar["tape_plain"]) | {"S134T-CAL"}
    assert set(ar["tape_plain"]) == set(ar["tape_act"]) | {"S134T-I", "T2-TAPE", "T2-CAL", "T2-PEER", "T2-SAVE", "T2-INI"}
    assert ar["tape_old"] == ar["tape_act"] == t("P0", "B5", "RX", "RUN", "ACT", "PAIR", "DECL", "END", "TRIP", "LOG")
    assert ar["tape_knob"] == t("RUN", "ACT", "PAIR", "DECL", "END", "LOG")
    assert ar["tape_dir"].replace("\\", "/").endswith(".harness-runs/coop-tapes/act-s133")
    # the tape leg's guest is coop_cut_hold's (+ ActionReplay, written per run)
    cut = (SCENARIOS / "coop_cut_hold.py").read_text(encoding="utf-8")
    for k, v in ar["values"].items():
        assert f'"{k}"' in cut, k
    assert "ActionReplay" not in ar["values"]


#: coop_action_replay's tape-leg judge and its tape reader, run on synthetic inputs (JSON on stdin), the checks read back
_ACT_REPLAY_JUDGE = r"""
import importlib.util, json, os, sys, types
scen, tools = sys.argv[1], sys.argv[2]
sys.path.insert(0, tools)
spec = importlib.util.spec_from_file_location("coop_action_replay", os.path.join(scen, "coop_action_replay.py"))
ar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ar)
BW = ar.BW
class Led:
    def __init__(self):
        self.checks = {}
    def check(self, cid, ok, detail=""):
        self.checks[cid] = [bool(ok), str(detail)]
    def unreached(self, ids, why):
        for c in ids:
            self.checks.setdefault(c, [False, "unreached: " + why])
doc = json.loads(sys.stdin.read())
out = {}
for name, run in doc["runs"].items():
    led = Led()
    ar.judge_tape(led, run["samples"], run["messages"], {"starts": run["tape_starts"]})
    out[name] = led.checks
cp = types.SimpleNamespace(tape_action_frames=lambda recs: [(0.0, bytes.fromhex(h)) for h in recs])
out["facts"] = {k: ar.tape_act_facts(v, cp, 7) for k, v in doc["tapes"].items()}
print(json.dumps(out))
"""


def _ar_run(**over) -> dict:
    """A synthetic tape-leg run: the guest's `act.guest` samples (booted, then after the return) and the engine's lines."""
    g = dict(BW.ACT_GUEST_SENTINELS, on=True, rework=True, knob=1, bit5=True, host_caps=0x22, starts_rx=3, ends_rx=3,
             started=3, ended=3, hits=4, credits=3, paired=5, swing_skipped=2, rx_dropped=0, battle_ms=9000)
    g.update(over.get("guest", {}))
    acting = over.get("acting", True)
    samples = [{"booted": True, "guest": dict(g, running=1, ended=g["ended"] - 1 if g["ended"] else 0),
                "units": [[0, acting, "ANH_A"], [4, False, "ANH_B"]]},
               {"booted": True, "guest": g, "units": [[0, False, "ANH_I"]]},
               {"booted": False, "guest": dict(g, battle_ms=-1), "units": []}]
    if over.get("trip"):
        samples[1]["guest"] = dict(g, calc_while_booted=1)
    if over.get("no_guest"):
        samples = [{"booted": True, "guest": None, "units": []}]
    messages = over.get("messages", [
        f"{BW.LOG_REPLAY_STARTED}1 slot 0 (player) cmd 1 sub 176 kind 3 num 100 tar 0x10 host speed 5 -- presentation only",
        f"{BW.LOG_REPLAY_SUMMARY}teardown) -- {g['starts_rx']} START(s) received, {g['started']} started, 0 declined"])
    return {"samples": samples, "messages": messages, "tape_starts": over.get("tape_starts", 3)}


def test_the_s134_tape_legs_judge_reads_each_engine_and_refuses_a_pre_s133_tape():
    """coop_action_replay.judge_tape (the T2 leg's verdict, pure) on synthetic runs: a healthy s134 guest GREEN on all ten;
    the knob (every START declined `knob`) red on exactly TAPE_KNOB_PREDICTED; an s133 guest (no `act.guest`) red on every
    act check; a fired tripwire red on TRIP alone; a non-end abort red on END -- [s134 review timing-04] judged by its
    reason (`aborts`), so an early `pending` MASKED by a later R8 abort_why is red too, and a block without `aborts` fails
    closed; [harness-9] a START the end's abort-all dropped is no DECL red; [harness-05] rx_dropped is judged ABSOLUTE
    (a fresh transport): a constant nonzero count (boot-backlog drops already in the first read) is an RX red, and so is
    a counter never read (-1 throughout). tape_act_facts: a tape with STARTs on the battle's nonce is an s133 tape, one
    with 46-byte impacts only (or STARTs on ANOTHER nonce) is "no s133 tape"."""
    start = BW.encode_action_start(7, 1, 3, 0, BW.ACTOR_IS_PLAYER, 1, 176, 0x10, 0, 0, 0, BW.VFX_KIND_SPECIAL, 100, -1, 5)
    other = BW.encode_action_start(8, 1, 3, 0, BW.ACTOR_IS_PLAYER, 1, 176, 0x10, 0, 0, 0, BW.VFX_KIND_SPECIAL, 100, -1, 5)
    old = BW.encode_action_impact(7, 1, 0, 4, fig_t=(0, 33, 0), flags=65, cmd_no=1, sub_no=176)
    knob = {"started": 0, "declined": 3, "declined_why": "knob", "ended": 0, "hits": 0, "credits": 0, "swing_skipped": 0}
    runs = {"green": _ar_run(), "knob": _ar_run(guest=knob, acting=False, messages=[
                f"{BW.LOG_REPLAY_SUMMARY}teardown) -- 3 START(s) received, 0 started, 3 declined"]),
            "old": _ar_run(no_guest=True), "trip": _ar_run(trip=True),
            "abort": _ar_run(guest={"ended": 2, "aborted": 1, "abort_why": "host-end",
                                    "aborts": dict(BW.ACT_GUEST_SENTINELS["aborts"], host_end=1)}),
            "masked": _ar_run(guest={"ended": 1, "aborted": 2, "abort_why": "r8",
                                     "aborts": dict(BW.ACT_GUEST_SENTINELS["aborts"], pending=1, r8=1)}),
            "endabort": _ar_run(guest={"ended": 2, "aborted": 1, "abort_why": "r8",
                                       "aborts": dict(BW.ACT_GUEST_SENTINELS["aborts"], r8=1)}),
            "dropped": _ar_run(guest={"starts_rx": 4, "declined": 1, "declined_why": "leave", "dropped": 1},
                               tape_starts=4),
            "unaccounted": _ar_run(guest={"starts_rx": 4, "declined": 1, "declined_why": "leave"}, tape_starts=4),
            "noaborts": _ar_run(guest={"aborts": None}),
            "bootdrops": _ar_run(guest={"rx_dropped": 2}), "unread": _ar_run(guest={"rx_dropped": -1})}
    env = {k: v for k, v in os.environ.items() if not k.startswith("COOP_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    out = subprocess.run([sys.executable, "-c", _ACT_REPLAY_JUDGE, str(SCENARIOS), str(REPO / "tools")], env=env,
                         input=json.dumps({"runs": runs, "tapes": {"s133": [start.hex(), old.hex()], "pre": [old.hex()],
                                                                   "other": [other.hex()]}}),
                         capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-2000:]
    got = json.loads(out.stdout.strip().splitlines()[-1])
    act = ("S134T-P0", "S134T-B5", "S134T-RX", "S134T-RUN", "S134T-ACT", "S134T-PAIR", "S134T-DECL", "S134T-END",
           "S134T-TRIP", "S134T-LOG")
    red = lambda name: sorted(c for c, (ok, _d) in got[name].items() if not ok)   # noqa: E731
    assert set(got["green"]) == set(act) and red("green") == [], got["green"]
    assert red("knob") == sorted(("S134T-RUN", "S134T-ACT", "S134T-PAIR", "S134T-DECL", "S134T-END", "S134T-LOG"))
    assert red("old") == sorted(act) and all("unreached" in d for _ok, d in got["old"].values())
    assert red("trip") == ["S134T-TRIP"] and red("abort") == ["S134T-END"] and red("masked") == ["S134T-END"]
    assert red("endabort") == [] and red("dropped") == [] and red("unaccounted") == ["S134T-DECL"]
    assert red("noaborts") == ["S134T-END"] and "fails closed" in got["noaborts"]["S134T-END"][1]
    assert red("bootdrops") == ["S134T-RX"] and "boot backlog" in got["bootdrops"]["S134T-RX"][1]
    assert red("unread") == ["S134T-RX"] and "never read" in got["unread"]["S134T-RX"][1]
    f = got["facts"]
    assert f["s133"]["ok"] and f["s133"]["starts"] == 1 and f["s133"]["impacts"] == 1
    assert not f["pre"]["ok"] and f["pre"]["why"].startswith("no s133 tape: no START on battle nonce 7")
    assert not f["other"]["ok"] and f["other"]["all_frames"] == 1                # (a START, but of another battle)


#: coop_action_replay's diorama cast (`_who`) and D0's batched boot (`_boot_and_leave`), on synthetic inputs
_ACT_REPLAY_CAST = r"""
import importlib.util, json, os, sys
scen, tools = sys.argv[1], sys.argv[2]
sys.path.insert(0, tools)
spec = importlib.util.spec_from_file_location("coop_action_replay", os.path.join(scen, "coop_action_replay.py"))
ar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ar)
def st(*names):
    us = [{"slot": i, "name": n, "player": True, "alive": True} for i, n in enumerate(names)]
    us += [{"slot": 4, "name": "Fang", "player": False}, {"slot": 5, "name": "Fang", "player": False}]
    return {"battle": {"units": us}}
def cast(x, ctx):
    w = ar._who(x, ctx)
    return {k: [None if u is None else u["slot"], wire] for k, (u, wire) in w.items()}
ctx = {"zidane_wire": 0, "vivi_wire": 1, "garnet_wire": 2}
out = {"battle1": cast(st("Zidane", "Vivi", "Dagger", "Steiner"), ctx),
       "diorama": cast(st("BENCH", "Vivi", "Dagger", "Steiner"), ctx),
       "no_ctx": cast(st("BENCH", "Vivi", "Dagger", "Steiner"), None),
       "impostor_unnamed": cast(st("Freya", "Vivi", "Dagger", "Steiner"), ctx)}
class G:
    def __init__(self, refuse):
        self.sent, self.refuse = [], refuse
    def send(self, *steps, timeout=60.0):
        self.sent.append(list(steps))
        if self.refuse:
            raise ar.HarnessError(self.refuse)
for name, refuse in (("deferred", "the game refused a step: netsync: netsync dioleave: deferred -- a scene fade is in "
                                  "flight; retry"), ("left", None)):
    g = G(refuse)
    ok, why = ar._boot_and_leave(g)
    out[name] = {"sent": g.sent, "ok": ok, "deferred": ar.LEAVE_DEFERRED in why}
print(json.dumps(out))
"""


def test_the_s134_benchs_diorama_zidane_is_the_bench_stand_in_and_d0_leaves_inside_the_boots_request():
    """[s134 solo run 1] coop_action_replay's diorama cast: every selftest `dioboot` seats the selftest mirror's stand-in
    (NetSyncParty.SelfTestMirror: name "BENCH") in party slot 0, so no diorama unit is named Zidane -- 'Zidane' there is
    the unit at Zidane's battle-1 WIRE, taken ONLY when it is that stand-in (an unnamed impostor at the seat is never
    taken: not reached, never a wrong actor). Battle 1's real Zidane wins by name; Vivi / Garnet keep their names.
    D0's `dioleave` rides the boot's OWN request (one send, dioboot first): LeaveFrom defers only while the swirl's fade
    is in flight (the boot's frame + 2), and a separate request landed past it -- where the selftest path strands the
    boot -- in the first in-game run."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("COOP_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    out = subprocess.run([sys.executable, "-c", _ACT_REPLAY_CAST, str(SCENARIOS), str(REPO / "tools")], env=env,
                         capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-2000:]
    got = json.loads(out.stdout.strip().splitlines()[-1])
    assert got["battle1"]["zidane"] == [0, 0] and got["battle1"]["vivi"] == [1, 1] and got["battle1"]["garnet"] == [2, 2]
    assert got["diorama"]["zidane"] == [0, 0] and got["diorama"]["vivi"] == [1, 1] and got["diorama"]["garnet"] == [2, 2]
    assert got["diorama"]["fang1"] == [4, 4] and got["diorama"]["fang2"] == [5, 5]
    assert got["no_ctx"]["zidane"] == [None, None]                               # never by seat without the taped wire
    assert got["impostor_unnamed"]["zidane"] == [None, None]                     # never a unit that is not the stand-in
    want = [["netsync dioboot 306 4", "netsync dioleave"]]
    assert got["deferred"] == {"sent": want, "ok": False, "deferred": True}
    assert got["left"] == {"sent": want, "ok": True, "deferred": False}


#: coop_action_replay's boot 3 (`_boot_3` + its pure `_judge_boot_3`) driven on a stub game: a Memoria.log the request
#: appends to, the agent's per-step 'error' events, the request's refusal latch (its LAST step's), the state before/after
_ACT_REPLAY_BOOT3 = r"""
import importlib.util, json, os, sys, tempfile
from pathlib import Path
scen, tools = sys.argv[1], sys.argv[2]
sys.path.insert(0, tools)
spec = importlib.util.spec_from_file_location("coop_action_replay", os.path.join(scen, "coop_action_replay.py"))
ar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ar)
ar.LOG_WAIT_S = 0.0
T = "16.10.2026 03:06:13 |M| "
BOOT = T + ar.BOOT_LINE + "start=BTL_START_NORMAL_ATTACK intro=own swirl=0 clamp=0"
DEFER = T + "[NetSync] diorama leave deferred: a fade is in flight; press Leave again."
LEFT = T + "[NetSync] diorama LEAVE requested -> FieldMap (mode 1)"
REFUSED = "16.10.2026 03:06:13 |W| [NetSync] diorama boot REFUSED: the field is not free (a dialog is open)"
DEFERRED = "netsync dioleave: deferred -- a scene fade is in flight; retry"
NONE = "netsync dioleave: no diorama is booted"
class St:
    def __init__(self, booted, aborted=0):
        self.raw = {"netsync": {"diorama": {"booted": booted}, "battle": {"act": {"guest": {"aborted": aborted}}}}}
        self.scene, self.frame = None, 1
class Chan:
    def __init__(self):
        self.ev = [{"kind": "error", "op": "netsync", "message": "netsync dioboot: an OLDER request's refusal"}]
    def events(self):
        return list(self.ev)
class G:
    def __init__(self, log, before, after, lines, errors):
        self.log, self.channel = log, Chan()
        self.state, self.after, self.lines, self.errors = before, after, lines, errors
        self.sent, self.notes = [], []
        # lines BEFORE the mark (a previous boot's): never boot 3's witnesses
        log.write_text(T + ar.BOOT_LINE + "(a previous boot)\n" + DEFER + "\n", encoding="utf-8")
    def engine_log(self):
        return self.log
    def netsync(self, *a, **k):
        return self.state
    def wait_for(self, pred, timeout=0, what=""):
        if pred(self.state):
            return self.state
        raise ar.HarnessError("timed out: " + what)
    def wait_frames(self, n):
        pass
    def note(self, t):
        self.notes.append(t)
    def send(self, *steps, timeout=60.0):
        self.sent.append(list(steps))
        with self.log.open("a", encoding="utf-8") as f:
            f.writelines(ln + "\n" for ln in self.lines)
        self.channel.ev += [{"kind": "error", "op": "netsync", "message": m} for m in self.errors]
        self.state = self.after
        if self.errors:                                   # the latch: the LAST refused step's only
            raise ar.HarnessError("the game refused a step: netsync: " + self.errors[-1])
class Led:
    def __init__(self):
        self.checks, self.done = {}, {}
    def check(self, cid, ok, detail=""):
        self.checks.setdefault(cid, [bool(ok), str(detail)])
        self.done[cid] = bool(ok)
    def unreached(self, ids, why):
        for c in ids:
            if c not in self.done:
                self.check(c, False, "not reached: " + why)
outs = []
ar._out = lambda g, field: outs.append(field)
cases = {
    "refused": (St(False), St(False), [REFUSED],
                ["netsync dioboot: refused (Memoria.log names why: [NetSync] diorama boot REFUSED)", NONE]),
    "norole": (St(False), St(False), [], ["netsync dioboot: needs the selftest role (netsync selftest 1)", NONE]),
    "stale": (St(True), St(True), [DEFER], ["netsync dioboot: a diorama is already booted", DEFERRED]),
    "left": (St(False), St(True), [BOOT, LEFT], []),
    "deferred": (St(False), St(True), [BOOT, DEFER], [DEFERRED]),
    "one_witness": (St(False), St(True), [BOOT], [DEFERRED]),
    "engine_only": (St(False), St(True), [BOOT, DEFER], []),
    "unbooted": (St(False), St(False), [BOOT, DEFER], [DEFERRED]),
    "aborted": (St(False), St(True, aborted=1), [BOOT, DEFER], [DEFERRED]),
    "boot_and_refused": (St(False), St(False), [BOOT, REFUSED], [NONE]),
    "boot_failed": (St(False), St(False), [BOOT, T + "[NetSync] diorama boot failed: NullReferenceException"],
                    ["netsync dioboot: refused (Memoria.log names why)", NONE]),
}
out = {}
with tempfile.TemporaryDirectory() as td:
    for name, (before, after, lines, errors) in cases.items():
        g = G(Path(td) / (name + ".log"), before, after, lines, errors)
        led = Led()
        ar._boot_3(g, led, 30602, {})
        out[name] = {"sent": g.sent, "checks": led.checks}
out["judge_stale"] = list(ar._judge_boot_3(False, "the game refused a step: netsync: " + DEFERRED, [DEFER],
                                           ["netsync dioboot: a diorama is already booted", DEFERRED], True, 0))
out["outs"] = len(outs)
print(json.dumps(out))
"""


def test_the_s134_benchs_d0_judges_only_a_fresh_boot_on_two_witnesses_never_the_latch_alone():
    """[s134 solo review 1/5] D0 (`_boot_3`) never trusts the request's refusal latch alone: the agent catches each step's
    refusal and runs the next, so the latch keeps only the LAST -- a refused `dioboot` is overwritten by the batched
    `dioleave`'s, and against a stale diorama that leave's 'deferred' is not boot 3's. A boot refused (by Boot's own
    REFUSED line, or before Boot: only its step event names why) is NOT REACHED with the boot's reason; a diorama up
    before boot 3 is never sent to (not reached, never green -- and the judge alone, fed a stale diorama's request, has
    no fresh BOOT line: not reached either); a Leave ACCEPTED is D0's red; GREEN needs a fresh BOOT line after the mark
    AND both witnesses of the deferral (the agent's refusal, LeaveFrom's line) with the diorama still booted -- one
    witness is red. Lines and events from before the mark never count. Every path leaves the field (`_out`)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("COOP_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    out = subprocess.run([sys.executable, "-c", _ACT_REPLAY_BOOT3, str(SCENARIOS), str(REPO / "tools")], env=env,
                         capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-2000:]
    got = json.loads(out.stdout.strip().splitlines()[-1])
    one = [["netsync dioboot 306 4", "netsync dioleave"]]
    d0 = lambda name: got[name]["checks"]["S134-D0"]                    # noqa: E731
    e1 = lambda name: got[name]["checks"]["S134-E1"]                    # noqa: E731
    # refused by Boot: not reached, with the boot's OWN reason (its REFUSED line, its step), never the leave's as its
    for name, why in (("refused", "the field is not free (a dialog is open)"), ("norole", "needs the selftest role")):
        assert got[name]["sent"] == one
        for ok, detail in (d0(name), e1(name)):
            assert not ok and detail.startswith("not reached: boot 3 did not boot") and why in detail, detail
            assert "the batched dioleave's, never the boot's" in detail and "OLDER request" not in detail
    # a stale diorama: nothing sent, not reached -- never green, though its leave would have said 'deferred'
    assert got["stale"]["sent"] == []
    for ok, detail in (d0("stale"), e1("stale")):
        assert not ok and detail.startswith("not reached: a diorama is already booted before boot 3"), detail
    assert got["judge_stale"][0] is None and got["judge_stale"][1] is False and "no fresh BOOT line" in got["judge_stale"][2]
    # a Leave accepted: D0's red (reached), E1 not reached on a boot that is gone
    assert d0("left")[0] is False and "LEFT (accepted)" in d0("left")[1] and not d0("left")[1].startswith("not reached")
    assert not e1("left")[0] and "the leave was ACCEPTED" in e1("left")[1]
    # deferred, both witnesses, still booted: D0 green (E1 then waits on the steady latch the stub never reaches)
    assert d0("deferred")[0] is True and "LeaveFrom's deferral line logged" in d0("deferred")[1]
    assert not e1("deferred")[0] and "steady latch" in e1("deferred")[1]
    # the agent's refusal alone (no LeaveFrom line after the mark): red
    assert d0("one_witness")[0] is False and "LeaveFrom's deferral line ABSENT" in d0("one_witness")[1]
    assert not e1("one_witness")[0] and "not proven deferred" in e1("one_witness")[1]
    # [review 2/2] each conjunct of the green can fail on its own: LeaveFrom's line alone (the leave accepted) is red;
    # both witnesses but the diorama gone is red ("not proven deferred"); both witnesses but an abort is red (E1 still
    # runs: the boot is up); a REFUSED line after a BOOT line, or a boot that FAILED after it, is "did not boot"
    assert d0("engine_only")[0] is False and "LEFT (accepted)" in d0("engine_only")[1]
    assert "LeaveFrom's deferral line logged" in d0("engine_only")[1]
    assert d0("unbooted")[0] is False and not d0("unbooted")[1].startswith("not reached")
    assert not e1("unbooted")[0] and "not proven deferred" in e1("unbooted")[1]
    assert d0("aborted")[0] is False and "aborted 1" in d0("aborted")[1]
    assert not e1("aborted")[0] and "steady latch" in e1("aborted")[1]
    for name, why in (("boot_and_refused", "a REFUSED line"), ("boot_failed", "a 'diorama boot failed' line")):
        for ok, detail in (d0(name), e1(name)):
            assert not ok and detail.startswith("not reached: boot 3 did not boot (" + why), detail
    assert got["outs"] == 11


#: coop_action_host._judge_tape run on tapes passed in (JSON on stdin: name -> [hex]), its ledger checks read back
_ACT_TAPE_JUDGE = r'''
import importlib.util, json, os, sys
scen, tools = sys.argv[1], sys.argv[2]
sys.path.insert(0, tools)
spec = importlib.util.spec_from_file_location("coop_action_host", os.path.join(scen, "coop_action_host.py"))
ah = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ah)
BW = ah.BW
class Led:
    def __init__(self):
        self.checks = {}
    def check(self, cid, ok, detail=""):
        self.checks[cid] = [bool(ok), str(detail)]
    def unreached(self, ids, why):
        for c in ids:
            self.checks[c] = [False, "unreached: " + why]
out = {}
for name, hexes in json.loads(sys.stdin.read()).items():
    tape = [bytes.fromhex(h) for h in hexes]
    decoded = [BW.decode_action(b) for b in tape]
    kinds = [BW.classify_action(d) for d in decoded]
    starts = [d for d, k in zip(decoded, kinds) if k == "start"]
    led = Led()
    nonce = BW.decode_action_legacy(tape[0])["nonce"]
    ah._judge_tape(led, {"slots": {}, "plan": {}}, {"nonce": nonce, "starts": len(starts)},
                   {"starts": len(starts), "overflow": 0}, tape, decoded, kinds, starts)
    out[name] = {k: led.checks[k] for k in ("S133-TAPE", "S133-ORDER")}
print(json.dumps(out))
'''


def test_the_s133_benchs_tape_judge_reds_each_corruption():
    """coop_action_host's own S133-TAPE (review wire-3 / harness-1 / wire-4), run on a tape written by the engine's rules:
    GREEN; then RED on each corruption the old clause could not see -- an impact's legacy cmd_no (its START's identity), an
    END whose legacy target slot resolves (lethal to an s110-s132 guest), a raw on a START, a START stamping a stale seq."""
    good = _act_tape_model()
    tapes = {"good": good,
             "impact_cmd": [_patched(b, 42, b"\x02\x00") if i == 1 else b for i, b in enumerate(good)],
             "end_slot": [_patched(b, 4, b"\x04") if i == 3 else b for i, b in enumerate(good)],
             "start_raw": [_patched(b, 25, b"\x01") if i == 0 else b for i, b in enumerate(good)],
             "stale_start": [_patched(b, 1, (11).to_bytes(2, "little")) if i == 4 else b for i, b in enumerate(good)]}
    env = {k: v for k, v in os.environ.items() if not k.startswith("COOP_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    out = subprocess.run([sys.executable, "-c", _ACT_TAPE_JUDGE, str(SCENARIOS), str(REPO / "tools")], env=env,
                         input=json.dumps({k: [b.hex() for b in v] for k, v in tapes.items()}), capture_output=True,
                         text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-2000:]
    got = json.loads(out.stdout.strip().splitlines()[-1])
    assert got["good"]["S133-TAPE"][0] and got["good"]["S133-ORDER"][0], got["good"]
    for name, needle in (("impact_cmd", "identity: impact id 1 at frame 1: legacy cmd/sub 2/176"),
                         ("end_slot", "END 52 B legacy c/t 255/4 inert False"),
                         ("start_raw", "START 76 B legacy c/t 255/255 inert False"),
                         ("stale_start", "horizon: START at frame 4 (nonce 7) stamps seq 11")):
        ok, detail = got[name]["S133-TAPE"]
        assert not ok and needle in detail, (name, detail)


def test_the_s135_bench_predicts_its_reds_as_its_docstring_says():
    """[ff9mapkit netsync s135] coop_action_hold.py's calibration tables, pinned to its docstring: on s134 (and older)
    every check is red but INI / S0 / PRE / TAPE / INV (the act.guest.hold probe fails closed: no hold op ever sent);
    under its own lever (`actbench hold off` before boot 1) exactly the LEVER set -- L4N and LOST in it too (the fix pass:
    each check's in-run red, a sibling leg where the hold acted, never comes there) -- every id one its catalog
    defines; the fix pass's QSUP and CATCH legs each on a boot of their own. Its tape leg: on an s134 guest every hold check, under ActionReplay=0
    exactly HELD / LAG / FIG / LOG. Its probe is the s135 key, its scene and tape the s134 bench's, its nonce and figures
    its own MARKERS, its proof line the engine's, the four s134 lessons and amendment 15 in its docstring -- and it never
    sends `endbench kill` (amendment 15: KillUnit bypasses the life mask)."""
    hd = _scenario_tables()["hd"]
    g = lambda *n: sorted(f"S135-{x}" for x in n)                     # noqa: E731
    assert set(hd["catalog"]) == set(hd["plain"]) | {"S135-CAL"} and len(hd["plain"]) == 27
    assert hd["old"] == sorted(set(hd["plain"]) - set(g("INI", "S0", "PRE", "TAPE", "INV")))
    assert hd["lever"] == g("L1", "L1F", "L5", "L3", "L4", "L4N", "L7", "REP", "DSK", "L8", "TD", "L2", "L2R", "LOST", "L6",
                            "QSUP", "DEF", "CATCH")
    assert hd["maybe"] == [] and set(hd["lever"]) < set(hd["old"]) and set(hd["hold"]) <= set(hd["plain"])
    assert set(hd["plain"]) - set(hd["lever"]) == set(g("INI", "S0", "P0", "PROOF", "PRE", "TAPE", "BOOT", "INV", "R"))
    for piece in ("RED, exactly: every check but INI, S0, PRE, TAPE, INV (nothing booted, nothing to change)",
                  "Predicted reds, exactly: L1, L1F, L5, L3, L4, L4N, L7, REP, DSK, L8, TD, L2, L2R, LOST, L6, QSUP, DEF, "
                  "CATCH (", "GREEN: INI, S0, P0, PROOF, PRE, TAPE, BOOT, INV, R.",
                  "ITS IN-RUN RED", "the caster lane's figure on a hit release",
                  "RED exactly P0, HELD, REST, LAG, FIG, LOG (fails closed)", "RED exactly HELD, LAG, FIG, LOG (REST is green",
                  "s134 LESSON 1", "s134 LESSON 2", "s134 LESSON 3", "s134 LESSON 4", "NEVER `endbench kill`: amendment 15",
                  "amendment 14", "Memoria.ini [Netsync] Enabled = 0 (or absent)", "THE REAL-LINK LAG (amendment 10)"):
        assert piece in hd["doc"], piece
    assert hd["probe"] == "netsync.battle.act.guest.hold" == Session.NETSYNC_ACTBENCH_OP_CAPS["hold"][1]
    assert hd["guest_probe"] == Session.NETSYNC_ACTBENCH_OP_CAPS["feed"][1]
    assert hd["scene"] == 306 and hd["group"] in (2, 4) and hd["leg"] == "solo" and hd["legs"] == ["solo", "tape"]
    assert hd["proof"] == BW.proof_ok(BW.PROOF_HOLD, BW.HOLD_SELFTEST_ROWS)
    assert hd["nonce"] == 0x5D != hd["replay_nonce"] and len(set(hd["figs"])) == len(hd["figs"]) == 17
    assert all(5135 <= f <= 5151 for f in hd["figs"])
    assert hd["boot1"][0] == "S135-BOOT" and hd["boot1"][-2:] == ["S135-L8", "S135-TD"]    # nothing kills before them
    assert not set(hd["boot1"]) & set(g("L2", "L2R", "LOST", "L6", "QSUP", "DEF", "CATCH"))   # the killers: own boots
    t = lambda *n: sorted(f"S135T-{x}" for x in n)                    # noqa: E731
    assert set(hd["tape"]) == set(hd["tape_plain"]) | {"S135T-CAL"}
    assert set(hd["tape_plain"]) == set(hd["tape_hold"]) | {"S135T-I", "T2-TAPE", "T2-CAL", "T2-PEER", "T2-SAVE", "T2-INI"}
    assert hd["tape_old"] == hd["tape_hold"] == t("P0", "HELD", "REST", "LAG", "FIG", "LOG")
    assert hd["tape_knob"] == t("HELD", "LAG", "FIG", "LOG")
    src = (SCENARIOS / "coop_action_hold.py").read_text(encoding="utf-8")
    code = "\n".join(ln for ln in src.split('"""', 2)[2].splitlines() if not ln.lstrip().startswith("#"))
    assert '"kill"' not in code and "endbench kill" not in code.replace("never `endbench kill`", "")
    # [s135 fix pass] each follow-up that must land before a replay's own hit rides the feed's OWN request (timing-3):
    # DEF's and CATCH's `endbench phase-defeat`, QSUP's `unit` -- never a lone try_ns after a poll
    assert "try_ns(g, \"endbench\", \"phase-defeat\")" not in code
    assert code.count('"netsync endbench phase-defeat"') == 2 and "leave=False" not in code and "cb.FIELD\n" not in code
    # [s135 fix pass: rtiming-1] a release on a unit the long summon hides (THE HIDE WINDOW) is judged on its counter and
    # the engine's own release line, never on figs[]: L4 / L7 / L8 / L6 each call judge_timer_release with their reason
    # and never judge_release; L4N is fed only once L4's summon is at rest
    for leg, via in (("_leg_l4", '"timeout"'), ("_leg_l7", '"hostdone"'), ("_leg_l8", '"timeout"'),
                     ("_legs_lost_l6", '"abort"')):
        body = code.split(f"def {leg}(", 1)[1].split("\ndef ", 1)[0]
        call = body.split("judge_timer_release(", 1)[1].split(")", 1)[0] if "judge_timer_release(" in body else ""
        assert via in call and "judge_release(" not in body.replace("judge_timer_release(", ""), (leg, call)
    l4 = code.split("def _leg_l4(", 1)[1].split("\ndef ", 1)[0]
    assert l4.index("_wait_rest(g, base)") < l4.index("orphan = _impact(")
    for piece in ("TIMING RISKS", "THE HIDE WINDOW", "IsDisappear=True", "THE FREEZE (amendment 14 as built"):
        assert piece in hd["doc"], piece


#: coop_action_hold's pure judges and its tape reader, run on synthetic inputs (JSON on stdin), the verdicts read back
_ACT_HOLD_JUDGE = r"""
import importlib.util, json, os, sys
scen, tools = sys.argv[1], sys.argv[2]
sys.path.insert(0, tools)
spec = importlib.util.spec_from_file_location("coop_action_hold", os.path.join(scen, "coop_action_hold.py"))
hd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hd)
BW = hd.BW
class Led:
    def __init__(self):
        self.checks = {}
    def check(self, cid, ok, detail=""):
        self.checks[cid] = [bool(ok), str(detail)]
    def unreached(self, ids, why):
        for c in ids:
            self.checks.setdefault(c, [False, "unreached: " + why])
doc = json.loads(sys.stdin.read())
out = {"wait": {k: list(hd.judge_figure_waits(c["samples"], c["value"], c.get("slot"), c.get("via", "hit")))
                for k, c in doc["wait"].items()},
       "release": {k: list(hd.judge_release(c["figs"], c["value"], c["via"], c["lo"], c["hi"]))
                   for k, c in doc["release"].items()},
       "flinch": {k: list(hd.judge_flinch([tuple(m) for m in c["mots"]], c["hit"])) for k, c in doc["flinch"].items()},
       "tape": {}}
for name, run in doc["tape"].items():
    led = Led()
    hd.judge_hold_tape(led, run["samples"], run["messages"])
    out["tape"][name] = led.checks
frames = [(i, 10 * i, bytes.fromhex(h)) for i, h in enumerate(doc["frames"])]
out["read_tape"] = hd.read_tape(frames, {"zidane_wire": 0, "garnet_wire": 2})
out["lost"] = {k: hd.lost_pred(**c) for k, c in doc["lost"].items()}
out["arrival"] = {k: hd.arrival_pred(c["figs"], c["value"], c["held0"], c["held1"]) for k, c in doc["arrival"].items()}
out["union"] = hd.figs_union(doc["union"])
out["timer"] = {k: list(hd.judge_timer_release(c["lines"], c["id"], c["slot"], c["via"], c["lo"], c["hi"], c.get("sup")))
                for k, c in doc["timer"].items()}
out["needle"] = hd.release_needle(7, 1)
print(json.dumps(out))
"""


def _hd_fig(value, via, arrival, release, slot=4) -> dict:
    return {"slot": slot, "value": value, "via": via, "arrival_ms": arrival, "release_ms": release}


def _hd_tape_run(**over) -> dict:
    """A synthetic tape-leg run: the guest's `act.guest` samples (with `hold`) and the engine's lines."""
    h = dict(BW.ACT_GUEST_HOLD_SENTINELS, on=True, lifeskip=True, held=5, rel_hit=4, rel_end=1,
             lag={"n": 4, "min": -20, "p50": 30, "max": 120},
             figs=[_hd_fig(26, "hit", 100, 230), _hd_fig(20, "hit", 900, 1010), _hd_fig(0, "arrival", 50, 50)])
    h.update(over.get("hold", {}))
    samples = [{"booted": True, "guest": {"running": 1, "hold": dict(h, held_now=1, rel_hit=h["rel_hit"] - 1)}},
               {"booted": True, "guest": {"running": 0, "hold": h}}]
    if over.get("no_hold"):
        samples = [{"booted": True, "guest": {"running": 0}}]
    messages = over.get("messages", [
        f"{BW.LOG_HOLD_FIRST_HELD} (id 11) on wire slot 4{BW.LOG_HOLD_FIRST_TAIL}",
        f"{BW.LOG_HOLD_HELD_IMPACT} of id 11 on wire slot 4{BW.LOG_HOLD_RELEASED_VIA}hit after 130 ms of battle time (lag 130 ms)"])
    return {"samples": samples, "messages": messages}


def test_the_s135_benchs_pure_judges_read_each_engine_and_can_fail():
    """coop_action_hold's judges, PURE, on synthetic runs -- each one GREEN on the s135 shape and RED on every shape it
    exists to catch: judge_figure_waits (amendment 8: a figure shown at ARRIVAL -- the `hold off` red --, shown twice,
    via the wrong reason, released before the hit, never hit, in another slot), judge_release (out of its window, the wrong
    reason, absent), judge_flinch (a flinch before the hit, none after), judge_hold_tape (an s134 guest fails closed; the
    knob -- nothing held -- is red on exactly HELD / LAG / FIG / LOG; a slot still held at rest, an unknown via, a hit
    figure released before its arrival, a fault line: each its own red), and read_tape (a Defend START found, a NOOP one
    skipped)."""
    hit = [{"figs": [], "first_hit_ms": -1}, {"figs": [], "first_hit_ms": 400},
           {"figs": [_hd_fig(5135, "hit", 0, 520)], "first_hit_ms": 400}]
    wait = {"green": {"samples": hit, "value": 5135, "slot": 4},
            "arrival": {"samples": [{"figs": [_hd_fig(5135, "arrival", 0, 0)], "first_hit_ms": -1},
                                    {"figs": [_hd_fig(5135, "arrival", 0, 0)], "first_hit_ms": 400}], "value": 5135},
            "twice": {"samples": hit[:2] + [{"figs": [_hd_fig(5135, "hit", 0, 520)] * 2, "first_hit_ms": 400}],
                      "value": 5135},
            "via": {"samples": hit[:2] + [{"figs": [_hd_fig(5135, "timeout", 0, 2500)], "first_hit_ms": 400}],
                    "value": 5135},
            "before": {"samples": hit[:2] + [{"figs": [_hd_fig(5135, "hit", 0, 300)], "first_hit_ms": 400}],
                       "value": 5135},
            "nohit": {"samples": [{"figs": [], "first_hit_ms": -1}], "value": 5135},
            "slot": {"samples": hit, "value": 5135, "slot": 5}}
    release = {"green": {"figs": [_hd_fig(5138, "timeout", 100, 2620)], "value": 5138, "via": "timeout", "lo": 2500,
                         "hi": 2750},
               "late": {"figs": [_hd_fig(5138, "timeout", 100, 2900)], "value": 5138, "via": "timeout", "lo": 2500,
                        "hi": 2750},
               "reason": {"figs": [_hd_fig(5138, "end", 100, 2620)], "value": 5138, "via": "timeout", "lo": 2500,
                          "hi": 2750},
               "absent": {"figs": [], "value": 5138, "via": "timeout", "lo": 2500, "hi": 2750}}
    flinch = {"green": {"mots": [[0, -1, 0], [400, 400, BW.MP_DAMAGE1], [450, 400, 0]], "hit": 400},
              "early": {"mots": [[0, -1, BW.MP_DAMAGE1], [400, 400, BW.MP_DAMAGE1]], "hit": 400},
              "none": {"mots": [[0, -1, 0], [400, 400, 0]], "hit": 400}}
    knob = {"held": 0, "rel_hit": 0, "rel_end": 0, "lag": {"n": 0, "min": -1, "p50": -1, "max": -1}, "figs": []}
    tape = {"green": _hd_tape_run(), "old": _hd_tape_run(no_hold=True),
            "knob": _hd_tape_run(hold=knob, messages=[]),
            "unrest": _hd_tape_run(hold={"held_now": 1}),
            "unknown": _hd_tape_run(hold={"figs": [_hd_fig(26, "hit", 100, 230), _hd_fig(3, "magic", 5, 5)]}),
            "order": _hd_tape_run(hold={"figs": [_hd_fig(26, "hit", 300, 230)]}),
            "fault": _hd_tape_run(messages=_hd_tape_run()["messages"] + [f"{BW.LOG_HOLD_FAULTED}NullReferenceException"]),
            # [s135 fix pass] a teardown's discard keeps the WHOLE account (harness-1): held 6 + queued 0 == 4 hit + 1 end +
            # 1 discarded -- green; a release counted twice beside a discard -- red (it read green before the fix)
            "discard": _hd_tape_run(hold={"held": 6, "discarded": 1}),
            "discard_double": _hd_tape_run(hold={"held": 6, "rel_hit": 5, "discarded": 1}),
            # the FIG judge reads the UNION of the samples' rings (harness-7): a hit shown early, evicted by the tail
            "evicted": {"samples": [{"booted": True, "guest": {"running": 1, "hold": dict(
                            BW.ACT_GUEST_HOLD_SENTINELS, on=True, lifeskip=True, held=1, held_now=1,
                            figs=[_hd_fig(26, "hit", 100, 230)])}},
                        {"booted": True, "guest": {"running": 0, "hold": dict(
                            BW.ACT_GUEST_HOLD_SENTINELS, on=True, lifeskip=True, held=1, rel_hit=1,
                            lag={"n": 1, "min": -1, "p50": -1, "max": -1},
                            figs=[_hd_fig(9000 + k, "arrival", 300 + k, 300 + k) for k in range(16)])}}],
                        "messages": _hd_tape_run()["messages"]}}
    # LOST's and L4N's predicates and their in-run reds (harness-3): green on their own shape, False on the sibling's
    lost = {"green": {"alive": False, "first_hit": -1, "held_now": 0, "mask_skips": 3, "base_skips": 3},
            "l2_op": {"alive": True, "first_hit": -1, "held_now": 1, "mask_skips": 4, "base_skips": 3},
            "hold_off_l2": {"alive": False, "first_hit": -1, "held_now": 0, "mask_skips": 3, "base_skips": 3}}
    arrival = {"green": {"figs": [_hd_fig(5139, "arrival", 10, 10)], "value": 5139, "held0": 2, "held1": 2},
               "l4": {"figs": [_hd_fig(5138, "timeout", 100, 2610)], "value": 5138, "held0": 1, "held1": 2},
               "hold_off_l4": {"figs": [_hd_fig(5138, "arrival", 100, 100)], "value": 5138, "held0": 1, "held1": 1}}
    union = [{"figs": [_hd_fig(1, "hit", 0, 5), _hd_fig(2, "arrival", 1, 1)]},
             {"figs": [_hd_fig(2, "arrival", 1, 1), _hd_fig(3, "late", 2, 2)]}, {"no": "figs"}, "junk"]
    # [fix pass: rtiming-1] judge_timer_release: the engine's own release line, never figs[] (a hidden unit shows none)
    rl = lambda i, slot, via, ms, tail="", head=BW.LOG_HOLD_HELD_IMPACT: (                       # noqa: E731
        f"16.10.2026 12:00:00 |M| {head} of id {i} on wire slot {slot}{BW.LOG_HOLD_RELEASED_VIA}{via} after {ms} ms of "
        f"battle time{tail}")
    tw = {"id": 7, "slot": 1, "via": "timeout", "lo": 2500, "hi": 2750}
    timer = {"green": dict(tw, lines=["noise", rl(8, 1, "timeout", 2510), rl(7, 2, "timeout", 2510),
                                      rl(7, 1, "timeout", 2610)]),
             "late": dict(tw, lines=[rl(7, 1, "timeout", 2900)]),
             "early": dict(tw, lines=[rl(7, 1, "timeout", 2400)]),
             "via": dict(tw, lines=[rl(7, 1, "end", 2610)]),
             "absent": dict(tw, lines=[]),
             "twice": dict(tw, lines=[rl(7, 1, "timeout", 2610)] * 2),
             "queued": dict(tw, lines=[rl(7, 1, "timeout", 2610, head=BW.LOG_HOLD_QUEUED_FRAME)]),
             "sup_green": dict(tw, sup=True, lines=[rl(7, 1, "timeout", 2610, BW.LOG_HOLD_SUPERSEDED)]),
             "sup_missing": dict(tw, sup=True, lines=[rl(7, 1, "timeout", 2610)]),
             "sup_unwanted": dict(tw, sup=False, lines=[rl(7, 1, "timeout", 2610, BW.LOG_HOLD_SUPERSEDED)])}
    dfd = BW.encode_action_start(7, 1, 3, 0, BW.ACTOR_IS_PLAYER, BW.CMD_DEFEND_ID, 179, 0x01, 0, 0, 0, BW.VFX_KIND_COMMON,
                                 4, -1, 5)
    noop = BW.encode_action_start(7, 1, 2, 1, BW.ACTOR_IS_PLAYER, BW.CMD_DEFEND_ID, 179, 0x02, 0, 0, 0, BW.VFX_KIND_NONE,
                                  0, -1, 5)
    env = {k: v for k, v in os.environ.items() if not k.startswith("COOP_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    out = subprocess.run([sys.executable, "-c", _ACT_HOLD_JUDGE, str(SCENARIOS), str(REPO / "tools")], env=env,
                         input=json.dumps({"wait": wait, "release": release, "flinch": flinch, "tape": tape,
                                           "frames": [noop.hex(), dfd.hex()], "lost": lost, "arrival": arrival,
                                           "union": union, "timer": timer}),
                         capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-2000:]
    got = json.loads(out.stdout.strip().splitlines()[-1])
    assert got["wait"]["green"][0], got["wait"]["green"]
    for name, needle in (("arrival", "BEFORE the replay's hit"), ("twice", "2 time(s)"), ("via", "want via 'hit'"),
                         ("before", "released at/after first_hit_ms 400"), ("nohit", "never hit"), ("slot", "slot 5")):
        ok, detail = got["wait"][name]
        assert not ok and needle in detail, (name, detail)
    assert [got["release"][k][0] for k in ("green", "late", "reason", "absent")] == [True, False, False, False]
    assert [got["flinch"][k][0] for k in ("green", "early", "none")] == [True, False, False]
    hold = ("S135T-P0", "S135T-HELD", "S135T-REST", "S135T-LAG", "S135T-FIG", "S135T-LOG")
    red = lambda name: sorted(c for c, (ok, _d) in got["tape"][name].items() if not ok)   # noqa: E731
    assert set(got["tape"]["green"]) == set(hold) and red("green") == [], got["tape"]["green"]
    assert red("old") == sorted(hold) and all("unreached" in d for _ok, d in got["tape"]["old"].values())
    assert red("knob") == sorted(("S135T-HELD", "S135T-LAG", "S135T-FIG", "S135T-LOG"))
    assert red("unrest") == ["S135T-REST"] and red("unknown") == ["S135T-FIG"] and red("order") == ["S135T-FIG"]
    assert red("fault") == ["S135T-LOG"] and "THE REAL-LINK MEASURE" in got["tape"]["green"]["S135T-LAG"][1]
    assert got["read_tape"]["defend"] == {"kind": BW.VFX_KIND_COMMON, "num": 4, "sub": 179}
    # [s135 fix pass] the discard's whole account; the union; a -1 ms lag is a measurement, never the sentinel
    assert red("discard") == [] and red("discard_double") == ["S135T-REST"], (got["tape"]["discard"],
                                                                            got["tape"]["discard_double"])
    assert red("evicted") == [] and "17 figure(s) shown over 2 sample(s), 1 via 'hit'" in got["tape"]["evicted"]["S135T-FIG"][1]
    assert BW.act_hold_at_rest(dict(BW.ACT_GUEST_HOLD_SENTINELS, held=2, rel_abort=1, discarded=1))
    assert not BW.act_hold_at_rest(dict(BW.ACT_GUEST_HOLD_SENTINELS, held=2, rel_abort=2, discarded=1))
    assert not BW.act_hold_at_rest(dict(BW.ACT_GUEST_HOLD_SENTINELS, held=3, queued=1, rel_abort=1, discarded=2))
    assert got["lost"] == {"green": True, "l2_op": False, "hold_off_l2": True}       # (`hold off`: no in-run red comes)
    assert got["arrival"] == {"green": True, "l4": False, "hold_off_l4": True}
    assert [(e["value"], e["via"]) for e in got["union"]] == [(1, "hit"), (2, "arrival"), (3, "late")]
    tm = {k: v[0] for k, v in got["timer"].items()}
    assert tm == {"green": True, "late": False, "early": False, "via": False, "absent": False, "twice": False,
                  "queued": False, "sup_green": True, "sup_missing": False, "sup_unwanted": False}, got["timer"]
    assert "released via 'timeout' after 2610 ms" in got["timer"]["green"][1]
    assert "0 release line(s)" in got["timer"]["queued"][1] and "2 release line(s)" in got["timer"]["twice"][1]
    assert got["needle"] == f"{BW.LOG_HOLD_HELD_IMPACT} of id 7 on wire slot 1{BW.LOG_HOLD_RELEASED_VIA}"


# =========================================================================== [ff9mapkit netsync s136]
# FALLBACK A, ONE STOCK CLIP PER UNCOVERED ACTION (studies/battle-coop/R3-DESIGN.md 3.3.5 as amended by
# R3-ACTION-REPLAY-AUDIT.md 2.4 -- amendments 1-6, decisions D-a / D-b / D-c; the audit's "s125"). Guest only, wire v14,
# harness protocol 5: one additive sub-object (`netsync.battle.act.guest.fallback`, the LAST key of `act.guest`), the
# `actbench fallback on|off` lever (no new sub-verb), one proof line. battlewire's twins of the PURE rules
# (ActFallbackPlayerClip ... ActFallbackCollapses, ActFallbackBook) EVALUATE ActFallbackSelfTest's OWN 30 rows off the stack
# -- translated statement by statement (its foreach, its book, its synthetic threads) -- each rule's mutant fails a row,
# the constants are pinned by name both ways, and s135 -- s136's calibration red -- is the ladder prefix through `acthold`
# (S135_CAPS): every check below that reads the key, the op or the proof line reads "cannot" there.
FB_ROW_MARKS = ("clip: a player's Item / AutoPotion / Throw plays MP_ITEM1 -- before the category (an item reads Void's)",
                "clip: Defend / Change -- and a monster-transformed caster -- play nothing",
                "enemy: the first caster PlayAnimation that is not Idle -- an earlier Idle is skipped, a later clip is not "
                "taken",
                "enemy: an Idle-only sequence (END's appended Idle), an empty one or an empty name plays nothing",
                "once: an old host's (caster, cmd, sub) plays once within 500 ms of battle time between arrivals, either way "
                "round",
                "covered: a START a newer one of its actor replaced, or an abort-all dropped -- no clip",
                "uncovered: no record (an old host, id 0, a START dropped, truncated or never received) plays the clip",
                "verdict: covered, then deduped, then a backlog drain (no clip), then the guards; else the action decides",
                "guard: a hit's caster plays; a self-cast plays only without a DmgMot (a Potion on self: its flinch owns a "
                "self-hit)",
                "collapse: a second clip on one actor in one frame overwrites the first -- counted once")
#: ActFallbackSelfTest's own helpers' bodies, pinned (the namespace below implements exactly these)
FB_HELPER_BLOCKS = {
    "private static BattleActionCode ActTestCode(String op, String anim)": [
        'return anim == null ? new BattleActionCode(op, "Char", "Caster") : new BattleActionCode(op, "Char", "Caster", '
        '"Anim", anim);'],
    "private static BattleActionThread ActTestThread(params BattleActionCode[] codes)": [
        "BattleActionThread t = new BattleActionThread();", "foreach (BattleActionCode c in codes)", "t.code.AddLast(c);",
        "return t;"],
    "private static List<BattleActionThread> ActTestThreads(params BattleActionThread[] threads)": [
        "return new List<BattleActionThread>(threads);"],
}
_FB_DECL = re.compile(r"(?:ActFallbackBook|BattleActionThread|Int64|Int32|String|Boolean) (\w+ = .+)", re.S)
_FB_FOREACH = re.compile(r"\w+ (\w+) in (.+)")


def _fb_python(stmts: list, indent: str = "") -> list:
    """ActFallbackSelfTest's statements as Python source lines: a Row -> ``__row(expr, name)``; a declaration (several
    declarators too) -> assignments; a ``foreach (T x in xs)`` -> ``for x in xs``; anything else (a call, an indexer
    assignment) as itself."""
    out = []
    for s in stmts:
        if not isinstance(s, str):
            kind, header, body = s
            m = _FB_FOREACH.fullmatch(header)
            assert kind == "foreach" and m, s
            out.append(f"{indent}for {m.group(1)} in {_rep_expr(m.group(2))}:")
            out += _fb_python(body, indent + "    ")
            continue
        masked, strings = _rep_mask(s)
        masked = _hold_init(masked)

        def back(code):
            for i, lit in enumerate(strings):
                code = code.replace(f"__S{i}__", lit)
            return code
        m = re.fullmatch(r"Row\((.*)\)", masked, re.S)
        if m:
            args = _rep_split(m.group(1), ",")
            assert len(args) == 4 and args[2:] == ["ref rows", "ref fail"], args
            name = " + ".join(f"str({_rep_expr(part, strings)})" for part in _rep_split(args[1], "+"))
            out.append(indent + back(f"__row({_rep_expr(args[0], strings)}, {name})"))
            continue
        m = _FB_DECL.fullmatch(masked)
        if m:
            for d in _rep_split(m.group(1), ","):
                name, _, value = d.partition("=")
                out.append(indent + back(f"{name.strip()} = {_rep_expr(value.strip(), strings)}"))
            continue
        out.append(indent + back(_rep_expr(masked, strings)))
    return out


def _fb_program() -> str:
    """ActFallbackSelfTest, read off the stack (the hunk that holds it whole), as one Python program."""
    block = _cs_block(REPLAY_FILE, "internal static Boolean ActFallbackSelfTest(")
    code = " ".join(_strip_comment(ln) for ln in block if not re.match(r"(?:internal|private|public) static ", ln))
    return "\n".join(_fb_python(_act_statements(code)))


def _fb_ns(**twins) -> dict:
    """The namespace ActFallbackSelfTest runs in: the constants by C# name (s134's, s135's and s136's; NetSyncBattle's,
    BattleCommandId's, CharacterCommandType's and PlayerMotionIndex's as attribute holders), the twins under their C#
    names (``twins`` replaces one -- a mutant), its own helpers (the pinned bodies of FB_HELPER_BLOCKS), btl_util's
    GetCommandTypeSafe, ``new ActFallbackBook()`` / ``ActBook.KeyOf``, and ``__row`` asserting each row."""
    tw = dict(covered=BW.act_fallback_covered, keyed=BW.act_fallback_keyed_by_id, winkey=BW.act_fallback_window_key,
              within=BW.act_fallback_within_window, guard=BW.act_fallback_guard, endblocks=BW.act_fallback_end_blocks,
              verdict=BW.act_fallback_verdict, player=BW.act_fallback_player_clip, item=BW.act_fallback_item_or_throw,
              defend=BW.act_fallback_defend_or_change, enemycmd=BW.act_fallback_enemy_seq_cmd,
              motion=BW.act_fallback_motion, kindname=BW.act_fallback_kind_name, first=BW.act_fallback_first_clip,
              collapses=BW.act_fallback_collapses, book=BW.ActFallbackBook, typesafe=BW.command_type_safe,
              # [fix pass] the deferral (cover-2), the restore's kept pose (timing-2), the write's refusal (stock-1)
              defers=BW.act_fallback_defers, deferstep=BW.act_fallback_defer_step, keepspose=BW.act_fallback_keeps_pose,
              playable=BW.act_fallback_clip_playable,
              # [fix pass 2: rcover-2] the record deferral
              awaits=BW.act_fallback_awaits_record, recordstep=BW.act_fallback_record_step)
    tw.update(twins)
    ns = dict(BW.CS_REPLAY_CONSTANTS)
    ns.update(BW.CS_HOLD_CONSTANTS)
    ns.update(BW.CS_FALLBACK_CONSTANTS)
    names: list = []

    def row(ok, name):
        if ok is not True:
            raise AssertionError(f"row {name!r} is {ok!r} for the twins")
        names.append(name)

    def member(obj, name):
        return getattr(obj, _snake(name))

    class _Book:                                                       # `ActBook.KeyOf(..)`
        KeyOf = staticmethod(BW.ActBook.key_of)

    # `new ActFallbackBook()`: the twin (or a mutant of it) reading THIS namespace's window rule, as the C# book reads the
    # static ActFallbackWithinWindow
    fb_book = type("_NsFallbackBook", (tw["book"],), {"within": staticmethod(tw["within"])})
    ids = {k.split(".", 1)[1]: v for k, v in BW.CS_STOCK_IDS.items() if k.startswith("BattleCommandId.")}
    ns.update(__row=row, __m=member, __names__=names,
              NetSyncBattle=SimpleNamespace(**BW.CS_ACTION_CONSTANTS), BattleCommandId=SimpleNamespace(**ids),
              CharacterCommandType=SimpleNamespace(Normal=BW.CMD_TYPE_NORMAL, Ability=BW.CMD_TYPE_ABILITY,
                                                   Item=BW.CMD_TYPE_ITEM, Throw=BW.CMD_TYPE_THROW,
                                                   Instant=BW.CMD_TYPE_INSTANT),
              BattlePlayerCharacter=SimpleNamespace(PlayerMotionIndex=SimpleNamespace(
                  MP_ATTACK=BW.MP_ATTACK, MP_MAGIC=BW.MP_MAGIC, MP_ITEM1=BW.MP_ITEM1)),
              btl_util=SimpleNamespace(get_command_type_safe=lambda c: tw["typesafe"](c)),
              ActTestNonce=BW.ACT_REPLAY_TEST_NONCE, ActBook=_Book, ActViaArrival=BW.ACT_VIA_ARRIVAL,
              ActViaDeferred=BW.ACT_VIA_DEFERRED, ActFallbackBook=fb_book,
              ActFallbackDefers=tw["defers"], ActFallbackDeferStep=tw["deferstep"], ActFallbackKeepsPose=tw["keepspose"],
              ActFallbackClipPlayable=tw["playable"], ActFallbackAwaitsRecord=tw["awaits"],
              ActFallbackRecordStep=tw["recordstep"],
              ActFallbackCovered=tw["covered"], ActFallbackKeyedById=tw["keyed"], ActFallbackWindowKey=tw["winkey"],
              ActFallbackWithinWindow=tw["within"], ActFallbackGuard=tw["guard"], ActFallbackEndBlocks=tw["endblocks"],
              ActFallbackVerdict=tw["verdict"], ActFallbackPlayerClip=tw["player"], ActFallbackItemOrThrow=tw["item"],
              ActFallbackDefendOrChange=tw["defend"], ActFallbackEnemySeqCmd=tw["enemycmd"],
              ActFallbackMotion=tw["motion"], ActFallbackKindName=tw["kindname"], ActFallbackFirstClip=tw["first"],
              ActFallbackCollapses=tw["collapses"],
              # the selftest's helpers (FB_HELPER_BLOCKS' bodies)
              ActTestCode=lambda op, anim: (BW.ActCode(op, "Char", "Caster") if anim is None else
                                            BW.ActCode(op, "Char", "Caster", "Anim", anim)),
              ActTestThread=lambda *codes: BW.ActThread(*codes), ActTestThreads=lambda *threads: list(threads))
    return ns


def _run_fb_selftest(**twins) -> list:
    ns = _fb_ns(**twins)
    exec(compile(_fb_program(), "<ActFallbackSelfTest>", "exec"), ns)              # noqa: S102 -- the stack's own rows
    return ns["__names__"]


def test_the_fallback_twins_evaluate_every_fallback_selftest_row_off_the_stack():
    """battlewire's s136 twins (the player clip, the command predicates, the motions and kind names, the enemy clip, the
    key, the once-per-action book and its window, covered vs uncovered, the verdict's order, the call-site guards, the end
    block, the collapse) against ActFallbackSelfTest's OWN rows, EVALUATED in order: 30, the proof line's count. Its
    helpers are the pinned bodies (FB_HELPER_BLOCKS). [fix pass] + the sliding window, the run-away hold and abort-all end
    blocks, the deferral (cover-2), the restore's kept pose (timing-2) and the write's refusal (stock-1). [fix pass 2] + the
    record deferral (rcover-2: two `defer` rows), the Loop / scripted enemy commands (rstock-1) and the ORDER-aware kept
    pose (rtiming-1)."""
    names = _run_fb_selftest()
    assert len(names) == BW.FALLBACK_SELFTEST_ROWS == 30 and len(set(names)) == 30, names
    assert all(mark in names for mark in FB_ROW_MARKS), set(FB_ROW_MARKS) - set(names)
    prefix = lambda n: n.split(":", 1)[0]                                # noqa: E731
    assert [sum(prefix(n) == p for n in names) for p in ("clip", "enemy", "key", "once", "covered", "uncovered",
                                                         "verdict", "guard", "collapse", "defer", "restore", "write")] \
        == [6, 3, 1, 5, 2, 2, 1, 3, 1, 4, 1, 1], names
    assert sum("ref rows, ref fail);" in ln for ln in net_lines(REPLAY_FILE, r".", [_patch_bytes("s136")])) == 30
    for head, body in FB_HELPER_BLOCKS.items():
        start = head.split("(", 1)[0] + "("
        got = [c for c in (_strip_comment(t) for t in _cs_block(REPLAY_FILE, start, "}")) if c][2:]
        assert got[:len(body)] == body, (head, got)


def _fb_verdict_with(**changes):
    """ActFallbackVerdict with ONE order changed (the twin's own body otherwise)."""
    def verdict(covered, seen, backlog, guard_ok):
        if changes.get("backlog_first") and backlog and not covered:
            return BW.ACT_FB_BACKLOG                                    # a backlog drain ahead of the dedupe
        if changes.get("guard_first") and not guard_ok and not covered:
            return BW.ACT_FB_GUARDED                                    # the guards ahead of the dedupe / backlog
        if changes.get("seen_first") and seen:
            return BW.ACT_FB_DEDUPED                                    # a covered impact counted deduped
        return BW.act_fallback_verdict(covered, seen, backlog, guard_ok)
    return verdict


class _FbBookNoRespend(BW.ActFallbackBook):
    """A book whose window key keeps its FIRST arrival (a decision after the window never re-spends it)."""

    def note(self, by_id, id_key, win_key, arrive_ms):
        if not by_id and int(win_key) in self.win:
            return
        super().note(by_id, id_key, win_key, arrive_ms)


class _FbBookIdsIgnored(BW.ActFallbackBook):
    """A book that forgets the id keys (every impact of one action plays again)."""

    def seen(self, by_id, id_key, win_key, arrive_ms):
        return False if by_id else super().seen(by_id, id_key, win_key, arrive_ms)


class _FbBookRewinds(BW.ActFallbackBook):
    """[fix pass: timing-6] A book whose window key keeps the LAST noted arrival, older or not (a queued frame rewinds it)."""

    def note(self, by_id, id_key, win_key, arrive_ms):
        if not by_id:
            self.win[int(win_key)] = int(arrive_ms)
            return
        super().note(by_id, id_key, win_key, arrive_ms)


class _FbBookNoSlide(BW.ActFallbackBook):
    """[fix pass: cover-5] A book whose window never follows a deduped sibling (anchored at the decision)."""

    def slide(self, win_key, arrive_ms):
        return None


class _FbBookSlidesBack(BW.ActFallbackBook):
    """[fix pass: cover-5] A book whose window follows ANY sibling, an older one too."""

    def slide(self, win_key, arrive_ms):
        if int(win_key) in self.win:
            self.win[int(win_key)] = int(arrive_ms)


class _FbBookSlideSpends(BW.ActFallbackBook):
    """[fix pass: cover-5] A book whose slide spends a key never spent."""

    def slide(self, win_key, arrive_ms):
        self.win[int(win_key)] = max(self.win.get(int(win_key), int(arrive_ms)), int(arrive_ms))


@pytest.mark.parametrize("twins", [
    {"player": lambda item, defend, transform, cat: BW.ACT_FB_MAGIC if cat & 16 else
        BW.act_fallback_player_clip(item, defend, transform, cat)},
    {"player": lambda item, defend, transform, cat: BW.act_fallback_player_clip(item, defend, False, cat)},
    {"player": lambda item, defend, transform, cat: BW.act_fallback_player_clip(item, False, transform, cat)},
    {"player": lambda item, defend, transform, cat: BW.act_fallback_player_clip(item, defend, transform, cat & ~16)},
    {"item": lambda t: t == BW.CMD_TYPE_ITEM},
    {"typesafe": lambda c: BW.CMD_TYPE_ITEM if c == BW.CMD_ITEM_ID else BW.CMD_TYPE_NORMAL},
    {"defend": lambda c: c == BW.CMD_DEFEND_ID},
    {"enemycmd": lambda c: c in (BW.CMD_ENEMY_ATK, BW.CMD_ENEMY_COUNTER)},
    {"enemycmd": lambda c: c in (BW.CMD_ENEMY_ATK, BW.CMD_ENEMY_COUNTER, BW.CMD_ENEMY_DYING, BW.CMD_ENEMY_REACTION)},
    {"enemycmd": lambda c: BW.act_fallback_enemy_seq_cmd(c) and c != BW.CMD_NONE_ID},
    {"enemycmd": lambda c: BW.act_fallback_enemy_seq_cmd(c) or c == BW.CMD_MAGIC_COUNTER},
    {"motion": lambda k: BW.MP_MAGIC if k == BW.ACT_FB_ITEM else BW.act_fallback_motion(k)},
    {"kindname": lambda k: {BW.ACT_FB_ITEM: "items"}.get(k, BW.act_fallback_kind_name(k))},
    {"first": lambda threads: next((c.argument.get("Anim") for th in threads or () for c in th.code
                                    if c.operation == "PlayAnimation" and c.argument.get("Char") == "Caster"), None)},
    {"first": lambda threads: next((c.argument.get("Anim") for th in threads or () for c in th.code
                                    if c.operation == "PlayAnimation" and c.argument.get("Anim") not in (None, "", "Idle")),
                                   None)},
    {"first": lambda threads: BW.act_fallback_first_clip(list(reversed(threads)) if threads else threads)},
    {"first": lambda threads: next((c.argument.get("Anim") for th in threads or () for c in th.code
                                    if c.operation == "PlayAnimation" and c.argument.get("Char") == "Caster"
                                    and c.argument.get("Anim") != "Idle"), None)},
    {"keyed": lambda has_ext, kind, act_id: bool(has_ext) and act_id != 0},
    {"keyed": lambda has_ext, kind, act_id: bool(has_ext) and kind == BW.ACT_EXT_IMPACT},
    {"winkey": lambda slot, player, cmd, sub: BW.act_fallback_window_key(slot, False, cmd, sub)},
    {"winkey": lambda slot, player, cmd, sub: BW.act_fallback_window_key(slot, player, cmd, 0)},
    {"winkey": lambda slot, player, cmd, sub: BW.act_fallback_window_key(0, player, cmd, sub)},
    {"within": lambda spent, arrive: abs(arrive - spent) <= BW.ACT_FALLBACK_WINDOW_MS},
    {"within": lambda spent, arrive: 0 <= arrive - spent < BW.ACT_FALLBACK_WINDOW_MS},
    {"book": _FbBookNoRespend}, {"book": _FbBookIdsIgnored}, {"book": _FbBookRewinds}, {"book": _FbBookNoSlide},
    {"book": _FbBookSlidesBack}, {"book": _FbBookSlideSpends},
    {"covered": lambda state, why: state in (BW.ACT_ST_REGISTERED, BW.ACT_ST_WAITING, BW.ACT_ST_RUNNING, BW.ACT_ST_ENDED,
                                             BW.ACT_ST_NOOP)},
    {"covered": lambda state, why: BW.act_fallback_covered(state, why) or state == BW.ACT_ST_DECLINED},
    {"covered": lambda state, why: BW.act_fallback_covered(state, why) and why != "superseded"},
    {"covered": lambda state, why: state in (BW.ACT_ST_REGISTERED, BW.ACT_ST_WAITING, BW.ACT_ST_RUNNING, BW.ACT_ST_ENDED,
                                             BW.ACT_ST_ABORTED, BW.ACT_ST_NOOP) or why == "superseded"},
    {"covered": lambda state, why: BW.act_fallback_covered(state, why) or state < 0},
    {"verdict": _fb_verdict_with(backlog_first=True)}, {"verdict": _fb_verdict_with(guard_first=True)},
    {"verdict": _fb_verdict_with(seen_first=True)},
    {"guard": lambda sc, dmg, lethal, revive, hidden, can, acting, end: not sc and not lethal and not revive
        and not hidden and can and not acting and not end},
    {"guard": lambda sc, dmg, lethal, revive, hidden, can, acting, end: not lethal and not revive and not hidden and can
        and not acting and not end},
    {"guard": lambda sc, dmg, lethal, revive, hidden, can, acting, end: (not sc or not dmg) and not lethal and not hidden
        and can and not acting and not end},
    {"guard": lambda sc, dmg, lethal, revive, hidden, can, acting, end: (not sc or not dmg) and not lethal and not revive
        and not hidden and can and not end},
    {"endblocks": lambda end, held, aborting, leaving, via: bool(end) or bool(held) or bool(aborting) or bool(leaving)},
    {"endblocks": lambda end, held, aborting, leaving, via: bool(end) or bool(held) or bool(aborting) or via == "end-inject"},
    {"endblocks": lambda end, held, aborting, leaving, via: BW.act_fallback_end_blocks(end, False, aborting, leaving, via)},
    {"endblocks": lambda end, held, aborting, leaving, via: BW.act_fallback_end_blocks(end, held, False, leaving, via)},
    {"endblocks": lambda end, held, aborting, leaving, via: BW.act_fallback_end_blocks(end, held, aborting, leaving, via)
        or via == BW.ACT_VIA_DEFERRED},
    {"collapses": lambda mask, btl_id: (mask & btl_id) != 0 or btl_id == 0},
    {"defers": lambda by_id, idle, acting: bool(acting) and bool(idle)},
    {"defers": lambda by_id, idle, acting: bool(by_id) and bool(acting)},
    {"defers": lambda by_id, idle, acting: bool(by_id) and bool(idle)},
    {"deferstep": lambda exp, acting, holder, pending: BW.ACT_FB_DEFER_WAIT if acting and not exp else
        BW.act_fallback_defer_step(exp, acting, holder, pending)},
    {"deferstep": lambda exp, acting, holder, pending: BW.act_fallback_defer_step(exp, acting, holder, False)},
    {"deferstep": lambda exp, acting, holder, pending: BW.act_fallback_defer_step(False, acting, holder, pending)},
    {"keepspose": lambda aborted, after, shows: bool(shows)},
    {"keepspose": lambda aborted, after, shows: not aborted or bool(after)},
    {"keepspose": lambda aborted, after, shows: not aborted and bool(shows)},
    {"awaits": lambda covered, pending: bool(covered)},
    {"awaits": lambda covered, pending: False},
    {"awaits": lambda covered, pending: bool(pending)},
    {"recordstep": lambda exp, pending: BW.ACT_FB_DEFER_WAIT if pending else BW.ACT_FB_DEFER_PLAY},
    {"recordstep": lambda exp, pending: BW.ACT_FB_DEFER_DROP if exp and pending else BW.act_fallback_record_step(exp,
                                                                                                                pending)},
    {"recordstep": lambda exp, pending: BW.ACT_FB_DEFER_COVERED if exp else BW.act_fallback_record_step(exp, pending)},
    {"playable": lambda has_anim, has_clip: bool(has_anim)},
    {"playable": lambda has_anim, has_clip: bool(has_clip)}],
    ids=["clip-category-before-item", "clip-transform-ignored", "clip-defend-ignored", "clip-magic-bit-missed",
         "item-throw-missed", "typesafe-autopotion-missed", "defend-change-missed", "enemycmd-dying-missed",
         "enemycmd-loop-missed", "enemycmd-scripted-missed", "enemycmd-magiccounter-taken",
         "motion-item-as-magic", "kindname-item-renamed", "first-idle-taken", "first-any-char", "first-subthreads-first",
         "first-empty-name-taken", "keyed-start-ext-keys", "keyed-id0-keys", "winkey-side-dropped",
         "winkey-sub-dropped", "winkey-slot-dropped", "within-boundary-inclusive", "within-one-way-round", "book-window-never-respent",
         "book-ids-forgotten", "book-older-rewinds", "book-window-never-slides", "book-slides-back", "book-slide-spends",
         "covered-aborted-uncovered", "covered-every-decline", "covered-superseded-uncovered",
         "covered-abort-all-uncovered", "covered-no-record", "verdict-backlog-before-dedupe",
         "verdict-guard-before-dedupe", "verdict-covered-counted-deduped", "guard-self-cast-always",
         "guard-self-hit-allowed", "guard-revive-allowed", "guard-acting-allowed", "endblocks-end-inject-plays",
         "endblocks-leave-plays", "endblocks-hold-plays", "endblocks-abortall-plays", "endblocks-deferred-blocked",
         "collapses-id0", "defers-id0-defers", "defers-any-refusal-defers", "defers-free-caster-defers",
         "deferstep-newer-waits", "deferstep-pending-ignored", "deferstep-never-stale", "keepspose-aborted-kept",
         "keepspose-idle-kept", "keepspose-order-blind", "awaits-any-covered", "awaits-never", "awaits-pending-only",
         "recordstep-never-stale", "recordstep-stale-guarded", "recordstep-stale-first", "playable-anim-only",
         "playable-clip-only"])
def test_each_fallback_rule_mutant_fails_a_selftest_row(twins):
    """A CHECK THAT CANNOT FAIL is no check: each rule of the clip choice, the predicates, the enemy clip, the key, the
    book, the covered rule, the verdict's order, the guards, the end block and the collapse, broken alone in its twin,
    fails one of the engine's own rows."""
    _fb_program()                                                       # (its own parse outside the raises)
    with pytest.raises(AssertionError, match=r"^row ['\"]"):
        _run_fb_selftest(**twins)


def test_the_fallback_twins_take_the_engines_parameters_in_its_order():
    """Each s136 twin's parameters ARE its C# method's, in order (camelCase -> snake_case)."""
    for start, fn in (("internal static Boolean ActFallbackCovered(", BW.act_fallback_covered),
                      ("internal static Boolean ActFallbackKeyedById(", BW.act_fallback_keyed_by_id),
                      ("internal static Int64 ActFallbackWindowKey(", BW.act_fallback_window_key),
                      ("internal static Boolean ActFallbackWithinWindow(", BW.act_fallback_within_window),
                      ("internal static Boolean ActFallbackGuard(", BW.act_fallback_guard),
                      ("internal static Boolean ActFallbackEndBlocks(", BW.act_fallback_end_blocks),
                      ("internal static Int32 ActFallbackVerdict(", BW.act_fallback_verdict),
                      ("internal static Int32 ActFallbackPlayerClip(", BW.act_fallback_player_clip),
                      ("internal static Boolean ActFallbackItemOrThrow(", BW.act_fallback_item_or_throw),
                      ("internal static Boolean ActFallbackDefendOrChange(", BW.act_fallback_defend_or_change),
                      ("internal static Boolean ActFallbackEnemySeqCmd(", BW.act_fallback_enemy_seq_cmd),
                      ("internal static BattlePlayerCharacter.PlayerMotionIndex ActFallbackMotion(", BW.act_fallback_motion),
                      ("internal static String ActFallbackKindName(", BW.act_fallback_kind_name),
                      ("internal static String ActFallbackFirstClip(", BW.act_fallback_first_clip),
                      ("internal static Boolean ActFallbackCollapses(", BW.act_fallback_collapses),
                      ("internal static Boolean ActFallbackDefers(", BW.act_fallback_defers),
                      ("internal static Int32 ActFallbackDeferStep(", BW.act_fallback_defer_step),
                      ("internal static Boolean ActFallbackKeepsPose(", BW.act_fallback_keeps_pose),
                      ("internal static Boolean ActFallbackAwaitsRecord(", BW.act_fallback_awaits_record),
                      ("internal static Int32 ActFallbackRecordStep(", BW.act_fallback_record_step),
                      ("internal static Boolean ActFallbackClipPlayable(", BW.act_fallback_clip_playable),
                      ("public Boolean Seen(", BW.ActFallbackBook.seen),
                      ("public void Note(", BW.ActFallbackBook.note),
                      ("public void Slide(", BW.ActFallbackBook.slide)):
        cs = [_snake(p) for p in _cs_signature(REPLAY_FILE, start)]
        params = _twin_params(fn)
        assert cs == (params[1:] if params[:1] == ["self"] else params), (start, cs, params)


def _fb_consts() -> dict:
    """Every `internal const Int32` the s136 patch declares (comments stripped) -> its value."""
    out = {}
    for line in net_lines(REPLAY_FILE, r"internal const Int32 ", [_patch_bytes("s136")]):
        m = re.fullmatch(r"internal const Int32 (.*);", _strip_comment(line))
        assert m, line
        for decl in m.group(1).split(","):
            d = re.fullmatch(r"\s*(\w+) = (0x[0-9A-Fa-f]+|-?\d+)\s*", decl)
            assert d, decl
            out[d.group(1)] = int(d.group(2), 0)
    return out


def test_the_fallback_constants_are_the_stacks_both_ways():
    """THE PIN: every CS_FALLBACK_CONSTANTS entry is NetSyncDiorama.Replay.cs's constant of that name and value, and every
    `internal const Int32` the s136 patch declares is in the table -- a constant added, renamed or retuned on either side
    turns this red. ActFallbackKindName's names are pinned by value."""
    cs = _fb_consts()
    assert cs == BW.CS_FALLBACK_CONSTANTS, sorted(set(cs.items()) ^ set(BW.CS_FALLBACK_CONSTANTS.items()))
    assert (cs["ActFallbackWindowMs"], cs["ActFallbackLogMax"]) == (500, 8)
    assert (cs["ActFallbackDeferMaxMs"], cs["ActFallbackDeferCap"]) == (4000, 16)          # [fix pass: cover-2]
    assert _battle_text('internal const String ActViaDeferred = "deferred";') and BW.ACT_VIA_DEFERRED == "deferred"
    for kind, name in BW.ACT_FB_KIND_NAMES.items():
        const = next(k for k, v in BW.CS_FALLBACK_CONSTANTS.items() if k.startswith("ActFb") and v == kind
                     and k not in ("ActFbDecide", "ActFbCovered", "ActFbDeduped", "ActFbBacklog", "ActFbGuarded"))
        assert _battle_text(f'case {const}: return "{name}";'), (const, name)
    assert _battle_text('default: return "none";')


def test_the_fallback_stock_values_are_the_clones_when_it_is_here():
    """The stock values fallback A's twins read beyond CS_STOCK_IDS (which test_the_stock_ids_... pins, Throw / AutoPotion
    / Fire included): PlayerMotionIndex's MP_ATTACK / MP_MAGIC / MP_ITEM1 by the enum's own order, and CharacterCommandType's
    five values -- read off the shared Memoria clone when this machine has it."""
    root = pathlib.Path(r"C:\gd\FFIX\Memoria\Assembly-CSharp")
    bpc = root / "Global" / "battle" / "BattlePlayerCharacter.cs"
    cct = root / "Memoria" / "Data" / "Characters" / "CharacterCommandType.cs"
    if not bpc.is_file() or not cct.is_file():
        pytest.skip("the shared Memoria clone is not on this machine")
    text = bpc.read_text(encoding="utf-8-sig", errors="replace")
    body = text[text.index("enum PlayerMotionIndex"):]
    body = body[body.index("{") + 1:body.index("}")]
    members = [m.strip() for m in body.replace("\n", " ").split(",") if m.strip()]
    assert (members.index("MP_ATTACK"), members.index("MP_MAGIC"), members.index("MP_ITEM1")) == (
        BW.MP_ATTACK, BW.MP_MAGIC, BW.MP_ITEM1)
    text = cct.read_text(encoding="utf-8-sig", errors="replace")
    got = {m.group(1): int(m.group(2)) for m in re.finditer(r"^\s*(\w+)\s*=\s*(\d+)", text, re.M)}
    assert got == {"Normal": BW.CMD_TYPE_NORMAL, "Ability": BW.CMD_TYPE_ABILITY, "Item": BW.CMD_TYPE_ITEM,
                   "Throw": BW.CMD_TYPE_THROW, "Instant": BW.CMD_TYPE_INSTANT}, got


def test_the_fallback_block_is_act_guests_last_key_at_the_catch_lines_sentinels():
    """THE CATCH-LITERAL RE-PIN for s136: `act.guest.fallback` in AppendNetsync's SECOND catch literal, right after `hold`,
    at its sentinels (`last` a nullable record); the line stays ONE line of two literals; AppendActGuestFallback writes
    the keys in the catch line's order (`last`'s fields in ACT_FALLBACK_LAST_KEYS' order), each through its NetSyncDiorama
    getter; AppendActGuest calls it after the hold's; published in every role; protocol stays 5."""
    catch = net_lines("HarnessAgent.cs", r'outer\.Append\("\\"netsync\\":\{\\"enabled')
    assert len(catch) == 1 and catch[0].count(".Append(") == 3 and ".Append(NetsyncF3Retired)" in catch[0], catch
    a, b = _literals(catch[0])
    assert '\\"figs\\":[]},\\"fallback\\":{\\"on\\":false,\\"clips\\":0,' in b and "fallback" not in a
    nothing = _agent_netsync_nothing()[0]
    assert _battle_of(nothing)["act"]["guest"]["fallback"] == BW.ACT_GUEST_FALLBACK_SENTINELS
    assert list(_battle_of(nothing)["act"]["guest"])[-2:] == ["hold", "fallback"]
    assert _catch_doc_in("s136") == nothing                                # s136 wrote the live catch line whole
    new = [t for _h, _k, t in _new_side("HarnessAgent.cs", _patch_bytes("s136"))]
    i = next(k for k, t in enumerate(new) if t.startswith("private static void AppendActGuestFallback("))
    j = next(k for k in range(i, len(new)) if new[k].startswith("// [ff9mapkit netsync B5] stage 5:"))
    body = " ".join(_strip_comment(t) for t in new[i:j])
    names = re.findall(r'(?:Bool|Num|Str)\(sb, "(\w+)"', body)
    top = [k for k in BW.ACT_GUEST_FALLBACK_SENTINELS if k != "last"]
    assert names == top + list(BW.ACT_FALLBACK_LAST_KEYS), names
    for k in top:
        assert re.search(rf'(?:Bool|Num)\(sb, "{k}", Memoria\.Netsync\.NetSyncDiorama\.HarnessFallback\w+\)', body), k
    assert '"last":null' in body.replace("\\", "") and '"last":{' in body.replace("\\", "")
    assert _added_after("s136", "HarnessAgent.cs", "AppendActGuestHold(sb);", "AppendActGuestFallback(sb);")
    assert net_lines("HarnessAgent.cs", r"public const Int32 ProtocolVersion = ") == ["public const Int32 ProtocolVersion = 5;"]
    assert not _battle_text("IsSelfTestRole ? _fb")                     # audit 3.6: published in EVERY role
    assert _battle_text("internal static Boolean HarnessFallbackOn { get { return ActFallbackOn; } }")
    assert _battle_text("private static Boolean ActFallbackOn { get { return !(_benchFallbackOff && "
                        "NetSyncClient.IsSelfTestRole); } }")


def test_state_reads_the_fallback_block_absent_on_s135_as_cannot():
    """On s135's catch block (s136's calibration red) every `act.guest.fallback` accessor reads None and
    `coop_act_fallback` False; on the live block they read the sentinels and True; a published block reads its values, a
    mistyped one None, and `last` a copy (None at null)."""
    old = State({"frame": 1, "netsync": _catch_doc_in("s135")})
    live = State({"frame": 1, "netsync": _agent_netsync_nothing()[0]})
    names = [n for p, n in State.NETSYNC_BATTLE_ACCESSORS.items()
             if p == "act.guest.fallback" or p.startswith("act.guest.fallback.")]
    assert len(names) == len(_leaves({"act": {"guest": {"fallback": BW.ACT_GUEST_FALLBACK_SENTINELS}}})) + 1 == 11, names
    assert (State({"frame": 1}).coop_act_fallback, old.coop_act_fallback, live.coop_act_fallback) == (None, False, True)
    assert old.coop_act_hold is True                                    # (s135's own block is there)
    assert all(getattr(old, n) is None for n in names)
    assert all(getattr(live, n) is not None for n in names if n != "coop_act_fallback_last")
    assert (live.coop_act_fallback_last, live.coop_act_fallback_on, live.coop_act_fallback_clips) == (None, False, 0)
    doc = _agent_netsync_nothing()[0]
    doc["battle"]["act"]["guest"]["fallback"].update(
        clips=2, deduped="2", on=True,
        last={"actor": 2, "clip": "ANH_MAIN_B0_006_210", "cmd": 14, "sub": 236, "keyed_by": "id", "kind": "item", "id": 7,
              "via": "arrival", "ms": 1234})
    st = State({"frame": 1, "netsync": doc})
    assert (st.coop_act_fallback_clips, st.coop_act_fallback_deduped, st.coop_act_fallback_on) == (2, None, True)
    last = st.coop_act_fallback_last
    last["clip"] = ""
    assert st.coop_act_fallback_last["clip"] == "ANH_MAIN_B0_006_210"   # a copy
    assert BW.act_fallback_decided(dict(BW.ACT_GUEST_FALLBACK_SENTINELS, deduped="x")) is None   # (a mistyped bucket)
    assert BW.act_fallback_decided(None) is None
    assert BW.act_fallback_decided(dict(BW.ACT_GUEST_FALLBACK_SENTINELS, clips=2, none=1, covered=4)) == 7


def test_a_fresh_stand_in_publishes_the_fallback_block_and_s135_none(game):
    """The default stand-in (s136) publishes `act.guest.fallback` at the agent's sentinels with no client -- but `on` the
    live read at rest (true); the stand-in at s135 publishes no `fallback`, no 'action fallback' proof line, and answers
    the fallback forms in s135's words (its usage for a 2- or 4-word form, its "unknown op" for a 3-word one)."""
    want = dict(BW.ACT_GUEST_FALLBACK_SENTINELS, on=True)
    assert _battle_of(FakeGame(game)._netsync_doc())["act"]["guest"]["fallback"] == want
    old = _selftest(FakeGame(game))
    old.netsync_caps = S135_CAPS
    assert "fallback" not in _battle_of(old._netsync_doc())["act"]["guest"]
    assert set(_leaves(_battle_of(old._netsync_doc()))) == set(_leaves(_battle_of(_catch_doc_in("s135"))))
    usage = f"{FG.NETSYNC_ACTBENCH_USAGE_S135}\r\nParameter name: netsync actbench"
    for args, words in ((["actbench", "fallback", "off"], "netsync actbench: unknown op 'fallback' (tape|hoststarts)"),
                        (["actbench", "fallback"], usage), (["actbench", "fallback", "off", "now"], usage)):
        with pytest.raises(RuntimeError) as err:
            old._netsync(args)
        assert str(err.value) == words, args


FB_REFUSALS = [
    # (a fragment the agent says -- ONE C# literal of the stack, or a piece --, the args, where: None / selftest)
    ("netsync actbench: needs the selftest role (netsync selftest 1)", ["actbench", "fallback", "off"], None),
    (BW.FALLBACK_USAGE, ["actbench", "fallback", "maybe"], "selftest"),
    (BW.FALLBACK_USAGE, ["actbench", "fallback"], "selftest"),
    (BW.FALLBACK_USAGE, ["actbench", "fallback", "on", "x"], "selftest"),
]


@pytest.mark.parametrize("fragment,args,where", FB_REFUSALS, ids=[f"{r[0][:30]}-{i}" for i, r in enumerate(FB_REFUSALS)])
def test_the_stand_in_refuses_the_fallback_op_in_the_agents_words(game, fragment, args, where):
    """Every fallback `actbench` gate the stand-in models refuses with the engine's own words (each a literal of the
    stack: HarnessActGuestBench's role gate, HarnessActFallbackBench's parse -- its WHOLE refusal)."""
    assert _battle_text(fragment), f"the live stack no longer says {fragment!r}"
    fake = FakeGame(game)
    if where == "selftest":
        _selftest(fake)
    with pytest.raises(RuntimeError) as err:
        fake._netsync(args)
    assert (str(err.value) == fragment) if where == "selftest" else (fragment in str(err.value)), str(err.value)


def test_the_fallback_op_is_the_agents_and_the_driver_gates_it_by_act_guest_fallback(game):
    """`fallback` is IsActGuestBenchOp's (a case of its own) and HarnessActGuestBench's (routed to
    HarnessActFallbackBench); the driver keys it on `act.guest.fallback` (s136), refuses a malformed form before the step
    in the engine's words, and on an s135 engine refuses every fallback form naming s136 and what s135 would answer."""
    new = [c for c in (_strip_comment(t) for _h, _k, t in _new_side(REPLAY_FILE, _patch_bytes("s136"))) if c]
    for site in (['case "unit":', 'case "fallback":', "return true;", 'case "tape":', 'return value == "play";'],
                 ['case "fallback":', "return HarnessActFallbackBench(args, val, out why);", "default:"]):
        assert any(new[k:k + len(site)] == site for k in range(len(new))), site
    attr, key, patch, _what = Session.NETSYNC_ACTBENCH_OP_CAPS["fallback"]
    assert (attr, key, patch) == ("coop_act_fallback", "netsync.battle.act.guest.fallback", "s136")
    assert Session.NETSYNC_ACTBENCH_FALLBACK_USAGE == {"fallback": BW.FALLBACK_USAGE} and _battle_text(BW.FALLBACK_USAGE)
    fake = FakeGame(game)
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.netsync("selftest", 1)
        n = len(fake.executed)
        for args in (("fallback",), ("fallback", "maybe"), ("fallback", "on", "x")):
            with pytest.raises(HarnessError) as err:
                g.netsync("actbench", *args)
            with pytest.raises(RuntimeError) as agent:
                fake._netsync(["actbench", *args])
            assert str(err.value) == str(agent.value) == BW.FALLBACK_USAGE, (args, str(err.value), str(agent.value))
        assert len(fake.executed) == n
        st = g.act_fallback(False)                                      # a well-made form goes to the engine
        assert st.coop_act_fallback_on is False
        st = g.actbench("FALLBACK", "On")                               # the agent lowercases both; so does the driver
        assert st.coop_act_fallback_on is True and fake.executed[-1] == ["netsync", "actbench", "FALLBACK", "On"]
    fake = FakeGame(game)
    fake.netsync_caps = S135_CAPS
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.netsync("selftest", 1)
        n = len(fake.executed)
        for args in (("fallback", "off"), ("fallback",), ("fallback", "on", "x")):
            with pytest.raises(HarnessError) as err:
                g.netsync("actbench", *args)
            with pytest.raises(RuntimeError) as agent:
                fake._netsync(["actbench", *(str(a) for a in args)])
            assert str(err.value).startswith("netsync actbench fallback: the deployed engine publishes no "
                                             "`netsync.battle.act.guest.fallback`"), str(err.value)
            assert f"(memoria-patch s136); it would answer \"{agent.value}\" only after the step" in str(err.value), \
                (args, str(err.value), str(agent.value))
        assert len(fake.executed) == n and g.state.coop_act_fallback is False and g.state.coop_act_hold is True


def test_the_fallback_log_lines_are_the_engines():
    """Every LOG_FALLBACK_* the stand-in writes and the bench reads is the stack's own words (one C# literal, or a piece
    the engine splices): a reworded engine line turns this red before a bench silently stops matching it."""
    for whole in (BW.LOG_FALLBACK_CLIP_TAIL, BW.LOG_FALLBACK_COLLAPSED, BW.LOG_FALLBACK_FURTHER, BW.LOG_FALLBACK_NONE,
                  BW.LOG_FALLBACK_NONE_TAIL.split(" -- ", 1)[1], BW.LOG_FALLBACK_PARSE,
                  BW.LOG_FALLBACK_PARSE_TAIL.split(" -- ", 1)[1], BW.LOG_FALLBACK_SUMMARY, BW.LOG_FALLBACK_LEVER_BACK, BW.FALLBACK_USAGE, BW.FALLBACK_NONE_DEFEND, BW.FALLBACK_NONE_TRANSFORM,
                  BW.FALLBACK_NONE_IDLE, BW.LOG_FALLBACK_BY_CASTER,
                  # [fix pass] stock-1's refusal reason and cover-2's deferral line (its literal pieces)
                  BW.FALLBACK_NONE_MISSING, BW.LOG_FALLBACK_DEFER, BW.LOG_FALLBACK_DEFER_MID, BW.LOG_FALLBACK_DEFER_TAIL,
                  ") waits for that replay's end, at most ",
                  # [fix pass 2: rcover-2] the record deferral's line (its literal pieces)
                  BW.LOG_FALLBACK_AWAIT_MID, BW.LOG_FALLBACK_AWAIT_WAITS, BW.LOG_FALLBACK_AWAIT_TAIL):
        assert _battle_text(whole), whole
    assert _battle_text('Log.Message("[NetSync] action fallback: wire slot " + a.CasterSlot + "\'s action (cmd " + a.CmdNo + '
                        '" sub " + a.SubNo + ", id "')
    assert _battle_text('+ a.ActId + ") waits for its START\'s decision (" + ActStateName(rec.State)')
    assert _battle_text('+ ") -- a launch covers it, a decline plays its clip; at most " + ActFallbackDeferMaxMs')
    # the spliced lines, pinned as the C# EXPRESSIONS that write them, piece by piece in order
    for quoted in ('Log.Message("[NetSync] action fallback: " + ActFallbackKindName(kind) + " clip " + clip + " on wire slot " '
                   '+ a.CasterSlot + " (cmd "',
                   '+ a.CmdNo + " sub " + a.SubNo + ", " + (byId ? "keyed by id " + a.ActId : "keyed by caster, cmd and sub '
                   'within "',
                   '+ ActFallbackWindowMs + " ms") + ", via " + via + ") at battle ms " + _actNowMs',
                   '(collapsed ? " -- collapsed onto this frame\'s earlier clip on that unit" : " -- one stock clip for an '
                   'action no replay covers")',
                   '(_fbLogged == ActFallbackLogMax ? "; further clips this boot are counted, not logged" : "")',
                   'why = transformed ? "a monster-transformed caster" : "Defend / Change";',
                   'Log.Message("[NetSync] action fallback: no clip for wire slot " + a.CasterSlot + " cmd " + a.CmdNo + " sub " '
                   '+ a.SubNo + " ("'):
        assert _battle_text(quoted), quoted
    for piece in ("[NetSync] action fallback faulted (logged once per boot; the impact's figures and state still applied): ",
                  " could not be parsed ("):
        assert _battle_text(piece), piece
    # the lever's two lines: ONE literal head + the ternary's two arms (s136 splits the OFF arm over two lines)
    head, off1, off2, on = ("[NetSync] harness: action fallback ", "OFF -- CALIBRATION: the pre-s136 guest (an impact no replay ",
                            "covers gets the s110 player-only MP_ATTACK swing; enemies nothing)", "ON")
    assert _battle_text(f'"{head}" + (_benchFallbackOff ? "{off1}"') and _battle_text(f'+ "{off2}" : "{on}"));')
    assert (BW.LOG_FALLBACK_OFF, BW.LOG_FALLBACK_ON) == (head + off1 + off2, head + on)
    # ...and the parser reads the clip line exactly as the engine (and the stand-in's twin) writes it, Memoria's prefix kept
    line = (f"16.10.2026 12:00:00 |M| {BW.LOG_FALLBACK}item clip ANH_MAIN_B0_006_210 on wire slot 2 (cmd 14 sub 236, keyed "
            f"by id 7, via arrival) at battle ms 4410{BW.LOG_FALLBACK_CLIP_TAIL}")
    assert BW.parse_fallback_clip(line) == {"kind": "item", "clip": "ANH_MAIN_B0_006_210", "slot": 2, "cmd": 14, "sub": 236,
                                            "keyed_by": "id", "id": 7, "via": "arrival", "ms": 4410, "collapsed": False}
    old = (f"{BW.LOG_FALLBACK}magic clip X on wire slot 1 (cmd 22 sub 25, {BW.LOG_FALLBACK_BY_CASTER}500 ms, via declined) at "
           f"battle ms 9{BW.LOG_FALLBACK_COLLAPSED}")
    assert BW.parse_fallback_clip(old)["keyed_by"] == "caster" and BW.parse_fallback_clip(old)["collapsed"] is True
    assert BW.parse_fallback_clip(BW.LOG_FALLBACK_NONE + "1 cmd 4 sub 0 (Defend / Change)") is None


#: the s136 hook sites (a file, then the lines in order inside s136's own patch: code lines, comments dropped)
FB_HOOKS = {
    "NetSyncDiorama.cs": [
        ("ApplyActionFrameNow(b, ref a, dT, dC, selfCast, covered, backlog, ActViaArrival, _actNowMs, false, 0, paired);",),
        ("Boolean s110Swing = dC != null && !selfCast && a.CasterIsPlayer && !lethalC && !reviveC && !hiddenC && "
         "CanPlayCosmeticMotion(dC);", "if (s110Swing && covered)", "{", "_actSwingSkipped++;", "}",
         "else if (!ActFallbackOn)", "{", "if (s110Swing)", "{",
         "btl_mot.setMotion(dC, BattlePlayerCharacter.PlayerMotionIndex.MP_ATTACK);"),
        ("if (ActFallbackOn)", "ActFallbackAtImpact(ref a, dC, selfCast, lethalC, reviveC, hiddenC, rec, backlog, via, "
                               "arriveMs);")],
    "NetSyncDiorama.Replay.cs": [
        ("ActRecomputeLive();", "ActFallbackReset(counters);", "if (!counters)", "return;"),
        ("ActLogSummary(why);", "ActFallbackDropDeferred();", "ActFallbackLogSummary(why);"),
        ('ApplyActionFrameNow(b, ref a, dT, dC, selfCast, covered, backlog, "late", _actNowMs, false, 0, paired);',),
        ("if (ActFallbackOn)", "{", "BTL_DATA fC = h.SelfCast ? dT : dC;", "Boolean fLethal = h.SelfCast ? lethalT : lethalC;"),
        ("q.Rec);",),
        ("_benchLifeSkipOff = false;", "if (_benchFallbackOff)")],
    "NetSyncClient.cs": [("Boolean fallbackOk = NetSyncDiorama.ActFallbackSelfTest(out fallbackDetail);",)],
}


def test_the_fallback_hooks_sit_at_the_audits_sites():
    """Each s136 hook at its audited site, read off s136's own patch (code lines, comments dropped, in order): NO stock
    file -- the four files are netsync's and the agent's only; the s110 swing's guard kept whole (swing_skipped exactly as
    before, the swing verbatim under the lever) with fallback A after it; the arrival and the late release pass the record
    (`paired`), a queued frame its own (`q.Rec`), a held release reads the caster's guards at the release AFTER the flinch
    and BEFORE the life lanes; the reset inside ActResetForBoot BEFORE its counters' early return; the summary after s134's;
    the lever in ActBenchRelease; the proof line."""
    s136 = _patch_bytes("s136")
    for file_name, sites in FB_HOOKS.items():
        new = [c for c in (_strip_comment(t) for _h, _k, t in _new_side(file_name, s136)) if c]
        for site in sites:
            at = next((k for k in range(len(new)) if new[k:k + len(site)] == list(site)), None)
            assert at is not None, (file_name, site[0])
    files = {p.replace("\\", "/").rsplit("/", 1)[-1] for p, _sec in msr.sections(s136) if p}
    assert files == {"HarnessAgent.cs", "NetSyncClient.cs", "NetSyncDiorama.Replay.cs", "NetSyncDiorama.cs"}, files
    assert all(any(d.endswith("/" + f) for d in msr.DEFAULT_FILES) for f in files), files   # (no new file to replay)
    # the held release's order: s135's flinch block (its ActHoldErr catch) right before fallback A, THE LIFE LANES after
    rel = [c for c in (_strip_comment(t) for _h, _k, t in _new_side(REPLAY_FILE, s136)) if c]
    # [fix pass: stock-3] fallback A's step in its OWN try (as the figure and flinch steps): a throw never drops the life lanes
    head = ["ActHoldErr(ex);", "}", "try", "{", "if (ActFallbackOn)", "{", "BTL_DATA fC = h.SelfCast ? dT : dC;"]
    tail = ["h.SelfCast ? hiddenT : hiddenC, h.Rec, h.Backlog, via, h.ArriveMs);", "}", "}", "catch (Exception ex)", "{",
            "ActHoldErr(ex);", "}", "Boolean superseded = false;"]
    for site in (head, tail):
        assert any(rel[k:k + len(site)] == site for k in range(len(rel))), site
    s135 = [c for c in (_strip_comment(t) for _h, _k, t in _new_side(REPLAY_FILE, _patch_bytes("s135"))) if c]
    flinch = s135.index("btl_mot.SetDamageMotion(new BattleUnit(dT), null);")
    assert s135[flinch + 1:flinch + 6] == ["}", "catch (Exception ex)", "{", "ActHoldErr(ex);", "}"], s135[flinch:flinch + 8]
    assert s135[flinch + 6] == "Boolean superseded = false;", s135[flinch + 6]          # (where s136's hunk goes in)
    # THE CONTAINMENT LAW at the parse: it borrows the btlseq reader and opcode and puts them back; no text is fetched
    for line in ("seq.sequenceReader = keepReader;", "seq.wSeqCode = keepCode;", "return String.Empty;",
                 "e.Clip = ActFallbackFirstClip(BattleActionThread.LoadFromBtlSeq(b.btl_scene, seq, ActFallbackNoText, sub));"):
        assert _battle_text(line), line


def test_reset_releases_the_fallback_lever(game):
    """HarnessReleaseBench's s136 half (audit 4.5): `fallback off` left set, then `reset`: the 'fallback lever back' line
    once, and re-read WITH a fresh selftest role the lever at rest -- while s134's and s135's levers come back too."""
    fake = _rep_dio(game)
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(FIELD)
        g.netsync("selftest", 1)
        for args in (("fallback", "off"), ("hold", "off"), ("replay", "off")):
            g.actbench(*args)
        st = g.state
        assert (st.coop_act_fallback_on, st.coop_act_hold_on, st.coop_act_guest_why) == (False, False, "lever")
        g.send("reset")
        g.wait_for(lambda s: s.netsync is not None and not s.netsync["forced"], timeout=10.0, what="the release")
        st = g.netsync("selftest", 1)
        assert (st.coop_act_fallback_on, st.coop_act_hold_on, st.coop_act_guest_on) == (True, True, True)
    assert len(_mlog_lines(fake, BW.LOG_FALLBACK_LEVER_BACK)) == 1 and len(_mlog_lines(fake, BW.LOG_HOLD_LEVERS_BACK)) == 1


# ---- [ff9mapkit netsync s136] fallback A's model: the stand-in end to end through the driver, then battlewire's lane on the
# rules no stand-in battle reaches (a lane rig: eight units, the bench feed, the stand-in's tick order)
#: the stand-in diorama's cast for fallback A: Zidane / Vivi / Garnet (wire 0-2) and two enemies (wire 4-5)
FB_UNITS = [
    {"slot": 0, "id": 1, "player": True, "name": "Zidane", "hp": 420, "hp_max": 600, "hp_raw": 420, "hp_max_raw": 600,
     "mp": 30, "mp_max": 40, "atb": 0, "atb_max": 6000, "can_act": True, "alive": True, "targetable": True, "level": 5,
     "status": "0"},
    {"slot": 1, "id": 2, "player": True, "name": "Vivi", "hp": 300, "hp_max": 380, "hp_raw": 300, "hp_max_raw": 380,
     "mp": 12, "mp_max": 20, "atb": 0, "atb_max": 6000, "can_act": True, "alive": True, "targetable": True, "level": 4,
     "status": "0"},
    {"slot": 2, "id": 4, "player": True, "name": "Garnet", "hp": 350, "hp_max": 400, "hp_raw": 350, "hp_max_raw": 400,
     "mp": 40, "mp_max": 50, "atb": 0, "atb_max": 6000, "can_act": True, "alive": True, "targetable": True, "level": 4,
     "status": "0"},
    {"slot": 4, "id": 16, "player": False, "name": "Fang", "hp": 900, "hp_max": 900, "hp_raw": 900, "hp_max_raw": 900,
     "mp": 0, "mp_max": 0, "atb": 0, "atb_max": 6000, "can_act": True, "alive": True, "targetable": True, "level": 3,
     "status": "0"},
    {"slot": 5, "id": 32, "player": False, "name": "Fang", "hp": 900, "hp_max": 900, "hp_raw": 900, "hp_max_raw": 900,
     "mp": 0, "mp_max": 0, "atb": 0, "atb_max": 6000, "can_act": True, "alive": True, "targetable": True, "level": 3,
     "status": "0"}]


def _fb_impact(act_id, *, caster: int, target: int, cmd: int, sub: int, player_caster: bool = True,
               player_target: bool = False, dmg: bool = False, hp: int = 300, cast_hp: int = 300, seq: int = 5,
               nonce: int = 0x77) -> bytes:
    """An impact naming ``act_id`` (None = a 46-byte old-host one) -- no figure; the host's raws (``cast_hp`` 0: lethal)."""
    flags = (1 if dmg else 0) | (32 if player_target else 0) | (64 if player_caster else 0)
    return BW.encode_action_impact(nonce, seq, caster, target, raws=(hp, 0, cast_hp, 0), flags=flags, cmd_no=cmd,
                                   sub_no=sub, act_id=act_id)


def _fb_dio(game, *, caps=None):
    fake = _rep_dio(game, caps=caps)
    fake.dio_units = [dict(u) for u in FB_UNITS]
    return fake


def test_the_stand_in_plays_one_clip_per_uncovered_action(game):
    """6.10 on the stand-in, with `replay off` (every START declines `lever`: every impact UNCOVERED): Garnet's Potion on
    HERSELF (no DmgMot: D-b) and on Vivi -> MP_ITEM1, Vivi's Fire -> MP_MAGIC, Zidane's Attack -> MP_ATTACK -- each the
    caster's `mot`, `last` naming it (keyed by id) --; Fang's sub 0 -> the first non-Idle caster clip of its sequence (its
    `anim`), sub 1 (END only) and Defend -> none; a self-hit (a DmgMot on self) guarded. `fallback off` is the pre-s136
    guest: the Potion on Vivi and the Fire play MP_ATTACK (the s110 swing), the self-Potion and the enemy nothing, and no
    counter moves."""
    for lever in (False, True):
        fake = _fb_dio(game)
        with session(game, fake) as g:
            _dio(g, fake)
            g.actbench("replay", "off")
            if lever:
                g.act_fallback(False)
            ids = iter(range(1, 99))

            def act(caster, target, cmd, sub, *, player_caster=True, player_target=True, dmg=False, settle=True):
                i = next(ids)
                g.act_feed([_rep_start(i, actor=caster, player=player_caster, cmd=cmd, sub=sub, tar=1 << target),
                            _fb_impact(i, caster=caster, target=target, cmd=cmd, sub=sub, player_caster=player_caster,
                                       player_target=player_target, dmg=dmg)])
                st = _rep_until(g, lambda s: s.coop_act_guest_declined >= i, f"START {i} declined")
                g.wait_frames(2)
                return g.state, i

            st, i = act(2, 2, BW.CMD_ITEM_ID, BW.ITEM_POTION_ID)        # Garnet's Potion on herself
            mot_self = st.unit_mot(2)
            g.wait_frames(30)
            st, i2 = act(2, 1, BW.CMD_ITEM_ID, BW.ITEM_POTION_ID)       # ...on Vivi
            mot_ally, last_ally = st.unit_mot(2), st.coop_act_fallback_last
            g.wait_frames(30)
            st, _ = act(1, 4, BW.CMD_BLACK_MAGIC_ID, BW.ABILITY_FIRE_ID, player_target=False)   # Vivi's Fire on Fang
            mot_magic = st.unit_mot(1)
            st, _ = act(0, 4, BW.CMD_ATTACK_ID, BW.ABILITY_ATTACK_ID, player_target=False)     # Zidane's Attack
            mot_attack = st.unit_mot(0)
            st, _ = act(4, 0, BW.CMD_ENEMY_ATK, 0, player_caster=False)                         # Fang sub 0 on Zidane
            enemy_anim, last_enemy = st.unit_anim(4), st.coop_act_fallback_last
            g.wait_frames(30)
            st, _ = act(4, 1, BW.CMD_ENEMY_ATK, 1, player_caster=False)                         # sub 1: END only
            st, _ = act(0, 0, BW.CMD_DEFEND_ID, 177)                                             # Zidane's Defend
            st, _ = act(1, 1, BW.CMD_ATTACK_ID, BW.ABILITY_ATTACK_ID, dmg=True)                  # a self-hit (confused)
            fb = st.coop_act_fallback_block
        if lever:
            assert (mot_self, mot_ally, mot_magic, mot_attack) == (0, BW.MP_ATTACK, BW.MP_ATTACK, BW.MP_ATTACK)
            assert enemy_anim == "IDLE" and fb == dict(BW.ACT_GUEST_FALLBACK_SENTINELS, on=False)
            continue
        assert (mot_self, mot_ally, mot_magic, mot_attack) == (BW.MP_ITEM1, BW.MP_ITEM1, BW.MP_MAGIC, BW.MP_ATTACK)
        assert last_ally == {"actor": 2, "clip": "ANH_FAKE_P2_031", "cmd": BW.CMD_ITEM_ID, "sub": BW.ITEM_POTION_ID,
                             "keyed_by": "id", "kind": "item", "id": i2, "via": "arrival", "ms": last_ally["ms"]}
        first = BW.act_fallback_first_clip(BW.act_seq_threads(BW.ActFallbackLane.FAKE_SCENE_SEQS[0]))
        assert enemy_anim == first == last_enemy["clip"] == "ANH_MON_FAKE_001_010" and last_enemy["kind"] == "enemy"
        assert (fb["clips"], fb["none"], fb["guarded"], fb["covered"], fb["deduped"], fb["collapsed"]) == (5, 2, 1, 0, 0, 0)
        assert _mlog_lines(fake, f"{BW.LOG_FALLBACK_NONE}4 cmd {BW.CMD_ENEMY_ATK} sub 1 (sequence 1{BW.FALLBACK_NONE_IDLE}")
    assert _mlog_lines(fake, BW.LOG_FALLBACK_OFF)


def test_the_stand_in_covers_a_replayed_action_and_plays_a_declined_ones_clip(game):
    """COVERED vs UNCOVERED on the stand-in (replay ON): a START + its impact -- held, released at the replay's hit --
    counts `covered` (no clip; swing_skipped +1); a NOOP START's impact (kind none) covered too; a START, its impact and
    its END in ONE feed -- the impact HELD, then the START declined `stale` -- plays its action's clip at that `declined`
    release (`last.via` "declined"); an impact naming no START (an id nothing registered) plays at arrival."""
    fake = _fb_dio(game)
    with session(game, fake) as g:
        _dio(g, fake)
        g.act_feed([_rep_start(1), _fb_impact(1, caster=0, target=4, cmd=BW.CMD_ATTACK_ID, sub=BW.ABILITY_ATTACK_ID,
                                              player_target=False, dmg=True)])
        st = _rep_until(g, lambda s: s.coop_act_hold_rel_hit == 1, "the hit release")
        assert (st.coop_act_fallback_covered, st.coop_act_fallback_clips, st.coop_act_guest_swing_skipped) == (1, 0, 1)
        _rep_until(g, lambda s: s.coop_act_guest_running == 0, "the replay's end")
        g.act_feed([_rep_start(2, actor=1, kind=BW.VFX_KIND_NONE, num=0, tar=0x02),
                    _fb_impact(2, caster=1, target=1, player_target=True, cmd=BW.CMD_DEFEND_ID, sub=177)])
        st = _rep_until(g, lambda s: s.coop_act_guest_noop == 1 and s.coop_act_hold_held_now == 0, "the noop")
        assert (st.coop_act_fallback_covered, st.coop_act_fallback_none, st.coop_act_fallback_clips) == (2, 0, 0)
        g.act_feed([_rep_start(3, actor=2, cmd=BW.CMD_ITEM_ID, sub=BW.ITEM_POTION_ID, tar=0x04),
                    _fb_impact(3, caster=2, target=2, player_target=True, cmd=BW.CMD_ITEM_ID, sub=BW.ITEM_POTION_ID),
                    BW.encode_action_end(0x77, 9, 3, BW.CMD_ITEM_ID, BW.ITEM_POTION_ID)])
        st = _rep_until(g, lambda s: s.coop_act_fallback_clips == 1, "the declined release's clip")
        assert st.coop_act_guest_declined_why == "stale" and st.coop_act_hold_rel_declined == 2   # (the NOOP's, then this)
        assert st.coop_act_hold_held == 3                               # (each of the three HELD -- never at arrival)
        assert st.coop_act_fallback_last["via"] == "declined" and st.coop_act_fallback_last["kind"] == "item"
        assert st.unit_mot(2) == BW.MP_ITEM1
        g.act_feed(_fb_impact(77, caster=1, target=4, cmd=BW.CMD_BLACK_MAGIC_ID, sub=BW.ABILITY_FIRE_ID,
                              player_target=False))
        st = _rep_until(g, lambda s: s.coop_act_fallback_clips == 2, "the orphan's clip")
        assert st.coop_act_fallback_last["via"] == BW.ACT_VIA_ARRIVAL and st.coop_act_fallback_last["id"] == 77


def test_the_stand_in_at_s135_keeps_the_s110_swing(game):
    """An s135 stand-in (S135_CAPS: no `actfallback` rung) keeps s135's model exactly: an uncovered Potion on an ally swings
    MP_ATTACK, an enemy plays nothing, no `fallback` key, no proof line."""
    fake = _fb_dio(game, caps=S135_CAPS)
    with session(game, fake) as g:
        _dio(g, fake)
        g.act_feed(_fb_impact(5, caster=2, target=1, player_target=True, cmd=BW.CMD_ITEM_ID, sub=BW.ITEM_POTION_ID))
        st = _rep_until(g, lambda s: s.unit_mot(2) == BW.MP_ATTACK, "the s110 swing")
        g.act_feed(_fb_impact(6, caster=4, target=0, cmd=BW.CMD_ENEMY_ATK, sub=0, player_caster=False,
                              player_target=True))
        g.wait_frames(3)
        assert g.state.unit_anim(4) == "IDLE" and st.coop_act_fallback is False
    assert not _mlog_lines(fake, BW.PROOF_FALLBACK)


class _FbRig(_LaneRig):
    """s134's lane rig with the hold AND fallback A on (an s136 lane), the frame counted (the collapse reads it)."""

    def __init__(self, frames: int = 10 ** 6):
        super().__init__(None, frames)
        self.lane.with_hold_fn = True
        self.lane.with_fallback_fn = True
        self.frame = 0

    def ctx(self, **kw) -> dict:
        c = super().ctx(**kw)
        c.setdefault("frame", self.frame)
        return c

    def step(self, n: int = 1, **kw) -> None:
        for _ in range(n):
            self.frame += 1
            super().step(1, **kw)

    def at(self, ms: int) -> None:
        """Step until the battle clock reads at least ``ms``."""
        while self.lane.now_ms < ms:
            self.step()

    @property
    def fb(self) -> dict:
        return self.lane.doc(role=True, booted=True)["fallback"]


def _fb_old(caster: int = 0, *, cmd: int = BW.CMD_ATTACK_ID, sub: int = BW.ABILITY_ATTACK_ID, target: int = 4,
            player: bool = True) -> bytes:
    return _fb_impact(None, caster=caster, target=target, cmd=cmd, sub=sub, player_caster=player)

def test_the_fallback_lane_keys_once_per_action_and_collapses_per_frame():
    """ONCE PER ACTION on battlewire's lane: three impacts naming ONE id play one clip (deduped +2); three distinct ids on
    one actor over three frames play three; three distinct ids on one actor in ONE drain play one (collapsed +2: counted
    when written); the clip lines stop at ActFallbackLogMax with the 'further clips' tail. An old host's (caster, cmd, sub)
    plays once within 500 ms of battle time between ARRIVALS -- an arrival < 500 ms after the spent one is deduped and
    [fix pass: cover-5, timing-5] SLIDES the window to its own arrival (an id-less multi-hit action whose hits span 500 ms
    or more stays one clip), one 500 ms or more after the action's LAST hit is a new decision that RE-SPENDS the key from
    its own arrival; another caster, command or sub is another action. (A drain's arrival is the battle clock the previous
    tick set: read before the step.)"""
    rig = _FbRig()
    rig.step()
    att = dict(caster=0, target=4, cmd=BW.CMD_ATTACK_ID, sub=BW.ABILITY_ATTACK_ID)
    rig.feed(*[_fb_impact(7, **att)] * 3)
    rig.step()
    assert (rig.fb["clips"], rig.fb["deduped"], rig.fb["last"]["keyed_by"], rig.fb["last"]["id"]) == (1, 2, "id", 7)
    for i in (8, 9, 10):
        rig.feed(_fb_impact(i, **att))
        rig.step()
    assert (rig.fb["clips"], rig.fb["collapsed"]) == (4, 0)
    rig.feed(*[_fb_impact(i, **att) for i in (11, 12, 13)])
    rig.step()
    assert (rig.fb["clips"], rig.fb["collapsed"], rig.fb["last"]["id"]) == (5, 2, 13)
    for i in (14, 15, 16):                                              # writes 8-10: the log's cap
        rig.feed(_fb_impact(i, **att))
        rig.step()
    lines = [ln for ln in rig.lane.lines if ln.startswith(BW.LOG_FALLBACK) and " clip " in ln]
    assert len(lines) == BW.ACT_FALLBACK_LOG_MAX and lines[-1].endswith(BW.LOG_FALLBACK_FURTHER), lines[-1]
    assert sum(BW.LOG_FALLBACK_COLLAPSED in ln for ln in lines) == 2 and rig.fb["clips"] == 8

    rig = _FbRig()
    rig.step()

    def old_at(ms: int, *frames) -> int:
        """Feed ``frames`` so they drain at the first arrival >= ``ms``; that arrival."""
        while rig.lane.now_ms < ms:
            rig.step()
        rig.feed(*frames)
        arrival = rig.lane.now_ms
        rig.step()
        return arrival
    spent = old_at(0, _fb_old())
    assert (rig.fb["clips"], rig.fb["last"]["keyed_by"], rig.fb["last"]["id"]) == (1, "caster", 0)
    a1 = old_at(spent + BW.ACT_FALLBACK_WINDOW_MS - 40, _fb_old())     # the first arrival in [460, 499]
    assert a1 - spent < BW.ACT_FALLBACK_WINDOW_MS and (rig.fb["clips"], rig.fb["deduped"]) == (1, 1), a1 - spent
    old_at(0, _fb_old(1), _fb_old(cmd=BW.CMD_BLACK_MAGIC_ID, sub=BW.ABILITY_FIRE_ID), _fb_old(sub=177))
    assert (rig.fb["clips"], rig.fb["collapsed"]) == (3, 1)             # (two on Zidane in one frame: one collapses)
    a2 = old_at(spent + BW.ACT_FALLBACK_WINDOW_MS, _fb_old())           # 500+ ms after the SPENT arrival, < 500 after a1
    assert a2 - spent >= BW.ACT_FALLBACK_WINDOW_MS and a2 - a1 < BW.ACT_FALLBACK_WINDOW_MS, (a2 - spent, a2 - a1)
    assert (rig.fb["clips"], rig.fb["deduped"]) == (3, 2), rig.fb      # the window SLID to a1: still one action
    a3 = old_at(a2 + BW.ACT_FALLBACK_WINDOW_MS, _fb_old())              # 500 ms after the action's LAST hit (or more)
    assert a3 - a2 >= BW.ACT_FALLBACK_WINDOW_MS and rig.fb["clips"] == 4, a3 - a2
    a4 = old_at(a3 + 200, _fb_old())                                    # re-spent at a3: 200+ ms later is deduped
    assert a4 - a3 < BW.ACT_FALLBACK_WINDOW_MS and (rig.fb["clips"], rig.fb["deduped"]) == (4, 3)


def test_the_fallback_lane_guards_spend_nothing_and_a_backlog_spends_the_key():
    """A guard refusal spends NO key -- a self-hit (a DmgMot on self) is guarded, its sibling (the same id on an enemy)
    still plays; a lethal caster is guarded; a BACKLOG drain spends the key -- a backlog impact plays nothing (D-c) and its
    live sibling is deduped, never a late clip; the end (presented or injected) / a Leave / the end-inject flush / [fix
    pass: timing-1] the run-away hold block every clip; a caster acting in a running replay is -- [fix pass: cover-2] for an
    id-keyed impact refused for nothing else -- DEFERRED (counted when it decides or drops: the teardown drops it
    `guarded`), and for an id-0 one guarded at once; [fix pass: stock-2] a unit hidden by bi.disappear is guarded."""
    rig = _FbRig()
    rig.step()
    att = dict(cmd=BW.CMD_ATTACK_ID, sub=BW.ABILITY_ATTACK_ID)
    rig.feed(_fb_impact(7, caster=1, target=1, player_target=True, dmg=True, **att))
    rig.step()
    assert (rig.fb["guarded"], rig.fb["clips"]) == (1, 0)
    rig.feed(_fb_impact(7, caster=1, target=4, **att))
    rig.step()
    assert (rig.fb["guarded"], rig.fb["clips"], rig.fb["deduped"]) == (1, 1, 0)
    rig.feed(_fb_impact(8, caster=2, target=4, cast_hp=0, **att))     # Garnet's own blow kills her: lethal
    rig.step()
    assert (rig.fb["guarded"], rig.fb["clips"]) == (2, 1)
    lane = rig.lane
    unit = {u["slot"]: u for u in rig.units}
    a = BW.decode_action(_fb_impact(9, caster=0, target=4, **att))
    lane.fallback.at_impact(a, unit[0], False, False, False, False, None, True, BW.ACT_VIA_ARRIVAL, lane.now_ms, rig.ctx())
    lane.fallback.at_impact(a, unit[0], False, False, False, False, None, False, BW.ACT_VIA_ARRIVAL, lane.now_ms, rig.ctx())
    assert (rig.fb["backlog"], rig.fb["deduped"], rig.fb["clips"]) == (1, 1, 1)
    b = BW.decode_action(_fb_impact(10, caster=3, target=4, **att))
    for via, kw in (("end-inject", {}), (BW.ACT_VIA_ARRIVAL, {"end_presented": True}),
                    (BW.ACT_VIA_ARRIVAL, {"end_injected": True}), ("queued", {"leaving": True}),
                    (BW.ACT_VIA_ARRIVAL, {"end_held": True}),
                    (BW.ACT_VIA_ARRIVAL, {"disappeared": lambda u: u is unit[3]})):
        lane.fallback.at_impact(b, unit[3], False, False, False, False, None, False, via, lane.now_ms, rig.ctx(**kw))
    assert (rig.fb["guarded"], rig.fb["clips"]) == (8, 1)
    rig.feed(_rep_start(20, actor=3, tar=0x10))                         # the caster acts: its own replay runs
    rig.step()
    assert lane.acting_record(unit[3]) is not None
    lane.fallback.at_impact(b, unit[3], False, False, False, False, None, False, BW.ACT_VIA_ARRIVAL, lane.now_ms, rig.ctx())
    # [fix pass: cover-2] refused ONLY for its caster's running replay: deferred (no counter yet), its key unspent
    assert (rig.fb["guarded"], rig.fb["clips"], len(lane.fallback.deferred)) == (8, 1, 1)
    z = BW.decode_action(_fb_impact(0, caster=3, target=4, **att))      # an id-0 impact: never deferred
    lane.fallback.at_impact(z, unit[3], False, False, False, False, None, False, BW.ACT_VIA_ARRIVAL, lane.now_ms, rig.ctx())
    assert (rig.fb["guarded"], len(lane.fallback.deferred)) == (9, 1)
    lane.fallback.at_impact(b, None, False, False, False, False, None, False, BW.ACT_VIA_ARRIVAL, lane.now_ms, rig.ctx())
    # every impact with a resolved caster in exactly one bucket: 1 clip + 9 guarded + 1 backlog + 1 deduped (no caster:
    # none) -- the deferred one once it decides or drops: the teardown drops it `guarded`
    assert BW.act_fallback_decided(rig.fb) == 12
    lane.discard_all("teardown (bench)")
    assert BW.act_fallback_decided(rig.fb) == 13 and rig.fb["guarded"] == 10 and lane.fallback.deferred == []


def _fb_lag(*, frames: int = 60, defer: bool = True, newer: bool = False) -> "_FbRig":
    """[fix pass: cover-2] THE GUEST-LAG CASE on the lane: Zidane's replay 1 runs; his START 2 + its impact + its END land
    in ONE drain -- the impact HELD (paired, Registered), START 2 declined `stale` before the holder check, its held
    impact released `declined` while replay 1 still runs (its caster ACTS). ``defer`` False = THE MUTANT (no deferral:
    refused at once); ``newer`` = Zidane's START 3 fed right after (it parks behind replay 1, then owns his turn)."""
    rig = _FbRig(frames=frames)
    if not defer:
        rig.lane.fallback.defer = lambda *args: False
    rig.step()
    rig.feed(_rep_start(1))
    rig.step()
    assert [r.id for r in rig.lane.running] == [1]
    rig.feed(_rep_start(2), _fb_impact(2, caster=0, target=4, cmd=BW.CMD_ATTACK_ID, sub=BW.ABILITY_ATTACK_ID),
             BW.encode_action_end(0x77, 9, 2, BW.CMD_ATTACK_ID, BW.ABILITY_ATTACK_ID))
    rig.step()
    hold = rig.lane.hold.doc(role=True)
    assert (hold["held"], hold["rel_declined"], rig.lane.stale) == (1, 1, 1), hold
    if newer:
        rig.feed(_rep_start(3))
        rig.step()
    return rig


def test_the_fallback_lane_defers_an_action_refused_only_for_its_casters_replay():
    """[fix pass: cover-2] An uncovered id-keyed action whose ONLY failing guard is "acting" WAITS for its caster's replay
    -- its key unspent, no counter -- and plays its one clip via "deferred" once that replay ends (THE MUTANT, refused at
    once, shows nothing: the stand-in can fail the ordering it claims). A NEWER replay of the actor owning the turn (one
    launched meanwhile) drops it `guarded`; so does ActFallbackDeferMaxMs of battle time; so does the teardown."""
    rig = _fb_lag()
    assert (rig.fb["clips"], rig.fb["guarded"], len(rig.lane.fallback.deferred)) == (0, 0, 1), rig.fb
    assert sum(ln.startswith(BW.LOG_FALLBACK_DEFER) for ln in rig.lane.lines) == 1
    while rig.lane.running:
        rig.step()
    assert (rig.fb["clips"], rig.fb["guarded"], rig.lane.fallback.deferred) == (1, 0, []), rig.fb
    assert {k: rig.fb["last"][k] for k in ("id", "via", "kind", "keyed_by")} == {
        "id": 2, "via": BW.ACT_VIA_DEFERRED, "kind": "attack", "keyed_by": "id"}, rig.fb["last"]
    rig = _fb_lag(defer=False)                                          # THE MUTANT: refused, never decided again
    while rig.lane.running:
        rig.step()
    assert (rig.fb["clips"], rig.fb["guarded"]) == (0, 1), ("the no-deferral red never came", rig.fb)
    rig = _fb_lag(newer=True)                                           # START 3 owns Zidane's next turn
    while 3 not in [r.id for r in rig.lane.running]:
        rig.step()
    assert (rig.fb["clips"], rig.fb["guarded"], rig.lane.fallback.deferred) == (0, 1, []), rig.fb
    rig = _fb_lag(frames=10 ** 6)                                       # replay 1 runs on: the deferral goes stale
    rig.step(BW.ACT_FALLBACK_DEFER_MAX_MS // 33 - 5)
    assert len(rig.lane.fallback.deferred) == 1 and rig.fb["guarded"] == 0
    rig.step(10)
    assert (rig.fb["clips"], rig.fb["guarded"], rig.lane.fallback.deferred) == (0, 1, []), rig.fb
    rig = _fb_lag(frames=10 ** 6)                                       # ...or the teardown takes it
    rig.lane.discard_all("teardown (bench)")
    assert (rig.fb["guarded"], rig.lane.fallback.deferred) == (1, [])
    assert [ln for ln in rig.lane.lines if ln.startswith(BW.LOG_FALLBACK_SUMMARY)][-1].endswith(
        "0 clip(s), 0 collapsed, 0 deduped, 0 covered, 0 none, 1 guarded, 0 backlog, 0 parse failure(s)")


def _fb_pending(start_tar: int, *, wait: bool = False) -> "_FbRig":
    """[fix pass 2: rcover-2] Zidane's START 2 (its TarId ``start_tar``) and an impact naming it whose OWN target (wire 6: no
    unit here) is unresolved -- so never HELD (the hold pairs only a resolved target): it applies at arrival, in the START's
    own drain, against the still-REGISTERED record. ``wait``: Zidane's replay 1 runs first, so START 2 parks Waiting behind
    it (the caller then steps with no steady frame: no launch, no pending abort)."""
    rig = _FbRig()
    rig.units[:] = [u for u in rig.units if u["slot"] != 6]
    rig.step()
    if wait:
        rig.feed(_rep_start(1))
        rig.step()
        assert [r.id for r in rig.lane.running] == [1]
    rig.feed(_rep_start(2, tar=start_tar), _fb_impact(2, caster=0, target=6, cmd=BW.CMD_ATTACK_ID, sub=BW.ABILITY_ATTACK_ID))
    rig.step()
    return rig


def test_the_fallback_lane_waits_for_a_pending_records_decision(monkeypatch):
    """[fix pass 2: rcover-2] An impact covered ONLY by a still-PENDING record has no verdict yet. A START whose TarId maps
    to no unit declines `target` -- and every impact of it has no resolved target, so none is ever held: the one drained
    with the START waits for the decision and, the START declined, plays its action's clip via "declined" (no counter
    before; the line once). A START that LAUNCHES covers it (`covered`). THE MUTANT (covered at arrival, never looked at
    again -- the pre-fix rule) leaves the declined action with NO clip: the stand-in can fail the ordering it claims. A
    record still pending past ActFallbackDeferMaxMs keeps its arrival verdict (`covered`; its START then declines `timeout`:
    nothing more); so does the teardown's drop."""
    rig = _fb_pending(0x40)                                             # its TarId names wire 6 too: declined `target`
    hold = rig.lane.hold.doc(role=True)
    assert (rig.lane.declined_why, hold["held"]) == ("target", 0), (rig.lane.declined_why, hold)
    assert (rig.fb["clips"], rig.fb["covered"], rig.lane.fallback.deferred) == (1, 0, []), rig.fb
    assert {k: rig.fb["last"][k] for k in ("id", "via", "kind", "keyed_by")} == {
        "id": 2, "via": "declined", "kind": "attack", "keyed_by": "id"}, rig.fb["last"]
    awaits = [ln for ln in rig.lane.lines if BW.LOG_FALLBACK_AWAIT_WAITS in ln]
    assert awaits == [f"{BW.LOG_FALLBACK_DEFER}0{BW.LOG_FALLBACK_AWAIT_MID}{BW.CMD_ATTACK_ID} sub {BW.ABILITY_ATTACK_ID}, id "
                      f"2{BW.LOG_FALLBACK_AWAIT_WAITS}queued{BW.LOG_FALLBACK_AWAIT_TAIL}{BW.ACT_FALLBACK_DEFER_MAX_MS}"
                      f"{BW.LOG_FALLBACK_DEFER_TAIL}"], awaits
    rig = _fb_pending(0x10)                                             # a TarId that maps: it LAUNCHES -- covered
    assert (rig.lane.started, rig.fb["clips"], rig.fb["covered"], rig.lane.fallback.deferred) == (1, 0, 1, []), rig.fb
    with monkeypatch.context() as m:                                    # THE MUTANT: covered at arrival, never again
        m.setattr(BW, "act_fallback_awaits_record", lambda covered, pending: False)
        rig = _fb_pending(0x40)
        assert rig.lane.declined_why == "target"
        assert (rig.fb["clips"], rig.fb["covered"]) == (0, 1), ("the pending-covered red never came", rig.fb)
    rig = _fb_pending(0x10, wait=True)                                  # parked Waiting behind replay 1, no steady frame
    assert (rig.lane.book.queue[0].state, rig.fb["covered"], len(rig.lane.fallback.deferred)) == (BW.ACT_ST_WAITING, 0, 1)
    rig.step(BW.ACT_FALLBACK_DEFER_MAX_MS // 33 - 5, steady=False)
    assert (rig.fb["covered"], len(rig.lane.fallback.deferred)) == (0, 1), rig.fb
    rig.step(10, steady=False)                                          # still pending past the bound: its arrival verdict
    assert (rig.fb["covered"], rig.fb["clips"], rig.lane.fallback.deferred) == (1, 0, []), rig.fb
    rig.step((BW.ACT_WAIT_MAX_MS - BW.ACT_FALLBACK_DEFER_MAX_MS) // 33 + 5, steady=False)
    assert rig.lane.declined_why == "timeout" and (rig.fb["covered"], rig.fb["clips"]) == (1, 0), rig.fb
    rig = _fb_pending(0x10, wait=True)                                  # ...and the teardown's drop: `covered`
    rig.lane.discard_all("teardown (bench)")
    assert (rig.fb["covered"], rig.fb["guarded"], rig.lane.fallback.deferred) == (1, 0, []), rig.fb


def test_the_fallback_lane_keeps_a_clip_written_after_its_units_abort(monkeypatch):
    """[fix pass 2: rtiming-1] THE ORDER, which the stand-in can fail: Zidane's replay 1 (on Fang 1) and Vivi's replay 2 (on
    Fang 2) run; Fang 1 plays an uncovered move (its clip written BEFORE replay 1 aborts); replay 1 aborts while replay 2
    keeps the busy window open; Zidane -- free now -- plays an uncovered Attack (written AFTER his replay's abort); replay 2
    ends and the window's FULL restore runs: Zidane's clip plays on, Fang 1's -- an aborted replay's unit, written before
    -- is cut to idle. THE MUTANT (ActFallbackKeepsPose blind to the order: the pre-fix rule) cuts Zidane's too; a LATER
    abort touching Zidane takes his kept clip back."""
    def run(later_abort: bool = False):
        rig = _FbRig(frames=20)
        rig.step()
        rig.feed(_rep_start(1, tar=0x10), _rep_start(2, actor=1, tar=0x20))
        rig.step()
        r1, r2 = rig.lane.running
        assert (r1.id, r2.id, rig.lane.window_open) == (1, 2, True)
        rig.feed(_fb_impact(40, caster=4, target=0, cmd=BW.CMD_ENEMY_ATK, sub=0, player_caster=False, player_target=True))
        rig.step()
        assert 4 in rig.lane.fallback.clip_on, rig.fb
        rig.lane._abort(r1, "fault", rig.ctx())
        rig.lane._window_check(rig.ctx())
        assert rig.lane.window_open and rig.lane.window_abort_mask == 0x11  # Zidane (1) and Fang 1 (16)
        rig.feed(_fb_impact(41, caster=0, target=5, cmd=BW.CMD_ATTACK_ID, sub=BW.ABILITY_ATTACK_ID))
        rig.step()
        assert 0 in rig.lane.fallback.clip_on and rig.lane.fallback.post_abort_mask == 0x01, rig.fb
        if later_abort:                                                 # replay 2 aborts WITH Zidane among its units
            r2.targets.append(next(u for u in rig.units if u["slot"] == 0))
            rig.lane._abort(r2, "fault", rig.ctx())
            assert rig.lane.fallback.post_abort_mask == 0
        while rig.lane.running:
            rig.step()
        rig.lane._window_check(rig.ctx())
        assert (rig.lane.restores, rig.lane.window_open) == (1, False)
        return rig
    rig = run()
    assert 0 in rig.lane.fallback.clip_on and 4 not in rig.lane.fallback.clip_on, rig.lane.fallback.clip_on
    rig = run(later_abort=True)
    assert 0 not in rig.lane.fallback.clip_on and 4 not in rig.lane.fallback.clip_on, rig.lane.fallback.clip_on
    monkeypatch.setattr(BW, "act_fallback_keeps_pose", lambda aborted, after, shows: not aborted and bool(shows))
    rig = run()
    assert 0 not in rig.lane.fallback.clip_on, ("the order-blind red never came", rig.lane.fallback.clip_on)


def test_the_fallback_lane_reads_loop_moves_and_scripted_sequences_as_scene_sequences(monkeypatch):
    """[fix pass 2: rstock-1] An enemy's Loop move (ScriptCounter1-3: sub_no the attack number, as EnemyAtk's) and a battle
    script's scripted sequence (cmd None: sub_no its pSeqNo) play their sequence's first non-Idle caster clip; MagicCounter
    still names none. THE MUTANT (btlseq's four only -- the pre-fix rule) plays nothing for them."""
    def run():
        rig = _FbRig()
        rig.step()
        for i, (cmd, sub, slot) in enumerate(((BW.CMD_SCRIPT_COUNTER1, 0, 4), (BW.CMD_SCRIPT_COUNTER3, 3, 5),
                                              (BW.CMD_NONE_ID, 2, 4), (BW.CMD_MAGIC_COUNTER, 0, 5)), start=1):
            rig.feed(_fb_impact(i, caster=slot, target=0, cmd=cmd, sub=sub, player_caster=False, player_target=True))
            rig.step()
        return rig
    rig = run()
    assert (rig.fb["clips"], rig.fb["none"], rig.fb["collapsed"]) == (3, 1, 0), rig.fb
    first = BW.act_fallback_first_clip(BW.act_seq_threads(BW.ActFallbackLane.FAKE_SCENE_SEQS[2]))
    assert {k: rig.fb["last"][k] for k in ("cmd", "sub", "kind", "clip")} == {
        "cmd": BW.CMD_NONE_ID, "sub": 2, "kind": "enemy", "clip": first}, rig.fb["last"]
    assert rig.lane.fallback.clip_on[5]["clip"] == BW.act_fallback_first_clip(
        BW.act_seq_threads(BW.ActFallbackLane.FAKE_SCENE_SEQS[3]))
    monkeypatch.setattr(BW, "act_fallback_enemy_seq_cmd", lambda c: c in (BW.CMD_ENEMY_ATK, BW.CMD_ENEMY_COUNTER,
                                                                           BW.CMD_ENEMY_DYING, BW.CMD_ENEMY_REACTION))
    rig = run()
    assert (rig.fb["clips"], rig.fb["none"]) == (0, 4), ("the btlseq-four red never came", rig.fb)


def test_the_fallback_lane_plays_no_clip_inside_an_abort_all(monkeypatch):
    """[fix pass: timing-1] A Leave's abort-all runs BEFORE the Leave is stamped: the frames its releases unblock -- here
    Vivi's old-host Attack QUEUED behind a held kill, released `queued` when the abort releases the kill -- play NO clip
    (`guarded`: ActFallbackEndBlocks' abortingAll). THE MUTANT (the abort-all input dropped) plays it."""
    def run():
        rig = _FbRig()
        rig.step()
        rig.feed(_rep_start(1, tar=0x20), _hold_impact(1, hp=0))       # Zidane on Fang 2 + a held KILL on Fang 1
        rig.step()
        assert rig.lane.hold.doc(role=True)["life_mask"] == 0x10
        rig.feed(_fb_old(1, target=4))                                  # Vivi's old-host Attack on Fang 1: QUEUED
        rig.step()
        assert rig.lane.hold.doc(role=True)["queued_now"] == 1 and rig.fb["clips"] == 0
        rig.lane.abort_all("leave", ctx=rig.ctx())
        hold = rig.lane.hold.doc(role=True)
        assert (hold["rel_abort"], hold["rel_queued"], rig.lane.aborting_all) == (1, 1, False), hold
        return rig
    rig = run()
    assert (rig.fb["guarded"], rig.fb["clips"]) == (1, 0), rig.fb
    orig = BW.act_fallback_end_blocks
    monkeypatch.setattr(BW, "act_fallback_end_blocks", lambda e, h, ab, lv, via: orig(e, h, False, lv, via))
    rig = run()
    assert (rig.fb["guarded"], rig.fb["clips"]) == (0, 1), ("the abort-all red never came", rig.fb)


def test_the_fallback_lane_reads_a_given_motion_table_as_the_engine():
    """[fix pass: harness-06] A unit's given motion table is the engine's d.mot: too short for the action's motion, or an
    empty name there, plays NOTHING (`none`, the engine's own reason naming the motion's enum name); a full one plays its
    name -- never the stand-in's synthetic ``ANH_FAKE_P<slot>_<index>``."""
    rig = _FbRig()
    units = {u["slot"]: u for u in rig.units}
    units[1]["mot_names"] = [f"ANH_VIVI_{i:03d}" for i in range(BW.MP_MAGIC)]          # no MP_MAGIC
    units[2]["mot_names"] = [f"ANH_GARNET_{i:03d}" for i in range(40)]
    units[2]["mot_names"][BW.MP_ATTACK] = ""                                            # an empty MP_ATTACK
    units[0]["mot_names"] = [f"ANH_ZIDANE_{i:03d}" for i in range(40)]
    rig.step()
    for i, (caster, cmd, sub) in enumerate(((1, BW.CMD_BLACK_MAGIC_ID, BW.ABILITY_FIRE_ID),
                                            (2, BW.CMD_ATTACK_ID, BW.ABILITY_ATTACK_ID),
                                            (0, BW.CMD_ATTACK_ID, BW.ABILITY_ATTACK_ID)), start=1):
        rig.feed(_fb_impact(i, caster=caster, target=4, cmd=cmd, sub=sub))
        rig.step()
    assert (rig.fb["none"], rig.fb["clips"]) == (2, 1), rig.fb
    assert rig.fb["last"]["clip"] == f"ANH_ZIDANE_{BW.MP_ATTACK:03d}"
    none = [ln for ln in rig.lane.lines if ln.startswith(BW.LOG_FALLBACK_NONE)]
    assert none == [f"{BW.LOG_FALLBACK_NONE}1 cmd {BW.CMD_BLACK_MAGIC_ID} sub {BW.ABILITY_FIRE_ID} (the unit's motion table "
                    f"has no MP_MAGIC{BW.LOG_FALLBACK_NONE_TAIL}"], none
    assert _battle_text('why = "the unit\'s motion table has no " + ActFallbackMotion(kind);')


def test_the_fallback_lane_judges_covered_at_the_motion_step_and_windows_on_arrivals():
    """THE ORDERINGS the stand-in claims -- each one it can FAIL: (1) COVERED is read at the impact's motion step, on the
    record's state THEN: a held impact whose START later declines `stale` plays its clip at the `declined` release (a model
    that decided `covered` at ARRIVAL -- Registered then -- shows none: [fix pass 2: rcover-2] it reads the frozen state as
    PENDING, so it never decides at all -- still waiting, or `covered` once the bound passes); (2) the window compares
    ARRIVALS: an old host's
    impact queued behind a held kill and released by its 2.5 s timeout is one action with its sibling that arrived beside
    it (a model that compared the RELEASE time plays a second clip); (3) a held release reads the caster's guards BEFORE
    the life lanes: a held REVIVE of a dead caster whose START then declines stays guarded (a model that ran fallback A
    after the life lanes sees her standing and plays)."""
    def held_then_stale(lane_patch=None):
        rig = _FbRig()
        if lane_patch is not None:
            lane_patch(rig.lane)
        rig.step()
        rig.feed(_rep_start(1, actor=2, cmd=BW.CMD_ITEM_ID, sub=BW.ITEM_POTION_ID, tar=0x04),
                 _fb_impact(1, caster=2, target=2, player_target=True, cmd=BW.CMD_ITEM_ID, sub=BW.ITEM_POTION_ID),
                 BW.encode_action_end(0x77, 9, 1, BW.CMD_ITEM_ID, BW.ITEM_POTION_ID))
        rig.step(3)
        return rig
    rig = held_then_stale()
    hold = rig.lane.hold.doc(role=True)
    assert (hold["held"], hold["rel_declined"], rig.lane.stale) == (1, 1, 1)
    assert rig.fb["clips"] == 1 and (rig.fb["last"]["via"], rig.fb["last"]["kind"]) == ("declined", "item")

    def at_arrival(lane):                                               # THE MUTANT: covered frozen at the arrival
        frozen = {}
        orig_intake = lane.hold.intake

        def intake(a, dt, dc, self_cast, rec, backlog, covered, ctx):
            if rec is not None:
                frozen[id(a)] = rec.state
            return orig_intake(a, dt, dc, self_cast, rec, backlog, covered, ctx)
        lane.hold.intake = intake
        orig = lane.fallback.at_impact

        def at_impact(a, caster, self_cast, lethal, revive, hidden, rec, backlog, via, arrive_ms, ctx):
            if rec is None or id(a) not in frozen:
                return orig(a, caster, self_cast, lethal, revive, hidden, rec, backlog, via, arrive_ms, ctx)
            state, rec.state = rec.state, frozen[id(a)]
            try:
                return orig(a, caster, self_cast, lethal, revive, hidden, rec, backlog, via, arrive_ms, ctx)
            finally:
                rec.state = state
        lane.fallback.at_impact = at_impact
    rig = held_then_stale(at_arrival)
    assert (rig.fb["clips"], rig.fb["covered"] + len(rig.lane.fallback.deferred)) == (0, 1), (
        "the arrival-frozen red never came", rig.fb)

    def queued_sibling(release_time: bool):
        rig = _FbRig()
        rig.step()
        # Zidane's replay on Fang 2 (wire 5) + a held KILL on Fang 1 (wire 4) it never hits: Fang 1's slot is busy until the
        # kill's 2.5 s timeout
        rig.feed(_rep_start(1, tar=0x20), _hold_impact(1, hp=0))
        rig.step()
        assert rig.lane.hold.doc(role=True)["life_mask"] == 0x10, rig.lane.hold.doc(role=True)
        if release_time:                                                # THE MUTANT: the window keyed on the RELEASE
            orig = rig.lane.fallback.at_impact
            rig.lane.fallback.at_impact = lambda a, c, sc, le, rv, hd, rec, bl, via, ms, ctx: orig(
                a, c, sc, le, rv, hd, rec, bl, via, rig.lane.now_ms, ctx)
        # Vivi's old-host Attack twice in ONE drain: on Fang 2 first (applied at arrival: the window key spent), then on
        # Fang 1 (its slot busy: QUEUED -- and Vivi's slot with it, so the FIRST frame must be the free one)
        rig.feed(_fb_old(1, target=5), _fb_old(1, target=4))
        rig.step()
        assert (rig.lane.hold.doc(role=True)["queued_now"], rig.fb["clips"]) == (1, 1), rig.lane.hold.doc(role=True)
        rig.step(BW.ACT_HOLD_TIMEOUT_MS // 33 + 3)
        assert rig.lane.hold.doc(role=True)["rel_queued"] == 1 and rig.lane.hold.doc(role=True)["rel_timeout"] == 1
        return rig
    rig = queued_sibling(False)
    assert (rig.fb["clips"], rig.fb["deduped"]) == (1, 1), rig.fb
    rig = queued_sibling(True)
    assert rig.fb["clips"] == 2, ("the release-time window red never came", rig.fb)

    def held_revive(after_lanes: bool):
        rig = _FbRig()
        next(u for u in rig.units if u["slot"] == 1)["alive"] = False   # Vivi dead
        rig.step()
        if after_lanes:                                                 # THE MUTANT: fallback A after the life lanes
            hold, pending = rig.lane.hold, []
            orig_release, orig_at = hold.release_held, rig.lane.fallback.at_impact
            rig.lane.fallback.at_impact = lambda *args: pending.append(args)

            def release_held(h, via, bracket, hit, ctx=None):
                orig_release(h, via, bracket, hit, ctx)
                for a, c, sc, le, _rv, *rest in pending:
                    orig_at(a, c, sc, le, bool(c is not None and not c.get("alive", True)), *rest)
                pending.clear()
            hold.release_held = release_held
        # Fang's START, Vivi's impact naming it -- her caster lane REVIVES her (dead here, raw HP 120: a held life lane) --
        # and its END in ONE drain: held, then the START declined `stale`, released `declined`
        rig.feed(_rep_start(1, actor=4, player=False, cmd=BW.CMD_ENEMY_ATK, sub=0, tar=0x02),
                 _fb_impact(1, caster=1, target=4, cmd=BW.CMD_ATTACK_ID, sub=BW.ABILITY_ATTACK_ID, cast_hp=120),
                 BW.encode_action_end(0x77, 9, 1, BW.CMD_ENEMY_ATK, 0))
        rig.step(3)
        assert rig.lane.hold.doc(role=True)["rel_declined"] == 1
        assert next(u for u in rig.units if u["slot"] == 1)["alive"] is True        # the life lane revived her
        return rig
    rig = held_revive(False)
    assert (rig.fb["guarded"], rig.fb["clips"]) == (1, 0), rig.fb
    rig = held_revive(True)
    assert rig.fb["clips"] == 1, ("the after-the-lanes red never came", rig.fb)


def test_the_fallback_lane_parses_each_scene_sequence_once_and_names_what_it_cannot():
    """The enemy clip: parsed once per (scene, sub) a boot -- a second impact of sub 0 reads the cache --; a sequence the
    scene lacks is a parse failure (parse_failed +1, the line once, played as nothing: none +1); a non-sequence enemy
    command names no sequence; a monster-transformed player plays nothing; the boot summary names every bucket, and a boot
    where only `covered` moved logs none."""
    rig = _FbRig()
    rig.step()
    for i, (sub, slot) in enumerate(((0, 4), (0, 5), (9, 4), (9, 5)), start=1):
        rig.feed(_fb_impact(i, caster=slot, target=0, cmd=BW.CMD_ENEMY_ATK, sub=sub, player_caster=False,
                            player_target=True))
        rig.step()
    assert (rig.fb["clips"], rig.fb["none"], rig.fb["parse_failed"]) == (2, 2, 1) and len(rig.lane.fallback.seq_cache) == 2
    rig.feed(_fb_impact(5, caster=4, target=0, cmd=BW.CMD_MAGIC_COUNTER, sub=0, player_caster=False, player_target=True))
    rig.step()
    next(u for u in rig.units if u["slot"] == 3)["monster_transform"] = True
    rig.feed(_fb_impact(6, caster=3, target=4, cmd=BW.CMD_ATTACK_ID, sub=BW.ABILITY_ATTACK_ID))
    rig.step()
    assert (rig.fb["none"], rig.fb["clips"]) == (4, 2)
    parse = [ln for ln in rig.lane.lines if ln.startswith(BW.LOG_FALLBACK_PARSE)]
    assert parse == [f"{BW.LOG_FALLBACK_PARSE}9 of scene -1 could not be parsed (the scene has no sequence 9"
                     f"{BW.LOG_FALLBACK_PARSE_TAIL}"]
    rig.lane.discard_all("teardown (bench)")
    summary = [ln for ln in rig.lane.lines if ln.startswith(BW.LOG_FALLBACK_SUMMARY)]
    assert summary == [f"{BW.LOG_FALLBACK_SUMMARY}teardown (bench)) -- 2 clip(s), 0 collapsed, 0 deduped, 0 covered, 4 none, "
                       "0 guarded, 0 backlog, 1 parse failure(s)"]
    assert rig.fb["clips"] == 2 and rig.lane.fallback.seq_cache == {}  # the counters stay; the cache is per boot
    quiet = _FbRig()
    quiet.lane.fallback.covered = 3
    quiet.lane.discard_all("teardown")
    assert not [ln for ln in quiet.lane.lines if ln.startswith(BW.LOG_FALLBACK_SUMMARY)]


#: coop_action_fallback's offline oracle, run in a CHILD (the scenario puts its own dir on sys.path at import): a synthetic
#: raw17 through the kit's seqcodec, the clips read back as JSON
_FB_ORACLE = r"""
import importlib.util, json, os, struct, sys
scen, tools = sys.argv[1], sys.argv[2]
sys.path.insert(0, tools)
spec = importlib.util.spec_from_file_location("coop_action_fallback", os.path.join(scen, "coop_action_fallback.py"))
fb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fb)
# 4 sequence slots: 0 = Idle (byte 255) then anim code 1; 1 = END only; 2 = no sequence (offset 0); 3 = anim code 0 only
# -- [fix pass: harness-04] with seqBaseAnim 1 (the scene's SECOND enemy type: its anims start one into the list), so sub
# 3's code 0 resolves to anim_list[1 + 0] = 1002, never anim_list[0]
seq_count, anim_count = 4, 2
body_start = 8 + 3 * seq_count + 4 * anim_count
b0, b1, b3 = bytes([0x05, 255, 0x05, 1, 0x00]), bytes([0x00]), bytes([0x05, 0, 0x00])
offs = (body_start - 4, body_start - 4 + len(b0), 0, body_start - 4 + len(b0) + len(b1))
cam = body_start + len(b0) + len(b1) + len(b3)
raw = (struct.pack("<hhhh", 0, cam, seq_count, anim_count) + struct.pack("<4h", *offs) + struct.pack("<2i", 1001, 1002)
       + bytes([0, 0, 0, 1]) + b0 + b1 + b3 + b"\x00" * 4)
names = {1001: "ANH_MON_TEST_000_000", 1002: "ANH_MON_TEST_000_010"}
clips = fb.btlseq_clips(raw, names)
# THE MUTANT: an oracle that drops seqBaseAnim (at = code) -- the kit's parse with every base zeroed
sc = fb._kit()[1]
orig = sc.parse
def parse_no_base(data):
    m = orig(data)
    m.seq_base_anim = [0] * len(m.seq_base_anim)
    return m
sc.parse = parse_no_base
try:
    mutant = fb.btlseq_clips(raw, names)
finally:
    sc.parse = orig
print(json.dumps({"clips": {str(k): v for k, v in clips.items()}, "idle": fb.idle_only_subs(clips),
                  "mutant": {str(k): v for k, v in mutant.items()},
                  "kit": fb.kit_file(), "bad": fb.btlseq_clips(b"\x00\x01", names)}))
"""


def test_the_offline_btlseq_oracle_reads_load_from_btl_seqs_way():
    """The s136 bench's OFFLINE enemy-clip oracle (coop_action_fallback.btlseq_clips over the kit's own seqcodec) reads a
    raw17 as BattleActionThread.LoadFromBtlSeq does -- each case-5 op's anim id through seqBaseAnim[sub] + its code into the
    anim list, byte 255 the literal "Idle", END's appended Idle -- and picks through battlewire's first-clip twin: a
    sequence whose first op is Idle reads its second clip; an END-only one none (an IDLE-ONLY sub); a slot with no sequence
    is absent; an unreadable raw17 reads {} (the bench names it). The kit it imports is THIS checkout's. [fix pass:
    harness-04] One sub has a NON-ZERO seqBaseAnim (a scene's second enemy type always does): its code 0 reads anim_list[1];
    THE MUTANT that drops the base (at = code) reads anim_list[0] there -- its own red."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("COOP_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    out = subprocess.run([sys.executable, "-c", _FB_ORACLE, str(SCENARIOS), str(REPO / "tools")], env=env,
                         capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-2000:]
    got = json.loads(out.stdout.strip().splitlines()[-1])
    assert got["clips"] == {"0": "ANH_MON_TEST_000_010", "1": None, "3": "ANH_MON_TEST_000_010"}, got
    assert got["mutant"]["3"] == "ANH_MON_TEST_000_000" != got["clips"]["3"], ("the base-dropping red never came", got)
    assert got["idle"] == [1] and got["bad"] == {}
    assert pathlib.Path(got["kit"]).resolve().is_relative_to((REPO / "ff9mapkit").resolve()), got["kit"]


#: [fix pass: harness-05] coop_action_fallback.oracle_overrides on a synthetic install (a CHILD, as the other bench runs)
_FB_OVERRIDES = r"""
import importlib.util, json, os, sys
scen, tools, game = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, tools)
spec = importlib.util.spec_from_file_location("coop_action_fallback", os.path.join(scen, "coop_action_fallback.py"))
fb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fb)
print(json.dumps({n: [os.path.relpath(p, game).replace(os.sep, "/") for p in fb.oracle_overrides(game, n)]
                  for n in ("EF_R004", "EF_R007", "EF_R999")}))
"""


def test_the_s136_oracle_fails_closed_on_a_stacked_override(tmp_path):
    """[fix pass: harness-05] The offline oracle reads the BASE p0data2 only, so a Memoria.ini [Mod] FolderNames folder
    that overrides the scene's sequences -- a loose raw17 under battlescene/evt_battle_<name>/, or its own p0data2.bin --
    is named (scene_oracle then fails closed with that path); a folder not in FolderNames, and another scene's raw17,
    are not; a clean install names nothing."""
    game = tmp_path / "game"
    raw = game / "ModA" / "StreamingAssets" / "Assets" / "Resources" / "BattleMap" / "BattleScene" / "EVT_BATTLE_EF_R004"
    raw.mkdir(parents=True)
    (raw / "EF_R004.raw17.bytes").write_bytes(b"\x00" * 8)
    (game / "ModB" / "StreamingAssets").mkdir(parents=True)
    (game / "ModC" / "StreamingAssets").mkdir(parents=True)
    (game / "ModC" / "StreamingAssets" / "p0data2.bin").write_bytes(b"\x00")      # not stacked: never read
    env = {k: v for k, v in os.environ.items() if not k.startswith("COOP_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    def run():
        out = subprocess.run([sys.executable, "-c", _FB_OVERRIDES, str(SCENARIOS), str(REPO / "tools"), str(game)],
                             env=env, capture_output=True, text=True, timeout=120)
        assert out.returncode == 0, out.stderr[-2000:]
        return json.loads(out.stdout.strip().splitlines()[-1])
    assert run() == {"EF_R004": [], "EF_R007": [], "EF_R999": []}                 # no Memoria.ini: nothing stacked
    (game / "Memoria.ini").write_text('[Mod]\nFolderNames = "ModA", "ModB"\n', encoding="utf-8")
    assert run() == {"EF_R004": ["ModA/StreamingAssets/Assets/Resources/BattleMap/BattleScene/EVT_BATTLE_EF_R004/"
                                 "EF_R004.raw17.bytes"], "EF_R007": [], "EF_R999": []}
    (game / "ModB" / "StreamingAssets" / "p0data2.bin").write_bytes(b"\x00")
    got = run()
    assert got["EF_R007"] == got["EF_R999"] == ["ModB/StreamingAssets/p0data2.bin"] and len(got["EF_R004"]) == 2, got


def test_the_s136_bench_predicts_its_reds_as_its_docstring_says():
    """[ff9mapkit netsync s136] coop_action_fallback.py's calibration tables, pinned to its docstring: on s135 (and older)
    every check is red but INI / S0 / PRE / TAPE / ORACLE / INV (the act.guest.fallback probe fails closed: no fallback op
    ever sent); under its own lever (`actbench fallback off` before boot 1) exactly the LEVER set -- every leg reads its
    counter's move -- every id one its catalog defines; boot 1 kills nothing (LETHAL and BACKLOG each own a boot) and plays
    OLD before the bursts (the per-boot clip-line cap). Its tape leg: on an s135 guest every fallback check, under the
    INVERSE knob (ActionReplay=1) exactly UNCOV / CLIP / ENEMY / LOG with NONE a maybe -- [fix pass: harness-03] its
    accounting check ACCT, not a once-per-action claim the tape cannot fail. [fix pass: harness-01] Its ARC leg (the s117
    arc tape: an old host through the real intake): on s135 every fallback check fails closed, on s136 nothing is predicted
    red. [fix pass: timing-4] OLD's two in-window impacts ride ONE `feedat` verb. Its probe is the s136 key, its scene
    the s134 bench's, its nonce and figures its own MARKERS, its proof line the engine's, the s134 lessons in its docstring
    -- the Potion leg's target named, the Idle-only and distinct-id burst legs there (audit 4.8) -- and it never sends a
    `dioleave` (s134 LESSON 2) or `endbench kill`, and every follow-up that must land inside a window or before a boot's
    latch rides its feed's OWN request."""
    fb = _scenario_tables()["fb"]
    g = lambda *n: sorted(f"S136-{x}" for x in n)                     # noqa: E731
    assert set(fb["catalog"]) == set(fb["plain"]) | {"S136-CAL"} and len(fb["plain"]) == 27
    assert fb["old"] == sorted(set(fb["plain"]) - set(g("INI", "S0", "PRE", "TAPE", "ORACLE", "INV")))
    assert fb["lever"] == g("ITEM", "ITEMA", "MAGIC", "ATTACK", "ENEMY", "IDLE", "DEF", "SELF", "BURST1", "BURSTD", "BURSTC",
                            "OLD", "COV", "DECL", "NOOP", "LETHAL", "BACKLOG")
    assert fb["maybe"] == [] and set(fb["lever"]) < set(fb["old"]) and set(fb["fallback"]) <= set(fb["plain"])
    assert set(fb["plain"]) - set(fb["lever"]) == set(g("INI", "S0", "P0", "PROOF", "PRE", "TAPE", "ORACLE", "BOOT", "INV",
                                                        "R"))
    for piece in ("RED, exactly: every check but INI, S0, PRE, TAPE, ORACLE, INV (nothing booted, nothing to change)",
                  "Predicted reds, exactly: ITEM, ITEMA, MAGIC, ATTACK, ENEMY, IDLE, DEF, SELF, BURST1, BURSTD, BURSTC, OLD, "
                  "COV, DECL, NOOP, LETHAL, BACKLOG (", "GREEN: INI, S0, P0, PROOF, PRE, TAPE, ORACLE, BOOT, INV, R.",
                  "ITS IN-RUN RED", "Garnet's Potion on HERSELF (the self target: no DmgMot -- D-b, amendment 4)",
                  "Garnet's Potion on VIVI", "an Idle-only sequence", "three distinct action ids",
                  "RED exactly P0, UNCOV, CLIP, ENEMY, NONE, ACCT, LOG (fails closed)",
                  "RED exactly P0, OLD, CLIP, ENEMY, ACCT, LOG (fails closed)", "THE ARC LEG (COOP_FB_LEG=arc)",
                  "ONCE PER ACTION is the solo BURST1 / OLD legs' proof", "'action fallback selftest: OK (30 rows)'",
                  "THE SLIDE dedupes", "ONE CLIP INJECTED", "LOOP move (ScriptCounter1, cmd 63)",
                  "RED exactly UNCOV, CLIP, ENEMY, LOG (nothing uncovered plays a clip); NONE is a maybe",
                  "THE ORACLE (an enemy's clip): derived OFFLINE", "Never read from the engine under test",
                  "THE CASTERS BY WIRE SLOT AND MODEL", "s134 LESSON 1", "s134 LESSON 2", "s134 LESSON 3", "s134 LESSON 4",
                  "Memoria.ini [Netsync] Enabled = 0 (or absent)", "THE PER-BOOT LOG CAP", "with [Netsync] ActionReplay=0"):
        assert piece in fb["doc"], piece
    assert fb["probe"] == "netsync.battle.act.guest.fallback" == Session.NETSYNC_ACTBENCH_OP_CAPS["fallback"][1]
    assert fb["scene"] == 306 and fb["group"] in (2, 4) and fb["leg"] == "solo" and fb["legs"] == ["solo", "tape", "arc"]
    assert fb["proof"] == BW.proof_ok(BW.PROOF_FALLBACK, BW.FALLBACK_SELFTEST_ROWS)
    assert fb["nonce"] == 0x5E and fb["nonce"] not in (fb["replay_nonce"], fb["hold_nonce"])
    assert len(set(fb["figs"])) == len(fb["figs"]) == 18 and all(5161 <= f <= 5178 for f in fb["figs"])
    assert not set(fb["figs"]) & set(_scenario_tables()["hd"]["figs"])
    boot1 = fb["boot1"]
    assert boot1[0] == "S136-BOOT" and not set(boot1) & set(g("LETHAL", "BACKLOG"))
    assert boot1.index("S136-OLD") < boot1.index("S136-BURST1") and boot1[-3:] == ["S136-COV", "S136-DECL", "S136-NOOP"]
    t = lambda *n: sorted(f"S136T-{x}" for x in n)                    # noqa: E731
    assert set(fb["tape"]) == set(fb["tape_plain"]) | {"S136T-CAL"}
    assert set(fb["tape_plain"]) == set(fb["tape_fb"]) | {"S136T-I", "T2-TAPE", "T2-CAL", "T2-PEER", "T2-SAVE", "T2-INI"}
    assert fb["tape_old"] == fb["tape_fb"] == t("P0", "UNCOV", "CLIP", "ENEMY", "NONE", "ACCT", "LOG")
    assert fb["tape_old_maybe"] == [] and fb["tape_replay"] == t("UNCOV", "CLIP", "ENEMY", "LOG")
    assert fb["tape_replay_maybe"] == t("NONE")
    a = lambda *n: sorted(f"S136A-{x}" for x in n)                    # noqa: E731
    assert set(fb["arc"]) == set(fb["arc_plain"]) | {"S136A-CAL"}
    assert set(fb["arc_plain"]) == set(fb["arc_fb"]) | {"S136A-I", "T2-TAPE", "T2-CAL", "T2-PEER", "T2-SAVE", "T2-INI"}
    assert fb["arc_old"] == fb["arc_fb"] == a("P0", "OLD", "CLIP", "ENEMY", "ACCT", "LOG")
    assert fb["arc_new"] == [] and fb["arc_maybe"] == [] and fb["arc_tape"] == fb["arc_name"]
    src = (SCENARIOS / "coop_action_fallback.py").read_text(encoding="utf-8")
    code = "\n".join(ln for ln in src.split('"""', 2)[2].splitlines() if not ln.lstrip().startswith("#"))
    assert "dioleave" not in code and "endbench kill" not in code and '"kill"' not in code
    # the follow-ups that must land inside a window or before the boot's latch ride ONE request (s135 LESSON)
    for leg, sends in (("_boot_backlog", 'g.send(f"netsync dioboot {SCENE} {GROUP}", f"netsync actbench feed'),
                       ("_leg_burst1", 'g.send(f"netsync actbench feed {_feed_arg([start, frames[0]])}", '
                                       'f"netsync actbench feed {_feed_arg(frames[1:])}"'),
                       ("_leg_old", 'g.send(f"netsync actbench feed {_feed_arg(old[0])}", f"netsync actbench feedat 250 '
                                    '{_feed_arg(old[1:3])}",\n               f"netsync actbench feedat 500 {_feed_arg(old[3])}", '
                                    'f"netsync actbench feedat 1100 {_feed_arg(old[4])}"'),
                       ("_leg_enemy", 'g.send(f"netsync actbench feed {_feed_arg(frames)}", f"netsync actbench feed '
                                      '{_feed_arg(loop_frames)}"')):
        body = code.split(f"def {leg}(", 1)[1].split("\ndef ", 1)[0]
        assert sends in body, leg
    # the lever: only under COOP_CALIBRATE (before boot 1, back after) and the release's left-set
    assert code.count('_act_verb(g, "fallback", "off")') == 2 and code.count('_act_verb(g, "fallback", "on")') == 1


#: coop_action_fallback's pure judges, run on synthetic inputs (JSON on stdin), the verdicts read back
_FB_JUDGE = r"""
import importlib.util, json, os, sys
scen, tools = sys.argv[1], sys.argv[2]
sys.path.insert(0, tools)
spec = importlib.util.spec_from_file_location("coop_action_fallback", os.path.join(scen, "coop_action_fallback.py"))
fb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fb)
class Led:
    def __init__(self):
        self.checks = {}
    def check(self, cid, ok, detail=""):
        self.checks[cid] = [bool(ok), str(detail)]
    def unreached(self, ids, why):
        for c in ids:
            self.checks.setdefault(c, [False, "unreached: " + why])
doc = json.loads(sys.stdin.read())
out = {"pred": {k: fb.no_clip_pred(c["delta"], c["bucket"], c.get("n", 1)) for k, c in doc["pred"].items()},
       "clip": {k: list(fb.judge_clip(c["last"], **c["want"])) for k, c in doc["clip"].items()},
       "window": {k: list(fb.judge_window(c["records"], 1, 22, 25, c["min_gap"]) if isinstance(c, dict) else
                          fb.judge_window(c, 1, 22, 25)) for k, c in doc["window"].items()},
       "red": {k: fb.in_run_red(c["delta"], c["bucket"], c.get("n", 1)) for k, c in doc["red"].items()},
       "union": fb.lasts_union(doc["union"]), "tape": {}, "arc": {},
       "arcfacts": {k: list(fb.arc_tape_facts(v)) for k, v in doc["arcfacts"].items()}}
# THE MUTANT of the in-run red's predicate: blind to the clips conjunct (the sibling-delta red could not tell it apart)
orig = fb.no_clip_pred
fb.no_clip_pred = lambda d, b, n=1: d.get(b) == n and d.get("collapsed") == 0
try:
    out["red_blind"] = {k: fb.in_run_red(c["delta"], c["bucket"], c.get("n", 1)) for k, c in doc["red"].items()}
finally:
    fb.no_clip_pred = orig
for leg, judge in (("tape", fb.judge_fallback_tape), ("arc", fb.judge_fallback_arc)):
    for name, run in doc[leg].items():
        led = Led()
        oracle = {int(k): v for k, v in run["oracle"].items()} if run.get("oracle") is not None else None
        judge(led, run["samples"], run["messages"], run["act"], oracle, "no oracle here")
        out[leg][name] = led.checks
print(json.dumps(out))
"""


def _fb_last(kind="attack", clip="ANH_MAIN_B0_000_103", *, actor=0, cmd=1, sub=176, keyed_by="id", act_id=7,
             via="arrival", ms=100) -> dict:
    return {"actor": actor, "clip": clip, "cmd": cmd, "sub": sub, "keyed_by": keyed_by, "kind": kind, "id": act_id,
            "via": via, "ms": ms}


def _fb_tape_run(**over) -> dict:
    """A synthetic tape-leg run on the knob: every START declined `knob`, the impacts uncovered -- clips (an attack and
    two enemy subs), the Defends' none -- and the engine's clip lines and summary."""
    fbk = dict(BW.ACT_GUEST_FALLBACK_SENTINELS, on=True, clips=5, none=8, last=_fb_last())
    fbk.update(over.get("fallback", {}))
    guest = {"starts_rx": 13, "started": 0, "declined": 13, "declined_why": "knob", "paired": 13, "fallback": fbk}
    guest.update(over.get("guest", {}))
    early = dict(fbk, last=_fb_last("enemy", "ANH_MON_B3_001_010", actor=4, cmd=47, sub=0, act_id=2), clips=1)
    samples = [{"booted": True, "guest": dict(guest, fallback=early)}, {"booted": True, "guest": guest}]
    if over.get("no_fallback"):
        samples = [{"booted": True, "guest": {k: v for k, v in guest.items() if k != "fallback"}}]
    line = lambda kind, clip, slot, cmd, sub, i: (                       # noqa: E731
        f"16.10.2026 12:00:00 |M| {BW.LOG_FALLBACK}{kind} clip {clip} on wire slot {slot} (cmd {cmd} sub {sub}, keyed by id "
        f"{i}, via arrival) at battle ms {100 * i}{BW.LOG_FALLBACK_CLIP_TAIL}")
    messages = over.get("messages", [
        line("enemy", "ANH_MON_B3_001_010", 4, 47, 0, 2), line("enemy", "ANH_MON_B3_001_030", 4, 47, 2, 12),
        line("attack", "ANH_MAIN_B0_000_103", 0, 1, 176, 13),
        f"{BW.LOG_FALLBACK_SUMMARY}teardown) -- 5 clip(s), 0 collapsed, 0 deduped, 0 covered, 8 none, 0 guarded, 0 backlog, "
        "0 parse failure(s)"])
    return {"samples": samples, "messages": messages, "act": {"starts": 13, "impacts": 13},
            "oracle": over.get("oracle", {"0": "ANH_MON_B3_001_010", "1": None, "2": "ANH_MON_B3_001_030"})}


def _fb_arc_run(**over) -> dict:
    """[fix pass: harness-01] A synthetic ARC-leg run: an old host (no START), every write keyed by (caster, cmd, sub) with
    id 0 -- an attack and an enemy clip, the window's dedupes -- and the engine's clip lines and summary."""
    old = lambda kind, clip, actor, cmd, sub, ms: _fb_last(kind, clip, actor=actor, cmd=cmd, sub=sub,  # noqa: E731
                                                           keyed_by="caster", act_id=0, ms=ms)
    fbk = dict(BW.ACT_GUEST_FALLBACK_SENTINELS, on=True, clips=4, deduped=6, none=1,
               last=old("attack", "ANH_MAIN_B0_000_103", 0, 1, 176, 900))
    fbk.update(over.get("fallback", {}))
    guest = {"starts_rx": 0, "started": 0, "declined": 0, "old_host": True, "paired": 0, "fallback": fbk}
    guest.update(over.get("guest", {}))
    early = dict(fbk, last=old("enemy", "ANH_MON_B3_001_010", 4, 47, 0, 300), clips=1)
    samples = [{"booted": True, "guest": dict(guest, fallback=early)}, {"booted": True, "guest": guest}]
    if over.get("no_fallback"):
        samples = [{"booted": True, "guest": {k: v for k, v in guest.items() if k != "fallback"}}]
    line = lambda kind, clip, slot, cmd, sub, ms: (                      # noqa: E731
        f"16.10.2026 12:00:00 |M| {BW.LOG_FALLBACK}{kind} clip {clip} on wire slot {slot} (cmd {cmd} sub {sub}, "
        f"{BW.LOG_FALLBACK_BY_CASTER}500 ms, via arrival) at battle ms {ms}{BW.LOG_FALLBACK_CLIP_TAIL}")
    messages = over.get("messages", [
        line("enemy", "ANH_MON_B3_001_010", 4, 47, 0, 300), line("attack", "ANH_MAIN_B0_000_103", 0, 1, 176, 900),
        f"{BW.LOG_FALLBACK_SUMMARY}teardown) -- 4 clip(s), 0 collapsed, 6 deduped, 0 covered, 1 none, 0 guarded, 0 backlog, "
        "0 parse failure(s)"])
    return {"samples": samples, "messages": messages, "act": {"starts": 0, "impacts": 13},
            "oracle": over.get("oracle", {"0": "ANH_MON_B3_001_010", "1": None, "2": "ANH_MON_B3_001_030"})}


def test_the_s136_benchs_pure_judges_read_each_engine_and_can_fail():
    """coop_action_fallback's judges, PURE, on synthetic runs -- each GREEN on the s136 shape and RED on every shape it
    exists to catch: no_clip_pred (a clip written, the bucket off by one, a collapse), judge_clip (the wrong kind, id, via,
    key, an "Idle" or empty clip, the oracle's clip missed), judge_window (one write, a gap under 500 ms, an id-keyed write),
    lasts_union (dedupes), [fix pass 2] judge_window's OLD shape (A and E: an anchored window's three writes, a second write
    that is D -- each red) and in_run_red (False on each no-clip leg's own shape; a predicate blind to the clips conjunct
    reads True there), and judge_fallback_tape: an s135 guest fails closed; the INVERSE knob (the replays cover: started
    13, covered 13, clips 0, no clip line) is red on exactly UNCOV / CLIP / ENEMY / LOG; an enemy clip off the oracle, a
    missing oracle, a fault line, a parse failure, an attack-only run, more decisions than impacts, [fix pass: harness-03]
    fewer than the paired impacts (a dropped bucket): each its own red. [fix pass: harness-01] judge_fallback_arc: an s135
    guest fails closed; a write keyed by id, a START seen, a guest that never saw an old host, an enemy clip off the oracle
    or none at all, more decisions than impacts, a fault line: each its own red; arc_tape_facts takes only an old host's
    battle (impacts, no START)."""
    zero = dict.fromkeys((*BW.ACT_FALLBACK_BUCKETS, "parse_failed"), 0)
    pred = {"green": {"delta": dict(zero, none=1), "bucket": "none"},
            "clip": {"delta": dict(zero, none=1, clips=1), "bucket": "none"},
            "two": {"delta": dict(zero, none=2), "bucket": "none"},
            "collapsed": {"delta": dict(zero, guarded=1, collapsed=1), "bucket": "guarded"},
            "pair": {"delta": dict(zero, none=2), "bucket": "none", "n": 2}}
    want = {"want_id": 7, "kind": "attack", "cmd": 1, "sub": 176, "actor": 0, "keyed_by": "id"}
    clip = {"green": {"last": _fb_last(), "want": want},
            "kind": {"last": _fb_last("magic"), "want": want},
            "id": {"last": _fb_last(act_id=8), "want": want},
            "via": {"last": _fb_last(via="declined"), "want": want},
            "key": {"last": _fb_last(keyed_by="caster", act_id=0), "want": want},
            "idle": {"last": _fb_last(clip="Idle"), "want": want},
            "empty": {"last": _fb_last(clip=""), "want": want},
            "oracle": {"last": _fb_last("enemy", "X", actor=4, cmd=47, sub=0),
                       "want": dict(want, kind="enemy", cmd=47, sub=0, actor=4, clip="Y")},
            "old": {"last": _fb_last("magic", actor=1, cmd=22, sub=25, keyed_by="caster", act_id=0),
                    "want": dict(want, want_id=None, kind="magic", cmd=22, sub=25, actor=1, keyed_by="caster")}}
    w = lambda ms, **kw: dict(_fb_last("magic", actor=1, cmd=22, sub=25, keyed_by="caster", act_id=0, ms=ms), **kw)  # noqa: E731
    window = {"green": [w(100), w(850)], "one": [w(100)], "short": [w(100), w(450)],
              "byid": [w(100), w(850, keyed_by="id", id=9)], "other": [w(100), w(850, sub=26)],
              # [fix pass 2: rharness-03] OLD's own shape: A and E (the slide deduped D); an ANCHORED window's A, D and E;
              # a second write that is D (under OLD_E_GAP)
              "slide": {"records": [w(100), w(1350)], "min_gap": 1000},
              "anchored": {"records": [w(100), w(760), w(1350)], "min_gap": 1000},
              "d_not_e": {"records": [w(100), w(760)], "min_gap": 1000}}
    # [fix pass 2: rharness-02] the in-run red on each no-clip leg's OWN shape: False with one clip injected
    red = {"none": {"delta": dict(zero, none=1), "bucket": "none"},
           "def": {"delta": dict(zero, none=2), "bucket": "none", "n": 2},
           "covered": {"delta": dict(zero, covered=1), "bucket": "covered"},
           "backlog": {"delta": dict(zero, backlog=1), "bucket": "backlog"}}
    union = [{"last": _fb_last()}, {"last": _fb_last()}, {"last": None}, {"last": _fb_last(act_id=9)}, "junk"]
    tape = {"green": _fb_tape_run(), "old": _fb_tape_run(no_fallback=True),
            "replay": _fb_tape_run(guest={"started": 13, "declined": 4, "declined_why": "stale"},
                                   fallback={"clips": 0, "covered": 9, "none": 4, "last": None},
                                   messages=[f"{BW.LOG_FALLBACK_SUMMARY}teardown) -- 0 clip(s), 0 collapsed, 0 deduped, 9 "
                                             "covered, 4 none, 0 guarded, 0 backlog, 0 parse failure(s)"]),
            "enemy_off": _fb_tape_run(oracle={"0": "ANH_MON_B3_001_011", "2": "ANH_MON_B3_001_030"}),
            "no_oracle": dict(_fb_tape_run(), oracle=None),
            "fault": _fb_tape_run(messages=_fb_tape_run()["messages"] + [f"{BW.LOG_FALLBACK_FAULTED}NullReferenceException"]),
            "parse": _fb_tape_run(fallback={"parse_failed": 1}),
            "attack_only": _fb_tape_run(messages=[_fb_tape_run()["messages"][2], _fb_tape_run()["messages"][3]],
                                        fallback={"last": _fb_last()}),
            "too_many": _fb_tape_run(fallback={"clips": 9, "none": 8}),
            "dropped": _fb_tape_run(fallback={"clips": 4, "none": 8})}         # 12 buckets < 13 paired: one dropped
    arc = {"green": _fb_arc_run(), "old": _fb_arc_run(no_fallback=True),
           "byid": _fb_arc_run(messages=_fb_arc_run()["messages"] + [
               f"{BW.LOG_FALLBACK}attack clip ANH_MAIN_B0_000_103 on wire slot 0 (cmd 1 sub 176, keyed by id 7, via arrival) "
               f"at battle ms 1200{BW.LOG_FALLBACK_CLIP_TAIL}"]),
           "starts": _fb_arc_run(guest={"starts_rx": 2}),
           "not_old": _fb_arc_run(guest={"old_host": False}),
           "enemy_off": _fb_arc_run(oracle={"0": "ANH_MON_B3_001_011"}),
           "no_enemy": _fb_arc_run(messages=_fb_arc_run()["messages"][1:]),
           "too_many": _fb_arc_run(fallback={"deduped": 9}),
           "fault": _fb_arc_run(messages=_fb_arc_run()["messages"] + [f"{BW.LOG_FALLBACK_FAULTED}KeyNotFoundException"])}
    arc["no_enemy"]["samples"] = arc["no_enemy"]["samples"][1:]
    arcfacts = {"old": {"starts": 0, "impacts": 13, "ext": 0}, "new": {"starts": 13, "impacts": 13, "ext": 13},
                "empty": {"starts": 0, "impacts": 0}}
    for name in ("attack_only", "replay"):                              # (no earlier enemy write on these runs)
        tape[name]["samples"] = tape[name]["samples"][1:]
    env = {k: v for k, v in os.environ.items() if not k.startswith("COOP_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    out = subprocess.run([sys.executable, "-c", _FB_JUDGE, str(SCENARIOS), str(REPO / "tools")], env=env,
                         input=json.dumps({"pred": pred, "clip": clip, "window": window, "red": red, "union": union,
                                           "tape": tape, "arc": arc, "arcfacts": arcfacts}),
                         capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-2000:]
    got = json.loads(out.stdout.strip().splitlines()[-1])
    assert got["pred"] == {"green": True, "clip": False, "two": False, "collapsed": False, "pair": True}, got["pred"]
    assert {k: v[0] for k, v in got["clip"].items()} == {"green": True, "kind": False, "id": False, "via": False,
                                                        "key": False, "idle": False, "empty": False, "oracle": False,
                                                        "old": True}, got["clip"]
    assert {k: v[0] for k, v in got["window"].items()} == {"green": True, "one": False, "short": False, "byid": False,
                                                          "other": False, "slide": True, "anchored": False,
                                                          "d_not_e": False}, got["window"]
    assert got["red"] == dict.fromkeys(red, False), got["red"]          # every own-shape red reads False...
    assert got["red_blind"] == dict.fromkeys(red, True), got["red_blind"]   # ...and a clips-blind predicate cannot
    assert "gap 750" in got["window"]["green"][1] and len(got["union"]) == 2
    fbk = ("S136T-P0", "S136T-UNCOV", "S136T-CLIP", "S136T-ENEMY", "S136T-NONE", "S136T-ACCT", "S136T-LOG")
    red = lambda name: sorted(c for c, (ok, _d) in got["tape"][name].items() if not ok)   # noqa: E731
    assert set(got["tape"]["green"]) == set(fbk) and red("green") == [], got["tape"]["green"]
    assert red("old") == sorted(fbk) and all("unreached" in d for _ok, d in got["tape"]["old"].values())
    assert red("replay") == sorted(("S136T-UNCOV", "S136T-CLIP", "S136T-ENEMY", "S136T-LOG")), got["tape"]["replay"]
    assert red("enemy_off") == ["S136T-ENEMY"] and "ANH_MON_B3_001_011" in got["tape"]["enemy_off"]["S136T-ENEMY"][1]
    assert red("no_oracle") == ["S136T-ENEMY"] and "no oracle here" in got["tape"]["no_oracle"]["S136T-ENEMY"][1]
    assert red("fault") == ["S136T-LOG"] and red("parse") == ["S136T-ACCT"] and red("too_many") == ["S136T-ACCT"]
    assert red("dropped") == ["S136T-ACCT"] and "paired 13" in got["tape"]["dropped"]["S136T-ACCT"][1]
    assert red("attack_only") == ["S136T-CLIP", "S136T-ENEMY"], got["tape"]["attack_only"]
    # [fix pass: harness-01] the arc leg's judge
    afb = ("S136A-P0", "S136A-OLD", "S136A-CLIP", "S136A-ENEMY", "S136A-ACCT", "S136A-LOG")
    ared = lambda name: sorted(c for c, (ok, _d) in got["arc"][name].items() if not ok)   # noqa: E731
    assert set(got["arc"]["green"]) == set(afb) and ared("green") == [], got["arc"]["green"]
    assert ared("old") == sorted(afb) and all("unreached" in d for _ok, d in got["arc"]["old"].values())
    assert (ared("byid"), ared("starts"), ared("not_old")) == (["S136A-CLIP"], ["S136A-OLD"], ["S136A-OLD"]), got["arc"]
    assert (ared("enemy_off"), ared("no_enemy"), ared("too_many"), ared("fault")) == (
        ["S136A-ENEMY"], ["S136A-ENEMY"], ["S136A-ACCT"], ["S136A-LOG"]), got["arc"]
    assert {k: v[0] for k, v in got["arcfacts"].items()} == {"old": True, "new": False, "empty": False}, got["arcfacts"]
