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
_T_ENTRANCE_OFF, _T_PRELOAD_OFF, _T_FIELD_OFF = 19, 26, 30   # set-D8:2 value, PreloadField + Field targets


def transition_for(target: int, dest_entrance: int = 0) -> bytes:
    """The proven fade+Field block, repatched to land on `target` at `dest_entrance` (set into D8:2)."""
    t = bytearray(_TRANSITION)
    assert struct.unpack_from("<H", t, _T_PRELOAD_OFF)[0] == 4000
    assert struct.unpack_from("<H", t, _T_FIELD_OFF)[0] == 4000
    struct.pack_into("<H", t, _T_ENTRANCE_OFF, dest_entrance)
    struct.pack_into("<H", t, _T_PRELOAD_OFF, target)
    struct.pack_into("<H", t, _T_FIELD_OFF, target)
    return bytes(t)


def warp_entry(target: int, dest_entrance: int = 0, gate_entrance: int | None = None) -> bytes:
    """A type-0 code entry that transitions to Field(target) at dest_entrance. If `gate_entrance` is
    given, it only fires when FieldEntrance == gate_entrance (the field-100 case, so non-New-Game
    arrivals are untouched); None = unconditional (the field-70 opening, only entered at New Game)."""
    trans = transition_for(target, dest_entrance)
    body = region.if_block(region.cond_eq(0xD8, 2, gate_entrance), trans) if gate_entrance is not None else trans
    return bytes([0x00, 0x01]) + struct.pack("<HH", 0, 4) + body + opcodes.RETURN


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


def inject(data: bytes, target: int, gate_entrance: int = NEWGAME_ENTRANCE):
    """field 100: warp to Field(target) at its entrance 0, ONLY when entered at gate_entrance (231 =
    New Game) so the hut-return (204) + normal arrivals stay normal. Activate at the executed
    RunSoundCode after the InitRegion cluster."""
    eb = EbScript.from_bytes(data)
    slot = eb.first_free_slot()
    out = edit.append_entry(data, slot, warp_entry(target, dest_entrance=0, gate_entrance=gate_entrance))
    off, length = _activation(EbScript.from_bytes(out))
    new = opcodes.init_code(slot, 0) + bytes(length - 3)   # InitCode(slot,0) (3B) + NOP pad to keep length
    out = edit.patch_bytes(out, off, new, expect=out[off:off + length])   # shift-free overwrite
    return out, slot, off


# --- stock path: field 70 (the stock New-Game opening) -> Field(100, 231) so field 100 sets up the
# party + runs its own ->4003 warp. NewGame() does NOT create the party, so we must route through a
# field that does (field 100). Field 70 is the opening, only entered at New Game -> unconditional. ---
F70_OVERRIDE = ("FF9CustomMap/StreamingAssets/assets/resources/commonasset/eventengine/"
                "eventbinary/field/{lang}/evt_alex1_ts_opening.eb.bytes")


def _activation_f70(eb: EbScript):
    """An executed, shift-free site EARLY in field 70's Main_Init (before the opening cinematic): the
    first RunSoundCode (the opening BGM, 0xC5), which runs before field 70's first jump. Returns
    (off, length). We warp immediately, so losing the opening BGM is moot."""
    f0 = eb.entry(0).func_by_tag(0)
    for ins in eb.instrs(f0):
        if ins.op == 0xC5:
            return ins.off, ins.length
    raise SystemExit("field 70 Main_Init has no RunSoundCode to anchor the activation on")


def inject_f70(data: bytes):
    """field 70 -> Field(100) entrance 231 (unconditional; field 70 is the opening, New-Game only)."""
    eb = EbScript.from_bytes(data)
    slot = eb.first_free_slot()
    out = edit.append_entry(data, slot, warp_entry(100, dest_entrance=NEWGAME_ENTRANCE))
    off, length = _activation_f70(EbScript.from_bytes(out))
    new = opcodes.init_code(slot, 0) + bytes(length - 3)
    out = edit.patch_bytes(out, off, new, expect=out[off:off + length])
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


def _patch(rel_template, fname, stamp, backups, inject_fn, label):
    """Back up + patch one override across all 7 languages with inject_fn(src) -> (out, slot, off)."""
    for L in LANGS:
        p = GAME / rel_template.format(lang=L)
        if not p.is_file():
            raise SystemExit(f"missing override: {p}\n(run from a build that has FF9CustomMap)")
        src = p.read_bytes()
        bkp = BKP / f"{L}-{fname}.prewarp.{stamp}"
        bkp.write_bytes(src)
        backups.append((str(p), str(bkp)))
        out, slot, off = inject_fn(src)
        p.write_bytes(out)
        print(f"  {label} {L}: {len(src)}->{len(out)} (+{len(out)-len(src)})  slot {slot}, InitCode@{off}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    stock = "--stock" in sys.argv
    target = int(args[0]) if args else 4003
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    _revert_prior()
    BKP.mkdir(exist_ok=True)
    backups = []
    # field 100 -> Field(target) at entrance 0, gated on the New-Game entrance 231 (always).
    _patch(OVERRIDE, "evt_alex1_at_street_a.eb.bytes", stamp, backups,
           lambda s: inject(s, target), "field100")
    if stock:
        # field 70 (stock New-Game opening) -> Field(100, 231); field 100 then sets up the party and
        # runs its ->target warp. Needed only when the engine is STOCK (New Game -> field 70).
        _patch(F70_OVERRIDE, "evt_alex1_ts_opening.eb.bytes", stamp, backups, inject_f70, "field70")
    rev = _write_revert(backups, stamp)
    chain = (f"New Game -> field 70 -> field 100 (entrance {NEWGAME_ENTRANCE}) -> field {target}"
             if stock else
             f"New Game (dev engine -> field 100, entrance {NEWGAME_ENTRANCE}) -> field {target}")
    print(f"\n{chain}")
    print(f"  NOTE: field {target} must be registered -- deploy to it first (e.g. py tools/deploy_field.py <toml>).")
    if not stock:
        print("  (dev-engine mode. For a STOCK + F6 engine, re-run with --stock to add the field-70 hop.)")
    print(f"  revert: py {rev.relative_to(HERE.parent).as_posix()}")


if __name__ == "__main__":
    main()
