"""Scene ladder rung 0: the DECORATIVE STATIC lane, proven in-game -- the ferry ship at anchor.

The lane under proof: WORLD-SCRIPTED-OBJECT-LANE-2026-07-25.md (byte-grounded, never deployed).
Its two laws, exercised verbatim here:
  * THE INDEX RULE  -- SetObjectIndex(0): fully inert (cache==10 skips all ground/shadow logic,
    authored Y kept verbatim, no vehicle-singleton hijack, shareable). Never 1-10.
  * THE ANIMATION RULE -- a real registered clip running: SetStandAnimation(<donor idle>) in
    tag 0 AND a per-frame RunAnimation(<same>) tag-1 loop (stock WORLD11 entry 11's exact
    shape). This install runs Memoria.ini WorldFPS=-1 -> the s49 smoother is LIVE; an
    anim-less static NREs every frame and silently kills the whole world script tick.

The demonstrator: the Lantern Ferry finally gets a visible vessel -- STOCK model 313 with its
stock idle 5106 (the exact WORLD11-entry-11 pairing; no mint, no 3DModel line, NO RELAUNCH),
moored at anchor off the Lantern Quay's west shore. Shore transect (deployed block (0,18),
engine ground query offline): sea until x<=32, land y=3.0 from x>=36 at z=-1168; the quay
trigger is (48,-1168), the berth arrival (60,-1168).

WORLD11 additions (dispatcher 9011 -- the ring's world state):
  entry 16 (new)  -- the ship: tag 0 = the study's minimal decorative Init (index 0, flags 1
                     show-only: no collision, no talk -- and no tag 2/3, so EventCollision
                     never selects it), tag 1 = the stock RunAnimation loop.
  entry 0 tag 0   -- Main_Init gains InitObject(16, 0) before the final RET (the boat/9009
                     pattern; lands AFTER the player anchor's InitObject(14) -- arming order).

Deploy: py rung0_quay_ship.py --deploy     (per-language into FF9CustomMap-world; hot --
        world re-entry reloads the dispatcher; no registration change)
Iterate: --pos X,Z  --y FP  --face BYTE    (re-run with --deploy replaces the bodies in place)
Revert: restore the printed backups from backups/scene-ladder/.
Bench:  enter the ring world (9011), stand at the quay / berth arrival, look west.
"""
import argparse
import pathlib
import shutil
import struct
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ff9mapkit"))

from ff9mapkit import config                                          # noqa: E402
from ff9mapkit.world.entrance import load_all_dispatchers, _WORLD_EB_SUBDIR   # noqa: E402
from ff9mapkit.eb.model import EbScript                               # noqa: E402
from ff9mapkit.eb import edit as E                                    # noqa: E402
from ff9mapkit.eb.cmdasm import assemble_block, disassemble_block     # noqa: E402

MOD_FOLDER = "FF9CustomMap-world"
NAME = "evt_world_world11"
FNAME = "EVT_WORLD_WORLD11.eb.bytes"
LANGS = ("us", "uk", "jp", "es", "fr", "gr", "it")

SHIP_UID = 16                        # first free WORLD11 slot (live-probed: 16-22 free, all langs)
MODEL_ID = 313                       # stock GEO_SUB_W0_021 -- the WORLD11-e11 ship; no mint, no relaunch
ANIM_ID = 5106                       # its stock idle -- the e11 pairing (THE ANIMATION RULE)
STOCK_DECOR_SLOT = 11                # stock WORLD11 entry 11 -- the etype oracle for a decorative

SHIP_POS = (18, -1168)               # ~18u off the Lantern Quay shore (sea until x<=32 at this z)
SHIP_Y = 200                         # fixed-point sea-level Y (the crimson boat's proven seed value)
SHIP_FACE = 192                      # byte units 0=S 64=W 128=N 192=E -- bow toward the quay


def fp(v: int) -> int:
    """World units -> x256 fixed-point as the unsigned const4 literal the .eb dialect wants."""
    return (v * 256) & 0xFFFFFFFF


def ship_init(pos, y_fp, face) -> str:
    return f"""
SetObjectIndex(0)
SetModel({MODEL_ID}, 100)
SetObjectFlags(1)
SetObjectSize({SHIP_UID}, 100, 100, 100)
SetStandAnimation({ANIM_ID})
SetWalkAnimation({ANIM_ID})
op_35({ANIM_ID})
MoveInstantXZY({{const4({fp(pos[0])}) B_EXPR_END}}, {{const({y_fp}) B_EXPR_END}}, {{const4({fp(pos[1])}) B_EXPR_END}})
TurnInstant({{const({face}) B_EXPR_END}})
RET()
"""


SHIP_LOOP = f"""
L0:
SetAnimationFlags(1, 1)
SetAnimationInOut(0, 0)
RunAnimation({ANIM_ID})
op_22(1)
JMP(L0)
"""


def build_entry(etype: int, funcs) -> bytes:
    """[etype, fc] + (tag u16, fpos u16)* + code; fpos from entryStart+2; 4-byte padded."""
    fc = len(funcs)
    table, code, fpos = b"", b"", fc * 4
    for tag, body in funcs:
        table += struct.pack("<HH", tag, fpos)
        code += body
        fpos += len(body)
    out = bytes([etype, fc]) + table + code
    if len(out) % 4:
        out += bytes(4 - len(out) % 4)
    return out


def asm(text: str) -> bytes:
    body = assemble_block(text)
    disassemble_block(body, 0, len(body))       # round-trip sanity
    return body


def patch_one(base: bytes, init_text: str) -> bytes:
    s = EbScript(base)
    e11 = s.entry(STOCK_DECOR_SLOT)
    etype = s.data[e11.abs_start]
    if etype != 2:
        raise SystemExit(f"stock decorative entry {STOCK_DECOR_SLOT} etype={etype} (wanted 2) -- refusing")

    init, loop = asm(init_text), asm(SHIP_LOOP)
    out = base
    have = None
    try:
        have = s.entry(SHIP_UID)
    except Exception:
        pass
    if have is None or not have.funcs:
        out = E.append_entry(out, SHIP_UID, build_entry(etype, [(0, init), (1, loop)]))
    else:                                        # re-run: replace in place
        out = E.replace_function_body(out, SHIP_UID, 0, init)
        out = E.replace_function_body(out, SHIP_UID, 1, loop)

    # Main_Init: InitObject(16, 0) before the final RET (after the anchor's InitObject(14))
    s3 = EbScript(out)
    f0 = next(f for f in s3.entry(0).funcs if f.tag == 0)
    text = disassemble_block(s3.data, f0.abs_start, f0.abs_end)
    if assemble_block(text) != s3.data[f0.abs_start:f0.abs_end]:
        raise SystemExit("Main_Init does not round-trip text<->bytes -- refusing to rebuild it")
    if f"InitObject({SHIP_UID}, 0)" not in text:
        lines = text.rstrip().splitlines()
        if lines[-1].strip() != "RET()":
            raise SystemExit(f"Main_Init does not end in RET() (got {lines[-1]!r}) -- refusing")
        lines.insert(len(lines) - 1, f"InitObject({SHIP_UID}, 0)")
        out = E.replace_function_body(out, 0, 0, assemble_block("\n".join(lines) + "\n"))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deploy", action="store_true")
    ap.add_argument("--pos", default=None, help="X,Z world units (default 18,-1168)")
    ap.add_argument("--y", type=int, default=SHIP_Y, help="fixed-point Y (default 200)")
    ap.add_argument("--face", type=int, default=SHIP_FACE, help="facing byte (default 192=E)")
    args = ap.parse_args()
    pos = tuple(int(v) for v in args.pos.split(",")) if args.pos else SHIP_POS
    init_text = ship_init(pos, args.y, args.face)

    alld = load_all_dispatchers()[NAME]
    game_path = config.find_game_path(None)
    eb_root = game_path / MOD_FOLDER / _WORLD_EB_SUBDIR
    bkdir = ROOT / "backups" / "scene-ladder"
    ts = time.strftime("%Y%m%d-%H%M%S")

    # phase 1: patch EVERY language in memory (a JP-layout surprise aborts before any write)
    patched = {}
    for lang in LANGS:
        mod_p = eb_root / lang / FNAME
        base = mod_p.read_bytes() if mod_p.is_file() else alld.get(lang, alld["us"])
        out = patch_one(base, init_text)
        patched[lang] = (mod_p, out)
        if lang == "us":
            s = EbScript(out)
            e = s.entry(SHIP_UID)
            print(f"[us] entry {SHIP_UID}: funcs {[f.tag for f in e.funcs]}, "
                  f"{len(out) - len(base):+} bytes vs base; ship at {pos} yfp={args.y} face={args.face}")
    if not args.deploy:
        print("dry run OK (all 7 languages patched in memory) -- re-run with --deploy to write")
        return
    for lang in LANGS:
        mod_p, out = patched[lang]
        if mod_p.is_file():
            bkdir.mkdir(parents=True, exist_ok=True)
            bk = bkdir / f"{FNAME}.{lang}.{ts}"
            shutil.copy2(mod_p, bk)
            print(f"  backed up {mod_p} -> {bk}")
        mod_p.parent.mkdir(parents=True, exist_ok=True)
        mod_p.write_bytes(out)
        print(f"  wrote {mod_p} ({len(out)} B)")


if __name__ == "__main__":
    main()
