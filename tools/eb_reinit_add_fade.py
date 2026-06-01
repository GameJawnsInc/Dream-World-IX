#!/usr/bin/env python3
# Add a fast fade-IN to a custom field's after-battle handler (entry-0 tag-10 "Main_Reinit").
#
# WHY (Session 12): On battle-return the engine starts a 256-FRAME timed fade-in
# (BattleResultUI.Hide -> SceneDirector.FF9Wipe_FadeInEx(256) -> InitFade(Sub,256,black)),
# advanced 1 frame per field update (HonoluluFieldMain ServiceFade). It is TIMED, not load-bound
# (that's why the overlay texture cache didn't help). A normal field's Main_Init issues its own
# FadeFilter (e.g. FadeFilter(7,16,...,0,0,0)) which re-inits the same fade to ~16 frames -> quick.
# But after BATTLE the field runs tag-10 (Main_Reinit), not Main_Init, and our tag-10 was just
# `EnableMove; return` -> nothing overrides the 256-frame crawl. Fix: prepend a quick FadeFilter
# fade-in to tag-10 so it re-inits the fade to 16 frames.
#
# FadeFilter = WIPERGB (0xEC), 6 one-byte args (EventEngine.DoEventCode.cs:631):
#   filterMode(bit1 set => SUB => fade-IN), frame, <unused>, cyan, magenta, yellow.
# All-immediate FadeFilter(2,16,0,0,0,0) = `EC 00 02 10 00 00 00 00`  (argflag 00 = no var args).
# InitFade(Sub,16,black) fades the screen IN over 16 frames from its current state.
#
# RE-LAYOUT (+8): tag-10 body is the last bytes of entry-0 (appended by eb_add_reinit, == `2E 04`).
# Insert the 8 FadeFilter bytes at the START of tag-10's body (before EnableMove). entry-0 grows +8;
# tag-10's fpos is unchanged (body still starts there); funcs 0/1 are before it (unchanged); every
# later entry with off>0 shifts in the file so its entry-table off += 8. Jumps are relative and the
# insertion is at entry-0's tail, so no jump relocation is needed.
import struct, os, sys

def u16(b, o): return struct.unpack_from('<H', b, o)[0]

FADE = bytes([0xEC, 0x00, 0x02, 0x10, 0x00, 0x00, 0x00, 0x00])  # FadeFilter(2,16,0,0,0,0) = 16-frame fade-in
REINIT_BODY = bytes([0x2E, 0x04])                               # EnableMove ; return

def add_fade(data):
    b = bytearray(data)
    off0, sz0 = u16(b, 128), u16(b, 130)
    es = 128 + off0
    etype, fc = b[es], b[es+1]
    fbase = es + 2
    funcs = [(u16(b, fbase+i*4), u16(b, fbase+i*4+2)) for i in range(fc)]
    t10 = [(t, fp) for t, fp in funcs if t == 10]
    if not t10:
        raise SystemExit("entry0 has no tag-10 (run eb_add_reinit first)")
    fp10 = t10[0][1]
    body_start = fbase + fp10
    body = bytes(b[body_start: es + sz0])
    if body != REINIT_BODY:
        raise SystemExit(f"tag-10 body is not the expected EnableMove;return (2e 04): {body.hex()}")
    if FADE in body or bytes(b[body_start:body_start+1]) == b'\xEC':
        raise SystemExit("tag-10 already has a FadeFilter")
    out = bytearray(bytes(b[:body_start]) + FADE + bytes(b[body_start:]))
    growth = len(FADE)
    struct.pack_into('<H', out, 130, sz0 + growth)                 # entry0 size += 8
    for i in range(1, 10):                                          # relocate later entries
        slot = 128 + i*8
        if u16(out, slot+2) > 0:
            struct.pack_into('<H', out, slot, u16(out, slot) + growth)
    return bytes(out)

if __name__ == "__main__":
    from datetime import datetime
    LANGS = ["us", "uk", "fr", "gr", "it", "es", "jp"]
    HERE = os.path.dirname(os.path.abspath(__file__))
    MOD  = HERE + "/../mod/hut/eb/{}-EVT_HUT_EXT.eb.bytes"
    BKP  = HERE + "/../backups"
    GAME = ("C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX/FF9CustomMap/StreamingAssets/"
            "assets/resources/commonasset/eventengine/eventbinary/field/{}/EVT_HUT_EXT.eb.bytes")
    only = sys.argv[1] if len(sys.argv) > 1 else None
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    for L in LANGS:
        if only and L != only:
            continue
        src = open(GAME.format(L), 'rb').read()
        open(f"{BKP}/{L}-EVT_HUT_EXT.eb.bytes.preFade.{stamp}", 'wb').write(src)  # backup
        out = add_fade(src)
        open(GAME.format(L), 'wb').write(out)
        open(MOD.format(L), 'wb').write(out)
        print(f"{L}: EVT_HUT_EXT {len(src)} -> {len(out)} bytes (+{len(out)-len(src)})  tag-10 fade-in added")
    print("done" + (f" ({only} only)" if only else " (all 7 langs deployed to game + mod/hut/eb)"))
