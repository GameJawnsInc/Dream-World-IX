# O5 -- the stair walk and the stored choice under the trace: the design

**Status: DESIGN, offline.** Nothing is imported, built, deployed, launched or frozen. The inputs are `o5_route.md` and
`o5_research.json` in this folder (the reconciled route, the walks, the start, the harness gaps, the fork gates) with the
critic's twelve problems (`critique.problems`) overriding the map where they conflict, and the nine decisions the lead
made on top of both (0.1). This file folds them into code-level decisions in `o4_design.md`'s structure and keeps what
O2-O4 learned. Every number below was read, read-only, from the stock US `.eb` files (through the kit at this branch's
head), the research's scratch listings (`<scratchpad>/o5_research/reconcile/L{151,153,154}.txt`, `win_*.txt`,
`stages*.out`, `route153.out`), the live install (mod folders, `Memoria.ini`) and the live Memoria source
(`C:\gd\FFIX\Memoria`, = the deployed DLL, sha256 `ba976242...`); 0.2 says how. The offline check (section 6)
re-derives every one of them.

**The segment** (decision 1): New Game, the trace armed, then in field 70 (after 70 e0 t0 ip130, before ip475) a raw
`warp 153 325 1190` (S) / `warp 31245 325 1190` (F). 153@325 (visit 1; EVT_ALEX1_AC_H2F): pages 113-117; THE STAIR WALK,
the segment's only control grant (e3 t1 EnableMove ip785, Zidane); pages 126 and 127; choice 128 answered "Examine her
face" (absolute 1: `Global.Bit[3795] := SYSVAR[9]` at e3 t1 ip1741, 0 -> 1); path 1's eleven windows, 131-133, the
KEYON pairs 134/135 and 139/138, the timed 137 and 140; `Field(154)` (e3 t1 ip3158, FieldEntrance 304). 154@304 (visit 2;
EVT_ALEX1_AC_ENT_2F; Zorn & Thorn, no control): pages 153/154 and three KEYON pairs; `Field(153)` (e2 t1 ip1528, 316).
153@316 (visit 3, no control): twelve pages and two pairs; `Field(151)` (e18 t1 ip1085, 110). It ENDS on arrival in 151
(EVT_ALEX1_AC_SEAT_R) -- real 151 on S, member(151) 31244 on F -- cut at 151's first EMITTED row, e0 t0 ip22 (0.2 #1).
SC 1190 throughout. No battle, FMV, ATE or naming: Steiner's naming and `Byte[6] |= 8` lie after the cut (O6's).

What O5 newly puts under the trace: a WALK in alxc whose goal is a HEIGHT (the stage-6 test at 153 e3 t1 ip859); a
CHOICE whose answer is STORED (so the claim needs the stored value proven the driver's verified pick); a route that
REVISITS its start place at the same SC (153 at 325, then at 316) -- the engine's per-site same-value suppression shapes
what the revisit emits (0.2 #2); and two members O4 deployed but never ran (31246, 31244) and one it ran only to its
first row (31245).

---

## 0. What this design decides, and what it found

### 0.1 Decided upstream (not relitigated)
1. **The segment** (the critic's problem 3, candidate 3): the run above; `visits` [153, 154, 153], the end on arrival in
   151 with `side_ends` {S: [151], F: [31244]}; the cut at 151's first emitted row (0.2 #1); SC 1190 throughout, O3's
   NO-SC shape. 151 e0 t0 ip315 `Byte[8] := 125` races the end-state read at the arrival: Byte[8] is out of `end_state`
   (its end value is the trace's last pre-cut write, 4.9). The stock event names are 153 EVT_ALEX1_AC_H2F, 154
   EVT_ALEX1_AC_ENT_2F, 151 EVT_ALEX1_AC_SEAT_R (the FBG names AC_FTI/AC_RST are scene names; the kit named the
   members O4_AC_H2F, O4_AC_FTI, O4_ALXC_AC_RST after them).
2. **The fork side:** O4's deployed members 31245 (153), 31246 (154), 31244 (151); nothing imported, built or deployed.
   `o5_forks.json` references O4's chain as `o3_forks.json` referenced O1's (6.4). Every route `Field()` is retargeted;
   O5-BUILD re-checks it offline, per language (6.1).
3. **Choice 128 picks "Examine her face" (absolute 1)** -- a fork that stores a constant fails it. The 127 -> 128
   stray-press race is closed by an OPT-IN PRE-CHOICE GUARD (S10: page-once on the marker page, the quiet window, closed
   by the published choice), generalized from O4's machinery as NEW opt-in code (O4's own paths untouched). choose()'s
   landing is VERIFIED (S11). The fallback (pick 0, `take: "default"`) is designed (2.5.7), frozen only if the
   rehearsals show the race cannot be closed.
4. **The outside-input witness runs the WHOLE run** (S12, `pred["witness"]`).
5. **s88's same-value suppression** is modelled in the FakeGame, opt-in, faithful to the sink (H13); the dry run's
   renderer models it (O4's renderer already does); the claim's scope line says which suppressed stores are compared
   (5.4); row counts are recounted from the model (4.16).
6. **O4's full preflight set** (6.2) minus what is O4's alone (P-GATE, P-TEXT block 2: 11.2 #1); all green today
   (0.2 #12).
7. **Rehearsals** (the lead): R-STAIRS x2, R-FULL x2, R-WALK-VOID, F-SMOKE, F-PASS (untraced, before the freeze) (7.1).
8. **Built ON the shared machinery:** `O5Segment` in `o5_hallway.py`; every shared change keeps O1, O2, O3 AND O4
   analysing byte-identically -- the O4 gate's baseline captured FIRST (1.4); G21's pins extended by its own rules. The
   critic's minor problems are binding fixes (11.1). Predictions frozen by the lead after the rehearsals (`--freeze`
   refusing to overwrite).
9. Master's `Session.fight` hardening may land meanwhile (it has: c5e5dd88, ad57966b, 0.2 #16); O5 has no battle; the
   lead merges master before the merge.

### 0.2 Found while designing (each verified offline, read-only)
1. **The end row is emitted.** The sink keys suppression by `Site {Fld, M, Src, Sid, Tag, Ip, First, Bit, Type}`
   (StoryTrace.cs:101-140), `Fld` the RAW `fldMapNo` (:374-376): 151's first store opens a NEW site in the epoch, and a
   site's first same-value store is emitted (`emit = !site.SameEmitted`, :383-390). So 151 e0 t0 ip22 `Bit[191] := 0`
   (0 -> 0, same 1) is the first `w` row in place 151 -- the cut row on both sides (31244 on F: the member's own
   `fldMapNo`). The row before it is 153 e18 t1 ip1077 `Int16[2] := 110`. (The critic's ip718 row belonged to
   candidate 4.)
2. **The revisit's emitted pattern** (StoryTrace.cs:383-401 over the raw warp's start values: Int16[9] 643, Byte[13] 1,
   Int16[11] -1, Byte[14] 0, Byte[8] 125, Bit[191] 0, Bit[184] 0 -- field 70's prologue, 70 e0 t0 ip57/130/138/200/249).
   Visit 1 (153@325) emits all six prologue stores: ip22 (0->0, same), ip49 (same), ip57 (643 -> -1, a change), ip119
   (1 -> 0, a change), ip138 (-1 -> -1, same), ip200 (0 -> 0, same). Visit 2 (154) opens eight new sites: all emitted.
   Visit 3 (153@316, the same `fldMapNo`, the same epoch): ip22, ip49, ip138, ip200 are same-value at sites that already
   EMITTED a same-value store -> SUPPRESSED (counted); ip57 (-1 -> -1) and ip119 (0 -> 0) are the FIRST same-value
   stores at sites whose visit-1 store was a change -> EMITTED with `same: 1`. So **visit 3's first emitted row is e0 t0
   ip57**, and the epoch's close (`storytrace 0`: `Stop` -> `EmitCounts`, :187-205, :540-557) writes four `c` rows for
   place 153 (ip22, ip49 masked; ip138 last -1, ip200 last 0; n 1 each), stamped with the SITE's fld/m. `cut_at_end`
   keeps them (their place, 153, is no end place: segment_trace.py:127-136). This pattern is START-DEPENDENT (critic #5,
   5.4): after a true O1-O4 run visit 1's ip57/ip119 would be same-value too, and visit 3's first emitted row would be
   e18 t1 ip890.
3. **Row counts before the cut** (from #2): 21 emitted `w` rows (17 unmasked + 4 masked: 153 ip22/ip49, 154 ip26/ip53)
   and 4 `c` rows (2 masked). 15 distinct unmasked keys: 12 writes + 3 chain (4.3-4.4). No SC row.
4. **Every key's function offset**, joined by `ScriptIndex.join` on the stock US bytes: 153 e0 t0 ip22/49/57/119/138/200
   -> off 16/43/51/113/132/194; e3 t1 ip1741/2953/3150 -> 1333/2545/2742; e18 t1 ip890/1077 -> 766/953; 154 e0 t0
   ip26/53/61/123/142/204/279 -> 16/43/51/113/132/194/269; e2 t1 ip1520 -> 1409; 151 e0 t0 ip22/315 -> 16/309; 153 e28 t2
   ip38/227 -> 8/197. Every join `status store`, `census` True.
5. **Store census:** stock 153 holds 51 global store sites, 154 holds 22, 151 holds 21 (`o3_prima_vista.store_sites`, 0
   undecoded). 151's first store at entrance 110 IS the cut: none of its sites precedes it (6.1 O5-CENSUS).
6. **Instancing per route entrance** (`o4_castle.instanced_at`): 153 at 325 {code 1, 2, 22; object 3, 7, 9, 11, 31;
   region 26, 27, 28}; 153 at 316 {code 1, 2; object 18, 20}; 154 at 304 {code 1; object 2, 4}. No instancing op lies
   outside e0 t0 in either field. 153 e15 (`Byte[8] := 125` ip32) is a SHARED entry: run only by e32 t1 ip866
   `RunSharedScript(15)`, and e32 is instanced at 328 alone. The shared entries run on the route (4, 5, 6, 8, 10, 12, 19
   in 153; 3 in 154) hold no store.
7. **Gateways** (`eventscan.scan_gateways`, `face_gate` None on every one): 153 e23 (-> 154 @315), e24 (-> 150 @315), e25
   (-> 64 / 151 @315), e28 (-> 150 @5); 154 e8 (-> 153 @301, 158 @300), e9 (-> 156, 155), e10 (-> 156, 167); 151 e8 (->
   153 @327). Of these only 153 e28 is instanced at a route entrance (325). e23/e26, e24/e28 and e25/e27 share quads.
8. **The side-scene and back-door guards, exact:** 153 e26 t2 ip38 `SET({obj(uid=250).f[1] const(65436) B_GT
   obj(uid=250).f[2] const(1333) B_GT B_ANDAND B_EXPR_END})` (on the ground and z > 1333), ip58 `Map.Byte[24] const(6)
   B_EQ`, ip88 `DisableMove()`, ip110 `Map.Byte[24] := 7`; e27 t2 ip38 the stage-6 test, ip68 `DisableMove()`, ip90
   `Map.Byte[24] := 14`; e28 t2 ip30 `SET({B_SYSVAR[2] B_EXPR_END})` (control) alone, ip38 `Byte[8] := 25`, ip83
   `ExitField()`, ip227 `Int16[2] := 5`, ip235 `Field(150)`.
9. **The stair test:** 153 e3 t1 ip859 `SET({obj(uid=255).f[1] const(65086) B_GT B_EXPR_END})` -- `const(65086)` is
   -450 (a 2-byte constant is signed, EBin.cs:1251-1255), `f[1]` is -pos[1] (EBin.cs:1785-1793), uid 255 the current
   object, e3 (EventEngine.cs:946-949). The grant: ip752 `WaitWindow(1)`, ip755 `Map.Bit[158] := 1`, ip785
   `EnableMove()`; the loss: ip874, ip893 `DisableMove()`; the teleport ip1466 `CreateObject(64371, 856)` = (-1165, 856).
10. **O4's `route_entrances` cannot serve O5:** it maps each route PLACE to one entrance, the place before it's LAST chain
    value -- for route [153, 154] it gives 154 the entrance 110 (153's ip1077). O5 reads entrances by VISIT (153: 325 and
    316; 154: 304) in its own census and region checks (6.1). O4's function is not edited (G25 pins its output).
11. **O2's dormant-region proof cannot serve 153:** `_dormant_problems` reads a `SWITCH` dispatch only (153 uses
    `SWITCHEX(L1098, 325, L273, 5, L438, 328, L603, 316, L799, 3, L951)`, ip255) and requires every `InitRegion(n)` in
    the default block (153's e23-e25 are also instanced at 328, L603). O5-REGIONS proves dormant by `instanced_at` at
    the route's entrances instead (6.1).
12. **The premises hold at the branch head** (a85e8305, off master e7ca1177): `o4_castle.py --analyse <story-o4>
    --predictions o4_predictions_v1.json` reproduces the archived `o4_report.txt` byte for byte (13941 chars + print's
    newline; 16 checks; PROVEN); `o4_dryrun.py --predictions o4_predictions_v1.json` prints "103/103 cases as
    registered" in 46 s; `--offline-check` 4 PASS; O4's `--preflight` on the live install 15/15 PASS today. Read for O5:
    no mod folder overrides 151, 153 or 154 (`storytrace.stock_overrides`); 151, 153 and 154 are each forked by exactly one
    ForkDonorPatch row (FF9CustomMap: 31244, 31245, 31246, registered O4_ALXC_AC_RST, O4_AC_H2F, O4_AC_FTI); 4600 is
    registered in FF9CustomMap-world; block 3 7 byte-equal of 7; the engine and the override at their pins.
13. **No back-door forbidden pattern is needed.** e28's tag 2 runs `Field(150)` right after its stores (ip38, ip227 ->
    ip235), so a run that wrote them lands in 150 (31243 on F, member(150)): there O4's `off_route` pattern hits; a
    driver walk is backed by its own V11 step row (`landed` 150), a fork's would not be (a finding); a covered run cannot
    hold them (WRITES exact). The critic's "no cause choice in place 153" (problem 7) holds: O5 registers only
    `off_route`.
14. **The race in ticks.** 127 is `WindowSync(2, 128, 127)` (e31 t1 ip663): e31 resumes when its close tween ends (0.09 s
    plus a frame, DialogAnimator.cs:144-173), sets `Map.Bit[231]` (ip670); e2 advances `Map.Byte[24] := 20` the next tick
    and e3 (after e2 in a tick) opens 128 in that tick (ip1713/ip1724): 128 is listed ~1 tick after 127 is GONE. A
    Confirm in 128's opening (0.105 s plus ~2 frames, DialogAnimator.cs:43-47, :61-126) sets SelectChoice to its default
    and closes nothing (Dialog.cs:798-802); one during its type-out completes the text (Dialog.cs:798-808); only after
    both does a Confirm answer at the cursor (0: flags 128 has bit 0 clear, so `sChoose = sChooseInit`, ETb.cs:100-103;
    no choose-param op in 151/153/154). So a stray press needs a decision on a STALE or CLOSING 127 sample plus a stall
    before its send of more than the opening and the type-out. Page-once judges a sample by its GAME frame against
    `ack + page_once_ticks` (a stale sample is held off); the quiet window presses nothing from 127's going to 128's
    publication. The residual -- a press decided on a fresh, legitimately pressable 127 sample that the harness then
    stalls past 128's type-out -- is attributed by its accepted frame (S10), V17 by the driver, never a finding.
15. **Control at the revisit would not read as the game's.** The beat table is keyed `(donor, sc)` (segment_drive.py
    `cell`): without a visit scope, a control grant at 153@316 (impossible in stock; possible on a fork that deviates)
    would run the stair step there and end V7 by the DRIVER -- which VOID-ASYM (a) never reads, so a one-sided fork
    deviation would be re-run away. S13 scopes the cell to visit 1: control at the revisit is V4 by the game.
16. **Master moved after the branch point** (c5e5dd88, ad57966b: `Session.fight` reads a vanished battle as its end):
    session.py's hunks sit at 44, 721 and 7280-7605 (the fight), fakegame.py's at 353, 1037 (`_execute`), 2199-2389
    (battle knobs); `source_pins.json` gained a `FakeGame._execute` row; `REQUIRED_TESTS_O3` two names. None touches
    `choose`, `_take_default_choice`, `_choice_left`, the machine beats or the story trace. The lead's merge: keep both
    sides' `source_pins.json` rows (rows of different names replay independently, `pin_rows_bad`), both
    `REQUIRED_TESTS_O3` additions, and re-run the whole gate (11.2 #8).

---

## 1. Module layout

### 1.1 Files

| File (in `studies/story-trace/` unless a path is given) | | What it holds |
|---|---|---|
| `segment_regress.py` | edit, FIRST (A0) | The gate extended to O4: G0''' (`--capture-o4`), G22-G25 (1.4); G21 over the UNION of the O3 and O4 baselines' `sources`, `--rebaseline-source` over both; `REQUIRED_TESTS_O5` empty; G26 joins at B3, G27 at C2. |
| `research/o4_regress_baseline.json` | new, FIRST (A0) | The captured O4 baseline (LF, `-text`), its `sources` included. |
| `segment_drive.py` | edit (A1-A3) | S10 (the guard), S12 (the run-wide witness), S13 (visit-scoped cells); `stray_answer`'s keyword-only labels (defaults O4's). Each opt-in. |
| `tools/harness/session.py` | edit (A2) | S11: ONE new method, `Session.choose_landed`. `choose`, `select`, `_take_default_choice`, `_choice_left` untouched. |
| `tools/harness/fakegame.py` | edit (B1) | H13 (`story_suppress`), H14 (the `{"visit": knobs}` machine beat, `_VisitBeat`), H15 (its fault knobs). The dispatch lines in `_next_beat` / `_start_machine` and the trace functions are re-baselined by name (G21). |
| `ff9mapkit/tests/test_harness.py` | edit | The tests of 1.2, 3 and 9; the O5 route builder `_o5_route` (test-side, 3.4). No existing test body changes (G21). |
| `o5_hallway.py` | new (C1) | `O5Segment(o4_castle.O4Segment)` and its module functions (1.3). |
| `o5_forks.json` | new (C1) | The chain manifest: O4's, reused (6.4). |
| `o5_dryrun.py` | new (C2) | Synthetic sessions, units and offline mutants (section 8). |
| `o5_rehearse.py` | new (C3) | R-STAIRS, R-FULL, R-WALK-VOID, F-SMOKE, F-PASS, R-RACE (optional) for `tools/play.py` (section 7). |
| `.gitattributes` | edit | `studies/story-trace/research/o4_regress_baseline.json -text` (A0); `studies/story-trace/o5_predictions*.json -text` (C1, before any freeze). |
| `PLAN.md` | edit (C4) | The O5 section: "draft: rehearsals pending, freeze pending". |

NOT edited: `o1_opening.py`, `o1_dryrun.py`, `o2_alexandria.py`, `o2_dryrun.py`, `o2_rehearse.py`, `o3_prima_vista.py`,
`o3_dryrun.py`, `o3_rehearse.py`, `o4_castle.py`, `o4_dryrun.py`, `o4_rehearse.py`, `tools/harness/channel.py`,
every frozen predictions file. `o2_alexandria`, `o3_prima_vista` and `o4_castle` are imported as shared code; their
outputs are the gate (G8-G11, G15-G18, G22-G25). O5's census, region and entrance logic are its own functions in
`o5_hallway.py` (0.2 #10, #11), never edits to O4's.

### 1.2 The shared changes (each opt-in or behaviour-neutral for O1-O4)

**S10 -- THE PRE-CHOICE GUARD** (`pred["guard"]`; decision 3; critic #2, #6, #7). New code beside O4's policy, never a
refactor of it (`quiet_tick`, `note_choice`, `policy_page` stay byte-identical).
```python
GUARD_KEYS = ("donor", "sc", "markers", "choice", "page_once_ticks", "quiet_cap_s", "why")
def guard_of(pred) -> dict | None:
    """pred["guard"] checked STRICT before anything is driven, or None (then nothing below reads it). ValueError on: a
    key not in GUARD_KEYS or one missing (why optional); donor, sc not ints (a bool is no int); markers not a non-empty
    list of non-empty strings; choice not the `match` of exactly one rule of pred["choices"], that rule without
    `take: "default"` and with a `pick` (the guard exists for a non-default pick); page_once_ticks not an int 4-30;
    quiet_cap_s not a number in (0, 10]; pred also carrying `chanbara` (one input policy a segment)."""
```
In `_Drive` (all behind `self.guard is not None`; state `self.gd`, reset at every new visit by rule 3):
- **Rule 6 (a choice published):** `guard_note_choice(st)` -- the quiet window closes; when the published choice is the
  guarded one (`rule_for(...)` is the guard's rule) its FIRST publication frame is kept (`gd["first"]`: the ring's
  earliest sample of it since the visit's first frame). Then the readiness hold (O1's) and the answer through S11.
- **Rule 7 (a page, control off; after the stop pages and `no_pages`):** `guard_page(st)`, in this order:
  (i) the guarded choice was published and the driver never answered it: it left unanswered -> `guard_stray("choice_gone")`;
  (ii) the quiet window is OPEN -> an `observed` row (kind `quiet_page`), V17 (driver), nothing pressed;
  (iii) in the guard's cell (place, published SC, control off) with some listed window holding a marker -- in its
  `phrase_raw` OR its rendered text (the raw holds the whole source from the first sample; the text can grow while it
  types) -> PAGE-ONCE: press only when some marker window's `phrase_raw` is not held off at `st.frame`; a pressed raw
  is held off until the press's ack-read frame + `frames_for_ticks(page_once_ticks)` (O4's S8 b, keyed on the RAW, not
  the text); the press row carries `seq`, `ack_frame`, `button`, `texts`, `raws`; the first such press ARMS the quiet
  window (`gd["quiet"] = {"armed_frame", "open_frame": None, "open_game": None}`);
  (iv) any other page: O1's rule 7 exactly, its press row also carrying `seq` (the attribution reads every Confirm).
  Then O1's wait (`frames_for_ticks(CUTSCENE_PAGE_TICKS)`).
- **`guard_quiet_tick()`** (every poll, rule 3's place where O4 runs `quiet_tick`): armed and not open -> the first ring
  sample after `armed_frame` listing no marker window OPENS it (`open_frame`; `open_game` = `_game_t` of that sample:
  the published `rt`, else the state file's mtime); open -> no choice published within `quiet_cap_s` of GAME time since
  `open_game` (the newest ring sample's game clock) is V14 (game) -- a starved harness slows both clocks alike, so load
  cannot fake it; a backstop of 10 x `quiet_cap_s` of WALL time with the game clock unreadable or frozen is V13
  (driver, "the game clock stalled in the quiet window").
- **`guard_stray(kind)`**: the window [`gd["first"]`, close) -- close the first ring sample after `first` no longer
  publishing the guarded choice -- through `stray_answer(log of this visit, g.channel.events(), steps.jsonl rows,
  first, close, pick=1, label="choice 128", off_pick="with the cursor on 'Let her pass'", reask="the game asked
  choice 128 again though the driver's answer landed")` (`pick` the rule's absolute pick): a Confirm of the driver's own in it -> V17
  (driver: "a Confirm of the driver's own (seq N, page) landed on choice 128 before its answer"); none -> an `observed`
  row of `kind` and then V17 (driver, GAME-OBSERVED: VOID-ASYM (d) reads it) for "choice_gone", V2 (game) for
  "choice_reask". Logged `{"k": "guard_stray", ...}`. Rule 6's once-VOID (V2) of the guarded rule passes through
  `guard_stray("choice_reask")` first (O4's `encore_stray` shape).
- **The `guard` row** (one per guarded choice, written when its answer lands or at a stray): `{"k": "guard", "field",
  "visit", "armed_frame", "open_frame", "choice_first", "choice_close", "presses": [{"seq", "why", "accepted_frame",
  "down_frame", "raws"}]}` -- every press row of the visit with a `seq`, its accepted frame joined from ONE
  `g.channel.events()` read (down = accepted + 1, HarnessAgent.cs:599-607). O5-CHOICE (d) reads it (5.3).
- **`stray_answer`** gains keyword-only `pick=1, label="choice 127", off_pick="with the cursor on Yes", reask="the game
  replayed though the driver confirmed No"` and tests `selected_before == pick`: the defaults reproduce O4's strings
  byte for byte (G24 proves it).

Tests (A3; each into `REQUIRED_TESTS`, G7's selection): `test_segment_guard_of_is_strict` (each refusal once);
`test_segment_guard_presses_the_marker_page_once` (a director re-shows the marker page after the first Confirm -- the
"only finished the type-out" case: re-pressed only once `page_once_ticks` of GAME frames passed; a stale sample
(`Session.state` wrapped to return the previous document once) is never pressed; break: key the hold-off on the text, or
compare wall time); `test_segment_guard_quiet_window_presses_nothing_until_the_choice` (a 30-frame gap between the
marker page's going and the choice: no press row in it, the `quiet` and `guard` rows logged, the choice answered;
break: open the window at the press); `test_segment_guard_page_in_the_quiet_window_is_v17_observed`;
`test_segment_guard_no_choice_within_the_cap_is_v14_on_the_game_clock` (the fake's `rt` frozen while the wall runs:
V13 backstop, not V14; `rt` running: V14); `test_segment_guard_attributes_a_stray_answer` (a mutant driver's Confirm
landing on the choice before its answer: V17 driver; the fake closing the choice with no press of the driver's: V17
with an `observed` row "choice_gone"); `test_segment_stray_answer_keeps_o4s_strings` (pure: O4's three outcomes byte
for byte with the defaults; O5's labels with `pick=1, label="choice 128"`); `test_segment_guard_is_opt_in` (O2- and
O4-shaped predictions: no `gd` state, plain rule 7's press rows carry no `seq`, `choose` -- never `choose_landed` -- on
a non-default pick).

**S11 -- THE VERIFIED LANDING** (`Session.choose_landed`; decision 3; critic #6).
```python
def choose_landed(self, index: int, *, timeout: float = 5.0) -> dict:
    """Select option `index` of the ready choice and Confirm it until the GAME took it -- judged as _take_default_choice
    judges its Confirm (the reads after it, on the game's clock: _choice_left), never by a blind wait. Returns
    {"index", "text", "prompt", "count", "field", "frame", "landed", "confirms", "why"}: landed True when a read after
    a Confirm stopped taking answers, or -- after a read gap -- another window is up (this one was answered); False when
    the window still takes answers after CHOICE_CONFIRMS Confirms, each re-pressed only while the window is ready with
    its cursor on `index` (why "did not land"), or when the cursor left `index` while it waited (why "the cursor left
    the pick: <selected>"; nothing more pressed). Raises ChoiceUnseen, as _take_default_choice does, after a read gap
    whose window reads as this one (_choice_could_be)."""
```
It is `_take_default_choice`'s loop with two differences: the cursor is steered to `index` first (`select`), and a
"waits" verdict re-presses only when the last read still publishes `selected == index`. A prompt still typing is already
ready (DialogAnimator.cs:117-124, Dialog.cs:645-647) and takes the first Confirm as "finish the text" (Dialog.cs:798-808):
the second Confirm answers -- the case a blind `choose()` read as answered and the driver's once-rule then read as V2 by
the GAME. Nothing else in session.py changes.

The driver (rule 6's `answer`, under the guard only): `before = g.channel.seq`; `took = g.choose_landed(index)`
(`ChoiceUnseen` -> V17 driver, "the answer's landing went unseen"); `self.row_choose(before, g.channel.seq, st)` (O4's
S9 rowing, now under the guard too: each press of the answer a `press` row `why` "choose", the Confirm marked `answer`
with `selected_before`); the witness polled at once (S12); `took["landed"]` False -> V17 driver ("the answer N did not
land: <why>"); the answer row's `selected_before` other than `index` -> V13 driver ("the cursor read N, not the pick, as
the answer's Confirm went down: outside input"); else the `choice` row (`took` the record) and `gd["answered"] = True`.
Without the guard: `g.choose(index)` exactly as today (O1's candle, O4's encore).

Tests (A2; G7's selection): `test_segment_choose_landed_lands_once`; `test_segment_choose_landed_repress_while_typing`
(the fake scene's `typing` 40 frames: the first Confirm completes the text, the second lands; `confirms` 2; break: a
blind wait after one Confirm); `test_segment_choose_landed_gives_up_unlanded` (the fake instance's `_scene_press`
wrapped to drop Confirms on the choice: landed False after 3, why "did not land"); `test_segment_choose_landed_stops_
when_the_cursor_moves` (a director moves the cursor to 0 after the select: landed False, why "the cursor left the
pick: 0", no Confirm after); `test_segment_choose_landed_raises_on_an_unseen_landing` (a read stall after the Confirm
with the same window up: `ChoiceUnseen`, nothing pressed again -- O2's starved-confirm pattern).

**S12 -- THE RUN-WIDE WITNESS** (`pred["witness"]`; decision 4; critic #10).
`witness_of(pred)` (strict: keys `input_every_s` -- a positive number at most 0.1 -- and optional `why`); `_Drive`:
`self.witness_pol = witness_of(pred)`, `self.witness_every = (self.witness_pol or self.chanbara or {}).get(
"input_every_s")`; `go()` polls when `self.chanbara is not None or self.witness_pol is not None`; `poll_witness` reads
`self.witness_every` (for O4, its policy's value: today's). The witness callable is `drive(..., witness=)`'s, as
O4's (`o4_castle.input_witness(g)`); a non-neutral reading is an `input` row, then V13. S11 polls it right after the
answer. Tests (A1): `test_segment_witness_of_is_strict`; `test_segment_drive_polls_the_witness_run_wide` (no Chanbara
policy: a stub non-neutral at a page -> V13 and an `input` row; without the key the stub is never called).

**S13 -- VISIT-SCOPED CELLS** (`cell["visit"]`; 0.2 #15). `cell(pred, donor, sc, visit=None)`: a cell carrying `visit`
(an int >= 1: the 1-based position of the visit in `visits`) matches only that visit; a cell without it, any visit
(today's). `_Drive.go` passes `self.at + 1` (rule 8 and the watch rows). The drive's start refuses a `visit` that is no
int >= 1 (a bool refused). `step_of`, O2-GOALS and every caller without the key are unchanged. Tests (A1):
`test_segment_cell_visit_scopes_a_cell` (pure); `test_segment_drive_control_at_another_visit_is_v4` (the fake: a
revisit of the same place at the same SC grants control -> V4, game; the same table without `visit` runs the step:
today's).

### 1.3 `o5_hallway.py`

`O5Segment(o4_castle.O4Segment)`:
- `tag = "O5"`, `predictions = HERE / "o5_predictions_v1.json"`, `manifest = HERE / "o5_forks.json"`, `session_file =
  "o5_session.json"`, `report_file = "o5_report.txt"`, `chain_dir`/`build_dir` O4's (`C:\gd\_ns_playtest\o4\fork`,
  `...\o4\build`), `accept_us_build = False`, `recovery = 4600`, `end_session_warps = True`.
- `core_ids = ("START", "NO-SC", "CHAIN", "RESIDUE", "WRITES", "NULL", "STABLE", "LANDING", "CHOICE", "WALK", "MASKED",
  "STATE", "JOIN")`; `titles` every check's O5 text (the O4 titles' shape).

**Inherited unchanged:** `read_session` and `why_void` (O2's A-NOSTART/A-FORBIDDEN/A-MISMATCH, O3's A-START/A-NOEND,
`cut_row`), `forbidden_check`, `void_asym_check` (O4's (a)-(d)), `start_check` (O3's, data-driven: four residue rows),
`no_sc_check` (O3's), `span_check` (CHAIN), `residue_check`, `writes_check` (O4's EXACT over writes + chain + ladder
`[]`), `null_check`/`stable_check`/`join_check`, `masked_check`, `history`/`suppressed`/`state_check` (O2's),
`text_check` (O4's, over `text_blocks` [3]), `fingerprint_extra` (O4's: override70, text, lang, settings, battle data,
text3, engine), `drive` (O4's: `SD.drive(..., witness=input_witness(g))`).

**Overridden:** `draft()` (section 4; members and names from O4's `campaign.toml`, `route_members` over 153, 154, 151);
`freeze()` (7.3's refusals, then the base's); `offline_extra` (O5-TEXT, O5-CENSUS, O5-REGIONS, O5-GOALS); `build_check`
(the base rule + O5's route build pins, 6.1); `keys_check` (O4's machinery -- O2's on a filtered copy, the `:=var` key,
`start_music` one key -- then O5's route pins instead of the fight pins); `census_check` (O5's own census);
`preflight_extra` and `capabilities` (6.2: P-DONOR and P-DONOR-LOG over 151, 153, 154; no P-GATE, no P-TEXT2);
`core_checks`; `landing_check`, `choice_check`, `walk_check` (5.3); `report_extra` (5.4); `add_arguments`/`handle`
(`--draft`, `--rehearsal-report`).

**Module functions** (pure unless named a reader): `ROUTE_DONORS = (153, 154, 151)`; `route_members(members)` (O4's
shape over 153, 154, 151); `visit_entrances(pred) -> {place: [entrances in visit order]}` (the start's `entrance`, then
each chain key's value for the visit after it: {153: [325, 316], 154: [304]}); `store_census(fields, stock, pred, *,
sites=None, classify=None)` (6.1); `regions_problems(pred, stock)` (6.1); `goals_extra(pred, walkmesh=None)` (6.1);
`route_pins()`; `trace_summary(rows, pred, *, side="S", end_fields=None)` (cut at the stage's end PLACES -- O4's lesson
CI14); `rehearsal_report(run_dir)`; `run(g)`; `main(argv)`.

### 1.4 The regression gate extended to O4 (`segment_regress.py`)

The implementer extends the gate and captures its O4 baseline FIRST (A0), before any shared-code change. The O4 items
import only O4's modules (`o4_castle`, `o4_dryrun`) inside their functions.

`O4S = C:\gd\Dream-World-IX\.harness-runs\20261002-091051-story-o4`, `V1_O4 = HERE / "o4_predictions_v1.json"`
(sha256 `638e43fc...`).

| Item | Check |
|---|---|
| G0''' | `py studies/story-trace/segment_regress.py --capture-o4` writes `research/o4_regress_baseline.json` (LF, `-text`): the full `(checks, report)` of O4S with V1_O4; every `o4_dryrun` session case's `(checks, report)` and "predictions-changed"'s; every unit's `(name, ok, detail)` (`o4_dryrun.units(...)` then `listed_units(...)`, in run_cases's order); `O4.offline_check(V1_O4)`; the tests G19 collects; the HEAD and V1_O4's sha; and `sources`: the AST sha of every test G19 collects and of every function in `FAKE_PINS_O4` (below) -- only names the O3 baseline does not already pin (a name pinned in both is refused). It refuses an existing file, refuses unless G19, G20 and G22-G25's baseline-free halves pass, and takes TWO readings first, refusing when they differ after every temporary root reads `<tmp>` (O3's rule, G0''). |
| G22 | `O4.analyse(O4S, pred_path=V1_O4)`: the report equals `(O4S/"o4_report.txt").read_text(encoding="utf-8")` exactly and the baseline's; the checks the baseline's; PROVEN with 16 checks, all True. |
| G23 | `py studies/story-trace/o4_castle.py --analyse O4S --predictions V1_O4` exits 0 and prints that report (plus print's newline). |
| G24 | Every `o4_dryrun` session case's `(checks, report)` and unit's `(name, ok, detail)` byte-equal to the baseline's (each temporary root `<tmp>`), and `o4_dryrun.run_cases(V1_O4)` returns 0 printing "103/103 cases as registered" (N from the replica: sessions + "predictions-changed" + units). The replica follows `run_cases` step for step (`prepare` -> `pred/`, `sessions/`, the CASES loop through `make_session` and `O4.analyse(d, stock=stock)`, the FROZEN case, `units(pred, stock, scripts, sdir, path, tmp)`, `listed_units(pred, stock, tmp)`), as G17 does O3's. G24 IS O4's VOID-PATH BASELINE: story-o4 holds six covered runs. |
| G25 | `O4.offline_check(V1_O4)` equals the baseline's `[(ok, what, detail)]`: 4 checks, all PASS (reads the O4 build and the install, read-only). |
| G21 (extended) | THE SOURCE PINS over the UNION of the O3 and O4 baselines' `sources`, against one `research/source_pins.json` (append-only; `--rebaseline-source NAME` looks NAME up in either baseline; `pin_row`'s refusals unchanged; its message names "the O3 and O4 baselines' sources"). |
| G26 (from B3) | `pytest tests/test_harness.py -q -p no:cacheprovider -W ignore -k "o5_ or fake_visit or fake_story_suppress"` from `ff9mapkit/`: all passed, 0 failed, 0 skipped, 0 errors; every name in `REQUIRED_TESTS_O5` among them. No baseline: the list is the floor. |
| G27 (from C2) | `o5_dryrun.run_cases` on the frozen O5 predictions once they exist, else the draft: returns 0 printing "N/N cases as registered", N at least `O5_DRYRUN_FLOOR` (the count C2 prints). |

`FAKE_PINS_O4` (the fake O4's tests run on, by qualified name): `FakeGame._start_machine`, `FakeGame._step_machine`,
`FakeGame._frame_once`, `FakeGame._story_row`, `FakeGame._story_start`, `FakeGame._story_stop`,
`FakeGame._story_store`, `FakeGame._warp_writes`, `FakeGame.script_store`, `_machine_knobs`, and every method of
`_Win`, `_Machine`, `_KeyonPairBeat` and `_ChanbaraBeat` (`functions_of` pins `Class.method`; module constants are not
pins -- a constant that changes behaviour fails G19). `_missing()` gains O4S's session and report, V1_O4, the O4
baseline, and from C2 the frozen O5 predictions or O4's `campaign.toml`. Tests O5 adds named `test_segment_*` join
`REQUIRED_TESTS` (G7); every `test_o5_*`, `test_fake_visit_*`, `test_fake_story_suppress_*` joins `REQUIRED_TESTS_O5`.
O5's rehearsal tests are named `test_o5_rehearsal_*` (never "rehearse": G12's selection); no O5 name holds "o4_",
"o3_drive", "o2_" or "o1_".

---

## 2. The drive

### 2.1 The model (keys the driver reads; the rest of the predictions is the analysis's)
- **`table`**: ONE cell, `{"donor": 153, "sc": 1190, "visit": 1, "steps": [the stair step]}` (2.4; S13). Control
  anywhere else -- 154@304, 153@316 (visit 3), 151 before rule 1 -- is V4 (game).
- **`battles: []`** (any battle V10); no `movies`; **`naming: []`** (151's naming is after the cut; one before it is V10).
- **`stop_pages`**: `[{"match": "Env Play()", "why": "153's and 154's ambient error window 56 ('Error Env Play() Slot=n':
  153 e0 t0 ip2304/2338, 154 e0 t0 ip487/521): Byte[13]/[14] arrived as 2 or 9"}]`.
- **`choices`**: the guarded rule and O1's skip net (2.5.1). **`guard`**, **`witness`** (4.10).
- **`route: [153, 154]`, `visits: [153, 154, 153]`, `end_fields: [151]`, `side_ends: {"S": [151], "F": [31244]}`**
  (S6). **`regions`** (4.15): the driver reads role `exit` (153.e28) for its landing judge and the step's `avoid`.
- **`budget`** with `end_row_s` (rule 1 waits for 151's first row) and `settle_s` (rule 6's readiness hold and rule 8's
  settle).

### 2.2 The driver loop for O5 (O4's rules in O4's order; the opt-in additions marked)
Every poll reads `st`, `sc` and `donor = place(fid, members)`. (S12) the witness first.
1. **End** (`fid in self.ends`: real 151 on S, member(151) 31244 on F): the end state (4.9, no Byte[8]), the last
   scan, the end row (151's first trace row, up to `end_row_s`), `reached`. Then the stall watchdog.
2. **Route**: on F a real 151/153/154 is **V19** (game, a finding: `rerun.stop_on`); anything else off the route V11.
3. **Visit**: the order 153 -> 154 -> 153; (S10) the guard's per-visit state reset; (S10) `guard_quiet_tick()`.
4. Naming: V10. 5. A tutorial or a battle: V10.
6. **A choice**: (S10) `guard_note_choice`; O1's readiness hold; the rules (2.5.1); (S11) the verified landing.
7. **A page**: the stop page (V5, nothing pressed); then (S10) `guard_page` -- the gone choice, the quiet window, page-
   once on the marker page -- else O1's press; each press a row with `seq`.
8. **Control held** (settled `settle_s`): (S13) the cell (153, 1190) at visit 1 runs the stair step (2.4); anywhere else
   V4 (game).
9. Otherwise wait (the scripted climb, fades, the scenes' walks).

`out()` keeps its keys (no `zones`/`prompts`: no Chanbara policy); the guard rows are log rows.

### 2.3 Every research beat, and what handles it
The research's `reconciled.route.beats` 1-34 (the rest are past the cut), with the critic's corrections.

| # | Field | Beat | Handled by |
|---|---|---|---|
| 1 | 70 -> 153 | the raw warp; residue SC bytes 0 (0->166), 1 (0->4), FieldEntrance bytes 2 (0->69), 3 (0->1) | `start_run` (O2's); O5-START (a) expects FOUR rows |
| 1 | 153 | Main_Init at 325 (SWITCHEX ip255 -> L273): the prologue ip22-ip200 (ip119 from old 1), `Map.Byte[24] := 1`, InitObject 3/7/31/9/11, InitRegion 26/27/28, InitCode 22 | nothing (WRITES, START) |
| 2-6 | 153 | pages 113, 114 (e7, waited by WaitWindow ip337/ip351), 115 (e3 + WaitWindow ip622), 116 (WindowSync), 117 (e7; e3's WaitWindow(1) ip752) | rule 7 |
| 7 | 153 | THE GRANT: ip755 `Map.Bit[158] := 1`, ip785 `EnableMove()`, no window up | rule 8: settle, then the cell's step |
| 8 | 153 | stage 6, THE STAIR WALK: the ip859 height test every tick; DisableMove ip893 the first tick PSX y <= -450 | the trigger step (2.4) |
| 9 | 153 | stage 17: the teleport ip1466 (2-3 ticks after the loss), the scripted climb at speed 37 | rule 9 (wait) |
| 10 | 153 | 126 (WindowAsync + WaitWindow ip1699) | rule 7 |
| 11 | 153 | 127 (e31 WindowSync ip663, typed at [SPED=2]; holds the marker "let me pass") | rule 7 under S10: page-once, the quiet window from its going |
| 12 | 153 | choice 128 (e3 WindowSync(0, 128, 128) ip1724, cursor 0) -> ip1741 `Bit[3795] := SYSVAR[9]` | rule 6: the guarded rule, `choose_landed(1)` (S11) |
| 13 | 153 | path 1: 141-150 and 130 (eleven windows, e3/e31 alternating) | rule 7 |
| 14-15 | 153 | 131 (e31 Sync), 132, 133 (e3, with walks) | rule 7 |
| 16 | 153 | KEYON pair 134 (window 7) + 135 (window 1), [INCS][TIME=-1]; gate (SYSVAR[8] or 250 ticks) then KEYON ip2336 | rule 7 (Confirm every 4 ticks until both close; an edge before the gate is lost) |
| 17 | 153 | 136 (e31 Sync) | rule 7 |
| 18 | 153 | 137 [NFOC][TIME=20] self-closing; the VIB ops ip2443-2453 (s62 on F) | rule 7 (inert Confirms, recorded `timed`) |
| 19 | 153 | KEYON pair 139 (window 0) + 138 (window 1); KEYON ip2711 | rule 7 |
| 20 | 153 | 140 [NFOC][TIME=20]; the jump; ip2953 `Byte[8] := 0`; DisableMove; Wait(65); ip3150 `Int16[2] := 304`; `Field(154)` ip3158 (F: 31246) | rule 7, then rule 3 |
| 21 | 154 | Main_Init at 304 (SWITCH ip234 -> L232): the prologue (eight new sites), the sound wait, ip279 `Byte[8] := 125`; Zorn e2 the defined player, no `Map.Bit[158]`: no control | nothing; control here V4 |
| 22-26 | 154 | pair 151/152 (KEYON ip215), 153 (Sync), 154 (Sync), pair 155/156 (ip392), walks, pair 157/158 (ip1265) | rule 7 |
| 27 | 154 | ip1520 `Int16[2] := 316`; `Field(153)` ip1528 (F: 31245) | rule 3 |
| 28 | 153 | Main_Init at 316 (L799): the prologue -- ip22/49/138/200 SUPPRESSED, ip57/119 emitted same (0.2 #2); Zorn e18 the defined player: no control | nothing; control here V4 (S13) |
| 29-32 | 153 | 159-164, pair 165/166 (KEYON e18 ip444), walks, 167-172, pair 173/174 (KEYON e20 ip883) | rule 7 |
| 33 | 153 | ip890 `Byte[8] := 0`; Wait(65); ip1077 `Int16[2] := 110`; `Field(151)` ip1085 (F: 31244) | rule 3 is never reached: rule 1 |
| 34 | 151 | THE END: 151 e0 t0 ip22 (31244 on F) -- the cut row; then (after the cut) the prologue, the BGM-load wait, ip315 `Byte[8] := 125` (the race) | rule 1 (per side) and its end row |

### 2.4 The stair walk (cell (153, 1190), visit 1)
**The step** (the walk plan with the critic's corrections; O2's `steps_default` under it):
```json
{"kind": "trigger", "name": "the stairs", "goal": [-1700, 300], "until": {"x_le": -1100},
 "avoid": ["153.e26", "153.e27", "153.e28"],
 "closed_tris": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 14, 15, 16, 17, 18, 19, 20, 21, 23, 24, 28, 32, 33, 34, 35, 38, 39,
                 41, 42, 43, 45, 46],
 "npcs": true, "interrupts": 1, "beat": "stairs", "start": [1105, -78]}
```
- **Who and when:** Zidane (e3, DefinePlayerCharacter e3 t0 ip176), controller radius 80 (SetObjectLogicalSize(20,24,40)
  ip218 x 4, DoEventCode.cs:1498-1531 = the planner's default clearance); granted at ip785 right after 117 closes; Blank
  (e7, (1068, 373)) shown with NO player collision (SetObjectFlags(5) ip770), talk on (118 "Hurry!", no store) -- never
  Confirmed: the driver presses Confirm only on pages (control off).
- **The floor:** `floor_for(153, closed)` = `PlayerWalkmesh(stock 153, closed=the 33)`: the upper corridor (floor 0,
  y -1499) over the hall would otherwise be the first tri `point_on_walkmesh` returns (no route at all on the plain
  mesh: `route153.out`); floor 1 (0xa001) is already closed at mask 255; closing floors [0, 1] would shut 15 real ground
  tris. The same floor on S and F (P-FLOOR pins member(153)'s deployed walkmesh to 153's).
- **The route** (the research's and the critic's re-plan with the harness's own call): (1105, -78) -> (-879, 818) ->
  (-1263, 754) -> (-1700, 300), 3196 u; from (1105 +- 25, -78 +- 25) 3169-3246 u; Blank >= 392 u off it; e26/e27/e28
  >= 350/885/634 u off every leg; the -450 contour crossed at ~(-1482, 527), x <= -1284 on every re-plan. O5-GOALS
  re-derives it (6.1).
- **The evidence** `{x_le: -1100}` (0.2 #9; disputes #3; critic #12): the only open tris at PSX y <= -450 are the west
  stair's (or reachable only through it), all at x <= -1100; no other control loss in stage 6 can stand at x <= -1100
  (e26 x -264..212, e27 -777..777, e28 >= 1739, Blank's talk at 1068); a late loss sample -- the contour (x -1403..-1722),
  the teleport (-1165, 856), the scripted climb (x <= -1100 for ~49 ticks, ~1814 u at 37 u a tick) -- still satisfies
  it. A height predicate would reject the teleport sample (published y ~231); `z_ge: 300` fails ~20 ticks after the
  loss. O5-GOALS (d) proves both halves on the bytes.
- **Hazards:** e28, the back door (live whenever he has control: its tag 2 tests `SYSVAR[2]` alone) -- in `avoid`,
  registered `exit` (to 150, entrance 5), so a loss in it is the landing judge's V11 (driver) and its landing's rows the
  `off_route` pattern's, backed by that step row (0.2 #13). e26/e27, the side scenes (stage 6 only; pages 119-123, no
  store; Walk(1105,-78) ip1230 and the re-grant ip1266) -- in `avoid`, role `scene`; a loss in one is outside every
  exit: `interrupted`, absorbed by `interrupts: 1`; the re-grant runs the same step again (its row's `attempt` 2). The
  hidden colliders e9 (-551, 2104), e11 (30, -1500), e31 (0, 1915; upper) are published (critic #12, HarnessAgent.cs:
  2321-2361) and planned round by `npcs` (>= 1327 u off). No facing gate (`face_gate` None everywhere), no hot-spot.
- **Calibration:** `route_to` calibrates clear of the `avoid` polygons with `key_prior(153)` (every SetControlDirection in
  153 is (248, 0): one basis); F calibrates `prior_for(153)` too (the place).
- **Timeouts:** `timeout_s` 20 (the walk ~2 s); `TRIGGER_WAIT_S` 2 after a walk that ended with control held, then
  `failed` (`attempts` 2 -> V7, driver); the stall watchdog does not run inside an executor.
- **Recovery from mid-walk:** a run stopped mid-walk (V7, V13) stands in 153 on FieldHUD, control held or not: the next
  run's `end_run` warps to 4600 and climbs the ladder (R-WALK-VOID proves it, F7).
- **THE PAIRED-WALK LAW** holds by construction: no story key depends on the path. Stage 6 stores nothing; the side
  scenes store nothing (0.2 #6, #8); the back door's stores make the run VOID V11 (driver). O5-WALK (b) checks that the
  walk windows wrote nothing (5.3).

### 2.5 The pre-choice guard and choice 128

#### 2.5.1 The rules
```json
[{"donor": 153, "sc": [1190], "match": "her face", "pick": "her face", "once": true, "beat": "choice128"},
 {"donor": null, "sc": null, "match": "want to skip", "pick": "default", "once": false, "beat": null}]
```
128's source `[PCHC=2,1][WDTH=...][IMME][ZDNE]` + the prompt + `[CHOO][MOVE=18,0]` + two lines: "her face" is on the
second line only, in every publication variant (prompt published or empty; a line short its first character, O1's
candle; or intact, O4's encore) -> absolute 1 through `active`; never `take: "default"` (V3 by design). The cursor opens
on 0 (0.2 #14). No `cause: "choice"` forbidden pattern in place 153 (critic #7): its backing (index other than
`selected`) would back the route's own answer and turn every run V12.

#### 2.5.2 The marker page and the quiet window
`guard.markers` ["let me pass"] (127's source; O5-KEYS pins it in block 3's US mes 127). 127 is pressed by page-once:
the first press usually lands in its opening (dropped, O4's 0.3 #1) or only finishes its [SPED=2] type-out; it is
pressed again only on a sample of GAME frame >= its hold-off; the press that closes it starts its tween; the quiet
window opens at the first ring sample without 127 and presses nothing until 128 is published; 128's publication
closes it (rule 6 runs before rule 7, so a sample carrying the choice never reaches rule 7). A page between 127's going
and 128 is V17 with an `observed` row; no choice within `quiet_cap_s` of game time is V14.

#### 2.5.3 The answer
Rule 6's readiness hold (`_choice_ready` and the snapshot unchanged for `settle_s` over live frames; while 128 types
its published options may grow, which restarts the hold) then `pick_for` -> (1, the rule) -> S11's `choose_landed(1)`:
`select(1)` (one Down, steered on the published cursor), Confirm, judged on the game's clock; re-pressed only while
still ready with the cursor on 1; rowed; the witness polled; `selected_before` 1 required. Bit[3795] := SYSVAR[9] at
ip1741 is written in the tick 128's WindowSync returns (after its close tween): the trace row follows the answer's down
frame (O5-CHOICE (c)).

#### 2.5.4 The stray attribution
- **The choice gone unanswered** (a page after it, the driver never answered): `guard_stray("choice_gone")` -- a driver
  Confirm in [first, close) is V17 (driver); none: V17 with an `observed` row (game-observed: VOID-ASYM (d) catches it
  on one side; outside input would have stopped the run V13 at the witness first).
- **The guarded rule asked again:** `guard_stray("choice_reask")` -- a driver Confirm on it before its answer: V17; else
  V2 (game: the script asked again after a VERIFIED landing -- impossible in stock, a WindowSync choice is asked once).
- A stray answer can never cover a run: the beat `choice128` is set only by the driver's verified answer with index 1
  (A-BEATS otherwise), so a stray costs a re-run, never a verdict.

#### 2.5.5 The residual
A press decided on a fresh 127 sample past its hold-off is pressable by design (127 still up: the previous press did
not close it). If the harness then stalls longer than 127's close tween + ~1 tick + 128's opening + its type-out
before the press goes down, it lands on 128 at its cursor (0): the guard row's `down_frame` places it inside [first,
close), so the run is V17 (driver), its trace never compared (uncovered). R-STAIRS and R-FULL measure the margin (F2).

#### 2.5.6 Timed and paired windows
Rule 7 presses them as pages (O3/O4's shape): the KEYON pairs take Confirms until the gate passes (<= 250 ticks, 8.3 s;
`no_progress_s` >= 60 covers it); the [TIME=20] [NFOC] windows (137, 140; 175/176 after the cut) are expected inert to
Confirm (O4 measured 150's [TIME] windows so) -- F8 records it.

#### 2.5.7 The fallback (designed, not frozen)
If F2 shows the race open with the guard (a stray inside [first, close) on a guarded run), the lead freezes instead:
the rule `{donor 153, sc [1190], match "her face", pick "Let her pass" (or "et her pass" as F3 publishes it), once,
take "default", beat "choice128"}` (absolute 0, the cursor's own), no `guard` (a stray then answers the same thing),
WRITES' ip1741 key value 0 (a same-value store 0 -> 0, emitted once), CHOICE (b)-(c) on index 0, and the claim's scope
line "the stored choice is the default; a fork that stores a constant 0 passes it". It is a weaker claim (lesson 13).

### 2.6 154@304, 153@316 and the arrival in 151 (no control)
- 154@304 and 153@316 run pages and KEYON pairs only (no `Map.Bit[158]` at 304 or 316: their Main_Init tails' EnableMove
  stays behind it; Zorn e2 / e18 the defined players). Control there is V4 (game) -- at 153@316 through S13. The
  published player is whichever actor is defined (the harness publishes no identity): only Zidane ever has control.
- 151: rule 1 fires on its first poll (31244 on F). The end state is read live but for Byte[8] (151 e0 t0 ip315 writes
  125 right after the BGM-load wait, ip274-294: a race with the read; its value is the trace's last pre-cut write,
  0 at 153 e18 t1 ip890). Nothing is pressed after rule 1: 151 waits on 177 (stage 1), long before the naming (stage
  20). `end_run` then warps to 4600 from 151's FieldHUD.

### 2.7 VOID conditions (each a RouteVoid with its class, cell and attribution; the run is not covered)
| | Condition in O5 | by |
|---|---|---|
| V1 | A choice no rule matches. | game |
| V2 | The guarded rule asked again after its VERIFIED landing, with no Confirm of the driver's own on it (S10). | game |
| V4 | Control held anywhere but the cell (153, 1190) at visit 1; control after its step is done. | game |
| V5 | The stop page ("Env Play()"), nothing pressed. | driver in visit 1 (the warp's start state); game after |
| V7 | The stair step out of attempts (2) or interruptions (1). | driver |
| V10 | A naming screen, a tutorial, a battle. | game |
| V11 | Off the route or its order; a walk into e28 (the landing judge). | game; driver after a walk |
| V12 | A forbidden write the driver's own log backs. | driver |
| V13 | The budget; an instrument stop; outside input anywhere (S12); the cursor not on the pick as the answer's Confirm went down (S11); the game clock stalled in the quiet window (S10). | driver |
| V14 | The watchdog; no choice within `quiet_cap_s` of game time (S10). | game |
| V17 | The choice's answer not proven the driver's: it did not land, its landing went unseen (S11); a Confirm of the driver's own landed on 128 before its answer (S10). GAME-OBSERVED causes, each with its `observed` row: a page in the quiet window; the choice gone with no Confirm of the driver's to explain it. Nothing is pressed after any of them. | driver |
| V19 | On F, a REAL 151, 153 or 154 (a `Field()` the chain did not retarget). A FINDING (`rerun.stop_on`). | game |

V3, V6, V8, V9, V15, V16 and V18 cannot arise (no default-take rule, no watched cell, no wait_sc or climb, no battle,
no fight).

---

## 3. Harness additions (FakeGame only; each opt-in, modelled on the bytes, tested)

No change to `channel` or the agent; S11 is the only session change (1.2). What is missing is a fake that (a) emits
the trace as the engine's sink does and (b) plays O5's visits with the timing the driver must survive. Each choice
below cites the byte or engine line it stands for; each knob's default is the engine's, or where unmeasured the
research's estimate, named so.

### 3.1 H13 -- the sink's same-value suppression (`FakeGame.story_suppress`, default False)
With the knob, `_story_store` keys every store by the engine's SITE -- `(fld, m, src, sid, tag, ip, byte, width, bit)`,
`fld` the field id NOW (StoryTrace.cs:374-376), `m` as `_story_row` computes it -- and per site per epoch keeps
`{"same": bool, "changes": int, "n": int, "last": None, "don": <the row's don>}`: a same-value store is emitted only if
the site has emitted none (`emit = !site.SameEmitted`, :383-390), a change only while `changes < 64`
(ChangeRowsPerSite, :56, :391-394), else counted (`n += 1`, `last = new`, `story_suppressed += 1`, no row,
`story_rows` unchanged -- the file stays exactly the rows the state block counts). The counts flush as `c` rows (`src
sid tag ip byte w bit n last`, the SITE's `fld`/`don`/`m`, the flush's `f`/`p`/`sc`; EmitCounts :540-557): in
`_story_stop` before the `off` row (Stop :187-205) and in `_story_start` when the trace is already on (Start's re-arm:
`Sync`, then `Resync` emits the running epoch's counts, :149-177), the site table cleared at every epoch. The `c` rows
leave in site-creation order (a Python dict; the reader never reads their order). Residue (`_warp_writes`) is never
suppressed (Diff emits every byte, :514). Not modelled: the published `suppressed` counter (`_publish` keeps 0: no
reader reads it; the knob's count is `fake.story_suppressed`). Without the knob the fake emits every store, as today.

Tests (B1): `test_fake_story_suppress_emits_the_first_same_value_per_site` (0 -> 0 twice: one row, then a `c` row n 1;
a change after it: a row; 65 changes: 64 rows, one counted; the same (sid, tag, ip) in ANOTHER field: a new site,
emitted; break: key the site without `fld`); `test_fake_story_suppress_counts_close_the_epoch` (`storytrace 0` writes
the `c` rows before `off`; a second `storytrace 1` writes them before its `arm`; each `c` row's fld/don are its site's;
`storytrace(False)` returns: the file's line count equals the published `rows`); `test_fake_story_suppress_is_off_by_
default` (every store a row, no `c` row: today's).

### 3.2 H14 -- the scripted visit (`{"visit": knobs}`, a machine beat)
A `_VisitBeat(_Machine)` runs ONE field visit from its arrival to its `Field()` as a STEP LIST, per field tick, with
O4's window model unchanged (the opening drop, the close tween, the per-frame UI Confirm, the per-tick KEYON edge:
`_Win`, `_Machine.frame`/`ui`/`publish`). `_next_beat`'s dispatch gains `"visit"` (its one-line change re-baselined by
name, G21) and `_start_machine` picks `_VisitBeat` for it. A scene of four visit beats plays O5's route; each visit
ends by moving the field (a fresh visit: `fake._visit += 1`, as H11's stage 9) and finishing, so the next beat starts in
the new field. Knobs (`_machine_knobs`, strict): `steps` (required), `field_to` map, `donor` (the visit's `fake.donor`:
on F the member's donor, DataPatchers' EffectiveFieldId; None on S), `close_s` 0.09 / `close_frames` 1, `open_s` 0.105 /
`open_frames` 2 (O4's), `wait_scale` 1.0 (scripted waits only; the tests run 0.25), `publish_order` "agent_first", and
H15's faults. `fake.visit_log` keeps every step's start tick and frame.

The step vocabulary (each a dict; every number in O5's builder, 3.4, cites its bytes):
| Step | Meaning (engine) |
|---|---|
| `{"store": [sid, tag, ip, byte, width, value, bit]}` | `fake.script_store` (a script store; H13 decides its row); `value` `"answer"` stores the last choice's answer (ip1741 `SYSVAR[9]`) |
| `{"wait": ticks}` | the script's op_22 / walks, scaled by `wait_scale` |
| `{"place": [x, z]}` | a scripted move of the player (no control): the position published |
| `{"page": mes, "slot": n, "typing_s": s}` | a WindowSync, or WindowAsync + WaitWindow: listed this tick (ETb.NewMesWin), complete after its opening, a Confirm while `typing_s` runs only completes the text (Dialog.cs:798-808), the next closes it; the script resumes the tick it is gone |
| `{"timed": mes, "slot": n, "ticks": t}` | a [TIME=t] window: Confirm-inert, closes itself `t` ticks after it opened (then its tween); the script does not wait |
| `{"pair": [[mes, slot], [mes, slot]], "lag": t, "gate": t}` | H10's KEYON pair: b `lag` ticks after a, the gate `gate` ticks after b, the first Confirm/Special EDGE closes both |
| `{"choice": mes, "slot": n, "header": s, "lines": [...], "typing_s": s, "gap": t, "branch": {"0": [...], "1": [...]}}` | `gap` ticks after the previous window is GONE (0.2 #14: 1), a WindowSync choice: its opening, its type-out (a Confirm completes it), the cursor on 0 (ETb.cs:100-103), Down/Up move it, Confirm answers at the cursor; then its close tween; the answer kept; the branch's steps run |
| `{"grant": [x, z]}` | EnableMove: `fake.control = True` with the player at (x, z) |
| `{"stairs": knobs}` | stage 6 + the side scenes + the back door + stage 17 (below) |
| `{"field": to}` | Field(): the field becomes `field_to[to]` (a fresh visit, control off), the beat finishes |

**The stairs step** (153 e3 t1 stage 6 and its neighbours), per field tick while control is held: (1) the regions'
tag 2 tests in entry order -- `scenes` (153.e26: its quad AND z > 1333 -- the ground half of `f[1] > -100` is the
floor-blind fake's ground; 153.e27: its quad), each live only in stage 6 (`Map.Byte[24] == 6`): the first hit takes
control (DisableMove ip88/ip68), lists the side scene's pages (`scene_pages`, rule 7's), then `{"place": regrant_at}`
(Walk(1105,-78) ip1230) and the re-grant (ip1266), back to stage 6; `back_door` (153.e28: its quad, any stage):
control off, its stores (e28 t2 ip38 `Byte[8] := 25`, ip227 `Int16[2] := 5`), then after `exit_ticks` the field
becomes `back_door_to` and the beat finishes; (2) THE HEIGHT TEST (ip859) -- `height_at(x, z)` (a callable: the real
mesh's interpolated tri height, PSX y) when given, else the `contour` polygon (the floor-blind stand-in): the first tick
he stands at PSX y <= -450 (or inside `contour`) takes control (ip874-915); `teleport_ticks` (3: the stage switch, op_1C,
Wait(1), the Bit[160] test -- an ESTIMATE, R-STAIRS measures) later the player is placed at `teleport` (-1165, 856)
(CreateObject ip1466), then walked along `climb` [(-1419,602), (-1602,298), (-1631,10), (-1631,-140), (-1416,-378),
(-978,-554), (-329,-624)] at `climb_speed` 37 u a tick (SetWalkSpeed(37)); then the next step. With `height_at` the
fake publishes `player[1] = -height` (the published y; the spawn's ~1, the contour's 450).

### 3.3 H15 -- fault knobs (each absent by default)
`store_override` ({ip: value}: a fork that stores another value at a site -- ip1741 0, "a fork that stores a
constant"); `grant_at` ({visit index: [x, z]}: control granted in a visit the bytes never grant -- 154@304, 153@316);
`land_real` (the `field` step lands in the REAL id: a Field() the chain did not retarget, V19's case); `reask` (128
asked again after its answer); `stray_confirm_at_ready` (the fake itself answers 128 at its readiness -- an input the
witness did not see); `cursor_to` ({after_frames: n, index}: the cursor moved by the game n frames after the driver's
select -- outside input's stand-in); `confirm_deaf` (the choice ignores its first k Confirms); `gap_ticks` override
(127 gone -> 128 listed; a huge one: the quiet cap's case); `no_contour` (the height test never fires); `side_scene_at`
(tick n of stage 6: a side scene fires wherever he stands -- a mis-walk's stand-in); `error_window` (Byte[13]
arrived 2: the prologue takes ip97 and lists window 56 "Env Play()": the stop page's case). Test-side, not knobs: a
driver stall (a wrapped `g.press` that sleeps before sending), a stale read (a wrapped `Session.state` returning the
previous document once), a READ stall, a stub witness.

Tests (B1; each names its break): `test_fake_visit_pages_open_type_and_close` (a Confirm in the opening dropped, one in
the type-out completes the text, the next closes it, WindowSync resumes after the tween; break: `open_s` 0);
`test_fake_visit_choice_opens_after_its_gap_on_cursor_zero` (127 gone -> 128 listed `gap` ticks later, cursor 0, a
Confirm in its opening changes nothing, in its type-out completes it, then answers at the cursor; the ip1741 store
carries the answer; branch 0's and branch 1's pages; break: open 128 beside a closing 127); `test_fake_visit_grant_and_
the_stair_contour` (the grant at the spawn; the contour takes control the tick he crosses it; the teleport
`teleport_ticks` later; x <= -1100 for >= 40 ticks after the loss; with `height_at` the published y; break: teleport in
the loss tick); `test_fake_visit_side_scene_and_regrant` (a side scene's pages, the re-grant at the spawn, stage 6
resumed; break: re-grant before the pages close); `test_fake_visit_back_door_stores_then_leaves` (e28's two stores,
then the field change; break: leave first); `test_fake_visit_keyon_pairs_and_timed_windows` (an edge before the gate
lost, one after closes both; a [TIME=20] window ignores Confirm and closes itself); `test_fake_visit_faults` (one
assertion per H15 knob); `test_fake_visit_sets_the_members_donor` (F rows' `don` the donor: no A-MISMATCH).

### 3.4 The O5 route builder (test-side `_o5_route(side, fields, **knobs)`)
Four visit beats from the bytes (`stages153.out`, `stages154.out`, `win_*.txt`; slots as the scripts open them). Window
TEXTS are placeholders (`"153 mes 113"`, raw `"[STRT=0,0]153 mes 113"`), each distinct, except where the driver
matches: 127 holds "let me pass", 128's lines are "Let her pass" / "Examine her face" (a knob for the first-character
variant), window 56 holds "Env Play()". Fixture fields: S 30820 ("153"), 30821 ("154"), 30810 ("151") -- the
`game` fixture registers these three -- and 30830 ("150", the back door); F 31245, 31246, 31244, 31243. A test-side
`_o5_register(game)` (`_o4_register`'s shape: FieldScene lines appended to the fixture's own
`FF9CustomMap/DictionaryPatch.txt`) registers 30830 and the four F ids under `_O5_NAMES`
({"31243": "O5_HALL", "31244": "O5_SEAT", "31245": "O5_H2F", "31246": "O5_ENT"}); the `game` fixture itself is not
edited. Members {31245: 30820, 31246: 30821, 31244: 30810, 31243: 30830}.
- **153@325:** stores e0 t0 ip22, 49, 57, 119, 138, 200 (Bit[191] 0, Bit[184] 0, Int16[9] -1, Byte[13] 0, Int16[11] -1,
  Byte[14] 0); wait 10; place (1105, -78); pages 113 (slot 1), 114 (1), 115 (0), 116 (1), 117 (1); grant (1105, -78);
  stairs; wait 10 (ip1658); page 126 (0, typing 0.3 s); page 127 (2, typing 0.5 s: [SPED=2], an ESTIMATE); choice 128
  (slot 0, gap 1, typing 0.5 s, ESTIMATE) then store e3 t1 ip1741 `Bit[3795] := answer`; branch "1": pages 141 (0),
  142 (2), 143 (0), 144 (0), 145 (2), 146 (0), 147 (2), 148 (0), 149 (2), 150 (0), 130 (0); branch "0": pages 129 (0),
  130 (0); page 131 (2); 132 (0); 133 (0); pair [[134, 7], [135, 1]] lag 20 gate 40; page 136 (2); timed 137 (2, 20);
  wait 35; pair [[139, 0], [138, 1]] lag 5 gate 40; timed 140 (1, 20); wait 40; store e3 t1 ip2953 `Byte[8] := 0`; wait
  65; store e3 t1 ip3150 `Int16[2] := 304`; field "154".
- **154@304:** stores e0 t0 ip26, 53, 61, 123, 142, 204; wait 10 (RunSoundCode + the SYSVAR[3] wait); store ip279
  `Byte[8] := 125`; wait 20; pair [[151, 2], [152, 3]]; page 153 (2); page 154 (3); pair [[155, 2], [156, 3]]; wait 60;
  pair [[157, 2], [158, 3]]; wait 35; store e2 t1 ip1520 `Int16[2] := 316`; field "153".
- **153@316:** stores e0 t0 ip22, 49, 57, 119, 138, 200; wait 20; pages 159 (6), 160 (5), 161 (6), 162 (5), 163 (6), 164
  (5); pair [[165, 5], [166, 6]]; wait 60; pages 167 (5), 168 (6), 169 (5), 170 (6), 171 (5), 172 (6); pair [[173, 5],
  [174, 6]]; store e18 t1 ip890 `Byte[8] := 0`; wait 65; store e18 t1 ip1077 `Int16[2] := 110`; field "151".
- **151@110:** stores e0 t0 ip22, 49, 57, 119, 138, 200; wait 10 (the BGM-load wait); store ip315 `Byte[8] := 125`; timed
  175 (4, 20); timed 176 (5, 20); page 177 (an end the driver never presses).
The stores are the predictions' sites (C1's `test_o5_hallway_route_builder_matches_the_keys` compares the builder's
store list with the draft's writes, chain, masked and start rows: one source of truth).

---

## 4. Predictions (draft v1: `O5Segment.draft()`)

### 4.1 Top level
```json
{"version": 1,
 "what": "O5: 153@1190 (warp, entrance 325; EVT_ALEX1_AC_H2F) -> the stairs -> choice 128 'Examine her face' -> 154@304 (EVT_ALEX1_AC_ENT_2F) -> 153@316 -> Field(151) (EVT_ALEX1_AC_SEAT_R), SC 1190; stock vs the alxc disc-1 chain as O4 deployed it (route members 31244-31246; PLAN.md, O5) -- a US session",
 "rehearsals": [],
 "order": ["S", "F", "S", "F", "S", "F"], "min_covered": 2, "rerun": {"max": 2, "stop_on": ["V19"]},
 "budget": {"run_s": 600, "run_min_s": 300, "session_s": 3600, "settle_s": 1.0, "no_progress_s": 60, "end_row_s": 10.0},
 "start": {"S": 153, "F": 31245}, "entrance": 325, "scenario": 1190, "lang": "us",
 "end_field": 151, "end_fields": [151], "side_ends": {"S": [151], "F": [31244]},
 "route": [153, 154], "visits": [153, 154, 153], "stock_fields": [151, 153, 154],
 "members": {"31240": 64, "...": "...", "31259": 167}, "names": {"31240": "O4_AC_AST", "...": "..."},
 "text_block": 3, "text_blocks": [3], "recovery": 4600, "cut_start": true,
 "start_first": "4.6", "start_music": "4.6", "start_residue": [[0, 0, 166], [1, 0, 4], [2, 0, 69], [3, 0, 1]],
 "residue_after_start": [], "sc_bytes": [0, 1], "ladder": [], "entrance_bytes": [2, 3], "chain": "4.3",
 "writes": "4.4", "error_path": "4.5", "forbidden_sites": "4.5", "dead": "4.5", "inert": "4.5",
 "start_dependent": [], "noise": [], "forbidden": "4.8", "landing": "5.3", "choice": "5.3", "walk": "5.3",
 "end_state": "4.9", "battles": [], "stop_pages": ["2.1"], "regions": "4.15", "hotspots": {}, "table": ["2.4"],
 "steps_default": "4.15", "choices": ["2.5.1"], "naming": [], "beats": ["stairs", "choice128"],
 "guard": "4.10", "witness": "4.10", "route_pins": "4.14", "pattern": "4.16",
 "settings": "4.13", "override70": "4.13", "derived": "4.13", "engine": "4.13"}
```
- `members`/`names` are O4's twenty (`chain_from_campaign` on O4's `campaign.toml`, exactly O4's donors);
  `route_members` over 153, 154, 151 derives 31245, 31246, 31244 (printed by `--offline-check`, never assumed).
  P-DEPLOY, P-EB, P-FLOOR and the fingerprint read all twenty.
- `start_residue`: SC 1190 = 0x04A6 writes bytes 0 (0 -> 166) and 1 (0 -> 4); FieldEntrance 325 = 0x0145 writes bytes 2
  (0 -> 69) AND 3 (0 -> 1): FOUR rows (StoryTrace.cs Diff per byte, :514-527; O2-O4 had three).
- `start_dependent: []`: no key's VALUE depends on the start (constants and the pick); the ROW PATTERN does (4.16, 5.4).
- `ladder: []` with `sc_bytes`: O5-NO-SC is O3's `no_sc_check` (O2's LADDER on an empty ladder could not fail).

### 4.2 No SC rung
No `Global.UInt16[0]` store in 151 or 153-154 (the census, 6.1); the reads 153 e0 t0 ip232 (`SC > 1900`: false) and 151
e0 t0 ip461 (`< 12000`, after the cut) take the same branch from the raw warp and from a true O4 end (both 1190).

### 4.3 The FieldEntrance chain (`Global.Int16[2]`; O5-CHAIN; the first `old` is 325, the warp's entrance)
| # | donor | sid | tag | ip | off | value | what |
|---|---|---|---|---|---|---|---|
| 1 | 153 | 3 | 1 | 3150 | 2742 | 304 | stage 30, then `Field(154)` ip3158 |
| 2 | 154 | 2 | 1 | 1520 | 1409 | 316 | stage 6, then `Field(153)` ip1528 |
| 3 | 153 | 18 | 1 | 1077 | 953 | 110 | stage 114 (visit 3), then `Field(151)` ip1085 |

### 4.4 Registered writes (O5-WRITES: every covered run's keys are EXACTLY these and the chain)
| donor | sid | tag | ip | off | target | value | op | what |
|---|---|---|---|---|---|---|---|---|
| 153 | 0 | 0 | 57 | 51 | Int16[9] | -1 | := | ambient (visit 1 from 643; visit 3 emitted same) |
| 153 | 0 | 0 | 119 | 113 | Byte[13] | 0 | := | ambient (visit 1 from 1: `start_music`; visit 3 emitted same) |
| 153 | 0 | 0 | 138 | 132 | Int16[11] | -1 | := | ambient (visit 3 suppressed) |
| 153 | 0 | 0 | 200 | 194 | Byte[14] | 0 | := | ambient (visit 3 suppressed) |
| 153 | 3 | 1 | 1741 | 1333 | Bit[3795] | 1 | :=var, rvalue `B_SYSVAR[9]` | **THE STORED CHOICE** (0 -> 1) |
| 153 | 3 | 1 | 2953 | 2545 | Byte[8] | 0 | := | stage 30 (old 125 after the raw warp) |
| 154 | 0 | 0 | 61 | 51 | Int16[9] | -1 | := | ambient |
| 154 | 0 | 0 | 123 | 113 | Byte[13] | 0 | := | ambient |
| 154 | 0 | 0 | 142 | 132 | Int16[11] | -1 | := | ambient |
| 154 | 0 | 0 | 204 | 194 | Byte[14] | 0 | := | ambient |
| 154 | 0 | 0 | 279 | 269 | Byte[8] | 125 | := | the 304 branch, after the sound wait |
| 153 | 18 | 1 | 890 | 766 | Byte[8] | 0 | := | stage 114 (visit 3) |

12 writes + 3 chain = **15 keys a run**, beside the masked prologue rows (Bit[191] ip22/ip26, Bit[184] ip49/ip53:
`boot_scratch`, `field_menu_guard`). The `:=var` key's value 1 rests on O5-CHOICE (the driver's verified pick), never
computed here (O4's score key shape: O4-KEYS reads its `rvalue` in the statement `Global.Bit[3795] B_SYSVAR[9] B_LET`).
EXACT for O4's reason: the key set is small and fully enumerated by the bytes (O5-CENSUS classifies every store site of
153 and 154; O5-KEYS proves every listed site). R-FULL must show the exact set before the freeze (F4).

### 4.5 The error path, the forbidden sites, the dead sites, the inert functions (registered; never expected)
- `error_path` (an incoming Byte[13]/[14] of 2 or 9): 153 e0 t0 ip97/91 `Byte[13] := 9`, ip178/172 `Byte[14] := 9`,
  ip2314/2308 `Byte[13] := 0`, ip2348/2342 `Byte[14] := 0` (window 56's resets); 154 e0 t0 ip101/91, ip182/172,
  ip497/487, ip531/521 (the same four). A 153 row at visit 1 is the start's fault (A-START, V5 driver); later, a fork
  deviation.
- `forbidden_sites`: 153 e28 t2 ip38/8 `Byte[8] := 25`, ip227/197 `Int16[2] := 5` (the back door; 0.2 #13).
- `dead` (each `:=`; why false on the route): 153 e0 t0 ip41/35 `Int16[2] := 10000` (behind `Bit[184] == 1`), ip130/124
  `Byte[13] := 1` and ip211/205 `Byte[14] := 1` (the else of `Int16[9] < 0` / `Int16[11] < 0`, just set -1), ip243/237
  `Int16[2] := 3` (behind ip232 `SC > 1900`), ip1188/1182 and ip1260/1254 `Byte[8] := 125` (the default entrance's
  branch, L1098); 153 e3 t1 ip3168/2760 `Byte[8] := 0` and ip3288/2880 `Int16[2] := 0` (the flashback: ip2942
  `Int16[2] != 3` false only at entrance 3); 154 e0 t0 ip45/35, ip134/124, ip215/205 (the same three shapes).
- `inert` (FUNCTION-level, proven by `instanced_at` at EVERY route entrance of the field, 6.1): `{"donor": 153, "sid":
  s, "tags": "*"}` for s in 23, 24, 25, 32 (instanced at 328 and the default only) and `{"donor": 153, "sid": 15, "tags":
  "*", "shared_by": [32]}` (a shared entry: proven by its callers, 6.1); `{"donor": 154, "sid": s, "tags": "*"}` for s
  in 5, 8, 9, 10 (instanced at 315 / the default only).

### 4.6 The start (O5-START)
```json
"start_first": {"donor": 153, "m": 1, "src": "eb", "sid": 0, "tag": 0, "ip": 22, "off": 16, "target": "Global.Bit[191]",
                "value": 0, "op": ":=", "what": "153's Main_Init: its first store (emitted same: a new site)"},
"start_music": {"donor": 153, "m": 1, "src": "eb", "sid": 0, "tag": 0, "ip": 119, "off": 113, "target": "Global.Byte[13]",
                "value": 0, "op": ":=", "old": 1,
                "what": "153's ambient branch from the warp's Byte[13] 1 (field 70's prologue :=1 at ip130; the warp leaves 70 before ip475's :=2)"}
```
The warp window and `old: 1` are O2-O4's (fifteen runs measured the same start), under the override P-OVERRIDE pins
(critic #8). A 2 would take ip97 and window 56: A-START.

### 4.7 Noise: none
No `SYSVAR[0]` read in 151/153/154; no battle, no ATE; the walk's path writes nothing (2.4); the choice's value is the
frozen pick. `noise: []`: NULL and STABLE set nothing aside.

### 4.8 Forbidden
```json
[{"off_route": true, "cause": "walk",
  "why": "a write off the route: S, a place outside [153, 154] + [151]; F, a field that is neither a member whose donor is on the route nor F's own end field (real 151/153/154 on F: an un-retargeted Field() or an engine id leak; 150/31243 after the back door, backed by its V11 step row)"}]
```
No back-door pattern (0.2 #13), no `cause: "choice"` pattern (critic #7).

### 4.9 End state (read live on arrival in 151 / member(151); O5-STATE (b))
```json
{"Global.UInt16[0]": 1190, "Global.Int16[2]": 110, "Global.Bit[3795]": 1,
 "Global.Byte[13]": 0, "Global.Byte[14]": 0, "Global.Int16[9]": -1, "Global.Int16[11]": -1,
 "Global.Bit[191]": 0, "Global.Bit[184]": 0,
 "Global.Byte[6]": 0, "Global.UInt16[19]": 0, "Global.UInt16[21]": 0, "Global.Byte[303]": 0, "Global.Byte[4]": 0,
 "Global.Byte[17]": 0, "Global.Byte[18]": 0, "Global.Byte[475]": 0, "Global.Bit[3815]": 0, "Global.Bit[3793]": 0,
 "Global.Bit[3717]": 0, "Global.Bit[3718]": 0, "Global.Int16[469]": 0, "Global.Byte[472]": 0, "Global.Byte[206]": 0}
```
Nine the route leaves, fifteen untouched since New Game. Byte[8] is NOT here (critic #4: 151 ip315 races the read);
its end value is the last pre-cut write in every covered run's trace (153 e18 t1 ip890 := 0), held by STATE (a)'s
ordered history `[153 e3 t1 0, 154 e0 t0 125, 153 e18 t1 0]`. Bit[3855]/Bit[3854] (153@328's) are not here either.
Stable through 151's arrival: its prologue rewrites equal values (0.2 #2), and nothing else stores before page 177.

### 4.10 The guard and the witness (S10, S12; F2, F6 and F9 re-size them)
```json
"guard": {"donor": 153, "sc": 1190, "markers": ["let me pass"], "choice": "her face", "page_once_ticks": 10, "quiet_cap_s": 4.0,
          "why": "153 e31 t1 ip663 WindowSync(2,128,127) -> ip670 Map.Bit[231] := 1 -> e2 t1 Map.Byte[24] := 20 -> e3 t1 ip1724 WindowSync(0,128,128), ~1 tick after 127 is gone: a Confirm decided on a stale or closing 127 can land on 128 at its cursor (0)"},
"witness": {"input_every_s": 0.05, "why": "Bit[3795] stores the player's answer: outside input at the choice would store another value while the driver logs its pick (critic #10)"}
```

### 4.11 Coverage beats
`stairs`: set by the stair step's `done`. `choice128`: set by the guarded rule's VERIFIED answer (S11). Plus `end ==
"reached"`. O5-WALK and O5-CHOICE re-read both from the rows.

### 4.12 Budget and recovery
Estimated ~4.7 min a run (the research: ~37 pages with pick 1, 7 KEYON pairs, 2 timed windows, 1 walk, the scripted
waits; ~4 s a page, calibrated on O4's 150). Drafts: `run_s` 600, `run_min_s` 300, `session_s` 3600, `settle_s` 1.0,
`no_progress_s` 60 (a pair's gate is <= 8.3 s), `end_row_s` 10; the guard's `quiet_cap_s` 4.0. F6 replaces every one.
Recovery is `end_run` (O4's): the warp to 4600 first (from 153 mid-walk, from a page, from 154, from 151 -- all FieldHUD),
then the ladder; the session ENDS through `end_run` (`end_session_warps`). F7 proves it from mid-walk.

### 4.13 Settings, the New-Game override, the engine, the derived facts
O4's frozen values, unchanged: `settings` (28 keys: [Battle], [Cheats], [Hacks] incl. `DisableNameChoice` 0, [Control]
incl. `AlwaysCaptureGamepad` 1 and `SwapConfirmCancel` 0, [Graphics] `FieldTPS` 30), `override70` {FF9CustomMap-world:
2ce8887e...}, `engine` {x64, x86: ba976242...}, `derived` (cfg.control 0, 30 ticks a second). `freeze` refuses an
engine that is not the live DLLs'.

### 4.14 The route pins (O5-KEYS (b): the bytes the driver, the guard and the FakeGame rest on)
`route_pins`, each `[donor, sid, tag, ip, eb-src text]`, compared EXACTLY with the stock US script's instruction text:
| what | site | text |
|---|---|---|
| the dispatch | 153 e0 t0 ip255 | `SWITCHEX(L1098, 325, L273, 5, L438, 328, L603, 316, L799, 3, L951)` |
| the SC read | 153 e0 t0 ip232 | `SET({Global.UInt16[0] const(1900) B_GT B_EXPR_END})` |
| the regions at 325 | 153 e0 t0 ip302, 305, 308 | `InitRegion(26, 0)`, `InitRegion(27, 0)`, `InitRegion(28, 0)` |
| the grant | 153 e3 t1 ip752, 755, 785 | `WaitWindow(1)`, `SET({Map.Bit[158] const(1) B_LET B_EXPR_END})`, `EnableMove()` |
| the height test | 153 e3 t1 ip859 | `SET({obj(uid=255).f[1] const(65086) B_GT B_EXPR_END})` |
| the loss | 153 e3 t1 ip874, 893 | `SET({Map.Bit[158] const(0) B_LET B_EXPR_END})`, `DisableMove()` |
| the teleport | 153 e3 t1 ip1466 | `CreateObject(64371, 856)` |
| 127 | 153 e31 t1 ip663, 670 | `WindowSync(2, 128, 127)`, `SET({Map.Bit[231] const(1) B_LET B_EXPR_END})` |
| 128 | 153 e3 t1 ip1713, 1724 | `SET({Global.Int16[2] const(3) B_NE B_EXPR_END})`, `WindowSync(0, 128, 128)` |
| the stored answer | 153 e3 t1 ip1741, 1749 | `SET({Global.Bit[3795] B_SYSVAR[9] B_LET B_EXPR_END})`, `SET({Map.Byte[27] B_SYSVAR[9] B_LET B_EXPR_END})` |
| the pairs | 153 e3 t1 ip2336, 2711; 154 e2 t1 ip215, 392, 1265; 153 e18 t1 ip444; e20 t1 ip883 | `SET({const4(131072) B_KEYON B_NOT const4(524288) B_KEYON B_NOT B_ANDAND B_EXPR_END})` |
| the VIB ops (s62) | 153 e3 t1 ip2443, 2448, 2453 | `RunVibrationTrack(0, 0, 1)`, `RunVibrationTrack(0, 1, 0)`, `ActivateVibration(1)` |
| e26 | 153 e26 t2 ip38, 58, 88, 110 | the ground/z test (0.2 #8), `SET({Map.Byte[24] const(6) B_EQ B_EXPR_END})`, `DisableMove()`, `SET({Map.Byte[24] const(7) B_LET B_EXPR_END})` |
| e27 | 153 e27 t2 ip38, 68, 90 | `SET({Map.Byte[24] const(6) B_EQ B_EXPR_END})`, `DisableMove()`, `SET({Map.Byte[24] const(14) B_LET B_EXPR_END})` |
| e28 | 153 e28 t2 ip30, 38, 83, 227, 235 | `SET({B_SYSVAR[2] B_EXPR_END})`, `SET({Global.Byte[8] const(25) B_LET B_EXPR_END})`, `ExitField()`, `SET({Global.Int16[2] const(5) B_LET B_EXPR_END})`, `Field(150)` |
| the exits | 153 e3 t1 ip3158; 154 e2 t1 ip1528; 153 e18 t1 ip1085 | `Field(154)`; `Field(153)`; `Field(151)` |
| 154's dispatch | 154 e0 t0 ip234 | `SWITCH(304, L392, L232)` |
| the end row and the race | 151 e0 t0 ip22, 232, 315 | `SET({Global.Bit[191] const(0) B_LET B_EXPR_END})`, `SET({Global.Int16[2] const(110) B_EQ B_EXPR_END})`, `SET({Global.Byte[8] const(125) B_LET B_EXPR_END})` |

Plus `route_mes` (block 3, US, the asset the engine reads): mes 127's source holds every `guard.markers` string; mes
128's `[CHOO]` lines hold "her face" in exactly one line (the second) and its source opens `[PCHC=2,1]`; mes 56 holds
"Env Play()". The guard, the rule and the stop page can then never drift from what the game shows.

### 4.15 The regions, the table's defaults
```json
"regions": {
 "153.e28": {"points": [[2850, 347], [2850, -13], [1739, -74], [1739, 406]], "role": "exit", "to": 150, "entrance": 5, "face_gate": null},
 "153.e26": {"points": [[-227, 3000], [200, 3000], [212, 935], [-264, 924]], "role": "scene", "stage": 6,
             "why": "side scene A: tag 2 on the ground and z > 1333 at stage 6, Map.Byte[24] := 7; no global store; re-grant e3 t1 ip1266"},
 "153.e27": {"points": [[-777, -2348], [777, -2348], [777, -900], [-777, -900]], "role": "scene", "stage": 6, "why": "side scene B: Map.Byte[24] := 14"},
 "153.e23": {"points": [[-227, 3000], [200, 3000], [212, 935], [-264, 924]], "role": "dormant", "entrances": [325, 316]},
 "153.e24": {"points": [[2850, 347], [2850, -13], [1739, -74], [1739, 406]], "role": "dormant", "entrances": [325, 316]},
 "153.e25": {"points": [[-777, -2348], [777, -2348], [777, -900], [-777, -900]], "role": "dormant", "entrances": [325, 316]},
 "154.e8": {"points": [[2222, -5555], [-2222, -5555], [-2222, -4080], [2222, -4080]], "role": "dormant", "entrances": [304]},
 "154.e9": {"points": [[-3777, -999], [-3777, -3111], [-1888, -3111], [-1888, -999]], "role": "dormant", "entrances": [304]},
 "154.e10": {"points": [[3777, -999], [3777, -3111], [1888, -3111], [1888, -999]], "role": "dormant", "entrances": [304]}}
```
e23/e24/e25 are e26/e28/e27's twin quads: registered `exit`, they would mislabel a side-scene loss as a door (the
research's dispute 13). `steps_default` is O2's exactly (`attempts` 2, `interrupts` 1, `timeout_s` 20, `tolerance` 45,
`exit_slack` 40, `exit_wait_s` 5.0, `npcs` true, `overlay_ok` false, `immediate` false, `settle` null, `lunge_ticks` 0,
`min_depth` 40, `confirm_s` 4.0, `climb` O2's).

### 4.16 The emitted row pattern (the suppression model's prediction; F4 measures it)
`pattern`, the analysis's report reads it, no check judges it but LANDING (b)'s re-entry row (5.3):
| visit | emitted `w` rows (in order) | suppressed (counted) |
|---|---|---|
| 153@325 | e0 t0 ip22 (masked, same), ip49 (masked, same), ip57 (643 -> -1), ip119 (1 -> 0), ip138 (same), ip200 (same); e3 t1 ip1741 (0 -> 1), ip2953 (125 -> 0), ip3150 (325 -> 304) | none |
| 154@304 | e0 t0 ip26 (masked), ip53 (masked), ip61, ip123, ip142, ip204 (all same), ip279 (0 -> 125); e2 t1 ip1520 (304 -> 316) | none |
| 153@316 | e0 t0 ip57 (same: the visit's FIRST emitted row), ip119 (same); e18 t1 ip890 (125 -> 0), ip1077 (316 -> 110) | e0 t0 ip22, ip49, ip138, ip200 |
| 151@110 | e0 t0 ip22 (THE CUT) | -- |
The epoch's close: four `c` rows of place 153 (n 1 each; ip138 last -1, ip200 last 0), kept by the cut. Totals before
the cut: 21 `w` rows (17 unmasked), 4 `c` rows. Each `c` row's `last` is a key some emitted row of the run carries, so
STATE (a)'s suppressed set holds no key beyond them (o2_alexandria.py `suppressed`).

---

## 5. Checks (O5's analysis)

### 5.1 Reading a run: the COVERED rule
O4's rule (skipped, install changed, the drive did not reach the end, a beat not done, no or an incomplete trace,
A-NOSTART, a BACKED forbidden hit, A-MISMATCH, A-START on 153's error path, A-NOEND), unchanged. A drive VOID carries
its V-class (2.7). The report lists every uncovered run's reasons per side.

### 5.2 The cuts (per side, frozen places)
`cut_at_start` from 153's first `w` row (place 153: real 153 on S, member(153) on F; the four residue rows in 70 go to
`pre`); `cut_at_end` at the first `w`/`r` row in an end PLACE -- `end_places(pred, side)`, [151] on both sides (S6).
Kept after the cut: the epoch rows and the `c` rows of places 153 and 154 (0.2 #2). On F the end place 151 is
member(151)'s; LANDING (d) reads the cut row's `fld` (31244 on F, 151 on S); a run that entered real 151 on F is VOID by
rule 2 first (V19).

### 5.3 The checks, in order, each with the mutant that makes it fail (section 8 registers every one)
**All-run checks** (every run with a readable trace, judged even when COVER is short):
- **O5-FORBIDDEN** (O2's). Mutant: back-door-unbacked-F.
- **O5-VOID-ASYM** (O4's (a)-(d); `stop_on` [V19]). Mutants: v19-one-F (a, c), v2-reask-one-F (a), v4-control-154-F
  (a), v4-control-316-F (a), v7-walk-all-F (b), observed-quiet-page-one-F (d alone), observed-choice-gone-one-F (d
  alone); and the PASS cases observed-quiet-page-each-side, v13-input-one-F, v17-stray-one-S.

**Then:** **O5-FROZEN**, **O5-COVER**. Mutants: predictions-changed; stairs-beat-missing, choice-beat-missing.

**Core checks** (over the covered runs):
- **O5-START** (O3's): (a) `pre` is exactly the FOUR residue rows; (b) the first `w` row in place 153 is `start_first`,
  raw; (c) the first Byte[13] row in place 153 is ip119 `:= 0` from old 1. Mutants: start-residue-three (S: byte 3's
  row missing -- O2-O4's three-row contract would pass it), start-residue-wrong, front-cut-write, start-first-missing,
  start-music-old-wrong.
- **O5-NO-SC** (O3's `no_sc_check`): no kept row over bytes 0-1 after the start. Mutants: sc-write-fork (a `cs`
  UInt16[0] row in 154 on F), sc-harness-poke-both (NO-SC alone).
- **O5-CHAIN** (O2's `span_check` over bytes 2-3 from 325): exactly 4.3, in order, each from the last. Mutants:
  chain-dropped-fork, chain-first-old-wrong (alone).
- **O5-RESIDUE**: none after the start. Mutant: residue-after-start.
- **O5-WRITES (exact)**: every covered run's keys outside the noise ARE the 15 (O4's `writes_check`). Mutants:
  fork-drops-a-write (no 154 ip279 on F), writes-extra-symmetric (both: 153 e3 t1 ip3168's flashback store),
  inert-row-both (both: 153 e32 t0 ip718 `Bit[3855] := 1`).
- **O5-NULL**, **O5-STABLE** (O1's, no noise). Mutants: NULL -- fork-drops-a-write, bit3795-zero-F; STABLE --
  extra-key-one-F (one F run of three holds the ip3168 store: STABLE F, WRITES F, STATE F; NULL passes).
- **O5-LANDING** (O4's shape over O5's crossings; every covered run, each clause named):
  - (a) every field-mode `w`/`c` row ran in its place's own field (member(place) on F) and stands in a route place
    [153, 154];
  - (b) the crossings, on field-mode `w` rows at their places' own fields: the run holds `landing.exit153` (153 e3 t1
    ip3150) and the next row after it is `landing.enter154` (154 e0 t0 ip26 `Bit[191] := 0`: 154 loaded by 153's
    Field(154)); it holds `landing.exit154` (154 e2 t1 ip1520) and the next row after it is `landing.enter153b` (153 e0
    t0 ip57 `Int16[9] := -1`, old -1: the revisit's first EMITTED row under this start's suppression pattern, 0.2 #2 --
    start-scoped, 5.4); no row of place 154 after `enter153b`;
  - (c) the last field-mode `w` row before the cut is `landing.exit153b` (153 e18 t1 ip1077, by PLACE), and the run's
    `end` log row names the side's end field (151 on S, 31244 on F);
  - (d) THE END PER SIDE: the cut row is `landing.end_row` (151 e0 t0 ip22 `Bit[191] := 0`) at `fld` the side's end
    field;
  - (e) every F digest records no seam and no seam key (the chain is closed from member(153) to member(151)).
  Mutants: lands-real-154-covered ((a)(b)(e), FORBIDDEN, WRITES), enter153b-unsuppressed-both ((b) alone: visit 3
  rendered without suppression, its first row ip22), 154-after-153b-both ((b) alone), last-place-harness-both ((c)
  alone), end-log-row-real-151-F ((c) alone, a synthetic log), end-real-151-F ((d) alone), end-boundary-residue-both
  ((d) alone).
- **O5-CHOICE** (new; decision 3), every covered run of both sides:
  - (a) exactly ONE store at `choice.store`'s site (153 e3 t1 ip1741, `Global.Bit[3795]`): one raw `w` row, old 0, new
    1, at fld member(153)/153, and NO `c` row of that site (a same-value repeat is suppressed into a `c` row: counting
    `w` rows alone could not see it);
  - (b) exactly one `choice` row for the guarded rule: `index` 1, `took.landed` True, its answer's `press` row (`why`
    "choose", `answer`) with `selected_before` 1 and a `down_frame`; no second;
  - (c) the store's value equals that `index`, and its row's frame `f` is at or after the answer's `down_frame` (both
    Time.frameCount);
  - (d) the `guard` row: the quiet window opened (`open_frame` set) before `choice_first`, and no press of the visit
    other than the answer's own presses has a `down_frame` in [`choice_first`, `choice_close`) (an unplaceable press
    -- no accepted event -- counts by its decision sample `pre.frame`, fail-closed: O4's SWORD (f) rule).
  Mutants (each CHOICE alone unless named): choice-second-1741-both ((a): a second ip1741 store 1 -> 1, a `c` row),
  choice-index-0-both ((b), with WRITES: the log's index 0 and the trace's 0), choice-unlanded-both ((b)),
  choice-cursor-off-pick-both ((b): `selected_before` 0), choice-store-before-answer-both ((c)), choice-stray-press-
  both ((d)), choice-no-quiet-both ((d)); bit3795-zero-F ((c) with WRITES F, NULL F, STATE F: "a fork that stores a
  constant").
- **O5-WALK** (new; THE PAIRED-WALK LAW), every covered run:
  - (a) exactly one `step` row of the stair step (`name` "the stairs", `donor` 153, `visit` 1) with `outcome` "done",
    its `lost` sample satisfying its `until` (re-checked: `until_ok`), its `landed` None; at most `interrupts` (1)
    `interrupted` rows of it before, each with no `door` (a side scene, never an exit);
  - (b) no `w` row (any target, masked or not) whose frame lies inside a walk window -- each attempt's [`frame0`, its
    `lost.frame`] and each interruption's [`lost.frame`, the next attempt's `frame0`]: the walk wrote nothing, so no
    key can depend on its path.
  Mutants (each alone): walk-no-step-both, walk-lost-east-both (the done row's `lost` x -900), walk-two-interrupts-
  both, walk-interrupt-in-door-both, walk-window-masked-write-both (a `Bit[191]` row inside the window: WRITES and
  MASKED cannot see it); and the PASS case walk-interrupted-once-both.
- **O5-MASKED** (O2's). Mutant: masked-differs.
- **O5-STATE** (O2's): (a) each unmasked target's emitted history identical across every covered run, in order, and the
  suppressed stores as a set; (b) every covered run's `end_state` == 4.9. Mutants: end-state-differs (b),
  suppressed-pattern-differs-F ((a) alone: every F run's visit-3 ip138 EMITTED -- an engine that does not suppress at
  that site: NULL's sets are equal, the ordered history is not), fork-drops-a-write (a); and the PASS case
  byte8-race-both (every live end state reads Byte[8] 125: not registered, so the race cannot fail it).
- **O5-JOIN** (O1's). Mutant: join-failure.
- **O5-THROW** (in `run`): nothing thrown through EventEngine, EBin, StoryTrace or HarnessAgent.

**VERDICT**: O1's `verdict()`. A failed check outranks a void one: a V19 reads "NOT PROVEN: O5-VOID-ASYM", never VOID.

### 5.4 Report-only (`report_extra`)
- **Scope**, five lines:
  - *start dependence* -- "under the raw warp no key's VALUE on the route is start-dependent (constants and the frozen
    pick; Byte[6] |= 8 is after the cut); the EMITTED ROW PATTERN is: the sink emits the first same-value store per site
    per epoch (StoryTrace.cs:383-401), so after this start visit 1's ip57/ip119 are changes and visit 3's are emitted
    (same 1) while its ip22/ip49/ip138/ip200 are suppressed; after a true O1-O4 run visit 1's would be same-value and
    visit 3's first emitted row would be e18 t1 ip890; the `old` values differ too (Int16[9] 643 vs -1, Byte[13] 1 vs 0,
    Byte[8] 125 vs 75 at ip2953). LANDING (b)'s re-entry row, STATE (a)'s ordered histories and every row count are this
    start's: never reuse them against a chained true-run trace. Not covered: party data, names, gil, Map variables
    (Map.Byte[27], the branch), the camera, field 70's override state, and the fifteen untouched targets' values after a
    true O1-O4 run" (critic #5);
  - *suppressed stores* -- "every suppressed store before the cut is in a kept `c` row: 153's visit-3 ip22/ip49 (masked:
    MASKED's counts) and ip138/ip200 (their last values -1/0 are visit 1's emitted keys, so STATE (a)'s suppressed set
    holds nothing beyond them); the end place 151's `c` rows are cut and hold only stores after the cut (its first
    store IS the cut)";
  - *the end state* -- "Byte[8] is read from the trace (153 e18 t1 ip890 := 0, the last pre-cut write), not live: 151
    e0 t0 ip315 races the read";
  - *settings and engine* -- the recorded `settings`, `derived`, `engine` (O4's lines);
  - *language* -- derived from the session's recorded P-TEXT3 line (O4's `scope_lang` shape, block 3).
- **The walk, per run:** the grant's sample (frame, x, z), the route record (legs, length, replans, pushes, waits,
  blockers), the loss sample (frame, x, z, published y) and the last control sample before it, ticks grant -> loss,
  interruptions, the calibration's probes.
- **The guard and the choice, per run:** 127's presses (decision and down frames, held-off), 127's last listed and
  first without, the quiet window's open frame, 128's first publication, readiness and type-out end (options stable),
  the RACE MARGIN (from 127's last listed sample to 128's type-out end, in ticks and seconds: the stall a stray press
  would need), 128 as published at readiness (options, active, selected), the pick, `took` (confirms, landed),
  `selected_before`.
- **The pattern, per run:** the emitted rows per visit, the `c` rows (site, n, last), visit 3's first emitted row
  (4.16).
- The session's end (S5), O4's sections copied (VOID reasons per side, masked counts, forbidden hits, the P-TEXT3 line,
  the folded transcripts), and the re-runs held.

---

## 6. Offline check and preflight

### 6.1 `--offline-check` (the install and O4's build, read-only; reads `--predictions`, else the frozen file, else the DRAFT, and prints which)
- **O5-BUILD**: `Segment.build_check` (every member's `.eb`, 7 languages, its own donor's with only in-chain `Field()`
  literals remapped: "140 files") + O5's ROUTE BUILD PINS, per language (each language's script decoded on its own; the
  US ips listed): the bytes in which member(153), member(154) and member(151) differ from their donors are EXACTLY the
  operands of their in-chain `Field()` instructions -- member(153): e3 t1 ip3158 (154), e18 t1 ip1085 (151), e23 t2 ip211
  (154), e24 t2 ip191 (150), e25 t2 ip203 (64) and ip429 (151), e28 t2 ip235 (150); member(154): e2 t1 ip1528 (153) and
  the six of e8/e9/e10 t2 (153, 158, 156, 155, 156, 167); member(151): e2 t1 ip940 (153), e8 t2 ip245 (153); member(153)'s
  `Field(204)` (e3 t1 ip3296, the flashback: 204 is no chain donor) stays the donor's. The sites are DATA in the
  predictions (`route_build`, O4's `fight.build` shape); C0 measures them on O4's build (every language) before C1
  registers them, and any other differing byte is explained at the byte level, never loosened.
- **O5-KEYS**: O4's `keys_check` machinery -- O2's on a filtered copy (the chain, the writes but the `:=var` key,
  `forbidden_sites` + `error_path` + `dead`, `start_first`), the `:=var` key (153 e3 t1 ip1741, rvalue `B_SYSVAR[9]`, in
  its statement), `start_music` one writes key -- then THE ROUTE PINS (4.14): every pin's text exactly the stock US
  script's, `route_mes` as pinned. Expected: O2's half "36 sites (36 keys), every op in its statement, 0 compound values
  computed from their priors, none masked (start_first's Bit[191] is boot_scratch: O2-START reads it raw)" -- chain 3,
  writes 11 (the `:=var` key filtered out), forbidden 2 + error path 8 + dead 11 (153: 8, 154: 3), start_first 1 --
  then "; the choice's :=var key (153 e3 t1 ip1741, rvalue B_SYSVAR[9]) in its statement; start_music one writes key"
  (37 sites; Bit[3795] lies outside the story-noise mask, `T.noise_regions` empty) and "; 47 route pins equal; mes 127
  holds the marker, mes 128's second line holds the pick, mes 56 the stop page" (4.14's table: 47 instruction sites,
  each text verified against the stock US listing while designing).
- **O5-TEXT**: O4's `text_check` on block 3, STRICT (`strict_text`): "block 3: 7 byte-equal of 7; KNOWN-KIT-DEFECT 0,
  FAIL 0".
- **O5-CENSUS** (O5's `store_census`): every gEventGlobal store site of stock 153 and 154 is in `writes`, `chain`, the
  noise mask, `start_first`, `error_path`, `forbidden_sites`, `dead` or an `inert` function (O4's class precedence);
  every function decodes; no unresolved store. THE INERT PROOF, per entrance: every instancing op of the field sits in e0
  t0 (`instancing_sites`), and NO entrance the route enters the field by (`visit_entrances`: 153 at 325 AND 316, 154 at
  304) instances an inert entry (`instanced_at`); a SHARED inert entry (`shared_by`) needs, besides, that every
  `RunSharedScript(n)` site of the field lies in a function of an inert entry (153 e15: its one caller e32 t1 ip866). A
  registered key inside an inert function FAILS by name. Expected: "153: 51, 154: 22 store sites -- all classified
  (writes 7/5, chain 2/1, masked 2/2 (153's ip22 is start_first), error_path 4/4, forbidden 2/0, dead 8/3, inert 26/7);
  0 unresolved; inert 153 e15 (shared, run only from e32), e23, e24, e25, e32 not instanced at 325 or 316; 154 e5, e8,
  e9, e10 not instanced at 304". 151 is the end place: its first store at 110 is the cut (O5-LANDING (d)); no site of
  it precedes the cut, and its census is O6's.
- **O5-REGIONS** (O5's `regions_problems`; 0.2 #11): every frozen region's points are the first SetRegion of its (donor,
  entry); `exit`: `scan_gateways` has its (to, entrance, face_gate) AND it is instanced at some route entrance of its
  place; `scene`: instanced at a route entrance, its tag 2 holds `DisableMove()` after a `Map.Byte[24] const(<stage>)
  B_EQ` test, its entry holds no gEventGlobal store and no `Field()`/`ExitField()`; `dormant`: instanced at none of its
  `entrances`, which must be exactly the place's route entrances. Every gateway of 153 and 154 (`scan_gateways`) and
  every region instanced at a route entrance is registered; no hot-spot (`hotspot_census` of 153 and 154 empty).
  Expected: "9 regions (1 exit, 2 scene, 6 dormant), 0 hot-spots, 7 gateway entries all registered".
- **O5-GOALS**: O2's `goals_check` on the table (the step runnable, `visits` a walk on the route from the start place,
  the goal on the floor >= 80 from a wall with the 33 tris closed, its `until` true at the goal, a route from `start`
  avoiding e26/e27/e28) -- then O5's `goals_extra`: (c) THE CONTOUR ON THE ROUTE: the planned route, sampled every 5 u
  on the real mesh (the open tri under each point, its interpolated height), reaches PSX y <= -450 before its end, at a
  point with x <= `until`'s -1100 (the research's ~(-1482, 527), 315 u into the last leg; the check prints the
  measured point); (d) THE EVIDENCE'S SOUNDNESS: every open tri vertex and centroid
  at PSX y <= -450 lies at x <= -1100 (the west stair; critic #12, `wm153.py`), and every registered `scene` and `exit`
  region of 153 lies wholly at x > -1100 -- so a loss at x <= -1100 in stage 6 is the stair's and nothing else's.
- No SEAM check (the chain is closed: LANDING (e)).

### 6.2 `--preflight` (the live install, read-only; ALL GREEN today -- nothing needs deploying)
- **P-MANIFEST** (`o5_forks.json` members = the frozen members, `deployed` true), **P-DEPLOY** (twenty, each once under
  its name, mapped once), **P-EB** (20 x 7 live `.eb` = O4's build), **P-FLOOR** (twenty deployed walkmeshes = their
  donors'; member(153)'s is the stair walk's floor).
- **P-STOCK**: no mod folder overrides 151, 153 or 154 (today: none).
- **P-TEXT3** (block 3, STRICT: O4's `p_text` with no tolerated copy): today "FF9CustomMap: KNOWN-KIT-DEFECT 0, FAIL 0, 7
  byte-equal of 7".
- **P-RECOVERY**: 4600 registered (FF9CustomMap-world).
- **P-DONOR**: 151, 153 and 154 each forked by exactly ONE ForkDonorPatch row across the stack, its member's (today:
  31244, 31245, 31246 in FF9CustomMap; the stack's twice-forked donors 312, 350-359 are off the route).
- **P-SETTINGS** (4.13's 28 keys), **P-PAD** (O4's), **P-OVERRIDE** (field 70's override, one folder, the pinned sha),
  **P-ENGINE** (the live x64/x86 DLLs the pinned sha).
- Not carried (11.2 #1): P-GATE (R-GATE's +30% witness: O4's fight alone), P-TEXT2 (block 2: no O5 field reads it).
- **In game** (`capabilities`): P-CAP, P-OBJECTS ("the engine publishes the field's objects (s89): the walk's `npcs`
  plans round Blank and the hidden colliders"), P-LANG (English(US)), P-DONOR-LOG (this launch's Memoria.log: the
  patchers ran, no ForkDonorPatch collision for 151, 153 or 154), P-LAUNCH (every stacked patch file, Memoria.ini and
  the engine DLLs older than the launch; the DLLs the pinned engine), P-PAD (re-sampled).
`--preflight` must read all green before any rehearsal; if it does not, the lead says exactly which line failed and
stops (decision 6).

### 6.3 The fingerprint (per run, before and after)
O4's, unchanged (registrations, ForkDonorPatch rows, `.eb` and walkmesh shas, stock overrides, `override70`, `text2`,
`text3`, `lang`, `settings`, battle data, `engine`): another session's deploy, a re-wired New Game or an engine rebuild
mid-session makes runs VOID (A-INSTALL), never skews them.

### 6.4 `o5_forks.json` (the implementer writes it; nothing to flip: the chain is live)
```json
{"what": "O5's fork chain: O4's alxc disc-1 chain as deployed (31240-31259, FF9CustomMap). O5 runs member(153) 31245 (visits 1 and 3), member(154) 31246, and ENDS in member(151) 31244: every route Field() is retargeted, so the chain is closed (no seam). Nothing is imported, built or deployed for O5.",
 "reuses": "studies/story-trace/o4_forks.json",
 "import": "O4's (o4_forks.json import)", "build": "O4's: C:/gd/_ns_playtest/o4/build", "deploy": "O4's, 2026-10-02 09:04 local",
 "mod_folder": "FF9CustomMap", "members": {"<20 fork ids>": "<donor>"}, "names": {"<20 fork ids>": "<name>"},
 "route_members": {"31244": 151, "31245": 153, "31246": 154},
 "text_blocks": {"3": [31243, "...", 31259]},
 "deployed": true, "relaunch_needed": false,
 "relaunch_why": "nothing is deployed for O5; P-LAUNCH proves the launch read the live patch files, P-DONOR-LOG that it logged no collision for 151, 153 or 154",
 "global_side_effects": "O4's (o4_forks.json global_side_effects): O5 adds none",
 "known_defects": [], "revert": "O4's (o4_forks.json revert)",
 "built": {"measured": "<C0: the route members' Field() operand sites per language, read from O4's build>"},
 "verified": null}
```

---

## 7. Rehearsal plan (the lead runs these in game)

### 7.1 The stages (`o5_rehearse.py`: `run(g, field=None)`; `O5_STAGE=<name>` picks one by name, `--field 153` R-STAIRS)
Each traced stage: New Game; `wait_frames(30)`; `storytrace(True)`; the raw warp; `segment_drive.drive(g, stage_pred,
side, log, end_fields=..., observe=recorder, forbid_live=True, witness=input_witness(g))`; the trace to
`rh_<stage>_<n>.jsonl`; the record into `o5_rehearsal.json`; `end_run`. Only R-FULL's traces may define or change the
keys, the start, the end state or the row pattern; the staged runs prove mechanics and are compared within their stage.
F-SMOKE and F-PASS send NO `storytrace` verb: no fork trace exists before the freeze.

| Stage | When | Warp | Ends in | Runs | What it settles |
|---|---|---|---|---|---|
| **R-STAIRS** (the go/no-go) | stock | `warp 153 325 1190` | 154 | 2 | F1-F3, F8, F9, F11, F12: the grant position and frame; the walk (route, wall contacts, calibration probes); the loss sample and its latency (the last control sample, the first without, published y); the teleport sample; e9/e11/e31 published; 127's presses and 128's timeline, the race margin; 128 as published at readiness, its type-out; the landing; the KEYON pairs' gates and the [TIME=20] windows under Confirm |
| **R-FULL** (by name) | stock | `warp 153 325 1190` | 151 | 2 | F4-F7: the 15 keys, the masked rows, the `c` rows and visit 3's first emitted row (4.16), the four residue rows, the end cut 151 e0 t0 ip22, the end state (Byte[8]'s read value recorded), the run time, the longest no-progress stretch |
| **R-WALK-VOID** (by name; LAST in a launch) | stock | `warp 153 325 1190`, the stage overlay `walk_stop_s` 0.8 | V13 | 1 | F7: the walk stopped mid-way (o5_rehearse wraps `g.route_to` to stop after `walk_stop_s` and raise "the rehearsal's stop mid-walk"); `end_run` (warp 4600 from 153's FieldHUD, the ladder) reaches the title |
| **F-SMOKE** (by name; NO trace) | any time (deployed) | `warp 31245 325 1190`, `warp 31246 304 1190`, `warp 31244 110 1190` -- each `member(<donor>)` resolved from the chain (`stage_ids`) -- and their stock twins | -- | 6 warps | F13: each member loads at its entrance and SC (field, FieldHUD), its published object sids its twin's after `smoke_s` (153@325 {3, 7, 9, 11, 31}; 154@304 {2, 4}; 151@110 {3, 4, 5, 12, 17}; the twins give the measured sets), 0 exceptions, `end_run` ok |
| **F-PASS** (by name; NO trace; before the freeze) | after F-SMOKE | `warp 31245 325 1190` | 31244 | 1 | F14: one F run through the whole route on the DRAFT (`forbid_live` False, `end_row_s` None): member(153)'s stage 27 VIB ops (s62's donor-name fix) run once; reached member(151), beats `stairs`/`choice128`, no V-class, no exception through EventEngine/EBin/HarnessAgent/HonoluluFieldMain/vib since the warp. Its record is NOT evidence for any key |
| **R-RACE** (optional, by name) | stock | `warp 153 325 1190`, the overlay `guard: null` | 154 | <= 3 | the unguarded race's frequency directly: a stray answer is recorded (the choice gone, path 0), never covered |

Default order without `O5_STAGE`: R-STAIRS, R-FULL, R-WALK-VOID (last). F-SMOKE, F-PASS and R-RACE by name only.
Estimates a run: R-STAIRS ~3 min, R-FULL ~4.7 min, R-WALK-VOID ~1 min, F-SMOKE ~3 min in all, F-PASS ~4.7 min.
`o5_rehearse.py` reuses O4's shapes (`select`, `stage_ids` resolving `member(N)` and checking every F-side id against the
chain, `stage_pred` merging an overlay into a COPY and re-checking it with `guard_of`/`step_of`, `one`, `smoke`,
`launch_readings`) and `O4R.Recorder` (each page's windows and `gone_frame`, the KEYON pairs), plus `fpass(g, ...)` (an
untraced start: New Game, `wait_frames(30)`, the warp, then the drive -- never `Segment.start_run`, which arms the trace)
and the walk's and the guard's records off the drive's own rows. Every summary is cut at the stage's end PLACES
(`o5_hallway.trace_summary`). The command: `py tools/play.py studies/story-trace/o5_rehearse.py --label o5-rh --timeout
240`.

### 7.2 What every stage records
O4's record (grants, pages with `timed`, the published choices, the press evidence, the longest no-progress stretch,
the end state, `end_run`'s rows) plus:
- the walk: the grant sample (frame, x, z) and the frames from 117's going to it; the step rows whole (route record,
  `lost`, `door`, attempts); the last control sample and the first without (ring); the published y at both; the
  teleport sample (the first sample at (-1165, 856) +- 32) and its ticks after the loss; the published objects at the
  grant (sids, `shown`, `coll`, `r`, `talk_r`, `range_r`); the calibration record (probes, lengths);
- the guard: 127's first seen, its presses (decision, accepted, down, ack frames; held-off), last listed, first without;
  the quiet window's open frame; 128's first publication, its first ready sample (group Dialog.Choice), its type-out end
  (the first sample from which its options stay equal), its options/active/selected at readiness; `choose_landed`'s
  record and presses; the RACE MARGIN (ticks and seconds from 127's last listed sample to 128's type-out end);
- the KEYON pairs (first seen -> gone, Confirms pressed), the timed windows (137, 140: the Confirms pressed while listed
  and their lives in ticks);
- the trace through `trace_summary`: the start rows, the chain rows, each registered key present or absent, every
  unregistered key, the emitted rows per visit and the `c` rows, visit 3's first emitted row, the end cut's row, the
  residue, the masked counts, the join failures;
- the launch's settings and engine, P-LAUNCH, P-DONOR-LOG, P-PAD, P-OVERRIDE and P-ENGINE readings;
- F-SMOKE: per warp the field and UI reached and when, the object sids against the twin's, exceptions, new Memoria.log
  warnings, `end_run`'s result; F-PASS: the drive's outcome and rows, the exceptions since the warp, whether page 137
  (stage 27) was seen.
`py studies/story-trace/o5_hallway.py --rehearsal-report <run dir>` prints all of it, stage by stage, run by run.

### 7.3 The freeze checklist (each item needs its evidence; the run dirs go into `rehearsals`)
- **F1 (the grant and the walk; go/no-go).** In every R-STAIRS and R-FULL run: control granted once in 153 near (1105,
  -78) (within 64 u; else the step's `start` takes the measured point and O5-GOALS runs again before the freeze), the
  stair step `done` on its first attempt (or after one absorbed side scene), its loss sample at x <= -1100, no V-class.
  A walk that fails its evidence: STOP and re-derive the contour and the evidence from the measured loss samples.
- **F2 (the race).** In every guarded run: 127 pressed by page-once until gone; the quiet window opened; nothing pressed
  in it; 128 published within `quiet_cap_s`; no press with a down frame inside [128's first publication, close) but
  the answer's; the race margin recorded. A stray inside the window on a guarded run: STOP -- the fallback (2.5.7) is
  then the lead's call. (R-RACE, if run, records the unguarded frequency.)
- **F3 (128 as published).** Options/active/selected at readiness: the rule's "her face" matches exactly one line,
  absolute 1; `selected` 0; the type-out time measured; the landing took <= `CHOICE_CONFIRMS` Confirms and
  `selected_before` 1.
- **F4 (keys and the pattern).** The R-FULL traces define the predictions: per run exactly the 15 keys and the masked
  rows; no error-path, dead, forbidden or inert row; exactly the four start residue rows and none after; 153's first
  `w` row ip22 and its first Byte[13] row ip119 from old 1; visit 3's first emitted row ip57 and the four `c` rows as
  4.16; the end cut 151 e0 t0 ip22; the two runs key for key identical; any difference explained at the byte level
  before the freeze (a new site only with O5-CENSUS's lists updated).
- **F5 (end state).** Every R-FULL `end_state` equals 4.9; Byte[8]'s live reading recorded (0 or 125: the race).
- **F6 (budgets).** `run_s` = 2 x the slowest R-FULL; `run_min_s` = 1.25 x the median; `session_s` = 8 x the median +
  1800; `no_progress_s` = max(60, 3 x the longest no-progress stretch of any traced stage); `quiet_cap_s` = max(2, 3 x the
  slowest 127-gone -> 128-published in game seconds); `settle_s` = max(1.0, 128's measured type-out + 0.5) (critic #6).
- **F7 (recovery).** R-WALK-VOID: the stop mid-walk with nothing pressed after, then `end_run`'s rows `recover-warp`
  (4600) and the title; `end_run` from 154 (R-STAIRS) and 151 (R-FULL) reach the title.
- **F8 (pairs and timed windows).** Every KEYON pair closed within 8.3 s of its second window; 137/140 inert to Confirm
  (else explained at the engine level before the freeze: a Confirm that closes them early changes no store).
- **F9 (pages' openings).** The dropped first presses counted; `page_once_ticks` := max(10, 2 x the longest measured
  page opening in ticks).
- **F10 (settings and launch).** P-SETTINGS, P-PAD, P-OVERRIDE, P-ENGINE, P-LAUNCH and P-DONOR-LOG pass on the
  rehearsal launch; its fingerprinted `settings` and `engine` equal 4.13's.
- **F11 (the input witness).** No `input` row in any run.
- **F12 (objects).** Blank published with no player collision; e9/e11/e31's publication (shown False) recorded; the
  walk planned round them without a push.
- **F13 (F-SMOKE).** The three members load as their twins.
- **F14 (F-PASS).** Reached member(151) with no throw and no V-class; page 137 seen (stage 27 ran).
Then `--freeze` (v1). `freeze` refuses: no `guard` or one `guard_of` refuses (or a `guard: null` overlay); no
`witness`; a table step carrying a rehearsal overlay (`walk_stop_s`); `side_ends` failing `side_ends_of`; a non-empty
`battles`; an empty `rehearsals`; an `engine` that is not the live DLLs'; an existing file.

### 7.4 After the freeze: the session (the lead)
- **G1.** `--preflight` all green on the session's launch (P-LAUNCH, P-ENGINE, P-DONOR-LOG in game).
- **G2.** The session, unattended and hands off (no key while the game has focus, no pad -- the witness VOIDs a run
  that sees one, V13): `py tools/play.py studies/story-trace/o5_hallway.py --label story-o5 --timeout 240`.

---

## 8. The dry run (`o5_dryrun.py`: synthetic sessions through `O5.analyse`)

Built like `o4_dryrun.py`: its own `render` (O4's, with O5's start values -- SC 1190, FieldEntrance 325, Byte[13] 1,
Int16[9] 643, Int16[11] -1, Byte[8] 125, every other target 0 -- and the sink's rule: a same-value store emitted once per
SITE, a change up to 64 times, the rest counted into `c` rows just before `off`; the site key holds `fld`, so the
revisit's prologue suppresses exactly as 4.16), O3's event helpers, and O3's EXACT `case()` (every check a case does not
name must read PASS; a COVER-VOID case expects every core check VOID; LANDING, CHOICE and WALK cases register the
clause the detail must name).
- **Real store sites** (every field row joins): 4.3-4.5's, the error-path, forbidden, dead and inert sites, 151 e0 t0
  ip22 (the end row) and 151's post-cut prologue and ip315.
- **A base run**: `arm` (fld 70); the four residue rows (fld 70); visit 1's rows (4.16) with ip1741 (0 -> 1) between the
  walk and the exit; visit 2's; visit 3's six prologue stores (render suppresses four) and its two; 151's ip22, then
  its post-cut rows; `off` (fld 151 / 31244). On F: 153 -> 31245, 154 -> 31246, 151 -> 31244.
- **A log**: the visit rows; the stair step row (`done`, `frame0` and `lost` bracketing no trace row, `lost` (-1482,
  527)); the page presses with `seq`; the `guard` row (armed, open before `choice_first`, the presses with down frames);
  the choice row (options `['Zidane\n"Hmm..."', 'Let her pass', 'Examine her face']`, active [0, 1], selected 0, index 1,
  `took` {landed True, confirms 1}); its `choose` press rows (down; confirm with `selected_before` 1, `answer`, a down
  frame before ip1741's row); the end row (151 / 31244); `end_state` (4.9); beats `{"stairs": true, "choice128": true}`.

| Case | Want |
|---|---|
| null-pair | PROVEN |
| fork-drops-a-write (no 154 ip279 on F) | NOT PROVEN (WRITES F, NULL F, STATE F) |
| chain-dropped-fork (no 154 ip1520 on F) | NOT PROVEN (CHAIN F, LANDING F (b), WRITES F, NULL F, STATE F) |
| chain-first-old-wrong (both: ip3150's old 326) | NOT PROVEN (CHAIN F alone) |
| start-residue-three (S: byte 3's row missing) | NOT PROVEN (START F) |
| start-residue-wrong (S: byte 3 0 -> 2) | NOT PROVEN (START F) |
| start-first-missing (both: visit 1's ip22 dropped -- render emits visit 3's ip22 instead, as the sink would) | NOT PROVEN (START F; LANDING and MASKED as the render shows -- registered with their byte-level reason) |
| start-music-old-wrong (both: ip119's old 3) | NOT PROVEN (START F) |
| front-cut-write (F: a `w` row in fld 70 before the start) | NOT PROVEN (START F) |
| error-path-start-S (one S run: 153 ip97, stopped at window 56; V5 driver [153, 1190]) | PROVEN (S 2 of 3); the run's classes include V5 and A-START |
| error-path-154-F (one F run: 154 ip101, window 56; V5 game [154, 1190]) | NOT PROVEN (VOID-ASYM F) |
| residue-after-start (F: an `r` row on byte 300) | NOT PROVEN (RESIDUE F) |
| writes-extra-symmetric (both: 153 e3 t1 ip3168) | NOT PROVEN (WRITES F; NULL P) |
| inert-row-both (both: 153 e32 t0 ip718) | NOT PROVEN (WRITES F; NULL P) |
| sc-write-fork (F: a `cs` UInt16[0] := 1190 row in 154) | NOT PROVEN (NO-SC F, WRITES F, NULL F, STATE F) |
| sc-harness-poke-both | NOT PROVEN (NO-SC F alone) |
| bit3795-zero-F (every F run: ip1741 := 0; end state Bit[3795] 0; the log unchanged) | NOT PROVEN (WRITES F, NULL F, STATE F, CHOICE F (c)) |
| choice-second-1741-both (a second ip1741 store, 1 -> 1: a `c` row) | NOT PROVEN (CHOICE F (a) alone) |
| choice-index-0-both (the choice row index 0, ip1741 := 0) | NOT PROVEN (CHOICE F (b), WRITES F) |
| choice-unlanded-both (`took.landed` False) | NOT PROVEN (CHOICE F (b) alone) |
| choice-cursor-off-pick-both (`selected_before` 0) | NOT PROVEN (CHOICE F (b) alone) |
| choice-store-before-answer-both (ip1741's frame before the answer's down frame) | NOT PROVEN (CHOICE F (c) alone) |
| choice-stray-press-both (a page press down inside [choice_first, choice_close)) | NOT PROVEN (CHOICE F (d) alone) |
| choice-no-quiet-both (the guard row's `open_frame` None) | NOT PROVEN (CHOICE F (d) alone) |
| v17-stray-one-S (one S run VOID V17 driver at [153, 1190]: path 0's rows, ip1741 := 0) | PROVEN (S 2 of 3) |
| v17-unlanded-one-F (one F run VOID V17 driver: the answer did not land) | PROVEN (F 2 of 3) |
| v13-input-one-F (one F run VOID V13 driver: outside input at the choice) | PROVEN (F 2 of 3) |
| v2-reask-one-F (one F run VOID V2 game at [153, 1190]) | NOT PROVEN (VOID-ASYM F (a)) |
| v4-control-154-F (one F run VOID V4 game at [154, 1190]) | NOT PROVEN (VOID-ASYM F (a)) |
| v4-control-316-F (one F run VOID V4 game at [153, 1190], visit 3) | NOT PROVEN (VOID-ASYM F (a)) |
| v19-one-F (one F run VOID V19 game at [151, 1190]: landed in real 151) | NOT PROVEN (VOID-ASYM F (a)(c)) |
| leak-real-154-F (one F run VOID V19 at [154, 1190]; its rows at fld 154) | NOT PROVEN (FORBIDDEN F, VOID-ASYM F) |
| back-door-S (one S run VOID V11 driver: e28's two rows, a step row V11 `door` 153.e28 `landed` 150, rows in 150) | PROVEN (S 2 of 3; the 150 hits backed: A-FORBIDDEN) |
| back-door-unbacked-F (one F run: e28's rows and rows in 31243, no step row explains them) | NOT PROVEN (FORBIDDEN F, and the co-failures the rows give -- registered with their reason) |
| v7-walk-all-F (every F run VOID V7 driver at [153, 1190]) | NOT PROVEN (VOID-ASYM F (b); COVER V) |
| walk-never-contour-one-S (one S run VOID V7: the walk ended with control held twice) | PROVEN (S 2 of 3) |
| walk-interrupted-once-both (every run: one `interrupted` row, then `done`) | PROVEN |
| walk-no-step-both | NOT PROVEN (WALK F (a) alone) |
| walk-lost-east-both (the done row's `lost` x -900) | NOT PROVEN (WALK F (a) alone) |
| walk-two-interrupts-both | NOT PROVEN (WALK F (a) alone) |
| walk-interrupt-in-door-both (an interrupted row with `door` 153.e28) | NOT PROVEN (WALK F (a) alone) |
| walk-window-masked-write-both (a Bit[191] row inside the walk window) | NOT PROVEN (WALK F (b) alone) |
| lands-real-154-covered (every F run: 154's rows at fld 154, the drive reached) | NOT PROVEN (LANDING F (a)(b)(e), FORBIDDEN F, WRITES F; NULL P) |
| enter153b-unsuppressed-both (visit 3 rendered without suppression: its first row ip22) | NOT PROVEN (LANDING F (b) alone) |
| 154-after-153b-both (a 154 harness row after visit 3's first row) | NOT PROVEN (LANDING F (b) alone) |
| last-place-harness-both (a harness row in 153 after ip1077) | NOT PROVEN (LANDING F (c) alone) |
| end-log-row-real-151-F (every F run's synthetic `end` row names 151) | NOT PROVEN (LANDING F (c) alone) |
| end-real-151-F (every F run's cut row at fld 151; `off` in 31244) | NOT PROVEN (LANDING F (d) alone) |
| end-boundary-residue-both (an `r` row in place 151 before its ip22) | NOT PROVEN (LANDING F (d) alone) |
| end-row-missing-one-S (one S run: no row in 151, `off` in 151) | PROVEN (S 2 of 3); that run A-NOEND |
| suppressed-pattern-differs-F (every F run: visit 3's ip138 emitted) | NOT PROVEN (STATE F (a) alone) |
| byte8-race-both (every live end state holds Byte[8] 125) | PROVEN (Byte[8] is not registered) |
| observed-quiet-page-one-F (one F run VOID V17 with an `observed` quiet_page) | NOT PROVEN (VOID-ASYM F (d) alone) |
| observed-quiet-page-each-side | PROVEN (S 2 of 3, F 2 of 3) |
| observed-choice-gone-one-F | NOT PROVEN (VOID-ASYM F (d) alone) |
| control-S (one S run VOID V4 game at [154, 1190]) | NOT PROVEN (VOID-ASYM F (a)) |
| stairs-beat-missing (two S runs: `{"stairs": false}`) | VOID (COVER V; VOID-ASYM P) |
| choice-beat-missing (two S runs: `{"choice128": false}`) | VOID (COVER V; VOID-ASYM P) |
| end-cut (S: rows in 151 past the end) | PROVEN |
| end-state-differs (one covered F run: Bit[3795] 0 live) | NOT PROVEN (STATE F) |
| masked-differs (every F run without its Bit[184] rows) | NOT PROVEN (MASKED F) |
| mismatched (one F run's member rows name another donor) | PROVEN; that run A-MISMATCH |
| no-start-row (one S run never reaches 153) | PROVEN; that run A-NOSTART |
| join-failure (both: an extra row at 153 e3 t1 ip1742) | NOT PROVEN (JOIN F alone) |
| trace-without-off | VOID |
| install-changed | VOID |
| predictions-changed | NOT PROVEN (FROZEN F) |

A case's want that the code cannot hold (a co-failure the table did not foresee) is explained at the byte level and
re-registered, never loosened silently (O3 11.6, O4 11.4 C #10 did this).

Units (no session): **guard-of** (each refusal); **witness-of**; **cell-visit**; **stray-answer** (O4's strings by
default, O5's labels, the `pick`); **render-suppression** (the base run's rendered rows: 21 `w` rows before the cut, 4
`c` rows, visit 3's first row ip57 -- and the SAME event list through the FakeGame's H13 knob gives the same `(k, fld,
sid, tag, ip, new, same, n, last)` sequence: one model, two implementations); **trace-summary** (a base S run: the
chain 3/3, writes 12/12, the cut row, the `c` rows; an R-STAIRS stage ending in 154 cut at 154's first row; the same
summary given end FIELDS on an F stage ending in a member is not cut -- the unit's mutant); **state-history**
(Byte[8] `[(153, 0), (154, 125), (153, 0)]`, Int16[11] `[(153, -1), (154, -1)]`, Bit[3795] `[(153, 1)]`); **visit-
entrances** ({153: [325, 316], 154: [304]}; O4's `route_entrances` on the same predictions gives 154 110 -- the reason
O5 has its own); **store-census** (PASS with 6.1's line; mutants each FAIL by name: `dead` without 153 ip41; `inert`
without 32; `error_path` without 154 ip497; an inert entry 3 (instanced at 325); e15 with its caller e32 made non-inert
(the shared proof fails); a registered key inside an inert function); **regions** (PASS; mutants: 153.e28 dormant
(instanced at 325), 153.e23 exit (instanced at no route entrance), 153.e26 role exit, 154.e9 missing, a dormant region
whose `entrances` omit 316); **goals** (PASS with the contour line; mutants: `closed_tris` empty (no route), the goal
at (-1700, 900) (off the floor), `until` x_le -1800 (false at the goal), no `start`, the contour required at x <= -1500
(fails: the crossing is at ~-1482)); **route-pins** (PASS; mutants: a pin's text changed, mes 127 without the marker, 128's pick on both
lines); **build-pins** (O5's route members on a synthetic three-member build: an extra byte changed in member(153)'s e3
t1, a `PreloadField` operand remapped, an in-chain `Field()` left unremapped: FAIL each); **keys offline mutants** (a
write's value, the `:=var` rvalue `B_SYSVAR[8]`, a chain `off` + 1, `start_first`'s target, a dead site's value,
`start_music` at ip138); **p-donor-log**, **p-launch** (O4's units with 151/153/154); **p-settings**, **p-pad**,
**p-override**, **p-engine**, **text-strict**, **input-witness** (O4's units on O5's pinned values).

It prints the summary columns (FROZEN COVER FORBIDDEN VOID-ASYM START NO-SC CHAIN RESIDUE WRITES NULL STABLE LANDING
CHOICE WALK MASKED STATE JOIN) and "N/N cases as registered", exiting 1 on any miss.

---

## 9. Build order (three parts; no deploy, no game, no `tools/play.py`, no full suite)

Run pytest from `ff9mapkit/`, the study scripts from the worktree root. The harness tests run in REAL TIME (the
FakeGame loops on a thread): run the named `-k` selections, never many at once, and the whole file only where a PART
says so, alone. A SKIPPED test is not a pass: every required pytest run reports 0 failed and its skips/xfails exactly
the PART's baseline's (taken before the PART's first change); a skip for missing templates is fixed with `py -m ff9mapkit
extract-templates` and the run repeated. **Load-robust tests** (O4 lost two nightly runs to load flakes): a test that
drives a long route on the fake re-runs its run (at most 2 more) when, and only when, it ends in a DRIVER class a
starved harness can cause (V13 budget, V17 "landing unseen" / "did not land", V7 by a timed-out walk), asserting the
class on each discarded attempt -- a GAME class (V2, V4, V14, V19) or a wrong verdict is never re-run; every race is
reproduced by a deterministic stall (a wrapped call), never by real starvation; waits are judged on the GAME clock (the
quiet cap, `_choice_left`); the fake's loop runs at most 4x its `render_fps`. A failure that passes on an immediate
re-run of that test alone is a timing flake: named in the commit message, never ignored. Commit on the branch when a
step is green, one step per commit, each message ending with "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>".
Write non-ASCII files with Python (utf-8) or the Edit/Write tools; frozen JSON and baselines are LF (`-text`); a
Windows path inside a Python string is raw or escaped.

### PART A -- the regression gate extended to O4 (baseline FIRST), then the shared opt-in changes
1. **A0: the O4 gate and its baseline, FIRST.** Extend `segment_regress.py` (1.4: G0''' `--capture-o4` with its
   two-readings rule and refusals; G22-G25; G21 over the union of `sources`; `--rebaseline-source` over both baselines;
   `FAKE_PINS_O4`; `REQUIRED_TESTS_O5` empty; `_missing()`; the module docstring gains G0''', G22-G25 and says G24 is
   O4's VOID-path baseline) with `test_segment_regress_o4_pins_join_the_union` (pure: G21's checker over two
   baselines on temporary copies -- a pinned O4 machine-beat method edited FAILS naming it; a re-baseline row for an
   O4-baseline name passes; a name pinned in both baselines is refused at capture; into `REQUIRED_TESTS`). Run `py
   studies/story-trace/segment_regress.py --capture-o4`, and commit `research/o4_regress_baseline.json` with its
   `.gitattributes` line before any other code change. Then `py studies/story-trace/segment_regress.py` reads G1-G25
   (G21 over both).
2. **A1: S12 and S13** (`witness_of`, the run-wide poll; `cell(..., visit=)`, `go()` passing `self.at + 1`, the
   table's `visit` check) with their four tests (1.2). Break for each: S12 -- poll only under the Chanbara policy; S13
   -- ignore the `visit` key (the revisit runs the step: V7 driver, not V4).
3. **A2: S11** (`Session.choose_landed`) with its five tests (1.2).
4. **A3: S10** (`guard_of`, `_Drive.gd`, `guard_note_choice`, `guard_page`, `guard_quiet_tick`, `guard_stray`, the
   `guard` row, rule 6's verified answer under the guard, `stray_answer`'s keyword-only labels) with its eight tests
   (1.2).

**PART A REQUIRED-GREEN** (after A0, and again after A1, A2 and A3):

| Command | Expected |
|---|---|
| `py studies/story-trace/segment_regress.py` | exit 0; G1-G25 each PASS (G21: every re-baseline row named in its commit; none expected in PART A) |
| `py studies/story-trace/o1_dryrun.py` | exit 0; "16/16 cases as registered" |
| `py studies/story-trace/o2_dryrun.py --predictions studies/story-trace/o2_predictions_v1.json` | exit 0; "86/86 cases as registered" |
| `py studies/story-trace/o3_dryrun.py --predictions studies/story-trace/o3_predictions_v1.json` | exit 0; "102/102 cases as registered" |
| `py studies/story-trace/o4_dryrun.py --predictions studies/story-trace/o4_predictions_v1.json` | exit 0; "103/103 cases as registered" |
| `py studies/story-trace/o4_castle.py --analyse C:\gd\Dream-World-IX\.harness-runs\20261002-091051-story-o4 --predictions studies/story-trace/o4_predictions_v1.json` | exit 0; `VERDICT: PROVEN`; the archived `o4_report.txt` byte for byte |
| `py studies/story-trace/o4_castle.py --offline-check --predictions studies/story-trace/o4_predictions_v1.json` | exit 0; 4 PASS (0.2 #12) |
| `py -m pytest tests/test_harness.py -q -p no:cacheprovider -W ignore -k "segment"` | all passed, 0 failed, 0 skipped (A0's test; A1's four after A1; A2's five after A2; A3's eight after A3) |
| `py -m pytest tests/test_harness.py -q -p no:cacheprovider -W ignore -k "o4_ or fake_chanbara or fake_keyon"` (after A3) | all passed, 0 failed, 0 skipped: O4's tests untouched by S10-S13 |

### PART B -- the FakeGame for O5's route, then the driver's O5 tests
1. **B0:** the PART's baseline of the whole `tests/test_harness.py` (passed / xfailed / skipped), run alone, from this
   worktree with the templates extracted. Expected: the branch point's count (measured before A0 and recorded in A0's
   commit message) plus PART A's 18 new tests; any other difference is explained before B1.
2. **B1: H13, H14, H15** (`fakegame.py`): `story_suppress` in `_story_store`/`_story_start`/`_story_stop` (each a G21 pin
   from A0's O4 baseline: re-baselined by name with its reason in this commit); `_VisitBeat` with the step vocabulary and
   the stairs step; `_next_beat`'s and `_start_machine`'s `"visit"` dispatch (re-baselined); H15's knobs; and the eleven
   fake tests of 3.1-3.3, each with its break. No existing test's fake changes.
3. **B2: the O5 route builder** (`_o5_route` and the fixture registration, test-side, 3.4) and
   `test_fake_visit_route_plays_to_151_unattended` (a scripted player, not the driver: the builder's four visits
   play to "151" with a director pressing Confirm on every page, Down + Confirm on 128 and walking the stair straight
   west; the trace with `story_suppress` holds exactly 4.16's pattern).
4. **B3: the driver on the fake** -- O5's predictions on the fixture's fields (`_o5_pred`: the cell (30820, 1190,
   visit 1), the guard, the witness stub, `side_ends` {S: [30810], F: [31244]}, the members). Tests (S at 60 fps mean
   ticks, F through the members at 31 fps quantized where named; `wait_scale` 0.25):
   - `test_o5_drive_walks_the_stairs_and_answers_her_face_on_the_fake` -- S and F: beats `stairs` and `choice128`; the
     step row `done`, `lost` x <= -1100; the `guard` row (open before 128, no press in [first, close) but the answer's);
     the choice row index 1, `took.landed`, `selected_before` 1; with the trace and `story_suppress`: visit 3's first
     emitted row ip57, four `c` rows of place 153, the end row 151 ip22 (31244 on F), no A-MISMATCH; `end_state`; with
     `forbid_live` True no forbidden row. Break: drop S11 (a blind `choose`).
   - `test_o5_drive_guard_closes_the_stray_press_race` -- a stale read right after 127's closing press (a wrapped
     `Session.state` returning the previous document once) plus a 1.0 s send stall on the next press: with the guard,
     no press decided on the stale sample, the run covered; with a mutant guard keyed on wall time the stale press
     lands on 128 (path 0); and the guard with a stalled LEGITIMATE re-press (the first press only finished 127's
     type-out): V17 (driver) by the guard's attribution, never V2. Break: no page-once (plain rule 7).
   - `test_o5_drive_choose_landed_repress_while_128_types` -- `settle_s` 0.3 and 128's type-out 1.0 s: the first Confirm
     completes the text, the second lands; one choice row. Break: a blind `choose` (the re-ask reads V2 by the game).
   - `test_o5_drive_unlanded_answer_is_the_drivers_v17` -- `confirm_deaf` 5: V17 driver after 3 Confirms. Break: count
     it answered (V2, game).
   - `test_o5_drive_outside_cursor_move_is_v13` -- `cursor_to` after the select: V13 (driver), the trace's ip1741 0; a
     stub witness reporting input at 128: V13 with an `input` row. Break: trust the logged index.
   - `test_o5_drive_control_off_the_cell_is_v4` -- `grant_at` in 154: V4 game at [154, 1190]; at 153@316: V4 game at
     [153, 1190] (S13). Break: drop `visit` (the step runs at 316: V7 driver).
   - `test_o5_drive_side_scene_is_one_interrupt` -- `side_scene_at` 5: `interrupted` once, the pages, the re-grant,
     then `done`; two: V7 driver. Break: `interrupts` 0.
   - `test_o5_drive_back_door_is_the_drivers_v11` -- a mutant table walking east into e28: V11 driver, the step row's
     `door` 153.e28 and `landed` "150"; its post-landing rows backed. Break: e28 registered `dormant`.
   - `test_o5_drive_never_reaching_the_contour_is_v7` -- `no_contour`: `failed` twice, V7 driver.
   - `test_o5_drive_fork_landing_in_real_151_is_v19` -- F with `land_real` on the last `field`: V19 game.
   - `test_o5_drive_page_in_the_quiet_window_is_v17_observed` -- a page queued between 127's going and 128: V17, an
     `observed` row quiet_page.
   - `test_o5_drive_no_choice_within_the_cap_is_v14` -- `gap_ticks` 600 at `quiet_cap_s` 2: V14 game.
   - `test_o5_drive_choice_gone_unanswered_is_v17_observed` -- `stray_confirm_at_ready`: V17 with an `observed`
     choice_gone row; no press of the driver's in the window.
   - `test_o5_drive_stop_page_in_the_start_is_v5_driver` -- `error_window`: V5 driver at [153, 1190], nothing pressed.
   - `test_o5_drive_climbs_the_real_stair_on_the_fake` -- the fake's floor `PlayerWalkmesh(stock 153, closed=the 33)`
     with `clearance` 80 and `height_at` from the real mesh; the driver's `floor_for` the same: the walk from (1105,
     -78) meets the contour at x <= -1284, the evidence holds. Reads the install (a skip-with-warning without it: a
     skip fails G26).
   In this commit every `test_o5_*`, `test_fake_visit_*` and `test_fake_story_suppress_*` name goes into
   `REQUIRED_TESTS_O5` and G26 joins the gate.
5. **B4:** the whole `tests/test_harness.py` alone: B0's counts + every new test passed, B0's xfails, 0 skipped, 0 failed.

**PART B REQUIRED-GREEN:**

| When | Command | Expected |
|---|---|---|
| B0, and B4 | `py -m pytest tests/test_harness.py -q -p no:cacheprovider -W ignore` (alone) | B4: B0's counts + every new test passed, B0's xfails, 0 skipped, 0 failed |
| after B1 | `... -k "fake_visit or fake_story_suppress"` | 11 passed (B2: 12), 0 failed, 0 skipped |
| after B1-B3 | `... -k "o1_ or o2_ or o3_ or o4_ or segment or fake_"` | all passed, 0 failed, 0 skipped |
| after B3 | `... -k "o5_"` | 15 passed, 0 failed, 0 skipped |
| after every B step | `py studies/story-trace/segment_regress.py` | exit 0; G1-G25 PASS (G21: each re-baseline row named in its commit), G26 from B3 |

### PART C -- O5 itself
1. **C0: measure, read-only.** From the worktree, on O4's build (`C:\gd\_ns_playtest\o4\build`, never written): the
   route members' byte diffs against their donors, per language (O5-BUILD's pins), and the chain's `campaign.toml`
   (route members 31244/31245/31246 -- anything else STOPS PART C until the predictions are re-derived). No commit (the
   numbers go into C1's `o5_forks.json` `built.measured`).
2. **C1: `o5_hallway.py`** (1.3, sections 4-6: the draft, the checks LANDING, CHOICE, WALK, the offline checks with
   the route pins, O5-CENSUS per entrance, O5-REGIONS, O5-GOALS, the preflight extras, `trace_summary`, the CLI),
   `o5_forks.json` (6.4), the `.gitattributes` line for `o5_predictions*.json`. Tests (into `REQUIRED_TESTS_O5`):
   `test_o5_hallway_draft_reads_the_chain_from_campaign`; `test_o5_hallway_freeze_refuses` (each refusal of 7.3);
   `test_o5_hallway_route_builder_matches_the_keys` (the test-side builder's stores == the draft's writes, chain,
   masked and start rows); `test_o5_hallway_census_proves_inert_per_entrance` (a synthetic Main_Init instancing an
   entry at 316 only fails the proof at 316; e15's shared proof); `test_o5_hallway_regions_roles`;
   `test_o5_hallway_goals_contour` (synthetic mesh: a route that never reaches the contour FAILS (c)); 
   `test_o5_hallway_preflight_verdicts` (P-DONOR over 151/153/154, P-TEXT3 strict, no P-GATE row).
3. **C2: `o5_dryrun.py`** -- every case and unit of section 8 as registered, O3's EXACT `case()`. G27 joins the gate with
   `O5_DRYRUN_FLOOR` = the count C2 prints; `test_o5_hallway_trace_summary_cuts_at_end_places` lands here (it reads the
   dry run's renderer, O4's C2 #11).
4. **C3: `o5_rehearse.py`** + `--rehearsal-report`. Tests (every one with `warp_arrive_control` False and the engine's
   `soft_reset_ui`): `test_o5_rehearsal_plumbing_on_the_fake` (R-STAIRS: the record holds every 7.2 section, the race
   margin, 128 as published, `end_run`'s rows); `test_o5_rehearsal_walk_void_stops_mid_walk_on_the_fake` (R-WALK-VOID:
   the stop mid-walk, nothing pressed after, `recover-warp` 4600 and the title); `test_o5_rehearsal_smoke_sends_no_
   storytrace_on_the_fake` (F-SMOKE: three pairs, each with its own entrance and SC, no `storytrace` step executed);
   `test_o5_rehearsal_fpass_runs_untraced_to_the_member_on_the_fake` (F-PASS: no `storytrace` step, `forbid_live`
   False, reached "member(151)"); `test_o5_rehearsal_stage_ids_follow_the_chain`.
5. **C4: the O5 section in `PLAN.md`** -- the question, the segment, the sides and their ends, the stored choice and the
   guard, the walk, the suppression pattern and its scope, the checks, "draft: rehearsals pending, freeze pending", "a
   US session" in its heading. The brief's milestone line (CLAUDE.md section 10) is left as it is.

**PART C REQUIRED-GREEN** (after each of C1-C4, as far as it exists):

| Command | Expected |
|---|---|
| `py studies/story-trace/o5_hallway.py --offline-check` | exit 0; "predictions: the draft"; "chain: member(153) 31245, member(154) 31246, member(151) 31244"; 6 PASS -- O5-BUILD (140 files, every language its own donor's; the route members' diffs exactly their in-chain Field() operands), O5-KEYS (6.1's line), O5-TEXT (block 3: 7 byte-equal of 7), O5-CENSUS (6.1's line), O5-REGIONS (6.1's line), O5-GOALS (the step, the route length, the contour crossed at ~(-1482, 527), the evidence sound) |
| `py studies/story-trace/o5_hallway.py --preflight` | exit 0, ALL GREEN (P-MANIFEST, P-DEPLOY, P-EB, P-FLOOR, P-STOCK, P-TEXT3, P-RECOVERY, P-DONOR, P-SETTINGS, P-PAD, P-OVERRIDE, P-ENGINE) -- or the exact failing line reported to the lead |
| `py studies/story-trace/o5_hallway.py --draft` | exit 0; the draft JSON: `side_ends` {"S": [151], "F": [31244]}, `visits` [153, 154, 153], the guard, the witness, `engine` the pinned sha, `rehearsals` [] |
| `py studies/story-trace/o5_dryrun.py` | exit 0; "N/N cases as registered" (from C2) |
| `py studies/story-trace/segment_regress.py` | exit 0; G1-G26, and G27 from C2 |
| `py -m pytest tests/test_harness.py -q -p no:cacheprovider -W ignore -k "o5_ or fake_visit or fake_story_suppress"` | all passed, 0 failed, 0 skipped, every `REQUIRED_TESTS_O5` name among them |

Then the lead's sequence (7.1-7.4): `--preflight`, the rehearsals, the freeze checklist, `--freeze` (v1), the session.

---

## 10. Open risks (what only the game can settle)
1. **The grant and the walk** (F1): the grant position is the bytes' (stage 1's Walk(1105,-78)); the loss sample's
   position and latency (the contour, the teleport or the climb) are unmeasured; the stair's slopes (0.85-0.93) and wall
   contacts on the curve are unwalked by the harness (the harness has never walked a stacked field: 153 is the first).
   A walk that stalls on the stair is V7 (driver) and re-runs; F1 STOPs a systematic failure.
2. **The race and 128's publication** (F2, F3): the type-out times of 127 and 128 ([SPED=2]) are estimates; 128's
   options may publish with the first line short its first character (O1) or intact (O4): the rule matches either.
   A guarded stray is V17 (driver), never a finding; F2 decides the fallback.
3. **The suppression pattern in game** (F4): derived from the sink's source; R-FULL is its first measurement. A different
   pattern changes LANDING (b)'s re-entry row and the counts -- re-derived at the byte level before the freeze, never
   loosened.
4. **s62's VIB fix on member(153)** (F14): never exercised in game; F-PASS runs it before the freeze. A throw aborts the
   frame (dropped stores): F-PASS STOPs before the session ever sees it.
5. **The [TIME=20] [NFOC] windows under Confirm** (F8): expected inert (O4's 150).
6. **The end-state race** (F5): Byte[8] is out of the claim; the live read of the other nine stays stable through 151's
   prologue (equal values).
7. **Recovery from mid-walk** (F7): `end_run`'s warp from 153 with control held is unmeasured (the same FieldHUD as O4's
   fight); R-WALK-VOID proves it.
8. **The hidden colliders** (F12): published with `shown` False (critic #12); a planner disc round them costs nothing on
   this route (>= 1327 u off).
9. **A pad or a hand at the machine** (F11): the witness polls the whole run between blocking calls; input shorter than
   a gap is unseen -- but at the choice, the answer's own `selected_before` reading closes that gap (S11).
10. **The shared install**: another session's deploy, a re-wired New Game or an engine rebuild mid-session is A-INSTALL
    (6.3); the lead re-runs `--preflight` on the session's own launch (G1).

Closed by the bytes or the source (no longer open): the end row's emission (0.2 #1); the revisit's suppression (0.2 #2);
the evidence's soundness (O5-GOALS (d)); choice 128's cursor (ETb.cs:100-103); Brahne at 110 (shown, size 1, the defined
player, no `Map.Bit[158]`: no control); no SC rung, no battle, FMV, ATE or naming before the cut; every route `Field()`
retargeted (O5-BUILD).

---

## 11. Critique log

### 11.1 The research critic's twelve
Each re-checked in the bytes or the engine source; none disproved.

| # | Problem | Re-checked | Disposition |
|---|---|---|---|
| 1 (major) | The chosen end row does not exist: the sink suppresses revisit prologue stores; FakeGame does not model it. | StoryTrace.cs:101-140, :374-401, :540-557; the stock 153/154/151 prologues; segment_trace.py:127-136 | ADOPTED with decision 1: candidate 3's end row 151 e0 t0 ip22 IS emitted (a new site: 0.2 #1); the revisit's pattern derived (0.2 #2, 4.16) and its first emitted row pinned (LANDING (b), start-scoped); H13 models the sink in the fake; the dry run's renderer models it; the counts recounted (21 + 4 rows, 15 keys); the scope line names the compared suppressed stores (5.4). |
| 2 (major) | The quiet window alone does not close the race: page-once is needed. | segment_drive.py rule 7, `quiet_tick`, `policy_page`; 153 e31 t1 ip663-670, e3 t1 ip1713-1724; Dialog.cs:798-808 | ADOPTED (S10): page-once keyed on the window's RAW and judged on GAME frames, the quiet window from the first sample without the marker, closed by the published choice; the residual (a stalled send) attributed V17 by the press's accepted frame (2.5.5); F2 measures the margin; the fallback designed (2.5.7). |
| 3 (major) | Candidate 3 is the cleaner primary. | rule 1, the live scan, `end_row`, `Segment.cut` | ADOPTED (decision 1): no `end_visit` code at all; O6 starts by a raw warp into 31244 at 110. |
| 4 (minor) | Part of the end state is written at the arrival; Byte[8] races 151 ip315. | 151 e0 t0 ip274-315 | ADOPTED: Byte[8] out of `end_state`, its end value the trace's last pre-cut write (STATE (a)); Bit[3855]/[3854] not registered; the byte8-race-both PASS case. |
| 5 (minor) | The emitted row pattern is start-dependent too. | StoryTrace.cs:383-401; field 70's override prologue | ADOPTED: the scope line (5.4), LANDING (b)'s pin named start-scoped, "never reuse O5's row expectations against a chained true-run trace". |
| 6 (minor) | `choose()` is fire-and-forget; a re-ask after an unlanded answer reads V2 by the game. | session.py `choose`, `_take_default_choice`, `_choice_left`; Dialog.cs:798-808 | ADOPTED (S11): `choose_landed`, the driver's own V17 for an unlanded answer, `settle_s` frozen above 128's measured type-out (F6). |
| 7 (minor) | The forbidden schema cannot express a value or a count; a `cause: "choice"` pattern in 153 backs the route's own answer. | segment_drive.py FORBID_KEYS, `backing` | ADOPTED: no `choice` pattern; the pick is WRITES-exact and CHOICE (a)-(c) -- (a) counts the site's `c` rows too, since a same-value repeat is suppressed. |
| 8 (minor) | The preflight drops O4's P-OVERRIDE and the rest. | the live override (1424 B, 2ce8887e) | ADOPTED: O4's set carried (6.2) but P-GATE and P-TEXT2 (11.2 #1). |
| 9 (minor) | The stock event names are wrong. | FF9DBAll.Events.cs:10, :13, :24 | ADOPTED: the EVT names in every `what` string and in this design; the kit's member names come from the scene names (4.1). |
| 10 (minor) | The outside-input witness runs only under the Chanbara policy. | segment_drive.py `go`, `poll_witness`; 153 e3 t1 ip1741 | ADOPTED (S12) and NARROWED at the choice: the answer's `selected_before` (S11) catches a cursor moved between the select and the Confirm, which a 50 ms witness can miss. |
| 11 (minor) | s62's VIB fix would get its first in-game exercise in the session. | HonoluluFieldMain.cs:93-104; 153 e3 t1 ip2443-2453 | ADOPTED: F-PASS (untraced, before the freeze, 7.1, F14). |
| 12 (minor) | Corrections: hidden objects are published; Blank is a body disc only; the re-plan numbers; the step lacks `start`. | HarnessAgent.cs:2321-2361; `wm153.py`, `route_check.py` | ADOPTED: `start` [1105, -78] in the step; F12 records the objects; O5-GOALS (c)(d) carries the contour and the evidence's soundness on the bytes. |

### 11.2 Where this design reads a decision's letter differently (each said, none relitigated)
1. **Decision 6's preflight set** names O4's; P-GATE (the +30% witness for member(64)) and P-TEXT for block 2 are O4's
   fight and fields alone -- carried, they would gate O5 on facts its route never reads. Every other check is carried.
2. **Decision 1's "verify against the s88 suppression"**: verified from the source (0.2 #1); R-FULL measures it (F4).
3. **Decision 3's "page-once on the marker page(s)"**: page-once applies to marker pages only; every other page keeps
   plain rule 7 (it carries a `seq` for the attribution). The hold-off keys on the window's RAW text (O4 keyed the
   rendered text, which can grow while 127 types).
4. **Decision 3's "re-ask after the driver's own unlanded answer is the driver's V-class"**: V17 (driver), the class O4
   gave "the driver's input not proven the frozen play"; V13 is kept for outside input (the cursor read off the pick).
5. **Decision 5's "Model it in the FakeGame"**: H13 is the sink's rule per site per epoch, both flush points, the
   site's fld/don on `c` rows; the published `suppressed` counter is left at 0 (no reader) so `_publish`, a G21 pin,
   stays untouched.
6. **Decision 7's "the 127 -> 128 race's frequency"**: measured passively in every guarded run (the race margin); an
   unguarded R-RACE is optional, by name.
7. **Decision 8's shared changes**: S13 (visit-scoped cells) is an addition no decision names -- without it a control
   grant at the revisit is the driver's V7 and invisible to VOID-ASYM (a) (0.2 #15). It is opt-in and O1-O4
   byte-identical.
8. **Decision 9**: the lead's merge of master meets three conflicts by construction (0.2 #16): `source_pins.json` (both
   sides append rows: keep all, per name in head order), `REQUIRED_TESTS_O3` (keep both additions), and possibly
   `segment_regress.py`'s neighbouring lines; then the whole gate and `tests/test_harness.py` run on the merged head.

### 11.3 As built (the implementer appends, PART by PART)
Where the design was silent or wrong, each the smallest correct thing, in O4's 11.4 form; and the review's findings, in
O4's 11.5 form.
