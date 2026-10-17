"""R3 GROUP 2, s138-s141 -- THE GUEST'S OWN FIELD MODEL (memoria-patches s138-s141), the solo bench, run unattended.

THE GOAL (the owner's words): "the guest to actually show which character they're puppeting (or a moogle if 1-person
party)". Today the guest's own field body is always Zidane (model 98); the host's ghost of the guest already wears a party
member (NetSyncVisitor.ResolveDress). The four patches build it in order (studies/battle-coop/R3-DESIGN.md 3.4, 6.12 as
amended by R3-FIELD-MODEL-AUDIT.md -- the audit OVERRIDES the design where they differ): s138 the INSTRUMENT (keys only),
s139 the host rule and wire section 8, s140 the guest dresses itself, s141 the polish.

ONE FILE, ONE LEG PER PATCH. Each leg registers (:data:`LEGS`) its catalog, its steps per PHASE, the fields it needs
registered (`pre`) and read by the oracle (`oracle`, plus an `oracle_extra` hook for a leg's own offline read -- s141's MCF
light), and its calibration: `old` -- its reds on an engine BEFORE its patch, by the stage the probe finds -- and `lever`
-- its reds under each of its own calibration levers, by mode; each a (reds, maybe) pair. The run walks the shared phases in
order and calls every selected leg's step in each:
    setup   INI (Memoria.ini, READ-ONLY) -> OR (the offline oracle) -> S0 (newgame, warp the stock field at entrance 0,
            encounters off, the forced selftest role) -> P0 (which instrument this engine publishes) -> PRE (the fields the
            selected legs need, registered)
    stock   field 250 BEFORE the party seed      (s139's G0 / G3a, which need an empty slot, join here)
    seed    warp through COOPPARTY (30604: [party] add = vivi, garnet, steiner) to 30801
    seeded  the seeded party, on 30801            (s139's G1-G7 join here)
    bench   field 30801's actors                  (s140's bench field 30606 legs N / T / X follow the same shape)
    close   the verdicts that need every field read
The file has leg I (s138) and leg G (s139: Session.NETSYNC_DRESS_SUBVERBS `selfdress`; its `old` row at stages 137 / 138
is every G check -- the verb refused before the step, `mode` / `codec` / `rig_idle_frames` absent --; its `lever` row
`rule-s138` is G_LEVER_REDS). s140 adds legs S/W/X/N/T (pre 30602 / 30606), s141 leg F. COOP_DRESS_LEGS=I,G picks legs
(default: every leg this file has). THE RIG SPACE is battlewire.RIG_NAMES: -1 none, 0-7 the CharacterId rows, 8 the moogle
(rig 8 is NOT CharacterId 8, Cinna) -- decoded by name, never compared with a CharacterId at 8.

LEG I (s138) -- THE DRESS INSTRUMENT. Harness keys only, no behaviour on any role (R3-FIELD-MODEL-AUDIT.md 2.1 and its
3.1 key design). Three homes: `player.*` OUTSIDE netsync, right after `control` (model, anim, geo, anim_geo, eye, uid, sid,
body, clip, clip_playing, frame_n, anim_frame, meshflags -- the s90 THREE CASES: absent = an older engine, null = no
controlled actor, else the raw value); `objects[].model` after `sid`; `netsync.dress` -- netsync's LAST key, after
`battle` -- `ghost{model, geo, clip, rig, playing, body}` (what the peer's ghost WEARS here) then `party[4]` (raw
FF9.party.member[i].Index, -1 empty, -2 unreadable -- never NetSyncParty.Slots, where the selftest mirror seats its
"BENCH" impostor). `body` is the texture stem of the actor root's OWN mesh0 (HarnessAgent.BodyOf; never the first renderer
depth-first, which on Zidane is the hidden battle_model0 and on every other rig the bone subtree -- a prop attached under a
bone). Later legs judge the dress on VALUES; leg I proves the instrument reads a stock Zidane right, against an oracle it
does not compute.

THE ORACLE (S138-OR) is read OFFLINE, before anything is launched, through the kit's own readers -- never the engine's own
published answer (s137 lesson: an offline oracle read from the install beats reading back the engine's answer). It is PER
FIELD: a field that reads clean is kept whatever else fails, and S138-OR is red whenever anything did (naming it):
  * each field's `.eb` -- the stock field's from the highest-priority mod folder that overrides it, else the install's
    p0data (ff9mapkit.extract.extract_event_script); the bench field's from the highest-priority mod folder that ships it
    (Memoria.ini [Mod] FolderNames order), language "us" -- parsed with ff9mapkit.eb: the CONTROLLED entry is the one whose
    Init runs DefinePlayerCharacter (0x2C) and that Main_Init's InitObject (0x09) inits (the LAST such entry: control
    binds to the last DefinePlayerCharacter); its sid is the entry index, its uid InitObject's second argument (0 = the
    sid); its body is its Init's first SetModel (0x2F: model, eye byte) and its loco ids SetStand/Walk/Run/Inactive
    Animation (0x33 / 0x34 / 0x35 / 0x52, playerswap.ANIM_OPS); the other InitObject'd entries' SetModel ids are the NPCs.
    Field 250 (HW test2_67): entry 10, SetModel(98, 93), 200 / 25 / 38, inactive 57. Bench 30801 (EVT_TEST30801): entry
    1, SetModel(98, 93), the same loco ids; entries 2-3 SetModel(217, 100) (GEO_NPC_F0_CSO).
  * each model's GEO name and texture stems off the install's p0data (ff9mapkit.models.extract.read_model: ZDN 98_0 /
    98_1 -> "98", CSO 217_0 / 217_1) and the kit's copy of the open-source GEO table; the clip NAMES off the kit's copy of
    the open-source AnimationDB (200 -> ANH_MAIN_F0_ZDN_IDLE).
  * EVERY stacked mod folder's DictionaryPatch.txt, for a `3DModel` / `3DModelAnimation` line touching a field's model or
    loco ids: stock Memoria remaps FF9BattleDB.GEO / AnimationDB from them at launch (DataPatchers), which the kit's tables
    do not -- such a field's oracle is DROPPED and named, so a remap can never masquerade as an engine bug.
  * the seed's party from studies/battle-coop/bench/coopparty.field.toml (`[party] add`, resolved by the kit's own
    content.party, CharacterOldIndex -> CharacterId) on top of the New-Game base (Zidane alone in slot 0): [0, 1, 2, 3].
  * THE INSTALL STAYS READ-ONLY: a stock field's `.eb` read goes through the kit's events-bundle cache, which the kit
    WRITES into StreamingAssets on a miss (KIT_CACHE_FILES). When it is missing the bench does not create it: that field's
    oracle reads "not reached: the kit cache is missing (run any ff9mapkit read once, by hand)".

PRECONDITIONS -- THE OPERATOR'S JOB (the bench never edits Memoria.ini, deploys nothing and launches nothing):
  * Memoria.ini [Netsync] Enabled = 0 (or absent) AND GhostAs one of "", auto, off, 0 (or absent): the selftest role is
    refused on a live-configured install (HarnessSelfTest), and a NAMED GhostAs dresses the selftest mirror whatever the
    slots (ResolveDress's named branch). S138-INI reads both READ-ONLY and, when either is off, records itself red and runs
    NOTHING. (At writing the shared ini reads Enabled=1 Role=host GhostAs=auto: set Enabled=0 by hand -- after a backup --
    and relaunch.) [s139] GhostAs is read once more, READ-ONLY, for what the mirror must wear: on an s139+ engine the
    selftest mirror runs THE HOST RULE under the forced role's GuestSlots pin 0, so `auto` dresses it as the MOOGLE (owner
    D2) and "" / off / 0 leave it undressed -- I7 and G0 judge whichever the ini names, never the ini a test assumed.
  * The DLL under test deployed and the game launched on it, controllers OFF (THE UNATTENDED LAW: no leg needs a human).
  * COOPPARTY (30604, FF9CustomMap-msgs) and 30801 (FF9CustomMap) registered (S138-PRE).

WHAT IS PROVEN (S138-*):
  INI   precondition: [Netsync] Enabled reads 0 / absent and GhostAs "" / auto / off / 0 / absent (READ-ONLY) -- else
        NOTHING runs.
  OR    the offline oracle read, per field (fields 250 and 30801, the models, the clips, the DictionaryPatch remaps, the
        seed) -- red when any part failed; a check whose OWN field's oracle failed reads "not reached: no oracle for field
        N (why)", every other check judges on.
  S0    newgame -> warp 250 at entrance 0 (Zidane_Init's default spawn, (2921, -1830): more than 3000u from both of 250's
        exits -- `warp 250 -1` would keep whatever General_FieldEntrance the last field set) -> `noencounter 1` (field
        250 runs random battles, and the forced selftest does not suppress them) -> `netsync selftest 1` forced
        (Memoria.ini untouched).
  P0    the probe: this engine's instrument is WHOLE or wholly ABSENT -- the s138 `player.*` keys (in WritePlayerDress's
        order) with `netsync.dress.ghost` (opening with s138's FROZEN six keys, BW.DRESS_GHOST_KEYS_BY_RUNG) and `party`
        (4), or none of them (an engine before s138: every value check below then reads red on "absent", never on a
        value). Its stage is the HIGHEST rung of the dress probe ladder (BW.DRESS_PROBES: 138 `netsync.dress.ghost`, 139
        `codec`, 140 `self`, 141 `self.steps`) the engine publishes, every rung below present. Red only on a TORN
        instrument (a half without the other, a short party, a gap in the ladder).
  PRE   precondition: the selected legs' fields (leg I: 30604 COOPPARTY and 30801) registered in a DictionaryPatch.txt --
        else the seed and the 30801 halves read "not reached".
  -- field 250, before the seed --
  I1    the controlled body's `model` is its field's SetModel id AND its witness `body` is that model's texture stem (a
        dress cannot compute it): 98 / "98" on 250 and on 30801. `body` null with the model right reads "not reached:
        cannot judge" (an unnamed texture), never a pass.
  I2    `geo` is that model's GEO name (read_model, cross-checked with the kit's table): GEO_MAIN_F0_ZDN on both fields.
  I4    `eye` is -4 x SetModel's eye byte: -372 on both fields.
  I9    `sid == uid ==` the field's controlled entry (InitObject(sid, 0)): 10 on 250, 1 on 30801.
  I5    the loco ids, on 250 (encounters off), JUDGED PER FIELD TICK: the engine moves the player only on 30 Hz ticks, so
        at ~60 fps every other publish shows the same position. A walk probe holds one direction WALK_TICKS ticks (sized
        to frames at the MEASURED render rate; up, then down / left / right until one moves), then walks back. MOVING:
        the publishes that moved are the ticks (a still publish between two of them is a render frame with no tick); the
        move's middle -- after its first STEADY_TICKS ticks, before its last TAIL_TICKS -- is judged on EVERY publish from
        its first tick to its last, the tickless frames included: the anim is the field's walk OR run id (25 / 38 --
        either: whether the hold walks or runs is Cancel XOR the config, never guessed), its clip plays and folds to the
        GEO. AT REST: the last publish of the REST_S window after the walk back, the player still for REST_STILL
        publishes, reads the stand id (200) and its clip's name. The idle timer's sleep clip (57, CheckSleep after
        (200 + r) << 2 ticks with no movement) is REPORTED as the known sleep clip, never a pass for 200; any other id is
        red. A hold that is TAKEN OVER -- the field left, control lost or a fade begun (a gateway's DisableMove + Wait(25)
        comes before its Field()) -- reads "not reached"; the bench waits the takeover out and warps back at entrance 0.
  I3    at rest on 250 (anim != 0 -- anim 0 is ANH_MAIN_F0_STN_B): the clip the Animation component ACTUALLY plays folds to
        the body's GEO (`anim_geo == geo`, the oracle's) and `clip_playing` is true.
  I7    the forced selftest's mirror on 250, FieldHUD: `netsync.session.ghost` true; on the LAST rest publish whose player
        anim AND ghost (model, geo, clip, rig) have held GHOST_HOLD+ publishes (DriveGhost runs from another
        MonoBehaviour: one frame of skew; a re-dress deferred off FieldHUD lands a frame late, the old body already on the
        new clip), every value non-null on both sides and the ghost wearing the player's own: model, geo, clip, rig -1
        (undressed: the selftest pins GuestSlots 0, so ResolveDress("auto") returns 0), playing true, and the player's
        body stem. ON AN s139+ ENGINE (the probe's stage) the mirror runs the host rule instead: I7 judges what
        judge_worn computes for the ini's GhostAs with every lever off -- the MOOGLE (220, rig 8, GEO_NPC_F0_MOG, body
        '220', ANH_NPC_F0_MOG_IDLE at rest) for auto, the player's own body for "" / off / 0 -- against the install's
        oracle (G0 judges the same baseline, with the mode).
        (The rest window is judged only while the game is still on 250 -- FieldHUD, control, no fade: its first sample
        that is not ends it. An empty window reads "not reached".)
  -- the seed: warp through 30604 to 30801 --
  I8    `netsync.dress.party` holds 4 slots: party[0] == 0 and the seated members, sorted, == the seed's oracle [0, 1, 2, 3].
  -- field 30801 --
  I6    >= 2 listed actors, every one carrying an int `model`, each its entry's SetModel id by sid (217: the oracle), and
        none reads 98 (the player's).
        (I1 / I2 / I4 / I9 judge 30801's kit player here too.)
  R     `reset` releases the forced selftest role (no lever exists at s138: nothing else to release). [s139] On an s139+
        engine (the probe's stage) the bench first HOLDS one inert lever into the reset -- `selfdress rule s139`, seen
        published -- so R also witnesses THE HARNESS RELEASE (HarnessReleaseBench -> HarnessReleaseDress): the line
        'selfdress levers released (released with the harness)' logged and every lever read back off (`bench_mask`,
        `empty_mask`, `wire`, `wire_anim` -1, `rule` null: the getters publish them raw, in every role).
NOT PROVEN HERE: `frame_n` / `anim_frame` / `meshflags` / `clip` beyond I5's name (published for s140-s141's legs), the
world actor (`player.*` on the world map), a body whose texture is not its own id's (an alias prefab), a body whose texture
has no name (a loose-FBX or CustomModelField body: `body` null), the ghost of a REAL peer (two machines: sitting B), a
1-frame clip's `anim_geo` (null: stopped at once -- never judged), and the dress itself (s139-s141). FOR s141's F8 (a prop
attached at bone 13): judge it on a NON-Zidane controlled body and assert the prop's own stem differs from the body's -- on
Zidane a first-renderer read finds battle_model0 ("98") with or without the prop, so an F8 there cannot fail.

CALIBRATION -- a check that cannot fail is not a check (R3-FIELD-MODEL-AUDIT.md 2.1 amendment 1).
  * THE DEPLOYED DLL AT WRITING (s137, Assembly-CSharp 0269771f24b626c1) -- and any engine before s138: `player.model`
    and `netsync.dress` are absent, so P0 reads "absent" (green: the instrument is wholly absent, not torn) and every
    value check reads red on its absent key. RED, exactly: I1-I9. GREEN: INI, OR, S0, P0, PRE, R. COOP_CALIBRATE=1 there
    judges exactly that red set as S138-CAL (leg I's `old` row at stage 137).
  * HOW THE LEGS COMBINE (:func:`predicted`): a leg whose patch is NEWER than the engine contributes its `old` row for
    that stage; a leg at or before the engine contributes its `lever` row for the mode COOP_DRESS_CAL names (default
    `old`: no lever pulled), or nothing -- it must stay GREEN; S138-CAL reads "no calibration" only when NO selected leg
    defines a red set. So leg I on s138 contributes nothing and leg G's `old` row at 138 still calibrates the run.
  * ON s138 there is no lever (an inert instrument): COOP_CALIBRATE=1 with leg I alone on an engine WITH the instrument
    records S138-CAL red, naming the engine to calibrate on. A COOP_DRESS_CAL mode no selected leg has records S138-CALMODE
    red and runs nothing.
  * OFFLINE: the stand-in (tools/harness/fakegame.py, rung `dressinstr`) publishes the keys with honest values and FAULT
    LEVERS (FakeGame.dress_faults: a wrong eye, a foreign body, nothing playing, a wrong uid, a missing ghost, a ghost in
    another model, an empty party, objects without `model` -- each a value OTHER than the one worn); ff9mapkit/tests/
    test_harness_netsync.py turns each pure judge below red on an absent key, an empty list, a null and each fault, and
    smokes this bench against the stand-in at mean ticks AND at whole (quantized) ticks rendering 60 and 31 fps -- never
    read S138-CAL offline: the engine is the calibration.

LEG G (s139) -- THE HOST'S DRESS RULE AND WIRE SECTION 8 (R3-FIELD-MODEL-AUDIT.md 2.2 and 4.3, with the owner's two
decisions of 2026-10-17: D1 Option A -- the host's GhostAs is the one knob for both screens, no position-frame change; D2
-- a spectating guest, GuestSlots 0, is the MOOGLE). The selftest mirror IS the guest and this machine its host: its dress
site runs the s139 rule (ResolveAuto: the first OCCUPIED named slot decides, a main wears its rig, an empty named slot is
skipped, a member 8+ is undressed, mask 0 or every named slot empty the moogle -- behind GhostGuard: a wire body of 98 or the
dress itself is dressed, any other shows as it is; the raw anim on the wire's own body), driven by the `selfdress` levers
(selftest role only, released with the harness): `ghost <mask>` stands in for GuestSlots AND forces mode auto, `empty
<mask>` empties party slots for the dress read, `wire <model> [anim]` stands in for the mirror's wire body (with `anim`
PLAYING that raw clip -- the raw-anim rule's only input the loco translation cannot reproduce), `rule s138` restores the
whole pre-s139 site (the calibration lever), `clear` releases them. EVERY EXPECTED VALUE IS COMPUTED, never asked of the
engine: battlewire.selftest_dress -- the site's Python twin, its rig rows pinned to the census AND to the s139 patch by
test_harness_netsync.py -- on each judged publish's own player model / anim and LIVE party (`netsync.dress.party`, never
NetSyncParty.Slots), the ini's GhostAs read offline and the levers the bench set; the expected model's GEO name and texture
stem off the install (read_model, cross-checked with the kit's GEO table), the clip NAME off the kit's copy of the
open-source AnimationDB, the idle frames off p0data5 (the kit's clip reader at catalog.locate_animation's folder,
round(length x rate) + 1 -- the oracle_extra hook `_g_oracle`; [60, 45, 30, 60, 50, 40, 30, 45, 72] at writing), and
Garnet's prefab renderer tree off p0data (the kit's prefab walk: G8's field-mode hides by ModelFactory's own rule,
battlewire.field_hides, with the ini's [Graphics] GarnetHair read offline and the published scenario counter). A row is
judged on the LAST publish where the player's anim and the ghost's tuple have held GHOST_HOLD+ publishes on FieldHUD with
the PUBLISHED levers equal to the ones set (the ops landed) and `ghost.mode` the one they imply ("bench:auto" under a
`ghost` lever -- the lever FORCES auto, amendment 1 -- else "ini:" + the ini's GhostAs), GHOST_SETTLE_S after the ops;
`playing` is judged only when the expected clip lives in the worn model's own GEO folder (EnsureGhost loads that folder
alone). Before every row the bench `clear`s whatever it set (under the calibration lever, `rule s138` again).
  -- field 250, before the seed (after leg I's rest window) --
  G0    the baseline, every lever off: `ghost.mode` == "ini:" + the ini's GhostAs and the mirror wears the twin's answer
        for it (the moogle for auto, owner D2; its own body for none).
  G4    `netsync.dress.codec` == "ok" and the proof line "dress codec selftest: OK (29 rows)" (its rows 16-26 run a REAL
        host frame through the s103 readers an old guest runs, a section appended AFTER section 8 included: the in-engine
        proof that section 8 is skipped by its length). Judged here: the proof block runs at S0, whatever the seed does.
  G6    `rig_idle_frames` == the install's oracle, row for row (the proof block's too).
  G3a   while the New-Game party's slot 1 is EMPTY (the real party read; "not reached" when the save already holds it):
        `ghost 2` -> the moogle (220, rig 8, GEO_NPC_F0_MOG, body '220', an ANH_NPC_F0_MOG clip, playing).
  -- the seed (leg I's), then on 30801, s1 = the first slot >= 1 holding a main (Vivi in slot 1 after COOPPARTY) --
  G1    `ghost 1<<s1` -> that member's rig row: model and rig == party[s1], its GEO and body, its loco clip, playing.
  G2    `ghost 6` + `empty 2` -> slot 2's member (Garnet: the empty named slot skipped). Not reached without a main there.
  G3    `ghost 2` + `empty 2` -> the moogle.        G3c  `ghost 6` + `empty 6` -> the moogle (a MULTI-bit mask, all empty).
  G3m   the moogle MOVING (box B19's "a moogle that walks, runs and turns"): `ghost 2` + `empty 2`, then a walk probe on
        30801 (leg I's: one hold, judged per tick) -- every mid-move publish whose player anim held 2+ publishes shows the
        twin's clip for that anim (25 -> ANH_NPC_F0_MOG_WALK, 38 -> ANH_NPC_F0_MOG_RUN: whichever the hold took), playing,
        on the moogle. The turn clips are left to the sitting (their timing depends on the run).
  G3d   `ghost 0` -> the moogle (a spectator), AND the proof block's line "dress section 8 as this machine would host now:"
        carries the twin's body for the ini's GhostAs under the pin -- "DC 00 FF (model 220, charId 255)" for auto, "00 00
        FF (model 0, charId 255)" for none (the producer's bytes; the selftest role has no socket: the wire's own witness is
        G9, below).
  G5    (control) its OWN setup: `ghost 1<<s1` held until the ghost wears party[s1]'s rig (the precondition), then `clear`
        ALONE -> every lever -1 / null, the mode G0's, the ghost back to G0's baseline (model, geo, rig) -- a witness that
        MOVES under every ini (Vivi -> the moogle under auto, Vivi -> the player's own body under none).
  G7a-d the guard, on `ghost <s1 bit>`: `wire 5489` (a Steiner-led guest) -> the ghost SHOWS 5489, rig -1, with Steiner's
        own loco clip; `wire <the dress model> <its rig's break clip>` (an s140 guest already dressed, PLAYING Vivi's 912)
        -> dressed, playing the RAW 912 (amendment 4: the s138 translation flattens it to her idle); `wire 98` (an s117 or
        SelfDress=0 guest: owner D1) -> dressed; `wire 532` (GEO_MAIN_F0_ZDD, no rig) -> shows 532.
  G8    THE REST MASK (amendment 8), on `ghost <Garnet's bit>` (Garnet seated by the seed): `shown_mask == rest_mask`, a
        hide among them, and `hidden` == the install prefab's field-mode hides (ModelFactory: Garnet's `short_hair` below
        ScenarioCounter 10300 unless [Graphics] GarnetHair forces a hairstyle; any `battle_model`) -- one hairstyle shown.
  Every lever is released at the leg's end (none is left for leg I's later reads), and `reset` releases them all (S138-R:
  on s139+ it holds `rule s139` into the reset and reads every lever back off -- the harness release witnessed in game).
NOT PROVEN BY LEG G: the turn clips of a moving moogle (timing-dependent: the sitting); the host's TRANSPORT site and
section 8 ON A REAL WIRE -- G9, below; a game_snap of the moogle (an AUDIT DEVIATION from 2.2 amendment 13 / 4.3 G3,
recorded in the README row: `geo` and `body` are read off the spawned GO -- the witnesses of what is worn -- and a
screenshot judges nothing unattended).
NOT PROVEN BY LEG G OR G9 (sitting boxes; a same-DLL duo guest always sends 98): the guard's non-98 half on the TRANSPORT
site (a guest wearing another body: B28) and the raw wire anim on the transport site (a guest whose wire body IS the dress:
an s140+ laptop, B20). Both are proven at the SELFTEST site only (G7a / G7d, G7b).
G9 -- SECTION 8 ON A REAL WIRE AND THE TRANSPORT SITE (studies/test-harness/scenarios/coop_dress_wire.py, a duo leg):
two s139 games through tools/harness/duo.py on the relay's tap -- the host at GhostAs auto with the COOPPARTY seed, field
250; the guest Role=client. An s139 GUEST's receive path IS the old path (no production code reads section 8 in s139:
test_harness_netsync.py pins it), so a same-DLL duo is a valid old-guest stand-in -- the duo's one limit (both roots
junction one Managed, so it cannot MIX DLLs) bites only box B19, an OLD laptop, which stays a sitting box. ONE dress cannot
tell the transport site from the s138 rule (at GuestSlots 2 both dress Vivi, who hides nothing), so the host's GuestSlots
is STEPPED LIVE through three dresses (duo.Duo.set_netsync, each step on the host's config echo, each judged publish
carrying its GuestSlots): G9d at 2 -- Vivi; G9e at 4 -- Garnet WITH THE REST MASK (rest_mask_verdict, the transport site's
`else if (hostRule) ApplyGhostMask(_ghostRestMask)`: one hairstyle); G9f at 0 -- a spectator, the MOOGLE (owner D2: the
s138 client rule leaves it undressed). G9a the tap, read last: section 8 on every host frame, skipped by the s103 walkers'
twins, its bodies in tape order 08 00 01 -> B9 00 02 -> DC 00 FF; G9b the guest's readers stepped past it ('state-mirror
ARMED', its story mirroring, `netsync.dress.mirror_party` == the host's party); G9c the guest's own body stays 98 at every
phase. Its cheap half on a recorded tape: `py tools/harness/coop_peer.py dress <tape> --ghost-as auto --guest-slots 2`
(each frame's own party read off its section 1; exit 0 = held) on a coop_tape_record.py tape; an s138 host's tape reads
"none -- an s138-or-older host" (exit 1: its calibration red). A relative tape path missing from the cwd is looked up
under the MAIN repo, then by name in the tape home (a worktree has no tapes).
  CALIBRATION: on s138 (the deployed DLL a8b0fd80ecc4013d at writing) and s137 every G check is red (G_CHECKS: the verb
  refused before the step, the keys absent) -- COOP_CALIBRATE=1 judges exactly that as S138-CAL. On s139 under
  COOP_DRESS_CAL=rule-s138 exactly G_LEVER_REDS go red (G3a, G2, G3, G3c, G3m, G3d, G7a, G7b, G7d, G8: the skip, the
  moogle, the guard's non-98 half, the raw anim, the rest mask); G0, G4 and G6 are read before the lever is pulled and
  G5's `clear` releases it, so they stay green with G1 and G7c (and leg I, judged before the lever). A lever-row red that
  reads "not reached" is the lever UNPROVEN there, never a predicted red: S138-CAL fails naming it. OFFLINE: the stand-in's
  `dresshost` rung models the site with battlewire.selftest_dress and its FAULT LEVERS (fakegame.DRESS_HOST_FAULTS) turn
  each row red on the shape it exists to catch; test_harness_netsync.py smokes this leg against it in every mode.

s139 ACCEPTANCE -- every step REQUIRED (the selftest site alone cannot witness the transport site or the wire):
  1. this bench, GhostAs auto (the owner's ini): green; then COOP_CALIBRATE=1 COOP_DRESS_CAL=rule-s138: S138-CAL green.
  2. this bench AGAIN with [Netsync] GhostAs = '' (the operator flips it BY HAND, after a backup, as for Enabled): green --
     under auto an engine whose `ghost` lever replaced the mask without forcing auto dresses identically, so only this
     pass can show G1-G3d red on it (fakegame's `ghost_keeps_ini_mode` fault).
  3. `py tools/harness/coop_peer.py dress C:/gd/Dream-World-IX/.harness-runs/coop-tapes/20261014-224827-host250-s117.f9tape`
     (the tape lives in the MAIN repo only) -> exit 1, "none -- an s138-or-older host": the tape check's calibration red.
  4. coop_tape_record.py on s139, then `py tools/harness/coop_peer.py dress <its tape> --ghost-as auto --guest-slots 2`
     -> exit 0, 08 00 01 (Vivi) on every host state frame (the recorder notes the host's own ghost tuple; no new check).
  5. `py tools/harness/duo.py studies/test-harness/scenarios/coop_dress_wire.py` -> G9a-f green: the transport site at
     GuestSlots 2 (Vivi), 4 (Garnet, one hairstyle) and 0 (the moogle), the tap 08 00 01 -> B9 00 02 -> DC 00 FF (and
     COOP_CALIBRATE=1 on the s138 DLL: exactly its OLD_PREDICTED red, G9f's detail the old DLL's undressed spectator).

RUN (from THIS worktree, so its tools/ and ff9mapkit/ are the ones imported):
    py tools/play.py studies/test-harness/scenarios/coop_self_dress.py --field 250
    COOP_CALIBRATE=1 py tools/play.py studies/test-harness/scenarios/coop_self_dress.py --field 250    (on the s137 DLL)
    COOP_CALIBRATE=1 COOP_DRESS_CAL=rule-s138 py tools/play.py studies/test-harness/scenarios/coop_self_dress.py --field 250
        (leg G's lever, on s139)      COOP_DRESS_LEGS=G ... (leg G alone; it still needs the seed, so PRE holds)
  PowerShell has no per-launch form: a `$env:` value PERSISTS in that shell -- clear it after each run:
    Remove-Item Env:COOP_CALIBRATE, Env:COOP_DRESS_LEGS, Env:COOP_DRESS_CAL -ErrorAction SilentlyContinue
"""
from __future__ import annotations

import os
import shutil
import sys
from itertools import takewhile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file

try:                                                       # play.py puts tools/ on sys.path before it loads a scenario
    from harness import battlewire as BW                   # noqa: E402
except ImportError:                                        # pragma: no cover - imported outside the driver
    sys.path.insert(0, str(cb.REPO / "tools"))
    from harness import battlewire as BW                   # noqa: E402

HarnessError = cb.HarnessError

STOCK_FIELD = 250                          # Evil Forest/Trail (reference/field-manifest.tsv: HW test2_67): random battles
STOCK_ENTRANCE = 0                         # 250's General_FieldEntrance 0: Zidane_Init's default spawn (2921, -1830)
BENCH_FIELD = 30801                        # EVT_TEST30801 (coop_talk_relay's bench): the kit player + two CSO NPCs
PARTY_FIELD = cb.PARTY_FIELD               # 30604 COOPPARTY: [party] add = vivi, garnet, steiner
PARTY_TOML = cb.REPO / "studies" / "battle-coop" / "bench" / "coopparty.field.toml"
PLAYER_PROBE = "player.model"              # the instrument's half OUTSIDE netsync (absent = s137 or older)
#: THE DRESS PROBE LADDER (battlewire.DRESS_PROBES): the stage the probe reports is the highest rung present
STAGE_PROBES = dict(BW.DRESS_PROBES)
DRESS_PROBE = STAGE_PROBES[138]            # netsync.dress.ghost: its half inside netsync (== cb.R3_PROBES[138])
#: s138's OWN `ghost` keys, FROZEN (never the live union a later rung grows): the probe holds an engine to these
S138_GHOST_KEYS = tuple(BW.DRESS_GHOST_KEYS_BY_RUNG["dressinstr"])
GHOST_AS_OK = ("", "auto", "off", "0")     # [Netsync] GhostAs values that leave the selftest mirror undressed
EVT_LANG = "us"                            # the event-script language read (the kit's EVT_LANG)
EVENT_DIR = ("StreamingAssets", "assets", "resources", "commonasset", "eventengine", "eventbinary", "field")
#: the cache the oracle's readers WRITE into the install's StreamingAssets on a miss (ff9mapkit.extract._events_bundle,
#: reached by a stock field's p0data read) -- the bench never creates it (the install is READ-ONLY): a missing one reads
#: "not reached" for every field that needs it. (read_model writes nothing; the field index is never consulted here.)
KIT_CACHE_FILES = (".ff9mapkit-events-bundle.txt",)
NEW_GAME_BASE = (0,)                       # FF9Play_SetParty(0, Zidane): New Game seats Zidane alone in slot 0
#: CharacterOldIndex (the .eb's / [party]'s id space) -> CharacterId (PLAYER.Index, what `dress.party` publishes): equal for
#: the mains 0-7; 8-11 differ (old Beatrix 8 / Cinna 9 / Marcus 10 / Blank 11 -> id Cinna 8 / Marcus 9 / Blank 10 / Beatrix 11)
OLD_INDEX_TO_ID = {**{i: i for i in range(8)}, 8: 11, 9: 8, 10: 9, 11: 10}
OP_INIT_OBJECT, OP_DEFINE_PLAYER, OP_SET_MODEL = 0x09, 0x2C, 0x2F
DICTIONARY_REMAP_VERBS = ("3DModel", "3DModelAnimation")   # DataPatchers: `<verb> <id> [<id> ...] <name>`
WALK_TICKS = 16                            # one probe hold, in FIELD TICKS (frames at the measured rate: 32 at 60 fps)
WATCH_EXTRA_TICKS = 15                     # how long past the hold it is watched (the request lands a few frames late)
WALK_DIRECTIONS = ("up", "down", "left", "right")
BACK = {"up": "down", "down": "up", "left": "right", "right": "left"}
MOVE_EPS = 1.0                             # field units between two publishes that count as a move (a tick ran)
STEADY_TICKS = 2                           # moving TICKS before the move's MIDDLE begins (the hold has taken)
TAIL_TICKS = 1                             # ...and the last moving ticks not judged (the release's coast)
#: the most still publishes in a row INSIDE one move: render frames that ran no field tick (1 at 60 fps, up to 3 at the
#: ~105 fps the harness has seen); more than this ends the move
TICK_GAP = 4
REST_S = 3.0                               # the rest window after the walk back: well inside the idle timer (~26 s)
REST_STILL = 3                             # publishes the player must hold still at the rest read
GHOST_HOLD = 2                             # publishes the player's anim must hold before the ghost is compared
SETTLE_S = 20.0                            # a field's arrival: FieldHUD + control
SETTLE_FRAMES = 45                         # frames after a warp before the reads (Main_Init's B_PARTYADD on 30604)
LEAVE_S = 20.0                             # how long a taken-over hold is given to finish (a gateway's wait + the load)
#: COOP_DRESS_CAL's no-lever mode: calibrate on an engine BEFORE a leg's patch
CAL_OLD = "old"


# ================================================================================================ the legs
def _catalog_i() -> dict:
    return {
        "S138-I1": "the controlled body's `model` is its field's SetModel id and its witness `body` that model's texture "
                   "stem: 98 / '98' on 250 and on 30801 (the oracle)",
        "S138-I2": "`geo` is that model's GEO name (read_model + the kit's table): GEO_MAIN_F0_ZDN on 250 and on 30801",
        "S138-I3": "at rest on 250 (anim != 0): the clip the Animation component plays folds to that GEO (`anim_geo == "
                   "geo`) and `clip_playing` is true",
        "S138-I4": "`eye` is -4 x SetModel's eye byte: -372 on 250 and on 30801",
        "S138-I5": "on 250, encounters off, judged per field tick: mid-move the anim is the field's walk or run id (25 / 38, "
                   "either) with its clip playing in the body's GEO; at rest (REST_S after the walk back, still) the stand "
                   "id 200 and its clip's name -- the sleep clip 57 reported, never a pass",
        "S138-I6": "on 30801: >= 2 listed actors, each carrying an int `model` equal to its entry's SetModel id (217), none "
                   "98",
        "S138-I7": "the forced selftest's mirror on 250, FieldHUD: session.ghost true; with the player's anim held 2+ "
                   "publishes the ghost wears the player's model / geo / clip, rig -1, playing, and the player's body",
        "S138-I8": "after the COOPPARTY seed: `dress.party` has 4 slots, party[0] == 0 and the seated members sorted == "
                   "the seed's oracle [0, 1, 2, 3]",
        "S138-I9": "`sid == uid ==` the field's controlled entry (InitObject(sid, 0)): 10 on 250, 1 on 30801",
    }


I_CHECKS = tuple(_catalog_i())

# ---- [ff9mapkit netsync s139] LEG G -- THE HOST'S DRESS RULE (see the docstring's LEG G)
#: the wire bodies the guard rows stand in (`selfdress wire`): a body WITH a rig (Steiner: the guard shows it, moving with
#: its own rig's loco clip) and one with NONE (GEO_MAIN_F0_ZDD: the guard shows it, playing my raw clip)
G_WIRE_RIGGED = 5489
G_WIRE_UNRIGGED = 532
#: every model leg G may expect the ghost to wear -- the nine rig rows (the twin's, pinned to the census) and the unrigged
#: wire body -- each read off the install by the oracle (GEO name, texture stem), never the engine's tables
G_MODELS = tuple(row[0] for row in BW.RIGS) + (G_WIRE_UNRIGGED,)
#: the models whose PREFAB renderer tree the oracle reads (G8's field-mode hides): Garnet, the one body with two hairstyles
G_PREFAB_MODELS = (185,)
#: G8's member: Garnet (CharacterId 2), seated by the seed
G_GARNET = 2
#: after a `selfdress` op: how long the ghost is watched before the LAST held publish is judged (EnsureGhost re-dresses in
#: the same frame on FieldHUD; DriveGhost trails one frame)
GHOST_SETTLE_S = 2.0
#: leg G's calibration lever (COOP_DRESS_CAL): `selfdress rule s138` -- the WHOLE pre-s139 selftest site (the first named
#: bit, no skip, no moogle, no guard, the loco translation on any dress, no rest mask), pulled after G0 / G4 / G6 and again
#: after every `clear`
CAL_RULE_S138 = "rule-s138"


def _catalog_g() -> dict:
    return {
        "S139-G0": "the baseline, first: `ghost.mode` reads 'ini:' + the ini's GhostAs (read offline) and the mirror wears "
                   "the s139 rule's answer for it under the GuestSlots-0 pin -- the MOOGLE for auto (owner D2), its own "
                   "body for '' / off / 0 -- model, rig, geo, body and clip against the twin and the install's oracle",
        "S139-G4": "`netsync.dress.codec` == 'ok' and the proof block's 'dress codec selftest: OK (29 rows)' line (judged at "
                   "the stock field: the proof block runs at S0)",
        "S139-G6": "`rig_idle_frames` == the oracle the kit's clip reader reads off the install's p0data5 (round(length x "
                   "rate) + 1 per rig row's idle clip)",
        "S139-G3a": "before the seed, slot 1 EMPTY on the real party: `ghost 2` (no `empty`) -> the moogle (220, rig 8, "
                    "GEO_NPC_F0_MOG, body '220', an ANH_NPC_F0_MOG clip, playing)",
        "S139-G1": "after the seed: `ghost 1<<s1` (s1 = the first slot >= 1 holding a main, read off the live party) -> that "
                   "member's rig row: model, rig == party[s1], its GEO and body off the install, its loco clip, playing",
        "S139-G2": "`ghost 6` + `empty 2` -> slot 2's member (an EMPTY named slot is skipped to the next named one)",
        "S139-G3": "`ghost 2` + `empty 2` -> the moogle (every named slot empty)",
        "S139-G3c": "`ghost 6` + `empty 6` -> the moogle (every named slot of a MULTI-bit mask empty)",
        "S139-G3m": "the moogle MOVING: `ghost 2` + `empty 2`, then a walk probe -- every mid-move publish whose player anim "
                    "held 2+ publishes shows the twin's clip for it (25 -> ANH_NPC_F0_MOG_WALK, 38 -> ANH_NPC_F0_MOG_RUN), "
                    "playing, on the moogle",
        "S139-G3d": "`ghost 0` (a spectator, owner D2) -> the moogle; and the proof block's section-8 line is the twin's body "
                    "for the ini's GhostAs under the pin (DC 00 FF for auto, 00 00 FF for none)",
        "S139-G5": "(control, its own setup) `ghost 1<<s1` held until the ghost wears party[s1]'s rig, then `clear` ALONE -> "
                   "every lever back off (-1 / null), the mode back to G0's, and the ghost back to G0's baseline",
        "S139-G7a": "the guard, `ghost <s1 bit>` + `wire 5489` (a Steiner-led guest) -> the ghost SHOWS 5489, rig -1, "
                    "moving with Steiner's own loco clip",
        "S139-G7b": "`wire <the dress model> <its rig's break clip>` (an s140 guest already dressed, PLAYING Vivi's 912) -> "
                    "dressed, playing the RAW wire clip (amendment 4; the s138 translation flattens it to the dressed idle)",
        "S139-G7c": "`wire 98` (a plain-Zidane wire body: an s117 guest, or an opted-out SelfDress=0 one -- owner D1) -> "
                    "dressed",
        "S139-G7d": "`wire 532` (GEO_MAIN_F0_ZDD, no rig) -> the ghost SHOWS 532, playing nothing it cannot load",
        "S139-G8": "THE REST MASK, `ghost <Garnet's bit>`: `shown_mask == rest_mask` with a hide among them, and `hidden` == "
                   "the install prefab's field-mode hides (ModelFactory's rule: one hairstyle by the scenario counter / "
                   "[Graphics] GarnetHair, any battle_model)",
    }


G_CHECKS = tuple(_catalog_g())
#: leg G's red set under its own lever (`rule s138`: the pre-s139 site) -- every row the host rule changed at this site:
#: the skip (G2), the moogle (G3a, G3, G3c, G3m, G3d), the guard's non-98 half (G7a, G7d), the raw anim on the wire's own
#: body (G7b: the pinned break clip translated to the dressed idle) and the rest mask (G8: 0xFFFF re-asserted, both
#: hairstyles shown). G0, G4 and G6 are read before the lever is pulled; G1, G5 and G7c stay GREEN (the first named bit
#: holds a main; `clear` releases the lever; a wire body of 98 is dressed by both rules, with the same translated clip).
G_LEVER_REDS = ("S139-G3a", "S139-G2", "S139-G3", "S139-G3c", "S139-G3m", "S139-G3d", "S139-G7a", "S139-G7b", "S139-G7d",
                "S139-G8")


#: THE LEG REGISTRY. Per leg: its patch; its catalog and checks; its steps per phase (each `step(g, led, ctx)`); `pre` --
#: the fields it needs REGISTERED (S138-PRE); `oracle` -- the fields whose `.eb` the oracle reads ("stock" = the run's
#: --field); `oracle_extra` -- None, or the NAME of a function ``(g, ctx) -> (dict, {key: why})`` reading this leg's own
#: offline oracle (merged into ``oracle["extra"][leg]``, its problems into S138-OR); `old` -- its predicted (reds, maybe) on
#: an engine BEFORE its patch, by the stage the probe finds (no row = no calibration defined there); `lever` -- its
#: (reds, maybe) under each of its OWN calibration levers, by COOP_DRESS_CAL mode.
LEGS = {
    "I": {"patch": 138, "catalog": _catalog_i, "checks": I_CHECKS,
          "steps": {"stock": "_i_stock", "seeded": "_i_seeded", "bench": "_i_bench", "close": "_i_close"},
          "pre": (PARTY_FIELD, BENCH_FIELD), "oracle": ("stock", BENCH_FIELD), "oracle_extra": None,
          "old": {137: (I_CHECKS, ())}, "lever": {}},
    # [ff9mapkit netsync s139] on an engine before s139 every G check reads red: the `selfdress` verb is refused before the
    # step (the driver: no `netsync.dress.ghost.bench_mask`), and `mode` / `codec` / `rig_idle_frames` are absent
    "G": {"patch": 139, "catalog": _catalog_g, "checks": G_CHECKS,
          "steps": {"stock": "_g_stock", "seeded": "_g_seeded"},
          "pre": (PARTY_FIELD, BENCH_FIELD), "oracle": ("stock",), "oracle_extra": "_g_oracle",
          "old": {137: (G_CHECKS, ()), 138: (G_CHECKS, ())}, "lever": {CAL_RULE_S138: (G_LEVER_REDS, ())}},
}
PHASES = ("stock", "seed", "seeded", "bench", "close")
#: the engine stages the probe tells apart: 137 = no instrument (s137 or older); 138-141 = the dress probe ladder's rungs
STAGE_NONE, STAGE_INSTR = 137, 138


def selected_legs(env=None) -> tuple:
    """COOP_DRESS_LEGS (comma list, case-insensitive) -> the legs to run, in :data:`LEGS` order; default every leg. A name
    this file lacks raises ValueError (the run records it and runs nothing)."""
    raw = (os.environ if env is None else env).get("COOP_DRESS_LEGS", "")
    want = [t.strip().upper() for t in str(raw).split(",") if t.strip()]
    if not want:
        return tuple(LEGS)
    bad = [t for t in want if t not in LEGS]
    if bad:
        raise ValueError(f"COOP_DRESS_LEGS names {bad}: this file has legs {tuple(LEGS)}")
    return tuple(k for k in LEGS if k in want)


def cal_modes(legs) -> tuple:
    """The COOP_DRESS_CAL modes these legs know: CAL_OLD, then every selected leg's own lever modes (in leg order)."""
    out = [CAL_OLD]
    for leg in legs:
        out += [m for m in LEGS[leg]["lever"] if m not in out]
    return tuple(out)


def selected_cal_mode(legs, env=None) -> str:
    """COOP_DRESS_CAL (case-insensitive; default CAL_OLD) -> the calibration mode. A mode no selected leg has raises
    ValueError (the run records S138-CALMODE and runs nothing)."""
    raw = str((os.environ if env is None else env).get("COOP_DRESS_CAL", "")).strip().lower() or CAL_OLD
    if raw not in cal_modes(legs):
        raise ValueError(f"COOP_DRESS_CAL={raw!r} is no calibration mode of legs {tuple(legs)}: one of {cal_modes(legs)}")
    return raw


def _union(legs, key: str, stock: int | None = None) -> tuple:
    out = []
    for leg in legs:
        for f in LEGS[leg][key]:
            f = stock if f == "stock" else f
            if f is not None and f not in out:
                out.append(int(f))
    return tuple(out)


def pre_fields(legs) -> tuple:
    """The fields the selected legs need registered (S138-PRE), in leg order."""
    return _union(legs, "pre")


def oracle_fields(legs, stock: int) -> tuple:
    """The fields whose `.eb` the oracle reads for the selected legs ("stock" -> ``stock``), in leg order."""
    return _union(legs, "oracle", stock)


def _shared_catalog(calibrate: bool, legs=tuple(LEGS)) -> dict:
    pre = pre_fields(legs)
    c = {
        "S138-INI": "precondition: Memoria.ini [Netsync] Enabled reads 0 / absent and GhostAs '' / auto / off / 0 / "
                    "absent, READ-ONLY -- else NOTHING runs",
        "S138-OR": "the offline oracle, per field (the fields' .eb, the models' GEO and texture stems, the clip names, the "
                   "DictionaryPatch remaps, the seed's party) read through the kit's readers -- never the engine's answer",
        "S138-S0": "newgame -> warp 250 at entrance 0 -> encounters off -> the forced selftest role (Memoria.ini untouched)",
        "S138-P0": "the probe: the instrument is WHOLE (the s138 player keys, dress.ghost opening with s138's six keys, "
                   "party[4]; the dress ladder gap-free) or wholly ABSENT (an engine before s138) -- never torn",
        "S138-PRE": f"precondition: {' and '.join(str(f) for f in pre)} registered in a DictionaryPatch.txt",
        "S138-R": "`reset` releases the forced selftest role",
    }
    if calibrate:
        c["S138-CAL"] = ("CALIBRATION: exactly the predicted checks are red -- each selected leg's `old` row on an engine "
                         "before its patch (leg I on s137: I1-I9; leg G on s137 / s138: every G check), its `lever` row "
                         "under COOP_DRESS_CAL (leg G's rule-s138: G3a, G2, G3, G3c, G3m, G3d, G7a, G7b, G7d, G8), nothing "
                         "else; a lever row whose red reads 'not reached' is UNPROVEN, never a predicted red")
    return c


def _catalog(legs, calibrate: bool) -> dict:
    c = _shared_catalog(calibrate, legs)
    for leg in legs:
        c.update(LEGS[leg]["catalog"]())
    return c


def predicted(stage, legs, mode: str = CAL_OLD) -> tuple:
    """COOP_CALIBRATE=1's prediction for the engine stage the probe FOUND, under COOP_DRESS_CAL ``mode``: (reds, maybe,
    why) -- reds None = no calibration is defined (the CAL row reads red with the why). Each selected leg CONTRIBUTES: a
    leg whose patch is newer than ``stage`` its `old` row for that stage (none there = undefined: None); a leg at or
    before ``stage`` its `lever` row for ``mode`` -- or nothing (no such lever, or CAL_OLD): it must stay GREEN. None only
    when NO selected leg defines a red set."""
    if stage is None:
        return None, (), "no calibration on a TORN instrument (S138-P0 is red): judge nothing on it"
    reds, maybe, defined = [], [], []
    for leg in legs:
        spec = LEGS[leg]
        if spec["patch"] > stage:
            row = spec["old"].get(stage)
            if row is None:
                return None, (), (f"no calibration for leg {leg} (s{spec['patch']}) on engine stage s{stage}: its `old` "
                                  f"table has no row for that engine")
        elif mode != CAL_OLD:
            row = spec["lever"].get(mode)
        else:
            row = None
        if row is not None:
            reds.extend(row[0])
            maybe.extend(row[1])
            defined.append(leg)
    if not defined:
        if mode != CAL_OLD:
            return None, (), f"no selected leg ({', '.join(legs)}) has the lever {mode!r} on engine stage s{stage}"
        return None, (), (f"no calibration for legs {', '.join(legs)} on engine stage s{stage}: "
                          + "; ".join(f"s{LEGS[g]['patch']} has no lever (an inert instrument)" for g in legs)
                          + " -- calibrate on the engine BEFORE it (the s137 DLL 0269771f24b626c1)")
    return tuple(dict.fromkeys(reds)), tuple(dict.fromkeys(maybe)), ""


def lever_unproven(stage, legs, mode: str, unreached) -> list:
    """(PURE) Under a calibration LEVER (``mode`` != CAL_OLD): the lever rows of the legs at or before ``stage`` whose red
    reads "not reached" (``unreached``: the ids recorded so) -- the lever never bit there, so the red proves nothing about
    it and S138-CAL must fail naming them (Ledger.judge_calibration alone would count any red). An `old` row (a leg newer
    than the engine: its verb refused before the step) is left alone -- there a pre-step refusal IS the predicted red."""
    if stage is None or mode == CAL_OLD:
        return []
    rows = [c for leg in legs if LEGS[leg]["patch"] <= stage for c in LEGS[leg]["lever"].get(mode, ((), ()))[0]]
    return sorted(c for c in dict.fromkeys(rows) if c in set(unreached or ()))


# ================================================================================================ reads (raw, absent-aware)
_ABSENT = object()


def _raw(x) -> dict:
    return cb.raw(x)


def _player(x) -> dict:
    p = _raw(x).get("player")
    return p if isinstance(p, dict) else {}


def _dress(x) -> dict | None:
    """``netsync.dress`` (None when absent: an engine before s138)."""
    ns = _raw(x).get("netsync")
    d = ns.get("dress") if isinstance(ns, dict) else None
    return d if isinstance(d, dict) else None


def _int(v) -> int | None:
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def _show(p: dict, key: str) -> str:
    """One player key for a detail line: ``key=value``, ``key=null`` or ``key ABSENT``."""
    if key not in p:
        return f"{key} ABSENT"
    return f"{key}={p[key]!r}"


def _pos(x) -> tuple | None:
    p = _player(x)
    xs, zs = p.get("x"), p.get("z")
    if not isinstance(xs, (int, float)) or not isinstance(zs, (int, float)):
        return None
    return float(xs), float(zs)


def _moved(a, b) -> bool:
    pa, pb = _pos(a), _pos(b)
    if pa is None or pb is None:
        return False
    return abs(pa[0] - pb[0]) > MOVE_EPS or abs(pa[1] - pb[1]) > MOVE_EPS


def free_on(x, field: int) -> bool:
    """(PURE) The game is still on ``field`` and the player free: FieldHUD, control, no fade -- what a read on the field is
    judged under (a gateway's DisableMove / fade, a load, a cutscene all end it)."""
    r = _raw(x)
    return ((r.get("field") or {}).get("id") == field and r.get("ui_state") == "FieldHUD"
            and bool((r.get("player") or {}).get("control")) and not r.get("fading", False))


def on_field_prefix(samples: list, field: int) -> list:
    """(PURE) The samples up to the first that is not :func:`free_on` ``field`` -- nothing after the game left is judged."""
    return list(takewhile(lambda s: free_on(s, field), samples))


def _no_oracle(fo) -> str | None:
    """A judge's first line: the "not reached" detail when ``fo`` is no oracle (missing, or :func:`_fo`'s named miss)."""
    if not fo:
        return "not reached: no oracle for this field"
    if "_none" in fo:
        return f"not reached: {fo['_none']}"
    return None


# ================================================================================================ the pure judges
def probe(x) -> tuple:
    """S138-P0 (PURE): (stage, detail) -- the HIGHEST rung of the dress probe ladder (:data:`STAGE_PROBES`) this engine
    publishes, every rung below it present too, with the s138 instrument WHOLE against s138's OWN FROZEN rows (every
    PLAYER_DRESS_KEY in the player block, in its order; `netsync.dress` opening with ghost, party; ghost opening with
    :data:`S138_GHOST_KEYS`; party 4 long). Later patches only APPEND (s139's levers in `ghost`, `codec` in `dress`), so a
    prefix is whole. STAGE_NONE when it is wholly ABSENT (no dress key in the player block, no `netsync.dress`); None when
    TORN (a half without the other, a short party, a gap in the ladder)."""
    p = _player(x)
    have = [k for k in p if k in BW.PLAYER_DRESS_KEYS]
    d = _dress(x)
    if not have and d is None:
        return STAGE_NONE, ("absent: no `player.model` and no `netsync.dress` -- an engine before s138 (every value "
                            "check reads its absent key)")
    ghost = d.get("ghost") if isinstance(d, dict) else None
    party = d.get("party") if isinstance(d, dict) else None
    whole = (have == list(BW.PLAYER_DRESS_KEYS) and isinstance(d, dict) and list(d)[:2] == ["ghost", "party"]
             and isinstance(ghost, dict) and tuple(ghost)[:len(S138_GHOST_KEYS)] == S138_GHOST_KEYS
             and isinstance(party, list) and len(party) == 4)
    rungs = [s for s in sorted(STAGE_PROBES) if cb.has(x, STAGE_PROBES[s])]
    gapless = bool(rungs) and rungs == sorted(STAGE_PROBES)[:len(rungs)]
    detail = (f"player dress keys {have}; netsync.dress keys {list(d) if isinstance(d, dict) else None}; ghost keys "
              f"{list(ghost) if isinstance(ghost, dict) else None}; party {party!r}; dress ladder rungs {rungs}")
    if not (whole and gapless):
        return None, "TORN: " + detail + ("" if gapless else " (a gap in the dress probe ladder)")
    return rungs[-1], f"whole (s{rungs[-1]}): " + detail


def judge_model(p: dict, fo: dict) -> tuple:
    """I1 on one field (PURE): `model` == the oracle's SetModel id AND `body` == its texture stem. `body` null with the
    model right is "not reached: cannot judge" (an unnamed texture -- a loose-FBX or CustomModelField body), never a pass."""
    miss = _no_oracle(fo)
    if miss:
        return False, miss
    detail = f"{_show(p, 'model')} {_show(p, 'body')} (oracle {fo.get('model')} / {fo.get('body')!r})"
    model_ok = _int(p.get("model")) is not None and _int(p.get("model")) == fo.get("model")
    if model_ok and "body" in p and p.get("body") is None:
        return False, f"not reached: cannot judge the body -- `body` null with the model right ({detail})"
    ok = model_ok and fo.get("body") is not None and p.get("body") == fo.get("body")
    return ok, detail


def judge_geo(p: dict, fo: dict) -> tuple:
    """I2 on one field (PURE)."""
    miss = _no_oracle(fo)
    if miss:
        return False, miss
    return (fo.get("geo") is not None and p.get("geo") == fo.get("geo"),
            f"{_show(p, 'geo')} (oracle {fo.get('geo')!r})")


def judge_eye(p: dict, fo: dict) -> tuple:
    """I4 on one field (PURE): `eye` == -4 x the oracle's eye byte."""
    miss = _no_oracle(fo)
    if miss:
        return False, miss
    if fo.get("eye") is None:
        return False, "not reached: no oracle eye for this field"
    want = BW.eye_of(fo["eye"])
    return _int(p.get("eye")) == want, f"{_show(p, 'eye')} (oracle -4 x {fo['eye']} = {want})"


def judge_ids(p: dict, fo: dict) -> tuple:
    """I9 on one field (PURE): sid == uid == the oracle's controlled entry."""
    miss = _no_oracle(fo)
    if miss:
        return False, miss
    if fo.get("sid") is None or fo.get("uid") is None:
        return False, "not reached: no oracle entry for this field"
    sid, uid = _int(p.get("sid")), _int(p.get("uid"))
    ok = sid is not None and sid == uid == fo["sid"] == fo["uid"]
    return ok, f"{_show(p, 'sid')} {_show(p, 'uid')} (oracle entry {fo['sid']}, uid {fo['uid']})"


def judge_rest_folder(p: dict, fo: dict) -> tuple:
    """I3 (PURE): at rest, anim an int and not 0, `anim_geo` == the oracle GEO, `clip_playing` is True."""
    miss = _no_oracle(fo)
    if miss:
        return False, miss
    anim = _int(p.get("anim"))
    ok = anim not in (None, 0) and fo.get("geo") is not None and p.get("anim_geo") == fo["geo"] \
        and p.get("clip_playing") is True
    return ok, (f"{_show(p, 'anim')} {_show(p, 'anim_geo')} {_show(p, 'clip_playing')} (oracle geo {fo.get('geo')!r}"
                + ("; anim 0 is ANH_MAIN_F0_STN_B -- never judged" if anim == 0 else "") + ")")


def moves(samples: list, *, gap: int = TICK_GAP) -> list:
    """The moves in ``samples`` COUNTED IN FIELD TICKS (PURE): each a list of the indices of the publishes that MOVED from
    the one before -- a field tick ran. The engine moves the player only on its 30 Hz ticks, so at ~60 fps every other
    publish shows the same position: such a still publish between two ticks is a render frame with no tick, collapsed
    here. More than ``gap`` still publishes in a row end a move."""
    out, ticks, still = [], [], 0
    for i in range(1, len(samples)):
        if _moved(samples[i - 1], samples[i]):
            if ticks and still > gap:
                out.append(ticks)
                ticks = []
            ticks.append(i)
            still = 0
        elif ticks:
            still += 1
    if ticks:
        out.append(ticks)
    return out


def moving_middle(samples: list, *, gap: int = TICK_GAP) -> list:
    """The MIDDLE of the move in ``samples`` (PURE), judged per TICK: the move with the most ticks (the first on a tie),
    without its first STEADY_TICKS ticks (the hold taking) and its last TAIL_TICKS (the release's coast) -- then EVERY
    publish from the middle's first tick to its last, the tickless frames between included (they must read the loco
    anim too). [] when no move has more than STEADY_TICKS + TAIL_TICKS ticks."""
    runs = moves(samples, gap=gap)
    best = max(runs, key=len) if runs else []
    if len(best) <= STEADY_TICKS + TAIL_TICKS:
        return []
    mid = best[STEADY_TICKS:len(best) - TAIL_TICKS]
    return [samples[i] for i in range(mid[0], mid[-1] + 1)]


def judge_walk(samples: list, fo: dict) -> tuple:
    """I5's MOVING half (PURE): every publish of the move's middle (ticks and the tickless frames between) reads the walk
    OR run id (never guessed which), its clip playing (`clip_playing` true) and folding to the GEO (`anim_geo`)."""
    miss = _no_oracle(fo)
    if miss:
        return False, miss
    loco = {fo.get("walk"), fo.get("run")} - {None}
    mid = moving_middle(samples)
    if not mid:
        runs = moves(samples)
        return False, (f"no move of {STEADY_TICKS + TAIL_TICKS + 1}+ field ticks ({len(samples)} samples; moves of "
                       f"{[len(r) for r in runs]} ticks)")
    ticks = sum(1 for a, b in zip(mid, mid[1:]) if _moved(a, b)) + 1
    seen = sorted({_show(_player(s), "anim") for s in mid})
    bad = [s for s in mid if _int(_player(s).get("anim")) not in loco or _player(s).get("clip_playing") is not True
           or _player(s).get("anim_geo") != fo.get("geo")]
    which = sorted({"walk" if _player(s).get("anim") == fo.get("walk") else "run" for s in mid if s not in bad})
    p0 = _player(bad[0]) if bad else {}
    return not bad and bool(loco), (f"{len(mid)} mid-move publishes over {ticks} ticks, anims {seen} (oracle walk "
                                    f"{fo.get('walk')} / run {fo.get('run')}: {which or 'neither'})"
                                    + (f"; first bad: {_show(p0, 'anim')} {_show(p0, 'clip_playing')} "
                                       f"{_show(p0, 'anim_geo')}" if bad else ""))


def judge_rest(samples: list, fo: dict) -> tuple:
    """I5's REST half (PURE): the LAST publish of the rest window, the player still over the last REST_STILL publishes,
    reads the stand id and its clip's NAME. The sleep clip is the known one, never a pass."""
    miss = _no_oracle(fo)
    if miss:
        return False, miss
    if len(samples) < REST_STILL:
        return False, f"only {len(samples)} rest publishes"
    tail = samples[-REST_STILL:]
    still = not any(_moved(a, b) for a, b in zip(tail, tail[1:]))
    p = _player(tail[-1])
    anim = _int(p.get("anim"))
    want_clip = (fo.get("clips") or {}).get("idle")
    if anim is not None and anim == fo.get("inactive") and anim != fo.get("idle"):
        return False, (f"anim {anim}: the known SLEEP clip (CheckSleep: the idle timer ran out) -- not a pass for the stand "
                       f"id {fo.get('idle')}")
    ok = still and anim == fo.get("idle") and want_clip is not None and p.get("clip") == want_clip
    return ok, (f"{_show(p, 'anim')} {_show(p, 'clip')} still={still} (oracle stand {fo.get('idle')} {want_clip!r})")


def _ghost_tuple(x):
    """``netsync.dress.ghost``'s (model, geo, clip, rig) -- the body the current ghost was built for, and its clip."""
    d = _dress(x)
    gh = d.get("ghost") if isinstance(d, dict) else None
    return tuple(gh.get(k) for k in ("model", "geo", "clip", "rig")) if isinstance(gh, dict) else None


def judge_ghost(samples: list, *, hold: int = GHOST_HOLD) -> tuple:
    """I7 (PURE): on the LAST sample where the player's anim AND the ghost's (model, geo, clip, rig) have held ``hold``+
    publishes, on FieldHUD, the selftest role forced and `session.ghost` true, the ghost is compared -- every value
    non-null on both sides, then model, geo and clip equal to the player's, rig -1, playing true, body equal to the
    player's (both bodies null: "not reached: cannot judge" -- an unnamed texture). The two skews it waits out: DriveGhost
    runs from another MonoBehaviour (its clip one frame behind the player's), and a re-dress requested off FieldHUD lands
    a frame after the HUD returns while DriveGhost already plays the new rig's clips (the old body with the new clip)."""
    if not samples:
        return False, "no publishes"
    if "anim" not in _player(samples[-1]) or _dress(samples[-1]) is None:
        return False, (f"{_show(_player(samples[-1]), 'anim')}, netsync.dress "
                       f"{'ABSENT' if _dress(samples[-1]) is None else 'present'} -- an engine before s138")
    pick, run, prev = None, 0, _ABSENT
    for s in samples:
        r = _raw(s)
        p = _player(s)
        anim = p.get("anim", _ABSENT)
        key = (anim, _ghost_tuple(s))
        run = run + 1 if anim is not _ABSENT and anim is not None and key == prev else 1
        prev = key
        ns = r.get("netsync") if isinstance(r.get("netsync"), dict) else {}
        sess = ns.get("session") if isinstance(ns.get("session"), dict) else {}
        if (run >= hold and r.get("ui_state") == "FieldHUD" and ns.get("selftest") is True and ns.get("forced") is True
                and sess.get("ghost") is True):
            pick = s
    if pick is None:
        last = _raw(samples[-1]) if samples else {}
        ns = last.get("netsync") if isinstance(last.get("netsync"), dict) else {}
        return False, (f"no publish with the player's anim held {hold}+ on FieldHUD, the role forced and session.ghost "
                       f"true (last: ui {last.get('ui_state')!r}, forced {ns.get('forced')!r}, session.ghost "
                       f"{(ns.get('session') or {}).get('ghost') if isinstance(ns.get('session'), dict) else 'ABSENT'!r})")
    d = _dress(pick)
    if d is None or not isinstance(d.get("ghost"), dict):
        return False, "netsync.dress.ghost ABSENT -- an engine before s138"
    gh, p = d["ghost"], _player(pick)
    nonnull = (_int(gh.get("model")) not in (None, -1) and gh.get("geo") is not None and gh.get("clip") is not None
               and _int(p.get("model")) is not None and p.get("geo") is not None and p.get("clip") is not None)
    detail = (f"ghost {cb.pick(gh, *S138_GHOST_KEYS)} vs player model {p.get('model')!r} geo {p.get('geo')!r} clip "
              f"{p.get('clip')!r} body {p.get('body')!r}")
    if not nonnull:
        return False, detail + " (a null on one side: nothing to compare)"
    same_but_body = (gh.get("model") == p.get("model") and gh.get("geo") == p.get("geo") and gh.get("clip") == p.get("clip")
                     and _int(gh.get("rig")) == BW.RIG_NONE and gh.get("playing") is True)
    if same_but_body and gh.get("body") is None and p.get("body") is None:
        return False, f"not reached: cannot judge the body -- both bodies null ({detail})"
    same = same_but_body and p.get("body") is not None and gh.get("body") == p.get("body")
    return same, detail


def judge_party(d: dict | None, want, *, why: str = "") -> tuple:
    """I8 (PURE): `dress.party` 4 ints, party[0] == 0, the seated members (>= 0) sorted == ``want`` (None: "not reached:
    no party oracle", ``why`` naming it). -2 (unreadable) is no seat."""
    if d is None or "party" not in d:
        return False, "netsync.dress.party ABSENT -- an engine before s138"
    party = d.get("party")
    if not isinstance(party, list) or len(party) != 4 or any(_int(v) is None for v in party):
        return False, f"party {party!r}: not 4 ints"
    if want is None:
        return False, f"not reached: no party oracle{f' ({why})' if why else ''} -- party {party}"
    seated = sorted(v for v in party if v >= 0)
    unreadable = [i for i, v in enumerate(party) if v == BW.PARTY_UNREADABLE]
    ok = party[0] == 0 and seated == sorted(want)
    return ok, (f"party {party} (seated {seated}; oracle {sorted(want)})"
                + (f"; slots {unreadable} UNREADABLE (-2: the read threw)" if unreadable else ""))


def judge_objects(x, fo: dict) -> tuple:
    """I6 (PURE): the listed actors' models -- >= 2, every entry with an int `model`, each == its sid's oracle SetModel id,
    none the player's 98."""
    miss = _no_oracle(fo)
    if miss:
        return False, miss
    objs = _raw(x).get("objects", _ABSENT)
    if objs is _ABSENT:
        return False, "objects ABSENT (an engine before s89)"
    if not isinstance(objs, list):
        return False, "objects null (off a field, or the walk failed)"
    if len(objs) < 2:
        return False, f"only {len(objs)} listed actor(s): an empty list proves nothing"
    missing = [o.get("uid") for o in objs if not isinstance(o, dict) or _int(o.get("model")) is None]
    if missing:
        return False, f"actors without an int `model`: uids {missing} (an engine before s138 lists none)"
    npcs = fo.get("npcs") or {}
    rows = [(o.get("uid"), o.get("sid"), o.get("model")) for o in objs]
    wrong = [r for r in rows if npcs.get(r[1]) != r[2]]
    zid = [r for r in rows if r[2] == (fo.get("model") or 98)]
    return not wrong and not zid, (f"(uid, sid, model) {rows}; oracle by sid {npcs}"
                                   + (f"; NOT the oracle's: {wrong}" if wrong else "")
                                   + (f"; the player's model: {zid}" if zid else ""))


# ---- [ff9mapkit netsync s139] leg G's pure judges -------------------------------------------------------------------
#: the `selfdress` levers all OFF, as the bench tracks them and the engine publishes them (`ghost.bench_mask`, `empty_mask`,
#: `rule`, `wire`, `wire_anim`)
LEVERS_OFF = {"mask": -1, "empty": -1, "rule": None, "wire": -1, "wire_anim": -1}


def published_levers(x) -> dict | None:
    """(PURE) The `selfdress` levers the engine PUBLISHES as set (`netsync.dress.ghost`'s s139 keys), in the bench's
    shape; None on an engine before s139 (no `bench_mask`)."""
    d = _dress(x)
    gh = d.get("ghost") if isinstance(d, dict) else None
    if not isinstance(gh, dict) or "bench_mask" not in gh:
        return None
    return {"mask": gh.get("bench_mask"), "empty": gh.get("empty_mask"), "rule": gh.get("rule"), "wire": gh.get("wire"),
            "wire_anim": gh.get("wire_anim")}


#: the lever S138-R holds into the reset on an s139+ engine: `rule s139` is INERT (the s139 rule is the site's own), so
#: holding it changes nothing a later read judges -- and HarnessReleaseDress logs only when a lever was held
HOLD_INTO_RESET = ("rule", "s139")
#: the line the harness release logs for it (NetSyncBattle.HarnessReleaseBench -> HarnessReleaseDress's cause)
RELEASE_LINE = "selfdress levers released (released with the harness)"


def judge_released(x) -> tuple:
    """S138-R's s139 half (PURE): after `reset` every selfdress lever reads OFF -- `bench_mask`, `empty_mask`, `wire`,
    `wire_anim` -1 and `rule` null (the getters publish the levers RAW, in every role, so the read is a witness, not a
    role gate's rest value). Red on any held lever and on an engine that publishes none."""
    got = published_levers(x)
    if got is None:
        return False, "the selfdress levers after the reset: not published (no `ghost.bench_mask`)"
    return got == LEVERS_OFF, f"the selfdress levers after the reset {got} (want every one off: {LEVERS_OFF})"


def hold_into_reset(g, ctx: dict) -> tuple:
    """(held, why): on an s139+ engine (the probe's stage) send :data:`HOLD_INTO_RESET` and see it PUBLISHED (the lever
    held: the reset must then release it) -> (True, None); before s139 nothing exists to hold -> (False, None); a refusal
    or a lever that never publishes -> (False, why)."""
    stage = ctx.get("stage")
    if stage is None or stage < 139:
        return False, None
    ok, why = cb.try_ns(g, "selfdress", *HOLD_INTO_RESET)
    if not ok:
        return False, f"`selfdress {' '.join(HOLD_INTO_RESET)}` refused: {why}"
    st = cb.poll(g, lambda s: (published_levers(s) or {}).get("rule") == HOLD_INTO_RESET[1], 5.0,
                 f"`selfdress {' '.join(HOLD_INTO_RESET)}` published")
    if st is None:
        return False, f"`selfdress {' '.join(HOLD_INTO_RESET)}` never published (levers {published_levers(g.state)})"
    return True, None


def want_mode(levers: dict, ghost_as) -> str:
    """(PURE) The `ghost.mode` the levers imply: "bench:auto" under a `ghost` lever (it FORCES mode auto -- audit 2.2
    amendment 1), else "ini:" + the ini's trimmed GhostAs."""
    return BW.DRESS_MODE_BENCH if int(levers["mask"]) >= 0 else BW.DRESS_MODE_INI + (ghost_as or "").strip()


def want_ghost(x, levers: dict, ghost_as) -> dict | None:
    """(PURE) What THE s139 SELFTEST SITE makes the mirror wear and play on this sample -- battlewire.selftest_dress, the
    site's twin (its rig rows pinned to the census), on the sample's own player model / anim and its LIVE party
    (`netsync.dress.party`), the ini's GhostAs and the GuestSlots-0 pin, the bench's ``levers`` (the `rule` lever is never
    applied: the expectation is always the s139 rule, so the calibration lever's red shows). None when the player's model
    or anim, or the party, is unread."""
    p, d = _player(x), _dress(x)
    model, anim = _int(p.get("model")), _int(p.get("anim"))
    party = d.get("party") if isinstance(d, dict) else None
    if model is None or anim is None or not isinstance(party, list) or len(party) != 4:
        return None
    return BW.selftest_dress(ghost_as=ghost_as or "", guest_slots=0, me_model=model, me_anim=anim, party=party,
                             role="selftest", selftest_role=True, bench_mask=int(levers["mask"]),
                             empty_mask=int(levers["empty"]), rule=None, wire=int(levers["wire"]),
                             wire_anim=int(levers.get("wire_anim", -1)))


def _held_pick(samples: list, levers: dict, hold: int):
    """The LAST sample where the player's anim AND the ghost's (model, geo, clip, rig) have held ``hold``+ publishes -- on
    FieldHUD, the selftest role forced, `session.ghost` true and the PUBLISHED levers equal to ``levers`` (the ops
    landed). None when there is none."""
    pick, run, prev = None, 0, _ABSENT
    for s in samples:
        r = _raw(s)
        anim = _player(s).get("anim", _ABSENT)
        key = (anim, _ghost_tuple(s))
        run = run + 1 if anim is not _ABSENT and anim is not None and key == prev else 1
        prev = key
        ns = r.get("netsync") if isinstance(r.get("netsync"), dict) else {}
        sess = ns.get("session") if isinstance(ns.get("session"), dict) else {}
        if (run >= hold and r.get("ui_state") == "FieldHUD" and ns.get("selftest") is True and ns.get("forced") is True
                and sess.get("ghost") is True and published_levers(s) == dict(levers)):
            pick = s
    return pick


def _no_pick_why(samples: list, levers: dict, hold: int) -> str:
    last = _raw(samples[-1])
    ns = last.get("netsync") if isinstance(last.get("netsync"), dict) else {}
    return (f"no publish with the ghost held {hold}+ on FieldHUD, the role forced, session.ghost true and the levers "
            f"{levers} published (last: levers {published_levers(samples[-1])}, ui {last.get('ui_state')!r}, forced "
            f"{ns.get('forced')!r})")


def _worn_verdict(pick, *, levers: dict, ghost_as, models: dict, clips: dict, moving: bool = False) -> tuple:
    """One sample against :func:`want_ghost`: (ok, detail) -- model, rig, GEO and texture stem off the INSTALL, the clip
    NAME of the twin's anim (playing, where that clip lives in the worn folder), and `ghost.mode` the one the levers imply.
    A ghost body null with everything else right reads "not reached: cannot judge"."""
    want = want_ghost(pick, levers, ghost_as)
    p, gh = _player(pick), _dress(pick)["ghost"]
    if want is None:
        return False, f"the player's model / anim or the party unread (player {cb.pick(p, 'model', 'anim')})"
    m = want["model"]
    facts = models.get(m) or {}
    if not facts.get("geo") or not facts.get("body"):
        return False, f"not reached: no install oracle for model {m} (the twin's answer: {BW.rig_name(want['rig'])})"
    want_clip = clips.get(want["anim"])
    judged_play = want_clip is not None and BW.folder_of(want_clip) == facts["geo"]
    mode, wmode = gh.get("mode"), want_mode(levers, ghost_as)
    detail = (f"ghost {cb.pick(gh, *S138_GHOST_KEYS)} mode {mode!r} vs the twin's "
              f"{BW.rig_name(want['rig']) or 'undressed'}: model {m} rig {want['rig']} geo {facts['geo']} body "
              f"{facts['body']!r} clip {want_clip!r} mode {wmode!r} (player {p.get('model')}/{p.get('anim')}, party "
              f"{_dress(pick).get('party')}, levers {levers}, GhostAs {ghost_as!r})"
              + ("" if judged_play else "; `playing` not judged: that clip is not in the worn model's own GEO folder"))
    same_but_body = (_int(gh.get("model")) == m and _int(gh.get("rig")) == want["rig"] and gh.get("geo") == facts["geo"]
                     and want_clip is not None and gh.get("clip") == want_clip
                     and (not judged_play or gh.get("playing") is True) and mode == wmode)
    if same_but_body and gh.get("body") is None:
        return False, f"not reached: cannot judge the body -- `ghost.body` null ({detail})"
    return same_but_body and gh.get("body") == facts["body"], detail


def judge_worn(samples: list, *, levers: dict, ghost_as, models: dict, clips: dict, hold: int = GHOST_HOLD) -> tuple:
    """Leg G (PURE): on the LAST publish where the player's anim AND the ghost's (model, geo, clip, rig) have held ``hold``+
    publishes -- on FieldHUD, the selftest role forced, `session.ghost` true and the PUBLISHED levers equal to ``levers``
    (the ops landed) -- the ghost wears what :func:`want_ghost` computes: its model and rig, the GEO and texture stem the
    INSTALL gives that model (``models``: the oracle's {model: {geo, body}} -- never the engine's tables), and the clip
    NAME of the twin's anim (``clips``: the kit's copy of the open-source AnimationDB), playing -- judged only when that
    clip lives in the worn model's own GEO folder (EnsureGhost loads the worn folder alone: a foreign clip cannot play) --
    and `ghost.mode` the one the levers imply (:func:`want_mode`: a `ghost` lever FORCES auto, so 'ini:auto' under a mask is
    red even where it dresses the same). A ghost body null with everything else right reads "not reached: cannot judge"."""
    if not samples:
        return False, "no publishes"
    d = _dress(samples[-1])
    if d is None or not isinstance(d.get("ghost"), dict) or "mode" not in d["ghost"]:
        return False, "netsync.dress.ghost.mode ABSENT -- an engine before s139"
    pick = _held_pick(samples, levers, hold)
    if pick is None:
        return False, _no_pick_why(samples, levers, hold)
    return _worn_verdict(pick, levers=levers, ghost_as=ghost_as, models=models, clips=clips)


def judge_worn_moving(samples: list, *, levers: dict, ghost_as, models: dict, clips: dict) -> tuple:
    """G3m (PURE): the ghost while the player MOVES -- the move's middle (:func:`moving_middle`: per tick, the tickless
    frames included), every publish whose player anim held over the publish before it (DriveGhost trails the player by one
    frame: a walk -> run switch is not judged on its first frame), with the levers published as set, on FieldHUD, the
    selftest role forced: each one :func:`_worn_verdict` -- the twin's clip for THAT anim (25 -> the dressed rig's walk, 38
    its run), playing, on the dressed body. Red on any judged publish that is not; "not reached" when no move has a
    middle."""
    if not samples:
        return False, "no publishes"
    d = _dress(samples[-1])
    if d is None or not isinstance(d.get("ghost"), dict) or "mode" not in d["ghost"]:
        return False, "netsync.dress.ghost.mode ABSENT -- an engine before s139"
    mid = moving_middle(samples)
    if not mid:
        runs = moves(samples)
        return False, (f"not reached: no move of {STEADY_TICKS + TAIL_TICKS + 1}+ field ticks ({len(samples)} samples; "
                       f"moves of {[len(r) for r in runs]} ticks)")
    judged, bad, anims, worn = 0, None, set(), set()
    for a, b in zip(mid, mid[1:]):
        r = _raw(b)
        ns = r.get("netsync") if isinstance(r.get("netsync"), dict) else {}
        sess = ns.get("session") if isinstance(ns.get("session"), dict) else {}
        if (_player(a).get("anim") != _player(b).get("anim") or r.get("ui_state") != "FieldHUD"
                or ns.get("forced") is not True or sess.get("ghost") is not True or published_levers(b) != dict(levers)):
            continue
        judged += 1
        anims.add(_player(b).get("anim"))
        worn.add(str(((_dress(b) or {}).get("ghost") or {}).get("clip")))
        ok, why = _worn_verdict(b, levers=levers, ghost_as=ghost_as, models=models, clips=clips)
        if not ok and bad is None:
            bad = why
    if not judged:
        return False, f"not reached: no mid-move publish held its anim with the levers {levers} published ({len(mid)} mid)"
    return bad is None, (f"{judged} mid-move publishes judged, player anims {sorted(a for a in anims if a is not None)}, "
                         f"ghost clips {sorted(worn)}" + (f"; first bad: {bad}" if bad else ""))


def judge_rest_mask(samples: list, *, levers: dict, tree, garnet_hair, hold: int = GHOST_HOLD) -> tuple:
    """G8's visibility half (PURE): on the held pick (:func:`_held_pick`), the ghost's `shown_mask` == its `rest_mask` (the
    rest mask APPLIED), with a hide among them (else nothing is proven: "not reached: cannot judge"), and `hidden` -- the
    renderers disabled now -- == the install prefab's field-mode hides by ModelFactory's own rule (BW.field_hides over
    ``tree``: {geo, transforms, renderers} read off p0data; ``garnet_hair``: the ini's [Graphics] GarnetHair; the sample's
    own published scenario counter), and `rest_mask` == that rule's mask. ``tree`` None: "not reached"."""
    if not samples:
        return False, "no publishes"
    d = _dress(samples[-1])
    gh0 = d.get("ghost") if isinstance(d, dict) else None
    if not isinstance(gh0, dict) or "rest_mask" not in gh0:
        return False, "netsync.dress.ghost.rest_mask ABSENT -- an engine before s139's visibility keys"
    if not tree:
        return False, "not reached: no prefab tree for the rest mask's oracle"
    pick = _held_pick(samples, levers, hold)
    if pick is None:
        return False, _no_pick_why(samples, levers, hold)
    return rest_mask_verdict(_dress(pick)["ghost"], _int(_raw(pick).get("scenario")), tree, garnet_hair)


def rest_mask_verdict(gh: dict, scenario, tree, garnet_hair) -> tuple:
    """(PURE) THE REST MASK on one picked ghost record ``gh`` (`netsync.dress.ghost`): `shown_mask` == `rest_mask` (the rest
    mask APPLIED) == the install prefab's rule mask, with a hide among them (else "not reached: cannot judge"), and `hidden`
    == the prefab's field-mode hides by ModelFactory's own rule (BW.field_hides over ``tree`` -- {geo, transforms,
    renderers} read off p0data -- with ``garnet_hair``, the ini's [Graphics] GarnetHair, and ``scenario``, the sample's own
    published scenario counter). Shared by G8 (the selftest site) and G9e (the host's TRANSPORT site, coop_dress_wire.py)."""
    if not isinstance(gh, dict) or "rest_mask" not in gh:
        return False, "netsync.dress.ghost.rest_mask ABSENT -- an engine before s139's visibility keys"
    if not tree:
        return False, "not reached: no prefab tree for the rest mask's oracle"
    if scenario is None:
        return False, "not reached: no published scenario counter (the hair rule's input)"
    want_hidden = BW.field_hides(tree["geo"], tree["transforms"], tree["renderers"], garnet_hair=garnet_hair or 0,
                                 scenario=scenario)
    want_rest = BW.visibility_mask(tree["renderers"], want_hidden)
    rest, shown, hidden = _int(gh.get("rest_mask")), _int(gh.get("shown_mask")), gh.get("hidden")
    detail = (f"rest_mask {rest} shown_mask {shown} hidden {hidden!r} vs the prefab's rule: rest {want_rest} hidden "
              f"{want_hidden} (scenario {scenario}, GarnetHair {garnet_hair!r}, {len(tree['renderers'])} renderers)")
    if not want_hidden:
        return False, f"not reached: cannot judge -- the rule hides nothing on this body ({detail})"
    ok = (rest is not None and rest == shown == want_rest and isinstance(hidden, list)
          and sorted(hidden) == sorted(want_hidden))
    return ok, detail


def judge_baseline(samples: list, *, ghost_as, models: dict, clips: dict) -> tuple:
    """G0 / G5 (PURE): every lever OFF, `ghost.mode` == "ini:" + the ini's GhostAs as the bench read it offline (trimmed),
    and the ghost what the s139 rule makes of it under the pin (:func:`judge_worn`)."""
    ok, why = judge_worn(samples, levers=LEVERS_OFF, ghost_as=ghost_as, models=models, clips=clips)
    d = _dress(samples[-1]) if samples else None
    gh = d.get("ghost") if isinstance(d, dict) else None
    mode = gh.get("mode", "ABSENT") if isinstance(gh, dict) else "ABSENT"
    want_mode_ = BW.DRESS_MODE_INI + (ghost_as or "").strip()
    return ok and mode == want_mode_, f"mode {mode!r} (want {want_mode_!r}); {why}"


def judge_section_line(lines: list, ghost_as) -> tuple:
    """G3d's second half (PURE over Memoria.log): the proof block's LATEST section-8 line carries the twin's body for the
    ini's GhostAs under the forced selftest's GuestSlots pin 0 (battlewire.host_dress_section) -- "DC 00 FF (model 220,
    charId 255)" for auto (owner D2), "00 00 FF (model 0, charId 255)" for none. The producer's bytes as this machine would
    host them (the selftest role has no socket: G9, the duo relay tap, is the wire's own witness)."""
    want = BW.dress_section_text(BW.host_dress_section(ghost_as or "", 0, "selftest", True, None))
    hits = [ln for ln in lines if BW.PROOF_DRESS_SECTION in ln]
    if not hits:
        return False, f"no '{BW.PROOF_DRESS_SECTION.strip()}' line in Memoria.log (want {want!r})"
    got = hits[-1].split(BW.PROOF_DRESS_SECTION, 1)[1].strip()
    return got == want, f"section 8 {got!r} (the twin's {want!r} for GhostAs {ghost_as!r} under the pin)"


def judge_codec(d: dict | None, lines: list) -> tuple:
    """G4 (PURE): `netsync.dress.codec` == "ok" AND the proof block's line reads OK with the engine's row count."""
    if d is None or "codec" not in d:
        return False, "netsync.dress.codec ABSENT -- an engine before s139"
    want = BW.proof_ok(BW.PROOF_DRESS, BW.DRESS_SELFTEST_ROWS)
    hits = [ln for ln in lines if BW.PROOF_DRESS in ln]
    line = hits[-1].split("[NetSync] ", 1)[-1].strip() if hits else None
    ok = d.get("codec") == BW.DRESS_CODEC_OK and line == want
    return ok, f"codec {d.get('codec')!r}; proof line {line!r} (want {want!r})"


def judge_idle_frames(d: dict | None, oracle) -> tuple:
    """G6 (PURE): `rig_idle_frames` -- nine ints -- equals the oracle the kit's clip reader read off the install (None:
    "not reached")."""
    if d is None or "rig_idle_frames" not in d:
        return False, "netsync.dress.rig_idle_frames ABSENT -- an engine before s139"
    got = d.get("rig_idle_frames")
    if oracle is None:
        return False, f"not reached: no idle-frame oracle (published {got})"
    if not isinstance(got, list) or len(got) != BW.RIG_ROW_COUNT or any(_int(v) is None for v in got):
        return False, f"rig_idle_frames {got!r}: not {BW.RIG_ROW_COUNT} ints"
    bad = [f"{BW.RIG_NAMES[i]} {got[i]} != {oracle[i]}" for i in range(BW.RIG_ROW_COUNT) if got[i] != oracle[i]]
    return not bad, f"rig_idle_frames {got} (oracle {list(oracle)})" + (f"; {bad}" if bad else "")


def first_main_slot(party) -> int | None:
    """(PURE) s1: the first slot >= 1 holding a main (CharacterId 0-7) -- what `ghost 1<<s1` names; None when none does."""
    if not isinstance(party, list):
        return None
    return next((i for i in range(1, min(4, len(party))) if _int(party[i]) is not None and 0 <= party[i] < BW.MAIN_RIG_COUNT),
                None)


# ================================================================================================ the offline oracle
_KIT = None


def _kit():
    """``ff9mapkit`` from THIS worktree (asserted), or raise naming where it resolved instead."""
    global _KIT
    if _KIT is not None:
        return _KIT
    pkg_root = cb.REPO / "ff9mapkit"
    if str(pkg_root) not in sys.path:
        sys.path.insert(0, str(pkg_root))
    import ff9mapkit                                       # noqa: E402 - path pinned above
    where = Path(getattr(ff9mapkit, "__file__", "") or ".").resolve()
    if not where.is_relative_to(pkg_root):
        raise RuntimeError(f"ff9mapkit resolved to {where}, not this worktree's {pkg_root}")
    _KIT = ff9mapkit
    return ff9mapkit


def eb_facts(data: bytes) -> dict:
    """A field script's CONTROLLED entry and its body, as the script itself sets them (PURE over the bytes; the kit's .eb
    reader): {sid, uid, model, eye, idle, walk, run, inactive, npcs {sid: model}, inits [(sid, uid)], players [sid],
    problems [...]}. The controlled entry is the LAST Main_Init-inited entry whose functions run DefinePlayerCharacter
    (control binds to the last one); uid 0 in InitObject is the sid; an operand that is an expression reads None."""
    _kit()
    from ff9mapkit.eb import disasm
    from ff9mapkit.eb.model import EbScript
    from ff9mapkit.playerswap import ANIM_OPS
    s = EbScript(data)
    out = {"sid": None, "uid": None, "model": None, "eye": None, "idle": None, "walk": None, "run": None,
           "inactive": None, "npcs": {}, "inits": [], "players": [], "problems": []}
    f0 = s.main.func_by_tag(0) if s.entries else None
    if f0 is None:
        out["problems"].append("no Main_Init")
        return out
    for ins in disasm.iter_code(s.data, f0.abs_start, f0.abs_end):
        if ins.op == OP_INIT_OBJECT:
            sid, uid = ins.imm(0), ins.imm(1)
            out["inits"].append((sid, sid if uid == 0 else uid))
    entries = {}
    for e in s.entries[1:]:
        if e.empty:
            continue
        facts = {"define": False}
        init = e.func_by_tag(0)
        for f in e.funcs:
            for ins in disasm.iter_code(s.data, f.abs_start, f.abs_end):
                if ins.op == OP_DEFINE_PLAYER:
                    facts["define"] = True
                if f is not init:
                    continue
                if ins.op == OP_SET_MODEL and "model" not in facts:
                    facts["model"], facts["eye"] = ins.imm(0), ins.imm(1)
                elif ins.op in ANIM_OPS and ANIM_OPS[ins.op] not in facts:
                    facts[ANIM_OPS[ins.op]] = ins.imm(0)
        entries[e.index] = facts
    inited = [sid for sid, _uid in out["inits"] if sid is not None]
    players = [sid for sid in inited if entries.get(sid, {}).get("define")]
    out["players"] = sorted(set(players))
    if not players:
        out["problems"].append("no Main_Init-inited entry runs DefinePlayerCharacter")
        return out
    sid = players[-1]
    uids = {uid for s_, uid in out["inits"] if s_ == sid}
    facts = entries[sid]
    out.update(sid=sid, uid=next(iter(uids)) if len(uids) == 1 else None, model=facts.get("model"),
               eye=facts.get("eye"), idle=facts.get("idle"), walk=facts.get("walk"), run=facts.get("run"),
               inactive=facts.get("inactive"))
    if len(uids) != 1:
        out["problems"].append(f"entry {sid} inited with uids {sorted(uids, key=str)}")
    for k in ("model", "eye", "idle", "walk", "run"):
        if out[k] is None:
            out["problems"].append(f"entry {sid}'s Init sets no immediate {k}")
    for n in sorted(set(inited) - {sid}):
        m = entries.get(n, {}).get("model")
        if m is not None:
            out["npcs"][n] = m
    return out


def _event_paths(game: Path, folders, evt: str) -> list:
    return [game.joinpath(f, *EVENT_DIR, EVT_LANG, f"{evt}.eb.bytes") for f in folders]


def kit_cache_missing(game: Path) -> list:
    """The :data:`KIT_CACHE_FILES` missing from the install's StreamingAssets -- each one the kit's readers would WRITE
    into the install on first use (the bench reads only: it never creates one)."""
    sa = Path(game) / "StreamingAssets"
    return [n for n in KIT_CACHE_FILES if not (sa / n).is_file()]


def field_eb(game: Path, fid: int, *, reg_name: str | None = None, install_ok: bool = True) -> tuple:
    """(bytes, where) of the `.eb` the engine loads for ``fid``: the highest-priority mod folder (FolderNames order) that
    ships its event, else -- a stock field -- the install's p0data (only when ``install_ok``: the kit's read caches into
    the install on a miss). (None, why) when neither has it."""
    _kit()
    from ff9mapkit import extract as X
    folders = X._mod_folders(game)
    names = [n for n in (X.ID_TO_EVT.get(int(fid)), f"EVT_{reg_name}" if reg_name else None,
                         f"EVT_TEST{int(fid)}") if n]
    for evt in dict.fromkeys(names):
        for p in _event_paths(game, folders, evt):
            if p.is_file():
                return p.read_bytes(), f"{p.relative_to(game)}"
    if int(fid) in X.ID_TO_EVT:
        if not install_ok:
            return None, (f"field {fid}'s `.eb` is only in the install's p0data, and the kit cache "
                          f"{KIT_CACHE_FILES} is missing from StreamingAssets (the kit would WRITE it into the install: "
                          f"run any ff9mapkit read once, by hand -- this bench never writes into the install)")
        data = X.extract_event_script(str(int(fid)), game=game, lang=EVT_LANG)
        if data:
            return data, f"p0data ({X.ID_TO_EVT[int(fid)]}, {EVT_LANG})"
    return None, f"no `.eb` for field {fid} ({names}) in {folders} nor the install's p0data"


def model_facts(game: Path, model: int) -> dict:
    """A model's GEO name and texture stems off the install (read_model), cross-checked with the kit's GEO table."""
    _kit()
    from ff9mapkit._modeldb import MODELS
    from ff9mapkit.models import extract as ME
    m = ME.read_model(str(int(model)), game=game)
    stems = sorted({BW.texture_stem(x.get("texture")) for x in m.get("materials", []) if x.get("texture")})
    geo = m.get("geo")
    return {"geo": geo if geo == MODELS.get(int(model)) else None, "geo_read": geo, "geo_table": MODELS.get(int(model)),
            "stems": stems, "body": stems[0] if len(stems) == 1 else None}


def dictionary_remaps(game: Path, folders, models, anims) -> list:
    """(PURE over the files) Every `3DModel` / `3DModelAnimation` line in a stacked mod folder's DictionaryPatch.txt that
    touches ``models`` / ``anims`` -- ``[(folder, line)]``. Stock Memoria applies them at launch (DataPatchers:
    ``3DModel <id> [<id> ...] <GEO>`` -> FF9BattleDB.GEO, ``3DModelAnimation <id> [<id> ...] <clip>`` -> AnimationDB),
    which the kit's tables do not see: a hit would turn I2 or I5 red on a correct engine."""
    models, anims = {int(m) for m in models if m is not None}, {int(a) for a in anims if a is not None}
    out = []
    for folder in folders:
        path = Path(game) / folder / "DictionaryPatch.txt"
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            tok = line.split()
            if len(tok) < 3 or tok[0] not in DICTIONARY_REMAP_VERBS:
                continue
            try:
                ids = {int(t) for t in tok[1:-1]}
            except ValueError:
                continue                                    # the engine skips a line it cannot parse too
            if ids & (models if tok[0] == "3DModel" else anims):
                out.append((folder, line.strip()))
    return out


def party_oracle(path: Path = PARTY_TOML) -> tuple:
    """(the seated CharacterIds the seed leaves, sorted, or None; why): the New-Game base + COOPPARTY's `[party] add`
    (resolved by the kit's content.party, CharacterOldIndex -> CharacterId)."""
    _kit()
    import tomllib
    from ff9mapkit.content import party as P
    try:
        doc = tomllib.loads(path.read_text(encoding="utf-8"))
        adds = [OLD_INDEX_TO_ID[P.resolve_member(n)] for n in (doc.get("party") or {}).get("add", [])]
    except (OSError, ValueError, KeyError) as err:
        return None, f"{path.name}: {err}"
    return sorted(set(NEW_GAME_BASE) | set(adds)), f"{path.name}: base {list(NEW_GAME_BASE)} + add {adds}"


def read_oracle(g, fields) -> tuple:
    """S138-OR, PER FIELD: ({"fields": {fid: {...eb_facts, src, geo, body, stems, clips, npc_geo}}, "party": [...] or
    None, "problems": {fid | "party" | "oracle": why}}, why). A field that reads clean is KEPT whatever else fails (one
    undeployed bench field never throws away another's oracle); a field whose read failed -- no `.eb`, no clean entry, a
    model the install and the table disagree on, a DictionaryPatch remap of its model or clips, the kit cache missing -- is
    left OUT of ``fields`` and named in ``problems``. S138-OR is red whenever ``problems`` is not empty."""
    game = Path(g.game_path)
    try:
        regs = g.registered_fields()[0]
    except (HarnessError, AttributeError, OSError):
        regs = {}
    out, why = {"fields": {}, "party": None, "problems": {}}, []
    probs = out["problems"]
    try:
        _kit()
        from ff9mapkit import extract as X
        from ff9mapkit._animdb_all import ANIMATIONS
        from ff9mapkit._modeldb import MODELS
        folders = X._mod_folders(game)
        install_ok = not kit_cache_missing(game)
        for fid in fields:
            try:
                data, src = field_eb(game, fid, reg_name=regs.get(fid), install_ok=install_ok)
                if data is None:
                    probs[fid] = src
                    continue
                fo = eb_facts(data)
                fo["src"] = src
                if fo["problems"] or fo["model"] is None:
                    probs[fid] = f"{src}: {fo['problems']}"
                    continue
                fo.update(model_facts(game, fo["model"]))
                fo["clips"] = {k: ANIMATIONS.get(fo[k]) for k in ("idle", "walk", "run", "inactive")
                               if fo.get(k) is not None}
                fo["npc_geo"] = {sid: MODELS.get(m) for sid, m in fo["npcs"].items()}
                if fo["geo"] is None or fo["body"] is None:
                    probs[fid] = (f"model {fo['model']} geo {fo['geo_read']!r} vs the table's {fo['geo_table']!r}, "
                                  f"stems {fo['stems']}")
                    continue
                remaps = dictionary_remaps(game, folders, [fo["model"], *fo["npcs"].values()],
                                           [fo.get(k) for k in ("idle", "walk", "run", "inactive")])
                if remaps:
                    probs[fid] = ("a DictionaryPatch remap touches its model or clips (stock Memoria applies it at "
                                  "launch; the kit's tables do not): " + "; ".join(f"{f}: {ln!r}" for f, ln in remaps))
                    continue
                out["fields"][fid] = fo
                why.append(f"{fid} <- {src}: entry {fo['sid']} uid {fo['uid']} SetModel({fo['model']}, {fo['eye']}) "
                           f"{fo['geo']} body {fo['body']!r} loco {fo['idle']}/{fo['walk']}/{fo['run']} inactive "
                           f"{fo['inactive']} npcs {fo['npcs']}")
            except Exception as err:         # noqa: BLE001 - one field that cannot be read is a named problem, never a crash
                probs[fid] = f"the oracle read raised {type(err).__name__}: {str(err)[:300]}"
        party, pwhy = party_oracle()
        out["party"] = party
        why.append(f"party {party} ({pwhy})")
        if party is None:
            probs["party"] = pwhy
    except Exception as err:                 # noqa: BLE001 - an oracle that cannot be read is a red row, never a crash
        probs["oracle"] = f"the oracle read raised {type(err).__name__}: {str(err)[:300]}"
    text = "; ".join([f"PROBLEM {k}: {v}" for k, v in probs.items()] + why)
    return out, text[:900]


def _oracle_extra(g, ctx: dict) -> None:
    """Each selected leg's own offline oracle (its `oracle_extra` hook), merged into ``ctx["oracle"]["extra"][leg]``."""
    oracle = ctx["oracle"]
    oracle.setdefault("extra", {})
    for leg in ctx["legs"]:
        hook = LEGS[leg].get("oracle_extra")
        if not hook:
            continue
        try:
            got, problems = globals()[hook](g, ctx)
        except Exception as err:             # noqa: BLE001 - a hook that raised is a named problem
            got, problems = None, {"hook": f"{hook} raised {type(err).__name__}: {str(err)[:200]}"}
        oracle["extra"][leg] = got
        oracle["problems"].update({f"{leg}.{k}": v for k, v in (problems or {}).items()})


# ================================================================================================ acting
def _ini_guard(g) -> tuple:
    enabled = cb.ini_value(g, "Netsync", "Enabled")
    role = cb.ini_value(g, "Netsync", "Role")
    ghost = cb.ini_value(g, "Netsync", "GhostAs")
    ok_e = enabled is None or enabled.strip() == "0"
    ok_g = ghost is None or ghost.strip().lower() in GHOST_AS_OK
    why = (f"[Netsync] Enabled = {enabled!r} (Role = {role!r}), GhostAs = {ghost!r}"
           + ("" if ok_e else " -- the selftest role is refused on a live-configured install: set Enabled = 0 BY HAND "
                              "(this bench never writes Memoria.ini) and relaunch")
           + ("" if ok_g else f" -- a NAMED GhostAs dresses the selftest mirror whatever the slots (I7 compares an "
                              f"undressed one): set it to one of {GHOST_AS_OK} BY HAND"))
    return ok_e and ok_g, why


def _archive_logs(g, tag: str) -> str:
    """BOTH logs into the run's artifact dir NOW (design 6.1): Memoria.log and Unity's output_log.txt."""
    out = [cb.archive_log(g, tag)]
    try:
        src = g.unity_log()
        dest_dir = getattr(g, "scenario_dir", None) or g.run_dir
        if src is not None and dest_dir is not None:
            dest = Path(dest_dir) / f"output_log-{tag}.txt"
            shutil.copy2(src, dest)
            out.append(str(dest))
    except (OSError, AttributeError) as err:
        out.append(f"output_log archive failed: {err}")
    return "; ".join(out)


def _setup(g, ctx: dict) -> tuple:
    """newgame -> the stock field at STOCK_ENTRANCE (always: `warp <id> -1` would keep the last field's entrance) ->
    encounters off -> the forced selftest role (cb.setup's order, without its seed: the seed is a PHASE here -- s139's G3a
    needs the empty slot before it). (ok, why)."""
    cb.provenance(g)
    g.note(f"R3 s138-s141: the guest's own field model, legs {ctx['legs']}"
           + (f" -- CALIBRATION ({ctx['cal_mode']})" if ctx["calibrate"] else ""))
    g.newgame()
    g.warp(ctx["stock"], entrance=STOCK_ENTRANCE)
    try:
        g.no_encounters(True)
    except (HarnessError, AttributeError) as err:
        g.note(f"noencounter refused ({str(err)[:120]}) -- a random battle may interrupt the walk")
    g.wait_frames(SETTLE_FRAMES)
    ok, why = cb.try_ns(g, "selftest", 1)
    ns = g.state.netsync or {}
    good = ok and bool(ns.get("selftest")) and bool(ns.get("forced"))
    return good, (why or f"selftest={ns.get('selftest')!r} forced={ns.get('forced')!r} role={ns.get('role')!r}")


def _settle(g, field: int):
    """The field up with the player free (or None): what every read on a field waits for."""
    return cb.poll(g, lambda s: free_on(s, field), SETTLE_S, f"field {field} with control")


def _read_field(g, ctx: dict, field: int) -> None:
    st = _settle(g, field)
    if st is None:
        ctx["unreached"][field] = f"field {field} never came up with control (field {g.state.field_id})"
        return
    ctx["reads"][field] = dict(_player(st))
    ctx["states"][field] = st


def _taken(s) -> str:
    """Why a probe hold's sample says the hold was TAKEN OVER (the field left, control lost, a fade) -- for the note."""
    r = _raw(s)
    return (f"field {(r.get('field') or {}).get('id')!r}, ui {r.get('ui_state')!r}, control "
            f"{(r.get('player') or {}).get('control')!r}, fading {r.get('fading', False)!r} at frame {r.get('frame')!r}")


def _walk_probe(g, field: int) -> dict:
    """I5's move: hold one direction WALK_TICKS field ticks -- sized to frames at the MEASURED render rate -- (each in turn
    until one moves), watched publish by publish, then walk back the same frames. A sample that is not :func:`free_on`
    ``field`` (the field left, control lost, a fade: a gateway's DisableMove + Wait(25) comes BEFORE its Field()) is the
    hold TAKEN OVER: the probe stops there. {"dir", "samples", "left", "why", "tried", "frames"}."""
    out = {"dir": None, "samples": [], "left": False, "why": None, "tried": [], "frames": None}
    try:
        rate = g.rate(require=True)
    except HarnessError as err:
        out["why"] = f"no measured render rate to size the hold in ticks ({str(err)[:160]})"
        return out
    walk_frames = max(1, rate.frames_for_ticks(WALK_TICKS))
    watch_frames = walk_frames + rate.frames_for_ticks(WATCH_EXTRA_TICKS)
    out["frames"] = walk_frames
    for d in WALK_DIRECTIONS:
        f0 = g.state.frame
        g.hold(d, walk_frames)
        samples, _end = cb.watch(g, lambda s, f0=f0: not free_on(s, field) or s.frame >= f0 + watch_frames,
                                 timeout=watch_frames / max(1.0, rate.fps_lo) * 3.0 + 5.0)
        out["tried"].append(d)
        bad = next((s for s in samples if not free_on(s, field)), None)
        if bad is not None:
            out.update(left=True, samples=samples, why=_taken(bad))
            return out
        if moving_middle(samples):
            out["dir"], out["samples"] = d, samples
            g.walk(BACK[d], walk_frames)
            return out
    out["why"] = f"no direction moved the player {STEADY_TICKS + TAIL_TICKS + 1}+ ticks ({walk_frames} frames a hold)"
    return out


def _recover(g, field: int) -> None:
    """After a hold was taken over: wait the takeover out (a gateway's wait and the next field's load, or the field
    free again), then warp back to ``field`` at STOCK_ENTRANCE."""
    cb.poll(g, lambda s: (s.field_id != field and s.control and not s.fading) or free_on(s, field), LEAVE_S,
            "the takeover to finish")
    try:
        g.warp(field, entrance=STOCK_ENTRANCE)
    except HarnessError as err:
        g.note(f"the warp back failed: {str(err)[:200]}")
    _settle(g, field)


def _seed(g, ctx: dict) -> None:
    if not ctx["pre"]:
        g.note("the seed skipped: PRE (the registrations) failed")
        return
    try:
        g.warp(PARTY_FIELD)
        g.wait_frames(SETTLE_FRAMES)        # Main_Init's B_PARTYADD ops run on entry
        g.warp(BENCH_FIELD)
        g.wait_frames(SETTLE_FRAMES)
        ctx["seeded"] = True
        g.note(f"the seed: warped through {PARTY_FIELD} (COOPPARTY) to {BENCH_FIELD}")
    except HarnessError as err:
        g.note(f"the seed failed: {str(err)[:300]}")


# ------------------------------------------------------------------------------------------------ leg I's steps
def _fo(ctx: dict, field: int) -> dict:
    """The oracle for ``field`` -- or a NAMED miss (``{"_none": why}``) the judges read as "not reached"."""
    oracle = ctx.get("oracle") or {}
    fo = (oracle.get("fields") or {}).get(field)
    if fo:
        return fo
    why = (oracle.get("problems") or {}).get(field) or (oracle.get("problems") or {}).get("oracle") or "not read"
    return {"_none": f"no oracle for field {field} ({why})"}


def _i_stock(g, led: cb.Ledger, ctx: dict) -> None:
    """Field 250, before the seed: the identity read on arrival, the walk probe (I5 moving), the rest window (I5 rest, I3,
    I7) -- in that order: only movement resets the idle timer, so the rest reads come right after the walk. Every rest
    read is judged only while the game is still on 250 with the player free."""
    field = ctx["stock"]
    fo = _fo(ctx, field)
    _read_field(g, ctx, field)
    if field not in ctx["reads"]:
        led.unreached(("S138-I3", "S138-I5", "S138-I7"), ctx["unreached"].get(field, "the stock field"))
        return
    walk = _walk_probe(g, field)
    ctx["walk"] = walk
    if walk["left"]:
        moving_why = (f"not reached: the probe hold {walk['tried'][-1]!r} was TAKEN OVER ({walk['why']}) -- the bench "
                      f"waited it out and warped back at entrance {STOCK_ENTRANCE}")
        _recover(g, field)
        moving_ok = False
    elif walk["dir"] is None:
        moving_ok, moving_why = False, f"not reached: {walk['why']} ({walk['tried']})"
    else:
        moving_ok, moving_why = judge_walk(walk["samples"], fo)
        moving_why = f"hold {walk['dir']!r} ({walk['frames']} frames): {moving_why}"
    if _settle(g, field) is None:
        led.check("S138-I5", False, f"MOVING {moving_why}; REST not reached: field {field} never came back free "
                                    f"(field {g.state.field_id})")
        led.unreached(("S138-I3", "S138-I7"), f"field {field} never came back with the player free")
        return
    whole = cb.hold_for(g, REST_S)
    rest = on_field_prefix(whole, field)
    ctx["rest"] = rest
    cut = "" if len(rest) == len(whole) else f" (the window cut at its first sample off field {field}: " \
                                            f"{_taken(whole[len(rest)])})"
    if not rest:
        led.check("S138-I5", False, f"MOVING {moving_why}; REST not reached: no rest publish on field {field}{cut}")
        led.unreached(("S138-I3", "S138-I7"), f"no rest publish on field {field}{cut}")
        return
    rest_ok, rest_why = judge_rest(rest, fo)
    led.check("S138-I5", moving_ok and rest_ok, f"MOVING {moving_why}; REST {rest_why}{cut}")
    ok, why = judge_rest_folder(_player(rest[-1]), fo)
    led.check("S138-I3", ok, why + cut)
    ok, why = _judge_i7(g, rest, ctx)
    led.check("S138-I7", ok, why + cut)


def _judge_i7(g, rest: list, ctx: dict) -> tuple:
    """I7 by the engine the probe found: before s139 (or a torn probe) the s138 rule -- the mirror wears the player's own
    body (:func:`judge_ghost`); from s139 on the mirror runs THE HOST RULE under the forced selftest's GuestSlots pin 0, so
    it wears what :func:`judge_worn` computes for the ini's GhostAs with every lever off -- the MOOGLE for auto (owner D2),
    the player's own body for '' / off / 0 -- against the install's oracle."""
    stage = ctx.get("stage")
    if stage is None or stage < 139:
        return judge_ghost(rest)
    want = want_ghost(rest[-1], LEVERS_OFF, ctx.get("ghost_as")) if rest else None
    models, clips = _dress_oracle(g, ctx, {want["model"]} if want else set())
    ok, why = judge_worn(rest, levers=LEVERS_OFF, ghost_as=ctx.get("ghost_as"), models=models, clips=clips)
    return ok, f"s{stage}: the host rule under the GuestSlots pin 0, GhostAs {ctx.get('ghost_as')!r} -- {why}"


def _i_seeded(g, led: cb.Ledger, ctx: dict) -> None:
    """After the seed, on 30801: I8 off the first state with control there."""
    if not ctx.get("seeded"):
        led.unreached(("S138-I8",), "the seed did not run (PRE, or a warp failed)")
        return
    st = _settle(g, BENCH_FIELD)
    if st is None:
        led.unreached(("S138-I8",), f"field {BENCH_FIELD} never came up with control")
        return
    oracle = ctx.get("oracle") or {}
    led.check("S138-I8", *judge_party(_dress(st), oracle.get("party"),
                                      why=(oracle.get("problems") or {}).get("party", "")))


def _i_bench(g, led: cb.Ledger, ctx: dict) -> None:
    """Field 30801: its kit player's identity (judged at close) and I6, its actors."""
    if not ctx.get("seeded"):
        ctx["unreached"][BENCH_FIELD] = "the seed did not reach it (PRE, or a warp failed)"
        led.unreached(("S138-I6",), ctx["unreached"][BENCH_FIELD])
        return
    _read_field(g, ctx, BENCH_FIELD)
    st = ctx["states"].get(BENCH_FIELD)
    if st is None:
        led.unreached(("S138-I6",), ctx["unreached"].get(BENCH_FIELD, "the bench field"))
        return
    led.check("S138-I6", *judge_objects(st, _fo(ctx, BENCH_FIELD)))


def _i_close(g, led: cb.Ledger, ctx: dict) -> None:
    """I1 / I2 / I4 / I9: every field's controlled body against its own oracle -- green only when each field was read."""
    for cid, judge in (("S138-I1", judge_model), ("S138-I2", judge_geo), ("S138-I4", judge_eye), ("S138-I9", judge_ids)):
        oks, parts = [], []
        for field in (ctx["stock"], BENCH_FIELD):
            p = ctx["reads"].get(field)
            if p is None:
                oks.append(False)
                parts.append(f"{field}: not reached ({ctx['unreached'].get(field, 'not read')})")
                continue
            ok, why = judge(p, _fo(ctx, field))
            oks.append(ok)
            parts.append(f"{field}: {why}")
        led.check(cid, all(oks), "; ".join(parts))


# ------------------------------------------------------------------------------------------------ leg G's offline oracle
def idle_frames_oracle(game: Path) -> tuple:
    """(the nine rig rows' idle frame counts, or None; why) -- THE FRAME LAW off the install: each rig row's idle clip (the
    twin's ids, battlewire.RIGS, pinned to the census) read out of p0data5 by the kit's clip reader (ff9mapkit.models.
    _gltf_io.read_clip at the folder ff9mapkit.catalog.locate_animation resolves -- the engine's own folder rule), counted
    by EventEngineUtils.GetCharAnimFrame's formula round(length x rate) + 1 (the kit's thumbcache frame law). READ-ONLY:
    a UnityPy load of the bundle writes nothing."""
    _kit()
    from ff9mapkit import catalog
    from ff9mapkit import extract as X
    from ff9mapkit.models import _gltf_io
    bundle = X._unitypy().load(str(Path(game) / "StreamingAssets" / "p0data5.bin"))
    disc = _gltf_io.anim_disc_map(bundle)
    out = []
    for i, row in enumerate(BW.RIGS):
        model, idle = row[0], row[1]
        loc = catalog.locate_animation(idle, model, disc)
        clip = _gltf_io.read_clip(bundle, loc[1], loc[0]) if loc else None
        if clip is None:
            return None, f"rig {i} ({BW.RIG_NAMES[i]}): its idle clip {idle} is not in p0data5 for model {model}"
        out.append(int(round(float(clip["length"]) * float(clip["sample_rate"] or 30.0))) + 1)
    return out, f"p0data5 idle frames {out}"


def g_oracle_read(game: Path) -> tuple:
    """Leg G's offline oracle: ({"models": {model: {geo, body, ...}}, "clips": {anim id: clip name}, "idle_frames": [9] or
    None}, {key: why}) -- every model leg G may expect (:data:`G_MODELS`) off the install (:func:`model_facts`: its GEO name
    cross-checked with the kit's table, its texture stem), the clip names off the kit's copy of the open-source
    AnimationDB, the idle frames (:func:`idle_frames_oracle`), and a DictionaryPatch `3DModel` / `3DModelAnimation` remap of
    any of those models or the rig rows' loco ids named (stock Memoria applies it at launch; the kit's tables do not)."""
    _kit()
    from ff9mapkit import extract as X
    from ff9mapkit._animdb_all import ANIMATIONS
    problems, models = {}, {}
    for m in G_MODELS:
        try:
            facts = model_facts(game, m)
        except Exception as err:             # noqa: BLE001 - one model that cannot be read is a named problem
            problems[f"model {m}"] = f"read_model raised {type(err).__name__}: {str(err)[:160]}"
            continue
        if facts.get("geo") is None or facts.get("body") is None:
            problems[f"model {m}"] = (f"geo {facts.get('geo_read')!r} vs the table's {facts.get('geo_table')!r}, stems "
                                      f"{facts.get('stems')}")
            continue
        models[m] = facts
    try:
        loco = [a for row in BW.RIGS for a in row[1:6]]
        remaps = dictionary_remaps(game, X._mod_folders(game), G_MODELS, loco)
    except Exception as err:                 # noqa: BLE001
        remaps, problems["remaps"] = [], f"the DictionaryPatch scan raised {type(err).__name__}: {str(err)[:160]}"
    for folder, line in remaps:
        problems[f"remap {folder}"] = f"{line!r} touches a leg-G model or loco id (stock Memoria applies it at launch)"
    try:
        frames, why = idle_frames_oracle(game)
    except Exception as err:                 # noqa: BLE001
        frames, why = None, f"the p0data5 read raised {type(err).__name__}: {str(err)[:160]}"
    if frames is None:
        problems["idle_frames"] = why
    prefabs = {}
    for m in G_PREFAB_MODELS:
        try:
            tree = prefab_tree(game, m)
        except Exception as err:             # noqa: BLE001 - a prefab that cannot be walked is a named problem
            problems[f"prefab {m}"] = f"the prefab walk raised {type(err).__name__}: {str(err)[:160]}"
            continue
        if not tree["renderers"]:
            problems[f"prefab {m}"] = f"{tree['geo']}: no renderer found"
            continue
        prefabs[m] = tree
    return {"models": models, "clips": dict(ANIMATIONS), "idle_frames": frames, "prefabs": prefabs}, problems


#: the Renderer subclasses a prefab's GameObjects carry (GetComponentsInChildren<Renderer> finds both)
RENDERER_TYPES = ("SkinnedMeshRenderer", "MeshRenderer")


def prefab_tree(game: Path, model: int) -> dict:
    """G8's offline oracle: a model's PREFAB as {geo, transforms, renderers} -- every transform's path under the root in
    depth-first pre-order (the root excluded) and every Renderer's path in GetComponentsInChildren order -- walked off
    p0data through the kit's bundle reader (ff9mapkit.models.extract._open_prefab; READ-ONLY, a UnityPy load writes
    nothing). ``geo`` is the REQUESTED identity (ModelFactory's garnetShortHairTable keys off it)."""
    _kit()
    from ff9mapkit.models import extract as ME
    geo, _gid, _tint, _pgeo, _pgid, _ptint, b, root_pid = ME._open_prefab(str(int(model)), game)
    transforms, renderers = [], []

    def walk(tr_tt, path: str) -> None:
        if not tr_tt:
            return
        go = b.tt(ME._pid(tr_tt.get("m_GameObject", {})))
        if path:
            transforms.append(path)
        if go and any(tn in RENDERER_TYPES for tn, _p in b.components(go)):
            renderers.append(path)
        for ch in tr_tt.get("m_Children", []):
            ctt = b.tt(ME._pid(ch))
            cgo = b.tt(ME._pid(ctt.get("m_GameObject", {}))) if ctt else None
            name = str(cgo.get("m_Name")) if cgo else "?"
            walk(ctt, f"{path}/{name}" if path else name)

    _tpid, root_tr = b.transform_of(b.tt(root_pid))
    walk(root_tr, "")
    return {"geo": geo, "transforms": transforms, "renderers": renderers}


def _g_oracle(g, ctx: dict) -> tuple:
    """Leg G's `oracle_extra` hook (:func:`g_oracle_read` on the run's install)."""
    return g_oracle_read(Path(g.game_path))


def _g_oracle_of(ctx: dict) -> dict | None:
    extra = ((ctx.get("oracle") or {}).get("extra") or {}).get("G")
    return extra if isinstance(extra, dict) and extra.get("models") is not None else None


def _dress_oracle(g, ctx: dict, need) -> tuple:
    """(models, clips) for a dress judge outside leg G (I7 on s139+), holding at least the models in ``need``: leg G's
    oracle when it ran; else the fields' own oracle (S138-OR already read each field's player model off the install);
    else the model read NOW (OFFLINE, read-only -- the moogle, when the ini's `auto` dresses the mirror), cached in
    ``ctx``. The clip names are the kit's copy of the open-source AnimationDB."""
    got = _g_oracle_of(ctx)
    if got is not None:
        return got["models"], got["clips"]
    cache = ctx.setdefault("dress_models", {})
    for fo in ((ctx.get("oracle") or {}).get("fields") or {}).values():
        if fo.get("model") is not None and fo.get("geo") and fo.get("body"):
            cache.setdefault(int(fo["model"]), {"geo": fo["geo"], "body": fo["body"]})
    for m in need:
        if m is None or m in cache:
            continue
        try:
            facts = model_facts(Path(g.game_path), int(m))
            cache[m] = facts if facts.get("geo") and facts.get("body") else {}
        except Exception:                    # noqa: BLE001 - an unread model reads "not reached" at the judge
            cache[m] = {}
    _kit()
    from ff9mapkit._animdb_all import ANIMATIONS
    return cache, dict(ANIMATIONS)


# ------------------------------------------------------------------------------------------------ leg G's steps
G_STOCK_CHECKS = ("S139-G0", "S139-G4", "S139-G6", "S139-G3a")
G_SEEDED_CHECKS = ("S139-G1", "S139-G2", "S139-G3", "S139-G3c", "S139-G3m", "S139-G3d", "S139-G5", "S139-G7a", "S139-G7b",
                   "S139-G7c", "S139-G7d", "S139-G8")


def _g_ctx(ctx: dict) -> dict:
    """Leg G's run state: the levers the bench holds, whether the calibration lever is pulled, the ini's GhostAs and
    [Graphics] GarnetHair (read READ-ONLY), G0's baseline."""
    if "g" not in ctx:
        ctx["g"] = {"levers": dict(LEVERS_OFF), "ghost_as": ctx.get("ghost_as"), "garnet_hair": ctx.get("garnet_hair"),
                    "base": None, "lever": bool(ctx.get("calibrate")) and ctx.get("cal_mode") == CAL_RULE_S138}
    return ctx["g"]


def _g_send(g, ctx: dict, *ops) -> str | None:
    """Each `selfdress` op in order, through the driver (refused BEFORE the step on an engine before s139), the levers the
    bench now holds tracked; the first refusal's text, or None."""
    lv = _g_ctx(ctx)["levers"]
    for op in ops:
        words = [str(a) for a in op]
        ok, why = cb.try_ns(g, "selfdress", *words)
        if not ok:
            return f"`selfdress {' '.join(words)}` refused: {why}"
        name, val = words[0], (words[1] if len(words) > 1 else None)
        if name == "clear":
            lv.update(LEVERS_OFF)
        elif name in ("ghost", "empty"):
            lv["mask" if name == "ghost" else "empty"] = -1 if val == "off" else int(val)
        elif name == "wire":
            lv["wire"] = -1 if val == "off" else int(val)
            lv["wire_anim"] = int(words[2]) if len(words) > 2 else -1
        elif name == "rule":
            lv["rule"] = val
    return None


def _g_clear(g, ctx: dict, *, relever: bool = True) -> str | None:
    """Every lever back off with `selfdress clear` -- then, under the calibration lever (``relever``), `rule s138` again
    (`clear` releases it). Nothing is sent when the bench already holds exactly that."""
    gx = _g_ctx(ctx)
    want = dict(LEVERS_OFF, rule="s138") if relever and gx["lever"] else dict(LEVERS_OFF)
    if gx["levers"] == want:
        return None
    why = _g_send(g, ctx, ("clear",))
    if why is None and want["rule"]:
        why = _g_send(g, ctx, ("rule", "s138"))
    return why


def _labelled(label: str, ok: bool, detail: str) -> tuple:
    """(ok, detail) with the ops' label -- a "not reached: " verdict kept FIRST (S138-CAL reads it there)."""
    nr = "not reached: "
    if detail.startswith(nr):
        return ok, f"{nr}{label}: {detail[len(nr):]}"
    return ok, f"{label}: {detail}"


def _g_apply(g, ctx: dict, ops) -> tuple:
    """Every lever cleared (the calibration lever re-pulled), ``ops`` sent -> (label, None) or (label, the refusal)."""
    label = " + ".join(f"`selfdress {' '.join(str(a) for a in op)}`" for op in ops)
    return label, _g_clear(g, ctx) or _g_send(g, ctx, *ops)


def _g_try(g, ctx: dict, field: int, ops) -> tuple:
    """One leg-G row: every lever cleared (the calibration lever re-pulled), ``ops`` sent, the ghost watched GHOST_SETTLE_S
    on ``field`` and its last held publish judged against the twin (:func:`judge_worn`) -> (ok, detail)."""
    gx, oracle = _g_ctx(ctx), _g_oracle_of(ctx)
    if oracle is None:
        return False, f"not reached: no leg-G oracle ({(ctx.get('oracle') or {}).get('problems')})"
    label, why = _g_apply(g, ctx, ops)
    if why is not None:
        return False, f"not reached: {why}"
    samples = on_field_prefix(cb.hold_for(g, GHOST_SETTLE_S), field)
    ok, detail = judge_worn(samples, levers=dict(gx["levers"]), ghost_as=gx["ghost_as"], models=oracle["models"],
                            clips=oracle["clips"])
    return _labelled(label, ok, detail)


def _g_stock(g, led: cb.Ledger, ctx: dict) -> None:
    """Field 250, before the seed (after leg I's rest window): G0 -- the baseline, every lever off --, G4 and G6 (the proof
    block's verdicts: it ran at S0), then, under COOP_DRESS_CAL=rule-s138, the calibration lever; then G3a while the
    New-Game party's slot 1 is EMPTY (the real party read: no `empty` lever); every lever cleared after it (under the
    calibration lever, `rule s138` pulled again: no leg-I read after it reads the ghost)."""
    field, gx = ctx["stock"], _g_ctx(ctx)
    oracle = _g_oracle_of(ctx)
    led.check("S139-G4", *judge_codec(_dress(g.state), cb.log_lines(g)))
    led.check("S139-G6", *judge_idle_frames(_dress(g.state), (oracle or {}).get("idle_frames")))
    if _settle(g, field) is None:
        led.unreached(("S139-G0", "S139-G3a"), f"field {field} never came up with the player free")
        return
    if oracle is None:
        led.unreached(("S139-G0", "S139-G3a"), f"no leg-G oracle ({(ctx.get('oracle') or {}).get('problems')})")
        return
    samples = on_field_prefix(cb.hold_for(g, GHOST_SETTLE_S), field)
    ok, why = judge_baseline(samples, ghost_as=gx["ghost_as"], models=oracle["models"], clips=oracle["clips"])
    gx["base"] = _ghost_tuple(samples[-1]) if samples else None
    led.check("S139-G0", ok, why)
    if gx["lever"]:
        w = _g_send(g, ctx, ("rule", "s138"))
        g.note("CALIBRATION: `selfdress rule s138` pulled -- the pre-s139 selftest site" + (f" (REFUSED: {w})" if w else ""))
    party = (_dress(g.state) or {}).get("party")
    if not isinstance(party, list) or len(party) != 4:
        led.check("S139-G3a", False, f"netsync.dress.party {party!r}: not 4 slots -- an engine before s138")
    elif party[1] != BW.PARTY_EMPTY:
        led.unreached(("S139-G3a",), f"the save's slot 1 already holds CharacterId {party[1]} (party {party}): the empty "
                                     f"named slot G3a needs is not there before the seed")
    else:
        led.check("S139-G3a", *_g_try(g, ctx, field, [("ghost", 2)]))
    w = _g_clear(g, ctx)
    if w is not None:
        g.note(f"leg G's cleanup on {field}: {w}")


def slot_of(party, char: int) -> int | None:
    """(PURE) The first slot >= 1 holding CharacterId ``char`` (G8: Garnet) -- None when none does."""
    if not isinstance(party, list):
        return None
    return next((i for i in range(1, min(4, len(party))) if _int(party[i]) == int(char)), None)


def _g_moving(g, ctx: dict, field: int) -> tuple:
    """G3m: `ghost 2` + `empty 2` (the moogle, whatever the ini), the ghost settled, then leg I's walk probe on ``field``
    -- its samples judged per tick (:func:`judge_worn_moving`). A hold TAKEN OVER reads "not reached" (the bench waits it
    out and warps back)."""
    gx, oracle = _g_ctx(ctx), _g_oracle_of(ctx)
    if oracle is None:
        return False, f"not reached: no leg-G oracle ({(ctx.get('oracle') or {}).get('problems')})"
    label, why = _g_apply(g, ctx, [("ghost", 2), ("empty", 2)])
    if why is not None:
        return False, f"not reached: {why}"
    cb.hold_for(g, GHOST_SETTLE_S)
    walk = _walk_probe(g, field)
    if walk["left"]:
        _recover(g, field)
        return False, f"not reached: {label}: the probe hold {walk['tried'][-1]!r} was TAKEN OVER ({walk['why']})"
    if walk["dir"] is None:
        return False, f"not reached: {label}: {walk['why']} ({walk['tried']})"
    _settle(g, field)
    ok, detail = judge_worn_moving(walk["samples"], levers=dict(gx["levers"]), ghost_as=gx["ghost_as"],
                                   models=oracle["models"], clips=oracle["clips"])
    return _labelled(f"{label}, hold {walk['dir']!r} ({walk['frames']} frames)", ok, detail)


def _g_rest_mask(g, ctx: dict, field: int, slot: int) -> tuple:
    """G8: `ghost 1<<slot` (Garnet's bit) -> the ghost wears her (:func:`judge_worn`) AND its visibility is the rest mask
    applied, equal to the install prefab's field-mode hides (:func:`judge_rest_mask`)."""
    gx, oracle = _g_ctx(ctx), _g_oracle_of(ctx)
    if oracle is None:
        return False, f"not reached: no leg-G oracle ({(ctx.get('oracle') or {}).get('problems')})"
    label, why = _g_apply(g, ctx, [("ghost", 1 << slot)])
    if why is not None:
        return False, f"not reached: {why}"
    samples = on_field_prefix(cb.hold_for(g, GHOST_SETTLE_S), field)
    lv = dict(gx["levers"])
    worn_ok, worn = judge_worn(samples, levers=lv, ghost_as=gx["ghost_as"], models=oracle["models"], clips=oracle["clips"])
    tree = (oracle.get("prefabs") or {}).get(BW.RIGS[G_GARNET][0])
    vis_ok, vis = judge_rest_mask(samples, levers=lv, tree=tree, garnet_hair=gx["garnet_hair"])
    nr = "not reached: "
    detail = (nr if not worn_ok and worn.startswith(nr) or not vis_ok and vis.startswith(nr) else "") + \
        f"VISIBILITY {vis.removeprefix(nr)}; WORN {worn.removeprefix(nr)}"
    return _labelled(label, worn_ok and vis_ok, detail)


def _g_seeded(g, led: cb.Ledger, ctx: dict) -> None:
    """After the seed, on 30801 (the live party read: s1 = its first slot >= 1 holding a main): G1, G2, G3, G3c, G3m (the
    moogle moving), G3d, G5 (its own setup: `ghost 1<<s1`, then `clear` alone -- the lever released for it, re-pulled
    after), the guard rows G7a-d on `ghost <s1 bit>`, then G8 on Garnet's bit; every lever released at the end (no `rule
    s138` left for the later phases)."""
    gx = _g_ctx(ctx)
    if not ctx.get("seeded"):
        led.unreached(G_SEEDED_CHECKS, "the seed did not run (PRE, or a warp failed)")
        return
    field = BENCH_FIELD
    st = _settle(g, field)
    if st is None:
        led.unreached(G_SEEDED_CHECKS, f"field {field} never came up with control")
        return
    oracle = _g_oracle_of(ctx)
    if oracle is None:
        led.unreached(G_SEEDED_CHECKS, f"no leg-G oracle ({(ctx.get('oracle') or {}).get('problems')})")
        return
    party = (_dress(st) or {}).get("party")
    s1 = first_main_slot(party)
    g.note(f"leg G: the seeded party {party} -- s1 = {s1}")
    if s1 is None:
        led.unreached(("S139-G1", "S139-G5", "S139-G7a", "S139-G7b", "S139-G7c", "S139-G7d"),
                      f"no slot >= 1 holds a main (party {party}): nothing for `ghost 1<<s1` to name")
    else:
        led.check("S139-G1", *_g_try(g, ctx, field, [("ghost", 1 << s1)]))
    if isinstance(party, list) and len(party) == 4 and _int(party[2]) is not None and 0 <= party[2] < BW.MAIN_RIG_COUNT:
        led.check("S139-G2", *_g_try(g, ctx, field, [("ghost", 6), ("empty", 2)]))
    else:
        led.unreached(("S139-G2",), f"slot 2 holds no main (party {party}): the skip has no next member to land on")
    led.check("S139-G3", *_g_try(g, ctx, field, [("ghost", 2), ("empty", 2)]))
    led.check("S139-G3c", *_g_try(g, ctx, field, [("ghost", 6), ("empty", 6)]))
    led.check("S139-G3m", *_g_moving(g, ctx, field))
    # G3d: a spectator (mask 0) -- the ghost half AND the producer's bytes off the proof block's line
    ok, why = _g_try(g, ctx, field, [("ghost", 0)])
    sec_ok, sec_why = judge_section_line(cb.log_lines(g), gx["ghost_as"])
    led.check("S139-G3d", ok and sec_ok, f"{why}; SECTION 8: {sec_why}")
    # G5 (control): its OWN setup -- `ghost 1<<s1` held until the ghost wears party[s1] (the precondition), then `clear`
    # ALONE: every lever off, the mode and the ghost back to G0's baseline (a witness that MOVES: Vivi -> the baseline)
    if s1 is not None:
        pre_ok, pre_why = _g_try(g, ctx, field, [("ghost", 1 << s1)])
        if not pre_ok:
            led.check("S139-G5", False, f"not reached: the precondition `ghost {1 << s1}` -> party[{s1}] did not hold "
                                        f"({pre_why})")
        else:
            why = _g_send(g, ctx, ("clear",))
            if why is not None:
                led.check("S139-G5", False, f"not reached: {why}")
            else:
                samples = on_field_prefix(cb.hold_for(g, GHOST_SETTLE_S), field)
                ok, detail = judge_baseline(samples, ghost_as=gx["ghost_as"], models=oracle["models"],
                                            clips=oracle["clips"])
                now = _ghost_tuple(samples[-1]) if samples else None
                base = gx["base"]
                same = base is not None and now is not None and (now[0], now[1], now[3]) == (base[0], base[1], base[3])
                led.check("S139-G5", ok and same,
                          f"after `ghost {1 << s1}` held ({pre_why[:160]}), `selfdress clear`: {detail}; (model, geo, rig) "
                          f"{now and (now[0], now[1], now[3])} vs G0's {base and (base[0], base[1], base[3])}")
    # G7: the guard, on `ghost <s1 bit>` (the dress is party[s1]'s rig row); G7b pins the wire body to its rig's BREAK clip
    if s1 is not None:
        dress = BW.rig_row(party[s1])
        for cid, wire in (("S139-G7a", (G_WIRE_RIGGED,)), ("S139-G7b", (dress["model"], dress["inactive"])),
                          ("S139-G7c", (BW.PLAIN_ZIDANE_MODEL,)), ("S139-G7d", (G_WIRE_UNRIGGED,))):
            if cid == "S139-G7b" and not dress["inactive"]:
                led.unreached((cid,), f"party[{s1}]'s rig ({BW.rig_name(party[s1])}) has no break clip (0 = none)")
                continue
            led.check(cid, *_g_try(g, ctx, field, [("ghost", 1 << s1), ("wire", *wire)]))
    # G8: the rest mask, on Garnet's bit
    gslot = slot_of(party, G_GARNET)
    if gslot is None:
        led.unreached(("S139-G8",), f"no slot >= 1 holds Garnet (party {party}): the rest mask's two-hairstyle body")
    else:
        led.check("S139-G8", *_g_rest_mask(g, ctx, field, gslot))
    w = _g_clear(g, ctx, relever=False)
    if w is not None:
        g.note(f"leg G's cleanup on {field}: {w}")


# ================================================================================================ the run
def _ctx_new(stock: int, legs, calibrate: bool, cal_mode: str | None = None) -> dict:
    return {"stock": int(stock), "legs": tuple(legs), "calibrate": bool(calibrate), "cal_mode": cal_mode,
            "ini_ok": False, "oracle": None, "stage": None, "pre": False, "seeded": False, "reads": {}, "states": {},
            "unreached": {}, "walk": None, "rest": None, "ghost_as": None, "garnet_hair": None}


def unreached_ids(g) -> set:
    """The check ids this run recorded RED with a "not reached" detail (off the session's own rows)."""
    return {str(r.get("what", "")).split(":")[0] for r in getattr(g, "checks", ()) or ()
            if not r.get("ok") and str(r.get("detail", "")).startswith("not reached")}


def run(g, field: int = STOCK_FIELD):
    calibrate = cb.CALIBRATE
    try:
        legs = selected_legs()
    except ValueError as err:
        led = cb.Ledger(g, {"S138-LEGS": "COOP_DRESS_LEGS names legs this file has"})
        led.check("S138-LEGS", False, str(err))
        return
    cal_mode = None
    if calibrate:
        try:
            cal_mode = selected_cal_mode(legs)
        except ValueError as err:
            led = cb.Ledger(g, {"S138-CALMODE": f"COOP_DRESS_CAL is one of {cal_modes(legs)}"})
            led.check("S138-CALMODE", False, str(err))
            return
    led = cb.Ledger(g, _catalog(legs, calibrate), finals=("S138-R", "S138-CAL"))
    ctx = _ctx_new(field, legs, calibrate, cal_mode)
    try:
        _run(g, led, ctx)
    except HarnessError as err:
        g.note(f"the run raised: {str(err)[:400]}")
        led.close(f"not reached: the run raised ({str(err)[:200]})")
    finally:
        g.note(f"logs archived: {_archive_logs(g, 'self-dress')}")
        led.close()
        if ctx["ini_ok"]:
            at = cb.mark(g)
            # [ff9mapkit netsync s139] on an s139+ engine one inert selfdress lever is HELD into the reset, so S138-R
            # witnesses the harness release itself (HarnessReleaseBench -> HarnessReleaseDress), not only the forced role
            try:
                held, hwhy = hold_into_reset(g, ctx)
            except HarnessError as err:                    # a dead game still gets its `reset` tried below
                held, hwhy = False, f"raised ({str(err)[:200]})"
            if held:
                extra, lines = judge_released, (RELEASE_LINE,)
            elif hwhy is not None:
                extra, lines = (lambda _st, w=hwhy: (False, f"the selfdress lever to hold into the reset: {w}")), ()
            else:
                extra, lines = None, ()
            cb.release(g, led, "S138-R", at=at, expect_lines=lines, extra=extra)
        else:
            led.unreached(("S138-R",), "the precondition refused the run (S138-INI): nothing was set")
        if calibrate:
            pred, maybe, why = predicted(ctx["stage"], legs, cal_mode or CAL_OLD)
            unproven = lever_unproven(ctx["stage"], legs, cal_mode or CAL_OLD, unreached_ids(g))
            if pred is None:
                led.check("S138-CAL", False, why)
            elif unproven:
                led.check("S138-CAL", False, f"the lever {cal_mode!r} is UNPROVEN on {unproven}: each predicted red reads "
                                             f"'not reached' (the lever never bit there) -- a red that proves nothing")
            else:
                led.judge_calibration("S138-CAL", pred, maybe)
        led.close(final=True)


def _run(g, led: cb.Ledger, ctx: dict) -> None:
    ok, why = _ini_guard(g)
    led.check("S138-INI", ok, why)
    if not ok:
        led.close(f"refused to run: {why}")
        return
    ctx["ini_ok"] = True
    # [ff9mapkit netsync s139] the config leg G (and I7 on s139+) judges by, read READ-ONLY: [Netsync] GhostAs as the engine
    # reads it (trimmed; absent = "")
    ctx["ghost_as"] = (cb.ini_value(g, "Netsync", "GhostAs") or "").strip()
    # ...and [Graphics] GarnetHair (G8's hair rule: 1 long, 2 short, else the scenario counter decides), READ-ONLY
    hair = (cb.ini_value(g, "Graphics", "GarnetHair") or "").strip()
    ctx["garnet_hair"] = int(hair) if hair.lstrip("-").isdigit() else 0
    oracle, owhy = read_oracle(g, oracle_fields(ctx["legs"], ctx["stock"]))
    ctx["oracle"] = oracle
    _oracle_extra(g, ctx)
    led.check("S138-OR", not oracle["problems"], owhy)
    ok, why = _setup(g, ctx)
    led.check("S138-S0", ok, why)
    if not ok:
        led.close(f"the selftest role was refused -- {why}")
        return
    stage, pwhy = probe(g.state)
    ctx["stage"] = stage
    led.check("S138-P0", stage is not None, pwhy)
    g.note(f"probe stage: {cb.stage_note(g.state)}; dress instrument "
           f"{'ABSENT' if stage == STAGE_NONE else 'TORN' if stage is None else f'present (s{stage})'}")
    pre = pre_fields(ctx["legs"])
    try:
        regs = g.registered_fields()[0]
    except (HarnessError, AttributeError, OSError) as err:
        regs, ctx["pre_why"] = {}, f"could not read the registrations ({str(err)[:120]})"
    missing = [f for f in pre if f not in regs]
    ctx["pre"] = not missing
    led.check("S138-PRE", not missing, ctx.get("pre_why") or
              (f"not registered: {missing} (deploy COOPPARTY: py tools/deploy_field.py "
               f"studies/battle-coop/bench/coopparty.field.toml --id {PARTY_FIELD} --mod-folder FF9CustomMap-msgs, then "
               f"relaunch)" if missing else ", ".join(f"{f} {regs.get(f)!r}" for f in pre)))
    try:
        g.state_every(1)
    except (HarnessError, AttributeError) as err:
        g.note(f"stateevery 1 refused ({str(err)[:120]})")
    for phase in PHASES:
        if phase == "seed":
            _seed(g, ctx)
            continue
        for leg in ctx["legs"]:
            step = LEGS[leg]["steps"].get(phase)
            if step is not None:
                globals()[step](g, led, ctx)
