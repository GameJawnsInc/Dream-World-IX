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
gw  = _load("eb_inject_gateway", HERE + "/eb_inject_gateway.py")

LANGS = ["us", "uk", "fr", "gr", "it", "es", "jp"]
SRC  = HERE + "/../mod/custom-room-01/ingame-eb/{}-EVT_CUSTOM_FIELD_001.eb.bytes"
MOD  = HERE + "/../mod/hut/eb/{}-EVT_HUT_INT.eb.bytes"
GAME = ("C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX/FF9CustomMap/StreamingAssets/"
        "assets/resources/commonasset/eventengine/eventbinary/field/{}/EVT_HUT_INT.eb.bytes")

# --- tunable positions (world x, z) ---
VIVI   = (0, -700)    # back/upper area, ahead of the player on entry
PLAYER = (0, -1350)   # mid floor, clearly ABOVE the exit zone (no spawn-in-zone instant-exit)
TEXTID = 500          # Vivi's custom line ("I miss you Zidane")

# --- exit gateway: front strip of the floor -> back outside (Field 4000) ---
EXIT_TARGET = 4000
EXIT_SLOT   = 3       # entry slot (Vivi=2); InitRegion(3,0) over the 2nd Main_Init Wait(2) @461
EXIT_WAIT   = 461     # the second Wait(2) filler (the first @458 was used for Vivi's InitObject)
EXIT_ENTR   = 0       # target has no EntryList -> entrance ignored, spawns at 4000's default (10,-754)
# IsInQuad (EventEngine.TreadQuad.cs) tests the player against a FAN of consecutive vertex
# triplets (q[i],q[i+1],q[i+2]), NOT the true polygon. Three collinear points => a zero-area
# triangle and a DEAD ZONE in the polygon centre (the old z[-2050,-2267] 5-pt strip had its
# whole front edge collinear -> centre-front never triggered). Use a CONVEX QUAD with the last
# vertex DOUBLED (5 pts, no degenerate triple) so the fan covers the region completely.
# Point ORDER matters beyond coverage: CalculateExitPosition (0xA4) projects the player onto the
# q[0]->q[1] edge and ExitField (0x9E) walks them there before the fade. Put the FRONT edge
# (z=-2400) first so the down-walking player continues FORWARD into the fade (no turn-around arc).
EXIT_ZONE   = [(-1100, -2400), (1100, -2400), (1100, -1750), (-1100, -1750), (-1100, -1750)]

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
    moved = set_player(withvivi, PLAYER[0], PLAYER[1])
    final = gw.inject(moved, EXIT_TARGET, EXIT_SLOT, EXIT_ENTR, EXIT_ZONE, wait_off=EXIT_WAIT)
    open(MOD.format(lang), 'wb').write(final)
    open(GAME.format(lang), 'wb').write(final)
    return len(final)

if __name__ == "__main__":
    for lang in LANGS:
        n = build_one(lang)
        print(f"{lang}: EVT_HUT_INT {n} bytes  (Vivi {VIVI}, player {PLAYER}, textid {TEXTID}, "
              f"exit->{EXIT_TARGET} slot{EXIT_SLOT})")
    print("deployed to mod/hut/eb + game FF9CustomMap")
