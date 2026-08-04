"""Demand-driven story-state seeding — rung 1 of the narrative-state arc.

``story-seed <field> --beat N`` answers ONE question: *which story bits does this field READ,
and which of them would a mainline playthrough have set by beat N?* It resolves ONLY the target
field's own read set (median 1 bit, ~90th percentile 12 — the scoping measurement), emits a
ready ``[startup]`` block with per-bit provenance, and lists every bit it could NOT resolve as
an explicit "defaulting clear" so the author's game knowledge can override.

Evidence comes from the rung-0 dominance census (``research/dominance_census.py`` →
``dominance_census.json``, regenerable from the install). Estimator ladder per bit, strongest
first: E1/E2 — a write site's proven SC window (direct, then armed); E3 — a literal SC advance
co-located in the writer function; E4 — the writer FIELD's lowest absolute SC write. A bit with
both set- and clear-writes is a TOGGLE (class W) and is reported, never auto-seeded.

Hard refusal (non-negotiable): a bit inside a reserved band or aliasing a named word is NEVER
emitted (``flags.is_reserved`` / ``flags.named_word_at``) — the 8512 lesson, enforced at the
emitter, not documented in prose.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field as dfield

from . import flags as flagsmod
from .eb import EbScript
from .eb.cfg import CfgError, FuncFlow, OP_SET

_HANDSHAKE = frozenset(range(184, 192))


def find_census(start: str | None = None) -> str | None:
    """Walk upward from *start* (or cwd) looking for research/dominance_census.json."""
    d = os.path.abspath(start or os.getcwd())
    for _ in range(8):
        p = os.path.join(d, "research", "dominance_census.json")
        if os.path.isfile(p):
            return p
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    return None


def read_set(eb: EbScript) -> dict[int, int]:
    """Every GLOB story bit the field's scripts READ → the number of read sites. A read is any
    Global bit var token in a ``SET`` statement that is not the statement's assignment target
    (token-complete: compounds, unsure conditions and computed expressions all count)."""
    from .eb.cfg import parse_set
    out: dict[int, int] = {}
    for e in eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            try:
                fl = FuncFlow.build(eb.data, f.abs_start, f.abs_end)
            except CfgError:
                fl = None
            blocks = fl.blocks if fl else []
            for blk in blocks:
                for ins in blk.instrs:
                    if ins.op != OP_SET:
                        continue
                    st = parse_set(eb.data, ins)
                    skip_first = st.kind == "assign"
                    pos, limit = ins.off + 1, ins.end
                    first = True
                    while pos < limit:
                        o = eb.data[pos]; pos += 1
                        if o == 0xD3:
                            pos += 3; continue
                        if o == 0x7E:
                            pos += 4; continue
                        if o in (0x7D, 0x78):
                            pos += 2; continue
                        if o >= 0xE0 or (0xC0 <= o < 0xE0):
                            idx = (eb.data[pos] | (eb.data[pos + 1] << 8)) if o >= 0xE0 \
                                else eb.data[pos]
                            pos += 2 if o >= 0xE0 else 1
                            is_bit = (o & 3) == 0 and ((o >> 2) & 7) in (0, 1)
                            if is_bit and not (first and skip_first) \
                                    and idx not in _HANDSHAKE:
                                out[idx] = out.get(idx, 0) + 1
                            first = False
                            continue
                        if o in (0x29, 0x5F, 0x79, 0x7A):
                            pos += 1; continue
                        if o == 0x7F:
                            break
                        first = False
    return out


@dataclass
class BitVerdict:
    bit: int
    decision: str            # 'set' | 'clear' | 'toggle' | 'unknown' | 'refused'
    lo: int | None = None    # the SC at/after which a mainline run has it set
    estimator: str = ""      # 'window' | 'armed' | 'advance' | 'envelope'
    writers: tuple = ()
    note: str = ""


@dataclass
class SeedReport:
    beat: int
    verdicts: list = dfield(default_factory=list)

    @property
    def set_bits(self):
        return [v for v in self.verdicts if v.decision == "set"]


def _site_lo(site: dict) -> tuple[int, str] | None:
    """The lowest SC bound a write site's evidence proves, with its estimator name."""
    best = None
    for chan, name in (("sc", "window"), ("sc_armed", "armed")):
        for (_s, _vt, _idx, cmp_, val) in site.get(chan, ()):
            vals = val if isinstance(val, list) else [val]
            if cmp_ in ("==", "in", ">=", ">"):
                v = min(vals) + (1 if cmp_ == ">" else 0)
                if best is None or v < best[0]:
                    best = (v, name)
    return best


def resolve(eb: EbScript, beat: int, census: dict) -> SeedReport:
    """Resolve the field's read set at *beat* against the census evidence."""
    by_bit: dict[int, list] = {}
    for s in census.get("bit_sites", ()):
        by_bit.setdefault(s["bit"], []).append(s)
    field_env: dict[int, int] = {}
    for s in census.get("sc_sites", ()):
        f = s["field"]
        if f not in field_env or s["value"] < field_env[f]:
            field_env[f] = s["value"]

    rep = SeedReport(beat)
    for bit in sorted(read_set(eb)):
        if flagsmod.is_reserved(bit) or flagsmod.named_word_at(bit // 8) is not None:
            rep.verdicts.append(BitVerdict(bit, "refused",
                                           note=str(flagsmod.bit_region(bit) or "named word")))
            continue
        sites = by_bit.get(bit, [])
        writers = tuple(sorted({s["field"] for s in sites}))
        sets = [s for s in sites if s.get("value") == 1]
        clears = [s for s in sites if s.get("value") == 0]
        if sets and clears:
            rep.verdicts.append(BitVerdict(bit, "toggle", writers=writers,
                                           note="set AND cleared by scripts (class W) - assert by hand"))
            continue
        if not sets:
            rep.verdicts.append(BitVerdict(bit, "unknown", writers=writers,
                                           note="no literal set-write in the census"))
            continue
        best = None
        for s in sets:
            e = _site_lo(s)
            if e and (best is None or e[0] < best[0]):
                best = e
        if best is None:
            envs = [field_env[f] for f in writers if f in field_env]
            if envs:
                best = (min(envs), "envelope")
        if best is None:
            rep.verdicts.append(BitVerdict(bit, "unknown", writers=writers,
                                           note="writers carry no SC evidence"))
            continue
        lo, kind = best
        rep.verdicts.append(BitVerdict(bit, "set" if lo <= beat else "clear",
                                       lo=lo, estimator=kind, writers=writers))
    return rep


def render_startup(rep: SeedReport, *, field_label: str = "") -> str:
    """The paste-ready ``[startup]`` block + provenance comments."""
    L = [f"# story-seed{' for ' + field_label if field_label else ''} @ beat {rep.beat}"
         f" ({flagsmod.nearest_milestone(rep.beat)[1]})"]
    L.append("[startup]")
    L.append(f"scenario = {rep.beat}")
    setters = rep.set_bits
    if setters:
        rows = ", ".join("{ flag = %d, value = 1 }" % v.bit for v in setters)
        L.append(f"flags = [ {rows} ]")
    for v in rep.verdicts:
        if v.decision == "set":
            L.append(f"# bit {v.bit}: SET -- first settable at SC {v.lo} ({v.estimator}; "
                     f"writers {list(v.writers)})")
        elif v.decision == "clear":
            L.append(f"# bit {v.bit}: clear -- first settable at SC {v.lo} > beat "
                     f"({v.estimator})")
        elif v.decision == "toggle":
            L.append(f"# bit {v.bit}: TOGGLE, not seeded -- {v.note}")
        elif v.decision == "refused":
            L.append(f"# bit {v.bit}: REFUSED (reserved/named: {v.note})")
        else:
            L.append(f"# bit {v.bit}: UNKNOWN, defaulting clear -- {v.note} "
                     f"(writers {list(v.writers)})")
    return "\n".join(L)


def party_seed(eb: EbScript) -> dict:
    """The party evidence for a fork of this field: ``add`` = the cast the field's own party
    ops both ADD and GATE on (its story reset builds the beat's roster), plus the donor's
    non-Zidane player identity (the controlled body must exist); ``dormant`` = members the
    field CHECKS but never adds (a cross-beat branch, e.g. a pre-join Quina check) — reported
    for the author to assert, never auto-seeded (the wrong extra member is a false beat)."""
    from . import eventscan, forkreport
    from .content.party import CHAR_OLD_INDEX

    ops = forkreport.scan_party_ops(eb.data)
    req, adds = set(ops.get("required", ())), set(ops.get("adds", ()))
    add_ids = sorted(req & adds)
    pents = eventscan.resolve_player_entries(eb)
    pnames = []
    for pe in pents:
        try:
            pnames.append(forkreport.player_name(eventscan._player_model(eb, pe)))
        except Exception:
            pass
    player_add = [] if any(n == "Zidane" for n in pnames) else \
        [n for n in pnames if n and not n.startswith("?")]
    name = lambda i: CHAR_OLD_INDEX.get(i, f"char{i}")           # noqa: E731
    return {
        "add": sorted({*(name(i).lower() for i in add_ids), *(n.lower() for n in player_add)}),
        "player": player_add,
        "gated": [name(i) for i in add_ids],
        "dormant": [name(i) for i in sorted(req - adds)],
    }


def render_party(ps: dict) -> str:
    if not ps["add"] and not ps["dormant"]:
        return ""
    L = []
    if ps["add"]:
        L.append("[party]")
        L.append("add = [ " + ", ".join(f'"{n}"' for n in ps["add"]) + " ]")
        bits = []
        if ps["player"]:
            bits.append(f"donor player: {'/'.join(ps['player'])} (non-Zidane -- must exist)")
            L.insert(0, "# NOTE: `add` never removes -- if the real beat is SOLO "
                        f"{'/'.join(ps['player'])}, also set remove = [the others] (author call)")
        if ps["gated"]:
            bits.append(f"field adds AND gates on: {', '.join(ps['gated'])}")
        L.append("# " + "; ".join(bits))
    if ps["dormant"]:
        L.append(f"# dormant party checks NOT seeded: {', '.join(ps['dormant'])} -- checked "
                 "but never added by this field; assert by hand only if the beat truly has them")
    return "\n".join(L)


def staged_beats(eb: EbScript) -> list[tuple[int, str]]:
    """The ScenarioCounter values this field's own scripts DISPATCH on (with milestone labels)
    — the beats the field actually stages. Seeding a beat BETWEEN gates lands in whatever band
    contains it; pick a staged value to hit a scene (the Dali-2700 lesson: 2700 fell between
    the inn-stay band 2600-2660 and 2790, so nothing special staged)."""
    from . import forkreport
    return [(v, flagsmod.nearest_milestone(v)[1]) for v in forkreport.scenario_gates(eb.data)]
