"""Seed one walkthrough section's ``[[entry]]`` skeletons from the treasure_join v2 atlas.

The SCHEMA.md division of labor: the machine seeds every mechanical column (id, latch bit, item
id, gil amount, TH points, category, source, provenance) and the human writes the prose + confirms
the section assignment. This script is the machine half. It never invents prose -- ``title`` and
``detail`` are emitted EMPTY for the authoring pass.

Usage:
    py seed_section.py <section-id> --rooms "Prima Vista/" [--rooms ...]
                       [--bits 7171,7172] [--exclude 7206,7207] [--order 7174,7175,...]

Room filters match by prefix against the atlas event's room names. --order pins the walkthrough
order (unlisted bits follow, atlas order); --exclude drops events that belong to a LATER section
even though their rooms match (e.g. a shop that does not exist yet at this point of the story --
record the reason in the section's authoring notes).

Output: TOML on stdout, ready to paste into data/journal_catalog.toml for the prose pass.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ATLAS = _HERE / "treasure_join.json"


def category_of(ev: dict) -> str:
    """The seed's category guess from the reward pool -- the human confirms."""
    pools = {r.get("pool") for r in ev["rewards"] if r["kind"] == "item"}
    if pools == {"card"}:
        return "card"
    if pools == {"key"}:
        return "keyitem"
    return "treasure"


def emit(ev: dict, section: str) -> str:
    rew = ev["rewards"]
    lines = [
        "[[entry]]",
        f'id       = "treasure.b{ev["bit"]}"',
        f'section  = "{section}"',
        f'category = "{category_of(ev)}"',
        'title    = ""',
        'detail   = ""',
        f'latch    = {ev["bit"]}',
    ]
    for r in rew:
        if r["kind"] == "item":
            lines.append(f'item     = {r["id"]}            # {r.get("label", "?")} (runtime-resolved in-game)')
        elif r["kind"] == "gil":
            lines.append(f'gil      = {r["amount"]}')
    if ev.get("th"):
        lines.append(f'th       = {ev["th"]}')
    rooms = "/".join(sorted({n for n in ev["names"]}))
    lines.append(f'source   = "treasure_join v2 bit {ev["bit"]} -- {rooms}, fields {sorted(set(ev["fields"]))}"')
    return "\n".join(lines) + "\n"


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("section")
    ap.add_argument("--rooms", action="append", default=[], help="room-name prefix filter")
    ap.add_argument("--bits", default="", help="extra bits to include, comma-separated")
    ap.add_argument("--exclude", default="", help="bits to drop (belong to a later section)")
    ap.add_argument("--order", default="", help="walkthrough order, comma-separated bits first")
    a = ap.parse_args(argv)

    atlas = json.loads(_ATLAS.read_text(encoding="utf-8"))
    want_bits = {int(b) for b in a.bits.split(",") if b}
    drop = {int(b) for b in a.exclude.split(",") if b}
    evs = [ev for ev in atlas["events"]
           if ev["bit"] not in drop
           and (ev["bit"] in want_bits
                or any(n.startswith(p) for p in a.rooms for n in ev["names"]))]
    order = [int(b) for b in a.order.split(",") if b]
    rank = {b: i for i, b in enumerate(order)}
    evs.sort(key=lambda ev: (rank.get(ev["bit"], len(order)), ev["bit"]))
    sys.stdout.write(f"# --- seeded: {a.section} ({len(evs)} events) ---\n\n")
    for ev in evs:
        sys.stdout.write(emit(ev, a.section) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
