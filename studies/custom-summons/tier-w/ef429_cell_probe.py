r"""TIER W rung W6b-1 -- THE STRIPED CELL CENSUS, generalized off ef211 and pinned to a default of 429.

    py ef429_cell_probe.py --from C:\gd\SCRATCH\summon-format\ef429.bytes ^
       --root C:\gd\SCRATCH\summon-format\repaint-w6b\ef429-15bpp\probe

WHY THIS PROBE EXISTS, AGAIN, ON A NEW CONTAINER
------------------------------------------------
``phoenix_cell_probe.py`` established the instrument and the law it enforces:

    AN ``so`` READER IS A BINDING, NOT A DRAW.  The so-record proves a model CAN sample a cell; it
    does not prove the model is ever drawn, or visible.  Two ef211 casts (1a, 1b) reached the FILE
    -- the live sha was verified after each deploy -- and neither figure appeared anywhere on screen,
    because cell (704,256) simply is not what the visible fire samples.

ef429 is the 15bpp lane's ONLY page-scope-safe vehicle (``W6b-SCENERY.md`` sections 1.2 / 2.3), and its
whole 15bpp write surface is TWO cells -- ``x448_y256`` and, through the per-cell map, its lower half
``x448_y384``.  Both are read by ONE ``so`` model (geom 0x2109c, 72 primitives, all ABR 1 = additive).
That is a binding.  Whether either cell is DRAWN is exactly what this probe measures, and it must be
measured BEFORE a repaint is cast, or the repaint's null result is uninterpretable -- which is the one
mistake this tier has already paid for twice.

THE INSTRUMENT.  Zero-writing is DEPTH-INVARIANT: a ``0x00`` byte is index 0 twice at 4bpp, index 0 at
8bpp, and half of the cutout word ``0x0000`` at 15bpp -- at every depth a zeroed texel is the
transparent / black-cutout value.  So a probe may lawfully mark EVERY cell, including the ones the edit
lane refuses as depth-unknown: this is a diagnostic instrument outside the edit lane, and what it writes
is the one value whose meaning does not depend on the answer it is measuring.  On ef429 the two 15bpp
cells make that concrete -- ``0x0000`` IS the hardware cutout, so a stripe there is a genuine hole in an
ADDITIVE surface, the one channel this tier has proven legible.

THE ENCODING.  Cell #k (1-based, sorted by ``(x, y, writer tag)``) gets **k evenly-spaced horizontal
zero stripes**, each ``STRIPE_ROWS`` byte-rows of 128 bytes.  A surface sampling cell #k shows k dark
bands per texture repeat -- scrolling moves the bands, never their count.  Count the bands in whatever
goes gappy and read off the cell.

    ★ THE ONE GENERALIZATION OVER THE ef211 PROBE -- COVER-AWARE PLACEMENT (``--placement cover``,
      the default).  ef211's readers cover nearly whole cells, so evenly spacing k stripes over all
      128 lines could not miss.  ef429's reader covers **31 lines of cell 1 (rows 97..127) and 32 of
      cell 2 (rows 0..31)** -- one 63-line texture band straddling the cell boundary -- so the ef211
      rule would put cell 1's single stripe at row 64, **outside every line any model reads**, and
      report a false negative on the very cell the 15bpp lane exists for.  Therefore: when a cell HAS
      an ``so`` cover, its k stripes are spread across the covered ROW SPAN; when it has none (the
      depth-unknown cells, where no prior exists), they are spread across all 128 lines exactly as
      before.  The COUNT semantics are untouched -- only where the count is drawn -- and every cell's
      placement rule is printed in the legend so a reader can tell which cells carry the weaker prior.

    ⚠ AND THE TRADE-OFF THAT BUYS, STATED.  ef429's cell 1 has TWO regions and only one of them has a
      reader: lines 97..127 are a FLAT WHITE 0xffff block (the additive glow the ``so`` model samples),
      while lines 0..96 hold real pictorial art -- eye / sucker figures -- that **no ``so`` record
      binds at all**.  If what reaches the screen is that unbound art (drawn by the id-3 program's own
      primitives, which is open question Q1), a cover-placed stripe misses it and a whole-cell stripe
      misses the glow instead.  One deploy cannot test both without making "count the bands" ambiguous,
      so it is a FLAG rather than a fudge: ``--placement cover`` answers the question CAST B depends on
      and runs first; ``--placement whole-cell`` is the same script, one flag and one revert away, and
      is the named follow-up when the first shows nothing.

THE LEDGER.  This script only ever writes under ``--root``.  It stages the probe container and emits a
``deploy_probe.py`` / ``revert_probe.py`` pair beside it; the deploy script is stdlib-only, takes a
FIRST-DEPLOY SNAPSHOT of whatever the mod folder already held, and is ``--root``-rebasable so it can be
rehearsed against a temp folder.  **This script never touches the install itself.**

PROVENANCE.  No stock byte run appears in this file.  The container is read at run time and every
destination goes through ``ff9mapkit.summons.export.assert_local_only``; the probe container is
SE-derived and stays in SCRATCH / the install.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "..", "..", "ff9mapkit"))

from ff9mapkit.summons import container as EC                    # noqa: E402
from ff9mapkit.summons import export as EX                       # noqa: E402
from ff9mapkit.summons import repaint as RP                      # noqa: E402
from ff9mapkit.summons import reskin as RS                       # noqa: E402

DEFAULT_EFFECT = 429
DEFAULT_ROOT = r"C:\gd\SCRATCH\summon-format\repaint-w6b\ef429-15bpp\probe"
DEFAULT_CORPUS_DIR = r"C:\gd\SCRATCH\summon-format"
DEFAULT_MOD_ROOT = (r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX"
                    r"\FF9CustomMap")
#: byte-rows per stripe (128 B each); bold enough to read on video at cast distance.
STRIPE_ROWS = 6
ROW_BYTES = 128
CELL_ROWS = 128


# ------------------------------------------------------------------------------- the stripe encoding
def stripe_rows(k: int, lo: int, hi: int) -> List[int]:
    """The TOP row of each of ``k`` evenly-spaced stripes inside the inclusive line span ``lo..hi``.

    The ef211 rule with the span made a parameter.  ``lo=0, hi=127`` reproduces it exactly, which is
    what a cell with no ``so`` cover gets; a covered cell gets its own span so the mark cannot land
    where nothing samples it.
    """
    span = hi - lo + 1
    rows: List[int] = []
    for s in range(k):
        centre = lo + int((s + 0.5) * span / k)
        rows.append(max(lo, min(hi - STRIPE_ROWS + 1, centre - STRIPE_ROWS // 2)))
    return rows


def striped(cell_bytes: bytes, k: int, lo: int, hi: int) -> bytes:
    """``k`` zero stripes of ``STRIPE_ROWS`` byte-rows, inside ``lo..hi``, over a 0x4000-byte cell."""
    out = bytearray(cell_bytes)
    for top in stripe_rows(k, lo, hi):
        for r in range(top, min(CELL_ROWS, top + STRIPE_ROWS)):
            out[r * ROW_BYTES:(r + 1) * ROW_BYTES] = b"\x00" * ROW_BYTES
    return bytes(out)


def cover_rows(blob: bytes, cell) -> Optional[Sequence[int]]:
    """The inclusive ``(lo, hi)`` LINE span every ``so`` reader of ``cell`` samples, or None."""
    rows = set()
    for m in RP.bound_models(blob):
        if cell in m.cover:
            rows |= {hw // RS.PAGE_CELL_W for hw in m.cover[cell]}
    return (min(rows), max(rows)) if rows else None


# ---------------------------------------------------------------------------------- the emitted pair
_DEPLOY = r'''#!/usr/bin/env python3
"""Auto-generated LIVE deploy for the ef%(ef)03d STRIPED CELL CENSUS -- stdlib only, no ff9mapkit import.

    py deploy_probe.py [--root <mod folder>]

Copies the staged probe container over the mod folder's ef%(ef)03d override, taking a FIRST-DEPLOY
SNAPSHOT of whatever that folder held beforehand.  ``--root`` defaults to the live FF9CustomMap; pass a
temp folder to rehearse.  The snapshot is per-root and is written once and never overwritten, so a
re-deploy still reverts all the way back to the pre-probe state.  Idempotent.
"""
import hashlib, json, os, shutil, sys
from pathlib import Path

PLAN = json.loads(%(plan)r)


def parse_root(argv):
    root, rest, i = PLAN["default_mod_root"], [], 0
    while i < len(argv):
        a = argv[i]
        if a == "--root":
            if i + 1 >= len(argv):
                print("FAIL: --root needs a directory"); raise SystemExit(2)
            root = argv[i + 1]; i += 2; continue
        if a.startswith("--root="):
            root = a.split("=", 1)[1]; i += 1; continue
        if a in ("-h", "--help"):
            print(__doc__); raise SystemExit(0)
        rest.append(a); i += 1
    if rest:
        print("FAIL: unexpected argument(s): %%s" %% " ".join(rest)); raise SystemExit(2)
    return Path(root)


def snapshot_dir(root):
    """One ledger PER ROOT, so a rehearsal under a temp root can never consume or overwrite the real
    first-deploy snapshot."""
    key = hashlib.sha256(str(Path(root).resolve()).lower().encode("utf-8")).hexdigest()[:12]
    return Path(PLAN["snapshot_base"]) / key


def _sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv):
    root = parse_root(argv)
    if not root.is_dir():
        print("FAIL: mod folder not found: %%s" %% root); return 1
    if (root / "ModFileList.txt").exists():
        print("REFUSING: %%s has a ModFileList.txt.  TryFindAssetInModOnDisc TRUSTS that list and "
              "never calls File.Exists, so an unlisted override is INVISIBLE.  Handle the list by "
              "hand, then re-run." %% root)
        return 1
    src = Path(PLAN["src"])
    if not src.is_file():
        print("FAIL: staged probe container missing: %%s" %% src); return 1
    got = _sha(src)
    if got != PLAN["sha256"]:
        print("FAIL: %%s sha256 %%s != the staged build's %%s -- re-run ef%(ef)03d_cell_probe.py."
              %% (src, got, PLAN["sha256"]))
        return 1

    dest = root / PLAN["rel"]
    snap_dir = snapshot_dir(root)
    snap_file = snap_dir / "snapshot.json"
    if snap_file.exists():
        snap = json.loads(snap_file.read_text(encoding="utf-8"))
        print("snapshot: reusing the FIRST-DEPLOY snapshot at %%s (%%s)" %% (snap_file, snap.get("taken")))
    else:
        snap_dir.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            backup = snap_dir / ("%%s.pre-probe" %% dest.name)
            shutil.copyfile(dest, backup)
            entry = {"rel": PLAN["rel"], "existed": True, "sha256": _sha(dest),
                     "backup": str(backup)}
            print("snapshot: TAKEN -- saved %%s (sha %%s)" %% (PLAN["rel"], entry["sha256"][:16]))
        else:
            entry = {"rel": PLAN["rel"], "existed": False, "sha256": None, "backup": None}
            print("snapshot: TAKEN -- no prior override existed, so revert DELETES")
        snap = {"taken": "first deploy", "root": str(root.resolve()), "entry": entry}
        tmp = snap_file.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(snap, indent=2), encoding="utf-8")
        os.replace(tmp, snap_file)
        print("snapshot: %%s" %% snap_file)

    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dest)
    rb = _sha(dest)
    if rb != PLAN["sha256"]:
        print("FAIL: write verification at %%s -- readback %%s != what we wrote" %% (dest, rb[:16]))
        return 1
    print("deployed %%s  (%%d B, sha %%s)" %% (dest, dest.stat().st_size, rb[:16]))
    print()
    print(PLAN["note"])
    print("revert with: py %%s%%s" %% (PLAN["revert_script"],
          "" if str(root) == PLAN["default_mod_root"] else ' --root "%%s"' %% root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
'''

_REVERT = r'''#!/usr/bin/env python3
"""Auto-generated REVERT for the ef%(ef)03d STRIPED CELL CENSUS -- stdlib only.

    py revert_probe.py [--root <mod folder>]

Restores whatever the mod folder held before ``deploy_probe.py`` first ran against THAT root, byte for
byte, or deletes the override if there was none.  Idempotent; safe to run twice.
"""
import hashlib, json, sys
from pathlib import Path

PLAN = json.loads(%(plan)r)


def parse_root(argv):
    root, i = PLAN["default_mod_root"], 0
    while i < len(argv):
        a = argv[i]
        if a == "--root":
            root = argv[i + 1]; i += 2; continue
        if a.startswith("--root="):
            root = a.split("=", 1)[1]; i += 1; continue
        if a in ("-h", "--help"):
            print(__doc__); raise SystemExit(0)
        i += 1
    return Path(root)


def main(argv):
    root = parse_root(argv)
    key = hashlib.sha256(str(root.resolve()).lower().encode("utf-8")).hexdigest()[:12]
    snap_file = Path(PLAN["snapshot_base"]) / key / "snapshot.json"
    if not snap_file.is_file():
        print("nothing to revert: no snapshot for root %%s (%%s)" %% (root, snap_file))
        return 0
    e = json.loads(snap_file.read_text(encoding="utf-8"))["entry"]
    dest = root / e["rel"]
    if e["existed"]:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(Path(e["backup"]).read_bytes())
        print("restored %%s (%%d B)" %% (dest, dest.stat().st_size))
    else:
        if dest.exists():
            dest.unlink()
            print("deleted %%s (there was no override before the probe)" %% dest)
        else:
            print("already absent: %%s" %% dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
'''


def emit_scripts(root: Path, effect: int, container: Path, sha: str, mod_root: str) -> Dict[str, str]:
    plan = json.dumps({
        "effect": effect,
        "label": "ef%03d-striped-cell-census" % effect,
        "src": str(container),
        "rel": "FF9_Data/SpecialEffects/ef%03d" % effect,
        "sha256": sha,
        "default_mod_root": mod_root,
        "snapshot_base": str(root / "live-snapshot"),
        "revert_script": str(root / "revert_probe.py"),
        "note": ("this artifact is STOCK ef%03d with every page-cell zero-striped by its 1-based cell "
                 "number -- a DIAGNOSTIC, not an edit.  It REPLACES whatever container the mod folder "
                 "holds for that effect; the first-deploy snapshot restores it byte for byte.  "
                 "SFX.Play re-reads the container on every cast, so the probe is live on the NEXT "
                 "cast -- no relaunch." % effect),
    }, indent=1)
    out = {}
    for name, tmpl in (("deploy_probe.py", _DEPLOY), ("revert_probe.py", _REVERT)):
        p = root / name
        p.write_text(tmpl % {"ef": effect, "plan": plan}, encoding="utf-8")
        out[name] = str(p)
    return out


# ------------------------------------------------------------------------------------------- the run
def generate(effect: int, from_path: Optional[str], root: str, mod_root: str,
             only: Optional[str] = None, placement: str = "cover") -> Dict[str, object]:
    src = from_path or os.path.join(DEFAULT_CORPUS_DIR, "ef%03d.bytes" % effect)
    stock = Path(src).read_bytes()
    root_p = Path(EX.assert_local_only(root))
    root_p.mkdir(parents=True, exist_ok=True)

    cells = RS.page_cells(stock)
    order = sorted(cells.values(), key=lambda pc: (pc.x, pc.y, pc.tag))
    if not order:
        raise SystemExit("ef%03d declares no page-cells -- nothing to stripe" % effect)

    blob = bytearray(stock)
    legend: List[dict] = []
    for i, pc in enumerate(order):
        k = i + 1
        cov = cover_rows(stock, (pc.x, pc.y)) if placement == "cover" else None
        lo, hi = cov if cov else (0, CELL_ROWS - 1)
        rec = {"k": k, "name": pc.name, "kind": pc.kind, "offset": pc.off, "cell": [pc.x, pc.y],
               "span": [lo, hi], "placement": "so-cover" if cov else "whole-cell",
               "stripe_tops": stripe_rows(k, lo, hi), "written": True}
        if only is not None and pc.name != only:
            rec["written"] = False
            rec["stripe_tops"] = []
        else:
            blob[pc.off:pc.off + pc.nbytes] = striped(
                bytes(stock[pc.off:pc.off + pc.nbytes]), k, lo, hi)
        legend.append(rec)
    if only is not None and not any(r["written"] for r in legend):
        raise SystemExit("--only %r matches no cell; the census names are:\n%s"
                         % (only, "\n".join("  " + pc.name for pc in order)))

    probe = bytes(blob)
    EC.parse_header(probe, strict=True)                          # the probe must still parse
    if len(probe) != len(stock):
        raise SystemExit("the probe changed the container's LENGTH -- refusing")
    changed = sum(1 for a, b in zip(stock, probe) if a != b)

    out = root_p / ("ef%03d.cellprobe" % effect)
    out.write_bytes(probe)
    sha = hashlib.sha256(probe).hexdigest()
    scripts = emit_scripts(root_p, effect, out, sha, mod_root)
    d = {"effect": effect, "source": src, "root": str(root_p), "container": str(out),
         "sha256": sha, "stock_sha256": hashlib.sha256(stock).hexdigest(),
         "bytes": len(probe), "changed_bytes": changed, "cells": len(order),
         "stripe_rows": STRIPE_ROWS, "placement": placement, "legend": legend, "scripts": scripts}
    (root_p / "probe.derivation.json").write_text(json.dumps(d, indent=1), encoding="utf-8")
    return d


def report(d: Dict[str, object]) -> List[str]:
    L = ["THE STRIPED CELL CENSUS -- ef%03d, %d cells marked, placement rule %r  <- %s"
         % (d["effect"], d["cells"], d["placement"], d["source"]),
         "  k  cell                        placement    lines      stripe tops"]
    for r in d["legend"]:
        L.append("  %2d %-27s %-12s %3d..%-3d  %s%s"
                 % (r["k"], r["name"], r["placement"], r["span"][0], r["span"][1],
                    r["stripe_tops"], "" if r["written"] else "   UNTOUCHED (control)"))
    L += ["  probe container  %d B  sha256 %s" % (d["bytes"], d["sha256"]),
          "  stock sha256     %s" % d["stock_sha256"],
          "  changed bytes    %d (%.1f%% of the container)"
          % (d["changed_bytes"], 100.0 * d["changed_bytes"] / d["bytes"]),
          "  staged           %s" % d["container"],
          "  deploy           py %s [--root <mod folder>]" % d["scripts"]["deploy_probe.py"],
          "  revert           py %s [--root <mod folder>]" % d["scripts"]["revert_probe.py"]]
    return L


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--effect", type=int, default=DEFAULT_EFFECT,
                    help="the effect id to stripe (default %d)" % DEFAULT_EFFECT)
    ap.add_argument("--from", dest="from_path", default=None,
                    help="the STOCK container FILE to stripe (default <corpus>/ef<NNN>.bytes)")
    ap.add_argument("--root", default=DEFAULT_ROOT, help="staging root (LOCAL-ONLY)")
    ap.add_argument("--mod-folder", default=DEFAULT_MOD_ROOT,
                    help="the mod folder the emitted deploy script defaults to")
    ap.add_argument("--only", default=None, metavar="CELL",
                    help="stripe ONLY this cell (e.g. cell.s0.x448_y256), keeping its canonical "
                         "stripe count from the full-census legend -- the surgical confirm: exactly "
                         "the surfaces reading this cell band, everything else is its own control")
    ap.add_argument("--placement", default="cover", choices=("cover", "whole-cell"),
                    help="where a covered cell's k stripes go: inside the `so` reader's own line span "
                         "(default -- the question CAST B depends on), or evenly over all 128 lines "
                         "(the ef211 rule -- the follow-up when `cover` shows nothing, because a "
                         "cell's UNBOUND lines may be what the id-3 program draws)")
    a = ap.parse_args(argv)
    d = generate(a.effect, a.from_path, a.root, a.mod_folder, a.only, a.placement)
    print("\n".join(report(d)))
    print("\n  NOTHING WAS DEPLOYED.  The install is untouched; run the deploy script above when the "
          "bench row is live.")
    return 0


if __name__ == "__main__":                                       # pragma: no cover
    raise SystemExit(main())
