"""B4/B5 STAGE 7 -- THE ROSTER-FED MENU CONTENT (memoria-patch s106), the solo bench ("coop_stock_menu part 2"), run
unattended.

THE GAP (studies/battle-coop/B4-B5-DESIGN.md 3.4, 4.5, section 7 stage 7). Stage 3 proved the stock panels compose
and take input inside the diorama's BattleMapDebug, but a mirrored slot's stand-in carries the DEFAULT preset and an
all-zero pa[], so its panels drew the wrong command for a script-changed preset, a blank row for every AP-learned
ability, the guest's OWN bag (a pick from it would forward an item the host may not hold) and a second pick the v1
frame cannot carry. s106 feeds a MIRRORED slot's panels from the host's type-4 roster through seven hooks (the
`bbench content` lever's bits): 1 command (ResolveMenuCommand), 2 grey (Change / Throw / Mix / AccessMenu drawn
state 1), 4 ability (RosterAbilityState + the MP column), 8 bag (DisplayItem lists the roster's items), 16 count
(the target-time item count), 32 cast (a double-cast command makes ONE pick), 64 refresh (a roster change repaints
the open panel under MuteActiveSound).

THE BENCH. Field 30602, `netsync selftest 1`, the party seeded through COOPPARTY (30604: +vivi +garnet +steiner), then
`netsync dioboot 67 0`. `netsync bbench roster auto 0` FABRICATES a two-marker roster for local slot 0 (the diorama's
BENCH stand-in: Attack/Defend/Jump/Dragon/Item/Change) through the REAL EncodeRoster/ParseRoster -- every marker chosen
from the guest's own state so it is ABSENT there (the TWO-MARKER law): a command outside the slot's preset
(WhiteMagicGarnet) whose 1st entry is listed ENABLED at MP 1 and whose 2nd is listed DISABLED; the slot's OWN
Ability-type command listing ONLY an entry the save has NOT learned (omitting one it HAS learned); a bag of ONE battle
item the guest owns 0 of, x77. The markers come back at `netsync.battle.menu.bench_roster`. THE STAND-IN'S ONE GAP: its
learned-ability table pa[] is ZEROED by design (that is why the roster exists), so its own DragonAct holds no LEARNED
entry to omit and the fabricator says so in `note` ("the slot's own DragonAct holds no LEARNED entry to omit") -- the
legs on slot 0 tolerate exactly that one note, and leg R proves the learned-omitted BLANK row on a REAL party slot
(the first of 1-3 whose fabrication chooses every marker: Vivi, whose Black Magic lists Fire). The panels are driven
like a player's (`bmenu open` = the stage-3 bench opener; press / cursor labels) and read back through `battle.hud`
(NetDescribeHud: what the NGUI draws); one in-engine PNG per panel leg PROVES the host roster is what is drawn -- READ
them after the run:
    s7-B-commands.png  s7-C-marker-abilities.png  s7-C-own-abilities.png  s7-D-items.png  s7-R-real-abilities.png
    s7-F-repainted.png
The deployment notes' BENCH CHANGES are applied: `menu.mirrored` is a LIST ([0] / []); leg F re-arms a plain roster
and opens the marker menu first (straight after leg E's `dbl` roster the repaint would bounce to the command panel).

WHAT IS PROVEN (S7-*; outcomes: the HUD as drawn, the engine's counters and log lines -- never an ack):
  P    the capability (`menu.content_hits`; `battle.hud.mirrored`; `bbench content on` accepted).
  BASE the stock panels before any roster: slot 0's commands as the stand-in draws them (Change on) -- the contrast.
  A    the fabricated roster through the REAL ParseRoster: the arm line, every marker chosen (note null -- or the
       stand-in's one learned gap, above), the marker command outside the stand-in's drawn commands, `mirrored == [0]`,
       `roster_src "bench"`, the guest owns 0 of M.
  B    commands: the marker menu draws the HOST's command (id, label != the stand-in's), Change grey (state 1, raw 1),
       AccessMenu grey when DRAWN and clamped (raw 1) when this layout does not draw it.
  C    abilities: the marker list -- marker_shown on with MP "1" (the stand-in's own MP is not 1), marker_grey grey,
       every other row blank; the own list -- the UNLEARNED entry on with "1", every other row blank (the stand-in
       has no LEARNED entry: leg R carries that row).
  R    (run after D, before E) a REAL party slot (pa[] not zeroed): `bbench roster auto L` chooses every marker (note
       null), and slot L's own list draws the UNLEARNED entry on with "1" and the LEARNED one BLANK (the host omitted it).
  D    bag + count: the item list is exactly "M x77" (no Potion); the target panel holds 30 frames (no SFX-101 bounce);
       the Confirm is captured {action 3, id M, local_slot 0, site SendCommand}; the guest's own M (0) and Potion (N)
       counts unchanged 5 s later; r9_refused 0.
  E    single cast: a `dbl` roster (DoubleBlackMagic) -> ONE pick is captured {action 2, menu, id marker_shown},
       hud.double_cast stays 0.
  F    repaint: `bbench roster auto 0 mp=9 grey` under the open marker list -> within 3 frames the row reads "9" and
       grey with no reopen and the cursor in place; refresh +1, roster_gen +1, painted == gen; the mute released.
       Both frame bounds count from the re-arm verb's ACK (no verb frame is published; the ack lands after the agent's
       2-frame block), so they bound "repainted by then" and "never stuck", not the hook's own latency; the run sets
       `stateevery 1` so the windows are read on every frame. F3 samples its OWN window (every publish from the ack to
       the first one past MUTE_FRAMES): mute_held true only inside the window, false on that first publish past it.
  G    only mirrored slots change: slot 1 (absent from the roster) draws the guest's own bag and Change on.
  H    `bbench roster clear` -> mirrored [] / roster_src null and slot 0 draws stock again; `reset` with a roster armed
       and the lever pulled logs both release lines.
  X    the raw-hex form of the plan through the REAL ParseRoster (the Python codec here composes it): the published
       roster equals this module's decode; a malformed roster is REFUSED by name; its marker command is drawn.
  INV  the guest's save/party/bag fingerprint (the sandbox autosave) is byte-identical across the run.
NOT PROVEN HERE (two-machine sitting 1): a non-identity wire/local mapping, the live peer roster's 1 s cadence driving
the repaint, the MirrorActive gate (design 4.2 -- the peer roster counts only under NetSyncParty.MirrorActive).

CALIBRATION -- a check that cannot fail is not a check.
  * THE DEPLOYED DLL AT WRITING (s105): no stage 7 at all. `netsync bbench ...` answers "netsync: unknown sub-verb
    'bbench' (...|bmenu|endbench)" and `menu.content_hits` / `battle.hud.mirrored` are absent, so the probe fails
    closed: P0, P1 and every A-H/R/X check RED ("not reached" with that refusal), H2 RED (no lever, no release lines).
    GREEN there: S0, PRE (the Potion count), BASE (the stage-3 opener draws stock content) and INV (nothing written).
    Measured on the s100-s105 stand-in (tools/harness/fakegame.py): S0 + BASE green; PRE and INV red there (the stand-in
    lists no Potion for `menus` in a diorama / writes no autosave) -- the real s105 adds those two greens.
    On the full s106-s110 stand-in (the green-path smoke, not an oracle): 24/33; its 9 reds are the stand-in's own gaps
    -- it writes no [NetSync] log lines (A1 B2 B3 E2 X1 H2 read their lines), lists no Potion (PRE), seats no slot 1 in
    the diorama (G1) and writes no autosave (INV). (Measured BEFORE leg R: R1/R2 are unmeasured on the stand-in.)
  * THE REAL s106-s110 DLL, run 20261013-131817 (before this round's fixes): 27/33. A1 A2 C2 E1 were the stand-in's
    zeroed pa[] (note "the slot's own DragonAct holds no LEARNED entry to omit"), B3 the undrawn AccessMenu (state 0,
    raw 1), F3 the sampler (the repaint landed by the ack, so F1's watch returned at once and the next read was the
    shot's, 20 frames on -- the published states show mute_held true at 2607/2609 and false from 2611).
  * IN-RUN, on the stage DLL: `COOP_CONTENT_ON=<mask>` pulls `bbench content <mask>` (the hooks left ON) right after leg
    A, runs every leg under it and judges S7-CAL against the predicted red set (PREDICTED below; the run itself is red
    by design). The eight sheet levers and their reds:
        0    B2 B3 C1 C2 C3 D1 D2 D3 E2 F1 F2 F3 R2 X3   (the pre-stage panels: Steal, Change on, the guest's bag,
                                                      the real slot's own learning)
        126  B2 C1 C3 E2 F1 F2 F3 X3   (command off: the marker command missing, so its lists cannot open; R's list is
                                        the real slot's OWN command, fed by the ability hook -- R2 stays green)
        125  B3                        (grey off: Change state 2)
        123  C1 C2 E2 F1 F2 F3 R2      (ability off: the rows blank / drawn by the slot's own learning -- the real
                                        slot draws its LEARNED row and blanks the unlearned; the blank marker_shown
                                        row cannot be picked, so leg F is not reached)
        R1 is never predicted red: the fabricator reads through the content BYPASS, so no lever reaches it.
        119  D1 D2 D3                  (bag off: the guest's own bag, M absent)
        111  D2 D3                     (count off: the pick of M bounces back to the item list, nothing captured)
        95   E2                        (cast off, with `dbl`: the target Confirm returns to the ability list,
                                        double_cast 2, no capture)
        63   F1 F2                     (refresh off: the open panel keeps "1" until reopened; refresh unchanged)

DRIVER NOTE. A Session.netsync that predates `bbench` (s106) refuses it before sending: _coop_battle.ns_verb then sends
it as a raw step (the agent's own gates and refusals apply unchanged). A driver that knows it refuses it first on an
engine without `menu.content_hits` ("publishes no ..."): read as "this engine cannot" (the probe), never as a pass.

    py tools/play.py studies/test-harness/scenarios/coop_stock_menu_content.py --field 30602
    COOP_CONTENT_ON=123 py tools/play.py studies/test-harness/scenarios/coop_stock_menu_content.py --field 30602
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file

HarnessError = cb.HarnessError

CONTENT_ALL = 127
HIT_KEYS = ("command", "grey", "ability", "bag", "count", "cast", "refresh")
WHITE_MAGIC_GARNET, DOUBLE_WHITE, DOUBLE_BLACK = 17, 21, 23
CHANGE_CMD = 7
OPEN_S = 3.0
HOLD_FRAMES = 30                         # D2: the target panel must hold this many frames (no SFX-101 bounce)
REPAINT_FRAMES = 3                       # F1: the open panel repaints within this many frames of the re-arm
MUTE_FRAMES = 8                          # F3: the repaint's MuteActiveSound is released within this many frames
POTION_WAIT_S = 5.0
ARMED = "harness: bench menu roster armed ("
GREY_LINE = "drawn GREYED -- Change is outside the v1 command scope (B4.2)"
SHOWS_HOST = "shows the HOST's "
ONE_PICK = "makes ONE pick on a mirrored slot"
REL_CONTENT = "stock-menu content hooks back ON (released with the harness)"
REL_ROSTER = "the bench menu roster cleared (released with the harness)"
NOT_FABRICATED = " -- NOT fabricated: "
#: BenchFabricate's note when a slot's OWN Ability-type command holds no LEARNED entry to omit -- the one gap the BENCH
#: stand-in (local slot 0) always has: its pa[] is ZEROED by design. Matched WHOLE, so any other gap ("no ... command
#: outside the slot's preset", "no battle item the guest owns 0 of") -- alone or '; '-joined to this one -- does not.
LEARNED_GAP = re.compile(r"the slot's own [A-Za-z0-9]+ holds no LEARNED entry to omit")
REAL_SLOTS = (1, 2, 3)                   # leg R's candidates: COOPPARTY seats Vivi / Garnet / Steiner here


def _env_mask():
    v = os.environ.get("COOP_CONTENT_ON", "").strip().lower()
    if not v:
        return None
    try:
        m = int(v, 16) if v.startswith("0x") else int(v)
    except ValueError:
        return None
    return m if 0 <= m <= CONTENT_ALL else None


CAL_MASK = _env_mask()

#: The on-mask -> the checks its lever must turn red (and nothing else). The sheet's eight levers.
PREDICTED = {
    # R2 under 0 and 123: with the ability hook off the real slot's list is its OWN learning -- the LEARNED row drawn
    # (state 2), the unlearned one blank -- the exact reverse of what R2 asks
    0: ("S7-B2", "S7-B3", "S7-C1", "S7-C2", "S7-C3", "S7-D1", "S7-D2", "S7-D3", "S7-E2", "S7-F1", "S7-F2", "S7-F3",
        "S7-R2", "S7-X3"),
    126: ("S7-B2", "S7-C1", "S7-C3", "S7-E2", "S7-F1", "S7-F2", "S7-F3", "S7-X3"),
    125: ("S7-B3",),
    # 123: marker_shown is not listed by the stand-in's own learning, so its row draws blank (NetDescribeList publishes
    # label ''), pick_row cannot reach it and leg F records F1-F3 "not reached" -- exactly as E2 is for the same reason
    123: ("S7-C1", "S7-C2", "S7-E2", "S7-F1", "S7-F2", "S7-F3", "S7-R2"),
    119: ("S7-D1", "S7-D2", "S7-D3"),
    111: ("S7-D2", "S7-D3"),
    95: ("S7-E2",),
    63: ("S7-F1", "S7-F2"),
}
#: Collateral a lever MAY turn red (a panel shot that cannot be taken once its list cannot open).
MAYBE = {0: ("S7-D5",), 119: ("S7-D5",), 123: ("S7-C3",)}


def _catalog() -> dict:
    c = {
        "S7-S0": "the harness forced the selftest role for this process (Memoria.ini untouched)",
        "S7-P0": "the engine publishes `netsync.battle.menu.content_hits` (memoria-patch s106, stage 7)",
        "S7-P1": "inside the diorama `battle.hud.mirrored` is published and `netsync bbench content on` is accepted",
        "S7-PRE": "precondition: the guest owns at least 1 Potion (`menus 0` lists item 236 with count N >= 1)",
        "S7-BASE": "BASE (no roster): `bmenu open 0` draws the stand-in's stock commands -- Change (menu 5) on (state 2), "
                   "every drawn command labelled -- recorded as the contrast",
        "S7-A1": "A: `bbench roster auto 0` is accepted and logs 'harness: bench menu roster armed (auto, N bytes through "
                 "the REAL ParseRoster; wire slot(s) 0, 1 item(s)) [..]; local slot 0 (wire 0): marker ...' -- note "
                 "null, or ONLY the stand-in's learned gap ('the slot's own <cmd> holds no LEARNED entry to omit', "
                 "learned -1), and the line ends with exactly that note",
        "S7-A2": "A: bench_roster carries every marker: src auto, slot 0, wire 0, marker_menu/uk_menu the two Ability "
                 "menus, marker_cmd outside the stand-in's drawn commands, marker_shown/marker_grey/unlearned/item "
                 "chosen, count 77, mp 1; learned chosen with note null -- or learned -1 with ONLY the stand-in's "
                 "learned gap as its note (leg R proves the learned marker on a real slot)",
        "S7-A3": "A: menu.mirrored == [0], roster_src 'bench', and the published roster carries wire 0 + exactly "
                 "[{id M, count 77}]",
        "S7-A4": "A: the TWO-MARKER law -- the guest's own bag (`menus 0`, FF9.item) holds 0 of M",
        "S7-B1": "B: `bmenu open 0` -> turn.slot 0 and battle.hud.mirrored true",
        "S7-B2": "B: the marker menu draws the HOST's command -- its row has id marker_cmd, state 2 and a label that is not "
                 "the stand-in's; content_hits.command moved; 'stock menu: local slot 0 menu <m> shows the HOST's <cmd> "
                 "instead of the stand-in's ...' logged since the roster arm (once per boot: A4's `menus 0` may log it)",
        "S7-B3": "B: Change (menu 5) is drawn GREY (state 1, raw 1) -- and AccessMenu GREY (state 1) when DRAWN, its "
                 "enabled state clamped (raw 1) when this layout does not draw it (state 0); content_hits.grey moved; "
                 "'(Change) drawn GREYED -- Change is outside the v1 command scope (B4.2)' logged",
        "S7-B4": "B: an in-engine PNG of the command panel, decoded non-blank (s7-B-commands)",
        "S7-C1": "C: the marker list -- the marker_shown row state 2 with MP '1' (the stand-in's own MP for it is not 1), "
                 "the marker_grey row state 1, every other visible row state 0; content_hits.ability moved",
        "S7-C2": "C: the stand-in's own list -- the UNLEARNED row state 2 with MP '1', the LEARNED row state 0 (blank); "
                 "when the stand-in has no learned entry (A's tolerated gap) every row but the unlearned one is state 0",
        "S7-C3": "C: an in-engine PNG of each list, decoded non-blank (s7-C-marker-abilities, s7-C-own-abilities)",
        "S7-D1": "D: the item list is exactly one row -- id M, number '77', state 2 -- and no Potion; content_hits.bag moved",
        "S7-D2": f"D: Confirm on M opens the target panel and it HOLDS {HOLD_FRAMES} frames (no SFX-101 bounce to the item "
                 f"list); content_hits.count moved",
        "S7-D3": "D: Confirm on the target is CAPTURED -- captures +1, captured == {action 3, id M, local_slot 0, site "
                 "'SendCommand'}, its hex decodes to that in Python, r9_refused 0",
        "S7-D4": "D: 5 s later the guest's OWN bag is untouched -- M still 0, Potion still N (`menus 0`)",
        "S7-D5": "D: an in-engine PNG of the item list, decoded non-blank (s7-D-items)",
        "S7-E1": "E: `bbench roster auto 0 dbl` arms a double-cast marker (bench_roster.dbl, marker_cmd DoubleBlackMagic "
                 "or DoubleWhiteMagic; note null, or ONLY the stand-in's learned gap -- it concerns the learn sub-marker, "
                 "not the double-cast one)",
        "S7-E2": "E: ONE pick + one target Confirm is captured {action 2, menu marker_menu, id marker_shown}, "
                 "hud.double_cast stays 0, content_hits.cast moved, '... makes ONE pick on a mirrored slot' logged",
        "S7-F1": f"F: under the open marker list `bbench roster auto 0 mp=9 grey` repaints IN PLACE within "
                 f"{REPAINT_FRAMES} frames of the re-arm's ack -- marker_shown reads '9' and state 1, the panel still "
                 f"'ability', the cursor on the same row",
        "S7-F2": "F: content_hits.refresh +1, roster_gen +1 and roster_painted == roster_gen",
        "S7-F3": f"F: the repaint's mute never STICKS -- every publish from the re-arm's ack on that shows mute_held true "
                 f"lies within {MUTE_FRAMES} frames of it, the first publish more than {MUTE_FRAMES} frames after it "
                 f"shows false, and so does the read after the shot (the 2-frame hold itself may fall between "
                 f"publishes: seen held is noted, not required -- so this proves 'released', not 'muted'; it stays green "
                 f"under the refresh-off lever 63, where nothing mutes)",
        "S7-R1": "R (a REAL party slot -- the stand-in's zeroed pa[] has no learned entry to omit): `bbench roster auto "
                 "L` on the first of local slots 1-3 whose fabrication chooses EVERY marker -- note null, learned and "
                 "unlearned chosen and distinct, uk_menu an Ability menu, one arm line naming local slot L with no "
                 "'NOT fabricated', mirrored == [L]",
        "S7-R2": "R: slot L's OWN list (the bench opener; hud.mirrored true) draws the UNLEARNED row state 2 with MP '1' "
                 "and the LEARNED row state 0 (BLANK: the host omitted it); content_hits.ability moved; an in-engine "
                 "PNG of it decoded non-blank (s7-R-real-abilities)",
        "S7-G1": "G: slot 1 (absent from the roster) is NOT mirrored -- hud.mirrored false, its item list the guest's own "
                 "bag (Potion N present, M absent), Change on (state 2)",
        "S7-H1": "H: `bbench roster clear` -> mirrored [] and roster_src null; slot 0 reopens with the stand-in's stock "
                 "commands (the BASE ids, Change on, mirrored false)",
        "S7-X1": "X: the plan's raw-hex roster (wire 0: Attack + Ability1 = WhiteMagicGarnet listing only Cure, enabled, "
                 "MP 1; bag M x77) is ACCEPTED through the REAL ParseRoster -- bench_roster src 'hex' with its byte count "
                 "and the published roster equal to this module's own decode of the bytes",
        "S7-X2": "X: a malformed roster (version 2; a truncated one) is REFUSED -- 'the REAL ParseRoster refused those N "
                 "bytes'",
        "S7-X3": "X: the hex roster is DRAWN -- slot 0's Ability1 row reads WhiteMagicGarnet (17), state 2",
        "S7-INV": "the guest's save/party/bag fingerprint (sandbox autosave) is byte-identical, setup to end",
        "S7-H2": "H (reset with a roster armed and the lever pulled): both 'stock-menu content hooks back ON (released with "
                 "the harness)' and 'the bench menu roster cleared (released with the harness)'; content_off 0, "
                 "bench_roster null",
    }
    if CAL_MASK is not None:
        c["S7-CAL"] = (f"CALIBRATION (`bbench content {CAL_MASK}`): the lever turned EXACTLY the predicted checks red "
                       f"({', '.join(PREDICTED.get(CAL_MASK, ())) or 'no prediction for this mask'})")
    return c


# ------------------------------------------------------------------------------------------- reads
def _menu(st) -> dict:
    return cb.bmenu(st)


def _hits(st) -> dict:
    h = _menu(st).get("content_hits")
    return h if isinstance(h, dict) else {}


def _hit_delta(h0: dict, st, key: str):
    a, b = (h0 or {}).get(key), _hits(st).get(key)
    return (b - a) if isinstance(a, int) and isinstance(b, int) else None


def _br(st) -> dict:
    b = _menu(st).get("bench_roster")
    return b if isinstance(b, dict) else {}


def _bb(g, *args) -> tuple:
    return cb.try_ns(g, "bbench", *args)


def _rows_brief(st) -> list:
    return [(r.get("id"), r.get("label"), r.get("number"), r.get("state")) for r in cb.hud(st).get("rows") or []][:10]


def _cmds_brief(st) -> list:
    return [(r.get("menu"), r.get("id"), r.get("label"), r.get("state"), r.get("raw")) for r in cb.hud(st).get("commands")
            or []]


# ------------------------------------------------------------------------------------------- verdicts
def _learned_gap_only(br: dict) -> bool:
    """The fabricator's note names EXACTLY ONE gap -- the learn sub-marker's learned entry -- and the record agrees
    (learned -1, the unlearned entry still chosen). This is what the BENCH stand-in (local slot 0) always reports: its
    pa[] is zeroed by design, so its own DragonAct holds nothing LEARNED to omit (run 20261013-131817). Red for any
    other gap: a missing marker command / unlearned entry / bag item, or two gaps '; '-joined."""
    note = br.get("note")
    return (isinstance(note, str) and LEARNED_GAP.fullmatch(note) is not None and br.get("learned") == -1
            and isinstance(br.get("unlearned"), int) and br["unlearned"] > 0)


def _note_ok(br: dict) -> bool:
    """A1/A2/E1's note verdict. Every marker fabricated (note null, so the learned entry IS chosen), or the stand-in's
    one tolerated gap (:func:`_learned_gap_only`) -- the learned-omitted blank row it cannot show is leg R's, on a real
    slot. Still red: any other note, a note with learned chosen, or no note with learned unchosen."""
    if br.get("note") is None:
        return isinstance(br.get("learned"), int) and br["learned"] > 0
    return _learned_gap_only(br)


def _arm_line_note_ok(line: str, br: dict) -> bool:
    """The arm line carries the SAME verdict as the published record: no 'NOT fabricated' tail for a null note, else it
    ends with exactly ' -- NOT fabricated: <note>' (ArmBenchRoster appends it last)."""
    if br.get("note") is None:
        return NOT_FABRICATED not in line
    return line.rstrip().endswith(NOT_FABRICATED + str(br.get("note")))


def _access_ok(acc) -> bool:
    """B3's AccessMenu (menu 7) verdict. NetDescribeHud publishes state 0 for a button that is NOT DRAWN
    (!button.IsActive or an empty label) and raw = the menu's _commandEnabledState. Run 20261013-131817's command panel
    (Attack/Defend/Jump/Dragon/Item/Change) does not draw it: state 0 with raw 1 after the grey hook, raw 2 in BASE (no
    roster) -- so a not-drawn AccessMenu is judged by the CLAMP (raw 1) and a drawn one by its colour (state 1). Still
    red: a drawn AccessMenu at state 2, or a not-drawn one whose enabled state was not clamped (raw 2 / -1)."""
    if acc is None:
        return True                     # this layout has no AccessMenu button at all (NetDescribeHud skips it)
    if acc.get("state") != 0:
        return acc.get("state") == 1
    return acc.get("raw") == 1


def _mute_verdict(pubs, f1: int, window: int = MUTE_FRAMES) -> tuple:
    """F3's judge over every publish from the re-arm's ACK (frame ``f1``) on. (ok, held frames, the first frame more than
    ``window`` frames after the ack or None, its mute_held). OK = every publish showing mute_held true lies within
    ``window`` frames of the ack AND the first publish past the window shows false. The engine holds MuteActiveSound for
    2 frames after the repaint (StockMenuMute/StockMenuMuteSettle): run 20261013-131817 published it true at 2607/2609
    (ack 2609) and false from 2611. Still red: a mute held past the window, true on the first publish past it, or no
    publish past it at all (a starved sampler proves nothing)."""
    seen = {}
    for x in pubs:
        f = cb.frame_of(x)
        if f >= f1:
            seen.setdefault(f, _menu(x).get("mute_held"))
    held = sorted(f for f, v in seen.items() if v is True)
    past = sorted(f for f in seen if f > f1 + window)
    first = past[0] if past else None
    val = seen[first] if first is not None else None
    ok = all(f <= f1 + window for f in held) and first is not None and val is False
    return ok, held, first, val


class _Ctx:
    potion_n = None
    base = None              # {menu: (id, label, state)} -- the stand-in's stock commands for slot 0
    br = None                # bench_roster of leg A
    a_mark = None            # the log mark taken just before leg A's roster arm (B2's line window -- see _leg_b)
    shots: dict = {}
    bench_ok = False


def _shot(g, ctx: _Ctx, key: str, name: str) -> None:
    g.wait_frames(10)
    p, why = cb.shot(g, name)
    ctx.shots[key] = (p, why)
    g.note(f"shot {name}: {p if p else why} -- READ it")


def _shot_ok(ctx: _Ctx, *keys) -> tuple:
    bad = {k: (ctx.shots.get(k) or (None, "not taken"))[1] or "blank" for k in keys
           if not (ctx.shots.get(k) or (None, ""))[0] or not cb.png_not_blank(ctx.shots[k][0])}
    return not bad, (", ".join(f"{k}={v}" for k, v in bad.items()) or "non-blank: " +
                     ", ".join(str(ctx.shots[k][0]) for k in keys))


# ------------------------------------------------------------------------------------------- the run
def run(g, field: int = cb.FIELD):
    led = cb.Ledger(g, _catalog(), finals=("S7-INV", "S7-H2", "S7-CAL"))
    ctx = _Ctx()
    ctx.shots = {}
    fp0 = [None, ""]
    try:
        _run(g, led, ctx, field, fp0)
    finally:
        g.note(f"Memoria.log archived: {cb.archive_log(g, 'stock-menu-content')}")
        led.close()
        try:
            if cb.dio(g.state).get("booted"):
                cb.leave(g, field)
            fpn, why = cb.fingerprint(g, field=field)
            if fp0[0] is None or fpn is None:
                led.check("S7-INV", False, f"not reached: the invariant snapshot failed ({fp0[1] or why})")
            else:
                diff = cb.fp_diff(fp0[0], fpn)
                led.check("S7-INV", not diff, f"changed: {diff}" if diff else
                          f"identical (gil {fpn.get('gil')}, {len(fpn.get('items') or [])} bag rows)")
        except HarnessError as err:
            g.note(f"the final invariant read failed: {str(err)[:160]}")
        _release(g, led, ctx)
        if CAL_MASK is not None:
            led.judge_calibration("S7-CAL", PREDICTED.get(CAL_MASK, ()), MAYBE.get(CAL_MASK, ()))
        led.close(final=True)


def _run(g, led: cb.Ledger, ctx: _Ctx, field: int, fp0: list) -> None:
    ok, why = cb.setup(g, field, label="B4/B5 stage 7: the roster-fed menu content (s106), solo"
                                       + (f" -- CALIBRATION (bbench content {CAL_MASK})" if CAL_MASK is not None else ""))
    led.check("S7-S0", ok, why)
    fp, fwhy = cb.fingerprint(g, field=field)
    fp0[0], fp0[1] = fp, fwhy
    st = g.state
    g.note(f"probe stage: {cb.stage_note(st)} (the highest B4/B5 stage and R3 patch whose keys this engine publishes)")
    led.check("S7-P0", cb.has(st, cb.PROBES[7]),
              f"netsync.battle.menu keys: {sorted(_menu(st))}" if cb.has(st, "netsync.battle") else
              "no `netsync.battle` at all (a pre-s100 engine)")
    try:
        g.state_every(1)                                   # D2's hold, F1's repaint and F3's mute are read in FRAMES
    except (HarnessError, AttributeError) as err:
        g.note(f"stateevery 1 refused ({str(err)[:120]}) -- frame windows read at the default cadence")
    booted, bwhy = cb.boot(g)
    if not booted:
        led.close(bwhy)
        cb.back_to_field(g, field)
        return
    st = cb.wait_steady(g)
    if st is None:
        led.close("the diorama never reached its command phase (PHASE_NORMAL + turn.enabled)")
        cb.leave(g, field)
        return
    m0 = cb.menus_of(g, 0)
    ctx.potion_n = cb.bag_count(m0, cb.POTION)
    led.check("S7-PRE", isinstance(ctx.potion_n, int) and ctx.potion_n >= 1, f"Potion count {ctx.potion_n!r} (`menus 0`)")
    _base(g, led, ctx)
    okp, whyp = _bb(g, "content", "on")
    led.check("S7-P1", okp and cb.has(g.state, "battle.hud.mirrored"),
              whyp or f"battle.hud keys: {sorted(cb.hud(g.state))}")
    if not okp:
        led.close(f"`netsync bbench` refused -- {whyp}")
        cb.leave(g, field)
        return
    ctx.bench_ok = True
    if not _leg_a(g, led, ctx):
        led.close("the bench roster never armed (leg A)")
        cb.leave(g, field)
        return
    if CAL_MASK is not None:
        okc, whyc = _bb(g, "content", str(CAL_MASK))
        g.note(f"CALIBRATION: `bbench content {CAL_MASK}` -> {'pulled' if okc else whyc} (content_off "
               f"{_menu(g.state).get('content_off')!r})")
    _leg_b(g, led, ctx)
    _leg_c(g, led, ctx)
    _leg_d(g, led, ctx)
    _leg_r(g, led, ctx)                    # re-arms the roster for a real slot; leg E re-arms slot 0 first thing
    _leg_e(g, led, ctx)
    _leg_f(g, led, ctx)
    _leg_g(g, led, ctx)
    _leg_h(g, led, ctx)
    _leg_x(g, led, ctx)
    cb.leave(g, field)


def _base(g, led: cb.Ledger, ctx: _Ctx) -> None:
    g.note("BASE: slot 0's stock commands before any roster")
    ok, why, st = cb.bmenu_open(g, 0)
    rows = cb.hud(st).get("commands") or []
    ctx.base = {int(r.get("menu", -1)): (r.get("id"), r.get("label"), r.get("state")) for r in rows}
    change = ctx.base.get(cb.MENU_CHANGE)
    led.check("S7-BASE", ok and change is not None and change[2] == 2 and rows and all(r.get("label") for r in rows),
              why or f"commands {_cmds_brief(st)}")
    cb.bmenu_close(g, 0)


def _leg_a(g, led: cb.Ledger, ctx: _Ctx) -> bool:
    g.note("A: fabricate the two-marker roster for local slot 0")
    at = cb.mark(g)
    ctx.a_mark = at
    ok, why = _bb(g, "roster", "auto", 0)
    st = g.state
    lines = cb.wait_log(g, at, ARMED, 2.0)
    arm = [ln for ln in lines if ARMED + "auto, " in ln and "bytes through the REAL ParseRoster; wire slot(s) 0, 1 item(s)) ["
           in ln and "; local slot 0 (wire 0): marker " in ln]
    br = _br(st)
    ctx.br = br
    # The note: null, or ONLY the stand-in's learned gap (its pa[] is zeroed -- run 20261013-131817 armed with "the slot's
    # own DragonAct holds no LEARNED entry to omit"); leg R proves the learned marker on a real slot. Any other gap, or a
    # line whose 'NOT fabricated' tail disagrees with the record, is still red.
    led.check("S7-A1", ok and len(arm) == 1 and _note_ok(br) and _arm_line_note_ok(arm[0], br),
              why or f"note {br.get('note')!r} learned {br.get('learned')!r}; {cb.grep(lines, 'bench menu roster')}")
    if not ok:
        led.unreached([c for c in led.pending("S7-A")], f"`bbench roster auto 0` refused -- {why}")
        return False
    base_ids = {v[0] for v in (ctx.base or {}).values()}
    menus = {cb.MENU_ABILITY1, cb.MENU_ABILITY2}
    good = (br.get("src") == "auto" and br.get("slot") == 0 and br.get("wire") == 0
            and br.get("marker_menu") in menus and br.get("uk_menu") in menus and br.get("marker_menu") != br.get("uk_menu")
            and isinstance(br.get("marker_cmd"), int) and br["marker_cmd"] > 0 and br["marker_cmd"] not in base_ids
            and all(isinstance(br.get(k), int) and br[k] > 0 for k in ("marker_shown", "marker_grey", "unlearned"))
            and isinstance(br.get("item"), int) and br["item"] >= 0 and br.get("count") == 77 and br.get("mp") == 1
            and _note_ok(br))                    # learned chosen + note null, or the stand-in's one gap (see A1)
    led.check("S7-A2", good, f"bench_roster={br}; the stand-in's drawn command ids {sorted(i for i in base_ids if i is not None)}")
    m = _menu(st)
    roster = m.get("roster") if isinstance(m.get("roster"), dict) else {}
    wires = [s.get("wire") for s in roster.get("slots") or []]
    led.check("S7-A3", m.get("mirrored") == [0] and m.get("roster_src") == "bench" and wires == [0]
              and roster.get("items") == [{"id": br.get("item"), "count": 77}],
              f"mirrored={m.get('mirrored')!r} roster_src={m.get('roster_src')!r} roster={roster}")
    m0 = cb.menus_of(g, 0)
    have = cb.bag_count(m0, br.get("item", -1))
    led.check("S7-A4", have == 0, f"the guest's own count of item {br.get('item')!r}: {have!r} (`menus 0`)")
    return True


def _leg_b(g, led: cb.Ledger, ctx: _Ctx) -> None:
    g.note("B: the command panel draws the host's commands")
    br = ctx.br or {}
    h0 = _hits(g.state)
    at = cb.mark(g)
    ok, why, st = cb.bmenu_open(g, 0)
    led.check("S7-B1", ok and st.turn_slot == 0 and cb.hud(st).get("mirrored") is True,
              why or f"turn.slot={st.turn_slot} {cb.hud_brief(st)}")
    if not ok:
        led.unreached(("S7-B2", "S7-B3", "S7-B4"), f"slot 0's window never opened: {why}")
        return
    g.wait_frames(6)
    st = g.state
    lines = cb.new(g, at)
    # The "shows the HOST's" line is logged ONCE PER BOOT (ContentLogFirst "cmd <slot>/<menu>/<host>"), by whichever call
    # resolves the mirrored command first -- and that is leg A's own `menus 0` read (S7-A4): the verb's CollectNetMenus ->
    # GetCommandFromCommandIndex -> NetResolveMenuCommand -> ResolveMenuCommand, before this leg's mark. So the line is
    # read from leg A's mark (the roster arm: the slot cannot be mirrored earlier); the per-LEG proof that THIS draw went
    # through the hook is the content_hits.command delta (from this leg's h0).
    lines_a = cb.new(g, ctx.a_mark) if isinstance(ctx.a_mark, int) else lines
    mk = cb.hud_cmd(st, br.get("marker_menu", -1)) or {}
    base_label = ((ctx.base or {}).get(br.get("marker_menu", -1)) or (None, None, None))[1]
    led.check("S7-B2", mk.get("id") == br.get("marker_cmd") and mk.get("state") == 2 and bool(mk.get("label"))
              and mk.get("label") != base_label and (_hit_delta(h0, st, "command") or 0) > 0
              and any("stock menu: local slot 0 menu " in ln and SHOWS_HOST in ln and "instead of the stand-in's" in ln
                      for ln in lines_a),
              f"marker row {mk} (want id {br.get('marker_cmd')}, state 2, a label not the stand-in's {base_label!r}); "
              f"command hits +{_hit_delta(h0, st, 'command')!r}; since the roster arm: {cb.grep(lines_a, SHOWS_HOST)}")
    ch = cb.hud_cmd(st, cb.MENU_CHANGE) or {}
    acc = cb.hud_cmd(st, cb.MENU_ACCESS)
    # AccessMenu: 'when present' means DRAWN -- a not-drawn one (state 0) is judged by the clamp, raw 1 (_access_ok)
    led.check("S7-B3", ch.get("state") == 1 and ch.get("raw") == 1 and _access_ok(acc)
              and (_hit_delta(h0, st, "grey") or 0) > 0 and any(GREY_LINE in ln and "(Change)" in ln for ln in lines),
              f"Change row {ch}; AccessMenu row {acc}; grey hits +{_hit_delta(h0, st, 'grey')!r}; {cb.grep(lines, 'GREYED')}")
    _shot(g, ctx, "commands", "s7-B-commands")
    sok, sdetail = _shot_ok(ctx, "commands")
    led.check("S7-B4", sok, sdetail)


def _leg_c(g, led: cb.Ledger, ctx: _Ctx) -> None:
    g.note("C: the ability lists draw the host's learned set")
    br = ctx.br or {}
    h0 = _hits(g.state)
    st = g.state
    if st.turn_slot != 0:
        cb.bmenu_close(g, 0)
        cb.bmenu_open(g, 0)
    ok, why, st = cb.pick_command(g, br.get("marker_menu", -1), expect_panel="ability")
    if ok:
        g.wait_frames(6)
        st = g.state
        rows = cb.hud(st).get("rows") or []
        shown, grey = cb.hud_row(st, br.get("marker_shown", -1)), cb.hud_row(st, br.get("marker_grey", -1))
        others = [r for r in rows if r is not shown and r is not grey and r.get("state") != 0]
        local_mp = br.get("marker_local_mp")
        led.check("S7-C1", shown is not None and shown.get("state") == 2 and cb.strip_tags(shown.get("number")) == "1"
                  and local_mp != 1 and grey is not None and grey.get("state") == 1 and not others
                  and (_hit_delta(h0, st, "ability") or 0) > 0,
                  f"rows {_rows_brief(st)}; marker_shown {br.get('marker_shown')} (the stand-in's own MP {local_mp!r}), "
                  f"marker_grey {br.get('marker_grey')}; non-blank others {others[:3]}; ability hits "
                  f"+{_hit_delta(h0, st, 'ability')!r}")
        _shot(g, ctx, "marker", "s7-C-marker-abilities")
        cb.back_to_root(g)
    else:
        led.check("S7-C1", False, f"the marker list never opened: {why}")
    ok2, why2, st = cb.pick_command(g, br.get("uk_menu", -1), expect_panel="ability")
    if ok2:
        g.wait_frames(6)
        st = g.state
        un, kn = cb.hud_row(st, br.get("unlearned", -1)), cb.hud_row(st, br.get("learned", -1))
        if isinstance(br.get("learned"), int) and br["learned"] > 0:
            learned_ok, lwhy = kn is not None and kn.get("state") == 0, "the learned row must be blank"
        else:
            # The stand-in's tolerated gap (A1/A2): nothing LEARNED to omit, so the learned-omitted blank row is leg R's.
            # What this list CAN prove: the roster lists ONLY the unlearned entry, so every other visible row is blank
            # (run 20261013-131817: Lancer '1' on, rows 118-124 state 0). Still red: another row drawn, or a note that is
            # not exactly the learned gap.
            others = [r for r in cb.hud(st).get("rows") or [] if r is not un and r.get("state") != 0]
            learned_ok = _learned_gap_only(br) and not others
            lwhy = f"no learned entry (leg R carries that row); non-blank others {others[:3]}"
        led.check("S7-C2", un is not None and un.get("state") == 2 and cb.strip_tags(un.get("number")) == "1"
                  and learned_ok,
                  f"rows {_rows_brief(st)}; unlearned {br.get('unlearned')} -> {un}; learned {br.get('learned')} -> {kn} "
                  f"({lwhy})")
        _shot(g, ctx, "own", "s7-C-own-abilities")
        cb.back_to_root(g)
    else:
        led.check("S7-C2", False, f"the stand-in's own list never opened: {why2}")
    sok, sdetail = _shot_ok(ctx, "marker", "own")
    led.check("S7-C3", sok, sdetail)


def _leg_d(g, led: cb.Ledger, ctx: _Ctx) -> None:
    g.note("D: the item list is the host's bag; the count holds the target panel; the pick is captured")
    br = ctx.br or {}
    item = br.get("item", -1)
    st = g.state
    if st.turn_slot != 0 or cb.hud(st).get("panel") != "command":
        cb.bmenu_close(g, 0)
        cb.bmenu_open(g, 0)
    h0 = _hits(g.state)
    m0 = _menu(g.state)
    c0, r90 = m0.get("captures"), m0.get("r9_refused")
    ok, why, st = cb.pick_command(g, cb.MENU_ITEM, expect_panel="item")
    if not ok:
        led.unreached(("S7-D1", "S7-D2", "S7-D3", "S7-D5"), f"the item list never opened: {why}")
    else:
        g.wait_frames(6)
        st = g.state
        rows = cb.hud(st).get("rows") or []
        led.check("S7-D1", len(rows) == 1 and rows[0].get("id") == item and cb.strip_tags(rows[0].get("number")) == "77"
                  and rows[0].get("state") == 2 and cb.hud_row(st, cb.POTION) is None
                  and (_hit_delta(h0, st, "bag") or 0) > 0,
                  f"rows {_rows_brief(st)} (want exactly [({item}, ..., '77', 2)]); bag hits +{_hit_delta(h0, st, 'bag')!r}")
        _shot(g, ctx, "items", "s7-D-items")
        sok, sdetail = _shot_ok(ctx, "items")
        led.check("S7-D5", sok, sdetail)
        _pick_item(g, led, item, h0, c0, r90)
    cb.to_root(g)
    cb.hold_for(g, POTION_WAIT_S)
    m = cb.menus_of(g, 0)
    have_m, have_p = cb.bag_count(m, item), cb.bag_count(m, cb.POTION)
    led.check("S7-D4", have_m == 0 and have_p == ctx.potion_n and isinstance(have_p, int),
              f"M {item}: {have_m!r} (want 0); Potion {have_p!r} (want {ctx.potion_n!r})")


def _pick_item(g, led: cb.Ledger, item: int, h0: dict, c0, r90) -> None:
    """D2 + D3 on the open item list: M -> the target panel must HOLD (the count hook), then the Confirm is captured."""
    pok, pwhy = cb.pick_row(g, item, group=cb.ITEM_GROUP)
    if not pok:
        led.unreached(("S7-D2", "S7-D3"), f"M is not pickable in the drawn list: {pwhy}")
        return
    g.press("confirm", 4)
    tgt = cb.wait_panel(g, "target", 3.0)
    if tgt is None:
        led.unreached(("S7-D2", "S7-D3"), f"Confirm on M opened no target panel (an SFX-101 bounce?): {cb.hud_brief(g.state)}")
        return
    f0 = cb.frame_of(tgt)
    samples, _ = cb.watch(g, lambda s: cb.hud(s).get("panel") != "target" or cb.frame_of(s) >= f0 + HOLD_FRAMES, 6.0)
    bounced = [cb.frame_of(x) for x in samples if cb.hud(x).get("panel") != "target"]
    span = (cb.frame_of(samples[-1]) - f0) if samples else 0
    led.check("S7-D2", not bounced and span >= HOLD_FRAMES and (_hit_delta(h0, g.state, "count") or 0) > 0,
              f"target panel from frame {f0}: left it on {bounced[:3]}; held {span} frames; count hits "
              f"+{_hit_delta(h0, g.state, 'count')!r}")
    if cb.hud(g.state).get("panel") != "target":
        led.check("S7-D3", False, f"not reached: no target panel to confirm on ({cb.hud_brief(g.state)})")
        return
    mask, name = cb.target_mask(g.state)
    g.press("confirm", 4)
    st2 = cb.poll(g, lambda s: _menu(s).get("captures") == (c0 or 0) + 1, 3.0, "the item capture") or g.state
    cap = cb.captured(st2)
    dec = cb.decode_cmd(cap.get("hex", ""))
    led.check("S7-D3", isinstance(c0, int) and _menu(st2).get("captures") == c0 + 1 and cap.get("action") == cb.ACT_ITEM
              and cap.get("id") == item and cap.get("local_slot") == 0 and cap.get("site") == "SendCommand"
              and dec is not None and dec.get("action") == cb.ACT_ITEM and dec.get("id") == item
              and _menu(st2).get("r9_refused") == 0 and r90 == 0,
              f"captures {c0!r}->{_menu(st2).get('captures')!r} captured={cap} decoded={dec} (target {name!r} "
              f"mask {mask!r}); r9_refused {r90!r}->{_menu(st2).get('r9_refused')!r}")


def _leg_r(g, led: cb.Ledger, ctx: _Ctx) -> None:
    """R: the learned-omitted BLANK row on a REAL party slot. The stand-in (slot 0) cannot show it -- its pa[] is zeroed,
    so it has nothing LEARNED to omit. COOPPARTY seats Vivi / Garnet / Steiner in local slots 1-3 with real learned sets
    (an earlier `menus 1` listed Vivi's Black Magic Fire enabled); the first of them whose fabrication chooses EVERY
    marker (note null, learned chosen) carries the leg. Runs after D (D needs leg A's slot-0 roster) and before E, whose
    first act re-arms slot 0 -- so G still finds slot 1 absent from the roster."""
    g.note("R: the learned-omitted blank row on a REAL party slot (the stand-in has learned nothing to omit)")
    cb.bmenu_close(g, 0)                   # no slot-0 panel up while the roster changes under it
    slot, br, arm, tried = None, {}, [], []
    for L in REAL_SLOTS:
        at = cb.mark(g)
        ok, why = _bb(g, "roster", "auto", L)
        b = _br(g.state)
        if not ok:
            tried.append(f"slot {L}: refused -- {why[:160]}")
            continue
        lines = cb.wait_log(g, at, ARMED, 2.0)
        if b.get("slot") == L and b.get("note") is None and isinstance(b.get("learned"), int) and b["learned"] > 0:
            slot, br = L, b
            arm = [ln for ln in lines if ARMED + "auto, " in ln and f"; local slot {L} (wire {b.get('wire')}): marker " in ln]
            break
        tried.append(f"slot {L}: note {b.get('note')!r} learned {b.get('learned')!r}")
    st = g.state
    m = _menu(st)
    led.check("S7-R1", slot is not None and len(arm) == 1 and NOT_FABRICATED not in arm[0]
              and br.get("src") == "auto" and isinstance(br.get("wire"), int) and br["wire"] >= 0
              and br.get("uk_menu") in (cb.MENU_ABILITY1, cb.MENU_ABILITY2)
              and isinstance(br.get("unlearned"), int) and br["unlearned"] > 0 and br["unlearned"] != br["learned"]
              and m.get("mirrored") == [slot],
              f"slot {slot!r}: bench_roster={br}; mirrored={m.get('mirrored')!r}; {len(arm)} arm line(s) "
              f"{cb.grep(arm, 'bench menu roster', limit=300)}; skipped: {tried or 'none'}")
    if slot is None:
        led.unreached(("S7-R2",), f"no real party slot in {REAL_SLOTS} fabricated every marker: {'; '.join(tried)}")
        return
    h0 = _hits(g.state)
    ok, why, st = cb.bmenu_open(g, slot)
    if ok:
        ok, why, st = cb.pick_command(g, br.get("uk_menu", -1), expect_panel="ability")
    if not ok:
        led.unreached(("S7-R2",), f"slot {slot}'s own list (menu {br.get('uk_menu')}) never opened: {why}")
        cb.to_root(g)
        cb.bmenu_close(g, slot)
        return
    g.wait_frames(6)
    st = g.state
    un, kn = cb.hud_row(st, br["unlearned"]), cb.hud_row(st, br["learned"])
    _shot(g, ctx, "real", "s7-R-real-abilities")
    sok, sdetail = _shot_ok(ctx, "real")
    led.check("S7-R2", cb.hud(st).get("mirrored") is True and cb.hud(st).get("slot") == slot
              and un is not None and un.get("state") == 2 and cb.strip_tags(un.get("number")) == "1"
              and kn is not None and kn.get("state") == 0 and (_hit_delta(h0, st, "ability") or 0) > 0 and sok,
              f"slot {slot} menu {br.get('uk_menu')} (cmd {br.get('uk_cmd')}) rows {_rows_brief(st)}; unlearned "
              f"{br['unlearned']} -> {un} (its stock MP {br.get('unlearned_local_mp')!r}); learned {br['learned']} -> {kn}; "
              f"mirrored={cb.hud(st).get('mirrored')!r}; ability hits +{_hit_delta(h0, st, 'ability')!r}; {sdetail}")
    cb.to_root(g)
    cb.bmenu_close(g, slot)


def _leg_e(g, led: cb.Ledger, ctx: _Ctx) -> None:
    g.note("E: a double-cast marker makes ONE pick")
    cb.bmenu_close(g, 0)
    ok, why = _bb(g, "roster", "auto", 0, "dbl")
    br = _br(g.state)
    # The double-cast marker is judged on its own: the stand-in's learned gap (run 20261013-131817: marker_cmd 23 =
    # DoubleBlackMagic, note "the slot's own DragonAct holds no LEARNED entry to omit") concerns the LEARN sub-marker,
    # not this one. Still red: no dbl, a marker outside the two double-cast commands, or any other note.
    led.check("S7-E1", ok and br.get("dbl") is True and br.get("marker_cmd") in (DOUBLE_BLACK, DOUBLE_WHITE)
              and _note_ok(br), why or f"bench_roster={br}")
    if not ok:
        led.unreached(("S7-E2",), f"`bbench roster auto 0 dbl` refused -- {why}")
        return
    h0 = _hits(g.state)
    m0 = _menu(g.state)
    c0 = m0.get("captures")
    at = cb.mark(g)
    ok, why, st = cb.bmenu_open(g, 0)
    if ok:
        ok, why, st = cb.pick_command(g, br.get("marker_menu", -1), expect_panel="ability")
    if ok:
        ok, why = cb.pick_row(g, br.get("marker_shown", -1), group=cb.ABILITY_GROUP)
    if not ok:
        led.check("S7-E2", False, f"not reached: {why}")
        return
    dbl_seen = []
    g.press("confirm", 4)
    tgt = cb.wait_panel(g, "target", 3.0)
    if tgt is None:
        led.check("S7-E2", False, f"the marker pick opened no target panel ({cb.hud_brief(g.state)})")
        return
    g.press("confirm", 4)
    samples, st2 = cb.watch(g, lambda s: _menu(s).get("captures") == (c0 or 0) + 1, 3.0,
                            on_sample=lambda s: dbl_seen.append(cb.hud(s).get("double_cast"))
                            if cb.hud(s).get("double_cast") not in (0, None) else None)
    st2 = st2 or g.state
    cap = cb.captured(st2)
    lines = cb.new(g, at)
    led.check("S7-E2", st2 is not None and isinstance(c0, int) and _menu(st2).get("captures") == c0 + 1
              and cap.get("action") == cb.ACT_ABILITY and cap.get("menu") == br.get("marker_menu")
              and cap.get("id") == br.get("marker_shown") and not dbl_seen and (_hit_delta(h0, st2, "cast") or 0) > 0
              and any(ONE_PICK in ln for ln in lines),
              f"captures {c0!r}->{_menu(st2).get('captures')!r} captured={cap} (want action 2, menu {br.get('marker_menu')}, "
              f"id {br.get('marker_shown')}); double_cast non-zero on {dbl_seen[:4]}; panel now {cb.hud(g.state).get('panel')!r}; "
              f"cast hits +{_hit_delta(h0, st2, 'cast')!r}; {cb.grep(lines, ONE_PICK)}")


def _leg_f(g, led: cb.Ledger, ctx: _Ctx) -> None:
    g.note("F: a roster change repaints the open list in place (the deployment notes' re-arm first)")
    cb.bmenu_close(g, 0)
    ok, why = _bb(g, "roster", "auto", 0)
    br = _br(g.state)
    if ok:
        ok, why, _ = cb.bmenu_open(g, 0)
    if ok:
        ok, why, _ = cb.pick_command(g, br.get("marker_menu", -1), expect_panel="ability")
    if ok:
        ok, why = cb.pick_row(g, br.get("marker_shown", -1), group=cb.ABILITY_GROUP)
    if not ok:
        led.unreached(("S7-F1", "S7-F2", "S7-F3"), f"the marker list never opened under a fresh roster: {why}")
        return
    st0 = g.state
    cur0 = cb.cursor_label(st0)
    m0 = _menu(st0)
    h0 = _hits(st0)
    gen0 = m0.get("roster_gen")
    try:
        st1 = cb.ns_verb(g, "bbench", "roster", "auto", 0, "mp=9", "grey")
    except HarnessError as err:
        led.unreached(("S7-F1", "S7-F2", "S7-F3"), f"`bbench roster auto 0 mp=9 grey` refused -- {str(err)[:300]}")
        cb.to_root(g)
        return
    f1 = cb.frame_of(st1)
    want = lambda s: ((cb.hud_row(s, br.get("marker_shown", -1)) or {}).get("state") == 1
                      and cb.strip_tags((cb.hud_row(s, br.get("marker_shown", -1)) or {}).get("number")) == "9")
    samples, hit = cb.watch_from(g, st1, want, 2.0)
    fhit = cb.frame_of(hit) if hit is not None else None
    left = [cb.frame_of(x) for x in samples if cb.hud(x).get("panel") != "ability"]
    # F3's OWN window: watch_from answers AT the ack when the repaint already landed by then (run 20261013-131817:
    # samples == [the ack, 2609] and the next read was the shot's, 2629 -- F3 measured the sampler), so read every
    # publish from here until the first one PAST the mute window before the shot's own wait.
    msamples, _ = cb.watch(g, lambda s: cb.frame_of(s) > f1 + MUTE_FRAMES, 2.0)
    _shot(g, ctx, "repaint", "s7-F-repainted")
    st2 = g.state
    led.check("S7-F1", hit is not None and fhit - f1 <= REPAINT_FRAMES and not left and cb.cursor_label(st2) == cur0
              and cb.hud(st2).get("panel") == "ability" and want(st2),
              f"re-armed at frame {f1}; '9'+grey seen at {fhit!r}; left the ability panel on {left[:3]}; cursor "
              f"{cur0!r} -> {cb.cursor_label(st2)!r}; rows {_rows_brief(st2)}")
    m2 = _menu(st2)
    led.check("S7-F2", _hit_delta(h0, st2, "refresh") == 1 and isinstance(gen0, int) and m2.get("roster_gen") == gen0 + 1
              and m2.get("roster_painted") == m2.get("roster_gen"),
              f"refresh hits +{_hit_delta(h0, st2, 'refresh')!r}; roster_gen {gen0!r}->{m2.get('roster_gen')!r} painted "
              f"{m2.get('roster_painted')!r}")
    # Judged on every publish from the ack on (the engine releases MuteActiveSound 2 frames after the repaint --
    # StockMenuMute / StockMenuMuteSettle), not on when the sampler first caught a false: see _mute_verdict.
    mok, held, first_past, past_val = _mute_verdict(samples + msamples, f1)
    released = cb.first_frame([x for x in samples + msamples if cb.frame_of(x) >= f1],
                              lambda x: _menu(x).get("mute_held") is False)
    led.check("S7-F3", mok and _menu(st2).get("mute_held") is False,
              f"mute_held true on {held[:4]} (seen: {bool(held)} -- a 2-frame hold can fall between publishes; all must "
              f"be <= {f1 + MUTE_FRAMES}); first false at {released!r}; first publish past the window {first_past!r} "
              f"mute_held {past_val!r}; after the shot (frame {cb.frame_of(st2)}) {_menu(st2).get('mute_held')!r} "
              f"(re-arm ack {f1}; {len(msamples)} window publishes)")
    cb.to_root(g)


def _leg_g(g, led: cb.Ledger, ctx: _Ctx) -> None:
    g.note("G: an unmirrored slot (1) keeps its own content")
    br = ctx.br or {}
    cb.bmenu_close(g, 0)
    ok, why, st = cb.bmenu_open(g, 1)
    if not ok:
        led.check("S7-G1", False, f"not reached: slot 1's window never opened ({why})")
        return
    mirrored = cb.hud(st).get("mirrored")
    ch = cb.hud_cmd(st, cb.MENU_CHANGE) or {}
    ok2, why2, st2 = cb.pick_command(g, cb.MENU_ITEM, expect_panel="item")
    g.wait_frames(6)
    st2 = g.state
    pot = cb.hud_row(st2, cb.POTION)
    led.check("S7-G1", mirrored is False and ch.get("state") == 2 and ok2 and pot is not None
              and cb.strip_tags(pot.get("number")) == str(ctx.potion_n) and cb.hud_row(st2, br.get("item", -1)) is None,
              (why2 or "") + f" mirrored={mirrored!r} Change={ch}; item rows {_rows_brief(st2)} (want Potion x{ctx.potion_n}, "
                             f"no item {br.get('item')})")
    cb.to_root(g)
    cb.bmenu_close(g, 1)


def _leg_h(g, led: cb.Ledger, ctx: _Ctx) -> None:
    g.note("H: `bbench roster clear` -- slot 0 draws stock again")
    ok, why = _bb(g, "roster", "clear")
    st = g.state
    m = _menu(st)
    ok2, why2, st2 = cb.bmenu_open(g, 0)
    base = ctx.base or {}
    mk_menu = (ctx.br or {}).get("marker_menu", -1)
    mk = cb.hud_cmd(st2, mk_menu) or {}
    ch = cb.hud_cmd(st2, cb.MENU_CHANGE) or {}
    led.check("S7-H1", ok and m.get("mirrored") == [] and m.get("roster_src") is None and ok2
              and cb.hud(st2).get("mirrored") is False and mk.get("id") == (base.get(mk_menu) or (None,))[0]
              and ch.get("state") == 2,
              (why or why2) or f"mirrored={m.get('mirrored')!r} roster_src={m.get('roster_src')!r}; reopened: "
                               f"{_cmds_brief(st2)} (BASE {base})")
    cb.bmenu_close(g, 0)


def _leg_x(g, led: cb.Ledger, ctx: _Ctx) -> None:
    g.note("X: the plan's raw-hex roster through the REAL ParseRoster")
    item = (ctx.br or {}).get("item")
    if not isinstance(item, int) or item < 0:
        led.unreached(("S7-X1", "S7-X2", "S7-X3"), "no marker item M from leg A to compose the hex roster with")
        return
    data = cb.roster_bytes({0: [{"menu": cb.MENU_ATTACK, "cmd": cb.CMD_ATTACK, "type": 0, "tinfo": 0, "abils": []},
                                {"menu": cb.MENU_ABILITY1, "cmd": WHITE_MAGIC_GARNET, "type": 1, "tinfo": 0,
                                 "abils": [{"id": 1, "mp": 1, "on": True, "tinfo": 1}]}]},
                           [{"id": item, "count": 77, "tinfo": 1}])
    hexs = cb.hexstr(data)
    mine = cb.roster_published(cb.roster_decode(data))
    at = cb.mark(g)
    ok, why = _bb(g, "roster", *hexs.split())
    st = g.state
    lines = cb.wait_log(g, at, ARMED, 2.0)
    m = _menu(st)
    br = _br(st)
    led.check("S7-X1", ok and br.get("src") == "hex" and br.get("bytes") == len(data) and m.get("roster") == mine
              and any(ARMED + f"hex, {len(data)} bytes through the REAL ParseRoster; wire slot(s) 0, 1 item(s)) [{hexs}]" in ln
                      for ln in lines),
              why or f"published roster {m.get('roster')} vs decoded {mine}; bench_roster src={br.get('src')!r} "
                     f"bytes={br.get('bytes')!r} (sent {len(data)}: [{hexs}]); {cb.grep(lines, 'bench menu roster')}")
    bad = []
    for name, junk in (("version 2", bytes([2]) + data[1:]), ("truncated", data[:-1])):
        okb, whyb = _bb(g, "roster", *cb.hexstr(junk).split())
        if okb or f"the REAL ParseRoster refused those {len(junk)} bytes" not in whyb:
            bad.append(f"{name}: {'ACCEPTED' if okb else whyb[:160]}")
    led.check("S7-X2", not bad and _br(g.state).get("src") == "hex", "; ".join(bad) or "both refused by name; the hex roster kept")
    ok3, why3, st3 = cb.bmenu_open(g, 0)
    row = cb.hud_cmd(st3, cb.MENU_ABILITY1) or {}
    led.check("S7-X3", ok3 and row.get("id") == WHITE_MAGIC_GARNET and row.get("state") == 2,
              why3 or f"Ability1 row {row}; commands {_cmds_brief(st3)}")
    cb.bmenu_close(g, 0)


def _release(g, led: cb.Ledger, ctx: _Ctx) -> None:
    """A roster ARMED and the lever PULLED on purpose, then `reset`: both must be released, each with its line. The hex
    form needs no diorama, so this runs on the field after the leave."""
    pre = []
    if ctx.bench_ok:
        okr, whyr = _bb(g, "roster", *cb.hexstr(cb.roster_bytes({0: [{"menu": 0, "cmd": 1, "abils": []}]}, [])).split())
        okc, whyc = _bb(g, "content", "off")
        pre = [w for w in (whyr, whyc) if w]
    at = cb.mark(g)
    cb.release(g)
    st = g.state
    lines = cb.new(g, at)
    m = _menu(st)
    led.check("S7-H2", ctx.bench_ok and not pre and cb.count(lines, REL_CONTENT) == 1 and cb.count(lines, REL_ROSTER) == 1
              and m.get("content_off") == 0 and m.get("bench_roster") is None and (st.netsync or {}).get("forced") is False,
              ("; ".join(pre) if pre else "") + (" `bbench` never worked on this engine" if not ctx.bench_ok else "")
              + f" content_off={m.get('content_off')!r} bench_roster={m.get('bench_roster')!r}; "
                f"{cb.grep(lines, 'released with the harness')}")
