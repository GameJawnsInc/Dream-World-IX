#!/usr/bin/env python3
"""LADDER (faithful climb experiment): replace the kit's teleport climb with the REAL Treno climb.

Copies the real entry-15 ladder's climb function (real Treno entry 19, tag 17 -- the actual SetupJump/
Jump arc sequence with jump animations + AddCharacterAttribute) VERBATIM into our player entry's tag 17,
NOP-ing only the RunSharedScript(2/3) polish (camera/sound helpers, to avoid a shared-script dependency
our fork doesn't have). Our player model == the real Treno player (SetModel 98,93), so the jump anims
transfer; and we BG-borrow Treno's real coords, so the climb's position-branching works as-is.

The ladder region (kit-built, RunScriptSync(2,250,17)) is unchanged -- it now runs the REAL climb.
The climb lands at the REAL ladder top (not the floor-1 teleport), so the exit may need re-placing.

Reversible (backs up EVT_TRENO_RES per lang). F6 in Treno to reload. Run: py tools/ladder_faithful.py
"""
import datetime
import os
import shutil
import struct
import sys
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit import extract                                  # noqa: E402
from ff9mapkit.binutils import set_u16, u16                    # noqa: E402
from ff9mapkit.config import LANGS, ModLayout, find_game_path  # noqa: E402
from ff9mapkit.eb import EbScript                              # noqa: E402
from ff9mapkit.eb.disasm import iter_code                      # noqa: E402
from ff9mapkit.content import ladder as _ladder                # noqa: E402

REPO = Path(__file__).resolve().parent.parent
CLIMB_TAG = 17


def real_climb_bytes():
    """The real Treno entry-15 ladder climb (entry 19 tag 17), with RunSharedScript (0x43) NOPed."""
    real = EbScript.from_bytes(extract.extract_event_script("trno_map401_tr_res"))
    f = real.entry(19).func_by_tag(CLIMB_TAG)
    body = bytearray(real.data[f.abs_start:f.abs_end])
    nopped = 0
    for ins in iter_code(real.data, f.abs_start, f.abs_end):
        if ins.op == 0x43:                       # RunSharedScript(N) -> NOP its 3 bytes (op,argflag,N)
            rel = ins.off - f.abs_start
            body[rel:rel + ins.length] = b"\x00" * ins.length
            nopped += 1
    return bytes(body), nopped, len(body)


def replace_function(data, entry_index, tag, new_body):
    """Replace the body of an existing function (tag) in an entry; re-layout + relocate later entries."""
    eb = EbScript.from_bytes(data)
    e = eb.entry(entry_index)
    funcs = [(f.tag, (new_body if f.tag == tag else data[f.abs_start:f.abs_end])) for f in e.funcs]
    table = b""
    pos = len(funcs) * 4
    for t, b in funcs:
        table += struct.pack("<HH", t, pos)
        pos += len(b)
    new_entry = bytes([e.type, len(funcs)]) + table + b"".join(b for _, b in funcs)
    slot = 128 + entry_index * 8
    off, sz = u16(data, slot), u16(data, slot + 2)
    es = 128 + off
    out = bytearray(bytes(data[:es]) + new_entry + bytes(data[es + sz:]))
    set_u16(out, slot + 2, len(new_entry))
    growth = len(new_entry) - sz
    for i in range(data[3]):
        if i == entry_index:
            continue
        s2 = 128 + i * 8
        if u16(out, s2 + 2) > 0 and u16(out, s2) > off:
            set_u16(out, s2, u16(out, s2) + growth)
    return bytes(out)


def main():
    climb, nopped, n = real_climb_bytes()
    print(f"real climb: {n} bytes, {nopped} RunSharedScript NOPed")
    live = ModLayout(find_game_path() / "FF9CustomMap")
    bk = REPO / "backups"
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    for L in LANGS:
        p = live.eb_path(L, "EVT_TRENO_RES.eb.bytes")
        data = p.read_bytes()
        shutil.copyfile(p, bk / f"{L}-EVT_TRENO_RES.eb.bytes.prefaithful.{stamp}")
        pe = _ladder.find_player_entry(EbScript.from_bytes(data))
        data = replace_function(data, pe, CLIMB_TAG, climb)
        p.write_bytes(data)
        print(f"  {L}: player tag17 -> real climb ({len(data)} bytes)")
    rev = REPO / "tools" / "scroll_out" / "revert_ladder_faithful.py"
    rev.parent.mkdir(parents=True, exist_ok=True)
    rev.write_text(
        '"""Revert the faithful-climb experiment on EVT_TRENO_RES."""\nimport shutil\nfrom pathlib import Path\n'
        f"live = Path(r{str(find_game_path() / 'FF9CustomMap')!r})\nbk = Path(r{str(bk)!r}); stamp={stamp!r}\n"
        "base='StreamingAssets/assets/resources/commonasset/eventengine/eventbinary/field'\n"
        f"for L in {LANGS!r}:\n"
        "    shutil.copyfile(bk/f'{L}-EVT_TRENO_RES.eb.bytes.prefaithful.{stamp}', live/base/L/'EVT_TRENO_RES.eb.bytes')\n"
        "print('reverted faithful climb')\n", encoding="utf-8", newline="\n")
    print("\nTEST: F6 in Treno. Walk to the ladder base -> \"!\" -> press action -> you should CLIMB "
          "(real jump animation + arc) up the ladder, not teleport.")
    print(f"revert: py {rev.relative_to(REPO).as_posix()}")


if __name__ == "__main__":
    main()
