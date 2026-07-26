"""``[[qte]]`` -- the button-prompt reaction game (the Blank sword duel's core).

FF9 ships exactly one QTE: the Prima Vista sword fight (field 64, ``test2_15``),
decoded 2026-07-26 (studies/minigame-ui/SURVEY.md substrate #4). Its engine is a
prompt/poll/score loop over stock opcodes:

  * a random prompt (8 button texts, ``[DBTN]/[MOBI]`` glyphs, window flags 160)
    with a NO-REPEAT re-roll (and, in stock, combo-gated difficulty filters --
    the fancy prompts only roll at high combo);
  * a per-frame NINE-button edge poll while a reaction countdown decrements: the
    matching button = HIT, any other listed button = MISS, held Start = a
    deliberate bail, countdown exhausted = timeout-MISS;
  * TWO-CHANNEL scoring, stock's exact shape: a hit banks the COUNTDOWN LEFTOVER
    (speed IS the score) into one channel and the current COMBO into the other,
    then increments the combo; a miss zeroes the combo; max-combo is tracked;
  * the finale: a 1..100 score from the two channels, tiered verdict lines, and
    an optional gil purse paid by stock's formula (points/5 + bonus + 2*max +
    2*combo, halved, +1) with the gold-lettered shower line.

Stock splits ISSUER / POLLER / AGGREGATOR across three parallel entries only
because its actors ANIMATE during the poll (the duel choreography). The core
loop is strictly sequential, so the kit emits it as ONE modal function on its
own seated code entry -- the ``[[numeric_input]]`` architecture verbatim: opened
from a ``[[choice]]`` option's ``qte = "<name>"`` inside the DisableMove
bracket, scratch in high gEventGlobal, texts minted on the field's block.

THE SCRATCH BAND (bytes 2018-2031, ``flags.QTE_SCRATCH_FLOOR``, kit-reserved)
sits ON PURPOSE below the netsync co-op cells (bytes 2032-2039): the engine
rewrites those EVERY FRAME while [Netsync] co-op runs -- on any field, gates or
no gates -- so scratch there would have its combo/points channels clobbered
mid-bout. The band still overlaps the behavior blackboard's headroom
(1220-2040), so v1 refuses a field carrying both ``[[qte]]`` and ``[behavior]``
-- relaxable later by teaching the blackboard to reserve the band. gMesValue
slots 0 (score) and 1 (purse) are loaded at the finale.

Deferred theater (the stock duel's feel, deliberately out of v1): per-prompt
actor choreography, the hit/miss SFX cues (RunSoundCode3 has no wrapper yet),
the stage-marker camera pans, the encore-replay loop (re-talking replays -- the
scratch re-seeds), and stock's combo-gated prompt filters.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

from .. import flags as _flags
from ..eb import exprasm, opcodes
from ..eb.labelasm import JMP, JMP_IF, JMP_IFNOT, asm, label

# The eight stock prompts (field 64 texts 112-119, verbatim glyph pairs), in
# stock's own prompt-id order. name -> (EventInput mask, DBTN tag, MOBI icon).
BUTTONS = {
    "left":     (128,   "LEFT",     267),
    "right":    (32,    "RIGHT",    269),
    "triangle": (4096,  "TRIANGLE", 272),
    "down":     (64,    "DOWN",     270),
    "cross":    (16384, "CROSS",    274),
    "up":       (16,    "UP",       268),
    "circle":   (8192,  "CIRCLE",   273),
    "square":   (32768, "SQUARE",   271),
}
START_MASK = 8                    # held Start = stock's deliberate bail-to-miss

# Modal scratch (gEventGlobal BYTE offsets) -- 2018-2031 (the flags.py
# `qte_scratch` reserved region), STRICTLY below the netsync co-op cells
# (2032-2039; engine-written every frame under live co-op -- never touch them),
# the choice-mask word (2040) and the numeric_input scratch (2042+; modal like
# this band, never live at once, but distinct bands keep the map legible).
# Re-seeded on every open.
S_COMBO = 2018                    # Int16 -- current combo (stock's 40)
S_MAXC = 2020                     # Int16 -- max combo (stock's 42)
S_POINTS = 2022                   # Int16 -- the speed channel (stock's 30)
S_BONUS = 2024                    # Int16 -- the combo channel (stock's 32)
S_STATE = 2026                    # 0 idle / 1 prompt live / 2 hit / 3 miss (stock's 47)
S_EXPECT = 2027                   # the expected prompt index (stock's 46)
S_LAST = 2028                     # last prompt (the no-repeat blocklist, stock's 44)
S_COUNT = 2029                    # the reaction countdown (stock's 52)
S_ROUND = 2030                    # rounds played (stock's 34)

QTE_TAG = 3                       # the game function's tag on its seated entry
DISPATCH_LEVEL = 4                # the house remote-dispatch level
PROMPT_FLAGS = 160                # stock's prompt-window style (WindowAsync 1,160,tx)
RESULT_FLAGS = 0                  # stock's verdict style (WindowSync 5,0,tx)
ROUND_GAP = 20                    # frames between rounds (stock's inter-beat breath)

DEFAULT_VERDICTS = (
    "The crowd is booing...",                     # score < 25
    "The crowd was not impressed.",               # < 50
    "The crowd seemed to like it!",               # < 75
    "They demand an encore!",                     # 75+
)
DEFAULT_SCORE_TEXT = "[WDTH=0,140,64,0,-1]The crowd roars — [NUMB=0] of 100!"
# stock 128's gold-lettered shower, verbatim shape (Yellow pair + White restore)
DEFAULT_PAYOUT_TEXT = ("[WDTH=0,147,64,1,-1]They shower you with "
                       "[C8B040][HSHD][NUMB=1] Gil[C8C8C8][HSHD]!")


class QteError(ValueError):
    pass


@dataclass
class QteSpec:
    """One ``[[qte]]`` block, validated. ``result``: the gEventGlobal byte offset
    of a ``Global.Int16`` receiving the 1..100 score when the game ends (always
    written -- there is no cancel; Start bails a ROUND, not the game)."""
    name: str
    result: int
    rounds: int = 10
    window: int = 50                  # reaction frames per prompt
    par: int = 65                     # % of the THEORETICAL max that scores 100.
                                      # Round 1 scored against 100% (100 impossible,
                                      # ~85 superhuman); round 2's 80 mirrored stock's
                                      # divisor — but stock's forgiveness lives in its
                                      # COMBO channel, which only pays over its 48
                                      # rounds (bonus = 39% of stock's target vs 11%
                                      # at 10 rounds), so SHORT bouts concentrate
                                      # every mistake (ENGARDE round 2, owner-called).
                                      # 65 puts 100 at "clean run, decent reactions"
                                      # for the default 10 rounds; raise it for long
                                      # stock-length bouts, 100 = merciless.
    buttons: tuple = tuple(BUTTONS)   # the prompt set (names, >= 2)
    gil: bool = False                 # pay stock's purse formula at the finale
    flag: int | None = None           # optional GLOB bit raised at the finale (safe band only)
    prompt_window: int = 1            # stock's window ids
    result_window: int = 5
    verdicts: tuple = DEFAULT_VERDICTS
    score_text: str = DEFAULT_SCORE_TEXT
    payout_text: str = DEFAULT_PAYOUT_TEXT


_KEYS = {"name", "result", "rounds", "window", "par", "buttons", "gil", "flag",
         "prompt_window", "result_window", "verdicts", "score_text", "payout_text"}


def from_raw(block: dict, idx: int) -> QteSpec:
    ctx = f"[[qte]] #{idx}"
    extra = set(block) - _KEYS
    if extra:
        raise QteError(f"{ctx}: unknown key(s) {sorted(extra)}")
    name = block.get("name")
    if not isinstance(name, str) or not name.strip():
        raise QteError(f"{ctx}: needs a name (the [[choice]] option's qte = target)")
    ctx = f"[[qte]] {name!r}"
    result = block.get("result")
    if not isinstance(result, int) or not 4 <= result <= _flags.RESULT_WORD_CAP:
        raise QteError(f"{ctx}: result must be a gEventGlobal byte offset "
                       f"4..{_flags.RESULT_WORD_CAP} (an Int16; 2006-2017 are the kit's "
                       f"nameplate-explored words, 2018+ the game's own scratch). It "
                       f"receives the 1..100 score at the finale.")
    # the Int16 spans bytes result..result+1 = bits result*8..result*8+15; NONE of them may land
    # in a reserved save region (the Mognet mailbox/locks/read-mail bytes, the byte-23 menu
    # handshake, the worldmap unlocks, the netsync co-op cells) -- a score write there corrupts
    # real letter/engine state and ordinary play clobbers the score right back.
    hit = next((b for b in range(result * 8, result * 8 + 16) if _flags.is_reserved(b)), None)
    if hit is not None:
        r = _flags.bit_region(hit)
        raise QteError(f"{ctx}: result {result} -- the Int16 word (bytes {result}-{result + 1}) "
                       f"overlaps FF9's reserved '{r.name}' region (bits {r.lo}-{r.hi}): a write "
                       f"there corrupts real save/engine state, and ordinary play writes it "
                       f"right back over the score. Pick a clear byte offset (e.g. 1998, or "
                       f"{_flags.READMAIL_PAYLOAD_HI // 8 + 1}+).")
    rounds = block.get("rounds", 10)
    if not isinstance(rounds, int) or not 1 <= rounds <= 99:
        raise QteError(f"{ctx}: rounds must be 1..99")
    window = block.get("window", 50)
    if not isinstance(window, int) or not 10 <= window <= 255:
        raise QteError(f"{ctx}: window must be 10..255 reaction frames (stock: 50, "
                       f"30 on the encore)")
    par = block.get("par", 65)
    if not isinstance(par, int) or not 10 <= par <= 100:
        raise QteError(f"{ctx}: par must be 10..100 (the % of the theoretical max "
                       f"that scores 100 — default 65, tuned for short bouts)")
    btns = tuple(str(b) for b in (block.get("buttons") or tuple(BUTTONS)))
    bad = [b for b in btns if b not in BUTTONS]
    if bad:
        raise QteError(f"{ctx}: unknown button(s) {bad} — pick from {list(BUTTONS)}")
    if len(set(btns)) != len(btns) or len(btns) < 2:
        raise QteError(f"{ctx}: buttons must be >= 2 distinct names (the no-repeat "
                       f"re-roll would spin forever on one)")
    flag = block.get("flag")
    if flag is not None:
        if not isinstance(flag, int) or isinstance(flag, bool):
            raise QteError(f"{ctx}: flag must be a gEventGlobal BIT index")
        if _flags.is_reserved(flag):
            r = _flags.bit_region(flag)
            raise QteError(f"{ctx}: flag {flag} is inside FF9's reserved '{r.name}' region "
                           f"(bits {r.lo}-{r.hi}) -- a write there corrupts real save/engine "
                           f"state. Use the safe band [{_flags.FIRST_SAFE_FLAG}, "
                           f"{_flags.CHOICE_SCRATCH_FLOOR}), like a [[flag]] index.")
        if not _flags.FIRST_SAFE_FLAG <= flag < _flags.CHOICE_SCRATCH_FLOOR:
            raise QteError(f"{ctx}: flag {flag} is outside the safe custom band "
                           f"[{_flags.FIRST_SAFE_FLAG}, {_flags.CHOICE_SCRATCH_FLOOR}) -- "
                           f"indices below it are real-FF9 story state (a write couples the "
                           f"bout to stock progress or corrupts it). Pick an index in the band.")
        if result * 8 <= flag < result * 8 + 16:
            raise QteError(f"{ctx}: flag {flag} sits inside the result word's own bits "
                           f"({result * 8}-{result * 8 + 15}) -- the finale writes both, so "
                           f"each would corrupt the other. Pick a bit outside bytes "
                           f"{result}-{result + 1}.")
    verd = block.get("verdicts", list(DEFAULT_VERDICTS))
    if not (isinstance(verd, list) and len(verd) == 4
            and all(isinstance(v, str) and v.strip() for v in verd)):
        raise QteError(f"{ctx}: verdicts must be 4 lines (score tiers <25 / <50 / "
                       f"<75 / 75+)")
    for wkey in ("prompt_window", "result_window"):
        wv = block.get(wkey, 1 if wkey == "prompt_window" else 5)
        if not isinstance(wv, int) or not 0 <= wv <= 7:
            raise QteError(f"{ctx}: {wkey} must be 0..7 (Dialog.WindowID)")
    return QteSpec(name=name, result=result, rounds=rounds, window=window, par=par,
                   buttons=btns, gil=bool(block.get("gil", False)), flag=flag,
                   prompt_window=int(block.get("prompt_window", 1)),
                   result_window=int(block.get("result_window", 5)),
                   verdicts=tuple(verd),
                   score_text=str(block.get("score_text", DEFAULT_SCORE_TEXT)),
                   payout_text=str(block.get("payout_text", DEFAULT_PAYOUT_TEXT)))


# --------------------------------------------------------------------- the .mes texts
def mes_texts(spec: QteSpec) -> list:
    """``(part, text, strt)`` tuples: one stock-verbatim prompt line per button
    (field 64's own glyph pairs), the score line, four verdicts, the payout."""
    out = []
    for b in spec.buttons:
        _mask, dbtn, mobi = BUTTONS[b]
        out.append((f"p_{b}", f"[IMME]Press [DBTN={dbtn}][MOBI={mobi}] ![TIME=-1]",
                    (54, 1)))                            # stock 112-119's geometry
    sc = spec.score_text if "[IMME]" in spec.score_text else "[IMME]" + spec.score_text
    out.append(("score", sc, (170, 1)))
    for i, v in enumerate(spec.verdicts):
        out.append((f"verdict{i}", v if "[IMME]" in v else "[IMME]" + v, None))
    if spec.gil:
        pt = (spec.payout_text if "[IMME]" in spec.payout_text
              else "[IMME]" + spec.payout_text)
        out.append(("payout", pt, (147, 1)))             # stock 128's geometry
    return out


# --------------------------------------------------------------------- the .eb emitter
def _stmt(text: str) -> bytes:
    return bytes([0x05]) + exprasm.assemble(text + " B_EXPR_END")


def game_body(spec: QteSpec, txids: dict) -> bytes:
    """The blocking QTE function (tag :data:`QTE_TAG`) — the field-64 core loop,
    label-assembled, one sequential entry. ``txids``: part name -> minted txid."""
    n = len(spec.buttons)
    W, RW = spec.prompt_window, spec.result_window
    B = []
    B.append(opcodes.wait(2))
    for off, val in ((S_STATE, 0), (S_ROUND, 0)):
        B.append(_stmt(f"Global.Byte[{off}] const({val}) B_LET"))
    B.append(_stmt(f"Global.Byte[{S_LAST}] const(255) B_LET"))    # no last yet
    for off in (S_COMBO, S_MAXC, S_POINTS, S_BONUS):
        B.append(_stmt(f"Global.Int16[{off}] const(0) B_LET"))
    B.append(label("round_top"))
    B.append(_stmt(f"Global.Byte[{S_ROUND}] const({spec.rounds}) B_GE"))
    B.append((JMP_IF, "results"))
    # THE PICK — random8 % n with the no-repeat re-roll (stock's 88-sentinel loop)
    B.append(label("pick"))
    B.append(_stmt(f"Global.Byte[{S_EXPECT}] B_SYSVAR[0] const({n}) B_REM B_LET"))
    B.append(_stmt(f"Global.Byte[{S_EXPECT}] Global.Byte[{S_LAST}] B_EQ"))
    B.append((JMP_IF, "pick"))                           # backward signed — legal
    B.append(_stmt(f"Global.Byte[{S_LAST}] Global.Byte[{S_EXPECT}] B_LET"))
    B.append(_stmt(f"Global.Byte[{S_COUNT}] const({spec.window}) B_LET"))
    B.append(_stmt(f"Global.Byte[{S_STATE}] const(1) B_LET"))
    # open the prompt — unrolled dispatch over the expected index
    for k, b in enumerate(spec.buttons):
        B.append(_stmt(f"Global.Byte[{S_EXPECT}] const({k}) B_EQ"))
        B.append((JMP_IFNOT, f"pw_{k}"))
        B.append(opcodes.window_async(W, PROMPT_FLAGS, txids[f"p_{b}"]))
        B.append((JMP, "poll"))
        B.append(label(f"pw_{k}"))
    B.append(label("poll"))
    for k, b in enumerate(spec.buttons):
        mask = BUTTONS[b][0]
        B.append(_stmt(f"const4({mask}) B_KEYON"))
        B.append((JMP_IFNOT, f"pb_{k}"))
        B.append(_stmt(f"Global.Byte[{S_EXPECT}] const({k}) B_EQ"))
        B.append((JMP_IFNOT, f"wrong_{k}"))
        B.append(_stmt(f"Global.Byte[{S_STATE}] const(2) B_LET"))
        B.append((JMP, "resolve"))
        B.append(label(f"wrong_{k}"))
        B.append(_stmt(f"Global.Byte[{S_STATE}] const(3) B_LET"))
        B.append((JMP, "resolve"))
        B.append(label(f"pb_{k}"))
    B.append(_stmt(f"const4({START_MASK}) B_KEY"))       # held Start = the bail
    B.append((JMP_IFNOT, "no_bail"))
    B.append(_stmt(f"Global.Byte[{S_STATE}] const(3) B_LET"))
    B.append((JMP, "resolve"))
    B.append(label("no_bail"))
    B.append(_stmt(f"Global.Byte[{S_COUNT}] const(1) B_MINUS_LET"))
    B.append(_stmt(f"Global.Byte[{S_COUNT}] const(0) B_GT"))
    B.append((JMP_IFNOT, "timeout"))
    B.append(opcodes.wait(1))
    B.append((JMP, "poll"))
    B.append(label("timeout"))
    B.append(_stmt(f"Global.Byte[{S_STATE}] const(3) B_LET"))
    B.append(label("resolve"))
    B.append(opcodes.encode(0x21, W))                    # CloseWindow(prompt)
    B.append(_stmt(f"Global.Byte[{S_STATE}] const(2) B_EQ"))
    B.append((JMP_IFNOT, "miss"))
    # THE HIT — stock's two channels: the countdown LEFTOVER + the current combo
    B.append(_stmt(f"Global.Int16[{S_POINTS}] Global.Byte[{S_COUNT}] B_PLUS_LET"))
    B.append(_stmt(f"Global.Int16[{S_BONUS}] Global.Int16[{S_COMBO}] B_PLUS_LET"))
    B.append(_stmt(f"Global.Int16[{S_COMBO}] const(1) B_PLUS_LET"))
    B.append((JMP, "tally"))
    B.append(label("miss"))
    B.append(_stmt(f"Global.Int16[{S_COMBO}] const(0) B_LET"))
    B.append(label("tally"))
    B.append(_stmt(f"Global.Int16[{S_COMBO}] Global.Int16[{S_MAXC}] B_GT"))
    B.append((JMP_IFNOT, "no_max"))
    B.append(_stmt(f"Global.Int16[{S_MAXC}] Global.Int16[{S_COMBO}] B_LET"))
    B.append(label("no_max"))
    B.append(opcodes.wait(ROUND_GAP))
    B.append(_stmt(f"Global.Byte[{S_ROUND}] const(1) B_PLUS_LET"))
    B.append((JMP, "round_top"))
    # THE FINALE — stock's score/clamp/tiers/purse, parameterized
    B.append(label("results"))
    par_max = max(1, spec.rounds * spec.window * spec.par // 100)
    B.append(_stmt(f"Global.Int16[{spec.result}] "
                   f"Global.Int16[{S_POINTS}] Global.Int16[{S_BONUS}] B_PLUS "
                   f"const(100) B_MULT const({par_max}) B_DIV "
                   f"B_LET"))
    B.append(_stmt(f"Global.Int16[{spec.result}] const(100) B_GT"))
    B.append((JMP_IFNOT, "cl_lo"))
    B.append(_stmt(f"Global.Int16[{spec.result}] const(100) B_LET"))
    B.append(label("cl_lo"))
    B.append(_stmt(f"Global.Int16[{spec.result}] const(1) B_LT"))
    B.append((JMP_IFNOT, "cl_done"))
    B.append(_stmt(f"Global.Int16[{spec.result}] const(1) B_LET"))
    B.append(label("cl_done"))
    B.append(opcodes.encode(0x66, 0,
                            exprasm.assemble(f"Global.Int16[{spec.result}] B_EXPR_END"),
                            arg_flags=0b10))
    B.append(opcodes.window_sync(RW, RESULT_FLAGS, txids["score"]))
    for i, thr in enumerate((25, 50, 75)):
        B.append(_stmt(f"Global.Int16[{spec.result}] const({thr}) B_LT"))
        B.append((JMP_IFNOT, f"tier_{i}"))
        B.append(opcodes.window_sync(RW, RESULT_FLAGS, txids[f"verdict{i}"]))
        B.append((JMP, "tiers_done"))
        B.append(label(f"tier_{i}"))
    B.append(opcodes.window_sync(RW, RESULT_FLAGS, txids["verdict3"]))
    B.append(label("tiers_done"))
    if spec.gil:
        purse = (f"Global.Int16[{S_POINTS}] const(5) B_DIV "
                 f"Global.Int16[{S_BONUS}] B_PLUS "
                 f"Global.Int16[{S_MAXC}] const(2) B_MULT B_PLUS "
                 f"Global.Int16[{S_COMBO}] const(2) B_MULT B_PLUS "
                 f"const(2) B_DIV const(1) B_PLUS")
        B.append(opcodes.encode(0x66, 1, exprasm.assemble(purse + " B_EXPR_END"),
                                arg_flags=0b10))
        B.append(opcodes.encode(0xCE, exprasm.assemble(purse + " B_EXPR_END"),
                                arg_flags=0b1))          # AddGil, expression form
        B.append(opcodes.window_sync(RW, RESULT_FLAGS, txids["payout"]))
    if spec.flag is not None:
        B.append(_stmt(f"Global.Bit[{spec.flag}] const(1) B_LET"))
    B.append(opcodes.RETURN)
    return asm(B)


def entry_bytes(spec: QteSpec, txids: dict) -> bytes:
    """The seated code entry: tag 0 = a bare return, tag :data:`QTE_TAG` = the
    game. Activate with ``init_code(slot, 0)``."""
    init = bytes(opcodes.RETURN)
    body = game_body(spec, txids)
    header = bytes([0x00, 0x02]) + struct.pack("<HHHH", 0, 8, QTE_TAG, 8 + len(init))
    return header + init + body


def call_bytes(slot: int) -> bytes:
    """The ``[[choice]]`` option's dispatch — block the talk body until the game
    ends (REQEW at the house dispatch level)."""
    return opcodes.run_script_sync(DISPATCH_LEVEL, slot, QTE_TAG)
