"""Author a complete custom OVERWORLD ENTRANCE end-to-end -- the one-shot fold of the whole proven flow
(model -> place -> seat -> trigger) into a single call.

An overworld entrance is NOT just an event tile: walking onto a tile whose IDALL event bits are set fires
``ff9.WorldEvent(cellX, cellZ, id)``, which packs a **cell tag** ``0x8000 | (cellZ<<8 & 0x3F00) | (cellX<<2 & 0xFC) | (id&3)`` and
``GetIP``-matches it against **object-0** (entry 0)'s function tags in the loaded world dispatcher ``.eb``. The
matched function sets ``Map.Byte[39] = <case>`` and ``RunScriptAsync(6, 1, 11)`` -> the shared entry-1/tag-1
dispatcher, whose base-2 AREA switch reads that case and emits ``Field(dest)`` (with the proper vehicle / scenario
gating + fade). So a working entrance is THREE things wired together, each of which this module authors:

  1. **the trigger function** -- clone WORLD00's proven Ice-Cavern entrance func (:data:`TEMPLATE_TAG` ``0x9895``,
     29 bytes), patch its single ``Byte[39]=<case>`` literal to the destination case, retag it to the new cell,
     and add it (via :func:`ff9mapkit.eb.edit.add_function`) to EVERY dispatcher whose AREA switch carries that
     case -- deployed to all 7 language folders (the bytecode is language-identical). There are 13 dispatchers
     (``EVT_WORLD_WORLD00..12``) selected by entry/story state, so an entrance authored into only one is dead in
     every other state -- this covers them all.
  2. **the event tile(s)** -- set the terrain tiles in the cell to ``event=<id>`` (+ a cosmetic ``area=<case>``
     stamp; the area bits are NOT read by dispatch) as a loose Terrain ``.ff9mesh`` override, so walking there
     fires ``WorldEvent`` with the matching tag.
  3. **(optional) the building** -- a Blender-modelled OBJ placed + seated in the cell as the Object mesh (the
     visible structure you walk up to), via :func:`ff9mapkit.world.blendio.build_from_obj`.

Everything is a loose override / mod-folder ``.eb`` -- reversible by deleting the printed files (or re-deploying
the journey). Needs the s34 ``WorldMeshOverride`` engine patch for the mesh overrides; the ``.eb`` funcs run on
stock Memoria. In-game proven 2026-07-01 (cell 35,25 -> forked Ice Cavern); this module generalises that spike.
"""
from __future__ import annotations

import glob
import re
import shutil
from pathlib import Path

from .. import config
from . import extract as W, mesh as M

LANGS = ("us", "uk", "jp", "es", "fr", "gr", "it")
TEMPLATE_TAG = 0x9895            # WORLD00 object-0's Ice-Cavern (case 4) entrance func -- the proven clone donor
_BYTE39_PAT = b"\xD5\x27\x7D"    # opD5(39) op7D ... : the Map.Byte[39]=<case> assignment; the case lo byte follows 7D
_WORLD_EB_SUBDIR = "StreamingAssets/assets/resources/commonasset/eventengine/eventbinary/world"
_AREA_SWITCH_BASE = 2
CELL_SIZE = 32                   # a world CELL is 32u (two cells per 64u block per axis)


# --------------------------------------------------------------------------- cell <-> tag <-> block geometry

def pack_cell_tag(cell_x: int, cell_z: int, event: int = 1) -> int:
    """The object-0 function tag that ``ff9.WorldEvent`` GetIP-matches for a walk onto cell ``(cell_x, cell_z)``
    whose event bits == ``event``: ``0x8000 | (cell_z<<8 & 0x3F00) | (cell_x<<2 & 0xFC) | (event&3)``.

    ``cell_z`` is a 6-bit field like ``cell_x`` (the engine masks with 0x3F00, aliasing z modulo 64) -- a tag
    packed with z >= 64 could never match a WorldEvent request, so out-of-range z raises rather than aliases.
    (The 24x20-block map only reaches cell_z 39 anyway.)"""
    if not 0 <= cell_x <= 0x3F:
        raise ValueError(f"cell_x {cell_x} out of range 0..63 (6 bits)")
    if not 0 <= cell_z <= 0x3F:
        raise ValueError(f"cell_z {cell_z} out of range 0..63 (6 bits -- the engine masks z with 0x3F00)")
    if not 1 <= event <= 3:
        raise ValueError(f"event {event} out of range 1..3 (0 = not an entrance tile)")
    return 0x8000 | ((cell_z & 0x3F) << 8) | ((cell_x & 0x3F) << 2) | (event & 3)


def unpack_cell_tag(tag: int):
    """``(cell_x, cell_z, event)`` for an object-0 entrance tag, or ``None`` if ``tag`` is not a cell tag
    (top bit unset -- an ordinary object function; or bit 14 set, which WorldEvent's formula never emits)."""
    if not tag & 0x8000 or tag & 0x4000:
        return None
    return ((tag >> 2) & 0x3F, (tag >> 8) & 0x3F, tag & 3)


def cell_to_block(cell_x: int, cell_z: int) -> tuple:
    """The terrain block ``(x, y)`` that contains cell ``(cell_x, cell_z)`` (32u cells, 64u blocks -> ``//2``)."""
    return (cell_x * CELL_SIZE // W.BLOCK_SIZE, cell_z * CELL_SIZE // W.BLOCK_SIZE)


def cell_world_center(cell_x: int, cell_z: int) -> tuple:
    """The world ``(x, z)`` centre of cell ``(cell_x, cell_z)`` -- ``z`` is negated (``w_worldPos2Cell`` inverse).
    Matches the debug-menu World-tab cell readout / :func:`ff9mapkit.world.extract.block_world_origin` frame."""
    return (cell_x * CELL_SIZE + CELL_SIZE // 2, -(cell_z * CELL_SIZE + CELL_SIZE // 2))


# --------------------------------------------------------------------------- world dispatchers (the .eb layer)

_WORLD_RE = re.compile(r"eventbinary/world/([a-z]{2})/(evt_world_world\d+)\.eb")


def load_all_dispatchers(game=None) -> dict:
    """``{name: {lang: bytes}}`` for every pristine ``EVT_WORLD_WORLDxx`` in EVERY language, from p0data (p0data7).

    ⚠ The world dispatchers are NOT fully language-identical: JP carries localized inline event dialogue in the
    dispatcher entries and a DIFFERENT byte layout (its ``WORLD00`` is 16 B shorter than US), while uk/es/fr/gr/it
    are code-identical to US (differ only in the header/name region). So an edit MUST patch each language's OWN copy
    -- cloning the US bytecode into ``jp/`` would overwrite the Japanese dialogue. (uk/es/fr/gr/it are safe, but we
    patch them per-lang too, uniformly.)"""
    from ..extract import _unitypy
    _unitypy()
    import UnityPy
    sa = config.find_game_path(game) / "StreamingAssets"
    out: dict = {}
    for p in sorted(glob.glob(str(sa / "p0data*.bin")),
                    key=lambda q: (0 if "p0data7." in Path(q).name else 1, q)):
        try:
            env = UnityPy.load(p)
        except Exception:                                # noqa: BLE001 -- odd/non-bundle file, keep scanning
            continue
        for o in env.objects:
            if o.type.name != "TextAsset":
                continue
            m = _WORLD_RE.search((getattr(o, "container", None) or "").lower())
            if not m:
                continue
            lang, name = m.group(1), m.group(2)
            s = o.read().m_Script
            out.setdefault(name, {})[lang] = s.encode("utf-8", "surrogateescape") if isinstance(s, str) else bytes(s)
        if out:
            break
    if not out:
        raise ValueError("no EVT_WORLD_WORLDxx dispatchers found in StreamingAssets/p0data*.bin "
                         "-- is this a full FF9 install?")
    return out


def load_world_dispatchers(game=None) -> dict:
    """``{name: us_bytes}`` -- the US view of :func:`load_all_dispatchers` (the entrance-func template + the case
    coverage are language-independent, so US is the reference). The per-language deploy uses ``load_all_dispatchers``."""
    return {name: langs["us"] for name, langs in load_all_dispatchers(game).items() if "us" in langs}


def dispatcher_cases(dispatcher_bytes: bytes):
    """The set of base-2 AREA-switch case values in a dispatcher's entry-1/tag-1 function, or ``None`` if it has no
    such switch (a tiny cutscene-state dispatcher). A destination case is only reachable in dispatchers that carry it."""
    from ..eb.model import EbScript
    from ..eb import disasm as D
    s = EbScript(dispatcher_bytes)
    try:
        f1 = next(f for f in s.entry(1).funcs if f.tag == 1)
    except StopIteration:
        return None
    for i in D.iter_code(s.data, f1.abs_start, f1.abs_end):
        if i.is_switch:
            si = D.decode_switch(i) or i.switch()
            if si and si.base == _AREA_SWITCH_BASE:
                return {ed.value for ed in si.edges if not ed.is_default}
    return None


# --------------------------------------------------------------------------- the trigger function body

def byte39_value(body: bytes):
    """Read the ``Map.Byte[39] = <case>`` literal an entrance-function body assigns (via disasm), or ``None``."""
    from ..eb import disasm as D
    for i in D.iter_code(body, 0, len(body)):
        if i.op == 0x05 and i.args:
            m = re.search(r"opD5\(39\)\s+op7D\((\d+),(\d+)\)", str(i.args[0]))
            if m:
                return int(m.group(1)) + int(m.group(2)) * 256
    return None


def patch_byte39(body: bytes, case: int) -> bytes:
    """Return ``body`` with its ``Map.Byte[39] = <case>`` destination literal rewritten to ``case``. The literal is
    the ``op7D`` immediate right after the unique ``opD5(39)`` (bytes ``D5 27 7D <lo> <hi>``); ``case`` (a switch
    case, 0-63) fits the low byte. Raises if the assignment is missing or not unique (a wrong template)."""
    if not 0 <= case <= 0xFFFF:
        raise ValueError(f"case {case} out of range 0..65535")
    b = bytearray(body)
    idx = b.find(_BYTE39_PAT)
    if idx < 0 or b.find(_BYTE39_PAT, idx + 1) != -1:
        raise ValueError("entrance-func template: the Map.Byte[39] literal (D5 27 7D) is missing or not unique")
    b[idx + 3] = case & 0xFF
    b[idx + 4] = (case >> 8) & 0xFF
    out = bytes(b)
    got = byte39_value(out)
    if got != case:
        raise ValueError(f"patched Byte[39] reads back as {got}, expected {case}")
    return out


def zone_in_body() -> bytes:
    """The real world->field ZONE-IN choreography, composed byte-identical to WORLD00's
    main service loop (entry-1/tag-1, the shared run between "a destination is pending"
    and its AREA switch -- whose case bodies then do the bare ``Field(dest)``):

    ``DisableMove; DisableMenu; CloseWindow(6); CloseWindow(7); RunWorldCode(32,75);
    RunWorldCode(41,0); FadeFilter(2,24,white); Wait(25); D8:2 = 9999; <ready poll>``

    - the FADE (SUB toward white == the screen fading to BLACK over 24 frames) is the
      transition black every arrival mechanic assumes ("fade BEFORE Field()") -- it hides
      the destination's smooth-cam settle and gives ``entry_settle`` its black to extend;
    - ``D8:2 = 9999`` is the real worldmap-arrival ENTRANCE sentinel, so the destination's
      ``[[player.arrival]]`` dispatch sees the same "came from the world map" value real
      fields see instead of a STALE last-gateway entrance;
    - the two ``RunWorldCode`` ops (PSX music fade / leftover) are stubbed no-ops on
      Memoria, carried for donor fidelity; the ready poll spins on ``B_SYSVAR(200)``
      (``ff9.w_frameGetParameter(200)`` -- constant 0 on Memoria, exits at once).

    Byte-asserted against the real dispatcher run in ``test_worldexit``."""
    from ..content import region as R
    from ..eb import opcodes as O
    return (O.DISABLE_MOVE                            # 2D -- the real run locks control first
            + bytes([0xAB])                           # DisableMenu
            + bytes([0x21, 0x00, 0x06])               # CloseWindow(6) -- dispatcher dialog cleanup
            + bytes([0x21, 0x00, 0x07])               # CloseWindow(7)
            + bytes([0xC4, 0x00, 0x20, 0x4B, 0x00])   # RunWorldCode(32, 75) -- PSX music fade (Memoria stub)
            + bytes([0xC4, 0x00, 0x29, 0x00, 0x00])   # RunWorldCode(41, 0)  -- PSX leftover (Memoria no-op)
            + O.fade_filter(2, 24, 0, 255, 255, 255)  # fade OUT: screen - white -> black, 24 frames
            + O.wait(25)
            + R.set_field_entrance(9999)              # the worldmap-arrival entrance sentinel
            + bytes([0x01, 0x03, 0x00])               # JMP +3 (enter the poll at its check)
            + O.wait(1)
            + bytes([0x05, 0x7A, 0xC8, 0x7F])         # EXPR: push B_SYSVAR(200) ("transition busy")
            + bytes([0x03, 0xF6, 0xFF]))              # JMP_IF -10 (loop while busy)


# The faithful CONFIRM-GATE, copied byte-exact from the real dispatcher main-loop entrance gate
# (WORLD00 entry-1/tag-1 @261): a real town's fade->warp block only runs when the Confirm button is
# held. Real overworld town/dungeon entry is NOT walk-on auto-warp -- you stand on the tile and press
# Confirm to enter (verified in-engine 2026-07-13; the earlier "walk-on" reading was WRONG -- the RPN
# operator 0x4F is B_KEYON, a controller read, not a field opcode).
FICON_EXCLAM = bytes([0x68, 0x00, 0x01])   # Bubble(IconType.Exclamation=1) -- raise the "!" over the player
# EXPR{ push EventInput.Confirm (0x20000, op7E 4-byte LE), B_KEYON (0x4F) } -> 1 if Confirm held, else 0.
# Byte-identical to the Confirm test inside the real main-loop gate (op7E(0,0,2,0) op4F).
CONFIRM_PRESSED = bytes([0x05, 0x7E, 0x00, 0x00, 0x02, 0x00, 0x4F, 0x7F])

# The native overworld ENTRANCE HUD (location nameplate + "Enter with [X]") CANNOT be self-painted from our own
# trigger: the dispatcher's IDLE loop (entry-0/tag-1, an every-frame loop) does CloseWindow(6);CloseWindow(7)
# whenever ``Byte[24] <= 100`` (verified WORLD09 @0-@17). Self-painting windows 6/7 while Byte[24] stays 100 means
# the idle loop closes them the same frame we open them -> the open command SPAMS (in-game 2026-07-13). The native
# nameplate avoids this because func-0xB raises ``Byte[24] > 100``, so the idle loop's close is skipped. So we HAVE
# to summon the native machinery -- BUT the 3 blackscreens taught us Byte[24] is ALSO the var our own trigger's
# template gate checks (``Byte[24]==100``): once func-0xB raises it, the main loop knocks it to 1, our gate fails,
# our warp never runs, and the native confirm path fades-to-black then hits the no-Field switch default. THE FIX:
# summon the native HUD (Byte[39]=1 + RunScriptAsync(6,1,11) -> func-0xB, spam-free) on the APPROACH frames, and
# gate our OWN trigger on ON-FOOT ONLY (drop the Byte[24]==100 term) so our Confirm->zone_in->Field(6500) still
# fires no matter what value the native machinery has left in Byte[24]. On Confirm the native path routes case 1
# (Byte[24]-100) to its benign switch default (no Field); OUR gate-independent warp does the real Field(6500).
NAMEPLATE_CASE = 1     # Byte[39] handed to func-0xB; =1 is UNMAPPED in every AREA switch (2-60 are real entrances)
                       # so the native confirm hits the no-op switch default (our own warp owns the real transition).
                       # func-0xB sets Byte[24]=101 -> the main loop shows the nameplate (name = location id 1 =
                       # "Alexandria Harbor") + "Enter with [X]", and keeps Byte[24]>100 so the idle loop won't close.
ONFOOT_GATE = bytes([0x05, 0xD4, 0xBE, 0x0E, 0x7F])   # EXPR{ !var190 } == "on foot" -- the template gate's on-foot
                       # term WITHOUT its Byte[24]==100 term, so our trigger stays armed while the nameplate is up.


def nameplate_summon(case: int = NAMEPLATE_CASE) -> bytes:
    """Summon the native entrance HUD via the real dispatcher handshake: ``Byte[39] = case`` +
    ``RunScriptAsync(6, 1, 11)`` -> func-0xB sets Byte[38]/Byte[24]=case+100, so the main loop shows the nameplate +
    "Enter with [X]" and (crucially) keeps ``Byte[24] > 100`` so the idle loop does NOT close the windows -- the
    ONLY spam-free way to show them (self-paint fights the idle-loop close). ``RunScriptAsync(6,1,11)`` is
    byte-verbatim from the trigger template. Runs on the approach frames only; our own Confirm gate does the warp.

    ``case`` defaults to :data:`NAMEPLATE_CASE` (=1, the "Alexandria Harbor" name-locked slot). A VIRGIN-band
    case (61-64, see :func:`author_entrance`) shows a CUSTOM name instead: func-0xB's 49+ range arm has no upper
    bound (``Byte[38] = w98 >> (case-49)``, byte-verified), and the plate window indexes block-68 split[case],
    which the kit ships extended."""
    from ..eb import opcodes as O
    c = int(case)
    return (bytes([0x05, 0xD5, 0x27, 0x7D, c & 0xFF, (c >> 8) & 0xFF, 0x2C, 0x7F])
            + O.run_script_async(6, 1, 11))


def entrance_func_body_direct(field_id: int, *, world_state=None, prompt=False, nameplate=False,
                              nameplate_case: int = None, explored_case: int = None, game=None,
                              dispatchers=None) -> bytes:
    """The DIRECT trigger body for a CUSTOM destination field: the proven template's
    vehicle/state GATE verbatim (its leading expression + conditional skip), then the
    real :func:`zone_in_body` choreography (fade-to-black + control lock + the D8:2
    arrival sentinel), an optional ``GLOB[WORLD_STATE_VAR] = <world_state>`` record,
    and ``Field(field_id)`` in place of the ``Byte[39]=case + RunScriptAsync``
    dispatcher handshake -- whose AREA switch only carries real base-game fields.

    The real handshake reaches that same choreography in the dispatcher's MAIN loop
    (the shared run before its AREA switch); the direct body bypasses the loop, so it
    must carry the run itself -- without it the custom destination loaded IN THE CLEAR
    (no fade-out), so you watched the smooth-cam settle that the black normally hides
    (in-game report, 2026-07-13: the waystation entrance showed the stuck camera).

    ``prompt=True`` makes it a FAITHFUL "!" ACTION-PROMPT entrance (the way real towns work,
    NOT walk-on auto-warp): the trigger -- which WorldEvent re-fires every frame the player
    stands on the tile -- raises the ``FICON`` "!" bubble and only warps when the Confirm
    button is held (``B_KEYON(Confirm)``, the exact gate real dispatchers use). Without it the
    warp fires the instant you step on the tile (auto-warp; fine for a scripted/cutscene entrance).

    ``nameplate=True`` (requires ``prompt``) additionally summons the NATIVE overworld entrance HUD --
    the location nameplate + the "Enter with [X]" dialog -- via :func:`nameplate_summon` on the approach
    frames, and gates the whole trigger on ON-FOOT ONLY (:data:`ONFOOT_GATE`) instead of the template's
    ``Byte[24]==100``, so our Confirm warp still fires while func-0xB holds ``Byte[24] > 100`` for the HUD
    (that Byte[24] coupling is what blackscreened 3x -- see :func:`nameplate_summon`).

    ``world_state`` (the wldMapNo of the dispatcher copy this body is deployed into --
    each dispatcher knows which world it is) records the CURRENT world state so the
    destination field's ``[[gateway]] to="worldmap" arrive=`` exit can return to it
    (``content.worldexit.WORLD_STATE_VAR``).

    Template shape (byte-asserted): ``[12B gate expr][JZ +13][8B Byte39=case]
    [5B RunScriptAsync][RETURN]`` -> auto:  ``[12B gate][JZ +skip][zone-in][rec?][Field][RETURN]``;
    prompt: ``[12B gate][JZ ->RET][FICON][B_KEYON(Confirm)][JZ ->RET][zone-in][rec?][Field][RETURN]``."""
    import struct
    if not 0 <= int(field_id) <= 0x7FFF:
        raise ValueError(f"field id {field_id} out of the engine's Int16 range")
    if nameplate and not prompt:
        raise ValueError("nameplate=True requires prompt=True (the native HUD rides the confirm-gated entrance)")
    if dispatchers is None:
        dispatchers = load_world_dispatchers(game)
    from ..eb.model import EbScript
    w00 = EbScript(dispatchers["evt_world_world00"])
    f = next((f for e in w00.entries for f in e.funcs if f.tag == TEMPLATE_TAG), None)
    if f is None:
        raise ValueError("WORLD00 has no trigger template func")
    tpl = w00.data[f.abs_start:f.abs_end]
    if len(tpl) != 29 or tpl[0] != 0x05 or tpl[12:15] != b"\x02\x0d\x00" \
            or tpl[15:18] != b"\x05\xd5\x27" or tpl[28] != 0x04:
        raise ValueError("unexpected trigger template shape -- the direct body's surgery "
                         "offsets no longer match WORLD00's 0x9895 func")
    fid = int(field_id)
    rec = b""
    if world_state is not None:
        from ..content import region as R
        from ..content.worldexit import WORLD_STATE_VAR
        rec = R.set_var(0xD8, WORLD_STATE_VAR, int(world_state))
    warp_core = zone_in_body() + rec + bytes([0x2B, 0x00, fid & 0xFF, (fid >> 8) & 0xFF])
    if not prompt:                                    # auto-warp: [gate][JZ over warp -> RET][warp][RET]
        return tpl[:12] + bytes([0x02]) + struct.pack("<h", len(warp_core)) + warp_core + b"\x04"
    if not nameplate:
        # confirm-gated "!": show the bubble every frame on the tile, warp only on a Confirm press. Keeps the
        # template's full Byte[24]==100 && on-foot gate (no HUD summon, so Byte[24] stays at the idle 100).
        confirm_gate = CONFIRM_PRESSED + bytes([0x02]) + struct.pack("<h", len(warp_core))   # JZ over warp -> RET
        after_vehicle = FICON_EXCLAM + confirm_gate + warp_core
        return (tpl[:12] + bytes([0x02]) + struct.pack("<h", len(after_vehicle)) + after_vehicle + b"\x04")
    # nameplate: summon the native HUD (spam-free -- see nameplate_summon) on the APPROACH frames, warp on Confirm.
    # The gate is ON-FOOT ONLY (not the template's Byte[24]==100), because func-0xB raises Byte[24] off 100 to show
    # the HUD; keeping the Byte[24]==100 gate would disarm our warp (that was the 3x blackscreen). Structure:
    #   [on-foot? -JZ-> RET] [Confirm? -JZ-> APPROACH] WARP(Byte[24]=100 + zone-in + Field) RET ; APPROACH(summon + "!") RET.
    # The WARP-branch-only Byte[24]=100 write fails the native main loop's own confirm gate (@200 needs Byte[24] in
    # [1,90]; func-0xB had left it there), so on the Confirm frame OUR fade is the only one -- no cosmetic double
    # fade-to-black regardless of which object the engine processes first. It runs ONLY on Confirm (never on the
    # approach frames), so it does not disturb the nameplate summon (which needs Byte[24]>100).
    #
    # ``nameplate_case`` (61-64, the VIRGIN band) swaps the summoned case so the plate shows a CUSTOM name from the
    # kit-extended block-68 table, and ``explored_case`` adds the explored-bit set to the WARP branch (the surgery
    # handler's own proven expr) so the plate faithfully upgrades "?" -> the name after first entry. The "!" bubble
    # is dropped in that mode for parity with the surgery-form entrances (the plate + "Enter with [X]" are the cue).
    settle = bytes([0x05, 0xD5, 0x18, 0x7D, 100, 0x00, 0x2C, 0x7F])   # Byte[24] = 100 -> suppress the native confirm
    explored = explored_set_expr(int(explored_case)) if explored_case is not None else b""
    warp_branch = settle + explored + warp_core + b"\x04"          # confirm held: single-fade guard, warp, return
    # APPROACH branch: gate the SUMMON on Byte[24]==100. func-0xB needs a clean Byte[24]==100 on entry (it was
    # the whole trigger gate in the version that DID show "Alexandria Harbor"); firing it every frame with a dirty
    # Byte[24] (already 101/1 from the prior summon) broke its slot setup so the main loop never showed the plate.
    # Byte[24] cycles back to 100 each time the idle loop reclaims it, so the summon re-fires and the HUD persists.
    summon = nameplate_summon(nameplate_case if nameplate_case is not None else NAMEPLATE_CASE)
    ficon = b"" if nameplate_case is not None else FICON_EXCLAM
    eq100 = bytes([0x05, 0xD5, 0x18, 0x7D, 100, 0x00, 0x20, 0x7F])    # EXPR: Byte[24] == 100
    approach = (eq100 + bytes([0x02]) + struct.pack("<h", len(summon))   # Byte[24]!=100 -> skip summon
                + summon + ficon)
    after_gate = (CONFIRM_PRESSED + bytes([0x02]) + struct.pack("<h", len(warp_branch))   # !Confirm -> APPROACH
                  + warp_branch + approach)
    return (ONFOOT_GATE + bytes([0x02]) + struct.pack("<h", len(after_gate)) + after_gate + b"\x04")


def entrance_func_body(case: int, *, game=None, dispatchers=None) -> bytes:
    """The trigger-function body for a destination ``case``: WORLD00's :data:`TEMPLATE_TAG` body, patched so it sets
    ``Map.Byte[39] = case``. Portable across dispatchers (references only globals + RunScriptAsync)."""
    from ..eb.model import EbScript
    disp = dispatchers if dispatchers is not None else load_world_dispatchers(game)
    w00 = EbScript(disp["evt_world_world00"])
    f = w00.entry(0).func_by_tag(TEMPLATE_TAG)
    if f is None:
        raise ValueError(f"WORLD00 has no template entrance func 0x{TEMPLATE_TAG:04X}")
    return patch_byte39(w00.data[f.abs_start:f.abs_end], case)


# --------------------------------------------------------------------------- the NAMEPLATE-SURGERY handler
# The AREA-switch case that carries our CUSTOM-name nameplate: a HIGH dead case (its arm == the switch default
# in every free-roam dispatcher, so repointing it breaks no real entrance) whose name index + explored bit are
# BOTH usable. 53 is the cleanest -- name index 53 -> world text block-68 split[53] (a "  ???  " placeholder we
# rename), explored bit -> gEventGlobal[98] bit 4 == navi marker locId 52 (a coord-less placeholder, so setting
# it reveals NO stray dot). See the PIN notes for why 53 beats 55 (locId 54 = a live "Chocobo's Air Garden").
NAMEPLATE_SURGERY_CASE = 53

# The name the nameplate renders == world text block 68 (mesID 68, shared by every EVT_WORLD_WORLDxx) txid-0,
# split by newline, indexed by the case value (main loop @3712 SetTextVariable(0, Byte[24]); Byte[24]=case). The
# kit's marker-rename tool writes that exact slot -- registering the name is `navimap` locId = case-1 (split
# index (case-1)+1 == case). Verified: split[1] == "Alexandria Harbor" == case 1's nameplate (PIN case_evidence).


def explored_word_bit(case: int) -> tuple:
    """The ``(gEventGlobal word, bit)`` whose set state makes case ``case``'s nameplate show its NAME (not "?").

    func-0xB (entry-1/tag-11) computes ``Byte[38] = (gEventGlobal[word] >> (case - lo)) & 1`` PER 16-case range
    (byte-verified WORLD09 @6333/@6365/@6397/@6418): 1-16 -> word 92 bit (case-1); 17-32 -> word 94 bit (case-17);
    33-48 -> word 96 bit (case-33); 49-64 -> word 98 bit (case-49). The main loop shows the NAME variant only when
    ``Byte[38] != 0``. This word/bit is ALSO the navi-marker discovery bit for locId ``case-1``
    (``navimap.marker_bit(case-1) == word*8 + bit``), so the two are one and the same save flag."""
    for lo, word in ((1, 92), (17, 94), (33, 96), (49, 98)):
        if lo <= case <= lo + 15:
            return word, case - lo
    raise ValueError(f"case {case} out of the nameplate range 1..64 (no explored bit)")


def explored_set_expr(case: int) -> bytes:
    """The expression that SETS case ``case``'s explored bit -- ``gEventGlobal[word] |= (1 << bit)`` as an explicit
    read-OR-write: ``05 <DC word> <DC word> 7D <1<<bit:i16> 26 2C 7F`` (opDC = getVarOperation(Global,UInt16), a
    valid lvalue that func-0xB reads with the same token; 0x26 = B_OR, 0x2C = B_LET). Byte-identical to the PIN's
    proven form (case 53 -> ``05 dc 62 dc 62 7d 10 00 26 2c 7f``)."""
    from ..content import region as R
    word, bit = explored_word_bit(case)
    v = 1 << bit
    return (bytes([0x05]) + R._push_var(R.GLOB_UINT16, word) + R._push_var(R.GLOB_UINT16, word)
            + bytes([0x7D, v & 0xFF, (v >> 8) & 0xFF, 0x26, 0x2C, 0x7F]))


def nameplate_handler(field_id: int, case: int = NAMEPLATE_SURGERY_CASE) -> bytes:
    """The repointed AREA-switch arm for a CUSTOM-name nameplate entrance: set case ``case``'s explored bit (so its
    name shows on the NEXT approach) then ``Field(field_id)`` -- the bare warp the shared zone-in prologue (which
    ran in the main loop before the switch: control lock + fade-to-black + the D8:2=9999 arrival sentinel) hands to.
    ``Field`` (0x2B) is a flow terminator, so no RETURN follows (matching every real switch case body)."""
    if not 0 <= int(field_id) <= 0x7FFF:
        raise ValueError(f"field id {field_id} out of the engine's Int16 range")
    fid = int(field_id)
    return explored_set_expr(case) + bytes([0x2B, 0x00, fid & 0xFF, (fid >> 8) & 0xFF])


def _repoint_dead_case(base_l: bytes, case: int, handler: bytes) -> bytes:
    """Repoint dispatcher entry-1/tag-1's DEAD AREA-switch ``case`` to ``handler`` in ``base_l`` -- IDEMPOTENTLY.
    Returns the input unchanged if the case already routes to this exact handler (a re-deploy); repoints if the
    case is dead (arm == the switch default); raises if the case is mapped to a DIFFERENT (real) handler. Applied
    per-language, since the switch (base 2, 59 cases) is present in every free-roam dispatcher in every language."""
    from ..eb import edit as E
    from ..eb.model import EbScript
    eb = EbScript.from_bytes(base_l)
    _f, ins, si = E.find_switch(eb, 1, 1, switch_base=_AREA_SWITCH_BASE)
    default_target = next(e.target for e in si.edges if e.is_default)
    edge = next((e for e in si.edges if e.value == case), None)
    if edge is None:
        raise ValueError(f"dispatcher AREA switch has no case {case}")
    if edge.target == default_target:                        # dead -> append handler + repoint
        out, _ = E.repoint_switch_case(base_l, 1, 1, case, handler, switch_base=_AREA_SWITCH_BASE)
        return out
    if base_l[edge.target:edge.target + len(handler)] == handler:
        return base_l                                        # already ours (idempotent re-deploy)
    raise ValueError(f"dispatcher case {case} is already mapped (target {edge.target}) to a different handler "
                     f"-- pick another nameplate_case (a DEAD high case)")


# --------------------------------------------------------------------------- destination resolution

def resolve_destination(*, field=None, case=None, game=None) -> dict:
    """Resolve the destination to a base-2 AREA-switch ``case`` (== the ``Byte[39]`` value) + its default field.

    ``case`` given -> validate it exists in WORLD00's switch, report its field. ``field`` given -> invert the
    dispatch table (prefer a case whose ``default`` branch leads there). Returns ``{case, field, note}``."""
    from .locate import case_to_fields
    a2f = case_to_fields(game=game)
    if case is not None and field is not None:
        raise ValueError("give a destination as EITHER field=<id> OR case=<n>, not both")
    if case is not None:
        if case not in a2f:
            raise ValueError(f"case {case} is not a live overworld dispatch case (see `world-locate`)")
        default = next((f for c, f in a2f[case] if c == "default"), None)
        return {"case": case, "field": default, "note": f"case {case} -> {a2f[case]}"}
    if field is not None:
        cands = [(c, cond) for c, branches in a2f.items() for cond, f in branches if f == field]
        if not cands:
            reachable = sorted({f for br in a2f.values() for _, f in br if f is not None})
            raise ValueError(f"no overworld dispatch case leads to field {field}. Reachable base fields: "
                             f"{reachable}. (Fork/journey redirects happen at the engine level -- author the "
                             f"entrance to the BASE field and let field_remap/s28 send it to your fork.)")
        default_cases = [c for c, cond in cands if cond == "default"]
        chosen = (sorted(default_cases) or sorted(c for c, _ in cands))[0]
        note = f"field {field} <- case {chosen}"
        if len(set(c for c, _ in cands)) > 1:
            note += f" (ambiguous; also cases {sorted(set(c for c, _ in cands))} -- picked {chosen})"
        return {"case": chosen, "field": field, "note": note}
    raise ValueError("give a destination: field=<id> or case=<n>")


# --------------------------------------------------------------------------- stacked block reads (compose edits)

def read_block_stacked(mod_folder: str, x: int, y: int, *, disc: int = 1, lod: str = "0_1", part: str = "terrain",
                       game=None, missing_ok: bool = False, fresh: bool = False):
    """Read block ``(x, y)``'s ``part`` mesh, preferring an already-deployed mod-folder ``.ff9mesh`` OVERRIDE (so a
    new edit stacks on a prior one) and falling back to the pristine p0data block. ``fresh=True`` IGNORES the override
    and reads pristine -- for re-iterating a block cleanly (GEOMETRY edits like a flatten pad / a kept building would
    otherwise COMPOUND on re-run). ``missing_ok`` returns ``None`` when neither exists (a block with no stock mesh)."""
    if not fresh:
        dest = config.find_game_path(game) / mod_folder / M.override_relpath(disc, x, y, lod, part.capitalize())
        if dest.is_file():
            return M.blockmesh_from_ff9mesh(dest, disc=disc, x=x, y=y, lod=lod, part=part)
    try:
        return W.read_block(x, y, disc=disc, lod=lod, part=part, game=game)
    except (ValueError, FileNotFoundError):
        if missing_ok:
            return None
        raise


# --------------------------------------------------------------------------- the one-shot author

def _timestamp() -> str:
    import time
    return time.strftime("%Y%m%d-%H%M%S")


# on-foot walkable topographs, decoded from Memoria's on-foot control limit {0x0010667F, 0xD8FF3CFF} (ff9.cs:1487):
# w_movementCheckTopographID tests bit `topo` of the 64-bit mask (check[0]=topo 32-63, check[1]=topo 0-31).
_WALK_TOPO = frozenset(t for t in range(64)
                       if (((0x0010667F >> (t - 32)) & 1) if t >= 32 else ((0xD8FF3CFF >> t) & 1)))


def _cell_openness_note(ter, cwx, cwz, ox, oz, summary, stock_obj=None):
    """Warn if the entrance cell is a POOR spot: much BLOCKED terrain (topo not on-foot-walkable = river/cliff) or an
    existing building/town collision beside it -- both pinch a trap-pocket around a placed structure (the cell-(35,25)
    soft-lock: 34% topo-49 river + Dali town adjacent). A good entrance cell is open walkable land."""
    from .extract import decode_id
    walk = blocked = 0
    for tri in ter.tris:
        cx = (ter.verts[tri[0]][0] + ter.verts[tri[1]][0] + ter.verts[tri[2]][0]) / 3.0 + ox
        cz = (ter.verts[tri[0]][2] + ter.verts[tri[1]][2] + ter.verts[tri[2]][2]) / 3.0 + oz
        if abs(cx - cwx) <= 16 and abs(cz - cwz) <= 16:
            if decode_id(int(round(ter.tangents[tri[0]][0])))["topograph"] in _WALK_TOPO:
                walk += 1
            else:
                blocked += 1
    total = walk + blocked
    if total and blocked / total > 0.20:
        summary.setdefault("notes", []).append(
            f"POOR SPOT: the entrance cell is {100 * blocked / total:.0f}% BLOCKED terrain (topo not on-foot-"
            f"walkable -- river/cliff); the player may get trapped. Prefer an open, all-walkable cell.")
    if stock_obj is not None:
        near = 0
        for tri in stock_obj.tris:
            if decode_id(int(round(stock_obj.tangents[tri[0]][0])))["topograph"] == 59:
                cx = (stock_obj.verts[tri[0]][0] + stock_obj.verts[tri[1]][0] + stock_obj.verts[tri[2]][0]) / 3.0 + ox
                cz = (stock_obj.verts[tri[0]][2] + stock_obj.verts[tri[1]][2] + stock_obj.verts[tri[2]][2]) / 3.0 + oz
                if abs(cx - cwx) <= 22 and abs(cz - cwz) <= 22:
                    near += 1
        if near:
            summary.setdefault("notes", []).append(
                f"POOR SPOT: an existing town/building ({near} collision tiles) is beside this cell -- placing a "
                f"structure here can pinch a trap-pocket against it. Prefer an open cell away from towns.")


def _building_world_box(building, default_at, margin: float = 2.0):
    """The world-XZ bounding box ``(xmin, xmax, zmin, zmax)`` a building occupies once placed (its XZ centroid at its
    ``at`` / ``default_at``), padded by ``margin``. Entrance-trigger tiles are kept OUT of this box so the player never
    triggers from UNDER the impassable structure (which would box them in -- the soft-lock the castle caused)."""
    from . import blendio as BIO
    ov = BIO.read_obj(building["obj"])["V"]
    if not ov:
        return None
    at = tuple(building["at"]) if building.get("at") else default_at
    xs = [v[0] for v in ov]; zs = [v[2] for v in ov]
    bcx = (min(xs) + max(xs)) / 2.0; bcz = (min(zs) + max(zs)) / 2.0   # bbox centre (matches build_from_obj's anchor)
    return (at[0] + (min(xs) - bcx) - margin, at[0] + (max(xs) - bcx) + margin,
            at[1] + (min(zs) - bcz) - margin, at[1] + (max(zs) - bcz) + margin)


def _building_world_hull(building, default_at):
    """The building's XZ CONVEX HULL in WORLD coords (its centroid placed at ``at``/``default_at``) -- the tight
    outline of the structure, so the footprint block matches the VISIBLE castle instead of a padded bounding box
    (which leaves an invisible collision skirt beyond the towers). Returns a list of ``(x, z)`` or ``None``."""
    from . import blendio as BIO, mesh as M
    ov = BIO.read_obj(building["obj"])["V"]
    if not ov:
        return None
    at = tuple(building["at"]) if building.get("at") else default_at
    xs = [v[0] for v in ov]; zs = [v[2] for v in ov]
    bcx = (min(xs) + max(xs)) / 2.0; bcz = (min(zs) + max(zs)) / 2.0   # bbox centre (matches build_from_obj's anchor)
    hull = M._convex_hull_xz([(v[0], v[2]) for v in ov])
    return [(at[0] + (hx - bcx), at[1] + (hz - bcz)) for (hx, hz) in hull] or None


def _capped_flatten_radius(requested: float, building, summary: dict) -> float:
    """Cap a ``--flatten-pad`` radius to the building's XZ footprint so the flattened (step-prone) ground stays UNDER
    the impassable structure. A flatten pad WIDER than the building leaves flat ground meeting the bumpy natural
    terrain out in the WALKABLE approach -- an edge step you can walk down into but (the overworld only raycasts DOWN)
    can't climb back out of = stuck. With ``radius == footprint`` the smoothstep falloff reaches natural terrain
    exactly at the building perimeter, so nothing walkable has a step. Records a note when it caps / when there's no
    building to hide the pad."""
    if not building:
        summary.setdefault("notes", []).append(
            "flatten-pad with no --building reshapes WALKABLE ground -- its edge is a step you can get stuck on; "
            "prefer seating the structure (no flatten) or add a building to cover the pad")
        return requested
    from . import blendio as BIO
    ov = BIO.read_obj(building["obj"])["V"]
    if not ov:
        return requested
    # The building seats with its XZ CENTROID at the pad centre; the pad must stay under it on EVERY side, so the
    # safe radius is the INSCRIBED circle from the centroid to the footprint's bounding box (min extent), NOT the max
    # corner distance -- an asymmetric structure (wide in X, shallow in Z) would otherwise leave the pad poking past
    # its narrow sides into walkable ground (the stuck-step).
    xs = [v[0] for v in ov]; zs = [v[2] for v in ov]
    bcx = sum(xs) / len(xs); bcz = sum(zs) / len(zs)
    foot_r = min(bcx - min(xs), max(xs) - bcx, bcz - min(zs), max(zs) - bcz)
    if requested > foot_r:
        summary.setdefault("notes", []).append(
            f"flatten-pad {requested:.0f} capped to the building's inscribed footprint {foot_r:.1f} -- a wider flat "
            f"pad pokes past the structure into walkable ground, leaving an edge-step you get stuck on. (Seating "
            f"alone usually suffices; the building skirt hides a small float.)")
        return foot_r
    return requested


def author_entrance(*, cell, mod_folder: str, field=None, case=None, direct_field=None,
                    event: int = 1, disc: int = 1, lod: str = "0_1",
                    trigger_at=None, trigger_radius: float = 14.0, set_tile_area: bool = True,
                    building=None, flatten_pad=None, block_footprint: bool = True, fresh: bool = False,
                    trigger_only: bool = False, prompt: bool = False, nameplate: bool = False,
                    nameplate_name: str = None, nameplate_case: int = NAMEPLATE_SURGERY_CASE,
                    backup_dir=None, dry_run: bool = False, game=None,
                    skip_mirror: bool = False) -> dict:
    """Author + deploy a complete overworld entrance at ``cell=(cell_x, cell_z)`` into ``mod_folder``.

    Destination: ``field=<id>`` (resolved to a dispatch case) or ``case=<n>`` (raw). ``event`` is the tile trigger
    id (1-3). ``trigger_at``/``trigger_radius`` place the event-tile cluster (default: the cell centre, r=14, kept
    inside the 32u cell). ``building`` (a dict ``{obj, at?, seat?, keep_block?, topograph?, idall?, texture?, tile?,
    tile_uv?}``) additionally models + seats a structure in the cell; the texture keys forward to
    :func:`ff9mapkit.world.blendio.build_from_obj` (stamp real atlas tiles / one picked tile / a custom UV rect
    onto UV-less faces -- seated against the STACKED terrain, so it works on a transplanted cell too). ``block_footprint`` (default True) makes the TERRAIN under the building impassable
    (topo 59) so the player stops at its edge and can't wander into a hollow model's interior and get boxed -- the
    terrain conforms to the ground, so it blocks reliably where a flat prop base would bury/float on uneven land.
    Uses :func:`ff9mapkit.world.mesh.split_retarget_by_polygon` (EXACT -- splits a straddling terrain triangle at
    the hull boundary) rather than a whole-triangle centroid test, so the blocked edge traces the building's real
    footprint bit-exactly regardless of how coarse the underlying donor terrain's own triangulation is.
    ⚠ **THE RENDER-ONLY LAW IS CONDITIONAL -- ``idall`` is how you honour it on a donor-backed cell.** The building
    layer's rule is "the Object mesh RENDERS, the terrain hull COLLIDES; never feed a 3D model to the walkmesh, or its
    back-face-culled walls + buried base become invisible collision". That holds automatically only on a **BARE**
    block, where ``WMWorld.RegisterBareObjectOverride`` creates the Object component with ``AddForm1Transform`` and
    NO ``AddWalkMeshForm1``. If the block's prefab ALREADY has an Object component -- a real town block, or a
    RECLAIMED cell whose ``Donor.txt`` names a donor that has one -- the override instead takes
    ``RegisterBlockComponent(..., form1: true)``, which DOES call ``AddWalkMeshForm1`` (WMWorld.cs:775-814), and it is
    registered BEFORE ``TerrainForm1``, so it also wins the first-mesh ground query. There, pass
    ``idall=4078`` (``0x0FEE``): ``WMPhysics.Raycast`` skips 4078/4088/2040 outright, so the model is genuinely
    render-only and cannot shadow an event tile, while footprint collision still comes from the topo-59 terrain hull.

    ``flatten_pad=radius`` optionally flattens a pad under the building. ``fresh`` re-reads the block from pristine
    p0data (ignoring a prior deployed override) so re-doing a block doesn't COMPOUND. ``trigger_only`` refreshes
    JUST the dispatcher trigger functions (step 1) and leaves the deployed terrain/tiles/building untouched -- the
    re-deploy mode for picking up a kit upgrade to the trigger body (a full re-run without the original
    ``--building`` would re-stamp event tiles WITHOUT the building-hull exclusion). ``dry_run`` reports the plan.

    ``nameplate_name`` selects the NATIVE-FLOW SURGERY nameplate (requires ``direct_field``, mutually exclusive
    with ``field``/``case`` and with the ``prompt``/``nameplate`` self-summon path): the whole entrance runs the
    game's REAL native flow. The trigger is the STOCK ``entrance_func_body(nameplate_case)`` (``Byte[39]=<case>`` +
    ``RunScriptAsync``); a DEAD high AREA-switch case (``nameplate_case``, default 53) is repointed to
    ``[explored-bit set] + Field(direct_field)`` in every carrying dispatcher/lang; and the name is registered into
    world text block 68 (via :func:`ff9mapkit.world.navimap.deploy_marker_renames`, locId = ``case-1``). Because the
    real func-0xB machinery drives the HUD, the location nameplate shows a genuine CUSTOM name (not "?" / a borrowed
    town) once the location is visited -- the handler sets its explored bit on entry, so first approach shows "?"
    then the name, exactly like a real town (faithful; the bit == navi marker ``locId case-1`` too).

    A real (non-``trigger_only``) deploy auto-mirrors the written terrain/building overrides to Disc4 (THE
    DISC-4 GAP; ``skip_mirror=True`` opts out)."""
    from ..eb.model import EbScript
    from ..eb import edit as E

    game_path = config.find_game_path(game)
    cell_x, cell_z = cell
    tag = pack_cell_tag(cell_x, cell_z, event)
    bx, by = cell_to_block(cell_x, cell_z)
    cwx, cwz = cell_world_center(cell_x, cell_z)

    if building and not Path(building["obj"]).is_file():   # fail BEFORE any write, so a bad path can't half-deploy
        raise ValueError(f"--building OBJ not found: {building['obj']}")

    alld = load_all_dispatchers(game)                      # {name: {lang: bytes}} -- per-lang (JP layout differs)
    us_disp = {n: L["us"] for n, L in alld.items() if "us" in L}
    surgery = nameplate_name is not None                   # the native-flow CUSTOM-name nameplate path
    handler = None                                          # the repointed switch arm (surgery only)
    exp_word = exp_bit = None
    if surgery:
        if direct_field is None:
            raise ValueError("nameplate_name requires direct_field=<custom id> (the surgery route warps a custom "
                             "destination through a repointed DEAD AREA-switch case)")
        if field is not None or case is not None:
            raise ValueError("nameplate_name is the direct/custom route -- drop field/case")
        if prompt or nameplate:
            raise ValueError("nameplate_name is the NATIVE-FLOW surgery nameplate; drop prompt/nameplate "
                             "(the superseded self-summon path)")
        the_case = int(nameplate_case)
        exp_word, exp_bit = explored_word_bit(the_case)
        if the_case > 60:
            # THE VIRGIN CASE BAND (61-64) -- the robust custom-name lane, NO stock-byte surgery at all.
            # The stock world has 61 name-table entries (cases 0-60): the AREA switch is base 2 x 59 cases
            # (2..60, so 61+ falls to its benign out-of-range default), func-0xB's 49+ range arm has NO
            # upper bound (explored bit = w98 >> (case-49), cases 49-64 exactly fill word 98), the plate
            # window admits any case < 90, and the ONLY main-loop special branch anywhere is case 52
            # (the quicksand's hardcoded `Byte[24]==52 && Confirm -> Battle(0,144)` -- the collision that
            # forced this lane; census 2026-07-26, all 9 free-roam dispatchers). So 61-64 are untouched by
            # every stock system EXCEPT the ones we want: the name table (which WE ship, extended by
            # navimap) and the explored bit. The trigger is the SELF-SUMMON body (fix-A2's verified laws:
            # summon gated on Byte[24]==100, warp on the on-foot gate, warp-branch Byte[24]=100 mute) with
            # the case's own summon + explored-bit set; the switch is never repointed -- there is no slot.
            if not 61 <= the_case <= 64:
                raise ValueError(f"nameplate_case {the_case} is past the explored-bit range (61-64 is the "
                                 f"virgin band; 65+ has no w98 bit and no plate machinery)")
            handler = None
            body = None                                    # per-dispatcher: carries the world-state record
            dest = {"case": the_case, "field": int(direct_field),
                    "note": f"VIRGIN-CASE nameplate: self-summon case {the_case} (no switch surgery; the "
                            f"AREA switch tops out at 60) -> Field({int(direct_field)}); name "
                            f"{nameplate_name!r} (locId {the_case - 1}, table extended); "
                            f"explored word {exp_word} bit {exp_bit}"}
            targets = sorted(name for name, L in alld.items()
                             if "us" in L and dispatcher_cases(L["us"]) is not None)
        else:
            handler = nameplate_handler(int(direct_field), the_case)
            body = entrance_func_body(the_case, dispatchers=us_disp)    # the STOCK trigger (language-independent)
            dest = {"case": the_case, "field": int(direct_field),
                    "note": f"NAMEPLATE SURGERY: dead case {the_case} -> Field({int(direct_field)}); "
                            f"name {nameplate_name!r} (locId {the_case - 1}); explored word {exp_word} bit {exp_bit}"}
            # dispatchers whose AREA switch carries this case (its contiguous range) -- every free-roam state
            targets = sorted(name for name, L in alld.items()
                             if "us" in L and (cs := dispatcher_cases(L["us"])) is not None and the_case in cs)
    elif direct_field is not None:
        if field is not None or case is not None:
            raise ValueError("give a destination as EITHER direct_field=<custom id> OR "
                             "field/case (the dispatcher-case route for real base fields)")
        # the DIRECT route (a CUSTOM destination): the trigger itself warps
        # Field(direct_field) behind the template's own vehicle/state gate --
        # no dispatcher case is touched, so it composes additively. Fires in
        # every free-roam state (the ones with an AREA switch). Each dispatcher
        # copy also RECORDS its own wldMapNo (the name's NN -> 9000+NN) so an
        # arrive= worldmap exit can return to the state the player left.
        the_case = None
        dest = {"case": None, "field": int(direct_field),
                "note": f"DIRECT Field({int(direct_field)}) -- custom destination, no dispatcher case"}
        body = None                                        # per-dispatcher (the state record)
        targets = sorted(name for name, L in alld.items()
                         if "us" in L and dispatcher_cases(L["us"]) is not None)
    else:
        dest = resolve_destination(field=field, case=case, game=game)
        the_case = dest["case"]
        body = entrance_func_body(the_case, dispatchers=us_disp)   # pure logic -> language-independent

        # dispatchers whose AREA switch carries this case (the states the entrance can fire in)
        targets = sorted(name for name, L in alld.items()
                         if "us" in L and (cases := dispatcher_cases(L["us"])) is not None and the_case in cases)
    if not targets:
        raise ValueError(f"no world dispatcher carries case {the_case} -- cannot route this entrance")

    eb_root = game_path / mod_folder / _WORLD_EB_SUBDIR
    summary = {
        "cell": [cell_x, cell_z], "tag": tag, "tag_hex": f"0x{tag:04X}", "block": [bx, by],
        "case": the_case, "field": dest["field"], "dest_note": dest["note"], "event": event,
        "cell_center": [cwx, cwz], "dispatchers_all": targets, "langs": list(LANGS),
        "dispatchers_written": [], "dispatchers_skipped": [], "backups": [], "dry_run": dry_run,
    }
    if surgery:
        summary.update({"surgery": True, "nameplate_name": nameplate_name, "name_locid": the_case - 1,
                        "explored_word": exp_word, "explored_bit": exp_bit,
                        "explored_bit_index": exp_word * 8 + exp_bit})

    # (1) the trigger function -> every carrying dispatcher, patched into EACH language's OWN base (stacking on any
    #     existing mod-folder .eb). Per-lang because JP's dispatcher carries localized dialogue + a distinct layout.
    bkdir = Path(backup_dir) if backup_dir else (Path.cwd() / "backups" / "world-entrance")
    for name in targets:
        fname = name.upper() + ".eb.bytes"
        us_mod = eb_root / "us" / fname
        us_base = us_mod.read_bytes() if us_mod.is_file() else alld[name]["us"]
        # the direct body is PER-DISPATCHER: it records the copy's own wldMapNo. The VIRGIN-band nameplate
        # (surgery with case 61-64, handler None) is a direct body too -- the self-summon form with the
        # case's own plate + explored bit; it composes additively exactly like a plain --field-direct.
        if body is not None:
            b = body
        elif surgery:
            b = entrance_func_body_direct(
                int(direct_field), world_state=9000 + int(name[-2:]), prompt=True, nameplate=True,
                nameplate_case=the_case, explored_case=the_case, dispatchers=us_disp)
        else:
            b = entrance_func_body_direct(
                int(direct_field), world_state=9000 + int(name[-2:]), prompt=prompt, nameplate=nameplate,
                dispatchers=us_disp)

        def _patch(base_l, _b=b):
            """Write the trigger func into object-0 (retagged to the cell) and, in switch-surgery mode, ALSO
            repoint the dead AREA-switch case to the handler (the virgin band has no slot to repoint --
            handler is None there). Idempotent -- an in-place re-run returns the input unchanged."""
            ex = EbScript.from_bytes(base_l).entry(0).func_by_tag(tag)
            if ex is None:
                base_l = E.add_function(base_l, 0, tag, _b)
            elif base_l[ex.abs_start:ex.abs_end] != _b:
                base_l = E.replace_function_body(base_l, 0, tag, _b)
            if surgery and handler is not None:
                base_l = _repoint_dead_case(base_l, the_case, handler)
            return base_l

        us_out = _patch(us_base)
        if us_out == us_base:                                              # trigger (+ repoint) already in place
            summary["dispatchers_skipped"].append(name)
            continue
        out_by_lang = {}                                                   # patch each lang's own base (stack if present)
        for lang in LANGS:
            lang_mod = eb_root / lang / fname
            base_l = lang_mod.read_bytes() if lang_mod.is_file() else alld[name].get(lang, alld[name]["us"])
            out_by_lang[lang] = us_out if lang == "us" else _patch(base_l)
        if not dry_run:
            if us_mod.is_file():                                           # back up the pre-edit representative
                bkdir.mkdir(parents=True, exist_ok=True)
                bk = bkdir / f"{name.upper()}.us.{_timestamp()}.eb.bytes"
                shutil.copy2(us_mod, bk)
                summary["backups"].append(str(bk))
            for lang in LANGS:
                p = eb_root / lang / fname
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(out_by_lang[lang])
        summary["dispatchers_written"].append({"name": name, "base_len": len(us_base),
                                               "out_len": len(out_by_lang["us"])})

    # (1c) surgery: register the CUSTOM name into world text block 68 (locId = case-1) so the native nameplate
    #      renders it. Per-language shadow; RELAUNCH to apply (the .mes isn't hot-reloaded).
    if surgery:
        from . import navimap
        summary["name_rename"] = {"locid": the_case - 1, "to": nameplate_name, "text_block": navimap.WORLD_TEXT_BLOCK}
        if not dry_run:
            written = navimap.deploy_marker_renames([{"locid": the_case - 1, "to": nameplate_name}],
                                                    mod_folder=mod_folder, game=game)
            summary["name_text_files"] = [str(p) for p in written]

    if trigger_only:                                        # .eb refresh only -- terrain/tiles/building untouched
        summary["trigger_only"] = True
        return summary

    # (2) event tile(s) on the cell's terrain block (+ optional flatten pad under the building), stacked
    ter = read_block_stacked(mod_folder, bx, by, disc=disc, lod=lod, part="terrain", game=game, fresh=fresh)
    try:                                                    # WARN if the cell is a poor spot (river/cliff or a town)
        _stock_obj = W.read_block(bx, by, disc=disc, lod=lod, part="object", game=game)
    except (ValueError, FileNotFoundError):
        _stock_obj = None
    _cell_openness_note(ter, cwx, cwz, *W.block_world_origin(bx, by), summary, stock_obj=_stock_obj)
    at = tuple(trigger_at) if trigger_at else (cwx, cwz)
    n_flat = 0
    if flatten_pad:
        pad_at = tuple(building["at"]) if (building and building.get("at")) else (cwx, cwz)
        eff_r = _capped_flatten_radius(float(flatten_pad), building, summary)
        pad_h = M.sample_ground_y(ter, pad_at[0] - bx * W.BLOCK_SIZE, pad_at[1] + by * W.BLOCK_SIZE)
        n_flat = M.flatten_region(ter, radius=eff_r, center=pad_at, height=pad_h,
                                  world_origin=W.block_world_origin(bx, by))
        M.recompute_normals(ter)
        summary["flatten_radius"] = eff_r
    hull = _building_world_hull(building, (cwx, cwz)) if building else None   # the building's tight world outline
    n_block = 0
    if hull and block_footprint:                            # make the terrain UNDER the building impassable (conforms
        from .extract import decode_id                       # to the ground; the tight HULL avoids an invisible skirt)
        # split_retarget_by_polygon (not the whole-triangle-centroid retarget_tiles) so the
        # blocked boundary traces the hull EXACTLY -- a real donor terrain triangle can be far
        # bigger than a small building footprint, and a centroid test over/under-shoots the
        # visible edge by up to half a triangle ("some collision, but not aligned", 2026-07-09)
        ter = M.split_retarget_by_polygon(ter, hull, topograph=59,
                                          world_origin=W.block_world_origin(bx, by))
        n_block = sum(1 for tri in ter.tris
                     if decode_id(int(round(ter.tangents[tri[0]][0])))["topograph"] == 59)
    # triggers OUTSIDE the building outline (walkable beside it). ORDER MATTERS: the footprint split above
    # already partitioned every straddling triangle at the hull, so this centroid-based exclusion is EXACT
    # here by construction -- do not stamp events before the split, or straddlers leak triggers under the wall
    n_tiles = M.retarget_tiles(ter, event=event, area=(the_case if set_tile_area else None),
                               center=at, radius=trigger_radius, world_origin=W.block_world_origin(bx, by),
                               exclude_polygon=hull)
    summary["tiles_set"] = n_tiles
    summary["tile_area_stamped"] = bool(set_tile_area)       # False => each tile KEEPS its existing area field
    summary["footprint_blocked"] = n_block
    summary["pad_flattened"] = n_flat
    if hull:
        summary["building_hull_pts"] = len(hull)
    entrance_written = []
    if not dry_run:
        terrain_dest = M.deploy_override(ter, mod_folder=mod_folder, game=game, lod=lod, part="Terrain")
        summary["terrain_override"] = str(terrain_dest)
        entrance_written.append(terrain_dest)
    if n_tiles == 0:
        summary["warning"] = (f"no terrain tiles matched at {at} r{trigger_radius} in block[{bx}][{by}] -- the "
                              f"trigger will never fire (widen --trigger-radius or check --trigger-at/--cell)")

    # (3) optional building -> Object mesh in the cell (seated on the possibly-flattened terrain, stacked on stock)
    if building:
        b_at = tuple(building["at"]) if building.get("at") else (cwx, cwz)
        keep = building.get("keep_block", True)
        if dry_run:
            summary["building"] = {"obj": building["obj"], "at": list(b_at), "seat": building.get("seat", True),
                                   "keep_block": keep, "topograph": building.get("topograph", 59),
                                   "idall": building.get("idall"),
                                   "texture": bool(building.get("texture") or building.get("tile") is not None
                                                   or building.get("tile_uv") is not None), "planned": True}
        else:
            from . import blendio as BIO
            stock = read_block_stacked(mod_folder, bx, by, disc=disc, lod=lod, part="object", game=game,
                                       missing_ok=True, fresh=fresh) if keep else None
            summary["building"] = BIO.build_from_obj(
                building["obj"], into_block=(bx, by), mod_folder=mod_folder, disc=disc, part="object", lod=lod,
                topograph=building.get("topograph", 59), idall=building.get("idall"),
                at=b_at, seat=building.get("seat", True),
                keep_block=keep, solid_base=building.get("solid_base", False),
                texture=building.get("texture", False), tile=building.get("tile"),
                tile_uv=building.get("tile_uv"), stock_bm=stock, terrain_bm=ter, game=game,
                skip_mirror=True)
            entrance_written.extend(summary["building"].get("written") or [])
    if not dry_run:
        from . import discmirror as DM
        DM.auto_mirror(entrance_written, mod_folder=mod_folder, skip_mirror=skip_mirror)
    return summary
