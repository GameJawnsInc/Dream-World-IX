"""[ff9mapkit netsync s144] WORLD-MAP CO-OP, WAIT THEN REJOIN -- the offline twins of the s144 patch's pure steps, pinned to the live
patch stack (memoria-patches/, read through tests/_patchstack -- no clone, no install). studies/world-coop/S144-DESIGN.md.

On the world map the HOST drives. A following guest there is FROZEN (NetSyncField's world freeze), REJOINS the host's next field
through the world's own field entry (NetSyncClient's world rejoin, behind the shared world-transition latch), and reads THE WAITING
LINE (section 7's b6 HfWorld / b7 HfTitle, the status overlay). Pinned here:

  * THE CAPTURE: the twelve files the patch touches (no wire file), every hunk tagged, the wire v14 and the harness protocol 5.
  * THE THREE SELFTESTS, row by row: every `FreezeRow` / `RejoinRow` / `OvlRow` the engine's proof block runs (parsed off the
    patch, in file order, by NAME) has a twin check here that holds on battlewire's twins -- an engine row without a twin, or a
    twin without an engine row, is red -- and each selftest's row count is the proof line's (42 / 70 / 50).
  * THE TWINS' CONSTANTS are the engine's (the bits, the clocks, the freeze table, the overlay states and names, the words).
  * EVERY CHECK CAN FAIL: each twin's mutants (the engine's own, plus the ones its offline harness ran) miss its table.
  * SECTION 7's new bits reach no old reader: the parser copies the byte unvalidated, the guest's reads mask single bits (a
    SOURCE PIN over every live read of the host's flags -- an injected whole-byte compare reads red), the harness's readers
    (channel, the stand-in) name them, and the host ORs them in their own try.
  * THE CALL SITES a law lives at (a law in a docstring is a wish): the frozen key mask returns exactly
    ControlOnScriptKeys(keys, true) with its counter in the same block, the release's own branch after it, the world rule
    ahead of RedirectGuestFieldJump's fldMapNo read, the world follow latch ahead of FollowHostTick's guard, the field
    follow cancelled at the guest's own WMAPJUMP, the arm's seed first in StartWorldFollowWarp; [review 2] the world skip
    consuming its press and running ahead of s38's gate, the redirect's hold term, the hold riding a landing and the field
    follow (and its intent, and F11 on a field) answering to it.
"""
import json
import pathlib
import re
import sys

import pytest

from ._patchstack import msr, net_lines, net_lines_ordered

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from harness import HarnessError, Session                              # noqa: E402
from harness import battlewire as BW                                   # noqa: E402
from harness import channel as CH                                      # noqa: E402
from harness import fakegame as FG                                     # noqa: E402
from harness.fakegame import FakeGame                                  # noqa: E402

PATCH = "s144-netsync-world-wait.patch"
TAG = "[ff9mapkit netsync s144]"
FILES = ("NetSyncDialog.cs", "NetSyncClient.cs", "NetSyncField.cs", "NetSyncBattle.cs", "HarnessAgent.cs", "Ff9mkDebugMenu.cs",
         "UIKeyTrigger.cs", "EventEngine.DoEventCode.cs", "EventCollision.cs", "ff9.cs", "WorldHUD.cs", "WMScriptDirector.cs")


def _patch() -> bytes:
    return (msr.PATCHES / PATCH).read_bytes()


def _new_side(file_name: str) -> list:
    """The patch's NEW-side lines for ``file_name``: (hunk, kind, stripped text)."""
    out, hunk = [], 0
    for path, sec in msr.sections(_patch()):
        if not path or path.rsplit("/", 1)[-1] != file_name:
            continue
        for ln in sec.decode("utf-8", "replace").splitlines():
            if ln.startswith("@@"):
                hunk += 1
            elif ln[:1] in (" ", "+") and not ln.startswith("+++"):
                out.append((hunk, ln[:1], ln[1:].strip()))
    return out


def _block(file_name: str, start: str, stop: str = "catch (Exception err)") -> list:
    """One block of the patch's new side, WHOLE in one hunk (the capture law), from the line starting ``start`` up to ``stop``."""
    new = _new_side(file_name)
    i = next(k for k, (_h, _kind, t) in enumerate(new) if t.startswith(start))
    j = next(k for k in range(i, len(new)) if new[k][2] == stop)
    assert all(h == new[i][0] for h, _k, _t in new[i:j]), (file_name, start, "split across hunks")
    return [t for _h, _k, t in new[i:j]]


def _code(line: str) -> str:
    """A C# line without its trailing // comment (string literals kept)."""
    out, quoted, i = [], False, 0
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


def _row_names(file_name: str, start: str, helper: str) -> list:
    """The selftest's rows, in file order: every ``<helper>(<expr>, "<name>", ref a, ref b)`` statement's name."""
    code = " ".join(_code(t) for t in _block(file_name, start))
    pat = re.compile(re.escape(helper) + r'\(((?:[^"]|"(?:[^"\\]|\\.)*")*?), "((?:[^"\\]|\\.)*)", ref \w+, ref \w+\);')
    return [m.group(2).replace('\\"', '"') for m in pat.finditer(code)]


def _cs_int(file_name: str, name: str) -> int:
    """The value of a C# integer constant the patch adds (``... name = <n>``, hex or decimal, a `u` suffix allowed)."""
    for line in net_lines(file_name, rf"\b{re.escape(name)} = ", [_patch()]):
        m = re.search(rf"\b{re.escape(name)} = (0x[0-9A-Fa-f]+|-?\d+)u?\b", line)
        if m:
            return int(m.group(1), 0)
    raise AssertionError(f"{name} not in the s144 patch's {file_name}")


# ------------------------------------------------------------------------------------------------ the capture
def test_the_patch_touches_its_twelve_files_and_no_wire_file():
    touched = [p.rsplit("/", 1)[-1] for p, _s in msr.sections(_patch()) if p]
    assert tuple(touched) == FILES, touched
    assert not {"NetSyncSocket.cs", "NetSyncRelay.cs", "NetSyncState.cs", "NetSyncParty.cs"} & set(touched)
    assert PATCH in msr.stack() and msr.stack().index(PATCH) == msr.stack().index("s143-netsync-guest-never-leader.patch") + 1
    # the replay's default file set diags every file s144 touches (ff9.cs, WorldHUD.cs, WMScriptDirector.cs, NetSyncDialog.cs
    # joined it with s144)
    defaults = {f.rsplit("/", 1)[-1] for f in msr.DEFAULT_FILES}
    assert set(FILES) <= defaults, set(FILES) - defaults


def test_every_hunk_carries_the_s144_tag_and_stays_ascii():
    text = _patch().decode("utf-8").replace("\r\n", "\n")
    hunks, cur = [], None
    for ln in text.split("\n"):
        if ln.startswith("@@"):
            cur = []
            hunks.append(cur)
        elif cur is not None and ln.startswith("+") and not ln.startswith("+++"):
            cur.append(ln)
    assert len(hunks) >= 40
    assert all(any(TAG in ln for ln in h) for h in hunks), [h[:1] for h in hunks if not any(TAG in ln for ln in h)]
    assert all(ord(c) < 128 for h in hunks for ln in h for c in ln)


def test_the_wire_stays_v14_and_the_protocol_5():
    versions = [ln for ln in net_lines("NetSyncSocket.cs", r".") if ln.startswith("public const Byte Version = ")]
    assert len(versions) == 1 and versions[0].startswith("public const Byte Version = 14;"), versions
    assert net_lines("HarnessAgent.cs", r"public const Int32 ProtocolVersion = ") == ["public const Int32 ProtocolVersion = 5;"]
    # no new [Netsync] ini knob: the patch reads no ini setting at all
    assert not net_lines("NetSyncClient.cs", r'GetSetting\("Netsync"', [_patch()])


# ------------------------------------------------------------------------------------------------ section 7's b6 / b7
def test_b6_b7_are_the_flags_bytes_free_bits_and_no_old_reader_drops_them():
    assert (_cs_int("NetSyncDialog.cs", "HfWorld"), _cs_int("NetSyncDialog.cs", "HfTitle")) == (BW.HF_WORLD, BW.HF_TITLE) == \
        (0x40, 0x80)
    old = {n: int(v, 0) for ln in net_lines("NetSyncDialog.cs", r"internal const Byte Hf(Scene|Control|Line|OnField|Menu|Battle) = ")
           for n, v in [re.search(r"(Hf\w+) = (0x[0-9A-Fa-f]+)", ln).groups()]}
    assert len(old) == 6 and sum(old.values()) == BW.HF_OLD_SIX and not (BW.HF_WORLD | BW.HF_TITLE) & BW.HF_OLD_SIX
    # the parser copies the flags byte unvalidated (an older guest keeps it, its single-bit reads ignore b6 / b7)
    assert "v.Flags = b[5];" in net_lines("NetSyncDialog.cs", r"v\.Flags = ")
    # the host ORs them in their OWN try (never costs b1 / b4 / b5), from the strict onWorld and the Title scene
    new = [(k, _code(t)) for _h, k, t in _new_side("NetSyncClient.cs")]
    i = next(n for n, (_k, t) in enumerate(new) if t.startswith("f |= HostWhereBits("))
    assert new[i][1] == "f |= HostWhereBits(IsOnWorldNow(PersistenSingleton<EventEngine>.Instance),"
    assert new[i + 1][1] == 'String.Equals(PersistenSingleton<SceneDirector>.Instance.CurrentScene, "Title"));'
    assert [t for _k, t in new[i - 4:i]] == ["f |= NetSyncDialog.HfMenu;", "}", "catch { }", "try"] or         [t for _k, t in new[i - 5:i]] == ["f |= NetSyncDialog.HfMenu;", "}", "catch { }", "try", "{"], new[i - 5:i]
    assert [t for _k, t in new[i + 2:i + 5]] == ["}", "catch { }", "return f;"], new[i + 2:i + 5]
    # the harness's readers mirror them by name; the stand-in's twin bits are the engine's
    assert CH.State.HOST_FLAG_BITS["world"] == BW.HF_WORLD and CH.State.HOST_FLAG_BITS["title"] == BW.HF_TITLE
    assert (FG.HF_WORLD, FG.HF_TITLE) == (BW.HF_WORLD, BW.HF_TITLE)
    assert CH.State({"frame": 1, "netsync": {"host_flags": 0xD8}}).dialogue_host_flag_set == {"on_field", "menu", "world",
                                                                                               "title"}


# ------------------------------------------------------------------------------------------------ the twins' constants
def test_the_twins_constants_are_the_engines():
    assert _cs_int("NetSyncClient.cs", "WaitAwayMs") == BW.WAIT_AWAY_MS == 3000
    assert _cs_int("NetSyncClient.cs", "WorldHoldMs") == BW.WORLD_HOLD_MS == 15000
    assert _cs_int("NetSyncClient.cs", "WorldArmTimeoutMs") == BW.WORLD_ARM_TIMEOUT_MS == 5000
    assert _cs_int("NetSyncField.cs", "WorldFreezeTable") == BW.WORLD_FREEZE_TABLE == BW.world_freeze_rule_mask()
    for name, value in (("OvlHostWorld", BW.OVL_HOST_WORLD), ("OvlRejoining", BW.OVL_REJOINING), ("OvlWorldHold", BW.OVL_WORLD_HOLD),
                        ("OvlHostTitle", BW.OVL_HOST_TITLE), ("OvlHostAway", BW.OVL_HOST_AWAY), ("OvlKeep", BW.OVL_KEEP)):
        assert _cs_int("NetSyncClient.cs", name) == value, name
    # OverlayName's vocabulary (the whole live stack) is battlewire's, s144's five names at its end
    names = [m.group(1) for ln in net_lines("NetSyncClient.cs", r'case Ovl\w+: return "') for m in
             [re.match(r'case Ovl\w+: return "(\w+)";', ln)] if m]
    assert set(names) == set(BW.OVERLAY_NAMES) and BW.OVERLAY_NAMES[-5:] == BW.OVERLAY_NAMES_S144
    # WaitLineName's vocabulary, and the words (decision 7's sentences, verbatim)
    body = " ".join(_block("NetSyncClient.cs", "internal static String WaitLineName(", "return null;"))
    assert re.findall(r'if \(state == Ovl(\w+)\) return "(\w+)";', body) == [
        ("HostWorld", "host_world"), ("Rejoining", "rejoin"), ("WorldHold", "hold"), ("HostTitle", "host_title"), ("HostAway", "away")]
    assert [BW.wait_line_name(s) for s in (9, 10, 11, 12, 13)] == ["host_world", "rejoin", "hold", "host_title", "away"]
    words = " ".join(_block("NetSyncClient.cs", "internal static String WaitLineText(", "default:"))
    for text in (BW.WAIT_TEXT_HOST_WORLD, BW.WAIT_TEXT_HOST_TITLE, BW.WAIT_TEXT_HOST_AWAY):
        assert json.dumps(text) in words, text
    assert '"FF9 co-op: Rejoining your partner at field " + detail + "...";' in words
    assert "Your partner is on the world map." in BW.WAIT_TEXT_HOST_WORLD and "You'll rejoin them at their next stop." in \
        BW.WAIT_TEXT_HOST_WORLD
    # the sentinels the catch literal carries are battlewire's
    lit = net_lines("HarnessAgent.cs", r'outer\.Append\("\\"netsync\\":\{\\"enabled')[0].replace('\\"', '"')
    esc = lambda d: json.dumps(d, separators=(",", ":"))                 # noqa: E731
    assert f'"ghost_held":false,"overlay_text":null,"follow":{esc(BW.SESSION_FOLLOW_SENTINELS)}}},"menu_refusal"' in lit
    assert lit.endswith(f'"world":{esc(BW.WORLD_SENTINELS)}}}");')
    # [ff9mapkit netsync s145] the s144 patch's own line ends with ITS three blocks (frozen); the live block adds s145's `dio`
    upto = [(msr.PATCHES / n).read_bytes() for n in msr.stack()[:msr.stack().index(PATCH) + 1] if n not in msr.DEAD]
    old = net_lines("HarnessAgent.cs", r'outer\.Append\("\\"netsync\\":\{\\"enabled', upto)[0].replace('\\"', '"')
    assert old.endswith(f'"world":{esc(BW.WORLD_SENTINELS_S144)}}}");') and list(BW.WORLD_SENTINELS)[:3] == list(BW.WORLD_SENTINELS_S144)


# ------------------------------------------------------------------------------------------------ THE FREEZE's rows
E = BW
FREEZE_ROWS = {
    "the rule's 32 rows are 0x2A (rows 1, 3, 5 freeze)": lambda: E.world_freeze_rule_mask() == E.WORLD_FREEZE_TABLE,
    "a live followed or mirroring guest freezes": lambda: E.world_freeze_rule(True, False, False, False, False),
    "vanilla, a host or a free roamer never freezes": lambda: not E.world_freeze_rule(False, False, False, False, False),
    "...not even with the lever stranded": lambda: not E.world_freeze_rule(False, True, True, False, False),
    "the selftest role under bench 1 freezes (the bench)": lambda: E.world_freeze_rule(True, False, True, False, False),
    "`bench worldfreeze off` lifts it on the selftest role (the lever)": lambda: not E.world_freeze_rule(True, True, True, False, False),
    "the lever on a non-selftest role cannot lift it": lambda: E.world_freeze_rule(True, True, False, False, False),
    "the ~ menu's release lifts it (the release latch)": lambda: not E.world_freeze_rule(True, False, False, True, False),
    "...on the selftest role too": lambda: not E.world_freeze_rule(True, False, True, True, False),
    "the bee scene never freezes": lambda: not E.world_freeze_rule(True, False, False, False, True),
    "mutant: no bee-scene term": lambda: E.world_freeze_rule_mask(lambda s, b, t, r, e: s and not r and not (b and t)) != E.WORLD_FREEZE_TABLE,
    "mutant: the lever lifts on any role": lambda: E.world_freeze_rule_mask(lambda s, b, t, r, e: s and not e and not r and not b) != E.WORLD_FREEZE_TABLE,
    "mutant: no release latch": lambda: E.world_freeze_rule_mask(lambda s, b, t, r, e: s and not e and not (b and t)) != E.WORLD_FREEZE_TABLE,
    "mutant: no spectator term": lambda: E.world_freeze_rule_mask(lambda s, b, t, r, e: not e and not r and not (b and t)) != E.WORLD_FREEZE_TABLE,
    "mutant: no lever": lambda: E.world_freeze_rule_mask(lambda s, b, t, r, e: s and not e and not r) != E.WORLD_FREEZE_TABLE,
    "why: a live followed session names `live`": lambda: E.world_freeze_why_term(True, True, True) == "live",
    "why: the grace (the peer lost, the mirror armed) names `mirroring`": lambda: E.world_freeze_why_term(False, True, True) == "mirroring",
    "why: the bench names `bench`": lambda: E.world_freeze_why_term(False, False, True) == "bench",
    "why: none holds, null": lambda: E.world_freeze_why_term(False, False, False) is None,
    "the lift reason is null on exactly the frozen rows": lambda: all(
        (E.world_freeze_lift_why(*a) is None) == E.world_freeze_rule(*a)
        for a in [(bool(i & 1), bool(i & 2), bool(i & 4), bool(i & 8), bool(i & 16)) for i in range(32)]),
    "edge: a world load's first frozen dispatch": lambda: E.world_freeze_edge_step(False, 0, 120),
    "edge: a held tick is none": lambda: not E.world_freeze_edge_step(True, 120, 121),
    "edge: a new world load while held (the counter went back)": lambda: E.world_freeze_edge_step(True, 900, 130),
    "edge: a re-freeze after a lift (the lever, a peer back)": lambda: E.world_freeze_edge_step(False, 500, 501),
    "keys: frozen, Cancel (dismount / land) is masked": lambda: E.control_on_script_keys(E.EV_CANCEL | E.EV_CIRCLE, True) == 0,
    "keys: unfrozen, Cancel passes (s143's mask: the gap the freeze closes)": lambda: E.control_on_script_keys(E.EV_CANCEL, False) == E.EV_CANCEL,
    "keys: frozen, Triangle (the deck) is masked": lambda: E.control_on_script_keys(E.EV_MENU | E.EV_TRIANGLE, True) == 0,
    "keys: unfrozen, Menu passes": lambda: E.control_on_script_keys(E.EV_MENU, False) == E.EV_MENU,
    "keys: Confirm / Special / Select masked either way (F1)": lambda: (
        E.control_on_script_keys(E.EV_CONFIRM | E.EV_SPECIAL | E.EV_SELECT, True) == 0
        and E.control_on_script_keys(E.EV_CONFIRM | E.EV_SPECIAL | E.EV_SELECT, False) == 0),
    "keys: frozen, directions, Navi, the triggers, the bumpers and Start stay the guest's": lambda: (
        lambda own: E.control_on_script_keys(own, True) == own)(
        E.EV_UP | E.EV_LEFT | E.EV_NAVI_CONTROL | E.EV_RIGHT_TRIGGER | E.EV_L1 | E.EV_R1 | E.EV_START),
    "keys: released, Confirm passes (a location's entry) and Cancel too": lambda: (
        E.released_world_script_keys(E.EV_CONFIRM | E.EV_CANCEL) == E.EV_CONFIRM | E.EV_CANCEL),
    "keys: released, Special / Select stay F1's (no pickup, no ATE menu)": lambda: E.released_world_script_keys(E.EV_SPECIAL | E.EV_SELECT) == 0,
    "mutant: a release keeping F1's mask takes Confirm (walking only: no way into the field load that ends it)": lambda: (
        E.control_on_script_keys(E.EV_CONFIRM, False) == 0 and E.released_world_script_keys(E.EV_CONFIRM) != 0),
    "skip: the skipped world battle's press is consumed -- the dispatcher's next poll (the location's Confirm) reads none": lambda: (
        (E.released_world_script_keys(E.world_skip_key_on(E.EV_CONFIRM | E.EV_CANCEL)) & (E.EV_CONFIRM | E.EV_CANCEL)) == 0),
    "skip: every host-owned edge goes, the guest's own keys stay": lambda: (
        lambda own: E.world_skip_key_on(own) == own and E.world_skip_key_on(E.HOST_OWNED_KEYS) == 0)(
        E.EV_UP | E.EV_LEFT | E.EV_NAVI_CONTROL | E.EV_RIGHT_TRIGGER | E.EV_L1 | E.EV_R1 | E.EV_START),
    "mutant: a skip that consumes nothing hands the press to the location poll (area 52's default: control off, no field)": lambda: (
        (E.released_world_script_keys(E.EV_CONFIRM) & E.EV_CONFIRM) != 0
        and (E.released_world_script_keys(E.world_skip_key_on(E.EV_CONFIRM)) & E.EV_CONFIRM) == 0),
    "release: a frozen live guest on the world map may": lambda: E.world_freeze_release_refusal(True, True, True, False) is None,
    "release: a live followed session only (the grace, the bench)": lambda: E.world_freeze_release_refusal(False, True, True, False) is not None,
    "release: the world map only": lambda: E.world_freeze_release_refusal(True, False, True, False) is not None,
    "release: nothing holds, nothing to release": lambda: E.world_freeze_release_refusal(True, True, False, False) is not None,
    "release: already released": lambda: E.world_freeze_release_refusal(True, True, False, True) is not None,
    "lever: the selftest role only": lambda: E.world_freeze_bench_refusal(True) is None and E.world_freeze_bench_refusal(False) is not None,
}


def _hold_any_zero(h, ms, host, w, dst):
    """WorldRejoinSelfTest's `anyZero` mutant: the hold ends on any frame the host is not on the held field."""
    return (E.HOLD_NONE if h < 0 else E.HOLD_EXPIRED if ms >= E.WORLD_HOLD_MS
            else E.HOLD_HOST_LEFT if host != h or w else E.HOLD_HOLDS if dst == h else E.HOLD_OTHER)


def _redir(*a):
    return E.world_redirect_step(*a)


def _chases_back(rule) -> bool:
    """ChasesBackInto2211's twin: the guest landed on 2856 (its world script's Field() passed under the hold on 2211), the host
    still on 2211 three seconds in -- under ``rule`` (the carry), does the field follow there chase straight back into 2211?"""
    return E.world_hold_step(2211 if rule(2211, 2856) else -1, 3000, 2211, False, 2211) != E.HOLD_HOLDS


def _entrance_state(entrance: int) -> bytes:
    """EntranceState's twin: a host state payload whose story section carries FieldEntrance ``entrance`` (bytes 2..3, LE)."""
    story = bytearray(2048)
    story[2], story[3] = entrance & 0xFF, (entrance >> 8) & 0xFF
    return E.append_section(b"", E.SECTION_STORY, bytes(story))


_ON_WORLD_ROWS = ((1, "WorldMap"), (2, "BattleMap"), (3, "WorldMap"), (3, "FieldMap"), (3, "BattleMapDebug"), (3, "Title"))


def _on_world_mask(rule) -> int:
    return sum(1 << k for k, (g, s) in enumerate(_ON_WORLD_ROWS) if rule(g, s))


def _arm(rule, **force):
    """WorldArmArms over the twin with one gate FORCED (a mutant)."""
    keys = ("h", "m", "f", "r", "s", "g", "e", "c", "fm", "hd", "l")

    def wrapped(*a):
        d = dict(zip(keys, a))
        d.update(force)
        return rule(*[d[k] for k in keys])
    return E.world_arm_arms(wrapped)


def _latch(rule, **force):
    keys = ("w", "m", "a", "x", "f", "b", "r", "j")

    def wrapped(*a):
        d = dict(zip(keys, a))
        d.update(force)
        return rule(*[d[k] for k in keys])
    return E.world_latch_frees(wrapped)


REJOIN_ROWS = {
    "onWorld: only gMode 3 on the WorldMap scene": lambda: _on_world_mask(E.on_world_rule) == 0x4,
    "onWorld: gMode 3 on the FieldMap scene (the world -> field load) is not": lambda: not E.on_world_rule(3, "FieldMap"),
    "onWorld: nor a world-booted diorama (gMode stays 3)": lambda: not E.on_world_rule(3, "BattleMapDebug"),
    "mutant: gMode alone reads the field load and the diorama as the world map": lambda: _on_world_mask(lambda g, s: g == 3) != 0x4,
    "mutant: the scene alone reads the field -> world load as the world map": lambda: _on_world_mask(lambda g, s: s == "WorldMap") != 0x4,
    "follow field: none on the world map (fldMapNo is the field the guest LEFT)": lambda: E.follow_field_for(True, 300) == -1,
    "follow field: fldMapNo off the world map (the field follow as before)": lambda: E.follow_field_for(False, 300) == 300 and E.follow_field_for(False, -1) == -1,
    "mutant: s143's fldMapNo reads the host on the departed field as arrived": lambda: E.follow_field_for(True, 300) != 300 and (lambda w, f: f)(True, 300) == 300,
    "arm: fires on exactly 1 of 2048 gate combinations, all eleven clear": lambda: E.world_arm_arms() == (1, 2047),
    "arm: a control-off world script holds it (it could overwrite nextMapNo)": lambda: E.world_arm_refusal(True, 3, False, False, True, True, False, False, False, False, None) is not None,
    "arm: no fresh host snapshot holds it (never seed 9999)": lambda: E.world_arm_refusal(True, 3, False, False, False, True, False, True, False, False, None) is not None,
    "arm: an event world map holds it": lambda: E.world_arm_refusal(True, 3, False, False, True, True, True, True, False, False, None) is not None,
    "arm: mode 1 (the world's shutdown ran) holds it": lambda: E.world_arm_refusal(True, 1, False, False, True, True, False, True, False, False, None) is not None,
    "arm: the full map open holds it (w_naviMode 2: stock never leaves the world from it)": lambda: E.world_arm_refusal(True, 3, False, False, True, True, False, True, True, False, None) is not None,
    "mutant: no control gate arms on 2 combinations": lambda: _arm(E.world_arm_refusal, c=True)[0] == 2,
    "mutant: no snapshot gate arms on 2": lambda: _arm(E.world_arm_refusal, s=True)[0] == 2,
    "mutant: no hold arms on 2": lambda: _arm(E.world_arm_refusal, hd=False)[0] == 2,
    "mutant: no latch arms on 2": lambda: _arm(E.world_arm_refusal, l=None)[0] == 2,
    "mutant: no full-map gate arms on 2": lambda: _arm(E.world_arm_refusal, fm=False)[0] == 2,
    "hold: none latched, none holds": lambda: E.world_hold_step(-1, 0, 300, False, 300) == E.HOLD_NONE,
    "hold: 3 s after my own exit from 300, the host still there: the rejoin into 300 waits": lambda: E.world_hold_step(300, 3000, 300, False, 300) == E.HOLD_HOLDS,
    "hold: ...up to the cap": lambda: E.world_hold_step(300, E.WORLD_HOLD_MS - 1, 300, False, 300) == E.HOLD_HOLDS,
    "hold: at 15 s it ends (a guest that walked out is pulled back)": lambda: E.world_hold_step(300, E.WORLD_HOLD_MS, 300, False, 300) == E.HOLD_EXPIRED,
    "hold: the host on another field ends it": lambda: E.world_hold_step(300, 3000, 301, False, 301) == E.HOLD_HOST_LEFT,
    "hold: the host on the world map (b6) ends it": lambda: E.world_hold_step(300, 3000, 0, True, 300) == E.HOLD_HOST_LEFT,
    "hold: field 0 without b6 (a battle, a menu, a fade on 300) keeps it": lambda: E.world_hold_step(300, 3000, 0, False, 300) == E.HOLD_HOLDS,
    "hold: the relay's 65535 is no field: kept": lambda: E.world_hold_step(300, 3000, 65535, False, 300) == E.HOLD_HOLDS,
    "hold: an intent to another field passes (the host leaving 300)": lambda: E.world_hold_step(300, 3000, 300, False, 302) == E.HOLD_OTHER,
    "mutant: ending the hold on any field-0 frame drops it in a battle on 300": lambda: _hold_any_zero(300, 3000, 0, False, 300) != E.world_hold_step(300, 3000, 0, False, 300),
    "redirect: Field(the host's field) passes": lambda: _redir(300, 300, 300, True, True, True) == (300, E.REDIR_PASS_HOST),
    "redirect: a donor id whose fork the host stands on passes (the shutdown redirects it)": lambda: _redir(250, 6250, 6250, True, True, True) == (250, E.REDIR_PASS_HOST),
    "redirect: the host on another registered field: redirected there (an instant rejoin)": lambda: _redir(2856, 2856, 300, True, True, True) == (300, E.REDIR_TO_HOST),
    "redirect: the host off-field (the world map, a battle, the title): passes": lambda: _redir(2856, 2856, 0, False, True, True) == (2856, E.REDIR_PASS_OFF_FIELD),
    "redirect: no host on the wire (stale, selftest): passes": lambda: _redir(2856, 2856, -1, False, False, True) == (2856, E.REDIR_PASS_OFF_FIELD),
    "redirect: the relay's 65535: passes": lambda: _redir(2856, 2856, 65535, False, True, True) == (2856, E.REDIR_PASS_OFF_FIELD),
    "redirect: the host's field not on this install: passes": lambda: _redir(2856, 2856, 300, False, True, True) == (2856, E.REDIR_PASS_UNREGISTERED),
    "redirect: no fresh host snapshot: passes": lambda: _redir(2856, 2856, 300, True, False, True) == (2856, E.REDIR_PASS_NO_SNAPSHOT),
    "mutant: s143's bounce sends 9006's Field(2856) back to 2211, the field it left": lambda: (
        (lambda dest, my, host: dest if dest in (my, host) else my)(2856, 2211, 0) == 2211 and _redir(2856, 2856, 0, False, True, True)[0] != 2211),
    "redirect: an unfollowed guest still mirroring (its exit ramp pending) passes -- its landing applies no host snapshot": lambda: (
        _redir(2856, 2856, 300, True, True, False) == (2856, E.REDIR_PASS_NOT_FOLLOWING)),
    "mutant: no following term redirects it into the host's field with the entrance its world script wrote for 2856": lambda: (
        _redir(2856, 2856, 300, True, True, True)[0] == 300 and _redir(2856, 2856, 300, True, True, False)[0] != 300),
    "redirect: the host still on the field I just left (its hold): Field(2856) passes, never back into 2211": lambda: (
        _redir(2856, 2856, 2211, True, True, True, True) == (2856, E.REDIR_PASS_HELD)),
    "mutant: no hold term rewrites it to 2211, the field it left (the replay decision 4 forbids)": lambda: (
        _redir(2856, 2856, 2211, True, True, True, False)[0] == 2211 and _redir(2856, 2856, 2211, True, True, True, True)[0] != 2211),
    "landing: the hold rides a landing on another field (the passed entry) and ends on the held field itself": lambda: (
        E.world_hold_carries(2211, 2856) and not E.world_hold_carries(2211, 2211) and not E.world_hold_carries(-1, 2856)),
    "mutant: ending the hold at every field load lets the field follow chase straight back into 2211": lambda: (
        not _chases_back(E.world_hold_carries) and _chases_back(lambda h, l: False)),
    "landing: a load off the world map restarts the field follow's debounce; a field -> field load keeps it (s143)": lambda: (
        E.landing_follow_candidate(True, 2211) == -1 and E.landing_follow_candidate(False, 2211) == 2211
        and E.landing_follow_candidate(False, -1) == -1),
    "mutant: keeping the world's stable candidate fires the field follow on the landing field's first frame": lambda: (
        E.landing_follow_candidate(True, 2211) != 2211 and (lambda w, c: c)(True, 2211) == 2211),
    "latch: free on exactly 1 of 256 combinations, all eight clear": lambda: E.world_latch_frees() == (1, 255),
    "latch: attr bits outside 0x3001 (events off) leave it free": lambda: E.world_latch_step(True, 3, 0x0100, 3, False, False, False, False) is None,
    "latch: attr 0x2000 and 0x0001 hold it (the shutdown's other arms)": lambda: (
        E.world_latch_step(True, 3, 0x2000, 3, False, False, False, False) is not None
        and E.world_latch_step(True, 3, 0x0001, 3, False, False, False, False) is not None),
    "latch: nextMode 1 (a field entry) and 2 (a battle) hold it": lambda: (
        E.world_latch_step(True, 3, 0, 1, False, False, False, False) is not None
        and E.world_latch_step(True, 3, 0, 2, False, False, False, False) is not None
        and E.world_latch_step(True, 3, 0, 0, False, False, False, False) is None),
    "latch: our own armed rejoin holds it (the exit ramp waits for it)": lambda: E.world_latch_step(True, 3, 0, 3, False, False, False, True) is not None,
    "latch: a booted diorama or a battle return in flight holds it (s145's boot gates here)": lambda: (
        E.world_latch_step(True, 3, 0, 3, False, True, False, False) is not None
        and E.world_latch_step(True, 3, 0, 3, False, False, True, False) is not None),
    "latch: off the live world map it reads busy (fail closed)": lambda: E.world_latch_step(False, 3, 0, 3, False, False, False, False) is not None,
    "mutant: no rejoin-armed term frees 2": lambda: _latch(E.world_latch_step, j=False)[0] == 2,
    "mutant: no mode term frees 2 (the window ff9ShutdownStateWorldMap opens before its Replace)": lambda: _latch(E.world_latch_step, m=3)[0] == 2,
    "mutant: no nextMode term frees 2": lambda: _latch(E.world_latch_step, x=3)[0] == 2,
    "timeout: nothing armed, nothing times out": lambda: not E.world_arm_timed_out(-1, 99999, True),
    "timeout: at 5 s exactly it is still in flight": lambda: not E.world_arm_timed_out(300, E.WORLD_ARM_TIMEOUT_MS, True),
    "timeout: past 5 s still on the world map re-arms": lambda: E.world_arm_timed_out(300, E.WORLD_ARM_TIMEOUT_MS + 1, True),
    "timeout: off the world map the field landing clears it instead": lambda: not E.world_arm_timed_out(300, 99999, False),
    "ramp: a free-roam world map settles at once (s143)": lambda: E.ramp_world_settled(False, False),
    "ramp: an event world mid-cutscene (control off) waits -- the 10 s fail-safe bounds it": lambda: not E.ramp_world_settled(True, False),
    "ramp: an event world with control on settles": lambda: E.ramp_world_settled(True, True),
    "follow latch: on the world map with no world arm a field follow's stamp drops (it can no longer land)": lambda: E.world_follow_latch(True, -1, 300) == -1,
    "follow latch: an armed world rejoin keeps its own; off the world map the field follow's stays": lambda: (
        E.world_follow_latch(True, 300, 300) == 300 and E.world_follow_latch(False, -1, 300) == 300),
    "mutant: s143's guard keeps the stamp: the host back on 300 never re-arms the rejoin into it": lambda: (
        E.world_follow_latch(True, -1, 300) != 300 and (lambda w, a, l: l)(True, -1, 300) == 300),
    "entrance: the arm seeds the host snapshot's own FieldEntrance (section 0's bytes 2..3), never 9999": lambda: (
        E.host_entrance_of(_entrance_state(11)) == 11 != 9999),
    "entrance: a state with no story section seeds nothing": lambda: (
        E.host_entrance_of(E.append_section(b"", E.SECTION_INTENT, bytes([44, 1, 7]))) is None and E.host_entrance_of(None) is None),
    "entrance: a passed world entry keeps the guest's own entrance; the host's own field and a redirect take the host's": lambda: (
        all(E.pass_keeps_own_entrance(c) for c in (E.REDIR_PASS_OFF_FIELD, E.REDIR_PASS_UNREGISTERED, E.REDIR_PASS_NO_SNAPSHOT,
                                                    E.REDIR_PASS_NOT_FOLLOWING, E.REDIR_PASS_HELD))
        and not E.pass_keeps_own_entrance(E.REDIR_TO_HOST) and not E.pass_keeps_own_entrance(E.REDIR_PASS_HOST)),
    "entrance: the own entrance comes back only on the field the pass lands on": lambda: (
        E.pass_entrance_restores(2856, 2856) and not E.pass_entrance_restores(2856, 300) and not E.pass_entrance_restores(-1, 2856)),
}


def _chain(rule=None, **force):
    """WorldChainMisses over the twin, one input FORCED (a mutant), or another rule."""
    keys = ("pl", "a", "h", "r", "hd", "b", "w", "t", "aw", "kp", "cur")
    base = rule or E.world_guest_overlay

    def wrapped(*args):
        d = dict(zip(keys, args))
        d.update(force)
        return base(*[d[k] for k in keys])
    return E.world_chain_misses(wrapped)


def _codec_ok(flags: int) -> bool:
    """WaitBitsCodec's twin: the host's section-7 builder and the guest's parser (battlewire's, the engine's twins) carry the
    flags byte -- b6 / b7 included -- byte-exact."""
    view = BW.parse_dialog_section(BW.dialog_section(0x0144, 0x0144, flags))
    return view is not None and view["flags"] == flags and view["open_n"] == 0 and view["ring_n"] == 0


WORLD_MENU = E.HF_WORLD | E.HF_MENU | E.HF_CONTROL
OVL_ROWS = {
    "bits: b6 / b7 are the flags byte's two free bits": lambda: E.HF_WORLD == 0x40 and E.HF_TITLE == 0x80 and not (E.HF_WORLD | E.HF_TITLE) & E.HF_OLD_SIX,
    "host: the live world map sets b6, the title b7, a field neither": lambda: (
        E.host_where_bits(True, False) == E.HF_WORLD and E.host_where_bits(False, True) == E.HF_TITLE and E.host_where_bits(False, False) == 0),
    "codec: b6 rides a real section 7 byte-exact (the old parser accepts it)": lambda: _codec_ok(WORLD_MENU),
    "codec: b7, and both, ride it too": lambda: _codec_ok(E.HF_TITLE) and _codec_ok(WORLD_MENU | E.HF_TITLE),
    "reads: the guest's every read of the host's flags (HostFlagReads) is blind to b6 / b7 -- all 256 bytes read as their low six bits": lambda: E.flag_reads_blind(),
    "reads: each old bit reads alone -- a world host reads as s143 did (b4 + b1, off-field, no battle)": lambda: (
        E.host_flag_reads(E.HF_OLD_SIX) == 0x3F and E.host_flag_reads(WORLD_MENU) == E.HR_MENU | E.HR_CONTROL),
    "mutant: a whole-byte compare (hf == b3 | b4) reads a host with b6 set differently": lambda: not E.flag_reads_blind(
        lambda f: (E.host_flag_reads(f) & ~E.HR_MENU) | (E.HR_MENU if f == E.HF_ON_FIELD | E.HF_MENU else 0)),
    "read: no section 7 on the lane reads neither": lambda: not E.host_where_read(-1, E.HF_WORLD) and not E.host_where_read(-1, E.HF_TITLE),
    "read: each bit alone (b4 is not b6)": lambda: (
        E.host_where_read(WORLD_MENU, E.HF_WORLD) and not E.host_where_read(WORLD_MENU, E.HF_TITLE) and not E.host_where_read(E.HF_MENU, E.HF_WORLD)),
    "world chain: every scenario reads its line, in order": lambda: E.world_chain_misses() == 0,
    "mutant: s143's local == null -> OvlOff (a world guest saw nothing)": lambda: _chain(lambda *a: E.OVL_OFF) >= 8,
    "mutant: b6 ahead of the link (a stale bit hides a lost peer)": lambda: _chain(
        lambda pl, a, h, r, hd, b, w, t, aw, kp, cur: E.OVL_HOST_WORLD if w else E.world_guest_overlay(pl, a, h, r, hd, b, w, t, aw, kp, cur)) >= 1,
    "mutant: no armed term (the arm in flight reads the host's field instead)": lambda: _chain(a=-1) >= 1,
    "mutant: no registration term (promises a field this install lacks)": lambda: _chain(r=True) >= 1,
    "mutant: no hold term (says rejoining while the source-field hold waits)": lambda: _chain(hd=-1) >= 1,
    "mutant: no battle term (a waiting line over the battle panel)": lambda: _chain(b=False) >= 1,
    "mutant: everything sticky (a grace countdown frozen on screen)": lambda: _chain(cur=E.OVL_REJOINING) >= 1,
    "mutant: the line kept with no keep window (a live field the lane cannot place reads 'on the world map' indefinitely)": lambda: _chain(kp=True) >= 1,
    "detail: the field each line names (the armed destination first)": lambda: (
        E.world_guest_detail(E.OVL_REJOINING, 300, 301) == 300 and E.world_guest_detail(E.OVL_REJOINING, -1, 301) == 301
        and E.world_guest_detail(E.OVL_WORLD_HOLD, -1, 300) == 300 and E.world_guest_detail(E.OVL_PEER_NO_FIELD, -1, 302) == 302
        and E.world_guest_detail(E.OVL_HOST_WORLD, -1, 0) == 0),
    "tail: b6, b7, then the debounced field 0": lambda: (
        E.wait_line_tail(True, False, False, E.OVL_WAITING) == E.OVL_HOST_WORLD
        and E.wait_line_tail(False, True, False, E.OVL_WAITING) == E.OVL_HOST_TITLE
        and E.wait_line_tail(False, False, True, E.OVL_WAITING) == E.OVL_HOST_AWAY),
    "tail: a bit that says where beats the fallback": lambda: (
        E.wait_line_tail(True, True, True, E.OVL_WAITING) == E.OVL_HOST_WORLD and E.wait_line_tail(False, True, True, E.OVL_WAITING) == E.OVL_HOST_TITLE),
    "tail: nothing said -- s143's waiting line on a field": lambda: E.wait_line_tail(False, False, False, E.OVL_WAITING) == E.OVL_WAITING,
    "decision 5: a guest left on the field and one on the world map show the same line": lambda: (
        E.wait_line_tail(True, False, False, E.OVL_WAITING) == E.world_guest_overlay(False, -1, 0, False, -1, False, True, False, False, False, E.OVL_OFF)),
    "field tail: its own line kept through the keep window, as the world chain keeps its own (decision 5)": lambda: (
        E.field_wait_tail(False, False, False, True, E.OVL_HOST_WORLD) == E.OVL_KEEP
        and E.field_wait_tail(False, False, False, True, E.OVL_WAITING) == E.OVL_WAITING
        and E.field_wait_tail(False, False, False, False, E.OVL_HOST_WORLD) == E.OVL_WAITING
        and E.field_wait_tail(True, False, False, True, E.OVL_HOST_AWAY) == E.OVL_HOST_WORLD),
    "mutant: a fixed OvlWaiting tail flickers host_world -> waiting -> host_world around a door": lambda: (
        E.wait_line_tail(False, False, False, E.OVL_WAITING) != E.field_wait_tail(False, False, False, True, E.OVL_HOST_WORLD)),
    "keep: a bare field 0 (no b3 / b5 / b6 / b7: a door, a swirl) is the window": lambda: (
        E.wait_keep_window(True, 0, 0, False) and E.wait_keep_window(True, 65535, E.HF_MENU | E.HF_CONTROL, False)),
    "keep: b3 at lane 0 (a live field the lane cannot place) is no window -- the line goes off": lambda: (
        not E.wait_keep_window(True, 0, E.HF_ON_FIELD, False) and not E.wait_keep_window(True, 0, E.HF_ON_FIELD | E.HF_CONTROL, False)),
    "keep: a battle starting (b5, no live battle lane yet) keeps; a live lane is the panel's": lambda: (
        E.wait_keep_window(True, 0, E.HF_BATTLE, False) and not E.wait_keep_window(True, 0, E.HF_BATTLE, True)),
    "keep: a real field, no lane, or a bit that says where is no window": lambda: (
        not E.wait_keep_window(True, 300, 0, False) and not E.wait_keep_window(False, 0, 0, False)
        and not E.wait_keep_window(True, 0, E.HF_WORLD, False)),
    "mutant: s143's field chain says 'waiting for your friend to arrive on this screen' with the host on the world map": lambda: (
        E.wait_line_tail(True, False, False, E.OVL_WAITING) != E.OVL_WAITING),
    "away: a host on field 0 saying nothing (no section 7, or no bits)": lambda: E.wait_away_condition(True, 0, -1, False) and E.wait_away_condition(True, 0, 0, False),
    "away: an s143 host on its world HUD (b4 + b1) counts": lambda: E.wait_away_condition(True, 0, E.HF_MENU | E.HF_CONTROL, False),
    "away: b6 / b7 say where -- no fallback": lambda: not E.wait_away_condition(True, 0, E.HF_WORLD, False) and not E.wait_away_condition(True, 0, E.HF_TITLE, False),
    "away: b3 (a field the lane cannot place) is not away": lambda: not E.wait_away_condition(True, 0, E.HF_ON_FIELD, False),
    "away: a battle (b5, or the live type-1 lane) is not away": lambda: not E.wait_away_condition(True, 0, E.HF_BATTLE, False) and not E.wait_away_condition(True, 0, 0, True),
    "away: a real field is not; the relay's 65535 is": lambda: not E.wait_away_condition(True, 300, 0, False) and E.wait_away_condition(True, 65535, 0, False),
    "away: no live lane is not (the link lines own it)": lambda: not E.wait_away_condition(False, 0, 0, False),
    "away: due at WaitAwayMs, not before": lambda: not E.wait_away_due(True, True, E.WAIT_AWAY_MS - 1) and E.wait_away_due(True, True, E.WAIT_AWAY_MS),
    "away: due needs the clock armed and the condition now": lambda: not E.wait_away_due(True, False, 99999) and not E.wait_away_due(False, True, 99999),
    "mutant: no debounce reads a door's 1 s field 0 as away (the line flickers)": lambda: (lambda c, a, ms: c)(True, True, 1000) and not E.wait_away_due(True, True, 1000),
    "mutant: no bit mask calls a host the lane cannot place away": lambda: (
        (lambda v, f, fl, b: v and not b and f in (0, 65535))(True, 0, E.HF_ON_FIELD, False) and not E.wait_away_condition(True, 0, E.HF_ON_FIELD, False)),
    "names: the waitline vocabulary": lambda: [E.wait_line_name(s) for s in (9, 10, 11, 12, 13)] == ["host_world", "rejoin", "hold", "host_title", "away"],
    "names: no other state is a waiting line": lambda: all(E.wait_line_name(s) is None for s in (E.OVL_WAITING, E.OVL_OFF, E.OVL_PEER_NO_FIELD, E.OVL_KEEP)),
    "names: every overlay state named, none twice, OvlKeep none": lambda: len(set(E.OVERLAY_NAMES)) == len(E.OVERLAY_NAMES) == 14,
    "words: the host on the world map": lambda: "Your partner is on the world map." in E.wait_line_text(E.OVL_HOST_WORLD) and "You'll rejoin them at their next stop." in E.wait_line_text(E.OVL_HOST_WORLD),
    "words: the host at the title": lambda: "Your partner is at the title screen." in E.wait_line_text(E.OVL_HOST_TITLE),
    "words: an old host away": lambda: "Your partner is away." in E.wait_line_text(E.OVL_HOST_AWAY),
    "words: the rejoin names its field": lambda: "Rejoining your partner" in E.wait_line_text(E.OVL_REJOINING, 300) and "300" in E.wait_line_text(E.OVL_REJOINING, 300),
    "words: the hold names its field and its cap": lambda: "300" in E.wait_line_text(E.OVL_WORLD_HOLD, 300) and f"{E.WORLD_HOLD_MS // 1000} s" in E.wait_line_text(E.OVL_WORLD_HOLD, 300),
    "words: none for the other states (SetOverlay composes those)": lambda: E.wait_line_text(E.OVL_WAITING) is None and E.wait_line_text(E.OVL_OFF) is None,
}

SELFTESTS = [
    ("freeze", "NetSyncField.cs", "internal static Boolean WorldFreezeSelfTest(", "FreezeRow", FREEZE_ROWS, BW.WORLD_FREEZE_SELFTEST_ROWS),
    ("rejoin", "NetSyncClient.cs", "internal static Boolean WorldRejoinSelfTest(", "RejoinRow", REJOIN_ROWS, BW.WORLD_REJOIN_SELFTEST_ROWS),
    ("overlay", "NetSyncClient.cs", "internal static Boolean OverlayTextSelfTest(", "OvlRow", OVL_ROWS, BW.OVERLAY_TEXT_SELFTEST_ROWS),
]


@pytest.mark.parametrize("kind,file_name,start,helper,rows,count", SELFTESTS, ids=[s[0] for s in SELFTESTS])
def test_every_engine_selftest_row_has_a_twin_that_holds(kind, file_name, start, helper, rows, count):
    names = _row_names(file_name, start, helper)
    assert len(names) == count == len(set(names)), (kind, len(names), count)
    assert names == list(rows), [n for n in names if n not in rows] + ["--"] + [n for n in rows if n not in names]
    failed = [name for name, check in rows.items() if check() is not True]
    assert not failed, failed


def test_the_proof_block_logs_the_three_lines_after_the_leader_guard_line_in_order():
    heads = [ln for ln in net_lines("NetSyncClient.cs", r'Log\.Message\("\[NetSync\] [a-z ]+ selftest: "')]
    order = [re.search(r'\[NetSync\] ([a-z ]+ selftest: )', ln).group(1) for ln in heads]
    i = order.index(BW.PROOF_LEADER_GUARD)
    assert order[i + 1:i + 4] == [BW.PROOF_WORLD_FREEZE, BW.PROOF_WORLD_REJOIN, BW.PROOF_OVERLAY_TEXT], order


# ------------------------------------------------------------------------------------------------ every check can fail
def test_each_twins_mutants_miss_its_table():
    """A twin that cannot fail proves nothing: each one-line mutant (the engine's own, and the ones its offline Roslyn harness
    ran against the real source) misses the twin's own table."""
    assert E.world_chain_misses() == 0
    for force in ({"pl": False}, {"a": -1}, {"r": True}, {"hd": -1}, {"b": False}, {"cur": E.OVL_OFF}, {"cur": E.OVL_REJOINING},
                  {"w": False}, {"t": False}, {"aw": False}, {"kp": True}, {"kp": False}):
        assert _chain(**force) >= 1, force
    assert _chain(lambda pl, a, h, r, hd, b, w, t, aw, kp, cur: E.world_guest_overlay(pl, a, h if h != 65535 else 1, r, hd, b, w, t, aw, kp, cur)) >= 1
    assert E.world_freeze_rule_mask(lambda s, b, t, r, e: s) != E.WORLD_FREEZE_TABLE
    assert _arm(E.world_arm_refusal, e=False)[0] == 2 and _latch(E.world_latch_step, w=True)[0] == 2
    assert not (lambda c, a, ms: c and a and ms > E.WAIT_AWAY_MS)(True, True, E.WAIT_AWAY_MS)   # `>` for `>=` misses the edge


# ------------------------------------------------------------------------------------------------ the call sites
def test_the_world_chain_runs_ahead_of_local_null_and_the_field_tail_replaces_the_bare_waiting_line():
    """A law in a docstring is a wish: the overlay chain's CALL SITES carry the waiting line -- the world guest's chain right
    after the session grace (ahead of s143's `local == null -> OvlOff`), the field chain's last branch through the shared tail,
    and SetOverlay composes the asked state (overlay_text) while drawing only the allowed one."""
    added = net_lines("NetSyncClient.cs", r".", [_patch()])
    assert "else if (onWorld && WaitLineOn)" in [_code(t) for t in added]
    code = [_code(t) for t in added]
    i = code.index("Int32 tail = FieldWaitTail(WaitLineOn && _hostWorld, WaitLineOn && _hostTitle, WaitLineOn && _waitAwayDue,")
    assert code[i + 1:i + 4] == ["WaitLineOn && _waitKeep, _ovlAsked);", "if (tail != OvlKeep)", "SetOverlay(tail);"], code[i:i + 4]
    assert "_waitKeep = client && WaitKeepWindow(rs.Valid, rs.Field, flags, NetSyncBattle.PeerBattleLive);" in code
    assert "else if (onWorld && _role == \"host\" && peerLost)" in code and "SetOverlay(OvlConnecting, 0);" in code
    removed = [ln[1:].strip() for p, sec in msr.sections(_patch()) if p and p.endswith("NetSyncClient.cs")
               for ln in sec.decode("utf-8").splitlines() if ln.startswith("-") and not ln.startswith("---")]
    assert "SetOverlay(OvlWaiting);" in removed and "switch (state)" in removed
    new = [t for _h, _k, t in _new_side("NetSyncClient.cs")]
    i = next(k for k, t in enumerate(new) if t.startswith("SetOverlay(OvlReconnecting, SessionGraceLeftSec());"))
    j = next(k for k in range(i, len(new)) if new[k].startswith("else if (local == null)"))
    assert any(_code(t) == "else if (onWorld && WaitLineOn)" for t in new[i:j])
    assert "NoteHostWhere(rs, Environment.TickCount);" in [_code(t) for t in added]
    j = next(k for k, t in enumerate(new) if t.startswith("else if (onWorld && WaitLineOn)"))
    h = next(k for k, t in enumerate(new) if _code(t) == 'else if (onWorld && _role == "host" && peerLost)')
    assert j < h < next(k for k in range(h, len(new)) if new[k].startswith("else if (local == null)"))
    getter = [t for t in added if t.startswith("public static String HarnessOverlayText")]
    assert len(getter) == 1 and "i._ovlComposed" in getter[0]
    assert "_ovlComposed = _ovlText;" in [_code(t) for t in added] and "_waitLine = WaitLineName(asked);" in [_code(t) for t in added]


def _hunk_of(file_name: str, start: str) -> list:
    """The s144 patch's hunk (new side: context and added lines, in file order) of ``file_name`` that holds a line starting
    ``start`` -- each line's code (comments off), empty ones dropped. A hunk IS contiguous file text: the pins below read their
    neighbours there, never through the stack-wide line order."""
    new = _new_side(file_name)
    h = next(hk for hk, _k, t in new if _code(t).startswith(start))
    return [c for hk, _k, t in new if hk == h for c in [_code(t)] if c]


def test_the_frozen_key_mask_returns_the_world_mask_and_counts_in_its_own_block():
    """freeze-key-closure-unwitnessed: the part of the mask that is new in s144 (Cancel, Triangle, the face buttons) has no
    in-game witness on foot, so its CALL SITE is pinned: inside `if (ee.gMode == 3 && WorldFreezeNow)` the counter, and the
    return is exactly ControlOnScriptKeys(keys, true) -- a block that counts and returns F1's mask (the stand-in's
    `keys_counted_s143`) reads red here. The release's own branch follows it, F1's after both."""
    block = _hunk_of("NetSyncField.cs", "if (ee.gMode == 3 && WorldFreezeNow)")
    i = block.index("if (ee.gMode == 3 && WorldFreezeNow)")
    j = block.index("if (ee.gMode == 3 && WorldFreezeReleased)")
    frozen, released = block[i:j], block[j:]
    assert frozen[1] == "{" and frozen[-1] == "}" and frozen[-2] == "return ControlOnScriptKeys(keys, true);", frozen

    def counted_and_masked(lines) -> bool:
        return "HarnessWorldFreezeKeys++;" in lines and lines[-2] == "return ControlOnScriptKeys(keys, true);"
    assert counted_and_masked(frozen) and "if ((keys & readMask & HostOwnedKeys) != 0)" in frozen
    assert released[released.index("}") - 1] == "return ReleasedWorldScriptKeys(keys);", released[:12]
    assert i < j < block.index("return ControlOnScriptKeys(keys, false);")
    # the check can fail: the counted-but-F1 shape
    assert not counted_and_masked(frozen[:-2] + ["return ControlOnScriptKeys(keys, false);", "}"])


def test_the_world_rule_runs_ahead_of_the_departed_field_bounce():
    """rejoin-selftest-vacuous-rows: the s143 bounce's mutant row cannot reach this law, so the call site is pinned --
    RedirectGuestFieldJump routes gMode 3 to RedirectGuestWorldFieldJump BEFORE it reads fldMapNo (the field the guest LEFT)."""
    block = _hunk_of("NetSyncClient.cs", "return RedirectGuestWorldFieldJump(ref dest);")
    gate = block.index("if (ee != null && ee.gMode == 3)")
    assert block[gate + 1] == "return RedirectGuestWorldFieldJump(ref dest);"
    assert gate < block.index("Int32 myField = FF9StateSystem.Common.FF9.fldMapNo;")
    world = _hunk_of("NetSyncClient.cs", "private static Boolean RedirectGuestWorldFieldJump(")
    assert "Boolean following = IsLiveFollowedSession && i != null && !i._exitRampPending;" in world
    assert "Boolean held = i != null && i.HoldHoldsFor(host);" in world
    assert "Int32 to = WorldRedirectStep(dest, land, host, registered, snapshot, following, held, out code);" in world


def _next_code(block, line, n=1) -> list:
    """The ``n`` code lines after ``line`` in ``block`` (a hunk's code: comments and empty lines off)."""
    i = block.index(line)
    return block[i + 1:i + 1 + n]


def _skip_ahead_of_s38(block, op) -> bool:
    """[review 2] the world skip sits right after the opcode's LAST getv and AHEAD of s38's IsMirroringStory gate (when the hunk
    shows it): s38 returns first and would consume nothing."""
    skip = f'if (Memoria.Netsync.NetSyncField.SkipWorldScriptedBattle(this.gMode, btlId & Int16.MaxValue, "{op}"))'
    if skip not in block:
        return False
    k = block.index(skip)
    mirror = "if (Memoria.Netsync.NetSyncClient.IsMirroringStory)"
    return block[k - 1].startswith("Int32 btlId = this.getv2();") and block[k + 1] == "return 0;" and \
        (mirror not in block or block.index(mirror) > k)


def test_the_world_skip_consumes_its_press_ahead_of_s38s_gate():
    """rfreeze-1 [review 2]: the skip's `return 0` continues the script INLINE (into the quicksand dispatcher's location poll),
    so SkipWorldScriptedBattle clears this key tick's host-owned edges inside its true branch, and both opcodes ask it FIRST --
    s38's IsMirroringStory gate returns 0 too and would consume nothing (a mirroring released guest's Confirm went on). The
    patch removes no s38 line. The old order reads red (the check can fail)."""
    skip = _hunk_of("NetSyncField.cs", "public static Boolean SkipWorldScriptedBattle(")
    s = skip.index("public static Boolean SkipWorldScriptedBattle(Int32 gMode, Int32 scene, String op)")
    body = skip[s:skip.index("return true;", s) + 1]
    assert body[2:4] == ["if (gMode != 3 || !SpectatorField)", "return false;"], body[:6]
    assert body.index("ETb.sKeyOn = WorldSkipKeyOn(ETb.sKeyOn);") > body.index("try") > body.index("return false;")
    key_on = skip.index("internal static UInt32 WorldSkipKeyOn(UInt32 keyOn)")
    assert skip[key_on + 2] == "return keyOn & ~HostOwnedKeys;", skip[key_on:key_on + 4]
    enc = _hunk_of("EventEngine.DoEventCode.cs", 'if (Memoria.Netsync.NetSyncField.SkipWorldScriptedBattle(this.gMode, btlId & Int16.MaxValue, "ENCOUNT"))')
    enc2 = _hunk_of("EventEngine.DoEventCode.cs", 'if (Memoria.Netsync.NetSyncField.SkipWorldScriptedBattle(this.gMode, btlId & Int16.MaxValue, "ENCOUNT2"))')
    assert _skip_ahead_of_s38(enc, "ENCOUNT") and _skip_ahead_of_s38(enc2, "ENCOUNT2")
    assert "if (Memoria.Netsync.NetSyncClient.IsMirroringStory)" in enc2                 # the order is in the hunk itself
    assert len(net_lines("EventEngine.DoEventCode.cs", r"NetSyncField\.SkipWorldScriptedBattle\(")) == 2
    removed = [ln[1:].strip() for p, sec in msr.sections(_patch()) if p and p.endswith("EventEngine.DoEventCode.cs")
               for ln in sec.decode("utf-8").splitlines() if ln.startswith("-") and not ln.startswith("---")]
    assert not [ln for ln in removed if "IsMirroringStory" in ln], removed
    # the check can fail: the as-built order (the skip AFTER s38's gate)
    old = ["Int32 btlId = this.getv2();", "if (Memoria.Netsync.NetSyncClient.IsMirroringStory)", "return 0;",
           'if (Memoria.Netsync.NetSyncField.SkipWorldScriptedBattle(this.gMode, btlId & Int16.MaxValue, "ENCOUNT2"))', "return 0;"]
    assert not _skip_ahead_of_s38(old, "ENCOUNT2")


def test_the_hold_binds_the_redirect_the_landing_and_the_field_follow_at_their_call_sites():
    """rrejoin-1 [review 2]: decision 4 binds every rejoin into the departed field, at its CALL SITES -- NoteWorldLanding restarts
    the follow's debounce on a load off the world map and ends the hold ONLY on the held field (else it rides the landing);
    FollowHostTick's field branch asks the hold right before StartFollowWarp; ServiceIntentFollow's field branch defers an
    intent into a held field before marking it seen; F11 on a field clears a hold that rode onto it before re-arming."""
    land = _hunk_of("NetSyncClient.cs", "_followCandidate = LandingFollowCandidate(ee != null && ee.gMode == 3, _followCandidate);")
    a = land.index("_followCandidate = LandingFollowCandidate(ee != null && ee.gMode == 3, _followCandidate);")
    assert land[a + 1:a + 3] == ["if (_worldHoldField >= 0)", "{"], land[a:a + 4]
    carry = land.index("if (WorldHoldCarries(_worldHoldField, fld))")
    e = land.index("else", carry)
    assert land[carry + 1].startswith('Log.Message("[NetSync] world rejoin hold on field "') and land[e + 1] == "{"
    assert "_worldHoldField = -1;" not in land[a:e] and land.index("_worldHoldField = -1;", e) > e    # only off the held field
    tick = _hunk_of("NetSyncClient.cs", "if (HoldHoldsFor(rs.Field))")
    h = tick.index("if (HoldHoldsFor(rs.Field))")
    assert tick[h - 2:h] == ["if (!EventEngineUtils.eventIDToFBGID.ContainsKey(rs.Field))", "return;"], tick[h - 3:h]
    assert tick[h + 1:h + 6] == ["{", "NoteFieldFollowHeld(rs.Field);", "return;", "}", "StartFollowWarp(rs.Field);"], tick[h:h + 6]
    intent = _hunk_of("NetSyncClient.cs", "if (HoldHoldsFor(destField))")
    k = intent.index("if (HoldHoldsFor(destField))")
    assert intent[k + 1:k + 4] == ["return;", "_lastIntentNonce = nonce;", "StartFollowWarp(destField);"], intent[k:k + 4]
    tp = _hunk_of("NetSyncClient.cs", 'Log.Message("[NetSync] teleport-to-host: following the peer to field " + rs.Field + (held')
    t = tp.index("Boolean held = _worldHoldField >= 0;")
    assert tp[t + 1] == "_worldHoldField = -1;" and tp.index("_followCandidate = rs.Field;") > t + 1
    # the check can fail: as-built's landing (the hold ended at every field load)
    asbuilt = ["if (_worldHoldField >= 0)", "{", 'Log.Message("[NetSync] world rejoin hold on field " + _worldHoldField', "_worldHoldField = -1;"]
    assert "if (WorldHoldCarries(_worldHoldField, fld))" not in asbuilt


def test_the_follow_latch_and_the_cancel_and_the_seed_sit_where_their_laws_need_them():
    """The stale-latch fixes at their call sites: FollowHostTick drops a field stamp on the world map at its TOP (ahead of its
    `rs.Valid` read, which precedes the same-destination guard); the guest's own WMAPJUMP (NoteGuestWorldJump) cancels a field
    follow in flight; ServiceFollowWarp drops its deferred half in mode 3; StartWorldFollowWarp seeds the host's entrance
    before its levers."""
    tick = _hunk_of("NetSyncClient.cs", "Int32 latch = WorldFollowLatch(onWorld, _worldFollowArmed, _followWarpedTo);")
    a = tick.index("Int32 latch = WorldFollowLatch(onWorld, _worldFollowArmed, _followWarpedTo);")
    assert tick[a - 2:a] == ["if (!_followHost || _followWarpPending >= 0)", "return;"], tick[a - 3:a]
    assert "if (!rs.Valid || rs.Field <= 0 || rs.Field == 65535)" in tick[a:]
    jump = _hunk_of("NetSyncClient.cs", "internal static void NoteGuestWorldJump(")
    k = next(n for n, ln in enumerate(jump) if ln.startswith("internal static void NoteGuestWorldJump("))
    assert "i._followWarpPending = -1;" in jump[k:] and "i._followWarpedTo = -1;" in jump[k:]
    warp = _hunk_of("NetSyncClient.cs", "if (PersistenSingleton<FF9StateSystem>.Instance.mode == 3)")
    assert warp.index("_followWarpPending = -1;") < warp.index("if (PersistenSingleton<FF9StateSystem>.Instance.mode == 3)") \
        < warp.index("try")
    arm = _hunk_of("NetSyncClient.cs", "private void StartWorldFollowWarp(")
    s = arm.index("private void StartWorldFollowWarp(Int32 dest)")
    assert arm[s + 2] == "SeedHostEntrance();" and arm[s + 3] == "PersistenSingleton<EventEngine>.Instance.SetNextMap(dest);"


#: the host-flag reads the live stack makes, by variable: a read must be a single-bit (or OR-of-bits) `&` test or a sentinel
#: test (`>= 0` / `< 0`), never a whole-byte compare or a switch. The two codec round-trip selftests compare the whole byte ON
#: PURPOSE (that the byte came back) and are named here.
_FLAG_VARS = r"(?:\bhf\b|\bhostFlags\b|\bhv\.Flags\b|_view\.Flags\b|\bHostFlags\b)"
_WHOLE_BYTE = re.compile(_FLAG_VARS + r"\s*(?:==|!=)|(?:==|!=)\s*" + _FLAG_VARS + r"|switch\s*\(\s*" + _FLAG_VARS)
_CODEC_COMPARES = ("return v.Flags == flags ? null :", "if (v.Epoch != 0x1234 || v.Heartbeat != 0xBEEF || v.Flags != (HfScene")


def _whole_byte_reads(lines) -> list:
    """The lines whose CODE (string literals blanked: a row's name may say "hf == b3 | b4") compares a flags read whole."""
    unquoted = lambda ln: re.sub(r'"(?:[^"\\]|\\.)*"', '""', ln)                    # noqa: E731
    return [ln for ln in lines if _WHOLE_BYTE.search(unquoted(ln)) and not any(ln.startswith(c) for c in _CODEC_COMPARES)]


def test_every_live_read_of_the_host_flags_is_a_single_bit_test():
    """wire-3: "an old guest ignores b6 / b7" is TRUE only while every read of the flags byte is a single-bit test -- pinned
    over the LIVE stack's NetSyncClient.cs / NetSyncDialog.cs (no `hf == 0x18`, no switch on it); ServiceDialogAuthority reads
    the byte only through HostFlagReads, whose six tests are single bits (the engine's selftest proves it blind to b6 / b7 over
    all 256 bytes). An injected whole-byte compare reads red (the check can fail)."""
    for name in ("NetSyncClient.cs", "NetSyncDialog.cs"):
        lines = [_code(t) for t in net_lines(name, r".")]
        assert not _whole_byte_reads(lines), (name, _whole_byte_reads(lines)[:3])
    client = [c for c in (_code(t) for t in net_lines("NetSyncClient.cs", r"\bhf\b"))
              if re.search(r"\bhf\b", re.sub(r'"(?:[^"\\]|\\.)*"', '""', c))]
    helper = [ln for ln in client if "? Hr" in ln]
    tests = re.findall(r"\(hf & NetSyncDialog\.Hf(\w+)\) != 0", " ".join(helper))
    assert tests == ["Scene", "OnField", "Battle", "Line", "Menu", "Control"], tests
    rest = [ln for ln in client if ln not in helper and not ln.startswith(("internal static Int32 HostFlagReads(",
                                                                          "private delegate Int32 HostFlagRule1("))]
    assert sorted(rest) == ["Byte hf = hv != null ? hv.Flags : (Byte)0;", "Int32 hr = HostFlagReads(hf);"], rest
    assert _whole_byte_reads(["if (hf == 0x18)", "switch (hostFlags)", "v.HostMenu = hv.Flags != NetSyncDialog.HfMenu;"]) == \
        ["if (hf == 0x18)", "switch (hostFlags)", "v.HostMenu = hv.Flags != NetSyncDialog.HfMenu;"]


# ------------------------------------------------------------------------------------------------ the keys, the accessors
def _agent_nothing() -> dict:
    """The live agent's `netsync` block at the catch line's sentinels (the one literal, its F3 pin spliced in)."""
    catch = net_lines("HarnessAgent.cs", r'outer\.Append\("\\"netsync\\":\{\\"enabled')
    head = net_lines("HarnessAgent.cs", r'NetsyncF3Retired = "')
    tail = net_lines("HarnessAgent.cs", r'\+ "\\"align_win')
    assert len(catch) == len(head) == len(tail) == 1
    a, b = re.findall(r'"((?:[^"\\]|\\.)*)"', catch[0])
    pinned = "".join(re.findall(r'"((?:[^"\\]|\\.)*)"', head[0]) + re.findall(r'"((?:[^"\\]|\\.)*)"', tail[0]))
    return json.loads("{" + (a + pinned + b).replace('\\"', '"') + "}")["netsync"]


def _leaves(node: dict, prefix: str = "") -> dict:
    out = {}
    for k, v in node.items():
        path = prefix + k
        out[path] = v
        if isinstance(v, dict):
            out.update(_leaves(v, path + "."))
    return out


def test_every_world_key_has_an_accessor_and_reads_its_sentinel():
    """`netsync.world`'s every key path (the blocks and their leaves) is exactly the world accessor table's, and each reads
    its sentinel's type at rest (a null string reads ""); on an s143 block every one reads None -- "this engine cannot" --
    and the capability False; the top-level keys outside netsync read None when absent."""
    nothing = _agent_nothing()
    assert nothing["world"] == BW.WORLD_SENTINELS and list(nothing)[-1] == "world"
    assert nothing["session"]["follow"] == BW.SESSION_FOLLOW_SENTINELS and nothing["session"]["overlay_text"] is None
    assert list(nothing["session"])[-2:] == list(BW.SESSION_KEYS_S144) and tuple(nothing["session"]) == FG.NETSYNC_SESSION_KEYS
    leaves = _leaves(nothing["world"])
    table = CH.State.NETSYNC_WORLD_ACCESSORS
    assert set(table) == set(leaves), sorted(set(table) ^ set(leaves))
    st = CH.State({"frame": 1, "netsync": nothing})
    for path, name in table.items():
        got, want = getattr(st, name), leaves[path]
        if want is None:
            assert got == "", (path, got)
        elif isinstance(want, dict):
            assert got == want and got is not want, path
        else:
            assert got == want and type(got) is type(want), (path, got, want)
    assert st.coop_world_wait is True and st.session_overlay_text == "" and st.session_follow == BW.SESSION_FOLLOW_SENTINELS
    before = [(msr.PATCHES / n).read_bytes() for n in msr.stack()[:msr.stack().index(PATCH)] if n not in msr.DEAD]
    old_line = net_lines("HarnessAgent.cs", r'outer\.Append\("\\"netsync\\":\{\\"enabled', before)
    assert len(old_line) == 1 and '\\"world\\":' not in old_line[0] and '\\"overlay_text\\"' not in old_line[0]
    old = CH.State({"frame": 1, "netsync": {"enabled": False, "session": {"grace_ms": -1}}})
    assert old.coop_world_wait is False and all(getattr(old, n) is None for n in table.values())
    assert old.session_overlay_text is None and old.session_follow is None
    assert CH.State({"frame": 1}).coop_world_wait is None
    for name in ("gmode", "field_entrance", "world_area", "world_topo", "world_move", "world_phase", "world_next_mode"):
        assert getattr(CH.State({"frame": 1}), name) is None, name
    live = CH.State({"frame": 1, "gmode": 3, "field": {"id": 0, "entrance": 9999},
                     "world": {"id": 9011, "area": 4, "topo": 7, "move": False, "phase": 2, "next_mode": 3}})
    assert (live.gmode, live.field_entrance, live.world_area, live.world_topo, live.world_move, live.world_phase,
            live.world_next_mode) == (3, 9999, 4, 7, False, 2, 3)


# ------------------------------------------------------------------------------------------------ the stand-in's rung, the driver
def test_the_worldwait_rung_is_s144s_after_leaderguard_and_calibrates_on_s143():
    names = list(FG.NETSYNC_BATTLE_CAPS)
    assert names[names.index("leaderguard") + 1] == "worldwait" and FG.NETSYNC_BATTLE_CAPS["worldwait"] == ("s144", ())
    assert FG.NETSYNC_S144_CAPS == frozenset(("worldwait",)) and "worldwait" not in FG.caps_through("leaderguard")
    assert FG.NETSYNC_TOP_CAP_KEYS["worldwait"] == ("world",) and FG.NETSYNC_BATTLE_CAP_KEYS["worldwait"] == {}
    assert FG.NETSYNC_SESSION_KEYS[-2:] == BW.SESSION_KEYS_S144 == ("overlay_text", "follow")
    assert Session.NETSYNC_BENCH_OPS["worldfreeze"][:3] == ("coop_world_wait", "netsync.world.freeze", "s144")
    assert isinstance(getattr(CH.State, "coop_world_wait"), property)
    src = (REPO / "studies" / "test-harness" / "scenarios" / "_coop_battle.py").read_text(encoding="utf-8")
    assert '144: "netsync.world.freeze",' in src


def _game(root):
    """A stand-in install: the exe, Memoria.log, one registered field (the bench's)."""
    (root / "x64").mkdir(parents=True)
    (root / "x64" / "FF9.exe").write_bytes(b"MZ")
    (root / "x64" / "Memoria.log").write_text("fake log" + chr(10), encoding="utf-8")
    mod = root / "FF9CustomMap"
    mod.mkdir()
    (mod / "DictionaryPatch.txt").write_text("FieldScene 30602 11 T30602 T30602 30602" + chr(10), encoding="utf-8")
    return root


def _session(game, fake) -> Session:
    return Session(game_path=game, run_dir=game / "run", save_dir=game / "player-saves", pid_probe=lambda: [],
                   launcher=lambda exe: fake.start(), boot_timeout=15.0, verbose=False)


def _stand_in(root, caps=None):
    fake = FakeGame(_game(root))
    if caps is not None:
        fake.netsync_caps = caps
    return fake


def _walk(fake, frames: int) -> None:
    held = fake._is_held
    fake._is_held = lambda key: key == "up" or held(key)
    try:
        for _ in range(frames):
            fake._step_overworld()
    finally:
        fake._is_held = held


@pytest.mark.parametrize("rung", ["worldwait", "leaderguard"])
def test_the_stand_in_freezes_its_overworld_walker_and_the_lever_lifts_it(tmp_path, rung):
    """The `worldwait` rung's model: in the selftest role under `bench 1` the overworld walker idles (the bumpers and the walk
    both skipped -- one dispatcher), `freeze.on` / `why` / `edges` / `skips` say so, `bench worldfreeze off` lifts it (on the
    selftest role only) and the harness release puts it back; s143's stand-in walks -- its calibration red."""
    fake = _stand_in(tmp_path, None if rung == "worldwait" else FG.caps_through("leaderguard"))
    fake.ui_state, fake.control = "WorldHUD", True                # w_movementControl runs only under user control
    fake.world["x"], fake.world["z"] = 100.0, 100.0
    fake.overworld = {"speed": 2.0, "lag": 1}
    fake._netsync(["selftest", "1"])
    fake._netsync(["bench", "1"])
    _walk(fake, 5)
    moved = (fake.world["x"], fake.world["z"]) != (100.0, 100.0)
    doc = fake._netsync_doc()
    if rung == "leaderguard":
        assert moved and "world" not in doc and "overlay_text" not in doc["session"]
        return
    freeze = doc["world"]["freeze"]
    assert not moved and freeze["on"] is True and freeze["why"] == "bench" and freeze["off"] is False
    assert freeze["skips"] == 5 and freeze["edges"] == 1
    assert doc["session"]["follow"]["on_world"] is True and doc["session"]["overlay_text"] is None
    assert doc["world"]["rejoin"] == BW.WORLD_REJOIN_SENTINELS and doc["world"]["waitline"] == BW.WORLD_WAITLINE_SENTINELS
    fake._netsync(["bench", "worldfreeze", "off"])
    _walk(fake, 1)
    assert (fake.world["x"], fake.world["z"]) != (100.0, 100.0)
    freeze = fake._netsync_doc()["world"]["freeze"]
    assert freeze["off"] is True and freeze["on"] is False and freeze["skips"] == 5
    fake._netsync(["bench", "worldfreeze", "on"])
    _walk(fake, 1)
    assert fake._netsync_doc()["world"]["freeze"]["edges"] == 2               # a re-freeze is a new edge
    fake._netsync(["bench", "worldfreeze", "off"])
    fake._netsync(["selftest", "0"])                                          # the harness release: the lever back on
    assert fake._wf_off is False


def test_the_stand_ins_freeze_runs_only_under_user_control(tmp_path):
    """freeze-standin-control-ungated: w_movementControl -- the freeze's one call site -- is reached only under
    ff9.GetUserControl() (ff9.cs 5185), so a world script's control-off window counts no skip and fires no edge; the edge
    fires on control's return (a freeze that engaged meanwhile)."""
    fake = _stand_in(tmp_path)
    fake.ui_state, fake.control = "WorldHUD", False
    fake.world["x"], fake.world["z"] = 100.0, 100.0
    fake.overworld = {"speed": 2.0, "lag": 1}
    fake._netsync(["selftest", "1"])
    fake._netsync(["bench", "1"])
    _walk(fake, 5)
    freeze = fake._netsync_doc()["world"]["freeze"]
    assert freeze["skips"] == 0 and freeze["edges"] == 0 and (fake.world["x"], fake.world["z"]) == (100.0, 100.0)
    fake.control = True
    _walk(fake, 3)
    freeze = fake._netsync_doc()["world"]["freeze"]
    assert freeze["skips"] == 3 and freeze["edges"] == 1 and (fake.world["x"], fake.world["z"]) == (100.0, 100.0)


def test_the_driver_never_sends_bench_worldfreeze_to_an_s143_engine(tmp_path):
    """THE s110 HAZARD AGAIN: an s143 agent reads `bench worldfreeze off` as `bench 1` (the FIELD-GATE bench ON). The driver
    refuses it before the step on an engine without `netsync.world.freeze`; that engine would turn the bench on; on s144 it
    lands and the field-gate bench stays as it was."""
    fake = _stand_in(tmp_path / "old", FG.caps_through("leaderguard"))
    with _session(tmp_path / "old", fake) as g:
        g.newgame(settle=0)
        g.netsync("selftest", 1)
        n = len(fake.executed)
        with pytest.raises(HarnessError, match=r"netsync bench worldfreeze: the deployed engine publishes no "
                                               r"`netsync\.world\.freeze` .*\(memoria-patch s144\)"):
            g.netsync("bench", "worldfreeze", "off")
        assert len(fake.executed) == n and g.state.netsync["bench"] is False
    fake._netsync(["bench", "worldfreeze", "off"])                            # what that engine would DO with it
    assert fake.netsync["bench"] is True
    new = _stand_in(tmp_path / "new")
    with _session(tmp_path / "new", new) as g:
        g.newgame(settle=0)
        g.netsync("selftest", 1)
        st = g.netsync("bench", "worldfreeze", "off")
        assert new.executed[-1] == ["netsync", "bench", "worldfreeze", "off"] and st.netsync["bench"] is False
        st = g.wait_for(lambda s: s.world_freeze_off is True, timeout=4.0, what="the lever")


def test_the_stand_in_logs_the_three_proof_lines_after_the_leader_guard_line(tmp_path):
    """[ff9mapkit netsync s145] on the s144 stand-in (the ladder through `worldwait`): s145 grows the freeze line to 46 rows and
    appends two lines after the overlay text one (tests/test_world_diorama_harness.py pins that stage)."""
    fake = _stand_in(tmp_path, FG.caps_through("worldwait"))
    logged = []
    fake._mlog = logged.append
    fake._dress_proof()
    heads = [ln.split("[NetSync] ", 1)[1] for ln in logged if "selftest: OK" in ln]
    i = heads.index(BW.proof_ok(BW.PROOF_LEADER_GUARD, BW.LEADER_GUARD_SELFTEST_ROWS))
    assert heads[i + 1:i + 4] == [BW.proof_ok(BW.PROOF_WORLD_FREEZE, 42), BW.proof_ok(BW.PROOF_WORLD_REJOIN, 70),
                                  BW.proof_ok(BW.PROOF_OVERLAY_TEXT, 50)]
    old = _stand_in(tmp_path / "old", FG.caps_through("leaderguard"))
    logged.clear()
    old._mlog = logged.append
    old._dress_proof()
    assert not any(BW.PROOF_WORLD_FREEZE in ln or BW.PROOF_OVERLAY_TEXT in ln for ln in logged)
