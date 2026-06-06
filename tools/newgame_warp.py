#!/usr/bin/env python3
"""PURE-MOD instant New-Game warp: jump straight into a custom field (default 4003), no engine edit.

The dev engine starts New Game in Alexandria/Main Street (field 100) at entrance 231. This patches the
FF9CustomMap override of field 100 so that WHEN it is entered at entrance 231 (i.e. New Game) it
immediately fades out and Field()s to the target -- entirely in mod files, no engine rebuild. The warp
is GATED on entrance 231, so every other field-100 arrival (e.g. the hut return at entrance 204, or a
normal Alexandria visit) is untouched.

How: append a tiny code entry  `if (FieldEntrance == 231) { <proven fade+Field transition> }`  and
activate it by overwriting a Main_Init Wait (shift-free) right after the field's InitRegion cluster --
the same safe injection wire_alexandria.py uses for the door. The transition block is lifted verbatim
from the field-70 opening override (DisableMove; DisableMenu; FadeFilter; Wait(25); set entrance=0;
PreloadField; Field), which is proven to warp cleanly; only its target id is repatched.

Reversible: backs up the 7-language override + writes tools/scroll_out/revert_newgame_warp.py.

Usage:  py tools/newgame_warp.py [field_id]            (default 4003)
NOTE: the target must be REGISTERED (e.g. deploy something to 4003 first with deploy_field.py), or the
      warp lands on an unregistered field = black screen.
"""
from __future__ import annotations

import datetime
import os
import struct
import sys
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit.eb import EbScript, edit, opcodes      # noqa: E402
from ff9mapkit.content import region                  # noqa: E402

GAME = Path("C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX")
OVERRIDE = ("FF9CustomMap/StreamingAssets/assets/resources/commonasset/eventengine/"
            "eventbinary/field/{lang}/evt_alex1_at_street_a.eb.bytes")
LANGS = ["us", "uk", "fr", "gr", "it", "es", "jp"]
HERE = Path(__file__).resolve().parent
BKP = HERE.parent / "backups"
NEWGAME_ENTRANCE = 231          # the value EventEngine.NewGame() sets for field 100 (dev engine)

# Proven fade+Field transition from the field-70 opening override (target id = 4000 here, repatched
# below): DisableMove; DisableMenu; FadeFilter(6,24,{D5:17},255,255,255); Wait(25); set D8:2=0;
# PreloadField(5,4000); Field(4000). Field 100's Main_Init sets D5:17 early, so the fade arg resolves.
_TRANSITION = bytes.fromhex("2dabec040618d5117fffffff22001905d8027d00002c7ffd0005a00f2b00a00f")
_T_PRELOAD_OFF, _T_FIELD_OFF = 26, 30      # the two 4000 targets inside _TRANSITION


def transition_for(target: int) -> bytes:
    t = bytearray(_TRANSITION)
    assert struct.unpack_from("<H", t, _T_PRELOAD_OFF)[0] == 4000
    assert struct.unpack_from("<H", t, _T_FIELD_OFF)[0] == 4000
    struct.pack_into("<H", t, _T_PRELOAD_OFF, target)
    struct.pack_into("<H", t, _T_FIELD_OFF, target)
    return bytes(t)


def warp_entry(target: int, entrance: int) -> bytes:
    """A type-0 code entry: `if (FieldEntrance == entrance) { transition to Field(target) }; return`."""
    gate = region.cond_eq(0xD8, 2, entrance)           # D8:02 == FieldEntrance (gEventGlobal[2..3])
    body = region.if_block(gate, transition_for(target)) + opcodes.RETURN
    return bytes([0x00, 0x01]) + struct.pack("<HH", 0, 4) + body


def _activation(eb: EbScript):
    """A shift-free, EXECUTED overwrite site in Main_Init: the first RunSoundCode (0xC5) right AFTER
    the InitRegion cluster. That cluster is where the door's InitRegion lives (proven executed in-game)
    and it runs BEFORE the unconditional jump (op 0x01) that skips the trailing Wait -- so a Wait after
    the cluster is DEAD CODE (the first attempt overwrote one and never fired). The resume-variant
    RunSoundCode here is redundant (the field BGM song_play that follows is untouched). Returns
    (off, length)."""
    f0 = eb.entry(0).func_by_tag(0)
    last_reg = None
    for ins in eb.instrs(f0):
        if ins.op == 0x08:                             # InitRegion -- find the last of the cluster
            last_reg = ins.end
    if last_reg is None:
        raise SystemExit("field 100 Main_Init has no InitRegion cluster to anchor the activation on")
    for ins in eb.instrs(f0):
        if ins.op == 0xC5 and ins.off >= last_reg:     # RunSoundCode after the cluster = executed
            return ins.off, ins.length
    raise SystemExit("no RunSoundCode after the InitRegion cluster to overwrite")


def inject(data: bytes, target: int, entrance: int = NEWGAME_ENTRANCE):
    eb = EbScript.from_bytes(data)
    slot = eb.first_free_slot()
    out = edit.append_entry(data, slot, warp_entry(target, entrance))
    off, length = _activation(EbScript.from_bytes(out))
    new = opcodes.init_code(slot, 0) + bytes(length - 3)   # InitCode(slot,0) (3B) + NOP pad to keep length
    out = edit.patch_bytes(out, off, new, expect=out[off:off + length])   # shift-free overwrite
    return out, slot, off


def _write_revert(backups, stamp):
    out = HERE / "scroll_out"
    out.mkdir(exist_ok=True)
    lines = ['"""Revert the New-Game instant warp: restore the field-100 override backups."""',
             "import shutil", "PAIRS = ["]
    for live, bkp in backups:
        lines.append(f"    ({live!r}, {bkp!r}),")
    lines += ["]", "for live, bkp in PAIRS:", "    shutil.copyfile(bkp, live)",
              "    print('restored', live)", f"print('reverted newgame_warp {stamp}')", ""]
    p = out / "revert_newgame_warp.py"
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


def _revert_prior():
    """Restore the override to its pre-warp state if a prior warp is installed (so re-running is
    idempotent -- it never stacks two warp entries)."""
    rev = HERE / "scroll_out" / "revert_newgame_warp.py"
    if rev.is_file():
        import runpy
        runpy.run_path(str(rev), run_name="__main__")


def main():
    target = int(sys.argv[1]) if len(sys.argv) > 1 else 4003
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    _revert_prior()
    BKP.mkdir(exist_ok=True)
    backups = []
    for L in LANGS:
        p = GAME / OVERRIDE.format(lang=L)
        if not p.is_file():
            raise SystemExit(f"missing field-100 override: {p}\n(run from a build that has FF9CustomMap)")
        src = p.read_bytes()
        bkp = BKP / f"{L}-evt_alex1_at_street_a.eb.bytes.prewarp.{stamp}"
        bkp.write_bytes(src)
        backups.append((str(p), str(bkp)))
        out, slot, off = inject(src, target)
        p.write_bytes(out)
        print(f"{L}: {len(src)}->{len(out)} (+{len(out)-len(src)})  slot {slot}, InitCode@{off}  "
              f"-> New Game (entrance {NEWGAME_ENTRANCE}) warps to Field({target})")
    rev = _write_revert(backups, stamp)
    print(f"\nNew Game now jumps straight to field {target} (gated on entrance {NEWGAME_ENTRANCE}).")
    print(f"  NOTE: field {target} must be registered -- deploy to it first (e.g. py tools/deploy_field.py <toml>).")
    print(f"  revert: py {rev.relative_to(HERE.parent).as_posix()}")


if __name__ == "__main__":
    main()
