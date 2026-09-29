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
    (token-complete: compounds, unsure conditions and computed expressions all count). Bits in the
    kit's story-noise mask (``flags.story_noise_bits``: handshakes, the Mognet letter network, kit
    scratch) are not story reads and never reach a verdict; the side state (the moogle-talk latches)
    is real save state and does -- :func:`resolve` refuses it by name."""
    from .eb.cfg import parse_set
    noise = flagsmod.story_noise_bits()
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
                                    and idx not in noise:
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
        word = flagsmod.named_word_at(bit)          # a BIT index -- never bit // 8
        if flagsmod.is_reserved(bit) or word is not None:
            note = (flagsmod.bit_region(bit).name if flagsmod.is_reserved(bit)
                    else f"named word {word.name}")
            rep.verdicts.append(BitVerdict(bit, "refused", note=note))
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


# ---------------------------------------------------------------- the POST-ADVANCE phase (F5b)
# THE SEED IS THE HAND-OVER STATE OF THE ENTRY. A journey whose entry lies BEFORE the beat's own
# advance (the SC := beat store has not run -- F5's member(359)) takes the pre-advance row above: the
# advance's writes belong to the advance, which the entry path still plays (the strict within-beat
# rule). A journey whose entry lies AFTER it takes what stock holds when its own flow hands control
# into the entry: the advance ran IN PLACE and handed control back, and the player left through one
# of the advance room's EXIT gateways into the entry. So the row also carries (a) each read bit's
# value where every path through the store ends (the reaching literal definitions inside the advance
# function), then (b) what that exit's own walk-in writes before its Field() (the same reaching pass,
# with the hand-back value flowing in at its entry), and (c) the members the advance's own
# presence-guarded RemoveParty took out of the roster. The census has no scripted flow BETWEEN
# fields, so the phase is the author's input (``--after-advance``), and the call site REFUSES every
# hand-over this pass does not model exactly: an entry into the advance room itself (stock hands back
# in place -- no Field() enters it), an entry deeper than one exit, an advance whose own run leaves
# the scene (its scripted warp IS stock's hand-over), an exit that can re-set the scenario or a
# stamped word at this beat, an advance run that moves either after its store, an exit whose own warp
# into the entry cannot run at this beat, a party op after the store (the Party menu and
# SetPartyReserve included), a RemoveParty on the way to the store that is not a proven
# presence-guarded remove, and a roster the removes would empty (the survivor fallback would re-add).
# Every store is read off the engine's own expression stack (:func:`_set_targets`): ``SC++`` is a
# store, ``A := B`` does not write B, an assignment inside a condition is a store of unknown value. A
# pre-phase row whose entrance IS such an exit (its warp live at the beat) is refused too, unless the
# author asks for it as a calibration control (``--pre-phase-control``).

REMOVE_PARTY_OP = 0xDD
_PARTY_MENU_OP = 0xB2              # Party: the party menu -- the player picks the roster
_PARTY_RESERVE_OP = 0xB4           # SetPartyReserve: who may be picked
_PARTYADD_TOKEN = 0x6D
_ENTRY_DEF = ("entry",)            # the value the function was entered with (unknown here)
_KEEP = "keep"                     # an exit that leaves a bit as it came in (the hand-back stands)


@dataclass
class AdvanceHandback:
    """What the beat's own advance leaves when its run hands control back (the post phase).
    ``stores`` [(field, entry, tag, rel off)]; ``bits`` {bit: (value, [why])} for read bits whose
    hand-back value is ONE literal on every path through every store; ``undetermined`` the read
    bits the advance writes whose value is not; ``removed`` {char: [why]} (every advance function
    agrees); ``readds`` [(char, why)] conditional re-adds between a remove and the store, ASSUMED NOT
    TAKEN (the survivor fallback); ``leaves`` [why] a scene-leaving op (Field, WorldMap, Battle, ...)
    the run executes after a store; ``tail_party`` [why] a party op it executes after a store (a
    remove, an add, the Party menu 0xB2, SetPartyReserve 0xB4); ``roster`` [why] a RemoveParty that
    reaches a store but is not a proven presence-guarded remove; ``tail_writes`` [why] a store the run
    executes after the SC := beat store that leaves SC off the beat or a stamped word off its stamp;
    ``tail_agree`` [why] such stores that leave them AT the beat / stamp (kept, noted)."""
    stores: list = dfield(default_factory=list)
    bits: dict = dfield(default_factory=dict)
    undetermined: list = dfield(default_factory=list)
    removed: dict = dfield(default_factory=dict)
    readds: list = dfield(default_factory=list)
    leaves: list = dfield(default_factory=list)
    tail_party: list = dfield(default_factory=list)
    roster: list = dfield(default_factory=list)
    tail_writes: list = dfield(default_factory=list)
    tail_agree: list = dfield(default_factory=list)


def advance_stores(census: dict, donors, beat: int) -> dict:
    """``{(field, entry, tag): [abs offsets]}`` of every literal SC := *beat* store the zone's
    donors write (census ``sc_sites`` -- the same channel :func:`chain_ladder` reads)."""
    ds = set(donors)
    out: dict = {}
    for s in census.get("sc_sites", ()):
        if s["field"] in ds and s["value"] == beat:
            out.setdefault((s["field"], s["entry"], s["func"]), []).append(s["off"])
    return {k: sorted(v) for k, v in sorted(out.items())}


def _set_ops(data: bytes, ins):
    """The OPERATOR tokens of one SET statement, in order (operands skipped -- the token walk of
    ``eb.cfg.stmt_write_effect``)."""
    pos, limit = ins.off + 1, ins.end
    while pos < limit:
        o = data[pos]
        pos += 1
        if o == 0xD3:
            pos += 3
        elif o == 0x7E:
            pos += 4
        elif o in (0x7D, 0x78) or o >= 0xE0:
            pos += 2
        elif o >= 0xC0 or o in (0x29, 0x5F, 0x79, 0x7A):
            pos += 1
        elif o == 0x7F:
            return
        else:
            yield o


# B_POST_PLUS / B_POST_MINUS / B_PRE_PLUS / B_PRE_MINUS: each writes its one operand
_INCDEC = frozenset({4, 5, 6, 7})
_B_LET = 44


def _set_targets(data: bytes, ins):
    """``[(source, vtype, index, literal-or-None)]`` every variable one SET statement WRITES, read
    off the engine's own RPN stack (each operator at its TRUE arity, ``eb.exprsem.OP_SEMANTICS``):
    an assignment operator writes its LVALUE -- the operand pushed under its right-hand side -- and
    an inc/dec operator (``B_PRE/POST_PLUS/MINUS``) its one operand, so ``SC++`` is a store of SC. A
    read operand is never a target (``A B B_LET`` writes A only); a multi-assign chain writes every
    var of it (``A B C const(v) B_LET B_LET B_LET``). The literal stands only for a plain ``B_LET``
    of a constant in the statement's TRAILING assignment chain; a compound or computed store, an
    inc/dec, and an assignment INSIDE the expression (under ``&&`` or a comparison, which the engine
    may skip) are None -- a definition of unknown value. Member-list stores and 0xD3 lvalues name no
    Global var. A token the walk cannot size ends it; then a var-led statement holding a write
    operator still names its lead var (None), so an unsized store is never invisible."""
    from .eb.cfg import _ASSIGN_ALL
    writes, sound = _rpn_writes(data, ins)
    out = list(writes)
    if not sound and any(t in _ASSIGN_ALL or t in _INCDEC for t in _set_ops(data, ins)):
        b0 = data[ins.off + 1] if ins.off + 1 < ins.end else 0
        if 0xC0 <= b0 and b0 != 0xD3:
            idx = (data[ins.off + 2] | (data[ins.off + 3] << 8)) if b0 >= 0xE0 else data[ins.off + 2]
            lead = (b0 & 3, (b0 >> 2) & 7, idx)
            if not any((s_, v_, i_) == lead for (s_, v_, i_, _l) in out):
                out.append((*lead, None))
    return out


def _rpn_writes(data: bytes, ins) -> tuple:
    """:func:`_set_targets`' stack walk: ``([(source, vtype, index, literal-or-None)], sound)`` --
    ``sound`` False when a token could not be sized or an operator underflowed the stack."""
    from .eb._exprtable import EXPR_OP_NAMES
    from .eb.cfg import _ASSIGN_ALL
    from .eb.exprsem import OP_SEMANTICS
    stack: list = []
    ops: list = []
    writes: list = []
    pos, limit = ins.off + 1, ins.end
    sound = True
    while pos < limit:
        o = data[pos]
        pos += 1
        if o == 0x7F:
            break
        if o == 0xD3:                  # flexible varfunc (u16 id + u8 argc): args popped, a value pushed
            argc = data[pos + 2] if pos + 2 < limit else 0
            pos += 3
            if len(stack) < argc:
                sound = False
                break
            del stack[len(stack) - argc:]
            stack.append(None)
        elif o == 0x7D:
            v = data[pos] | (data[pos + 1] << 8)
            stack.append(("c", v - 0x10000 if v >= 0x8000 else v))
            pos += 2
        elif o == 0x7E:
            stack.append(("c", int.from_bytes(data[pos:pos + 4], "little")))
            pos += 4
        elif o >= 0xC0:
            idx = (data[pos] | (data[pos + 1] << 8)) if o >= 0xE0 else data[pos]
            pos += 2 if o >= 0xE0 else 1
            stack.append(("v", o & 3, (o >> 2) & 7, idx))
        elif o in (0x29, 0x5F, 0x79, 0x7A):
            pos += 1
            stack.append(None)
        elif o == 0x78:
            pos += 2
            stack.append(None)
        else:
            name = EXPR_OP_NAMES.get(o)
            if name is None or name not in OP_SEMANTICS or len(stack) < OP_SEMANTICS[name][0]:
                sound = False
                break
            n = OP_SEMANTICS[name][0]
            args = stack[len(stack) - n:]
            del stack[len(stack) - n:]
            res = None
            if o in _INCDEC or (o in _ASSIGN_ALL and n == 2):
                lv = args[0]
                if lv is not None and lv[0] == "v":
                    const = o == _B_LET and args[1] is not None and args[1][0] == "c"
                    lit = args[1][1] if const else None
                    writes.append((lv[1], lv[2], lv[3], lit, len(ops)))
                if o == _B_LET and args[1] is not None and args[1][0] == "c":
                    res = args[1]              # B_LET pushes its value: a chain passes the literal on
            # a member-list store (B_*_LET_A / _E, arity 3) writes a party member's field (putv),
            # never gEventGlobal: no Global lvalue
            ops.append(o)
            stack.append(res)
    out = []
    for (s_, v_, i_, lit, k) in writes:
        trailing = all(t in _ASSIGN_ALL for t in ops[k + 1:])
        out.append((s_, v_, i_, lit if trailing else None))
    return out, sound


def _bit_value_of(vtype: int, index: int, lit, bit: int):
    """The value a literal store of this width leaves in *bit* (None: a computed value). A bit store
    sets the bit for ANY nonzero value (EBin.cs setVarOperation: ``value == 0`` clears, else sets)."""
    from .eb.cfg import _var_bit_range
    lo, _hi = _var_bit_range(vtype, index)
    if lit is None:
        return None
    if vtype in (0, 1):
        return int(lit != 0)
    return (int(lit) >> (bit - lo)) & 1


def _bit_defs(eb: EbScript, fl, bits, dead=frozenset()) -> dict:
    """``{bit: {block: [(off, value | None)]}}`` every store in the function that can change one of
    *bits*: a Global bit store, and any wider Global store overlapping it (its literal decides the
    bit; a computed or compound one is an unknown definition, None). Blocks in *dead* are skipped."""
    from .eb.cfg import _var_bit_range
    out: dict = {b: {} for b in bits}
    for blk in fl.blocks:
        if not fl._dom[blk.index] or blk.index in dead:
            continue
        for ins in blk.instrs:
            if ins.op != OP_SET:
                continue
            here: dict = {}                    # one definition per bit per statement
            for (src, vt, idx, lit) in _set_targets(eb.data, ins):
                if src != 0 or vt is None or idx is None:
                    continue
                lo, hi = _var_bit_range(vt, idx)
                for b in bits:
                    if lo <= b <= hi:
                        v = _bit_value_of(vt, idx, lit, b)
                        here[b] = v if b not in here or here[b] == v else None
            for b, v in here.items():
                out[b].setdefault(blk.index, []).append((ins.off, v))
    for d in out.values():
        for v in d.values():
            v.sort(key=lambda t: t[0])
    return out


def _heads(fl, block: int) -> set:
    """The blocks dominating *block* (itself excluded): the edge back into one of them ends the
    advance's run -- a dispatch loop's head waits for the next case (Dali's 352 e17 t1)."""
    return {d for d in range(len(fl.blocks)) if d != block and fl._dom[block] >> d & 1}


def _reaching_at(fl, defs: dict, block: int, off: int) -> set:
    """Reaching definitions of one bit AT instruction *off* (the function entry carries
    ``_ENTRY_DEF``): every path from the entry, loops included (a worklist fixpoint)."""
    IN: dict = {fl.entry: {_ENTRY_DEF}}
    OUT: dict = {}
    work = [fl.entry]
    while work:
        x = work.pop()
        ds = defs.get(x, ())
        o = {("def",) + ds[-1]} if ds else set(IN.get(x, ()))
        if OUT.get(x) == o:
            continue
        OUT[x] = o
        for (s, _c) in fl.blocks[x].succs:
            cur = IN.setdefault(s, set())
            if not o <= cur or s not in OUT:
                cur |= o
                work.append(s)
    ds = [d for d in defs.get(block, ()) if d[0] < off]
    return {("def",) + ds[-1]} if ds else set(IN.get(block, ()))


def _handback(fl, defs: dict, block: int, off: int, at: set) -> set:
    """Reaching definitions where the run through the store at *off* ENDS: every function exit it
    reaches, and every edge back into a block dominating the store's (:func:`_heads`) or into the
    store's own block. ``at`` is the value set at the store."""
    heads = _heads(fl, block)
    IN: dict = {"V": {("at",)}}
    OUT: dict = {}
    hb: set = set()
    work = ["V"]
    while work:
        x = work.pop()
        b = block if x == "V" else x
        ds = [d for d in defs.get(b, ()) if x != "V" or d[0] > off]
        o = {("def",) + ds[-1]} if ds else set(IN.get(x, ()))
        if OUT.get(x) == o:
            continue
        OUT[x] = o
        ss = [s for (s, _c) in fl.blocks[b].succs]
        if not ss:
            hb |= o
        for s in ss:
            if s in heads or s == block:
                hb |= o
                continue
            cur = IN.setdefault(s, set())
            if not o <= cur or s not in OUT:
                cur |= o
                work.append(s)
    res: set = set()
    for d in hb:
        res |= at if d == ("at",) else {d}
    return res


def _run_instrs(fl, block: int, off: int) -> list:
    """Every instruction the run through the store at *off* can execute before it hands back: the
    rest of the store's block, then every block :func:`_handback` walks (up to each function exit and
    each edge back into a block dominating the store's, or into the store's own block)."""
    heads = _heads(fl, block)
    out = [i for i in fl.blocks[block].instrs if i.off > off]
    seen, st = {block}, [block]
    while st:
        x = st.pop()
        for (s, _c) in fl.blocks[x].succs:
            if s in heads or s in seen:
                continue
            seen.add(s)
            st.append(s)
            out += fl.blocks[s].instrs
    return out


def _reach_fwd(fl, a: int, b: int) -> bool:
    """Block *b* reachable from block *a* along FORWARD edges (a back edge -- into a block that
    dominates its source -- would go round a loop: the next run of the loop, not this one)."""
    seen, st = {a}, [a]
    while st:
        x = st.pop()
        if x == b:
            return True
        for (s, _c) in fl.blocks[x].succs:
            if s not in seen and not fl._dom[x] >> s & 1:
                seen.add(s)
                st.append(s)
    return False


def _truth_at_beat(data: bytes, ins, beat: int):
    """Three-valued truth of one SET statement's condition when the scenario counter is *beat* and
    every other operand is unknown: True, False, or None (unknown). Operators take their TRUE engine
    arity (``eb.exprsem.OP_SEMANTICS``); a comparison needs both sides known; ``&&``/``&`` are false
    when either side is, ``||``/``|`` true when either side is known nonzero; anything else, and any
    token this walk cannot size, is unknown -- so a dead verdict is never guessed."""
    from .eb._exprtable import EXPR_OP_NAMES
    from .eb.exprsem import OP_SEMANTICS
    stack: list = []
    pos, limit = ins.off + 1, ins.end
    while pos < limit:
        o = data[pos]
        pos += 1
        if o == 0x7F:
            break
        if o == 0x7D:
            v = data[pos] | (data[pos + 1] << 8)
            stack.append(v - 0x10000 if v >= 0x8000 else v)
            pos += 2
        elif o == 0x7E:
            stack.append(int.from_bytes(data[pos:pos + 4], "little"))
            pos += 4
        elif o == 0xD3:                # the flexible varfunc lives INSIDE the var-token space: first
            argc = data[pos + 2]
            pos += 3
            if len(stack) < argc:
                return None
            del stack[len(stack) - argc:]
            stack.append(None)
        elif o >= 0xC0:
            idx = (data[pos] | (data[pos + 1] << 8)) if o >= 0xE0 else data[pos]
            pos += 2 if o >= 0xE0 else 1
            src, vt = o & 3, (o >> 2) & 7
            stack.append(beat if (src == 0 and vt in (6, 7) and idx == 0) else None)
        elif o in (0x29, 0x5F, 0x79, 0x7A):
            pos += 1
            stack.append(None)
        elif o == 0x78:
            pos += 2
            stack.append(None)
        else:
            name = EXPR_OP_NAMES.get(o)
            if name is None or name not in OP_SEMANTICS:
                return None
            n = OP_SEMANTICS[name][0]
            if len(stack) < n:
                return None
            args = stack[len(stack) - n:]
            del stack[len(stack) - n:]
            r = None
            if n == 2 and name in ("B_EQ", "B_NE", "B_LT", "B_GT", "B_LE", "B_GE"):
                a, b = args
                if a is not None and b is not None:
                    r = int({"B_EQ": a == b, "B_NE": a != b, "B_LT": a < b, "B_GT": a > b,
                             "B_LE": a <= b, "B_GE": a >= b}[name])
            elif n == 2 and name in ("B_ANDAND", "B_AND"):
                if 0 in args:
                    r = 0
                elif name == "B_ANDAND" and all(x is not None for x in args):
                    r = int(bool(args[0]) and bool(args[1]))
            elif n == 2 and name in ("B_OROR", "B_OR"):
                if any(x not in (None, 0) for x in args):
                    r = 1
                elif all(x == 0 for x in args):
                    r = 0
            elif n == 1 and name == "B_NOT" and args[0] is not None:
                r = int(not args[0])
            stack.append(r)
    if len(stack) != 1 or stack[0] is None:
        return None
    return bool(stack[0])


def _dead_at_beat(eb: EbScript, fl, beat: int) -> set:
    """The blocks of *fl* that cannot run when the scenario counter is *beat*: those reachable only
    through a ``SET(cond) JMP_IF/JMP_IFNOT`` edge whose condition :func:`_truth_at_beat` decides
    against it (Dali's 352 exit re-sets SC only under ``SC == 2640 && ...``)."""
    dead_edges = set()
    for blk in fl.blocks:
        if len(blk.instrs) < 2 or blk.instrs[-1].op not in (0x02, 0x03) or blk.instrs[-2].op != OP_SET:
            continue
        t = _truth_at_beat(eb.data, blk.instrs[-2], beat)
        if t is None:
            continue
        jmp = blk.instrs[-1]
        succ = [s for (s, _c) in blk.succs]
        fall = [s for s in succ if fl.blocks[s].start == jmp.end]
        other = [s for s in succ if fl.blocks[s].start != jmp.end]
        if len(fall) != 1 or len(other) != 1:
            continue                              # a jump onto the next instruction: no fork
        true_s, false_s = (fall[0], other[0]) if jmp.op == 0x02 else (other[0], fall[0])
        dead_edges.add((blk.index, false_s if t else true_s))
    live, st = {fl.entry}, [fl.entry]
    while st:
        x = st.pop()
        for (s, _c) in fl.blocks[x].succs:
            if (x, s) not in dead_edges and s not in live:
                live.add(s)
                st.append(s)
    return {b.index for b in fl.blocks if fl._dom[b.index] and b.index not in live}


def _stamp_byte(words: dict, byte: int):
    """The value the row's ``set_words`` stamp leaves in *byte* (each stamp a UInt16 at its byte), or
    None when no stamp covers it."""
    for b, v in words.items():
        if byte == b:
            return int(v) & 0xFF
        if byte == b + 1:
            return (int(v) >> 8) & 0xFF
    return None


def _at_the_stamp(vt: int, idx: int, lit, beat: int, words: dict) -> tuple:
    """``(hit, agrees)`` for one Global store (vtype/index/literal) run after the SC := *beat* store:
    ``hit`` the SC / stamped-word bytes it writes; ``agrees`` when it leaves every one of them at
    the beat / the stamp (a literal that re-writes SC := beat, or a stamped byte's own value)."""
    from .eb.cfg import _var_bit_range
    lo, hi = _var_bit_range(vt, idx)
    byts = set(range(lo // 8, hi // 8 + 1))
    hit = sorted(byts & ({0, 1} | {b + k for b in words for k in (0, 1)}))
    if not hit or lit is None:
        return hit, False
    for B in hit:
        want = ((beat >> 8 * B) & 0xFF) if B in (0, 1) else _stamp_byte(words, B)
        if vt in (0, 1):
            ok = int(lit != 0) == (want >> (lo % 8)) & 1
        else:
            ok = ((int(lit) >> 8 * (B - lo // 8)) & 0xFF) == want
        if not ok:
            return hit, False
    return hit, True


def _avoids(fl, frm: int, avoid: int, targets) -> bool:
    """Block *frm* reaches a block in *targets* along FORWARD edges without passing *avoid*."""
    seen, st = {frm}, [frm]
    while st:
        x = st.pop()
        if x in targets:
            return True
        for (s, _c) in fl.blocks[x].succs:
            if s == avoid or s in seen or fl._dom[x] >> s & 1:
                continue
            seen.add(s)
            st.append(s)
    return False


def advance_handback(census: dict, donors, beat: int, eb_for_donor, read_bits,
                     words=None) -> AdvanceHandback:
    """The post phase's evidence (see the section comment): for every advance function of the
    beat in the zone, each READ bit's value at the hand-back of every store, the roster the
    advance's own presence-guarded removes leave, and what its run does after the store that the
    pass refuses to model (a scene exit, a party op, a store that moves SC or a stamped word --
    *words* the row's ``set_words``). A bit is carried only when EVERY store of the beat in the zone
    hands back the same literal, and a member leaves only when EVERY advance function removes it;
    anything else is ``undetermined`` / kept (never guessed). A RemoveParty on the way to a store
    that is not a proven presence-guarded remove is named in ``roster`` (refused, never guessed)."""
    from .eblint import _LEAVE_OPS
    words = dict(words or {})
    rep = AdvanceHandback()
    per_bit: dict = {}
    why: dict = {}
    rm: dict = {}
    fkeys = set()
    for (fid, ei, tag), offs in advance_stores(census, donors, beat).items():
        fkeys.add((fid, ei, tag))
        eb = eb_for_donor(fid)
        fn = next((f for f in eb.entries[ei].funcs if f.tag == tag), None)
        try:
            if fn is None:                     # the census names a function this script lacks
                raise CfgError(f"{fid} e{ei} has no tag {tag}")
            fl = FuncFlow.build(eb.data, fn.abs_start, fn.abs_end)
        except CfgError:
            for b in read_bits:
                per_bit.setdefault(b, []).append(None)
            continue
        rep.stores += [(fid, ei, tag, o - fn.abs_start) for o in offs]
        defs = _bit_defs(eb, fl, set(read_bits))
        in_run: set = set()
        for off in offs:
            blk = fl.block_at(off)
            for ins in _run_instrs(fl, blk, off):
                in_run.add(ins.off)
                site = f"{fid} e{ei} t{tag} +{ins.off - fn.abs_start}"
                if ins.op in _LEAVE_OPS:
                    rep.leaves.append(f"{site} (op 0x{ins.op:02X})")
                elif ins.op in (REMOVE_PARTY_OP, _PARTY_MENU_OP, _PARTY_RESERVE_OP) or (
                        ins.op == OP_SET and _PARTYADD_TOKEN in set(_set_ops(eb.data, ins))):
                    rep.tail_party.append(site if ins.op in (OP_SET, REMOVE_PARTY_OP)
                                          else f"{site} (op 0x{ins.op:02X})")
                elif ins.op == OP_SET and ins.off not in offs:      # the beat's own stores aside
                    # the hand-over is at the beat and the row's stamped words: a store after the
                    # SC := beat store that moves either is the exit's clash on the advance's side
                    for (src, vt, idx, lit) in _set_targets(eb.data, ins):
                        if src != 0 or vt is None:
                            continue
                        hit, agrees = _at_the_stamp(vt, idx, lit, beat, words)
                        if hit:
                            (rep.tail_agree if agrees else rep.tail_writes).append(
                                f"{site} writes byte(s) {hit}"
                                + (f" := {lit}" if lit is not None else " (not one literal)"))
            for b, d in defs.items():
                if not d:
                    # this advance function never writes the bit: its store hands it back as it
                    # came in, so no other advance function's literal may stand for it
                    per_bit.setdefault(b, []).append(_ENTRY_DEF)
                    continue
                hb = _handback(fl, d, blk, off, _reaching_at(fl, d, blk, off))
                if hb == {_ENTRY_DEF}:
                    # only the value the function was entered with reaches this hand-back (its
                    # writes of the bit lie on other paths): the store hands it back as it came in
                    per_bit.setdefault(b, []).append(_ENTRY_DEF)
                    continue
                vals = {x[2] for x in hb if x != _ENTRY_DEF}
                ok = _ENTRY_DEF not in hb and len(vals) == 1 and None not in vals
                per_bit.setdefault(b, []).append(next(iter(vals)) if ok else None)
                why.setdefault(b, []).append(
                    f"{fid} e{ei} t{tag} +" + ",+".join(
                        str(x[1] - fn.abs_start) for x in sorted(hb - {_ENTRY_DEF}))
                    + f" -> store +{off - fn.abs_start}"
                    + (" (+ the value it was entered with)" if _ENTRY_DEF in hb else ""))
        # the roster: RemoveParty(c) as the first instruction of the TRUE arm of
        # `if PARTYCHK(c)`, the check dominating every store, the remove reaching every store. Any
        # other RemoveParty on the way to a store (unguarded, guarded by something else, a computed
        # member) changes the roster in a way this pass does not model: named, and refused
        sblocks = [fl.block_at(o) for o in offs]
        for blk in fl.blocks:
            if not fl._dom[blk.index]:
                continue
            for k, ins in enumerate(blk.instrs):
                if ins.op != REMOVE_PARTY_OP or ins.off in in_run:
                    continue                           # a remove after the store is tail_party's
                site = f"{fid} e{ei} t{tag} +{ins.off - fn.abs_start}"
                if not any(_reach_fwd(fl, blk.index, sb) and (sb != blk.index or ins.off < o)
                           for sb, o in zip(sblocks, offs)):
                    continue                           # never on the way to a store of this beat
                c = int(ins.args[0]) if ins.args and not any(ins.arg_is_expr) else None
                preds = set(blk.preds)
                p = fl.blocks[next(iter(preds))] if len(preds) == 1 else None
                guarded = (k == 0 and c is not None and p is not None and len(p.instrs) >= 2
                           and p.instrs[-1].op == 0x02 and p.instrs[-1].end == blk.start
                           and p.instrs[-2].op == OP_SET
                           and eb.data[p.instrs[-2].off:p.instrs[-2].end]
                           == b"\x05\x7d" + c.to_bytes(2, "little") + b"\x6b\x7f")
                dom = guarded and all(fl._dom[sb] >> p.index & 1 for sb in sblocks)
                reach = all(_reach_fwd(fl, blk.index, sb) for sb in sblocks)
                if not (guarded and dom and reach):
                    rep.roster.append(f"{site} RemoveParty({'a computed member' if c is None else c})"
                                      + ("" if guarded else " not behind its own `if PARTYCHK`"))
                    continue
                rm.setdefault(c, []).append((True, site, blk.index, sblocks, fl, eb, fn,
                                             (fid, ei, tag)))
    for c, rows in rm.items():
        # a member leaves only when EVERY advance function of the beat proves the remove (one that
        # never removes it -- a second advance room -- hands back a roster that still holds it)
        if {r[7] for r in rows} != fkeys:
            continue
        undone = False
        for (_ok, site, rb, sblocks, fl, eb, fn, _k) in rows:
            add = b"\x7d" + c.to_bytes(2, "little") + b"\x6d"
            for blk in fl.blocks:
                if not fl._dom[blk.index]:
                    continue
                for ins in blk.instrs:
                    if ins.op != OP_SET or add not in eb.data[ins.off:ins.end]:
                        continue
                    # a re-add BETWEEN the remove and the store: after the remove, before a store
                    if not (_reach_fwd(fl, rb, blk.index)
                            and all(_reach_fwd(fl, blk.index, sb) for sb in sblocks)):
                        continue
                    # it cancels when every path from the remove to a store passes it -- it
                    # dominates every store, or post-dominates the remove on the way there (the
                    # re-add in the remove's own block, or the remove cannot reach a store without
                    # it); otherwise it is conditional, ASSUMED NOT TAKEN (the survivor fallback)
                    if (all(fl._dom[sb] >> blk.index & 1 for sb in sblocks) or blk.index == rb
                            or not _avoids(fl, rb, blk.index, set(sblocks))):
                        undone = True                  # an unconditional re-add: c is back
                    else:
                        rep.readds.append((c, f"{site.rsplit(' +', 1)[0]} +{ins.off - fn.abs_start}"))
        if not undone:
            rep.removed[c] = [r[1] for r in rows]
    for b, vs in sorted(per_bit.items()):
        if all(v == _ENTRY_DEF for v in vs):
            continue                           # no advance function writes it: the pre-phase value
        if all(v is not None and v != _ENTRY_DEF and v == vs[0] for v in vs):
            rep.bits[b] = (vs[0], why.get(b, []))
        else:
            rep.undetermined.append(b)
    return rep


def exit_fold(eb: EbScript, g_entry: int, to: int, entrance: int, beat: int, bits,
              stamped_bytes, *, label: str = "") -> tuple:
    """What the advance room's EXIT writes on its way to ``Field(to)`` at *entrance* (region entry
    *g_entry*): ``(vals, why, clash, dead)``. ``vals`` {bit: value | None | _KEEP} per bit in *bits*
    (``_KEEP``: only the value the exit was entered with reaches the Field -- the hand-back stands;
    None: no single literal). ``clash`` [why] for a store of SC (bytes 0-1) or of a *stamped_bytes*
    byte that can run before that Field at this beat -- the hand-over would not be at *beat* / the
    stamped word. ``dead`` [why] such stores that cannot run at *beat* (dropped, not guessed).
    Blocks :func:`_dead_at_beat` proves unreachable at SC == *beat* are dropped (Dali's 352 exit
    re-sets SC only under ``SC == 2640 && ...``). A warp that is itself dead is skipped: whether
    any warp is left is :func:`_exit_is_live`'s question."""
    from .eventscan import FIELD_OP, _entrance_at
    from .eb.cfg import _var_bit_range
    vals: dict = {}
    why: dict = {}
    clash: list = []
    dead_notes: list = []
    e = eb.entries[g_entry]
    for fn in e.funcs:
        entr = 0
        for ins in eb.instrs(fn):
            if ins.op == OP_SET:
                v = _entrance_at(eb.data, ins.off)
                if v is not None:
                    entr = v
                continue
            if ins.op != FIELD_OP or ins.imm(0) != to or entr != entrance:
                continue
            try:
                fl = FuncFlow.build(eb.data, fn.abs_start, fn.abs_end)
            except CfgError as err:
                clash.append(f"{label} e{g_entry} t{fn.tag} does not decode soundly ({err})")
                continue
            dead = _dead_at_beat(eb, fl, beat)
            fb = fl.block_at(ins.off)
            if fb in dead:
                continue
            fwd = fl._fwd_reach()
            here = f"{label} e{g_entry} t{fn.tag}"
            for blk in fl.blocks:
                if not fl._dom[blk.index] or not (fwd[blk.index] >> fb & 1):
                    continue
                for i2 in blk.instrs:
                    if i2.op != OP_SET or (blk.index == fb and i2.off >= ins.off):
                        continue
                    for (src, vt, idx, _lit) in _set_targets(eb.data, i2):
                        if src != 0 or vt is None or idx is None:
                            continue
                        lo, hi = _var_bit_range(vt, idx)
                        byts = set(range(lo // 8, hi // 8 + 1))
                        hit = byts & ({0, 1} | set(stamped_bytes))
                        if not hit:
                            continue
                        w = f"{here} +{i2.off - fn.abs_start} writes byte(s) {sorted(hit)}"
                        if blk.index in dead:
                            dead_notes.append(w + f" (dead at SC {beat}: every path to it tests "
                                                  f"SC against a value {beat} fails)")
                        else:
                            clash.append(w)
            defs = _bit_defs(eb, fl, set(bits), dead)
            for b in bits:
                R = _reaching_at(fl, defs.get(b, {}), fb, ins.off)
                if R == {_ENTRY_DEF}:
                    r = _KEEP
                else:
                    lits = {x[2] for x in R if x != _ENTRY_DEF}
                    r = (next(iter(lits)) if _ENTRY_DEF not in R and len(lits) == 1
                         and None not in lits else None)
                    why.setdefault(b, []).append(
                        f"the exit {here} +" + ",+".join(
                            str(x[1] - fn.abs_start) for x in sorted(R - {_ENTRY_DEF}))
                        + f" before Field({to}) +{ins.off - fn.abs_start}"
                        + (" (+ the value it was entered with)" if _ENTRY_DEF in R else ""))
                if b in vals and vals[b] != r:
                    r = None                     # two Field(to) paths disagree
                vals[b] = r
    return vals, why, clash, dead_notes


def _exit_is_live(eb: EbScript, g_entry: int, to: int, entrance: int, beat: int) -> bool:
    """True when the region entry *g_entry* holds a ``Field(to)`` at *entrance* that can run when the
    scenario counter is *beat* (the same warp reading as :func:`exit_fold`). False when every such warp
    sits in code :func:`_dead_at_beat` rules out: at this beat the player cannot leave through this
    exit into *to*, so it hands nothing over. An undecodable function counts as live (exit_fold
    refuses it as a clash)."""
    from .eventscan import FIELD_OP, _entrance_at
    for fn in eb.entries[g_entry].funcs:
        entr = 0
        for ins in eb.instrs(fn):
            if ins.op == OP_SET:
                v = _entrance_at(eb.data, ins.off)
                if v is not None:
                    entr = v
                continue
            if ins.op != FIELD_OP or ins.imm(0) != to or entr != entrance:
                continue
            try:
                fl = FuncFlow.build(eb.data, fn.abs_start, fn.abs_end)
            except CfgError:
                return True
            if fl.block_at(ins.off) not in _dead_at_beat(eb, fl, beat):
                return True
    return False


def _sites(xs, n: int = 3) -> str:
    """The first *n* distinct sites of a refusal, and how many more."""
    u = list(dict.fromkeys(xs))
    return ", ".join(u[:n]) + (f" (+{len(u) - n} more)" if len(u) > n else "")


def _post_advance(census, zone, members, entry, entrance, beat, eb_for_donor, read_bits,
                  set_bits, words, party) -> tuple:
    """The post phase for :func:`hub_journey_toml`: validates the hand-over and returns
    ``(new_bits, removed, notes)`` -- ``new_bits`` {bit: value} to stamp over the pre-phase row."""
    from . import eventscan
    from .content.party import CHAR_OLD_INDEX
    if entrance is None:
        raise ValueError("--after-advance needs --entrance: the hand-over is an exit gateway, and "
                         "the entrance it writes selects the entry's arrival")
    hb = advance_handback(census, zone, beat, eb_for_donor, read_bits, words)
    if not hb.stores:
        raise ValueError(f"--after-advance: no member donor writes SC := {beat} (the zone's "
                         f"ladder lists the beats its own scripts advance to: story-seed --chain)")
    adv = sorted({s[0] for s in hb.stores})
    edon = next((d for (m, d) in members if m == entry), None)
    if edon in adv:
        raise ValueError(f"--after-advance: entry {entry} is the advance room {edon} itself -- stock "
                         f"hands control back IN PLACE after SC := {beat} (no Field() enters that "
                         f"room at the hand-back); enter behind one of its exit gateways")
    if hb.leaves:
        raise ValueError(f"--after-advance: the advance's own run leaves the scene after SC := "
                         f"{beat} ({_sites(hb.leaves)}) -- that scripted exit IS stock's "
                         f"hand-over, which the post phase does not model")
    if hb.tail_party:
        raise ValueError(f"--after-advance: the advance changes the party after SC := {beat} "
                         f"({_sites(hb.tail_party)}) -- the roster at the hand-back is not "
                         f"modelled")
    if hb.roster:
        raise ValueError(f"--after-advance: the advance changes the roster on its way to SC := {beat} "
                         f"({_sites(hb.roster)}) -- only `if PARTYCHK(c) RemoveParty(c)` on every "
                         f"path to the store is modelled")
    if hb.tail_writes:
        raise ValueError(f"--after-advance: the advance's own run re-sets the scenario or a stamped "
                         f"word after SC := {beat} ({_sites(hb.tail_writes)}) -- the hand-over is "
                         f"not at this beat's stamp")
    exits = sorted({(d, g["entry"], g["entrance"]) for d in adv
                    for g in eventscan.scan_gateways(eb_for_donor(d).data) if g["to"] == edon})
    if edon is None or not exits:
        raise ValueError(f"--after-advance: entry {entry} (donor {edon}) is not behind an exit "
                         f"gateway of the advance room {adv} -- the only hand-overs the post phase "
                         f"models; a deeper entry needs the route's own writes")
    gws = sorted({x[2] for x in exits})
    if entrance not in gws:
        raise ValueError(f"--after-advance: entry {entry} is reached by the advance room's exit "
                         f"with entrance {gws}, not {entrance}; pass --entrance {gws[0]} (the "
                         f"hand-over writes it)")
    stamped = {b + k for b in words for k in (0, 1)}
    notes = [f"# POST-ADVANCE: the entry lies after the SC := {beat} store hands back ("
             + ", ".join(f"{f} e{e} t{t} +{o}" for (f, e, t, o) in hb.stores)
             + f"), through the exit into {edon} at entrance {entrance}"]
    notes += [f"# the advance's run re-writes the beat / a stamped word at its own value: {w}"
              for w in dict.fromkeys(hb.tail_agree)]
    finals: dict = {}
    fwhy: dict = {b: list(w) for b, (_v, w) in hb.bits.items()}
    by_exit: set = set()                 # bits an exit's own write decides (its sites replace the advance's)
    dead_exits: list = []                # exits whose Field(entry) cannot run at this beat
    live_exits = 0
    for (d, gi, _ent) in [x for x in exits if x[2] == entrance]:
        vals, ewhy, clash, dead = exit_fold(eb_for_donor(d), gi, edon, entrance, beat, read_bits,
                                            stamped, label=str(d))
        if clash:
            raise ValueError(f"--after-advance: the exit re-sets the scenario or a stamped word "
                             f"before Field({edon}) at SC {beat} ({'; '.join(clash)}) -- the "
                             f"hand-over is not at this beat's stamp")
        if not _exit_is_live(eb_for_donor(d), gi, edon, entrance, beat):
            dead_exits.append(f"{d} e{gi}")
            continue                     # no hand-over through this exit at this beat
        live_exits += 1
        notes += [f"# dead at the hand-over: {w}" for w in dead]
        for b in read_bits:
            r = vals.get(b, _KEEP)
            if r == _KEEP:
                r = (hb.bits[b][0] if b in hb.bits else
                     None if b in hb.undetermined else "pre")
            else:
                if b not in by_exit:
                    fwhy[b] = []
                    by_exit.add(b)
                fwhy[b].extend(ewhy.get(b, []))
            if b in finals and finals[b] != r:
                r = None
            finals[b] = r
    if not live_exits:
        raise ValueError(f"--after-advance: the exit into {edon} at entrance {entrance} "
                         f"({', '.join(dead_exits)}) reaches Field({edon}) only through code that "
                         f"cannot run at SC {beat} -- no hand-over through it at this beat")
    new_bits: dict = {}
    und = []
    for b, v in sorted(finals.items()):
        if v == "pre":
            continue
        if v is None:
            und.append(b)
            continue
        pre = set_bits.get(b, 0)
        tail = "" if v != pre else f" (the pre-phase row already leaves it {v})"
        notes.append(f"# bit {b} = {v} at the hand-over: {'; '.join(fwhy.get(b, []))}{tail}")
        if v != pre:
            new_bits[b] = v
    removed: list[str] = []
    for c, sites in sorted(hb.removed.items()):
        nm = CHAR_OLD_INDEX.get(c, f"char{c}").lower()
        removed.append(nm)
        notes.append(f"# {nm} leaves: the advance's `if PARTYCHK({c}) RemoveParty({c})` at "
                     f"{', '.join(sites)}")
    for c, site in hb.readds:
        nm = CHAR_OLD_INDEX.get(c, f"char{c}").lower()
        if nm in removed:
            notes.append(f"# ASSUMED NOT TAKEN: the conditional re-add of {nm} at {site}")
    if removed and not (party - set(removed)):
        raise ValueError(f"--after-advance: the advance's removes ({', '.join(removed)}) leave no "
                         f"member of the derived party {sorted(party)} -- the survivor fallback "
                         f"would re-add one, which the post phase does not model")
    # a bit with no single literal at the hand-over keeps the PRE-PHASE row's value: say which of
    # them the row still stamps (resolve() set it) and which it leaves clear
    kept = [b for b in und if set_bits.get(b) == 1]
    gone = [b for b in und if set_bits.get(b) != 1]
    if kept:
        notes.append(f"# kept at the pre-phase value 1 (no single literal at the hand-over): "
                     f"bits {kept}")
    if gone:
        notes.append(f"# not carried (no single literal at the hand-over): bits {gone}")
    return new_bits, removed, notes


def _behind_advance_exit(census, zone, members, entry, entrance, beat, eb_for_donor) -> bool:
    """True when (entry, entrance) is an exit gateway of a room that writes SC := *beat* and that
    exit's warp can run at the beat (:func:`_exit_is_live`): the entry lies AFTER the advance,
    whatever phase the row claims. An exit whose warp into the entry is dead at the beat hands
    nothing over there, so it does not put the entry past the advance (the post phase refuses it
    for the same reason)."""
    from . import eventscan
    adv = sorted({k[0] for k in advance_stores(census, zone, beat)})
    edon = next((d for (m, d) in members if m == entry), None)
    if edon is None or edon in adv:
        return False
    return any(g["to"] == edon and g["entrance"] == entrance
               and _exit_is_live(eb_for_donor(d), g["entry"], edon, entrance, beat)
               for d in adv for g in eventscan.scan_gateways(eb_for_donor(d).data))


def hub_row_slug(chain_dir: str, beat: int, *, entrance: int | None = None,
                 after_advance: bool = False, pre_phase_control: bool = False) -> str:
    """A generated journey row's id: ``<chain>_<beat>``, plus what makes the row distinct -- the
    entrance, and the phase (``_post`` / ``_control``) -- so a post-phase or control row never
    REPLACES a frozen pre-phase row of the same chain and beat (:func:`update_hub_journeys` is
    marker-keyed by it). A plain row keeps its historical id byte for byte."""
    return (f"{os.path.basename(os.path.normpath(chain_dir))}_{beat}"
            + (f"_e{int(entrance)}" if entrance is not None else "")
            + ("_post" if after_advance else "")
            + ("_control" if pre_phase_control else ""))


def hub_journey_toml(chain_dir: str, beat: int, census: dict, eb_for_donor, *,
                     entry: int, slug: str | None = None, name: str | None = None,
                     entrance: int | None = None, after_advance: bool = False,
                     pre_phase_control: bool = False) -> str:
    """A ``[[journey]]`` row for the World Hub (``gen-hub``) carrying the CHAIN'S WHOLE derived
    seed -- the hub-format answer to beat seeding (round 7): the journey PICK stamps scenario +
    flags + words + party hub-side and then warps, so the members stay pure verbatim forks and
    in-journey progression is never re-stamped at a door. The seed is the UNION over members of
    the same per-member derivations ``seed_chain`` used to emit (bit resolution is global, so
    the union is consistent; the ATE words derive zone-wide; the party is the windowed union).
    THE SEED IS THE HAND-OVER STATE OF THE ENTRY: with ``after_advance`` the entry lies behind an
    exit of the beat's own advance room and the row also carries what the advance and that exit
    leave (the post phase, :func:`_post_advance`); without it the row is the pre-advance row, and an
    ``entrance`` that IS such an exit is refused unless ``pre_phase_control`` asks for it. ``slug``
    defaults to :func:`hub_row_slug` (the entrance and the phase in the id, as the CLI's)."""
    members = chain_donors(chain_dir)
    if not members:
        raise ValueError(f"no chain members (donor= field.tomls) under {chain_dir}")
    zone = sorted({d for (_m, d) in members})
    set_bits: dict[int, int] = {}
    words: dict[int, int] = {}
    party: set[str] = set()
    read_bits: set[int] = set()
    for _mid, donor in members:
        eb = eb_for_donor(donor)
        for v in resolve(eb, beat, census).verdicts:
            if v.decision == "set":
                set_bits[v.bit] = 1
            if v.decision != "refused":
                read_bits.add(v.bit)
        detected = ate_word_seed(eb)
        if detected:
            vals = ate_word_values(list(detected), beat, census, zone)
            for b, val in vals.items():
                if val is None and detected[b] == "cmp":
                    val = 1                      # the comparison-channel placeholder
                if val is not None:
                    words[b] = words.get(b, 0) | val
        party |= set(party_seed(eb, beat=beat, census=census, donor=donor)["add"])
    removed: list[str] = []
    notes: list[str] = []
    milestone = flagsmod.nearest_milestone(beat)[1]
    if after_advance:
        if pre_phase_control:
            raise ValueError("--pre-phase-control builds a PRE-phase row; it cannot be combined "
                             "with --after-advance")
        new_bits, removed, notes = _post_advance(census, zone, members, entry, entrance, beat,
                                                 eb_for_donor, read_bits, set_bits, words, party)
        set_bits.update(new_bits)
        party -= set(removed)
        label = name or f"{milestone} (SC {beat}, past the advance)"
    elif entrance is not None or pre_phase_control:
        if entrance is None:
            raise ValueError("--pre-phase-control needs --entrance (the advance room's exit)")
        past = _behind_advance_exit(census, zone, members, entry, entrance, beat, eb_for_donor)
        if past and not pre_phase_control:
            raise ValueError(f"entry {entry} through entrance {entrance} is an exit of the room "
                             f"that writes SC := {beat}: the entry lies AFTER the advance -- pass "
                             f"--after-advance (or --pre-phase-control for a deliberate pre-phase "
                             f"calibration row)")
        if pre_phase_control and not past:
            raise ValueError(f"--pre-phase-control: entry {entry} through entrance {entrance} is "
                             f"not an exit of the room that writes SC := {beat} -- nothing to control")
        if past:
            notes.append(f"# PRE-PHASE ROW ENTERED PAST THE ADVANCE -- a calibration control: the "
                         f"SC := {beat} advance's own writes (latches, removes) are NOT carried")
            label = name or f"{milestone} (SC {beat}, pre-phase control)"
        else:
            label = name or f"{milestone} (SC {beat}, entrance {int(entrance)})"
    else:
        label = name or f"{milestone} (SC {beat})"
    from .hub import _q      # the hub's own TOML escape: a quote or backslash in a --name stays a string
    slug = slug or hub_row_slug(chain_dir, beat, entrance=entrance, after_advance=after_advance,
                                pre_phase_control=pre_phase_control)
    L = ["[[journey]]",
         f'id    = "{_q(slug)}"',
         f'name  = "{_q(label)}"',
         f"entry = {entry}"]
    if entrance is not None:
        L.append(f"entrance = {int(entrance)}")
    L.append(f"set_scenario = {beat}")
    if set_bits:
        rows = ", ".join("{ flag = %d, value = %d }" % (b, v) for b, v in sorted(set_bits.items()))
        L.append(f"set_flags = [ {rows} ]")
    if words:
        rows = ", ".join("{ byte = %d, value = %d }" % (b, v) for b, v in sorted(words.items()))
        L.append(f"set_words = [ {rows} ]")
    if party:
        L.append("party_add = [ " + ", ".join(f'"{n}"' for n in sorted(party)) + " ]")
    if removed:
        L.append("party_remove = [ " + ", ".join(f'"{n}"' for n in sorted(removed)) + " ]")
    L += notes
    return "\n".join(L)


def update_hub_journeys(journeys_path: str, row_toml: str, slug: str) -> None:
    """Insert (or replace, marker-delimited by *slug*) one generated ``[[journey]]`` row in a
    ``journeys.toml``. The ``[hub]`` presentation table stays the author's; only the marked
    generated rows are touched."""
    begin = f'# --- story-seed journey "{slug}" (generated; re-run story-seed --hub to refresh) ---'
    end = f'# --- end story-seed journey "{slug}" ---'
    text = open(journeys_path, encoding="utf-8").read()
    block = f"{begin}\n{row_toml}\n{end}\n"
    if begin in text and end in text:
        pre = text[:text.index(begin)]
        post = text[text.index(end) + len(end):].lstrip("\n")
        text = pre + block + post
    else:
        if not text.endswith("\n"):
            text += "\n"
        text += "\n" + block
    with open(journeys_path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def strip_chain_seeds(chain_dir: str) -> list[tuple[str, int, int]]:
    """Remove the generated ``# story-seed`` block from every member field.toml under
    *chain_dir* -- the members become pure verbatim forks (retarget maps only) and ALL story
    state comes from the hub journey pick. Returns ``[(path, member_id, donor_id)]`` for the
    members that had a seed to strip."""
    import glob
    import re
    out = []
    for p in sorted(glob.glob(os.path.join(chain_dir, "**", "*.field.toml"), recursive=True)):
        text = open(p, encoding="utf-8").read()
        m_donor = re.search(r"^donor\s*=\s*(\d+)", text, re.M)
        m_id = re.search(r"^id\s*=\s*(\d+)", text, re.M)
        if not m_donor or not m_id:
            continue
        lines = text.splitlines(keepends=True)
        cut = next((i for i, l in enumerate(lines) if l.startswith("# story-seed")), None)
        if cut is None:
            continue
        base = "".join(lines[:cut])
        with open(p, "w", encoding="utf-8", newline="") as fh:
            fh.write(base)
        out.append((p, int(m_id.group(1)), int(m_donor.group(1))))
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
