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


def _sc_by_func(census: dict) -> dict:
    """(field, entry, func) -> the SC values that function itself writes (estimator E3)."""
    d: dict = {}
    for s in census.get("sc_sites", ()):
        d.setdefault((s["field"], s["entry"], s["func"]), []).append(s["value"])
    return d


def _field_env(census: dict) -> dict[int, int]:
    """field -> its lowest literal SC write (estimator E4, the writer-field envelope)."""
    d: dict[int, int] = {}
    for s in census.get("sc_sites", ()):
        f = s["field"]
        if f not in d or s["value"] < d[f]:
            d[f] = s["value"]
    return d


def _site_lo_full(site: dict, sc_by_func: dict, field_env: dict) -> tuple[int, str] | None:
    """The full estimator ladder for ANY censused site (party/word/bit alike): the site's own
    proven SC window (direct, then armed), else a co-located SC advance in the same function
    (E3), else the writer field's envelope (E4). None = the site carries no SC evidence."""
    best = _site_lo(site)
    if best:
        return best
    k = (site["field"], site["entry"], site["func"])
    if k in sc_by_func:
        return (min(sc_by_func[k]), "advance")
    if site["field"] in field_env:
        return (field_env[site["field"]], "envelope")
    return None


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
        # STRICT within-beat rule (the Dali-latch lesson): lo == beat means the write happens
        # DURING this beat's own play (the seed target is the state at the instant the SC
        # first equals the beat), so the bit boots clear and the resident scripts flip it --
        # seeding it set replays the beat with its own latches pre-tripped, which SUPPRESSES
        # once-guarded content (the ATE offer chain enters only while its latch is 0).
        rep.verdicts.append(BitVerdict(bit, "set" if lo < beat else "clear",
                                       lo=lo, estimator=kind, writers=writers))
    return rep


def render_startup(rep: SeedReport, *, field_label: str = "", once_flag: int | None = None) -> str:
    """The paste-ready ``[startup]`` block + provenance comments. ``once_flag`` emits the
    once-sentinel guard (the chain lever): the stamp fires on the FIRST entry into any member
    sharing the sentinel and never again, so in-chain story progression (the resident scripts'
    own SC advances and once-bits) is never rewound at a door."""
    L = [f"# story-seed{' for ' + field_label if field_label else ''} @ beat {rep.beat}"
         f" ({flagsmod.nearest_milestone(rep.beat)[1]})"]
    L.append("[startup]")
    L.append(f"scenario = {rep.beat}")
    if once_flag is not None:
        L.append(f"once = {once_flag}")
        L.append("# once-stamp sentinel (shared chain-wide): the first room entered stamps the "
                 "beat and sets this bit; later entries leave the RUNNING story alone. New Game "
                 "zeroes it for a fresh run.")
    setters = rep.set_bits
    if setters:
        rows = ", ".join("{ flag = %d, value = 1 }" % v.bit for v in setters)
        L.append(f"flags = [ {rows} ]")
    for v in rep.verdicts:
        if v.decision == "set":
            L.append(f"# bit {v.bit}: SET -- first settable at SC {v.lo} ({v.estimator}; "
                     f"writers {list(v.writers)})")
        elif v.decision == "clear":
            if v.lo == rep.beat:
                L.append(f"# bit {v.bit}: clear -- flips DURING this beat (first settable "
                         f"at SC {v.lo} == beat; the resident scripts set it as the beat plays)")
            else:
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


def _window_party_adds(add_ids, beat, census, donor):
    """Split *add_ids* into (kept, windowed_out) at *beat* using the census party_sites:
    a member whose EVERY add site in this donor first fires at an SC ABOVE the beat belongs
    to a different visit's roster (the Dali-Marcus lesson) and is windowed OUT — reported
    with its earliest SC, never silently dropped. A member with no census evidence is kept
    (the pre-window behavior; evidence absence is not evidence of absence)."""
    by_char: dict[int, list] = {}
    for s in census.get("party_sites", ()):
        if s["field"] == donor and s["kind"] == "add" and s.get("char") is not None:
            by_char.setdefault(s["char"], []).append(s)
    scf, fenv = _sc_by_func(census), _field_env(census)
    kept, out = [], []
    for i in add_ids:
        los = [e[0] for e in (_site_lo_full(s, scf, fenv) for s in by_char.get(i, ()))
               if e is not None]
        if los and min(los) > beat:
            out.append((i, min(los)))
        else:
            kept.append(i)
    return kept, out


def party_seed(eb: EbScript, beat: int | None = None, census: dict | None = None,
               donor: int | None = None) -> dict:
    """The party evidence for a fork of this field: ``add`` = the cast the field's own party
    ops both ADD and GATE on (its story reset builds the beat's roster), plus the donor's
    non-Zidane player identity (the controlled body must exist); ``dormant`` = members the
    field CHECKS but never adds (a cross-beat branch, e.g. a pre-join Quina check) — reported
    for the author to assert, never auto-seeded (the wrong extra member is a false beat).
    With *beat*+*census*+*donor*, the adds are WINDOWED: a member whose add sites all prove
    an SC above the beat is excluded and reported under ``future`` (the same rung-0 guard
    evidence the [startup] bits use — no hand rules)."""
    from . import eventscan, forkreport
    from .content.party import CHAR_OLD_INDEX

    ops = forkreport.scan_party_ops(eb.data)
    req, adds = set(ops.get("required", ())), set(ops.get("adds", ()))
    add_ids = sorted(req & adds)
    windowed_out: list[tuple[int, int]] = []
    if beat is not None and census is not None and donor is not None:
        add_ids, windowed_out = _window_party_adds(add_ids, beat, census, donor)
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
        "future": [(name(i), lo) for i, lo in windowed_out],
    }


def render_party(ps: dict) -> str:
    if not ps["add"] and not ps["dormant"] and not ps.get("future"):
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
    for n, lo in ps.get("future", ()):
        L.append(f"# {n}: windowed OUT -- this donor's add first fires at SC {lo} > beat "
                 "(a different visit's roster)")
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


OP_ATE = 0xD7


def _expr_word_reads(data: bytes, ins) -> set[int]:
    """Global word/byte indexes (vtype 4-7, idx > 3) token-read anywhere in one SET
    statement's expression — catches BITWISE availability tests (``word & 1``) that the
    comparison parser rightly treats as opaque (the Dali-297 lesson)."""
    out: set[int] = set()
    pos, limit = ins.off + 1, ins.end
    while pos < limit:
        o = data[pos]; pos += 1
        if o == 0xD3:
            pos += 3; continue
        if o == 0x7E:
            pos += 4; continue
        if o in (0x7D, 0x78):
            pos += 2; continue
        if o >= 0xC0:
            idx = (data[pos] | (data[pos + 1] << 8)) if o >= 0xE0 else data[pos]
            pos += 2 if o >= 0xE0 else 1
            if (o & 3) == 0 and ((o >> 2) & 7) in (4, 5, 6, 7) and idx > 3:
                out.add(idx)
            continue
        if o in (0x29, 0x5F, 0x79, 0x7A):
            pos += 1; continue
        if o == 0x7F:
            break
    return out


def _self_written_words(eb: EbScript) -> set[int]:
    """Byte indexes of Global word/byte vars this field's OWN scripts assign (any function —
    the field manages that state itself, so a seed for it is at best noise and at worst a
    mis-ordering: the room-code/sequencing words the Dali controllers rewrite at entry)."""
    from .eb.cfg import parse_set
    out: set[int] = set()
    for e in eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            try:
                fl = FuncFlow.build(eb.data, f.abs_start, f.abs_end)
            except CfgError:
                continue
            for st, _blk in fl.iter_sets(eb.data):
                if st.kind == "assign" and st.source == 0 and st.vtype in (4, 5, 6, 7) \
                        and st.index is not None and st.index > 3:
                    span = 1 if st.vtype in (6, 7) else 0
                    out.update(range(st.index, st.index + span + 1))
    return out


def ate_word_seed(eb: EbScript) -> list[int]:
    """Bytes of the gEventGlobal WORD(s) gating this field's ``ATE(1)`` arm — the
    availability detection (docs/ATE_SYSTEM.md: a cold fork boots with the word 0 → the ATE
    menu never arms; THIS, not the ScenarioCounter, is why scenario-only forks show no ATE).
    Two evidence channels, both from the rung-0 CFG: word-var COMPARISONS dominating an
    ATE(1) site, and word-vars token-read in the dominator chain's branch statements (the
    bitwise ``word & 1`` hub-enable idiom is opaque to the comparison parser). Words the
    field's OWN scripts assign are then excluded — that is self-managed sequencing state
    (room codes, frame counters) the resident logic rewrites at entry; what remains is the
    EXTERNAL story state a fork must seed.

    Returns ``{byte_idx: channel}`` — ``'cmp'`` (a proven comparison gate; seeded even
    without a derivable value) or ``'expr'`` (an opaque-test read; seeded ONLY when a value
    derives — the token scan may over-collect neighbours of the arm)."""
    cands: dict[int, str] = {}
    for e in eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            try:
                fl = FuncFlow.build(eb.data, f.abs_start, f.abs_end)
            except CfgError:
                continue
            for blk in fl.blocks:
                for ins in blk.instrs:
                    if ins.op != OP_ATE or ins.imm(0) != 1:
                        continue
                    for c in (fl.guards_at(ins.off) or ()):
                        if c.source == 0 and c.vtype in (4, 5, 6, 7) and c.index > 3:
                            cands[c.index] = "cmp"
                    b = fl.block_at(ins.off)
                    if b is None:
                        continue
                    mask = fl._dom[b]
                    d = 0
                    while mask:
                        if mask & 1:
                            dblk = fl.blocks[d]
                            if len(dblk.instrs) >= 2 \
                                    and dblk.instrs[-1].op in (0x02, 0x03, 0x06, 0x0B, 0x0D) \
                                    and dblk.instrs[-2].op == OP_SET:
                                for idx in _expr_word_reads(eb.data, dblk.instrs[-2]):
                                    cands.setdefault(idx, "expr")
                        mask >>= 1
                        d += 1
    self_w = _self_written_words(eb)
    return {i: ch for i, ch in sorted(cands.items()) if i not in self_w}


def ate_word_values(byte_idxs: list[int], beat: int, census: dict,
                    donors: list[int]) -> dict[int, int | None]:
    """Derive each detected avail byte's value AT the beat from the census word_sites: among
    the *donors*' literal writes covering the byte whose windowed SC is at/below the beat,
    the latest PURE write (the reset idiom) sets the floor, and every write from that floor
    up ORs in (the accumulation idiom — B_OR_LET per unlocked ATE). None = no windowed write
    found (the caller falls back to the value-1 placeholder). No hand tables: the mask is
    read off the same guard evidence the [startup] bits use. A donor write with NO SC
    evidence at all contributes BEFORE every beat (lo = -1): within the zone's own writer
    set, an unordered pure write is arrival/enable state (the Dali hub word 297 = 1,
    written by the village entrance with no SC gate)."""
    ds = set(donors)
    scf, fenv = _sc_by_func(census), _field_env(census)
    out: dict[int, int | None] = {}
    for bidx in byte_idxs:
        cands = []                                   # (lo, pure, byte_contribution)
        for s in census.get("word_sites", ()):
            if s["field"] not in ds or s.get("value") is None:
                continue
            span = 1 if s["vt"] in (6, 7) else 0     # a word write covers idx..idx+1
            if not (s["idx"] <= bidx <= s["idx"] + span):
                continue
            e = _site_lo_full(s, scf, fenv)
            lo = -1 if e is None else e[0]
            if lo > beat:
                continue
            v = int(s["value"]) & 0xFFFF
            contrib = (v >> 8) & 0xFF if bidx == s["idx"] + 1 else v & 0xFF
            cands.append((lo, bool(s.get("pure")), contrib))
        if not cands:
            out[bidx] = None
            continue
        pures = [lo for lo, p, _v in cands if p]
        floor = max(pures) if pures else min(lo for lo, _p, _v in cands)
        val = 0
        for lo, _p, v in cands:
            if lo >= floor:
                val |= v
        out[bidx] = val
    return out


def render_words(word_vals: dict[int, int | None]) -> str:
    if not word_vals:
        return ""
    rows = ", ".join("{ byte = %d, value = %d }" % (b, 1 if v is None else v)
                     for b, v in sorted(word_vals.items()))
    L = [f"words = [ {rows} ]"]
    derived = [(b, v) for b, v in sorted(word_vals.items()) if v is not None]
    fallback = [b for b, v in sorted(word_vals.items()) if v is None]
    if derived:
        L.append("# ATE availability word(s) gating ATE(1); value = OR of the donors' writes "
                 "windowed at/below the beat (each bit = one offered ATE)")
    if fallback:
        L.append(f"# byte(s) {fallback}: no windowed write derived -- value 1 arms ONE menu "
                 "row; WIDEN to the beat's unlocked set (e.g. 0x0F = 4 rows)")
    return "\n".join(L)


def seed_text(eb: EbScript, beat: int, census: dict, *, field_label: str = "",
              donor: int | None = None, zone_donors: list[int] | None = None,
              once_flag: int | None = None) -> str:
    """The complete seed for one field: [startup] (+ derived ATE words) + [party]. *donor*
    enables the beat-windowed party filter and the ATE mask derivation; *zone_donors* widens
    the mask's writer set to the whole chain (avail state is zone-global); *once_flag* emits
    the once-sentinel guard (chains stamp once, never rewinding in-chain progression)."""
    parts = [render_startup(resolve(eb, beat, census), field_label=field_label,
                            once_flag=once_flag)]
    detected = ate_word_seed(eb)
    if detected:
        writers = zone_donors or ([donor] if donor is not None else [])
        vals = ate_word_values(list(detected), beat, census, writers) if writers \
            else {b: None for b in detected}
        # 'expr'-channel words are speculative (opaque-test token scan): seed only when a
        # value actually derived; 'cmp'-channel words keep the placeholder fallback
        vals = {b: v for b, v in vals.items()
                if v is not None or detected[b] == "cmp"}
        parts.append(render_words(vals))
    p = render_party(party_seed(eb, beat=beat, census=census, donor=donor))
    if p:
        parts.append("\n" + p)
    return "\n".join(parts)


def backwards_advance_hazards(census: dict, donor: int, beat: int) -> list[int]:
    """SC values this donor's scripts WRITE that are BELOW the seeded beat -- a resident
    advance sequence (e.g. the Dali inn's sleep->morning SC=2600 write) run at a later seeded
    beat trips stock's backwards-write debug guard ("Error Set Scenario Counter()"; Skip is
    safe -- each room re-stamps its seed on entry). Warn, don't block: the sequence may be
    unreachable at the seeded beat."""
    return sorted({x["value"] for x in census.get("sc_sites", ())
                   if x["field"] == donor and 0 < x["value"] < beat})


def seed_chain(chain_dir: str, beat: int, census: dict, eb_for_donor) -> list[tuple[str, int, int]]:
    """Append a seed to EVERY member field.toml under *chain_dir* (a fresh seed replaces a
    prior one -- the '# story-seed' marker delimits). ``eb_for_donor(donor_id) -> EbScript``.
    Returns [(toml_path, member_id, donor_id)]."""
    import glob
    import re
    members = []
    for p in sorted(glob.glob(os.path.join(chain_dir, "**", "*.field.toml"), recursive=True)):
        text = open(p, encoding="utf-8").read()
        m_donor = re.search(r"^donor\s*=\s*(\d+)", text, re.M)
        m_id = re.search(r"^id\s*=\s*(\d+)", text, re.M)
        if not m_donor or not m_id:
            continue
        members.append((p, int(m_id.group(1)), int(m_donor.group(1)), text))
    zone = sorted({d for (_p, _m, d, _t) in members})
    # ONE once-stamp sentinel for the whole chain, derived from the lowest member id into the
    # safe custom band -- the first room entered stamps the beat; every other member sees the
    # sentinel set and leaves the RUNNING story alone (the Dali round-5 lesson: a per-entry
    # stamp rewinds the player's own SC advances at every door)
    once = chain_once_flag([m for (_p, m, _d, _t) in members]) if members else None
    out = []
    for p, mid, donor, text in members:
        lines = text.splitlines(keepends=True)
        cut = next((i for i, l in enumerate(lines) if l.startswith("# story-seed")), None)
        base = "".join(lines[:cut]) if cut is not None else text
        if not base.endswith("\n"):
            base += "\n"
        seed = seed_text(eb_for_donor(donor), beat, census, field_label=str(donor),
                         donor=donor, zone_donors=zone, once_flag=once)
        with open(p, "w", encoding="utf-8", newline="") as fh:
            fh.write(base + seed + "\n")
        out.append((p, mid, donor))
    return out


def chain_once_flag(member_ids: list[int]) -> int:
    """The chain's shared once-stamp sentinel bit: deterministic from the lowest member id,
    inside the safe custom band (>= FIRST_SAFE_FLAG -- the 8512 lesson). Distinct chains land
    on distinct bits as long as their id bases differ mod 1024 (dev chains mint spread bases)."""
    return flagsmod.FIRST_SAFE_FLAG + (min(member_ids) % 1024)


def chain_ladder(census: dict, donors: list[int]) -> list[tuple[int, str, list[int]]]:
    """The zone's ADVANCE LADDER: every ScenarioCounter value the member donors' own scripts
    WRITE, sorted, with milestone label + the writers. The story's flow through the zone is
    this ladder -- the resident content moments are the intervals between consecutive writes,
    and 'boot the zone at moment K' means seeding AT the K-th write value (the state just
    after that advance). This is the beat-selection surface for a chain; the --beats GATE
    list is a dispatch map, not the story's own flow (the Dali lesson: picking mid-gate-band
    2650 landed five sub-beats into the zone's storyline)."""
    ds = set(donors)
    by_val: dict[int, set] = {}
    for x in census.get("sc_sites", ()):
        if x["field"] in ds and x["value"] > 0:
            by_val.setdefault(x["value"], set()).add(x["field"])
    return [(v, flagsmod.nearest_milestone(v)[1], sorted(w)) for v, w in sorted(by_val.items())]


def chain_donors(chain_dir: str) -> list[tuple[int, int]]:
    """[(member_id, donor_id)] for every member field.toml under *chain_dir*."""
    import glob
    import re
    out = []
    for p in sorted(glob.glob(os.path.join(chain_dir, "**", "*.field.toml"), recursive=True)):
        text = open(p, encoding="utf-8").read()
        m_d = re.search(r"^donor\s*=\s*(\d+)", text, re.M)
        m_i = re.search(r"^id\s*=\s*(\d+)", text, re.M)
        if m_d and m_i:
            out.append((int(m_i.group(1)), int(m_d.group(1))))
    return out
