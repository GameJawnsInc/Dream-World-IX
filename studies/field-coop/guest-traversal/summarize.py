"""Summarize full_vN.json + wm_vN.json into the report tables (stdout)."""
import json
import sys
from collections import Counter, defaultdict

full = json.load(open(sys.argv[1], encoding="utf-8"))
wm = json.load(open(sys.argv[2], encoding="utf-8"))
rows = full["rows"]
wmk = {(x["fid"], x["root"], x["entry"]): x for x in wm}
MOVERS = {"ladder-navigable", "ladder-auto", "jump", "carry-loop", "walk", "teleport"}
P = print

P("== fields:", full["stats"])
P("\n== class x root")
roots = ["QUAD", "NPC", "TREAD-POLL", "LOOP-POLL", "CARD"]
classes = Counter(r["class"] for r in rows)
P(f"{'class':20s}" + "".join(f"{k:>11s}" for k in roots) + f"{'ALL':>8s}")
for cl, _ in classes.most_common():
    n = [sum(1 for r in rows if r["root"] == k and r["class"] == cl) for k in roots]
    P(f"{cl:20s}" + "".join(f"{v:11d}" for v in n) + f"{sum(n):8d}")
P(f"{'TOTAL':20s}" + "".join(f"{sum(1 for r in rows if r['root']==k):11d}" for k in roots) + f"{len(rows):8d}")

P("\n== QUAD: player-moving interactions (loco kind x class), with walkmesh verdict")
q = [r for r in rows if r["root"] == "QUAD" and r["loco"] in MOVERS]
P(f"  player-moving QUADs: {len(q)} of {sum(1 for r in rows if r['root']=='QUAD')}")
tab = defaultdict(Counter)
for r in q:
    tab[(r["loco"], r["class"])][wmk.get((r["fid"], r["root"], r["entry"]), {}).get("wm", "?")] += 1
for k in sorted(tab, key=lambda k: (k[0], -sum(tab[k].values()))):
    P(f"  {k[0]:18s} {k[1]:18s} n={sum(tab[k].values()):3d}  {dict(tab[k])}")

safe_cls = {"LOCO-ONLY", "LOCO+LATCH", "LOCO+EXIT", "LOCO+ACTORS", "LOCO+ACTORS+LATCH"}
guest = [r for r in q if r["class"] in safe_cls]
P(f"\n== GUEST-LOCAL CANDIDATES (player-moving QUAD, class in {sorted(safe_cls)}): {len(guest)}")
P("   by class:", Counter(r["class"] for r in guest))
P("   by kind :", Counter(r["loco"] for r in guest))
P("   walkmesh:", Counter(wmk.get((r["fid"], r["root"], r["entry"]), {}).get("wm") for r in guest))
P("   fields  :", len({r["fid"] for r in guest}))
P("   gates   :", Counter(g for r in guest for g in r["gate"]))
P("   gated by glob/scenario:", sum(1 for r in guest if set(r["gate"]) & {"glob", "scenario"}),
  " by map(non-bracket):", sum(1 for r in guest if "map" in r["gate"]),
  " by local:", sum(1 for r in guest if "local" in r["gate"]))
P("   call shapes:", Counter(tuple(sorted({pc[2] for pc in r["player_calls"]})) for r in guest))

P("\n== STATEFUL player-moving QUADs: why (reason x count)")
st = [r for r in q if r["class"] == "STATEFUL"]
P("  n =", len(st), Counter(x for r in st for x in r["reasons"]).most_common())

P("\n== EDGE CASES among player-moving QUADs")
P("  windows inside the PLAYER's climb/jump body:", [(r["fid"], r["entry"], r["loco"], r["class"])
                                                      for r in q if r["windows_in_player"]])
hp = [(r["fid"], r["entry"], r["loco"], [k for k in r["keys"] if k[1] and int(k[1], 16) & 0x10F3F01]) for r in q
      if any(k[1] and (int(k[1], 16) & 0x10F3F01) for k in r["keys"])]
P("  HOST-OWNED key polls inside (Confirm/Cancel/etc):", hp)
P("  direction-key polls (navigable):", sum(1 for r in q if any(k[1] and (int(k[1], 16) & 0xF0) for k in r["keys"])))
P("  multi-floor (>=2 floors touched):", sum(1 for r in q
      if len(wmk.get((r['fid'], r['root'], r['entry']), {}).get('floors', [])) >= 2))
P("  ends in Field()/WorldMap():", [(r["fid"], r["entry"], r["loco"], r["class"], r["exit_targets"][:2]) for r in q if r["exit_targets"]])
P("  RunScriptAsync / RunScript dispatch (not Sync):",
  [(r["fid"], r["entry"], r["loco"], r["class"], [pc[2] for pc in r["player_calls"]][:3]) for r in q
   if any(pc[2] != "Sync" for pc in r["player_calls"])])
P("  ATE inside:", [(r["fid"], r["entry"]) for r in q if "ate" in r["buckets"]])
P("  unresolved calls:", [(r["fid"], r["entry"], r["unresolved"]) for r in rows if r["unresolved"]])
P("  missing call targets (Request no-op):", sum(1 for r in rows if r["missing"]))
P("  order (window vs move first) in QUADs having BOTH:", Counter(r["order"] for r in rows
      if r["root"] == "QUAD" and "window" in r["buckets"] and "loco_player" in r["buckets"]))
P("  'anim-only' QUADs (player animates, no displacement):",
  Counter(r["class"] for r in rows if r["root"] == "QUAD" and r["loco"] == "anim-only"))

P("\n== FLAVOR (window, no persistent write) by root:", {k: sum(1 for r in rows if r["root"] == k and r["class"] in
   ("FLAVOR-TALK", "FLAVOR+CHOICE", "FLAVOR+LATCH")) for k in roots})
P("== GLOB-gated FLAVOR NPC talks:", sum(1 for r in rows if r["root"] == "NPC" and r["class"].startswith("FLAVOR")
                                       and set(r["gate"]) & {"glob", "scenario"}))

P("\n== examples: guest-local candidates")
for r in sorted(guest, key=lambda r: (r["loco"], r["fid"])):
    w = wmk.get((r["fid"], r["root"], r["entry"]), {})
    P(f"  {r['fid']:5d} {r['name'][:30]:30s} e{r['entry']:<3d} {r['loco']:17s} {r['class']:17s} {w.get('wm','?'):17s}"
      f" gate={r['gate']} pc={r['player_calls'][:2]} exit={r['exit_targets'][:1]}")
