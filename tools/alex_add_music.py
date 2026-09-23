#!/usr/bin/env python3
# Add field BGM (Vivi's Theme) to Alexandria/Main Street (field 100) so it plays on our cold
# New-Game skip. Field 100's own music call is RunSoundCode(1792, 9): songcode 1792 is a
# resume/sync variant that no-ops when the song was never loaded by a preceding scene (we skip
# straight in) -- songid 9 (Vivi's Theme) is correct. We insert the known-good song_play call
# RunSoundCode(0, 9) = C5 00 00 00 09 00 right AFTER the 1792 call so it force-starts the track.
#
# Insertion @752 (right after RunSoundCode(1792,9) @746) is jump-safe: Main_Init func0 jumps are
# 766->755 and 851->844, all endpoints > 752, so they shift together. The insert goes through the
# kit's edit.insert_in_function, which also moves Main_Init's later siblings (Main_Loop, Main_Reinit)
# with the bytes -- the local raw relayout this tool used to carry left both fpos 6 bytes short.
import os, sys
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit")))
from ff9mapkit.eb import EbScript, edit  # noqa: E402

RUNSOUND_VIVI = bytes([0xC5,0x00,0x00,0x00,0x09,0x00])   # RunSoundCode(0, 9)
MUSIC1792     = bytes([0xC5,0x00,0x00,0x07,0x09,0x00])    # RunSoundCode(1792, 9)
INS_OFF = 752                                            # right after the 1792 call (746..752)

def add(data):
    if bytes(data[INS_OFF-6:INS_OFF]) != MUSIC1792:
        raise SystemExit(f"no RunSoundCode(1792,9) before {INS_OFF}: {data[INS_OFF-6:INS_OFF].hex()}")
    main_init = EbScript.from_bytes(data).entry(0).func_by_tag(0)
    return edit.insert_in_function(data, 0, 0, INS_OFF - main_init.abs_start, RUNSOUND_VIVI)

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
