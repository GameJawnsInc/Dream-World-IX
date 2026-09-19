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
    # the v1 TICKER emission golden — the `brains = false` escape hatch must
    # keep the ratified round-4 shape byte-for-byte (brains is the default)
    spec = _spec(brains=False)
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


def test_win_flash_reveal_beat():
    """With win_flash the DETECT branches carry the wash (the rout one also
    raises `routed`) and the cries move BELOW it — THE REVEAL BEAT (round-3
    playtest: a window opening as the white-out starts fights it): the wash
    body holds the dispatch level and the request lane fires on run==0 in
    ladder order, so cry -> purse -> jingle land at the release."""
    b = S.behavior_raw(_spec(win_sfx=108, win_flash=True))
    br = b["unit"][0]["branch"]
    flashes = [x for x in br if isinstance(x["do"], dict) and "flash" in x["do"]]
    assert len(flashes) == 2                      # one per ending, both the colour
    assert all(x["do"] == {"flash": [255, 255, 255]} for x in flashes)
    assert flashes[0]["raise_flags"] == ["won", "routed"]     # the rout detect
    assert flashes[1]["raise_flags"] == ["won"]               # the timer detect
    crys = [x for x in br if isinstance(x["do"], dict) and "announce" in x["do"]
            and x.get("once") in ("routcry", "wincry")]
    assert crys[0]["when"] == [{"flag": "routed"}]
    assert crys[1]["when"] == [{"flag": "won"}, {"not_flag": "routed"}]
    assert not crys[0].get("raise_flags") and not crys[1].get("raise_flags")
    dos = [x["do"] for x in br]
    i_flash = dos.index({"flash": [255, 255, 255]})
    i_cry = br.index(crys[0])
    i_pay = dos.index({"award": 2000, "item": "Phoenix Down"})
    i_sfx = dos.index({"sfx": 108})
    assert i_flash < i_cry < i_pay < i_sfx        # wash -> cry -> purse -> jingle
    # a colour list passes through; WITHOUT win_flash the proven announce-on-
    # detect shape is unchanged; junk is refused
    b2 = S.behavior_raw(_spec(win_flash=[255, 60, 60]))
    assert any(x["do"] == {"flash": [255, 60, 60]} for x in b2["unit"][0]["branch"]
               if isinstance(x["do"], dict))
    plain = S.behavior_raw(_spec(win_sfx=108))["unit"][0]["branch"]
    det = [x for x in plain if x.get("once") in ("routcry", "wincry")]
    assert all(x.get("raise_flags") == ["won"] and "announce" in x["do"]
               for x in det)
    with pytest.raises(S.SiegeError, match="win_flash"):
        _spec(win_flash=[255, 300, 0])
    with pytest.raises(S.SiegeError, match="win_flash"):
        _spec(win_flash="white")


def test_fight_theater_folds_onto_the_generated_actions():
    """Per-class clips + the global hit cue ride the generated swing/engage/die
    actions; absent dials add NO keys (the proven shapes stay byte-for-byte)."""
    over = copy.deepcopy(RAW)
    over["hit_sfx"] = 640
    over["brains"] = False                    # the v1 per-unit rows this test pins
    over["ally"][0].update(anim="attack_cid_1", death_anim="hiza_1", linger=45)
    over["raider"][0].update(anim="jump", death_anim="jump")
    b = S.behavior_raw(S.from_raw(over))
    sold = next(u for u in b["unit"] if u["npc"] == "soldier0")
    assert sold["branch"][0]["do"] == {"die": True, "anim": "hiza_1", "linger": 45}
    assert sold["branch"][1]["do"]["anim"] == "attack_cid_1"
    assert sold["branch"][1]["do"]["hit_sfx"] == 640
    mu0 = next(u for u in b["unit"] if u["npc"] == "mu0")
    assert mu0["branch"][0]["do"] == {"die": "kills", "anim": "jump",
                                      "linger": S.DEATH_LINGER}
    assert mu0["branch"][1]["do"]["hit_sfx"] == 640          # the depot commit
    assert mu0["branch"][2]["do"]["anim"] == "jump"          # THE PIN
    # a class with no dials keeps the bare shapes; so does a siege with none
    shoot = next(u for u in b["unit"] if u["npc"] == "shooter0")
    assert shoot["branch"][0]["do"] == {"die": True}
    assert "anim" not in shoot["branch"][1]["do"]
    assert shoot["branch"][1]["do"]["hit_sfx"] == 640        # ... but the global cue
    plain = S.behavior_raw(_spec())
    for u in plain["unit"]:
        for br in u["branch"]:
            assert "anim" not in br["do"] and "hit_sfx" not in br["do"]
    with pytest.raises(S.SiegeError, match="hit_sfx"):
        _spec(hit_sfx="thwack")


def test_clock_stops_before_the_ending_theater():
    """THE CLOCK-COUPLED BATTLE LAW (REDOUBT rung-D playtest): B_SYSVAR[17] IS
    TimerUI.Time and real battle AI reads it — the donor's own Hunt scenes
    (35 / LB_E080x) run `B_SYSVAR[17] B_NOT -> RunBattleCode` end, so they
    terminate themselves when the countdown reads 0. The ending's theater takes
    seconds, so the clock MUST freeze before any of it runs."""
    b = S.behavior_raw(S.from_raw({**copy.deepcopy(RAW), "loss_sfx": 1942,
                                   "text_loss": ["l1", "l2"]}))
    br = b["unit"][0]["branch"]
    stops = [x for x in br
             if isinstance(x["do"], dict) and x["do"].get("stop_timer")]
    assert len(stops) == 2                                  # the loss + the rout
    loss_stop = next(x for x in stops if x["when"] == [{"hp_le": 0}])
    assert loss_stop["once"] == "clockstop"
    # it outranks EVERY loss cue — sting, staged text, and the battle
    i_stop = br.index(loss_stop)
    for once in ("losssting", "losstext0", "losstext1"):
        assert i_stop < next(i for i, x in enumerate(br) if x.get("once") == once)
    assert i_stop < next(i for i, x in enumerate(br) if "battle" in x["do"])
    # the rout freezes too (it wins EARLY — the clock is still running); the
    # timer win is at 0:00 by definition and needs no stop
    rout_stop = next(x for x in stops if x["when"] == [{"flag": "routed"}])
    assert rout_stop["once"] == "routclock"
    # stop_timer without a field timer is refused by lint
    bad = {"player": {"spawn": [0, -900]},
           "npc": [{"name": "c", "pos": [0, -300], "dialogue": "..."}],
           "behavior": {"unit": [{"npc": "c", "branch": [
               {"when": [{"hp_le": 0}], "do": {"stop_timer": True},
                "once": "s"},
               {"do": {"hold": [0, -300]}}]}]}}
    assert any("needs field-level" in p for p in BT.validate(bad))


def test_loss_sfx_pre_detect_sting():
    """`loss_sfx` seats an event-Once sting BETWEEN die-on-`lost` and the loss
    detect — the branch holds selection until it delivers (the reveal-beat
    serialization pointed the other way), so it rings before the detect raises
    `lost`, before a loss_battle suspends the field, and before the die branch
    terminates the base. hp<=0 is monotonic (swings gate on target hp > 0)."""
    for over in ({}, {"loss_battle": None}):      # the battle AND announce paths
        b = S.behavior_raw(S.from_raw({**copy.deepcopy(RAW), "loss_sfx": 1942,
                                       **over}))
        br = b["unit"][0]["branch"]
        sting = next(x for x in br
                     if isinstance(x["do"], dict) and x["do"].get("sfx") == 1942)
        assert sting["when"] == [{"hp_le": 0}] and sting["once"] == "losssting"
        assert not sting.get("raise_flags")       # detection stays the detect's job
        # the SUSTAIN is the beat: order alone gave the sting ONE ~33ms frame
        # before the battle took the audio (rung-C round-1 playtest)
        assert sting["do"]["sustain"] == S.LOSS_STING_SUSTAIN
        i_die = next(i for i, x in enumerate(br) if x["do"] == {"die": True})
        i_det = next(i for i, x in enumerate(br)
                     if x.get("raise_flags") == ["lost"])
        assert i_die < br.index(sting) < i_det    # die > sting > detect
    # absent key -> no sting; junk refused
    assert not any(isinstance(x["do"], dict) and x["do"].get("sfx") == 1942
                   for x in S.behavior_raw(_spec())["unit"][0]["branch"])
    with pytest.raises(S.SiegeError, match="loss_sfx"):
        _spec(loss_sfx="thud")


def test_staged_ending_text():
    """Ending texts as LISTS page on held dispatch levels: loss lines page
    PRE-detect (the sting idiom scaled to text — last line sustained before a
    battle); win/rout aftermath lines page AFTER the proven cry/purse/jingle
    beat, gated per-ending (the flashless rout detect grows `routed` so the
    win stages can tell the endings apart). Plain strings keep today's bytes."""
    over = {"text_win": ["WE HELD!", "The city pays.", "The Colonel smiles."],
            "text_rout": ["BROKEN!", "None left standing."],
            "text_loss": ["The depot burns.", "Fall back!"]}
    b = S.behavior_raw(S.from_raw({**copy.deepcopy(RAW), **over}))
    br = b["unit"][0]["branch"]
    # loss (battle path): both lines pre-detect, the last sustained, then battle
    lt = [x for x in br if str(x.get("once", "")).startswith("losstext")]
    assert [x["do"]["announce"] for x in lt] == ["The depot burns.", "Fall back!"]
    assert "delay" not in lt[0]["do"] and lt[1]["do"]["delay"] == 120
    assert lt[1]["do"]["sustain"] == 120
    i_battle = next(i for i, x in enumerate(br) if "battle" in x["do"])
    assert br.index(lt[1]) < i_battle
    # flashless staging: the rout detect raises `routed`
    rout_det = next(x for x in br if x.get("once") == "routcry")
    assert rout_det["raise_flags"] == ["won", "routed"]
    # aftermath stages sit BELOW pay (below fanfare too when present) and
    # gate per ending
    wt = [x for x in br if str(x.get("once", "")).startswith("wintext")]
    assert [x["do"]["announce"] for x in wt] == ["The city pays.",
                                                 "The Colonel smiles."]
    assert all(x["do"]["delay"] == 120 for x in wt)
    assert all(x["when"] == [{"flag": "won"}, {"not_flag": "routed"}] for x in wt)
    rt = [x for x in br if str(x.get("once", "")).startswith("routtext")]
    assert [x["do"]["announce"] for x in rt] == ["None left standing."]
    assert rt[0]["when"] == [{"flag": "routed"}]
    i_pay = next(i for i, x in enumerate(br) if "award" in x["do"])
    assert i_pay < br.index(rt[0]) < br.index(wt[0])
    # announce-path loss (no battle): the FINAL line is the losscry, delayed
    b2 = S.behavior_raw(S.from_raw({**copy.deepcopy(RAW), "loss_battle": None,
                                    "text_loss": ["l1", "l2"]}))
    cry = next(x for x in b2["unit"][0]["branch"] if x.get("once") == "losscry")
    assert cry["do"] == {"announce": "l2", "delay": 120}
    assert cry["raise_flags"] == ["lost"]
    # refusals
    with pytest.raises(S.SiegeError, match="text_pace"):
        _spec(text_pace=5)
    with pytest.raises(S.SiegeError, match="text_win"):
        _spec(text_win=[])


def test_wave_herald_and_alarm_theater():
    """A siege's waves otherwise arrive in SILENCE. `text_waves` (one cry per
    wave) + `wave_sfx` herald each arrival off the MONOTONIC wave counter, so
    they ride the event-Once lane straight; `alarm_sfx` cues the alarm and
    `text_alarm` stages like the endings."""
    b = S.behavior_raw(_spec(text_waves=["FIRST WAVE!", "", "HEAVIES!"],
                             wave_sfx=700, alarm_sfx=701,
                             text_alarm=["They're through!", "Hold the line!"]))
    br = b["unit"][0]["branch"]
    cues = [x for x in br if str(x.get("once", "")).startswith("wavecue")]
    crys = [x for x in br if str(x.get("once", "")).startswith("wavecry")]
    assert len(cues) == 3                       # one per wave, even unnamed ones
    assert all(x["do"] == {"sfx": 700} for x in cues)
    assert [x["do"]["announce"] for x in crys] == ["FIRST WAVE!", "HEAVIES!"]
    # gates are counter_ge on the monotonic wave counter, in wave order
    assert [x["when"] for x in cues] == [[{"counter_ge": ["wave", i]}]
                                         for i in (1, 2, 3)]
    assert crys[1]["when"] == [{"counter_ge": ["wave", 3]}]   # "" skipped wave 2
    # cue precedes its line
    assert br.index(cues[0]) < br.index(crys[0])
    # the alarm: cue, then staged lines (the 2nd delayed by text_pace)
    acue = next(x for x in br if x.get("once") == "alarmcue")
    a0 = next(x for x in br if x.get("once") == "alarm")
    a1 = next(x for x in br if x.get("once") == "alarm1")
    assert acue["do"] == {"sfx": 701}
    assert br.index(acue) < br.index(a0) < br.index(a1)
    assert "delay" not in a0["do"] and a1["do"]["delay"] == 120
    # the alarm gate (`any_near`) DRAINS, so only the FIRST beat rides it and
    # latches; the rest gate on that flag (THE DRAINING-CONDITION LAW)
    assert acue["raise_flags"] == ["alarmed"]
    assert a0["when"] == a1["when"] == [{"flag": "alarmed"}]
    # a siege with none of these dials is byte-unchanged: one plain alarm, no waves
    plain = S.behavior_raw(_spec())["unit"][0]["branch"]
    assert not [x for x in plain if str(x.get("once", "")).startswith("wave")]
    pa = [x for x in plain if str(x.get("once", "")).startswith("alarm")]
    assert len(pa) == 1 and pa[0]["do"] == {"announce": S.DEFAULT_ALARM_TEXT}
    # refusals
    with pytest.raises(S.SiegeError, match="text_waves"):
        _spec(text_waves=["a", "b", "c", "d"])   # 4 lines, 3 waves
    with pytest.raises(S.SiegeError, match="text_waves"):
        _spec(text_waves="FIRST")
    with pytest.raises(S.SiegeError, match="wave_sfx"):
        _spec(wave_sfx="horn")


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
              "win_flash = true\nloss_sfx = 1942\nloss_battle = 35\n"
              'text_win = ["WE HELD THE DEPOT!", "The city pays in full."]\n'
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
    # the v1 full-build golden (brains = false; the default path is covered by
    # test_brains_full_build_compiles)
    f = tmp_path / "s.field.toml"
    f.write_text(_siege_toml().replace("[siege]", "[siege]\nbrains = false", 1),
                 encoding="utf-8")
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
    assert plays == [(53248, 1942), (53248, 108)]     # the sting body seats first
                                                      # (ladder order); then the fanfare
    # the clock freeze compiled through: RunTimer(0) bodies (loss + rout)
    stops = [ins.imm(0) for _tag, body in cb.action_funcs["base"]
             for ins in D.iter_code(body, 0, len(body)) if ins.op == 0x7D]
    assert stops == [0, 0]
    # ... and the flash (win_flash = true): white ADD-channel pairs (the stock
    # white-out, NOT the mode-6/7 warp fade) — one body per detect branch
    fades = [(ins.imm(0), ins.imm(3), ins.imm(4), ins.imm(5))
             for _tag, body in cb.action_funcs["base"]
             for ins in D.iter_code(body, 0, len(body))
             if ins.op == 0xEC]
    assert fades == [(0, 255, 255, 255), (1, 0, 0, 0)] * 2
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


# ------------------------------------------------- brains emission (condor P1)
def test_brains_emits_class_rows():
    """`brains = true`: each ally TYPE and each raider GROUP folds into ONE
    npcs= class row (one shared brain); the raider march drops its per-member
    [stage] head (members hold_post at their stage spawns and walk the SHARED
    lane at private wp progress), and the raider engage/march carry NO speed=
    so each member walks at its OWN row-speeds preset (anti-lockstep jitter)."""
    spec = _spec(brains=True)
    b = S.behavior_raw(spec)
    assert b["brains"] is True
    rows = {u.get("class"): u for u in b["unit"] if u.get("npcs")}
    assert set(rows) == {"soldier", "shooter", "mu", "fang"}
    assert rows["soldier"]["npcs"] == ["soldier0", "soldier1", "soldier2"]
    assert rows["soldier"]["pooled"] and rows["soldier"]["pool"] == "soldier"
    assert rows["mu"]["speeds"] == [50, 45]
    mu = rows["mu"]["branch"]
    march = next(br["do"] for br in mu if "march" in br["do"])
    assert march["march"] == [[-400, 0], [0, 300]]        # no [stage] head
    assert "speed" not in march
    engage = next(br["do"] for br in mu if "engage" in br["do"])
    assert "speed" not in engage
    assert mu[-1]["do"] == {"hold_post": True}
    # the base stays a single-unit row (its theater inlines in its own brain)
    base_rows = [u for u in b["unit"] if u.get("npc") == "base"]
    assert len(base_rows) == 1


def test_brains_is_the_default():
    """CONDOR P2: no `brains` key -> the per-class brains emission (parity-
    ratified on the acceptance field); `brains = false` is the escape hatch."""
    assert _spec().brains is True
    b = S.behavior_raw(_spec())
    assert b["brains"] is True
    assert any(u.get("npcs") for u in b["unit"])


def test_brains_false_restores_v1_emission():
    """The escape hatch: per-unit rows with the [stage] march head and
    per-action speeds — byte-for-byte the round-4 shape the goldens pin."""
    b = S.behavior_raw(_spec(brains=False))
    assert "brains" not in b
    assert all(u.get("npc") for u in b["unit"])           # no class rows
    mu0 = next(u for u in b["unit"] if u["npc"] == "mu0")
    march = next(br["do"] for br in mu0["branch"] if "march" in br["do"])
    assert march["march"][0] == [-800, -600]              # the stage head
    assert march["speed"] == 50


def test_brains_full_build_compiles(tmp_path):
    """The whole [siege] -> desugar -> validate -> compile path under brains:
    class brains exist per type, the council still resolves hireable flags."""
    raw = copy.deepcopy(RAW)
    raw["brains"] = True
    field = {"id": 30990, "name": "BRSIEGE", "siege": raw}
    S.desugar(field)
    assert "_siege_error" not in field, field.get("_siege_error")
    assert field["behavior"]["brains"] is True
    work = copy.deepcopy(field)
    for u in work["behavior"]["unit"]:
        for br in u.get("branch", []) or []:
            if isinstance(br.get("do"), dict):
                br["do"].pop("route", None)
    assert BT.validate(work) == []
    names = [m for u in work["behavior"]["unit"] for m in BT.row_members(u)]
    txids = {(ui, bi): 900 + 10 * ui + bi for ui, bi, _ in BT.announce_lines(work)}
    txids.update({("hud", hi): 890 + hi for hi, _h in BT.hud_lines(work)})
    fb = BT.build(work, npc_slots={n: i + 2 for i, n in enumerate(names)},
                  npc_txids_by_name={n.get("name"): 0 for n in work.get("npc", [])},
                  behavior_txids=txids)
    cb = fb.compile()
    assert set(cb.brain_bodies) == {"base", "soldier", "shooter", "mu", "fang"}
    assert len(cb.ticker_body) < 12000                    # the residual ticker only


def test_wide_band_carries_its_own_flag_window():
    """THE REDOUBT REGRESSION (found rebuilding the shipped acceptance bench):
    the safe partition's 96-flag Blackboard window cannot hold a condor-scale
    siege's event-once latch+request lanes under the v1 ticker — the shipped
    REDOUBT stopped compiling after the partition landed. byte_band = "wide"
    now brings its own 240-flag window seated directly below the wide byte
    band, under the same standalone-only contract."""
    from ff9mapkit.content import behavior as B
    assert (B.WIDE_FLAG_BASE, B.WIDE_FLAG_END) == (9520, 9759)
    assert B.WIDE_FLAG_END + 1 == B.WIDE_BYTE_BASE * 8    # flush under the bytes
    raw = {"npc": [{"name": "u0", "pos": [0, 0]}],
           "behavior": {"byte_band": "wide", "unit": [
               {"npc": "u0", "branch": [{"do": {"hold": [0, 0]}}]}]}}
    fb = BT.build(raw, npc_slots={"u0": 2}, npc_txids_by_name={"u0": 0},
                  behavior_txids={})
    assert fb.bb.flag_band == (B.WIDE_FLAG_BASE, B.WIDE_FLAG_END)
