#!/usr/bin/env python3
# Add field BGM (Vivi's Theme) to custom field 4000 (EVT_HUT_EXT).
#
# Field music is played by the FLDSND0 opcode RunSoundCode(soundCode, soundID):
#   soundCode 0 = ff9fldsnd_song_play (FF9Snd.cs:1434).  song id 9 = "Vivi's Theme (Disc 1)" (=music008)
#   verified by real fields 100/103 ("RunSoundCode( 0, 9 ) // Play Music ; Vivi's Theme").
# Encoding: FLDSND0 = 0xC5, two getv2 args, argflag 0 (both immediate):
#   RunSoundCode(0, 9) = C5 00  00 00  09 00   (opcode, argflag, soundCode:2LE, soundID:2LE)
#
# Two insertion points, both into JUMP-FREE linear code (no jump relocation needed):
#   1) the appended encounter init-entry (last entry, code starts with SetRandomBattles 0x3C) — runs
#      once on field load via InitCode in Main_Init -> plays the theme on room ENTRY.
#   2) entry-0 tag-10 "Main_Reinit" (currently FadeFilter 0xEC; EnableMove; return) — runs after
#      BATTLE -> replays the theme so it's not silent on battle-return.
# Re-layout per insertion: grow the containing entry's size, shift later entries' table offsets
# (internal fpos are relative so they're unchanged). Verified with eb_disasm.
import struct, os, sys

def u16(b, o): return struct.unpack_from('<H', b, o)[0]

RUNSOUND_VIVI = bytes([0xC5, 0x00, 0x00, 0x00, 0x09, 0x00])  # RunSoundCode(0, 9) = play Vivi's Theme

def insert_bytes(data, abs_off, ins):
    b = bytearray(data)
    E = Eoff = None
    for i in range(10):
        off, sz = u16(b, 128+i*8), u16(b, 128+i*8+2)
        if off > 0 and 128+off <= abs_off < 128+off+sz:
            E, Eoff, Esz = i, off, sz; break
    if E is None:
        raise SystemExit(f"no entry contains file offset {abs_off}")
    struct.pack_into('<H', b, 128+E*8+2, Esz + len(ins))            # grow containing entry
    for j in range(10):                                            # shift entries after it
        if j == E: continue
        off = u16(b, 128+j*8)
        if off > 0 and off > Eoff:
            struct.pack_into('<H', b, 128+j*8, off + len(ins))
    return bytes(b[:abs_off]) + ins + bytes(b[abs_off:])

def tag10_body_start(data):
    off0 = u16(data, 128); es = 128 + off0; fc = data[es+1]; fbase = es + 2
    for i in range(fc):
        if u16(data, fbase+i*4) == 10:
            return fbase + u16(data, fbase+i*4+2)
    raise SystemExit("entry0 has no tag-10")

def last_entry_code_start(data):
    best = -1; best_off = -1
    for i in range(10):
        off = u16(data, 128+i*8)
        if off > best_off:
            best, best_off = i, off
    es = 128 + best_off; fc = data[es+1]
    return es + 2 + fc*4   # code begins right after the func table

def add_music(data):
    # 1) after-battle: insert at tag-10 body start (before the FadeFilter)
    t10 = tag10_body_start(data)
    if data[t10] != 0xEC:
        raise SystemExit(f"tag-10 body doesn't start with FadeFilter(0xEC): {data[t10]:#x} (run eb_reinit_add_fade first)")
    data = insert_bytes(data, t10, RUNSOUND_VIVI)
    # 2) on-entry: insert at the last entry's code start (before SetRandomBattles)
    ce = last_entry_code_start(data)
    if data[ce] != 0x3C:
        raise SystemExit(f"last entry code doesn't start with SetRandomBattles(0x3C): {data[ce]:#x}")
    data = insert_bytes(data, ce, RUNSOUND_VIVI)
    return data

if __name__ == "__main__":
    from datetime import datetime
    LANGS = ["us", "uk", "fr", "gr", "it", "es", "jp"]
    HERE = os.path.dirname(os.path.abspath(__file__))
    MOD  = HERE + "/../mod/hut/eb/{}-EVT_HUT_EXT.eb.bytes"
    BKP  = HERE + "/../backups"
    GAME = ("C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX/FF9CustomMap/StreamingAssets/"
            "assets/resources/commonasset/eventengine/eventbinary/field/{}/EVT_HUT_EXT.eb.bytes")
    only = sys.argv[1] if len(sys.argv) > 1 else None
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    for L in LANGS:
        if only and L != only:
            continue
        src = open(GAME.format(L), 'rb').read()
        open(f"{BKP}/{L}-EVT_HUT_EXT.eb.bytes.preMusic.{stamp}", 'wb').write(src)
        out = add_music(src)
        open(GAME.format(L), 'wb').write(out)
        open(MOD.format(L), 'wb').write(out)
        print(f"{L}: EVT_HUT_EXT {len(src)} -> {len(out)} bytes (+{len(out)-len(src)})  Vivi's Theme on entry + after-battle")
    print("done" + (f" ({only})" if only else " (all 7 langs -> game + mod/hut/eb)"))
