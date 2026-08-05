"""``[[numeric_input]]`` -- the game's own numeric INPUT widget as kit vocabulary.

FF9 has exactly one number-entry idiom: the Treno auction's 3-digit bid stepper, carried
BYTE-FOR-BYTE by nine shipping fields (852/909/1600/1607/1909/2800/2950/2951/2952 -- the
studio's own reusable snippet). This module is that golden (field 909 ``Code10_31``,
decoded 2026-07-25, studies/minigame-ui/SURVEY.md substrate #2) re-emitted with the
digit count / step ceiling / multiplier / texts as parameters:

  * a FRAMELESS value window (``WindowAsync`` flags 16) whose text is the digit run --
    ``[NUMB=5][NUMB=6][NUMB=7]00 Gil`` (the multiplier is LITERAL trailing zeros, exactly
    stock's shape);
  * one frameless CURSOR window per digit: the SAME ``[NUMB]`` variable re-rendered in the
    engine's Pink pair (``[B880E0][HSHD]`` -- FFIXTextTagCode.Pink) at the same MPOS, so
    the selected digit reads highlighted because the pink glyph draws OVER the white one.
    Left/Right closes one overlay and opens the next (stock swaps windows 3/4/5 this way);
  * Up/Down mutates the selected digit's place with stock's auto-repeat ramp (a counter
    that arms after 8 held frames, then re-fires every 2) and per-place floor/ceiling
    guards; Confirm/Cancel exits (stock's sentinel-65535 shape, kept internal).

WHY THE SPLIT WINDOWS (vs stock's one framed legend holding the digits): stock aligns its
cursor overlays to ``x = 33 + 7*i`` under a framed window at MPOS 8 -- constants that bake
the pixel width of the literal prefix "Bid: ". A kit emitter with an AUTHORED label cannot
know that width offline. Frameless windows render their glyphs AT their MPOS (stock's own
overlays prove it), so the kit puts the digit run in its own frameless window and derives
every cursor MPOS as ``value_pos.x + 7*j`` -- aligned BY CONSTRUCTION, no font metrics.
The button legend becomes a free-floating framed window with no alignment constraint.
``[WDTH]`` only feeds the frame-width hint (DialogBoxSymbols.OnWidths -> WidthHint); it
never moves glyphs, so copying stock's tag shapes is safe. Digit glyphs advance a uniform
7px (stock's 33/40/47 pitch), so a digit variable never changes width -- the HUD lane's
``digits`` width-reserve problem does not exist here.

THE MODAL CONTRACT: the stepper is a blocking function on its own seated code entry,
dispatched ``RunScriptSync`` from a ``[[choice]]`` option (``input = "<name>"``). Choice
option bodies run between ``DisableMove``/``EnableMove`` (:mod:`.choice`), so field
movement is off while the loop polls the d-pad -- the walk-while-stepping hazard is
structural, not lucky. Because it is modal, ALL instances share one scratch block
(:data:`SCRATCH_VAL`/:data:`SCRATCH_RAMP`/:data:`SCRATCH_SEL` -- bytes 2042-2046, above
:data:`region.MASK_SCRATCH_IDX` and re-seeded on every open, the same transient-scratch
argument). On SUBMIT the stepped value lands in ``Global.Int16[result]`` (the author's
byte offset, STEPPED units -- the multiplier is display-only) plus gMesValue slot 0 as
``stepped * multiplier`` (for a ``[NUMB=0]`` echo/reply), and the optional ``flag`` bit
is raised. CANCEL touches nothing.

gMesValue slots: the digits live in slots ``8-digits .. 7`` (stock's 5/6/7) and the echo
in slot 0 -- build validation refuses a ``[[behavior.hud]]`` whose slots would collide.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field

from .. import flags as _flags
from ..eb import exprasm, opcodes
from ..eb.labelasm import JMP, JMP_IF, JMP_IFNOT, asm, label
from . import text as _text

# Field-event input masks (EventInput.cs) -- what a B_KEY/B_KEYON const tests. The
# directional values are the ladder module's proven set; Confirm is the world-entrance
# module's proven 0x20000; Cancel = 0x10000 (stock's `IsButton(65536)` cancel test in
# the auction golden, field 909).
KEY_UP = 0x10
KEY_RIGHT = 0x20
KEY_DOWN = 0x40
KEY_LEFT = 0x80
KEY_CANCEL = 0x10000
KEY_CONFIRM = 0x20000

# Modal scratch (gEventGlobal BYTE offsets) -- above region.MASK_SCRATCH_IDX (2040-2041),
# below the array's 2048 end. Re-seeded by every open, so stale values never matter (the
# choice-mask precedent). RAMP is an Int16 so the held-repeat counter is SIGNED -- stock
# used an entry-local Int8, and minted entries allocate zero locals (eb.edit hard-sets
# loc=0), so the kit's twin lives here with -8/+8 compared directly.
SCRATCH_VAL = 2042      # Global.Int16 -- the stepped value (0..9999)
SCRATCH_RAMP = 2044     # Global.Int16 -- the auto-repeat ramp
SCRATCH_SEL = 2046      # Global.Byte  -- the selected digit, 0 = rightmost (stock's shape)

INPUT_TAG = 3           # the stepper function's tag on its seated entry
DISPATCH_LEVEL = 4      # the house remote-dispatch level (field 574's redirect idiom)
HELP_WINDOW = 1         # the button-legend window (stock parks its status frame on 1)
ECHO_WINDOW = 0         # the submit-ack WindowSync (stock's deny lines use window 0)
DIGIT_PITCH = 7         # px per digit glyph -- stock's cursor MPOS run 33/40/47
RAMP_ARM = 8            # stock: first auto-repeat after 8 held frames...
RAMP_PULLBACK = 2       # ...then every 2 (each step pulls the ramp back by 2)

# The stock button-legend lines (field 909 text 203, verbatim -- [DBTN]/[CBTN] render the
# bound key glyph on PC, [MOBI] the mobile icon).
HELP_LINES = ("[DBTN=UP][MOBI=276][DBTN=DOWN][MOBI=275]: Adjust number\n"
              "[DBTN=LEFT][MOBI=267][DBTN=RIGHT][MOBI=269]: Select digit\n"
              "[CBTN=CROSS][MOBI=260]: Confirm\n"
              "[CBTN=CIRCLE][MOBI=261]: Cancel")
HELP_STRT_WIDTH = 113   # stock text 203's [STRT] width -- fits the legend lines


class NumericInputError(ValueError):
    pass


@dataclass
class InputSpec:
    """One ``[[numeric_input]]`` block, validated. ``result`` is the author's contract:
    the gEventGlobal BYTE offset of a ``Global.Int16`` receiving the STEPPED value on
    submit. ``max``/``start`` are stepped units; ``multiplier`` is display + echo only."""
    name: str
    result: int
    digits: int = 3
    multiplier: int = 1
    max: int = 0                      # 0 -> default 10^digits - 1 (fixed in from_raw)
    start: int = 0
    gil_ceiling: bool = False
    label: str = ""
    suffix: str = ""
    echo: str | None = None
    flag: int | None = None
    window: int = 6                   # value window; cursors = window-digits .. window-1
    pos: tuple = (33, 80)             # the value line's MPOS (stock's digit-run spot)
    help: bool = True
    help_pos: tuple = (8, 96)

    def cursor_window(self, sel: int) -> int:
        """Cursor window for digit ``sel`` (0 = rightmost) -- stock's ``3 + sel`` shape
        generalized to ``(window - digits) + sel``."""
        return self.window - self.digits + sel

    def slot(self, sel: int) -> int:
        """gMesValue slot for digit ``sel`` -- stock's 7/6/5 right-to-left run."""
        return 7 - sel

    def place(self, sel: int) -> int:
        """The decimal place a digit steps: 10^sel."""
        return 10 ** sel


_KEYS = {"name", "result", "digits", "multiplier", "max", "start", "gil_ceiling",
         "label", "suffix", "echo", "flag", "window", "pos", "help", "help_pos"}
_MULTIPLIERS = (1, 10, 100, 1000)


def from_raw(block: dict, idx: int) -> InputSpec:
    """Validate one raw ``[[numeric_input]]`` table into an :class:`InputSpec`.
    Raises :class:`NumericInputError` naming the block -- build/lint surface it."""
    ctx = f"[[numeric_input]] #{idx}"
    extra = set(block) - _KEYS
    if extra:
        raise NumericInputError(f"{ctx}: unknown key(s) {sorted(extra)}")
    name = block.get("name")
    if not isinstance(name, str) or not name.strip():
        raise NumericInputError(f"{ctx}: needs a name (the [[choice]] option's input = target)")
    ctx = f"[[numeric_input]] {name!r}"
    digits = block.get("digits", 3)
    if not isinstance(digits, int) or not 1 <= digits <= 4:
        raise NumericInputError(f"{ctx}: digits must be 1..4 (got {digits!r})")
    cap = 10 ** digits - 1
    mult = block.get("multiplier", 1)
    if mult not in _MULTIPLIERS:
        raise NumericInputError(f"{ctx}: multiplier must be one of {_MULTIPLIERS} "
                                f"(display-only trailing zeros, stock's x100 bid shape)")
    vmax = block.get("max", cap)
    if not isinstance(vmax, int) or not 1 <= vmax <= cap:
        raise NumericInputError(f"{ctx}: max must be 1..{cap} (stepped units at {digits} digits)")
    start = block.get("start", 0)
    if not isinstance(start, int) or not 0 <= start <= vmax:
        raise NumericInputError(f"{ctx}: start must be 0..max ({vmax})")
    result = block.get("result")
    if not isinstance(result, int) or not 4 <= result <= _flags.RESULT_WORD_CAP:
        raise NumericInputError(f"{ctx}: result must be a gEventGlobal byte offset "
                                f"4..{_flags.RESULT_WORD_CAP} (an Int16 lands at [result, "
                                f"result+1]; 2006+ is kit/game-owned -- the nameplate-explored "
                                f"words, the [[qte]] band, the netsync co-op cells the engine "
                                f"rewrites every frame under live co-op, the choice mask, this "
                                f"stepper's own scratch). It receives the STEPPED value on submit.")
    # the Int16's 16 bits must also clear the reserved save regions (Mognet mailbox/locks/
    # read-mail, the byte-23 menu handshake, ...) -- same walk as a [[qte]] result word
    hit = next((b for b in range(result * 8, result * 8 + 16) if _flags.is_reserved(b)), None)
    if hit is not None:
        r = _flags.bit_region(hit)
        raise NumericInputError(f"{ctx}: result {result} -- the Int16 word (bytes {result}-"
                                f"{result + 1}) overlaps FF9's reserved '{r.name}' region (bits "
                                f"{r.lo}-{r.hi}): a write there corrupts real save/engine state, "
                                f"and ordinary play clobbers the value right back. Pick a clear "
                                f"byte offset (e.g. 2000, or {_flags.READMAIL_PAYLOAD_HI // 8 + 1}+).")
    flag = block.get("flag")
    if flag is not None and not (isinstance(flag, int) and 0 <= flag <= 16383):
        raise NumericInputError(f"{ctx}: flag must be a gEventGlobal BIT index (raised on submit)")
    window = block.get("window", 6)
    if not isinstance(window, int) or not 0 <= window <= 7:
        raise NumericInputError(f"{ctx}: window must be 0..7 (Dialog.WindowID)")
    if window - digits < 2:
        raise NumericInputError(f"{ctx}: window {window} leaves no room for {digits} cursor "
                                f"windows below it (need window - digits >= 2; window 0 is the "
                                f"echo, window 1 the legend)")
    label = str(block.get("label", "") or "")
    if "\n" in label:
        raise NumericInputError(f"{ctx}: label must be a single line")
    pos = _xy(block.get("pos", (33, 80)), ctx, "pos")
    help_pos = _xy(block.get("help_pos", (8, 96)), ctx, "help_pos")
    echo = block.get("echo")
    if echo is not None and (not isinstance(echo, str) or not echo.strip()):
        raise NumericInputError(f"{ctx}: echo must be a non-empty line (shown on submit; "
                                f"[NUMB=0] renders the value)")
    return InputSpec(name=name, result=result, digits=digits, multiplier=mult, max=vmax,
                     start=start, gil_ceiling=bool(block.get("gil_ceiling", False)),
                     label=label, suffix=str(block.get("suffix", "") or ""), echo=echo,
                     flag=flag, window=window, pos=pos, help=bool(block.get("help", True)),
                     help_pos=help_pos)


def _xy(v, ctx: str, key: str) -> tuple:
    ok = isinstance(v, (list, tuple)) and len(v) == 2 and all(isinstance(c, int) for c in v)
    if not ok or not (0 <= v[0] <= 320 and 0 <= v[1] <= 224):
        raise NumericInputError(f"{ctx}: {key} must be [x, y] on the 320x224 dialog grid")
    return (int(v[0]), int(v[1]))


# --------------------------------------------------------------------- the .mes texts
def mes_texts(spec: InputSpec) -> list:
    """The block's minted ``.mes`` entries: ``(part, text, strt)`` tuples for the build's
    raw text channel (no speaker, no tail -- pinned windows draw none). Parts: ``value``,
    ``cur0..curN``, optional ``help``, optional ``echo``.

    ⚠ EVERY WINDOW CARRIES ``[NTUR]`` -- THE TURBO-INJECTION LAW (arm B). The stepper is
    exactly arm B's configuration: every open window is dismiss-inhibited ([NFOC]/[TIME=-1],
    so arm A never fires) while the value/cursor windows are flags-16 TRANSPARENT (inside the
    style predicate, UIKeyTrigger.cs:984) and the loop polls ``B_KEYON`` every frame (arming
    ``scriptRequestedButtonPress``, EBin.cs:1080). Under a latched F9 the engine then
    SYNTHESIZES a Confirm into the script's own input stream -- and the poll mask contains
    KEY_CONFIRM, so an un-guarded stepper submits its start value on the first poll frame
    with no player press (a Treno bid resolves itself). ``[NTUR]`` (preventTurboKey) bails
    at UIKeyTrigger.cs:976 BEFORE either arm, renders nothing, and never blocks the player's
    real keys; every digit step re-renders a window (re-asserting it), and the only Confirm
    that clears it is the one that legitimately ends the loop. The frameless flags-16 style
    is the overlay mechanism itself, so a style-side guard is not available here."""
    d = spec.digits
    vx, vy = spec.pos
    zeros = "0" * len(str(spec.multiplier)[1:])          # 100 -> "00", 1 -> ""
    # the digit run, left to right = highest place first = slots 8-d .. 7
    wdth = "".join(f"64,{spec.slot(d - 1 - j)}," for j in range(d))
    numbs = "".join(f"[NUMB={spec.slot(d - 1 - j)}]" for j in range(d))
    out = [("value", f"[MPOS={vx},{vy}][WDTH=0,0,{wdth}-1][NTUR][NFOC][IMME]"
                     f"{numbs}{zeros}{spec.suffix}[TIME=-1]", (0, 1))]
    for sel in range(d):
        x = vx + DIGIT_PITCH * (d - 1 - sel)             # screen column of digit `sel`
        out.append((f"cur{sel}", f"[MPOS={x},{vy}][WDTH=0,0,64,{spec.slot(sel)},-1]"
                                 f"[NTUR][NFOC][B880E0][HSHD][IMME][NUMB={spec.slot(sel)}][TIME=-1]",
                    (0, 1)))
    if spec.help:
        hx, hy = spec.help_pos
        head = f"{spec.label}\n" if spec.label else ""
        lines = HELP_LINES.count("\n") + 1 + (1 if spec.label else 0)
        out.append(("help", f"[MPOS={hx},{hy}][NANI][NTUR][NFOC][IMME]{head}{HELP_LINES}[TIME=-1]",
                    (HELP_STRT_WIDTH, lines)))
    if spec.echo:
        txt = spec.echo if "[IMME]" in spec.echo else "[IMME]" + spec.echo
        if _text.NO_TURBO_TAG not in txt and _text.renders_live_value(txt):
            txt = _text.NO_TURBO_TAG + txt               # a READOUT survives the player's own turbo
        out.append(("echo", txt, None))
    return out


# --------------------------------------------------------------------- the .eb emitter
def _stmt(text: str) -> bytes:
    return bytes([0x05]) + exprasm.assemble(text + " B_EXPR_END")


def _publish(spec: InputSpec) -> bytes:
    """SetTextVariable every digit slot from the stepped value -- stock's ``v%10`` /
    ``(v/10)%10`` / ``v/100`` split, as expression args (the engine re-renders a changed
    ``[NUMB]`` in place -- HUD law 1, so the windows are never re-issued)."""
    out = b""
    for sel in range(spec.digits):
        expr = f"Global.Int16[{SCRATCH_VAL}]"
        if spec.place(sel) > 1:
            expr += f" const({spec.place(sel)}) B_DIV"
        if sel < spec.digits - 1:                        # the top digit needs no % 10
            expr += " const(10) B_REM"
        out += opcodes.encode(0x66, spec.slot(sel),
                              exprasm.assemble(expr + " B_EXPR_END"), arg_flags=0b10)
    return out


def _up_guard(spec: InputSpec, step: int) -> str:
    """Room to grow: ``VAL <= max - step``, AND (gil_ceiling) ``gil/mult >= VAL + step``
    -- stock's live ``GetGil/100`` clamp with the -9/-99 offsets normalized."""
    g = f"Global.Int16[{SCRATCH_VAL}] const({spec.max - step}) B_LE"
    if spec.gil_ceiling:
        gil = "B_SYSVAR[6]"
        if spec.multiplier > 1:
            gil += f" const({spec.multiplier}) B_DIV"
        g += (f" {gil} Global.Int16[{SCRATCH_VAL}] const({step}) B_PLUS B_GE B_ANDAND")
    return g


def stepper_body(spec: InputSpec, txids: dict) -> bytes:
    """The blocking stepper function (tag :data:`INPUT_TAG`) -- the field-909 golden's
    control flow, label-assembled. ``txids``: part name -> minted txid."""
    d = spec.digits
    B = []
    B.append(opcodes.wait(2))                            # stock's settle
    B.append(_stmt(f"Global.Int16[{SCRATCH_VAL}] const({spec.start}) B_LET"))
    B.append(_stmt(f"Global.Byte[{SCRATCH_SEL}] const(0) B_LET"))
    B.append(_stmt(f"Global.Int16[{SCRATCH_RAMP}] const(0) B_LET"))
    B.append(_publish(spec))                             # seed BEFORE open (stock's order)
    B.append(opcodes.window_async(spec.window, 16, txids["value"]))
    if spec.help:
        B.append(opcodes.window_async(HELP_WINDOW, 0, txids["help"]))
    B.append(opcodes.window_async(spec.cursor_window(0), 16, txids["cur0"]))
    B.append(opcodes.wait(3))                            # stock's pre-loop debounce
    B.append(label("loop"))
    B.append(_stmt(f"const4({KEY_CONFIRM | KEY_CANCEL}) B_KEYON"))
    B.append((JMP_IF, "exit"))
    # RIGHT: cursor toward digit 0; else-coupled with LEFT exactly like stock
    B.append(_stmt(f"const4({KEY_RIGHT}) B_KEYON"))
    B.append((JMP_IFNOT, "try_left"))
    for k in range(1, d):                                # sel k -> k-1, swap the overlays
        B.append(_stmt(f"Global.Byte[{SCRATCH_SEL}] const({k}) B_EQ"))
        B.append((JMP_IFNOT, f"right_{k}"))
        B.append(opcodes.encode(0x21, spec.cursor_window(k)))          # CloseWindow
        B.append(opcodes.window_async(spec.cursor_window(k - 1), 16, txids[f"cur{k - 1}"]))
        B.append(_stmt(f"Global.Byte[{SCRATCH_SEL}] const({k - 1}) B_LET"))
        B.append((JMP, "after_lr"))
        B.append(label(f"right_{k}"))
    B.append((JMP, "after_lr"))                          # right pressed at sel 0: no-op
    B.append(label("try_left"))
    B.append(_stmt(f"const4({KEY_LEFT}) B_KEYON"))
    B.append((JMP_IFNOT, "after_lr"))
    for k in range(0, d - 1):                            # sel k -> k+1
        B.append(_stmt(f"Global.Byte[{SCRATCH_SEL}] const({k}) B_EQ"))
        B.append((JMP_IFNOT, f"left_{k}"))
        B.append(opcodes.encode(0x21, spec.cursor_window(k)))
        B.append(opcodes.window_async(spec.cursor_window(k + 1), 16, txids[f"cur{k + 1}"]))
        B.append(_stmt(f"Global.Byte[{SCRATCH_SEL}] const({k + 1}) B_LET"))
        B.append((JMP, "after_lr"))
        B.append(label(f"left_{k}"))
    B.append(label("after_lr"))
    # the auto-repeat ramp: held Up counts up, held Down counts down, neither resets
    B.append(_stmt(f"const4({KEY_UP}) B_KEY"))
    B.append((JMP_IFNOT, "ramp_a"))
    B.append(_stmt(f"Global.Int16[{SCRATCH_RAMP}] const(1) B_PLUS_LET"))
    B.append((JMP, "ramp_z"))
    B.append(label("ramp_a"))
    B.append(_stmt(f"const4({KEY_DOWN}) B_KEY"))
    B.append((JMP_IFNOT, "ramp_b"))
    B.append(_stmt(f"Global.Int16[{SCRATCH_RAMP}] const(1) B_MINUS_LET"))
    B.append((JMP, "ramp_z"))
    B.append(label("ramp_b"))
    B.append(_stmt(f"Global.Int16[{SCRATCH_RAMP}] const(0) B_LET"))
    B.append(label("ramp_z"))
    # DOWN step (edge OR ramp == -ARM), else-coupled with UP -- stock's exact structure
    B.append(_stmt(f"const4({KEY_DOWN}) B_KEYON Global.Int16[{SCRATCH_RAMP}] "
                   f"const({-RAMP_ARM}) B_EQ B_OROR"))
    B.append((JMP_IFNOT, "try_up"))
    for k in range(d):
        step = spec.place(k)
        B.append(_stmt(f"Global.Byte[{SCRATCH_SEL}] const({k}) B_EQ"))
        B.append((JMP_IFNOT, f"down_{k}"))
        B.append(_stmt(f"Global.Int16[{SCRATCH_VAL}] const({step}) B_GE"))
        B.append((JMP_IFNOT, "down_done"))               # no room below: no step
        B.append(_stmt(f"Global.Int16[{SCRATCH_VAL}] const({step}) B_MINUS_LET"))
        B.append((JMP, "down_done"))
        B.append(label(f"down_{k}"))
    B.append(label("down_done"))
    B.append(_stmt(f"Global.Int16[{SCRATCH_RAMP}] const({RAMP_PULLBACK}) B_PLUS_LET"))
    B.append((JMP, "step_done"))
    B.append(label("try_up"))
    B.append(_stmt(f"const4({KEY_UP}) B_KEYON Global.Int16[{SCRATCH_RAMP}] "
                   f"const({RAMP_ARM}) B_EQ B_OROR"))
    B.append((JMP_IFNOT, "step_done"))
    for k in range(d):
        step = spec.place(k)
        B.append(_stmt(f"Global.Byte[{SCRATCH_SEL}] const({k}) B_EQ"))
        B.append((JMP_IFNOT, f"up_{k}"))
        B.append(_stmt(_up_guard(spec, step)))
        B.append((JMP_IFNOT, "up_done"))                 # at the ceiling: no step
        B.append(_stmt(f"Global.Int16[{SCRATCH_VAL}] const({step}) B_PLUS_LET"))
        B.append((JMP, "up_done"))
        B.append(label(f"up_{k}"))
    B.append(label("up_done"))
    B.append(_stmt(f"Global.Int16[{SCRATCH_RAMP}] const({RAMP_PULLBACK}) B_MINUS_LET"))
    B.append(label("step_done"))
    B.append(_publish(spec))
    B.append(opcodes.wait(1))
    B.append((JMP, "loop"))
    B.append(label("exit"))
    for sel in range(d):                                 # stock closes every window blind
        B.append(opcodes.encode(0x21, spec.cursor_window(sel)))
    B.append(opcodes.encode(0x21, spec.window))
    if spec.help:
        B.append(opcodes.encode(0x21, HELP_WINDOW))
    B.append(_stmt(f"const4({KEY_CANCEL}) B_KEYON"))     # same-frame edge re-test (stock)
    B.append((JMP_IF, "cancelled"))
    B.append(_stmt(f"Global.Int16[{spec.result}] Global.Int16[{SCRATCH_VAL}] B_LET"))
    if spec.flag is not None:
        B.append(_stmt(f"Global.Bit[{spec.flag}] const(1) B_LET"))
    echo_expr = f"Global.Int16[{SCRATCH_VAL}]"
    if spec.multiplier > 1:
        echo_expr += f" const({spec.multiplier}) B_MULT"
    B.append(opcodes.encode(0x66, 0, exprasm.assemble(echo_expr + " B_EXPR_END"),
                            arg_flags=0b10))
    if spec.echo:
        B.append(opcodes.window_sync(ECHO_WINDOW, 0, txids["echo"]))
    B.append(label("cancelled"))
    B.append(opcodes.RETURN)
    return asm(B)


def entry_bytes(spec: InputSpec, txids: dict) -> bytes:
    """The seated code entry: type 0, tag 0 = a bare return (the object just parks),
    tag :data:`INPUT_TAG` = the stepper. Activate with ``init_code(slot, 0)``."""
    init = bytes(opcodes.RETURN)
    body = stepper_body(spec, txids)
    header = bytes([0x00, 0x02]) + struct.pack("<HHHH", 0, 8, INPUT_TAG, 8 + len(init))
    return header + init + body


def call_bytes(slot: int) -> bytes:
    """The ``[[choice]]`` option's dispatch: block the talk body until the stepper
    returns (REQEW at the house dispatch level)."""
    return opcodes.run_script_sync(DISPATCH_LEVEL, slot, INPUT_TAG)


def recall_bytes(spec: InputSpec) -> bytes:
    """Re-load gMesValue slot 0 from the input's RESULT var (stepped x multiplier) —
    the ``recall`` option key. Slot 0 is TRANSIENT display state shared by every
    stepper's submit echo, so a row that renders ``[NUMB=0]`` at any LATER time
    (the bench's Report row: it showed the previous BID's 3500 as "soldiers")
    must recall from the save-backed ``Global.Int16[result]`` first."""
    expr = f"Global.Int16[{spec.result}]"
    if spec.multiplier > 1:
        expr += f" const({spec.multiplier}) B_MULT"
    return opcodes.encode(0x66, 0, exprasm.assemble(expr + " B_EXPR_END"), arg_flags=0b10)
