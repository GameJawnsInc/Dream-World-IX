r"""TIER W rung W6b-3 CAST A -- THE ZERO-STRIPE PROBE on ef424, the two CHANNEL-A ladder cells.

    py odin_cell_probe.py                 # stage only; the install is untouched
    py odin_cell_probe.py --deploy        # snapshot the live override and write the probe over it
    py odin_cell_probe.py --deploy --mod-folder <temp>\FF9CustomMap --root <temp>\probe-root
                                          # REHEARSE the whole ledger against a folder the game
                                          # never reads.  Do this first -- it is how the emitted
                                          # revert script's `\U`-in-a-docstring parse failure was
                                          # found, at zero cost, instead of at the cast.

WHY THIS PROBE RUNS FIRST, AND WHY THE LADDER IS NOT NEGOTIABLE
--------------------------------------------------------------
``phoenix_cell_probe.py`` established the instrument and the law it enforces:

    AN ``so`` READER IS A BINDING, NOT A DRAW.  The so-record proves a model CAN sample a cell; it
    does not prove the model is ever drawn, or visible.  Two ef211 casts reached the FILE -- the live
    sha was verified after each deploy -- and neither figure appeared anywhere on screen, because
    cell (704,256) simply is not what the visible fire samples.  ef429 then scored 0-for-2 on the
    same question with a 60 fps frame sweep to prove it.

ef424 (``SpecialEffect.Odin__Short``) is CHANNEL A's first cast vehicle, and channel A's whole
prediction record so far is 0 HITS / 4 MISSES / 2 VACUOUS PASSES over six named cells.  So the ink
cast (``odin_channel_a.toml``) may only be deployed after this probe has answered the prior question:

    IS EITHER LADDER CELL DRAWN AT ALL?

BINDING-IS-NOT-A-DRAW gates the depth read, not the reverse.  A negative cast A makes a negative
cast B uninterpretable, which is the one mistake this tier has already paid for twice.

THE TWO LADDER CELLS
--------------------
Both are named by ONE multi-part ``so`` record, 0x2f9a4, P = 2:

  * ``cell.s0.x704_y384``  slot 1's column, and **nothing else in the container binds it** --
    CHANNEL A only.  Its palette entry 0 is ``0x0000`` with stp = 0, so a zeroed texel there is a
    genuine hardware hole in a surface that is already 73.6 % cutout: the stripes REMOVE structure.
  * ``cell.s0.x448_y384``  slot 0's column, also bound by SEVEN incumbent single-part records, so it
    is licensed on the ``so``-UV channel and carries real declared cover (1,506 halfwords).

Everything else in the container is left UNTOUCHED as its own control.

THE INSTRUMENT.  Zero-writing is DEPTH-INVARIANT: a ``0x00`` byte is index 0 twice at 4bpp, index 0
at 8bpp, and half of the cutout word ``0x0000`` at 15bpp -- at every depth a zeroed texel is the
transparent / black-cutout value.  So a probe may lawfully mark a cell whose depth is exactly what is
in question: it is a diagnostic instrument OUTSIDE the edit lane, and what it writes is the one value
whose meaning does not depend on the answer it is measuring.

THE ENCODING, UNCHANGED FROM THE ef211 CENSUS.  Cell #k (1-based, sorted by ``(x, y, writer tag)``)
gets **k evenly-spaced horizontal zero stripes**, each ``STRIPE_ROWS`` byte-rows of 128 bytes.  A
surface sampling cell #k shows k dark bands per texture repeat -- scrolling moves the bands, never
their count.  Count the bands in whatever goes gappy and read off the cell.  On ef424 the canonical
k values are printed per run and CROSS-CHECKED against ``odin_band_stamp.py``'s own band counts, which
are imported rather than restated: if a cast-A signature ever collided with a cast-B one, the two
reads would contaminate each other and no amount of prose in a runbook would undo it.

THE LEDGER.  ``--deploy`` snapshots whatever the live override holds into this root before writing,
verifies the readback sha, and emits ``revert_probe.py``.  One file written, one file restored,
nothing else touched.  **THE LEDGER TRAP:** revert this probe BEFORE the kit's ``summon-reskin
deploy`` runs.  The kit takes its own FIRST-DEPLOY snapshot per root and never overwrites it, so a
kit deploy on top of a live probe records THE PROBE as the pre-state -- and its revert would then
restore the probe forever, as the resting state of a mod folder nobody is looking at any more.

PROVENANCE.  Everything is derived from the user's own container at run time; the probe container is
SE-derived and stays in SCRATCH / the install.  Zero SE bytes here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "..", "..", "ff9mapkit"))
sys.path.insert(0, _HERE)

from ff9mapkit.summons import reskin as RS                        # noqa: E402
from ff9mapkit.summons import container as EC                     # noqa: E402
# THE COUNTS AND THE PLACEMENT RULE COME FROM THE OTHER INSTRUMENT, never from a second copy of them.
# A restated constant is how the two casts' signatures would silently converge, and a restated placement
# rule is how one instrument would end up marking lines the other's read assumes are marked.
from odin_band_stamp import BANDS as CAST_B_BANDS                 # noqa: E402
from odin_band_stamp import BAND_ROWS as CAST_B_BAND_ROWS         # noqa: E402
from odin_band_stamp import cover_span, evenly_spaced_tops        # noqa: E402
# THE SOURCE PIN, imported for the same reason: `EFFECT` and `GAME_OVERRIDE` below are pinned to ef424
# while `--from` is a free path, so a foreign source would be staged as `ef424.cellprobe` and DEPLOYED
# over the ef424 override.  One owner for the pin, one for the counts.
from odin_band_stamp import pin_source                            # noqa: E402

EFFECT = 424
DEFAULT_ROOT = r"C:\gd\SCRATCH\summon-format\repaint-w6b\ef424-channel-a\cellprobe"
DEFAULT_CORPUS = r"C:\gd\SCRATCH\summon-format\ef424.bytes"
MOD_ROOT = (r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX"
            r"\FF9CustomMap")
GAME_OVERRIDE = os.path.join(MOD_ROOT, "FF9_Data", "SpecialEffects", "ef%03d" % EFFECT)
STRIPE_ROWS = 6                     # byte-rows per stripe (128 B each); bold enough to read on video
ROW_BYTES = 128
CELL_ROWS = 128

#: THE LADDER.  Exactly the two cells `odin_channel_a.toml` targets, at their CANONICAL census k --
#: every other cell in the container stays stock and is its own control.
LADDER_CELLS = ("cell.s0.x704_y384", "cell.s0.x448_y384")


def stripe_tops(k: int, lo: int = 0, hi: int = CELL_ROWS - 1):
    """The TOP row of each of ``k`` evenly-spaced stripes inside ``lo..hi``.

    ``lo=0, hi=127`` is the ef211 whole-cell rule exactly.  A COVERED cell gets its own span instead --
    see :func:`odin_band_stamp.cover_span` for why that is not optional on this vehicle: the order
    cell's declared cover stops at line 63, so the whole-cell rule would put its second stripe at 93
    where nothing samples, and a probe whose COUNT is its whole content would read 1 where it wrote 2.
    """
    return evenly_spaced_tops(k, STRIPE_ROWS, lo, hi)


def striped(cell_bytes: bytes, k: int, lo: int, hi: int) -> bytes:
    """``k`` evenly-spaced zero stripes of ``STRIPE_ROWS`` byte-rows, inside ``lo..hi``."""
    out = bytearray(cell_bytes)
    for top in stripe_tops(k, lo, hi):
        for r in range(top, min(CELL_ROWS, top + STRIPE_ROWS)):
            out[r * ROW_BYTES:(r + 1) * ROW_BYTES] = b"\x00" * ROW_BYTES
    return bytes(out)


def contamination_notes(ks: dict) -> list:
    """Every way a cast-A signature could be MISTAKEN for a cast-B one, checked rather than asserted.

    Three independent axes separate the instruments -- COUNT (k vs the band count), DUTY (a 6-row zero
    stripe vs a 12-row ink band) and POLARITY (dark holes vs bright ink).  Each check below names the
    axis it defends, and a collision is printed LOUD into the emitted protocol instead of being
    quietly tolerated: a read nobody was warned about is worse than a read nobody takes.
    """
    L = []
    names = list(ks)
    if len(set(ks.values())) != len(ks):
        L.append("*** LOUD: two ladder cells share a canonical k (%s) -- COUNT cannot tell them "
                 "apart.  Do NOT read this probe per cell." % ks)
    for n in names:
        for m in names:
            if ks[n] == CAST_B_BANDS.get(m):
                L.append("*** LOUD: %s's zero-stripe k = %d EQUALS cast B's band count on %s.  The "
                         "two casts would produce the same COUNT on screen -- re-pick one before "
                         "either is read." % (n, ks[n], m))
    for n in names:
        a_rows = ks[n] * STRIPE_ROWS
        b_rows = CAST_B_BANDS.get(n, 0) * CAST_B_BAND_ROWS
        if a_rows == b_rows and b_rows:
            L.append(
                "*** LOUD, DISCLOSED AND ACCEPTED: on %s cast A's aggregate duty (%d x %d = %d rows, "
                "%.1f%%) EQUALS cast B's (%d x %d = %d rows).  The COUNT still differs (%d vs %d) and "
                "so does the POLARITY (dark holes vs bright ink), which are the two axes the read uses"
                " -- but the DUTY-CYCLE shortcut the ef211 census decoded with (`dark fraction = "
                "%d*k/128`) is DEGENERATE here.  On this cell count the features; never infer the "
                "instrument from how much of the surface changed."
                % (n, ks[n], STRIPE_ROWS, a_rows, 100.0 * a_rows / CELL_ROWS,
                   CAST_B_BANDS[n], CAST_B_BAND_ROWS, b_rows, ks[n], CAST_B_BANDS[n], STRIPE_ROWS))
    if not L:
        L.append("no collision: every ladder cell's k differs from every other k and from every "
                 "cast-B band count, and no duty coincides.")
    return L


def generate(from_path: str, root: str, cells, placement: str = "cover") -> dict:
    stock = Path(from_path).read_bytes()
    # THE SOURCE PIN runs INSIDE generate(), not in main(), so no caller -- and no import of this
    # module -- can reach the striping (or the deploy that consumes its output) with a container these
    # constants were not measured on.  A guard at the CLI edge is a guard one call site wide.
    pin = pin_source(stock, from_path)
    census = RS.page_cells(stock)
    order = sorted(census.values(), key=lambda pc: (pc.x, pc.y, pc.tag))
    if not order:
        raise SystemExit("ef%03d declares no page-cells -- nothing to stripe" % EFFECT)
    want = list(cells)
    unknown = [c for c in want if c not in {pc.name for pc in order}]
    if unknown:
        raise SystemExit("no such cell(s) %r; the census names are:\n%s"
                         % (unknown, "\n".join("  " + pc.name for pc in order)))

    blob = bytearray(stock)
    legend, ks = [], {}
    for i, pc in enumerate(order):
        k = i + 1
        cov = cover_span(stock, (pc.x, pc.y)) if placement == "cover" else None
        lo, hi = cov if cov else (0, CELL_ROWS - 1)
        rec = {"k": k, "name": pc.name, "kind": pc.kind, "offset": pc.off,
               "cell": [pc.x, pc.y], "written": pc.name in want,
               "span": [lo, hi], "placement": "so-cover" if cov else "whole-cell",
               "stripe_tops": stripe_tops(k, lo, hi) if pc.name in want else [],
               "duty_rows": k * STRIPE_ROWS if pc.name in want else 0}
        if rec["written"]:
            ks[pc.name] = k
            blob[pc.off:pc.off + pc.nbytes] = striped(
                bytes(stock[pc.off:pc.off + pc.nbytes]), k, lo, hi)
        legend.append(rec)

    probe = bytes(blob)
    EC.parse_header(probe, strict=True)                          # the probe must still parse
    if len(probe) != len(stock):
        raise SystemExit("the probe changed the container's LENGTH -- refusing")
    changed = sum(1 for a, b in zip(stock, probe) if a != b)

    root_p = Path(root)
    root_p.mkdir(parents=True, exist_ok=True)
    out = root_p / ("ef%03d.cellprobe" % EFFECT)
    out.write_bytes(probe)
    d = {"effect": EFFECT, "source": from_path, "root": str(root_p), "container": str(out),
         "sha256": hashlib.sha256(probe).hexdigest(),
         "stock_sha256": hashlib.sha256(stock).hexdigest(),
         "bytes": len(probe), "changed_bytes": changed, "cells": len(order),
         "stripe_rows": STRIPE_ROWS, "placement": placement, "ks": ks, "legend": legend,
         "source_pin": pin,
         "cast_b_bands": dict(CAST_B_BANDS), "cast_b_band_rows": CAST_B_BAND_ROWS,
         "notes": contamination_notes(ks)}
    (root_p / "probe.derivation.json").write_text(json.dumps(d, indent=1), encoding="utf-8")
    return d


def protocol(d: dict) -> list:
    L = ["THE ZERO-STRIPE PROBE -- ef%03d CAST A, the two CHANNEL-A ladder cells" % d["effect"],
         "  source           %s" % d["source"],
         "  stock sha256     %s" % d["stock_sha256"],
         "  source pin       %s" % d.get("source_pin", "(none)"),
         "  placement rule   %s (a COVERED cell's stripes go inside its own `so` cover span; an "
         "uncovered one's over all %d lines)" % (d["placement"], CELL_ROWS),
         "",
         "  k  cell                     stripes  duty       placement    lines      stripe tops",
         ]
    for r in d["legend"]:
        if r["written"]:
            L.append("  %2d %-24s %-8s %2d/%-3d rows %-12s %3d..%-3d  %s"
                     % (r["k"], r["name"], "%d x %d" % (r["k"], STRIPE_ROWS),
                        r["duty_rows"], CELL_ROWS, r["placement"], r["span"][0], r["span"][1],
                        r["stripe_tops"]))
        else:
            L.append("  %2d %-24s %-8s %-10s %-12s %3d..%-3d  UNTOUCHED (control)"
                     % (r["k"], r["name"], "-", "-", r["placement"], r["span"][0], r["span"][1]))
    L += ["",
          "  probe container  %d B  sha256 %s" % (d["bytes"], d["sha256"]),
          "  changed bytes    %d (%.2f%% of the container)"
          % (d["changed_bytes"], 100.0 * d["changed_bytes"] / d["bytes"]),
          "  staged           %s" % d["container"],
          "",
          "  THE CANONICAL k VALUES ARE THE READ.  %s"
          % ", ".join("%s -> %d dark band(s)" % (n, k) for n, k in d["ks"].items()),
          "  CAST B's counts, imported from odin_band_stamp.py: %s at %d rows each"
          % (", ".join("%s -> %d band(s)" % (n, v) for n, v in d["cast_b_bands"].items()),
             d["cast_b_band_rows"]),
          ""]
    L += ["  " + n for n in d["notes"]]
    L += ["",
          "  READ IT LIKE THIS.  Cast Stock Odin Short on bench 30301 and watch the TWO surfaces the",
          "  record's parts are: part 0 is a long thin square-section tube shooting away from the",
          "  camera (z -1028..-422); part 1 is a flat billboard plane near the origin (x == 0,",
          "  y -130..130).  For each surface, count the dark bands per texture repeat:",
          "    %d bands  -> that surface samples %s (CHANNEL A -- the cell is DRAWN, cast B is armed)"
          % (d["ks"].get(LADDER_CELLS[0], 0), LADDER_CELLS[0]),
          "    %d bands  -> that surface samples %s (the licensed so-UV column)"
          % (d["ks"].get(LADDER_CELLS[1], 0), LADDER_CELLS[1]),
          "    clean     -> that surface samples NEITHER; it is this cast's own control.",
          "  NOTHING banding anywhere = BOUND-NEVER-DRAWN on channel A, and the ghost table gains an",
          "  entry.  That is a RESULT, not a failure -- and it forbids deploying the ink cast, because",
          "  a negative depth read on an undrawn cell measures nothing.",
          ]
    return L


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--from", dest="from_path", default=DEFAULT_CORPUS,
                    help="the STOCK container to stripe (default the corpus ef%03d)" % EFFECT)
    ap.add_argument("--root", default=DEFAULT_ROOT, help="staging root (LOCAL-ONLY)")
    ap.add_argument("--cells", default=",".join(LADDER_CELLS), metavar="CELL[,CELL...]",
                    help="which cells to stripe, each at its CANONICAL census k (default: exactly "
                         "the two ladder cells).  Narrow it to one for the surgical confirm; every "
                         "cell left out stays stock and is its own control")
    ap.add_argument("--all", action="store_true",
                    help="stripe the FULL 10-cell census instead -- the named follow-up if neither "
                         "ladder cell bands and the question becomes which cell the visible surfaces "
                         "read")
    ap.add_argument("--placement", default="cover", choices=("cover", "whole-cell"),
                    help="where a COVERED cell's stripes go: inside its `so` reader's own line span "
                         "(default), or evenly over all 128 lines (the ef211 rule -- the named "
                         "follow-up when the covered placement shows nothing, because a cell's "
                         "UNBOUND lines may be what the program's own primitives draw).  IMPORTED "
                         "from odin_band_stamp so both instruments place marks by the same rule")
    ap.add_argument("--deploy", action="store_true",
                    help="snapshot the live override and write the probe container over it")
    ap.add_argument("--mod-folder", default=MOD_ROOT,
                    help="the mod folder --deploy writes into.  Defaults to the live FF9CustomMap; "
                         "point it at a temp dir to REHEARSE the whole ledger + revert path without "
                         "touching the install (calibrate the instrument before judging with it -- and "
                         "the rehearsal prints REHEARSAL so a real run can never be mistaken for one)")
    a = ap.parse_args(argv)

    stock = Path(a.from_path).read_bytes()
    if a.all:
        cells = [pc.name for pc in sorted(RS.page_cells(stock).values(),
                                          key=lambda pc: (pc.x, pc.y, pc.tag))]
    else:
        cells = [s.strip() for s in a.cells.split(",") if s.strip()]
    d = generate(a.from_path, a.root, cells, a.placement)
    lines = protocol(d)
    print("\n".join(lines))
    Path(a.root, "PROTOCOL.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n  protocol         %s" % Path(a.root, "PROTOCOL.txt"))

    if not a.deploy:
        print("\n  NOTHING WAS DEPLOYED.  The install is untouched; re-run with --deploy once bench "
              "rows 203/204 are registered (they need a relaunch; this container does not).")
        return 0

    # ---- the live write, with the folder's state MEASURED rather than assumed --------------------
    mod = Path(a.mod_folder)
    live = mod / "FF9_Data" / "SpecialEffects" / ("ef%03d" % EFFECT)
    rehearsal = str(mod.resolve()).lower() != str(Path(MOD_ROOT).resolve()).lower()
    if not rehearsal and str(live) != GAME_OVERRIDE:
        # GAME_OVERRIDE is a PIN, not documentation: if the derived destination ever stops agreeing
        # with the constant this file names, the constant is a comment and the write is somewhere else.
        raise SystemExit("FAIL: the derived destination %s does not match this script's own "
                         "GAME_OVERRIDE pin %s -- refusing to write to a path the file does not name."
                         % (live, GAME_OVERRIDE))
    if rehearsal:
        print("\n  *** REHEARSAL -- --mod-folder is %s, NOT the live install.  Nothing the game reads "
              "will change." % mod)
        mod.mkdir(parents=True, exist_ok=True)
    if not mod.is_dir():
        raise SystemExit("FAIL: mod folder not found: %s" % mod)
    if (mod / "ModFileList.txt").exists():
        raise SystemExit(
            "REFUSING: %s has a ModFileList.txt.  THE SILENT-FALLBACK LAW -- "
            "TryFindAssetInModOnDisc TRUSTS that list and never calls File.Exists, so an unlisted "
            "override is INVISIBLE and this probe would read as a clean negative.  Handle the list "
            "by hand, then re-run." % mod)
    root = Path(a.root)
    pre = root / ("ef%03d" % EFFECT)
    absent_flag = root / "pre.ABSENT"
    print("\n  live override    %s" % live)
    # ⚠ THE STALE-SNAPSHOT DEFECT, found by rehearsing the U1 deploy path (U1-SECOND-ARRAY-CAST.md
    # §8 item 2) and ported back here.  The emitted revert decides by `pre.exists()`.  A root that
    # has ALREADY been deployed into once keeps whichever marker that run left behind, so a PRESENT
    # run followed by an ABSENT run would leave the old `pre` snapshot lying beside the new
    # `pre.ABSENT` -- and the revert would RESTORE somebody else's container instead of deleting
    # ours.  The two markers are mutually exclusive by construction: whichever branch runs CLEARS
    # the other one first, and says so.
    stale = [p for p in (pre, absent_flag) if p.exists()]
    if stale:
        print("  prior ledger     %s -- from an earlier deploy into this root; it is CLEARED below "
              "so the" % ", ".join(p.name for p in stale))
        print("                   emitted revert can never restore a stale snapshot.")
    if live.exists():
        absent_flag.unlink(missing_ok=True)
        pre.write_bytes(live.read_bytes())
        pre_sha = hashlib.sha256(pre.read_bytes()).hexdigest()
        print("  OBSERVED         PRESENT, %d B sha %s -- NOT the expected state.  Recon read this "
              "folder as ABSENT;" % (pre.stat().st_size, pre_sha[:16]))
        print("                   another session deployed an ef%03d override since.  The snapshot "
              "restores it byte for byte," % EFFECT)
        print("                   but say so in the ledger note before casting -- somebody else's "
              "cast is underneath this one.")
        state = {"existed": True, "sha256": pre_sha, "backup": str(pre)}
    else:
        pre.unlink(missing_ok=True)
        absent_flag.write_text(
            "no override existed before the probe; revert = delete\n", encoding="utf-8")
        print("  OBSERVED         ABSENT (as expected) -- revert DELETES; the resting state is stock.")
        state = {"existed": False, "sha256": None, "backup": None}

    probe = Path(d["container"]).read_bytes()
    live.parent.mkdir(parents=True, exist_ok=True)
    live.write_bytes(probe)
    rb = hashlib.sha256(live.read_bytes()).hexdigest()
    print("  DEPLOYED         %s  (readback sha %s: %s)"
          % (live, rb[:16], "OK" if rb == d["sha256"] else "*** MISMATCH ***"))
    if rb != d["sha256"]:
        raise SystemExit("FAIL: the readback does not match what we wrote -- do not cast.")

    rv = root / "revert_probe.py"
    # ⚠ NO PATH IS EVER INTERPOLATED INTO THE DOCSTRING.  A Windows path inside a triple-quoted
    # string turns `...\Users\...` into an invalid `\U` escape and the emitted script does not even
    # PARSE -- which the first rehearsal of this deploy path caught, and which would have failed at the
    # one moment the revert matters (immediately before the kit deploy, THE LEDGER TRAP).  Paths go
    # through %r into CODE lines only, where the repr escapes the backslashes.
    rv.write_text(
        '"""Auto-generated REVERT for the ef%03d ZERO-STRIPE PROBE -- stdlib only.\n\n'
        "Restores whatever the mod folder held before this probe first ran, byte for byte, or DELETES\n"
        "the override if there was none (the paths are the two literals below).  Idempotent.\n\n"
        "RUN THIS BEFORE `summon-reskin deploy`: the kit's own first-deploy snapshot is taken once per\n"
        "root and never overwritten, so a kit deploy on top of a live probe records THE PROBE as the\n"
        "pre-state and its revert would then restore the probe forever.\n"
        '"""\n'
        "import pathlib\n"
        "live = pathlib.Path(%r)\n"
        "pre = pathlib.Path(%r)\n"
        "if pre.exists():\n"
        "    live.parent.mkdir(parents=True, exist_ok=True)\n"
        "    live.write_bytes(pre.read_bytes()); print('restored', live)\n"
        "elif live.exists():\n"
        "    live.unlink(); print('deleted', live)\n"
        "else:\n"
        "    print('already reverted (absent):', live)\n"
        % (EFFECT, str(live), str(pre)), encoding="utf-8")
    # AND IT IS COMPILED HERE, not hoped over: a revert script that does not parse is worse than none.
    compile(rv.read_text(encoding="utf-8"), str(rv), "exec")
    (root / "deploy.ledger.json").write_text(
        json.dumps({"effect": EFFECT, "live": str(live), "pre": state,
                    "probe_sha256": d["sha256"], "readback_sha256": rb,
                    "revert": str(rv)}, indent=1), encoding="utf-8")
    print("  ledger           %s" % (root / "deploy.ledger.json"))
    print("  revert with      py %s" % rv)
    print("\n  *** REVERT THE PROBE BEFORE THE KIT DEPLOY.  SFX.Play re-reads the container on every "
          "cast, so the probe")
    print("      is live on the NEXT cast with no relaunch -- and so is its removal.")
    return 0


if __name__ == "__main__":                                       # pragma: no cover
    raise SystemExit(main())
