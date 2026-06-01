#!/usr/bin/env python3
# Wire field 4000 (our custom room) into Alexandria Main Street (field 100) as a ROUND TRIP:
#   - EXIT  : HUT field 4000 -> Field(100) entrance 204 (arrive at field 100's "from-107" spot)
#   - DOOR  : field 100 -> Field(4000) entrance 0   (the Alexandria entrance, sensible first-guess)
#
# Both use field 109's proven exit-region TEMPLATE (272 B): SetRegion polygon -> CalculateExitPosition
# /ExitField -> PreloadField -> FadeFilter -> set General_FieldEntrance -> Field(target). The entry is
# appended into a free entry-table slot and ACTIVATED by inserting InitRegion(slot,0) into Main_Init at
# a jump-safe offset (grow containing entry, shift later entries; internal fpos are relative).
#
# Zones are convex quads with the LAST vertex DOUBLED (IsInQuad fans triplets; collinear pts => dead
# zone -> doubled-quad gives full coverage via 2 real triangles). Point order q0->q1 = walk-out edge.
import struct, os, sys
from datetime import datetime

TEMPLATE = bytes.fromhex(
 "010200000800020020002900058800e6f7e4feaaf7d5fde3f9c602dffa5704b9fa04057a027f"
 "0301000405c5a27d01002c7f05c5a37d01002c7fa49e05c59e7d00002c7f05c59f7d0100207f"
 "0213002d05c5907d0000207f020400ab01030022000127007ffd0005670005d9157d67002c7f"
 "05d5117dff00207f020f00057a0c7da000157a0d7d700015667fa900faec040618d5117fffff"
 "ff22001905c5a77d0100207f020e00c5000901ffff05c5a77d00002c7f05c5a27d0000207f02"
 "1c0005d40d7d0900187f02080005d40d7d03002c7fc6008051630100000005c5a37d0000207f"
 "021c0005d40e7d0900187f02080005d40e7d03002c7fc60080519f0100000005d8027de4002c"
 "7f2b00670004")
assert len(TEMPLATE) == 272
REL_PTS, REL_ENTRANCE, REL_FIELD = 13, 263, 269

def u16(b, o): return struct.unpack_from('<H', b, o)[0]

def insert_bytes(data, abs_off, ins):
    """Insert `ins` at abs_off; grow the containing entry; shift later entries (entry-count aware)."""
    b = bytearray(data); n = b[3]
    E = Eoff = None
    for i in range(n):
        off, sz = u16(b, 128+i*8), u16(b, 128+i*8+2)
        if sz > 0 and 128+off <= abs_off < 128+off+sz:
            E, Eoff, Esz = i, off, sz; break
    if E is None:
        raise SystemExit(f"no entry contains file offset {abs_off}")
    struct.pack_into('<H', b, 128+E*8+2, Esz + len(ins))
    for j in range(n):
        if j == E: continue
        off = u16(b, 128+j*8)
        if off > Eoff:
            struct.pack_into('<H', b, 128+j*8, off + len(ins))
    return bytes(b[:abs_off]) + ins + bytes(b[abs_off:])

def make_entry(target, entrance, zone):
    e = bytearray(TEMPLATE)
    assert len(zone) == 5, "need 5 polygon points (convex quad + doubled last vertex)"
    for i,(x,z) in enumerate(zone):
        struct.pack_into('<hh', e, REL_PTS+i*4, x, z)
    struct.pack_into('<H', e, REL_ENTRANCE, entrance)
    struct.pack_into('<H', e, REL_FIELD, target)
    return bytes(e)

def inject_gateway(data, target, entrance, slot, zone, insert_off, prev_initregion):
    """Append a gateway entry into `slot`, activate via InitRegion(slot,0) at insert_off.
       prev_initregion = the 3 bytes that must immediately precede insert_off (sanity check)."""
    b = bytearray(data)
    # sanity: insert point sits right after an existing InitRegion(prev,0)
    got = bytes(b[insert_off-3:insert_off])
    if got != prev_initregion:
        raise SystemExit(f"insert@{insert_off}: expected preceding {prev_initregion.hex()} got {got.hex()}")
    # sanity: target slot empty
    if u16(b, 128+slot*8+2) != 0:
        raise SystemExit(f"slot {slot} not empty (sz={u16(b,128+slot*8+2)})")
    # 1) insert InitRegion(slot,0) into Main_Init (shifts later entries)
    b = bytearray(insert_bytes(bytes(b), insert_off, bytes([0x08, slot, 0x00])))
    # 2) append gateway entry at end, register in slot
    entry = make_entry(target, entrance, zone)
    off = len(b) - 128
    b += entry
    struct.pack_into('<H', b, 128+slot*8, off)
    struct.pack_into('<H', b, 128+slot*8+2, len(entry))
    b[128+slot*8+4] = 0; b[128+slot*8+5] = 0; b[128+slot*8+6] = 0; b[128+slot*8+7] = 0
    return bytes(b)

LANGS = ["us","uk","fr","gr","it","es","jp"]
GAME = "C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"
AF   = GAME + "/AlternateFantasy/StreamingAssets/assets/resources/commonasset/eventengine/eventbinary/field/{lang}/evt_alex1_at_street_a.eb.bytes"
CM_F = GAME + "/FF9CustomMap/StreamingAssets/assets/resources/commonasset/eventengine/eventbinary/field/{lang}/{name}"
HERE = os.path.dirname(os.path.abspath(__file__))
BKP  = HERE + "/../backups"
MODA = HERE + "/../mod/alex/eb"
MODH = HERE + "/../mod/hut/eb"

# --- ZONES (sensible first guesses; user verifies/iterates) ---
# HUT 4000 exit: LEFT side of room, clear of the front-center 4002 door (z -85..-600).
#   walkmesh trapezoid back z=340 x[-1142,-3], front z=-3344 x[-1799,1465]; left edge @ z=-2000 ~ x=-1559.
HUT_ZONE = [(-1400,-1800),(-1400,-2600),(-700,-2600),(-700,-1800),(-700,-1800)]  # q0->q1 = left edge (walk -x)
# Field 100 door: center-left, MID-street (z 2200..3400), away from existing exits
#   (top z6500+, bottom z-440..190, right x1224+) and from the from-107 spawn (bottom).
F100_ZONE = [(-700,2200),(200,2200),(200,3400),(-700,3400),(-700,3400)]

def run():
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    os.makedirs(MODA, exist_ok=True); os.makedirs(MODH, exist_ok=True)
    INITREG = lambda s: bytes([0x08, s, 0x00])
    for L in LANGS:
        # ---- HUT 4000 EXIT -> Field(100) ent 204 (slot 4, insert after InitRegion(2,0) @465) ----
        hp = CM_F.format(lang=L, name="EVT_HUT_EXT.eb.bytes")
        src = open(hp,'rb').read()
        open(f"{BKP}/{L}-EVT_HUT_EXT.eb.bytes.prealexit.{stamp}",'wb').write(src)
        out = inject_gateway(src, target=100, entrance=204, slot=4, zone=HUT_ZONE,
                             insert_off=465, prev_initregion=INITREG(2))
        open(hp,'wb').write(out); open(f"{MODH}/{L}-EVT_HUT_EXT.eb.bytes",'wb').write(out)
        h_delta = len(out)-len(src)
        # ---- Field 100 DOOR -> Field(4000) ent 0 (slot 18, insert after InitRegion(11,0) @743) ----
        ap = AF.format(lang=L)
        asrc = open(ap,'rb').read()
        open(f"{BKP}/{L}-evt_alex1_at_street_a.eb.bytes.afbase.{stamp}",'wb').write(asrc)
        aout = inject_gateway(asrc, target=4000, entrance=0, slot=18, zone=F100_ZONE,
                              insert_off=743, prev_initregion=INITREG(11))
        cm = CM_F.format(lang=L, name="evt_alex1_at_street_a.eb.bytes")
        os.makedirs(os.path.dirname(cm), exist_ok=True)
        open(cm,'wb').write(aout); open(f"{MODA}/{L}-evt_alex1_at_street_a.eb.bytes",'wb').write(aout)
        print(f"{L}: HUT {len(src)}->{len(out)} (+{h_delta}) exit->100 ; ALEX {len(asrc)}->{len(aout)} (+{len(aout)-len(asrc)}) door->4000")
    print("done (7 langs). backups in backups/, tracked copies in mod/alex|hut/eb/")

if __name__ == "__main__":
    run()
