"""Dump FF9's MOGNET mailbox out of a save file -- the observation probe for the 42nd-moogle work.

The mailbox lives in gEventGlobal (EventState.gEventGlobal, Byte[2048]) at these addresses, decoded
byte-by-byte from the real save-moogle template (fields 300 / 407 / 1102):

    Byte[1024]            init/migration guard -- must be 1 once the mailbox has ever been used.
                          If it is 0 AND any slot is occupied, the next real save moogle shows
                          "Old letter data. Erasing..." and ZEROES all 12 mailbox bytes.
    Byte[1032]            lifetime "letters delivered" counter (post-increment only; read by
                          Mognet Central for "Thanks for delivering N letters!").
    Byte[1033]            Stiltzkin's 6-letter sub-quest tally.
    Byte[1034 + 4k]       slot k occupied (0 = empty)          k = 0,1,2
              +1          letter variant id
              +2          FROM moogle id   (index into the 41-name roster)
              +3          TO   moogle id
    Byte[1064-1073]       dialog-menu OPTION CODE table (indexed by the player's choice, NOT by
    Byte[1079-1088]       moogle id) + its paired display-number twin. Dumped for completeness.

Usage:
    py tools/mognet_dump.py                      # auto-find the Steam save, dump every populated slot
    py tools/mognet_dump.py <path-to-save>       # SavedData_ww.dat / Memoria extra .dat / save JSON
    py tools/mognet_dump.py <a> --json out.json  # also write a machine-readable snapshot to compare

Compare two snapshots (before/after talking to a moogle):
    py tools/mognet_dump.py save.dat --json before.json
    ... play ...
    py tools/mognet_dump.py save.dat --json after.json
    py tools/mognet_dump.py --compare before.json after.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ff9mapkit"))

GUARD, DELIVERED, STILTZKIN = 1024, 1032, 1033
SLOT0, NSLOTS, SLOTSZ = 1034, 3, 4
OPTION_CODES, OPTION_NUMS = range(1064, 1074), range(1079, 1089)

# The 41-name roster, read from text entry 0 of a real field's text block. Index = moogle id.
ROSTER = ["Ruby", "Kupo", "Mosh", "Mosco", "Monty", "Mogpi", "Mois", "Gumo", "Kumop", "Moodon",
          "Mogki", "Moonte", "Mogmi", "Atla", "Grimo", "Nazna", "Mogrich", "Mochos", "Monev", "Mopli",
          "Serino", "Mogrody", "Mozme", "Kuppo", "Mogryo", "Mogmatt", "Suzuna", "Mocchi", "Mojito",
          "Mogsam", "Mimoza", "Mooel", "Moolan", "Mogtaka", "Kumool", "Mogrika", "Moorock", "Noggy",
          "Stiltzkin", "Artemicion", "Mogribs"]


def moogle(i: int) -> str:
    if 0 <= i < len(ROSTER):
        return f"{ROSTER[i]} ({i})"
    return f"<UNKNOWN id {i}>" + (" <- OUR 42nd moogle" if i == len(ROSTER) else "")


def snapshot(blob: bytes) -> dict:
    b = list(blob)
    slots = []
    for k in range(NSLOTS):
        base = SLOT0 + k * SLOTSZ
        slots.append({"slot": k, "occupied": b[base], "variant": b[base + 1],
                      "from": b[base + 2], "to": b[base + 3]})
    return {
        "guard_1024": b[GUARD],
        "delivered_1032": b[DELIVERED],
        "stiltzkin_1033": b[STILTZKIN],
        "slots": slots,
        "option_codes_1064_1073": b[1064:1074],
        "option_nums_1079_1088": b[1079:1089],
        "raw_1024_1090": b[1024:1091],
    }


def render(label: str, s: dict) -> str:
    out = [f"=== {label} ==="]
    g = s["guard_1024"]
    occupied = [x for x in s["slots"] if x["occupied"]]
    warn = ""
    if g != 1 and occupied:
        warn = "   *** WIPE PENDING: guard==0 with letters present -> the next real save moogle ERASES them ***"
    out.append(f"  guard Byte[1024]      = {g}{warn}")
    out.append(f"  delivered Byte[1032]  = {s['delivered_1032']}   (lifetime letters delivered)")
    out.append(f"  stiltzkin Byte[1033]  = {s['stiltzkin_1033']}   (of 6)")
    out.append(f"  mailbox ({len(occupied)}/3 slots occupied):")
    for x in s["slots"]:
        base = SLOT0 + x["slot"] * SLOTSZ
        if not x["occupied"]:
            out.append(f"    slot {x['slot']} @{base}: empty")
        else:
            out.append(f"    slot {x['slot']} @{base}: variant {x['variant']:3}  "
                       f"FROM {moogle(x['from'])}  ->  TO {moogle(x['to'])}")
    out.append(f"  option codes [1064-1073] = {s['option_codes_1064_1073']}")
    out.append(f"  option nums  [1079-1088] = {s['option_nums_1079_1088']}")
    return "\n".join(out)


def compare(a: dict, b: dict) -> str:
    out = ["=== COMPARE (before -> after) ==="]
    same = True
    for key in ("guard_1024", "delivered_1032", "stiltzkin_1033"):
        if a[key] != b[key]:
            same = False
            out.append(f"  {key}: {a[key]} -> {b[key]}")
    for i, (x, y) in enumerate(zip(a["slots"], b["slots"])):
        if x != y:
            same = False
            out.append(f"  slot {i}: occ {x['occupied']}->{y['occupied']}  var {x['variant']}->{y['variant']}"
                       f"  from {x['from']}->{y['from']}  to {x['to']}->{y['to']}")
    for key in ("option_codes_1064_1073", "option_nums_1079_1088"):
        if a[key] != b[key]:
            same = False
            out.append(f"  {key}: {a[key]} -> {b[key]}")
    ra, rb = a["raw_1024_1090"], b["raw_1024_1090"]
    changed = [1024 + i for i, (x, y) in enumerate(zip(ra, rb)) if x != y]
    if changed:
        out.append(f"  raw bytes changed: {changed}")
    if same and not changed:
        out.append("  NO CHANGE -- the mailbox is byte-identical.")
    return "\n".join(out)


SAVE_NAME = "SavedData_ww.dat"


def _resolve_save(path) -> str:
    """Accept a DIRECTORY (the EncryptedSavedData folder) as well as a file, and fail with a readable
    message rather than letting a non-save fall through to the Base64 branch and die inside b64decode."""
    p = str(path)
    if os.path.isdir(p):
        cand = os.path.join(p, SAVE_NAME)
        if os.path.exists(cand):
            return cand
        dats = sorted(f for f in os.listdir(p) if f.lower().endswith(".dat"))
        if not dats:
            raise SystemExit(f"no .dat save found in directory: {p}")
        return os.path.join(p, dats[0])
    if not os.path.exists(p):
        raise SystemExit(f"no such file: {p}")
    return p


def _raw_blobs(path) -> "list[tuple[str, bytes]]":
    """``[(label, gEventGlobal_bytes)]`` -- the RAW blob per populated slot. Mirrors ``save.inspect``'s
    source resolution, but returns the bytes (``SaveReport`` carries only the decoded story flags, and we
    need arbitrary byte addresses in the mailbox range). Honours Memoria's per-slot extra file, which is
    the AUTHORITATIVE gEventGlobal when present -- the main block is stale in that case."""
    from ff9mapkit import save as _save
    from ff9mapkit import flags as _flags
    p = _resolve_save(path)
    if p.lower().endswith(".dat"):
        blob = _save.read_extra_gEventGlobal(p)
        if blob is not None:
            return [("Memoria extra-save", blob)]
        sv = _save.FF9Save.load(p)
        out = []
        for s in sv.populated():
            extra = _save.extra_file_path(p, s.block)
            eblob = _save.read_extra_gEventGlobal(extra) if (extra and os.path.exists(extra)) else None
            # sanitise: save._slot_label uses a middle dot, which mojibakes on a cp1252 console
            lbl = _save._slot_label(s).replace("·", "-")
            out.append((lbl + (" - Memoria extra" if eblob is not None else ""),
                        eblob if eblob is not None else sv.gEventGlobal(s.block)))
        if not out:
            raise ValueError("no populated save slots found in this file")
        return out
    return [("gEventGlobal", _flags.gEventGlobal_from_save(p))]


def main() -> int:
    ap = argparse.ArgumentParser(description="dump FF9's Mognet mailbox from a save")
    ap.add_argument("save", nargs="?", help="save path (default: auto-find the Steam save)")
    ap.add_argument("--json", help="write the snapshot(s) here for a later --compare")
    ap.add_argument("--compare", nargs=2, metavar=("BEFORE", "AFTER"), help="diff two --json snapshots")
    a = ap.parse_args()

    if a.compare:
        before, after = (json.load(open(p, encoding="utf8")) for p in a.compare)
        bl = before["snapshots"] if "snapshots" in before else {"": before}
        al = after["snapshots"] if "snapshots" in after else {"": after}
        for k in bl:
            if k in al:
                print(compare(bl[k], al[k]))
        return 0

    from ff9mapkit import save as _save
    path = a.save
    if not path:
        d = _save.default_save_dir()
        if not d:
            print("could not auto-find the FF9 save folder; pass the path explicitly", file=sys.stderr)
            return 2
        path = _resolve_save(d)
        print(f"(auto) {path}\n")

    snaps = {}
    for label, blob in _raw_blobs(path):
        s = snapshot(blob)
        snaps[label] = s
        print(render(label, s))
        print()
    if a.json:
        with open(a.json, "w", encoding="utf8") as fh:
            json.dump({"source": path, "snapshots": snaps}, fh, indent=1)
        print(f"wrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
