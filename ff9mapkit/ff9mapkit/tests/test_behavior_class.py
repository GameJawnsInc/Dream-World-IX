"""PER-CLASS BRAIN SHARING — the brains backend's cross-product kill.

N same-tree units share ONE Seq brain entry (P3's multi-spawn shape); their
protocol state strides into uid-indexed gScriptVector cells, and the shared
brain indexes its caller's cells through THE IDENTITY CHANNEL —
``obj(uid=255).f[5]`` (B_OBJSPECA resolves uid 255 through GetObjUID → gCur,
the calling unit, and getvobj field 5 IS ``obj.uid``; 0xD3 args resolve
through the same EvaluateValueExpression the proven scan-loop indices ride).
Member-side bodies read the same cells at their constant uid.
"""
import pytest

from ff9mapkit.content import behavior as B

IDENTITY = bytes((0x78, 0xFF, 0x05))               # obj(uid=255).f[5] — B_OBJSPECA
REQ_255 = bytes((0x10, 0x00, 0x04, 0xFF))          # REQ, argflag 0, level 4, uid 255


def _class_field(**kw):
    fb = B.FieldBehavior(
        [B.UnitSpec("kn0", 2, spawn=(0, 0), hp=3),
         B.UnitSpec("kn1", 3, spawn=(100, 0), hp=3, walk_speed=44),
         B.UnitSpec("mu0", 4, spawn=(500, 0), hp=2),
         B.UnitSpec("mu1", 5, spawn=(600, 0), hp=2),
         B.UnitSpec("crier", 6, spawn=(300, 300))],
        brains=True, counters=("fallen",),
        classes=[B.ClassSpec("guard", ("kn0", "kn1")),
                 B.ClassSpec("beast", ("mu0", "mu1"))], **kw)
    fb.group("mus", ["mu0", "mu1"])
    fb.group("kns", ["kn0", "kn1"])
    fb.classes["guard"].tree = B.Selector(
        B.Sequence(fb.hp_le("guard", 0), B.Do(B.Die(count="fallen", linger=20))),
        B.Once("greet", B.Sequence(fb.near("guard", B.PLAYER, 300),
                                   B.Do(B.Chase(B.PLAYER, speed=60)))),
        fb.engage_node("guard", B.Engage(group="mus", radius=900, contact=160)),
        B.Cooldown(90, B.Sequence(fb.near("guard", "crier", 350),
                                  B.Do(B.WalkTo((300, 300))))),
        B.Do(B.HoldPost()),
    )
    fb.classes["beast"].tree = B.Selector(
        B.Sequence(fb.hp_le("beast", 0), B.Do(B.Die(count="fallen"))),
        fb.engage_node("beast", B.Engage(group="kns", radius=900, contact=160,
                                         nearest=True)),
        B.Do(B.Wander(center=(550, 0), radius=250)),
    )
    fb.units["crier"].tree = B.Selector(
        B.Once("first", B.Sequence(fb.counter_ge("fallen", 1), B.Do(B.Announce(902)))),
        B.Do(B.Hold((300, 300))),
    )
    return fb


def test_one_brain_per_class_with_identity_reads():
    fb = _class_field()
    cb = fb.compile()
    assert set(cb.brain_bodies) == {"guard", "beast", "crier"}
    for cn in ("guard", "beast"):
        assert IDENTITY in cb.brain_bodies[cn]      # the strided self reads
        assert REQ_255 in cb.brain_bodies[cn]       # caller-context dispatch
    # the unclassed brain neither strides nor pays for identity
    assert IDENTITY not in cb.brain_bodies["crier"]
    # 5 units, 3 brains: the class members share
    assert len(cb.duty_bodies) == 5


def test_members_share_tag_numbering_and_get_own_bodies():
    cb = _class_field().compile()
    tags = {m: [t for t, _ in cb.action_funcs[m]]
            for m in ("kn0", "kn1", "mu0", "mu1")}
    assert tags["kn0"] == tags["kn1"]               # the shared brain REQs by tag
    assert tags["mu0"] == tags["mu1"]
    # bodies are per-member (constant-uid cell refs) — same size, distinct bytes
    kn0 = dict(cb.action_funcs["kn0"])
    kn1 = dict(cb.action_funcs["kn1"])
    assert set(kn0) == set(kn1)
    assert any(kn0[t] != kn1[t] for t in kn0)       # uid constants differ


def test_members_take_no_glob_protocol_slots():
    fb = _class_field()
    fb.compile()
    rep = fb.bb.report()
    for m in ("kn0", "kn1", "mu0", "mu1"):
        for slot in (".selected", ".running", ".spd", ".mx", ".tx", ".active"):
            assert f"{m}{slot}" not in rep
    # the unclassed unit keeps the v1 slots
    assert "crier.selected" in rep


def test_strided_tables_are_seeded_with_presets():
    fb = _class_field()
    cb = fb.compile()
    # core families + per-class lazies allocated
    for tname in ("cls.act", "cls.sel", "cls.run", "cls.tx", "cls.tz",
                  "cls.guard.ctgt", "cls.beast.ctgt", "cls.guard.ord"):
        assert tname in fb._cls_tids, tname
    # ctgt presets to 255 at every member cell (0 is a VALID roster index)
    assert fb._cls_values["cls.guard.ctgt"] == {2: 255, 3: 255}
    # spd0/spd presets carry each member's own walk_speed
    assert fb._cls_values["cls.spd"] == {2: 50, 3: 44, 4: 50, 5: 50}
    # HoldPost fallback: tx/tz preset per member = its own spawn (kn0's zero
    # rides the zero-fill — _cls_preset stores only non-zero seed values)
    assert fb._cls_values["cls.tx"].get(2, 0) == 0
    assert fb._cls_values["cls.tx"][3] == 100
    # the ord table maps uid -> roster index (kn1 is kns[1]; kn0's 0 rides zero-fill)
    assert fb._cls_values["cls.guard.ord"] == {3: 1}
    # every registered table gets the size-wipe/grow seed in main_init
    assert cb.main_init.count(b"\x05") > 0


def test_no_class_build_allocates_no_cls_tables():
    fb = B.FieldBehavior([B.UnitSpec("a", 2, spawn=(0, 0))], brains=True)
    fb.units["a"].tree = B.Do(B.Hold((0, 0)))
    cb = fb.compile()
    assert not fb._cls_tids
    assert "cls." not in cb.report
    assert IDENTITY not in cb.brain_bodies["a"]


def test_determinism():
    assert _class_field().compile().stable_hash() == \
        _class_field().compile().stable_hash()


# ------------------------------------------------------------------ refusals
def test_classes_need_brains():
    with pytest.raises(B.BehaviorError, match="brains"):
        B.FieldBehavior([B.UnitSpec("a", 2, spawn=(0, 0))],
                        classes=[B.ClassSpec("c", ("a",))])


def test_class_member_validation():
    for members, msg in ((("nope",), "unknown member"),
                         (("a", "a"), "duplicate"),
                         ((), "at least one")):
        with pytest.raises(B.BehaviorError, match=msg):
            B.FieldBehavior([B.UnitSpec("a", 2, spawn=(0, 0))], brains=True,
                            classes=[B.ClassSpec("c", members)])
    with pytest.raises(B.BehaviorError, match="already in"):
        B.FieldBehavior([B.UnitSpec("a", 2, spawn=(0, 0))], brains=True,
                        classes=[B.ClassSpec("c", ("a",)), B.ClassSpec("d", ("a",))])


def test_class_tree_refuses_one_shot_actions():
    fb = B.FieldBehavior([B.UnitSpec("a", 2, spawn=(0, 0)),
                          B.UnitSpec("b", 3, spawn=(9, 0))], brains=True,
                         classes=[B.ClassSpec("pair", ("a", "b"))])
    fb.classes["pair"].tree = B.Selector(
        B.Sequence(fb.near("pair", B.PLAYER, 300), B.Do(B.Announce(900))),
        B.Do(B.Hold((0, 0))),
    )
    with pytest.raises(B.BehaviorError, match="not a v1 class action"):
        fb.compile()


def test_class_name_refused_as_target():
    fb = _class_field()
    with pytest.raises(B.BehaviorError, match="TARGET"):
        fb.near("crier", "guard", 300)
    with pytest.raises(B.BehaviorError, match="TARGET"):
        fb.units["crier"].tree = None
        fb._feed_effect("crier", B.Chase("guard"))
    with pytest.raises(B.BehaviorError):
        fb.active("guard")


def test_class_self_hp_needs_one_home():
    fb = B.FieldBehavior([B.UnitSpec("a", 2, spawn=(0, 0), hp=3),
                          B.UnitSpec("b", 3, spawn=(9, 0), hp=3)], brains=True,
                         classes=[B.ClassSpec("pair", ("a", "b"))])
    fb.group("g1", ["a"])                            # a grouped, b not: MIXED homes
    with pytest.raises(B.BehaviorError, match="ONE home"):
        fb.hp_le("pair", 0)


def test_class_hp_ungrouped_uses_cls_cells():
    fb = B.FieldBehavior([B.UnitSpec("a", 2, spawn=(0, 0), hp=3),
                          B.UnitSpec("b", 3, spawn=(9, 0), hp=5)], brains=True,
                         classes=[B.ClassSpec("pair", ("a", "b"))])
    ref = fb._hp_ref("pair")
    assert "obj(uid=255).f[5]" in ref
    assert fb._cls_values["cls.pair.hp"] == {2: 3, 3: 5}
    # a member's concrete ref indexes the same table at its own uid
    mref = fb._hp_ref("a")
    assert "const(2) B_VECTOR" in mref and "obj(" not in mref


# ------------------------------------------------------------------ TOML surface
def test_toml_class_row_builds_and_lints():
    from ff9mapkit.content import behaviortoml as BT
    raw = {
        "npc": [{"name": n, "pos": [i * 100, 0]}
                for i, n in enumerate(["g0", "g1", "prey"])],
        "behavior": {
            "brains": True,
            "group": [{"name": "prey_g", "units": ["prey"]}],
            "unit": [
                {"npcs": ["g0", "g1"], "class": "pack", "hp": 3, "branch": [
                    {"when": [{"hp_le": 0}], "do": {"die": True}},
                    {"do": {"engage": "prey_g"}},
                    {"do": {"hold_post": True}},
                ]},
                {"npc": "prey", "hp": 5, "branch": [
                    {"do": {"wander": [100, 0]}},
                ]},
            ],
        },
    }
    assert BT.validate(raw) == []
    fb = BT.build(raw, npc_slots={"g0": 2, "g1": 3, "prey": 4})
    cb = fb.compile()
    assert set(cb.brain_bodies) == {"pack", "prey"}
    assert IDENTITY in cb.brain_bodies["pack"]
    # class rows expand everywhere rows are iterated
    assert BT.row_members(raw["behavior"]["unit"][0]) == ["g0", "g1"]
    assert BT.pooled_npcs(raw) == set()


def test_toml_class_row_refusals():
    from ff9mapkit.content import behaviortoml as BT
    base = {
        "npc": [{"name": "a", "pos": [0, 0]}, {"name": "b", "pos": [9, 0]}],
        "behavior": {"brains": True, "unit": [
            {"npcs": ["a", "b"], "branch": [{"do": {"hold": [0, 0]}}]}]},
    }
    import copy
    ok = BT.validate(base)
    assert ok == [], ok
    nb = copy.deepcopy(base)
    nb["behavior"]["brains"] = False
    assert any("brains = true" in p for p in BT.validate(nb))
    both = copy.deepcopy(base)
    both["behavior"]["unit"][0]["npc"] = "a"
    assert any("mutually exclusive" in p for p in BT.validate(both))
    shot = copy.deepcopy(base)
    shot["behavior"]["unit"][0]["branch"].insert(0, {"do": {"sfx": 108}})
    assert any("not a v1 CLASS action" in p for p in BT.validate(shot))
    dup = copy.deepcopy(base)
    dup["behavior"]["unit"].append(
        {"npc": "a", "branch": [{"do": {"hold": [0, 0]}}]})
    assert any("duplicate unit" in p for p in BT.validate(dup))


# ------------------------------------------------------------------ install (game-gated)
def _game_ready():
    try:
        import UnityPy  # noqa: F401
        from ff9mapkit import config
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_class_install_members_share_one_brain_slot():
    """End-to-end on real field 559: a 2-member class seats ONE brain entry and
    both members' tag-1 heads RunSharedScript the SAME slot."""
    from ff9mapkit.eb.model import EbScript
    from ff9mapkit.extract import EventBundle

    data = EventBundle().eb_for_id(559)
    eb = EbScript.from_bytes(data)
    hosts = [i for i in range(1, eb.entry_count)
             if eb.entry(i).func_by_tag(0) is not None
             and eb.entry(i).func_by_tag(1) is not None
             and eb.entry(i).func_by_tag(15) is None][:2]
    fb = B.FieldBehavior(
        [B.UnitSpec("a", entry=hosts[0], spawn=(0, 0), hp=3),
         B.UnitSpec("b", entry=hosts[1], spawn=(100, 100), hp=3)],
        brains=True, classes=[B.ClassSpec("pair", ("a", "b"))])
    fb.classes["pair"].tree = B.Selector(
        B.Sequence(fb.hp_le("pair", 0), B.Do(B.Die())),
        B.Sequence(fb.near("pair", B.PLAYER, 300), B.Do(B.Chase(B.PLAYER))),
        B.Do(B.HoldPost()),
    )
    cb = fb.compile()
    assert len(cb.brain_bodies) == 1
    out = fb.install(data, cb)
    eb2 = EbScript.from_bytes(out)

    def used(e):
        return {i for i in range(e.entry_count) if e.entry(i).size > 0}
    new = sorted(used(eb2) - used(eb))
    assert len(new) == 2                            # the ticker + ONE shared brain
    slots = set()
    for h in hosts:
        f1 = eb2.entry(h).func_by_tag(1)
        assert out[f1.abs_start] == 0x43            # RunSharedScript
        slots.add(out[f1.abs_start + 2])
    assert len(slots) == 1 and slots < set(new)     # the SAME brain slot


def test_wake_publication_law():
    """THE WAKE-PUBLICATION LAW (the BTCLASS boot misfire): under brains, the
    warm-up expiry pass must FALL THROUGH into the run path, so activation and
    the first mirror/scan/counter publication are ONE atomic ticker slice — a
    brain is its own Seq and can otherwise tick between "active set" and
    "counters published", reading a counter at its SEED (alive-counts seed 0
    and counter_eq 0 is armed AT the seed: the crier called the wipe at boot).
    v1 keeps the jump-to-wait byte-for-byte: its tree segments run inside the
    ticker AFTER the scan blocks, so the gap is structurally unobservable."""
    for brains in (False, True):
        fb = B.FieldBehavior([B.UnitSpec("a", 2, spawn=(0, 0)),
                              B.UnitSpec("b", 3, spawn=(9, 9))], brains=brains)
        fb.units["a"].tree = B.Selector(B.Do(B.Hold((0, 0))))
        fb.units["b"].tree = B.Selector(B.Do(B.Hold((9, 9))))
        cb = fb.compile()
        mirror0 = B._stmt(f"Global.Int16[{fb.bb.int16('player.mx')}] "
                          f"obj(uid=250).f[0] B_LET")
        at = cb.ticker_body.find(mirror0)
        assert at > 0
        if brains:
            # the wake block's last statement (…B_EXPR_END) falls through
            assert cb.ticker_body[at - 1] == 0x7F
        else:
            # v1: the 3-byte JMP-to-wait still sits between wake and run
            assert cb.ticker_body[at - 3] == 0x01
