"""``[start_inventory]`` -- author the NEW-GAME starting bag (the items the player begins a New Game with).

Writes ``<mod>/StreamingAssets/Data/Items/InitialItems.csv``. ★ The engine reads this
**HIGHEST-PRIORITY-WINS** (NOT merged -- ``ff9item.LoadInitialItems`` via ``GetCsvWithHighestPriority``), so
this file **REPLACES the base starting bag entirely**: list the COMPLETE intended inventory. A stacked mod
folder that also defines ``InitialItems.csv`` SHADOWS this one (the ``text_block`` trap) -> the build lints.

Read ONCE at new-game init, so it only affects a true **New Game** (not an F6 / campaign mid-game entry).
It is mod-global (one bag per mod) and lives on the ENTRY field's ``field.toml`` -- emitted at the mod-write
stage, not into any field's ``.eb``. (memory project-ff9-items-equipment / project-ff9-branch-lanes.)

    [start_inventory]
    items = [["Potion", 20], ["Phoenix Down", 5], ["Tent", 3], ["Ether", 10]]
"""
from __future__ import annotations

from .. import items as _items

NO_ITEM = 255          # the empty sentinel -- never a real starting item
MAX_COUNT = 99         # the per-item inventory cap (UInt8 column; the engine clamps, we clamp too)


def inventory_rows(items) -> list:
    """``[[name, count], ...]`` (or bare names) -> sorted ``[(item_id, count), ...]`` -- names resolved,
    dup ids summed, counts clamped 1..99, NoItem dropped. Raises ValueError (via :func:`items.resolve`) on an
    unknown name."""
    by_id: dict = {}
    for entry in items:
        if isinstance(entry, (list, tuple)):
            name = entry[0]
            count = int(entry[1]) if len(entry) > 1 else 1
        else:
            name, count = entry, 1
        iid = _items.resolve(name)
        if iid == NO_ITEM:
            continue
        by_id[iid] = min(MAX_COUNT, by_id.get(iid, 0) + max(1, count))
    return sorted(by_id.items())


def render_initial_items(items) -> str:
    """The FULL ``InitialItems.csv`` text (header + ``id;count;# name`` rows). Replaces the base bag entirely
    (highest-priority-wins), so this is the complete starting inventory."""
    lines = [
        "# ff9mapkit [start_inventory] -- the FULL new-game starting bag (REPLACES the base; highest-priority-wins).",
        "# ItemID;Count",
        "# Int32;UInt8",
    ]
    for iid, count in inventory_rows(items):
        nm = _items.name_of(iid)
        lines.append(f"{iid};{count};" + (f"# {nm}" if nm else ""))
    return "\n".join(lines) + "\n"


def write_initial_items(layout, items) -> None:
    """Pure writer: emit the starting-bag CSV into ``layout``'s mod root (``Data/Items/InitialItems.csv``)."""
    path = layout.initial_items_csv
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_initial_items(items), encoding="utf-8", newline="\n")
