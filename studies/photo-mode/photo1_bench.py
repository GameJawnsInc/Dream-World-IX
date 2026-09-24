"""PHOTO MODE, RUNG 1 -- the in-game proof of the KIT feature (field 30956, PHOTO1, bench/photo1.field.toml).

The field is authored ONLY through `[photo]`; the kit builds and arms the photo daemon. After deploy_field, this script
seats ONE study-local OBSERVER entry into every language's live .eb (the rung-0 pattern; the deploy's revert script
restores the field). The observer never moves the camera. Each tick it mirrors, into Global Int16s the harness reads:
the view (0xEA, copied at once), the player's screen point (0xA9), usercontrol, the camera index, the held keys, how
many ticks each d-pad direction was held, and the show bit of every object photo mode can hide. A dispatcher on
Global.Byte[CMD] plays what a foreign script would: EnableMove / DisableMove, the conductor's scene bit (MAP 110), and
the hide / show of balloon C through photo mode's own seated functions (a target already hidden when photo mode
opens).

The observer is armed right AFTER the photo daemon's InitCode in Main_Init, so every object it reads exists.

Usage (repo root):  py studies/photo-mode/photo1_bench.py probe | deploy
30956 is a NEW id -> the FIRST deploy needs a relaunch (a harness launch is one).
Revert: py tools/scroll_out/revert_deploy_30956.py
"""
from __future__ import annotations

import argparse
import struct
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "ff9mapkit"))

from ff9mapkit import build, eblint                                   # noqa: E402
from ff9mapkit.config import LANGS, ModLayout, find_game_path        # noqa: E402
from ff9mapkit.content import object as _object, photo               # noqa: E402
from ff9mapkit.eb import EbScript, disasm as D, edit as eb_edit, exprasm, opcodes  # noqa: E402
from ff9mapkit.eb.labelasm import JMP, JMP_IFNOT, asm, label         # noqa: E402
from ff9mapkit.fsutil import atomic_write_bytes                      # noqa: E402

FIELD_ID, FIELD_NAME, MOD_FOLDER = 30956, "PHOTO1", "FF9CustomMap"
BENCH_TOML = HERE / "bench" / "photo1.field.toml"
BALLOON = 226
# the observer's mirrors -- Global Int16 byte offsets (the safe band, clear of 2032-2047)
O16 = {"t": 1500, "vx": 1502, "vy": 1504, "psx": 1506, "psy": 1508, "uc": 1510, "cam": 1512, "keys": 1514,
       "flags": 1516, "ack": 1518, "last": 1520, "ackt": 1522, "nr": 1524, "nl": 1526, "nd": 1528, "nu": 1530}
WATCHED = tuple(O16)
CMD = 1560                                        # Global.Byte, harness-poked
CMDS = {"ENABLEMOVE": 1, "DISABLEMOVE": 2, "SCENE_ON": 5, "SCENE_OFF": 6, "PREHIDE_C": 7, "RESHOW_C": 8}
KEYS = (("select", 0x1, 1), ("cancel", 0x10000, 2), ("r1", 0x200000, 4), ("l1", 0x100000, 8),
        ("right", 0x20, 16), ("left", 0x80, 32), ("up", 0x10, 64), ("down", 0x40, 128))
FLAG_BIT = {"player": 1, "L": 2, "C": 4, "R": 8, "guard": 16, "talker": 32}


# ------------------------------------------------------------------- reading the built script
def balloons(eb: bytes) -> dict:
    """{"L": slot, "C": slot, "R": slot} -- the balloon props, told apart by x (the prop Init's loc Int16[0] := x)."""
    s = EbScript.from_bytes(eb)
    found = []
    for e in s.entries:
        if e.size <= 0 or not e.funcs:
            continue
        f0 = e.funcs[0]
        ins = list(D.iter_code(eb, f0.abs_start, f0.abs_end))
        if not any(i.op == 0x2F and struct.unpack_from("<H", eb, i.off + 2)[0] == BALLOON for i in ins):
            continue
        xs = [i for i in ins if i.op == 0x05 and eb[i.off + 1:i.off + 4] == b"\xd9\x00\x7d"]
        found.append((struct.unpack_from("<h", eb, xs[0].off + 4)[0], e.index))
    if len(found) != 3:
        raise SystemExit(f"expected three balloons, found {found}")
    xs = sorted(found)
    return {"L": xs[0][1], "C": xs[1][1], "R": xs[2][1]}


def seated(eb: bytes) -> dict:
    """{entry: (hide_tag, show_tag)} -- every entry carrying a photo hide/show pair (bodies == flag_function)."""
    s = EbScript.from_bytes(eb)
    pl = photo.player_entry(eb)
    out = {}
    for e in s.entries:
        if e.size <= 0:
            continue
        uid = 250 if e.index == pl else e.index
        tags = {}
        for f in e.funcs:
            body = eb[f.abs_start:f.abs_end]
            for show in (False, True):
                if body.startswith(photo.flag_function(uid, show)):
                    tags[show] = f.tag
        if tags:
            out[e.index] = (tags.get(False), tags.get(True))
    return out


def npc_entries(eb: bytes) -> dict:
    """{"guard": slot, "talker": slot}: the two NPCs -- the one with photo functions is the guard (it is a hide
    target), the other with a SetModel and a talk function (tag 3) is the talker."""
    s = EbScript.from_bytes(eb)
    pl, b, st = photo.player_entry(eb), balloons(eb), seated(eb)
    guard = [k for k in st if k not in (pl, *b.values())]
    talker = [e.index for e in s.entries if e.size > 0 and e.index not in (pl, *b.values(), *guard)
              and e.func_by_tag(3) is not None and e.func_by_tag(0) is not None
              and any(i.op == 0x2F for i in D.iter_code(eb, e.func_by_tag(0).abs_start, e.func_by_tag(0).abs_end))]
    if len(guard) != 1 or len(talker) != 1:
        raise SystemExit(f"expected one guard and one talker, found {guard} / {talker}")
    return {"guard": guard[0], "talker": talker[0]}


def parts(eb: bytes, raw: dict) -> list:
    """The photo parts in step order, read off the built bytes."""
    spec = photo.parse(raw)
    b, n, st, pl = balloons(eb), npc_entries(eb), seated(eb), photo.player_entry(eb)
    where = {"balloon-l": b["L"], "balloon-c": b["C"], "guard": n["guard"], "player": pl}
    out = []
    for t, step in enumerate(spec.steps):
        if step == "all":
            continue
        entry = where[step]
        ht, sht = st[entry]
        out.append(photo.Part(step=t, uid=250 if entry == pl else entry, entry=entry, hide_tag=ht, show_tag=sht))
    return out


def photo_slot(eb: bytes, raw: dict) -> int:
    """The ONE entry equal to the kit's photo.entry_bytes over the parts read back -- P-BYTES: the kit's daemon."""
    want = photo.entry_bytes(photo.parse(raw), parts(eb, raw), [bx.viewport for bx in photo.pan_boxes(raw)])
    s = EbScript.from_bytes(eb)
    hits = [e.index for e in s.entries if e.size > 0 and eb[e.abs_start:e.abs_end] == want]
    if len(hits) != 1:
        raise SystemExit(f"{len(hits)} entries equal photo.entry_bytes")
    return hits[0]


# ------------------------------------------------------------------- the observer
def _x(e: str) -> bytes:
    return exprasm.assemble(e + " B_EXPR_END")


def _stmt(text: str) -> bytes:
    return opcodes.encode(0x05, _x(text), arg_flags=0b1)


def g(name: str) -> str:
    return f"Global.Int16[{O16[name]}]"


def _k(m: int) -> str:
    return f"const({m})" if m <= 0x7FFF else f"const4({m})"


def observer_body(objs: dict, c_tags: tuple) -> bytes:
    """``objs`` = {flag name: uid}; ``c_tags`` = (hide, show) photo tags on balloon C."""
    cmd = f"Global.Byte[{CMD}]"
    keys = " ".join(f"{_k(m)} B_KEY const({bit}) B_MULT" + (" B_PLUS" if i else "") for i, (_n, m, bit) in enumerate(KEYS))
    flags = " ".join(f"obj(uid={objs[n]}).f[4] const(1) B_AND const({bit}) B_MULT" + (" B_PLUS" if i else "")
                     for i, (n, bit) in enumerate(FLAG_BIT.items()))
    B: list = [_stmt(f"{g(n)} const(0) B_LET") for n in O16] + [_stmt(f"{cmd} const(0) B_LET"), label("top"),
               _stmt(f"{g('t')} {g('t')} const(1) B_PLUS B_LET"),
               opcodes.encode(0xEA), _stmt(f"{g('vx')} B_SYSVAR[12] B_LET"), _stmt(f"{g('vy')} B_SYSVAR[13] B_LET"),
               opcodes.encode(0xA9, 250), _stmt(f"{g('psx')} B_SYSVAR[12] B_LET"),
               _stmt(f"{g('psy')} B_SYSVAR[13] B_LET"),
               _stmt(f"{g('uc')} B_SYSVAR[2] B_LET"), _stmt(f"{g('cam')} B_SYSVAR[1] B_LET"),
               _stmt(f"{g('keys')} {keys} B_LET"), _stmt(f"{g('flags')} {flags} B_LET")]
    for name, mask in (("nr", 0x20), ("nl", 0x80), ("nd", 0x40), ("nu", 0x10)):
        B.append(_stmt(f"{g(name)} {g(name)} {_k(mask)} B_KEY B_PLUS B_LET"))
    bodies = {1: [opcodes.encode(0x2E)], 2: [opcodes.encode(0x2D)],
              5: [_stmt(f"Map.Bit[{photo.SCENE_BIT}] const(1) B_LET")],
              6: [_stmt(f"Map.Bit[{photo.SCENE_BIT}] const(0) B_LET")],
              7: [opcodes.run_script_sync(photo.SYNC_LEVEL, objs["C"], c_tags[0])],
              8: [opcodes.run_script_sync(photo.SYNC_LEVEL, objs["C"], c_tags[1])]}
    B += [_stmt(f"{cmd} const(0) B_NE"), (JMP_IFNOT, "c_done")]
    for k, body in bodies.items():
        B += [_stmt(f"{cmd} const({k}) B_EQ"), (JMP_IFNOT, f"c_not{k}"), *body, (JMP, "c_ok"), label(f"c_not{k}")]
    B += [_stmt(f"{g('last')} const(0) {cmd} B_MINUS B_LET"), (JMP, "c_fin"),
          label("c_ok"), _stmt(f"{g('last')} {cmd} B_LET"),
          label("c_fin"), _stmt(f"{g('ack')} {g('ack')} const(1) B_PLUS B_LET"), _stmt(f"{g('ackt')} {g('t')} B_LET"),
          _stmt(f"{cmd} const(0) B_LET"),
          label("c_done"), opcodes.wait(1), (JMP, "top"), opcodes.RETURN]
    return asm(B)


def _objs(eb: bytes) -> dict:
    b, n = balloons(eb), npc_entries(eb)
    return {"player": 250, "L": b["L"], "C": b["C"], "R": b["R"], "guard": n["guard"], "talker": n["talker"]}


def patch_eb(eb0: bytes, raw: dict) -> tuple:
    """Seat + arm the observer right after the photo daemon's InitCode. Returns (bytes, observer slot, photo slot)."""
    pslot = photo_slot(eb0, raw)
    objs = _objs(eb0)
    c_tags = seated(eb0)[objs["C"]]
    baseline = {str(p) for p in eblint.lint_eb(eb0)}
    body = observer_body(objs, c_tags)
    out, oslot = _object.seat_entry(eb0, bytes([0x00, 0x01]) + struct.pack("<HH", 0, 4) + body)
    main = EbScript.from_bytes(out).entry(0).func_by_tag(0)
    ic = [i for i in D.iter_code(out, main.abs_start, main.abs_end) if i.op == 0x07 and out[i.off + 1] == pslot]
    if len(ic) != 1:
        raise SystemExit(f"expected one InitCode of the photo daemon, found {len(ic)}")
    out = eb_edit.insert_in_function(out, 0, 0, ic[0].end - main.abs_start, opcodes.init_code(oslot, 0))
    fresh = [p for p in eblint.lint_eb(out) if getattr(p, "severity", "error") == "error" and str(p) not in baseline]
    if fresh:
        raise SystemExit("patch produced NEW lint errors:\n  " + "\n  ".join(map(str, fresh)))
    return out, oslot, pslot


def is_patched(eb: bytes, raw: dict) -> bool:
    try:
        objs = _objs(eb)
        return observer_body(objs, seated(eb)[objs["C"]]) in eb
    except SystemExit:
        return False


def raw() -> dict:
    return build.FieldProject.load(BENCH_TOML).raw


# ------------------------------------------------------------------- verbs
def probe() -> None:
    import tempfile
    out = Path(tempfile.mkdtemp(prefix="photo1-"))
    r = subprocess.run([sys.executable, "-m", "ff9mapkit", "build", str(BENCH_TOML), "--out", str(out)],
                       cwd=REPO / "ff9mapkit", capture_output=True, text=True)
    print("\n".join(ln for ln in r.stderr.splitlines() + r.stdout.splitlines() if "[photo]" in ln))
    eb = next(out.rglob(f"EVT_{FIELD_NAME}.eb.bytes")).read_bytes()
    rr = raw()
    print("parts", parts(eb, rr))
    print("objects", _objs(eb), "photo slot", photo_slot(eb, rr))
    patched, oslot, pslot = patch_eb(eb, rr)
    print(f"observer at slot {oslot} ({len(patched) - len(eb)} bytes), photo daemon slot {pslot}; is_patched "
          f"{is_patched(patched, rr)}")


def deploy() -> None:
    r = subprocess.run([sys.executable, str(REPO / "tools" / "deploy_field.py"), str(BENCH_TOML),
                        "--id", str(FIELD_ID), "--name", FIELD_NAME, "--text-block", str(FIELD_ID),
                        "--mod-folder", MOD_FOLDER])
    if r.returncode != 0:
        raise SystemExit("deploy_field failed")
    live = ModLayout(find_game_path() / MOD_FOLDER)
    rr, n = raw(), 0
    for lang in LANGS:
        p = live.eb_path(lang, f"EVT_{FIELD_NAME}.eb.bytes")
        if p.exists():
            out, oslot, pslot = patch_eb(p.read_bytes(), rr)
            atomic_write_bytes(p, out)
            n += 1
    if not n:
        raise SystemExit(f"no live EVT_{FIELD_NAME}.eb.bytes found to patch")
    print(f"seated the observer in {n} language .eb file(s): observer slot {oslot}, photo daemon slot {pslot}")
    print(f"  Revert: py tools/scroll_out/revert_deploy_{FIELD_ID}.py")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("verb", choices=["probe", "deploy"])
    {"probe": probe, "deploy": deploy}[ap.parse_args().verb]()
