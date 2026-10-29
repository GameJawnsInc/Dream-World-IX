"""s163 -- THE HOST'S SPEED ON A FOLLOWING GUEST, the TWO-GAME bench (tools/harness/duo.py; studies/field-coop/SPEED-MIRROR.md rev 3).
[ff9mapkit netsync s163]

Two real FF9s on this desktop, paired by duo.py (the guest FOLLOWING, its state mirror ARMED). The solo bench (coop_speed_mirror.py)
proves the latch, the getter and the levers on the selftest role through a bench host; it cannot reach section 10 on a REAL lane, the
ATE episode's START term (b), or the follow's tail hold. This bench replays GUEST-TRAVERSAL-TWO-PC.md Finding 10 end to end: "Dagger
Tries" (Dali 351 -> 450 -> 351) with the HOST at 3x through the real F1 path (`speedmode 1`) and the guest following at its own 1x.
In the third two-PC session the guest's copy played 450 at 1x, the host left after ~21 s, the tail hold let go on its 8 s progress
clock across 450's 9 s wordless beat (texts 161 -> 162), seqs 88-101 were dropped as another field's, the guest was cut at line 162 of
175 and the host waited ~11 s for it on 351.

THE ATE ON 351 (the HW export test2_94.txt, field 351's script). Code3_Loop is the ATE menu: `IsMovementEnabled == 1 && VAR_GenInt8_238
== 1 && IsButton(Select)` opens `EnableDialogChoices(VAR_GenInt16_241 | 32768, 0)` + WindowSync(1, 64, 98); choice 2 ("Dagger
Tries") shows its title (WindowAsync(0, 64, 101)), saves the player's spot into 243/245/247/249, sets entrance 16 and runs
Field(450). The gate is the same pair 352 uses -- gEventGlobal byte 238 (availability) and the Int16 at 241/242 (the row mask, bit i =
choice i) -- and Main_Init writes them at every load: with a New Game's VARL bits (VARL_GenUInt16_297 & 1 == 0) its cascade falls to
`ATE(0); 238 = 0; 241 = 0`, so the load CLEARS the gate, exactly as on 352. Nothing on an idle 351 rewrites them afterwards: Code4_Loop
re-arms only under VARL_GenBool_2102 (0 in a New Game), Cat_Loop only on entrance 16, Dagger_Init only when Dagger is the player. So
the bench pokes AFTER both copies settle -- the guest first, the host last, right before its press: byte 238 = 1, word 241 = 4 (bit 2,
"Dagger Tries"; the window adds Cancel), 242 = 0; the pick is choice 2. Main_Init's `VAR_GenInt16_239 = 2` (entrance not 16 / 18)
is 450's way home: OglopA_Loop's `switchex (VAR_GenInt16_239)` case 2 sets entrance 17 and runs Field(351) after the last line, and
351's Zidane_Init case 17 restores the saved spot. On 450 (test2_112.txt) the ATE is Dagger_Loop case 0: Wait(35), the first line
WindowSync(3, 128, 153) "I wonder...", the last WindowAsync(3, 128, 175) "Aaahhh!" (Dagger's window 3; the Old Lady speaks in 6).

THE HOST'S PACE. The host presses Confirm PAGE_S (0.5 s) after a window opened and again every PAGE_S while it stays up -- the owner's
own pace in Finding 10 (153-175, 23 lines, in ~16 s at 3x). A first press on a line still typing only finishes its text, so the host
never closes a line before it is whole: a correct 3x guest (whose lock waits for its own copy's typing and MinShowMs 350) then trails
by the lane's latency alone, never by a growing backlog. A slower host would let the 1x calibration guest past 450's wordless beat
before the tail arms (D1's span bound guards it).

  D0      both on 351 with control (the guest by ONE follow); the host's own 238, poked to 1 (and read back) BEFORE its warp, read 0
          after its load (the instrument: the load did wipe it -- a 0 that was 0 already would prove nothing), and after the pokes
          both copies read 238 = 1, 241 = 4, 242 = 0.
  D1      THE HOST AT 3x: `speedmode 1` on the host logs 'speed mirror (host): my booster is ON (setting S, FieldTPS T)' once (S > 1),
          the host reads raw true, own_factor S and ff S on 351 and ff S on every sample of its own on 450, and its 450 span (its
          landing to its 351 load) is at most HOST_SPAN_MAX_S (24 s: the 3x ATE ran ~21 s in Finding 10; at 1x it runs ~3x longer).
  D2      SECTION 10 ON THE WIRE: a guest sample reads netsync.speed host_setting S, host_tps T, src "wire", host_seen true, host_stale
          false (the guest's cache from a real host frame).
  D3      THE GUEST'S OWN JUMP (the s161 relay, the instrument): 'my copy's own Field(450) passes -- the host's pick (choice 2) on field
          351' once, its landed line, ONE 'Map: 450', and 450's first line 'win 3 text 153 opened locked' after the landing.
  D4      THE MIRROR ON 450: after the guest's landed line, a 'speed mirror: ON on field 450 -- factor F (the host's booster S x T TPS
          covers my G x M; my own factor 1) -- ...' with F == S == G > 1; and a guest sample on 450 with its control off reads mirror and
          applied true, factor_now F, ff F, raw false (its own flag untouched), with FAST MODE on some applied sample. With S == G (the
          prereq below) D4 cannot tell my G from the host's S: an engine that applied the host's setting reads the same here -- the
          solo bench's S-ON (its bench host 5 above G) and NetSyncSpeed.SelfTest's factor.host_faster_is_still_mine carry that law.
  D5      NO TAIL RELEASE: the guest logs no 'the follow to field 351 stops waiting -- my copy's ATE on field 450 ...' (neither the
          progress clock, 'made no progress for 8 s', nor the 30 s cap) -- its copy kept pace and took its own exit.
  D6      NO DROPS: the guest logs no 'host seq N (win W text T) dropped -- it is for field 450' (Finding 10: seqs 88-101).
  D7      THE LAST LINE: the guest's copy opened 450's last line locked ('win 3 text 175 opened locked') and the host's event closed
          it ('dialogue: win 3 text 175 closed (host seq') -- Finding 10 cut it at 162.
  D8      THE GAP: the guest's first sample on 351 after 450 lands at most GAP_MAX_S (4 s) after the host's, and by its own exit (no
          'following the peer to field 351'). Why 4 s: under the mirror both copies run 450 at the same factor, so the guest trails by
          its landing offset (Finding 10: within a second), plus the lock's per-line delivery (a state frame and the hop, ~0.15-0.3 s,
          NOT cumulative while the guest's line is ready before the host's next close arrives -- the host's paging keeps it so),
          plus the same scripted exit at the same factor: ~1.5 s expected, 4 s with margin. At 1x the same measure read ~11 s
          (Finding 10), and the s162 rule cannot get back on its own at all: a 1x copy needs ~3x the host's ATE, so the follow carries
          it once a tail clock lets go -- part two reds whatever the clock.
  D9      THE GUEST'S FREE ROAM: back on 351 with its control on (from 1 s after control, for 2 s), every guest sample reads ff 1,
          factor_now 1, applied / mirror false, raw false -- while every host sample still reads ff S (the host's own 3x roam: the
          positive control).

THE CALIBRATION (COOP_CALIBRATE=1 or off; rev 3): `netsync speed off` on the GUEST (legal on a client since rev 3: both duo games load
one Assembly-CSharp through the instance junction, so a DLL swap to s162 would take `speedmode` from the host too), held from before the
press to the end. PREDICTED_OFF = D4, D5, D6, D7, D8 red: the guest plays 450 at 1x, Finding 10's very shape -- no ON line (its
why_not reads the lever), the progress clock releases the follow across the wordless beat, the rest of 450's events are dropped as
another field's, the guest never reaches 175, and the follow (not its own exit) carries it to 351 late. D0-D3 and D9 stay green: the
relay, the host's booster, section 10 on the wire (the lever only refuses the START) and the guest's own speed in free roam (1 either
way). The calibration's shape rests on Finding 10's timing for BOTH copies, and each side has its guard. The host's: D1's span bound
(a host slower than 24 s could let the 1x copy past the beat before the tail arms -- then it reds D1 itself, an unpredicted red that
voids the calibration). The guest's: the BEAT GUARD in D-CAL-M -- the copy's highest Dagger line opened locked by the host's first
351 sample is at most 161, i.e. the 1x copy had not yet passed 450's 9 s wordless beat (161 -> 162) when the tail armed; a copy that
cleared it early (its lines close at typing + MinShowMs on the host's already-queued closes) gets no progress release, only the 30 s
cap's, by when the host's 162-175 events may have aged out (PendingTtlMs 20 s): no drop, D6 green -- a timing miss the guard names as
the calibration's own void, never an unexplained unpredicted green. D-CAL-M needs the guest's lever read back ('off'), the beat
guard, and each predicted red's marker: D4 no ON line on 450 and the lever's why_not on a control-off 450 sample; D5 a release by the
PROGRESS clock (the predicted one -- a cap release is the other timing); D6 a drop; D7 the copy's highest Dagger line below 175; D8
the follow's line.
Any other COOP_CALIBRATE word is REFUSED AT LOAD, before duo.py boots the pair (the s162 lesson: never a silent default).

    py tools/harness/duo.py studies/test-harness/scenarios/coop_speed_mirror_duo.py
    COOP_CALIBRATE=1 py tools/harness/duo.py studies/test-harness/scenarios/coop_speed_mirror_duo.py

Prereqs as duo.py's: no FF9 running from either root, no controller connected, nobody at the keyboard (THE UNATTENDED LAW); both
roots' [Cheats] SpeedFactor and [Graphics] FieldTPS equal (the mirror refuses a guest rate that would overshoot the host's).
NOT PROVEN HERE: a non-ATE scene (term (a) alone) and a relayed talk (term (c)) on a real lane; a stale lane (killing the host's
bridge); Finding 4's capped follow-hold (not built); a 3x GUEST behind a 1x host (README step 3).
"""
from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                          # noqa: E402 - Ledger
from harness import duo as duo_mod                                 # noqa: E402 - watched_byte

HarnessError = cb.HarnessError

HUB, DEST, SCENARIO = 351, 450, 2600     # Dali/Inn (the lobby) -> Dali/Field; the morning after the inn rest (the session's)
B_AVAIL, B_ROWS_LO, B_ROWS_HI = 238, 241, 242
ROWS = 4                                 # bit 2: choice 2 "Dagger Tries" (the window adds Cancel, bit 15)
PICK = 2
TITLE_WORD = "Dagger"                    # the title card, WindowAsync(0, 64, 101) "Dagger Tries"
FIRST_LINE = (3, 153)                    # 450's Dagger_Loop case 0: WindowSync(3, 128, 153) "I wonder..."
LAST_LINE = (3, 175)                     # ...WindowAsync(3, 128, 175) "Aaahhh!" (Finding 10 cut the guest at 162)
BEAT_LAST = 161                          # the last Dagger line before 450's 9 s wordless beat (161 -> 162): D-CAL-M's beat guard
ARRIVE_S = 30.0
MENU_S = 5.0
WIRE_S = 3.0
PAGE_S = 0.5                             # the host presses Confirm this long after a line opened, and again every PAGE_S (Finding 10's pace)
ATE_S = 150.0                            # the title's close to both back on 351 (a cap: the 3x ATE runs ~20 s)
BACK_S = 40.0                            # after the host's 351 load: the 1x calibration guest is carried in by a release (8-30 s)
SETTLE_S = 1.5                           # after both are back: the guest's late lines land
HOST_SPAN_MAX_S = 24.0                   # D1: the host's 450 span at 3x (Finding 10: ~21 s)
GAP_MAX_S = 4.0                          # D8 (see the module note)
ROAM_SETTLE_S = 1.0                      # D9: from this long after the guest's control (the latch's StepInMs 500 is spent)
ROAM_S = 2.0
ROAM_MIN = 5
FIELD_SCENE = "FieldMap"

ON_RX = re.compile(r"speed mirror: ON on field (-?\d+) -- factor (-?\d+) \(the host's booster (-?\d+) x (-?\d+) TPS covers my (-?\d+) x "
                   r"(-?\d+); my own factor (-?\d+)\) -- (.+?)\s*$")
HOST_ON_RX = re.compile(r"speed mirror \(host\): my booster is ON \(setting (\d+), FieldTPS (\d+)\)")
LOCKED_RX = re.compile(r"dialogue lock: win (\d+) text (\d+) opened locked")
WHY_LEVER = "the speed lever is off"
PASSES = f"ATE relay: my copy's own Field({DEST}) passes -- the host's pick (choice {PICK}) on field {HUB}"
LANDED = f"ATE relay: my copy's own Field({DEST}) landed"
RELEASE = f"stops waiting -- my copy's ATE on field {DEST}"
RELEASE_PROGRESS = "the tail hold's progress clock"
RELEASE_CAP = "hold's cap"
DROPPED = f"dropped -- it is for field {DEST}"
FOLLOWED = f"following the peer to field {HUB}"

CLAIMS = {
    "D0": "both on 351 with control (the guest by ONE follow), the host's 238 (poked to 1 before its warp) wiped by its load, the gate "
          "bytes 238 = 1, 241 = 4, 242 = 0 on both",
    "D1": "the host at 3x through `speedmode 1`: its booster-ON line once (setting S > 1), raw true, own_factor / ff S on 351, ff S on "
          "its own 450 samples, its 450 span <= 24 s",
    "D2": "section 10 on the wire: a guest sample reads host_setting S, host_tps T, src 'wire', host_seen true, host_stale false",
    "D3": "the guest's own Field(450) passed on the host's pick (choice 2), landed, one 'Map: 450', and 450's first line (win 3 text "
          "153) opened locked after the landing",
    "D4": "the guest's mirror ON on 450 after its landing at factor F = S = its own G (my own factor 1); a control-off 450 sample "
          "reads mirror / applied, factor_now F, ff F, raw false; FAST MODE",
    "D5": "no tail-hold release for 450 on the guest (neither the 8 s progress clock nor the 30 s cap)",
    "D6": "no host seq dropped on the guest as field 450's",
    "D7": "the guest's copy opened 450's last line (win 3 text 175) locked and the host's event closed it",
    "D8": "the guest back on 351 within 4 s of the host, by its own exit (no follow to 351)",
    "D9": "the guest's free roam on 351 at its own factor 1 (ff, factor_now 1, no mirror, raw false) while the host still reads ff S",
}
PREDICTED_OFF = ("D4", "D5", "D6", "D7", "D8")
CAL_ID, CAL_M_ID = "D-CAL", "D-CAL-M"
OFF_MARKER = ("the guest's lever read back 'off'; the beat guard (the copy's highest Dagger line at the host's 351 landing <= 161); D4 "
              "no ON line on 450 and the lever's why_not on a control-off 450 sample; D5 a tail release by the progress clock; D6 a drop; "
              "D7 the copy's highest Dagger line below 175; D8 the follow's line")


def calibration() -> str | None:
    v = os.environ.get("COOP_CALIBRATE", "").strip().lower()
    if v in ("", "0"):
        return None
    if v in ("1", "off", "true", "yes", "on"):
        return "off"
    raise SystemExit(f"coop_speed_mirror_duo: COOP_CALIBRATE={v!r} is refused -- the duo takes 1 / off (`netsync speed off` on the "
                     f"GUEST, same DLL: rev 3) and nothing else; refused before the pair boots.")


CAL_MODE = calibration()                 # at load: duo.py imports the scenario before it boots the pair


def catalog(cal) -> dict:
    cat = dict(CLAIMS)
    if cal:
        cat[CAL_M_ID] = "the lever was taken on the guest and every predicted red carries its marker: " + OFF_MARKER
        cat[CAL_ID] = "the guest's `speed off` calibration (same DLL): exactly " + ", ".join(PREDICTED_OFF) + " red"
    return cat


# --------------------------------------------------------------------------------------------- reads (pure)
def ival(v) -> int | None:
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def read(st, t: float) -> dict:
    """One sample of one game, flattened: what every judge below reads."""
    sp = cb.path(st, "netsync.speed")
    sp = sp if isinstance(sp, dict) else {}
    raw = cb.raw(st)
    return {"t": t, "field": int((raw.get("field") or {}).get("id", -1)), "ctl": (raw.get("player") or {}).get("control") is True,
            "scene": raw.get("scene"), "ff": ival(raw.get("ff")), "mirror": sp.get("mirror") is True, "applied": sp.get("applied") is True,
            "factor_now": ival(sp.get("factor_now")), "raw": sp.get("raw"), "own": ival(sp.get("own_factor")),
            "fast_mode": sp.get("fast_mode") is True, "why_not": sp.get("why_not"), "host_setting": ival(sp.get("host_setting")),
            "host_tps": ival(sp.get("host_tps")), "src": sp.get("src"), "seen": sp.get("host_seen"), "stale": sp.get("host_stale"),
            "lever": sp.get("lever")}


def _count(msgs, needle: str) -> int:
    return sum(1 for m in msgs if needle in m)


def _count_both(msgs, needle: str, also: str) -> int:
    """Lines holding both ``needle`` and ``also`` (a tail release AND its clock's words)."""
    return sum(1 for m in msgs if needle in m and also in m)


def _rx(msgs, pattern: str) -> list:
    rx = re.compile(pattern)
    return [m for m in msgs if rx.search(m)]


def _grep(msgs, *needles, limit: int = 500) -> str:
    return " || ".join(m for m in msgs if any(n in m for n in needles))[:limit]


def _fmt(parts) -> str:
    return ", ".join(f"{k} {'ok' if v else 'NO'}" for k, v in parts)


def parse_on(msgs) -> list:
    out = []
    for i, m in enumerate(msgs):
        r = ON_RX.search(m)
        if r:
            f, fac, s, t, g, mt, own = (int(r.group(k)) for k in range(1, 8))
            out.append({"i": i, "field": f, "factor": fac, "s": s, "t": t, "g": g, "m": mt, "own": own, "why": r.group(8)})
    return out


def host_booster(hmsgs) -> tuple:
    """(S, T, how many ON lines) off the host's booster-ON lines (S / T None without one)."""
    hits = [HOST_ON_RX.search(m) for m in hmsgs]
    hits = [h for h in hits if h]
    return (int(hits[0].group(1)), int(hits[0].group(2)), len(hits)) if hits else (None, None, 0)


def locked_texts(msgs, win: int) -> list:
    """Every text id opened locked in window ``win``, in order."""
    out = []
    for m in msgs:
        r = LOCKED_RX.search(m)
        if r and int(r.group(1)) == win:
            out.append(int(r.group(2)))
    return out


def judge_host(hmsgs, h351, host_samples, t_h450, t_h351) -> tuple:
    """D1 (PURE): the host's booster line, a 351 sample right after `speedmode 1` (``h351``), its own 450 samples, its 450 span."""
    s, t, n = host_booster(hmsgs)
    on450 = [x for x in host_samples if x["field"] == DEST and x["scene"] == FIELD_SCENE and x["ff"] is not None and x["ff"] >= 0]
    span = (t_h351 - t_h450) if (t_h450 is not None and t_h351 is not None) else None
    parts = [("one booster-ON line", n == 1), ("S > 1", isinstance(s, int) and s > 1), ("T > 0", isinstance(t, int) and t > 0),
             ("raw true on 351", h351 is not None and h351["raw"] is True),
             ("own_factor S on 351", h351 is not None and h351["own"] == s), ("ff S on 351", h351 is not None and h351["ff"] == s),
             ("ff S on 450", len(on450) >= 5 and all(x["ff"] == s for x in on450)),
             ("450 span <= %g s" % HOST_SPAN_MAX_S, span is not None and 0 < span <= HOST_SPAN_MAX_S)]
    return all(v for _, v in parts), (_fmt(parts) + f"; setting {s!r}, FieldTPS {t!r}; 450 span {span if span is None else round(span, 2)} s; "
                                      f"ff on 450 {sorted({str(x['ff']) for x in on450})}; {_grep(hmsgs, 'speed mirror (host)')}")


def judge_wire(guest_samples, s, t) -> tuple:
    """D2 (PURE): some guest sample reads the host's section 10 off the wire."""
    hit = [x for x in guest_samples if x["host_setting"] == s and x["host_tps"] == t and x["src"] == "wire" and x["seen"] is True
           and x["stale"] is False]
    last = guest_samples[-1] if guest_samples else {}
    return (bool(hit) and isinstance(s, int) and s > 1), (f"{len(hit)} of {len(guest_samples)} guest samples read setting {s} x "
                                                         f"{t} from the wire; last {({k: last.get(k) for k in ('host_setting', 'host_tps', 'src', 'seen', 'stale')})}")


def judge_jump(gm) -> tuple:
    """D3 (PURE): the guest's own jump into 450 and its first line there."""
    land = next((i for i, m in enumerate(gm) if LANDED in m), None)
    first = f"dialogue lock: win {FIRST_LINE[0]} text {FIRST_LINE[1]} opened locked"
    after = land is not None and any(first in m for m in gm[land + 1:])
    parts = [("passes once", _count(gm, PASSES) == 1), ("landed", land is not None), ("one Map: 450", _count(gm, f"Map: {DEST} ") == 1),
             ("153 after the landing", after)]
    return all(v for _, v in parts), _fmt(parts) + f"; {_grep(gm, 'Field(', 'Map: ', 'text 153', limit=500)}"


def judge_on(gm, guest_samples, s) -> tuple:
    """D4 (PURE): the guest's ON line on 450 after its landing, at the host's setting and its own G; a control-off 450 sample with the
    factor applied through the real getter."""
    land = next((i for i, m in enumerate(gm) if LANDED in m), None)
    ons = [o for o in parse_on(gm) if o["field"] == DEST and land is not None and o["i"] > land]
    o = ons[0] if ons else {}
    fac = o.get("factor")
    live = [x for x in guest_samples if x["field"] == DEST and not x["ctl"] and x["mirror"] and x["applied"]]
    good = [x for x in live if x["factor_now"] == fac and x["ff"] == fac and x["raw"] is False]
    parts = [("landed", land is not None), ("an ON line on 450 after it", bool(ons)),
             ("F = the host's S", isinstance(fac, int) and fac == s), ("F = my G", fac is not None and fac == o.get("g")),
             ("F > 1", isinstance(fac, int) and fac > 1), ("my own factor 1", o.get("own") == 1),
             ("applied through the getter", bool(good)), ("FAST MODE", any(x["fast_mode"] for x in live))]
    return all(v for _, v in parts), (_fmt(parts) + f"; ON lines on 450 {[(x['factor'], x['why']) for x in ons][:3]}; {len(good)} of "
                                      f"{len(live)} applied samples read F; why_not on 450 "
                                      f"{sorted({str(x['why_not']) for x in guest_samples if x['field'] == DEST})}")


def judge_hold(gm) -> tuple:
    """D5 (PURE): no tail-hold release for 450 (either clock)."""
    rel = [m for m in gm if RELEASE in m]
    prog = sum(1 for m in rel if RELEASE_PROGRESS in m)
    return not rel, (f"releases {len(rel)} (progress clock {prog}, cap {sum(1 for m in rel if RELEASE_CAP in m)}); holds "
                     f"{_count(gm, f'the follow to field {HUB} waits')}; {_grep(gm, 'stops waiting', 'the follow to field', limit=400)}")


def judge_drops(gm) -> tuple:
    """D6 (PURE): no host seq dropped as field 450's."""
    d = [m for m in gm if DROPPED in m]
    return not d, f"dropped as 450's {len(d)}, aged out (any field) {_count(gm, 'aged out')}; {_grep(gm, DROPPED, limit=400)}"


def judge_last(gm) -> tuple:
    """D7 (PURE): the guest's copy opened 450's last line locked and the host's event closed it."""
    w, t = LAST_LINE
    opened = _count(gm, f"dialogue lock: win {w} text {t} opened locked")
    closed = len(_rx(gm, r"dialogue: win %d text %d closed \(host seq" % (w, t)))
    texts = locked_texts(gm, w)
    return opened >= 1 and closed >= 1, (f"175 opened locked {opened}, closed by the host {closed}; the guest's window-3 lines "
                                         f"{texts[:30]}")


def judge_gap(gm, t_h351, t_g351) -> tuple:
    """D8 (PURE): the guest's 351 arrival (seconds, the bench's one clock) within GAP_MAX_S of the host's, by its own exit."""
    gap = (t_g351 - t_h351) if (t_h351 is not None and t_g351 is not None) else None
    fol = _count(gm, FOLLOWED)
    parts = [("both back", gap is not None), ("gap <= %g s" % GAP_MAX_S, gap is not None and gap <= GAP_MAX_S),
             ("by its own exit (no follow)", fol == 0)]
    return all(v for _, v in parts), (_fmt(parts) + f"; gap {gap if gap is None else round(gap, 2)} s (host back at {t_h351!r}, guest at "
                                      f"{t_g351!r}); follows to {HUB} {fol}")


def judge_roam(guest_roam, host_roam, s) -> tuple:
    """D9 (PURE): the guest's own factor in free roam on 351 while the host still reads its booster."""
    g_on = [x for x in guest_roam if x["field"] == HUB and x["ctl"]]
    parts = [("guest roam samples", len(g_on) >= ROAM_MIN and len(g_on) == len(guest_roam)),
             ("ff 1", bool(g_on) and all(x["ff"] == 1 for x in g_on)),
             ("factor_now 1", bool(g_on) and all(x["factor_now"] == 1 for x in g_on)),
             ("no mirror / applied", not any(x["mirror"] or x["applied"] for x in guest_roam)),
             ("raw false", bool(g_on) and all(x["raw"] is False for x in g_on)),
             ("the host still at S", bool(host_roam) and isinstance(s, int) and s > 1 and all(x["ff"] == s for x in host_roam))]
    return all(v for _, v in parts), (_fmt(parts) + f"; guest ff {sorted({str(x['ff']) for x in guest_roam})} ({len(g_on)} of "
                                      f"{len(guest_roam)} with control), host ff {sorted({str(x['ff']) for x in host_roam})}")


def markers(gm, guest_samples) -> dict:
    """The calibration's markers, one per predicted red (PURE): leg -> (ok, detail)."""
    land = next((i for i, m in enumerate(gm) if LANDED in m), None)
    ons = [o for o in parse_on(gm) if o["field"] == DEST and land is not None and o["i"] > land]
    lever = [x for x in guest_samples if x["field"] == DEST and not x["ctl"] and x["why_not"] == WHY_LEVER]
    texts = [t for t in locked_texts(gm, LAST_LINE[0]) if FIRST_LINE[1] <= t <= LAST_LINE[1]]
    top = max(texts) if texts else None
    return {"D4": (not ons and bool(lever), f"ON lines on 450 {len(ons)}, control-off 450 samples with the lever's why_not {len(lever)}"),
            "D5": (_count_both(gm, RELEASE, RELEASE_PROGRESS) >= 1,
                   f"tail releases {_count(gm, RELEASE)} (progress clock {_count_both(gm, RELEASE, RELEASE_PROGRESS)}, cap "
                   f"{_count_both(gm, RELEASE, RELEASE_CAP)})"),
            "D6": (_count(gm, DROPPED) >= 1, f"drops as 450's {_count(gm, DROPPED)}"),
            "D7": (top is not None and top < LAST_LINE[1], f"the copy's highest Dagger line {top!r}"),
            "D8": (_count(gm, FOLLOWED) >= 1, f"follows to {HUB} {_count(gm, FOLLOWED)}")}


def beat_guard(gm_exit) -> tuple:
    """D-CAL-M's guest-side precondition (PURE), D1's span bound's twin: ``gm_exit`` the guest's lines up to the host's first 351
    sample (None: never seen). The predicted shape needs the 1x copy NOT yet past 450's wordless beat when the host leaves -- its
    highest Dagger line opened locked by then at most BEAT_LAST (161; none yet is fine) -- so the tail arms before the beat and the
    progress clock lets go across it. A copy already past it is a timing miss: the calibration's own void, named here."""
    if gm_exit is None:
        return False, "beat guard: the host's 351 landing never seen"
    texts = [t for t in locked_texts(gm_exit, LAST_LINE[0]) if FIRST_LINE[1] <= t <= LAST_LINE[1]]
    top = max(texts) if texts else None
    ok = top is None or top <= BEAT_LAST
    return ok, (f"beat guard: the copy's highest Dagger line at the host's 351 landing {top!r} (<= {BEAT_LAST} wanted"
                + ("" if ok else "; PAST the wordless beat: the calibration's timing missed, its verdicts void") + ")")


def judge_markers(lever_ok: bool, gm, guest_samples, gm_exit) -> tuple:
    """D-CAL-M (PURE): the lever read back, the beat guard (``gm_exit``: :func:`beat_guard`) and every predicted red's marker."""
    mk = markers(gm, guest_samples)
    beat_ok, beat_why = beat_guard(gm_exit)
    ok = lever_ok and beat_ok and all(mk[leg][0] for leg in PREDICTED_OFF)
    return ok, (f"lever {'read back off' if lever_ok else 'NOT TAKEN'}; {beat_why}; "
                + "; ".join(f"{leg}: {mk[leg][1]}" for leg in PREDICTED_OFF))


# --------------------------------------------------------------------------------------------- the run
class _DuoG:
    """cb.Ledger's ``g``: each row recorded on the duo (and the guest's report), its id the catalog's."""

    def __init__(self, d):
        self.d = d

    def check(self, ok, what, detail=""):
        return self.d.check(bool(ok), str(what), str(detail), role="guest", cid=str(what).split(":", 1)[0])

    def note(self, msg):
        self.d.note(str(msg))


def _msgs(d, role: str, at: int = 0) -> list:
    return [m for _t, _l, m in d.lines(role)[at:]]


def _settle_on(g, fid: int, timeout: float) -> bool:
    """On `fid` with control and no line open, paging any line on the way in."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        st = g.state
        if st.field_id == fid and st.control and not st.dialog_open:
            return True
        if st.field_id == fid and st.dialog_open:
            g.press("confirm", 2)
        g.wait_frames(6)
    return False


GATE_BYTES = (B_AVAIL, B_ROWS_LO, B_ROWS_HI)


def _gate(g) -> None:
    g.poke(B_AVAIL, 1)
    g.poke(B_ROWS_LO, ROWS & 0xFF)
    g.poke(B_ROWS_HI, (ROWS >> 8) & 0xFF)


def _gate_reads(st) -> tuple:
    return tuple(duo_mod.watched_byte(st, b) for b in GATE_BYTES)


def _ate_watch(d, host, guest, timeout: float) -> dict:
    """From the title's close: every distinct HOST and GUEST frame (:func:`read`, stamped with seconds since the close), the host's
    lines on 450 paged at PAGE_S, and the times each game first stood on 450 and then back on 351. Stops SETTLE_S after both are
    back, BACK_S after the host is back without the guest, or at ``timeout``."""
    out = {"host": [], "guest": [], "t_h450": None, "t_g450": None, "t_h351": None, "t_g351": None, "pages": 0,
           "g_lines_at_h351": None}             # the guest's log length at the host's first 351 sample (D-CAL-M's beat guard)
    t0 = time.time()
    deadline = t0 + timeout
    seen = {"host": None, "guest": None}
    key, since = None, 0.0
    while time.time() < deadline:
        now = time.time()
        last = {}
        for role, g in (("host", host), ("guest", guest)):
            st = g.state
            last[role] = st
            if st.frame == seen[role]:
                continue
            seen[role] = st.frame
            x = read(st, now - t0)
            out[role].append(x)
            r = "h" if role == "host" else "g"
            if x["field"] == DEST and out[f"t_{r}450"] is None:
                out[f"t_{r}450"] = x["t"]
            if x["field"] == HUB and out[f"t_{r}450"] is not None and out[f"t_{r}351"] is None:
                out[f"t_{r}351"] = x["t"]
                if role == "host":
                    out["g_lines_at_h351"] = len(d.lines("guest"))
        hs = last["host"]
        if hs.field_id == DEST and hs.dialog_open and hs.choice is None:
            k = (hs.text or "")[:80]
            if k != key:
                key, since = k, now
            elif now - since >= PAGE_S:
                host.press("confirm", 2)
                out["pages"] += 1
                since = time.time()
        else:
            key = None
        th, tg = out["t_h351"], out["t_g351"]
        if th is not None and tg is not None and now - t0 >= max(th, tg) + SETTLE_S:
            break
        if th is not None and tg is None and now - t0 >= th + BACK_S:
            break
        time.sleep(0.02)
    return out


def _roam(host, guest) -> tuple:
    """D9's samples: wait until the guest has had control on 351 for ROAM_SETTLE_S, then ROAM_S of both games."""
    deadline = time.time() + BACK_S
    since = None
    while time.time() < deadline:
        st = guest.state
        if st.field_id == HUB and st.control and not st.dialog_open:
            since = since or time.time()
            if time.time() - since >= ROAM_SETTLE_S:
                break
        else:
            since = None
            if st.field_id == HUB and st.dialog_open:
                guest.press("confirm", 2)
        time.sleep(0.05)
    out = {"host": [], "guest": []}
    if since is None:
        return out["guest"], out["host"]
    seen = {"host": None, "guest": None}
    t0 = time.time()
    while time.time() - t0 < ROAM_S:
        for role, g in (("host", host), ("guest", guest)):
            st = g.state
            if st.frame != seen[role]:
                seen[role] = st.frame
                out[role].append(read(st, time.time() - t0))
        time.sleep(0.02)
    return out["guest"], out["host"]


def run_duo(d) -> None:
    led = cb.Ledger(_DuoG(d), catalog(CAL_MODE), finals=(CAL_M_ID, CAL_ID) if CAL_MODE else (), width=1400)
    strict, d.strict = d.strict, False
    ctx = {"lever_ok": False, "gm": [], "guest": [], "gm_exit": None}
    try:
        _run(d, led, ctx)
    except HarnessError as err:
        d.note(f"the run raised: {str(err)[:400]}")
        led.close(f"not reached: the run raised ({str(err)[:200]})")
    finally:
        for step in (lambda: d.host.speedmode(False), lambda: cb.try_ns(d.guest, "speed", "act") if CAL_MODE else None):
            try:
                step()
            except Exception as err:                        # noqa: BLE001 - teardown must not mask the verdicts
                d.note(f"teardown step failed: {err}")
        try:
            d.note(f"logs archived: {d.archive('speed-mirror')}")
        except Exception as err:                            # noqa: BLE001 - teardown must not mask the verdicts
            d.note(f"archive failed: {err}")
        if CAL_MODE:
            led.close("not reached: the run ended before this check")
            ok, why = judge_markers(ctx["lever_ok"], ctx["gm"], ctx["guest"], ctx["gm_exit"])
            led.check(CAL_M_ID, ok, why)
            led.judge_calibration(CAL_ID, PREDICTED_OFF)
        led.close(final=True)
        d.strict = strict


def _run(d, led, ctx) -> None:
    host, guest = d.host, d.guest
    if not guest.state.coop_speed_mirror:
        d.note("the guest's engine publishes no `netsync.speed` (s162 or older): every mirror row is red by design")

    # ---- D0: both to 351, then the gate (351's own load clears it): the guest first, the host last, right before its press
    for g in (host, guest):
        g.watch(*(b * 8 + i for b in GATE_BYTES for i in range(8)))
    g0 = len(d.lines("guest"))
    host.poke(B_AVAIL, 1)                                # the instrument armed: a 0 after the load is then the load's own wipe
    armed = cb.poll(host, lambda s: _gate_reads(s)[0] == 1, 3.0, "the host's 238 poked before the warp") is not None
    host.warp(HUB, entrance=0, scenario=SCENARIO)
    ok_h = _settle_on(host, HUB, ARRIVE_S)
    ok_g = _settle_on(guest, HUB, ARRIVE_S)
    host_before = _gate_reads(host.state)[0]             # the instrument: 351's load wiped the host's 238 (else the gate proves nothing)
    _gate(guest)
    _gate(host)
    want = (1, ROWS & 0xFF, (ROWS >> 8) & 0xFF)
    rh = cb.poll(host, lambda s: _gate_reads(s) == want, 3.0, "the host's gate bytes")
    rg = cb.poll(guest, lambda s: _gate_reads(s) == want, 3.0, "the guest's gate bytes")
    loads = _count(_msgs(d, "guest", g0), f"Map: {HUB} ")
    led.check("D0", ok_h and ok_g and loads == 1 and armed and host_before == 0 and rh is not None and rg is not None,
              f"host on {host.state.field_id} ctl {host.state.control}, guest on {guest.state.field_id} ctl {guest.state.control}, "
              f"guest 'Map: {HUB}' x{loads}; host 238 poked to 1 before the warp: {'read back' if armed else 'NOT READ BACK'}, "
              f"after its load {host_before!r}; gate host {_gate_reads(host.state)} guest {_gate_reads(guest.state)}")
    if not (ok_h and ok_g):
        raise HarnessError("D0: the pair never settled on 351")

    # ---- the host at 3x (the real F1 path), section 10 on the wire, then the calibration lever on the GUEST
    h1 = len(d.lines("host"))
    host.speedmode(True)
    h351 = read(cb.poll(host, lambda x: cb.path(x, "netsync.speed.raw") is True, 3.0, "the host's booster") or host.state, 0.0)
    deadline = time.time() + WIRE_S                      # HostTick logs the edge in the host's next Update: wait for the line to land
    s, t, _n = host_booster(_msgs(d, "host", h1))
    while s is None and time.time() < deadline:
        time.sleep(0.15)
        s, t, _n = host_booster(_msgs(d, "host", h1))
    wire = []
    deadline = time.time() + WIRE_S
    while time.time() < deadline:
        wire.append(read(guest.state, 0.0))
        if wire[-1]["src"] == "wire" and wire[-1]["host_setting"] == s:
            break
        time.sleep(0.1)
    ok2, why2 = judge_wire(wire, s, t)
    led.check("D2", ok2, why2)
    if CAL_MODE:
        ok, why = cb.try_ns(guest, "speed", "off")
        back = cb.poll(guest, lambda x: cb.path(x, "netsync.speed.lever") == "off", 3.0, "the guest's off lever read back")
        ctx["lever_ok"] = ok and back is not None
        d.note(f"CALIBRATION: the guest's `speed off` {'taken' if ok else 'REFUSED: ' + why}, held to the end; predicted red "
               f"{', '.join(PREDICTED_OFF)}")

    # ---- the host's menu, its pick, its title (the s161 relay carries them to the guest)
    g1 = len(d.lines("guest"))
    host.press("select", 2)
    if cb.poll(host, lambda x: x.choice is not None, MENU_S, "the host's ATE menu") is None:
        raise HarnessError("the host's ATE menu never opened on 351 (the gate bytes?)")
    cb.poll(guest, lambda x: False, 1.5, "a moment for the guest's copy")   # the relay + the guest's serve
    host.choose_landed(PICK)
    title = cb.poll(host, lambda x: x.dialog_open and TITLE_WORD in (x.text or ""), 5.0, "the host's title card")
    if title is not None:
        host.wait_frames(25)
        host.press("confirm", 4)

    # ---- 450 at the host's 3x, the host paging at the owner's pace, until both are back on 351
    w = _ate_watch(d, host, guest, ATE_S)
    gm = _msgs(d, "guest", g1)
    ctx["gm"], ctx["guest"] = gm, w["guest"]
    at = w["g_lines_at_h351"]
    ctx["gm_exit"] = gm[:max(0, at - g1)] if at is not None else None
    ok1, why1 = judge_host(_msgs(d, "host", h1), h351, w["host"], w["t_h450"], w["t_h351"])
    led.check("D1", ok1, why1 + f"; pages {w['pages']}")
    for cid, (ok, why) in (("D3", judge_jump(gm)), ("D4", judge_on(gm, w["guest"], s)), ("D5", judge_hold(gm)),
                           ("D6", judge_drops(gm)), ("D7", judge_last(gm)), ("D8", judge_gap(gm, w["t_h351"], w["t_g351"]))):
        led.check(cid, ok, why)

    # ---- D9: the guest's own free roam back on 351, the host still at 3x
    groam, hroam = _roam(host, guest)
    ok9, why9 = judge_roam(groam, hroam, s)
    led.check("D9", ok9, why9)
