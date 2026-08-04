"""Census every in-text presentation tag across stock FF9's field text.

The messages survey censused the SCRIPT side exhaustively (opcodes, flags, window ids, fade
brackets -- all from the 817 HW exports) but never the TEXT side: §6 is a capability list read off
the engine parser, not a usage census. This closes that: it reads the real `.mes` for every distinct
field text block in the install and counts what stock actually writes inside its entries.
"""
import collections
import json
import re
import sys

sys.path.insert(0, r"C:\gd\Dream-World-IX\.claude\worktrees\game-textbox-messages-819d17\ff9mapkit")

from ff9mapkit import dialogue as d
from ff9mapkit._fieldtext import EVENT_ID_TO_MES

TAG = re.compile(r"\[([^\]\[]*)\]")
# a colour push is a bare 6/8 hex code (or 2-hex alpha); everything else is a named tag
HEXCOL = re.compile(r"^[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$")
HEXA = re.compile(r"^[0-9A-Fa-f]{2}$")

blocks = sorted(set(EVENT_ID_TO_MES.values()))
print(f"distinct field text blocks: {len(blocks)}", flush=True)

tag_count = collections.Counter()        # tag name -> total occurrences
tag_blocks = collections.Counter()       # tag name -> how many blocks use it
color_count = collections.Counter()      # exact colour code -> occurrences
color_blocks = collections.Counter()
entry_total = 0
ok = miss = 0
samples = collections.defaultdict(list)  # tag -> a few example entry snippets

for i, b in enumerate(blocks):
    try:
        mes = d.extract_field_mes(str(b), lang="us")
    except Exception:
        mes = None
    if not mes:
        miss += 1
        continue
    ok += 1
    entry_total += mes.count("[STRT=")
    seen, seen_col = set(), set()
    for m in TAG.finditer(mes):
        raw = m.group(1)
        name = raw.split("=")[0].strip()
        if HEXCOL.match(raw) or HEXA.match(raw):
            color_count[raw.upper()] += 1
            seen_col.add(raw.upper())
            name = "<colour>"
        tag_count[name] += 1
        seen.add(name)
        if len(samples[name]) < 3:
            s = mes[max(0, m.start() - 45):m.end() + 25].replace("\n", "\\n")
            samples[name].append(f"[blk {b}] ...{s}...")
    for n in seen:
        tag_blocks[n] += 1
    for c in seen_col:
        color_blocks[c] += 1
    if i % 40 == 0:
        print(f"  ...{i}/{len(blocks)}", flush=True)

print(f"\nblocks read OK: {ok}   unreadable/absent: {miss}   entries seen: {entry_total}\n")
print(f"{'tag':<14}{'uses':>8}{'blocks':>8}   ({ok} blocks total)")
print("-" * 44)
for name, n in tag_count.most_common():
    print(f"{name:<14}{n:>8}{tag_blocks[name]:>8}")

print("\n--- COLOUR CODES (exact) ---")
for c, n in color_count.most_common(30):
    print(f"  [{c}]  {n:>6} uses in {color_blocks[c]:>3} blocks")

out = {
    "blocks_ok": ok, "blocks_missing": miss, "entries": entry_total,
    "tags": dict(tag_count), "tag_blocks": dict(tag_blocks),
    "colors": dict(color_count), "color_blocks": dict(color_blocks),
    "samples": {k: v for k, v in samples.items()},
}
with open(r"C:\Users\skaki\AppData\Local\Temp\claude\C--gd-Dream-World-IX--claude-worktrees-game-textbox-messages-819d17\beaecbb2-e258-41ea-9395-66816b6c3f5f\scratchpad\tagcensus.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1)
print("\nwrote tagcensus.json")
