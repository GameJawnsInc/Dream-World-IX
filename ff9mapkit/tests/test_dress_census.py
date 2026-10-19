"""[ff9mapkit netsync s140] THE GUEST DRESSES ITSELF -- the offline CENSUS tests (studies/battle-coop/R3-FIELD-MODEL-AUDIT.md
2.3 amendments 1, 3 and 12; its 4.4 "Offline: the B_FRAME census test, the loco-class table test and the frame-count oracle
table"), with the owner's 8-11 decision (rigs 9-12: "their own models").

Four instruments, each pinned to the engine (the s140 patch, read off ``memoria-patches/``), to battlewire's twin and to the
census JSON that DERIVED it from the install (studies/battle-coop/dress-census/: rigs_8_11.json, loco_table.json,
bframe_sites.json -- each a frozen, reproducible read of the user's own install, numbers and open-source names only):

  * THE RIG ROWS 9-12 (Cinna, Marcus, Blank, Beatrix = CharacterId 8-11): the patch's Rig rows == battlewire.RIGS == the
    census rows, every column; the engine's SubRigsAreCensus literals the same.
  * THE 13-ROW FRAME ORACLE (round(length x rate) + 1 off p0data5): battlewire.RIG_FRAMES == rigs_8_11.json `frames_13`
    == the B_FRAME census's frame table; `rig_idle_frames` on s140 = [60, 45, 30, 60, 50, 40, 30, 45, 72, 40, 30, 40, 45].
  * THE CLOSED LOCO-CLASS TABLE: the patch's C# LocoClassSuffixes == battlewire.LOCO_CLASS_SUFFIXES == loco_table.json
    `engine_map`, and the table classifies ALL 401 ZDN names exactly as the generator's rule does.
  * THE B_FRAME CENSUS (the blocking law of amendment 1): every one of the 650 stock threshold sites stays reachable on all
    13 rigs under the s140 laws; `law bframe off` wedges exactly field 2705's three loops, `law timeline off` exactly
    307 x 3 and 2934:474; every body GetAnimDuration answers the frame count of the timeline the id runs on. Its pure
    evaluator (bframe_census.py) runs over the FROZEN sites; each mutant (the law dropped, INACTIVE as loco everywhere,
    KeepSourceTimeline dropped, a rig's idle edited, the 2705 sites dropped, an off-by-one engine model) turns a check red.
    The regeneration from the install is INSTALL-GATED and skips cleanly without it (and, per the worktree skip trap, in
    a fresh worktree: run it in the main repo or the gate).
  * THE JUMP SLOT is NOT a reachability fact: every stock jump / land window is reachable on the idle alias as well as on
    the source clip, so the census verdicts agree with KeepJumpTimeline on or off. Its law is pinned twice instead:
    test_every_stock_jump_window_keeps_stocks_ticks_on_every_rig (a mount / dismount lasts stock's ticks on every rig,
    the hookless mutant red) and test_the_census_jump_timeline_is_the_engines (the census's own jump timeline ==
    battlewire.jump_frame_n, the engine's twin, on every jump / land candidate, rig and dressed law -- so the oracle
    cannot drift from the DLL again).
"""
import importlib.util
import json
import pathlib
import re
import subprocess
import sys

import pytest

from ._patchstack import msr, net_lines, net_lines_ordered

REPO = pathlib.Path(__file__).resolve().parents[2]
CENSUS = REPO / "studies" / "battle-coop" / "dress-census"
sys.path.insert(0, str(REPO / "tools"))
from harness import battlewire as BW                                   # noqa: E402
from harness import fakegame as FG                                     # noqa: E402

MEMORIA = pathlib.Path(r"C:\gd\FFIX\Memoria")
EXPORTS = pathlib.Path(r"C:\gd\FFIX\reference\test2")
RIG_IDLE_13 = [60, 45, 30, 60, 50, 40, 30, 45, 72, 40, 30, 40, 45]


def _json(name: str) -> dict:
    return json.loads((CENSUS / name).read_text(encoding="utf-8"))


def _module(name: str):
    """A census script, loaded from its file under a private name (its module level is stdlib-only)."""
    spec = importlib.util.spec_from_file_location(f"_census_{name}_under_test", CENSUS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _patch(stem: str) -> bytes:
    names = [n for n in msr.stack() if n.startswith(stem + "-") and n not in msr.DEAD]
    assert len(names) == 1, (stem, names)
    return (msr.PATCHES / names[0]).read_bytes()


def _added(file_name: str, stem: str) -> list:
    """The lines ``stem``'s patch ADDS to ``file_name`` (stripped, in order)."""
    out = []
    for path, sec in msr.sections(_patch(stem)):
        if path and path.replace("\\", "/").rsplit("/", 1)[-1] == file_name:
            out += [ln[1:].strip() for ln in sec.decode("utf-8", "replace").splitlines()
                    if ln.startswith("+") and not ln.startswith("+++")]
    return out


def _rig_rows(lines) -> list:
    rows = []
    for t in lines:
        m = re.match(r"new Rig\(([-\d,\s]+)\),", t)
        if m:
            rows.append(tuple(int(x) for x in m.group(1).split(",")))
    return rows


# ================================================================================================ the rig rows 9-12
def test_the_rig_rows_9_to_12_are_the_census_the_patch_and_the_twin():
    """Rows 9-12 come ONLY from the census (orchestrator O3): rigs_8_11.json's rows -- CharacterId 8-11 in CharacterId
    order (O1: 9 Cinna, 10 Marcus, 11 Blank, 12 Beatrix), every column in the table's order -- ARE the s140 patch's four
    new Rig rows, battlewire's RIGS[9:13] and SUB_RIG_CENSUS, and NetSyncClient.SubRigsAreCensus' literals; rows 0-8 are
    s139's, untouched (the census's calibration reproduces them); the live stack holds exactly the thirteen; each model is
    its character's plain GEO_SUB_F0 body by the kit's copy of GEO."""
    from ff9mapkit._modeldb import MODELS
    rj = _json("rigs_8_11.json")
    assert tuple(rj["columns"]) == BW.RIG_COLUMNS
    assert sorted(rj["rows"], key=int) == ["9", "10", "11", "12"]
    for rig in range(9, 13):
        row = rj["rows"][str(rig)]
        assert row["char_id"] == rig - 1 and BW.char_to_rig(rig - 1) == rig and BW.rig_to_char(rig) == rig - 1, rig
        assert row["name"] == BW.RIG_NAMES[rig], rig
        assert tuple(row["row"]) == BW.RIGS[rig] == BW.SUB_RIG_CENSUS[rig], rig
        assert {c: row["cols"][c] for c in BW.RIG_COLUMNS} == dict(zip(BW.RIG_COLUMNS, BW.RIGS[rig])), rig
        assert row["model_facts"]["geo"] == MODELS[BW.RIGS[rig][0]] == f"GEO_SUB_F0_{('CNA', 'MRC', 'BLN', 'BTX')[rig - 9]}"
    assert rj["calibration_reproduces_s139"] is True
    new = _rig_rows(_added("NetSyncVisitor.cs", "s140"))
    assert new == list(BW.RIGS[9:13]), new
    live = _rig_rows(net_lines_ordered("NetSyncVisitor.cs", r"new Rig\("))          # FILE order (s141 rewrites 3 / 7)
    assert live == list(BW.RIGS) and len(live) == BW.RIG_ROW_COUNT == 13, live
    assert _rig_rows(_added("NetSyncVisitor.cs", "s139")) == list(BW.S139.RIGS)       # s139's nine, as it wrote them
    lits = [tuple(int(x) for x in m.group(1).split(","))
            for t in _added("NetSyncClient.cs", "s140") for m in [re.search(r"RigIs\((\d+(?:,\s*-?\d+){16})\)", t)] if m]
    assert {r[0]: r[1:] for r in lits} == BW.SUB_RIG_CENSUS, lits
    assert BW.sub_rigs_are_census() and not BW.sub_rigs_are_census(BW.RIGS[:9] + BW.RIGS[10:11] + BW.RIGS[9:10] + BW.RIGS[11:])


def test_a_transposed_or_edited_census_row_is_caught():
    """The pins above can fail: two rows swapped, one column slipped, or a row out of CharacterId order each break the
    census twin (and so the engine's own SubRigsAreCensus, which holds the same literals)."""
    rows = list(BW.RIGS)
    swapped = rows[:9] + [rows[10], rows[9]] + rows[11:]
    slipped = rows[:12] + [rows[12][:1] + (rows[12][2],) + (rows[12][1],) + rows[12][3:]]
    assert not BW.sub_rigs_are_census(swapped) and not BW.sub_rigs_are_census(slipped)
    assert BW.sub_rigs_are_census(rows)


# ================================================================================================ the frame oracle
def test_the_13_row_frame_oracle_is_the_census_and_the_engines_comment():
    """battlewire.RIG_FRAMES (idle / walk / run / turns / break / alias per rig, the stand-in's MODELLED frame counts) ==
    rigs_8_11.json `frames_13` == the B_FRAME census's frame table (the same p0data5 read, per rig and slot, with the same
    ids as battlewire.RIGS); `rig_idle_frames` on s140 is the thirteen the engine's comments cite; rows 0-8 are s139's
    oracle; an alias has its idle's frames (the same clip). The frame facts s140 leans on: every idle is at least 30 (303:
    2234's literal 20 is safe by margin), every dressed walk shorter than FRA_WALK's 40 (2705 needs the B_FRAME law)."""
    rj = _json("rigs_8_11.json")
    bs = _json("bframe_sites.json")
    for rig in range(13):
        want = rj["frames_13"][str(rig)]
        assert want["name"] == BW.RIG_NAMES[rig]
        assert tuple(want[c] for c in BW.RIG_FRAME_COLUMNS) == BW.RIG_FRAMES[rig], rig
        ft = bs["frame_table"]["rigs"][rig]
        assert ft["rig"] == rig and ft["model"] == BW.RIGS[rig][0], rig
        assert {c: ft["frames"][c] for c in BW.RIG_FRAME_COLUMNS} == dict(zip(BW.RIG_FRAME_COLUMNS, BW.RIG_FRAMES[rig]))
        r = BW.rig_row(rig)
        assert {c: ft["ids"][c] for c in BW.RIG_FRAME_COLUMNS} == {c: r[c] for c in BW.RIG_FRAME_COLUMNS}, rig
        assert BW.RIG_FRAMES[rig][6] == BW.RIG_FRAMES[rig][0], rig            # the alias plays the idle's clip
        assert (BW.RIG_FRAMES[rig][5] is None) == (r["inactive"] == 0), rig
    assert list(BW.RIG_IDLE_FRAMES) == RIG_IDLE_13 == rj["frames_check"]["rig_idle_frames_13"]
    assert RIG_IDLE_13[:9] == rj["frames_check"]["s139_oracle"] and rj["frames_check"]["match"] is True
    assert list(FG.FAKE_RIG_IDLE_FRAMES) == RIG_IDLE_13 and list(FG.FAKE_RIG_IDLE_FRAMES_S139) == RIG_IDLE_13[:9]
    assert min(BW.RIG_IDLE_FRAMES) == 30 > 20 and all(f[1] < 40 for f in BW.RIG_FRAMES[1:])
    clips = bs["frame_table"]["clips"]
    assert {int(k): clips[str(k)]["src_frames"] for k in BW.SOURCE_FRAMES} == BW.SOURCE_FRAMES
    oracle = "[" + ", ".join(str(f) for f in RIG_IDLE_13) + "]"
    assert any(oracle in t for t in _added("NetSyncVisitor.cs", "s140")), oracle
    assert any(oracle.replace(" ", "") in t for t in _added("HarnessAgent.cs", "s140"))
    assert bs["frame_table"]["cross_check_rigs_8_11"] == "every rig x slot equals frames_13"


# ================================================================================================ the loco-class table
def _cs_loco_table() -> tuple:
    """NetSyncSelfDress.LocoClassSuffixes as the s140 patch writes it: one tuple of suffixes per row, row index = code."""
    lines = _added("NetSyncSelfDress.cs", "s140")
    i = lines.index("private static readonly String[][] LocoClassSuffixes =")
    j = lines.index("};", i)
    rows = []
    for t in lines[i + 2:j]:
        if t.startswith("new String[0]"):
            rows.append(())
            continue
        m = re.match(r"new String\[\] \{ (.*) \},", t)
        assert m, t
        rows.append(tuple(re.findall(r'"([A-Z0-9_]+)"', m.group(1))))
    return tuple(rows)


def test_the_loco_class_table_is_the_engines_and_the_census_on_every_name():
    """THE CLOSED TABLE (amendment 3; classify by NAME): the s140 patch's LocoClassSuffixes == battlewire's
    LOCO_CLASS_SUFFIXES == loco_table.json `engine_map` (its 40 non-OTHER full names), the class codes the C# constants
    (0-5 the wire's LocoOther..LocoTurnR); battlewire.loco_class_of answers the JSON's class on ALL 401 ZDN names -- and
    the generator's own rule (gen_loco_table.classify_name) agrees on every one; every one of the 801 ids classifies by
    its NAME through the kit's copy of AnimationDB (200 and 324 both IDLE); null and a non-ZDN name are OTHER; the SelfTest
    sample (LocoSampleIds / LocoSampleCodes) is the JSON's `selftest_rows` and battlewire's LOCO_SAMPLE."""
    lt = _json("loco_table.json")
    gen = _module("gen_loco_table")
    cs = _cs_loco_table()
    assert cs == BW.LOCO_CLASS_SUFFIXES and len(cs) == 8 and cs[0] == ()
    codes = {name: c["code"] for name, c in lt["classes"].items()}
    assert tuple(codes) == BW.LOCO_CLASS_NAMES and list(codes.values()) == list(range(8))
    engine_map = {full: code for full, _cls, code in lt["engine_map"]}
    assert engine_map == BW.LOCO_CLASS_BY_NAME and len(engine_map) == 40
    assert all(codes[cls] == code for _full, cls, code in lt["engine_map"])
    assert len(lt["table"]) == 401 and len(lt["by_id"]) == 801
    for suffix, cls in lt["table"].items():                    # the table is keyed on the suffix after the prefix
        name = BW.LOCO_CLASS_PREFIX + suffix
        assert BW.loco_class_of(name) == codes[cls] == codes[gen.classify_name(name)], name
    for anim, (suffix, cls) in lt["by_id"].items():
        assert BW.anim_name(int(anim)) == BW.LOCO_CLASS_PREFIX + suffix, (anim, suffix)
        assert BW.loco_class_of_id(int(anim)) == codes[cls], (anim, suffix)
    assert BW.loco_class_of_id(200) == BW.loco_class_of_id(324) == BW.LOCO_CLASS_IDLE
    assert BW.loco_class_of(None) == BW.loco_class_of("ANH_MAIN_F0_FRJ_IDLE") == BW.loco_class_of(7) == BW.LOCO_CLASS_OTHER
    sample = tuple((anim, code) for anim, _name, _cls, code in lt["selftest_rows"])
    assert sample == BW.LOCO_SAMPLE
    text = " ".join(_added("NetSyncSelfDress.cs", "s140"))
    ids = re.search(r"LocoSampleIds = \{ ([\d, ]+) \};", text).group(1)
    cc = re.search(r"LocoSampleCodes = \{ ([\d, ]+) \};", text).group(1)
    assert tuple(zip(map(int, ids.split(",")), map(int, cc.split(",")))) == BW.LOCO_SAMPLE
    assert ("internal const Byte LocoClassOther = 0, LocoClassIdle = 1, LocoClassWalk = 2, LocoClassRun = 3, "
            "LocoClassTurnL = 4," in text and "LocoClassTurnR = 5, LocoClassInactive = 6, LocoClassJumpLadder = 7;" in text)
    assert (BW.LOCO_CLASS_OTHER, BW.LOCO_CLASS_TURN_R) == (BW.LOCO_OTHER, BW.LOCO_TURN_R)
    assert BW.loco_table(BW.loco_class_of) is None


def test_the_loco_table_pin_can_fail():
    """The design's literal suffix rule (MutantSuffixClass: CHO_WALK a walk -- a dressed rider walking in mid-air) is
    caught by the sample AND disagrees with the census table on real names; dropping one qualified row from the closed
    table is caught by the all-names check."""
    lt = _json("loco_table.json")
    codes = {name: c["code"] for name, c in lt["classes"].items()}
    assert BW.loco_table(BW.mutant_suffix_class) == "12782 ANH_MAIN_F0_ZDN_CHO_WALK"
    full = {BW.LOCO_CLASS_PREFIX + n: cls for n, cls in lt["table"].items()}
    wrong = [n for n, cls in full.items() if BW.mutant_suffix_class(n) != codes[cls]]
    assert "ANH_MAIN_F0_ZDN_CHO_WALK" in wrong and "ANH_MAIN_F0_ZDN_FRA_WALK_1" not in wrong
    dropped = {k: v for k, v in BW.LOCO_CLASS_BY_NAME.items() if k != "ANH_MAIN_F0_ZDN_FRA_WALK"}
    assert [n for n, cls in full.items() if dropped.get(n, 0) != codes[cls]] == ["ANH_MAIN_F0_ZDN_FRA_WALK"]


@pytest.mark.skipif(not (MEMORIA / "Assembly-CSharp" / "Global" / "ff9" / "FF9DBAll.Animation.cs").is_file(),
                    reason="no Memoria clone (FF9DBAll.Animation.cs): the generator reads the open-source AnimationDB")
def test_the_loco_generator_reproduces_its_frozen_table():
    """gen_loco_table.py --check (with no exports: the evidence block is not compared) rebuilds loco_table.json from the
    open-source FF9DBAll.Animation.cs and finds no drift."""
    out = subprocess.run([sys.executable, "-X", "utf8", str(CENSUS / "gen_loco_table.py"), "--check", "--exports", ""],
                         capture_output=True, text=True, timeout=120)
    assert out.returncode == 0 and "matches (401 names, 801 ids)" in out.stdout, (out.stdout, out.stderr[-2000:])


# ================================================================================================ the B_FRAME census
@pytest.fixture(scope="module")
def census():
    """(the evaluator module, the frozen doc, evaluate_all over it) -- evaluated once per module (~3 s)."""
    bc = _module("bframe_census")
    doc = _json("bframe_sites.json")
    return bc, doc, bc.evaluate_all(doc)


def _codes(bc, ev) -> dict:
    return {k: bc.verdict_codes(v) for k, v in ev["sites"].items()}


def _reds(codes: dict, law: str) -> dict:
    """{site: [rigs whose code is not '.']} under ``law``."""
    return {k: [r for r, ch in enumerate(v[law]) if ch != "."] for k, v in codes.items() if set(v[law]) != {"."}}


T3_TIMELINE_REDS = {"307:1478": [2, 6, 10], "307:1558": [1, 2, 5, 6, 7, 9, 10, 11, 12],
                    "307:1562": [1, 2, 4, 5, 6, 7, 9, 10, 11, 12], "2934:474": [1, 2, 5, 6, 7, 9, 10, 11, 12]}
T2_BFRAME_REDS = {k: list(range(1, 13)) for k in ("2705:1264", "2705:1285", "2705:1305")}


def _bframe_remap_oracle(lt: dict, cls: str, rig: dict) -> bool:
    """loco_table.json's `bframe_remap` for ``cls`` on ``rig`` -- the INDEPENDENT oracle (never the module's is_loco)."""
    rule = lt["classes"][cls]["bframe_remap"]
    return rule == "always" or (rule == "iff rig.Inactive != 0" and bool(rig["ids"].get("inactive")))


def _problems(bc, doc, ev) -> list:
    """Every census check's failures (T1-T7), as strings -- [] when the laws hold: the test asserts [], and each mutant
    must make it non-empty."""
    lt = _json("loco_table.json")
    out = []
    codes = _codes(bc, ev)
    # T1: no drift, and every bound reachable under the stock calibration AND the s140 laws on all 13 rigs
    if codes != doc["verdicts"]:
        out.append("T1 drift: " + ", ".join(k for k in codes if codes[k] != doc["verdicts"].get(k))[:200])
    for law in ("stock", "s140"):
        bad = _reds(codes, law)
        if bad:
            out.append(f"T1 {law} unreachable: {dict(list(bad.items())[:5])}")
    # T2 / T3: each lever's red is exactly its sites
    if _reds(codes, "bframe_off") != T2_BFRAME_REDS:
        out.append(f"T2 bframe_off reds {_reds(codes, 'bframe_off')}")
    if _reds(codes, "timeline_off") != T3_TIMELINE_REDS:
        out.append(f"T3 timeline_off reds {_reds(codes, 'timeline_off')}")
    # T4: every body duration read answers its timeline under s140; under bframe_off exactly the remapped loco rigs
    rigs, durs = doc["frame_table"]["rigs"], doc["frame_table"]["clips"]
    for k, mism in ev["durations"].items():
        if mism["s140"]:
            out.append(f"T4 s140 duration mismatch {k}: {mism['s140']}")
        site = next(s for s in doc["duration_sites"] if s["key"] == k)
        d = durs[str(site["id"])]
        want = [r["rig"] for r in rigs if r["rig"] != 0 and _bframe_remap_oracle(lt, d["class"], r)
                and r["frames"][bc.SLOT_OF_CLASS[d["class"]]] != d["src_frames"]]
        if sorted(mism["bframe_off"]) != want:
            out.append(f"T4 bframe_off {k}: {mism['bframe_off']} != {want}")
    # T5: the law rows, restated by hand (GetAnimDuration id, rig, law -> frames)
    by = {r["rig"]: r for r in rigs}
    for anim, rig, law, want in ((8847, 8, "s140", 16), (8847, 8, "bframe_off", 40), (8847, 0, "s140", 40),
                                 (186, 4, "s140", 70), (186, 1, "s140", 50), (186, 1, "bframe_off", 70),
                                 (2572, 2, "s140", 70), (7935, 8, "s140", 10), (185, 6, "s140", 83),
                                 (185, 12, "s140", 64)):
        got = bc.bframe(anim, durs[str(anim)], by[rig], law, True)
        if got != want:
            out.append(f"T5 GetAnimDuration({anim}) on rig {rig} under {law}: {got} != {want}")
    # T6: the census's shape
    sm = doc["summary"]
    if (sm["threshold_sites"], sm["waits"], sm["tests"], sm["duration_reads"]) != (650, 375, 275, 31):
        out.append(f"T6 counts {sm['threshold_sites'], sm['waits'], sm['tests'], sm['duration_reads']}")
    dur_waits = sorted(s["key"] for s in doc["threshold_sites"] if s["form"] == "wait" and s["rhs"]["kind"] == "dur")
    if dur_waits != sorted(T2_BFRAME_REDS):
        out.append(f"T6 duration-bound waits {dur_waits}")
    lit = sorted(s["key"] for s in doc["threshold_sites"] if s["form"] == "wait" and s["cond_py"] != "F != 0")
    if collections_counter(k.split(":")[0] for k in lit) != {"302": 3, "303": 3, "304": 3, "307": 4, "2705": 3,
                                                               "2934": 2}:
        out.append(f"T6 non-`!= 0` waits {lit}")
    if [(r["key"], r["min_s140_frame_n"]) for r in sm["loco_family_literal_waits"]] != [("303:2234", 30)]:
        out.append(f"T6 literal waits on a native timeline {sm['loco_family_literal_waits']}")
    # T7: the frame table is the census's
    rj = _json("rigs_8_11.json")
    for r in rigs:
        want = rj["frames_13"][str(r["rig"])]
        if any(r["frames"][c] != want[c] for c in BW.RIG_FRAME_COLUMNS):
            out.append(f"T7 rig {r['rig']} frames {r['frames']} != {want}")
    if [r["frames"]["idle"] for r in rigs] != RIG_IDLE_13:
        out.append("T7 rig_idle_frames")
    return out


def collections_counter(it) -> dict:
    out: dict = {}
    for k in it:
        out[k] = out.get(k, 0) + 1
    return out


def test_every_stock_threshold_stays_reachable_on_all_13_rigs_under_the_s140_laws(census):
    """THE BLOCKING LAW (amendment 1), over the FROZEN census: T1 no drift, every one of the 650 sites reachable under the
    stock calibration and the s140 laws on all 13 rigs; T2 `law bframe off` wedges exactly 2705's three loops on rigs 1-12
    (the walk branch; the stand branch only Garnet / Eiko / Marcus); T3 `law timeline off` exactly 307 x 3 and 2934:474;
    T4 every body GetAnimDuration answers its timeline under s140, and under bframe_off exactly the rigs the loco table's
    `bframe_remap` predicts (computed here, never by the module's own is_loco); T5 the law rows by hand; T6 the census's
    shape (650 / 375 / 275 / 31, the 2705 trio the only duration-bound waits, 303:2234 the only literal wait on a native
    timeline -- safe by margin, its shortest idle 30 > 20); T7 the frame table is the census's."""
    bc, doc, ev = census
    assert _problems(bc, doc, ev) == []
    v = doc["summary"]["field_2705"]["2705:1264"]["bframe_off"]
    assert (v["move:walk"]["wedge_rigs"], v["move:arrived_idle"]["wedge_rigs"]) == (list(range(1, 13)), [2, 6, 10])
    # the twin agrees with the census evaluator on the rows it shares: the B_FRAME target's native frames
    for rig, anim, frames in ((8, 8847, 16), (4, 8847, 24), (8, 7935, 10), (1, 186, 50)):
        assert BW.rig_clip_frames(rig, BW.bframe_target(rig, anim, True, True)) == frames, (rig, anim)
    for rig, anim in ((4, 186), (12, 185), (4, 12782)):
        assert BW.bframe_target(rig, anim, True, True) == anim                  # a gesture: stock (its source timeline)


def _mutant(name: str):
    """A FRESH evaluator module with one fault planted, and the doc it runs on (the census stage's M1-M6)."""
    bc = _module("bframe_census")
    doc = _json("bframe_sites.json")
    if name == "M1_bframe_raw":                    # B_FRAME answers the raw clip: the law dropped
        bc.bframe = lambda dur_id, dur, rig, law, gcur_is_body: int(dur["src_frames"])
    elif name == "M2_inactive_always_loco":        # INACTIVE a loco family on every rig (no `iff rig.Inactive != 0`)
        orig = bc.is_loco
        bc.is_loco = lambda cls, rig: True if cls == "INACTIVE" else orig(cls, rig)
        nat = bc.native_frames
        bc.native_frames = lambda cls, rig: (int(rig["frames"]["idle"]) if cls == "INACTIVE"
                                             and not rig["frames"].get("inactive") else nat(cls, rig))
    elif name == "M3_no_keep_source":              # KeepSourceTimeline dropped: a gesture plays the alias natively
        orig = bc.timeline_frames
        bc.timeline_frames = lambda cand, rig, law: orig(cand, rig, "timeline_off" if law == "s140" else law)
    elif name == "M4_garnet_idle_20":              # Garnet's idle edited from 30 to 20
        for r in doc["frame_table"]["rigs"]:
            if r["rig"] == 2:
                r["frames"]["idle"] = r["frames"]["idle_alias"] = 20
    elif name == "M5_2705_dropped":                # the 2705 sites dropped from the census
        doc["threshold_sites"] = [s for s in doc["threshold_sites"] if not s["key"].startswith("2705:")]
        doc["verdicts"] = {k: v for k, v in doc["verdicts"].items() if not k.startswith("2705:")}
    elif name == "M6_off_by_one":                  # the engine model capped and wrapped at frameN (not frameN - 1)
        fv = bc.frames_visited
        bc.frames_visited = lambda frame_n, **kw: fv(int(frame_n) + 1, **kw)
    return bc, doc


@pytest.mark.parametrize("name,check", [("M1_bframe_raw", "T1"), ("M2_inactive_always_loco", "T4"),
                                        ("M2_inactive_always_loco", "T5"), ("M3_no_keep_source", "T1"),
                                        ("M4_garnet_idle_20", "T1"), ("M5_2705_dropped", "T2"),
                                        ("M6_off_by_one", "T3")])
def test_each_census_mutant_turns_its_check_red(name, check):
    """A check that cannot fail is not a check: each planted fault makes the census check named red -- M1 (the law
    dropped) T1 at 2705, M2 (INACTIVE loco everywhere -- invisible to reachability) T4 and T5, M3 (KeepSourceTimeline
    dropped) T1 at 307 / 2934, M4 (Garnet's idle 20) T1 at 303:2234, M5 (the 2705 sites dropped) T2, M6 (an off-by-one
    engine model) T3."""
    bc, doc = _mutant(name)
    problems = _problems(bc, doc, bc.evaluate_all(doc))
    assert any(p.startswith(check) for p in problems), problems


def _install_gate():
    """The regeneration's inputs, or the reason to skip (never write the install; a fresh worktree skips too)."""
    game = pathlib.Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
    try:
        from ff9mapkit import config
        found = config.find_game_path(None)
        if found:
            game = pathlib.Path(found)
    except Exception:                                       # noqa: BLE001 - no install configured
        pass
    if not (game / "StreamingAssets" / "p0data5.bin").is_file():
        return None, "no FF9 install (StreamingAssets/p0data5.bin)"
    if not EXPORTS.is_dir() or len(list(EXPORTS.glob("test2_*.txt"))) < 817:
        return None, f"no HW field-script exports ({EXPORTS}, 817 test2_*.txt)"
    for rel in ("Assembly-CSharp/Global/ff9/FF9DBAll.Animation.cs", "Assembly-CSharp/Global/ff9/Battle/FF9BattleDB.GEO.cs",
                "Assembly-CSharp/Global/Model/ModelFactory.cs"):
        if not (MEMORIA / rel).is_file():
            return None, f"no Memoria clone file {rel}"
    if importlib.util.find_spec("UnityPy") is None:
        return None, "UnityPy is not installed"
    return game, None


def test_the_census_regenerates_byte_for_byte_from_the_install():
    """INSTALL-GATED (READ-ONLY): with the 817 exports, p0data5, UnityPy and the Memoria clone's tables present,
    bframe_census.build() reproduces bframe_sites.json byte for byte (the CLI's --check, ~10 s). Skips cleanly otherwise --
    and the census asserts its kit is THIS tree's (a mismatch fails loudly, it never skips)."""
    game, why = _install_gate()
    if game is None:
        pytest.skip(why)
    out = subprocess.run([sys.executable, "-X", "utf8", str(CENSUS / "bframe_census.py"), "--check", "--game", str(game),
                          "--exports", str(EXPORTS), "--memoria", str(MEMORIA)], capture_output=True, text=True,
                         timeout=600)
    assert out.returncode == 0 and out.stdout.startswith("OK:"), (out.stdout, out.stderr[-2000:])


def test_the_rig_rows_regenerate_from_the_install():
    """INSTALL-GATED (READ-ONLY): rigs_8_11.py --check rebuilds the census in memory off the 817 exports, p0data4 / p0data5
    and the Memoria clone's tables and diffs `rows` (every column of rigs 9-12 -- model, eye, the loco ids, the idle alias,
    the footfalls, the step sound, the hand bones) and `frames_13` against the frozen rigs_8_11.json: the other census
    tests pin the patch, the twin and the JSON to EACH OTHER, so an edit made to all three together would stay green --
    this one re-reads the install (~15 s). Skips cleanly without it."""
    game, why = _install_gate()
    if game is None:
        pytest.skip(why)
    out = subprocess.run([sys.executable, "-X", "utf8", str(CENSUS / "rigs_8_11.py"), "--check", "--game", str(game),
                          "--exports", str(EXPORTS), "--memoria", str(MEMORIA)], capture_output=True, text=True,
                         timeout=900)
    assert out.returncode == 0 and "OK: rows 9-12 and frames_13 regenerate exactly" in out.stdout, (out.stdout[-3000:],
                                                                                                     out.stderr[-2000:])


# ================================================================================================ the jump slot's timeline
def test_every_stock_jump_window_keeps_stocks_ticks_on_every_rig():
    """THE JUMP SLOT ON THE SOURCE TIMELINE (the review's ladder finding): for every JUMP / LADDER / OTHER clip a 98+CC
    player entry hands SetJumpAnimation (loco_table.json `evidence.jump_windows`, with each clip's source frame count off
    the census frame table -- bframe_sites.json, regenerated from the install by the gated test above), on EVERY rig 1-12,
    the dressed body's PREJUMP and POSTJUMP tick counts (battlewire.jump_frame_n: the slot holds the idle ALIAS, and
    KeepJumpTimeline puts the SOURCE count back; battlewire.jump_ticks: EventEngine.ProcessAnime's run to min(outFrame,
    frameN - 1)) EQUAL stock's. The mutant without the hook (the alias's own count) is red on every rig for the ladders:
    LADDER_1_1 (2, 6) lands in stock's 0 ticks, on a 30-72 frame alias in 22-64 -- every mount / dismount of ~40 fields
    (Dali 404 on the narrative-state hub lane among them). The engine half -- the three hook sites, AtJumpSlot's raw id --
    is test_harness_netsync.py's source pins."""
    ft = _json("bframe_sites.json")["frame_table"]["clips"]
    jw = _json("loco_table.json")["evidence"]["jump_windows"]["by_name"]
    by_name = {v["name"]: (int(k), int(v["src_frames"])) for k, v in ft.items() if v.get("src_frames")}
    covered, names, held = 0, [], {}
    for suffix, row in sorted(jw.items()):
        hit = by_name.get("ANH_MAIN_F0_ZDN_" + suffix)
        if hit is None:
            continue
        raw, src = hit
        names.append(suffix)
        for rig in range(1, BW.RIG_ROW_COUNT):
            def frames_of(a, rig=rig, raw=raw, src=src):
                return src if a == raw else BW.rig_clip_frames(rig, a)
            for j0, j1 in row["windows"]:
                stock = BW.jump_ticks(src, j0, j1)
                assert BW.jump_ticks(BW.jump_frame_n(rig, raw, frames_of), j0, j1) == stock, (suffix, rig, j0, j1)
                covered += 1
                if suffix == "LADDER_1_1":
                    held[rig] = BW.jump_ticks(BW.jump_frame_n(rig, raw, frames_of, keep=False), j0, j1)[1]
    assert {"LADDER_1_1", "LADDER_2_3", "LADDER_1_3", "LADDER_2_1", "JUMP_3"} <= set(names), names
    assert covered >= 12 * 6, covered
    # the mutant: no KeepJumpTimeline -> the landing runs to the ALIAS's end (its frames - 7) on every rig
    assert set(held) == set(range(1, BW.RIG_ROW_COUNT)) and all(
        held[r] == BW.rig_frames(r, "idle_alias") - 1 - 7 > 0 for r in held), held
    assert BW.jump_ticks(8, 2, 6) == (1, 0) and min(held.values()) == 22 and max(held.values()) == 64, held


def test_the_census_jump_timeline_is_the_engines(census):
    """THE CENSUS MODELS THE JUMP SLOT THE DLL SHIPS (AtJumpSlot + KeepJumpTimeline after PREJUMP / POSTJUMP / SETVY3's
    ExecAnim(actor.jump)): for every jump / land candidate of the frozen sites (29 + 29 over 20 sites), on every rig 0-12
    and under every dressed law, bframe_census.timeline_frames == battlewire.jump_frame_n -- the slot holds the idle alias,
    the SOURCE clip's count is put back while the timeline law is on (s140 and bframe_off: KeepSourceTimeline gates on
    LawTimeline only), the alias's own count under `law timeline off`. Reachability cannot see this (the verdicts agree
    either way: the stock jump windows are reachable on the alias too); this pin keeps the oracle's model the engine's.
    It can fail: the pre-fix model (the alias under every dressed law) drifts on every candidate x rig 1-12 under s140
    and bframe_off, and dropping the hook's law gate (the source under timeline off too) drifts there."""
    bc, doc, _ev = census
    rigs = doc["frame_table"]["rigs"]
    cands = [(s["key"], c) for s in doc["threshold_sites"] for c in s["candidates"] if c["how"] in ("jump", "land")]
    assert (len(cands), len({k for k, _c in cands})) == (58, 20)
    assert all(not bc.is_loco(c["class"], r) for _k, c in cands for r in rigs)      # every stock jump id is a gesture
    laws = ("s140", "bframe_off", "timeline_off")

    def twin(c, r, law):
        raw, src = int(c["id"]), int(c["src_frames"])

        def frames_of(a):
            return src if a == raw else BW.rig_clip_frames(r["rig"], a)
        return BW.jump_frame_n(r["rig"], raw, frames_of, keep=law != "timeline_off")

    def drift(tf):
        return [(k, c["id"], r["rig"], law) for k, c in cands for r in rigs for law in laws
                if tf(c, r, law) != twin(c, r, law)]
    assert drift(bc.timeline_frames) == []
    pre_fix = drift(lambda c, r, law: int(c["src_frames"]) if r["rig"] == 0 else int(r["frames"]["idle_alias"]))
    assert {law for *_x, law in pre_fix} == {"s140", "bframe_off"} and len(pre_fix) == 58 * 12 * 2, len(pre_fix)
    ungated = drift(lambda c, r, law: bc.timeline_frames(c, r, "s140"))
    assert {law for *_x, law in ungated} == {"timeline_off"} and len(ungated) == 58 * 12, len(ungated)
