"""``[siege]`` -- the fort-condor productization (:mod:`ff9mapkit.content.siege`).

Golden provenance: the desugared output mirrors ``condor_fit_bench.py``'s round-4
GROUP RE-FIT emission (in-game proven on field 30400) block for block -- the wave
table+schedule, the two rosters + alive scans, the war-room strip, THE PIN, the
stance-as-radius:contact engage, THE WIN-CONDITION SHAPE (detect-then-pay), the
parked pooled seats, and the honest (hireable-gated) war council."""
from __future__ import annotations

import copy

import pytest

from ff9mapkit import build as BLD
from ff9mapkit.content import behaviortoml as BT, siege as S

RAW = {
    "timer": 60, "waves": [55, 40, 20], "stipend": 3000,
    "win_gil": 2000, "win_item": "Phoenix Down", "loss_battle": 35,
    "base": {"model": "GEO_NPC_F4_CSO", "pos": [0, 400], "hp": 24, "face": 64},
    "ally": [
        {"name": "soldier", "label": "Soldier (chases, melee)",
         "model": "GEO_NPC_F0_CSO", "count": 3, "price": 300,
         "stance": "chase", "radius": 2000, "speed": 65},
        {"name": "shooter", "label": "Shooter (stationary)",
         "model": "GEO_NPC_F3_CSO", "count": 2, "price": 550,
         "stance": "hold", "radius": 600, "hp": 3, "interval": 15},
    ],
    "raider": [
        {"name": "mu", "model": "GEO_MON_F0_MUU", "count": 2, "wave": 1,
         "entrance": [[-800, -600], [-950, -600]], "route": [[-400, 0], [0, 300]],
         "speeds": [50, 45], "autoroute": False},
        {"name": "fang", "model": "GEO_MON_F0_FFG", "count": 1, "wave": 3,
         "hp": 6, "damage": 2, "entrance": [[-800, 900]], "route": [[-200, 500]],
         "autoroute": False},
    ],
}


def _spec(**over):
    return S.from_raw({**copy.deepcopy(RAW), **over})


# ------------------------------------------------------------------- validation
@pytest.mark.parametrize("over,frag", [
    ({"timer": None}, "timer"),
    ({"waves": [20, 40]}, "DESCENDING"),
    ({"waves": [70]}, "DESCENDING"),
    ({"base": {"model": "M"}}, "pos"),
    ({"flag_base": 8000}, "safe band"),
    ({"bogus": 1}, "unknown"),
])
def test_from_raw_rejects(over, frag):
    with pytest.raises(S.SiegeError) as ei:
        _spec(**over)
    assert frag in str(ei.value)


def test_from_raw_rejects_nested():
    bad = copy.deepcopy(RAW)
    bad["ally"][0]["stance"] = "sprint"
    with pytest.raises(S.SiegeError, match="stance"):
        S.from_raw(bad)
    bad2 = copy.deepcopy(RAW)
    bad2["raider"][0]["entrance"] = [[0, 0]]              # count=2, one stage
    with pytest.raises(S.SiegeError, match="entrance"):
        S.from_raw(bad2)
    bad3 = copy.deepcopy(RAW)
    bad3["raider"][1]["wave"] = 4                         # only 3 waves
    with pytest.raises(S.SiegeError, match="wave"):
        S.from_raw(bad3)
    bad4 = copy.deepcopy(RAW)
    bad4["ally"][1]["name"] = "soldier"                   # name collision
    with pytest.raises(S.SiegeError, match="distinct"):
        S.from_raw(bad4)


# ------------------------------------------------------------------- the emission
def test_behavior_raw_structure():
    spec = _spec()
    b = S.behavior_raw(spec)
    assert len(b["unit"]) == 1 + 3 + 5                    # base + raiders + allies
    assert [g["name"] for g in b["group"]] == ["raiders", "allies"]
    assert b["group"][0]["units"] == ["mu0", "mu1", "fang0"]
    assert b["table"][0]["values"] == [55, 40, 20]
    assert [p.get("button") for p in b["pool"]] == [True, None]   # ONE poller
    assert b["hud"][0]["values"][-1] == "hp:base"

    base = b["unit"][0]
    dos = [br["do"] for br in base["branch"]]
    # THE WIN-CONDITION SHAPE: two detect branches raise `won`, ONE pays
    raises = [br for br in base["branch"] if br.get("raise_flags") == ["won"]]
    assert len(raises) == 2
    assert all({"not_flag": "won"} in br["when"] for br in raises)
    pays = [br for br in base["branch"]
            if isinstance(br["do"], dict) and "award" in br["do"]
            and br.get("once") == "paid"]
    assert len(pays) == 1 and pays[0]["do"] == {"award": 2000, "item": "Phoenix Down"}
    assert {"battle": 35} in dos                          # the loss fight

    mu0 = next(u for u in b["unit"] if u["npc"] == "mu0")
    rdos = [br["do"] for br in mu0["branch"]]
    assert rdos[0] == {"die": "kills"}                    # the tally death
    assert rdos[1]["swing_at"] == "base"                  # the depot commit
    assert rdos[2]["engage"] == "allies" and rdos[2]["radius"] == 750   # THE PIN
    march = mu0["branch"][3]
    assert march["when"] == [{"counter_ge": ["wave", 1]}]
    assert march["do"]["march"][0] == [-800, -600]        # own stage prepended
    assert "route" not in march["do"]                     # autoroute=false passes through
    fang = next(u for u in b["unit"] if u["npc"] == "fang0")
    assert fang["branch"][3]["when"] == [{"counter_ge": ["wave", 3]}]

    sold = next(u for u in b["unit"] if u["npc"] == "soldier0")
    assert sold["pooled"] and sold["pool"] == "soldier"
    assert sold["branch"][1]["do"]["contact"] == S.CHASE_CONTACT      # chase stance
    shoot = next(u for u in b["unit"] if u["npc"] == "shooter0")
    assert shoot["branch"][1]["do"]["contact"] == 599     # hold: radius-1 = never moves
    assert shoot["branch"][2]["do"] == {"hold_post": True}


def test_win_sfx_fanfare_branch():
    """`win_sfx` adds ONE event-Once fanfare branch below the pay, gated on the
    same monotonic `won` flag (THE DRAINING-CONDITION LAW's authoring shape:
    the purse fires one tick, the cue the next)."""
    b = S.behavior_raw(_spec(win_sfx=108))
    base = b["unit"][0]
    fan = [br for br in base["branch"]
           if isinstance(br["do"], dict) and "sfx" in br["do"]]
    assert len(fan) == 1 and fan[0]["do"] == {"sfx": 108}
    assert fan[0]["when"] == [{"flag": "won"}] and fan[0]["once"] == "fanfare"
    dos = [br["do"] for br in base["branch"]]
    assert dos.index({"award": 2000, "item": "Phoenix Down"}) < dos.index({"sfx": 108})
    # absent key -> no fanfare branch; a non-int id is refused
    assert not any(isinstance(br["do"], dict) and "sfx" in br["do"]
                   for br in S.behavior_raw(_spec())["unit"][0]["branch"])
    with pytest.raises(S.SiegeError, match="win_sfx"):
        _spec(win_sfx="loud")


def test_win_flash_branch():
    """`win_flash` adds the wash one rung below the jingle: pay -> fanfare ->
    flash, all event-Once on the monotonic `won` flag. `true` means white."""
    b = S.behavior_raw(_spec(win_sfx=108, win_flash=True))
    base = b["unit"][0]
    dos = [br["do"] for br in base["branch"]]
    assert dos.index({"sfx": 108}) < dos.index({"flash": [255, 255, 255]})
    fl = next(br for br in base["branch"]
              if isinstance(br["do"], dict) and "flash" in br["do"])
    assert fl["when"] == [{"flag": "won"}] and fl["once"] == "winflash"
    # a colour list passes through; junk is refused
    b2 = S.behavior_raw(_spec(win_flash=[255, 60, 60]))
    assert any(br["do"] == {"flash": [255, 60, 60]} for br in b2["unit"][0]["branch"]
               if isinstance(br["do"], dict))
    with pytest.raises(S.SiegeError, match="win_flash"):
        _spec(win_flash=[255, 300, 0])
    with pytest.raises(S.SiegeError, match="win_flash"):
        _spec(win_flash="white")


def test_npc_blocks_park_the_pools():
    spec = _spec()
    npcs = S.npc_blocks(spec)
    assert npcs[0]["name"] == "base" and npcs[0]["face"] == 64
    stages = {n["name"]: n["pos"] for n in npcs}
    assert stages["mu1"] == [-950, -600]                  # raiders at their entrances
    # pooled allies park at the 9000-band (the ARMOURY idiom), spread apart
    parks = [n["pos"] for n in npcs if n["name"].startswith(("soldier", "shooter"))]
    assert all(p[0] >= 9000 and p[1] >= 8800 for p in parks)
    assert len({tuple(p) for p in parks}) == 5


def test_council_rows_are_honest():
    spec = _spec()
    ch = S.council_choice(spec, {"soldier": 8876, "shooter": 8877})
    texts = [o["text"] for o in ch["options"]]
    assert texts == ["Soldier (chases, melee) — 300 gil",
                     "Shooter (stationary) — 550 gil", "Never mind."]
    assert ch["options"][0]["set_flag"] == [S.REQUEST_FLAG_BASE, 1]
    assert ch["options"][0]["requires_flag"] == 8876
    assert "requires_flag" not in ch["options"][-1]       # the decline row is always shown


# ------------------------------------------------------------------- desugar + full build
_FIELD = ('[field]\nid = 30001\nname = "SIEGE"\narea = 11\n'
          "\n[camera]\npitch = 48.0\ndistance = 480.0\nfov = 46.0\n")


def _siege_toml() -> str:
    import io
    out = io.StringIO()
    out.write(_FIELD)
    out.write("\n[siege]\ntimer = 60\nwaves = [55, 40, 20]\nstipend = 3000\n"
              'win_gil = 2000\nwin_item = "Phoenix Down"\nwin_sfx = 108\n'
              "win_flash = true\nloss_battle = 35\n"
              '\n[siege.base]\nmodel = "GEO_NPC_F4_CSO"\npos = [0, 400]\nhp = 24\n')
    for a in RAW["ally"]:
        out.write("\n[[siege.ally]]\n")
        for k, v in a.items():
            out.write(f"{k} = {v!r}\n".replace("'", '"'))
    for r in RAW["raider"]:
        out.write("\n[[siege.raider]]\n")
        for k, v in r.items():
            if k == "autoroute":
                out.write("autoroute = false\n")
            else:
                out.write(f"{k} = {v!r}\n".replace("'", '"').replace("(", "[").replace(")", "]"))
    return out.getvalue()


def test_full_build_compiles(tmp_path):
    f = tmp_path / "s.field.toml"
    f.write_text(_siege_toml(), encoding="utf-8")
    p = BLD.FieldProject.load(f)
    assert not p.raw.get("_siege_error") and not p.raw.get("_siege_conflict")
    assert BLD.validate(p) == []
    assert len(p.raw["behavior"]["unit"]) == 9
    # the council's gates match a fresh allocation pass (deterministic contract)
    gates = [o["requires_flag"] for o in p.raw["choice"][-1]["options"][:-1]]
    assert gates == sorted(gates) and all(isinstance(g, int) for g in gates)
    # the generated behavior COMPILES to bytecode (the bench's dry-build check)
    all_units = [u["npc"] for u in p.raw["behavior"]["unit"]]
    txids = {(ui, bi): 900 + 10 * ui + bi for ui, bi, _ in BT.announce_lines(p.raw)}
    txids.update({("hud", hi): 890 + hi for hi, _h in BT.hud_lines(p.raw)})
    fb = BT.build(p.raw, npc_slots={n: i + 2 for i, n in enumerate(all_units)},
                  npc_txids_by_name={n.get("name"): 0 for n in p.raw.get("npc", [])},
                  behavior_txids=txids)
    cb = fb.compile()
    assert len(cb.ticker_body) > 1000
    # the fanfare (win_sfx = 108) compiled through: one RunSoundCode3 in the
    # base's dispatch bodies, chest-proven bank first
    from ff9mapkit.eb import disasm as D
    plays = [(ins.imm(0), ins.imm(1))
             for _tag, body in cb.action_funcs["base"]
             for ins in D.iter_code(body, 0, len(body))
             if ins.name == "RunSoundCode3"]
    assert plays == [(53248, 108)]
    # ... and the flash (win_flash = true): one white ADD-channel pair (the
    # stock white-out, NOT the mode-6/7 warp fade)
    fades = [(ins.imm(0), ins.imm(3), ins.imm(4), ins.imm(5))
             for _tag, body in cb.action_funcs["base"]
             for ins in D.iter_code(body, 0, len(body))
             if ins.op == 0xEC]
    assert fades == [(0, 255, 255, 255), (1, 0, 0, 0)]
    # determinism: a second load desugars to the identical raw
    p2 = BLD.FieldProject.load(f)
    assert p2.raw["behavior"] == p.raw["behavior"]
    assert p2.raw["choice"] == p.raw["choice"]


def test_validate_conflicts(tmp_path):
    conflicted = _siege_toml() + "\n[behavior]\nwarmup = 30\n"
    f = tmp_path / "c.field.toml"
    f.write_text(conflicted, encoding="utf-8")
    p = BLD.FieldProject.load(f)
    assert p.raw.get("_siege_conflict")
    assert any("owns the field's [behavior]" in pr for pr in BLD.validate(p))
    bad = _siege_toml().replace("timer = 60", "timer = 5")
    f2 = tmp_path / "b.field.toml"
    f2.write_text(bad, encoding="utf-8")
    probs = BLD.validate(BLD.FieldProject.load(f2))
    assert any("timer" in pr for pr in probs)
