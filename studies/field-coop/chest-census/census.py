"""Census of stock tag-2 (Range) bodies that poll Confirm/Special with control on -- the s161 chest relay's scope.

Reads the Hades Workshop text exports (not in the repo; `C:\\gd\\FFIX\\reference\\test2\\test2_*.txt`, one per
field-script, several copies of each entry per file) and counts each (file, entry) once. A body is in scope when
its tag-2 function holds an `IsButton(mask)` whose mask names Confirm (0x20000) or Special (0x80000); the JP
exports poll Cancel|Special (589824) instead, which the engine's own layout swap answers (ETb.ProcessJapaneseLayout).

    py studies/field-coop/chest-census/census.py [export_dir]

Printed for the 2026-10-28 design (studies/field-coop/CHEST-RELAY.md, "The census").
"""
import collections
import glob
import os
import re
import sys

CONFIRM, SPECIAL = 0x20000, 0x80000
CHEST_MODELS = {75, 91, 701, 702}


def functions(lines):
    """[(tag, name, start, end)] for every `#HW newfunction` block."""
    out, cur = [], None
    for i, line in enumerate(lines):
        m = re.match(r"#HW newfunction (\d+)", line)
        if m:
            if cur:
                out.append(tuple(cur) + (i,))
            cur = [int(m.group(1)), None, i]
            continue
        m = re.match(r"Function (\S+)", line)
        if m and cur and cur[1] is None:
            cur[1] = m.group(1)
        if line.startswith("#HW newentry") and cur:
            out.append(tuple(cur) + (i,))
            cur = None
    if cur:
        out.append(tuple(cur) + (len(lines),))
    return out


def main(export_dir):
    cats = collections.Counter()
    gated = collections.Counter()
    actor = collections.Counter()
    examples = collections.defaultdict(list)
    model_use = collections.Counter()           # (model, named Chest*, polls in tag 2)
    chest_no_poll = []
    for path in sorted(glob.glob(os.path.join(export_dir, "test2_*.txt"))):
        lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
        by_entry = collections.defaultdict(dict)
        for tag, name, s, e in functions(lines):
            if name:
                by_entry[name.rsplit("_", 1)[0]].setdefault(tag, "\n".join(lines[s:e]))
        short = os.path.basename(path)[len("test2_"):-len(".txt")]
        for ent, fs in by_entry.items():
            init, body = fs.get(0, ""), fs.get(2, "")
            models = [int(x) for x in re.findall(r"SetModel\(\s*(\d+)", init)]
            polls = any(int(x) & (CONFIRM | SPECIAL) for x in re.findall(r"IsButton\(\s*(\d+)L?\s*\)", body))
            for m in models:
                if m in CHEST_MODELS:
                    model_use[(m, "Chest" in ent, polls)] += 1
            if "Chest" in ent and not polls:
                chest_no_poll.append(short + ":" + ent)
            if not polls:
                continue
            called = "\n".join(fs.get(int(t), "") for t in re.findall(r"RunScript\w*\(\s*\d+,\s*255,\s*(\d+)\s*\)", body))
            both = body + "\n" + called
            if any(m in CHEST_MODELS for m in models):
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
            actor[cat] += bool(models)
            if len(examples[cat]) < 5:
                examples[cat].append(short + ":" + ent)
    print("tag-2 Confirm/Special polls, unique (field-script, entry):", sum(cats.values()))
    for cat, n in cats.most_common():
        print("  %-48s %4d  facing-gated %3d  actors %3d  e.g. %s" % (cat, n, gated[cat], actor[cat], examples[cat]))
    print("chest models (model, named Chest*, polls in tag 2):", sorted(model_use.items()))
    print("Chest* entries with no tag-2 poll (out of scope):", len(chest_no_poll), chest_no_poll)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else r"C:\gd\FFIX\reference\test2")
