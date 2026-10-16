#!/usr/bin/env python3
"""A protocol stand-in for the in-game agent, so the driver can be tested with no game running.

WHAT THIS PROVES, AND WHAT IT DOES NOT. It implements the s83 wire protocol -- sequence handling,
the arm transition, frame-stepped queue draining, state publication, screenshots -- plus just enough
of a world (a rectangular walkmesh, the engine's 30 Hz field ticks behind a VIRTUAL render rate -- one MovePC call a
tick walking, two running -- a gateway, a dialogue box, a menu cursor, a body
standing in the way and the engine's walk-through-by-insisting, the field's actors published as s89's
``objects`` -- walkers and contact triggers included -- a freeze with control held, stock's door facing
gate, and s90's published facing with its in-place ``turn``) for the
driver's closed-loop verbs to actually close their loops. A green run against it says the DRIVER is
correct: seq numbers advance, acks belong to the request that earned them, torn reads are survived,
timeouts fire, bad bases are rejected, artifacts land.

⚠ IT SAYS NOTHING ABOUT THE ENGINE. It models the agent as SPECIFIED, not the DLL as deployed -- so
a green suite means the driver still handles what it was taught, and nothing about whether a warp
lands, a button moves a character, or the bytes on disk behave. Those are only ever answered by a
real game, and this project has learned repeatedly that a passing offline gate is a regression
harness, not an oracle.

It exists because the alternative is worse: debugging the driver and the engine at the same time,
through a 40-second game launch, with no way to tell which half is lying.

THE FAULT MODES ARE THE POINT. ``FakeGame(mode=...)`` can be a game that freezes its frame counter,
one that slides the character along a wall instead of walking, one that hands over control before it
has a position, one whose agent kept a stale sequence number, and one that never resets on re-arm.
Each of those is a real failure this harness has produced or nearly produced, and each has a driver
behaviour that must be asserted rather than assumed.
"""
from __future__ import annotations

import json
import math
import os
import random
import struct
import threading
import time
import zlib
from pathlib import Path

#: IMPORTED, not restated. This stand-in models the agent AS SPECIFIED, so publishing an older
#: version would put every offline run in the DEGRADED path instead of the real one -- a suite
#: permanently in a compatibility mode it is not meant to be testing. It was a second literal
#: until rev 4, and a second literal is a skew waiting for someone to bump only one of them: that
#: is exactly what happened, and 23 tests failed reporting the wrong cause.
from .channel import BUTTONS, DIRECTIONS, PROTOCOL
from .tickrate import CALLS_PER_TICK, DEFAULT_FIELD_TPS, MAX_DELTA_TIME, TickAccumulator
# [ff9mapkit netsync B4] the battle lane's codec and pure decisions -- the stand-in fabricates through the same functions
# the tests pin to the engine (its `endbench` round trip, ClassifyEnd, the presentation and exit verdicts)
from . import battlewire as BW

#: The real agent polls req.txt every 2 frames while idle and every 10 while a queue is running, and
#: the arm file every 30. Modelled because the driver's "do not overwrite an unaccepted request" gate
#: only means anything against a reader that is not instantaneous.
REQ_POLL_IDLE = 2
REQ_POLL_BUSY = 10
ARM_POLL = 30

#: ``[Graphics] FieldTPS``: the field ticks a second this stand-in runs (times `fast_forward`) -- the engine's
#: default and this install's (harness.tickrate.DEFAULT_FIELD_TPS, the one literal).
FIELD_TPS = DEFAULT_FIELD_TPS

#: The field ticks one frame of the fake's CALIBRATED model holds -- 60 fps, 30 Hz: half a tick. The unit a walker's
#: ``speed`` is given in (units a frame at 60 fps, so ``speed / WALKER_FRAME_TICKS`` a tick), which every walk written
#: before the tick model was written against.
WALKER_FRAME_TICKS = 0.5

#: SCollTimer after a push-out, in field ticks: the engine counts it down once a tick (ProcessEvents), and the push lock
#: counts only while it runs (see `_lock_fallback`). Four frames at 60 fps -- what the fake counted before ticks.
COLL_TICKS = 2.0

#: How the fake turns frames into field ticks (`FakeGame(ticks=...)`): "mean" -- every frame holds its AVERAGE,
#: ``tick_hz / render_fps`` (half a tick at 60 fps: smooth, what every walk written before this was written against);
#: "quantized" -- the engine's WHOLE ticks, FPSManager's accumulator (harness.tickrate.TickAccumulator): 0, 1 or more a
#: frame, in a phase nobody publishes.
TICK_MODES = ("mean", "quantized")

#: The clocks the fake can publish (`FakeGame(publish=...)`): "rt" -- the virtual realtime clock, seconds (a future
#: engine's ``Time.realtimeSinceStartup``); "ticks" -- the field ticks run so far (the s91 counter, a float in mean
#: mode); "mtime" -- no key: state.json's MODIFIED TIME is stamped with the virtual write time instead, and the loop
#: runs in real time (see `publish`), so the driver's mtime path measures the render rate.
PUBLISHED_CLOCKS = ("rt", "ticks", "mtime")

#: The most frames one ``turn`` may hold its keys (HarnessAgent.TurnMaxFrames; its ``frames`` is clamped to
#: 1..this, 30 when not given).
TURN_MAX_FRAMES = 36000
#: Memoria.ini ``[AnalogControl] StickThreshold`` (default 10, in hundredths: Configuration/Access/Control.cs:10):
#: the |axis| over which MovePC's axis branch walks him -- a `turn` is refused, or cut, over it.
STICK_THRESHOLD = 0.10

#: FF9's own soft reset: L1+R1+L2+R2+Start+Select, all reporting IsInputDown on ONE frame.
#: Modelled with the same-frame requirement intact, because that requirement is the whole reason the
#: driver has to send all six in a single request -- six separate presses would never overlap, and a
#: stand-in that accepted them sequentially would let a broken driver pass.
SOFT_RESET_COMBO = ("l1", "l2", "r1", "r2", "start", "select")
#: The agent's `netsync` sub-verbs, in its order (its "unknown sub-verb" refusal prints them): the F3.2 engine (s96,
#: `FakeGame.netsync_caps` empty) and an F3 lockstep engine (s84/s85, `FakeGame.netsync_dialogue` None).
#: [ff9mapkit netsync F3.3] The live stack's agent (s99) adds one verb group per capability, in patch order
#: (:data:`NETSYNC_F33_CAPS`): the stand-in's list is the s96 one plus the groups its `netsync_caps` names.
#: test_harness_netsync.py pins every list to the patch that printed it.
NETSYNC_SUBVERBS_F32 = ("selftest", "bench", "l1", "hostscene", "lock", "stale", "unlock", "click", "drag",
                        "advance", "choice", "unmatched", "talk")
NETSYNC_SUBVERBS_F3 = ("selftest", "bench", "l1", "advance", "choice", "unmatched", "talk")
#: [ff9mapkit netsync F3.3] Each F3.3 capability, in patch order: (the patch, its sub-verbs). Additive under protocol 5 --
#: the contract tag stays "authority", so a capability is told by its keys' PRESENCE (:data:`NETSYNC_CAP_KEYS`).
#:   "diorama" -- s97 DIO-1, the diorama warm return (`netsync.diorama`);
#:   "ring"    -- s98 C3, the section-7 dialogue ring + the bench host (wire v14);
#:   "keys"    -- s99 C3 R5, the script-key relay + the R9 tap-record bench (needs "ring": KEY rides section 7).
NETSYNC_F33_CAPS = {"diorama": ("s97", ("dioboot", "dioleave")),
                    "ring": ("s98", ("host",)),
                    "keys": ("s99", ("tap-record", "replay"))}
#: [ff9mapkit netsync F3.3] The flat keys each capability adds to the `netsync` block (the "diorama" capability adds the
#: one `diorama` block), in AppendRing / AppendKeys order.
NETSYNC_CAP_KEYS = {"diorama": ("diorama",),
                    "ring": ("wire", "epoch", "head_seq", "last_seen", "gaps", "heartbeat", "host_stalled", "host_flags",
                             "host_open", "cursor", "key_ignored", "host_frozen", "host_menu", "host_battle"),
                    "keys": ("key_tick", "key_hold", "key_reader", "keys", "key_served", "key_expired", "key_gaveup",
                             "key_taps", "tap_record", "tape", "replay_left")}
#: [ff9mapkit netsync F3.3] The bench host's ops (NetSyncClient.BenchHostOp), in its "unknown op" refusal's order.
NETSYNC_HOST_OPS = ("open", "shut", "adv", "choice", "key", "gap", "epoch", "freeze", "menu", "battle")
#: [ff9mapkit netsync B4] [ff9mapkit netsync B5] The battle co-op capabilities (studies/battle-coop/B4-B5-DESIGN.md
#: section 7, stages 1-6), in patch order: (the patch, the sub-verbs it adds). Additive under protocol 5 like F3.3, each
#: told by its keys' PRESENCE inside the one `netsync.battle` block (:data:`NETSYNC_BATTLE_CAP_KEYS`). Each needs every
#: capability before it (the stack is a ladder): a set with a gap models no engine.
#:   "gates"       -- s100 stage 1, the host command-phase gates (`netsync.battle` itself);
#:   "containment" -- s101 stage 2, the guest containment backstop R9 + G2 (+ `battle.units[].cmd_busy`);
#:   "stockmenu"   -- s102 stage 3, the guest stock menu's first look + capture (+ `battle.seq`, `battle.hud`);
#:   "endblock"    -- s103 stage 4, the host END BLOCK trailer (+ `battle.result_ui`);
#:   "present"     -- s104 stage 5, the guest's victory presentation (`netsync.battle.end`; `endbench guest`);
#:   "exit"        -- s105 stage 6, the guest's exit with the host (`end.end_leave` / `end.declined`; `endbench exit`);
#:   "content"     -- s106 stage 7, the roster-fed menu content (`menu.content_hits` ...; `bbench roster|content`;
#:                    `battle.hud.mirrored`);
#:   "mirror"      -- s107 stage 8, the production ready mirror + the bench feed (`menu.stock_owns` ...; `bbench start|...`);
#:   "manifest"    -- s108 stage 9, the host result manifest (`host.manifest` ..., `peer.manifest_*`; `endbench manifest`;
#:                    `battle.result_ui` labels / rows / model / items);
#:   "replay"      -- s109 stage 10, the guest result-screen replay (`end.replay`; `endbench fieldsong|replay|quit`;
#:                    `battle.result_ui.replay`);
#:   "handback"    -- s110 stage 11, the host's guest-slot hand-back (`host.handback`; `bench lapse|handback`).
#: [ff9mapkit netsync R3] battle co-op round 3 (studies/battle-coop/R3-DESIGN.md section 4), no new sub-verb:
#:   "intro"       -- s111, the battle intro mirror (`host.cfg` / `host.intro`, `netsync.diorama.intro`; `bench intro|cfg`,
#:                    `battle ... rand`, `dioboot ... [wire] [skip|play|own] [rand]`);
#:   "swirl"       -- s112, the diorama swirl clamp (`netsync.diorama.intro.swirl_clamp`; `bench swirl local|clamp`);
#:   "waitparity"  -- s113, Wait parity (`host.wait`, `menu.ctl`, the feed's `ctl`/`ctl_menu`, `lapse.reserve`;
#:                    `bench waitparity|ctl`, `bench cfg atb`, `bench lapse ... reserve`);
#:   "starthold"   -- s114, the start hold (`host.start_hold`, `menu.ctl` nonce/boot, `netsync.diorama.live`;
#:                    `bench boot|starthold`);
#:   "flee"        -- s115, the guest's flee presentation (`end.flee`, `end_leave.reverted`, `battle.units[].mot|disappear|z`;
#:                    `endbench guest hold|nor9b`);
#:   "fleegil"     -- s116, the host's "Dropped N Gil" relayed (`host.flee_gil`, `end.flee.msg_gil`, `host.end`/`peer.end`
#:                    `flee_gil`; `endbench fleegil`);
#:   "defeat"      -- s117, the guest's defeat presentation (`end.follow_msg`; `endbench kill|phase-defeat`).
#: [ff9mapkit netsync R3 s118-s121] the SITTING-A FIX ROUND (studies/battle-coop/R3-SITTING-A-FIXES.md), no new sub-verb or
#: op. The deployed s117 DLL (the calibration) is the ladder prefix :func:`caps_through` ``("defeat")``:
#:   "ownreport"   -- s118, the hand-back needs a live guest (`host.handback.refused_report|refused_now|diorama_seen`; the
#:                    loopback guest's `bench boot declined|busy|stale` -- and `none` after the latch -- keep its slots);
#:   "holdpeer"    -- s119, the diorama hold keyed on the peer (`netsync.diorama.hold`; the "diorama watcher" proof line);
#:   "grace"       -- s120, the session grace (`netsync.session`; `hold.cap_ms` = the grace; the "session grace" line);
#:   "menurefusal" -- s121, the audible menu refusal (`netsync.menu_refusal`; the "main menu refusal" line).
#: [ff9mapkit netsync s131] THE EXPIRED SEQ (the Pump null re-adopt), no new sub-verb or op. The DEPLOYED s121 DLL (the
#: calibration) is ``caps_through("menurefusal")``:
#:   "expiredseq"  -- s131, the guest's peer adopt step (`netsync.battle.peer.expired`, at its sentinels here: the selftest
#:                    role never runs a view out; the "peer adopt" proof line).
#: [ff9mapkit netsync s132] THE GRACE DEFAULT IS ITS MAXIMUM, no new key, verb or op. Its calibration (s131) is
#: ``caps_through("expiredseq")``:
#:   "grace40"     -- s132, an ABSENT [Netsync] SessionGraceMs reads 40000 (`netsync.session.grace_ms`, `hold.cap_ms`);
#:                    30000 without it. An explicit value reads the same on both.
#: [ff9mapkit netsync s133] GROUP 2 (action replay s133-s137, the guest's field model s138-s141; renumbered from the
#: design's s122-s130 so number order is capture order). Its calibration (s132: the `act` probe fails closed) is
#: ``caps_through("grace40")``:
#:   "actstart"    -- s133, the HOST action-start lane (`netsync.battle.act.host`; the sub-verb `actbench`: `hoststarts
#:                    on|off`, `tape rec|stop|clear|info`, `tape dump <from> <count>`; type-1 caps bit 5; the "action lane"
#:                    proof line). The stand-in models it through battlewire.ActHostLane (see FakeGame._act_command).
#: [ff9mapkit netsync s134] Its calibration (s133: the `act.guest` probe fails closed) is ``caps_through("actstart")``:
#:   "actreplay"   -- s134, the GUEST action replay (`netsync.battle.act.guest`, `battle.units[].anim|anim_frame|away|rot_y|
#:                    acting|die_seq|row`; no new sub-verb -- `actbench` gains the guest ops `feed|feedat|replay|rework|
#:                    shortcircuit|knob|clear|teardown` and the `tape play` value; the "action replay" proof line). The
#:                    stand-in models it through battlewire.ActGuestLane (see FakeGame._act_guest_tick and that class's
#:                    docstring: the decisions are modelled, the sequencer is not).
#: [ff9mapkit netsync s135] Its calibration (s134: the `act.guest.hold` probe fails closed) is ``caps_through("actreplay")``:
#:   "acthold"     -- s135, THE REPLAY HIT HOLD (`netsync.battle.act.guest.hold`, the LAST key of `act.guest`; no new
#:                    sub-verb -- `actbench` gains the guest ops `hold|lifeskip on|off` and `unit <slot> dead|alive|trance0|
#:                    trance1`; the "action hold" proof line). The stand-in models it through battlewire.ActHoldLane (the
#:                    lane's `hold`; see its docstring): from this rung on the arrival path's state writes, figures (figs[])
#:                    and flinch are modelled too -- an s134 stand-in keeps s134's model (pairing only).
#: [ff9mapkit netsync s136] Its calibration (s135: the `act.guest.fallback` probe fails closed) is ``caps_through("acthold")``:
#:   "actfallback" -- s136, FALLBACK A, one stock clip per uncovered action (`netsync.battle.act.guest.fallback`, the LAST key
#:                    of `act.guest`; no new sub-verb -- `actbench` gains the guest op `fallback on|off`; the "action
#:                    fallback" proof line). The stand-in models it through battlewire.ActFallbackLane (the lane's
#:                    `fallback`; see its docstring): from this rung on an uncovered impact's motion step plays the action's
#:                    clip (a unit's `mot` / `anim` read it) -- an s135 stand-in keeps the s110 player-only swing.
NETSYNC_BATTLE_CAPS = {"gates": ("s100", ("guestslots", "bcmd", "hostgates")),
                       "containment": ("s101", ("containment", "bctl")),
                       "stockmenu": ("s102", ("bmenu",)),
                       "endblock": ("s103", ("endbench",)),
                       "present": ("s104", ()),
                       "exit": ("s105", ()),
                       "content": ("s106", ("bbench",)),
                       "mirror": ("s107", ()),
                       "manifest": ("s108", ()),
                       "replay": ("s109", ()),
                       "handback": ("s110", ()),
                       "intro": ("s111", ()),
                       "swirl": ("s112", ()),
                       "waitparity": ("s113", ()),
                       "starthold": ("s114", ()),
                       "flee": ("s115", ()),
                       "fleegil": ("s116", ()),
                       "defeat": ("s117", ()),
                       "ownreport": ("s118", ()),
                       "holdpeer": ("s119", ()),
                       "grace": ("s120", ()),
                       "menurefusal": ("s121", ()),
                       "expiredseq": ("s131", ()),
                       "grace40": ("s132", ()),
                       "actstart": ("s133", ("actbench",)),
                       "actreplay": ("s134", ()),
                       "acthold": ("s135", ()),
                       "actfallback": ("s136", ())}
#: [ff9mapkit netsync R3] Each round's RUNG NAMES -- what that round added to the ladder, nothing more. A calibration engine
#: is NEVER the default stand-in minus a rung set (subtracting one rung keeps every later rung: an engine that never
#: existed -- audit 3.1 / 4.1); it is the ladder PREFIX through the previous rung, :func:`caps_through`.
#: The four sitting-A rungs (s118-s121; their calibration, s117, is ``caps_through("defeat")``).
NETSYNC_SITTING_A_CAPS = frozenset(("ownreport", "holdpeer", "grace", "menurefusal"))
#: [ff9mapkit netsync s131] The expired-seq rung (its calibration, the deployed s121, is ``caps_through("menurefusal")``).
NETSYNC_S131_CAPS = frozenset(("expiredseq",))
#: [ff9mapkit netsync s132] The grace-default rung (its calibration, s131, is ``caps_through("expiredseq")``: an absent
#: SessionGraceMs reads 30000).
NETSYNC_S132_CAPS = frozenset(("grace40",))
#: [ff9mapkit netsync s133] The action-start rung (its calibration, s132, is ``caps_through("grace40")``).
NETSYNC_S133_CAPS = frozenset(("actstart",))
#: [ff9mapkit netsync s134] The guest action-replay rung (its calibration, s133, is ``caps_through("actstart")``).
NETSYNC_S134_CAPS = frozenset(("actreplay",))
#: [ff9mapkit netsync s135] The replay-hit-hold rung (its calibration, s134, is ``caps_through("actreplay")``).
NETSYNC_S135_CAPS = frozenset(("acthold",))
#: [ff9mapkit netsync s136] The fallback-A rung (its calibration, s135, is ``caps_through("acthold")``).
NETSYNC_S136_CAPS = frozenset(("actfallback",))
#: [ff9mapkit netsync B4] The battle sub-verbs in the order the agent PRINTS them: s106 inserted `bbench` before
#: `endbench`, so the list is not the patch order (:func:`netsync_subverbs`). [ff9mapkit netsync s133] `actbench` appends.
NETSYNC_BATTLE_VERB_ORDER = ("guestslots", "bcmd", "hostgates", "containment", "bctl", "bmenu", "bbench", "endbench",
                             "actbench")
#: [ff9mapkit netsync B4] The keys each battle capability adds, by `netsync.battle` sub-object, in the agent's order
#: (AppendNetsyncBattle / AppendBattleEnd / AppendEndLeave) -- `end_leave` and `declined` are the two keys whose values
#: are themselves fixed sub-objects (:data:`NETSYNC_BATTLE_END_LEAVE_KEYS`, :data:`NETSYNC_BATTLE_DECLINED_KEYS`).
NETSYNC_BATTLE_CAP_KEYS = {
    "gates": {"host": ("gates_off", "guest_slots", "cmd_phase", "caps", "ready_mask", "cmd_refused", "cmd_dropped",
                       "cmd_queued", "refused_why", "dropped_why", "roster_lag", "loop_cmds"),
              "peer": ("live", "seq", "nonce", "caps", "ready_mask"),
              "menu": ("roster_slots",)},
    "containment": {"menu": ("r9_refused", "r9_total", "r9_cmd", "r9_site", "guest_owned", "contained",
                             "containment_off")},
    "stockmenu": {"menu": ("captures", "capture_refused", "capture_why", "capture_off", "outbox", "bench_open",
                           "side_refused", "side_why", "captured")},
    "endblock": {"host": ("end", "end_trail", "end_edges", "end_changes", "end_mode", "end_cmd"),
                 "peer": ("end", "end_trail", "trailer_bad", "trailer_skipped", "trailer_why")},
    "present": {"end": ("injected", "held", "kind", "kind_name", "action", "inject_phase", "inject_seq", "inject_ms",
                        "r8_hits", "r8_first_ms", "w1_armed", "watchdog", "blocker", "why", "faulted", "hud_reasserts",
                        "guest_mode", "ach_held", "ach_enemy_no", "music", "btl_flag")},
    "exit": {"end": ("exit_mode", "end_leave", "declined")},
    "content": {"menu": ("mirrored", "roster_src", "roster_sig", "roster_gen", "roster_painted", "content_off",
                         "content_hits", "content_faults", "content_why", "mute_held", "roster", "bench_roster")},
    "mirror": {"menu": ("stock_owns", "why", "knob", "knob_bench", "assist_slot", "stranded", "pending", "pending_mask",
                        "refused", "sent", "mirror", "feed")},
    "manifest": {"host": ("manifest", "manifest_bytes", "manifest_captures", "manifest_skipped", "manifest_why",
                          "manifest_mode", "overflow", "learned"),
                 "peer": ("manifest_bad", "manifest_bad_why", "manifest_nonce", "manifest_rx", "bench_manifest",
                          "bench_manifest_note")},
    "replay": {"end": ("replay",)},
    "handback": {"host": ("handback",)},
    # [ff9mapkit netsync R3] s111-s117 (s112 adds nothing at this level: its block sits inside `netsync.diorama.intro`)
    "intro": {"host": ("cfg", "intro")},
    "swirl": {},
    "waitparity": {"host": ("wait",), "menu": ("ctl",)},
    "starthold": {"host": ("start_hold",)},
    "flee": {"end": ("flee",)},
    "fleegil": {"host": ("flee_gil",)},
    "defeat": {"end": ("follow_msg",)},
    # [ff9mapkit netsync R3 s118-s121] nothing at this level: s118 keys INSIDE `host.handback`, s119 inside
    # `netsync.diorama`, s120 / s121 add TOP-LEVEL `netsync` blocks (NETSYNC_TOP_CAP_KEYS)
    "ownreport": {},
    "holdpeer": {},
    "grace": {},
    "menurefusal": {},
    # [ff9mapkit netsync s131] the last key of `peer`, a FIXED sub-object (:data:`NETSYNC_PEER_EXPIRED_KEYS`)
    "expiredseq": {"peer": ("expired",)},
    # [ff9mapkit netsync s132] no key at all: the agent is s131's (only an absent SessionGraceMs reads differently)
    "grace40": {},
    # [ff9mapkit netsync s133] a FIFTH sub-object, `act`, with its `host` half (a FIXED sub-object:
    # :data:`NETSYNC_ACT_HOST_KEYS`); s134 adds `act.guest` (audit amendment 13: `actbench` is keyed on `act.host`)
    "actstart": {"act": ("host",)},
    # [ff9mapkit netsync s134] `act`'s `guest` half (a FIXED sub-object: :data:`NETSYNC_ACT_GUEST_KEYS`)
    "actreplay": {"act": ("guest",)},
    # [ff9mapkit netsync s135] nothing at this level: `hold` keys INSIDE `act.guest` (NETSYNC_BATTLE_NESTED_KEYS)
    "acthold": {},
    # [ff9mapkit netsync s136] nothing at this level: `fallback` keys INSIDE `act.guest` (NETSYNC_BATTLE_NESTED_KEYS)
    "actfallback": {},
}
#: [ff9mapkit netsync R3] The keys a capability adds INSIDE an older fixed sub-object (dotted under `netsync.battle`).
NETSYNC_BATTLE_NESTED_KEYS = {
    "waitparity": {"host.handback.lapse": ("reserve",)},
    "starthold": {"menu.ctl": ("nonce", "boot", "boot_name")},
    "flee": {"end.end_leave": ("reverted",)},
    "fleegil": {"end.flee": ("msg_gil",)},
    "ownreport": {"host.handback": ("refused_report", "refused_now", "diorama_seen")},   # [ff9mapkit netsync R3 s118]
    "acthold": {"act.guest": ("hold",)},             # [ff9mapkit netsync s135] after `last` (a fixed block)
    "actfallback": {"act.guest": ("fallback",)},     # [ff9mapkit netsync s136] the LAST key of `act.guest` (a fixed block)
}
#: [ff9mapkit netsync R3] The keys a battle capability adds to the F3.3 `netsync.diorama` block (s111 `intro`, s114 `live`;
#: [ff9mapkit netsync R3 s119] `hold`) and inside it (s112 `intro.swirl_clamp`).
NETSYNC_DIORAMA_CAP_KEYS = {"intro": ("intro",), "starthold": ("live",), "holdpeer": ("hold",)}
NETSYNC_DIORAMA_NESTED_KEYS = {"swirl": {"intro": ("swirl_clamp",)}}
#: [ff9mapkit netsync R3 s120/s121] The TOP-LEVEL `netsync` blocks a battle capability adds, in the agent's order --
#: between `diorama` and `battle` (AppendSession, AppendMenuRefusal).
NETSYNC_TOP_CAP_KEYS = {"grace": ("session",), "menurefusal": ("menu_refusal",)}
NETSYNC_BATTLE_END_LEAVE_KEYS = ("trigger", "latched_ms", "tries", "deferred", "requested", "request_ms", "why", "settled",
                                 "via", "stamp", "stamp_host", "stamped", "stamped_was", "music_shut", "music_why",
                                 "wipe_lifted", "reverted")
NETSYNC_BATTLE_DECLINED_KEYS = ("count", "nonce", "why")
#: [ff9mapkit netsync B4] [ff9mapkit netsync B5] s106-s110's FIXED sub-objects (always published whole, in the agent's
#: order): `menu.content_hits`, `menu.mirror`, `end.replay`, `host.handback` and its `lapse`.
NETSYNC_BATTLE_CONTENT_HIT_KEYS = BW.CONTENT_NAMES
NETSYNC_BATTLE_MIRROR_KEYS = ("serving", "open", "fed", "accepted", "obsolete", "closed", "no_roster", "faulted",
                              "fault_why")
NETSYNC_BATTLE_REPLAY_KEYS = ("mode", "armed", "pending", "opened", "live", "closed", "aborted", "abort_why", "refused",
                              "verdict", "why", "row_mask", "seated_mask", "manifest_rows", "host_state_at_arm", "bench",
                              "arm_ms", "open_ms", "close_ms", "exit_waited", "exit_wait_ms", "screen", "fp")
NETSYNC_BATTLE_HANDBACK_KEYS = ("off", "held", "held_ms", "owed", "g6_mask", "captures", "returns", "deferred", "faults",
                                "last", "lapse", "refused_report", "refused_now", "diorama_seen")   # (s118: the last 3)
NETSYNC_BATTLE_LAPSE_KEYS = ("active", "hold", "left_ms", "count", "end_frame", "reserve")
#: [ff9mapkit netsync R3] s111-s117's FIXED sub-objects (always published whole, in the agent's order): `host.cfg`,
#: `host.intro`, `host.wait`, `menu.ctl`, `host.start_hold` (+ its `released` / `guest`), `end.flee`; and inside
#: `netsync.diorama`: `intro` (+ `swirl_clamp`) and `live`. Each tuple is the live agent's; an older patch's is a prefix.
NETSYNC_BATTLE_CFG_KEYS = ("atb", "skip_btl_camera", "speed", "swirl_frames")
NETSYNC_BATTLE_HOST_INTRO_KEYS = ("off", "published", "own_skip")
NETSYNC_BATTLE_WAIT_KEYS = ("parity_off", "menu", "open", "deep", "legacy_seen")
NETSYNC_BATTLE_CTL_KEYS = ("menu", "hex", "src", "nonce", "boot", "boot_name")
NETSYNC_BATTLE_START_HOLD_KEYS = ("off", "cap_ms", "state", "nonce", "why", "release", "held_ms", "late_ms", "count",
                                  "released", "guest")
NETSYNC_BATTLE_RELEASED_KEYS = ("live", "declined", "link", "oldguest", "cap", "ended")
NETSYNC_BATTLE_HOLD_GUEST_KEYS = ("r3", "lane_ms", "fmt", "nonce", "boot", "boot_name")
NETSYNC_BATTLE_FLEE_KEYS = ("r9b", "bypassed", "overload", "ability_flag", "gil_now", "penalty", "msg_gil")
NETSYNC_DIORAMA_INTRO_KEYS = ("wire", "applied", "own", "off", "calls", "normal_ms", "swirl_frames", "swirl_clamp")
NETSYNC_DIORAMA_SWIRL_KEYS = ("ini", "clamp", "src", "bench_local", "diorama", "own", "used", "clamped", "dwell_ms",
                              "swirls", "dioramas", "clamps")
NETSYNC_DIORAMA_LIVE_KEYS = ("latched", "ms", "nonce")
#: [ff9mapkit netsync R3 s119-s121] the round's FIXED blocks, in the agent's order (AppendDioramaHold, AppendSession,
#: AppendMenuRefusal).
NETSYNC_DIORAMA_HOLD_KEYS = ("state", "since_ms", "cap_ms", "settle_ms", "holds", "resumes", "gaveup", "last_ms",
                             "peer_alive", "host_field", "terminal", "why")
NETSYNC_SESSION_KEYS = ("grace_ms", "state", "left_ms", "out_ms", "outages", "resumes", "gaveup", "last_ms", "peer_alive",
                        "seen_live", "mirroring", "ramp_pending", "ramp_cause", "overlay", "overlay_detail", "ghost",
                        "ghost_held")
NETSYNC_MENU_REFUSAL_KEYS = ("now", "count", "lines", "silent", "last_state", "last_field", "age_ms", "muted")
#: [ff9mapkit netsync s131] `netsync.battle.peer.expired`, in AppendPeerExpired's order (battlewire.PeerLane.doc).
NETSYNC_PEER_EXPIRED_KEYS = tuple(BW.PEER_EXPIRED_SENTINELS)
#: [ff9mapkit netsync s133] `netsync.battle.act.host` and its fixed sub-objects, in AppendAct's order
#: (battlewire.ActHostLane.doc); `last` and `tape.page` are nullable records (ACT_LAST_FIELDS / ACT_PAGE_KEYS when set).
NETSYNC_ACT_HOST_KEYS = tuple(BW.ACT_HOST_SENTINELS)
NETSYNC_ACT_KINDS_KEYS = tuple(BW.ACT_HOST_SENTINELS["kinds"])
NETSYNC_ACT_VFX_KEYS = tuple(BW.ACT_HOST_SENTINELS["vfx"])
NETSYNC_ACT_LOOP_KEYS = tuple(BW.ACT_HOST_SENTINELS["loop"])
NETSYNC_ACT_TAPE_KEYS = tuple(BW.ACT_HOST_SENTINELS["tape"])
NETSYNC_ACT_LAST_KEYS = tuple(BW.ACT_LAST_FIELDS)
#: [ff9mapkit netsync s133] `actbench <op>` (NetSyncBattle.HarnessActBench), in its "unknown op" refusal's order, and the
#: `tape` op's values (`tape rec|stop|clear|info` + `tape dump <from> <count>`: the agent's own argument parse names dump)
NETSYNC_ACTBENCH_OPS = ("tape", "hoststarts")
NETSYNC_ACTBENCH_TAPE_OPS = ("rec", "stop", "clear", "info", "dump")
#: [ff9mapkit netsync s134] `netsync.battle.act.guest` and its fixed sub-objects, in AppendActGuest's order
#: (battlewire.ActGuestLane.doc); `last` is a nullable record (ACT_GUEST_LAST_KEYS when set).
NETSYNC_ACT_GUEST_KEYS = tuple(BW.ACT_GUEST_SENTINELS)
NETSYNC_ACT_GUEST_LEVERS_KEYS = tuple(BW.ACT_GUEST_SENTINELS["levers"])
NETSYNC_ACT_GUEST_GRACE_KEYS = tuple(BW.ACT_GUEST_SENTINELS["grace"])
NETSYNC_ACT_GUEST_WINDOW_KEYS = tuple(BW.ACT_GUEST_SENTINELS["window"])
NETSYNC_ACT_GUEST_ABORTS_KEYS = tuple(BW.ACT_GUEST_SENTINELS["aborts"])
NETSYNC_ACT_GUEST_DISCARDED_KEYS = tuple(BW.ACT_GUEST_SENTINELS["discarded"])
NETSYNC_ACT_GUEST_LAST_KEYS = BW.ACT_GUEST_LAST_KEYS
#: [ff9mapkit netsync s134] `actbench`'s GUEST ops (NetSyncDiorama.IsActGuestBenchOp, routed before HarnessActBench) -- the
#: s133 "unknown op" list (NETSYNC_ACTBENCH_OPS) is left as it was: an op neither half knows is refused in s133's words
NETSYNC_ACTBENCH_GUEST_OPS = BW.ACT_GUEST_BENCH_OPS
#: the agent's argument-parse refusal for a non-guest form, as s133 printed it and as s134 rewrote it (one
#: ArgumentOutOfRangeException("netsync actbench", <this>) each)
NETSYNC_ACTBENCH_USAGE_S133 = ("expected `actbench hoststarts on|off`, `actbench tape rec|stop|clear|info` or `actbench "
                               "tape dump <from> <count>`")
NETSYNC_ACTBENCH_USAGE_S134 = ("expected `actbench hoststarts on|off`, `actbench tape rec|stop|clear|info|play [pct]`, "
                               "`actbench tape dump <from> <count>`, `actbench feed <hex>`, `actbench feedat <ms> <hex>`, "
                               "`actbench replay|rework|shortcircuit on|off`, `actbench knob 0|1|ini`, `actbench clear` "
                               "or `actbench teardown`")
#: [ff9mapkit netsync s135] `netsync.battle.act.guest.hold` and its fixed `lag` (battlewire.ActHoldLane.doc); `figs` is a
#: list of {slot, value, via, arrival_ms, release_ms} (BW.ACT_HOLD_FIG_KEYS) -- one leaf
NETSYNC_ACT_GUEST_HOLD_KEYS = tuple(BW.ACT_GUEST_HOLD_SENTINELS)
NETSYNC_ACT_GUEST_HOLD_LAG_KEYS = BW.ACT_HOLD_LAG_KEYS
#: [ff9mapkit netsync s135] `actbench`'s replay-hit-hold ops (routed with the guest ops: IsActGuestBenchOp)
NETSYNC_ACTBENCH_HOLD_OPS = BW.ACT_HOLD_BENCH_OPS
#: ...and the agent's usage line as s135 rewrote it (an s135 engine says this for every non-guest form)
NETSYNC_ACTBENCH_USAGE_S135 = ("expected `actbench hoststarts on|off`, `actbench tape rec|stop|clear|info|play [pct]`, "
                               "`actbench tape dump <from> <count>`, `actbench feed <hex>`, `actbench feedat <ms> <hex>`, "
                               "`actbench replay|rework|shortcircuit on|off`, `actbench knob 0|1|ini`, `actbench clear`, "
                               "`actbench teardown`, `actbench hold|lifeskip on|off` or `actbench unit <slot> "
                               "dead|alive|trance0|trance1`")
#: [ff9mapkit netsync s136] `netsync.battle.act.guest.fallback` (battlewire.ActFallbackLane.doc); `last` is a nullable record
#: (BW.ACT_FALLBACK_LAST_KEYS when set) -- one leaf
NETSYNC_ACT_GUEST_FALLBACK_KEYS = tuple(BW.ACT_GUEST_FALLBACK_SENTINELS)
NETSYNC_ACT_FALLBACK_LAST_KEYS = BW.ACT_FALLBACK_LAST_KEYS
#: [ff9mapkit netsync s136] `actbench`'s fallback-A op (routed with the guest ops: IsActGuestBenchOp)
NETSYNC_ACTBENCH_FALLBACK_OPS = BW.ACT_FALLBACK_BENCH_OPS
#: ...and the agent's usage line as s136 rewrote it (an s136 engine says this for every non-guest form)
NETSYNC_ACTBENCH_USAGE_S136 = ("expected `actbench hoststarts on|off`, `actbench tape rec|stop|clear|info|play [pct]`, "
                               "`actbench tape dump <from> <count>`, `actbench feed <hex>`, `actbench feedat <ms> <hex>`, "
                               "`actbench replay|rework|shortcircuit on|off`, `actbench knob 0|1|ini`, `actbench clear`, "
                               "`actbench teardown`, `actbench hold|lifeskip on|off`, `actbench unit <slot> "
                               "dead|alive|trance0|trance1` or `actbench fallback on|off`")


def caps_through(cap: str) -> frozenset:
    """[ff9mapkit netsync s133] The stand-in capability set of the engine AT battle capability ``cap``: every F3.3 cap +
    the battle ladder up to and including ``cap`` (a ladder PREFIX -- audit 3.1 / 4.1). The calibration engine of a round
    is the prefix through the rung before its own (s133's: ``caps_through("grace40")``, s132)."""
    names = list(NETSYNC_BATTLE_CAPS)
    return frozenset(NETSYNC_F33_CAPS) | frozenset(names[:names.index(cap) + 1])


def actbench_ops(caps) -> tuple:
    """[ff9mapkit netsync s133] The `actbench` ops an engine with these capabilities has (s133: tape, hoststarts; none
    before it -- the sub-verb itself is unknown there). [ff9mapkit netsync s134] + the guest ops (`tape play` is a later
    VALUE of `tape`, not an op). [ff9mapkit netsync s135] + the replay hit hold's (`hold|lifeskip|unit`). [ff9mapkit netsync
    s136] + fallback A's (`fallback`)."""
    if "actstart" not in caps:
        return ()
    return NETSYNC_ACTBENCH_OPS + (NETSYNC_ACTBENCH_GUEST_OPS if "actreplay" in caps else ()) + (
        NETSYNC_ACTBENCH_HOLD_OPS if "acthold" in caps else ()) + (
        NETSYNC_ACTBENCH_FALLBACK_OPS if "actfallback" in caps else ())
#: [ff9mapkit netsync B4] `bmenu <op>` (NetSyncBattle.HarnessStockMenu), in its "unknown op" refusal's order.
NETSYNC_BMENU_OPS = ("open", "close", "closeall", "capture", "mainmenu")
#: [ff9mapkit netsync B4] `bbench <op>` (NetSyncBattle.HarnessStockBench): s106's two, then s107's bench feed -- each
#: engine's "unknown op" text (s106 names stage 8's ops in a note).
NETSYNC_BBENCH_OPS_S106 = ("roster", "content")
NETSYNC_BBENCH_OPS = ("roster", "content", "start", "stop", "ready", "caps", "mode", "freeze", "unmap", "knob")
NETSYNC_BBENCH_UNKNOWN_S106 = "roster|content; stage 8 adds start|ready|caps|mode|unmap|stop"
#: [ff9mapkit netsync B5] `endbench <op>` (NetSyncEnd.HarnessEndBench) as s103 printed it; s104 inserts `guest` and s105
#: `exit` after `host`, s108 `manifest` after `afterevent`, s109 `fieldsong` before it and `replay|quit` after `exit`
#: (:func:`endbench_ops`). Before s108 `manifest` is an op the engine knows and refuses (stage 9) but never lists.
NETSYNC_ENDBENCH_OPS_S103 = ("victory", "pending", "nopose", "other", "defeat", "escape", "event", "fight", "ui", "state",
                             "overflow", "afterevent", "cmd", "host", "selftest", "clear")


def netsync_subverbs(caps) -> tuple:
    """[ff9mapkit netsync B4] The sub-verbs an "authority" engine with these capabilities prints, in its order: the F3.2
    list, the F3.3 groups in patch order, then the battle verbs in :data:`NETSYNC_BATTLE_VERB_ORDER`."""
    battle = {v: cap for cap, (_p, verbs) in NETSYNC_BATTLE_CAPS.items() for v in verbs}
    return NETSYNC_SUBVERBS_F32 + tuple(v for cap, (_p, verbs) in NETSYNC_F33_CAPS.items() if cap in caps
                                        for v in verbs) \
        + tuple(v for v in NETSYNC_BATTLE_VERB_ORDER if battle[v] in caps)


NETSYNC_SUBVERBS = netsync_subverbs(frozenset(NETSYNC_F33_CAPS) | frozenset(NETSYNC_BATTLE_CAPS))


def endbench_ops(caps) -> tuple:
    """[ff9mapkit netsync B5] The `endbench` ops an engine with these capabilities lists (its "unknown op" order)."""
    ops = list(NETSYNC_ENDBENCH_OPS_S103)
    at = ops.index("host") + 1
    if "present" in caps:
        ops.insert(at, "guest")
        at += 1
    if "exit" in caps:
        ops.insert(at, "exit")
        at += 1
    if "replay" in caps:
        ops[at:at] = ["replay", "quit"]
    if "manifest" in caps:
        ops.insert(ops.index("afterevent") + 1, "manifest")
    if "replay" in caps:
        ops.insert(ops.index("afterevent") + 1, "fieldsong")
    if "fleegil" in caps:                               # [ff9mapkit netsync R3 s116] after `manifest`
        ops.insert(ops.index("manifest") + 1, "fleegil")
    if "defeat" in caps:                                # [ff9mapkit netsync R3 s117] after `defeat`, and after `fleegil`
        ops.insert(ops.index("defeat") + 1, "phase-defeat")
        ops.insert(ops.index("fleegil") + 1, "kill")
    return tuple(ops)


def bbench_ops(caps) -> tuple:
    """[ff9mapkit netsync B4] The `bbench` ops an engine with these capabilities has."""
    return NETSYNC_BBENCH_OPS if "mirror" in caps else NETSYNC_BBENCH_OPS_S106 if "content" in caps else ()


#: [ff9mapkit netsync B5] The stand-in's level table (ff9level.CharacterLevelUps' role): level L becomes L + 1 at
#: ``fake_threshold(L)`` EXP; LEVEL_COUNT levels.
FAKE_LEVEL_COUNT = 99


def fake_threshold(level: int) -> int:
    return 100 * level * level


#: [ff9mapkit netsync B5] The stand-in's field party at New Game (FF9.party.member's four seats): Zidane and Vivi -- the
#: default battle units' two players -- each with its preset's abilities ``(abil id, max AP)`` and its pa[]. Zidane has
#: mastered Flee (30) and not Detect (31): the two-marker manifest's learn marker is Detect.
FAKE_PARTY = ({"char": 0, "name": "Zidane", "level": 5, "exp": 1700, "status": 0, "pa": [25, 0],
               "abils": [(30, 25), (31, 40)]},
              {"char": 1, "name": "Vivi", "level": 4, "exp": 1000, "status": 0, "pa": [0], "abils": [(20, 30)]},
              None, None)


def _int32(text) -> int | None:
    """Int32.TryParse(text) (NumberStyles.Integer): surrounding white space and one leading sign; None = it fails."""
    a = str(text if text is not None else "").strip()
    if not a or not all(c.isdigit() for c in a.lstrip("+-")) or len(a) - len(a.lstrip("+-")) > 1 or a in ("+", "-"):
        return None
    v = int(a)
    return v if -2 ** 31 <= v < 2 ** 31 else None
#: [ff9mapkit netsync F3.3] Section 7's host flags (NetSyncDialog.Hf*): b0 the sticky scene, b1 control, b2 an
#: input-taking line open, b3 on a live field, b4 a non-HUD UI, b5 in battle.
HF_SCENE, HF_CONTROL, HF_LINE, HF_ON_FIELD, HF_MENU, HF_BATTLE = 0x01, 0x02, 0x04, 0x08, 0x10, 0x20
#: [ff9mapkit netsync F3.3] An open window's wflags (NetSyncDialog.Wf*), and the KEY / ADV-CHO kinds.
WF_CHOICE, WF_COMPLETE, WF_INH = 0x01, 0x02, 0x04
KIND_ADV, KIND_CHO, KIND_KEY = 0, 1, 2
#: [ff9mapkit netsync F3.3] The KEY event's compact bits (NetSyncField.CompactKeys: b0 Select b1 Triangle b2 Circle b3 Cross
#: b4 Square b5 Cancel b6 Confirm b7 MenuControl b8 Special b9 Menu) -- every one a HOST-OWNED key; a KEY with none of
#: them is ignored. A press as the agent's Control reaches a script poll: its logical bit OR its physical button's
#: (:data:`CONTROL_BITS` -- Confirm = logical Confirm b6 + Cross b3), so `netsync host key <uid> 64` is "Confirm".
COMPACT_HOST_OWNED = 0x3FF
COMPACT_BY_CONTROL = {"confirm": 0x40 | 0x08, "cancel": 0x20 | 0x04, "menu": 0x200 | 0x02, "special": 0x100 | 0x10,
                      "select": 0x01}
#: What an F3.2 engine publishes in place of the F3 lockstep keys: the contract tag, and every F3 key PINNED to its
#: "nothing" value (HarnessAgent.AppendNetsync, s96 -- protocol stays 5, the block is additive).
NETSYNC_F3_PINNED = {"dialogue": "authority", "l1_pinned": False, "l1_forced_control": False, "align_win": -1,
                     "align_text": -1, "applied_seq": -1, "wait_armed": False, "wait_ms": -1, "wait_limit_ms": -1,
                     "pending": None}
#: The guest's dialogue keys the F3.2 lock swallows (UIKeyTrigger's dialogue path; the arrows: the cursor lock), by
#: every name `_menu_step` answers to.
GUEST_DIALOG_KEYS = ("confirm", "ok", "cancel", "back", "b", "up", "down")
#: The UI states the ENGINE's soft-reset combo fires in: it is held through ``UIKeyTrigger.GetKey``, which answers
#: false outside these four (UIKeyTrigger.cs:94; research/o3_design.md 0.2 #9). `FakeGame.soft_reset_ui` defaults to
#: the narrower pair every test before H9 was written against; a test that models the engine passes this.
SOFT_RESET_ENGINE_UI = ("FieldHUD", "WorldHUD", "BattleHUD", "QuadMistBattle")
#: H9's movie skip dialog, as the ENGINE answers it -- the dialog's text aside (a test may stage any text in its slot):
#: FieldHUD.OnKeyConfirm puts the cursor on No (``ETb.sChoose = 1``, FieldHUD.cs:280) before it attaches the dialog,
#: whatever the dialog says, and OnKeyConfirmAfterDialogHidden skips on choice 0 ALONE (:430-433); any other answer
#: re-arms the hit area and the movie resumes (:434-440). Absolute indexes, never the fixture's: a skip ``default``
#: other than the cursor is refused when the scene is built (:meth:`FakeGame.scene`), so a fixture cannot flip the
#: sign of the skip.
SKIP_CURSOR = 1
SKIP_CHOICE = 0

# ======================================================================== H20-H21: O7's levels and squeeze
#: H20 (research/o7_design.md 3.1): how far from his height an open triangle under him may lie and still be HIS. The
#: engine keeps the actor on its active triangle and crosses only a shared edge to a neighbour; nearest-within-this is
#: that graph wherever stacked levels lie further apart than it and a step changes his height by less. A 60-u tick step
#: on stock 154's steepest open triangle (tri 205, the west flight, 52.8 deg) changes his height by 79.1, on 163's
#: (tri 134) by 63.0; 154's stacked open triangles lie at least 1298 apart (a stair over the ground; the balcony 1711
#: over it) -- test_fake_level_meshes_hold_the_levels_premises measures each.
LEVEL_STEP_DY = 200.0
#: H20: the engine's own "same level" pairing band (WalkMesh.cs:922), the stand-in for "his own surface": a wall is his
#: when its height at the point nearest him lies within this of his. Sound while stacked levels lie more than twice it
#: apart.
LEVEL_BAND = 400.0
#: H21 (research/o7_design.md 3.2): how far under the controller's radius a side a PINCH may be and still let him
#: through -- an ESTIMATE over 163's measured 3.3-u overlap (0.2 #12) that R-STAIR measures (F5); a NO-GO there is the
#: fallback end, never a wider slack.
SQUEEZE_SLACK_W = 8.0
#: H21: the spacing of the search across a pinch for its widest point.
SQUEEZE_SAMPLE_W = 2.0

# ======================================================================== H25: O8's knight walker
#: H25 (research/o8_design.md 3.2): a walker's ``start`` terms on the player's PUBLISHED y -- the release its height
#: gate reads (164 e1 t1 ip178's test read through ip187's JMP_IF loop: ``{"y_ge": 8400}``).
_WALKER_TESTS = {"y_ge": lambda y, h: y >= h, "y_gt": lambda y, h: y > h,
                 "y_le": lambda y, h: y <= h, "y_lt": lambda y, h: y < h}


def _walker_knobs(b: dict) -> None:
    """H25's keys read STRICT on a walker's first step (the H23 ``hold`` reader's place): ``start`` None or exactly
    one of :data:`_WALKER_TESTS`' terms to a number (a bool is no number); ``store`` None or a dict of exactly
    ``after_ticks`` -- a number >= 0 -- and ``args`` -- the seven ``[sid, tag, ip, byte, width, new, bit]`` of a
    :meth:`FakeGame.script_store`; ``path`` (H25b, the review's #2) ``[[x, z], ...]`` or ``[[x, z, y], ...]`` -- y the
    walker's level at the point, on every point or none -- numbers all. A ValueError names the fault."""
    def num(v) -> bool:
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    path = b.get("path")
    if path is not None and not (isinstance(path, (list, tuple)) and all(
            isinstance(p, (list, tuple)) and len(p) in (2, 3) and all(num(v) for v in p) for p in path)
            and len({len(p) for p in path}) <= 1):
        raise ValueError(f"a walker's path is [[x, z], ...] or [[x, z, y], ...] (y its level at the point, on every point "
                         f"or none), not {path!r}")
    start, store = b.get("start"), b.get("store")
    if start is not None and not (isinstance(start, dict) and len(start) == 1 and set(start) <= set(_WALKER_TESTS)
                                  and num(next(iter(start.values())))):
        raise ValueError(f"a walker's start is exactly one of {sorted(_WALKER_TESTS)} to a number (his published y), "
                         f"not {start!r}")
    if store is not None and not (isinstance(store, dict) and set(store) == {"after_ticks", "args"}
                                  and num(store["after_ticks"]) and store["after_ticks"] >= 0
                                  and isinstance(store["args"], (list, tuple)) and len(store["args"]) == 7):
        raise ValueError(f"a walker's store is {{'after_ticks': n >= 0, 'args': [sid, tag, ip, byte, width, new, bit]}}, "
                         f"not {store!r}")


class Levels:
    """H20 (research/o7_design.md 3.1): a STACKED walkmesh as the engine walks one actor on it -- stock 154's balcony
    1711 over its ground, its floor indices mixing both heights (0.2 #7), which the kit's floor-blind
    ``point_on_walkmesh`` and ``distance_to_boundary`` cannot tell apart. Over a kit walkmesh: a ``PlayerWalkmesh``
    (its open triangles) or a ``BgiWalkmesh`` (every triangle), its world verts in PSX y (up negative).

      * :meth:`tri_under` -- among the open triangles containing (x, z), the one whose height there is NEAREST his and
        within ``step_dy`` of it, else None: the actor stays on its active triangle and crosses only a shared edge
        (the walkmesh traversal), which this is wherever stacked levels lie more than ``step_dy`` apart and a step
        changes his height by less; :meth:`tri_nearest` -- the same without the bound (a placement, GetTriIdxAtPos,
        FieldMapActorController.cs:1279-1306);
      * :meth:`height` -- the interpolated PSX height on a triangle;
      * :meth:`wall_gap` -- the XZ distance to the nearest WALL of his level: an edge of an open triangle with no open
        neighbour (PlayerWalkmesh's rule, per triangle -- not per floor index), kept when its height at its point
        nearest him lies within ``band`` of his; None off his level;
      * :meth:`squeeze` -- H21 (3.2), with ``squeeze_slack`` set: a PINCH's midline.

    The fake walks him on it through ``fake.levels`` (:meth:`FakeGame._move_to`)."""

    def __init__(self, wmesh, *, step_dy: float = LEVEL_STEP_DY, band: float = LEVEL_BAND,
                 squeeze_slack: float | None = None):
        from ff9mapkit.scene import bgi
        mesh = getattr(wmesh, "mesh", wmesh)                 # a PlayerWalkmesh's raw mesh, or a BgiWalkmesh
        closed = frozenset(getattr(wmesh, "closed", ()) or ())
        for name, v in (("step_dy", step_dy), ("band", band)):
            if not isinstance(v, (int, float)) or isinstance(v, bool) or not v > 0:
                raise ValueError(f"Levels: {name} is a positive number of world units, not {v!r}")
        if squeeze_slack is not None and (not isinstance(squeeze_slack, (int, float))
                                          or isinstance(squeeze_slack, bool) or squeeze_slack < 0):
            raise ValueError(f"Levels: squeeze_slack is None or a number of world units >= 0, not {squeeze_slack!r}")
        self.mesh = mesh
        self.step_dy, self.band = float(step_dy), float(band)
        self.squeeze_slack = None if squeeze_slack is None else float(squeeze_slack)
        self._wv = mesh.world_verts()
        tris = mesh.tris
        self.open = frozenset(i for i in range(len(tris)) if i not in closed)
        walls = []
        for ti in sorted(self.open):
            t = tris[ti]
            for k, (i, j) in enumerate(bgi.SLOT_PAIRS):
                n = t.nbr[k]
                if 0 <= n < len(tris) and n in self.open:
                    continue                                 # an open neighbour across this edge: not a wall
                a, b = self._wv[t.vtx[i]], self._wv[t.vtx[j]]
                dx, dy, dz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
                walls.append((a[0], a[1], a[2], dx, dy, dz, dx * dx + dz * dz))
        self._walls = walls

    def height(self, ti: int, x: float, z: float) -> float:
        """The PSX height (up negative) of triangle ``ti``'s plane at (x, z), barycentric over its world verts."""
        a, b, c = (self._wv[k] for k in self.mesh.tris[ti].vtx)
        den = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
        if den == 0:
            return float(a[1])
        wa = ((b[2] - c[2]) * (x - c[0]) + (c[0] - b[0]) * (z - c[2])) / den
        wb = ((c[2] - a[2]) * (x - c[0]) + (a[0] - c[0]) * (z - c[2])) / den
        return wa * a[1] + wb * b[1] + (1.0 - wa - wb) * c[1]

    def tri_nearest(self, x: float, z: float, h: float) -> int | None:
        """The open triangle containing (x, z) whose height there is nearest ``h`` (ties: the lower id), else None."""
        best = None
        for ti in self.mesh.tris_at(x, z):
            if ti not in self.open:
                continue
            d = abs(self.height(ti, x, z) - h)
            if best is None or d < best[0]:
                best = (d, ti)
        return None if best is None else best[1]

    def tri_under(self, x: float, z: float, h: float) -> int | None:
        """His triangle at (x, z): :meth:`tri_nearest` when within ``step_dy`` of ``h``, else None (no triangle of his
        level there -- the edge of a balcony, over the ground below it)."""
        ti = self.tri_nearest(x, z, h)
        return ti if ti is not None and abs(self.height(ti, x, z) - h) <= self.step_dy else None

    def wall_gap(self, x: float, z: float, h: float) -> float | None:
        """The XZ distance from (x, z) to the nearest wall of HIS level (a wall whose height at its point nearest him
        lies within ``band`` of ``h``); None when no triangle of his level is under him (:meth:`tri_under`); infinity
        when no wall of his level stands anywhere."""
        if self.tri_under(x, z, h) is None:
            return None
        best = math.inf
        for ax, ay, az, dx, dy, dz, l2 in self._walls:
            t = 0.0 if l2 == 0 else ((x - ax) * dx + (z - az) * dz) / l2
            t = 0.0 if t < 0.0 else 1.0 if t > 1.0 else t
            if abs(ay + t * dy - h) > self.band:
                continue                                     # another level's wall
            d = math.hypot(x - (ax + t * dx), z - (az + t * dz))
            if d < best:
                best = d
        return best

    def squeeze(self, x: float, z: float, ux: float, uz: float, h: float, clearance: float):
        """H21 (research/o7_design.md 3.2): where a step ending at (x, z) along (ux, uz) is placed in a PINCH -- the
        point of the LARGEST wall gap on the segment across the step through its end, ``clearance`` either side, each
        side only as far as his level's floor runs (the corridor's midline, where the engine's opposing pushes average
        out: RadiusValid pushes each wall's force out to the controller's radius, ServiceForces averages several x
        1.05, FieldMapActorController.cs:1060-1254) -- ``(px, pz)``, kept when that gap is at least ``clearance -
        squeeze_slack``. None -- the caller's rule as ever -- without ``squeeze_slack``, off his level, for no step, where
        a point across stands at the full ``clearance`` (no pinch: a press into a wall), or where the pinch is narrower
        than that bound (he stops: the radius cannot fit)."""
        if self.squeeze_slack is None or self.tri_under(x, z, h) is None:
            return None
        n = math.hypot(ux, uz)
        if n < 1e-9:
            return None
        px, pz = -uz / n, ux / n                             # across the step
        best = None
        for side in (1.0, -1.0):
            t = 0.0
            while t <= clearance + 1e-9:
                qx, qz = x + side * t * px, z + side * t * pz
                g = self.wall_gap(qx, qz, h)
                if g is None:
                    break                                    # off his level: no further this side
                if g >= clearance:
                    return None                              # room at the full radius across: no pinch here
                if best is None or g > best[0]:
                    best = (g, qx, qz)
                t += SQUEEZE_SAMPLE_W
        if best is None or best[0] < clearance - self.squeeze_slack:
            return None
        return best[1], best[2]


class FakeGame:
    """Runs the agent's side of the protocol in a background thread at a simulated frame rate.

    Two rates, never one: the LOOP turns frames at `fps` a wall second (a test's speed), and each frame is one frame of
    a game rendering at `render_fps` on a virtual clock -- whose seconds become the engine's field ticks (`tick_mode`,
    `fast_forward`), and whose clocks the driver can time it by (`publish`). See "the clock" below."""

    def __init__(self, game_path: Path, *, fps: float = 240.0, boot_state: str = "Title",
                 mode: str = "normal", walkmesh=(-600.0, -600.0, 600.0, 600.0),
                 resets_on_arm: bool = True, twist: float = 0.0, render_fps: float = 60.0,
                 ticks: str = "mean", hitches: dict | None = None, publish=("rt",)):
        self.game_path = Path(game_path)
        self.dir = self.game_path / "x64" / "ff9harness"
        self.shots = self.dir / "shots"
        #: How fast the frame LOOP runs, in WALL-clock frames a second -- NOT a render rate: every frame is one
        #: `render_fps` frame of the virtual clock, however fast the loop turns it (240 by default, so a suite spends
        #: a quarter of the wall time a 60 fps game would). `FakeGame(fps=30)` tests nothing about 30 fps; set
        #: `render_fps`. (With "mtime" published the loop runs in real time at `render_fps` and ignores this.)
        self.fps = fps
        # -- the clock (see harness.tickrate): a VIRTUAL clock, frames -> seconds -> field ticks ----------------------
        if ticks not in TICK_MODES:
            raise ValueError(f"ticks must be one of {TICK_MODES}, not {ticks!r}")
        publish = tuple(publish)
        if any(p not in PUBLISHED_CLOCKS for p in publish):
            raise ValueError(f"publish takes only {PUBLISHED_CLOCKS}, not {publish!r}")
        #: FastForwardFactor (the F1 speed-mode cheat: Memoria.ini [Cheats] SpeedFactor): field ticks a second are
        #: FIELD_TPS x this (FPSManager.cs:95-97), and the engine publishes it nowhere -- a driver sees it only as
        #: movement that outruns its rate. 1 = off.
        self.fast_forward = 1.0
        self._tick_mode = ticks
        self._render_fps = self._positive_fps(render_fps)
        #: The clocks published (`PUBLISHED_CLOCKS`). The default, ``("rt",)``, lets the driver's TickClock time the
        #: fake by its VIRTUAL clock whatever the loop's pace; ``()`` publishes none, so the driver falls back on
        #: state.json's real mtime -- which follows the LOOP (`fps`), not `render_fps`, and only approximately
        #: (sleep overshoot); ``("mtime",)`` makes that path exact: the loop paces itself in real time on the virtual
        #: clock and stamps each state.json with its virtual write time, so the file's mtime IS the render clock.
        self.publish = publish
        #: Extra VIRTUAL seconds a frame takes, by frame number (``{frame: seconds}``): a hitch -- the frame runs the
        #: ticks those seconds hold on top of its own (the engine catches a long frame up in the next frame's
        #: ticks, FPSManager.cs:94-99, at most ~10: `MAX_DELTA_TIME`). :meth:`hitch` adds one to the next frame.
        self._hitches: dict[int, float] = {int(k): float(v) for k, v in (hitches or {}).items()}
        self.rt = 0.0                              # the virtual clock, seconds since the first frame
        self._rt_anchor, self._rt_frames = 0.0, 0  # rt = anchor + frames / render_fps (exact: no drift to add)
        self.ticks_run = 0.0                       # field ticks run since the first frame (int-valued when quantized)
        self._acc = TickAccumulator(FIELD_TPS)     # the engine's accumulator, for "quantized"
        self._dt = 0.0                             # this frame's virtual seconds (0 on a frame the counter froze)
        self._frame_ticks = 0.0                    # this frame's field ticks
        self._steps: list = []                     # ...as the world runs them: [avg] (mean), [1.0] * n (quantized)
        self._clock_frame = 0                      # the frame those are for (a test may step `frame` by hand)
        self._tick = 0.0                           # the step of `_steps` the world is running now
        self._plan: tuple | None = None            # the player's plan for this frame (`_player_plan`), once read
        self._wall0 = 0.0                          # time.time() the virtual clock's 0 is stamped at ("mtime")
        #: Unity rewrites output_log.txt on every launch. False models a game that died before it
        #: did, so the file on disk is the PREVIOUS launch's -- which the driver must not archive as
        #: this run's evidence, because nothing in an untimestamped log says it is stale.
        self.writes_unity_log = True
        #: The protocol this stand-in claims to speak, or None to follow the module constant. A
        #: dial so a test can put an OLDER engine on the wire -- otherwise the driver's "rebuild
        #: the DLL" refusal is a guard that can never fire, which is the same shape as no guard.
        #: ⚠ None rather than a snapshot: the module constant is also monkeypatched by a test, and
        #: a value captured here at construction would silently ignore that.
        self.protocol: int | None = None
        self.mode = mode
        self.resets_on_arm = resets_on_arm
        #: Screen-to-world yaw, in degrees. FF9 fields are viewed by a fixed camera that is
        #: frequently yawed and movement is expressed in SCREEN space, so "up" is +z on one field
        #: and something diagonal on the next. A stand-in that always mapped up to +z would let a
        #: broken calibration pass, which is the one thing calibrate_axes exists to prevent.
        self.twist = float(twist)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.returncode: int | None = None

        # the simulated world
        self.frame = 0
        self.publish_frame = 0
        self.seq = -1
        self.ack = -1
        self.error_seq = -1
        self.pending_ack = False
        self.queue: list[list[str]] = []
        self.block_until = 0
        self.arm_seen = False
        self.armed = False
        self.arm_poll_frame = 0
        self.req_poll_frame = 0
        self.state_every = 2
        self.held: dict[str, int] = {}          # button -> absolute frame it is released on
        self.down_at: dict[str, int] = {}
        self.ui_state = boot_state
        self.field_id = -1
        self.player = [0.0, 0.0, 0.0]
        self.control = False
        self.has_position = True
        self.world = {"id": -1, "x": None, "z": None, "vehicle": 0}
        #: The overworld on foot (None: the world position never moves, as before). Set a dict to walk him:
        #: ``speed`` u/frame while "up" is held, along the CAMERA yaw ``cam`` (deg, atan2(dz, dx) -- the
        #: engine's RotTrue = camera rotation + stick direction, ff9.cs:6162); ``turn`` deg/frame that L1
        #: adds to the camera (R1 the opposite; 0 = the bumpers do not reach it); ``lag`` frames the actor
        #: takes to come onto the camera's line from a standstill facing elsewhere; ``blocked(x, z)`` and
        #: ``height(x, z)`` the ground. x wraps at 1536, as the real map does. Published player.* is the
        #: world position x 256 (s83's GetControlChar pos[]), y included -- and a teleport keeps y until
        #: he next moves (the engine's InitSlice re-grounds it, not the teleport).
        self.overworld: dict | None = None
        self._ow_yaw: float | None = None          # the actor's own yaw, easing onto the camera's
        self.texts: list[str] = []
        self.raw_texts: list[str] = []
        self.choice: dict | None = None
        #: A scripted scene with control withheld (:meth:`scene`): the beats still to play, where its choice
        #: window is ("opening" / "ready" / "closing") and the frame that ends that phase, every choice the
        #: scene was answered with (the absolute index taken), and when each window became READY as
        #: ``len(self.executed)`` then -- so a test can name the steps a waiter issued before it could answer.
        self._beats: list = []
        self._beat_phase: str | None = None
        self._beat_until = 0
        self._beat_frames = (6, 6)                 # (opening, closing) frames of a choice window
        self._typing_until = 0                     # a ready choice's prompt types on until this frame
        self.answered: list[int] = []
        self.readied: list[int] = []
        #: H9: a scene's MOVIE beat (:meth:`scene`) while it plays -- its skip dialog up included (MBG stays marked
        #: played until the movie ends) -- else None; and every movie as it went: ``{"frames", "start", "end",
        #: "played" (the frames it actually ran), "skips" (skip dialogs opened), "ended" ("played" | "skipped" |
        #: "warp")}``.
        self._movie: dict | None = None
        self.movies: list[dict] = []
        self._scene_control = True                 # what the scene's end does to control (:meth:`scene`'s ``control``)
        self.menu = {"selected": None, "hovered": None, "label": None, "group": None}
        self.menu_entries: list[str] = []
        self.menu_index = 0
        self.flags: dict[int, bool] = {}
        self.watch: list[int] = []
        self.error: str | None = None
        self.note = ""
        self.no_encounter = False          # s94: the F4 booster
        self.shots_taken = 0
        #: The co-op client's observables, at the engine's "nothing" sentinels. The stand-in models
        #: the GATES and the state block -- what each `netsync` verb refuses, what it publishes
        #: afterwards, and that `reset`/disarm release the override -- and, under the F3.2 contract,
        #: THE LOCK on its one dialogue window (:class:`_GuestDialog`). Not the wire's bytes. [ff9mapkit
        #: netsync F3.3] With :attr:`netsync_caps`: the section-7 ring and its bench host (:class:`_BenchHost`),
        #: the script-key relay on one polled line (:attr:`dialog_poll`), the tap-record tape, and the
        #: diorama warm return (:attr:`reinit_fields` / :attr:`encounter_fields`).
        #: `netsync_dialogue` is the dialogue contract this stand-in's engine speaks: "authority" (s96,
        #: F3.2 host-authoritative dialogue -- the agent's current source) or None, an F3 lockstep engine
        #: (s84/s85): no `dialogue` tag, the one-slot holder and its timeout, no F3.2 sub-verb.
        self.netsync_dialogue: str | None = "authority"
        #: [ff9mapkit netsync F3.3] the F3.3 capabilities this stand-in's engine has (:data:`NETSYNC_F33_CAPS`): all three
        #: = s99; empty = an F3.2 engine (s96: the type-7 FIFO, u8 host seqs, no `host`/`dioboot`/`tap-record`). Read
        #: only under "authority". "keys" without "ring" models no engine. [ff9mapkit netsync B4] plus the battle co-op
        #: capabilities (:data:`NETSYNC_BATTLE_CAPS`, s100-s110): the default -- every one of both -- is the live stack;
        #: `frozenset(NETSYNC_F33_CAPS)` is an s99 engine (no `netsync.battle`).
        self.netsync_caps: frozenset = frozenset(NETSYNC_F33_CAPS) | frozenset(NETSYNC_BATTLE_CAPS)
        #: [ff9mapkit netsync B4] [ff9mapkit netsync B5] the battle co-op lane's harness state (:class:`_BattleLane`)
        self._nb = _BattleLane()
        #: [ff9mapkit netsync B4] the battle scene's `btl_scene.Info.NoGameOver` (the guest's return settle reads it)
        self.scene_no_gameover = False
        #: [ff9mapkit netsync R3 s111] the stand-in's per-save config and ini (`netsync.battle.host.cfg`, LIVE reads):
        #: cfg.atb (1 = Wait, the stock default), cfg.skip_btl_camera (1 = play the intro), [Battle] Speed, [Graphics]
        #: BattleSwirlFrames, and [Netsync] DioramaSwirlFrames / StartHoldMs (s112 / s114). `bench cfg` overrides the
        #: first two for the process; `battle ... rand` makes an own battle a random encounter (the intro test's input).
        self.cfg_atb = 1
        self.cfg_skipcam = 1
        self.cfg_speed = 5
        self.cfg_swirl_frames = 0
        self.ini_swirl_clamp = 0
        self.ini_start_hold_ms = BW.START_HOLD_MS
        #: [ff9mapkit netsync R3 s120] [Netsync] SessionGraceMs as Memoria.ini holds it (an int or the raw text: the engine's
        #: ParseSessionGrace clamps it) -- `netsync.session.grace_ms` and, from s120, `netsync.diorama.hold.cap_ms`.
        #: [ff9mapkit netsync s132] None = the key ABSENT: the engine's own default (40000 with cap `grace40`, else 30000)
        self.ini_session_grace_ms = None
        #: [ff9mapkit netsync R3 s120/s121] NetSyncClient.IsMirroringStory -- a FOLLOWING guest's armed story mirror. The
        #: stand-in has no transport (the selftest role never mirrors), so a test sets this to stand in for 'state-mirror
        #: ARMED' (`netsync.session.mirroring`; s121's Menu-key refusal reads it, s38's silent drop before it)
        self.story_mirroring = False
        #: [ff9mapkit netsync R3 s121] UIManager.IsMenuControlEnable (a scene's MENUOFF clears it) and FF9Sfx.muteSfx
        self.menu_control_enable = True
        self.mute_sfx = False
        #: [ff9mapkit netsync R3 s121] NetSyncField's refusal statics (:class:`_MenuRefusal`: per PROCESS)
        self._menu_refusal = _MenuRefusal()
        #: [ff9mapkit netsync s131] NetSyncBattle's guest-lane statics (battlewire.PeerLane: per PROCESS) -- published as
        #: `netsync.battle.peer.expired`. The stand-in has no transport and its selftest loopback writes the view directly
        #: (as the engine's does), so nothing ever runs out and the block sits at its sentinels; a test may pump it by hand.
        self._peer_lane = BW.PeerLane()
        #: [ff9mapkit netsync s133] NetSyncBattle's host action-start lane (battlewire.ActHostLane: its statics, per PROCESS
        #: for the lever, the tape and `edge_declined`; per own battle for the rest) -- `netsync.battle.act.host`. Fed by
        #: the stand-in's own selftest battles (:meth:`_act_command`); its Log.Message lines go to Memoria.log.
        self._act_lane = BW.ActHostLane()
        self._act_logged = 0
        #: [ff9mapkit netsync s134] NetSyncDiorama.Replay.cs's statics (battlewire.ActGuestLane: the levers and the inbox
        #: harness-scoped, the rest per diorama boot) -- `netsync.battle.act.guest`; driven by a booted selftest diorama's
        #: tick (:meth:`_act_guest_tick`), its Log.Message lines into Memoria.log. ``act_guest.action_replay`` is the
        #: install's [Netsync] ActionReplay, ``act_guest.sfx_rework`` its [Battle] SFXRework.
        self._act_guest = BW.ActGuestLane()
        self._act_guest_logged = 0
        #: [ff9mapkit netsync s135] the replay hit hold runs on an engine with the `acthold` rung (the lane's `hold`)
        self._act_guest.with_hold_fn = lambda: "acthold" in self._nb_caps()
        #: [ff9mapkit netsync s136] fallback A runs on an engine with the `actfallback` rung (the lane's `fallback`); its
        #: shapes -- the scene's sequences, the units' motion tables, the categories -- are the lane's (a test sets them)
        self._act_guest.with_fallback_fn = lambda: "actfallback" in self._nb_caps()
        #: [ff9mapkit netsync s134] HonoluluBattleMain.IsPaused on a diorama (NOPUTDISPENV): the replay's battle clock skips
        #: a span between two paused reads and nothing launches -- the stand-in has no pause key, a test sets this
        self.battle_paused = False
        #: [ff9mapkit netsync s133] the stand-in's enemy attack's sub_no (an EnemyAtk START names it: kind 2, num == sub)
        self.act_enemy_sub = 3
        #: [ff9mapkit netsync R3] the selftest proof block is logged once per process; s120's overlay is composed by the
        #: selftest role's first tick ("off", detail 0) and keeps that state after it
        self._proof_logged = False
        self._ovl_composed = False
        self.battle_random = False
        #: [ff9mapkit netsync R3 s111] a skipped intro's length in frames (the plunge camera skipped: SkipCameraAnimation)
        self.battle_intro_skip_frames = 6
        #: [ff9mapkit netsync R3 s115] the presented run-away's frames: the runners turn and run, then the escape fade
        self.dio_run_frames = 20
        #: [ff9mapkit netsync B5] the diorama's victory camera never advances by itself (the native callback, SFX code
        #: 110, may never fire in BattleMapDebug [I]) -- W1's case; False: the stock tail's camera runs out on its own
        self.dio_camera_stuck = False
        #: [ff9mapkit netsync B5] the presented victory's stock tail, in frames: MENU_OFF's trailing loop, then the victory
        #: camera (SEQ_VICTORY_CAMERA_MOVE); each fade (FADEOUT -> WAIT) is the stock 32
        self.dio_tail_frames = 12
        self.dio_camera_frames = 60
        #: [ff9mapkit netsync B5] the result screen's ResultState while ``ui_state`` is "BattleResult" (an own battle's
        #: `host.end.res_state` / `battle.result_ui.state`; 0 Start .. 6 End, 7 Hide, 8 None)
        self.result_state = 0
        #: [ff9mapkit netsync B5] FF9StateSystem.Achievement.enemy_no -- the invariant R8 protects (`end.ach_enemy_no`)
        self.ach_enemy_no = 0
        #: [ff9mapkit netsync B4] Memoria.ini [Netsync] GuestStockMenu (default 1): the ready mirror's knob (s107);
        #: `bbench knob 0|1` overrides it for the process, `knob ini` returns to this
        self.guest_stock_menu = True
        #: [ff9mapkit netsync B5] the game's own QUIT prompt is up (`endbench quit on`, s109): Cancel closes it, Confirm --
        #: its Yes -- QUITS the stand-in (returncode 0), as the engine's quits the game
        self.quit_prompt = False
        #: [ff9mapkit netsync B4] the units a `dioboot` diorama seats (None: :meth:`start_battle`'s defaults -- Zidane, a
        #: KO'd Vivi, the Masked Man). Copied per boot.
        self.dio_units: list[dict] | None = None
        #: [ff9mapkit netsync B5] the SAVE the result manifest (s108) and the replay's write guard (s109) read: the field
        #: party's four seats (None = an empty seat; each ``{"char": PLAYER.info.slot_no, "name", "level", "exp",
        #: "status", "pa": the AP per preset ability, "abils": [(abil id, max AP)]}``), the gil, the bag ``{item id:
        #: count}`` and the card collection ``{card id: count}``. Nothing the stand-in's battles do writes them.
        self.save_party: list = [dict(m, pa=list(m["pa"]), abils=list(m["abils"])) if m else None for m in FAKE_PARTY]
        self.save_gil = 500
        self.save_bag: dict = {236: 7, 237: 2}
        self.save_cards: dict = {}
        self.save_passive: set = set()        # the ability-achievement sets (FF9.party: learned, passive)
        self._rng = random.Random()                 # the bench host's epoch draws (Guid bytes on the engine)
        #: [ff9mapkit netsync F3.3] C3 R9: the selftest bench HOST and its ring (:class:`_BenchHost`)
        self._bench = _BenchHost(self._rng)
        #: [ff9mapkit netsync F3.3] R5: the open window's SCRIPT POLL, when its script polls the buttons instead of taking a
        #: Dialog confirm -- a FlagButtonInh ([NFOC]) page or polled choice: ``{"uid": the reading object's uid, "mask":
        #: the compact bits it polls (64 = Confirm)}``, or None. Each frame the open, input-inhibited window's poll reads
        #: the PRESS edges (B_KEYON) through NetSyncField.FilterScriptButtons; a hit is its script closing the page (a
        #: choice: committing the cursor) -- "closed by its own script/timer". `script_poll_hits` is the stand-in's own
        #: receipt (NOT published): ``{"uid", "bits", "by": "host" | "local", "choice"}`` per hit.
        self.dialog_poll: dict | None = None
        self.script_poll_hits: list[dict] = []
        self._key_tick = 0                          # NetSyncField.KeyTick: one per ServiceEvents -- field, battle, world (inert)
        self._key_reader = -1                       # NetSyncField.LastMaskedReader (process lifetime)
        self._key_tap_tick = None                   # TapScriptKeyIfHost's one-KEY-per-(key tick, reader) dedup
        self._key_tap_uids: set[int] = set()
        self._key_taps = 0
        #: R9: the tap-record tape (TapeCap 256) and a running replay: ``{"kind", "fld", "a", "b", "c", "x", "t"}`` rows
        self._tape: list[dict] = []
        self._tap_record = False
        self._replay: list[dict] = []
        self._replay_next = 0
        self._replay_paced = True
        self._replay_start = 0
        #: [ff9mapkit netsync F3.3] DIO-1 (s97): the battle scene ids this install registers (FF9StateSystem.Battle.mapName;
        #: `dioboot` refuses any other), the fields with an entry-0 tag-10 Main_Reinit, the fields that arm random
        #: encounters (encratio > 0) -- a WARM return needs both -- and each field's Main_Init placement (where a COLD
        #: return re-enters him; (0, 0) when not named). The frames a boot's swirl, a leave's fade and a return's
        #: Main_Reinit / Main_Init take (control back after the last).
        self.battle_scenes: frozenset = frozenset(range(0, 1000))
        self.reinit_fields: set[int] = set()
        self.encounter_fields: set[int] = set()
        self.field_spawn: dict[int, tuple[float, float]] = {}
        self.dio_swirl_frames = 8
        self.dio_leave_frames = 10
        self.dio_resume_frames = 6
        #: A boot the engine refuses after the agent's gates (a fade in flight, a failed snapshot): its reason, or None
        self.dio_boot_refusal: str | None = None
        self._dio = {"booted": False, "boot": None, "boot_why": None, "boot_field": -1, "boot_x": None,
                     "boot_z": None, "primed": False, "returns": 0, "last_return": None, "last_return_field": -1}
        self._dio_by_harness = False                # HarnessAgent._dioramaByHarness
        self._dio_release_pending = False           # ...and _dioramaReleasePending (the role held until the teardown)
        self._dio_retry_rt = 0.0                    # ...and _dioramaRetryTick (a Leave re-requested once a second)
        self._dio_boot_frame = 0
        self._dio_leave_at: int | None = None       # the frame a requested Leave's teardown lands
        self._dio_leave_rt = -3600.0                # LeaveRequestedRecently: within 5 s of the last Leave (a real tick)
        self._dio_resume_until: int | None = None   # a return's Main_Reinit / Main_Init runs until this frame
        self._dio_warm_return = False               # ...and whether it is the warm branch (`resuming` while it runs)
        self.netsync: dict = {
            "enabled": False, "role": "host", "instance": False, "selftest": False, "forced": False,
            "bench": False, "l1": False, "l1_pinned": False, "l1_forced_control": False,
            "suppress": False, "align_win": -1, "align_text": -1, "applied_seq": -1,
            "wait_armed": False, "wait_ms": -1, "wait_limit_ms": 8000, "pending": None,
            "lock": False, "stale": False,          # F3.2 bench levers (published only under "authority")
        }
        self._lockstep_seq = 0
        self._wait_since_frame = 0
        #: The uid the last accepted `netsync talk` replayed -- the stand-in's own receipt for a test. NOT published:
        #: no engine's AppendNetsync carries it, so a state read of it would pass only here.
        self.last_talk_uid: int | None = None
        self._guest = _GuestDialog()
        #: The open window as the F3.2 guest keys it against the host's events: its ``Id`` (winnum) and
        #: ``TextId``, and FlagButtonInh (a script-polled ``[NFOC]`` line: never suppressed, never driven, handed
        #: back by the orphan rule). One window at a time -- the stand-in's dialogue is one window.
        self.dialog_id = 0
        self.dialog_text_id = 0
        self.dialog_inh = False
        #: Memoria.ini ``[Control] DisableMouseForMenus``: ``netsync click`` is refused under it.
        self.disable_mouse_for_menus = False
        self._dialog_gen = 0                       # bumped by every say()/offer(): a NEW window (dialogs are pooled)
        #: The open window's page as the engine publishes it (windows[].page = Dialog.CurrentPage): 1 on the first
        #: visible page -- PrepareNextPage post-increments (`PageParsers[this.currentPage++]`, Dialog.cs:1550) the
        #: moment the Phrase is set -- and +1 per page turn. 0 only with no window.
        self._dialog_page = 0
        #: The story-write trace (s88), modelled as its CONTRACT: the `storytrace` verb's gates, the
        #: state block, and proto-1 rows -- the `arm`/`off` epochs, the harness's own pokes as `harness`
        #: rows, and a script store a test drives through :meth:`script_store`. Not the engine's
        #: suppression or its residue net: those are the DLL's to prove in-game. `storytrace_proto`
        #: None models an engine that predates the trace (no block published at all).
        self.storytrace_proto: int | None = 1
        self.story_on = False
        self.story_rows = 0
        self.story_error: str | None = None
        self.story_bytes = bytearray(2048)          # the modelled gEventGlobal the rows read old/new from
        self.scenario = 0
        self.donor = None                           # EffectiveFieldId: None = the field's own id
        #: H13 (research/o5_design.md 3.1), OPT-IN: the sink's same-value SUPPRESSION (:meth:`_story_site`). False (the
        #: default): every store is a row, as above. True: the engine's per-site rule -- a site's first same-value store
        #: and its first STORY_CHANGE_ROWS changes are rows, the rest counted -- and the counts closed as ``c`` rows at
        #: every epoch's close (:meth:`_story_counts`). `story_suppressed` counts the stores it did not emit (the
        #: published ``suppressed`` stays 0: no reader reads it); `_story_sites` is the running epoch's site table.
        self.story_suppress = False
        self.story_suppressed = 0
        self._story_sites: dict = {}
        #: The floor: one box ``(x0, z0, x1, z1)``, or a list of boxes whose UNION is walkable (a room
        #: opening into a corridor). A step that lands in none of them is clamped to the box he is in.
        #: Or a real walkmesh (anything with ``point_on_walkmesh``: a stock field's, through
        #: ``pathfind.PlayerWalkmesh``): his centre must stand on it -- see :meth:`_move_to`.
        self.walkmesh = walkmesh
        #: On a real walkmesh, how far his CENTRE is kept off every wall (``distance_to_boundary``) -- the
        #: engine's controller radius, cam.COLLISION_RADIUS_W, when a test sets it; None = anywhere on the mesh.
        #: A step that would come closer stops where it reaches that line, as the engine pushes him back out
        #: to it (2507's wall-slide samples sit 80-81u off its boundary), and the rest of the step slides on
        #: along the wall. A gateway zone only a few units deep past that line is then as hard to stand in as
        #: in the game. Placed nearer a wall than that (a scene's own spot), his first moving frame pushes him
        #: straight out onto the line, as the engine's does (:meth:`_pushed_out`).
        self.clearance: float | None = None
        #: H26 (research/o8_design.md 3.1), OPT-IN: the clearance PER FIELD -- ``{field id: radius}``, read through
        #: :meth:`_clearance` wherever a step reads `clearance` (the levels' radius rule, the never-closer rule, H21's
        #: squeeze and the push-out). Empty (the default): every field walks at `clearance`, today's one value. One run
        #: crosses fields whose controllers differ -- 164's Steiner is radius 80 (DoEventCode.cs:1507-1508, through
        #: EffectiveFieldId), 165's 120.
        self.clearances: dict = {}
        #: H20 (research/o7_design.md 3.1), OPT-IN: a STACKED walkmesh's levels, by field id -- ``{field id:
        #: Levels}``. Empty (the default): today's fake. On a field with an entry, :meth:`_move_to` keeps him on ONE
        #: level of it (the open triangle under him within a step of his height), walls him in by his own level's walls
        #: alone, and publishes his height in ``player[1]`` (the agent's ``pos[1]``: f[1] = -pos[1]); a scripted
        #: placement sets it (:meth:`place_height`). `clearance` is required there (ValueError otherwise), and a level's
        #: ``squeeze_slack`` turns on H21's pinch rule.
        self.levels: dict = {}
        #: Frames the character keeps moving after the direction is released. Measured on bench 30801,
        #: a hold covers what it commanded give or take ONE frame at 60 fps (`hold down 1` moves 60
        #: units at run speed, `hold down 31` moves 900) -- which the smooth 60 fps model (half a tick
        #: every frame) cannot reproduce without a frame of tail: a stand-in that stopped dead on
        #: release could not reproduce it at all -- and the pathological case, where the tail lands
        #: inside the NEXT burst's measurement window and is attributed to the direction pressed
        #: there, is what a test raises this to reproduce.
        #: Counted in FRAMES, moved in TICKS: a coast frame applies the last press to that frame's own ticks.
        #: ⚠ THE ENGINE RUNS NO SUCH COAST: HarnessAgent.IsHeld keys on the current Time.frameCount (:70-77) and MovePC
        #: reads the pad on every call (FieldMapActorController.cs:601-630) -- nothing buffers a key a frame. The bench's
        #: extra frame is the tick a one-frame hold catches in one phase of WHOLE ticks, and the published position's
        #: lag (tickrate.TAIL_TICKS). So None (the default) is ONE frame only where the smooth model is the fake -- 60
        #: fps, mean ticks, what every walk before the tick model was written against -- and NONE anywhere else: at
        #: 30 fps a frame is a whole tick, and a coast there moved him a tick the engine never runs, exactly Rate.reach
        #: with no slack (a sure-side test could not catch a tick of over-credit). A test that sets it gets what it sets.
        self.coast_frames: int | None = None
        self._coast = None                  # (dx, dz, calls a tick, frames_left): the last press's direction and gait
        #: THE PUBLISHED POSITION'S LAG, where a test models it: None (the default) publishes each frame's position with
        #: that frame's ticks run; else a predicate of the frame number -- true on a frame whose publish shows the
        #: position from BEFORE its own ticks, as the agent's does when its Update runs before HonoBehaviorSystem's (the
        #: one frame the research measured) -- an order Unity does not fix, so it may come and go (tickrate.TAIL_TICKS;
        #: Session.SETTLE_TICKS is two ticks for it).
        self.publish_lag = None
        self._pos_before = [0.0, 0.0, 0.0]  # the player's position before this frame's ticks (`publish_lag`)
        #: The field INHIBITS RUNNING (stock's DASHOFF, EventEngine.DoEventCode.cs:3009-3012): a run hold walks -- one
        #: MovePC call a tick, a turn's lerp too (FieldMapActorController.cs:196-198) -- and ``input.dash_inh`` reads 1,
        #: as the agent publishes it (AppendInput).
        self.dash_inhibit = False
        #: Whether the agent has redirected its save path away from the player's folder. Modelled
        #: because the driver must VERIFY this rather than trust it -- an unchecked sandbox is a
        #: check that cannot fail, and what it would fail to catch is the owner's overwritten game.
        self.save_sandboxed = True
        #: `[Control] SoftReset` in Memoria.ini. The ENGINE default is 0; this install has it on.
        #: False here models the install where the recovery ladder's top rung simply does not exist,
        #: which the driver must report honestly rather than hang on.
        self.soft_reset_enabled = True
        self.soft_resets = 0
        #: H9 (research/o3_design.md 3): the UI states the soft-reset combo fires in -- see :meth:`_check_soft_reset`.
        #: The default is today's pair; the engine's set is :data:`SOFT_RESET_ENGINE_UI` (BattleHUD among them,
        #: BattleResult never). A playing movie swallows the combo whatever this says.
        self.soft_reset_ui: tuple = ("FieldHUD", "WorldHUD")
        #: H9: True -- ``warp`` refuses unless ui_state is "FieldHUD", as the agent does (Ff9mkDebugMenu.Warp is false
        #: off the field HUD, and HarnessAgent throws "warp refused (not on a field?)"): nothing is written, nothing
        #: moves. False (the default): today's fake, a warp from any state.
        self.warp_field_only = False
        #: H9: False -- a warp lands with control OFF. The engine zeroes control at every field start (EventEngine.cs:
        #: 627) and a field that never grants it (61-63: research/o3_design.md 0.2 #4, #19) leaves it off; a test's
        #: director gives it where a field would. True (the default): today's warp, control handed over on arrival --
        #: which is how a smoke built on Session.warp() (its wait_playable needs control) passes here and hangs there.
        self.warp_arrive_control = True
        #: H16b (research/o6_design.md 3.2): fields whose running scene SWALLOWS the soft reset -- O1d's measurement (a
        #: soft reset through Alexandria's running opening scene did not reach the title: PLAN.md O1, story-o1d),
        #: whatever the engine's reason. Empty by default: the combo fires as :meth:`_check_soft_reset` says.
        self.reset_blocked_fields: set = set()
        # -- battle ----------------------------------------------------------------------------
        #: `party.battle_no`: monotonic, save-persistent, never reset. The ONE unambiguous "a battle
        #: started" edge -- modelled as such because every driver wait is anchored to it.
        self.battle_epoch = 7
        self.battle_active = False
        #: The diorama property that makes a whole class of assertion vacuous: under isDebug the
        #: engine suppresses the auto-end, so the battle CANNOT finish. The driver must refuse to
        #: wait for a result here rather than hang, and this is what lets a test prove it does.
        self.battle_debug = False
        #: btl_result. ⚠ 0 both DURING a battle and BEFORE any has run -- the ambiguity is the point.
        self.battle_result = 0
        self.battle_scene = -1
        #: Scenes that open the battle TUTORIAL screen before the first command (battle.cs:100-105 opens it on
        #: scene 336, the Masked Man): ui_state "Tutorial", no command menu, until one Confirm closes it
        #: (TutorialUI.cs:116-125). A fight that waited for a command there would wait out its whole timeout.
        self.tutorial_scenes: set = set()
        self._tutorial = False
        #: H9 (research/o3_design.md 3), each None by default -- today's fake exactly. A SCRIPTED end, King Leo's
        #: latch (BSC_TH_E002 e1 t1 [587] ``cur.hp <= 10000``, latched at [601]): ``{"unit": name, "hp_raw_le": n,
        #: "result": r, "after_frames": k}`` -- the first time that unit's ``hp_raw`` is at or below ``n`` after a
        #: command resolves, the battle ends with ``r`` ``k`` frames later, whoever is standing; it latches once a
        #: battle. Without it, `_settle_battle` (one side gone) is the only end.
        self.battle_script_end: dict | None = None
        #: The ENGINE'S END ORDER (research/o3_design.md 0.2 #8): ``{"field": id, "fade_frames": a, "result_frames":
        #: b, "load_frames": c, "arrive_control": False}``. Every end (:meth:`end_battle`) then runs four phases: (1)
        #: the FADE, ``a`` frames -- the end's result published while the field id is still the battle's,
        #: ``battle_active`` True, ui BattleHUD, no command asked; (2) the OVER FRAME, one frame -- a result of 2 folds
        #: to 1 AND the field id becomes ``field``, together (HonoluluBattleMain.UpdateOverFrame), ui "BattleResult",
        #: still active; (3) BATTLERESULT, ``b`` frames, the same (no panel); (4) the LOAD, ``c`` frames --
        #: ``battle_active`` False, ui still "BattleResult" (the lag); then FieldHUD in ``field``, control as
        #: ``arrive_control`` says, a new visit (a fresh load). No sample ever pairs ``field`` with a result of 2.
        #: None: today's end -- the same field, FieldHUD at once.
        self.battle_exit: dict | None = None
        #: Every phase of a `battle_exit` end as it began: ``{"phase": "fade" | "over" | "load" | "field", "frame",
        #: "field", "result", "active", "ui"}`` -- the frame the scene went is the "load" row's.
        self.exits: list[dict] = []
        self._bexit: tuple | None = None           # (phase, the frame it ends on, the end's result) while one runs
        self._script_end: tuple | None = None      # (the frame it is due, its result) once the latch fired
        self._script_latched = False
        #: THE COMMAND RACE, pinned: ``{"result": r, "nth": n, "op": "battlecmd" | "menus"}`` -- the battle ENDS with
        #: ``r`` (0: the scene goes with no result) as its ``n``-th (default 1) step ``op`` (default "battlecmd")
        #: arrives, BEFORE that step runs: an end (King Leo's scripted one in battle 338) landing between a driver's
        #: read of "asking slot N" and its command, which the step then meets as the agent does -- no battle HUD; with
        #: `battle_exit`, the fade's "not asking". With ``"after": a`` (frames) the step RUNS instead -- a ``menus``
        #: collects its menu and the request acks as usual -- and the end lands ``a`` frames later, after the drain (0:
        #: the step's own frame, so no published sample ever carries that menu): the end between the ack and the
        #: driver's read of the menu, which the battle doc carries only while the battle is up. Once a battle. None
        #: (the default): no such end.
        self.battle_end_on_command: dict | None = None
        self._race_steps = 0                       # this battle's steps of the raced op, for `battle_end_on_command`
        self._race_due: tuple | None = None        # (the frame it is due, its result): an `after` end, scheduled
        #: The naming screen (``Menu(1, char)``, a scene beat ``{"naming": char}``): each character named, in order.
        self.named: list[int] = []
        #: H17 (research/o6_design.md 3.3): the name a visit's naming screen SAVED, by character -- what PLAYER.Name
        #: holds after its OK; empty until one is saved, so a page's [STNR] renders the pre-filled default.
        self.names: dict[int, str] = {}
        self._name_focus = False
        self.battle_units: list[dict] = []
        self.battle_bonus = {"exp": 0, "gil": 0, "ap": 0, "items": 0}
        self.battle_commands: list[list[int]] = []
        #: Whose command menu is open -- BattleHUD.CurrentPlayerIndex. -1 between turns.
        self.battle_turn = -1
        self.battle_ready: list[int] = []
        self.battle_done: list[int] = []
        #: The last `menus` collection. ⚠ DELIBERATELY NOT CLEARED BETWEEN BATTLES, like the engine's
        #: own fields: a driver that trusts it without checking the stamp must be able to be caught.
        self.battle_menu: dict = {"slot": -1, "epoch": -1, "commands": [], "abilities": [],
                                  "items": []}
        #: cmd_status bit 0 -- a SysEscape command is queued and the party is leaving.
        self.escaping = False
        #: BattleHUD._runCounter: UNBROKEN real seconds with both bumpers down. Resets to 0 the
        #: instant either lifts, which is the whole reason a re-issued hold used to be fatal.
        self.run_counter = 0.0
        #: The per-roll escape chance, as a fraction. The engine computes it from levels; here it is
        #: a dial so a test can have a flee that always lands AND one that never does.
        self.escape_rate = 1.0
        #: When true the bumpers are held but the battle never sees them -- an input path that is
        #: not connected, as opposed to a roll that has not landed. flee() must tell them apart.
        self.deaf_bumpers = False
        #: btl_scene.Info.Runaway -- whether this scene permits running at all.
        self.scene_runaway = True
        #: ATB gained per frame, per side. ⚠ ZERO BY DEFAULT: a stand-in whose gauges fill on their
        #: own would make every battle test race a clock it did not ask for -- and the enemy would
        #: chew through the party in the middle of an assertion about HP. A test that wants turns
        #: turns them on, which also makes the turn machinery an explicit part of what it tests.
        self.atb_gain = 0
        self.enemy_hit = 90
        #: Frames between committing a command and its RESOLUTION -- when the damage lands and the
        #: slot leaves ready/done and can be asked again (btl_cmd dequeues, then
        #: InputFinishList.Remove). Without this a slot that acted once never acted again and no
        #: fight could be played out. A test that needs the "its turn is spent" refusal pins it
        #: high, so the refusal never races the resolution.
        self.cmd_resolve_frames = 45
        self.battle_pending: list[list] = []
        #: FF9BMenu_IsEnable(): the command phase is live. False through the opening camera and
        #: again once the fight is over -- which is exactly when everything else in the turn block
        #: is holding the LAST battle's contents.
        self.commands_enabled = False
        #: Frames of opening camera before InitialBattle() runs. ⚠ NOT ZERO BY DEFAULT: the stale
        #: window is the whole point, and a stand-in with no intro could not reproduce the freeze
        #: that a stale `turn.slot` caused in a real second battle.
        self.battle_intro_frames = 30
        self._intro_until = 0
        self.gateway: tuple[float, float, float, float, int] | None = None
        #: Walk-in gateway REGIONS per field, modelled on the engine's ExitField rather than on the
        #: instant `gateway` box above: ``{field id: [{"zone": [[x, z], ...], "to": id,
        #: "arrive": (x, z)}]}``. Stepping into a zone takes control on THAT frame; the field changes
        #: `exit_frames` later (the fade), and the player appears at ``arrive`` with control -- so a
        #: button still held at that moment walks him in the destination, which is the whole bug the
        #: routed verbs exist to avoid. ``exit_frames = 0`` changes the field on the same frame.
        #:
        #: As TreadQuad (TreadQuad.cs:6-22), the FIRST region in the list that contains his centre answers,
        #: and only it: a region that answers without firing shadows every region after it. Opt-in keys, each
        #: absent by default (and a region without them behaves exactly as above):
        #:   * ``"face"`` -- stock's DOOR FACING GATE (scan_gateways' ``face_gate``): the region fires only
        #:     while his yaw `_face_deg` faces his projection onto its first edge
        #:     (content.doorface.door_faced) -- True for the stock window (48, 208), or an explicit
        #:     ``[lo, hi]``. A region that fails it answers and fires nothing, and -- as the engine's tag 2
        #:     runs every tick he has control -- it is tested again on every frame he STANDS in it too, so a
        #:     press that turns him without moving him (into a wall) can fire it.
        #:   * ``"to": None`` -- a DEAD region: armed, answers, never fires (a stock region whose tag 2 returns
        #:     at once still blocks every region after it).
        #:   * ``"arrive_face"`` -- his yaw, in degrees, where he appears (applied with ``arrive``).
        #:   * ``"points"`` -- the ENGINE's polygon (scan_gateways' ``region``): membership by
        #:     content.doorface.region_contains (the ring of triplet triangles; a 5+-gon's middle is dead)
        #:     instead of the even-odd test on ``zone``, and the facing gate's first edge.
        #:   * ``"take": True`` -- a WALK-IN TRIGGER, not a gateway: entering it takes control on that frame
        #:     (its tag 2's DisableMove) and nothing warps -- logged in `fired` with ``to`` None. Control comes
        #:     back only when the test's scene gives it back.
        #:   * ``"arrive_control": False`` -- the destination arrives with control OFF: the arrival scene's to
        #:     hand back (a test's director gives it), as 101's Herald and 115's Puck hold it.
        #:   * ``"walkout"`` -- H16 (research/o6_design.md 3.1): ExitField's WALK-OUT, ``{"to": [x, z], "speed": u,
        #:     "stop_z": z}`` (``speed`` default 60, ``stop_z`` default None): from the fire to the switch he keeps
        #:     moving toward ``to`` at ``speed`` units a field tick -- MOVJ, at the speed of his last controlled frame
        #:     (HonoUpdate's 60 for a run) -- control off, and stops at ``to`` or, ``stop_z`` given, once his z passes
        #:     it (where pathing holds his centre a radius short of the floor's end). Without it he stands where the
        #:     region took him, as ever. The switch itself waits on `exit_gate` when a test holds one.
        #: ⚠ An UNGATED region fires only on a frame a step (or the coast after one) lands him in it, never
        #: while he stands there -- the engine re-tests those every tick too, but the suite's fixtures that
        #: place him inside a zone depend on the step-only rule, so only a gated region gets the standing test.
        self.regions: dict[int, list[dict]] = {}
        self.exit_frames = 0
        #: Every region that fired: ``{"frame", "from", "to", "executed"}`` -- ``executed`` is
        #: ``len(self.executed)`` at that moment, so a test can name the steps issued AFTER it.
        self.fired: list[dict] = []
        self._exit: tuple[int, int, tuple[float, float]] | None = None   # (due frame, dest, arrive)
        self._arrive_face: float | None = None     # the firing region's ``arrive_face``, applied on arrival
        self._arrive_control = True                # the firing region's ``arrive_control``, applied on arrival
        self._walkout: dict | None = None          # H16: the firing region's walk-out, until the switch
        #: H16's GATE (research/o6_design.md 3.1, rev. 2): a ``threading.Event`` a TEST holds; None (the default) is
        #: today's fake. With it, a scheduled exit's switch waits, once its ``exit_frames`` have run, until the event is
        #: set -- he stands where the walk-out left him meanwhile -- so a test can fix which side of route_to's return
        #: the switch falls on, whatever the harness thread's load.
        self.exit_gate = None
        #: A LADDER, where a test models one (115's climb: e15 t3 DisableMove, then the climb loop reads B_KEY(16)
        #: every tick): ``{"top": y, "bottom": y, "step": units a field tick}`` -- y is ``player[1]``, the ``pos[1]``
        #: the agent publishes, and UP is the way from ``bottom`` to ``top``: on 115's real ladder it RISES as he climbs
        #: (stock rehearsal o2-rh-115: 0 -> 2691 in 9 bursts, then held there), so the model reads the direction from
        #: the pair rather than assuming one. While `climbing` (control OFF, as the climb runs), each field tick moves
        #: him ``step`` up while Up or Left is held and down while Down or Right is (B_KEY(96) descends); past ``top`` he is
        #: `climbed` (control stays off: the scene at the top takes over), past ``bottom`` the climb ends with
        #: control back (the bottom's EnableMove). None: no ladder.
        self.ladder: dict | None = None
        self.climbing = False
        self.climbed = False
        #: Bodies the walkmesh does not know about -- someone standing still in the way: ``{field id:
        #: [(x, z, r) or (x, z, r, solid), ...]}``, ``r`` centre to centre (WalkMesh.Collision). A step
        #: into one that has it in FRONT of him is pushed back out to ``r`` along the line from its
        #: centre (FieldMapActorController.cs:776-797), so a press at an angle slides him round it and a
        #: press straight at it stops him dead -- stock Zidane pressed into a Dali child on 350, six
        #: bursts, 0u. A push-out that lands in another body is undone, move and all.
        #: A body is PASSABLE unless ``solid`` (object flag 16, which no NPC on stock 350 sets): the
        #: engine's sLockTimer (CheckCollFallback, :822) counts one a colliding MovePC call, flips to
        #: -25 at 25, and the push-out is off until it counts back to 0 -- so one unbroken hold walks
        #: through him, and bursts with a pause between never do. Counted here in MovePC calls, a tick's
        #: calls (two running, one walking or idle) times the ticks a frame holds -- at the default 60 fps, mean
        #: ticks, a running frame one and a walking or idle frame half; whole calls one at a time when quantized.
        #:
        #: A body may also be a DICT -- the s89 object it models, published under ``objects`` (see
        #: `objects_mode`): ``{"x", "z", "r"}`` and optionally ``"y"`` (it collides only while |dy| < 400,
        #: WalkMesh.cs:922), ``"solid"``, ``"coll"`` (False: walk-through), ``"uid"`` / ``"sid"`` (default
        #: 128 + / 10 + its index), ``"shown"``; ``"range_r"`` -- a CONTACT trigger: with control, standing
        #: still or not, his centre inside it fires the entry's Range (CollisionRequest, every tick; logged
        #: in `touched`; only while ``coll``, as mode 2 keeps the pair rule), and with ``"talk_r"`` too it
        #: also fires inside that while he faces it; ``"to"`` / ``"arrive"`` make that Range a warp (stock
        #: 350's Vivi sends the run to 358); and ``"path"`` [(x, z), ...] with ``"speed"`` (units a frame of the
        #: calibrated 60 fps model -- ``speed / WALKER_FRAME_TICKS`` a field tick, as MoveToward steps once a tick, so
        #: the same units a SECOND at any `render_fps`) makes
        #: it a WALKER, back and forth along the path (``"once"``: to its end, then it stands), published
        #: ``moving`` -- and held while its next step would come within ``r`` of him (MoveToward stops on
        #: the player), still ``moving``.
        self.blockers: dict[int, list] = {}
        #: What `objects` / `pushout` publish: "listed" (the s89 agent: the list on a field, null off
        #: one), "null" (an agent that could not walk the list -- never a partial one) or "absent" (an
        #: engine without s89: no key at all).
        self.objects_mode = "listed"
        #: Every contact trigger that fired: ``{"frame", "field", "uid", "kind" ("range" / "talk"),
        #: "executed"}`` -- once per entry into its radius.
        self.touched: list[dict] = []
        #: Every step that met a body -- the push-out ran, or the step was refused: ``{"frame", "uid"}``.
        #: A router that sees the bodies should leave this empty.
        self.contacts: list[dict] = []
        self._in_trigger: set = set()             # (field, body index) whose trigger he stands in
        self._facing = (0.0, 1.0)                 # the direction last pressed (the talk search wants +-90 deg)
        #: His model yaw, Actor.rotAngle[1] in degrees (0 faces -z, 90 -x, +-180 +z, -90 +x) -- what a gated
        #: region reads (``regions`` ``"face"``). Every tick a held direction spends MovePC calls (a press, or the
        #: coast after one, whether or not he moves: a press into a wall turns him too) turns it toward that
        #: direction, 40% a call (content.doorface.turn_step; FieldMapActorController.cs:744-761 at stock 6b8bb2d5)
        #: -- a tick's calls its step over the 30u a call steps (content.doorface.movepc_calls): one a tick walking,
        #: two running, so a frame's the ticks it holds times that -- at the default 60 fps, mean ticks, a run frame
        #: one call and a walked one half, ON AVERAGE ("quantized" ticks, or `tick_phase`, turn him in whole calls
        #: instead). Standing, frozen or without control it holds. PRIVATE, and settable by a test: the agent
        #: publishes ``dir`` 0 on a field (PosObj.rot[1], which a field never writes), and so does this stand-in.
        self._face_deg = 0.0
        #: None (the default): a frame turns him by its ticks' calls -- in mean mode its AVERAGE, half a call a walked
        #: frame at 60 fps: smooth, and what every walk written before this was written against. 0 or 1: the
        #: engine's WHOLE calls FOR THE TURN ALONE, the precursor of ``ticks="quantized"`` kept for the tests pinned
        #: on it -- a 30 Hz tick on every other frame of the 60 fps model (FPSManager.cs:77-110 at stock), falling on
        #: the frames whose number is that phase mod 2, where the frame turns him by its tick's whole calls (a walked
        #: frame 1, a run frame 2; nothing on the frames between), and the settle passes of a turn count only there.
        #: Only the TURN is whole: the step stays a frame's average, as every walk in the suite measures it. A press of
        #: an odd number of walked frames then turns him the fewer whole calls in one phase and the more in the other
        #: -- what a planner that credits half calls cannot see (harness.tickrate.Rate.calls_sure). Refused (ValueError)
        #: unless the fake is that model: ``render_fps`` 60 and ``ticks`` "mean" -- `_check_legacy_knobs`.
        self.tick_phase: int | None = None
        #: The facing as memoria-patch s90 publishes it, and its in-place ``turn``. "absent" (the DEFAULT -- an
        #: engine without s90, what every walk written before it was written against): no ``player.yaw`` /
        #: ``player.face`` keys, and ``turn`` raises ``unknown op 'turn'`` as the old agent's Execute does.
        #: "published" (the s90 agent): on a field with a controlled character ``player.yaw`` is round(`_face_deg`,
        #: 3) and ``player.face`` content.doorface.facing_byte of it -- a JSON NUMBER, as state.json's numbers are --
        #: both null off one (HarnessAgent.PublishState); and ``turn <dir>[+<dir>] [frames]`` (:meth:`_begin_turn`)
        #: holds the direction KEYS with no axis, turning `_face_deg` by the frame's MovePC calls and never stepping
        #: him, then reports ``turn_end`` once the field has judged the final facing (:meth:`_service_turn`).
        self.facing_mode = "absent"
        #: `[AnalogControl] Enabled` in Memoria.ini. False models the install whose key path would STEP him (MovePC
        #: normalises the key vector and nothing zeroes it, FieldMapActorController.cs:710-711): the agent refuses
        #: every ``turn`` there (``[AnalogControl] Enabled=0 -- ...``).
        self.analog_control = True
        #: The event passes the agent lets the field run on a turn's final facing, after its keys lift, before it
        #: reports ``turn_end`` (HarnessAgent.TurnSettlePasses: the region pass that reads the facing runs a pass
        #: after the MovePC call that wrote it). Counted as the agent counts them -- FRAMES that ran a pass
        #: (HarnessAgent.ServiceTurn: "a frame that runs two passes counts once"): every frame in mean mode (each
        #: holds a share of a tick), the frames that ran a whole tick in quantized mode, and under `tick_phase` its
        #: tick frames. A test raises it to hold the report well past the request's ack.
        self.turn_settle_passes = 2
        #: MovePC calls one frame of an IN-PLACE turn spends, when set -- an override of the tick model. None: the
        #: frame's ticks times the gait's calls a tick (run: two; with ``cancel`` held, walk: one) -- at the default
        #: 60 fps, mean ticks, one call a run frame and half a walked one, the calibrated rate the driver used to plan
        #: by. Set, it is the calls every frame spends whatever `render_fps` says (the turn of a monitor that is not
        #: the calibrated one, before the fake had a render rate). Mean ticks only -- `_check_legacy_knobs`.
        self.turn_calls: float | None = None
        #: A HUMAN at the controls, as ``turn`` sees one: ``stick`` the |axis| a physical stick or key pushes
        #: (HarnessAgent.PhysicalAxis), ``click_path`` a click-to-move path pending (the controller's hasTarget /
        #: movePaths). Over STICK_THRESHOLD the agent refuses a turn (``a physical stick or key is pushing the axis``)
        #: and CUTS one open (``axis``); a pending path refuses one (``a click-to-move path is pending``). Neither
        #: moves him here -- the fake's walk is the harness's keys alone.
        self.stick = 0.0
        self.click_path = False
        #: The ``turn`` being reported, None when none is (HarnessAgent's _turnFrom / _turnLift / _turnField /
        #: _turnPo and its start): ``{"from", "lift", "field", "visit", "x", "y", "z", "yaw0", "passes"}``; and
        #: `_turn_keys`, the directions a turn holds (_turnMask) -- held keys no step is ever taken on (MoveHeld).
        self._turn_open: dict | None = None
        self._turn_keys: set = set()
        #: Bumped by every warp and every arrival: a new visit's actor is a new controlled actor, as a same-id reload
        #: makes new ones -- a turn begun on the old one is cut ("player"; "field" when the id changed too).
        self._visit = 0
        self._lock = 0.0                          # EventEngine.sLockTimer
        self._lock_free = 1                       # sLockFree: 0 while the last body touched is solid
        self._coll = 0.0                          # SCollTimer, in ticks (COLL_TICKS after a push-out)
        #: Movement FREEZES with control held -- MovePC's other gate, the script's pad mask
        #: (EventInput.IsMovementControl), which the agent does not publish: ``{field id: [{"zone":
        #: [[x, z], ...], "frames": n}]}``. Stepping into a zone holds all movement for ``n`` frames OF THE
        #: CALIBRATED 60 FPS -- ``n`` / 2 field TICKS: the script that masks the pad counts once a tick
        #: (ProcessEvents), whatever the render rate -- (None = for good) while `control` stays True. Each zone
        #: fires once; a warp ends a freeze. `_frozen_ticks` is in `ticks_run`; `_frozen_until`, in FRAMES, is a hold on
        #: movement a test lays on (or lifts) by hand -- a frame count it means literally, which replaces every hold.
        self.freezes: dict[int, list[dict]] = {}
        self._frozen_frames: float = 0
        self._frozen_ticks: float = 0
        self._froze: set = set()                  # (field id, index) of every freeze zone that fired
        #: every op the fake ever executed, so a test can assert a step was DELIVERED rather than
        #: inferring it from a state that several other ops could also have produced.
        self.executed: list[list[str]] = []
        self.arm_transitions = 0
        #: Publishes that STALL MID-REWRITE, one queued duration (seconds) consumed per publish --
        #: see :meth:`stall_publish`. Empty by default: the ordinary publish replaces the file.
        self._publish_stalls: list[float] = []
        #: events.jsonl appends that COLLIDE with the driver's read, by event kind: ``{"turn_end": 1}`` makes the next
        #: ``turn_end`` append fail as the agent's File.AppendAllText does while the driver has the log open
        #: (IOException). The agent keeps such rows BUFFERED and writes them with its next event, whatever that is
        #: (HarnessAgent.Event / FlushEvents) -- so a row can reach the log late, behind a row written after it was
        #: made, and only once something else is logged. `_pending_events` is that buffer.
        self.event_collisions: dict = {}
        self._pending_events: list = []
        #: Set while a stalled publish holds state.json truncated and EMPTY, so a test can read the
        #: channel inside the gap rather than hoping to land in it.
        self.stalling = threading.Event()
        # -- H10-H12 (research/o4_design.md 3): the machine beats, opt-in -------------------------------------------
        #: The machine beat running now -- a ``{"keyon_pair": knobs}`` or ``{"chanbara": knobs}`` scene beat
        #: (:meth:`_start_machine`) -- else None. It reads the agent's HELD keys per frame and runs whole field ticks
        #: (:class:`_Machine`), so a press is judged on the frame and the tick it lands on, never at execute time.
        self._machine = None
        #: H11: one row per prompt the Chanbara beat armed -- ``{"fight", "n", "dbtn", "value", "arm_tick", "arm_frame",
        #: "edge_tick", "edge_frame", "j", "result", "sb38", "max_combo"}`` -- its arm tick S, the tick its key's edge
        #: landed on and the TRUE j (the tests' oracle for the driver's j bounds); ``result`` "hit", "miss" or "timeout";
        #: ``sb38`` and ``max_combo`` what the roll's filters read.
        self.chanbara_log: list[dict] = []
        #: H11: the fight's Map variables as the last score read them (``I30`` .. ``I50``, ``b47`` ...), for a test.
        self.chanbara_vars: dict = {}
        #: H11: what EMinigame reported to Steam: "Encore" once a score of 75 or more is read (EMinigame.cs:34-38).
        self.achievements: list[str] = []
        #: H11: the gil AddGi gave after page 128 (its ``[NUMB=1]``).
        self.gil = 0
        #: H10/H11: every window a machine beat listed, as it went -- ``{"event": "open" | "close" | "gone", "kind",
        #: "slot", "text", "frame", "tick", "rt"}`` (``tick`` the beat's own field-tick count).
        self.machine_log: list[dict] = []
        #: H14 (research/o5_design.md 3.2): every step a visit beat (:class:`_VisitBeat`) started, as it started --
        #: ``{"index", "field", "at", "kind", "tick", "frame"}``: the visit's ``index`` knob, the field it ran in, the
        #: step's place (``"7"``; ``"12.1.0"`` inside a choice's branch "1"; ``"8.s.0"`` in a side scene), its kind, and
        #: the beat's tick and the fake's frame it began on. With ``stairs`` rows of the height test's loss
        #: (``kind`` "lost": where the contour took control) and of a side scene or the back door firing.
        self.visit_log: list[dict] = []

    # -- lifecycle -----------------------------------------------------------------------------
    def start(self) -> "FakeGame":
        self.shots.mkdir(parents=True, exist_ok=True)
        if self.writes_unity_log:
            self.unity_log.parent.mkdir(parents=True, exist_ok=True)
            self.unity_log.write_bytes(b"Initialize engine version: 5.2.3p2 (fakegame)\r\n")
        self._wall0 = time.time()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    # -- the clock -----------------------------------------------------------------------------
    # THE ENGINE'S TIME, MODELLED ON A VIRTUAL CLOCK. A frame is 1 / render_fps virtual seconds (plus any hitch), the
    # seconds become field ticks at tick_hz (FIELD_TPS x fast_forward) -- their average ("mean") or FPSManager's whole
    # ones ("quantized") -- and everything the engine does once a tick is done once a tick here: MovePC's steps (one
    # call walking, two running, 30u each: FieldMapActorController.cs:198-209 at stock 6b8bb2d5) and its turn (40% a
    # call), the push lock's count (a call at a time), SCollTimer, a walker's step, a contact's and a gated region's
    # re-test, a freeze's countdown (the script's pad mask counts ticks). Frame-counted things stay frame-counted, as
    # the agent counts them: holds, waits, publishes, polls -- and the fade, as a SIMPLIFICATION (its duration is the
    # engine's, not the agent's; no test yet runs a fade off 60 fps). At the defaults -- 60 fps, mean -- every frame is
    # half a tick, and the fake moves EXACTLY as it did when its speeds were 30u / 15u a frame.
    @staticmethod
    def _positive_fps(v) -> float:
        v = float(v)
        if not (math.isfinite(v) and v > 0):
            raise ValueError(f"render_fps must be a positive number of frames a second, not {v!r}")
        return v

    @property
    def render_fps(self) -> float:
        """The VIRTUAL render rate: the seconds a frame spans on the fake's clock (default 60). Settable mid-run -- a
        regime switch: the clock re-anchors, so rt stays continuous."""
        return self._render_fps

    @render_fps.setter
    def render_fps(self, value) -> None:
        value = self._positive_fps(value)
        self._check_legacy_knobs(render_fps=value)
        self._rt_anchor, self._rt_frames = self.rt, 0
        self._render_fps = value

    @property
    def tick_mode(self) -> str:
        """``"mean"`` or ``"quantized"`` (`TICK_MODES`), as constructed with ``ticks=``."""
        return self._tick_mode

    @tick_mode.setter
    def tick_mode(self, value: str) -> None:
        if value not in TICK_MODES:
            raise ValueError(f"ticks must be one of {TICK_MODES}, not {value!r}")
        self._check_legacy_knobs(tick_mode=value)
        self._tick_mode = value

    @property
    def tick_phase(self) -> int | None:
        return self._tick_phase

    @tick_phase.setter
    def tick_phase(self, value) -> None:
        if value is not None and value not in (0, 1):
            raise ValueError(f"tick_phase is None, 0 or 1, not {value!r}")
        self._check_legacy_knobs(tick_phase=value)
        self._tick_phase = value

    @property
    def turn_calls(self) -> float | None:
        return self._turn_calls

    @turn_calls.setter
    def turn_calls(self, value) -> None:
        self._check_legacy_knobs(turn_calls=value)
        self._turn_calls = None if value is None else float(value)

    def _check_legacy_knobs(self, **change) -> None:
        """Refuse a combination the two pre-tick knobs cannot mean: `tick_phase` is the 60 fps model's turn-only whole
        calls (a tick every other frame), so it needs ``render_fps`` 60 and mean ticks; `turn_calls` is calls a FRAME,
        which quantized frames (0, 1, 2 ticks) have no one value of. Checked on every change of any of the four, so
        no order of setting them can reach a silently wrong turn."""
        fps = change.get("render_fps", getattr(self, "_render_fps", 60.0))
        mode = change.get("tick_mode", getattr(self, "_tick_mode", "mean"))
        phase = change.get("tick_phase", getattr(self, "_tick_phase", None))
        calls = change.get("turn_calls", getattr(self, "_turn_calls", None))
        if phase is not None and (fps != 60.0 or mode != "mean"):
            raise ValueError(f"tick_phase models a 30 Hz tick every other frame of a 60 fps, mean-tick fake; this one "
                             f"is {fps:g} fps, {mode} -- use ticks='quantized' for whole ticks at any rate")
        if calls is not None and mode != "mean":
            raise ValueError("turn_calls is MovePC calls a frame, which quantized ticks (0, 1 or more a frame) have no "
                             "one value of -- leave it None and let the ticks turn him")

    @property
    def tick_hz(self) -> float:
        """Field ticks a second: FIELD_TPS x `fast_forward`."""
        return FIELD_TPS * self.fast_forward

    def hitch(self, seconds: float, *, frame: int | None = None) -> None:
        """Make ``frame`` (default: the next) take ``seconds`` more virtual time -- a stall the engine catches up in
        that frame's ticks."""
        at = self.frame + 1 if frame is None else int(frame)
        self._hitches[at] = self._hitches.get(at, 0.0) + float(seconds)

    def _advance_clock(self) -> None:
        """The virtual clock's frame: its seconds (``_dt``: 1 / render_fps + any hitch), ``rt``, and its field ticks
        (``_frame_ticks``; ``_steps`` as the world runs them -- one share in mean mode, one per whole tick quantized)."""
        self._clock_frame = self.frame
        extra = self._hitches.pop(self.frame, 0.0)
        self._rt_frames += 1
        if extra:
            self._rt_anchor += extra
        self.rt = self._rt_anchor + self._rt_frames / self._render_fps
        self._dt = 1.0 / self._render_fps + extra
        if self._tick_mode == "quantized":
            self._acc.fast_forward = self.fast_forward
            n = self._acc.advance(self._dt)
            self._frame_ticks, self._steps = float(n), [1.0] * n
        else:
            # the average, EXACT at the defaults: 30 / 60 is 0.5, so a run frame is 1.0 call and 30.0 units
            r = (self.tick_hz / self._render_fps if not extra
                 else self.tick_hz * min(self._dt, MAX_DELTA_TIME))
            self._frame_ticks, self._steps = r, [r]
        self.ticks_run += self._frame_ticks

    def _hold_frame(self) -> None:
        """A frame the counter did NOT advance on (``mode="frozen"``): no time passes, no tick runs."""
        self._clock_frame = self.frame
        self._dt, self._frame_ticks, self._steps = 0.0, 0.0, []

    def _frame_steps(self) -> list:
        """This frame's field ticks as the world runs them (`_steps`), the clock advanced first if the frame moved on
        without it -- a test that steps ``frame`` by hand and calls ``_step_world`` gets the same frame the loop
        would."""
        if self._clock_frame != self.frame:
            self._advance_clock()
        return self._steps

    # -- the two exception logs ----------------------------------------------------------------
    @property
    def unity_log(self) -> Path:
        return self.game_path / "x64" / "FF9_Data" / "output_log.txt"

    @property
    def memoria_log(self) -> Path:
        """The game ROOT's -- the working directory a launcher-style start gives the game."""
        return self.game_path / "Memoria.log"

    def throw(self, exc: str = "NullReferenceException",
              frames=("FieldMapActorController.MovePC ()",
                      "FieldMapActorController.UpdateMovement (Boolean copyLastPos)",
                      "HonoBehaviorSystem.Update ()"),
              *, message: str = "Object reference not set to an instance of an object",
              caught: bool = False) -> None:
        """Log an exception the way the engine does -- and in the log the engine would.

        Which log is decided by who CATCHES it. ``caught=True`` is one thrown under a Memoria
        ``catch (Exception err) { Log.Error(err); }`` -- all battle code, via
        ``HonoluluBattleMain.Update`` -- and lands in Memoria.log only, as timestamped ``|E|``
        lines. ``caught=False`` escaped a MonoBehaviour and lands in output_log.txt only, as an
        untimestamped block. The BYTES are a real run's, terminators included: Memoria.log is CRLF
        on every line, its |E| lines too ([ff9mapkit netsync R3] re-measured over the archived
        .harness-runs/*/Memoria.log: 233 logs, 0 bare LF; this said LF before, and :meth:`_mlog`
        writes CRLF -- one stand-in log, one terminator), and Unity ends every frame but the last
        with CR CR LF -- which a naive ``splitlines()`` reads as a blank line, so a stand-in that
        wrote plain CRLF there would pass a reader the real log breaks.
        """
        tail = " [0x00000] in <filename unknown>:0 "
        if caught:
            stamp = time.strftime("%d.%m.%Y %H:%M:%S")
            lines = [f"{stamp} |E| System.{exc}: {message}"]
            lines += [f"{stamp} |E|   at {f}{tail}" for f in frames]
            body, path = "".join(line + "\r\n" for line in lines), self.memoria_log
        else:
            trace = "\r\r\n".join(f"  at {f}{tail}" for f in frames)
            body = f"{exc}: {message}\r\n" + (trace + "\r\n" if trace else "")
            body += " \r\n(Filename:  Line: -1)\r\n\r\n"
            path = self.unity_log
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "ab") as f:
            f.write(body.encode("utf-8"))

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    # Popen-compatible surface, so Session can treat this exactly like a launched game.
    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        deadline = time.time() + (timeout or 5)
        while time.time() < deadline:
            if self.returncode is not None:
                return self.returncode
            time.sleep(0.01)
        raise TimeoutError("fake game did not exit")

    def kill(self):
        self.returncode = -9
        self.stop()

    # -- the frame loop ------------------------------------------------------------------------
    def _run(self) -> None:
        while not self._stop.is_set() and self.returncode is None:
            self._frame_once()
            if "mtime" in self.publish:
                self._pace_real_time()
            else:
                time.sleep(1.0 / self.fps)          # read each frame: a test may change the loop's pace mid-run

    def _frame_once(self) -> None:
        """One frame of the loop -- what :meth:`_run` turns, and what a test that steps the fake BY HAND calls. A
        machine beat (H10/H11) runs its frame before the publish under ``publish_order`` "agent_last" and after it under
        "agent_first" (:meth:`_step_machine`): a sample of frame f then shows its state after the ticks of frames <= f-1
        -- the engine's measured order, the agent's Update before HonoBehaviorSystem's (tickrate.py:67-69)."""
        if self.mode != "frozen":
            self.frame += 1
            self._advance_clock()
        else:
            self._hold_frame()
        try:
            self._poll_arm()
            if self.armed:
                self._poll_request()
                self._drain()
                self._check_soft_reset()
                self._step_world()
                self._step_scene()
                self._step_machine("agent_last")
                self._step_battle()
                self._step_netsync_battle()  # [ff9mapkit netsync B4/B5] the own battle's pump, the diorama's EndTick
                self._step_selftest_proof()  # [ff9mapkit netsync R3] the selftest overlay + the proof block's R3 lines
                self._service_turn()        # s90: end, or cut, an in-place turn
                self._step_netsync()        # s96: the F3.2 guest's dialogue lock (bench only)
                self._step_script_poll()    # [ff9mapkit netsync F3.3] R5: the open polled line's script button-poll
                self._step_diorama()        # [ff9mapkit netsync F3.3] DIO-1: a booted diorama's leave and return
                self._publish()
                self._step_machine("agent_first")
            else:
                self._step_diorama()        # ServiceHarnessDiorama runs armed or not: a deferred release finishes
        except OSError as err:
            # Mirrors the agent's own try/catch. Without this a single transient sharing
            # violation killed the publisher thread, and every later wait then timed out
            # pointing at the wrong half of the system -- which is exactly how a harness
            # earns a reputation for being flaky when it is actually deterministic.
            self.error = str(err)

    #: How far the real-time loop ("mtime" published) may fall behind the wall clock before it re-anchors rather than
    #: catch up: past this a stamp would read stale to the driver (Session's LIVE_WITHIN is 2 s).
    REALTIME_SLIP = 1.0

    def _pace_real_time(self) -> None:
        """Sleep until the wall clock reaches the virtual clock (``_wall0 + rt``), so each state.json stamped with its
        virtual write time is stamped at about the real moment it was written. A loop that has fallen behind (a busy
        machine) runs its frames back to back until it catches up -- their stamps stay exactly 1 / render_fps apart --
        and one more than REALTIME_SLIP behind re-anchors instead: a jump in the stamps the driver drops as a stall.
        A frozen frame advances nothing, so it just waits a frame."""
        if not self._steps and not self._dt:
            time.sleep(1.0 / self._render_fps)
            return
        ahead = self._wall0 + self.rt - time.time()
        if ahead > 0:
            time.sleep(ahead)
        elif ahead < -self.REALTIME_SLIP:
            self._wall0 -= ahead

    def _poll_arm(self) -> None:
        """Model the agent's arm gate EXACTLY, including the part that bites.

        ⚠ The real agent compares the file's existence against its own flag and returns early when
        they agree. So rewriting an existing arm file is a no-op: sequence numbers are NOT reset,
        buttons are NOT released, the error latch is NOT cleared. A driver that re-arms by writing
        the file gets an agent still carrying a dead run's counters, and every request it sends is
        discarded as stale while acking instantly. Reproducing that here is the whole point.
        """
        if self.frame - self.arm_poll_frame < ARM_POLL:
            return
        self.arm_poll_frame = self.frame
        present = (self.dir / "arm").exists()
        if present == self.armed:
            return
        self.armed = present
        self.queue.clear()
        self.held.clear()
        self.down_at.clear()
        self._turn_open, self._turn_keys = None, set()     # s90: an arm transition clears a turn silently
        if present:
            self.arm_transitions += 1
            if self.resets_on_arm:
                self.seq = -1
                self.ack = -1
                self.error_seq = -1
                self.pending_ack = False
                self.block_until = 0
                self.error = None
                self.watch = []
                self.note = ""
            # s88: arming resets the tracer to OFF, silently -- an armed run that never sends
            # `storytrace 1` writes no story.jsonl at all
            self.story_on = False
            self.story_rows = 0
            self.story_error = None
            self._event("armed", protocol=PROTOCOL)
        else:
            self._story_stop()                 # the trace is dormant unless armed
            self._release_netsync()            # the override is process-local: it dies with the run
            self._publish(force=True)          # a final document that says it stood down
            self._event("disarmed")

    def _poll_request(self) -> None:
        every = REQ_POLL_IDLE if not self.queue else REQ_POLL_BUSY
        if self.frame - self.req_poll_frame < every:
            return
        self.req_poll_frame = self.frame
        req = self.dir / "req.txt"
        if not req.exists():
            return
        try:
            lines = req.read_text(encoding="utf-8").splitlines()
        except OSError:
            return
        if not lines:
            return
        head = lines[0].split()
        if len(head) < 2 or head[0] != "seq":
            return
        try:
            seq = int(head[1])
        except ValueError:
            return
        if seq <= self.seq:
            return
        self.seq = seq
        # The FIXED agent clears the error latch per request. Without this one refusal poisons every
        # later step, and the driver blames innocent requests for it.
        self.error = None
        self.pending_ack = True
        added = 0
        for line in lines[1:]:
            tok = line.split()
            if tok and not tok[0].startswith("#"):
                self.queue.append(tok)
                added += 1
        # the agent's receipt in the event log (HarnessAgent.PollRequest): what a turn's report is ordered after
        self._event("accepted", seq=seq, steps=added)

    def _drain(self) -> None:
        while self.queue and self.frame >= self.block_until:
            step = self.queue.pop(0)
            self.executed.append(list(step))
            try:
                self._execute(step)
            except Exception as err:                       # mirrors the agent: report, never die
                self.error = f"{step[0]}: {err}"
                self.error_seq = self.seq
                # ...and log it, as HarnessAgent.DrainQueue does: the error latch holds the LAST refusal of a
                # request, the event log every one
                self._event("error", op=step[0].lower(), message=str(err))
        # Persistent latch, not a frame-local "was busy" -- see the matching comment in
        # HarnessAgent.DrainQueue. A blocking final step empties the queue one frame before the block
        # elapses, so a frame-local flag is already false by the time the ack is due.
        if self.pending_ack and not self.queue and self.frame >= self.block_until:
            self.pending_ack = False
            self.ack = self.seq
            self._event("ack", seq=self.ack)

    def _execute(self, step: list[str]) -> None:
        op, args = step[0].lower(), step[1:]

        def num(i, default=0):
            try:
                return int(args[i])
            except (IndexError, ValueError):
                return default

        def real(i, default=0.0):
            try:
                return float(args[i])
            except (IndexError, ValueError):
                return default

        if op == "wait":
            self._block(num(0, 1))
        elif op == "press":
            button = _control(args[0])
            self._claim_for_move(button)               # s90: never a step inside a turn
            self._schedule(button, max(1, num(1, 2)))
            self._block(num(1, 2) + 2)
            self._menu_step(button)
        elif op == "hold":
            button = _control(args[0])
            self._claim_for_move(button)               # s90: never a step inside a turn
            self._extend(button, max(1, num(1, 30)))
        elif op == "release":
            # ⚠ A RELEASE MUST NEVER PRESS, and it lands NEXT frame (HarnessAgent `release`): a key down now stays
            # down this frame and lifts on the next -- so `release up` then `turn up` in one request is still a
            # direction down on the turn's frame, and refused, as the agent refuses it -- a key not down now (only
            # scheduled, or never pressed) is cleared outright
            button = _control(args[0])
            if self._is_held(button):
                self.held[button] = self.frame + 1
            else:
                self.held.pop(button, None)
                self.down_at.pop(button, None)
        elif op == "turn":
            # s90's in-place turn (an engine without it: `unknown op`, like any verb it never had)
            if self.facing_mode != "published":
                raise RuntimeError(f"unknown op '{op}'")
            self._begin_turn(_turn_directions(args[0] if args else ""), min(TURN_MAX_FRAMES, max(1, num(1, 30))))
        elif op == "newgame":
            if self.ui_state != "Title":
                raise RuntimeError("newgame: not at the title screen")
            self.ui_state = "FieldHUD"
            self.field_id = 70
            self.control = True
            # H17: New Game rebuilds every player with its CharacterDefaultName (FF9Play_New, ff9play.cs:131-144): a
            # name an earlier run saved never reaches this one's [STNR] pages (the review, research/o6_design.md 11.7 #2)
            self.names = {}
            self._block(3)
        elif op == "warp":
            # H9: the agent refuses a warp off the field HUD (Ff9mkDebugMenu.Warp, HarnessAgent.cs:652-656) -- before
            # anything is written -- when `warp_field_only` models it
            if self.warp_field_only and self.ui_state != "FieldHUD":
                raise RuntimeError("warp refused (not on a field?)")
            # ServicePendingWarp writes the entrance and the scenario straight into gEventGlobal BEFORE the map
            # changes, so the trace's residue net sees them in the OLD field (`_warp_writes`); -1 writes nothing
            self._warp_writes(num(1, -1), num(2, -1))
            self.field_id = num(0, -1)
            self._guest.field_load()                    # s96: every field load re-arms the panic unlock (a reload too)
            self.ui_state = "FieldHUD"
            self.control = self.warp_arrive_control     # H9: False -- control zeroed at the field start, not given
            if self._movie is not None:
                self._end_scene("warp")        # H9: the field load destroys MBG -- the movie and the scene it was in
            self.player = [0.0, 0.0, 0.0]
            self._visit += 1                   # a new visit's actor: a turn begun before it is cut
            self._in_trigger.clear()           # a new visit: a trigger he lands in fires afresh
            self._exit = None                  # a warp outruns any exit still fading
            self._arrive_control = True
            self.climbing = False              # ...and any climb
            self._frozen_frames = self._frozen_ticks = 0      # ...and any freeze
            self._lock, self._coll = 0.0, 0.0
            self._block(3)
        elif op == "battle":
            brand = False
            if len(args) > 2 and "intro" in self._nb_caps():
                # [ff9mapkit netsync R3 s111] `battle <scene> [group] [rand|1|0]` -- parsed BEFORE the field gate (the agent
                # throws its ArgumentOutOfRangeException first); an engine before s111 ignores the third argument
                ra = args[2].lower()
                if len(args) > 3 or ra not in ("rand", "1", "0"):
                    raise RuntimeError("expected `battle <scene> [group] [rand|1|0]`, got '" + " ".join(args)
                                       + "'\r\nParameter name: battle")
                brand = ra != "0"
            if self.ui_state != "FieldHUD":
                raise RuntimeError("battle: field only")
            self.start_battle(num(0, -1), group=num(1, -1), rand=brand)
            self._block(3)
        elif op == "battlecmd":
            self._race_end(op)
            if not self.battle_active:
                raise RuntimeError("battlecmd: no battle HUD (not in a battle?)")
            self._battle_command(num(0, 0), num(1, 0), num(2, 0), num(3, 0), num(4, 0))
            self._block(2)
        elif op == "menus":
            self._race_end(op)
            if not self.battle_active:
                raise RuntimeError("menus: no battle HUD (not in a battle?)")
            self._collect_menus(num(0, -1))
        elif op == "worldwarp":
            if self.ui_state != "WorldHUD":
                raise RuntimeError("world warp: overworld only")
            self.field_id = num(0, -1)
            self.ui_state = "FieldHUD"
            self.control = True
            self._block(3)
        elif op == "teleport":
            if self.ui_state != "WorldHUD":
                raise RuntimeError("teleport: not in world mode")
            self.world["x"], self.world["z"] = real(0), real(1)
        elif op == "control":
            self.control = num(0, 1) != 0
        elif op == "flag":
            bit = num(0, -1)
            if bit < 0:
                raise RuntimeError(f"flag bit {bit} is out of range")
            self.flags[bit] = num(1, 1) != 0
            self._story_store("harness", bit >> 3, "Bit", int(self.flags[bit]), bit=bit)
        elif op == "byte":
            idx = num(0, -1)
            if not 0 <= idx < len(self.story_bytes):
                raise RuntimeError(f"byte index {idx} is out of range")
            self._story_store("harness", idx, "Byte", num(1, 0) & 0xFF)
        elif op == "storytrace":
            if self.storytrace_proto is None:          # a pre-s88 agent has no such verb
                raise RuntimeError(f"unknown op '{op}'")
            if num(0, 1) != 0:
                self._story_start()
            else:
                self._story_stop()
        elif op == "watch":
            for a in args:
                try:
                    bit = int(a)
                except ValueError:
                    continue
                if bit < 0:
                    # The FIXED agent rejects this. The unfixed one appended the key and THEN threw,
                    # leaving a truncated document and an unparseable channel for the rest of the run.
                    raise RuntimeError(f"watch bit {bit} is out of range")
                if bit not in self.watch:
                    self.watch.append(bit)
        elif op == "unwatch":
            self.watch = []
        elif op == "reset":
            self.held.clear()
            self.down_at.clear()
            self._turn_open, self._turn_keys = None, set()      # s90: cleared silently, one being judged included
            self.watch = []
            self.note = ""
            self.error = None
            self.state_every = 2
            self._release_netsync()
            self._story_stop()                 # one scenario's trace must not run on into the next
            self.no_encounter = False          # s94: reset switches the booster off again
            self._block(2)
        elif op == "noencounter":                      # s94: the F4 booster, set directly
            self.no_encounter = num(0, 1) != 0
        elif op == "timescale":
            if real(0, 1.0) <= 0.0:
                raise RuntimeError("timescale must be positive")
        elif op == "stateevery":
            self.state_every = max(1, num(0, 2))
        elif op == "shot":
            self._write_png(args[0] if args else "shot")
            self._block(2)
        elif op == "note":
            self.note = " ".join(args)
        elif op == "netsync":
            self._netsync(args)
            self._block(2)
        elif op == "quit":
            self._story_stop()                 # the trace's last rows land before the window closes
            self.returncode = 0
        else:
            raise RuntimeError(f"unknown op '{op}'")

    def _block(self, frames: int) -> None:
        self.block_until = max(self.block_until, self.frame + max(0, frames))

    def _schedule(self, button: str, frames: int) -> None:
        self.down_at[button] = self.frame + 1
        self.held[button] = self.frame + 1 + frames

    def _extend(self, button: str, frames: int) -> None:
        """Lengthen a hold in progress instead of restarting it (HarnessAgent.Extend).

        ⚠ THE ONE-FRAME HOLE THIS AVOIDS IS NOT COSMETIC. Restarting sets down_at to frame + 1, so
        on the frame the second hold arrives the button reads UP -- invisible to anything sampling
        it, fatal to anything counting unbroken held time. In the real engine that is
        BattleHUD._runCounter, and a flee re-issued every 0.8s therefore never rolled once.
        """
        if self._is_held(button):
            self.held[button] = max(self.held[button], self.frame + frames)
        else:
            self._schedule(button, frames)

    # -- the simulated world -------------------------------------------------------------------
    def _is_held(self, button: str) -> bool:
        return self.down_at.get(button, 1 << 30) <= self.frame < self.held.get(button, -1)

    def _step_world(self) -> None:
        """Move the character for one frame, so the driver's closed-loop verbs actually close.

        The basis is deliberately NOT the identity in every mode: FF9 fields are viewed by a yawed
        camera and movement is expressed in screen space, which is why `calibrate_axes` exists at
        all. A stand-in that always mapped "up" to +z would let a broken calibration pass.
        """
        if self._exit is not None and self.frame >= self._exit[0] and self._exit_open():
            self._step_exit_now()
        if self._exit is None:
            self._walkout = None                # H16: the exit landed, or a warp outran it: no walk-out is left
        self._pos_before = list(self.player)
        self._plan, visit = None, self._visit
        for ticks in self._frame_steps():       # the frame's field ticks: one share (mean) or each whole one
            self._tick = ticks
            self._coll = max(0.0, self._coll - ticks)       # ProcessEvents counts SCollTimer down every tick
            if self.ui_state != "FieldHUD":
                continue
            self._step_walkers(ticks)
            if self.climbing and self._visit == visit:
                self._step_ladder(ticks)        # the climb runs with control OFF: before the skip below
            if self._walkout is not None and self._visit == visit:
                self._step_walkout(ticks)       # H16: ExitField's walk-out runs with control OFF, until the switch
            if not self.control or self._visit != visit:
                continue                        # control gone, or a warp mid-frame: no tick of it moves him there
            self._step_player()
            if self.control:
                self._fire_contacts()           # CollisionRequest: every tick he has control, moving or not
        if self._plan is None and self.ui_state == "FieldHUD" and self.control:
            self._player_plan()                 # a frame no tick ran on still reads the pad: a coast frame is spent
        if self.ui_state == "WorldHUD" and self.overworld is not None:
            self._step_overworld()

    def _step_overworld(self) -> None:
        """One frame on foot on the overworld (see ``overworld``): the bumpers turn the camera, "up" walks
        the actor along it once his own yaw has eased on, ground that is ``blocked`` stops him, and his
        height follows ``height`` -- published, like the engine, as player.* = world x 256."""
        import math
        ow = self.overworld
        if self.world["x"] is None:
            return
        turn = float(ow.get("turn", 2.8125))
        if self._is_held("leftbumper") or self._is_held("l1"):
            ow["cam"] = (ow.get("cam", 0.0) + turn) % 360.0
        if self._is_held("rightbumper") or self._is_held("r1"):
            ow["cam"] = (ow.get("cam", 0.0) - turn) % 360.0
        x, z = self.world["x"], self.world["z"]
        if self._is_held("up"):
            cam = ow.get("cam", 0.0)
            if self._ow_yaw is None:
                self._ow_yaw = cam
            lag = max(1, int(ow.get("lag", 3)))
            d = (cam - self._ow_yaw + 180.0) % 360.0 - 180.0
            self._ow_yaw = (self._ow_yaw + d / lag) % 360.0 if abs(d) > 0.01 else cam
            sp = float(ow.get("speed", 1.0))
            nx = (x + sp * math.cos(math.radians(self._ow_yaw))) % 1536.0
            nz = z + sp * math.sin(math.radians(self._ow_yaw))
            blocked = ow.get("blocked")
            if blocked is None or not blocked(nx, nz):
                x, z = nx, nz
                self.world["x"], self.world["z"] = x, z
                height = ow.get("height")
                self._ow_y = float(height(x, z)) if height is not None else 0.0
        y = getattr(self, "_ow_y", 0.0)
        self.player = [x * 256.0, y * 256.0, z * 256.0]

    def _step_ladder(self, ticks: float) -> None:
        """One field tick (or, in mean mode, the frame's share of one) of the `ladder` climb: ``step`` up a tick while
        Up or Left is held, down while Down or Right is (both ways at once: nowhere); past ``top`` the climb is over,
        `climbed`, with control still off; past ``bottom`` it is over with control back."""
        lad = self.ladder
        if lad is None:
            self.climbing = False
            return
        way = ((1 if self._is_held("up") or self._is_held("left") else 0)
               - (1 if self._is_held("down") or self._is_held("right") else 0))
        if not way:
            return
        top, bottom = float(lad["top"]), float(lad["bottom"])
        up = 1.0 if top > bottom else -1.0                 # the sign of a step toward the top in published y
        self.player[1] += way * up * float(lad["step"]) * ticks
        if (self.player[1] - top) * up > 0:
            self.climbing, self.climbed = False, True
        elif (bottom - self.player[1]) * up > 0:
            self.climbing, self.control = False, True

    def _exit_open(self) -> bool:
        """H16's gate: whether a due exit may switch the field now -- always, unless a test holds `exit_gate` unset."""
        return self.exit_gate is None or self.exit_gate.is_set()

    def _walkout_of(self, r: dict) -> dict | None:
        """H16 (research/o6_design.md 3.1): a firing region's ``walkout``, read STRICT and armed from where he stands --
        or None without the key (today's ExitField: he stands where it took him)."""
        w = r.get("walkout")
        if w is None:
            return None
        if not isinstance(w, dict) or "to" not in w or not set(w) <= {"to", "speed", "stop_z"}:
            raise ValueError(f"a region's walkout is {{'to': [x, z], 'speed': u, 'stop_z': z | None}}, not {w!r}")
        tx, tz = (float(v) for v in w["to"])
        stop = None if w.get("stop_z") is None else float(w["stop_z"])
        way = 1.0 if tz >= self.player[2] else -1.0        # the sign of his z along the walk-out
        return {"to": (tx, tz), "speed": float(w.get("speed", 60.0)), "stop_z": stop, "way": way,
                "done": stop is not None and (self.player[2] - stop) * way >= 0}

    def _step_walkout(self, ticks: float) -> None:
        """H16: one field tick (in mean mode, the frame's share of one) of ExitField's walk-out -- MOVJ toward ``to`` at
        ``speed`` a tick (DoEventCode.cs:860-869; EventEngine.MoveToward.cs:15-30, :166), control off -- held at ``to``,
        or where his z passes ``stop_z`` (pathing holding his centre a radius short of the floor's end:
        research/o6_design.md 0.2 #6, an ESTIMATE the game measures)."""
        w = self._walkout
        if w["done"]:
            return
        x, z = self.player[0], self.player[2]
        (tx, tz), step = w["to"], w["speed"] * ticks
        d = math.hypot(tx - x, tz - z)
        nx, nz = (tx, tz) if d <= step else (x + (tx - x) / d * step, z + (tz - z) / d * step)
        w["done"] = d <= step
        stop = w["stop_z"]
        if stop is not None and (nz - stop) * w["way"] >= 0:
            t = (stop - z) / (nz - z) if nz != z else 1.0
            nx, nz, w["done"] = x + (nx - x) * t, stop, True
        self.player[0], self.player[2] = nx, nz

    def _player_plan(self) -> tuple:
        """What the controlled player does THIS FRAME, read once from the pad (IsHeld keys on the frame: every tick in
        it sees the same keys) -- ``("frozen",)``, ``("turn", ux, uz, calls a tick)`` (an s90 turn's keys, no axis),
        ``("idle",)``, ``("coast", dx, dz, calls a tick)`` (the last press still applied: its frame consumed here, once,
        however many ticks it holds), or ``("press", ux, uz, calls a tick)``: ``ux``/``uz`` the unit press after the
        twist, ``dx``/``dz`` the direction a step actually took (after the wall-slide projection)."""
        if self._frozen():
            self._coast = None                  # MovePC returns before it moves anyone
            return ("frozen",)
        vx = vz = 0.0
        if self._move_held("up"):
            vz += 1.0
        if self._move_held("down"):
            vz -= 1.0
        if self._move_held("right"):
            vx += 1.0
        if self._move_held("left"):
            vx -= 1.0
        gait = CALLS_PER_TICK["walk" if self._is_held("cancel") or self.dash_inhibit else "run"]
        if vx == 0.0 and vz == 0.0:
            turn = self._turn_keys_direction()
            if turn is not None:
                self._coast = None              # the keys' own sample replaces the last movement's
                self._facing = turn
                return ("turn", turn[0], turn[1], gait)     # s90: the keys of a `turn`, no axis -- he turns in place
            if not self._coast:
                return ("idle",)
            # Nothing held -- but the engine is still applying the last movement it sampled.
            dx, dz, c, left = self._coast
            self._coast = (dx, dz, c, left - 1) if left > 1 else None
            return ("coast", dx, dz, c)
        mag = (vx * vx + vz * vz) ** 0.5
        return ("press", *self._twisted(vx / mag, vz / mag), gait)

    def _twisted(self, vx: float, vz: float) -> tuple[float, float]:
        """A screen-space press as the world direction it moves him (`twist`)."""
        if not self.twist:
            return vx, vz
        a = math.radians(self.twist)
        return vx * math.cos(a) - vz * math.sin(a), vx * math.sin(a) + vz * math.cos(a)

    def _step_player(self) -> None:
        """The tick being run (`_tick`: one field tick, or in mean mode the frame's share of one -- so at the defaults
        this is once a frame) of the controlled player, on the frame's plan (`_plan`, read from the pad at the frame's
        first: :meth:`_player_plan`): the pad, the push-out, the floor, the regions. A tick's step is its MovePC calls
        x 30u -- one call walking, two running (FieldMapActorController.cs:198-209 at stock 6b8bb2d5) -- so at the
        defaults (60 fps, mean) a run frame steps 30u in one call and a walked frame 15u in half of one."""
        from ff9mapkit.content import doorface
        if self._plan is None:
            self._plan = self._player_plan()   # the pad, read once: every tick of a frame sees the same keys
        plan, ticks = self._plan, self._tick
        kind = plan[0]
        if kind == "frozen":
            self._retest_gated()
            return
        if kind == "idle":
            self._lock_fallback(ticks * CALLS_PER_TICK["walk"])   # MovePC still runs, once a tick
            self._retest_gated()
            return
        if kind == "turn":
            self._turn_in_place(plan[1], plan[2], ticks * plan[3])
            return
        if kind == "coast":
            _k, dx, dz, c = plan
            step = ticks * c * doorface.STEP_PER_CALL
            vx, vz = dx * step, dz * step
            calls = doorface.movepc_calls((vx * vx + vz * vz) ** 0.5)
            self._turn(vx, vz, calls)           # the coast is the press still being applied: it turns him too
            self._move_to(self.player[0] + vx, self.player[2] + vz, calls)
            self._enter_regions()
            self._enter_freezes()
            return
        _k, vx, vz, c = plan
        speed = ticks * c * doorface.STEP_PER_CALL
        calls = doorface.movepc_calls(speed)    # the MovePC calls this tick's step is worth (30u each)
        # the turn comes first, as in MovePC: the press turns him whether or not the step then moves him
        self._turn(vx, vz, calls)

        if self.mode == "wall_slide":
            # Every press is projected onto one fixed wall direction. The character always MOVES --
            # which is why a "did it move at all" probe cannot detect this -- but never where he was
            # sent. A basis measured here is a well-formed lie.
            wall = (0.7071, 0.7071)
            along = vx * wall[0] + vz * wall[1]
            vx, vz = wall[0] * along, wall[1] * along
            if vx == 0.0 and vz == 0.0:
                return

        moved = self._move_to(self.player[0] + vx * speed, self.player[2] + vz * speed, calls)
        # Arm the tail with the direction and gait actually applied this tick.
        coast = self._coast_frames()
        self._coast = (vx, vz, c, coast) if coast > 0 and moved else None

        if self.gateway is not None:
            gx0, gz0, gx1, gz1, dest = self.gateway
            if gx0 <= self.player[0] <= gx1 and gz0 <= self.player[2] <= gz1:
                self.field_id = dest
                self.player = [0.0, 0.0, 0.0]
                self.control = True
        self._enter_regions()
        self._enter_freezes()

    @property
    def _frozen_until(self) -> float:
        """A hold on movement in FRAMES, as a test lays one by hand (movement held while ``frame`` is below it)."""
        return self._frozen_frames

    @_frozen_until.setter
    def _frozen_until(self, frame: float) -> None:
        """Lay -- or, with a frame already past, lift -- a hold in frames; it REPLACES every hold, a zone's tick-counted
        freeze included (a test that lifts "the" hold lifts it, whichever kind the walk stepped on)."""
        self._frozen_frames, self._frozen_ticks = frame, 0

    def _frozen(self) -> bool:
        """Whether movement is held this frame: a zone's freeze still counting its ticks, or a hold a test laid on in
        frames."""
        return self.frame < self._frozen_frames or self.ticks_run < self._frozen_ticks

    def _coast_frames(self) -> int:
        """`coast_frames` as set, or -- None -- one frame at the calibrated model (60 fps, mean ticks) and none off it
        (see `coast_frames`)."""
        if self.coast_frames is not None:
            return int(self.coast_frames)
        return 1 if self._render_fps == 60.0 and self._tick_mode == "mean" else 0

    def _move_held(self, button: str) -> bool:
        """A direction held to MOVE: down, and not a ``turn`` key (HarnessAgent.MoveHeld: a turn key feeds no
        axis)."""
        return self._is_held(button) and button not in self._turn_keys

    def _turn_keys_direction(self) -> tuple[float, float] | None:
        """The world direction the s90 ``turn`` keys down this frame compose (after the twist) -- MovePC's key branch
        builds the 8-way target from them (FieldMapActorController.cs:698-708) -- or None when no turn key is down (or
        they cancel: refused at the start, never composed here)."""
        keys = [b for b in self._turn_keys if self._is_held(b)]
        if not keys:
            return None
        vx = (1.0 if "right" in keys else 0.0) - (1.0 if "left" in keys else 0.0)
        vz = (1.0 if "up" in keys else 0.0) - (1.0 if "down" in keys else 0.0)
        if vx == 0.0 and vz == 0.0:
            return None
        mag = (vx * vx + vz * vz) ** 0.5
        return self._twisted(vx / mag, vz / mag)

    def _turn_in_place(self, vx: float, vz: float, calls: float) -> None:
        """A tick of an s90 ``turn`` whose keys are down (and no other direction: the agent refuses both ways) toward
        world direction (``vx``, ``vz``): the stick-threshold test zeroes the step because the axis is under threshold
        (FieldMapActorController.cs:736-737), and the facing lerp (:749-764) keys on the booleans -- so `_face_deg`
        turns by the tick's MovePC calls (``calls``; `turn_calls` a frame when set) and he takes no step. The zero step
        still runs the push-outs a step would (:meth:`_move_to` to where he stands: a body he overlaps, or a wall nearer
        than his radius, moves him -- what ``turn_end``'s ``moved`` witnesses), and the region he stands in is
        re-tested, a gated door he now faces firing (:meth:`_retest_gated`)."""
        if self.turn_calls is not None:
            calls = self.turn_calls
        self._turn(vx, vz, calls)
        before = (self.player[0], self.player[2])
        self._move_to(before[0], before[1], calls)
        if (self.player[0], self.player[2]) != before:
            self._enter_regions()               # pushed: a step's rule
        else:
            self._retest_gated()                # standing: the gated region's every-tick re-test

    def _turn(self, vx: float, vz: float, calls: float) -> None:
        """His yaw (`_face_deg`) after a frame that held world direction (``vx``, ``vz``) -- the press after the
        twist, as MovePC's ``moveVec`` -- for ``calls`` MovePC calls (the frame's average): content.doorface.turn_step
        toward ``yaw_of(vx, vz)``; under `tick_phase`, the tick's whole calls on a tick frame and none between.
        Called on every frame a direction is applied, BEFORE the step: whatever the walls or a body then do to his
        position, the yaw has turned (FieldMapActorController.cs:744-761 precede the collision at :762, at stock)."""
        from ff9mapkit.content import doorface
        if self.tick_phase is not None:
            if self.frame % 2 != self.tick_phase:
                return                          # no tick this frame: MovePC does not run
            calls = round(2 * calls)            # the tick's whole calls: a walked frame's 1, a run frame's 2
        self._face_deg = doorface.turn_step(self._face_deg, doorface.yaw_of(vx, vz), calls)

    def _move_to(self, x: float, z: float, calls: float = 1.0) -> bool:
        """One frame's step to (x, z), worth ``calls`` MovePC calls: kept on the floor (`walkmesh`), and --
        while sLockTimer is not negative -- pushed out of a body it enters that is in front of him (see
        `blockers`), refused (False, he stays put) when the push-out lands in another. Then the lock's
        count for the frame (CheckCollFallback). Only a body that collides is met: ``coll``, and within
        400 of him in y (WalkMesh.Collision's pair rule and its |dy| band).

        H20 (research/o7_design.md 3.1), OPT-IN: on a field with an entry in `levels` the floor is HIS LEVEL of a
        stacked walkmesh -- the clearance rule below, its walls his level's (:meth:`Levels.wall_gap`) and its floor the
        open triangle under him within a step of his height (:meth:`Levels.tri_under`, his height ``-player[1]``) --
        and his height is published after the step (``player[1]``, minus the height there); `clearance` is required.
        H21 (3.2): with the level's ``squeeze_slack``, a PINCH -- a corridor with no point across it at `clearance` --
        is passed down to ``clearance - squeeze_slack`` (:meth:`Levels.squeeze`), where the engine's opposing pushes
        average out at its midline. H26 (research/o8_design.md 3.1), OPT-IN: every rule here reads THIS field's
        clearance (:meth:`_clearance`, read once a step): `clearances`' entry for the field, else `clearance`."""
        ox, oz = self.player[0], self.player[2]
        ax, az = x - ox, z - oz                     # the step as pressed (H21's refused step reads it)
        if (x, z) != (ox, oz):
            m = ((x - ox) ** 2 + (z - oz) ** 2) ** 0.5
            self._facing = ((x - ox) / m, (z - oz) / m)
        bodies = [(d["x"], d["z"], d["r"], bool(d.get("solid")), i) for i, d in self._bodies()
                  if d.get("coll", True) and abs(float(d.get("y", 0.0)) - self.player[1]) < 400]
        pushed = False
        for b in bodies:
            bx, bz, r = b[0], b[1], b[2]
            d = ((x - bx) ** 2 + (z - bz) ** 2) ** 0.5
            if d >= r:
                continue
            self.contacts.append({"frame": self.frame, "uid": self._uid(b[4])})
            self._lock_free = 0 if b[3] else 1
            if not self._lock_free:
                self._lock = 0.0
            # facing = the step (the engine lerps toward it); the push-out wants the body within +-90 deg
            if self._lock >= 0 and (x - ox) * (bx - x) + (z - oz) * (bz - z) >= 0:
                if d < 1e-6:
                    self._lock_fallback(calls)
                    return False
                x, z = bx + (x - bx) / d * r, bz + (z - bz) / d * r
                self._coll = COLL_TICKS
                pushed = True
            break                                   # WalkMesh.Collision answers with ONE body
        on = getattr(self.walkmesh, "point_on_walkmesh", None)
        lv = self.levels.get(self.field_id)         # H20 (opt-in): his level of a stacked walkmesh
        clearance = self._clearance()               # H26 (opt-in): THIS field's radius, else the one value
        h = None
        if lv is not None and clearance is None:
            raise ValueError(f"fake.levels[{self.field_id}]: a level is walked at the controller's radius -- set "
                             f"fake.clearance (Steiner's: 120) or fake.clearances[{self.field_id}]")
        if lv is not None or (on is not None and clearance is not None):
            # his centre kept `clearance` off every wall -- pushed out onto that line where he stands closer (placed
            # there), or, where no push lands him on it, never closer still: the step stops on that line, and its
            # rest slides on along the wall
            if lv is not None:
                h = -float(self.player[1])          # his height (PSX y, up negative): f[1] = -pos[1]

                def wall(px, pz):
                    d = lv.wall_gap(px, pz, h)
                    return -1.0 if d is None else d
            else:
                def wall(px, pz):
                    d = self.walkmesh.distance_to_boundary(int(round(px)), int(round(pz)))
                    return -1.0 if d is None or on(int(round(px)), int(round(pz))) is None else d
            squeeze = lv is not None and lv.squeeze_slack is not None     # H21 (opt-in)
            squeezed = False
            least = max(0.0, min(clearance, wall(ox, oz)))          # off the mesh (an arrival): onto it

            def floor(px, pz):
                return wall(px, pz) >= least
            if not floor(x, z):
                ex, ez = x, z                       # H21: the step's own end
                lo, hi = 0.0, 1.0
                for _ in range(16):
                    mid = (lo + hi) / 2
                    lo, hi = (mid, hi) if floor(ox + (x - ox) * mid, oz + (z - oz) * mid) else (lo, mid)
                bx, bz = ox + (x - ox) * lo, oz + (z - oz) * lo
                # the rest of the step, slid along the wall: its component along the nearest bearing (15-degree
                # steps either side) that still stands -- the engine keeps the part of a step along the wall
                import math
                rx, rz = x - bx, z - bz
                x, z = bx, bz
                slid = False
                for deg in (15, 30, 45, 60, 75):
                    c = math.cos(math.radians(deg))
                    for s in (math.sin(math.radians(deg)), -math.sin(math.radians(deg))):
                        px, pz = bx + (rx * c - rz * s) * c, bz + (rx * s + rz * c) * c
                        if floor(px, pz):
                            x, z = px, pz
                            slid = True
                            break
                    else:
                        continue
                    break
                if squeeze and not slid:
                    # H21: neither the never-closer rule nor a slide stands -- in a PINCH (no point across the step's
                    # end at full clearance) the opposing pushes average out at its midline: placed there when the
                    # pinch is no narrower than clearance - squeeze_slack a side; else he stops, as ever
                    got = lv.squeeze(ex, ez, ex - ox, ez - oz, h, clearance)
                    if got is not None:
                        x, z = got
                        squeezed = True
            if not squeezed and 0.0 <= wall(ox, oz) < clearance and 0.0 <= wall(x, z) < clearance:
                got = lv.squeeze(x, z, x - ox, z - oz, h, clearance) if squeeze else None
                if got is not None:
                    # H21: inside a pinch his place is its midline, where the pushes balance -- never pushed back out
                    # of it along the corridor to a spot at full clearance
                    x, z = got
                else:
                    # placed nearer a wall than his radius (a scene's own spot): where the step ends -- kept on the
                    # floor above, as the engine's triangle walk keeps it -- is pushed straight out onto the radius
                    # line, as the engine pushes it on his first moving frame
                    got = self._pushed_out(x, z, wall)
                    if (squeeze and got is not None and (got[0] - ox) * ax + (got[1] - oz) * az < 0
                            and lv.squeeze(ox, oz, ax, az, h, clearance) is not None):
                        # H21 at a pinch NARROWER than its bound (research/o8_design.md 11.4 PART B, #1): standing on a
                        # pinch's midline (he fits where he stands), a step that no squeeze places further in is pushed
                        # out BEHIND where it started, against the press -- back out of the pinch along the corridor,
                        # then squeezed in again on the next press: a jitter at its mouth, never a stop. The engine
                        # refuses that step (IsRadiusValid fails; a pushed position across a wall is rejected:
                        # FieldMapActorController.cs:975-993, 1188-1254): he stays where he stands -- he stops, as
                        # Levels.squeeze says
                        got = (ox, oz)
                    x, z = got or (x, z)
        elif on is not None:
            # a real walkmesh: his centre must stand on it -- a step off keeps whichever one axis of it
            # still does (a crude slide along the edge), or he stays put
            def floor(px, pz):
                return on(int(round(px)), int(round(pz))) is not None
            if not floor(x, z):
                x, z = next(((px, pz) for px, pz in ((x, oz), (ox, z)) if floor(px, pz)), (ox, oz))
        else:
            boxes = self.walkmesh if isinstance(self.walkmesh[0], (tuple, list)) else [self.walkmesh]
            if not any(b[0] <= x <= b[2] and b[1] <= z <= b[3] for b in boxes):
                x0, z0, x1, z1 = next((b for b in boxes if b[0] <= ox <= b[2] and b[1] <= oz <= b[3]), boxes[0])
                x, z = min(max(x, x0), x1), min(max(z, z0), z1)
        if pushed and any((x - b[0]) ** 2 + (z - b[1]) ** 2 < (b[2] - 1e-6) ** 2 for b in bodies):
            self._lock_fallback(calls)
            return False
        self.player[0], self.player[2] = x, z
        if lv is not None:                          # H20: his height where the step left him, on his level
            ti = lv.tri_under(x, z, h)
            if ti is not None:
                self.player[1] = -lv.height(ti, x, z)
        self._lock_fallback(calls)
        return True

    def place_height(self, x: float, z: float, h: float) -> None:
        """H20 (research/o7_design.md 3.1): a scripted placement's HEIGHT -- ``h`` the PSX y operand of the bytes'
        MoveInstantXZY (up negative; 154 e15 t0 ip2827's ``Map.Int16[2]``, -1741). With a level entry for this field
        ``player[1]`` is minus the height of the open triangle under (x, z) nearest ``h`` -- no step bound: a placement
        lands on the nearest-height triangle (GetTriIdxAtPos, FieldMapActorController.cs:1279-1306) -- else (no entry,
        or no open triangle under (x, z)) minus ``h``. His x and z are the caller's."""
        lv = self.levels.get(self.field_id)
        ti = None if lv is None else lv.tri_nearest(x, z, h)
        self.player[1] = -float(h) if ti is None else -lv.height(ti, x, z)

    def _clearance(self) -> float | None:
        """H26 (research/o8_design.md 3.1): the engine radius his centre keeps off a wall in THIS field -- the field's
        entry in ``clearances``, else ``clearance`` (today's one value). 164's Steiner is radius 80 (DoEventCode.cs:
        1507-1508, through EffectiveFieldId), 165's 120."""
        return self.clearances.get(self.field_id, self.clearance)

    def _pushed_out(self, x: float, z: float, wall):
        """Where the engine's push off the walls puts a centre standing nearer one than his radius: straight away from
        it, onto the radius line (FieldMapActorController.RadiusValid -> ServiceForces: one force lands it exactly
        there, several are averaged). Modelled as the move to ``clearance`` off every wall along whichever of 64
        bearings stands it furthest off them, over floor all the way -- again from there while a second wall holds
        it (a corner: 352's pocket between strip and back wall takes five). None when no bearing gets further out:
        the caller keeps its never-closer-still rule. H26 (research/o8_design.md 3.1): THIS field's clearance
        (:meth:`_clearance`)."""
        import math
        clearance = self._clearance()
        for _ in range(16):                         # each round nearer the line, or it gives up
            d = wall(x, z)
            if d >= clearance:
                return x, z
            r = clearance - d + 0.5
            best = None
            for k in range(64):
                ux, uz = math.cos(k * math.pi / 32), math.sin(k * math.pi / 32)
                if any(wall(x + ux * r * s / 8, z + uz * r * s / 8) < 0 for s in range(1, 9)):
                    continue                            # off the floor on the way: not a push he gets
                there = wall(x + ux * r, z + uz * r)
                if best is None or there > best[0]:
                    best = (there, x + ux * r, z + uz * r)
            if best is None or best[0] <= d:
                return None
            x, z = best[1], best[2]
        return (x, z) if wall(x, z) >= clearance else None

    def _lock_fallback(self, calls: float) -> None:
        """FieldMapActorController.CheckCollFallback, ``calls`` times over: while SCollTimer runs, count
        sLockTimer up by sLockFree -- flipping it to -25 at 25, which turns the push-out off -- else
        reset a non-negative count to 0 and count a negative one back up to it. WHOLE calls (a quantized run tick's
        two) are counted one at a time, as the engine calls it once a MovePC -- so the flip at 25 lands on the call
        that reaches it; a mean frame's share of a call (half a call a walked frame at 60 fps) is counted at once."""
        n = round(calls)
        if n > 1 and abs(calls - n) < 1e-9:
            for _ in range(n):
                self._lock_call(1.0)
        else:
            self._lock_call(calls)

    def _lock_call(self, calls: float) -> None:
        """One CheckCollFallback, worth ``calls`` MovePC calls (see :meth:`_lock_fallback`)."""
        if self._coll > 0:
            self._lock = -25.0 if self._lock >= 25 else self._lock + self._lock_free * calls
        elif self._lock >= 0:
            self._lock = 0.0
        else:
            self._lock = min(0.0, self._lock + calls)

    # -- the field's other actors (s89) ---------------------------------------------------------
    def _bodies(self) -> list:
        """This field's `blockers` as ``(index, dict)`` -- a tuple is ``(x, z, r[, solid])``."""
        out = []
        for i, b in enumerate(self.blockers.get(self.field_id, ())):
            if not isinstance(b, dict):
                b = {"x": b[0], "z": b[1], "r": b[2], "solid": len(b) > 3 and bool(b[3])}
            out.append((i, b))
        return out

    def _uid(self, i: int) -> int:
        b = self.blockers.get(self.field_id, ())[i]
        return int(b.get("uid", 128 + i)) if isinstance(b, dict) else 128 + i

    @staticmethod
    def _walking(b: dict) -> bool:
        return bool(b.get("path")) and float(b.get("speed", 0)) > 0 and not b.get("_done")

    def _step_walkers(self, ticks: float) -> None:
        """Every walker (a body with a ``path``) one tick along it (or, in mean mode, the frame's share of one:
        ``ticks``) -- ``speed / WALKER_FRAME_TICKS`` units a tick, MoveToward's step a tick -- unless that step would
        bring it within ``r`` of the player, where it waits, still moving (MoveToward.cs:187-189).

        H23 (research/o7_design.md 3.4), opt-in: a walker's ``hold`` -- ``{"within": r, "latch_below": y1,
        "unlatch_above": y2, "at": [k, ...]}`` -- keeps it standing at a path index in ``at`` (its placement is index
        0) while his XZ distance is under ``within`` OR its latch is set (154 e5 t1 ip263 / ip486: ``B_DISTANCEA < 3600
        || Map.Byte[30] == 1``). The latch sets the first tick his published y is under ``latch_below`` (e11 t1 ip14 /
        ip33: ``f[1] > -600``) and then clears once it is over ``unlatch_above`` (ip128 / ip147: ``f[1] < -500``) --
        each tick, in that order; it starts clear (e15 t0 ip2116 ``Map.Byte[30] := 2``). Held, it stands -- its script
        waits in ip263's loop, no walk runs: ``objects`` publishes it ``moving`` False. Elsewhere on its path it walks
        without a wait (e5 t1 ip316-ip474).

        H25 (research/o8_design.md 3.2), opt-in: THE KNIGHT -- a walker carrying ``start`` or ``store`` (read STRICT on
        its first step: :func:`_walker_knobs`). ``start``, exactly one of ``{"y_ge": h}`` / ``{"y_gt": h}`` /
        ``{"y_le": h}`` / ``{"y_lt": h}`` on his PUBLISHED y (``player[1]``), holds it at its placement (``_held``:
        ``objects`` publishes it ``moving`` False) until the first tick it holds, when it walks -- and it is LATCHED,
        never held by it again (164 e1 t1 ip178 ``obj(uid=250).f[1] > -8400`` looped by ip187's JMP_IF, released at y >=
        8400). ``store``, ``{"after_ticks": n, "args": [sid, tag, ip, byte, width, new, bit]}``: once its ``once`` path's
        last index is reached, ``n`` field ticks later :meth:`script_store` is called ONCE (``_stored``: 164 e1 t1
        ip221-ip230, the stand anim and RunAnimation(9920), then ``Bit[3811] := 1``) -- the countdown runs before the
        walking skip (a done walker still counts), and it lives on the BODY: a visit that ends first takes its bodies
        with it (:meth:`_VisitBeat.end`) and the store never comes. And such a body is "held by him" only at |its y - his
        published y| < 400 (WalkMesh.Collision's pair band, WalkMesh.cs:919-921: the knight on loop 2 never pairs with
        Steiner on loop 1); every other walker keeps the XZ-only rule. H25b (the review's #2), opt-in: a path whose
        points carry a third coordinate -- the walker's LEVEL there, read off the mesh -- moves its ``y`` with its x
        and z, linearly along each leg (the knight climbs loop 2 from his placement's 11255 to his seat's 11896), so
        the pair band and ``objects`` read the level it stands on; a two-coordinate path keeps ``y`` as given."""
        for _i, b in self._bodies():
            h25 = b.get("start") is not None or b.get("store") is not None
            if h25:                                        # H25: read strict once, then the store's countdown
                if "_h25" not in b:
                    _walker_knobs(b)
                    b["_h25"] = True
                store = b.get("store")
                if store is not None and b.get("_done") and not b.get("_stored"):
                    b["_left"] = b.get("_left", float(store["after_ticks"])) - ticks
                    if b["_left"] <= 1e-9:
                        b["_stored"] = True
                        args = store["args"]
                        self.script_store(int(args[0]), int(args[1]), int(args[2]), int(args[3]), str(args[4]),
                                          int(args[5]), bit=int(args[6]))
            if not self._walking(b):
                continue
            start = b.get("start")
            if start is not None and not b.get("_started"):          # H25: held at its placement until released
                (term, h), = start.items()
                y = self.player[1]
                if y is None or not _WALKER_TESTS[term](float(y), float(h)):
                    b["_held"] = True
                    continue
                b["_started"], b["_held"] = True, False      # LATCHED: never held by it again
            hold = b.get("hold")
            if hold is not None:                           # H23: the latch, then the hold at its stops
                y = self.player[1]
                if not b.get("_latch") and y < float(hold["latch_below"]):
                    b["_latch"] = True
                if b.get("_latch") and y > float(hold["unlatch_above"]):
                    b["_latch"] = False
                b["_held"] = b.setdefault("_at", 0) in hold["at"] and bool(
                    b.get("_latch") or math.hypot(b["x"] - self.player[0], b["z"] - self.player[2])
                    < float(hold["within"]))
                if b["_held"]:
                    continue                               # held at its stop: its script waits, no walk runs
            path = b["path"]
            k = b.setdefault("_k", 1 if len(path) > 1 else 0)
            tx, tz = path[k][0], path[k][1]
            dx, dz = tx - b["x"], tz - b["z"]
            dist = (dx * dx + dz * dz) ** 0.5
            step = min(float(b["speed"]) * (ticks / WALKER_FRAME_TICKS), dist)
            nx, nz = (b["x"] + dx / dist * step, b["z"] + dz / dist * step) if dist > 0 else (tx, tz)
            px, pz = self.player[0], self.player[2]
            near = ((nx - px) ** 2 + (nz - pz) ** 2) ** 0.5
            paired = not h25 or (self.player[1] is not None
                                 and abs(float(b.get("y", 0.0)) - float(self.player[1])) < 400)    # H25: the pair band
            if paired and near < b["r"] and near < ((b["x"] - px) ** 2 + (b["z"] - pz) ** 2) ** 0.5:
                continue                                   # held by him
            b["x"], b["z"] = nx, nz
            if len(path[k]) > 2:                           # H25b: its level moves with it, linearly along the leg
                ty = float(path[k][2])
                y0 = float(b.get("y", ty))
                b["y"] = ty if step >= dist else y0 + (ty - y0) * step / dist
            if hold is not None:
                b["_at"] = k if step >= dist else None     # H23: the stop it stands at, None between two
            if step < dist:
                continue
            if len(path) < 2 or (b.get("once") and k == len(path) - 1):
                b["_done"] = True
                continue
            way = b.setdefault("_way", 1)
            if not 0 <= k + way < len(path):
                way = b["_way"] = -way
            b["_k"] = k + way

    def _fire_contacts(self) -> None:
        """CollisionRequest, modelled for the triggers it can fire: his centre inside a body's ``range_r`` (the
        mode-2 search: the pair rule, so only while ``coll``; |dy| < 400), or -- for an entry with both
        functions -- inside ``talk_r`` while he faces it (+-90 degrees). Logged once per entry into the radius
        (`touched`); a ``"to"`` makes it an ExitField, control taken now and the field changed a fade later."""
        px, pz = self.player[0], self.player[2]
        for i, b in self._bodies():
            rr, tr = b.get("range_r"), b.get("talk_r")
            if rr is None or abs(float(b.get("y", 0.0)) - self.player[1]) >= 400:
                continue
            dx, dz = b["x"] - px, b["z"] - pz
            dist = (dx * dx + dz * dz) ** 0.5
            kind = "range" if b.get("coll", True) and dist < rr else None
            if kind is None and tr is not None and dist < tr and dx * self._facing[0] + dz * self._facing[1] > 0:
                kind = "talk"
            key = (self.field_id, i)
            if kind is None:
                self._in_trigger.discard(key)
                continue
            if key in self._in_trigger:
                continue
            self._in_trigger.add(key)
            self.touched.append({"frame": self.frame, "field": self.field_id, "uid": self._uid(i), "kind": kind,
                                 "executed": len(self.executed)})
            if b.get("to") is not None and self._exit is None:
                self.control = False
                self._coast = None
                self._exit = (self.frame + self.exit_frames, int(b["to"]), tuple(b.get("arrive", (0, 0))))
                self._arrive_control = True
                if self.exit_frames <= 0:
                    self._step_exit_now()
                return

    def _objects_doc(self) -> list:
        """``objects`` as the s89 agent publishes it, for this field's bodies."""
        out = []
        for i, b in self._bodies():
            coll = bool(b.get("coll", True))
            rr, tr = b.get("range_r"), b.get("talk_r")
            shown = bool(b.get("shown", True))
            out.append({"uid": self._uid(i), "sid": int(b.get("sid", 10 + i)),
                        "x": float(b["x"]), "y": float(b.get("y", 0.0)), "z": float(b["z"]),
                        "range": rr is not None, "talk": tr is not None,
                        "r": float(b["r"]), "solid": coll and bool(b.get("solid")), "coll": coll,
                        "range_r": float(rr) if rr is not None and coll else None,
                        "talk_r": float(tr) if tr is not None else None,
                        "shown": shown, "moving": self._walking(b) and not b.get("_held"),    # H23: a held walker stands
                        "flags": (1 if shown else 0) | (0 if coll else 14) | (16 if b.get("solid") else 0)})
        return out

    def _enter_freezes(self) -> None:
        """A step into one of this field's `freezes` zones holds movement from the next frame on."""
        x, z = self.player[0], self.player[2]
        for i, f in enumerate(self.freezes.get(self.field_id, ())):
            if (self.field_id, i) not in self._froze and _in_poly(x, z, f["zone"]):
                self._froze.add((self.field_id, i))
                n = f.get("frames")
                self._frozen_ticks = float("inf") if n is None else self.ticks_run + int(n) * WALKER_FRAME_TICKS
                self._coast = None

    def _region_at(self, x: float, z: float):
        """The region that ANSWERS for a centre at (``x``, ``z``): the first of this field's `regions` containing it
        (TreadQuad's first match) -- by its engine polygon ``points`` (content.doorface.region_contains) when it has
        one, else by the even-odd test on its ``zone`` -- or None."""
        from ff9mapkit.content import doorface
        for r in self.regions.get(self.field_id, ()):
            pts = r.get("points")
            if doorface.region_contains(x, z, pts) if pts is not None else _in_poly(x, z, r["zone"]):
                return r
        return None

    def _faces(self, r: dict) -> bool:
        """Whether region ``r``'s facing gate lets it fire now: True when it has none (no ``"face"``); else
        content.doorface.door_faced of his centre and `_face_deg` against its first edge (``points`` when it has
        them, else ``zone``), with the stock window for ``"face": True`` or the given ``[lo, hi]``."""
        face = r.get("face")
        if not face:
            return True
        from ff9mapkit.content import doorface
        q = r.get("points") or r["zone"]
        window = doorface.FACE_WINDOW if face is True else (int(face[0]), int(face[1]))
        return doorface.door_faced(self.player[0], self.player[2], self._face_deg, q[0], q[1], window)[0]

    def _enter_regions(self) -> None:
        """ExitField, modelled: a step into one of this field's `regions` takes control now and
        schedules the field change (see `regions`) -- when the region that answers (the first containing
        him) is live (``to`` not None) and, if gated (``face``), faced. A region that answers without firing
        ends the search: no region after it is tried."""
        if not self.control or self._exit is not None:
            return
        r = self._region_at(self.player[0], self.player[2])
        if r is None or not self._faces(r):
            return
        if r.get("take"):
            # a walk-in trigger (see `regions`): its tag 2 takes control this tick, and nothing warps
            self.fired.append({"frame": self.frame, "from": self.field_id, "to": None,
                               "executed": len(self.executed)})
            self.control = False
            self._coast = None
            return
        if r.get("to") is None:
            return
        self.fired.append({"frame": self.frame, "from": self.field_id, "to": int(r["to"]),
                           "executed": len(self.executed)})
        self.control = False
        self._coast = None
        self._exit = (self.frame + self.exit_frames, int(r["to"]), tuple(r["arrive"]))
        self._arrive_face = r.get("arrive_face")
        self._arrive_control = bool(r.get("arrive_control", True))
        self._walkout = self._walkout_of(r)        # H16 (opt-in): he walks on until the switch
        if self.exit_frames <= 0 and self._exit_open():
            self._step_exit_now()

    def _retest_gated(self) -> None:
        """CollisionRequest on a frame he STANDS -- nothing held and no coast, or frozen: the engine runs the tag 2
        of the region he stands in every tick he has control (EventEngine.ProcessEvents.cs:174-178 at stock
        6b8bb2d5, then EventCollision.cs:281-284), so a gated door whose
        facing a blocked press has turned fires without a step. Only when the answering region IS gated (see
        `regions`: ungated regions keep the step-only rule)."""
        if not self.control or self._exit is not None:
            return
        r = self._region_at(self.player[0], self.player[2])
        if r is not None and r.get("face"):
            self._enter_regions()

    def _step_exit_now(self) -> None:
        _due, dest, arrive = self._exit
        self._exit = None
        self._walkout = None                       # H16: the field changes under the walk-out
        self.field_id = dest
        self._visit += 1
        self._guest.field_load()                   # s96: a gateway's load re-arms the panic unlock (to the same field too)
        self.player = [float(arrive[0]), 0.0, float(arrive[1])]
        if self._arrive_face is not None:          # the firing region's ``arrive_face`` (see `regions`)
            self._face_deg = float(self._arrive_face)
            self._arrive_face = None
        self._in_trigger.clear()
        self._coast = None
        self.control = self._arrive_control        # the firing region's ``arrive_control`` (see `regions`)
        self._arrive_control = True

    # -- the in-place turn (memoria-patch s90) ------------------------------------------------------
    # Modelled as the agent's CONTRACT (the s90 DRIVER.md, and where they differ HarnessAgent.cs: BeginTurn,
    # ServiceTurn, EndTurn, TurnBlocker, ClaimForMove): the refusals, in the agent's order and words, raised
    # through the ordinary error path; the keys held with no axis, so he turns and never steps
    # (:meth:`_turn_in_place`); the report held until the field has judged the final facing, a door that fires in
    # those passes reported as the `control` that took him. Not the engine's float noise: a turn in place moves him
    # exactly 0, unless a push-out does (then ``moved`` says how far).
    def _on_field(self) -> bool:
        """A field is up with a controlled character: what the agent publishes ``player.yaw`` / ``face`` on."""
        return (self.field_id > 0 and self.ui_state not in ("Title", "WorldHUD", "BattleHUD")
                and not self.battle_active and self.has_position)

    def _turn_blocker(self) -> str | None:
        """HarnessAgent.TurnBlocker's token -- why the field would not honour a turn now -- for the fake's world,
        in the agent's order: ``field`` (no field up), ``player`` (no controlled character: `has_position` off),
        ``control``, ``movement`` (a hold on movement, `_frozen`), ``hud`` (a UI other than the field HUD);
        None when it would."""
        if self.field_id <= 0 or self.ui_state in ("Title", "WorldHUD", "BattleHUD") or self.battle_active:
            return "field"
        if not self.has_position:
            return "player"
        if not self.control:
            return "control"
        if self._frozen():
            return "movement"
        if self.ui_state != "FieldHUD":
            return "hud"
        return None

    def _turn_keys_from(self, frame: int) -> set:
        """The turn keys down on ``frame`` or any later one (HarnessAgent.TurnKeysFrom: down on [down, up))."""
        return {b for b in self._turn_keys if self.held.get(b, -1) > frame}

    def _begin_turn(self, dirs: list, frames: int) -> None:
        """``turn`` (HarnessAgent.BeginTurn): every refusal raises before anything is pressed, in the agent's order
        and words -- no field / player / control / movement / HUD; the last turn still being judged; a turn in
        progress on another visit; `analog_control` off; any direction down now or on a later frame (the turn's own
        keys exempt while composing onto it); opposite directions (turn keys still down counted); a human's `stick`
        over STICK_THRESHOLD, or a `click_path` pending; a collidable body he overlaps. Then the turn is committed --
        its start kept while its keys are down, so two turns sent while the first's keys are down compose into one
        report -- and each key is held by `_extend`, as `hold` holds."""
        import math
        why = self._turn_blocker()
        if why is not None:
            raise RuntimeError(f"needs a field with a controlled player under user control ({why})")
        f = self.frame
        t = self._turn_open
        if t is not None and (t["lift"] is not None or not self._turn_keys_from(f)):
            raise RuntimeError("the last turn's keys are up and the field is still judging it -- wait for its turn_end")
        if t is not None and (t["field"] != self.field_id or t["visit"] != self._visit):
            raise RuntimeError("the turn in progress began on another actor or field -- it is cut this frame; turn "
                               "again after its turn_end")
        if not self.analog_control:
            raise RuntimeError("[AnalogControl] Enabled=0 -- MovePC's key path would step him, not turn him")
        fresh = self._turn_open is None
        for d in ("up", "down", "left", "right"):
            if not fresh and d in self._turn_keys:
                continue
            if self._is_held(d) or self.held.get(d, -1) > f + 1:
                raise RuntimeError(f"{d.capitalize()} is held or scheduled -- release it (and let it lift) first")
        every = self._turn_keys_from(f + 1) | set(dirs)
        if {"up", "down"} <= every or {"left", "right"} <= every:
            raise RuntimeError("opposite directions cancel to no direction")
        if self.stick > STICK_THRESHOLD:
            raise RuntimeError(f"a physical stick or key is pushing the axis (|a| {_fmt(self.stick)}) -- MovePC's "
                               f"axis branch would walk him")
        if self.click_path:
            raise RuntimeError("a click-to-move path is pending -- the turn keys would consume it")
        px, py, pz = self.player
        for i, b in self._bodies():
            if (b.get("coll", True) and abs(float(b.get("y", 0.0)) - py) < 400
                    and math.hypot(b["x"] - px, b["z"] - pz) < b["r"]):
                raise RuntimeError(f"overlapping object uid {self._uid(i)} -- a turn toward it would push him out")
        if fresh:
            self._turn_open = {"from": f + 1, "lift": None, "field": self.field_id, "visit": self._visit,
                               "x": px, "y": py, "z": pz, "yaw0": self._face_deg, "passes": 0}
        self._turn_keys = self._turn_keys_from(f) | set(dirs)
        for d in dirs:
            self._extend(d, frames)

    def _claim_for_move(self, button: str) -> None:
        """``hold`` / ``press`` of a DIRECTION while a turn is open (HarnessAgent.ClaimForMove): refused -- it would
        hand MovePC an axis inside what the driver believes is a turn in place, or a walk inside the passes the field
        judges it on; refused too while a turn key is still down when this key would go down. Otherwise the key's
        stale turn bit is dropped, so the hold feeds the axis. Any other button passes."""
        if button not in ("up", "down", "left", "right"):
            return
        if self._turn_open is not None:
            raise RuntimeError("a `turn` is still open (its keys down, or up and being judged) -- wait for its "
                               "turn_end")
        if self._turn_keys_from(self.frame + 1) or (button in self._turn_keys and self._is_held(button)):
            raise RuntimeError("a `turn` key is still down -- release it (and let it lift) first")
        self._turn_keys.discard(button)

    def _service_turn(self) -> None:
        """Once a frame, after the world's (HarnessAgent.ServiceTurn): end, or cut, the turn being reported. While its
        keys are down it is CUT the moment the field stops honouring it (`_turn_blocker`, the field id or the visit
        changing, a human's `stick` over STICK_THRESHOLD: ``axis``) -- `turn_end` with that token, the keys lifted on
        the next frame by the release rule. Once they
        lift, the report stays open `turn_settle_passes` passes after the lift frame (frames that ran a tick -- every
        frame in mean mode; or under `tick_phase` the tick frames) under the same tests: a gated door that fires on the
        final facing takes
        control, and is reported as that ``control``; ``ended`` means the field ran its passes on that facing and
        nothing took him."""
        f = self.frame
        t = self._turn_open
        if t is None:
            if self._turn_keys and not self._turn_keys_from(f):
                self._turn_keys = set()             # a cut turn's keys have lifted: the bits are stale
            return
        down = bool(self._turn_keys_from(f))
        if not down and t["lift"] is None:
            t["lift"], t["passes"] = f, 0           # the facing is final; the field's next passes read it
            self._turn_keys = set()
        why = self._turn_blocker()
        if why is None and self.field_id != t["field"]:
            why = "field"
        if why is None and self._visit != t["visit"]:
            why = "player"
        if why is None and self.stick > STICK_THRESHOLD:
            why = "axis"                            # a human's stick crossed the threshold: he would walk
        if why is None:
            if down:
                return
            # a frame that RAN a pass counts once (HarnessAgent.ServiceTurn): every frame of mean ticks, a frame that
            # ran a whole tick when quantized, and under tick_phase its tick frames
            if f > t["lift"] and self._frame_steps() and (self.tick_phase is None or f % 2 == self.tick_phase):
                t["passes"] += 1
            if t["passes"] < self.turn_settle_passes:
                return
            why = "ended"
        if not down:
            self._end_turn(why, t["lift"] - t["from"])
            return
        for b in list(self._turn_keys):             # lifted by the release rule: never a press
            if self.held.get(b, -1) <= f:
                continue
            if f >= self.down_at.get(b, 1 << 30):
                self.held[b] = f + 1
            else:
                self.held.pop(b, None)
                self.down_at.pop(b, None)
        self._end_turn(why, f + 1 - t["from"])

    def _end_turn(self, why: str, frames: int) -> None:
        """``turn_end`` (HarnessAgent.EndTurn), every value but ``frame`` a STRING as the agent's event writer quotes
        them: ``why``, ``frames`` (the frames its keys were down), ``yaw0`` / ``yaw`` (degrees, "0.###"), ``face``
        (content.doorface.facing_byte of the yaw) and ``moved`` (3-D distance from the start) -- the last three null
        off a field or on another field id or visit than the turn began on."""
        import math
        from ff9mapkit.content import doorface
        t = self._turn_open
        same = self._on_field() and self.field_id == t["field"] and self._visit == t["visit"]
        yaw = self._face_deg if same else None
        moved = (math.sqrt((self.player[0] - t["x"]) ** 2 + (self.player[1] - t["y"]) ** 2
                           + (self.player[2] - t["z"]) ** 2) if same else None)
        self._event("turn_end", why=why, frames=max(0, int(frames)), yaw0=_fmt(t["yaw0"]), yaw=_fmt(yaw),
                    face=None if yaw is None else doorface.facing_byte(yaw), moved=_fmt(moved))
        self._turn_open = None

    def _check_soft_reset(self) -> None:
        """All six buttons reporting a DOWN EDGE on the same frame sends the game to the title.

        The real handler closes every dialog, hides the HUD, disables all button groups and the
        battle menu, un-pauses, normalises btl_seq and replaces the scene with Title -- which is why
        it is the only recovery rung that reaches a battle or a stuck menu. What matters for the
        driver is the observable end state, so that is what this models.

        WHERE IT FIRES is `soft_reset_ui` (H9, research/o3_design.md 0.2 #9). The reset is held through
        ``UIKeyTrigger.GetKey``, which answers false outside FieldHUD / WorldHUD / BattleHUD / QuadMistBattle
        (UIKeyTrigger.cs:94) -- so in the ENGINE it fires from BattleHUD mid-fight (on the combo's second held frame:
        the down frame's Select is the menu handler's) and NEVER from BattleResult: the battle's end sequence swallows
        it. The default here is the narrower pair every test before H9 was written against; a test that models the
        engine passes :data:`SOFT_RESET_ENGINE_UI`, and a reset from BattleHUD then ends the battle with the scene.
        And while a MOVIE plays (a scene's movie beat, its skip dialog included) the combo is swallowed whatever the
        set says: ``HandleBoosterButton``, which holds the reset, returns at once while MBG is marked played
        (UIKeyTrigger.cs:241, MBG.cs:607-610).
        """
        if not self.soft_reset_enabled:
            return
        if not all(self.down_at.get(b) == self.frame for b in SOFT_RESET_COMBO):
            return
        # ⚠ A MENU SWALLOWS THE COMBO, and the stand-in has to swallow it too. `UIKeyTrigger.Update`
        # runs `if (HandleMenuControlKeyPressCustomInput()) return;` before the soft-reset check, and
        # that handler consumes Control.Select unconditionally. MEASURED in-game
        # (scenarios/soft_reset_reach.py): from a field YES, from an open MainMenu NO. A stand-in
        # more forgiving than the engine is worse than none -- it certifies a ladder that cannot
        # actually climb.
        if self._movie is not None or self.ui_state not in self.soft_reset_ui:
            return
        if self.field_id in self.reset_blocked_fields:
            return                              # H16b: a running scene there swallows it (O1d)
        if self.ui_state == "BattleHUD":
            # mid-fight, from a set that holds it: the battle goes with the scene -- nothing of it is up at the title
            self.battle_active = False
            self.commands_enabled = False
            self._tutorial = False
            self._bexit = self._script_end = None
            self.battle_pending = []
        self.soft_resets += 1
        self.ui_state = "Title"
        self.field_id = -1
        self.control = False
        self.texts = []
        self.raw_texts = []
        self.choice = None
        self._beats, self._beat_phase = [], None
        self.menu = {"selected": None, "hovered": None, "label": None, "group": None}
        self.menu_entries = []
        self.player = [0.0, 0.0, 0.0]
        # ⚠ NOT held.clear(). FF9's handler does not release the player's buttons, and a stand-in
        # that did would make `reset_agent` -- the thing that actually releases them -- untestable:
        # it could be reduced to a no-op with every test still green.
        self._event("soft_reset")

    # -- the battle HUD's cursor ---------------------------------------------------------------
    #: The command list as the HUD lays it out: a TWO-COLUMN grid that does NOT wrap vertically.
    #: Measured live 2026-09-04 -- from `Steal`, `down` reaches `Item` and then moves nothing, and
    #: `Attack` (one row up) is never seen by a one-direction walk. A stand-in whose battle menu
    #: wrapped, or had one column, would certify a battle_pick that cannot find half the commands.
    BATTLE_GRID = [["Attack", "Defend"], ["Steal", "Skill"], ["Item", "Change"]]
    #: What each command opens on confirm (BattleHUD.Const.cs group names). `Attack`/`Steal` go to
    #: the target cursor; `Skill` and `Item` open SUBMENUS -- distinct groups a driver must not
    #: mistake for the target cursor (the first cut confirmed a Potion that way).
    BATTLE_OPENS = {"Attack": "Battle.Target", "Steal": "Battle.Target", "Skill": "Battle.Ability",
                    "Item": "Battle.Item"}
    BATTLE_SUBMENU_ROWS = {"Battle.Item": ["Potion", "Hi-Potion"], "Battle.Ability": ["Flee"]}

    def _open_battle_cursor(self) -> None:
        self._grid_pos = [0, 0]
        self._battle_pending_cmd = None
        self._sub_index = 0
        self._nb_pick = None                    # [ff9mapkit netsync B4] s106: a mirrored slot's picked row
        self._nb.double_cast, self._nb.cast_first = 0, None
        self._set_battle_cursor("Battle.Command", self.BATTLE_GRID[0][0])
        self._nb_on_panel("Battle.Command", force=True)

    def _close_battle_cursor(self) -> None:
        self.menu = {"selected": None, "hovered": None, "label": None, "group": None,
                     "button": None, "button_label": None}

    def _set_battle_cursor(self, group: str, label: str) -> None:
        prev = self.menu.get("group")
        self.menu = {"selected": f"btn_{label}", "hovered": None, "label": label, "group": group,
                     "button": f"btn_{label}", "button_label": label}
        if group != prev:
            self._nb_on_panel(group)            # [ff9mapkit netsync B4] s106: a panel DISPLAYED (a mirrored one drawn)

    def _battle_rows(self, group: str) -> list:
        """The labels a submenu's cursor walks: a mirrored slot's drawn rows, else the stand-in's own."""
        snap = self._nb_snap_for(group)
        if snap is not None:
            return [r["label"] for r in snap["rows"]] or [""]
        return self.BATTLE_SUBMENU_ROWS[group]

    def _battle_menu_step(self, button: str) -> None:
        group = self.menu.get("group")
        mirrored = self._nb_snap_for(group) is not None
        if group == "Battle.Command":
            r, c = self._grid_pos
            if button == "down":
                r = min(r + 1, len(self.BATTLE_GRID) - 1)        # clamp: no wrap
            elif button == "up":
                r = max(r - 1, 0)
            elif button == "right":
                c = min(c + 1, len(self.BATTLE_GRID[0]) - 1)
            elif button == "left":
                c = max(c - 1, 0)
            elif button in ("confirm", "ok"):
                label = self.BATTLE_GRID[r][c]
                opens = self.BATTLE_OPENS.get(label)
                if mirrored:
                    # [ff9mapkit netsync B4] s106: a mirrored slot's command is the one DRAWN -- a greyed one takes no
                    # Confirm; a roster Ability-type command opens its list
                    drawn = self._nb.hud_snap["commands"][r * 2 + c]
                    if drawn["state"] != 2:
                        return
                    self._nb_pick = None
                    if drawn["id"] in self.FAKE_COMMAND_ABILITIES and label != "Item":
                        opens = "Battle.Ability"
                if opens is None:
                    # Defend / Change: no target, committed straight away.
                    if self._nb_commit(label, 1 << self.battle_turn if self.battle_turn >= 0 else 0, None):
                        return                      # [ff9mapkit netsync B4] captured (or refused) inside the diorama
                    self._battle_command(self.battle_turn, 2, 177, 0, 0,
                                         site="BattleHUD.SendCommand < BattleHUD.OnKeyConfirm")
                    self._close_battle_cursor()
                    return
                self._battle_pending_cmd = label
                self._sub_index = 0
                if opens == "Battle.Target":
                    foe = next((u for u in self.battle_units
                                if not u["player"] and u["alive"] and u["targetable"]), None)
                    self._set_battle_cursor(opens, foe["name"] if foe else "nobody")
                else:
                    self._set_battle_cursor(opens, "")              # (a mirrored panel is drawn here)
                    first = self._battle_rows(opens)[0]
                    self.menu.update(selected=f"btn_{first}", label=first, button=f"btn_{first}", button_label=first)
                return
            self._grid_pos = [r, c]
            self._set_battle_cursor("Battle.Command", self.BATTLE_GRID[r][c])
            return
        if group in ("Battle.Item", "Battle.Ability"):
            rows = self._battle_rows(group)
            if mirrored and button in ("confirm", "ok"):
                # [ff9mapkit netsync B4] s106: a row the roster drew blank or disabled takes no Confirm; a pick is
                # remembered for the target panel's count (5) and the capture
                drawn = self._nb.hud_snap["rows"][self._sub_index] if self._nb.hud_snap["rows"] else None
                if drawn is None or drawn["state"] != 2:
                    return
                m = self._nb.hud_snap["menu"]
                self._nb_pick = {"menu": 0 if group == "Battle.Item" else m, "id": drawn["id"],
                                 "cmd": 8 if group == "Battle.Item" else self._nb.hud_snap["commands"][m]["id"],
                                 "label": drawn["label"], "item": group == "Battle.Item"}
            if button in ("cancel", "back", "b"):
                self._set_battle_cursor("Battle.Command", self.BATTLE_GRID[self._grid_pos[0]][self._grid_pos[1]])
            elif button == "down":
                self._sub_index = min(self._sub_index + 1, len(rows) - 1)
                self._set_battle_cursor(group, rows[self._sub_index])
            elif button == "up":
                self._sub_index = max(self._sub_index - 1, 0)
                self._set_battle_cursor(group, rows[self._sub_index])
            elif button in ("confirm", "ok"):
                # Picking an item/ability then opens the target cursor, as the HUD does.
                foe = next((u for u in self.battle_units if not u["player"] and u["alive"]), None)
                self._set_battle_cursor("Battle.Target", foe["name"] if foe else "nobody")
            return
        if group == "Battle.Target":
            if button in ("cancel", "back", "b"):
                self._set_battle_cursor("Battle.Command", self.BATTLE_GRID[self._grid_pos[0]][self._grid_pos[1]])
            elif button in ("confirm", "ok"):
                foe = next((u for u in self.battle_units
                            if not u["player"] and u["alive"] and u["targetable"]), None)
                label = self._battle_pending_cmd
                pick = self._nb_pick if mirrored else None
                if pick is not None and not pick["item"] and pick["cmd"] in self.FAKE_DOUBLE_CAST:
                    # [ff9mapkit netsync B4] s106 (6) SingleCastSlot: a mirrored slot's double-cast command makes ONE
                    # pick (the v1 frame carries one); the hook off, stock's second pick first
                    if self._nb_content_on(BW.CONTENT_CAST):
                        self._nb_hit(BW.CONTENT_CAST)
                    elif self._nb.double_cast == 0:
                        self._nb.double_cast, self._nb.cast_first = 2, dict(pick)
                        self._set_battle_cursor("Battle.Ability", pick["label"])
                        return
                    else:
                        self._nb.double_cast, self._nb.cast_first = 0, None
                sub_group = {"Item": "Battle.Item", "Skill": "Battle.Ability"}.get(label)
                row = self.BATTLE_SUBMENU_ROWS[sub_group][self._sub_index] if sub_group and pick is None else None
                # [ff9mapkit netsync B4] inside the diorama the commit is CAPTURED (a Potion's default target: the caster)
                item = label == "Item" or (pick is not None and pick["item"])
                mask = (1 << self.battle_turn) if item and self.battle_turn >= 0 else (foe["id"] if foe else 0)
                if self._nb_commit(label, mask, row, pick=pick):
                    return
                cmd = {"Attack": (1, 176), "Steal": (3, 178)}.get(self._battle_pending_cmd, (8, 1))
                self._battle_command(self.battle_turn, cmd[0], cmd[1], foe["id"] if foe else 0, 0,
                                     site="BattleHUD.SendCommand < BattleHUD.OnKeyConfirm")
                self._close_battle_cursor()

    def _menu_step(self, button: str) -> None:
        if AGENT_CONTROL.get(str(button).lower()) == "menu" and self._menu_key_press():
            return      # [ff9mapkit netsync R3 s121] a mirroring guest's Menu key: s38's refusal (s121: audible on the HUDs)
        if button in GUEST_DIALOG_KEYS and self._guest_suppress():
            return      # s96: UIKeyTrigger swallows a following guest's dialogue keys under the lock (and the cursor holds)
        if button in ("confirm", "ok", "cancel", "back", "b") and self.dialog_inh and self._dialog_open():
            # [ff9mapkit netsync F3.3] an input-inhibited ([NFOC]) window ignores its own confirm/cancel (ignoreInputFlag):
            # its SCRIPT polls the press (:meth:`_step_script_poll`) -- the arrows still move a polled choice's cursor
            return
        if self.quit_prompt:
            # [ff9mapkit netsync B5] s109: the game's own QUIT prompt takes the keys: Cancel closes it, Confirm is its Yes
            if button in ("cancel", "back", "b"):
                self.quit_prompt = False
                self._nb.quit_opened = False
            elif button in ("confirm", "ok"):
                self._event("quit")
                self.returncode = 0                 # the game quits -- why the bench must never Confirm it
            return
        sc = self._nb.screen
        if (self.ui_state == "BattleResult" and sc is not None and self._nb.r_opened and not sc["hidden"]
                and not sc["aborted"] and button in ("confirm", "ok")):
            self._nb_replay_local_confirm()         # [ff9mapkit netsync B5] s109 seam c: the guest's own Confirm
            return
        if self.ui_state == "Tutorial":
            if button in ("confirm", "ok"):
                self._tutorial = False
                self.ui_state = "BattleHUD"
            return
        if self._beats:
            self._scene_press(button)
            return
        if str(self.menu.get("group") or "").startswith("Battle."):
            self._battle_menu_step(button)
            return
        # Cancel backs a screen OUT. Modelled because the close-UI recovery rung is built on it: the
        # soft-reset combo is swallowed inside a menu, so Cancel is the only way out of one, and a
        # stand-in whose menus could not be left would certify a ladder that cannot climb.
        if button in ("cancel", "back", "b") and self.ui_state == "MainMenu":
            self.ui_state = "FieldHUD"
            self.menu_entries = []
            self.menu = {"selected": None, "hovered": None, "label": None, "group": None}
            self.control = True
            return
        if not self.menu_entries:
            return
        if button == "down":
            self.menu_index = (self.menu_index + 1) % len(self.menu_entries)
        elif button == "up":
            self.menu_index = (self.menu_index - 1) % len(self.menu_entries)
        elif button in ("confirm", "ok") and self.choice is not None:
            self._dialog_tap(KIND_CHO)          # [ff9mapkit netsync F3.3] R9: Dialog.OnKeyConfirm's host tap (the commit)
            self.choice = None
            return
        self.menu["label"] = self.menu_entries[self.menu_index]
        self.menu["selected"] = f"Button{self.menu_index}"
        if self.choice is not None:
            self.choice["selected"] = self.menu_index

    # -- publication ---------------------------------------------------------------------------
    def _publish(self, force: bool = False) -> None:
        if not force and self.frame - self.publish_frame < self.state_every:
            return
        self.publish_frame = self.frame
        held = [b for b in self.held if self._is_held(b)]
        px, py, pz = self._pos_before if self.publish_lag is not None and self.publish_lag(self.frame) else self.player
        if not self.has_position:
            px = py = pz = None
        doc = {
            "v": PROTOCOL if self.protocol is None else self.protocol, "frame": self.frame, "seq": self.seq, "ack": self.ack,
            "queue": len(self.queue),
            "busy": bool(self.queue) or self.frame < self.block_until,
            "armed": self.armed,
            "shots": self.shots_taken, "timescale": 1.0, "note": self.note,
            "error": self.error, "error_seq": self.error_seq,
            "debug_status": None,
            "save_path": str(self.dir / "save" / "SavedData_ww.dat"),
            "save_sandboxed": self.save_sandboxed,
            # [ff9mapkit netsync F3.3] DIO-1: a booted diorama's battle is the debug scene (BattleUI's own recipe)
            "ui_state": self.ui_state, "scene": "BattleMapDebug" if self._dio["booted"] and self.battle_active
                                                 else "FieldMap", "fading": False,
            "sys_mode": 1, "scenario": self.scenario,
            "field": {"id": self.field_id, "name": f"FBG_FAKE_{self.field_id}"},
            "world": dict(self.world),
            # floor/tri mirror s83 faithfully, dead values and all: PosObj's battle-entry snapshot
            # reads 0/0 until the session's first battle (State.player_tri_battle_snapshot).
            "player": {"x": px, "y": py, "z": pz,
                       "dir": 0, "floor": 0, "tri": 0, "control": self.control},
            "input": {"key_up": self._is_held("up"), "key_confirm": self._is_held("confirm"),
                      "move_key": bool(held), "dash_inh": int(self.dash_inhibit), "axis_x": 0.0, "axis_y": 0.0},
            "dialog": {"open": bool(self.texts) or self.choice is not None,
                       "count": len(self.texts),
                       "texts": self.texts, "phrase_raw": self.raw_texts or self.texts,
                       "choice": self.choice},
            "menu": dict(self.menu),
            "battle": self._battle_doc(),
            "flags": {str(b): self._watched_bit(b) for b in self.watch},
            "netsync": self._netsync_doc(),
            "held": held,
        }
        if self.facing_mode == "published":
            # s90: the yaw raw (to 0.001) and the gate's facing byte, both null exactly together -- off a field or with
            # no controlled character; published with or without user control (a scripted turn moves the yaw too)
            from ff9mapkit.content import doorface
            on = self._on_field()
            doc["player"]["yaw"] = round(self._face_deg, 3) if on else None
            doc["player"]["face"] = doorface.facing_byte(self._face_deg) if on else None
        if self.storytrace_proto is not None:
            doc["storytrace"] = {"proto": self.storytrace_proto, "on": self.story_on,
                                 "rows": self.story_rows, "suppressed": 0, "error": self.story_error}
        if self.objects_mode != "absent":
            # s89: both null off a field or on any failure, never a partial list
            listed = self.objects_mode == "listed" and self.ui_state == "FieldHUD"
            doc["objects"] = self._objects_doc() if listed else None
            doc["pushout"] = ({"slock": int(self._lock), "scoll": math.ceil(self._coll - 1e-9),
                               "slockfree": int(self._lock_free), "fallback": True} if listed else None)
        # the clocks (`publish`): the virtual realtime clock and the ticks run, IN the document -- what a driver pairs
        # frames with before it falls back on the file's mtime (harness.tickrate.TickClock)
        if "rt" in self.publish:
            doc["rt"] = self.rt
        if "ticks" in self.publish:
            doc["ticks"] = int(self.ticks_run) if self._tick_mode == "quantized" else self.ticks_run
        stamp = self._wall0 + self.rt if "mtime" in self.publish else None
        if self._publish_stalls:
            _publish_in_place(self.dir / "state.json", json.dumps(doc),
                              stall=self._publish_stalls.pop(0), began=self.stalling,
                              stop=self._stop, mtime=stamp)
        else:
            _publish_atomic(self.dir / "state.json", json.dumps(doc), mtime=stamp)

    def stall_publish(self, seconds: float, *, times: int = 1) -> None:
        """Make the next ``times`` publishes stall MID-REWRITE for ``seconds`` each.

        THE REAL AGENT'S SHAPE, which the ordinary publish here is not. ``HarnessAgent.WriteAtomic``
        writes state.json IN PLACE (``FileMode.Create``: truncate, then the bytes land), so between
        the two the file is EMPTY -- and MEASURED 2026-09-23 with that exact open mode at 60 Hz, the
        gap has a median of 0.7 ms and a p99 of ~80 ms (max ~200 ms, an on-access scan holding the
        rewrite). The channel's own parse retry spans ~30 ms, so a stall past it turned a healthy
        game into "no state published" (studies/platform-land/rung0_land.py, 40-frame ride).

        The frame loop blocks for the stall, as the game's main thread does inside the write. A
        long stall is the game hung INSIDE the publish; ``stop()`` cuts it short, so a test's
        teardown never waits one out.
        """
        self._publish_stalls.extend([float(seconds)] * max(1, int(times)))

    def _event(self, kind: str, **kv) -> None:
        # every value but `frame` a STRING, as the agent's Event() writes them -- or null (its Str of a null)
        row = {"frame": self.frame, "kind": kind}
        row.update({k: None if v is None else str(v) for k, v in kv.items()})
        # buffered first and flushed whole, as HarnessAgent.Event / FlushEvents: an append that fails keeps every row
        # it carried for the next event's append (`event_collisions` makes one fail on purpose)
        self._pending_events.append(json.dumps(row))
        if self.event_collisions.get(kind, 0) > 0:
            self.event_collisions[kind] -= 1
            return
        try:
            with (self.dir / "events.jsonl").open("a", encoding="utf-8") as fh:
                fh.write("\n".join(self._pending_events) + "\n")
            self._pending_events.clear()
        except OSError:
            pass

    def _write_png(self, name: str) -> None:
        """A real PNG -- the driver decodes it to check the frame is not uniformly blank."""
        safe = "".join(c if (c.isalnum() or c in "-_.") else "_" for c in name) or "shot"
        # 4x1 with four different colours, so a "not a blank screen" check has something to find.
        rows = b"\x00" + bytes(range(12))
        png = (b"\x89PNG\r\n\x1a\n"
               + _chunk(b"IHDR", struct.pack(">IIBBBBB", 4, 1, 8, 2, 0, 0, 0))
               + _chunk(b"IDAT", zlib.compress(rows))
               + _chunk(b"IEND", b""))
        (self.shots / f"{safe}.png").write_bytes(png)
        self.shots_taken += 1
        self._event("shot", name=name)

    # -- battle --------------------------------------------------------------------------------
    def _battle_doc(self) -> dict:
        # Outside a battle only the three cheap facts are published, exactly as the agent does --
        # because every OTHER value in FF9Battle is STALE rather than absent afterwards, and
        # publishing them on a field would hand a scenario a plausible, entirely historical battle.
        # `result`, `scene` and `bonus` ride alongside `epoch` and are published ALWAYS: they are
        # what a scenario needs AFTER the fight, and the epoch is what says which fight they belong
        # to. Everything below them is a mid-battle concept the engine leaves holding the previous
        # battle's contents, so publishing it on a field would be a plausible historical lie.
        doc = {"active": self.battle_active, "epoch": self.battle_epoch, "debug": self.battle_debug,
               "result": self.battle_result, "scene": self.battle_scene,
               "bonus": dict(self.battle_bonus)}
        if not self.battle_active:
            return doc
        caps = self._nb_caps()
        doc.update({
            # [ff9mapkit netsync B4] the phase as the stand-in runs it (PHASE_ENTER through the opening camera, NORMAL
            # after it, the CLOSE fade of a `battle_exit` end, a diorama presentation's own) -- and, from s102, its seq
            "phase": self._battle_phase_now(),
            **({"seq": self._battle_seq_now()} if "stockmenu" in caps else {}),
            # ⚠ escape_held says the BUMPERS ARE DOWN and nothing more -- it is set before every
            # gate. `escaping` is the queued SysEscape, i.e. the roll actually landed. A stand-in
            # that conflated them could not catch a driver that waits on the wrong one.
            "escape_held": 0 if self.deaf_bumpers else
                           (1 if (self._is_held("l1") and self._is_held("r1")) else 0),
            "escaping": self.escaping,
            # ⚠ btl_scene.Info. `runaway` false means CheckEscape shows "Cannot escape!" and NEVER
            # rolls -- while btl_escape_key still runs the animation. Modelled because the driver
            # refuses that scene up front, and an unmodelled block makes that a guard nothing fires.
            "scene_info": {"runaway": self.scene_runaway, "no_gameover": self.scene_no_gameover,
                           "preemptive": False, "back_attack": False},
            # ⚠ GATED, exactly as the agent publishes it. `slot_raw` is the ungated value, which
            # during the intro is the PREVIOUS battle's -- and acting on it froze a real fight.
            "turn": {"enabled": self.commands_enabled,
                     "slot": self.battle_turn if self.commands_enabled else -1,
                     "slot_raw": self.battle_turn,
                     "ready": list(self.battle_ready) if self.commands_enabled else [],
                     "done": list(self.battle_done) if self.commands_enabled else []},
        })
        if "stockmenu" in caps:
            doc["hud"] = self._battle_hud_doc()                   # [ff9mapkit netsync B4] s102 NetDescribeHud
        if "endblock" in caps:                                    # [ff9mapkit netsync B5] s103 the live result screen
            doc["result_ui"] = self._result_ui_doc() if self.ui_state == "BattleResult" else None
        doc["menu"] = dict(self.battle_menu)
        units = [dict(u) for u in self.battle_units]
        if "containment" in caps:
            # [ff9mapkit netsync B4] s101: bit i while cmd[i] is queued or executing -- bit 0, the ATB command, from the
            # commit to its resolution (an R9-refused enqueue never sets it)
            pending = {e[1] for e in self.battle_pending}
            for u in units:
                status = u.pop("status", "0")               # (the agent's order: cmd_busy before status)
                u["cmd_busy"] = 1 if u["slot"] in pending else 0
                u["status"] = status
        if "flee" in caps:
            # [ff9mapkit netsync R3 s115] the run-away made readable, after cmd_busy and before status (the agent's order):
            # `mot` (17 MP_ESCAPE while running, 4 MP_DISABLE once down; 0 the idle), `disappear` (5 once the escape fade
            # finished) and `z` (falls while a runner runs)
            for i, u in enumerate(units):
                r = self._nb.unit_r3.get(u["slot"], {})
                status = u.pop("status", "0")
                u["mot"] = r.get("mot", BW.MP_DISABLE if not u.get("alive", True) else 0)
                if "actreplay" in caps and u["slot"] in self._act_guest.swings:
                    u["mot"] = BW.MP_ATTACK                 # [ff9mapkit netsync s134] an uncovered impact's legacy swing
                if "acthold" in caps and u["slot"] in self._act_guest.hold.flinches and u.get("alive", True):
                    u["mot"] = BW.MP_DAMAGE1                # [ff9mapkit netsync s135] a released (or arrival) flinch
                fb = self._act_guest.fallback.clip_on.get(u["slot"]) if "actfallback" in caps else None
                if fb is not None and u.get("alive", True):
                    u["mot"] = fb["mot"]                    # [ff9mapkit netsync s136] fallback A's clip (an enemy's: -1)
                u["disappear"] = r.get("disappear", 0)
                u["z"] = float(r.get("z", -600.0 if u.get("player") else 600.0))
                if "actreplay" in caps:
                    # [ff9mapkit netsync s134] the action replay made readable, after z and before status (the agent's
                    # order): battlewire.ActGuestLane.unit_doc -- shapes, not engine clips (its docstring)
                    live = next((x for x in self.battle_units if x.get("slot") == u["slot"]), u)
                    u.update(self._act_guest.unit_doc(live))
                u["status"] = status
        doc["units"] = units
        return doc

    def start_battle(self, scene: int, *, group: int = -1, debug: bool = False,
                     units: list[dict] | None = None, rand: bool = False) -> None:
        """Stand a battle up, advancing the epoch the way battle.InitBattle does. [ff9mapkit netsync R3 s111] ``rand``: a
        random encounter -- with cfg.skip_btl_camera 0 the stock intro test skips the plunge camera (a short intro);
        inside a booted diorama the HOST's choice decides instead (NetSyncDiorama.SkipBattleIntro)."""
        self.battle_epoch += 1
        self.battle_active = True
        self.battle_debug = debug
        self.battle_random = bool(rand)
        self.battle_result = 0                    # reset at START, which is why 0 is ambiguous
        self._nb.flee_ability_flag = False        # [ff9mapkit netsync R3 s115] InitBattle zeroes ff9.btl_flag (its flee bit too)
        self.battle_scene = scene
        self.ui_state = "BattleHUD"
        self._tutorial = scene in self.tutorial_scenes
        if self._tutorial:
            self.ui_state = "Tutorial"
        self.battle_bonus = {"exp": 0, "gil": 0, "ap": 0, "items": 0}
        # ⚠ battle_turn / ready / done are deliberately NOT cleared here. In the engine they are
        # reset by BattleHUD.InitialBattle(), which runs LATER than the battle scene goes live --
        # so through the opening camera they still hold the PREVIOUS fight's contents. That window
        # is what published a plausible "your move" for a battle that was not asking, and a
        # stand-in that tidied up here could not reproduce it. _step_battle clears them when the
        # intro ends, which is where the engine clears them too.
        self.commands_enabled = False
        self._intro_until = self.frame + self.battle_intro_frames
        if "intro" in self._nb_caps() and self._nb_intro_skipped(debug):
            # [ff9mapkit netsync R3 s111] the stock intro test (or, in a diorama, the host's choice) skips the camera
            self._intro_until = self.frame + min(self.battle_intro_frames, self.battle_intro_skip_frames)
        if "swirl" in self._nb_caps() and not debug:
            self._nb_record_swirl(False)            # [ff9mapkit netsync R3 s112] a real battle's swirl keeps its own length
        self.battle_pending = []
        self.escaping = False
        self.run_counter = 0.0
        self._bexit = self._script_end = None     # H9: no end running, and the latch not yet fired, in a new battle
        self._script_latched = False
        self._race_steps, self._race_due = 0, None
        # ⚠ battle_menu is deliberately NOT cleared here either, for the same reason: a driver that
        # reads the menu without checking its epoch stamp has to be catchable.
        self.battle_units = units if units is not None else [
            # hp/hp_max are the LOGICAL values the HUD shows; hp_raw/hp_max_raw are cur.hp/max.hp,
            # what the AI reads as B_MEMBER (36)/(35). The enemy below carries the 10000 offset a
            # FLG_NON_DYING_BOSS gets under CustomBattleFlagsMeaning=1, so a test asserting on "the"
            # HP has to choose -- which is the whole reason both are published.
            {"slot": 0, "id": 1, "player": True, "name": "Zidane", "hp": 420, "hp_max": 600,
             "hp_raw": 420, "hp_max_raw": 600, "mp": 30, "mp_max": 40, "atb": 0, "atb_max": 6000,
             "can_act": True, "alive": True, "targetable": True, "level": 5, "status": "0"},
            {"slot": 1, "id": 2, "player": True, "name": "Vivi", "hp": 0, "hp_max": 380,
             "hp_raw": 0, "hp_max_raw": 380, "mp": 12, "mp_max": 20, "atb": 0, "atb_max": 6000,
             "can_act": False, "alive": True, "targetable": True, "level": 4, "status": "0"},
            {"slot": 4, "id": 16, "player": False, "name": "Masked Man", "hp": 1200,
             "hp_max": 1200, "hp_raw": 11200, "hp_max_raw": 11200, "mp": 0, "mp_max": 0,
             "atb": 3000, "atb_max": 6000, "can_act": True, "alive": True, "targetable": True,
             "level": 9, "status": "0"},
        ]

    #: What the stand-in's party can do. Shapes and TRAPS, not real FF9 ids: an Ability command
    #: that is a sub-menu rather than a move (type 1), an ability that is learned but not castable
    #: (enabled false), an item that targets the dead, and a command the HUD would not draw
    #: (offered false) -- each of which the driver has to refuse for its own distinct reason.
    MENU_COMMANDS = [
        {"menu": 0, "id": 1, "type": 0, "target": 2, "for_dead": False, "sub": 176,
         "offered": True, "name": "Attack"},
        {"menu": 1, "id": 2, "type": 4, "target": -1, "for_dead": False, "sub": 177,
         "offered": True, "name": "Defend"},
        {"menu": 2, "id": 4, "type": 1, "target": -1, "for_dead": False, "sub": 0,
         "offered": True, "name": "Blk Mag"},
        {"menu": 3, "id": 5, "type": 1, "target": -1, "for_dead": False, "sub": 0,
         "offered": False, "name": "Swd Art"},
        {"menu": 4, "id": 8, "type": 2, "target": -1, "for_dead": False, "sub": 0,
         "offered": True, "name": "Item"},
    ]
    MENU_ABILITIES = [
        {"menu": 2, "sub": 20, "mp": 6, "enabled": True, "target": 2, "for_dead": False,
         "name": "Fire"},
        {"menu": 2, "sub": 21, "mp": 6, "enabled": False, "target": 2, "for_dead": False,
         "name": "Blizzard"},
        # TargetType.AllEnemy: the engine's cursor for this is the GROUP, so a single target id
        # would be a command the UI could never have produced.
        {"menu": 2, "sub": 22, "mp": 18, "enabled": True, "target": 8, "for_dead": False,
         "name": "Meteor"},
    ]
    MENU_ITEMS = [
        {"sub": 1, "count": 9, "target": 1, "for_dead": False, "name": "Potion"},
        {"sub": 2, "count": 2, "target": 1, "for_dead": True, "name": "Phoenix Down"},
    ]

    def _collect_menus(self, slot: int) -> None:
        """The `menus` verb: refuse what the engine refuses, then stamp what it collected."""
        if not self.commands_enabled:
            raise RuntimeError("menus: the battle is not asking for commands yet")
        if slot < 0 or slot >= 32:
            raise RuntimeError("menus needs a party slot (0-31)")
        unit = next((u for u in self.battle_units if u["slot"] == slot), None)
        # ⚠ CollectNetMenus indexes _abilityDetailDict unguarded, so a slot with no party member --
        # or one asked during the battle intro -- throws in the engine. Modelled as the refusal the
        # agent turns it into, because a scenario has to be able to hit it.
        if unit is None or not unit.get("player"):
            raise RuntimeError(f"menus: slot {slot} has no ability detail yet")
        self.battle_menu = {
            "slot": slot, "epoch": self.battle_epoch,
            "commands": [dict(c) for c in self.MENU_COMMANDS],
            "abilities": [dict(a) for a in self.MENU_ABILITIES],
            "items": [dict(i) for i in self.MENU_ITEMS],
        }

    def _battle_command(self, slot: int, cmd: int, sub: int, tar_id: int, cursor: int,
                        site: str = "BattleHUD.SendNetCommand < HarnessAgent.Execute") -> None:
        """Commit a command for a slot -- with the engine's own refusals, then its effect.

        ⚠ THE REFUSALS ARE THE POINT. SendNetCommand returns false for an enemy slot and for a slot
        whose turn is already spent, and a stand-in that accepted everything would let a driver bug
        through that the real engine rejects. What it does NOT model is the local-slot refusal:
        that one the agent now dissolves with SetIdle() before calling, so from here the slot is
        already free.
        """
        # ⚠ The guard that would have saved a frozen fight: a command queued on a battle still in
        # its opening camera wedges it solid -- no HUD, no ATB, the intro camera held indefinitely.
        if not self.commands_enabled:
            raise RuntimeError("battlecmd: the battle is not asking for commands yet")
        unit = next((u for u in self.battle_units if u["slot"] == slot), None)
        if unit is None:
            raise RuntimeError(f"battlecmd: the HUD refused the command for slot {slot} -- "
                               f"there is no unit in slot {slot}")
        if not unit.get("player"):
            raise RuntimeError(f"battlecmd: the HUD refused the command for slot {slot} -- "
                               f"slot {slot} is an ENEMY; only party slots take commands")
        if slot in self.battle_done:
            raise RuntimeError(f"battlecmd: the HUD refused the command for slot {slot} -- "
                               f"a command is already in flight for this slot")
        if self._nb_r9(slot, cmd, site):
            # [ff9mapkit netsync B4] s101 R9: inside a live diorama SetCommand refuses the enqueue at its head -- the HUD's
            # bookkeeping around it still runs (the slot done, the HUD idle: the verb ACKS), the swing never plays
            self.battle_done.append(slot)
            if self.battle_turn == slot:
                self.battle_turn = -1
                self._close_battle_cursor()
            return
        self.battle_commands.append([slot, cmd, sub, tar_id, cursor])
        self.battle_done.append(slot)
        if self.battle_turn == slot:
            self.battle_turn = -1           # SetIdle: the HUD stops asking
            self._close_battle_cursor()
        unit["atb"] = 0
        # [ff9mapkit netsync s133] + the sub and the cursor (the action-start lane's START carries them)
        self.battle_pending.append([self.frame + self.cmd_resolve_frames, slot, cmd, tar_id, sub, cursor])

    def _resolve_commands(self) -> None:
        """Execute the commands whose time has come, then hand their slots back.

        The delay is not decoration: between committing and resolving, the slot sits in
        InputFinishList and the engine REFUSES a second command for it. Collapsing the two would
        make the stand-in accept something the real game rejects.
        """
        for entry in [e for e in self.battle_pending if e[0] <= self.frame]:
            self.battle_pending.remove(entry)
            _, slot, cmd, tar_id = entry[:4]
            sub, cursor = (entry[4], entry[5]) if len(entry) > 5 else (0, 0)
            # Only Attack and Fire do damage here; Defend and items resolve harmlessly. That is
            # enough for a fight to actually END, which is what makes fight() testable at all.
            hits = []
            if cmd in (1, 4):
                damage = 260 if cmd == 1 else 400
                for target in self.battle_units:
                    if tar_id & target["id"] and target["alive"]:
                        target["hp"] = max(0, target["hp"] - damage)
                        target["hp_raw"] = max(0, target["hp_raw"] - damage)
                        hits.append((target, damage))
                        if target["hp"] == 0:
                            target["alive"] = False
                            target["targetable"] = False
            else:
                hits = [(t, 0) for t in self.battle_units if tar_id & t["id"]]
            self._act_command(slot, cmd, sub, tar_id, cursor, hits)
            if slot in self.battle_done:
                self.battle_done.remove(slot)
            if slot in self.battle_ready:
                self.battle_ready.remove(slot)
        self._script_latch()
        self._settle_battle()

    def _script_latch(self) -> None:
        """`battle_script_end`'s latch (H9): ONCE a battle, the first time the named unit's ``hp_raw`` is at or below
        ``hp_raw_le`` after a command resolves, the end is due ``after_frames`` later with ``result`` -- whoever is
        standing then (:meth:`_step_battle` ends it)."""
        se = self.battle_script_end
        if se is None or self._script_latched:
            return
        unit = next((u for u in self.battle_units if u.get("name") == se["unit"]), None)
        if unit is not None and int(unit["hp_raw"]) <= int(se["hp_raw_le"]):
            self._script_latched = True
            self._script_end = (self.frame + max(0, int(se.get("after_frames", 0))), int(se["result"]))

    def _race_end(self, op: str) -> None:
        """`battle_end_on_command`: as its ``n``-th step ``op`` of the battle arrives, the battle ends first, and the
        step meets whatever that end left -- or, with ``after``, the step runs and the end is due ``after`` frames on
        (:meth:`_step_battle` ends it, after the drain)."""
        race = self.battle_end_on_command
        if race is None or not self.battle_active or op != race.get("op", "battlecmd"):
            return
        self._race_steps += 1
        if self._race_steps == int(race.get("nth", 1)):
            if race.get("after") is None:
                self.end_battle(int(race["result"]))
            else:
                self._race_due = (self.frame + max(0, int(race["after"])), int(race["result"]))

    def _settle_battle(self) -> None:
        """End the fight when one side is gone. ⚠ Never under isDebug -- the diorama cannot end."""
        if not self.battle_active or self.battle_debug or self._bexit is not None:
            return
        if not [u for u in self.battle_units if not u["player"] and u["alive"]]:
            self.end_battle(1)
        elif not [u for u in self.battle_units if u["player"] and u["alive"]]:
            self.end_battle(3)

    def _step_battle(self) -> None:
        """One frame of battle: gauges fill, the HUD asks somebody, enemies act, escapes roll. While a `battle_exit`
        end runs, only its phases do (:meth:`_step_battle_exit`); a `battle_script_end` that is due ends the battle."""
        if self._bexit is not None:
            self._step_battle_exit()
            return
        if not self.battle_active:
            return
        if self._script_end is not None and self.frame >= self._script_end[0]:
            result, self._script_end = self._script_end[1], None
            self.end_battle(result)                     # the scripted end: whoever is standing
            return
        if self._race_due is not None and self.frame >= self._race_due[0]:
            result, self._race_due = self._race_due[1], None
            self.end_battle(result)                     # `battle_end_on_command`'s `after` end
            return

        # InitialBattle(): the opening camera ends, the HUD resets its turn bookkeeping, and only
        # THEN does the battle start asking for commands.
        # [ff9mapkit netsync B5] ...never again while a diorama presents the host's end (its injection hid the HUD)
        if not self.commands_enabled and self.frame >= self._intro_until and not self._tutorial \
                and not self._nb_hud_off():
            self.battle_turn = -1
            self.battle_ready = []
            self.battle_done = []
            self.commands_enabled = True
        # ⚠ NOTHING RUNS DURING THE INTRO -- not the gauges, not the enemies, not the escape roll.
        # battle.cs gates BattleMainLoop on btl_phase, and BattleHUD.Update returns early while
        # _commandEnable is false, so the bumpers cannot even set btl_escape_key there. A stand-in
        # that ran combat through its own intro would let the party die before the fight began.
        if not self.commands_enabled:
            return

        # -- the escape roll. _runCounter counts UNBROKEN real seconds; either bumper lifting
        # resets it to zero, which is the defect class this whole model exists to preserve.
        if not self.deaf_bumpers and self._is_held("l1") and self._is_held("r1"):
            self.run_counter += self._dt           # REAL seconds: the frame's, on the virtual clock
            if self.run_counter > 1.0:
                self.run_counter = 0.0
                if self._roll() < self.escape_rate:
                    self.escaping = True
        else:
            self.run_counter = 0.0
        if self.escaping:
            self.end_battle(4)
            self.escaping = False
            return

        self._resolve_commands()
        if not self.battle_active or self._bexit is not None:      # it ended (with `battle_exit`: the fade began)
            return
        # A character who goes down mid-prompt stops being asked -- the HUD's own
        # _unconsciousStateList / RemovePlayerFromAction. Without this the turn would stay pinned
        # to a corpse and every later wait would time out against it.
        if self.battle_turn >= 0:
            asked = next((u for u in self.battle_units if u["slot"] == self.battle_turn), None)
            if asked is None or not asked["alive"]:
                self.battle_turn = -1
                self._close_battle_cursor()

        # [ff9mapkit netsync R3 s113/s114] IsNativeEnableAtb false (the start hold, the Wait freeze): ProcessActiveTime does
        # not run -- no gauge moves, no player turns Ready, no enemy acts
        frozen = self._nb_atb_frozen()
        for unit in ([] if frozen else self.battle_units):
            if not unit["alive"]:
                continue
            unit["atb"] = min(unit["atb_max"], unit["atb"] + self.atb_gain)
            ready = unit["atb"] >= unit["atb_max"]
            if unit["player"]:
                # [ff9mapkit netsync B4] the ReadyQueue's only feeder (ProcessActiveTime -> AddPlayerToReady) runs under
                # !isDebug alone: a diorama's queue fills only through the bench opener (`netsync bmenu open`)
                if ready and unit["slot"] not in self.battle_ready and not self.battle_debug \
                        and unit["slot"] not in self.battle_done and unit.get("can_act", True):
                    self.battle_ready.append(unit["slot"])
            elif ready:
                unit["atb"] = 0
                victim = next((u for u in self.battle_units if u["player"] and u["alive"]), None)
                if victim is not None:
                    victim["hp"] = max(0, victim["hp"] - self.enemy_hit)
                    victim["hp_raw"] = max(0, victim["hp_raw"] - self.enemy_hit)
                    if victim["hp"] == 0:
                        victim["alive"] = False
                    # [ff9mapkit netsync s133] the enemy's EnemyAtk: its START, the hit, its END on the action lane
                    self._act_command(unit["slot"], BW.CMD_ENEMY_ATK, self.act_enemy_sub, int(victim["id"]), 0,
                                      [(victim, self.enemy_hit)])

        # The HUD asks the first ready slot that has not answered -- BattleHUD.UpdatePlayer. [ff9mapkit netsync B4] It skips a
        # GUEST-OWNED slot (IsGuestOwnedSlot: a `guestslots` slot of a selftest own battle -- the loopback guest commands it)
        if self.battle_turn < 0:
            for slot in list(self.battle_ready):
                if slot not in self.battle_done and not self._nb_guest_owned(slot):
                    self.battle_turn = slot
                    self._open_battle_cursor()        # the command list opens on that slot
                    break
        self._settle_battle()

    def _roll(self) -> float:
        """A deterministic pseudo-roll, so a suite does not depend on the clock."""
        self._roll_state = (getattr(self, "_roll_state", 12345) * 1103515245 + 12345) & 0x7FFFFFFF
        return self._roll_state / float(0x7FFFFFFF)

    def end_battle(self, result: int = 1, *, exp: int = 120, gil: int = 88) -> None:
        """Finish the battle. ⚠ Refuses under isDebug, exactly as the engine's auto-end does. With `battle_exit` set
        (H9) the end runs the engine's four phases from here -- the FADE first, the result published at the battle's
        own field (:meth:`_step_battle_exit` runs the rest); without it, today's end: the same field, FieldHUD at
        once. An end already running is not begun again."""
        if self.battle_debug or self._bexit is not None:
            return
        self.battle_result = result
        self.battle_bonus = {"exp": exp, "gil": gil, "ap": 3, "items": 1}
        if self.battle_exit is not None and self.battle_active:
            # (1) the FADE (btl_scrp.cs:785-799: the result set, SEQ_DEFEATCLOSE_FADEOUT begun) -- fldMapNo still the
            # battle's field, the scene still up, the HUD asking nobody
            self._close_battle_cursor()
            self.commands_enabled = False
            self._bexit = ("fade", self.frame + max(0, int(self.battle_exit.get("fade_frames", 0))), result)
            self._exit_mark("fade")
            return
        self.battle_active = False
        self._close_battle_cursor()
        # ⚠ commands_enabled goes false at PHASE_MENU_OFF, but battle_turn does NOT get cleared --
        # the engine leaves it for InitialBattle. That is the stale value the next battle inherits.
        self.commands_enabled = False
        self.ui_state = "FieldHUD"
        self._guest.field_load()               # s96: the battle's return LOADS the field -- the panic unlock re-arms

    def _step_battle_exit(self) -> None:
        """A `battle_exit` end, phase by phase, in the engine's order (research/o3_design.md 0.2 #8): the FADE runs
        out; then ONE call of HonoluluBattleMain.UpdateOverFrame (:721-741) folds a result of 2 into 1 AND sets
        ``fldMapNo`` to the exit field -- the same frame, the scene still up -- and GoToBattleResult (ui BattleResult,
        its InitialEvent hiding every panel); then the scene goes (``battle_active`` False) while the UI still reads
        BattleResult through the load; then FieldHUD in the exit field, a fresh visit, control as ``arrive_control``
        says (the engine zeroes it at every field start: EventEngine.cs:627)."""
        phase, until, result = self._bexit
        if self.frame < until:
            return
        ex = self.battle_exit
        if phase == "fade":
            self.battle_result = 1 if result == 2 else result
            self.field_id = int(ex["field"])
            self.ui_state = "BattleResult"
            self._bexit = ("result", self.frame + 1 + max(0, int(ex.get("result_frames", 0))), result)
            self._exit_mark("over")
        elif phase == "result":
            self.battle_active = False
            self._bexit = ("load", self.frame + max(0, int(ex.get("load_frames", 0))), result)
            self._exit_mark("load")
        else:
            self._bexit = None
            self.ui_state = "FieldHUD"
            self._guest.field_load()               # s96: the exit field's load re-arms the panic unlock
            self.control = bool(ex.get("arrive_control", False))
            self._visit += 1                       # a fresh load: a new visit's actor
            self._in_trigger.clear()
            self._exit_mark("field")

    def _exit_mark(self, phase: str) -> None:
        """One row of `exits`: the phase a `battle_exit` end entered, and what it publishes there."""
        self.exits.append({"phase": phase, "frame": self.frame, "field": self.field_id, "result": self.battle_result,
                           "active": self.battle_active, "ui": self.ui_state})

    # -- test conveniences ---------------------------------------------------------------------
    # -- the story-write trace (s88) -----------------------------------------------------------
    def _story_row(self, kind: str, **kv) -> None:
        """Append one proto-1 row: the common fields, then the kind's own (StoryTrace.BeginRow)."""
        mode = 3 if self.ui_state == "WorldHUD" else 2 if self.battle_active else 1
        fld = self.field_id
        row = {"k": kind, "f": self.frame, "p": self.frame, "m": mode, "fld": fld,
               "don": fld if self.donor is None else self.donor, "sc": self.scenario, **kv}
        with (self.dir / "story.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, separators=(",", ":")) + "\n")
        self.story_rows += 1

    def _story_start(self) -> None:
        if self.story_error is not None:
            raise RuntimeError(f"storytrace: turned itself off earlier ({self.story_error}); re-arm the "
                               f"harness to clear it")
        if self.story_suppress:                     # H13 (opt-in): a re-arm closes the running epoch's counts first
            if self.story_on:                       # (Start: Sync, then Resync's EmitCounts, StoryTrace.cs:170-176),
                self._story_counts()                # and every epoch starts with no site
            self._story_sites.clear()
        self.story_on = True
        self._story_row("e", why="arm")

    def _story_stop(self) -> None:
        if not self.story_on:
            return
        if self.story_suppress:                     # H13 (opt-in): Stop's EmitCounts, before its `off` (:198-202)
            self._story_counts()
        self._story_row("e", why="off")
        self.story_on = False

    def _story_store(self, src: str, byte: int, width: str, new: int, *, bit: int = -1,
                     sid: int = -1, tag: int = -1, ip: int = -1) -> None:
        """A store to the modelled gEventGlobal, and -- when tracing -- its `w` row. Only a script row
        names its writer (StoryTrace.AfterStore): cs/harness rows carry -1 attribution. ``old`` is the variable as
        its width reads it (the row contract): an Int16 signed, so a second store of -1 reads old -1, never 65535."""
        if width == "Bit":
            old = (self.story_bytes[byte] >> (bit & 7)) & 1
            self.story_bytes[byte] = (self.story_bytes[byte] & ~(1 << (bit & 7))) | (new << (bit & 7))
        elif width == "Byte":
            old = self.story_bytes[byte]
            self.story_bytes[byte] = new
        else:
            old = self.story_bytes[byte] | (self.story_bytes[byte + 1] << 8)
            if width == "Int16" and old >= 0x8000:
                old -= 0x10000
            self.story_bytes[byte:byte + 2] = bytes((new & 0xFF, (new >> 8) & 0xFF))
        if not self.story_on:
            return
        script = src == "eb"
        if self.story_suppress and not self._story_site(src, sid if script else -1, tag if script else -1,
                                                         ip if script else -1, byte, width, bit, old, new):
            return                                  # H13 (opt-in): the sink counted it -- no row
        self._story_row("w", src=src, sid=sid if script else -1, uid=sid if script else -1,
                        lvl=0 if script else -1, ip=ip if script else -1, tag=tag if script else -1,
                        add=0, byte=byte, w=width, bit=bit, old=old, new=new, same=int(old == new))

    def _story_site(self, src: str, sid: int, tag: int, ip: int, byte: int, width: str, bit: int, old: int,
                    new: int) -> bool:
        """H13 (research/o5_design.md 3.1), ``story_suppress`` on: the sink's per-site rule (StoryTrace.AfterStore,
        StoryTrace.cs:374-401) -- True when this store's ``w`` row is EMITTED. The SITE is the engine's key ``(fld, m,
        src, sid, tag, ip, byte, w, bit)`` (StoryTrace.cs:101-110), ``fld`` the field id NOW (``fldMapNo``, :374) and
        ``m`` the row's mode, the attribution the row's own (-1 off a script row). Per epoch a site keeps whether it
        emitted a SAME-VALUE row -- only a same-value store sets that (:383-388), so a site whose first store was a
        change still emits its first same-value one -- its changes emitted, at most :data:`STORY_CHANGE_ROWS`
        (:391-394), what it counted (``n``, ``last``: :396-401) and the ``don`` its rows carry (EffectiveFieldId of its
        field: ``fake.donor`` when the site opened). A store not emitted is counted (``story_suppressed``): no row,
        ``story_rows`` unchanged -- the file stays exactly the rows the state block counts."""
        mode = 3 if self.ui_state == "WorldHUD" else 2 if self.battle_active else 1
        key = (self.field_id, mode, src, sid, tag, ip, byte, width, bit)
        site = self._story_sites.get(key)
        if site is None:
            site = self._story_sites[key] = {"same": False, "changes": 0, "n": 0, "last": None,
                                             "don": self.field_id if self.donor is None else self.donor}
        if old == new:
            emit, site["same"] = not site["same"], True
        else:
            emit = site["changes"] < STORY_CHANGE_ROWS
            site["changes"] += int(emit)
        if not emit:
            site["n"] += 1
            site["last"] = new
            self.story_suppressed += 1
        return emit

    def _story_counts(self) -> None:
        """H13: the running epoch's counts closed (StoryTrace.EmitCounts, StoryTrace.cs:540-557) -- one ``c`` row per site
        that counted a store, in site-creation order (the reader never reads their order), stamped with the SITE's
        ``fld``/``don``/``m`` and the flush's ``f``/``p``/``sc`` -- then the site table cleared, as the engine clears it
        at every epoch (Resync, Stop: :199, :532)."""
        for (fld, m, src, sid, tag, ip, byte, width, bit), site in self._story_sites.items():
            if site["n"]:
                self._story_row("c", m=m, fld=fld, don=site["don"], src=src, sid=sid, tag=tag, ip=ip, byte=byte,
                                w=width, bit=bit, n=site["n"], last=site["last"])
        self._story_sites.clear()

    def _warp_writes(self, entrance: int, scenario: int) -> None:
        """The debug warp's own writes (Ff9mkDebugMenu.ServicePendingWarp): ``entrance`` (when >= 0) as Int16 at byte
        2 (FieldEntrance) and ``scenario`` (when >= 0) as UInt16 at bytes 0-1 (ScenarioCounter, also the published
        ``scenario``), straight into gEventGlobal before the map changes -- no script and no store hook runs, so a
        trace sees them only through its residue net: one ``r`` row (``why`` "frame") per byte that changed,
        stamped with the field he is warping FROM (rung 1: "seen in field 70 before the load")."""
        before = bytes(self.story_bytes[0:4])
        if scenario >= 0:
            v = scenario & 0xFFFF
            self.story_bytes[0:2] = bytes((v & 0xFF, v >> 8))
            self.scenario = scenario
        if entrance >= 0:
            v = entrance & 0xFFFF                      # Int16, two's complement
            self.story_bytes[2:4] = bytes((v & 0xFF, v >> 8))
        if not self.story_on:
            return
        for b in range(4):
            if self.story_bytes[b] != before[b]:
                self._story_row("r", byte=b, old=before[b], new=self.story_bytes[b], why="frame")

    def _watched_bit(self, bit: int) -> bool:
        """A watched bit as the agent publishes it: read from the modelled gEventGlobal (`story_bytes`), which the
        ``flag`` verb, ``byte`` and :meth:`script_store` all write -- so a script's store shows in ``flags``."""
        byte = bit >> 3
        return 0 <= byte < len(self.story_bytes) and bool((self.story_bytes[byte] >> (bit & 7)) & 1)

    def script_store(self, sid: int, tag: int, ip: int, byte: int, width: str, new: int, *,
                     bit: int = -1) -> None:
        """Model a field script's store (an ``eb`` row). ``width`` is ``Bit`` / ``Byte`` / ``UInt16``."""
        self._story_store("eb", byte, width, new, bit=bit, sid=sid, tag=tag, ip=ip)

    def story_fault(self, why: str = "story.jsonl has not accepted an append") -> None:
        """The tracer turning itself off (StoryTrace.Fail): off, no `off` epoch, the reason published."""
        self.story_on = False
        self.story_error = why

    # -- co-op (netsync) benches ---------------------------------------------------------------
    def _cap(self, name: str) -> bool:
        """[ff9mapkit netsync F3.3] Does this stand-in's engine have the F3.3 capability `name` (:data:`NETSYNC_F33_CAPS`)?
        Only an F3.2-contract engine can: the F3 lockstep has none."""
        return self.netsync_dialogue == "authority" and name in self.netsync_caps

    def _netsync_subverbs(self) -> tuple:
        """The sub-verbs this stand-in's agent has, in its order -- the list its "unknown sub-verb" refusal prints."""
        if self.netsync_dialogue != "authority":
            return NETSYNC_SUBVERBS_F3
        return netsync_subverbs(self.netsync_caps)

    def _netsync(self, args: list[str]) -> None:
        """The agent's `netsync` verb: the same gates, the same refusal texts, the same state -- for the contract
        :attr:`netsync_dialogue` names (HarnessAgent `case "netsync"`; s96 for "authority", s84/s85 for None) and, under
        "authority", the F3.3 capabilities :attr:`netsync_caps` names (s97 `dioboot`/`dioleave`, s98 `host`, s99
        `tap-record`/`replay`)."""
        sub = args[0].lower() if args else ""
        ns = self.netsync
        authority = self.netsync_dialogue == "authority"
        flag = (args[1] if len(args) > 1 else "1") != "0"
        int_min = -2 ** 31

        def arg(i: int, default: int) -> int:             # the agent's Arg(s, i, default): Int32.TryParse, else default
            try:
                v = int(args[i])
            except (IndexError, ValueError):
                return default
            return v if -2 ** 31 <= v < 2 ** 31 else default   # an Int32 overflow fails TryParse too

        def out_of_range(param: str, message: str) -> RuntimeError:
            # the agent's `throw new ArgumentOutOfRangeException(param, message)`: under the game's Mono its Message is
            # message + NewLine + "Parameter name: " + param (Windows: CRLF) -- NOT "<param>: <message>"
            return RuntimeError(f"{message}\r\nParameter name: {param}")

        known = self._netsync_subverbs()
        if sub not in known:
            raise RuntimeError(f"netsync: unknown sub-verb '{sub}' ({'|'.join(known)})")
        if sub == "selftest":
            if flag:
                if ns["enabled"] and ns["role"] != "selftest":
                    raise RuntimeError(f"netsync selftest: co-op is configured live (role={ns['role']}) "
                                       f"-- refusing to override a real session")
                ns.update(enabled=True, role="selftest", instance=True, selftest=True, forced=True)
            else:
                self._selftest_release()        # HarnessSelfTest(false) itself -- not the diorama-aware release
            # [ff9mapkit netsync F3.3] an explicit role call supersedes a release still waiting on a diorama's teardown
            self._dio_release_pending = False
        elif sub in ("bench", "l1", "hostscene", "lock", "stale"):
            if not ns["selftest"]:
                raise RuntimeError(f"netsync {sub}: needs the selftest role (netsync selftest 1)")
            bnop = args[1].lower() if len(args) > 1 else ""
            if sub == "bench" and bnop in ("lapse", "handback") and "handback" in self._nb_caps():
                # [ff9mapkit netsync B4] s110: two NAMED ops of `bench` (an older agent's Arg() reads them as `bench 1`)
                self._nb_bench_named(bnop, args, arg, int_min, out_of_range)
                return
            r3_op = {"intro": "intro", "cfg": "intro", "swirl": "swirl", "waitparity": "waitparity",
                     "ctl": "waitparity", "boot": "starthold", "starthold": "starthold"}.get(bnop)
            if sub == "bench" and r3_op is not None and r3_op in self._nb_caps():
                # [ff9mapkit netsync R3] s111-s114's named ops (the same hazard: an older agent reads each as `bench 1`)
                self._nb_bench_r3(bnop, args, arg, out_of_range)
                return
            key = "l1" if sub == "hostscene" else sub
            if key == "l1" and flag and not ns["l1"]:
                self._guest.scene_nonce = (self._guest.scene_nonce + 1) & 0xFF   # BenchSceneEdge: one per rise
            ns[key] = flag
            if sub == "l1" and not flag and not authority:
                ns["l1_pinned"] = False
                ns["l1_forced_control"] = False
        elif sub == "unlock":
            # the ~ menu panic unlock (HarnessReleaseDialogLock): THIS field, until the next field load
            if not ns["instance"]:
                raise RuntimeError("netsync unlock: no co-op client in this process")
            if not (ns["selftest"] and ns["bench"]):
                raise RuntimeError("netsync unlock: needs a live followed session (or the selftest field-gate bench)")
            self._guest.unlock_field = self.field_id
        elif sub in ("click", "drag"):
            # the mouse/touchpad seams (DialogManager.OnClick / OnDrag): stock seams, so no role gate
            if not self._dialog_open():
                raise RuntimeError(f"netsync {sub}: no dialogue window is open")
            if sub == "click":
                if self.disable_mouse_for_menus:
                    raise RuntimeError("netsync click: [Control] DisableMouseForMenus is on -- a click never "
                                       "reaches the dialogue")
                if self._guest_suppress() or self.choice is not None:
                    return          # swallowed under the lock; a choice window takes no click (GetChoiceDialog)
                if not self._beats and self.texts and not self.dialog_inh:
                    # DialogManager.OnClick -> OnKeyConfirm: a plain say() window PAGES (Dialog.OnKeyConfirm -> Hide ->
                    # the next sub-page, or the close); an [NFOC] one ignores it (ignoreInputFlag)
                    self._dialog_tap(KIND_ADV)          # [ff9mapkit netsync F3.3] R9: Dialog.OnKeyConfirm's host tap
                    self.texts = self.texts[1:]
                    self.raw_texts = self.raw_texts[1:] if self.raw_texts else []
                    self._dialog_page += 1
                    return
                self._menu_step("confirm")          # the window's own OnKeyConfirm, as a real click lands
            else:
                dy = arg(1, 0)
                if dy == 0:
                    raise out_of_range("netsync drag", "needs a non-zero <dy> (|dy| > 50 moves a choice)")
                if self.choice is None or self._guest_suppress():
                    return          # no choice to move, or a locked one (IsGuestLockedChoice)
                if dy < -50:
                    self._menu_step("down")         # MoveCurrentChoice(1)
                elif dy > 50:
                    self._menu_step("up")
        elif sub in ("advance", "choice", "unmatched"):
            if sub == "unmatched":
                win, text = 15, 0xFFFF              # a key no real window can have
            elif not self._dialog_open():
                raise RuntimeError(f"netsync {sub}: no dialogue window is open")
            else:
                win, text = self.dialog_id, self.dialog_text_id
            idx = arg(1, -1) if sub == "choice" else 0xFF
            if sub == "choice" and idx < 0:
                raise out_of_range("netsync choice", "needs a choice index")
            if not ns["instance"]:
                raise RuntimeError("netsync: no co-op client in this process (netsync selftest 1 first)")
            if not ns["selftest"]:
                raise RuntimeError(f"netsync: role is '{ns['role']}' -- the dialog bench needs the selftest role")
            if not ns["bench"]:
                raise RuntimeError("netsync: the field-gate bench is OFF (netsync bench 1)")
            if authority:
                if not ns["lock"]:
                    raise RuntimeError("netsync: the bench dialogue lock is OFF (netsync lock 1) -- host events "
                                       "feed the locked inbox")
                inh = self._inhibited_refusal(win, text)          # [ff9mapkit netsync F3.3] R5: LAW :1369
                if inh is not None:
                    raise RuntimeError(f"netsync: {inh}")
                kind = KIND_CHO if sub == "choice" else KIND_ADV
                if self._cap("ring"):
                    self._bench_append(win, text, kind, idx)      # C3: through the bench host's ring (section 7)
                else:
                    self._guest.ingest(self.field_id, win, text, kind, idx, self._guest_now())
                return
            if not ns["l1"]:
                raise RuntimeError("netsync: the L1 host-event flag is OFF (netsync l1 1) -- L2 engages only under L1")
            seq = self._lockstep_seq
            self._lockstep_seq = (seq + 1) & 0xFF
            if sub == "unmatched":
                ns["pending"] = {"field": self.field_id, "win": 15, "text": 0xFFFF,
                                 "kind": 0, "index": 0xFF, "seq": seq}
                ns["wait_armed"] = True
                self._wait_since_frame = self.frame
                return
            if sub == "choice":
                self.choice = None
                self.menu_entries = []
            # MATCHED: the engine drives the window's own OnKeyConfirm -- one page turns, the frame
            # is consumed, and with the window closed nothing is left under lockstep.
            if self.texts:
                self.texts = self.texts[1:]
                self.raw_texts = self.raw_texts[1:] if self.raw_texts else []
            ns.update(applied_seq=seq, pending=None, suppress=False, align_win=-1, align_text=-1)
        elif sub == "talk":
            # F3.1: the guest-side replay of a host's press-fired talk, by object uid (solo bench). The agent's order:
            # a missing / negative / unparsable uid first (Arg -> -1), then HarnessInjectTalk's gates, then the range
            uid = arg(1, -1)
            if uid < 0:
                raise out_of_range("netsync talk", "needs an object uid")
            if not ns["instance"]:
                raise RuntimeError("netsync talk: no co-op client in this process (netsync selftest 1 first)")
            if not ns["selftest"]:
                raise RuntimeError(f"netsync talk: role is '{ns['role']}' -- the bench needs the selftest role")
            if not ns["bench"]:
                raise RuntimeError("netsync talk: the field-gate bench is OFF (netsync bench 1)")
            if uid > 0xFFFF:
                raise RuntimeError(f"netsync talk: uid {uid} is outside 0..65535")
            self.last_talk_uid = uid            # the stand-in's own receipt -- NO engine publishes it
        elif sub == "dioboot":
            # [ff9mapkit netsync F3.3] DIO-1: the ~ menu's diorama "Boot" (selftest role, a live field, a registered scene)
            if not ns["selftest"]:
                raise RuntimeError("netsync dioboot: needs the selftest role (netsync selftest 1)")
            if self._dio["booted"]:
                raise RuntimeError("netsync dioboot: a diorama is already booted")
            if not self._live_field():
                raise RuntimeError("netsync dioboot: boots from a live field only (the ~ menu offers it nowhere else)")
            scene = arg(1, -1)
            if scene < 0 or scene not in self.battle_scenes:
                raise out_of_range("netsync dioboot", "needs a battle scene id registered on this install")
            wire, rand, wire_bench = -1, False, False
            if "intro" in self._nb_caps():
                # [ff9mapkit netsync R3 s111] `dioboot <scene> [pattern] [wire] [skip|play|own] [rand]` (the agent's dioTok:
                # the tokens start at args[2] when it is not an integer, else at args[3]); an older agent ignores them
                tok = 2 if len(args) > 2 and arg(2, int_min) == int_min else 3
                for k in range(tok, len(args)):
                    dt = args[k].lower()
                    if dt in ("skip", "play", "own"):
                        wire = {"skip": 1, "play": 0, "own": -1}[dt]
                    elif dt == "rand":
                        rand = True
                    elif dt == "wire":
                        wire_bench = True
                    else:
                        raise out_of_range("netsync dioboot", "expected `netsync dioboot <scene> [pattern] [wire] "
                                           f"[skip|play|own] [rand]`, got '{args[k]}'")
                if wire_bench:
                    if rand:
                        raise out_of_range("netsync dioboot", "`wire` boots the wire bench, whose header is always a "
                                           "random encounter: drop `rand`")
                    # WireBenchBoot: the fabricated header (flags 0x01, or 0x0D / 0x09) through the parse -> WireIntro;
                    # its header is a random encounter
                    flags = 0x01 | (0 if wire < 0 else BW.CAP_INTRO_MIRROR | (BW.FLAG_INTRO_SKIPPED if wire == 1 else 0))
                    wire, rand = BW.wire_intro(flags), True
            self._dio_boot(scene, wire_intro=wire, rand=rand)
            if not self._dio["booted"]:
                raise RuntimeError("netsync dioboot: refused (Memoria.log names why: [NetSync] diorama boot REFUSED)")
            self._dio_by_harness = True
        elif sub == "dioleave":
            # [ff9mapkit netsync F3.3] DIO-1: the ~ menu's "Leave diorama" -- request-only, the teardown lands later
            if not self._dio["booted"]:
                raise RuntimeError("netsync dioleave: no diorama is booted")
            self._dio_leave()
            if not self._dio_leave_recently():
                raise RuntimeError("netsync dioleave: deferred -- a scene fade is in flight; retry")
        elif sub == "host":
            # [ff9mapkit netsync F3.3] C3 R9: the bench HOST. Every argument after the op must be an Int32 (refused before
            # any gate), then HarnessBenchHost's gates, then the op's own (NetSyncClient.BenchHostOp)
            op = args[1].lower() if len(args) > 1 else ""
            for k in range(2, len(args)):
                if arg(k, int_min) == int_min:
                    raise out_of_range("netsync host", f"argument '{args[k]}' is not an integer")
            argc = len(args) - 2 if len(args) > 2 else 0
            if not ns["instance"]:
                raise RuntimeError("netsync host: no co-op client in this process (netsync selftest 1 first)")
            if not ns["selftest"]:
                raise RuntimeError(f"netsync host: role is '{ns['role']}' -- the bench host needs the selftest role")
            if not ns["bench"]:
                raise RuntimeError("netsync host: the field-gate bench is OFF (netsync bench 1)")
            if not ns["lock"]:
                raise RuntimeError("netsync host: the bench dialogue lock is OFF (netsync lock 1) -- the bench host "
                                   "rides the locked lane")
            self._bench_host_op(op, argc, arg(2, -1), arg(3, -1), arg(4, -1))
        elif sub == "tap-record":
            # [ff9mapkit netsync F3.3] R9: this copy's real host taps onto a fresh tape (they record only with the lock OFF)
            if not ns["instance"]:
                raise RuntimeError("netsync tap-record: no co-op client in this process (netsync selftest 1 first)")
            if not ns["selftest"]:
                raise RuntimeError(f"netsync tap-record: role is '{ns['role']}' -- the tap bench needs the selftest role")
            if not ns["bench"]:
                raise RuntimeError("netsync tap-record: the field-gate bench is OFF (netsync bench 1)")
            on = arg(1, 1) != 0
            if on:
                self._tape.clear()
                self._key_tap_tick = None
            self._tap_record = on
        elif sub == "replay":
            # [ff9mapkit netsync F3.3] R9: `replay`, `replay 1|0` and `replay paced 1|0` are one verb; anything else is
            # refused BEFORE the gates (C3KEYS-6)
            ri = 2 if len(args) > 1 and args[1].lower() == "paced" else 1
            paced = arg(ri, int_min) if len(args) > ri else 1
            if paced not in (0, 1) or len(args) > ri + 1:
                raise out_of_range("netsync replay", f"expected `netsync replay [[paced] 1|0]`, got '{' '.join(args[1:])}'")
            if not ns["instance"]:
                raise RuntimeError("netsync replay: no co-op client in this process (netsync selftest 1 first)")
            if not ns["selftest"]:
                raise RuntimeError(f"netsync replay: role is '{ns['role']}' -- the replay bench needs the selftest role")
            if not ns["bench"]:
                raise RuntimeError("netsync replay: the field-gate bench is OFF (netsync bench 1)")
            if not ns["lock"]:
                raise RuntimeError("netsync replay: the bench dialogue lock is OFF (netsync lock 1) -- the replay feeds "
                                   "the bench host's lane")
            if not self._tape:
                raise RuntimeError("netsync replay: the tape is empty (netsync tap-record 1, play the scene with the lock "
                                   "OFF, then tap-record 0)")
            self._replay = [dict(t) for t in self._tape]
            self._tap_record = False
            self._replay_next = 0
            self._replay_paced = paced != 0
            self._replay_start = self._guest_now()
        elif sub in ("guestslots", "bcmd", "hostgates", "containment", "bctl", "bmenu", "bbench", "endbench",
                     "actbench"):
            # [ff9mapkit netsync B4] [ff9mapkit netsync B5] the battle co-op benches (s100-s110; s133 `actbench`)
            self._battle_bench_verb(sub, args, arg, out_of_range)

    def _release_netsync(self) -> None:
        """ReleaseNetsyncOverride, on `reset`, disarm and fault. [ff9mapkit netsync F3.3] DIO-1: a diorama THIS harness
        booted is a leak too -- its Leave is requested (the teardown lands later) and the selftest role is HELD until it
        tears down (:meth:`_step_diorama` finishes the release), so no watcher fence is switched off under it."""
        if self._dio_by_harness and self._dio["booted"]:
            if not self._dio_leave_recently():
                self._dio_leave()
            self._dio_retry_rt = self.rt
            self._dio_release_pending = True
            return
        self._dio_by_harness = False
        self._dio_release_pending = False
        self._selftest_release()

    def _selftest_release(self) -> None:
        """HarnessSelfTest(false), on `selftest 0` and from the release: the override and every bench lever go, and the
        guest forgets its lock, inbox and panic unlock (``orphan_closes`` is the process's telemetry and stays). A session
        the harness did not force is left alone. [ff9mapkit netsync F3.3] ApplyConfigChange -> ResetDialogLockstepState:
        the bench host's ring restarts under a NEW epoch (seq from 1), the guest's lane half goes (epoch -1, gaps and the
        KEY counters 0), the bench host's levers, the tape and a running replay with it; the key tick and the last masked
        reader are process statics and stay."""
        self._nb_release()          # [ff9mapkit netsync B4] on EVERY path, above the forced-role return (HarnessSelfTest)
        ns = self.netsync
        if not ns["forced"]:
            return
        ns.update(enabled=False, role="selftest", instance=True, selftest=False, forced=False,
                  bench=False, l1=False, l1_pinned=False, l1_forced_control=False, suppress=False,
                  align_win=-1, align_text=-1, applied_seq=-1, wait_armed=False, wait_ms=-1,
                  pending=None, lock=False, stale=False)
        self._guest.release()
        self._bench.release()
        self._tap_record = False
        self._tape.clear()
        self._replay, self._replay_next = [], 0
        self._key_tap_tick = None

    def _netsync_doc(self) -> dict:
        ns = self.netsync
        if self.netsync_dialogue == "authority":
            g = self._guest
            doc = {k: ns[k] for k in ("enabled", "role", "instance", "selftest", "forced", "bench", "l1", "lock",
                                      "stale")}
            doc.update(lock_engaged=g.engaged, unlocked=g.unlock_field >= 0, suppress=self._guest_suppress())
            doc.update(NETSYNC_F3_PINNED)
            doc.update(windows=self._guest_windows(), inbox=g.inbox_doc(self._guest_now()),
                       host_settled_ms=g.settled_ms, orphan_closes=g.orphan_closes, chip=g.chip)
            if self._cap("ring"):
                doc.update(self._ring_doc())
            if self._cap("keys"):
                doc.update(self._keys_doc())
            if self._cap("diorama"):
                doc["diorama"] = self._diorama_doc()
            caps = self._nb_caps()
            if "grace" in caps:
                doc["session"] = self._session_doc()    # [ff9mapkit netsync R3 s120] between `diorama` and `battle`
            if "menurefusal" in caps:
                doc["menu_refusal"] = self._menu_refusal_doc()   # [ff9mapkit netsync R3 s121] ...after `session`
            if "gates" in caps:
                doc["battle"] = self._nb_doc()          # [ff9mapkit netsync B4] s100+
            return doc
        if ns["wait_armed"]:
            ns["wait_ms"] = int((self.frame - self._wait_since_frame) * 1000 / self.fps)
            if ns["wait_ms"] > ns["wait_limit_ms"]:
                ns.update(pending=None, wait_armed=False, wait_ms=-1)
        doc = {k: v for k, v in ns.items() if k not in ("lock", "stale")}
        return dict(doc, pending=None if ns["pending"] is None else dict(ns["pending"]))

    def _ring_doc(self) -> dict:
        """[ff9mapkit netsync F3.3] AppendRing: the guest's view of section 7 (-1 = absent: no section on the lane, not
        baselined, no epoch seen) and the bench host's levers. `wire` is the engine's constant (NetSyncWire.Version)."""
        g, b = self._guest, self._bench
        v = g.view if g.view_valid else None
        return {"wire": 14, "epoch": g.epoch if g.epoch_have else -1, "head_seq": v["head"] if v else -1,
                "last_seen": g.last_seen if g.baselined else -1, "gaps": g.gaps,
                "heartbeat": v["hb"] if v else -1, "host_stalled": g.stalled, "host_flags": v["flags"] if v else -1,
                "host_open": [{"win": o["win"], "text": o["text"], "cursor": -1 if o["cursor"] is None else o["cursor"],
                               "page": o["page"], "flags": o["flags"]} for o in (v["open"] if v else [])],
                "cursor": g.mirror_cursor, "key_ignored": g.key_ignored,
                "host_frozen": b.frozen, "host_menu": b.menu, "host_battle": b.battle}

    def _keys_doc(self) -> dict:
        """[ff9mapkit netsync F3.3] AppendKeys: the script-key relay (R5) and the tap-record bench (R9)."""
        g, now = self._guest, self._guest_now()
        keys = [{"seq": k["seq"], "field": k["fld"], "uid": k["uid"], "bits": k["compact"],
                 "cursor": -1 if k["cursor"] is None else k["cursor"], "age_ms": now - k["seen"],
                 "state": "active" if k["active"] else "stored" if k["released"] else "pending"} for k in g.keys[:8]]
        return {"key_tick": self._key_tick, "key_hold": self._key_hold_published(), "key_reader": self._key_reader,
                "keys": keys, "key_served": g.key_served, "key_expired": g.key_expired, "key_gaveup": g.key_gaveup,
                "key_taps": self._key_taps, "tap_record": self._tap_record, "tape": len(self._tape),
                "replay_left": len(self._replay) - self._replay_next}

    def _diorama_doc(self) -> dict:
        """[ff9mapkit netsync F3.3] AppendDiorama -- `resuming` = a WARM return's battle-return bracket still open."""
        d = self._dio
        doc = {"booted": d["booted"], "boot": d["boot"], "boot_why": d["boot_why"], "boot_field": d["boot_field"],
               "boot_x": d["boot_x"], "boot_z": d["boot_z"], "primed": d["primed"], "returns": d["returns"],
               "last_return": d["last_return"], "last_return_field": d["last_return_field"],
               "resuming": self._dio_warm_return and self._dio_resume_until is not None}
        caps, nb = self._nb_caps(), self._nb
        if "intro" in caps:
            # [ff9mapkit netsync R3 s111] AppendDioramaIntro -- THIS boot only (`wire` -1 between boots); `swirl_frames` the
            # process's own (s112: the `bench swirl local` stand-in while set)
            intro = {"wire": nb.d_wire if d["booted"] else -1,
                     "applied": {1: "skip", 0: "play"}.get(nb.d_applied), "own": {1: "skip", 0: "play"}.get(nb.d_own),
                     "off": not self._nb_intro_on(), "calls": nb.d_calls, "normal_ms": nb.d_normal_ms,
                     "swirl_frames": self._nb_local_swirl() if "swirl" in caps else self.cfg_swirl_frames}
            if "swirl" in caps:                             # [ff9mapkit netsync R3 s112] AppendSwirlClamp
                intro["swirl_clamp"] = {
                    "ini": self.ini_swirl_clamp, "clamp": self._nb_swirl_clamp(),
                    "src": "bench" if nb.swirl_clamp_set else "ini", "bench_local": nb.swirl_local,
                    "diorama": nb.sw_diorama, "own": nb.sw_own, "used": nb.sw_used,
                    "clamped": nb.sw_swirls > 0 and nb.sw_used != nb.sw_own, "dwell_ms": nb.sw_dwell_ms,
                    "swirls": nb.sw_swirls, "dioramas": nb.sw_dioramas, "clamps": nb.sw_clamps}
            doc["intro"] = intro
        if "starthold" in caps:                             # [ff9mapkit netsync R3 s114] AppendDioramaLive
            doc["live"] = {"latched": nb.live_latched and d["booted"], "ms": nb.live_ms, "nonce": nb.live_nonce}
        if "holdpeer" in caps:                              # [ff9mapkit netsync R3 s119] AppendDioramaHold
            doc["hold"] = self._diorama_hold_doc()
        return doc

    # -- [ff9mapkit netsync R3 s119-s121] the sitting-A round's guest blocks ------------------------------------------
    def _session_grace_ms(self) -> int:
        """NetSyncClient._sessionGraceMs: [Netsync] SessionGraceMs through the engine's own parse and clamp -- an absent or
        malformed key keeps THAT engine's default ([ff9mapkit netsync s132] 40000 with cap `grace40`, 30000 on s120-s131)."""
        parse = BW.parse_session_grace if "grace40" in self._nb_caps() else BW.parse_session_grace_s120
        return parse(self.ini_session_grace_ms)[0]

    def _diorama_hold_doc(self) -> dict:
        """[ff9mapkit netsync R3 s119] AppendDioramaHold. The watcher runs only for a FOLLOWING guest on a real transport
        (the selftest role returns before DioramaTick): the stand-in has none, so its hold never steps -- `state` / `why`
        null, the counters 0 -- and only the two LIVE reads move: `cap_ms` (DioramaHoldCapMs: s119's 8000, from s120 the
        session grace) and `settle_ms`."""
        grace = self._session_grace_ms() if "grace" in self._nb_caps() else None
        return {"state": None, "since_ms": -1, "cap_ms": BW.hold_cap_ms(grace), "settle_ms": BW.DIORAMA_SETTLE_MS,
                "holds": 0, "resumes": 0, "gaveup": 0, "last_ms": -1, "peer_alive": False, "host_field": -1,
                "terminal": False, "why": None}

    def _session_doc(self) -> dict:
        """[ff9mapkit netsync R3 s120] AppendSession. The outage clock runs only on a GUEST with a transport (SessionTick
        returns at once on a host or the selftest role): the stand-in has neither, so the block sits at rest -- `state`
        "none" with a client instance (null without), no outage, the process counters 0 -- but for the LIVE reads
        (`grace_ms`, `mirroring` = :attr:`story_mirroring`) and the selftest role's own overlay ("off", detail 0, from its
        first tick) and ghost (the mirror beside the player on a field in scope)."""
        inst = bool(self.netsync["instance"])
        return {"grace_ms": self._session_grace_ms(), "state": "none" if inst else None, "left_ms": -1, "out_ms": -1,
                "outages": 0, "resumes": 0, "gaveup": 0, "last_ms": -1, "peer_alive": False, "seen_live": False,
                "mirroring": bool(self.story_mirroring), "ramp_pending": False, "ramp_cause": None,
                "overlay": "off" if inst and self._ovl_composed else None,
                "overlay_detail": 0 if inst and self._ovl_composed else -1,
                "ghost": inst and self._nb_role() and self._selftest_in_scope(), "ghost_held": False}

    def _selftest_in_scope(self) -> bool:
        """NetSyncClient.Update's selftest `inScope` (approximated): on a field (gMode 1, its fieldmap up) -- not the
        title, the world map or a battle."""
        return self.field_id > 0 and not self.battle_active and self.ui_state not in ("Title", "WorldHUD")

    def _menu_key_now(self) -> str | None:
        """NetSyncField.HarnessMenuKeyNow: MenuKeyStep through MenuKeyRoute on the stand-in's UI -- "dialog" under an open
        dialogue window (not paused) or a state with no scene (UIManager.GetSceneFromState)."""
        return BW.menu_key_now(self.menu_control_enable, self.story_mirroring, self.ui_state, self._dialog_open(),
                               self.ui_state == "Pause")

    def _menu_refusal_doc(self) -> dict:
        """[ff9mapkit netsync R3 s121] AppendMenuRefusal (`now` a LIVE read; the rest NetSyncField's process statics)."""
        m = self._menu_refusal
        return {"now": self._menu_key_now(), "count": m.count, "lines": m.lines, "silent": m.silent,
                "last_state": m.last_state, "last_field": m.last_field,
                "age_ms": int((self.rt - m.last_rt) * 1000) if m.armed else -1, "muted": m.muted}

    def _menu_key_press(self) -> bool:
        """[ff9mapkit netsync R3 s121] UIKeyTrigger's Menu key on a MIRRORING guest (s38 Road A: the main menu stays shut).
        Only the scene branch sees it (MenuKeyRoute: under a dialogue window, not paused, the press takes the untouched
        dialogue path); there s121's RefuseMainMenu -- on FieldHUD / WorldHUD the buzz (FF9Sfx 102), a count and ONE line
        per place per process (DeclineOnce; WorldHUD latches its own class on wldMapNo), anywhere else a silent drop,
        counted. An engine before s121 drops the key with no sound, no line and no count. True = the key is spent here; a
        guest that is not mirroring (or a scene's MENUOFF: stock's own silent refusal) falls through to the stand-in."""
        if not self.story_mirroring or not self.menu_control_enable:
            return False
        state = self.ui_state
        if BW.menu_key_route(state in BW.UI_SCENE_STATES, self._dialog_open(), state == "Pause",
                             BW.MENU_KEY_REFUSE_SILENT) == BW.MENU_KEY_DIALOG_PATH:
            return False
        if "menurefusal" not in self._nb_caps():
            return True                                     # s38: dropped -- no buzz, no line, counted nowhere
        verdict = BW.menu_key_step(self.menu_control_enable, True, state)
        m = self._menu_refusal
        place = BW.menu_refusal_place(state, self.field_id, self.world.get("id", -1))
        m.last_state, m.last_field, m.last_rt, m.armed = state, place, self.rt, True
        if verdict == BW.MENU_KEY_REFUSE_SILENT:
            m.silent += 1
            return True
        m.count += 1
        m.muted = bool(self.mute_sfx)
        m.buzzes += 1                                       # FF9Sfx.FF9SFX_Play(102)
        latch = BW.menu_refusal_latch(state)
        if m.latch.get(latch) != place:
            m.latch[latch] = place
            m.lines += 1
            self._mlog(BW.menu_refusal_line(state, place))
        return True

    def _mlog(self, msg: str) -> None:
        """[ff9mapkit netsync R3] One Memoria.Prime.Log.Message line in the game root's Memoria.log: ``dd.MM.yyyy HH:mm:ss
        |M| <msg>``, CRLF as the archived real logs read (.harness-runs/*/Memoria.log). The stand-in writes only the lines a
        modelled R3 bench reads: the selftest proof block's R3 lines, the hand-back lines (s110 / s118) and s121's line --
        [ff9mapkit netsync s133] and the host action-start lane's (battlewire.ActHostLane.lines: the battle's summary, the
        `actbench` lever and tape lines, their release)."""
        stamp = time.strftime("%d.%m.%Y %H:%M:%S")
        path = self.memoria_log
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "ab") as f:
            f.write(f"{stamp} |M| {msg}\r\n".encode("utf-8"))

    def _step_selftest_proof(self) -> None:
        """[ff9mapkit netsync R3] NetSyncClient's selftest branch, the two pieces the round reads: every tick composes the
        overlay "off" (SetOverlay(OvlOff) -- s120's `session.overlay`), and the FIRST tick in scope logs the proof block,
        once per PROCESS. The stand-in writes the R3 lines its capabilities carry, in the engine's order: "battle control
        selftest: OK (33 rows)" from s114 (53 from s118), "diorama watcher selftest: OK (24 rows)" (s119), "session grace
        selftest: OK (31 rows)" (s120), "main menu refusal selftest: OK (14 rows)" (s121), [ff9mapkit netsync s131] "peer
        adopt selftest: OK (20 rows)" (s131). NOT MODELLED: the five lines before them (state-mirror, party-mirror, diorama
        containment, dialogue authority, battle end-block) -- their details are save- and stage-dependent, so a bench that
        reads one stays red here as it always did. [ff9mapkit netsync s131 fix] NO IN-GAME READER of the s119-s131 lines:
        coop_handback_live (S18-PROOF) and coop_battle_start_hold (S14-B2) read the control line alone, and a client-role
        bench (coop_cut_hold's guest) never logs the block -- an older engine's missing line here is the stand-in's red."""
        if not self._nb_role():
            return
        self._ovl_composed = True
        if self._proof_logged or not self._selftest_in_scope():
            return
        self._proof_logged = True
        caps = self._nb_caps()
        rows = []
        if "starthold" in caps:
            rows.append((BW.PROOF_CONTROL,
                         BW.CONTROL_SELFTEST_ROWS if "ownreport" in caps else BW.CONTROL_SELFTEST_ROWS_S114))
        if "holdpeer" in caps:
            rows.append((BW.PROOF_WATCH, BW.WATCH_SELFTEST_ROWS))
        if "grace" in caps:
            rows.append((BW.PROOF_GRACE, BW.GRACE_SELFTEST_ROWS))
        if "menurefusal" in caps:
            rows.append((BW.PROOF_MENU, BW.MENU_SELFTEST_ROWS))
        if "expiredseq" in caps:                            # [ff9mapkit netsync s131] right after the menu refusal's
            rows.append((BW.PROOF_ADOPT, BW.ADOPT_SELFTEST_ROWS))
        if "actstart" in caps:                              # [ff9mapkit netsync s133] right after the peer adopt's
            rows.append((BW.PROOF_ACTION, BW.ACTION_SELFTEST_ROWS))
        if "actreplay" in caps:                             # [ff9mapkit netsync s134] right after the action lane's
            rows.append((BW.PROOF_REPLAY, BW.REPLAY_SELFTEST_ROWS))
        if "acthold" in caps:                               # [ff9mapkit netsync s135] right after the action replay's
            rows.append((BW.PROOF_HOLD, BW.HOLD_SELFTEST_ROWS))
        if "actfallback" in caps:                           # [ff9mapkit netsync s136] right after the hold's
            rows.append((BW.PROOF_FALLBACK, BW.FALLBACK_SELFTEST_ROWS))
        for head, n in rows:
            self._mlog("[NetSync] " + BW.proof_ok(head, n))

    # -- [ff9mapkit netsync B4] [ff9mapkit netsync B5] the battle co-op lane (s100-s105) -------------------------------
    def _nb_caps(self) -> frozenset:
        """The battle co-op capabilities this stand-in's engine has (:data:`NETSYNC_BATTLE_CAPS`) -- none on an F3 engine."""
        if self.netsync_dialogue != "authority":
            return frozenset()
        return frozenset(c for c in NETSYNC_BATTLE_CAPS if c in self.netsync_caps)

    def _nb_role(self) -> bool:
        """NetSyncClient.IsSelfTestRole (`_enabled && _role == "selftest"`)."""
        return bool(self.netsync["enabled"] and self.netsync["selftest"])

    def _nb_gates_on(self) -> bool:
        """NetSyncBattle.HostGatesOn: the lever bites only in the selftest role."""
        return not (self._nb.gates_off_lever and self._nb_role())

    def _nb_containment_on(self) -> bool:
        """NetSyncBattle.ContainmentOn (s101); an engine before s101 has no containment at all."""
        if "containment" not in self._nb_caps():
            return False
        return not (self._nb.containment_off_lever and self._nb_role())

    def _nb_capture_on(self) -> bool:
        """NetSyncBattle.StockCaptureOn (s102); an engine before s102 captures nothing."""
        if "stockmenu" not in self._nb_caps():
            return False
        return not (self._nb.capture_off_lever and self._nb_role())

    def _nb_guest_mode(self) -> int:
        """NetSyncEnd.GuestMode (s104)."""
        return self._nb.guest_mode if self._nb_role() else BW.GUEST_ON

    def _nb_exit_mode(self) -> int:
        """NetSyncEnd.GuestExitMode (s105)."""
        return self._nb.exit_mode if self._nb_role() else BW.EXIT_MODE_ON

    def _nb_host_mode(self) -> int:
        """NetSyncEnd.HostMode (s103)."""
        return self._nb.host_mode if self._nb_role() else BW.MODE_ON

    def _nb_active(self) -> bool:
        """NetSyncDiorama.Active -- a booted diorama whose battle scene is live (the containment predicate)."""
        return bool(self._dio["booted"] and self.battle_active and self.battle_debug)

    def _nb_hud_off(self) -> bool:
        """NetSyncDiorama.EndHudOff: an end presented or held on THIS live diorama, or the guest following the host out
        (s105) -- keyed on Active, so a later battle never inherits it."""
        nb = self._nb
        following = nb.trigger != BW.TRIGGER_NONE and self._nb_exit_mode() == BW.EXIT_MODE_ON
        return bool((nb.presented or following) and self._nb_active())

    def _nb_guest_owned(self, slot: int) -> bool:
        """NetSyncBattle.IsGuestOwnedSlot: a GuestSlots bit, the control lane fresh (MenuStaleMs 2.5 s) -- and, from
        s101, never inside a diorama while containment is on (G2)."""
        nb = self._nb
        if not self.netsync["enabled"] or not nb.guest_slots or not 0 <= slot < 4 or not nb.guest_slots & (1 << slot):
            return False
        if self._nb_active() and self._nb_containment_on():
            return False
        return self.rt - nb.assist_rt < 2.5

    def _nb_doc(self) -> dict:
        """HarnessAgent.AppendNetsyncBattle -- the `netsync.battle` block for this stand-in's capabilities, in the agent's
        key order (absent = an engine without the patch)."""
        caps, nb = self._nb_caps(), self._nb
        role = self._nb_role()
        peer = self._nb_peer_view()
        host = {"gates_off": nb.gates_off_lever and role, "guest_slots": nb.guest_slots,
                "cmd_phase": nb.phase_open, "caps": nb.last_caps, "ready_mask": nb.last_ready,
                "cmd_refused": nb.cmd_refused, "cmd_dropped": nb.cmd_dropped, "cmd_queued": nb.cmd_queued,
                "refused_why": nb.refused_why, "dropped_why": nb.dropped_why, "roster_lag": nb.roster_lag,
                "loop_cmds": len(nb.loop)}
        pdoc = {"live": peer is not None, "seq": peer["seq"] if peer else -1, "nonce": peer["nonce"] if peer else -1,
                "caps": peer["caps"] if peer else -1, "ready_mask": peer["ready"] if peer else -1}
        menu = {"roster_slots": list(nb.roster_slots) if peer is not None and nb.own_epoch is not None else []}
        if "endblock" in caps:
            host.update(end=None if nb.host_end is None else BW.published_end(nb.host_end, with_flee="fleegil" in caps),
                        end_trail=list(nb.host_trail), end_edges=nb.host_edges, end_changes=nb.host_changes,
                        end_mode=BW.HOST_MODE_NAMES[self._nb_host_mode()], end_cmd=nb.cmd_status)
            pdoc.update(end=self._nb_peer_end(), end_trail=list(nb.peer_trail), trailer_bad=nb.trailer_bad,
                        trailer_skipped=nb.trailer_skipped, trailer_why=nb.trailer_why)
        if "manifest" in caps:                              # [ff9mapkit netsync B5] s108
            host.update(manifest=None if nb.host_manifest is None else BW.published_manifest(nb.host_manifest),
                        manifest_bytes=0, manifest_captures=nb.manifest_captures, manifest_skipped=nb.manifest_skipped,
                        manifest_why=None, manifest_mode=BW.MANIFEST_MODE_NAMES[self._nb_manifest_mode()],
                        overflow=False, learned=[])
            pdoc.update(manifest_bad=nb.manifest_bad, manifest_bad_why=nb.manifest_bad_why, manifest_nonce=-1,
                        manifest_rx=nb.manifest_rx,
                        bench_manifest=nb.manifest_preset if nb.template.get("manifest") is not None else 0,
                        bench_manifest_note=nb.manifest_note)
        if "expiredseq" in caps:                            # [ff9mapkit netsync s131] AppendPeerExpired, `peer`'s last key
            pdoc["expired"] = self._peer_lane.doc()
        if "handback" in caps:                              # [ff9mapkit netsync B4] s110
            host["handback"] = self._nb_handback_doc()
            if "waitparity" in caps:                        # [ff9mapkit netsync R3 s113]
                host["handback"]["lapse"]["reserve"] = nb.lapse_armed and nb.lapse_reserve
        if "intro" in caps:                                 # [ff9mapkit netsync R3 s111] AppendHostIntro (LIVE cfg reads)
            host["cfg"] = {"atb": self.cfg_atb, "skip_btl_camera": self.cfg_skipcam, "speed": self.cfg_speed,
                           "swirl_frames": self.cfg_swirl_frames}
            host["intro"] = {"off": not self._nb_intro_on(),
                             "published": -1 if nb.last_caps < 0 else BW.wire_intro(nb.last_caps),
                             "own_skip": nb.own_intro}
        if "waitparity" in caps:                            # [ff9mapkit netsync R3 s113] AppendHostWait
            host["wait"] = {"parity_off": nb.waitparity_off_lever and role, "menu": nb.remote_seen,
                            "open": self._nb_remote_open(), "deep": self._nb_remote_deep(),
                            "legacy_seen": nb.legacy_seen}
        if "starthold" in caps:                             # [ff9mapkit netsync R3 s114] AppendHostStartHold
            host["start_hold"] = self._nb_hold_doc()
        if "fleegil" in caps:                               # [ff9mapkit netsync R3 s116] the host tap's receipt
            host["flee_gil"] = nb.host_flee_gil
        if "containment" in caps:
            menu.update(r9_refused=nb.r9_refused, r9_total=nb.r9_total, r9_cmd=nb.r9_cmd, r9_site=nb.r9_site,
                        guest_owned=sum(1 << s for s in range(4) if self._nb_guest_owned(s)),
                        contained=self._nb_active(), containment_off=nb.containment_off_lever and role)
        if "stockmenu" in caps:
            menu.update(captures=nb.captures, capture_refused=nb.capture_refused, capture_why=nb.capture_why,
                        capture_off=nb.capture_off_lever and role, outbox=len(nb.outbox), bench_open=nb.bench_open,
                        side_refused=nb.side_refused, side_why=nb.side_why,
                        captured=None if nb.captured is None else dict(nb.captured))
        if "content" in caps:                               # [ff9mapkit netsync B4] s106 AppendStockContent
            roster, src = self._nb_menu_roster()
            menu.update(mirrored=self._nb_mirrored_slots(), roster_src=src, roster_sig=BW.roster_sig_text(roster),
                        roster_gen=nb.roster_gen, roster_painted=nb.roster_painted,
                        content_off=(nb.content_off_lever & BW.CONTENT_ALL) if role else 0,
                        content_hits=dict(nb.content_hits), content_faults=nb.content_faults, content_why=None,
                        mute_held=nb.mute_until >= 0, roster=BW.published_roster(roster),
                        bench_roster=dict(nb.bench_info) if nb.bench_roster is not None and nb.bench_info else None)
        if "mirror" in caps:                                # [ff9mapkit netsync B4] s107 AppendStockMirror
            owns, why = self._nb_stock_owns(self._nb_feed_view_live(), self._nb_active())
            if owns:
                gate = self._nb_menu_gate()
                why = None if gate is None else "waiting: " + gate
            pend = min(nb.pend) if nb.pend else None
            menu.update(stock_owns=owns, why=why, knob=1 if self._nb_knob_on() else 0,
                        knob_bench=nb.knob_bench if role else -1, assist_slot=nb.assist_slot,
                        stranded=[w for w in range(4) if nb.stranded_mask & (1 << w)],
                        pending=None if pend is None else {
                            "slot": pend, "wire": nb.pend[pend]["wire"],
                            "ms": int((self.rt - nb.pend[pend]["rt"]) * 1000),
                            "seqs": max(0, (self._nb_feed_seq() - nb.pend[pend]["seq0"]))},
                        pending_mask=sum(1 << s for s in nb.pend), refused=nb.mirror_refused, sent=nb.stock_sent,
                        mirror={"serving": nb.mirror_serving, "open": nb.mirror_mask, "fed": nb.mirror_fed,
                                "accepted": nb.mirror_accepted, "obsolete": nb.mirror_obsolete,
                                "closed": nb.mirror_closed,
                                "no_roster": nb.no_roster_mask, "faulted": nb.mirror_faulted,
                                "fault_why": nb.mirror_fault_why},
                        feed=self._nb_feed_doc())
        if "waitparity" in caps:                            # [ff9mapkit netsync R3 s113] AppendMenuCtl (s114: + the trailer)
            out = nb.ctl_out
            ctl = {"menu": out[1] if out is not None and len(out) > 1 else -1,
                   "hex": None if out is None else BW.hex_bytes(out), "src": nb.ctl_src if out is not None else None}
            if "starthold" in caps:
                trailer = out is not None and len(out) >= 5 and out[2] == BW.CTL_FMT1
                ctl.update(nonce=out[3] if trailer else -1, boot=out[4] if trailer else -1,
                           boot_name=BW.boot_name(out[4]) if trailer else None)
            menu["ctl"] = ctl
        doc = {"host": host, "peer": pdoc, "menu": menu}
        if "present" in caps:
            end = {"injected": nb.injected, "held": nb.held, "kind": nb.kind,
                   "kind_name": None if nb.kind < 0 else BW.kind_name(nb.kind), "action": BW.present_name(nb.action),
                   "inject_phase": nb.inject_phase, "inject_seq": nb.inject_seq,
                   "inject_ms": int((self.rt - nb.inject_rt) * 1000) if nb.injected and self._dio["booted"] else -1,
                   "r8_hits": nb.r8_hits, "r8_first_ms": nb.r8_first_ms, "w1_armed": nb.w1_armed,
                   "watchdog": nb.watchdog, "blocker": nb.blocker, "why": nb.why, "faulted": nb.faulted,
                   "hud_reasserts": nb.hud_reasserts, "guest_mode": BW.GUEST_MODE_NAMES[self._nb_guest_mode()],
                   "ach_held": nb.ach_held, "ach_enemy_no": self.ach_enemy_no, "music": nb.music,
                   "btl_flag": nb.btl_flag}
            if "exit" in caps:
                end["exit_mode"] = "off" if self._nb_exit_mode() == BW.EXIT_MODE_OFF else "on"
                end["end_leave"] = {
                    "trigger": BW.trigger_name(nb.trigger),
                    "latched_ms": int((self.rt - nb.latched_rt) * 1000) if nb.trigger and self._dio["booted"] else -1,
                    "tries": nb.tries, "deferred": nb.deferred, "requested": nb.requested, "request_ms": nb.request_ms,
                    "why": nb.exit_why, "settled": nb.settled, "via": nb.via,
                    "stamp": nb.stamped if nb.stamped >= 0 else nb.stamp_pending, "stamp_host": nb.stamp_host,
                    "stamped": nb.stamped, "stamped_was": nb.stamped_was, "music_shut": nb.music_shut,
                    "music_why": nb.music_why, "wipe_lifted": nb.wipe_lifted}
                if "flee" in caps:                          # [ff9mapkit netsync R3 s115] the scoped no-leak rule's receipt
                    end["end_leave"]["reverted"] = nb.reverted
                end["declined"] = {"count": nb.declined_count, "nonce": nb.declined_nonce, "why": nb.declined_why}
            if "replay" in caps:                            # [ff9mapkit netsync B5] s109 AppendReplay
                end["replay"] = self._nb_replay_doc()
            if "flee" in caps:                              # [ff9mapkit netsync R3 s115] AppendEndFlee (s116: + msg_gil)
                booted = self._dio["booted"]
                # ability_flag is the LIVE ff9.btl_flag & BTL_FLAG_ABILITY_FLEE (HarnessFleeAbilityFlag: no booted gate):
                # the teardown leaves it set, and only the next battle's InitBattle (start_battle) clears it (R3H-7)
                end["flee"] = {"r9b": nb.flee_r9b, "bypassed": nb.flee_bypassed, "overload": False,
                               "ability_flag": nb.flee_ability_flag, "gil_now": self.save_gil,
                               "penalty": nb.flee_penalty if nb.flee_penalty >= 0 or not booted
                               else self._nb_flee_penalty()}
                if "fleegil" in caps:
                    end["flee"]["msg_gil"] = nb.flee_msg_gil
            if "defeat" in caps:                            # [ff9mapkit netsync R3 s117]
                end["follow_msg"] = nb.follow_msg
            doc["end"] = end
        if "actstart" in caps:                              # [ff9mapkit netsync s133] AppendAct, the fifth sub-object
            doc["act"] = {"host": self._act_lane.doc(enabled=bool(self.netsync["enabled"]), selftest_role=role)}
            if "actreplay" in caps:                         # [ff9mapkit netsync s134] AppendActGuest, after `host`
                doc["act"]["guest"] = self._act_guest.doc(role=role, booted=bool(self._dio["booted"]))
        return doc

    def _nb_peer_end(self) -> dict | None:
        """NetSyncBattle.TryGetPeerEnd: the selftest bench seam first (bench True), else the live loopback's trailer.
        [ff9mapkit netsync B5] From s108 it carries the decoded `manifest` / `manifest_why` (and `rows` counts it)."""
        nb = self._nb
        with_manifest = "manifest" in self._nb_caps()
        with_flee = "fleegil" in self._nb_caps()            # [ff9mapkit netsync R3 s116] + flee_gil
        if nb.bench_armed and self._nb_role():
            return BW.published_end(nb.bench_block, nonce=BW.BENCH_NONCE, wire_seq=nb.bench_wire_seq, bench=True,
                                    with_manifest=with_manifest, with_flee=with_flee)
        peer = nb.peer if nb.own_epoch is not None else None
        if peer is None or peer["end"] is None:
            return None
        return BW.published_end(peer["end"], nonce=peer["nonce"], wire_seq=peer["seq"], bench=False,
                                with_manifest=with_manifest, with_flee=with_flee)

    def _nb_peer_view(self) -> dict | None:
        """The production `_peerView` while it is live: a selftest OWN battle's loopback, or (s107) the bench feed's lane
        inside its diorama -- None when neither is live."""
        nb = self._nb
        if nb.own_epoch is not None:
            return nb.peer
        return self._nb_feed_view_live()

    def _nb_release(self) -> None:
        """NetSyncBattle.HarnessReleaseBench + the GuestSlots restore -- what NetSyncClient.HarnessSelfTest(false) runs on
        EVERY path (disarm, fault, `reset`, `selftest 0`; a forced role or an ini-configured selftest alike), ABOVE its
        forced-role early return."""
        nb = self._nb
        nb.gates_off_lever = False
        nb.loop.clear()
        nb.containment_off_lever = False
        if nb.bench_control:
            nb.bench_control = False
            nb.remote_menu = False
            nb.assist_rt = self.rt - 60.0
            # [ff9mapkit netsync R3 s118] ...the lane's stamp and a refusal too, and the latch a `bctl` report raised
            nb.lane_rt = self.rt - 60.0
            nb.rpt_refused = nb.rpt_refused_counted = False
            nb.own_latch["seen"] = False
        nb.capture_off_lever = False
        # [ff9mapkit netsync B4] s106-s107 HarnessReleaseStockMenu: the content lever, the bench roster, the feed, the knob
        nb.content_off_lever = 0
        nb.bench_roster = nb.bench_info = None
        self._nb_stop_feed("released with the harness")
        nb.knob_bench = -1
        nb.host_mode = BW.MODE_ON
        nb.guest_mode = BW.GUEST_ON
        nb.exit_mode = BW.EXIT_MODE_ON
        nb.manifest_mode = BW.MANIFEST_SHIP_ON           # [ff9mapkit netsync B5] s108
        nb.replay_mode = BW.REPLAY_MODE_ON               # [ff9mapkit netsync B5] s109 -- and a quit prompt the bench opened
        if nb.quit_opened:
            nb.quit_opened = False
            self.quit_prompt = False
        nb.clear_bench()
        nb.handback_off_lever = False                    # [ff9mapkit netsync B4] s110 -- and a lapse ended
        self._nb_end_lapse()
        # [ff9mapkit netsync R3] s111-s114's levers and bench values (HarnessReleaseBench, HarnessReleaseSwirl, the cfg
        # overrides' restore)
        nb.intro_off_lever = False
        self._nb_cfg_restore("skipcam")
        self._nb_cfg_restore("atb")
        nb.swirl_local, nb.swirl_clamp_set, nb.swirl_clamp = -1, False, -1
        nb.waitparity_off_lever = False
        nb.bench_ctl = -1
        nb.starthold_off_lever, nb.starthold_cap_bench = False, -1
        if nb.bench_boot >= 0 and self._nb_role():
            nb.own_latch["seen"] = False            # [ff9mapkit netsync R3 s118] the lever's reports are forgotten with it
        nb.bench_boot, nb.bench_boot_late_ms = -1, 0
        if nb.bench_guest_slots:
            nb.bench_guest_slots = False
            nb.guest_slots = 0                      # the pin while forced, else the ini's own value (0 here)
        # [ff9mapkit netsync s133] ActHarnessRelease, last: the action-start lever back on, the action tape emptied
        self._act_lane.release()
        self._act_flush()
        # [ff9mapkit netsync s134] NetSyncDiorama.ActBenchRelease, right after it: the replay levers back, the inbox emptied
        self._act_guest.release()
        self._act_flush()

    def _battle_bench_verb(self, sub: str, args: list, arg, out_of_range) -> None:
        """The agent's B4/B5 `netsync` sub-verbs (HarnessAgent, s100-s105): each one's argument parse FIRST (an
        ArgumentOutOfRangeException), then its Harness* entry point's gates and refusals, in the agent's order and
        words."""
        ns, nb, caps = self.netsync, self._nb, self._nb_caps()
        role = self._nb_role()
        if sub == "guestslots":
            mask = BW.parse_mask(args[1] if len(args) > 1 else None)
            if mask < 0:
                raise out_of_range("netsync guestslots", "needs a slot mask 0-15 (decimal or 0x hex)")
            if not role:
                raise RuntimeError("netsync guestslots: needs the selftest role (netsync selftest 1)")
            nb.guest_slots = mask
            nb.bench_guest_slots = True
        elif sub == "bcmd":
            frame = BW.parse_hex(args[1:])
            if frame is None:
                raise out_of_range("netsync bcmd", "needs hex bytes, e.g. `netsync bcmd 01 01 00 00 00 00 10 00 00`")
            if not role:
                raise RuntimeError("netsync bcmd: needs the selftest role (netsync selftest 1)")
            if not 0 < len(frame) <= 64:
                raise RuntimeError("netsync bcmd: needs 1..64 bytes of hex (a v1 command frame is 9: ver slot action "
                                   "menu idLo idHi maskLo maskHi cursor)")
            if len(nb.loop) >= 16:
                raise RuntimeError("netsync bcmd: 16 frames already wait on the loopback (no own battle is draining "
                                   "them)")
            nb.loop.append(frame)
        elif sub == "hostgates":
            on = arg(1, 1) != 0
            if not role:
                raise RuntimeError("netsync hostgates: needs the selftest role (netsync selftest 1)")
            nb.gates_off_lever = not on
        elif sub == "containment":
            on = arg(1, 1) != 0
            if not role:
                raise RuntimeError("netsync containment: needs the selftest role (netsync selftest 1)")
            nb.containment_off_lever = not on
        elif sub == "bctl":
            frame = BW.parse_hex(args[1:])
            if frame is None:
                raise out_of_range("netsync bctl", "needs hex bytes, e.g. `netsync bctl 00 00`")
            if not role:
                raise RuntimeError("netsync bctl: needs the selftest role (netsync selftest 1)")
            if not 0 < len(frame) <= 64:
                raise RuntimeError("netsync bctl: needs 1..64 bytes of hex (a control frame is 2: 00 " + (
                    "<menuOpen 0|1>)" if "waitparity" not in caps else
                    "<menu 0 shut|1 legacy|2 root|3 deep>)" if "starthold" not in caps else
                    "<menu 0 shut|1 legacy|2 root|3 deep>, or 5 with the start-hold trailer: ... 01 <host battle nonce> "
                    "<boot 0-4>)"))
            # ParseControl: a valid frame stamps the lane fresh; an invalid one clears the menu flag and stamps nothing
            if "waitparity" in caps:
                self._nb_parse_control(frame)               # [ff9mapkit netsync R3 s113/s114] the depth byte, the trailer
            elif BW.control_valid(frame):
                nb.assist_rt = nb.lane_rt = self.rt
                nb.remote_menu = frame[1] != 0
            else:
                nb.remote_menu = False
            nb.bench_control = True
        elif sub == "bmenu":
            self._nb_bmenu(args, arg, out_of_range)
        elif sub == "bbench":
            self._nb_bbench(args, out_of_range, caps)
        elif sub == "endbench":
            self._nb_endbench(args, arg, out_of_range, caps)
        elif sub == "actbench":
            self._nb_actbench(args, arg, out_of_range)        # [ff9mapkit netsync s133]

    def _nb_bmenu(self, args: list, arg, out_of_range) -> None:
        """`netsync bmenu ...` (s102): HarnessAgent's parse of `capture` / `open` / `close`, then
        NetSyncBattle.HarnessStockMenu."""
        nb = self._nb
        op = args[1].lower() if len(args) > 1 else ""
        barg = -1
        if op == "capture":
            v = args[2].lower() if len(args) > 2 else ""
            barg = 1 if v in ("on", "1") else 0 if v in ("off", "0") else -1
            if barg < 0:
                raise out_of_range("netsync bmenu capture", "needs on|off (1|0)")
        elif op in ("open", "close"):
            barg = arg(2, -1)
            if barg < 0 or barg > 3:
                raise out_of_range("netsync bmenu " + op, "needs a local party slot 0-3")
        if not self._nb_role():
            raise RuntimeError("netsync bmenu: needs the selftest role (netsync selftest 1)")
        if op == "capture":
            nb.capture_off_lever = barg == 0
        elif op == "open":
            self._nb_bench_open(barg)
        elif op == "close":
            if not self._nb_active():
                raise RuntimeError("netsync bmenu close: needs a live diorama")
            if self.battle_turn == barg:
                self.battle_turn = -1                       # SetIdle
                self._close_battle_cursor()
            self._nb_drop_slot(barg)
            nb.bench_open &= ~(1 << barg)
        elif op == "closeall":
            self._nb_close_all("harness `bmenu closeall`")
        elif op == "mainmenu":
            if not self._nb_active():
                raise RuntimeError("netsync bmenu mainmenu: needs a live diorama (a real battle's main menu is stock and is "
                                   "never probed)")
            if self.ui_state != "BattleHUD":
                raise RuntimeError("netsync bmenu mainmenu: the battle HUD is not the UI state")
            self._nb_side_refused("the in-battle main menu (AccessMenu / OnKeyMenu)")
        else:
            raise RuntimeError(f"netsync bmenu: unknown op '{op}' ({'|'.join(NETSYNC_BMENU_OPS)})")

    def _nb_bench_open(self, slot: int) -> None:
        """NetSyncBattle.BenchOpen: BenchMenuGate (a live diorama in its steady command phase), then
        BattleHUD.NetStockMenuOpen (the stock feeder, duplicate-guarded) -- the HUD's next ready pass opens the panel."""
        why = self._nb_menu_gate()
        if why is not None:
            raise RuntimeError("netsync bmenu open: " + why)
        unit = next((u for u in self.battle_units if u["slot"] == slot and u.get("player")), None)
        if unit is None:
            raise RuntimeError(f"netsync bmenu open: local slot {slot} holds no party member in this battle")
        if slot in self.battle_ready:
            if slot in self.battle_done:
                raise RuntimeError(f"netsync bmenu open: local slot {slot} already committed this turn -- "
                                   f"`netsync bmenu close {slot}` first")
        else:
            if not unit.get("alive") or not unit.get("can_act", True):
                raise RuntimeError(f"netsync bmenu open: local slot {slot} cannot take input (KO, a NoInput status, or "
                                   f"outside member_flag) -- the stock feeder refuses it")
            self.battle_ready.append(slot)                  # AddPlayerToReady
        self._nb.touched = True
        self._nb.bench_open |= 1 << slot

    def _nb_drop_slot(self, slot: int) -> bool:
        """BattleHUD.NetDropSlot: the slot off ReadyQueue / InputFinishList."""
        any_ = slot in self.battle_ready or slot in self.battle_done
        self.battle_ready = [s for s in self.battle_ready if s != slot]
        self.battle_done = [s for s in self.battle_done if s != slot]
        return any_

    def _nb_close_all(self, why: str) -> None:
        """NetSyncBattle.StockMenuCloseAll: the outbox and the bench mask always; the HUD only if this lane opened or
        captured this boot -- the party slots drained, then SetIdle."""
        nb = self._nb
        nb.outbox.clear()
        nb.bench_open = 0
        nb.mute_until = -1                                  # [ff9mapkit netsync B4] s106: the repaint's mute force-released
        nb.double_cast, nb.cast_first = 0, None
        if nb.mirror_mask or nb.pend:                       # [ff9mapkit netsync B4] s107: what the mirror held goes too
            nb.mirror_closed += bin(nb.mirror_mask | sum(1 << s for s in nb.pend)).count("1")
            nb.mirror_mask = 0
            nb.pend.clear()
        if not nb.touched:
            return
        for s in range(4):
            self._nb_drop_slot(s)
        if self.battle_turn >= 0:
            self.battle_turn = -1
            self._close_battle_cursor()
        nb.touched = False

    def _nb_side_refused(self, what: str) -> None:
        """NetSyncBattle.NoteSideRefused."""
        self._nb.side_refused += 1
        self._nb.side_why = what

    def _nb_r9(self, slot: int, cmd_no: int, site: str) -> bool:
        """btl_cmd.SetCommand's head (s101 R9, NetSyncDiorama.RefuseLocalEnqueue): inside a live diorama with containment
        on, a player's cmd[0] is never enqueued -- counted (`r9_refused` this boot, `r9_total`), the swing never plays.
        True = refused."""
        if not self._nb_active() or not self._nb_containment_on():
            return False
        unit = next((u for u in self.battle_units if u["slot"] == slot), None)
        if unit is None or not unit.get("player"):
            return False
        nb = self._nb
        nb.r9_refused += 1
        nb.r9_total += 1
        nb.r9_cmd = cmd_no
        nb.r9_site = site
        return True

    #: The stand-in's battle grid command -> its stock (BattleCommandId, v1 action, wire menu); Change has none.
    STOCK_COMMANDS = {"Attack": (1, BW.ACT_ATTACK, 0), "Defend": (2, BW.ACT_DEFEND, 0), "Steal": (3, BW.ACT_INSTANT, 2),
                      "Skill": (5, BW.ACT_ABILITY, 3), "Item": (8, BW.ACT_ITEM, 0), "Change": (6, None, 0)}
    #: The stand-in's submenu rows -> the ids a commit carries (RegularItem Potion 236 / Hi-Potion 237; an ability).
    STOCK_ROW_IDS = {"Potion": 236, "Hi-Potion": 237, "Flee": 30}

    def _nb_commit(self, label: str, mask: int, row: str | None, pick: dict | None = None) -> bool:
        """A stock COMMIT inside a live diorama (BattleHUD.SendCommand's head, s102): captured -- forwarded as one v1
        frame (ForwardStockCommand), the slot marked done, the panel idle, never enqueued -- or refused (outside the v1
        scope: SFX 102, nothing committed, the panel stays). False = not in a diorama with the capture on: the stock body
        runs (into R9, :meth:`_battle_command`). [ff9mapkit netsync B4] s106: a MIRRORED slot's ``pick`` (the drawn row)
        names the command, menu and id; s107: a capture on a slot the serving mirror holds goes PENDING, and under the
        bench feed the bench host takes the frame at once."""
        if not (self._nb_active() and self._nb_capture_on()):
            return False
        nb, slot = self._nb, self.battle_turn
        cmd_id, action, menu = self.STOCK_COMMANDS.get(label, (0, None, 0))
        nb.touched = True
        if action is None:
            nb.capture_refused += 1
            nb.capture_why = "Change is outside the v1 command scope (B4.2)"
            return True
        ident = self.STOCK_ROW_IDS.get(row, 0) if action in (BW.ACT_ABILITY, BW.ACT_ITEM) else 0
        if pick is not None:
            cmd_id, menu, ident = pick["cmd"], pick["menu"], pick["id"]
            action = BW.ACT_ITEM if pick["item"] else BW.ACT_ABILITY
        if not mask:
            nb.capture_refused += 1
            nb.capture_why = "empty target mask"
            return True
        frame = BW.encode_command(slot, action, menu, ident, mask, 0)          # the bench seats the own party: identity
        if len(nb.outbox) >= 8:
            nb.outbox.pop(0)
        nb.outbox.append(frame)
        nb.captures += 1
        c = BW.decode_command(frame)
        nb.captured = {"slot": c["slot"], "action": c["action"], "menu": c["menu"], "id": c["id"], "mask": c["mask"],
                       "cursor": c["cursor"], "local_slot": slot, "cmd": cmd_id, "site": "SendCommand",
                       "hex": BW.hex_bytes(frame), "action_name": BW.action_name(c["action"])}
        if slot not in self.battle_done:
            self.battle_done.append(slot)                   # InputFinishList.Add (the stock bookkeeping still runs)
        self.battle_turn = -1                               # SetIdle
        self._close_battle_cursor()
        self._nb_pick = None
        if "mirror" in self._nb_caps():
            self._nb_note_pending(slot)
            self._nb_drain_outbox()
        return True

    def _nb_endbench(self, args: list, arg, out_of_range, caps) -> None:
        """`netsync endbench ...` (s103-s109): HarnessAgent's parse, then NetSyncEnd.HarnessEndBench."""
        nb = self._nb
        op = args[1].lower() if len(args) > 1 else ""
        earg, loading, frame, mode = -1, False, None, None
        mode_ops = ("host",) + (("guest",) if "present" in caps else ()) + (("exit",) if "exit" in caps else ()) \
            + (("replay", "quit") if "replay" in caps else ())
        int_ops = ("other", "ui", "state", "overflow", "afterevent") + (("fieldsong",) if "replay" in caps else ())
        if op == "manifest" and "manifest" in caps:
            # [ff9mapkit netsync B5] s108: `manifest 0|none|1|2|3` or `manifest host on|off` (a mode only for the latter)
            ma = args[2].lower() if len(args) > 2 else ""
            if ma == "host":
                if len(args) != 4:
                    raise out_of_range("netsync endbench manifest host", "expected `manifest host on|off`")
                mode = args[3].lower()
            elif ma == "none":
                earg = 0
            else:
                earg = arg(2, -1)
                if earg < 0 or len(args) > 3:
                    raise out_of_range("netsync endbench manifest",
                                       "expected `manifest 0|none|1|2|3` or `manifest host on|off`")
        elif op in int_ops:
            earg = arg(2, -1)
            if earg < 0:
                raise out_of_range("netsync endbench " + op, "needs a non-negative integer argument")
            if op == "state" and len(args) > 3:
                if len(args) > 4 or args[3].lower() != "loading":
                    raise out_of_range("netsync endbench state", "expected `state <0-8> [loading]`")
                loading = True
        elif op == "cmd":
            if len(args) > 2:
                frame = BW.parse_hex(args[2:])
                if frame is None:
                    raise out_of_range("netsync endbench cmd",
                                       "needs hex bytes, e.g. `netsync endbench cmd 01 01 00 00 00 00 10 00 00`")
        elif op in mode_ops:
            mode = args[2].lower() if len(args) > 2 else ""
        elif op == "fleegil" and "fleegil" in caps:         # [ff9mapkit netsync R3 s116] `fleegil <gil>|none`
            fa = args[2].lower() if len(args) > 2 else ""
            if fa == "none" and len(args) == 3:
                mode = "none"
            else:
                earg = arg(2, -1)
                if earg < 0 or len(args) > 3:
                    raise out_of_range("netsync endbench fleegil",
                                       "expected `fleegil <gil>|none` (gil a non-negative integer)")
        elif op == "kill" and "defeat" in caps:             # [ff9mapkit netsync R3 s117] `kill [mask]`, 1-15 (default 15)
            earg = arg(2, -1) if len(args) > 2 else 15
            if earg < 1 or earg > 15 or len(args) > 3:
                raise out_of_range("netsync endbench kill",
                                   "expected `kill [mask]` (mask 1-15, a bit per player btl_id; default 15)")
        elif op == "phase-defeat" and "defeat" in caps:     # [ff9mapkit netsync R3 s117] no argument
            if len(args) > 2:
                raise out_of_range("netsync endbench phase-defeat", "takes no argument")
        if not self._nb_role():
            raise RuntimeError("netsync endbench: needs the selftest role (netsync selftest 1)")
        t = nb.template
        raw = {"victory": (BW.PHASE_VICTORY, BW.SEQ_VICTORY_CAMERA_MOVE, BW.BTL_RESULT_VICTORY),
               "pending": (BW.PHASE_MENU_OFF, BW.SEQ_MENU_OFF_VICTORY, BW.BTL_RESULT_INITIAL),
               "nopose": (BW.PHASE_CLOSE, BW.SEQ_DEFEATCLOSE_FADEOUT, BW.BTL_RESULT_VICTORY_NO_POSE),
               "defeat": (BW.PHASE_MENU_OFF, BW.SEQ_MENU_OFF_DEFEAT, BW.BTL_RESULT_INITIAL),
               "escape": (BW.PHASE_MENU_OFF, BW.SEQ_MENU_OFF_ESCAPE, BW.BTL_RESULT_INITIAL),
               "event": (BW.PHASE_MENU_OFF, BW.SEQ_MENU_OFF_EVENT, BW.BTL_RESULT_INITIAL),
               "fight": (BW.PHASE_NORMAL, 0, BW.BTL_RESULT_INITIAL)}
        if "defeat" in caps:                                # [ff9mapkit netsync R3 s117] past the settle, or var 34
            raw["phase-defeat"] = (BW.PHASE_DEFEAT, BW.SEQ_DEFEATCLOSE_FADEOUT, BW.BTL_RESULT_DEFEAT)
        if op in raw:
            t["phase"], t["seq"], t["result"] = raw[op]
        elif op == "other":
            if earg > 255:
                raise RuntimeError("netsync endbench other: needs a btl_result 0-255 (5 interruption, 7 enemy flee, ...)")
            t["phase"], t["seq"], t["result"] = BW.PHASE_CLOSE, BW.SEQ_DEFEATCLOSE_FADEOUT, earg
        elif op == "ui":
            if earg > 3:
                raise RuntimeError("netsync endbench ui: needs 0 (battle/other), 1 (BattleResult), 2 (GameOver) or 3 "
                                   "(Title)")
            t["ui"] = earg
        elif op == "state":
            if earg > BW.RES_NONE:
                raise RuntimeError("netsync endbench state: needs a ResultState 0-8 (0 Start .. 6 End, 7 Hide, 8 None) "
                                   "[loading]")
            t["state"], t["loading"] = earg, loading
        elif op in ("overflow", "afterevent") or (op == "fieldsong" and "replay" in caps):
            if earg not in (0, 1):
                raise RuntimeError(f"netsync endbench {op}: needs 0|1")
            bit = {"overflow": BW.FLAG_ITEM_OVERFLOW, "fieldsong": BW.FLAG_FIELD_SONG}.get(op, BW.FLAG_AFTER_EVENT)
            t["flags"] = t["flags"] | bit if earg else t["flags"] & ~bit
        elif op == "cmd":
            if frame is not None and not 0 < len(frame) <= 64:
                raise RuntimeError("netsync endbench cmd: needs 1..64 bytes of hex (a v1 command frame is 9)")
            nb.cmd_frame = frame or bytes([1, 1, 0, 0, 0, 0, 0x10, 0, 0])
            nb.cmd_armed = True
            nb.cmd_status = "armed"
            return
        elif op == "host":
            m = {"on": BW.MODE_ON, "cadence": BW.MODE_CADENCE, "off": BW.MODE_OFF}.get(mode)
            if m is None:
                raise RuntimeError("netsync endbench host: needs on|cadence|off")
            nb.host_mode = m
            return
        elif op == "guest" and "present" in caps:
            modes = {"on": BW.GUEST_ON, "off": BW.GUEST_OFF, "settle": BW.GUEST_SETTLE}
            if "flee" in caps:                              # [ff9mapkit netsync R3 s115] + hold | nor9b
                modes.update(hold=BW.GUEST_HOLD, nor9b=BW.GUEST_NOR9B)
            m = modes.get(mode)
            if m is None:
                raise RuntimeError("netsync endbench guest: needs " + "|".join(modes))
            nb.guest_mode = m
            return
        elif op == "kill" and "defeat" in caps:
            self._nb_kill(earg)                             # [ff9mapkit netsync R3 s117] no fabricate: the template stands
            return
        elif op == "exit" and "exit" in caps:
            m = {"on": BW.EXIT_MODE_ON, "off": BW.EXIT_MODE_OFF}.get(mode)
            if m is None:
                raise RuntimeError("netsync endbench exit: needs on|off")
            nb.exit_mode = m
            return
        elif op == "replay" and "replay" in caps:
            m = {"on": BW.REPLAY_MODE_ON, "off": BW.REPLAY_MODE_OFF, "local": BW.REPLAY_MODE_LOCAL}.get(mode)
            if m is None:
                raise RuntimeError("netsync endbench replay: needs on|off|local")
            nb.replay_mode = m
            return
        elif op == "quit" and "replay" in caps:
            self._nb_bench_quit(mode)
            return
        elif op == "selftest":
            return                                          # the engine runs NetSyncEnd.SelfTest; the stand-in passes it
        elif op == "clear":
            nb.clear_bench()
            return
        elif op == "manifest" and "manifest" in caps:
            if mode:
                m = {"on": BW.MANIFEST_SHIP_ON, "off": BW.MANIFEST_SHIP_OFF}.get(mode)
                if m is None:
                    raise RuntimeError("netsync endbench manifest host: needs on|off")
                nb.manifest_mode = m
                return
            if not 0 <= earg <= 3:
                raise RuntimeError("netsync endbench manifest: needs 0 (none), 1 (two-marker), 2 (escape with gil), 3 "
                                   "(foreign charIds) or `host on|off`")
            if earg == 0:
                t["manifest"], nb.manifest_note = None, None
            else:
                built, note = self._nb_bench_manifest(earg)
                if built is None:
                    raise RuntimeError(f"netsync endbench manifest {earg}: {note or 'could not build the manifest'}")
                t["manifest"], nb.manifest_note = built, note
            nb.manifest_preset = earg
            t["flags"] = t["flags"] | BW.FLAG_ESCAPE_GIL if earg == 2 else t["flags"] & ~BW.FLAG_ESCAPE_GIL
        elif op == "manifest":
            raise RuntimeError("netsync endbench manifest: the result manifest is stage 9 -- this engine ships the end "
                               "block only")
        elif op == "fleegil" and "fleegil" in caps:         # [ff9mapkit netsync R3 s116] the template's flee record
            t["flee_gil"] = -1 if mode == "none" else earg
        elif op == "phase-defeat" and "defeat" in caps:
            pass                                            # (the raw table above set it)
        else:
            raise RuntimeError(f"netsync endbench: unknown op '{op}' ({'|'.join(endbench_ops(caps))})")
        # Fabricate: the template -> a block as a host ships it -> the codec -> the parse; the PARSED block is served
        block = BW.make_block(t["phase"], t["seq"], t["result"], ui=t["ui"], state=t["state"], loading=t["loading"],
                              flags=t["flags"])
        mbytes = BW.encode_manifest(t["manifest"]) if t.get("manifest") is not None else None
        if mbytes is not None:                              # [ff9mapkit netsync B5] s108: the manifest rides the body
            block["flags"] |= BW.FLAG_MANIFEST
            block["manifest_len"] = len(mbytes)
        else:
            block["flags"] &= ~BW.FLAG_MANIFEST
        flee = t.get("flee_gil", -1) if "fleegil" in caps else -1
        rec = BW.encode_flee_record(BW.FLEE_GIL_DROP, flee) if flee >= 0 else b""   # [ff9mapkit netsync R3 s116]
        got, why, _skipped = BW.read_trailer(BW.encode_trailer(block, mbytes) + rec)
        if got is None or why is not None or {k: got[k] for k in block} != block:
            raise RuntimeError(f"netsync endbench {op}: the codec mangled the block -- sent {BW.block_text(block)}, "
                               f"parsed {BW.block_text(got) if got else 'nothing'}")
        if (got["flee_gil"] if got["flee_flags"] >= 0 else -1) != flee:
            raise RuntimeError(f"netsync endbench {op}: the codec mangled the flee record (sent {flee})")
        if (not BW.same_manifest(got["manifest"], t["manifest"]) if mbytes is not None
                else got["manifest"] is not None or got["manifest_len"] != 0):
            raise RuntimeError(f"netsync endbench {op}: the codec mangled the manifest -- parsed "
                               f"{got['manifest_why'] or 'a different manifest'}")
        nb.bench_seq = (nb.bench_seq + 1) & 0xFFFF
        nb.bench_block = got
        nb.bench_wire_seq = nb.bench_seq
        nb.bench_armed = True

    # ---- [ff9mapkit netsync B4] the opener's gate, shared by `bmenu open`, `bbench roster auto` and the ready mirror
    def _nb_menu_gate(self) -> str | None:
        """NetSyncBattle.StockMenu.BenchMenuGate's text: None = open (a live diorama in its steady command phase)."""
        if not self._nb_active():
            return "needs a live diorama (netsync dioboot <scene>, then wait for battle.turn.enabled)"
        if self.ui_state != "BattleHUD":
            return f"the UI state is {self.ui_state}, not BattleHUD"
        if self._battle_phase_now() != BW.PHASE_NORMAL:
            return f"the diorama is in phase {self._battle_phase_now()}, not its steady phase ({BW.PHASE_NORMAL})"
        if not self.commands_enabled:
            return "the HUD's command menu is not enabled yet (wait for battle.turn.enabled)"
        return None

    # ---- [ff9mapkit netsync B4] s106 (stage 7): the roster-fed menu content ------------------------------------------
    #: The stand-in's command world for the roster-fed panels (shapes, not real FF9 ids beyond the markers'): each command
    #: id the HUD can draw -> its label; an Ability-type command -> its ability list; the double-cast commands; each
    #: ability's name and the stand-in's OWN MP for it; what the stand-in's pa[] has learned; the item names.
    FAKE_COMMAND_NAMES = {1: "Attack", 2: "Defend", 3: "Steal", 5: "Skill", 6: "Change", 8: "Item", 17: "White Magic",
                          21: "Double White Magic", 22: "Black Magic", 23: "Double Black Magic"}
    FAKE_COMMAND_ABILITIES = {5: (30, 31), 17: (6, 7, 8, 9), 21: (6, 7, 8), 22: (20, 21, 22), 23: (20, 21, 22)}
    FAKE_DOUBLE_CAST = frozenset({21, 23})
    FAKE_ABILITY_NAMES = {6: "Cure", 7: "Cura", 8: "Curaga", 9: "Life", 20: "Fire", 21: "Blizzard", 22: "Meteor",
                          30: "Flee", 31: "Detect"}
    FAKE_ABILITY_MP = {6: 6, 7: 10, 8: 22, 9: 8, 20: 6, 21: 6, 22: 18, 30: 0, 31: 4}
    FAKE_LEARNED = frozenset({30})
    FAKE_ITEM_NAMES = {236: "Potion", 237: "Hi-Potion", 238: "Ether", 239: "Elixir", 240: "Phoenix Down"}
    #: `bbench roster auto`'s marker commands, tried in order (WhiteMagicGarnet, BlackMagic -- and under `dbl` the
    #: double-cast DoubleBlackMagic, DoubleWhiteMagic): the first OUTSIDE the slot's preset wins
    FAKE_MARKERS = (17, 22)
    FAKE_DBL_MARKERS = (23, 21)
    #: the stand-in's preset, by menu index (Attack, Defend, Ability1, Ability2, Item, Change -- BATTLE_GRID's order)
    FAKE_PRESET = (1, 2, 3, 5, 8, 6)

    def _nb_content_on(self, bit: int) -> bool:
        """NetSyncBattle.StockMenu.ContentOn: a hook is ON unless the selftest lever turned it off."""
        return not (self._nb.content_off_lever & bit and self._nb_role())

    def _nb_hit(self, bit: int) -> None:
        """A hook answer that REPLACED stock content (`content_hits`, monotonic per process)."""
        self._nb.content_hits[BW.CONTENT_NAMES[bit.bit_length() - 1]] += 1

    def _nb_menu_roster(self) -> tuple:
        """MenuRoster -> (roster, src): the bench roster while armed (selftest role) -- under the s107 bench feed only while
        its lane is live (it rides the feed's lane) -- else none: the live peer roster counts only under
        NetSyncParty.MirrorActive, which the stand-in (no party mirror) never reaches."""
        nb = self._nb
        if nb.bench_roster is not None and self._nb_role():
            if nb.feed is not None and self._nb_feed_view_live() is None:
                return None, None
            return nb.bench_roster, "bench"
        return None, None

    def _nb_mirrored_cmds(self, slot: int) -> list | None:
        """MirroredRoster: a mirrored LOCAL slot's roster commands (the bench seats the guest's own party, so local = wire);
        None = not mirrored -> stock content."""
        if not 0 <= slot <= 3 or "content" not in self._nb_caps() or not self._nb_active():
            return None
        if not any(u["slot"] == slot and u.get("player") for u in self.battle_units):
            return None
        roster, _src = self._nb_menu_roster()
        return None if roster is None else roster["slots"].get(slot)

    def _nb_mirrored_slots(self) -> list:
        return [s for s in range(4) if self._nb_mirrored_cmds(s) is not None]

    def _nb_resolve(self, slot: int, menu: int) -> tuple:
        """(1) ResolveMenuCommand -> (command id, replaced): the roster's command for Attack / Ability1 / Ability2 when it
        is not the local preset's; any doubt (not mirrored, no roster entry, an id this install lacks) = the local one."""
        local = self.FAKE_PRESET[menu]
        cmds = self._nb_mirrored_cmds(slot)
        if cmds is None or menu not in (0, 2, 3) or not self._nb_content_on(BW.CONTENT_COMMAND):
            return local, False
        rc = next((c for c in cmds if c["menu"] == menu), None)
        if rc is None or rc["cmd"] == local or rc["cmd"] not in self.FAKE_COMMAND_NAMES:
            return local, False
        return rc["cmd"], True

    def _nb_display_commands(self, slot: int) -> list:
        """DisplayCommand on a mirrored slot: (1) the resolved commands, (2) Change drawn grey."""
        out = []
        for i, label in enumerate(lab for row in self.BATTLE_GRID for lab in row):
            cid, replaced = self._nb_resolve(slot, i)
            if replaced:
                self._nb_hit(BW.CONTENT_COMMAND)
            state = 2
            if label == "Change" and self._nb_content_on(BW.CONTENT_GREY):
                state = 1
                self._nb_hit(BW.CONTENT_GREY)
            out.append({"menu": i, "id": cid, "label": self.FAKE_COMMAND_NAMES.get(cid, label), "state": state,
                        "raw": state})
        return out

    def _nb_display_abilities(self, slot: int, menu: int, cmd_id: int) -> list:
        """(3) RosterAbilityState + RosterAbilityMp on a mirrored slot's ability list: a row the roster lists draws the
        host's enabled flag and MP, an unlisted one blank -- the hook off, the stand-in's own pa[] and MP."""
        cmds = self._nb_mirrored_cmds(slot) or []
        rc = next((c for c in cmds if c["menu"] == menu and c["cmd"] == cmd_id), None)
        listed = {a["id"]: a for a in rc["abils"]} if rc is not None else {}
        on = self._nb_content_on(BW.CONTENT_ABILITY)
        rows = []
        for i, aid in enumerate(self.FAKE_COMMAND_ABILITIES.get(cmd_id, ())):
            if on:
                a = listed.get(aid)
                state = 0 if a is None else 2 if a["enabled"] else 1
                mp = 0 if a is None else a["mp"]
                self._nb_hit(BW.CONTENT_ABILITY)
            else:
                state = 2 if aid in self.FAKE_LEARNED else 0
                mp = self.FAKE_ABILITY_MP.get(aid, 0)
            rows.append({"i": i, "id": aid, "label": self.FAKE_ABILITY_NAMES.get(aid, "") if state else "",
                         "number": "" if state == 0 or mp == 0 else str(mp), "state": state, "raw": state})
        return rows

    def _nb_display_items(self, slot: int) -> list:
        """(4) RosterBag on a mirrored slot: the HOST's items, never the guest's own -- the hook off, the stand-in's."""
        roster, _src = self._nb_menu_roster()
        if roster is None or not self._nb_content_on(BW.CONTENT_BAG):
            return [{"i": i, "id": self.STOCK_ROW_IDS.get(label, 0), "label": label, "number": "9", "state": 2, "raw": 2}
                    for i, label in enumerate(self.BATTLE_SUBMENU_ROWS["Battle.Item"])]
        self._nb_hit(BW.CONTENT_BAG)
        return [{"i": i, "id": it["id"], "label": self.FAKE_ITEM_NAMES.get(it["id"], f"Item {it['id']}"),
                 "number": str(it["count"]), "state": 2, "raw": 2} for i, it in enumerate(roster["items"])]

    def _nb_on_panel(self, group: str | None, force: bool = False) -> None:
        """A panel DISPLAYED for the HUD's slot (the stock Display* calls): a mirrored slot's panel is drawn here, from the
        menu roster, and stays as drawn until the next display or a repaint (the stock NGUI labels)."""
        nb, slot = self._nb, self.battle_turn
        if not group or slot < 0 or self._nb_mirrored_cmds(slot) is None:
            nb.hud_snap = None
            return
        snap = nb.hud_snap if nb.hud_snap is not None and nb.hud_snap["slot"] == slot and not force else None
        if snap is None or group == "Battle.Command":
            snap = {"slot": slot, "commands": self._nb_display_commands(slot)}
        snap = dict(snap, group=group, rows=[], menu=snap.get("menu"))
        if group == "Battle.Command":
            snap["menu"] = None
        elif group == "Battle.Ability":
            m = self._grid_pos[0] * 2 + self._grid_pos[1]
            snap.update(menu=m, rows=self._nb_display_abilities(slot, m, snap["commands"][m]["id"]))
        elif group == "Battle.Item":
            snap.update(menu=4, rows=self._nb_display_items(slot))
        nb.hud_snap = snap

    def _nb_snap_for(self, group: str | None) -> dict | None:
        """The drawn panel the HUD doc shows for ``group`` (None = draw it stock)."""
        snap = self._nb.hud_snap
        if snap is None or snap["slot"] != self.battle_turn or snap["group"] != group:
            return None
        return snap

    def _nb_content_tick(self) -> None:
        """One HUD frame of stage 7: the repaint's mute settle, (7) StockRosterRepaintDue -> NetRefreshMenus while a diorama
        menu is up (the generation moves only then), and (5) the item target's per-frame count (RosterItemCount)."""
        nb = self._nb
        if nb.mute_until >= 0 and self.frame >= nb.mute_until:
            nb.mute_until = -1
        group = str(self.menu.get("group") or "")
        if not self._nb_active() or self.battle_turn < 0 or not group.startswith("Battle."):
            return
        roster, _src = self._nb_menu_roster()
        sig = 0 if roster is None else BW.roster_signature(roster)
        if sig != nb.roster_seen:
            nb.roster_gen += 1
            nb.roster_seen = sig
        if nb.roster_painted != nb.roster_gen:
            nb.roster_painted = nb.roster_gen
            if self._nb_content_on(BW.CONTENT_REFRESH):
                self._nb_hit(BW.CONTENT_REFRESH)
                nb.mute_until = self.frame + 2
                self._nb_repaint(group)
        pick = getattr(self, "_nb_pick", None)
        if group == "Battle.Target" and pick is not None and pick.get("item") \
                and self._nb_mirrored_cmds(self.battle_turn) is not None:
            if self._nb_content_on(BW.CONTENT_COUNT):
                count = next((it["count"] for it in (roster or {}).get("items", ()) if it["id"] == pick["id"]), 0)
                self._nb_hit(BW.CONTENT_COUNT)
            else:
                count = self.save_bag.get(pick["id"], 0)
            if count <= 0:                                  # ManageTargetCommand: none left -> back (SFX 101)
                self._set_battle_cursor("Battle.Item", pick["label"])

    def _nb_repaint(self, group: str) -> None:
        """BattleHUD.NetRefreshMenus: the command buttons redrawn; an open submenu or target panel whose menu's command
        RE-RESOLVED goes back to the command panel (stock's trance-flip bounce), else its list is redrawn."""
        nb, slot = self._nb, self.battle_turn
        old = nb.hud_snap
        if self._nb_mirrored_cmds(slot) is None:
            nb.hud_snap = None
            return
        cmds = self._nb_display_commands(slot)
        m = old.get("menu") if old is not None else None
        if group != "Battle.Command" and old is not None and m is not None and old["commands"][m]["id"] != cmds[m]["id"]:
            nb.hud_snap = {"slot": slot, "group": "Battle.Command", "commands": cmds, "rows": [], "menu": None}
            self._set_battle_cursor("Battle.Command", self.BATTLE_GRID[self._grid_pos[0]][self._grid_pos[1]])
            return
        nb.hud_snap = {"slot": slot, "group": group, "commands": cmds, "rows": [], "menu": m}
        if group == "Battle.Ability" and m is not None:
            nb.hud_snap["rows"] = self._nb_display_abilities(slot, m, cmds[m]["id"])
        elif group == "Battle.Item":
            nb.hud_snap["rows"] = self._nb_display_items(slot)

    def _nb_bbench(self, args: list, out_of_range, caps) -> None:
        """`netsync bbench ...` (s106-s107): HarnessAgent's parse (a hex roster refused BEFORE the role gate), then
        NetSyncBattle.HarnessStockBench -- the role, then the op."""
        nb = self._nb
        op = args[1].lower() if len(args) > 1 else ""
        rest = list(args[2:])
        hexb = None
        if op == "roster" and rest and rest[0].lower() not in ("auto", "clear"):
            hexb = BW.parse_hex(rest)
            if hexb is None:
                raise out_of_range("netsync bbench roster", "needs hex bytes (a v1 type-4 roster), `auto <L> [dbl] [grey] "
                                                            "[mp=<n>] [count=<n>]` or `clear`")
        if not self._nb_role():
            raise RuntimeError("netsync bbench: needs the selftest role (netsync selftest 1)")
        if op == "roster":
            self._nb_bench_roster(rest, hexb)
        elif op == "content":
            on = BW.parse_content_mask(rest[0] if rest else "")
            if on < 0:
                raise RuntimeError("netsync bbench content: on|off|<mask 0-127> (the hooks left ON: 1 command, 2 grey, 4 "
                                   "ability, 8 bag, 16 count, 32 cast, 64 refresh)")
            nb.content_off_lever = BW.CONTENT_ALL & ~on
        elif op in NETSYNC_BBENCH_OPS[2:] and "mirror" in caps:
            self._nb_feed_verb(op, rest)
        else:
            known = "|".join(NETSYNC_BBENCH_OPS) if "mirror" in caps else NETSYNC_BBENCH_UNKNOWN_S106
            raise RuntimeError(f"netsync bbench: unknown op '{op}' ({known})")

    def _nb_bench_roster(self, rest: list, hexb: bytes | None) -> None:
        """BenchRoster: `clear`, `auto <L> [dbl] [grey] [mp=<n>] [count=<n>]` (the two-marker fabricator, read back through
        the Python ParseRoster and refused if the round trip changes a field) or a raw v1 roster."""
        nb = self._nb
        sub = rest[0].strip().lower() if rest else ""
        if sub == "clear":
            nb.bench_roster = nb.bench_info = None
            return
        if sub == "auto":
            slot = _int32(rest[1]) if len(rest) > 1 else None
            if slot is None or not 0 <= slot <= 3:
                raise RuntimeError("netsync bbench roster auto: needs a local party slot 0-3")
            dbl = grey = False
            mp, count = 1, 77
            for a in rest[2:]:
                t = a.strip().lower()
                if t == "dbl":
                    dbl = True
                elif t in ("grey", "gray"):
                    grey = True
                elif t.startswith("mp=") and _int32(t[3:]) is not None and 0 <= _int32(t[3:]) <= 255:
                    mp = _int32(t[3:])
                elif t.startswith("count=") and _int32(t[6:]) is not None and 1 <= _int32(t[6:]) <= 255:
                    count = _int32(t[6:])
                else:
                    raise RuntimeError(f"netsync bbench roster auto: unknown option '{a}' (dbl | grey | mp=<0-255> | "
                                       f"count=<1-255>)")
            roster, info = self._nb_fabricate(slot, dbl, grey, mp, count)
            raw = BW.encode_roster(roster)
            parsed = BW.parse_roster(raw)
            if parsed is None or BW.roster_signature(parsed) != BW.roster_signature(roster):
                raise RuntimeError("netsync bbench roster auto: the v1 roster codec round trip CHANGED the fabricated roster "
                                   f"[{BW.hex_bytes(raw)}]")
            info["bytes"] = len(raw)
            nb.bench_roster, nb.bench_info = parsed, info
            return
        if not hexb:
            raise RuntimeError("netsync bbench roster: needs hex bytes (a v1 type-4 roster), `auto <L> [dbl] [grey] "
                               "[mp=<n>] [count=<n>]` or `clear`")
        parsed = BW.parse_roster(hexb)
        if parsed is None:
            raise RuntimeError(f"netsync bbench roster: the REAL ParseRoster refused those {len(hexb)} bytes (not a v1 "
                               f"roster -- the log names the fault)")
        nb.bench_roster = parsed
        nb.bench_info = {"src": "hex", "bytes": len(hexb), "slot": -1, "wire": -1, "marker_menu": -1, "marker_cmd": -1,
                         "marker_shown": -1, "marker_grey": -1, "marker_local_mp": -1, "uk_menu": -1, "uk_cmd": -1,
                         "unlearned": -1, "unlearned_local_mp": -1, "learned": -1, "item": -1, "count": -1, "mp": 1,
                         "dbl": False, "grey": False, "note": None}

    def _nb_fabricate(self, slot: int, dbl: bool, grey: bool, mp: int, count: int) -> tuple:
        """BenchFabricate on the stand-in's world: the opener's gate, the slot's unit, then the TWO-MARKER roster -- the
        slot's OWN Ability-type command listing only an entry the stand-in has NOT learned (Skill: Detect, not Flee), a
        marker command OUTSIDE its preset in the other ability menu (White Magic; `dbl` Double Black Magic: its 1st entry
        listed enabled -- disabled under `grey` -- its 2nd disabled), a bag of one item the guest owns 0 of."""
        gate = self._nb_menu_gate()
        if gate is not None:
            raise RuntimeError("netsync bbench roster auto: " + gate)
        if not any(u["slot"] == slot and u.get("player") for u in self.battle_units):
            raise RuntimeError(f"netsync bbench roster auto: local slot {slot} holds no party member in this battle")
        uk_menu, uk_cmd = 3, self.FAKE_PRESET[3]
        unlearned = next(a for a in self.FAKE_COMMAND_ABILITIES[uk_cmd] if a not in self.FAKE_LEARNED)
        learned = next(a for a in self.FAKE_COMMAND_ABILITIES[uk_cmd] if a in self.FAKE_LEARNED)
        marker = next(c for c in (self.FAKE_DBL_MARKERS if dbl else self.FAKE_MARKERS) if c not in self.FAKE_PRESET)
        shown, greyed = self.FAKE_COMMAND_ABILITIES[marker][:2]
        item = next(i for i in sorted(self.FAKE_ITEM_NAMES) if self.save_bag.get(i, 0) == 0)
        roster = {"slots": {slot: [BW.roster_cmd(0, self.FAKE_PRESET[0], type=0, target=1),
                                   BW.roster_cmd(2, marker, abils=[(shown, mp, not grey), (greyed, mp, False)]),
                                   BW.roster_cmd(uk_menu, uk_cmd, abils=[(unlearned, mp, True)])]},
                  "items": [{"id": item, "count": count, "target": 1, "for_dead": False}]}
        info = {"src": "auto", "bytes": 0, "slot": slot, "wire": slot, "marker_menu": 2, "marker_cmd": marker,
                "marker_shown": shown, "marker_grey": greyed, "marker_local_mp": self.FAKE_ABILITY_MP[shown],
                "uk_menu": uk_menu, "uk_cmd": uk_cmd, "unlearned": unlearned,
                "unlearned_local_mp": self.FAKE_ABILITY_MP[unlearned], "learned": learned, "item": item, "count": count,
                "mp": mp, "dbl": dbl, "grey": grey, "note": None}
        return roster, info

    # ---- [ff9mapkit netsync B4] s107 (stage 8): the production ready mirror + the bench feed -------------------------
    def _nb_knob_on(self) -> bool:
        """StockKnobOn: the `bbench knob` override (selftest role), else [Netsync] GuestStockMenu."""
        nb = self._nb
        return nb.knob_bench != 0 if nb.knob_bench >= 0 and self._nb_role() else bool(self.guest_stock_menu)

    def _nb_feed_view_live(self) -> dict | None:
        """The view the bench feed published into the production _peerView, while it is live (StaleMs: 2 s)."""
        v = self._nb.feed_view
        if v is None or self.rt - v["rt"] >= BW.STALE_MS / 1000.0:
            return None
        return v

    def _nb_feed_seq(self) -> int:
        v = self._nb.feed_view
        return v["seq"] if v is not None else 0

    def _nb_stock_owns(self, view: dict | None, active: bool) -> tuple:
        """StockMenuOwns -> (owns, why): the knob, a live diorama, the party mirror or the bench feed, a live lane, caps
        bit 1, not faulted -- the first missing condition is the why."""
        nb = self._nb
        if not self._nb_knob_on():
            return False, ("the knob is off ([Netsync] GuestStockMenu=0, the bench override)"
                           if nb.knob_bench >= 0 and self._nb_role() else "the knob is off ([Netsync] GuestStockMenu=0)")
        if not active:
            return False, "no live battle diorama"
        if nb.feed is None:
            return False, ("the party mirror is not active (the diorama seats the guest's own party, so the wire-to-local "
                           "join means nothing)")
        if view is None:
            return False, "no live peer battle lane"
        if not view["caps"] & BW.CAP_COMMAND_PHASE_GATED:
            return False, "host predates the command-phase gates"
        if nb.mirror_faulted:
            return False, nb.mirror_fault_why or "the ready mirror faulted this boot"
        return True, None

    def _nb_feed_verb(self, op: str, rest: list) -> None:
        """BenchFeedVerb: `start <mask>` (inside a live diorama), `stop`, `knob 0|1|ini`; then -- a feed running --
        `ready <mask>`, `caps <0-255>`, `mode accept|refuse|freeze`, `freeze 1|0`, `unmap <w>|none`."""
        nb = self._nb
        a = rest[0].strip().lower() if rest else ""
        if op == "start":
            v = BW.parse_bench_int(a, 0x0F)
            if v <= 0:
                raise RuntimeError("netsync bbench start: needs the host's guest-slot offer, a WIRE slot mask 1-15 (decimal "
                                   "or 0x hex)")
            if not self._nb_active():
                raise RuntimeError("netsync bbench start: needs a live diorama (netsync dioboot <scene>)")
            nb.feed_nonce = (nb.feed_nonce + 1) & 0xFF
            nb.feed = {"guest_slots": v & 0x0F, "ready": 0, "caps": BW.CAP_COMMAND_PHASE_GATED, "refuse": False,
                       "frozen": False, "unmap": -1, "nonce": nb.feed_nonce, "seq": 0, "frames": 0, "taken": 0,
                       "accepted": 0, "refused": 0, "bad": 0, "last": None, "force": True, "sample_rt": -3600.0}
            return
        if op == "stop":
            self._nb_stop_feed("harness `bbench stop`")
            return
        if op == "knob":
            knob = {"ini": -1, "1": 1, "on": 1, "0": 0, "off": 0}.get(a)
            if knob is None:
                raise RuntimeError("netsync bbench knob: 0|1|ini (force GuestStockMenu off/on for this process, or back to "
                                   "the ini's value)")
            nb.knob_bench = knob
            return
        f = nb.feed
        if f is None:
            raise RuntimeError(f"netsync bbench {op}: no bench feed is running (`bbench start <mask>` inside a live diorama "
                               f"first)")
        if op == "ready":
            v = BW.parse_bench_int(a, 0x0F)
            if v < 0:
                raise RuntimeError("netsync bbench ready: needs a WIRE slot mask 0-15 (decimal or 0x hex)")
            f["ready"], f["force"] = v, True
        elif op == "caps":
            v = BW.parse_bench_int(a, 0xFF)
            if v < 0:
                raise RuntimeError("netsync bbench caps: needs the header flags byte 0-255 (bit 1 = a command-phase-gated "
                                   "host)")
            f["caps"], f["force"] = v, True
        elif op == "mode":
            if a in ("accept", "refuse"):
                f["refuse"] = a == "refuse"
            elif a == "freeze":
                f["frozen"] = True
            else:
                raise RuntimeError("netsync bbench mode: accept|refuse|freeze")
        elif op == "freeze":
            if a in ("1", "on"):
                f["frozen"] = True
            elif a in ("0", "off"):
                f["frozen"], f["force"] = False, True
            else:
                raise RuntimeError("netsync bbench freeze: 1|0")
        elif op == "unmap":
            if a in ("none", "off", "-1"):
                f["unmap"] = -1
            else:
                v = BW.parse_bench_int(a, 3)
                if v < 0:
                    raise RuntimeError("netsync bbench unmap: a WIRE slot 0-3, or none")
                f["unmap"] = v

    def _nb_stop_feed(self, why: str) -> None:
        """StopFeed: the feed and the lane it published go (the mirror stands down on its next tick)."""
        nb = self._nb
        if nb.feed is None:
            return
        nb.feed = None
        nb.feed_view = None
        nb.assist_slot = -1

    def _nb_feed_doc(self) -> dict | None:
        """`netsync.battle.menu.feed` (HarnessBenchFeed): None = no feed running."""
        f = self._nb.feed
        if f is None:
            return None
        view = self._nb_feed_view_live()
        doc = {"guest_slots": f["guest_slots"], "ready": f["ready"], "caps": f["caps"],
               "mode": "refuse" if f["refuse"] else "accept", "frozen": f["frozen"], "unmap": f["unmap"],
               "nonce": f["nonce"], "seq": f["seq"], "live": view is not None,
               "menu_open": view is not None and self._nb_first_ready_guest(view) >= 0}
        if "waitparity" in self._nb_caps():
            # [ff9mapkit netsync R3 s113] the EXACT frame Pump would send this tick, and its byte 1 (`menu_open` is
            # `ctl_menu > 0`, as before)
            frame, _src = self._nb_feed_control()
            doc.update(ctl=None if frame is None else BW.hex_bytes(frame), ctl_menu=frame[1] if frame is not None else -1)
            doc["menu_open"] = frame is not None and frame[1] > 0
        doc.update(frames=f["frames"], taken=f["taken"], accepted=f["accepted"], refused=f["refused"], bad=f["bad"],
                   last=f["last"])
        return doc

    def _nb_feed_control(self) -> tuple:
        """[ff9mapkit netsync R3 s113/s114] The bench feed's control frame -- what Pump's guest branch would send while the
        feed's lane is live: GuestControl over the feed view (the stock window below its root = 3, the Quit prompt
        excluded) and, s114, the report of a WIRE boot of the feed's nonce (LIVE once the LIVE latch holds)."""
        view = self._nb_feed_view_live()
        if view is None:
            return None, None
        nb = self._nb
        ready = self._nb_first_ready_guest(view) >= 0
        slot = self.battle_turn
        deep = (slot >= 0 and bool(nb.mirror_mask & (1 << slot)) and not self.quit_prompt
                and self.menu.get("group") in ("Battle.Ability", "Battle.Item", "Battle.Target"))
        return self._nb_guest_control(view["nonce"], ready, deep=deep, booted_live=nb.live_latched)

    def _nb_first_ready_guest(self, view: dict) -> int:
        """FirstReadyGuestSlot: the first WIRE slot the view offers that is Ready and alive (-1 = none)."""
        for u in sorted(self.battle_units, key=lambda x: x["slot"]):
            w = u["slot"]
            if u.get("player") and 0 <= w < 4 and view["guest_slots"] & (1 << w) and view["ready"] & (1 << w) \
                    and u.get("alive", True) and u["hp"] > 0:
                return w
        return -1

    def _nb_feed_tick(self) -> None:
        """The bench feed, once a frame inside its live diorama: a type-1 frame every SampleMs (and at once on a lever
        change) from the diorama's own units -- players at their wire index -- into the production view."""
        nb, f = self._nb, self._nb.feed
        if f is None:
            return
        if not self._nb_active():
            self._nb_stop_feed("its diorama ended")
            return
        if f["frozen"] or not (f["force"] or self.rt - f["sample_rt"] >= BW.SAMPLE_MS / 1000.0):
            return
        f["force"] = False
        f["sample_rt"] = self.rt
        f["seq"] = (f["seq"] + 1) & 0xFFFF
        f["frames"] += 1
        seated = sum(1 << u["slot"] for u in self.battle_units if u.get("player") and 0 <= u["slot"] < 4)
        nb.feed_view = {"seq": f["seq"], "nonce": f["nonce"], "caps": f["caps"], "ready": f["ready"] & seated,
                        "guest_slots": f["guest_slots"], "rt": self.rt}

    def _nb_mirror_close(self, slot: int) -> None:
        """NetStockMenuClose: SetIdle when its panel is up, then the slot off ReadyQueue / InputFinishList."""
        if self.battle_turn == slot:
            self.battle_turn = -1
            self._close_battle_cursor()
        self._nb_drop_slot(slot)

    def _nb_mirror_stand_down(self) -> None:
        """A failed ownership check or gate closes only the slots the mirror holds (its open mask and the pending ones)."""
        nb = self._nb
        held = nb.mirror_mask | sum(1 << s for s in nb.pend)
        for s in range(4):
            if held & (1 << s):
                self._nb_mirror_close(s)
                nb.mirror_closed += 1
        nb.mirror_mask = 0
        nb.pend.clear()

    def _nb_mirror_tick(self) -> None:
        """StockMenuTick (+ GuestAssistTick's AssistSlot): ownership, the opener's gate, then MirrorServe -- per offered
        wire unit: Ready + alive + in the menu roster opens its local seat on the stock ReadyQueue; a fallen bit closes it
        (a pending command's fall = accepted, a new nonce or a KO = obsolete); a bit still up 2.5 s and 3 host samples
        after a commit = refused (reopened at the root); an unseated one (the `unmap` lever) is stranded while Ready, a
        Ready one the roster never carries (2.5 s) or the stock feeder refuses STRANDED for the turn; a held slot no
        offered unit maps to any more is an orphan, closed."""
        nb = self._nb
        view = self._nb_feed_view_live()
        active = self._nb_active()
        owns, _why = self._nb_stock_owns(view, active)
        if view is not None:
            stranded_first, first = -1, -1
            for w in range(4):
                if view["guest_slots"] & (1 << w) and view["ready"] & (1 << w):
                    unit = next((u for u in self.battle_units if u.get("player") and u["slot"] == w), None)
                    if unit is not None and unit.get("alive", True) and unit["hp"] > 0:
                        first = w if first < 0 else first
                        if nb.stranded_mask & (1 << w) and stranded_first < 0:
                            stranded_first = w
            nb.assist_slot = -1 if first < 0 else stranded_first if owns else first
        else:
            nb.assist_slot = -1
        if not owns or self._nb_menu_gate() is not None:
            if nb.mirror_mask or nb.pend:
                self._nb_mirror_stand_down()
            nb.mirror_serving = False
            nb.no_roster_since.clear()
            nb.no_roster_mask = 0
            if not owns:
                nb.stranded_mask = 0
            return
        nb.mirror_serving = True
        f = nb.feed
        if view["nonce"] != nb.mirror_nonce:
            nb.mirror_nonce = view["nonce"]
            nb.stranded_turn = 0                            # a new battle: every slot tries the stock menu again
            nb.no_roster_since.clear()
        roster, _src = self._nb_menu_roster()
        seen = stranded = no_roster = 0
        for w in range(4):
            wbit = 1 << w
            unit = next((u for u in self.battle_units if u.get("player") and u["slot"] == w), None)
            if unit is None or not view["guest_slots"] & wbit:
                continue
            up = bool(view["ready"] & wbit) and unit.get("alive", True) and unit["hp"] > 0
            if not up:
                nb.stranded_turn &= ~wbit                   # the turn is over: a later Ready tries the stock menu again
            local = -1 if f["unmap"] == w else w            # LocalIndexForWire (the bench seats the own party: identity)
            if local < 0:
                nb.no_roster_since.pop(w, None)
                if up:
                    stranded |= wbit                        # no local seat: the digit panel serves it
                continue
            lbit = 1 << local
            seen |= lbit
            queued, finished = local in self.battle_ready, local in self.battle_done
            if local in nb.pend:
                p = nb.pend[local]
                obsolete = view["nonce"] != p["nonce"] or not unit.get("alive", True) or unit["hp"] <= 0
                if obsolete or not view["ready"] & wbit:
                    del nb.pend[local]
                    nb.mirror_mask &= ~lbit
                    self._nb_mirror_close(local)
                    if obsolete:
                        nb.mirror_obsolete += 1
                    else:
                        nb.mirror_accepted += 1
                    continue
                if self.rt - p["rt"] < BW.MIRROR_REFUSE_MS / 1000.0 or                         ((view["seq"] - p["seq0"]) & 0xFFFF) < BW.MIRROR_REFUSE_SEQS:
                    continue                                # the host has not answered yet: the slot stays shut
                del nb.pend[local]                          # REFUSED or lost: buzzer, the slot reopens at the root
                nb.mirror_mask &= ~lbit
                nb.mirror_refused += 1
                self._nb_mirror_close(local)
                queued = finished = False
            want = up
            if up and (roster is None or w not in roster["slots"]):
                if not nb.stranded_turn & wbit:
                    since = nb.no_roster_since.setdefault(w, self.rt)
                    if self.rt - since >= BW.MIRROR_NO_ROSTER_MS / 1000.0:
                        del nb.no_roster_since[w]
                        nb.stranded_turn |= wbit            # the bounded wait ran out: STRANDED for this turn (G7)
                if not nb.stranded_turn & wbit:
                    want = False                            # the host's menu content has not arrived: wait
                    no_roster |= wbit
                elif queued or finished:
                    self._nb_mirror_close(local)
                    nb.mirror_closed += 1
                    nb.mirror_mask &= ~lbit
                    queued = finished = False
            else:
                nb.no_roster_since.pop(w, None)
            if not want:
                if queued or finished:
                    self._nb_mirror_close(local)
                    nb.mirror_closed += 1
                nb.mirror_mask &= ~lbit
                continue
            if nb.stranded_turn & wbit:
                stranded |= wbit
                continue
            if finished:
                self._nb_mirror_close(local)                # committed with no verdict pending: a clean turn
                queued = False
            if not queued:
                if unit.get("can_act", True):
                    self.battle_ready.append(local)         # NetStockMenuOpen -> AddPlayerToReady
                    nb.mirror_mask |= lbit
                    nb.mirror_fed += 1
                    nb.touched = True
                else:
                    nb.stranded_turn |= wbit                # the stock feeder refuses it: STRANDED for the turn (G7)
                    stranded |= wbit
            else:
                nb.mirror_mask |= lbit                      # already queued and awaiting input: the mirror owns it
        orphan = (nb.mirror_mask | sum(1 << s for s in nb.pend)) & ~seen & 0x0F
        for s in range(4):
            if orphan & (1 << s):
                nb.mirror_mask &= ~(1 << s)
                nb.pend.pop(s, None)
                self._nb_mirror_close(s)
                nb.mirror_closed += 1
        nb.stranded_mask, nb.no_roster_mask = stranded, no_roster

    def _nb_note_pending(self, slot: int) -> None:
        """NoteMirrorPending (from ForwardStockCommand): a capture on a slot the serving mirror holds awaits the host."""
        nb = self._nb
        if nb.mirror_serving and nb.mirror_mask & (1 << slot):
            view = nb.feed_view
            nb.pend[slot] = {"wire": slot, "rt": self.rt, "seq0": self._nb_feed_seq(),
                             "nonce": view["nonce"] if view is not None else -1}

    def _nb_drain_outbox(self) -> None:
        """The outbox's drain while the bench feed runs: the BENCH HOST stands in for the socket and decodes every frame
        with the host's own decoder -- `mode accept` drops that wire slot's Ready bit at once, `refuse` leaves it up."""
        nb, f = self._nb, self._nb.feed
        while f is not None and nb.outbox:
            frame = nb.outbox.pop(0)
            nb.stock_sent += 1
            f["taken"] += 1
            c = BW.decode_command(frame)
            if c is None:
                f["bad"] += 1
                f["last"] = f"[{BW.hex_bytes(frame)}] malformed"
                continue
            bit = 1 << c["slot"]
            if not f["refuse"] and f["ready"] & bit:
                f["ready"] &= ~bit
                f["accepted"] += 1
                f["force"] = True
                verdict = "ACCEPTED"
            else:
                f["refused"] += 1
                verdict = "REFUSED"
            f["last"] = f"[{BW.hex_bytes(frame)}] slot {c['slot']} {BW.action_name(c['action'])} -- {verdict}"

    # ---- [ff9mapkit netsync B5] s108 (stage 9): the result manifest ----------------------------------------------------
    def _nb_manifest_mode(self) -> int:
        """NetSyncEnd.ManifestMode: the `endbench manifest host` lever (selftest role only)."""
        return self._nb.manifest_mode if self._nb_role() else BW.MANIFEST_SHIP_ON

    def _nb_bench_manifest(self, preset: int) -> tuple:
        """NetSyncEnd.BenchManifest on the stand-in's SAVE (:attr:`save_party` / :attr:`save_gil` / :attr:`save_bag` /
        :attr:`save_cards`, the level table :func:`fake_threshold`) -> (manifest, note): 1 the TWO-MARKER manifest, 2 escape
        with gil, 3 preset 1 with FOREIGN char ids; (None, why) with no seated member."""
        notes = []
        party = self.save_party[:BW.MANIFEST_MAX_ROWS]
        first = next((i for i, p in enumerate(party) if p is not None), -1)
        if first < 0:
            return None, "no seated party member to build rows from"
        escape = preset == 2
        p0 = party[first]
        gain = 0
        if not escape:
            if p0["level"] >= FAKE_LEVEL_COUNT or p0["exp"] >= BW.EXP_CAP:
                gain = 1
                notes.append(f"row {first} is at the level/exp cap (no LEVEL UP)")
            else:
                thr = fake_threshold(min(p0["level"] + 1, FAKE_LEVEL_COUNT - 1))
                gain = thr - p0["exp"] if thr > p0["exp"] else 1
                if BW.level_after(p0["level"], p0["exp"], gain, FAKE_LEVEL_COUNT, fake_threshold) != p0["level"] + 2:
                    notes.append(f"row {first} is near the level cap (fewer than two LEVEL UPs)")
        seated = {p["char"] for p in party if p is not None}
        foreign = 0
        rows: list = [None] * BW.MANIFEST_MAX_ROWS
        for i, p in enumerate(party):
            if p is None:
                continue
            cid = p["char"]
            if preset == 3:
                while foreign < 0xFF and foreign in seated:
                    foreign += 1
                cid, foreign = foreign, foreign + 1
            exp_gain = 0 if escape else gain
            status, learns = p["status"], []
            if i == first and not escape:
                if not status & BW.STATUS_POISON:
                    status |= BW.STATUS_POISON
                elif not status & BW.STATUS_BLIND:
                    status |= BW.STATUS_BLIND
                else:
                    notes.append(f"row {first} already carries Poison and Blind (no status marker)")
                abil = next((a for (a, max_ap), ap in zip(p["abils"], p["pa"]) if a and ap < max_ap), 0)
                if abil:
                    learns = [(abil, 3)]
                else:
                    notes.append(f"row {first} has no unmastered ability in its preset (no learn marker)")
            rows[i] = BW.manifest_row(cid if 0 <= cid < 0xFF else 0xFF, lv_before=p["level"],
                                      lv_after=BW.level_after(p["level"], p["exp"], exp_gain, FAKE_LEVEL_COUNT,
                                                              fake_threshold),
                                      exp_before=p["exp"], exp_gain=exp_gain, ap_gain=0 if escape else 5, status=status,
                                      learns=learns)
        items, card = [], BW.CARD_NONE
        if not escape:
            item = next((i for i in sorted(self.FAKE_ITEM_NAMES) if self.save_bag.get(i, 0) == 0), None)
            if item is not None:
                items = [(item, 7)]
            else:
                notes.append("no item the bag holds 0 of (no item marker)")
            card = next((c for c in range(100) if self.save_cards.get(c, 0) == 0), None)
            if card is None:
                card = 0
                notes.append("no card the collection holds 0 of (card 0)")
        m = BW.make_manifest(rows, default_exp=0 if escape else gain, default_ap=0 if escape else 5,
                             gil_gain=321 if escape else 4321,
                             gil_before=1234566 if self.save_gil == 1234567 else 1234567, items=items, card=card)
        return m, ("; ".join(notes) if notes else None)

    # ---- [ff9mapkit netsync B5] s109 (stage 10): the guest's write-nothing result-screen replay ----------------------
    #: frames the HUD's hide fade takes before the replay's screen shows; a result page's fade (EndEXPAndAP -> the gil
    #: page, End -> Hide); a tick page (EXP/AP, gil) at its natural pace
    REPLAY_OPEN_FRAMES = 8
    RESULT_FADE_FRAMES = 12
    RESULT_TICK_FRAMES = 24

    def _nb_replay_mode(self) -> int:
        """NetSyncEnd.ReplayMode: the `endbench replay` lever (selftest role only)."""
        return self._nb.replay_mode if self._nb_role() else BW.REPLAY_MODE_ON

    def _nb_replay_live(self) -> bool:
        nb = self._nb
        return nb.r_pending or (nb.r_opened and not nb.r_closed and not nb.r_aborted)

    def _nb_seated(self) -> tuple:
        """SeatedSlots: the seated party's slot_no per RAW slot (-1 = an empty seat), and the seated mask."""
        seated = [p["char"] if p is not None else -1 for p in (self.save_party + [None] * 4)[:4]]
        return seated, sum(1 << i for i, c in enumerate(seated) if c >= 0)

    def _nb_fp(self) -> dict:
        """BattleResultUI.NetFingerprint on the stand-in's save: FNV-1a 64 (FpMix) over the gil, the bag, each seated
        member's level / exp / pa[], the card count and the ability-achievement set -- `end.replay.fp`."""
        h = BW.fp_mix(BW.FP_SEED, self.save_gil)
        items = sorted((i, c) for i, c in self.save_bag.items() if c > 0)
        for i, c in items:
            h = BW.fp_mix(BW.fp_mix(h, i), c)
        players = [p for p in self.save_party if p is not None]
        for p in players:
            h = BW.fp_mix(BW.fp_mix(BW.fp_mix(h, p["char"]), p["level"]), p["exp"])
            for ap in p["pa"]:
                h = BW.fp_mix(h, ap)
        cards = sum(1 for c in self.save_cards.values() if c > 0)
        h = BW.fp_mix(BW.fp_mix(h, cards), len(self.save_passive))
        return {"hash": f"0x{h:016X}", "gil": self.save_gil, "items": len(items), "item_sum": sum(c for _i, c in items),
                "players": len(players), "level_sum": sum(p["level"] for p in players),
                "exp_sum": sum(p["exp"] for p in players), "pa_sum": sum(sum(p["pa"]) for p in players), "cards": cards,
                "abilities": sum(1 for p in players for (_a, max_ap), ap in zip(p["abils"], p["pa"]) if ap >= max_ap),
                "passive": len(self.save_passive)}

    def _nb_replay_doc(self) -> dict:
        """AppendReplay -- `netsync.battle.end.replay` (per boot; `fp` read LIVE)."""
        nb = self._nb
        return {"mode": BW.REPLAY_MODE_NAMES[self._nb_replay_mode()], "armed": nb.r_armed, "pending": nb.r_pending,
                "opened": nb.r_opened, "live": self._nb_replay_live(), "closed": nb.r_closed, "aborted": nb.r_aborted,
                "abort_why": nb.r_abort_why, "refused": nb.r_refused, "verdict": nb.r_verdict,
                "why": None if nb.r_verdict < 0 else BW.arm_why(nb.r_verdict), "row_mask": nb.r_row_mask,
                "seated_mask": nb.r_seated_mask, "manifest_rows": nb.r_manifest_rows,
                "host_state_at_arm": nb.r_host_state_at_arm, "bench": nb.r_bench, "arm_ms": nb.r_arm_ms,
                "open_ms": nb.r_open_ms, "close_ms": nb.r_close_ms, "exit_waited": nb.r_exit_waiting,
                "exit_wait_ms": nb.r_exit_wait_ms, "screen": self._nb_screen_doc(), "fp": self._nb_fp()}

    def _nb_screen_doc(self) -> dict | None:
        """AppendReplayScreen: the screen's own replay receipts (None until a replay screen has shown)."""
        sc = self._nb.screen
        if sc is None:
            return None
        return {"replay": True, "inert": False, "state": sc["state"], "host_state": sc["host_state"],
                "host_loading": sc["host_loading"], "follow": sc["follow"],
                "follow_why": None if sc["follow"] < 0 else BW.follow_why(sc["follow"]), "steps": sc["steps"],
                "trail": list(sc["trail"]), "local_confirms": sc["local_confirms"], "local_steps": sc["local_steps"],
                "rows": [{"slot": r["slot"], "char": r["char"], "level": r["level"], "exp": r["exp"]} for r in sc["rows"]],
                "gil": sc["gil"], "learned": [dict(x) for x in sc["learned"]], "host_overflow": sc["host_overflow"],
                "overflow_shown": sc["overflow_shown"], "hidden": sc["hidden"], "aborted": sc["aborted"],
                "faulted": False, "open_ms": int((self.rt - sc["open_rt"]) * 1000) if not sc["hidden"] else -1,
                "writes": sc["writes"], "fp_open": sc["fp_open"]}

    def _nb_replay_arm_tick(self, ours: bool, e: dict | None) -> None:
        """NetSyncDiorama.ReplayArmTick (EndTick, after an injected end, until it arms or is refused): ArmVerdict on the raw
        conditions, then -- they all hold -- on the manifest (TryGetPeerManifest: the bench end's own), the HUD and the
        seats; GO arms it, and the HUD's hide fade later the stock result screen opens as the REPLAY."""
        nb = self._nb
        if nb.r_armed or nb.r_refused or nb.r_aborted:
            return
        mode = self._nb_replay_mode()
        exit_latched = nb.trigger != BW.TRIGGER_NONE or self._dio_leave_recently() or nb.settled
        ui = e["ui"] if ours else 0xFF
        host_state = BW.block_state(e) if ours else -1
        flags = e["flags"] if ours else 0
        res = e["result"] if ours else 0                    # [ff9mapkit netsync R3 s115] an ESCAPE ignores b0
        v = BW.arm_verdict(mode, nb.injected, nb.r8_hits, exit_latched, ui, host_state, flags, res, True, True, 0x0F)
        m, mask, seated_mask = None, 0, 0
        if v == BW.ARM_GO:
            m = e.get("manifest")
            hud_up = self.ui_state == "BattleHUD" and not self.quit_prompt
            seated, seated_mask = self._nb_seated()
            mask = BW.valid_row_mask(m, seated) if m is not None and hud_up else 0
            v = BW.arm_verdict(mode, nb.injected, nb.r8_hits, exit_latched, ui, host_state, flags, res, m is not None,
                               hud_up, mask)
        nb.r_verdict = v
        if v != BW.ARM_GO:
            if v == BW.ARM_NO_VALID_ROW:
                nb.r_refused = True
            return
        nb.r_armed = nb.r_pending = True
        nb.r_manifest, nb.r_row_mask, nb.r_seated_mask, nb.r_flags = m, mask, seated_mask, flags
        nb.r_manifest_rows = BW.manifest_row_count(m)
        nb.r_host_state_at_arm = host_state
        nb.r_bench = True                                   # the stand-in arms off the endbench seam only
        nb.r_arm_rt = self.rt
        nb.r_arm_ms = int((self.rt - nb.inject_rt) * 1000)
        nb.r_open_frame = self.frame + self.REPLAY_OPEN_FRAMES

    def _nb_replay_host_state(self) -> tuple:
        """NetSyncDiorama.ReplayHostState -> (state, loading): Hide once the exit latched as a result-hide; else the
        host's block (ui 1), else -1 (no host state)."""
        nb = self._nb
        if nb.trigger == BW.TRIGGER_RESULT_HIDE:
            return BW.RES_HIDE, False
        e = nb.bench_block if nb.bench_armed and self._nb_role() else None
        if e is None or e["ui"] != BW.UI_RESULT:
            return -1, False
        return BW.block_state(e), BW.block_loading(e)

    def _nb_replay_open(self) -> None:
        """The HUD-hide callback: the stock result screen opens on the host's manifest, written nowhere (the shadows)."""
        nb = self._nb
        if not nb.r_pending or self.frame < nb.r_open_frame:
            return
        if not (self._dio["booted"] and self._nb_active()):
            return
        nb.r_pending, nb.r_opened = False, True
        nb.r_open_rt = self.rt
        nb.r_open_ms = int((self.rt - nb.r_arm_rt) * 1000)
        m = nb.r_manifest
        rows = []
        for i, r in enumerate(m["rows"][:BW.MANIFEST_MAX_ROWS]):
            if r is not None and nb.r_row_mask & (1 << i):
                rows.append({"slot": i, "char": r["char"], "level": r["lv_before"], "exp": r["exp_before"], "ap": 0,
                             "row": r})
        fp = self._nb_fp()["hash"]
        nb.screen = {"state": BW.RES_START, "loading": False, "loading_until": -1, "host_state": -1,
                     "host_loading": False, "follow": -1, "steps": 0, "trail": [], "local_confirms": 0, "local_steps": 0,
                     "rows": rows, "gil": m["gil_before"], "gil_value": m["gil_gain"], "learned": [],
                     "host_overflow": False, "overflow_shown": False, "hidden": False, "aborted": False,
                     "open_rt": self.rt, "writes": 0, "fp_open": fp, "fp_last": fp, "last_step_state": -1,
                     "last_step_rt": -3600.0, "tick_frame": -1}
        self.commands_enabled = False
        if self.battle_turn >= 0:
            self.battle_turn = -1
        self._close_battle_cursor()
        self.ui_state = "BattleResult"

    def _nb_screen_tick(self) -> None:
        """The replay screen, one frame: its tick pages run at their own pace, a Loading transition ends, the WRITE GUARD
        compares the fingerprint, then NetFollow -- FollowVerdict, and on STEP one stock Confirm step (StepConfirm)."""
        nb, sc = self._nb, self._nb.screen
        if sc is None or sc["hidden"] or sc["aborted"] or not nb.r_opened:
            return
        fp = self._nb_fp()["hash"]
        if fp != sc["fp_last"]:
            sc["writes"] += 1
            sc["fp_last"] = fp
        if sc["loading"] and self.frame >= sc["loading_until"]:
            sc["loading"] = False
            if sc["state"] == BW.RES_HIDE:
                self._nb_replay_hide_tail()
                return
        if sc["state"] == BW.RES_EXP_TICK:
            self._nb_screen_exp(min(1.0, (self.frame - sc["tick_frame"]) / float(self.RESULT_TICK_FRAMES)))
        elif sc["state"] == BW.RES_GIL_TICK:
            self._nb_screen_gil(min(1.0, (self.frame - sc["tick_frame"]) / float(self.RESULT_TICK_FRAMES)))
        host, host_loading = self._nb_replay_host_state()
        sc["host_state"], sc["host_loading"] = host, host_loading
        e = nb.bench_block if nb.bench_armed else None
        sc["host_overflow"] = bool(((e["flags"] if e is not None else nb.r_flags) & BW.FLAG_ITEM_OVERFLOW))
        v = BW.follow_verdict(False, self.ui_state == "BattleResult", self.quit_prompt, sc["loading"], sc["state"], host,
                              host_loading, sc["last_step_state"], int((self.rt - sc["last_step_rt"]) * 1000))
        sc["follow"] = v
        if v == BW.FOLLOW_STEP:
            sc["steps"] += 1
            sc["trail"].append(f"{sc['state']}>{host}{'L' if host_loading else ''}")
            sc["last_step_state"], sc["last_step_rt"] = sc["state"], self.rt
            self._nb_screen_step(host)

    def _nb_screen_step(self, host: int) -> None:
        """StepConfirm: the stock OnKeyConfirm switch, one step, on the replay's shadows."""
        nb, sc = self._nb, self._nb.screen
        s = sc["state"]
        if s == BW.RES_START:
            sc["state"], sc["tick_frame"] = BW.RES_EXP_TICK, self.frame
        elif s == BW.RES_EXP_TICK:
            self._nb_screen_exp(1.0)                        # a Confirm mid-tick: the whole remainder at once
        elif s == BW.RES_END_EXP:
            sc["state"], sc["loading"], sc["loading_until"] = BW.RES_START_GIL, True, self.frame + self.RESULT_FADE_FRAMES
        elif s == BW.RES_START_GIL:
            e = nb.bench_block if nb.bench_armed else None
            flags = e["flags"] if e is not None else nb.r_flags
            if BW.replay_overflow(flags, host):
                sc["state"], sc["overflow_shown"] = BW.RES_ITEM_FULL, True
            else:
                sc["state"], sc["tick_frame"] = BW.RES_GIL_TICK, self.frame
        elif s == BW.RES_ITEM_FULL:
            sc["state"], sc["tick_frame"] = BW.RES_GIL_TICK, self.frame
        elif s == BW.RES_GIL_TICK:
            self._nb_screen_gil(1.0)
        elif s == BW.RES_END:
            sc["state"], sc["loading"], sc["loading_until"] = BW.RES_HIDE, True, self.frame + self.RESULT_FADE_FRAMES

    def _nb_screen_exp(self, frac: float) -> None:
        """Seams h + i: the shadow EXP / level (ReplayLevel, never past levelAfter -- forced to it once all is in) and the
        AP, its scheduled learns fired in their (old, new] window (LearnsDue) -- pa[] untouched."""
        sc = self._nb.screen
        for r in sc["rows"]:
            row = r["row"]
            r["exp"] = row["exp_before"] + int(row["exp_gain"] * frac)
            r["level"] = BW.replay_level(row["lv_before"], r["exp"], row["lv_after"], FAKE_LEVEL_COUNT, fake_threshold)
            new_ap = int(row["ap_gain"] * frac)
            for x in row["learns"]:
                if r["ap"] < x["ap_at"] <= new_ap:
                    sc["learned"].append({"slot": r["slot"], "abil": x["abil"], "ap": x["ap_at"]})
            r["ap"] = new_ap
            if frac >= 1.0:
                r["level"] = row["lv_after"]
        if frac >= 1.0:
            sc["state"] = BW.RES_END_EXP

    def _nb_screen_gil(self, frac: float) -> None:
        """Seam k: the SHADOW party gil ticks up (the guest's own never moves); all in -> End."""
        nb, sc = self._nb, self._nb.screen
        m = nb.r_manifest
        added = int(m["gil_gain"] * frac)
        sc["gil"], sc["gil_value"] = m["gil_before"] + added, m["gil_gain"] - added
        if frac >= 1.0:
            sc["state"] = BW.RES_END

    def _nb_replay_hide_tail(self) -> None:
        """Seam b: the replay's OWN hide tail -- the song half under SongVerdict (ReplayHideTailSong; recorded for the
        settle's music_why), the fade lift, NoteReplayHideTail (CLOSED: the end-leave stops waiting)."""
        nb, sc = self._nb, self._nb.screen
        sc["hidden"] = True
        nb.r_hide_tail = True
        if nb.r_opened and not nb.r_closed:
            nb.r_closed = True
            nb.r_close_ms = int((self.rt - nb.r_arm_rt) * 1000)
        flags = nb.exit_last["flags"] if nb.exit_seen and nb.exit_last is not None else nb.r_flags
        v = BW.song_verdict(flags, False)
        if v == BW.SONG_SHUT:
            nb.music = -1
            nb.r_music_why = "the replay's own hide tail already shut the songs (stage 10): nothing shut down twice"
        else:
            nb.r_music_why = BW.song_why(v) + " -- the replay's own hide tail kept it too (stage 10)"
        self.ui_state = "BattleHUD"

    def _nb_replay_abort(self, why: str) -> None:
        """NetSyncDiorama.AbortReplay: a replay still pending is dropped; one on screen stops (its tick loops stop) and
        holds -- the settle then owns the song shutdown and the teardown the fade lift."""
        nb = self._nb
        if nb.r_pending:
            nb.r_pending = False
            nb.r_aborted = True
            nb.r_abort_why = why + " (before the result screen opened)"
            return
        if not nb.r_opened or nb.r_closed or nb.r_aborted:
            return
        nb.r_aborted = True
        nb.r_abort_why = why
        if nb.screen is not None:
            nb.screen["aborted"] = True

    def _nb_replay_local_confirm(self) -> None:
        """Seam c: the guest's own Confirm on the replay -- swallowed (counted), or under `endbench replay local` a step."""
        nb, sc = self._nb, self._nb.screen
        if self._nb_replay_mode() == BW.REPLAY_MODE_LOCAL:
            sc["local_steps"] += 1
            host, _loading = self._nb_replay_host_state()
            self._nb_screen_step(host)
        else:
            sc["local_confirms"] += 1

    def _nb_bench_quit(self, mode: str | None) -> None:
        """BenchQuitPrompt: `on` opens the guest's OWN quit prompt (the stock quit command), `off` hides it. ⚠ Never press
        Confirm on it: its Yes quits the game (the stand-in quits too)."""
        nb, sc = self._nb, self._nb.screen
        if mode == "on":
            if self.ui_state == "BattleResult" and sc is not None and (sc["loading"] or sc["state"] == BW.RES_HIDE):
                raise RuntimeError("netsync endbench quit on: the quit prompt did not open (the UI is Loading, or the current "
                                   "scene refuses Quit -- BattleResultUI refuses it at Hide and while Loading)")
            self.quit_prompt = True
            nb.quit_opened = True
        elif mode == "off":
            self.quit_prompt = False
            nb.quit_opened = False
        else:
            raise RuntimeError("netsync endbench quit: needs on|off")

    def _result_ui_doc(self) -> dict:
        """HarnessAgent.AppendResultUi on the stand-in: `state` / `loading` / `paused`, s109 `replay`, s108's describe
        (labels, card_shown, model, rows, items) -- the REPLAY's own view when the replay is the screen up."""
        caps, nb = self._nb_caps(), self._nb
        sc = nb.screen if nb.screen is not None and nb.r_opened and not nb.screen["hidden"] else None
        doc = {"state": sc["state"] if sc else self.result_state, "loading": bool(sc["loading"]) if sc else False,
               "paused": self.quit_prompt}
        if "replay" in caps:
            doc["replay"] = sc is not None
        if "manifest" in caps:
            doc.update(self._result_describe(sc))
        return doc

    def _result_describe(self, sc: dict | None) -> dict:
        """BattleResultUI.NetDescribe: the labels as drawn, the model, the four rows and the item list."""
        nb = self._nb
        if sc is None:                                      # an own battle's screen: the stand-in draws no reward pages
            b = self.battle_bonus
            return {"labels": {"exp": None, "ap": None, "gil_receive": None, "gil_current": None, "card": None},
                    "card_shown": False,
                    "model": {"default_exp": b.get("exp", 0), "default_ap": b.get("ap", 0), "default_gil": b.get("gil", 0),
                              "gil_value": 0, "gil_current": self.save_gil, "party_gil": self.save_gil,
                              "card": BW.CARD_NONE},
                    "rows": [], "items": []}
        m = nb.r_manifest
        page2 = sc["state"] >= BW.RES_START_GIL
        card = m["card"] if page2 and m["card"] != BW.CARD_NONE else None
        rows = []
        by_slot = {r["slot"]: r for r in sc["rows"]}
        for i in range(4):
            r = by_slot.get(i)
            if r is None:
                rows.append({"slot": i, "shown": False, "name": None, "level": None, "exp": None, "next": None,
                             "dim": False, "level_ups": 0, "exp_value": 0, "exp_current": 0, "ap_value": 0,
                             "ap_current": 0, "need_exp": False, "need_ap": False})
                continue
            row = r["row"]
            rows.append({"slot": i, "shown": True, "name": f"Char {row['char']}", "level": str(r["level"]),
                         "exp": str(r["exp"]), "next": str(max(0, fake_threshold(r["level"]) - r["exp"])),
                         "dim": not row["flags"] & BW.ROW_DRAW, "level_ups": r["level"] - row["lv_before"],
                         "exp_value": row["exp_before"] + row["exp_gain"] - r["exp"], "exp_current": r["exp"],
                         "ap_value": row["ap_gain"] - r["ap"], "ap_current": r["ap"],
                         "need_exp": bool(row["flags"] & BW.ROW_NEED_EXP), "need_ap": bool(row["flags"] & BW.ROW_NEED_AP)})
        return {"labels": {"exp": str(m["default_exp"]), "ap": str(m["default_ap"]),
                           "gil_receive": str(sc["gil_value"]) if page2 else "",
                           "gil_current": str(sc["gil"]) if page2 else "",
                           "card": None if card is None else f"Card {card}"},
                "card_shown": card is not None,
                "model": {"default_exp": m["default_exp"], "default_ap": m["default_ap"], "default_gil": m["gil_gain"],
                          "gil_value": sc["gil_value"], "gil_current": sc["gil"], "party_gil": self.save_gil,
                          "card": m["card"]},
                "rows": rows,
                "items": [{"id": it["id"], "count": it["count"], "shown": page2,
                           "name": self.FAKE_ITEM_NAMES.get(it["id"], f"Item {it['id']}"), "number": str(it["count"])}
                          for it in m["items"]]}

    # ---- [ff9mapkit netsync B4] s110 (stage 11): the host's guest-slot hand-back ---------------------------------------
    def _nb_handback_on(self) -> bool:
        """NetSyncBattle.HandbackOn: the `bench handback 0` lever bites only in the selftest role."""
        return not (self._nb.handback_off_lever and self._nb_role())

    def _nb_handback_doc(self) -> dict:
        """AppendHandback -- `netsync.battle.host.handback`."""
        nb = self._nb
        lapse_left = -1
        if nb.lapse_armed and not nb.lapse_hold:
            lapse_left = max(0, nb.lapse_ms - int((self.rt - nb.lapse_start_rt) * 1000))
        doc = {"off": not self._nb_handback_on(), "held": nb.hb_held,
               "held_ms": int((self.rt - nb.hb_held_rt) * 1000) if nb.hb_held >= 0 else -1,
               "owed": nb.hb_held >= 0 and self._nb_guest_owned(nb.hb_held), "g6_mask": nb.g6_mask,
               "captures": nb.hb_captures, "returns": nb.hb_returns, "deferred": nb.hb_deferred,
               "faults": nb.hb_faults, "last": None if nb.hb_last is None else dict(nb.hb_last),
               "lapse": {"active": nb.lapse_armed and (nb.lapse_hold or lapse_left > 0), "hold": nb.lapse_armed
                         and nb.lapse_hold, "left_ms": lapse_left, "count": nb.lapse_count,
                         "end_frame": nb.lapse_end_frame}}
        if "ownreport" in self._nb_caps():
            # [ff9mapkit netsync R3 s118] HarnessHandbackRefusedReport / RefusedNow (the episode on a FRESH lane) / DioramaSeen
            doc.update(refused_report=nb.refused_report,
                       refused_now=nb.rpt_refused and self.rt - nb.lane_rt < BW.MENU_STALE_MS / 1000.0,
                       diorama_seen=nb.own_latch["seen"])
        return doc

    def _nb_bench_named(self, op: str, args: list, arg, int_min: int, out_of_range) -> None:
        """`netsync bench lapse <1-600000 ms>|hold|end` / `netsync bench handback 1|0` (s110): the agent's parse (exactly
        three arguments), then HarnessBenchLapse / HarnessHandback."""
        nb = self._nb
        if op == "lapse":
            la = args[2].lower() if len(args) > 2 else ""
            lms = arg(2, int_min)
            lhold, lend = la == "hold", la == "end" or lms == 0
            if "waitparity" in self._nb_caps():
                # [ff9mapkit netsync R3 s113] an optional 4th argument `reserve` (a timed or held lapse)
                reserve = len(args) == 4 and args[3].lower() == "reserve"
                if (len(args) != 3 and not reserve) or (not lhold and not lend and not 1 <= lms <= 600000) \
                        or (reserve and lend):
                    raise out_of_range("netsync bench lapse", "expected `netsync bench lapse <1-600000 ms>|hold|end` or "
                                       "`netsync bench lapse <1-600000 ms>|hold reserve`")
            else:
                reserve = False
                if len(args) != 3 or (not lhold and not lend and not 1 <= lms <= 600000):
                    raise out_of_range("netsync bench lapse", "expected `netsync bench lapse <1-600000 ms>|hold|end`")
            if not self._nb_role():
                raise RuntimeError("netsync bench lapse: needs the selftest role (netsync selftest 1)")
            if lend:
                self._nb_end_lapse()
                return
            if reserve and nb.lapse_last_ctl is None:
                raise RuntimeError("netsync bench lapse: `reserve` has no loopback control frame to re-serve -- arm it "
                                   "inside an own battle once the loopback guest has pumped")
            nb.lapse_reserve = reserve
            nb.lapse_armed, nb.lapse_hold = True, lhold
            nb.lapse_ms = 0 if lhold else lms
            nb.lapse_start_rt = self.rt
            nb.lapse_end_frame = -1
            nb.lapse_count += 1
            return
        hb = arg(2, -1)
        if len(args) != 3 or hb not in (0, 1):
            raise out_of_range("netsync bench handback", "expected `netsync bench handback 1|0`")
        if not self._nb_role():
            raise RuntimeError("netsync bench handback: needs the selftest role (netsync selftest 1)")
        nb.handback_off_lever = hb == 0

    def _nb_end_lapse(self) -> None:
        nb = self._nb
        if not nb.lapse_armed:
            return
        nb.lapse_armed = nb.lapse_hold = nb.lapse_reserve = False
        nb.lapse_end_frame = self.frame

    # ---- [ff9mapkit netsync R3] s111-s114: the intro mirror, the swirl clamp, Wait parity and the start hold
    def _nb_bench_r3(self, op: str, args: list, arg, out_of_range) -> None:
        """`netsync bench intro|cfg|swirl|waitparity|ctl|boot|starthold ...` (s111-s114): the agent's argument counts
        first (an ArgumentOutOfRangeException), then each Harness* entry point's role gate and refusals, in its words."""
        nb = self._nb
        if op == "intro":
            v = arg(2, -1)
            if len(args) != 3 or v not in (0, 1):
                raise out_of_range("netsync bench intro", "expected `netsync bench intro 1|0`")
            if not self._nb_role():
                raise RuntimeError("netsync bench intro: needs the selftest role (netsync selftest 1)")
            nb.intro_off_lever = v == 0
        elif op == "cfg":
            if len(args) != 4:
                raise out_of_range("netsync bench cfg", "expected `netsync bench cfg skipcam 0|1|restore` or `netsync "
                                   "bench cfg atb wait|active|restore`")
            if not self._nb_role():
                raise RuntimeError("netsync bench cfg: needs the selftest role (netsync selftest 1)")
            what, value = args[2].lower(), args[3].lower()
            if what == "atb" and "waitparity" in self._nb_caps():
                if value == "restore":
                    self._nb_cfg_restore("atb")
                    return
                if value not in ("wait", "active"):
                    raise RuntimeError("netsync bench cfg atb: expected wait|active|restore (the per-save ATB mode: Wait "
                                       "= 1, Active = 0)")
                if not nb.atb_set:
                    nb.atb_set, nb.atb_was = True, self.cfg_atb
                self.cfg_atb = 1 if value == "wait" else 0
                return
            if what != "skipcam":
                raise RuntimeError(f"netsync bench cfg: unknown setting '{what}' ("
                                   + ("skipcam|atb" if "waitparity" in self._nb_caps() else "skipcam") + ")")
            if value == "restore":
                self._nb_cfg_restore("skipcam")
                return
            if value not in ("0", "1"):
                raise RuntimeError("netsync bench cfg skipcam: expected 0|1|restore (0 = skip the intro camera on a "
                                   "random encounter)")
            if not nb.skipcam_set:
                nb.skipcam_set, nb.skipcam_was = True, self.cfg_skipcam
            self.cfg_skipcam = int(value)
        elif op == "swirl":
            if len(args) != 4:
                raise out_of_range("netsync bench swirl", "expected `netsync bench swirl local <frames>|ini` or `netsync "
                                   "bench swirl clamp <frames>|-1|ini`")
            if not self._nb_role():
                raise RuntimeError("netsync bench swirl: needs the selftest role (netsync selftest 1)")
            what, value = args[2].lower(), args[3].lower()
            ini = value == "ini"
            n = _int32(value)
            top = BW.SWIRL_BENCH_MAX_FRAMES
            if what == "local":
                if not ini and (n is None or not 0 <= n <= top):
                    raise RuntimeError(f"netsync bench swirl local: expected <0-{top} frames>|ini (this process's own "
                                       f"swirl; ini = [Graphics] BattleSwirlFrames)")
                nb.swirl_local = -1 if ini else n
            elif what == "clamp":
                if not ini and (n is None or not -1 <= n <= top):
                    raise RuntimeError(f"netsync bench swirl clamp: expected <0-{top} frames>|-1|ini (-1 = keep own; ini = "
                                       f"[Netsync] DioramaSwirlFrames)")
                nb.swirl_clamp_set, nb.swirl_clamp = not ini, -1 if ini else n
            else:
                raise RuntimeError(f"netsync bench swirl: unknown setting '{what}' (local|clamp)")
        elif op == "waitparity":
            v = arg(2, -1)
            if len(args) != 3 or v not in (0, 1):
                raise out_of_range("netsync bench waitparity", "expected `netsync bench waitparity 1|0`")
            if not self._nb_role():
                raise RuntimeError("netsync bench waitparity: needs the selftest role (netsync selftest 1)")
            nb.waitparity_off_lever = v == 0
        elif op == "ctl":
            if len(args) != 3:
                raise out_of_range("netsync bench ctl", "expected `netsync bench ctl auto|shut|legacy|root|deep`")
            if not self._nb_role():
                raise RuntimeError("netsync bench ctl: needs the selftest role (netsync selftest 1)")
            v = BW.BENCH_CTL.get(args[2].lower())
            if v is None:
                raise RuntimeError("netsync bench ctl: expected auto|shut|legacy|root|deep (the control byte 1 a Ready "
                                   "loopback / feed guest sends)")
            nb.bench_ctl = v
        elif op == "boot":
            if len(args) not in (3, 4):
                raise out_of_range("netsync bench boot", "expected `netsync bench boot auto|none|booting|live|declined|"
                                   "busy|stale|silent` or `netsync bench boot late <ms>`")
            if not self._nb_role():
                raise RuntimeError("netsync bench boot: needs the selftest role (netsync selftest 1)")
            name = args[2].lower()
            v = BW.BENCH_BOOT.get(name)
            if v is None:
                raise RuntimeError("netsync bench boot: expected auto|none|booting|live|declined|busy|stale|silent|late <ms>")
            late = 0
            if v == BW.BENCH_BOOT_LATE:
                late = _int32(args[3].strip()) if len(args) == 4 else None
                if late is None or not 0 <= late <= 600000:
                    raise RuntimeError("netsync bench boot late: needs <ms> 0-600000 (no control frame until that long "
                                       "after the host's command phase opens, then BOOTING)")
            elif len(args) == 4:
                raise RuntimeError(f"netsync bench boot {name}: takes no argument")
            nb.bench_boot, nb.bench_boot_late_ms = v, late
        elif op == "starthold":
            if len(args) not in (3, 4):
                raise out_of_range("netsync bench starthold", "expected `netsync bench starthold 1|0` or `netsync bench "
                                   "starthold cap <ms>|ini`")
            if not self._nb_role():
                raise RuntimeError("netsync bench starthold: needs the selftest role (netsync selftest 1)")
            a = args[2].lower()
            if a in ("1", "0") and len(args) == 3:
                nb.starthold_off_lever = a == "0"
                return
            if a == "cap" and len(args) == 4:
                c = args[3].strip().lower()
                ms = _int32(c)
                if c == "ini":
                    nb.starthold_cap_bench = -1
                elif ms is not None and 0 <= ms <= 600000:
                    nb.starthold_cap_bench = ms
                else:
                    raise RuntimeError("netsync bench starthold cap: expected 0-600000 ms, or ini (back to [Netsync] "
                                       f"StartHoldMs = {self.ini_start_hold_ms})")
                return
            raise RuntimeError("netsync bench starthold: expected 1|0|cap <ms>|cap ini")

    def _nb_cfg_restore(self, which: str) -> None:
        """BenchCfgRestoreSkipCam / BenchCfgRestoreAtb: the save's value back (a restore, or every harness release)."""
        nb = self._nb
        if which == "skipcam" and nb.skipcam_set:
            nb.skipcam_set, self.cfg_skipcam = False, nb.skipcam_was
        if which == "atb" and nb.atb_set:
            nb.atb_set, self.cfg_atb = False, nb.atb_was

    def _nb_intro_on(self) -> bool:
        """NetSyncBattle.IntroMirrorOn: the `bench intro 0` lever bites only in the selftest role."""
        return not (self._nb.intro_off_lever and self._nb_role())

    def _nb_intro_skipped(self, debug: bool) -> bool:
        """The intro the battle starting now plays: the stock test (cfg.skip_btl_camera 0 on a random encounter) -- or,
        in a booted diorama, NetSyncDiorama.SkipBattleIntro (the HOST's wire choice unless none or the lever), which also
        records `applied` / `own` / `calls`. An own battle latches its choice (NoteOwnBattleStart's _ownIntro)."""
        nb = self._nb
        stock = BW.own_intro_skipped(self.cfg_skipcam, self.battle_random)
        if not debug:
            nb.own_intro = 1 if stock else 0
            return stock
        skip = stock
        if nb.d_wire >= 0 and self._nb_intro_on():
            skip = nb.d_wire == 1
            nb.d_calls += 1
        nb.d_own, nb.d_applied = int(stock), int(skip)
        return skip

    def _nb_local_swirl(self) -> int:
        """NetSyncDiorama.LocalSwirlFrames: the `bench swirl local` stand-in, else [Graphics] BattleSwirlFrames."""
        return self._nb.swirl_local if self._nb.swirl_local >= 0 else self.cfg_swirl_frames

    def _nb_swirl_clamp(self) -> int:
        """NetSyncDiorama.SwirlClamp: the `bench swirl clamp` override, else [Netsync] DioramaSwirlFrames (-1 = off)."""
        return self._nb.swirl_clamp if self._nb.swirl_clamp_set else self.ini_swirl_clamp

    def _nb_record_swirl(self, booted: bool) -> None:
        """NetSyncDiorama.SwirlFrames from SFX_Rush's constructor: every swirl recorded (a diorama's clamped); its dwell is
        the nominal 30 Hz length (NOT MODELLED: the swirl's real frames -- the stand-in's boot keeps `dio_swirl_frames`)."""
        nb = self._nb
        own = self._nb_local_swirl()
        used = BW.swirl_frames(own, booted, self._nb_swirl_clamp())
        nb.sw_diorama, nb.sw_own, nb.sw_used, nb.sw_dwell_ms = booted, own, used, BW.swirl_ms(used)
        nb.sw_swirls += 1
        nb.sw_dioramas += 1 if booted else 0
        nb.sw_clamps += 1 if used != own else 0

    def _nb_start_hold_cap(self) -> int:
        """NetSyncBattle.StartHoldCapMs: the `bench starthold 0` lever (0), the bench cap, else [Netsync] StartHoldMs."""
        nb = self._nb
        if self._nb_role() and nb.starthold_off_lever:
            return 0
        if self._nb_role() and nb.starthold_cap_bench >= 0:
            return nb.starthold_cap_bench
        return self.ini_start_hold_ms

    def _nb_atb_frozen(self) -> bool:
        """BattleHUD.IsNativeEnableAtb's netsync gates on the HOST (an own battle, the command menu enabled): s114's start
        hold (HoldGate: every ATB mode), then s113's Wait freeze (cfg.atb 1: RemoteMenuDeep -- a fresh open guest window
        below its root, or any open one under the `bench waitparity 0` lever). Before s113 the stand-in models no remote
        freeze at all (NOT MODELLED: the GuestWaitMs cap, turn-based Speed < 3)."""
        nb, caps = self._nb, self._nb_caps()
        if nb.own_epoch is None or not self.commands_enabled:
            return False
        if "starthold" in caps and nb.hold is not None and \
                BW.hold_gate(nb.hold, int(self.rt * 1000), self._nb_start_hold_cap()):
            return True
        return "waitparity" in caps and self.cfg_atb == 1 and self._nb_remote_deep()

    def _nb_remote_open(self) -> bool:
        """NetSyncBattle.RemoteMenuOpen: an open window on a fresh control lane (MenuStaleMs)."""
        nb = self._nb
        return nb.remote_menu and self.rt - nb.assist_rt < BW.MENU_STALE_MS / 1000.0

    def _nb_remote_deep(self) -> bool:
        """NetSyncBattle.RemoteMenuDeep (the Wait freeze)."""
        on = not (self._nb.waitparity_off_lever and self._nb_role())
        return BW.remote_menu_deep(self._nb_remote_open(), self._nb.remote_byte, on)

    def _nb_guest_control(self, view_nonce: int, ready: bool, *, deep: bool = False, booted_live: bool | None = None,
                          src_deep: str = "stock") -> tuple:
        """NetSyncBattle.GuestControl: the frame this process's GUEST side sends this tick -> ``(frame | None, src)``.
        Byte 1: 0 with no Ready guest slot, the `bench ctl` byte, 3 below the root (``deep``), else 2; s114's trailer
        reports on ``view_nonce`` -- the `bench boot` value, else the guest's own (``booted_live``: None = the selftest
        loopback, no diorama -> NONE; else a wire boot of that nonce -> LIVE / BOOTING). `silent` and an early `late`
        send no frame at all (None)."""
        nb, caps = self._nb, self._nb_caps()
        if not ready:
            menu, src = BW.CTL_SHUT, "none"
        elif nb.bench_ctl >= 0 and self._nb_role():
            menu, src = nb.bench_ctl, "bench"
        elif deep:
            menu, src = BW.CTL_DEEP, src_deep
        else:
            menu, src = BW.CTL_ROOT, "root"
        if "starthold" not in caps:
            return BW.encode_control(menu), src
        b, nonce = nb.bench_boot if self._nb_role() else -1, view_nonce
        if b == BW.BENCH_BOOT_SILENT:
            return None, src
        if b == BW.BENCH_BOOT_LATE:
            # none until <ms> after the HOST's command phase opened (its hold's own opening tick), then BOOTING; a feed
            # diorama (no own battle, no hold) reports BOOTING at once
            h = nb.hold
            if h is not None and (not h["open_seen"] or int(self.rt * 1000) - h["open_tick"] < nb.bench_boot_late_ms):
                return None, src
            b = BW.BOOT_BOOTING
        elif b == BW.BENCH_BOOT_STALE:
            b, nonce = BW.BOOT_LIVE, (view_nonce - 1) & 0xFF
        elif b < 0:
            b = BW.BOOT_NONE if booted_live is None else (BW.BOOT_LIVE if booted_live else BW.BOOT_BOOTING)
        return BW.encode_control(menu, nonce, b), src

    def _nb_parse_control(self, frame, loopback_auto: bool = False) -> None:
        """NetSyncBattle.ParseControl on the HOST (s113 byte 1 = the depth; s114 the trailer behind the byte-1 nonce gate):
        a valid frame stamps the lane; null (a stale socket / a lapse) and a malformed frame shut the menu flag.
        [ff9mapkit netsync R3 s118] TWO stamps: the LANE (any valid frame) and the OWNERSHIP one (`assist_rt`, what
        IsGuestOwnedSlot reads), which a frame earns only through GuestOwnsStep -- no report, LIVE / BOOTING on this
        battle, or NONE before the per-battle latch (``loopback_auto``: SelfTestPump's own frame under `bench boot auto`
        owns as before); a frame that does not own reads byte 1 shut and starts / continues a refusal episode."""
        nb, caps = self._nb, self._nb_caps()
        if frame is None:
            nb.remote_menu, nb.remote_seen = False, -1
            if nb.hold is not None and nb.hold["primed"] and not nb.hold["released"]:
                nb.ctl_null_seen = True               # the transport's silence verdict while the hold is primed
            return
        owning = "ownreport" in caps
        if owning:                                    # [ff9mapkit netsync R3 s118] the step runs first (the latch notes it)
            d = BW.parse_control_owned(frame, nb.nonce, nb.own_latch, loopback_auto)
        else:
            d = BW.decode_control(frame, nb.nonce) if "starthold" in caps else \
                ({"menu": frame[1], "trailer": False, "nonce": -1, "boot": -1} if BW.control_valid(frame) else None)
        if d is None:
            nb.remote_menu, nb.remote_seen = False, -1
            return
        nb.lane_rt = self.rt
        if d.get("owns", True):
            nb.assist_rt = self.rt                    # (before s118: any valid control frame)
        nb.remote_byte, nb.remote_seen, nb.remote_menu = d["menu"], d["menu"], d["menu"] != 0
        if d["menu"] == BW.CTL_LEGACY:
            nb.legacy_seen = True
        if "starthold" in caps:
            data = bytes(frame)
            nb.rpt_fmt = data[2] if len(data) > 2 else 0
            nb.ctl_trailer = d["trailer"]
            if d["trailer"]:
                nb.rpt_nonce, nb.rpt_boot, nb.rpt_rt, nb.guest_r3 = d["nonce"], d["boot"], self.rt, True
                nb.last_ctl_legacy = False
            else:
                nb.last_ctl_legacy = True
        if owning:
            if d["owns"]:
                nb.rpt_refused = nb.rpt_refused_counted = False   # the refusal episode (if any) ends here
            else:
                self._nb_note_refused_report()

    def _nb_note_refused_report(self) -> None:
        """[ff9mapkit netsync R3 s118] NoteRefusedReport, on every valid frame whose report keeps the slots here: the
        episode flag (`handback.refused_now`, the capture line); then, only with guest slots set and the host's command
        phase open, one count per episode (`refused_report`) and one line per own battle (the end-leave stays quiet)."""
        nb = self._nb
        nb.rpt_refused = True
        if nb.rpt_refused_counted or not nb.guest_slots or not nb.phase_open:
            return
        nb.rpt_refused_counted = True
        nb.refused_report += 1
        if nb.rpt_refused_logged:
            return
        nb.rpt_refused_logged = True
        self._nb_handback_log(
            BW.LOG_HANDBACK_REFUSED + BW.refused_report_phrase(nb.rpt_nonce, nb.rpt_boot, nb.nonce)
            + " -- its slots stay with the host's window (the host's ready loop commands them; G3 hands them back at the "
              "command root once it reports live or booting on this battle; logged once per own battle), refused_report="
            + str(nb.refused_report))

    def _nb_handback_log(self, line: str) -> None:
        """HandbackLog: HandbackLogBudget hand-back lines per own battle, then silence (the last one says so)."""
        nb = self._nb
        if nb.hb_logs >= BW.HANDBACK_LOG_BUDGET:
            return
        nb.hb_logs += 1
        self._mlog(line if nb.hb_logs < BW.HANDBACK_LOG_BUDGET
                   else line + " (the last hand-back line this battle -- the harness counters keep counting)")

    def _nb_loopback_control(self, caps, ready: bool) -> None:
        """SelfTestPump's control lane in an own battle (s113+): the loopback guest's frame (GuestControl), a `bench lapse`
        (none -- or, `reserve`, the last pre-lapse frame for LAPSE_RESERVE_MS), then the HOST's ParseControl of it."""
        nb = self._nb
        frame, src = self._nb_guest_control(nb.nonce, ready)
        auto = nb.bench_boot < 0                            # [ff9mapkit netsync R3 s118] ParseControl(..., BenchBoot < 0)
        if "handback" in caps and self._nb_lapse_tick():
            if nb.lapse_reserve and self.rt - nb.lapse_start_rt < BW.LAPSE_RESERVE_MS / 1000.0:
                self._nb_parse_control(nb.lapse_last_ctl, auto)
            else:
                self._nb_parse_control(None)
            return
        nb.ctl_out, nb.ctl_src = frame, src if frame is not None else None
        if frame is not None:
            nb.lapse_last_ctl = frame
        self._nb_parse_control(frame, auto)

    def _nb_start_hold_tick(self) -> None:
        """NetSyncBattle.StartHoldTick (both pumps, after the control parse): one StartHoldStep, its counters and the
        opening's / release's reasons (the agent's `start_hold` keys)."""
        nb = self._nb
        h = nb.hold
        if h is None:
            return
        now = int(self.rt * 1000)
        cap = self._nb_start_hold_cap()
        rpt_this = nb.ctl_trailer and nb.rpt_nonce == nb.nonce and self.rt - nb.rpt_rt < BW.MENU_STALE_MS / 1000.0
        held = now - h["since_tick"] if h["armed"] and not h["released"] and h["started"] else 0
        ev = BW.start_hold_step(h, now, cap > 0, cap, nb.phase_open, rpt_this, nb.rpt_boot, nb.ctl_null_seen,
                                nb.last_ctl_legacy)
        if ev == BW.HOLD_ARMED:
            nb.hold_count += 1
            nb.hold_why = "booting"
        elif ev == BW.HOLD_LATE_ARMED:
            nb.hold_count += 1
            nb.hold_why, nb.hold_late_ms = "late", h["late_ms"]
        elif ev == BW.HOLD_NOT_ARMED:
            nb.hold_why = self._nb_not_armed_why(rpt_this)
        elif ev in BW.HOLD_RELEASE_NAMES:
            self._nb_release_hold(ev, held)

    def _nb_not_armed_why(self, rpt_this: bool) -> str:
        """NetSyncBattle.NotArmedWhy's short key."""
        nb = self._nb
        if rpt_this:
            return {BW.BOOT_LIVE: "live", BW.BOOT_DECLINED: "declined", BW.BOOT_BUSY: "busy", BW.BOOT_NONE: "none",
                    BW.BOOT_BOOTING: "link"}.get(nb.rpt_boot, "unknown")
        fresh = self.rt - nb.rpt_rt < BW.MENU_STALE_MS / 1000.0
        if nb.ctl_trailer and fresh:
            return "stale nonce"
        if nb.last_ctl_legacy and self.rt - nb.lane_rt < BW.MENU_STALE_MS / 1000.0:   # (s118: the LANE's stamp)
            return "old guest"
        return "no word yet"

    def _nb_release_hold(self, ev: int, held_ms: int) -> None:
        """NetSyncBattle.ReleaseStartHold: final, counted (per reason), the release's name and held length."""
        nb = self._nb
        if nb.hold is not None:
            nb.hold["released"] = True
        key = BW.HOLD_RELEASED_KEYS.get(ev)
        if key is not None:
            nb.released[key] += 1
        nb.hold_release, nb.hold_held_ms = BW.HOLD_RELEASE_NAMES[ev], max(0, held_ms)

    def _nb_hold_doc(self) -> dict:
        """`netsync.battle.host.start_hold` (AppendHostStartHold)."""
        nb = self._nb
        cap = self._nb_start_hold_cap()
        h = nb.hold
        held = int(self.rt * 1000) - h["since_tick"] if h is not None and BW.hold_bit(h) else nb.hold_held_ms
        lane = int((self.rt - nb.lane_rt) * 1000)           # [ff9mapkit netsync R3 s118] the LANE's stamp (= assist's before)
        return {"off": cap <= 0, "cap_ms": cap, "state": BW.hold_state_name(h, cap), "nonce": nb.hold_nonce,
                "why": nb.hold_why, "release": nb.hold_release, "held_ms": held, "late_ms": nb.hold_late_ms,
                "count": nb.hold_count, "released": dict(nb.released),
                "guest": {"r3": nb.guest_r3, "lane_ms": lane if 0 <= lane < BW.STALL_MEMORY_MS else -1,
                          "fmt": nb.rpt_fmt, "nonce": nb.rpt_nonce, "boot": nb.rpt_boot,
                          "boot_name": BW.boot_name(nb.rpt_boot)}}

    def _nb_diorama_r3_tick(self) -> None:
        """NetSyncDiorama.LiveTick (s111: the first steady frame -> `normal_ms`; s114: the LIVE latch -- a steady frame with
        a host sample in hand, the bench feed's live view here)."""
        nb, caps = self._nb, self._nb_caps()
        if not self._nb_active() or not self.commands_enabled or self._battle_phase_now() != BW.PHASE_NORMAL:
            return
        ms = int((self.rt - nb.d_boot_rt) * 1000)
        if "intro" in caps and nb.d_normal_ms < 0:
            nb.d_normal_ms = ms
        view = self._nb_feed_view_live() if "mirror" in caps else None
        if "starthold" in caps and not nb.live_latched and view is not None:
            nb.live_latched, nb.live_ms, nb.live_nonce = True, ms, view["nonce"]
        if "actreplay" in caps:
            # [ff9mapkit netsync s134] ActLaneTick: the bit-5 latch from the live view, and the lane edge the bench drain reads
            self._act_guest.lane_tick(view is not None, self._nb_role(),
                                      caps=(view or {}).get("caps", -1) if view is not None else -1, booted=True)

    # -- [ff9mapkit netsync s134] the guest action replay ----------------------------------------------------------------
    def _act_guest_resolve(self, index: int, is_player: bool) -> dict | None:
        """ResolveWireUnit, as the stand-in models it: a player wire index i -> the player in btl slot i (the stand-in's
        party sits in slots 0-3 in order: the compacted-party lookup is not modelled), an enemy wire index 4-7 -> the enemy
        in that btl slot."""
        if index < 0 or index > 7:
            return None
        if is_player:
            return next((u for u in self.battle_units if u.get("player") and u.get("slot") == index), None)
        if index < 4:
            return None
        return next((u for u in self.battle_units if not u.get("player") and u.get("slot") == index), None)

    def _act_guest_ctx(self) -> dict:
        """What ActTick / ActionTickBench read off the diorama (battlewire.ActGuestLane.tick's ``ctx``)."""
        nb = self._nb
        ms = int(self.rt * 1000)
        return {"booted": bool(self._dio["booted"]), "role": self._nb_role(),
                "steady": self._nb_active() and self._battle_phase_now() == BW.PHASE_NORMAL,
                "normal_latched": nb.d_normal_ms >= 0, "live_latched": bool(nb.live_latched),
                "paused": bool(self.battle_paused), "now_ms": ms, "wall_ms": ms, "end_injected": bool(nb.injected),
                "r8_hits": int(nb.r8_hits), "end_presented": self._nb_hud_off(), "leaving": self._dio_leave_recently(),
                "hidden_mask": 0, "resolve": self._act_guest_resolve,
                # [ff9mapkit netsync s136] fallback A's collapse reads Time.frameCount; its sequence cache keys the scene
                "frame": self.frame, "scene": self.battle_scene,
                # [ff9mapkit netsync s135] btl2d's own gate for a figure (bi.disappear): a faded runner shows none
                "disappeared": lambda u: bool(self._nb.unit_r3.get(u.get("slot"), {}).get("disappear", 0)),
                "linked": lambda u: any(x is u for x in self.battle_units), "units": self.battle_units}

    def _act_guest_tick(self) -> None:
        """[ff9mapkit netsync s134] NetSyncClient's selftest branch: ActionTickBench (the bench inbox through ActRouteFrame),
        then ActTick -- after SelfTestPump, before EndTick and LiveTick (design 3.3.3's selftest order)."""
        ctx = self._act_guest_ctx()
        self._act_guest.drain_bench(ctx)                    # (its due times read the clock the previous ActTick set)
        self._act_guest.tick(ctx)
        self._act_flush()

    # ---- [ff9mapkit netsync R3] s115-s117: the run-away, the annihilation, the defeat
    def _nb_players(self) -> list:
        return [u for u in self.battle_units if u.get("player")]

    def _nb_all_down(self) -> bool:
        """NetSyncDiorama.AllPlayersDown: every linked player under BattleEndFull (the stand-in: Death), at least one."""
        players = self._nb_players()
        return BW.all_down(len(players), sum(1 for u in players if not u.get("alive", True)))

    def _nb_kill(self, mask: int) -> None:
        """NetSyncDiorama.HarnessKillPlayers: the reconciler's KillUnit on every seated player whose btl_id bit is in
        ``mask`` -- HP 0, Death, the death pose (MP_DISABLE) -- BTL_DATA only; refused off a live PHASE_NORMAL diorama."""
        if not self._dio["booted"] or not self._nb_active():
            raise RuntimeError("netsync endbench kill: needs a booted battle diorama (`netsync dioboot <scene>`)")
        phase = self._battle_phase_now()
        if phase != BW.PHASE_NORMAL:
            raise RuntimeError(f"netsync endbench kill: needs the diorama in PHASE_NORMAL (phase {phase})")
        matched = [u for u in self._nb_players() if u.get("id", 0) & mask]
        if not matched:
            raise RuntimeError(f"netsync endbench kill: no linked player's btl_id is in mask 0x{mask:X}")
        for u in matched:
            if not u.get("alive", True):
                continue
            u.update(hp=0, hp_raw=0, alive=False)
            self._nb.unit_r3.setdefault(u["slot"], {})["mot"] = BW.MP_DISABLE

    def _nb_flee_penalty(self) -> int:
        """The stock default flee method's gil penalty (NOT the engine's formula: a tenth of the save's gil)."""
        return self.save_gil // 10

    def _nb_run_step(self) -> None:
        """The run-away, one frame (battle.cs SEQ_MENU_OFF_ESCAPE): each runner's z falls 100 a frame; once the run is
        over the escape fade has finished and every runner reads `disappear` 5."""
        nb = self._nb
        done = self.frame >= nb.run_until
        for r in nb.unit_r3.values():
            if r.get("mot") != BW.MP_ESCAPE:
                continue
            if done:
                r["disappear"] = BW.DISAPPEAR_DONE
            else:
                r["z"] = r.get("z", -600.0) - 100.0

    def _nb_standing(self) -> int:
        """MenuOffBlocker's defeat row: visible players neither down (MP_DISABLE) nor dead."""
        return sum(1 for u in self._nb_players()
                   if u.get("alive", True) and self._nb.unit_r3.get(u["slot"], {}).get("mot") != BW.MP_DISABLE)

    def _nb_defeat_song(self) -> None:
        """PHASE_DEFEAT's BattleIdleLoop: ManageBattleSong(30, 6) -- song 6 and BTL_SONG_FADEOUT | BTL_PLAY_END_SONG in a
        Game-Over scene only (btl_scene.Info.NoGameOver gates the call); BTL_END_LOAD either way."""
        nb = self._nb
        nb.btl_flag |= BW.BTL_END_LOAD
        if not self.scene_no_gameover:
            nb.btl_flag |= BW.BTL_PLAY_END_SONG | BW.BTL_SONG_FADEOUT
            nb.music = 6

    def _nb_flee_gil_tick(self, ours: bool, e: dict | None) -> None:
        """NetSyncDiorama.FleeGilTick (s116): FleeMsgVerdict over this boot's run-away -- the HOST's figure shown once,
        through the stock follow message ("dropped-gil"), never the guest's own gil."""
        nb = self._nb
        flags = e.get("flee_flags", -1) if ours and e is not None else -1
        gil = e.get("flee_gil", -1) if ours and e is not None else -1
        v = BW.flee_msg_verdict(nb.action, nb.flee_r9b, nb.r8_hits, nb.flee_msg_gil >= 0, ours, flags, gil)
        if v == BW.FLEE_MSG_SHOW:
            nb.flee_msg_gil = gil
            nb.follow_msg = BW.FOLLOW_MSG_DROPPED_GIL


    def _nb_lapse_tick(self) -> bool:
        """BenchLapseTick (SelfTestPump, before its ParseControl): True while a lapse holds the loopback guest silent; the
        first tick after a timed lapse runs out ends it."""
        nb = self._nb
        if not nb.lapse_armed:
            return False
        if not self._nb_role():
            self._nb_end_lapse()
            return False
        if nb.lapse_hold or self.rt - nb.lapse_start_rt < nb.lapse_ms / 1000.0:
            return True
        self._nb_end_lapse()
        return False

    def _nb_host_held(self) -> int:
        """HostHeldGuestSlot: the GuestSlots slot the host's OWN window holds (CurrentPlayerIndex), PHASE_NORMAL only."""
        nb, s = self._nb, self.battle_turn
        if not nb.guest_slots or self._battle_phase_now() != BW.PHASE_NORMAL:
            return -1
        return s if 0 <= s < 4 and nb.guest_slots & (1 << s) else -1

    def _nb_track_hold(self) -> None:
        """TrackHostHold: a change of the held guest slot -- a hold counts as a capture (the counter counts under the
        lever too)."""
        nb = self._nb
        held = self._nb_host_held()
        if held == nb.hb_held:
            nb.handback_edge = False
            return
        nb.handback_edge = False
        # [ff9mapkit netsync R3] its lines (HandbackLog), logged only for a STALL -- the lane fresh within StallMemoryMs (s118:
        # the LANE's stamp, so a guest whose report keeps the slot is logged, naming the report)
        stall = self.rt - nb.lane_rt < BW.STALL_MEMORY_MS / 1000.0
        if nb.hb_held >= 0 and stall:
            self._nb_handback_log(f"[NetSync] hand-back: the host's window on guest slot {nb.hb_held} closed after "
                                  f"{int((self.rt - nb.hb_held_rt) * 1000)} ms by itself (the host's own pick, a KO, or "
                                  f"the turn or the battle ending) -- nothing to hand back")
        nb.hb_held, nb.hb_defer_noted = held, False
        if held >= 0:
            nb.hb_held_rt = self.rt
            nb.hb_captures += 1
            if stall:
                silent_ms = int((self.rt - nb.lane_rt) * 1000)
                if silent_ms >= BW.MENU_STALE_MS:
                    why = f"the guest's control lane has been silent {silent_ms} ms (a stall)"
                elif nb.rpt_refused and "ownreport" in self._nb_caps():
                    why = ("the guest's control lane is live but "
                           + BW.refused_report_phrase(nb.rpt_nonce, nb.rpt_boot, nb.nonce)
                           + " (its diorama is not live on it: the host keeps the slot)")
                else:
                    why = "the slot became a guest slot while the host's window held it (a GuestSlots change)"
                self._nb_handback_log(
                    BW.LOG_HANDBACK_CAPTURE + f"{held} -- {why}"
                    + ("; its Ready bit is withheld while the host holds it (G6), and it is handed back at the command "
                       "root once the guest is live again (G3)" if self._nb_handback_on()
                       else " -- hand-back lever OFF (calibration): no G6, no hand-back")
                    + f"; captures={nb.hb_captures}")

    def _nb_hand_back(self) -> None:
        """HandBackGuestSlot (G3), level-triggered after ParseControl: a held slot the guest owns again goes back at the
        command ROOT (SetIdle; it stays on ReadyQueue and the HUD skips it); anywhere else the hand-back WAITS (counted and
        noted once per hold)."""
        nb = self._nb
        if not self._nb_handback_on() or not nb.guest_slots:
            return
        slot = self._nb_host_held()
        if slot < 0 or not self._nb_guest_owned(slot):
            return
        held_ms = int((self.rt - nb.hb_held_rt) * 1000) if slot == nb.hb_held else -1
        group = self.menu.get("group")
        if self.quit_prompt or group != "Battle.Command":
            if not nb.hb_defer_noted:
                nb.hb_defer_noted = True
                nb.hb_deferred += 1
                why = ("the host's Quit prompt is up" if self.quit_prompt else
                       f"the host's window is in a submenu ({group})" if group in ("Battle.Ability", "Battle.Item",
                                                                                   "Battle.Target") else
                       "the host's command window is hidden, paused or disabled" if not group else
                       f"another UI holds the buttons ({group})")
                nb.hb_last = {"slot": slot, "frame": self.frame, "held_ms": held_ms, "why": "deferred: " + why}
                self._nb_handback_log(f"[NetSync] hand-back: guest slot {slot} is the guest's again, but the hand-back "
                                      f"WAITS -- {why}; the host finishes its own pick (root-only, owner decision 4; logged "
                                      f"once per hold), deferred={nb.hb_deferred}")
            return
        self.battle_turn = -1                               # SetIdle + SetPartySwapButtonActive(false)
        self._close_battle_cursor()
        if slot == nb.hb_held:
            nb.hb_held, nb.hb_defer_noted, nb.handback_edge = -1, False, True
        nb.hb_returns += 1
        nb.hb_last = {"slot": slot, "frame": self.frame, "held_ms": held_ms, "why": "handed back"}
        self._nb_handback_log(f"[NetSync] hand-back: guest slot {slot}{BW.LOG_HANDBACK_HANDED}its control lane is live "
                              f"again and the host's window sat at the command root (held {held_ms} ms); the host's "
                              f"window closed, the slot's Ready bit returns (BTL-1), returns={nb.hb_returns}")

    # ---- the per-frame lane: an own battle's host gates (SelfTestPump) and a diorama's end presentation (EndTick)
    def _battle_phase_now(self) -> int:
        """The battle's btl_phase as the stand-in runs it: the presentation's own once it moved it, the CLOSE fade of a
        `battle_exit` end, NORMAL once the opening camera is over, PHASE_ENTER through it."""
        if self._nb.phase is not None:
            return self._nb.phase
        if self._bexit is not None:
            return BW.PHASE_CLOSE
        return BW.PHASE_NORMAL if self.frame >= self._intro_until else BW.PHASE_ENTER

    def _battle_seq_now(self) -> int:
        if self._nb.seq is not None:
            return self._nb.seq
        if self._bexit is not None:
            return BW.SEQ_DEFEATCLOSE_FADEOUT if self._bexit[0] == "fade" else BW.SEQ_DEFEATCLOSE_WAIT
        return 0

    def _step_netsync_battle(self) -> None:
        """One frame of the battle lane: a selftest OWN battle's pump (rising / falling edges included), and a booted
        diorama's EndTick."""
        caps = self._nb_caps()
        if "gates" not in caps:
            return
        nb = self._nb
        own = (self.battle_active and not self.battle_debug and not self._dio["booted"] and self._nb_role())
        if own:
            if nb.own_epoch != self.battle_epoch:
                self._nb_own_start()
            self._nb_pump_own(caps)
        elif nb.own_epoch is not None:
            self._nb_own_end()
        if "actreplay" in caps and self._dio["booted"] and self._nb_role():
            self._act_guest_tick()                          # [ff9mapkit netsync s134] ActionTickBench -> ActTick
        if "intro" in caps and self._nb_active():
            self._nb_diorama_r3_tick()                      # [ff9mapkit netsync R3 s111/s114] LiveTick
        if "present" in caps and self._nb_active() and self._nb_role():
            self._nb_end_tick(caps)
        if self._nb_active() and nb.phase is not None:
            self._nb_present_step()
        if "content" in caps:                               # [ff9mapkit netsync B4] s106: the HUD frame's repaint check
            self._nb_content_tick()
        if "mirror" in caps:                                # [ff9mapkit netsync B4] s107: the bench feed, then StockMenuTick
            self._nb_feed_tick()
            self._nb_mirror_tick()
            self._nb_drain_outbox()
            if "waitparity" in caps and nb.feed is not None and nb.own_epoch is None:
                frame, src = self._nb_feed_control()        # [ff9mapkit netsync R3 s113] the feed records the frame Pump
                if frame is not None:                       # would send: `menu.ctl` reads it back
                    nb.ctl_out, nb.ctl_src = frame, src
        if "replay" in caps:                                # [ff9mapkit netsync B5] s109: the replay's screen
            self._nb_replay_open()
            self._nb_screen_tick()

    def _nb_own_start(self) -> None:
        """An own battle's rising edge (NoteOwnBattleStart + the nonce bump + NetSyncEnd.NoteHostBattleStart)."""
        nb = self._nb
        nb.own_epoch = self.battle_epoch
        nb.own_battles += 1
        nb.nonce = (nb.nonce + 1) & 0xFF
        nb.phase_open = False
        nb.phase_open_frame = -1
        nb.roster_lag = -1
        nb.roster_slots = []
        nb.roster_next_rt = self.rt + 1.0
        nb.refuse_logged.clear()
        nb.host_key = None
        nb.host_end = None
        nb.host_changes = 0
        nb.host_edges = 0
        nb.host_trail = []
        nb.host_trail_key = -1
        if nb.bench_armed:                                  # DisarmStaleBenchEnd: the loopback's real block serves now
            nb.bench_armed = False
            nb.bench_block = None
        nb.peer = None
        nb.hb_held, nb.hb_defer_noted, nb.handback_edge, nb.g6_mask = -1, False, False, -1   # [ff9mapkit netsync B4] s110
        nb.hb_logs = 0                                      # ...and the hand-back lines' budget re-arms
        # [ff9mapkit netsync R3 s118] a refusal is counted and logged per own battle, and a NONE owns again until the guest
        # reports a diorama of THIS battle
        nb.rpt_refused = nb.rpt_refused_counted = nb.rpt_refused_logged = False
        nb.own_latch["seen"] = False
        # [ff9mapkit netsync R3 s113/s114] NoteOwnBattleStart: a fresh hold for this nonce, the edge's flags cleared (the
        # previous battle's why / release / held / late stay readable until now)
        nb.legacy_seen = False
        nb.hold = BW.new_hold_state()
        nb.hold_nonce = nb.nonce
        nb.hold_why = nb.hold_release = None
        nb.hold_held_ms = nb.hold_late_ms = -1
        nb.ctl_null_seen = nb.last_ctl_legacy = False
        if "actstart" in self._nb_caps():
            self._act_lane.battle_start(nb.nonce)           # [ff9mapkit netsync s133] ActBattleStart, after the nonce bump

    def _nb_own_end(self) -> None:
        """An own battle's falling edge (NoteOwnBattleEnd): the host's "last sample" reads -1, `host.end` null, the lane
        is no longer live (the trails stay readable). [ff9mapkit netsync B4] s110: the hold ends and a lapse with it.
        [ff9mapkit netsync s133] SelfTestPump's falling edge closes the own battle's action lane (no_end vs cut) before Reset
        -- and Reset DISCARDS the frames buffered since the last in-battle tick unsent, as Pump's falling edge does (the
        loopback models the wire: they never reach the audit or the tape)."""
        nb = self._nb
        if "actstart" in self._nb_caps():
            self._act_lane.close_battle(False, mid_action=False)
            self._act_lane.out.clear()
            self._act_flush()
        nb.own_epoch = None
        nb.phase_open = False
        nb.last_caps = -1
        nb.last_ready = -1
        nb.host_end = None
        nb.host_key = None
        nb.peer = None
        nb.hb_held, nb.hb_defer_noted, nb.handback_edge, nb.g6_mask = -1, False, False, -1
        self._nb_end_lapse()
        # [ff9mapkit netsync R3] NoteOwnBattleEnd: a hold still holding dies with its battle ("ended"); the intro latch and
        # the host's decode of the lane go (`host.wait.menu` -1)
        h = nb.hold
        if h is not None and h["armed"] and not h["released"]:
            self._nb_release_hold(BW.HOLD_REL_ENDED, int(self.rt * 1000) - h["since_tick"] if h["started"] else 0)
        nb.hold, nb.hold_nonce = None, -1
        nb.own_intro = -1
        nb.remote_seen = -1
        nb.remote_menu = False
        nb.ctl_null_seen = nb.last_ctl_legacy = False

    # -- [ff9mapkit netsync s133] the host action-start lane ------------------------------------------------------------
    #: The stand-in's describe (btl_vfx.DescribeCommandVfx's kind and number) for ITS command ids (MENU_COMMANDS: shapes,
    #: not real FF9 ids): Attack the weapon's SpecialEffect (one number per caster slot, as a weapon serial is), Defend
    #: COMMON, a Blk Mag ability and an item their sub_no as a SpecialEffect, an enemy's EnemyAtk its sub (kind 2).
    ACT_FAKE_ATTACK_SFX = 100

    def _act_describe(self, slot: int, cmd: int, sub: int) -> tuple:
        if cmd == BW.CMD_ENEMY_ATK:
            return BW.VFX_KIND_ENEMY, sub
        if cmd == 1:
            return BW.VFX_KIND_SPECIAL, self.ACT_FAKE_ATTACK_SFX + slot
        if cmd == 2:
            return BW.VFX_KIND_COMMON, cmd
        if cmd in (4, 8):
            return BW.VFX_KIND_SPECIAL, sub
        return BW.VFX_KIND_NONE, 0

    def _act_command(self, slot: int, cmd: int, sub: int, tar_id: int, cursor: int, hits: list) -> None:
        """[ff9mapkit netsync s133] One resolved command on the HOST's action-start lane (battlewire.ActHostLane): the START
        (QueueActionStart's gate: [Netsync] Enabled, no booted diorama, !isDebug, the lever, the pump's rising edge; the
        actor's wire slot), the describe check (SelectCommandVfx is modelled as running what was described: no drift), one
        impact per unit hit (QueueActionFrame's 46 bytes + the id), then the END (FinishCommand). NOT MODELLED: the
        stand-in resolves a command in ONE frame, so START, impacts and END land in the same tick (the engine spreads them
        over the sequence; the FIFO order is the same) -- no command is ever open across a falling edge (no `no_end` / `cut`
        from a stand-in battle), no scripted sequence (StartBtlSeq: `scripted` 0), no stat tick, no counter / double-cast
        slot, no unresolved actor, no buffer drop at the stand-in's action rates; the old engine is never modelled
        (`vfx.unchecked` 0). The seqs follow the STATE-WRITE<=>HORIZON law: each impact stamps the sample clock and CONSUMES
        it (the engine's ``bw.Write(_seq++)``), the START and the END stamp it without consuming -- so the next sample's seq
        is past every impact's horizon."""
        if "actstart" not in self._nb_caps():
            return
        nb, lane, ns = self._nb, self._act_lane, self.netsync
        role = self._nb_role()
        unit = next((u for u in self.battle_units if u["slot"] == slot), None)
        if unit is None:
            return
        player = bool(unit.get("player"))
        gate = dict(enabled=bool(ns["enabled"]), booted=bool(self._dio["booted"]), is_debug=bool(self.battle_debug))
        key = ("cmd0", slot)                                # a unit's cmd[0], reused turn after turn as the engine's is
        nonce = nb.nonce
        kind, num = self._act_describe(slot, cmd, sub)
        flags = (BW.ACTOR_IS_PLAYER if player else 0) | BW.ACTOR_HOST_REWORK | (
            BW.ACTOR_HOST_FAST if self.cfg_speed >= 3 else 0)
        lane.start(key, scripted=False, actor_slot=slot, actor_flags=flags, cmd_no=cmd, sub_no=sub, tar_id=tar_id,
                   nonce=nonce, seq=nb.wire_seq, selftest_role=role, was_in_battle=nb.own_epoch == self.battle_epoch,
                   cursor=cursor, vfx=(kind, num), host_speed=self.cfg_speed, **gate)
        added = None if kind == BW.VFX_KIND_NONE else (kind == BW.VFX_KIND_ENEMY, num if kind in (
            BW.VFX_KIND_ENEMY, BW.VFX_KIND_SPECIAL) else 0)
        lane.check_vfx(key, rework=True, added=added)
        for target, damage in hits:
            fl = (1 if damage else 0) | (32 if target.get("player") else 0) | (64 if player else 0)
            legacy = BW.encode_action_impact(nonce, nb.wire_seq, slot, target["slot"], fig_t=(0, damage, 0),
                                             raws=(target.get("hp_raw", 0), 0, unit.get("hp_raw", 0), 0), flags=fl,
                                             cmd_no=cmd, sub_no=sub)
            if lane.impact(key, legacy, selftest_role=role, **gate) is not None:
                nb.wire_seq = (nb.wire_seq + 1) & 0xFFFF   # QueueActionFrame's `_seq++`: the horizon CONSUMED
        lane.end(key, nonce=nonce, seq=nb.wire_seq, enabled=gate["enabled"])
        self._act_flush()

    def _act_flush(self) -> None:
        """The lane's new Log.Message lines into Memoria.log (Memoria's line shape). [ff9mapkit netsync s134] ...and the
        guest replay lane's."""
        lines = self._act_lane.lines
        for text in lines[self._act_logged:]:
            self._mlog(text)
        self._act_logged = len(lines)
        lines = self._act_guest.lines
        for text in lines[self._act_guest_logged:]:
            self._mlog(text)
        self._act_guest_logged = len(lines)

    def _nb_actbench(self, args: list, arg, out_of_range) -> None:
        """[ff9mapkit netsync s133] `netsync actbench ...`: HarnessAgent's argument parse FIRST (`tape dump <from> <count>`
        with count 1-ActTapePageMax, every other form exactly three words), then NetSyncBattle.HarnessActBench (the
        selftest role, the op, its value) -- in the agent's order and words. [ff9mapkit netsync s134] The guest ops
        (NetSyncDiorama.IsActGuestBenchOp: `feed|feedat|replay|rework|shortcircuit|knob|clear|teardown`, `tape play`) go
        to HarnessActGuestBench FIRST, with its own arity; every other form keeps s133's parse, its usage s134's text.
        [ff9mapkit netsync s135] + the hold's `hold|lifeskip|unit`; [ff9mapkit netsync s136] + fallback A's `fallback`
        (HarnessActFallbackBench) -- each rewrote the usage line (NETSYNC_ACTBENCH_USAGE_S135 / _S136)."""
        aop = args[1].lower() if len(args) > 1 else ""
        aval = args[2].lower() if len(args) > 2 else ""
        replay = "actreplay" in self._nb_caps()
        hold = "acthold" in self._nb_caps()                 # [ff9mapkit netsync s135] + `hold|lifeskip|unit`
        fallback = "actfallback" in self._nb_caps()         # [ff9mapkit netsync s136] + `fallback`
        if replay and BW.ActGuestLane.is_bench_op(aop, aval, hold=hold, fallback=fallback):
            ok, why = self._act_guest.bench(args, booted=bool(self._dio["booted"]), role=self._nb_role(),
                                            tape=list(self._act_lane.tape),
                                            ctx=self._act_guest_ctx() if self._dio["booted"] else None)
            self._act_flush()
            if not ok:
                raise RuntimeError(why or "netsync actbench refused")
            return
        afrom = acount = -1
        if aop == "tape" and aval == "dump":
            afrom, acount = arg(3, -1), arg(4, -1)
            if len(args) != 5 or afrom < 0 or acount < 1 or acount > BW.ACT_TAPE_PAGE_MAX:
                raise out_of_range("netsync actbench tape dump", "expected `tape dump <from> <count>` (from >= 0, count 1-"
                                   + str(BW.ACT_TAPE_PAGE_MAX) + ")")
        elif len(args) != 3:
            raise out_of_range("netsync actbench", NETSYNC_ACTBENCH_USAGE_S136 if fallback else
                               NETSYNC_ACTBENCH_USAGE_S135 if hold else
                               NETSYNC_ACTBENCH_USAGE_S134 if replay else NETSYNC_ACTBENCH_USAGE_S133)
        ok, why = self._act_lane.bench(aop, aval, afrom, acount, selftest_role=self._nb_role(), now_ms=int(self.rt * 1000))
        self._act_flush()
        if not ok:
            raise RuntimeError(why or "netsync actbench refused")

    def _nb_pump_own(self, caps) -> None:
        """SelfTestPump in an own battle: TrackCommandPhase, the roster, the sample (caps + Ready bits + the end block),
        the loopback parse, the `endbench cmd` one-shot, then the parked `bcmd` frames through the real intake."""
        nb = self._nb
        gates = self._nb_gates_on()
        phase = self._battle_phase_now()
        open_ = bool(self.commands_enabled and phase == BW.PHASE_NORMAL)
        if open_ != nb.phase_open:
            nb.phase_open = open_
            if open_:
                nb.phase_open_frame = self.frame
                nb.roster_lag = -1
        handback = "handback" in caps
        if handback:
            self._nb_track_hold()                           # [ff9mapkit netsync B4] s110 TrackHostHold (beside the phase)
        if "waitparity" in caps:
            # [ff9mapkit netsync R3 s113/s114] the loopback guest's GuestControl (its depth byte, the s114 report), a lapse
            # (none, or the reserve), then the host's ParseControl of it
            view = nb.peer
            self._nb_loopback_control(caps, bool(view is not None and view["ready"] & nb.guest_slots))
        elif not (handback and self._nb_lapse_tick()):
            nb.assist_rt = nb.lane_rt = self.rt             # the loopback's own control frame stamps the lane every tick
        if handback:                                        # ...a `bench lapse` sends none: ParseControl(null), a STALL
            self._nb_hand_back()                            # G3, right after ParseControl
        if "starthold" in caps:
            self._nb_start_hold_tick()                      # [ff9mapkit netsync R3 s114] right after HandBackGuestSlot
        # the roster: gated -> only in the command phase, rebuilt at its opening; ungated -> the RosterMs cadence (a
        # second battle's intro reads the previous battle's ability keys as ready -- the stale roster leak)
        menus_ready = open_ or (not gates and nb.own_battles > 1)
        build = open_ if gates else self.rt >= nb.roster_next_rt
        if not gates and self.rt >= nb.roster_next_rt:
            nb.roster_next_rt += 1.0
        if build and menus_ready:
            slots = sorted(u["slot"] for u in self.battle_units
                           if u.get("player") and 0 <= u["slot"] < 4 and nb.guest_slots & (1 << u["slot"]))
            nb.roster_slots = slots
            if nb.roster_lag < 0 and open_ and nb.phase_open_frame >= 0:
                nb.roster_lag = self.frame - nb.phase_open_frame
        # the sample
        pending = {e[1] for e in self.battle_pending}
        ready = g6 = 0
        g6_on = handback and self._nb_handback_on()
        for u in self.battle_units:
            s = u["slot"]
            if not u.get("player") or not 0 <= s < 8:
                continue
            if s in self.battle_ready and s not in self.battle_done and s not in pending and (open_ or not gates):
                if g6_on and s == self.battle_turn:
                    g6 |= 1 << s                            # [ff9mapkit netsync B4] s110 G6: the host's own window holds it
                    continue
                ready |= 1 << s
        if handback:
            nb.g6_mask = g6
        caps_byte = BW.CAP_COMMAND_PHASE_GATED if gates else 0
        if "intro" in caps:
            # [ff9mapkit netsync R3 s111] bit 0 random, bits 2-3 the intro (clear under the `bench intro 0` lever); s114 bit
            # 4 while the start hold holds
            caps_byte = BW.own_battle_caps(gates, self.battle_random, intro_on=self._nb_intro_on(),
                                           skipped=nb.own_intro == 1,
                                           holding="starthold" in caps and nb.hold is not None and BW.hold_bit(nb.hold))
        if "actstart" in caps and self._act_lane.starts_on(self._nb_role()):
            caps_byte |= BW.CAP_ACTION_STARTS               # [ff9mapkit netsync s133] bit 5 (not under `hoststarts off`)
        nb.last_caps, nb.last_ready = caps_byte, ready
        nb.wire_seq = (nb.wire_seq + 1) & 0xFFFF
        if "actstart" in caps:
            # [ff9mapkit netsync s133] LoopActions: this tick's type-6 frames round-trip the codec into the audit and tape
            self._act_lane.loop_actions(int(self.rt * 1000))
            self._act_flush()
        end = None
        if "endblock" in caps:
            ui, state = BW.UI_OTHER, 0
            if self.ui_state == "BattleResult":
                ui, state = BW.UI_RESULT, self.result_state
            block = BW.make_block(phase, self._battle_seq_now(), self.battle_result, ui=ui, state=state)
            key = (block["phase"], block["seq"], block["result"], block["res_byte"], block["ui"])
            if key != nb.host_key:
                if nb.host_key is not None:
                    nb.host_changes += 1
                    if self._nb_host_mode() == BW.MODE_ON:
                        nb.host_edges += 1
                nb.host_key = key
            if self._nb_host_mode() != BW.MODE_OFF:
                end = block
                nb.host_end = block
                nb.host_trail_key = BW.append_trail(nb.host_trail, nb.host_trail_key, block)
            else:
                nb.host_end = None
        nb.peer = {"seq": nb.wire_seq, "nonce": nb.nonce, "caps": caps_byte, "ready": ready, "end": end}
        if "endblock" in caps:
            if nb.peer_nonce != nb.nonce:                   # NotePeer: a new battle nonce restarts the trail
                nb.peer_nonce = nb.nonce
                nb.peer_trail, nb.peer_trail_key = [], -1
            if end is not None:
                nb.peer_trail_key = BW.append_trail(nb.peer_trail, nb.peer_trail_key, end)
            if nb.cmd_armed and nb.host_end is not None and BW.is_end_kind(nb.host_end["kind"]):
                nb.cmd_armed = False                        # BenchCommandTick: drained this tick
                if len(nb.loop) < 16:
                    nb.loop.append(nb.cmd_frame)
                    nb.cmd_status = "fired " + BW.kind_name(nb.host_end["kind"])
                else:
                    nb.cmd_status = ("failed: netsync bcmd: 16 frames already wait on the loopback (no own battle is "
                                     "draining them)")
        while nb.loop:
            self._nb_handle_command(nb.loop.pop(0), open_, gates, phase)

    def _nb_drop(self, why: str) -> None:
        self._nb.cmd_dropped += 1
        self._nb.dropped_why = why

    def _nb_handle_command(self, frame: bytes, open_: bool, gates: bool, phase: int) -> None:
        """NetSyncBattle.HandleCommandPayload: the decoder's acceptance test, THE INTAKE GUARD (s100: before ownership),
        ownership, the mask, the unit, "awaiting input", then the action through SendNetCommand."""
        nb = self._nb
        c = BW.decode_command(frame)
        if c is None:
            self._nb_drop("malformed command frame: " + f"len {len(frame)}" + (f", ver {frame[0]}" if frame else "")
                          + " (want 9 bytes, ver 1)")
            return
        slot, action, mask = c["slot"], c["action"], c["mask"]
        if gates and not open_:
            nb.cmd_refused += 1
            nb.refused_why = BW.phase_why(phase) if phase != BW.PHASE_NORMAL else BW.MENU_DISABLED_WHY
            return
        if not self._nb_guest_owned(slot):
            self._nb_drop(f"slot {slot} is not a guest slot")
            return
        if mask == 0:
            self._nb_drop(f"slot {slot} {BW.action_name(action)}: empty target mask")
            return
        unit = next((u for u in self.battle_units if u.get("player") and u["slot"] == slot), None)
        if unit is None or unit["hp"] == 0:
            self._nb_drop(f"slot {slot} absent or KO")
            return
        if slot not in self.battle_ready or slot in self.battle_done or slot in {e[1] for e in self.battle_pending}:
            self._nb_drop(f"slot {slot} not awaiting input")
            return
        if action in (BW.ACT_ATTACK, BW.ACT_INSTANT):
            living = any(mask & u["id"] and (u["hp"] > 0 or u.get("player")) for u in self.battle_units)
            if action == BW.ACT_ATTACK and not living:
                foe = next((u for u in self.battle_units if not u.get("player") and u["hp"] > 0), None)
                mask = foe["id"] if foe else 0
            if mask == 0:
                self._nb_drop(f"slot {slot} Attack: no living target left to retarget to")
                return
            cmd, sub, what = (1, 176, "Attack") if action == BW.ACT_ATTACK else (3, 0, "Instant")
        elif action == BW.ACT_DEFEND:
            cmd, sub, mask, what = 2, 177, 1 << slot, "Defend"
        elif action == BW.ACT_ABILITY:
            ab = next((a for a in self.MENU_ABILITIES if a["sub"] == c["id"] and a["enabled"]), None)
            if ab is None:
                self._nb_drop(f"slot {slot} ability {c['id']} not usable")
                return
            cmd, sub, what = 4, c["id"], f"ability {c['id']}"
        elif action == BW.ACT_ITEM:
            it = next((i for i in self.MENU_ITEMS if i["sub"] == c["id"] and i["count"] > 0), None)
            if it is None:
                self._nb_drop(f"item {c['id']}: none left")
                return
            cmd, sub, what = 8, c["id"], f"Item {c['id']}"
        else:
            self._nb_drop(f"slot {slot}: unknown action {action} (v1 knows 0-4)")
            return
        try:
            self._battle_command(slot, cmd, sub, mask, c["cursor"])
        except RuntimeError:
            self._nb_drop(f"slot {slot} {what}: the HUD refused -- a command is already in flight for it (or the unit "
                          f"has no command slot)")
            return
        nb.cmd_queued += 1

    def _nb_boot(self) -> None:
        """Every diorama Boot: R9's per-boot ledger, the stock menu's per-boot state, the presentation and the exit.
        [ff9mapkit netsync s134] ...and the action replay's (ActResetForBoot(true), next to ResetIntro)."""
        nb = self._nb
        if "actreplay" in self._nb_caps():
            self._act_guest.reset_for_boot(True)
        nb.r9_refused, nb.r9_cmd, nb.r9_site = 0, -1, None
        nb.outbox.clear()
        nb.touched = False
        nb.bench_open = 0
        nb.captured = None
        nb.reset_presentation()
        nb.reset_exit()
        nb.btl_flag = 0
        # [ff9mapkit netsync B4] s106-s107: the repaint's mute, the drawn panel, a running feed (a new boot stops it) and
        # the mirror's per-boot state; [ff9mapkit netsync B5] s109: the replay and its receipts
        nb.mute_until = -1
        nb.hud_snap = None
        nb.double_cast, nb.cast_first = 0, None
        self._nb_stop_feed("a new boot")
        nb.mirror_mask, nb.stranded_mask, nb.mirror_serving, nb.assist_slot = 0, 0, False, -1
        nb.stranded_turn, nb.no_roster_mask, nb.mirror_nonce = 0, 0, -1
        nb.pend.clear()
        nb.no_roster_since.clear()
        nb.mirror_faulted, nb.mirror_fault_why = False, None
        nb.reset_replay()
        # [ff9mapkit netsync R3] s111/s114: the intro's and the LIVE latch's per-boot record (the boot's wire intro is
        # stamped by the caller after this); s115-s117: the flee / defeat presentation's
        nb.d_applied = nb.d_own = -1
        nb.d_calls, nb.d_normal_ms, nb.d_boot_rt = 0, -1, self.rt
        nb.live_latched, nb.live_ms, nb.live_nonce = False, -1, -1
        nb.reset_r3_end()
        nb.unit_r3.clear()

    def _nb_teardown(self) -> None:
        """NetSyncDiorama.ForceDisarm at the teardown: StockMenuCloseAll("the diorama tore down"), then (s105) the
        return settle -- the btl_result stamp re-decided from the host's latest terminal block, the injected end fade
        lifted. The presentation's phase override goes with the battle. [ff9mapkit netsync B4/B5] s107: the bench feed
        stops with its diorama; s109: a replay still up aborts, and one that closed through its own hide tail already
        lifted the fade (the teardown does not again)."""
        nb = self._nb
        caps = self._nb_caps()
        if "replay" in caps:
            self._nb_replay_abort("the diorama tore down")
        if "actreplay" in caps:
            # [ff9mapkit netsync s134] ActDiscardAll("teardown"), between AbortReplay and Disarm: dropped, never applied
            # [ff9mapkit netsync s135] ...after ForceDisarm's ActHoldClearSeq (the life mask, the applied seqs)
            self._act_guest.hold.clear_seq()
            self._act_guest.discard_all("teardown")
            self._act_flush()
        if "stockmenu" in caps:
            self._nb_close_all("the diorama tore down")
        self._nb_stop_feed("its diorama ended")
        nb.hud_snap = None
        if "exit" in caps:
            if (nb.settled and nb.stamped < 0 and nb.exit_seen and nb.exit_last is not None
                    and BW.is_terminal(nb.exit_last["kind"], nb.exit_last["ui"])):
                nb.stamp_host = nb.exit_last["result"]
                nb.stamp_pending = BW.stamp_for(nb.exit_last["result"], nb.settle_no_gameover)
            if nb.stamp_pending >= 0:
                nb.stamped_was = self.battle_result
                self.battle_result = nb.stamp_pending
                nb.stamped, nb.stamp_pending = nb.stamp_pending, -1
            elif "flee" in caps and nb.settled and nb.stamped < 0:
                # [ff9mapkit netsync R3 s115] THE NO-LEAK RULE, scoped (ApplyReturnSettle): nothing stamped -- a local
                # DEFEAT / GAMEOVER, or any local value once the host's final kind is Defeat, reverts to the pre-injection
                # result
                kind = nb.exit_last["kind"] if nb.exit_seen and nb.exit_last is not None else nb.kind
                back = BW.no_leak_result(-1, nb.injected, self.battle_result, nb.pre_inject, kind)
                if back >= 0:
                    nb.reverted, self.battle_result = self.battle_result, back
            if nb.injected and not nb.wipe_lifted and not nb.r_hide_tail and self._nb_exit_mode() == BW.EXIT_MODE_ON:
                nb.wipe_lifted = True
        if nb.gil_taken:                                    # [ff9mapkit netsync R3 s115] Disarm's Restore: party.gil back
            self.save_gil += nb.gil_taken
            nb.gil_taken = 0
        nb.phase = nb.seq = None

    def _nb_end_tick(self, caps) -> None:
        """NetSyncDiorama.EndTick (s104; s105's ExitTick first): this boot's end block (the bench seam -- a dioboot has
        no wire nonce), the exit with the host, then -- once per boot -- the injection the host's kind names."""
        nb = self._nb
        if nb.faulted:
            return
        e = nb.bench_block if nb.bench_armed else None
        ours = e is not None
        if ours:
            nb.exit_seen = True
            nb.exit_last = e
            if e["kind"] == BW.K_EVENT:                     # [ff9mapkit netsync R3 s117] the host's latest pre-end state
                nb.host_event = True
            elif e["kind"] == BW.K_FIGHTING:
                nb.host_event = False
        leaving = self._nb_exit_tick(ours, e) if "exit" in caps else False
        if self._nb_hud_off() and self.commands_enabled:
            self.commands_enabled = False                   # KeepHudOff
        if nb.injected:
            if not nb.w1_armed and ours and e["ui"] >= BW.UI_RESULT:
                nb.w1_armed, nb.w1_since = True, self.rt
            self._nb_watchdogs()
            if "fleegil" in caps:
                self._nb_flee_gil_tick(ours, e)             # [ff9mapkit netsync R3 s116] a record that came after R9b
            if "replay" in caps:
                self._nb_replay_arm_tick(ours, e)           # [ff9mapkit netsync B5] s109 ReplayArmTick
            return
        if leaving:
            nb.why = (f"the host already left its battle ({BW.trigger_name(nb.trigger)}) -- the guest follows it out "
                      f"without presenting")
            return
        if e is None:
            nb.why = "no peer end block (no live lane, or a host that predates the end block)"
            return
        if "acthold" in caps and BW.act_end_inject_flushes(ours, e["kind"]):
            # [ff9mapkit netsync s135] THE END-INJECT RELEASE (amendment 2, D02): every held impact and queued frame NOW,
            # through the legacy path, BEFORE AllPlayersDown reads the party (a held kill would read a dying player as up)
            self._act_guest.hold.flush("end-inject", self._act_guest_ctx())
            self._act_flush()
        action = BW.present_action(e["kind"])
        # EndTick reads AllPlayersDown ONCE, here (after the s135 flush), and InjectEnd's settle-or-tail choice takes THAT
        # value -- the engine's `allDown` parameter -- never a re-read after InjectEnd's own flush ([ff9mapkit netsync s135]
        # fix pass rharness-1: a re-read hid a flush moved below this line)
        all_down = e["kind"] == BW.K_DEFEAT and self._nb_all_down()
        if "flee" in caps:
            # [ff9mapkit netsync R3 s115] the phase-aware table; s117 + the defeat rows (an s115/s116 guest still holds a
            # defeat: PresentFor's last line)
            action = BW.present_for(e["kind"], e["phase"], self._nb_guest_mode(), all_down, nb.host_event)
            if "defeat" not in caps and e["kind"] == BW.K_DEFEAT and self._nb_guest_mode() != BW.GUEST_HOLD:
                action = BW.PRESENT_HOLD
        if action == BW.PRESENT_NONE or (action == BW.PRESENT_HOLD and nb.held):
            nb.why = None
            return
        verdict = BW.inject_verdict(self._nb_guest_mode(), True, self._battle_phase_now(), self.ui_state == "BattleHUD")
        if verdict is not None:
            nb.why = f"the host's {BW.kind_name(e['kind'])} waits: {verdict}"
            return
        self._nb_inject(e, action, all_down)

    def _nb_inject(self, e: dict, action: int, all_down: bool) -> None:
        """NetSyncDiorama.InjectEnd: the stock menu closed, the HUD hidden, then the stock end the kind names.
        [ff9mapkit netsync R3] s115 the run-away (the SysEscape executor's VISUAL half), s117 the annihilation ("Annihilated"
        BEFORE the hide; the stock settle, or the defeat tail's writes at once for a standing party) and var 34's defeat.
        ``all_down`` is EndTick's AllPlayersDown (the engine's parameter), never re-read here."""
        nb = self._nb
        if "acthold" in self._nb_caps():                    # [ff9mapkit netsync s135] every inject path: nothing held
            self._act_guest.hold.flush("end-inject", self._act_guest_ctx())   # survives it (a no-op after EndTick's)
            self._act_flush()
        nb.pre_inject = self.battle_result                  # [ff9mapkit netsync R3 s115] the no-leak rule's baseline
        if action == BW.PRESENT_ANNIHILATE:
            nb.follow_msg = BW.FOLLOW_MSG_ANNIHILATED       # [ff9mapkit netsync R3 s117] CheckBattlePhase's order
        if "stockmenu" in self._nb_caps():
            self._nb_close_all("end injected")
        self.commands_enabled = False                       # FF9BMenu_EnableMenu(false)
        if self.battle_turn >= 0:
            self.battle_turn = -1
            self._close_battle_cursor()
        nb.kind, nb.action, nb.why = e["kind"], action, None
        if action == BW.PRESENT_HOLD:
            nb.held = True
            return
        if action == BW.PRESENT_VICTORY:
            nb.phase, nb.seq = BW.PHASE_MENU_OFF, BW.victory_seq(self._nb_guest_mode())
            nb.stage_until = self.frame + self.dio_tail_frames
        elif action == BW.PRESENT_FLEE:
            # [ff9mapkit netsync R3 s115] every living player turns and runs (MP_ESCAPE, z falling), then the escape fade
            if self._nb_guest_mode() == BW.GUEST_NOR9B:
                nb.flee_ability_flag = True                 # CALIBRATION ONLY: the stock penalty's flag
            for u in self._nb_players():
                if u.get("alive", True) and u["hp"] > 0:
                    nb.unit_r3[u["slot"]] = {"mot": BW.MP_ESCAPE, "disappear": 0, "z": -600.0}
            nb.phase, nb.seq = BW.PHASE_MENU_OFF, BW.SEQ_MENU_OFF_ESCAPE
            nb.run_until = self.frame + self.dio_run_frames
            nb.stage_until = nb.run_until
        elif action == BW.PRESENT_ANNIHILATE:
            if BW.annihilate_settles(all_down, self._nb_guest_mode()):
                nb.phase, nb.seq = BW.PHASE_MENU_OFF, BW.SEQ_MENU_OFF_DEFEAT
                nb.stage_until = self.frame + self.dio_tail_frames
            else:                                           # a standing party: the tail's writes, its settle skipped
                self.battle_result = BW.BTL_RESULT_DEFEAT
                nb.phase, nb.seq = BW.PHASE_DEFEAT, BW.SEQ_DEFEATCLOSE_FADEOUT
                self._nb_defeat_song()
                nb.stage_until = self.frame + 32
        elif action == BW.PRESENT_DEFEAT:                   # [ff9mapkit netsync R3 s117] var 34's writes, no message
            self.battle_result = BW.BTL_RESULT_DEFEAT
            nb.phase, nb.seq = BW.PHASE_DEFEAT, BW.SEQ_DEFEATCLOSE_FADEOUT
            self._nb_defeat_song()
            nb.stage_until = self.frame + 32
        else:
            self.battle_result = BW.close_result(e["result"])
            nb.phase, nb.seq = BW.PHASE_CLOSE, BW.SEQ_DEFEATCLOSE_FADEOUT
            nb.stage_until = self.frame + 32
        nb.injected, nb.inject_rt = True, self.rt
        nb.inject_phase, nb.inject_seq = nb.phase, nb.seq

    def _nb_watchdogs(self) -> None:
        """W1 (the victory camera stuck > 4 s after the host's ui >= 1) and W2 (still MENU_OFF > 8 s after the injection)."""
        nb = self._nb
        if not nb.w1_fired and BW.w1_due(nb.phase, nb.seq, nb.w1_armed, int((self.rt - nb.w1_since) * 1000)):
            nb.w1_fired = True
            nb.watchdog = "W1" if nb.watchdog is None else nb.watchdog + "+W1"
            nb.seq, nb.stage_until = BW.SEQ_VICTORY_FADEOUT, self.frame + 32
        if not nb.w2_fired and BW.w2_due(nb.phase, int((self.rt - nb.inject_rt) * 1000)):
            nb.w2_fired = True
            nb.watchdog = "W2" if nb.watchdog is None else nb.watchdog + "+W2"
            blockers = []
            if nb.seq == BW.SEQ_MENU_OFF_VICTORY:
                n = sum(1 for u in self.battle_units if not u.get("player") and u.get("alive"))
                if n:
                    blockers.append(f"{n} unsettled unit(s) (SEQ_MENU_OFF_VICTORY's per-unit settle: an enemy without "
                                    f"BattleEnd, or a dead player not yet down)")
            if nb.seq == BW.SEQ_MENU_OFF_DEFEAT and "defeat" in self._nb_caps():
                n = self._nb_standing()                     # [ff9mapkit netsync R3 s117] the defeat tail's own blocker
                if n:
                    blockers.append(f"{n} player(s) not down (the defeat tail waits for every player's MP_DISABLE or a "
                                    f"BattleEnd status)")
            nb.blocker = "; ".join(blockers) or "no blocker visible"
            nb.btl_flag |= BW.BTL_END_LOAD
            # [ff9mapkit netsync R3 s115/s117] KIND-AWARE: the tail of the kind actually injected (W2Force)
            if "flee" in self._nb_caps():
                phase, seq, result = BW.w2_force(nb.action)
            else:
                phase, seq, result = BW.PHASE_VICTORY, BW.SEQ_VICTORY_FADEOUT, BW.BTL_RESULT_VICTORY
            self.battle_result = result
            nb.phase, nb.seq, nb.stage_until = phase, seq, self.frame + 32

    def _nb_present_step(self) -> None:
        """The stock tail the injection set running, one frame: MENU_OFF's trailing loop (the _WITH_ENEMY seq has no
        per-unit settle; the settle seq stalls while an enemy stands), PHASE_VICTORY's camera / fade / WAIT, the CLOSE
        fade -- and R8 at the WAIT seq, where ManageBattleEnd is reached only when the Byte btl_fade_time++ > 32."""
        nb = self._nb
        if nb.phase == BW.PHASE_MENU_OFF and nb.seq == BW.SEQ_MENU_OFF_ESCAPE:
            self._nb_run_step()                             # [ff9mapkit netsync R3 s115] the runners, every frame
        if self.frame < nb.stage_until:
            return
        if nb.phase == BW.PHASE_MENU_OFF and nb.seq == BW.SEQ_MENU_OFF_ESCAPE:
            # [ff9mapkit netsync R3 s115] battle.cs's escape tail: ESCAPE, PHASE_CLOSE -- then R9b (the STATE half skipped:
            # counted; the `guest nor9b` lever lets the stock penalty run instead), BTL_END_LOAD, the CLOSE fade
            self.battle_result = BW.BTL_RESULT_ESCAPE
            nb.btl_flag |= BW.BTL_END_LOAD
            nb.phase, nb.seq = BW.PHASE_CLOSE, BW.SEQ_DEFEATCLOSE_FADEOUT
            nb.flee_penalty = self._nb_flee_penalty()
            if self._nb_guest_mode() == BW.GUEST_NOR9B:
                nb.flee_bypassed += 1
                self.save_gil -= nb.flee_penalty            # the stock penalty, in the diorama (the teardown puts it back)
                nb.gil_taken = nb.flee_penalty
            else:
                nb.flee_r9b += 1
                if "fleegil" in self._nb_caps():
                    self._nb_flee_gil_tick(nb.bench_armed, nb.bench_block)
            nb.stage_until = self.frame + 32
            return
        if nb.phase == BW.PHASE_MENU_OFF and nb.seq == BW.SEQ_MENU_OFF_DEFEAT:
            # [ff9mapkit netsync R3 s117] the defeat tail's per-unit settle: every visible player down, then DEFEAT,
            # PHASE_DEFEAT -- song 6 in a Game-Over scene only -- and the fade
            if self._nb_standing():
                return
            self.battle_result = BW.BTL_RESULT_DEFEAT
            nb.btl_flag |= BW.BTL_END_LOAD
            nb.phase, nb.seq = BW.PHASE_DEFEAT, BW.SEQ_DEFEATCLOSE_FADEOUT
            self._nb_defeat_song()
            nb.stage_until = self.frame + 32
            return
        if nb.phase == BW.PHASE_MENU_OFF:
            if nb.seq == BW.SEQ_MENU_OFF_VICTORY and any(not u.get("player") and u.get("alive")
                                                         for u in self.battle_units):
                return                                      # the per-unit settle: no host ever kills a bench enemy
            self.battle_result = BW.BTL_RESULT_VICTORY      # the victory tail: VICTORY, song 5, poses, camera 2
            nb.btl_flag |= BW.BTL_PLAY_END_SONG | BW.BTL_END_LOAD
            nb.music = 5
            nb.phase, nb.seq = BW.PHASE_VICTORY, BW.SEQ_VICTORY_CAMERA_MOVE
            nb.stage_until = self.frame + self.dio_camera_frames
        elif nb.phase == BW.PHASE_VICTORY and nb.seq == BW.SEQ_VICTORY_CAMERA_MOVE:
            if not self.dio_camera_stuck:
                nb.seq, nb.stage_until = BW.SEQ_VICTORY_FADEOUT, self.frame + 32
        elif (nb.phase, nb.seq) in ((BW.PHASE_VICTORY, BW.SEQ_VICTORY_FADEOUT),
                                    (BW.PHASE_CLOSE, BW.SEQ_DEFEATCLOSE_FADEOUT),
                                    (BW.PHASE_DEFEAT, BW.SEQ_DEFEATCLOSE_FADEOUT)):
            nb.seq = BW.SEQ_VICTORY_WAIT if nb.phase == BW.PHASE_VICTORY else BW.SEQ_DEFEATCLOSE_WAIT
            nb.fade = 0
        else:                                               # a WAIT seq: R8 at the head of ManageBattleEnd
            old, nb.fade = nb.fade, (nb.fade + 1) & 0xFF
            if old > 32:
                nb.r8_hits += 1
                if nb.r8_hits == 1 and nb.injected:
                    nb.r8_first_ms = int((self.rt - nb.inject_rt) * 1000)

    def _nb_exit_tick(self, ours: bool, e: dict | None) -> bool:
        """NetSyncDiorama.ExitTick (s105): latch the host's exit once per boot, then the end-leave at 1 Hz -- never into
        the boot's swirl (a fade), never while a leave is in flight. True = the guest is following the host out."""
        nb = self._nb
        mode = self._nb_exit_mode()
        if nb.trigger == BW.TRIGGER_NONE:
            t = BW.host_exit_trigger(e["ui"], e["res_byte"]) if ours else BW.TRIGGER_NONE
            if t == BW.TRIGGER_NONE:
                nb.exit_why = BW.exit_why(BW.EXIT_NOT_LATCHED if mode == BW.EXIT_MODE_ON else BW.EXIT_HELD_BY_LEVER)
                return False
            nb.trigger, nb.latched_rt = t, self.rt
            if mode == BW.EXIT_MODE_ON and "stockmenu" in self._nb_caps():
                self._nb_close_all("the host left its battle")
        if mode == BW.EXIT_MODE_ON and not self._dio_leave_recently() and "replay" in self._nb_caps():
            # [ff9mapkit netsync B5] s109 (design 5.4 steps 1-2): a replay armed or on screen gets up to ReplayExitWaitMs
            # to chase the host's Hide and run its OWN hide tail; past the window the Leave aborts it
            since = int((self.rt - nb.latched_rt) * 1000)
            if BW.exit_waits_for_replay(nb.trigger, self._nb_replay_live(), since):
                nb.r_exit_waiting = True
                nb.exit_why = "waiting for the result-screen replay to reach Hide (its own hide tail; up to 5 s)"
                return True
            if nb.r_exit_waiting and nb.r_exit_wait_ms < 0:
                nb.r_exit_wait_ms = since
        fading = self.frame - self._dio_boot_frame < self.dio_swirl_frames
        v = BW.exit_verdict(mode, True, self._dio_leave_recently(), fading, int((self.rt - nb.try_rt) * 1000))
        if v == BW.EXIT_RATE_LIMITED:
            return True
        if v == BW.EXIT_FADE_DEFER:
            nb.try_rt = self.rt
            nb.deferred += 1
            nb.exit_why = BW.exit_why(v)
            return True
        if v == BW.EXIT_IN_FLIGHT:
            nb.exit_why = None if nb.requested else BW.exit_why(v)
            return True
        if v != BW.EXIT_GO:
            nb.exit_why = BW.exit_why(v)
            return False
        nb.try_rt = self.rt
        nb.tries += 1
        self._dio_leave(via="end-leave")
        if self._dio_leave_recently():
            nb.requested = True
            nb.request_ms = int((self.rt - nb.latched_rt) * 1000)
            nb.exit_why = None
        else:
            nb.exit_why = "Leave() did not issue its Replace (Memoria.log names why) -- retrying at 1 Hz"
        return True

    def _nb_settle(self, via: str | None) -> None:
        """NetSyncDiorama.SettleForReturn (s105): once per boot, a Leave of a FINISHED fight shuts the battle song down
        and provisionally decides the btl_result the teardown stamps."""
        nb = self._nb
        if "exit" not in self._nb_caps() or nb.settled or not nb.exit_seen or nb.exit_last is None:
            return
        e = nb.exit_last
        if not BW.is_terminal(e["kind"], e["ui"]):
            return
        if self._nb_exit_mode() != BW.EXIT_MODE_ON:
            nb.music_why = "the calibration lever `endbench exit off` (no settle)"
            return
        nb.settled, nb.via = True, via or "leave"
        nb.settle_no_gameover = self.scene_no_gameover
        nb.stamp_host = e["result"]
        nb.stamp_pending = BW.stamp_for(e["result"], nb.settle_no_gameover)
        if nb.r_hide_tail:
            # [ff9mapkit netsync B5] s109: the replay's own hide tail already ran the song half -- nothing shut down twice
            nb.music_why = nb.r_music_why or ("the replay's own hide tail already shut the songs (stage 10): nothing shut "
                                              "down twice")
        elif BW.song_verdict(e["flags"], False) != BW.SONG_SHUT:
            nb.music_why = BW.song_why(BW.song_verdict(e["flags"], False))
        else:
            nb.music_shut = True
            nb.music = -1

    def _battle_hud_doc(self) -> dict:
        """BattleHUD.NetDescribeHud (s102) as the stand-in draws its battle cursor: `commands`/`rows` only while a menu
        is up (their labels would be the LAST menu's)."""
        group = self.menu.get("group")
        panel = {"Battle.Command": "command", "Battle.Ability": "ability", "Battle.Item": "item",
                 "Battle.Target": "target"}.get(group, "none")
        up = panel != "none" and self.battle_turn >= 0
        commands, rows = [], []
        # [ff9mapkit netsync B4] s106: a MIRRORED slot's panels are the ones drawn from the menu roster (as drawn: a
        # repaint or the next display redraws them)
        snap = self._nb_snap_for(group) if up and "content" in self._nb_caps() else None
        if up:
            if snap is not None:
                commands = [dict(c) for c in snap["commands"]]
            else:
                i = 0
                for r in self.BATTLE_GRID:
                    for label in r:
                        cmd_id = self.STOCK_COMMANDS.get(label, (0, None, 0))[0]
                        commands.append({"menu": i, "id": cmd_id, "label": label, "state": 2, "raw": 2})
                        i += 1
            if panel in ("ability", "item") and snap is not None:
                rows = [dict(r) for r in snap["rows"]]
            elif panel in ("ability", "item"):
                for i, label in enumerate(self.BATTLE_SUBMENU_ROWS[group]):
                    # the ability row's MP cell: Flee costs 0, and the stock list draws a 0-MP cell BLANK
                    # (BattleHUD.cs:845 `mp == 0 ? String.Empty : mp.ToString()`), never "0"
                    rows.append({"i": i, "id": self.STOCK_ROW_IDS.get(label, 0), "label": label,
                                 "number": "9" if panel == "item" else "", "state": 2, "raw": 2})
            elif panel == "target":
                for i, u in enumerate(u for u in self.battle_units if not u.get("player")):
                    rows.append({"i": i, "id": u["slot"], "label": u["name"], "number": "",
                                 "state": 2 if u.get("targetable") else 1, "raw": 1 if u.get("targetable") else 0})
        doc = {"group": group, "panel": panel, "shown": bool(self.commands_enabled and not self._nb_hud_off())}
        if "content" in self._nb_caps():
            doc["mirrored"] = bool(up and self._nb_mirrored_cmds(self.battle_turn) is not None)
        doc.update({"slot": self.battle_turn if up else -1, "menu": 0, "cmd": 0, "sub": 0,
                    "double_cast": self._nb.double_cast if up else 0, "cursor_type": 0, "target_cursor": 0,
                    "trance_menu": False, "manual_trance": False, "auto": False, "hiding": False, "main_menu": False,
                    "can_force_next": not self._nb_active(), "force_next": False, "caption": "", "commands": commands,
                    "rows": rows})
        return doc

    # -- s96: the F3.2 guest's dialogue lock, on the stand-in's one window ---------------------------------------
    def _dialog_open(self) -> bool:
        return bool(self.texts) or self.choice is not None

    def _dialog_more_pages(self) -> bool:
        """[ff9mapkit netsync F3.3] `d.SubPage.Count > d.CurrentPage` -- the open window has a page after this one, so a
        confirm now turns a page rather than closing it (Hide()'s own test). A scene beat and a choice are one page."""
        return self.choice is None and len(self.texts) > 1

    def _dialog_ready(self) -> bool:
        """The window takes a confirm that answers it: complete, and a scene choice READY and done typing
        (IsChoiceReady). A plain window is complete the frame it opens -- the stand-in has no typewriter."""
        if self._beats and self.choice is not None:
            return self._beat_phase == "ready" and self.frame >= self._typing_until
        return True

    def _guest_now(self) -> int:
        """The guest's clock, ms on the VIRTUAL clock (the engine reads Environment.TickCount deltas)."""
        return int(self.rt * 1000)

    def _guest_on_field(self) -> bool:
        return self.field_id > 0 and not self.battle_active and self.ui_state not in (
            "Title", "WorldHUD", "BattleHUD", "BattleResult")

    def _guest_suppress(self) -> bool:
        """SuppressLocalDialogInput: the lock is engaged and a lockable, non-``inh`` line is open that is not Local --
        an UNTRACKED line counts as locked, so one opened this frame is covered before the next tick sees it.
        [ff9mapkit netsync F3.3] C3KEYS-2 (s99): ...or a polled ``inh`` CHOICE while the script-key lock holds -- its
        branch is the host's relayed press + cursor (NetSyncDialog.AnyLockedLine)."""
        g = self._guest
        if self.netsync_dialogue != "authority" or not g.engaged or not self._dialog_open():
            return False
        w = g.win
        if w is not None and w["gen"] == self._dialog_gen and w["cls"] == "local":
            return False
        if not self.dialog_inh:
            return True
        return self._cap("keys") and self.choice is not None and g.key_hold(self.field_id)

    def _guest_windows(self) -> list[dict]:
        w = self._guest.win
        if w is None:
            return []
        field, win, text = w["key"]
        return [{"win": win, "text": text, "field": field, "cls": w["cls"],
                 "state": "CompleteAnimation" if self._dialog_ready() else "TextAnimation",
                 "page": w["page"], "inh": self.dialog_inh}]

    def _guest_track(self, now: int) -> None:
        """Track: the open window joins LOCKED (lock from open) unless it is the one already tracked; a page turn
        re-arms its read clock; a closed window is forgotten (its KEY cursor pins with it -- C3KEYS-1).
        [ff9mapkit netsync F3.3] C3KEYS-4: a host-driven line opening on the field whose Local lines owned their polls
        hands those polls back to the host."""
        g = self._guest
        if not self._dialog_open():
            if g.win is not None:
                g.unbind_key_cursors(g.win["gen"])
            g.win = None
        elif g.win is None or g.win["gen"] != self._dialog_gen:
            if g.win is not None:
                g.unbind_key_cursors(g.win["gen"])
            g.win = {"gen": self._dialog_gen, "key": (self.field_id, self.dialog_id, self.dialog_text_id),
                     "cls": "locked", "page": self._dialog_page, "complete_ms": now, "orphan_ms": now}
            if g.own_polls_field == self.field_id:
                g.own_polls_field = -1
        elif g.win["page"] != self._dialog_page:
            g.win.update(page=self._dialog_page, complete_ms=now)

    def _host_confirm(self, index: int | None = None) -> bool:
        """A HOST-driven confirm (NetSyncDialog.HostConfirm): what the window's own OnKeyConfirm does, past the
        guest's suppression. ``index`` is set on a choice first -- out of range, the window's default (never the
        guest's cursor). True when the window ADVANCED (a page turned, the window closed, a choice answered)."""
        if self._beats:
            beat = self._beats[0]
            if isinstance(beat, str):
                self._beats.pop(0)
                self._next_beat()
                return True
            if self.choice is None or not self._dialog_ready():
                return False
            if index is not None:
                active = self.choice.get("active") or list(range(int(self.choice.get("count", 0))))
                self._choice_cursor(index if index in active else int(beat.get("default", 0)))
            answered = len(self.answered)
            self._scene_press("confirm")
            return len(self.answered) > answered
        if self.choice is not None:
            self.choice = None
            self.menu_entries = []
            return True
        if self.texts:
            self.texts = self.texts[1:]
            self.raw_texts = self.raw_texts[1:] if self.raw_texts else []
            self._dialog_page += 1
            return True
        return False

    def _set_choice(self, index: int) -> bool:
        """[ff9mapkit netsync F3.3] Dialog.TrySetCurrentChoice under HostApplying: the open choice's cursor onto `index` --
        false (nothing moves) when it is not one of the window's ACTIVE rows."""
        if self.choice is None:
            return False
        active = self.choice.get("active") or list(range(int(self.choice.get("count", 0))))
        if index not in active:
            return False
        if self._beats:
            self._choice_cursor(index)
        else:
            self.choice["selected"] = index
            if 0 <= index < len(self.menu_entries):
                self.menu_index = index
                self.menu["label"] = self.menu_entries[index]
                self.menu["selected"] = f"Button{index}"
        return True

    def _step_netsync(self) -> None:
        """The guest's dialogue tick (ServiceDialogAuthority + NetSyncDialog.GuestTick) on the selftest BENCH: the
        session is the bench lock (`lock 1`, with `bench 1`), and `stale 1` reads the link dead -- the lock holds
        LinkGraceMs, then lets go. THE LOCK = session && on a field && this field not panic-unlocked; the window open
        when the session rises stays Local; every later one opens locked. Host events (the injections) apply per
        window key after MinShowMs; nothing local pages a locked line; only host state releases it -- an event, the
        orphan rule (`hostscene 0`: the host settled OrphanGraceMs, then one page per AutoReadMs), the link dead,
        the session ending, or `unlock`. F3 engines (`netsync_dialogue` None) have no tick here.

        [ff9mapkit netsync F3.3] With the "ring" capability (s98) the injections reach the guest only through the bench
        HOST's section 7: the bench builds it every tick while the lock is on (a frozen host re-sends its last one), the
        guest OBSERVES it (an epoch change clears the inbox and re-baselines; a heartbeat frozen HostStallMs is a hung
        host and drops the session) and MERGES the ring after its baseline (a session's first merge only baselines; a
        gap counts once). The host's flags, open set and cursor refine the settle clock, the orphan claim, the cursor
        MIRROR and the chip; an ADV's closes bit pages on to the close (or is a no-op on the last page). With "keys"
        (s99) a KEY joins the key list behind the ordering guard and the script-key lock's host half is kept here."""
        if self.netsync_dialogue != "authority":
            return
        ns, g = self.netsync, self._guest
        now = self._guest_now()
        ring, keys = self._cap("ring"), self._cap("keys")
        if self.field_id != g.field_seen:                 # RearmDialogLockAtFieldLoad (a same-field warp: the verb)
            g.field_seen = self.field_id
            g.unlock_field = -1
        bench = ns["selftest"] and ns["bench"]
        if bench and ring:
            self._bench_host_tick()                       # the bench HOST: section 7 every bench tick
            g.observe(None if ns["stale"] else self._bench.state, now)   # a dead link = no lane (the ring keeps filling)
        base = bench and ns["lock"] and not (ring and g.stalled)
        live = not ns["stale"]
        if base and live:
            g.live_ms, g.live_armed = now, True
        elif g.live_armed and (not base or now - g.live_ms >= g.LINK_GRACE_MS):
            g.live_armed = False                          # spent: the grace runs once
        if not (base and (live or g.live_armed)):
            g.session_prev = False
            g.forget()                                    # drain-and-discard: every line is local
            return
        on_field = self._guest_on_field()
        unlocked_here = on_field and g.unlock_field == self.field_id
        engaged = on_field and not unlocked_here
        if not g.session_prev and engaged and self._dialog_open():
            self._guest_track(now)                        # the session rose: what is already open predates it
            g.win["cls"] = "local"
            if keys:
                g.own_polls_field = self.field_id         # C3KEYS-4: ...and so do its script polls
        g.engaged, g.session_prev, g.live = engaged, True, live
        if ring:
            g.merge(now, unlocked_here, keys)             # skipped, not merged, on a panic-unlocked field
            if unlocked_here:
                g.clear_inbox()
        elif unlocked_here:
            g.inbox.clear()                               # lock off on this field: the host's taps are discarded
        # the host as section 7 reads it (none on the lane: the C2 reading -- the bench's simulated scene, co-located)
        hv = g.view if ring and g.view_valid else None
        hf = hv["flags"] if hv else 0
        scene_up = bool(hf & HF_SCENE) if hv else bool(ns["l1"])
        on_field_bit = hv is None or bool(hf & HF_ON_FIELD)
        battle_bit = hv is not None and bool(hf & HF_BATTLE)
        host_here = on_field and on_field_bit
        co_located = host_here and (hv is None or not hf & HF_LINE)
        host_menu = hv is not None and on_field_bit and not battle_bit and bool(hf & HF_MENU)
        holds_input = host_here and hv is not None and not hf & HF_CONTROL
        g.purge(self.field_id, now, self.dialog_inh)
        if keys:
            self._purge_keys(now, engaged, scene_up, holds_input)
        if not engaged:
            if g.win is not None:
                g.unbind_key_cursors(g.win["gen"])
            g.win, g.settled_since, g.settled_ms = None, None, -1
            g.own_polls_field = -1
            g.mirror_cursor = -1
            g.key_hold_base = False
            g.chip = g.CHIP_HOST_SCENE if scene_up and host_here else None
            return
        self._guest_track(now)
        if g.own_polls_field >= 0 and g.own_polls_field != self.field_id:
            g.own_polls_field = -1                        # C3KEYS-4: the latch is per field
        w = g.win
        if w is not None and w["cls"] != "local":         # apply: the earliest event for this window's key
            e = g.earliest(w["key"])
            if e is not None:
                if w["cls"] == "orphaned":
                    w["cls"] = "locked"                   # a late host event: back under the host
                # held, not tried, until it can apply: never onto an inh line (it ages out), never before MinShowMs,
                # never onto a choice that is not READY (DLG-7)
                if not self.dialog_inh and self._dialog_ready() and now - w["complete_ms"] >= g.MIN_SHOW_MS:
                    closes = not self._dialog_more_pages()          # Hide()'s own test, read BEFORE the confirm
                    if ring and e["kind"] == KIND_ADV and not e["closes"] and closes:
                        g.inbox.remove(e)                 # R4 FEWER PAGES: a page this copy lacks -- consumed, no-op
                        g.noop_pages += 1
                    elif self._host_confirm(e["index"] if e["kind"] == KIND_CHO else None):
                        if not (ring and e["closes"] and not closes):
                            g.inbox.remove(e)             # (R4 THE CLOSES BIT: kept -- it pages on to the close)
                        self._guest_track(now)
                    else:
                        e["tried"] = True                 # kept, retried; it ages out at PendingTtlMs
        if keys:
            self._release_keys(now)                       # AFTER the window events this tick applied (the guard)
            self._land_key_cursors()                      # a released KEY's cursor, the first tick its choice is ready
        # R4 THE CURSOR MIRROR (and R5's press cursor ahead of it): a locked, READY choice's cursor is the host's
        g.mirror_cursor = -1
        w = g.win
        if (ring and w is not None and w["cls"] != "local" and self.choice is not None and self._dialog_ready()
                and (not self.dialog_inh or (keys and g.key_hold(self.field_id)))):
            press = g.pending_key_cursor(self._dialog_gen) if keys else None
            if press is not None:
                self._set_choice(press)
                g.mirror_cursor = press
            elif host_here and hv is not None:
                cursor = next((o["cursor"] for o in hv["open"] if (o["win"], o["text"]) == w["key"][1:]), None)
                if cursor is not None and self._set_choice(cursor):
                    g.mirror_cursor = cursor
        # the orphan rule -- settled = the host's scene down and co-located (the bench host is never elsewhere/off-field)
        if not scene_up and co_located:
            if g.settled_since is None:
                g.settled_since = now
        else:
            g.settled_since = None
        g.settled_ms = -1 if g.settled_since is None else now - g.settled_since
        settled_long = g.settled_ms >= g.ORPHAN_GRACE_MS
        # C3KEYS-4: a polled line is handed back only on the key lock's own idle (settled AND not holding input here)
        settled = settled_long and not (keys and self.dialog_inh and holds_input)
        w = g.win
        if w is not None and w["cls"] != "local":
            host_has_it = host_here and hv is not None and any((o["win"], o["text"]) == w["key"][1:] for o in hv["open"])
            pending = g.earliest(w["key"]) is not None or host_has_it      # R4: the host's open set claims it too
            if w["cls"] == "locked":
                if settled and not pending:
                    if self.dialog_inh:
                        w["cls"] = "local"                # a script-polled line: handed back
                    else:
                        w.update(cls="orphaned", orphan_ms=now)
            elif pending or not settled:
                w["cls"] = "locked"                       # the host is busy again, or a late event
            elif self.dialog_inh:
                w["cls"] = "local"
            elif self._dialog_ready() and now - max(w["orphan_ms"], w["complete_ms"]) >= g.AUTO_READ_MS:
                # reading pace: confirm it as the host would -- a choice takes its CANCEL row, else its default
                # (NetSyncDialog.OrphanChoice(d.CancelChoice, d.DefaultChoice)); the cancel row is the beat's, as
                # SetupChoose builds it (:func:`choice_cancel`)
                closes = self.choice is not None or bool(self._beats) or len(self.texts) <= 1
                pick = None
                if self._beats and self.choice is not None:
                    cancel = choice_cancel(self._beats[0])
                    pick = cancel if cancel >= 0 else int(self._beats[0].get("default", 0))
                if self._host_confirm(pick):
                    if closes:
                        g.orphan_closes += 1
                    self._guest_track(now)
                else:
                    w["orphan_ms"] = now                  # one attempt per AutoReadMs, never per tick
        if keys:
            # R5: the script-key lock's host half -- the host busy (not settled OrphanGraceMs) or holding input here, and
            # never on a field whose Local lines still own their polls (C3KEYS-4)
            g.key_hold_base = (not settled_long or holds_input) and g.own_polls_field != self.field_id
            if g.own_polls_field >= 0 and not (g.win is not None and g.win["cls"] == "local"):
                g.own_polls_field = -1                    # no Local line left to own a poll
        g.chip = g.chip_for(self.dialog_inh, scene_up and host_here, battle=battle_bit, menu=host_menu)

    # -- [ff9mapkit netsync F3.3] C3: the bench HOST (s98) ------------------------------------------------------------
    def _bench_host_tick(self) -> None:
        """NetSyncClient.BenchHostTick, each bench tick: no bench lock = no bench host on the "lane"; otherwise a running
        replay feeds the ring (R9), the heartbeat bumps and section 7 is rebuilt -- unless the host is FROZEN (`host
        freeze`): then the last section is re-sent unchanged, exactly as a hung host's writer thread does. Flags: b0 the
        simulated scene (b1 its opposite), b2 an open non-[NFOC] bench window, b3 on a field unless `host battle`, b4
        `host menu` (or battle), b5 `host battle`."""
        ns, b = self.netsync, self._bench
        if not ns["lock"]:
            b.state = None
            return
        b.ensure()
        if b.frozen and b.state is not None:
            return
        if self._cap("keys"):
            self._service_replay()
        b.heartbeat = (b.heartbeat + 1) & 0xFFFF
        f = HF_SCENE if ns["l1"] else HF_CONTROL
        if any(not o["flags"] & WF_INH for o in b.open):
            f |= HF_LINE
        f |= (HF_BATTLE | HF_MENU) if b.battle else HF_ON_FIELD
        if b.menu:
            f |= HF_MENU
        b.state = b.build(f, self._guest.scene_nonce, self.field_id)

    def _bench_append(self, win: int, text: int, kind: int, index: int, closes_override: int = -1) -> int:
        """NetSyncClient.BenchAppend: one ADV/CHO into the bench ring, stamped with the bench scene. The page and the
        closes bit are read off this copy's own window as the host's tap reads its own (no such window -- `unmatched` --
        = page 0, closing); `closes_override` 0/1 forces the bit (R4's catch-up bench)."""
        live = self._dialog_open() and (win, text) == (self.dialog_id, self.dialog_text_id)
        page = self._dialog_page if live else 0
        closes = bool(closes_override) if closes_override >= 0 else (not live or not self._dialog_more_pages())
        b = self._bench
        b.ensure()
        bit = 0x80 if closes else 0
        if kind == KIND_CHO:
            return b.append(KIND_CHO, self._guest.scene_nonce, self.field_id, win, text, index & 0xFF, bit)
        return b.append(KIND_ADV, self._guest.scene_nonce, self.field_id, win, text, (page & 0x7F) | bit, 0)

    def _inhibited_refusal(self, win: int, text: int) -> str | None:
        """[ff9mapkit netsync F3.3] R5 LAW :1369 on the bench (NetSyncClient.InhibitedRefusal, s99): no bench verb may
        fabricate a confirm for an input-inhibited window -- its script's poll is driven by a KEY instead. None =
        allowed (no such window, or not inhibited; always None below s99)."""
        if not self._cap("keys") or not self.dialog_inh or not self._dialog_open():
            return None
        if (win, text) != (self.dialog_id, self.dialog_text_id):
            return None
        return (f"win {win} text {text} is input-inhibited ([NFOC]/[TIME]) -- no host ever emits a confirm for it "
                f"(LAW :1369); drive its script's poll with `netsync host key <uid> <bits>` (the polling uid is "
                f"`key_reader`)")

    def _bench_host_op(self, op: str, argc: int, a1: int, a2: int, a3: int) -> None:
        """NetSyncClient.BenchHostOp: the bench host's levers, each reaching the guest half only through section 7."""
        b = self._bench
        b.ensure()
        if op == "open":
            cursor = -1
            if argc >= 2:
                fw, ft = a1, a2
                if argc >= 3:
                    cursor = a3
            else:
                if not self._dialog_open():
                    raise RuntimeError("netsync host open: no dialogue window is open (or name one: open <win> <text> "
                                       "[cursor])")
                fw, ft = self.dialog_id, self.dialog_text_id
                if argc == 1:
                    cursor = a1
            if fw < 0 or fw > 255 or ft < 0 or ft > 0xFFFF or cursor >= 0xFF:
                raise RuntimeError("netsync host open: win 0..255, text 0..65535, cursor 0..254 (or none)")
            live = self._dialog_open() and (fw, ft) == (self.dialog_id, self.dialog_text_id)
            page = max(0, min(255, self._dialog_page)) if live else 1
            flags = (WF_CHOICE if cursor >= 0 else 0) | WF_COMPLETE | (WF_INH if live and self.dialog_inh else 0)
            row = {"win": fw, "text": ft, "cursor": cursor if cursor >= 0 else None, "page": page, "flags": flags}
            at = next((i for i, o in enumerate(b.open) if (o["win"], o["text"]) == (fw, ft)), None)
            if at is None:
                if len(b.open) >= b.OPEN_CAP:
                    raise RuntimeError(f"netsync host open: the bench host already has {b.OPEN_CAP} windows open "
                                       f"(netsync host shut)")
                b.open.append(row)
            else:
                b.open[at] = row
        elif op == "shut":
            b.open.clear()
        elif op in ("adv", "choice"):
            cho = op == "choice"
            if cho and (argc < 1 or a1 < 0 or a1 > 254):
                raise RuntimeError("netsync host choice: needs a choice index 0..254")
            if not self._dialog_open():
                raise RuntimeError(f"netsync host {op}: no dialogue window is open")
            inh = self._inhibited_refusal(self.dialog_id, self.dialog_text_id)      # R5: LAW :1369
            if inh is not None:
                raise RuntimeError(f"netsync host {op}: {inh}")
            self._bench_append(self.dialog_id, self.dialog_text_id, KIND_CHO if cho else KIND_ADV, a1 if cho else 0xFF,
                               (1 if a1 != 0 else 0) if not cho and argc >= 1 else -1)
        elif op == "key":
            if argc < 2 or a1 < 0 or a1 > 255 or a2 < 0 or a2 > 0xFFFF or (argc >= 3 and (a3 < 0 or a3 > 255)):
                raise RuntimeError("netsync host key: needs <uid 0..255> <bits 0..65535> [cursor 0..255]")
            b.append(KIND_KEY, self._guest.scene_nonce, self.field_id, a1, a2, a3 if argc >= 3 else 0xFF, 0)
        elif op == "gap":
            if argc < 1 or a1 < 1 or a1 > 30000:
                raise RuntimeError("netsync host gap: needs <n> 1..30000")
            b.lose(a1)
        elif op == "epoch":
            b.reset()
            b.open.clear()
        elif op == "freeze":
            b.frozen = argc < 1 or a1 != 0
        elif op == "menu":
            b.menu = argc < 1 or a1 != 0
        elif op == "battle":
            b.battle = argc < 1 or a1 != 0
        else:
            raise RuntimeError(f"netsync host: unknown op '{op}' ({'|'.join(NETSYNC_HOST_OPS)})")

    # -- [ff9mapkit netsync F3.3] R5: the script-key relay, guest half (s99) ------------------------------------------
    def _key_hold_published(self) -> bool:
        """HarnessKeyHold: enabled && the lock engaged && KeyHold(this field) -- whatever the guest's control."""
        return bool(self.netsync["enabled"] and self._guest.engaged and self._guest.key_hold(self.field_id))

    def _script_key_lock_active(self) -> bool:
        """NetSyncClient.ScriptKeyLockActive -- the caller checked the guest's control is OFF."""
        return self._cap("keys") and self._key_hold_published()

    def _purge_keys(self, now: int, engaged: bool, scene_up: bool, holds_input: bool) -> None:
        """PurgeKeys (+ HoldKeyClocks' disengaged half), every tick engaged or not: drop SPENT entries (served on an
        earlier key tick), entries for another field, entries older than KeyTtlMs, and -- once BOTH sides have been
        idle KeyIdleMs (the host's scene down and not holding input; the guest's control on, no locked line) -- entries
        at least that old. Disengaged, a cursor wait re-arms."""
        g = self._guest
        idle = (not scene_up and not holds_input and self.control
                and not (g.win is not None and g.win["cls"] != "local" and not self.dialog_inh))
        if idle:
            if not g.key_idle_armed:
                g.key_idle_armed, g.key_idle_since = True, now
        else:
            g.key_idle_armed = False
        if not g.keys:
            return
        idle_long = g.key_idle_armed and now - g.key_idle_since >= g.KEY_IDLE_MS
        keep = []
        for k in g.keys:
            if not engaged and k["defer_armed"]:
                k["defer_since"] = now
            if k["active"]:
                if k["active_tick"] == self._key_tick:
                    keep.append(k)                        # served (counted at the serve): its key tick is not over
                continue
            if (k["fld"] != self.field_id or now - k["seen"] >= g.KEY_TTL_MS
                    or (idle_long and now - k["seen"] >= g.KEY_IDLE_MS)):
                g.key_expired += 1
                continue
            keep.append(k)
        g.keys[:] = keep

    def _release_keys(self, now: int) -> None:
        """THE ORDERING GUARD (ReleaseKeys): walk the pending KEYs in seq order and release each only when no EARLIER
        host window event is still pending for the open, driven, non-[NFOC] window (KeyGuardMs at most, then released
        with a give-up). Order is kept: the walk stops at the first KEY it holds. The press cursor applies at release."""
        g = self._guest
        for k in g.keys:
            if k["released"]:
                continue
            w = g.win
            blocker = None
            if w is not None and w["cls"] != "local" and not self.dialog_inh:
                blocker = next((e for e in g.inbox if (e["field"], e["win"], e["text"]) == w["key"]
                                and _seq_after(k["seq"], e["seq"])), None)
            if blocker is not None:
                if not k["guard_armed"]:
                    k["guard_armed"], k["guard_since"] = True, now
                    return
                if now - k["guard_since"] < g.KEY_GUARD_MS:
                    return
                g.key_gaveup += 1
            k["released"] = True
            self._apply_key_cursor(k)

    def _land_key_cursors(self) -> None:
        """LandKeyCursors: a released, unserved KEY whose cursor found no ready choice at its release lands it now."""
        for k in self._guest.keys:
            if k["released"] and not k["active"] and k["cursor"] is not None and k["cursor_on"] is None:
                self._apply_key_cursor(k)

    def _apply_key_cursor(self, k: dict) -> tuple[int, bool]:
        """ApplyKeyCursor on the stand-in's one window: the press's host cursor onto a driven, READY choice before the
        poll reads GetChoose -- (the cursor applied, or a CUR_* verdict; whether the selection had to MOVE). Only the
        OLDEST cursor-carrying KEY of a reader binds (the binding order); the window it lands on is remembered."""
        g = self._guest
        if k["cursor"] is None:
            return CUR_NONE, False
        if not g.cursor_turn(k):
            return CUR_NOT_READY, False
        pinned = k["cursor_on"] is not None
        if self.choice is None or not self._dialog_open() or (pinned and k["cursor_on"] != self._dialog_gen):
            return (CUR_NOT_READY if pinned else CUR_NO_WINDOW), False
        w = g.win if g.win is not None and g.win["gen"] == self._dialog_gen else None
        if w is not None and w["cls"] == "local":
            return CUR_OWN, False                         # the guest's own choice: its own cursor
        if not pinned and (g.held_by_other_key(self._dialog_gen, k) or (w is not None and g.earliest(w["key"]))):
            return CUR_NO_WINDOW, False
        if w is None or not self._dialog_ready():
            return CUR_WAIT, False                        # opening / printing: wait for it
        if self.choice.get("selected") == k["cursor"]:
            k["cursor_on"] = self._dialog_gen
            return k["cursor"], False
        if self._set_choice(k["cursor"]):
            k["cursor_on"] = self._dialog_gen
            return k["cursor"], True
        return CUR_OUT_OF_RANGE, False

    def _take_key(self, uid: int, mask: int) -> int:
        """THE SERVE (TakeKey): the relayed press for THIS reader, once per reader per key tick -- an entry already active
        this tick answers every read by its reader in it; otherwise the first released entry for (this field, this
        reader) that overlaps the poll's mask activates, unless its cursor had to move first (served on a later read) or
        its cursor wait holds (C3KEYS-SEM-1). Returns compact bits (0 = no host press for this read)."""
        g = self._guest
        if not g.keys or uid < 0:
            return 0
        tick, fld, now = self._key_tick, self.field_id, self._guest_now()
        g.keys[:] = [k for k in g.keys if not (k["active"] and k["active_tick"] != tick)]
        for k in g.keys:
            if k["active"] and k["uid"] == uid and k["fld"] == fld:
                return k["bits"]
        for k in g.keys:
            if not k["released"] or k["active"] or k["uid"] != uid or k["fld"] != fld or not k["bits"] & mask:
                continue
            applied, changed = self._apply_key_cursor(k)
            if changed:
                return 0                                  # the cursor first: a later read sees it, then the press
            if not self._key_cursor_settled(k, applied, now):
                return 0
            k["active"], k["active_tick"] = True, tick
            g.key_served += 1
            return k["bits"]
        return 0

    def _key_cursor_settled(self, k: dict, applied: int, now: int) -> bool:
        """THE CURSOR WAIT (KeyCursorSettled): a press carrying the host's cursor is served only once that cursor is
        what the poll reads -- applied, none carried, out of range or the guest's own window: serve; no window but
        GetChoose already reads it: serve; still opening: wait (re-armed); otherwise wait KeyGuardMs, then serve with
        a give-up."""
        g = self._guest
        if applied >= 0 or applied in (CUR_NONE, CUR_OUT_OF_RANGE, CUR_OWN):
            return True
        if applied == CUR_NO_WINDOW and self.choice is not None and self.choice.get("selected") == k["cursor"]:
            return True
        if not k["defer_armed"] or applied == CUR_WAIT:
            k["defer_armed"], k["defer_since"] = True, now
            return False
        if now - k["defer_since"] < g.KEY_GUARD_MS:
            return False
        g.key_gaveup += 1
        return True

    def _filter_script_buttons(self, keys: int, mask: int, uid: int) -> tuple[int, str]:
        """NetSyncField.FilterScriptButtons for one control-off-or-on script poll (compact bits): not a spectator =
        unchanged; a spectator with control ON = the free-walk mask (Confirm/Special/Select gone -- a KEY is never served
        to a control-on read); control OFF under the script-key lock (s99) = the host-owned bits masked, the reader
        published, and the host's relayed press OR'd in; else the stock pass (and the tap-record bench taps here).
        Returns (the bits the poll reads, whose press they are)."""
        ns = self.netsync
        if not (ns["selftest"] and ns["bench"]):          # SpectatorField (the bench; a live session is not modelled)
            return keys, "local"
        if self.control:
            return keys & ~(0x40 | 0x100 | 0x01), "local"
        if self._script_key_lock_active():
            self._key_reader = uid                        # LastMaskedReader: every masked read
            return (keys & ~COMPACT_HOST_OWNED) | self._take_key(uid, mask), "host"
        self._tap_script_key(keys, mask, uid)
        return keys, "local"

    def _step_script_poll(self) -> None:
        """[ff9mapkit netsync F3.3] One script KEY TICK (EventEngine.ServiceEvents -> NetSyncField.KeyTick++), then the open
        input-inhibited window's SCRIPT POLL (:attr:`dialog_poll`, a B_KEYON on its mask) reading this frame's PRESS edges
        through :meth:`_filter_script_buttons`: a hit is its script closing the page (a polled choice: committing the
        cursor GetChoose reads) -- never a Dialog confirm. ServiceEvents runs in EVERY event-engine mode -- the field
        (HonoluluFieldMain), a battle (battle.cs / HonoluluBattleMain) and the world map (WMScriptDirector) -- so the
        counter keeps counting through a battle and on the world map; only the title screen services no events."""
        if self.ui_state != "Title" and (self.field_id > 0 or self.battle_active or self.ui_state == "WorldHUD"):
            self._key_tick += 1
        poll = self.dialog_poll
        if poll is None or not self.dialog_inh or not self._dialog_open():
            return
        uid, mask = int(poll["uid"]), int(poll.get("mask", 0x40))
        local = 0
        for button, at in self.down_at.items():
            if at == self.frame:
                local |= COMPACT_BY_CONTROL.get(AGENT_CONTROL.get(button, button), 0)
        keys, by = self._filter_script_buttons(local, mask, uid)
        hit = keys & mask
        if not hit:
            return
        choice = None
        if self.choice is not None:
            choice = int(self.choice.get("selected", 0))
            self.answered.append(choice)
            self.choice = None
            self.menu_entries = []
            self.texts, self.raw_texts = [], []
        else:
            self.texts = self.texts[1:]
            self.raw_texts = self.raw_texts[1:] if self.raw_texts else []
            self._dialog_page += 1
        self.script_poll_hits.append({"uid": uid, "bits": hit, "by": by, "choice": choice})

    # -- [ff9mapkit netsync F3.3] R9: the tap-record bench (s99) --------------------------------------------------------
    #: NetSyncClient.TapeCap: the tape holds this many events; further taps are not recorded
    TAPE_CAP = 256

    def _tap_recording(self) -> bool:
        """NetSyncClient.TapRecording: the lever, the selftest role + the bench, and the bench lock OFF."""
        ns = self.netsync
        return self._cap("keys") and self._tap_record and ns["selftest"] and ns["bench"] and not ns["lock"]

    def _record_tap(self, kind: int, a: int, b: int, c: int, x: int) -> None:
        if len(self._tape) < self.TAPE_CAP:
            self._tape.append({"kind": kind, "fld": self.field_id, "a": a, "b": b, "c": c, "x": x,
                               "t": self._guest_now()})

    def _dialog_tap(self, kind: int) -> None:
        """EmitDialogTap under the tap-record bench (the stand-in is never a socket host): a LOCAL confirm about to
        advance the open, lockable, non-[NFOC] window records one ADV (page | closes) or CHO (the committed row | closes)
        -- read BEFORE the confirm, as the engine reads it before Hide()."""
        if not self._tap_recording() or not self._dialog_open() or self.dialog_inh or not self._guest_on_field():
            return
        closes = 0x80 if not self._dialog_more_pages() else 0
        if kind == KIND_CHO and self.choice is not None:
            self._record_tap(KIND_CHO, self.dialog_id, self.dialog_text_id, int(self.choice.get("selected", 0)) & 0xFF,
                             closes)
        else:
            self._record_tap(KIND_ADV, self.dialog_id, self.dialog_text_id, (self._dialog_page & 0x7F) | closes, 0)

    def _tap_script_key(self, keys: int, mask: int, uid: int) -> None:
        """TapScriptKeyIfHost under the tap-record bench: a control-off poll that HIT host-owned bits records one KEY per
        (key tick, reader), with the frontmost choice's cursor (or none)."""
        if not self._tap_recording() or self.control:
            return
        hit = keys & mask & COMPACT_HOST_OWNED
        if not hit:
            return
        if self._key_tap_tick != self._key_tick:
            self._key_tap_tick, self._key_tap_uids = self._key_tick, set()
        if uid in self._key_tap_uids:
            return
        self._key_tap_uids.add(uid)
        cursor = int(self.choice.get("selected", 0)) if self.choice is not None else 0xFF
        self._key_taps += 1
        self._record_tap(KIND_KEY, uid, hit, cursor if 0 <= cursor < 0xFF else 0xFF, 0)

    def _service_replay(self) -> None:
        """ServiceReplay (in the bench host's tick): the due taped events into the bench ring -- paced, each at its
        recorded offset from the first; else all at once -- stamped with the bench scene NOW and the recorded field."""
        now = self._guest_now()
        base = self._replay[0]["t"] if self._replay else 0
        while self._replay_next < len(self._replay):
            t = self._replay[self._replay_next]
            if self._replay_paced and now - self._replay_start < t["t"] - base:
                return
            self._bench.append(t["kind"], self._guest.scene_nonce, t["fld"], t["a"], t["b"], t["c"], t["x"])
            self._replay_next += 1

    # -- [ff9mapkit netsync F3.3] DIO-1: the diorama warm return (s97) ----------------------------------------------
    def _live_field(self) -> bool:
        """The `dioboot` gate: gMode 1 on a field scene with a live FieldMap (a menu over it still counts)."""
        return self.field_id > 0 and not self.battle_active and self.ui_state not in (
            "Title", "WorldHUD", "BattleHUD", "BattleResult", "Tutorial")

    def _warm_verdict(self) -> str | None:
        """NetSyncDiorama.WarmVerdict's rows the stand-in can reach, in its order (None = free-standing: WARM).
        [ff9mapkit netsync F3.3] A return's entry script (:attr:`_dio_resume_until`, warm Main_Reinit or cold Main_Init)
        runs entry 0 at LEVEL 0, and the engine tests that row (`mainLevel <= 0`) BEFORE `resuming` and control -- so a
        boot in that window names the level-0 reason on either branch. The `resuming` row (entry 0 idle above level 0
        with objects still suspended) is a state the stand-in never reaches: its bracket closes with the entry script."""
        fld = self.field_id
        if fld not in self.reinit_fields:
            return f"field {fld} has no Main_Reinit (entry-0 tag 10) -- a reinit return would leave every object suspended"
        if fld not in self.encounter_fields:
            return "no random encounters are armed here -- its Main_Reinit (if any) answers a scripted fight, not a random one"
        if self._dio_resume_until is not None:
            return ("the field's entry script is still running at level 0 (Main_Init/Main_Reinit) -- Main_Reinit could "
                    "not be requested")
        if not self.control:
            return "player control is off (a scene holds it)"
        if self.ui_state != "FieldHUD":
            return "a menu or transition is up"
        if self._dialog_open():
            return "a dialogue window is open"
        if not self.has_position:
            return "no controlled actor"
        return None

    def _dio_boot(self, scene: int, *, wire_intro: int = -1, rand: bool = False) -> None:
        """NetSyncDiorama.Boot: (a refusal, :attr:`dio_boot_refusal`, leaves every observable alone) PrimeWarmReturn --
        WARM only when free-standing, the actor's position kept -- then the Replace into the debug battle, which never
        ends by itself (isDebug). [ff9mapkit netsync R3 s111] ``wire_intro`` (1 skip, 0 play, -1 own) is the boot's
        _wireIntro (HarnessBoot / BootFromWire), ``rand`` its random-encounter flag; [s112] the boot's swirl is
        recorded (its OWN length, clamped by DioramaSwirlFrames)."""
        if self.dio_boot_refusal is not None:
            return
        # [ff9mapkit netsync F3.3] Boot's `_leaveTick = TickCount - 3600000` (after every refusal): a fresh boot
        # invalidates any old leave intent, so a `dioleave` in THIS boot's swirl is deferred even if the previous
        # diorama's Leave was under 5 s ago, and a release re-requests the Leave at once
        self._dio_leave_rt = self.rt - 3600.0
        why = self._warm_verdict()
        d = self._dio
        d["boot_field"] = self.field_id
        if why is None:
            d.update(boot="warm", boot_why=None, primed=True, boot_x=round(self.player[0], 3),
                     boot_z=round(self.player[2], 3))
        else:
            d.update(boot="cold", boot_why=why, primed=False, boot_x=None, boot_z=None)
        d["booted"] = True
        self._dio_boot_frame = self.frame
        self._dio_resume_until = None
        self._dio_warm_return = False
        self.texts, self.raw_texts, self.choice = [], [], None     # the field scene is replaced
        self._beats, self._beat_phase = [], None
        self.control = False
        self._nb_boot()                                   # [ff9mapkit netsync B4] the battle lane's per-boot state
        self._nb.d_wire = wire_intro if "intro" in self._nb_caps() and wire_intro in (0, 1) else -1
        if "swirl" in self._nb_caps():
            self._nb_record_swirl(True)                   # [ff9mapkit netsync R3 s112] SFX_Rush's constructor, booted
        self.start_battle(scene, debug=True, rand=rand,
                          units=None if self.dio_units is None else [dict(u) for u in self.dio_units])

    def _dio_leave_recently(self) -> bool:
        """NetSyncDiorama.LeaveRequestedRecently: a Leave issued its Replace in the last 5 s."""
        return self.rt - self._dio_leave_rt < 5.0

    def _dio_leave(self, via: str | None = None) -> None:
        """NetSyncDiorama.Leave -- request-only: deferred (nothing issued) while the boot's swirl is still in flight;
        else the teardown lands :attr:`dio_leave_frames` later (a Leave already in flight is not re-issued).
        [ff9mapkit netsync B5] LeaveFrom(via): past its fade check, the return settle runs (s105, once per boot)."""
        if not self._dio["booted"] or self.frame - self._dio_boot_frame < self.dio_swirl_frames:
            return
        if "replay" in self._nb_caps():                     # [ff9mapkit netsync B5] s109 (design 5.4 step 2)
            self._nb_replay_abort("the host left its battle and the replay did not reach Hide within "
                                  f"{BW.REPLAY_EXIT_WAIT_MS} ms" if via == "end-leave" else "a leave of the diorama")
        if "actreplay" in self._nb_caps():
            # [ff9mapkit netsync s134] every replay still acting ends here -- past the fade check above (audit amendment 12:
            # a deferred Leave aborts nothing)
            self._act_guest.abort_all("leave", booted=True, ctx=self._act_guest_ctx())
            self._act_flush()
        self._nb_settle(via)
        self._dio_leave_rt = self.rt
        if self._dio_leave_at is None:
            self._dio_leave_at = self.frame + self.dio_leave_frames

    def _dio_return(self) -> None:
        """The teardown lands on the boot field: BeforeFieldEvents consumes a primed copy, and StartEvents takes the
        reinit branch (WARM: Main_Reinit, every actor where it stood) or Main_Init (COLD: the arrival placement).
        `returns` bumps here, before the actors are placed; control comes back when the entry script finishes."""
        d = self._dio
        warm = d["primed"]
        fld = d["boot_field"]
        self._nb_teardown()                       # [ff9mapkit netsync B4/B5] ForceDisarm: the stock menu, the return settle
        self.battle_active = False
        self.battle_debug = False
        self.commands_enabled = False
        self._close_battle_cursor()
        self.field_id = fld
        self.ui_state = "FieldHUD"
        d.update(booted=False, primed=False, returns=d["returns"] + 1, last_return="warm" if warm else "cold",
                 last_return_field=fld)
        self._guest.field_load()                  # a field load re-arms the panic unlock
        if not warm:
            x, z = self.field_spawn.get(fld, (0.0, 0.0))
            self.player = [float(x), self.player[1], float(z)]
        self.control = False
        self._dio_warm_return = warm
        self._dio_resume_until = self.frame + self.dio_resume_frames
        self._visit += 1                          # a fresh load: a new visit's actor
        self._in_trigger.clear()

    def _step_diorama(self) -> None:
        """A requested Leave's teardown landing, the return's entry script running out (control back), and
        HarnessAgent.ServiceHarnessDiorama: forget the diorama once it is down, finish a deferred release, and until
        then re-request the Leave once a second."""
        if self._dio_leave_at is not None and self.frame >= self._dio_leave_at:
            self._dio_leave_at = None
            if self._dio["booted"]:
                self._dio_return()
        if self._dio_resume_until is not None and self.frame >= self._dio_resume_until:
            self._dio_resume_until = None
            self._dio_warm_return = False
            self.control = True
        if not self._dio["booted"]:
            self._dio_by_harness = False
            if self._dio_release_pending:
                self._dio_release_pending = False
                self._selftest_release()
            return
        if self._dio_release_pending and self.rt - self._dio_retry_rt >= 1.0 and not self._dio_leave_recently():
            self._dio_retry_rt = self.rt
            self._dio_leave()

    def say(self, *pages: str, raw: str | None = None) -> None:
        """Put a dialogue box on screen. ``raw`` models the untagged SOURCE the engine also carries."""
        self.texts = list(pages)
        self.raw_texts = [raw] if raw else list(pages)
        self._dialog_gen += 1                             # s96: a NEW window, whatever it says
        self._dialog_page = 1                             # CurrentPage on its first visible page (see __init__)

    def offer(self, options: list[str], *, header: str = "What now?",
              active: list[int] | None = None) -> None:
        """Open a choice dialogue. ``active`` models the absolute indexes of the ENABLED lines."""
        self.menu_entries = list(options)
        self.menu_index = 0
        self.choice = {"selected": 0, "count": len(options) if active is None else len(active),
                       "options": [header, *options]}
        if active is not None:
            self.choice["active"] = list(active)
        self.menu["label"] = options[0] if options else None
        self._dialog_gen += 1
        self._dialog_page = 1

    def scene(self, *beats, stale: int = 0, opening: int = 6, closing: int = 6, control: bool = True) -> None:
        """Play a scripted scene with control withheld, beat by beat; control comes back after the last -- unless
        ``control`` is False: a scene in a field that never grants it (61-63, research/o3_design.md 0.2 #4), whose
        script moves on with control still off (H9; the default is as it always was). A
        beat is a page (a str) that Confirm turns, or a CHOICE (a dict: ``options``; ``default``, the script's
        defaultChoice -- the ABSOLUTE index its cursor starts on; optionally ``header``, and ``disabled``, the
        absolute indexes the script's mask leaves out; ``cancel``, its CancelChoice when a tag names one (default: the
        last row, as SetupChoose builds it -- :func:`choice_cancel`); ``typing``, frames its prompt types on once the window
        is ready) that Confirm answers at the cursor, into :attr:`answered`, or the NAMING screen (a dict
        ``{"naming": char}``: ui_state "NameSetting", no dialog; two Confirms keep the default name, into
        :attr:`named`), or a MOVIE (H9: a dict ``{"movie": frames, "skip": {"header", "options"[, "default"]}}``): no
        dialog and no control for ``frames`` frames, ui FieldHUD -- and with ``skip``, a Confirm while it plays opens
        the skip dialog (FieldHUD.cs:275-286), a choice beat with its cursor on No, :data:`SKIP_CURSOR` (``ETb.sChoose
        = 1``, :280) -- a ``default`` given must be that cursor (ValueError here otherwise); answering option 0,
        :data:`SKIP_CHOICE`, ends the movie (:430-433), any other answer resumes it for the frames it had left
        (:434-440). With ``skip``'s opt-in ``armed_after`` (frames) the hit area takes no Confirm until the movie has
        played that far (MBG.Play arms it; no dialog before the first frame). While a movie plays (its dialog up
        included) the soft-reset combo is swallowed, and a warp ends it with its scene (:attr:`movies` records each).

        A choice window as the engine publishes it (recorded at 30937 frames 900/906/936 and 30921): for
        ``opening`` frames it is up with group '' and no button and ``selected`` reads ``stale`` -- whatever
        the pooled window last held (Dialog.selectedChoice survives Reset) -- and it takes no answer; then
        group ``Dialog.Choice``, the cursor on the default (no button when that line is disabled: choiceList
        holds null there), answers taken; after one, ``closing`` frames with group '' again and the choice
        still published, then the next beat. While the prompt TYPES (the window already ready: the engine sets
        the group and the default cursor in AfterShown, with the text still animating) a Confirm only
        finishes the text (Dialog.OnKeyConfirm's TextAnimation branch) and is not an answer.

        Each dict beat is COPIED: a movie keeps its countdown (``_left``) on its beat, and the caller's dict must not
        carry it into the next scene that stages it (a replayed movie would then play no frame at all)."""
        for b in beats:                                  # checked before anything changes: the engine's cursor only
            skip = b.get("skip") if isinstance(b, dict) and "movie" in b else None
            if skip and int(skip.get("default", SKIP_CURSOR)) != SKIP_CURSOR:
                raise ValueError(f"a movie's skip dialog opens with its cursor on No, option {SKIP_CURSOR} (ETb.sChoose "
                                 f"= 1, FieldHUD.cs:280), and skips on option {SKIP_CHOICE} alone (:430): default "
                                 f"{skip['default']!r} models no engine")
        self._beats = [dict(b) if isinstance(b, dict) else b for b in beats]
        self._beat_frames = (int(opening), int(closing))
        self._scene_control = bool(control)
        self.control = False
        self._next_beat(stale)

    def _next_beat(self, stale: int = 0) -> None:
        self.menu = {"selected": None, "hovered": None, "label": None, "group": None}
        self._beat_phase = None
        if not self._beats:
            self.texts, self.raw_texts, self.choice = [], [], None
            self.control = self._scene_control
            return
        beat = self._beats[0]
        if isinstance(beat, str):
            self.say(beat)
            self.choice = None
            return
        if "keyon_pair" in beat or "chanbara" in beat or "visit" in beat:
            self._start_machine(beat)                # H10/H11/H14 (research/o4_design.md 3, o5 3.2): a machine beat
            return
        if "naming" in beat:
            # NameSettingUI: no dialog, the box focused on the prefilled default name (NameSettingUI.cs:146)
            self.texts, self.raw_texts, self.choice = [], [], None
            self.ui_state, self._name_focus = "NameSetting", True
            return
        if "movie" in beat:
            # H9: a movie -- MBG marked played (`_movie`) from its first frame to its last; resumed with the frames
            # it had left (``_left``) after its skip dialog, ended here when that dialog took the skip
            if "_left" not in beat:
                beat["_left"] = max(0, int(beat["movie"]))
                self._movie = beat
                self.movies.append({"frames": beat["_left"], "start": self.frame, "end": None, "played": 0,
                                    "skips": 0, "ended": None})
            if beat["_left"] <= 0:
                if self._movie is beat:
                    self._movie_over("played")
                self._beats.pop(0)
                self._next_beat()
                return
            self.texts, self.raw_texts, self.choice = [], [], None
            self._beat_phase = "movie"
            return
        header = beat.get("header", "What now?")
        disabled = list(beat.get("disabled", ()))
        active = [i for i in range(len(beat["options"])) if i not in disabled]
        shown = [beat["options"][i] for i in active]
        self.say("\n".join([header, *shown]))
        self.choice = {"selected": stale, "count": len(beat["options"]), "active": active, "disabled": disabled,
                       "options": [header, *shown]}
        self.menu = {"selected": None, "hovered": None, "label": None, "group": "", "button": None}
        self._beat_phase, self._beat_until = "opening", self.frame + self._beat_frames[0]

    def _choice_cursor(self, index: int) -> None:
        self.choice["selected"] = index
        button = None if index in self.choice["disabled"] else f"Choice#{index}"
        self.menu = {"selected": button, "hovered": None, "label": None, "group": "Dialog.Choice", "button": button}

    def _movie_over(self, how: str) -> None:
        """The playing movie ends (``how``: "played", "skipped" or "warp"): MBG no longer marked played."""
        self._movie = None
        if self.movies and self.movies[-1]["end"] is None:
            self.movies[-1].update(end=self.frame, ended=how)

    def _end_scene(self, why: str) -> None:
        """A scene cut short (a warp's field load): its movie ended, every beat dropped, its window closed."""
        if self._movie is not None:
            self._movie_over(why)
        self._beats, self._beat_phase = [], None
        self.texts, self.raw_texts, self.choice = [], [], None
        self.menu = {"selected": None, "hovered": None, "label": None, "group": None}

    def _step_scene(self) -> None:
        """A choice window's frame-driven phases: opening -> ready, closing -> the next beat; and a playing movie's
        frames (H9), the next beat when they run out."""
        if self._beats and self._beat_phase == "movie":
            beat = self._beats[0]
            beat["_left"] -= 1
            self.movies[-1]["played"] += 1
            if beat["_left"] <= 0:
                self._movie_over("played")
                self._beats.pop(0)
                self._next_beat()
            return
        if not self._beats or self._beat_phase not in ("opening", "closing") or self.frame < self._beat_until:
            return
        if self._beat_phase == "opening":
            self._beat_phase = "ready"
            self._choice_cursor(int(self._beats[0]["default"]))
            self._typing_until = self.frame + int(self._beats[0].get("typing", 0))
            self.readied.append(len(self.executed))
        else:
            self._beats.pop(0)
            self._next_beat()

    def _scene_press(self, button: str) -> None:
        """A press during a scene: Confirm turns a page or answers a READY choice; up/down move a ready
        choice's cursor over the enabled lines, clamped (Dialog.MoveCurrentChoice); nothing else acts."""
        if isinstance(self._beats[0], str):
            if button in ("confirm", "ok"):
                self._dialog_tap(KIND_ADV)      # [ff9mapkit netsync F3.3] R9: Dialog.OnKeyConfirm's host tap (the close)
                self._beats.pop(0)
                self._next_beat()
            return
        if "naming" in self._beats[0]:
            # the first Confirm takes focus off the box, the next is OK and saves (NameSettingUI.cs:72-83, :107,
            # :173); Cancel puts focus back on the box
            if button in ("confirm", "ok") and self._name_focus:
                self._name_focus = False
            elif button in ("confirm", "ok"):
                self.named.append(int(self._beats[0]["naming"]))
                self.ui_state = "FieldHUD"
                self._beats.pop(0)
                self._next_beat()
            elif button in ("cancel", "back", "b"):
                self._name_focus = True
            return
        if "movie" in self._beats[0]:
            # H9: a Confirm during a movie with a skip dialog opens it (FieldHUD.cs:275-286), the cursor on No
            # (SKIP_CURSOR: ETb.sChoose = 1, whatever the fixture's text); the movie waits under it with the frames it
            # has left. Opt-in (``armed_after``, frames; default 0, the hit area live from the first frame): the hit
            # area arms only that far into the movie -- MBG.Play sets it active (MBG.cs:207), and until the first frame
            # decodes MBG.IsFinished() refuses the dialog (:597-600) -- so a Confirm before then does nothing to it
            beat = self._beats[0]
            if button in ("confirm", "ok") and beat.get("skip") and self._beat_phase == "movie":
                skip = beat["skip"]
                if self.movies[-1]["played"] < int(skip.get("armed_after", 0)):
                    return
                self.movies[-1]["skips"] += 1
                self._beats.insert(0, {"header": skip.get("header", ""), "options": list(skip["options"]),
                                       "default": SKIP_CURSOR, "_movie": beat})
                self._next_beat()
            return
        if self._beat_phase != "ready":
            return
        if button in ("confirm", "ok") and self.frame < self._typing_until:
            self._typing_until = self.frame              # the text completes; nothing is answered
        elif button in ("confirm", "ok"):
            self._dialog_tap(KIND_CHO)          # [ff9mapkit netsync F3.3] R9: Dialog.OnKeyConfirm's host tap (the commit)
            self.answered.append(int(self.choice["selected"]))
            movie = self._beats[0].get("_movie")
            if movie is not None and int(self.choice["selected"]) == SKIP_CHOICE:
                # the engine's own rule, never the fixture's default: choice 0 skips (FieldHUD.cs:430-433) and the
                # movie ends under its closing dialog; any other answer resumes it (:434-440)
                movie["_left"] = 0
                self._movie_over("skipped")
            self.menu = {"selected": None, "hovered": None, "label": None, "group": "", "button": None}
            self._beat_phase, self._beat_until = "closing", self.frame + self._beat_frames[1]
        elif button in ("up", "down"):
            active = self.choice["active"]
            at = active.index(self.choice["selected"]) if self.choice["selected"] in active else 0
            at = max(0, min(len(active) - 1, at + (1 if button == "down" else -1)))
            self._choice_cursor(active[at])

    # -- H10-H12 (research/o4_design.md 3): the machine beats ----------------------------------------------------------
    def _start_machine(self, beat: dict) -> None:
        """A machine beat begins (:meth:`_next_beat`'s dispatch): ``{"keyon_pair": knobs}`` (H10, :class:`_KeyonPairBeat`),
        ``{"chanbara": knobs}`` (H11, :class:`_ChanbaraBeat`) or ``{"visit": knobs}`` (H14, :class:`_VisitBeat`;
        research/o5_design.md 3.2), its knobs checked strict here. No dialog yet, control as
        the scene left it (off); from its first frame on the machine owns the published dialog (its windows), the choice,
        the menu group and the bodies until it ends -- its own end pops the beat and moves the scene on, a warp (any new
        visit) cuts it with its scene (:meth:`_Machine.frame`). A press reaches it only through the HELD keys it reads per
        frame: :meth:`_scene_press` leaves a beat in phase "machine" alone."""
        self.texts, self.raw_texts, self.choice = [], [], None
        self._beat_phase = "machine"
        if "visit" in beat:
            self._machine = _VisitBeat(self, beat["visit"])
            return
        knobs = beat["keyon_pair"] if "keyon_pair" in beat else beat["chanbara"]
        self._machine = (_KeyonPairBeat if "keyon_pair" in beat else _ChanbaraBeat)(self, knobs)

    def _step_machine(self, slot: str) -> None:
        """The running machine beat's frame, in the slot its ``publish_order`` names (:meth:`_frame_once`)."""
        if self._machine is not None:
            self._machine.frame(self, slot)

    def open_menu(self, entries: list[str], group: str = "MainMenu") -> None:
        self.ui_state = "MainMenu"
        self.menu_entries = list(entries)
        self.menu_index = 0
        self.menu = {"selected": "Button0", "hovered": None,
                     "label": entries[0] if entries else None, "group": group}


# ======================================================================== s96: the F3.2 guest's dialogue lock
def choice_cancel(beat: dict) -> int:
    """A scene() choice beat's CANCEL row (absolute index), as DialogBoxSymbols.SetupChoose builds Dialog.CancelChoice:
    the beat's ``cancel`` when it names one (a [PCHC]/[PCHM] tag's second parameter -- -1 = none), else the LAST row
    (``choiceExactCount - 1``, the untagged menu's rule); then, with any row disabled, a cancel row that is disabled or
    not active becomes the highest ACTIVE row (``ActiveIndexes.Max()``), else it is clamped to the last row. -1 left
    standing means "no cancel": the orphan rule then takes the default (NetSyncDialog.OrphanChoice)."""
    count = len(beat["options"])
    disabled = set(int(i) for i in beat.get("disabled", ()))
    active = [i for i in range(count) if i not in disabled]
    cancel = int(beat.get("cancel", count - 1))
    if disabled:
        if cancel in disabled or cancel not in active:
            cancel = max(active) if active else -1
    else:
        cancel = min(cancel, count - 1)
    return cancel


class _GuestDialog:
    """The F3.2 guest's dialogue authority (s96: NetSyncClient.ServiceDialogAuthority + NetSyncDialog), cut down to the
    stand-in's ONE dialogue window and driven by :meth:`FakeGame._step_netsync`: THE LOCK, the inbox, the orphan rule
    and the chip -- the gates and the outcomes a driver asserts on, at the engine's tunings, on the fake's virtual
    clock. NOT modelled: the wire's bytes (s96: a bench inject IS the inbox, as on the engine; s98+: it rides the bench
    host's section 7, held as a dict -- below), a second window, the typewriter (a
    page is complete when it opens, so MinShowMs runs from the open or the page turn), the pause menu, the relay-accept
    purge and its RelayOwnMs claim, the settle clock's talk-live and host-elsewhere legs, and the `talk` relay itself
    (`netsync talk` opens nothing here: no relay-opened line, no TalkRelayTtlMs defer). An orphaned scene() choice
    closes on its CANCEL row, else its default (:func:`choice_cancel`); an offer() menu has no rows to pick from and
    simply closes.

    [ff9mapkit netsync F3.3] And the guest's LANE half of section 7 (s98): the latest view the bench host built, the epoch
    it last saw, the merge baseline, the gaps, the hung-host clock and the cursor it mirrored -- plus (s99) the KEY list
    the script-key relay serves to a polled line. The lane half survives a session drop (:meth:`forget`) and dies with
    the transport (:meth:`release`); the merge baseline and the KEYs die with the session. NOT modelled here: the codec's
    bytes (RingScript's), a pause (the KEY clocks never hold), more than one reader's binding race."""

    LINK_GRACE_MS = 3000        # NetSyncDialog.LinkGraceMs: the lock outlives a dead-reading session this long
    MIN_SHOW_MS = 350           # a host event never pages a line shown for less
    PENDING_TTL_MS = 20000      # an event its window is not waiting on ages out after this
    ORPHAN_GRACE_MS = 2000      # the host must read settled this long before an orphan
    AUTO_READ_MS = 2000         # an orphaned page stays up this long before its auto-confirm
    HOST_STALL_MS = 10000       # [ff9mapkit netsync F3.3] R6: a heartbeat frozen this long on a live lane = a hung host
    KEY_GUARD_MS = 2000         # R5: a KEY waits at most this long behind an earlier host window event (or its cursor)
    KEY_IDLE_MS = 1500          # both sides idle this long (and the KEY this old): it expires unserved
    KEY_TTL_MS = 20000          # an unserved KEY expires after this, whatever
    KEY_CAP = 32
    INBOX_CAP = 64
    HEADS_MAX = 8               # HarnessAgent publishes at most this many inbox heads
    CHIP_HICCUP = "Co-op: link hiccup -- holding this conversation for the host"
    CHIP_CLOSING = "Co-op: this line isn't on the host's screen -- closing it"
    CHIP_FOLLOWING = "Co-op: following the host's conversation"
    CHIP_HOST_SCENE = "Co-op: the host is in a scene"
    CHIP_HOST_MENU = "Co-op: the host is in a menu -- waiting"                                  # F3.3 R7: section 7 b4
    CHIP_HOST_BATTLE = "Co-op: the host is in a battle -- this line continues after it"        # F3.3 R7: section 7 b5

    def __init__(self) -> None:
        self.inbox: list[dict] = []
        self.keys: list[dict] = []  # [ff9mapkit netsync F3.3] R5: the relayed KEY list (seq order)
        self.orphan_closes = 0      # the process's telemetry: a release does not reset it (the engine's _dlg outlives it)
        self.unlock_field = -1      # the field `unlock` released (-1 = none); the next field load re-arms it
        self.field_seen = None
        self.live_armed = False     # LinkGraceMs runs from live_ms while armed (the tick-baseline law)
        self.live_ms = 0
        self.session_prev = False   # the session half of the lock on the previous tick (its rising edge marks Local)
        self.seq = 0                # the s96 bench's own host seq (u8, as _dialogSeq) -- the ring's lives on _BenchHost
        self.scene_nonce = 0        # bumps on each simulated host-scene rise (the events' `scene` stamp)
        self.noop_pages = 0         # [ff9mapkit netsync F3.3] R4 receipts (NOT published): pages consumed as no-ops
        self.epoch_resets = 0       # ...and epoch changes / head regressions that cleared the inbox
        self.view: dict | None = None
        self._lane_reset()
        self.forget()

    def _lane_reset(self) -> None:
        """[ff9mapkit netsync F3.3] NetSyncDialog.ResetLane's own half: the view, the epoch, the heartbeat and stall clock,
        and the lane counters (the KEY counters with them)."""
        self.view_valid = False
        self.view_stamp = 0
        self.last_payload: dict | None = None
        self.epoch_have = False
        self.epoch = 0
        self.hb_have = False
        self.hb = 0
        self.hb_since = 0
        self.stalled = False
        self.gaps = 0
        self.key_ignored = 0
        self.key_served = 0
        self.key_expired = 0
        self.key_gaveup = 0

    def forget(self) -> None:
        """The session is off (ResetAll): inbox, window, clocks and chip -- every line is local. [ff9mapkit netsync F3.3]
        ...the ring MERGE baseline too (a session that rises re-baselines at the host's head) and the KEY list, but NOT
        the lane (a stalled host drops the session; forgetting the stall here would re-raise it at once)."""
        self.inbox.clear()
        self.win: dict | None = None
        self.settled_since: int | None = None
        self.settled_ms = -1
        self.engaged = False
        self.live = True
        self.chip: str | None = None
        self.baselined = False
        self.last_seen = 0
        self.merged_stamp = -1
        self.mirror_cursor = -1
        self.keys.clear()
        self.key_hold_base = False
        self.key_idle_armed = False
        self.key_idle_since = 0
        self.own_polls_field = -1   # C3KEYS-4: the field whose Local lines still own their script polls

    def release(self) -> None:
        """HarnessSelfTest(false): the session's state goes, the panic unlock with it -- and the bench's host seq
        (ApplyConfigChange -> ResetIntentAndL1State -> ResetDialogLockstepState sets _dialogSeq = 0), so the first
        event after a release carries seq 0 again. [ff9mapkit netsync F3.3] ...and the lane (ResetLane): the next epoch
        this guest sees is a FIRST one."""
        self.forget()
        self._lane_reset()
        self.unlock_field = -1
        self.session_prev = False
        self.live_armed = False
        self.seq = 0

    def field_load(self) -> None:
        """RearmDialogLockAtFieldLoad: ApplyStoryBeforeEvents runs it on EVERY field scene load (HonoluluFieldMain) --
        a warp, a gateway, a reload of the same field, and the field's reload after a battle -- so the panic unlock
        ends there. (A field-id change is also caught by :meth:`FakeGame._step_netsync`; this covers the same-field
        loads it cannot see.)"""
        self.unlock_field = -1

    def ingest(self, field: int, win: int, text: int, kind: int, index: int, now: int) -> None:
        """An s96 bench injection, as DebugInjectDialogAdvanceImpl fed it: one host event into the seq-ordered inbox."""
        seq, self.seq = self.seq, (self.seq + 1) & 0xFF
        self._queue({"field": field, "win": win, "text": text, "kind": kind, "index": index & 0xFF, "seq": seq,
                     "scene": self.scene_nonce, "seen": now, "tried": False, "page": -1, "closes": False})

    def _queue(self, e: dict) -> None:
        self.inbox.append(e)
        if len(self.inbox) > self.INBOX_CAP:
            self.inbox.pop(0)                 # oldest dropped

    def clear_inbox(self) -> None:
        """ClearInbox (the panic unlock holds here): the host's events AND its relayed presses for this field."""
        self.inbox.clear()
        self.keys.clear()

    def earliest(self, key: tuple) -> dict | None:
        return next((e for e in self.inbox if (e["field"], e["win"], e["text"]) == key), None)

    def purge(self, field: int, now: int, inh: bool) -> None:
        """Drop an event for another field, and one that aged out unless the open, driven window is still on its
        way to applying it (untried, its key, not Local, not ``inh``)."""
        w = self.win

        def awaited(e: dict) -> bool:
            return (not e["tried"] and w is not None and w["cls"] != "local" and not inh
                    and w["key"] == (e["field"], e["win"], e["text"]))

        self.inbox[:] = [e for e in self.inbox if e["field"] == field
                         and (now - e["seen"] < self.PENDING_TTL_MS or awaited(e))]

    def inbox_doc(self, now: int) -> dict:
        heads, keys = [], set()
        for e in self.inbox:
            key = (e["field"], e["win"], e["text"])
            if key in keys:
                continue
            keys.add(key)
            heads.append({"field": e["field"], "win": e["win"], "text": e["text"], "kind": e["kind"],
                          "index": e["index"], "seq": e["seq"], "scene": e["scene"], "age_ms": now - e["seen"],
                          "tried": e["tried"]})
            if len(heads) >= self.HEADS_MAX:
                break
        return {"count": len(self.inbox), "heads": heads}

    def chip_for(self, inh: bool, host_scene_here: bool, *, battle: bool = False, menu: bool = False) -> str | None:
        """The chip (NetSyncDialog.UpdateChip): a hiccup while the link reads dead over a held line, else the line's
        own state, else the host's scene. [ff9mapkit netsync F3.3] R7: a locked line under a host in a battle / a menu
        (section 7 b5 / b4) reads that variant of 'following'."""
        w = self.win
        locked = w is not None and w["cls"] == "locked" and not inh   # a script-polled strip is no conversation
        orphaned = w is not None and w["cls"] == "orphaned"
        if not self.live and (locked or orphaned):
            return self.CHIP_HICCUP
        if orphaned:
            return self.CHIP_CLOSING
        if locked:
            return self.CHIP_HOST_BATTLE if battle else self.CHIP_HOST_MENU if menu else self.CHIP_FOLLOWING
        return self.CHIP_HOST_SCENE if host_scene_here else None

    # -- [ff9mapkit netsync F3.3] C3: observe the lane, the stall clock, the merge (s98) -------------------------------
    def observe(self, payload: dict | None, now: int) -> None:
        """ObserveHostDialog: section 7 read ONCE per new payload (a frozen host's re-sent slot is the same object --
        skipped), then the hung-host clock steps."""
        if payload is None or payload is not self.last_payload:
            self.last_payload = payload
            self._observe(payload)
        self._stall_step(now)

    def _observe(self, p: dict | None) -> None:
        """NetSyncDialog.Observe: no section = no view. The FIRST epoch a lane sees resets nothing; a CHANGED epoch -- or
        the same epoch with the head gone BACKWARDS (C3RING-W1) -- is a new host session: the inbox and the KEYs clear,
        a baselined guest re-baselines at the new head (history never replays) and the heartbeat restarts."""
        if p is None:
            self.view_valid = False
            return
        prev_head = self.view["head"] if self.view is not None else 0
        self.view, self.view_valid = p, True
        self.view_stamp += 1
        if not self.epoch_have:
            self.epoch_have, self.epoch = True, p["epoch"]
            return
        backwards = p["epoch"] == self.epoch and _seq_after(prev_head, p["head"])
        if p["epoch"] == self.epoch and not backwards:
            return
        self.epoch = p["epoch"]
        self.inbox.clear()
        self.keys.clear()
        if self.baselined:
            self.last_seen, self.merged_stamp = p["head"], self.view_stamp
        self.hb_have = False
        self.stalled = False
        self.epoch_resets += 1

    def _stall_step(self, now: int) -> None:
        """R6 StallStep: the heartbeat must MOVE -- unchanged HostStallMs on a fresh lane = a hung host; it re-arms the
        moment it moves. No section freezes the clock where it is (the link-dead rule owns a stale lane)."""
        if not self.view_valid:
            return
        hb = self.view["hb"]
        if not self.hb_have or hb != self.hb:
            self.hb, self.hb_since, self.hb_have = hb, now, True
            self.stalled = False
            return
        if not self.stalled and now - self.hb_since >= self.HOST_STALL_MS:
            self.stalled = True

    def merge(self, now: int, discard: bool, keys: bool) -> None:
        """NetSyncDialog.Merge: the view's ring events after the baseline into the inbox, once each (the slot re-sends
        every tick). A session's FIRST merge only baselines (what the ring holds predates the lock); `discard` (a
        panic-unlocked field) skips them; events the ring no longer holds count ONE gap. KEY: the key list (`keys`, s99)
        or counted and ignored (s98)."""
        if not self.view_valid or self.merged_stamp == self.view_stamp:
            return
        self.merged_stamp = self.view_stamp
        v = self.view
        if not self.baselined:
            self.baselined, self.last_seen = True, v["head"]
            return
        if discard:
            if _seq_after(v["head"], self.last_seen):
                self.last_seen = v["head"]
            return
        lost = (_seq_steps(self.last_seen, v["ring"][0]["seq"]) - 1 if v["ring"]
                else _seq_steps(self.last_seen, v["head"]))
        if lost > 0:
            self.gaps += 1
        for r in v["ring"]:
            if not _seq_after(r["seq"], self.last_seen):
                continue                      # already merged (the slot re-sends) -- never applied twice
            self._ingest_ring(r, now, keys)
            self.last_seen = r["seq"]
        if _seq_after(v["head"], self.last_seen):
            self.last_seen = v["head"]        # an empty ring past a gap

    def _ingest_ring(self, r: dict, now: int, keys: bool) -> None:
        if r["kind"] == KIND_KEY:
            bits = r["b"] & COMPACT_HOST_OWNED
            if not keys or bits == 0:
                self.key_ignored += 1         # s98: every KEY; s99: one with no host-owned button
                return
            self.keys.append({"seq": r["seq"], "scene": r["scene"], "fld": r["fld"], "uid": r["a"], "compact": r["b"],
                              "bits": bits, "cursor": None if r["c"] == 0xFF else r["c"], "seen": now,
                              "released": False, "guard_armed": False, "guard_since": 0, "active": False,
                              "active_tick": None, "cursor_on": None, "defer_armed": False, "defer_since": 0})
            if r["fld"] == self.own_polls_field:
                self.own_polls_field = -1     # C3KEYS-4: the host pressed here -- polls follow the host again
            if len(self.keys) > self.KEY_CAP:
                self.keys.pop(0)
                self.key_expired += 1
            return
        if r["kind"] not in (KIND_ADV, KIND_CHO):
            return                            # an unknown kind: ignored
        cho = r["kind"] == KIND_CHO
        self._queue({"field": r["fld"], "win": r["a"], "text": r["b"], "kind": r["kind"],
                     "index": r["c"] if cho else 0xFF, "seq": r["seq"], "scene": r["scene"], "seen": now,
                     "tried": False, "page": -1 if cho else r["c"] & 0x7F,
                     "closes": bool((r["x"] if cho else r["c"]) & 0x80)})

    # -- [ff9mapkit netsync F3.3] R5: the KEY list (s99) ----------------------------------------------------------------
    def key_hold(self, fld: int) -> bool:
        """KeyHold: the host half this tick, or any KEY -- pending or stored -- still waiting for this field."""
        return self.key_hold_base or any(k["fld"] == fld for k in self.keys)

    def cursor_turn(self, k: dict) -> bool:
        """THE BINDING ORDER: of one reader's cursor-carrying KEYs, only the OLDEST may put its cursor on a window."""
        for o in self.keys:
            if o is k:
                return True
            if o["uid"] == k["uid"] and o["fld"] == k["fld"] and o["cursor"] is not None:
                return False
        return True

    def held_by_other_key(self, gen: int, k: dict) -> bool:
        return any(o is not k and not o["active"] and o["cursor_on"] == gen for o in self.keys)

    def pending_key_cursor(self, gen: int) -> int | None:
        """PendingKeyCursor: the cursor a released, unserved KEY holds this window to (the oldest such), or None."""
        return next((k["cursor"] for k in self.keys if k["released"] and not k["active"] and k["cursor"] is not None
                     and k["cursor_on"] == gen), None)

    def unbind_key_cursors(self, gen: int) -> None:
        """C3KEYS-1: a departed window holds no unserved KEY's cursor (it may land again on the next one)."""
        for k in self.keys:
            if not k["active"] and k["cursor_on"] == gen:
                k["cursor_on"] = None


def _seq_after(seq: int, ref: int) -> bool:
    """[ff9mapkit netsync F3.3] NetSyncDialog.SeqAfter: (Int16)(seq - ref) > 0 -- within half the u16 space."""
    d = (seq - ref) & 0xFFFF
    return 0 < d < 0x8000


def _seq_steps(frm: int, to: int) -> int:
    """NetSyncDialog.SeqSteps: steps from `frm` to `to` along the skip-0 sequence (0 when `to` is not after it) --
    65535 -> 1 is ONE step, so a wrap never reads as a lost event."""
    if not _seq_after(to, frm):
        return 0
    d = (to - frm) & 0xFFFF
    if frm + d > 0xFFFF and frm != 0:
        d -= 1
    return d


#: [ff9mapkit netsync F3.3] ApplyKeyCursor's verdicts besides a cursor (>= 0 = that cursor is on the window the poll reads)
CUR_NONE, CUR_WAIT, CUR_NOT_READY, CUR_NO_WINDOW, CUR_OUT_OF_RANGE, CUR_OWN = -1, -2, -3, -4, -5, -6


class _BenchHost:
    """[ff9mapkit netsync F3.3] C3 R9: the selftest bench HOST -- NetSyncClient's _benchRing / _benchOpen / _benchHeartbeat
    and the DebugHost* levers -- and its HostRing (NetSyncDialog.HostRing): the newest 32 events, a u16 seq that SKIPS 0
    (65535 -> 1), an epoch drawn fresh per host session (never 0, never the last two -- C3RING-W1). `state` is the
    section 7 it built last bench tick (a dict: the stand-in carries no bytes -- the codec is RingScript's to prove),
    None while no bench lock holds the lane; a FROZEN host keeps re-sending the same object."""

    RING_CAP = 32
    OPEN_CAP = 4

    def __init__(self, rng: random.Random) -> None:
        self._rng = rng
        self.epoch = 0
        self.prev_epoch = 0
        self.seq = 0
        self.ring: list[dict] = []
        self.open: list[dict] = []    # {"win", "text", "cursor" (None = not a ready choice), "page", "flags"}
        self.heartbeat = 0
        self.frozen = self.menu = self.battle = False
        self.state: dict | None = None

    def _draw(self, avoid: int, avoid2: int) -> int:
        while True:
            e = self._rng.randrange(0, 0x10000)
            if e not in (0, avoid, avoid2):
                return e

    def ensure(self) -> None:
        """First use: Reset(NewEpoch(0)) -- epochs are never 0."""
        if self.epoch == 0:
            self.prev_epoch, self.epoch = self.epoch, self._draw(0, 0)
            self.seq = 0
            self.ring.clear()

    def reset(self) -> None:
        """A new host session (`host epoch`, a release): a new epoch -- never the current one nor the one before --,
        an empty ring, the seq from 0."""
        self.prev_epoch, self.epoch = self.epoch, self._draw(self.epoch, self.prev_epoch)
        self.seq = 0
        self.ring.clear()

    def release(self) -> None:
        """ResetDialogLockstepState's bench half: a new epoch, no open windows, no section on the lane; the levers off."""
        self.reset()
        self.open.clear()
        self.state = None
        self.frozen = self.menu = self.battle = False

    def append(self, kind: int, scene: int, fld: int, a: int, b: int, c: int, x: int) -> int:
        """HostRing.Append: one event at the next seq (skipping 0), the oldest dropped past 32. Returns its seq."""
        self.seq = 1 if self.seq == 0xFFFF else self.seq + 1
        self.ring.append({"seq": self.seq, "kind": kind, "scene": scene & 0xFF, "fld": fld & 0xFFFF, "a": a & 0xFF,
                          "b": b & 0xFFFF, "c": c & 0xFF, "x": x & 0xFF})
        if len(self.ring) > self.RING_CAP:
            self.ring.pop(0)
        return self.seq

    def lose(self, n: int) -> None:
        """`host gap <n>`: n events emitted and LOST -- the seq moves on, the ring holds none of them."""
        for _ in range(n):
            self.seq = 1 if self.seq == 0xFFFF else self.seq + 1
        self.ring.clear()

    def build(self, flags: int, scene: int, fld: int) -> dict:
        """HostRing.BuildSection: one consistent snapshot -- epoch, heartbeat, flags, the scene, the head, the first four
        open windows and the whole ring (copies)."""
        return {"epoch": self.epoch, "hb": self.heartbeat, "flags": flags, "scene": scene & 0xFF,
                "field": max(0, fld), "head": self.seq, "open": [dict(o) for o in self.open[:self.OPEN_CAP]],
                "ring": [dict(e) for e in self.ring]}


# ======================================================================== [ff9mapkit netsync R3 s121] the menu refusal
class _MenuRefusal:
    """[ff9mapkit netsync R3 s121] NetSyncField's audible-refusal statics (`netsync.menu_refusal`): the counters are
    monotonic per PROCESS (read DELTAS), and DeclineOnce's latch -- gate-class -> the LAST place it logged -- is never
    cleared at session end, so a second leg on the same field writes no new line (`lines` +0)."""

    def __init__(self) -> None:
        self.count = 0                              # HarnessMenuRefusals: audible refusals (SFX 102 asked for each)
        self.lines = 0                              # HarnessMenuRefusalLines: ...of which wrote the line
        self.silent = 0                             # HarnessMenuRefusalsSilent: s38's silent drops, counted
        self.last_state: str | None = None          # the last refused press's UIState name, either kind
        self.last_field = -1                        # ...its place (fldMapNo, wldMapNo on WorldHUD)
        self.last_rt = 0.0                          # ...its virtual time (`age_ms`; read only once `armed`)
        self.armed = False                          # _menuRefusedArmed (the tick-baseline law)
        self.muted = False                          # FF9Sfx.muteSfx at the last audible refusal
        self.buzzes = 0                             # FF9Sfx 102 plays asked for (not published: the stand-in's own tally)
        self.latch: dict = {}                       # DeclineOnce's _lastDeclineField for the menu's two gate-classes


# ======================================================================== [ff9mapkit netsync B4/B5] the battle lane
class _BattleLane:
    """[ff9mapkit netsync B4] [ff9mapkit netsync B5] The battle co-op lane's harness half on the stand-in (s100-s105,
    studies/battle-coop/B4-B5-DESIGN.md): the state behind `netsync.battle` and the B4/B5 sub-verbs. The process-wide
    statics of NetSyncBattle / NetSyncEnd / NetSyncDiorama the agent reads, kept apart so FakeGame's methods read as the
    engine's call sites.

    MODELLED: every verb's gates, refusals and levers (the agent's words, pinned by test_harness_netsync.py), every key at
    the agent's sentinels, the release on disarm / fault / `reset` (HarnessReleaseBench), and a small behaviour core --
    a selftest OWN battle's host gates (the Ready bits, the caps byte, the roster's opening, the `bcmd` intake through
    the command-phase guard), R9 in a `dioboot` diorama (a refused enqueue counts, the swing never plays), the stock
    menu's capture (`bmenu open` + the cursor's commit forwarded as a v1 frame), the bench END block fabricated through
    the Python codec (:mod:`harness.battlewire`), its presentation (victory / close / hold, R8 counting, W1 / W2) and the
    exit with the host (the end-leave, the return settle's btl_result stamp). [ff9mapkit netsync B4/B5] s106-s110: the
    roster-fed panels of a mirrored slot (the bench roster through the Python ParseRoster, each content hook and its
    lever, the repaint on a roster change, the single cast, the item count), the bench feed + the ready mirror (the
    wire Ready bit onto the stock queue, the bench host's accept / refuse, pending / refused / stranded / no-roster /
    unmap / knob / freeze), the bench manifest presets on the stand-in's save (:attr:`FakeGame.save_party` / `save_gil` /
    `save_bag` / `save_cards`), the write-nothing result-screen replay (the arm verdict, the host-chasing steps, the shadows, the
    quit guard, the abort, its own hide tail and the end-leave's wait, the fingerprint) and the host's guest-slot
    hand-back (the selftest stall, G6, G3 at the root, the submenu deferral, the lever).
    NOT MODELLED: the wire, timing below a frame, an own battle's victory and result screen (the stand-in's battles end
    at once -- so `endbench cmd` stays "armed", and the HOST's manifest is never captured: `host.manifest` stays null),
    a live peer's lane or roster (only the selftest loopback and the bench feed), the trance bridge, log lines."""

    def __init__(self):
        # ---- s100: the host command-phase gates (NetSyncBattle statics)
        self.gates_off_lever = False                # BenchHostGatesOff
        self.guest_slots = 0                        # NetSyncBattle.GuestSlots (the battle lane's; `guestslots` override)
        self.bench_guest_slots = False              # NetSyncClient._benchGuestSlots
        self.cmd_refused = 0                        # monotonic per process
        self.cmd_dropped = 0
        self.cmd_queued = 0
        self.refused_why: str | None = None
        self.dropped_why: str | None = None
        self.loop: list[bytes] = []                 # _loopCommands: parked `bcmd` frames
        self.refuse_logged: set = set()
        self.own_epoch: int | None = None           # the own battle being streamed (its battle epoch)
        self.own_battles = 0                        # own battles this process (a second one's intro sees stale keys)
        self.nonce = 0                              # the type-1 battle nonce (bumped per own battle)
        self.phase_open = False                     # _hostPhaseOpen
        self.phase_open_frame = -1
        self.roster_lag = -1
        self.roster_slots: list[int] = []
        self.roster_next_rt = 0.0                   # the plain RosterMs cadence (`hostgates 0`)
        self.last_caps = -1
        self.last_ready = -1
        self.wire_seq = 0                           # the loopback lane's seq
        self.peer: dict | None = None               # the loopback's live view {seq, nonce, caps, ready, end}
        # ---- s101: the containment backstop
        self.containment_off_lever = False          # BenchContainmentOff
        self.r9_refused = 0                         # per boot
        self.r9_total = 0                           # per process
        self.r9_cmd = -1
        self.r9_site: str | None = None
        self.assist_rt = -1e9                       # _assistTick: the control lane's last fresh frame (virtual seconds)
        self.remote_menu = False
        self.bench_control = False                  # _benchControlStamped
        # ---- s102: the stock menu
        self.capture_off_lever = False              # BenchStockCaptureOff
        self.captures = 0
        self.capture_refused = 0
        self.capture_why: str | None = None
        self.side_refused = 0
        self.side_why: str | None = None
        self.outbox: list[bytes] = []
        self.bench_open = 0
        self.touched = False                        # _stockTouched
        self.captured: dict | None = None
        # ---- s103: the end block
        self.host_mode = 0                          # BW.MODE_ON
        self.host_end: dict | None = None           # the block the last own-battle sample shipped
        self.host_trail: list[str] = []
        self.host_trail_key = -1
        self.host_key = None
        self.host_edges = 0
        self.host_changes = 0
        self.cmd_armed = False
        self.cmd_frame: bytes | None = None
        self.cmd_status: str | None = None
        self.bench_armed = False
        self.bench_block: dict | None = None        # the fabricated block, as the codec parsed it (`peer.end` serves it)
        self.bench_seq = 0                          # _benchSeq (a u16 static: never reset)
        self.bench_wire_seq = 0                     # ...the armed block's (its fabricate's) wire seq
        self.template = self.blank_template()
        self.peer_trail: list[str] = []
        self.peer_trail_key = -1
        self.peer_nonce: int | None = None
        self.trailer_bad = 0
        self.trailer_skipped = 0
        self.trailer_why: str | None = None
        # ---- s104: the guest presentation (per boot unless noted)
        self.guest_mode = 0                         # BW.GUEST_ON
        self.ach_held = 0                           # per process
        self.music = -1                             # the current music id as the stand-in plays it
        self.btl_flag = 0
        self.reset_presentation()
        # ---- s105: the exit with the host
        self.exit_mode = 0                          # BW.EXIT_MODE_ON
        self.declined_count = 0                     # per process (the watcher's late-join declines: never on a bench)
        self.declined_nonce = -1
        self.declined_why: str | None = None
        self.reset_exit()
        # ---- s106: the roster-fed menu content (NetSyncBattle.StockMenu statics)
        self.content_off_lever = 0                  # BenchContentOff: bit per hook turned OFF
        self.bench_roster: dict | None = None       # _benchRoster (as the Python ParseRoster read it)
        self.bench_info: dict | None = None         # _benchInfo (as `bench_roster` publishes it)
        self.content_hits = {n: 0 for n in BW.CONTENT_NAMES}   # monotonic per process
        self.content_faults = 0
        self.roster_gen = 0                         # _rosterGen / _rosterGenPainted (statics)
        self.roster_painted = 0
        self.roster_seen: int | None = None         # the signature TrackRosterGen last saw (None = no roster)
        self.mute_until = -1                        # the frame a repaint's MuteActiveSound releases on (-1 = not held)
        self.hud_snap: dict | None = None           # the mirrored panel AS DRAWN {slot, group, commands, rows, menu}
        self.double_cast = 0                        # BattleHUD._doubleCastCount (a double-cast pick's first half done)
        self.cast_first: dict | None = None         # ...and that first pick
        # ---- s107: the production ready mirror + the bench feed
        self.knob_bench = -1                        # BenchKnob (-1 = the ini)
        self.feed: dict | None = None               # the bench feed while armed (StartFeed)
        self.feed_nonce = 0                         # _feedNonce (a static: ++ per start)
        self.feed_view: dict | None = None          # the production _peerView the feed published {seq, nonce, caps, ready,
        #                                             guest_slots, rt}
        self.mirror_mask = 0                        # _mirrorMask: LOCAL slots the mirror holds on ReadyQueue
        self.pend: dict = {}                        # local slot -> {"wire", "rt", "seq0"} (a forwarded command's verdict)
        self.stranded_mask = 0                      # WIRE slots the last serving tick left to the digit panel
        self.stranded_turn = 0                      # _strandedTurn: WIRE slots stranded for the turn (sticky)
        self.no_roster_mask = 0                     # WIRE slots Ready and waiting for the roster
        self.mirror_nonce = -1                      # the view nonce the mirror last served
        self.no_roster_since: dict = {}             # WIRE slot -> rt it was first seen Ready without a roster entry
        self.mirror_serving = False
        self.mirror_fed = self.mirror_accepted = self.mirror_obsolete = self.mirror_closed = 0   # monotonic
        self.mirror_refused = 0                     # `menu.refused` -- monotonic
        self.stock_sent = 0                         # `menu.sent` -- monotonic
        self.mirror_faulted = False
        self.mirror_fault_why: str | None = None
        self.assist_slot = -1                       # _assistSlot
        # ---- s108: the result manifest
        self.manifest_mode = 0                      # BW.MANIFEST_SHIP_ON (`endbench manifest host on|off`)
        self.host_manifest: dict | None = None      # NOT MODELLED beyond the keys: the stand-in's own battles have no result
        self.manifest_captures = 0                  # screen, so nothing is ever captured (`host.manifest` stays null)
        self.manifest_skipped = 0
        self.manifest_bad = 0
        self.manifest_bad_why: str | None = None
        self.manifest_rx = 0
        self.manifest_preset = 0                    # the template's preset (0 = none) -- `peer.bench_manifest`
        self.manifest_note: str | None = None
        # ---- s109: the result-screen replay (per boot unless noted)
        self.replay_mode = 0                        # BW.REPLAY_MODE_ON
        self.quit_opened = False                    # _benchQuitOpened
        self.reset_replay()
        # ---- s110: the guest-slot hand-back (NetSyncBattle statics; the counters monotonic per process)
        self.handback_off_lever = False             # BenchHandbackOff
        self.hb_held = -1                              # _heldSlot
        self.hb_held_rt = 0.0
        self.hb_defer_noted = False
        self.handback_edge = False
        self.hb_captures = self.hb_returns = self.hb_deferred = self.hb_faults = 0
        self.hb_last: dict | None = None
        self.g6_mask = -1                           # _lastG6Mask (-1 = no sample)
        self.lapse_armed = False
        self.lapse_hold = False
        self.lapse_ms = 0
        self.lapse_start_rt = 0.0
        self.lapse_count = 0
        self.lapse_end_frame = -1
        self.hb_logs = 0                            # _handbackLogs: hand-back lines this own battle (HandbackLogBudget)
        # ---- [ff9mapkit netsync R3 s118] the hand-back needs a live guest: the LANE stamp beside the ownership one
        # (assist_rt), the per-own-battle latch and the refusal episode
        self.lane_rt = -1e9                         # _ctlLaneTick: ANY valid control frame (stall memory, `guest.lane_ms`)
        self.own_latch = BW.new_own_latch()         # _rptDioramaSeen (GuestOwnsStep's latch)
        self.rpt_refused = False                    # _rptRefused: the last valid frame's report kept the slots here
        self.rpt_refused_counted = False            # ...this refusal episode is counted
        self.rpt_refused_logged = False             # ...this own battle's one line is spent
        self.refused_report = 0                     # _rptRefusedCount: refusal episodes -- monotonic
        # ---- [ff9mapkit netsync R3] s111: the intro mirror (NetSyncBattle / NetSyncDiorama statics)
        self.intro_off_lever = False                # BenchIntroOff (both halves)
        self.own_intro = -1                         # _ownIntro: this own battle's latch (1 skipped, 0 played, -1 none)
        self.skipcam_set = False                    # the `bench cfg skipcam` override: in force / the value it replaced
        self.skipcam_was = 0
        self.atb_set = False                        # [s113] the `bench cfg atb` override
        self.atb_was = 0
        self.d_wire = -1                            # the diorama's _wireIntro (THIS boot)
        self.d_applied = -1                         # _introApplied / _introOwn (-1 = no SkipBattleIntro call yet)
        self.d_own = -1
        self.d_calls = 0
        self.d_normal_ms = -1
        self.d_boot_rt = 0.0
        # ---- s112: the swirl clamp
        self.swirl_local = -1                       # `bench swirl local` (-1 = [Graphics])
        self.swirl_clamp_set = False                # `bench swirl clamp` in force
        self.swirl_clamp = -1
        self.sw_diorama = False                     # the LAST swirl constructed
        self.sw_own = -1
        self.sw_used = -1
        self.sw_dwell_ms = -1
        self.sw_swirls = self.sw_dioramas = self.sw_clamps = 0   # monotonic per process
        # ---- s113: Wait parity
        self.waitparity_off_lever = False           # BenchWaitParityOff
        self.bench_ctl = -1                         # BenchCtl (-1 = auto)
        self.remote_byte = 0                        # _remoteMenuByte
        self.remote_seen = -1                       # _remoteMenuSeen (-1 = none since a null/malformed frame or a reset)
        self.legacy_seen = False
        self.ctl_out: bytes | None = None           # _ctlOut: the frame my guest side built last
        self.ctl_src: str | None = None
        self.lapse_reserve = False
        self.lapse_last_ctl: bytes | None = None    # _lapseLastCtl: the loopback's last pre-lapse frame
        # ---- s114: the start hold
        self.starthold_off_lever = False            # BenchStartHoldOff
        self.starthold_cap_bench = -1               # BenchStartHoldCapMs (-1 = the ini)
        self.bench_boot = -1                        # BenchBoot (-1 = auto)
        self.bench_boot_late_ms = 0
        self.hold: dict | None = None               # _hold (BW.new_hold_state) -- None between own battles
        self.hold_nonce = -1
        self.ctl_trailer = False
        self.rpt_nonce = self.rpt_boot = self.rpt_fmt = -1
        self.rpt_rt = -60.0
        self.guest_r3 = False
        self.ctl_null_seen = False
        self.last_ctl_legacy = False
        self.hold_why: str | None = None
        self.hold_release: str | None = None
        self.hold_held_ms = -1
        self.hold_late_ms = -1
        self.hold_count = 0                         # monotonic
        self.released = {k: 0 for k in BW.HOLD_RELEASED_KEYS.values()}   # monotonic, per reason
        self.live_latched = False                   # the diorama's LIVE latch (THIS boot)
        self.live_ms = -1
        self.live_nonce = -1
        # ---- s115-s117: flee and defeat (per boot unless noted)
        self.unit_r3: dict = {}                     # btl slot -> {mot, disappear, z} (the run-away / a KillUnit)
        self.reset_r3_end()
        self.host_flee_gil = -1                     # NOT MODELLED: the stand-in's own battles never take the flee tail

    def reset_r3_end(self) -> None:
        """[ff9mapkit netsync R3 s115-s117] NetSyncDiorama's per-boot flee / defeat state (Boot's reset)."""
        self.flee_r9b = 0
        self.flee_bypassed = 0
        self.flee_penalty = -1
        self.flee_ability_flag = False
        self.flee_msg_gil = -1
        self.follow_msg: str | None = None
        self.pre_inject = -1
        self.reverted = -1
        self.host_event = False
        self.run_until = -1                         # the run-away's frames (then the escape fade)
        self.gil_taken = 0                          # the `guest nor9b` penalty Disarm's Restore puts back at the teardown

    def reset_replay(self) -> None:
        """NetSyncDiorama.ResetReplay (every boot): the arm, its receipts and the screen's."""
        self.r_armed = self.r_pending = self.r_opened = self.r_closed = self.r_aborted = self.r_refused = False
        self.r_abort_why: str | None = None
        self.r_verdict = -1
        self.r_row_mask = self.r_seated_mask = self.r_manifest_rows = 0
        self.r_host_state_at_arm = -1
        self.r_bench = False
        self.r_arm_rt = self.r_open_rt = 0.0
        self.r_arm_ms = self.r_open_ms = self.r_close_ms = -1
        self.r_exit_waiting = False
        self.r_exit_waited = False
        self.r_exit_wait_ms = -1
        self.r_manifest: dict | None = None
        self.r_flags = 0
        self.r_open_frame = -1                      # the frame the HUD's hide callback opens the screen on
        self.r_hide_tail = False                    # _replayHideTail (the screen's own tail ran: song + fade lift)
        self.r_music_why: str | None = None
        self.screen: dict | None = None             # the replay screen's receipts (BattleResultUI's replay state)

    @staticmethod
    def blank_template() -> dict:
        """NetSyncEnd's bench template at rest (ClearBench): fighting, ui 0, no screen -- [ff9mapkit netsync B5] and no
        result manifest (s108)."""
        return {"phase": 4, "seq": 0, "result": 0, "ui": 0, "state": 0, "loading": False, "flags": 0, "manifest": None,
                "flee_gil": -1}

    def reset_presentation(self) -> None:
        """NetSyncDiorama.ResetEndPresentation (every boot): the presentation, its watchdogs and its counters."""
        self.injected = False
        self.held = False
        self.kind = -1
        self.action = 0                             # BW.PRESENT_NONE
        self.inject_phase = -1
        self.inject_seq = -1
        self.inject_rt = 0.0
        self.w1_armed = False
        self.w1_since = 0.0
        self.w1_fired = False
        self.w2_fired = False
        self.watchdog: str | None = None
        self.blocker: str | None = None
        self.why: str | None = None
        self.faulted = False
        self.hud_reasserts = 0
        self.r8_hits = 0
        self.r8_first_ms = -1
        self.phase: int | None = None               # the diorama's btl_phase / btl_seq once the presentation moved them
        self.seq: int | None = None
        self.stage_until = 0                        # the frame the current presentation step ends
        self.fade = 0                               # btl_fade_time (a Byte) at the WAIT seq

    def reset_exit(self) -> None:
        """NetSyncDiorama.ResetExit (every boot): the exit, its settle and its receipts."""
        self.exit_seen = False
        self.exit_last: dict | None = None
        self.trigger = 0                            # BW.TRIGGER_NONE
        self.latched_rt = 0.0
        self.try_rt = -3600.0
        self.tries = 0
        self.deferred = 0
        self.requested = False
        self.request_ms = -1
        self.exit_why: str | None = None
        self.settled = False
        self.via: str | None = None
        self.stamp_pending = -1
        self.stamp_host = -1
        self.stamped = -1
        self.stamped_was = -1
        self.music_shut = False
        self.music_why: str | None = None
        self.wipe_lifted = False
        self.settle_no_gameover = False

    def clear_bench(self) -> None:
        """NetSyncEnd.ClearBench: the bench end, its template and the command one-shot (the levers stay)."""
        self.bench_armed = False
        self.bench_block = None
        self.template = self.blank_template()
        self.manifest_preset = 0                    # [ff9mapkit netsync B5] s108 (_bManifestPreset / _bManifestNote)
        self.manifest_note = None
        self.cmd_armed = False
        self.cmd_frame = None
        self.cmd_status = None

    @property
    def presented(self) -> bool:
        """This boot presented (injected) or held an end -- kept after the teardown, like the engine's flags."""
        return self.injected or self.held


# ======================================================================== H10-H12: the machine beats (O4)
#: H10/H11 (research/o4_design.md 3): the agent's Control for every name a ``press`` / ``hold`` may carry --
#: HarnessAgent.ParseControl (HarnessAgent.cs:1430-1449), aliases included: ``circle``, ``x``, ``a`` and ``ok`` are
#: CONFIRM (the Cross bit, never Circle's), ``b``/``back`` Cancel, ``triangle``/``y`` Menu, ``square`` Special,
#: ``start`` Pause. Read only by the machine beats (:meth:`_Machine.level`); :func:`_control`, every other model's,
#: keeps the name as it was sent.
AGENT_CONTROL = {"confirm": "confirm", "ok": "confirm", "x": "confirm", "circle": "confirm", "a": "confirm",
                 "cancel": "cancel", "back": "cancel", "b": "cancel",
                 "menu": "menu", "triangle": "menu", "y": "menu",
                 "special": "special", "square": "special",
                 "l1": "l1", "leftbumper": "l1", "r1": "r1", "rightbumper": "r1",
                 "l2": "l2", "lefttrigger": "l2", "r2": "r2", "righttrigger": "r2",
                 "start": "pause", "pause": "pause", "select": "select",
                 "up": "up", "north": "up", "down": "down", "south": "down",
                 "left": "left", "west": "left", "right": "right", "east": "right"}
#: The bits each Control sets in the engine's input word (ETb.GetInputs = FPSManager.DelayedInputs & 0x3FFFFFF) under
#: cfg.control 0, New Game's identity logicalToButton (research/o4_design.md 0.2 #6): GetKeyMaskFromControl
#: (EventInput.cs:476-534) is the logical bit OR the physical button's -- Cross 0x4000, Circle 0x2000, Triangle 0x1000,
#: Square 0x8000, L1 0x400, R1 0x800, L2 0x100, R2 0x200 -- the four directions are set straight by ProcessInput
#: (:328-346), Pause sets Start 0x8 (:303-305) and Select 0x1.
CONTROL_BITS = {"confirm": 0x20000 | 0x4000, "cancel": 0x10000 | 0x2000, "menu": 0x1000000 | 0x1000,
                "special": 0x80000 | 0x8000, "l1": 0x100000 | 0x400, "r1": 0x200000 | 0x800,
                "l2": 0x400000 | 0x100, "r2": 0x800000 | 0x200, "pause": 0x8, "select": 0x1,
                "up": 0x10, "right": 0x20, "down": 0x40, "left": 0x80}
#: What the KEYON pairs' loops read (64 e13 t1 ip868 / ip1404 / ip1156; 150 e2 t1 ip538): logical Confirm or Special.
KEYON_PAIR_BITS = 0x20000 | 0x80000
#: e3 t1's eight KEYON checks in ip order (64 e3 t1 ip34-363): ``(bit, Byte[46] value, wrong code)`` -- a pressed bit
#: sets Byte[47] 2 when Byte[46] is its value, else Byte[47] 3 and Byte[46] its wrong code (so two keys in a tick miss).
CHANBARA_KEYS = ((0x80, 0, 11), (0x20, 1, 10), (0x1000, 2, 10), (0x40, 3, 11), (0x4000, 4, 10), (0x10, 5, 11),
                 (0x2000, 6, 11), (0x8000, 7, 11))
CHANBARA_WRONG = {value: wrong for _bit, value, wrong in CHANBARA_KEYS}
#: Byte[46] -> the prompt's button (window 112 + Byte[46], 64 e20 t1 ip789-852; block 2's mes 112-119) and its MOBI.
CHANBARA_DBTN = ("LEFT", "RIGHT", "TRIANGLE", "DOWN", "CROSS", "UP", "CIRCLE", "SQUARE")
CHANBARA_MOBI = (267, 269, 272, 270, 274, 268, 273, 271)
#: 64's windows the visit shows (block 2, US -- the research's mes_64_105_128): ``mes -> (STRT, TAIL, source,
#: rendered)``. The agent publishes the rendered text as ``texts`` (tags gone, [ZDNE] Zidane's name, ``{0}`` the
#: [NUMB] the score fills in) and ``[STRT=..][TAIL=..]`` + the source as ``phrase_raw`` -- the form O3 measured on
#: 105 (INFERRED for the rest; research/o4_design.md 3: R-CHANBARA's F1 replaces it). 124-127's "rendered" is the
#: choice's prompt; its lines are the knob ``choice_lines``.
CHANBARA_MES = {
    105: ("70,2", "LORF", "Blank\n“En garde!”[INCS][TIME=-1]", "Blank\n“En garde!”"),
    106: ("171,2", "UPLF", "[ZDNE]\n“Expect no quarter from me!”[INCS][TIME=-1]",
          "Zidane\n“Expect no quarter from me!”"),
    107: ("152,2", "LORF", "Blank\n“We shall finish this later!”[INCS][TIME=-1]", "Blank\n“We shall finish this later!”"),
    108: ("109,2", "UPLF", "[ZDNE]\n“Come back here!”[INCS][TIME=-1]", "Zidane\n“Come back here!”"),
    109: ("193,2", "LORF", "Blank\n“Is that the best thou canst do!?”[INCS][TIME=-1]",
          "Blank\n“Is that the best thou canst do!?”"),
    110: ("83,2", "UPLF", "[ZDNE]\n“Die, traitor!”[INCS][TIME=-1]", "Zidane\n“Die, traitor!”"),
    111: ("233,5", "DEFT", "[IMME][CENT=233]To follow Blank’s lead, enter the correct\n[CENT=209]commands from the "
                           "following choices:\n[XTAB=88][YADD=6][DBTN=UP][MOBI=268][XTAB=132][DBTN=TRIANGLE][MOBI=272]\n"
                           "[CENT=77][DBTN=LEFT][MOBI=267][FEED=6][DBTN=RIGHT][MOBI=269][FEED=13][DBTN=SQUARE][MOBI=271]"
                           "[FEED=6][DBTN=CIRCLE][MOBI=273]\n[XTAB=88][YSUB=6][DBTN=DOWN][MOBI=270][XTAB=132]"
                           "[DBTN=CROSS][MOBI=274]",
          "To follow Blank’s lead, enter the correct\ncommands from the following choices:"),
    120: ("156,2", "DEFT", "[WDTH=0,96,64,0,-1][IMME]Of the 100 nobles watching,\n[NUMB=0] were impressed.",
          "Of the 100 nobles watching,\n{0} were impressed."),
    121: ("102,2", "DEFT", "[IMME]Queen Brahne was\nnot impressed.", "Queen Brahne was\nnot impressed."),
    122: ("134,2", "DEFT", "[WDTH=0,96,64,0,-1][IMME]Of 100 nobles watching,\n[NUMB=0] were impressed.",
          "Of 100 nobles watching,\n{0} were impressed."),
    123: ("102,2", "DEFT", "[IMME]Queen Brahne was\nquite impressed.", "Queen Brahne was\nquite impressed."),
    124: ("174,4", "DEFT", "[PCHC=2,1][IMME]The audience is booing...\nPerform the fight scene again?\n[CHOO]"
                           "[MOVE=18,0]Yes\n[MOVE=18,0]No", "The audience is booing...\nPerform the fight scene again?"),
    125: ("174,4", "DEFT", "[PCHC=2,1][IMME]The audience did not enjoy it.\nPerform the fight scene again?\n[CHOO]"
                           "[MOVE=18,0]Yes\n[MOVE=18,0]No",
          "The audience did not enjoy it.\nPerform the fight scene again?"),
    126: ("175,4", "DEFT", "[PCHC=2,1][IMME]The audience seemed to like it.\nPerform the fight scene again?\n[CHOO]"
                           "[MOVE=18,0]Yes\n[MOVE=18,0]No",
          "The audience seemed to like it.\nPerform the fight scene again?"),
    127: ("174,4", "DEFT", "[PCHC=2,1][IMME]They demand an encore!\nPerform the fight scene again?\n[CHOO]"
                           "[MOVE=18,0]Yes\n[MOVE=18,0]No", "They demand an encore!\nPerform the fight scene again?"),
    128: ("147,1", "DEFT", "[WDTH=0,147,64,1,-1][IMME]They shower you with [C8B040][HSHD][NUMB=1] Gil[C8C8C8][HSHD]!",
          "They shower you with {0} Gil!"),
}
#: A machine beat's frame runs after the publish ("agent_first": a sample of frame f shows its state after the ticks
#: of frames <= f-1, the engine's measured order, tickrate.py:67-69) or before it ("agent_last": frames <= f).
PUBLISH_ORDERS = ("agent_first", "agent_last")
#: H10's knobs and defaults (research/o4_design.md 3): the pair's texts (and sources), the second window ``lag_ticks``
#: after the first (106 after e13's Wait(15), ip816), its INCS/250 gate ``gate_ticks`` after the second opened (an
#: ESTIMATE: <= 250), every window's close tween (``close_frames`` + ``close_s``), the publication order.
KEYON_PAIR_DEFAULTS = {"texts": None, "raw": None, "lag_ticks": 15, "gate_ticks": 40, "close_s": 0.09,
                       "close_frames": 1, "publish_order": "agent_first"}
#: H11's and H12's knobs and defaults (research/o4_design.md 3) -- each an engine value, or where unmeasured the
#: research's estimate (named so): ``seed`` (the rolls: SYSVAR[0] is Unity's unseeded Random.Range(0, 256)); ``sa``
#: (Memoria.ini SwordplayAssistance); ``bonus_fires`` (EMinigame's +30% hook fires: False models a fork whose
#: EffectiveFieldId wrap fails); ``walk_in_s`` (measured, story-o3 run 6); ``gates`` (each KEYON pair's INCS/250 gate
#: in ticks, by its first window's mes: ESTIMATES); the tweens (``close_s``/``close_frames``, ``open_s``/
#: ``open_frames``); ``reaction`` (ticks from a pass's arm to its WAIT, by the previous result Byte[45]: 99 the first
#: pass's Wait(30), 0/1 a LEFT/RIGHT hit's slide + WaitAnimation + Wait(22), the 30-frame clips -- ESTIMATES);
#: ``reqsw_ticks`` (RunScript(2,13,11)'s wait for e13); ``publish_order``; the prompts' ``prompt_raw`` /
#: ``prompt_text`` (INFERRED); ``arm_after_111`` (T0 + 12); ``walk_off_s``, ``walk_back_s`` (the encore's walk back,
#: stage 7: not in section 3's list, an ESTIMATE like walk_off_s); ``exit_wait_ticks`` (stage 9's Wait(65));
#: ``exit_to`` (REQUIRED: where Field(150) lands); ``choice_lines`` (the encore choice's published lines -- O1's
#: lesson: the first lost); ``encore`` (False: no choice, the No branch at once); ``slides`` (the LEFT/RIGHT slides
#: move the bodies); and H12's faults: ``lost`` (instance numbers whose presses the game never reads), ``miss_read``
#: (instance numbers whose right key the game scores as a miss), ``score_override`` (the score the page shows),
#: ``extra_prompts`` (passes armed past the bytes' 49), ``menu_on_triangle`` (a Triangle edge opens the main menu),
#: ``unsubstituted_once`` (122/120 and 128 publish their raw [NUMB=n] once -- for ``unsubstituted_frames`` frames from
#: that first publish, 1 by default: a drive test's way to make sure a read lands on it), ``replay_on_no`` (No replays
#: too), ``tutorial`` (False: stage 2 shows no 111 -- T0 the tick after its Wait(5) -- so the driver enters the zone on
#: its first prompt, research/o4_design.md 2.4.2).
CHANBARA_DEFAULTS = {
    "seed": 0, "sa": 1, "bonus_fires": True, "walk_in_s": 1.83, "gates": {"105": 40, "107": 40, "109": 40},
    "close_s": 0.09, "close_frames": 1, "open_s": 0.105, "open_frames": 2,
    "reaction": {99: 30, 0: 28, 1: 28, "others": 30}, "reqsw_ticks": 0, "publish_order": "agent_first",
    "prompt_raw": "[STRT=54,1][TAIL=UPRF][IMME]Press [DBTN={dbtn}][MOBI={mobi}] ![TIME=-1]",
    "prompt_text": "Press  !", "arm_after_111": 12, "walk_off_s": 2.0, "walk_back_s": 2.0, "exit_wait_ticks": 65,
    "exit_to": None, "choice_lines": ("es", "No"), "encore": True, "slides": True,
    "lost": (), "miss_read": (), "score_override": None, "extra_prompts": 0, "menu_on_triangle": False,
    "unsubstituted_once": False, "unsubstituted_frames": 1, "replay_on_no": False, "tutorial": True}
#: Blank's and Zidane's x where the fight begins (arbitrary: only a slide's delta is ever read). Blank is published
#: as the field object sid 20 (64 e0 t0 ip449's InitObject(20)); Zidane is the player.
CHANBARA_BLANK_X, CHANBARA_ZIDANE_X = 600.0, 0.0
#: The stage handshake after the fight's last pass (the Byte[26]/Bit[230] sync, e2's stage := 4 the tick after):
#: an ESTIMATE in ticks.
CHANBARA_SYNC_TICKS = 3
#: 64 e0 t0's gEventGlobal stores at entrance 100 (research/o4_design.md 4.4, 4.6): ``(ip, byte, width, value, bit)``.
CHANBARA_MAIN_INIT = ((22, 191 >> 3, "Bit", 0, 191), (49, 184 >> 3, "Bit", 0, 184), (57, 9, "Int16", -1, -1),
                      (119, 13, "Byte", 0, -1), (138, 11, "Int16", -1, -1), (200, 14, "Byte", 0, -1),
                      (416, 3815 >> 3, "Bit", 0, 3815), (425, 475, "Byte", 0, -1), (475, 8, "Byte", 125, -1))


def _machine_knobs(defaults: dict, given, what: str) -> dict:
    """A machine beat's knobs over its defaults, STRICT: an unknown knob is a ValueError (a typo is never a default),
    and so is a ``publish_order`` not in :data:`PUBLISH_ORDERS`."""
    if not isinstance(given, dict):
        raise ValueError(f"{what}: its knobs are a dict, not {given!r}")
    unknown = sorted(set(given) - set(defaults))
    if unknown:
        raise ValueError(f"{what}: unknown knob(s) {unknown} -- its knobs are {sorted(defaults)}")
    out = {**defaults, **given}
    if out["publish_order"] not in PUBLISH_ORDERS:
        raise ValueError(f"{what}: publish_order {out['publish_order']!r} is not one of {PUBLISH_ORDERS}")
    return out


class _Win:
    """One dialog window a machine beat lists (activeDialogList's order is the beat's list's): its ``slot`` (the
    script's window id), its ``kind`` -- "page" and "choice" take the UI's Confirm, "prompt" and "keyon" only a script's
    read ([TIME=-1] inhibits UI paging, DialogBoxSymbols.cs:811-826) -- the agent's ``text`` (rendered) and ``raw``
    (phrase_raw), and its life: OPENING (a page or a choice takes Confirm only once complete: the box grows from 0.3 to
    1 at deltaTime / 0.15 and AfterShown follows a frame on, DialogAnimator.cs:43-47, :61-126 -- ``open_s`` of the
    fake's clock, then ``open_frames``; research/o4_design.md 0.3 #1), listed, then CLOSING (one WaitForEndOfFrame,
    then 0 -> 0.6 at deltaTime / 0.15, DialogAnimator.cs:144-173 -- ``close_frames``, then ``close_s``; 0.2 #1) until it
    is gone from the list."""

    def __init__(self, fake, slot: int, kind: str, text: str, raw: str, *, unsub: str | None = None):
        self.slot, self.kind, self.text, self.raw = slot, kind, text, raw
        self.frame0, self.rt0 = fake.frame, fake.rt
        self.ready_at = None                       # the frame its opening ends on (a page's, a choice's)
        self.complete = kind not in ("page", "choice")
        self.closing = self.gone = False
        self.tween_frame = self.tween_rt = None
        self.unsub, self.unsub_mark = unsub, fake.publish_frame      # H12: the text its FIRST publish shows
        self.header, self.lines, self.cursor, self.answer = "", [], 0, None   # a choice's

    def shown(self) -> str:
        return self.text if self.unsub is None else self.unsub

    def close(self, fake, close_frames: int) -> None:
        if not self.closing:
            self.closing = True
            self.tween_frame = fake.frame + int(close_frames)

    def timers(self, fake, k: dict) -> None:
        """At a frame's start: the opening's end, the close tween's end, and (H12) an unsubstituted text's first
        publish behind it."""
        if not self.complete:
            if self.ready_at is None and fake.rt - self.rt0 >= float(k["open_s"]) - 1e-9:
                self.ready_at = fake.frame + int(k["open_frames"])
            if self.ready_at is not None and fake.frame >= self.ready_at:
                self.complete = True
        if self.closing and not self.gone:
            if self.tween_rt is None and fake.frame >= self.tween_frame:
                self.tween_rt = fake.rt
            if self.tween_rt is not None and fake.rt - self.tween_rt >= float(k["close_s"]) - 1e-9:
                self.gone = True
        if self.unsub is not None and fake.publish_frame - self.unsub_mark >= int(k.get("unsubstituted_frames", 1)):
            self.unsub = None


class _Machine:
    """What the machine beats share (research/o4_design.md 3, "The input model"). Per FRAME: the LEVEL -- the OR of
    the bits of every key the agent holds this frame (its down-at-frame+1 Schedule, :meth:`FakeGame._is_held`), each
    name mapped the AGENT's way (:data:`AGENT_CONTROL` -> :data:`CONTROL_BITS`); FPSManager's delayed inputs -- after a
    frame that ran a field tick the accumulator is this frame's level (FlushDelayedInputs), after one that ran none it
    ORs it in (CollectDelayedInputs), FPSManager.cs:77-139 (the release bookkeeping, which matters only for a key
    released and pressed again between two ticks, modelled as the plain OR); and the UI's own per-frame reads (a key's
    DOWN frame: a page's Confirm, a choice's cursor). Per whole field TICK of the frame (floor(ticks_run) crossings:
    whole ticks in "quantized" mode, every other frame at 60 fps "mean"): the edge ETb.ProcessKeyEvents makes, ``keyon
    = acc & ~skey; skey = acc`` (ETb.cs:50-56) -- one edge a press, none for a key held across ticks -- and the beat's
    script. Then its windows are published. A frame runs once, in the slot its ``publish_order`` names; a warp (any new
    visit) cuts the beat with its scene."""

    def __init__(self, fake, knobs: dict):
        self.k = knobs
        self.windows: list = []
        self.tick = 0
        self.acc = self.skey = self.keyon = 0
        self._ran = 1                              # the ticks the previous frame ran: the first frame flushes
        self._ticks_seen = fake.ticks_run
        self._frame_seen = fake.frame              # a frame is run once (a frozen counter repeats its number)
        self.visit0 = fake._visit
        self.done = False
        self.script = None
        self.queued: list = []                     # windows a test's director asked for (:meth:`queue_window`)

    # -- the agent's keys, as the engine reads them
    def level(self, fake) -> int:
        bits = 0
        for name in list(fake.held):
            if fake._is_held(name):
                bits |= CONTROL_BITS.get(AGENT_CONTROL.get(str(name).lower(), ""), 0)
        return bits & 0x3FFFFFF

    def downs(self, fake) -> set:
        """The Controls whose key goes DOWN on this frame -- the agent reports Down on exactly its down frame
        (HarnessAgent.cs:60-77): what the UI's per-frame reads take."""
        out = set()
        for name, at in list(fake.down_at.items()):
            if at == fake.frame and fake._is_held(name):
                c = AGENT_CONTROL.get(str(name).lower())
                if c is not None:
                    out.add(c)
        return out

    def log(self, fake, event: str, w: _Win) -> None:
        fake.machine_log.append({"event": event, "kind": w.kind, "slot": w.slot, "text": w.text, "frame": fake.frame,
                                 "tick": self.tick, "rt": round(fake.rt, 6)})

    def open(self, fake, slot: int, kind: str, text: str, raw: str, *, unsub: str | None = None) -> _Win:
        """A window joins the list THIS tick (ETb.NewMesWin: a window of its slot still open is closed first -- one
        already in its tween keeps it, ``ForceClose`` being a no-op there; research/o4_design.md 0.2 #1)."""
        for old in self.windows:
            if old.slot == slot and not old.closing:
                old.close(fake, self.k["close_frames"])
                self.log(fake, "close", old)
        w = _Win(fake, slot, kind, text, raw, unsub=unsub)
        self.windows.append(w)
        self.log(fake, "open", w)
        return w

    def close(self, fake, w: _Win) -> None:
        if not w.closing:
            w.close(fake, self.k["close_frames"])
            self.log(fake, "close", w)

    def queue_window(self, slot: int, kind: str, text: str, raw: str) -> None:
        """A test's hand from ANOTHER thread (a director): a window this beat opens at its next frame -- a page the
        script never waits on (an unclaimed dialog, a page in a quiet window). The list is the loop thread's, so the
        director only queues; the beat's own frame opens it."""
        self.queued.append((int(slot), str(kind), str(text), str(raw)))

    # -- the frame
    def frame(self, fake, slot: str) -> None:
        if self.done:
            return
        if slot == "agent_last" and fake._visit != self.visit0:
            self.cut(fake)                         # a warp or a scripted move: a new visit ends the beat
            return
        if slot != self.k["publish_order"] or fake.frame == self._frame_seen:
            return
        self._frame_seen = fake.frame
        while self.queued:
            self.open(fake, *self.queued.pop(0))
        for w in self.windows:
            was = w.gone
            w.timers(fake, self.k)
            if w.gone and not was:
                self.log(fake, "gone", w)
        self.windows = [w for w in self.windows if not w.gone]
        self.ui(fake)
        n = int(math.floor(fake.ticks_run + 1e-9) - math.floor(self._ticks_seen + 1e-9))
        self._ticks_seen = fake.ticks_run
        level = self.level(fake)
        self.acc = level if self._ran > 0 else (self.acc | level)     # Flush / CollectDelayedInputs
        self._ran = n
        for _ in range(max(0, n)):
            self.keyon = self.acc & ~self.skey                        # ETb.ProcessKeyEvents
            self.skey = self.acc
            self.tick += 1
            if fake.ui_state == "FieldHUD":                           # a menu up holds the field (H12)
                self.on_tick(fake)
            if self.done:
                return
        self.publish(fake)

    def ui(self, fake) -> None:
        """The UI's per-frame reads: a Confirm going down closes a COMPLETE page (in its opening it is dropped,
        Dialog.cs:762-797); a complete choice's cursor moves on Up / Down and a Confirm answers it at the cursor (in its
        opening a Confirm only sets SelectChoice to its default, Dialog.cs:798-802: nothing moves, nothing closes)."""
        downs = self.downs(fake)
        if not downs:
            return
        for w in self.windows:
            if w.closing or not w.complete:
                continue
            if w.kind == "page" and "confirm" in downs:
                self.close(fake, w)
            elif w.kind == "choice":
                if "down" in downs:
                    w.cursor = min(len(w.lines) - 1, w.cursor + 1)
                if "up" in downs:
                    w.cursor = max(0, w.cursor - 1)
                if "confirm" in downs:
                    w.answer = w.cursor
                    fake.answered.append(w.cursor)
                    self.close(fake, w)

    def on_tick(self, fake) -> None:
        try:
            next(self.script)
        except StopIteration:
            if not self.done:
                self.finish(fake)

    def publish(self, fake) -> None:
        """The beat's windows as the agent publishes them: ``texts`` / ``phrase_raw`` per listed window (a closing one
        until its tween ends), a choice's ``choice`` and menu group ('' while it opens or closes, Dialog.Choice ready)."""
        listed = [w for w in self.windows if not w.gone]
        fake.texts = [w.shown() for w in listed]
        fake.raw_texts = [w.raw for w in listed]
        ch = next((w for w in listed if w.kind == "choice"), None)
        if ch is None:
            fake.choice = None
            fake.menu = {"selected": None, "hovered": None, "label": None, "group": None}
            return
        fake.choice = {"selected": ch.cursor, "count": len(ch.lines), "active": list(range(len(ch.lines))),
                       "disabled": [], "options": [ch.header, *ch.lines]}
        ready = ch.complete and not ch.closing
        button = f"Choice#{ch.cursor}" if ready else None
        fake.menu = {"selected": button, "hovered": None, "label": None, "group": "Dialog.Choice" if ready else "",
                     "button": button}

    # -- the end
    def end(self, fake) -> None:
        """What the beat set up and must take down (a subclass's bodies)."""

    def finish(self, fake) -> None:
        """The beat's own end: popped, and the scene moves on (:meth:`FakeGame._next_beat`)."""
        self.done = True
        self.end(fake)
        fake._machine = None
        if fake._beats:
            fake._beats.pop(0)
        fake._next_beat()

    def cut(self, fake) -> None:
        """A warp (any new visit) cut the beat: it and its scene are gone, its windows with them."""
        self.done = True
        self.end(fake)
        fake._machine = None
        fake._beats, fake._beat_phase = [], None
        fake.texts, fake.raw_texts, fake.choice = [], [], None
        fake.menu = {"selected": None, "hovered": None, "label": None, "group": None}


class _KeyonPairBeat(_Machine):
    """H10 (research/o4_design.md 3): THE KEYON PAIR -- 64's 105/106 and 107/108, 150's 98/99, staged on their own.
    Window a, then b ``lag_ticks`` later, both [INCS][TIME=-1] (a Confirm does not page them: ``kind`` "keyon"); from
    ``gate_ticks`` after b opened (the INCS/250 gate, e13 ip825-859) each tick reads ``keyon & (Confirm | Special)``
    (ip865-885) -- an edge before the gate is consumed by its tick and lost -- and the first such edge closes both
    (ip888/891). The beat ends once both are gone (their tweens run out)."""

    def __init__(self, fake, knobs):
        k = _machine_knobs(KEYON_PAIR_DEFAULTS, knobs, "keyon_pair")
        texts = k["texts"]
        if not isinstance(texts, (list, tuple)) or len(texts) != 2 or not all(isinstance(t, str) for t in texts):
            raise ValueError(f"keyon_pair: texts is the pair's two texts, not {texts!r}")
        raw = k["raw"] if k["raw"] is not None else list(texts)
        if not isinstance(raw, (list, tuple)) or len(raw) != 2:
            raise ValueError(f"keyon_pair: raw is the pair's two sources, not {raw!r}")
        k["raw"] = list(raw)
        super().__init__(fake, k)
        self.script = self._script(fake)

    def _script(self, fake):
        k = self.k
        a = self.open(fake, 1, "keyon", k["texts"][0], k["raw"][0])
        for _ in range(int(k["lag_ticks"])):
            yield
        b = self.open(fake, 0, "keyon", k["texts"][1], k["raw"][1])
        for _ in range(int(k["gate_ticks"])):
            yield
        while not self.keyon & KEYON_PAIR_BITS:
            yield
        self.close(fake, a)
        self.close(fake, b)
        while not (a.gone and b.gone):
            yield


class _ChanbaraBeat(_Machine):
    """H11 (research/o4_design.md 3): THE CHANBARA VISIT -- 64 at entrance 100 from its arrival to Field(150), one beat
    (the score pages depend on the fight). Main_Init's stores (trace on: ``script_store``, the engine's values); stage 1,
    the walk-in (``walk_in_s``); stage 2, the KEYON pair 105/106 (105 three ticks into the stage, 106 at fifteen: e20's
    Wait(3), e13's Wait(15)) and its gate; Wait(5); the tutorial 111 (a page: WindowSync, slot 6) -- T0 the tick it is
    gone; the first arm at T0 + ``arm_after_111``; stage 3, THE FIGHT; the stage handshake; stage 4, the pair 107/108
    (at 25 and 37: e20's Wait(25), e13's Wait(37)); stage 5, the walk-off; stage 6, the score (and on Yes stages 7, 8 --
    the 109/110 pair, no 111 -- and 3 again); stage 9, Field(``exit_to``).

    THE FIGHT, per field tick in the engine's object order -- e2, e4, e3, e13, e20 (Main_Init's InitCode(4),
    InitCode(3), InitObject 5, 6, 13, 20 append in that order, Obj.cs:31-45; EBin.ProcessCode walks the list once a
    tick):
      * e4 (``sa`` >= 2): ``Byte[52] > 0 and Int16[34] < 50`` refills TimeLeft to 50 (EMinigame.cs:23-30);
      * e3 (a prompt up, ``Byte[47] == 1``): the eight checks in ip order (:data:`CHANBARA_KEYS`) on this tick's EDGE,
        Start held a LEVEL miss (ip412), CloseWindow(1) on a hit or a miss (ip459/484), then TimeLeft-- (the hit tick
        decrements too: a hit at the j-th poll credits 50 - j);
      * e13: Zidane's slide, a tick behind Blank's (0.3 #3);
      * e20, the pass machine: ARM (the roll and its filters, ip462-707; while ``Int16[34] < 49``: Byte[47] 1, the
        no-repeat Byte[44], TimeLeft 50 and window 112 + Byte[46] LISTED THIS TICK, ip721-852), REACT for
        ``reaction[Byte[45]] + reqsw_ticks`` ticks (a LEFT / RIGHT hit before it: SByte[38] -/+ 1 and the slide, Blank
        -60 a tick from S+1 to -300 after S+5, Zidane from S+2 to S+6), then the WAIT while ``TimeLeft > 0 and
        Byte[47] == 1``, then SCORE (a timeout: Byte[47] 3, CloseWindow; a hit: I30 += TimeLeft, I32 += I40, I40 + 1; a
        miss: I40 0; I42 the max; Byte[45] := Byte[46]; Int16[34] + 1) and the next ARM IN THE SAME TICK -- so a timeout,
        or a hit later than the reaction, re-arms at once, the old window still in its tween beside the new (0.2 #1, #2).
        Pass 49 arms nothing: the PHANTOM pass credits pass 48's result again (I32 1225, I42 50 on 49 hits).

    The score (e4 t1 ip208-537): (I30 + I32) // 29; EMinigame's hook (``bonus_fires``: +30% at ``sa`` >= 1, then
    "Encore" at >= 75); H12's ``score_override``; the clamp; the gil; ip338's store when Byte[475] is below it; 120/121
    (max combo below 50) or 122, Wait(5), 123 and ip390's Bit[3815] := 1 AFTER 123; Wait(10); the choice by band (124
    < 25, 125 < 50, 126 < 75, else 127) with its cursor on Yes (0); No: Wait(15), 128, the gil; Yes: the encore.
    ``fake.chanbara_log`` keeps every prompt's arm tick, edge tick and true j."""

    def __init__(self, fake, knobs):
        k = _machine_knobs(CHANBARA_DEFAULTS, knobs, "chanbara")
        if not isinstance(k["exit_to"], int) or isinstance(k["exit_to"], bool):
            raise ValueError(f"chanbara: exit_to (the field Field(150) lands in) is required, not {k['exit_to']!r}")
        k["gates"] = {**CHANBARA_DEFAULTS["gates"], **{str(m): int(t) for m, t in (knobs.get("gates") or {}).items()}}
        k["reaction"] = {**CHANBARA_DEFAULTS["reaction"],
                         **{("others" if r == "others" else int(r)): int(t)
                            for r, t in (knobs.get("reaction") or {}).items()}}
        k["lost"], k["miss_read"] = {int(n) for n in k["lost"]}, {int(n) for n in k["miss_read"]}
        k["choice_lines"] = list(k["choice_lines"])
        super().__init__(fake, k)
        import random
        self.rng = random.Random(k["seed"])
        self.v = dict.fromkeys(("I30", "I32", "I34", "I36", "I40", "I42", "I48", "I50", "sb38", "sb39", "b27", "b44",
                                "b45", "b46", "b47", "b52"), 0)
        self.fight = 0                             # fights begun (the encore's is the second)
        self.instance = 0                          # prompts armed in this fight (1-based)
        self.prompt = self.row = None              # the armed prompt's window and its chanbara_log row
        self.phase = None                          # e20's: "arm" / "react" / "wait" / "done"
        self.arm_tick = self.react = 0
        self.slides: list = []                     # [body, x0, dir, start tick]
        self.t0_tick = None
        self.field = fake.field_id
        self.blank = {"x": CHANBARA_BLANK_X, "z": 0.0, "r": 1.0, "sid": 20, "uid": 20, "coll": False}
        fake.blockers[self.field] = [*fake.blockers.get(self.field, ()), self.blank]
        fake.player = [CHANBARA_ZIDANE_X, 0.0, 0.0]
        self.script = self._script(fake)

    # -- the input (H12 ``lost``) and the UI (H12 ``menu_on_triangle``)
    def level(self, fake) -> int:
        if self.phase in ("react", "wait") and self.v["b47"] == 1 and self.instance in self.k["lost"]:
            return 0                               # the agent took the press; the game's input path dropped it
        return super().level(fake)

    def ui(self, fake) -> None:
        if self.k["menu_on_triangle"] and fake.ui_state == "FieldHUD" and "menu" in self.downs(fake):
            fake.ui_state = "MainMenu"             # IsMenuControlEnable on: the menu, the prompt left armed
        super().ui(fake)

    def on_tick(self, fake) -> None:
        super().on_tick(fake)
        if not self.done:
            self._slide_tick(fake)

    def end(self, fake) -> None:
        bodies = fake.blockers.get(self.field)
        if bodies is not None:
            fake.blockers[self.field] = [b for b in bodies if b is not self.blank]

    # -- the script's pieces
    def _wait_s(self, fake, seconds):
        until = fake.rt + float(seconds)
        while fake.rt < until - 1e-9:
            yield

    def _ticks(self, n):
        for _ in range(int(n)):
            yield

    def _open_mes(self, fake, slot: int, kind: str, mes: int, *, numb=None) -> _Win:
        strt, tail, src, text = CHANBARA_MES[mes]
        shown = text.format(numb) if numb is not None else text
        unsub = None
        if numb is not None and self.k["unsubstituted_once"]:
            unsub = text.format(f"[NUMB={1 if mes == 128 else 0}]")
        return self.open(fake, slot, kind, shown, f"[STRT={strt}][TAIL={tail}]{src}", unsub=unsub)

    def _pair(self, fake, a: int, b: int, a_at: int, b_at: int, gate: int):
        """A KEYON pair (H10's rule): a ``a_at`` ticks into the stage (slot 1, e20's), b at ``b_at`` (slot 0, e13's),
        the gate ``gate`` ticks after b opened, then the first Confirm or Special EDGE closes both."""
        yield from self._ticks(a_at)
        wa = self._open_mes(fake, 1, "keyon", a)
        yield from self._ticks(b_at - a_at)
        wb = self._open_mes(fake, 0, "keyon", b)
        yield from self._ticks(gate)
        while not self.keyon & KEYON_PAIR_BITS:
            yield
        self.close(fake, wa)
        self.close(fake, wb)

    def _page(self, fake, mes: int, *, numb=None):
        """WindowSync(5|6, 0, mes): a page the UI's Confirm closes once complete; the script resumes the tick it is
        gone."""
        w = self._open_mes(fake, 6 if mes == 111 else 5, "page", mes, numb=numb)
        while not w.gone:
            yield
        return w

    def _choice(self, fake, mes: int):
        """WindowSync(5, 0, mes): the encore choice, its cursor on Yes -- ETb.sChoose 0 after a flags-0 WindowSync
        (ETb.cs:100-104) -- answered by the UI; the script resumes the tick it is gone, with the answer."""
        strt, tail, src, header = CHANBARA_MES[mes]
        lines = list(self.k["choice_lines"])
        w = self.open(fake, 5, "choice", "\n".join([header, *lines]), f"[STRT={strt}][TAIL={tail}]{src}")
        w.header, w.lines, w.cursor = header, lines, 0
        while not w.gone:
            yield
        return w.answer

    def _script(self, fake):
        k, v = self.k, self.v
        for ip, byte, width, value, bit in CHANBARA_MAIN_INIT:      # 64 e0 t0 at entrance 100
            fake.script_store(0, 0, ip, byte, width, value, bit=bit)
        yield from self._wait_s(fake, k["walk_in_s"])               # stage 1
        first = True
        while True:
            for key in v:                                           # e13 stage 2 / 8: every minigame var := 0
                v[key] = 0
            if first:
                yield from self._pair(fake, 105, 106, 3, 15, k["gates"]["105"])     # stage 2
                yield from self._ticks(5)                           # SetDialogProgression(0), Wait(5)
                if k["tutorial"]:                                   # H12: False -- no 111 (the zone entered on a prompt)
                    yield from self._page(fake, 111)                # WindowSync(6, 0, 111)
                self.t0_tick = self.tick                            # T0: the tick 111 is gone
            else:
                yield from self._pair(fake, 109, 110, 3, 15, k["gates"]["109"])     # stage 8: no tutorial
            yield from self._ticks(k["arm_after_111"])              # Wait(10), the sync, e2's Byte[24] := 3
            yield from self._fight(fake)                            # stage 3
            yield from self._ticks(CHANBARA_SYNC_TICKS)
            yield from self._pair(fake, 107, 108, 25, 37, k["gates"]["107"])        # stage 4
            yield from self._wait_s(fake, k["walk_off_s"])          # stage 5
            again = yield from self._score(fake)                    # stage 6
            if not again:
                break
            yield from self._wait_s(fake, k["walk_back_s"])         # stage 7: the walk back
            first = False
        fake.script_store(2, 1, 331, 8, "Byte", 0)                  # stage 9 (64 e2 t1 ip331)
        yield from self._ticks(k["exit_wait_ticks"])                # Wait(65), ip478
        fake.script_store(2, 1, 528, 2, "Int16", 325)               # ip528
        self.windows = []
        fake.field_id = int(k["exit_to"])                           # Field(150), ip536: a fresh visit
        fake.player = [0.0, 0.0, 0.0]
        fake._visit += 1
        fake._in_trigger.clear()
        self.finish(fake)

    # -- stage 3
    def _fight(self, fake):
        self.fight += 1
        self.instance = 0
        self.v["b45"] = 99                                          # e20 stage 3's start (ip440)
        self.phase = "arm"
        while True:
            self._fight_tick(fake)
            if self.phase == "done":
                return
            yield

    def _fight_tick(self, fake) -> None:
        k, v = self.k, self.v
        # e4: under SwordplayAssistance >= 2 every sid-4 token fetch refills TimeLeft (EMinigame.cs:23-30)
        if k["sa"] >= 2 and v["b52"] > 0 and v["I34"] < 50:
            v["b52"] = 50
        # e3: the poll, only while a prompt is up (ip23)
        if v["b47"] == 1:
            for bit, value, wrong in CHANBARA_KEYS:
                if self.keyon & bit:
                    if v["b46"] == value:
                        v["b47"] = 2
                    else:
                        v["b47"], v["b46"] = 3, wrong
            if self.acc & 0x8:                                      # Start HELD: a level read (B_KEY(8), ip412)
                v["b47"], v["b46"] = 3, 11
            if v["b47"] == 2 and self.instance in k["miss_read"]:  # H12: the right key scored as a miss
                v["b47"], v["b46"] = 3, CHANBARA_WRONG[v["b46"]]
            if v["b47"] in (2, 3):
                self.close(fake, self.prompt)                       # CloseWindow(1), ip459 / ip484
                self.row.update(edge_tick=self.tick, edge_frame=fake.frame, j=self.tick - self.row["arm_tick"],
                                result="hit" if v["b47"] == 2 else "miss")
            if v["b52"] > 0:
                v["b52"] -= 1
        # e20: the pass machine
        if self.phase == "arm":
            self._arm(fake)
        elif self.phase == "react" and self.tick - self.arm_tick >= self.react:
            self.phase = "wait"
        if self.phase == "wait" and not (v["b52"] > 0 and v["b47"] == 1):
            if v["b47"] == 1:                                       # the timeout, ip1397-1424
                v["b47"], v["b46"] = 3, 11
                self.close(fake, self.prompt)
                self.row["result"] = "timeout"
            if v["b47"] == 2:                                       # ip1438-1474
                v["I30"] += v["b52"]
                v["I32"] += v["I40"]
                v["I40"] += 1
            if v["b47"] == 3:                                       # ip1490
                v["I40"] = 0
            if v["I40"] > v["I42"]:                                 # ip1498-1508
                v["I42"] = v["I40"]
            v["b45"] = v["b46"]                                     # ip1534
            v["I34"] += 1                                           # ip1541
            if v["I34"] < 50 + int(k["extra_prompts"]):             # ip1546: the next pass, IN THIS TICK
                self._arm(fake)
            else:
                self.phase = "done"

    def _arm(self, fake) -> None:
        k, v = self.k, self.v
        v["b46"] = 88                                               # the roll and its filters, ip451-707
        while v["b46"] == 88:
            v["b46"] = self.rng.randrange(256) & 7
            if v["sb38"] in (-1, 0) and v["b46"] == 0:
                v["b46"] = 88
            if v["sb38"] in (1, 2) and v["b46"] == 1:
                v["b46"] = 88
            if v["I42"] < 10 and v["b46"] in (3, 5):
                v["b46"] = 88
            if v["I42"] < 15 and v["b46"] == 6:
                v["b46"] = 2
            if v["I42"] < 15 and v["b46"] == 7:
                v["b46"] = 4
            if v["b46"] == v["b44"]:
                v["b46"] = 88
        if v["I34"] < 49 + int(k["extra_prompts"]):                # ip710: passes 0..48 show their prompt
            v["b47"], v["b44"], v["b52"] = 1, v["b46"], 50         # ip721-736
            self.instance += 1
            dbtn = CHANBARA_DBTN[v["b46"]]
            self.prompt = self.open(fake, 1, "prompt", k["prompt_text"],
                                    k["prompt_raw"].format(dbtn=dbtn, mobi=CHANBARA_MOBI[v["b46"]]))
            self.row = {"fight": self.fight, "n": self.instance, "dbtn": dbtn, "value": v["b46"], "arm_tick": self.tick,
                        "arm_frame": fake.frame, "edge_tick": None, "edge_frame": None, "j": None, "result": None,
                        "sb38": v["sb38"], "max_combo": v["I42"]}       # what the roll's filters read
            fake.chanbara_log.append(self.row)
        prev = v["b45"]                                             # the reaction to the previous result (ip861-1370)
        self.react = int(k["reaction"].get(prev, k["reaction"]["others"])) + int(k["reqsw_ticks"])
        if prev in (0, 1):
            d = -1 if prev == 0 else 1
            v["sb38"] += d                                          # ip918 / ip1066
            if k["slides"]:
                self.slides.append(["blank", self.blank["x"], d, self.tick])
                self.slides.append(["player", fake.player[0], d, self.tick + 1])
        self.arm_tick = self.tick
        self.phase = "react"

    def _slide_tick(self, fake) -> None:
        """Each running slide's step this tick: -/+60 a tick, k = 1..5 ticks past its start (Blank's start the arm tick,
        Zidane's a tick later: e13 takes the request the next tick; each loop's i = 0 moves nothing, 0.3 #3)."""
        keep = []
        for s in self.slides:
            body, x0, d, start = s
            kk = self.tick - start
            if kk >= 1:
                x = x0 + d * 60.0 * min(kk, 5)
                if body == "blank":
                    self.blank["x"] = x
                else:
                    fake.player[0] = x
            if kk < 5:
                keep.append(s)
        self.slides = keep

    # -- stage 6
    def _score(self, fake):
        k, v = self.k, self.v
        v["I48"] = (v["I30"] + v["I32"]) // 29                      # ip208
        if k["bonus_fires"]:                                        # EMinigame at sid 4 ip 223 (EMinigame.cs:12-21)
            if k["sa"] >= 1:
                v["I48"] += v["I48"] // 10 * 3
            if v["I48"] >= 75:
                fake.achievements.append("Encore")                  # EMinigame.cs:34-38
        if k["score_override"] is not None:                         # H12: a fork that scores differently
            v["I48"] = int(k["score_override"])
        if v["I48"] > 100:                                          # ip233
            v["I48"] = 100
        if v["I48"] <= 0:                                           # ip252
            v["I48"] = 1
        v["I50"] = ((v["I30"] // 5 + v["I32"]) + v["I42"] * 2 + v["I40"] * 2) // 2 + 1     # ip260
        if v["I48"] == 100:                                         # ip296-307
            v["I50"] = 10000
        fake.chanbara_vars = dict(v)
        if fake.story_bytes[475] < v["I48"]:                        # ip327-338
            fake.script_store(4, 1, 338, 475, "Byte", v["I48"])
        if v["I42"] < 50:                                           # ip346-366
            yield from self._page(fake, 120, numb=v["I48"])
            yield from self._ticks(5)
            yield from self._page(fake, 121)
        else:                                                       # ip375-390
            yield from self._page(fake, 122, numb=v["I48"])
            yield from self._ticks(5)
            yield from self._page(fake, 123)
            fake.script_store(4, 1, 390, 3815 >> 3, "Bit", 1, bit=3815)
        yield from self._ticks(10)                                  # ip399
        if k["encore"]:
            mes = 124 if v["I48"] < 25 else 125 if v["I48"] < 50 else 126 if v["I48"] < 75 else 127
            answer = yield from self._choice(fake, mes)
        else:
            answer = 1
        if answer == 0 or k["replay_on_no"]:                        # ip476: Yes (or H12's replay on No)
            return True
        v["b27"] = 1                                                # ip509
        yield from self._ticks(15)                                  # ip517
        yield from self._page(fake, 128, numb=v["I50"])             # ip531
        fake.gil += v["I50"]                                        # AddGi, ip537
        return False


# ======================================================================== H13-H15: O5's sink and visit beat
#: H13 (research/o5_design.md 3.1): StoryTrace.ChangeRowsPerSite (StoryTrace.cs:56) -- the CHANGING stores the sink emits
#: per site per epoch (:391-394); later ones are counted, as every same-value store after a site's first is.
STORY_CHANGE_ROWS = 64
#: H14 (research/o5_design.md 3.2): a visit beat's step kinds -- each step names exactly one -- and the other keys each
#: kind may carry; anything else is a ValueError when the beat starts (:func:`_visit_steps`), never a default. ``text`` /
#: ``raw`` (a pair's ``texts`` / ``raws``) are what the agent publishes: default ``mes N`` and ``[STRT=0,0]`` + it.
VISIT_STEP_KEYS = {"store": (), "wait": (), "place": (), "grant": (), "field": (), "stairs": (),
                   "page": ("slot", "typing_s", "text", "raw", "async"), "timed": ("slot", "ticks", "text", "raw"),
                   "pair": ("lag", "gate", "texts", "raws"),
                   "choice": ("slot", "header", "lines", "typing_s", "gap", "stale", "branch", "raw"),
                   # H17, H18 (research/o6_design.md 3.3, 3.4): Menu(1, char)'s naming screen -- ``name`` the default it
                   # pre-fills -- and the regions' tag 2 with ExitField's walk-out (its knobs :data:`DOOR_DEFAULTS`)
                   "naming": ("name",), "door": (),
                   # H24 (the O7 review's finding, 159 e16 t1's own order): a page's ``async`` -- WindowAsync: the
                   # script runs on while it is up -- and WaitWindow(slot), the hold until that slot's window is gone
                   "wait_window": ()}
#: H14's knobs and defaults (research/o5_design.md 3.2), each the engine's value or the design's named estimate:
#: ``steps`` (REQUIRED: the visit's step list); ``index`` (its 1-based position in the route -- what H15's per-visit faults
#: are keyed by); ``field_to`` (a ``field`` step's ``to`` -> the field id it lands in); ``donor`` (the visit's
#: ``fake.donor``: on F the member's donor, DataPatchers' EffectiveFieldId; None on S -- and in the donor's own field);
#: O4's tweens (``open_s``/``open_frames``, ``close_s``/``close_frames``); ``ready_lag_frames`` (a choice's frames between
#: its group and ``isChoiceReady``, Dialog.cs:161-164); ``wait_scale`` (the ``wait`` steps only: a test runs 0.25);
#: ``publish_order``; ``bodies`` (the visit's published objects, as ``fake.blockers`` dicts) -- then H15's faults
#: (research/o5_design.md 3.3), each absent by default: see :class:`_VisitBeat` -- and O6's (research/o6_design.md 3.3,
#: 3.5), each absent by default too: ``name_typed`` (the name a naming screen's OK saves: a typed name's stand-in),
#: ``naming_deaf`` (the screen drops its first k Confirms), ``unparsed_frames`` (``{mes: k}``: that window publishes its
#: raw text, tags included, for its first k frames) and ``door_misroute`` (``{door name: field_to key}``: that door's
#: Field() lands there).
VISIT_DEFAULTS = {
    "steps": None, "index": None, "field_to": {}, "donor": None, "open_s": 0.105, "open_frames": 2, "close_s": 0.09,
    "close_frames": 1, "ready_lag_frames": 1, "wait_scale": 1.0, "publish_order": "agent_first", "bodies": (),
    "store_override": None, "grant_at": None, "land_real": None, "reask": False, "stray_confirm_at_ready": False,
    "cursor_to": None, "confirm_deaf": 0, "gap_ticks": None, "no_contour": False, "side_scene_at": None,
    "error_window": None, "name_typed": None, "naming_deaf": 0, "unparsed_frames": None, "door_misroute": None}
#: H17 (research/o6_design.md 3.3): the text tag a page renders as Steiner's name -- [STNR], a constant replace tag
#: (FFIXTextTag.cs:390) resolved to PLAYER.Name of CharacterId 3 (DialogBoxSymbols.cs:67-68) -- and the default
#: NameSettingUI pre-fills (CharacterDefaultName), rendered until a naming screen's OK saves another (``fake.names``).
STNR_TAG, STNR_CHAR, STNR_NAME = "[STNR]", 3, "Steiner"
#: H18 (research/o6_design.md 3.4): a ``door`` step's knobs and defaults -- ``doors``, the regions' tag 2 in ENTRY order
#: (each a dict of :data:`DOOR_KEYS`), and ``speed``, the walk-out's u a field tick (MOVJ at his last controlled frame's
#: speed: HonoUpdate's 60 for a run, FieldMapActorController.cs:210-211). A door holds every :data:`DOOR_NEEDS` --
#: ``name``, ``points`` (IsInQuad's polygon), ``stores`` (its tag 2's stores before its Field(), each a store's 7
#: values), ``ticks`` (its fade's op_22 wait: e23's 25), ``to`` (a ``field_to`` key) -- and optionally ``z_gt`` (its z
#: term: e23 t2 ip38's f[2] > 1333) and ``walkout`` (``{"to": [x, z], "stop_z": z | None}``: ExitField's walk toward
#: MJPOS's point). H22 (research/o7_design.md 3.3): a door's HEIGHT terms ``y_gt`` / ``y_le`` -- his published y past it /
#: at or under it (154 e8 t2 ip38's ``f[1] < -100``: the balcony branch y > 100, the ground branch y <= 100) -- and the
#: step's ``scenes`` (:data:`SCENE_KEYS`): an object's one-shot scene, tested after the doors each tick he has control.
DOOR_DEFAULTS = {"doors": (), "speed": 60.0, "scenes": ()}
DOOR_KEYS = ("name", "points", "z_gt", "y_gt", "y_le", "stores", "ticks", "to", "walkout")
DOOR_NEEDS = ("name", "points", "stores", "ticks", "to")
#: H22 (research/o7_design.md 3.3): a door step's SCENE -- ``name``; ``any_of`` (a dict of ``x_lt`` / ``x_gt`` / ``z_lt``
#: / ``z_gt``: ANY holding fires -- 159 e16 t1 ip390's B_OROR); ``unless_bit`` (the gEventGlobal bit whose 1 disarms it,
#: read from the modelled array -- ip390's ``Bit[3796] == 0``; None: never disarmed); ``steps`` (its pages, stores and
#: waits, :data:`SCENE_STEP_KINDS` -- H24's WaitWindow among them); ``regrant`` ("in_place", the only form: ip711
#: EnableMove with no Walk).
SCENE_KEYS = ("name", "any_of", "unless_bit", "steps", "regrant")
SCENE_NEEDS = ("name", "any_of", "steps")
SCENE_TESTS = ("x_lt", "x_gt", "z_lt", "z_gt")
SCENE_STEP_KINDS = ("page", "store", "wait", "wait_window")
#: A ``stairs`` step's knobs and defaults (153 e3 t1 stage 6, its side scenes, its back door and stage 17;
#: research/o5_design.md 3.2): ``scenes`` (each ``{"points", "z_gt", "pages"}``: e26 -- its quad AND z > 1333 -- and e27,
#: live in stage 6 alone; ``pages`` page steps); ``back_door`` (``{"points", "stores", "exit_ticks", "to"}``: e28, live
#: while he has control, any stage; ``to`` a ``field_to`` key); ``contour`` (the floor-blind stand-in for the height test:
#: a polygon) or ``height_at`` (a callable: the real mesh's PSX y under (x, z), or None off it); ``level`` (ip859's
#: -450); ``teleport_ticks`` (the loss to CreateObject ip1466: the stage switch, op_1C, Wait(1), the Bit[160] test -- an
#: ESTIMATE, R-STAIRS measures); ``teleport``; ``climb`` (stage 17's scripted walk) at ``climb_speed`` (SetWalkSpeed(37),
#: u a tick); ``regrant_at`` (a side scene's Walk(1105,-78), ip1230).
STAIRS_DEFAULTS = {"scenes": (), "back_door": None, "contour": None, "height_at": None, "level": -450,
                   "teleport_ticks": 3, "teleport": (-1165.0, 856.0),
                   "climb": ((-1419.0, 602.0), (-1602.0, 298.0), (-1631.0, 10.0), (-1631.0, -140.0),
                             (-1416.0, -378.0), (-978.0, -554.0), (-329.0, -624.0)),
                   "climb_speed": 37.0, "regrant_at": (1105.0, -78.0)}
#: H15's ``error_window``: the page 153 e0 t0 lists when Byte[13] arrived 2 or 9 (window 56, ip2304: O3's text), and the
#: store its error branch makes where the ambient branch makes ip119's (153 e0 t0 ip97 ``Byte[13] := 9``; 154's is
#: ip101 -- not modelled per field: a test of it reads the V-class, never the row).
VISIT_ERROR_TEXT = "Error Env Play()  Slot=1"
VISIT_ERROR_STORE = (0, 0, 97, 13, "Byte", 9, -1)


def _visit_steps(steps, k: dict, where: str) -> None:
    """H14's steps checked STRICT before the beat runs any (research/o5_design.md 3.2): a list of dicts, each naming
    exactly one kind of :data:`VISIT_STEP_KEYS` and only that kind's keys; a store of its 7 values; a pair of two
    windows; a ``field`` step's ``to`` -- and a back door's -- a ``field_to`` key; a choice's ``lines`` a non-empty list
    of strings, its ``branch`` steps and a ``stairs`` step's side-scene ``pages`` steps themselves; a ``stairs`` step's
    knobs :data:`STAIRS_DEFAULTS`' and -- unless H15's ``no_contour`` -- a ``contour`` or a ``height_at``; H17's
    ``naming`` a character id (an int >= 0) and its ``name`` a non-empty str; H18's ``door`` read by
    :func:`_door_knobs` (research/o6_design.md 3.3, 3.4); H20's ``place`` and ``grant`` two numbers ``[x, z]`` or three,
    ``[x, z, h]`` (research/o7_design.md 3.1); H24's page ``async`` a bool and ``wait_window`` a window slot, an int >=
    0 (the O7 review's finding: 159 e16 t1's WindowAsync / WaitWindow)."""
    if not isinstance(steps, (list, tuple)):
        raise ValueError(f"{where}: the steps are a list, not {steps!r}")
    for i, step in enumerate(steps):
        at = f"{where}[{i}]"
        if not isinstance(step, dict):
            raise ValueError(f"{at}: a step is a dict, not {step!r}")
        kinds = [kd for kd in VISIT_STEP_KEYS if kd in step]
        if len(kinds) != 1:
            raise ValueError(f"{at}: a step names exactly one of {sorted(VISIT_STEP_KEYS)}, not {sorted(step)}")
        kind = kinds[0]
        extra = sorted(set(step) - {kind, *VISIT_STEP_KEYS[kind]})
        if extra:
            raise ValueError(f"{at}: a {kind} step has no {extra} (it takes {list(VISIT_STEP_KEYS[kind])})")
        xz = step.get(kind) if kind in ("place", "grant") else None
        if kind in ("place", "grant") and not (isinstance(xz, (list, tuple)) and len(xz) in (2, 3) and all(
                isinstance(v, (int, float)) and not isinstance(v, bool) for v in xz)):
            raise ValueError(f"{at}: a {kind} is [x, z], or [x, z, h] with h the PSX y it places him at, not {xz!r}")
        if kind == "store" and (not isinstance(step["store"], (list, tuple)) or len(step["store"]) != 7):
            raise ValueError(f"{at}: a store is [sid, tag, ip, byte, width, value, bit], not {step['store']!r}")
        if kind == "pair" and (not isinstance(step["pair"], (list, tuple)) or len(step["pair"]) != 2):
            raise ValueError(f"{at}: a pair is [[mes, slot], [mes, slot]], not {step['pair']!r}")
        if kind == "field" and str(step["field"]) not in k["field_to"]:
            raise ValueError(f"{at}: field {step['field']!r} is not in field_to {sorted(k['field_to'])}")
        if kind == "choice":
            lines = step.get("lines")
            if not isinstance(lines, (list, tuple)) or not lines or not all(isinstance(x, str) for x in lines):
                raise ValueError(f"{at}: a choice's lines are a non-empty list of strings, not {lines!r}")
            for a, sub in dict(step.get("branch") or {}).items():
                _visit_steps(sub, k, f"{at}.branch[{a}]")
        if kind == "stairs":
            s = step["stairs"]
            if not isinstance(s, dict):
                raise ValueError(f"{at}: the stairs' knobs are a dict, not {s!r}")
            unknown = sorted(set(s) - set(STAIRS_DEFAULTS))
            if unknown:
                raise ValueError(f"{at}: the stairs have no knob {unknown} (they take {sorted(STAIRS_DEFAULTS)})")
            if s.get("contour") is None and s.get("height_at") is None and not k["no_contour"]:
                raise ValueError(f"{at}: the stairs' height test needs a contour or a height_at")
            for n, sc in enumerate(s.get("scenes") or ()):
                _visit_steps(sc.get("pages") or [], k, f"{at}.scenes[{n}]")
            bd = s.get("back_door")
            if bd is not None and str(bd.get("to")) not in k["field_to"]:
                raise ValueError(f"{at}: the back door's to {bd.get('to')!r} is not in field_to {sorted(k['field_to'])}")
        if kind == "naming":
            char = step["naming"]
            if not isinstance(char, int) or isinstance(char, bool) or char < 0:
                raise ValueError(f"{at}: a naming step names a character id, an int >= 0, not {char!r}")
            if "name" in step and (not isinstance(step["name"], str) or not step["name"]):
                raise ValueError(f"{at}: a naming step's name is the default it pre-fills, a non-empty str, not "
                                 f"{step['name']!r}")
        if kind == "page" and not isinstance(step.get("async", False), bool):
            raise ValueError(f"{at}: a page's async is a bool (WindowAsync), not {step['async']!r}")
        if kind == "wait_window":
            slot = step["wait_window"]
            if not isinstance(slot, int) or isinstance(slot, bool) or slot < 0:
                raise ValueError(f"{at}: a wait_window step names a window slot, an int >= 0, not {slot!r}")
        if kind == "door":
            _door_knobs(step["door"], k, at)


def _door_knobs(d, k: dict, at: str) -> None:
    """H18's ``door`` step checked STRICT (research/o6_design.md 3.4): its knobs :data:`DOOR_DEFAULTS`' -- ``speed`` a
    positive number, ``doors`` a non-empty list in entry order -- and each door a dict holding every
    :data:`DOOR_NEEDS` and nothing outside :data:`DOOR_KEYS`: ``points`` a polygon of three points or more, each
    store its 7 values, ``ticks`` an int >= 0, ``to`` a ``field_to`` key, ``z_gt`` a number, ``walkout`` ``{"to":
    [x, z], "stop_z": z | None}``. H22 (research/o7_design.md 3.3): a door's ``y_gt`` and ``y_le`` numbers; the step's
    ``scenes`` a list, each a dict holding every :data:`SCENE_NEEDS` and nothing outside :data:`SCENE_KEYS` -- ``name`` a
    non-empty str, ``any_of`` a non-empty dict of :data:`SCENE_TESTS` to numbers, ``unless_bit`` None or an int >= 0,
    ``steps`` visit steps (:func:`_visit_steps`) of :data:`SCENE_STEP_KINDS` alone, ``regrant`` "in_place". A ValueError
    names the first fault."""
    if not isinstance(d, dict):
        raise ValueError(f"{at}: the door's knobs are a dict, not {d!r}")
    unknown = sorted(set(d) - set(DOOR_DEFAULTS))
    if unknown:
        raise ValueError(f"{at}: the door has no knob {unknown} (it takes {sorted(DOOR_DEFAULTS)})")
    speed = d.get("speed", DOOR_DEFAULTS["speed"])
    if not isinstance(speed, (int, float)) or isinstance(speed, bool) or not speed > 0:
        raise ValueError(f"{at}: the door's walk-out speed is a positive number of u a tick, not {speed!r}")
    doors = d.get("doors")
    if not isinstance(doors, (list, tuple)) or not doors:
        raise ValueError(f"{at}: a door step's doors are a non-empty list, in entry order, not {doors!r}")
    for n, door in enumerate(doors):
        w = f"{at}.doors[{n}]"
        if not isinstance(door, dict):
            raise ValueError(f"{w}: a door is a dict, not {door!r}")
        if [x for x in DOOR_NEEDS if x not in door] or set(door) - set(DOOR_KEYS):
            raise ValueError(f"{w}: a door holds {list(DOOR_NEEDS)} and optionally z_gt, y_gt, y_le and walkout, not "
                             f"{sorted(door)}")
        if not isinstance(door["points"], (list, tuple)) or len(door["points"]) < 3:
            raise ValueError(f"{w}: a door's points are a polygon, [[x, z], ...] of three or more, not "
                             f"{door['points']!r}")
        for s in door["stores"]:
            if not isinstance(s, (list, tuple)) or len(s) != 7:
                raise ValueError(f"{w}: a store is [sid, tag, ip, byte, width, value, bit], not {s!r}")
        if not isinstance(door["ticks"], int) or isinstance(door["ticks"], bool) or door["ticks"] < 0:
            raise ValueError(f"{w}: a door's ticks are an int >= 0 (its fade's wait), not {door['ticks']!r}")
        if str(door["to"]) not in k["field_to"]:
            raise ValueError(f"{w}: the door's to {door['to']!r} is not in field_to {sorted(k['field_to'])}")
        for term in ("z_gt", "y_gt", "y_le"):                     # H22: the height terms beside the z term
            v = door.get(term)
            if v is not None and (not isinstance(v, (int, float)) or isinstance(v, bool)):
                raise ValueError(f"{w}: a door's {term} is a number, not {v!r}")
        wo = door.get("walkout")
        if wo is not None and (not isinstance(wo, dict) or "to" not in wo or set(wo) - {"to", "stop_z"}
                               or not isinstance(wo["to"], (list, tuple)) or len(wo["to"]) != 2):
            raise ValueError(f"{w}: a door's walkout is {{'to': [x, z], 'stop_z': z | None}}, not {wo!r}")
    scenes = d.get("scenes", DOOR_DEFAULTS["scenes"])
    if not isinstance(scenes, (list, tuple)):
        raise ValueError(f"{at}: a door step's scenes are a list, not {scenes!r}")
    for n, sc in enumerate(scenes):                               # H22: an object's one-shot scene
        w = f"{at}.scenes[{n}]"
        if not isinstance(sc, dict) or [x for x in SCENE_NEEDS if x not in sc] or set(sc) - set(SCENE_KEYS):
            raise ValueError(f"{w}: a scene holds {list(SCENE_NEEDS)} and optionally unless_bit and regrant, not "
                             f"{sorted(sc) if isinstance(sc, dict) else sc!r}")
        if not isinstance(sc["name"], str) or not sc["name"]:
            raise ValueError(f"{w}: a scene's name is a non-empty str, not {sc['name']!r}")
        tests = sc["any_of"]
        if not isinstance(tests, dict) or not tests or set(tests) - set(SCENE_TESTS) or not all(
                isinstance(v, (int, float)) and not isinstance(v, bool) for v in tests.values()):
            raise ValueError(f"{w}: a scene's any_of is a non-empty dict of {list(SCENE_TESTS)} to numbers, not "
                             f"{tests!r}")
        bit = sc.get("unless_bit")
        if bit is not None and (not isinstance(bit, int) or isinstance(bit, bool) or bit < 0):
            raise ValueError(f"{w}: a scene's unless_bit is None or a gEventGlobal bit, an int >= 0, not {bit!r}")
        if sc.get("regrant", "in_place") != "in_place":
            raise ValueError(f"{w}: a scene's regrant is 'in_place' (EnableMove where he stands, no Walk), not "
                             f"{sc['regrant']!r}")
        _visit_steps(sc["steps"], k, f"{w}.steps")
        odd = [s for s in sc["steps"] if not any(kd in s for kd in SCENE_STEP_KINDS)]
        if odd:
            raise ValueError(f"{w}: a scene's steps are pages, stores and waits ({list(SCENE_STEP_KINDS)}), not {odd!r}")


class _VisitBeat(_Machine):
    """H14 (research/o5_design.md 3.2): ONE FIELD VISIT, from its arrival to its Field(), played as a STEP LIST per field
    tick, with O4's window model unchanged (:class:`_Win`: the opening drop, the close tween; :class:`_Machine`: the
    per-frame UI Confirm, the per-tick KEYON edge, the publication order). A scene of visit beats plays a route: each
    ends by moving the field (a fresh visit) and finishing, so the next starts in the new field. The steps
    (:data:`VISIT_STEP_KEYS`, checked strict by :func:`_visit_steps`):

      * ``{"store": [sid, tag, ip, byte, width, value, bit]}`` -- a script store (:meth:`FakeGame.script_store`; H13
        decides its row); ``value`` "answer" stores the last choice's answer (153 e3 t1 ip1741's ``SYSVAR[9]``);
      * ``{"wait": ticks}`` -- the script's op_22 / walks, scaled by ``wait_scale``;
      * ``{"place": [x, z]}`` -- a scripted move of the player, control untouched;
      * ``{"page": mes, ...}`` -- WindowSync (or WindowAsync + WaitWindow): listed THIS tick (ETb.NewMesWin), complete
        after its opening; with ``typing_s`` its text types on for that long of the game's clock after the opening -- a
        Confirm then only completes it (Dialog.cs:798-808), the next closes it; the script resumes the tick it is gone.
        H24: ``async`` True is WindowAsync ALONE -- listed this tick, the script goes on at once while it is up (159 e16
        t1's RunAnimation + WaitAnimation pairs and stores under pages 296, 298, 299 and 300);
      * ``{"wait_window": slot}`` -- H24's WaitWindow(slot): the script holds until no window of that slot is listed;
      * ``{"timed": mes, "ticks": t, ...}`` -- a [TIME=t] window: Confirm-inert, closing itself ``t`` ticks after it
        opened (then its tween); the script does not wait;
      * ``{"pair": [[mes, slot], [mes, slot]], "lag", "gate"}`` -- H10's KEYON pair (:meth:`_pair`);
      * ``{"choice": mes, "lines", ...}`` -- ``gap`` ticks after the previous window is GONE, a WindowSync choice GATED as
        the engine gates SelectChoice (:meth:`_choice`, :meth:`ui`, :meth:`publish`); then ``branch[str(answer)]``;
      * ``{"grant": [x, z]}`` -- EnableMove: control, the player at (x, z);
      * ``{"stairs": knobs}`` -- 153's stage 6, its side scenes and back door, the height test and stage 17
        (:meth:`_stairs`, :data:`STAIRS_DEFAULTS`);
      * ``{"naming": char, "name": default}`` -- H17 (research/o6_design.md 3.3): Menu(1, char), the naming screen over
        the field -- ui "NameSetting", no window -- which holds the script until its OK (:meth:`_naming`, :meth:`ui`);
      * ``{"door": knobs}`` -- H18 (research/o6_design.md 3.4): the regions' tag 2 while he has control, ExitField's
        walk-out, the door's stores and its Field() (:meth:`_door`, :data:`DOOR_DEFAULTS`);
      * ``{"field": to}`` -- Field(): the field becomes ``field_to[to]`` (a fresh visit, control off), the beat finishes.

    H17's NAME ON THE PAGE: every window's text has [STNR] rendered as the name the naming screen saved
    (``fake.names``), the default until one is saved (:meth:`open`); its raw keeps the tag, as phrase_raw does.

    H15's faults (research/o5_design.md 3.3), each absent by default: ``store_override`` ``{ip: value}`` (a fork that
    stores another value at a site); ``grant_at`` ``{index: [x, z]}`` (control granted after that visit's leading stores,
    where the bytes grant none -- then the script holds); ``land_real`` ``{to: id}`` (a ``field`` step landing in the
    REAL id: a Field() the chain did not retarget); ``reask`` (a choice asked again once its answer is gone, ``gap`` ticks
    later); ``stray_confirm_at_ready`` (the fake itself answers a choice the first frame it takes answers -- input no
    witness saw); ``cursor_to`` ``{"after_frames": n, "index": i}`` (the game moves the cursor to ``i`` ``n`` frames after
    the first Down/Up that moved it: outside input after the driver's select) or ``{"at_confirm": True, "index": i}``
    (in the frame the answering Confirm goes down, after every published sample); ``confirm_deaf`` (a choice drops its
    first k Confirms once it takes answers); ``gap_ticks`` (every choice's ``gap``); ``no_contour`` (the height test never
    fires); ``side_scene_at`` (the n-th MOVING tick of a stage-6 period -- or a list, one per period: a side scene fires
    wherever he stands, the first scene's pages: a mis-walk's stand-in); ``error_window`` ``{index: value}`` (Byte[13]
    arrived ``value``: the leading stores take the error branch's :data:`VISIT_ERROR_STORE`, and window 56,
    :data:`VISIT_ERROR_TEXT`, waits). ``fake.visit_log`` keeps every step's start.

    O6's faults (H17, H19: research/o6_design.md 3.3, 3.5), each absent by default: ``name_typed`` (the name the naming
    screen's OK saves -- outside input typed into the box: the page witness's V13); ``naming_deaf`` (the screen drops
    its first k Confirms -- 4 or more and accept_name raises: the stuck screen); ``unparsed_frames`` ``{mes: k}`` (that
    window publishes its RAW text, tags included, for its first k frames: the TextParser's ``ParsedText =
    InitialText`` before Parse, TextParser.cs:54-60 -- a state the engine is not expected to publish, kept to test the
    page witness's guard); ``door_misroute`` ``{door name: field_to key}`` (that door's Field() lands there: a
    misrouted fork operand's stand-in)."""

    def __init__(self, fake, knobs):
        k = _machine_knobs(VISIT_DEFAULTS, knobs, "visit")
        if not isinstance(k["steps"], (list, tuple)) or not k["steps"]:
            raise ValueError(f"visit: steps is a non-empty list of steps, not {k['steps']!r}")
        k["field_to"] = {str(t): int(f) for t, f in dict(k["field_to"] or {}).items()}
        k["land_real"] = {str(t): int(f) for t, f in dict(k["land_real"] or {}).items()}
        k["store_override"] = {int(ip): int(v) for ip, v in dict(k["store_override"] or {}).items()}
        k["grant_at"] = {int(n): [float(c) for c in xz] for n, xz in dict(k["grant_at"] or {}).items()}
        k["error_window"] = {int(n): int(v) for n, v in dict(k["error_window"] or {}).items()}
        k["unparsed_frames"] = {int(m): int(n) for m, n in dict(k["unparsed_frames"] or {}).items()}
        k["door_misroute"] = {str(d): str(t) for d, t in dict(k["door_misroute"] or {}).items()}
        astray = sorted(t for t in k["door_misroute"].values() if t not in k["field_to"])
        if astray:
            raise ValueError(f"visit: door_misroute sends a door to {astray}, not in field_to {sorted(k['field_to'])}")
        typed, deaf = k["name_typed"], k["naming_deaf"]
        if typed is not None and (not isinstance(typed, str) or not typed):
            raise ValueError(f"visit: name_typed is the name the OK saves, a non-empty str, or None, not {typed!r}")
        if not isinstance(deaf, int) or isinstance(deaf, bool) or deaf < 0:
            raise ValueError(f"visit: naming_deaf is the Confirms the naming screen drops, an int >= 0, not {deaf!r}")
        cur = k["cursor_to"]
        if cur is not None and not (isinstance(cur, dict) and "index" in cur
                                    and set(cur) <= {"index", "after_frames", "at_confirm"}
                                    and ("after_frames" in cur) != bool(cur.get("at_confirm"))):
            raise ValueError(f"visit: cursor_to is {{'after_frames': n, 'index': i}} or {{'at_confirm': True, "
                             f"'index': i}}, not {cur!r}")
        side = k["side_scene_at"]
        k["side_scene_at"] = [] if side is None else [int(side)] if isinstance(side, int) else [int(n) for n in side]
        _visit_steps(k["steps"], k, "visit")
        super().__init__(fake, k)
        self.field = fake.field_id
        donor = k["donor"]
        fake.donor = None if donor is None or int(donor) == fake.field_id else int(donor)
        self.bodies = [dict(b) for b in k["bodies"]]
        if self.bodies:
            fake.blockers[self.field] = [*fake.blockers.get(self.field, ()), *self.bodies]
        self.answer = None                         # the last choice's answer: a store's "answer"
        self.choice_closed = False                 # a choice of this visit closed: the group '' since (:meth:`publish`)
        self.deaf = int(k["confirm_deaf"])         # H15: Confirms still to drop
        self.move = None                           # H15 cursor_to: the move due, (frame, index)
        self.moved = False                         # ...scheduled once
        self.strayed = False                       # H15 stray_confirm_at_ready: fired once
        self.naming = None                         # H17: the naming screen while it is up (:meth:`_naming`)
        self.script = self._script(fake)

    # -- the UI: the engine's gating of a page's type-out and a choice's answer
    def open(self, fake, slot: int, kind: str, text: str, raw: str, *, unsub: str | None = None,
             mes=None) -> _Win:
        """:meth:`_Machine.open`, every window given the type-out state :meth:`ui` reads -- none (``typing_s`` 0) unless
        its step sets one -- so a window a director queues (:meth:`_Machine.queue_window`) is a plain page here too.
        H17 (research/o6_design.md 3.3): its TEXT has [STNR] rendered as the name the naming screen saved -- the
        default until one is (``fake.names``; DialogBoxSymbols.cs:67-68), resolved as the window's parser first runs --
        its raw keeping the tag; and ``mes`` (the step's) keyed in ``unparsed_frames``: its raw text published for its
        first k frames (:meth:`shown`)."""
        text = text.replace(STNR_TAG, fake.names.get(STNR_CHAR, STNR_NAME))
        w = super().open(fake, slot, kind, text, raw, unsub=unsub)
        w.typing_s, w.typed, w.done_frame, w.done_rt = 0.0, False, None, None
        n = self.k["unparsed_frames"].get(mes)
        w.mes, w.unparsed_until = mes, (fake.frame + int(n) if n else None)
        return w

    def typing(self, fake, w) -> bool:
        """Whether a page's or a choice's text still TYPES: complete, ``typing_s`` > 0, not yet completed by a Confirm,
        and less than ``typing_s`` of the game's clock since its opening ended."""
        return (not w.typed and w.typing_s > 0 and w.done_rt is not None
                and fake.rt - w.done_rt < w.typing_s - 1e-9)

    def shown(self, fake, w) -> str:
        """A window's text as the agent publishes it: whole, but for a page or a choice that types -- its first
        character through the opening, then a share of it as its type-out runs (the raw holds the whole source from the
        first sample: ``phrase_raw``). H17: an UNPARSED window (``unparsed_frames``) publishes its raw text, tags
        included, until its k frames are out (research/o6_design.md 3.3)."""
        if w.unparsed_until is not None and fake.frame < w.unparsed_until:
            return w.raw
        if w.kind not in ("page", "choice") or w.typing_s <= 0 or w.typed:
            return w.text
        if w.done_rt is None:
            return w.text[:1]
        frac = (fake.rt - w.done_rt) / w.typing_s
        return w.text if frac >= 1.0 else w.text[:max(1, int(len(w.text) * frac))]

    def take(self, fake, w) -> None:
        """The choice answered at its cursor (Dialog.Hide: the group '' from this Confirm on, Dialog.cs:629)."""
        w.answer = w.cursor
        fake.answered.append(w.cursor)
        self.choice_closed = True
        self.close(fake, w)

    def ui(self, fake) -> None:
        """The UI's per-frame reads, gated as the engine gates them (research/o5_design.md 3.2): a window's opening ends
        (``done_frame``: AfterShown; a choice's cursor then on its default 0, ETb.cs:100-103); a Confirm going down
        closes a COMPLETE page -- or, while it types, only completes its text (Dialog.cs:803-807); on a complete choice
        Down/Up move the cursor (OnItemSelect, CompleteAnimation, :826-835) and a Confirm answers at it -- but in its
        first ``ready_lag_frames`` it commits SelectChoice and hides nothing (:787-789), and while its prompt types it
        only completes the text. The cursor WRAPS: Dialog.cs:157 links the choice buttons with
        NGUIExtension.SetKeyNevigation (NGUIExtension.cs:17-29: the last button's onDown is the first, the first's onUp
        the last), and UIKeyNavigation.GetDown/GetUp take an active onDown/onUp before anything else
        (UIKeyNavigation.cs:94-95, :108-109) -- a Down on the last line lands on the first (O4's machines and the
        generic beat clamp: theirs, pinned, untouched). In a window's opening nothing is taken (a Confirm there sets
        SelectChoice to the default and closes nothing, :798-801). H15's choice faults act here. H17: while the naming
        screen is up, its keys are the screen's (:meth:`_naming_keys`) and no window takes one."""
        k = self.k
        lag = int(k["ready_lag_frames"])
        cur = k["cursor_to"]
        for w in self.windows:
            if w.kind in ("page", "choice") and w.complete and w.done_frame is None:
                w.done_frame, w.done_rt = fake.frame, fake.rt
                if w.kind == "choice":
                    w.cursor = 0
        ch = next((w for w in self.windows if w.kind == "choice" and w.complete and not w.closing), None)
        if ch is not None:
            if self.move is not None and fake.frame >= self.move[0]:
                ch.cursor, self.move = int(self.move[1]), None          # H15: the game moved it
            if k["stray_confirm_at_ready"] and not self.strayed and fake.frame >= ch.done_frame + lag:
                self.strayed = True
                self.take(fake, ch)                                     # H15: answered by no press of the driver's
                return
        downs = self.downs(fake)
        if self.naming is not None:                                     # H17: the naming screen takes the keys
            self._naming_keys(fake, downs)
            return
        if not downs:
            return
        for w in self.windows:
            if w.closing or not w.complete:
                continue
            if w.kind == "page" and "confirm" in downs:
                if self.typing(fake, w):
                    w.typed = True                                      # the type-out completed; nothing closed
                else:
                    self.close(fake, w)
            elif w.kind == "choice":
                before = w.cursor
                if "down" in downs:                                     # WRAPS, as the engine's navigation does
                    w.cursor = (w.cursor + 1) % len(w.lines)
                if "up" in downs:
                    w.cursor = (w.cursor - 1) % len(w.lines)
                if w.cursor != before and cur is not None and "after_frames" in cur and not self.moved:
                    self.moved = True
                    self.move = (fake.frame + int(cur["after_frames"]), int(cur["index"]))
                if "confirm" not in downs or fake.frame < w.done_frame + lag:
                    continue                                            # the ready-lag frame: committed, nothing hidden
                if self.typing(fake, w):
                    w.typed = True
                    continue
                if self.deaf > 0:
                    self.deaf -= 1                                      # H15: dropped
                    continue
                if cur is not None and cur.get("at_confirm"):
                    w.cursor = int(cur["index"])                        # H15: moved in the Confirm's own frame
                self.take(fake, w)

    def publish(self, fake) -> None:
        """The visit's windows as the agent publishes them -- :meth:`_Machine.publish`'s shape, with a typing window's
        text as it stands (:meth:`shown`) and, once a choice of the visit has closed, the menu group '' where it reads
        None: the engine's DisableAllGroup at the answering Confirm (Dialog.cs:629, ButtonGroupState.cs:291) leaves it ''
        until another group activates. A choice in its opening publishes ``selected`` as its ``stale`` cursor (the
        pooled window's last) and the group ''; complete, the group ``Dialog.Choice`` (its ready-lag frames included)."""
        listed = [w for w in self.windows if not w.gone]
        fake.texts = [self.shown(fake, w) for w in listed]
        fake.raw_texts = [w.raw for w in listed]
        ch = next((w for w in listed if w.kind == "choice"), None)
        if ch is None:
            fake.choice = None
            fake.menu = {"selected": None, "hovered": None, "label": None, "group": "" if self.choice_closed else None}
            return
        fake.choice = {"selected": ch.cursor, "count": len(ch.lines), "active": list(range(len(ch.lines))),
                       "disabled": [], "options": [ch.header, *ch.lines]}
        ready = ch.complete and not ch.closing
        button = f"Choice#{ch.cursor}" if ready else None
        fake.menu = {"selected": button, "hovered": None, "label": None, "group": "Dialog.Choice" if ready else "",
                     "button": button}

    def on_tick(self, fake) -> None:
        """A field tick: every [TIME=t] window due closes itself (:meth:`_timed`), then the script runs."""
        for w in self.windows:
            if w.kind == "timed" and not w.closing and self.tick >= w.close_tick:
                self.close(fake, w)
        super().on_tick(fake)

    def end(self, fake) -> None:
        """The visit's bodies are taken down with it, and its donor: the field's own id until a visit says otherwise."""
        bodies = fake.blockers.get(self.field)
        if bodies is not None and self.bodies:
            fake.blockers[self.field] = [b for b in bodies if not any(b is o for o in self.bodies)]
        fake.donor = None

    # -- the script
    def _log(self, fake, at: str, kind: str, **kv) -> None:
        fake.visit_log.append({"index": self.k["index"], "field": fake.field_id, "at": at, "kind": kind,
                               "tick": self.tick, "frame": fake.frame, **kv})

    @staticmethod
    def _ticks(n):
        for _ in range(max(0, int(n))):
            yield

    def _script(self, fake):
        """The visit: its leading stores (Main_Init's prologue), then -- H15 -- ``error_window``'s error branch (the
        stores with the error store for ip119's, window 56, nothing after) or ``grant_at``'s control (then nothing
        after), else every other step in turn (:meth:`_run`)."""
        k = self.k
        steps = list(k["steps"])
        lead = next((i for i, s in enumerate(steps) if "store" not in s), len(steps))
        err = k["error_window"].get(k["index"])
        if err is not None:
            fake.story_bytes[13] = err & 0xFF            # the value it arrived with: no store, no row
            for i, step in enumerate(steps[:lead]):
                self._log(fake, str(i), "store")
                s = step["store"]
                self._store(fake, VISIT_ERROR_STORE if (int(s[3]), str(s[4])) == (13, "Byte") else s)
            self._log(fake, "error", "page")
            yield from self._page(fake, {"page": 56, "slot": 1, "text": VISIT_ERROR_TEXT, "raw": VISIT_ERROR_TEXT})
            return
        yield from self._run(fake, steps[:lead], "")
        grant = k["grant_at"].get(k["index"])
        if grant is not None:
            self._log(fake, "grant_at", "grant")
            self._grant(fake, grant)
            while True:
                yield
        yield from self._run(fake, steps[lead:], "", base=lead)

    def _run(self, fake, steps, path: str, base: int = 0):
        """Each step in turn, logged as it starts (``fake.visit_log``); a ``field`` step -- or the back door, or H18's
        door -- ends the beat, and nothing after it runs."""
        for i, step in enumerate(steps, base):
            if self.done:
                return
            kind = next(kd for kd in VISIT_STEP_KEYS if kd in step)
            at = f"{path}{i}"
            self._log(fake, at, kind)
            if kind == "store":
                self._store(fake, step["store"])
            elif kind == "wait":
                yield from self._ticks(round(float(step["wait"]) * float(self.k["wait_scale"])))
            elif kind == "place":
                self._place(fake, step["place"])
            elif kind == "grant":
                self._grant(fake, step["grant"])
            elif kind == "page":
                yield from self._page(fake, step)
            elif kind == "timed":
                self._timed(fake, step)
            elif kind == "pair":
                yield from self._pair(fake, step)
            elif kind == "choice":
                yield from self._choice(fake, step, at)
            elif kind == "stairs":
                yield from self._stairs(fake, step["stairs"], at)
            elif kind == "naming":
                yield from self._naming(fake, step)
            elif kind == "door":
                yield from self._door(fake, step["door"], at)
            elif kind == "wait_window":
                yield from self._wait_window(int(step["wait_window"]))
            else:
                self._field(fake, str(step["field"]))

    def _store(self, fake, args) -> None:
        """A script store (:meth:`FakeGame.script_store`): ``value`` "answer" is the last choice's answer; H15's
        ``store_override`` replaces the value stored at an ip."""
        sid, tag, ip, byte, width, value, bit = args
        if value == "answer":
            value = self.answer
        value = self.k["store_override"].get(int(ip), value)
        fake.script_store(int(sid), int(tag), int(ip), int(byte), str(width), int(value), bit=int(bit))

    def _place(self, fake, xz) -> None:
        """A scripted move: the player published where it puts him (no coast carries a press on from there). H20
        (research/o7_design.md 3.1): ``[x, z, h]`` -- ``h`` the PSX y operand of the bytes' MoveInstantXZY -- places his
        height too (:meth:`FakeGame.place_height`); ``[x, z]`` leaves it as it was."""
        fake.player[0], fake.player[2] = float(xz[0]), float(xz[1])
        if len(xz) == 3:
            fake.place_height(float(xz[0]), float(xz[1]), float(xz[2]))
        fake._coast = None

    def _grant(self, fake, xz) -> None:
        """EnableMove (153 e3 t1 ip785, after WaitWindow(1) ip752 and Map.Bit[158] := 1 ip755): control, him at (x, z)."""
        self._place(fake, xz)
        fake.control = True

    def _open_mes(self, fake, step: dict, kind: str):
        """The window of a page / timed step as the agent publishes it -- ``text`` (default ``mes N``) and its ``raw``
        (default ``[STRT=0,0]`` + the text) -- with the type-out state :meth:`typing` reads; its mes (the step's) is
        what H17's ``unparsed_frames`` keys."""
        text = str(step.get("text", f"mes {step[kind]}"))
        w = self.open(fake, int(step.get("slot", 0)), kind, text, str(step.get("raw", f"[STRT=0,0]{text}")),
                      mes=step[kind])
        w.typing_s, w.typed, w.done_frame, w.done_rt = float(step.get("typing_s") or 0.0), False, None, None
        return w

    def _page(self, fake, step: dict):
        w = self._open_mes(fake, step, "page")
        if step.get("async"):                        # H24: WindowAsync -- listed this tick, the script goes on at once
            return
        while not w.gone:
            yield

    def _wait_window(self, slot: int):
        """H24 (the O7 review's finding): WaitWindow(``slot``) -- the script holds until no window of that slot is
        listed (159 e16 t1 ip534, ip558, ip577, ip669 after its WindowAsync pages), the tick it is gone; none up: it goes
        on at once."""
        while any(w.slot == slot and not w.gone for w in self.windows):
            yield

    def _timed(self, fake, step: dict) -> None:
        """A [TIME=t] [NFOC] window (153's 137, 140): Confirm-inert -- kind "timed": the UI takes Confirm on a page and
        a choice alone -- closing itself ``ticks`` after it opened (:meth:`on_tick`); the script goes on at once."""
        w = self._open_mes(fake, step, "timed")
        w.close_tick = self.tick + int(step["ticks"])

    def _pair(self, fake, step: dict):
        """H10's KEYON pair (153's 134/135 and 139/138, 154's three, 153@316's two): a, then b ``lag`` ticks later, both
        [INCS][TIME=-1] (kind "keyon": no UI Confirm pages them); from ``gate`` ticks after b each tick reads ``keyon &
        (Confirm | Special)`` -- an edge before the gate is consumed by its tick and lost -- and the first such EDGE
        closes both (the KEYON check, e.g. 153 e3 t1 ip2336); the script resumes once both are gone. Each window's mes
        is what H17's ``unparsed_frames`` keys."""
        (ma, sa), (mb, sb) = step["pair"]
        texts = list(step.get("texts") or (f"mes {ma}", f"mes {mb}"))
        raws = list(step.get("raws") or [f"[STRT=0,0]{t}[INCS][TIME=-1]" for t in texts])
        a = self.open(fake, int(sa), "keyon", texts[0], raws[0], mes=ma)
        yield from self._ticks(int(step.get("lag", 15)))
        b = self.open(fake, int(sb), "keyon", texts[1], raws[1], mes=mb)
        yield from self._ticks(int(step.get("gate", 40)))
        while not self.keyon & KEYON_PAIR_BITS:
            yield
        self.close(fake, a)
        self.close(fake, b)
        while not (a.gone and b.gone):
            yield

    def _choice(self, fake, step: dict, at: str):
        """A WindowSync choice ``gap`` ticks after the previous window is GONE -- the script resumed the tick it went:
        e31's WaitAnimation rest, e2's stage tick and e3's open (research/o5_design.md 0.2 #14); H15's ``gap_ticks``
        overrides it -- its text the header and its lines, ``selected`` its ``stale`` cursor until it is complete
        (:meth:`ui`, :meth:`publish`). The script resumes the tick it is gone, its answer kept for a store's "answer";
        then ``branch[str(answer)]``'s steps. H15's ``reask``: once gone, the same choice is asked again, ``gap`` ticks
        later, before the branch."""
        k = self.k
        gap = int(k["gap_ticks"] if k["gap_ticks"] is not None else step.get("gap", 2))
        header, lines = str(step.get("header", "")), [str(x) for x in step["lines"]]
        text = "\n".join([header, *lines])
        for _ask in range(2 if k["reask"] else 1):
            yield from self._ticks(gap)
            w = self.open(fake, int(step.get("slot", 0)), "choice", text, str(step.get("raw", f"[STRT=0,0]{text}")))
            w.typing_s, w.typed, w.done_frame, w.done_rt = float(step.get("typing_s") or 0.0), False, None, None
            w.header, w.lines, w.stale = header, lines, int(step.get("stale", 0))
            w.cursor = w.stale
            while not w.gone:
                yield
            self.answer = w.answer
        yield from self._run(fake, (step.get("branch") or {}).get(str(self.answer), ()), f"{at}.{self.answer}.")

    @staticmethod
    def _contour(s: dict, x: float, z: float) -> bool:
        """THE HEIGHT TEST (153 e3 t1 ip859, ``obj(uid=255).f[1] > -450`` failing): his height on the real mesh at or
        below ``level`` (PSX y: up is negative), or -- floor-blind -- his centre inside ``contour``."""
        if s["height_at"] is not None:
            h = s["height_at"](x, z)
            return h is not None and h <= float(s["level"])
        return _in_poly(x, z, s["contour"])

    @staticmethod
    def _height(fake, s: dict) -> None:
        """With ``height_at``: the published y is minus his height there (f[1] is -pos[1], EBin.cs:1785-1793)."""
        if s["height_at"] is not None:
            h = s["height_at"](fake.player[0], fake.player[2])
            if h is not None:
                fake.player[1] = -float(h)

    def _stairs(self, fake, knobs: dict, at: str):
        """153 e3 t1 STAGE 6 and its neighbours (research/o5_design.md 3.2), per field tick while he has control: (1)
        the regions' tag 2 tests in entry order -- each side scene (e26: its quad AND z > ``z_gt``; e27: its quad), live
        in stage 6 alone: the first hit takes control (DisableMove ip88 / ip68), lists its pages (rule 7's), places him
        at ``regrant_at`` (Walk(1105,-78) ip1230) and grants control again (ip1266): stage 6 again; then the back door
        (e28, its quad, live whenever he has control): control off, its stores (e28 t2 ip38, ip227), and ``exit_ticks``
        later its Field() -- the beat ends there; (2) THE HEIGHT TEST (:meth:`_contour`): the first tick it holds takes
        control (ip874-915), ``teleport_ticks`` later CreateObject puts him at ``teleport`` (ip1466) and stage 17 walks
        him along ``climb`` at ``climb_speed`` u a tick; then the next step. H15: ``no_contour`` -- the test never fires;
        ``side_scene_at`` -- at the n-th MOVING tick of a stage-6 period (a tick he stands somewhere new: the walk's, not
        the settle's before it) a side scene fires wherever he stands. ``fake.visit_log`` rows: "scene", "back_door",
        "lost" (each with his x, z)."""
        from ff9mapkit.content import doorface
        s = {**STAIRS_DEFAULTS, **knobs}
        fires, period, moving = self.k["side_scene_at"], 0, 0
        last = (fake.player[0], fake.player[2])
        while True:
            x, z = fake.player[0], fake.player[2]
            self._height(fake, s)
            if fake.control:
                if (x, z) != last:
                    moving += 1
                last = (x, z)
                scene = next((sc for sc in s["scenes"] if doorface.region_contains(x, z, sc["points"])
                              and z > float(sc.get("z_gt", float("-inf")))), None)
                if scene is None and period < len(fires) and moving == fires[period] and s["scenes"]:
                    scene = s["scenes"][0]
                if scene is not None:
                    fake.control, fake._coast = False, None
                    self._log(fake, f"{at}.s", "scene", x=x, z=z)
                    yield from self._run(fake, scene.get("pages") or (), f"{at}.s.")
                    self._grant(fake, s["regrant_at"])
                    period, moving, last = period + 1, 0, (fake.player[0], fake.player[2])
                    yield
                    continue
                bd = s["back_door"]
                if bd is not None and doorface.region_contains(x, z, bd["points"]):
                    fake.control, fake._coast = False, None
                    self._log(fake, f"{at}.d", "back_door", x=x, z=z)
                    for args in bd.get("stores") or ():
                        self._store(fake, args)
                    yield from self._ticks(int(bd.get("exit_ticks", 0)))
                    self._field(fake, str(bd["to"]))
                    return
                if not self.k["no_contour"] and self._contour(s, x, z):
                    fake.control, fake._coast = False, None
                    self._log(fake, f"{at}.l", "lost", x=x, z=z)
                    yield from self._ticks(int(s["teleport_ticks"]))
                    self._place(fake, s["teleport"])
                    self._height(fake, s)
                    speed = float(s["climb_speed"])
                    for tx, tz in s["climb"]:
                        tx, tz = float(tx), float(tz)
                        while (fake.player[0], fake.player[2]) != (tx, tz):
                            yield
                            px, pz = fake.player[0], fake.player[2]
                            d = math.hypot(tx - px, tz - pz)
                            if d <= speed:
                                fake.player[0], fake.player[2] = tx, tz
                            else:
                                fake.player[0], fake.player[2] = px + (tx - px) / d * speed, pz + (tz - pz) / d * speed
                            self._height(fake, s)
                    yield
                    return
            yield

    def _naming(self, fake, step: dict):
        """H17 (research/o6_design.md 3.3): Menu(1, char) -- EventService.StartMenu opens NameSettingUI over the field
        (DoEventCode.cs:2317-2341): ui "NameSetting", no window listed, the box focused on the pre-filled default
        (CharacterDefaultName, NameSettingUI.cs:137-151; the step's ``name``). The script stands still while it is up --
        :meth:`_Machine.frame` runs a tick's script only on FieldHUD ("a menu up holds the field"), the engine's Menu
        blocking the event code -- and :meth:`ui` takes the screen's keys (:meth:`_naming_keys`); the script resumes the
        tick the screen closes."""
        fake.ui_state = "NameSetting"
        self.naming = {"char": int(step["naming"]), "name": step.get("name"), "focus": True,
                       "deaf": int(self.k["naming_deaf"])}
        yield
        self.naming = None

    def _naming_keys(self, fake, downs: set) -> None:
        """H17: NameSettingUI's keys (NameSettingUI.cs:72-83, :107, :173), as the scene beat's naming rule reads them: a
        Confirm going down while the box is focused takes the focus off it; the next is OK -- the name saved
        (``name_typed``, else the pre-filled default) into ``fake.named`` / ``fake.names``, the field HUD back (the
        script resumes in this frame's tick); a Cancel puts the focus back on the box. ``naming_deaf``: the screen drops
        its first k Confirms."""
        n = self.naming
        if "confirm" in downs:
            if n["deaf"] > 0:
                n["deaf"] -= 1                                          # H17: dropped
            elif n["focus"]:
                n["focus"] = False
            else:
                typed = self.k["name_typed"]
                name = typed if typed is not None else n["name"]
                fake.named.append(n["char"])
                if name is not None:
                    fake.names[n["char"]] = name
                fake.ui_state = "FieldHUD"
                self.naming = None
        elif "cancel" in downs:
            n["focus"] = True

    def _door(self, fake, knobs: dict, at: str):
        """H18 (research/o6_design.md 3.4): THE REGIONS' TAG 2, every field tick he has control, in ENTRY order (the
        engine runs region objects by entry: e23, e24, e25) -- each door's polygon (doorface.region_contains: IsInQuad)
        and, with ``z_gt``, his z past it (153 e23 t2 ip38's f[2] > 1333; its f[1] > -100 ground half is the
        floor-blind fake's ground). The first hit FIRES: control off (ExitField ip59) and a visit_log row "fire" (the
        door's name, where he stood); then ``ticks`` ticks (e23: 25 -- ip153's op_22(25); ip95's op_22(1) is skipped) of
        ExitField's WALK-OUT -- with ``walkout``, toward its ``to`` at ``speed`` u a tick (MOVJ at his last controlled
        frame's speed, DoEventCode.cs:860-869, EventEngine.MoveToward.cs:15-30), held at ``to`` or where his z passes
        ``stop_z`` (pathing's hold a radius short of the floor's end: 0.2 #6); without it he stands -- then, the exit
        gate set or absent (``fake.exit_gate``, H16: he stands meanwhile), the door's ``stores`` and its Field() in the
        same tick (ip203, then ip211). H19's ``door_misroute`` sends that Field() to another ``field_to`` key, and
        ``land_real`` applies to it (:meth:`_field`).

        H22 (research/o7_design.md 3.3): a door's HEIGHT terms -- ``y_gt`` / ``y_le``, his published y past it / at or
        under it (154 e8 t2 ip38's ``f[1] < -100``: one polygon, two doors in entry order, the balcony's and the
        ground's) -- beside ``z_gt``; and the step's SCENES, tested after the doors each tick he has control (159's
        regions e10-e12 precede Steiner's e16, and the engine runs objects by entry): an ARMED scene -- its ``unless_bit``
        clear in the modelled gEventGlobal -- whose ``any_of`` holds (any one: ip390's B_OROR) FIRES: control off (ip445
        DisableMove), a visit_log row "scene" (its name, where he stood), its steps -- pages, stores, waits -- then
        control back where he stands (``regrant`` "in_place": ip711 EnableMove, no Walk), and the doors' loop goes on. A
        scene whose own steps store its ``unless_bit`` (ip672) cannot fire again."""
        from ff9mapkit.content import doorface
        s = {**DOOR_DEFAULTS, **knobs}
        while True:
            if fake.control:
                x, z, y = fake.player[0], fake.player[2], fake.player[1]
                door = next((d for d in s["doors"] if doorface.region_contains(x, z, d["points"])
                             and (d.get("z_gt") is None or z > float(d["z_gt"]))
                             and (d.get("y_gt") is None or y > float(d["y_gt"]))
                             and (d.get("y_le") is None or y <= float(d["y_le"]))), None)
                if door is not None:
                    break
                scene = next((sc for sc in s["scenes"] if self._scene_fires(fake, sc, x, z)), None)
                if scene is not None:                            # H22: an object's scene takes control here
                    fake.control, fake._coast = False, None
                    self._log(fake, f"{at}.s", "scene", name=scene["name"], x=x, z=z)
                    yield from self._run(fake, scene["steps"], f"{at}.s.")
                    if self.done:
                        return
                    fake.control, fake._coast = True, None      # ip711 EnableMove: where he stands, no Walk
                    yield
                    continue
            yield
        fake.control, fake._coast = False, None
        self._log(fake, f"{at}.{door['name']}", "fire", name=door["name"], x=x, z=z)
        wo = door.get("walkout")
        walk = None
        if wo is not None:
            tx, tz = (float(v) for v in wo["to"])
            stop = None if wo.get("stop_z") is None else float(wo["stop_z"])
            way = 1.0 if tz >= z else -1.0
            walk = {"to": (tx, tz), "stop_z": stop, "way": way, "done": stop is not None and (z - stop) * way >= 0}
        for _ in range(int(door["ticks"])):
            yield
            if walk is not None:
                self._walk_out(fake, walk, float(s["speed"]))
        while not fake._exit_open():
            yield
        for args in door["stores"]:
            self._store(fake, args)
        self._field(fake, self.k["door_misroute"].get(str(door["name"]), str(door["to"])))

    @staticmethod
    def _scene_fires(fake, sc: dict, x: float, z: float) -> bool:
        """H22 (research/o7_design.md 3.3): whether a door step's scene fires with him standing at (x, z) -- ARMED (no
        ``unless_bit``, or that gEventGlobal bit clear in the modelled array: ip390's ``Bit[3796] == 0``) and ANY of its
        ``any_of`` tests holding (ip390's B_OROR: x < -1600 || x > 1600 || z < 800)."""
        bit = sc.get("unless_bit")
        if bit is not None and (fake.story_bytes[bit >> 3] >> (bit & 7)) & 1:
            return False
        tests = {"x_lt": lambda v: x < v, "x_gt": lambda v: x > v, "z_lt": lambda v: z < v, "z_gt": lambda v: z > v}
        return any(tests[key](float(v)) for key, v in sc["any_of"].items())

    @staticmethod
    def _walk_out(fake, w: dict, step: float) -> None:
        """H18's walk-out, one field tick: ``step`` u toward ``to``, held there or where his z passes ``stop_z``."""
        if w["done"]:
            return
        x, z = fake.player[0], fake.player[2]
        tx, tz = w["to"]
        d = math.hypot(tx - x, tz - z)
        nx, nz = (tx, tz) if d <= step else (x + (tx - x) / d * step, z + (tz - z) / d * step)
        w["done"] = d <= step
        stop = w["stop_z"]
        if stop is not None and (nz - stop) * w["way"] >= 0:
            t = (stop - z) / (nz - z) if nz != z else 1.0
            nx, nz, w["done"] = x + (nx - x) * t, stop, True
        fake.player[0], fake.player[2] = nx, nz

    def _field(self, fake, to: str) -> None:
        """Field() (153 e3 t1 ip3158, 154 e2 t1 ip1528, 153 e18 t1 ip1085; e28's ip235): the field becomes ``field_to[to]``
        -- H15's ``land_real``: the REAL id -- a fresh visit with control off (the engine zeroes it at a field's start)
        and no window; the beat finishes, and the scene's next beat starts in the new field."""
        fid = self.k["land_real"].get(to, self.k["field_to"][to])
        self.windows = []
        fake.field_id = int(fid)
        fake.player = [0.0, 0.0, 0.0]
        fake.control, fake._coast = False, None
        fake._visit += 1
        fake._in_trigger.clear()
        self.finish(fake)


def _control(name: str) -> str:
    """A ``press`` / ``hold`` / ``release`` button as the agent keys it (HarnessAgent.ParseControl): the direction
    aliases ``north`` / ``south`` / ``west`` / ``east`` ARE ``up`` / ``down`` / ``left`` / ``right`` -- one Control,
    one held key: a ``hold north`` walks him up, and a ``turn`` refuses it as the Up it is. The other buttons keep the
    name they were sent as (nothing in the fake tells their aliases apart)."""
    return DIRECTIONS.get(str(name).lower(), name)


def _turn_directions(arg: str) -> list:
    """``up``, ``up+right``, ... as the agent parses a ``turn``'s directions (HarnessAgent.ParseTurnDirections over
    ParseControl): ``+``-joined names or aliases, directions only, each to its Control name -- and its refusals in its
    words."""
    if not arg:
        raise RuntimeError("needs a direction (up|down|left|right, '+'-joined)")
    out = []
    for part in arg.split("+"):
        name = part.lower()
        if name not in BUTTONS:
            raise RuntimeError(f"unknown button '{part}'")
        if name not in DIRECTIONS:
            raise RuntimeError(f"'{part}' is not a direction (up|down|left|right, '+'-joined)")
        out.append(DIRECTIONS[name])
    return out


def _fmt(v) -> str | None:
    """A float as the agent's Fmt writes it: C#'s ``"0.###"`` -- at most three decimals, no trailing zeros -- or None
    for a missing one."""
    if v is None:
        return None
    s = f"{float(v):.3f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def _in_poly(x: float, z: float, poly) -> bool:
    """(x, z) inside polygon ``poly`` ([[x, z], ...]), even-odd rule -- the stand-in's IsInQuad."""
    inside = False
    n = len(poly)
    for i in range(n):
        ax, az = poly[i]
        bx, bz = poly[(i + 1) % n]
        if (az > z) != (bz > z) and x < ax + (z - az) * (bx - ax) / (bz - az):
            inside = not inside
    return inside


def _stamp(path: Path, mtime: float | None) -> None:
    """Set ``path``'s modified time to ``mtime`` (epoch seconds) -- the fake's VIRTUAL write time, when it publishes
    "mtime" -- or leave the real one (None). A stamp that cannot land costs one sample's time, never the publish."""
    if mtime is None:
        return
    try:
        ns = int(round(mtime * 1e9))
        os.utime(path, ns=(ns, ns))
    except OSError:
        pass


def _publish_atomic(path: Path, text: str, attempts: int = 6, *, mtime: float | None = None) -> None:
    """Replace ``path`` atomically, retrying the Windows sharing violation.

    ``os.replace`` fails with ERROR_ACCESS_DENIED whenever the reader happens to have the target
    open at that instant -- a real collision at a 60 Hz write against a 30 Hz poll, not a theoretical
    one. Retry briefly, then fall back to a direct write: the reader retries parse failures, so a
    torn read costs one poll, whereas a failed publish costs the whole run.

    ``mtime`` stamps the file's modified time (:func:`_stamp`) BEFORE the rename, which keeps it -- so no reader ever
    stats the new document with the wrong time. (The stamp changes only WHICH time the file carries; the
    read-body-then-stat race of a driver against the next rewrite is still there, as in the game.)
    """
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    _stamp(tmp, mtime)
    for attempt in range(attempts):
        try:
            tmp.replace(path)
            return
        except PermissionError:
            time.sleep(0.002 * (attempt + 1))
    path.write_text(text, encoding="utf-8")
    _stamp(path, mtime)
    try:
        tmp.unlink()
    except OSError:
        pass


def _publish_in_place(path: Path, text: str, *, stall: float, began: threading.Event,
                      stop: threading.Event, mtime: float | None = None) -> None:
    """``HarnessAgent.WriteAtomic`` as deployed: truncate in place, then write -- gap held open.

    Python's ``open(..., "w")`` is CREATE_ALWAYS with read+write sharing, like the agent's
    ``FileMode.Create`` + ``FileShare.Read``: a reader is never locked out, it reads an empty file.
    """
    try:
        with open(path, "w", encoding="utf-8") as fh:
            began.set()
            stop.wait(stall)
            fh.write(text)
        _stamp(path, mtime)
    finally:
        began.clear()


def _chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
