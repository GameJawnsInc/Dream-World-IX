"""[ff9mapkit netsync s154] THE RETURN'S BATTLE HALF's BENCH, its REPO HALF -- studies/test-harness/scenarios/coop_battle_song.py.

The in-game bench is the proof (it runs the s153 DLL first: exactly BS-C-SIL and BS-W-SIL red). This file pins what the bench
builds on: its calibration ledger (the predicted set behavioural only, the N/A rows kept out of it), the offline oracle (BS-OR)
over real .eb bytes -- a load-time song op on a silent field must red it, since it would hide the battle song a SIL leg reads --
and every pure judge, each fed an s153-shaped sample set it must red and an s154-shaped one it must pass. The calibration's
PREMISE (BS-PRE) through the shipped sil_legs / song_leg / finish_calibration: a second silence that fails (BS-P2), or a SIL red
that is not the s153 behaviour, reds BS-CAL; on s154 the orphan witness must have read TRUE inside a stop's fade on some leg.

Every scenario-touching test runs in a CHILD process: a scenario puts its own dir on sys.path and reads its COOP_* knobs at import.
"""
import json
import pathlib
import subprocess
import sys
import textwrap

REPO = pathlib.Path(__file__).resolve().parents[2]
SCENARIOS = REPO / "studies" / "test-harness" / "scenarios"

_PRELUDE = r'''
import importlib.util, json, os, struct, sys
scen, tools, kit = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, tools)
sys.path.insert(0, kit)
os.environ.pop("COOP_CALIBRATE", None)
os.environ.pop("COOP_BS_SONGSRC", None)
from harness.channel import State
spec = importlib.util.spec_from_file_location("coop_battle_song", os.path.join(scen, "coop_battle_song.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
cb = m.cb

def field(n, fld, *, music=-1, returns=1, last="cold", ret_field=None, sid=-1, slot=-1, live=None, settled=False, control=True,
          ui="FieldHUD"):
    dio = {"booted": False, "boot": last, "returns": returns, "last_return": last,
           "last_return_field": fld if ret_field is None else ret_field}
    if live is not None:
        dio["boot_song"] = -1
        dio["leave_song_live"] = live
    return State({"frame": n, "ui_state": ui, "field": {"id": fld}, "player": {"x": 0.0, "z": -1900.0, "control": control},
                  "netsync": {"battle": {"end": {"music": music, "end_leave": {"settled": settled}}}, "diorama": dio,
                              "world": {"dio": {"suspend_song": slot, "song_sid": sid}}}})

def timed(states, dt=0.1, t0=100.0):
    return [(t0 + i * dt, s) for i, s in enumerate(states)]

class G:
    """A bench handle for a Ledger: every check and note recorded, nothing else."""
    def __init__(self):
        self.checks, self.notes = [], []
    def check(self, ok, label, detail=""):
        self.checks.append((bool(ok), label, str(detail)))
        return bool(ok)
    def note(self, text):
        self.notes.append(text)

def ledger(calibrate=True):
    g = G()
    return g, cb.Ledger(g, m.catalog(calibrate), finals=m.CAL_ONLY, width=1600)

def detail_of(g, cid):
    return [d for _ok, label, d in g.checks if label.startswith(cid + ":")][-1]

S153_SIL = "BOOT ok; RETURN ...; WRONG [156]; reached True, behavioural True"
BEH, NOT_REACHED = {"reached": True, "behavioural": True, "live_inside": None}, {"reached": False, "behavioural": False,
                                                                                  "live_inside": None}

def s153_other_rows(led):
    """the rows run() records around sil_legs, as s153 reads them (green, or N/A red)"""
    led.check("BS-OR", True, "problems none")
    led.check("BS-I", True, "armed")
    led.check("BS-S0a", False, "N/A -- not discriminating on this engine")
    led.check("BS-S0b", False, "N/A -- not discriminating on this engine")

def s153_tail(led):
    led.check("BS-W-SUSP", True, "the proven path")
    led.check("BS-C-SUSP", False, "N/A -- not discriminating on this engine")
    led.check("BS-R", True, "released")
'''


def _child(body: str) -> str:
    code = _PRELUDE + "\n" + textwrap.dedent(body)
    out = subprocess.run([sys.executable, "-c", code, str(SCENARIOS), str(REPO / "tools"), str(REPO / "ff9mapkit")],
                         capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, (out.stdout[-3000:], out.stderr[-3000:])
    return out.stdout


def test_the_calibration_ledger_is_behavioural_and_the_na_rows_stay_out_of_it():
    _child('''
        assert m.PREDICTED_S153 == ("BS-C-SIL", "BS-W-SIL")
        assert set(m.PREDICTED_S153) | set(m.NA_S153) <= set(m.CHECKS)
        assert not set(m.PREDICTED_S153) & set(m.NA_S153)
        assert "BS-W-SUSP" not in m.PREDICTED_S153 and "BS-W-SUSP" not in m.NA_S153   # the proven path: green on both
        assert "BS-OR" not in m.NA_S153 and "BS-P" not in m.NA_S153 and "BS-I" not in m.NA_S153
        assert m.calibration(False) == (m.PREDICTED_S153, m.NA_S153)
        assert m.calibration(True) == ((), ())                 # no lever on s154: nothing red
        assert m.CAL_ONLY == ("BS-PRE", "BS-CAL")
        for cid in m.CAL_ONLY:                                  # the calibration's own rows: never asked for, never a row
            assert cid not in m.catalog(False) and cid in m.catalog(True)
            assert cid not in m.PREDICTED_S153 and cid not in m.NA_S153
        # the second silence is its OWN row on every run, never predicted, never N/A (a red there is unpredicted)
        assert "BS-P2" in m.catalog(False) and "BS-P2" not in m.PREDICTED_S153 and "BS-P2" not in m.NA_S153
        assert list(m.CHECKS).index("BS-C-SIL") < list(m.CHECKS).index("BS-P2") < list(m.CHECKS).index("BS-W-SIL")
        assert set(m.LEGS) == set(m.PREDICTED_S153) | {"BS-W-SUSP", "BS-C-SUSP"}
        assert m.PROBE == "netsync.diorama.boot_song" and m.BENCH_SONG == 156
        assert m.SILENT_FIELDS == (30604, 30602) and m.SONGSRC == 30610
    ''')


def test_the_oracle_reads_the_load_time_sound_ops_off_real_eb_bytes():
    """load_sound_ops over a synthetic .eb in the real layout (the test_main_init_prepend fixture): every entry's tag 0 and entry
    0's tag 10 count; another entry's tag 10 and a region's tag 2 (a gateway's whoosh) never do."""
    _child('''
        from ff9mapkit.eb import opcodes
        RET = opcodes.RETURN
        def eb(*entries):
            bodies = []
            for funcs in entries:
                table, code, fpos = b"", b"", len(funcs) * 4
                for tag, body in funcs:
                    table += struct.pack("<HH", tag, fpos)
                    code += body
                    fpos += len(body)
                bodies.append(bytes([0, len(funcs)]) + table + code)
            head = bytearray(0x80)
            head[0:2] = b"EV"
            head[3] = len(entries)
            slots, off = bytearray(), len(entries) * 8
            for body in bodies:
                slots += struct.pack("<HHBBH", off, len(body), 0, 0, 0)
                off += len(body)
            return bytes(head) + bytes(slots) + b"".join(bodies)
        play9 = opcodes.run_sound_code(0, 9) + RET
        stop = opcodes.run_sound_code(265, 0xFFFF) + RET
        load = opcodes.run_sound_code(1792, 9) + RET
        raw = eb([(0, play9), (10, load)], [(0, stop), (2, opcodes.run_sound_code(265, 0xFFFF) + RET), (10, play9)])
        ops = m.load_sound_ops(raw)
        assert ops == [(0, 0, 0, 9), (0, 10, 1792, 9), (1, 0, 265, 0xFFFF)], ops
        assert m.song_changers(ops) == ops
        assert m.load_sound_ops(eb([(0, RET)], [(2, stop)])) == []          # a gateway's whoosh is no load-time op
        assert m.song_changers([(3, 0, 4616, 912)]) == []                    # a sound-bank preload is no song op
        assert m.song_changers([(3, 0, None, 9)]) == [(3, 0, None, 9)]       # a computed code could be one
    ''')


def test_the_oracle_reds_a_silent_field_with_any_song_op_and_an_ambiguous_source():
    _child('''
        ok = {30604: ([], "w4"), 30602: ([(3, 0, 4616, 912)], "w2"), 30610: ([(7, 0, 0, 9)], "src")}
        o = m.judge_oracle(ok, 30610)
        assert o["problems"] == {} and o["silent_ok"] and o["song"] == 9, o
        for code in (0, 1792, 265, None):
            bad = dict(ok)
            bad[30602] = ([(0, 0, code, 9)], "w2")
            o = m.judge_oracle(bad, 30610)
            assert not o["silent_ok"] and "field 30602" in o["problems"] and o["song"] == 9, (code, o)
            bad = dict(ok)
            bad[30604] = ([(0, 10, code, 9)], "w4")                          # Main_Reinit counts (a warm return runs it)
            assert not m.judge_oracle(bad, 30610)["silent_ok"], code
        missing = dict(ok)
        missing[30604] = (None, "field 30604: no stacked mod folder registers it")
        o = m.judge_oracle(missing, 30610)
        assert not o["silent_ok"] and "field 30604" in o["problems"]
        for src_ops in ([(7, 0, 0, 9), (8, 0, 0, 5)], [], [(7, 0, 0, None)], [(7, 0, 0, 156)], [(7, 0, 0, 9), (7, 0, None, 1)]):
            o = m.judge_oracle({**ok, 30610: (src_ops, "src")}, 30610)
            assert o["song"] is None and "song source" in o["problems"] and o["silent_ok"], (src_ops, o)
        o = m.judge_oracle({30604: ([], "w4"), 30602: ([], "w2")}, 30610)
        assert o["song"] is None and "song source" in o["problems"] and o["silent_ok"]
    ''')


def test_the_return_judge_never_judges_a_pre_init_sample():
    """[ff9mapkit netsync s154 calibration] THE PRE-INIT SAMPLE, as the first s153 calibration run measured it on BS-W-SUSP: the
    field already reads FieldHUD / not fading / not booted, but its init (where the seam stops the song, the slot is restored and
    `returns` is counted) has not run -- 156 current, sid 22, slot 9, returns not yet +1. Two frames later: the restored 9, the SAME
    instance 18, the slot empty, returns +1. The judge reads only samples after the return was counted, so s153's proven warm
    suspended path is green, and s153's silent-field red (156 still current long after the init) stays red."""
    _child('''
        pre = field(1, 30602, music=156, returns=0, last="warm", sid=22, slot=9)
        post = [field(i, 30602, music=9, returns=1, last="warm", sid=18) for i in range(2, 20)]
        ok, why, f = m.judge_return(timed([pre, *post]), 30602, want_music=9, mode="warm", returns0=0, sid=18)
        assert ok and "1 pre-init sample(s) not judged" in why, why
        # the pre-fix judge (every free sample) read that run red -- the fix is load-bearing
        free = [s for _t, s in timed([pre, *post]) if m.on_field_free(s, 30602)]
        assert m.music(free[0]) == 156 and m.suspend_song(free[0]) == 9
        # a silent field's s153 red is not a pre-init artefact: the battle song stays current after the init
        sil = timed([field(1, 30604, music=156, returns=0), *[field(i, 30604, music=156) for i in range(2, 20)]])
        ok, why, f = m.judge_return(sil, 30604, want_music=-1, mode="cold", returns0=0)
        assert not ok and "WRONG [156]" in why and f["behavioural"] is True, (why, f)
        # a return that is never counted is never judged green (all samples pre-init)
        never = timed([field(i, 30604, returns=0) for i in range(1, 10)])
        ok, why, f = m.judge_return(never, 30604, want_music=-1, mode="cold", returns0=0)
        assert not ok and "after the return was counted" in why, why
    ''')


def test_the_return_judge_reds_s153s_battle_song_and_passes_s154s_silence():
    _child('''
        # s154 (BS-C-SIL): the return counted cold on 30604, every free FieldHUD sample silent
        s154 = timed([field(1, 30604, ui="BattleHUD", returns=0), *[field(i, 30604) for i in range(2, 20)]])
        ok, why, f = m.judge_return(s154, 30604, want_music=-1, mode="cold", returns0=0)
        assert ok and f == {"behavioural": False, "live_inside": None}, (why, f)   # a green is never "the s153 behaviour"
        # s153: the battle song current on the returned field -- red on the music alone, and the ONE behavioural shape
        s153 = timed([field(1, 30604, ui="BattleHUD", returns=0), *[field(i, 30604, music=156) for i in range(2, 20)]])
        ok, why, f = m.judge_return(s153, 30604, want_music=-1, mode="cold", returns0=0)
        assert not ok and "WRONG [156]" in why and f["behavioural"] is True, (why, f)
        # ...one stray sample is enough (still only 156 wrong: behavioural)
        one = timed([*[field(i, 30604) for i in range(1, 10)], field(10, 30604, music=156)])
        ok, _why, f = m.judge_return(one, 30604, want_music=-1, mode="cold", returns0=0)
        assert not ok and f["behavioural"]
        # a song that is not the battle song's is red, but NOT the s153 behaviour
        ok, _why, f = m.judge_return(timed([field(i, 30604, music=9) for i in range(1, 10)]), 30604, want_music=-1,
                                     mode="cold", returns0=0)
        assert not ok and not f["behavioural"]
        # the instrument terms: not counted, the wrong branch, the wrong field, no free sample at all -- red, and never
        # behavioural even with s153's 156 on every sample (each is a red the s153 calibration must not count)
        assert not m.judge_return(s154, 30604, want_music=-1, mode="cold", returns0=1)[0]
        assert not m.judge_return(s154, 30604, want_music=-1, mode="warm", returns0=0)[0]
        other = timed([field(i, 30604, ret_field=30602) for i in range(1, 10)])
        assert not m.judge_return(other, 30604, want_music=-1, mode="cold", returns0=0)[0]
        unfree = timed([field(i, 30604, control=False) for i in range(1, 10)])
        ok, why, f = m.judge_return(unfree, 30604, want_music=-1, mode="cold", returns0=0)
        assert not ok and "no free FieldHUD sample" in why and not f["behavioural"]
        not_counted = m.judge_return(s153, 30604, want_music=-1, mode="cold", returns0=1)
        wrong_branch = m.judge_return(s153, 30604, want_music=-1, mode="warm", returns0=0)
        wrong_field = m.judge_return(timed([field(i, 30604, music=156, ret_field=30602) for i in range(1, 10)]), 30604,
                                     want_music=-1, mode="cold", returns0=0)
        held_slot = m.judge_return(timed([field(i, 30604, music=156, slot=9) for i in range(1, 10)]), 30604, want_music=-1,
                                   mode="cold", returns0=0)
        no_free = m.judge_return(timed([field(i, 30604, music=156, control=False) for i in range(1, 10)]), 30604,
                                 want_music=-1, mode="cold", returns0=0)
        for name, (ok, why, f) in {"not counted": not_counted, "wrong branch": wrong_branch, "wrong field": wrong_field,
                                   "slot held": held_slot, "no free sample": no_free}.items():
            assert not ok and f["behavioural"] is False, (name, why, f)
        # samples that are not free (the fade in, control off) are never judged on music
        mixed = timed([field(1, 30604, control=False, music=156), *[field(i, 30604) for i in range(2, 10)]])
        assert m.judge_return(mixed, 30604, want_music=-1, mode="cold", returns0=0)[0]
    ''')


def test_the_suspended_legs_judge_the_instance_and_the_slot_and_s154_the_orphan():
    _child('''
        good = timed([field(i, 30602, music=9, sid=4242, last="warm") for i in range(1, 30)])
        assert m.judge_return(good, 30602, want_music=9, mode="warm", returns0=0, sid=4242)[0]
        # a restart (a new instance: the double-suspend hazard) and a slot still holding the song are red
        restart = timed([field(i, 30602, music=9, sid=4343, last="warm") for i in range(1, 30)])
        ok, why, _f = m.judge_return(restart, 30602, want_music=9, mode="warm", returns0=0, sid=4242)
        assert not ok and "CHANGED" in why
        held = timed([field(i, 30602, music=9, sid=4242, slot=9, last="warm") for i in range(1, 30)])
        assert not m.judge_return(held, 30602, want_music=9, mode="warm", returns0=0, sid=4242)[0]
        # s154's orphan witness: false past the fade is green, true past it is THE ORPHAN, true only inside it is the stop's fade
        clean = timed([field(i, 30604, music=9, sid=7, live=False) for i in range(1, 30)])
        ok, why, f = m.judge_return(clean, 30604, want_music=9, mode="cold", returns0=0, sid=7, probe=True)
        assert ok and f["live_inside"] == 0 and "never read TRUE inside" in why, (why, f)   # green, but no receipt
        orphan = timed([field(i, 30604, music=9, sid=7, live=True) for i in range(1, 30)])
        ok, why, _f = m.judge_return(orphan, 30604, want_music=9, mode="cold", returns0=0, sid=7, probe=True)
        assert not ok and "the orphan" in why, why
        fading = timed([field(i, 30604, music=9, sid=7, live=i < 6) for i in range(1, 30)])   # 0.5 s of 0.1 s samples
        ok, why, f = m.judge_return(fading, 30604, want_music=9, mode="cold", returns0=0, sid=7, probe=True)
        # THE RECEIPT (L12): the stop's own fade read TRUE inside -- the latch armed; still green past the fade
        assert ok and f["live_inside"] == 5 and "read TRUE on 5 sample(s) inside" in why, (why, f)
        # the receipt counts only inside the fade: a true read at/after fade_s is the orphan, never a receipt
        edge = timed([field(i, 30604, music=9, sid=7, live=(i == 11)) for i in range(1, 30)])   # t0 + 1.0 s exactly
        ok, _why, f = m.judge_return(edge, 30604, want_music=9, mode="cold", returns0=0, sid=7, probe=True)
        assert not ok and f["live_inside"] == 0
        # the receipt reads FieldHUD samples on the field, free or not (the stop lands at the field's init, before control)
        early = timed([*[field(i, 30604, music=-1, sid=-1, live=True, control=False) for i in range(1, 4)],
                       *[field(i, 30604, music=9, sid=7, live=False) for i in range(4, 30)]])
        ok, _why, f = m.judge_return(early, 30604, want_music=9, mode="cold", returns0=0, sid=7, probe=True)
        assert ok and f["live_inside"] == 3, f
        short = timed([field(i, 30604, music=9, sid=7, live=False) for i in range(1, 5)])    # nothing 1 s past the first
        ok, why, _f = m.judge_return(short, 30604, want_music=9, mode="cold", returns0=0, sid=7, probe=True)
        assert not ok and "NONE that late" in why
        # an engine without the key: the probe term is skipped (the caller records that leg N/A), never read as false
        ok, _why, f = m.judge_return(good, 30602, want_music=9, mode="warm", returns0=0, sid=4242, probe=False)
        assert ok and f["live_inside"] is None
        absent = timed([field(i, 30604, music=9, sid=7) for i in range(1, 30)])
        ok, _why, f = m.judge_return(absent, 30604, want_music=9, mode="cold", returns0=0, sid=7, probe=True)
        assert not ok and f["live_inside"] == 0
    ''')


def test_the_second_silence_is_its_own_row_and_a_non_behavioural_red_reds_the_calibration():
    """M11 through the SHIPPED sequence (sil_legs + finish_calibration, run()'s own; silence / song_leg stubbed): s153's truth
    calibrates green; a failed second silence (BS-P2) or a SIL red that is not the s153 behaviour turns BS-CAL red."""
    _child('''
        def drive(silences, legs, *, probe=False):
            g, led = ledger()
            s153_other_rows(led)
            sil = iter(silences)
            leg = iter(legs)
            m.silence = lambda _g: next(sil)
            m.song_leg = lambda _g, **kw: next(leg)
            facts = {}
            m.sil_legs(g, led, {"silent_ok": True, "problems": {}}, probe, facts)
            s153_tail(led)
            led.close()
            m.finish_calibration(led, probe, facts)
            led.close(final=True)
            return g, led
        red_beh = (False, S153_SIL, BEH)
        # s153's truth: both silences read, both SIL legs red BY THE BEHAVIOUR -> BS-PRE and BS-CAL green
        g, led = drive([(True, "music [-1]"), (True, "music [-1]")], [red_beh, red_beh])
        assert led.done["BS-P2"] and led.done["BS-PRE"] and led.done["BS-CAL"], g.checks
        assert led.failed() == {"BS-C-SIL", "BS-W-SIL", "BS-S0a", "BS-S0b", "BS-C-SUSP"}
        # the review's hole 1: BS-C-SIL red by the behaviour, the SECOND silence fails -> BS-W-SIL 'not reached' is no
        # longer the predicted red: BS-P2 is an unpredicted red, so BS-CAL is red through it (and BS-PRE: W-SIL never ran)
        g, led = drive([(True, "music [-1]"), (False, "silence: dioboot refused")], [red_beh])
        assert not led.done["BS-P2"] and not led.done["BS-W-SIL"] and "not reached" in detail_of(g, "BS-W-SIL")
        assert not led.done["BS-CAL"] and "BS-P2" in detail_of(g, "BS-CAL"), detail_of(g, "BS-CAL")
        assert not led.done["BS-PRE"] and "BS-W-SIL: never ran" in detail_of(g, "BS-PRE")
        # hole 2: a SIL red folded in from a precondition (reached False) -- BS-PRE red, so BS-CAL red, the SET still equal
        g, led = drive([(True, "-1"), (True, "-1")], [red_beh, (False, "not reached: dioboot refused", NOT_REACHED)])
        assert not led.done["BS-PRE"] and not led.done["BS-CAL"]
        assert "unpredicted reds: ['BS-PRE']" in detail_of(g, "BS-CAL"), detail_of(g, "BS-CAL")
        # the first silence fails: every SIL row (BS-P2 included) is recorded red, never left to look predicted
        g, led = drive([(False, "silence: no free return")], [])
        assert {"BS-P", "BS-C-SIL", "BS-P2", "BS-W-SIL"} <= led.failed() and not led.done["BS-CAL"]
        # the oracle cannot vouch: the same
        g, led = ledger()
        m.silence = lambda _g: (True, "-1")
        m.sil_legs(g, led, {"silent_ok": False, "problems": {"field 30602": "PLAY"}}, False, {})
        assert {"BS-C-SIL", "BS-P2", "BS-W-SIL"} <= led.failed() and led.done["BS-P"]
    ''')


def test_song_legs_reached_term_keeps_a_wrong_boot_out_of_the_behaviour():
    """song_leg's own `reached` (the shipped leg, its moves stubbed): a warm leg that boots COLD still shows WRONG [156] on the
    return, but it is not the s153 behaviour, so BS-PRE stays red; the same leg booted warm is."""
    _child('''
        def booted(mode):
            return State({"frame": 1, "scene": "BattleMapDebug", "ui_state": "BattleHUD", "battle": {"debug": True},
                          "netsync": {"diorama": {"boot": mode}, "battle": {"end": {"music": 156}},
                                      "world": {"dio": {"suspend_song": -1}}}})
        class Game:
            state = field(0, 30602, returns=0, last="warm")
        ret = timed([field(i, 30602, music=156, last="warm") for i in range(1, 20)])
        m.cb.mark = lambda _g: 0
        m.cb.new = lambda _g, _at: ["26.10.2026 10:00:00 |I| [NetSync] diorama RETURN (warm) -> field 30602"]
        m._leave_timed = lambda _g, _f: (ret, "")
        for mode, want in (("warm", True), ("cold", False)):
            m._wire_boot = lambda _g, silent=False, mode=mode: (booted(mode), "")
            ok, why, f = m.song_leg(Game(), field=30602, warm=True, song=None, probe=False)
            assert not ok and "WRONG [156]" in why, why
            assert f["reached"] is want and f["behavioural"] is want, (mode, why, f)
            assert (f"reached {want}, behavioural {want}") in why
            g, led = ledger()
            m.finish_calibration(led, False, {"BS-C-SIL": BEH, "BS-W-SIL": f})
            assert led.done["BS-PRE"] is want, detail_of(g, "BS-PRE")
        # a leave that came back SETTLED (not mid-fight) is not reached either
        m._wire_boot = lambda _g, silent=False: (booted("warm"), "")
        m._leave_timed = lambda _g, _f: (timed([field(i, 30602, music=156, last="warm", settled=True) for i in range(1, 20)]), "")
        _ok, _why, f = m.song_leg(Game(), field=30602, warm=True, song=None, probe=False)
        assert f == {"reached": False, "behavioural": False, "live_inside": None}, f
        # a precondition miss and a refused boot never reach
        m._wire_boot = lambda _g, silent=False: (None, "dioboot refused: a scene fade is in flight")
        ok, why, f = m.song_leg(Game(), field=30602, warm=True, song=None, probe=False)
        assert not ok and why.startswith("not reached") and f == NOT_REACHED
    ''')


def test_the_s154_premise_is_the_witness_shown_true_inside_a_stops_fade():
    """L12's positive control: on s154 BS-PRE (hence BS-CAL) is green only when some leg's `leave_song_live` read TRUE inside the
    stop's fade -- a dropped or misplaced field latch (never true) reds the s154 calibration."""
    _child('''
        legs = {c: {"reached": True, "behavioural": False, "live_inside": 0} for c in m.LEGS}
        def cal(facts):
            g, led = ledger()
            for cid in m.CHECKS:
                if cid not in m.CAL_ONLY:
                    led.check(cid, True, "green")
            m.finish_calibration(led, True, facts)
            return g, led
        g, led = cal(legs)
        assert not led.done["BS-PRE"] and not led.done["BS-CAL"] and "on NO leg" in detail_of(g, "BS-PRE")
        assert "unpredicted reds: ['BS-PRE']" in detail_of(g, "BS-CAL")
        g, led = cal(dict(legs, **{"BS-W-SUSP": dict(legs["BS-W-SUSP"], live_inside=4)}))
        assert led.done["BS-PRE"] and led.done["BS-CAL"] and "['BS-W-SUSP']" in detail_of(g, "BS-PRE")
        g, led = cal({})                                         # nothing ran (an early raise): no receipt, red
        assert not led.done["BS-PRE"] and not led.done["BS-CAL"]
        # the pure premise on s153 ignores the receipts and wants the behaviour; on s154 it ignores the behaviour
        assert m.premise(False, {"BS-C-SIL": BEH, "BS-W-SIL": BEH})[0]
        assert not m.premise(True, {"BS-C-SIL": BEH, "BS-W-SIL": BEH})[0]
        assert not m.premise(False, {c: dict(BEH, behavioural=False, live_inside=9) for c in m.LEGS})[0]
    ''')


def test_the_boot_judge_wants_the_bench_song_the_branch_and_the_slot():
    _child('''
        def booted(mode, music, slot):
            return State({"frame": 1, "scene": "BattleMapDebug", "ui_state": "BattleHUD", "battle": {"debug": True},
                          "netsync": {"diorama": {"boot": mode}, "battle": {"end": {"music": music}},
                                      "world": {"dio": {"suspend_song": slot}}}})
        assert m.judge_booted(booted("warm", 156, 9), want_mode="warm", want_slot=9)[0]
        assert m.judge_booted(booted("cold", 156, -1), want_mode="cold", want_slot=-1)[0]
        assert not m.judge_booted(booted("cold", 156, 9), want_mode="warm", want_slot=9)[0]   # a cold boot on the warm leg
        assert not m.judge_booted(booted("warm", 9, 9), want_mode="warm", want_slot=9)[0]     # the battle song never played
        assert not m.judge_booted(booted("warm", 156, -1), want_mode="warm", want_slot=9)[0]  # nothing suspended
        assert not m.judge_booted(None, want_mode="warm", want_slot=9)[0]
    ''')


def test_the_returnsong_rung_is_s154s_after_worlddio_and_its_keys_end_the_diorama_block(tmp_path):
    """THE LEVEL HOME for s154's harness keys: the `returnsong` rung rides the ONE ladder right after `worlddio`, adds no sub-verb
    and nothing under `netsync.battle`, and appends `boot_song` (-1) + `leave_song_live` (false) at the END of `netsync.diorama`
    (after `hold`: AppendDioramaReturnSong); the s153 stand-in (the ladder prefix through `worlddio`) publishes neither. The
    agent's own catch line is pinned against these by test_harness_netsync's f33-sentinel test once the s154 patch lands."""
    sys.path.insert(0, str(REPO / "tools"))
    from harness import fakegame as FG
    from harness.fakegame import FakeGame
    names = list(FG.NETSYNC_BATTLE_CAPS)
    assert names[names.index("worlddio") + 1] == "returnsong" and FG.NETSYNC_BATTLE_CAPS["returnsong"] == ("s154", ())
    assert FG.NETSYNC_S154_CAPS == frozenset(("returnsong",)) and "returnsong" not in FG.caps_through("worlddio")
    assert FG.NETSYNC_BATTLE_CAP_KEYS["returnsong"] == {} and FG.NETSYNC_DIORAMA_CAP_KEYS["returnsong"] == ("boot_song",
                                                                                                           "leave_song_live")
    (tmp_path / "x64").mkdir()
    (tmp_path / "x64" / "FF9.exe").write_bytes(b"MZ")
    (tmp_path / "x64" / "Memoria.log").write_text("fake log\n", encoding="utf-8")
    fake = FakeGame(tmp_path)
    dio = fake._netsync_doc()["diorama"]
    assert list(dio)[-3:] == ["hold", "boot_song", "leave_song_live"] and (dio["boot_song"], dio["leave_song_live"]) == (-1, False)
    fake.netsync_caps = FG.caps_through("worlddio")
    old = fake._netsync_doc()["diorama"]
    assert "boot_song" not in old and "leave_song_live" not in old and list(old)[-1] == "hold"


def test_the_songsrc_bench_field_is_a_plain_song_room():
    """The minted song source (deployed and registered as 30610 in FF9CustomMap-msgs; the bench's BS-OR re-reads the DEPLOYED bytes
    every run, never this file) plays one song and nothing else."""
    import tomllib
    doc = tomllib.loads((REPO / "studies" / "battle-coop" / "bench" / "songsrc.field.toml").read_text(encoding="utf-8"))
    assert doc["field"]["id"] == 30610 and doc["music"] == {"song": 9}
    assert not {"encounter", "party", "gateway", "npc", "playable"} & set(doc)
    assert json.dumps(doc["music"]["song"]) != "156"
