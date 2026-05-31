#!/usr/bin/env python3
# Build EVT_HUT_INT (Vivi's House interior) for all 7 langs, reproducibly:
#   clean script (CUSTOM_FIELD_001, 956B)  -> inject Vivi NPC (eb_inject_npc)  -> move player spawn.
# ORDER MATTERS: eb_inject_npc asserts the pristine player bytes (x=10 @658, z=-754 @666) because it
# clones entry1 as the Vivi template, so reposition the PLAYER only AFTER Vivi is injected.
#
# Layout (48-deg cam, floor z[-2267 front .. -85 back], canvasY 432..205):
#   player spawns at the FRONT/bottom (the hut door they walked through) facing into the room;
#   Vivi stands ahead, in the visible centre of the floor.
import os, struct, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
npc = _load("eb_inject_npc", HERE + "/eb_inject_npc.py")

LANGS = ["us", "uk", "fr", "gr", "it", "es", "jp"]
SRC  = HERE + "/../mod/custom-room-01/ingame-eb/{}-EVT_CUSTOM_FIELD_001.eb.bytes"
MOD  = HERE + "/../mod/hut/eb/{}-EVT_HUT_INT.eb.bytes"
GAME = ("C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX/FF9CustomMap/StreamingAssets/"
        "assets/resources/commonasset/eventengine/eventbinary/field/{}/EVT_HUT_INT.eb.bytes")

# --- tunable positions (world x, z) ---
VIVI   = (0, -950)    # canvasY ~274, centre of the visible floor
PLAYER = (0, -1850)   # canvasY ~372, front/bottom near the door; clear of any front exit zone
TEXTID = 500          # Vivi's custom line ("I miss you Zidane")

PX_OFF, PZ_OFF = 658, 666   # player (entry1) X / Z const bytes, file offsets in the clean script

def set_player(data, x, z):
    b = bytearray(data)
    assert bytes(b[PX_OFF:PX_OFF+2]) == bytes([0x0A, 0x00]), b[PX_OFF:PX_OFF+2].hex()
    assert bytes(b[PZ_OFF:PZ_OFF+2]) == bytes([0x0E, 0xFD]), b[PZ_OFF:PZ_OFF+2].hex()
    struct.pack_into('<h', b, PX_OFF, x); struct.pack_into('<h', b, PZ_OFF, z)
    return bytes(b)

def build_one(lang):
    clean = open(SRC.format(lang), 'rb').read()
    model, animset, anims = npc.PRESETS["vivi"]
    withvivi = npc.inject(clean, VIVI[0], VIVI[1], model, animset, talk_textid=TEXTID, anims=anims)
    final = set_player(withvivi, PLAYER[0], PLAYER[1])
    open(MOD.format(lang), 'wb').write(final)
    open(GAME.format(lang), 'wb').write(final)
    return len(final)

if __name__ == "__main__":
    for lang in LANGS:
        n = build_one(lang)
        print(f"{lang}: EVT_HUT_INT {n} bytes  (Vivi {VIVI}, player {PLAYER}, textid {TEXTID})")
    print("deployed to mod/hut/eb + game FF9CustomMap")
