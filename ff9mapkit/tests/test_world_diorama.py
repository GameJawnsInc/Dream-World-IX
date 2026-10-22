"""[ff9mapkit netsync s145] BATTLES FROM THE WORLD MAP -- the offline twins of the s145 patch's pure steps, pinned to the live patch
stack (memoria-patches/, read through tests/_patchstack -- no clone, no install). studies/world-coop/S145-DESIGN.md.

A following guest frozen on the world map (s144) boots its battle diorama there when the host fights, and comes back WARM, where it
stood; it never takes a cold world reload (a warm refusal is no boot). Pinned here:

  * THE CAPTURE: the nine files the patch touches (no wire file; fix1 + AllSoundDispatchPlayer.cs, the music-instance witness),
    every hunk tagged, ASCII, the wire v14 and the harness protocol 5, no new [Netsync] ini knob, the replay's default file set
    diagging every one of them.
  * THE CONSTANTS are the engine's: the verdict's 17 rows, their names and the durable mask 0x110BC, Free() and the disqualifier
    table field by field, the kinds, the lever, the over-signal's why, the report's constants, the release lifetime; the harness
    keys (the dio block's sentinels in the catch literal, AppendWorldDio's order, `prev_mode` after `gmode`, the six witness keys
    after `next_mode`) and every accessor reading its sentinel.
  * THE THREE SELFTESTS, row by row: every WdioRow (98, the loop's 34 included) / WWatchRow (59, the report table's 15 and the
    projection loop's 17 included) / the freeze line's 46 FreezeRow the engine's proof block runs has a twin check here that holds
    on battlewire's twins -- an engine row without a twin, or a twin without an engine row, is red; each count is the proof line's.
  * EVERY CHECK CAN FAIL: each pure twin, drifted by one line in memory, turns at least one of those engine rows red.
  * THE CALL SITES a law lives at (a law in a docstring is a wish): the warm pre-verdict before BootFromWire, the loose gMode 3 into
    NoteBootWatch, Boot's world verdict before Arm, Leave's Replace("WorldMap"), never a nextMode 2 write, the boot-time director
    (never WMScriptDirector.Instance), the world-load seam before ff9InitStateWorldMap's StartEvents, the lever released with the
    harness, the `vehicle` verb never forcing. [fix1] ...and the overload trap closed (a dropped `_hostWorld`, a dropped follow or
    ramp input fails to COMPILE: the b6-clear step, the dio follow rule and the closed-bracket settle have their own names), the
    production lines pinned (each pin red on a copy without its line), the leave's stay before the settle, Boot's world-scene
    routing, the epoch / session resets of the watcher's dedup.
  * THE LOG-LINE TWINS the bench judges by (battlewire.log_world_* and the literals) are the patch's own words, piece by piece.
  * THE STAGE LAW: s144's words s145 rewrote (the release's lifetime) are said by the s144 stack and by no live line.
"""
import json
import pathlib
import re
import sys

import pytest

from ._patchstack import msr, net_lines, net_lines_ordered

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from harness import Session                                            # noqa: E402
from harness import battlewire as BW                                   # noqa: E402
from harness import channel as CH                                      # noqa: E402
from harness import fakegame as FG                                     # noqa: E402

PATCH = "s145-netsync-world-battle.patch"
TAG = "[ff9mapkit netsync s145]"
FILES = ("NetSyncDiorama.cs", "NetSyncClient.cs", "NetSyncField.cs", "NetSyncBattle.cs", "HarnessAgent.cs", "Ff9mkDebugMenu.cs",
         "ff9.cs", "WMScriptDirector.cs", "AllSoundDispatchPlayer.cs")              # fix1: + the music-instance witness's getter


def _patch() -> bytes:
    return (msr.PATCHES / PATCH).read_bytes()


def _upto(stem: str) -> list:
    """The live stack's patch bytes up to and including ``stem`` (the agent AT that patch)."""
    out = []
    for name in msr.stack():
        if name in msr.DEAD:
            continue
        out.append((msr.PATCHES / name).read_bytes())
        if name.startswith(stem + "-"):
            return out
    raise AssertionError(f"no live patch {stem}")


def _new_side(file_name: str) -> list:
    """The s145 patch's NEW-side lines for ``file_name``: (hunk, kind, stripped text)."""
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
    """One block of the s145 patch's new side, WHOLE in one hunk (the capture law), from the line starting ``start`` to ``stop``."""
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
    """The selftest's LITERAL-named rows, in file order: every ``<helper>(<expr>, "<name>", ref a, ref b)`` statement's name."""
    code = " ".join(_code(t) for t in _block(file_name, start))
    pat = re.compile(re.escape(helper) + r'\(((?:[^"]|"(?:[^"\\]|\\.)*")*?), "((?:[^"\\]|\\.)*)", ref \w+, ref \w+\);')
    return [m.group(2).replace('\\"', '"') for m in pat.finditer(code)]


def _helper_calls(file_name: str, start: str, helper: str) -> int:
    """How many ``<helper>(`` statements the block runs (a loop's body counted once)."""
    return sum(_code(t).startswith(helper + "(") for t in _block(file_name, start))


def _cs_int(file_name: str, name: str) -> int:
    """A C# integer constant the s145 patch adds (``... name = <n>``, hex or decimal, a `u` suffix allowed)."""
    for line in net_lines(file_name, rf"\b{re.escape(name)} = ", [_patch()]):
        m = re.search(rf"\b{re.escape(name)} = (0x[0-9A-Fa-f]+|-?\d+)u?\b", line)
        if m:
            return int(m.group(1), 0)
    raise AssertionError(f"{name} not in the s145 patch's {file_name}")


# ------------------------------------------------------------------------------------------------ the capture
def test_the_patch_touches_its_nine_files_and_no_wire_file():
    touched = [p.rsplit("/", 1)[-1] for p, _s in msr.sections(_patch()) if p]
    assert tuple(touched) == FILES, touched
    assert not {"NetSyncSocket.cs", "NetSyncRelay.cs", "NetSyncState.cs", "NetSyncParty.cs", "NetSyncDialog.cs"} & set(touched)
    st = msr.stack()
    assert PATCH in st and st.index(PATCH) == st.index("s144-netsync-world-wait.patch") + 1
    defaults = {f.rsplit("/", 1)[-1] for f in msr.DEFAULT_FILES}
    assert set(FILES) <= defaults, set(FILES) - defaults


def test_every_hunk_carries_the_s145_tag_and_stays_ascii():
    text = _patch().decode("utf-8").replace("\r\n", "\n")
    hunks, cur = [], None
    for ln in text.split("\n"):
        if ln.startswith("@@"):
            cur = []
            hunks.append(cur)
        elif cur is not None and ln.startswith("+") and not ln.startswith("+++"):
            cur.append(ln)
    assert len(hunks) >= 60
    assert all(any(TAG in ln for ln in h) for h in hunks), [h[:1] for h in hunks if not any(TAG in ln for ln in h)]
    assert all(ord(c) < 128 for h in hunks for ln in h for c in ln)


def test_the_wire_stays_v14_the_protocol_5_and_no_ini_knob_is_added():
    versions = [ln for ln in net_lines("NetSyncSocket.cs", r".") if ln.startswith("public const Byte Version = ")]
    assert len(versions) == 1 and versions[0].startswith("public const Byte Version = 14;"), versions
    assert net_lines("HarnessAgent.cs", r"public const Int32 ProtocolVersion = ") == ["public const Int32 ProtocolVersion = 5;"]
    for f in FILES:
        assert not net_lines(f, r'GetSetting\("Netsync"', [_patch()]), f
        assert not net_lines(f, r'\[Netsync\]\s+\w+\s*=', [_patch()]), f


# ------------------------------------------------------------------------------------------------ the constants
def test_the_verdicts_rows_names_and_classes_are_the_engines():
    rows = {"WorldRowLive": BW.WORLD_ROW_LIVE, "WorldRowHud": BW.WORLD_ROW_HUD, "WorldRowLeverOff": BW.WORLD_ROW_LEVER_OFF,
            "WorldRowBee": BW.WORLD_ROW_BEE, "WorldRowVehicle": BW.WORLD_ROW_VEHICLE, "WorldRowCtx0": BW.WORLD_ROW_CTX0,
            "WorldRowCtx1": BW.WORLD_ROW_CTX1, "WorldRowReinit": BW.WORLD_ROW_REINIT, "WorldRowLevel": BW.WORLD_ROW_LEVEL,
            "WorldRowResuming": BW.WORLD_ROW_RESUMING, "WorldRowLatch": BW.WORLD_ROW_LATCH,
            "WorldRowFullMap": BW.WORLD_ROW_FULL_MAP, "WorldRowTopograph": BW.WORLD_ROW_TOPOGRAPH,
            "WorldRowDialog": BW.WORLD_ROW_DIALOG, "WorldRowControl": BW.WORLD_ROW_CONTROL, "WorldRowPlayer": BW.WORLD_ROW_PLAYER,
            "WorldRowColdWorld": BW.WORLD_ROW_COLD_WORLD, "WorldRows": BW.WORLD_ROWS}
    new = [t for _h, _k, t in _new_side("NetSyncDiorama.cs")]
    i = next(k for k, t in enumerate(new) if t.startswith("internal const Int32 WorldRowLive = 0"))
    j = next(k for k in range(i, len(new)) if new[k].endswith(";"))
    decl = " ".join(_code(t) for t in new[i:j + 1])
    got = {n: int(v) for n, v in re.findall(r"(WorldRow\w+) = (\d+)", decl)}
    assert got == rows, got
    names = " ".join(_code(t) for t in _block("NetSyncDiorama.cs", "private static readonly String[] WorldRowNames", "};"))
    assert tuple(re.findall(r'"([^"]+)"', names)) == BW.WORLD_ROW_NAMES and len(BW.WORLD_ROW_NAMES) == BW.WORLD_ROWS == 17
    mask = " ".join(_code(t) for t in _block("NetSyncDiorama.cs", "internal const UInt32 WorldDurableRows", "internal static Boolean WorldRowDurable(Int32 row)"))
    terms = re.findall(r"1u << WorldRow(\w+)", mask)
    assert sum(1 << rows["WorldRow" + t] for t in terms) == BW.WORLD_DURABLE_ROWS == 0x110BC == BW.world_durable_mask()
    for name, value in (("KindNone", BW.KIND_NONE), ("KindField", BW.KIND_FIELD), ("KindWorld", BW.KIND_WORLD),
                        ("WorldWarmOn", BW.WORLD_WARM_ON), ("WorldWarmOff", BW.WORLD_WARM_OFF),
                        ("WorldWarmCold", BW.WORLD_WARM_COLD), ("WorldWarmColdWorld", BW.WORLD_WARM_COLD_WORLD)):
        assert _cs_int("NetSyncDiorama.cs", name) == value, name
    loads = " ".join(t for _h, _k, t in _new_side("NetSyncDiorama.cs") if t.startswith("internal const Int32 ReturnLoadNone"))
    assert re.findall(r"(ReturnLoad\w+) = (\d)", loads) == [("ReturnLoadNone", "0"), ("ReturnLoadOurs", "1"),
                                                             ("ReturnLoadMismatch", "2")]
    assert (BW.RETURN_LOAD_NONE, BW.RETURN_LOAD_OURS, BW.RETURN_LOAD_MISMATCH) == (0, 1, 2)


def _struct_assigns(lines, var: str) -> dict:
    """``<var>.Field = value;`` / ``<var>[Row].Field = value;`` statements -> {(row|None, snake field): python value}."""
    out = {}
    for t in lines:
        m = re.match(rf"{re.escape(var)}(?:\[(?:NetSyncDiorama\.)?(\w+)\])?\.(\w+) = (.+);$", _code(t))
        if not m:
            continue
        raw = m.group(3).strip()
        val = (None if raw == "null" else True if raw == "true" else False if raw == "false" else
               raw.strip('"') if raw.startswith('"') else
               {"WorldWarmOn": 0, "WorldWarmOff": 1, "WorldWarmCold": 2, "WorldWarmColdWorld": 9011,
                "NetSyncDiorama.WorldWarmOff": 1, "NetSyncDiorama.WorldWarmCold": 2}.get(raw, None if not raw.lstrip("-").isdigit()
                                                                                       else int(raw)))
        out[(m.group(1), BW.WORLD_WARM_CS_FIELDS[m.group(2)])] = val
    return out


def test_free_and_the_disqualifiers_are_the_engines_field_for_field():
    free = _struct_assigns(_block("NetSyncDiorama.cs", "internal static WorldWarmIn Free()", "return w;"), "w")
    assert {k: v for (_r, k), v in free.items()} == BW.WORLD_WARM_FREE
    assert set(BW.WORLD_WARM_CS_FIELDS.values()) == set(BW.WORLD_WARM_FREE)
    rows = {n: getattr(BW, "WORLD_ROW_" + re.sub(r"(?<!^)(?=[A-Z])", "_", n[8:]).upper()) for n in
            ("WorldRowLive", "WorldRowHud", "WorldRowLeverOff", "WorldRowBee", "WorldRowVehicle", "WorldRowCtx0", "WorldRowCtx1",
             "WorldRowReinit", "WorldRowLevel", "WorldRowResuming", "WorldRowLatch", "WorldRowFullMap", "WorldRowTopograph",
             "WorldRowDialog", "WorldRowControl", "WorldRowPlayer", "WorldRowColdWorld")}
    for file_name, start, end in (("NetSyncDiorama.cs", "private static WorldWarmIn[] WorldWarmDisqualifiers()", "return dq;"),
                                  ("NetSyncClient.cs", "private static NetSyncDiorama.WorldWarmIn[] WorldWatchDisqualifiers()",
                                   "return dq;")):
        dq = [BW.world_warm_in() for _ in range(BW.WORLD_ROWS)]
        for (row, field), v in _struct_assigns(_block(file_name, start, end), "dq").items():
            dq[rows[row]][field] = v
        assert dq == BW.world_warm_disqualifiers(), file_name


def test_the_verdicts_words_are_the_engines():
    """Every row's refusal (each disqualifier alone, and the live row's other two forms) is the engine's own sentence: its
    literal pieces, in order, in WorldWarmRow's body."""
    body = " ".join(_code(t) for t in _block("NetSyncDiorama.cs", "private static String WorldWarmRow(", "row = -1;"))
    lits = re.findall(r'"((?:[^"\\]|\\.)*)"', body)
    flat = "\0".join(lits)
    for i, w in enumerate(BW.world_warm_disqualifiers()):
        why, row = BW.world_warm_row(w)
        assert row == i and why
        pieces = [p for p in re.split(r"\b(?:9011|9002|6|1|3|a fade is in flight)\b", why) if p.strip()]
        assert all(p in flat or any(p in lit for lit in lits) for p in pieces), (i, why, pieces)
    assert BW.world_warm_row(BW.world_warm_in(world_scene=False))[0] == "not on the live world map (mode 3, gMode 3, another scene)"


def test_the_harness_keys_are_the_agents_and_every_accessor_reads_its_sentinel():
    lit = net_lines("HarnessAgent.cs", r'outer\.Append\("\\"netsync\\":\{\\"enabled')[0].replace('\\"', '"')
    esc = lambda d: json.dumps(d, separators=(",", ":"))                 # noqa: E731
    assert lit.endswith(f'"waitline":{esc(BW.WORLD_WAITLINE_SENTINELS)},"dio":{esc(BW.WORLD_DIO_SENTINELS)}}}}}");')
    assert lit.endswith(f'"world":{esc(BW.WORLD_SENTINELS)}}}");') and list(BW.WORLD_SENTINELS)[-1] == "dio"
    assert _catch(_upto("s144")).endswith(f'"world":{esc(BW.WORLD_SENTINELS_S144)}}}");')       # the s144 stage, frozen
    dio = " ".join(_code(t) for t in _block("HarnessAgent.cs", "private static void AppendWorldDio(StringBuilder sb)", 'sb.Append("}");'))
    assert re.findall(r'(?:Bool|Num|Str)\(sb, "(\w+)"', dio) == list(BW.WORLD_DIO_SENTINELS), dio
    wit = " ".join(_code(t) for t in _block("HarnessAgent.cs", "private static void AppendWorldWarmWitness(", "}"))
    assert re.findall(r'(?:Num|Str)\(sb, "(\w+)"', wit) == list(BW.WORLD_WITNESS_SENTINELS)
    live = " ".join(net_lines("HarnessAgent.cs", r'Num\(sb, "(phase|next_mode)"|AppendWorldWarmWitness\(sb, live\)'))
    assert live.index('"next_mode"') < live.index("AppendWorldWarmWitness(sb, live)")
    state = [t for t in net_lines("HarnessAgent.cs", r'Num\(sb, "(gmode|prev_mode)"')]
    assert len(state) == 2 and "gmode" in state[0] and "prev_mode" in state[1]
    # the accessors: every dio leaf one (NETSYNC_WORLD_ACCESSORS), each reading its sentinel; absent on an s144 block
    table = {p: n for p, n in CH.State.NETSYNC_WORLD_ACCESSORS.items() if p.split(".")[0] == "dio"}
    assert set(table) == {"dio"} | {f"dio.{k}" for k in BW.WORLD_DIO_SENTINELS}
    st = CH.State({"frame": 1, "netsync": {"world": json.loads("{" + f'"dio":{esc(BW.WORLD_DIO_SENTINELS)}' + "}")}})
    for path, name in table.items():
        got = getattr(st, name)
        want = BW.WORLD_DIO_SENTINELS if path == "dio" else BW.WORLD_DIO_SENTINELS[path[4:]]
        assert (got == "" if want is None else got == want and type(got) is type(want)), (path, got, want)
    assert st.coop_world_dio is True
    old = CH.State({"frame": 1, "netsync": {"world": dict(BW.WORLD_SENTINELS_S144)}})
    assert old.coop_world_dio is False and all(getattr(old, n) is None for n in table.values())
    assert CH.State({"frame": 1}).coop_world_dio is None
    w = CH.State({"frame": 1, "prev_mode": 3, "world": {"id": 9011, "cam_rot": 56.25, "cam_upper": 2048, "ctl": 1,
                                                       "battle_prob": 231, "ticks": 120, "mapvar": "00" * 80}})
    assert (w.prev_mode, w.world_cam_rot, w.world_cam_upper, w.world_ctl, w.world_battle_prob, w.world_ticks, w.world_mapvar) == \
        (3, 56.25, 2048, 1, 231, 120, "00" * 80)
    off = CH.State({"frame": 1, "world": dict({"id": 9011}, **BW.WORLD_WITNESS_SENTINELS)})
    assert (off.world_cam_rot, off.world_cam_upper, off.world_ctl, off.world_mapvar) == (None, -1, -1, None)
    none = CH.State({"frame": 1, "world": {"id": 9011}})
    assert all(getattr(none, n) is None for n in ("prev_mode", "world_cam_rot", "world_cam_upper", "world_ctl",
                                                   "world_battle_prob", "world_ticks", "world_mapvar"))
    assert BW.mapvar_hex(bytes(range(80)))[:8] == "00010203" and len(BW.mapvar_hex(bytes(80))) == 160


def _catch(patches) -> str:
    lines = net_lines("HarnessAgent.cs", r'outer\.Append\("\\"netsync\\":\{\\"enabled', patches)
    assert len(lines) == 1, lines
    return lines[0].replace('\\"', '"')


def test_the_lever_the_vehicle_verb_and_the_dioboot_gate_say_the_engines_words():
    agent = " ".join(_code(t) for _h, _k, t in _new_side("HarnessAgent.cs"))
    assert "HarnessBenchWorldWarm(s.Args.Length == 3 ? s.Args[2] : \"\", out why)" in agent
    dio = " ".join(_code(t) for _h, _k, t in _new_side("NetSyncDiorama.cs"))
    for words in (BW.WORLD_WARM_EXPECTED, BW.WORLD_WARM_BENCH_REFUSAL):
        assert json.dumps(words) in dio, words
    lits = re.findall(r'"((?:[^"\\]|\\.)*)"', dio)
    assert '"[NetSync] harness: world warm gate "' in dio
    for line in (BW.LOG_WORLD_WARM_OFF, BW.LOG_WORLD_WARM_ON):
        assert line.split("harness: world warm gate ", 1)[1] in lits, line
    assert "[NetSync] " + BW.LOG_WORLD_WARM_RELEASED in lits
    cold = BW.LOG_WORLD_WARM_COLD.split("harness: world warm gate ", 1)[1].split(str(BW.WORLD_WARM_COLD_WORLD))
    assert cold[0] in lits and cold[1] in lits, cold
    assert BW.vehicle_usage(["x", "y"]) == "expected `vehicle <mode>` (0 on foot, 1-6 chocobo, 7 boat, 8-9 airship), got 'x y'"
    assert '"expected `vehicle <mode>` (0 on foot, 1-6 chocobo, 7 boat, 8-9 airship), got \'"' in agent
    menu = " ".join(_code(t) for _h, _k, t in _new_side("Ff9mkDebugMenu.cs"))
    for why in ("overworld only", "the bee scene has no vehicles", "the world is still loading"):
        assert json.dumps(why) in menu, why
    assert BW.harness_vehicle_refusal(True, 1, False, True, None) == "not in world mode (1)" and '"not in world mode ("' in menu
    assert BW.harness_vehicle_refusal(True, 3, False, True, "x") == "a world transition is in flight (x)"
    assert "return _instance.SetVehicle(mode, false);" in menu and "SetVehicle(mode, _vehicleForceAll);" in menu
    assert dict(BW.VEHICLE_ALLOW_BY_WORLD) == {9002: 0x3FF, 9010: 0x3FF, 9011: 0x3FF}
    assert BW.vehicle_status(1, 9011)[0] and not BW.vehicle_status(1, 9000)[0] and not BW.vehicle_status(10, 9011)[0]
    gate = " ".join(_code(t) for t in _block("HarnessAgent.cs", 'case "dioboot":', 'case "host":'))
    assert '"netsync dioboot: the world map is not on WorldHUD (ui_state "' in gate
    assert '"netsync dioboot: a world transition is in flight ("' in gate
    assert BW.dioboot_world_refusal("WorldHUD", None) is None and BW.dioboot_world_refusal("MainMenu", None).startswith(
        "netsync dioboot: the world map is not on WorldHUD (ui_state MainMenu)")
    # s144's refusal text kept verbatim for any other scene (the stage law: never reworded)
    assert json.dumps(BW.DIOBOOT_FIELD_ONLY)[1:-1] in " ".join(net_lines("HarnessAgent.cs", r"boots from a live field only"))


# ------------------------------------------------------------------------------------------------ the selftests, row by row
E = BW
_FREE = E.world_warm_in


def _x(**kw):
    return E.world_warm_in(**kw)


def _verdict(**kw):
    return E.world_warm_verdict(_x(**kw))


def _row(**kw):
    return E.world_warm_row(_x(**kw))


_BOOTED_LATCH = E.world_latch_step(True, 3, 0, 3, False, True, False, False)
WDIO_ROWS = {
    "the free row (on foot on world 9011, WorldHUD, nothing in flight) boots warm": lambda: E.world_warm_verdict(_FREE()) == (None, False),
    "every row is named": lambda: len(E.WORLD_ROW_NAMES) == E.WORLD_ROWS,
    "durable = the lever off, the bee scene, a vehicle, a foreign context, no Main_Reinit, topograph 52, the cold reference off 9011 (0x110BC)": lambda: E.world_durable_mask() == 0x110BC,
    "no row outside the table is durable": lambda: not E.world_row_durable(-1) and not E.world_row_durable(E.WORLD_ROWS),
    "live: mode 1 (the world handing over to a field) refuses": lambda: _row(sys_mode=1)[1] == E.WORLD_ROW_LIVE,
    "live: gMode 3 on another scene (a world-booted diorama, the world -> field load) waits": lambda: (
        _row(world_scene=False)[1] == E.WORLD_ROW_LIVE and _verdict(world_scene=False)[0] is not None and not _verdict(world_scene=False)[1]),
    "ctx0: a field's context (inited 1) is not this world's (durable)": lambda: _row(ctx0_inited=1)[1] == E.WORLD_ROW_CTX0 and _verdict(ctx0_inited=1)[1],
    "a chocobo (travel mode 1) declines for the visit: vehicles decline (decision 4)": lambda: _verdict(travel_mode=1)[0] is not None and _verdict(travel_mode=1)[1],
    "an event world (no tag 10) declines for the visit": lambda: _verdict(has_reinit=False)[0] is not None and _verdict(has_reinit=False)[1],
    "the bee scene declines for the visit": lambda: _verdict(bee_scene=True)[0] is not None and _verdict(bee_scene=True)[1],
    "control off is a quiet wait": lambda: _verdict(control=False)[0] is not None and not _verdict(control=False)[1],
    "a dialogue is a quiet wait": lambda: _verdict(dialogs=True)[0] is not None and not _verdict(dialogs=True)[1],
    "the full map is a quiet wait": lambda: _verdict(full_map=True)[0] is not None and not _verdict(full_map=True)[1],
    "a reinit bracket still open is a quiet wait": lambda: _verdict(resuming=True)[0] is not None and not _verdict(resuming=True)[1],
    "a transition in flight is a quiet wait": lambda: (
        _verdict(latch_why="the world rejoin is armed")[0] is not None and not _verdict(latch_why="the world rejoin is armed")[1]),
    "latch (booted false): free on the quiet world map": lambda: E.world_latch_no_boot(True, 3, 0, 3, False, False, False) is None,
    "...where s144's latch with booted true reads busy ('a diorama is booted')": lambda: _BOOTED_LATCH is not None,
    "mutant: a verdict fed the booted latch refuses every world boot (inside Boot _booted is true)": lambda: (
        _row(latch_why=E.world_latch_step(True, 3, 0, 3, False, True, False, False))[1] == E.WORLD_ROW_LATCH),
    "latch keeps nextMode 2 (a battle starting) and 1 (a field entry)": lambda: (
        E.world_latch_no_boot(True, 3, 0, 2, False, False, False) is not None and E.world_latch_no_boot(True, 3, 0, 1, False, False, False) is not None),
    "latch keeps a world shutdown armed and a fade": lambda: (
        E.world_latch_no_boot(True, 3, 0x1000, 3, False, False, False) is not None and E.world_latch_no_boot(True, 3, 0, 3, True, False, False) is not None),
    "latch keeps a battle return in flight and the world rejoin armed": lambda: (
        E.world_latch_no_boot(True, 3, 0, 3, False, True, False) is not None and E.world_latch_no_boot(True, 3, 0, 3, False, False, True) is not None),
    "latch fails closed off the live world map and while the world hands over": lambda: (
        E.world_latch_no_boot(False, 3, 0, 3, False, False, False) is not None and E.world_latch_no_boot(True, 1, 0, 3, False, False, False) is not None),
    "lever: off the selftest role it reads on (production never boots cold)": lambda: (
        E.world_warm_lever_for(False, E.WORLD_WARM_COLD) == E.WORLD_WARM_ON and E.world_warm_lever_for(False, E.WORLD_WARM_OFF) == E.WORLD_WARM_ON),
    "lever: on the selftest role it reads the bench (garbage reads on)": lambda: (
        E.world_warm_lever_for(True, E.WORLD_WARM_COLD) == E.WORLD_WARM_COLD and E.world_warm_lever_for(True, E.WORLD_WARM_OFF) == E.WORLD_WARM_OFF
        and E.world_warm_lever_for(True, 7) == E.WORLD_WARM_ON),
    "lever: off|cold|on parse, nothing else": lambda: (
        E.parse_world_warm_lever("off") == E.WORLD_WARM_OFF and E.parse_world_warm_lever(" COLD ") == E.WORLD_WARM_COLD
        and E.parse_world_warm_lever("on") == E.WORLD_WARM_ON and E.parse_world_warm_lever("warm") < 0 and E.parse_world_warm_lever(None) < 0),
    "lever: the selftest role only": lambda: (
        E.world_warm_bench_refusal(True, E.WORLD_WARM_COLD) is None and E.world_warm_bench_refusal(False, E.WORLD_WARM_COLD) is not None
        and E.world_warm_bench_refusal(True, -1) is not None),
    "lever: its names": lambda: [E.world_warm_lever_name(v) for v in (E.WORLD_WARM_OFF, E.WORLD_WARM_COLD, E.WORLD_WARM_ON)] == ["off", "cold", "on"],
    "lever cold: boots on world 9011 (the cold reference)": lambda: _verdict(lever=E.WORLD_WARM_COLD)[0] is None,
    "lever cold: on foot only": lambda: _verdict(lever=E.WORLD_WARM_COLD, travel_mode=1)[0] is not None and _verdict(lever=E.WORLD_WARM_COLD, travel_mode=1)[1],
    "lever off: a durable decline (NONE, never a cold return)": lambda: _verdict(lever=E.WORLD_WARM_OFF)[0] is not None and _verdict(lever=E.WORLD_WARM_OFF)[1],
    "kinds are the consuming load's gMode (field 1, world 3)": lambda: E.KIND_FIELD == 1 and E.KIND_WORLD == 3,
    "return: a world copy on its own world, mode 3, is ours": lambda: E.return_is_ours(True, E.KIND_WORLD, 9011, E.KIND_WORLD, 9011, 3),
    "return: ...not on another world": lambda: not E.return_is_ours(True, E.KIND_WORLD, 9011, E.KIND_WORLD, 9002, 3),
    "return: ...nor at a field load (a stale inited-3 copy there re-adds every actor)": lambda: not E.return_is_ours(True, E.KIND_WORLD, 9011, E.KIND_FIELD, 9011, 1),
    "return: a field copy at a world load is never ours": lambda: not E.return_is_ours(True, E.KIND_FIELD, 100, E.KIND_WORLD, 100, 3),
    "return: the KIND refuses a foreign copy even where the mode and the id agree with it": lambda: (
        not E.return_is_ours(True, E.KIND_WORLD, 100, E.KIND_FIELD, 100, 3) and not E.return_is_ours(True, E.KIND_FIELD, 100, E.KIND_WORLD, 100, 1)),
    "return: ...nor a copy with no return pending": lambda: not E.return_is_ours(False, E.KIND_WORLD, 9011, E.KIND_WORLD, 9011, 3),
    "return: ...nor a world load in mode 1": lambda: not E.return_is_ours(True, E.KIND_WORLD, 9011, E.KIND_WORLD, 9011, 1),
    "return: no copy is never ours": lambda: (
        not E.return_is_ours(True, E.KIND_NONE, -1, E.KIND_WORLD, -1, 3) and not E.return_is_ours(True, E.KIND_NONE, -1, E.KIND_NONE, -1, 0)),
    "return: the field rows are F3.3's": lambda: (
        E.return_is_ours_field(True, 100, 100, 1) and not E.return_is_ours_field(False, 100, 100, 1)
        and not E.return_is_ours_field(True, 100, 101, 1) and not E.return_is_ours_field(True, 100, 100, 3)),
    "mutant: s144's field-only test undoes a world copy at its own world load (the return goes cold)": lambda: (
        not (lambda p, warm, fld, mode: p and fld == warm and mode == 1)(True, 9011, 9011, 3)
        and E.return_is_ours(True, E.KIND_WORLD, 9011, E.KIND_WORLD, 9011, 3)),
    "mutant: a kind-blind test claims a field copy at a world load": lambda: (
        (lambda p, k, i, lk, li, m: p and i == li and m == lk)(True, E.KIND_FIELD, 100, E.KIND_WORLD, 100, 3)
        and not E.return_is_ours(True, E.KIND_FIELD, 100, E.KIND_WORLD, 100, 3)),
    "consume: a world return is counted on its own world load": lambda: E.return_load_step(True, E.KIND_WORLD, 3) == E.RETURN_LOAD_OURS,
    "consume: ...a field load first takes it with the mismatch line (counted once)": lambda: E.return_load_step(True, E.KIND_WORLD, 1) == E.RETURN_LOAD_MISMATCH,
    "consume: a battle's StartEvents never takes it": lambda: (
        E.return_load_step(True, E.KIND_WORLD, 2) == E.RETURN_LOAD_NONE and E.return_load_step(True, E.KIND_FIELD, 4) == E.RETURN_LOAD_NONE),
    "consume: a field return on its field load (F3.3), a world load first is a mismatch": lambda: (
        E.return_load_step(True, E.KIND_FIELD, 1) == E.RETURN_LOAD_OURS and E.return_load_step(True, E.KIND_FIELD, 3) == E.RETURN_LOAD_MISMATCH),
    "consume: nothing pending, nothing taken": lambda: (
        E.return_load_step(False, E.KIND_WORLD, 3) == E.RETURN_LOAD_NONE and E.return_load_step(False, E.KIND_FIELD, 1) == E.RETURN_LOAD_NONE),
    "mutant: s144's gMode-1-only rule leaves a world return pending past its own load (counted on the rejoin's field)": lambda: (
        not (lambda p, gm: p and gm == 1)(True, 3) and E.return_load_step(True, E.KIND_WORLD, 3) == E.RETURN_LOAD_OURS),
    # [fix1] THE LEAVE's stay (WorldLeaveStays)
    "leave: the boot's own WorldMap still alive stays (its Replace never started)": lambda: (
        E.world_leave_stays(True, "WorldMap") and E.world_leave_stays(True, "SwirlScene")),
    "leave: a live WorldMap the boot already returned to stays (a Replace there is a cold world reload)": lambda: (
        E.world_leave_stays(False, "WorldMap")),
    "leave: from SwirlScene or BattleMapDebug, the boot's world gone, it Replaces (the warm return)": lambda: (
        not E.world_leave_stays(False, "SwirlScene") and not E.world_leave_stays(False, "BattleMapDebug")
        and not E.world_leave_stays(False, None)),
    "mutant: the boot-director-only stay Replaces from a live WorldMap the boot returned to (a cold world reload, each release retry)": lambda: (
        not (lambda alive, scene: alive)(False, "WorldMap") and E.world_leave_stays(False, "WorldMap")),
    # [fix4] THE PASSIVE PROMPTS (WorldWindowBusy / WorldWindowsBusy: the verdict's Dialogs input)
    "prompts: the entrance tile's two [NFOC] prompts are no dialogue -- the guest boots there, warm": lambda: (
        not E.world_windows_busy([E.WORLD_PROMPT_WINDOW] * 2, E.world_window_busy)
        and _verdict(dialogs=E.world_windows_busy([E.WORLD_PROMPT_WINDOW] * 2, E.world_window_busy)) == (None, False)),
    "prompts: no window is no dialogue": lambda: not E.world_windows_busy([], E.world_window_busy),
    "prompts: a focus-taking line (a talk, no [NFOC]) is busy": lambda: E.world_window_busy(True, False, False, True),
    "prompts: a choice is busy, an input-inhibited (script-polled) one too": lambda: E.world_window_busy(True, True, True, True),
    "prompts: a UI dialog (the full map's navigate prompt, a menu popup) is busy, [NFOC] or not": lambda: (
        E.world_window_busy(False, True, False, True) and E.world_window_busy(False, False, False, True)),
    "prompts: a window not fully shown (opening or closing: its tags maybe unparsed) is busy": lambda: (
        E.world_window_busy(True, True, False, False)),
    "prompts: a talk beside the two prompts refuses at the dialogue row, a quiet wait": lambda: (
        E.world_windows_busy([E.WORLD_PROMPT_WINDOW, (True, False, False, True), E.WORLD_PROMPT_WINDOW], E.world_window_busy)
        and _row(dialogs=E.world_windows_busy([E.WORLD_PROMPT_WINDOW, (True, False, False, True), E.WORLD_PROMPT_WINDOW],
                                              E.world_window_busy))[1] == E.WORLD_ROW_DIALOG
        and _verdict(dialogs=True)[0] is not None and not _verdict(dialogs=True)[1]),
    "prompts: an unreadable window list is busy": lambda: E.world_windows_busy(None, E.world_window_busy),
    "mutant: Dialogs.Visible reads the entrance tile's prompts busy -- the guest every field exit lands there waits out the fight": lambda: (
        E.world_windows_busy([E.WORLD_PROMPT_WINDOW] * 2, lambda sl, ih, ch, sh: True)
        and not E.world_windows_busy([E.WORLD_PROMPT_WINDOW] * 2, E.world_window_busy)),
    "mutant: an [NFOC]-only rule boots under a script-polled choice": lambda: (
        not (lambda sl, ih, ch, sh: not ih)(True, True, True, True) and E.world_window_busy(True, True, True, True)),
    "mutant: a script-blind rule boots under an [NFOC] UI dialog": lambda: (
        not (lambda sl, ih, ch, sh: not ih or ch or not sh)(False, True, False, True) and E.world_window_busy(False, True, False, True)),
    "mutant: a shown-blind rule boots under a window still opening (its choice not yet parsed)": lambda: (
        not (lambda sl, ih, ch, sh: not sl or not ih or ch)(True, True, False, False) and E.world_window_busy(True, True, False, False)),
}


def _wdio_loop_rows() -> dict:
    """The selftest's loop: for each of the 17 rows, its disqualifier alone refuses THERE, and the verdict without that row boots
    it (one mutant per row: no row shadowed by another)."""
    out = {}
    for i, w in enumerate(E.world_warm_disqualifiers()):
        n = E.WORLD_ROW_NAMES[i]
        out[f"row {i} ({n}): its disqualifier alone refuses there"] = (
            lambda w=w, i=i: E.world_warm_row(w)[0] is not None and E.world_warm_row(w)[1] == i)
        out[f"mutant: without row {i} ({n}) its disqualifier boots"] = lambda w=w, i=i: E.world_warm_row(w, i) == (None, -1)
    return out


def _wdio_rows_in_order() -> dict:
    """All 98 rows in the engine's order: the two literal rows before the loop, the loop's 34, then the 62 after it."""
    lit = list(WDIO_ROWS.items())
    return dict(lit[:2] + list(_wdio_loop_rows().items()) + lit[2:])


def test_every_world_diorama_selftest_row_has_a_twin_that_holds():
    names = _row_names("NetSyncDiorama.cs", "internal static Boolean WorldDioramaSelfTest(", "WdioRow")
    assert names == list(WDIO_ROWS), [n for n in names if n not in WDIO_ROWS] + ["--"] + [n for n in WDIO_ROWS if n not in names]
    # the loop body's two rows run once per row (17 x 2); every other statement once
    assert _helper_calls("NetSyncDiorama.cs", "internal static Boolean WorldDioramaSelfTest(", "WdioRow") == len(names) + 2
    rows = _wdio_rows_in_order()
    assert len(rows) == BW.WORLD_DIORAMA_SELFTEST_ROWS == 98
    code = " ".join(_code(t) for t in _block("NetSyncDiorama.cs", "internal static Boolean WorldDioramaSelfTest(", "catch (Exception err)"))
    assert 'WdioRow(WorldWarmRow(dq[i], -1, out r) != null && r == i, "row " + i + " (" + WorldRowNames[i] + "): its disqualifier alone refuses there"' in code
    assert 'WdioRow(WorldWarmRow(dq[i], i, out r) == null && r == -1, "mutant: without row " + i + " (" + WorldRowNames[i] + ") its disqualifier boots"' in code
    assert code.index('"every row is named"') < code.index("for (Int32 i = 0; i < WorldRows; i++)") < code.index("0x110BCu")
    failed = [name for name, check in rows.items() if check() is not True]
    assert not failed, failed


# ---- the world watcher selftest (NetSyncClient.WorldWatchSelfTest)
_U = {"WUiField": E.WREPORT_UI_FIELD, "WUiWorld": E.WREPORT_UI_WORLD, "WUiOther": E.WREPORT_UI_OTHER}
_BOOT = {"NetSyncBattle.BootNone": E.BOOT_NONE, "NetSyncBattle.BootBooting": E.BOOT_BOOTING, "NetSyncBattle.BootLive": E.BOOT_LIVE,
         "NetSyncBattle.BootDeclined": E.BOOT_DECLINED, "NetSyncBattle.BootBusy": E.BOOT_BUSY}


def _report_cases() -> list:
    """WorldReportCases, parsed off the s145 patch's table (every WCase line) -- the engine's scenarios, run through the twins."""
    block = _block("NetSyncClient.cs", "private static WReportCase[] WorldReportCases()", "};")
    v = next(re.search(r'const String V = "([^"]+)";', t).group(1) for t in block if t.startswith("const String V = "))
    env = {"N": E.WREPORT_NONCE, "No": -1, "V": v, "null": None, "true": True, "false": False, "WTestStartLoop": E.WORLD_START_LOOP,
           **_U, **_BOOT}
    cases = []
    for t in block:
        m = re.match(r'WCase\("((?:[^"\\]|\\.)*)", (.*)\),?$', _code(t))
        if not m:
            continue
        args = [a.strip() for a in m.group(2).split(",")]
        vals = [env[a] if a in env else int(a) if re.fullmatch(r"-?\d+", a) else
                eval(a, {}, {k: x for k, x in env.items() if isinstance(x, int)}) for a in args]   # noqa: S307 (N - 1, WTestStartLoop + 1)
        cases.append(dict(zip(E.WREPORT_FIELDS, [m.group(1)] + vals)))
    return cases


def _misses(watch=None, ui=None, skip=False) -> int:
    return sum(E.world_report_at(c, watch, ui, skip) != c["want"] for c in _report_cases())


_WATCH = lambda f, w, o, d: E.boot_watching(True, True, f, w, True, d)              # noqa: E731
_UI = lambda h, m, o, k: E.world_ui_free(h, m, o, k, E.WORLD_START_LOOP)            # noqa: E731
_BEHIND = E.world_warm_in(world_hud=False, travel_mode=6)
_EVT = E.world_warm_in(world=9001, ctx0_lastmap=9001, has_reinit=False)
_BUSY = E.world_warm_in(sys_mode=1, world_hud=False, ctx1_inited=3, main_level=0, resuming=True, latch_why="a fade is in flight",
                        full_map=True, dialogs=True, control=False, player=False)      # (fix1: no topograph 52 -- durable now)


def _latch(**kw):
    a = dict(live=True, mode=3, attr=0, nxt=3, fade=False, booted=False, ret=False, armed=False)
    a.update(kw)
    return E.world_latch_step(a["live"], a["mode"], a["attr"], a["nxt"], a["fade"], a["booted"], a["ret"], a["armed"])


WWATCH_ROWS = {
    "report: a host, a non-follower or a session that may not boot watches nothing": lambda: (
        not E.boot_watching(False, True, True, False, True, None) and not E.boot_watching(True, False, True, False, True, None)
        and not E.boot_watching(True, True, True, False, False, None) and not E.boot_watching(True, True, False, True, False, None)),
    "mutant: s144's watching (a field only) reads the world map NONE -- the host's start hold never arms": lambda: _misses(lambda f, w, o, d: f, _UI) > 0,
    "mutant: the strict onWorld reads fight 2 NONE from inside a world-booted diorama": lambda: (
        _misses(lambda f, w, o, d: E.boot_watching(True, True, f, o, True, d), _UI) > 0),
    "mutant: no construct frames reads them BUSY (an armed hold released for good)": lambda: _misses(_WATCH, lambda h, m, o, k: h and not m) > 0,
    "mutant: the full map free reads it BOOTING (the host holds on a guest that cannot boot)": lambda: (
        _misses(_WATCH, lambda h, m, o, k: E.world_ui_free(h, False, o, k, E.WORLD_START_LOOP)) > 0),
    "mutant: a durable decline stamped as the skip reads DECLINED": lambda: _misses(_WATCH, _UI, True) > 0,
    "mutant: a decline that keeps watching reads BOOTING (the host holds every such fight to its cap)": lambda: (
        _misses(lambda f, w, o, d: E.boot_watching(True, True, f, w, True, None), _UI) > 0),
    "ownership: NONE keeps s144's digit-panel slots; DECLINED would hand them to the host's ready loop": lambda: (
        E.guest_owns_from_report(True, E.WREPORT_NONCE, E.BOOT_NONE, E.WREPORT_NONCE, False)
        and not E.guest_owns_from_report(True, E.WREPORT_NONCE, E.BOOT_DECLINED, E.WREPORT_NONCE, False)),
    "projection: the free world declines nothing": lambda: len(E.world_warm_disqualifiers()) == E.WORLD_ROWS and E.world_decline_why(E.world_warm_in()) is None,
    "projection: a vehicle behind the construct frames still declines": lambda: E.world_decline_why(_BEHIND) is not None,
    "mutant: the full verdict as the projection reads it transient -- BOOTING first, then NONE (dioramaSeen up, the slots gone)": lambda: (
        E.world_warm_verdict(_BEHIND)[0] is not None and not E.world_warm_verdict(_BEHIND)[1]),
    "projection: an event world (9001, no tag 10) declines, naming it": lambda: "Main_Reinit" in (E.world_decline_why(_EVT) or ""),
    "projection: every transient input bad at once declines nothing": lambda: E.world_decline_why(_BUSY) is None,
    "follow: the world map compares against no field (s144)": lambda: E.follow_field_for_dio(True, False, False, 300) == -1,
    "follow: a world-booted diorama compares against no field (the departed field never reads arrived)": lambda: E.follow_field_for_dio(False, True, False, 300) == -1,
    "follow: a world return still pending (torn down, the world not loaded yet) compares against no field": lambda: (
        E.follow_field_for_dio(False, False, True, 300) == -1),
    "follow: a field and a field-booted diorama keep fldMapNo (F3.3 unchanged)": lambda: E.follow_field_for_dio(False, False, False, 300) == 300,
    "mutant: s144's follow field inside a world-booted diorama reads the departed field (the host there 'arrived')": lambda: (
        E.follow_field_for(False, 300) != E.follow_field_for_dio(False, True, False, 300)),
    "mutant: the booted-only rule reads the departed field between the teardown and the world load (the host there 'arrived')": lambda: (
        (lambda o, b, p, f: E.follow_field_for(o or b, f))(False, False, True, 300) == 300
        and E.follow_field_for_dio(False, False, True, 300) == -1),
    "ramp: the free world map is safe (s144)": lambda: _latch() is None and E.ramp_world_safe(True, _latch(), False),
    "ramp: the reinit bracket alone is safe, never settled (the bound)": lambda: (
        _latch(ret=True) is not None and E.ramp_world_safe(True, _latch(ret=True), True)
        and not E.ramp_world_settled_closed(False, True, True) and not E.ramp_world_settled_closed(True, True, True)),
    "ramp: the bracket closed, s144's settle (a free-roam world at once, an event world with control on)": lambda: (
        E.ramp_world_settled_closed(False, False, False) and E.ramp_world_settled_closed(True, True, False)
        and not E.ramp_world_settled_closed(True, False, False)),
    "mutant: a resuming-blind settle reloads the save on a warm return's first frame (every object still suspended)": lambda: (
        (lambda e, c, r: E.ramp_world_settled(e, c))(False, True, True) and not E.ramp_world_settled_closed(False, True, True)),
    "ramp: a fade, a booted diorama, the rejoin armed or a battle starting stay unsafe": lambda: (
        not E.ramp_world_safe(True, _latch(fade=True, ret=True), False) and not E.ramp_world_safe(True, _latch(booted=True, ret=True), False)
        and not E.ramp_world_safe(True, _latch(armed=True), False) and not E.ramp_world_safe(True, _latch(nxt=2), False)),
    "ramp: off the live world map, never": lambda: not E.ramp_world_safe(False, _latch(live=False), False) and not E.ramp_world_safe(False, None, True),
    "mutant: s144's world branch (the latch free) never starts the settle clock on a stuck bracket -- the ramp wedged for good": lambda: (
        (lambda live, why, r: live and why is None)(True, _latch(ret=True), True) != E.ramp_world_safe(True, _latch(ret=True), True)),
    "over: the peer alive for the settle and back on the world map leaves (host_world)": lambda: (
        E.diorama_watch_step(False, 0, E.WREPORT_NONCE, True, 0, True, False, 600, 600, 500, 60000, 8000, E.WATCH_WHY_NONE)
        == (E.WATCH_LEAVE_FINAL, E.WATCH_WHY_HOST_WORLD) and E.watch_why_name(E.WATCH_WHY_HOST_WORLD) == "host_world"),
}


def _wwatch_rows_in_order() -> dict:
    """All 59 rows in the engine's order: the 15 report rows, the literal rows to the free projection, the projection loop's 17,
    then the rest."""
    rep = {f"report: {c['name']}": (lambda c=c: E.world_report_at(c) == c["want"]) for c in _report_cases()}
    loop = {}
    for i, w in enumerate(E.world_warm_disqualifiers()):
        durable = E.world_row_durable(i)
        loop[f"projection: row {i}'s disqualifier alone " + ("declines (durable)" if durable else "declines nothing (transient)")] = (
            lambda w=w, durable=durable: E.world_warm_verdict(w)[0] is not None and E.world_warm_verdict(w)[1] == durable
            and (E.world_decline_why(w) is not None) == durable)
    lit = list(WWATCH_ROWS.items())
    cut = [n for n, _c in lit].index("projection: the free world declines nothing") + 1
    return dict(list(rep.items()) + lit[:cut] + list(loop.items()) + lit[cut:])


def test_every_world_watcher_selftest_row_has_a_twin_that_holds():
    names = _row_names("NetSyncClient.cs", "internal static Boolean WorldWatchSelfTest(", "WWatchRow")
    assert names == list(WWATCH_ROWS), [n for n in names if n not in WWATCH_ROWS] + ["--"] + [n for n in WWATCH_ROWS if n not in names]
    cases = _report_cases()
    assert len(cases) == 15 and len({c["name"] for c in cases}) == 15
    rows = _wwatch_rows_in_order()
    assert len(rows) == BW.WORLD_WATCHER_SELFTEST_ROWS == 59
    code = " ".join(_code(t) for t in _block("NetSyncClient.cs", "internal static Boolean WorldWatchSelfTest(", "catch (Exception err)"))
    assert 'WWatchRow(WorldReportAt(c, watch, ui, false) == c.Want, "report: " + c.Name, ref n, ref bad);' in code
    assert '"projection: row " + i + "\'s disqualifier alone " + (durableRow ? "declines (durable)" : "declines nothing (transient)")' in code
    failed = [name for name, check in rows.items() if check() is not True]
    assert not failed, failed


# ---- the freeze line's 46 rows (its four release-lifetime rows are s145's)
FREEZE_S145_ROWS = {
    "release: a field load ends it": lambda: E.world_freeze_release_ends_at(E.RELEASE_AT_FIELD),
    "release: a world load keeps it (a world battle round trip: the diorama's warm return)": lambda: not E.world_freeze_release_ends_at(E.RELEASE_AT_WORLD),
    "release: the title ends it (a world-map save's Continue never starts free)": lambda: E.world_freeze_release_ends_at(E.RELEASE_AT_TITLE),
    "mutant: s144's lifetime re-freezes a released guest at every world diorama's return, and keeps it past the title": lambda: (
        sum(E.world_freeze_release_ends_at_s144(a) != E.world_freeze_release_ends_at(a) for a in (0, 1, 2)) == 2),
}


def _freeze_rows() -> dict:
    """The s145 block's order: s144's 42 rows with the four lifetime rows right before its last (the lever's)."""
    from . import test_world_coop as WC
    old = list(WC.FREEZE_ROWS.items())
    return dict(old[:-1] + list(FREEZE_S145_ROWS.items()) + old[-1:])


def test_the_freeze_lines_46_rows_each_hold_and_the_lifetime_constants_are_the_engines():
    names = _row_names("NetSyncField.cs", "internal static Boolean WorldFreezeSelfTest(", "FreezeRow")
    rows = _freeze_rows()
    assert names == list(rows) and len(names) == BW.WORLD_FREEZE_SELFTEST_ROWS_S145 == BW.world_freeze_selftest_rows(145) == 46
    assert BW.world_freeze_selftest_rows(144) == BW.WORLD_FREEZE_SELFTEST_ROWS == 42
    failed = [name for name, check in rows.items() if check() is not True]
    assert not failed, failed
    consts = " ".join(t for _h, _k, t in _new_side("NetSyncField.cs") if t.startswith("internal const Int32 ReleaseAtField"))
    assert re.findall(r"(ReleaseAt\w+) = (\d)", consts) == [("ReleaseAtField", "0"), ("ReleaseAtWorld", "1"), ("ReleaseAtTitle", "2")]
    assert (E.RELEASE_AT_FIELD, E.RELEASE_AT_WORLD, E.RELEASE_AT_TITLE) == (0, 1, 2)


def test_the_proof_block_logs_the_two_lines_after_the_overlay_text_line_and_the_watcher_line_grew():
    heads = [ln for ln in net_lines("NetSyncClient.cs", r'Log\.Message\("\[NetSync\] [a-z ]+ selftest: "')]
    order = [re.search(r'\[NetSync\] ([a-z ]+ selftest: )', ln).group(1) for ln in heads]
    i = order.index(BW.PROOF_OVERLAY_TEXT)
    assert order[i + 1:i + 3] == [BW.PROOF_WORLD_DIORAMA, BW.PROOF_WORLD_WATCHER], order
    block = " ".join(net_lines("NetSyncClient.cs", r"WorldDioramaSelfTest\(out wdioDetail\)|WorldWatchSelfTest\(out wwatchDetail\)"))
    assert "NetSyncDiorama.WorldDioramaSelfTest(out wdioDetail)" in block and "WorldWatchSelfTest(out wwatchDetail)" in block
    assert BW.watch_selftest_rows(145) == 32 and BW.watch_selftest_rows(144) == BW.watch_selftest_rows(119) == 24
    assert BW.proof_ok(BW.PROOF_WORLD_DIORAMA, 98) == "world diorama selftest: OK (98 rows)"


# ------------------------------------------------------------------------------------------------ every check can fail
_O = {name: getattr(BW, name) for name in (
    "world_warm_row", "world_row_durable", "world_latch_no_boot", "world_warm_lever_for", "parse_world_warm_lever",
    "world_warm_bench_refusal", "world_warm_lever_name", "return_is_ours", "return_is_ours_field", "return_load_step",
    "world_durable_in", "world_decline_why", "boot_watching", "world_ui_free", "ramp_world_safe", "follow_field_for_dio",
    "diorama_watch_step", "world_freeze_release_ends_at", "world_report_at", "world_warm_disqualifiers",
    "world_leave_stays", "ramp_world_settled_closed",                   # fix1
    "world_window_busy", "world_windows_busy")}                         # fix4


def _drop_row(n):
    def mutant(w, skip=-1):
        why, row = _O["world_warm_row"](w, skip if skip >= 0 else n)
        return why, row
    return mutant


#: one mutant per twin the s145 selftests pin (a one-line drift), and the table whose ENGINE rows must then go red
TWIN_MUTANTS = [
    ("wdio", "world_warm_row", _drop_row(BW.WORLD_ROW_VEHICLE)),                                       # the vehicle row gone
    ("wdio", "world_row_durable", lambda row: _O["world_row_durable"](row) and row != BW.WORLD_ROW_BEE),   # bee transient
    ("wdio", "world_latch_no_boot", lambda l, m, a, x, f, r, j: BW.world_latch_step(l, m, a, x, f, True, r, j)),   # booted
    ("wdio", "world_warm_lever_for", lambda role, bench: int(bench) if int(bench) in (1, 2) else 0),     # any role
    ("wdio", "parse_world_warm_lever", lambda v: {"warm": 0}.get(str(v or "").strip().lower(), _O["parse_world_warm_lever"](v))),
    ("wdio", "world_warm_bench_refusal", lambda role, lever: BW.WORLD_WARM_EXPECTED if lever < 0 else None),   # no role
    ("wdio", "world_warm_lever_name", lambda lever: "cold" if lever == BW.WORLD_WARM_OFF else _O["world_warm_lever_name"](lever)),
    ("wdio", "return_is_ours", lambda p, k, i, lk, li, m: bool(p) and i == li and m == lk),              # kind-blind
    ("wdio", "return_is_ours_field", lambda p, warm, fld, mode: bool(p) and fld == warm),                # mode-blind
    ("wdio", "return_load_step", lambda p, k, g: (BW.RETURN_LOAD_OURS if g == k else BW.RETURN_LOAD_MISMATCH)
     if p and g == 1 else BW.RETURN_LOAD_NONE),                                                          # s144: gMode 1 only
    ("wwatch", "world_durable_in", lambda w: BW.world_warm_in(**{k: w[k] for k in BW.WORLD_DURABLE_INPUTS if k != "travel_mode"})),
    ("wwatch", "world_decline_why", lambda w: BW.world_warm_verdict(w)[0] if BW.world_warm_verdict(w)[1] else None),   # the full verdict
    ("wwatch", "boot_watching", lambda c, f, fm, ws, mb, d: bool(c and f and mb and fm)),               # s144: a field only
    ("wwatch", "world_ui_free", lambda h, m, o, k, s=BW.WORLD_START_LOOP: bool(h) and not m),           # no construct frames
    ("wwatch", "ramp_world_safe", lambda live, why, r: bool(live) and why is None),                     # s144
    ("wwatch", "follow_field_for_dio", lambda o, wb_, wp, fld: BW.follow_field_for(o, fld)),            # s144
    ("wwatch", "follow_field_for_dio", lambda o, wb_, wp, fld: BW.follow_field_for(bool(o) or bool(wb_), fld)),   # booted-only
    ("wdio", "world_leave_stays", lambda alive, scene: bool(alive)),                                   # the boot director only
    ("wwatch", "ramp_world_settled_closed", lambda e, c, r: BW.ramp_world_settled(e, c)),              # resuming-blind
    ("wwatch", "diorama_watch_step", lambda *a: _O["diorama_watch_step"](*a[:5], False, *a[6:])),        # b6-blind
    ("freeze", "world_freeze_release_ends_at", lambda at: at in (BW.RELEASE_AT_FIELD, BW.RELEASE_AT_WORLD)),   # s144's
    ("wwatch", "world_report_at", lambda c, w=None, u=None, s=False: _O["world_report_at"](dict(c, fading=False), w, u, s)),
    ("wdio", "world_warm_disqualifiers", lambda: [dict(w, topograph=3) if i == BW.WORLD_ROW_TOPOGRAPH else w
                                                  for i, w in enumerate(_O["world_warm_disqualifiers"]())]),
    ("wdio", "world_window_busy", lambda sl, ih, ch, sh: True),                                       # [fix4] Dialogs.Visible
    ("wdio", "world_window_busy", lambda sl, ih, ch, sh: not ih),                                     # [fix4] [NFOC] only
    ("wdio", "world_window_busy", lambda sl, ih, ch, sh: not ih or ch or not sh),                     # [fix-r1] script-blind
    ("wdio", "world_window_busy", lambda sl, ih, ch, sh: not sl or not ih or ch),                     # [fix-r1] shown-blind
    ("wdio", "world_windows_busy", lambda wins, rule=None: False if wins is None else _O["world_windows_busy"](wins, rule)),
]


def _engine_rows(kind: str) -> dict:
    return {"wdio": _wdio_rows_in_order, "wwatch": _wwatch_rows_in_order, "freeze": _freeze_rows}[kind]()


@pytest.mark.parametrize("kind,name,mutant", TWIN_MUTANTS, ids=[m[1] for m in TWIN_MUTANTS])
def test_each_twin_mutant_turns_an_engine_row_red(monkeypatch, kind, name, mutant):
    """EVERY CHECK CAN FAIL: with one twin drifted (in memory), at least one of the engine's own selftest rows evaluated against
    the twins reads red -- and with the twins as shipped, none does."""
    assert all(check() is True for check in _engine_rows(kind).values())
    monkeypatch.setattr(BW, name, mutant)
    red = []
    for row, check in _engine_rows(kind).items():
        try:
            if check() is not True:
                red.append(row)
        except Exception:                            # noqa: BLE001 -- a drifted twin that throws reads red too
            red.append(row)
    assert red, f"{name}: no {kind} row read the mutant"


def test_every_pure_twin_has_a_mutant():
    assert {m[1] for m in TWIN_MUTANTS} == set(_O)


# ------------------------------------------------------------------------------------------------ the call sites
def _seq(lines, *needles) -> list:
    """The index of each needle's first line in ``lines`` (code only), in the order given -- -1 = absent."""
    code = [_code(t) for t in lines]
    return [next((i for i, t in enumerate(code) if n in t), -1) for n in needles]


def test_the_watcher_runs_the_pre_verdict_before_boot_from_wire_and_reports_on_the_loose_gmode():
    client = [t for _h, _k, t in _new_side("NetSyncClient.cs")]
    i = _seq(client, "if (!onField && !onWorld)", "if (onWorld && WorldBootWaits(nonce))",
             "PersistenSingleton<UIManager>.Instance.State != (onWorld ? UIManager.UIState.WorldHUD : UIManager.UIState.FieldHUD)",
             "if (onWorld && WorldBootRefused(nonce))")
    assert -1 not in i and i == sorted(i), i
    # THE ORDER, as a chain the patches themselves pin: in s145's hunk the pre-verdict sits right before s114's `fadingAtTry`
    # (its context), and in s114's hunk `fadingAtTry` sits before the BootFromWire call -- so the pre-verdict runs before it
    new = _new_side("NetSyncClient.cs")
    k = next(n for n, (_h, _kd, t) in enumerate(new) if _code(t) == "if (onWorld && WorldBootRefused(nonce))")
    tail = [(h, _code(t)) for h, _kd, t in new[k:k + 6]]
    assert ("return;" in [t for _h, t in tail[:3]] and (new[k][0], "Boolean fadingAtTry = false;") in tail), tail
    s114 = (msr.PATCHES / "s114-netsync-start-hold.patch").read_bytes()
    old = []
    for path, sec in msr.sections(s114):
        if path and path.rsplit("/", 1)[-1] == "NetSyncClient.cs":
            old += [ln[1:].strip() for ln in sec.decode("utf-8", "replace").splitlines() if ln[:1] in (" ", "+")]
    a = old.index("Boolean fadingAtTry = false;")
    assert any(t.startswith("NetSyncDiorama.BootFromWire(") for t in old[a:a + 12]), old[a:a + 12]
    assert sum(_code(t) == "Boolean fadingAtTry = false;" for t in net_lines("NetSyncClient.cs", r"Boolean fadingAtTry = false;")) == 1
    assert len([t for t in net_lines("NetSyncClient.cs", r"NetSyncDiorama\.BootFromWire\(") if _code(t)]) == 1
    assert "NoteBootWatch(ee != null && ee.gMode == 3, onWorld);" in [_code(t) for t in client]
    assert "DioramaTick(onField, onWorld);" in [_code(t) for t in client]
    # the decline line never says REFUSED (dioboot's refusal grep stays Boot's) and never stamps the skip nonce
    decl = " ".join(_code(t) for t in _block("NetSyncClient.cs", "private void NoteWatcherWorldDecline(", "}"))
    assert "REFUSED" not in decl and "_dioramaSkipNonce" not in decl and "NetSyncDiorama.NoteWorldDecline(why, true);" in decl
    assert not any("_dioramaSkipNonce =" in _code(t) for t in _block("NetSyncClient.cs", "private Boolean WorldBootRefused(", "}"))


def test_boot_reads_the_world_verdict_before_arm_and_the_world_shape_never_writes_next_mode():
    dio = [t for _h, _k, t in _new_side("NetSyncDiorama.cs")]
    i = _seq(dio, "String worldWhy = WorldWarmWhyNow(out worldDurable);", "NoteWorldDecline(worldWhy, worldDurable);",
             "_bootWorld = world;")
    assert -1 not in i and i == sorted(i), i
    added = net_lines("NetSyncDiorama.cs", r".", [_patch()]) + net_lines("NetSyncClient.cs", r".", [_patch()])
    assert not [t for t in added if re.search(r"nextMode\s*=\s*2", _code(t))]          # never written from outside
    assert any("FindObjectOfType<WMScriptDirector>()" in _code(t) for t in added)
    assert not [t for t in net_lines("NetSyncDiorama.cs", r"WMScriptDirector\.Instance", [_patch()]) if _code(t)]
    shape = " ".join(_code(t) for t in _block("NetSyncDiorama.cs", "private static void BootWorldShape()",
                                               'Log.Message("[NetSync] diorama pre-swirl (world): prevMode 3 (was " + _prevModeAtBoot + "), input off, audio " + lane);'))
    assert shape.index("sys.prevMode = 3;") < shape.index("SceneDirector.Replace(") < shape.index("EventInput.IsProcessingInput = false;")
    assert "SetCenterPosition(1)" in shape and "SetCenterPosition(0)" not in shape
    leave = " ".join(_code(t) for t in dio)
    assert 'SceneDirector.Replace("WorldMap", SceneTransition.FadeOutToBlack, true);' in leave
    ff9 = [t for _h, _k, t in _new_side("ff9.cs")]
    j = _seq(ff9, "Memoria.Netsync.NetSyncDiorama.BeforeWorldEvents();", "StartEvents(")
    assert -1 not in j and j[0] < j[1], j
    rel = " ".join(_code(t) for _h, _k, t in _new_side("NetSyncBattle.cs"))
    assert "NetSyncDiorama.HarnessReleaseWorldWarm();" in rel


# ------------------------------------------------------------------------------------------------ the stage law
def _said_by(patches, file_name: str, text: str) -> bool:
    lits = [m.group(1).replace('\\"', '"') for ln in net_lines(file_name, r'"', patches) for m in re.finditer(r'"((?:[^"\\]|\\.)*)"', ln)]
    return any(text in lit for lit in lits) or text in "".join(lits)


def test_the_release_words_s145_rewrote_are_s144s_on_its_stack_and_gone_from_the_live_one():
    s144 = _upto("s144")
    for text in ("released from the ~ menu until the next field or world load", "already released (until the next field or world load)",
                 " until the next field or world load: the guest walks, rides and enters locations on its own"):
        assert _said_by(s144, "NetSyncField.cs", text), text
        assert not _said_by(None, "NetSyncField.cs", text), text
    # s144 composed "re-armed (world load)" from its load's name; s145's world load no longer re-arms a release
    rearm = lambda patches: [_code(t) for t in net_lines("NetSyncField.cs", r"RearmWorldFreeze\(|re-armed \(", patches)]   # noqa: E731
    assert 'RearmWorldFreeze("world");' in rearm(s144)
    assert 'Log.Message("[NetSync] world freeze re-armed (" + what + " load)");' in rearm(s144)
    assert 'RearmWorldFreeze("world");' not in rearm(None) and "RearmWorldFreeze(ReleaseAtWorld);" in rearm(None)
    assert BW.LOG_WORLD_FREEZE_REARMED_WORLD == "world freeze re-armed (world load)"
    assert BW.world_freeze_lift_why_s144(True, False, False, True, False) == "released from the ~ menu until the next field or world load"
    assert BW.world_freeze_lift_why(True, False, False, True, False) == BW.RELEASE_LIFT_WHY
    assert _said_by(None, "NetSyncField.cs", BW.RELEASE_LIFT_WHY) and _said_by(None, "NetSyncField.cs", BW.LOG_WORLD_FREEZE_REARMED_TITLE)
    assert BW.world_freeze_release_refusal_s144(True, True, False, True) == "already released (until the next field or world load)"
    assert BW.world_freeze_release_refusal(True, True, False, True) == "already released (until the next field load)"
    assert "until the next field or world load" in BW.log_world_freeze_released_s144("~ menu", 9011)
    assert "until the next field or world load" not in BW.log_world_freeze_released("~ menu", 9011)
    # the ~ menu's own words (Ff9mkDebugMenu) moved with it
    menu = " ".join(net_lines("Ff9mkDebugMenu.cs", r"until the next field"))
    assert "until the next field or world load" not in menu and "world freeze released until the next field load" in menu


# ------------------------------------------------------------------------------------------------ the harness ladder, the driver
def test_the_worlddio_rung_is_s145s_after_worldwait_and_the_driver_keys_on_its_probe():
    names = list(FG.NETSYNC_BATTLE_CAPS)
    assert names[names.index("worldwait") + 1] == "worlddio" and FG.NETSYNC_BATTLE_CAPS["worlddio"] == ("s145", ())
    assert FG.NETSYNC_S145_CAPS == frozenset(("worlddio",)) and "worlddio" not in FG.caps_through("worldwait")
    assert FG.NETSYNC_BATTLE_CAP_KEYS["worlddio"] == {} and FG.NETSYNC_WORLD_KEYS_BY_RUNG["worlddio"] == tuple(BW.WORLD_SENTINELS)
    assert Session.NETSYNC_BENCH_OPS["worldwarm"][:3] == ("coop_world_dio", "netsync.world.dio", "s145")
    assert isinstance(getattr(CH.State, "coop_world_dio"), property)
    src = (REPO / "studies" / "test-harness" / "scenarios" / "_coop_battle.py").read_text(encoding="utf-8")
    assert '145: "netsync.world.dio",' in src
    probe = re.search(r'Probe `?netsync\.world\.dio`? first|probe `netsync\.world\.dio` first',
                      " ".join(net_lines("HarnessAgent.cs", r"netsync\.world\.dio")))
    assert probe, "the agent names the probe"
    assert BW.WATCH_WHY_NAMES[BW.WATCH_WHY_HOST_WORLD] == "host_world" and BW.WATCH_WHY_HOST_WORLD == 6
    assert BW.CS_CLIENT_CONSTANTS["WatchWhyHostWorld"] == _cs_int("NetSyncClient.cs", "WatchWhyHostWorld")
    text = " ".join(net_lines("NetSyncClient.cs", r"case WatchWhyHostWorld: return"))
    assert '"host_world"' in text and json.dumps(BW.WATCH_WHY_TEXT_HOST_WORLD) in text


# ------------------------------------------------------------------------------------------------ fix1: the call sites, pinned
def _call(lines, head: str) -> list | None:
    """The argument list (code only, stripped) of the statement in ``lines`` (new-side texts) whose first line starts with ``head``
    -- joined up to the line ending ``);`` -- or None when no line starts with it."""
    code = [_code(t) for t in lines]
    i = next((k for k, t in enumerate(code) if t.startswith(head)), None)
    if i is None:
        return None
    j = next(k for k in range(i, len(code)) if code[k].endswith(");"))
    text = " ".join(code[i:j + 1])
    inner = text[text.index("(") + 1:text.rindex(")")]
    return [a.strip() for a in inner.split(",")]


def _watch_call_ok(lines) -> bool:
    """DioramaTick's production step call hands section 7's b6 (`_hostWorld`) as its sixth argument, 13 inputs + `out`."""
    args = _call(lines, "Int32 step = DioramaWatchStep(")
    return args is not None and len(args) == 14 and args[5] == "_hostWorld" and args[-1] == "out watchWhy"


def _has_line(lines, line: str) -> bool:
    return any(_code(t) == line for t in lines)


#: the production lines the overload trap and the live wiring hang on -- (file, the line's code, what it carries)
FIX1_PINS = (
    ("NetSyncClient.cs", "Int32 followFld = FollowFieldForDio(onWorld, NetSyncDiorama.BootedFromWorld, "
                         "NetSyncDiorama.WorldReturnPending, fld);", "the follow field: the world, the booted diorama, its pending return"),
    ("NetSyncClient.cs", "settled = rampWorld && RampWorldSettledClosed(ff9.IsEventWorldMap, e2.GetUserControl(), rampResuming);",
     "the ramp's settle never inside the reinit bracket"),
    ("NetSyncClient.cs", "NetSyncField.OnTitleWorldFreeze();", "the title ends a ~ menu release (decision 10)"),
    ("NetSyncClient.cs", "ResetWorldWatchDedup();", "the world watcher's dedup reset at an epoch change and a session end"),
    ("NetSyncDiorama.cs", "if (_bootWorld && WorldLeaveStays(WorldBootStillAlive, Application.loadedLevelName))",
     "a Leave on a live world map disarms in place"),
    ("NetSyncDiorama.cs", "try { world = world || Application.loadedLevelName == SceneDirector.WorldMapSceneName; }",
     "a boot on the WorldMap scene goes through the world verdict"),
    # [fix4] THE PASSIVE PROMPTS: ReadWorldWarm's Dialogs input is the live list through the selftested rule
    ("NetSyncDiorama.cs", "w.Dialogs = WorldDialogsBusy(ui);", "the world verdict reads the passive prompts as no dialogue"),
    ("NetSyncDiorama.cs", "wins[k] = new WorldWindow(NetSyncDialog.IsLockable(dlg), dlg.FlagButtonInh, shown && dlg.HasChoices, shown);",
     "each live window projected: a script line, [NFOC], a choice read on a shown window, shown"),
    ("NetSyncDiorama.cs", "Boolean shown = dlg.CurrentState == Dialog.State.CompleteAnimation;", "shown = fully shown"),
    ("NetSyncDiorama.cs", "return WorldWindowsBusy(wins, WorldWindowBusy);", "the live list runs the selftested rule"),
    # [fix-r1 -- g-prompts-no-witness] the watcher's dialogue-row wait names the window behind it, by the verdict's own rule
    ("NetSyncClient.cs", "String which = String.Equals(why, NetSyncDiorama.WorldWhyDialog) ? "
                         "NetSyncDiorama.WorldDialogsBusyWhich(PersistenSingleton<UIManager>.Instance) : null;",
     "the dialogue row's wait names its window (once per reason, beside the line)"),
    ("NetSyncDiorama.cs", "if (WorldWindowBusy(script, inh, choice, shown))", "the window named by the verdict's own rule"),
    ("NetSyncDiorama.cs", 'internal const String WorldWhyDialog = "a dialogue window is open";', "the dialogue row's why, named"),
)


def test_the_dialogue_rows_wait_names_its_window_and_its_why_is_the_verdicts():
    """[fix-r1 -- g-prompts-no-witness] If a redeployed T2 or duo guest still waits on the world map, the log says WHICH window held
    the dialogue row: WorldBootRefused's wait line (unchanged: the bench greps its why) is followed, once per reason, by the busy
    window WorldDialogsBusyWhich names through WorldWindowBusy itself. The const it keys on IS the world verdict's dialogue-row why
    (a renamed literal at WorldRowDialog would silence the line: read red), and the line's text stays the bench's."""
    dio = [_code(t) for _h, _k, t in _new_side("NetSyncDiorama.cs")]
    i = dio.index("row = WorldRowDialog;")
    assert dio[i + 1] == "if (skip != row && w.Dialogs)" and dio[i + 2] == 'return "a dialogue window is open";', dio[i:i + 3]
    const = next(c for c in dio if c.startswith("internal const String WorldWhyDialog = "))
    assert const.split(" = ", 1)[1].rstrip(";") == dio[i + 2][len("return "):].rstrip(";")
    drift = [c.replace('"a dialogue window is open"', '"a window is open"') if c.startswith("return") else c for c in dio[i:i + 3]]
    assert drift[2][len("return "):].rstrip(";") != const.split(" = ", 1)[1].rstrip(";")   # the pin can fail
    client = [c for c in (_code(t) for _h, _k, t in _new_side("NetSyncClient.cs")) if c]       # (comment-only lines dropped)
    k = next(n for n, c in enumerate(client) if c.startswith("String which = String.Equals(why, NetSyncDiorama.WorldWhyDialog)"))
    assert client[k - 1] == '+ "; retried each second, logged once per reason)");' and client[k + 1] == "if (which != null)", \
        client[k - 1:k + 3]
    assert client[k + 2].startswith('Log.Message("[NetSync] diorama world wait: the dialogue row\'s window -- " + which'), client[k + 2]
    which = " ".join(_code(t) for t in _block("NetSyncDiorama.cs", "internal static String WorldDialogsBusyWhich(UIManager ui)",
                                               "catch (Exception err)"))
    assert "Boolean shown = dlg.CurrentState == Dialog.State.CompleteAnimation;" in which and "return null;" in which
    assert "Boolean choice = shown && dlg.HasChoices;" in which and "NetSyncDialog.IsLockable(dlg)" in which


def test_the_world_dialogue_input_is_the_prompt_rule_and_the_field_verdict_keeps_visible():
    """[fix4] The world verdict's Dialogs input is WorldDialogsBusy (the passive prompts are no dialogue) at its ONE live site,
    ReadWorldWarm -- s145's own Dialogs.Visible read is gone from the patch's code -- while the FIELD verdict (F3.3's WarmVerdict
    call) keeps Dialogs.Visible byte for byte: exactly one code line of the live stack reads it, and the s145 patch adds or removes
    none. Each check reads red on a copy that restores the old line."""
    dio = [t for _h, _k, t in _new_side("NetSyncDiorama.cs")]
    code = [_code(t) for t in dio]
    assert not [c for c in code if "ui.Dialogs.Visible" in c], [c for c in code if "ui.Dialogs.Visible" in c]
    # every write of the input: Free()'s `false`, ReadWorldWarm's fail-closed `true` and the live rule -- nothing else
    assert sorted(c for c in code if c.startswith("w.Dialogs = ")) == [
        "w.Dialogs = WorldDialogsBusy(ui);", "w.Dialogs = false;", "w.Dialogs = true;"]
    old = [("w.Dialogs = ui == null || ui.Dialogs == null || ui.Dialogs.Visible;" if c == "w.Dialogs = WorldDialogsBusy(ui);" else c)
           for c in code]
    assert [c for c in old if "ui.Dialogs.Visible" in c]                 # the pin can fail: the pre-fix4 line reads red
    field = [t for t in net_lines("NetSyncDiorama.cs", r"Dialogs\.Visible") if "ui.Dialogs.Visible" in _code(t)]
    assert field == ["ui == null || ui.Dialogs == null || ui.Dialogs.Visible,   // unreadable = busy"], field
    assert not [t for t in net_lines("NetSyncDiorama.cs", r"Dialogs\.Visible", [_patch()]) if "ui.Dialogs.Visible" in _code(t)]
    # the selftest's prompt rows run the live rule and the old rule as their mutant
    st = " ".join(_code(t) for t in _block("NetSyncDiorama.cs", "internal static Boolean WorldDioramaSelfTest(", "catch (Exception err)"))
    assert "Func<Boolean, Boolean, Boolean, Boolean, Boolean> rule = WorldWindowBusy;" in st
    assert "Func<Boolean, Boolean, Boolean, Boolean, Boolean> visible = (sl, ih, ch, sh) => true;" in st


def test_the_overload_trap_is_closed_each_step_has_one_name():
    """A dropped input must FAIL TO COMPILE, never bind an older rule: the production DioramaWatchStep has no b6-clear overload (that
    one is DioramaWatchStepB6Clear), FollowFieldForDio / RampWorldSettledClosed are no overloads of s144's FollowFieldFor /
    RampWorldSettled -- each name declared exactly once on the live stack, the s144 forms keeping their own arity."""
    decl = lambda name: [t for t in net_lines("NetSyncClient.cs", rf"\bstatic (?:Int32|Boolean) {name}\(") if _code(t)]   # noqa: E731
    assert len(decl("DioramaWatchStep")) == 1 and "Boolean hostWorld" in " ".join(
        _block("NetSyncClient.cs", "internal static Int32 DioramaWatchStep(", "{"))
    assert len(decl("DioramaWatchStepB6Clear")) == 1 and decl("DioramaWatchStepB6Clear")[0].startswith("private static")
    assert len(decl("FollowFieldFor")) == 1 and "(Boolean onWorld, Int32 fld)" in decl("FollowFieldFor")[0]
    assert len(decl("FollowFieldForDio")) == 1 and \
        "(Boolean onWorld, Boolean worldBooted, Boolean worldReturnPending, Int32 fld)" in decl("FollowFieldForDio")[0]
    assert len(decl("RampWorldSettled")) == 1 and "(Boolean eventWorld, Boolean control)" in decl("RampWorldSettled")[0]
    assert len(decl("RampWorldSettledClosed")) == 1 and \
        "(Boolean eventWorld, Boolean control, Boolean resuming)" in decl("RampWorldSettledClosed")[0]
    # the s119 / s120 tables' rows read the b6-clear step by its own name (13 arguments: 12 + out)
    for start in ("private static Int32 WatchAt(", "internal static Boolean SessionGraceSelfTest("):
        body = " ".join(_code(t) for t in _block("NetSyncClient.cs", start, "}" if "WatchAt(" in start else "catch (Exception err)"))
        assert "DioramaWatchStepB6Clear(" in body and not re.search(r"\bDioramaWatchStep\(", body), start


def test_the_production_lines_are_pinned_and_each_pin_can_fail():
    """The call sites the s145 laws live at (a law in a docstring is a wish), each on the s145 patch's new side -- and each pin read
    on a copy WITHOUT its line reads red (a check that cannot fail is no check)."""
    client = [t for _h, _k, t in _new_side("NetSyncClient.cs")]
    assert _watch_call_ok(client)
    dropped = [t for t in client if _code(t) != "_hostWorld,"]
    assert len(dropped) == len(client) - 1 and not _watch_call_ok(dropped)     # the b6-blind call is red
    for file_name, line, what in FIX1_PINS:
        side = [t for _h, _k, t in _new_side(file_name)]
        assert _has_line(side, line), (what, line)
        assert not _has_line([t for t in side if _code(t) != line], line), what
    assert sum(_code(t) == "ResetWorldWatchDedup();" for t in client) == 2   # ResetGuestDedupForEpoch and ResetIntentAndL1State
    # WorldBootWaits reads the LIVE latch (never Update's cached _worldLatch) and no longer waits quietly on the bee scene
    waits = " ".join(_code(t) for t in _block("NetSyncClient.cs", "private Boolean WorldBootWaits(Int32 nonce)", "}"))
    assert "WorldTransitionWhy() != null" in waits and "_worldLatch" not in waits and "IsBeeScene" not in waits
    # the title's freeze end sits in Update's atTitle branch
    code = [_code(t) for t in client]
    i = code.index("if (atTitle)")
    assert "NetSyncField.OnTitleWorldFreeze();" in code[i:i + 5], code[i:i + 5]
    # the leave's stay runs BEFORE the settle and the mode write; [fix2] the battle song's instance is latched AFTER the settle (a song
    # the settle shut is no longer current: its 2 s stop fade never reads 'left playing') and before the mode write
    dio = [t for _h, _k, t in _new_side("NetSyncDiorama.cs")]
    i = _seq(dio, "if (_bootWorld && WorldLeaveStays(WorldBootStillAlive, Application.loadedLevelName))",
             "SettleForReturn(via);", "_leaveSongSid = MusicSoundIdNow();", "PersistenSingleton<FF9StateSystem>.Instance.mode = _returnMode;")
    assert -1 not in i and i == sorted(i), i
    assert sum(_code(t) == "_leaveSongSid = MusicSoundIdNow();" for t in dio) == 1   # ...exactly once (no pre-settle latch left)
    latch = next(t for t in dio if _code(t) == "_leaveSongSid = MusicSoundIdNow();")
    # [fix3 -- v-raudio-1-3] ...and WORLD-only: the line right above it is its `if (_bootWorld)` guard (a field leave latching a field
    # battle song into the WORLD witness `netsync.world.dio.boot_song_live` would drift the key's meaning) -- a copy without it is red
    j = dio.index(latch)
    assert _code(dio[j - 1]) == "if (_bootWorld)", dio[j - 3:j + 1]
    unguarded = dio[:j - 1] + dio[j:]
    assert _code(unguarded[unguarded.index(latch) - 1]) != "if (_bootWorld)"
    mut = [t for t in dio if t is not latch]
    k = next(n for n, t in enumerate(mut) if _code(t) == "SettleForReturn(via);")
    mut = mut[:k] + [latch] + mut[k:]                                  # the pre-fix2 order: the latch right before the settle
    m = _seq(mut, "if (_bootWorld && WorldLeaveStays(WorldBootStillAlive, Application.loadedLevelName))",
             "SettleForReturn(via);", "_leaveSongSid = MusicSoundIdNow();", "PersistenSingleton<FF9StateSystem>.Instance.mode = _returnMode;")
    assert -1 not in m and m != sorted(m), m                           # ...reads red: the pin can fail
    # the dedup reset clears the decline's and the wait's latches, both halves
    reset = " ".join(_code(t) for t in _block("NetSyncClient.cs", "private void ResetWorldWatchDedup()", "}"))
    for latch in ("_dioramaWorldDeclineNonce = -1;", "_dioramaWorldDeclineLogged = null;", "_worldBootWaitNonce = -1;",
                  "_worldBootWaitWhy = null;"):
        assert latch in reset, latch


# ------------------------------------------------------------------------------------------------ fix1: the log-line twins
def _literals(file_name: str) -> list:
    """The s145 patch's new-side string literals in ``file_name``, in file order."""
    out = []
    for _h, _k, t in _new_side(file_name):
        out += [m.group(1).replace('\\"', '"') for m in re.finditer(r'"((?:[^"\\]|\\.)*)"', _code(t))]
    return out


def _pieces_in_order(text: str, holes, lits) -> bool:
    """``text`` (a twin's line) split at each value in ``holes`` (the engine's runtime parts): every remaining piece is found, in
    order, in the literals' concatenation in file order (a piece may span two adjacent literals: `" (for this world visit)" + " -- a
    world return..."`)."""
    pat = "|".join(re.escape(str(h)) for h in holes) if holes else None
    pieces = [p for p in (re.split(pat, text) if pat else [text]) if p]
    joined, pos = "".join(lits), 0
    for p in pieces:
        pos = joined.find(p, pos)
        if pos < 0:
            return False
        pos += len(p)
    return True


_POS = (1234.25, -77.25)                     # a position whose text ("(1234.3, -77.3)") no literal carries
_WHY = "<a reason>"


def _line_twins() -> dict:
    """name -> (file, the twin's text with stand-in runtime values, those values)."""
    pos = BW.boot_pos_text(*_POS)
    return {
        "log_world_boot_refused durable": ("NetSyncDiorama.cs", BW.log_world_boot_refused(_WHY, True), (_WHY,)),
        "log_world_boot_refused": ("NetSyncDiorama.cs", BW.log_world_boot_refused(_WHY, False), (_WHY,)),
        "log_world_warm_primed": ("NetSyncDiorama.cs", BW.log_world_warm_primed(90123, *_POS), (90123, pos)),
        "log_world_cold_primed": ("NetSyncDiorama.cs", BW.log_world_cold_primed(90123), (90123, BW.LOG_WORLD_COLD_WHY)),
        "LOG_WORLD_COLD_WHY": ("NetSyncDiorama.cs", BW.LOG_WORLD_COLD_WHY, ()),
        "log_world_leave": ("NetSyncDiorama.cs", BW.log_world_leave(90123, 3), (90123, 3)),
        "log_world_return_warm": ("NetSyncDiorama.cs", BW.log_world_return_warm(90123, *_POS), (90123, pos)),
        "log_world_return_warm_prefix": ("NetSyncDiorama.cs", BW.log_world_return_warm_prefix(90123), (90123,)),
        "log_world_return_cold_calibration": ("NetSyncDiorama.cs", BW.log_world_return_cold_calibration(90123),
                                              (90123, BW.LOG_WORLD_COLD_WHY)),
        "LOG_WORLD_RETURN_UNPRIMED": ("NetSyncDiorama.cs", BW.LOG_WORLD_RETURN_UNPRIMED, ()),
        "LOG_PRESWIRL_AUDIO_FAILED": ("NetSyncDiorama.cs", BW.LOG_PRESWIRL_AUDIO_FAILED, ()),
        "LOG_SWIRL_CENTRE_WORLD_FAILED": ("NetSyncDiorama.cs", BW.LOG_SWIRL_CENTRE_WORLD_FAILED, ()),
        "LOG_WORLD_LEAVE_IN_PLACE": ("NetSyncDiorama.cs", BW.LOG_WORLD_LEAVE_IN_PLACE, ()),
        "log_world_declined": ("NetSyncClient.cs", BW.log_world_declined(90123, _WHY, 77), (90123, _WHY, 77)),
        "log_world_waits": ("NetSyncClient.cs", BW.log_world_waits(90123, _WHY, 77), (90123, _WHY, 77)),
    }


def test_the_log_line_twins_are_the_patchs_own_words():
    """THE LINES THE BENCH JUDGES BY (counts of the twins' text in Memoria.log -- AUDIO on their ABSENCE) are the engine's: each twin,
    split at its runtime values, is the s145 patch's literals in order; BootPosText's "0.#" (InvariantCulture) is the twin's
    rounding. A drifted twin would make the absence rows checks that cannot fail -- the next test proves this one can."""
    lits = {f: _literals(f) for f in ("NetSyncDiorama.cs", "NetSyncClient.cs")}
    for name, (file_name, text, holes) in _line_twins().items():
        assert _pieces_in_order(text, holes, lits[file_name]), (name, text)
    fmt = net_lines("NetSyncDiorama.cs", r'ToString\("0\.#", System\.Globalization\.CultureInfo\.InvariantCulture\)')
    assert len(fmt) == 2 and "LastBootX" in fmt[0] and "LastBootZ" in fmt[1], fmt
    assert BW.boot_pos_text(1.25, -1.25) == "(1.3, -1.3)" and BW.boot_pos_text(2.0, 3.04) == "(2, 3)"


@pytest.mark.parametrize("name", list(_line_twins()))
def test_each_drifted_line_twin_reads_red(name):
    """EVERY CHECK CAN FAIL: each twin drifted by one space reads red against the patch's literals."""
    file_name, text, holes = _line_twins()[name]
    lits = _literals(file_name)
    drifted = re.sub(r" ", "  ", text, count=1) if " " in text else text + "x"
    assert not _pieces_in_order(drifted, holes, lits), (name, drifted)
