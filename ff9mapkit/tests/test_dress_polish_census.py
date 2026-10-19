"""[ff9mapkit netsync s141] THE DRESS POLISH -- the offline CENSUS tests (studies/battle-coop/R3-FIELD-MODEL-AUDIT.md 2.4
amendments 1-6, its 4.5 leg F; the orchestrator's O1 and O4-O8).

The census (studies/battle-coop/dress-census/polish_census.py -> polish.json: a frozen, reproducible read of the user's own
install through the kit's readers -- numbers and open-source names only) is leg F's ORACLE. Each instrument here is pinned
three ways -- to the engine (the s141 patch's rig table and PolishSelfTest's literals, read off ``memoria-patches/``), to
battlewire's twins, and to the census JSON that derived it -- and each pin is shown able to fail (a mutant document):

  * THE RIG TABLE the census replayed (`rigs`) == the live stack's thirteen Rig rows == battlewire.RIGS, every column.
  * FIELD 250's FOOTSTEPS (`a_field250`): Zidane_Init's twelve ops == Zidane_13's (the warm return's) == BW.FIELD250_STEPS;
    every rig's `steps` / drops after one load, under `polish off` and after a warm return == battlewire's replay of those
    ops through MapFootstep's twin (BW.replay_steps) == FIELD250_ORACLE; leg F's rows (`bench`: F1, F2, F2c, F3, F6, F7).
  * CINNA WALKS SILENTLY (O1): no CHRFX 16-19 registration on any CNA body; her row's -1 footfalls drop all twelve.
  * THE LIGHTING ORACLE (`d_lighting`): field 250's three mapconfig rows and five lights == BW.FIELD250_MCF; every floor's
    tint under the 98 row and the default row == BW.mcf_light_color; F4 / F4g; the 818 / 474 / 344 mapconfig counts.
  * THE HAND BONES (`e_hands`): every rig's R_hand / R_hand_end == the rig table's HandBone / HandBoneEnd == the proof's
    literals; F8's parent names == "bone%03d" of BW.attach_bone_rule's bone, both lever states.
  * THE CENSUS'S OWN TWINS' selftest (`twin_selftest`): every row green, every mutant caught.
  * THE REGENERATION from the install (polish_census.py --check) -- INSTALL-GATED: it skips cleanly without the install,
    the 817 HW exports, UnityPy or the Memoria clone (and, per the worktree skip trap, read a skip as "not run", never green).
"""
import copy
import importlib.util
import json
import pathlib
import re
import subprocess
import sys

import pytest

from ._patchstack import msr, net_lines

REPO = pathlib.Path(__file__).resolve().parents[2]
CENSUS = REPO / "studies" / "battle-coop" / "dress-census"
sys.path.insert(0, str(REPO / "tools"))
from harness import battlewire as BW                                   # noqa: E402

MEMORIA = pathlib.Path(r"C:\gd\FFIX\Memoria")
EXPORTS = pathlib.Path(r"C:\gd\FFIX\reference\test2")
DROP_RIGS = (5, 8, 9)                                                  # Quina, the moogle, Cinna: no footfall frames


def _doc() -> dict:
    return json.loads((CENSUS / "polish.json").read_text(encoding="utf-8"))


def _key(i: int) -> str:
    return f"{i} {BW.RIG_NAMES[i]}"


def _rig_rows(lines) -> list:
    rows = []
    for t in lines:
        m = re.match(r"new Rig\(([-\d,\s]+)\),", t)
        if m:
            rows.append(tuple(int(x) for x in m.group(1).split(",")))
    return rows


# ================================================================================================ the pins, as one judge
def _problems(doc: dict) -> list:
    """Every census pin's failures (P1-P6) as strings -- [] when the census, battlewire's twins and the engine's fixtures
    agree; each mutant document must make it non-empty."""
    out = []
    rigs = [dict(zip(BW.RIG_COLUMNS, r)) for r in BW.RIGS]
    # P1: the rig table the census replayed is battlewire's (the live stack's: test_the_census_rig_table_is_the_stacks)
    got = [tuple(r[c] for c in BW.RIG_COLUMNS) for r in doc["rigs"]]
    if got != list(BW.RIGS) or [r["name"] for r in doc["rigs"]] != list(BW.RIG_NAMES):
        out.append(f"P1 rigs {[i for i, r in enumerate(got) if i >= len(BW.RIGS) or r != BW.RIGS[i]]}")
    # P2: field 250's ops and every rig's one-load / polish-off / warm-return table, through MapFootstep's twin
    a = doc["a_field250"]
    ops = [(o["code"], o["anim"], o["frame"], o["arg4"]) for o in a["load_ops"]]
    if ops != list(BW.FIELD250_STEPS) or [(o["code"], o["anim"], o["frame"], o["arg4"]) for o in a["reinit_ops"]] != ops:
        out.append(f"P2 field 250's ops {ops}")
    if (a["field"], a["load_ops_n"], a["reinit_ops_n"], a["load_equals_reinit"]) != (250, 12, 12, True):
        out.append("P2 field 250's op counts")
    for i, rig in enumerate(rigs):
        row = a["per_rig"][_key(i)]
        for stage, kw in (("s141", {}), ("s141_polish_off", {"polish": False}), ("s141_warm_return", {})):
            mine = BW.replay_steps(rig, BW.FIELD250_STEPS, **kw)
            want = {k: row[stage][k] for k in ("steps", "steps_dropped", "steps_passed")}
            if {k: mine[k] for k in want} != want or row[stage]["faults"]:
                out.append(f"P2 {_key(i)} {stage}: census {want} twin {[mine[k] for k in want]}")
        if row["s141"]["steps"] != BW.FIELD250_ORACLE[i]:
            out.append(f"P2 {_key(i)}: census steps {row['s141']['steps']} != FIELD250_ORACLE")
        if (row["s141"]["steps_dropped"] == 12) != (i in DROP_RIGS):
            out.append(f"P2 {_key(i)}: a drop rig is exactly Quina, the moogle and Cinna")
    # P3: Cinna (O1) -- no stock registration on any CNA body, so her row's -1 footfalls are stock's
    cna = doc["c_subs"]["CNA"]
    if (cna["rig"], cna["registrations_on_family_anims"], cna["registrations_by_family_body"]) != (9, 0, 0) or \
            (BW.RIGS[9][8], BW.RIGS[9][10]) != (-1, -1):
        out.append(f"P3 Cinna: {cna['registrations_on_family_anims']} registrations, row {BW.RIGS[9][8:12]}")
    # P4: field 250's mapconfig and every floor's tint, F4 / F4g, the counts
    d = doc["d_lighting"]
    f250 = d["field250"]
    chars = tuple((c["geo"], c["shadowI"], c["shadowR"], tuple(c["clr"])) for c in f250["chars"])
    lights = tuple((lt["type"], tuple(lt["clr"]), tuple(lt["floor"])) for lt in f250["lights"])
    if (chars, lights) != (BW.FIELD250_MCF["chars"], BW.FIELD250_MCF["lights"]):
        out.append(f"P4 field 250's mapconfig {chars} {lights}")
    for floor, v in f250["floors"].items():
        for kind, src, polish in (("dressed_98_row", 98, True), ("default_row", 98, False), ("zidane_own_98", 0, True)):
            model = 98 if kind == "zidane_own_98" else 192
            mine = BW.mcf_light_color(BW.FIELD250_MCF, model, int(floor), src, polish)
            if (mine["row"], mine["rgb"]) != (v[kind]["row"], v[kind]["rgb"]):
                out.append(f"P4 floor {floor} {kind}: census {v[kind]['row']} {v[kind]['rgb']} twin {mine}")
    for k, v in f250["per_rig_floor0"].items():
        i = int(k.split()[0])
        for kind, polish in (("s141", True), ("polish_off", False)):
            mine = BW.mcf_light_color(BW.FIELD250_MCF, v["model"], 0, 98 if i else 0, polish)
            if (mine["row"], mine["rgb"]) != (v[kind]["row"], v[kind]["rgb"]):
                out.append(f"P4 {k} {kind}")
        for kind, polish in (("ghost_s141", True), ("ghost_polish_off", False)):
            mine = BW.ghost_mcf_light_color(BW.FIELD250_MCF, v["model"], v["model"], 0, 98 if i else 0, polish)
            if (mine["row"], mine["rgb"]) != (v[kind]["row"], v[kind]["rgb"]):
                out.append(f"P4 {k} {kind}")
    m = d["mcfs"]
    if (m["total"], m["with_default_row"], m["with_98_row"], m["lacking_98_row"], m["unparsed"]) != (818, 818, 474, 344, []):
        out.append(f"P4 mapconfig counts {m}")
    # P5: the hand bones -- the table's, the proof's literals, the skeleton's names, F8's parents
    for i, rig in enumerate(rigs):
        h = doc["e_hands"][_key(i)]
        pair = (rig["hand_bone"], rig["hand_bone_end"])
        if (h["hand_bone"], h["hand_bone_end"]) != pair or tuple(h["expected"]) != pair or not h["agree"] or \
                pair != BW.POLISH_HAND_ORACLE[i] or not h["hand_bones_exist"] or not h["name_format_ok"]:
            out.append(f"P5 {_key(i)} hand bones {h['hand_bone']}/{h['hand_bone_end']} table {pair}")
        if (h["hand_bone_name"], h["hand_bone_end_name"]) != (BW.bone_name(pair[0]), BW.bone_name(pair[1])):
            out.append(f"P5 {_key(i)} names")
        for bone in (12, 13):
            for polish, tag in ((True, "s141"), (False, "polish_off")):
                want = BW.bone_name(BW.attach_bone_rule(rig, bone, polish)[0])
                if h[f"f8_parent_bone{bone}_{tag}"] != want:
                    out.append(f"P5 {_key(i)} F8 bone {bone} {tag}: census {h[f'f8_parent_bone{bone}_{tag}']} twin {want}")
    # P6: the census twins' own selftest and leg F's rows
    t = doc["twin_selftest"]
    if not (t["ok"] and t["every_mutant_caught"] and not t["fails"] and all(v > 0 for v in t["mutants_rows_wrong"].values())):
        out.append(f"P6 twin_selftest {t}")
    b = doc["bench"]
    for leg, i in (("F1 freya", 4), ("F2 moogle", 8), ("F2c cinna", 9), ("F7 steiner", 3)):
        if b[leg]["s141"]["steps"] != BW.FIELD250_ORACLE[i] or b[leg]["s141_polish_off"]["steps"] != BW.FIELD250_ORACLE[0]:
            out.append(f"P6 {leg}")
    if b["F3 zidane control"]["any_stage"]["steps"] != BW.FIELD250_ORACLE[0] or \
            b["F6 freya warm return"]["s141"]["steps"] != BW.FIELD250_ORACLE[4]:
        out.append("P6 F3 / F6")
    if (b["F4 light floor0"]["s141"], b["F4 light floor0"]["s141_polish_off"]) != (
            {"light_row": 98, "light_rgb": [80, 96, 120]}, {"light_row": 65535, "light_rgb": [128, 128, 128]}):
        out.append("P6 F4")
    if doc["table_disagreements"]:
        out.append(f"P6 table disagreements {doc['table_disagreements']}")
    return out


def test_the_census_is_the_twins_and_the_engines_fixtures():
    """Every pin holds on the frozen census (P1-P6 above): the rig table, field 250's twelve ops (load == warm return), every
    rig's leg-F `steps` / drops through MapFootstep's twin (on, `polish off`, a warm return), Cinna's silence (O1), field
    250's mapconfig and every floor's tint, F4 / F4g, the 818 / 474 / 344 mapconfig counts, every rig's hand bones and
    F8's parent names, the census twins' own selftest, leg F's rows."""
    assert _problems(_doc()) == []


def _mutant(name: str) -> dict:
    doc = _doc()
    if name == "P1_cell":                          # the census replayed a table with one cell off (Freya's walk B)
        doc["rigs"][4]["walk_step_b"] = 15
    elif name == "P2_steps":                       # Steiner's per-rig oracle stepping with Zidane's 919
        doc["a_field250"]["per_rig"]["3 steiner"]["s141"]["steps"] = [[1996, 4, 919], [1996, 14, 919], [2005, 0, 919],
                                                                       [2005, 9, 919]]
    elif name == "P2_warm":                        # a warm return that doubled (no per-load reset)
        doc["a_field250"]["per_rig"]["8 moogle"]["s141_warm_return"]["steps_dropped"] = 24
    elif name == "P2_reinit":                      # Main_Reinit's ops drifting from the load's
        doc["a_field250"]["reinit_ops"] = doc["a_field250"]["reinit_ops"][:-1]
    elif name == "P3_cinna":                       # a Cinna registration the row ignores
        doc["c_subs"]["CNA"]["registrations_on_family_anims"] = 1
    elif name == "P4_row":                         # the 98 row's colour misread
        doc["d_lighting"]["field250"]["chars"][2]["clr"] = [10, 12, 16]
    elif name == "P4_floor":                       # a floor's tint off the default row
        doc["d_lighting"]["field250"]["floors"]["0"]["dressed_98_row"]["rgb"] = [128, 128, 128]
    elif name == "P5_hand":                        # Cinna's labels_for hand (none) taken for her R_hand
        doc["e_hands"]["9 cinna"]["hand_bone"] = 12
    elif name == "P5_parent":                      # F8's parent from the swapped pair
        doc["e_hands"]["3 steiner"]["f8_parent_bone13_s141"] = "bone014"
    elif name == "P6_twin":                        # a census twin mutant that went uncaught
        doc["twin_selftest"]["mutants_rows_wrong"]["bone_swap"] = 0
    return doc


@pytest.mark.parametrize("name", ["P1_cell", "P2_steps", "P2_warm", "P2_reinit", "P3_cinna", "P4_row", "P4_floor", "P5_hand",
                                  "P5_parent", "P6_twin"])
def test_each_census_pin_can_fail(name):
    """A check that cannot fail is not a check: each planted fault in the census document turns ITS pin red."""
    problems = _problems(_mutant(name))
    assert any(p.startswith(name[:2]) for p in problems), problems


# ================================================================================================ against the engine
def test_the_census_rig_table_is_the_stacks():
    """The census's `rigs` (the clone's NetSyncVisitor.Rigs, parsed by polish_census.parse_rigs) == the live stack's thirteen
    Rig rows (read off memoria-patches/) == battlewire.RIGS; its sha line names the 13 rows."""
    live = _rig_rows(net_lines("NetSyncVisitor.cs", r"new Rig\("))
    doc = _doc()
    assert live == list(BW.RIGS) == [tuple(r[c] for c in BW.RIG_COLUMNS) for r in doc["rigs"]], live
    assert doc["sources"]["rig_table"].endswith("(13 rows)") and "NetSyncVisitor.cs" in doc["sources"]["rig_table"]
    assert doc["schema"] == "ff9mapkit.dress-census.polish/1"


def test_the_proofs_literals_are_the_censuss():
    """PolishSelfTest's PolishFootOracle (read off the s141 patch) states, per rig, the census's walk / run pair and step
    sound (polish.json `a_field250.per_rig[*].pairs` / `step_sound`; -1 for the drop rigs), and its PolishHandOracle the
    census's R_hand / R_hand_end -- the proof's literals are the install's, never the rig table's."""
    per, hands = _doc()["a_field250"]["per_rig"], _doc()["e_hands"]
    for i in range(BW.RIG_ROW_COUNT):
        row = per[_key(i)]
        o = BW.POLISH_FOOT_ORACLE[i]
        assert (row["walk"], row["run"], row["step_sound"]) == (BW.RIGS[i][2], BW.RIGS[i][3], o[6]), i
        want = ([-1, -1], [-1, -1]) if o[0] < 0 else ([o[1], o[2]], [o[4], o[5]])
        assert (row["pairs"]["walk"], row["pairs"]["run"]) == want, i
        if o[0] >= 0:
            assert (o[0], o[3]) == (row["walk"], row["run"]), i
        assert tuple(hands[_key(i)]["expected"]) == BW.POLISH_HAND_ORACLE[i], i
    text = " ".join(t for path, sec in msr.sections(_patch_from("s141")) if path and path.endswith("NetSyncSelfDress.cs")
                    for t in [sec.decode("utf-8", "replace")])
    assert "{ 1996, 4,  14, 2005,  0,  9, 925 }," in text and "{ 24, 25 }, { 5, 6 }, { 13, 14 }, { 15, 16 }," in text


def _patch_from(stem: str) -> bytes:
    names = [n for n in msr.stack() if n.startswith(stem + "-") and n not in msr.DEAD]
    assert len(names) == 1, (stem, names)
    return (msr.PATCHES / names[0]).read_bytes()


def test_the_census_twins_load_and_agree_with_battlewires():
    """polish_census.py's pure twins import cleanly (from ANY tree: its kit pin is the tree, never a worktree path) and agree
    with battlewire's on the census's own cases: map_footstep vs footstep_rule, expected_steps vs replay_steps, the bone
    remap, light_color vs mcf_light_color on field 250's frozen mapconfig."""
    spec = importlib.util.spec_from_file_location("_polish_census_pure", CENSUS / "polish_census.py")
    pc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pc)
    rigs = [dict(zip(BW.RIG_COLUMNS, r)) for r in BW.RIGS]
    for rig in rigs:
        for op in BW.FIELD250_STEPS + ((19, 38, 8, 0), (16, 200, 4, 919), (16, 25, 7, 919)):
            v, a, f, s = BW.footstep_rule(rig, *op)
            assert (BW.STEP_CENSUS_NAMES[v], a, f, s) == tuple(pc.map_footstep(rig, *op, zidane=rigs[0])), (rig, op)
        mine = BW.replay_steps(rig, BW.FIELD250_STEPS)
        assert mine["steps"] == pc.expected_steps(rig, [list(o) for o in BW.FIELD250_STEPS], zidane=rigs[0])["steps"]
        for bone in (0, 12, 13, 19):
            got, v = BW.attach_bone_rule(rig, bone, True)
            assert (got, BW.ATTACH_CENSUS_NAMES[v]) == tuple(pc.remap_attach_bone(rig, bone)), (rig, bone)
    assert pc.DEFAULT_ROW == BW.DEFAULT_MCF_ROW and pc.DRESS_SRC == BW.PLAIN_ZIDANE_MODEL
    assert pc.FOOTSTEP_CODES == BW.FOOTSTEP_CODES and pc.RIG_NAMES == BW.RIG_NAMES and pc.COLUMNS == BW.RIG_COLUMNS


# ================================================================================================ the regeneration
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
    if not (game / "StreamingAssets" / "p0data4.bin").is_file():
        return None, "no FF9 install (StreamingAssets/p0data4.bin)"
    if not EXPORTS.is_dir() or len(list(EXPORTS.glob("test2_*.txt"))) < 817:
        return None, f"no HW field-script exports ({EXPORTS}, 817 test2_*.txt)"
    for rel in ("Assembly-CSharp/Memoria/Netsync/NetSyncVisitor.cs", "Assembly-CSharp/Global/ff9/FF9DBAll.Animation.cs",
                "Assembly-CSharp/Global/ff9/Battle/FF9BattleDB.GEO.cs"):
        if not (MEMORIA / rel).is_file():
            return None, f"no Memoria clone file {rel}"
    if importlib.util.find_spec("UnityPy") is None:
        return None, "UnityPy is not installed"
    return game, None


def test_the_census_regenerates_from_the_install():
    """INSTALL-GATED (READ-ONLY): polish_census.py --check rebuilds the census in memory off the 817 exports, the install's
    mapconfigs and skeletons (the kit's readers) and the clone's rig table, and diffs every oracle key (rigs, a_field250,
    b_steps, c_subs, d_lighting, e_hands, fg_ops, o6_other_sites, twin_selftest, bench, table_disagreements) against the
    frozen polish.json: the pins above tie the patch, the twins and the JSON to EACH OTHER, so an edit made to all three
    together would stay green -- this one re-reads the install. Skips cleanly without it."""
    game, why = _install_gate()
    if game is None:
        pytest.skip(why)
    out = subprocess.run([sys.executable, "-X", "utf8", str(CENSUS / "polish_census.py"), "--check", "--game", str(game),
                          "--exports", str(EXPORTS), "--memoria", str(MEMORIA)], capture_output=True, text=True,
                         timeout=1500)
    assert out.returncode == 0 and "OK: polish.json regenerates exactly" in out.stdout, (out.stdout[-3000:],
                                                                                       out.stderr[-2000:])
