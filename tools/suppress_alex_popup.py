#!/usr/bin/env python3
# Suppress field 100's two leftover DEBUG popups ("Error Env Play() Slot=0/1") that fire on
# re-entry from our custom room. They are SetTextVariable(2,n) -> WindowAsync(6,0,68) ->
# RaiseWindows -> WaitWindow(6), where text 68 is a dev debug string, gated behind an
# env-audio-failure check (false in retail, true out-of-context). NOP the WindowAsync+
# RaiseWindows+WaitWindow in each block (keep SetTextVariable; same byte count so no shift,
# no jump/entry-table relocation). Edits our FF9CustomMap field-100 override (post-gateway).
import os, sys
from datetime import datetime

# 10-byte ranges to NOP (WindowAsync 6 + RaiseWindows 1 + WaitWindow 3), per block.
# Two pairs: func0/tag-0 (on entry) at 954/988, and func2/tag-10 (after-battle) at 1521/1555.
BLOCKS = [(954, 964), (988, 998), (1521, 1531), (1555, 1565)]
WA = bytes([0x20,0x00,0x06,0x00,0x44,0x00]); RAISE = bytes([0x8E]); WAIT = bytes([0x54,0x00,0x06])

def patch(data):
    b = bytearray(data)
    for (a, z) in BLOCKS:
        cur = bytes(b[a:z])
        if cur == bytes(z - a):
            continue  # already NOPed (idempotent)
        assert cur == WA + RAISE + WAIT, f"unexpected bytes at [{a}..{z}): {cur.hex()}"
        for i in range(a, z):
            b[i] = 0x00  # NOTHING
    return bytes(b)

LANGS = ["us","uk","fr","gr","it","es","jp"]
GAME = "C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"
CM   = GAME + "/FF9CustomMap/StreamingAssets/assets/resources/commonasset/eventengine/eventbinary/field/{lang}/evt_alex1_at_street_a.eb.bytes"
HERE = os.path.dirname(os.path.abspath(__file__))
BKP  = HERE + "/../backups"; MODA = HERE + "/../mod/alex/eb"

if __name__ == "__main__":
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    for L in LANGS:
        p = CM.format(lang=L); src = open(p,'rb').read()
        open(f"{BKP}/{L}-evt_alex1_at_street_a.eb.bytes.prepopupfix.{stamp}",'wb').write(src)
        out = patch(src)
        open(p,'wb').write(out); open(f"{MODA}/{L}-evt_alex1_at_street_a.eb.bytes",'wb').write(out)
        print(f"{L}: NOPed 2 debug-window blocks ({len(src)} bytes, unchanged size)")
    print("done (7 langs -> game + mod/alex/eb). backups: backups/*.prepopupfix.*")
