"""Census of stock tag-2 (Range) bodies that poll Confirm/Special with control on -- the s160 chest relay's scope.

Reads the Hades Workshop text exports (not in the repo; `C:\\gd\\FFIX\\reference\\test2\\test2_*.txt`, one per field
script). Each export holds the whole script once per language block (`#HW language us`, then `jp`, ...); only the FIRST
block is read, and entries are keyed by their `#HW newentry N` index -- never by name: HW names an entry after its model,
so a field with three model-75 chests has three entries all called `ChestA`.

A body is in scope when its tag-2 function holds an `IsButton(mask)` whose mask names Confirm (0x20000) or Special
(0x80000); the JP exports poll Cancel|Special (589824) instead, which the engine's own layout swap answers
(ETb.ProcessJapaneseLayout) -- the first block is the `us` one, so Confirm is what it reads.

    py studies/field-coop/chest-census/census.py [export_dir]

Printed for studies/field-coop/CHEST-RELAY.md, "The census". (The 2026-10-28 first cut keyed entries by name and printed
186 / 140 / 9; the pre-build review caught the merge.)
"""
import collections
import glob
import os
import re
import sys

CONFIRM, SPECIAL = 0x20000, 0x80000
CHEST_MODELS = {75, 91, 701, 702}


def first_block(lines):
    """The lines of the first `#HW language` block (the whole file when it has none)."""
    starts = [i for i, ln in enumerate(lines) if ln.startswith("#HW language ")]
    if len(starts) < 2:
        return lines
    return lines[starts[0]:starts[1]]


def entries(lines):
    """{entry index: {tag: function text}} -- the first function per tag in each `#HW newentry` block."""
    out = collections.defaultdict(dict)
    entry, tag, start = None, None, None

    def close(end):
        if entry is not None and tag is not None:
            out[entry].setdefault(tag, "\n".join(lines[start:end]))

    for i, line in enumerate(lines):
        m = re.match(r"#HW newentry (\d+)", line)
        if m:
            close(i)
            entry, tag, start = int(m.group(1)), None, None
            continue
        m = re.match(r"#HW newfunction (\d+)", line)
        if m:
            close(i)
            tag, start = int(m.group(1)), i
    close(len(lines))
    return out


def main(export_dir):
    cats = collections.Counter()
    gated = collections.Counter()
    examples = collections.defaultdict(list)
    chest_entries = chest_polling = 0
    by_model = collections.Counter()
    no_poll = []
    files_with_polling_chest = set()
    for path in sorted(glob.glob(os.path.join(export_dir, "test2_*.txt"))):
        lines = first_block(open(path, encoding="utf-8", errors="replace").read().splitlines())
        short = os.path.basename(path)[len("test2_"):-len(".txt")]
        for ent, fs in sorted(entries(lines).items()):
            init, body = fs.get(0, ""), fs.get(2, "")
            models = [int(x) for x in re.findall(r"SetModel\(\s*(\d+)", init)]
            polls = any(int(x) & (CONFIRM | SPECIAL) for x in re.findall(r"IsButton\(\s*(\d+)L?\s*\)", body))
            chest = any(m in CHEST_MODELS for m in models)
            if chest:
                chest_entries += 1
                if polls:
                    chest_polling += 1
                    files_with_polling_chest.add(short)
                    by_model[next(m for m in models if m in CHEST_MODELS)] += 1
                else:
                    no_poll.append("%s:%d" % (short, ent))
            if not polls:
                continue
            called = "\n".join(fs.get(int(t), "") for t in re.findall(r"RunScript\w*\(\s*\d+,\s*255,\s*(\d+)\s*\)", body))
            both = body + "\n" + called
            if chest:
                cat = "chest"
            elif re.search(r"\bAdd(Item|Gil)\(|AddCard", both):
                cat = "pickup (item/gil in the body)"
            elif re.search(r"\bField\(", both):
                cat = "gateway (Field)"
            elif "GetDialogChoice" in both:
                cat = "menu/choice"
            elif re.search(r"Window(Sync|Async)\(", both):
                cat = "sign/text"
            else:
                cat = "other (indirect: a player function, a barrel)"
            cats[cat] += 1
            gated[cat] += "GetEntryAngle(250)" in body
            if len(examples[cat]) < 5:
                examples[cat].append("%s:%d" % (short, ent))
    print("tag-2 Confirm/Special polls (first language block, by entry index):", sum(cats.values()))
    for cat, n in cats.most_common():
        print("  %-48s %4d  facing-gated %3d  e.g. %s" % (cat, n, gated[cat], examples[cat]))
    print("chest-model entries:", chest_entries, "| polling in tag 2:", chest_polling, "in", len(files_with_polling_chest),
          "field scripts | by model:", dict(by_model))
    print("chest-model entries with no tag-2 Confirm/Special poll (out of scope):", len(no_poll), no_poll)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else r"C:\gd\FFIX\reference\test2")
