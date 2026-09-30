# O2 -- Alexandria under the trace: the design

**Status: DESIGN, offline.** Nothing is deployed, launched or frozen. The inputs are `o2_route.md` and `o2_research.json`
in this folder: the reconciled route, with the completeness critic's corrections overriding the route where the two
conflict. This file folds both into code-level decisions, and adds what a re-check of the stock bytes and walkmeshes
found (section 0.2). Every number below was read with the kit, read-only, from the stock US `.eb` files, the
reconciler's listings (`<scratchpad>/o2_research/reconcile/L<fid>.txt`) and the stock walkmeshes as the player walks
them (`pathfind.PlayerWalkmesh`). The offline check (section 6) re-derives every one of them.

**The segment:** New Game, trace on, then a raw `warp <100 | member(100)=31220> 102 1000`. The route runs
100 -> 101 -> 102 -> 103 -> 104 -> 103 -> 105 -> 106 -> 115 -> 116 and ends at `Field(61)` (116 e2 t1 ip1702). It ends
on ARRIVAL in real 61 on both sides. SC climbs 1000 -> 1150 -> 1151 -> 1152 -> 1153 -> 1154 -> 1155.

---

## 0. What this design decides, and what it found

### 0.1 Decided upstream (not relitigated)
- **The start.** A raw harness warp at entrance 102 with scenario 1000: `warp 100 102 1000` stock, `warp 31220 102 1000`
  fork. It runs right after New Game, with the trace armed first. It is not a replay of O1.
- **The end.** Arrival in real field 61, on both sides. Member(116)'s `Field(61)` stays real: that is the seam, and the
  end is judged in donor terms.
- **The session.** S F S F S F. A side short of 2 covered runs re-runs, at most 2 more.
- **The chain.** `import-chain 100 --verbatim --ids 100-117 --fresh-ids --id-base 31220 --name-prefix O2`: 18 members,
  31220-31237, sharing text block 33. The build is at `C:\gd\_ns_playtest\o2\build`. It is NOT deployed.
- **The freeze.** The predictions are frozen by the lead after the in-game stock rehearsals. So the code ships a draft
  function plus a `--freeze` CLI that refuses to overwrite, exactly like `o1_opening.py`.

### 0.2 Found while designing (each verified offline, read-only)
1. **The build is the own-language remap, all 126 files.** Every member's `.eb`, in all 7 languages, equals
   `remap_fields(the donor's stock .eb IN THAT LANGUAGE, donor -> member)`, with 0 US fallbacks. Member(116) = 31236's
   only `Field()` target is real 61. So O2-BUILD accepts the own-language generation only; O1 accepted either.
2. **The build ships text block 33 into FF9CustomMap.** It writes `FF9_Data/embeddedasset/text/<lang>/field/33.mes` in
   7 languages, each byte-equal to the stock block 33 (`dialogue.extract_field_mes("100", lang)`, utf-8, 430 entries).
   Once deployed, the STOCK side reads that file too, since block 33 is 100-117's own. So there is an offline O2-TEXT
   check and a live P-TEXT check: the file must stay byte-equal, or the S side is no longer stock.
3. **100 e11 is the street, not a door.** It has 5 points (x -300..300, z 166..6333), and its tag 2 writes only
   `Map.Byte[36]` (100 e11 t2 ip138). The control spot (0,850) stands inside it. It is registered `benign` and never
   goes in an avoid set.
4. **105 e12 is dead at SC 1152, and it lies across the exit line.** Its tag 2 guard `1150<=SC<1152` (e12 t2 ip38)
   fails at 1152. With e12 avoided, `route_avoiding` finds NO route from the lookout (-244,2562) to e11. Without it, the
   route is one straight 2995u leg. So the critic's rule "pass every non-target region as an avoid zone" becomes: pass
   every LIVE HAZARD of the cell, registered per (field, SC) (section 2.5). The router still gets exactly what the bytes
   say can fire.
5. **115 e14 is a dormant twin of the ladder.** It is the same quad as e15. `InitRegion(14)` sits only in Main_Init's
   default branch (e0 t0 ip406), never at entrance 213 or 215. With e14 avoided, no route reaches the ladder. It is
   registered `dormant`.
6. **Two gated doors sit beside the walked lines.** 101 e17 (-> 112) and 106 e13 (-> 113) carry stock's facing gate
   [48, 208] (`scan_gateways`) and stand on or near the lines walked, so both are always avoided. No O2 TARGET exit is
   gated, so no step passes `gate=` or runs a facing step.
7. **Control points and start spots, from the scripts' own walks.**
   - 105: the lookout (-244,2562) (e14 t1 Walk ip2280; EnableMove ip2859).
   - 116, control #1: (2718,-137) (e21 t1 Walk ip580; EnableMove ip662).
   - 116, control #2: the jump's landing (-339,244) (SetupJump ip877; EnableMove ip958). Triangle 217 is
     (-62,75) (-62,306) (670,305), floor 1; `EnablePathTriangle(217,0)` closes it at ip923, before #2.
   - 115 warped at SC 1155 (entrance 215): the player spawns at (257,-2500) (e17 t0 L197).
   - 106 Puck (e2) walks (800,2200) -> (800,1800) -> (800,-300) -> (800,-1250) -> (-300,-1300) at speed 60.
8. **Start dependence is exactly two keys.** The route has five value-dependent stores:
   - 100 e19 t1 ip1100 `Byte[303]++` (after `:=0` at ip1066);
   - 104 e7 t0 ip333 `Int16[469] |= 1` and e7 t1 ip613 `&= 8190` (after `:=1042` at ip313);
   - 100 e19 t1 ip1531 `UInt16[19] |= 2`;
   - 116 e2 t1 ip765 `Byte[6] |= 2`.

   Only the last two depend on the start. The warp start writes 2 and 2. After O1 they would write 1799 and 3: O1's
   archived S#3 leaves UInt16[19] at 1797 (50 e17 ip1629/1667, 50 e13 ip1149/1187/1225) and Byte[6] at 1 (50 e17
   ip3240).
9. **Hot-spot and pickup scratch are stray-Confirm evidence.** On the route fields, `Int16[220]`, `[222]`, `[224]`,
   `[228]` and `Byte[226]` are written ONLY by two kinds of script. One is the Confirm hot-spots: 100 e12/e13,
   101 e11-e14, 102 e7, 103 e19-e21, 105 e9, 106 e11, 115 e11/e12 and 116 e17-e19, all tag 1. The other is the player
   pickup functions those hot-spots call through `RunScriptSync(2,250,N)`: 100 e19 t16/t17, 101 e19 t14/t15, 102 e12 t12,
   103 e30 t14-t16 and 105 e14 t15. They are registered as forbidden (section 4.7), never as noise.
10. **Jack's contact takes control.** 105 e7 t2 hits DisableMove at ip584 and opens its 16-frame "!" window. A press
    there writes `Bit[3714]:=1` (ip729, L175) and runs `Field(112)`. No press means the mugging, with
    `Bit[3715]:=1` (ip945, L391).
11. **The O1 baseline holds.** At HEAD 47a83122, `o1_opening.py --analyse <archive> --predictions o1_predictions_v4.json`
    reproduces the archived `o1_report.txt` byte for byte; the CLI's `print` adds one trailing newline. The regression
    gate (1.6) rests on this.

---

## 1. Module layout

### 1.1 Files

| File (in `studies/story-trace/` unless a path is given) | | What it holds |
|---|---|---|
| `segment_trace.py` | new | The shared engine, as class `Segment`: predictions I/O and freeze, the offline build/keys checks, the preflight skeleton, the install fingerprint, the session loop, recovery, cutting, reading a session, judging, the verdict, the report, and the CLI. |
| `segment_drive.py` | new | `RouteVoid` and `pick_for`, moved from `o1_opening` with backward-compatible extensions. Also the beat-table driver `drive()`, its step executors and its table helpers. |
| `o1_opening.py` | refactored, thin | O1's constants, plus `draft_predictions()` and `drive()` with their BODIES UNCHANGED. `O1Segment(Segment)` carries O1's exact strings. Module-level wrappers keep every public name. |
| `o2_alexandria.py` | new | `O2Segment(Segment)`: the draft predictions (beat table, regions, keys), O2's extra checks and report sections, the offline checks O2-TEXT, O2-REGIONS and O2-GOALS, the preflight extras, and `--rehearsal-report`. |
| `o2_dryrun.py` | new | O2's synthetic sessions (section 8). |
| `o2_rehearse.py` | new | The stock rehearsal scenario for `tools/play.py`; `--field` picks the stage (section 7). |
| `o2_forks.json` | new | The chain manifest, with `deployed: false` (section 6.4). |
| `segment_regress.py` | new | The O1 regression gate (1.6). |
| `.gitattributes` | edit | `studies/story-trace/o2_predictions*.json -text`, added before any freeze. |
| `tools/harness/session.py` | edit | H1-H3 (section 3). |
| `tools/harness/fakegame.py` | edit | H4. |
| `ff9mapkit/ff9mapkit/content/pathfind.py` | edit | H5: `PlayerWalkmesh(..., closed=())`. |
| `ff9mapkit/tests/test_harness.py` (+ `tests/test_route_avoiding.py` for H5) | edit | The FakeGame and unit tests (sections 3 and 9). |

### 1.2 `segment_trace.py`: the shared engine

O1's machinery, moved and parameterised. Every method is O1's function of the same job, cited by its line in
`o1_opening.py` at HEAD.

```python
THROWS, WHERE                     # o1:64-66, moved; o1_opening re-exports them
RECOVERY_FIELD = 4600             # o1:460

class Segment:
    tag: str                      # "O1" / "O2": check-id prefix, report title; print tag is tag.lower()
    predictions: Path             # the frozen file a session loads (O1: o1_predictions_v4.json)
    manifest: Path                # <tag>_forks.json
    session_file: str             # "o1_session.json" / "o2_session.json"
    report_file: str              # "o1_report.txt"  / "o2_report.txt"
    chain_dir: Path; build_dir: Path
    accept_us_build: bool         # O1 True (its deployed chain predates own-language capture); O2 False
    recovery: int = RECOVERY_FIELD
    titles: dict                  # check id -> its full "what" text; O1's are its archived strings, byte for byte

    # predictions (pure)
    def draft(self) -> dict                                   # subclass
    def load(self, path=None) -> tuple                        # o1:129 load_predictions -> (pred, sha)
    def freeze(self, path=None) -> str                        # o1:134: refuses an existing file; LF; sort_keys
    # offline (reads the install; writes nothing)
    def offline_check(self, pred, build=None) -> list         # o1:222 + self.offline_extra(pred, build)
    def build_check(self, pred, build, stock_lang=None)       # o1:167; the us generation only if accept_us_build
    def keys_check(self, pred, stock, lists=("ladder",))      # o1:205, over every list named
    # the live install (read-only)
    def roots(self) -> list                                   # dali_tour.mod_roots()
    def preflight(self, pred, roots) -> list                  # o1:233 (P-MANIFEST P-DEPLOY P-EB P-FLOOR P-STOCK) + preflight_extra()
    def fingerprint(self, roots, pred) -> dict                # o1:287 + fingerprint_extra()
    # the session (in game)
    def capabilities(self, g) -> list                         # o1:489 P-CAP; O2 adds P-OBJECTS
    def start_run(self, g, side, pred) -> tuple               # o1:544-551, returns the story mark (see below)
    def drive(self, g, pred, side, log, *, deadline, progress) -> dict   # subclass
    def end_run(self, g, log) -> None                         # o1:463, recovery=self.recovery
    def run(self, g) -> None                                  # o1:486-604, the whole session loop
    # analysis (offline, pure but for the stock scripts)
    def cut(self, rows, pred) -> tuple                        # (kept, start_line, end_line, pre)
    def why_void(self, rec, r, pred) -> list                  # extra VOID reasons (base: [])
    def read_session(self, run_dir, pred, *, session=None, stock=None) -> list   # o1:618
    def judge(self, runs, pred, *, frozen) -> list            # o1:667: FROZEN, COVER, then core_checks
    def core_checks(self, runs, cov, pred) -> list            # O1: LADDER NULL STABLE JOIN (o1:680-705)
    def report(self, run_dir, session, pred, sha, runs, checks) -> str   # o1:731-752 + report_extra()
    def analyse(self, run_dir, *, pred_path=None, stock=None) -> tuple   # o1:719
    def main(self, argv=None) -> int                          # o1:756 + subclass flags

# module functions (pure)
members_of(pred); wkey(k); chain_from_campaign(path); stock_lang(game=None)       # o1:143, 147, 70, 156
key_matches(k: WriteKey, pattern: dict) -> bool        # see 4.6/4.7
is_noise(k, pred) -> bool                              # o1:151, extended (4.6)
cut_at_end(rows, end_fields) -> tuple                  # o1:608; a set of donor places now
cut_at_start(rows, start_fields) -> tuple              # new (5.2)
verdict(checks) -> str                                 # o1:709
```

**`start_run`** is O1's sequence with the warp read from the predictions:
1. `g.newgame()`, then `g.wait_frames(30)`;
2. `smark = g.story_mark()`, then `g.storytrace(True)`;
3. `g._check_field_id(start, "warp", True)`;
4. `g.send(f"warp {start} {pred['entrance']} {pred.get('scenario', -1)}")`;
5. `g.wait_for(field_id == start, 60 s)`.

O1's v4 predictions have no `scenario` key, so O1 still sends `warp 50 0 -1` / `warp 31200 0 -1`. No subclass
override is needed.

**`run`** is O1's `run()` step for step: P-CAP, preflight, fingerprint, the members' script snapshot, the session record
with the same keys, `one(i, side)` with the same try/except/finally and record fields, the S F order, reruns while a
side is short, `finished`, `restore_baseline`, `analyse`, the report file, and THROW. The changes are:
- the file names and the print tag come from the attributes;
- the THROW title is `titles["THROW"]`;
- the capability checks are a list (O2 adds P-OBJECTS);
- `drive` and `start_run` are the Segment's methods.

**What differs between O1 and O2** (every other line is shared):

| | O1 (`O1Segment`) | O2 (`O2Segment`) |
|---|---|---|
| start | `warp <50/31200> 0 -1` (v4: no `scenario`) | `warp <100/31220> 102 1000` |
| front cut | none (v4: no `cut_start`) | `cut_start: true`: rows before the first row in the start field are cut, and O2-START judges them |
| end | `end_field: 100` (`end_fields` absent: `[end_field]`) | `end_fields: [61]` |
| coverage beats | `candle, named, battle, garnet`; battle judged by `battle_won` | `booth, ticket, fake, alright, clear, understand, named, climbed` |
| VOID extras | none | forbidden keys in the digest (4.7); no row in the start field |
| core checks | LADDER NULL STABLE JOIN (O1's texts) | START LADDER CHAIN WRITES NULL STABLE JOIN |
| LADDER | the keys present and SC exactly once (`sc_writes: 1`) | the keys present, SC exactly 6 times, in ladder order, each `old` the previous rung (`sc_order: true`) |
| noise patterns | `{not_m, target}` | full key patterns (4.6) |
| BUILD generations | own OR the us build | own only |
| extra offline | none | O2-TEXT, O2-REGIONS, O2-GOALS |
| extra preflight | none | P-TEXT, P-RECOVERY |
| extra fingerprint | none | field 70's override `.eb` sha per folder, each folder's `field/33.mes` sha per language |
| report extras | the dialogue line (O1's text) | start-dependent keys, the SC timeline, the steps table, forbidden hits, the folded transcripts |
| drive | `o1_opening.drive` (unchanged) | `segment_drive.drive` |

### 1.3 `o1_opening.py` after the refactor
- **Unchanged in body:** the constants `PREDICTIONS`, `MANIFEST`, `SESSION_FILE`, `CHAIN_DIR` and `BUILD_DIR`;
  `draft_predictions()`; and `drive()`. Its only change is that `RouteVoid` and `pick_for` now come from
  `segment_drive`, with O1's semantics exactly (section 1.4).
- **`O1 = O1Segment()`**: its `titles` are O1's check texts copied verbatim from HEAD (the gate checks them byte for
  byte), with `accept_us_build = True` and `drive = drive`.
- **Wrappers, so no importer changes:** `load_predictions`, `freeze`, `members_of`, `wkey`, `is_noise`,
  `chain_from_campaign`, `build_check`, `keys_check`, `offline_check`, `preflight`, `fingerprint`, `end_run`, `run`,
  `cut_at_end`, `read_session`, `judge`, `verdict`, `analyse` and `main`. They also re-export `RouteVoid`, `pick_for`,
  `THROWS`, `WHERE` and `RECOVERY_FIELD`, and keep `SIDES` and the private helpers `_roots`, `_changed`, `_show` and
  `_stock_lang`.
  - The FakeGame tests use `O.draft_predictions`, `O.drive`, `O.end_run`, `O.RouteVoid` and `O.pick_for`.
  - `o1_dryrun.py` uses `O.load_predictions`, `O.members_of`, `O.SESSION_FILE`, `O.analyse`, `O.verdict` and
    `O.PREDICTIONS`.
- `o1_dryrun.py` and O1's tests are NOT edited. That they stay green unchanged is part of the gate.

### 1.4 `segment_drive.py`
- **`RouteVoid(Exception)`**, moved from o1_opening.
- **`pick_for(choice, donor, pred, *, sc=None, answered=())`** is O1's function (o1:320). Three rule keys are added,
  each optional and each skipped when absent, so O1's rules behave exactly as before:
  - `sc` (a list): the rule applies only when the published scenario is in it;
  - `once` (bool): a second match, by rule index in `answered`, raises RouteVoid;
  - `take: "default"`: the pick must be the game's own ready cursor (section 2.2, rule 5).

  The candidate loop, the substring rule, the `active` mapping and the "default" pick are untouched.
- **`drive(g, pred, side, log, *, deadline, floor_for=None, prior_for=None, progress=None, end_fields=None,
  observe=None, forbid_live=True) -> dict`** is the beat-table driver (section 2.2). It returns
  `{"end", "why", "beats", "pages", "timed", "choices", "steps", "overlays", "t"}`.
  - `floor_for(donor, closed)` defaults to `PlayerWalkmesh(extract.stock_walkmesh(donor), closed=closed)`.
  - `prior_for(donor)` defaults to `g.key_prior(donor)`. A member walks its donor's floor and prior, which P-FLOOR and
    P-EB prove on the live files.
  - `end_fields` overrides `pred["end_fields"]` for a rehearsal stage.
  - `observe(st, ctx)` is the rehearsal recorder's hook; it is None in a session.
  - `forbid_live` runs rule V12 (section 2.7).
- **Helpers:** `cell(pred, donor, sc)`, `region(pred, key)`, `polys(pred, keys)`, `until_ok(expr, x, z)` and
  `closed_tris(pred, step, wmesh)`, which expands `closed_floors` to triangle indices.

### 1.5 `o2_alexandria.py`
`O2Segment(Segment)` has:
- `tag = "O2"`, `predictions = HERE / "o2_predictions_v1.json"`, `manifest = HERE / "o2_forks.json"`;
- `session_file = "o2_session.json"`, `report_file = "o2_report.txt"`;
- `chain_dir = C:\gd\_ns_playtest\o2\fork`, `build_dir = C:\gd\_ns_playtest\o2\build`.

It carries:
- `draft()`, the section 4 content. Members and names are read from `campaign.toml` as O1 does, with an assertion that
  there are exactly `{31220+i: 100+i for i in range(18)}`.
- `core_checks`, `why_void`, `report_extra`, `offline_extra` (O2-TEXT, O2-REGIONS, O2-GOALS), `preflight_extra`
  (P-TEXT, P-RECOVERY), `fingerprint_extra`, and `capabilities` (P-CAP, P-OBJECTS).
- `trace_summary(rows, pred)`: the SC sequence, the Int16[2] sequence, each registered key present or absent, and every
  unregistered key. `--rehearsal-report` and the dry run both use it.
- The CLI: `--offline-check`, `--preflight`, `--analyse DIR`, `--predictions PATH`, `--freeze` (refuses an existing
  file), `--draft` (prints the draft JSON for review) and `--rehearsal-report DIR`.
- Module-level `run(g)` for `tools/play.py`, which is `O2.run(g)`.

### 1.6 The O1 regression gate (`segment_regress.py`)
The implementer runs it at HEAD before the extraction, then after every commit that touches shared code. It exits 0
only if all five items pass; exit 2 means the archive is missing, and the gate was not run.

| Item | Check |
|---|---|
| G1 | `o1_opening.analyse(ARCHIVE, pred_path=HERE/"o1_predictions_v4.json")`: the report text equals `(ARCHIVE/"o1_report.txt").read_text(encoding="utf-8")` exactly (read_text folds the archive's CRLF), and the verdict is `PROVEN` with 6 checks, all True. `ARCHIVE = C:\gd\Dream-World-IX\.harness-runs\20260929-213149-story-o1e`. |
| G2 | `py studies/story-trace/o1_opening.py --analyse ARCHIVE --predictions studies/story-trace/o1_predictions_v4.json` exits 0. |
| G3 | `o1_dryrun.run_cases(o1_predictions_v4.json)` returns 0: 16/16 as registered. |
| G4 | `o1_opening.offline_check(v4)` returns the same `[(ok, what, detail)]` as `research/o1_regress_baseline.json`, which the implementer captures at HEAD BEFORE the refactor and commits with the gate. |
| G5 | `py -m pytest tests/test_harness.py -q -p no:cacheprovider -W ignore -k "o1_ or overlay_hint"`, run from `ff9mapkit/`, is green. |

The archived `o1_session.json` records the O1 worktree's predictions path. G1 and G2 pass `--predictions` explicitly,
with the same sha.

---

## 2. The beat table

### 2.1 The model (JSON in the predictions)
- **`table`** is a list of CELLS, keyed `(donor, sc)`: the donor place and the PUBLISHED scenario counter while the
  player holds control. A cell has `steps` and optional flags:
  - `no_pages` (a page there is VOID, and nothing is pressed);
  - `watch` (objects whose radius is VOID: `[{"sid", "name", "radius": "range_r"}]`).
- **The counter.** Each VISIT keeps a per-cell count of the steps done. A new visit starts when the published field id
  changes; the second visit to 103 is a new visit. Control held in a cell runs `steps[done]`. A step counts as done
  only on its own `done` evidence (2.3).
- **The step shape.**
  ```json
  {"kind": "cross|trigger|confirm|wait_sc|leave_now", "name": "...", "target": "<region key>",
   "until": {"x_le": 900}, "goal": [x, z], "avoid": ["<region key>", ...], "to": <donor>,
   "expect": "choice|control_lost", "then": "climb", "sc": 1153, "wait_s": 90,
   "npcs": true, "overlay_ok": false, "immediate": false, "settle": null, "lunge_ticks": 0,
   "closed_tris": [], "closed_floors": [], "attempts": 2, "interrupts": 1, "beat": null, "start": [x, z]}
  ```
  - `target` and `until` are exclusive.
  - `start` is used only by the offline route check (O2-GOALS). The live walk plans from where he stands.
  - The defaults are in `steps_default` (4.1).
- **Other keys:** `regions` (2.5), `choices` (2.6), `naming: [{"donor", "sc", "beat"}]` and
  `route: [100, 101, 102, 103, 104, 105, 106, 115, 116]`. The places a run may stand in before the end are `route`
  plus `end_fields`.

### 2.2 The driver loop (`segment_drive.drive`)
O1's loop, with its rules in O1's order. First match wins, and every poll reads `st = g.state`,
`donor = members.get(fid, fid)` and `sc = st.scenario`.
1. **End.** `donor in end_fields` -> return `reached`.
2. **Route.** `fid > 0` and `donor` not in `route` -> RouteVoid "left the route: entered <fid> (donor <d>)". A field id
   of 0 or below, published during a load, is waited out (rule 9).
3. **Visit.** When the (positive) field id changed, start a new visit. With `forbid_live`, scan the run's own rows
   (`g.story_rows()` after its last `arm` epoch) for forbidden patterns (4.7) -> RouteVoid on a hit (V12).
4. **Naming** (ui `NameSetting`). A registered `(donor, sc)` runs `g.accept_name()` and sets its beat. Anywhere else,
   RouteVoid.
5. **Tutorial or battle.** RouteVoid: O2 registers neither. O1 keeps its own drive, so O1's battle path is untouched.
6. **Choice.** O1's readiness hold, unchanged: `_choice_ready`, and the snapshot held unchanged for `settle_s` over live
   frames. Then:
   - `index, rule = pick_for(st.choice, donor, pred, sc=sc, answered=answered)`;
   - with `rule["take"] == "default"`: `index` must equal `st.choice["selected"]`, the game's own ready cursor, or
     RouteVoid "the frozen pick <text> is not the game's default <selected>: stepping the cursor is not the route".
     Then `g._take_default_choice(st)`, which confirms the cursor option and never presses up or down;
   - otherwise `g.choose(index)`, which O1's non-default picks keep;
   - record `{field, donor, sc, options, active, selected, count, index, took}`, add the rule to `answered`, set its
     beat.
7. **Page** (dialog open, text, control OFF).
   - In a `no_pages` cell: RouteVoid "a page where the route has none: <text>". Nothing is pressed: in (105, 1152) a
     Confirm could be exactly Jack's side trip.
   - Otherwise O1's rule: record the text, then `press("confirm", 3)` and `wait_frames(frames_for_ticks(4))`.
   - A page whose `raw_texts` holds `[TIME=` is recorded in `timed` (its index), so the transcript can fold it.
8. **Control held** (`player_x` known, not fading).
   - Log an overlay: a dialog up WITH control is O1's rule, never paged.
   - `cell = table[(donor, sc)]`; if absent, RouteVoid "control held in <fid> (donor <d>) at SC <sc>, where the table has
     no entry" (V4).
   - Settle O1's way: `settle_s` of consecutive control samples, unless the next step is `immediate`.
   - `step = cell.steps[done]`; if `done == len(steps)`, RouteVoid "control held after the cell's last step".
   - Run the step's executor (2.3), then update the counters from its outcome.
9. **Otherwise:** sleep 0.05 s.

Between executor calls, while in a cell with `watch`, every poll checks each watched object:
`dist(player, object) <= object[radius]` -> RouteVoid (V6).

The deadline raises `HarnessError("the run's budget ran out in field <fid>")`, as O1's does.

### 2.3 Step kinds (the executors)
Each executor returns `(outcome, record)`, where outcome is one of:
- `done` (the step's evidence seen);
- `interrupted` (control went away in the same field with no evidence);
- `failed` (the walk ended with control held and no evidence);
- `void: <why>`.

The counters: `failed` spends an attempt (`attempts` exhausted -> VOID). `interrupted` spends an interruption
(`interrupts` exhausted -> VOID). The walk calls all pass `walkmesh=floor_for(donor, closed)`,
`prior=prior_for(donor)`, `unstick=True`, `smooth=True`, `margin=pathfind.KEEPOUT_MARGIN_W`, `timeout=timeout_s`,
`handoff=True` (H1), `npcs=step.npcs` and `overlay_ok=step.overlay_ok`.
- **`cross`** calls `g.route_cross(*goal, zone=R.points, region=R.points, avoid=polys(step.avoid), ...)`.
  - The field changed: `done` if the new donor is `step.to`; otherwise VOID (V11).
  - Control went away in the same field: `interrupted` (100's Rat Kid).
  - Otherwise: `failed` (the record's `inside` says whether he stood in the zone).
- **`trigger`** calls `g.route_to(*goal, zone=R.points if target else None, avoid=..., ...)`.
  - Control went away with the evidence true at that sample (standing in `target` by `doorface.region_contains`, or
    `until` holding for the published x/z): `done`.
  - Control went away without the evidence: `interrupted`.
  - The walk ended with control held: wait up to 2 s for control to go; `done` or `failed` as above.
- **`confirm`** calls `g.route_to(*goal, zone=R.points, avoid=..., ...)`.
  - If he stands in the target with control: `g.press("confirm", 4)` (a plain press, as O1's candle), then
    `g.wait_for(expect, confirm_s)`. `expect` `choice` means `st.choice is not None`; `control_lost` means
    `not st.control`. The expectation seen: `done`. Nothing seen: `failed`.
  - With `then: "climb"` and `done`: `g.climb("up", until=..., **step.climb)` (H2). It stops when page 384 opens, the
    field changes, or `player_y < -2431`.
    - `until`: `done`, and the beat `climbed` is set.
    - `control` (he slid to the bottom and control came back): `failed`, and the step runs again.
    - `stalled` or `not-started`: VOID (V9).
- **`wait_sc`** calls `g.route_to(*goal, avoid=..., ...)`, then
  `g.wait_for(sc == step.sc or not control or field changed, step.wait_s)`.
  - The scenario reached: `done`. Control lost: `interrupted`. Timeout: VOID (V8).
- **`leave_now`** (`immediate`: no driver settle):
  1. `lunge = g.lunge(*goal, ticks=step.lunge_ticks, avoid=..., walkmesh=...)` (H3), skipped when `lunge_ticks` is 0
     or the field has no cached basis;
  2. then `g.route_cross(..., settle=0.0, npcs=False, handoff=True)`.

  The outcome is judged as `cross`, but `interrupted` is VOID there (`interrupts: 0`): in (105, 1152) a lost control is
  Jack.

Every step writes a log row
`{"k": "step", "field", "donor", "sc", "visit", "n", "kind", "name", "attempt", "outcome", "t0", "t1", "from", "to",
"route": <route record trimmed as dali_tour does>, "lunge", "climb"}`. The rehearsal report and the analysis's steps
table read these rows.

### 2.4 The O2 table

The measurements used in the Goal column:
- **wall** is `PlayerWalkmesh.distance_to_boundary`, against cam.COLLISION_RADIUS_W = 80;
- **depth** is the distance inside the target region by the engine's IsInQuad rule;
- **route** is `route_avoiding` from the step's `start`, with the step's `avoid` set, `leave_wall`.

| Cell | Control comes | Step | Goal (checked) | Avoid (and not avoided) | Flags | Done |
|---|---|---|---|---|---|---|
| (100, 1000) | Stage 6: 100 e19 t1 EnableMove ip2020, at (0,850). Again after the bump: e19 t15 EnableMove ip2143. | cross `100.e15` -> 101 | (0,7000): floor 1, wall 421, depth 331. Route 1 leg, 6150u. | `100.e16` (-> 107), `100.e17` (-> 114). Not avoided: `100.e11`, benign (0.2 #3). | `npcs: false` (the Rat Kid is a MoveInstant chaser at z+83/frame; a planner keeping out of his disc stalls, and the bump is forced), `interrupts: 1`, `closed_floors: [3]` (EnablePath(3,0) e1 t1 ip124 until ip410; conservative after it) | Landed in 101 |
| (101, 1000) | Stage 2: 101 e7 t1 EnableMove ip358, at (1939,-883). | cross `101.e16` -> 102 | (-2936,-400) (region_goal): floor 2, wall 461, depth 470. Route 3 legs, 5170u. | `101.e15` (-> 100: the arrival door, 300u east of the control spot), `101.e17` (-> 112, facing-gated, on the street). | `npcs: true` (the nobles walk off to (-4000,-400)) | Landed in 102 |
| (102, 1000) | On arrival: 102 e0 t0 ip543, at (865,2525). | cross `102.e8` -> 103 | (752,5415): wall 308, depth 323. Route 1 leg, 2892u. | `102.e9` (-> 101), `102.e10` (-> 108). | `npcs: true` | Landed in 103 |
| (103, 1000) | On arrival, at (-75,-2210). | confirm `103.e28` (the booth "?"), `expect: choice` (215) | (50,-800): wall 292, depth 200, 762u from the plaque hot-spot 103 e20 (600,-272). Route 1 leg, 1416u. | `103.e22` to `103.e27` (e26 and e27 are one quad). | `npcs: true` (Hippaul, e18, walks the square) | The choice opened; the rule answers it (2.6) |
| (104, *) | Never: 104 gives no control. | (none) | | | | Control here is V4 |
| (103, 1150) | On arrival: spawn (45,-950), INSIDE `103.e28` (the "?" is up). | cross `103.e22` -> 105 | (-3993,-965) (region_goal): wall 477, depth 512. Route 3 legs, 4199u. | `103.e23` to `103.e27`. Not avoided: `103.e28`, benign here: its tag 2 only shows the bubble, and a cross never presses Confirm. | `npcs: true`. 215 opening here is V1 (rule scope). | Landed in 105 |
| (105, 1150) | On arrival: 105 e14 t0 EnableMove ip348, at (-51,2986). | trigger `105.e12` (tag 2: guard ip38, DisableMove ip75) | (-500,1750): wall 381, depth 291. Route 1 leg, 1315u. | `105.e10` (-> 103), `105.e11` (-> 106). | `npcs: true`, `closed_floors: [2]` (EnablePath(2,0), Main_Init ip296/325) | Control lost standing in e12 |
| (105, 1152) | Stage 14: 105 e14 t1 EnableMove ip2859, at the lookout (-244,2562), about 13-29 ticks after Jack wakes (Map.Byte[35]:=0 ip2720). | leave_now `105.e11` -> 106 | (-667,-403) (region_goal): wall 533, depth 422. Route 1 leg, 2995u. | `105.e10`. Not avoided: `105.e12`, dead at 1152 and lying across the line (0.2 #4). | `immediate`, `lunge_ticks: 10`, `settle: 0`, `npcs: false` (never wait for Jack), `attempts: 1`, `interrupts: 0`. Cell: `no_pages`, `watch: [{sid 7, "Alleyway Jack", range_r}]` | Landed in 106 |
| (106, 1152) | On arrival: 106 e16 t0 EnableMove ip406, at (-123,3494). | wait_sc `sc: 1153` | (550,2000): floor 3, wall 427, 320u from Puck's stop (800,1800), well inside his 1200/1400. Route 2 legs, 1655u. | `106.e12` (-> 105, 140u from the spawn), `106.e13` (-> 113, gated, on the street at z about 0), `106.e14` (-> 115, not before 1153). | `overlay_ok` ("Over here!" [TIME=45], shown WITH control), `npcs: true`, `wait_s: 90`. Cell: `no_pages` | Published SC 1153 (106 e2 t1 ip312) |
| (106, 1153) | Continues from the wait. | cross `106.e14` -> 115 | (-123,-1306) (region_goal): floor 3, wall 84, depth 88, the deepest standable spot, so the walk finishes on the zone. Route from (550,2000): 5 legs, 3939u. | `106.e12`, `106.e13`. | `overlay_ok` (328/329 [TIME=45]), `npcs: true` (Puck walks the same line into e14 and removes himself). Cell: `no_pages` | Landed in 115 |
| (115, 1154) | Stage 1: 115 e1 t1 EnableMove ip500, at (206,-1911). | confirm `115.e15` (the ladder "!"), `expect: control_lost` (e15 t3 Map.Byte[49]:=1 ip65, then e17 t1 DisableMove ip913) | (0,50): wall 117, depth 90. Route 1 leg, 1972u. | `115.e13` (-> 106: the arrival door). Not avoided: `115.e14`, dormant (0.2 #5). | `npcs: true` | Control lost |
| (115, 1155) | Stage 10: 115 e17 t1 EnableMove ip1841 (SC already 1155); the position is the rehearsal's to measure. The warp-start spawn is (257,-2500): route 3 legs, 2607u. | confirm `115.e15`, `expect: control_lost`, `then: climb`, `beat: climbed` | (0,50) | `115.e13` | `npcs: true` (Kupo is talkable at about (304,-785) from stage 10; the plan keeps out of his talk radius, and only the ladder gets a Confirm), `attempts: 2` (a slide to the bottom gives control back) | The climb reached the top: page 384 or field 116 |
| (116, 1155) #1 | Stage 3: 116 e21 t1 EnableMove ip662, at (2718,-137). | trigger `until {x_le: 900}` (e21 t1 ip742, DisableMove ip773) | (630,190): floor 1, wall 115. Route 3 legs, 2303u. | 116 has no regions. | `npcs: true` (Puck walks this line and pauses: wait behind him, never push) | Control lost with x <= 900 |
| (116, 1155) #2 | Stage 8: e21 t1 EnableMove ip958, at the landing (-339,244). | trigger `until {z_ge: 2300}` (ip1038, DisableMove ip1069) | (-750,2690): wall 115. Route 3 legs, 2736u. | | `npcs: true`, `closed_tris: [217]` (EnablePathTriangle(217,0) ip923) | Control lost with z >= 2300 |
| (116, 1155) #3 | Stage 11: 116 e2 t1 EnableMove ip901. | trigger `until {x_gt: 3000, z_gt: 10300}` (e16 t1 ip11, DisableMove ip50) | (3410,10700): wall 137. Route from (-750,2690): 14 legs, 13610u. | | `npcs: true`, `closed_tris: [217]` | Control lost with the predicate true |
| end | | donor 61 -> `reached` | | | | |

`naming: [{"donor": 116, "sc": 1155, "beat": "named"}]`: this is stage 10, `Menu(1,1)` at 116 e2 t1 ip758.

The steps with `closed_floors` or `closed_tris` were re-checked with those triangles closed, using a stand-in for H5:
- 100: floor 3's 7 triangles closed;
- 105: floor 2's 2 triangles closed;
- 116: triangle 217 closed.

Every route and goal above is unchanged.

The rejected points are recorded so nobody re-picks them:
- the map's (100,1800) in 106 is OFF the mesh;
- the map's (-100,-1320) in 106 is 65u from a wall, under the controller radius;
- the map's booth point (45,-950) is only 50 deep, so it is the candle-class miss;
- the map's 116 points (800,260), (-715,2400) and (3370,10500) are 74, 79 and 88 from walls.

### 2.5 Regions (frozen with the predictions; O2-REGIONS re-decodes each from the stock bytes)
Points are the engine's, in SetRegion order: `(x, z)`, s16 from the packed args. Roles:
- `exit`: a gateway; its `to` and entrance are from `scan_gateways`.
- `confirm`: its tag 3 runs on Confirm.
- `walkin`: its tag 2 takes control.
- `benign`: never fires anything global or takes control.
- `dormant`: never InitRegion'ed on this visit.

| Key | Points | Role |
|---|---|---|
| 100.e11 | (300,166) (-300,166) (-300,3555) (-50,6333) (70,6333) | benign: tag 2 writes `Map.Byte[36]` only |
| 100.e15 | (-365,7708) (295,7708) (355,6538) (-371,6532) | exit -> 101 (200) |
| 100.e16 | (-1019,-439) (961,-439) (704,104) (-860,191) | exit -> 107 (200) |
| 100.e17 | (1224,1225) (1252,923) (777,893) (677,1074) (777,1253) | exit -> 114 (200) |
| 101.e15 | (3295,-65) (3326,-987) (2238,-1444) (2872,261) | exit -> 100 (201) |
| 101.e16 | (-3500,-600) (-3500,-200) (-2621,444) (-2254,-1444) | exit -> 102 (201) |
| 101.e17 | (110,233) (-100,233) (-183,-855) (206,-855) | exit -> 112 (201), gate [48,208] |
| 102.e8 | (858,6987) (468,6987) (404,5142) (1134,5019) | exit -> 103 (203) |
| 102.e9 | (175,663) (2190,999) (1607,2186) (941,2429) (191,2361) | exit -> 101 (203) |
| 102.e10 | (2753,4854) (2804,4832) (2220,4436) (2130,4617) | exit -> 108 (203) |
| 103.e22 | (-4263,-1798) (-4605,-734) (-3611,-119) (-3150,-2777) | exit -> 105 (205) |
| 103.e23 | (333,-4477) (-555,-4477) (-888,-3430) (666,-3411) | exit -> 102 (205) |
| 103.e24 | (2537,3762) (2792,3650) (2440,2476) (2160,2641) | exit -> 109 (205) |
| 103.e25 | (4999,400) (4999,999) (3848,999) (3868,400) | exit -> 110 (205) |
| 103.e26 | (-3351,2611) (-3656,2216) (-2835,1505) (-2480,1977) | exit -> 111 (205) |
| 103.e27 | the same quad as e26 | exit -> 111 (206) |
| 103.e28 | (-500,-111) (550,-111) (250,-1000) (-200,-1000) | confirm (the booth: tag 3 `Map.Byte[24]:=1` ip95) |
| 105.e10 | (1138,3845) (1098,4226) (-292,4577) (264,2527) | exit -> 103 (111) |
| 105.e11 | (-185,-770) (-1223,-895) (-1327,-167) (-220,195) | exit -> 106 (111) |
| 105.e12 | (-964,1677) (-1055,2300) (55,2000) (-122,1203) | walkin, live only while 1150 <= SC < 1152 |
| 106.e12 | (-1048,4163) (-1048,3623) (-262,3319) (-364,4135) | exit -> 105 (211) |
| 106.e13 | (-487,156) (-487,-84) (180,-196) (180,164) | exit -> 113 (211), gate [48,208] |
| 106.e14 | (-327,-1240) (-317,-1462) (151,-1458) (151,-1188) | exit -> 115 (211) |
| 115.e13 | (-124,-3597) (984,-3546) (745,-2881) (633,-2741) (-34,-2783) | exit -> 106 (212) |
| 115.e14 | (150,144) (-150,144) (-150,-40) (150,-40) | dormant (InitRegion(14) only in e0 t0's default branch, ip406) |
| 115.e15 | the same quad as e14 | confirm (the ladder: tag 3 ip65, climb at ip125 when Map.Byte[24]==10) |

104 and 116 have no SetRegion at all.

### 2.6 Choice rules (in this order; first match wins)

Every O2 pick is option 0, which is the game's default cursor (ETb.cs:100-103; 104's `EnableDialogChoices(1043, 0)`).
So every O2 rule is `take: "default"`, and the driver never moves a cursor.

| # | donor | sc | match | pick | once | beat | publication (research + critic) |
|---|---|---|---|---|---|---|---|
| 1 | 103 | [1000] | `ticket booth` | `ticket booth` | yes | booth | 215 has no prompt line, so it publishes `['', 'eek into the ticket booth', 'Cancel']` |
| 2 | 104 | [1000] | `ticket` | `ticket` | yes | ticket | 251, masked by 1043: active [0, 1, 4, 10], default absolute 0 `Show ticket`. It has 2 prompt lines, so the first option is intact (the critic); `ticket` matches either way. Never an info option (they rewrite Int16[469]). |
| 3 | 105 | [1150] | `fake` | `Yeah` | yes | fake | 305: `Y-Yeah, it's fake` / `N-No, it's not fake` / `Are you Alleyway Jack?` |
| 4 | 105 | [1151] | `want to` | `right` | yes | alright | 310: `Alright` / `N-No, I don't want to`. Option 1 would park the scene (stage 7). |
| 5 | 105 | [1151] | `someone` | `clear` | yes | clear | 314: `Yeah, it's clear` / `I think someone's coming` |
| 6 | 115 | [1154] | `Once more` | `understand` | yes | understand | 367: `I understand` / `Once more...` |
| 7 | null | null | `want to skip` | `default` | no | none | O1's skip-movie rule, kept LAST. mbg101 cannot raise it (type 1), and 61's FMV003 comes after the end. |

The apostrophes in this text block are U+2019, and no rule string contains one. The SC column is what the scene
publishes when each window opens: 1150 is written before 305 (104's store), 1151 right after 305/308 (105 e3 t1 ip511),
and 1154 before stage 6 (115 e1 t1 ip462).

### 2.7 VOID conditions (live; each is a RouteVoid with its reason, and the run is not covered)
- **V1.** A choice no rule matches for its donor and SC. 215 re-offered at SC 1150 lands here.
- **V2.** A `once` rule asked again: 251 after an info option, or 215 twice.
- **V3.** A `take: "default"` rule whose ready cursor is not the pick. This forbids stepping the cursor, including in
  104's menu.
- **V4.** Control held in a cell the table does not have, e.g. 104 or (105, 1151); or control after a cell's last step.
- **V5.** A page (control off) in a `no_pages` cell: Jack's window or the mugging in (105, 1152), or anything
  unexpected in 106. It is VOID with NO Confirm.
- **V6.** A watched object within its radius: Jack (sid 7) inside his published `range_r` in (105, 1152).
- **V7.** A step out of `attempts`, or over its `interrupts`.
- **V8.** `wait_sc` timed out (SC never reached 1153).
- **V9.** The climb stalled (3 Up bursts moved y by nothing), or never started (control still held 5 s after the
  Confirm).
- **V10.** A naming screen, battle or tutorial outside a registered cell.
- **V11.** The run left the route: it stood in a place outside `route + end_fields`, or a crossing landed somewhere
  other than its step's `to`.
- **V12.** Live forbidden scan: at a new visit, the run's own rows since its arm hold a forbidden key (4.7).
- **V13.** The budget (`STOPPED: ...`), or an unexpected exception (`STOPPED (unexpected): ...`), as in O1.

Every one of these makes the run VOID, never a finding. The analysis repeats the trace-visible ones (4.7), so a driver
fault can never turn a walk divergence into STOCK ONLY or FORK ONLY.

### 2.8 Every research beat, and what handles it
The beat numbers are `o2_research.json`'s `reconciled.route.beats`. The rules are the loop's (2.2); cells are 2.4;
choice rules are 2.6.

| Beats | Field | Handled by |
|---|---|---|
| 1-2 | 100 | Rule 9, waiting: mbg101 plays with no control and no dialog. Nothing is pressed; type 1 has no skip dialog. |
| 3, 5, 6 | 100 | The page rule: 146; 147 (async + WaitWindow); 148 [TIME=20], recorded as timed. |
| 4 | 100 | Nothing: the stage-3 party writes (4.4). |
| 7-10 | 100 | Cell (100, 1000). The cross is interrupted once by the bump; 154 [TIME=10] and 155 are pages; the same step then runs again. |
| 11-13 | 101 | The page rule (168), then cell (101, 1000). |
| 14 | 102 | Cell (102, 1000). |
| 15 | 103 | Nothing: Hippaul's `:=1` is registered (4.4), his `:=2` is noise (4.6). |
| 16-17 | 103 | Cell (103, 1000) confirm, then choice rule 1 (215). |
| 18-24 | 104 | The page rule (250, 252, 253, 254, 255, 256, three times 70, 257) and choice rule 2 (251). There is no control anywhere in 104. |
| 25-26 | 103 | Cell (103, 1150); no Confirm. |
| 27 | 105 | Cell (105, 1150). |
| 28-34 | 105 | The page rule (415 timed, 416-418, 304, 308, 312, 313, 315) and choice rules 3, 4 and 5. |
| 35-36 | 105 | Cell (105, 1152), leave_now. Jack is handled by V5, V6 and V12. |
| 37-38 | 106 | Cells (106, 1152) wait_sc and (106, 1153) cross, under overlays. |
| 39-40 | 115 | The page rule (352, 353), then cell (115, 1154) confirm. |
| 41-44 | 115 | The page rule (356 timed, 357-366, 368, 370-383) and choice rule 6 (367). |
| 45-47 | 115 | Cell (115, 1155): confirm, then the climb; then the page rule (384). |
| 48-52 | 116 | The page rule (387-394), cell (116, 1155) #1 and #2. |
| 53 | 116 | The page rule (395, 396), the naming (116, 1155), the page rule (397-399). |
| 54-56 | 116 | Cell (116, 1155) #3, the page rule (400-402), then the end (61). |
| 57 | all | Never taken: the forbidden keys (4.7) and V1/V3 keep optional content out. |

---

## 3. Harness additions (each minimal, modelled in the FakeGame, tested)

Every default keeps today's behaviour, so no existing caller changes. Each addition lands with the FakeGame tests named
here, in `ff9mapkit/tests/test_harness.py`.

**H1. `route_to` / `route_cross` pass-throughs: `settle`, `overlay_ok`, `handoff`.**
- `route_to(..., settle=None, handoff=False)`:
  - `settle` goes to its opening `wait_control(settle=...)`. None is SETTLE (1.0 s), as today.
  - `handoff=True`: when control goes away mid-walk, during a facing step, or the field changes, `land()` returns at
    once. It does not call `_await_landing(origin, timeout)`, so there is no wait for the landing, no wait for control
    to come back, and no wait for the destination to become playable. `landed` is the new id if the field already
    changed, else None, and `record["handoff"] = True`.
- `route_cross(..., settle=None, overlay_ok=False, handoff=False)`:
  - It passes all three to `route_to`. Today it never passes `overlay_ok`, so its opening `wait_control` holds for as
    long as a hint is up: every one of 106's [TIME=45] hints costs its whole duration, and a hint Puck shows again
    (while Vivi is over 1200u away) can outlast the wait.
  - With `handoff`, a walk that ended with control held waits (bounded by `timeout`) for `field_id != origin or not
    control`, then returns. It never calls `expect_field_change`'s `wait_playable`, so an arrival scene (101's Herald,
    115's Puck) is the caller's to sit through. There is no "never became playable" error and no parsing of error
    text, unlike dali_tour's `_REACHED`.
- **Tests:**
  - `test_route_cross_handoff_returns_at_the_field_change_into_a_scene`: a region whose destination arrives without
    control (H4 `arrive_control: False`) returns `landed` = the destination. The control case: `handoff=False` raises
    "never became playable" with a 2 s timeout.
  - `test_route_to_handoff_returns_when_a_trigger_takes_control`: an H4 `take` region returns within 10 frames with
    `during` "walk" and `landed` None. The control case waits out its timeout.
  - `test_route_to_settle_zero_walks_on_the_first_control_sample`: a director grants control at fake frame F, and
    `g._axes` is pre-seeded, so there is no calibration. With `settle=0.0`, the first `hold` is executed within 0.2 s of
    wall time of the grant. The control case (default settle) is not before 1.0 s. Assert in wall time, or in the
    fake's frames converted at its loop `fps` (240 by default, not the 60 fps render clock): SETTLE is a wall-clock
    hold.
  - `test_route_cross_walks_under_an_overlay_only_when_told`: O1's overlay test, applied to route_cross.

**H2. `Session.climb(button="up", *, until, burst_frames=30, max_bursts=80, stall_bursts=3, start_timeout=5.0) -> dict`.**
- It refuses off a field (`_require_field`).
- It waits up to `start_timeout` for control to go away. A climb runs with control off (115 e15 t3 DisableMove ip103);
  if control is still held, it returns `ended: "not-started"`.
- It then holds `button` in bursts, `hold <button> <burst_frames>` plus `wait <burst_frames + 2>` in one request, as
  `walk()` does. It never presses or holds any other button: Down and Right descend (B_KEY(96)).
- After each burst it reads the state. `until(st)` true gives `"until"`; the field changed gives `"field"`; control
  back gives `"control"` (the bottom's EnableMove, ip172); y moved by less than 1u over `stall_bursts` consecutive
  bursts after the first move gives `"stalled"`; burst `max_bursts` gives `"bursts"`.
- It returns `{"ended", "bursts", "frames", "y0", "y1", "ys"}`.
- **FakeGame model (H4):** `fake.ladder = {"top": -2431, "bottom": -101, "step": 20}`, `fake.climbing`,
  `fake.climbed`.
- **Tests:**
  - `test_climb_holds_up_until_the_page_and_nothing_else`: the director opens a page when `climbed`, and `executed`
    holds only `up` holds.
  - `test_climb_says_stalled_when_up_moves_nothing` (a deaf ladder).
  - `test_climb_says_control_when_he_slides_back` (the director drops him to the bottom).
  - `test_climb_not_started_when_control_stays`.

**H3. `Session.lunge(x, z, *, ticks=10, avoid=(), walkmesh=None, margin=None, gait="run") -> dict`.**
This is the leave-immediately press: one hold toward (x, z) on the FIRST live sample with control, with no settle, no
calibration and no plan.
- It needs control now (one live sample) and a CACHED basis `self._axes[field]`. It raises HarnessError without one: in
  (105, 1152) the e12 walk of the same visit has calibrated 105 (or 31225).
- The pad is the `_eight_way(basis)` direction with the largest dot product with the bearing to the goal.
- The hold is `rate.frames_for_ticks(ticks)` frames, clipped to the longest prefix whose segment, out to
  `rate.reach(frames, gait)`:
  - stays on `walkmesh` with `distance_to_boundary >= cam.COLLISION_RADIUS_W`, sampled every 16u;
  - stays `margin` (default `pathfind.KEEPOUT_MARGIN_W`) clear of every `avoid` polygon (`pathfind.seg_poly_gap`);
  - does not pass the goal's projection.

  Under one tick, it presses nothing and returns `pressed: False`.
- It sends `hold <b> <frames>` for each button of the pad, then `wait <frames + 2>`, in ONE request, and returns
  `{"pressed", "pad", "frames", "from", "to", "travelled", "sample_frame", "done_frame"}`. `sample_frame` is the frame
  of the control sample it acted on, so the rehearsal can read the latency.
- **Tests:**
  - `test_lunge_holds_toward_the_goal_on_the_first_sample`: control is granted at F. The hold is executed within
    0.1 s of wall time (a single request after one state read), it is the eight-way pad nearest the bearing, and it
    moves him toward the goal.
  - `test_lunge_stops_short_of_an_avoid_zone`: a zone 300u ahead leaves a shorter hold, and he ends outside the margin.
  - `test_lunge_refuses_without_a_basis`.

**H4. FakeGame (`tools/harness/fakegame.py`).**
- `warp <field> [entrance] [scenario]` sets `self.entrance` (arg 1, when >= 0) and `self.scenario` (arg 2, when >= 0).
  Today both are dropped, so `warp 30820 102 1000` cannot publish SC 1000.
- **The ladder:** `self.ladder` (None), `self.climbing = False`, `self.climbed = False`. In `_step_world`, BEFORE the
  "no control, no tick of it moves him" skip, `_step_ladder(ticks)` runs while `climbing`:
  - Up or Left held: y -= step per field tick. Down or Right: y += step.
  - y < top: `climbing = False`, `climbed = True`, control stays off.
  - y > bottom: `climbing = False`, `control = True`.
  - y is `player[1]`, already published.
- **Regions** (the `regions` dicts) get two opt-in keys:
  - `"take": True`: entering sets `control = False` and appends to `fired` with `to` None; it is a walk-in trigger.
  - `"arrive_control": False`: the destination arrives with control OFF, the arrival scene's to hand back.
- **Tests:** `test_fake_warp_publishes_the_scenario`, plus the ladder and region keys through the H1/H2 tests above.

**H5. `pathfind.PlayerWalkmesh(wmesh, mask=0xFF, opened=(), closed=())` (kit, additive).**
The triangles in `closed` are closed to him like a door strip: not floor, their edges are walls. This is the script's
`EnablePathTriangle(n, 0)` / `EnablePath(floor, 0)`, which the offline planner otherwise cannot see:
- 116 triangle 217 after ip923;
- 105 floor 2 until Puck's ladder (Main_Init ip296/325; e3 t1 ip1113/1448);
- 100 floor 3 during the chase (e1 t1 ip124 -> ip410).

`standing_at` keeps `closed`. Test: a closed triangle is off the floor, its shared edges are walls, and
`route_avoiding` goes round it. The planned O2 routes already clear all three (O2-GOALS checks it), so H5 guards
REPLANS: a stall or an NPC replan must never plan over the fallen plank.

**Not needed:**
- Runtime region decoding: the polygons are frozen (2.5).
- Stage or bubble publication: cells key on SC plus the counter; triggers on regions and positions.
- NPC tracking: s89's `objects` is live.
- A new choice verb: `_take_default_choice` and `choose`.
- A naming verb: `accept_name`.
- Recovery: `end_run`, warping to 4600 first.

---

## 4. Predictions (draft v1: `O2Segment.draft()`)

### 4.1 Top level
```json
{"version": 1,
 "what": "O2: 100@1000 (warp, entrance 102) -> 101 -> 102 -> 103 -> 104 -> 103 -> 105 -> 106 -> 115 -> 116 -> Field(61), stock vs the alxt zone's verbatim fork (PLAN.md, O2)",
 "rehearsals": [],
 "order": ["S","F","S","F","S","F"], "min_covered": 2, "rerun": {"max": 2},
 "budget": {"run_s": 1800, "run_min_s": 1200, "session_s": 14400, "settle_s": 1.0},
 "start": {"S": 100, "F": 31220}, "entrance": 102, "scenario": 1000,
 "end_field": 61, "end_fields": [61], "route": [100,101,102,103,104,105,106,115,116],
 "stock_fields": [100,101,102,103,104,105,106,115,116,61],
 "members": {"31220": 100, "...": "...", "31237": 117}, "names": {"31220": "O2_AT_MSA", "...": "..."},
 "text_block": 33, "recovery": 4600,
 "cut_start": true,
 "start_first": {"donor": 100, "m": 1, "src": "eb", "sid": 0, "tag": 0, "ip": 30, "off": 16,
                 "target": "Global.Bit[191]", "value": 0, "what": "100's Main_Init: its first store"},
 "start_residue_bytes": [0, 1, 2, 3],
 "ladder": ["4.2"], "sc_writes": 6, "sc_order": true,
 "chain": ["4.3"], "writes": ["4.4"], "start_dependent": ["4.5"], "noise": ["4.6"], "forbidden": ["4.7"],
 "regions": {"2.5": "..."}, "table": ["2.4"], "choices": ["2.6"],
 "naming": [{"donor": 116, "sc": 1155, "beat": "named"}],
 "beats": ["booth","ticket","fake","alright","clear","understand","named","climbed"],
 "steps_default": {"attempts": 2, "interrupts": 1, "timeout_s": 20, "confirm_s": 4.0, "npcs": true,
                   "overlay_ok": false, "immediate": false, "settle": null, "lunge_ticks": 0,
                   "climb": {"burst_frames": 30, "max_bursts": 80, "stall_bursts": 3}}}
```

The member names, from `campaign.toml`, are:

| Member | Donor | Name | Member | Donor | Name |
|---|---|---|---|---|---|
| 31220 | 100 | O2_AT_MSA | 31229 | 109 | O2_AT_WPN |
| 31221 | 101 | O2_AT_MSB | 31230 | 110 | O2_AT_MGC |
| 31222 | 102 | O2_AT_MSC | 31231 | 111 | O2_AT_INN |
| 31223 | 103 | O2_AT_CNT_N | 31232 | 112 | O2_AT_SLN |
| 31224 | 104 | O2_AT_CNT | 31233 | 113 | O2_AT_HOM |
| 31225 | 105 | O2_AT_BST | 31234 | 114 | O2_AT_HOM_A |
| 31226 | 106 | O2_AT_TSS | 31235 | 115 | O2_AT_SIN |
| 31227 | 107 | O2_AT_GAT | 31236 | 116 | O2_AT_ROF |
| 31228 | 108 | O2_AT_ITM | 31237 | 117 | O2_AT_STH |

A key has O1's shape: `{"donor", "m": 1, "src": "eb", "sid", "tag", "ip", "off", "target", "value", "what"}`, plus an
optional `"op"` for O2-KEYS' statement check (section 6). `ip` is the trace's entry-relative ip and `off` the offset
inside the function, both from the reconciler's listing (`e.. t.. ip.. L..`). The draft hard-codes them, as O1 did, and
O2-KEYS re-derives each by joining a synthetic row against the stock bytes.

### 4.2 The SC ladder (`Global.UInt16[0]`; O2-LADDER)
| # | donor | sid | tag | ip | off | value | when |
|---|---|---|---|---|---|---|---|
| 1 | 104 | 7 | 1 | 1046 | 546 | 1150 | Stage 4, about 20 frames after 254 "Nooooo!" opens. Guard ip964. |
| 2 | 105 | 3 | 1 | 511 | 362 | 1151 | Stage 4, after choice 305 and 308/309. |
| 3 | 105 | 14 | 1 | 2818 | 2274 | 1152 | Stage 14, before EnableMove ip2859. |
| 4 | 106 | 2 | 1 | 312 | 221 | 1153 | Puck at (800,1800) and the player within 1400 (ip210). |
| 5 | 115 | 1 | 1 | 462 | 244 | 1154 | Stage 1, after 353. |
| 6 | 115 | 1 | 1 | 1683 | 1465 | 1155 | Stage 9, after 383. |

The rungs must appear in this order. Each row's `old` is the previous rung; the first is 1000, the warp's scenario.
There is no other SC `w` row. Besides these six, the only SC stores in 100-106, 115, 116 and 61 are the debug
overwrites (e.g. 105 e3 t1 ip497, "Error Set Scenario Counter"), each behind `SC > value`, which is false on the
route.

### 4.3 The FieldEntrance chain (`Global.Int16[2]`; O2-CHAIN, in order; the first `old` is 102, the warp's entrance)
| # | donor | sid | tag | ip | off | value |
|---|---|---|---|---|---|---|
| 1 | 100 | 15 | 2 | 255 | 225 | 200 |
| 2 | 101 | 0 | 0 | 291 | 281 | 202 |
| 3 | 101 | 16 | 2 | 255 | 225 | 201 |
| 4 | 102 | 8 | 2 | 255 | 225 | 203 |
| 5 | 103 | 30 | 1 | 972 | 257 | 205 |
| 6 | 104 | 2 | 1 | 558 | 547 | 209 |
| 7 | 103 | 22 | 2 | 261 | 231 | 205 |
| 8 | 105 | 11 | 2 | 227 | 197 | 111 |
| 9 | 106 | 14 | 2 | 222 | 192 | 211 |
| 10 | 115 | 0 | 0 | 249 | 235 | 213 |
| 11 | 115 | 1 | 1 | 1951 | 1733 | 0 |
| 12 | 116 | 2 | 1 | 1694 | 1575 | 0 |

The prologues' `Int16[2]:=10000` never fires: `Bit[184]==1` is false on this route.

### 4.4 Registered writes (O2-WRITES: every covered run of BOTH sides writes each one, at its site)
| donor | sid | tag | ip | off | target | value | op |
|---|---|---|---|---|---|---|---|
| 100 | 19 | 1 | 834 | 151 | Byte[8] | 125 | := |
| 100 | 19 | 1 | 981 | 298 | UInt16[21] | 2 | := (party: Vivi only) |
| 100 | 19 | 1 | 1066 | 383 | Byte[303] | 0 | := |
| 100 | 19 | 1 | 1100 | 417 | Byte[303] | 1 | ++ |
| 100 | 19 | 1 | 1497 | 814 | Byte[4] | 0 | := |
| 100 | 19 | 1 | 1531 | 848 | UInt16[19] | 2 | \|= 2 (START-DEPENDENT, 4.5) |
| 100 | 19 | 1 | 1562 | 879 | Byte[4] | 0 | := |
| 100 | 19 | 1 | 1570 | 887 | Byte[17] | 0 | := |
| 100 | 19 | 1 | 1578 | 895 | Byte[18] | 1 | := |
| 100 | 1 | 18 | 579 | 143 | Bit[3718] | 1 | := (the Rat Kid) |
| 101 | 7 | 1 | 319 | 152 | Bit[3717] | 1 | := (the Herald) |
| 103 | 0 | 0 | 367 | 357 | Byte[8] | 125 | := (both visits: one key) |
| 103 | 18 | 1 | 218 | 15 | Byte[472] | 1 | := (Hippaul, first visit) |
| 104 | 7 | 0 | 313 | 299 | Int16[469] | 1042 | := |
| 104 | 7 | 0 | 333 | 319 | Int16[469] | 1043 | \|= 1 (SC < 1150) |
| 104 | 7 | 1 | 613 | 113 | Int16[469] | 1042 | &= 8190 (the ticket pick) |
| 104 | 7 | 1 | 955 | 455 | Byte[472] | 4 | := (guard < 4) |
| 103 | 22 | 2 | 205 | 175 | Byte[13] | 3 | := (the exit's music write) |
| 103 | 22 | 2 | 244 | 214 | Byte[14] | 3 | := |
| 106 | 5 | 0 | 109 | 91 | Bit[3712] | 0 | := (Ilia's init) |
| 106 | 14 | 2 | 194 | 164 | Byte[13] | 3 | := |
| 115 | 0 | 0 | 467 | 453 | Byte[8] | 125 | := |
| 116 | 0 | 0 | 335 | 321 | Byte[8] | 125 | := |
| 116 | 2 | 1 | 765 | 646 | Byte[6] | 2 | \|= 2 (after `Menu(1,1)`; START-DEPENDENT, 4.5) |
| 116 | 2 | 1 | 1469 | 1350 | Byte[8] | 0 | := |
| 116 | 2 | 1 | 1666 | 1547 | Byte[13] | 3 | := |

Every target is `Global.<width>[<index>]`: a bit's index is the bit, any other width's is the first byte.

Not registered here are the ambient prologues: `Bit[191]`, `Bit[184]`, `Int16[9]`, `Byte[13]:=1`, `Int16[11]`,
`Byte[14]` and the tails (o2_route.md's table). They are deterministic, and O2-NULL compares them key for key.
`start_first` pins 100's first one.

### 4.5 Start-dependent keys
These are compared stock against fork like any key; both sides start alike. They are declared so that no reader takes
O2's value for the value a real O1 -> O2 play writes:
```json
[{"donor": 100, "sid": 19, "tag": 1, "ip": 1531, "off": 848, "target": "Global.UInt16[19]", "value": 2,
  "after_o1": 1799, "why": "UInt16[19] |= 2 on New Game's 0; after O1 it holds 1797 (bits 1, 4, 256, 512, 1024)"},
 {"donor": 116, "sid": 2, "tag": 1, "ip": 765, "off": 646, "target": "Global.Byte[6]", "value": 2,
  "after_o1": 3, "why": "Byte[6] |= 2 on New Game's 0; after O1 it holds 1 (50 e17 ip3240)"}]
```
Both are also rows of 4.4 at these values, so O2-WRITES and O2-NULL judge them. The report prints them with
`after_o1`.

### 4.6 Noise: the minimal set, one key
```json
[{"donor": 103, "m": 1, "src": "eb", "sid": 18, "tag": 1, "off": 51, "target": "Global.Byte[472]", "value": 2,
  "why": "Hippaul's :=2 (103 e18 t1 ip254) runs only if his three legs at speed 15 (about 6600u) end before 103 unloads; 104 writes :=4 either way (e7 t1 ip955, guard < 4), so it never propagates"}]
```
`key_matches(k, p)` is true when every field `p` names equals `k`'s. `is_noise` also keeps O1's
`{not_m, target}` form (`k.m != p["not_m"] and k.target == p["target"]`), so O1's v4 reads as before.

What is deliberately NOT noise:
- **Ilia's `Bit[3712]:=1`** (106 e5 t1 ip165) waits WHILE z < 2200, armed only after Puck's ip520. The route never
  walks back north, so it never fires (the critic). Registering it would hide a real walk or fork divergence.
- **Jack, the hot-spots, Kupo and 104's info options** are forbidden (4.7): a run with one is VOID, never "unstable".
- **Nothing else on the route is random or timing-bound** (research nondeterminism 1-8). The rehearsals' traces are the
  test (7.3 F6): a key that differs between stock rehearsals and is not registered stops the freeze until it is
  explained at the byte level.

### 4.7 Forbidden (a covered run may carry none; the driver scans live, V12, and the analysis again)
```json
[{"donor": 105, "sid": 7, "tag": 2, "why": "Alleyway Jack's contact ran (mugging or the card tutorial)"},
 {"target": "Global.Bit[3714]", "why": "Jack's card branch (105 e7 t2 ip729)"},
 {"target": "Global.Bit[3715]", "why": "Jack's mugging branch (105 e7 t2 ip945)"},
 {"target": "Global.Int16[220]", "why": "a hot-spot pickup: a stray Confirm"},
 {"target": "Global.Int16[222]", "why": "a hot-spot pickup: a stray Confirm"},
 {"target": "Global.Int16[224]", "why": "a hot-spot pickup: a stray Confirm"},
 {"target": "Global.Int16[228]", "why": "a hot-spot pickup (the player's pickup function)"},
 {"target": "Global.Byte[226]", "why": "a hot-spot pickup (the player's pickup function)"},
 {"donor": 115, "sid": 2, "tag": 3, "why": "Kupo's talk (Mognet/save/shop): a stray Confirm"},
 {"donor": 104, "sid": 7, "tag": 1, "target": "Global.Int16[469]", "off_range": [146, 363],
  "why": "a 104 info option was chosen (e7 t1 ip646-863)"},
 {"donor_not_in": [100,101,102,103,104,105,106,115,116], "why": "a write in a field off the route"}]
```
The analysis matches the patterns against the digest's keys. `off_range` needs a join, so the live scan skips that one
pattern: the live scan matches raw rows (`don`, `sid`, `tag`, `target`, `new`).

### 4.8 Coverage beats
The beats are the driver's own required actions, never the game's reactions:

| Beat | Set when |
|---|---|
| booth | rule 1 answered |
| ticket | rule 2 answered |
| fake | rule 3 answered |
| alright | rule 4 answered |
| clear | rule 5 answered |
| understand | rule 6 answered |
| named | 116's naming screen accepted |
| climbed | the climb ended `until` |

Plus `end == "reached"`. The Rat Kid's bump and Puck's SC 1153 are NOT beats. A fork that never bumps, or never writes
1153, must show in the trace (O2-WRITES, O2-NULL, O2-LADDER) or as a VOID with its reason (V8), never as a quietly
uncovered run.

### 4.9 Budget and recovery
O1 ran about 3.5 minutes and was budgeted 720 s. O2 is roughly 3x longer. It has:
- 10 field visits and mbg101;
- about 70 pages and 6 choices;
- the naming screen and the climb;
- about 53,000u of walking.

The estimate is 8-12 minutes a run. The draft budget is `run_s 1800`, `run_min_s 1200`, `session_s 14400` (6 runs + 2
re-runs at about 15 minutes, with slack) and `settle_s 1.0`. Freeze item F7 replaces them from the rehearsal timings.
Recovery is `end_run`: warp to 4600 first, then the soft reset; freeze item F8 proves it from 61. `recovery: 4600`,
and P-RECOVERY checks that it is registered.

---

## 5. Checks (O2's analysis)

### 5.1 Reading a run: the COVERED rule
A run is covered when all of O1's reasons are absent (o1:630-656):
- skipped;
- the install changed;
- the drive did not reach the end;
- a beat not done;
- no trace, or a trace unreadable or incomplete.

O2 adds two reasons:
- **No start.** The front cut found no row in the start field: "never reached the start field".
- **A forbidden key** in the digest's keys: "walk divergence: <why> (<key>)", one per hit.

### 5.2 The cuts
- **`cut_at_end(rows, end_fields)`** is O1's rule, in donor places. Kept: every row before the first `w`/`r` row whose
  `don` is an end place, plus every `e` row, plus every `c` row whose site is outside the end places.
- **`cut_at_start(rows, start_fields)`** is new. `at` is the first `w` or `r` row whose `don` is the start donor (100).
  Rows before `at`, except `e` rows, are removed and returned as `pre`. So are the `c` rows whose `fld` appears only
  among the removed rows (field 70's). It returns `(kept, at, pre)`. Without `cut_start`, nothing is cut: O1 is
  unchanged.

### 5.3 The checks, in order
- **O2-FROZEN:** the predictions sha is the session's.
- **O2-COVER:** at least 2 covered runs a side. Too few makes every check below VOID ("too few covered runs"), as in
  O1.
- **O2-START:** every covered run starts at the start field's Main_Init, after only the warp's own residue.
  - (a) `pre` holds only `r` rows on `start_residue_bytes`: the debug warp writes SC 1000 into bytes 0-1 and FieldEntrance
    102 into byte 2 (rung 1's calibration);
  - (b) the first `w` row after the cut is `start_first` (don 100, e0 t0 ip30, `Bit[191]`, new 0).
- **O2-LADDER:** every covered run writes the six SC rungs at their stores, in order, and SC nowhere else. Each ladder
  WriteKey is in the digest's keys, AND the run's field `w` rows on `Global.UInt16[0]` are exactly
  `[(don, sid, tag, ip, new)]` of 4.2 in line order, with each `old` the previous rung (1000 first).
- **O2-CHAIN:** every covered run writes the twelve FieldEntrance stores in order, and Int16[2] nowhere else. It is the
  same test on `Global.Int16[2]` with 4.3 (first `old` 102).
- **O2-WRITES:** every covered run of both sides writes every registered story key: each 4.4 key is in every covered
  run's digest keys.
- **O2-NULL:** STOCK ONLY and FORK ONLY are empty outside the registered noise. `T.compare(S, F, members)`, with the
  noise set aside by `is_noise`.
- **O2-STABLE:** no key outside the registered noise is written in some runs of a side and not others.
- **O2-JOIN:** every script row joins a store in the bytes its field ran.
- **O2-THROW:** nothing is thrown through EventEngine, EBin, StoryTrace or HarnessAgent (O1's rule, in `run`).

**VERDICT:** `PROVEN`, `NOT PROVEN: <failed checks>` or `VOID: <void checks>`. This is O1's `verdict()`.

**Report-only,** after O1's body, with its title line, per-run lines and `T.report`:
- the start-dependent keys, with their values on both sides and `after_o1`;
- the SC timeline per covered run: the frame of each rung, and the deltas;
- the steps table per run: cell, step, attempts, interrupts, seconds, lunge and climb records;
- forbidden hits per VOID run;
- the dialogue per covered fork run against the first covered stock run, with `timed` pages removed and consecutive
  duplicates collapsed. This is O1's lesson: self-closing windows stack and are sampled at varying moments.

---

## 6. Offline check and preflight

### 6.1 `--offline-check` (reads the install and the build; writes nothing; must be green before any rehearsal ends in a freeze)
- **O2-BUILD:** every member's `.eb`, in all 7 languages, is `remap_fields(stock donor .eb in that language, retarget)`
  (`Segment.build_check`, `accept_us_build=False`). Measured today: 126/126.
- **O2-TEXT:** the build's `field/33.mes`, per language, is byte-equal to
  `dialogue.extract_field_mes("100", lang).encode("utf-8")`. Measured today: 7/7.
- **O2-KEYS:** every key of `ladder`, `chain`, `writes`, `start_dependent`, `noise` and `start_first`, plus the two
  concrete forbidden sites (105 e7 t2 ip729 off 175 `Bit[3714]`; ip945 off 391 `Bit[3715]`), is a store of its variable
  at `(sid, tag, ip)` with rel == `off`. This is O1's `keys_check`: build a `T.Row` and `ScriptIndex.join`, with
  `status == "store"`. With `op` given, the statement's text at `off` (`ScriptIndex.text_at`) also carries it:
  `const(<value>) B_LET` for `:=`, `const(<c>) B_OR_LET` / `B_AND_LET` for `|=`/`&=`, `B_POST_PLUS` for `++`.
- **O2-REGIONS:** every frozen region's points equal the first `SetRegion` of `(donor, entry)` in the stock bytes
  (`eventscan._region_points`, or a public `scan_regions` if the implementer adds one). Each role holds:
  - `exit`: `scan_gateways` has a row for that entry with `to` and the entrance, and `face_gate` as frozen;
  - `dormant` (115.e14): no `InitRegion(14)` on Main_Init's path for entrances 213-215;
  - `walkin` (105.e12): its tag 2 opens with the `1150 <= SC < 1152` guard.
- **O2-GOALS:** for every table step, on `PlayerWalkmesh(stock_walkmesh(donor), closed=...)`:
  - the goal is on the floor, with `distance_to_boundary >= 80`;
  - a `target` step's goal is inside the target (`doorface.region_contains`) with depth >= 80; an `until` step's goal
    satisfies its predicate;
  - `pathfind.route_avoiding(start, goal, polys(avoid), leave_wall=True)` exists.

  Section 2.4's numbers are today's run of exactly this.

### 6.2 `--preflight` (the live install, read-only; red until the owner-gated deploy, which is expected)
- **P-MANIFEST:** `o2_forks.json` members == the predictions', `deployed: true`.
- **P-DEPLOY:** each member is registered once under its name, and has one ForkDonorPatch row to its donor.
- **P-EB:** each member's live `.eb` in 7 languages equals the build's.
- **P-FLOOR:** each member's deployed walkmesh is its donor's.
- **P-STOCK:** no mod folder overrides stock 100-106, 115, 116 or 61.
- **P-TEXT (new):** every mod folder's `FF9_Data/embeddedasset/text/<lang>/field/33.mes`, where present, is byte-equal to
  the stock block 33 of that language. Present is expected in FF9CustomMap after the deploy.
- **P-RECOVERY (new):** 4600 is registered in some mod folder.
- **In game only** (`capabilities`): P-CAP (storytrace proto 1) and P-OBJECTS (`objects_status != "cannot"`: s89,
  needed for `npcs` and V6).

### 6.3 The fingerprint (per run, before and after, as O1)
O1's keys, plus:
- `"override70"`: `{folder: sha of field 70's .eb, us}` for every folder that ships one. Today that is
  FF9CustomMap-world's New-Game override.
- `"text33"`: `{folder: {lang: sha}}` of every `field/33.mes`.

Another session re-wiring New Game, or touching block 33, mid-session makes the runs VOID; it can never skew them.

### 6.4 `o2_forks.json` (the implementer writes it; the lead flips `deployed` after the owner-gated deploy)
It mirrors `o1_forks.json`:
- `what`;
- `import`: the command in 0.1, `--mod-folder FF9CustomMap --out C:/gd/_ns_playtest/o2/fork`;
- `build`: `py -m ff9mapkit build-all C:/gd/_ns_playtest/o2/fork/campaign.toml --out C:/gd/_ns_playtest/o2/build`;
- `deploy`: one member at a time, in id order, `tools/deploy_field.py <member>.field.toml --id <fork id> --name <name>
  --mod-folder FF9CustomMap`;
- `members` and `names` (4.1);
- `text_block: 33`, `deployed: false`, `relaunch_needed: true` (18 FieldScene ids and 18 ForkDonorPatch rows);
- `revert`: newest first, 31237 down to 31220. The first deploy writes block 33 fresh (its revert deletes it); later
  deploys back it up.
- `verified: null`.

---

## 7. Rehearsal plan (stock only, no deploy; the lead runs these in game before freezing)

### 7.1 The scenario
`o2_rehearse.py` exposes `run(g, field=None)`. `tools/play.py --field N` selects one stage; no `--field` runs every stage
in one launch, cheapest first. Each stage runs this sequence:
1. New Game; `wait_frames(30)`;
2. `storytrace(True)`: the rehearsal traces too, which is free ground truth;
3. raw `warp <field> <entrance> <sc>` and wait for the field;
4. `segment_drive.drive(g, O2.draft(), "S", log, end_fields=[stage end], observe=recorder, forbid_live=True)`;
5. collect the trace to `rh_<stage>_<n>.jsonl`;
6. write the record into `o2_rehearsal.json`;
7. `end_run`.

The command is `py tools/play.py studies/story-trace/o2_rehearse.py --field 115 --label o2-rh-115 --timeout 240`.

| Stage | Warp | Ends in | Runs | What it settles |
|---|---|---|---|---|
| R-115 | `warp 115 215 1155` (Main_Init rewrites the entrance to 215 at ip287: stage 10 with control, spawn (257,-2500)) | 116 | 3 | Does `hold up` reach B_KEY(16)? The climb: y per burst, frames to the top. |
| R-105 | `warp 105 205 1150` | 106 | 5 (Jack's legs take SYSVAR[0] offsets) | Jack and the leave-now exit; choices 305/310/314; e12 |
| R-106 | `warp 106 111 1152` | 115 | 2 | The wait point, Puck, SC 1153, the hints, e14 |
| R-116 | `warp 116 0 1155` | 61 | 2 | The three triggers, Puck's pauses, the naming, end_run from 61 |
| R-FULL | `warp 100 102 1000` | 61 | 2 | Everything in sequence, plus mbg101, the Rat Kid, the Herald, 102, the booth and 215's publication, 104 and 251's publication, Hippaul's ip254, the second 103 visit, the total time |
| R-103 (optional) | `warp 103 203 1000` | 105 | 1-2 | A cheaper iteration on the booth, 104 and the second 103 visit |

### 7.2 What every stage records (`observe` plus the driver's own log)
- **Control grants:** `{t, frame, field, sc, x, z, y, fps}`. Every step's `start` in 2.4 is checked against these.
- **Steps:** the 2.3 log rows, including the route records, the lunge (`sample_frame`, `done_frame`, travel) and the
  climb (`ys`, `frames`, `ended`).
- **Choices:** the full published choice (`options`, `active`, `selected` at readiness, `count`), the rule picked and
  the frame. This covers 215's first-character drop and 251's masked lines.
- **Pages:** the text, `raw_texts`, whether timed, and the frame.
- **NPC tracks** (`st.objects`, every sample, in these cells only): 105 sid 7 (Jack) from SC 1152 on; 106 sid 2
  (Puck); 116 sid 2 (Puck). Each sample has uid, sid, x, z, moving, r, range_r, talk_r and the distance to the player.
  The minimum player-to-Jack distance and the latency (control sample -> first held frame -> first position change)
  are summarised.
- **mbg101** (R-FULL): the frame from arrival to the first page, and the published fps before, during and after.
- **The end:** `end_run`'s result from 61 (did it reach the title, and how).
- **The trace:** `trace_summary`, i.e. the SC sequence, the Int16[2] sequence, each registered key present or absent,
  and every UNREGISTERED key with its site. Hippaul's ip254 is present or absent, Ilia's ip165 present or absent (it
  must be absent), and the JOIN failures must be 0.

`py studies/story-trace/o2_alexandria.py --rehearsal-report <run dir>` prints all of it, per stage and per run.

### 7.3 The freeze checklist (each item needs its evidence before `--freeze`; record the run dirs in `rehearsals`)
- **F1.** `hold up` climbs: y falls on every burst, and the top is reached in every R-115 run and in R-FULL. If it does
  not, STOP: the agent's input path (IsHeld -> B_KEY) needs a fix, and O2 cannot run.
- **F2.** Jack: every R-105 run leaves 105 with no e7 t2 row, and a minimum distance above his `range_r`. Set
  `lunge_ticks` from the measured latency: 0 if `route_cross(settle=0)` alone moves him within 0.5 s of control.
  Otherwise keep 10, or size it to the clear segment.
- **F3.** 106: SC 1153 arrives while he waits at (550,2000), and `wait_s` is 3x the slowest wait seen.
- **F4.** Every step is done within its attempts. Any goal a run missed moves, re-checked by O2-GOALS.
- **F5.** Every choice publishes a line the rule matches, with `selected` equal to the pick at readiness. This includes
  104's masked 251 (active [0, 1, 4, 10]).
- **F6.** The traces: the ladder, the chain and every 4.4 key exactly as drafted, in every stage that covers them. Any
  key present in some stock rehearsals and absent in others is either Hippaul's ip254 or is explained at the byte level
  before the freeze (a new noise entry only with that explanation).
- **F7.** Budget: `run_s` = 2x the slowest R-FULL, `run_min_s` = 1.25x the median, `session_s` = 8x the median plus
  1800.
- **F8.** `end_run` from 61 reaches the title.
- **F9.** R-FULL's first rows after the arm are the warp's residue on bytes 0-2 (at most 3), then 100 e0 t0 ip30
  `Bit[191]:=0`. Any other pre-start row stops the freeze.
- **F10.** The control-grant positions of 2.4 are confirmed (or corrected), especially (115, 1155) stage 10 and 116's
  three grants.

After the freeze comes the owner-gated deploy of the 18 members, the relaunch, `--preflight` green, then the session:
`py tools/play.py studies/story-trace/o2_alexandria.py --label story-o2 --timeout 240`.

---

## 8. The dry run (`o2_dryrun.py`: synthetic sessions through `O2.analyse`)

It is built like `o1_dryrun.py`.
- **Real store sites.** The rows are real store sites of the stock bytes: 4.2-4.4, `start_first`, 61 e0 t0 ip22
  `Bit[191]:=0` (off 16) as the end row, and 105 e7 t2 ip945 for Jack. Every row joins.
- **The fork side.** Rows are shifted onto member ids (`fld` = member, `don` = donor).
- **Scripts.** `scripts/<member>.eb` = `remap_fields(stock(donor), retarget)` for all 18.
- **A base run** is: `arm` (fld 70); residue rows in fld 70 on bytes 0 (0 -> 232), 1 (0 -> 3) and 2 (0 -> 102);
  `start_first`; 100's `Bit[184]:=0` (e0 t0 ip57, off 43); the route's registered rows in route order; the 61 row;
  `off` (fld 61).
- **A log** carries `outcome.pages` and `timed`, and the beats.

| Case | Want |
|---|---|
| null-pair | PROVEN |
| fork-drops-SC1153 | NOT PROVEN (LADDER F, NULL F) |
| SC-out-of-order (1151's row before 1150's, both sides) | NOT PROVEN (LADDER F; NULL P: keys are sets) |
| SC-seventh-write (a debug-overwrite site, e.g. 105 e3 t1 ip497, both sides) | NOT PROVEN (LADDER F) |
| SC-old-not-1000 (the first rung's `old` 0) | NOT PROVEN (LADDER F) |
| chain-out-of-order (rows 6 and 7 swapped) | NOT PROVEN (CHAIN F) |
| chain-extra (215 answered twice: 103 e30 t1 ip972 twice, stock only) | NOT PROVEN (CHAIN F) |
| fork-extra-key / stock-extra-key (a real store off the route: 100 e0 t0 ip105 `Byte[13]:=9`, L91, the ambient-9 branch) | NOT PROVEN (NULL F; LADDER, CHAIN P) |
| writes-missing (no `Bit[3717]` on either side) | NOT PROVEN (WRITES F; NULL P) |
| unstable-outside-noise (Ilia's 106 e5 t1 ip165 `Bit[3712]:=1` in one stock run) | NOT PROVEN (STABLE F) |
| hippaul-noise-only (Byte[472]:=2 in two F runs and one S run) | PROVEN (NULL P, STABLE P) |
| start-dependent-equal (UInt16[19]=2, Byte[6]=2 on both sides) | PROVEN, and the report lists both with `after_o1` |
| start-dependent-differs (the fork writes UInt16[19]=1799) | NOT PROVEN (NULL F, WRITES F) |
| front-cut-residue (fld-70 residue only before the start) | PROVEN (START P) |
| front-cut-write (a `w` row in fld 70 before the start, fork only) | NOT PROVEN (START F; NULL P: cut) |
| start-first-missing (100's `Bit[191]:=0` ip30 row dropped on both sides, so the first `w` row in 100 is ip57's `Bit[184]:=0`) | NOT PROVEN (START F; NULL P) |
| end-cut (rows in 61 past the end, stock only) | PROVEN |
| jack-one (one F run carries 105 e7 t2 ip945 `Bit[3715]:=1`) | PROVEN, with F 2 of 3 covered and that run VOID "walk divergence" |
| jack-two (two F runs carry it) | VOID (COVER V) |
| hotspot-stray (one S run carries 103 e20 t1 `Int16[220]`) | that run VOID |
| off-route (a run with rows in donor 112) | that run VOID |
| beat-missing (`climbed` False in two S runs) | VOID (COVER V) |
| no-start-row (a run whose trace never reaches 100) | that run VOID |
| trace-without-off | VOID |
| install-changed | VOID |
| join-failure (a row one byte off a real store) | NOT PROVEN (JOIN F) |
| predictions-changed | NOT PROVEN (FROZEN F) |

It prints O1's style of summary line and "N/N cases as registered", and exits 1 on any miss.

---

## 9. Build order, tests, commits (the implementer; no deploy, no game, no full suite)

Run these from `ff9mapkit/` unless noted.

1. **`segment_drive.RouteVoid` and `pick_for`**, extended per 1.4. `o1_opening` imports and re-exports them.
   - Test: `test_o2_pick_for_scopes_rules_by_sc_and_once`, plus the whole O1 set.
   - Commit after `pytest -k "o1_ or pick_for"` is green.
2. **`segment_trace.Segment`**, with `o1_opening` rewritten as `O1Segment` plus wrappers (1.2, 1.3).
   - Capture `research/o1_regress_baseline.json` at HEAD FIRST.
   - Test: `test_segment_session_loop_on_the_fake`. A stub Segment (preflight, fingerprint and roots stubbed; a drive
     that reaches or VOIDs on cue) runs S F S F S F on the FakeGame. It checks the session record, each run's trace and
     log file, the re-run of a short side, and the finished and report files.
   - Then run `segment_regress.py` (G1-G5), all green. Commit.
3. **H1** plus its tests. Commit.
4. **H4's warp arguments, ladder and region keys, then H2 with its tests.** Commit.
5. **H3** plus its tests. Commit.
6. **H5** (kit) plus its test in `tests/test_route_avoiding.py`. Commit.
7. **`segment_drive.drive`**, the step executors and the FakeGame tests below. Commit.
8. **`o2_alexandria.py`** (draft, O2 checks, offline, preflight, CLI) and `o2_forks.json`.
   `py studies/story-trace/o2_alexandria.py --offline-check`, from the worktree root, must be 5/5 PASS (O2-BUILD,
   O2-TEXT, O2-KEYS, O2-REGIONS, O2-GOALS). `--preflight` is expected red, since nothing is deployed. Add the
   `.gitattributes` line. Commit.
9. **`o2_dryrun.py`**: all cases as registered. Commit.
10. **`o2_rehearse.py`** plus `--rehearsal-report`. Test: `test_o2_rehearse_plumbing_on_the_fake`, one stage on a fake
    two-field route, where the record file has every section. Commit.
11. **The O2 section in `PLAN.md`**: the design in brief, "draft: rehearsals pending, freeze pending". Commit.

**Driver tests** (FakeGame; fields 30810, 30820 and 30821 from the fixture):
- `test_o2_drive_walks_its_table_to_the_end`: a confirm step opens a default-take choice; the answer warps into a scene
  field; a wait_sc step is released by a director setting `scenario`; a cross with `handoff` lands in the end field.
  The beats, choices and steps logs are as expected, and no `up`/`down` press is executed.
- `test_o2_drive_climbs_after_the_ladder_confirm`: H2 through the driver; beat `climbed`.
- `test_o2_drive_leaves_at_once`: an `immediate` leave_now. The first hold comes within 0.2 s of wall time of the
  control grant; the same cell without `immediate` waits at least `settle_s`. A walking "Jack" object never reaches him.
- `test_o2_drive_counts_steps_per_visit`: three `until` triggers in one cell, each taken by a director at its
  threshold.
- `test_o2_drive_voids_control_without_a_cell`: V4.
- `test_o2_drive_voids_a_once_choice_asked_again`: V2, plus an SC-scoped rule at the wrong SC (V1).
- `test_o2_drive_voids_when_the_default_is_not_the_pick`: V3; the cursor is left alone.
- `test_o2_drive_voids_a_page_in_a_no_pages_cell`: V5; no Confirm is executed.
- `test_o2_drive_voids_a_watched_object_in_reach`: V6.
- `test_o2_drive_voids_leaving_the_route`: V11.
- `test_o2_drive_voids_on_a_live_forbidden_row`: V12, through `fake.script_store`.

**The test command:**
`py -m pytest tests/test_harness.py -q -p no:cacheprovider -W ignore -k "o1_ or o2_ or segment or climb or lunge or
handoff or overlay or fake_warp"`. Also run `py -m pytest tests/test_route_avoiding.py -q -p no:cacheprovider -W ignore`
for H5. The study scripts run from the worktree root: `o1_dryrun.py`, `o2_dryrun.py`, `segment_regress.py` and
`o2_alexandria.py --offline-check`.

---

## 10. Open risks (what only the game can settle)
- **The climb** (F1). The input path was read, never run. If `hold up` does not reach B_KEY(16), O2 stops before any
  session: an agent patch is the owner's call.
- **Jack's timing** (F2). This design gives him about 1.9-2.7 s from control to his pass near the lookout. The runs
  prove it; V6 and V12 keep a lost race out of the verdict.
- **mbg101 sets the target FPS while it plays.** The tick clock re-measures, but the page and choice waits planned in
  ticks must not run during a rate flip; the rehearsal records the flip.
- **Kupo near the ladder at stage 10.** A Confirm could reach his talk instead of the ladder. The plan keeps Vivi out
  of his talk disc and the ladder point is about 890u from him, but only the rehearsal proves it; a talk would show as
  a V1 choice.
- **116's narrow walks** (wall gaps 74-137 along the line) with Puck pausing on it. `npcs` waits behind him; the
  rehearsal proves the pace.
- **The facing for tag-3 Confirms** (the booth, the ladder). O1's candle took a plain Confirm; these are assumed to as
  well, and are proven in the rehearsal (F4).
- **61's FMV003 under `end_run`'s warp** (F8). O1's warp left 100 mid-MBG; a type-0 FMV is untested.
