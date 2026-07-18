"""Dump FF9's MOGNET mailbox out of a save file -- the observation probe for the 42nd-moogle work.

The mailbox lives in gEventGlobal (EventState.gEventGlobal, Byte[2048]) at these addresses, decoded
byte-by-byte from the real save-moogle template (fields 300 / 407 / 1102):

    Byte[1024]            init/migration guard -- must be 1 once the mailbox has ever been used.
                          If it is 0 AND any slot is occupied, the next real save moogle shows
                          "Old letter data. Erasing..." and ZEROES all 12 mailbox bytes.
    Byte[1032]            lifetime "letters delivered" counter (post-increment only; read by
                          Mognet Central for "Thanks for delivering [NUMB] letters!").
                          ** LIVE-VERIFIED 2026-07-18: ticked 12 -> 13 on delivering a letter. **
    Byte[1033]            Stiltzkin's 6-letter sub-quest tally.
    Byte[1034 + 4k]       slot k occupied (0 = empty)          k = 0,1,2
              +1          letter variant id
              +2          FROM moogle id   (index into the 41-name roster)
              +3          TO   moogle id
                          ** LIVE-VERIFIED: delivering slot 0's letter zeroed its whole quad. **
    Byte[1047-1054]       GIVE-side variant one-shot locks: bit set = that letter variant has
                          already been handed out somewhere. bit(v) = 8383 + 8*(v//8) - (v%8).
    Byte[1055-1062]       READ-side variant locks, same shape anchored at 8447: bit set = that
                          letter has been read. ** LIVE-VERIFIED: reading variants 19/22/33 set
                          exactly bits 8460/8457/8478 (bytes 1057 bit4, 1057 bit1, 1059 bit6). **
                          Together = the game's own 8376-8503 band inside the reserved 8376-8511
                          block (the kit's custom flags start at 8512 -- no collision either way).
    Byte[1064-1073]       the READ-MAIL menu payload, one entry per menu row: the row's letter
    Byte[1079-1088]       VARIANT id (1064+) and its SENDER moogle id (1079+, rendered through the
                          roster). Indexed by menu row, never by moogle id. ** LIVE-VERIFIED: after
                          a read-mail session these held [19,22,33] / [23,35,38] = the exact three
                          letters read (from Kuppo, Mogrika, Stiltzkin). **

Usage:
    py tools/mognet_dump.py                      # auto-find the Steam save, dump every populated slot
    py tools/mognet_dump.py <path-to-save>       # SavedData_ww.dat / Memoria extra .dat / save JSON
    py tools/mognet_dump.py <a> --json out.json  # also write a machine-readable snapshot to compare

Compare two snapshots (before/after talking to a moogle):
    py tools/mognet_dump.py save.dat --json before.json
    ... play ...
    py tools/mognet_dump.py save.dat --json after.json
    py tools/mognet_dump.py --compare before.json after.json

WRITE probes (close the game first; a timestamped backup of the extra file is always taken):
    py tools/mognet_dump.py --inject --into "slot 1 - save 3"      # a letter TO the 42nd moogle
        [--variant 55] [--from-id 1] [--to-id 41]                  #   (defaults: Kupo -> Mogwai)
    py tools/mognet_dump.py --fill --into "slot 1 - save 3"        # occupy ALL 3 slots with junk
                                                                   #   (the full-mailbox refusal probe)
Writes go to the slot's MEMORIA EXTRA file -- the plaintext sidecar the game treats as the
AUTHORITATIVE gEventGlobal on load (the encrypted main block is stale when it exists). A slot without
an extra file is refused: load + re-save it in-game once to create one.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ff9mapkit"))

GUARD, DELIVERED, STILTZKIN = 1024, 1032, 1033
SLOT0, NSLOTS, SLOTSZ = 1034, 3, 4
GIVE_LOCKS, READ_LOCKS = 1047, 1055          # 8 bytes each: variant one-shot locks (bit math below)
MENU_VARIANTS, MENU_SENDERS = range(1064, 1074), range(1079, 1089)


def _locked_variants(raw_1024_1090, base_byte: int) -> list:
    """Decode a lock table into the sorted list of locked variant ids. The engine's bit(v) formula is
    ``anchor + 8*(v//8) - (v%8)`` (anchor 8383 give / 8447 read), which inside byte ``base+k`` puts
    variant ``k*8 + (7 - bitpos)`` at bit position ``bitpos``. Inverse checked against live data:
    reading variants 19/22/33 set bytes 1057 bit4 / 1057 bit1 / 1059 bit6."""
    out = []
    for k in range(8):
        byte = raw_1024_1090[base_byte - 1024 + k]
        for p in range(8):
            if byte & (1 << p):
                out.append(k * 8 + (7 - p))
    return sorted(out)

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
    raw = b[1024:1091]
    return {
        "guard_1024": b[GUARD],
        "delivered_1032": b[DELIVERED],
        "stiltzkin_1033": b[STILTZKIN],
        "slots": slots,
        "give_locks": _locked_variants(raw, GIVE_LOCKS),   # variant ids already handed out
        "read_locks": _locked_variants(raw, READ_LOCKS),   # variant ids already read
        # legacy key names kept so old --json snapshots stay comparable; the MEANING is corrected:
        # 1064+ = the read-mail menu's variant per row, 1079+ = its sender moogle id per row.
        "option_codes_1064_1073": b[1064:1074],
        "option_nums_1079_1088": b[1079:1089],
        "raw_1024_1090": raw,
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
    out.append(f"  give-locks [1047-1054]   = variants {s.get('give_locks', '?')} already handed out")
    out.append(f"  read-locks [1055-1062]   = variants {s.get('read_locks', '?')} already read")
    rows = [(v, m) for v, m in zip(s["option_codes_1064_1073"], s["option_nums_1079_1088"]) if v or m]
    if rows:
        out.append("  last read-mail menu (variant <- sender), per row:")
        for v, m in rows:
            out.append(f"    variant {v:3}  from {moogle(m)}")
    else:
        out.append("  last read-mail menu: empty")
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
    for key, label in (("give_locks", "give-locks (variants handed out)"),
                       ("read_locks", "read-locks (variants read)"),
                       ("option_codes_1064_1073", "read-menu variants [1064-1073]"),
                       ("option_nums_1079_1088", "read-menu senders  [1079-1088]")):
        va, vb = a.get(key), b.get(key)                # .get: older --json snapshots lack the lock keys
        if va != vb and not (va is None or vb is None):
            same = False
            out.append(f"  {label}: {va} -> {vb}")
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


def inject_letter(blob: bytes, variant: int, from_id: int, to_id: int) -> bytes:
    """Pure transform: the letter into the FIRST EMPTY slot + the wipe-guard, mirroring the give
    write-set (occupied / FROM / TO / variant + Byte[1024]=1; the give-lock belongs to the SENDER's
    field and is deliberately not touched). Raises if the mailbox is full."""
    G = bytearray(blob)
    for k in range(NSLOTS):
        base = SLOT0 + k * SLOTSZ
        if G[base] == 0:
            G[base], G[base + 1], G[base + 2], G[base + 3] = 1, variant, from_id, to_id
            G[GUARD] = 1
            return bytes(G)
    raise SystemExit("mailbox full (3/3) -- deliver or --fill was already run; nothing injected")


def fill_mailbox(blob: bytes) -> bytes:
    """Pure transform: occupy ALL three slots with recognizable junk (variants 60/61/62) -- the
    full-mailbox refusal probe (test B). The guard is set so no real moogle erases it as old data."""
    G = bytearray(blob)
    for k in range(NSLOTS):
        base = SLOT0 + k * SLOTSZ
        G[base], G[base + 1], G[base + 2], G[base + 3] = 1, 60 + k, 2 * k + 2, 2 * k + 3
    G[GUARD] = 1
    return bytes(G)


def _write_probe(path, into_label: str, transform) -> int:
    """Locate the slot by its dump label, back up its Memoria extra file, transform, write, show."""
    import shutil
    import time
    from ff9mapkit import save as _save
    p = _resolve_save(path) if path else _resolve_save(_save.default_save_dir() or "")
    sv = _save.FF9Save.load(p)
    want = into_label.lower().replace(" - memoria extra", "").strip()
    for s in sv.populated():
        if _save._slot_label(s).replace("·", "-").lower().strip() != want:
            continue
        extra = _save.extra_file_path(p, s.block)
        blob = _save.read_extra_gEventGlobal(extra) if (extra and os.path.exists(extra)) else None
        if blob is None:
            print(f"'{into_label}' has NO Memoria extra file -- the game would ignore a main-block "
                  f"write. Load + re-save that slot in-game once, then retry.", file=sys.stderr)
            return 2
        bak = f"{extra}.mogbak.{time.strftime('%Y%m%d-%H%M%S')}"
        shutil.copyfile(extra, bak)
        new = transform(blob)
        if not _save.patch_extra_gEventGlobal(extra, new):
            print("extra file lost its gEventGlobal field?! nothing written", file=sys.stderr)
            return 2
        print(f"backup: {bak}\n  (restore: copy it back over {os.path.basename(extra)})\n")
        print(render("BEFORE", snapshot(blob)))
        print()
        print(render("AFTER", snapshot(new)))
        return 0
    labels = [_save._slot_label(s).replace("·", "-") for s in sv.populated()]
    print(f"no populated slot matches {into_label!r}. Slots: {labels}", file=sys.stderr)
    return 2


def main() -> int:
    ap = argparse.ArgumentParser(description="dump FF9's Mognet mailbox from a save")
    ap.add_argument("save", nargs="?", help="save path (default: auto-find the Steam save)")
    ap.add_argument("--json", help="write the snapshot(s) here for a later --compare")
    ap.add_argument("--compare", nargs=2, metavar=("BEFORE", "AFTER"), help="diff two --json snapshots")
    ap.add_argument("--inject", action="store_true", help="write a letter TO the 42nd moogle into --into")
    ap.add_argument("--fill", action="store_true", help="occupy all 3 slots with junk (refusal probe)")
    ap.add_argument("--into", metavar="LABEL", help='the dump label to write, e.g. "slot 1 - save 3"')
    ap.add_argument("--variant", type=int, default=55, help="letter variant for --inject (default 55)")
    ap.add_argument("--from-id", type=int, default=1, help="sender moogle id (default 1 = Kupo)")
    ap.add_argument("--to-id", type=int, default=41, help="recipient id (default 41 = the 42nd moogle)")
    a = ap.parse_args()

    if a.inject or a.fill:
        if a.inject and a.fill:
            print("--inject and --fill are mutually exclusive", file=sys.stderr)
            return 2
        if not a.into:
            print("--into LABEL is required for a write (run a plain dump to see the labels)",
                  file=sys.stderr)
            return 2
        for name, v in (("variant", a.variant), ("from-id", a.from_id), ("to-id", a.to_id)):
            if not 0 <= v <= (63 if name == "variant" else 255):
                print(f"--{name} {v} out of range", file=sys.stderr)
                return 2
        tf = (lambda b: inject_letter(b, a.variant, a.from_id, a.to_id)) if a.inject else fill_mailbox
        return _write_probe(a.save, a.into, tf)

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
