"""Cutscenes -- ordered, control-locked scripted sequences.

This is the one thing the declarative content (NPCs / events / flags) can't express: a SEQUENCE that
runs in order. A cutscene runs its actions in order with the player's control disabled for the
duration, optionally once (flag-gated), triggered on field entry.

There are two flavours, by whether the cutscene declares a cast (``actors = [...]``):

* **Narration (no cast)** -- a standalone code entry whose function steps through *controller-
  level* actions that need no per-actor targeting: ``say`` (a dialogue/narration window),
  ``wait`` (pause N frames), ``set_flag`` (set a story flag). Triggered on load via ``InitCode``.
  This module builds it (:func:`build_body` / :func:`inject_cutscene`).

* **Cast scene (``actors = ["name", ...]``)** -- the CONDUCTOR (:mod:`ff9mapkit.content.conductor`):
  one central director code entry drives every cast member by uid via the ``*Ex`` opcode family;
  walk / path / teleport / face_player run as per-actor tags executed in the actor's own context.
  (The old single-actor loop-splice flavor -- ``actor = "<name>"`` -- was REMOVED in the #13 v3
  redesign: a one-name cast expresses it through the conductor, which is strictly more capable.)
  This module still supplies the shared actor-op primitives (:func:`actor_walk` / :func:`actor_teleport`
  / :func:`actor_animation` / :func:`actor_turn` / :func:`actor_face`) its tag bodies are built from.

Both grounded in the standard FF9 pattern -- ``DisableMove`` (0x2D) ... actions ... ``EnableMove``
(0x2E), flag-gated so a one-time scene doesn't replay -- and in real walk cutscenes (e.g. Gargan
Roo's Kuja walk function: SetWalkSpeed -> RunAnimation -> WaitAnimation -> InitWalk -> Walk).
"""

from __future__ import annotations

import struct

from .. import flags as _flags
from ..eb import EbScript, edit, opcodes
from . import region as _region
from . import event as _event

# Default flag for a "play once" cutscene: the SAVE-PERSISTENT Global bool (survives reloads), in the
# provably-safe custom band and clear of the event auto-once band (flags.AUTO_EVENT_BASE -- the band
# map lives there).
CUTSCENE_FLAG_CLASS = _region.GLOB_BOOL
DEFAULT_CUTSCENE_FLAG = _flags.AUTO_CUTSCENE_BASE   # GLOB (save-persistent) once-flag: plays once EVER
DEFAULT_CUTSCENE_MAP_FLAG = 80      # MAP-bit (transient, byte 10 -- clear of the field's init bits 144-159
                                    # and the camera Map-byte 24): replays each visit, still once per visit

PLAYER_UID = 250        # GetObjUID(250) resolves to the player's control character (engine convention)

# A field's Main_Init enables control then runs a ~16-frame entry FadeFilter; for the first frames
# the field is still fading + the smooth-frame-updater is settling actor positions. Issuing an actor
# Walk during that window makes the actor circle and never converge (its synchronous Walk then hangs
# -> softlock). So an ACTOR cutscene waits a warm-up before commanding the actor -- exactly what real
# entry cutscenes do (Main_Loop `Wait(...)` before RunScript). Tunable via `[cutscene] warmup = N`.
DEFAULT_WARMUP = 30     # frames (~1s @ 30fps); generous margin over the 16-frame entry fade


# A compulsory / auto-advance ATE (FF9's FORCED "Active Time Event" cutscene -- no menu, plays at a story
# beat, e.g. field 956 Gargant / the Festival-of-the-Hunt cluster) is an ordinary cutscene with two cosmetic
# ATE flourishes, both grounded byte-for-byte in the real grey mode-6 fields (`docs/ATE_SYSTEM.md` Flavor A):
#   * its dialogue windows carry the winATE caption flag (64) -> the "Active Time Event" header. This flag
#     is ALSO what makes the engine tag the closed dialog `isCompulsory` (ETb.ProcessATEDialog) -- the
#     defining, engine-recognized marker of a compulsory ATE.
#   * the body is bracketed `ATE(6) ... ATE(0)` (0xD7) -- the grey-unskippable HUD-icon arm (Gray+force; the
#     mode arg is a 3-bit flag word, not an enum -- &3==2 Gray, &4 force; see EIcon.cs:416-454 / ATE_SYSTEM.md).
#     (NB field 1901's Eiko ATE is the OPTIONAL Blue mode-1 menu hub, NOT this forced flavor -- don't mirror it.)
# TWO real templates for an auto-playing ATE (676-field byte sweep + the grey-unskippable re-classification,
# docs/ATE_SYSTEM.md):
#   * ate_mode = 6 (GREY + force-show) = the AUTHENTIC UNSKIPPABLE ATE and the DEFAULT -- the real game's forced
#     ATEs (field 956, the Festival-of-the-Hunt cluster) use ATE(6): a grey, force-shown icon that renders even
#     under the control-lock. It drives the bottom-left "ACTIVE TIME EVENT" HUD banner (ActiveTimeEvent.cs), whose
#     grey "ATE" sprite blinks 1s on / 1s off (DisplayGrayATEText) and shows NO press glyph. ★ in-game proven @30008.
#   * ate_mode = 1 (Blue, no force) = the opt-in quiet no-icon variant: mode 1's render gate
#     (`mode>0 && ((mode&4) || GetUserControl())`) FAILS under the control-lock, so no HUD banner shows -- the
#     winATE CAPTION window is the only marker (also proven @30008, before the mode-6 switch).
# AVOID ate_mode = 5 (Blue + force): a force-shown Blue icon re-flashes the "Press SELECT" glyph (the Blue
# coroutine), wrongly inviting a press during an auto-play. mode 2 is unused in the real game; the only grey is 6.
# (NB the kit holds ATE(6) armed across the whole body so the grey banner blinks throughout -- more legible than
# real 956, which clears it behind a white fade-in; this matches what players remember seeing.)
# Seen-state + the ATE80 trophy register only on a REAL field id (MappingATEID keyed on fldMapNo/SC) -- the wall.
# Mirrors `ate.WIN_ATE`; kept local to avoid importing the ate module (which imports choice -> region).
ATE_CAPTION_FLAG = 64
ATE_DEFAULT_MODE = 6     # ATE(mode) HUD arm. 6 = the authentic GREY UNSKIPPABLE banner (default, in-game proven
                         # @30008); 1 = opt-in quiet no-icon variant. Avoid 5 (Blue force-show re-flashes press glyph)

# How long the grey ATE banner shows as a pre-warp WARNING (real field 956 Gargan Roo: ATE(6) -> Wait(45) ->
# fade -> ATE(0) -> Field(scene)). ~1.5s @ 30fps.
ATE_WARN_FRAMES = 45
FORCED_ATE_TAG = 38      # player-entry func tag for the forced-ATE warp sequence (clear of the conductor's
                         # 19/20, the ladder's 17, the jump's 40)


def forced_ate_warp_body(target: int, *, mode: int = ATE_DEFAULT_MODE, frames: int = ATE_WARN_FRAMES,
                         title_txid: int | None = None) -> bytes:
    """The forced-ATE player func body -- ``RunScript``'d from the trigger region (NOT run inline in the
    region). It MUST run in the player's delegated context because a region's own tag-2 body is stepped only
    while ``usercontrol == 1`` (``region.py``), so a ``DisableMove`` + ``Wait`` *inline in the region* FREEZES
    -- the Wait never counts down and the warp never fires (the in-game bug). A ``RunScript``'d func's Waits
    tick regardless of the lock (same reason the ladder/jump arcs are RunScript'd, not inlined).

    Real grey ATEs 956 (Gargan Roo) + 2211 (Palace/Dock) verified byte-for-byte:
    ``ATE(6) -> Wait(45) -> FadeFilter -> ATE(0) -> WindowAsync(0, winATE, title) -> Field``. The title there is a
    NON-BLOCKING async window (``WindowAsync``, not a press-to-continue ``WindowSync``) shown CENTERED (its
    centering is the .mes geometry ``[STRT=W,1][IMME][CENT=W]``, set in :func:`ff9mapkit.build.collect_text`).

    ONE faithful deviation: the real game opens that WindowAsync AFTER the fade because it's a MULTI-screen ATE,
    so the title rides the NEXT screen's fade-in. A single warp has no such screen -- a window opened on the
    already-black screen is cleared by ``Field()`` before it draws (in-game: "no title window"). So the kit shows
    the centered async title DURING the banner WARNING (before the fade), where it's actually on-screen -- same
    visible result (centered title + grey banner as the ATE triggers), still async + centered. The banner clears
    before the warp, so the destination scene has NO banner. Pair the trigger with a plain ``[cutscene]`` +
    ``exit_warp`` on ``target`` (it warps the player back)."""
    title = (opcodes.window_async(0, ATE_CAPTION_FLAG, int(title_txid)) if title_txid is not None else b"")
    return (opcodes.ate(int(mode)) + title + opcodes.wait(int(frames))          # grey banner + centered title, the WARNING
            + opcodes.fade_filter(*_event.WARP_FADE) + opcodes.wait(25)         # fade to black (the proven warp fade)
            + opcodes.ate(0) + opcodes.field(int(target)) + opcodes.RETURN)     # clear banner, warp to the scene


def forced_ate_region(zone, ate_tag: int = FORCED_ATE_TAG, *, player_uid: int = PLAYER_UID) -> bytes:
    """A type-1 TREAD region that fires the forced-ATE warp the moment the player walks in -- the ladder/jump
    dispatch shape: Init ``SetRegion`` / tread ``MOVEMENT_GATE; DisableMove; RunScriptSync(2, player, ate_tag)``.
    The lock is set HERE (the region), but the timed sequence runs in the RunScript'd player func (so its Waits
    tick). The func warps away, so control never returns to this region (the destination restores it)."""
    import struct as _struct
    init = _region.set_region(zone) + opcodes.RETURN
    tread = (_region.MOVEMENT_GATE + opcodes.DISABLE_MOVE
             + opcodes.run_script_sync(2, int(player_uid), int(ate_tag)))
    funcs = [(0, init), (_region.RANGE_TAG, tread)]
    table, pos = b"", len(funcs) * 4
    for tag, body in funcs:
        table += _struct.pack("<HH", tag, pos)
        pos += len(body)
    return bytes([_region.REGION_ENTRY_TYPE, len(funcs)]) + table + b"".join(b for _, b in funcs)


def inject_forced_ate(data, zone, target: int, *, mode: int = ATE_DEFAULT_MODE,
                      title_txid: int | None = None, ate_tag: int = FORCED_ATE_TAG,
                      reserve_party_band: bool = False) -> bytes:
    """Inject a forced-ATE warp-in (the faithful grey-ATE TRIGGER): graft the warp func onto the player entry
    as ``ate_tag``, append a tread region that fires it, and arm it. The banner WARNS, then warps to ``target``
    -- pair ``target`` with a plain ``[cutscene]`` + ``exit_warp`` to play the scene and return the player.
    Returns new .eb bytes. (Native/synth: the player entry + a normal slot. ``reserve_party_band`` seats the
    region below a verbatim fork's party band.)"""
    from .ladder import find_player_entry
    from . import object as _object
    z = [tuple(p) for p in zone]
    if len(z) == 4:                                            # IsInQuad-safe: double the last vertex
        z = z + [z[-1]]
    pe = find_player_entry(EbScript.from_bytes(data))
    data = edit.add_function(data, pe, ate_tag,
                             forced_ate_warp_body(int(target), mode=mode, title_txid=title_txid))
    data, slot = _object.seat_entry(data, forced_ate_region(z, ate_tag),
                                    reserve_party_band=reserve_party_band)
    return edit.activate(data, opcodes.init_region(slot, 0))


def say(text_id: int, *, window: int = 1, flags: int = 128) -> bytes:
    """Step: open a dialogue/narration window showing ``text_id`` (blocks until the player dismisses).
    ``flags = 64`` (winATE) renders it with the "Active Time Event" caption (a compulsory-ATE window)."""
    return opcodes.window_sync(window, flags, text_id)


def wait(frames: int) -> bytes:
    """Step: pause for ``frames`` frames."""
    return opcodes.wait(frames)


def set_flag(idx: int, value: int = 1, *, flag_class=CUTSCENE_FLAG_CLASS) -> bytes:
    """Step: set a GlobBool story flag (advance/record state from within the scene)."""
    return _region.set_var(flag_class, idx, value)


# --- actor-context steps (v2) -- only valid inside an `actor` cutscene (run in the NPC's entry) ---
# How fast the actor rotates toward its destination while walking (omega, 0..255). High = the
# turn-while-walk arc shrinks to ~nothing, so a walk to a point BEHIND the actor turns and goes
# straight instead of orbiting it forever. This replaces a separate animated pre-turn
# (TurnTowardPosition/TimedTurn + WaitTurn), which can HANG at ~180deg (the animated big-turn path
# never completing -> WaitTurn stuck -> softlock). Self-converging + deterministic at exactly 180.
WALK_TURN_SPEED = 255


def actor_walk(x: int, z: int, speed: int | None = None) -> bytes:
    """Step: the actor walks to world (x, z).

    Sets a high walk-turn-speed first so the Walk rotates tightly toward the destination and walks
    straight (no arc), converging even when the target is directly BEHIND the actor -- without the
    animated pre-turn that hangs at ~180deg. ``StopAnimation`` clears the anim flags first so the
    engine actually swaps idle->walk while moving (else a player-cloned NPC glides in its idle pose).
    ``Walk`` blocks until arrival. Optional ``speed`` sets the walk movement speed. Uses the NPC's
    walk animation (set in its Init)."""
    pre = opcodes.set_walk_speed(int(speed)) if speed is not None else b""
    return (pre + opcodes.set_walk_turn_speed(WALK_TURN_SPEED) + opcodes.stop_animation()
            + opcodes.init_walk() + opcodes.walk(int(x), int(z)))


def actor_teleport(x: int, z: int) -> bytes:
    """Step: instantly move the actor to world (x, z) -- no walk animation -- then re-enable its
    walkmesh pathing (MoveInstantXZY disables it). Use it as a cutscene's FIRST step to place the
    actor off-screen for a walk-in (the kit handles the engine's POS3 Z-negation; a leading teleport
    runs before the warm-up so the actor settles off-screen rather than flashing at its spawn)."""
    return opcodes.move_instant_xzy(int(x), int(z), 0) + opcodes.set_pathing(1)


# Cutscene steps are NON-BLOCKING on the animation system: we never use WaitAnimation/WaitTurn,
# because they HANG if the actor's anim playback doesn't drive them to completion (a player-cloned
# NPC's walk/turn anims don't always engage -> WaitTurn/WaitAnimation never return -> softlock). A
# turn is done INSTANTLY (no turn anim needed); an animation is played then given a fixed hold.
ANIM_HOLD = 40          # frames to let a played animation run before the next step (~1.3s)


def actor_animation(anim: int, hold: int = ANIM_HOLD) -> bytes:
    """Step: play animation ``anim`` on the actor, then hold ``hold`` frames (RunAnimation + a fixed
    Wait -- NOT WaitAnimation, which hangs if the anim doesn't complete)."""
    return opcodes.run_animation(int(anim)) + opcodes.wait(int(hold))


def actor_turn(angle: int) -> bytes:
    """Step: face ``angle`` INSTANTLY (0=south, 64=west, 128=north, 192=east). Instant (TurnInstant) so
    it works without a turn animation and never hangs."""
    return opcodes.turn_instant(int(angle))


def actor_face(uid: int = PLAYER_UID, speed: int = 16) -> bytes:
    """Step: turn the actor to face an object by UID (default 250 = the player), animated, non-blocking
    (no WaitTurn). Visible only if the turn anim engages; for a guaranteed instant facing use ``turn``."""
    return opcodes.turn_toward_object(int(uid), int(speed))


def compile_steps(steps, txids, *, say_flags: int = 128) -> bytes:
    """Compile ordered cutscene step dicts to bytes. Handles global steps (``say`` / ``wait`` /
    ``set_flag``) and actor-context steps (``walk`` / ``path`` / ``teleport`` / ``animation`` /
    ``turn`` / ``face_player``). ``say`` steps consume ``txids`` (a list of resolved text ids) in order.

    Actor steps are only meaningful inside an ``actor`` cutscene (they act on the executing object);
    :func:`ff9mapkit.build.validate` enforces that. ``say_flags`` is the window flag for every ``say``
    step -- pass ``ATE_CAPTION_FLAG`` (64) to render a compulsory ATE's windows with the ATE caption.
    A step's own ``style`` / ``window`` keys override per line (an explicit step style wins over
    ``say_flags``). Same encoders the round-trip tests cover."""
    from . import text as _text
    out, ti = [], 0
    for s in steps:
        if "say" in s:
            # dim swaps the whole presentation for the letter bracket (async + RaiseWindows +
            # WaitWindow -- the raise is what puts the text ABOVE the fade); routed through
            # event.message so both forms have ONE owner
            b = _event.message(txids[ti], window=int(s.get("window", 1)),
                               flags=_text.resolve_style(s.get("style"), default=say_flags),
                               dim=bool(s.get("dim")))
            out.append(b)
            ti += 1
        elif "wait" in s:
            out.append(wait(int(s["wait"])))
        elif "set_flag" in s:
            sf = s["set_flag"]
            out.append(set_flag(int(sf[0]), int(sf[1]) if len(sf) > 1 else 1))
        elif "walk" in s:
            out.append(actor_walk(s["walk"][0], s["walk"][1], s.get("speed")))
        elif "path" in s:                          # a multi-waypoint route = consecutive straight walks
            for pt in s["path"]:
                out.append(actor_walk(int(pt[0]), int(pt[1])))
        elif "teleport" in s:
            out.append(actor_teleport(s["teleport"][0], s["teleport"][1]))
        elif "animation" in s:
            out.append(actor_animation(s["animation"]))
        elif "turn" in s:
            out.append(actor_turn(s["turn"]))
        elif "face_player" in s:
            out.append(actor_face())
        else:
            raise ValueError(f"unknown cutscene step: {s!r}")
    return b"".join(out)


def blocks(raw_cutscene) -> list:
    """Normalize the cutscene section to a LIST of blocks in author order: the legacy singleton
    ``[cutscene]`` (one table) and the plural ``[[cutscene]]`` (array of tables -- the story-event
    DISPATCH: several scenes on one field, each gated to its own beat) both come out the same way.
    ``None``/empty -> ``[]``. Every consumer goes through this, so a singleton project's behavior
    (indices, auto flags, txid order) is exactly the one-block case."""
    if raw_cutscene is None:
        return []
    if isinstance(raw_cutscene, dict):
        return [raw_cutscene]
    return [b for b in raw_cutscene if isinstance(b, dict)]


def once_flag_for(cs: dict, k: int = 0):
    """(flag_class, flag_idx) for a cutscene's gate. ``once=true`` -> a SAVE-PERSISTENT Global bool
    (plays once ever); ``once=false`` -> a TRANSIENT Map bool (replays each visit -- the Map var resets
    on field load -- but still runs once per visit). An explicit ``flag = N`` overrides the index.
    ``k`` = the block's index in the ``[[cutscene]]`` dispatch -- each block auto-allocates its own
    default (GLOB ``DEFAULT_CUTSCENE_FLAG+k`` / MAP ``80+k``), so two scenes never share a once-flag;
    ``k=0`` reproduces the singleton's defaults byte-for-byte. NB build._FlagAlloc is the authoritative
    single-field allocator (it also SKIPS the project's authored flags); this bare default is its
    reserved-free fallback for callers without a project."""
    if cs.get("once", True):
        return _region.GLOB_BOOL, int(cs.get("flag", DEFAULT_CUTSCENE_FLAG + k))
    return _region.MAP_BOOL, int(cs.get("flag", DEFAULT_CUTSCENE_MAP_FLAG + k))


def early_return_unless(cond: bytes) -> bytes:
    """A story-gate PROLOGUE for a standalone cutscene/conductor entry: ``if (cond) skip-the-return`` --
    i.e. the entry returns immediately unless ``cond`` holds. The exact byte shape of
    :func:`ff9mapkit.content.onentry.scenario_gate` / :func:`ff9mapkit.content.region.flag_gate`
    (re-emitted here -- onentry imports this module, so it can't be imported back). Stack several for AND.
    This is the DIRECTOR gate (fork-fidelity #13): "this scene belongs to beat N / story-state S" -- the
    scene (and its then_warp) simply doesn't exist outside its beat, so its once-flag isn't burned."""
    return cond + bytes([_region.JMP_TRUE]) + struct.pack("<h", 1) + opcodes.RETURN


# A narration cutscene runs in a SEPARATE code entry armed by `InitCode` in Main_Init -- but Main_Init
# itself calls `EnableMove` (and a fade) AFTER that InitCode. If the director's `DisableMove` ran first
# it would be immediately overridden by Main_Init's `EnableMove`, so the player keeps control during the
# text. Yielding a couple of frames first lets Main_Init reach its `EnableMove` (it does so in the first
# frame), so the director's `DisableMove` is the LAST control-setter and the lock sticks. (A CAST scene
# avoids this with the conductor's control-grant spin.) ~2 frames is imperceptible (<100ms) and the
# window only shows during the entry fade.
REORDER_WAIT = 2


def build_body(steps, once_flag: int | None, flag_class=CUTSCENE_FLAG_CLASS,
               reorder: int = REORDER_WAIT, *, ate_mode: int | None = None,
               then_warp: int | None = None, gate: bytes = b"", end_writes: bytes = b"") -> bytes:
    """The cutscene function body: a brief reorder ``Wait`` (so the lock outlives Main_Init's EnableMove)
    then ``DisableMove`` + the ordered ``steps`` + ``EnableMove``, all gated ``if (!once_flag) { ...;
    once_flag = 1 }`` when ``once_flag`` is set (so it plays once).

    ``ate_mode`` (not None) brackets the steps ``ATE(mode) ... ATE(0)`` -- a compulsory ATE's HUD prompt
    (the winATE caption on its windows is set by the caller via ``compile_steps(say_flags=...)``).

    ``then_warp`` (a field id) makes the scene AUTO-RETURN: it ends with a FADE-TO-BLACK then
    ``Field(then_warp)`` instead of restoring control -- exactly how real grey ATEs end (field 956 ->
    ``Field(2054)``). The warp sits OUTSIDE the once-gate so it ALWAYS fires (even on a re-entry that skips
    a once'd cutscene, the player still warps back); it transitions away, so it's the last op (no
    ``EnableMove`` -- the destination's Main_Init restores control). It fades out first (``warp(fade=True)``)
    so the destination doesn't load in the clear (the static-screen bug). Field() transitions from this
    InitCode'd entry just like the World-Hub menu-row warp does (same code-entry context -- NOT the
    Main_Init no-op case)."""
    pre = opcodes.wait(int(reorder)) if reorder and reorder > 0 else b""
    inner = pre + opcodes.DISABLE_MOVE
    if ate_mode is not None:
        inner += opcodes.ate(int(ate_mode))
    inner += b"".join(steps)
    if ate_mode is not None:
        inner += opcodes.ate(0)
    if then_warp is None:
        inner += opcodes.ENABLE_MOVE                      # restore control (a normal cutscene stays put)
    # the DIRECTOR advance (#13): set_scenario/set_flags bytes (built by the caller) INSIDE the once-gate
    # (before the once-flag set) -- the story advances exactly once, only when the scene actually played;
    # with then_warp the writes land before the warp fires. Empty -> byte-identical.
    inner += end_writes
    if once_flag is not None:
        inner += _region.set_var(flag_class, once_flag, 1)
        body = _region.if_block(_region.cond_not(flag_class, once_flag), inner)
    else:
        body = inner
    if then_warp is not None:
        # fade=True: fade to black BEFORE the warp, like every field transition (gateway/ladder/choice).
        # Without it the destination loads in the clear and you see its camera-init frames (the static-
        # screen bug). A real grey-ATE return may already be black behind the ATE banner, but the kit
        # doesn't reproduce that, so an explicit source-side fade is the safe default. See event.warp.
        body += _event.warp(int(then_warp), fade=True)    # AUTO-RETURN: fade to black, then transition
    # the DIRECTOR gate (#13): a story-gate PROLOGUE (early_return_unless, stacked for AND) placed FIRST --
    # outside its beat/state the scene (once-flag, warp and all) simply doesn't run. Empty -> byte-identical.
    return gate + body + opcodes.RETURN


def inject_cutscene(data, steps, *, once_flag: int | None = None, flag_class=CUTSCENE_FLAG_CLASS,
                    spawn_wait_n: int = 2, spawn_wait_occurrence: int = 0,
                    ate_mode: int | None = None, then_warp: int | None = None,
                    gate: bytes = b"", end_writes: bytes = b"") -> bytes:
    """Append a cutscene code entry (the sequence in :func:`build_body`) and run it on field load via
    an ``InitCode`` (over a Wait filler, or inserted into Main_Init). Returns new .eb bytes.
    ``ate_mode`` (not None) styles it as a compulsory ATE (the ``ATE(mode)`` HUD bracket); ``then_warp``
    (a field id) makes it auto-return with ``Field(then_warp)`` at the end. ``gate`` / ``end_writes`` =
    the director story-gate prologue + end-of-scene story advance (see :func:`build_body`)."""
    body = build_body(steps, once_flag, flag_class, ate_mode=ate_mode, then_warp=then_warp,
                      gate=gate, end_writes=end_writes)
    entry = bytes([0x00, 0x01]) + struct.pack("<HH", 0, 4) + body
    slot = EbScript.from_bytes(data).first_free_slot()
    out = edit.append_entry(data, slot, entry)
    return edit.activate(out, opcodes.init_code(slot, 0), spawn_wait_n=spawn_wait_n,
                         spawn_wait_occurrence=spawn_wait_occurrence)
