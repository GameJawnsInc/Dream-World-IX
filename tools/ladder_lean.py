#!/usr/bin/env python3
"""LADDER LEAN (faithful) -- reproduce the real game's forward lean on the Treno ladder.

The real climb (entry 19 tag 17) launches two CONCURRENT sequences via RunSharedScript/STARTSEQ (0x43):
  - entry 2 ramps SetPitchAngle (ROTXZ, 0x37) 0 -> 16  (leans Zidane onto the rungs as the climb starts)
  - entry 3 ramps it 16 -> 0                            (straightens him at the top)
STARTSEQ runs "entry N of THIS field" as a per-frame Seq on the climber -- so entries 2/3 are the real
field's own helper entries, NOT global. Our import NOPed the STARTSEQ calls AND the fork never had
entries 2/3, so Zidane climbs bolt-upright.

Fix (faithful, clean byte-wise): graft entries 2/3 into the fork at free slots + restore the STARTSEQ
calls un-NOPed, remapping their entry-arg to the new slots (a same-length 1-byte patch -- no shift), and
overwrite the player's tag-17 climb with the un-NOPed remapped version (same length, no relayout).

Patches the live EVT_TRENO_RES (7 langs -- bytecode is lang-identical). Reversible. F6 in Treno to test.
Run: py tools/ladder_lean.py
"""
import datetime
import os
import shutil
import sys
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit import extract                                    # noqa: E402
from ff9mapkit.binutils import u16                               # noqa: E402
from ff9mapkit.config import LANGS, ModLayout, find_game_path    # noqa: E402
from ff9mapkit.eb import EbScript, edit                          # noqa: E402
from ff9mapkit.eb.disasm import iter_code                        # noqa: E402
from ff9mapkit.content.ladder import find_player_entry           # noqa: E402

REPO = Path(__file__).resolve().parent.parent
CLIMB_TAG = 17
STARTSEQ = 0x43            # RunSharedScript -- runs "entry arg0 of this field" as a concurrent Seq


def _entry_bytes(data, ei):
    slot = 128 + ei * 8
    off, sz = u16(data, slot), u16(data, slot + 2)
    return data[128 + off:128 + off + sz]


def harvest():
    """From the real residence: the un-NOPed climb, its STARTSEQ (rel_off, entry) refs, and the
    referenced sequence entries' raw bytes (the SetPitchAngle ramps)."""
    real = EbScript.from_bytes(extract.extract_event_script("trno_map401_tr_res"))
    f = real.entry(19).func_by_tag(CLIMB_TAG)
    climb = real.data[f.abs_start:f.abs_end]
    refs = [(ins.off - f.abs_start, ins.args[0])
            for ins in iter_code(real.data, f.abs_start, f.abs_end) if ins.op == STARTSEQ]
    seqs = {ei: _entry_bytes(real.data, ei) for _, ei in refs}
    return climb, refs, seqs


def graft(data, climb, refs, seqs):
    ei2slot = {}
    for ei in sorted(seqs):                                       # append each pitch-ramp entry
        slot = EbScript.from_bytes(data).first_free_slot()
        data = edit.append_entry(data, slot, seqs[ei])
        ei2slot[ei] = slot
    climb = bytearray(climb)                                      # remap STARTSEQ entry-arg -> new slots
    for rel, ei in refs:
        assert climb[rel] == STARTSEQ, hex(climb[rel])
        climb[rel + 2] = ei2slot[ei]
    eb = EbScript.from_bytes(data)                                # overwrite tag-17 climb in place
    f = eb.entry(find_player_entry(eb)).func_by_tag(CLIMB_TAG)
    assert f.abs_end - f.abs_start == len(climb), (f.abs_end - f.abs_start, len(climb))
    data = bytearray(data)
    data[f.abs_start:f.abs_end] = climb
    return bytes(data), ei2slot


def main():
    climb, refs, seqs = harvest()
    print(f"climb {len(climb)}B; STARTSEQ refs {refs}; seq entries {[(ei, len(b)) for ei, b in seqs.items()]}")
    live = ModLayout(find_game_path() / "FF9CustomMap")
    bk = REPO / "backups"
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    for L in LANGS:
        p = live.eb_path(L, "EVT_TRENO_RES.eb.bytes")
        data = p.read_bytes()
        shutil.copyfile(p, bk / f"{L}-EVT_TRENO_RES.eb.bytes.prelean.{stamp}")
        out, ei2slot = graft(data, climb, refs, seqs)
        p.write_bytes(out)
        print(f"  {L}: leaned (seq entries -> slots {ei2slot}) -> {len(out)}B")
    rev = REPO / "tools" / "scroll_out" / "revert_ladder_lean.py"
    rev.parent.mkdir(parents=True, exist_ok=True)
    rev.write_text(
        '"""Revert the ladder-lean experiment on EVT_TRENO_RES."""\nimport shutil\nfrom pathlib import Path\n'
        f"live = Path(r{str(find_game_path() / 'FF9CustomMap')!r})\nbk = Path(r{str(bk)!r}); stamp={stamp!r}\n"
        "base='StreamingAssets/assets/resources/commonasset/eventengine/eventbinary/field'\n"
        f"for L in {LANGS!r}:\n"
        "    shutil.copyfile(bk/f'{L}-EVT_TRENO_RES.eb.bytes.prelean.{stamp}', live/base/L/'EVT_TRENO_RES.eb.bytes')\n"
        "print('reverted ladder lean')\n", encoding="utf-8", newline="\n")
    print("\nTEST: F6 in Treno; climb the ladder -> Zidane should now LEAN forward onto the rungs "
          "(0->16 pitch on the way up, 16->0 at the top).")
    print(f"revert: py {rev.relative_to(REPO).as_posix()}")


if __name__ == "__main__":
    main()
