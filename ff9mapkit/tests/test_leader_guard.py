"""[ff9mapkit netsync s143] THE GUEST NEVER COMMANDS THE HOST'S LEADER -- the offline twin of NetSyncBattle's leader guard, pinned
to the live patch stack (memoria-patches/, read through tests/_patchstack -- no clone, no install).

Owner decision 2026-10-19 (after the Plant Brain report "the host lost control of Zidane"): [Netsync] GuestSlots stays a
party-POSITION mask, but a guest bit that lands on the host's LEADER (the character its controlled field body is) moves to the
next occupied index after it (wrapping) that is neither the leader nor already owned; none -> the bit drops. Pinned here:

  * THE RULE: a Python twin of LeaderGuard / LeaderGuardCore, run over the engine selftest's OWN rows (parsed off the patch:
    every `GuardIs(rule, ...)` row) -- each row holds on the twin, and each of the engine's three mutants (no guard, no wrap,
    onto an owned bit) fails FIRST at the row the engine's selftest names for it; a twin mutant that is not caught turns red.
  * THE LEADER MAP: the patch's PcVariantModels / PcVariantChars == the frozen census's `pc_variants` (studies/battle-coop/
    dress-census/leader_census.json, numbers and open-source names only; its Zidane subset == `zidane_variants`), and its rows
    agree with the rig table; THE LATCH STEP (NextLeader: a body naming no character keeps the leader; the world map's walker
    from `world_leader`) and the guest line's same-battle test and its STEP over sequences (a relaunched host's latch is
    forgotten -- review s143 rwire-1), each engine row evaluated on the twin and failed by a mutant;
    the census regenerates from the user's own exports when they are on this machine (skips cleanly without them).
  * THE LINE's text: the twin's strings are the engine selftest's.
  * THE CALL-SITE LAW (a law in a docstring is a wish): every battle OWNERSHIP read of GuestSlots in NetSyncBattle.cs goes
    through EffectiveGuestSlots -- the raw reads left are the getter itself, the cheap gates in front of it and the line's
    "is co-op battle on" test; no other file of the stack reads the mask QUALIFIED (`NetSyncBattle.GuestSlots`) but the
    harness's raw-by-contract `guest_slots` key; the guest side -- its own files AND NetSyncBattle.cs's guest methods --
    reads only the host's header (`view.GuestSlots`), each scan shown able to fail on an injected read.
  * THE PROTOCOL: the harness keys are additive (`netsync.battle.host.guard`, `netsync.battle.peer.guard`, `netsync.dress.guard`)
    with their sentinels in AppendNetsync's catch literal, the `bench leaderguard` op released by HarnessReleaseBench, the
    harness protocol 5 and the wire v14.
"""
import json
import pathlib
import re
import sys

import pytest

from ._patchstack import msr, net_lines, net_lines_ordered

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from harness import battlewire as BW                                   # noqa: E402
CENSUS = REPO / "studies" / "battle-coop" / "dress-census"
EXPORTS = pathlib.Path(r"C:\gd\FFIX\reference\test2")
MEMORIA = pathlib.Path(r"C:\gd\FFIX\Memoria")
PATCH = "s143-netsync-guest-never-leader.patch"

ZIDANE, VIVI, GARNET, STEINER = 0, 1, 2, 3


# ------------------------------------------------------------------------------------------------ the twin (battlewire's)
leader_guard = BW.leader_guard
mutant_no_guard = BW.mutant_guard_none
mutant_no_wrap = BW.mutant_guard_no_wrap
mutant_onto_owned = BW.mutant_guard_onto_owned
guard_line_text = BW.guard_line_text


# ------------------------------------------------------------------------------------------------ the engine's rows
_ROW = re.compile(r'if \(!GuardIs\(rule, (null|new Int32\[\] \{ ([-\d, ]+) \}), (0x[0-9A-Fa-f]+|\d+), (-?\d+), '
                  r'(0x[0-9A-Fa-f]+|\d+), (-?\d+), (-?\d+), ref n\)\) return "((?:[^"\\]|\\.)*)";')


def _rows() -> list:
    """The engine selftest's table rows, in FILE order: (name, chars|None, raw, leader, (eff, from, to))."""
    out = []
    for line in net_lines_ordered("NetSyncBattle.cs", r"if \(!GuardIs\(rule, "):
        m = _ROW.match(line)
        assert m, line
        chars = None if m.group(1) == "null" else tuple(int(x) for x in m.group(2).split(","))
        out.append((m.group(8), chars, int(m.group(3), 0), int(m.group(4)),
                    (int(m.group(5), 0), int(m.group(6)), int(m.group(7)))))
    return out


def _first_failure(rule) -> str | None:
    for name, chars, raw, leader, want in _rows():
        if rule(chars, raw, leader) != want:
            return name
    return None


def _upto(stem: str) -> list:
    """[ff9mapkit netsync s144] The live stack's patch bytes up to and including ``stem`` (the agent AT that patch)."""
    out = []
    for name in msr.stack():
        if name in msr.DEAD:
            continue
        out.append((msr.PATCHES / name).read_bytes())
        if name.startswith(stem + "-"):
            return out
    raise AssertionError(f"no live patch {stem}")


_CATCH = r'outer\.Append\("\\"netsync\\":\{\\"enabled'


def _catch_line(patches=None) -> str:
    """The agent's catch literal (AppendNetsync's), unescaped -- the live stack's, or ``patches``'."""
    lines = net_lines("HarnessAgent.cs", _CATCH, patches)
    assert len(lines) == 1, lines
    return lines[0].replace('\\"', '"')


def _stack(file_name: str) -> list:
    return net_lines(file_name, r".")


def test_the_engines_rows_are_the_story_and_hold_on_the_twin():
    rows = _rows()
    assert len(rows) == 25, len(rows)
    names = [r[0] for r in rows]
    for story in ("Plant Brain", "the forest exit", "COOPPARTY", "Shell Dragon", "Amdusias", "Abadon", "Ice Cavern",
                  "multi-bit", "solo", "leader absent", "no leader known", "unreadable", "empty"):
        assert any(n.startswith(story) for n in names), story
    for name, chars, raw, leader, want in rows:
        assert leader_guard(chars, raw, leader) == want, name
    # the owner's case, by hand: field 257 seats [Blank, Zidane, Vivi, Steiner]; GuestSlots 2 hands the guest VIVI now
    assert leader_guard((10, ZIDANE, VIVI, STEINER), 0x2, ZIDANE) == (0x4, 1, 2)
    # Shell Dragon's hidden-at-boot Garnet counts: the guest gets her (the wrap), the host keeps Zidane
    assert leader_guard((GARNET, ZIDANE, -1, -1), 0x2, ZIDANE) == (0x1, 1, 0)


@pytest.mark.parametrize("mutant,row", [(mutant_no_guard, "Plant Brain"), (mutant_no_wrap, "Shell Dragon"),
                                        (mutant_onto_owned, "multi-bit")])
def test_each_mutant_fails_first_at_the_row_the_engine_names(mutant, row):
    got = _first_failure(mutant)
    assert got is not None and got.startswith(row), got
    assert _first_failure(leader_guard) is None


def test_the_engines_mutants_and_their_rows_are_the_twins():
    body = " ".join(_stack("NetSyncBattle.cs"))
    for frag in ('GuardMutantRow(LeaderGuardTable(MutantNoGuard, out n), "Plant Brain", "no guard", ref rows, ref fail);',
                 'GuardMutantRow(LeaderGuardTable(MutantNoWrap, out n), "Shell Dragon", "no wrap", ref rows, ref fail);',
                 'GuardMutantRow(LeaderGuardTable(MutantOntoOwned, out n), "multi-bit", "onto an owned bit", ref rows, ref fail);',
                 "return LeaderGuardCore(slotChar, ownedMask, leaderChar, false, true, out movedFrom, out movedTo);",
                 "return LeaderGuardCore(slotChar, ownedMask, leaderChar, true, false, out movedFrom, out movedTo);",
                 "return LeaderGuardCore(slotChar, ownedMask, leaderChar, true, true, out movedFrom, out movedTo);",
                 "if (c < 0 || c == leaderChar || (skipOwned && (eff & (1 << j)) != 0))",
                 "if ((raw & (1 << i)) == 0 || GuardCharAt(slotChar, i) != leaderChar)",
                 "if (leaderChar < 0 || slotChar == null)",
                 "Int32 raw = ownedMask & 0x0F;"):
        assert frag in body, frag


def test_a_twin_that_drifts_is_caught():
    """A check that cannot fail is not a check: a twin that skips EMPTY targets wrongly, or ignores unreadable reads, fails a
    row of the engine's own table."""
    def bad_empty(chars, raw, leader):                  # treats an unreadable (-2) slot as a free member
        if chars is None:
            return leader_guard(chars, raw, leader)
        return leader_guard(tuple(VIVI if c == -2 else c for c in chars), raw, leader)

    def bad_drop(chars, raw, leader):                   # keeps the leader's bit when nothing is free
        eff, f, t = leader_guard(chars, raw, leader)
        return (eff | (1 << f), f, t) if f >= 0 and t < 0 else (eff, f, t)

    assert _first_failure(bad_empty) is not None and _first_failure(bad_drop) is not None


def test_the_leader_map_is_the_census_and_the_rig_table():
    census = json.loads((CENSUS / "leader_census.json").read_text(encoding="utf-8"))
    assert census["zidane_variants"] == [532, 203, 432]
    pc = census["pc_variants"]
    assert [(v["model"], v["char"]) for v in pc] == [(658, 3), (532, 0), (203, 0), (432, 0), (202, 2), (419, 2)]
    body = " ".join(_stack("NetSyncBattle.cs"))
    m = re.search(r"internal static readonly UInt16\[\] PcVariantModels = \{ ([\d, ]+) \};", body)
    c = re.search(r"internal static readonly Byte\[\] PcVariantChars = \{ ([\d, ]+) \};", body)
    assert m and c, (m, c)
    models, chars = [int(x) for x in m.group(1).split(",")], [int(x) for x in c.group(1).split(",")]
    assert list(zip(models, chars)) == [(v["model"], v["char"]) for v in pc]
    assert [mm for mm, cc in zip(models, chars) if cc == 0] == census["zidane_variants"]      # the Zidane subset, kept
    assert "ZidaneVariantModels" not in body
    assert BW.PC_VARIANT_MODELS == tuple(models) and BW.PC_VARIANT_CHARS == tuple(chars)
    by_model = {r["model"]: r for r in census["player_models"]}
    for v in pc:                                                             # each a main body outside the rig table
        assert by_model[v["model"]]["rig"] is None and v["geo"].startswith("GEO_MAIN_"), v
    assert by_model[98]["rig"] == 0 and by_model[98]["entries"] > 600       # the plain Zidane: the rig table's row 0
    assert census["zidane_unworn"] == [668, 669, 670]                        # worn by no player entry: not listed
    for frag in ("LeaderCharForModel(98) == 0", "LeaderCharForModel(532) == 0", "LeaderCharForModel(203) == 0",
                 "LeaderCharForModel(432) == 0", "LeaderCharForModel(658) == 3", "LeaderCharForModel(202) == 2",
                 "LeaderCharForModel(419) == 2", "LeaderCharForModel(220) == LeaderNone",
                 "LeaderCharForModel(668) == LeaderNone", "LeaderCharForModel(615) == LeaderNone",
                 "LeaderCharForModel(5467) == 10", "LeaderCharForModel(204) == 11"):
        assert frag in body, frag
    # the world map's walker (census `world_leader`: ff9.cs's k_moveCHRStatus_*): Dagger (2) walks as Garnet, else Zidane
    world = {w["status"]: w for w in census["world_leader"]}
    assert world[1]["name"] == "Zidane" and world[2]["name"] == "Dagger" and world[2]["leader"] == 2
    assert all(w["leader"] == 0 for s, w in world.items() if s != 2)
    for s, w in world.items():
        assert BW.next_leader(-1, BW.world_walker_model(s)) == w["leader"], w
    assert "return status <= 0 ? 0 : status == 2 ? WorldDaggerModel : WorldLeaderModel;" in body
    # the genuine body: a self-dressed body reads its source model (the host's own body is never dressed)
    assert "Int32 model = me.netSelfDress != 0 ? me.netDressSrc : me.model;" in body


_SYMS = {"LeaderNone": -1, "WorldLeaderModel": -3, "WorldDaggerModel": -4}


def _sym(tok: str) -> int:
    return _SYMS[tok] if tok in _SYMS else int(tok, 0)


def _next_leader_rows(body: str) -> list:
    """The engine selftest's literal NextLeader / WorldWalkerModel claims: (prev, model, want) and (status, want)."""
    nl = [(_sym(a), _sym(b), _sym(w)) for a, b, w in re.findall(r"NextLeader\((\w+), (-?\w+)\) == (\w+)", body)]
    ww = [(int(s), _sym(w)) for s, w in re.findall(r"WorldWalkerModel\((\d+)\) == (\w+)", body)]
    nw = [(_sym(a), int(s), _sym(w)) for a, s, w in re.findall(r"NextLeader\((\w+), WorldWalkerModel\((\d+)\)\) == (\w+)", body)]
    return nl, ww, nw


def test_the_latch_step_rows_hold_on_the_twin_and_the_old_overwrite_fails():
    """(review s143 field-1 / own-1) LeaderGuardSelfTest's latch rows, EVALUATED on battlewire.next_leader /
    world_walker_model: 98 -> Zidane, a chocobo or the gargant KEEPS him, 5489 -> Steiner, nothing seen + a chocobo -> none,
    the world map's walker; the pre-review overwrite (every body overwrites, no world leader) fails a row."""
    body = " ".join(_stack("NetSyncBattle.cs"))
    nl, ww, nw = _next_leader_rows(body)
    assert nl == [(-1, 98, 0), (0, 615, 0), (0, 306, 0), (0, 5489, 3), (3, 658, 3), (-1, 615, -1)], nl
    assert ww == [(0, 0), (1, -3), (3, -3), (10, -3)] and nw == [(-1, 2, 2), (3, 1, 0)], (ww, nw)
    for prev, model, want in nl:
        assert BW.next_leader(prev, model) == want, (prev, model, want)
    for status, want in ww:
        assert BW.world_walker_model(status) == want, (status, want)
    for prev, status, want in nw:
        assert BW.next_leader(prev, BW.world_walker_model(status)) == want, (prev, status, want)
    assert any(BW.mutant_next_leader_overwrite(p, m) != w for p, m, w in nl)          # the old latch is caught
    # the latch's own code: NextLeader on every field body, the world map's walker, the title's forget
    for frag in ("_leaderChar = NextLeader(was, model);", "Int32 model = WorldWalkerModel(status);",
                 "if (_leaderModel == -1 && _leaderChar == LeaderNone)"):
        assert frag in body, frag
    client = " ".join(_code(ln) for ln in _stack("NetSyncClient.cs"))
    for frag in ('atTitle = String.Equals(PersistenSingleton<SceneDirector>.Instance.CurrentScene, "");',
                 "NetSyncBattle.ForgetLeader();", "NetSyncBattle.NoteFieldLeader(ee);", "else if (ee != null && ee.gMode == 3)",
                 "try { walker = WMUIData.StatusNo; } catch { }", "NetSyncBattle.NoteWorldLeader(walker);"):
        assert frag in client, frag
    # the order: the title first (a world-map gMode can outlive a quit), then a field, then the world map
    assert client.index("NetSyncBattle.ForgetLeader();") < client.index("NetSyncBattle.NoteFieldLeader(ee);") \
        < client.index("NetSyncBattle.NoteWorldLeader(walker);")


def test_the_guest_line_rows_hold_on_the_twin_and_the_nonce_only_test_fails():
    """(review s143 wire-3) GuestLineSameBattle's rows, EVALUATED on the twin; the nonce-only test (what Pump's run-out
    forget papered over) fails one; and the run-out no longer forgets the line (GuestLineForget in NetSyncBattle.cs only in
    Reset -- the relaunch forgets are GuestLineStep's in place and NetSyncClient's epoch reset, review s143 rwire-1)."""
    body = " ".join(_stack("NetSyncBattle.cs"))
    rows = [(neg == "!", tuple(int(x) for x in args)) for neg, *args in
            re.findall(r"(!?)GuestLineSameBattle\((-?\d+), (-?\d+), (-?\d+), (-?\d+)\)", body)]
    assert len(rows) == 6, rows
    for negated, a in rows:
        assert BW.guest_line_same_battle(*a) is (not negated), (negated, a)
    assert any(BW.mutant_guest_line_nonce_only(*a) is negated for negated, a in rows)
    code = [_code(ln) for ln in _stack("NetSyncBattle.cs")]
    joined = " ".join(code)
    assert sum(ln.count("GuestLineForget();") for ln in code) == 1               # Reset only
    assert "if (!hud || _youShown || _youMask <= 0 || _youLine == null || !NetSyncDiorama.Active)" in joined
    # GuestLineTick in FILE order (net_lines keeps first-added order, so a "{" / "return;" run is only sequential here)
    tick = " ".join(" ".join(_code(ln) for ln in _method(net_lines_ordered("NetSyncBattle.cs", r"."), "GuestLineTick")).split())
    for frag in ("Int32 step = GuestLineStep(view.Nonce, view.Seq, phase, ref _youNonce, ref _youSeq);",
                 "if (step == GuestLineSame) { GuestLineLate(hud); return; }", "if (step != GuestLineNew) return;",
                 "_youSeq = view.Seq;"):
        assert frag in tick, frag
    assert "if (GuestLineSameBattle(" not in tick                               # the step decides, nothing beside it
    assert tick.index("Int32 step = GuestLineStep(") < tick.index("_youNonce = view.Nonce;")   # the step BEFORE the latch
    assert BW.guard_guest_late_log("You: Vivi", 3) == ('leader guard line (guest): "You: Vivi" shown late -- the diorama '
                                                       'came up after the host\'s command phase (nonce 3)')
    p = (msr.PATCHES / PATCH).read_bytes().decode("utf-8", "replace")
    assert '"[NetSync] leader guard line (guest): \\"" + _youLine + "\\" shown late -- the diorama came up after the host\'s "' in p


def test_the_guest_line_step_forgets_a_relaunched_hosts_latch():
    """(review s143 rwire-1) A relaunched host restarts its battle nonce AND seq, so a latch kept across the relaunch re-matched
    the new run's battle once its climbing seq passed the old one: the new line never latched (or an old log-only line showed
    LATE on the new diorama). GuestLineStep forgets the latch on an EARLIER seq of the latched nonce (the battle lane is an
    ordered TCP latest-slot), and NetSyncClient's host-epoch reset forgets it for a guest that reads section 7. Pinned: the
    engine's SEQUENCES evaluated on the twin, the review's replay by hand, the mutant without the forget failing at its own
    sequence, the twin's sequence names == the engine's, and the epoch reset's call."""
    assert BW.guest_line_sequences() is None
    bad = BW.guest_line_sequences(BW.mutant_guest_line_no_forget)
    assert bad is not None and bad.startswith("relaunch"), bad

    def latch_run(step, latch, views):
        """GuestLineTick's latch over views [(nonce, seq, ready)]: the seq each NEW latched at."""
        yn, ys = latch
        out = []
        for n, s, r in views:
            v, yn, ys = step(n, s, r, yn, ys)
            if v == BW.GUEST_LINE_NEW:
                yn, ys = n, s
                out.append(s)
        return out

    # the review's replay (scratchpad rwire_restart.py): latch (1, 150); the restarted host's views (1, 0..399), first Ready
    # at 180 -- the step latches at 180 exactly once; the wire-3 step never does
    replay = [(1, s, s >= 180) for s in range(400)]
    assert latch_run(BW.guest_line_step, (1, 150), replay) == [180]
    assert latch_run(BW.mutant_guest_line_no_forget, (1, 150), replay) == []
    # ...and never twice in one battle: a stall and resume of the same host battle (later seqs) stays latched
    assert latch_run(BW.guest_line_step, (-1, -1), [(5, s, True) for s in range(10, 300)]) == [10]
    # a step that forgets on ANY seq change, or one blind to the nonce, fails its own sequence (the instrument can fail)
    def forget_any(n, s, r, yn, ys):
        if yn >= 0 and n == yn and s != ys:
            yn, ys = -1, -1
        return BW.guest_line_step(n, s, r, yn, ys)

    def nonce_blind(n, s, r, yn, ys):
        v, yn2, ys2 = BW.guest_line_step(yn if yn >= 0 else n, s, r, yn, ys)
        return v, yn2, ys2

    assert (BW.guest_line_sequences(forget_any) or "").startswith("resume")
    assert (BW.guest_line_sequences(nonce_blind) or "").startswith("next")
    # the twin's sequence names ARE the engine's (the mutant row matches by name), and the engine's statements are the twin's
    raw = " ".join(net_lines("NetSyncBattle.cs", r"."))
    for name in (bad, BW.guest_line_sequences(forget_any), BW.guest_line_sequences(nonce_blind)):
        assert f'return "{name}";' in raw, name
    body = " ".join(_code(ln) for ln in _stack("NetSyncBattle.cs"))
    for frag in ("if (youNonce >= 0 && youSeq >= 0 && nonce == youNonce && !GuestLineSameBattle(nonce, seq, youNonce, youSeq))",
                 "if (GuestLineSameBattle(nonce, seq, youNonce, youSeq)) return GuestLineSame;",
                 "return ready ? GuestLineNew : GuestLineWait;",
                 "internal const Int32 GuestLineWait = 0;", "internal const Int32 GuestLineSame = 1;",
                 "internal const Int32 GuestLineNew = 2;",
                 "String seqBad = GuestLineSequences(GuestLineStep);",
                 'GuardMutantRow(GuestLineSequences(MutantGuestLineNoForget), "", "", ref rows, ref fail);',
                 "Int32 yn = 1, ys = 150, at = -1;", "for (Int32 s = 0; s <= 200 && at < 0; s++)",
                 "if (step(1, s, s >= 180, ref yn, ref ys) == GuestLineNew)",
                 "if (at != 180 || yn != 1 || ys != 180)", "for (Int32 s = 801; s <= 1100; s++)",
                 "if (step(3, s, true, ref yn, ref ys) != GuestLineSame || yn != 3 || ys != 800)",
                 "for (Int32 s = 1200; s <= 1215 && first < 0; s++)", "if (step(4, s, s >= 1210, ref yn, ref ys) == GuestLineNew)",
                 "if (first != 1210 || yn != 3 || ys != 800)", "internal static void GuestLineForget()"):
        assert frag in " ".join(body.split()), frag
    # the mutant is the step minus the forget (its body: the same test and the verdict, nothing else)
    mut = " ".join(" ".join(_code(ln) for ln in _method(net_lines_ordered("NetSyncBattle.cs", r"."),
                                                        "MutantGuestLineNoForget")).split())
    assert "youNonce = -1;" not in mut and "return ready ? GuestLineNew : GuestLineWait;" in mut
    # the CLIENT: a host epoch change (a relaunched host) forgets the guest's line latch beside the other battle-nonce dedups
    client = net_lines_ordered("NetSyncClient.cs", r".")
    reset = " ".join(_code(ln) for ln in _method(client, "ResetGuestDedupForEpoch"))
    assert "NetSyncBattle.GuestLineForget();" in reset and "_dioramaSeenNonce = -1;" in reset
    assert sum("NetSyncBattle.GuestLineForget();" in _code(ln) for ln in client) == 1


def test_the_field_core_rows_hold_on_the_twin():
    """(review s143 field-5) LeaderGuardSelfTest's field rows go through NetSyncClient.FieldGuardMaskCore (the dress sites'
    own core, FieldGuardMask's body), its named-mode and no-leader rows included -- evaluated on battlewire.field_guard_mask_core."""
    body = " ".join(_stack("NetSyncBattle.cs"))
    calls = re.findall(r'NetSyncClient\.FieldGuardMaskCore\("(\w*)", (0x[0-9A-F]+), (\w+), (\w+), out from, out to\)', body)
    assert sorted(calls) == sorted([("auto", "0x2", "f257", "0"), ("auto", "0x1", "solo", "0"), ("vivi", "0x2", "f257", "0"),
                                    ("auto", "0x2", "f257", "LeaderNone")]), calls
    f257, solo = [10, 0, 1, 3], [0, -1, -1, -1]
    assert BW.field_guard_mask_core("auto", 2, f257, 0) == (4, 1, 2)
    assert BW.field_guard_mask_core("auto", 1, solo, 0) == (0, 0, -1)
    assert BW.field_guard_mask_core("vivi", 2, f257, 0) == (2, -1, -1)
    assert BW.field_guard_mask_core("auto", 2, f257, -1) == (2, -1, -1)
    assert "GuardRow(named == 0x2 && nFrom == -1 && nTo == -1 && none == 0x2 && from == -1 && to == -1," in body
    client = " ".join(_code(ln) for ln in _stack("NetSyncClient.cs"))
    assert "Int32 eff = FieldGuardMaskCore(mode, mask, slotChar, leader, out from, out to);" in client
    assert "return NetSyncBattle.LeaderGuard(slotChar, mask, leader, out movedFrom, out movedTo);" in client


@pytest.mark.skipif(not (EXPORTS / "test2_74.txt").is_file() or not (MEMORIA / "Assembly-CSharp").is_dir(),
                    reason="no HW exports / Memoria clone on this machine (the census is install-side)")
def test_the_leader_census_regenerates_from_the_exports():
    import importlib.util
    spec = importlib.util.spec_from_file_location("_leader_census_under_test", CENSUS / "leader_census.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    frozen = json.loads((CENSUS / "leader_census.json").read_text(encoding="utf-8"))
    assert mod.build(EXPORTS, MEMORIA) == frozen


def test_the_line_text_is_the_twins():
    body = " ".join(_stack("NetSyncBattle.cs"))
    pb, cp = ("Blank", "Zidane", "Vivi", "Steiner"), ("Zidane", "Vivi", "Garnet", "Steiner")
    cases = [(True, pb, 0x4, 1), (True, cp, 0x2, -1), (True, cp, 0x6, 0), (True, ("Zidane", None, None, None), 0x0, 0),
             (True, ("Zidane", "Vivi", None, None), 0x4, -1), (False, pb, 0x4, 1), (False, pb, 0x0, -1), (False, None, 0x2, -1)]
    want = ["Partner: Vivi (not Zidane)", "Partner: Vivi", "Partner: Vivi, Garnet (not Zidane)",
            "Partner: watching (not Zidane)", "Partner: watching", "You: Vivi", "You: watching", "You: watching"]
    assert [guard_line_text(*c) for c in cases] == want
    for w in want:
        assert f'== "{w}"' in body, w


# ------------------------------------------------------------------------------------------------ the call-site law
_STRING = re.compile(r'"(?:[^"\\]|\\.)*"')


def _code(line: str) -> str:
    """A C# line without its string literals (emptied) and its // comment."""
    return _STRING.sub('""', line).split("//", 1)[0]


#: the raw GuestSlots reads NetSyncBattle.cs may keep (as source lines): the mirror and the header field themselves, the cheap
#: gate in front of IsGuestOwnedSlot's guarded test, the getter, the line's "is co-op battle on" test and log, the harness key
_RAW_ALLOWED = (
    "public static Int32 GuestSlots;",
    "public Int32 GuestSlots;",
    "if (!Enabled || GuestSlots == 0 || slot < 0 || slot >= 4 || (EffectiveGuestSlots & (1 << slot)) == 0)",
    "Int32 raw = GuestSlots & 0x0F;",
    "if (!_hostPhaseOpen || _guardLineNonce == _battleNonce || (GuestSlots & 0x0F) == 0)",
    '+ " (GuestSlots 0x" + (GuestSlots & 0x0F).ToString("X") + " -> 0x" + eff.ToString("X") + "; once per own battle)");',
    "public static Int32 HarnessGuardRaw { get { return GuestSlots & 0x0F; } }",
)


def _raw_reads(lines) -> list:
    """Code lines reading the bare GuestSlots (never EffectiveGuestSlots, never the guest's view.GuestSlots)."""
    out = []
    for ln in lines:
        code = _code(ln).replace("EffectiveGuestSlots", "").replace("view.GuestSlots", "")
        if re.search(r"(?<![\w.])GuestSlots\b", code):
            out.append(_code(ln).strip())
    return out


def test_every_battle_ownership_read_goes_through_the_guard():
    src = _stack("NetSyncBattle.cs")
    allowed = {_code(a).strip() for a in _RAW_ALLOWED}
    stray = [ln for ln in _raw_reads(src) if ln not in allowed]
    assert not stray, stray
    # the instrument can fail: the s141 file's own raw reads (the ownership lanes before the guard) are all stray here
    pre = net_lines("NetSyncBattle.cs", r".", [(msr.PATCHES / n).read_bytes() for n in msr.stack()
                                             if n not in msr.DEAD and n != PATCH])
    assert len([ln for ln in _raw_reads(pre) if ln not in allowed]) >= 10
    lines = [_code(ln) for ln in src]
    body = " ".join(lines)
    # the converted sites, each read through the guard
    for frag in ("bw.Write((Byte)(EffectiveGuestSlots & 0x0F));", "if (!HandbackOn || EffectiveGuestSlots == 0)",
                 "Int32 owned = EffectiveGuestSlots;", "return s >= 0 && s < 4 && (owned & (1 << s)) != 0 ? s : -1;",
                 "if ((owned & (1 << slot)) == 0)", "if (_rptRefusedCounted || EffectiveGuestSlots == 0 || !_hostPhaseOpen)",
                 "if (!Enabled || EffectiveGuestSlots == 0 || !_remoteMenuFlag ||"):
        assert frag in body, frag
    assert body.count("if (EffectiveGuestSlots != 0 && (_rosterForceTries > 0 || now - _lastRosterTick > RosterMs))") == 2
    assert body.count("GuardLineTick();") == 2                               # both pumps
    # the latch: organized players only, keyed on GuestSlots + the leader + the battle, per own battle
    for frag in ("(btlsys.btl_load_status & global::FF9.ff9btl.LOAD_INITCHR) == 0",
                 "if (!_guardLatched || raw != _guardRaw || leader != _guardLeaderUsed || battleNo != _guardBattleNo || sig != _guardSig)",
                 "Int32 sig = BattleSlotSig(btlsys);", "c = d != null && d.btl_id == (UInt16)(1 << i) && d.bi.player != 0 ? d.bi.slot_no : 0xFF;",
                 "Int32 battleNo = FF9StateSystem.Common.FF9.party.battle_no;", "GuardBattleEdge(true);", "GuardBattleEdge(false);",
                 "if (d != null && d.btl_id == (UInt16)(1 << i) && d.bi.player != 0)"):
        assert frag in body, frag


def test_the_field_sites_take_the_guard_and_the_client_rule_does_not():
    client = " ".join(_code(ln) for ln in _stack("NetSyncClient.cs"))
    assert client.count("FieldGuardMask(") == 3                              # HostDress, the selftest mirror, the definition
    assert "return NetSyncVisitor.ResolveDressRule(mode, FieldGuardMask(mode, _guestSlots, chars)," in client
    assert "stDress = NetSyncVisitor.GhostGuard(NetSyncVisitor.ResolveDressRule(stMode, FieldGuardMask(stMode, stMask, stChars)," \
        in client
    assert "dressModel = NetSyncVisitor.ResolveDress(_guestSlots, out dressRig);" in client     # the client's s138 site, as is
    assert "stDress = NetSyncVisitor.ResolveDressS138(stMode, stMask, ReadSlotChars(), out stRig);" in client   # the s138 lever
    assert "Int32 eff = FieldGuardMaskCore(mode, mask, slotChar, leader, out from, out to);" in client
    # NetSyncVisitor's rules and the `self auto` bench (NetSyncSelfDress) are untouched by s143: their hunks are comments
    for name in ("NetSyncVisitor.cs", "NetSyncSelfDress.cs"):
        sec = [s for p, s in msr.sections((msr.PATCHES / PATCH).read_bytes()) if p and p.endswith(name)]
        assert len(sec) == 1, name
        changed = [ln for ln in sec[0].decode("utf-8").splitlines() if ln[:1] in "+-" and not ln.startswith(("+++", "---"))]
        assert changed and all(ln[1:].strip().startswith("//") for ln in changed), (name, changed)
        assert any(ln.startswith("+") for ln in changed), name


# ------------------------------------------------------------------------------------------------ the protocol
def test_the_keys_are_additive_with_their_sentinels_and_the_lever_is_released():
    agent = net_lines("HarnessAgent.cs", r'outer\.Append\("\\"netsync\\":\{\\"enabled')
    assert len(agent) == 1
    lit = agent[0].replace('\\"', '"')
    assert ('"flee_gil":-1,"guard":{"leader":-1,"raw":0,"effective":0,"moved_from":-1,"moved_to":-1,"off":false,"line":null,'
            '"line_shown":false,"leader_model":-1,"chars":[-1,-1,-1,-1],"nonce":-1}},"peer":{') in lit
    assert '"ready_mask":-1,"guard":{"nonce":-1,"mask":-1,"line":null,"shown":false},"end":null' in lit
    # [ff9mapkit netsync s144] the END is s143's own (frozen): s144 appends `world` after `dress`, netsync's new last key
    assert _catch_line(_upto("s143")).endswith(
        '"polish":false},"guard":{"leader":-1,"raw":-1,"effective":-1,"moved_from":-1,"moved_to":-1}}}");')
    assert '"polish":false},"guard":{"leader":-1,"raw":-1,"effective":-1,"moved_from":-1,"moved_to":-1}},"world":{' in lit
    agent_all = " ".join(_stack("HarnessAgent.cs"))
    for key in ("leader", "raw", "effective", "moved_from", "moved_to", "off", "line", "line_shown", "leader_model", "nonce"):
        assert f'"{key}", Memoria.Netsync.NetSyncBattle.Harness' in agent_all, key
    assert 'AppendIntList(sb, "chars", Memoria.Netsync.NetSyncBattle.HarnessGuardChars());' in agent_all
    assert 'if (bnop == "leaderguard")' in agent_all
    assert net_lines("HarnessAgent.cs", r"public const Int32 ProtocolVersion = ") == ["public const Int32 ProtocolVersion = 5;"]
    battle = " ".join(_stack("NetSyncBattle.cs"))
    assert "BenchLeaderGuardOff = false;" in battle and "return !(benchOff && selfTestRole);" in battle
    versions = [ln for ln in _stack("NetSyncSocket.cs") if ln.startswith("public const Byte Version = ")]
    assert len(versions) == 1 and versions[0].startswith("public const Byte Version = 14;"), versions
    # s143 touches no wire file
    assert {p.rsplit("/", 1)[-1] for p, _s in msr.sections((msr.PATCHES / PATCH).read_bytes()) if p} == {
        "NetSyncBattle.cs", "NetSyncClient.cs", "NetSyncVisitor.cs", "NetSyncSelfDress.cs", "HarnessAgent.cs"}


def test_battlewires_tables_are_the_engines():
    """The twin's constants ARE the engine's: the census rows, the selftest's row counts (44 = 25 table rows + 19 `ref rows,
    ref fail);` calls), the leader map on every rig body and census model, and the three sentinel blocks the catch literal
    carries (the stand-in publishes the same at rest)."""
    assert BW.ZIDANE_VARIANT_MODELS == (532, 203, 432)
    assert BW.PC_VARIANT_MODELS == (658, 532, 203, 432, 202, 419) and BW.PC_VARIANT_CHARS == (3, 0, 0, 0, 2, 2)
    assert (BW.WORLD_LEADER_MODEL, BW.WORLD_DAGGER_MODEL) == (-3, -4)
    assert len(_rows()) == BW.LEADER_GUARD_TABLE_ROWS == 25
    calls = [ln for ln in net_lines("NetSyncBattle.cs", r"ref rows, ref fail\);", [(msr.PATCHES / PATCH).read_bytes()])]
    assert len(calls) == BW.LEADER_GUARD_REF_ROWS == 19, calls
    assert BW.LEADER_GUARD_SELFTEST_ROWS == BW.LEADER_GUARD_TABLE_ROWS + BW.LEADER_GUARD_REF_ROWS == 44
    body = " ".join(_stack("NetSyncBattle.cs"))
    for model, want in re.findall(r"LeaderCharForModel\((-?\w+)\) == (\w+)", body):
        m = int(model, 0)
        assert BW.leader_char_for_model(m) == (BW.LEADER_NONE if want == "LeaderNone" else int(want)), (model, want)
    assert [BW.leader_char_for_model(r[0]) for r in BW.RIGS] == [0, 1, 2, 3, 4, 5, 6, 7, -1, 8, 9, 10, 11]
    lit = net_lines("HarnessAgent.cs", r'outer\.Append\("\\"netsync\\":\{\\"enabled')[0].replace('\\"', '"')
    esc = lambda d: json.dumps(d, separators=(",", ":"))                 # noqa: E731
    assert f'"flee_gil":-1,"guard":{esc(BW.GUARD_HOST_SENTINELS)}}},"peer":{{' in lit
    assert f'"ready_mask":-1,"guard":{esc(BW.GUARD_PEER_SENTINELS)},"end":null' in lit
    # [ff9mapkit netsync s144] s143's line ENDS with dress's guard (frozen); the live one carries it right before s144's `world`
    assert _catch_line(_upto("s143")).endswith(f'"guard":{esc(BW.DRESS_GUARD_SENTINELS)}}}}}");')
    assert f'"guard":{esc(BW.DRESS_GUARD_SENTINELS)}}},"world":{esc(BW.WORLD_SENTINELS)},"guestlocal":{{' in lit   # [ff9mapkit netsync s156]
    # [ff9mapkit netsync s145] ...an s144 engine's `world` block is the three s144 blocks (frozen); s145's live one adds `dio`
    assert _catch_line(_upto("s144")).endswith(f'"guard":{esc(BW.DRESS_GUARD_SENTINELS)}}},"world":{esc(BW.WORLD_SENTINELS_S144)}}}");')
    assert BW.DRESS_SENTINELS["guard"] == BW.DRESS_GUARD_SENTINELS and list(BW.DRESS_SENTINELS)[-1] == "guard"


#: a GUEST-side read of the mask by ANY name -- bare, qualified (`NetSyncBattle.GuestSlots`), the battle getter (on a guest
#: it IS the guest's own ini mask: the guard is off outside an own battle) or the host's ownership tests -- once the
#: header's `view.GuestSlots` is taken out (review s143 wire-1: `_raw_reads` skipped every qualified name)
_GUEST_READ = re.compile(r"\b(?:NetSyncBattle\.)?(?:Effective)?GuestSlots\b|\bIsGuestOwnedSlot\b|\bHarnessGuestOwnedMask\b")
_GUEST_ALLOWED = {"public Int32 GuestSlots, Ready, Caps, Unmap, Nonce, Seq, Frames, Taken, Accepted, Refused, Bad;",
                  "GuestSlots = _feedGuestSlots,"}
#: NetSyncBattle.cs's GUEST-side methods (the guest's line, the digit panel, its control frame and menu depth, the panel's
#: drawing and menu) -- their bodies are scanned like the guest's own files
GUEST_METHODS = ("GuestLineTick", "GuestLineStep", "GuestLineLate", "FirstReadyGuestSlot", "GuestAssistTick", "GuestControl", "GuestMenuByte",
                 "DrawGUI", "AppendMenu")


def _guest_reads(lines) -> list:
    out = []
    for ln in lines:
        code = _code(ln).replace("view.GuestSlots", "")
        if _GUEST_READ.search(code) and _code(ln).strip() not in _GUEST_ALLOWED:
            out.append(_code(ln).strip())
    return out


def _method(lines: list, name: str) -> list:
    """One method's lines (signature through its closing brace) out of a FILE-ordered line list."""
    sig = re.compile(r"\b(?:private|internal|public)\b[^;=]*\b" + name + r"\(")
    start = next((i for i, ln in enumerate(lines) if sig.search(ln) and not ln.rstrip().endswith(";")), None)
    assert start is not None, name
    depth, seen, out = 0, False, []
    for ln in lines[start:]:
        out.append(ln)
        code = _code(ln)
        depth += code.count("{") - code.count("}")
        seen = seen or "{" in code
        if seen and depth == 0:
            break
    return out


def test_the_guest_side_reads_only_the_hosts_header():
    """THE GUEST NEEDS NO CHANGE: every guest-side ownership decision (the digit panel, the stock menu's mirror, the diorama,
    the replay, the end lane, the guest's line) reads the HOST's header byte (`view.GuestSlots`, the leader guard's mask),
    never its own ini's GuestSlots by ANY name -- the only reads there are the bench feed's fabricated offer
    (`_feedGuestSlots`) and its struct. The scan covers the guest's own files and NetSyncBattle.cs's guest methods, and
    the instrument can fail: a qualified read injected into a copy turns it red."""
    for name in ("NetSyncBattle.StockMenu.cs", "NetSyncDiorama.cs", "NetSyncDiorama.Replay.cs", "NetSyncEnd.cs"):
        stray = _guest_reads(_stack(name))
        assert not stray, (name, stray)
    ordered = net_lines_ordered("NetSyncBattle.cs", r".")
    for m in GUEST_METHODS:
        body = _method(ordered, m)
        assert len(body) > 3, m
        assert not _guest_reads(body), (m, _guest_reads(body))
    # the instrument can fail: every way a guest file could read the mask
    dio = _stack("NetSyncDiorama.cs")
    for bad in ("if ((NetSyncBattle.GuestSlots & 1) != 0)", "Int32 m = Memoria.Netsync.NetSyncBattle.EffectiveGuestSlots;",
                "if (NetSyncBattle.IsGuestOwnedSlot(L)) continue;", "Int32 h = NetSyncBattle.HarnessGuestOwnedMask;"):
        assert _guest_reads(dio + [bad]) == [bad], bad
    assert _guest_reads(_method(ordered, "GuestControl") + ["if ((GuestSlots & 2) != 0)"])
    assert _guest_reads(["if ((view.GuestSlots & 2) != 0)"]) == []      # the header itself is the guest's to read
    menu = " ".join(_code(ln) for ln in _stack("NetSyncBattle.StockMenu.cs"))
    assert menu.count("(view.GuestSlots & (1 << u.Index))") == 2     # AssistSlot and the ready mirror: the header's mask
    battle = " ".join(_code(ln) for ln in _stack("NetSyncBattle.cs"))
    assert "if (u.IsPlayer && u.Ready && u.Alive && (view.GuestSlots & (1 << u.Index)) != 0)" in battle   # the digit panel


#: the qualified reads of the mask OUTSIDE NetSyncBattle.cs the stack may keep: the harness's raw-by-contract `guest_slots`
#: key (and the bench feed's struct field); every other one is a host ownership read that skipped the guard
_QUALIFIED_ALLOWED = {'Num(sb, "", Memoria.Netsync.NetSyncBattle.GuestSlots); sb.Append("");'}
_QUALIFIED = re.compile(r"\bNetSyncBattle\.(?:Effective)?GuestSlots\b(?!\s*=[^=])")


def _stack_files() -> list:
    files = set()
    for n in msr.stack():
        if n in msr.DEAD:
            continue
        for p, _s in msr.sections((msr.PATCHES / n).read_bytes()):
            if p and p.endswith(".cs"):
                files.add(p.replace("\\", "/").rsplit("/", 1)[-1])
    return sorted(files - {"NetSyncBattle.cs"})


def _qualified_reads(lines) -> list:
    return [_code(ln).strip() for ln in lines if _QUALIFIED.search(_code(ln)) and _code(ln).strip() not in _QUALIFIED_ALLOWED]


def test_no_other_file_reads_the_mask_qualified():
    """(review s143 own-4) THE CALL-SITE LAW across the stack: no file but NetSyncBattle.cs reads `NetSyncBattle.GuestSlots`
    (or the getter) -- the BattleHUD partials, NetSyncClient, NetSyncSelfDress, the diorama and end files, the harness -- save
    the harness's raw `guest_slots` key; NetSyncClient only WRITES it (the ini, the harness override). A qualified read
    injected into a copy of a patched BattleHUD file turns it red."""
    files = _stack_files()
    assert {"BattleHUD.cs", "BattleHUD.Unity.cs", "NetSyncClient.cs", "NetSyncSelfDress.cs", "HarnessAgent.cs",
            "NetSyncDiorama.cs", "NetSyncEnd.cs"} <= set(files)
    stray = {f: _qualified_reads(_stack(f)) for f in files}
    assert not {f: s for f, s in stray.items() if s}, stray
    agent = [_code(ln).strip() for ln in _stack("HarnessAgent.cs")]
    assert sum(1 for ln in agent if ln in _QUALIFIED_ALLOWED) == 1
    writes = [_code(ln).strip() for ln in _stack("NetSyncClient.cs") if "NetSyncBattle.GuestSlots" in _code(ln)]
    assert writes and all(re.match(r"NetSyncBattle\.GuestSlots = [^=]", w) for w in writes), writes
    hud = _stack("BattleHUD.Unity.cs")
    bad = "if ((Memoria.Netsync.NetSyncBattle.GuestSlots & (1 << playerId)) != 0)"
    assert _qualified_reads(hud + [bad]) == [bad]
    assert _qualified_reads(["Memoria.Netsync.NetSyncBattle.EffectiveGuestSlots != 0"])
    assert not _qualified_reads(["NetSyncBattle.GuestSlots = mask;"])
