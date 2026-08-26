"""The per-unit-brain backend (``brains=True``) — rung 0 of the SEQBRAIN fold-back.

The architecture the bench proved (30422, all five composites in-game): each
unit's tree segment compiles into its OWN one-function Seq entry, spawned from
the unit's tag-1 head via RunSharedScript; gCur = the unit for the Seq's whole
life, so dispatches target uid 255; the residual ticker keeps every field-level
lane. v1 (brains off) must be byte-identical to before the flag existed.
"""
import pytest

from ff9mapkit.content import behavior as B

REQ_255 = bytes((0x10, 0x00, 0x04, 0xFF))          # REQ, argflag 0, level 4, uid 255
DIE_GUARDED = bytes((0x45, 0x1C, 0x00, 0xFF))      # StopSharedScript then TerminateEntry(255)


def _roster(brains: bool) -> tuple:
    fb = B.FieldBehavior([
        B.UnitSpec("kn", 2, spawn=(0, 0), hp=3),
        B.UnitSpec("mu", 3, spawn=(100, 0), hp=2),
    ], brains=brains)
    for u, foe in (("kn", "mu"), ("mu", "kn")):
        fb.units[u].tree = B.Selector(
            B.Sequence(fb.hp_le(u, 0), B.Do(B.Die(linger=30))),
            B.Sequence(fb.near(u, foe, 300), B.Do(B.SwingAt(foe, damage=1, interval=40))),
            B.Do(B.Wander(center=(0, 0), radius=400)),
        )
    return fb, fb.compile()


def test_brains_moves_unit_segments_out_of_the_ticker():
    _, cb0 = _roster(False)
    _, cb1 = _roster(True)
    assert not cb0.brain_bodies
    assert set(cb1.brain_bodies) == {"kn", "mu"}
    # the ticker keeps only the shared lanes — every unit segment left it
    assert len(cb1.ticker_body) < len(cb0.ticker_body) // 2
    assert not any(nm.startswith("unit ") for nm, _ in cb1.sizes["ticker_segments"])
    assert any(nm.startswith("unit ") for nm, _ in cb0.sizes["ticker_segments"])
    # brains show up in the histogram
    assert "brains" in cb1.size_report()
    assert cb0.stable_hash() != cb1.stable_hash()


def test_brains_dispatch_targets_uid_255():
    _, cb0 = _roster(False)
    _, cb1 = _roster(True)
    assert all(REQ_255 in b for b in cb1.brain_bodies.values())
    assert REQ_255 not in cb0.ticker_body             # v1 targets the unit's entry


def test_brains_die_body_stops_its_own_shared_script():
    """THE ORPHAN-BRAIN LAW: TerminateEntry(255) disposes the unit and DisposeObj
    does NOT cascade to uid+64 — the die body must 0x45 first (and only in
    brains mode: a v1 field has no Seq to orphan)."""
    _, cb0 = _roster(False)
    _, cb1 = _roster(True)
    for cb, want in ((cb0, False), (cb1, True)):
        die = [b for b in dict(cb.action_funcs["kn"]).values()
               if b"\x1c\x00\xff" in b]
        assert len(die) == 1
        assert (DIE_GUARDED in die[0]) is want


def test_brains_off_by_default_and_toml_key():
    from ff9mapkit.content import behaviortoml as BT
    raw = {
        "npc": [{"name": "g", "pos": [0, 0]}],
        "behavior": {
            "brains": True,
            "unit": [{"npc": "g", "branch": [
                {"do": {"hold": [0, 0]}},
            ]}],
        },
    }
    fb = BT.build(raw, npc_slots={"g": 2})
    assert fb.brains is True
    raw["behavior"].pop("brains")
    fb2 = BT.build(raw, npc_slots={"g": 2})
    assert fb2.brains is False
    assert not fb2.compile().brain_bodies


def test_64_stride_guard():
    units = [B.UnitSpec("a", 2, spawn=(0, 0)), B.UnitSpec("b", 200, spawn=(0, 0))]
    with pytest.raises(B.BehaviorError, match="255"):
        B.check_64_stride(set(), units)                    # 200 + 64 > Byte
    with pytest.raises(B.BehaviorError, match="OCCUPIED"):
        B.check_64_stride({66}, units[:1])                 # 2 + 64 collides
    B.check_64_stride({0, 1, 2, 3, 10}, units[:1])         # clean layout passes


# ------------------------------------------------------------------ install (game-gated)
def _game_ready():
    try:
        import UnityPy  # noqa: F401
        from ff9mapkit import config
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_brains_install_on_a_real_field_eb():
    """End-to-end on real field 559: brains seat as dormant one-function entries,
    each unit's tag-1 head opens with RunSharedScript(its brain's slot), and the
    lint baseline-diff gate passes."""
    from ff9mapkit.eb.model import EbScript
    from ff9mapkit.extract import EventBundle

    data = EventBundle().eb_for_id(559)
    eb = EbScript.from_bytes(data)
    hosts = [i for i in range(1, eb.entry_count)
             if eb.entry(i).func_by_tag(0) is not None
             and eb.entry(i).func_by_tag(1) is not None
             and eb.entry(i).func_by_tag(15) is None][:2]
    fb = B.FieldBehavior([
        B.UnitSpec("a", entry=hosts[0], spawn=(0, 0)),
        B.UnitSpec("b", entry=hosts[1], spawn=(100, 100), hp=3),
    ], brains=True)
    fb.units["a"].tree = B.Selector(
        B.Sequence(fb.near("a", B.PLAYER, 300), B.Do(B.Chase(B.PLAYER))),
        B.Do(B.Hold((0, 0))),
    )
    fb.units["b"].tree = B.Selector(
        B.Sequence(fb.hp_le("b", 0), B.Do(B.Die())),
        B.Do(B.Patrol([(0, 0), (200, 0)])),
    )
    cb = fb.compile()
    out = fb.install(data, cb)
    eb2 = EbScript.from_bytes(out)

    def used(e):
        return {i for i in range(e.entry_count) if e.entry(i).size > 0}
    new = sorted(used(eb2) - used(eb))
    assert len(new) == 1 + len(cb.brain_bodies)       # the ticker + one brain per unit
    # each unit's tag-1 opens with RunSharedScript(one of the new slots)
    for h in hosts:
        f1 = eb2.entry(h).func_by_tag(1)
        assert out[f1.abs_start] == 0x43
        assert out[f1.abs_start + 2] in new
    # brains are one-function (tag 0) code entries
    for s in new:
        tags = [f.tag for f in eb2.entry(s).funcs]
        assert tags == [0]
