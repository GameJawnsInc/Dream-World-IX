"""The co-op guest-traversal table (engine patch s156), INSTALL-GATED half: the committed JSON re-derives EXACTLY
from the install, and the promoted classifier is faithful to the frozen study census on every real QUAD root.

The install-free pins (``test_guest_traversal_table.py``) hold the JSON, the generated C# and the vectors to EACH
OTHER, so an edit made to all of them together stays green there; this is the only pin that re-reads the game.

Gating (D16): every committed field's ``.eb`` SHA-1 in all seven languages is compared FIRST. A missing install,
missing UnityPy, or a different install (GOG, a patched copy) warns ``THE GUEST TRAVERSAL TABLE WENT UNVERIFIED``
and skips -- the committed table is the owner's -- and FAILS instead when ``FF9MAPKIT_REQUIRE_INSTALL=1`` (the
nightly gate sets it in ``tools/nightly_gate.py`` child_env), so the gate can never go green on a skip. The test
only READS the install: the generator's loader never writes a cache into it, and the census is fed bytes, never its
own ``EventBundle`` (whose cache miss would write into StreamingAssets).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import pathlib
import warnings
from collections import defaultdict

import pytest

from ff9mapkit import guest_traversal as G
from ff9mapkit.eb import pressclosure as P

REPO = pathlib.Path(__file__).resolve().parents[2]
STUDY = REPO / "studies" / "field-coop" / "guest-traversal"


def _unverified(why: str):
    msg = (f"THE GUEST TRAVERSAL TABLE WENT UNVERIFIED in this run: {why}. This is the WORKTREE SKIP TRAP class -- a "
           "green run here says nothing about the table; run in the MAIN repo or the gate worktree.")
    if os.environ.get("FF9MAPKIT_REQUIRE_INSTALL") == "1":
        pytest.fail("install required here (FF9MAPKIT_REQUIRE_INSTALL=1): " + msg)
    warnings.warn(UserWarning(msg))
    pytest.skip(msg)


def _committed() -> dict:
    return json.loads(G.JSON_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def events():
    """The install's event scripts, read-only -- after the SHA-1 precheck proves it is the install the committed
    table was derived from."""
    if importlib.util.find_spec("UnityPy") is None:
        _unverified("UnityPy is not installed (the assets extra)")
    try:
        ev = G.InstallEvents(None)
    except Exception as ex:                               # noqa: BLE001 -- any resolution failure is a skip
        _unverified(f"the FF9 install did not resolve ({type(ex).__name__}: {ex})")
    drift = []
    for ent in _committed()["eb_sha1"]:
        for lang in G.LANGS:
            b = ev.eb(ent["field"], lang)
            have = hashlib.sha1(b).hexdigest() if b else None
            if have != ent[lang]:
                drift.append(f"{ent['field']}/{lang}")
    if drift:
        _unverified(f"a different install -- {len(drift)} .eb files differ from the committed table's "
                    f"({', '.join(drift[:6])}{' ...' if len(drift) > 6 else ''}); the committed table is the owner's")
    return ev


@pytest.fixture(scope="module")
def index(events):
    """The install's ALREADY-built field index (R15's walkmesh loader reads through it and never builds it)."""
    idx = G._existing_field_index(events.game)
    if idx is None:
        _unverified("the install's field index is not built, so R15 cannot read a walkmesh (the generator never "
                    "builds it: that writes into the install)")
    return idx


@pytest.fixture(scope="module")
def derived(events, index):
    return G.derive(events=events)


def _field(events, index, fid, lang="us"):
    """One field re-derived through the real read-only walkmesh loader: (FieldModel, Ground, arrival, walk-ins)."""
    fld = P.FieldModel.from_bytes(events.eb(fid, lang), fid)
    gr = G.field_ground(fld, G._r15_walkmesh(events, index, fid))
    return fld, gr, G.field_arrival(fld, gr), G.walk_ins(fld, gr)


@pytest.fixture(scope="module")
def census():
    """The frozen study census, loaded from its file (it asserts its ff9mapkit import is this repo's)."""
    spec = importlib.util.spec_from_file_location("_census_guest_traversal_install", STUDY / "interaction_census.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_derive_from_the_install_is_the_committed_table(derived):
    want = G.JSON_PATH.read_text(encoding="utf-8")
    if G.render_json(derived) != want:
        pytest.fail("the install no longer derives the committed table:\n  "
                    + "\n  ".join(G.diff_tables(json.loads(want), derived)))
    assert not [r for r in derived["refused"] if r["refusal"].startswith("R9")], "a language diverged"


#: the stock install's refusals, MEASURED: R11 (the path-aware latch audit) with the reader that consumes the latch,
#: and R15's walk-ins with the BUMP (an object's tag 2) on the ground the climb newly opens
STOCK_REFUSALS = {
    # 2702's stone latch Map.Byte[32] is read FIRST by the other stone functions, two of them window-bearing
    (2702, 15): "R11 latch: Map.Byte[32] is read before it is written by 21:",
    (2702, 19): "R11 latch: Map.Byte[32] is read before it is written by 21:",
    # 353's 16:1 reads the ladder's Map.Int16[2] at a join one of whose paths (a choice switch's default arm) no
    # write covers -- the byte order says write-first (K1)
    (353, 11): "R11 latch: Map.Int16[2] is read before it is written by 16:1",
    # 2507's 13:1 reads Map.Int16[2] at init, but 0:11's ReturnEntryFunctions(13) restarts its tag 1 (K2)
    (2507, 4): "R11 latch: Map.Int16[2] is read before it is written by 13:1",
    (2507, 5): "R11 latch: Map.Int16[2] is read before it is written by 13:1",
    # 1209's monster 2 chases the player (2:1 walks toward it) and its bump starts a battle with no key, in every
    # language. It is a WALKER (V1: only its own pathing-on Walk and constant CreateObjects), so its footprint is
    # bounded -- but its region reaches component 1: tris 163-172 (flags 0xA001, player-blocked bit 0x80 only) are
    # open to an NPC (WalkMesh.BGI_findAccessibleTriangle, WalkMesh.cs:1155-1169) and bridge the two components, and
    # Main_Init's EnablePath(1, 0) takes them off only after two yields (0:0 +247 Wait(1) loop, +306 Wait(2)), so
    # walker_blocks cannot prove no walker ever steps on them first
    (1209, 5): "R15 walk-in: landing component 1 (not an arrival) carries bump 2:2 (battle)",
}

#: THE JP WAIVER, pinned: the rows that ship ONLY because R15's Japanese refusal is waived (guest_traversal.WAIVER_WHY)
#: -- the stock chest template on new ground, exempt in six languages, polls KEYON(Cancel | Special) in Japanese
#: (ETb.ProcessJapaneseLayout hands a Japanese script the physical Confirm as Cancel), which F1 does not strip.
#: 407's chests 12 and 22 (12 moved by its own 12:18), 408's 15, 912's / 1912's 16 and 17, 1950's 9, 2602's / 2605's 11
WAIVED_ROWS = {(407, 16), (407, 17), (407, 18), (408, 6), (408, 9), (912, 14), (1912, 15), (1950, 4), (1950, 5),
               (2602, 5), (2605, 4), (2605, 5), (2605, 6), (2605, 7)}

#: F1: the four rows whose climb can end at a point R15 cannot name -- they land on every walkable component, and none
#: of their fields holds an exposed walk-in off its arrival ground, so they ship
UNNAMED_LANDINGS = {(2353, 3), (2353, 4), (2456, 14), (2955, 23)}

#: the rows the in-game bench climbs (studies/test-harness/scenarios/coop_guest_traversal.py): they MUST ship
BENCH_ROWS = {(114, 9), (408, 4), (408, 5), (207, 10), (207, 11)}


def test_the_refused_set_is_exactly_the_measured_one(derived):
    """R11 refuses exactly the five stock latches above: 2702's stone latch (read-first in byte order), 353:11 (read
    first on a path the byte order hides) and 2507:4/5 (a load-once reader that a ReturnEntryFunctions restarts); R15
    refuses exactly 1209:5, whose new ground the battle monster's walker region reaches (the fourteen Japanese chest
    refusals are WAIVED, below). R12's ops, R13's Global / Null writes, R14's key polls, a tread region, an incomplete
    walk-in closure, an unnamed landing on its own, and R16 (not enforced) refuse nothing on the stock install."""
    got = {(r["field"], r["entry"]): r["refusal"] for r in derived["refused"]}
    assert set(got) == set(STOCK_REFUSALS), got
    assert all(got[k].startswith(want) for k, want in STOCK_REFUSALS.items()), got
    assert not [r for r in derived["refused"] if r["refusal"].startswith(("R12", "R13", "R14", "R16"))]
    assert not [r for r in derived["refused"] if "carries walk-in" in r["refusal"] or "may carry walk-in" in r["refusal"]]
    assert UNNAMED_LANDINGS <= {(r["field"], r["entry"]) for r in derived["rows"]}


def test_the_jp_waiver_ships_exactly_the_measured_rows(derived):
    """THE JP WAIVER, pinned to the measured set: exactly these fourteen rows ship although Japanese R15 refuses them,
    each recorded in the JSON's top-level "waivers" (never in the rows: table_crc and render_cs do not see it) with the
    waived walk-ins. They are not a new class -- a Japanese guest's physical Confirm already opens such a chest on its
    arrival ground at control-on, through the same hole. THE ENGINE FOLLOW-UP that retires the waiver: strip the
    JP-mapped bits (Cancel, where ETb.ProcessJapaneseLayout puts a Japanese guest's Confirm) in
    NetSyncField.ControlOnScriptKeys (NetSyncField.cs:955), then drop the waiver and this pin."""
    got = {(w["field"], w["entry"]): w["waiver"] for w in derived["waivers"]}
    assert set(got) == WAIVED_ROWS, sorted(set(got) ^ WAIVED_ROWS)
    assert all(t.startswith("R15 walk-in waived: jp F1 hole -- bump ") and t.endswith(G.WAIVER_WHY) for t in got.values())
    assert WAIVED_ROWS <= {(r["field"], r["entry"]) for r in derived["rows"]}
    assert not [r for r in derived["rows"] if "waived" in r]
    assert [w for w in derived["waivers"] if w["field"] == 408] == [
        {"field": 408, "entry": e, "waiver": f"R15 walk-in waived: jp F1 hole -- bump 15:2 {G.WAIVER_WHY}"} for e in (6, 9)]


def test_the_bench_rows_ship(derived):
    shipped = {(r["field"], r["entry"]) for r in derived["rows"]}
    assert BENCH_ROWS <= shipped, sorted(BENCH_ROWS - shipped)


def test_r14_agrees_with_the_census_host_owned_column(events):
    """R14 on real bytes: every census candidate polls directions only (no key_press, no key_other), and the study
    TSV's host_owned_key_poll column agrees row for row with pressclosure's key_press bucket -- its True rows (1202's
    Confirm|Special jumps) are LOCO+LATCH, never candidates."""
    tsv = (STUDY / "guest_local_candidates.tsv").read_text(encoding="utf-8").splitlines()
    head = tsv[0].split("\t")
    disagree, polled = [], set()
    for c in (dict(zip(head, ln.split("\t"))) for ln in tsv[1:]):
        fid, ei = int(c["field_id"]), int(c["entry"])
        v = P.analyze_root(P.FieldModel.from_bytes(events.eb(fid, "us"), fid), ei, 3)
        buckets = {b for (_k, _m, b, _n, _o) in v.closure.key_sites}
        if ("key_press" in buckets) != (c["host_owned_key_poll"] == "True"):
            disagree.append((fid, ei))
        if v.candidate and buckets - {"key_dir"}:
            polled.add((fid, ei))
        if c["host_owned_key_poll"] == "True":
            assert not v.candidate, (fid, ei)
    assert disagree == [] and polled == set(), (disagree, polled)


#: the review's walk-in exposures: row -> (the STATEFUL walk-in its landing component carries, its effects)
REVIEW_WALKINS = {(2505, 7): (6, "battle, window, GLOB write, item"), (2955, 21): (24, "exit, window, GLOB write, item"),
                  (2853, 5): (4, "exit, GLOB write"), (2918, 4): (2, "exit, GLOB write")}


@pytest.mark.parametrize("row", sorted(REVIEW_WALKINS))
def test_r15_the_reviews_walk_ins_land_on_arrival_ground(events, index, row):
    """MEASURED: each walk-in the review named sits on a component where the field's own tag 0 leaves the player on
    some entrance branch (2505's default entrance, 2955's only spawn, a 2853 / 2918 branch), so the climb opens nothing
    new and the row ships. ARRIVAL is the UNION over entrance branches: on one visit the player spawns on ONE of them,
    so these per-visit exposures remain BY DESIGN (no per-visit rule -- 207:10, a bench row, is one). The clause is LIVE
    on the same bytes: with the arrivals taken away (and the hidden-item exemption, which 2955's Confirm-gated 24:2
    holds) the very walk-in refuses."""
    fid, ei = row
    want_e, effects = REVIEW_WALKINS[row]
    fld, gr, arrival, walks = _field(events, index, fid)
    v = P.analyze_root(fld, ei, 3)
    (under,) = [c for (k, e, c, _w, tv, _x, _g) in walks if k == "walk-in" and e == want_e and tv.tier == "STATEFUL"]
    w = G.walkin(fld, v, gr, arrival, walks)
    assert w["why"] is None and under & w["land"] and under & w["land"] <= arrival
    cold = G.walkin(fld, v, gr, set(), [x[:5] + (False,) + x[6:] for x in walks if x[0] == "walk-in"])
    assert cold["why"] == (f"R15 walk-in: landing component {min(under & cold['new'])} (not an arrival) "
                           f"carries walk-in {want_e}:2 ({effects})"), cold["why"]


@pytest.mark.parametrize("row", sorted(UNNAMED_LANDINGS))
def test_r15_an_unnamed_landing_lands_everywhere_and_still_ships(events, index, row):
    """F1 on real bytes: each row's final landing cannot be named (2353's mid-air if/elif fall-through, 2456's top 2691 u
    above tri 57, 2955's computed 40-step arc), so it lands on EVERY walkable component -- and its field holds no
    exposed walk-in (STATEFUL, not exempt) that a landing anywhere could newly reach."""
    fid, ei = row
    fld, gr, arrival, walks = _field(events, index, fid)
    w = G.walkin(fld, P.analyze_root(fld, ei, 3), gr, arrival, walks)
    assert w["wild"] and w["land"] == set(gr.walkable) and w["why"] is None
    exposed = [x for x in walks if G.exposed(x)]
    assert all(c is not None and not (c & w["new"]) for (_k, _e, c, _w, _tv, _x, _g) in exposed)


#: F3's chest bumps: (field, chest entry) -> the rows whose new ground holds it; the chest is exempt in every language
#: but Japanese (KEYON(0x90000) -- Cancel is not in F1's control-on mask)
CHEST_BUMPS = {(408, 15): {6, 9}, (912, 16): {14}, (1912, 16): {15}, (1950, 9): {4, 5}, (2602, 11): {5},
               (2605, 11): {4, 5, 6, 7}}


@pytest.mark.parametrize("chest", sorted(CHEST_BUMPS))
def test_r15_the_chest_bumps_ship_on_f1s_control_on_mask_alone(events, index, chest):
    """THE CHEST DEPENDENCY, pinned: on new ground, each stock chest bump is safe in the western languages ONLY because
    every effect of its tag 2 sits under a user-control test AND a constant KEYON(Confirm | Special) -- which
    NetSyncField.ControlOnScriptKeys strips from a following guest's control-on poll. Drop the exemption and the same
    US row refuses on this very bump; the Japanese chest polls Cancel | Special and is never exempt."""
    fid, ce = chest
    for lang in ("us", "jp"):
        fld, gr, arrival, walks = _field(events, index, fid, lang)
        (bump,) = [x for x in walks if x[0] == "bump" and x[1] == ce]
        assert bump[4].tier == "STATEFUL" and bump[5] is (lang == "us") and bump[6] is None
        (jp_hyp,) = [x for x in G.walk_ins(fld, gr, P.JP_F1_STRIPPED) if x[0] == "bump" and x[1] == ce]
        assert jp_hyp[5] is True                                    # the JP waiver's hypothesis exempts it everywhere
        polls = {m for (_s, m) in P.watch_scan(fld, ce, 2).polls}
        assert polls == ({0xA0000} if lang == "us" else {0x90000})
        for ei in sorted(CHEST_BUMPS[chest]):
            v = P.analyze_root(fld, ei, 3)
            w = G.walkin(fld, v, gr, arrival, walks)
            if lang == "us":
                assert w["why"] is None
                forced = [x[:5] + (False,) + x[6:] if x is bump else x for x in walks]
                assert f"bump {ce}:2" in G.walkin(fld, v, gr, arrival, forced)["why"]
            else:
                assert w["why"].startswith("R15 walk-in: landing component") and f"bump {ce}:2" in w["why"]


def test_r15_a_stateful_walk_in_with_no_effect_op_is_not_exempt(events):
    """V2 on real bytes: 1650's treads 7-11 and 2510's tread 14 tier STATEFUL (an SPS op with the player's motion) with
    no op R16 calls an effect -- the round-2 exemption called them exempt for want of anything to cover. The exemption
    now sees each STATEFUL bucket's site, and none of theirs sits under both halves."""
    for fid, entries in ((1650, range(7, 12)), (2510, (14,))):
        fld = P.FieldModel.from_bytes(events.eb(fid, "us"), fid)
        for ei in entries:
            tv = P.analyze_root(fld, ei, 2)
            ws = P.watch_scan(fld, ei, 2, spawn=True)
            assert tv.tier == "STATEFUL" and ws.effects == [] and "sps" in tv.reasons, (fid, ei)
            assert G.walk_judgement(fld, ei, tv) == (False, None)
            assert ws.exempt_why(tv).startswith("sps at ") and ws.exempt_why(tv).endswith(
                "is not under both a user-control test and a stripped poll"), (fid, ei)


def test_f4_the_engine_frames_bite_where_they_should_and_change_no_row(events, index):
    """F4 on real bytes, each pinned where it bites: (b) 2505's entrance 122 ends its tag 0 on a ladder
    (AddCharacterAttribute(4), SetPathing(0)) and is no arrival -- the entrance switch's arm is followed into the later
    `== 122` test; (c) Main_Init disables tris in many shipped fields; (d) 1553's region 6 is a QuadCircleData key and
    touches every component -- its tag 2 is TRIVIAL, so nothing is exposed. The derivation pin above holds the rows."""
    fld, gr, arrival, walks = _field(events, index, 2505)
    pts = {(x, y, z) for (_e, _o, _op, x, y, z) in G.spawn_points(fld)}
    assert (2432, 384, 1783) not in pts and (-831, 0, 651) in pts
    disabling = [fid for fid in sorted({r["field"] for r in _committed()["rows"]})
                 if G.main_init_disables(P.FieldModel.from_bytes(events.eb(fid, "us"), fid),
                                         G._r15_walkmesh(events, index, fid))]
    assert len(disabling) >= 10, disabling
    fld, gr, arrival, walks = _field(events, index, 1553)
    (q,) = [x for x in walks if x[0] == "walk-in" and x[1] == 6]
    assert q[2] is None and "QuadCircleData" in q[3] and q[4].tier == "TRIVIAL"


#: R16 MEASURED (not enforced): every watch root that trips, with the languages it trips in. By hand: the stock
#: SCENARIO GUARD in a Main_Loop (scenario past N: a window, a wait for Select or Start, the scenario reset -- (a), no
#: user-control test): 207, 301, 307, 565, 914, 2505 9:1, 2605, 2853 0:1, 2918 0:1, 353 16:1; the hidden-item template
#: with no control test ((a)): 1952 10:1, 2853 10:1, 353 13:1, 2507 13:1; the Japanese hidden-item template ((b):
#: KEYON(Cancel | Special) is not in F1's mask): 114 4-7, 207 5, 557 3, 565 4, 1312 4, 1863 5-7, 2212 1, 2918 1; a
#: story NPC whose position read picks its walk ((b), 114 3:1); position-fired Main_Loop / exit sequences ((b): 353
#: 9:1, 1209 1:1, 1460 0:1, 2918 8:1, 3059 0:1); a sender call no root can name (2212 0:1); V3's Japanese pair (407 5:1,
#: 2955 0:1): a talk's user-control test reaches its key-dependent writes only across a yielding wait loop, and the
#: Japanese poll (Cancel) proves no F1-stripped press to pair it with, so the writes taint (a)
_ALL = frozenset(G.LANGS)
R16_TRIPS = {
    (114, 3, 1): _ALL, (114, 4, 1): {"jp"}, (114, 5, 1): {"jp"}, (114, 6, 1): {"jp"}, (114, 7, 1): {"jp"},
    (207, 0, 1): _ALL, (207, 5, 1): {"jp"}, (301, 0, 1): _ALL, (307, 0, 1): _ALL, (407, 5, 1): {"jp"},
    (353, 9, 1): _ALL, (353, 13, 1): _ALL, (353, 16, 1): _ALL, (557, 3, 1): {"jp"}, (565, 0, 1): _ALL,
    (565, 4, 1): {"jp"}, (914, 0, 1): _ALL, (1209, 1, 1): _ALL, (1312, 4, 1): {"jp"}, (1460, 0, 1): _ALL,
    (1863, 5, 1): {"jp"}, (1863, 6, 1): {"jp"}, (1863, 7, 1): {"jp"}, (1952, 10, 1): _ALL, (2212, 0, 1): _ALL,
    (2212, 1, 1): {"jp"}, (2505, 9, 1): _ALL, (2507, 13, 1): _ALL, (2605, 0, 1): _ALL, (2853, 0, 1): _ALL,
    (2853, 10, 1): _ALL, (2918, 0, 1): _ALL, (2918, 1, 1): {"jp"}, (2918, 8, 1): _ALL, (2955, 0, 1): {"jp"},
    (3059, 0, 1): _ALL,
}
#: ... and the rows it would refuse, enforced: the bench's 114:9, 207:10 and 207:11 among them -- why it is not
#: (the waived 407:16-18 and 2605:4-7 reach R16 now, and refuse there: a waiver never reaches past it)
R16_ROWS = {(114, 9), (207, 10), (207, 11), (301, 7), (301, 8), (307, 5), (307, 6), (307, 7), (307, 8), (407, 16),
            (407, 17), (407, 18), (407, 19), (557, 11), (557, 12), (565, 11), (565, 12), (914, 10), (1312, 11),
            (1312, 12), (1460, 8), (1460, 9), (1863, 9), (1952, 8), (2212, 3), (2212, 4), (2505, 3), (2505, 4),
            (2505, 7), (2605, 4), (2605, 5), (2605, 6), (2605, 7), (2605, 9), (2853, 5), (2853, 9), (2918, 3),
            (2918, 4), (2955, 17), (2955, 21), (2955, 23), (3059, 9), (3059, 10)}


def test_r16_trips_exactly_the_measured_watchers(events):
    """R16 MEASURED on every field the table touches, in all seven languages: the expected 1952 10:1 and 2853 10:1 (the
    ladder-top hidden items with no user-control test) and the rest, each inspected by hand (the groups above)."""
    got = defaultdict(set)
    for fid in sorted({r["field"] for r in _committed()["rows"] + _committed()["refused"]}):
        for lang in G.LANGS:
            for ((e, t), _why) in G.watchers(P.FieldModel.from_bytes(events.eb(fid, lang), fid)):
                got[(fid, e, t)].add(lang)
    assert {k: frozenset(v) for k, v in got.items()} == {k: frozenset(v) for k, v in R16_TRIPS.items()}


def test_r16_enforced_would_refuse_the_bench(events, index):
    """Why R16_ENFORCED is False: enforced, R16 refuses exactly R16_ROWS -- 1952:8 and 2853:9 (the F2 finding) and the
    bench's 114:9 (114's 3:1) and 207:10 / 207:11 (207's Main_Loop scenario guard), which must ship."""
    refused = []
    for fid in sorted({r["field"] for r in _committed()["rows"]}):
        by_lang = {lang: events.eb(fid, lang) for lang in G.LANGS}
        _, _r, x, _ = G.derive_field(fid, by_lang, walkmesh=lambda fid=fid: G._r15_walkmesh(events, index, fid), r16=True)
        refused += x
    r16 = {(x["field"], x["entry"]) for x in refused if x["refusal"].startswith("R16 watcher: ")}
    assert r16 == R16_ROWS and BENCH_ROWS & r16 == {(114, 9), (207, 10), (207, 11)}
    assert G.R16_ENFORCED is False


def test_r15_reads_the_walkmesh_without_touching_the_install(events, index):
    """R15's loader reads through the parsed index only: a derive_field with the real provider leaves every
    StreamingAssets dot-file (the field index, the events-bundle cache) as it was."""
    sa = events.game / "StreamingAssets"

    def dot_files():
        return sorted((p.name, p.stat().st_size, p.stat().st_mtime_ns) for p in sa.iterdir() if p.name.startswith("."))
    before = dot_files()
    by_lang = {lang: events.eb(114, lang) for lang in G.LANGS}
    _, rows, refused, _ = G.derive_field(114, by_lang, walkmesh=lambda: G._r15_walkmesh(events, index, 114))
    assert [(r["field"], r["entry"]) for r in rows] == [(114, 9)] and refused == [] and "r15" not in rows[0]
    assert dot_files() == before


def _reader(events, fid, region, label):
    fld = P.FieldModel.from_bytes(events.eb(fid, "us"), fid)
    v = next(x for x in P.analyze_regions(fld) if x.region == region)
    (r,) = [x for x in P.latch_consumers(fld, v) if x.label == label]
    return fld, r


def test_353_is_refused_by_a_path_the_byte_order_hides(events):
    """K1 on real bytes: 353 16:1's FIRST access in byte order is a plain write (the old rule's 'write-first'), but
    a later read is reached on a path no write covers -- the path-aware audit's uncovered read."""
    fld, r = _reader(events, 353, 11, "16:1")
    assert r.consumer and r.var == (1, 6, 2)
    reads, first = P.latch_access(fld, 16, 1, 1, P.var_bits(6, 2))
    ins = next(i for i in fld.instrs(16, 1) if i.off == first)
    rd, cov = P._access(fld, 16, 1, ins, 1, P.var_bits(6, 2))
    assert (rd, cov) == (frozenset(), P.var_bits(6, 2)) and first < reads[0] == r.off


def test_2507_is_refused_by_the_return_alone(events, monkeypatch):
    """K2 on real bytes: 2507 13:1 is the load-once shape exactly (exempt when ReturnEntryFunctions is not an op the
    rule knows), and 0:11's ReturnEntryFunctions(13) is what makes it a consumer."""
    _, r = _reader(events, 2507, 4, "13:1")
    assert r.consumer
    monkeypatch.setattr(P, "RETURN_ENTRY_OP", -1)
    _, r = _reader(events, 2507, 4, "13:1")
    assert not r.consumer and "load-once" in r.exempt_why


def test_pressclosure_is_the_census_on_every_quad_root(events, census):
    """FAITHFULNESS: on every real field, the promoted classifier finds the census's QUAD roots and gives each the
    census's tier, kind and gate; its LOCO-ONLY movers are the census's, which are the study TSV's LOCO-ONLY rows and
    exactly the committed table's rows + refusals (re-derived == committed is pinned above, so the committed JSON
    stands in for the derivation here and the module derives once). Counts are the JSON's, never literals."""
    from ff9mapkit._fieldtable import FIELD_BY_ID
    bad, quads, cands = [], 0, set()
    for fid in sorted(FIELD_BY_ID):
        data = events.eb(fid, "us")
        if not data:
            continue
        eb = census.EbScript.from_bytes(data)
        cf = census.Field(fid, eb)
        pf = P.FieldModel(eb, fid)
        croots = [ei for (rk, ei, _t, _s) in census.roots_of(cf) if rk == "QUAD"]
        if croots != P.quad_roots(pf):
            bad.append((fid, "roots", croots, P.quad_roots(pf)))
            continue
        for ei in croots:
            quads += 1
            c = census.Closure(cf, ei)
            c.walk(ei, 3, None)
            c.finish()
            want = (census.classify(c)[0], census.loco_kind(c), sorted(census.root_gate(cf, ei, 3, None)))
            v = P.analyze_root(pf, ei, 3)
            if (v.tier, v.kind, list(v.gate)) != want:
                bad.append((fid, ei, want, (v.tier, v.kind, list(v.gate))))
            if want[0] == "LOCO-ONLY" and want[1] in P.MOVERS:
                cands.add((fid, ei))
            if v.funcs != tuple(dict.fromkeys((n[0], n[1]) for n in c.nodes)):
                bad.append((fid, ei, "closure", v.funcs))
    assert not bad, bad[:10]
    committed = _committed()
    counts = committed["counts"]
    assert quads == counts["quad_roots"]
    assert len(cands) == counts["census_candidates"]
    table = {(r["field"], r["entry"]) for r in committed["rows"] + committed["refused"]}
    assert cands == table
    tsv = (STUDY / "guest_local_candidates.tsv").read_text(encoding="utf-8").splitlines()
    head = tsv[0].split("\t")
    study = {(int(c["field_id"]), int(c["entry"])) for c in (dict(zip(head, ln.split("\t"))) for ln in tsv[1:])
             if c["tier"] == "LOCO-ONLY"}
    assert cands == study, (sorted(cands - study), sorted(study - cands))


def test_the_far_tread_report_never_builds_the_index(events):
    """The informational report reads the field index only when it ALREADY exists and parses, and never writes the
    install: every dot-file (the field index, the events-bundle cache) keeps its name, size and mtime. (The
    install-free twins in test_guest_traversal_pressclosure.py are the ones that can go red on this machine.)"""
    sa = events.game / "StreamingAssets"

    def dot_files():
        return sorted((p.name, p.stat().st_size, p.stat().st_mtime_ns) for p in sa.iterdir() if p.name.startswith("."))
    before = dot_files()
    text = G.far_tread_report(obj=_committed(), events=events)
    assert text.isascii() and text.startswith("# far-component tread report")
    assert dot_files() == before


def test_the_gate_turns_an_unverified_table_into_a_failure(monkeypatch):
    """The call-site law behind 'skips loudly here, fails in the gate': the nightly gate's child environment sets
    FF9MAPKIT_REQUIRE_INSTALL=1, and under it the unverified path FAILS; without it, it warns and skips."""
    spec = importlib.util.spec_from_file_location("_nightly_gate_under_test", REPO / "tools" / "nightly_gate.py")
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    monkeypatch.delenv("FF9MAPKIT_REQUIRE_INSTALL", raising=False)
    assert gate.child_env()["FF9MAPKIT_REQUIRE_INSTALL"] == "1"
    with pytest.warns(UserWarning, match="THE GUEST TRAVERSAL TABLE WENT UNVERIFIED"):
        with pytest.raises(pytest.skip.Exception):
            _unverified("probe")
    monkeypatch.setenv("FF9MAPKIT_REQUIRE_INSTALL", "1")
    with pytest.raises(pytest.fail.Exception, match="install required here"):
        _unverified("probe")
