"""RUNG 1 of the sine kit -- the kit's `[[prop]] motion`, in-game, against the kit's own predictor.

    py studies/sine-kit/sine1_bench.py deploy
    py tools/play.py studies/sine-kit/rung1_motion.py --label sine-rung1

The bench (field 30946, bench/sine1.field.toml) authors seven movers and a static control ONLY with the kit; the build
seats and arms the motion daemon. sine1_bench.py seats a study-side OBSERVER right after the daemon (its own tick
counter K; the FIRST band read once after the daemon's tick 0; Global Int16 mirrors of the movers' published transform
every tick, keyed by M_K). Every sample therefore carries its own tick, and content.motion.pose(K) says EXACTLY what
the engine must hold -- the predictor the build report prints is the oracle, never re-derived here. 30947 is the CAL
arm: the same bytes with the daemon armed FIRST in Main_Init (the shape THE ORDER LAW refuses).

PRE  P0 30946 and 30947 are each served by FF9CustomMap alone
     P1 DERIVE-FORWARD: rebuilding each arm from the toml with this kit and re-applying the deterministic observer patch
        == the deployed bytes, in every language; the daemon entry == motion.entry_bytes(the bench's movers)
     P2 motion.arming_problems == [] on 30946 and names THE ORDER LAW on 30947; the observer is armed after every
        prop on both; no yielding op between the daemon's and the observer's InitCode (K == the daemon's tick n)
     P3 the DEPLOYED daemon, run in tests/_ebengine.MotionEngine for two cycles, == motion.path for every mover
C0   COVERAGE: W1 holds >= 150 distinct K spanning > 256 ticks and all 16 phase bins of B's 256-tick bob
C1   EXACT: every mirror == pose(K) (x, b, z, facing byte) in every 30946 window -- worst error 0
C2   STILL: D and G (no turn) keep their spawn facing; the control H == its spawn (x, 0, z, 64) in every sample
     (on K 0 its y is still CreateObject's 32768 placeholder -- sine1_bench.expected predicts it)
C3   PHASE LOCK: B is A's antipode in every sample (one shared clock)
C4   FIRST FRAME / THE ORDER LAW: the FIRST band == pose(0) -- tick 0 landed after CreateObject, before any later
     entry ran (the band is poked to a sentinel first, so the read needs a fresh write)
C5   INT26 EDGE: G (r 8191) is exact in >= 5 samples whose sine intermediate is >= 4000 * 8191 (~32.8 M)
C6   CADENCE: K per wall-second over W1 within [26, 34] * FieldTPS / 30 -- FieldTPS read from the live Memoria.ini
C7   HORIZON: W2 samples with K > 1024 are exact (every clock has wrapped; P 90 at least 11 times)
C8   RE-ENTRY: V increments, FIRST == pose(0) again (after a sentinel), the first K seen is <= 10, >= 50 exact samples
C-WALK  the player walks west from the spawn straight through D's line (walk-through) and D stays exact meanwhile
CAL  30947: FIRST == the SPAWN pose exactly (the check CAN fail), samples with K >= 1 are exact (a pre-Init 0xAD
     neither throws nor sticks)
C9   BATTLE (LAST -- a lost fight must not cost the rest): V unchanged, the FIRST band still holds the sentinel poked
     before the fight (Main_Init did not re-run), K continued past the last pre-battle K, >= 50 exact samples after
NC-THROW  no NullReference / InvalidCast / IndexOutOfRange through the event engine or the evaluator since the mark
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "ff9mapkit"))
sys.path.insert(0, str(HERE))
import sine1_bench as SB  # noqa: E402
from ff9mapkit.config import LANGS  # noqa: E402
from ff9mapkit.content import motion as M  # noqa: E402
from harness import HarnessError  # noqa: E402

THROWS = {"NullReferenceException", "InvalidCastException", "IndexOutOfRangeException"}
BATTLE_SCENE = 67                                      # the bench's [encounter] scene (freq 0: never random)
WALK_FRAMES = 60                                       # a leg that reaches the west wall when unblocked
D_WEST = SB.SPAWN["D"][0]                              # D's shuttle spans x -1000 .. -302 on z -1600


# ------------------------------------------------------------------- helpers
def _field_tps(game: Path) -> tuple:
    """(Memoria.ini [Graphics] FieldTPS, where it came from) -- the daemon ticks once per field logic tick."""
    ini = Path(game) / "Memoria.ini"
    try:
        section = None
        for line in ini.read_text(encoding="utf-8", errors="replace").splitlines():
            s = line.strip()
            if not s or s.startswith(";"):
                continue
            if s.startswith("[") and s.endswith("]"):
                section = s[1:-1].strip()
            elif section == "Graphics" and "=" in s:
                k, v = (x.strip() for x in s.split("=", 1))
                if k == "FieldTPS":
                    return int(v), str(ini)
    except (OSError, ValueError):
        pass
    return M.TICKS_PER_SECOND, "the default (Memoria.ini unreadable or silent)"


def _try(fn, *a, **kw):
    """(value, None) or (None, the error) -- the bench helpers refuse with SystemExit, which must not end the run."""
    try:
        return fn(*a, **kw), None
    except (SystemExit, Exception) as e:                  # noqa: BLE001 -- recorded as a failed check
        return None, f"{type(e).__name__}: {e}"


def _watch(g, offsets) -> None:
    g.unwatch()
    b = SB.bits(offsets)
    for i in range(0, len(b), 128):                        # the agent APPENDS to its watch set
        g.watch(*b[i:i + 128])


def _rolling(g) -> dict:
    _watch(g, SB.ROLLING_OFFS)
    st = g.wait_for(lambda s: SB.read_rolling(s) is not None, timeout=15, what="the rolling mirrors published")
    return SB.read_rolling(st)


def _first_band(g) -> dict:
    """Switch the watch to the FIRST band (it persists for the visit), read it, and switch back."""
    _watch(g, SB.FIRST_OFFS)
    st = g.wait_for(lambda s: SB.read_first(s) is not None, timeout=15, what="the FIRST band published")
    got = SB.read_first(st)
    _rolling(g)
    return got


def _poke16(g, off: int, v: int) -> None:
    g.poke(off, v & 0xFF)
    g.poke(off + 1, (v >> 8) & 0xFF)


def _poke_sentinel(g) -> None:
    for k in SB.FIRST:
        _poke16(g, SB.FIRST_OFF[k], SB.SENTINEL)


def _enter(g, fid: int, v_before: int) -> tuple:
    """Warp to ``fid`` with the rolling watch ON and keep every sample from the moment the observer's prelude ran (V
    advanced). g.warp would block through the entry settle (~50+ ticks) and lose the first K. The registration guard
    g.warp carries is repeated here: a warp to an unregistered id black-screens the game."""
    if fid not in g.registered_fields()[0]:
        raise HarnessError(f"field {fid} is not registered -- deploy it (sine1_bench.py deploy) and relaunch")
    v_new = SB.s16(v_before + 1)
    got: dict = {}
    first: list = []

    def rec(s) -> bool:
        m = SB.read_rolling(s)
        if m is not None and s.field_id == fid and m["V"] == v_new:
            if not first:
                first.append(m["K"])
            got.setdefault(m["K"], dict(m, t=time.time(), frame=s.frame, px=s.player_x, pz=s.player_z))
        return (bool(first) and s.ui_state == "FieldHUD" and s.field_id == fid and s.control and not s.fading
                and s.player_x is not None)

    g.send(f"warp {fid} -1 -1")
    g.wait_for(rec, timeout=90, what=f"field {fid}: the observer's prelude (V -> {v_new}) and player control")
    return first[0], got


def _collect(g, seconds: float, fid: int, v: int | None, into: dict | None = None) -> dict:
    """Every distinct K seen on ``fid`` (in visit ``v``, or any visit when None) with its mirrors."""
    got = {} if into is None else into
    deadline = time.time() + seconds
    last = None
    while time.time() < deadline:
        st = g.state
        if st.frame != last:
            last = st.frame
            m = SB.read_rolling(st)
            if m is not None and st.field_id == fid and (v is None or m["V"] == v):
                got.setdefault(m["K"], dict(m, t=time.time(), frame=st.frame, px=st.player_x, pz=st.player_z))
        time.sleep(0.005)
    return got


def _err(key, got: int, want: int) -> int:
    if key[1] == 3:
        d = (got - want) % 256
        return min(d, 256 - d)
    return abs(got - want)


def _exact(samples: dict, labs=None, kmin: int | None = None) -> tuple:
    """(exact, total, worst error, first mismatches) over ``samples`` (optionally only props ``labs``, K >= kmin)."""
    n = ok = worst = 0
    bad = []
    for k in sorted(samples):
        if kmin is not None and k < kmin:
            continue
        errs = SB.sample_errors(samples[k], labs)
        n += 1
        ok += not errs
        if errs:
            worst = max(worst, max(_err(key, g_, w) for key, (g_, w) in errs.items()))
            if len(bad) < 4:
                bad.append((k, {f"{a}{b}": v for (a, b), v in list(errs.items())[:6]}))
    return ok, n, worst, bad


def _stats(name: str, samples: dict, **kw) -> tuple:
    ok, n, worst, bad = _exact(samples, **kw)
    ks = sorted(samples)
    print(f"[sine-rung1] {name}: {n} samples K {ks[:1]}..{ks[-1:]}, exact {ok}/{n}, worst {worst}"
          + (f", e.g. {bad}" if bad else ""))
    return ok, n, worst, bad


def _first_check(got: dict | None, want: dict) -> list:
    if got is None:
        return ["not read"]
    return [f"{a}{b}: {got[(a, b)]} != {want[(a, b)]}" for a, b in SB.FIRST if got[(a, b)] != want[(a, b)]]


# ------------------------------------------------------------------- preflight (offline)
def _preflight(g) -> bool:
    game = Path(g.game_path)
    registered = True
    for fid in SB.ARMS:
        folders = [p.parent.name for p in game.glob("*/DictionaryPatch.txt")
                   if re.search(rf"FieldScene {fid}\b", p.read_text(encoding="utf-8", errors="replace"))]
        registered &= g.check(folders == [SB.MOD_FOLDER], f"P0: {fid} is served by {SB.MOD_FOLDER} alone",
                              str(folders))
    live = {fid: {L: SB.live_path(fid, L, game).read_bytes() for L in LANGS if SB.live_path(fid, L, game).exists()}
            for fid in SB.ARMS}
    patched = all(live[fid] and all(SB.is_patched(b) for b in live[fid].values()) for fid in SB.ARMS)
    g.check(patched, "P1: every deployed language .eb of both arms carries the observer",
            str({fid: {L: SB.is_patched(b) for L, b in live[fid].items()} for fid in SB.ARMS}))
    for fid, (name, cal) in SB.ARMS.items():
        derived, err = _try(SB.derive, fid)
        same = sorted(L for L in (derived or {}) if live[fid].get(L) == derived[L])
        g.check(err is None and bool(derived) and same == sorted(derived) == sorted(live[fid]),
                f"P1: DERIVE-FORWARD -- {fid} rebuilt from the toml + the same observer patch == the deployed bytes "
                f"in every language", err or f"derived {sorted(derived or {})} live {sorted(live[fid])} same {same}")
        slots = {}
        for L, b in live[fid].items():
            uids, e1 = _try(SB.prop_uids, b)
            slots[L] = _try(SB.daemon_slot, b, uids)[0] if uids else e1
        g.check(bool(slots) and all(isinstance(s, int) for s in slots.values()),
                f"P1: {fid}'s daemon entry == motion.entry_bytes(the bench's movers) in every language", str(slots))
    for fid, (name, cal) in SB.ARMS.items():
        verdicts = {}
        for L, b in live[fid].items():
            uids, err = _try(SB.prop_uids, b)
            if err:
                verdicts[L] = err
                continue
            ds, err = _try(SB.daemon_slot, b, uids)
            os_ = SB.observer_slot(b, uids) if not err else None
            if err or os_ is None:
                verdicts[L] = err or "no observer"
                continue
            verdicts[L] = (M.arming_problems(b, ds, [uids[lab] for lab in SB.MOVERS]),
                           M.arming_problems(b, os_, list(uids.values())), SB.between_problems(b, ds, os_))
        tup = bool(verdicts) and all(isinstance(v, tuple) for v in verdicts.values())
        g.check(tup and all(not v[1] and not v[2] for v in verdicts.values()),
                f"P2: {fid} -- the observer is armed after every prop and no op between the daemon's and the "
                f"observer's InitCode can yield (K == the daemon's tick n)",
                str({L: v[1:] if isinstance(v, tuple) else v for L, v in verdicts.items()})[:400])
        if cal:
            g.check(tup and all(any("armed before" in p for p in v[0]) for v in verdicts.values()),
                    f"P2: THE ORDER LAW refuses the deployed CAL arm {fid} (the daemon armed before the movers) -- the "
                    f"law's verdict predicts the in-game difference",
                    str({L: v[0][:1] if isinstance(v, tuple) else v for L, v in verdicts.items()})[:400])
        else:
            g.check(tup and all(v[0] == [] for v in verdicts.values()),
                    f"P2: THE ORDER LAW holds on the deployed {fid} (motion.arming_problems == [])",
                    str({L: v[0] if isinstance(v, tuple) else v for L, v in verdicts.items()})[:400])
    for fid in SB.ARMS:
        runs = {L: _try(SB.engine_mismatches, b) for L, b in sorted(live[fid].items())}
        ok = bool(runs) and all(err is None and not r[1] for r, err in runs.values())
        g.check(ok, f"P3: {fid}'s DEPLOYED daemon in the MotionEngine == motion.path for every mover (two cycles of "
                f"the slowest), every language",
                str({L: (r[0], r[1][:2]) if r else err for L, (r, err) in runs.items()})[:400])
    return registered and patched


# ------------------------------------------------------------------- the run
def run(g) -> None:
    if not _preflight(g):
        print("[sine-rung1] preflight: the bench is not deployed/registered as required -- not launching the run")
        g.quit()
        return
    tps, tps_src = _field_tps(Path(g.game_path))
    lo, hi = tps * 26 / 30, tps * 34 / 30
    print(f"[sine-rung1] FieldTPS {tps} ({tps_src}) -> C6 window [{lo:.1f}, {hi:.1f}] ticks/s")
    g.note("sine kit rung 1")
    g.newgame()
    mark = g.log_mark()
    g.state_every(1)
    v0 = _rolling(g)["V"]
    _poke_sentinel(g)
    k_first, entry = _enter(g, SB.FIELD_ID, v0)
    v1 = SB.s16(v0 + 1)
    first = _first_band(g)
    print(f"[sine-rung1] entry: V {v0} -> {first['V']}, first K {k_first}; FIRST {first}")
    g.check(first["V"] == v1 and not _first_check(first, SB.FIRST_POSE0),
            "C4: FIRST FRAME -- the FIRST band == pose(0) (A.z, A.f, B.b, B.z, C.z, F.f, G.z): tick 0 landed after "
            "CreateObject and before any later entry ran (THE ORDER LAW; the band held a sentinel before)",
            f"V {first['V']} (want {v1}); {_first_check(first, SB.FIRST_POSE0)}")

    g.shot("1-orbit")
    w1 = _collect(g, 20.0, SB.FIELD_ID, v1)
    g.shot("2-later")
    ks = sorted(w1)
    span = ks[-1] - ks[0] if ks else 0
    bins = {(k % 256) // 16 for k in ks}
    g.check(len(ks) >= 150 and span > 256 and len(bins) == 16,
            "C0: COVERAGE -- W1 holds >= 150 distinct K spanning > 256 ticks, all 16 phase bins of B's 256-tick bob",
            f"{len(ks)} values, span {span}, bins {len(bins)}/16")
    rate = tpf = None
    if len(ks) >= 2 and w1[ks[-1]]["t"] > w1[ks[0]]["t"]:
        rate = span / (w1[ks[-1]]["t"] - w1[ks[0]]["t"])
        if w1[ks[-1]]["frame"] != w1[ks[0]]["frame"]:
            tpf = span / (w1[ks[-1]]["frame"] - w1[ks[0]]["frame"])
    print(f"[sine-rung1] cadence: {rate} ticks/s, {tpf} ticks per published frame (rung 0 measured 0.50)")
    g.check(rate is not None and lo <= rate <= hi,
            f"C6: CADENCE -- K per wall-second over W1 in [{lo:.1f}, {hi:.1f}] (FieldTPS {tps}: a Wait(1) daemon "
            f"ticks once per field logic tick; High Speed Mode would scale it)",
            f"{rate} ticks/s over {span} ticks; {tpf} ticks/frame")

    # C-WALK: west from the spawn, straight through D's shuttle line
    s0 = g.state
    g.hold("left", WALK_FRAMES)
    walk = _collect(g, 2.5, SB.FIELD_ID, v1)
    s1 = g.state
    moved = (s0.player_x - s1.player_x) if None not in (s0.player_x, s1.player_x) else None
    dok, dn, dworst, dbad = _stats("C-WALK (D only)", walk, labs=("D",))
    g.check(moved is not None and moved >= 500 and s1.player_x < D_WEST - 40 and dn >= 5 and dok == dn,
            f"C-WALK: the player walks west >= 500 u from the spawn and ends west of D's whole line (x < {D_WEST - 40}"
            f": through the walk-through shuttle, whichever way it was moving), and D stays exact meanwhile",
            f"moved {moved} ({s0.player_x} -> {s1.player_x}, z {s1.player_z}); D exact {dok}/{dn} worst {dworst} {dbad}")

    g.wait_for(lambda s: (m := SB.read_rolling(s)) is not None and m["V"] == v1 and m["K"] > 1024,
               timeout=120, what="K > 1024 (every clock wrapped)")
    w2 = _collect(g, 10.0, SB.FIELD_ID, v1)
    visit1 = {**entry, **w1, **walk, **w2}
    for name, s in (("entry", entry), ("W1", w1), ("walk", walk), ("W2", w2)):
        _stats(name, s)
    ok, n, worst, bad = _exact(visit1)
    g.check(n > 0 and ok == n and all(len(s) > 0 for s in (w1, w2)),
            "C1: EXACT -- every mover's mirrors == pose(K) (x, b, z, facing byte) in every 30946 window, worst 0",
            f"exact {ok}/{n}, worst {worst}, e.g. {bad}")
    still = [(k, {key: v for key, v in SB.sample_errors(visit1[k], ("D", "G", "H")).items() if key[0] == "H"
                  or key[1] == 3}) for k in sorted(visit1)]
    still = [(k, e) for k, e in still if e]
    g.check(n > 0 and not still,
            "C2: STILL -- D and G (no turn) keep their spawn facing and the control H == its spawn (x, 0, z, 64) in "
            "every sample, y the CreateObject placeholder on K 0 (the daemon writes only what a mover asks for)", str(still[:4]))
    cx, cz = SB.SPECS["A"].pos
    anti = [k for k, m in visit1.items() if abs((m[("A", 0)] - cx) + (m[("B", 0)] - cx)) > 1
            or abs((m[("A", 2)] - cz) + (m[("B", 2)] - cz)) > 1]
    g.check(n > 0 and not anti, "C3: PHASE LOCK -- B is A's antipode in every sample (one shared 128-tick clock)",
            str(anti[:5]))
    gs = SB.SPECS["G"]
    big = M.cdiv(4000 * gs.radius, 4096)
    edge = [k for k, m in visit1.items()
            if max(abs(SB.expected("G", 0, k) - gs.pos[0]), abs(SB.expected("G", 2, k) - gs.pos[1])) >= big]
    edge_ok = [k for k in edge if not SB.sample_errors(visit1[k], ("G",))]
    g.check(len(edge_ok) >= 5 and len(edge_ok) == len(edge),
            f"C5: INT26 EDGE -- G (r {gs.radius}) exact in >= 5 samples whose sine intermediate is >= 4000 * "
            f"{gs.radius} (~{4000 * gs.radius / 1e6:.1f} M, inside 2^25)", f"exact {len(edge_ok)}/{len(edge)}")
    horizon = {k: m for k, m in w2.items() if k > 1024}
    ok, n2, worst, bad = _exact(horizon)
    g.check(n2 >= 50 and ok == n2, "C7: HORIZON -- W2 samples with K > 1024 are exact (every clock wrapped; P 90 "
            "at least 11 times)", f"exact {ok}/{n2}, worst {worst}, e.g. {bad}")

    # C8: re-entry (the ~ Reload path)
    v2 = SB.s16(v1 + 1)
    try:
        _poke_sentinel(g)
        k8, e8 = _enter(g, SB.FIELD_ID, v1)
        f8 = _first_band(g)
        s8 = _collect(g, 10.0, SB.FIELD_ID, v2, into=dict(e8))
        ok, n8, worst, bad = _stats("C8", s8)
        g.check(f8["V"] == v2 and not _first_check(f8, SB.FIRST_POSE0) and k8 <= 10 and n8 >= 50 and ok == n8,
                "C8: RE-ENTRY -- V increments, the FIRST band == pose(0) again (it held a sentinel), the first K seen "
                "is <= 10, and >= 50 new samples are exact",
                f"V {f8['V']} (want {v2}); FIRST {_first_check(f8, SB.FIRST_POSE0)}; first K {k8}; exact {ok}/{n8} "
                f"worst {worst} {bad}")
    except HarnessError as err:
        g.check(False, "C8: RE-ENTRY", f"the phase raised: {err}")

    # CAL: 30947, the daemon armed FIRST -- the FIRST check must fail there, and nothing may throw or stick
    try:
        _poke_sentinel(g)
        v_now = _rolling(g)["V"]
        kc, ec = _enter(g, SB.CAL_ID, v_now)
        v3 = SB.s16(v_now + 1)
        fc = _first_band(g)
        sc = _collect(g, 10.0, SB.CAL_ID, v3, into=dict(ec))
        g.shot("4-cal")
        ok, nc, worst, bad = _stats("CAL (K >= 1)", sc, kmin=1)
        g.check(fc["V"] == v3 and not _first_check(fc, SB.FIRST_SPAWN) and nc >= 50 and ok == nc,
                "CAL: on 30947 (daemon armed before the movers) the FIRST band == the SPAWN pose exactly -- CreateObject "
                "overwrote tick 0, so the FIRST check CAN fail -- and every sample with K >= 1 is exact (the pre-Init "
                "0xAD neither threw nor stuck)",
                f"V {fc['V']} (want {v3}); FIRST vs spawn {_first_check(fc, SB.FIRST_SPAWN)} (vs pose(0) "
                f"{_first_check(fc, SB.FIRST_POSE0)}); first K {kc}; exact {ok}/{nc} worst {worst} {bad}")
    except HarnessError as err:
        g.check(False, "CAL", f"the phase raised: {err}")

    # C9 LAST: a battle round trip on 30946 (a failed flee + a lost fight is Game Over -- it must cost nothing else)
    try:
        v_now = _rolling(g)["V"]
        _k, e9 = _enter(g, SB.FIELD_ID, v_now)
        v4 = SB.s16(v_now + 1)
        pre = _collect(g, 6.0, SB.FIELD_ID, v4, into=dict(e9))
        _poke_sentinel(g)                                  # NOW only a Main_Init re-run could overwrite it
        last_pre = max(pre) if pre else None
        g.start_battle(BATTLE_SCENE)
        escaped, how = False, []
        for _attempt in range(3):
            try:
                escaped = g.flee(timeout=30)
            except HarnessError as err:
                how.append(f"flee refused: {err}")
                break
            how.append(f"flee -> {escaped}")
            if escaped or not g.state.in_battle:
                break
        if not escaped and g.state.in_battle:
            how.append(f"fight -> {g.fight(finish=False)}")
        how.append(f"leave -> {g.leave_battle()}")
        g.wait_for(lambda s: s.ui_state == "FieldHUD" and s.field_id == SB.FIELD_ID and not s.in_battle,
                   timeout=90, what="back on 30946 after the battle")
        post = _collect(g, 10.0, SB.FIELD_ID, None)
        fb = _first_band(g)
        g.shot("3-after-battle")
        vs = sorted({m["V"] for m in post.values()})
        after = {k: m for k, m in post.items() if last_pre is not None and k > last_pre}
        ok, n9, worst, bad = _stats("C9 post-battle", after)
        still_sentinel = all(fb[k] == SB.SENTINEL for k in SB.FIRST)
        print(f"[sine-rung1] C9: {how}; V pre {v4} post {vs} / band {fb['V']}; last pre K {last_pre}, post K "
              f"{min(post, default=None)}..{max(post, default=None)}")
        g.check(vs == [v4] and fb["V"] == v4 and still_sentinel and bool(post) and last_pre is not None
                and min(post) >= last_pre and n9 >= 50 and ok == n9,
                "C9: BATTLE -- V unchanged and the FIRST band still holds the sentinel poked before the fight (Main_Init "
                "did not re-run; Main_Reinit resumed), K continued past the last pre-battle K (the Instance locals "
                "survived the context copy, and the daemon's phase with them), >= 50 post-battle samples exact",
                f"{how}; V {vs}/{fb['V']} (want {v4}); band sentinel {still_sentinel}; K pre {last_pre} post "
                f"{min(post, default=None)}; exact {ok}/{n9} worst {worst} {bad}")
    except HarnessError as err:
        g.check(False, "C9: BATTLE", f"the phase raised: {err}")

    every = g.exceptions_since(mark)
    ours = [e for e in every if e.name in THROWS and any(k in fr for fr in e.trace for k in ("EventEngine", "EBin"))]
    print(f"[sine-rung1] exceptions since the mark: {len(every)}")
    g.check(not ours, "NC-THROW: no NullReference / InvalidCast / IndexOutOfRange through the event engine or the "
            "evaluator -- across the entries, the walk, the re-entry, CAL and the battle",
            str([(e.name, e.where) for e in ours[:5]]))
    g.quit()
