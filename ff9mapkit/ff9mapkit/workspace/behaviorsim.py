"""The offline tick-stepper (the behavior GUI charter's rung E1) — a pure-Python
interpreter of the DOCUMENTED tree semantics, stepping simulated positions so the tab
can scrub a timeline: watch selection sweep the ladder rows, watch units move on the
stage, and catch the priority/starvation authoring family before a playtest.

AN INSTRUMENT, NOT PROOF. Offline ≠ in-game — and this module keeps a ledger
(:attr:`Sim.notes`) of every approximation it makes, built at construction so the GUI
can put the honesty on its face. The big ones: walks are STRAIGHT LINES (no walkmesh,
no collision — the Sweep lane owns wall truth), pooled units stay dormant (no hire
economy), ``battle`` logs an event instead of suspending the field, and ``have_item``
reads false.

What it DOES interpret is grounded, not guessed:
  * the tick model — every tick each unit's branches are tried top to bottom, first
    match selects (docs/BEHAVIOR.md "The model"); the ticker cadence is ``Wait(1)`` so
    one tick is one engine frame, 30/s (the alternator teach's 400 frames ≈ 13 s).
  * movement — the engine moves ``actor.speed`` UNITS PER FRAME straight at the target
    (Memoria ``EventEngine.MoveToward``/``GetMoveVector``; MSPEED stores the byte raw).
  * ALL proximity is Chebyshev (|dx|<r AND |dz|<r) — the compiler's own Int24 law.
  * defaults (standoff/arrive_r/avoid_r/intervals/…) are DERIVED from the compiler's
    action dataclasses at import, never copied numbers.
  * the hysteresis law — a sticky ``once``/``cooldown`` condition is both trigger and
    keep: the engagement ends the first tick the condition FAILS (preemption by a
    higher row does not latch it); ``once`` over the one-shot family is an EVENT — it
    fires once and releases immediately (the starvation-family distinction this
    instrument exists to show).
  * feeds persist — selecting a non-feed branch (swing/one-shot) leaves the walk
    targets where the last feed wrote them, exactly like the duty walk's GLOBs.

Qt-free, like behaviorscan: the projections are plain data over a raw field dict.
Determinism is a contract — same doc + same player path ⇒ identical history (wander
rolls come from a hash of (tick, unit, axis), not the wall clock).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from ..content import behavior as B
from ..content import behaviortoml as BT
from . import behaviorscan as BS

TICKS_PER_SEC = 30                     # the engine event loop; 400-frame alternator ≈ 13 s


def _dflt(cls, name):
    """A compiler action dataclass's field default — derived, never copied."""
    return cls.__dataclass_fields__[name].default


_STANDOFF = int(_dflt(B.Chase, "standoff"))
_ARRIVE = int(_dflt(B.Patrol, "arrive_r"))
_AVOID = int(_dflt(B.Flee, "avoid_r"))
_WANDER_R = int(_dflt(B.Wander, "radius"))
_WANDER_HOLD = int(_dflt(B.Wander, "hold"))
_SWING_IV = int(_dflt(B.SwingAt, "interval"))
_ENGAGE_R = int(_dflt(B.Engage, "radius"))
_ENGAGE_IV = int(_dflt(B.Engage, "interval"))
_ENGAGE_DMG = int(_dflt(B.Engage, "damage"))
_ENGAGE_CONTACT = int(_dflt(B.Engage, "contact"))
_WALK_SPEED = int(_dflt(B.UnitSpec, "walk_speed"))

_FEEDS = {"walk_to", "hold", "hold_post", "patrol", "march", "flee", "wander",
          "chase", "hold_ground"}
_ONE_SHOTS = {"announce", "announce_npc", "battle", "award", "sfx", "flash",
              "stop_timer", "add_shop_item", "remove_shop_item", "add_shop_synth",
              "remove_shop_synth"}


def _cheb(a, b) -> float:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def _rand8(tick: int, unit: str, axis: str) -> int:
    """Deterministic stand-in for the engine's Comn.random8() — a hash, not a clock."""
    h = hashlib.blake2s(f"{tick}:{unit}:{axis}".encode(), digest_size=2).digest()
    return h[0]


@dataclass
class SimEvent:
    """One logged one-shot: what fired, who fired it, when."""
    tick: int
    unit: str
    kind: str
    text: str


@dataclass
class _Unit:
    name: str
    row: int                           # owning unit-row index
    row_name: str                      # the tab's row identity (class or npc name)
    x: float
    z: float
    spawn: tuple
    hp: int | None
    speed: int
    pooled: bool
    alive: bool = True
    dormant: bool = False              # pooled: seated but not in play
    sel: int = -1                      # selected branch index this tick (-1 = none)
    feed: tuple | None = None          # live walk target (x, z) or None
    feed_speed: int = 0
    wp: int = 0                        # patrol/march waypoint index
    marching_done: bool = False
    wander_tgt: tuple | None = None
    register: str | None = None        # engage target register
    mirror: tuple = (0, 0)             # last-alive position (scan-freeze semantics)


class Sim:
    """Build once from the OPEN document (or a [siege] view), then :meth:`run_to` /
    :meth:`at`. Lenient like the stage: what cannot resolve is SKIPPED with a note,
    never raised — validate() owns refusals."""

    def __init__(self, raw: dict):
        self.notes: list[str] = []
        self.events: list[SimEvent] = []
        b = BT.table(raw) or {}
        positions = BT._npc_marker_positions(raw)
        self._mpaths = BT.marker_paths(raw)
        self._positions = positions
        self.timer0 = b.get("timer")
        self.tables0 = {str(t.get("name")): [int(v) for v in (t.get("values") or [])]
                        for t in (b.get("table") or [])}
        self.counters0 = {str(n): 0 for n in (b.get("counters") or [])}
        self.alternators = [(str(a.get("name")), int(a.get("frames", 1)))
                            for a in (b.get("alternators") or []) if a.get("frames")]
        self.schedules = [(str(s.get("counter")), str(s.get("table")))
                          for s in (b.get("schedule") or [])]
        self.scans = list(b.get("scan") or [])
        self.groups = {str(g.get("name")): [str(u) for u in (g.get("units") or [])]
                       for g in (b.get("group") or [])}
        player = (raw.get("player", {}) or {}).get("spawn") or [0, 0]
        self.player_moves: dict[int, tuple] = {0: (float(player[0]), float(player[1]))}

        self.rows: list[dict] = []     # normalized unit rows: {"branches": [...], ...}
        self._units: list[_Unit] = []
        pooled_names, no_pos = [], []
        for ui, u in enumerate(BT.units(raw)):
            rn = BS.row_name(u, ui)
            spd_list = u.get("speeds")
            branches = [br for br in (u.get("branch") or []) if isinstance(br, dict)]
            self.rows.append({"name": rn, "branches": branches})
            for mi, m in enumerate(BT.row_members(u)):
                if m not in positions:
                    no_pos.append(m)
                    continue
                x, z = positions[m]
                spd = int(spd_list[mi]) if spd_list is not None else \
                    int(u.get("speed") or _WALK_SPEED)
                pu = _Unit(name=m, row=ui, row_name=rn, x=float(x), z=float(z),
                           spawn=(float(x), float(z)), hp=u.get("hp"), speed=spd,
                           pooled=bool(u.get("pooled")), mirror=(float(x), float(z)))
                if pu.pooled:
                    pu.dormant = True
                    pooled_names.append(m)
                self._units.append(pu)

        self._hp0 = {u.name: u.hp for u in self._units}
        # decorator state, keyed (row, branch, member)
        self._once: set = set()
        self._cool: dict = {}
        self._sel_prev: dict = {}      # member -> selected branch index last tick
        self._swing_phase: dict = {}   # (member, row, branch) -> next strike tick
        self._history: list[dict] = []
        self._live: dict = {}          # scratch mutable state while stepping

        self.notes.append("walks are STRAIGHT lines — no walkmesh, no unit collision "
                          "(the Sweep lane owns wall truth; a route clean here can "
                          "still jam in-game)")
        if pooled_names:
            self.notes.append("pooled units stay dormant (%s) — the hire economy is "
                              "not simulated" % ", ".join(sorted(pooled_names)))
        if no_pos:
            self.notes.append("no position for %s — left out of the sim"
                              % ", ".join(sorted(set(no_pos))))
        if any(any("battle" in (br.get("do") or {}) for br in r["branches"])
               for r in self.rows):
            self.notes.append("battle logs an event here; in-game it suspends the "
                              "field (swirl, fight, Main_Reinit return)")
        self._snapshot(0)              # state 0 = boot

    # ------------------------------------------------------------------ public API
    @property
    def head(self) -> int:
        return len(self._history) - 1

    def run_to(self, tick: int) -> None:
        while self.head < tick:
            self._step(self.head + 1)

    def at(self, tick: int) -> dict:
        """The snapshot at ``tick`` (running forward as needed)."""
        self.run_to(tick)
        return self._history[tick]

    def move_player(self, tick: int, x, z) -> None:
        """Move the SIM's player at ``tick`` — the stepper's one interactive input.
        The move joins the timeline (scrubbing back and forward replays identically),
        so all state is recomputed from boot: cheap by determinism."""
        self.player_moves = {t: p for t, p in self.player_moves.items() if t <= tick}
        self.player_moves[tick] = (float(x), float(z))
        self._rebuild_to(tick)

    def player_at(self, tick: int) -> tuple:
        t = max(k for k in self.player_moves if k <= tick)
        return self.player_moves[t]

    # ------------------------------------------------------------------ the tick
    def _rebuild_to(self, tick: int) -> None:
        """Reset every stepping state and replay 0..tick — a player move edits the
        timeline's past, and determinism makes the replay exact and cheap."""
        self._once.clear()
        self._cool.clear()
        self._sel_prev.clear()
        self._swing_phase.clear()
        self._live.clear()
        self.events = []
        for u in self._units:
            u.x, u.z = u.spawn
            u.mirror = u.spawn
            u.alive, u.dormant = True, u.pooled
            u.hp = None if u.hp is None else self._hp0[u.name]
            u.sel, u.feed, u.feed_speed = -1, None, 0
            u.wp, u.marching_done, u.wander_tgt, u.register = 0, False, None, None
        self._history = []
        self._snapshot(0)
        self.run_to(tick)

    def _step(self, tick: int) -> None:
        st = self._history[-1]
        flags = dict(st["flags"])
        counters = dict(st["counters"])
        tables = {k: list(v) for k, v in st["tables"].items()}
        frozen = st["timer_frozen"]
        remaining = None
        if self.timer0 is not None:
            remaining = st["timer"] if frozen else max(0.0, self.timer0 - tick / TICKS_PER_SEC)

        # 1. clocks: alternators flip on the frame parity of their period
        for name, frames in self.alternators:
            flags[name] = (tick // frames) % 2

        # 2. the schedule clock: while remaining < table[counter], counter += 1
        for cname, tname in self.schedules:
            t = tables.get(tname) or self.tables0.get(tname) or []
            idx = counters.get(cname, 0)
            v = t[idx] if 0 <= idx < len(t) else 0   # off-end reads 0: the terminator
            if remaining is not None and v and remaining < v:
                counters[cname] = idx + 1

        # 3. scans (Chebyshev box headcounts; mirrors freeze on deactivate)
        for s in self.scans:
            roster = ([str(u) for u in (s.get("units") or [])] or
                      self.groups.get(str(s.get("group") or ""), []))
            alive_only = bool(s.get("alive_only"))
            pt, r = s.get("point"), s.get("radius")
            hits = []
            for m in roster:
                u = self._by_name(m)
                if u is None or u.dormant:
                    hits.append(0)
                    continue
                if alive_only and not u.alive:
                    hits.append(0)
                    continue
                if pt is None or r is None:
                    hits.append(1 if (u.alive or not alive_only) else 0)
                else:
                    p = self._point(pt)
                    hits.append(1 if (p and _cheb(u.mirror, p) < int(r)) else 0)
            if s.get("count"):
                counters[str(s["count"])] = sum(hits)
            if s.get("flags"):
                tables[str(s["flags"])] = hits

        # 4. per unit, roster order: select top-down, act
        player = self.player_at(tick)
        ctx = {"flags": flags, "counters": counters, "tables": tables,
               "remaining": remaining, "player": player, "tick": tick}
        for u in self._units:
            if u.dormant or not u.alive:
                u.sel = -1
                continue
            row = self.rows[u.row]
            sel = -1
            for bi, br in enumerate(row["branches"]):
                key = (u.row, bi, u.name)
                if key in self._once:
                    continue
                if self._cool.get(key, 0) > tick:
                    continue
                if all(self._cond(u, c, ctx) for c in (br.get("when") or [])
                       if isinstance(c, dict)):
                    sel = bi
                    break
            # the hysteresis law: a sticky decorator latches when its own cond FAILS
            prev = self._sel_prev.get(u.name, -1)
            if prev >= 0 and prev != sel and prev < len(row["branches"]):
                pbr = row["branches"][prev]
                verb = self._verb(pbr)
                if verb not in _ONE_SHOTS and (pbr.get("once") or pbr.get("cooldown")):
                    ended = not all(self._cond(u, c, ctx)
                                    for c in (pbr.get("when") or [])
                                    if isinstance(c, dict))
                    if ended:
                        pkey = (u.row, prev, u.name)
                        if pbr.get("once"):
                            self._once.add(pkey)
                        if pbr.get("cooldown"):
                            self._cool[pkey] = tick + int(pbr["cooldown"])
            u.sel = sel
            if sel >= 0:
                br = row["branches"][sel]
                for fname in (br.get("raise_flags") or []):
                    flags[str(fname)] = 1
                for fname in (br.get("clear_flags") or []):
                    flags[str(fname)] = 0
                self._act(u, sel, br, ctx, tick, counters, flags)
            self._sel_prev[u.name] = sel

        # 5. movement integration: speed units per frame, straight at the feed
        for u in self._units:
            if not u.alive or u.dormant or u.feed is None:
                continue
            dx, dz = u.feed[0] - u.x, u.feed[1] - u.z
            d = max(abs(dx), abs(dz), 1e-9)
            eu = (dx * dx + dz * dz) ** 0.5
            spd = u.feed_speed or u.speed
            if eu <= spd:                          # the engine's own arrive test
                u.x, u.z = u.feed
            else:
                u.x += dx / eu * spd
                u.z += dz / eu * spd
            u.mirror = (u.x, u.z)
        self._snapshot(tick, flags, counters, tables, remaining, frozen)

    # ------------------------------------------------------------------ conditions
    def _by_name(self, name: str):
        for u in self._units:
            if u.name == name:
                return u
        return None

    def _pos_of(self, name: str, ctx):
        if name == "player":
            return ctx["player"]
        u = self._by_name(str(name))
        if u is not None:
            return u.mirror                        # frozen on death, like the mirrors
        return self._positions.get(str(name))

    def _point(self, v):
        try:
            x, z = BT._resolve_point(v, self._positions, "sim")
            return (float(x), float(z))
        except Exception:                          # noqa: BLE001 -- validate's job
            return None

    def _note_once(self, text: str) -> None:
        if text not in self.notes:
            self.notes.append(text)

    def _cond(self, u: _Unit, c: dict, ctx) -> bool:
        me = (u.x, u.z)
        if "hp_le" in c:
            return u.hp is not None and u.hp <= int(c["hp_le"])
        if "hp_gt" in c:
            return u.hp is not None and u.hp > int(c["hp_gt"])
        if "near" in c or "not_near" in c:
            k = "near" if "near" in c else "not_near"
            tgt, r = c[k][0], int(c[k][1])
            p = self._pos_of(tgt, ctx)
            inside = p is not None and _cheb(me, p) < r
            return inside if k == "near" else not inside
        if "near_point" in c or "not_near_point" in c:
            k = "near_point" if "near_point" in c else "not_near_point"
            p = self._point(c[k][0])
            inside = p is not None and _cheb(me, p) < int(c[k][1])
            return inside if k == "near_point" else not inside
        if "any_near" in c:
            names, r = c["any_near"][0], int(c["any_near"][1])
            return any((p := self._pos_of(n, ctx)) is not None and _cheb(me, p) < r
                       for n in names)
        if "flag" in c:
            return bool(ctx["flags"].get(str(c["flag"])))
        if "not_flag" in c:
            return not ctx["flags"].get(str(c["not_flag"]))
        if "any_flag" in c:
            return any(ctx["flags"].get(str(n)) for n in c["any_flag"])
        if "active" in c:
            t = self._by_name(str(c["active"]))
            return t is not None and t.alive and not t.dormant
        if "not_active" in c:
            t = self._by_name(str(c["not_active"]))
            return t is None or not t.alive or t.dormant
        if "any_active" in c:
            return any((t := self._by_name(str(n))) is not None and t.alive
                       and not t.dormant for n in c["any_active"])
        if "time_below" in c:
            return ctx["remaining"] is not None and ctx["remaining"] < int(c["time_below"])
        if "time_above" in c:
            return ctx["remaining"] is not None and ctx["remaining"] > int(c["time_above"])
        if "counter_ge" in c or "counter_le" in c or "counter_eq" in c:
            k = next(k for k in ("counter_ge", "counter_le", "counter_eq") if k in c)
            name, n = str(c[k][0]), int(c[k][1])
            v = ctx["counters"].get(name, 0)
            return {"counter_ge": v >= n, "counter_le": v <= n,
                    "counter_eq": v == n}[k]
        if "table_ge" in c or "table_le" in c or "table_eq" in c:
            k = next(k for k in ("table_ge", "table_le", "table_eq") if k in c)
            name, idx, n = str(c[k][0]), c[k][1], int(c[k][2])
            t = ctx["tables"].get(name) or self.tables0.get(name) or []
            i = ctx["counters"].get(str(idx), 0) if isinstance(idx, str) else int(idx)
            v = t[i] if 0 <= i < len(t) else 0     # off-end reads 0, like the engine lane
            return {"table_ge": v >= n, "table_le": v <= n, "table_eq": v == n}[k]
        if "have_item" in c:
            self._note_once("have_item reads FALSE here — inventory is not simulated")
            return False
        self._note_once(f"unknown condition {sorted(c)} reads FALSE here")
        return False

    # ------------------------------------------------------------------ actions
    @staticmethod
    def _verb(br: dict) -> str:
        do = br.get("do")
        if not isinstance(do, dict):
            return "?"
        for k in do:
            if k in _FEEDS or k in _ONE_SHOTS or k in ("swing_at", "engage", "die"):
                return k
        return next(iter(do), "?")

    def _fire(self, u: _Unit, tick: int, kind: str, text: str) -> None:
        self.events.append(SimEvent(tick, u.name, kind, text))

    def _act(self, u: _Unit, bi: int, br: dict, ctx, tick: int, counters, flags) -> None:
        do = br.get("do") or {}
        verb = self._verb(br)
        key = (u.row, bi, u.name)
        spd = int(do.get("speed") or 0)

        if verb in _ONE_SHOTS:
            # once here is an EVENT: fire, latch, release (never a held engagement).
            # battle latches by construction (one-shot per field load); the rest latch
            # on their selection EDGE when un-onced.
            prev = self._sel_prev.get(u.name, -1)
            if verb == "battle" or br.get("once"):
                self._once.add(key)
            elif prev == bi:
                return                             # edge-fired already, still selected
            text = {"announce": str(do.get("announce", "")),
                    "announce_npc": str(do.get("announce_npc", "")),
                    "battle": f"battle scene {do.get('battle')}",
                    "award": f"award {do.get('award')} gil",
                    "sfx": f"sfx {do.get('sfx')}",
                    "flash": "screen flash",
                    "stop_timer": "timer frozen"}.get(verb, verb)
            self._fire(u, tick, verb, text)
            if verb == "stop_timer":
                self._live["freeze"] = True
            return

        if verb == "die":
            u.alive = False
            u.sel = bi
            u.feed = None
            cname = do.get("die")
            if isinstance(cname, str):
                counters[cname] = counters.get(cname, 0) + 1
            self._fire(u, tick, "die", f"{u.name} dies")
            return

        if verb == "swing_at":
            iv = int(do.get("interval") or _SWING_IV)
            if tick >= self._swing_phase.get(key, 0):
                self._swing_phase[key] = tick + iv
                t = self._by_name(str(do.get("swing_at")))
                if t is not None and t.alive and t.hp is not None:
                    t.hp -= int(do.get("damage") or 1)
            return

        if verb == "engage":
            radius = int(do.get("radius") or _ENGAGE_R)
            contact = int(do.get("contact") or _ENGAGE_CONTACT)
            iv = int(do.get("interval") or _ENGAGE_IV)
            roster = self.groups.get(str(do.get("engage")), [])
            reg = self._by_name(u.register) if u.register else None
            if reg is None or not reg.alive or _cheb((u.x, u.z), reg.mirror) >= radius:
                u.register = None
                cands = [t for m in roster if (t := self._by_name(m)) is not None
                         and t.alive and not t.dormant
                         and _cheb((u.x, u.z), (t.x, t.z)) < radius]
                if cands:
                    if do.get("nearest"):
                        cands.sort(key=lambda t: _cheb((u.x, u.z), (t.x, t.z)))
                    u.register = cands[0].name
                reg = self._by_name(u.register) if u.register else None
            if reg is None:
                u.feed, u.feed_speed = (u.x, u.z), spd or u.speed   # hold ground
                return
            if _cheb((u.x, u.z), (reg.x, reg.z)) <= contact:
                u.feed = (u.x, u.z)
                if tick >= self._swing_phase.get(key, 0):
                    self._swing_phase[key] = tick + iv
                    if reg.hp is not None:
                        reg.hp -= int(do.get("damage") or _ENGAGE_DMG)
            else:
                u.feed, u.feed_speed = (reg.x, reg.z), spd or u.speed
            return

        # feeds
        if verb == "walk_to":
            p = self._point(do["walk_to"])
        elif verb == "hold":
            p = self._point(do["hold"])
        elif verb == "hold_post":
            p = u.spawn
        elif verb == "hold_ground":
            p = (u.x, u.z)
        elif verb == "chase":
            tp = self._pos_of(do.get("chase"), ctx)
            standoff = int(do.get("standoff") or _STANDOFF)
            p = (u.x, u.z) if (tp is None or _cheb((u.x, u.z), tp) <= standoff) else tp
        elif verb in ("patrol", "march"):
            pts = self._route(do.get(verb))
            if not pts:
                return
            arrive = int(do.get("arrive_r") or _ARRIVE)
            if u.marching_done and verb == "march":
                p = pts[-1]
            else:
                if _cheb((u.x, u.z), pts[u.wp % len(pts)]) < arrive:
                    if verb == "march" and u.wp + 1 >= len(pts):
                        u.marching_done = True
                    else:
                        u.wp += 1
                p = pts[-1] if (verb == "march" and u.marching_done) \
                    else pts[u.wp % len(pts)]
        elif verb == "flee":
            threat = self._pos_of(do.get("flee"), ctx)
            avoid = int(do.get("avoid_r") or _AVOID)
            refs = [self._point(r) for r in (do.get("to") or [])]
            refs = [r for r in refs if r is not None]
            if not refs:
                return
            p = next((r for r in refs
                      if threat is None or _cheb(threat, r) >= avoid), refs[-1])
        elif verb == "wander":
            centre = self._point(do.get("wander"))
            if centre is None:
                return
            radius = int(do.get("radius") or _WANDER_R)
            hold = int(do.get("hold") or _WANDER_HOLD)
            if u.wander_tgt is None or tick % hold == 0:
                ox = (_rand8(tick - tick % hold, u.name, "x") - 128) * radius / 128
                oz = (_rand8(tick - tick % hold, u.name, "z") - 128) * radius / 128
                u.wander_tgt = (centre[0] + ox, centre[1] + oz)
            p = u.wander_tgt
        else:
            self._note_once(f"action {verb!r} is not simulated (the unit stands)")
            return
        if p is not None:
            u.feed, u.feed_speed = p, spd or u.speed

    def _route(self, v):
        if isinstance(v, str):
            pts, _closed = self._mpaths.get(v, ((), False))
            return [(float(x), float(z)) for x, z in pts]
        if isinstance(v, (list, tuple)):
            return [(float(p[0]), float(p[1])) for p in v
                    if isinstance(p, (list, tuple)) and len(p) >= 2]
        return []

    # ------------------------------------------------------------------ snapshots
    def _snapshot(self, tick, flags=None, counters=None, tables=None,
                  remaining=None, frozen=False) -> None:
        if flags is None:
            flags, counters = {}, dict(self.counters0)
            tables = {k: list(v) for k, v in self.tables0.items()}
            remaining = float(self.timer0) if self.timer0 is not None else None
        if self._live.pop("freeze", False):
            frozen = True
        self._history.append({
            "tick": tick,
            "timer": remaining,
            "timer_frozen": frozen,
            "flags": flags,
            "counters": counters,
            "tables": tables,
            "player": self.player_at(tick),
            "units": {u.name: {"x": u.x, "z": u.z, "hp": u.hp, "alive": u.alive,
                               "dormant": u.dormant, "sel": u.sel, "row": u.row,
                               "unit": u.row_name}
                      for u in self._units},
            "events": len(self.events),
        })
