#!/usr/bin/env python3
# Inject random-battle encounters into a field .eb WITHOUT shifting bytecode.
#   - Append a type-0 "code" entry whose func0 runs:
#       SetRandomBattles(0x3C, pattern, s0,s1,s2,s3)  ; SetRandomBattleFrequency(0x57, freq) ; return(0x04)
#   - Activate it via InitCode(slot,0) (0x07) written over a Main_Init Wait(2) filler (22 00 02).
# _enCountData / encratio are engine-context globals, so a separate init thread setting them is fine.
#
# Opcode encoding (argflag=0 => all immediate; sizes from EventEngineUtils):
#   SetRandomBattles  0x3C: argCount 5, sizes [1,2,2,2,2]
#   SetRandomBattleFreq 0x57: argCount 1, sizes [1]
#   InitCode 0x07 (NEW): "07 <slot> 00"  (opcode <0x10 => no argflag; arg1=slot, arg2=uid)
import struct

def build_entry(pattern, scenes, freq):
    assert len(scenes) == 4
    code = bytes([0x3C, 0x00, pattern & 0xFF])
    for s in scenes:
        code += struct.pack('<H', s & 0xFFFF)
    code += bytes([0x57, 0x00, freq & 0xFF])
    code += bytes([0x04])                              # return
    # entry: type=0, funcCount=1, funcTable[tag=0, fpos=4], then code
    return bytes([0x00, 0x01]) + struct.pack('<H', 0) + struct.pack('<H', 4) + code

def inject(data, slot, wait_off, pattern=1, scenes=(139, 139, 139, 139), freq=255):
    b = bytearray(data)
    if bytes(b[wait_off:wait_off+3]) != bytes([0x22, 0x00, 0x02]):
        raise SystemExit(f"no Wait(2) filler at {wait_off}: {b[wait_off:wait_off+3].hex()}")
    tslot = 128 + slot * 8
    if struct.unpack_from('<H', b, tslot+2)[0] != 0:
        raise SystemExit(f"entry slot {slot} not free: {b[tslot:tslot+8].hex()}")
    entry = build_entry(pattern, list(scenes), freq)
    b[wait_off:wait_off+3] = bytes([0x07, slot, 0x00])      # InitCode(slot, 0)
    off = len(b) - 128
    b += entry
    struct.pack_into('<H', b, tslot,   off)
    struct.pack_into('<H', b, tslot+2, len(entry))
    b[tslot+4] = 0; b[tslot+5] = 0; b[tslot+6] = 0; b[tslot+7] = 0
    return bytes(b)

if __name__ == "__main__":
    import os
    LANGS = ["us", "uk", "fr", "gr", "it", "es", "jp"]
    MOD  = os.path.dirname(os.path.abspath(__file__)) + "/../mod/hut/eb/{}-EVT_HUT_EXT.eb.bytes"
    GAME = ("C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX/FF9CustomMap/StreamingAssets/"
            "assets/resources/commonasset/eventengine/eventbinary/field/{}/EVT_HUT_EXT.eb.bytes")
    SLOT, WAIT, SCENE, FREQ = 3, 461, 139, 255
    for L in LANGS:
        src = open(GAME.format(L), 'rb').read()
        out = inject(src, SLOT, WAIT, pattern=1, scenes=(SCENE,)*4, freq=FREQ)
        open(GAME.format(L), 'wb').write(out)
        open(MOD.format(L), 'wb').write(out)
        print(f"{L}: EVT_HUT_EXT {len(out)} bytes  (encounter slot {SLOT}: scene {SCENE} x4, freq {FREQ})")
    print("deployed to game + mod/hut/eb")
