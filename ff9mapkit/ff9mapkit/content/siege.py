"""``[siege]`` -- the fort-condor tower-defense as ONE declarative block.

THE PRODUCTIZATION of the fort-condor arc (rungs 0-5, all in-game proven on
benches 30400/30410-30416): the 557-line bench script's ~40 authoring
decisions -- classes, waves, economy, positions -- expressed as a single TOML
table, with every mechanical emission the bench scripts hand-rolled generated
by this desugarer:

  * the ``[behavior]`` header (clock + counters) + the data-table wave clock
    (``[[behavior.table]]`` + ``[[behavior.schedule]]``),
  * the two rosters (``[[behavior.group]]`` raiders/allies) + the alive-only
    headcount scans feeding the war-room ``[[behavior.hud]]`` strip,
  * one ``[[behavior.pool]]`` per ally class (priced, request-flagged, the
    SELECT button poller on the first),
  * the base/raider/ally ``[[behavior.unit]]`` trees -- the die branches, the
    stance-as-radius:contact engage, the wave-gated march, THE PIN (a raider
    counter-engages whoever blocks it), the depot-commit swing,
  * THE WIN-CONDITION SHAPE (BEHAVIOR.md): endings only DETECT and raise a
    shared ``won`` flag; ONE payout branch pays exactly once,
  * the parked-seat ``[[npc]]`` blocks (pooled allies at the 9000-band -- the
    ARMOURY idiom) + raider stage npcs + the base npc,
  * the WAR COUNCIL ``[[choice]]`` with HONEST rows: each hire row is gated on
    its pool's ``hireable`` flag, resolved here by a build-time allocation
    pass (the bench's two-pass, internalized) -- a row you can SEE is a hire
    that will succeed.

Named ``[siege]`` because kit vocabulary names the GAME SHAPE (``[[gauge]]``,
``[[qte]]``, ``[[ferry]]``) -- "minigame" says nothing and "condor" is FFVII
provenance, not a product name.

Desugars at project load (the ``[[ferry]]`` pattern): everything downstream --
validate, the behavior compiler, collect_text, the layout probe -- sees plain
proven blocks. ``[siege]`` OWNS the field's ``[behavior]``; a field cannot
carry both.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field as _field

# the war-council parking zone + the ally seat park (both far off-play; the
# parked-choice / parked-seat idioms proven on the ARMOURY + CONDOR benches)
COUNCIL_ZONE = [[9000, 9000], [9200, 9000], [9200, 8800], [9000, 8800]]
SEAT_PARK_X, SEAT_PARK_Z, SEAT_PARK_STEP = 9000, 9000, 400
REQUEST_FLAG_BASE = 8840          # outside the blackboard band; safe band starts 8712
ALARM_RADIUS = 500
RAIDER_CONTACT = 210              # the proven melee reach for a marching raider
CHASE_CONTACT = 170               # a mobile ally's melee reach
COUNTER_IVL_PAD = 8               # a raider counter-swings a touch slower than its siege swing
DEATH_LINGER = 30                 # default frames a corpse holds after its death clip (the
                                  # fort-condor "instant vanish" complaint — see BEHAVIOR.md)
LOSS_STING_SUSTAIN = 55           # ~1s of held dispatch level so the sting rings CLEAR before
                                  # the loss_battle/cry (rung-C round 1: zero sustain gave the
                                  # sting one ~33ms frame before the battle took the audio)

DEFAULT_STIPEND_TEXT = ("The city fronts you {stipend} gil for the defense, kupo!"
                        "  Press Select anywhere to deploy troops where you stand.")
DEFAULT_WIN_TEXT = "WE HELD THE DEPOT!  The city pays in full."
DEFAULT_ROUT_TEXT = "THE RAID IS BROKEN — every raider is down!  The city pays in full."
DEFAULT_ALARM_TEXT = "They're through!  Protect the depot!"
DEFAULT_LOSS_TEXT = "The depot has fallen..."
DEFAULT_PROMPT = "WAR COUNCIL — deploy on this spot:"
DEFAULT_REPLY = "Deployed!  He holds this very spot."

_KEYS = {"timer", "warmup", "waves", "stipend", "win_gil", "win_item",
         "win_sfx", "win_flash", "loss_sfx", "hit_sfx", "loss_battle", "button",
         "council_prompt", "hud", "hud_text", "flag_base", "alarm_radius",
         "base", "ally", "raider",
         "text_stipend", "text_win", "text_rout", "text_alarm", "text_loss",
         "text_pace"}
_BASE_KEYS = {"name", "model", "pos", "hp", "face", "dialogue", "speed"}
_ALLY_KEYS = {"name", "label", "model", "count", "price", "hp", "stance",
              "radius", "contact", "damage", "interval", "speed", "reply",
              "anim", "death_anim", "linger"}
_RAIDER_KEYS = {"name", "model", "count", "wave", "hp", "damage", "interval",
                "speed", "speeds", "leash", "contact", "entrance", "route",
                "autoroute", "dialogue", "anim", "death_anim", "linger"}


class SiegeError(ValueError):
    pass


@dataclass(frozen=True)
class BaseSpec:
    model: str
    pos: tuple
    name: str = "base"
    hp: int = 24
    face: int | None = None
    dialogue: str = "This depot is everything we have.  Hold them off!"
    speed: int = 30


@dataclass(frozen=True)
class AllySpec:
    name: str
    label: str
    model: str
    count: int
    price: int
    stance: str                      # "chase" | "hold"
    radius: int
    hp: int = 4
    contact: int | None = None       # default: chase -> 170, hold -> radius-1
    damage: int = 1
    interval: int = 25
    speed: int = 60
    reply: str = DEFAULT_REPLY
    anim: object = None              # strike clip (gesture name or id) — own-clip law
    death_anim: object = None        # collapse clip
    linger: int = DEATH_LINGER

    def contact_r(self) -> int:
        if self.contact is not None:
            return self.contact
        return CHASE_CONTACT if self.stance == "chase" else self.radius - 1

    def unit_names(self) -> list:
        return [f"{self.name}{i}" for i in range(self.count)]


@dataclass(frozen=True)
class RaiderSpec:
    name: str
    model: str
    count: int
    wave: int                        # 1-based index into waves
    entrance: tuple                  # count [x, z] stage points
    route: tuple                     # the march lane (waypoints after the stage)
    hp: int = 3
    damage: int = 1
    interval: int = 30
    speeds: tuple = ()               # per-unit; filled from `speed` when omitted
    leash: int = 750
    contact: int = RAIDER_CONTACT
    autoroute: bool = True
    dialogue: str = "Kweeeh!"
    anim: object = None
    death_anim: object = None
    linger: int = DEATH_LINGER

    def unit_names(self) -> list:
        return [f"{self.name}{i}" for i in range(self.count)]


@dataclass(frozen=True)
class SiegeSpec:
    timer: int
    waves: tuple
    base: BaseSpec
    allies: tuple
    raiders: tuple
    warmup: int = 45
    stipend: int = 0
    win_gil: int = 0
    win_item: str | None = None
    win_sfx: int | None = None       # the purse fanfare cue (`ff9mapkit sfx-list` ids)
    win_flash: tuple | None = None   # the win screen-flash colour (true = white)
    loss_sfx: int | None = None      # the loss sting — rings BEFORE the cry/battle
    hit_sfx: int | None = None       # the impact cue every strike plays (both sides)
    loss_battle: int | None = None
    button: bool = True
    council_prompt: str = DEFAULT_PROMPT
    hud: bool = True
    hud_text: str | None = None
    flag_base: int = REQUEST_FLAG_BASE
    alarm_radius: int = ALARM_RADIUS
    text_stipend: str = DEFAULT_STIPEND_TEXT
    # the three ENDING texts take a string (one window — today's proven shape)
    # or a tuple of lines (STAGED text, paged at text_pace)
    text_win: "str | tuple" = DEFAULT_WIN_TEXT
    text_rout: "str | tuple" = DEFAULT_ROUT_TEXT
    text_alarm: str = DEFAULT_ALARM_TEXT
    text_loss: "str | tuple" = DEFAULT_LOSS_TEXT
    text_pace: int = 120             # frames each staged line holds before the next


def _need(d: dict, key, ctx: str):
    v = d.get(key)
    if v is None:
        raise SiegeError(f"{ctx}: needs {key}")
    return v


def _point(v, ctx: str) -> tuple:
    if not (isinstance(v, list) and len(v) == 2
            and all(isinstance(c, (int, float)) for c in v)):
        raise SiegeError(f"{ctx}: must be an [x, z] point")
    return (int(v[0]), int(v[1]))


def _ending_text(s: dict, key: str, default: str, ctx: str):
    """An ending text: a string (one window) or a list of lines -> a tuple
    (STAGED text — the list IS the request to stage)."""
    v = s.get(key)
    if v is None:
        return default
    if isinstance(v, str) and v:
        return v
    if isinstance(v, list) and v and all(isinstance(x, str) and x for x in v):
        return tuple(v)
    raise SiegeError(f"{ctx}: {key} must be a non-empty string or a non-empty "
                     f"list of non-empty strings (a list = staged text, paged "
                     f"at text_pace)")


def _lines(v) -> list:
    return list(v) if isinstance(v, tuple) else [v]


def from_raw(s: dict) -> SiegeSpec:
    ctx = "[siege]"
    extra = set(s) - _KEYS
    if extra:
        raise SiegeError(f"{ctx}: unknown key(s) {sorted(extra)}")
    timer = _need(s, "timer", ctx)
    if not isinstance(timer, int) or not 10 <= timer <= 3600:
        raise SiegeError(f"{ctx}: timer must be 10..3600 seconds")
    waves = _need(s, "waves", ctx)
    if not (isinstance(waves, list) and waves
            and all(isinstance(w, int) and 0 < w < timer for w in waves)
            and sorted(waves, reverse=True) == waves):
        raise SiegeError(f"{ctx}: waves must be DESCENDING start times in "
                         f"remaining-seconds, each 1..timer-1 (e.g. [55, 40, 20])")

    braw = _need(s, "base", ctx)
    bctx = "[siege.base]"
    extra = set(braw) - _BASE_KEYS
    if extra:
        raise SiegeError(f"{bctx}: unknown key(s) {sorted(extra)}")
    base = BaseSpec(model=str(_need(braw, "model", bctx)),
                    pos=_point(_need(braw, "pos", bctx), f"{bctx} pos"),
                    name=str(braw.get("name", "base")),
                    hp=int(braw.get("hp", 24)),
                    face=(int(braw["face"]) if braw.get("face") is not None else None),
                    dialogue=str(braw.get("dialogue", BaseSpec.dialogue)),
                    speed=int(braw.get("speed", 30)))

    allies = []
    for ai, a in enumerate(s.get("ally", []) or []):
        actx = f"[[siege.ally]] #{ai}"
        extra = set(a) - _ALLY_KEYS
        if extra:
            raise SiegeError(f"{actx}: unknown key(s) {sorted(extra)}")
        name = str(_need(a, "name", actx))
        stance = str(_need(a, "stance", actx))
        if stance not in ("chase", "hold"):
            raise SiegeError(f"{actx}: stance must be \"chase\" (pursues into melee) or "
                             f"\"hold\" (fires from its post, never moves)")
        count = _need(a, "count", actx)
        if not isinstance(count, int) or not 1 <= count <= 24:
            raise SiegeError(f"{actx}: count must be 1..24")
        radius = _need(a, "radius", actx)
        if not isinstance(radius, int) or radius < 100:
            raise SiegeError(f"{actx}: radius must be >= 100 world units")
        allies.append(AllySpec(
            name=name, label=str(_need(a, "label", actx)), model=str(_need(a, "model", actx)),
            count=count, price=int(_need(a, "price", actx)), stance=stance, radius=radius,
            hp=int(a.get("hp", 4)),
            contact=(int(a["contact"]) if a.get("contact") is not None else None),
            damage=int(a.get("damage", 1)), interval=int(a.get("interval", 25)),
            speed=int(a.get("speed", 60)), reply=str(a.get("reply", DEFAULT_REPLY)),
            anim=a.get("anim"), death_anim=a.get("death_anim"),
            linger=int(a.get("linger", DEATH_LINGER))))
    if not allies:
        raise SiegeError(f"{ctx}: needs at least one [[siege.ally]] class")

    raiders = []
    for ri, r in enumerate(s.get("raider", []) or []):
        rctx = f"[[siege.raider]] #{ri}"
        extra = set(r) - _RAIDER_KEYS
        if extra:
            raise SiegeError(f"{rctx}: unknown key(s) {sorted(extra)}")
        count = _need(r, "count", rctx)
        wave = _need(r, "wave", rctx)
        if not isinstance(wave, int) or not 1 <= wave <= len(waves):
            raise SiegeError(f"{rctx}: wave must be 1..{len(waves)} (an index into waves)")
        ent = _need(r, "entrance", rctx)
        if not (isinstance(ent, list) and len(ent) == count):
            raise SiegeError(f"{rctx}: entrance must list exactly count={count} "
                             f"[x, z] stage points (one per unit)")
        route = _need(r, "route", rctx)
        if not (isinstance(route, list) and route):
            raise SiegeError(f"{rctx}: route must be a non-empty [x, z] waypoint list "
                             f"(the march lane; each unit's own stage is prepended)")
        speeds = r.get("speeds")
        if speeds is not None:
            if not (isinstance(speeds, list) and len(speeds) == count
                    and all(isinstance(v, int) for v in speeds)):
                raise SiegeError(f"{rctx}: speeds must list count={count} ints")
        else:
            speeds = [int(r.get("speed", 50))] * count
        raiders.append(RaiderSpec(
            name=str(_need(r, "name", rctx)), model=str(_need(r, "model", rctx)),
            count=count, wave=wave,
            entrance=tuple(_point(p, f"{rctx} entrance") for p in ent),
            route=tuple(_point(p, f"{rctx} route") for p in route),
            hp=int(r.get("hp", 3)), damage=int(r.get("damage", 1)),
            interval=int(r.get("interval", 30)), speeds=tuple(speeds),
            leash=int(r.get("leash", 750)), contact=int(r.get("contact", RAIDER_CONTACT)),
            autoroute=bool(r.get("autoroute", True)),
            dialogue=str(r.get("dialogue", "Kweeeh!")),
            anim=r.get("anim"), death_anim=r.get("death_anim"),
            linger=int(r.get("linger", DEATH_LINGER))))
    if not raiders:
        raise SiegeError(f"{ctx}: needs at least one [[siege.raider]] block")

    names = [base.name] + [a.name for a in allies] + [r.name for r in raiders]
    if len(set(names)) != len(names):
        raise SiegeError(f"{ctx}: base/ally/raider names must be distinct (got {names})")
    ws = s.get("win_sfx")
    if ws is not None and (isinstance(ws, bool) or not isinstance(ws, int)
                           or not 0 <= ws <= 0xFFFF):
        raise SiegeError(f"{ctx}: win_sfx must be a sound id int 0..65535 "
                         f"(`ff9mapkit sfx-list`; 108 = the item-get jingle)")
    ls = s.get("loss_sfx")
    if ls is not None and (isinstance(ls, bool) or not isinstance(ls, int)
                           or not 0 <= ls <= 0xFFFF):
        raise SiegeError(f"{ctx}: loss_sfx must be a sound id int 0..65535 "
                         f"(`ff9mapkit sfx-list`)")
    hs = s.get("hit_sfx")
    if hs is not None and (isinstance(hs, bool) or not isinstance(hs, int)
                           or not 0 <= hs <= 0xFFFF):
        raise SiegeError(f"{ctx}: hit_sfx must be a sound id int 0..65535 "
                         f"(`ff9mapkit sfx-list`)")
    tp = s.get("text_pace", 120)
    if isinstance(tp, bool) or not isinstance(tp, int) or not 15 <= tp <= 255:
        raise SiegeError(f"{ctx}: text_pace must be an int 15..255 frames "
                         f"(the read time each staged line holds)")
    wf = s.get("win_flash")
    if wf is True:
        wf = (255, 255, 255)                     # win_flash = true -> white
    elif wf is not None:
        if (not isinstance(wf, list) or len(wf) != 3
                or not all(isinstance(c, int) and not isinstance(c, bool)
                           and 0 <= c <= 255 for c in wf)):
            raise SiegeError(f"{ctx}: win_flash takes true (white) or [r, g, b] "
                             f"ints 0..255")
        wf = tuple(wf)
    fb = s.get("flag_base", REQUEST_FLAG_BASE)
    if not isinstance(fb, int) or not 8712 <= fb <= 16300:
        raise SiegeError(f"{ctx}: flag_base must be a GLOB bit in the safe band "
                         f"(8712..16300; see ff9mapkit.flags)")
    if 9100 <= fb + 2 * len(allies) and fb <= 9599:
        raise SiegeError(f"{ctx}: flag_base band {fb}..{fb + 2 * len(allies) - 1} "
                         f"overlaps the kit's auto-flag lanes (9100..9599) -- "
                         f"pick a base outside them (the default {REQUEST_FLAG_BASE} is)")
    return SiegeSpec(
        timer=timer, waves=tuple(waves), base=base, allies=tuple(allies),
        raiders=tuple(raiders), warmup=int(s.get("warmup", 45)),
        stipend=int(s.get("stipend", 0)), win_gil=int(s.get("win_gil", 0)),
        win_item=(str(s["win_item"]) if s.get("win_item") else None),
        win_sfx=(int(ws) if ws is not None else None),
        win_flash=wf,
        loss_sfx=(int(ls) if ls is not None else None),
        hit_sfx=(int(hs) if hs is not None else None),
        loss_battle=(int(s["loss_battle"]) if s.get("loss_battle") is not None else None),
        button=bool(s.get("button", True)),
        council_prompt=str(s.get("council_prompt", DEFAULT_PROMPT)),
        hud=bool(s.get("hud", True)),
        hud_text=(str(s["hud_text"]) if s.get("hud_text") else None),
        flag_base=fb, alarm_radius=int(s.get("alarm_radius", ALARM_RADIUS)),
        text_stipend=str(s.get("text_stipend", DEFAULT_STIPEND_TEXT)),
        text_win=_ending_text(s, "text_win", DEFAULT_WIN_TEXT, ctx),
        text_rout=_ending_text(s, "text_rout", DEFAULT_ROUT_TEXT, ctx),
        text_alarm=str(s.get("text_alarm", DEFAULT_ALARM_TEXT)),
        text_loss=_ending_text(s, "text_loss", DEFAULT_LOSS_TEXT, ctx),
        text_pace=tp)


# ----------------------------------------------------------------- the emission
def _branch(do, when=None, once=None, raise_flags=None) -> dict:
    b: dict = {}
    if when:
        b["when"] = when
    b["do"] = do
    if once:
        b["once"] = once
    if raise_flags:
        b["raise_flags"] = raise_flags
    return b


def _theater(do: dict, *, anim=None, hit=None, death=None, linger=None) -> dict:
    """Fold the FIGHT THEATER onto a generated action — the strike clip + impact
    cue on a swing/engage, the collapse clip + corpse hold on a die. Absent dials
    add no keys at all, so a siege without theater emits the proven shapes
    byte-for-byte."""
    if anim is not None:
        do["anim"] = anim
    if hit is not None:
        do["hit_sfx"] = hit
    if death is not None:
        do["anim"] = death
        if linger:
            do["linger"] = int(linger)
    return do


def behavior_raw(spec: SiegeSpec) -> dict:
    """The generated ``[behavior]`` table -- the CONDOR round-4 shape, verbatim."""
    all_raiders = [n for r in spec.raiders for n in r.unit_names()]
    all_allies = [n for a in spec.allies for n in a.unit_names()]
    b: dict = {
        "warmup": spec.warmup, "timer": spec.timer,
        "counters": ["wave", "kills", "troops", "raiders_up"],
        "table": [{"name": "sched", "values": list(spec.waves)}],
        "schedule": [{"counter": "wave", "table": "sched"}],
        "group": [{"name": "raiders", "units": all_raiders},
                  {"name": "allies", "units": all_allies}],
        "scan": [{"name": "raid_up", "group": "raiders", "count": "raiders_up",
                  "alive_only": True},
                 {"name": "troop_up", "group": "allies", "count": "troops",
                  "alive_only": True}],
    }
    if spec.hud:
        # the war-room strip. MPOS 10,48: the COUNTDOWN TIMER owns the top-left
        # corner of the 320x224 grid (the round-4 playtest law).
        b["hud"] = [{"window": 6, "digits": [6, 2, 2, 2],
                     "values": ["gil", "troops", "raiders_up", f"hp:{spec.base.name}"],
                     "text": spec.hud_text or ("[MPOS=10,48]GIL [NUMB=0]  TROOPS [NUMB=1]"
                                               "  RAIDERS [NUMB=2]  DEPOT [NUMB=3]")}]
    pools = []
    for i, a in enumerate(spec.allies):
        p = {"name": a.name, "price": a.price, "request_flag": spec.flag_base + 2 * i}
        if spec.button and i == 0:
            p["button"] = True                    # ONE poller opens the shared council
        pools.append(p)
    b["pool"] = pools

    units = []
    # THE BASE -- loss, stipend, the detect-then-pay win shape, the alarm.
    bb: list = []
    bctx_die = {"die": True}
    bb.append(_branch(when=[{"flag": "lost"}], do=bctx_die))
    # ⚠ THE CLOCK-COUPLED BATTLE LAW (REDOUBT rung-D playtest, byte-proven in the
    # donor's own AI): B_SYSVAR[17] IS TimerUI.Time, and real battle scripts read
    # it — the Festival of the Hunt scenes (35 and the LB_E080x family, which a
    # 559-donor siege naturally borrows) run `B_SYSVAR[17] B_NOT -> RunBattleCode`
    # end, so they TERMINATE THEMSELVES the moment the countdown reads 0. The
    # ending's own theater (sting + staged text) takes seconds, so a late loss let
    # the clock reach 0:00 before the battle fired and the fight died on entry.
    # Freezing the clock FIRST — the very top of the loss lane, above every cue —
    # keeps the reading nonzero for whatever the ending fires.
    bb.append(_branch(when=[{"hp_le": 0}], once="clockstop",
                      do={"stop_timer": True}))
    if spec.loss_sfx is not None:
        # THE PRE-DETECT STING: an event-Once branch HOLDS selection until it
        # delivers, so seated between die-on-`lost` and the loss detect it is
        # guaranteed to ring BEFORE the detect raises `lost` (and before a
        # loss_battle transition suspends the field) and before the die branch
        # can terminate the base — the reveal-beat serialization, pointed the
        # other way. hp<=0 is monotonic (swings gate on target hp > 0), so the
        # stacked once-branches ride THE DRAINING-CONDITION LAW's exemption.
        # The sustain is the beat: order alone gave the sting ONE frame of air.
        bb.append(_branch(when=[{"hp_le": 0}], once="losssting",
                          do={"sfx": spec.loss_sfx,
                              "sustain": LOSS_STING_SUSTAIN}))
    ll, pace = _lines(spec.text_loss), spec.text_pace
    if spec.loss_battle is not None:
        # a STAGED text_loss pages pre-detect (the sting idiom scaled to text);
        # each stage's `delay` is the previous line's read time, and the LAST
        # line sustains so it rings before the battle takes the screen. A plain
        # string keeps today's shape byte-for-byte: the battle IS the loss text.
        if isinstance(spec.text_loss, tuple):
            for i, ln in enumerate(ll):
                stage = {"announce": ln}
                if i:
                    stage["delay"] = pace
                if i == len(ll) - 1:
                    stage["sustain"] = pace
                bb.append(_branch(when=[{"hp_le": 0}], once=f"losstext{i}",
                                  do=stage))
        bb.append(_branch(when=[{"hp_le": 0}], do={"battle": spec.loss_battle},
                          raise_flags=["lost"]))
    else:
        for i, ln in enumerate(ll[:-1]):
            stage = {"announce": ln}
            if i:
                stage["delay"] = pace
            bb.append(_branch(when=[{"hp_le": 0}], once=f"losstext{i}", do=stage))
        final = {"announce": ll[-1]}
        if len(ll) > 1:
            final["delay"] = pace
        bb.append(_branch(when=[{"hp_le": 0}], do=final,
                          once="losscry", raise_flags=["lost"]))
    if spec.stipend > 0:
        bb.append(_branch(when=[{"time_above": spec.timer - 5}], once="stipend",
                          do={"award": spec.stipend}))
        bb.append(_branch(when=[{"time_above": spec.timer - 6}], once="stiptext",
                          do={"announce": spec.text_stipend.format(stipend=spec.stipend)}))
    # THE WIN-CONDITION SHAPE: endings DETECT (raise `won` once, mutually
    # excluded via not_flag), ONE branch PAYS (the double-payout playtest law).
    # With win_flash, the detect branch CARRIES the wash and the cries move
    # below it — THE REVEAL BEAT (round-3 playtest: a window opening as the
    # white-out starts fights it): the wash's ~65-frame body holds the base's
    # dispatch level, and the request lane only fires on run==0 in LADDER
    # order — so the queued cry, purse, and jingle land on consecutive ticks
    # right at the release. The serialization IS the choreography.
    rout_when = [{"counter_ge": ["wave", len(spec.waves)]},
                 {"counter_eq": ["raiders_up", 0]}, {"not_flag": "won"}]
    win_when = [{"time_below": 1}, {"not_flag": "won"}]
    wl, rl = _lines(spec.text_win), _lines(spec.text_rout)
    # staging needs `routed` even without a flash — win stages gate on
    # won && !routed, so the rout detect must distinguish the endings
    staged_ends = isinstance(spec.text_win, tuple) or isinstance(spec.text_rout, tuple)
    # the ROUT also freezes the clock (it wins EARLY, so the countdown is still
    # running through its aftermath); the timer win is already at 0:00 by
    # definition, so it needs no stop.
    bb.append(_branch(when=[{"flag": "routed"}], once="routclock",
                      do={"stop_timer": True}))
    if spec.win_flash is not None:
        # win-lane only — a loss cue on the base would race its die-on-`lost`
        # TerminateEntry, so the loss keeps its own drama (the cry / the battle)
        bb.append(_branch(when=rout_when, once="routdet",
                          raise_flags=["won", "routed"],
                          do={"flash": list(spec.win_flash)}))
        bb.append(_branch(when=win_when, once="windet", raise_flags=["won"],
                          do={"flash": list(spec.win_flash)}))
        bb.append(_branch(when=[{"flag": "routed"}], once="routcry",
                          do={"announce": rl[0]}))
        bb.append(_branch(when=[{"flag": "won"}, {"not_flag": "routed"}],
                          once="wincry", do={"announce": wl[0]}))
    else:
        bb.append(_branch(when=rout_when, once="routcry",
                          raise_flags=(["won", "routed"] if staged_ends
                                       else ["won"]),
                          do={"announce": rl[0]}))
        bb.append(_branch(when=win_when, once="wincry", raise_flags=["won"],
                          do={"announce": wl[0]}))
    if spec.win_gil > 0 or spec.win_item:
        pay: dict = {"award": spec.win_gil}
        if spec.win_item:
            pay["item"] = spec.win_item
        bb.append(_branch(when=[{"flag": "won"}], once="paid", do=pay))
    if spec.win_sfx is not None:
        # the purse FANFARE — its own event-Once branch below the pay, gated on
        # the same `won` flag (flags don't drain, so the pay fires one tick and
        # the cue the next — THE DRAINING-CONDITION LAW's authoring shape)
        bb.append(_branch(when=[{"flag": "won"}], once="fanfare",
                          do={"sfx": spec.win_sfx}))
    # the STAGED AFTERMATH: extra ending lines page AFTER the proven
    # cry/purse/jingle beat — each stage's `delay` is the previous line's read
    # time, spent holding the dispatch level (the reveal-beat serialization)
    for i, ln in enumerate(rl[1:], 1):
        bb.append(_branch(when=[{"flag": "routed"}], once=f"routtext{i}",
                          do={"announce": ln, "delay": spec.text_pace}))
    for i, ln in enumerate(wl[1:], 1):
        bb.append(_branch(when=[{"flag": "won"}, {"not_flag": "routed"}],
                          once=f"wintext{i}",
                          do={"announce": ln, "delay": spec.text_pace}))
    bb.append(_branch(when=[{"any_near": [all_raiders, spec.alarm_radius]}],
                      once="alarm", do={"announce": spec.text_alarm}))
    bb.append(_branch(do={"hold": list(spec.base.pos)}))
    units.append({"npc": spec.base.name, "hp": spec.base.hp,
                  "speed": spec.base.speed, "branch": bb})

    # THE RAIDERS -- die-tally, depot-commit, THE PIN (counter-engage), the
    # wave-gated march down the lane, the stage hold.
    for r in spec.raiders:
        for i, uname in enumerate(r.unit_names()):
            stage = list(r.entrance[i])
            speed = r.speeds[i]
            rb = [
                _branch(when=[{"hp_le": 0}],
                        do=_theater({"die": "kills"}, death=r.death_anim,
                                    linger=r.linger)),
                _branch(when=[{"active": spec.base.name},
                              {"near": [spec.base.name, 300]}],
                        do=_theater({"swing_at": spec.base.name,
                                     "damage": r.damage, "interval": r.interval},
                                    anim=r.anim, hit=spec.hit_sfx)),
                _branch(do=_theater({"engage": "allies", "nearest": True,
                                     "radius": r.leash, "contact": r.contact,
                                     "damage": r.damage,
                                     "interval": r.interval + COUNTER_IVL_PAD,
                                     "speed": speed},
                                    anim=r.anim, hit=spec.hit_sfx)),
            ]
            march: dict = {"march": [stage] + [list(p) for p in r.route],
                           "arrive_r": 180, "speed": speed}
            if r.autoroute:
                march["route"] = "auto"
            rb.append(_branch(when=[{"counter_ge": ["wave", r.wave]}], do=march))
            rb.append(_branch(do={"hold": stage}))
            units.append({"npc": uname, "hp": r.hp, "speed": speed, "branch": rb})

    # THE ARMY -- pooled, stance as radius:contact, holding its hire post.
    for a in spec.allies:
        for uname in a.unit_names():
            units.append({
                "npc": uname, "hp": a.hp, "pooled": True, "pool": a.name,
                "speed": a.speed, "branch": [
                    _branch(when=[{"hp_le": 0}],
                            do=_theater({"die": True}, death=a.death_anim,
                                        linger=a.linger)),
                    _branch(do=_theater({"engage": "raiders", "nearest": True,
                                         "radius": a.radius,
                                         "contact": a.contact_r(),
                                         "damage": a.damage,
                                         "interval": a.interval,
                                         "speed": a.speed},
                                        anim=a.anim, hit=spec.hit_sfx)),
                    _branch(do={"hold_post": True}),
                ]})
    b["unit"] = units
    return b


def npc_blocks(spec: SiegeSpec) -> list:
    """The minted ``[[npc]]`` blocks: the base, raiders at their entrance
    stages, pooled allies at PARKED 9000-band seats (the ARMOURY idiom -- a
    pooled unit never boot-spawns; its settle happens far off-play before the
    hire lands it at the player's feet, keeping the layout probe clean)."""
    out = [{"name": spec.base.name, "model": spec.base.model,
            "pos": list(spec.base.pos), "dialogue": spec.base.dialogue,
            **({"face": spec.base.face} if spec.base.face is not None else {})}]
    for r in spec.raiders:
        for i, uname in enumerate(r.unit_names()):
            out.append({"name": uname, "model": r.model,
                        "pos": list(r.entrance[i]), "dialogue": r.dialogue})
    seat = 0
    for a in spec.allies:
        for uname in a.unit_names():
            out.append({"name": uname, "model": a.model,
                        "pos": [SEAT_PARK_X + SEAT_PARK_STEP * seat, SEAT_PARK_Z],
                        "dialogue": "Holding this ground!"})
            seat += 1
    return out


def council_choice(spec: SiegeSpec, hireable: dict) -> dict:
    """The WAR COUNCIL: a parked-zone menu whose hire rows are gated on the
    pools' hireable flags -- a row you can SEE is a hire that will succeed."""
    options = []
    for i, a in enumerate(spec.allies):
        options.append({"text": f"{a.label} — {a.price} gil", "reply": a.reply,
                        "set_flag": [spec.flag_base + 2 * i, 1],
                        "requires_flag": int(hireable[a.name])})
    options.append({"text": "Never mind."})
    return {"zone": [list(p) for p in COUNCIL_ZONE], "prompt": spec.council_prompt,
            "instant": True, "options": options}


def resolve_hireable(raw: dict) -> dict:
    """The pools' ``hireable`` blackboard flags, WITHOUT compiling: allocation
    is deterministic from the FieldBehavior constructor alone (the allocation
    contract), so a throwaway build on a route-stripped copy resolves them.
    (Stripped because ``route = "auto"`` demands a walkmesh at build; routing
    only splices WAYPOINTS into code and never moves blackboard allocation.)"""
    from . import behaviortoml as BT
    work = copy.deepcopy(raw)
    for u in work.get("behavior", {}).get("unit", []) or []:
        for br in u.get("branch", []) or []:
            if isinstance(br.get("do"), dict):
                br["do"].pop("route", None)
    all_units = [u["npc"] for u in work["behavior"]["unit"]]
    txids = {(ui, bi): 900 + 10 * ui + bi for ui, bi, _ in BT.announce_lines(work)}
    txids.update({("hud", hi): 890 + hi for hi, _h in BT.hud_lines(work)})
    fb = BT.build(work, npc_slots={n: i + 2 for i, n in enumerate(all_units)},
                  npc_txids_by_name={n.get("name"): 0 for n in work.get("npc", [])},
                  behavior_txids=txids)
    return dict(fb.pool_hireable)


def desugar(raw: dict) -> None:
    """Expand ``[siege]`` into the proven blocks, in place. Malformed input is
    left for :func:`ff9mapkit.build.validate` to report (the ferry pattern);
    a field already carrying ``[behavior]`` is also left untouched (validate
    refuses the combination -- ``[siege]`` owns the behavior table)."""
    s = raw.get("siege")
    if not s:
        return
    if raw.get("behavior"):
        raw["_siege_conflict"] = True             # validate() reports; nothing emitted
        return
    try:
        spec = from_raw(s)
    except SiegeError:
        return                                    # validate() re-parses and reports
    raw.setdefault("npc", [])
    raw["npc"] += npc_blocks(spec)
    raw["behavior"] = behavior_raw(spec)
    try:
        hire = resolve_hireable(raw)
    except Exception as e:                        # a generated-raw bug must not crash load
        raw["_siege_error"] = f"hireable-flag resolution failed: {e}"
        return
    raw.setdefault("choice", [])
    raw["choice"].append(council_choice(spec, hire))
