#!/usr/bin/env python3
# Add field BGM (Vivi's Theme) to Alexandria/Main Street (field 100) so it plays on our cold
# New-Game skip. Field 100's own music call is RunSoundCode(1792, 9): songcode 1792 is a
# resume/sync variant that no-ops when the song was never loaded by a preceding scene (we skip
# straight in) -- songid 9 (Vivi's Theme) is correct. We insert the known-good song_play call
# RunSoundCode(0, 9) = C5 00 00 00 09 00 right AFTER the 1792 call so it force-starts the track.
#
# Insertion @752 (right after RunSoundCode(1792,9) @746) is jump-safe: Main_Init func0 jumps are
# 766->755 and 851->844, all endpoints > 752, so they shift together. insert_bytes grows the
# containing entry + shifts later entries (entry-count aware).
import os, struct
from datetime import datetime

RUNSOUND_VIVI = bytes([0xC5,0x00,0x00,0x00,0x09,0x00])   # RunSoundCode(0, 9)
MUSIC1792     = bytes([0xC5,0x00,0x00,0x07,0x09,0x00])    # RunSoundCode(1792, 9)
INS_OFF = 752                                            # right after the 1792 call (746..752)

def u16(b,o): return struct.unpack_from('<H',b,o)[0]

def insert_bytes(data, abs_off, ins):
    b = bytearray(data); n = b[3]
    E=Eoff=None
    for i in range(n):
        off,sz=u16(b,128+i*8),u16(b,128+i*8+2)
        if sz>0 and 128+off <= abs_off < 128+off+sz: E,Eoff,Esz=i,off,sz; break
    if E is None: raise SystemExit(f"no entry at {abs_off}")
    struct.pack_into('<H', b, 128+E*8+2, Esz+len(ins))
    for j in range(n):
        if j==E: continue
        off=u16(b,128+j*8)
        if off>Eoff: struct.pack_into('<H', b, 128+j*8, off+len(ins))
    return bytes(b[:abs_off])+ins+bytes(b[abs_off:])

def add(data):
    if bytes(data[INS_OFF-6:INS_OFF]) != MUSIC1792:
        raise SystemExit(f"no RunSoundCode(1792,9) before {INS_OFF}: {data[INS_OFF-6:INS_OFF].hex()}")
    return insert_bytes(data, INS_OFF, RUNSOUND_VIVI)

LANGS=["us","uk","fr","gr","it","es","jp"]
GAME="C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"
CM=GAME+"/FF9CustomMap/StreamingAssets/assets/resources/commonasset/eventengine/eventbinary/field/{lang}/evt_alex1_at_street_a.eb.bytes"
HERE=os.path.dirname(os.path.abspath(__file__)); BKP=HERE+"/../backups"; MODA=HERE+"/../mod/alex/eb"

if __name__=="__main__":
    stamp=datetime.now().strftime("%Y%m%d-%H%M%S")
    for L in LANGS:
        p=CM.format(lang=L); src=open(p,'rb').read()
        open(f"{BKP}/{L}-evt_alex1_at_street_a.eb.bytes.premusic.{stamp}",'wb').write(src)
        out=add(src)
        open(p,'wb').write(out); open(f"{MODA}/{L}-evt_alex1_at_street_a.eb.bytes",'wb').write(out)
        print(f"{L}: field100 {len(src)}->{len(out)} (+{len(out)-len(src)})  RunSoundCode(0,9) Vivi's Theme on entry")
    print("done (7 langs). backups: backups/*.premusic.*")
