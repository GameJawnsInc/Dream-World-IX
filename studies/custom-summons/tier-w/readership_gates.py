r"""THE GAIN HALF, DECLINABLE -- `py readership_gates.py` prints D1..D6 with PASS/FAIL.

The W6b-3 (iv) adoption (`linear-add-v1`) is the edit surface's default, and its gain half fails
SILENTLY: a gained cell is licensed on the derivation alone, with no key, so if the model did not hold
on a container a repaint there would be invisible in game with no error anywhere.  ef407's cast closed
that on ef407; an author who distrusts the model on THEIR container can now read the cell each record
BINDS instead -- `repaint.READINGS["bound"]`: `[reskin] readership = "bound"`, `export-art
--readership bound`, `channels=` on `texel_page` / `export_art` / `build`.  This runner proves that
reading is what it says:

D1  THE RECOVERY.  On every corpus container the EFFECTIVE path, with every measured displacement
    forced to identity (`reskin.Binding.mover` answering None for the run), returns the `bound`
    reading's page set and its export-blocking refusals exactly -- so `bound` is the adoption UNDONE,
    not a third surface.  And the comparison can fail: unforced, the two readings differ (pinned).
D2  RESOLUTION, 372/372.  `texel_page(channels=bound)` returns every addressable `bound` page identical
    to the surface's and refuses every name only the effective reading resolves, saying the default
    would have licensed it; the DEFAULT `texel_page` still resolves every addressable effective page.
D3  EXPORT, 372/372.  `export_art(channels=bound)` names exactly the `bound` surface in the lane minus
    its export-blocking refusals, records `readership "bound"`, and every model entry reads its bound
    cover; the DEFAULT export names exactly the effective surface and says so.  The indexed lane runs on
    every container; the direct15 lane on every container that carries a 15bpp page on either reading
    (on the rest its expected set is empty on both, by the surfaces D1 compares).
D4  BUILD, on the gain cast's own container.  ef407's cast spec (`ef407_gain.toml`) rebuilds the cast's
    bytes on the default reading and, with `readership = "bound"`, refuses `cell.s0.x704_y256` with
    its pre-adoption reason and the GAINED line.  On the same container the loss half's
    `cell.s0.x640_y384` is a page again on `bound`, refused by THE SECOND-ARRAY GATE without the key
    and, with it, spliced to the SAME bytes the effective reading's acknowledged build writes.
D5  THE CLI.  `summon-reskin export-art --readership bound` on ef407 writes a manifest and a scaffold
    that say `bound`; `plan` on that scaffold reads it from the spec; `plan --readership effective`
    refuses, because a reading stated only on a command line would build one thing and verify another.
D6  THE POPULATION, pinned: the containers where the readings differ, the names only one of them
    resolves, the GAINED names among the effective-only ones, and how many of the loss half's names
    the `bound` reading hands back as pages.

Reads `C:\gd\SCRATCH\summon-format` ONLY; exports go to a temp dir under it and are deleted -- no
install read, no deploy, no install write, no commit.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Dict, List, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import reskin as RS_STUDY                                        # noqa: E402,F401  (sets up sys.path)
from ff9mapkit.summons import depth_attribution as DA            # noqa: E402
from ff9mapkit.summons import repaint as RP                      # noqa: E402
from ff9mapkit.summons import reskin as RS                       # noqa: E402

_REPO = os.path.normpath(os.path.join(_HERE, "..", "..", ".."))
_KIT = os.path.join(_REPO, "ff9mapkit")
# THE WORKTREE PIN: a study script that silently imported the MAIN checkout's kit would grade the
# wrong code and pass.  Assert the module under test is THIS tree's.
assert os.path.normcase(os.path.abspath(RP.__file__)).startswith(os.path.normcase(_KIT)), RP.__file__

CORPUS = r"C:\gd\SCRATCH\summon-format"
BOUND, EFFECTIVE = RP.READINGS["bound"], RP.READINGS["effective"]
LANES = {"indexed": (4, 8), "direct15": (15,)}
CAST_SPEC = os.path.join(_HERE, "ef407_gain.toml")
#: the zebra cast's patched container, rebuilt on THE UPLOAD WALK's page map.  The cast itself ran as
#: `71d04a12...`, written at the pre-walk offset 0x2146c, 916 bytes before where the game loads the cell
#: (tier-w/PLAN.md, owner item 1, and the page-offset fix); this is the same zebra at 0x21800.
CAST_SHA_PREFIX = "53d93424"
GAIN_CELL, LOSS_CELL = "cell.s0.x704_y256", "cell.s0.x640_y384"

# THE POPULATION PINS (D6), measured by this runner's own walk
PIN_DIFFERING_CONTAINERS = 29
PIN_BOUND_ONLY = 72
PIN_EFFECTIVE_ONLY = 52
PIN_GAINED = 43
#: the LOSS half on the effective reading (`displaced-readerless` + `-substituted` names) and how many of
#: them the `bound` reading resolves -- the cells declining the gain half hands back as pages
PIN_LOSS_NAMES = 55
PIN_LOSS_RESOLVED_ON_BOUND = 54

_FAILS: List[str] = []


def chk(name: str, got, want) -> None:
    """Compare a re-measured value against its pin; collect rather than raise, so the board prints."""
    if got != want:
        _FAILS.append("%s: measured %r, pinned %r" % (name, got, want))


def _load(ef: int) -> bytes:
    with open(os.path.join(CORPUS, "ef%03d.bytes" % ef), "rb") as fh:
        return fh.read()


def _ident(p) -> tuple:
    """A page's IDENTITY -- every fact an author's spec guards or a build splices by."""
    return (p.name, p.bpp, p.cell, p.depth_source, p.palette_name, p.clut_offset, p.tpage, p.clut,
            p.page_offset, p.page_bytes, p.w, p.h)


def _blocking(refused) -> List[tuple]:
    return sorted((r.name, r.klass) for r in refused if r.klass in RP._EXPORT_BLOCKING)


def _addressable(pages, refused) -> Dict[str, object]:
    """The names :func:`texel_page` hands back: emitted, and not refused as unaddressable."""
    unaddr = {r.name for r in refused if r.klass in RP._UNADDRESSABLE}
    return {p.name: p for p in pages if p.name not in unaddr}


class _Identity:
    """Every measured displacement forced to identity for the duration -- `Binding.mover` answers
    None, which is exactly what a binding with no measured pair answers, so `bound_models` gives
    every model `effective_cover is cover`.  Process-wide, restored on exit."""

    def __enter__(self):
        self._orig = RS.Binding.mover
        RS.Binding.mover = property(lambda self: None)
        return self

    def __exit__(self, *exc):
        RS.Binding.mover = self._orig
        return False


class _SurfaceCache:
    """`repaint.scenery_surface` MEMOISED on its exact arguments, for D2's per-name walk.

    `texel_page` re-derives the whole surface on every call, so resolving each of ~600 names one by
    one costs an hour on the big containers.  The cache keeps everything `texel_page` itself decides --
    which channel set it asks for, the refusal-before-page ordering, the name match, the declined
    line -- because a call with the WRONG channels is a different key and gets that scope's surface.
    The surface derivation itself is D1's to judge, uncached.  Process-wide, restored on exit.
    """

    def __init__(self, blob: bytes):
        self._blob, self._memo = blob, {}

    def __enter__(self):
        self._orig = RP.scenery_surface

        def cached(blob, effect=None, **kw):
            # EVERY keyword is part of the key, whatever the kit's signature grows -- a wrapper that
            # re-typed the parameter list would break (or worse, drop one) the day the kit adds one
            if blob is not self._blob:
                return self._orig(blob, effect, **kw)
            key = (effect,) + tuple(sorted((k, frozenset(v) if k == "channels" else v)
                                           for k, v in kw.items()))
            if key not in self._memo:
                self._memo[key] = self._orig(blob, effect, **kw)
            return self._memo[key]

        RP.scenery_surface = cached
        return self

    def __exit__(self, *exc):
        RP.scenery_surface = self._orig
        return False


# ------------------------------------------------------------------ THE WALK (shared by D1-D3, D6)
_WALK: Dict[int, dict] = {}
_SPENT = {"surfaces": 0.0, "resolve": 0.0, "export": 0.0}
_LOSS = ("displaced-readerless", "displaced-readership-substituted")


def _walk() -> Dict[int, dict]:
    if _WALK:
        return _WALK
    t0 = time.time()
    tmp = tempfile.mkdtemp(prefix="readership-", dir=CORPUS)
    try:
        for path in sorted(glob.glob(os.path.join(CORPUS, "ef*.bytes"))):
            ef = int(os.path.basename(path)[2:5])
            blob = _load(ef)
            row: dict = {"err": ""}
            t1 = time.time()
            try:
                lp, lr = RP.scenery_surface(blob, ef, channels=BOUND)
                ep, er = RP.scenery_surface(blob, ef, channels=EFFECTIVE)
                with _Identity():
                    ip, ir = RP.scenery_surface(blob, ef, channels=EFFECTIVE)
            except Exception as exc:                              # a container the lane cannot read
                row["err"] = "%s: %s" % (type(exc).__name__, exc)
                _WALK[ef] = row
                continue
            row.update(bound=(lp, lr), eff=(ep, er), ident=(ip, ir))
            t2 = time.time()
            with _SurfaceCache(blob):
                row["resolve"] = _resolve(blob, ef, lp, lr, ep, er)
            t3 = time.time()
            row["export"] = _export(blob, ef, lp, lr, ep, er, tmp)
            _SPENT["surfaces"] += t2 - t1
            _SPENT["resolve"] += t3 - t2
            _SPENT["export"] += time.time() - t3
            _WALK[ef] = row
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("   walked %d containers in %.0fs (surfaces %.0fs, texel_page %.0fs, export_art %.0fs)"
          % (len(_WALK), time.time() - t0, _SPENT["surfaces"], _SPENT["resolve"], _SPENT["export"]))
    return _WALK


def _resolve(blob, ef, lp, lr, ep, er) -> dict:
    """D2's measurements on one container: resolution through the SHIPPED entry point."""
    out = {"bound_bad": [], "eff_bad": [], "eff_only_bad": [], "bound_only_bad": []}
    la, ea = _addressable(lp, lr), _addressable(ep, er)
    for name, p in sorted(la.items()):
        try:
            q = RP.texel_page(blob, name, ef, channels=BOUND)
            if _ident(q) != _ident(p) or q.readership != "bound":
                out["bound_bad"].append(name)
        except RP.RepaintError:
            out["bound_bad"].append(name)
    for name, p in sorted(ea.items()):
        try:
            if _ident(RP.texel_page(blob, name, ef)) != _ident(p):
                out["eff_bad"].append(name)
        except RP.RepaintError:
            out["eff_bad"].append(name)
    eff_only, bound_only = sorted(set(ea) - set(la)), sorted(set(la) - set(ea))
    gained = 0
    for name in eff_only:
        try:
            RP.texel_page(blob, name, ef, channels=BOUND)
            out["eff_only_bad"].append(name)                      # resolved: the reading leaked
        except RP.RepaintError as exc:
            if "Under the default 'effective' reading" not in str(exc):
                out["eff_only_bad"].append(name)
            gained += "GAINED" in str(exc)
    for name in bound_only:
        try:
            RP.texel_page(blob, name, ef)
            out["bound_only_bad"].append(name)
        except RP.RepaintError:
            pass
    loss = sorted({r.name for r in er if r.klass in _LOSS})
    out.update(eff_only=eff_only, bound_only=bound_only, gained=gained, loss=loss,
               loss_on_bound=[n for n in loss if n in la])
    return out


def _export(blob, ef, lp, lr, ep, er, tmp) -> dict:
    """D3's measurements on one container: both scenery lanes, both readings, the shipped export."""
    out: dict = {"bad": [], "skipped_direct15": False}
    has15 = any(p.bpp == 15 for p in list(lp) + list(ep))
    for lane, want in LANES.items():
        if lane == "direct15" and not has15:
            # NO 15bpp page on EITHER reading, so the lane's expected scenery set is empty on both by
            # the surfaces themselves -- the export would hand back creature pages only, which no
            # reading touches.  Skipped for time, and counted, never silently.
            out["skipped_direct15"] = True
            continue
        for tag, ch, (pages, refused) in (("bound", BOUND, (lp, lr)), ("effective", EFFECTIVE,
                                                                       (ep, er))):
            blocked = {r.name for r in refused if r.klass in RP._EXPORT_BLOCKING}
            expect = {p.name for p in pages if p.bpp in want and p.name not in blocked}
            d = os.path.join(tmp, "x")
            shutil.rmtree(d, ignore_errors=True)                  # one export per directory
            try:
                man = RP.export_art(blob, ef, d, lane=lane, overlays=False, scaffold=True,
                                    channels=ch)
            except RP.RepaintError as exc:
                # nothing in the lane at all is the export's own refusal -- right only if the
                # surface agrees there is nothing to hand back
                if expect or "exports no texel art" not in str(exc):
                    out["bad"].append((lane, tag, "raised: %s" % str(exc)[:120]))
                continue
            got = {e["name"] for e in man["scenery"]}
            why = []
            if got != expect:
                why.append("cells +%s -%s" % (sorted(got - expect)[:3], sorted(expect - got)[:3]))
            if man.get("readership") != tag:
                why.append("manifest readership %r" % man.get("readership"))
            if tag == "bound":
                if any(e["readership"] != "bound" for e in man["scenery"] + man["models"]):
                    why.append("a displaced readership on the bound export")
                if any(m["effective_columns"] != m["columns"] for m in man["models"]):
                    why.append("a model reads a cover other than its bound one")
                with open(os.path.join(d, RP.SCAFFOLD_NAME), encoding="utf-8") as fh:
                    if '\n%s = "bound"\n' % RP.READING_KEY not in fh.read():
                        why.append("the scaffold does not state the reading")
            if why:
                out["bad"].append((lane, tag, "; ".join(why)))
    return out


def _read_rows() -> List[Tuple[int, dict]]:
    w = _walk()
    return [(ef, r) for ef, r in sorted(w.items()) if not r["err"]]


# --------------------------------------------------------------------------- D1
def d1_recovery() -> None:
    w = _walk()
    errs = sorted(ef for ef, r in w.items() if r["err"])
    rows = _read_rows()
    same = sum(1 for _ef, r in rows
               if [_ident(p) for p in r["ident"][0]] == [_ident(p) for p in r["bound"][0]]
               and _blocking(r["ident"][1]) == _blocking(r["bound"][1]))
    differ = [ef for ef, r in rows
              if [_ident(p) for p in r["eff"][0]] != [_ident(p) for p in r["bound"][0]]
              or _blocking(r["eff"][1]) != _blocking(r["bound"][1])]
    print("   %d containers; identity-forced effective == bound on %d; unforced they differ on %d"
          % (len(w), same, len(differ)))
    chk("D1 the corpus is the 372 and every container reads", (len(w), errs), (372, []))
    chk("D1 identity-forced effective == bound, pages + export-blocking refusals", same, len(rows))
    chk("D1 the comparison can fail: unforced, the readings differ", bool(differ), True)
    # the forcing really reached the surface: no displaced readership survives it
    leak = [ef for ef, r in rows if any(p.readership == "displaced" for p in r["ident"][0])]
    chk("D1 the forced run carries no displaced reader", leak, [])


# --------------------------------------------------------------------------- D2
def d2_resolution() -> None:
    rows = _read_rows()
    bad = {k: [(ef, n) for ef, r in rows for n in r["resolve"][k]]
           for k in ("bound_bad", "eff_bad", "eff_only_bad", "bound_only_bad")}
    nb = sum(len(_addressable(*r["bound"])) for _ef, r in rows)
    ne = sum(len(_addressable(*r["eff"])) for _ef, r in rows)
    print("   texel_page: %d bound names, %d effective names resolved through the entry point"
          % (nb, ne))
    chk("D2 bound: every addressable bound page resolves IDENTICAL", bad["bound_bad"], [])
    chk("D2 default: every addressable effective page resolves IDENTICAL", bad["eff_bad"], [])
    chk("D2 bound refuses every effective-only name, and says the default licenses it",
        bad["eff_only_bad"], [])
    chk("D2 default refuses every bound-only name (the loss half)", bad["bound_only_bad"], [])


# --------------------------------------------------------------------------- D3
def d3_export() -> None:
    rows = _read_rows()
    bad = [(ef,) + b for ef, r in rows for b in r["export"]["bad"]]
    skipped = sum(1 for _ef, r in rows if r["export"]["skipped_direct15"])
    print("   export_art: %d containers x 2 readings in the indexed lane; the direct15 lane on the %d "
          "that carry a 15bpp page on either reading (the other %d have none, so its expected set is "
          "empty on both)" % (len(rows), len(rows) - skipped, skipped))
    for b in bad[:8]:
        print("     %s" % (b,))
    chk("D3 every export names exactly its reading's surface and states it", bad, [])


# --------------------------------------------------------------------------- D4
def d4_build() -> None:
    blob = _load(407)
    spec = RP.load_spec(CAST_SPEC)
    b = RP.build(spec, CAST_SPEC, blob=blob)
    print("   ef407 cast spec, default reading: %s  sha %s" % (b.reading, b.sha_out[:16]))
    chk("D4 the cast spec rebuilds the CAST'S bytes on the default reading",
        (b.reading, b.sha_out[:len(CAST_SHA_PREFIX)]), ("effective", CAST_SHA_PREFIX))
    spec["reskin"][RP.READING_KEY] = "bound"
    try:
        RP.build(spec, CAST_SPEC, blob=blob)
        chk("D4 bound refuses the gained cast cell", "built", "refused")
    except RP.RepaintError as exc:
        msg = str(exc)
        print("   bound: %s" % msg[:150].replace("\n", " "))
        chk("D4 bound refuses the gained cast cell BY NAME, saying the default licenses it",
            (GAIN_CELL in msg, "REFUSED, not unknown" in msg,
             "Under the default 'effective' reading" in msg, "GAINED" in msg),
            (True, True, True, True))
    # THE LOSS HALF, same container
    page = RP.texel_page(blob, LOSS_CELL, 407, channels=BOUND)
    chk("D4 the loss cell is a page on bound, every reader displaced",
        (page.depth_source, page.readership, page.hazards.every_reader_moves),
        ("so-uv", "bound", True))
    try:
        RP.texel_page(blob, LOSS_CELL, 407)
        chk("D4 the default refuses the loss cell", "resolved", "refused")
    except RP.RepaintError as exc:
        chk("D4 the default refuses the loss cell as displaced-readerless",
            "displaced-readerless" in str(exc), True)
    tmp = tempfile.mkdtemp(prefix="readership-d4-", dir=CORPUS)
    try:
        raw = bytearray(blob[page.page_offset:page.page_offset + page.page_bytes])
        for i in range(0, len(raw), 7):                           # a sparse, cutout-safe edit
            if raw[i]:
                raw[i] = 1 + (raw[i] % 255)
        png = os.path.join(tmp, "%s.png" % LOSS_CELL)
        RP.write_indexed_png(bytes(raw), RP.palette_words(blob, page), page.w, page.h, png)
        sha = hashlib.sha256(blob).hexdigest()

        def _spec(reading, ack):
            row = {"name": LOSS_CELL, "source": png, "expect_bpp": page.bpp}
            if ack:
                row[DA.ACK_MOVER_KEY] = True
            r = {"effect": 407, "label": "d4", "expect_sha256": sha, "texel": [row]}
            if reading:
                r[RP.READING_KEY] = reading
            return {"reskin": r}

        try:
            RP.build(_spec("bound", False), os.path.join(tmp, "d4.toml"), blob=blob)
            chk("D4 bound, no key: THE SECOND-ARRAY GATE refuses", "built", "refused")
        except RP.RepaintError as exc:
            chk("D4 bound, no key: THE SECOND-ARRAY GATE refuses",
                "THE SECOND-ARRAY GATE" in str(exc), True)
        bb = RP.build(_spec("bound", True), os.path.join(tmp, "d4.toml"), blob=blob)
        be = RP.build(_spec(None, True), os.path.join(tmp, "d4.toml"), blob=blob)
        moved = sum(1 for i in range(len(blob)) if blob[i] != bb.patched[i])
        print("   loss cell %s: bound+key %s, effective+key %s, %d bytes moved"
              % (LOSS_CELL, bb.sha_out[:16], be.sha_out[:16], moved))
        chk("D4 the reading moves the LICENCE, not the bytes: one picture, one splice",
            (bb.patched == be.patched, moved > 0), (True, True))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------- D5
def _cli(args: List[str]) -> Tuple[int, str]:
    p = subprocess.run([sys.executable, "-m", "ff9mapkit"] + args, cwd=_KIT,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout + p.stderr


def d5_cli() -> None:
    src = os.path.join(CORPUS, "ef407.bytes")
    tmp = tempfile.mkdtemp(prefix="readership-d5-", dir=CORPUS)
    try:
        art = os.path.join(tmp, "art")
        rc, out = _cli(["summon-reskin", "export-art", "--ef", "407", "--from", src, "--out", art,
                        "--readership", "bound"])
        chk("D5 export-art --readership bound runs", rc, 0)
        chk("D5 ...and prints the reading", "readership    : bound" in out, True)
        with open(os.path.join(art, RP.ART_MANIFEST), encoding="utf-8") as fh:
            man = json.load(fh)
        names = {e["name"] for e in man["scenery"]}
        chk("D5 the manifest says bound and drops the gained cell, keeps the loss cell",
            (man["readership"], GAIN_CELL in names, LOSS_CELL in names), ("bound", False, True))
        spec = os.path.join(art, RP.SCAFFOLD_NAME)
        rc, out = _cli(["summon-reskin", "plan", spec, "--from", src])
        print("   plan on the bound scaffold: rc %d" % rc)
        chk("D5 plan reads the reading from the spec", (rc, "gain half DECLINED" in out), (0, True))
        rc, out = _cli(["summon-reskin", "plan", spec, "--from", src, "--readership", "effective"])
        chk("D5 plan --readership effective on a bound spec refuses",
            (rc, "this call asked for 'effective'" in out), (2, True))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------- D6
def d6_population() -> None:
    rows = _read_rows()
    differ = sum(1 for _ef, r in rows if r["resolve"]["eff_only"] or r["resolve"]["bound_only"])
    bound_only = sum(len(r["resolve"]["bound_only"]) for _ef, r in rows)
    eff_only = sum(len(r["resolve"]["eff_only"]) for _ef, r in rows)
    gained = sum(r["resolve"]["gained"] for _ef, r in rows)
    loss = sum(len(r["resolve"]["loss"]) for _ef, r in rows)
    loss_back = sum(len(r["resolve"]["loss_on_bound"]) for _ef, r in rows)
    print("   %d containers resolve different names; %d names only bound resolves, %d only effective"
          " (%d of them GAINED)" % (differ, bound_only, eff_only, gained))
    kept = ["ef%03d %s" % (ef, n) for ef, r in rows for n in r["resolve"]["loss"]
            if n not in r["resolve"]["loss_on_bound"]]
    print("   the loss half: %d names refused on effective, %d of them pages again on bound%s"
          % (loss, loss_back, ("; still refused there: %s" % ", ".join(kept)) if kept else ""))
    chk("D6 the population", (differ, bound_only, eff_only, gained),
        (PIN_DIFFERING_CONTAINERS, PIN_BOUND_ONLY, PIN_EFFECTIVE_ONLY, PIN_GAINED))
    chk("D6 the loss half handed back", (loss, loss_back),
        (PIN_LOSS_NAMES, PIN_LOSS_RESOLVED_ON_BOUND))


GATES = [
    ("D1", "THE RECOVERY -- identity-forced effective == bound, 372/372", d1_recovery),
    ("D2", "RESOLUTION -- texel_page on both readings, every name, 372/372", d2_resolution),
    ("D3", "EXPORT -- export_art on both readings and both lanes, 372/372", d3_export),
    ("D4", "BUILD -- ef407's gain cast and its loss cell, on both readings", d4_build),
    ("D5", "THE CLI -- export-art --readership bound, and plan reading the spec", d5_cli),
    ("D6", "THE POPULATION -- what the two readings disagree on, pinned", d6_population),
]


def main(argv=None) -> int:
    only = set(a.upper() for a in (argv or sys.argv[1:]) if a.upper().startswith("D"))
    print("READERSHIP GATES -- the gain half declinable, the declined reading re-derived")
    print("corpus: %s" % CORPUS)
    print("=" * 72)
    board = []
    for tag, title, fn in GATES:
        if only and tag not in only:
            continue
        before = len(_FAILS)
        print("%s  %s" % (tag, title))
        try:
            fn()
            ok = len(_FAILS) == before
        except Exception as exc:                                   # a crashed gate is a red gate
            _FAILS.append("%s raised %s: %s" % (tag, type(exc).__name__, exc))
            ok = False
        board.append((tag, title, ok))
        print("   [%s] %s\n" % ("PASS" if ok else "FAIL", tag))
    print("=" * 72)
    for tag, title, ok in board:
        print("%-4s %s %s" % ("PASS" if ok else "FAIL", tag, title))
    if _FAILS:
        print("-" * 72)
        for f in _FAILS:
            print("  FAIL  %s" % f)
    print("=" * 72)
    print("%d/%d gates pass" % (sum(1 for _, _, ok in board if ok), len(board)))
    return 1 if _FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
