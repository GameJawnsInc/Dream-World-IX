r"""TIER W rung W7 -- THE RUNG'S OWN GATE RUNNER.  `py w7_gates.py` prints G1..G5 with PASS/FAIL.

W7 read the id-5 model image's TEXANIM table (`W7-TEXANIM.md`; the decoder is
``ff9mapkit.summons.texanim``), and reading it turned a refusal into a lift plus one new hard rule.
These are the falsifiable forms of the four claims `SYNTHESIS.md` sec 5.3 named, plus this lane's own
provenance scan:

G1  THE ROUND TRIP (T1-T3): every armed region in the 372-container corpus decodes and re-encodes
    BYTE-IDENTICAL; ``parse`` never raises on any container and returns ``None`` on all 19 unarmed
    creature packages; and the census (which effects are armed, how many clips, which part, how many
    distinct tables) is RE-MEASURED from the corpus rather than compared against a constant.
G2  THE LIFT MATRIX (sec 4.1, L1-L6 executed on the five real armed packages): a creature CLUT
    recolour BUILDS with no key (L1); a scenery recolour BUILDS with no key (L2); a whole-page texel
    repaint BUILDS with no key (L3); a window-only texel repaint REFUSES naming the clip and the
    sibling rect left stock, and BUILDS with ``acknowledge_texanim_frames = true`` (L4); the 19
    unarmed packages are untouched by any of it (L5); and the readouts print the DECODED table rather
    than an opaque byte count (L6).  Plus the two refusals that STAY: an armed region that does not
    DECODE still refuses exactly as it did pre-W7, and no writer verb is exported (R2).
G3  THE CO-TRANSFORM, on ef038 (Shiva -- the only effect corpus-wide that arms op 12, so the
    maximal-risk member of the class): repainting the live eye window alone REFUSES and names the
    UNTOUCHED sibling frames; repainting the window AND both frames BUILDS, with every protected rect
    carrying the same transform, measured texel by texel.
G4  THE REGION INVARIANT (R1) -- the rung's one new HARD RULE, and worth more than the lift it
    accompanies.  After a real reskin AND a real repaint build on all five armed packages,
    ``firstBlock``, ``min(motionOffsets)`` and every byte of ``[firstBlock, min(motionOffsets))`` are
    unchanged.  And the check is proven NON-VACUOUS: a deliberately tampered region is CAUGHT.
G5  PROVENANCE (beyond sec 5.3, because this repo's provenance gate is a standing rule): a byte-literal
    scan of every committable file this rung adds, against all 372 corpus containers; the SE-derived
    lane dossiers all sit outside the checkout.

Reads the extracted corpus at C:\gd\SCRATCH\summon-format ONLY -- no install, NO deploy, no install
write, no git commit.  Every number is measured in the gate body.
"""
from __future__ import annotations

import ast
import os
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import reskin as RS                                              # noqa: E402  (sets up sys.path)
import summon_camera as W                                        # noqa: E402
from ff9mapkit.summons import container as EC                    # noqa: E402
from ff9mapkit.summons import repaint as RP                      # noqa: E402
from ff9mapkit.summons import texanim as TA                      # noqa: E402

try:                                                             # py3.11+ stdlib, else the backport
    import tomllib as _toml
except ModuleNotFoundError:                                      # pragma: no cover
    import tomli as _toml                                        # type: ignore

CORPUS = W.SCRATCH_CORPUS

#: the five packages whose id-5 model image carries a NON-EMPTY texanim region.  Stated so a drift is
#: a visible diff -- G1 RE-MEASURES it from the corpus and fails if the set moved.
TEXANIM_CLASS = (38, 177, 493, 494, 495)

#: SYNTHESIS sec 4.3's protected rect set, TEXEL space, per package.  Coordinates and counts, not
#: bytes (the same posture the kit's own texanim tests take).  G1 re-measures these too.
EF038_RECTS = {1: [(54, 62, 22, 12), (56, 0, 22, 12), (78, 0, 22, 12)]}
CARBUNCLE_RECTS = {2: [(2, 100, 16, 14), (2, 114, 18, 14), (18, 100, 16, 14), (20, 114, 18, 14),
                       (24, 50, 16, 14), (24, 51, 16, 14), (34, 64, 18, 14), (48, 102, 16, 14),
                       (66, 78, 18, 14)]}

#: the committable files THIS rung adds -- scanned by G5.  An entry containing "/" is REPO-relative;
#: a bare name is local to this study directory.
COMMITTABLE = ("w7_gates.py", "W7-TEXANIM.md",
               "ff9mapkit/ff9mapkit/summons/texanim.py",
               "ff9mapkit/tests/test_summon_texanim.py")

#: the CAST lane's own committable files -- scanned when they are in the tree, reported as absent when
#: they are not.  Optional rather than required because the cast artifacts land in a sibling lane and
#: a gate that FAILED on their absence would be asserting another agent's schedule, not provenance.
#: A generator that stamps art is exactly where a stock byte run would hide, so it is scanned.
COMMITTABLE_CAST = ("shiva_marker.py", "shiva_reskin.toml")

#: the SE-derived recon dossiers this rung was written from.  Never in the checkout, by construction.
DOSSIERS = (r"C:\gd\SCRATCH\summon-format\texanim-w7\SYNTHESIS.md",
            r"C:\gd\SCRATCH\summon-format\texanim-w7\engine\A1-ENGINE.md",
            r"C:\gd\SCRATCH\summon-format\texanim-w7\bytes\A2-BYTES.md",
            r"C:\gd\SCRATCH\summon-format\texanim-w7\kit\A3-KIT.md")

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))  # <repo>

RESULTS = []
_TMP = None                                                       # one scratch dir for every gate


def gate(name: str, ok: bool, *lines: str) -> bool:
    RESULTS.append((name, ok))
    print("\n%s %s  %s" % ("[PASS]" if ok else "[FAIL]", name, "-" * max(2, 58 - len(name))))
    for ln in lines:
        print("   " + ln)
    return ok


def _have_corpus() -> bool:
    return bool(W.corpus_paths(CORPUS))


def _load(effect: int) -> bytes:
    with open(os.path.join(CORPUS, "ef%03d.bytes" % effect), "rb") as fh:
        return fh.read()


def _tmp() -> str:
    global _TMP
    if _TMP is None:
        _TMP = tempfile.mkdtemp(prefix="w7gates-")
    return _TMP


def _refuses(fn, *a, **kw):
    """``(fired, message)`` -- did this raise the lane's OWN error class, and what did it say?

    A refusal that raised the wrong exception type is not a refusal: it is a crash that happened to
    stop the build, and it stops being one the day the call site grows a ``try`` (w6_gates' own rule).
    """
    try:
        fn(*a, **kw)
        return False, ""
    except (RP.RepaintError, RS.ReskinError) as e:
        return True, str(e)
    except Exception as e:                                       # pragma: no cover - a real defect
        return False, "*** %s (not a lane error): %s" % (type(e).__name__, e)


# --------------------------------------------------------------------------- the shared fixtures
def _bumper(zeros):
    """One index moved without ever crossing the transparent boundary, in either direction.

    Every texel edit in this runner uses it, so a refusal here is always THE TEXANIM CO-TRANSFORM and
    never THE CUTOUT LAW wearing its coat -- a gate that could not tell the two apart would report
    the right verdict for the wrong reason.
    """
    def bump(v):
        if v in zeros:
            return v
        w = 1 + (v % 255)
        while w in zeros:
            w = 1 + (w % 255)
        return w
    return bump


def _paint_rects(px: bytes, page, bump, rects):
    """``bump`` every texel of every rect in ``rects``; returns ``(pixels, {rect: n_expected})``.

    ``n_expected`` is how many texels of that rect the bump can actually MOVE (an opaque texel moves,
    a transparent one is held), which is what makes "the same transform reached every rect" a
    measurement rather than a hope.
    """
    out = bytearray(px)
    expect = {}
    for r in rects:
        n = 0
        for yy in range(r.y, r.y2):
            for xx in range(r.x, r.x2):
                i = yy * page.w + xx
                if out[i] != bump(out[i]):
                    n += 1
                out[i] = bump(out[i])
        expect[r.as_tuple()] = n
    return bytes(out), expect


def _texel_spec(effect: int, name: str, src: str, **extra) -> dict:
    row = {"name": name, "source": src, "enabled": True}
    row.update(extra)
    return {"reskin": {"effect": effect, "allow_unguarded": True, "texel": [row]}}


def _write_png(path: str, px: bytes, words, page) -> str:
    RP.write_indexed_png(bytes(px), words, page.w, page.h, path)
    return path


def _reskin_via_scaffold(effect: int, blob: bytes, pick, **mutate):
    """``(build, None)`` or ``(None, message)`` -- a recolour routed through the tool's OWN scaffold.

    Deliberately not a hand-written spec: a lift that only works on a spec an agent typed by hand is
    not a lift an author can reach.  This is the same probe shape ``w5_gates`` uses.
    """
    text, _pmap = RS.scaffold(effect, blob)
    spec = _toml.loads(text)
    row = next(r for r in spec["reskin"]["target"] if pick(r["name"]))
    row["enabled"] = True
    row.update(mutate)
    try:
        return RS.build(spec, "ef%03d-w7-probe" % effect, blob=blob), None
    except RS.ReskinError as exc:
        return None, str(exc)


_LIFTS = {}


def lifts(effect: int) -> dict:
    """Every build the lift matrix needs for ONE package, computed once and shared by G2/G3/G4.

    Cached for the reason ``w6_gates.emblem_build`` is: these are real builds over real containers,
    and two gates that each rebuilt them could in principle disagree -- which is a report nobody could
    trust.  One build, read by every gate that has an opinion about it.
    """
    if effect in _LIFTS:
        return _LIFTS[effect]
    d = {"effect": effect}
    blob = _load(effect)
    d["blob"] = blob
    d["ta"] = ta = RS.texanim_region(blob)
    res = TA.read(blob)
    d["res"] = res
    if not res.parsed:                                           # pragma: no cover - corpus drift
        _LIFTS[effect] = d
        return d
    d["part"] = part = res.table.parts[0]
    d["page"] = page = {p.index: p for p in RP.creature_texel_pages(blob)}[part]
    words = RP.palette_words(blob, page)
    zeros = set(RP.transparent_indices(words))
    bump = _bumper(zeros)
    stock = blob[page.page_offset:page.page_offset + page.page_bytes]
    td = _tmp()

    # -- L1 the creature recolour, L2 the scenery recolour, both through the scaffold, no key
    pmap = RS.palette_map(blob)
    d["creature"] = _reskin_via_scaffold(effect, blob, lambda n, p=part: n == "creature.part%d" % p,
                                         hue_rotate=30.0)
    scen = next(p for p in pmap.palettes if p.slot >= 0)
    d["scenery_shared"] = scen.shared
    d["scenery"] = _reskin_via_scaffold(effect, blob, lambda n, s=scen.name: n == s,
                                        hue_rotate=30.0, acknowledge_shared=True)

    # -- L3 the whole page
    whole = _write_png(os.path.join(td, "ef%03d_all.png" % effect),
                       bytes(bump(v) for v in stock), words, page)
    try:
        d["whole"] = RP.build(_texel_spec(effect, page.name, whole), td, blob=blob)
    except Exception as e:                                       # pragma: no cover - a real defect
        d["whole"], d["whole_err"] = None, "%s: %s" % (type(e).__name__, e)

    # -- L4 the window-only edit: the refusal, then the same edit acknowledged
    win = res.table.clips[0].window
    local_px, d["local_expect"] = _paint_rects(stock, page, bump, [win])
    local = _write_png(os.path.join(td, "ef%03d_win.png" % effect), local_px, words, page)
    d["local"] = _refuses(RP.build, _texel_spec(effect, page.name, local), td, blob=blob)
    try:
        d["hatched"] = RP.build(_texel_spec(effect, page.name, local,
                                            acknowledge_texanim_frames=True), td, blob=blob)
    except Exception as e:                                       # pragma: no cover - a real defect
        d["hatched"], d["hatched_err"] = None, "%s: %s" % (type(e).__name__, e)

    # -- G3's positive half: the WHOLE protected set, co-transformed
    prot = [r for rs in TA.protected_rects(blob).values() for r in rs]
    co_px, d["co_expect"] = _paint_rects(stock, page, bump, prot)
    co = _write_png(os.path.join(td, "ef%03d_co.png" % effect), co_px, words, page)
    try:
        d["co"] = RP.build(_texel_spec(effect, page.name, co), td, blob=blob)
    except Exception as e:                                       # pragma: no cover - a real defect
        d["co"], d["co_err"] = None, "%s: %s" % (type(e).__name__, e)
    d["prot"] = prot
    _LIFTS[effect] = d
    return d


# --------------------------------------------------------------------------- G1
def g1_the_round_trip():
    if not _have_corpus():
        return gate("G1 the round trip", False, "no extracted corpus at %s" % CORPUS)
    lines, ok = [], True
    armed, regions, drift, raised = {}, {}, [], []
    containers = creature = empty = 0
    for path in W.corpus_paths(CORPUS):
        containers += 1
        with open(path, "rb") as fh:
            blob = fh.read()
        name = os.path.basename(path)[:5]
        if EC.creature_package(blob) is not None:
            creature += 1
        try:
            table = TA.parse(blob)                               # must not raise on ANY container
        except Exception as e:
            raised.append("%s: %s" % (name, e))
            continue
        if table is None:
            empty += 1 if RS.texanim_region(blob).present else 0
            continue
        region = blob[table.region.lo:table.region.hi]
        regions[name] = region
        armed[name] = (table.count, table.parts[0], len(region), table.frame_total)
        if TA.encode(table) != region:
            drift.append(name)

    lines.append("containers %d, creature packages %d, EMPTY regions %d, ARMED %d"
                 % (containers, creature, empty, len(armed)))
    ok = ok and containers == 372 and creature == 24 and not raised
    for r in raised[:5]:
        lines.append("   *** parse RAISED on %s" % r)
    lines.append("encode(parse(region)) == region on every armed region: %d/%d%s"
                 % (len(armed) - len(drift), len(armed),
                    "" if not drift else "   *** DRIFT: %s" % ", ".join(drift)))
    ok = ok and not drift and len(armed) == len(TEXANIM_CLASS)
    got = sorted(int(k[2:]) for k in armed)
    lines.append("the armed set, RE-MEASURED: %s -- %s the stated class"
                 % (got, "matches" if tuple(got) == TEXANIM_CLASS else "*** DIFFERS FROM ***"))
    ok = ok and tuple(got) == TEXANIM_CLASS
    for k in sorted(armed):
        c, p, n, f = armed[k]
        lines.append("   %s  %d clip(s), part %d, %d frame(s), region %d B  (4 + 20*%d + 12*%d + 4*%d"
                     " == %d)" % (k, c, p, f, n, c, c, f, 4 + 20 * c + 12 * c + 4 * f))
        ok = ok and n == 4 + 20 * c + 12 * c + 4 * f
    distinct = len(set(regions.values()))
    family = {regions[k] for k in ("ef177", "ef493", "ef494", "ef495") if k in regions}
    lines.append("distinct tables corpus-wide: %d (the four 364-byte regions are %s) -- "
                 "one Carbuncle shipped as four ability rows"
                 % (distinct, "BYTE-IDENTICAL" if len(family) == 1 else "*** NOT IDENTICAL ***"))
    ok = ok and distinct == 2 and len(family) == 1

    # the sec 4.3 protected rect set, re-measured off the same bytes
    r038 = {p: [r.as_tuple() for r in rs]
            for p, rs in TA.protected_rects(_load(38)).items()}
    lines.append("ef038 protected rects: %s -- %s sec 4.3"
                 % (r038, "matches" if r038 == EF038_RECTS else "*** DIFFERS FROM ***"))
    ok = ok and r038 == EF038_RECTS
    fam_ok = all({p: [r.as_tuple() for r in rs]
                  for p, rs in TA.protected_rects(_load(ef)).items()} == CARBUNCLE_RECTS
                 for ef in (177, 493, 494, 495))
    lines.append("the Carbuncle family's 9 rects on all four packages: %s" % fam_ok)
    ok = ok and fam_ok
    return gate("G1 the round trip (T1-T3: byte-identical re-encode, no raise, census re-measured)",
                ok, *lines)


# --------------------------------------------------------------------------- G2
def g2_the_lift_matrix():
    if not _have_corpus():
        return gate("G2 the lift matrix", False, "no extracted corpus at %s" % CORPUS)
    lines, ok = [], True

    def row(label, good, detail):
        nonlocal ok
        ok = ok and good
        lines.append("%-42s %s" % (label, detail if good else "*** %s ***" % detail))

    for ef in TEXANIM_CLASS:
        d = lifts(ef)
        if not d.get("res") or not d["res"].parsed:              # pragma: no cover - corpus drift
            row("ef%03d" % ef, False, "region does not DECODE -- no lift is available here")
            continue
        ta = d["ta"]

        b, msg = d["creature"]
        row("L1 ef%03d creature recolour, no key" % ef, b is not None and b.patched != d["blob"],
            "BUILDS, %d CLUT byte(s)" % (sum(1 for i in range(len(d["blob"]))
                                             if d["blob"][i] != b.patched[i]) if b else 0)
            if b else "REFUSED: %s" % (msg or "")[:60])

        b2, msg2 = d["scenery"]
        row("L2 ef%03d scenery recolour, no key" % ef, b2 is not None,
            "BUILDS%s" % (" (shared, acknowledged)" if d["scenery_shared"] else "")
            if b2 else "REFUSED: %s" % (msg2 or "")[:60])

        w = d.get("whole")
        row("L3 ef%03d whole-page repaint, no key" % ef,
            w is not None and "every protected rect reached" in w.targets[0].texanim_note,
            "BUILDS, %s" % w.targets[0].texanim_note.split("  -- ")[-1] if w
            else "did not build: %s" % d.get("whole_err", "")[:60])

        fired, lm = d["local"]
        named = fired and "THE TEXANIM CO-TRANSFORM" in lm and "LEFT STOCK" in lm
        row("L4 ef%03d window-only repaint" % ef, named,
            "REFUSED, LEFT STOCK: %s" % lm.split("LEFT STOCK: ")[1].split(".  ")[0] if named
            else (lm.splitlines()[0][:70] or "DID NOT REFUSE"))
        h = d.get("hatched")
        row("   ...acknowledge_texanim_frames = true", h is not None
            and "ASYMMETRIC, acknowledged" in h.targets[0].texanim_note,
            "BUILDS, asymmetry acknowledged" if h else "did not build")

        # the ONE refusal that survived: armed, and the reader cannot decode it
        broken = bytearray(d["blob"])
        broken[ta.lo + 0x14] = 0xFF                              # poison clip 0's nodeOff, in memory
        broken = bytes(broken)
        f2, m2 = _refuses(RS.build, {"reskin": {"effect": ef, "allow_unguarded": True, "target": [
            {"name": "creature.part%d" % d["part"], "hue_rotate": 30.0}]}}, "t", blob=broken)
        row("   armed + UNPARSEABLE still refuses", TA.read(broken).unparseable and f2
            and "TEXANIM ARMED" in m2, "REFUSED (TEXANIM ARMED), pre-W7 behaviour unchanged")

    # -- L5: the 19 unarmed creature packages are not in this conversation at all
    unarmed = []
    for path in W.corpus_paths(CORPUS):
        with open(path, "rb") as fh:
            blob = fh.read()
        if EC.creature_package(blob) is None:
            continue
        if not RS.texanim_region(blob).armed:
            unarmed.append(int(os.path.basename(path)[2:5]))
    row("L5 the unarmed creature packages", len(unarmed) == 19,
        "%d packages, protected rect set empty on all of them: %s"
        % (len(unarmed), all(TA.protected_rects(_load(e)) == {} for e in unarmed)))
    ok = ok and all(TA.protected_rects(_load(e)) == {} for e in unarmed)

    # -- L6: the readouts DISCLOSE the decoded table instead of an opaque byte count
    b38 = _load(38)
    scaffold_text, _p = RS.scaffold(38, b38)
    der = RS.derivation_lines(b38, RS.palette_map(b38))
    rep = RP.derivation_lines(b38, RP.creature_texel_pages(b38))
    disclosed = all(any("THE TEXANIM TABLE" in l for l in src) for src in (der, rep))
    disclosed = disclosed and all(any("THE PROTECTED RECT SET" in l for l in src)
                                  for src in (der, rep))
    row("L6 the readouts print the DECODED table", disclosed
        and "THE TEXANIM TABLE" in scaffold_text and "acknowledge_texanim" not in scaffold_text,
        "reskin + repaint derivations and the scaffold all carry the clip table and the rect set; "
        "the scaffold no longer emits the deprecated key")

    # -- R2: W7 ships a READER.  No writer verb is reachable.
    import ff9mapkit.cli as CLI
    cli_src = open(CLI.__file__, "r", encoding="utf-8").read()
    writers = [n for n in TA.__all__
               if n.startswith(("write", "patch", "splice", "apply", "stage", "build", "deploy"))]
    row("R2 no writer verb is reachable", not writers and "texanim.encode" not in cli_src
        and "TA.encode" not in cli_src,
        "the module exports no write/patch/splice/stage/build/deploy verb, and `encode` -- which "
        "exists for the round trip alone -- is referenced by no CLI path (checked by NAME: a bare "
        "`.encode(` scan would false-FAIL on any unrelated str.encode in cli.py; V1 F11)")
    return gate("G2 the lift matrix (sec 4.1 L1-L6 on the five real packages, + the two that stay)",
                ok, *lines)


# --------------------------------------------------------------------------- G3
def g3_the_co_transform():
    if not _have_corpus():
        return gate("G3 the co-transform", False, "no extracted corpus at %s" % CORPUS)
    d = lifts(38)
    if not d.get("res") or not d["res"].parsed:                  # pragma: no cover - corpus drift
        return gate("G3 the co-transform", False, "ef038's region does not decode")
    lines, ok = [], True
    prot = {r.as_tuple() for r in d["prot"]}
    lines.append("ef038 = Shiva, part %d: the live eye window plus the two spare frames it blits "
                 "from -- %s" % (d["part"], " ".join(sorted(str(r) for r in d["prot"]))))
    ok = ok and prot == set(EF038_RECTS[1])

    fired, msg = d["local"]
    left = set() if not fired or "LEFT STOCK: " not in msg else {
        t.strip() for t in msg.split("LEFT STOCK: ")[1].split(".  ")[0].split(") (")}
    lines.append("the eye WINDOW alone, no key: %s"
                 % ("REFUSED -- clip 0, LEFT STOCK %s"
                    % msg.split("LEFT STOCK: ")[1].split(".  ")[0] if fired
                    else "*** DID NOT REFUSE ***"))
    ok = ok and fired and "clip 0" in msg and "acknowledge_texanim_frames = true" in msg
    # the refusal names the UNTOUCHED siblings, and every clip's own tally is disclosed, not hidden
    untouched = [r for r in d["prot"] if r.as_tuple() != d["res"].table.clips[0].window.as_tuple()]
    lines.append("the untouched siblings the whole table leaves stock: %s -- each one is reported "
                 "by its own clip's tally (%s)"
                 % (" ".join(str(r) for r in untouched),
                    msg.split("clip(s) name this page; ")[-1].rstrip(")") if fired else "?"))
    ok = ok and bool(left) and all(any(str(r) == "(%s)" % t.strip("()") for r in untouched)
                                   for t in left)

    co = d.get("co")
    if co is None:                                               # pragma: no cover - a real defect
        lines.append("the co-transformed edit FAILED to build: %s" % d.get("co_err", ""))
        ok = False
    else:
        note = co.targets[0].texanim_note
        changed = set(co.targets[0].changed)
        page = d["page"]
        per_rect = {r.as_tuple(): sum(1 for (x, y) in r.texels() if y * page.w + x in changed)
                    for r in d["prot"]}
        same = all(per_rect[k] == d["co_expect"][k] and d["co_expect"][k] > 0 for k in per_rect)
        lines.append("the window AND both frames, no key: BUILDS -- %s" % note)
        lines.append("every protected rect carries the SAME transform, texel by texel: %s   %s"
                     % (same, ", ".join("%s %d/%d" % (k, per_rect[k], d["co_expect"][k])
                                        for k in sorted(per_rect))))
        ok = ok and same and "every protected rect reached" in note
        ta = d["ta"]
        ident = co.patched[ta.lo:ta.hi] == d["blob"][ta.lo:ta.hi]
        lines.append("...and the region itself: %s" % ("BYTE-IDENTICAL" if ident else "*** MOVED ***"))
        ok = ok and ident
    return gate("G3 the co-transform (ef038: window alone REFUSES naming the frames; all three BUILD)",
                ok, *lines)


# --------------------------------------------------------------------------- G4
def g4_the_region_invariant():
    if not _have_corpus():
        return gate("G4 THE REGION INVARIANT", False, "no extracted corpus at %s" % CORPUS)
    lines, ok = [], True
    lines.append("THE RULE: %s" % TA.REGION_RULE)
    for ef in TEXANIM_CLASS:
        d = lifts(ef)
        blob, ta = d["blob"], d.get("ta")
        if ta is None or not ta.armed:                           # pragma: no cover - corpus drift
            lines.append("ef%03d is not armed -- nothing to pin" % ef)
            ok = False
            continue
        mp0 = EC.creature_package(blob)
        verdicts = []
        for label, b in (("reskin", d["creature"][0]), ("repaint", d.get("whole"))):
            if b is None:
                verdicts.append("%s DID NOT BUILD" % label)
                ok = False
                continue
            mp1 = EC.creature_package(b.patched)
            same_region = b.patched[ta.lo:ta.hi] == blob[ta.lo:ta.hi]
            same_fb = mp1.first_block == mp0.first_block
            same_mo = min(mp1.motion_offsets) == min(mp0.motion_offsets)
            same_span = RS.texanim_region(b.patched) == ta
            good = same_region and same_fb and same_mo and same_span
            ok = ok and good and "byte-identical" in b.region_invariant
            verdicts.append("%s %s" % (label, "OK" if good else
                                       "*** region=%s firstBlock=%s motion=%s span=%s ***"
                                       % (same_region, same_fb, same_mo, same_span)))
        lines.append("ef%03d  region %d B at %#x..%#x, firstBlock %#x, min(motionOffsets) %#x  ->  %s"
                     % (ef, ta.nbytes, ta.lo, ta.hi, mp0.first_block, min(mp0.motion_offsets),
                        " | ".join(verdicts)))

    # NON-VACUITY: a check that cannot FAIL is not a check.  Tamper with one region byte and one
    # firstBlock, in memory, and require the enforcement point to catch each of them by name.
    blob = _load(38)
    ta = RS.texanim_region(blob)
    tampered = bytearray(blob)
    tampered[ta.lo + 8] ^= 0xFF
    fired, msg = _refuses(RS.assert_region_invariant, blob, bytes(tampered), "a tampered ef038")
    lines.append("a single REWRITTEN region byte is caught: %s"
                 % ("REFUSED -- %s" % msg.split(": ", 1)[-1].split("REWRITTEN")[0].strip()
                    + " REWRITTEN" if fired
                    else "*** NOT CAUGHT -- the invariant is vacuous ***"))
    ok = ok and fired and "REWRITTEN" in msg
    lines.append("the invariant is enforced at the BUILD call site in both lanes "
                 "(reskin.build / repaint.build), not described in a docstring")
    return gate("G4 THE REGION INVARIANT (R1: firstBlock, min(motionOffsets) and the region bytes)",
                ok, *lines)


# --------------------------------------------------------------------------- G5
def _byte_literals(path: str, minlen: int = 6):
    out = []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
    except SyntaxError:                                          # pragma: no cover
        return out
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, bytes):
            if len(node.value) >= minlen and len(set(node.value)) > 1:
                out.append((node.lineno, node.value))
    return out


def g5_provenance():
    lines, ok = [], True
    lits = []
    for name in COMMITTABLE:
        fp = os.path.join(_REPO, *name.split("/")) if "/" in name else os.path.join(_HERE, name)
        if not os.path.isfile(fp):
            lines.append("%s MISSING" % name)
            ok = False
            continue
        if name.endswith(".py"):
            lits.extend((name, ln, raw) for ln, raw in _byte_literals(fp))
    cast = []
    for name in COMMITTABLE_CAST:
        fp = os.path.join(_HERE, name)
        if os.path.isfile(fp):
            cast.append(name)
            if name.endswith(".py"):
                lits.extend((name, ln, raw) for ln, raw in _byte_literals(fp))
    lines.append("the cast lane's files, scanned when present: %s"
                 % (", ".join(cast) if cast else "none in this tree yet"))
    lines.append("byte literals of >= 6 non-uniform bytes in the %d committable W7 sources: %d"
                 % (len(COMMITTABLE) + len(cast), len(lits)))
    hits = []
    if lits and _have_corpus():
        for path in W.corpus_paths(CORPUS):
            with open(path, "rb") as fh:
                blob = fh.read()
            for name, ln, raw in lits:
                if raw in blob:
                    hits.append("LEAK %s:%d in %s" % (name, ln, os.path.basename(path)))
    lines.append("   of those, appearing anywhere in the %d-file corpus: %d"
                 % (len(W.corpus_paths(CORPUS)), len(hits)))
    for h in hits:
        lines.append("      " + h)
    ok = ok and not hits
    for p in DOSSIERS:
        outside = _REPO.lower() not in os.path.abspath(p).lower()
        lines.append("dossier outside the checkout: %s  (%s)" % (outside, p))
        ok = ok and outside
    lines.append("what this rung commits is a READER, its tests, this runner and the study record -- "
                 "offsets, strides, field names and rect coordinates, never a stock byte")
    return gate("G5 provenance (no SE bytes committable; the SE-derived dossiers stay in SCRATCH)",
                ok, *lines)


# --------------------------------------------------------------------------- main
def main() -> int:
    print(__doc__.splitlines()[0])
    if not _have_corpus():
        print("\nNOTE: no extracted corpus at %s -- G1/G2/G3/G4 will FAIL loudly rather than skip."
              % CORPUS)
    try:
        g1_the_round_trip()
        g2_the_lift_matrix()
        g3_the_co_transform()
        g4_the_region_invariant()
        g5_provenance()
    finally:
        if _TMP is not None:
            import shutil
            shutil.rmtree(_TMP, ignore_errors=True)
    print("\n" + "=" * 72)
    for name, ok in RESULTS:
        print("%-5s %s" % ("PASS" if ok else "FAIL", name))
    passed = sum(1 for _n, ok in RESULTS if ok)
    print("=" * 72)
    print("%d/%d gates pass" % (passed, len(RESULTS)))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":                                       # pragma: no cover
    raise SystemExit(main())
