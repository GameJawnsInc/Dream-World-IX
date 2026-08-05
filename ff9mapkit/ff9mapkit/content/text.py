"""Author field dialogue text (``.mes``).

Memoria loads field text cumulatively across mods: a mod's
``FF9_Data/embeddedasset/text/<lang>/field/<mesId>.mes`` is merged over the base block, and
explicit ``[TXID=n]`` indices let a mod *add* entries without disturbing the base text — as
long as you use indices the base block doesn't occupy (a high TXID like 500+). That is the
trick proven in Session 9: drop a ``<mesId>.mes`` with our line at a high index; the base
text is untouched, our entry is added, and an NPC's WindowSync(... , txid) resolves to it.

Format of one entry::

    _[TXID=500][STRT=10,1][TAIL=UPR]I miss you Zidane[ENDN]

The leading ``_`` (any non-``[STRT=`` character) is required so the parser treats ``[TXID=]``
as a re-index rather than the start of entry 0.
"""

from __future__ import annotations

import re

# A safe starting index for mod-added dialogue (base field blocks don't use these).
DEFAULT_BASE_TXID = 500

# The DEFAULT talk line for a dialogue-less ``[[npc]]`` (the classic FF9 silent villager). A dialogue-less
# NPC still keeps a talk func, and its ``WindowSync`` needs a txid the NPC OWNS: pointing it at the raw
# allocation base (:data:`DEFAULT_BASE_TXID`) rendered whichever entry allocated that txid first (the
# fort-condor swarm bench: 40 silent NPCs all opened the [[choice]] prompt, dead menu rows included) --
# so the build allocates each one its own line of this through the normal text channel.
DEFAULT_SILENT_TALK = "..."

# The dialogue window's TAIL — the little pointer that aims at the speaker (FF9's "who's talking"
# cue; there's no separate name-box). Codes map to Dialog.TailPosition (FFIXTextTag.GetTailPosition):
#   UPR/UPL upper-right/left · LOR/LOL lower-right/left · UPC/LOC upper/lower-center
#   ...F variants force that corner · DEFT = engine default/auto-position
TAIL_CODES = {"UPR", "UPL", "LOR", "LOL", "UPC", "LOC",
              "UPRF", "UPLF", "LORF", "LOLF", "DEFT"}
DEFAULT_TAIL = "UPR"

# The window STYLE -- the flags byte of WindowSync/WindowAsync (ETb.FlagsToStyles + SetFollow, decoded
# in studies/messages/SURVEY.md §2). Named for the NINE combinations stock actually ships:
#   bubble             128  speech bubble attached to the speaking actor (tail + follow + neck-turn)
#   plain                0  screen-fixed plain panel (system announces, signs, pickers)
#   notail               4  chat-style frame, screen-fixed, no tail (tutorial pages, HUD toasts)
#   transparent         16  frameless floating text (letters, narration overlays, HUD counters)
#   mognet               8  plain panel with the "Mognet" caption (moogle menus)
#   ate                 64  plain panel with the "Active Time Event" caption (ATE titles/pickers)
#   bubble_nopan       160  bubble whose speaker the camera does NOT pan to (QTE prompts, rituals)
#   bubble_notail      132  attached to the actor but tail-less (off-screen voices, "Zzz...")
#   bubble_transparent 144  frameless text floating on the actor (the H&C dig number)
# Captions (mognet/ate) exist only WITHOUT the bubble bit -- the engine drops the caption when 128 is
# set (ETb.cs:170-181), which is why there is no "bubble_ate" name. A raw int 0-255 is accepted for
# engine spelunking; the named forms cover every shipping combination.
STYLE_NAMES = {
    "bubble": 128, "plain": 0, "notail": 4, "transparent": 16, "mognet": 8, "ate": 64,
    "bubble_nopan": 160, "bubble_notail": 132, "bubble_transparent": 144,
}
DEFAULT_STYLE = STYLE_NAMES["bubble"]      # ordinary dialogue -- what every emitter already used


def resolve_style(value, default: int = DEFAULT_STYLE) -> int:
    """Resolve an author ``style`` value (a :data:`STYLE_NAMES` name, or a raw flags int) to the
    WindowSync/WindowAsync flags byte. ``None`` -> ``default`` (byte-identical when unset)."""
    if value is None:
        return default
    if isinstance(value, bool):
        raise ValueError(f"window style must be a name or a flags byte, not a bool ({value!r})")
    if isinstance(value, int):
        if not 0 <= value <= 255:
            raise ValueError(f"window style {value} out of range (a flags byte is 0..255)")
        return value
    name = str(value).strip().lower()
    if name in STYLE_NAMES:
        return STYLE_NAMES[name]
    raise ValueError(f"unknown window style {value!r} -- one of {', '.join(sorted(STYLE_NAMES))} "
                     f"or a raw flags byte 0..255")

# THE SPEAKER CONVENTION (census 2026-07-18: 12,711 stock entries across 33 field blocks). FF9 has no
# name-box; attribution is authored INTO the text, and the real game's form is NOT "Name: line" -- it is
#
#     Name\n“line”        (the name on its own line, then the dialogue in literal curly quotes)
#
# 9,009/12,711 sampled entries (70.9%) use exactly this; ZERO stock entries use a colon join. The
# quotes are ordinary UTF-8 glyphs (U+201C/U+201D -- the engine has no speaker/quote concept at all;
# FFIXTextTagCode/Dialog render them like any letter), opening once on the first dialogue line and
# closing once on the last (wrapped interior lines carry neither). The name may be a literal string
# ("Dali Villager", "Black Waltz No. 1"), a renameable-character tag ([ZDNE]/[VIVI]/... -> the player's
# chosen name), or a variable ([TEXT=0,0] -- the save moogles' own roster identity). Unattributed text
# (28.9% -- system windows, signs, narration) has NO name line and NO quotes. The one stock sibling
# convention: a SILENT THOUGHT is Name\n(line) -- parentheses, no quotes ([ZDNE]\n(Hmm?  She sure is
# dressed funny...)); with_speaker auto-detects a fully-parenthesized line and emits that form.
QUOTE_OPEN = "“"      # “ -- a literal glyph in the entry bytes, not a tag
QUOTE_CLOSE = "”"     # ”

# Dialogue CHOICE text (one entry holds the prompt + the selectable rows). After the prompt, [CHOO]
# starts the option list and each subsequent newline is one selectable row; [MOVE=18,0] indents each
# row so the selection cursor has room (FF9's exact convention -- see Memoria FFIXTextTagCode). So a
# choice entry's text is:  prompt + CHOICE_OPEN + ("\n" + CHOICE_INDENT).join(options).
CHOICE_INDENT = "[MOVE=18,0]"
CHOICE_OPEN = "\n[CHOO]" + CHOICE_INDENT
# [IMME] = IMMEDIATE display: the window pops fully drawn with NO character-by-character type-on. FF9's own
# shop/menu choices use it (e.g. the Treno Weapon Shop's "What can I do for you?" Buy/Sell menu ends in
# [IMME]) so a SELECTOR feels instant, while story dialogue types out. Appended to a choice entry when the
# [[choice]] sets `instant = true` (the World Hub journey menu turns it on).
CHOICE_IMME = "[IMME]"

# --- the save-moogle MENU window shape (stock field 300 txids 3/4/5/6, read from the install) --------
# A save moogle's own windows are not plain dialogue. Stock's menu head is, byte for byte:
#
#     [PCHM=7,6][WDTH=0,2,6,0,-1][IMME][FEED=2][TEXT=0,0]\n[FEED=4]“Can I help you, kupo?”\n[CHOO]...
#
# Three things beyond the ordinary dialogue shape, all decoded from Memoria:
#   * [IMME]  -- the window pops instantly (a selector, not speech). EVERY stock moogle window has it.
#   * [FEED=n] -- DialogBoxSymbols.OnFeed: ``modifiers.extraOffset.x += n * ResourceXMultipier``, i.e. a
#     HORIZONTAL indent, and it is skipped inside the [CHOO] rows (``if (!modifiers.choice)``). Stock
#     indents the name line by 2 and every dialogue line by 4. A PLAIN moogle line (txid 6, the
#     no-tents window) carries [IMME] but NO feed -- feeds ride the CHOICE windows only.
#   * [WDTH=...] -- OnWidths: repeating ``lineIndex, lineWidth, <sub-params...>, -1`` groups, where each
#     ``6,<var>`` sub-param adds the RENDERED width of ``[TEXT=0,<var>]`` and the total feeds
#     ``dialog.WidthHint``. It exists so a window whose speaker is a runtime VARIABLE still reserves the
#     right frame width -- which is exactly what a moogle's roster-name speaker needs.
MENU_FEED_NAME = 2         # [FEED=2] on the speaker line
MENU_FEED_LINE = 4         # [FEED=4] on each dialogue line
_TEXTVAR_RE = re.compile(r"\[TEXT=0,(\d+)\]")
# [MPOS=x,y] -- DialogBoxSymbols.OnDialogPosition: `dialog.Position = new Vector2(x, y)`. Decoded from
# `Dialog.InitializeDialogTransition` (2026-07-18):
#   * setting Position **nulls `this.Po`**, so the window leaves auto-position-near-the-speaker mode
#     and takes the ABSOLUTE branch;
#   * there, `(x, y)` is the window's **TOP-LEFT corner**, y measured DOWN from the top of the content
#     area (`posY = UIContentSize.y - posY - size.y/2` re-centres it), scaled by ResourceYMultipier;
#   * the absolute branch never calls `setTailAutoPosition`, so a pinned window draws NO tail -- which
#     is why stock's own pinned entries (field 300 txids 3/4/5) carry no `[TAIL]` at all, while its
#     unpinned plain lines (6/7) do.
# Stock pins every moogle menu: the option list at (20, 16), the sub-windows at (30, 26). That 16-unit
# headroom is what the MOGNET caption (drawn ABOVE the frame) needs -- an unpinned menu grew a line
# with the faithful speaker form and clipped its caption off the top (in-game 2026-07-18), which is
# exactly the bug the pin prevents. So `[[savepoint]]` pins by DEFAULT; `menu_pos` overrides.
MENU_POS_STOCK = ((20, 16), (30, 26))      # (main option list, sub-windows) -- field 300 txids 3 / 4,5


def menu_pos_tag(pos) -> str:
    """``[MPOS=x,y]`` for a ``(x, y)`` pair, or ``""`` for ``None`` (the engine's own placement)."""
    if not pos:
        return ""
    x, y = (int(v) for v in pos)
    return f"[MPOS={x},{y}]"


# --- COLOUR + GLYPH markup (studies/messages/SURVEY.md §6b, the in-text census) ----------------------
# Colour is the third most-used tag in the shipping game -- 20,438 pushes across all 64 field text
# blocks -- and it is SEMANTIC, not decorative. Counted over the whole corpus, stock colours the parts
# of a line it did NOT author: cyan wraps a substituted name (almost always a [TEXT=0,n]), yellow wraps
# a quantity or an item ("[NUMB=0] Gil", "[ITEM=0]", "Card"). Colour is how FF9 tells the reader "this
# word came out of your save, not the script."
#
# Two laws from the census, both exact:
#   1. every colour push is paired with [HSHD] -- the counts match to the unit (20,438 == 20,438), and
#      Memoria's own importer encodes exactly that pair as its named colour tokens (FieldTags.cs:40-45,
#      "[68C0D8][HSHD]" -> "{Cyan}");
#   2. stock NEVER pops with [-] (zero occurrences) -- it re-pushes C8C8C8 explicitly to close a span.
# So a span is  [CODE][HSHD] ... [C8C8C8][HSHD]  and nothing else is stock-shaped.
#
# ⚠ NOT auto-applied to the system announce box. Stock writes " Received [ITEM=0]! " with NO colour
# (64 sites, one per block) while an item named inside NPC PROSE is wrapped yellow (52 sites). The
# whole box is already non-prose, so there is nothing to distinguish -- and the kit's received box is
# byte-faithful to that shape. Auto-colouring substitutions everywhere would have broken it.
COLOR_WHITE = "C8C8C8"
COLOR_CODES = {                 # the SIX codes that appear in shipping field text, with their counts
    "white": COLOR_WHITE,       # 9,953 -- the restore
    "cyan": "68C0D8",           # 9,603 -- substituted names
    "yellow": "C8B040",         #   404 -- quantities + items
    "pink": "B880E0",           #   246
    "brown": "D06050",          #   210
    "green": "78C840",          #    22
}
# Semantic aliases -- the names that carry the CONVENTION rather than the pigment. Prefer these.
COLOR_ALIASES = {"name": "cyan", "item": "yellow", "amount": "yellow"}
# 909090 grey is in the engine palette and is used ZERO times in field text; it is deliberately absent.

# Button glyphs: [DBTN=NAME] draws the platform's button sprite inline ([CBTN=NAME] honours the
# player's rebinding). These eleven names are every one stock uses, with their corpus counts.
BUTTON_GLYPHS = {"SELECT": 72, "START": 64, "PAD": 52, "SQUARE": 23, "CROSS": 22, "UP": 15,
                 "LEFT": 15, "RIGHT": 15, "CIRCLE": 15, "DOWN": 15, "TRIANGLE": 14}

# ★★ THE SPACE-AFTER-GLYPH LAW (traced from bench 30603 round 3, owner: "two spaces on either side
# still makes it appear uneven... more space on the left than the right"). An inline image does not
# merely overhang -- the engine DELIBERATELY DROPS every space that follows one, in both passes:
#
#   measure  NGUIText.cs:885   if (!isSpace || !afterImage) { currentX += advanceX; ... }
#   print    NGUIText.cs:1081  if (!afterImage || ch != ' ')  { ...draw the glyph... }
#
# `afterImage` is set where the image advances currentX (:820) and is cleared only by a NON-space
# character -- a space skips the whole block without clearing it. So EVERY consecutive space after a
# glyph is swallowed, not just the first: padding to the right is impossible at any width, which is
# exactly the left-heavy asymmetry the playtest saw. `IsSpace` (:660-663) also covers thin (U+2009),
# hair (U+200A) and zero-width (U+200B) spaces, so none of those work either.
#
# This is WHY stock never writes a space after a glyph (§6b: 128 sites use ':' and 192 a following
# tag, zero use a space) -- its legend idiom works precisely because ':' is a non-space character
# that clears the flag. Authors get a lint rather than an invisible no-op.
IMAGE_TAGS = ("DBTN", "CBTN", "KCBT", "JCBT", "ICON", "SPRT")
_SPACE_AFTER_IMAGE = re.compile(r"\[(" + "|".join(IMAGE_TAGS) + r")(?:=[^\]]*)?\][   ​]")


def space_after_glyph_problems(text) -> list:
    """Report each inline-image tag followed by a space -- the engine drops it (see THE
    SPACE-AFTER-GLYPH LAW above), so the author's spacing silently does nothing."""
    return [f"[{m.group(1)}...] is followed by a space, which the engine DROPS (every consecutive "
            f"one, not just the first) -- so this spacing does nothing. Stock's idiom is a colon "
            f"straight after the glyph (\"[{m.group(1)}=CROSS]: Confirm\", 128 sites). A no-break "
            f"space (U+00A0) does survive and renders as a gap (in-game confirmed), but stock never "
            f"writes a glyph mid-sentence at all -- prefer the legend form"
            for m in _SPACE_AFTER_IMAGE.finditer(str(text or ""))]


MARKUP_CLOSE = "{/}"
_MARKUP = re.compile(r"\{(/|[A-Za-z_][A-Za-z0-9_]*)\}")


def resolve_color(name: str) -> str:
    """A markup colour name (or semantic alias) -> its 6-hex code. Raises on an unknown name."""
    key = str(name).strip().lower()
    key = COLOR_ALIASES.get(key, key)
    try:
        return COLOR_CODES[key]
    except KeyError:
        raise ValueError(f"unknown colour {name!r} -- one of "
                         f"{', '.join(sorted(set(COLOR_CODES) | set(COLOR_ALIASES)))}")


def color_span(name: str, text: str) -> str:
    """One stock-shaped colour span: ``[CODE][HSHD]text[C8C8C8][HSHD]``."""
    return f"[{resolve_color(name)}][HSHD]{text}[{COLOR_WHITE}][HSHD]"


def markup_problems(text) -> list:
    """Author-facing problems in a line's ``{colour}...{/}`` markup: unknown names, and a span left
    open at end of line. Unknown ``{...}`` that is NOT a colour name is left ALONE (it may be literal
    prose), so only a recognised-looking-but-wrong name is reported."""
    out, depth = [], 0
    for m in _MARKUP.finditer(str(text or "")):
        tok = m.group(1)
        if tok == "/":
            depth -= 1
            if depth < 0:
                out.append(f"{MARKUP_CLOSE} with no colour span open")
                depth = 0
            continue
        key = tok.strip().lower()
        if key in COLOR_CODES or key in COLOR_ALIASES:
            depth += 1
    if depth > 0:
        out.append(f"{depth} colour span(s) left open -- close each with {MARKUP_CLOSE}")
    return out


def apply_markup(text):
    """Expand ``{colour}...{/}`` spans to stock's ``[CODE][HSHD]...[C8C8C8][HSHD]`` shape.

    A NO-OP on any line without a recognised colour name, so every pre-existing emission stays
    byte-identical. Unrecognised ``{...}`` passes through untouched (it may be literal prose). Runs
    BEFORE wrapping, so the emitted tags measure as zero-width like every other control tag rather
    than eating the line budget."""
    s = str(text)
    if "{" not in s:
        return text
    open_spans = []

    def _sub(m):
        tok = m.group(1)
        if tok == "/":
            if not open_spans:
                return m.group(0)                  # unbalanced; validation reports it
            open_spans.pop()
            return f"[{COLOR_WHITE}][HSHD]"
        key = tok.strip().lower()
        key = COLOR_ALIASES.get(key, key)
        if key not in COLOR_CODES:
            return m.group(0)                      # not a colour -- leave the author's braces alone
        open_spans.append(key)
        return f"[{COLOR_CODES[key]}][HSHD]"

    return _MARKUP.sub(_sub, s)


# --- text-synchronized SIGNALS (studies/messages/SURVEY.md §8) ---------------------------------------
# A signal tag fires when its POSITION IN THE STRING appears on screen -- typewriter-aware, so a tag at
# the end of a line means "this line has finished typing". It writes ETb.gMesSignal, which a script reads
# back as sysvar 8; that is FF9's only text->script clock. Two spellings, and the difference is NOT
# cosmetic:
#   [INCS]    increment    (DialogBoxSymbols.cs:500-505)
#   [SIGL=n]  set to n     (:506-507; the param is a plain Int32 -- OnSignal takes any value, and any
#                           NEGATIVE value increments, so [SIGL=-1] == [INCS])
# ⚠ THE BRACKET-FORM CAVEAT. Memoria has a second, compound tag ALSO called IncreaseSignal that both
# signals AND sets FlagButtonInh (undismissable) -- but it is reachable only from the modern curly
# format (`{IncreaseSignal}`); the ORIGINAL bracket table this kit writes maps the string "INCS" to
# IncreaseSignalEx, which signals and nothing more (FFIXTextTag.cs:343 OriginalTagNames). That is why
# stock's unison entries carry the PAIR `[INCS][TIME=-1]` -- Memoria's own importer collapses exactly
# that pair into the compound token (Import/Fields/FieldTags.cs:45). So an author who wants stock's
# shape needs `hold = true` alongside the signal; emitting the signal alone leaves the window
# dismissable and the player can race the handshake.
SIGNAL_INCREMENT = "+"
HOLD_TAG = "[TIME=-1]"        # FlagButtonInh only -- undismissable, closes only when the script says so

# ★ THE TURBO-CONFIRM LAW (the ENVIRONMENTAL sibling of THE BROADCAST-CONFIRM LAW, SURVEY.md §7a).
# The broadcast law is about a press the PLAYER makes; this one is about a press the ENGINE
# SYNTHESIZES, every frame, with the player's hands off the pad:
#   UIKeyTrigger.Update -> HandleDialogControlKeyPressCustomInput() runs unconditionally on every
#   render frame (UIKeyTrigger.cs:198). Its gate (UIKeyTrigger.cs:834) is
#   `<a dialog-progress key went down> || ShouldTurboDialog(...)`, and ShouldTurboDialog
#   (UIKeyTrigger.cs:974-991) returns TRUE WITH NO KEY DOWN whenever `Configuration.Control
#   .TurboDialog` is on (Memoria.ini [Control] TurboDialog -- DEFAULT 1, so on for everyone),
#   `preventTurboKey` is false, the latched `TurboKey` is set (F9 toggles it, :393-399, no on-screen
#   indicator, persists across field reloads for the whole game session) or RightBumper/Shift is held
#   with a confirm key, AND `DialogManager.IsDialogNeedControl()` is true -- which is merely "some
#   open dialog has FlagButtonInh == false" (DialogManager.cs:422-427). It then calls
#   Dialogs.OnKeyConfirm (:837), which fans out to EVERY active dialog with no filter
#   (DialogManager.cs:334-340), and each Dialog.OnKeyConfirm calls Hide() the moment
#   `currentState == CompleteAnimation && !ignoreInputFlag` (Dialog.cs:789-796).
# SYMPTOM, exactly: the window plays its OPEN animation, the text shows, and it immediately plays the
# CLOSE animation and unwinds the whole handler -- with no input. A CHOICE window is immune by
# accident (UILabel.cs:804-806 sets preventTurboKey while a choice/overlay renders), which is why a
# selector survives and every page opened after it dies.
#
# THE ONE LEVER that blocks the SYNTHESIZED press and leaves the PLAYER's own working: `[NTUR]`
# (NGUIText.NoTurboDialog = "NTUR" -> FFIXTextTagCode.TurboOff -> DialogBoxSymbols.cs:327-329 sets
# UIKeyTrigger.preventTurboKey = true). It is UPSTREAM Memoria, not one of our patches, so it is safe
# on a stock engine. Note what it is NOT: it does not touch FlagButtonInh, so unlike [NFOC]/[TIME=n]
# it does not make the window undismissable -- which matters, because a BLOCKING WindowSync page that
# the player cannot dismiss hangs the script forever on `wait == 254` (EBin.cs:137-148). The flag is
# sticky: nothing clears preventTurboKey until a confirm/cancel is actually delivered
# (UIKeyTrigger.cs:838/849), so one render pass of the tag protects the window for its whole life.
NO_TURBO_TAG = "[NTUR]"

# ★ THE TURBO-INJECTION LAW -- ``ShouldTurboDialog`` HAS TWO ARMS, and the second one is why
# "[NFOC] + poll" is not a fix but a second spelling of the same bug (UIKeyTrigger.cs:974-991):
#
#   ARM A (:981-982)  `if (Dialogs.IsDialogNeedControl()) return true;`  -> the caller (:834-837)
#     fans OnKeyConfirm to EVERY open window and each one Hides unless `ignoreInputFlag`. This is
#     the broadcast arm the law above describes. Beaten by [NTUR], or by [NFOC]/[TIME] (which set
#     FlagButtonInh, so IsDialogNeedControl() reports "needs no control" and the arm is skipped).
#
#   ARM B (:984-988)  reached ONLY when arm A did NOT fire -- i.e. exactly when every open window is
#     dismiss-inhibited:
#         if (VoicePlayer.scriptRequestedButtonPress
#             && ActiveDialogList.Any(Style == WindowStyleAuto || Style == WindowStyleTransparent))
#         { ETb.sKey &= ~Confirm; EventInput.ReceiveInput(Confirm); }
#     It SYNTHESIZES a Confirm into the SCRIPT'S OWN input stream -- and `scriptRequestedButtonPress`
#     is set by ``B_KEYON`` itself (EBin.cs:1080), re-armed every ProcessEvents tick
#     (EventEngine.ProcessEvents.cs:11-14). So a script that inhibits its window and then POLLS for a
#     press reads a press it never got, on frame 1.
#
# Arm B has two independent locks and this module owns both: [NTUR] (``preventTurboKey`` bails at
# :976 BEFORE either arm) and a window STYLE outside the predicate. Style is the primary guard --
# it is structural, needs no tag and no render pass -- because [NTUR] is only re-asserted while a
# label RENDERS (DialogBoxSymbols.cs:327-329 via UILabel.OnFill) and is cleared by any delivered
# confirm/cancel (UIKeyTrigger.cs:838/849), so a fully-typed static page can lose it mid-life.
NO_FOCUS_TAG = "[NFOC]"       # FlagButtonInh = true AND FlagResetChoice = false (DialogBoxSymbols.cs:593-598)

#: The author key that declares a window SCRIPT-POLLED: opened async, held, watched for a real
#: button edge by the script, and closed by the script. :func:`window_polled` reads it through a
#: plain copy so this module's universal call sites do not harvest it into every block's vocabulary.
POLLED_KEY = "polled"

#: The authoring lanes that WIRE :data:`POLLED_KEY`. Both reach ``content.choice.option_body``,
#: which is the ONLY call site in the kit that emits ``content.event.polled_window``.
#:
#: ⚠ THE KEY IS READ EVERYWHERE AND WIRED ONLY HERE, and that gap was a live softlock mint:
#: :func:`window_polled` runs from :func:`dress_window`, which every dialogue-bearing block routes
#: through, so ``[[npc]] polled = true`` defaulted ``[NFOC]`` ON -- onto a BLOCKING ``WindowSync``
#: with no script close -- while the schema lint told the author the build never read the key.
#: The plain-copy read keeps ``polled`` out of those blocks' harvested VOCAB; it does NOT make the
#: key inert. ``build.validate`` REFUSES it outside these lanes (:func:`polled_lane_problem`).
POLLED_LANES = ("[[choice.options]]", "[ate] options")

#: The two ``Dialog.WindowStyle`` values arm B's predicate names (Dialog.cs:1921-1927).
TURBO_INJECTABLE_STYLES = ("WindowStyleAuto", "WindowStyleTransparent")


def window_style_of(flags: int) -> str:
    """The ``Dialog.WindowStyle`` a flags byte resolves to -- ``ETb.FlagsToStyles`` (ETb.cs:167-186)
    transcribed, not a lookup table, so a raw flags int an author spells for engine spelunking is
    classified by the engine's own rule rather than by whichever named combinations we listed.

    The engine picks Auto when bit 128 is set (else Plain, with the mognet/ate captions), and THEN
    overrides: bit 16 -> Transparent, else bit 4 -> NoTail. That ordering is why 144
    (``bubble_transparent``) is Transparent and 132 (``bubble_notail``) is NoTail."""
    style = "WindowStyleAuto" if int(flags) & 128 else "WindowStylePlain"
    if int(flags) & 16:
        return "WindowStyleTransparent"
    if int(flags) & 4:
        return "WindowStyleNoTail"
    return style


def turbo_injectable(flags: int) -> bool:
    """True when a window opened with these flags sits INSIDE arm B's predicate -- i.e. a script
    that polls ``B_KEYON`` while this window is open and inhibited will read a synthesized Confirm.
    Of the nine named styles the exposed set is exactly ``bubble`` 128, ``transparent`` 16,
    ``bubble_transparent`` 144 and ``bubble_nopan`` 160; ``plain`` 0, ``notail`` 4, ``mognet`` 8,
    ``ate`` 64 and ``bubble_notail`` 132 are safe."""
    return window_style_of(flags) in TURBO_INJECTABLE_STYLES


def window_polled(src: dict) -> bool:
    """Whether this block declares its window SCRIPT-POLLED (:data:`POLLED_KEY`).

    Read through a PLAIN COPY, for the same reason :func:`body_text` is: this runs from
    :func:`dress_window`, which every dialogue-bearing block routes through at ``collect_text``, and
    ``src.get`` on a live tree is a schema PROBE (``fieldschema._Spy.get``). Probing here would
    harvest ``polled`` into the vocabulary of ``[[npc]]``, ``[[prop]]``, ``[cutscene]`` and every
    other block that does NOT wire it. ``dict(src)`` records nothing (``fieldschema._Spy``
    docstring) and the values are unchanged.

    ⚠ WHAT THE PLAIN COPY DOES **NOT** DO. It hides the key from the harvested VOCAB; it does not
    make it inert. This function still returns True for ``[[npc]] polled = true``, and
    :func:`want_no_focus` still defaults ``[NFOC]`` on from it -- onto a BLOCKING ``WindowSync``
    with no script close, i.e. the ``wait == 254`` softlock. Only :data:`POLLED_LANES` WIRE the
    key; ``build.validate`` refuses it everywhere else (:func:`polled_lane_problem`)."""
    if isinstance(src, dict):
        return bool(dict(src).get(POLLED_KEY))
    return False


# The tags that already make a window immune to the confirm fan-out because they set
# Dialog.FlagButtonInh (DialogBoxSymbols.cs:593-598 NoFocus, :811-829 OnTime): such a window reports
# "needs no control", so ShouldTurboDialog's IsDialogNeedControl() gate never opens for it.
# ⚠ INHIBITED IS NOT SAFE, IT IS ARM A SAFE. Inhibiting every open window is the precondition arm B
# waits for -- see THE TURBO-INJECTION LAW above.
_TURBO_INHIBITORS = (NO_TURBO_TAG, NO_FOCUS_TAG, "[TIME=")

# The tags that render a LIVE VALUE into the window -- gMesValue via [NUMB=n], a text-table string via
# [TEXT=bank,slot], an item name via [ITEM=n]. A window carrying one of these is a READOUT: the player
# opened it to READ A NUMBER, so an auto-skip does not "speed up the story", it deletes the feature.
# That is the class the kit turbo-proofs by default (:func:`dress_window`).
_VALUE_TAG_RE = re.compile(r"\[(?:NUMB|TEXT|ITEM)=")


def renders_live_value(line: str) -> bool:
    """True when ``line`` renders a runtime value ([NUMB=]/[TEXT=]/[ITEM=]) -- i.e. it is a READOUT
    window whose whole point is to be read. See :data:`NO_TURBO_TAG`."""
    return bool(_VALUE_TAG_RE.search(str(line or "")))


def turbo_skippable(line: str) -> bool:
    """True when ``line`` carries NO turbo inhibitor, so a turbo session's synthesized confirm
    (:data:`NO_TURBO_TAG`) closes the window the instant it finishes typing."""
    s = str(line or "")
    return not any(t in s for t in _TURBO_INHIBITORS)


def window_inhibited(src: dict, line: str) -> bool:
    """True when this window is immune to the confirm FAN-OUT (arm A) -- the author wrote an
    inhibitor tag into the text, or ``no_focus`` / ``hold`` / ``duration = n>=1`` will append a tag
    that sets ``Dialog.FlagButtonInh``. (``duration = 0`` is the engine's third mode -- it CLEARS
    FlagButtonInh, so it inhibits nothing.)

    ⚠ READ THE NAME NARROWLY. "Inhibited" means arm A cannot reach this window; it is precisely the
    state arm B is written to act on (THE TURBO-INJECTION LAW above). It is not "turbo-proof"."""
    if not turbo_skippable(line):
        return True
    if src.get("no_focus") or src.get("hold"):
        return True
    d = src.get("duration")
    return d is not None and not isinstance(d, bool) and int(d) != 0


# The key each dialogue-bearing block carries its authored BODY under. Kept here, not in build, so the
# emitter (dress_window) and the validator score the same string.
BODY_KEYS = ("dialogue", "message", "reply", "say", "open", "text")


def body_text(src: dict) -> str:
    """The authored body of a dialogue-bearing block -- the string BEFORE the speaker prefix. The
    readout test reads this, never the speaker-dressed line: a variable speaker is itself a
    ``[TEXT=bank,slot]`` tag, and scoring that as a readout would turbo-proof every named-speaker
    window in the kit.

    Read through a PLAIN COPY on purpose. This is the one place in the kit that asks a block about
    keys it may not own -- an ``[[npc]]`` has no ``reply``, a choice option has no ``dialogue`` --
    and ``src.get`` on a live tree is a schema PROBE (fieldschema._Spy.get), so probing all six here
    would harvest ``reply``/``say``/``open`` into ``[[npc]]``'s vocabulary and silently bless
    ``[[npc]] reply = "..."`` as a legal key. ``dict(src)`` is the documented exhaustive read: it
    records nothing (fieldschema._Spy docstring), and the values are unchanged."""
    if isinstance(src, dict):
        plain = dict(src)
        for k in BODY_KEYS:
            v = plain.get(k)
            if isinstance(v, str):
                return v
    return ""


def want_no_turbo(src: dict, line: str) -> bool:
    """Whether :func:`dress_window` emits :data:`NO_TURBO_TAG` for this window.

    Default ON for a READOUT and for a SCRIPT-POLLED window, OFF otherwise; an explicit
    ``no_turbo`` wins over every default; a tag already present in the authored text is never
    duplicated.

    ⚠ THE ORDER OF THE FIRST TWO TESTS IS THE FIX, and it used to be backwards. The rule opened
    with ``if window_inhibited(...): return False`` -- "a second inhibitor buys nothing" -- which
    silently discarded an EXPLICIT ``no_turbo = true`` and, worse, guaranteed that the one shape
    that NEEDS [NTUR] could never get it. An inhibited window is arm-A-safe and is exactly what arm
    B acts on (THE TURBO-INJECTION LAW), so `inhibited AND turbo-proof` was unrepresentable in the
    kit: a page carrying ``no_focus``/``hold`` and a ``B_KEYON`` poll read a synthesized Confirm on
    frame 1 and closed itself, with a NEW mechanism and the SAME symptom as the broadcast bug.

    What did NOT change: an inhibited window with no explicit key and no poll still gets nothing
    (a second arm-A inhibitor really does buy nothing), and a plain narrative window is still
    turbo-skippable like the base game's."""
    if NO_TURBO_TAG in str(line or ""):
        return False                    # already carried in the authored text -- no second copy
    v = src.get("no_turbo")
    if v is not None:
        return bool(v)                  # an explicit key wins, inhibited or not
    if window_polled(src):
        return True                     # arm B fires ONLY at a polled+inhibited window
    if window_inhibited(src, line):
        return False
    return renders_live_value(body_text(src))


def want_no_focus(src: dict, line: str) -> bool:
    """Whether :func:`dress_window` emits :data:`NO_FOCUS_TAG`. Default ON for a SCRIPT-POLLED
    window (it is the script, not a press, that closes it), OFF otherwise; an explicit ``no_focus``
    wins; a tag already in the authored text is never duplicated."""
    if NO_FOCUS_TAG in str(line or ""):
        return False
    v = src.get("no_focus")
    if v is not None:
        return bool(v)
    return window_polled(src)


#: Every way an author can put ``Dialog.FlagButtonInh`` on a window, as ``(key, the tag it emits)``
#: and the literal spellings of those tags. ONE table, read by :func:`hold_sources`, so a new
#: inhibitor key cannot be added to :func:`dress_window` without landing in the softlock rule too.
#: ``duration`` is deliberately absent: ``[TIME=n>0]`` auto-closes, so the window ends on its own
#: and the blocked script is released (``duration = 0`` clears the flag outright).
HOLD_KEYS = (("hold", HOLD_TAG), ("no_focus", NO_FOCUS_TAG))
HOLD_LITERALS = (HOLD_TAG, NO_FOCUS_TAG)


def hold_sources(src: dict, body: str) -> list:
    """Every reason this window would ship dismiss-INHIBITED, named the way the author spelled it
    (a key, or the literal tag written straight into the body). Empty list = the player's own
    Confirm can still close it."""
    out = [f"`{key} = true` ({tag})" for key, tag in HOLD_KEYS if src.get(key)]
    out += [f"a literal {tag} in the text" for tag in HOLD_LITERALS if tag in str(body or "")]
    return out


def sync_hold_problems(src: dict, body: str) -> list:
    """★ THE SYNC-HOLD SOFTLOCK RULE -- returns message tails (the caller prefixes the block's
    identity), empty when the window is safe.

    Score this on any block whose window is a BLOCKING ``WindowSync`` (0x1F) that no script close
    follows -- which is every ordinary dialogue block in the kit: ``[[npc]]``, ``[[prop]]``,
    ``[[event]]``, ``[[on_entry]]``, ``[[coop]]``, a ``[[choice]]`` prompt, a cutscene ``say`` step,
    and any option ``reply`` that is not :data:`POLLED_KEY`. ``WindowSync`` parks the script on
    ``gCur.wait = 254`` and the engine's ONLY escape is ``!ETb.MesWinActive(winnum)``, i.e. the
    window closing (EBin.cs:137-148) -- while every :data:`HOLD_KEYS` tag makes
    ``Dialog.OnKeyConfirm``'s ``!this.ignoreInputFlag`` guard false (Dialog.cs:789), so NO press can
    ever close it. The field hangs with a window up and control locked.

    ⚠ UNCONDITIONAL. It does not depend on turbo, on ``instant``, or on what the player does -- and
    it is the reason the rule cannot live in the ``[[choice]]`` option loop where it was born: the
    keys are universal (``no_focus`` was added to the VOCAB of npc/prop/event/cutscene steps in the
    same change that linted only choice replies), so an ``[[npc]] no_focus = true`` validated clean
    and shipped the hang. The legitimate homes are the two shapes that close their own window: a
    cutscene ``open`` step (async + an explicit ``close``) and a :data:`POLLED_KEY` reply."""
    srcs = hold_sources(src, body)
    if not srcs:
        return []
    return [f": {' and '.join(srcs)} on a BLOCKING window is an unconditional SOFTLOCK. The window "
            f"is a WindowSync (0x1F), which parks the script on gCur.wait == 254 until the window "
            f"closes (EBin.cs:137-148), and FlagButtonInh means Dialog.OnKeyConfirm never closes it "
            f"(Dialog.cs:789) -- no press, ever. Drop the hold and let the player dismiss it, or "
            f"move the line to a shape that closes its own window: a cutscene `open` step (with a "
            f"matching `close`), or a reply with `polled = true` ({' / '.join(POLLED_LANES)})."]


def polled_lane_problem(label: str) -> str:
    """The refusal for :data:`POLLED_KEY` on a block that does not WIRE it (:data:`POLLED_LANES`).

    Not a style nit: the key is READ on every block (:func:`window_polled` runs from
    :func:`dress_window`) and defaults ``[NFOC]`` on, so an unwired ``polled = true`` ships the
    exact :func:`sync_hold_problems` softlock with none of the async machinery that makes it safe."""
    return (f"{label}: `{POLLED_KEY}` is not wired on this block -- it is read only by "
            f"{' and '.join(POLLED_LANES)}, which route through content.choice.option_body and "
            f"emit the async open + B_KEYON poll + script close. Here it is NOT ignored: "
            f"content.text.window_polled runs from dress_window on every dialogue block, so it "
            f"would default [NFOC] onto a BLOCKING WindowSync with no close -- the gCur.wait == 254 "
            f"hang (EBin.cs:137-148). Drop the key, or move this line to an option reply.")


#: Tags that break the polled-page primitive, each in a different in-game-only way. Checked by
#: :func:`polled_window_problems`, never by the emitter -- the .eb shape and the .mes entry are
#: produced by two lanes that only meet at build, so no single emitter can make these unrepresentable.
#:
#: ⚠ KEYED ON THE MATCH TOKEN, NOT THE PRETTY NAME. A PARAMETERISED tag must be keyed by its
#: ``[NAME=`` prefix, because that is the only form that exists in the bytes: this table shipped
#: with a valueless ``"[WDTH]"`` key, which the engine never writes and the kit never emits
#: (:func:`width_hint` emits ``[WDTH=0,...]``), so that arm COULD NOT FIRE and a real
#: ``[WDTH=0,69,14,0,-1]`` reached a shipped polled entry with ``validate`` silent -- a check that
#: cannot fail. :func:`polled_window_problems` prints a ``[NAME=...]`` form for these keys.
POLL_FORBIDDEN_TAGS = {
    "[IMME]": ("the reply pops fully drawn, so the very confirm that PICKED the row finds a "
               "finished window and dismisses it on arrival (THE BROADCAST-CONFIRM LAW)"),
    "[PAGE]": ("CloseWindow TURNS THE PAGE instead of closing on a paged entry "
               "(Dialog.Hide short-circuits while pages remain, Dialog.cs:616-624), so the poll's "
               "close leaves a live window behind"),
    # NOT a width rule -- [WDTH] IS DUMMIED (studies/messages/SURVEY.md:144): ApplyFormatTag
    # consumes it and does nothing ("Unused anymore... variable width is now automatically
    # handled", DialogBoxSymbols.cs:650-653) and the OnWidths body :905-935 is dead. The refusal
    # is about keeping a DEAD tag out of the one entry whose geometry has to be reasoned about
    # exactly: a polled page bakes its size ONCE, at the async open, from the values published
    # just before it (Dialog.AutomaticSize) -- an inert width hint in that entry reads like the
    # thing that sized it and sends the next author debugging a tag the engine ignores.
    "[WDTH=": ("that tag is DUMMIED. ApplyFormatTag consumes it and does nothing "
               "(DialogBoxSymbols.cs:650-653, \"Unused anymore... variable width is now "
               "automatically handled\"; the OnWidths body :905-935 is dead -- "
               "studies/messages/SURVEY.md:144), so it sizes NOTHING. On a polled page that makes "
               "it a dead tag standing exactly where the real mechanism is: the width bakes ONCE, "
               "at the async open, from the values published just before it "
               "(Dialog.AutomaticSize). Delete it"),
}
_TIME_TAG_RE = re.compile(r"\[TIME=(-?\d+)\]")


def _forbidden_tag_label(tag: str) -> str:
    """How a :data:`POLL_FORBIDDEN_TAGS` key is SHOWN to the author -- a match prefix like
    ``"[WDTH="`` prints as ``[WDTH=...]``, a whole tag prints as itself."""
    return f"{tag}...]" if tag.endswith("=") else tag


def polled_window_problems(src: dict, entry: str) -> list:
    """THE POLLED-PAGE RULEBOOK, in one place -- returns message tails (the caller prefixes the
    row's identity). ``entry`` is the DRESSED ``.mes`` body (what :func:`dress_window` emits), so
    the rules score the bytes that ship rather than the keys that produced them.

    Four independent failure modes, and none of them is visible offline without this:

      * no ``[NTUR]`` -> arm B injects a Confirm into the script's own input stream and the poll
        exits on frame 1;
      * no ``[NFOC]`` -> arm A's fan-out hides the window before the poll ever runs;
      * a forbidden tag (:data:`POLL_FORBIDDEN_TAGS`);
      * ``[TIME=n]`` with ``n >= 0`` -- ``n > 0`` auto-closes and races the poll, and ``n == 0`` is
        the engine's THIRD mode: it CLEARS FlagButtonInh (DialogBoxSymbols.cs:811-829), undoing the
        very hold this window depends on.

    The STYLE rule is separate and lives at the emitter as well (``content.event.polled_window``
    refuses an injectable style outright): a style inside arm B's predicate is the one guard that
    can be made structurally unrepresentable."""
    out = []
    for tag, why in (("[NTUR]", "arm B (UIKeyTrigger.cs:984-988) SYNTHESIZES a Confirm into the "
                                "script's own input stream at an inhibited window while a B_KEYON "
                                "poll is armed, so the poll exits on frame 1 with no press"),
                     ("[NFOC]", "arm A (UIKeyTrigger.cs:981-982 -> DialogManager.cs:335-341) fans "
                                "a confirm to every open window and Dialog.cs:789 hides this one "
                                "the moment it finishes typing, before the poll can see anything")):
        if tag not in entry:
            out.append(f"is script-polled but its .mes entry carries no {tag} -- {why}. "
                       f"The polled shape needs BOTH tags and a poll-safe style.")
    for tag, why in POLL_FORBIDDEN_TAGS.items():
        if tag in entry:
            out.append(f"is script-polled and its .mes entry carries "
                       f"{_forbidden_tag_label(tag)} -- {why}.")
    for m in _TIME_TAG_RE.finditer(entry):
        if int(m.group(1)) >= 0:
            out.append(f"is script-polled and its .mes entry carries {m.group(0)} -- "
                       f"[TIME=n>0] auto-closes and races the poll; [TIME=0] CLEARS FlagButtonInh "
                       f"(DialogBoxSymbols.cs:811-829) and un-holds the window. A polled window is "
                       f"closed by its own script, so it needs no timer at all.")
    try:
        flags = resolve_style(src.get("style"))
    except ValueError:
        return out                      # the bad style is reported by the style rule itself
    if turbo_injectable(flags):
        out.append(
            f"is script-polled with window style {flags} ({window_style_of(flags)}) -- that is "
            f"INSIDE arm B's predicate (UIKeyTrigger.cs:984 tests `Style == WindowStyleAuto || "
            f"Style == WindowStyleTransparent`), so a latched F9 resolves the poll with no press. "
            f"Use a poll-safe style: plain (0), notail (4), mognet (8), ate (64) or "
            f"bubble_notail (132). Style is the STRUCTURAL guard -- [NTUR] is only re-asserted on "
            f"a label render pass and is cleared by any delivered confirm.")
    return out


def signal_tag(value) -> str:
    """The text-side signal tag for an author ``signal`` value: ``"+"`` (or a negative int) ->
    ``[INCS]``; an int ``n >= 0`` -> ``[SIGL=n]``. ``None``/``False`` -> ``""``."""
    if value is None or value is False:
        return ""
    if value is True or (isinstance(value, str) and value.strip() == SIGNAL_INCREMENT):
        return "[INCS]"
    n = int(value)
    return "[INCS]" if n < 0 else f"[SIGL={n}]"


def dress_window(src: dict, line: str):
    """Apply a dialogue block's TEXT-side window-attribute keys to an assembled (already speaker-
    attributed, already wrapped) line. Returns ``(line, strt, tail)`` for the ``.mes`` entry:

    * ``window_pos = [x, y]`` -> a leading ``[MPOS=x,y]`` pin (top-left, y measured DOWN). Pinning
      DETACHES the window from any speaker (the engine nulls ``Po``) and a pinned window draws NO
      tail -- so with no explicit ``tail`` the entry ships tail-less, like stock's own pinned windows.
    * ``speed = n``   -> ``[SPED=n]`` (typewriter speed; engine default ticks {4,7,10,...}).
    * ``instant``     -> ``[IMME]`` (pop fully drawn -- FF9's selector/system-window convention).
    * ``duration = n`` -> a trailing ``[TIME=n]`` (auto-close after n frames; the player cannot
      dismiss it early -- the engine sets FlagButtonInh). A WindowSync + duration = a timed beat.
      ``duration = 0`` is the engine's third mode: it CLEARS FlagButtonInh, re-granting dismissal
      to a window some earlier tag inhibited (``OnTime`` DialogBoxSymbols.cs:811-829).
    * ``hold = true`` -> a trailing ``[TIME=-1]``: undismissable with no auto-close, so the window
      stands until the SCRIPT closes it. The half of stock's unison shape that keeps the player
      from racing a signal handshake.
    * ``signal = "+" | n`` -> a trailing :func:`signal_tag` (``[INCS]`` / ``[SIGL=n]``), which fires
      when the line finishes typing. Placed BEFORE the time tag so the signal lands with the last
      glyph rather than after the close.
    * ``box = [w, lines]`` -> the ``[STRT]`` geometry. NB the engine auto-measures WIDTH whenever it
      can (``AutomaticSize``); ``w`` only matters on the no-autoresize paths, ``lines`` is a MINIMUM.
    * ``no_turbo`` -> ``[NTUR]`` (:data:`NO_TURBO_TAG`) -- THE TURBO-CONFIRM LAW. **Defaults to ON for
      a READOUT window** (one that renders [NUMB=]/[TEXT=]/[ITEM=], :func:`renders_live_value`),
      because a turbo session synthesizes a confirm EVERY FRAME and closes any such window the instant
      it finishes typing, with no player input at all. Set ``no_turbo = false`` to opt a readout back
      out (validate then refuses it -- an opt-out of a law has to be loud, not silent); set
      ``no_turbo = true`` on a plain narrative window to protect that one too. Already dismiss-
      inhibited ([NFOC] / a ``hold`` / a ``duration``) and NOT polled -> nothing is added, arm A
      cannot reach that window anyway. This is the ONLY inhibitor that does not also set
      FlagButtonInh, i.e. the only one that keeps the player's own Confirm working -- and a blocking
      WindowSync page the player cannot dismiss hangs the script on ``wait == 254``
      (EBin.cs:137-148).
    * ``no_focus`` -> ``[NFOC]`` (:data:`NO_FOCUS_TAG`) -- ``Dialog.FlagButtonInh = true`` AND
      ``FlagResetChoice = false`` (DialogBoxSymbols.cs:593-598). The window can then be closed only
      by the script, so it belongs on an ASYNC open with an explicit close; on a blocking
      ``WindowSync`` it is an unconditional softlock (``wait == 254`` forever) and ``validate``
      refuses it on EVERY such block (:func:`sync_hold_problems`, run from the one window sweep
      each dialogue-bearing block passes -- not just on a choice reply, where the rule was born).
      **Defaults to ON for a ``polled`` window.**
    * ``polled`` (:data:`POLLED_LANES`) -> the reply is opened ASYNC, held, watched for a real
      button edge and closed by the script (``content.event.polled_window``). It defaults both
      ``no_turbo`` and ``no_focus`` ON -- the two text-side halves of THE TURBO-INJECTION LAW -- and
      ``validate`` re-checks the emitted entry (:func:`polled_window_problems`), because the .eb
      shape and the .mes entry are built by two lanes that meet only at build time. The key is READ
      here on every block but WIRED only in those lanes, so ``validate`` refuses it anywhere else
      (:func:`polled_lane_problem`) rather than letting it default an [NFOC] hang.

    Every key absent -> ``(line, None, src.get("tail"))``, byte-identical to the pre-key layout, unless
    the line is a readout (then it gains ``[NTUR]`` -- see above)."""
    pre = menu_pos_tag(src.get("window_pos"))
    if src.get("speed") is not None:
        pre += f"[SPED={int(src['speed'])}]"
    if src.get("instant"):
        pre += CHOICE_IMME
    # ★ THE TURBO-CONFIRM LAW, applied at the call site EVERY dialogue-bearing block routes through
    # (build.collect_text._add). A docstring rule would be a wish: the tag has to be emitted here or
    # authors ship turbo-skippable readouts and never learn why their page vanished.
    if want_no_turbo(src, line):
        pre += NO_TURBO_TAG
    # ...and its structural partner. [NFOC] holds the window against arm A's fan-out AND sets
    # FlagResetChoice = false, so a page opened from a selector does not clobber the pending
    # sysvar-9 answer. Emitted AFTER [NTUR] so a polled entry reads `[NTUR][NFOC]<body>`.
    if want_no_focus(src, line):
        pre += NO_FOCUS_TAG
    suf = signal_tag(src.get("signal"))
    if src.get("hold"):
        suf += HOLD_TAG
    elif src.get("duration") is not None:
        suf += f"[TIME={int(src['duration'])}]"
    strt = tuple(int(v) for v in src["box"]) if src.get("box") is not None else None
    return pre + line + suf, strt, default_tail(src)


def default_tail(src: dict):
    """The tail an entry ships when the author sets none. THE WINDOW-GEOMETRY LAW (three playtest
    bugs): on a window with NO attached actor, a ``[TAIL]`` code is a screen-CORNER anchor -- the
    dialogue default ``UPR`` pins a system box to a corner instead of centering it. So a PINNED
    (``window_pos``) or DETACHED-style window (a non-bubble ``style``: plain/notail/transparent/
    caption) ships **tail-less** like stock's own centered system windows (the grey-ATE title, the
    pinned moogle menus); everything else keeps the dialogue default. An explicit ``tail`` always
    wins (a corner anchor on a plain window is legitimate -- stock's air-cab picker)."""
    tail = src.get("tail")
    if tail is not None:
        return tail
    if src.get("window_pos") is not None:
        return ""                                  # pinned -> no [TAIL] tag (stock's pinned shape)
    if src.get("style") is not None:
        try:
            if not resolve_style(src.get("style")) & 128:
                return ""                          # detached style -> centered, tail-less
        except ValueError:
            pass                                   # validate already reported the bad style
    return None                                    # the dialogue default (UPR) applies downstream


def width_hint(speaker, base: int = MENU_FEED_NAME) -> str:
    """The ``[WDTH]`` frame-width hint for a window whose SPEAKER is a runtime variable
    (``[TEXT=0,n]``) -- ``""`` for a literal name (the engine measures those itself). ``base`` is the
    line's fixed width; stock uses its own feed indent (2) for the name line."""
    m = _TEXTVAR_RE.fullmatch(str(speaker or "").strip())
    return f"[WDTH=0,{int(base)},6,{m.group(1)},-1]" if m else ""


def menu_style(text: str, *, speaker=None, feeds: bool = True) -> str:
    """Dress an already-attributed (and already-wrapped) line as a save moogle's OWN window: the
    ``[WDTH]`` hint when the speaker is a variable, ``[IMME]``, and -- for a CHOICE window
    (``feeds=True``) -- stock's per-line ``[FEED]`` indents (the name line 2, every other line 4).

    Runs AFTER :func:`wrap_text` so each wrapped line gets its own indent, exactly as stock's own
    multi-line moogle windows do (field 300 txid 5 feeds both lines of its tent prompt). Stock's tag
    order is ``[MPOS][PCHC/PCHM][WDTH][IMME][FEED]``; the caller composes the leading two (see
    :func:`menu_pos_tag`) and this supplies everything from ``[WDTH]`` on."""
    lines = str(text).split("\n")
    if feeds:
        named = bool(speaker) and len(lines) > 1
        lines = [f"[FEED={MENU_FEED_NAME if (named and i == 0) else MENU_FEED_LINE}]{ln}"
                 for i, ln in enumerate(lines)]
    return width_hint(speaker) + CHOICE_IMME + "\n".join(lines)


def with_speaker(speaker, text: str) -> str:
    """Attribute a dialogue line the way the real game does (see the SPEAKER CONVENTION note above)::

        with_speaker("Vivi", "Hello.")   -> "Vivi\\n“Hello.”"      the spoken form
        with_speaker("Vivi", "(Hmm...)") -> "Vivi\\n(Hmm...)"      a fully-parenthesized line = a
                                                                    silent thought -- parens, no quotes
        with_speaker(None, anything)     -> unchanged               narration/system: no name, no quotes

    Colour markup (``{item}Ore{/}``) is expanded here, before any wrapping, so it applies at every
    prose site that attributes a line and its emitted tags measure zero-width. A line with no
    recognised ``{colour}`` name comes through byte-identical.

    ``speaker`` may be a literal name, a renameable-character tag (``[ZDNE]``/``[VIVI]``/...), or a
    variable like ``[TEXT=0,0]``. Auto-wrap composes cleanly: the ``\\n`` makes the name its own
    segment, and the quotes glue to the first/last words so a wrapped body keeps ONE quote pair
    spanning all its lines -- exactly the stock shape. (An audible hushed aside -- stock's rare
    ``“(Kupo!)”`` -- is unattributed in the wild; author it as literal text with your own quotes.)"""
    if not speaker:
        return apply_markup(text)
    t = apply_markup(str(text))
    if t.startswith("(") and t.endswith(")"):
        return f"{speaker}\n{t}"                        # the silent-thought convention
    return f"{speaker}\n{QUOTE_OPEN}{t}{QUOTE_CLOSE}"


def mes_entry(text: str, txid: int, *, strt: tuple = (10, 1), tail: str = DEFAULT_TAIL) -> str:
    """One ``.mes`` entry line that ADDS dialogue at ``txid`` without touching base text. A falsy ``tail``
    (``""``/``None``) emits NO ``[TAIL]`` tag -- matching FF9's CENTERED system windows (a real grey-ATE title
    window has no tail; a ``[TAIL]`` like ``DEFT``/``UPR`` would nudge it off the true centre)."""
    strt_s = ",".join(str(v) for v in strt)
    tail_s = f"[TAIL={tail}]" if tail else ""
    return f"_[TXID={txid}][STRT={strt_s}]{tail_s}{text}[ENDN]"


def txid_map(count: int, *, start_txid: int = DEFAULT_BASE_TXID) -> dict:
    """``{position: TXID}`` for ``count`` sequentially-built entries -- **THE assignment rule, with one
    owner**. :func:`build_mes` computes its mapping from here, so a caller that needs an entry's txid
    *before* the body exists cannot drift from what ``build_mes`` will actually assign.

    That caller is real: a ``[[text_table]]`` bank is referenced by ``[TEXT=<bank>,slot]`` tags inside
    OTHER lines, so the reference has to be substituted into the line text before the body is built --
    i.e. the txid must be known one step earlier than ``build_mes`` returns it. Re-deriving
    ``start_txid + i`` at that call site would be a second copy of the rule, and the failure mode of a
    drifted copy is an off-by-one bank that renders the WRONG TABLE or a blank line in-game."""
    return {i: start_txid + i for i in range(int(count))}


def build_mes(lines, *, start_txid: int = DEFAULT_BASE_TXID, tails=None, strts=None) -> tuple[str, dict]:
    """Build a ``.mes`` file body from an ordered list of dialogue strings.

    Returns ``(text, mapping)`` where ``mapping[i]`` is the TXID assigned to ``lines[i]`` (so a
    caller can point each NPC's WindowSync at the right id). TXIDs are ``start_txid + i``
    (:func:`txid_map`).
    ``tails`` (optional) is a per-line list of TAIL codes; ``None``/missing entries use
    :data:`DEFAULT_TAIL`. ``strts`` (optional) is a per-line ``(x, y)`` window geometry; ``None``/missing
    entries use ``mes_entry``'s default ``(10, 1)`` -- so existing callers stay byte-identical. (A FF9
    *system* window like the chest's item-get box auto-CENTERS from its ``[STRT=width,lines]``, so it must
    pass its real geometry, not the dialogue default.)
    """
    entries = []
    mapping = txid_map(len(lines), start_txid=start_txid)
    for i, line in enumerate(lines):
        txid = mapping[i]
        _t = tails[i] if (tails and i < len(tails)) else None
        tail = DEFAULT_TAIL if _t is None else _t          # None = unspecified -> default; "" = explicit NO tail
        strt = (strts[i] if strts and i < len(strts) and strts[i] else (10, 1))
        entries.append(mes_entry(line, txid, strt=strt, tail=tail))
    return "\n".join(entries) + "\n", mapping


def build_mes_fixed(fixed, *, tails=None, strts=None) -> str:
    """Build ``.mes`` entries at EXPLICIT txids, from ``[(txid, text), ...]``.

    :func:`build_mes` assigns ``start_txid + i`` -- fine for authored dialogue, which lives at 500+ to
    stay clear of a base block. But FF9's own save-Moogle windows reference **low, fixed** ids: the
    moogle-name roster is text entry **0**, the option menu **3**, the save confirm **4**, the Mognet
    submenu **8**, the mail list **11-18**. Reproducing that menu means emitting those exact ids, which
    sequential assignment cannot express.

    **Only legal in a field's OWN minted text block** (``[field] text_block = <fresh id>`` +
    ``register_text_block = true``). A fresh mesID has no base ``.mes`` at all -- ``FF9TextTool.
    GetFieldTextFileName`` is just ``mesID.ToString()`` and ``FieldImporter.LoadInternal`` clears the
    table and reads only that one file -- so txid 0 is as safe as txid 500 there. Writing low ids into a
    SHARED base block (1073, 8, 22, ...) would shadow the base game's text for every field that uses it.
    :func:`build.validate` enforces the minted-block rule; do not bypass it.

    ``tails``/``strts`` are keyed by TXID here (not by position), since there is no positional index.
    """
    tails, strts = tails or {}, strts or {}
    out = []
    for txid, text in sorted(fixed, key=lambda kv: kv[0]):
        _t = tails.get(txid)
        out.append(mes_entry(text, int(txid), strt=(strts.get(txid) or (10, 1)),
                             tail=(DEFAULT_TAIL if _t is None else _t)))
    return ("\n".join(out) + "\n") if out else ""


# --------------------------------------------------------------------------- proportional auto-wrap
# FF9 field dialogue does NOT auto-wrap: the window grows to fit the widest line, so an un-broken long
# line runs off the screen. The original game hand-breaks every line; we reproduce that at build time.
#
# Why this is PROPORTIONAL and not pixel-exact (from Memoria source): the field dialogue font is a
# *runtime dynamic TrueType* font -- EncryptFontManager.InitializeFont ->
# Font.CreateDynamicFontFromOSFont(Configuration.Font.Names, ...), default the bundled "TBUDGoStd-Bold",
# overridable in Memoria.ini [Font]. Glyph widths come from Unity's TTF rasterizer at a configurable
# size, per language (NGUIText.GetGlyphWidth -> mTempChar.advance). So there is NO fixed pixel-width
# table to ship and exact-per-install wrapping is impossible offline. Instead we model RELATIVE glyph
# widths for a bold proportional sans ('W'/'m' ~3x 'i'/'l') and wrap at a conservative width budget --
# accurate where it matters (it respects glyph widths) and erring toward wrapping a hair early so it
# never overflows. Tune `wrap` per field for fuller lines (one in-game check finds your true max).

# max rendered line width, in "width units" (~ average characters). Conservative by default.
DEFAULT_WRAP_WIDTH = 28.0
_DEFAULT_GLYPH_W = 1.0

# relative advances for a bold proportional sans (em-ish; a typical letter ~0.9). Approximate by design.
_GLYPH_W = {
    " ": 0.5,
    "'": 0.3, "|": 0.3, "`": 0.3, ".": 0.4, ",": 0.4, ";": 0.4, ":": 0.4,
    "!": 0.45, "i": 0.45, "j": 0.45, "l": 0.45, "I": 0.5,
    "(": 0.5, ")": 0.5, "[": 0.5, "]": 0.5, "/": 0.5, "\\": 0.5,
    "f": 0.55, "t": 0.55, '"': 0.6, "-": 0.6, "r": 0.6,
    # the curly quote/apostrophe glyphs the speaker convention now emits (match their straight kin)
    "“": 0.6, "”": 0.6, "‘": 0.3, "’": 0.3,
    "s": 0.75, "J": 0.75, "?": 0.9,
    "m": 1.45, "w": 1.4, "M": 1.6, "W": 1.6, "@": 1.6, "&": 1.25,
}
for _c in "abcdeghknopquvxyz":
    _GLYPH_W.setdefault(_c, 0.9)
for _c in "ABCDEFGHKLNOPQRSTUVXYZ":
    _GLYPH_W.setdefault(_c, 1.15)
for _c in "0123456789":
    _GLYPH_W.setdefault(_c, 0.95)

_TAG_RE = re.compile(r"\[[^\]]*\]")
# tags render nothing (color/format/control) EXCEPT name/variable tags, which render text at runtime.
_NAME_TAGS = {"ZDNE", "VIVI", "DGGR", "STNR", "FRYA", "QUIN", "EIKO", "AMRT",
              "PTY1", "PTY2", "PTY3", "PTY4"}


def _tag_render_width(tag: str) -> float:
    code = tag[1:-1].split("=", 1)[0].strip().upper()      # "[VIVI]" -> "VIVI"; "[ICON=5]" -> "ICON"
    if code in _NAME_TAGS:
        return 6.0          # a (renameable) party name; ~6 characters
    if code in ("TEXT", "NUMB", "ITEM", "ICON"):
        return 4.0          # an inserted variable / item name / icon; rough
    if code in ("DBTN", "CBTN", "KCBT", "JCBT"):
        return 2.0          # a button glyph draws a sprite roughly two characters wide
    return 0.0              # color / format / page / control tag -> no glyphs


def measure(text: str) -> float:
    """Approximate rendered width of a dialogue line in width units (~average characters). Literal
    ``[...]`` tag brackets are not counted; their *rendered* content is (a name tag ~ a name, a color
    tag ~ nothing). Approximate by design -- see the module note on why pixel-exact is impossible."""
    total, i = 0.0, 0
    for m in _TAG_RE.finditer(text):
        total += sum(_GLYPH_W.get(c, _DEFAULT_GLYPH_W) for c in text[i:m.start()])
        total += _tag_render_width(m.group())
        i = m.end()
    total += sum(_GLYPH_W.get(c, _DEFAULT_GLYPH_W) for c in text[i:])
    return total


def wrap_text(text: str, width: float = DEFAULT_WRAP_WIDTH):
    """Break ``text`` into lines that each fit within ``width`` units, reproducing FF9's hand-broken
    dialogue. Existing ``\\n`` and ``[PAGE]`` breaks are respected (each page/line wrapped on its own),
    and a segment that already fits is kept BYTE-IDENTICAL (so short lines never change). Returns
    ``(wrapped, overflow)`` where ``overflow`` lists single words too wide to fit on a line alone."""
    overflow = []
    out_pages = []
    for page in text.split("[PAGE]"):
        out_lines = []
        for seg in page.split("\n"):
            if measure(seg) <= width:
                out_lines.append(seg)                      # already fits -> verbatim
                continue
            cur = ""
            for word in seg.split(" "):
                if measure(word) > width:
                    overflow.append(word)                  # an unbreakable, over-wide single word
                cand = f"{cur} {word}" if cur else word
                if cur and measure(cand) > width:
                    out_lines.append(cur)
                    cur = word
                else:
                    cur = cand
            out_lines.append(cur)
        out_pages.append("\n".join(out_lines))
    return "[PAGE]".join(out_pages), overflow


def overflow_lines(text: str, width: float = DEFAULT_WRAP_WIDTH):
    """Final wrapped lines that STILL exceed ``width`` -- i.e. an unbreakable over-wide word (a long
    name/URL). Empty list = everything fits after wrapping. Used to warn at build time."""
    wrapped, _ = wrap_text(text, width)
    bad = []
    for page in wrapped.split("[PAGE]"):
        bad.extend(ln for ln in page.split("\n") if measure(ln) > width)
    return bad
