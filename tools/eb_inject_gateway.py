#!/usr/bin/env python3
# Inject a field-exit GATEWAY (region trigger) into a clean field .eb, by cloning field 109's
# proven exit region (entry 6 of EVT_CUSTOM_FIELD_002) and patching only:
#   - the SetRegion trigger polygon (5 points, x/z),
#   - the Field() target id,
#   - General_FieldEntrance (which entrance to arrive at in the target).
# Then append it as a region entry and activate it via InitRegion(slot,0) over a Main_Init
# Wait(2) filler (offset 458, same trick as the NPC injector -> no byte shift, no relocation).
#
# Region template = field 109 Region6 (272 bytes): SetRegion -> CalculateExitPosition/ExitField
# -> PreloadField -> FadeFilter -> set General_FieldEntrance -> Field(target). Internal jumps are
# relative, so the entry relocates cleanly when appended.
#
# Usage: eb_inject_gateway.py <in.eb> <out.eb> <target_field> <slot> [entrance] [x1 z1 ... x5 z5]
import sys, struct

TEMPLATE = bytes.fromhex(
 "010200000800020020002900058800e6f7e4feaaf7d5fde3f9c602dffa5704b9fa04057a027f"
 "0301000405c5a27d01002c7f05c5a37d01002c7fa49e05c59e7d00002c7f05c59f7d0100207f"
 "0213002d05c5907d0000207f020400ab01030022000127007ffd0005670005d9157d67002c7f"
 "05d5117dff00207f020f00057a0c7da000157a0d7d700015667fa900faec040618d5117fffff"
 "ff22001905c5a77d0100207f020e00c5000901ffff05c5a77d00002c7f05c5a27d0000207f02"
 "1c0005d40d7d0900187f02080005d40d7d03002c7fc6008051630100000005c5a37d0000207f"
 "021c0005d40e7d0900187f02080005d40e7d03002c7fc60080519f0100000005d8027de4002c"
 "7f2b00670004")
assert len(TEMPLATE) == 272, len(TEMPLATE)

REL_PTS, REL_ENTRANCE, REL_FIELD = 13, 263, 269   # offsets within the entry
WAIT2_OFF = 458                                    # Main_Init Wait(2) filler -> InitRegion

def inject(data, target, slot, entrance, zone):
    b = bytearray(data)
    if bytes(b[WAIT2_OFF:WAIT2_OFF+3]) != bytes([0x22,0x00,0x02]):
        raise SystemExit(f"no Wait(2) filler at {WAIT2_OFF}: {b[WAIT2_OFF:WAIT2_OFF+3].hex()}")
    tslot = 128 + slot*8
    if bytes(b[tslot:tslot+4]) != bytes([0x00,0x02,0x00,0x00]):
        raise SystemExit(f"entry slot {slot} not empty (off2 sz0): {b[tslot:tslot+8].hex()}")
    e = bytearray(TEMPLATE)
    for i,(x,z) in enumerate(zone):                # patch 5-point polygon
        struct.pack_into('<hh', e, REL_PTS+i*4, x, z)
    struct.pack_into('<H', e, REL_ENTRANCE, entrance)
    struct.pack_into('<H', e, REL_FIELD, target)
    b[WAIT2_OFF:WAIT2_OFF+3] = bytes([0x08, slot, 0x00])   # InitRegion(slot,0)
    off = len(b) - 128
    b += e
    struct.pack_into('<H', b, tslot, off)          # entry table slot: off, sz, loc=0, fl=0
    struct.pack_into('<H', b, tslot+2, len(e))
    b[tslot+4]=0; b[tslot+5]=0; b[tslot+6]=0; b[tslot+7]=0
    return bytes(b)

# default door zone: back of the floor (near the hut), pentagon x[-400,400], z[-85,-600]
DEFAULT_ZONE = [(-400,-85),(400,-85),(400,-600),(0,-600),(-400,-600)]

if __name__ == "__main__":
    inp, outp, target, slot = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
    entrance = int(sys.argv[5]) if len(sys.argv) > 5 else 228
    if len(sys.argv) > 6:
        nums = list(map(int, sys.argv[6:])); zone = [(nums[2*i],nums[2*i+1]) for i in range(len(nums)//2)]
    else:
        zone = DEFAULT_ZONE
    assert len(zone) == 5, "need exactly 5 polygon points"
    out = inject(open(inp,'rb').read(), target, slot, entrance, zone)
    open(outp,'wb').write(out)
    print(f"wrote {outp}: {len(out)} bytes; gateway slot {slot} -> Field({target}) entrance {entrance} zone {zone}")
