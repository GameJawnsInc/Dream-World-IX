#!/usr/bin/env python3
# Inject an NPC object entry into a clean field .eb (field 1357/CUSTOM_FIELD_001 layout),
# WITHOUT shifting existing bytecode (HW's custom-field export corrupts entry-adds).
#
# Strategy:
#   * Clone the known-good Zidane object entry (entry1, file 640..956, 316 bytes) as new entry 2.
#   * NOP its DefinePlayerCharacter (so it's an NPC, not a 2nd player).
#   * Reposition it (x,z) so it doesn't overlap the player.
#   * Spawn it by overwriting one Main_Init Wait(2) (offset 458, "22 00 02") with
#     InitObject(2,0) ("09 02 00") -- identical length, no shift, no jump relocation.
#   * Append the clone, point entry-2's table slot at it.
#
# Usage: eb_inject_npc.py <in.eb> <out.eb> [npc_x] [npc_z] [model] [animset]
import sys, struct

E1_OFF, E1_LEN = 640, 316           # Zidane entry (clone source) file range
WAIT2_OFF = 458                     # a Main_Init Wait(2) to repurpose into InitObject(2,0)
E2_TBL = 144                        # entry-2 table slot (8 bytes: off2 sz2 loc1 fl1 pad2)
REL_DPC = 902 - E1_OFF              # DefinePlayerCharacter opcode, relative to entry start
REL_X   = 658 - E1_OFF              # x const (2 bytes LE), relative
REL_Z   = 666 - E1_OFF              # z const (2 bytes LE), relative
REL_MODEL = 691 - E1_OFF            # SetModel model arg (2 bytes LE) -> 2F 00 [62 00] 5D ; model at 689+2
REL_ANIMSET = 693 - E1_OFF          # SetModel animset (1 byte) -> ...5D

EXPECT = {
    WAIT2_OFF: bytes([0x22,0x00,0x02]),                 # Wait(2)
    E1_OFF:    bytes([0x02,0x02]),                      # entry1 type=2 funcCount=2
    658:       bytes([0x0A,0x00]),                      # x=10
    666:       bytes([0x0E,0xFD]),                      # z=-754
    689:       bytes([0x2F,0x00,0x62,0x00,0x5D]),       # SetModel(98,93)
    902:       bytes([0x2C]),                           # DefinePlayerCharacter
    E2_TBL:    bytes([0x00,0x02,0x00,0x00,0x00,0x00]),  # entry2: off=512 sz=0 loc=0 fl=0
}

def s16le(v): return struct.pack('<h', v)
def u16le(v): return struct.pack('<H', v)

def inject(data, npc_x, npc_z, model, animset):
    b = bytearray(data)
    for off, exp in EXPECT.items():
        if bytes(b[off:off+len(exp)]) != exp:
            raise SystemExit(f"ASSERT FAIL at {off}: got {b[off:off+len(exp)].hex()} expected {exp.hex()}")
    # 1) clone Zidane entry
    clone = bytearray(b[E1_OFF:E1_OFF+E1_LEN])
    # 2) NPC-ify: NOP DefinePlayerCharacter (0x2C -> 0x00 NOTHING)
    clone[REL_DPC] = 0x00
    # 3) reposition
    clone[REL_X:REL_X+2]   = s16le(npc_x)
    clone[REL_Z:REL_Z+2]   = s16le(npc_z)
    # 4) optional model/animset swap
    if model is not None:   clone[REL_MODEL:REL_MODEL+2] = u16le(model)
    if animset is not None: clone[REL_ANIMSET] = animset & 0xFF
    # 5) spawn: Main_Init Wait(2) -> InitObject(2,0)
    b[WAIT2_OFF:WAIT2_OFF+3] = bytes([0x09, 0x02, 0x00])
    # 6) append clone, set entry-2 table slot
    new_off = len(b) - 128
    b += clone
    b[E2_TBL:E2_TBL+2]   = u16le(new_off)     # off
    b[E2_TBL+2:E2_TBL+4] = u16le(E1_LEN)      # sz
    b[E2_TBL+4]          = 0x00               # loc
    b[E2_TBL+5]          = 0x00               # fl
    return bytes(b)

if __name__ == "__main__":
    inp, outp = sys.argv[1], sys.argv[2]
    npc_x = int(sys.argv[3]) if len(sys.argv) > 3 else 400
    npc_z = int(sys.argv[4]) if len(sys.argv) > 4 else -1400
    model = int(sys.argv[5]) if len(sys.argv) > 5 else None
    animset = int(sys.argv[6]) if len(sys.argv) > 6 else None
    out = inject(open(inp,'rb').read(), npc_x, npc_z, model, animset)
    open(outp,'wb').write(out)
    print(f"wrote {outp}: {len(out)} bytes (was {len(open(inp,'rb').read())}); NPC x={npc_x} z={npc_z} model={model}")
