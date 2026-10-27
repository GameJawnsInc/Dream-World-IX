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
def derived(events):
    return G.derive(events=events)


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


#: the stock install's refusals, all R11 (the path-aware latch audit), each with the reader that consumes the latch
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
}


def test_the_refused_set_is_exactly_the_stock_latches(derived):
    """R11 refuses exactly the five stock latches above: 2702's stone latch (read-first in byte order), 353:11 (read
    first on a path the byte order hides) and 2507:4/5 (a load-once reader that a ReturnEntryFunctions restarts).
    Every other rule -- R12's ops and R13's Global / Null writes included -- refuses nothing on the stock install."""
    got = {(r["field"], r["entry"]): r["refusal"] for r in derived["refused"]}
    assert set(got) == set(STOCK_REFUSALS), got
    assert all(got[k].startswith(want) for k, want in STOCK_REFUSALS.items()), got


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
