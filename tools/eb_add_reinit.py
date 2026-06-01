#!/usr/bin/env python3
# Add an after-battle handler (entry 0, function tag 10 = "Main_Reinit") to a field .eb.
#
# WHY: After a random battle, EventEngine restores the field context, then does
# Request(entry0, 0, 10) (EventEngine.cs:627). EnterBattleEnd() (1188) has suspended every object
# (obj.uid != 0 -> state=stateSuspend). When the tag-10 handler RETURNS at level 0, the Return
# handler calls ExitBattleEnd() (EventEngine.cs:1188-1189 -> 1167) which un-suspends them
# (obj.state = obj.state0). Battle fields ship a Main_Reinit (tag 10) for this; fields cloned from a
# CUTSCENE field (e.g. 1357) have none, so the player stays suspended -> frozen after battle.
# Minimal handler: EnableMove(0x2E) ; return(0x04)  -> re-enables control AND triggers the resume.
#
# RE-LAYOUT (no assembler needed; code blocks are copied verbatim, jumps are relative / tag-based):
#   entry0 func table grows +4 (new [tag2,fpos2]); existing funcs' fpos += 4 (code shifts past the
#   bigger table); the new func is appended after entry0's code; every later entry with sz>0 shifts
#   in the file, so its entry-table off += growth. entryCount (header byte 3) is unchanged.
import struct, sys, os

def u16(b, o): return struct.unpack_from('<H', b, o)[0]

NEWFUNC = bytes([0x2E, 0x04])   # EnableMove ; return

def add_reinit(data, tag=10, newfunc=NEWFUNC):
    b = bytearray(data)
    off0, sz0 = u16(b, 128), u16(b, 130)
    es = 128 + off0
    etype, fc = b[es], b[es+1]
    fbase = es + 2
    funcs = [[u16(b, fbase+i*4), u16(b, fbase+i*4+2)] for i in range(fc)]
    if any(t == tag for t, _ in funcs):
        raise SystemExit(f"entry0 already has function tag {tag}")
    code = bytes(b[fbase + fc*4 : es + sz0])
    new_funcs = [[t, fp+4] for t, fp in funcs] + [[tag, (fc+1)*4 + len(code)]]
    newentry = bytes([etype, fc+1])
    for t, fp in new_funcs:
        newentry += struct.pack('<HH', t, fp)
    newentry += code + newfunc
    growth = len(newentry) - sz0
    out = bytearray(bytes(b[:es]) + newentry + bytes(b[es+sz0:]))
    struct.pack_into('<H', out, 130, len(newentry))            # entry0 size
    for i in range(1, 10):                                      # relocate later entries
        slot = 128 + i*8
        if u16(out, slot+2) > 0:
            struct.pack_into('<H', out, slot, u16(out, slot) + growth)
    return bytes(out)

if __name__ == "__main__":
    LANGS = ["us", "uk", "fr", "gr", "it", "es", "jp"]
    base = os.path.dirname(os.path.abspath(__file__))
    MOD  = base + "/../mod/hut/eb/{}-EVT_HUT_EXT.eb.bytes"
    GAME = ("C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX/FF9CustomMap/StreamingAssets/"
            "assets/resources/commonasset/eventengine/eventbinary/field/{}/EVT_HUT_EXT.eb.bytes")
    for L in LANGS:
        out = add_reinit(open(GAME.format(L), 'rb').read())
        open(GAME.format(L), 'wb').write(out)
        open(MOD.format(L), 'wb').write(out)
        print(f"{L}: EVT_HUT_EXT +after-battle handler -> {len(out)} bytes")
    print("deployed to game + mod/hut/eb")
