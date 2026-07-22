"""Emit TransportControls.csv -- the rung-0 physics probe for the custom-vehicle study.

Stock Memoria (WorldConfiguration.PatchWorldCHRControl, runs on EVERY world scene load)
replaces ff9.w_moveCHRControl wholesale from the highest-priority mod folder's
StreamingAssets/Data/World/TransportControls.csv (>=12 rows required, more legal).
The stock table lives in ff9's STATIC constructor (once per process), so the CSV wins
and hot-applies on a ~-menu overworld reload.

This file = the 12 stock rows byte-faithful, with ONE change: row 10 ("???", the cut
all-terrain vehicle) gets type 3 -> 0. Type 3 has no arm in w_movementBasicOperation
(cases 0/1/2 = human/plane/ship only), so stock row 10 accepts NO input at all --
in-game confirmed 2026-07-22 (rows 10/11 forced via the s48 ~ menu: 10 = frozen solid,
11 = turns but speed 0). Type 0 routes it through w_movementHumanOperation: on-foot
handling at speed 140 with the row's all-terrain traversal mask (limit = 0xFFFFFFFF x2).

NOTE the CSV must carry type_cam explicitly (0,1,1,1,1,1,4,2,3,3,0,0): the stock
initializers leave it 0 and the FixTypeCam block (also static-ctor) patches it once --
a CSV-replaced table never re-runs that block.

Deploy: py transport_controls.py --deploy   (writes into FF9CustomMap-world)
Revert: delete the deployed file (stock table returns at the next world load).
"""
import argparse
import pathlib

GAME = pathlib.Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
DEPLOY = GAME / "FF9CustomMap-world" / "StreamingAssets" / "Data" / "World" / "TransportControls.csv"
HERE = pathlib.Path(__file__).parent

# type;flg_gake;speed_move;speed_rotation;speed_updown;speed_roll;speed_rollback;
# flg_fly;flg_upcam;fetchdist;music;se;encount;radius;camrot;type_cam;pad2;limit0;limit1
# Transcribed from ff9.cs static ctor (pinned 6b8bb2d5, lines 1467-1768). Booleans as 1/0.
ROWS = [
    # name, type, gake, move, rot, updown, roll, rollback, fly, upcam, fetch, music, se, enc, radius, camrot, cam, limit0, limit1
    ("Walking",              0, 0, 112, 64,   0,   0, 0, 0, 1, 2, 0,  0, 1,   0, 1, 0, 0x0010667F, 0xD8FF3CFF),
    ("Yellow Chocobo",       0, 0, 200, 64,   0,   0, 0, 0, 1, 2, 1,  0, 0, 300, 1, 1, 0x0010667F, 0xD8FF3CFF),
    ("Light Blue Chocobo",   0, 1, 200, 64,   0,   0, 0, 0, 1, 2, 1,  0, 0, 300, 1, 1, 0x20F8667F, 0xD8FF3CFF),
    ("Red Chocobo",          0, 1, 200, 64,   0,   0, 0, 0, 1, 2, 1,  0, 0, 300, 1, 1, 0x20FE667F, 0xD8FF3CFF),
    ("Deep Blue Chocobo",    0, 1, 200, 64,   0,   0, 0, 0, 1, 2, 1,  0, 0, 300, 1, 1, 0x23FF667F, 0xD8FF3CFF),
    ("Gold Chocobo ground",  0, 1, 200, 64,   0,   0, 0, 0, 1, 2, 1,  0, 0, 300, 1, 1, 0x23FF667F, 0xD8FF3CFF),
    ("Gold Chocobo air",     1, 0, 300, 30, 128,  64, 0, 1, 0, 3, 1,  0, 0, 400, 0, 4, 0x7FFF667F, 0xD8FF3CFF),
    ("Blue Narciss",         2, 0, 240, 36,   0,   0, 0, 0, 1, 3, 0, 24, 0, 560, 0, 2, 0x02600000, 0x00000000),
    ("Hilda Garde III",      1, 0, 500, 13, 255, 127, 0, 1, 0, 4, 2, 23, 0, 640, 0, 3, 0x7FFF667F, 0xD8FF3CFF),
    ("Invincible",           1, 0, 500, 13, 255, 127, 0, 1, 0, 4, 2, 22, 0, 720, 0, 3, 0x7FFF667F, 0xD8FF3CFF),
    # THE ONE CHANGE: type 3 -> 0 (the probe). Everything else = stock row 10.
    ("Probe all-terrain",    0, 0, 140, 32, 255,   0, 0, 0, 1, 3, 0,  0, 0, 480, 0, 0, 0xFFFFFFFF, 0xFFFFFFFF),
    ("Unused empty",         0, 0,   0,  0,   0,   0, 0, 0, 0, 0, 0,  0, 0,   0, 0, 0, 0x00000000, 0x00000000),
]

HEADER = """\
# Dream World IX -- custom-vehicle study, rung-0 probe (studies/custom-vehicle/).
# Stock w_moveCHRControl rows 0-11 byte-faithful EXCEPT row 10: type 3 -> 0
# (type 3 has no input handler; type 0 = the on-foot handler drives the all-terrain row).
# ----------------------------------------------------------------------------------------------------------------------------------
# type;flg_gake;speed_move;speed_rotation;speed_updown;speed_roll;speed_rollback;flg_fly;flg_upcam;fetchdist;music;se;encount;radius;camrot;type_cam;pad2;limit0;limit1;
# Byte;Byte;Int16;Byte;Byte;SByte;SByte;Boolean;Boolean;Byte;Byte;Byte;Boolean;Int16;Boolean;Byte;UInt16;UInt32;UInt32;
# ----------------------------------------------------------------------------------------------------------------------------------
"""


def emit() -> str:
    lines = [HEADER]
    for name, typ, gake, move, rot, updown, roll, rollback, fly, upcam, fetch, music, se, enc, radius, camrot, cam, l0, l1 in ROWS:
        vals = [typ, gake, move, rot, updown, roll, rollback, fly, upcam, fetch,
                music, se, enc, radius, camrot, cam, 0, l0, l1]
        lines.append(";".join(str(v) for v in vals) + ";# " + name + "\n")
    return "".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deploy", action="store_true", help="write into FF9CustomMap-world")
    args = ap.parse_args()
    csv = emit()
    local = HERE / "TransportControls.csv"
    local.write_text(csv, encoding="utf-8", newline="\n")
    print(f"wrote {local}")
    if args.deploy:
        DEPLOY.parent.mkdir(parents=True, exist_ok=True)
        existed = DEPLOY.exists()
        DEPLOY.write_text(csv, encoding="utf-8", newline="\n")
        print(f"deployed {DEPLOY} ({'REPLACED existing' if existed else 'new file'})")
        print("revert = delete that file; stock table returns at the next world load")


if __name__ == "__main__":
    main()
