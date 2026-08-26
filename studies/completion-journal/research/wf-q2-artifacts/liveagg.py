"""Aggregate the JOIN over CONSTANT-FOLD-LIVE rows only, and look for bit collisions."""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import foldcheck as F                                            # noqa: E402

from ff9mapkit.extract import EventBundle                        # noqa: E402
from ff9mapkit.eb import EbScript                                # noqa: E402
from ff9mapkit.eb.cfg import FieldFlow                           # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

rows = json.load(open(F.REPO + "/studies/completion-journal/research/treasure_join.json",
                      encoding="utf-8"))["grants"]
names = {}
for line in open(F.REPO + "/reference/field-manifest.tsv", encoding="utf-8"):
    p = line.rstrip("\n").split("\t")
    if len(p) >= 3:
        try:
            names.setdefault(int(p[1]), p[2])
        except ValueError:
            pass

by_field = defaultdict(list)
for r in rows:
    by_field[r["field"]].append(r)

bundle = EventBundle()
live_rows = []
for fid, rs in sorted(by_field.items()):
    try:
        eb = EbScript.from_bytes(bundle.eb_for_id(fid))
        ff = FieldFlow.build(eb)
    except Exception:
        continue
    flows = defaultdict(list)
    for (ei, fi), fl in ff.flows.items():
        flows[(ei, eb.entries[ei].funcs[fi].tag)].append(fl)
    cache = {}
    for r in rs:
        for fl in flows.get((r["entry"], r["func"]), []):
            bi = fl._block_of.get(r["off"])
            if bi is None:
                continue
            key = id(fl)
            if key not in cache:
                cache[key] = F.folded_reachable(fl, eb.data)
            if bi in cache[key]:
                live_rows.append(r)
            break

cls = Counter(r["cls"] for r in live_rows)
tot = len(live_rows)
strong = cls["latch"] + cls["latch-write"]
print("LIVE rows", tot, dict(sorted(cls.items())))
print("live strong_single_latch", strong, "any_single_latch",
      strong + cls["latch-guard"],
      "pct %.1f" % ((strong + cls["latch-guard"]) / tot * 100))

li = [r for r in live_rows if r["kind"] == "item" and isinstance(r.get("latch"), int)]
print("live ITEM rows with an int latch:", len(li))
bits = defaultdict(set)
bitfields = defaultdict(set)
for r in li:
    bits[r["latch"]].add(r["id"])
    bitfields[r["latch"]].add(r["field"])
print("distinct latch bits over live item rows:", len(bits))
coll = {b: sorted(v) for b, v in bits.items() if len(v) > 1}
print("latch bits claimed by MORE THAN ONE item id:", len(coll))
for b, v in sorted(coll.items())[:15]:
    fl = sorted(bitfields[b])
    print("   bit", b, "items", v, "fields", [(f, names.get(f, "?")) for f in fl][:6])
multi = {b: sorted(v) for b, v in bitfields.items() if len(v) > 1}
print("latch bits claimed in MORE THAN ONE field:", len(multi))
th = sorted({r["latch"] for r in li if r.get("th")})
print("distinct TH-scored item latches over LIVE rows:", len(th))
print("(census claimed 276 over all rows)")

# gil: how many LIVE literal gil grants remain, and are any above the party cap?
lg = [r for r in live_rows if r["kind"] == "gil"]
lit = [r for r in lg if r.get("amount") is not None]
print("live gil rows", len(lg), "of which literal", len(lit),
      "above 9,999,999:", sum(1 for r in lit if r["amount"] > 9999999))
