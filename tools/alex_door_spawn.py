#!/usr/bin/env python3
# Make field-100 entrance 204 (used by BOTH New-Game->Alexandria and our 4000->100 return)
# spawn the player right in FRONT OF the custom-room door instead of the bottom of the walkway.
#
# Field 100's player init (entry 19, tag-0) switches on General_FieldEntrance (=D8(2)) at [10805]:
#   entrance 201 -> block A (top), 231 -> block B, 204 -> block C, default -> block D.
# Block C @10975 sets the spawn: D9(0)=X, D9(4)=Z, D9(6)=dir, then CreateObject(D9(0),D9(4)).
#   X imm @10979 (00 00 = 0), Z imm @10987 (4c 01 = 332), dir @10995 (80 00 = 128).
# Door region (entry 18) is x[-700,200], z[2200,3400]. Spawn just below its near edge, centered:
#   X = -250 (0xFF06), Z = 2100 (0x0834). dir kept (128). No insert -> zero jump/table risk.
import os, struct
from datetime import datetime

X_OFF, Z_OFF = 10979, 10987
OLD_X, OLD_Z = bytes([0x00,0x00]), bytes([0x4C,0x01])   # 0, 332  (block C, entrance 204)
NEW_X = struct.pack('<h', -250)   # 06 ff
NEW_Z = struct.pack('<h', 2100)   # 34 08

def patch(data):
    b = bytearray(data)
    assert bytes(b[X_OFF:X_OFF+2]) == OLD_X, f"X not 0 at {X_OFF}: {b[X_OFF:X_OFF+2].hex()}"
    assert bytes(b[Z_OFF:Z_OFF+2]) == OLD_Z, f"Z not 332 at {Z_OFF}: {b[Z_OFF:Z_OFF+2].hex()}"
    b[X_OFF:X_OFF+2] = NEW_X
    b[Z_OFF:Z_OFF+2] = NEW_Z
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
        open(f"{BKP}/{L}-evt_alex1_at_street_a.eb.bytes.predoorspawn.{stamp}",'wb').write(src)
        out = patch(src)
        open(p,'wb').write(out); open(f"{MODA}/{L}-evt_alex1_at_street_a.eb.bytes",'wb').write(out)
        print(f"{L}: entrance-204 spawn (0,332) -> (-250,2100) [in front of door]")
    print("done (7 langs). backups: backups/*.predoorspawn.*")
