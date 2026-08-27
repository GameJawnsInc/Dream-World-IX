"""THE LEDGER COVERAGE AUDIT -- how much deployed world content does the ownership refusal
actually protect?

`mesh.deploy_override` (ff9mapkit/ff9mapkit/world/mesh.py:328-380) carries THE DEPLOY LEDGER +
THE OWNERSHIP REFUSAL (audit rec 6): every write appends a JSON line to
`<mod_folder>/.ff9world.jsonl`, and before overwriting DIFFERING bytes it refuses when the
on-disk sha256 matches no ledger entry for that cell+part+write_disc -- because 18+ concurrent
sessions share ONE install. It is a good mechanism and it has fired for real (the rec-16 compose
smoke: island mint -> coastnav stamp -> island re-mint refused our own bytes as foreign, which is
why `record_ledger_write` exists).

But the refusal has a bootstrap clause -- `mesh.py:368`:

    if shas and cur_sha not in shas and not force_overwrite ...

`if shas` means: a cell+part with NO ledger entry at all is permissive, forever. The ledger is
write-side only; there is no adopt/backfill path, so it can never learn about content it did not
itself write. Anything deployed before the ledger shipped, or by any writer that does not go
through `deploy_override`, is invisible to it permanently. That is not a bootstrap window -- it
is a standing hole the size of the pre-existing install.

This audit measures the hole. Read-only: it hashes files and reads the ledger, and writes
nothing but its own report.

Classification per deployed `.ff9mesh`:
  PROTECTED   -- the ledger has entries for this cell+part+disc AND the on-disk sha is one of
                 them. A differing overwrite is allowed (we own it); a foreign one would refuse.
  DIVERGED    -- entries exist but the on-disk sha matches NONE. The refusal WOULD fire here.
                 Either a hand edit, another session, or a non-ledgered in-place writer (the
                 `record_ledger_write` class of bug).
  UNPROTECTED -- no ledger entry for this cell+part+disc at all. The refusal is disarmed: any
                 verb may overwrite these bytes without challenge.

THE SOURCE SEAM: `--src DIR` points at a snapshot mod-folder root instead of the live install,
so a result is reproducible after the shared install drifts.
"""
import argparse
import collections
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit import config as _cfg
from ff9mapkit.world import mesh as M

OUT = Path(__file__).resolve().parent / "out" / "world-design"

# FF9_Data/WorldMap/Disc{D}/{lod}/r{y}/Block[{x}][{y}] {Part}.ff9mesh -- mesh.override_relpath
_RX = re.compile(r"Disc(?P<disc>\d+)[/\\](?P<lod>[^/\\]+)[/\\]r(?P<ry>\d+)[/\\]"
                 r"Block\[(?P<x>\d+)\]\[(?P<y>\d+)\] (?P<part>[A-Za-z0-9_]+)\.ff9mesh$")

STATES = ("PROTECTED", "DIVERGED", "UNPROTECTED")


def mod_root(mod_folder, src=None):
    if src is not None:
        return Path(src)
    return Path(_cfg.find_game_path(None)) / mod_folder


def load_ledger(root):
    """{(disc, x, y, part): [entries]} from the append-only JSONL. A torn concurrent line is
    skipped exactly as `_ledger_shas` does -- this audit must not be stricter than the gate."""
    p = root / M.LEDGER_NAME
    idx = collections.defaultdict(list)
    n_lines = n_torn = 0
    if not p.is_file():
        return idx, 0, 0
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        n_lines += 1
        try:
            e = json.loads(line)
        except ValueError:
            n_torn += 1
            continue
        cell = e.get("cell") or [None, None]
        idx[(e.get("write_disc"), cell[0], cell[1], e.get("part"))].append(e)
    return idx, n_lines, n_torn


def classify(entries, sha):
    if not entries:
        return "UNPROTECTED"
    if sha in {e.get("sha256") for e in entries}:
        return "PROTECTED"
    return "DIVERGED"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mod-folder", default="FF9CustomMap-world")
    ap.add_argument("--src", default=None,
                    help="snapshot mod-folder root (default: the live install)")
    ap.add_argument("--json", default=None,
                    help="write the report here (default: out/world-design/)")
    args = ap.parse_args()

    root = mod_root(args.mod_folder, args.src)
    wm = root / "FF9_Data" / "WorldMap"
    if not wm.is_dir():
        raise SystemExit("no WorldMap tree under %s" % root)

    ledger, n_lines, n_torn = load_ledger(root)
    print("mod root : %s" % root)
    torn = (", %d torn" % n_torn) if n_torn else ""
    print("ledger   : %d lines, %d distinct (disc,x,y,part) keys%s"
          % (n_lines, len(ledger), torn))

    rows = []
    by_disc = collections.defaultdict(collections.Counter)
    unprot_parts = collections.Counter()
    unparsed = []
    for f in sorted(wm.rglob("*.ff9mesh")):
        m = _RX.search(str(f))
        if not m:
            unparsed.append(str(f))
            continue
        disc, x, y, part = int(m["disc"]), int(m["x"]), int(m["y"]), m["part"]
        entries = ledger.get((disc, x, y, part), [])
        sha = hashlib.sha256(f.read_bytes()).hexdigest()
        state = classify(entries, sha)
        by_disc[disc][state] += 1
        if state == "UNPROTECTED":
            unprot_parts[part] += 1
        rows.append(dict(disc=disc, cell=[x, y], part=part, state=state, sha256=sha,
                         n_ledger_entries=len(entries)))

    for p in unparsed:
        print("  !! unparsed override path (NOT audited): %s" % p)

    tot = collections.Counter(r["state"] for r in rows)
    n = len(rows)
    print("\ndeployed .ff9mesh overrides: %d" % n)
    for s in STATES:
        pct = (100.0 * tot[s] / n) if n else 0.0
        print("  %-12s %5d  (%5.1f%%)" % (s, tot[s], pct))

    print("\nper write-disc:")
    for d in sorted(by_disc):
        c = by_disc[d]
        print("  Disc%-2d total=%5d  PROTECTED=%5d  DIVERGED=%4d  UNPROTECTED=%5d"
              % (d, sum(c.values()), c["PROTECTED"], c["DIVERGED"], c["UNPROTECTED"]))

    if unprot_parts:
        print("\nUNPROTECTED by part: %s" % dict(unprot_parts.most_common()))

    # NB the sidecar is named "Block[X][Y] Donor.txt" (mesh.donor_sidecar_relpath), NOT
    # "Donor.txt" -- a bare rglob("Donor.txt") silently reports zero.
    donors = list(wm.rglob("*Donor.txt"))
    baks = list(wm.rglob("*.bak-*"))
    print("\nsidecars OUTSIDE the ledger's scope entirely: %d Donor.txt "
          "(deploy_donor_sidecar does not ledger at all), %d .bak-* parked backups"
          % (len(donors), len(baks)))
    if donors:
        print("  ^ these are load-bearing: Donor.txt picks which REAL coastal block prefab the "
              "s34 divert renders on a reclaimed cell, so an overwrite silently changes the look "
              "with no ledger line and no refusal.")

    if n:
        verdict = ("%d/%d deployed overrides (%.1f%%) sit in the ownership refusal's permissive "
                   "`if shas` branch (mesh.py:368) -- any verb may overwrite them unchallenged. "
                   "The ledger is write-side only and has no adopt/backfill path, so this does "
                   "not heal over time." % (tot["UNPROTECTED"], n, 100.0 * tot["UNPROTECTED"] / n))
    else:
        verdict = "no overrides deployed"
    print("\nVERDICT: %s" % verdict)

    out = Path(args.json) if args.json else (OUT / "ledger_coverage_audit.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(dict(
        mod_root=str(root), source="snapshot" if args.src else "live install",
        ledger_lines=n_lines, ledger_keys=len(ledger), ledger_torn=n_torn,
        n_overrides=n, totals=dict(tot),
        per_disc=dict((str(d), dict(c)) for d, c in by_disc.items()),
        unprotected_by_part=dict(unprot_parts),
        n_donor_sidecars=len(donors), n_parked_backups=len(baks),
        unparsed_paths=unparsed, verdict=verdict, rows=rows), indent=1), encoding="utf-8")
    print("wrote %s" % out)


if __name__ == "__main__":
    main()
