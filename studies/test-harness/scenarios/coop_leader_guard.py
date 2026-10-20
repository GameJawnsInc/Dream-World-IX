"""s143 -- THE GUEST NEVER COMMANDS THE HOST'S LEADER (memoria-patch s143), the solo bench, run unattended.

THE DEFECT (the owner's Plant Brain report, "the host lost control of Zidane"; the read-only diagnosis two skeptics could
not refute). [Netsync] GuestSlots is a party-POSITION mask and every co-op battle lane reads its bit n as btl_data index n.
A story party rebuild can seat the character the host WALKS AS in a guest position: field 257 rebuilds [Blank, Zidane,
Vivi, Steiner] right before Battle(1, 303), so GuestSlots 2 handed the guest ZIDANE for the whole Plant Brain fight (Blank's
code-32 appear re-links him -- the HUD rows shift, ownership does not); field 261 then leaves [Garnet, Zidane, Vivi, Steiner]
for the stretch after the forest.

THE FIX (s143; the owner's decision 2026-10-19 -- positions stay, "by character" is weird because the lineup changes a lot):
a guest bit that lands on the host's LEADER (the CharacterId of its own controlled field body, latched on the field: a body
naming no character keeps it, the world map latches its walker, the title forgets it) moves to the next occupied index after
it, wrapping, that is neither the leader nor already owned; none -> it drops. One pure
rule (NetSyncBattle.LeaderGuard), read by EVERY host ownership lane in battle (EffectiveGuestSlots: the HUD's skip, the
command intake, the roster, G6 / G3, the type-1 header the guest reads) and by the host's field dress sites
(NetSyncClient.FieldGuardMask: the ghost and section 8); a battle-start line on both screens ("Partner: Vivi (not Zidane)"
/ "You: Vivi"). Lever: `netsync bench leaderguard on|off` (selftest role only; off = the pre-s143 positional rule).

THE BENCH. The selftest role (`netsync selftest 1`), `netsync guestslots 2` (party position 1 -- the owner's ini), the
loopback guest. Three party SEATS, each a kit field whose Main_Init rebuilds the party the way the story does (every
RemoveParty first, then the B_PARTYADD in order -- content.party.party_body), its player the kit's Zidane (model 98: the
leader):
    COOPPARTY  30604  [party] add vivi, garnet, steiner on the New-Game base       -> [Zidane, Vivi, Garnet, Steiner]
    COOPFOREST 30608  studies/battle-coop/bench/forestexit.field.toml (field 261) -> [Garnet, Zidane, Vivi, Steiner]
    COOPPBRAIN 30607  studies/battle-coop/bench/plantbrain.field.toml (field 257) -> [Blank, Zidane, Vivi, Steiner]
and one LEADER-BODY seat, the only one whose player is not Zidane:
    COOPVIVI   30609  studies/battle-coop/bench/vivibody.field.toml: no [party] (the seed's), the player the kit's VIVI (8)
Every battle starts from 30602 (LOCKT2: a warm battle return): `battle 67 0` (one Goblin) for the first two seats, `battle
303 0` -- Plant Brain, ITS OWN SCRIPT running (`battle` boots a real, non-debug battle: Ff9mkDebugMenu.StartBattle is
ENCOUNT2's write) -- for the last. The run order, and what each step proves:
  setup  INI (read-only: Enabled 0 or absent; AllCharactersAvailable < 2 -- else every RemoveParty is a no-op; a value that
         does not parse is red) -> OR (the offline oracle) -> S0 (newgame, the COOPPARTY seed, 30602, encounters off, the
         forced role) -> P0 (the s143 keys and the proof line) -> P1 (`guestslots 2`) -> P2 (the lever at rest -- or pulled
         for calibration) -> PRE (the fields)
  L10    THE LEADER BODY (30609, the kit's Vivi walking COOPPARTY's party): `host.guard.leader` 1 off `leader_model` 8 -- the
         latch reads the BODY, not a constant; `selfdress wire 98` (the stand-in wire body GhostGuard dresses) + `selfdress
         ghost 2` -> bit 1 is the LEADER now: the mirror wears GARNET (185, rig 2), `netsync.dress.guard` {leader 1, raw 2,
         effective 4, moved 1 -> 2}, its field line once.
  L7     THE NEGATIVE CONTROL on COOPPARTY's party (the leader at position 0, outside the guest's bit): on the field
         `selfdress ghost 2` -> the mirror wears Vivi (8, rig 1) and `netsync.dress.guard` reads nothing moved (raw 2,
         effective 2, moved -1/-1); then `battle 67 0` -> `host.guard` effective == raw == 2, moved -1/-1, chars [0, 1, 2,
         3], the lines "Partner: Vivi" / "You: Vivi" (header mask 2). The fight is won and the field comes back.
  L8     THE FOREST-EXIT SEAT (30608 -> 30602, `battle 67 0`): `host.guard` effective 0x4, moved 1 -> 2, chars [2, 0, 1, 3];
         the latch line; "Partner: Vivi (not Zidane)" on the HUD; the guest's "You: Vivi" off a header mask of 0x4.
  L0     THE PLANT BRAIN SEAT (30607): `netsync.dress.party` == [10, 0, 1, 3] -- the oracle's seat (FF9.party, raw).
  L6     ...its FIELD half, on 30607: `selfdress ghost 2` -> the selftest mirror's ghost wears VIVI (model 8, rig 1), not
         Zidane (98), and `netsync.dress.guard` == {leader 0, raw 2, effective 4, moved 1 -> 2}, with its line once.
  L1     `battle 303 0` from 30602, at its first command phase: `host.guard` == {leader 0, leader_model 98, raw 2,
         effective 4, moved_from 1, moved_to 2, off false, chars [10, 0, 1, 3] (Blank HIDDEN at boot, counted), nonce = the
         battle's} and exactly one latch line naming them.
  L5     THE LINES: `host.guard.line` == "Partner: Vivi (not Zidane)" ON SCREEN -- the agent's `battle.message` (the dialog
         box's own label) reads it within MESSAGE_S of the command phase: the engine's `line_shown` alone is the engine's own
         claim --, its log line once; the loopback guest's `peer.guard` == {nonce, mask 0x4, "You: Vivi", shown false} -- the
         guest reads only the HEADER: its mask IS the host's guarded offer. (L7 / L8 judge their lines the same way.)
  L2     THE HOST'S WINDOWS, from the first command phase + GRACE_FRAMES (the documented start race: a full gauge may open
         locally for its first turn) to Blank's appear, every state the driver READ with the loopback live (the session's
         ring: the drive loop reads every ~20 ms, each command's ack and each `bcmd`'s settle window read continuously):
         turn.slot reads 1 (Zidane) at least once and NEVER 2 (Vivi). The bench commands every host window (Attack, Plant
         Brain) so the HUD moves on -- a window it does not command stays open, so a read cannot miss one. The window opens
         at the first command phase's frame, never the first sample the ring still holds: a ring gap (the ring lost the
         start) reads "not reached".
  L9     THE OTHER LANES, off the same reads: the loopback roster (`menu.roster_slots`: BuildRoster) reads [2] at least once
         and never holds 1; the G3 hold (`host.handback.held`: HostHeldGuestSlot) never names 1. (`g6_mask` is no ownership
         witness: G6 withholds whatever unit the host's window holds, owned or not.)
  L3     THE INTAKE: a `bcmd` for slot 1 (the leader) is refused -- cmd_dropped +1, dropped_why "slot 1 is not a guest
         slot", "peer command for slot 1 refused (not a guest slot)" once; a `bcmd` for slot 2 once its Ready bit is up
         LANDS -- cmd_queued +1, "peer command: slot 2 Attack -> mask 0x10" once, 2 in turn.done. A `bcmd` the PHASE gate
         refused instead (cmd_refused advanced, cmd_dropped not: drained after the command phase closed) is resent, at most
         BCMD_TRIES times.
  L4     BLANK'S APPEAR (Plant Brain's own trigger: its 7th turn, 916 damage, or Zidane LowHP / KO -- the bench keeps
         attacking): a BRACKETED witness -- a command-phase publish with no slot-0 player in `battle.units`, then one with
         Blank linked at its HEAD -- across which `host.guard` (effective, moved, chars, nonce) is UNCHANGED, bit 0 stays
         off the mask, and the host's window opens on Blank (turn.slot 0) within APPEAR_HOLD_S: Blank is the host's.
  R      `reset` releases the role, the guestslots override and -- when pulled -- the lever ("leader guard back ON
         (released with the harness)" once); RE-READ WITH THE ROLE (`netsync selftest 1` releases nothing): off false.
The Plant Brain fight is LAST and left running (a level-1 party): the session teardown quits it.

THE ORACLE (S143-OR), offline, before anything is launched -- never the engine's answer: the seats' [party] blocks through
the kit's own content.party (CharacterOldIndex -> CharacterId: battlewire.OLD_INDEX_TO_ID) folded by battlewire.seat_after
(RemoveParty, then B_PARTYADD into the first empty seat) onto the New-Game base [Zidane]; the battle's units by
battlewire.battle_slot_chars (InitPlayerData's compaction); each DEPLOYED seat's `.eb` (the highest-priority mod folder
that ships it -- the DictionaryPatch registration names it) PREFLIGHTED: its Main_Init must open with exactly the toml's
RemoveParty / B_PARTYADD sequence (a STALE seat fails closed) and its player entry's SetModel names the body (98); the
leader is that body through battlewire.leader_char_for_model (the rig table + the census's Zidane variants); every expected
mask, move and dress through battlewire's twins (leader_guard, selftest_dress, guard_line_text, guard_latch_line). Plant
Brain's hidden member is Blank (CharacterId 10: EF_E009 hides the linked player whose B_MEMBER(66) is BLANK / BLANK_ARMOR).

PRECONDITIONS -- THE OPERATOR'S JOB (the bench edits no ini, deploys nothing, launches nothing): the DLL under test
deployed, controllers OFF (THE UNATTENDED LAW), FF9 unfocused; [Netsync] Enabled 0 (the runners' selftest_block.sh flips
it, byte-exact restore); 30602 / 30604 / 30607 / 30608 / 30609 registered (30607, 30608 and 30609 are NEW: their first
deploy needs a relaunch -- studies/battle-coop/bench/run/cal143.example.sh).

WHAT NO SOLO BENCH REACHES (named, not hidden): a world-map battle after a load (the latch's world-map walker and the
title's forget are the engine selftest's and the stand-in's rows), a real guest's diorama line (`peer.guard.shown` true,
on time or late), and a real host's section 8 / header at a seat (full143.example.sh STEP 6b records a host tape on the
Plant Brain seat and checks both with coop_peer.py).

CALIBRATION -- a check that cannot fail is not a check.
  * ON s141 (the live DLL at writing, Assembly-CSharp 0293cb46ffa176f6) with COOP_CALIBRATE=1: no `host.guard`, so the
    lever is never sent (the driver's NETSYNC_BENCH_OPS gate: an s141 agent reads `bench leaderguard` as `bench 1`). Red,
    exactly (OLD_PREDICTED): P0 (absent), P2 (the lever's keys absent), L1 / L5 / L7 / L8 / L10 (their keys absent), L2
    (Zidane never opens on the host while the guest is live; Vivi does), L3 (slot 1 is the guest's, slot 2 is not), L4 (no
    key to judge "unchanged"), L6 (the ghost wears Zidane; no `dress.guard`), L9 (the roster carries slot 1, the hold names
    it). GREEN: S0, OR, PRE, P1, L0 (the seat is the kit field's, engine-independent: it calibrates the SEAT, not the
    guard), R (the role and the override).
  * ON s143 with COOP_CALIBRATE=1: `bench leaderguard off` at P2 (the pre-s143 rule, battle AND field), held to the end.
    Red, exactly (LEVER_PREDICTED), each BEHAVIOURALLY: L1 (effective 2, off true), L2 (the host loses Zidane), L3, L5
    ("Partner: Zidane"), L6 (the ghost wears Zidane), L8, L9 (the roster carries Zidane), L10 (the ghost wears Vivi -- the
    latch still reads Vivi: the lever unguards the SITE). GREEN: L0, L4 (the appear moves nothing either way; Blank is the
    host's), L7 (nothing moves either way), R (the release line, off false re-read with the role).
  * OFFLINE: the stand-in (tools/harness/fakegame.py, rung `leaderguard`, ``battle_seat_party``) models the guard and its
    FAULT LEVERS (FakeGame.guard_faults); ff9mapkit/tests/test_coop_leader_guard.py smokes this bench against it and turns
    each fault red in exactly its GUARD_FAULT_REDS row -- never read S143-CAL offline: the engine is the calibration.

    py tools/play.py studies/test-harness/scenarios/coop_leader_guard.py --field 30602
    COOP_CALIBRATE=1 py tools/play.py studies/test-harness/scenarios/coop_leader_guard.py --field 30602
"""
from __future__ import annotations

import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file

HarnessError = cb.HarnessError
BW = None                                                  # battlewire, bound by _bw() (the driver puts tools/ on sys.path)


def _bw():
    global BW
    if BW is None:
        from harness import battlewire
        BW = battlewire
    return BW


_bw()

PROBE = cb.R3_PROBES[143]                                  # netsync.battle.host.guard: the s143 capability
PEER_PROBE = "netsync.battle.peer.guard"
DRESS_PROBE = "netsync.dress.guard"
BATTLE_FIELD = cb.FIELD                                    # 30602 LOCKT2: every battle starts here (a warm return)
PARTY_FIELD = cb.PARTY_FIELD                               # 30604 COOPPARTY (the negative control's party)
PB_FIELD = 30607                                           # COOPPBRAIN (field 257's party)
FX_FIELD = 30608                                           # COOPFOREST (field 261's party)
BODY_FIELD = 30609                                         # COOPVIVI (the leader body: the kit's Vivi walks it)
NEEDED_FIELDS = (BATTLE_FIELD, PARTY_FIELD, PB_FIELD, FX_FIELD, BODY_FIELD)
BENCH = cb.REPO / "studies" / "battle-coop" / "bench"
TOMLS = {PARTY_FIELD: BENCH / "coopparty.field.toml", PB_FIELD: BENCH / "plantbrain.field.toml",
         FX_FIELD: BENCH / "forestexit.field.toml", BODY_FIELD: BENCH / "vivibody.field.toml"}
BODY_WIRE = 98                                             # L10: `selfdress wire 98` -- a wire body GhostGuard dresses
NEW_GAME_PARTY = [0, -1, -1, -1]                           # FF9Play_SetParty(0, Zidane): the New-Game base
GUEST_SLOTS = 2                                            # the owner's ini: party position 1
GOBLIN = cb.SCENE                                          # 67, one Goblin
PLANT_BRAIN = 303
SCENE_GROUP = 0
PB_HIDDEN_CHAR = 10                                        # Blank: EF_E009 hides B_MEMBER(66) BLANK / BLANK_ARMOR at boot
EVT_LANG = "us"
EVT_DIR = ("StreamingAssets", "assets", "resources", "commonasset", "eventengine", "eventbinary", "field")
OP_DEFINE_PLAYER, OP_SET_MODEL, OP_REMOVE_PARTY, OP_EXPR = 0x2C, 0x2F, 0xDD, 0x05
PARTYADD_HEAD, PARTYADD_TAIL = bytes((0x05, 0xC5, 0x93, 0x7D)), bytes((0x6D, 0x2C, 0x7F))   # content.party.add_member
INTRO_S = 60.0                                             # the opening camera (a scripted battle plays its whole intro)
GRACE_FRAMES = 60                                          # L2: the start race's window (a full gauge may open locally once)
LINES_S = 30.0                                             # ...the guest's line waits for a player's first Ready bit
WINDOW_S = 150.0                                           # L2 / L3: Zidane's window and Vivi's Ready bit
APPEAR_S = 300.0                                           # L4: Plant Brain's trigger (its 7th turn, 916 damage, Zidane low)
APPEAR_HOLD_S = 10.0                                       # ...then Blank's full gauge opens his window
FIGHT_S = 240.0
GHOST_SETTLE_S = 1.6                                       # a `selfdress` op -> the ghost re-dressed and held
GHOST_HOLD = 3                                             # publishes the judged ghost tuple must have held
BCMD_SETTLE_S = 1.0                                        # a `bcmd` -> drained, judged, its line written (read meanwhile)
BCMD_TRIES = 3                                             # L3: a `bcmd` the PHASE refused (not the slot) is resent
MESSAGE_S = 6.0                                            # L5 / L7 / L8: the host line on `battle.message` (it shows ~2-4 s)
MESSAGE_POLL_S = 0.1                                       # ...read every 0.1 s (a 2 s message: 20 reads; the ring keeps L2)
CMD_ATTACK, ATTACK_SUB = cb.CMD_ATTACK, cb.ATTACK_SUB

GUARD_HOST_KEYS = ("leader", "raw", "effective", "moved_from", "moved_to", "off", "line", "line_shown", "leader_model",
                   "chars", "nonce")
GUARD_PEER_KEYS = ("nonce", "mask", "line", "shown")
GUARD_DRESS_KEYS = ("leader", "raw", "effective", "moved_from", "moved_to")


def _catalog(calibrate: bool) -> dict:
    c = {
        "S143-INI": "precondition (Memoria.ini, READ-ONLY): [Netsync] Enabled 0 / absent (the selftest role) and [Hacks] "
                    "AllCharactersAvailable < 2 (>= 2 turns every RemoveParty into a no-op: no seat can be built)",
        "S143-OR": "the offline oracle: the three seats' [party] blocks through the kit's content.party + seat_after, each "
                   "DEPLOYED seat's Main_Init party sequence equal to its toml's (never STALE) and its player's body -> "
                   "the leader (the rig table + the Zidane census)",
        "S143-S0": "newgame -> the COOPPARTY seed -> 30602 -> encounters off -> the forced selftest role",
        "S143-P0": f"the engine publishes `{PROBE}` (its {len(GUARD_HOST_KEYS)} keys in order), `{PEER_PROBE}`, "
                   f"`{DRESS_PROBE}` and logged 'leader guard selftest: OK ({_bw().LEADER_GUARD_SELFTEST_ROWS} rows)'",
        "S143-P1": "`netsync guestslots 2` is accepted -- host.guest_slots 2 (the loopback guest's party position 1)",
        "S143-P2": ("the lever PULLED for calibration: `bench leaderguard off` -> host.guard.off true + its OFF line once; on "
                    "the field raw 2 == effective 2" if calibrate else
                    "the lever at rest on the field: host.guard.off false, raw 2 == effective 2 (outside an own battle the "
                    "mask IS GuestSlots), leader == the oracle's (my own body), leader_model == its model"),
        "S143-PRE": "precondition: 30602, 30604 (COOPPARTY), 30607 (COOPPBRAIN), 30608 (COOPFOREST) registered",
        "S143-L10": "THE LEADER BODY (30609 COOPVIVI: the kit's Vivi walks COOPPARTY's party): host.guard.leader 1 off "
                    "leader_model 8; `selfdress wire 98` + `ghost 2` -> the mirror wears GARNET (185, rig 2) -- bit 1 is the "
                    "leader now -- and dress.guard == {leader 1, raw 2, effective 4, moved 1 -> 2}, its field line once",
        "S143-L7": "NEGATIVE CONTROL (COOPPARTY's [Zidane, Vivi, Garnet, Steiner]): `selfdress ghost 2` -> the mirror wears "
                   "Vivi, `dress.guard` nothing moved; `battle 67 0` -> host.guard effective == raw == 2, moved -1/-1, chars "
                   "the oracle's, the lines 'Partner: Vivi' (on `battle.message`) / 'You: Vivi' (header mask 2)",
        "S143-L8": "THE FOREST-EXIT SEAT ([Garnet, Zidane, Vivi, Steiner]), `battle 67 0`: host.guard effective 0x4, moved "
                   "1 -> 2, chars the oracle's, the latch line once; 'Partner: Vivi (not Zidane)'; the guest's 'You: Vivi' "
                   "off a header mask of 0x4",
        "S143-L0": "THE PLANT BRAIN SEAT: netsync.dress.party == the oracle's [Blank, Zidane, Vivi, Steiner] (10, 0, 1, 3)",
        "S143-L6": "its FIELD half (on 30607): `selfdress ghost 2` -> the selftest mirror's ghost wears VIVI (8, rig 1), not "
                   "Zidane; dress.guard == {leader 0, raw 2, effective 4, moved 1 -> 2}; its field line once",
        "S143-L1": "`battle 303 0`, the first command phase: host.guard == {leader, leader_model, raw 2, effective 0x4, "
                   "moved 1 -> 2, off false, chars [10, 0, 1, 3] (Blank hidden, counted), nonce the battle's}; one latch line",
        "S143-L5": "THE LINES: host.guard.line 'Partner: Vivi (not Zidane)' ON SCREEN (`battle.message` reads it -- the "
                   "engine's `line_shown` alone is its own claim), its log line once; peer.guard == {the battle's nonce, mask "
                   "0x4, 'You: Vivi', shown false} and its log line once",
        "S143-L2": f"THE HOST'S WINDOWS, first command phase + {GRACE_FRAMES} frames .. Blank's appear, every state the "
                   "driver read with the loopback live: turn.slot reads 1 (Zidane) at least once and NEVER 2 (Vivi)",
        "S143-L9": "THE OTHER LANES, the same reads: the loopback roster (menu.roster_slots: BuildRoster) reads [2] at least "
                   "once and never holds 1; the G3 hold (host.handback.held: HostHeldGuestSlot) never names 1",
        "S143-L3": "THE INTAKE: a slot-1 `bcmd` is refused ('slot 1 is not a guest slot', cmd_dropped +1, its line once); a "
                   "slot-2 `bcmd` on Vivi's Ready bit LANDS (cmd_queued +1, 'peer command: slot 2 Attack -> mask', 2 in "
                   "turn.done)",
        "S143-L4": "BLANK'S APPEAR, bracketed (no slot-0 player in battle.units, then Blank linked at its head): host.guard "
                   "(effective, moved, chars, nonce) unchanged across it, bit 0 off the mask, the host's window opens on "
                   "Blank (turn.slot 0) -- he is the host's",
        "S143-R": "`reset` releases the role, the guestslots override (guest_slots 0, guard raw / effective 0) and, when "
                  "pulled, the lever ('leader guard back ON (released with the harness)' once); re-read WITH the role: off "
                  "false",
    }
    if calibrate:
        c["S143-CAL"] = ("CALIBRATION: the engine's stage decides the set -- before s143 exactly OLD_PREDICTED red, on s143 "
                         "under `bench leaderguard off` exactly LEVER_PREDICTED red")
    return c


#: every L row: a leg that cannot run records them "not reached"
L_ROWS = ("S143-L10", "S143-L7", "S143-L8", "S143-L0", "S143-L6", "S143-L1", "S143-L5", "S143-L2", "S143-L9", "S143-L3",
          "S143-L4")
#: [calibration] an engine before s143 (s141): every key-judged row and the behavioural L2 / L3 / L6 / L9 red
OLD_PREDICTED = ("S143-P0", "S143-P2", "S143-L1", "S143-L2", "S143-L3", "S143-L4", "S143-L5", "S143-L6", "S143-L7",
                 "S143-L8", "S143-L9", "S143-L10")
#: [calibration] s143 under `bench leaderguard off`: the rows the positional rule changes, each behaviourally
LEVER_PREDICTED = ("S143-L1", "S143-L2", "S143-L3", "S143-L5", "S143-L6", "S143-L8", "S143-L9", "S143-L10")
#: the stand-in's FAULT LEVERS (fakegame.GUARD_FAULTS) -> exactly the rows each turns red (tests pin it)
GUARD_FAULT_REDS = {
    "keys_raw": ("S143-L1", "S143-L8"),
    "lanes_raw": ("S143-L2", "S143-L3", "S143-L9"),
    "roster_raw": ("S143-L9",),
    "hold_raw": ("S143-L9",),
    "header_raw": ("S143-L5", "S143-L8"),
    "line_text": ("S143-L5", "S143-L8"),
    "line_unshown": ("S143-L5", "S143-L7", "S143-L8"),
    "field_raw": ("S143-L6", "S143-L7", "S143-L10"),   # L7's field half reads `dress.guard`'s record: none was written
    "appear_relatch": ("S143-L4",),
    "moves_any": ("S143-L7",),
    "leader_none": ("S143-P2", "S143-L1", "S143-L2", "S143-L3", "S143-L5", "S143-L6", "S143-L8", "S143-L9", "S143-L10"),
    "leader_fixed_zidane": ("S143-L10",),
}
#: ...and in a CALIBRATION run on s143 (the lever pulled at P2): the release that keeps it -- its reds ON TOP of
#: LEVER_PREDICTED (S143-CAL goes red with it: R is a red the lever did not predict)
GUARD_FAULT_REDS_CAL = {"lever_stuck": ("S143-R", "S143-CAL")}


# ------------------------------------------------------------------------------------------------ the offline oracle
def _kit():
    pkg_root = cb.REPO / "ff9mapkit"
    if str(pkg_root) not in sys.path:
        sys.path.insert(0, str(pkg_root))
    import ff9mapkit                                       # noqa: E402 - path pinned above
    where = Path(getattr(ff9mapkit, "__file__", "") or ".").resolve()
    if not where.is_relative_to(pkg_root):
        raise RuntimeError(f"ff9mapkit resolved to {where}, not this worktree's {pkg_root}")
    return ff9mapkit


def toml_party(path: Path) -> tuple:
    """((removes, adds) as CharacterIds, (removes, adds) as CharacterOldIndex) -- a seat's [party] block through the kit's own
    content.party.resolve_member. Raises (OSError / ValueError / KeyError) on an unreadable block."""
    _kit()
    from ff9mapkit.content import party as P
    raw = tomllib.loads(Path(path).read_text(encoding="utf-8")).get("party") or {}
    old_rm = tuple(P.resolve_member(m) for m in raw.get("remove", ()))
    old_add = tuple(P.resolve_member(m) for m in raw.get("add", ()))
    to_id = _bw().OLD_INDEX_TO_ID
    return (tuple(to_id[i] for i in old_rm), tuple(to_id[i] for i in old_add)), (old_rm, old_add)


def eb_party_ops(eb: bytes) -> list:
    """(PURE) The party sequence the kit prepends to Main_Init (entry 0, tag 0), in order: ("remove", CharacterOldIndex)
    for each RemoveParty (0xDD) and ("add", CharacterOldIndex) for each B_PARTYADD expression (05 C5 93 7D <id u16> 6D 2C
    7F), up to the first instruction that is neither."""
    _kit()
    from ff9mapkit.eb import EbScript
    s = EbScript.from_bytes(bytes(eb))
    f = s.entry(0).func_by_tag(0)
    out = []
    if f is None:
        return out
    for ins in s.instrs(f):
        raw = s.data[ins.off:ins.end]
        if ins.op == OP_REMOVE_PARTY and ins.args:
            out.append(("remove", int(ins.args[0])))
        elif ins.op == OP_EXPR and len(raw) == 9 and raw[:4] == PARTYADD_HEAD and raw[6:] == PARTYADD_TAIL:
            out.append(("add", raw[4] | (raw[5] << 8)))
        else:
            break
    return out


def eb_player_model(eb: bytes) -> int | None:
    """(PURE) The controlled body: the LAST entry whose Init (tag 0) runs DefinePlayerCharacter (0x2C) -- its first SetModel
    (0x2F) model id. None when there is none."""
    _kit()
    from ff9mapkit.eb import EbScript
    s = EbScript.from_bytes(bytes(eb))
    model = None
    for e in s.entries:
        if e.empty:
            continue
        f = e.func_by_tag(0)
        if f is None:
            continue
        ins = list(s.instrs(f))
        if any(i.op == OP_DEFINE_PLAYER for i in ins):
            sm = next((i for i in ins if i.op == OP_SET_MODEL and i.args), None)
            if sm is not None:
                model = int(sm.args[0])
    return model


def _folder_order(game: Path) -> list:
    """Memoria.ini [Mod] FolderNames, highest priority first (READ-ONLY)."""
    import re
    try:
        text = (game / "Memoria.ini").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    m = re.search(r'(?mi)^\s*FolderNames\s*=\s*(.+?)\s*$', text)
    return re.findall(r'"([^"]+)"', m.group(1)) if m else []


def deployed_eb(game: Path, field: int) -> tuple:
    """(bytes | None, where) -- the field's `.eb` (language us) from the highest-priority mod folder whose DictionaryPatch
    registers it AND ships its EVT_<name>.eb.bytes. READ-ONLY."""
    import re
    game = Path(game)
    folders = _folder_order(game) or sorted(p.name for p in game.iterdir() if (p / "DictionaryPatch.txt").is_file())
    for name in folders:
        d = game / name
        try:
            text = (d / "DictionaryPatch.txt").read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        m = re.search(rf"(?m)^\s*FieldScene\s+{int(field)}\s+\d+\s+(\S+)", text)
        if not m:
            continue
        p = d.joinpath(*EVT_DIR, EVT_LANG, f"EVT_{m.group(1)}.eb.bytes")
        if p.is_file():
            return p.read_bytes(), str(p)
    return None, f"field {field}: no stacked mod folder registers it with an EVT_*.eb.bytes"


def seat_want(party: list, leader: int, guest_slots: int = GUEST_SLOTS, *, me_model: int | None = None,
              wire: int = -1) -> dict:
    """(PURE) What the s143 rule must do for a seated party: the battle's units (InitPlayerData's compaction), the battle
    mask's move (leader_guard), the field dress's (FieldGuardMask over the RAW seats + the s139 rule: the mirror's model and
    rig for my own body ``me_model`` -- default the plain Zidane -- or the `selfdress wire` body ``wire``)."""
    R = _bw()
    chars = R.battle_slot_chars(party)
    eff, f, t = R.leader_guard(chars, guest_slots, leader)
    feff, mv = R.field_guard_mask("auto", guest_slots, R.live_slot_chars(party), leader)
    worn = R.selftest_dress(ghost_as="auto", guest_slots=0,
                            me_model=R.PLAIN_ZIDANE_MODEL if me_model is None else int(me_model), me_anim=0, party=party,
                            bench_mask=guest_slots, leader=leader, wire=int(wire))
    return {"party": list(party), "chars": chars, "raw": guest_slots & 0x0F, "effective": eff, "moved_from": f,
            "moved_to": t, "field": {"leader": leader, "raw": guest_slots & 0x0F, "effective": feff,
                                     "moved_from": mv[0], "moved_to": mv[1]},
            "ghost": (worn["model"], worn["rig"])}


def read_oracle(game: Path) -> dict:
    """The offline oracle (S143-OR): per seat its party (toml -> seat_after), the deployed `.eb`'s preflight (its Main_Init
    party ops == the toml's, in order) and the player body -> the leader; then each seat's :func:`seat_want`. A seat that
    cannot be read is named in ``problems`` and left out (its rows read "not reached"). ``body``: the LEADER-BODY seat
    (30609: no party ops -- COOPPARTY's party --, its player body another character) and its want under `selfdress wire`."""
    R = _bw()
    out = {"seats": {}, "leader": None, "model": None, "problems": {}, "body": None}
    base = list(NEW_GAME_PARTY)
    for field in (PARTY_FIELD, FX_FIELD, PB_FIELD):
        try:
            (rm, add), (old_rm, old_add) = toml_party(TOMLS[field])
        except (OSError, ValueError, KeyError, TypeError) as err:
            out["problems"][f"toml {field}"] = f"{TOMLS[field].name}: {type(err).__name__}: {str(err)[:160]}"
            continue
        party = R.seat_after(base, rm, add)
        eb, where = deployed_eb(Path(game), field)
        if eb is None:
            out["problems"][f"eb {field}"] = where
            continue
        try:
            ops = eb_party_ops(eb)
            model = eb_player_model(eb)
        except Exception as err:                          # noqa: BLE001 - a parse fault is a named problem
            out["problems"][f"eb {field}"] = f"{where}: {type(err).__name__}: {str(err)[:160]}"
            continue
        want_ops = [("remove", i) for i in old_rm] + [("add", i) for i in old_add]
        if ops != want_ops:
            out["problems"][f"eb {field}"] = (f"STALE: {where} Main_Init opens with {ops[:20]} -- the toml says {want_ops} "
                                              f"(re-deploy the seat)")
            continue
        leader = R.leader_char_for_model(model) if isinstance(model, int) else R.LEADER_NONE
        if leader < 0:
            out["problems"][f"leader {field}"] = f"{where}: the player body {model!r} names no leader"
            continue
        if out["leader"] is not None and leader != out["leader"]:
            out["problems"][f"leader {field}"] = f"{where}: leader {leader} differs from the other seats' {out['leader']}"
            continue
        out["leader"], out["model"] = leader, model
        out["seats"][field] = dict(seat_want(party, leader), where=where)
    _read_body_seat(Path(game), out)
    return out


def _read_body_seat(game: Path, out: dict) -> None:
    """The leader-body seat's oracle (L10): its toml carries no party (the seed's -- COOPPARTY's party stays), its deployed
    `.eb` no party op (never STALE), its player body names a leader OTHER than the seats' (else it proves nothing)."""
    R = _bw()
    cp = out["seats"].get(PARTY_FIELD)
    if cp is None:
        out["problems"]["body"] = "no COOPPARTY oracle: the body seat stands on its party"
        return
    try:
        (rm, add), _old = toml_party(TOMLS[BODY_FIELD])
    except (OSError, ValueError, KeyError, TypeError) as err:
        out["problems"][f"toml {BODY_FIELD}"] = f"{TOMLS[BODY_FIELD].name}: {type(err).__name__}: {str(err)[:160]}"
        return
    if rm or add:
        out["problems"][f"toml {BODY_FIELD}"] = f"the body seat must keep the seed's party (it removes {rm}, adds {add})"
        return
    eb, where = deployed_eb(game, BODY_FIELD)
    if eb is None:
        out["problems"][f"eb {BODY_FIELD}"] = where
        return
    try:
        ops = eb_party_ops(eb)
        model = eb_player_model(eb)
    except Exception as err:                              # noqa: BLE001 - a parse fault is a named problem
        out["problems"][f"eb {BODY_FIELD}"] = f"{where}: {type(err).__name__}: {str(err)[:160]}"
        return
    if ops:
        out["problems"][f"eb {BODY_FIELD}"] = f"STALE: {where} Main_Init opens with party ops {ops[:12]} -- the toml has none"
        return
    want_model = int((tomllib.loads(TOMLS[BODY_FIELD].read_text(encoding="utf-8")).get("player") or {}).get("model", 0))
    leader = R.leader_char_for_model(model) if isinstance(model, int) else R.LEADER_NONE
    if model != want_model or leader < 0 or leader == out["leader"]:
        out["problems"][f"leader {BODY_FIELD}"] = (f"{where}: the player body {model!r} (the toml's {want_model}) -> leader "
                                                   f"{leader} -- the body seat needs a leader other than the seats' "
                                                   f"{out['leader']!r}")
        return
    party = cp["party"]
    out["body"] = dict(seat_want(party, leader, me_model=model, wire=BODY_WIRE), where=where, leader=leader, model=model)


# ------------------------------------------------------------------------------------------------ pure judges
def _guard(x) -> dict:
    g = cb.path(x, PROBE)
    return g if isinstance(g, dict) else {}


def _peer_guard(x) -> dict:
    g = cb.path(x, PEER_PROBE)
    return g if isinstance(g, dict) else {}


def _dress_guard(x) -> dict:
    g = cb.path(x, DRESS_PROBE)
    return g if isinstance(g, dict) else {}


def judge_probe(st, log_lines) -> tuple:
    """P0 (PURE): the three s143 blocks present -- host.guard with its keys in the agent's order -- and the proof line."""
    R = _bw()
    if not cb.has(st, PROBE):
        return False, f"absent: no `{PROBE}` -- an engine before s143"
    keys = list(_guard(st))
    want = f"{R.PROOF_LEADER_GUARD}OK ({R.LEADER_GUARD_SELFTEST_ROWS} rows)"
    proof = cb.count(log_lines, want)
    ok = (keys == list(GUARD_HOST_KEYS) and list(_peer_guard(st)) == list(GUARD_PEER_KEYS)
          and list(_dress_guard(st)) == list(GUARD_DRESS_KEYS) and proof >= 1
          and cb.count(log_lines, R.PROOF_LEADER_GUARD + "FAIL") == 0)
    return ok, (f"host.guard keys {keys}; peer.guard {list(_peer_guard(st))}; dress.guard {list(_dress_guard(st))}; "
                f"'{want}' logged {proof}x")


def judge_rest(st, *, leader: int, model: int, lever: bool) -> tuple:
    """P2 (PURE): on the field the battle mask IS GuestSlots, the field latch my own body's, the lever as set (L10 reads
    the same off the leader-body seat)."""
    if not cb.has(st, PROBE):
        return False, f"absent: no `{PROBE}`"
    g = _guard(st)
    ok = (g.get("off") is bool(lever) and g.get("raw") == GUEST_SLOTS and g.get("effective") == GUEST_SLOTS
          and g.get("leader") == leader and g.get("leader_model") == model)
    return ok, f"host.guard {cb.pick(g, 'off', 'raw', 'effective', 'leader', 'leader_model')} (want off {lever}, raw = " \
               f"effective {GUEST_SLOTS}, leader {leader}, model {model})"


def judge_party(st, want) -> tuple:
    party = (cb.path(st, "netsync.dress") or {}).get("party") if isinstance(cb.path(st, "netsync.dress"), dict) else None
    return party == list(want), f"netsync.dress.party {party!r} (the oracle: {list(want)})"


def ghost_tuple(x) -> tuple:
    gh = (cb.path(x, "netsync.dress.ghost") or {}) if isinstance(cb.path(x, "netsync.dress.ghost"), dict) else {}
    return gh.get("model"), gh.get("rig"), gh.get("bench_mask")


def judge_field(samples, *, want_ghost: tuple, want_guard: dict | None, check: tuple = GUARD_DRESS_KEYS,
                log_lines=(), want_line: str | None = None) -> tuple:
    """L6 / L7's field half (PURE): the LAST publish whose ghost (model, rig) held GHOST_HOLD+ publishes with the `ghost`
    lever published at GUEST_SLOTS (the op landed) and `session.ghost` up: it wears ``want_ghost``; `netsync.dress.guard`
    matches ``want_guard`` on ``check`` (None: not judged -- absent counts red); ``want_line`` logged exactly once."""
    pick, run, last = None, 0, None
    for s in samples:
        t = ghost_tuple(s)
        if cb.path(s, "netsync.session.ghost") is not True or t[2] != GUEST_SLOTS:
            run, last = 0, None
            continue
        run = run + 1 if t[:2] == last else 1
        last = t[:2]
        if run >= GHOST_HOLD:
            pick = s
    if pick is None:
        return False, (f"not reached: no publish with the ghost held {GHOST_HOLD}+ under `selfdress ghost {GUEST_SLOTS}` "
                       f"(last: {ghost_tuple(samples[-1]) if samples else None})")
    worn = ghost_tuple(pick)[:2]
    ok = worn == tuple(want_ghost)
    detail = f"ghost (model, rig) {worn} (want {tuple(want_ghost)})"
    if want_guard is not None:
        if not cb.has(pick, DRESS_PROBE):
            return False, detail + f"; `{DRESS_PROBE}` absent"
        got = {k: _dress_guard(pick).get(k) for k in check}
        ok = ok and got == {k: want_guard[k] for k in check}
        detail += f"; dress.guard {got} (want {({k: want_guard[k] for k in check})})"
    if want_line is not None:
        n = cb.count(log_lines, want_line)
        ok = ok and n == 1
        detail += f"; '{want_line[:90]}' logged {n}x"
    return ok, detail


def judge_keys(st, want: dict, *, nonce=None) -> tuple:
    """L1 / L7 / L8's keys (PURE): host.guard on ``want``'s keys (and its nonce the battle's, when given)."""
    if not cb.has(st, PROBE):
        return False, f"absent: no `{PROBE}`"
    g = _guard(st)
    got = {k: g.get(k) for k in want}
    ok = got == want and (nonce is None or g.get("nonce") == nonce)
    return ok, f"host.guard {got} nonce {g.get('nonce')!r} (want {want}, nonce {nonce!r})"


def unit_names(st) -> list:
    """The names per btl index 0-3 off `battle.units` (a hidden unit: None)."""
    names = [None] * 4
    for u in cb.units(st, player=True):
        s = int(u.get("slot", -1))
        if 0 <= s < 4:
            names[s] = u.get("name")
    return names


def judge_lines(st, lines, *, eff: int, moved_from: int, nonce, names, messages=None) -> tuple:
    """L5 (and L7 / L8's lines) (PURE): the host's line ON SCREEN -- ``messages``, the `battle.message` values the driver
    read from the command phase on (None: not judged), must hold it: a witness the engine's `line_shown` flag is not -- with
    its log line once; the loopback guest's line off the HEADER's mask (== the host's guarded offer) with its log line once
    -- each text computed by the twins."""
    R = _bw()
    if not cb.has(st, PROBE) or not cb.has(st, PEER_PROBE):
        return False, f"absent: no `{PROBE}` / `{PEER_PROBE}`"
    host_want = R.guard_line_text(True, names, eff, moved_from)
    guest_want = R.guard_line_text(False, names, eff, -1)
    g, p = _guard(st), _peer_guard(st)
    host_log = R.guard_host_line_log(host_want, GUEST_SLOTS, eff, shown=True, partner=True)
    guest_log = R.guard_guest_line_log(guest_want, nonce if isinstance(nonce, int) else -1, eff, shown=False, hud=False)
    nh, ng = cb.count(lines, host_log), cb.count(lines, guest_log)
    on_screen = messages is None or host_want in list(messages)
    ok = (g.get("line") == host_want and g.get("line_shown") is True and nh == 1 and on_screen
          and p.get("line") == guest_want and p.get("mask") == eff and p.get("nonce") == nonce and p.get("shown") is False
          and ng == 1)
    seen = sorted({m for m in (messages or ()) if m})
    return ok, (f"host line {g.get('line')!r} shown {g.get('line_shown')!r} (want {host_want!r}, logged {nh}x"
                + ("" if messages is None else f"; on screen: {'yes' if on_screen else 'NOT OBSERVED'} -- battle.message "
                                               f"read {seen[:4]}") + ")"
                + f"; guest {cb.pick(p, 'nonce', 'mask', 'line', 'shown')} (want nonce {nonce!r}, mask {eff}, "
                  f"{guest_want!r}, logged {ng}x)")


def judge_windows(samples, *, leader_idx: int, guest_idx: int, f0: int | None, ring_first: int | None = None) -> tuple:
    """L2 (PURE): over ``samples`` -- (frame, turn.slot, peer.live) of EVERY published state from the first command phase
    (frame ``f0``, the battle's own -- never the first sample the ring still held) to the appear -- after ``f0`` +
    GRACE_FRAMES, with the loopback live: turn.slot reads ``leader_idx`` at least once and never ``guest_idx``.
    ``ring_first`` = the first frame the ring still held at ``f0`` or after: later than the grace = a GAP, "not reached"."""
    if f0 is None or not samples:
        return False, "not reached: no command phase sampled"
    if ring_first is not None and ring_first > f0 + GRACE_FRAMES:
        return False, (f"not reached: a ring gap -- the first sample it held is frame {ring_first}, past the command phase "
                       f"{f0} + {GRACE_FRAMES}: a window on {guest_idx} in the gap would be unseen")
    judged = [(f, s) for f, s, live in samples if f >= f0 + GRACE_FRAMES and live]
    seen = sorted({s for _f, s in judged if s >= 0})
    bad = [f - f0 for f, s in judged if s == guest_idx]
    ok = bool(judged) and leader_idx in seen and not bad
    return ok, (f"{len(judged)} live publish(es) after the grace; host windows opened on {seen} (want {leader_idx} "
                f"among them, never {guest_idx}); on {guest_idx} at +frames {bad[:8]}")


def judge_lanes(samples, *, leader_idx: int, guest_idx: int) -> tuple:
    """L9 (PURE): over ``samples`` -- (frame, roster_slots, handback.held) of every command-phase publish L2 judged: the
    roster (BuildRoster, through the loopback) reads [``guest_idx``] at least once and never holds ``leader_idx``; the G3
    hold (HostHeldGuestSlot) never names ``leader_idx``."""
    if not samples:
        return False, "not reached: no command phase sampled"
    rosters = [tuple(r) for _f, r, _h in samples if isinstance(r, list)]
    held = sorted({h for _f, _r, h in samples if isinstance(h, int) and h >= 0})
    bad_roster = [f for f, r, _h in samples if isinstance(r, list) and leader_idx in r]
    bad_held = [f for f, _r, h in samples if h == leader_idx]
    ok = (guest_idx,) in rosters and not bad_roster and not bad_held
    return ok, (f"{len(samples)} publish(es): rosters {sorted(set(rosters))[:6]} (want ({guest_idx},) among them, never "
                f"{leader_idx}: on {leader_idx} at frames {bad_roster[:6]}); handback.held {held} (never {leader_idx}: at "
                f"frames {bad_held[:6]})")


def judge_appear(pre, post: list, *, hidden_idx: int) -> tuple:
    """L4 (PURE, over raw published states): ``pre`` = the last command-phase publish with no slot-``hidden_idx`` player,
    ``post`` = every state read from the first with that player linked at the HEAD of `battle.units` through
    APPEAR_HOLD_S.
    The guard unchanged across them, the bit off the mask, the host's window on the newcomer."""
    if pre is None or not post:
        return False, ("not reached: no bracketed appear (a command-phase publish without the hidden member, then one with "
                       "it at the head of battle.units)")
    head = cb.units(post[0])
    linked = bool(head) and bool(head[0].get("player")) and int(head[0].get("slot", -1)) == hidden_idx
    if not cb.has(pre, PROBE):
        return False, f"absent: no `{PROBE}` to judge 'unchanged' (linked at the head: {linked})"
    keys = ("effective", "moved_from", "moved_to", "chars", "nonce")
    was = {k: _guard(pre).get(k) for k in keys}
    drift = [(cb.raw(s).get("frame"), {k: _guard(s).get(k) for k in keys}) for s in post
             if {k: _guard(s).get(k) for k in keys} != was]
    owned = (was.get("effective") or 0) & (1 << hidden_idx)
    opened = any(cb.turn(s).get("slot") == hidden_idx for s in post)
    ok = linked and not drift and not owned and opened
    return ok, (f"linked at the head: {linked}; guard before {was}; changed after on {drift[:3]}; bit {hidden_idx} owned: "
                f"{bool(owned)}; the host's window on {hidden_idx}: {opened} ({len(post)} publish(es) after)")


# ------------------------------------------------------------------------------------------------ the run
def run(g, field: int = BATTLE_FIELD):
    calibrate = cb.CALIBRATE
    led = cb.Ledger(g, _catalog(calibrate), finals=("S143-R", "S143-CAL"))
    ctx = {"calibrate": calibrate, "lever": False, "stage": None}
    try:
        _run(g, led, ctx)
    finally:
        g.note(f"Memoria.log archived: {cb.archive_log(g, 'leader-guard')}")
        led.close()
        _release(g, led, ctx)
        if calibrate:
            _judge_cal(led, ctx)
        led.close(final=True)


def stage_of(st) -> int | None:
    """143 when the engine publishes `netsync.battle.host.guard`; else the dress ladder's highest rung (138-141); None."""
    R = _bw()
    if cb.has(st, PROBE):
        return 143
    top = None
    for n in sorted(R.DRESS_PROBES):
        if cb.has(st, R.DRESS_PROBES[n]):
            top = n
    return top


def _judge_cal(led: cb.Ledger, ctx: dict) -> None:
    stage = ctx.get("stage")
    if stage is None:
        led.check("S143-CAL", False, "no engine stage was read (the run died before P0)")
        return
    led.judge_calibration("S143-CAL", OLD_PREDICTED if stage < 143 else LEVER_PREDICTED)


def _ini_ok(g) -> tuple:
    en = cb.ini_value(g, "Netsync", "Enabled")
    aca = cb.ini_value(g, "Hacks", "AllCharactersAvailable")
    try:
        aca_n = int(str(aca).strip()) if aca is not None and str(aca).strip() != "" else 0
    except ValueError:
        aca_n = None                                       # unreadable: the engine's reading is unknown -- red
    ok = (en is None or str(en).strip() in ("0", "")) and aca_n is not None and aca_n < 2
    return ok, (f"[Netsync] Enabled {en!r}; [Hacks] AllCharactersAvailable {aca!r}"
                + (" (does not parse: refused)" if aca_n is None else ""))


def _run(g, led: cb.Ledger, ctx: dict) -> None:
    ok, why = _ini_ok(g)
    led.check("S143-INI", ok, why)
    if not ok:
        led.close("the install's ini refuses the bench (S143-INI)")
        return
    oracle = read_oracle(Path(g.game_path))
    ctx["oracle"] = oracle
    body = oracle.get("body") or {}
    led.check("S143-OR", not oracle["problems"] and len(oracle["seats"]) == 3 and bool(body),
              f"seats {sorted(oracle['seats'])}, leader {oracle['leader']!r} (model {oracle['model']!r}); the body seat "
              f"{BODY_FIELD}: leader {body.get('leader')!r} (model {body.get('model')!r}); problems "
              f"{oracle['problems'] or 'none'}")
    ok, why = cb.setup(g, BATTLE_FIELD, label="s143: the guest never commands the host's leader, solo"
                                              + (" -- CALIBRATION" if ctx["calibrate"] else ""))
    led.check("S143-S0", ok, why)
    st = g.state
    ctx["stage"] = stage_of(st)
    g.note(f"engine stage: {ctx['stage']} ({cb.stage_note(st)})")
    led.check("S143-P0", *judge_probe(st, cb.log_lines(g)))
    ok, why = cb.try_ns(g, "guestslots", GUEST_SLOTS)
    st = cb.poll(g, lambda s: cb.host(s).get("guest_slots") == GUEST_SLOTS, 2.0, "host.guest_slots to read 2") or g.state
    led.check("S143-P1", ok and cb.host(st).get("guest_slots") == GUEST_SLOTS,
              why or f"guest_slots={cb.host(st).get('guest_slots')!r}")
    if not ok:
        led.close(f"`netsync guestslots` refused -- {why}")
        return
    _p2(g, led, ctx)
    try:
        regs = g.registered_fields()[0]
    except (HarnessError, AttributeError, OSError) as err:
        regs = {}
        g.note(f"registrations unreadable: {str(err)[:160]}")
    missing = [f for f in NEEDED_FIELDS if f not in regs]
    led.check("S143-PRE", not missing, f"missing {missing} (deploy: studies/battle-coop/bench/run/cal143.example.sh)"
              if missing else f"{list(NEEDED_FIELDS)} registered")
    if missing:
        led.unreached(L_ROWS, f"fields {missing} are not registered (S143-PRE)")
        return
    seats = oracle["seats"]
    _leg_body(g, led, ctx, oracle.get("body"))
    _leg_l7(g, led, ctx, seats.get(PARTY_FIELD))
    _leg_l8(g, led, ctx, seats.get(FX_FIELD))
    _leg_pb(g, led, ctx, seats.get(PB_FIELD))


def _p2(g, led: cb.Ledger, ctx: dict) -> None:
    oracle = ctx["oracle"]
    leader = oracle["leader"] if oracle["leader"] is not None else 0
    model = oracle["model"] if oracle["model"] is not None else _bw().PLAIN_ZIDANE_MODEL
    if ctx["calibrate"] and ctx["stage"] is not None and ctx["stage"] >= 143:
        at = cb.mark(g)
        ok, why = cb.try_ns(g, "bench", "leaderguard", "off")
        ctx["lever"] = ok
        lines = cb.wait_log(g, at, _bw().LOG_GUARD_OFF, 2.0)
        st = cb.poll(g, lambda s: _guard(s).get("off") is True, 2.0, "host.guard.off to read true") or g.state
        r_ok, r_why = judge_rest(st, leader=leader, model=model, lever=True)
        n = cb.count(lines, _bw().LOG_GUARD_OFF)
        led.check("S143-P2", ok and r_ok and n == 1, why or f"{r_why}; the OFF line logged {n}x")
        g.note("CALIBRATION: `bench leaderguard off` pulled -- the pre-s143 positional rule, battle and field, to the end")
        return
    if ctx["calibrate"]:
        g.note(f"CALIBRATION on stage {ctx['stage']}: no `{PROBE}` -- `bench leaderguard` is NEVER sent (an s141 agent "
               f"reads it as `bench 1`)")
    st = cb.poll(g, lambda s: _guard(s).get("leader") == leader, 3.0, "the field latch") or g.state
    led.check("S143-P2", *judge_rest(st, leader=leader, model=model, lever=False))


def _to_field(g, field: int) -> bool:
    try:
        g.warp(field)
    except HarnessError as err:
        g.note(f"warp {field} failed: {str(err)[:200]}")
        return False
    st = cb.poll(g, lambda s: s.field_id == field and s.on_field and s.ui_state == "FieldHUD", 30.0,
                 f"field {field} up")
    g.wait_frames(45)                                      # Main_Init's party ops run on entry
    return st is not None


def _ghost_leg(g, want: dict, *, check=GUARD_DRESS_KEYS, line: bool = True, wire: int = -1) -> tuple:
    """`selfdress ghost 2` on the current field (after `selfdress wire <wire>` when given), the ghost watched
    GHOST_SETTLE_S, judged, the levers cleared."""
    at = cb.mark(g)
    if wire >= 0:
        ok, why = cb.try_ns(g, "selfdress", "wire", int(wire))
        if not ok:
            return False, f"not reached: `selfdress wire {wire}` refused -- {why}"
    ok, why = cb.try_ns(g, "selfdress", "ghost", GUEST_SLOTS)
    if not ok:
        return False, f"not reached: `selfdress ghost {GUEST_SLOTS}` refused -- {why}"
    samples = cb.hold_for(g, GHOST_SETTLE_S)
    f = want["field"]
    want_line = None
    if line and f["moved_from"] >= 0:
        want_line = _bw().guard_field_log(f["raw"], f["effective"], f["moved_from"], f["moved_to"], f["leader"])
    res = judge_field(samples, want_ghost=want["ghost"], want_guard=f, check=check, log_lines=cb.new(g, at),
                      want_line=want_line)
    cb.try_ns(g, "selfdress", "clear")
    return res


def _battle_up(g, scene: int):
    """Start ``scene`` from 30602 and wait for its first command phase -> (state | None, why)."""
    try:
        g.start_battle(scene, group=SCENE_GROUP)
    except HarnessError as err:
        return None, f"`battle {scene} {SCENE_GROUP}` did not start: {str(err)[:200]}"
    st = cb.poll(g, lambda s: s.commands_enabled, INTRO_S, f"battle {scene}'s command phase")
    return st, "" if st is not None else f"battle {scene} never reached its command phase"


def _latched(g, at: int):
    """The first publish within LINES_S whose guard latch belongs to THIS battle (host.guard.nonce == peer.nonce) and whose
    two lines are published -- the guest's waits for a player's first Ready bit (the last read when it never comes; an
    engine without `host.guard` is read at once: it never latches) -- AND THIS battle's host line logged after ``at``
    (`host.guard.line` keeps the last battle's text until the next GuardLineTick: the identical text must not pass)."""
    if not cb.has(g.state, PROBE):
        return g.state

    def ready(s):
        n = cb.peer(s).get("nonce")
        return (isinstance(n, int) and n >= 0 and _guard(s).get("nonce") == n and _guard(s).get("line") is not None
                and _peer_guard(s).get("nonce") == n)
    st = cb.poll(g, ready, LINES_S, "this battle's guard latch and both lines") or g.state
    cb.wait_log(g, at, _bw().LOG_GUARD_LINE_HOST, LINES_S)
    return g.state if ready(g.state) else st


def _messages(g, frame0: int, want: str) -> list:
    """Every `battle.message` the driver read from ``frame0`` (the command phase) on, reading on (every MESSAGE_POLL_S: the
    ring keeps L2's start -- STATE_RING reads) until ``want`` shows or MESSAGE_S runs out -- the host line's ON-SCREEN
    witness (the agent's dialog-box label: transient, a miss is "not observed")."""
    import time
    got = [cb.battle(x).get("message") for x in (g.states_since(int(frame0) - 1) or [])]
    deadline = time.time() + MESSAGE_S
    while want not in got and time.time() < deadline:
        got.append(cb.battle(g.state).get("message"))
        time.sleep(MESSAGE_POLL_S)
    return got


def _finish(g) -> bool:
    """Fight a Goblin battle out and get back to the field."""
    try:
        g.fight(timeout=FIGHT_S, finish=True)
    except HarnessError as err:
        g.note(f"the fight did not finish: {str(err)[:200]}")
    st = cb.poll(g, lambda s: s.on_field and s.ui_state == "FieldHUD", 45.0, "the field after the battle")
    return st is not None


def _goblin_leg(g, led: cb.Ledger, cid: str, want: dict) -> bool:
    """A `battle 67 0` leg: the keys, the latch line (when something moved), the lines -- judged as ``cid``."""
    at = cb.mark(g)
    st, why = _battle_up(g, GOBLIN)
    if st is None:
        led.check(cid, False, f"not reached: {why}")
        return False
    frame0 = st.frame
    st = _latched(g, at)
    nonce = cb.peer(st).get("nonce")
    keys = {"raw": want["raw"], "effective": want["effective"], "moved_from": want["moved_from"],
            "moved_to": want["moved_to"], "chars": want["chars"]}
    k_ok, k_why = judge_keys(st, keys, nonce=nonce)
    names = unit_names(st)
    msgs = _messages(g, frame0, _bw().guard_line_text(True, names, want["effective"], want["moved_from"]))
    lines = cb.new(g, at)
    l_ok, l_why = judge_lines(st, lines, eff=want["effective"], moved_from=want["moved_from"], nonce=nonce,
                              names=names, messages=msgs)
    latch_ok, latch_why = True, ""
    if want["moved_from"] >= 0:
        R = _bw()
        oracle_leader = want["field"]["leader"]
        latch = R.guard_latch_line(want["chars"], want["raw"], oracle_leader, want["effective"], want["moved_from"],
                                   want["moved_to"], nonce if isinstance(nonce, int) else -1)
        n = cb.count(lines, latch)
        latch_ok, latch_why = n == 1, f"; the latch line logged {n}x"
    led.check(cid, k_ok and l_ok and latch_ok, f"KEYS {k_why}; LINES {l_why}{latch_why}")
    return _finish(g)


def _leg_body(g, led: cb.Ledger, ctx: dict, want: dict | None) -> None:
    """L10: the leader-body seat -- the latch reads the body the host walks (the kit's Vivi), and the field guard moves
    the bit off HER: the mirror (on a plain-Zidane wire body) wears Garnet."""
    g.note("L10: the leader body -- the kit's Vivi walks COOPPARTY's party (30609)")
    if want is None:
        led.unreached(("S143-L10",), f"no oracle for {BODY_FIELD} ({ctx['oracle']['problems']})")
        return
    if not _to_field(g, BODY_FIELD):
        led.unreached(("S143-L10",), f"the leader-body seat {BODY_FIELD} never came up")
        return
    party_ok, party_why = judge_party(g.state, want["party"])
    if not party_ok:
        led.check("S143-L10", False, f"not reached: the seed's party is not the oracle's -- {party_why}")
        return
    st = cb.poll(g, lambda s: _guard(s).get("leader_model") == want["model"], 3.0, "the latch on the body") or g.state
    g_ = _guard(st)
    latch_ok = cb.has(st, PROBE) and g_.get("leader") == want["leader"] and g_.get("leader_model") == want["model"]
    latch_why = (f"host.guard leader {g_.get('leader')!r} leader_model {g_.get('leader_model')!r} (want {want['leader']}, "
                 f"{want['model']})" if cb.has(st, PROBE) else f"absent: no `{PROBE}`")
    f_ok, f_why = _ghost_leg(g, want, wire=BODY_WIRE)
    led.check("S143-L10", latch_ok and f_ok, f"LATCH {latch_why}; FIELD {f_why}")


def _leg_l7(g, led: cb.Ledger, ctx: dict, want: dict | None) -> None:
    g.note("L7: the negative control -- COOPPARTY's party, nothing moves")
    if want is None:
        led.unreached(("S143-L7",), f"no oracle for 30604 ({ctx['oracle']['problems']})")
        return
    st = g.state
    if st.field_id != BATTLE_FIELD and not _to_field(g, BATTLE_FIELD):
        led.unreached(("S143-L7",), "30602 never came up")
        return
    party_ok, party_why = judge_party(g.state, want["party"])
    if not party_ok:
        led.check("S143-L7", False, f"not reached: the seed's party is not the oracle's -- {party_why}")
        return
    f_ok, f_why = _ghost_leg(g, want, check=("raw", "effective", "moved_from", "moved_to"), line=False)
    at = cb.mark(g)
    st, why = _battle_up(g, GOBLIN)
    if st is None:
        led.check("S143-L7", False, f"FIELD {f_why}; not reached: {why}")
        return
    frame0 = st.frame
    st = _latched(g, at)
    nonce = cb.peer(st).get("nonce")
    k_ok, k_why = judge_keys(st, {"raw": GUEST_SLOTS, "effective": want["effective"], "moved_from": want["moved_from"],
                                  "moved_to": want["moved_to"], "chars": want["chars"]}, nonce=nonce)
    names = unit_names(st)
    msgs = _messages(g, frame0, _bw().guard_line_text(True, names, want["effective"], want["moved_from"]))
    l_ok, l_why = judge_lines(st, cb.new(g, at), eff=want["effective"], moved_from=want["moved_from"], nonce=nonce,
                              names=names, messages=msgs)
    nothing = want["effective"] == GUEST_SLOTS and want["moved_from"] < 0     # the oracle's own premise
    led.check("S143-L7", nothing and f_ok and k_ok and l_ok,
              f"oracle: nothing moves {nothing}; FIELD {f_why}; KEYS {k_why}; LINES {l_why}")
    _finish(g)


def _leg_l8(g, led: cb.Ledger, ctx: dict, want: dict | None) -> None:
    g.note("L8: the forest-exit seat -- [Garnet, Zidane, Vivi, Steiner]")
    if want is None:
        led.unreached(("S143-L8",), f"no oracle for 30608 ({ctx['oracle']['problems']})")
        return
    if not _to_field(g, FX_FIELD):
        led.unreached(("S143-L8",), "the forest-exit seat 30608 never came up")
        return
    party_ok, party_why = judge_party(g.state, want["party"])
    if not party_ok:
        led.check("S143-L8", False, f"not reached: the seat did not seat the oracle's party -- {party_why}")
        return
    if not _to_field(g, BATTLE_FIELD):
        led.unreached(("S143-L8",), "30602 never came up after the seat")
        return
    _goblin_leg(g, led, "S143-L8", want)


def _leg_pb(g, led: cb.Ledger, ctx: dict, want: dict | None) -> None:
    g.note("PLANT BRAIN: the seat (L0), its field half (L6), then `battle 303 0` (L1 L5 L2 L3 L4) -- LAST, left running")
    pb_rows = ("S143-L0", "S143-L6", "S143-L1", "S143-L5", "S143-L2", "S143-L9", "S143-L3", "S143-L4")
    if want is None:
        led.unreached(pb_rows, f"no oracle for 30607 ({ctx['oracle']['problems']})")
        return
    if not _to_field(g, PB_FIELD):
        led.unreached(pb_rows, "the Plant Brain seat 30607 never came up")
        return
    ok, why = judge_party(g.state, want["party"])
    led.check("S143-L0", ok, why)
    if not ok:
        led.unreached(pb_rows, f"the seat is not the oracle's (L0): {why}")
        return
    led.check("S143-L6", *_ghost_leg(g, want))
    if not _to_field(g, BATTLE_FIELD):
        led.unreached(pb_rows, "30602 never came up after the seat")
        return
    at = cb.mark(g)
    st, why = _battle_up(g, PLANT_BRAIN)
    if st is None:
        led.unreached(pb_rows, why)
        return
    frame0 = st.frame                                      # the first command phase: L2's window opens here
    st = _latched(g, at)
    nonce = cb.peer(st).get("nonce")
    leader = ctx["oracle"]["leader"]
    keys = {"leader": leader, "leader_model": ctx["oracle"]["model"], "raw": GUEST_SLOTS, "effective": want["effective"],
            "moved_from": want["moved_from"], "moved_to": want["moved_to"], "off": False, "chars": want["chars"]}
    k_ok, k_why = judge_keys(st, keys, nonce=nonce)
    lines = cb.new(g, at)
    latch = _bw().guard_latch_line(want["chars"], GUEST_SLOTS, leader, want["effective"], want["moved_from"],
                                   want["moved_to"], nonce if isinstance(nonce, int) else -1)
    n = cb.count(lines, latch)
    led.check("S143-L1", k_ok and n == 1, f"{k_why}; the latch line logged {n}x")
    # L5 is judged AFTER the drive, on the `battle.message` of every state the drive read from the command phase on (a wait
    # for the line here would let Plant Brain's own clock run ahead of L2 / L3 / L4)
    names = unit_names(st)
    msgs = _drive_pb(g, led, want, frame0)
    led.check("S143-L5", *judge_lines(st, cb.new(g, at), eff=want["effective"], moved_from=want["moved_from"],
                                      nonce=nonce, names=names, messages=msgs))


def _attack(g, st, slot: int) -> None:
    foe = cb.first_enemy(st)
    if foe is None:
        return
    try:
        g.battle_command(slot, CMD_ATTACK, sub=ATTACK_SUB, target=int(foe.get("id", 0x10)))
    except HarnessError as err:
        g.note(f"battlecmd {slot} refused: {str(err)[:160]}")
    g.wait_frames(6)


def _drive_pb(g, led: cb.Ledger, want: dict, frame0: int) -> list:
    """L2 / L3 / L4 on the running Plant Brain battle: command every host window (Attack), send the two `bcmd`s, watch for
    Blank's appear -- each check judged off what was recorded: every state the driver READ since ``frame0`` (the first
    command phase) -- the session's ring, which keeps every read: this loop's (each pass, ~20 ms apart), each command's own
    acks and each `bcmd`'s settle window (which reads continuously) -- never one sample per pass. Returns every
    `battle.message` those states carried (L5's on-screen witness)."""
    import time
    leader_idx, guest_idx = want["moved_from"], want["moved_to"]
    msgs: list = []
    if leader_idx < 0 or guest_idx < 0:
        led.unreached(("S143-L2", "S143-L9", "S143-L3", "S143-L4"), f"the oracle moves nothing on this seat ({want})")
        return msgs
    hidden_idx = want["chars"].index(PB_HIDDEN_CHAR) if PB_HIDDEN_CHAR in want["chars"] else 0
    windows: list = []                                    # (frame, turn.slot, peer.live): the command phase .. the appear
    lanes: list = []                                      # (frame, menu.roster_slots, host.handback.held): the same reads
    f0 = int(frame0)                                      # the battle's own first command phase (never the ring's first)
    ring_first = None                                     # the first frame the ring still held at f0 or after
    refused = {"sent": False, "ok": False, "tries": 0, "why": "not reached: the slot-1 `bcmd` was never sent"}
    landed = {"sent": False, "ok": False, "tries": 0, "why": "not reached: slot 2 never showed its Ready bit to the guest"}
    pre, post, appear_at = None, [], None
    last = int(frame0) - 1
    deadline = time.time() + WINDOW_S + APPEAR_S
    while time.time() < deadline:
        st = g.state
        for x in g.states_since(last) or [cb.raw(st)]:
            fr = int(x.get("frame", last))
            if fr <= last:
                continue
            last = fr
            if ring_first is None:
                ring_first = fr
            if not cb.battle(x).get("active"):
                continue
            msgs.append(cb.battle(x).get("message"))
            enabled = bool(cb.turn(x).get("enabled"))
            players = [int(u.get("slot", -1)) for u in cb.units(x, player=True)]
            linked = hidden_idx in players
            head = cb.units(x)
            head_ok = linked and bool(head) and int(head[0].get("slot", -1)) == hidden_idx
            if appear_at is None and linked and pre is not None and head_ok:
                appear_at = time.time()
            if appear_at is not None:
                post.append(x)
                continue
            if enabled and not linked:
                pre = x
            if enabled:
                windows.append((fr, int(cb.turn(x).get("slot", -1)), cb.peer(x).get("live") is True))
                if fr >= f0 + GRACE_FRAMES:
                    lanes.append((fr, cb.bmenu(x).get("roster_slots"), (cb.host(x).get("handback") or {}).get("held")))
        if not st.in_battle or (appear_at is not None and time.time() - appear_at > APPEAR_HOLD_S):
            break
        if appear_at is None and st.commands_enabled:
            if not refused["sent"] and cb.battle(st).get("phase") == cb.PHASE_NORMAL:
                refused.update(_bcmd_refused(g, st, leader_idx), sent=True)
                refused["tries"] += 1
                if refused.get("phase") and refused["tries"] < BCMD_TRIES:
                    refused["sent"] = False                # the PHASE refused it (drained late): resend, bounded
                continue
            if refused["sent"] and not landed["sent"] and cb.mask_bits(cb.peer(st).get("ready_mask")) & (1 << guest_idx):
                landed.update(_bcmd_landed(g, st, guest_idx), sent=True)
                landed["tries"] += 1
                if landed.get("phase") and landed["tries"] < BCMD_TRIES:
                    landed["sent"] = False
                continue
        if st.commands_enabled and st.turn_slot >= 0:
            _attack(g, st, st.turn_slot)
        else:
            time.sleep(0.02)
    led.check("S143-L2", *judge_windows(windows, leader_idx=leader_idx, guest_idx=guest_idx, f0=f0, ring_first=ring_first))
    led.check("S143-L9", *judge_lanes(lanes, leader_idx=leader_idx, guest_idx=guest_idx))
    led.check("S143-L3", refused["ok"] and landed["ok"], f"SLOT {leader_idx} ({refused['tries']} send(s)): {refused['why']}; "
                                                         f"SLOT {guest_idx} ({landed['tries']} send(s)): {landed['why']}")
    led.check("S143-L4", *judge_appear(pre, post, hidden_idx=hidden_idx))
    return msgs


def _bcmd_refused(g, st, slot: int) -> dict:
    h = cb.host(st)
    d0, q0, r0 = h.get("cmd_dropped"), h.get("cmd_queued"), h.get("cmd_refused")
    foe = cb.first_enemy(st)
    mask = int(foe.get("id", 0x10)) if foe else 0x10
    at = cb.mark(g)
    ok, why = cb.try_ns(g, "bcmd", *cb.cmd_hex(slot, cb.ACT_ATTACK, mask=mask).split())
    if not ok:
        return {"ok": False, "why": f"`bcmd` refused by the agent: {why}"}
    cb.poll(g, lambda s: cb.host(s).get("loop_cmds") == 0, 3.0, "the loopback to drain")
    st2 = (cb.hold_for(g, BCMD_SETTLE_S) or [g.state])[-1]   # READING states meanwhile: L2's ring stays dense
    h2 = cb.host(st2)
    want = f"peer command for slot {slot} refused (not a guest slot)"
    lines = cb.new(g, at)
    n = cb.count(lines, want)
    good = (isinstance(d0, int) and h2.get("cmd_dropped") == d0 + 1 and h2.get("cmd_queued") == q0
            and h2.get("dropped_why") == f"slot {slot} is not a guest slot" and n == 1)
    phase = (not good and isinstance(r0, int) and isinstance(h2.get("cmd_refused"), int) and h2.get("cmd_refused") > r0
             and h2.get("cmd_dropped") == d0)
    return {"ok": good, "phase": phase,
            "why": f"cmd_dropped {d0!r}->{h2.get('cmd_dropped')!r} cmd_queued {q0!r}->{h2.get('cmd_queued')!r} "
                   f"cmd_refused {r0!r}->{h2.get('cmd_refused')!r} dropped_why {h2.get('dropped_why')!r} refused_why "
                   f"{h2.get('refused_why')!r}; '{want}' {n}x; {cb.grep(lines, 'peer command')}"}


def _bcmd_landed(g, st, slot: int) -> dict:
    h = cb.host(st)
    q0, d0, r0 = h.get("cmd_queued"), h.get("cmd_dropped"), h.get("cmd_refused")
    foe = cb.first_enemy(st)
    if foe is None:
        return {"ok": False, "why": "no living enemy to aim at"}
    mask = int(foe.get("id", 0x10))
    at = cb.mark(g)
    ok, why = cb.try_ns(g, "bcmd", *cb.cmd_hex(slot, cb.ACT_ATTACK, mask=mask).split())
    if not ok:
        return {"ok": False, "why": f"`bcmd` refused by the agent: {why}"}
    samples = cb.hold_for(g, BCMD_SETTLE_S)                # READING states meanwhile: L2's ring stays dense
    st2 = samples[-1] if samples else g.state
    want = f"peer command: slot {slot} Attack -> mask 0x{mask:02X}"
    lines = cb.new(g, at)
    n = cb.count(lines, want)
    done = any(slot in (cb.turn(s).get("done") or []) for s in samples)
    h2 = cb.host(st2)
    good = isinstance(q0, int) and h2.get("cmd_queued") == q0 + 1 and n == 1 and done
    phase = (not good and isinstance(r0, int) and isinstance(h2.get("cmd_refused"), int) and h2.get("cmd_refused") > r0
             and h2.get("cmd_dropped") == d0 and h2.get("cmd_queued") == q0)
    return {"ok": good, "phase": phase,
            "why": f"cmd_queued {q0!r}->{h2.get('cmd_queued')!r}; cmd_refused {r0!r}->{h2.get('cmd_refused')!r}; {slot} in "
                   f"turn.done: {done}; '{want}' {n}x; dropped_why {h2.get('dropped_why')!r}"}


def _release(g, led: cb.Ledger, ctx: dict) -> None:
    """`reset` (HarnessSelfTest(false) -> HarnessReleaseBench): the role, the guestslots override, the lever (its line when
    pulled); then -- on an engine with the guard -- the re-read WITH the role (LeaderGuardOn reads the lever only with it:
    a read without the role is green whatever the lever holds). One verdict, after both reads."""
    at = cb.mark(g)
    stage = ctx.get("stage") or 0
    lever = bool(ctx.get("lever"))
    try:
        cb.release(g)
    except HarnessError as err:
        led.check("S143-R", False, f"`reset` failed: {str(err)[:300]}")
        return
    st = g.state
    ns = st.netsync or {}
    ok = ns.get("forced") is False and not cb.dio(st).get("booted") and cb.host(st).get("guest_slots") in (0, None)
    detail = f"forced={ns.get('forced')!r} booted={cb.dio(st).get('booted')!r} guest_slots={cb.host(st).get('guest_slots')!r}"
    if stage >= 143:
        gd = _guard(st)
        ok = ok and gd.get("raw") == 0 and gd.get("effective") == 0
        st2, why = cb.reread_with_role(g)
        off = _guard(st2).get("off") if st2 is not None else None
        n = cb.count(cb.new(g, at), _bw().LOG_GUARD_RELEASED)
        ok = ok and st2 is not None and off is False and n == (1 if lever else 0)
        detail += (f"; guard raw/effective {gd.get('raw')!r}/{gd.get('effective')!r}; " + (why or "")
                   + f"; re-read with the role: off {off!r}; the release line {n}x (want {1 if lever else 0})")
    led.check("S143-R", ok, detail)
