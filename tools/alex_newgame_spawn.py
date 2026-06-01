#!/usr/bin/env python3
# Decouple the New-Game Alexandria spawn from the room-door spawn.
#
# Field 100's player-init switch (entry 19 @10805) maps General_FieldEntrance:
#   201 -> block A (top), 231 -> block B, 204 -> block C (now the door).
# Main_Init's switch (@587) treats 201/231/204 as the NORMAL (festival-free) branch;
# ANY other value -> the festival ticket cutscene (softlock). So we can't invent a new
# entrance -- we must reuse a real one. We route New Game through entrance 231 -> block B
# and repaint block B to the original bottom-of-walkway spawn (0, 332, dir 128). Block C
# (entrance 204) stays the door for the 4000->100 return. (Engine New-Game entrance is
# changed 204 -> 231 separately.)
#
# Block B @10894: D9(0)=X @10898 (8e 02=654), D9(4)=Z @10906 (31 04=1073), D9(6)=dir @10914 (40 00=64).
import os, struct
from datetime import datetime

X_OFF, Z_OFF, DIR_OFF = 10898, 10906, 10914
OLD = {X_OFF: bytes([0x8E,0x02]), Z_OFF: bytes([0x31,0x04]), DIR_OFF: bytes([0x40,0x00])}
NEW = {X_OFF: struct.pack('<h', 0), Z_OFF: struct.pack('<h', 332), DIR_OFF: struct.pack('<h', 128)}

def patch(data):
    b = bytearray(data)
    for off, old in OLD.items():
        assert bytes(b[off:off+2]) == old, f"unexpected @{off}: {b[off:off+2].hex()} (want {old.hex()})"
    for off, new in NEW.items():
        b[off:off+2] = new
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
        open(f"{BKP}/{L}-evt_alex1_at_street_a.eb.bytes.prenewgamespawn.{stamp}",'wb').write(src)
        out = patch(src)
        open(p,'wb').write(out); open(f"{MODA}/{L}-evt_alex1_at_street_a.eb.bytes",'wb').write(out)
        print(f"{L}: block B (entrance 231) spawn (654,1073) -> (0,332) [New-Game bottom]")
    print("done (7 langs). backups: backups/*.prenewgamespawn.*")
