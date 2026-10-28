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
            selected legs need, registered) -> PF ([s140] the bench field's preflight, FAILING CLOSED)
    stock   field 250 BEFORE the party seed      (s139's G0 / G3a, which need an empty slot, join here)
    seed    warp through COOPPARTY (30604: [party] add = vivi, garnet, steiner) to 30801 (only for a leg that needs it)
            ([s140] leg S warps through COOPSUB -- 30605: [party] remove steiner, add blank -- itself, in the "self"
            phase, for S7 / S8: a CharacterId 8-11 member SEATED)
    seeded  the seeded party, on 30801            (s139's G1-G8 join here)
    bench   field 30801's actors (leg I); [s140] 30602's warm return (leg W), then the bench field 30606 (legs X / N / T)
    self    [s140] the stock field AGAIN, every leg-G lever released: leg S (the guest's own body, dressed by `self`)
    close   the verdicts that need every field read
The file has leg I (s138), leg G (s139: Session.NETSYNC_DRESS_SUBVERBS `selfdress`; its `old` row at stages 137 / 138
is every G check -- the verb refused before the step, `mode` / `codec` / `rig_idle_frames` absent --; its `lever` row
`rule-s138` is G_LEVER_REDS), legs S / W / X / N / T (s140: Session.NETSYNC_SELFDRESS_OP_CAPS `self` / `gate` / `law`) and
leg F (s141: the `polish` op; its `old` row at stages 137-140 every F check, its `lever` row `polish-off`
S141_LEVER_PREDICTED). COOP_DRESS_LEGS=I,G (or I+G: the bench runners' ENV lists are comma-separated) picks legs (default:
every leg this file has). THE RIG SPACE is battlewire.RIG_NAMES:
-1 none, 0-7 the CharacterId rows, 8 the moogle, [s140] 9-12 Cinna / Marcus / Blank / Beatrix (CharacterId 8-11: the
owner's "their own models") -- rig 8 is NOT CharacterId 8 (Cinna), rig 9 NOT CharacterId 9 (Marcus): decoded by name
(battlewire.char_to_rig / rig_to_char are the only bridges), never compared with a CharacterId.

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
    WRITES into StreamingAssets on a miss, and the kit's field index (resolve_field) is written the same way
    (KIT_CACHE_FILES: both). When either is missing the bench does not create it: that field's oracle reads "not
    reached: the kit cache is missing (run any ff9mapkit read once, by hand)". Event names come from the kit's id table
    or the DictionaryPatch registration, never from resolve_field.

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

LEGS S / W / X / N / T (s140) -- THE GUEST DRESSES ITSELF (R3-FIELD-MODEL-AUDIT.md 2.3 and 4.4 -- the audit OVERRIDES the
design --, with the owner's decision of 2026-10-17: Blank, Marcus, Cinna and Beatrix, CharacterId 8-11, get "their own
models", rigs 9-12). The selftest role arms ITSELF at each FIELD LOAD from the `selfdress self` spec (NetSyncSelfDress.
ArmBench: section 8 through the real encoder and reader), so every s140 row sends its spec and RE-WARPS; a dressed body is
undressed only by its next SetModel (the teardown law). The levers (selftest role only; `selfdress clear` and every
harness release free them; each published AS SET under `netsync.dress.self`): `self off|auto [mask]|<name>`, `gate 0`
(the player gate skipped) and `law bframe|attach|alias|timeline off` (one s140 law off). Each row starts with `clear`,
then the run's calibration lever, then its spec (THE KNOB is never an ini edit: `self off` stands in for SelfDress=0).
EVERY EXPECTED VALUE IS READ OFFLINE -- the s140 oracle hook `_s_oracle` (part of S138-OR, read once): each rig's model (a
main's off the kit's playerswap.CHARACTERS; the moogle's and Cinna..Beatrix's by their GEO name in the kit's table:
GEO_SUB_F0_BLN = 5467, never the Pluto Knight's 190), its GEO name and texture stem off the install (read_model), its eye
byte (a main's off playerswap; the others' the modal SetModel byte of a STOCK script that wears it, read through the kit's
events-bundle cache: 407 the moogle, 50 Cinna / Marcus / Blank, 767 Beatrix), its loco clips' NAMES (the kit's
AnimationDB) and its idle's frame count off p0data5 (the kit's clip reader; the conductors' source clips too). The twin's
rig table (battlewire.RIGS) and the census (studies/battle-coop/dress-census/rigs_8_11.json) are CROSS-CHECKS: a
disagreement is an S138-OR problem, named -- never the oracle. Every counter (`confirmed`, `skip_npc`, `remaps`, ...) is
PER PROCESS: a row judges its own delta.
  PF    precondition: the bench field 30606's DEPLOYED .eb (READ-ONLY, the first FolderNames folder that ships it) passes
        _selfdress_field.preflight -- MAIN_INIT_ORDER (the twin's InitObject before the player's), the sids, T3's 2705
        bound, the late entry's never-run CC and its GUARDED load-time InitObject, J's ladder jump, every conductor and the
        caller's ESCAPE protocol (every WEDGED / DONE write, every bound, the EnableMoves: a missing escape would turn a
        lever red into a timeout with DisableMove held) -- FAILING CLOSED: else every 30606 row reads "not reached".
        (deploy_field.py alone cannot ship it: `py studies/battle-coop/bench/selfdress_bench.py deploy` builds and seats.)
  -- the "self" phase, on the stock field (250), after the bench phase --
  S1    `self freya` + a re-warp (entrance 0) -> the oracle's Freya: model 192, GEO_MAIN_F0_FRJ, body '192', eye -376, at
        rest anim_geo GEO_MAIN_F0_FRJ; `self` why 'dressed', rig / want_rig 4, want_char 4, from 'bench', uid ==
        player.uid, net_byte 5, src 98, confirmed +1; AttachDress AT THIS LOAD (site a): attach_cold +1 / attach_warm +0
        across the warp -- a per-load call counter, never the last-write src_attached alone (the bench phase's W / T
        loads leave it > 0 long before S1) -- then src_attached > 0 and src_list_clips == the stock field's
        GEO_MAIN_F0_ZDN EventAnimation line read offline (field 250: 1, BREAK1_XARM); ONE dress line; and ARMING AT THE
        FIELD LOAD ONLY: the `self` op's own publish shows bench_self 'freya' with the arm and the body still as they
        were (the `arm_live` stand-in fault is its red).
  S2    the dressed Freya per field tick (leg I's walk probe): mid-move 2553 / 2558 (either) playing in her folder; at rest
        a clip NAMED ANH_MAIN_F0_FRJ_IDLE (before the idle timer); anim_geo GEO_MAIN_F0_FRJ on EVERY publish, read live.
  S5    the selftest mirror's ghost wears 192 (the dressed body is the wire's own: GhostGuard shows it as it is).
  S3    `self auto 2` + `empty 2` + a re-warp -> the MOOGLE: 220, GEO_NPC_F0_MOG, body '220', eye -200, rig 8, want_char 255.
  S6    THE OWNER'S 8-11 ROW: `self blank` + a re-warp -> 5467, GEO_SUB_F0_BLN, body '5467', eye -348, rig 11, want_char 10,
        his idle NAMED ANH_SUB_F0_BLN_IDLE in his own folder (by NAME; S7 seats him).
  S4    THE TEARDOWN LAW: the publish read BEFORE the `clear` and the one after `clear` + `self off` (held OP_SETTLE_S)
        show the SAME live body (model, body, GEO, eye, self.rig, net_byte -- S6's Blank: the knob and Clear() never
        undress a live body; the `clear_undresses` stand-in fault is its red); then the re-warp -> Zidane again at the
        NEXT SetModel (98, '98', -372); why 'model 0', net_byte 0.
  S7    THE 8-11 PARTY PATH, SEATED: a warp through COOPSUB (30605) seats Blank -- `dress.party` the oracle's (the seed's
        RemoveParty / B_PARTYADD over the party read before it), CharacterId 10 (never his old index 11) -- then `self
        auto <his bit>` + a re-warp -> the body is Blank (5467, rig 11, want_char 10) through the LIVE FF9.party read.
  S8    ...the HOST side over him: `self off` + a re-warp (the wire body 98), then `ghost <his bit>` -> the mirror's ghost
        wears 5467 / rig 11 (GhostGuard dresses a 98 wire; the s140 host rule over a live 8-11 slot), the twin's clip
        playing, at rest and per tick moving (his own walk / run clip).
  -- the "bench" phase (before "self"): 30602 (W), then the bench field 30606 (X, N, T) --
  W1    THE WARM RETURN on 30602, on STEINER (his break clip 119 is a clip no 30602 entry lists: only AttachDress at the
        rebuild puts it back -- Freya has none, so on her CheckSleep plays nothing either way): `self steiner` + a warp,
        `dioboot` / `dioleave` -> last_return 'warm', returns +1; the body still Steiner (`self.uid` unchanged, net_byte
        4) with NO new dress line (PosObj.copy carried it: no SetModel); AttachDress AT THE REBUILD (site b): attach_warm
        +1 / attach_cold +0 across the return, then src_attached > 0 and src_list_clips == 30602's own list (0: deployed
        before the kit shipped EventAnimation lists -- the source list is S1's witness); at rest his idle id; idle past
        the inactive timer (IDLE_PAST_S, its longest draw): his break clip ANH_MAIN_F0_STN_BREAK_1 plays BY NAME,
        clip_playing, frame_n 110 (off p0data5), never IDLE_NULL_RUN publishes in a row playing nothing (the frameN-255
        freeze of a clip the go lacks), anim_geo GEO_MAIN_F0_STN wherever published; a walk: GEO_MAIN_F0_STN mid-move (a
        hold TAKEN OVER reads "not reached"). The design's `netsync talk` to a GESTURING NPC is NOT PROVEN: 30602's only
        NPC (Vivi, `control`) runs a kit talk window, no gesture.
  W2    (the cold control) a plain warp to 30602 -> dressed THROUGH SetModel: confirmed +1, ONE dress line.
  X1    the X conductor (RunAnimationEx(250, 186 BREAK1_LOOK) + WaitAnimationEx) on Freya: DONE_X, remaps +1, the gesture
        showed, every clip from the trigger to DONE NAMED ANH_MAIN_F0_FRJ_IDLE (the alias by NAME, never the id) in
        GEO_MAIN_F0_FRJ -- never a ZDN folder.
  X2    after it the stored idle 2556 plays with frame_n == her idle's frame count off p0data5 (50: the ALIAS proof --
        DefaultAnim's SetAnim saw another id); control back within the gesture's hold (70 source frames) + 5 s.
  X3    THE JUMP SLOT ON THE SOURCE TIMELINE (same load): the J conductor -- field 404's ladder mount without its arc,
        SetJumpAnimation(10687 LADDER_1_1, 2, 6) / RunJumpAnimation / RunLandAnimation in the player's own entry -- ends
        DONE_J; every publish playing the jump slot (her idle ALIAS by NAME) runs on frame_n 8 (LADDER_1_1's, off
        p0data5; the alias's own 50 is the red: a landing that holds ~42 ticks instead of stock's 0), and the landing
        (J_LAND -> J_END) lasts no longer than stock's ticks / 30 + J_SLOP_S.
  N1    `self freya` on 30606: the TWIN (by its BUILT sid 2, never by model) stays 98 and skip_npc +1 (the player gate);
        the player's BODY (model, texture stem, GEO, eye -- not only po.model, which the hook itself writes) the oracle's
        Freya; exactly ONE dress line for the load, the player's sid.
  N3    the N3 conductor InitObjects the LATE 98+CC entry after the player's CC -> skip_second +1, the late entry (sid 3)
        stays 98 with NO dress line for its sid since the trigger, control unchanged, the player's body still Freya.
  N2    `gate 0` + a re-warp -> skip_npc +0, the twin AND the player both wear 192 (the player's body the oracle's),
        exactly TWO dress lines (the twin's sid and the player's), `self.gate` false. (objects[] carries no `body`: the
        twin's own texture-stem witness is s141's.)
  T2    the self-dress proof: `self.selftest` 'ok' and 'self-dress selftest: OK (29 rows)' (its T2 row: the effMapNo
        checks read the raw `anim`; the dress order's control-first mutant -- the bench field has no 98 NPC inited AFTER
        the player's CC without a CC of its own, so the in-game legs cannot tell that order: the proof row is its home).
  T1    on Garnet (a 30-frame idle) the T1 conductor (2572 COLD_FAINT_1, then `while GetEntryAnimFrame(250) < 58`) ends --
        DONE_T1, never WEDGED_T1 -- with timeline_kept +1; the moogle (72 frames) ends too: the CONTROL, never the
        discriminator (a control that does not end reads "not reached": the bench, not the law).
  T3    on EVERY rig (`self <name>` + a re-warp each, zidane .. beatrix: the eight mains, the moogle, Cinna..Beatrix) the
        body wears that rig and field 2705's loop in the player's entry ends -- DONE_T3 and T3_END, never WEDGED_T3 (a red,
        recovered by the next warp) -- with bframe_remaps +1 on each dressed rig and +0 on Zidane (stock).
NOT PROVEN BY THE s140 LEGS: a client's arm off a REAL host's section 8 (the selftest role arms from its bench spec through
the same reader: a duo or sitting box), the sticky skip on a live client (the stand-in models it; the engine's SelfTest
row), the exit ramp's / OnDestroy's / a config change's Clear() (S4 proves `clear`'s ReleaseBench -> Clear() leaves the
live body alone), the multi-binder fields' ctl_elsewhere (D3: sitting B samples them), SETVY3's airborne window (X3
jumps in place: the source pins and the census test cover it), a real footstep (s141), a body re-armed to ANOTHER rig
mid-field (the engine's SelfTest body row, through BodyRig: every hook resolves its rig there).
FOR THE OWNER'S SITTING (what s140 SHOWS, so it is judged as expected, never as a fault -- R3-DESIGN.md's B boxes are
the owner's to amend):
  * THE DISC-1 OPENING (the 8-11 decision): a guest whose host's GuestSlots names a slot holding Cinna / Marcus / Blank
    wears that member's own model -- in a field that also InitObjects that member's NPC (field 63 after battle 338 is the
    clear case: field 62 seats Zidane / Cinna / Marcus / Blank, field 63 inits all three Tantalus NPCs, so GuestSlots 2 =
    Cinna, section 8 = 6B 00 08) both screens show TWO of that member; in fields 50-57 the party is Zidane alone (the
    named slot EMPTY at load), so there the guest is the MOOGLE on both screens. The audit's amendment 13 ("the opening
    fields 50-69 are never dressed") is false under s140 (and was already, for 50-57's moogle, under s139's host rule).
    The exclusion stays 70 and 3000-3012 (R3 risk 11 accepts the class). This result goes to the owner BEFORE the s140
    deploy (review rrigs-2), not first at the sitting; if the duplicate is rejected, the consistent change is a
    SetModel-time SKIP on the guest (the field's own entries already SetModel the rig's model: an NPC of the same
    character) plus the matching HostDress fallback on the host -- both sides, so the screens agree; a skip, never an arm
    state, as the exclusion is. GhostAs=moogle (one knob, both screens) already avoids it today.
  * A GUEST-SIDE GhostAs (review rrigs-1): the guest's own body wears what the HOST's GhostAs names, while the guest's
    ghost of the HOST still follows the s138 client rule (the GUEST's own GhostAs / GuestSlots / FF9.party, kept byte for
    byte: the 8 mains). With a GhostAs on the guest's machine too (the Workspace's shared play-style panel, or `coop join
    --ghost-as`), the guest sees the host dressed beside its own dressed body -- and with the same pick on both machines,
    TWO of that character, while the host's screen shows host Zidane plus the dressed guest. Expected, not a fault: the
    kit now warns a joiner that names one (`coop join` prints a NOTE; the --ghost-as help and the Workspace tooltip say
    leave it off when joining).
  * B20 (a dressed body on field 250): the MCF default light row (flat grey, not Zidane's), the default blob shadow, and
    NO footfalls (Zidane_Init's RunModelCode keys ZDN clip ids the dressed body never plays) -- all s141's.
  * B23 (a gesture on a dressed body): the rig's idle ALIAS stretched over the SOURCE frame count -- a 134-frame STAND on
    Garnet's 30-frame idle reads as a near-frozen sway; ladders and jumps glide in the idle (amendment 10) on the SOURCE
    clip's timeline (X3: every mount / dismount lasts stock's).
  * B27 (SelfDress=0): it takes effect at the next COLD load; a warm return after the switch stays dressed (the teardown
    law).
LEG G BY STAGE (the owner's 8-11 rows): every leg-G expectation is the PROBED engine's (`stage_rules`: battlewire.
dress_rules) -- on s139 its frozen rules (nine rig rows: Cinna..Beatrix undressed; G4's 29 codec rows; G6's nine idle
frames), on s140+ the live table (rows 9-12 dressed; 38 rows; thirteen frames [.., 40, 30, 40, 45]); G7e `wire 5467`
(a Blank-led guest's own body) shows Blank's own loco clip on s140+ and my raw clip on s139 -- so legs I and G stay GREEN
on both engines, and G's lever (rule-s138) reds G7e with G7a / G7d.
CALIBRATION (s140): on the live s139 (COOP_CALIBRATE=1) exactly OLD_PREDICTED -- every S / W / X / N / T check: `self`
refused before the step ("not reached"; S4, S8 and N1 too, never green), T2's proof absent -- with INI, OR, S0, P0, PRE,
PF, R and legs I / G GREEN (judged by s139's rules). On s140, COOP_CALIBRATE=1 COOP_DRESS_CAL=<lever> reds exactly
LEVER_PREDICTED[<lever>], each a JUDGED red (a lever row reading "not reached" is UNPROVEN): self-off (`self off` in place
of every dress spec) every dressed row (S4, S8 -- the host's ghost --, T2 stay green); gate-0 N1; law-bframe T3;
law-attach S1 + W1 (src_attached 0; W1's break clip plays nothing); law-alias X2 (the gesture played the idle id itself:
frame_n stays the gesture's); law-timeline T1 + X3 (the jump slot on the alias's own count). A lever that bites
none of the selected legs is refused (S138-CAL red, naming the legs it bites). OFFLINE: the stand-in's `dressself` rung
(fakegame) models the arm, the dress order, the maps, the laws, the conductors and the warm return, and its FAULT LEVERS
(fakegame.DRESS_SELF_FAULTS) turn each row red on the shape it exists to catch; test_harness_netsync.py smokes these legs
against it in every mode -- never read S138-CAL offline: the engine is the calibration.

s140 ACCEPTANCE (the order matters: the calibration BEFORE the deploy):
  0. the bench field: `py studies/battle-coop/bench/selfdress_bench.py deploy` (it runs `py tools/deploy_field.py
     studies/battle-coop/bench/selfdress.field.toml --id 30606 --mod-folder FF9CustomMap-msgs`, then seats the conductors
     and re-runs the preflight) and the 8-11 seed `py tools/deploy_field.py studies/battle-coop/bench/coopsub.field.toml
     --id 30605 --mod-folder FF9CustomMap-msgs`, then ONE relaunch (both are new ids).
  1. on the live s139: COOP_CALIBRATE=1 -> S138-CAL green (exactly OLD_PREDICTED red).
  2. deploy s140; then this bench (GhostAs auto) green, and each lever: COOP_CALIBRATE=1 COOP_DRESS_CAL=self-off, gate-0,
     law-bframe, law-attach, law-alias, law-timeline -> S138-CAL green each.
  3. legs I + G again with [Netsync] GhostAs = '' (s139's step 2), and the s139 duo G9 -- which still steps Vivi, Garnet
     and the moogle only: the host's ghost dressing a SEATED CharacterId 8-11 member is S8's (the selftest site), its
     transport site a sitting box.

LEG F (s141) -- THE DRESS POLISH (R3-FIELD-MODEL-AUDIT.md 2.4 and 4.5 -- the audit OVERRIDES the design --, with the
orchestrator's O1-O11, binding: Cinna walks silently; MapFootstep reads only the rig rows; the footstep witnesses; held
props to the worn rig's hand (D3); the mesh-op drop; the lighting fallback and the ghost's (D6); the `polish` lever (D7)).
On s140 a dressed body is lit by the mapconfig's DEFAULT row, walks with Zidane's footstep keys (which never match its
clip: it is silent) and holds a prop on Zidane's bone index, on the wrong rig part. s141 maps the keys onto the worn rig's
own clip and footfall frames (Steiner's 925 in both slots, D4; a rig with no stock footfall -- Quina, the moogle, Cinna --
DROPS codes 16-19), lights the body by its SOURCE (98) row when its own model has none (and the ghost by the local player's
stand-in row), remaps bone 12 / 13 to the rig's R_hand / R_hand_end and drops a mesh op on the dressed body. Every s141 count
and witness is PER FIELD LOAD (reset beside the stock footstep table: a warm return reads one load). Each F load pulls
ONLY leg F's own lever (`selfdress polish off` under COOP_DRESS_CAL=polish-off), never an s140 lever: leg F has no row for
those and stays green under each. EVERY EXPECTED VALUE IS READ OFFLINE -- the oracle hook `_f_oracle` (part of S138-OR):
  * the stock field's footstep ops off the install's own `.eb` (the kit's .eb reader, :func:`eb_footsteps`): the
    controlled entry's Init CHRFX ops and those of the function Main_Reinit runs on the player -- on 250 Zidane_Init's
    twelve (codes 16 / 17 / 18 on 25@4, 25@13, 38@0, 38@8; Arg4 919 / 914 / 1) and, through RunScriptAsync(0, 250, 13),
    Zidane_13's same twelve;
  * each judged rig's footfall pairs and step sound from the INSTALL CENSUS (studies/battle-coop/dress-census/polish.json
    `b_steps`: the modal RunModelCode(16) frames per rig walk / run clip over the 817 stock scripts; `polish_census.py
    --check` re-derives it) -- Freya 2553 {4, 16} / 2558 {0, 9}, Steiner 1996 {4, 14} / 2005 {0, 9} with 925, Zidane 25 {4,
    13} / 38 {0, 8}, the moogle and Cinna none (O1) -- the walk / run ids the census counts (their clip NAMES the s140
    oracle's: the kit's tables);
  * the expected `steps` per rig: the census's OWN pure twin (polish_census.expected_steps: MapFootstep, then stock
    FF9Snd's find-or-create table) replayed over those ops -- polish on, off, and the warm return's;
  * the light: the stock field's MapConfigData (the census's load_mcf: ff9mapkit.mapconfig.parse) through the census's pure
    light_color / ghost_light_color, per WALKMESH FLOOR (and 255, none: the default light); the floor is the ENGINE's
    `self.light_floor` -- the FF9FieldCharState.floor fldmcf lit the body by, written with the tint: the oracle's INPUT,
    never its answer -- and the kit's stock walkmesh (floors_at) at the LIVE published x / z is reported beside it (the two
    disagreeing is a red with both shown); the published `player.floor` is s83's dead battle-entry snapshot (channel.py
    player_floor_battle_snapshot), never read. Field 250's rows: 0xFFFF (16, 16, 16), 176, 98 (10, 12, 15); floor 0's
    light (0, 0, 0) -> the 98 row (80, 96, 120), the default (128, 128, 128); floors 1-2 (-3, -3, -4) -> (56, 72, 88) /
    (104, 104, 96). (The kit's walkmesh puts 250's entrance-0 spawn (2921, -1830) on floor 2: (56, 72, 88) there.);
  * F2d's: the bench field's player footstep registrations off the DEPLOYED 30606 .eb (the kit template's twelve: 16 /
    17 / 18 on 25 @ 4 / 13, 38 @ 0 / 8, Arg4 912) and the conductor's op checked against field 2930's own bytes (the
    stock form), replayed for the moogle through the census twin WITH the engine's guard (expected_steps(guard=True)):
    one load, then the op -- +1 dropped, +0 passed, steps [] -- and its PRECONDITION checked, not assumed: the player Init
    is the footstep table's ONLY writer (:func:`bench_table_writers`: every other CHRFX 16-18 in the deployed .eb is the
    named problem `f2d table` and F2d reads "not reached" -- the engine's guard reads the GLOBAL table, the replay the
    player's registrations alone);
  * F8's rig hand off the install's SKIN (polish_census.skin_hand over the kit's models.extract.read_model -- NEVER
    labels_for, which sits one bone toward the shoulder on Steiner's arm: :func:`hand_oracle_read`), cross-checked
    against the census's e_hands (stock's own AttachObject on the same body): its R_hand_end bone NAME.
  CROSS-CHECKS, each a named problem: the census's clip ids against the kit's, the twin's rig row (battlewire.RIGS: pairs,
  step sound, hand bones), 250's ops and mapconfig rows against battlewire.FIELD250_STEPS / FIELD250_MCF, 30606's player
  registrations against battlewire.KIT_PLAYER_STEPS (the stand-in's), the F2d op against field 2930's.
  -- the "bench" phase (after leg T): the proof, then the bench field 30606 (S140-PF: its preflight FAILS CLOSED, and an
     s140-seated .eb -- no F5 / F2d conductors -- reads STALE until `selfdress_bench.py deploy` re-seats it) --
  FP    the dress polish proof: 'dress polish selftest: OK (20 rows)' (the proof block, at S0; no key publishes it -- the
        line is the record).
  F5    `self steiner` + a warp: the caller's F5H (HideObject(250, 1)) on the dressed body -> DONE_F5H, mesh_drops +1 or more
        across it and `player.meshflags` 0 on every publish after it (the op DROPPED: stock sets bit 1 << 1 = 2); then F5S
        (ShowObject(250, 1)) -> DONE_F5S and meshflags 0 (restored in every mode: PosObj.copy carries meshflags into a warm
        return).
  F8    the same load -- STEINER: his HandBoneEnd is 16 (bone016, the 0-vertex end leaf under his gauntlet bone 15: the
        skin's, and where stock's own AttachObject puts the Sword on his body), never 13; his skeleton HAS a bone013 (his
        upper arm), so `polish off` attaches there and reads a real parent 'bone013' (a judged red); his R_hand / R_hand_end
        are distinct (15 / 16), so a swapped pair shows too (Freya's hand is a leaf: 12 / 12) --: F8A (AttachObject(the
        cup 4, 250, 13)) -> DONE_F8A, attach_remaps +1 and attach_notes +0 across it, `attach_last` == {uid 4, bone_in 13,
        bone_out 16, parent 'bone016'} (the parent the carried go's LIVE transform parent, matched by NAME against the
        skin's R_hand_end); F8D (DetachObject(4)) -> DONE_F8D and the parent no longer that bone (read live, never a
        value cached at the attach).
  F2d   THE EMPTY-TABLE GUARD's in-game witness: `self moogle` + a fresh load of 30606 (the player's Init registers the
        twelve keys, the moogle DROPS them all: the table is EMPTY), then the caller's F2d -- RunScript(2, 250, 51) into the
        PLAYER's entry (CHRFX acts on gCur): field 2930's RunModelCode(19, 190, 4, 0) verbatim (a code 19 on a NON-pair id:
        the rule passes it, only the guard can drop it) -> DONE_F2D, steps_dropped +1, steps_passed +0, `steps` [], the
        s140 `faults` +0, no fault / IndexOutOfRangeException line since the trigger, and the guard's own line ("from an
        EMPTY table -- dropped"). WEDGED_F2D (the player's function never returned: the caller's bound) is a judged red,
        recovered by a warp.
  -- the "self" phase, on the stock field (250), after leg S --
  F1    `self freya` + a FRESH load (entrance 0): `steps` as (anim, frame) pairs in TABLE order == the oracle's Freya set
        [(2553, 4), (2553, 16), (2558, 0), (2558, 9)], steps_dropped 0, steps_passed 0 (per load) -- and no duplicate key
        (a STOCK invariant, never a polish witness: fldchar's find-or-create never appends a key twice). Every F row first
        PINS the body it asked for (player.model the oracle's, self.rig), else "not reached".
  F4    the same publish: light_row 98 (the SOURCE row: her 192 has none on 250) and light_rgb == the census tint of the 98
        row on `light_floor` (the floor fldmcf lit her by), the kit walkmesh's floor under the published x / z reported
        beside it (a disagreement is red) -- with player.model 192 (an UNDRESSED Zidane reads his OWN 98 row's colour and
        publishes no light_row: the colour alone proves nothing).
  F4g   the selftest mirror's ghost wearing the dressed model (192: GhostGuard shows the dressed wire as it is) re-tints by
        the LOCAL player's stand-in row: `netsync.dress.ghost.light_row` 98 (-1 until its first re-tint this load) AND
        `ghost.light_rgb` -- the tint ApplyGhostLighting WROTE, read off the ghost's material -- the 98 row's on the
        player's `light_floor` (the witness the row cannot give: a re-tint that set the row and lost the write).
  F1b   walk the dressed Freya ~3 s (harness input: four ALTERNATING holds of F_WALK_TICKS ticks -- never more than one hold
        from the spawn, 250's exits sit 3000u+ away --, each watched; it must MOVE F_MIN_MOVE_TICKS+ field ticks, else "not
        reached") -> steps_fired +2 or more across the walk (FF9Snd's own frame match on HER clip: the witness the table
        cannot give), steps_fired_player +0.
  F6    the same load, then `dioboot` / `dioleave` (W1's lane, here on 250: it has Main_Reinit and random battles --
        SetRandomBattleFrequency(128), encratio > 0; `noencounter` is a booster, never encratio -- so the diorama primes a
        WARM return; the warm diorama return on 250 is two-machine proven): last_return 'warm' (else "not reached"), the body
        still Freya, `steps` == the oracle's warm-return replay (Main_Reinit re-runs the twelve into the table the load
        reset cleared: the same four), the counters ONE load's (steps_fired 0 at the return: the per-load reset -- judged
        only when the publish before the boot CARRIED F_FIRED_MIN+ fires: F1b's settled publish, or a fresh walk's when
        F1b's was taken over -- else "not reached"), then a walk -> steps_fired +2 or more.
  F2    `self moogle` + a fresh load: steps [], steps_dropped 12 (the field's twelve, per load), steps_passed 0, the s140
        `faults` +0 and no 'self-dress fault' / IndexOutOfRangeException line since the warp. (250 runs no code 19: this
        half catches a HOOK fault only -- the code-19 guard's in-game witness is the bench row F2d.)
  F2c   (O1) `self cinna`: as F2 -- no stock footstep registration for any Cinna body (107 / 661), so her ops drop.
  F7    `self steiner`: his set [(1996, 4), (1996, 14), (2005, 0), (2005, 9)] with sndEffectID[0] -- code 16's slot, the
        one `steps` publishes -- 925 on EVERY key (D4; code 17's slot [1] is PolishSelfTest's foot row's, never read here).
  F3    (the control) `self off` + a fresh load: Zidane's own set [(25, 4), (25, 13), (38, 0), (38, 8)], 0 dropped (no hook
        on an undressed body); a walk -> steps_fired_player +2 or more, steps_fired +0.
  Every lever is released at each step's end (`clear`: the polish back on); S138-R holds `polish off` into the reset on an
  s141 engine and reads `self.polish` back TRUE (ReleaseBench's line names `polish`).
NOT PROVEN BY LEG F: footstep keys on Zidane's OTHER walk / run ids (COLD_WALK, SWORD_WALK / RUN on 62-64, ...) pass
unmapped and never fire -- but every such stock field also registers the plain 25 / 38 keys, which DO fire on the rig's
native walk / run (s140 maps the variant clip there): the dressed body steps with the plain-walk sound at its own footfalls
(Blank and Marcus on 62-64, Cinna and the moogle silent; on 2705's FRA_WALK, where stock Zidane is silent) -- KNOWN, census
open issue 1; a held prop's ORIENTATION (it keeps Zidane's bone-local offset and an identity rotation: in the rig's hand,
turned to that bone's axes -- KNOWN, cosmetic); a kit whole-body HideObject (dropped with every mesh op: the dressed body
stays visible -- KNOWN); the twin ladder / jump clips (amendment 7: not built, O2), the shadow SIZE on the 98 fallback
(amendment 4's nit: not built, O3 -- 250 calls DisableShadow every frame), a prop on a non-player carrier, a prop on a warm
return (stock restores attachTargetBoneIndex only on 1508; elsewhere a re-run AttachObject passes the hook again), the
other hard-coded geoAttach sites (field 112's glasses carry on NPCs;
the 62 / 3010 bone-19 override keys on King Leo's entry), a REAL client's footsteps off a host's section 8 (the selftest
role's lane: the same hooks; a duo or sitting box), and a kit field's light (no MCF: light_row -1 -- the stand-in's row).
CALIBRATION (s141): on the live s140 (COOP_CALIBRATE=1) exactly S141_OLD_PREDICTED -- EVERY F row, each red on what s140
lacks (the dress itself runs there): F1 / F2 / F2c / F6 / F7 read `steps` ABSENT; F1b and F3 TOO (the audit's "F3 green on
s140" assumed `steps`: s140 publishes no footstep table and no fired count -- only the s138 instrument, player.anim / clip,
25 / 38 while moving, can be read there); F4 / F4g read `light_row` / `ghost.light_row` absent (the body IS on the default
row there, unwitnessed); F5 reads mesh_drops absent with meshflags 2 (the mesh hidden: the behavioural red); F8 reads
`attach_last` absent; F2d reads `steps_dropped` absent -- and NO throw there: with no hook the player Init's twelve
register, the table holds Zidane's four and 2930's 19 on 190 is stock's no-op (the hazard is the polish's own drop); FP
finds no proof line. Before s140 (s137-s139) `self` is refused before the step: every F row "not reached" (FP red: no
line). On s141, COOP_CALIBRATE=1 COOP_DRESS_CAL=polish-off reds exactly S141_LEVER_PREDICTED -- F1, F1b, F2, F2c, F2d, F4,
F4g, F5, F6, F7, F8 -- each a JUDGED red (a row reading "not reached" is UNPROVEN: S138-CAL fails naming it): every
footstep op registers as read (Zidane's four keys on every rig, nothing dropped; nothing fires on the rig's own clip; F2d's
19 meets Zidane's four, so the guard has nothing to guard: +0), the default row (65535) for the body and the ghost, the
mesh op runs (meshflags 2), the prop stays on bone 13 ('bone013'). F3 (an undressed body: no hook) and FP (the proof never
reads the live lever) stay GREEN. OFFLINE: the
stand-in's `dresspolish` rung (fakegame) models MapFootstep into the stock table, the fired footsteps, the light rows and
the tint, the ghost's row, the mesh-op drop and the prop remap per load, and its FAULT LEVERS (fakegame.DRESS_POLISH_FAULTS)
turn each row red on the shape it exists to catch; test_harness_netsync.py smokes leg F against it in every mode.

s141 ACCEPTANCE (the order matters: the calibration BEFORE the deploy):
  0. re-seat the bench field (its caller gained F5's and F2d's conductors, its player F2d's function), with the owner's yes:
     `py studies/battle-coop/bench/selfdress_bench.py deploy` (30606 is registered: it re-deploys in place, no relaunch;
     the runners do it only under RESEAT=yes); S140-PF then reads CLEAN, never STALE.
  1. on the live s140: COOP_CALIBRATE=1 -> S138-CAL green (exactly S141_OLD_PREDICTED red; every earlier leg green).
  2. deploy s141; then this bench (GhostAs auto) green, COOP_CALIBRATE=1 COOP_DRESS_CAL=polish-off COOP_DRESS_LEGS=F ->
     S138-CAL green, and each s140 lever again on legs S / W / X / N / T.
  3. legs I + G + S + F again with [Netsync] GhostAs = '' (F4g's mirror under the other GhostAs), and the duo G9
     (coop_dress_wire.py). studies/battle-coop/bench/run/cal141.example.sh and full141.example.sh run them.

RUN (from THIS worktree, so its tools/ and ff9mapkit/ are the ones imported):
    py tools/play.py studies/test-harness/scenarios/coop_self_dress.py --field 250
    COOP_CALIBRATE=1 py tools/play.py studies/test-harness/scenarios/coop_self_dress.py --field 250    (on the s137 DLL)
    COOP_CALIBRATE=1 COOP_DRESS_CAL=rule-s138 py tools/play.py studies/test-harness/scenarios/coop_self_dress.py --field 250
        (leg G's lever, on s139)      COOP_DRESS_LEGS=G ... (leg G alone; it still needs the seed, so PRE holds)
    COOP_CALIBRATE=1 COOP_DRESS_CAL=law-bframe COOP_DRESS_LEGS=T py tools/play.py studies/test-harness/scenarios/coop_self_dress.py --field 250
        ([s140] one lever on the legs it bites; studies/battle-coop/bench/run/full140.example.sh runs them all)
    COOP_CALIBRATE=1 COOP_DRESS_CAL=polish-off COOP_DRESS_LEGS=F py tools/play.py studies/test-harness/scenarios/coop_self_dress.py --field 250
        ([s141] leg F's lever, on s141; full141.example.sh runs it with every earlier lever and leg)
  PowerShell has no per-launch form: a `$env:` value PERSISTS in that shell -- clear it after each run:
    Remove-Item Env:COOP_CALIBRATE, Env:COOP_DRESS_LEGS, Env:COOP_DRESS_CAL -ErrorAction SilentlyContinue
"""
from __future__ import annotations

import os
import re
import shutil
import sys
from itertools import takewhile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file
import _selfdress_field as sdf                             # noqa: E402 - [ff9mapkit netsync s140] the bench field's contract

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
#: the caches the kit's readers WRITE into the install's StreamingAssets on a miss -- the events-bundle cache
#: (ff9mapkit.extract._events_bundle, reached by a stock field's p0data read) and the field index (extract.INDEX_NAME,
#: built by resolve_field: reached by any kit read that names a field the id table does not know). The bench never creates
#: either (the install is READ-ONLY): a missing one reads "not reached" for every field that needs the install. (read_model
#: writes nothing; the bench names events by the id table or the DictionaryPatch registration, never by resolve_field --
#: [ff9mapkit netsync s140] the index is listed so any read that could still build it is refused, never run.)
KIT_CACHE_FILES = (".ff9mapkit-events-bundle.txt", ".ff9mapkit-field-index.json")
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
#: [ff9mapkit netsync s140] ...and a CharacterId 8-11 member's own body (GEO_SUB_F0_BLN, Blank's): the owner's 8-11 rows BY
#: STAGE -- on s139 it has no rig (shown, playing my raw clip), on s140+ rig 11 (shown, moving with BLANK's own loco clip)
G_WIRE_SUB = 5467
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
        "S139-G7e": "[s140] THE OWNER'S 8-11 ROWS BY STAGE, on the guard: `wire 5467` (a Blank-led guest's own body, "
                    "CharacterId 10) -> the ghost SHOWS 5467, rig -1 -- on s140+ moving with BLANK's own loco clip (rig 11: "
                    "the owner's row), on s139 playing my raw clip (no rig there: Cinna..Beatrix undressed) -- the probed "
                    "stage's twin",
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
                "S139-G7e", "S139-G8")


# ---- [ff9mapkit netsync s140] LEGS S / W / X / N / T -- THE GUEST DRESSES ITSELF (see the docstring's s140 section)
DIO_FIELD = cb.FIELD                       # 30602 LOCKT2: entry-0 tag-10 Main_Reinit + [encounter] -> a diorama returns WARM
SELF_FIELD = sdf.FIELD_ID                  # 30606 SELFDRESS (FF9CustomMap-msgs): the twin, the late entry, the caller
#: the `self` names the s140 rows dress as (NetSyncSelfDress.SelfNames); every row's VALUES come from the s140 oracle
S_RIG = "freya"                            # S1 / S2 / S5, W, X, N: rig 4 -- GEO_MAIN_F0_FRJ, no break clip
S_MOOGLE = "moogle"                        # S3's answer: `self auto 2` + `empty 2` (every named slot empty)
S_AUTO_MASK = 2                            # ...the slot-1 bit; `empty 2` empties it on whatever party the save holds
S_SUB = "blank"                            # S6, the owner's 8-11 row (CharacterId 10, rig 11) -- by NAME
#: S7 / S8: the SEATED 8-11 member -- Blank seated by the COOPSUB seed (studies/battle-coop/bench/coopsub.field.toml:
#: [party] remove = steiner, add = blank; CharacterOldIndex 11 -> CharacterId 10), then `self auto <his bit>` (the arm
#: through the live FF9.party read) and `ghost <his bit>` (the host rule's dressed ghost over a plain-Zidane wire body)
S_SEAT = "blank"
SUB_PARTY_FIELD = 30605                    # COOPSUB (FF9CustomMap-msgs): its Main_Init's RemoveParty(3) + B_PARTYADD(11)
SUB_PARTY_TOML = cb.REPO / "studies" / "battle-coop" / "bench" / "coopsub.field.toml"
#: W1 / W2: rig 3 -- GEO_MAIN_F0_STN, whose BREAK clip (119 ANH_MAIN_F0_STN_BREAK_1, 110 frames) no 30602 entry lists:
#: only AttachDress at the warm rebuild (site b) puts it back on the rebuilt go, so CheckSleep's play of the stored sleep
#: slot is W1's witness of site (b) -- on Freya (no break clip: sleep 0) CheckSleep plays nothing either way
W_RIG = "steiner"
T1_RIG = "garnet"                          # T1's discriminator: a 30-frame idle (alias) under COLD_FAINT_1's `< 58`
T1_CONTROL = "moogle"                      # T1's control: a 72-frame idle reaches 58 with or without the law
T3_RIGS = tuple(BW.RIG_NAMES)              # T3 on EVERY rig row (zidane = stock: `self zidane` disarms "zidane")
#: the rigs the s140 oracle reads: every name a row dresses as (all thirteen: T3's)
S_ORACLE_RIGS = T3_RIGS
#: the GEO name the kit's table gives each non-main rig's model (a main's model is the kit's playerswap.CHARACTERS'): the
#: owner's 8-11 rows wear their F0 body (GEO_SUB_F0_BLN = 5467 -- never the Pluto Knight's F1 190)
RIG_GEO_NAMES = {"moogle": "GEO_NPC_F0_MOG", "cinna": "GEO_SUB_F0_CNA", "marcus": "GEO_SUB_F0_MRC",
                 "blank": "GEO_SUB_F0_BLN", "beatrix": "GEO_SUB_F0_BTX"}
#: the STOCK fields whose scripts wear each non-main rig's model -- its eye byte's oracle (the modal SetModel(model, eye) of
#: the install's own script, read through the kit's events-bundle cache): 407 Dali/Storage Area (the moogle), 50 Prima
#: Vista/Cargo Room (Cinna, Marcus, Blank), 767 Burmecia/Palace (Beatrix)
EYE_FIELDS = {"moogle": (407,), "cinna": (50,), "marcus": (50,), "blank": (50,), "beatrix": (767,)}
#: the census the oracle is CROSS-CHECKED against (never read as the oracle): rows 9-12's model and eye byte
CENSUS_JSON = cb.REPO / "studies" / "battle-coop" / "dress-census" / "rigs_8_11.json"
#: the SOURCE clips the conductors play on the player (Zidane's own) -- their frame counts off p0data5 (the contract's
#: numbers a cross-check): X's BREAK1_LOOK, T1's COLD_FAINT_1
SOURCE_CLIPS = {"x": (sdf.ANIM_X, sdf.ANIM_X_FRAMES), "t1": (sdf.ANIM_T1, sdf.ANIM_T1_FRAMES),
                "j": (sdf.ANIM_J, sdf.ANIM_J_FRAMES)}
#: AtSetModel's dress line (one per dressed SetModel): field, uid, sid, the GEO, model, rig, eye, where the arm came from
DRESS_LINE = re.compile(r"self-dress: field (\d+) uid (\d+) sid (\d+): Zidane \(98\) -> (\S+) \(model (\d+), rig (-?\d+), "
                        r"eye (-?\d+)\) \[(\w+)\]")
DRESS_READ_S = 1.0                         # after an arrival: the identity is judged on the window's LAST free publish
OP_SETTLE_S = 0.5                          # after a `self` op: its own publish, held (the arm must not move before the load)
X_GRACE_S = 5.0                            # X2: control back within the gesture's hold (its source frames at 30 Hz) + this
X_AFTER_S = 1.5                            # X2: the publishes after DONE_X it judges
COND_READY_S = 20.0                        # 30606: the caller's READY bit (and control) after a load
COND_TIMEOUT_S = {"x": 20.0, "t1": 20.0, "t3": 40.0, "n3": 10.0, "j": 10.0,
                  # [ff9mapkit netsync s141] F5 / F8: one instant op each (no DisableMove), DONE on the caller's next tick;
                  # F2d: RunScript into the player, its F2D_END within ~2 ticks (the caller's own bound: F2D_LIMIT)
                  "f5h": 10.0, "f5s": 10.0, "f8a": 10.0, "f8d": 10.0, "f2d": 10.0}
N3_AFTER_S = 1.0                           # N3: the publishes after DONE_N3 its late entry is read on
IDLE_PAST_S = 62.0                         # W1: past the idle timer's longest draw ((200 + 255) << 2 = 1820 ticks at 30 Hz)
TICK_HZ = 30.0                             # the field tick: a clip's frames play at aspeed 16 = one frame a tick
SOURCE_GEO = "GEO_MAIN_F0_ZDN"             # AttachDress's SOURCE list: the field's Zidane EventAnimation line
IDLE_NULL_RUN = 5                          # W1: this many idle publishes in a row playing NOTHING (clip / anim_geo null)
J_SLOP_S = 0.5                             # X3: the landing's wall-clock slack over its tick count (a tick + publish cadence)
#: [Netsync] SelfDress values that keep the knob ON (absent = 1, quotes accepted): SelfDress=0 switches off the guest's own
#: dress (owner D1) -- every s140 row would read it, so the precondition refuses it (the bench's knob is `self off`)
SELF_DRESS_OK = ("", "1")
#: the s140 calibration levers (COOP_DRESS_CAL): `self off` in place of every dress spec, `gate 0`, one `law <name> off`
CAL_SELF_OFF = "self-off"
CAL_GATE_0 = "gate-0"
CAL_LAWS = {"law-bframe": "bframe", "law-attach": "attach", "law-alias": "alias", "law-timeline": "timeline"}
S140_LEVER_MODES = (CAL_SELF_OFF, CAL_GATE_0) + tuple(CAL_LAWS)


def _catalog_s() -> dict:
    return {
        "S140-S1": "`selfdress self freya` + a re-warp of the stock field (entrance 0) -> the controlled body is the oracle's "
                   "Freya: model 192, `geo` GEO_MAIN_F0_FRJ, `body` '192' (its texture stem), `eye` -376 (-4 x the kit's "
                   "eye byte 94), at rest `anim_geo` GEO_MAIN_F0_FRJ; `self` why 'dressed', rig and want_rig 4, want_char 4, "
                   "from 'bench', uid == player.uid, net_byte 5, src 98, confirmed +1 since the warp; AttachDress AT "
                   "THIS LOAD's SetModel (amendment 2 site a): attach_cold +1 and attach_warm +0 since the warp, then "
                   "src_attached > 0 and src_list_clips == the field's GEO_MAIN_F0_ZDN EventAnimation line (the SOURCE "
                   "list, read offline); ONE dress line for the load; the `self` op alone moves neither the arm nor the "
                   "body (it arms at the FIELD LOAD only)",
        "S140-S2": "the dressed Freya judged per field tick (leg I's walk probe): mid-move her walk or run id (2553 / 2558 -- "
                   "either), its clip playing in GEO_MAIN_F0_FRJ; at rest (REST_S, inside the idle timer) the clip NAMED "
                   "ANH_MAIN_F0_FRJ_IDLE (her break clip accepted where she has one: none); `anim_geo` GEO_MAIN_F0_FRJ on "
                   "EVERY publish of the probe and the rest window, read live -- never a ZDN folder",
        "S140-S5": "the selftest mirror's ghost of this guest wears 192: the dressed body is the wire's own (GhostGuard shows it "
                   "as it is, its raw clip) -- the oracle's Freya model, and the stage's twin (battlewire.selftest_dress) on "
                   "the dressed rest publishes",
        "S140-S3": "`self auto 2` + `empty 2` + a re-warp -> the MOOGLE: model 220, GEO_NPC_F0_MOG, body '220', eye -200 (-4 "
                   "x 50, read off a stock script); rig 8, want_char 255 (the moogle has no CharacterId)",
        "S140-S6": "THE OWNER'S 8-11 ROW: `self blank` + a re-warp -> Blank's own model (5467, GEO_SUB_F0_BLN -- never the "
                   "Pluto Knight's 190), body '5467', eye -348 (-4 x 87, read off a stock script), rig 11, want_char 10; at "
                   "rest his idle NAMED ANH_SUB_F0_BLN_IDLE playing in his own folder",
        "S140-S4": "THE TEARDOWN LAW: `clear` + `self off` leave the LIVE body as it was (model, body, GEO, eye, self.rig, "
                   "net_byte read BEFORE the `clear` == after the ops, held OP_SETTLE_S -- S6's Blank, or whatever the load "
                   "before wore), then a re-warp -> Zidane again at the NEXT SetModel: model 98, body '98', eye -372, "
                   "GEO_MAIN_F0_ZDN; `self` why 'model 0', rig -1, net_byte 0, bench_self 'off'",
        "S140-S7": "THE OWNER'S 8-11 ROW, SEATED: through COOPSUB (30605: [party] remove steiner, add blank) the live party "
                   "holds CharacterId 10 (never the old index 11) in the slot the oracle's party read predicts; `self auto "
                   "<that slot's bit>` + a re-warp -> the body is Blank (5467, GEO_SUB_F0_BLN, body '5467', eye -348), "
                   "rig / want_rig 11, want_char 10 -- the arm off the LIVE FF9.party read (LiveSlotChars -> ResolveAuto "
                   "-> CharToRig)",
        "S140-S8": "...and the HOST side over the seated Blank: `self off` + a re-warp (the wire body is the plain Zidane), "
                   "then `ghost <his bit>` -> the mirror's ghost wears 5467 at rig 11 (GhostGuard dresses a 98 wire: the "
                   "s140 host rule over a live 8-11 slot), the twin's clip, playing, its body and GEO off the install -- at "
                   "rest AND moving (Blank's own walk / run clip per tick)",
    }


def _catalog_w() -> dict:
    return {
        "S140-W1": "THE WARM RETURN on 30602: `self steiner` + a warp (dressed), then `dioboot` / `dioleave` -> "
                   "last_return 'warm', returns +1; the body still Steiner (model, body, GEO, eye; `self.uid` unchanged, "
                   "net_byte 4) with NO new dress line (PosObj.copy carried the dress -- no SetModel); AttachDress AT THE "
                   "REBUILD (amendment 2 site b): attach_warm +1 and attach_cold +0 across the return, then src_attached > 0 "
                   "and src_list_clips == 30602's own SOURCE list (its EventAnimation line, read offline); at rest `anim` "
                   "== his idle id; idle past the inactive timer (IDLE_PAST_S): his BREAK clip plays by NAME "
                   "(ANH_MAIN_F0_STN_BREAK_1, clip_playing, frame_n == its 110 frames off p0data5 -- a clip only site (b) "
                   "re-attaches), never IDLE_NULL_RUN publishes in a row playing nothing, `anim_geo` GEO_MAIN_F0_STN on "
                   "every publish that has one; a walk: GEO_MAIN_F0_STN mid-move",
        "S140-W2": "(the cold control) a plain warp to 30602 -> dressed THROUGH SetModel: the oracle's Steiner, confirmed "
                   "+1, ONE dress line for the load",
    }


def _catalog_x() -> dict:
    return {
        "S140-X1": "the bench field's X conductor (RunAnimationEx(250, 186 ZDN BREAK1_LOOK) + WaitAnimationEx) on the "
                   "dressed Freya: DONE_X; MapAndAttach mapped the gesture (remaps +1); it showed (the anim or frame_n moved "
                   "off the idle's); every publish from the trigger to DONE plays a clip NAMED ANH_MAIN_F0_FRJ_IDLE (the "
                   "alias by NAME, never by id) in GEO_MAIN_F0_FRJ -- never a ZDN folder",
        "S140-X2": "after X (DONE_X): the stored idle (2556) plays with `frame_n` == her idle's frame count off p0data5 (50: "
                   "DefaultAnim's SetAnim saw ANOTHER id -- the ALIAS proof, amendment 4), and control is back within the "
                   "gesture's hold (its 70 source frames at 30 Hz) + 5 s of the trigger",
        "S140-X3": "THE JUMP SLOT ON THE SOURCE TIMELINE: the J conductor (field 404's ladder mount, no arc: "
                   "SetJumpAnimation(10687 LADDER_1_1, 2, 6) / RunJumpAnimation / RunLandAnimation in the player's own "
                   "entry) on the dressed Freya ends DONE_J; every publish playing the jump slot (her idle ALIAS, by NAME) "
                   "runs on frame_n == LADDER_1_1's 8 frames off p0data5 (never the alias's 50), and the landing (J_LAND "
                   "-> J_END) lasts no longer than stock's tick count + J_SLOP_S",
    }


def _catalog_n() -> dict:
    return {
        "S140-N1": "`self freya` on 30606: the TWIN (by its BUILT sid 2, never by model -- its InitObject precedes the "
                   "player's: S140-PF) stays 98 (`objects[sid 2].model`) and skip_npc +1 since the warp (the player gate), "
                   "while the player's BODY is the oracle's Freya (model, body stem, GEO, eye); exactly ONE dress line for "
                   "the load, the player's sid's",
        "S140-N3": "the N3 conductor InitObjects the LATE entry (a 98 whose never-run function holds DefinePlayerCharacter) "
                   "after the player's CC -> skip_second +1, the late entry (sid 3) stays 98 with NO dress line for sid 3 "
                   "since the trigger, control unchanged (the player's uid, control back, the body still the oracle's "
                   "Freya)",
        "S140-N2": "`gate 0` + a re-warp (the gate's calibration, restated): skip_npc +0, the twin AND the player both wear "
                   "192 (control is null at both SetModels) -- the player's BODY the oracle's Freya, and exactly TWO dress "
                   "lines for the load, the twin's sid and the player's --, `self.gate` false",
    }


def _catalog_t() -> dict:
    return {
        "S140-T2": "the self-dress proof: `self.selftest` 'ok' and the proof line 'self-dress selftest: OK (29 rows)' -- its "
                   "T2 row (2934's 12429 / 1601's 3005 map OFF their raw id on every rig: the effMapNo checks must read the "
                   "raw `anim`) among them",
        "S140-T1": "THE SOURCE TIMELINE: on Garnet (rig 2, a 30-frame idle) the T1 conductor (RunAnimationEx(250, 2572 "
                   "COLD_FAINT_1), then `while GetEntryAnimFrame(250) < 58`) finishes -- DONE_T1, never WEDGED_T1 -- with "
                   "timeline_kept +1; the moogle (a 72-frame idle) finishes too: the CONTROL (it ends without the law -- "
                   "never the discriminator)",
        "S140-T3": "THE B_FRAME LAW: on EVERY rig (`self <name>` + a re-warp each, zidane .. beatrix) the body wears that "
                   "rig's model (Zidane undressed: 'zidane') and the T3 conductor's field-2705 loop in the player's entry "
                   "(`GetEntryAnimFrame(255) < GetAnimDuration(8847) - 1`) finishes -- DONE_T3 and T3_END, never WEDGED_T3 "
                   "(read as red, recovered by the next warp) -- with bframe_remaps +1 on each dressed rig and +0 on Zidane",
    }


S_CHECKS = tuple(_catalog_s())
W_CHECKS = tuple(_catalog_w())
X_CHECKS = tuple(_catalog_x())
N_CHECKS = tuple(_catalog_n())
T_CHECKS = tuple(_catalog_t())
S140_CHECKS = S_CHECKS + W_CHECKS + X_CHECKS + N_CHECKS + T_CHECKS
#: COOP_CALIBRATE=1 on an engine BEFORE s140 (the live s139 at writing): EVERY s140 check -- the `self` op refused before
#: the step ("not reached": S4, S8 and N1 too, never green), T2's proof absent. Everything else (INI, OR, S0, P0, PRE, PF,
#: R and legs I / G judged by the probed stage's rules) stays green.
OLD_PREDICTED = S140_CHECKS
#: ...on s140 under each of its levers (COOP_DRESS_CAL), exactly these checks red -- each a JUDGED red (a lever row that
#: reads "not reached" is the lever UNPROVEN): `self off` (every dress spec sent as `off`): every dressed row (S4 stays
#: green: it IS `self off`; S8 is `self off` + the HOST's ghost; T2 runs at S0); `gate 0`: the twin dresses (N1); `law
#: bframe off`: 2705's loop wedges on every dressed rig (T3); `law attach off`: no source list, no rig set (src_attached 0:
#: S1 at SetModel, W1 at the warm rebuild -- and there the break clip plays nothing); `law alias off`: the gesture plays the
#: idle id itself, frame_n stays stretched (X2); `law timeline off`: the gesture plays on the alias's own 30 frames, `< 58`
#: never ends (T1), and the jump slot runs on the alias's 50 frames (X3).
LEVER_PREDICTED = {
    CAL_SELF_OFF: tuple(c for c in S140_CHECKS if c not in ("S140-S4", "S140-S8", "S140-T2")),
    CAL_GATE_0: ("S140-N1",),
    "law-bframe": ("S140-T3",),
    "law-attach": ("S140-S1", "S140-W1"),
    "law-alias": ("S140-X2",),
    "law-timeline": ("S140-X3", "S140-T1"),
}


# ---- [ff9mapkit netsync s141] LEG F -- THE DRESS POLISH (see the docstring's LEG F)
#: the rigs leg F dresses as (by NAME, NetSyncSelfDress.SelfNames); every VALUE comes from the s141 oracle (`_f_oracle`)
F_RIG = "freya"                            # F1 / F1b / F4 / F4g / F6: rig 4, a census pair of her own, no row on 250
F_DROP = "moogle"                          # F2 / F2d: rig 8, no stock footfall registration (the audit's own drop rig)
F_CINNA = "cinna"                          # F2c (O1): rig 9 -- no stock footstep registration for any Cinna body
F_STEINER = "steiner"                      # F7 (D4): rig 3 -- 925 in both slots in every stock registration
#: F5 / F8's rig (the bench field): Steiner -- his HandBoneEnd is 16 (bone016, the skin's end leaf under his gauntlet 15 --
#: stock's own Sword sits there on his body), never 13, and his skeleton HAS a bone013 (his upper arm), so `polish off`
#: attaches there and reads a real parent 'bone013' (a JUDGED red, never "not reached"); his R_hand / R_hand_end are
#: DISTINCT (15 / 16), so a swapped pair shows too -- Freya's 12 / 12 (her hand is a leaf: no end bone) would hide it
F8_RIG = "steiner"
F8_BONE = sdf.ATTACH_BONE                  # F8's bone: stock's held-item bone on Zidane (13 -- R_hand_end)
F_ZIDANE = "zidane"                        # F3's control: `self off` -- the undressed body's own keys
F_STEP_RIGS = (F_ZIDANE, F_RIG, F_DROP, F_CINNA, F_STEINER)
#: F1b / F3 / F6's walk: four ALTERNATING holds of this many field ticks (out, back, out, back: ~3 s of input, never more than
#: one hold's run from the spawn -- 250's exits sit 3000u+ away), each watched per publish
F_WALK_TICKS = 22
F_WALK_HOLDS = 4
F_MIN_MOVE_TICKS = 30                      # the walk must MOVE this many field ticks (else "not reached": no step to fire)
F_FIRED_MIN = 2                            # F1b / F3 / F6: footsteps fired over the walk
F_GHOST_LIGHT_S = 3.0                      # F4g: ApplyGhostLighting re-tints ~7 Hz while the ghost is driven (-1 until then)
F_AFTER_S = 0.5                            # F5 / F8: the publishes after a conductor's DONE it judges
#: the dress polish proof (no key publishes its verdict: the line is the record)
F_PROOF_LINE = BW.proof_ok(BW.PROOF_DRESS_POLISH, BW.DRESS_POLISH_SELFTEST_ROWS)
#: the lines a footstep fault would leave (F2 / F2c / F2d): the s140 hook's caught-fault line, and a VM throw (stock
#: DeleteChar indexing charSoundArray[-1] on an EMPTY table -- 250 runs no code 19: F2d is where a 19 meets one)
F_FAULT_LINES = ("self-dress fault", "IndexOutOfRangeException")
#: the empty-table guard's OWN line (MapFootstep's StepDroppedEmpty branch, once per load): F2d's 19 took that branch
F2D_GUARD_LINE = "from an EMPTY table -- dropped"
#: the install census the footfall pairs come from (studies/battle-coop/dress-census: polish.json, built by polish_census.py
#: from the 817 stock scripts and the install through the kit's readers; `--check` re-derives it) -- its pure twins
#: (expected_steps, light_color, ghost_light_color, load_mcf) are the oracle's arithmetic, never battlewire's
POLISH_CENSUS_JSON = cb.REPO / "studies" / "battle-coop" / "dress-census" / "polish.json"
POLISH_CENSUS_PY = cb.REPO / "studies" / "battle-coop" / "dress-census" / "polish_census.py"
#: CHRFX (RunModelCode) and the three run-script forms Main_Reinit may call the player's function with
OP_CHRFX = 0x88
OP_RUN_SCRIPTS = (0x10, 0x12, 0x14)        # RunScriptAsync (REQ), RunScript (REQSW), RunScriptSync (REQEW)
#: leg F's calibration lever (COOP_DRESS_CAL): `selfdress polish off` before every F load (the s141 polish bypassed)
CAL_POLISH_OFF = "polish-off"


def _catalog_f() -> dict:
    return {
        "S141-F1": "`self freya` + a FRESH load of the stock field: `steps` (as (anim, frame) pairs, in table order) == the "
                   "oracle's Freya set [(2553, 4), (2553, 16), (2558, 0), (2558, 9)] (the census pairs replayed over the "
                   "field's own footstep ops), steps_dropped 0, steps_passed 0 -- per load (no duplicate key: a stock "
                   "invariant, not a polish witness)",
        "S141-F1b": "walk the dressed Freya ~3 s (harness input, moving F_MIN_MOVE_TICKS+ field ticks) -> steps_fired +2 or "
                    "more, steps_fired_player +0 (FF9Snd's own frame match on her clip: the witness the table cannot give)",
        "S141-F2": "`self moogle` + a fresh load -> steps [], steps_dropped == the field's footstep op count (12 on 250, per "
                   "load), steps_passed 0, `faults` +0 and no fault / IndexOutOfRangeException line since the warp (250 runs "
                   "no code 19: a hook fault only -- F2d is the guard's)",
        "S141-F2c": "(O1) `self cinna` -> as F2: no stock footstep registration for any Cinna body, so her ops are DROPPED",
        "S141-F2d": "30606, `self moogle` (its Init's twelve keys dropped: an EMPTY table): the caller's F2d -- field 2930's "
                    "RunModelCode(19, 190, 4, 0) in the player's own entry -> DONE_F2D, steps_dropped +1 (the GUARD: the rule "
                    "passes a 190), steps_passed +0, steps [], `faults` +0, no fault / IndexOutOfRangeException line, the "
                    "guard's own line logged (WEDGED_F2D a judged red)",
        "S141-F3": "(the control) `self off` + a fresh load -> Zidane's own set [(25, 4), (25, 13), (38, 0), (38, 8)], 0 "
                   "dropped; a walk -> steps_fired_player +2 or more, steps_fired +0",
        "S141-F4": "the F1 load: light_row 98 (the SOURCE row: the rig model has none) and light_rgb == the census tint of the "
                   "98 row on `light_floor`, the floor fldmcf lit the body by ((56, 72, 88) at 250's entrance-0 spawn, floor "
                   "2; (80, 96, 120) on floor 0), the kit walkmesh's floor under the live x / z beside it (a disagreement "
                   "is red), the body Freya (an undressed Zidane reads his own 98 row's colour: the colour alone proves "
                   "nothing)",
        "S141-F4g": "the F1 load: the selftest mirror's ghost wears the dressed model, `netsync.dress.ghost.light_row` == 98 "
                    "(ApplyGhostLighting's stand-in row: the LOCAL player's netDressSrc) and `ghost.light_rgb` == that row's "
                    "tint on the player's `light_floor` (the tint it WROTE, read off the ghost's material)",
        "S141-F5": "30606, `self steiner`: the caller's F5H (HideObject(250, 1)) -> mesh_drops +1 or more and "
                   "`player.meshflags` 0 after it (the op DROPPED on the dressed body); F5S (ShowObject(250, 1)) -> "
                   "meshflags 0 (restored)",
        "S141-F6": "the F1 load, then `dioboot` / `dioleave` (a WARM return) -> the body still Freya, `steps` == the oracle's "
                   "warm-return set (Main_Reinit's twelve again: the same four), the counters ONE load's (steps_fired 0 at "
                   "the return, judged when the publish before the boot carried 2+ fires), then a walk -> steps_fired +2 or "
                   "more",
        "S141-F7": "`self steiner` + a fresh load -> his set [(1996, 4), (1996, 14), (2005, 0), (2005, 9)] with sndEffectID[0] "
                   "(code 16's slot, the one `steps` publishes) 925 on EVERY key (D4; slot 1 is the proof's foot row's)",
        "S141-F8": "30606, `self steiner` (HandBoneEnd 16): F8A (AttachObject(cup, 250, 13)) -> attach_remaps +1, "
                   "attach_notes +0, `attach_last` {uid 4, bone_in 13, bone_out 16, parent 'bone016'} -- the parent the "
                   "carried go's LIVE transform parent, matched by NAME against the skin's R_hand_end (the oracle); "
                   "F8D (DetachObject) -> the parent no longer that bone",
        "S141-FP": "the dress polish proof: 'dress polish selftest: OK (20 rows)' logged by the proof block (no key "
                   "publishes it: the line is the record)",
    }


F_CHECKS = tuple(_catalog_f())
#: COOP_CALIBRATE=1 on an engine BEFORE s141 -- EVERY F row. On s140 (the live DLL at writing) each is red on the keys s140
#: lacks (the dress itself runs there: `steps`, the fired counts, `light_row` / `light_rgb`, `ghost.light_row`, mesh_drops,
#: attach_* are ABSENT; F5 also reads meshflags 2, the behavioural red; F2d reads steps_dropped absent -- no throw there:
#: with no hook 30606's twelve register, so 2930's 19 meets Zidane's four, stock's no-op; FP has no proof line) -- F3 TOO:
#: the audit's "F3 green on s140" assumed `steps`, which s140 never publishes. Before s140 `self` is refused before the step
#: ("not reached").
S141_OLD_PREDICTED = F_CHECKS
#: ...on s141 under its lever (COOP_DRESS_CAL=polish-off: `selfdress polish off` before every F load), exactly these red --
#: each a JUDGED red (a lever row that reads "not reached" is the lever UNPROVEN): every footstep op registers as read
#: (Zidane's keys on every rig, nothing dropped, nothing fires on the rig's clip: F1 F1b F2 F2c F6 F7 -- and F2d: the
#: moogle's twelve REGISTER, so 2930's 19 meets Zidane's four and the guard, though it holds under the lever, has nothing
#: to guard: +0 dropped, steps Zidane's four -- the empty table is the polish's own drop), the default row (65535) for the
#: body and the ghost (F4 F4g), the mesh op runs (F5: meshflags 2), the prop stays on bone 13 ('bone013': F8). F3 (an
#: undressed body: no hook) and FP (the proof never reads the live lever) stay GREEN.
S141_LEVER_PREDICTED = {
    CAL_POLISH_OFF: ("S141-F1", "S141-F1b", "S141-F2", "S141-F2c", "S141-F2d", "S141-F4", "S141-F4g", "S141-F5", "S141-F6",
                     "S141-F7", "S141-F8"),
}
#: the F rows each phase judges: the 30606 bench rows ("bench", after FP -- the proof block, no field), the stock field's
#: ("self")
F_BENCH_CHECKS = ("S141-F5", "S141-F8", "S141-F2d")
F_STOCK_CHECKS = tuple(c for c in F_CHECKS if c not in F_BENCH_CHECKS + ("S141-FP",))


def _s140_leg(checks, catalog, steps: dict, pre, *, preflight: bool = False) -> dict:
    """[ff9mapkit netsync s140] One s140 leg's registry row: its `old` row (every check, on s137 / s138 / s139) and its
    lever rows (each lever's reds that are this leg's -- an empty row: it must stay green under that lever)."""
    return {"patch": 140, "catalog": catalog, "checks": checks, "steps": steps, "pre": tuple(pre), "oracle": (),
            "oracle_extra": "_s_oracle", "preflight": preflight,
            "old": {stage: (checks, ()) for stage in (137, 138, 139)},
            "lever": {mode: (tuple(c for c in LEVER_PREDICTED[mode] if c in checks), ()) for mode in S140_LEVER_MODES}}


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
    # [ff9mapkit netsync s140] the guest's own dress: on an engine before s140 every check reads red (`self` refused before
    # the step: "not reached"; T2's proof absent); on s140 each lever (COOP_DRESS_CAL) reds exactly LEVER_PREDICTED's rows
    "S": _s140_leg(S_CHECKS, _catalog_s, {"self": "_s_self"}, (SUB_PARTY_FIELD,)),
    "W": _s140_leg(W_CHECKS, _catalog_w, {"bench": "_w_bench"}, (DIO_FIELD,)),
    "X": _s140_leg(X_CHECKS, _catalog_x, {"bench": "_x_bench"}, (SELF_FIELD,), preflight=True),
    "N": _s140_leg(N_CHECKS, _catalog_n, {"bench": "_n_bench"}, (SELF_FIELD,), preflight=True),
    "T": _s140_leg(T_CHECKS, _catalog_t, {"bench": "_t_bench"}, (SELF_FIELD,), preflight=True),
    # [ff9mapkit netsync s141] the dress polish: F5 / F8 on the bench field (the "bench" phase, after T), the rest on the
    # stock field (the "self" phase, after S); on an engine before s141 every F row is red (s140: the s141 keys absent;
    # s137-s139: `self` refused before the step), on s141 its one lever (polish-off) reds S141_LEVER_PREDICTED
    "F": {"patch": 141, "catalog": _catalog_f, "checks": F_CHECKS, "steps": {"bench": "_f_bench", "self": "_f_self"},
          "pre": (SELF_FIELD,), "oracle": (), "oracle_extra": "_f_oracle", "preflight": True,
          "old": {stage: (S141_OLD_PREDICTED, ()) for stage in (137, 138, 139, 140)},
          "lever": {mode: (reds, ()) for mode, reds in S141_LEVER_PREDICTED.items()}},
}
# [ff9mapkit netsync s157] LEG L -- THE TWIN ROWS (a dressed body's Zidane ladder / jump plays the rig's own clip; NOT YET
# REGISTERED -- register it in LEGS after leg F, and append "L" to the kit's leg-list pins). Its `old` row at stages 137-156:
# every L check reads "cannot" (the probe finds no `self.twins`); its `lever` rows: `twin-off` -> the L1 L2 L4 clip and twin
# counter checks red, `twin-miss` -> the L1 L4 clip checks red and the miss checks green, `law-timeline` -> L1's frame_n and
# landing red, L2 green (moot: the same length). Steps: the s157 twin spec's bench plan (its Q1-Q6; `Q` itself is the kit's
# deliberately-unknown leg name, so the leg is L).
#: [ff9mapkit netsync s140] + "self", AFTER the bench phase (leg I's 30801 read follows the seed's warp there): the stock
#: field again, every leg-G lever released, leg S -- [ff9mapkit netsync s141] then leg F's stock-field rows
PHASES = ("stock", "seed", "seeded", "bench", "self", "close")
#: the engine stages the probe tells apart: 137 = no instrument (s137 or older); 138-141 = the dress probe ladder's rungs
STAGE_NONE, STAGE_INSTR = 137, 138


def selected_legs(env=None) -> tuple:
    """COOP_DRESS_LEGS (a ',' / '+' list, case-insensitive) -> the legs to run, in :data:`LEGS` order; default every leg. A
    name this file lacks raises ValueError (the run records it and runs nothing)."""
    raw = (os.environ if env is None else env).get("COOP_DRESS_LEGS", "")
    # [ff9mapkit netsync s140] ',' or '+' (or spaces): the bench runners' ENV lists are comma-separated, so they write S+W+X
    want = [t.strip().upper() for t in re.split(r"[,+\s]+", str(raw)) if t.strip()]
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
        "S138-R": "`reset` releases the forced selftest role -- on s139+ with `rule s139` held into it (and on s140+ "
                  "`self off` + `law timeline off`, on s141+ `polish off`): every lever read back off (the polish back "
                  "on) and the release lines logged",
    }
    if any(LEGS[leg].get("preflight") for leg in legs):
        c["S140-PF"] = ("precondition: the bench field's DEPLOYED .eb (the first FolderNames folder that ships "
                        "EVT_TEST30606, READ-ONLY) passes _selfdress_field.preflight -- MAIN_INIT_ORDER (the twin's "
                        "InitObject before the player's), the sids, T3's 2705 bound, the late entry's never-run CC and its "
                        "GUARDED load-time InitObject, J's ladder jump, every conductor and the caller's escape protocol "
                        "(every WEDGED / DONE write, every bound, the EnableMoves) -- FAILING CLOSED (else every 30606 row "
                        "reads 'not reached')")
    if calibrate:
        c["S138-CAL"] = ("CALIBRATION: exactly the predicted checks are red -- each selected leg's `old` row on an engine "
                         "before its patch (leg I on s137: I1-I9; leg G on s137 / s138: every G check; legs S / W / X / N / "
                         "T on s137-s139: every s140 check; leg F on s137-s140: every s141 check), its `lever` row under "
                         "COOP_DRESS_CAL (leg G's rule-s138: G3a, G2, G3, G3c, G3m, G3d, G7a, G7b, G7d, G7e, G8; s140's "
                         "self-off / gate-0 / law-bframe / law-attach / law-alias / law-timeline: LEVER_PREDICTED; s141's "
                         "polish-off: S141_LEVER_PREDICTED), nothing else; a lever row whose red reads 'not reached' is "
                         "UNPROVEN, never a predicted red")
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
                          + "; ".join(f"s{LEGS[g]['patch']} has no lever (an inert instrument)" if not LEGS[g]["lever"]
                                      else f"leg {g} (s{LEGS[g]['patch']}) calibrates under one of its levers: "
                                           f"COOP_DRESS_CAL={'|'.join(LEGS[g]['lever'])}" for g in legs)
                          + " -- calibrate on the engine BEFORE it (the s137 DLL 0269771f24b626c1)")
    if mode != CAL_OLD and not reds:
        # [ff9mapkit netsync s140] a lever that turns NOTHING red in the selected legs proves nothing: refuse it
        return None, (), (f"the lever {mode!r} turns nothing red in legs {', '.join(defined)} on engine stage s{stage}: "
                          f"select a leg it bites ({', '.join(g for g in LEGS if LEGS[g]['lever'].get(mode, ((),))[0])})")
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
#: [ff9mapkit netsync s140] on an s140+ engine two s140 levers are held into the reset as well -- `self off` (it acts at a
#: field LOAD: none follows the reset) and `law timeline off` (the selftest role's: the reset releases the role) -- each
#: published AS SET (`self.bench_self`, `self.law_off`), so the read-back after the reset witnesses NetSyncSelfDress.
#: ReleaseBench and its own line
HOLD_INTO_RESET_S140 = (("self", "off"), ("law", "timeline", "off"))
RELEASE_LINE_S140 = "selfdress self / gate / law levers released (released with the harness)"
#: [ff9mapkit netsync s141] ...and on an s141+ engine ReleaseBench's line names the `polish` lever too (one line for all)
RELEASE_LINE_S141 = "selfdress self / gate / law / polish levers released (released with the harness)"
#: [ff9mapkit netsync s141] ...and on an s141+ engine `polish off` is held into the reset as well (published AS SET,
#: `self.polish`, raw in every role): the read-back after the reset must show the polish back ON
HOLD_INTO_RESET_S141 = (("polish", "off"),)


def judge_released(x) -> tuple:
    """S138-R's s139 half (PURE): after `reset` every selfdress lever reads OFF -- `bench_mask`, `empty_mask`, `wire`,
    `wire_anim` -1 and `rule` null (the getters publish the levers RAW, in every role, so the read is a witness, not a
    role gate's rest value). Red on any held lever and on an engine that publishes none. [ff9mapkit netsync s140] On an
    engine that publishes `self`: its levers too -- `bench_self` null and every `law_off` false (both AS SET: the role's
    release cannot hide a leak; `gate` is the EFFECTIVE gate, so it is no witness here). [ff9mapkit netsync s141] On an
    engine that publishes `self.polish`: the polish lever back ON (`polish` true -- the lever AS SET)."""
    got = published_levers(x)
    if got is None:
        return False, "the selfdress levers after the reset: not published (no `ghost.bench_mask`)"
    s = _self(x)
    if s is None:
        return got == LEVERS_OFF, f"the selfdress levers after the reset {got} (want every one off: {LEVERS_OFF})"
    law = s.get("law_off")
    s_off = s.get("bench_self") is None and isinstance(law, dict) and not any(law.values())
    polish = ("polish" not in s) or s.get("polish") is True
    return got == LEVERS_OFF and s_off and polish, (
        f"the selfdress levers after the reset {got} (want every one off: {LEVERS_OFF}); self.bench_self "
        f"{s.get('bench_self')!r} law_off {law!r} (want null / all false)"
        + (f"; self.polish {s.get('polish')!r} (want true: released back on)" if "polish" in s else ""))


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
    if stage < 140:
        return True, None
    # [ff9mapkit netsync s140] the s140 levers, held into the same reset
    for op in HOLD_INTO_RESET_S140:
        ok, why = cb.try_ns(g, "selfdress", *op)
        if not ok:
            return False, f"`selfdress {' '.join(op)}` refused: {why}"
    st = cb.poll(g, lambda s: (_self(s) or {}).get("bench_self") == "off"
                 and ((_self(s) or {}).get("law_off") or {}).get("timeline") is True, 5.0, "the s140 levers published")
    if st is None:
        return False, f"the s140 levers never published (self {cb.pick(_self(g.state), 'bench_self', 'law_off')})"
    if stage < 141:
        return True, None
    # [ff9mapkit netsync s141] the polish lever, held into the same reset (ReleaseBench puts it back on)
    for op in HOLD_INTO_RESET_S141:
        ok, why = cb.try_ns(g, "selfdress", *op)
        if not ok:
            return False, f"`selfdress {' '.join(op)}` refused: {why}"
    st = cb.poll(g, lambda s: (_self(s) or {}).get("polish") is False, 5.0, "the s141 lever published")
    if st is None:
        return False, f"the s141 lever never published (self {cb.pick(_self(g.state), 'polish')})"
    return True, None


def want_mode(levers: dict, ghost_as) -> str:
    """(PURE) The `ghost.mode` the levers imply: "bench:auto" under a `ghost` lever (it FORCES mode auto -- audit 2.2
    amendment 1), else "ini:" + the ini's trimmed GhostAs."""
    return BW.DRESS_MODE_BENCH if int(levers["mask"]) >= 0 else BW.DRESS_MODE_INI + (ghost_as or "").strip()


def want_ghost(x, levers: dict, ghost_as, rules=None) -> dict | None:
    """(PURE) What THE s139 SELFTEST SITE makes the mirror wear and play on this sample -- battlewire.selftest_dress, the
    site's twin (its rig rows pinned to the census), on the sample's own player model / anim and its LIVE party
    (`netsync.dress.party`), the ini's GhostAs and the GuestSlots-0 pin, the bench's ``levers`` (the `rule` lever is never
    applied: the expectation is always the s139 rule, so the calibration lever's red shows). None when the player's model
    or anim, or the party, is unread. [ff9mapkit netsync s140] ``rules``: the PROBED engine's (:func:`stage_rules`: an s139
    engine leaves Cinna..Beatrix undressed, s140 dresses them as rigs 9-12); None = the live table."""
    p, d = _player(x), _dress(x)
    model, anim = _int(p.get("model")), _int(p.get("anim"))
    party = d.get("party") if isinstance(d, dict) else None
    if model is None or anim is None or not isinstance(party, list) or len(party) != 4:
        return None
    # [ff9mapkit netsync s143] the site's leader guard (FieldGuardMask, `auto` only) with the leader the engine takes on THIS
    # sample (cb.guard_leader: -1 before s143 / under the lever) -- an s139 / s140 stage's frozen rules know no guard
    lead = cb.guard_leader(x) if rules is None or rules is BW else -1
    kw = {"leader": lead} if lead >= 0 else {}
    return (rules or BW).selftest_dress(ghost_as=ghost_as or "", guest_slots=0, me_model=model, me_anim=anim, party=party,
                             role="selftest", selftest_role=True, bench_mask=int(levers["mask"]),
                             empty_mask=int(levers["empty"]), rule=None, wire=int(levers["wire"]),
                             wire_anim=int(levers.get("wire_anim", -1)), **kw)


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


def _worn_verdict(pick, *, levers: dict, ghost_as, models: dict, clips: dict, moving: bool = False, rules=None) -> tuple:
    """One sample against :func:`want_ghost`: (ok, detail) -- model, rig, GEO and texture stem off the INSTALL, the clip
    NAME of the twin's anim (playing, where that clip lives in the worn folder), and `ghost.mode` the one the levers imply.
    A ghost body null with everything else right reads "not reached: cannot judge"."""
    want = want_ghost(pick, levers, ghost_as, rules)
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


def judge_worn(samples: list, *, levers: dict, ghost_as, models: dict, clips: dict, hold: int = GHOST_HOLD,
               rules=None) -> tuple:
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
    return _worn_verdict(pick, levers=levers, ghost_as=ghost_as, models=models, clips=clips, rules=rules)


def judge_worn_moving(samples: list, *, levers: dict, ghost_as, models: dict, clips: dict, rules=None) -> tuple:
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
        ok, why = _worn_verdict(b, levers=levers, ghost_as=ghost_as, models=models, clips=clips, rules=rules)
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


def judge_baseline(samples: list, *, ghost_as, models: dict, clips: dict, rules=None) -> tuple:
    """G0 / G5 (PURE): every lever OFF, `ghost.mode` == "ini:" + the ini's GhostAs as the bench read it offline (trimmed),
    and the ghost what the s139 rule makes of it under the pin (:func:`judge_worn`)."""
    ok, why = judge_worn(samples, levers=LEVERS_OFF, ghost_as=ghost_as, models=models, clips=clips, rules=rules)
    d = _dress(samples[-1]) if samples else None
    gh = d.get("ghost") if isinstance(d, dict) else None
    mode = gh.get("mode", "ABSENT") if isinstance(gh, dict) else "ABSENT"
    want_mode_ = BW.DRESS_MODE_INI + (ghost_as or "").strip()
    return ok and mode == want_mode_, f"mode {mode!r} (want {want_mode_!r}); {why}"


def judge_section_line(lines: list, ghost_as, rules=None) -> tuple:
    """G3d's second half (PURE over Memoria.log): the proof block's LATEST section-8 line carries the twin's body for the
    ini's GhostAs under the forced selftest's GuestSlots pin 0 (battlewire.host_dress_section) -- "DC 00 FF (model 220,
    charId 255)" for auto (owner D2), "00 00 FF (model 0, charId 255)" for none. The producer's bytes as this machine would
    host them (the selftest role has no socket: G9, the duo relay tap, is the wire's own witness)."""
    want = BW.dress_section_text((rules or BW).host_dress_section(ghost_as or "", 0, "selftest", True, None))
    hits = [ln for ln in lines if BW.PROOF_DRESS_SECTION in ln]
    if not hits:
        return False, f"no '{BW.PROOF_DRESS_SECTION.strip()}' line in Memoria.log (want {want!r})"
    got = hits[-1].split(BW.PROOF_DRESS_SECTION, 1)[1].strip()
    return got == want, f"section 8 {got!r} (the twin's {want!r} for GhostAs {ghost_as!r} under the pin)"


def judge_codec(d: dict | None, lines: list, rules=None) -> tuple:
    """G4 (PURE): `netsync.dress.codec` == "ok" AND the proof block's line reads OK with the engine's row count -- the
    PROBED stage's ([ff9mapkit netsync s140] ``rules``: s139's 29 rows, s140's 38 -- the owner's 8-11 rows grew it)."""
    if d is None or "codec" not in d:
        return False, "netsync.dress.codec ABSENT -- an engine before s139"
    want = BW.proof_ok(BW.PROOF_DRESS, (rules or BW).DRESS_SELFTEST_ROWS)
    hits = [ln for ln in lines if BW.PROOF_DRESS in ln]
    line = hits[-1].split("[NetSync] ", 1)[-1].strip() if hits else None
    ok = d.get("codec") == BW.DRESS_CODEC_OK and line == want
    return ok, f"codec {d.get('codec')!r}; proof line {line!r} (want {want!r})"


def judge_idle_frames(d: dict | None, oracle, rules=None) -> tuple:
    """G6 (PURE): `rig_idle_frames` -- one int per rig row of the PROBED engine ([ff9mapkit netsync s140] ``rules``: s139's
    nine, s140's thirteen: Cinna..Beatrix appended) -- equals the oracle the kit's clip reader read off the install, row
    for row (its first rows: the oracle reads every row of the live table; None: "not reached")."""
    if d is None or "rig_idle_frames" not in d:
        return False, "netsync.dress.rig_idle_frames ABSENT -- an engine before s139"
    got = d.get("rig_idle_frames")
    if oracle is None:
        return False, f"not reached: no idle-frame oracle (published {got})"
    rows = (rules or BW).RIG_ROW_COUNT
    names = (rules or BW).RIG_NAMES
    if not isinstance(got, list) or len(got) != rows or any(_int(v) is None for v in got):
        return False, f"rig_idle_frames {got!r}: not {rows} ints"
    if len(oracle) < rows:
        return False, f"not reached: the oracle reads {len(oracle)} rows, the engine publishes {rows}"
    want = list(oracle)[:rows]
    bad = [f"{names[i]} {got[i]} != {want[i]}" for i in range(rows) if got[i] != want[i]]
    return not bad, f"rig_idle_frames {got} (oracle {want})" + (f"; {bad}" if bad else "")


def first_main_slot(party) -> int | None:
    """(PURE) s1: the first slot >= 1 holding a main (CharacterId 0-7) -- what `ghost 1<<s1` names; None when none does."""
    if not isinstance(party, list):
        return None
    return next((i for i in range(1, min(4, len(party))) if _int(party[i]) is not None and 0 <= party[i] < BW.MAIN_RIG_COUNT),
                None)


# ---- [ff9mapkit netsync s140] the s140 legs' pure judges ---------------------------------------------------------------
def stage_rules(stage):
    """[ff9mapkit netsync s140] The dress rules the PROBED engine runs (battlewire.dress_rules): an s139 engine's FROZEN rules
    below s140 (nine rig rows, Cinna..Beatrix undressed, the 29-row codec proof, nine idle frames), the live table from s140
    on (and on a torn probe) -- leg G and I7 judge by the engine the run found, never the one the twin was last edited for."""
    return BW.dress_rules("dresshost") if stage is not None and stage < 140 else BW


def _self(x) -> dict | None:
    """``netsync.dress.self`` (None when absent: an engine before s140)."""
    d = _dress(x)
    s = d.get("self") if isinstance(d, dict) else None
    return s if isinstance(s, dict) else None


def self_count(x, key: str) -> int | None:
    """(PURE) One `netsync.dress.self` key as an int (None when absent or not an int)."""
    s = _self(x)
    return _int(s.get(key)) if s is not None else None


def count_delta(a, b, key: str) -> int | None:
    """(PURE) A `self` counter's growth from ``a`` to ``b`` -- the counters are PER PROCESS, so a row judges its own delta,
    never the raw value; None when either is unread."""
    x, y = self_count(a, key), self_count(b, key)
    return None if x is None or y is None else y - x


def dress_lines(lines, field=None) -> list:
    """(PURE over Memoria.log) AtSetModel's dress lines -- {field, uid, sid, geo, model, rig, eye, from} each -- only
    ``field``'s when given."""
    out = []
    for ln in lines or ():
        m = DRESS_LINE.search(str(ln))
        if not m:
            continue
        row = {"field": int(m.group(1)), "uid": int(m.group(2)), "sid": int(m.group(3)), "geo": m.group(4),
               "model": int(m.group(5)), "rig": int(m.group(6)), "eye": int(m.group(7)), "from": m.group(8)}
        if field is None or row["field"] == int(field):
            out.append(row)
    return out


def body_mismatch(p: dict, ro: dict) -> list:
    """(PURE) The controlled body ``p`` (`player.*`) against one rig's oracle ``ro`` -- [] when it wears that rig: `model`,
    `body` (the texture stem: a dress cannot compute it), `geo`, `eye` (-4 x the oracle's SetModel byte)."""
    eye = BW.eye_of(ro["eye"]) if _int(ro.get("eye")) is not None else None
    bad = []
    for key, want in (("model", ro.get("model")), ("body", ro.get("body")), ("geo", ro.get("geo")), ("eye", eye)):
        if want is None or p.get(key) != want:
            bad.append(f"{key} {p.get(key)!r} (want {want!r})")
    return bad


def _ro_text(ro: dict) -> str:
    return (f"the oracle's {ro.get('name')}: model {ro.get('model')} {ro.get('geo')} body {ro.get('body')!r} eye byte "
            f"{ro.get('eye')}")


def arm_of(x) -> tuple:
    """(PURE) The arm as published -- (armed, want_model, want_rig, why) -- and the controlled body's model."""
    s = _self(x) or {}
    return (s.get("armed"), s.get("want_model"), s.get("want_rig"), s.get("why"), _player(x).get("model"))


def attach_mismatch(a, b, *, site: str, src_list) -> tuple:
    """(PURE) AttachDress AT THIS LOAD (amendment 2), judged across the publishes ``a`` (before the load / the return) and
    ``b`` (after it) -- never a last-write value alone: the site's own call counter moved by exactly one (``site`` "cold":
    attach_cold +1 and attach_warm +0 -- SetModel, site a; "warm": attach_warm +1 and attach_cold +0 -- the rebuild, site
    b), and only then what that call attached: src_attached > 0 and src_list_clips == ``src_list`` (the field's
    GEO_MAIN_F0_ZDN EventAnimation line, read offline; None = no oracle: > 0 then). -> (problems, the facts read)."""
    mine, other = ("attach_cold", "attach_warm") if site == "cold" else ("attach_warm", "attach_cold")
    dm, do = count_delta(a, b, mine), count_delta(a, b, other)
    s = _self(b) or {}
    sa, sl = _int(s.get("src_attached")), _int(s.get("src_list_clips"))
    bad = []
    if dm != 1 or do != 0:
        bad.append(f"{mine} +{dm} / {other} +{do} (want +1 / +0: AttachDress at {'SetModel -- site a' if site == 'cold' else 'the warm rebuild -- site b'}, THIS load)")
    if sa is None or sa <= 0:
        bad.append(f"src_attached {sa!r} (want > 0: the source list + the rig's set on the body)")
    if src_list is None:
        if sl is None or sl <= 0:
            bad.append(f"src_list_clips {sl!r} (want > 0: the SOURCE list; no offline count for this field)")
    elif sl != int(src_list):
        bad.append(f"src_list_clips {sl!r} (want {src_list}: the field's GEO_MAIN_F0_ZDN EventAnimation line)")
    return bad, f"{mine} +{dm}, {other} +{do}, src_attached {sa}, src_list_clips {sl} (oracle {src_list})"


def judge_self_dress(st, ro: dict, *, rig: int, before=None, lines=None, field=None, attach=None, op=None,
                     spec=None) -> tuple:
    """S1 / S3 / S6 / S7 / W2 (PURE): one dressed field load judged on its settled publish ``st`` against the rig's oracle
    ``ro``: the body (:func:`body_mismatch`); at rest `anim_geo` == the oracle's GEO (a clip of its OWN folder plays); `self`
    why 'dressed', rig and want_rig == ``rig``, want_char == RigToChar(rig) (255 for the moogle: no CharacterId), from
    'bench', uid == player.uid, net_byte == rig + 1, src 98. With ``before`` (the publish before the warp): confirmed +1 or
    more; with ``lines`` (Memoria.log since the warp): exactly ONE dress line for ``field`` naming the oracle's GEO, model,
    rig and eye; with ``attach`` ({"src_list": the field's SOURCE-list size or None}, and ``before``): AttachDress at THIS
    load's SetModel (:func:`attach_mismatch`, site a); with ``op`` -- (the publish before the `self` op, the op's own
    publish) -- ARMING AT THE FIELD LOAD ONLY: the op's publish shows `bench_self` == ``spec`` while the arm (armed,
    want_model, want_rig, why) and the body are still what they were before it (ArmBench runs at the load)."""
    p, s = _player(st), _self(st)
    if s is None:
        return False, "netsync.dress.self ABSENT -- an engine before s140"
    bad = body_mismatch(p, ro)
    if p.get("anim_geo") != ro.get("geo"):
        bad.append(f"anim_geo {p.get('anim_geo')!r} at rest (want {ro.get('geo')!r})")
    for key, want in (("why", "dressed"), ("rig", rig), ("want_rig", rig), ("want_char", BW.rig_to_char(rig)),
                      ("from", "bench"), ("net_byte", rig + 1), ("src", BW.PLAIN_ZIDANE_MODEL)):
        if s.get(key) != want:
            bad.append(f"self.{key} {s.get(key)!r} (want {want!r})")
    if _int(s.get("uid")) is None or s.get("uid") != p.get("uid"):
        bad.append(f"self.uid {s.get('uid')!r} != player.uid {p.get('uid')!r}")
    extra = []
    if before is not None:
        dc = count_delta(before, st, "confirmed")
        extra.append(f"confirmed +{dc}")
        if dc is None or dc < 1:
            bad.append(f"confirmed +{dc} (want +1: DefinePlayerCharacter bound control to the dressed body)")
    if lines is not None:
        rows = dress_lines(lines, field)
        want_line = (ro.get("geo"), ro.get("model"), rig,
                     BW.eye_of(ro["eye"]) if _int(ro.get("eye")) is not None else None, "bench")
        extra.append(f"dress lines {[(r['geo'], r['model'], r['rig'], r['eye'], r['from']) for r in rows]}")
        if len(rows) != 1 or (rows[0]["geo"], rows[0]["model"], rows[0]["rig"], rows[0]["eye"], rows[0]["from"]) != want_line:
            bad.append(f"{len(rows)} dress line(s) for field {field} (want ONE: {want_line})")
    if op is not None:
        pre, post = op
        if post is None:
            bad.append(f"the `self {spec}` op never published bench_self {spec!r}")
        else:
            extra.append(f"at the op: arm {arm_of(pre)} -> {arm_of(post)}")
            if arm_of(post) != arm_of(pre) or (_self(post) or {}).get("bench_self") != spec:
                bad.append(f"the `self {spec}` op MOVED the arm before the load: {arm_of(pre)} -> {arm_of(post)} (want it "
                           f"unchanged until the field load, bench_self {spec!r})")
    if attach is not None:
        abad, afacts = attach_mismatch(before, st, site="cold", src_list=attach.get("src_list"))
        extra.append(afacts)
        bad += abad
    # what is WRONG leads (the ledger keeps a detail's first 900 characters)
    detail = ((f"WRONG: {'; '.join(bad)} -- " if bad else "")
              + f"{_show(p, 'model')} {_show(p, 'body')} {_show(p, 'geo')} {_show(p, 'eye')} {_show(p, 'anim_geo')} "
              f"{_show(p, 'uid')}; self {cb.pick(s, 'why', 'rig', 'want_rig', 'want_char', 'from', 'uid', 'net_byte', 'src')} "
              f"vs {_ro_text(ro)}, rig {rig}" + (f"; {'; '.join(extra)}" if extra else ""))
    return not bad, detail


def live_body(x) -> tuple:
    """(PURE) The LIVE body as one publish shows it: (model, body stem, GEO, eye, self.rig, self.net_byte)."""
    p, s = _player(x), _self(x) or {}
    return (p.get("model"), p.get("body"), p.get("geo"), p.get("eye"), s.get("rig"), s.get("net_byte"))


def judge_self_off(st, ro: dict, *, prev=None, clear=None) -> tuple:
    """S4 (PURE): THE TEARDOWN LAW then the next SetModel. ``clear`` -- (the publish read BEFORE the `clear`, the publish
    after `clear` + `self off`, held OP_SETTLE_S) -- the knob and Clear() never undress a LIVE body: the body
    (:func:`live_body`) is unchanged across the ops (and, when ``prev`` -- the load before -- was dressed, still wears ITS
    rig: S6's Blank); after the re-warp the body is ZIDANE again (``ro`` the oracle's Zidane: model, body, GEO, eye) --
    `self` why 'model 0', rig -1, net_byte 0, bench_self 'off'."""
    p, s = _player(st), _self(st)
    if s is None:
        return False, "netsync.dress.self ABSENT -- an engine before s140"
    bad = body_mismatch(p, ro)
    for key, want in (("why", "model 0"), ("rig", -1), ("net_byte", 0), ("bench_self", "off")):
        if s.get(key) != want:
            bad.append(f"self.{key} {s.get(key)!r} (want {want!r})")
    was = _player(prev).get("model") if prev is not None else None
    tear = ""
    if clear is not None:
        pre, post = clear
        prig = _int((_self(prev) or {}).get("rig")) if prev is not None else None
        a, z = live_body(pre), (live_body(post) if post is not None else None)
        tear = f"; across `clear` + `self off`: {a} -> {z}"
        if z is None:
            bad.append("the ops' own publish was never read (no `self off` published)")
        elif a != z:
            bad.append(f"`clear` + `self off` CHANGED the live body {a} -> {z} (the teardown law: it changes only at the "
                       f"next SetModel)")
        if prig is not None and prig >= 0 and _int(a[4]) != prig:
            bad.append(f"before the ops the body wore rig {a[4]!r}, not the load before's {prig} (the law's input)")
    return not bad, (f"{_show(p, 'model')} {_show(p, 'body')} {_show(p, 'geo')} {_show(p, 'eye')}; self "
                     f"{cb.pick(s, 'why', 'rig', 'net_byte', 'bench_self')} vs {_ro_text(ro)} (the load before wore "
                     f"{was!r}){tear}" + (f"; WRONG: {'; '.join(bad)}" if bad else ""))


def judge_rest_named(samples: list, ro: dict) -> tuple:
    """S2's / S6's REST (PURE): the LAST publish of the window, the player still over the last REST_STILL publishes, plays
    a clip NAMED the rig's idle (by NAME: the idle id and its alias are one clip) -- or the rig's break clip where it has
    one -- playing, in the rig's own GEO."""
    if len(samples) < REST_STILL:
        return False, f"only {len(samples)} rest publishes"
    tail = samples[-REST_STILL:]
    still = not any(_moved(a, b) for a, b in zip(tail, tail[1:]))
    p = _player(tail[-1])
    names = {n for n in (ro.get("idle_clip"), ro.get("inactive_clip")) if n}
    ok = (still and p.get("clip") in names and p.get("anim_geo") == ro.get("geo") and p.get("clip_playing") is True)
    return ok, (f"{_show(p, 'anim')} {_show(p, 'clip')} {_show(p, 'anim_geo')} {_show(p, 'clip_playing')} still={still} "
                f"(want a clip named {sorted(names)} in {ro.get('geo')!r})")


def judge_geo_throughout(samples: list, geo) -> tuple:
    """(PURE) `anim_geo` read LIVE on every publish that has one: each == ``geo`` (never a ZDN folder) -- red when none has
    one (nothing was judged)."""
    seen = [s for s in samples if _player(s).get("anim_geo") is not None]
    bad = [s for s in seen if _player(s).get("anim_geo") != geo]
    if not seen:
        return False, f"no publish carried an `anim_geo` ({len(samples)} publishes)"
    first = _player(bad[0]) if bad else {}
    return not bad, (f"{len(seen)} publishes with an anim_geo, {len(bad)} not {geo!r}"
                     + (f" (first: {_show(first, 'anim')} {_show(first, 'clip')} {_show(first, 'anim_geo')})" if bad
                        else ""))


def judge_ghost_wears(samples: list, ro: dict, *, ghost_as, models: dict, clips: dict, rules=None) -> tuple:
    """S5 (PURE): on the dressed rest window, the selftest mirror's ghost wears the dressed body -- `ghost.model` == the
    oracle's model (192 for Freya) AND :func:`judge_worn` (the stage's twin, every leg-G lever off: GhostGuard shows a wire
    body that is neither 98 nor the dress as it is, playing its raw clip)."""
    ok, why = judge_worn(samples, levers=LEVERS_OFF, ghost_as=ghost_as, models=models, clips=clips, rules=rules)
    d = _dress(samples[-1]) if samples else None
    gh = d.get("ghost") if isinstance(d, dict) else None
    model = gh.get("model") if isinstance(gh, dict) else None
    return ok and model == ro.get("model"), f"ghost.model {model!r} (want {ro.get('model')}); {why}"


def object_model(x, sid: int) -> int | None:
    """(PURE) `objects[]`'s model of the entry built at ``sid`` -- by its BUILT sid, never by model (N2 dresses the twin)."""
    objs = _raw(x).get("objects")
    if not isinstance(objs, list):
        return None
    for o in objs:
        if isinstance(o, dict) and _int(o.get("sid")) == int(sid):
            return _int(o.get("model"))
    return None


def judge_x1(run: dict, ro: dict) -> tuple:
    """X1 (PURE): the X conductor (``run``: :func:`_conduct`'s) ended DONE; MapAndAttach mapped its gesture (remaps +1 or
    more, trigger to DONE); the gesture SHOWED (some publish's anim or frame_n moved off the pre-trigger idle's); and every
    publish from the trigger to DONE that plays a clip plays one NAMED the rig's idle (the alias by NAME, never by id) in
    the rig's GEO -- never a ZDN folder."""
    if run["outcome"] != "done":
        return False, f"the X conductor ended {run['outcome']!r} ({run.get('why') or 'no DONE_X'})"
    win, base = run["samples"], _player(run["before"])
    rm = count_delta(run["before"], run["end"], "remaps")
    moved = any((_player(s).get("anim"), _player(s).get("frame_n")) != (base.get("anim"), base.get("frame_n"))
                for s in win)
    playing = [s for s in win if _player(s).get("clip") is not None]
    bad = [s for s in playing if _player(s).get("clip") != ro.get("idle_clip")
           or _player(s).get("anim_geo") != ro.get("geo")]
    seen = sorted({(_player(s).get("anim"), _player(s).get("clip"), _player(s).get("anim_geo")) for s in playing},
                  key=str)
    ok = rm is not None and rm >= 1 and moved and bool(playing) and not bad
    return ok, (f"remaps +{rm}; the gesture showed: {moved}; (anim, clip, anim_geo) played {seen[:6]} (want every clip "
                f"named {ro.get('idle_clip')!r} in {ro.get('geo')!r})" + (f"; {len(bad)} publishes off it" if bad else ""))


def judge_x2(run: dict, after: list, ro: dict, *, idle_frames, hold_s: float) -> tuple:
    """X2 (PURE): after DONE_X the stored idle (the oracle's idle id) plays with `frame_n` == ``idle_frames`` (its frame
    count off p0data5: DefaultAnim's SetAnim saw ANOTHER id -- the ALIAS proof, amendment 4; the idle id itself returns
    early and keeps the gesture's stretched count) -- on the first publish after DONE playing it with control; and control
    was back within ``hold_s`` + X_GRACE_S of the trigger (the DONE publish: EnableMove precedes DONE)."""
    if run["outcome"] != "done":
        return False, f"the X conductor ended {run['outcome']!r} ({run.get('why') or 'no DONE_X'})"
    if idle_frames is None:
        return False, "not reached: no idle frame count off p0data5 for the rig"
    end = run["end"]
    back_s = cb.elapsed(run["trig"], end)
    on_time = bool(_player(end).get("control")) and back_s <= hold_s + X_GRACE_S
    pick = next((s for s in [end] + list(after) if _player(s).get("anim") == ro.get("idle")
                 and bool(_player(s).get("control"))), None)
    if pick is None:
        p = _player(after[-1] if after else end)
        return False, (f"no publish after DONE_X plays the stored idle {ro.get('idle')} ({_show(p, 'anim')} "
                       f"{_show(p, 'frame_n')}); control back {back_s:.2f} s")
    p = _player(pick)
    return on_time and _int(p.get("frame_n")) == int(idle_frames), (
        f"after DONE_X {_show(p, 'anim')} {_show(p, 'clip')} {_show(p, 'frame_n')} (want frame_n {idle_frames}: the idle's "
        f"own); control back {back_s:.2f} s after the trigger (want <= {hold_s:.2f} + {X_GRACE_S} s)")


def _line_sids(lines, field) -> list:
    return sorted(r["sid"] for r in dress_lines(lines, field))


def judge_x3(run: dict, ro: dict, *, src_frames, jump0: int, jump1: int) -> tuple:
    """X3 (PURE): THE JUMP SLOT ON THE SOURCE TIMELINE. The J conductor (``run``: :func:`_conduct`'s) ended DONE on a body
    wearing the rig (its pre-trigger publish: the oracle's model); every publish from the trigger to J_END that plays the
    JUMP SLOT -- the rig's idle ALIAS: its idle clip by NAME under an id that is not the idle's -- runs on frame_n ==
    ``src_frames`` (the source clip's count off p0data5; the alias's own count is the s140-without-the-fix red); and the
    landing -- the first J_LAND publish to the first J_END publish -- lasts no longer than stock's own landing ticks
    (battlewire.jump_ticks on the source count) / TICK_HZ + J_SLOP_S. A run with no alias publish is judged on the landing
    alone (the alias law off maps the slot to the idle id itself)."""
    if run["outcome"] != "done":
        return False, f"the J conductor ended {run['outcome']!r} ({run.get('why') or 'no DONE_J'})"
    if src_frames is None:
        return False, "not reached: no source frame count off p0data5 for the jump clip"
    base = _player(run["before"])
    samples = list(run["samples"])
    end_k = next((k for k, s in enumerate(samples) if s.flag(sdf.J_END) is True), None) if samples and \
        hasattr(samples[0], "flag") else None
    land_k = next((k for k, s in enumerate(samples) if s.flag(sdf.J_LAND) is True), None) if samples and \
        hasattr(samples[0], "flag") else None
    if end_k is None or land_k is None:
        return False, f"the J phase bits never published (J_LAND at {land_k}, J_END at {end_k} of {len(samples)} publishes)"
    jumps = [s for s in samples[:end_k + 1] if _player(s).get("clip") == ro.get("idle_clip")
             and _int(_player(s).get("anim")) not in (None, _int(ro.get("idle")))]
    off = [s for s in jumps if _int(_player(s).get("frame_n")) != int(src_frames)]
    stock_land = BW.jump_ticks(int(src_frames), jump0, jump1)[1]
    bound = stock_land / TICK_HZ + J_SLOP_S
    dur = cb.elapsed(samples[land_k], samples[end_k])
    dressed = base.get("model") == ro.get("model")
    ok = dressed and not off and dur <= bound
    seen = sorted({(_player(s).get("anim"), _player(s).get("frame_n")) for s in jumps}, key=str)
    return ok, (f"body {base.get('model')!r} (want {ro.get('model')}); {len(jumps)} jump-slot publishes (anim, frame_n) "
                f"{seen[:6]} (want frame_n {src_frames}: the SOURCE clip's)" + (f", {len(off)} off it" if off else "")
                + f"; the landing {dur:.2f} s (want <= {bound:.2f}: stock's {stock_land} ticks + {J_SLOP_S} s)")


def judge_seated(st, before_party, want_party, *, char: int) -> tuple:
    """S7's seat (PURE): after the COOPSUB seed the LIVE party (`netsync.dress.party`, FF9.party.member[i].Index) is the
    oracle's (:func:`seat_party` over the party read before the seed) and the seated member's slot reads ``char`` -- the
    CharacterId (Blank 10), never his CharacterOldIndex (11)."""
    party = (_dress(st) or {}).get("party")
    slot = slot_of(party, char)
    ok = isinstance(party, list) and list(party) == list(want_party or []) and slot is not None
    return ok, (f"dress.party {party!r} (want {want_party!r}: the seed over {before_party!r}); CharacterId {char} in slot "
                f"{slot}")


def judge_n1(st, before, ro: dict, zid: dict, *, lines=None) -> tuple:
    """N1 (PURE): the twin (TWIN_SID) stays the oracle's Zidane model, skip_npc +1 or more since the warp (the player gate
    turned it away), and the player's BODY is the dress (:func:`body_mismatch`: model, texture stem, GEO, eye -- a witness
    the hook does not write) -- the gate published on; with ``lines`` (Memoria.log since the warp): exactly ONE dress line
    for the bench field, the player's sid (the twin logged none)."""
    s = _self(st)
    if s is None:
        return False, "netsync.dress.self ABSENT -- an engine before s140"
    twin, p = object_model(st, sdf.TWIN_SID), _player(st)
    dn = count_delta(before, st, "skip_npc")
    body = body_mismatch(p, ro)
    sids = _line_sids(lines, SELF_FIELD) if lines is not None else None
    ok = (twin == zid.get("model") and dn is not None and dn >= 1 and not body and s.get("gate") is True
          and (sids is None or sids == [sdf.PLAYER_SID]))
    return ok, (f"objects[sid {sdf.TWIN_SID}].model {twin!r} (want {zid.get('model')}), skip_npc +{dn} (want >= 1), the "
                f"player {_show(p, 'model')} {_show(p, 'body')}" + (f" WRONG {body}" if body else " (the oracle's)")
                + f", self.gate {s.get('gate')!r}, dress-line sids {sids} (want [{sdf.PLAYER_SID}])")


def judge_n2(st, before, ro: dict, *, lines=None) -> tuple:
    """N2 (PURE): under `gate 0` skip_npc +0 since the warp, and the twin AND the player both wear the dress (control is
    null at both SetModels) -- the player's BODY the oracle's, the gate published off; with ``lines``: exactly TWO dress
    lines for the bench field, the twin's sid and the player's."""
    s = _self(st)
    if s is None:
        return False, "netsync.dress.self ABSENT -- an engine before s140"
    twin, p = object_model(st, sdf.TWIN_SID), _player(st)
    dn = count_delta(before, st, "skip_npc")
    body = body_mismatch(p, ro)
    sids = _line_sids(lines, SELF_FIELD) if lines is not None else None
    want_sids = sorted((sdf.PLAYER_SID, sdf.TWIN_SID))
    ok = (dn == 0 and twin == ro.get("model") and not body and s.get("gate") is False
          and (sids is None or sids == want_sids))
    return ok, (f"skip_npc +{dn} (want +0), objects[sid {sdf.TWIN_SID}].model {twin!r} (want {ro.get('model')}) and the "
                f"player {_show(p, 'model')} {_show(p, 'body')}" + (f" WRONG {body}" if body else " (the oracle's)")
                + f", self.gate {s.get('gate')!r} (want false), dress-line sids {sids} (want {want_sids})")


def judge_n3(run: dict, after: list, ro: dict, zid: dict, *, uid) -> tuple:
    """N3 (PURE): the N3 conductor ended DONE; skip_second +1 or more (trigger to the last publish read); the late entry
    (LATE_SID) stays the oracle's Zidane model and logged NO dress line since the trigger (``run["lines"]``); control
    unchanged -- the player's uid ``uid``, control on, the body still the oracle's dress (:func:`body_mismatch`)."""
    if run["outcome"] != "done":
        return False, f"the N3 conductor ended {run['outcome']!r} ({run.get('why') or 'no DONE_N3'})"
    last = after[-1] if after else run["end"]
    late, p = object_model(last, sdf.LATE_SID), _player(last)
    ds = count_delta(run["before"], last, "skip_second")
    body = body_mismatch(p, ro)
    sids = _line_sids(run.get("lines") or [], SELF_FIELD)
    ok = (ds is not None and ds >= 1 and late == zid.get("model") and p.get("uid") == uid and bool(p.get("control"))
          and not body and sdf.LATE_SID not in sids)
    return ok, (f"skip_second +{ds} (want >= 1), objects[sid {sdf.LATE_SID}].model {late!r} (want {zid.get('model')}), "
                f"dress-line sids since the trigger {sids} (want none for {sdf.LATE_SID}), the player {_show(p, 'uid')} "
                f"(want {uid}) {_show(p, 'control')} {_show(p, 'model')}" + (f" WRONG {body}" if body else " (the oracle's)"))


def _worn_text(run: dict) -> str:
    return f"{run.get('name')}: {run.get('outcome')!r} wearing {run.get('model')!r} (want {run.get('want')!r})"


def judge_t1(rig_run: dict | None, control_run: dict | None) -> tuple:
    """T1 (PURE): the discriminator (Garnet: a 30-frame idle) wears its rig and its T1 run ends DONE with timeline_kept +1
    or more; the CONTROL (the moogle: a 72-frame idle) wears its rig and ends DONE too -- a control that does not end is the
    BENCH failing, never the law (that reads "not reached")."""
    if rig_run is None or control_run is None:
        return False, "not reached: a T1 run did not happen"
    if control_run["outcome"] != "done" and control_run.get("model") == control_run.get("want"):
        return False, (f"not reached: the CONTROL did not finish -- the conductor, not the law ({_worn_text(control_run)}); "
                       f"the rig {_worn_text(rig_run)}")
    tk = rig_run.get("timeline")
    ok = (rig_run["outcome"] == "done" and rig_run.get("model") == rig_run.get("want") and tk is not None and tk >= 1
          and control_run["outcome"] == "done" and control_run.get("model") == control_run.get("want"))
    return ok, (f"{_worn_text(rig_run)}, timeline_kept +{tk} (want >= 1); the control {_worn_text(control_run)}, "
                f"timeline_kept +{control_run.get('timeline')}")


def judge_t3(runs: list) -> tuple:
    """T3 (PURE): every rig's run (``runs``: one per T3_RIGS name) wears its oracle model and ends DONE with T3_END set
    (never WEDGED_T3), bframe_remaps +1 or more on a dressed rig and +0 on Zidane (stock: `self zidane` disarms). A run
    whose load was not reached makes the row "not reached" (naming it); every other miss is a judged red."""
    if not runs:
        return False, "not reached: no T3 run"
    miss = [r for r in runs if r.get("unreached")]
    if miss:
        return False, f"not reached: rig {miss[0]['name']}: {miss[0]['unreached']} ({len(miss)} of {len(runs)} runs)"
    bad, parts = [], []
    for r in runs:
        zid = r["name"] == BW.RIG_NAMES[0]
        rm = r.get("remaps")
        ok = (r.get("model") == r.get("want") and r["outcome"] == "done" and r.get("end_bit") is True
              and rm is not None and (rm == 0 if zid else rm >= 1))
        parts.append(f"{r['name']} {r['outcome']} +{rm}")
        if not ok:
            bad.append(f"{_worn_text(r)}, T3_LOOP {r.get('loop_bit')!r} T3_END {r.get('end_bit')!r}, bframe_remaps +{rm} "
                       f"(want {'+0: stock' if zid else '>= +1'})")
    return not bad, (f"{len(runs)} rigs: {', '.join(parts)}" + (f"; WRONG: {'; '.join(bad[:4])}" if bad else ""))


def judge_self_selftest(s: dict | None, lines: list) -> tuple:
    """T2 (PURE): `self.selftest` == 'ok' AND the proof block's LATEST self-dress line reads OK with the engine's row
    count (battlewire.SELF_DRESS_SELFTEST_ROWS)."""
    if s is None or "selftest" not in s:
        return False, "netsync.dress.self(.selftest) ABSENT -- an engine before s140"
    want = BW.proof_ok(BW.PROOF_SELF_DRESS, BW.SELF_DRESS_SELFTEST_ROWS)
    hits = [ln for ln in lines if BW.PROOF_SELF_DRESS in ln]
    line = hits[-1].split("[NetSync] ", 1)[-1].strip() if hits else None
    return s.get("selftest") == BW.SELF_DRESS_SELFTEST_OK and line == want, (
        f"self.selftest {s.get('selftest')!r}; proof line {line!r} (want {want!r})")


def judge_break_clip(idle: list, ro: dict) -> tuple:
    """W1's idle window (PURE): the rig's BREAK clip -- the one clip only AttachDress at the warm rebuild (site b) puts
    back on the rebuilt go (no 30602 entry lists it; ReassignBasicAnimationForField re-adds only the five loco slots) --
    plays BY NAME (``ro["inactive_clip"]``) in the rig's GEO, clip_playing, frame_n == its count off p0data5
    (``ro["inactive_frames"]``; CheckSleep's ExecAnim of a clip the go lacks reads frameN 255 and plays nothing); and never
    IDLE_NULL_RUN publishes in a row with the player free and NOTHING playing (clip or anim_geo null: that freeze). A rig
    with no break clip judges the null run alone."""
    run = worst = 0
    for s in idle:
        p = _player(s)
        run = run + 1 if (p.get("clip") is None or p.get("anim_geo") is None) else 0
        worst = max(worst, run)
    bad = []
    if worst >= IDLE_NULL_RUN:
        bad.append(f"{worst} idle publishes in a row playing NOTHING (want < {IDLE_NULL_RUN}: a clip the go lacks)")
    name, frames = ro.get("inactive_clip"), _int(ro.get("inactive_frames"))
    hits = []
    if name:
        hits = [s for s in idle if _player(s).get("clip") == name]
        good = [s for s in hits if _player(s).get("anim_geo") == ro.get("geo") and _player(s).get("clip_playing") is True
                and _int(_player(s).get("frame_n")) == frames]
        if not good:
            first = _player(hits[0]) if hits else {}
            bad.append(f"the break clip {name!r} never played in {ro.get('geo')!r} with frame_n {frames} ({len(hits)} "
                       f"publishes named it" + (f"; first: {_show(first, 'anim_geo')} {_show(first, 'clip_playing')} "
                                                f"{_show(first, 'frame_n')}" if hits else "") + ")")
    return not bad, (f"break clip {name!r}: {len(hits)} publishes, longest null run {worst}"
                     + (f"; WRONG: {'; '.join(bad)}" if bad else ""))


def judge_w1(*, base, back, returns0, lines: list, rest: list, idle: list, walk: dict, ro: dict, rig: int,
             src_list=None) -> tuple:
    """W1 (PURE): THE WARM RETURN -- the return WARM (last_return 'warm', returns +1); the body back still the rig (the
    oracle's model, body, GEO, eye), `self.uid` the dressed load's, net_byte rig + 1, AttachDress AT THE REBUILD
    (:func:`attach_mismatch` across [base, back], site b: attach_warm +1, attach_cold +0, then src_attached > 0 and
    src_list_clips == ``src_list``, the field's own SOURCE list read offline) and NO dress line since the boot (no SetModel:
    PosObj.copy carried the dress); at rest `anim` == the oracle's idle id; the idle window past the inactive timer
    (:func:`judge_break_clip`: the rig's break clip by NAME, never a run of nothing playing) with every `anim_geo` it carries
    the rig's GEO, and the walk's middle on the rig's GEO (:func:`judge_geo_throughout`)."""
    d, s, p = cb.dio(back), _self(back), _player(back)
    if s is None:
        return False, "netsync.dress.self ABSENT -- an engine before s140"
    bad = []
    if d.get("last_return") != "warm" or not (isinstance(returns0, int) and d.get("returns") == returns0 + 1):
        bad.append(f"the return: last_return {d.get('last_return')!r} returns {returns0!r} -> {d.get('returns')!r} (want "
                   f"'warm', +1)")
    bad += [f"back: {b}" for b in body_mismatch(p, ro)]
    uid0 = (_self(base) or {}).get("uid")
    if s.get("uid") != uid0 or _int(uid0) is None:
        bad.append(f"self.uid {s.get('uid')!r} (want the dressed load's {uid0!r})")
    if s.get("net_byte") != rig + 1:
        bad.append(f"self.net_byte {s.get('net_byte')!r} (want {rig + 1})")
    abad, afacts = attach_mismatch(base, back, site="warm", src_list=src_list)
    bad += abad
    relines = dress_lines(lines)
    if relines:
        bad.append(f"{len(relines)} dress line(s) since the boot (want none: a warm return re-dresses through no SetModel)")
    pr = _player(rest[-1]) if rest else {}
    if not rest or _int(pr.get("anim")) != ro.get("idle"):
        bad.append(f"at rest {_show(pr, 'anim')} (want the idle id {ro.get('idle')})")
    ok_i, why_i = judge_geo_throughout(idle, ro.get("geo"))
    if not ok_i:
        bad.append(f"idle past the timer: {why_i}")
    ok_b, why_b = judge_break_clip(idle, ro)
    if not ok_b:
        bad.append(f"idle past the timer: {why_b}")
    mid = moving_middle(walk.get("samples") or []) if walk.get("dir") else []
    ok_w, why_w = judge_geo_throughout(mid, ro.get("geo")) if mid else (False, f"no move ({walk.get('why')})")
    if not ok_w:
        bad.append(f"walking: {why_w}")
    return not bad, ((f"WRONG: {'; '.join(bad)} -- " if bad else "")
                     + f"return {cb.pick(d, 'last_return', 'returns')}; back {_show(p, 'model')} {_show(p, 'body')} "
                     f"{_show(p, 'anim_geo')}; self {cb.pick(s, 'uid', 'net_byte')}; {afacts}; idle window "
                     f"{len(idle)} publishes ({why_i}; {why_b}); walk {why_w}")


# ---- [ff9mapkit netsync s141] leg F's pure judges -------------------------------------------------------------------
def _polish(x) -> dict | None:
    """``netsync.dress.self`` when it carries s141's polish keys (`steps` present), else None (an engine before s141)."""
    s = _self(x)
    return s if isinstance(s, dict) and "steps" in s else None


def _f_absent(x, key: str) -> str:
    """The red detail of an engine before s141 (the s141 key ``key`` absent) -- what that engine shows instead: s140 dresses
    the body (its `self` block) but publishes no footstep, light, mesh or prop witness; only the s138 instrument reads."""
    p = _player(x)
    return (f"netsync.dress.self.{key} ABSENT -- an engine before s141 (`self` "
            f"{'present: s140 dresses the body but publishes no s141 witness' if _self(x) is not None else 'absent'}); "
            f"only the s138 instrument reads here: {_show(p, 'model')} {_show(p, 'anim')} {_show(p, 'clip')} "
            f"{_show(p, 'meshflags')}")


def step_pairs(steps) -> list | None:
    """(PURE) `steps` ([anim, frame, sndEffectID[0]] triples) -> [(anim, frame)] in table order; None when it is not a list
    of int triples."""
    if not isinstance(steps, list):
        return None
    out = []
    for r in steps:
        if not isinstance(r, list) or len(r) != 3 or any(_int(v) is None for v in r):
            return None
        out.append((r[0], r[1]))
    return out


def f_dress_pin(x, ro: dict, rig: int) -> str | None:
    """(PURE) None when the controlled body wears what the row dressed it as -- `player.model` the oracle's and, on an engine
    that publishes `self`, `self.rig` == ``rig`` (-1: the undressed control) -- else why not. A row's PREMISE (read "not
    reached"): the steps / light / prop of a body that is not the one asked for prove nothing (pin the intended dress)."""
    p, s = _player(x), _self(x)
    bad = []
    if _int(p.get("model")) is None or p.get("model") != ro.get("model"):
        bad.append(f"player.model {p.get('model')!r} (want the oracle's {ro.get('name')} {ro.get('model')})")
    if s is not None and s.get("rig") != rig:
        bad.append(f"self.rig {s.get('rig')!r} (want {rig})")
    return "; ".join(bad) or None


def judge_f_steps(st, want: dict, ro: dict, *, rig: int, sound=None, before=None, lines=None) -> tuple:
    """F1 / F2 / F2c / F3 / F7 (PURE): one FRESH load's settled publish ``st`` against the oracle's one-load replay ``want``
    ({steps, steps_dropped, steps_passed}: the census twin over the field's own footstep ops) -- on the body the row asked
    for (:func:`f_dress_pin`, else "not reached"): `steps` as (anim, frame) pairs in TABLE order == the oracle's, no
    duplicate key, steps_dropped / steps_passed == the oracle's (ONE load's); with ``sound`` every key's sndEffectID[0] ==
    it (F7: Steiner's 925); with ``before`` (the publish before the warp) the s140 `faults` counter +0 across the load and
    with ``lines`` (Memoria.log since the warp) no :data:`F_FAULT_LINES` line (F2 / F2c: a hook fault -- field 250 runs no
    code 19, so the empty-table guard is F2d's to witness, never these rows'). The duplicate-key half is a STOCK invariant
    (fldchar's find-or-create never appends a key twice), kept as a malformed-witness check, never as a polish witness."""
    pin = f_dress_pin(st, ro, rig)
    if pin:
        return False, f"{_NR}the body is not the one asked for: {pin}"
    s = _polish(st)
    if s is None:
        return False, _f_absent(st, "steps")
    pairs, want_pairs = step_pairs(s.get("steps")), [tuple(r[:2]) for r in want["steps"]]
    bad, extra = [], []
    if pairs is None:
        bad.append(f"steps {s.get('steps')!r} (not a list of [anim, frame, sound] ints)")
    else:
        if pairs != want_pairs:
            bad.append(f"steps (anim, frame) {pairs} (want {want_pairs})")
        dup = sorted({k for k in pairs if pairs.count(k) > 1})
        if dup:
            bad.append(f"duplicate keys {dup} (want each once: one load's table)")
        if sound is not None and (not pairs or any(r[2] != sound for r in s["steps"])):
            bad.append(f"sounds {[r[2] for r in s['steps']]} (want {sound} on every key)")
    for key in ("steps_dropped", "steps_passed"):
        if s.get(key) != want[key]:
            bad.append(f"{key} {s.get(key)!r} (want {want[key]}: one load's)")
    if before is not None:
        df = count_delta(before, st, "faults")
        extra.append(f"faults +{df}")
        if df != 0:
            bad.append(f"faults +{df} across the load (want +0: no hook fault)")
    if lines is not None:
        hits = [ln for ln in lines if any(n in ln for n in F_FAULT_LINES)]
        extra.append(f"{len(hits)} fault line(s) since the warp")
        if hits:
            bad.append(f"{len(hits)} fault line(s) since the warp: {cb.grep(hits, *F_FAULT_LINES, limit=240)}")
    return not bad, ((f"WRONG: {'; '.join(bad)} -- " if bad else "")
                     + f"steps {s.get('steps')!r} dropped {s.get('steps_dropped')!r} passed {s.get('steps_passed')!r} "
                     f"(oracle {want['steps']} / {want['steps_dropped']} / {want['steps_passed']}) on {ro.get('name')} "
                     f"(model {ro.get('model')}, rig {rig})" + (f"; {'; '.join(extra)}" if extra else ""))


def walk_ticks(samples: list) -> int:
    """(PURE) The field ticks a walk MOVED: the publishes that moved from the one before (a tickless render frame does
    not move)."""
    return sum(1 for a, b in zip(samples, samples[1:]) if _moved(a, b))


def judge_f_fired(walk: dict, ro: dict, *, rig: int, key: str, other: str) -> tuple:
    """F1b / F3 / F6's walk (PURE): ``walk`` (:func:`_f_walk`: its samples, the publish BEFORE its first hold and the one
    AFTER it settled -- the bracket) on the body the row asked for: the walk MOVED F_MIN_MOVE_TICKS+ field ticks on the
    field (else "not reached": no footfall could fire -- a hold TAKEN OVER the same); then FF9Snd's own frame match counted
    ``key`` +F_FIRED_MIN or more across the bracket, and ``other`` +0 (the dressed / undressed split: a footfall on a
    dressed body is `steps_fired`, on an undressed one `steps_fired_player`)."""
    if walk.get("left"):
        return False, f"{_NR}the walk's hold was TAKEN OVER ({walk.get('why')})"
    before, after = walk.get("before"), walk.get("after")
    if before is None or after is None:
        return False, f"{_NR}the walk did not run ({walk.get('why')})"
    pin = f_dress_pin(before, ro, rig)
    if pin:
        return False, f"{_NR}the body is not the one asked for: {pin}"
    samples = walk.get("samples") or []
    ticks = walk_ticks(samples)
    anims = sorted({_player(s).get("anim") for s in samples if _int(_player(s).get("anim")) is not None})
    moved = f"the walk moved {ticks} field ticks ({walk.get('dir')!r}, anims {anims})"
    if ticks < F_MIN_MOVE_TICKS:
        return False, f"{_NR}{moved} -- want {F_MIN_MOVE_TICKS}+ (no footfall could fire on so short a walk)"
    if _polish(after) is None:
        return False, f"{_f_absent(after, key)}; {moved}"
    d, o = count_delta(before, after, key), count_delta(before, after, other)
    ok = d is not None and d >= F_FIRED_MIN and o == 0
    return ok, (("" if ok else f"WRONG: {key} +{d} (want +{F_FIRED_MIN} or more) / {other} +{o} (want +0) -- ")
                + f"{key} +{d}, {other} +{o} across the walk; {moved}")


def _light_floor_read(x, floors) -> tuple:
    """(the engine's `self.light_floor` as an int or None, the kit walkmesh's floors as a sorted list or None, the text
    naming both) -- the F4 / F4g oracle's INPUT and its cross-check."""
    lf = _int((_polish(x) or {}).get("light_floor"))
    kit = sorted(int(f) for f in floors) if floors is not None else None
    return lf, kit, f"light_floor {lf!r} (the kit walkmesh puts (x, z) {_pos(x)} on floor(s) {kit})"


def judge_f4(st, light: dict, ro: dict, *, rig: int, floors, src: int) -> tuple:
    """F4 (PURE): the dressed body's light on the F1 load's settled publish -- on the body the row asked for (the rig's model,
    never 98: an UNDRESSED Zidane reads his own 98 row's colour, so the colour alone proves nothing). THE FLOOR is the
    ENGINE's `light_floor` (the FF9FieldCharState.floor fldmcf lit the body by, written with the tint -- the oracle's INPUT,
    never its answer); ``light`` the oracle's per-floor table for the rig model ({floor: {"s141": {row, rgb}, "off": {row,
    rgb}}}: the census's light_color over the field's own MapConfigData, every walkmesh floor and 255 = none): `light_row`
    == the source row ``src`` (98) and `light_rgb` == its tint on `light_floor`; ``floors`` the kit's stock walkmesh floors
    under the publish's OWN x / z (read offline -- the published `player.floor` is s83's dead battle-entry snapshot, never
    read), REPORTED beside it: `light_floor` not among them is a red with both shown, never silently passed. A rig model
    with its OWN row on that floor cannot show the fallback ("not reached"); no `light_floor` (-1: no mapconfig service for
    the dressed body) is red."""
    pin = f_dress_pin(st, ro, rig)
    if pin:
        return False, f"{_NR}the body is not the one asked for: {pin}"
    s = _polish(st)
    if s is None:
        return False, _f_absent(st, "light_row")
    row, rgb = s.get("light_row"), s.get("light_rgb")
    lf, kit, where = _light_floor_read(st, floors)
    if lf is None or lf < 0:
        return False, f"WRONG -- light_row {row!r} light_rgb {rgb!r}, {where}: no floor the engine lit the dressed body by"
    w = light.get(lf)
    if w is None:
        return False, f"{_NR}no oracle light for {where}"
    if w["s141"]["row"] != src:
        return False, (f"{_NR}the rig model {ro.get('model')} has its OWN row on floor {lf} ({w['s141']['row']}): F4 cannot "
                       f"see the source-row fallback")
    bad = []
    if row != src:
        bad.append(f"light_row {row!r} (want the source row {src})")
    if not (isinstance(rgb, list) and list(rgb) == list(w["s141"]["rgb"])):
        bad.append(f"light_rgb {rgb!r} (want the source row's tint on floor {lf}: {w['s141']['rgb']})")
    if kit is None or lf not in kit:
        bad.append(f"the engine lit floor {lf}, the kit walkmesh names {kit} at (x, z) {_pos(st)}: the two disagree")
    return not bad, ((f"WRONG: {'; '.join(bad)} -- " if bad else "")
                     + f"light_row {row!r} light_rgb {rgb!r} on {where} (oracle: row {src}, the source row's tint "
                     f"{w['s141']['rgb']}; the default row's {w['off']['rgb']}) on {ro.get('name')} model {ro.get('model')}")


def judge_f4g(samples: list, ghost_light: dict, ro: dict, *, rig: int, floors, src: int) -> tuple:
    """F4g (PURE): the ghost's lighting fallback -- on the LAST publish of ``samples`` (the F1 load, FieldHUD, the ghost
    driven) whose ghost has RE-TINTED (`ghost.light_row` != -1, its per-load sentinel) while wearing the dressed body's
    model (ghost.model == player.model == the rig's: GhostGuard shows the dressed wire as it is): `ghost.light_row` == the
    oracle's ghost row (``ghost_light``: the census's ghost_light_color -- the ghost model has no row, so ApplyGhostLighting
    falls to the LOCAL player's stand-in row: 98 while dressed) AND `ghost.light_rgb` -- the tint it WROTE, read off the
    ghost's material: the witness the row (the engine's own decision) cannot give -- that row's tint on the player's
    `light_floor` (the ghost is lit by the LOCAL player's floor light); the kit walkmesh's floors (``floors``) reported beside
    it, a disagreement red. A ghost model with its own row cannot show it ("not reached"); a ghost that never re-tinted on
    the dressed model is red."""
    if not samples:
        return False, f"{_NR}no publish on the field after the load"
    pin = f_dress_pin(samples[-1], ro, rig)
    if pin:
        return False, f"{_NR}the body is not the one asked for: {pin}"
    gh = ((_dress(samples[-1]) or {}).get("ghost") or {})
    if "light_row" not in gh:
        return False, (f"netsync.dress.ghost.light_row ABSENT -- an engine before s141 (the ghost wears "
                       f"{gh.get('model')!r}, the default row unwitnessed)")
    worn = [s for s in samples
            if (((_raw(s).get("netsync") or {}).get("session") or {}).get("ghost") is True
                and ((_dress(s) or {}).get("ghost") or {}).get("model") == _player(s).get("model") == ro.get("model"))]
    tinted = [s for s in worn if _int(((_dress(s) or {}).get("ghost") or {}).get("light_row")) not in (None, -1)]
    if not worn:
        return False, (f"{_NR}the ghost never wore the dressed model {ro.get('model')} (last: ghost.model "
                       f"{gh.get('model')!r}, session.ghost "
                       f"{((_raw(samples[-1]).get('netsync') or {}).get('session') or {}).get('ghost')!r})")
    if not tinted:
        return False, f"the ghost wore {ro.get('model')} on {len(worn)} publishes but never re-tinted (light_row -1)"
    last = tinted[-1]
    g = (_dress(last) or {}).get("ghost") or {}
    row, rgb = _int(g.get("light_row")), g.get("light_rgb")
    lf, kit, where = _light_floor_read(last, floors)
    if lf is None or lf < 0:
        return False, f"WRONG -- ghost.light_row {row!r} light_rgb {rgb!r}, {where}: no floor the engine lit the player by"
    w = ghost_light.get(lf)
    if w is None:
        return False, f"{_NR}no oracle ghost light for {where}"
    if w["s141"]["row"] != src:
        return False, (f"{_NR}the oracle's ghost row on floor {lf} is {w['s141']['row']} (want the stand-in row {src}: a "
                       f"ghost model with its own row cannot show the fallback)")
    bad = []
    if row != src:
        bad.append(f"ghost.light_row {row!r} (want the stand-in row {src})")
    if not (isinstance(rgb, list) and list(rgb) == list(w["s141"]["rgb"])):
        bad.append(f"ghost.light_rgb {rgb!r} (want the {src} row's tint on floor {lf}: {w['s141']['rgb']} -- the tint the "
                   f"re-tint WROTE)")
    if kit is None or lf not in kit:
        bad.append(f"the engine lit floor {lf}, the kit walkmesh names {kit} at (x, z) {_pos(last)}: the two disagree")
    return not bad, ((f"WRONG: {'; '.join(bad)} -- " if bad else "")
                     + f"ghost.light_row {row!r} light_rgb {rgb!r} on the dressed model {ro.get('model')} "
                     f"({len(tinted)} re-tinted publishes; {where}; oracle {src} / {w['s141']['rgb']}: the local player's "
                     f"stand-in row, the default {w['off']['row']} / {w['off']['rgb']} under `polish off`)")


def judge_f5(hide: dict, after_hide: list, show: dict | None, after_show: list, ro: dict, *, rig: int) -> tuple:
    """F5 (PURE): the bench field's F5H run (:func:`_conduct`) on the dressed body -- DONE_F5H (else "not reached": the
    conductor never ran); mesh_drops +1 or more across [the READY publish, the last publish after it] and
    `player.meshflags` 0 on the DONE publish and every one after (the op DROPPED -- stock would set bit 1 << 1 = 2); then
    F5S: DONE_F5S and meshflags 0 after it (restored in every mode: PosObj.copy would carry a set bit into a warm
    return)."""
    if hide.get("outcome") != "done":
        return False, f"{_NR}F5H: {hide.get('why')} ({hide.get('outcome')})"
    pin = f_dress_pin(hide.get("before"), ro, rig)
    if pin:
        return False, f"{_NR}the body is not the one asked for: {pin}"
    tail = [hide["end"]] + list(after_hide)
    flags = [_player(s).get("meshflags") for s in tail]
    s_end = _self(tail[-1]) or {}
    show_ok, show_why = False, "F5S not run"
    if show is not None:
        sflags = [_player(s).get("meshflags") for s in ([show["end"]] + list(after_show))] if show.get("end") else []
        show_ok = show.get("outcome") == "done" and bool(sflags) and all(f == 0 for f in sflags)
        show_why = f"F5S {show.get('outcome')}, meshflags after it {sorted(set(map(str, sflags)))}"
    if "mesh_drops" not in s_end:
        return False, (f"netsync.dress.self.mesh_drops ABSENT -- an engine before s141: F5H ran on the dressed body, meshflags "
                       f"after it {sorted(set(map(str, flags)))} (stock sets bit 1 << 1 = 2); {show_why}")
    d = count_delta(hide.get("before"), tail[-1], "mesh_drops")
    ok = d is not None and d >= 1 and all(f == 0 for f in flags) and show_ok
    return ok, (("" if ok else "WRONG -- ") + f"mesh_drops +{d} across F5H (want +1 or more), meshflags after it "
                f"{sorted(set(map(str, flags)))} (want 0: the op dropped); {show_why} (want done, 0)")


def judge_f6(*, base, back, returns0, want: dict, walk: dict, ro: dict, rig: int) -> tuple:
    """F6 (PURE): THE WARM RETURN on the stock field -- last_return 'warm', returns +1 (else "not reached": the row is about a
    warm return; the body at the return the rig asked for, else "not reached"); `steps` == the oracle's warm-return replay
    ``want`` (Main_Reinit re-runs the player's footstep ops into the table the load reset cleared: the same keys),
    steps_dropped / steps_passed ONE load's, and steps_fired 0 at the return -- the per-load reset, judged only when
    ``base`` (the last publish before the boot) CARRIED F_FIRED_MIN+ fires (else the half cannot fail: "not reached"); then
    the walk after the return (:func:`judge_f_fired`) fires +2 or more. A JUDGED red in any half is the verdict, even when
    another half did not run ("not reached" only when no judged half is red)."""
    d = cb.dio(back)
    if d.get("last_return") != "warm" or not (isinstance(returns0, int) and d.get("returns") == returns0 + 1):
        return False, (f"{_NR}the return: last_return {d.get('last_return')!r} returns {returns0!r} -> {d.get('returns')!r} "
                       f"(want 'warm', +1: F6 is the warm return)")
    ok_s, why_s = judge_f_steps(back, want, ro, rig=rig)
    if why_s.startswith(_NR):
        return False, f"{_NR}at the return: {why_s[len(_NR):]}"
    if _polish(back) is None:
        return False, f"at the return: {why_s}"
    fired_back, fired_base = self_count(back, "steps_fired"), self_count(base, "steps_fired")
    reset_judged = isinstance(fired_base, int) and fired_base >= F_FIRED_MIN
    reset_ok = fired_back == 0
    ok_w, why_w = judge_f_fired(walk, ro, rig=rig, key="steps_fired", other="steps_fired_player")
    walk_nr = why_w.startswith(_NR)
    reset_why = (f"steps_fired {fired_base!r} before the boot -> {fired_back!r} at the return (want 0: ONE load's count)"
                 if reset_judged else f"the reset half NOT JUDGED: steps_fired {fired_base!r} before the boot (want "
                                      f"{F_FIRED_MIN}+ to witness the per-load reset), {fired_back!r} at the return")
    detail = (f"return {cb.pick(d, 'last_return', 'returns')}; at the return {why_s}; {reset_why}; after the return "
              f"{why_w.removeprefix(_NR)}")
    judged_red = (not ok_s) or (reset_judged and not reset_ok) or (not walk_nr and not ok_w)
    if judged_red:
        return False, "WRONG -- " + detail
    if walk_nr or not reset_judged:
        return False, _NR + detail
    return True, detail


def judge_f8(attach: dict, after_a: list, detach: dict | None, after_d: list, hand: dict, ro: dict, *, rig: int,
             cup: int, bone: int) -> tuple:
    """F8 (PURE): F8A on the dressed carrier -- DONE_F8A (else "not reached"); attach_remaps +1 and attach_notes +0 across
    [the READY publish, the last publish after it]; `attach_last` on that last publish == {uid: the cup, bone_in: ``bone``
    (13, stock's held-item bone), bone_out: the skin's R_hand_end, parent: its NAME} -- ``hand``, the oracle read off the
    rig's SKIN (:func:`hand_oracle_read`: never labels_for, never the engine's table); the parent is read LIVE (the carried
    go's transform parent:
    geoAttach's 'bone%03d'). Then F8D: DONE_F8D and the parent no longer that bone (a live read, never a value the engine
    cached at the attach)."""
    if attach.get("outcome") != "done":
        return False, f"{_NR}F8A: {attach.get('why')} ({attach.get('outcome')})"
    pin = f_dress_pin(attach.get("before"), ro, rig)
    if pin:
        return False, f"{_NR}the body is not the one asked for: {pin}"
    if hand.get("hand_end") is None or hand.get("end_name") not in (hand.get("names") or ()):
        return False, f"{_NR}no oracle R_hand_end on {ro.get('name')}'s skeleton ({hand})"
    last = ([attach["end"]] + list(after_a))[-1]
    s = _self(last) or {}
    if "attach_last" not in s:
        return False, ("netsync.dress.self.attach_last ABSENT -- an engine before s141 (the prop went to bone "
                       f"{bone} as asked: on {ro.get('name')} that is not the hand; unwitnessed)")
    want = {"uid": int(cup), "bone_in": int(bone), "bone_out": int(hand["hand_end"]), "parent": hand["end_name"]}
    al = s.get("attach_last")
    got = {k: (al or {}).get(k) for k in want} if isinstance(al, dict) else al
    dr, dn = count_delta(attach.get("before"), last, "attach_remaps"), count_delta(attach.get("before"), last, "attach_notes")
    bad = []
    if dr != 1 or dn != 0:
        bad.append(f"attach_remaps +{dr} / attach_notes +{dn} (want +1 / +0)")
    if got != want:
        bad.append(f"attach_last {got} (want {want})")
    det = "F8D not run"
    if detach is not None:
        tail = ([detach["end"]] + list(after_d)) if detach.get("end") is not None else []
        par = (((_self(tail[-1]) or {}).get("attach_last") or {}).get("parent")) if tail else None
        det = f"F8D {detach.get('outcome')}, parent after it {par!r}"
        if detach.get("outcome") != "done" or par == hand["end_name"]:
            bad.append(f"{det} (want done, and the prop OFF {hand['end_name']}: a live read)")
    else:
        bad.append(det)
    return not bad, ((f"WRONG: {'; '.join(bad)} -- " if bad else "")
                     + f"attach_last {got}, attach_remaps +{dr}, attach_notes +{dn}; {det} (oracle: {ro.get('name')}'s "
                     f"R_hand_end bone {hand['hand_end']} = {hand['end_name']!r}, by {hand.get('source')})")


def judge_f2d(run: dict, after: list, ro: dict, *, rig: int, want: dict) -> tuple:
    """F2d (PURE): THE EMPTY-TABLE GUARD's in-game witness -- the bench field's F2d run (:func:`_conduct`) on the dressed DROP
    rig (the moogle) after a fresh load whose twelve footstep registrations the rig DROPPED (the table is EMPTY): field 2930's
    RunModelCode(19, 190, 4, 0) in the player's own entry (a 190: the rule PASSES it, so only the guard can drop it). The
    caller's DONE (WEDGED -- the player's function never set F2D_END within the caller's bound -- is a JUDGED red; no answer
    at all "not reached"); across [the READY publish, the last publish after it] steps_dropped and steps_passed move by the
    oracle's ``want`` (the census twin WITH the guard over the deployed .eb's own registrations + the op: +1 / +0), `steps`
    ends the oracle's ([]), the s140 `faults` +0, no :data:`F_FAULT_LINES` line since the trigger (stock DeleteChar's
    IndexOutOfRangeException would be one) and the guard's OWN line (:data:`F2D_GUARD_LINE`) logged -- the branch the 19
    took. s140's shape (no `steps_dropped`) is red; so is `polish off`'s (the twelve register: the 19 is stock's no-op)."""
    outcome = run.get("outcome")
    if outcome not in ("done", "wedged"):
        return False, f"{_NR}F2d: {run.get('why')} ({outcome})"
    pin = f_dress_pin(run.get("before"), ro, rig)
    if pin:
        return False, f"{_NR}the body is not the one asked for: {pin}"
    last = ([run["end"]] + list(after or []))[-1] if run.get("end") is not None else run.get("before")
    lines = list(run.get("lines") or [])
    hits = [ln for ln in lines if any(n in ln for n in F_FAULT_LINES)]
    guard = [ln for ln in lines if F2D_GUARD_LINE in ln]
    s = _polish(last)
    if s is None:
        return False, (f"{_f_absent(last, 'steps_dropped')}; F2d {outcome}, {len(hits)} fault line(s) since the trigger"
                       + (f": {cb.grep(hits, *F_FAULT_LINES, limit=240)}" if hits else ""))
    before = run.get("before")
    dd, dp, df = (count_delta(before, last, k) for k in ("steps_dropped", "steps_passed", "faults"))
    bad = []
    if outcome != "done":
        bad.append(f"F2d WEDGED ({run.get('why')}: the player's function never set F2D_END -- the op did not return)")
    if dd != want["steps_dropped"]:
        bad.append(f"steps_dropped +{dd} (want +{want['steps_dropped']}: the guard's drop)")
    if dp != want["steps_passed"]:
        bad.append(f"steps_passed +{dp} (want +{want['steps_passed']}: a drop is never a pass)")
    if s.get("steps") != want["steps"]:
        bad.append(f"steps {s.get('steps')!r} (want {want['steps']})")
    if df != 0:
        bad.append(f"faults +{df} (want +0: no hook fault)")
    if hits:
        bad.append(f"{len(hits)} fault line(s) since the trigger: {cb.grep(hits, *F_FAULT_LINES, limit=240)}")
    if not guard:
        bad.append(f"no guard line ('{F2D_GUARD_LINE}') since the trigger: the 19 took another branch")
    return not bad, ((f"WRONG: {'; '.join(bad)} -- " if bad else "")
                     + f"F2d {outcome}: steps_dropped +{dd}, steps_passed +{dp}, steps {s.get('steps')!r}, faults +{df}, "
                     f"{len(hits)} fault line(s), {len(guard)} guard line(s) since the trigger (oracle {want}) on "
                     f"{ro.get('name')} (model {ro.get('model')}, rig {rig})")


def judge_f_proof(lines: list) -> tuple:
    """FP (PURE): the proof block's LATEST 'dress polish selftest' line reads OK with the engine's row count
    (battlewire.DRESS_POLISH_SELFTEST_ROWS) -- no key publishes the verdict (audit 3.1 lists none): the line is the record."""
    hits = [ln for ln in lines or () if BW.PROOF_DRESS_POLISH in ln]
    if not hits:
        return False, f"no '{BW.PROOF_DRESS_POLISH.strip()}' line in Memoria.log -- an engine before s141 (want {F_PROOF_LINE!r})"
    line = hits[-1].split("[NetSync] ", 1)[-1].strip()
    return line == F_PROOF_LINE, f"proof line {line!r} (want {F_PROOF_LINE!r})"


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
def _ini_guard(g, legs=()) -> tuple:
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
    # [ff9mapkit netsync s140] [Netsync] SelfDress (read LIVE by the engine, a behaviour key): 0 switches off the guest's
    # own dress, so every s140 row would read it -- the bench's knob is `self off`, never an ini edit mid-run
    ok_s = True
    if any(LEGS[leg]["patch"] >= 140 for leg in legs):
        sd = cb.ini_value(g, "Netsync", "SelfDress")
        ok_s = sd is None or sd.strip().strip('"').strip() in SELF_DRESS_OK
        why += f", SelfDress = {sd!r}" + ("" if ok_s else " -- the guest's own dress is switched OFF: every s140 row would "
                                                         "read it red; set it to 1 (or remove it) BY HAND")
    return ok_e and ok_g and ok_s, why


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
    # [ff9mapkit netsync s140] only a leg that needs the seed (legs I / G) runs it, and only its OWN fields gate it
    if not any(PARTY_FIELD in LEGS[leg]["pre"] for leg in ctx["legs"]):
        return
    if {PARTY_FIELD, BENCH_FIELD} & set(ctx.get("missing") or ()):
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
    rules = stage_rules(stage)                         # [ff9mapkit netsync s140] the PROBED engine's rules
    want = want_ghost(rest[-1], LEVERS_OFF, ctx.get("ghost_as"), rules) if rest else None
    models, clips = _dress_oracle(g, ctx, {want["model"]} if want else set())
    ok, why = judge_worn(rest, levers=LEVERS_OFF, ghost_as=ctx.get("ghost_as"), models=models, clips=clips, rules=rules)
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
    """(every rig row's idle frame count, or None; why) -- THE FRAME LAW off the install: each rig row's idle clip (the
    twin's ids, battlewire.RIGS, pinned to the census: [ff9mapkit netsync s140] thirteen rows, G6 judges the probed engine's
    first rows) read out of p0data5 by the kit's clip reader (ff9mapkit.models._gltf_io.read_clip at the folder
    ff9mapkit.catalog.locate_animation resolves -- the engine's own folder rule), counted by EventEngineUtils.
    GetCharAnimFrame's formula round(length x rate) + 1 (the kit's thumbcache frame law). READ-ONLY: a UnityPy load of the
    bundle writes nothing ([s140] loaded once a run, :func:`_p0data5`: the s140 oracle reads it too)."""
    _kit()
    from ff9mapkit import catalog
    from ff9mapkit.models import _gltf_io
    bundle, disc = _p0data5(game)
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


# ------------------------------------------------------------------------------------------------ the s140 legs' offline oracle
_P0DATA5: dict = {}


def _p0data5(game: Path) -> tuple:
    """(bundle, its animation disc map) of the install's p0data5 -- loaded ONCE per run (a UnityPy load writes nothing)."""
    key = str(Path(game))
    if key not in _P0DATA5:
        _kit()
        from ff9mapkit import extract as X
        from ff9mapkit.models import _gltf_io
        bundle = X._unitypy().load(str(Path(game) / "StreamingAssets" / "p0data5.bin"))
        _P0DATA5[key] = (bundle, _gltf_io.anim_disc_map(bundle))
    return _P0DATA5[key]


def clip_frames(game: Path, pairs) -> dict:
    """{(anim, model): frames or None} -- each clip read out of p0data5 by the kit's clip reader at the folder
    ff9mapkit.catalog.locate_animation resolves (the engine's own folder rule), counted by EventEngineUtils.GetCharAnimFrame's
    formula round(length x rate) + 1 (THE FRAME LAW). READ-ONLY."""
    _kit()
    from ff9mapkit import catalog
    from ff9mapkit.models import _gltf_io
    bundle, disc = _p0data5(game)
    out = {}
    for anim, model in pairs:
        loc = catalog.locate_animation(anim, model, disc) if anim else None
        clip = _gltf_io.read_clip(bundle, loc[1], loc[0]) if loc else None
        out[(anim, model)] = (None if clip is None
                              else int(round(float(clip["length"]) * float(clip["sample_rate"] or 30.0))) + 1)
    return out


def setmodel_eyes(data: bytes, model: int) -> list:
    """(PURE over a field script) The eye byte of every SetModel(``model``, eye) in any entry's functions (the kit's .eb
    reader; an expression operand reads None and is skipped)."""
    _kit()
    from ff9mapkit.eb import disasm
    from ff9mapkit.eb.model import EbScript
    s = EbScript(data)
    out = []
    for e in s.entries[1:]:
        if e.empty:
            continue
        for f in e.funcs:
            for ins in disasm.iter_code(s.data, f.abs_start, f.abs_end):
                if ins.op == OP_SET_MODEL and ins.imm(0) == int(model) and ins.imm(1) is not None:
                    out.append(int(ins.imm(1)))
    return out


def _census_rows() -> tuple:
    """({name: {model, eye}} of the census's rows 9-12 -- dress-census/rigs_8_11.json, a CROSS-CHECK only), or (None, why)."""
    import json
    try:
        rows = json.loads(CENSUS_JSON.read_text(encoding="utf-8"))["rows"]
        return {str(r["name"]): {"model": int(r["cols"]["model"]), "eye": int(r["cols"]["eye"])}
                for r in rows.values()}, ""
    except (OSError, ValueError, KeyError, TypeError) as err:
        return None, f"{CENSUS_JSON.name}: {type(err).__name__}: {str(err)[:160]}"


def s_oracle_read(game: Path, known_models: dict | None = None) -> tuple:
    """The s140 legs' OFFLINE oracle: ({"rigs": {name: {name, model, geo, body, eye, idle, walk, run, inactive, idle_clip,
    walk_clip, run_clip, inactive_clip, idle_frames}}, "models": {model: {geo, body}}, "clips": AnimationDB, "sources": {x:
    frames, t1: frames}}, {key: why}) -- every rig a row dresses as (:data:`S_ORACLE_RIGS`), each read through the KIT'S
    readers, never the engine's tables: a main's model, eye byte and loco ids off the kit's playerswap.CHARACTERS (its
    proven home-field rig table); the moogle's and Cinna..Beatrix's model by their GEO name in the kit's table
    (:data:`RIG_GEO_NAMES`), their loco ids off the kit's model->animation join (catalog.npc_anims) and their eye byte the
    modal SetModel byte of a STOCK script that wears them (:data:`EYE_FIELDS`, through the kit's events-bundle cache -- "not
    reached" when it is missing: the bench never creates it); each model's GEO name and texture stem off the install
    (:func:`model_facts`, or ``known_models`` -- leg G's oracle, the same reader); the clip NAMES off the kit's copy of the
    open-source AnimationDB; each idle's and the conductors' source clips' frame counts off p0data5 (:func:`clip_frames`).
    CROSS-CHECKS, each disagreement a named problem: the twin's rig row (battlewire.RIGS via NAME_TO_RIG: model, eye, the
    idle / walk / run clip NAMES), the census (rows 9-12's model and eye), the bench field's contract (the source clips'
    frames)."""
    _kit()
    from ff9mapkit import catalog
    from ff9mapkit import extract as X
    from ff9mapkit._animdb_all import ANIMATIONS
    from ff9mapkit._modeldb import MODELS
    from ff9mapkit.playerswap import ALIASES, CHARACTERS
    game = Path(game)
    problems, rigs, models = {}, {}, dict(known_models or {})
    by_geo = {}
    for mid, geo in MODELS.items():
        by_geo.setdefault(geo, mid)
    install_ok = not kit_cache_missing(game)
    scripts = {}

    def script(fid: int):
        if fid not in scripts:
            scripts[fid] = X.extract_event_script(str(int(fid)), game=game, lang=EVT_LANG) if install_ok else None
        return scripts[fid]

    for name in S_ORACLE_RIGS:
        try:
            key = ALIASES.get(name, name)
            if key in CHARACTERS:
                spec = CHARACTERS[key]
                ro = {"model": int(spec["model"]), "eye": int(spec["eye"]), "idle": spec["idle"], "walk": spec["walk"],
                      "run": spec["run"], "inactive": spec.get("inactive"), "src": "playerswap.CHARACTERS"}
            else:
                model = by_geo.get(RIG_GEO_NAMES[name])
                if model is None:
                    raise KeyError(f"no model named {RIG_GEO_NAMES[name]} in the kit's GEO table")
                anims = catalog.npc_anims(model) or {}
                eyes = []
                if not install_ok:
                    raise RuntimeError(f"not reached: the kit cache {KIT_CACHE_FILES} is missing (its eye byte is a stock "
                                       f"script's: run any ff9mapkit read once, by hand -- this bench never writes it)")
                for fid in EYE_FIELDS[name]:
                    data = script(fid)
                    eyes += setmodel_eyes(data, model) if data else []
                if not eyes:
                    raise RuntimeError(f"no SetModel({model}, eye) in the stock scripts of {EYE_FIELDS[name]}")
                ro = {"model": int(model), "eye": max(set(eyes), key=eyes.count), "idle": anims.get("stand"),
                      "walk": anims.get("walk"), "run": anims.get("run"), "inactive": None,
                      "src": f"{RIG_GEO_NAMES[name]} + catalog.npc_anims + SetModel in fields {EYE_FIELDS[name]}"}
            m = ro["model"]
            facts = models.get(m) or model_facts(game, m)
            if not facts.get("geo") or not facts.get("body"):
                raise RuntimeError(f"model {m}: geo {facts.get('geo_read')!r} vs the table's {facts.get('geo_table')!r}, "
                                   f"stems {facts.get('stems')}")
            models[m] = facts
            ro.update(name=name, geo=facts["geo"], body=facts["body"],
                      **{f"{k}_clip": ANIMATIONS.get(ro[k]) if ro.get(k) else None
                         for k in ("idle", "walk", "run", "inactive")})
            rigs[name] = ro
        except Exception as err:             # noqa: BLE001 - one rig that cannot be read is a named problem
            problems[f"rig {name}"] = f"{type(err).__name__}: {str(err)[:240]}"
    # the frame counts: each rig's idle and break clip, and the conductors' source clips (Zidane's own), off p0data5
    sources = {}
    try:
        pairs = [(ro["idle"], ro["model"]) for ro in rigs.values()] + [(a, BW.PLAIN_ZIDANE_MODEL) for a, _n in
                                                                       SOURCE_CLIPS.values()]
        pairs += [(ro["inactive"], ro["model"]) for ro in rigs.values() if ro.get("inactive")]
        frames = clip_frames(game, pairs)
        for ro in rigs.values():
            ro["idle_frames"] = frames.get((ro["idle"], ro["model"]))
            ro["inactive_frames"] = frames.get((ro["inactive"], ro["model"])) if ro.get("inactive") else None
        for k, (anim, n) in SOURCE_CLIPS.items():
            sources[k] = frames.get((anim, BW.PLAIN_ZIDANE_MODEL))
            if sources[k] != n:
                problems[f"source {k}"] = f"clip {anim} reads {sources[k]} frames off p0data5 (the contract says {n})"
    except Exception as err:                 # noqa: BLE001
        problems["frames"] = f"the p0data5 read raised {type(err).__name__}: {str(err)[:200]}"
    # the cross-checks: the twin's row (pinned to the census and the patch) and the census itself
    census, cwhy = _census_rows()
    if census is None:
        problems["census"] = cwhy
    for name, ro in rigs.items():
        row = BW.rig_row(BW.NAME_TO_RIG.get(name))
        if row is None:
            problems[f"twin {name}"] = "no rig row for this name in battlewire.NAME_TO_RIG"
            continue
        diff = [f"{k} {row[k]} vs {ro[k]}" for k in ("model", "eye") if row[k] != ro[k]]
        diff += [f"{k} clip {ANIMATIONS.get(row[k])!r} vs {ro.get(k + '_clip')!r}" for k in ("idle", "walk", "run")
                 if ANIMATIONS.get(row[k]) != ro.get(k + "_clip")]
        if diff:
            problems[f"twin {name}"] = "the twin's rig row disagrees with the oracle: " + ", ".join(diff)
        crow = (census or {}).get(name)
        if crow is not None and (crow["model"], crow["eye"]) != (ro["model"], ro["eye"]):
            problems[f"census {name}"] = (f"rigs_8_11.json model {crow['model']} eye {crow['eye']} vs the oracle's "
                                          f"{ro['model']} / {ro['eye']}")
    return {"rigs": rigs, "models": models, "clips": dict(ANIMATIONS), "sources": sources}, problems


def source_lists_read(game: Path, fields, regs: dict | None = None) -> tuple:
    """({field: n}, {key: why}) -- each field's SOURCE list as AttachDress reads it: the distinct clip names on the
    "GEO_MAIN_F0_ZDN:" line of the field's EventAnimation list (AnimationFactory.LoadAnimationUseInEvent's format), from
    the FIRST Memoria.ini FolderNames folder that ships it (commonasset/eventengine/eventanimation/EVT_<name>.txt.bytes),
    else the install's own p0data bundle (stock fields) -- 0 when the field has no list or no such line (a kit field
    deployed before ff9mapkit.eventanim ships none: 30602). READ-ONLY. The event name is :func:`field_eb`'s rule, never
    the kit's resolve_field (which BUILDS the field index into the install on a miss): the kit's id table for a stock
    field, else EVT_<the DictionaryPatch registration's name> (``regs``: {id: name}, Session.registered_fields), else
    deploy_field.py's sandbox name EVT_TEST<id>."""
    _kit()
    from ff9mapkit import extract as X
    game, out, problems, regs = Path(game), {}, {}, dict(regs or {})
    folders = X._mod_folders(game)
    rel = ("StreamingAssets", "assets", "resources", "commonasset", "eventengine", "eventanimation")
    for fid in fields:
        try:
            stock = X.ID_TO_EVT.get(int(fid))
            evt = stock or (f"EVT_{regs[int(fid)]}" if regs.get(int(fid)) else f"EVT_TEST{int(fid)}")
            text = None
            for folder in folders:
                pth = game.joinpath(folder, *rel, f"{evt}.txt.bytes")
                if pth.is_file():
                    text = pth.read_bytes().decode("utf-8", "replace")
                    break
            if text is None and stock and not kit_cache_missing(game):
                env = X._load_env(X._streaming_assets(game) / X._events_bundle(game))
                key = next((k for k in env.container if k.lower().endswith(f"eventanimation/{evt.lower()}.txt.bytes")),
                           None)
                if key is not None:
                    obj = env.container[key].read()
                    data = getattr(obj, "m_Script", None)
                    text = data if isinstance(data, str) else bytes(data or b"").decode("utf-8", "replace")
            elif text is None and stock:
                raise RuntimeError(f"not reached: a kit cache of {KIT_CACHE_FILES} is missing (a stock list is read "
                                   f"through the install -- run any ff9mapkit read once, by hand)")
            names = set()
            for ln in (text or "").replace("\r", "").split("\n"):
                if ln.startswith(SOURCE_GEO + ":"):
                    names |= {n for n in ln.split(":", 1)[1].split(",") if n}
            out[int(fid)] = len(names)
        except Exception as err:             # noqa: BLE001 - a field whose list cannot be read is a named problem
            problems[f"source list {fid}"] = f"{type(err).__name__}: {str(err)[:200]}"
    return out, problems


def seat_oracle(path: Path = SUB_PARTY_TOML) -> tuple:
    """((removes, adds) as CharacterIds, why) -- the COOPSUB seed's [party] block through the kit's own content.party
    (CharacterOldIndex -> CharacterId: OLD_INDEX_TO_ID); ((), ()) + why when it cannot be read."""
    import tomllib
    try:
        _kit()
        from ff9mapkit.content import party as P
        raw = tomllib.loads(Path(path).read_text(encoding="utf-8")).get("party") or {}
        rm = tuple(OLD_INDEX_TO_ID[P.resolve_member(m)] for m in raw.get("remove", ()))
        add = tuple(OLD_INDEX_TO_ID[P.resolve_member(m)] for m in raw.get("add", ()))
        return (rm, add), ""
    except (OSError, ValueError, KeyError, TypeError) as err:
        return ((), ()), f"{Path(path).name}: {type(err).__name__}: {str(err)[:160]}"


def seat_party(party, removes, adds) -> list | None:
    """(PURE) The party after a Main_Init that runs RemoveParty for each of ``removes`` (the seat holding that CharacterId
    cleared; none = a no-op -- EventEngine PARTYDELETE) and then B_PARTYADD for each of ``adds`` (the first EMPTY seat; one
    already seated is a no-op -- partyadd's partychk). None when ``party`` is not 4 slots."""
    if not isinstance(party, list) or len(party) != 4:
        return None
    out = list(party)
    for c in removes:
        k = next((i for i, m in enumerate(out) if m == c), None)
        if k is not None:
            out[k] = BW.PARTY_EMPTY
    for c in adds:
        if c in out:
            continue
        k = next((i for i, m in enumerate(out) if m == BW.PARTY_EMPTY), None)
        if k is not None:
            out[k] = c
    return out


def _s_oracle(g, ctx: dict) -> tuple:
    """The s140 legs' `oracle_extra` hook (:func:`s_oracle_read` on the run's install, leg G's model facts reused, plus the
    SOURCE lists of the fields whose rows judge them -- the stock field (S1) and 30602 (W1) -- and the COOPSUB seed's
    party ops) -- read ONCE per run: every s140 leg shares it, the first names its problems."""
    memo = ctx.get("_s_oracle_memo")
    if memo is not None:
        return memo, {}
    known = (_g_oracle_of(ctx) or {}).get("models")
    got, problems = s_oracle_read(Path(g.game_path), known)
    try:
        regs = g.registered_fields()[0]
    except (HarnessError, AttributeError, OSError):
        regs = {}
    lists, lprob = source_lists_read(Path(g.game_path), (ctx["stock"], DIO_FIELD), regs)
    got = dict(got, source_lists=lists)
    problems = dict(problems, **lprob)
    seat, swhy = seat_oracle()
    got["seat"] = {"remove": list(seat[0]), "add": list(seat[1])}
    if swhy or not seat[1]:
        problems["seat"] = swhy or f"{SUB_PARTY_TOML.name}: no [party] add"
    ctx["_s_oracle_memo"] = got
    return got, problems


def _s_oracle_of(ctx: dict) -> dict | None:
    extra = (ctx.get("oracle") or {}).get("extra") or {}
    for leg in ("S", "W", "X", "N", "T"):
        got = extra.get(leg)
        if isinstance(got, dict) and isinstance(got.get("rigs"), dict):
            return got
    # [ff9mapkit netsync s141] leg F alone reads the s140 oracle through its own hook (kept under its `s140` key)
    got = (extra.get("F") or {}).get("s140") if isinstance(extra.get("F"), dict) else None
    if isinstance(got, dict) and isinstance(got.get("rigs"), dict):
        return got
    return None


# ------------------------------------------------------------------------------------------------ leg F's offline oracle
_PC = None
_CENSUS_DOC: dict = {}


def _polish_census():
    """studies/battle-coop/dress-census/polish_census.py -- the census's PURE twins (expected_steps, light_color,
    ghost_light_color) and its MapConfigData reader (load_mcf) -- loaded once, off THIS checkout's kit."""
    global _PC
    if _PC is None:
        _kit()
        import importlib.util
        spec = importlib.util.spec_from_file_location("polish_census", POLISH_CENSUS_PY)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _PC = mod
    return _PC


def polish_census_doc(path: Path = POLISH_CENSUS_JSON) -> dict:
    """studies/battle-coop/dress-census/polish.json (read once): the install census leg F's footfall pairs come from."""
    key = str(path)
    if key not in _CENSUS_DOC:
        import json
        _CENSUS_DOC[key] = json.loads(Path(path).read_text(encoding="utf-8"))
    return _CENSUS_DOC[key]


def eb_footsteps(data: bytes) -> dict:
    """(PURE over a field script; the kit's .eb reader) The CONTROLLED entry's footstep ops as the script runs them --
    {"sid", "uid", "load": its Init's CHRFX (0x88) ops [(code, anim, frame, Arg4)] in script order, "reinit": the CHRFX ops
    of each function Main_Reinit (entry 0 tag 10) runs on the player (RunScriptAsync / RunScript / RunScriptSync whose uid
    is 250 -- the control alias -- or the entry's own) in call order, "reinit_tags", "problems"}. A computed operand is
    skipped and named. Field 250: Zidane_Init's twelve, and Main_Reinit's RunScriptAsync(0, 250, 13) -> Zidane_13's twelve."""
    _kit()
    from ff9mapkit.eb import disasm
    from ff9mapkit.eb.model import EbScript
    facts = eb_facts(data)
    out = {"sid": facts.get("sid"), "uid": facts.get("uid"), "load": [], "reinit": [], "reinit_tags": [],
           "problems": list(facts.get("problems") or [])}
    if facts.get("sid") is None:
        return out
    s = EbScript(data)
    ent = s.entries[facts["sid"]]

    def chrfx(f) -> list:
        ops = []
        for ins in disasm.iter_code(s.data, f.abs_start, f.abs_end):
            if ins.op != OP_CHRFX:
                continue
            args = [ins.imm(i) for i in range(4)]
            if any(a is None for a in args):
                out["problems"].append(f"entry {facts['sid']} tag {f.tag}: a computed CHRFX operand {ins.args}")
                continue
            ops.append(tuple(int(a) for a in args))
        return ops

    init = ent.func_by_tag(0)
    out["load"] = chrfx(init) if init is not None else []
    reinit = s.main.func_by_tag(10)
    uids = {sdf.CONTROL_UID, facts.get("uid")} - {None}
    if reinit is not None:
        for ins in disasm.iter_code(s.data, reinit.abs_start, reinit.abs_end):
            if ins.op in OP_RUN_SCRIPTS and ins.imm(1) in uids and ins.imm(2) is not None:
                out["reinit_tags"].append(int(ins.imm(2)))
                f = ent.func_by_tag(int(ins.imm(2)))
                if f is not None:
                    out["reinit"] += chrfx(f)
    return out


def hand_oracle_read(game: Path, model: int) -> dict:
    """A rig model's right-hand bones off the INSTALL's SKIN (READ-ONLY: the kit's models.extract.read_model through the
    census's polish_census.skin_hand -- the right arm's third skinned bone is the hand, the next bone on the arm its end,
    else the hand itself; NEVER labels_for, which sits one bone toward the shoulder on Steiner's and Amarant's arms):
    {"model", "geo", "hand", "hand_end", "end_name" ('bone%03d' -- geoAttach's parent node), "names" (every bone name),
    "source", "arm" (the skin's right arm, root to tip: [bone, skinned verts, rest x])}. A vertex-owning LEAF hand (Freya,
    Amarant, the moogle) lands both on the hand, the table's rule."""
    _kit()
    pc = _polish_census()
    from ff9mapkit.models import extract as MX
    md = MX.read_model(str(int(model)), game=game)
    sk = pc.skin_hand(md["bones"], md["meshes"])
    hand, end = sk["hand"], sk["end"]
    return {"model": int(model), "geo": md.get("geo"), "hand": hand, "hand_end": end,
            "end_name": BW.bone_name(end) if end is not None else None,
            "names": sorted(str(b["name"]) for b in md["bones"]), "source": "the skin (polish_census.skin_hand)",
            "arm": sk["arm"]}


def entry_chrfx(data: bytes, sid: int, tag: int) -> list | None:
    """(PURE over a field script; the kit's .eb reader) Entry ``sid``'s function ``tag``'s CHRFX (0x88) footstep ops (codes
    16-19) as (code, anim, frame, Arg4) in script order; None when there is no such function (a computed operand is
    skipped)."""
    _kit()
    from ff9mapkit.eb import disasm
    from ff9mapkit.eb.model import EbScript
    s = EbScript(data)
    if not (0 < sid < len(s.entries)) or s.entries[sid].empty:
        return None
    f = s.entries[sid].func_by_tag(tag)
    if f is None:
        return None
    ops = []
    for ins in disasm.iter_code(s.data, f.abs_start, f.abs_end):
        if ins.op != OP_CHRFX:
            continue
        args = [ins.imm(i) for i in range(4)]
        if any(a is None for a in args) or int(args[0]) not in BW.FOOTSTEP_CODES:
            continue
        ops.append(tuple(int(a) for a in args))
    return ops


def bench_player_steps(game: Path) -> tuple:
    """F2d's precondition, READ-ONLY: the bench field's player Init footstep registrations off the DEPLOYED 30606 .eb (the
    one the engine loads: :func:`_selfdress_field.deployed_eb`) -> (ops, where) or (None, why). A missing or unparseable
    deploy is the preflight's to name (S140-PF), never an oracle problem."""
    try:
        eb, where = sdf.deployed_eb(Path(game))
    except Exception as err:                 # noqa: BLE001 - an unreadable deploy is a reason
        return None, f"the deployed 30606 .eb read raised {type(err).__name__}: {str(err)[:200]}"
    if eb is None:
        return None, where
    try:
        ops = entry_chrfx(eb, sdf.PLAYER_SID, 0)
    except Exception as err:                 # noqa: BLE001
        return None, f"{where}: does not parse ({type(err).__name__}: {str(err)[:160]})"
    if ops is None:
        return None, f"{where}: no player entry {sdf.PLAYER_SID} Init"
    return ops, where


def bench_table_writers(game: Path) -> tuple:
    """F2d's OTHER precondition, READ-ONLY (rbench-1): the footstep table the engine's empty-table guard (and stock
    DeleteChar) reads is the GLOBAL one -- charSoundUse counts EVERY body's records -- while F2d's oracle replays the
    player Init's registrations alone, so the player Init must be the table's ONLY writer. -> (strays, where):
    :func:`_selfdress_field.f2d_table_strays` over the DEPLOYED 30606 .eb ([] = it holds), or (None, why) when the deploy
    cannot be read."""
    try:
        eb, where = sdf.deployed_eb(Path(game))
    except Exception as err:                 # noqa: BLE001 - an unreadable deploy is a reason
        return None, f"the deployed 30606 .eb read raised {type(err).__name__}: {str(err)[:200]}"
    if eb is None:
        return None, where
    try:
        return sdf.f2d_table_strays(sdf.facts(eb)), where
    except Exception as err:                 # noqa: BLE001
        return None, f"{where}: does not parse ({type(err).__name__}: {str(err)[:160]})"


def stock_f2d_form(game: Path, regs: dict | None = None, install_ok: bool = True) -> tuple:
    """The F2d op's STOCK form, READ-ONLY: field 2930's own `.eb` (the one the engine loads) holds RunModelCode(19, 190, 4,
    0) in an entry's Init (Zidane_Init, test2_790.txt:515) -> (True, where) or (False, why)."""
    _kit()
    from ff9mapkit.eb.model import EbScript
    data, src = field_eb(Path(game), sdf.F2D_FIELD, reg_name=(regs or {}).get(sdf.F2D_FIELD), install_ok=install_ok)
    if data is None:
        return False, src
    s = EbScript(data)
    for e in s.entries[1:]:
        if not e.empty and tuple(sdf.F2D_OP) in (entry_chrfx(data, e.index, 0) or []):
            return True, f"{src}: entry {e.index}'s Init"
    return False, f"{src}: no Init runs RunModelCode{tuple(sdf.F2D_OP)} (the F2d op is not field {sdf.F2D_FIELD}'s)"


def _census_rig(doc: dict, name: str) -> dict | None:
    """polish.json `b_steps.rigs` row for rig ``name`` (keyed "<index> <name>")."""
    return next((v for k, v in ((doc.get("b_steps") or {}).get("rigs") or {}).items() if k.split(" ", 1)[-1] == name), None)


def f_oracle_read(game: Path, stock: int, so: dict | None, regs: dict | None = None) -> tuple:
    """Leg F's OFFLINE oracle (S138-OR, read once): ({"field", "ops", "rigs", "steps", "steps_off", "reinit", "light",
    "ghost_light", "floors_at", "src_model", "hands", "f2d", "f2d_why"}, {key: why}) -- every expected value read through
    the KIT'S readers
    and the install census, never the engine's tables:
      * ``ops``: the stock field's player footstep ops (:func:`eb_footsteps` over the `.eb` the engine loads -- :func:`field_eb`);
      * ``rigs``: each judged rig's model off the s140 oracle ``so`` (the kit's tables), its walk / run ids, footfall pairs
        and step sound off the census (polish.json `b_steps`: the ids stock REGISTERS footsteps on and the modal
        RunModelCode(16) frames per clip over the 817 stock scripts -- -1 / -1 for a rig with none: the moogle, Cinna, O1),
        the ids' clip NAMES cross-checked against the kit's;
      * ``steps`` / ``steps_off`` / ``reinit``: one load's replay per rig (the census twin polish_census.expected_steps:
        MapFootstep on a dressed body -- Zidane UNDRESSED, F3's control --, then stock FF9Snd's table) with the polish on /
        off, and the warm return's (Main_Reinit's ops into the table the load reset cleared);
      * ``light`` / ``ghost_light``: per walkmesh floor (and 255: no floor -- the default light), the census's light_color
        / ghost_light_color of the F rig's model over the field's own MapConfigData (polish_census.load_mcf), dressed
        (source row 98) with the polish on / off -- keyed by the floor the ENGINE names (`light_floor`); ``floors_at`` the
        kit's stock walkmesh lookup (x, z) -> floors (reported beside it); ``src_model`` the source body (Zidane's 98);
      * ``hands``: F8's rig hand off the install's skin (:func:`hand_oracle_read`), cross-checked against the census's
        e_hands (the skin's pair AND stock's own AttachObject on the body agreeing);
      * ``f2d``: the bench field's player registrations (:func:`bench_player_steps`, the DEPLOYED .eb) and the F2d op, its
        stock form (:func:`stock_f2d_form`), replayed for the moogle through the census twin WITH the guard -- ``want``
        {steps, steps_dropped, steps_passed} the op's deltas; None with ``f2d_why`` when the deploy cannot be read (the
        preflight's to name) or F2d's precondition does not hold (:func:`bench_table_writers`: a footstep writer besides
        the player Init -- the problem `f2d table`, F2d "not reached", never a WRONG on a correct engine).
    The kit cache missing (a read that would WRITE into the install) leaves the install half out, named "not reached".
    CROSS-CHECKS, each disagreement a named problem: the census's clip ids against the kit's, the twin's rig row
    (battlewire.RIGS: pairs, sound, hand bones), field 250's ops and mapconfig against battlewire.FIELD250_STEPS /
    FIELD250_MCF."""
    _kit()
    pc = _polish_census()
    from ff9mapkit import extract as X
    game, stock, problems = Path(game), int(stock), {}
    out = {"field": stock, "ops": None, "rigs": {}, "steps": {}, "steps_off": {}, "reinit": {}, "light": None,
           "ghost_light": None, "floors_at": None, "src_model": None, "hands": {}, "f2d": None, "f2d_why": None}
    install_ok = not kit_cache_missing(game)
    # (a) the stock field's player footstep ops, off the .eb the engine loads
    try:
        data, src = field_eb(game, stock, reg_name=(regs or {}).get(stock), install_ok=install_ok)
        if data is None:
            problems["ops"] = src
        else:
            fs = eb_footsteps(data)
            out["ops"] = {"load": fs["load"], "reinit": fs["reinit"], "reinit_tags": fs["reinit_tags"], "sid": fs["sid"],
                          "src": src}
            if fs["problems"]:
                problems["ops eb"] = f"{src}: {fs['problems']}"
            if not any(op[0] in BW.FOOTSTEP_CODES for op in fs["load"]):
                problems["ops"] = (f"{src}: the controlled entry {fs['sid']} runs no footstep op at a load (leg F needs a "
                                   f"field whose player registers footsteps: 250)")
            if stock == STOCK_FIELD and (tuple(fs["load"]) != BW.FIELD250_STEPS or tuple(fs["reinit"]) != BW.FIELD250_STEPS):
                problems["twin ops"] = (f"field {stock}'s footstep ops {fs['load']} / reinit {fs['reinit']} vs "
                                        f"battlewire.FIELD250_STEPS {list(BW.FIELD250_STEPS)}")
    except Exception as err:                 # noqa: BLE001 - one part that cannot be read is a named problem
        problems["ops"] = f"the .eb read raised {type(err).__name__}: {str(err)[:200]}"
    # (b) the rigs: the census's walk / run ids (the ids stock REGISTERS footsteps on) and pairs, the model and the clip
    # NAMES off the s140 oracle (the kit's tables: an alias id of the same clip -- the moogle's 2926 / 2927 -- is the same
    # clip), the twin's row as a cross-check
    try:
        from ff9mapkit._animdb_all import ANIMATIONS
        doc = polish_census_doc()
        for name in dict.fromkeys(F_STEP_RIGS + (F8_RIG, F_DROP)):
            ro, c = ((so or {}).get("rigs") or {}).get(name), _census_rig(doc, name)
            if ro is None or c is None:
                problems[f"rig {name}"] = (f"no {'s140 oracle row' if ro is None else 'census row'} for {name} "
                                           f"(the s140 oracle's problems name why)")
                continue
            cen = c["census"]
            r = {"name": name, "model": ro["model"], "walk": int(c["walk"]["id"]), "run": int(c["run"]["id"]),
                 "walk_step_a": int(cen["walk_pair"][0]), "walk_step_b": int(cen["walk_pair"][1]),
                 "run_step_a": int(cen["run_pair"][0]), "run_step_b": int(cen["run_pair"][1]),
                 "step_sound": int(cen["step_sound"])}
            names = (ANIMATIONS.get(r["walk"]), ANIMATIONS.get(r["run"]))
            if names != (ANIMATIONS.get(ro["walk"]), ANIMATIONS.get(ro["run"])) or None in names:
                problems[f"census {name}"] = (f"the census's walk / run clips {r['walk']} / {r['run']} {names} vs the "
                                              f"kit's {ro['walk']} / {ro['run']} ({ANIMATIONS.get(ro['walk'])}, "
                                              f"{ANIMATIONS.get(ro['run'])})")
            tw = BW.rig_row(BW.NAME_TO_RIG[name])
            diff = [f"{k} {tw[k]} vs {r[k]}" for k in ("walk_step_a", "walk_step_b", "run_step_a", "run_step_b",
                                                       "step_sound") if tw[k] != r[k]]
            if diff:
                problems[f"twin {name}"] = "the twin's rig row disagrees with the census: " + ", ".join(diff)
            out["rigs"][name] = r
    except Exception as err:                 # noqa: BLE001
        problems["census"] = f"{POLISH_CENSUS_JSON.name}: {type(err).__name__}: {str(err)[:200]}"
    # (c) the expected tables per rig, one load each (the census twin over the field's own ops)
    z = out["rigs"].get(F_ZIDANE)
    if out["ops"] is not None and z is not None:
        zid = {k: z[k] for k in ("walk", "run", "walk_step_a", "walk_step_b", "run_step_a", "run_step_b")}
        keep = ("steps", "steps_dropped", "steps_passed")
        for name, r in out["rigs"].items():
            dressed = name != F_ZIDANE
            for key, ops, polish in (("steps", "load", True), ("steps_off", "load", False), ("reinit", "reinit", True)):
                got = pc.expected_steps(r, list(out["ops"][ops]), polish=polish, dressed=dressed, zidane=zid)
                out[key][name] = {k: got[k] for k in keep}
                if got["faults"]:
                    problems[f"faults {name} {key}"] = f"the replay throws in stock: {got['faults'][:2]}"
    out["src_model"] = z["model"] if z is not None else None
    # (d) the light: the field's MapConfigData and walkmesh (both through the install: the kit cache must exist)
    fr = out["rigs"].get(F_RIG)
    try:
        if not install_ok:
            raise RuntimeError(f"not reached: the kit cache {KIT_CACHE_FILES} is missing from the install (the "
                               f"mapconfig and walkmesh reads would WRITE it -- run any ff9mapkit read once, by hand)")
        mcf = pc.load_mcf(stock, game)
        if mcf is None:
            raise RuntimeError(f"field {stock} has no MapConfigData (a kit field: the service returns early -- F4 needs a "
                               f"stock field's)")
        if stock == STOCK_FIELD:
            chars = tuple((c.geo, c.shadow_i, c.shadow_r, tuple(c.clr[:3])) for c in mcf.chars[:mcf.char_use])
            if chars != tuple((g_, si, sr, tuple(clr)) for g_, si, sr, clr in BW.FIELD250_MCF["chars"]):
                problems["twin mcf"] = f"field {stock}'s mapconfig rows {chars} vs battlewire.FIELD250_MCF"
        wm = X.stock_walkmesh(stock, game=game)
        if fr is None or z is None:
            raise RuntimeError("no rig row for the light (see the rig problems)")
        src_m, model = z["model"], fr["model"]
        light, ghost = {}, {}
        for f in list(range(len(wm.floors))) + [255]:          # 255: no floor (fldmcf's default light)
            light[f] = {k: {kk: pc.light_color(mcf, model, f, src_m, pol)[kk] for kk in ("row", "rgb")}
                        for k, pol in (("s141", True), ("off", False))}
            ghost[f] = {k: dict(pc.ghost_light_color(mcf, model, model, f, src_m, pol)) for k, pol in (("s141", True),
                                                                                                     ("off", False))}
        out.update(light=light, ghost_light=ghost, floors_at=wm.floors_at)
    except Exception as err:                 # noqa: BLE001
        problems["light"] = f"{type(err).__name__}: {str(err)[:240]}"
    # (e) F8's rig skeleton: the bone the prop must land on, by NAME
    r8 = out["rigs"].get(F8_RIG)
    try:
        if r8 is None:
            raise RuntimeError(f"no rig row for {F8_RIG}")
        hand = hand_oracle_read(game, r8["model"])
        out["hands"][F8_RIG] = hand
        tw = BW.rig_row(BW.NAME_TO_RIG[F8_RIG])
        if (tw["hand_bone"], tw["hand_bone_end"]) != (hand["hand"], hand["hand_end"]):
            problems[f"twin hands {F8_RIG}"] = (f"the twin's hand bones {tw['hand_bone']} / {tw['hand_bone_end']} vs the "
                                                f"skin's {hand['hand']} / {hand['hand_end']} ({hand['source']})")
        eh = next((v for v in (polish_census_doc().get("e_hands") or {}).values()
                   if isinstance(v, dict) and v.get("model") == int(r8["model"])), None)
        if eh is None or tuple(eh.get("expected") or ()) != (hand["hand"], hand["hand_end"]) or \
                not (eh.get("stock") or {}).get("agrees"):
            problems[f"census hands {F8_RIG}"] = (
                f"the census's e_hands for {F8_RIG} ({None if eh is None else eh.get('expected')}, stock agrees "
                f"{None if eh is None else (eh.get('stock') or {}).get('agrees')}) vs the skin's {hand['hand']} / "
                f"{hand['hand_end']}")
        if hand["hand_end"] == F8_BONE or hand["end_name"] not in hand["names"]:
            problems[f"hands {F8_RIG}"] = (f"{F8_RIG}'s R_hand_end {hand['hand_end']} ({hand['end_name']!r}) cannot "
                                           f"discriminate (want a bone other than {F8_BONE}, on the skeleton)")
    except Exception as err:                 # noqa: BLE001
        problems[f"hands {F8_RIG}"] = f"{type(err).__name__}: {str(err)[:200]}"
    # (f) F2d: the bench field's player registrations (the DEPLOYED .eb) and field 2930's op (its stock form), replayed for
    # the drop rig through the census twin WITH the engine's guard: one load, then the op -- the deltas F2d judges
    mo = out["rigs"].get(F_DROP)
    try:
        if mo is None or z is None:
            raise RuntimeError(f"no rig row for {F_DROP} / {F_ZIDANE} (see the rig problems)")
        load, where = bench_player_steps(game)
        strays, swhere = bench_table_writers(game) if load is not None else ([], where)
        if load is None:
            out["f2d_why"] = f"the bench field's player registrations: {where}"
        elif strays is None or strays:
            problems["f2d table"] = swhere if strays is None else f"{swhere}: {sdf.f2d_table_why(strays)}"
            out["f2d_why"] = f"F2d's precondition does not hold (the oracle's `f2d table`): {problems['f2d table'][:200]}"
        else:
            found, fsrc = stock_f2d_form(game, regs, install_ok)
            if not found:
                problems["f2d stock"] = fsrc
            if tuple(tuple(o) for o in load) != BW.KIT_PLAYER_STEPS:
                problems["twin kit steps"] = (f"{where}: the player Init's footstep ops {load} vs battlewire.KIT_PLAYER_STEPS "
                                              f"{list(BW.KIT_PLAYER_STEPS)} (the stand-in's)")
            zid = {k: z[k] for k in ("walk", "run", "walk_step_a", "walk_step_b", "run_step_a", "run_step_b")}
            ops = [list(o) for o in load]
            base = pc.expected_steps(mo, ops, polish=True, dressed=True, zidane=zid, guard=True)
            full = pc.expected_steps(mo, ops + [list(sdf.F2D_OP)], polish=True, dressed=True, zidane=zid, guard=True)
            if full["faults"]:
                problems["f2d replay"] = f"the guarded replay still throws: {full['faults'][:2]}"
            out["f2d"] = {"load": ops, "op": list(sdf.F2D_OP), "src": where, "stock": fsrc,
                          "want": {"steps": full["steps"], "steps_dropped": full["steps_dropped"] - base["steps_dropped"],
                                   "steps_passed": full["steps_passed"] - base["steps_passed"]}}
    except Exception as err:                 # noqa: BLE001
        problems["f2d"] = f"{type(err).__name__}: {str(err)[:200]}"
    return out, problems


#: the s140 oracle's problem keys leg F reads through (the rows of its own rigs, the 8-11 census, a raised hook) -- every
#: other s140 problem (the COOPSUB seat, the 30602 source lists, another rig's p0data5 frames) is an s140 leg's to name
F_S140_PROBLEM_KEYS = ("census", "hook")


def _f_s140_problems(sprob: dict, legs) -> dict:
    """The s140 oracle's problems leg F names (``s140 <key>``): none when an s140 leg is selected (it named them first --
    :func:`_s_oracle` memoises the read and hands its problems to the FIRST caller only), else only those about the rigs leg
    F reads (rig / twin / census rows of F_STEP_RIGS, F8_RIG) and :data:`F_S140_PROBLEM_KEYS`."""
    if any(leg in legs for leg in ("S", "W", "X", "N", "T")):
        return {}
    mine = set(F_STEP_RIGS + (F8_RIG, F_DROP))
    return {f"s140 {k}": v for k, v in (sprob or {}).items()
            if k in F_S140_PROBLEM_KEYS or str(k).split(" ", 1)[-1] in mine and str(k).split(" ", 1)[0] in ("rig", "twin",
                                                                                                         "census")}


def _f_oracle(g, ctx: dict) -> tuple:
    """Leg F's `oracle_extra` hook: :func:`f_oracle_read` on the run's install and stock field, over the s140 oracle (the
    rigs' models and clip ids -- read once per run: :func:`_s_oracle` memoises it). Of the s140 oracle's problems it names
    only :func:`_f_s140_problems`' -- those about the rigs leg F reads, and only when no s140 leg named them first."""
    so, sprob = _s_oracle(g, ctx)
    try:
        regs = g.registered_fields()[0]
    except (HarnessError, AttributeError, OSError):
        regs = {}
    got, problems = f_oracle_read(Path(g.game_path), ctx["stock"], so, regs)
    got["s140"] = so
    return got, dict(_f_s140_problems(sprob, ctx.get("legs") or ()), **problems)


def _f_oracle_of(ctx: dict) -> tuple:
    """(leg F's oracle, None) or (None, why)."""
    got = ((ctx.get("oracle") or {}).get("extra") or {}).get("F")
    if isinstance(got, dict) and isinstance(got.get("rigs"), dict):
        return got, None
    return None, f"no s141 oracle ({(ctx.get('oracle') or {}).get('problems')})"


def _f_part(fo: dict, ctx: dict, *parts) -> str | None:
    """None when every oracle part a row needs is there, else its "not reached" why (the oracle's problems named)."""
    missing = [p for p in parts if not fo.get(p)]
    if not missing:
        return None
    probs = {k: v for k, v in ((ctx.get("oracle") or {}).get("problems") or {}).items() if str(k).startswith("F.")}
    return f"no s141 oracle {missing} ({probs})"


# ------------------------------------------------------------------------------------------------ leg G's steps
G_STOCK_CHECKS = ("S139-G0", "S139-G4", "S139-G6", "S139-G3a")
G_SEEDED_CHECKS = ("S139-G1", "S139-G2", "S139-G3", "S139-G3c", "S139-G3m", "S139-G3d", "S139-G5", "S139-G7a", "S139-G7b",
                   "S139-G7c", "S139-G7d", "S139-G7e", "S139-G8")


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
                            clips=oracle["clips"], rules=stage_rules(ctx.get("stage")))
    return _labelled(label, ok, detail)


def _g_stock(g, led: cb.Ledger, ctx: dict) -> None:
    """Field 250, before the seed (after leg I's rest window): G0 -- the baseline, every lever off --, G4 and G6 (the proof
    block's verdicts: it ran at S0), then, under COOP_DRESS_CAL=rule-s138, the calibration lever; then G3a while the
    New-Game party's slot 1 is EMPTY (the real party read: no `empty` lever); every lever cleared after it (under the
    calibration lever, `rule s138` pulled again: no leg-I read after it reads the ghost)."""
    field, gx = ctx["stock"], _g_ctx(ctx)
    oracle = _g_oracle_of(ctx)
    rules = stage_rules(ctx.get("stage"))              # [ff9mapkit netsync s140] the PROBED engine's rows
    led.check("S139-G4", *judge_codec(_dress(g.state), cb.log_lines(g), rules))
    led.check("S139-G6", *judge_idle_frames(_dress(g.state), (oracle or {}).get("idle_frames"), rules))
    if _settle(g, field) is None:
        led.unreached(("S139-G0", "S139-G3a"), f"field {field} never came up with the player free")
        return
    if oracle is None:
        led.unreached(("S139-G0", "S139-G3a"), f"no leg-G oracle ({(ctx.get('oracle') or {}).get('problems')})")
        return
    samples = on_field_prefix(cb.hold_for(g, GHOST_SETTLE_S), field)
    ok, why = judge_baseline(samples, ghost_as=gx["ghost_as"], models=oracle["models"], clips=oracle["clips"], rules=rules)
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
                                   models=oracle["models"], clips=oracle["clips"], rules=stage_rules(ctx.get("stage")))
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
    worn_ok, worn = judge_worn(samples, levers=lv, ghost_as=gx["ghost_as"], models=oracle["models"], clips=oracle["clips"],
                               rules=stage_rules(ctx.get("stage")))
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
        led.unreached(("S139-G1", "S139-G5", "S139-G7a", "S139-G7b", "S139-G7c", "S139-G7d", "S139-G7e"),
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
    sec_ok, sec_why = judge_section_line(cb.log_lines(g), gx["ghost_as"], stage_rules(ctx.get("stage")))
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
                                            clips=oracle["clips"], rules=stage_rules(ctx.get("stage")))
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
                          ("S139-G7c", (BW.PLAIN_ZIDANE_MODEL,)), ("S139-G7d", (G_WIRE_UNRIGGED,)),
                          ("S139-G7e", (G_WIRE_SUB,))):          # [ff9mapkit netsync s140] the 8-11 rows, by stage
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


# ------------------------------------------------------------------------------------------------ the s140 legs' steps
_NR = "not reached: "


def _s_ctx(ctx: dict) -> dict:
    """The s140 legs' run state: the calibration lever this run pulls (COOP_DRESS_CAL, when it names an s140 lever), the
    levers the bench holds."""
    if "s140" not in ctx:
        mode = ctx.get("cal_mode") if ctx.get("calibrate") else None
        ctx["s140"] = {"lever": mode if mode in S140_LEVER_MODES else None, "spec": None, "gate_off": False,
                       "law_off": [], "watched": False}
    return ctx["s140"]


def _s_send(g, ctx: dict, *op) -> str | None:
    """One `selfdress` op through the driver (refused BEFORE the step where the engine lacks it: s139 has no `self` / `gate`
    / `law`, s138 no `selfdress`), the levers the bench holds tracked -- leg G's too (`clear` releases them all, `empty` is
    G's). The refusal's text, or None."""
    words = [str(a) for a in op]
    if words[0] in ("ghost", "empty", "wire", "rule", "clear"):
        why = _g_send(g, ctx, tuple(words))
    else:
        ok, w = cb.try_ns(g, "selfdress", *words)
        why = None if ok else f"`selfdress {' '.join(words)}` refused: {w}"
    if why is not None:
        return why
    sx = _s_ctx(ctx)
    if words[0] == "clear":
        sx.update(spec=None, gate_off=False, law_off=[])
    elif words[0] == "self":
        sx["spec"] = " ".join(words[1:])
    elif words[0] == "gate":
        sx["gate_off"] = words[1] == "0"
    elif words[0] == "law":
        laws = [w for w in sx["law_off"] if w != words[1]]
        sx["law_off"] = laws + ([words[1]] if words[2] == "off" else [])
    return None


def _f_ctx(ctx: dict) -> dict:
    """[ff9mapkit netsync s141] Leg F's run state: the calibration lever this run pulls (COOP_DRESS_CAL=polish-off)."""
    if "s141" not in ctx:
        mode = ctx.get("cal_mode") if ctx.get("calibrate") else None
        ctx["s141"] = {"lever": mode if mode in S141_LEVER_PREDICTED else None}
    return ctx["s141"]


def _lever_ops(ctx: dict, leg: str) -> list:
    """The calibration lever ops a load of ``leg`` pulls again after its `clear`: an s140 row's (`gate 0` / `law <name>
    off`), or -- [ff9mapkit netsync s141] -- leg F's own (`polish off`), never another leg's (leg F has no row for the s140
    levers and stays green under each; the s140 rows none for `polish`)."""
    if leg == "F":
        return [("polish", "off")] if _f_ctx(ctx)["lever"] == CAL_POLISH_OFF else []
    lever = _s_ctx(ctx)["lever"]
    if lever == CAL_GATE_0:
        return [("gate", 0)]
    if lever in CAL_LAWS:
        return [("law", CAL_LAWS[lever], "off")]
    return []


def _s_prepare(g, ctx: dict, spec: str, *extra, leg: str = "s140") -> tuple:
    """Before a dress load: `clear` (every lever, leg G's included), then the run's calibration lever pulled again (an s140
    row's `gate 0` / `law <name> off`; [ff9mapkit netsync s141] leg F's `polish off`), the dress spec -- under
    COOP_DRESS_CAL=self-off an s140 row sends `self off` IN ITS PLACE --, then the ``extra`` ops. -> (the spec sent, the
    first refusal or None, the publish read right BEFORE the `self` op, the publish read BEFORE the `clear` -- THE TEARDOWN
    LAW's input: no op may undress the live body)."""
    pre_clear = g.state
    why = _s_send(g, ctx, "clear")
    for op in _lever_ops(ctx, leg):
        if why is None:
            why = _s_send(g, ctx, *op)
    sent = "off" if leg != "F" and _s_ctx(ctx)["lever"] == CAL_SELF_OFF else str(spec)
    pre = g.state
    if why is None:
        why = _s_send(g, ctx, "self", *sent.split())
    for op in extra:
        if why is None:
            why = _s_send(g, ctx, *op)
    return sent, why, pre, pre_clear


def _s_watch(g, ctx: dict) -> None:
    """The bench field's bits published in every state (once a run: `reset` clears the watch list)."""
    sx = _s_ctx(ctx)
    if not sx["watched"]:
        try:
            g.watch(*sdf.ALL_FLAGS)
            sx["watched"] = True
        except (HarnessError, AttributeError, ValueError) as err:
            g.note(f"watch of the bench field's bits refused ({str(err)[:160]})")


def _s_load(g, ctx: dict, field: int, spec: str, *extra, leg: str = "s140") -> dict:
    """ONE DRESS LOAD: :func:`_s_prepare`, then a warp to ``field`` (the stock field at entrance 0; on the bench field its
    READY bit cleared first and waited for, the gate bits read 0) and the arrival settled -> {"st": the LAST free publish of
    DRESS_READ_S (None = not reached), "window", "before": the publish before the warp, "lines": Memoria.log since it,
    "sent", "label", "why"}. The `self` spec arms at THIS load (ArmBench runs at the field load, never at the op).
    [ff9mapkit netsync s141] ``leg`` "F": leg F's lever (`polish off`) in place of the s140 rows', named in the label."""
    sent, why, pre, pre_clear = _s_prepare(g, ctx, spec, *extra, leg=leg)
    ops = ([" ".join(str(a) for a in op) for op in _lever_ops(ctx, leg)] if leg == "F" else []) + [f"self {sent}"] + [
        " ".join(str(a) for a in op) for op in extra]
    label = " + ".join(f"`selfdress {o}`" for o in ops) + f" + a warp to {field}"
    out = {"st": None, "window": [], "before": None, "lines": [], "sent": sent, "label": label, "why": None,
           "op": None, "clear": None}
    if why is not None:
        out["why"] = why
        return out
    # the op's own publish (its `bench_self` AS SET), held a moment: the ARM must not have moved yet -- it moves at the LOAD
    post = cb.poll(g, lambda s: (_self(s) or {}).get("bench_self") == sent, OP_SETTLE_S + 4.0, f"`self {sent}` published")
    if post is not None:
        post = (cb.hold_for(g, OP_SETTLE_S) or [post])[-1]
    out["op"] = (pre, post)
    out["clear"] = (pre_clear, post)                 # the live body across `clear` + the ops (THE TEARDOWN LAW)
    out["before"] = g.state
    at = cb.mark(g)
    try:
        if field == SELF_FIELD:
            _s_watch(g, ctx)
            g.flag(sdf.READY, False)
        g.warp(field, entrance=STOCK_ENTRANCE if field == ctx["stock"] else None)
    except HarnessError as err:
        out["why"] = f"the warp to {field} failed: {str(err)[:200]}"
        return out
    if field == SELF_FIELD:
        st = cb.poll(g, lambda s: s.flag(sdf.READY) is True and free_on(s, field), COND_READY_S,
                     f"field {field}'s caller READY with control")
        if st is None:
            out["why"] = (f"field {field}'s caller never set READY with control (READY {g.state.flag(sdf.READY)!r}, "
                          f"field {g.state.field_id})")
            return out
        gates = (st.flag(sdf.TWIN_GATE), st.flag(sdf.LATE_GATE))
        if gates != (False, False):
            out["why"] = f"the bench field's gate bits {sdf.TWIN_GATE} / {sdf.LATE_GATE} read {gates} (nothing may set them)"
            return out
    elif _settle(g, field) is None:
        out["why"] = f"field {field} never came up with the player free (field {g.state.field_id})"
        return out
    window = on_field_prefix(cb.hold_for(g, DRESS_READ_S), field)
    if not window:
        out["why"] = f"no free publish on field {field} after the arrival"
        return out
    out.update(st=window[-1], window=window, lines=cb.new(g, at))
    return out


def _s_rig(ctx: dict, name: str):
    """(the oracle's row for rig ``name``, None) or (None, why) -- every s140 value comes from it."""
    so = _s_oracle_of(ctx)
    if so is None:
        return None, f"no s140 oracle ({(ctx.get('oracle') or {}).get('problems')})"
    ro = so["rigs"].get(name)
    if ro is None:
        return None, f"no s140 oracle for rig {name!r} ({(ctx.get('oracle') or {}).get('problems')})"
    return ro, None


def _rig_index(name: str) -> int:
    return BW.NAME_TO_RIG[name]


def _bench_pre(ctx: dict, field: int) -> str | None:
    """Why ``field``'s rows cannot run (None = they can): not registered (S138-PRE), or -- the bench field -- its preflight
    failed CLOSED (S140-PF)."""
    if field in set(ctx.get("missing") or ()):
        return f"field {field} is not registered (S138-PRE)"
    if field == SELF_FIELD:
        pf = ctx.get("pf")
        if pf is None:
            return "the bench field's preflight did not run"
        if not pf[0]:
            return f"the bench field's preflight failed CLOSED: {pf[1]}"
    return None


def _s_self(g, led: cb.Ledger, ctx: dict) -> None:
    """[ff9mapkit netsync s140] The "self" phase (after "bench"), on the stock field (every leg-G lever released by then):
    S1 (`self freya` + a re-warp) -> S2 (leg I's walk probe, then the rest window) with S5 off that rest window -> S3
    (`self auto 2` + `empty 2`) -> S6 (`self blank`) -> S4 (`self off`), then every lever released (`clear`)."""
    field = ctx["stock"]
    fr, why = _s_rig(ctx, S_RIG)
    if fr is None:
        led.unreached(S_CHECKS, why)
        return
    rig = _rig_index(S_RIG)
    ld = _s_load(g, ctx, field, S_RIG)
    if ld["st"] is None:
        led.unreached(S_CHECKS, f"{ld['label']}: {ld['why']}")
        return
    src_list = ((_s_oracle_of(ctx) or {}).get("source_lists") or {}).get(field)
    led.check("S140-S1", *_labelled(ld["label"], *judge_self_dress(ld["st"], fr, rig=rig, before=ld["before"],
                                                                   lines=ld["lines"], field=field,
                                                                   attach={"src_list": src_list}, op=ld["op"],
                                                                   spec=ld["sent"])))
    # S2: the dressed body moving (judged per field tick) and at rest; S5 off the same rest window
    walk = _walk_probe(g, field)
    if walk["left"]:
        moving = (False, f"not reached: the probe hold {walk['tried'][-1]!r} was TAKEN OVER ({walk['why']})")
        _recover(g, field)
    elif walk["dir"] is None:
        moving = (False, f"not reached: {walk['why']} ({walk['tried']})")
    else:
        moving = judge_walk(walk["samples"], {"walk": fr["walk"], "run": fr["run"], "geo": fr["geo"]})
    if _settle(g, field) is None:
        led.unreached(("S140-S2", "S140-S5"), f"field {field} never came back with the player free")
    else:
        rest = on_field_prefix(cb.hold_for(g, REST_S), field)
        rest_ok, rest_why = judge_rest_named(rest, fr)
        geo_ok, geo_why = judge_geo_throughout(on_field_prefix(list(walk.get("samples") or []), field) + rest,
                                               fr["geo"])
        nr = _NR if moving[1].startswith(_NR) else ""
        led.check("S140-S2", moving[0] and rest_ok and geo_ok,
                  f"{nr}MOVING {moving[1].removeprefix(_NR)}; REST {rest_why}; ANIM_GEO THROUGHOUT {geo_why}")
        so = _s_oracle_of(ctx)
        if rest:
            led.check("S140-S5", *judge_ghost_wears(rest, fr, ghost_as=ctx.get("ghost_as"), models=so["models"],
                                                    clips=so["clips"], rules=stage_rules(ctx.get("stage"))))
        else:
            led.unreached(("S140-S5",), f"no rest publish on field {field}")
    # S3: the moogle (every named slot empty)
    mo, why = _s_rig(ctx, S_MOOGLE)
    ld = _s_load(g, ctx, field, f"auto {S_AUTO_MASK}", ("empty", S_AUTO_MASK)) if mo else None
    if mo is None:
        led.unreached(("S140-S3",), why)
    elif ld["st"] is None:
        led.unreached(("S140-S3",), f"{ld['label']}: {ld['why']}")
    else:
        led.check("S140-S3", *_labelled(ld["label"], *judge_self_dress(ld["st"], mo, rig=_rig_index(S_MOOGLE),
                                                                       before=ld["before"], lines=ld["lines"],
                                                                       field=field)))
    # S6: the owner's 8-11 row, by name
    bo, why = _s_rig(ctx, S_SUB)
    prev = ld["st"] if ld is not None else None
    ld = _s_load(g, ctx, field, S_SUB) if bo else None
    if bo is None:
        led.unreached(("S140-S6",), why)
    elif ld["st"] is None:
        led.unreached(("S140-S6",), f"{ld['label']}: {ld['why']}")
    else:
        ok, why = judge_self_dress(ld["st"], bo, rig=_rig_index(S_SUB), before=ld["before"], lines=ld["lines"],
                                   field=field)
        rok, rwhy = judge_rest_named(ld["window"], bo)
        led.check("S140-S6", *_labelled(ld["label"], ok and rok, f"{why}; AT REST {rwhy}"))
        prev = ld["st"]
    # S4: `self off` -> Zidane at the NEXT SetModel
    zo, why = _s_rig(ctx, BW.RIG_NAMES[0])
    ld = _s_load(g, ctx, field, "off") if zo else None
    if zo is None:
        led.unreached(("S140-S4",), why)
    elif ld["st"] is None:
        led.unreached(("S140-S4",), f"{ld['label']}: {ld['why']}")
    else:
        led.check("S140-S4", *_labelled(ld["label"], *judge_self_off(ld["st"], zo, prev=prev, clear=ld["clear"])))
    _s_seated(g, led, ctx, field)
    _s_release(g, ctx, field)


def _s_seated(g, led: cb.Ledger, ctx: dict, field: int) -> None:
    """[ff9mapkit netsync s140] S7 / S8 -- THE OWNER'S 8-11 ROWS OVER A SEATED MEMBER: a warp through COOPSUB (30605: its
    Main_Init's RemoveParty(steiner) + B_PARTYADD(blank)) seats CharacterId 10 in the slot the oracle predicts; S7 `self
    auto <his bit>` + a re-warp of the stock field dresses the body as Blank through the LIVE party read; S8 `self off` + a
    re-warp (the plain-Zidane wire body), then `ghost <his bit>` -- the mirror's ghost wears him (rig 11) at rest and
    moving."""
    rows = ("S140-S7", "S140-S8")
    why = _bench_pre(ctx, SUB_PARTY_FIELD)
    bo, owhy = _s_rig(ctx, S_SEAT)
    so = _s_oracle_of(ctx) or {}
    seat = so.get("seat") or {}
    if why or bo is None or not seat.get("add"):
        led.unreached(rows, why or owhy or f"no seat oracle ({(ctx.get('oracle') or {}).get('problems')})")
        return
    rig = _rig_index(S_SEAT)
    char = BW.rig_to_char(rig)
    before = (_dress(g.state) or {}).get("party")
    want = seat_party(before, seat["remove"], seat["add"])
    try:
        g.warp(SUB_PARTY_FIELD)
        g.wait_frames(SETTLE_FRAMES)                # Main_Init's RemoveParty + B_PARTYADD run on entry
    except HarnessError as err:
        led.unreached(rows, f"the seed warp to {SUB_PARTY_FIELD} failed: {str(err)[:200]}")
        return
    seated = (_dress(g.state) or {}).get("party")
    slot = slot_of(seated, char)
    if slot is None:
        led.check("S140-S7", False, f"the COOPSUB seed seated no CharacterId {char}: dress.party {seated!r} (want {want!r} "
                                    f"off {before!r})")
        led.unreached(("S140-S8",), f"no seated CharacterId {char} to dress the ghost by")
        return
    bit = 1 << slot
    ld = _s_load(g, ctx, field, f"auto {bit}")
    if ld["st"] is None:
        led.unreached(("S140-S7",), f"{ld['label']}: {ld['why']}")
    else:
        ok, why = judge_self_dress(ld["st"], bo, rig=rig, before=ld["before"], lines=ld["lines"], field=field)
        sok, swhy = judge_seated(ld["st"], before, want, char=char)
        led.check("S140-S7", *_labelled(ld["label"], ok and sok, f"{swhy}; {why}"))
    ld = _s_load(g, ctx, field, "off")
    if ld["st"] is None:
        led.unreached(("S140-S8",), f"{ld['label']}: {ld['why']}")
        return
    label = f"{ld['label']} + `selfdress ghost {bit}`"
    w = _s_send(g, ctx, "ghost", bit)
    if w is not None:
        led.unreached(("S140-S8",), f"{label}: {w}")
        return
    levers = dict(LEVERS_OFF, mask=bit)
    rules = stage_rules(ctx.get("stage"))
    rest = on_field_prefix(cb.hold_for(g, GHOST_SETTLE_S), field)
    ok_r, why_r = judge_worn(rest, levers=levers, ghost_as=ctx.get("ghost_as"), models=so["models"], clips=so["clips"],
                             rules=rules)
    gh = ((_dress(rest[-1]) or {}).get("ghost") or {}) if rest else {}
    worn = (_int(gh.get("model")), _int(gh.get("rig")))
    ok_r = ok_r and worn == (bo["model"], rig)
    walk = _walk_probe(g, field)
    if walk["left"]:
        _recover(g, field)
        moving = (False, f"not reached: the probe hold {walk['tried'][-1]!r} was TAKEN OVER ({walk['why']})")
    elif walk["dir"] is None:
        moving = (False, f"not reached: {walk['why']} ({walk['tried']})")
    else:
        _settle(g, field)
        moving = judge_worn_moving(walk["samples"], levers=levers, ghost_as=ctx.get("ghost_as"), models=so["models"],
                                   clips=so["clips"], rules=rules)
    nr = _NR if (moving[1].startswith(_NR) or why_r.startswith(_NR)) else ""
    led.check("S140-S8", ok_r and moving[0],
              f"{nr}{label}: AT REST ghost (model, rig) {worn} (want ({bo['model']}, {rig})) -- {why_r.removeprefix(_NR)}; "
              f"MOVING {moving[1].removeprefix(_NR)}")


def _s_release(g, ctx: dict, field: int) -> None:
    """A leg's end: every lever released (`clear`) -- the body stays as it is until its next SetModel (the teardown law)."""
    w = _s_send(g, ctx, "clear")
    if w is not None:
        g.note(f"the s140 cleanup on {field}: {w}")


def _w_bench(g, led: cb.Ledger, ctx: dict) -> None:
    """[ff9mapkit netsync s140] Field 30602: W1 -- `self steiner` + a warp (dressed through SetModel), `dioboot` /
    `dioleave` (the WARM return), then at rest, idle past the inactive timer (his break clip: site b's witness), a walk (a
    hold TAKEN OVER reads "not reached") -- and W2, the cold control (a plain warp: dressed through SetModel again)."""
    field = DIO_FIELD
    why = _bench_pre(ctx, field)
    fr, owhy = _s_rig(ctx, W_RIG)
    if why or fr is None:
        led.unreached(W_CHECKS, why or owhy)
        return
    rig = _rig_index(W_RIG)
    src_list = ((_s_oracle_of(ctx) or {}).get("source_lists") or {}).get(field)
    ld = _s_load(g, ctx, field, W_RIG)
    if ld["st"] is None:
        led.unreached(W_CHECKS, f"{ld['label']}: {ld['why']}")
        return
    base = ld["st"]
    returns0 = cb.dio(base).get("returns")
    at = cb.mark(g)
    ok, bwhy = cb.boot(g)
    if not ok:
        led.unreached(("S140-W1",), f"{ld['label']} + `dioboot`: {bwhy}")
    else:
        cb.wait_steady(g)
        ok, lwhy = cb.leave(g, field)
        if not ok:
            led.unreached(("S140-W1",), f"{ld['label']} + `dioboot` / `dioleave`: {lwhy}")
            cb.back_to_field(g, field)
        else:
            back = g.state
            lines = cb.new(g, at)
            rest = on_field_prefix(cb.hold_for(g, REST_S), field)
            idle = on_field_prefix(cb.hold_for(g, IDLE_PAST_S), field)
            walk = _walk_probe(g, field)
            wlabel = f"{ld['label']} + `dioboot` / `dioleave`"
            if walk["left"]:
                _recover(g, field)
                led.unreached(("S140-W1",), f"{wlabel}: the walk probe hold {walk['tried'][-1]!r} was TAKEN OVER "
                                            f"({walk['why']})")
            elif walk["dir"] is None:
                led.unreached(("S140-W1",), f"{wlabel}: the walk probe: {walk['why']} ({walk['tried']})")
            else:
                led.check("S140-W1", *_labelled(wlabel, *judge_w1(base=base, back=back, returns0=returns0, lines=lines,
                                                                   rest=rest, idle=idle, walk=walk, ro=fr, rig=rig,
                                                                   src_list=src_list)))
    ld = _s_load(g, ctx, field, W_RIG)
    if ld["st"] is None:
        led.unreached(("S140-W2",), f"{ld['label']}: {ld['why']}")
    else:
        led.check("S140-W2", *_labelled(f"the cold control: {ld['label']}",
                                        *judge_self_dress(ld["st"], fr, rig=rig, before=ld["before"], lines=ld["lines"],
                                                          field=field)))
    _s_release(g, ctx, field)


def _conduct(g, name: str) -> dict:
    """ONE bench conductor on 30606: READY and control first (one trigger at a time), its TRIG bit set, every publish
    watched until its DONE (or WEDGED) bit -> {"outcome": "done" | "wedged" | "timeout" | "not ready", "samples" (the
    trigger's publish first), "before" (the READY publish), "trig", "end", "lines" (Memoria.log since the trigger),
    "why"}."""
    out = {"name": name, "outcome": "not ready", "samples": [], "before": None, "trig": None, "end": None, "why": None}
    st0 = cb.poll(g, lambda s: s.flag(sdf.READY) is True and free_on(s, SELF_FIELD), COND_READY_S,
                  "the caller READY with control")
    if st0 is None:
        out["why"] = f"the caller never read READY with control (READY {g.state.flag(sdf.READY)!r})"
        return out
    done, wedged = sdf.DONES[name], sdf.WEDGES.get(name)
    at = cb.mark(g)
    try:
        g.flag(sdf.TRIGGERS[name], True)
    except HarnessError as err:
        out.update(before=st0, why=f"`flag {sdf.TRIGGERS[name]} 1` refused: {str(err)[:200]}")
        return out
    trig = g.state
    samples, end = cb.watch(g, lambda s: s.flag(done) is True or (wedged is not None and s.flag(wedged) is True),
                            COND_TIMEOUT_S[name])
    outcome = "timeout" if end is None else ("done" if end.flag(done) is True else "wedged")
    out.update(outcome=outcome, samples=[trig] + samples, before=st0, trig=trig, end=end or (samples[-1] if samples
                                                                                            else trig),
               lines=cb.new(g, at))                 # Memoria.log since the trigger (N3: no dress line for the late sid)
    if outcome != "done":
        out["why"] = (f"{'WEDGED' if outcome == 'wedged' else 'no DONE bit'} after "
                      f"{cb.elapsed(trig, out['end']):.1f} s")
    return out


def _x_bench(g, led: cb.Ledger, ctx: dict) -> None:
    """[ff9mapkit netsync s140] The bench field's X conductor on the dressed Freya: X1 (the gesture by NAME, never ZDN) and
    X2 (after it, the idle's own frame count -- the ALIAS proof; control back within the hold + 5 s); then the J conductor
    on the same load: X3 (the jump slot on the SOURCE timeline)."""
    why = _bench_pre(ctx, SELF_FIELD)
    fr, owhy = _s_rig(ctx, S_RIG)
    if why or fr is None:
        led.unreached(X_CHECKS, why or owhy)
        return
    ld = _s_load(g, ctx, SELF_FIELD, S_RIG)
    if ld["st"] is None:
        led.unreached(X_CHECKS, f"{ld['label']}: {ld['why']}")
        return
    run = _conduct(g, "x")
    if run["outcome"] == "not ready":
        led.unreached(X_CHECKS, f"{ld['label']}: {run['why']}")
    else:
        after = on_field_prefix(cb.hold_for(g, X_AFTER_S), SELF_FIELD)
        label = f"{ld['label']} + TRIG_X"
        led.check("S140-X1", *_labelled(label, *judge_x1(run, fr)))
        src = (_s_oracle_of(ctx) or {}).get("sources", {}).get("x") or sdf.ANIM_X_FRAMES
        led.check("S140-X2", *_labelled(label, *judge_x2(run, after, fr, idle_frames=fr.get("idle_frames"),
                                                         hold_s=src / TICK_HZ)))
    # X3: the jump slot on the same load (field 404's ladder mount on the dressed Freya)
    jrun = _conduct(g, "j")
    if jrun["outcome"] == "not ready":
        led.unreached(("S140-X3",), f"{ld['label']}: {jrun['why']}")
    else:
        jsrc = (_s_oracle_of(ctx) or {}).get("sources", {}).get("j")
        led.check("S140-X3", *_labelled(f"{ld['label']} + TRIG_J", *judge_x3(jrun, fr, src_frames=jsrc, jump0=sdf.J_JUMP0,
                                                                            jump1=sdf.J_JUMP1)))
        if jrun["outcome"] != "done":
            _s_send(g, ctx, "clear")
            try:
                g.warp(SELF_FIELD)                  # a wedged player function dies with the field
            except HarnessError as err:
                g.note(f"the recovery warp after a J that did not finish failed: {str(err)[:200]}")
    _s_release(g, ctx, SELF_FIELD)


def _n_bench(g, led: cb.Ledger, ctx: dict) -> None:
    """[ff9mapkit netsync s140] The bench field's Zidanes: N1 (the twin turned away by the player gate) and N3 (the late
    98+CC entry turned away by the control check) on one `self freya` load, then N2 (`gate 0` + a re-warp)."""
    why = _bench_pre(ctx, SELF_FIELD)
    fr, owhy = _s_rig(ctx, S_RIG)
    zo, zwhy = _s_rig(ctx, BW.RIG_NAMES[0])
    if why or fr is None or zo is None:
        led.unreached(N_CHECKS, why or owhy or zwhy)
        return
    ld = _s_load(g, ctx, SELF_FIELD, S_RIG)
    if ld["st"] is None:
        led.unreached(N_CHECKS, f"{ld['label']}: {ld['why']}")
        return
    led.check("S140-N1", *_labelled(ld["label"], *judge_n1(ld["st"], ld["before"], fr, zo, lines=ld["lines"])))
    uid = _player(ld["st"]).get("uid")
    run = _conduct(g, "n3")
    if run["outcome"] == "not ready":
        led.unreached(("S140-N3",), f"{ld['label']}: {run['why']}")
    else:
        after = on_field_prefix(cb.hold_for(g, N3_AFTER_S), SELF_FIELD)
        led.check("S140-N3", *_labelled(f"{ld['label']} + TRIG_N3", *judge_n3(run, after, fr, zo, uid=uid)))
    ld = _s_load(g, ctx, SELF_FIELD, S_RIG, ("gate", 0))
    if ld["st"] is None:
        led.unreached(("S140-N2",), f"{ld['label']}: {ld['why']}")
    else:
        led.check("S140-N2", *_labelled(ld["label"], *judge_n2(ld["st"], ld["before"], fr, lines=ld["lines"])))
    _s_release(g, ctx, SELF_FIELD)


def _t_run(g, ctx: dict, name: str, cond: str) -> dict:
    """One rig's conductor run on its own load: `self <name>` + a re-warp of 30606, then ``cond`` -> {"name", "outcome",
    "model" (worn at the load), "want" (the oracle's), "timeline" / "remaps" (deltas over the run), "loop_bit", "end_bit",
    "unreached" (a load that never came up)}."""
    ro, why = _s_rig(ctx, name)
    if ro is None:
        return {"name": name, "outcome": "not ready", "unreached": why}
    ld = _s_load(g, ctx, SELF_FIELD, name)
    if ld["st"] is None:
        return {"name": name, "outcome": "not ready", "unreached": f"{ld['label']}: {ld['why']}", "label": ld["label"]}
    run = _conduct(g, cond)
    if run["outcome"] == "not ready":
        return {"name": name, "outcome": "not ready", "unreached": f"{ld['label']}: {run['why']}"}
    end = run["end"]
    return {"name": name, "outcome": run["outcome"], "model": _player(ld["st"]).get("model"), "want": ro["model"],
            "timeline": count_delta(run["before"], end, "timeline_kept"),
            "remaps": count_delta(run["before"], end, "bframe_remaps"),
            "loop_bit": end.flag(sdf.T3_LOOP) if hasattr(end, "flag") else None,
            "end_bit": end.flag(sdf.T3_END) if hasattr(end, "flag") else None, "label": ld["label"]}


def _t_bench(g, led: cb.Ledger, ctx: dict) -> None:
    """[ff9mapkit netsync s140] T2 (the proof block's self-dress line: no field needed), then on the bench field T1 (the
    source timeline: Garnet, then the moogle control) and T3 (field 2705's loop on EVERY rig, each its own load -- a
    WEDGED_T3 is recovered by the next warp, the last one by a final reload)."""
    led.check("S140-T2", *judge_self_selftest(_self(g.state), cb.log_lines(g)))
    why = _bench_pre(ctx, SELF_FIELD)
    if why:
        led.unreached(("S140-T1", "S140-T3"), why)
        return
    rig_run = _t_run(g, ctx, T1_RIG, "t1")
    if rig_run.get("unreached"):
        led.unreached(("S140-T1",), f"{T1_RIG}: {rig_run['unreached']}")
    else:
        control = _t_run(g, ctx, T1_CONTROL, "t1")
        if control.get("unreached"):
            led.unreached(("S140-T1",), f"the control {T1_CONTROL}: {control['unreached']}")
        else:
            led.check("S140-T1", *judge_t1(rig_run, control))
    runs = []
    for name in T3_RIGS:
        r = _t_run(g, ctx, name, "t3")
        runs.append(r)
        if r.get("unreached") and not runs[:-1]:
            break                                   # the first load refused (an engine before s140): nothing else runs
    led.check("S140-T3", *judge_t3(runs))
    if runs and runs[-1].get("outcome") == "wedged":
        _s_send(g, ctx, "clear")
        try:
            g.warp(SELF_FIELD)                      # the wedged player function dies with the field
        except HarnessError as err:
            g.note(f"the recovery warp after a WEDGED_T3 failed: {str(err)[:200]}")
    _s_release(g, ctx, SELF_FIELD)


# ------------------------------------------------------------------------------------------------ leg F's steps (s141)
def _f_walk(g, field: int, *, ticks: int = F_WALK_TICKS, holds: int = F_WALK_HOLDS) -> dict:
    """[ff9mapkit netsync s141] F1b / F3 / F6's walk (harness input, THE UNATTENDED LAW): ``holds`` ALTERNATING holds of
    ``ticks`` field ticks each -- sized to frames at the MEASURED render rate; the first direction that moves the player
    (up, then down / left / right), then back, then out again -- every publish watched; a sample that is not
    :func:`free_on` ``field`` is the hold TAKEN OVER (the walk stops there). -> {"dir", "samples", "left", "why", "tried",
    "before" (the publish before the first hold), "after" (the last publish of a short window once the field is free
    again)} -- the bracket a fired count is judged across."""
    out = {"dir": None, "samples": [], "left": False, "why": None, "tried": [], "before": None, "after": None}
    try:
        rate = g.rate(require=True)
    except HarnessError as err:
        out["why"] = f"no measured render rate to size the holds in ticks ({str(err)[:160]})"
        return out
    frames = max(1, rate.frames_for_ticks(ticks))
    watch = frames + rate.frames_for_ticks(WATCH_EXTRA_TICKS)
    timeout = watch / max(1.0, rate.fps_lo) * 3.0 + 5.0
    if _settle(g, field) is None:
        out["why"] = f"field {field} never came up with the player free before the walk"
        return out
    out["before"] = g.state

    def hold(d) -> list:
        f0 = g.state.frame
        g.hold(d, frames)
        samples, _end = cb.watch(g, lambda s, f0=f0: not free_on(s, field) or s.frame >= f0 + watch, timeout=timeout)
        out["tried"].append(d)
        out["samples"] += samples
        bad = next((s for s in samples if not free_on(s, field)), None)
        if bad is not None:
            out.update(left=True, why=_taken(bad))
        return samples

    for d in WALK_DIRECTIONS:
        moved = hold(d)
        if out["left"]:
            return out
        if moving_middle(moved):
            out["dir"] = d
            break
    if out["dir"] is None:
        out["why"] = f"no direction moved the player {STEADY_TICKS + TAIL_TICKS + 1}+ ticks ({frames} frames a hold)"
        return out
    for i in range(1, holds):
        hold(BACK[out["dir"]] if i % 2 else out["dir"])
        if out["left"]:
            return out
    if _settle(g, field) is None:
        out.update(left=True, why=f"field {field} never came back with the player free after the walk")
        return out
    out["after"] = (on_field_prefix(cb.hold_for(g, F_AFTER_S), field) or [g.state])[-1]
    return out


def _f_rig(ctx: dict, name: str) -> tuple:
    """(the s140 oracle's row for rig ``name`` -- its model, GEO, clips --, its rig index; None) or (None, None, why)."""
    ro, why = _s_rig(ctx, name)
    if ro is None:
        return None, None, why
    return ro, (-1 if name == F_ZIDANE else _rig_index(name)), None


def _f_floors(fo: dict, st) -> list | None:
    """The walkmesh floors under ``st``'s published x / z (the oracle's offline walkmesh) -- None when unread."""
    xz = _pos(st)
    lookup = fo.get("floors_at")
    if xz is None or not callable(lookup):
        return None
    try:
        return list(lookup(xz[0], xz[1]))
    except Exception:                        # noqa: BLE001 - an unreadable lookup names no floor
        return None


def _f_bench(g, led: cb.Ledger, ctx: dict) -> None:
    """[ff9mapkit netsync s141] FP (the proof block's dress polish line: no field needed), then on the bench field 30606 one
    `self steiner` load: F5 (the caller's F5H, then F5S) and F8 (F8A, then F8D); then a `self moogle` load: F2d (the
    caller's F2d -- field 2930's code 19 on the table the moogle's drops emptied)."""
    led.check("S141-FP", *judge_f_proof(cb.log_lines(g)))
    why = _bench_pre(ctx, SELF_FIELD)
    fo, fwhy = _f_oracle_of(ctx)
    if why or fo is None:
        led.unreached(F_BENCH_CHECKS, why or fwhy)
        return
    _f_bench_steiner(g, led, ctx, fo)
    _f_bench_f2d(g, led, ctx, fo)
    _s_release(g, ctx, SELF_FIELD)


def _f_bench_f2d(g, led: cb.Ledger, ctx: dict, fo: dict) -> None:
    """[ff9mapkit netsync s141] F2d: `self moogle` + a FRESH load of 30606 (the player's twelve registrations dropped: an
    EMPTY table), then the caller's F2d -- a WEDGED_F2D (the player's function never returned) is recovered by a warp."""
    ro, rig, owhy = _f_rig(ctx, F_DROP)
    pwhy = owhy or (None if fo.get("f2d") else f"no s141 F2d oracle ({fo.get('f2d_why') or _f_part(fo, ctx, 'f2d')})")
    if pwhy:
        led.unreached(("S141-F2d",), pwhy)
        return
    ld = _s_load(g, ctx, SELF_FIELD, F_DROP, leg="F")
    if ld["st"] is None:
        led.unreached(("S141-F2d",), f"{ld['label']}: {ld['why']}")
        return
    run = _conduct(g, "f2d")
    if run["outcome"] == "not ready":
        led.unreached(("S141-F2d",), f"{ld['label']}: {run['why']}")
        return
    after = on_field_prefix(cb.hold_for(g, F_AFTER_S), SELF_FIELD)
    led.check("S141-F2d", *_labelled(f"{ld['label']} + TRIG_F2D", *judge_f2d(run, after, ro, rig=rig,
                                                                               want=fo["f2d"]["want"])))
    if run["outcome"] != "done":
        _s_send(g, ctx, "clear")
        try:
            g.warp(SELF_FIELD)                      # a wedged player function dies with the field
        except HarnessError as err:
            g.note(f"the recovery warp after an F2d that did not finish failed: {str(err)[:200]}")


def _f_bench_steiner(g, led: cb.Ledger, ctx: dict, fo: dict) -> None:
    """[ff9mapkit netsync s141] F5 and F8 on one `self steiner` load of 30606."""
    rows = ("S141-F5", "S141-F8")
    ro, rig, owhy = _f_rig(ctx, F8_RIG)
    if ro is None:
        led.unreached(rows, owhy)
        return
    ld = _s_load(g, ctx, SELF_FIELD, F8_RIG, leg="F")
    if ld["st"] is None:
        led.unreached(rows, f"{ld['label']}: {ld['why']}")
        return
    hide = _conduct(g, "f5h")
    if hide["outcome"] == "not ready":
        led.unreached(rows, f"{ld['label']}: {hide['why']}")
        return
    after_h = on_field_prefix(cb.hold_for(g, F_AFTER_S), SELF_FIELD)
    show = _conduct(g, "f5s")                       # ALWAYS: a set meshflags bit would ride PosObj.copy into a later return
    after_s = on_field_prefix(cb.hold_for(g, F_AFTER_S), SELF_FIELD)
    led.check("S141-F5", *_labelled(f"{ld['label']} + TRIG_F5H / TRIG_F5S",
                                    *judge_f5(hide, after_h, show if show["outcome"] != "not ready" else None, after_s, ro,
                                              rig=rig)))
    hwhy = _f_part(fo, ctx, "hands") or (None if (fo.get("hands") or {}).get(F8_RIG) else f"no {F8_RIG} hand oracle")
    if hwhy:
        led.unreached(("S141-F8",), hwhy)
    else:
        attach = _conduct(g, "f8a")
        after_a = on_field_prefix(cb.hold_for(g, F_AFTER_S), SELF_FIELD)
        detach = _conduct(g, "f8d") if attach["outcome"] != "not ready" else None
        after_d = on_field_prefix(cb.hold_for(g, F_AFTER_S), SELF_FIELD) if detach is not None else []
        if attach["outcome"] == "not ready":
            led.unreached(("S141-F8",), f"{ld['label']}: {attach['why']}")
        else:
            led.check("S141-F8", *_labelled(f"{ld['label']} + TRIG_F8A / TRIG_F8D",
                                            *judge_f8(attach, after_a, detach if detach and detach["outcome"] != "not ready"
                                                      else None, after_d, fo["hands"][F8_RIG], ro, rig=rig,
                                                      cup=sdf.CUP_SID, bone=F8_BONE)))


def _f_load(g, ctx: dict, field: int, name: str) -> dict:
    """One FRESH leg-F load of the stock field dressed as ``name`` (`self off` for the undressed control): :func:`_s_load`
    with leg F's lever."""
    return _s_load(g, ctx, field, "off" if name == F_ZIDANE else name, leg="F")


def _f_self(g, led: cb.Ledger, ctx: dict) -> None:
    """[ff9mapkit netsync s141] The "self" phase's leg F, on the stock field (after leg S): one `self freya` load -- F1, F4,
    F4g on its arrival, F1b (a walk), F6 (a diorama's WARM return on the same load, then a walk) --, then one fresh load
    each: F2 (the moogle), F2c (Cinna), F7 (Steiner), F3 (`self off`: the control, then a walk); every lever released."""
    field = ctx["stock"]
    fo, why = _f_oracle_of(ctx)
    if fo is None:
        led.unreached(F_STOCK_CHECKS, why)
        return
    _f_freya(g, led, ctx, fo, field)
    for cid, name in (("S141-F2", F_DROP), ("S141-F2c", F_CINNA), ("S141-F7", F_STEINER)):
        ro, rig, owhy = _f_rig(ctx, name)
        pwhy = owhy or _f_part(fo, ctx, "steps") or (None if name in fo["steps"] else f"no s141 oracle steps for {name}")
        if pwhy:
            led.unreached((cid,), pwhy)
            continue
        ld = _f_load(g, ctx, field, name)
        if ld["st"] is None:
            led.unreached((cid,), f"{ld['label']}: {ld['why']}")
            continue
        drop = cid != "S141-F7"
        sound = (fo["rigs"][name].get("step_sound") or None) if not drop else None
        led.check(cid, *_labelled(ld["label"], *judge_f_steps(ld["st"], fo["steps"][name], ro, rig=rig, sound=sound,
                                                              before=ld["before"] if drop else None,
                                                              lines=ld["lines"] if drop else None)))
    _f_control(g, led, ctx, fo, field)
    _s_release(g, ctx, field)


def _f_freya(g, led: cb.Ledger, ctx: dict, fo: dict, field: int) -> None:
    """[ff9mapkit netsync s141] The F1 load (`self freya` + a fresh warp): F1 / F4 / F4g on its arrival, F1b (a walk), then
    F6 -- `dioboot` / `dioleave` (field 250 has Main_Reinit and random battles: the diorama primes a WARM return), the
    arrival back, a walk."""
    rows = ("S141-F1", "S141-F4", "S141-F4g", "S141-F1b", "S141-F6")
    ro, rig, owhy = _f_rig(ctx, F_RIG)
    pwhy = owhy or _f_part(fo, ctx, "steps", "reinit") or (None if F_RIG in fo["steps"] else f"no steps for {F_RIG}")
    if pwhy:
        led.unreached(rows, pwhy)
        return
    ld = _f_load(g, ctx, field, F_RIG)
    if ld["st"] is None:
        led.unreached(rows, f"{ld['label']}: {ld['why']}")
        return
    st, src = ld["st"], fo.get("src_model")
    led.check("S141-F1", *_labelled(ld["label"], *judge_f_steps(st, fo["steps"][F_RIG], ro, rig=rig)))
    lwhy = _f_part(fo, ctx, "light", "ghost_light")
    floors = _f_floors(fo, st) if not lwhy else None
    if lwhy:
        led.unreached(("S141-F4", "S141-F4g"), lwhy)
    else:
        led.check("S141-F4", *_labelled(ld["label"], *judge_f4(st, fo["light"], ro, rig=rig, floors=floors, src=src)))
        # the ghost re-tints ~7 Hz while driven (its row -1 until the first re-tint this load)
        win = list(ld["window"]) + on_field_prefix(cb.hold_for(g, F_GHOST_LIGHT_S), field)
        led.check("S141-F4g", *_labelled(ld["label"], *judge_f4g(win, fo["ghost_light"], ro, rig=rig, floors=floors,
                                                                  src=src)))
    walk = _f_walk(g, field)
    led.check("S141-F1b", *_labelled(f"{ld['label']} + a walk", *judge_f_fired(walk, ro, rig=rig, key="steps_fired",
                                                                               other="steps_fired_player")))
    if walk["left"]:
        _recover(g, field)
    # F6: a diorama's WARM return on this load (W1's lane, on the stock field). Its per-load-reset half needs a publish
    # before the boot that CARRIES fires: F1b's settled one -- or, when F1b's walk was taken over (the recover warp is a cold
    # load: it reset the counts), a fresh walk's
    pre = walk if not walk["left"] and walk.get("after") is not None else _f_walk(g, field)
    if pre is not walk and pre["left"]:
        _recover(g, field)
    wlabel = f"{ld['label']} + `dioboot` / `dioleave`"
    base = pre["after"] if not pre["left"] and pre.get("after") is not None else g.state
    returns0 = cb.dio(base).get("returns")
    ok, bwhy = cb.boot(g)
    if not ok:
        led.unreached(("S141-F6",), f"{ld['label']} + `dioboot`: {bwhy}")
        return
    cb.wait_steady(g)
    ok, lwhy2 = cb.leave(g, field)
    if not ok:
        led.unreached(("S141-F6",), f"{wlabel}: {lwhy2}")
        cb.back_to_field(g, field)
        return
    back_win = on_field_prefix(cb.hold_for(g, DRESS_READ_S), field)
    if not back_win:
        led.unreached(("S141-F6",), f"{wlabel}: no free publish on field {field} after the return")
        return
    walk = _f_walk(g, field)
    led.check("S141-F6", *_labelled(wlabel, *judge_f6(base=base, back=back_win[-1], returns0=returns0,
                                                      want=fo["reinit"][F_RIG], walk=walk, ro=ro, rig=rig)))
    if walk["left"]:
        _recover(g, field)


def _f_control(g, led: cb.Ledger, ctx: dict, fo: dict, field: int) -> None:
    """[ff9mapkit netsync s141] F3, the control: `self off` + a fresh load -- Zidane's own keys (no hook on an undressed
    body), then a walk: steps_fired_player +2 or more, steps_fired +0."""
    ro, rig, owhy = _f_rig(ctx, F_ZIDANE)
    pwhy = owhy or _f_part(fo, ctx, "steps") or (None if F_ZIDANE in fo["steps"] else "no steps for zidane")
    if pwhy:
        led.unreached(("S141-F3",), pwhy)
        return
    ld = _f_load(g, ctx, field, F_ZIDANE)
    if ld["st"] is None:
        led.unreached(("S141-F3",), f"{ld['label']}: {ld['why']}")
        return
    ok_s, why_s = judge_f_steps(ld["st"], fo["steps"][F_ZIDANE], ro, rig=rig)
    walk = _f_walk(g, field)
    ok_w, why_w = judge_f_fired(walk, ro, rig=rig, key="steps_fired_player", other="steps_fired")
    if walk["left"]:
        _recover(g, field)
    # "not reached" only when NO judged half is red (a judged red at the load is the verdict whatever the walk did)
    nr_s, nr_w = why_s.startswith(_NR), why_w.startswith(_NR)
    judged_red = (not nr_s and not ok_s) or (not nr_w and not ok_w)
    nr = _NR if (nr_s or nr_w) and not judged_red else ""
    led.check("S141-F3", *_labelled(ld["label"], ok_s and ok_w, f"{nr}AT THE LOAD {why_s.removeprefix(_NR)}; WALKING "
                                                                f"{why_w.removeprefix(_NR)}"))


def bench_preflight(g) -> tuple:
    """S140-PF: the bench field's DEPLOYED .eb (READ-ONLY: the first Memoria.ini FolderNames folder that ships
    EVT_TEST30606, as the engine loads it) through _selfdress_field.preflight -> (ok, why). FAILS CLOSED: no .eb, one that
    does not parse, or any row off reads red."""
    try:
        eb, where = sdf.deployed_eb(Path(g.game_path))
    except Exception as err:                 # noqa: BLE001 - an unreadable deploy is a red precondition, never a crash
        return False, f"the deployed .eb read raised {type(err).__name__}: {str(err)[:200]}"
    if eb is None:
        return False, where
    why = sdf.preflight(eb)
    if why is not None:
        return False, f"{where}: {why}"
    _ok, order = sdf.main_init_order(eb)
    return True, f"{where}: every preflight row holds -- {order}"


# ================================================================================================ the run
def _ctx_new(stock: int, legs, calibrate: bool, cal_mode: str | None = None) -> dict:
    return {"stock": int(stock), "legs": tuple(legs), "calibrate": bool(calibrate), "cal_mode": cal_mode,
            "ini_ok": False, "oracle": None, "stage": None, "pre": False, "seeded": False, "reads": {}, "states": {},
            "unreached": {}, "walk": None, "rest": None, "ghost_as": None, "garnet_hair": None,
            "missing": [], "pf": None}                    # [ff9mapkit netsync s140] the unregistered fields, the preflight


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
                # [ff9mapkit netsync s141] the s140 line by stage: s141's ReleaseBench names `polish` too
                stage = ctx.get("stage") or 0
                extra, lines = judge_released, (RELEASE_LINE,) + (
                    (RELEASE_LINE_S141 if stage >= 141 else RELEASE_LINE_S140,) if stage >= 140 else ())
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
    ok, why = _ini_guard(g, ctx["legs"])
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
    ctx["missing"] = list(missing)
    led.check("S138-PRE", not missing, ctx.get("pre_why") or
              (f"not registered: {missing} (deploy COOPPARTY: py tools/deploy_field.py "
               f"studies/battle-coop/bench/coopparty.field.toml --id {PARTY_FIELD} --mod-folder FF9CustomMap-msgs"
               + (f"; the s140 bench field: py studies/battle-coop/bench/selfdress_bench.py deploy" if SELF_FIELD in missing
                  else "")
               + (f"; the 8-11 seed: py tools/deploy_field.py studies/battle-coop/bench/coopsub.field.toml --id "
                  f"{SUB_PARTY_FIELD} --mod-folder FF9CustomMap-msgs" if SUB_PARTY_FIELD in missing else "")
               + ", then relaunch)" if missing else ", ".join(f"{f} {regs.get(f)!r}" for f in pre)))
    # [ff9mapkit netsync s140] the bench field's preflight (READ-ONLY, offline): FAILS CLOSED
    if any(LEGS[leg].get("preflight") for leg in ctx["legs"]):
        ctx["pf"] = bench_preflight(g)
        led.check("S140-PF", *ctx["pf"])
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
