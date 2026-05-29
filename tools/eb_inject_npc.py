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
# animation-setter arg offsets relative to func0 body start (file 650): each setter is op+argflag+2byte arg
REL_ANIM = {  # name: offset-within-func0-body of the 2-byte anim id
    "stand": 709 - 650, "walk": 713 - 650, "run": 717 - 650, "left": 721 - 650, "right": 725 - 650,
}

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

def inject(data, npc_x, npc_z, model, animset, talk_textid=62, anims=None):
    b = bytearray(data)
    for off, exp in EXPECT.items():
        if bytes(b[off:off+len(exp)]) != exp:
            raise SystemExit(f"ASSERT FAIL at {off}: got {b[off:off+len(exp)].hex()} expected {exp.hex()}")
    # --- extract the two functions of the Zidane entry (funcBase = E1_OFF+2) ---
    fbase = E1_OFF + 2
    # original func table: (tag0=0,fpos0=8),(tag1=1,fpos1)
    fpos0 = b[fbase+2] | (b[fbase+3] << 8)            # =8
    fpos1 = b[fbase+6] | (b[fbase+7] << 8)            # Zidane_Loop start
    f0 = bytearray(b[fbase+fpos0 : fbase+fpos1])      # func0 (Init) body
    f1 = bytearray(b[fbase+fpos1 : E1_OFF+E1_LEN])    # func1 (Loop) body
    # --- NPC-ify func0 (offsets are relative to func0 body start = fbase+fpos0 = file 650) ---
    body0 = fbase + fpos0                             # =650
    f0[REL_DPC - (body0 - E1_OFF)] = 0x00             # NOP DefinePlayerCharacter
    f0[REL_X  - (body0 - E1_OFF) : REL_X - (body0 - E1_OFF) + 2] = s16le(npc_x)
    f0[REL_Z  - (body0 - E1_OFF) : REL_Z - (body0 - E1_OFF) + 2] = s16le(npc_z)
    if model is not None:   f0[REL_MODEL - (body0 - E1_OFF):REL_MODEL - (body0 - E1_OFF)+2] = u16le(model)
    if animset is not None: f0[REL_ANIMSET - (body0 - E1_OFF)] = animset & 0xFF
    for name, val in (anims or {}).items():
        o = REL_ANIM[name]; f0[o:o+2] = u16le(val)
    # --- build func2 = _SpeakBTN: WindowSync(1,128,textid) ; return(0x04) ---
    f2 = bytes([0x1F, 0x00, 0x01, 0x80]) + u16le(talk_textid) + bytes([0x04])
    # --- assemble new entry: type=2, funcCount=3, 12-byte func table, then f0|f1|f2 ---
    TABLE = 3 * 4
    nf0, nf1, nf2 = TABLE, TABLE + len(f0), TABLE + len(f0) + len(f1)
    table = u16le(0)+u16le(nf0) + u16le(1)+u16le(nf1) + u16le(3)+u16le(nf2)
    entry = bytes([0x02, 0x03]) + table + bytes(f0) + bytes(f1) + f2
    # --- spawn: Main_Init Wait(2) -> InitObject(2,0) ---
    b[WAIT2_OFF:WAIT2_OFF+3] = bytes([0x09, 0x02, 0x00])
    # --- append entry, set entry-2 table slot ---
    new_off = len(b) - 128
    b += entry
    b[E2_TBL:E2_TBL+2]   = u16le(new_off)
    b[E2_TBL+2:E2_TBL+4] = u16le(len(entry))
    b[E2_TBL+4]          = 0x00
    b[E2_TBL+5]          = 0x00
    return bytes(b)

# character presets: (model, animset, {stand,walk,run,left,right})
PRESETS = {
    "vivi":   (8,  61, {"stand":148, "walk":571, "run":419, "left":917, "right":918}),
    "zidane": (None, None, None),  # leave the cloned Zidane model/anims as-is
}

if __name__ == "__main__":
    inp, outp = sys.argv[1], sys.argv[2]
    npc_x = int(sys.argv[3]) if len(sys.argv) > 3 else 400
    npc_z = int(sys.argv[4]) if len(sys.argv) > 4 else -1400
    preset = sys.argv[5] if len(sys.argv) > 5 else "zidane"
    talk_textid = int(sys.argv[6]) if len(sys.argv) > 6 else 62
    model, animset, anims = PRESETS[preset]
    out = inject(open(inp,'rb').read(), npc_x, npc_z, model, animset, talk_textid, anims)
    open(outp,'wb').write(out)
    print(f"wrote {outp}: {len(out)} bytes; NPC x={npc_x} z={npc_z} preset={preset} textid={talk_textid}")
