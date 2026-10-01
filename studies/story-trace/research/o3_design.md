# O3 -- the play under the trace: the design

**Status: DESIGN, offline.** Nothing is imported, built, deployed, launched or frozen; nothing NEEDS deploying (O3 runs
on O1's chain as it stands). The inputs are `o3_route.md` and `o3_research.json` in this folder: the reconciled route,
with the critic's twelve problems (`critique.problems`) overriding the route where the two conflict. This file folds
both into code-level decisions, in `o2_design.md`'s structure, and keeps what O2 learned. Every number below was
read, read-only, from the stock US `.eb` files (through the kit), the reconciler's listings
(`<scratchpad>/o3_research/reconcile/L{61,62,63}.txt`), the battle scenes' own `.eb` and raw16 (through the kit), the
live install (mod folders, `Memoria.ini`, `Memoria.log`) and the live Memoria source; section 0.2 says how. The
offline check (section 6) re-derives every one of them.

**The segment:** New Game, the trace armed, then a raw `warp <61 | member(61)=31211> 0 1155`. The route runs
61 (FMV003, the narrator, the curtain) -> 62 (Act I, then `Battle(0,338)`) -> battle 338 (King Leo) -> 63 (loaded
FRESH by the battle's own `RunBattleCode(37,63)`) -> `Field(64)` (63 e4 t1 ip828). It ends on ARRIVAL in real 64 on
both sides (the cut is 64's first row, e0 t0 ip22). SC holds 1155 throughout: there is no ladder. The F side is O1's
deployed whole-zone tshp chain (31200-31219); its members 31211/31212/31213 run here for the first time.

What O3 newly puts under the trace: a battle beat inside a segment driven by the beat-table driver, the s24
battle-return redirect (scene 338 bakes real 63; a fork run must land in 31213), a type-0 FMV under the driver's
watchdog, a segment with an empty SC ladder, and three members never loaded in game.

---

## 0. What this design decides, and what it found

### 0.1 Decided upstream (not relitigated)
- **The segment and its end.** Arrival in 61 -> 62 -> battle 338 -> 63 -> `Field(64)`; the end is the arrival in REAL
  64 on both sides (31213's `Field(64)` is not retargeted: the seam), cut at 64's first row.
- **The start.** Each run: New Game, `storytrace 1`, then the raw harness warp `warp 61 0 1155` (S) /
  `warp 31211 0 1155` (F) -- O2's form (`Segment.start_run`, unchanged). Not a replay of O2.
- **The session.** S F S F S F, `min_covered` 2 a side, at most 2 re-runs -- except that a FINDING class stops a side's
  re-runs (S2, 1.2).
- **The chain.** O1's: 61 -> 31211, 62 -> 31212, 63 -> 31213, deployed 2026-09-29 21:07 into FF9CustomMap with the
  rest of O1's 20 members. A LEGACY build: every member's jp/fr/gr/it/es `.eb` is US bytecode (`accept_us_build`, as
  O1), and text block 2's uk copy is the US text (a KNOWN-KIT-DEFECT line, never silent). Nothing is imported, built or
  deployed for O3; O1's chain is not touched, rebuilt or redeployed.
- **The freeze.** The lead freezes the predictions AFTER the in-game stock rehearsals and an F-side no-trace load
  smoke (section 7). The code ships `O3Segment.draft()` plus a `--freeze` CLI that refuses to overwrite.
- **The machinery.** O3 is built ON the shared machinery: `O3Segment` (a subclass of `O2Segment`), the battle beat as
  an OPT-IN registry in `segment_drive`, and the regression gate extended to O2 with its baseline captured FIRST.
  Every change to shared code keeps O1 and O2 analysing byte-identically (1.4).
- **The critic's twelve problems are binding** unless the bytes or the engine disprove one (section 11). None was
  disproved; one proposed remedy (the movie state in the watchdog's signature) is impossible without an engine patch,
  and the other remedy the critic offered is taken (11, #4).

### 0.2 Found while designing (each verified offline, read-only)
1. **Battle 338's one store, located.** `BSC_TH_E002`'s script (read with `battle.battleai._scene_eb("TH_E002")`,
   walked with `eb.model.EbScript` + `storytrace.instruction_stores`) holds exactly ONE gEventGlobal store:
   `Global.Byte[206] := B_SYSVAR[0]` at entry 1 tag 1, abs 539, entry 1's `abs_start` 272, so **entry-relative ip
   267** -- the trace's `ip`. The same walk over `TH_E001` (O1's scene 336) gives e0 t1 ip93, e0 t1 ip168, e0 t1 ip213
   (Byte[199]), e1 t1 ip267, e2 t1 ip37, e3 t1 ip37 -- and O1e's traces hold exactly `(m 2, sid 1, tag 1, ip 267,
   Byte 206)` x64 + its count row, and `(m 2, sid 0, tag 1, ip 93)` x1, at fld 50 (S) / 31200 (F), don 50. So the
   trace's battle ip convention is calibrated, and O3 can pin every battle-mode row to `(1, 1, 267)` (O3-LANDING (b)).
2. **The scene, decoded.** 338 = `BSC_TH_E002` (`_scenedb.SCENES`); its raw16 (`battle.extract.read_scene_assets`,
   `battle.scene_codec.parse_scene`): flags **0x1839** -- 0x10 set (WinPose off: a scripted end reports 2,
   BTL_SCENE.cs:222, btl_scrp.cs:785-797), 0x20 (no escape), 0x8 (no EXP), 0x1 (preemptive); MaxHP King Leo (type 0)
   10186, Zenero 32, Benero 28. Entry 0 tag 0 [265] `RunBattleCode(37, 63)`; entry 1 tag 1 [587]
   `B_SYSLIST[1] B_MEMBER(36) const(10000) B_LE_E B_COUNT`: the end needs >= 186 damage to King Leo.
3. **Every drafted key is a real store.** The 43 sites of section 4 (24 writes, 3 chain keys, the forbidden site
   62 ip1345, 14 error-path sites, `start_first`) were run through O2-KEYS's machinery (`O2Segment.keys_check` on a
   synthetic predictions dict): "43 sites (43 keys), every op in its statement, 4 compound values computed from their
   priors, none masked". Of O3's targets only `Bit[191]` (boot_scratch) and `Bit[184]` (field_menu_guard) lie in the
   story-noise mask (`storytrace.noise_regions`); `Int16[11]` (bytes 22-23) does not.
4. **61, 62 and 63 hold no gateway and no hot-spot.** O2-REGIONS's census (`O2Segment.regions_check` over route
   [61, 62, 63] with no regions registered): "0 regions, 0 hot-spots, 0 gateways all registered". (64 has two
   gateways, to 153; it is the end field, never walked.) Every `EnableMove` in 61-63 sits behind `Map.Bit[158]==1`
   (61 e0 t0 ip399/ip440, 62 ip396/ip437 and e0 t10 ip630/ip671, 63 ip412/ip453), which nothing on the route sets.
5. **Text block 2, measured.** `O2`'s `text_rule` against each language's stock asset read by its ResourceManager
   path (`stock_text_assets(2)`): the O1 build (`C:\gd\_ns_playtest\o1\build`) and the live FF9CustomMap both read
   **6 byte-equal, KNOWN-KIT-DEFECT 1, FAIL 0**: uk ships stock us (3a6f3246c2; stock uk 7ac9f17435).
6. **The live install, read.** No mod folder overrides 61, 62, 63 or 64 (`storytrace.stock_overrides`); field 70's
   New-Game override is FF9CustomMap-world's; 4600 (the recovery field) is registered in FF9CustomMap-world.
   ForkDonorPatch: 73 rows, all in FF9CustomMap; donors 61, 62, 63 appear once each (31211, 31212, 31213); the only
   duplicated donors are 312 and 350-359. Members 31211-31213 are registered once each (O1_TH_BST, O1_TH_STG,
   O1_TSHP_TH_STG). `o1_opening.py --preflight`: 5/5 PASS; `--offline-check`: O1-BUILD "140 files; other languages: 15
   own-language, 105 us-build", O1-KEYS "4 keys".
7. **The launch's own donor map is readable.** The engine logs a ForkDonorPatch collision only as a warning
   (DataPatchers.cs:156-160: "[DataPatchers] ForkDonorPatch: donor field {donor} is forked by both {prev} and {fork}
   -> remap DISABLED") and logs "[DataPatchers] Initialized" (:128) once the patchers ran; there is no positive
   "mapped once" line. Today's `Memoria.log` (launch 2026-09-30 19:27:44) holds the warning for 312 and 350-359 only,
   then "Initialized", then "Updating text localization [English(US)]". So P-DONOR-LOG reads the ABSENCE of the warning
   for 61-63 on a log that proves the patchers ran, and its scan is calibrated on real lines.
8. **The id flip is inside the battle.** `HonoluluBattleMain.UpdateOverFrame` (:732-741) folds result 2 into 1 AND sets
   `fldMapNo := IsForkField(PreBattleFieldNo) ? ForkSiblingField(nextMapNo) : nextMapNo` (63 / 31213) on the SAME
   frame, then `GoToBattleResult()` -- while `SceneDirector.IsBattleScene()` (the published `in_battle`) is still true.
   The agent publishes the raw `fldMapNo` (HarnessAgent.cs:1537). So for a stretch of samples the run reads
   `in_battle` AND field 63/31213 -- the critic's blocker (a). `fight()` reads 2 or 1 depending on the sample: won is
   `[1, 2]`.
9. **The warp is refused in a battle, at once.** `Ff9mkDebugMenu.Warp` returns false unless the UI state is FieldHUD
   (:2083); the agent then throws "warp refused (not on a field?)" (HarnessAgent.cs:652-656). So `end_run`'s warp fails
   fast inside a battle; the cost is `restore_baseline`'s `close_ui` (6 Cancels, then a 20 s wait for a field) before
   the soft reset, which has never been tried from a battle. The FakeGame swallows the soft reset outside
   FieldHUD/WorldHUD (fakegame.py:1781) and does not refuse a warp in a battle (fakegame.py:931-946).
10. **`fight()` and `leave_battle()` today.** `fight()` raises a plain HarnessError on both no-result exits (max turns,
    session.py:7407-7411; timeout, :7442-7444) -- nothing tells them apart from an instrument failure. `leave_battle()`
    presses Confirm every 20 frames while `in_battle` or the UI reads BattleHUD/BattleResult (:7457-7463) and logs
    neither its presses nor the states it pressed in.
11. **The agent publishes no movie state.** HarnessAgent.cs has no MBG/movie/cinematic field; during FMV003 nothing in
    the driver's progress signature (segment_drive.py:1067-1069) changes. Adding the movie to the signature needs an
    agent patch (an engine rebuild); sizing `no_progress_s` from the rehearsals is the fix (11, #4).
12. **The baseline holds at HEAD.** `o2_alexandria.py --analyse <story-o2> --predictions o2_predictions_v1.json`
    reproduces the archived `o2_report.txt` byte for byte (the CLI adds print's newline), PROVEN, 15 checks;
    `o2_dryrun.py --predictions o2_predictions_v1.json` reads "86/86 cases as registered" (65 s); `o2_alexandria.py
    --offline-check` 5 PASS (O2-BUILD 126 files own-language, O2-KEYS 48 sites (50 keys), O2-TEXT 7 byte-equal,
    O2-REGIONS 26 regions 17 hot-spots 21 gateways, O2-GOALS 14 steps). O2's START detail hard-codes "3 residue rows"
    (o2_alexandria.py:1347): O3 writes its own START (its start has two).
13. **The settings the runs live under.** `Memoria.ini`: `[Battle] Enabled 1, SFXRework 1, Speed 5 (Simultaneous),
    CustomBattleFlagsMeaning 0`; `[Cheats] Enabled 1, AutoBattle 1, SpeedMode 1, SpeedFactor 3, SpeedTimer 0,
    BattleAssistance 1, Attack9999 1, NoRandomEncounter 1, MasterSkill 0, LvMax 0, GilMax 0`; `[Hacks] Enabled 1,
    AllCharactersAvailable 1, SwordplayAssistance 1, DisableNameChoice 0`; `[Control] SoftReset 1, TurboDialog 1,
    BattleAutoConfirm 1, DialogProgressButtons "Confirm"`. They shape the battle's timing (SYSVAR[25]/[30] at King
    Leo's latch), not its stores; they are fingerprinted and frozen (4.13).
14. **The map's wording, corrected** (the critic's #4 and #10, re-read in the listings): 61's pages come AFTER FMV003's
    end (61 e2 t1 ip324 passes at movie frame 1100, then ip371-ip422 loops until `SYSVAR[15]&127 == 1`, the movie's end;
    frame 1100 only times sound cues); 61-63 DO read keys -- Bit[184], Byte[13], Int16[9], Byte[14] and Int16[11] in e0
    t0 (ip30-ip189; Bit[184], Byte[13] and Byte[14] before writing them), and Byte[8], UInt16[21] and Byte[303] after
    writing them; O1 already played FMV002 inside its segment -- what is new is a type-0 FMV under `segment_drive`'s
    watchdog; and an incoming Byte[13] of 2 would not stall a run (the page rule would confirm the error window) -- O3
    makes that window a deliberate VOID instead (2.2, rule 7).

---

## 1. Module layout

### 1.1 Files

| File (in `studies/story-trace/` unless a path is given) | | What it holds |
|---|---|---|
| `segment_regress.py` | edit, FIRST | The regression gate extended to O2: items G8-G12 (1.4) beside O1's G1-G7, and `--capture-o2`. Its O2 baseline is captured BEFORE any other code change. |
| `research/o2_regress_baseline.json` | new, FIRST | The captured O2 baseline (1.4 G8-G12), LF, `-text`. |
| `segment_trace.py` | edit (PART A) | S1 (a registered battle's won set in the coverage rule), S2 (`rerun.stop_on`), S3 (`end_run` from inside a battle). |
| `segment_drive.py` | edit (PART B) | S4: the opt-in battle registry and its executor, `stop_pages`, V15 and V16. |
| `o3_prima_vista.py` | new | `O3Segment(O2Segment)`: the draft predictions, O3's checks and report, the offline checks and preflight extras, `trace_summary`, the CLI (`--offline-check`, `--preflight`, `--draft`, `--analyse`, `--freeze`, `--rehearsal-report`), module-level `run(g)`. |
| `o3_forks.json` | new | The chain manifest: O1's members, `deployed: true`, pointing at O1's deploy and revert record (6.4). |
| `o3_dryrun.py` | new | O3's synthetic sessions, units and offline mutants (section 8). |
| `o3_rehearse.py` | new | The stock rehearsal stages and the F-side load smoke for `tools/play.py` (section 7). |
| `.gitattributes` | edit | `studies/story-trace/research/o2_regress_baseline.json -text` (A0) and `studies/story-trace/o3_predictions*.json -text` (C1, before any freeze). |
| `tools/harness/channel.py` | edit (PART B) | H7's `FightTimeout(HarnessError)`, beside `HarnessError` and `StepRefused` (:86-90), exported where they are. |
| `tools/harness/session.py` | edit (PART B) | H7 (`fight` raises `FightTimeout`; `last_fight` fields), H8 (`leave_battle(stop_on_field=)`, `last_leave`). |
| `tools/harness/fakegame.py` | edit (PART B) | H9 (opt-in knobs: a scripted battle end, a battle exit into another field, `warp_field_only`, `soft_reset_in_battle`, a movie beat with the skip dialog). |
| `ff9mapkit/tests/test_harness.py` | edit | The FakeGame and unit tests named in sections 1.2, 3 and 9. |
| `PLAN.md` | edit (PART C) | The O3 section: "draft: rehearsals pending, freeze pending". |

`o1_opening.py`, `o1_dryrun.py`, `o2_alexandria.py`, `o2_dryrun.py`, `o2_rehearse.py` and every frozen predictions file
are NOT edited. That they keep their outputs is the gate.

### 1.2 The shared changes (each opt-in or behaviour-neutral for O1 and O2)

**S1 -- `Segment.read_session`: a registered battle is judged by its row's won set** (segment_trace.py:653-657).
Today a beat named `battle` is done when its value is in `pred["battle_won"]` (O1's legacy rule), and any other beat
when its value is truthy -- so an O3 beat holding a result 3 (defeat) would read done. The change:
```python
won = {b["beat"]: list(b["won"]) for b in pred.get("battles") or ()}

def done(b):
    if b in won:
        return beats.get(b) in won[b]
    return beats.get(b) in pred["battle_won"] if b == "battle" else beats.get(b)
missed = [b for b in pred["beats"] if not done(b)]
if rec.get("end") == "reached" and missed:
    why = (f"beats not done: {missed} (battle result {beats.get('battle')})" if not won   # O1's text, exactly
           else f"beats not done: {missed} (" + ", ".join(f"{b} result {beats.get(b)}" for b in won) + ")")
```
O1 and O2 carry no `battles` key: their path and text are unchanged.
Test (A1): `test_segment_read_session_judges_a_registered_battle_by_its_won` -- a stub session (the `_stub_segment`
pattern) whose runs record `{"leo": 2}`, `{"leo": 1}`, `{"leo": 3}`, `{"leo": None}` against `battles: [{"beat": "leo",
"won": [1, 2], ...}]`: covered, covered, A-BEATS ("leo result 3"), A-BEATS.

**S2 -- `Segment.run`: a FINDING class stops its side's re-runs** (segment_trace.py:585-594). `pred["rerun"]` may
name `stop_on` (a list of V-classes). A side with any run VOID in one of them is not re-run however short it is:
re-running a finding only repeats it (the s24 leak, V16), and VOID-ASYM already reads it (5.3). The re-run loop reads
the session once per pass (today it reads it twice inside the comprehension):
```python
stop_on = set(pred["rerun"].get("stop_on") or ())
while reruns < pred["rerun"]["max"]:
    runs = self.read_session(g.run_dir, pred, session=session)
    held = {s for s in SIDES if any(r["side"] == s and r["rec"].get("v") in stop_on for r in runs)}
    short = [s for s in SIDES if s not in held and
             sum(1 for r in runs if r["side"] == s and r["covered"]) < pred["min_covered"]]
    if held:
        session["rerun_held"] = {s: sorted({r["rec"]["v"] for r in runs if r["side"] == s
                                             and r["rec"].get("v") in stop_on}) for s in sorted(held)}
    ...
```
No `stop_on` (O1, O2): exactly today's behaviour; `rerun_held` is written only when non-empty.
Test (A2): `test_segment_rerun_stops_on_a_finding_class` -- `_stub_segment` (it gains a `rerun` keyword) whose F runs
VOID with `v="V16"`: with `stop_on: ["V16"]` the session is exactly S F S F S F (no re-run) and records
`rerun_held {"F": ["V16"]}`; the control, without `stop_on`, re-runs F twice.

**S3 -- `Segment.end_run` from inside a battle** (segment_trace.py:460-480). A run stopped mid-battle (V15, the
budget, an exception) must not spend the refused warp and `close_ui`'s 20 s before the one rung that can work there:
```python
if g.state.ui_state != "Title":
    if g.state.in_battle:
        log.append({"k": "recover-in-battle", "scene": g.state.battle.get("scene")})
        try:
            g.soft_reset()
            log.append({"k": "recover-reset"})
        except HarnessError as err:
            log.append({"k": "recover-reset-failed", "why": str(err)[:200]})
    else:
        ...today's warp to `recovery` and its log rows...
ok, why = g.restore_baseline()        # unchanged from here
```
O1 and O2 never end a run in a battle on their covered paths; a run stopped mid-battle now takes the soft reset
first. No analysis output changes.
Tests: (A3) `test_segment_end_run_resets_from_inside_a_battle_without_a_warp` -- a stub session object (a
`SimpleNamespace` with `state.in_battle` True, recording `warp`/`soft_reset`/`restore_baseline`): no warp, one soft
reset, then the ladder; (B5, once H9 lands) `test_segment_end_run_from_a_battle_on_the_fake` -- the FakeGame with
`warp_field_only` and `soft_reset_in_battle`: the title, no warp executed; with `soft_reset_in_battle` False: "the
title could not be restored".

**S4 -- `segment_drive`: the battle registry, `stop_pages`, V15 and V16** (PART B; section 2). Every addition is
read only when the predictions carry it (`battles`, `stop_pages`): with neither, the driver is byte-for-byte today's
loop, which the O2 driver tests (G12) prove.

### 1.3 `o3_prima_vista.py`

`O3Segment(o2_alexandria.O2Segment)`:
- `tag = "O3"`, `predictions = HERE / "o3_predictions_v1.json"`, `manifest = HERE / "o3_forks.json"`,
  `session_file = "o3_session.json"`, `report_file = "o3_report.txt"`, `chain_dir = C:\gd\_ns_playtest\o1\fork`,
  `build_dir = C:\gd\_ns_playtest\o1\build`, **`accept_us_build = True`**, `recovery = 4600`.
- `core_ids = ("START", "NO-SC", "CHAIN", "RESIDUE", "WRITES", "NULL", "STABLE", "SEAM", "LANDING", "MASKED",
  "STATE", "JOIN")`; `titles` gives every check its O3 text (5.3, 6.1, 6.2).

**Inherited unchanged from O2Segment:** `current` (the draft until frozen), `text_check` (block 2 through
`pred["text_block"]`), `regions_check`, `read_session`, `_run_log`, `forbidden_check`, `void_asym_check`,
`span_check` (CHAIN), `residue_check`, `null_check`/`stable_check`/`join_check` (the base's), `seam_check` (through
`pred["seam"]`), `masked_check`, `history`/`suppressed`/`state_check`, `add_arguments`, `drive` (`segment_drive.drive`:
the battle beat is in the predictions, so `drive` itself does not change).

**Overridden:**
- `draft()` -- section 4. Members and names come from O1's `campaign.toml` (`ST.chain_from_campaign`), asserted to be
  exactly O1's twenty (`o1_forks.json` members) and to map 31211 -> 61, 31212 -> 62, 31213 -> 63.
- `keys_check(pred, stock)` -- O2's machinery on a filtered copy, so O2's code is untouched:
  `super().keys_check({**pred, "ladder": [], "start_dependent": [], "noise": [], "forbidden_sites":
  pred["forbidden_sites"] + pred["error_path"]}, stock)`. O3's one noise pattern is O1's legacy battle-mode form, which
  has no field site to join; O3-SCENE proves it instead (6.1).
- `offline_extra` -- `[text_check, keys_check..., regions_check, scene_check]` (6.1). No GOALS: there is no table.
- `preflight_extra` -- O2's (P-TEXT on block 2, P-RECOVERY) + P-DONOR + P-SETTINGS (6.2).
- `capabilities(g)` -- O2's (P-CAP, P-OBJECTS, P-LANG) + P-DONOR-LOG (6.2).
- `fingerprint_extra` -- O2's (`override70`, `text2`, `lang`) + `settings` (6.3).
- `why_void` -- O2's (A-NOSTART, A-FORBIDDEN, A-MISMATCH) + A-START (5.1).
- `core_checks` -- 5.3, in `core_ids` order: O3's own `start_check`, `no_sc_check`, `writes_check` (exact),
  `landing_check`; the inherited ones for the rest.
- `report_extra` -- O3's own sections (5.4); O2's names O2's scope line and SC timeline.
- `handle(args)` -- `--rehearsal-report` reads `o3_rehearsal.json` (O3's own `rehearsal_report`); everything else is
  O2's `handle`.

**Module functions (pure):** `scene_census(scene_name)` (O3-SCENE's reader), `ini_settings(text, keys)` (the
engine's ini reading: the last assignment wins, sections and keys case-insensitive), `donor_log(log_text, donors)` (P-DONOR-LOG's
reader: `(initialized, [warning lines naming a donor])`), `trace_summary(rows, pred, ...)` (O2's shape for O3's lists,
plus the battle's rows and the first field row after them; 7.2), `rehearsal_report(run_dir)`, `run(g)` = `O3.run(g)`,
`main(argv)`.

O3 imports `o2_alexandria`, so that module is now shared code: any later edit to it must keep O2's gate (G8-G12) AND
O3's dry run green.

### 1.4 The regression gate extended to O2 (`segment_regress.py`)

The implementer extends the gate and captures its O2 baseline FIRST (A0), before any other code change, at the
design commit. The O2 items import only O2's modules (`o2_alexandria`, `o2_dryrun`) through their public names,
inside their functions (the O1 items keep importing only O1's). From then on the gate is run after every commit that
touches shared code. It exits 0 only if every item passes; 2 if an archive or a baseline is missing (the gate did not
run, which is not a pass).

`O2S = C:\gd\Dream-World-IX\.harness-runs\20260930-192740-story-o2`, `V1 = HERE / "o2_predictions_v1.json"`.

| Item | Check |
|---|---|
| G0' | `py studies/story-trace/segment_regress.py --capture-o2` (once, before any O3 code change) writes `research/o2_regress_baseline.json` (LF, `-text`): the full `(checks, report)` of O2S with V1; every `o2_dryrun` session case's `(checks, report)` and "predictions-changed"'s; every unit case's and offline mutant's `(name, ok, detail)`; `O2.offline_check(V1)`; the G12 tests collected; the HEAD and V1's sha. It refuses an existing file, and refuses to write unless G8-G12's baseline-free halves pass (the archive equality, PROVEN, `run_cases(V1)` 0, 5 PASS offline, the pytest selection green). |
| G8 | `O2.analyse(O2S, pred_path=V1)`: the report equals `(O2S/"o2_report.txt").read_text(encoding="utf-8")` exactly, and the baseline's; the checks are the baseline's; the verdict PROVEN with 15 checks, all True. |
| G9 | `py studies/story-trace/o2_alexandria.py --analyse O2S --predictions V1` exits 0 and prints that report (plus print's newline). |
| G10 | Every `o2_dryrun` case's `(checks, report)` is byte-equal to the baseline's, every unit and offline mutant's `(name, ok, detail)` too, and `o2_dryrun.run_cases(V1)` returns 0 printing "86/86 cases as registered". The gate replicates `run_cases`'s loop step for step (as G3 does O1's), so every session gets the label `run_cases` gives it (`s0`, `s1`, ... in creation order). |
| G11 | `O2.offline_check(V1)` equals the baseline's `[(ok, what, detail)]` (it reads the O2 build and the stock assets, read-only). |
| G12 | `pytest tests/test_harness.py -q -p no:cacheprovider -W ignore -k "o2_ or rehearse"` from `ff9mapkit/`: all passed, 0 failed, 0 skipped, 0 errors; every test the baseline collected still runs, plus every name in `REQUIRED_TESTS_O2`. |

O1's G1-G7 stay as they are; tests O3 adds whose names match G7's selection (`test_segment_*`) join it through
`REQUIRED_TESTS` as each lands, and tests matching G12's (`test_o3_rehearse_*`) through `REQUIRED_TESTS_O2`.

---

## 2. The drive

### 2.1 The model (keys the driver reads; the rest of the predictions is the analysis's)
- **`table: []`.** 61, 62 and 63 never grant control (0.2 #4), so there is no cell: control anywhere is V4.
- **`battles`** -- the registry, a list of rows, each STRICT (`segment_drive.battle_of`: an unknown key, a missing one
  or a wrong type raises `ValueError` before anything is driven, like `step_of`):
  ```json
  {"donor": 62, "sc": 1155, "scene": 338, "won": [1, 2], "lands": 63, "beat": "leo",
   "timeout_s": 180, "max_turns": 40, "land_s": 30,
   "why": "62 e4 t1 ip1293 Battle(0,338) = BSC_TH_E002 (King Leo, 10186): ends by script once King Leo's own cur.hp <= 10000 (>= 186 damage) -- RunBattleCode(33,1), result 2 (WinPose off), folded to 1 at the over frame; its own RunBattleCode(37,63) lands the run in 63, fresh (F: ForkSiblingField(63) = 31213, s24)"}
  ```
  `donor` is the place of the VISIT the battle began in; `sc` the published SC (null = any); `scene` the published
  `battle.scene` (`battleMapIndex`, HarnessAgent.cs:1815); `won` the results that count the beat done (S1); `lands`
  the place the battle must hand the run to; `beat` the beat it sets (its value is the result); `timeout_s` and
  `max_turns` bound `fight()`; `land_s` bounds the wait for the landing field's FieldHUD.
- **`stop_pages`** -- pages that VOID instead of being confirmed: `[{"match": "Env Play()", "why": "61-63's ambient
  error window 3 ('Error Env Play()  Slot=n', e0 t0 WindowAsync(6,0,3) + WaitWindow): Byte[13]/[14] arrived as 2 or 9"}]`.
  A page matches when `match` is a substring of its rendered text or of any `raw_texts` line.
- **`choices`**: O1's skip-movie rule only (2.5). **`naming: []`**. **`route: [61, 62, 63]`, `visits: [61, 62, 63]`,
  `end_fields: [64]`.** **`forbidden`**: O2's `off_route` pattern only (4.8). **`beats: ["leo"]`.**

### 2.2 The driver loop for O3 (O2's loop, rules in O2's order, with S4's two opt-in additions)
Every poll reads `st`, `sc` and `donor = place(fid, members)` as O2's does.
1. **End** (`fid in end_fields`, real 64 on both sides): the end state read (`read_end_state`), the last forbidden scan,
   `reached`. Unchanged.
   **The stall watchdog** runs after rule 1, unchanged (its signature cannot see a movie: 0.2 #11; `no_progress_s` is
   sized to cover FMV003, 4.12).
- **1b (new, opt-in: `battles` non-empty) -- a NEW battle.** `st.in_battle` and `st.battle_epoch > self.battle_seen`:
  the battle executor (2.3) runs and owns the loop until the landing field is up; then `continue`. It sits BEFORE
  rules 9, 2 and 3 so that the field id a battle publishes at its over frame (0.2 #8) is never read as a load, a leave
  or a visit. `self.battle_seen` starts at the epoch published when the drive starts (only deltas mean anything).
9. A field id <= 0: waited out. Unchanged.
2. **Route.** On F only a member whose donor is on the route (31211-31213) or the end field; real 61/62/63 on F is
   V11 (game). Unchanged. (Real 63 after the battle is caught earlier, by the executor's landing judge, as V16.)
3. **Visit.** The order 61 -> 62 -> 63; a new visit runs the live forbidden scan. Unchanged.
4. **Naming**: V10 (none registered). Unchanged.
5. **A tutorial or a battle** that rule 1b did not answer (a tutorial outside a battle; a battle already answered and
   still up): V10. Unchanged -- and with no registry it is O2's rule exactly, so O2 sees no difference.
6. **A choice**: O1's readiness hold, then the rules (2.5); no rule -> V1. Unchanged.
7. **A page** (dialog open, text, control off).
   - **(new, opt-in: `stop_pages`)** a page matching a stop page: VOID **V5**, NOTHING pressed. `by` is `driver` when
     the run is in its first visit and that visit is the start place (the error window there is the START's: the
     warp's incoming Byte[13]/[14]), else `game` (62's or 63's error path is reachable only if the run's own fields
     wrote 2 or 9 to Byte[13]/[14], which no route store does: a fork deviation, which VOID-ASYM then reads).
   - Otherwise O1's page rule (record, `press("confirm", 3)`, a `press` row, wait 4 ticks). Unchanged. 61's stage
     lines and 62's play lines are `[TIME=-1]` windows closed by CloseWindow: a Confirm does nothing to them, and
     `timed` records them so the transcript folds them.
8. **Control held**, settled O1's way (`settle_s` 1.0 of consecutive control polls): V4 (the table has no cell).
   Unchanged: a single control sample at a field load is not control, and a window up WITH control is an overlay,
   logged and never paged (O1's rule) -- in O3 the control itself is the VOID.
9. Otherwise wait.

`out()` gains `"battles": [battle rows]` only when the registry is non-empty, and `progress` carries the same list, so
a run that raises inside a battle still records it.

### 2.3 The battle executor (`_Drive.battle(st)`)
1. **Match.** `epoch = st.battle_epoch`, `scene = st.battle["scene"]`, `vplace = place(self.cur, members)` (the visit the
   battle began in -- never the per-poll place, which the over frame can flip). The row is
   `battle_row(pred, vplace, self.sc, scene)` (pure): `scene` equal, `donor == vplace`, `sc` null or equal, and not yet
   answered in this run. No row: **V10 (game)** "an unregistered battle: scene {scene} (epoch {epoch}) in {fid} (place
   {vplace}) at SC {sc}" -- another scene, another place or SC, or the same row asked twice. `self.battle_seen = epoch`.
2. **Fight.** `bound = min(row["timeout_s"], deadline - now)`;
   `result = g.fight(timeout=bound, max_turns=row["max_turns"], finish=False)` (the default policy: Attack the first
   standing foe each turn; tutorials are dismissed inside, H7 counts them).
   - `FightTimeout` (H7) with `bound` the row's own: **V15 (driver)** "battle {scene} reached no result within {bound} s /
     {max_turns} turns" -- King Leo's scripted end fires once (TH_E002 e1 t1 [601] latches `Map.Byte[24]`); a miss
     must cost `timeout_s`, not the run. With `bound` cut by the run's deadline: `HarnessError("the run's budget ran
     out in battle {scene}")`, which the session records as V13 like any budget.
   - Any other HarnessError propagates (V13, STOPPED), as `fight()`'s instrument failures always have.
3. **Leave.** `g.leave_battle(stop_on_field=True)` (H8): it presses Confirm only while the battle scene is up and stops
   at the first sample with the scene gone (whatever the UI state still says) or FieldHUD. Each of its presses is logged
   as a `press` row (`why: "leave_battle"`, `pre` the sample it was pressed on, `post` None, `near` []).
4. **Land.** `g.wait_for(lambda s: not s.in_battle and s.ui_state == "FieldHUD" and s.field_id > 0,
   timeout=row["land_s"])`; no field: **V14 (game)** "battle {scene} ended and no field came up within {land_s} s".
5. **The flip, recorded.** From `g.states_since(frame0)`, the first sample with `in_battle` and a field id other than
   the battle's: its frame is the row's `flip_frame` (the evidence for 0.2 #8; None if no sample caught it).
6. **The row.** `{"k": "battle", "field", "donor": vplace, "visit", "sc", "scene", "epoch", "row" (its index), "frame0",
   "t0", "result", "turns", "seconds", "tutorials", "timed_out", "leave": {"presses", "uis", "stopped"}, "flip_frame",
   "landed", "landed_place", "land_frame", "t1", "v", "by", "why"}` -- logged and appended to `out["battles"]`;
   `beats[row["beat"]] = result`; `self.since = now` (the watchdog); `self.walked = None`.
7. **The landing judge.** `want = row["lands"]`.
   - S: the landed id must be `want` (63).
   - F: the landed id must be a member whose donor is `want` (31213). The landed id equal to `want` itself -- REAL 63 --
     is **V16 (game)** "battle {scene} landed in real {want}, not member({want}) {member}: the s24 redirect did not
     fire". It is a FINDING: `rerun.stop_on: ["V16"]` holds the side's re-runs (S2), and O3-VOID-ASYM (a) reads it.
   - Anything else (62/31212: the battle returned to 62; any other field): **V11 (game)** "battle {scene} landed in
     {fid} (place {p}), not {want}".
8. Return; the loop's next poll starts the new visit (63) by rule 3.

### 2.4 Every research beat, and what handles it
The beats are `o3_research.json`'s `reconciled.route.beats`, with the critic's corrections.

| Beats | Field | Handled by |
|---|---|---|
| 1 | 61 | Nothing: Main_Init's ambient stores (4.4). No control (V4 if any, after the settle). |
| 2 | 61 | Rule 9, waiting: FMV003 (type 0) plays with no dialog and no control; nothing is pressed, so no skip dialog can open. Its whole length plus about 5 s sits inside the watchdog (`no_progress_s`, 4.12). |
| 3 | 61 | The page rule: 72-78, each a Confirm page (WindowAsync + WaitWindow), AFTER the movie's end. |
| 4 | 61 | The page rule on 79-86 (`[TIME=-1]`, closed by CloseWindow; a Confirm is inert; recorded `timed`). |
| 5 | 61 | Nothing: the exit (`Int16[2]:=100` ip363, `Field(62)`), then rule 3 (visit 62). |
| 6 | 62 | Nothing: Main_Init's ambient stores; the play's lines 87-95 by the page rule (inert, timed). |
| 7 | 62 | Nothing: the party rebuild and its stores (4.4). |
| 8 | 62 | Rule 1b: the registry row (62, 1155, 338) -> `fight()`, `leave_battle(stop_on_field)`, the landing. |
| 9 | 62 -> 63 | The executor's landing judge (2.3 step 7); then rule 3 (visit 63). |
| 10 | 63 | Nothing: Main_Init's ambient stores, loaded FRESH (O3-LANDING (c) proves it on the trace). |
| 11 | 63 | The page rule: 98, 100, 101 (Confirm pages); 96, 97, 99, 103 x3, 104 (timed; a Confirm may close one early: no store depends on it). |
| 12 | 63 | Nothing: the exit (`Int16[2]:=100` ip820, `Field(64)`). |
| 13 | 64 | Rule 1: the end. |
| 14-16 | 64, 150 | Beyond the end (O4). |

### 2.5 Choice rules
O3 has no choice. The only one possible is the skip-movie dialog, opened only by a Confirm during FMV003 (FieldHUD.cs
275-286, cursor `ETb.sChoose = 1`, No); the driver presses only on pages and none is up during the movie.
```json
[{"donor": null, "sc": null, "match": "want to skip", "pick": "default", "once": false, "beat": null}]
```
O1's rule, kept as a net. Its publication is unmeasured: if R-SKIP (7.1, optional) shows the prompt line publishing
empty, the freeze adds a second rule matching the dialog's option line as R-SKIP measured it (F4). Any other choice
is V1.

### 2.6 VOID conditions (each a RouteVoid with its class, cell and attribution; the run is not covered)
O2's classes keep their meaning; O3 can raise these:

| | Condition in O3 | by |
|---|---|---|
| V1 | A choice no rule matches (anything but the skip dialog). | game |
| V4 | Control held anywhere, after the settle (the table is empty). | game |
| V5 | A stop page: the "Error Env Play()" window. Nothing is pressed. | driver in the start visit (the warp's state); game after |
| V10 | A naming screen; a tutorial outside a battle; a battle the registry does not answer (another scene, place or SC; a second battle). | game |
| V11 | The run left the route or its visit order (rule 2/3); the battle landed somewhere other than `lands` (not the s24 case). | game (O3 has no walks) |
| V13 | The run budget (inside a battle too), or an unexpected exception: `STOPPED`. | driver |
| V14 | The watchdog; or a battle that ended with no field up within `land_s`. | game |
| **V15** (new) | The registered battle reached no result within its `timeout_s` / `max_turns` (`FightTimeout`). | **driver**: the driver's policy and bound own the fight; a one-off miss re-runs, and a structural one (every run of a side) fails VOID-ASYM (b) |
| **V16** (new) | On F, the registered battle landed in REAL `lands` (63), not its member: the s24 redirect did not fire. A FINDING (`rerun.stop_on`). | **game** |

V2, V3, V6, V7, V8, V9 and V12 cannot arise (no `once` rule, no default-take rule, no watched cell, no step, no
wait, no climb, and the only forbidden pattern is never backed: 4.8). The analysis repeats the trace-visible ones
(5.1), so a driver fault never turns into STOCK ONLY or FORK ONLY.

---

## 3. Harness additions (each minimal, opt-in, modelled in the FakeGame, tested)

Every default keeps today's behaviour; no existing caller changes.

**H7. `Session.fight`: a typed no-result, and what the fight did.**
- A new `FightTimeout(HarnessError)` (beside `HarnessError` and `StepRefused` in `harness/channel.py:86-90`, exported
  where they are), raised on both no-result exits instead of the plain HarnessError: the turns bound
  (session.py:7407-7411) and the timeout (:7442-7444), with the same messages. Every existing `except HarnessError`
  still catches it.
- `self.last_fight` is set on BOTH exits and gains `"seconds"` (wall time from the call), `"tutorials"` (screens
  `_dismiss_tutorial` closed inside the call) and `"timed_out"` (bool). Its existing keys are unchanged.
- Tests: `test_fight_raises_fight_timeout_without_a_result` -- a fake battle no attack can end (one enemy with a huge
  `hp`, no scripted end): `timeout=2` raises `FightTimeout` naming the timeout, `max_turns=1` raises it naming the
  turns, and `last_fight["timed_out"]` is True in both; `test_fight_counts_its_tutorials_and_seconds` -- scene 336 in
  `tutorial_scenes`: `last_fight["tutorials"] == 1`, `"seconds" > 0`.

**H8. `Session.leave_battle(*, timeout=90.0, stop_on_field=False)`: stop where the field begins, and say what it
pressed.**
- Always: `self.last_leave = {"presses": [{"frame", "ui", "in_battle", "field", "result"} for each press],
  "ended": ui_state, "field": field_id, "frame": frame, "stopped": "scene-gone" | "field" | "presses"}`. The return value
  (the UI state) is unchanged.
- With `stop_on_field=True`: before each press, if the sample shows the battle scene gone (`not in_battle`, whatever
  `ui_state` still reads -- it can lag as BattleResult while the field loads) or `ui_state == "FieldHUD"`, stop: never a
  Confirm into a loading field or onto its first windows (63's 96/97/98). The default (`False`) is O1's loop exactly,
  presses recorded.
- Tests: `test_leave_battle_stops_where_the_field_begins_and_logs_its_presses` -- H9's `battle_exit` with a lagging
  BattleResult UI during its close: with `stop_on_field=True` every recorded press has `in_battle` True and none is
  executed after the scene is gone; `stopped == "scene-gone"`; the control (`stop_on_field=False`) presses during the
  lag. `test_leave_battle_records_presses_on_o1s_path` -- a same-field battle (O1's shape): the loop and its return as
  today, the presses recorded.

**H9. FakeGame (opt-in knobs; each absent by default).**
- `battle_script_end = {"unit": <name>, "hp_raw_le": n, "result": r, "after_frames": k}` -- King Leo's latch: once
  that unit's `hp_raw` is <= n (after a command resolves), the battle ends with `result` `k` frames later, whoever is
  standing. Without it, today's `_settle_battle` (all foes down) is the only end.
- `battle_exit = {"field": id, "over_frames": a, "close_frames": b, "arrive_control": False}` -- the over frame and
  the scene change: at the end the published field id becomes `field` at once while `battle_active` stays True for
  `a` frames (result 2 folds to 1 at their end, as UpdateOverFrame does); then `b` frames with `battle_active` False and
  `ui_state` "BattleResult" (the lag); then FieldHUD in `field`, control as `arrive_control` says, `_visit` bumped (a
  fresh load). Without it, `end_battle` is today's (same field, FieldHUD at once).
- `warp_field_only = False` -- True: `warp` refuses unless `ui_state == "FieldHUD"` ("warp refused (not on a field?)"),
  as the agent does (0.2 #9).
- `soft_reset_in_battle = False` -- True: the soft-reset combo reaches the title from BattleHUD too (which the game
  does is R-BATTLE-VOID's to measure; the default keeps today's model, swallowed).
- A movie scene beat `{"movie": frames, "skip": {"header", "options", "default"}}` -- no dialog and no control for
  `frames` frames; a Confirm during it opens the skip choice (cursor on `default`); answering the default resumes the
  movie for what remains, the other option ends it.
- Tests: `test_fake_battle_script_end_ends_on_the_units_hp`, `test_fake_battle_exit_flips_the_field_inside_the_battle`
  (during `over_frames` a published sample has `in_battle` and the exit field together; the result reads 2 then 1),
  `test_fake_warp_refuses_off_the_field_when_told`, `test_fake_soft_reset_from_a_battle_when_told`,
  `test_fake_movie_beat_holds_and_offers_the_skip_dialog`.

**Not needed:** a movie state in the published state (impossible without an agent patch: 0.2 #11); a battle-scene
verb (the agent publishes `battle.scene`); a new choice or naming verb; NPC or region modelling (61-63 have none).

---

## 4. Predictions (draft v1: `O3Segment.draft()`)

### 4.1 Top level
```json
{"version": 1,
 "what": "O3: 61@1155 (warp, entrance 0) -> 62 -> battle 338 -> 63 -> Field(64), stock vs O1's tshp chain (members 31211-31213; PLAN.md, O3)",
 "rehearsals": [],
 "order": ["S","F","S","F","S","F"], "min_covered": 2, "rerun": {"max": 2, "stop_on": ["V16"]},
 "budget": {"run_s": 1200, "run_min_s": 600, "session_s": 7200, "settle_s": 1.0, "no_progress_s": 300},
 "start": {"S": 61, "F": 31211}, "entrance": 0, "scenario": 1155, "lang": "us",
 "end_field": 64, "end_fields": [64], "route": [61, 62, 63], "visits": [61, 62, 63],
 "stock_fields": [61, 62, 63, 64],
 "members": {"31200": 50, "...": "...", "31219": 3010}, "names": {"31200": "O1_TH_CGR", "...": "..."},
 "text_block": 2, "recovery": 4600,
 "seam": {"donor": 63, "to": 64, "why": "member(63) = 31213's Field(64) (63 e4 t1 ip828) stays real: the end, on both sides"},
 "cut_start": true,
 "start_first": "4.6", "start_music": "4.6", "start_residue": [[0, 0, 131], [1, 0, 4]], "residue_after_start": [],
 "sc_bytes": [0, 1],
 "chain": "4.3", "entrance_bytes": [2, 3],
 "writes": "4.4", "error_path": "4.5", "forbidden_sites": "4.5", "start_dependent": [],
 "noise": "4.7", "forbidden": "4.8", "landing": "4.7",
 "end_state": "4.9",
 "battles": "4.10", "stop_pages": ["2.1"],
 "regions": {}, "hotspots": {}, "table": [],
 "choices": ["2.5"], "naming": [],
 "beats": ["leo"],
 "settings": "4.13"}
```
- `members` and `names` are O1's twenty (31200-31219, `o1_forks.json`): the deployed chain is one unit (one deploy, one
  revert record; text blocks 2 and 187), and P-DEPLOY, P-EB, P-FLOOR and the fingerprint read all of it. The route runs
  three of them.
- `start_residue` is `[byte, old, new]`: SC 1155 = 0x0483 writes byte 0 (0 -> 131) and byte 1 (0 -> 4); entrance 0
  leaves byte 2 at 0, so no row. `residue_after_start` is empty until R-FULL shows otherwise, with a byte-level reason.
- No `ladder`: O3 writes no SC (4.2). `start_dependent` is empty: under the raw warp no key on the route is start
  dependent (5.4's scope line).

### 4.2 No SC write (O3-NO-SC)
61, 62 and 63 neither write nor read `Global.UInt16[0]` (0 stores, 0 reads in each listing); the next SC store is O4's
(150 e3 t1 ip1966, 1190). So after the start the trace carries NO row over bytes 0-1: SC reads 1155 throughout. O2's
LADDER on an empty ladder would be a check that cannot fail; O3-NO-SC selects rows by BYTE SPAN (`span_rows`, any
width, target, mode or source; `c` rows too) and requires none.

### 4.3 The FieldEntrance chain (`Global.Int16[2]`; O3-CHAIN, in order; the first `old` is 0, the warp's entrance)
| # | donor | sid | tag | ip | off | value | what |
|---|---|---|---|---|---|---|---|
| 1 | 61 | 1 | 1 | 363 | 352 | 100 | 61's exit (the conductor's stage 7), then `Field(62)` ip371 |
| 2 | 62 | 4 | 1 | 1285 | 1274 | 0 | stage 10, before `Battle(0,338)` ip1293 |
| 3 | 63 | 4 | 1 | 820 | 809 | 100 | 63's exit (stage 110), then `Field(64)` ip828 |

Every op is `:=`. **62 e4 t1 ip1345 (`Int16[2]:=0`, off 1334) must not appear**: it runs only if the battle returned
to 62; it is registered in `forbidden_sites` (4.5) so O3-KEYS proves the site, and because CHAIN is exact over bytes
2-3, its row (a same-value store, still emitted once) would be a fourth row and fail CHAIN. The prologues'
`Int16[2]:=10000` (61 ip41, 62 ip45, 63 ip41) sit behind `Bit[184]==1`, false on the route.

### 4.4 Registered writes (O3-WRITES: every covered run's keys are EXACTLY these and the chain, the noise aside)
Every op is `:=` but the four `++` (O2's key form: `op` mandatory, a compound value computed from its `prior`).

| donor | sid | tag | ip | off | target | value | what |
|---|---|---|---|---|---|---|---|
| 61 | 0 | 0 | 57 | 51 | Int16[9] | -1 | ambient (65535 as Int16) |
| 61 | 0 | 0 | 119 | 113 | Byte[13] | 0 | ambient: the route's branch (also `start_music`, 4.6) |
| 61 | 0 | 0 | 138 | 132 | Int16[11] | -1 | ambient |
| 61 | 0 | 0 | 200 | 194 | Byte[14] | 0 | ambient |
| 61 | 2 | 1 | 752 | 637 | Byte[8] | 125 | after FMV003 and pages 72-78 |
| 62 | 0 | 0 | 61 | 51 | Int16[9] | -1 | ambient |
| 62 | 0 | 0 | 123 | 113 | Byte[13] | 0 | ambient |
| 62 | 0 | 0 | 142 | 132 | Int16[11] | -1 | ambient |
| 62 | 0 | 0 | 204 | 194 | Byte[14] | 0 | ambient |
| 62 | 4 | 1 | 319 | 308 | UInt16[21] | 3585 | the play's party (0xE01: Zidane, Cinna, Marcus, Blank) |
| 62 | 4 | 1 | 603 | 592 | Byte[303] | 0 | |
| 62 | 4 | 1 | 637 | 626 | Byte[303] | 1 | `++`, prior 62/4/1/603 |
| 62 | 4 | 1 | 659 | 648 | Byte[303] | 2 | `++`, prior 62/4/1/637 |
| 62 | 4 | 1 | 681 | 670 | Byte[303] | 3 | `++`, prior 62/4/1/659 |
| 62 | 4 | 1 | 703 | 692 | Byte[303] | 4 | `++`, prior 62/4/1/681 |
| 62 | 4 | 1 | 1034 | 1023 | Byte[4] | 0 | PARTYCHK(5) false (ip1023 `:=1` not taken) |
| 62 | 4 | 1 | 1085 | 1074 | Byte[4] | 0 | |
| 62 | 4 | 1 | 1093 | 1082 | Byte[17] | 0 | |
| 62 | 4 | 1 | 1101 | 1090 | Byte[18] | 1 | |
| 63 | 0 | 0 | 57 | 51 | Int16[9] | -1 | ambient |
| 63 | 0 | 0 | 119 | 113 | Byte[13] | 0 | ambient |
| 63 | 0 | 0 | 138 | 132 | Int16[11] | -1 | ambient |
| 63 | 0 | 0 | 200 | 194 | Byte[14] | 0 | ambient |
| 63 | 14 | 1 | 805 | 330 | Byte[8] | 125 | stage 5, after 99 (a same-value store: emitted once) |

Every target is `Global.<width>[<index>]`; none is masked (0.2 #3). With the chain these are the route's 27 keyed
field stores; with the six masked prologue rows (`Bit[191]:=0` at ip22/26/22, `Bit[184]:=0` at ip49/53/49) the
research's 33 field rows. Why EXACT and not "at least" (O2's): O3's key set is small and fully enumerated by the bytes
(every gEventGlobal store of 61-63 is classified in 4.3-4.5), so any extra key -- even on both sides, where NULL
cannot see it (a dead branch firing, an error path, a C# write) -- is a claim failure, not noise. R-FULL must show the
exact set before the freeze (F6).

### 4.5 The error path and the forbidden site (registered so O3-KEYS proves each; never expected)
`error_path` -- each Main_Init's ambient music branch for an incoming Byte[13]/Byte[14] of 2 or 9 (`:=9`, the debug
window 3 "Error Env Play()", then `:=0`). All are `:=`:

| donor | sid | tag | ip / off | target := value |
|---|---|---|---|---|
| 61 | 0 | 0 | 97/91, 178/172, 349/343, 383/377 | Byte[13]:=9, Byte[14]:=9, Byte[13]:=0, Byte[14]:=0 |
| 62 | 0 | 0 | 101/91, 182/172, 346/336, 380/370 | the same four |
| 62 | 0 | 10 | 580/52, 614/86 | Byte[13]:=0, Byte[14]:=0 (Main_Reinit: never runs, 62 is not resumed) |
| 63 | 0 | 0 | 97/91, 178/172, 362/356, 396/390 | the same four |

`forbidden_sites`: `{62, 4, 1, 1345, 1334, Int16[2], 0}` (4.3).
A 61 error-path row is the START's fault: `why_void` uncovers the run (A-START, 5.1) and the live stop page VOIDs it
(V5, driver). A 62/63 one is a fork deviation: the live stop page VOIDs the run (V5, game -> VOID-ASYM), and in a
covered run its keys are extra keys (O3-WRITES).

### 4.6 The start (O3-START)
```json
"start_first": {"donor": 61, "m": 1, "src": "eb", "sid": 0, "tag": 0, "ip": 22, "off": 16, "target": "Global.Bit[191]",
                "value": 0, "op": ":=", "what": "61's Main_Init: its first store"},
"start_music": {"donor": 61, "m": 1, "src": "eb", "sid": 0, "tag": 0, "ip": 119, "off": 113, "target": "Global.Byte[13]",
                "value": 0, "op": ":=", "old": 1,
                "what": "61's ambient branch from the warp's Byte[13] 1 (field 70's prologue :=1 at ip130; the warp leaves FMV001 before its tail's :=2)"}
```
`old: 1` is MEASURED: all six O2 runs show old 1 at their first Byte[13] row after the warp. A true O2 end hands 61
a 3 (O2's traces: 61 ip119 old 3 -> 0); both take ip119. A 2 would take ip97 and the error window: the start state
is the instrument's (F7 confirms `old` from R-FULL).

### 4.7 Noise, and the battle's own rows
```json
"noise": [{"not_m": 1, "target": "Global.Byte[206]",
           "why": "battle 338's AI (BSC_TH_E002 e1 t1 ip267): Byte[206] := SYSVAR[0] each frame until ATB starts (random value and count)"}],
"landing": {"route_places": [61, 62, 63], "last_place": 63, "end": 64,
            "battle": {"place": 62, "m": 2, "sid": 1, "tag": 1, "ip": 267, "target": "Global.Byte[206]"},
            "fresh": {"place": 63, "sid": 0, "tag": 0, "ip": 22, "target": "Global.Bit[191]", "value": 0}}
```
- The noise is O1's legacy shape (`is_noise`: every key of that target whose mode is NOT field mode), and ONLY
  Byte[206]: O1's second row (Byte[199], TH_E001's) does not come along. TH_E002 stores no Byte[199] (0.2 #1).
- The legacy shape is keyed by target and mode, so alone it would also hide ANOTHER battle's Byte[206]. Two things
  pin it to 338: the registry asserts scene 338 live (V10 otherwise), and O3-LANDING (b) requires every battle-mode
  row to be exactly `landing.battle`'s store (m 2, e1 t1 ip267, Byte[206]) in member(62)/62. So a Byte[199] row, a
  Byte[206] from another site or scene, or a battle row in real 62 on F is a FAILURE, even when symmetric.
- What is deliberately NOT noise: nothing else on the route is random or timing-bound (research nondeterminism 1-6).
  FMV, page and battle timing change no store.

### 4.8 Forbidden (O2's patterns and backing rule; O3 registers one)
```json
[{"off_route": true, "cause": "walk",
  "why": "a write off the route: S, a place outside route + end_fields; F, a field that is neither a member whose donor is on the route nor an end field (real 61/62/63 on F: the s24 leak)"}]
```
`walk` backing needs a `step` row with a V11 landing; O3 has no steps, so a hit is never backed: it is a FINDING
(O3-FORBIDDEN, judged over EVERY run, VOID ones included). On F, the rows of real 63 that a leaked run writes before
its V16 VOID are exactly such hits -- so the leak fails FORBIDDEN as well as VOID-ASYM, with the rows named.

### 4.9 End state (read live on arrival in 64; O3-STATE (b))
```json
{"Global.UInt16[0]": 1155, "Global.Int16[2]": 100, "Global.UInt16[21]": 3585, "Global.Byte[303]": 4,
 "Global.Byte[4]": 0, "Global.Byte[17]": 0, "Global.Byte[18]": 1, "Global.Byte[8]": 125,
 "Global.Byte[13]": 0, "Global.Byte[14]": 0, "Global.Int16[9]": -1, "Global.Int16[11]": -1,
 "Global.Bit[191]": 0, "Global.Bit[184]": 0,
 "Global.Byte[6]": 0, "Global.UInt16[19]": 0, "Global.Byte[472]": 0, "Global.Int16[469]": 0,
 "Global.Bit[3717]": 0, "Global.Bit[3718]": 0}
```
The first fourteen are what the route leaves; the last six are untouched by it and hold New Game's 0 after the raw
warp (after a real O2 they would hold 3, 1799, 4, 1042, 1, 1 -- the scope line, 5.4). Byte[206] is excluded (random).
64's Main_Init rewrites only equal values before the read can land (Bit[3815]:=0, Byte[475]:=0, Byte[8]:=125, the
ambient keys): the read is stable through it.

### 4.10 The battle registry
One row, 2.1's. Its numbers are drafts: `timeout_s` 180, `max_turns` 40, `land_s` 30 (F9 re-sizes them).

### 4.11 Coverage beats
`leo`: the registered battle's result, done when in `won` [1, 2] (S1). Plus `end == "reached"`. The landing is not a
beat: a wrong landing is a VOID with its class (V11, V16), read per side by VOID-ASYM, never a quietly uncovered run.

### 4.12 Budget and recovery
The estimate is about 6 minutes a run (FMV003's 84.8 s file plus the fade, 10 Confirm pages, about 17 timed or
scripted lines, a battle of >= 186 damage, 63's scene). Drafts: `run_s` 1200, `run_min_s` 600, `session_s` 7200
(6 runs + 2 re-runs with slack), `settle_s` 1.0, **`no_progress_s` 300** (3 x the ~90-100 s arrival-to-page-72
stretch, which the signature cannot see move). F9 replaces all of them from the rehearsals. Recovery is `end_run`:
warp to 4600 first (from 64, a FieldHUD field), the soft reset directly from inside a battle (S3). F8 proves the
first from 64, F3 the second from inside battle 338.

### 4.13 Settings (P-SETTINGS; the fingerprint; the report's scope)
```json
{"Battle": {"Enabled": "1", "SFXRework": "1", "Speed": "5", "CustomBattleFlagsMeaning": "0"},
 "Cheats": {"Enabled": "1", "AutoBattle": "1", "SpeedMode": "1", "SpeedFactor": "3", "SpeedTimer": "0",
            "BattleAssistance": "1", "Attack9999": "1", "NoRandomEncounter": "1", "MasterSkill": "0", "LvMax": "0",
            "GilMax": "0"},
 "Hacks": {"Enabled": "1", "AllCharactersAvailable": "1", "SwordplayAssistance": "1", "DisableNameChoice": "0"},
 "Control": {"SoftReset": "1", "TurboDialog": "1", "BattleAutoConfirm": "1", "DialogProgressButtons": "\"Confirm\""}}
```
Raw ini values as the engine takes them (the last assignment wins; read by `ini_settings`). Today's install, measured
(0.2 #13); F12 confirms the rehearsals ran under them.

---

## 5. Checks (O3's analysis)

### 5.1 Reading a run: the COVERED rule
O2's rule (skipped, install changed, the drive did not reach the end, a beat not done (S1), no or an incomplete trace,
A-NOSTART, a BACKED forbidden hit, A-MISMATCH), plus:
- **A-START** (driver): the run's rows hold a registered `error_path` site of the START place (61) -- the warp's
  incoming Byte[13]/[14] took the error path. "the start state took 61's error path: <row>".

A drive VOID carries its V-class (2.6). The report lists every uncovered run's reasons per side.

### 5.2 The cuts
O2's: `cut_at_start` from 61's first `w` row (the residue in field 70 goes to `pre`), `cut_at_end` at the first row in
place 64. On F, 64 is no member, so its place is 64 itself; the `off` row (collected in 64 before `end_run`) is kept
as an `e` row and gives the digest its one seam (31213 -> 64), as O1's and O2's.

### 5.3 The checks, in order, each with the mutant that makes it fail (section 8 registers every one)
**All-run checks** (every run with a readable trace, judged even when COVER is short):
- **O3-FORBIDDEN** (inherited): no unbacked forbidden hit. Mutant: lands-real-63 (F rows in real 63: off the chain).
- **O3-VOID-ASYM** (inherited): (a) a game-attributed class (with its cell) on one side only; (b) every run of one side
  VOID in one class while the other has >= `min_covered` covered. Mutants: v16-all-F (a and b), unregistered-battle-F
  (a), control-S (a), v15-all-F (b, a driver class), error-path-63-F (a).

**Then:**
- **O3-FROZEN**, **O3-COVER**: O2's. Mutant: predictions-changed; beat-missing.

**Core checks** (over the covered runs):
- **O3-START.** (a) `pre` is EXACTLY `start_residue` (kind `r`, `(byte, old, new)` as a multiset), nothing else before
  the start; (b) the first `w` row in place 61 is `start_first`, read RAW (Bit[191] is masked); (c) the first Byte[13]
  row in place 61 is `start_music`: e0 t0 ip119 `:= 0` with `old == start_music.old` (1). Its detail counts the
  residue rows from the predictions (O2's hard-codes 3). Mutants: start-residue-wrong (a), front-cut-write (a),
  start-first-missing (b), start-music-old-wrong (c).
- **O3-NO-SC.** No kept row over `sc_bytes` (0-1) after the start: `span_sequence(rows, rk, [0, 1], [], 1155)` must
  return nothing (a `w` row of any width or source fails by name, keyed or not; a `c` row over the span fails as a
  suppressed repeat). Mutants: sc-write-fork (a C# `cs` write of UInt16[0] in 62, F only), sc-write-both (the same on
  both sides: NULL passes it, NO-SC does not); unit no-sc-span (a Byte[1] row).
- **O3-CHAIN.** O2's `span_check` over `entrance_bytes` (2-3) with 4.3: exactly the three keys, in line order, each
  `old` the previous value, the first from 0. Mutants: chain-dropped-fork, battle-returned-to-62 (ip1345, a fourth
  row), chain-first-old-wrong.
- **O3-RESIDUE** (inherited): no unmasked residue after the start beyond `residue_after_start` (empty). Mutant:
  residue-after-start.
- **O3-WRITES (exact).** For every covered run: `{k for k in digest.keys if not is_noise(k, pred)}` ==
  `{wkey(k) for k in writes + chain}`. Its detail names the missing and the extra keys per run. Mutants:
  fork-drops-a-write (missing), writes-extra-symmetric (62 ip1023 `Byte[4]:=1` on both sides: extra; NULL passes it).
- **O3-NULL**, **O3-STABLE**: O1's, with O3's legacy noise set aside (the battle's Byte[206] keys, random values).
  Mutants: fork-drops-a-write (NULL), byte199-fork (NULL, STABLE), byte206-field-mode-fork (NULL: the legacy noise
  covers m != 1 only).
- **O3-SEAM** (inherited, `seam` {63 -> 64}): no seam key, no across-seam or seam-only key, every Seam member(63)
  [31213] -> 64. NULL cannot see a seam leak (`Comparison.stock_only` leaves out keys with a seam count). Mutants:
  lands-real-63-covered, battle-rows-real-62-fork.
- **O3-LANDING (new).** For every covered run (F with the members map; S with its own ids):
  - (a) every field-mode (`m` 1) `w`/`c` row ran in its place's own field: a row whose place is 61/62/63 carries fld
    member(place) on F (31211/31212/31213) and the place itself on S, and no field-mode row stands in any place but
    61, 62 or 63 between the start and the cut;
  - (b) every battle-mode row (`m` != 1, `w` and `c`) is `landing.battle`'s store: m 2, sid 1, tag 1, ip 267,
    Global.Byte[206], fld member(62) (31212) on F / 62 on S;
  - (c) the first field-mode `w` row after the LAST battle-mode `w` row is `landing.fresh` -- 63 e0 t0 ip22
    `Bit[191]:=0` at member(63)/63: 63 loaded FRESH from the battle's own `RunBattleCode(37,63)` -- and no field-mode
    `w` row of place 62 follows the FIRST battle-mode `w` row (62 was never resumed; its Main_Reinit and ip1298-ip1353
    never ran);
  - (d) the last field-mode `w` row before the end cut is in place 63 (`last_place`), and the run's `end` log row names
    field 64 itself (real, on both sides); the seam's record is O3-SEAM's.

  (c) and (d) read `w` rows only: the engine writes every `c` (count) row at the epoch's close, after the end, so a
  `c` row's position says nothing about when its stores ran; (a) and (b) read both.

  Mutants: lands-real-63-covered (a), battle-rows-real-62-fork (b), byte199-both (b: symmetric, which NULL and STABLE
  pass), other-battle-noise-both (b: TH_E001's e0 t1 ip93 site, which the legacy noise alone would hide),
  battle-returned-to-62 (c), fresh-missing (c: 63's Main_Init rows absent, its first row after the battle is e14 t1
  ip805), last-place-wrong (d).
- **O3-MASKED** (inherited): the story-noise regions per side. Mutant: masked-differs (every F run without its Bit[184]
  rows).
- **O3-STATE** (inherited): (a) each unmasked target's emitted write history, identical across every covered run of
  both sides, in order; suppressed stores as a set; the registered noise (Byte[206] at m 2) left out; (b) every
  covered run's live `end_state` equals 4.9. Mutants: end-state-differs (b), fork-drops-a-write (a).
- **O3-JOIN** (inherited): every field row joins a store in the bytes its field ran (battle rows are census gaps, never
  failures: `storytrace._locate`). Mutant: join-failure.
- **O3-THROW** (in `run`, inherited): nothing thrown through EventEngine, EBin, StoryTrace or HarnessAgent.

**VERDICT:** O1's `verdict()`: PROVEN, NOT PROVEN: <failed>, or VOID: <void>; a failed check outranks a void one, so
FORBIDDEN and VOID-ASYM make a short session NOT PROVEN (the s24 leak reads "NOT PROVEN: O3-FORBIDDEN,
O3-VOID-ASYM", never VOID).

### 5.4 Report-only (`report_extra`, after the shared body)
- **Scope**, three lines:
  - start dependence (gEventGlobal values only): "under the raw warp no key on the route is start-dependent: 61 reads
    Byte[13]/Byte[14]/Bit[184] before writing them and takes the same branch from the warp's (1, 0, 0) as from a true
    O2 end's (3, 0, 0); 62 writes UInt16[21] and Byte[303] before reading them; battle 338 reads Byte[16..18] (0, and
    17/18 written by 62 first); 63 reads nothing global. The party is rebuilt by 62 e4 t1 from [Zidane] (here) or
    [Vivi] (after O2) to the same four. Not covered: party data, items, gil, AP, cards, field 70's override state, and
    the six untouched targets' values after a real O2 (4.9)";
  - settings: the `settings` dict as recorded in the session's fingerprint;
  - language: "a US session (P-LANG): the members' jp/fr/gr/it/es .eb are US bytecode (accept_us_build), and block 2's
    uk copy is the US text (the KNOWN-KIT-DEFECT line below)".
- **The battle, per run:** scene, result (and whether the harness read 2 or 1), turns, seconds, tutorials, the leave
  presses (count, the UI states pressed in, how it stopped), the flip frame, the landing (id, place, frames from the
  end to FieldHUD), and V15/V16 when raised.
- **61's movie, per run:** the arrival frame (the visit row) and the first page press (frames, seconds).
- O2's sections, copied (not called -- O2's names O2's scope line and SC timeline): VOID reasons per side, the masked
  counts, the forbidden hits with their backing, the P-TEXT KNOWN-KIT-DEFECT lines, the folded transcripts.
- **Re-runs held:** `rerun_held` (S2), when present.

---

## 6. Offline check and preflight

### 6.1 `--offline-check` (the install and O1's build, read-only; reads `--predictions`, else the frozen file, else the DRAFT, and prints which)
- **O3-BUILD:** `Segment.build_check` with `accept_us_build`: today "140 files; other languages: 15 own-language, 105
  us-build" (= O1-BUILD).
- **O3-TEXT:** O2's `text_check` on block 2 against the O1 build: today "KNOWN-KIT-DEFECT 1, FAIL 0, 6 byte-equal of
  7 languages", and the CLI prints the defect's own line ("KNOWN-KIT-DEFECT uk: ships stock us (3a6f3246c2; stock uk
  7ac9f17435): ..."). A us mismatch would FAIL (the session language).
- **O3-KEYS:** O2's `keys_check` on the filtered copy (1.3): chain, writes, `forbidden_sites` + `error_path`,
  `start_first`; `start_music` is a writes site and is checked with them. Today (0.2 #3): "43 sites (43 keys), every op
  in its statement, 4 compound values computed from their priors, none masked".
- **O3-REGIONS:** O2's `regions_check` over route [61, 62, 63] with no region registered: "0 regions, 0 hot-spots, 0
  gateways all registered" -- it FAILS the day a gateway or a Confirm hot-spot appears in a route field.
- **O3-SCENE (new):** for every `battles` row, `scene_census(name)` over the install's own scene (`_scenedb.SCENES`
  -> `BSC_<name>`; `battle.extract.read_scene_assets(name)`; `scene_codec.parse_scene(raw16)`; `EbScript` +
  `storytrace.instruction_stores` over the scene's `.eb`):
  - WinPose off (flags & 0x10) -> 2 and 1 are in `won`; on -> 1 is;
  - entry 0 tag 0's `RunBattleCode(37, N)`: N == `lands`;
  - the scene's gEventGlobal stores, every entry and function: exactly `landing.battle`'s site (sid, tag, ip, target),
    and the noise pattern's target is that site's;
  - entry 1 tag 1 holds the end test `B_SYSLIST[1] B_MEMBER(36) const(c) B_LE_E` with c below type 0's MaxHP (the
    detail states the damage it needs).
  Today: "338 BSC_TH_E002: flags 0x1839 (WinPose off: won [1, 2]); RunBattleCode(37, 63) = lands 63; 1 gEventGlobal
  store, Global.Byte[206] at e1 t1 ip267; end at cur.hp <= 10000 of 10186 (>= 186 damage)".

### 6.2 `--preflight` (the live install, read-only; GREEN today, since nothing needs deploying)
- **P-MANIFEST:** `o3_forks.json` members == the predictions', `deployed: true`.
- **P-DEPLOY**, **P-EB**, **P-FLOOR:** the base's, over O1's twenty: today PASS (20 members; 20 x 7 files).
- **P-STOCK:** no mod folder overrides 61, 62, 63 or 64: today none.
- **P-TEXT:** O2's `text_rule` on every folder's block 2: today FF9CustomMap ships all 7, PASS with the uk
  KNOWN-KIT-DEFECT line, which the session report repeats.
- **P-RECOVERY:** 4600 registered: today in FF9CustomMap-world.
- **P-DONOR (new):** every route donor (61, 62, 63) appears in exactly ONE ForkDonorPatch row across every stacked
  folder (`rung3_trace._fork_donor_rows`), its member's: today 61 -> 31211, 62 -> 31212, 63 -> 31213; the duplicated
  donors are 312 and 350-359 only. A donor forked twice sets `ForkSiblingMap[donor] = -1` (DataPatchers.cs:156-160)
  and battle 338 would leak the fork run into real 63.
- **P-SETTINGS (new):** `ini_settings(Memoria.ini)` == `pred["settings"]` key for key; a FAIL names each difference.
- **In game only** (`capabilities`): P-CAP, P-OBJECTS, P-LANG (O2's), and **P-DONOR-LOG (new)**: this launch's
  Memoria.log (`g._log_paths()`, rewritten at launch) holds "[DataPatchers] Initialized" and NO line "[DataPatchers]
  ForkDonorPatch: donor field <61|62|63> is forked by both" -- the engine's donor map is fixed at launch
  (DataPatchers.cs:107-127, once per launch), so a duplicate present then and removed since would read clean in the
  files and still disable the redirect. Calibrated on today's log (0.2 #7).

### 6.3 The fingerprint (per run, before and after, as O1's)
The base's (members' registrations, ForkDonorPatch rows, `.eb` and walkmesh shas, stock overrides) + O2's
(`override70`, `text2`, `lang`) + **`settings`** (`ini_settings` over 4.13's keys). Another session re-wiring New Game,
touching block 2, a language change or a settings change mid-session makes runs VOID (A-INSTALL), never skews them.

### 6.4 `o3_forks.json` (the implementer writes it; nothing to flip: the chain is live)
```json
{"what": "O3's fork chain: O1's tshp chain as deployed (31200-31219, FF9CustomMap). O3 runs members 31211 (61), 31212 (62), 31213 (63); member(63)'s Field(64) is real 64, the seam and the segment's end on both sides. Nothing is imported, built or deployed for O3.",
 "reuses": "studies/story-trace/o1_forks.json",
 "import": "O1's (o1_forks.json import)", "build": "O1's: C:/gd/_ns_playtest/o1/build",
 "deploy": "O1's, 2026-09-29 21:07 local", "mod_folder": "FF9CustomMap",
 "members": "<O1's twenty>", "names": "<O1's twenty>",
 "route_members": {"31211": 61, "31212": 62, "31213": 63},
 "text_block": 2, "deployed": true, "relaunch_needed": false,
 "relaunch_why": "nothing is deployed for O3; the live launch already holds the chain's FieldScene ids and ForkDonorPatch rows (P-DEPLOY, P-DONOR, P-DONOR-LOG)",
 "known_defects": [
   "uk/field/2.mes is stock us (3a6f3246c2; stock uk 7ac9f17435): O1's build predates the per-language text pick (aa627d52). Block 2 is a global block: a UK game shows US text in stock 61-69 too. Not redeployed for O3 (the session runs US: P-LANG); O4's alxc members 64/68/69 also carry block 2, so their deploy rewrites it",
   "every member's jp/fr/gr/it/es .eb is US bytecode (the kit before 3d8b7f1b): O3-BUILD accepts the us build, and the claim is a US session's"],
 "revert": "O1's (o1_forks.json revert: 31219 down to 31200, newest first)",
 "verified": null}
```

---

## 7. Rehearsal plan (the lead runs these in game before freezing; nothing is deployed)

### 7.1 The stages (`o3_rehearse.py`: `run(g, field=None)`; `O3_STAGE=<name>` picks one by name, `--field N` the one non-by-name stage warping into N)
Each traced stage: New Game; `wait_frames(30)`; `storytrace(True)`; the raw warp; `segment_drive.drive(g,
stage_pred, "S", log, end_fields=[stage end], observe=recorder, forbid_live=True)`; the trace to
`rh_<stage>_<n>.jsonl`; the record into `o3_rehearsal.json`; `end_run`. Only R-FULL's traces may define or change the
writes, the chain, the noise, the start or the end state; the staged runs prove mechanics, compared within their stage.

| Stage | Warp | Ends in | Runs | What it settles |
|---|---|---|---|---|
| **R-START** (runs first: the go/no-go) | `warp 61 0 1155` | 62 | 2 | F1, F7: FMV003 plays after the warp has cut FMV001 (type 0 into type 0, never measured); no skip dialog; arrival -> page 72 (frames, seconds); the start rows (residue, 61 ip22, ip119 old 1). |
| **F-SMOKE** (by name; NO trace) | `warp 31211 0 1155`, `warp 31212 0 1155`, `warp 31213 0 1155`, and their stock twins `warp 61/62/63 0 1155` | -- | 6 warps, one each | F5: each member loads at entrance 0 SC 1155 (field id, FieldHUD) and its Main_Init runs -- its published object sids after `smoke_s` (8 s) equal its stock twin's (InitObject's entries: 61 {2, 7, 8, 14, 16}, 62 {12 x4, 20, 18, 19, 8, 9, 10}, 63 {11-13, 21, 19, 20, 6, 8, 9}, the player aside -- the twins give the measured sets); 0 exceptions through EventEngine/EBin/HarnessAgent; `end_run` (from mid-movie, mid-play, mid-scene). It never fights: the 338 landing is the session's claim. No trace, so no fork data exists before the freeze. |
| **R-62** | `warp 62 0 1155` | 64 | 2 | F2, F8: the battle beat (the registry match on the published scene, turns, seconds, the result read, tutorials 0, the leave presses, the flip, the landing in 63 and its latency), the cmd-37 landing on STOCK under the trace (63 e0 t0 ip22 the first field row after the battle), 63's pages, `end_run` from 64. |
| **R-FULL** | `warp 61 0 1155` | 64 | 2 | Everything in sequence; the only stage whose traces define predictions (F6, F7, F11); the total time (F9). |
| **R-SKIP** (optional, by name) | `warp 61 0 1155`; a wrapper round the recorder's `observe` hook presses Confirm once, 10 s after the run's first poll in 61, and records the frame | 62 | 1 | F4: the skip dialog's published choice (prompt, options, active, selected at readiness); the rule answers it; FMV003 continues. |
| **R-BATTLE-VOID** (LAST in a launch, or its own) | `warp 62 0 1155`, the battle row's `timeout_s` 15 | V15 | 1 | F3: `end_run` from inside battle 338 (S3's soft reset) reaches the title, with its seconds. A failure ends the launch (the next run would start from an unknown state). |

Default order without `O3_STAGE`/`--field`: R-START, F-SMOKE, R-62, R-FULL, R-BATTLE-VOID (R-SKIP only by name).
Estimates a run: R-START ~150 s, F-SMOKE ~150 s in all, R-62 ~240 s, R-FULL ~360 s, R-BATTLE-VOID ~90 s, R-SKIP
~150 s.

`o3_rehearse.py` reuses `o2_rehearse.Recorder` (a stage with `"movie": {"donor": 61}` records arrival, first page and
fps; `tracks` empty) and `stage_pred` (plus O3's `battle_override`); it has its own `STAGES`, `select` (keyed on
`O3_STAGE`), `one` (O3's `trace_summary`, the battle rows), `smoke` (no `storytrace` verb is ever sent; asserted in its
test) and `run`. The command: `py tools/play.py studies/story-trace/o3_rehearse.py --label o3-rh --timeout 240`.

### 7.2 What every stage records
O2's record (grants -- there must be none --, pages with `timed`, published choices, the `press` evidence, the longest
no-progress stretch and where, the end state, `end_run`'s result) plus:
- **the battle rows** of the driver log (2.3 step 6), whole;
- **the movie** (61): arrival frame, first page frame, fps before/during/after;
- **the trace**, through O3's `trace_summary`: the start rows (residue before, other rows before), the chain rows with
  their keys, the rows over SC's bytes (must be none), each registered key present or absent, every UNREGISTERED key
  (the battle noise aside), the battle-mode rows (count, sites, flds, the c row), the first field row after the battle,
  the error-path rows (must be none), the residue after the start, the masked counts, the join failures (0);
- **the settings** fingerprint and the P-DONOR-LOG reading of the launch;
- **F-SMOKE:** per warp, the field id and UI reached and when, the published object sids and `objects_status`, the
  exceptions and the new Memoria.log warnings/errors after the warp, `end_run`'s result.

`py studies/story-trace/o3_prima_vista.py --rehearsal-report <run dir>` prints all of it, stage by stage, run by run.

### 7.3 The freeze checklist (each item needs its evidence; the run dirs go into `rehearsals`)
- **F1.** In every R-START and R-FULL run FMV003 plays to its end after the warp and page 72 opens; no skip dialog
  opens. The arrival -> page 72 time is recorded. If FMV003 does not play or the run stalls, STOP: the start must be
  redesigned before anything else (10, risk 1).
- **F2.** In every R-62 and R-FULL run: the registry matched on the PUBLISHED `battle.scene` 338 (if the agent
  publishes another number, STOP and correct the row, re-checked by O3-SCENE); result in {1, 2} (which one is
  recorded); tutorials 0; the leave presses all inside the battle scene; the flip frame seen inside the battle (or
  not caught); the landing in 63 with 63 e0 t0 ip22 the first field row after the battle rows and no 62 row after the
  battle; the battle rows only e1 t1 ip267 Byte[206] at fld 62.
- **F3.** R-BATTLE-VOID: `end_run` from inside the battle reaches the title. If not, STOP: recovery from a battle is
  redesigned (e.g. let `end_run` fight the battle out first) before any session.
- **F4.** (if run) R-SKIP: the rule matches the published dialog with `selected` 1 (No) at readiness; if the prompt
  published empty, a second rule matching the measured option line is added.
- **F5.** F-SMOKE: every member loads, its object sids equal its twin's, 0 exceptions, `end_run` ok. If a member does
  not load, STOP: that is a chain defect, not a finding the session should discover.
- **F6.** The R-FULL traces define the predictions: per run, keys == the 27 drafted (24 writes + 3 chain) plus the
  Byte[206] noise; no row over SC's bytes; residue exactly the start's two rows and none after; no error-path row; the
  two runs key for key identical outside Byte[206]; any difference explained at the byte level before the freeze (a new
  key only with that explanation).
- **F7.** R-FULL/R-START: the rows before the start are exactly `[[0, 0, 131], [1, 0, 4]]`; the first `w` row is 61 e0
  t0 ip22; 61's first Byte[13] row is ip119 with old 1 (`start_music.old`).
- **F8.** `end_run` from 64 reaches the title (R-62, R-FULL).
- **F9.** Budgets: `run_s` = 2x the slowest R-FULL; `run_min_s` = 1.25x the median; `session_s` = 8x the median +
  1800; `no_progress_s` = max(120, 3x the longest no-progress stretch seen in any traced stage, FMV003 included);
  `timeout_s` = max(120, 3x the slowest battle's seconds); `max_turns` = max(30, 3x the most turns); `land_s` =
  max(10, 3x the slowest battle-end -> FieldHUD).
- **F10.** P-DONOR-LOG passes on the rehearsal launch's own log.
- **F11.** Every R-FULL `end_state` read equals 4.9's.
- **F12.** The rehearsal launch's fingerprinted `settings` equal 4.13's.

Then `--freeze` (v1), `--preflight` green (nothing to deploy, no relaunch), and the session:
`py tools/play.py studies/story-trace/o3_prima_vista.py --label story-o3 --timeout 240`.

---

## 8. The dry run (`o3_dryrun.py`: synthetic sessions through `O3.analyse`)

Built like `o2_dryrun.py`, with its own `render` (the start values are O3's: SC 1155, Int16[2] 0, Byte[13] 1; every
other target 0) and O2's event helpers (`w`, `r`, `e`, `drop`, `after`, `before`, `edit`, `upto`).
- **Real store sites** (every field row joins): 4.3-4.6's, the error-path and forbidden sites, 62 e4 t1 ip1023 (the dead
  `Byte[4]:=1`), 63 e14 t1 ip805, 64 e0 t0 ip22 (the end row).
- **The battle's rows**: m 2 at fld 62 (S) / 31212 (F), don 62, sid 1 tag 1 ip 267, Byte[206], 70 random values a run
  (seeded) -- so each run emits 64 and counts the rest into a `c` row, as the engine does.
- **A base run**: `arm` (fld 70); residue rows (fld 70) byte 0 0 -> 131, byte 1 0 -> 4; 61's rows (start_first, Bit[184],
  the ambient four, ip752, ip363); 62's (the ambient six, ip319, the Byte[303] five, ip1034, ip1085, ip1093, ip1101,
  ip1285); the battle rows; 63's (the ambient six, ip805, ip820); 64's ip22; `off` (fld 64). On F, fields are shifted
  onto members (61 -> 31211, 62 -> 31212, 63 -> 31213); 64 stays 64.
- **A log**: the visit rows, the battle row (`result` 2), `end_state` (4.9), the beats `{"leo": 2}`; a VOID drive's
  class and cell.

| Case | Want |
|---|---|
| null-pair | PROVEN |
| fork-drops-a-write (no 62 ip1101 on F) | NOT PROVEN (WRITES F, NULL F, STATE F) |
| sc-write-fork (a `cs` UInt16[0]:=1190 row in 62, F) | NOT PROVEN (NO-SC F, WRITES F, NULL F, STATE F) |
| sc-write-both (the same on both sides) | NOT PROVEN (NO-SC F, WRITES F; NULL P) |
| chain-dropped-fork (no 62 ip1285 on F) | NOT PROVEN (CHAIN F, WRITES F, NULL F, STATE F) |
| battle-returned-to-62 (both sides: 62 e4 t1 ip1345 after the battle rows) | NOT PROVEN (CHAIN F, LANDING F, WRITES F; NULL P) |
| chain-first-old-wrong (61 ip363's old 102) | NOT PROVEN (CHAIN F) |
| byte206-more-rows-fork (F 100 battle rows, S 70) | PROVEN |
| byte199-fork (one F run: an m 2 Byte[199] row) | NOT PROVEN (NULL F, STABLE F, LANDING F, STATE F) |
| byte199-both (every run: the same row, the same value) | NOT PROVEN (LANDING F; NULL P, STABLE P) |
| other-battle-noise-both (every run: an m 2 Byte[206] row at e0 t1 ip93, TH_E001's site) | NOT PROVEN (LANDING F; NULL P) |
| byte206-field-mode-fork (F: an m 1 addition-buffer Byte[206] row at 62 e4, `add` 1) | NOT PROVEN (NULL F, WRITES F, STATE F) |
| lands-real-63-covered (every F run: 63's rows at fld 63, the drive reached) | NOT PROVEN (LANDING F, SEAM F, FORBIDDEN F, WRITES F; NULL P: a seam leak is invisible to it, O2's seam-leak lesson) |
| v16-all-F (every F run VOID V16 game at [62, 1155]; its rows reach real 63's prologue) | NOT PROVEN (FORBIDDEN F, VOID-ASYM F; COVER V) |
| v16-one-F (one F run so) | NOT PROVEN (FORBIDDEN F, VOID-ASYM F; COVER P) |
| battle-rows-real-62-fork (every F run's battle rows at fld 62) | NOT PROVEN (LANDING F, SEAM F, FORBIDDEN F) |
| fresh-missing (both sides: 63's e0 t0 rows dropped) | NOT PROVEN (LANDING F, WRITES F) |
| last-place-wrong (both sides: 61 e0 t0 ip130 `Byte[13]:=1`, the dead branch, after 63's ip820) | NOT PROVEN (LANDING F, WRITES F) |
| v15-one-S (one S run VOID V15 driver, its rows up to the battle) | PROVEN (S 2 of 3; VOID-ASYM P) |
| v15-all-F (every F run VOID V15 driver) | NOT PROVEN (VOID-ASYM F (b); COVER V) |
| unregistered-battle-F (one F run VOID V10 game at [62, 1155]) | NOT PROVEN (VOID-ASYM F) |
| control-S (one S run VOID V4 game at [63, 1155]) | NOT PROVEN (VOID-ASYM F) |
| error-path-start-S (one S run: 61 ip97 in place of ip119, the run stopped at the window; VOID V5 driver [61, 1155]) | PROVEN (S 2 of 3); the run's classes include V5 and A-START |
| error-path-start-covered-S (61 ip97 and ip349 in place of ip119, then the whole route; the drive reached) | PROVEN (S 2 of 3); the run VOID by A-START |
| error-path-63-F (one F run: 63 ip97 in place of ip119, the run stopped at the window; VOID V5 game [63, 1155]) | NOT PROVEN (VOID-ASYM F) |
| start-residue-wrong (S: byte 0 0 -> 132) | NOT PROVEN (START F) |
| start-first-missing (both: 61 ip22 dropped) | NOT PROVEN (START F; NULL P: masked) |
| start-music-old-wrong (both: the incoming Byte[13] 3, so 61 ip119's old is 3) | NOT PROVEN (START F) |
| front-cut-write (F: a `w` row in fld 70 before the start) | NOT PROVEN (START F) |
| residue-after-start (F: an `r` row on byte 300 after the start) | NOT PROVEN (RESIDUE F) |
| writes-extra-symmetric (both: 62 ip1023 `Byte[4]:=1` before ip1034) | NOT PROVEN (WRITES F; NULL P) |
| end-cut (S: rows in 64 past the end) | PROVEN |
| end-state-differs (one covered F run: Byte[303] 3) | NOT PROVEN (STATE F) |
| battle-result-1 (every run `leo` 1) | PROVEN |
| battle-result-3-one-S (one S run `leo` 3) | PROVEN (S 2 of 3); that run A-BEATS |
| beat-missing (`leo` None in two S runs) | VOID (COVER V; VOID-ASYM P) |
| masked-differs (every F run without its Bit[184] rows) | NOT PROVEN (MASKED F) |
| mismatched (one F run's member rows name another donor) | PROVEN; that run A-MISMATCH |
| no-start-row (one S run never reaches 61) | PROVEN; that run A-NOSTART |
| join-failure (both: a row one byte off 62 ip1101) | NOT PROVEN (JOIN F) |
| trace-without-off | VOID |
| install-changed | VOID |
| predictions-changed | NOT PROVEN (FROZEN F) |

Units (no session):
- **no-sc-span:** a `Global.Byte[1]` row is selected by NO-SC's span and fails by name; a Byte[4] row is not selected.
- **trace-summary:** O3's `trace_summary` of a base S run: chain 3/3, writes 24/24, no SC row, the battle's rows (64
  emitted, the rest in one count row), the first field row after the battle 63 e0 t0 ip22, no unregistered key, no
  error-path row, no join failure, the two start residue rows.
- **state-history:** Byte[8]'s history is `[(61, 125), (63, 125)]`; the battle noise is in neither history nor
  suppressed set.
- **p-donor-log:** synthetic logs -- "Initialized" plus today's real 351 warning: PASS; plus "donor field 63 is forked by
  both 31213 and 31299": FAIL naming 63; no "Initialized": FAIL.
- **p-settings:** a synthetic ini equal to 4.13: PASS; `Speed = 0`: FAIL naming it; a later duplicate assignment wins.
- **scene-census:** O3-SCENE on the install: PASS; mutants each FAIL by their clause: `lands` 64, `won` [1],
  `landing.battle.ip` 268, the noise target `Global.Byte[199]`.
- **build-legacy:** `Segment.build_check` on a synthetic two-member build with an injected `stock_lang` (its
  `stock_lang=` seam) and `accept_us_build`: a member whose jp `.eb` is the us build reads PASS, counted "us-build"; one
  whose jp is neither its own donor language remapped nor the us build FAILs by name; the same build without
  `accept_us_build` FAILs the us-build copy -- O3-BUILD's legacy acceptance is the opt-in, never a blanket pass.
- **offline mutants** (O2's `OFFLINE_MUTANTS` pattern, each FAIL by its clause after all read PASS on the draft): KEYS --
  a write's value (UInt16[21] 3586), a `++` prior unknown, an error-path ip + 1, a chain `off` + 1, `start_first`'s
  target; REGIONS -- a frozen hot-spot 62 e9 that the bytes lack; P-DONOR -- synthetic folders with a second row
  `31299 63` (FAIL), and with none for 61 (FAIL).

It prints O2's summary columns (FROZEN COVER FORBIDDEN VOID-ASYM START NO-SC CHAIN RESIDUE WRITES NULL STABLE SEAM
LANDING MASKED STATE JOIN) and "N/N cases as registered", exiting 1 on any miss.

---

## 9. Build order (three parts; no deploy, no game, no `tools/play.py`, no full suite)

Run pytest from `ff9mapkit/`, the study scripts from the worktree root. The harness tests run in REAL TIME (the
FakeGame loops on a thread): run the named `-k` selections, never many at once, and the whole file only where a
PART says so. A SKIPPED test is not a pass: every required pytest run reports 0 failed, and its skips and xfails are
exactly the PART's baseline's (taken before the PART's first change); a skip for missing templates is fixed with `py
-m ff9mapkit extract-templates` (read-only on the install) and the run repeated. A failure that passes on an
immediate re-run of that test alone is a timing flake: named in the commit message, never ignored. Commit on the
branch when a step is green, one step per commit, each message ending with
"Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>". Write non-ASCII files with Python (utf-8) or the
Edit/Write tools; frozen JSON and baselines are LF (`-text`).

### PART A -- the regression gate extended to O2 (baseline FIRST), then the shared session changes
1. **A0: the O2 gate and its baseline, FIRST.** Extend `segment_regress.py` (1.4), run `py
   studies/story-trace/segment_regress.py --capture-o2`, and commit it with `research/o2_regress_baseline.json` and its
   `.gitattributes` line before any other code change. Then `py studies/story-trace/segment_regress.py` reads G1-G12.
2. **A1: S1** (`read_session`'s registered-battle won set) + `test_segment_read_session_judges_a_registered_battle_by_its_won`.
3. **A2: S2** (`rerun.stop_on`) + `test_segment_rerun_stops_on_a_finding_class` (`_stub_segment` gains `rerun=`).
4. **A3: S3** (`end_run` from inside a battle) + `test_segment_end_run_resets_from_inside_a_battle_without_a_warp`.
   Each A1-A3 test joins `REQUIRED_TESTS` as it lands.

**PART A REQUIRED-GREEN** (after A0, and again after each of A1-A3):

| Command | Expected |
|---|---|
| `py studies/story-trace/segment_regress.py` | exit 0; G1-G7 and G8-G12 each PASS |
| `py studies/story-trace/o1_dryrun.py` | exit 0; "16/16 cases as registered" |
| `py studies/story-trace/o2_dryrun.py --predictions studies/story-trace/o2_predictions_v1.json` | exit 0; "86/86 cases as registered" |
| `py studies/story-trace/o1_opening.py --analyse C:\gd\Dream-World-IX\.harness-runs\20260929-213149-story-o1e --predictions studies/story-trace/o1_predictions_v4.json` | exit 0; `VERDICT: PROVEN` |
| `py studies/story-trace/o2_alexandria.py --analyse C:\gd\Dream-World-IX\.harness-runs\20260930-192740-story-o2 --predictions studies/story-trace/o2_predictions_v1.json` | exit 0; `VERDICT: PROVEN`; the archived report |
| `py studies/story-trace/o1_opening.py --offline-check` | exit 0; O1-BUILD (140 files; 15 own-language, 105 us-build), O1-KEYS (4 keys) |
| `py studies/story-trace/o2_alexandria.py --offline-check` | exit 0; 5 PASS as 0.2 #12 |
| `py -m pytest tests/test_harness.py -q -p no:cacheprovider -W ignore -k "segment or pick_for or key_matches or is_noise or cut_at or row_keys"` | all passed, 0 failed, 0 skipped |

### PART B -- the harness additions and the battle beat in `segment_drive`
1. **B0:** the PART's baseline of the whole `tests/test_harness.py` (passed / xfailed / skipped), taken before B1 from
   this worktree with the field manifest present (O2's B0 note: a snapshot lacking `reference/field-manifest.tsv`
   fails 22 stock-warp tests).
2. **B1: H9** (the FakeGame knobs) + its five fake tests.
3. **B2: H7** (`FightTimeout`, `last_fight`) + its two tests.
4. **B3: H8** (`leave_battle(stop_on_field=)`, `last_leave`) + its two tests.
5. **B4: S4** -- `segment_drive`: `battle_of`/`battle_row` (pure), `_Drive.battle`, rule 1b, rule 7's stop pages, V15/V16,
   `out()`'s `battles` -- with these FakeGame tests (fields 30820/30821/30810 of the fixture as "61/62/63", an
   unregistered end id as "64"; F-side members appended to the fixture's DictionaryPatch as O1's pinning test does):
   - `test_o3_drive_fights_its_registered_battle_and_lands_fresh` (S): pages, the director starts battle 338 at "62"
     (`battle_script_end` on a 10186-hp "King Leo", `battle_exit` "63"), the drive fights, leaves, lands; beats
     `{"leo": 2 or 1}`; one `battle` row (scene, epoch, result, turns, presses, flip_frame, landed "63"); visits
     61, 62, 63; the end reached.
   - `test_o3_drive_lands_in_the_member_on_the_fork_side` (F, `battle_exit` member("63")).
   - `test_o3_drive_reads_a_landing_in_the_real_field_as_a_finding` (F, `battle_exit` real "63"): V16, by game, cell
     ["62", sc].
   - `test_o3_drive_ignores_the_id_flip_inside_the_battle` (`over_frames` long: a published sample with `in_battle` and
     "63" together; no V10, no visit, no V11 until the landing).
   - `test_o3_drive_voids_an_unregistered_battle` (scene 337 at "62"; scene 338 at "61"; the same row twice): V10, game.
   - `test_o3_drive_voids_a_battle_with_no_result` (no scripted end, a huge hp, `timeout_s` 3): V15, driver; the
     battle row has `timed_out`.
   - `test_o3_drive_logs_leave_battle_presses_as_press_rows`.
   - `test_o3_drive_stops_on_a_stop_page` (the error window in the start visit: V5 driver; in a later visit: V5 game;
     nothing pressed either way).
   - `test_o3_drive_answers_a_skip_dialog_at_its_default` (a movie beat, a Confirm injected by the director: the rule
     takes No; the movie resumes; the end reached).
   - `test_o3_drive_watchdog_against_a_long_movie` (a movie longer than `no_progress_s`: V14; with `no_progress_s`
     above it: reached -- the sizing rule of 4.12, on the fake).
   - `test_o3_drive_without_a_registry_keeps_o2s_battle_rule` (O2-shaped predictions, a battle: V10 with O2's message).
6. **B5:** `test_segment_end_run_from_a_battle_on_the_fake` (S3 on H9's knobs).

**PART B REQUIRED-GREEN.** H9, H7 and H8 change the fake and two shared verbs, so the WHOLE file runs after B3 and
once more at the end of PART B:

| When | Command | Expected |
|---|---|---|
| after B1, B2, B4, B5 | `py -m pytest tests/test_harness.py -q -p no:cacheprovider -W ignore -k "o1_ or o2_ or o3_ or segment or fight or leave_battle or fake_"` | all passed, 0 failed, 0 skipped |
| after B3 and after B5 | `py -m pytest tests/test_harness.py -q -p no:cacheprovider -W ignore` | B0's counts + the new tests passed, B0's xfails, 0 skipped, 0 failed |
| after every B step | `py studies/story-trace/segment_regress.py` | exit 0 |

### PART C -- O3 itself
1. **C1: `o3_prima_vista.py`** (1.3, 4-6), **`o3_forks.json`** (6.4), the `.gitattributes` line for
   `o3_predictions*.json`. Tests: `test_o3_draft_members_are_o1s_chain` (SKIPS, saying so, where O1's chain is not
   built), `test_o3_freeze_refuses_an_existing_file` (a synthetic chain: runs everywhere),
   `test_o3_p_donor_log_reads_the_launchs_warnings`, `test_o3_settings_read_the_ini_the_engines_way`.
2. **C2: `o3_dryrun.py`** -- every case and unit of section 8 as registered.
3. **C3: `o3_rehearse.py`** + `--rehearsal-report`. Tests: `test_o3_rehearse_plumbing_on_the_fake` (one traced stage
   with a battle on the fake: the record holds every 7.2 section) and `test_o3_rehearse_smoke_sends_no_storytrace_on_the_fake`
   (F-SMOKE: no `storytrace` step executed, the object sids recorded, `end_run` after each warp). Both join
   `REQUIRED_TESTS_O2` (G12's selection matches "rehearse").
4. **C4: the O3 section in `PLAN.md`** -- the question, the segment, the sides, the entry, the battle beat, the checks,
   "draft: rehearsals pending, freeze pending", the uk KNOWN-KIT-DEFECT and the legacy build as scoped facts.

**PART C REQUIRED-GREEN** (after each of C1-C4, as far as it exists):

| Command | Expected |
|---|---|
| `py studies/story-trace/o3_prima_vista.py --offline-check` | exit 0; "predictions: the draft"; 5 PASS -- O3-BUILD (140 files; 15 own-language, 105 us-build), O3-TEXT (KNOWN-KIT-DEFECT 1, FAIL 0, 6 byte-equal of 7, and the printed KNOWN-KIT-DEFECT uk line), O3-KEYS (43 sites, 4 compound values computed, none masked), O3-REGIONS (0 regions, 0 hot-spots, 0 gateways), O3-SCENE (338 as 6.1) |
| `py studies/story-trace/o3_prima_vista.py --preflight` | exit 0; P-MANIFEST, P-DEPLOY, P-EB, P-FLOOR, P-STOCK, P-TEXT (with the uk line), P-RECOVERY, P-DONOR, P-SETTINGS PASS |
| `py studies/story-trace/o3_prima_vista.py --draft` | exit 0; the draft JSON |
| `py studies/story-trace/o3_dryrun.py` | exit 0; "N/N cases as registered" |
| `py studies/story-trace/segment_regress.py` | exit 0 |
| `py -m pytest tests/test_harness.py -q -p no:cacheprovider -W ignore -k "o3_ or segment or rehearse"` | all passed, 0 failed, 0 skipped |

---

## 10. Open risks (what only the game can settle)
1. **FMV003 right after the warp cut FMV001** (F1). Both are type 0 (skip hit-area armed); O2's warp landed in a type-1
   movie, O1's FMV002 came minutes after its warp. If FMV003 does not play, the start needs a redesign (a two-hop
   start through a quiet field changes `start_residue` and START), so R-START runs first.
2. **The s24 redirect under the trace** (the session's own claim). In-game proven only for the June 6013/6014 fork,
   never traced; a leak reads NOT PROVEN through V16, FORBIDDEN and LANDING, never VOID. P-DONOR and P-DONOR-LOG keep a
   launch-time duplicate from causing it.
3. **King Leo's latch fires once** (TH_E002 e1 t1 [601]). A miss is V15 at `timeout_s`; O1's twin latch held in every
   O1 run.
4. **The soft reset from inside a battle** (F3, S3). If the engine swallows it there, a run stopped mid-battle cannot
   recover and the launch stops.
5. **The published battle scene and result** (F2). `battle.scene` is `battleMapIndex` (the scene id) by the source;
   the result reads 2 or 1 (0.2 #8): both count.
6. **`leave_battle` after a scripted end with no result screen** (F2): the presses are logged and stopped at the scene
   change; a result UI that outlives the battle scene would leave the field down (V14, `land_s`).
7. **Control at a field load.** The settle (1 s) absorbs a one-sample flicker; real control anywhere is V4.
8. **The watchdog against FMV003** (F9): the signature cannot see a movie; `no_progress_s` must exceed the stretch.
9. **The members' first load** (F5): never loaded in game before the smoke.
10. **Settings the agent cannot see**: the boosters (SpeedMode, Attack9999, AutoBattle) are toggled by keys, not
    published; the ini is fingerprinted, a toggle mid-session is not. They change timing, never a store.
11. **63's timed windows under the page rule**: a Confirm may close one early; no store depends on their timing.

---

## 11. Critique log

The critic's twelve problems (`o3_research.json` `critique.problems`), each re-checked in the bytes or the engine
source, and its disposition. Nothing was disproved; nothing was rejected outright.

| # | Problem | Re-checked | Disposition |
|---|---|---|---|
| 1 (blocker) | The driver VOIDs every battle; the id flips to 63/31213 inside the battle's end; King Leo's end fires once and a miss burns `fight()`'s 300 s / 120 turns. | segment_drive.py:1114-1116 (rule 5); HonoluluBattleMain.cs:732-741 (the fold and `fldMapNo` on one frame, `in_battle` still true); HarnessAgent.cs:1537 (raw `fldMapNo`), :1815 (`scene` = `battleMapIndex`); session.py:7407-7411, :7442-7444. | ADOPTED: the registry row `{donor 62, sc 1155, scene 338, won [1,2], lands 63}` matched on a NEW epoch, the published scene and the VISIT's place (2.3 step 1); rule 1b before the route and visit rules (2.2); the executor owns the loop through `leave_battle` to FieldHUD (2.3); `timeout_s`/`max_turns` from the row and `FightTimeout` -> V15 (H7, 2.6); FakeGame cases for an unregistered battle, a wrong scene and a real-63 landing (B4). |
| 2 (major) | Members 31211-31213 have never loaded in game. | No archive since 09-29 holds fld 31211-31213 (the research); O1's preflight is static. | ADOPTED: F-SMOKE (7.1), no trace (so no fork data exists before the freeze), Main_Init's evidence the published objects against stock twins, F5 a STOP item. |
| 3 (major) | NULL cannot see the landing; the donor map is fixed at launch. | `Comparison.stock_only` excludes seam-counted keys; DataPatchers.cs:107-127 (read once a launch), :148-160 (-1 and a warning only); today's log (0.2 #7). | ADOPTED: O3-LANDING (a)-(d) and O3-SEAM over the covered runs (5.3); VOID-ASYM reads V16; FORBIDDEN's `off_route` names the leaked rows of a VOID run (4.8); P-DONOR (files) and P-DONOR-LOG (the launch's own log: the absence of the warning for 61-63 on a log holding "Initialized" -- the engine writes no positive "mapped once" line, 0.2 #7). |
| 4 | The pages come after FMV003's end; the whole ~90 s stretch sits in the 120 s watchdog. | 61 e2 t1 ip324, ip371-ip422 (the critic's reading holds); the agent publishes no movie state (0.2 #11). | ADOPTED with one remedy of the two offered: the beat corrected (2.4); `no_progress_s` drafted 300 and sized by F9 from the measured stretch. The other remedy -- the MBG state in the signature -- needs an agent patch (an engine rebuild), outside this arc: not taken. B4 pins the sizing rule on the fake. |
| 5 | The start lands in a type-0 FMV right after cutting another; never measured. | segment_trace.py:447-454 (the warp ~30 frames after New Game, during FMV001); MBG.cs:205-208, :829. | ADOPTED: R-START first, F1 a STOP item; F-SMOKE records the F side's start too. |
| 6 | The chain is a legacy build: BUILD fails unless O3 opts in as O1 did. | O1-BUILD today: 140 files, 15 own-language, 105 us-build (0.2 #6); Memoria.log English(US). | ADOPTED: `accept_us_build = True`, P-LANG kept, the claim scoped to a US session (5.4), the defect in `o3_forks.json`. |
| 7 | Block 2 is a global override read by both sides; uk ships the US text. | `text_rule` today: 6 byte-equal, KNOWN-KIT-DEFECT 1 (uk), FAIL 0, build and live alike (0.2 #5). | ADOPTED: O3-TEXT and P-TEXT on block 2 (us exact, uk a KNOWN-KIT-DEFECT line); no redeploy before O3; the O4 note in `o3_forks.json`. |
| 8 | LADDER would be vacuous; `Byte[303]++` needs O2's key form. | 61-63: 0 stores and 0 reads of UInt16[0]; 62 e4 t1 ip637-ip703 are `B_POST_PLUS` (O2-KEYS computes them: 0.2 #3). | ADOPTED: O3-NO-SC (by byte span, `c` rows included), the CHAIN with ip1345 excluded by exactness and proven by O3-KEYS, Byte[303] keyed `:=0` then `++` x4 with chained priors (4.2-4.4). |
| 9 | Register only Byte[206]; the legacy noise would also hide another battle's Byte[206]. | TH_E002's census: one store, e1 t1 ip267 (0.2 #1); O1's Byte[199] belongs to TH_E001. | ADOPTED: noise = `[{not_m 1, Byte[206]}]` only; the registry asserts scene 338 live; O3-LANDING (b) pins every battle row to that one store, so a Byte[199] or another site's Byte[206] FAILS even when symmetric; Byte[206] out of STATE and the end state (4.7, 4.9). |
| 10 | Wording; the error-path ips must be explicit forbidden rows that VOID the start. | 61 e0 t0 ip65-ip130, ip323-ip383 (and 62/63's), win_route.txt's window 3 text. | ADOPTED: the wording fixed (0.2 #14); the 14 error-path sites registered and proven (O3-KEYS), the window a stop page (V5: driver at the start, game after; 2.2), A-START uncovers a run whose 61 took the path (5.1), START (c) pins the warp's Byte[13] (old 1), and O3-WRITES (exact) fails any error-path key in a covered run. |
| 11 | `leave_battle`'s presses are unlogged and land in the transition; the stock truth runs under non-default battle settings. | session.py:7457-7463; Memoria.ini (0.2 #13). | ADOPTED: H8 (stop where the field begins; `last_leave`), the presses as `press` rows (2.3 step 3); `settings` frozen, fingerprinted and checked (P-SETTINGS), stated in the report's scope. |
| 12 | Recovery is unmeasured from 64 and from inside battle 338. | segment_trace.py:460-480; the warp refused in a battle (0.2 #9). | ADOPTED: S3 (the soft reset first from a battle); F8 (from 64, R-62 and R-FULL) and F3 (R-BATTLE-VOID). |

The critic's GO conditions -- the battle registry, the F load smoke and the landing check before any session -- are
PART B (S4), section 7 (F-SMOKE, F5) and PART C (O3-LANDING) respectively.
