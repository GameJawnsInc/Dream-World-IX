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
    literals == THE INSTALL's pair -- the SKIN (polish_census.skin_hand: the right arm's third skinned bone, its end the
    next bone, else the hand) with stock's own AttachObject on the same body agreeing (stock_hand_check) -- NEVER
    labels_for (one bone toward the shoulder on Steiner's and Amarant's arms: rlook-1 / rlook-2); F8's parent names ==
    "bone%03d" of BW.attach_bone_rule's bone, both lever states.
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

from ._patchstack import msr, net_lines, net_lines_ordered

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
        skin, stock = h.get("skin") or {}, h.get("stock") or {}
        if [skin.get("hand"), skin.get("end")] != list(h["expected"]) or not stock.get("agrees") or \
                "labels_for" in str(h.get("source", "")).replace("never labels_for", ""):
            out.append(f"P5 {_key(i)} the oracle: skin {skin.get('hand')}/{skin.get('end')}, stock agrees "
                       f"{stock.get('agrees')}, source {h.get('source')!r}")
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
    elif name == "P5_hand":                        # Steiner's labels_for hand (14: his ELBOW) taken for his R_hand
        doc["e_hands"]["3 steiner"]["hand_bone"] = 14
    elif name == "P5_stock":                       # stock's own AttachObject on Amarant disagreeing with the skin
        doc["e_hands"]["7 amarant"]["stock"]["agrees"] = False
    elif name == "P5_source":                      # an oracle that came from labels_for
        doc["e_hands"]["4 freya"]["source"] = "labels_for"
    elif name == "P5_parent":                      # F8's parent from the swapped pair
        doc["e_hands"]["3 steiner"]["f8_parent_bone13_s141"] = "bone014"
    elif name == "P6_twin":                        # a census twin mutant that went uncaught
        doc["twin_selftest"]["mutants_rows_wrong"]["bone_swap"] = 0
    return doc


@pytest.mark.parametrize("name", ["P1_cell", "P2_steps", "P2_warm", "P2_reinit", "P3_cinna", "P4_row", "P4_floor", "P5_hand",
                                  "P5_stock", "P5_source", "P5_parent", "P6_twin"])
def test_each_census_pin_can_fail(name):
    """A check that cannot fail is not a check: each planted fault in the census document turns ITS pin red."""
    problems = _problems(_mutant(name))
    assert any(p.startswith(name[:2]) for p in problems), problems


# ================================================================================================ against the engine
def test_the_census_rig_table_is_the_stacks():
    """The census's `rigs` (the clone's NetSyncVisitor.Rigs, parsed by polish_census.parse_rigs) == the live stack's thirteen
    Rig rows (read off memoria-patches/) == battlewire.RIGS; its sha line names the 13 rows."""
    live = _rig_rows(net_lines_ordered("NetSyncVisitor.cs", r"new Rig\("))          # FILE order (s141 rewrites 3 / 7)
    doc = _doc()
    assert live == list(BW.RIGS) == [tuple(r[c] for c in BW.RIG_COLUMNS) for r in doc["rigs"]], live
    assert doc["sources"]["rig_table"].endswith("(13 rows)") and "NetSyncVisitor.cs" in doc["sources"]["rig_table"]
    assert doc["schema"] == "ff9mapkit.dress-census.polish/1"


def _foot_oracle_problems(doc: dict) -> list:
    """PolishFootOracle (battlewire's copy of the s141 proof's literals) against the INSTALL census: per rig, `b_steps.rigs`'
    `census` columns -- the modal RunModelCode(16) frames per rig walk / run clip and the step-sound rule over the 817 stock
    scripts ([-1, -1] for the drop rigs) -- and every `agree` flag (the census vs the table) true. [] = they agree."""
    out = []
    for i in range(BW.RIG_ROW_COUNT):
        b = doc["b_steps"]["rigs"][_key(i)]
        o = BW.POLISH_FOOT_ORACLE[i]
        want = ([-1, -1], [-1, -1], o[6]) if o[0] < 0 else ([o[1], o[2]], [o[4], o[5]], o[6])
        got = (list(b["census"]["walk_pair"]), list(b["census"]["run_pair"]), b["census"]["step_sound"])
        if got != want:
            out.append(f"{_key(i)}: the install census {got}, the proof {want}")
        if not all(b["agree"].values()):
            out.append(f"{_key(i)}: the census and the table disagree {b['agree']}")
    return out


def test_the_proofs_literals_are_the_censuss():
    """PolishSelfTest's literals against the census, two pins. THE INSTALL'S: its PolishFootOracle (read off the s141 patch)
    states, per rig, the INSTALL census's walk / run footfall pair and step sound (polish.json `b_steps.rigs[*].census`:
    the modal stock registrations, never the rig table; -1 for the drop rigs) with every `agree` flag true, and its
    PolishHandOracle the install's R_hand / R_hand_end (`e_hands[*].expected`: the skin's pair, stock's own AttachObject
    agreeing -- never labels_for). THE
    TABLE'S (a copy of the rig table, kept as the table pin): `a_field250.per_rig[*].pairs` / `walk` / `run` / `step_sound`.
    Each pin is shown able to fail on a planted cell."""
    doc = _doc()
    assert _foot_oracle_problems(doc) == []
    bad = copy.deepcopy(doc)
    bad["b_steps"]["rigs"]["4 freya"]["census"]["walk_pair"] = [4, 15]               # the install census one cell off
    assert _foot_oracle_problems(bad) == ["4 freya: the install census ([4, 15], [0, 9], 0), the proof ([4, 16], [0, 9], 0)"]
    bad = copy.deepcopy(doc)
    bad["b_steps"]["rigs"]["3 steiner"]["agree"]["step_sound"] = False
    assert _foot_oracle_problems(bad) and "disagree" in _foot_oracle_problems(bad)[0]
    per, hands = doc["a_field250"]["per_rig"], doc["e_hands"]
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


# ================================================================================================ the hand oracle (rlook-1 / 2)
def _census_pure(name: str):
    spec = importlib.util.spec_from_file_location(name, CENSUS / "polish_census.py")
    pc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pc)
    return pc


def _arm(chain, mirror=False) -> list:
    """A synthetic skeleton: (name, parent, local x, local y, dominant-weight verts) rows -> read_model-shaped bones."""
    s = -1.0 if mirror else 1.0
    return [{"name": n, "parent": p, "pos": (s * x, y, 0.0), "rot": (0.0, 0.0, 0.0, 1.0), "scale": (1.0, 1.0, 1.0)}
            for n, p, x, y, _v in chain]


def _skin_model(leaf_hand: bool = False) -> tuple:
    """Steiner's arm SHAPE (studies/battle-coop/dress-census/polish.json e_hands['3 steiner'].skin.arm): a 0-vertex
    clavicle and shoulder pivot, then the upper arm (13), the forearm (14), the gauntlet (15) and a 0-vertex end leaf
    (16); a mirrored left arm, two legs. ``leaf_hand`` drops the end leaf (Amarant's / Freya's shape)."""
    trunk = [("bone000", None, 0, 0, 0), ("bone010", "bone000", 0, -300, 270), ("bone011", "bone010", 0, -60, 0)]
    right = [("bone012", "bone011", 48, 0, 0), ("bone013", "bone012", 44, 10, 87), ("bone014", "bone013", 69, 70, 48),
             ("bone015", "bone014", 51, 50, 170)] + ([] if leaf_hand else [("bone016", "bone015", 20, 48, 0)])
    left = [("bone020", "bone011", 48, 0, 0), ("bone021", "bone020", 44, 10, 87), ("bone022", "bone021", 69, 70, 48),
            ("bone023", "bone022", 51, 50, 170)]
    legs = [("bone030", "bone000", 40, 0, 120), ("bone031", "bone030", 0, 100, 90),
            ("bone040", "bone000", -40, 0, 120), ("bone041", "bone040", 0, 100, 90)]
    rows = trunk + right + legs
    bones = _arm(rows) + _arm(left, mirror=True)
    weights = [[(int(n[4:]), 1.0)] for n, _p, _x, _y, v in rows + left for _k in range(v)]
    return bones, [{"weights": weights}]


def test_the_hand_oracle_is_the_skin_and_stock_never_labels_for():
    """rlook-1 / rlook-2: THE HAND ORACLE can fail on the table it once agreed with. PURE (no install): the skin rule
    (polish_census.skin_hand) over Steiner's arm SHAPE answers 15 / 16 -- the gauntlet and its 0-vertex end leaf, never
    labels_for's 14 / 15 (his elbow / his wrist) -- and over a vertex-owning leaf hand answers the hand for both; stock's
    own AttachObject (stock_hand_check: a prop Zidane holds at 12 / 13 lands on the body's hand / end) agrees with 15 / 16
    and reads 14 / 15 as a disagreement. Then THE FROZEN CENSUS: Steiner's and Amarant's pairs are the skin's AND stock's
    (Steiner's Purple_Bottle 12 -> 15, Sword 13 -> 16; Amarant carries Vivi on his leaf hand 16), and the pre-fix table
    (Steiner 14 / 15, Amarant 15 / 16) would read `agree` false there."""
    pc = _census_pure("_polish_census_hands")
    bones, meshes = _skin_model()
    sk = pc.skin_hand(bones, meshes)
    assert (sk["hand"], sk["end"], sk["leaf_hand"]) == (15, 16, False) and sk["skinned"] == [13, 14, 15], sk
    assert [a[0] for a in sk["arm"]] == [0, 10, 11, 12, 13, 14, 15, 16]
    leaf = pc.skin_hand(*_skin_model(leaf_hand=True))
    assert (leaf["hand"], leaf["end"], leaf["leaf_hand"]) == (15, 15, True), leaf
    import collections
    sa = {98: collections.Counter({((227,), 12): 2, ((243,), 13): 4, ((487,), 12): 7}),
          5489: collections.Counter({((227,), 15): 1, ((243,), 16): 8, ((31,), 15): 2})}
    good = pc.stock_hand_check(sa, 5489, sk["arm"], 15, 16)
    assert good["agrees"] and good["pair_majority"] == {"12": 15, "13": 16} and good["arm_bones"] == {"15": 3, "16": 8}
    assert not pc.stock_hand_check(sa, 5489, sk["arm"], 14, 15)["agrees"]          # labels_for's pair: stock disagrees
    assert not pc.stock_hand_check(sa, 5489, sk["arm"], None, None)["agrees"]      # no skin hand: never vacuously true
    doc = _doc()
    st, am = doc["e_hands"]["3 steiner"], doc["e_hands"]["7 amarant"]
    assert (st["skin"]["hand"], st["skin"]["end"], st["stock"]["pair_majority"]) == (15, 16, {"12": 15, "13": 16}), st
    assert st["bone13"]["role"] == "upper arm" and st["stock"]["agrees"]
    assert (am["skin"]["hand"], am["skin"]["end"], am["skin"]["leaf_hand"]) == (16, 16, True), am
    assert am["stock"]["arm_bones"] == {"16": 1} and am["stock"]["agrees"]
    for key, old in (("3 steiner", [14, 15]), ("7 amarant", [15, 16])):        # the pre-fix rows read as disagreements
        h = doc["e_hands"][key]
        assert old != h["expected"] and h["agree"] and [h["hand_bone"], h["hand_bone_end"]] == h["expected"]
    for key, h in doc["e_hands"].items():
        if isinstance(h, dict) and "skin" in h:
            assert "labels_for" not in h["source"].replace("never labels_for", ""), key


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
    # the census reads the install's MapConfigData through the kit's events-bundle index, which the kit WRITES into
    # StreamingAssets when it is missing: this test never writes the install (the sibling install-gated tests' rule)
    for cache in (".ff9mapkit-events-bundle.txt", ".ff9mapkit-field-index.json"):
        if not (game / "StreamingAssets" / cache).is_file():
            return None, f"the kit cache {cache} is missing from the install: this test would WRITE it there"
    # the census parses the rig table out of the SHARED clone: a clone carrying another session's unmerged rig-table edits
    # is not this tree's stack -- a drift there says nothing about this tree
    clone = _rig_rows(t.strip() for t in (MEMORIA / "Assembly-CSharp/Memoria/Netsync/NetSyncVisitor.cs").read_text(
        encoding="utf-8-sig", errors="replace").splitlines()
        if t.strip().startswith("new Rig("))
    stack = _rig_rows(net_lines_ordered("NetSyncVisitor.cs", r"new Rig\("))
    if clone != stack:
        return None, "the shared clone's NetSyncVisitor.Rigs is not this tree's stack (another session's in-flight edits)"
    return game, None


def test_the_census_regenerates_from_the_install():
    """INSTALL-GATED (READ-ONLY: skipped when the kit's caches are missing -- the read would WRITE them into the install --,
    and when the shared clone's rig table is not this tree's stack): polish_census.py --check rebuilds the census in memory
    off the 817 exports, the install's
    mapconfigs and skeletons (the kit's readers) and the clone's rig table, and diffs every oracle key (rigs, a_field250,
    b_steps, c_subs, d_lighting, e_hands, fg_ops, o6_other_sites, twin_selftest, bench, table_disagreements) against the
    frozen polish.json: the pins above tie the patch, the twins and the JSON to EACH OTHER, so an edit made to all three
    together would stay green -- this one re-reads the install. Skips cleanly without it. StreamingAssets is untouched."""
    game, why = _install_gate()
    if game is None:
        pytest.skip(why)
    sa = game / "StreamingAssets"
    before = {p.name: p.stat().st_mtime for p in sa.iterdir()}
    out = subprocess.run([sys.executable, "-X", "utf8", str(CENSUS / "polish_census.py"), "--check", "--game", str(game),
                          "--exports", str(EXPORTS), "--memoria", str(MEMORIA)], capture_output=True, text=True,
                         timeout=1500)
    assert out.returncode == 0 and "OK: polish.json regenerates exactly" in out.stdout, (out.stdout[-3000:],
                                                                                       out.stderr[-2000:])
    assert {p.name: p.stat().st_mtime for p in sa.iterdir()} == before          # READ-ONLY: nothing written there


def test_the_census_twin_takes_the_engines_guard_opt_in():
    """expected_steps' `guard` is OPT-IN: off (the default) the twin books stock's throw for a 19 on an EMPTY table -- the
    hazard detector b_steps.code19_empty_table_hazard reads (field 2930's on the moogle / Quina / Cinna) --; on, it drops
    and counts it as the shipping engine does (StepDroppedEmpty, either lever state, never a pass), and agrees with
    battlewire's replay case for case: the bench's F2d shape (the moogle's twelve, then 2930's 19 on 190: [] with 13),
    `polish off` (Zidane's four, the 19 stock's no-op), Freya's 19 on (25, 13) (DeleteChar's top shrink), a lone 19."""
    spec = importlib.util.spec_from_file_location("_polish_census_guard", CENSUS / "polish_census.py")
    pc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pc)
    rigs = [dict(zip(BW.RIG_COLUMNS, r)) for r in BW.RIGS]
    lone = [list(o) for o in BW.GUARD_2930]
    assert pc.expected_steps(rigs[4], lone, zidane=rigs[0])["faults"]                      # the hazard detector's default
    got = pc.expected_steps(rigs[4], lone, zidane=rigs[0], guard=True)
    assert (got["steps"], got["steps_dropped"], got["steps_passed"], got["faults"]) == ([], 1, 0, [])
    off = pc.expected_steps(rigs[4], lone, polish=False, zidane=rigs[0], guard=True)
    assert (off["steps_dropped"], off["faults"]) == (1, [])                                  # under `polish off` too
    assert pc.expected_steps(rigs[4], lone, dressed=False, zidane=rigs[0], guard=True)["faults"]   # never an undressed body
    for rig, polish, names, want, dropped in BW.GUARD_REPLAY_ORACLE:
        ops = [list(o) for n in names for o in getattr(BW, n)]
        theirs = pc.expected_steps(rigs[rig], ops, polish=polish, zidane=rigs[0], guard=True)
        assert (BW.steps_text(theirs["steps"]), theirs["steps_dropped"], theirs["faults"]) == (want, dropped, []), names
        assert BW.replay_ops(rigs[rig], polish, *[getattr(BW, n) for n in names]) == (want, dropped), names
    haz = _doc()["b_steps"]["code19_empty_table_hazard"]
    assert [h["field"] for h in haz] == [2930] and sorted(haz[0]["s141_faults_by_rig"]) == ["5 quina", "8 moogle", "9 cinna"]
