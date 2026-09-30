# O2 -- Alexandria under the trace: the design

**Status: DESIGN, offline, REVISED once.** Nothing is deployed, launched or frozen. The inputs are `o2_route.md` and
`o2_research.json` in this folder: the reconciled route, with the completeness critic's corrections overriding the
route where the two conflict. This file folds both into code-level decisions, and adds what a re-check of the stock
bytes and walkmeshes found (section 0.2). Every number below was read with the kit, read-only, from the stock US `.eb`
files, the reconciler's listings (`<scratchpad>/o2_research/reconcile/L<fid>.txt`), the stock walkmeshes as the player
walks them (`pathfind.PlayerWalkmesh`) and the live Memoria source. The offline check (section 6) re-derives every one
of them.

**The revision** (this file's second commit) folds in two critiques of the first version (9d0e7780): the
driver-robustness critique (6 items, 2 of them blockers) and the claim-integrity critique (14 items), and the lead's
ruling on the uk text mis-pick. Each item was re-verified in the bytes, the engine source or the walkmesh before it was folded in. Section 11
is the critique log: every item, what was checked, adopted or rejected, and why. Section 9 is the build order in three
parts, each with its required-green list.

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
- **The uk text (the lead's ruling on claim-integrity #1).** The kit's text carry hands uk the US block (0.2 #2). The
  KIT fix is NOT made on this branch: it touches the verbatim fork's text carry, needs the full suite, and already
  affects live blocks 2, 187 and 276, so the lead makes it on its own branch. Here:
  - O2-TEXT (offline) and P-TEXT (live) compare each language against the asset read through the engine's own
    ResourceManager path (`embeddedasset/text/<lang>/field/33.mes`), never through `extract_field_mes`;
  - P-LANG proves the session runs US, and the language is in the fingerprint;
  - a mismatch is a hard FAIL for the session language (us). For any other language, a mismatch whose shipped file is
    byte-equal to ANOTHER language's stock asset is a named, counted KNOWN-KIT-DEFECT line; any other mismatch is a hard
    FAIL. With today's build O2-TEXT reports the uk mismatch visibly. Once the kit fix lands and the build is
    regenerated, it reads clean in all 7 languages with no code change here (6.1).

### 0.2 Found while designing (each verified offline, read-only)
1. **The build is the own-language remap, all 126 files.** Every member's `.eb`, in all 7 languages, equals
   `remap_fields(the donor's stock .eb IN THAT LANGUAGE, donor -> member)`, with 0 US fallbacks. Member(116) = 31236's
   only `Field()` target is real 61. So O2-BUILD accepts the own-language generation only; O1 accepted either.
2. **The build ships text block 33 into FF9CustomMap, and its uk file is the US text.** It writes
   `FF9_Data/embeddedasset/text/<lang>/field/33.mes` in 7 languages. Read the way the engine reads it -- the
   ResourceManager's `m_Container` path `embeddedasset/text/<lang>/field/33.mes` in `mainData`, resolved into
   `resources.assets`, as `battle.extract._read_battle_text` already does for battle text -- six are byte-equal to their
   stock asset, and uk is not:

   | | sha256 (first 10) | chars |
   |---|---|---|
   | stock us | 4751874951 | 42868 |
   | stock uk | 8c94536b6c | 42896 |
   | build uk | 4751874951 (= stock us) | 42868 |

   The cause is `dialogue._lang_score`: `_LANG_ALIAS` gives us and uk one English stopword set (dialogue.py:374), the
   two English copies tie at 826, and `extract_field_mes` / `extract_field_mes_all_langs` hand uk the same pick as us.
   The first version of this design measured "7/7 byte-equal" against `extract_field_mes` itself, which is a check of
   the tool against itself. The same mis-pick is live today in FF9CustomMap's blocks 2, 187 and 276 (each ships uk =
   stock us; stock uk differs), which is the lead's to report.

   Once deployed, the STOCK side reads this file too, since block 33 is 100-117's own. With the session in US (P-LANG),
   that is stock US bytes. Hence O2-TEXT offline, P-TEXT live, and the KNOWN-KIT-DEFECT rule of 0.1.
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
   registered `dormant`. Its tag 3 calls 115 e17 t12, a card event (see #9): a write from there is a finding.
6. **Two gated doors sit beside the walked lines.** 101 e17 (-> 112) and 106 e13 (-> 113) carry stock's facing gate
   [48, 208] (`scan_gateways`) and stand on or near the lines walked, so both are always avoided. No O2 TARGET exit is
   gated, so no step passes `gate=` or runs a facing step.
7. **Control points and start spots, from the scripts' own walks.**
   - 105: the lookout (-244,2562) (e14 t1 Walk ip2280; EnableMove ip2859).
   - 116, control #1: (2718,-137) (e21 t1 Walk ip580; EnableMove ip662).
   - 116, control #2: the jump's landing (-339,244) (SetupJump ip877; EnableMove ip958). Triangle 217 is
     (-62,75) (-62,306) (670,305), floor 1; `EnablePathTriangle(217,0)` closes it at ip923, before #2.
   - 115 warped at SC 1155 (entrance 215): the player spawns at (257,-2500) (e17 t0 L197). On the real route (and in
     R-115a, 7.1) stage 10's control comes where stage 5 walked him, about (50,-968) (e17 t1 Walk).
   - 106 Puck (e2) walks (800,2200) -> (800,1800) -> (800,-300) -> (800,-1250) -> (-300,-1300) at speed 60.
8. **Start dependence of gEventGlobal VALUES is exactly two keys.** The route has five value-dependent stores:
   - 100 e19 t1 ip1100 `Byte[303]++` (after `:=0` at ip1066);
   - 104 e7 t0 ip333 `Int16[469] |= 1` and e7 t1 ip613 `&= 8190` (after `:=1042` at ip313);
   - 100 e19 t1 ip1531 `UInt16[19] |= 2`;
   - 116 e2 t1 ip765 `Byte[6] |= 2`.

   Only the last two depend on the start. The warp start writes 2 and 2. After O1 they would write 1799 and 3: O1's
   archived S#3 leaves UInt16[19] at 1797 (50 e17 ip1629/1667, 50 e13 ip1149/1187/1225) and Byte[6] at 1 (50 e17
   ip3240). O1 S#3's end state differs from the warp start at bytes 6, 13, 18, 19-22, 206 and 303. The
   claim-integrity critic found that on the route those bytes are read only by the Byte[13] music branch (both starts
   then write `Byte[13]:=1`), `SetPartyReserve(UInt16[21])` after its `:=2`, Byte[303] after its `:=0`, the UInt16[19]
   bit-1 guard (clear in both starts) and the two `|=` stores. So the claim covers gEventGlobal values only: party data,
   cards (SYSVAR[19] is read in 104 and 115) and field 70's override state are NOT covered by it (4.5).
9. **Hot-spot and pickup scratch are stray-Confirm evidence, and each hit names its hot-spot.** On the route fields,
   `Int16[220]`, `[222]`, `[224]`, `[228]` and `Byte[226]` are written only by three kinds of script:
   - the Confirm hot-spots: 100 e12/e13, 101 e11-e14, 102 e7, 103 e19-e21, 105 e9, 106 e11, 115 e11/e12 and
     116 e17-e19, all tag 1. Each fires on `B_KEYON` Confirm|Special (the press edge) with `SYSVAR[2]==1`, within
     32*sqrt(N) of its own position (`Instance.Int24[0] := ((dx/8)^2 + (dz/8)^2)/16`, then `< N`);
   - the player pickup functions those hot-spots call through `RunScriptSync(2,250,N)`: 100 e19 t16/t17, 101 e19
     t14/t15, 102 e12 t12, 103 e30 t14-t16, 105 e14 t15, 106 e16 t12, 115 e17 t16 and 116 e21 t14 (the first version
     listed only the first five fields: the claim-integrity critique #3);
   - 115 e17 t12, a card event reachable only through the DORMANT 115 e14 t3 (ip103). Besides `Int16[224]` it writes
     `Byte[472]:=4` (ip2150) and `Bit[7202]:=1` (ip2205).

   Every hot-spot writes its OWN position first, `Int16[220] := x` and `Int16[222] := z` as store constants (100 e12 t1
   ip175/ip183 = (-658,4843)), so a trace hit names the hot-spot that fired. They are registered as forbidden (4.7),
   never as noise, and a hit VOIDs a run only when the driver's own log shows a Confirm that could have fired that
   hot-spot. Otherwise it is a finding (4.7). The 17 hot-spots, decoded, are in 2.5. Every control point and confirm
   goal of the table is at least 469u beyond every hot-spot's reach (the nearest: 115 (206,-1911), 469u beyond e12's).
10. **Jack's contact takes control, about 1.5-2.0 s after control comes.** 105 e7 t2 hits DisableMove at ip584 and opens
    its 16-frame "!" window. A press there writes `Bit[3714]:=1` (ip729, L175) and runs `Field(112)`. No press means the
    mugging, with `Bit[3715]:=1` (ip945, L391). His contact radius is his published `range_r` =
    4*(collRad 26 + Vivi's collRad 30) + speed 15 + 60 = 299 (HarnessAgent.cs:2349-2355, the engine's mode-2 search;
    `SetObjectLogicalSize(20,26,30)` 105 e7 t0 ip262, `(20,30,44)` e14 t0 ip146, arg 2 = collRad by
    EventEngine.DoEventCode.cs RADIUS). On his second leg, (440,3700) -> (-250,2800) at 15u a tick, he comes within
    299 of the lookout about 74 ticks after he wakes, at (-206,2858). Control comes 13-29 ticks after the wake, so the
    window is 45-61 ticks: 1.5-2.0 s at FieldTPS 30. (The first version timed his third leg, 85-95 ticks: wrong.)
11. **The O1 baseline holds, and it is deterministic.** At HEAD 9d0e7780:
    - `o1_opening.py --analyse <o1e> --predictions o1_predictions_v4.json` reproduces the archived `o1_report.txt` byte
      for byte (the CLI's `print` adds one trailing newline);
    - the VOID archive o1d (`20260929-212507-story-o1d`, v4) analyses to `VOID: O1-COVER, ...`;
    - the 16 dry-run cases give the same (checks, report) pairs on every run, with no path in them;
    - the v1-v3 archives raise KeyError 'battle_won', so the gate uses the two v4 archives.

    The regression gate (1.6) rests on all four.
12. **Every route exit takes control about 26 ticks before its `Field()`.** Every exit on the route (100 e15, 101 e16,
    102 e8, 103 e22, 105 e11, 106 e14) runs this sequence:
    1. `CalculateExitPosition()`;
    2. `ExitField()` (MOVQ: `usercontrol = 0` at once, EventEngine.DoEventCode.cs:859-869);
    3. `FadeFilter(6,24,...)` and `op_22(25)`;
    4. only then `Int16[2] :=` and `Field()`. For example, 106 e14 t2 runs ExitField at ip50, FadeFilter/op_22 at
       ip134/ip144, and `Int16[2]`/`Field(115)` at ip222/ip230.

    Meanwhile ExitField walks the player to his projection on the region's FIRST edge (MJPOS, :2247-2270) at his actor
    speed. Whether that walk or the fade ends first is a race per exit:
    - 100 e15's walk (about 1170u at 30u a tick, 39 ticks) outlasts the fade;
    - 105 e11's (about 884u at 34, 26 ticks) ties it;
    - 106 e14's first edge is its WEST edge (230-480u at 30, 8-16 ticks), so the walk ends first.

    So the first sample a crossing shows is control gone with the field unchanged, and that is not an interruption
    (2.3). 106 e14 t2 has no CloseWindow (its 40 lines), so a [TIME=45] hint can still be up in that gap. The published
    field id flips only when the map switches (`FF9ChangeMap` sets `nextMapNo`), after `Field()`.
13. **The warp's own writes are residue in field 70: exactly three rows.** The debug warp writes FieldEntrance and
    ScenarioCounter straight into gEventGlobal before the map change (Ff9mkDebugMenu.cs ServicePendingWarp,
    :2129-2135). So s88's residue net emits them as `r` rows in field 70 (rung 1: "seen in field 70 before the load").
    From New Game's zeros, `warp <start> 102 1000` gives exactly three rows:
    - byte 0: 0 -> 232;
    - byte 1: 0 -> 3 (SC 1000 = 0x03E8);
    - byte 2: 0 -> 102 (entrance 102 = 0x0066). Byte 3 does not change.

    O1's `warp 50 0 -1` wrote no residue at all: in o1e run 1 the arm is in field 70 and the first row is in field 50.
    O2-START (5.3) and V12's scan window (2.2) are built on this.

---

## 1. Module layout

### 1.1 Files

| File (in `studies/story-trace/` unless a path is given) | | What it holds |
|---|---|---|
| `segment_regress.py` | new, FIRST | The O1 regression gate (1.6), with `--capture`. It imports only the O1 modules, so its baseline can be captured before any code changes. |
| `research/o1_regress_baseline.json` | new, FIRST | The captured baseline (1.6 G0), LF. |
| `segment_trace.py` | new | The shared engine, as class `Segment`: predictions I/O and freeze, the offline build/keys checks, the preflight skeleton, the install fingerprint, the session loop, recovery, cutting, reading a session, judging, the verdict, the report, and the CLI. Also the pure helpers of 1.2 (strict noise matching, frozen places, cuts, the digest's row keys). |
| `segment_drive.py` | new | `RouteVoid` and `pick_for`, moved from `o1_opening` with backward-compatible extensions. Also the beat-table driver `drive()`, its step executors, its table helpers, the forbidden scan and the backing rule (4.7), which the analysis shares. |
| `o1_opening.py` | refactored, thin | O1's constants, plus `draft_predictions()` and `drive()` with their BODIES UNCHANGED. `O1Segment(Segment)` carries O1's exact strings. Module-level wrappers keep every public name. |
| `o2_alexandria.py` | new | `O2Segment(Segment)`: the draft predictions (beat table, regions, hot-spots, keys), O2's checks and report sections, the offline checks O2-TEXT, O2-REGIONS and O2-GOALS, the preflight extras, P-LANG, and `--rehearsal-report`. |
| `o2_dryrun.py` | new | O2's synthetic sessions (section 8). |
| `o2_rehearse.py` | new | The stock rehearsal scenario for `tools/play.py`; `--field` picks the stage (section 7). |
| `o2_forks.json` | new | The chain manifest, with `deployed: false` and the known text defect (section 6.4). |
| `.gitattributes` | edit | `studies/story-trace/o2_predictions*.json -text` (before any freeze) and `studies/story-trace/research/o1_regress_baseline.json -text` (with the baseline). |
| `tools/harness/session.py` | edit | H1-H3 and H6 (section 3). |
| `tools/harness/artifacts.py` | edit | H6: `StateRing.since(frame)`. |
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
    def capabilities(self, g) -> list                         # o1:489 P-CAP; O2 adds P-OBJECTS and P-LANG
    def start_run(self, g, side, pred) -> tuple               # o1:544-551, returns the story mark (see below)
    def drive(self, g, pred, side, log, *, deadline, progress) -> dict   # subclass
    def end_run(self, g, log) -> None                         # o1:463, recovery=self.recovery
    def run(self, g) -> None                                  # o1:486-604, the whole session loop
    # analysis (offline, pure but for the stock scripts)
    def cut(self, rows, pred, side) -> tuple                  # (kept, start_line, end_line, pre)
    def why_void(self, rec, r, pred) -> list                  # extra VOID reasons, each (reason, class, by) (base: [])
    def read_session(self, run_dir, pred, *, session=None, stock=None) -> list   # o1:618
    def judge(self, runs, pred, *, frozen) -> list            # o1:667: FROZEN, COVER, all_run_checks, then core_checks
    def all_run_checks(self, runs, pred) -> list              # judged over EVERY run, covered or not (base: [])
    def core_checks(self, runs, cov, pred) -> list            # O1: LADDER NULL STABLE JOIN (o1:680-705)
    def report(self, run_dir, session, pred, sha, runs, checks) -> str   # o1:731-752 + report_extra()
    def analyse(self, run_dir, *, pred_path=None, stock=None) -> tuple   # o1:719
    def main(self, argv=None) -> int                          # o1:756 + subclass flags

# module functions (pure)
members_of(pred); wkey(k); chain_from_campaign(path); stock_lang(game=None)       # o1:143, 147, 70, 156
place(fld, members) -> int                             # the FROZEN place: a member's donor, else the id itself
key_matches(k: WriteKey, pattern: dict) -> bool        # 4.6: strict; raises on any field it does not know
is_noise(k, pred) -> bool                              # O1's legacy {not_m, target, why} form, or 4.6's full-key form
cut_at_end(rows, end_places, members) -> tuple         # o1:608, on frozen places
cut_at_start(rows, start_place, members) -> tuple      # 5.2
row_keys(digest) -> dict                               # {Row.site: WriteKey} from the digest's own Observed entries, keys and seam keys (5.3)
verdict(checks) -> str                                 # o1:709
```

**`start_run`** is O1's sequence with the warp read from the predictions:
1. `g.newgame()`, then `g.wait_frames(30)`;
2. `smark = g.story_mark()`, then `g.storytrace(True)`;
3. `g._check_field_id(start, "warp", True)`;
4. `g.send(f"warp {start} {pred['entrance']} {pred.get('scenario', -1)}")`;
5. `g.wait_for(field_id == start, 60 s)`.

O1's v4 predictions have no `scenario` key, so O1 still sends `warp 50 0 -1` / `warp 31200 0 -1`. No subclass
override is needed, and a FakeGame test pins it (1.6 G7).

**`run`** is O1's `run()` step for step: P-CAP, preflight, fingerprint, the members' script snapshot, the session record
with the same keys, `one(i, side)` with the same try/except/finally and record fields, the S F order, reruns while a
side is short, `finished`, `restore_baseline`, `analyse`, the report file, and THROW. The changes are:
- the file names and the print tag come from the attributes;
- the THROW title is `titles["THROW"]`;
- the capability checks are a list (O2 adds P-OBJECTS and P-LANG);
- `drive` and `start_run` are the Segment's methods;
- a RouteVoid's class (`v`, `cell`, `by`, 2.7) is copied into the run record, so the analysis can read it per side.

**`judge`** is O1's: FROZEN, COVER, then the core checks, which are VOID ("too few covered runs") when a side is short.
Between COVER and the core checks it adds `all_run_checks`, which read every run and are judged even when COVER is
short. For O1 that list is empty, so O1's checks and their order are unchanged. O2's are O2-FORBIDDEN and O2-VOID-ASYM
(5.3): a structural fork deviation that VOIDs every fork run must still read NOT PROVEN, never VOID.

**What differs between O1 and O2** (every other line is shared):

| | O1 (`O1Segment`) | O2 (`O2Segment`) |
|---|---|---|
| start | `warp <50/31200> 0 -1` (v4: no `scenario`) | `warp <100/31220> 102 1000` |
| front cut | none (v4: no `cut_start`) | `cut_start: true`: rows before the first `w` row in the start PLACE are cut. O2-START requires them to be exactly the warp's three residue rows. |
| end | `end_field: 100` (`end_fields` absent: `[end_field]`) | `end_fields: [61]` |
| places | the frozen members map (identical to O1's `fld` rule: 100 is no member) | the frozen members map, in the cuts, the driver, the forbidden scan and the checks |
| coverage beats | `candle, named, battle, garnet`; battle judged by `battle_won` | `booth, ticket, fake, alright, clear, understand, named, climbed` |
| VOID extras | none | a BACKED forbidden hit (4.7); no `w` row in the start place; the engine's donor mapping disagreeing with the frozen members (`digest.mismatched`) |
| all-run checks | none | FORBIDDEN VOID-ASYM |
| core checks | LADDER NULL STABLE JOIN (O1's texts) | START LADDER CHAIN RESIDUE WRITES NULL STABLE SEAM MASKED STATE JOIN |
| LADDER | the keys present and SC exactly once (`sc_writes: 1`), rows by target name | rows by BYTE SPAN (bytes 0-1), each joined to its key: exactly the six rungs, in order, each `old` the previous rung |
| noise patterns | the legacy `{not_m, target, why}` | the full 8-field key, strict (4.6) |
| BUILD generations | own OR the us build | own only |
| extra offline | none | O2-TEXT, O2-REGIONS (regions and hot-spots), O2-GOALS |
| extra preflight | none | P-TEXT, P-RECOVERY; in game P-OBJECTS, P-LANG |
| extra fingerprint | none | field 70's override `.eb` sha per folder, each folder's `field/33.mes` sha per language, the game language |
| report extras | the dialogue line (O1's text) | start-dependent keys, the SC timeline, the steps table, VOID reasons per side, masked counts per side, forbidden hits with their backing, KNOWN-KIT-DEFECT lines, the folded transcripts |
| drive | `o1_opening.drive` (unchanged) | `segment_drive.drive` |

### 1.3 `o1_opening.py` after the refactor
- **Unchanged in body:** the constants `PREDICTIONS`, `MANIFEST`, `SESSION_FILE`, `CHAIN_DIR` and `BUILD_DIR`;
  `draft_predictions()`; and `drive()`. Its only change is that `RouteVoid` and `pick_for` now come from
  `segment_drive`, with O1's semantics exactly (section 1.4).
- **`O1 = O1Segment()`**: its `titles` are O1's check texts copied verbatim from HEAD (the gate checks them byte for
  byte), with `accept_us_build = True` and `drive = drive`.
- **Shared functions, O1's results:**
  - `cut_at_end` now judges frozen places. O1's end field 100 is no member, so the place of every 100 row is its
    `fld`, and the cut keeps exactly the rows O1's `fld` rule kept.
  - `is_noise` keeps O1's legacy `{not_m, target, why}` shape bit for bit. The gate's G6 proves it was not widened to
    field-mode keys.
- **Wrappers, so no importer changes:** `load_predictions`, `freeze`, `members_of`, `wkey`, `is_noise`,
  `chain_from_campaign`, `build_check`, `keys_check`, `offline_check`, `preflight`, `fingerprint`, `end_run`, `run`,
  `cut_at_end` (signature `(rows, end_field)`), `read_session`, `judge`, `verdict`, `analyse` and `main`. They also
  re-export `RouteVoid`, `pick_for`, `THROWS`, `WHERE` and `RECOVERY_FIELD`, and keep `SIDES` and the private helpers
  `_roots`, `_changed`, `_show` and `_stock_lang`.
  - The FakeGame tests use `O.draft_predictions`, `O.drive`, `O.end_run`, `O.RouteVoid` and `O.pick_for`.
  - `o1_dryrun.py` uses `O.load_predictions`, `O.members_of`, `O.SESSION_FILE`, `O.analyse`, `O.verdict` and
    `O.PREDICTIONS`.
- `o1_dryrun.py` and O1's tests are NOT edited. That they stay green unchanged is part of the gate. The new O1 mutant
  the claim-integrity critique asked for (a field-mode Byte[206]) lives in `segment_regress.py` (G6), not in
  `o1_dryrun.py`.

### 1.4 `segment_drive.py`
- **`RouteVoid(Exception)`**, moved from o1_opening. It gains three optional attributes: `v` (the class, "V1".."V14"),
  `cell` (`[donor, sc]` or None) and `by` ("driver" or "game", 2.7). O1's `raise RouteVoid(msg)` still works, and its
  runs record no class.
- **`pick_for(choice, donor, pred, *, sc=None, answered=())`** is O1's function (o1:320). Three rule keys are added,
  each optional and each skipped when absent, so O1's rules behave exactly as before:
  - `sc` (a list): the rule applies only when the published scenario is in it;
  - `once` (bool): a second match, by rule index in `answered`, raises RouteVoid;
  - `take: "default"`: the pick must be the game's own ready cursor (section 2.2, rule 6).

  The candidate loop, the substring rule, the `active` mapping and the "default" pick are untouched.
- **`drive(g, pred, side, log, *, deadline, floor_for=None, prior_for=None, progress=None, end_fields=None,
  observe=None, forbid_live=True) -> dict`** is the beat-table driver (section 2.2). It returns
  `{"end", "why", "void", "beats", "pages", "timed", "choices", "steps", "overlays", "forbidden", "end_state", "t"}`.
  - `floor_for(donor, closed)` defaults to `PlayerWalkmesh(extract.stock_walkmesh(donor), closed=closed)`.
  - `prior_for(donor)` defaults to `g.key_prior(donor)`. A member walks its donor's floor and prior, which P-FLOOR and
    P-EB prove on the live files.
  - `end_fields` overrides `pred["end_fields"]` for a rehearsal stage.
  - `observe(st, ctx)` is the rehearsal recorder's hook; it is None in a session.
  - `forbid_live` runs rule V12 (section 2.2, rule 3).
- **Helpers:** `cell(pred, donor, sc)`, `region(pred, key)`, `polys(pred, keys)`, `until_ok(expr, x, z)`,
  `closed_tris(pred, step, wmesh)` (which expands `closed_floors` to triangle indices), and `on_route(fid, members,
  route, end_fields)`.
- **Shared with the analysis (pure):** `forbidden_hits(rows, pred, members, start_place) -> list` (4.7's patterns over
  raw `w` rows) and `backing(hit, log, pred) -> dict | None` (4.7's backing rule over the run's own log). The driver's
  live scan and the analysis call the same two functions.

### 1.5 `o2_alexandria.py`
`O2Segment(Segment)` has:
- `tag = "O2"`, `predictions = HERE / "o2_predictions_v1.json"`, `manifest = HERE / "o2_forks.json"`;
- `session_file = "o2_session.json"`, `report_file = "o2_report.txt"`;
- `chain_dir = C:\gd\_ns_playtest\o2\fork`, `build_dir = C:\gd\_ns_playtest\o2\build`.

It carries:
- `draft()`, the section 4 content. Members and names are read from `campaign.toml` as O1 does, with an assertion that
  there are exactly `{31220+i: 100+i for i in range(18)}`.
- `all_run_checks` (O2-FORBIDDEN, O2-VOID-ASYM), `core_checks`, `why_void`, `report_extra`, `offline_extra` (O2-TEXT,
  O2-REGIONS, O2-GOALS), `preflight_extra` (P-TEXT, P-RECOVERY), `fingerprint_extra`, and `capabilities` (P-CAP,
  P-OBJECTS, P-LANG).
- `text_rule(stock: {lang: bytes}, shipped: {lang: bytes}, session_lang) -> (ok, lines)`: the lead's ruling as one pure
  function, which O2-TEXT and P-TEXT share (6.1).
- `trace_summary(rows, pred)`: the SC sequence, the Int16[2] sequence, each registered key present or absent, and every
  unregistered key. `--rehearsal-report` and the dry run both use it.
- The CLI: `--offline-check`, `--preflight`, `--analyse DIR`, `--predictions PATH`, `--freeze` (refuses an existing
  file), `--draft` (prints the draft JSON for review) and `--rehearsal-report DIR`.
- Module-level `run(g)` for `tools/play.py`, which is `O2.run(g)`.

### 1.6 The O1 regression gate (`segment_regress.py`)
The implementer writes it and captures its baseline FIRST, before any other code change, at the design commit. Then it
is run after every commit that touches shared code. It exits 0 only if every item passes. Exit 2 means an archive or the
baseline is missing, so the gate was not run, which is not a pass.

| Item | Check |
|---|---|
| G0 | `py studies/story-trace/segment_regress.py --capture` (once, before the refactor) writes `research/o1_regress_baseline.json` (LF, `-text`). It holds the full `(checks, report)` of o1e, of o1d, of every one of the 16 dry-run cases (the 15 of `CASES` and "predictions-changed"), and `offline_check(v4)`. It refuses to overwrite an existing baseline. |
| G1 | `o1_opening.analyse(O1E, pred_path=HERE/"o1_predictions_v4.json")`: the report text equals `(O1E/"o1_report.txt").read_text(encoding="utf-8")` exactly (read_text folds the archive's CRLF), and the verdict is `PROVEN` with 6 checks, all True. `O1E = C:\gd\Dream-World-IX\.harness-runs\20260929-213149-story-o1e`. |
| G2 | `py studies/story-trace/o1_opening.py --analyse O1E --predictions studies/story-trace/o1_predictions_v4.json` exits 0. |
| G3 | Every dry-run case's `(checks, report)` is byte-equal to the baseline's: not only the verdict and each check's pass/fail (which is all `o1_dryrun.result` compares), but every detail and every report line. `o1_dryrun.run_cases(v4)` also still returns 0 (16/16 as registered). |
| G4 | `o1_opening.offline_check(v4)` equals the baseline's `[(ok, what, detail)]`. |
| G5 | o1d's `(checks, report)` is byte-equal to the baseline's (`VOID: O1-COVER, O1-LADDER, O1-NULL, O1-STABLE, O1-JOIN`): a real VOID path. `O1D = C:\gd\Dream-World-IX\.harness-runs\20260929-212507-story-o1d`. |
| G6 | The O1 noise mutant: `o1_dryrun.six(v4)` with a FIELD-mode (`m` 1) Byte[206] row (an addition-buffer row at 50 e17, `add` 1, `tag` -1, keyed with no join; one random `new`, the same in every F run) added to the F runs only reads `O1-NULL` False, `O1-JOIN` True and `NOT PROVEN: O1-NULL`. O1's noise covers `m != 1` only, so an `is_noise` widened to every mode would read PROVEN here. (No stock store of Byte[206] exists in 50 or any O1 donor: 11.3 A0.) |
| G7 | `py -m pytest tests/test_harness.py -q -p no:cacheprovider -W ignore -k "o1_ or overlay_hint or segment"`, from `ff9mapkit/`, is green with 0 skipped. This includes `test_o1_segment_run_pins_o1s_session_surface` (9, PART A): the gate's `REQUIRED_TESTS` names it once A3 lands, and every test the baseline collected must still run. |

The archived `o1_session.json` records the O1 worktree's predictions path. G1, G2 and G5 pass the predictions path
explicitly, with the same sha.

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
   "tolerance": 45, "min_depth": 40, "exit_wait_s": 8.0, "exit_slack": 40,
   "closed_tris": [], "closed_floors": [], "attempts": 2, "interrupts": 1, "beat": null, "start": [x, z]}
  ```
  - `target` and `until` are exclusive.
  - `start` is used only by the offline route check (O2-GOALS). The live walk plans from where he stands.
  - `min_depth` applies to confirm steps; `exit_wait_s` and `exit_slack` to cross and leave_now steps (2.3).
  - The defaults are in `steps_default` (4.1).
- **Other keys:** `regions` and `hotspots` (2.5), `choices` (2.6), `naming: [{"donor", "sc", "beat"}]` and
  `route: [100, 101, 102, 103, 104, 105, 106, 115, 116]`. The places a run may stand in before the end are `route`
  plus `end_fields`, on the F side through the members map (2.2, rule 2).

### 2.2 The driver loop (`segment_drive.drive`)
O1's loop, with its rules in O1's order. First match wins. Every poll reads `st = g.state`, `sc = st.scenario` and the
place `donor = place(fid, members)`: on the F side a member's donor, on the S side (members `{}`) the id itself.
1. **End.** `fid in end_fields` (61 is a real field on both sides):
   - read the `end_state` variables (4.1) into the outcome: `g.watch(*their bits)`, the next state's `flags`, then
     `unwatch`;
   - run rule 3's forbidden scan once more, so nothing after the last new visit goes unscanned (the claim-integrity
     critique #4);
   - return `reached`.

   **Every poll after rule 1 runs the stall watchdog.** The progress signature is `(fid, sc, ui_state, dialog texts,
   choice snapshot, control, round(x/8), round(z/8), storytrace rows)`. If it stays unchanged for
   `budget.no_progress_s` (120 s draft) of wall time, the driver raises RouteVoid V14 "no progress for 120 s in <fid>
   (place <d>) at SC <sc>". Executors are bounded by their own timeouts, so the watchdog is read between them. A hang
   (a fork MBG that never starts, a stuck page) then costs 120 s, not the whole 1800 s run budget.
2. **Route.** `fid > 0` and not `on_route` -> RouteVoid V11 "left the route: entered <fid> (place <d>)".
   - On the S side a field is on the route when it is in `route` or `end_fields`.
   - On the F side it is on the route only when it is a MEMBER whose donor is in `route`, or an end field. A real route
     field reached on the F side (real 103: its place is 103, which a donor test would pass) is OFF the chain, the
     claim-integrity critique #2.

   A field id of 0 or below, published during a load, is waited out (rule 9).
3. **Visit.** When the (positive) field id changed, start a new visit. With `forbid_live`, run the forbidden scan
   (4.7).
   - It reads the run's own rows (`g.story_rows()` after its last `arm`) and scans only `w` rows, from the run's START
     ROW on: the first `w` row whose place is the start place. So the warp's residue in field 70 (0.2 #13) is never
     scanned.
   - A hit whose cause the driver's own log backs (4.7) -> RouteVoid V12.
   - An unbacked hit is logged (`{"k": "forbidden", "backed": false, "row", "pattern", "why"}`) and the run goes on. The
     analysis judges it as a finding (O2-FORBIDDEN), never as a VOID.
4. **Naming** (ui `NameSetting`). A registered `(donor, sc)` runs `g.accept_name()` and sets its beat. Anywhere else,
   RouteVoid V10.
5. **Tutorial or battle.** RouteVoid V10: O2 registers neither. O1 keeps its own drive, so O1's battle path is
   untouched.
6. **Choice.** O1's readiness hold, unchanged: `_choice_ready`, and the snapshot held unchanged for `settle_s` over live
   frames. Then:
   - `index, rule = pick_for(st.choice, donor, pred, sc=sc, answered=answered)`;
   - with `rule["take"] == "default"`: `index` must equal `st.choice["selected"]`, the game's own ready cursor, or
     RouteVoid V3 "the frozen pick <text> is not the game's default <selected>: stepping the cursor is not the route".
     Then `g._take_default_choice(st)`, which confirms the cursor option and never presses up or down;
   - otherwise `g.choose(index)`, which O1's non-default picks keep;
   - record `{field, donor, sc, options, active, selected, count, index, took}`, add the rule to `answered`, set its
     beat.
7. **Page** (dialog open, text, control OFF).
   - In a `no_pages` cell: RouteVoid V5 "a page where the route has none: <text>". Nothing is pressed: in (105, 1152) a
     Confirm could be exactly Jack's side trip.
   - Otherwise O1's rule: record the text, then `press("confirm", 3)` and `wait_frames(frames_for_ticks(4))`, and log a
     `press` row (below).
   - A page whose `raw_texts` holds `[TIME=` is recorded in `timed` (its index), so the transcript can fold it.
8. **Control held** (`player_x` known, not fading).
   - Log an overlay: a dialog up WITH control is O1's rule, never paged.
   - `cell = table[(donor, sc)]`; if absent, RouteVoid V4 "control held in <fid> (place <d>) at SC <sc>, where the table
     has no entry".
   - Settle O1's way: `settle_s` of consecutive control samples, unless the next step is `immediate`.
   - `step = cell.steps[done]`; if `done == len(steps)`, RouteVoid V4 "control held after the cell's last step".
   - Run the step's executor (2.3), then update the counters from its outcome.
9. **Otherwise:** sleep 0.05 s.

**Watched cells.** Between executor calls, while in a cell with `watch`, every poll logs a `watch` row and checks each
watched object: control held and `dist(player, object) <= object[radius]` -> RouteVoid V6.

**The evidence the driver keeps** (what 4.7's backing rule reads):
- A `press` row for every Confirm it presses: `{"k": "press", "why": "page" | "confirm", "field", "donor", "visit",
  "pre": {"frame", "control", "x", "z"}, "post": {...}, "near": [{"sid", "kind": "talk" | "range", "dist", "radius"}]}`.
  - `pre` is the sample the press was decided on.
  - `post` is the loop's next sample; no extra read is taken.
  - `near` lists the published objects (s89) whose `talk_r` or `range_r` disc, 64u wider, contained him at `pre`.
- A `watch` row for every poll in a watch cell, and, after each executor call in one, one row per StateRing sample the
  harness read during the call (`g.states_since(frame0)`, H6). This puts a race lost inside a harness call on record
  too. The shape is `{"k": "watch", "frame", "control", "x", "z", "objects": [{"sid", "x", "z", "range_r", "dist"}]}`,
  with the watched sids only.

The deadline raises `HarnessError("the run's budget ran out in field <fid>")`, as O1's does (V13).

### 2.3 Step kinds (the executors)
Each executor returns `(outcome, record)`, where outcome is one of:
- `done` (the step's evidence seen);
- `interrupted` (control went away in the same field with no evidence);
- `failed` (the walk ended with control held and no evidence);
- `void: <why>` (with its class, 2.7).

The counters: `failed` spends an attempt (`attempts` exhausted -> V7). `interrupted` spends an interruption
(`interrupts` exhausted -> V7). The walk calls all pass:
- `walkmesh=floor_for(donor, closed)`, `prior=prior_for(donor)`;
- `unstick=True`, `smooth=True`, `margin=pathfind.KEEPOUT_MARGIN_W`, `timeout=timeout_s`;
- `handoff=True` (H1), `npcs=step.npcs` and `overlay_ok=step.overlay_ok`.

**`cross`** calls `g.route_cross(*goal, zone=R.points, region=R.points, avoid=polys(step.avoid), handoff=True, ...)`,
then judges the record:
- **The field changed** (the record's `landed`, or the id already differs): `done` if the new place is `step.to`, else
  VOID V11.
- **Control went away with the field unchanged** (`lost` set, `landed` None). Every exit starts this way (0.2 #12).
  The loss sample is `record["lost"]` (H1):
  - **At or inside the target:** `pathfind.poly_gap(lost.x, lost.z, R.points) <= exit_slack` (40u; ExitField walks
    him onto the region's first edge, so the sample can sit on the boundary). This is the exit's fade. The executor
    itself waits, up to `exit_wait_s` (8 s draft) of live frames, for the published field id to change and then for a
    positive id. It returns `done` if the new place is `step.to` and V11 otherwise. If there is no change within the
    wait, it returns `interrupted`.
  - The wait stays INSIDE the executor, so no rule of the loop runs during a fade. 106's [TIME=45] hint, still up with
    control off in that gap, is therefore never read as a page (V5) in the `no_pages` cell (106, 1153). This was the
    driver critique's blocker.
  - **Outside the target:** `interrupted` at once. 100's Rat Kid bump stops Vivi at z 6160-6220, over 300u south of
    e15's z 6532.
- **The walk ended with control held**: `failed` (the record's `inside` says whether he stood in the zone).

**`trigger`** calls `g.route_to(*goal, zone=R.points if target else None, avoid=..., ...)`.
- Control went away with the evidence true at the loss sample (standing in `target` by `doorface.region_contains`, or
  `until` holding for its x/z): `done`. A walk-in trigger takes control on the tick he stands in it, with no exit walk
  after it.
- Control went away without the evidence: `interrupted`.
- The walk ended with control held: wait up to 2 s for control to go; `done` or `failed` as above.

**`confirm`** calls `g.route_to(*goal, tolerance=step.tolerance, avoid=..., ...)` WITHOUT `zone`. A zone ends the walk
on the first sample inside the region, at its edge (session.py:3199-3200), not at the deep goal. Then:
1. `st = g.settle()`. He must stand in the target by the engine's rule (`doorface.region_contains` on the settled
   sample), at depth `>= step.min_depth` (40u draft), or the outcome is `failed` and nothing is pressed.
   - TreadQuad tests the actor's transform position (EventEngine.TreadQuad.cs:9-10). A settled sample equals it, and
     the depth covers the rest.
   - Neither region has a QuadCircle or QuadTalkable override (EventEngineUtils.cs has no 103xxx or 115xxx key), so
     the quad rule is the engine's rule.
   - O2-GOALS proves offline that an arrival within `tolerance` always meets the depth: `depth(goal) - tolerance >=
     min_depth` (2.4).
2. `g.press("confirm", 4)` (a plain press, as O1's candle), with a `press` row, then `g.wait_for(expect, confirm_s)`.
   `expect` `choice` means `st.choice is not None`; `control_lost` means `not st.control`. The expectation seen: `done`.
   Nothing seen: `failed`.
3. With `then: "climb"` and `done`: `g.climb("up", until=..., **step.climb)` (H2). It stops when page 384 opens, the
   field changes, or `player_y < -2431`.
   - `until`: `done`, and the beat `climbed` is set.
   - `control` (he slid to the bottom and control came back): `failed`, and the step runs again.
   - `stalled` or `not-started`: VOID V9.

**`wait_sc`** calls `g.route_to(*goal, avoid=..., ...)`, then
`g.wait_for(sc == step.sc or not control or field changed, step.wait_s)`.
- The scenario reached: `done`. Control lost: `interrupted`. Timeout: VOID V8.

**`leave_now`** (`immediate`: no driver settle):
1. `lunge = g.lunge(*goal, ticks=step.lunge_ticks, avoid=..., walkmesh=...)` (H3), skipped when `lunge_ticks` is 0
   or the field has no cached basis;
2. then `g.route_cross(..., settle=0.0, npcs=False, handoff=True)`.

It is judged exactly as `cross`, inside rule included, but `interrupted` is VOID there (`interrupts: 0`): in
(105, 1152) a lost control outside e11 is Jack. Its watch cell also appends the StateRing samples of both calls as
`watch` rows (2.2).

Every step writes a log row
`{"k": "step", "field", "donor", "sc", "visit", "n", "kind", "name", "attempt", "outcome", "t0", "t1", "from", "to",
"lost", "route": <route record trimmed as dali_tour does>, "lunge", "climb", "depth"}`. The rehearsal report and the
analysis's steps table read these rows. `lost` and the frame the id flipped are what F7 sizes `exit_wait_s` from.

### 2.4 The O2 table

The measurements used in the Goal column:
- **wall** is `PlayerWalkmesh.distance_to_boundary`, against cam.COLLISION_RADIUS_W = 80;
- **depth** is the distance inside the target region by the engine's IsInQuad rule;
- **route** is `route_avoiding` from the step's `start`, with the step's `avoid` set, `leave_wall`;
- **hot-spot clear** is the distance beyond the nearest hot-spot's reach of that field (2.5).

| Cell | Control comes | Step | Goal (checked) | Avoid (and not avoided) | Flags | Done |
|---|---|---|---|---|---|---|
| (100, 1000) | Stage 6: 100 e19 t1 EnableMove ip2020, at (0,850). Again after the bump: e19 t15 EnableMove ip2143. | cross `100.e15` -> 101 | (0,7000): floor 1, wall 421, depth 331. Route 1 leg, 6150u. | `100.e16` (-> 107), `100.e17` (-> 114). Not avoided: `100.e11`, benign (0.2 #3). | `npcs: false` (the Rat Kid is a MoveInstant chaser at z+83/frame; a planner keeping out of his disc stalls, and the bump is forced), `interrupts: 1` (the bump, outside e15), `closed_floors: [3]` (EnablePath(3,0) e1 t1 ip124 until ip410; conservative after it) | Landed in 101 |
| (101, 1000) | Stage 2: 101 e7 t1 EnableMove ip358, at (1939,-883). | cross `101.e16` -> 102 | (-2936,-400) (region_goal): floor 2, wall 461, depth 470. Route 3 legs, 5170u. | `101.e15` (-> 100: the arrival door, 300u east of the control spot), `101.e17` (-> 112, facing-gated, on the street). | `npcs: true` (the nobles walk off to (-4000,-400)) | Landed in 102 |
| (102, 1000) | On arrival: 102 e0 t0 ip543, at (865,2525). | cross `102.e8` -> 103 | (752,5415): wall 308, depth 323. Route 1 leg, 2892u. | `102.e9` (-> 101), `102.e10` (-> 108). | `npcs: true` | Landed in 103 |
| (103, 1000) | On arrival, at (-75,-2210). | confirm `103.e28` (the booth "?"), `expect: choice` (215) | (50,-800): wall 292, depth 200 (155 at worst within tolerance 45, over `min_depth` 40), hot-spot clear 536 (e20 (600,-272), reach 226). Route 1 leg, 1416u. | `103.e22` to `103.e27` (e26 and e27 are one quad). | `npcs: true` (Hippaul, e18, walks the square) | The choice opened; the rule answers it (2.6) |
| (104, *) | Never: 104 gives no control. | (none) | | | | Control here is V4 |
| (103, 1150) | On arrival: spawn (45,-950), INSIDE `103.e28` (the "?" is up). | cross `103.e22` -> 105 | (-3993,-965) (region_goal): wall 477, depth 512. Route 3 legs, 4199u. | `103.e23` to `103.e27`. Not avoided: `103.e28`, benign here: its tag 2 only shows the bubble, and a cross never presses Confirm. | `npcs: true`. 215 opening here is V1 (rule scope). | Landed in 105 |
| (105, 1150) | On arrival: 105 e14 t0 EnableMove ip348, at (-51,2986). | trigger `105.e12` (tag 2: guard ip38, DisableMove ip75) | (-500,1750): wall 381, depth 291. Route 1 leg, 1315u. | `105.e10` (-> 103), `105.e11` (-> 106). | `npcs: true`, `closed_floors: [2]` (EnablePath(2,0), Main_Init ip296/325) | Control lost standing in e12 |
| (105, 1152) | Stage 14: 105 e14 t1 EnableMove ip2859, at the lookout (-244,2562), 13-29 ticks after Jack wakes (Map.Byte[35]:=0 ip2720). Jack is within his `range_r` 299 of the lookout about 74 ticks after the wake: a 45-61 tick window (0.2 #10). | leave_now `105.e11` -> 106 | (-667,-403) (region_goal): wall 533, depth 422. Route 1 leg, 2995u. | `105.e10`. Not avoided: `105.e12`, dead at 1152 and lying across the line (0.2 #4). | `immediate`, `lunge_ticks: 10`, `settle: 0`, `npcs: false` (never wait for Jack), `attempts: 1`, `interrupts: 0`. Cell: `no_pages`, `watch: [{sid 7, "Alleyway Jack", range_r}]` | Landed in 106 |
| (106, 1152) | On arrival: 106 e16 t0 EnableMove ip406, at (-123,3494). | wait_sc `sc: 1153` | (550,2000): floor 3, wall 427, 320u from Puck's stop (800,1800), well inside his 1200/1400. Route 2 legs, 1655u. | `106.e12` (-> 105, 140u from the spawn), `106.e13` (-> 113, gated, on the street at z about 0), `106.e14` (-> 115, not before 1153). | `overlay_ok` ("Over here!" [TIME=45], shown WITH control), `npcs: true`, `wait_s: 90`. Cell: `no_pages` | Published SC 1153 (106 e2 t1 ip312) |
| (106, 1153) | Continues from the wait. | cross `106.e14` -> 115 | (-123,-1306) (region_goal): floor 3, wall 84, depth 88, the deepest standable spot, so the walk finishes on the zone. Route from (550,2000): 5 legs, 3939u. | `106.e12`, `106.e13`. | `overlay_ok` (328/329 [TIME=45]), `npcs: true` (Puck walks the same line into e14 and removes himself). The exit's first edge is its west edge: control goes 8-16 ticks before the fade ends, and the executor waits it out (2.3). Cell: `no_pages` | Landed in 115 |
| (115, 1154) | Stage 1: 115 e1 t1 EnableMove ip500, at (206,-1911). | confirm `115.e15` (the ladder "!"), `expect: control_lost` (e15 t3 Map.Byte[49]:=1 ip65, then e17 t1 DisableMove ip913) | (0,50): wall 117, depth 90 (45 at worst within tolerance 45, over `min_depth` 40; 90 is the quad's deepest point, so no depth floor near 80 is walkable), hot-spot clear 1535. Route 1 leg, 1972u. | `115.e13` (-> 106: the arrival door). Not avoided: `115.e14`, dormant (0.2 #5). | `npcs: true` | Control lost |
| (115, 1155) | Stage 10: 115 e17 t1 EnableMove ip1841 (SC already 1155), where stage 5 walked him, about (50,-968). R-115a measures it (F10). The warp-start spawn (R-115, entrance 215) is (257,-2500): route 3 legs, 2607u. | confirm `115.e15`, `expect: control_lost`, `then: climb`, `beat: climbed` | (0,50), as above | `115.e13` | `npcs: true` (Kupo is talkable at about (304,-785) from stage 10, 889u from the goal; only the ladder gets a Confirm, and a press with him `near` is recorded), `attempts: 2` (a slide to the bottom gives control back) | The climb reached the top: page 384 or field 116 |
| (116, 1155) #1 | Stage 3: 116 e21 t1 EnableMove ip662, at (2718,-137). | trigger `until {x_le: 900}` (e21 t1 ip742, DisableMove ip773) | (630,190): floor 1, wall 115. Route 3 legs, 2303u. | 116 has no regions. | `npcs: true`. Puck (speed 68 against Vivi's 60; `TimedTurn(...,64)` is a 4-8 tick turn) stays ahead of her. `npcs` plans round his published body and pushes a non-solid one only when no route goes round, which the driver critique found this route never needs. | Control lost with x <= 900 |
| (116, 1155) #2 | Stage 8: e21 t1 EnableMove ip958, at the landing (-339,244). | trigger `until {z_ge: 2300}` (ip1038, DisableMove ip1069) | (-750,2690): wall 115. Route 3 legs, 2736u. | | `npcs: true`, `closed_tris: [217]` (EnablePathTriangle(217,0) ip923) | Control lost with z >= 2300 |
| (116, 1155) #3 | Stage 11: 116 e2 t1 EnableMove ip901. | trigger `until {x_gt: 3000, z_gt: 10300}` (e16 t1 ip11, DisableMove ip50) | (3410,10700): wall 137. Route from (-750,2690): 14 legs, 13610u. | | `npcs: true`, `closed_tris: [217]` | Control lost with the predicate true |
| end | | place 61 -> `reached` | | | | |

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

### 2.5 Regions and hot-spots (frozen with the predictions; O2-REGIONS re-decodes each from the stock bytes)
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
| 106.e14 | (-327,-1240) (-317,-1462) (151,-1458) (151,-1188) | exit -> 115 (211); its first edge is the west edge |
| 115.e13 | (-124,-3597) (984,-3546) (745,-2881) (633,-2741) (-34,-2783) | exit -> 106 (212) |
| 115.e14 | (150,144) (-150,144) (-150,-40) (150,-40) | dormant (InitRegion(14) only in e0 t0's default branch, ip406); tag 3 -> 115 e17 t12 |
| 115.e15 | the same quad as e14 | confirm (the ladder: tag 3 ip65, climb at ip125 when Map.Byte[24]==10) |

104 and 116 have no SetRegion at all.

**Hot-spots** (`hotspots`, per donor). Each is decoded from its tag 1:
- `x` and `z` are its `Global.Int16[220]` / `[222]` store constants (s16);
- `n` is its `Instance.Int24[0] const(n) B_LT` compare;
- reach is `32*sqrt(n)`, rounded down.

| Donor | sid: (x, z) n reach |
|---|---|
| 100 | e12: (-658, 4843) 77 280; e13: (-758, 1121) 77 280 |
| 101 | e11: (-540, -979) 60 247; e12: (-1011, -2327) 60 247; e13: (998, -2356) 60 247; e14: (2434, 492) 40 202 |
| 102 | e7: (1477, 4748) 80 286 |
| 103 | e19: (2239, 1114) 300 554; e20: (600, -272) 50 226; e21: (-891, 4413) 50 226 |
| 105 | e9: (-1561, 447) 60 247 |
| 106 | e11: (-155, 1205) 120 350 |
| 115 | e11: (1800, -323) 90 303; e12: (-547, -1739) 90 303 |
| 116 | e17: (-1124, -98) 40 202; e18: (-291, 10894) 80 286; e19: (4200, 2762) 90 303 |

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
Each carries its class `v`, its `cell` and an attribution `by`. `by: "driver"` means the driver's own action or record
explains it (a lost race, a failed walk, the instrument). `by: "game"` means the game showed something the table does
not expect and no driver action explains it. O2-VOID-ASYM (5.3) reads the classes per side, so a structural fork
deviation cannot hide as a VOID.

| | Condition | by |
|---|---|---|
| V1 | A choice no rule matches for its donor and SC. 215 re-offered at SC 1150 lands here. | game |
| V2 | A `once` rule asked again: 251 after an info option, or 215 twice. | game |
| V3 | A `take: "default"` rule whose ready cursor is not the pick. This forbids stepping the cursor, including in 104's menu. | game |
| V4 | Control held in a cell the table does not have, e.g. 104 or (105, 1151); or control after a cell's last step. | game |
| V5 | A page (control off) in a `no_pages` cell: Jack's window or the mugging in (105, 1152), or anything unexpected in 106. It is VOID with NO Confirm. | driver when 4.7's `contact` backing holds before it for a watched object (a lost race); else game |
| V6 | A watched object within its radius, control held: Jack (sid 7) inside his published `range_r` in (105, 1152). | driver |
| V7 | A step out of `attempts`, or over its `interrupts`. | driver |
| V8 | `wait_sc` timed out (SC never reached 1153). | game |
| V9 | The climb stalled (3 Up bursts moved y by nothing), or never started (control still held 5 s after the Confirm). | driver |
| V10 | A naming screen, battle or tutorial outside a registered cell. | game |
| V11 | The run left the route (rule 2), or a crossing landed somewhere other than its step's `to`. | driver when it happened during a driver step (a walk into the wrong door); else game (a scripted transition) |
| V12 | Live forbidden scan: a hit whose cause the driver's log backs (4.7). An unbacked hit is not a VOID. | driver |
| V13 | The budget (`STOPPED: ...`), or an unexpected exception (`STOPPED (unexpected): ...`), as in O1. | driver |
| V14 | The stall watchdog: nothing published changed for `no_progress_s`. | game |

Every one of these makes the run VOID. The analysis repeats the trace-visible ones (4.7, 5.1), so a driver fault can
never turn a walk divergence into STOCK ONLY or FORK ONLY. It also reads their classes per side (O2-VOID-ASYM), so a
game-caused VOID on one side only is a finding, never a quiet VOID.

### 2.8 Every research beat, and what handles it
The beat numbers are `o2_research.json`'s `reconciled.route.beats`. The rules are the loop's (2.2); cells are 2.4;
choice rules are 2.6.

| Beats | Field | Handled by |
|---|---|---|
| 1-2 | 100 | Rule 9, waiting: mbg101 plays with no control and no dialog. Nothing is pressed; type 1 has no skip dialog. The watchdog allows 120 s of it (F7 re-sizes). |
| 3, 5, 6 | 100 | The page rule: 146; 147 (async + WaitWindow); 148 [TIME=20], recorded as timed. |
| 4 | 100 | Nothing: the stage-3 party writes (4.4). |
| 7-10 | 100 | Cell (100, 1000). The cross is interrupted once by the bump (outside e15); 154 [TIME=10] and 155 are pages; the same step then runs again and lands through the exit's fade. |
| 11-13 | 101 | The page rule (168), then cell (101, 1000). |
| 14 | 102 | Cell (102, 1000). |
| 15 | 103 | Nothing: Hippaul's `:=1` is registered (4.4), his `:=2` is noise (4.6). |
| 16-17 | 103 | Cell (103, 1000) confirm, then choice rule 1 (215). |
| 18-24 | 104 | The page rule (250, 252, 253, 254, 255, 256, three times 70, 257) and choice rule 2 (251). There is no control anywhere in 104. |
| 25-26 | 103 | Cell (103, 1150); no Confirm. |
| 27 | 105 | Cell (105, 1150). |
| 28-34 | 105 | The page rule (415 timed, 416-418, 304, 308, 312, 313, 315) and choice rules 3, 4 and 5. |
| 35-36 | 105 | Cell (105, 1152), leave_now. Jack is handled by V5, V6 and V12, with the `watch` evidence. |
| 37-38 | 106 | Cells (106, 1152) wait_sc and (106, 1153) cross, under overlays; the exit's fade is waited out inside the executor. |
| 39-40 | 115 | The page rule (352, 353), then cell (115, 1154) confirm. |
| 41-44 | 115 | The page rule (356 timed, 357-366, 368, 370-383) and choice rule 6 (367). |
| 45-47 | 115 | Cell (115, 1155): confirm, then the climb; then the page rule (384). |
| 48-52 | 116 | The page rule (387-394), cell (116, 1155) #1 and #2. |
| 53 | 116 | The page rule (395, 396), the naming (116, 1155), the page rule (397-399). |
| 54-56 | 116 | Cell (116, 1155) #3, the page rule (400-402), then the end (61), where the end state is read. |
| 57 | all | Never taken: the forbidden keys (4.7) and V1/V3 keep optional content out. |

---

## 3. Harness additions (each minimal, modelled in the FakeGame, tested)

Every default keeps today's behaviour, so no existing caller changes. Each addition lands with the FakeGame tests named
here, in `ff9mapkit/tests/test_harness.py`. **Every test here in which a region warps sets `fake.exit_frames = 50`.**
The fake's ExitField model already has the fade (fakegame.py:354-378: control off on the entering frame, the field
change `exit_frames` later), but it defaults to 0, and with 0 no test can see the race of 0.2 #12.

**H1. `route_to` / `route_cross` pass-throughs: `settle`, `overlay_ok`, `handoff`; and where control went.**
- `route_to(..., settle=None, handoff=False)`:
  - `settle` goes to its opening `wait_control(settle=...)`. None is SETTLE (1.0 s), as today.
  - `handoff=True`: when control goes away mid-walk, during a facing step, or the field changes, `land()` returns at
    once. It does not call `_await_landing(origin, timeout)`, so there is no wait for the landing, no wait for control
    to come back, and no wait for the destination to become playable. `landed` is the new id if the field already
    changed, else None, and `record["handoff"] = True`.
  - Always, with or without handoff: `record["lost"]` = `{"frame", "field", "x", "z", "control"}` of the first state
    the call reads with control gone (in `land()`, or in route_cross's own wait below). It is None when control never
    went. With handoff the executor judges the crossing from it (2.3).
- `route_cross(..., settle=None, overlay_ok=False, handoff=False)`:
  - It passes all three to `route_to`. Today it never passes `overlay_ok`, so its opening `wait_control` holds for as
    long as a hint is up: every one of 106's [TIME=45] hints costs its whole duration, and a hint Puck shows again
    (while Vivi is over 1200u away) can outlast the wait.
  - With `handoff`, a walk that ended with control held waits (bounded by `timeout`) for `field_id != origin or not
    control`, then returns. It never calls `expect_field_change`'s `wait_playable`, so an arrival scene (101's Herald,
    115's Puck) is the caller's to sit through. There is no "never became playable" error and no parsing of error
    text, unlike dali_tour's `_REACHED`.
- **Tests:**
  - `test_route_cross_handoff_returns_at_the_control_loss`: `exit_frames = 50`, and the destination arrives without
    control (H4 `arrive_control: False`). With `handoff=True` it returns during the fade, with `landed` None and `lost`
    inside the region. The field changes 50 frames after `lost.frame`, into the scene, and nothing raises. The control
    case, `handoff=False`, raises "never became playable" with a 2 s timeout.
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
- **The warp, with its residue.** `warp <field> [entrance] [scenario]` models ServicePendingWarp:
  - it writes `entrance` (arg 1, when >= 0) into the modelled gEventGlobal as Int16 at byte 2;
  - it writes `scenario` (arg 2, when >= 0) as UInt16 at bytes 0-1 and sets `self.scenario`;
  - while tracing, it emits one `r` row (`why: "frame"`) per byte that changed, stamped with the field BEFORE the
    warp (rung 1's net), then changes the field.

  Today both args are dropped, so `warp 30820 102 1000` cannot publish SC 1000, and no fake trace has residue.
- **The ladder:** `self.ladder` (None), `self.climbing = False`, `self.climbed = False`. In `_step_world`, BEFORE the
  "no control, no tick of it moves him" skip, `_step_ladder(ticks)` runs while `climbing`:
  - Up or Left held: y -= step per field tick. Down or Right: y += step.
  - y < top: `climbing = False`, `climbed = True`, control stays off.
  - y > bottom: `climbing = False`, `control = True`.
  - y is `player[1]`, already published.
- **Regions** (the `regions` dicts) get two opt-in keys:
  - `"take": True`: entering sets `control = False` and appends to `fired` with `to` None; it is a walk-in trigger.
  - `"arrive_control": False`: the destination arrives with control OFF, the arrival scene's to hand back.
- **Watched bits read the modelled gEventGlobal.** The published `flags` of watched bits come from `story_bytes`,
  which `flag` and `script_store` both write, so the end-state read (2.2, rule 1) is testable.
- **Tests:** `test_fake_warp_publishes_the_scenario`, `test_fake_warp_writes_its_residue_in_the_old_field` (bytes 0-2
  from zeros; nothing on byte 3), `test_fake_watched_bits_read_the_story_bytes`, plus the ladder and region keys through
  the H1/H2 tests above.

**H5. `pathfind.PlayerWalkmesh(wmesh, mask=0xFF, opened=(), closed=())` (kit, additive).**
The triangles in `closed` are closed to him like a door strip: not floor, their edges are walls. This is the script's
`EnablePathTriangle(n, 0)` / `EnablePath(floor, 0)`, which the offline planner otherwise cannot see:
- 116 triangle 217 after ip923;
- 105 floor 2 until Puck's ladder (Main_Init ip296/325; e3 t1 ip1113/1448);
- 100 floor 3 during the chase (e1 t1 ip124 -> ip410).

`standing_at` keeps `closed`. Test: a closed triangle is off the floor, its shared edges are walls, and
`route_avoiding` goes round it. The planned O2 routes already clear all three (O2-GOALS checks it), so H5 guards
REPLANS: a stall or an NPC replan must never plan over the fallen plank.

**H6. `Session.states_since(frame) -> list[dict]` and `StateRing.since(frame)` (artifacts.py).**
The raw published states the Session's ring holds with `frame > frame`, oldest first. The ring (`self._ring`, fed by
every read the harness makes, `STATE_RING` 300 distinct frames, about 10-20 s) already holds every sample a walk read.
This exposes them, so the driver can keep a race lost inside `lunge`/`route_cross` on record (2.2). Test:
`test_states_since_returns_the_rings_samples_after_a_frame`.

**Not needed:**
- Runtime region decoding: the polygons and hot-spots are frozen (2.5).
- Stage or bubble publication: cells key on SC plus the counter; triggers on regions and positions.
- NPC tracking: s89's `objects` is live.
- A new choice verb: `_take_default_choice` and `choose`.
- A naming verb: `accept_name`.
- A gEventGlobal read verb: `watch` publishes bits.
- Recovery: `end_run`, warping to 4600 first.

---

## 4. Predictions (draft v1: `O2Segment.draft()`)

### 4.1 Top level
```json
{"version": 1,
 "what": "O2: 100@1000 (warp, entrance 102) -> 101 -> 102 -> 103 -> 104 -> 103 -> 105 -> 106 -> 115 -> 116 -> Field(61), stock vs the alxt zone's verbatim fork (PLAN.md, O2)",
 "rehearsals": [],
 "order": ["S","F","S","F","S","F"], "min_covered": 2, "rerun": {"max": 2},
 "budget": {"run_s": 1800, "run_min_s": 1200, "session_s": 14400, "settle_s": 1.0, "no_progress_s": 120},
 "start": {"S": 100, "F": 31220}, "entrance": 102, "scenario": 1000, "lang": "us",
 "end_field": 61, "end_fields": [61], "route": [100,101,102,103,104,105,106,115,116],
 "stock_fields": [100,101,102,103,104,105,106,115,116,61],
 "members": {"31220": 100, "...": "...", "31237": 117}, "names": {"31220": "O2_AT_MSA", "...": "..."},
 "text_block": 33, "recovery": 4600,
 "cut_start": true,
 "start_first": {"donor": 100, "m": 1, "src": "eb", "sid": 0, "tag": 0, "ip": 30, "off": 16, "op": ":=",
                 "target": "Global.Bit[191]", "value": 0, "what": "100's Main_Init: its first store"},
 "start_residue": [[0, 0, 232], [1, 0, 3], [2, 0, 102]],
 "residue_after_start": [],
 "ladder": ["4.2"], "sc_bytes": [0, 1], "sc_order": true,
 "chain": ["4.3"], "entrance_bytes": [2, 3],
 "writes": ["4.4"], "start_dependent": ["4.5"], "noise": ["4.6"], "forbidden": ["4.7"],
 "end_state": {"Global.UInt16[0]": 1155, "Global.Int16[2]": 0, "Global.UInt16[19]": 2, "Global.UInt16[21]": 2,
               "Global.Byte[6]": 2, "Global.Byte[472]": 4, "Global.Int16[469]": 1042,
               "Global.Bit[3717]": 1, "Global.Bit[3718]": 1},
 "regions": {"2.5": "..."}, "hotspots": {"2.5": "..."}, "table": ["2.4"], "choices": ["2.6"],
 "naming": [{"donor": 116, "sc": 1155, "beat": "named"}],
 "beats": ["booth","ticket","fake","alright","clear","understand","named","climbed"],
 "steps_default": {"attempts": 2, "interrupts": 1, "timeout_s": 20, "confirm_s": 4.0, "npcs": true,
                   "overlay_ok": false, "immediate": false, "settle": null, "lunge_ticks": 0,
                   "tolerance": 45, "min_depth": 40, "exit_wait_s": 8.0, "exit_slack": 40,
                   "climb": {"burst_frames": 30, "max_bursts": 80, "stall_bursts": 3}}}
```

- `start_residue` is `[byte, old, new]` for exactly the warp's three residue rows (0.2 #13).
- `residue_after_start` is the registered post-start residue: empty until R-FULL shows otherwise, with a byte-level
  explanation (F6, F9).
- `end_state` is the research's expected end state on arrival in 61 (o2_route.md "End state"), plus UInt16[19]. The
  driver reads it through `watch`ed bits (2.2, rule 1), and O2-STATE compares it.

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

A key has O1's shape plus a MANDATORY `op`: `{"donor", "m": 1, "src": "eb", "sid", "tag", "ip", "off", "target",
"value", "op", "what"}`.
- `ip` is the trace's entry-relative ip and `off` the offset inside the function, both from the reconciler's listing
  (`e.. t.. ip.. L..`).
- `op` is one of `:=`, `|=`, `&=`, `++`. A compound op also names its `prior`: another registered key (by its
  `donor/sid/tag/ip`) or `"newgame0"` (New Game's zero, which R-FULL's rows witness as their `old`, F6).

The draft hard-codes them, as O1 did. O2-KEYS re-derives each: it joins a synthetic row against the stock bytes, and it
COMPUTES the value from the op and the prior instead of trusting the typed one (6.1). The claim-integrity critic
re-derived all 48 drafted sites against the stock US bytes and found none wrong; the computation keeps it so.

### 4.2 The SC ladder (`Global.UInt16[0]`; O2-LADDER)
| # | donor | sid | tag | ip | off | op | value | when |
|---|---|---|---|---|---|---|---|---|
| 1 | 104 | 7 | 1 | 1046 | 546 | := | 1150 | Stage 4, about 20 frames after 254 "Nooooo!" opens. Guard ip964. |
| 2 | 105 | 3 | 1 | 511 | 362 | := | 1151 | Stage 4, after choice 305 and 308/309. |
| 3 | 105 | 14 | 1 | 2818 | 2274 | := | 1152 | Stage 14, before EnableMove ip2859. |
| 4 | 106 | 2 | 1 | 312 | 221 | := | 1153 | Puck at (800,1800) and the player within 1400 (ip210). |
| 5 | 115 | 1 | 1 | 462 | 244 | := | 1154 | Stage 1, after 353. |
| 6 | 115 | 1 | 1 | 1683 | 1465 | := | 1155 | Stage 9, after 383. |

The rungs must appear in this order. Each row's `old` is the previous rung; the first is 1000, the warp's scenario.
There is no other store to bytes 0-1:
- O2-LADDER selects rows by BYTE SPAN, every kept `w` row whose bytes overlap `sc_bytes`, whatever its width or
  target name. So a store to SC through another width is counted too.
- Residue on bytes 0-1 after the start is O2-RESIDUE's.
- Besides these six, the only SC stores in 100-106, 115, 116 and 61 are the debug overwrites (e.g. 105 e3 t1 ip497,
  "Error Set Scenario Counter"), each behind `SC > value`, which is false on the route. No store in the route fields
  writes bytes 0-3 through any other width (a census of the listings: 12 UInt16[0] and 42 Int16[2] stores, nothing
  else).

### 4.3 The FieldEntrance chain (`Global.Int16[2]`; O2-CHAIN, in order; the first `old` is 102, the warp's entrance)
Every row's `op` is `:=`. O2-CHAIN selects rows by byte span over `entrance_bytes` (2-3), as LADDER does.

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
| donor | sid | tag | ip | off | target | value | op (prior) |
|---|---|---|---|---|---|---|---|
| 100 | 19 | 1 | 834 | 151 | Byte[8] | 125 | := |
| 100 | 19 | 1 | 981 | 298 | UInt16[21] | 2 | := (party: Vivi only) |
| 100 | 19 | 1 | 1066 | 383 | Byte[303] | 0 | := |
| 100 | 19 | 1 | 1100 | 417 | Byte[303] | 1 | ++ (100/19/1/1066: 0 + 1) |
| 100 | 19 | 1 | 1497 | 814 | Byte[4] | 0 | := |
| 100 | 19 | 1 | 1531 | 848 | UInt16[19] | 2 | \|= 2 (newgame0: 0 \| 2; START-DEPENDENT, 4.5) |
| 100 | 19 | 1 | 1562 | 879 | Byte[4] | 0 | := |
| 100 | 19 | 1 | 1570 | 887 | Byte[17] | 0 | := |
| 100 | 19 | 1 | 1578 | 895 | Byte[18] | 1 | := |
| 100 | 1 | 18 | 579 | 143 | Bit[3718] | 1 | := (the Rat Kid) |
| 101 | 7 | 1 | 319 | 152 | Bit[3717] | 1 | := (the Herald) |
| 103 | 0 | 0 | 367 | 357 | Byte[8] | 125 | := (both visits: one key) |
| 103 | 18 | 1 | 218 | 15 | Byte[472] | 1 | := (Hippaul, first visit) |
| 104 | 7 | 0 | 313 | 299 | Int16[469] | 1042 | := |
| 104 | 7 | 0 | 333 | 319 | Int16[469] | 1043 | \|= 1 (104/7/0/313: 1042 \| 1; SC < 1150) |
| 104 | 7 | 1 | 613 | 113 | Int16[469] | 1042 | &= 8190 (104/7/0/333: 1043 & 8190; the ticket pick) |
| 104 | 7 | 1 | 955 | 455 | Byte[472] | 4 | := (guard < 4) |
| 103 | 22 | 2 | 205 | 175 | Byte[13] | 3 | := (the exit's music write) |
| 103 | 22 | 2 | 244 | 214 | Byte[14] | 3 | := |
| 106 | 5 | 0 | 109 | 91 | Bit[3712] | 0 | := (Ilia's init) |
| 106 | 14 | 2 | 194 | 164 | Byte[13] | 3 | := |
| 115 | 0 | 0 | 467 | 453 | Byte[8] | 125 | := |
| 116 | 0 | 0 | 335 | 321 | Byte[8] | 125 | := |
| 116 | 2 | 1 | 765 | 646 | Byte[6] | 2 | \|= 2 (newgame0: 0 \| 2; after `Menu(1,1)`; START-DEPENDENT, 4.5) |
| 116 | 2 | 1 | 1469 | 1350 | Byte[8] | 0 | := |
| 116 | 2 | 1 | 1666 | 1547 | Byte[13] | 3 | := |

Every target is `Global.<width>[<index>]`: a bit's index is the bit, any other width's is the first byte. None lies in
the story-noise mask (O2-KEYS checks it).

**The ambient prologues are not registered here, and NULL does not see all of them.**
- `Bit[191]` and `Bit[184]` are story noise (`boot_scratch` and `field_menu_guard`, flags.STORY_NOISE_REGION_NAMES).
  The digest drops them before keying (storytrace.py:815-819), so NULL never compares them. `start_first` is itself one
  of them, which is why O2-START reads it on the RAW rows. The masked counts are reported per side, and O2-MASKED
  compares their region names.
- `Int16[9]`, `Byte[13]:=1`, `Int16[11]`, `Byte[14]` and the tails (o2_route.md's table) are keyed and deterministic,
  and NULL compares them key for key.

The first version said NULL compared all of them key for key. It does not.

### 4.5 Start-dependent keys
These are compared stock against fork like any key; both sides start alike. They are declared so that no reader takes
O2's value for the value a real O1 -> O2 play writes:
```json
[{"donor": 100, "sid": 19, "tag": 1, "ip": 1531, "off": 848, "target": "Global.UInt16[19]", "value": 2, "op": "|=",
  "prior": "newgame0", "after_o1": 1799, "why": "UInt16[19] |= 2 on New Game's 0; after O1 it holds 1797 (bits 1, 4, 256, 512, 1024)"},
 {"donor": 116, "sid": 2, "tag": 1, "ip": 765, "off": 646, "target": "Global.Byte[6]", "value": 2, "op": "|=",
  "prior": "newgame0", "after_o1": 3, "why": "Byte[6] |= 2 on New Game's 0; after O1 it holds 1 (50 e17 ip3240)"}]
```
Both are also rows of 4.4 at these values, so O2-WRITES and O2-NULL judge them. The report prints them with `after_o1`,
under the line "start dependence of gEventGlobal values only: party data, cards and field 70's override state are not
covered" (0.2 #8).

### 4.6 Noise: the minimal set, one key, strictly shaped
```json
[{"donor": 103, "m": 1, "src": "eb", "sid": 18, "tag": 1, "off": 51, "target": "Global.Byte[472]", "value": 2,
  "ip": 254, "op": ":=",
  "why": "Hippaul's :=2 (103 e18 t1 ip254) runs only if his three legs at speed 15 (about 6600u) end before 103 unloads; 104 writes :=4 either way (e7 t1 ip955, guard < 4), so it never propagates"}]
```
**`key_matches(k, p)`**:
- An O2 noise pattern names EXACTLY the 8 WriteKey fields (`donor, m, src, sid, tag, off, target, value`) plus the
  metadata `ip`, `op` and `why`. `ip` and `op` are for O2-KEYS, which needs `ip` to build its row.
- Matching compares the 8 fields and requires `k.aligned`.
- Any other key raises. So a typo such as `offset` is an error, never a silently wider match, and a pattern without
  `ip` cannot pass O2-KEYS.
- No operators (ranges, lists) are allowed in noise. Only forbidden patterns (4.7) may use `ip_range` and `off_route`.

**`is_noise(k, pred)`** accepts two shapes, told apart by their key sets:
- O1's legacy `{not_m, target, why}` (`k.m != p["not_m"] and k.target == p["target"]`), so O1's v4 reads as before;
- O2's full-key form above.

Any third shape raises.

What is deliberately NOT noise:
- **Ilia's `Bit[3712]:=1`** (106 e5 t1 ip165) waits WHILE z < 2200, armed only after Puck's ip520. The route never
  walks back north, so it never fires (the critic). Registering it would hide a real walk or fork divergence.
- **Jack, the hot-spots, Kupo, 104's info options and 115 e17 t12** are forbidden (4.7). A backed hit makes the run
  VOID; an unbacked one is a finding. None is ever "unstable".
- **Nothing else on the route is random or timing-bound** (research nondeterminism 1-8). The R-FULL traces are the
  test (7.3 F6): a key that differs between R-FULL runs and is not registered stops the freeze until it is explained at
  the byte level.

### 4.7 Forbidden: patterns, backing, and what a hit means
The patterns match RAW `w` rows, never digest keys. The digest drops masked sites before keying: Kupo's talk
(115 e2 t3) stores only masked bytes (Bit[184], Bit[189], the mognet mailbox 1024-1045) on every path but case 202's
`Bit[3784]:=1` (ip1023), so a key-level scan misses it. The digest also files seam rows apart from its keys. So the
scan reads every kept `w` row: masked sites, seam rows and every mode included.

The scan window is the same live and in the analysis: from the run's START ROW (the first `w` row in the start place)
to the end cut. The warp's residue is never scanned: residue rows are `r`, and they sit before the start row.

A row's place is `place(fld, members)` (the frozen members map), not the engine's `don`.

```json
[{"donor": 105, "sid": 7, "tag": 2, "cause": "contact", "object": 7,
  "why": "Alleyway Jack's contact ran (the mugging or the card tutorial)"},
 {"target": "Global.Bit[3714]", "cause": "contact", "object": 7, "why": "Jack's card branch (105 e7 t2 ip729)"},
 {"target": "Global.Bit[3715]", "cause": "contact", "object": 7, "why": "Jack's mugging branch (105 e7 t2 ip945)"},
 {"target": "Global.Int16[220]", "cause": "confirm_hotspot", "why": "a hot-spot pickup: a stray Confirm"},
 {"target": "Global.Int16[222]", "cause": "confirm_hotspot", "why": "a hot-spot pickup: a stray Confirm"},
 {"target": "Global.Int16[224]", "cause": "confirm_hotspot", "why": "a hot-spot pickup: a stray Confirm"},
 {"target": "Global.Int16[228]", "cause": "confirm_hotspot", "why": "a hot-spot pickup (the player's pickup function)"},
 {"target": "Global.Byte[226]", "cause": "confirm_hotspot", "why": "a hot-spot pickup (the player's pickup function)"},
 {"donor": 115, "sid": 2, "tag": 3, "cause": "confirm_talk", "object": 2, "why": "Kupo's talk (Mognet/save/shop): a stray Confirm"},
 {"donor": 104, "sid": 7, "tag": 1, "target": "Global.Int16[469]", "ip_range": [646, 863], "cause": "choice",
  "why": "a 104 info option was chosen (e7 t1 ip646-863)"},
 {"off_route": true, "cause": "walk",
  "why": "a write off the route: S, a place outside route + end_fields; F, a field that is neither a member whose donor is on the route nor an end field"}]
```
The schema is strict: the keys are `donor, sid, tag, target, ip_range, off_route, cause, object, why`, and any other
raises. `ip_range` is on the raw entry-relative `ip`, which O2-BUILD proves equal on both sides: the verbatim fork's
`.eb` is the donor's with same-length operand remaps. So the live scan needs no join.

**The backing rule** (`segment_drive.backing(hit, log, pred)`, shared by the driver and the analysis): a hit is BACKED
only when the run's own driver log, at a frame before the hit's row frame (trace `f` and state `frame` are both
`Time.frameCount`), holds the stray action its `cause` names:

| cause | backed when |
|---|---|
| `contact` | a `watch` row with control held and the player within the object's published `range_r` of it, plus 150u: what Vivi (60u a tick) and Jack (15u) can close in the two field ticks between published samples. The rows are the driver's polls and the StateRing samples of 2.2. |
| `confirm_hotspot` | a `press` row with control held at `pre` or `post`, in the hit's place and visit, standing within reach + 64u of the hot-spot the hit names. The hot-spot is identified by the same run's `Int16[220]`/`[222]` values at the hit (s16), matched to 2.5's `hotspots` of that place; the 64u covers a moving sample's lag. With no such pair, or a position that is no registered hot-spot, the hit is unbacked. |
| `confirm_talk` | a `press` row with control held whose `near` lists the object's `talk` disc. |
| `choice` | a `choice` row in that place whose taken index is not its rule's pick, or any cursor step. The driver takes defaults only (V3), so this is backed only by a driver fault. |
| `walk` | a `step` row whose crossing landed off the route (its V11 was a step outcome). A scripted transition off the route is unbacked. |

**What a hit means:**
- **Backed**: a walk divergence the driver caused. Live, it is V12 (the run stops). In the analysis, the run is not
  covered: "walk divergence: <why>, backed by <evidence>".
- **Unbacked**: a finding. Live, the hit is logged and the run goes on. In the analysis, it never uncovers a run, and
  O2-FORBIDDEN FAILS listing it, judged over EVERY run with a readable trace, covered or not.

  Examples: a fork 106 that writes a hot-spot key by itself; a live dormant e14 in 115 (a card event from e17 t12,
  which names no hot-spot); a fork member whose `Field()` left the chain; Jack's contact with no sample of him in reach.
  Each of these is a fork difference the instrument must report, never a VOID it hides behind.

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
1153, must show in the trace (O2-WRITES, O2-NULL, O2-LADDER, O2-STATE) or as a VOID with its class (V8, game-caused,
which O2-VOID-ASYM reads), never as a quietly uncovered run.

### 4.9 Budget and recovery
O1 ran about 3.5 minutes and was budgeted 720 s. O2 is roughly 3x longer. It has:
- 10 field visits and mbg101;
- about 70 pages and 6 choices;
- the naming screen and the climb;
- about 53,000u of walking.

The estimate is 8-12 minutes a run. The draft budget is `run_s 1800`, `run_min_s 1200`, `session_s 14400` (6 runs + 2
re-runs at about 15 minutes, with slack), `settle_s 1.0` and `no_progress_s 120`. The watchdog makes a hang cost 120 s
instead of 1800. Freeze item F7 replaces all five from the rehearsal timings. Recovery is `end_run`: warp to 4600
first, then the soft reset; freeze item F8 proves it from 61. `recovery: 4600` (registered today in
FF9CustomMap-world), and P-RECOVERY checks it.

---

## 5. Checks (O2's analysis)

### 5.1 Reading a run: the COVERED rule
A run is covered when all of O1's reasons are absent (o1:630-656):
- skipped;
- the install changed;
- the drive did not reach the end;
- a beat not done;
- no trace, or a trace unreadable or incomplete.

O2 adds three reasons:
- **No start.** The front cut found no `w` row in the start place: "never reached the start field".
- **A BACKED forbidden hit** (4.7): "walk divergence: <why> (<row>), backed by <evidence>", one per hit. An unbacked hit
  is not a reason here; it is O2-FORBIDDEN's.
- **The engine's donor mapping disagrees with the frozen members** (`digest.mismatched` non-empty): "member <m>'s rows
  name donor <d>, the frozen members say <d'>". The first version left this a note.

Each reason carries a class (`A-NOSTART`, `A-FORBIDDEN`, `A-MISMATCH`, `A-BEATS`, `A-TRACE`, `A-INSTALL`, all
attributed `driver`: they are the instrument's or the driver's), and a VOID drive carries its V-class. The report lists
every uncovered run's reasons per side.

### 5.2 The cuts (frozen places everywhere)
- **`cut_at_end(rows, end_places, members)`** is O1's rule, on frozen places. Kept: every row before the first `w`/`r`
  row whose place is an end place, plus every `e` row, plus every `c` row whose site's place is not an end place. For
  O1 (end 100, no member) this is O1's `fld` rule exactly.
- **`cut_at_start(rows, start_place, members)`** is new.
  - `at` is the first `w` row whose place is the start place (100). A `w` row, never an `r` row: a residue row landing
    in 100 cannot become `at` and leave the residue unjudged among the kept rows.
  - Rows before `at`, except `e` rows, are removed and returned as `pre`. So are the `c` rows whose site appears only
    among the removed rows (field 70's).
  - It returns `(kept, at, pre)`. Without `cut_start`, nothing is cut: O1 is unchanged.

### 5.3 The checks, in order
**All-run checks** (every run with a readable trace, judged even when COVER is short):
- **O2-FORBIDDEN:** no run carries an UNBACKED forbidden hit (4.7). It lists each: the run, the row (`fld`/place/`sid`/
  `tag`/`ip`/target/`new`), the pattern's `why`, and why unbacked.
- **O2-VOID-ASYM:** the VOID classes are read per side (a drive's V-class with its cell, or its place outside a cell,
  2.7; the analysis's A-classes, 5.1). It FAILS when either holds:
  - (a) a `game`-attributed class occurs in some run of one side and in no run of the other side;
  - (b) every run of one side is VOID in the same class while the other side has at least `min_covered` covered runs.

  (b) catches, for example, every F run V8 at (106, 1152) while the stock runs are covered: a fork 106 that never
  publishes 1153 must read NOT PROVEN, never VOID. A driver-attributed class on one side only (a lost race, a stall)
  fails only under (b).

**Then as O1:**
- **O2-FROZEN:** the predictions sha is the session's.
- **O2-COVER:** at least 2 covered runs a side, with every uncovered run's reasons per side. Too few makes every core
  check below VOID ("too few covered runs"), as in O1; the all-run checks above stand.

**Core checks** (over the covered runs):
- **O2-START:** every covered run starts at the start field's Main_Init, after only the warp's own residue.
  - (a) `pre` is EXACTLY the three residue rows of `start_residue`: kind `r`, `(byte, old, new)` equal as a set. The
    first version only required `r` rows on bytes 0-3.
  - (b) the first `w` row from `at` is `start_first` (place 100, e0 t0 ip30, `Global.Bit[191]`, new 0), read on RAW
    rows, since Bit[191] is masked in the digest.
- **O2-LADDER:** every covered run's kept `w` rows whose bytes overlap `sc_bytes` (0-1), of any width, target, mode or
  source, are exactly the six rungs of 4.2 in line order. Each row is compared on its JOINED key (`row_keys`: the
  digest's own `Observed.row.site -> WriteKey`, so donor through the frozen members and `off` as the digest aligned
  it), never the raw `ip`. Each `old` is the previous rung, the first 1000. A row with no key (a join failure) fails by
  name. A `c` row whose site overlaps those bytes fails too: the engine emits a site's value changes (64 an epoch) and
  its first same-value store, and only counts the rest (StoryTrace.cs:383-400), so a suppressed repeat is visible only
  there. Every rung is a change at its own site, so none is expected.
- **O2-CHAIN:** the same test over `entrance_bytes` (2-3) with 4.3; the first `old` is 102.
- **O2-RESIDUE:** every covered run's residue rows from `at` on, outside the story-noise mask, equal
  `residue_after_start` (registered empty): `(byte, new)` as a set, the same in every covered run of both sides. Masked
  residue is counted in the report.
- **O2-WRITES:** every covered run of both sides writes every registered story key: each 4.4 key is in every covered
  run's digest keys (a seam key is not a key).
- **O2-NULL:** STOCK ONLY and FORK ONLY are empty outside the registered noise. `T.compare(S, F, members)`, with the
  noise set aside by `is_noise`.
- **O2-STABLE:** no key outside the registered noise is written in some runs of a side and not others.
- **O2-SEAM:** the fork side never left its members before the end.
  - Every covered fork digest has empty `seam_keys`, and `c.across_seam` and `c.seam_only` are empty.
  - Every recorded Seam is exactly member(116) = 31236 -> real 61. O1's digests record their one seam from the kept
    `off` row the same way.

  NULL cannot see a seam leak: `Comparison.stock_only` leaves out every key with a seam count (storytrace.py:1076).
- **O2-MASKED:** the story-noise region names written per side (`digest.masked`). It FAILS when a region is written in
  some covered run of one side and in no covered run of the other; the counts per side are always reported.
- **O2-STATE:** the state handed to 61 is the same.
  - (a) Each unmasked target's write history at the cut is identical across every covered run of both sides, outside
    the noise keys. The history is its emitted rows' keys in line order, plus each suppressed site's `last`. The counts
    are left out: a loop's count can vary with timing. The history contains the final value, and it catches the same
    key set written in a different order, which NULL (sets) cannot.
  - (b) Every covered run's `end_state`, read live on arrival in 61 (2.2, rule 1), equals the frozen `end_state`.
- **O2-JOIN:** every script row joins a store in the bytes its field ran.
- **O2-THROW:** nothing is thrown through EventEngine, EBin, StoryTrace or HarnessAgent (O1's rule, in `run`).

**VERDICT:** `PROVEN`, `NOT PROVEN: <failed checks>` or `VOID: <void checks>`. This is O1's `verdict()`: a failed check
outranks a void one, so O2-FORBIDDEN and O2-VOID-ASYM can make a short session NOT PROVEN.

**Report-only,** after O1's body, with its title line, per-run lines and `T.report`:
- the start-dependent keys, with their values on both sides and `after_o1`, under 4.5's scope line;
- the SC timeline per covered run: the frame of each rung, and the deltas;
- the steps table per run: cell, step, attempts, interrupts, seconds, `lost`, the id-flip latency, lunge and climb
  records;
- the VOID reasons per side: class, cell, `by`, why;
- the masked region counts per side, and the masked residue count;
- the forbidden hits per run, each with its backing (or why unbacked);
- the KNOWN-KIT-DEFECT lines P-TEXT reported (6.2);
- the dialogue per covered fork run against the first covered stock run, with `timed` pages removed and consecutive
  duplicates collapsed. This is O1's lesson: self-closing windows stack and are sampled at varying moments.

---

## 6. Offline check and preflight

### 6.1 `--offline-check` (reads the install and the build; writes nothing; must be green before any rehearsal ends in a freeze)
- **O2-BUILD:** every member's `.eb`, in all 7 languages, is `remap_fields(stock donor .eb in that language, retarget)`
  (`Segment.build_check`, `accept_us_build=False`). Measured today: 126/126.
- **O2-TEXT:** the lead's ruling, as `text_rule`.
  - The reference is each language's stock asset read by its ResourceManager path: `mainData`'s `m_Container` entry
    `embeddedasset/text/<lang>/field/33.mes`, resolved into `resources.assets`, the way
    `battle.extract._read_battle_text` reads battle text. Never `dialogue.extract_field_mes*`.
  - For each language, the build's `FF9_Data/embeddedasset/text/<lang>/field/33.mes` is:
    - byte-equal to that reference: ok;
    - if the language is the session language (`lang`, us) and it differs: FAIL;
    - for any other language, if it differs but is byte-equal to ANOTHER language's stock asset: a KNOWN-KIT-DEFECT
      line, named and counted ("uk ships stock us (4751874951; stock uk 8c94536b6c): dialogue._lang_score aliases uk to
      us, dialogue.py:374 -- the lead's kit fix");
    - any other difference: FAIL.
  - The check passes when there is no FAIL. Its detail always leads with the KNOWN-KIT-DEFECT count, and the CLI prints
    each defect on its own `KNOWN-KIT-DEFECT` line.
  - Measured today: 6 byte-equal, KNOWN-KIT-DEFECT 1 (uk), FAIL 0. After the lead's kit fix and a rebuild, it reads 7
    byte-equal and 0 defects with no code change here.
- **O2-KEYS:** O1's `keys_check` extended. Its keys are every key of `ladder`, `chain`, `writes`, `start_dependent`,
  `noise` and `start_first`, plus the two concrete forbidden sites (105 e7 t2 ip729 off 175 `Bit[3714]`; ip945 off 391
  `Bit[3715]`): 48 sites.
  - Each is a store of its variable at `(sid, tag, ip)` with rel == `off` (build a `T.Row` and `ScriptIndex.join`, with
    `status == "store"`).
  - Its `op` is mandatory, and the statement at `off` (`ScriptIndex.text_at`) carries it, anchored on the target:
    `Global.<W>[<i>] const(<c>) B_LET` for `:=` (with c == value), `Global.<W>[<i>] const(<c>) B_OR_LET` / `B_AND_LET`
    for `|=` / `&=`, and `Global.<W>[<i>] B_POST_PLUS` for `++`. These forms were read today at 100/19/1 off 417 and
    848, 104/7/0 off 319, 104/7/1 off 113 and 116/2/1 off 646.
  - A compound key's value is COMPUTED from its `prior` (the prior key's value, or 0 for `newgame0`) and the constant,
    and must equal the frozen value: 1042|1 = 1043, 1043&8190 = 1042, 0+1 = 1, 0|2 = 2.
  - No key's target lies in the story-noise mask (`T.noise_regions` of its synthetic row is empty).
- **O2-REGIONS:** every frozen region's points equal the first `SetRegion` of `(donor, entry)` in the stock bytes
  (`eventscan._region_points`, or a public `scan_regions` if the implementer adds one). Each role holds:
  - `exit`: `scan_gateways` has a row for that entry with `to` and the entrance, and `face_gate` as frozen;
  - `dormant` (115.e14): no `InitRegion(14)` on Main_Init's path for entrances 213-215;
  - `walkin` (105.e12): its tag 2 opens with the `1150 <= SC < 1152` guard.

  And every frozen hot-spot's `x`, `z` and `n` equal its tag 1's `Int16[220]`/`[222]` store constants and its
  `Instance.Int24[0] const(n) B_LT` compare. The census is 17 hot-spots in the route fields; a hot-spot entry in the
  bytes that is missing from `hotspots` fails.
- **O2-GOALS:** for every table step, on `PlayerWalkmesh(stock_walkmesh(donor), closed=...)`:
  - the goal is on the floor, with `distance_to_boundary >= 80`;
  - a `target` step's goal is inside the target (`doorface.region_contains`) with depth >= 80; an `until` step's goal
    satisfies its predicate;
  - a `confirm` step's `depth(goal) - tolerance >= min_depth`: the booth 200 - 45 = 155, the ladder 90 - 45 = 45;
  - the goal and the step's `start` stand farther than reach + tolerance + 64 from every hot-spot of that field, the
    offline twin of the backing rule (today the nearest is 469u beyond a reach);
  - `pathfind.route_avoiding(start, goal, polys(avoid), leave_wall=True)` exists.

  Section 2.4's numbers are today's run of exactly this.

### 6.2 `--preflight` (the live install, read-only; red until the owner-gated deploy, which is expected)
- **P-MANIFEST:** `o2_forks.json` members == the predictions', `deployed: true`.
- **P-DEPLOY:** each member is registered once under its name, and has one ForkDonorPatch row to its donor.
- **P-EB:** each member's live `.eb` in 7 languages equals the build's.
- **P-FLOOR:** each member's deployed walkmesh is its donor's.
- **P-STOCK:** no mod folder overrides stock 100-106, 115, 116 or 61.
- **P-TEXT (new):** `text_rule` on every mod folder's `FF9_Data/embeddedasset/text/<lang>/field/33.mes`, where present,
  against the same ResourceManager-path references. None present passes ("no mod folder ships block 33": today). After
  the deploy FF9CustomMap ships all 7, and with today's build P-TEXT passes with the uk KNOWN-KIT-DEFECT line, which
  the session report repeats.
- **P-RECOVERY (new):** 4600 is registered in some mod folder (today FF9CustomMap-world).
- **In game only** (`capabilities`):
  - P-CAP: storytrace proto 1.
  - P-OBJECTS: `objects_status != "cannot"`. This is s89, needed for `npcs`, V6 and the `near` evidence.
  - **P-LANG (new):** the running game's text is English(US), the language the keys, joins and text were checked in.
    This launch's Memoria.log (`g._log_paths()`; the log is rewritten at launch) must have, as its last "Updating text
    localization [<name>]" line (FF9TextTool.cs:395), `English(US)`. And Memoria.ini `[VoiceActing] ForceLanguage` must
    be -1 or 0. Today: English(US), -1.

### 6.3 The fingerprint (per run, before and after, as O1)
O1's keys, plus:
- `"override70"`: `{folder: sha of field 70's .eb, us}` for every folder that ships one. Today that is
  FF9CustomMap-world's New-Game override.
- `"text33"`: `{folder: {lang: sha}}` of every `field/33.mes`.
- `"lang"`: `{"log": <the last localization line's name>, "force": <ForceLanguage>}`.

Another session re-wiring New Game, touching block 33, or a language change mid-session makes the runs VOID; it can
never skew them.

### 6.4 `o2_forks.json` (the implementer writes it; the lead flips `deployed` after the owner-gated deploy)
It mirrors `o1_forks.json`:
- `what`;
- `import`: the command in 0.1, `--mod-folder FF9CustomMap --out C:/gd/_ns_playtest/o2/fork`;
- `build`: `py -m ff9mapkit build-all C:/gd/_ns_playtest/o2/fork/campaign.toml --out C:/gd/_ns_playtest/o2/build`;
- `deploy`: one member at a time, in id order, `tools/deploy_field.py <member>.field.toml --id <fork id> --name <name>
  --mod-folder FF9CustomMap`;
- `members` and `names` (4.1);
- `text_block: 33`, `deployed: false`, `relaunch_needed: true` (18 FieldScene ids and 18 ForkDonorPatch rows);
- `known_defects`: `["uk/field/33.mes is stock us (dialogue._lang_score aliases uk to us); the lead's kit fix and a
  rebuild should land before the deploy: deployed as built, UK players see US text in stock 100-117"]`;
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

**What a stage may settle.** Only R-FULL traces may define or change the ladder, the chain, the writes, the noise, the
start residue or `end_state`. The staged runs start at other SC values and entrances, and write keys the route never
writes: 115 at SC 1155 writes `Int16[2]:=215` at ip287, which is not in the chain. So staged runs prove driver
mechanics only (the claim-integrity critique #12).

| Stage | Warp | Ends in | Runs | What it settles |
|---|---|---|---|---|
| R-115 | `warp 115 215 1155` (Main_Init rewrites the entrance to 215 at ip287: stage 10 with control, spawn (257,-2500)) | 116 | 3 | Does `hold up` reach B_KEY(16)? The climb: y per burst, frames to the top. |
| R-115a | `warp 115 213 1153` (Main_Init on SC 1153 sets `Int16[2]:=213` at ip249: stage 1) | 116 | 2 | The whole 115 scene as the route plays it: the (115, 1154) ladder confirm, about 25 pages, choice 367, stage 10's REAL control grant (where stage 5 walked him) with Kupo in his route state, then the climb. F10 reads the grant from it. |
| R-105 | `warp 105 205 1150` | 106 | 5 (Jack's legs take SYSVAR[0] offsets) | Jack and the leave-now exit; choices 305/310/314; e12; e11's fade race |
| R-106 | `warp 106 111 1152` | 115 | 2 | The wait point, Puck, SC 1153, the hints, e14's fade (control lost 8-16 ticks before the fade ends) |
| R-116 | `warp 116 0 1155` | 61 | 2 | The three triggers, Puck's pace, the naming, the end-state read, end_run from 61 |
| R-FULL | `warp 100 102 1000` | 61 | 2 | Everything in sequence, plus mbg101, the Rat Kid, the Herald, 102, the booth and 215's publication, 104 and 251's publication, Hippaul's ip254, the second 103 visit, the start residue, the end state, the total time. The only stage whose traces define predictions. |
| R-103 (optional) | `warp 103 203 1000` | 105 | 1-2 | A cheaper iteration on the booth, 104 and the second 103 visit |

### 7.2 What every stage records (`observe` plus the driver's own log)
- **Control grants:** `{t, frame, field, sc, x, z, y, fps}`. Every step's `start` in 2.4 is checked against these.
- **Steps:** the 2.3 log rows, including the route records, `lost` with the frame the id flipped, the lunge
  (`sample_frame`, `done_frame`, travel) and the climb (`ys`, `frames`, `ended`).
- **Choices:** the full published choice (`options`, `active`, `selected` at readiness, `count`), the rule picked and
  the frame. This covers 215's first-character drop and 251's masked lines.
- **Pages:** the text, `raw_texts`, whether timed, and the frame.
- **Evidence:** the `press` and `watch` rows (2.2), as a session keeps them.
- **NPC tracks** (`st.objects`, every sample, in these cells only): 105 sid 7 (Jack) from SC 1152 on; 106 sid 2
  (Puck); 115 sid 2 (Kupo) from stage 10; 116 sid 2 (Puck). Each sample has uid, sid, x, z, moving, r, range_r, talk_r
  and the distance to the player. Summarised per run:
  - the minimum player-to-Jack distance against his published `range_r`;
  - the frame Jack first comes within `range_r` of the lookout;
  - the latency from the control sample to the first held frame to the first position change.
- **The longest no-progress stretch** per run, with where it was (mbg101 included), for F7.
- **mbg101** (R-FULL): the frame from arrival to the first page, and the published fps before, during and after.
- **The end:** the `end_state` read, and `end_run`'s result from 61 (did it reach the title, and how).
- **The trace:** `trace_summary`, i.e. the SC sequence, the Int16[2] sequence, each registered key present or absent,
  and every UNREGISTERED key with its site. Hippaul's ip254 is present or absent, Ilia's ip165 present or absent (it
  must be absent), the residue rows before and after the start, the forbidden hits with their backing, and the JOIN
  failures (which must be 0).

`py studies/story-trace/o2_alexandria.py --rehearsal-report <run dir>` prints all of it, per stage and per run.

### 7.3 The freeze checklist (each item needs its evidence before `--freeze`; record the run dirs in `rehearsals`)
- **F1.** `hold up` climbs: y falls on every burst, and the top is reached in every R-115, R-115a and R-FULL run. If it
  does not, STOP: the agent's input path (IsHeld -> B_KEY) needs a fix, and O2 cannot run.
- **F2.** Jack: every R-105 run leaves 105 with no e7 t2 row and a minimum distance above his published `range_r`. The
  lunge is sized against measurements, not the design's estimate:
  - the measured latency (control sample -> first held frame -> first position change), plus any planning pause after
    the lunge;
  - against the measured contact time: the frame Jack first comes within his published `range_r` of the lookout,
    expected 45-61 ticks (1.5-2.0 s) after control;
  - with at least 0.5 s of margin in every run.

  `lunge_ticks` is 0 if `route_cross(settle=0)` alone clears that margin; otherwise keep 10, or size it to the clear
  segment.
- **F3.** 106: SC 1153 arrives while he waits at (550,2000), and `wait_s` is 3x the slowest wait seen.
- **F4.** Every step is done within its attempts. Any goal a run missed moves, re-checked by O2-GOALS. Every confirm's
  settled depth is at least `min_depth`, and every exit's `lost` sample is at or inside its target.
- **F5.** Every choice publishes a line the rule matches, with `selected` equal to the pick at readiness. This includes
  104's masked 251 (active [0, 1, 4, 10]).
- **F6.** The R-FULL traces define the predictions:
  - the ladder, the chain and every 4.4 key exactly as drafted, with each `newgame0` prior witnessed by its row's `old`
    (0);
  - any key present in one R-FULL run and absent in the other is either Hippaul's ip254 or explained at the byte level
    before the freeze (a new noise entry only with that explanation);
  - any post-start residue is registered in `residue_after_start` only with the same explanation.

  A staged run's trace is compared only with runs of its own stage, to prove that stage's mechanics. It never adds or
  removes a key.
- **F7.** Budget and bounds:
  - `run_s` = 2x the slowest R-FULL, `run_min_s` = 1.25x the median, `session_s` = 8x the median plus 1800;
  - `no_progress_s` = the larger of 120 and 3x the longest no-progress stretch seen in any stage (mbg101 included);
  - `exit_wait_s` = the larger of 5 and 3x the slowest `lost` -> id-flip latency seen.
- **F8.** `end_run` from 61 reaches the title.
- **F9.** R-FULL's rows before the start row are exactly `start_residue`: (0: 0 -> 232), (1: 0 -> 3), (2: 0 -> 102).
  The first `w` row is 100 e0 t0 ip30 `Bit[191]:=0`. Any other pre-start row stops the freeze.
- **F10.** The control-grant positions of 2.4 are confirmed (or corrected), especially (115, 1155) stage 10 from R-115a
  and R-FULL (not R-115's warp spawn), and 116's three grants.
- **F11.** Every R-FULL `end_state` read equals the drafted `end_state`.

After the freeze comes the owner-gated deploy of the 18 members (the lead's kit fix for uk and a rebuild first, 6.4),
the relaunch, `--preflight` green, then the session:
`py tools/play.py studies/story-trace/o2_alexandria.py --label story-o2 --timeout 240`.

---

## 8. The dry run (`o2_dryrun.py`: synthetic sessions through `O2.analyse`)

It is built like `o1_dryrun.py`.
- **Real store sites.** The rows are real store sites of the stock bytes: 4.2-4.4, `start_first`, 61 e0 t0 ip22
  `Bit[191]:=0` (off 16) as the end row, 105 e7 t2 ip945 for Jack, 103 e20 t1 ip175/ip183 (the plaque hot-spot),
  115 e2 t3 for Kupo, and 115 e17 t12 ip2150/ip2205 for the dormant card event. Every row joins.
- **The fork side.** Rows are shifted onto member ids (`fld` = member, `don` = donor).
- **Scripts.** `scripts/<member>.eb` = `remap_fields(stock(donor), retarget)` for all 18.
- **A base run** is:
  - `arm` (fld 70);
  - the residue rows in fld 70 on bytes 0 (0 -> 232), 1 (0 -> 3) and 2 (0 -> 102);
  - `start_first`, then 100's `Bit[184]:=0` (e0 t0 ip57, off 43);
  - the route's registered rows in route order;
  - the 61 row;
  - `off` (fld 61).
- **A log** carries `outcome.pages`, `timed`, the beats, `end_state` (the drafted one), the `step` rows, and, for a VOID
  drive, its `void` class. The backed cases add the `press` / `watch` rows that back them; the unbacked ones do not.

| Case | Want |
|---|---|
| null-pair | PROVEN |
| fork-drops-SC1153 | NOT PROVEN (LADDER F, NULL F, STATE F) |
| SC-out-of-order (1151's row before 1150's, both sides) | NOT PROVEN (LADDER F; NULL P: keys are sets) |
| SC-seventh-write (a debug-overwrite site, e.g. 105 e3 t1 ip497, both sides) | NOT PROVEN (LADDER F) |
| SC-old-not-1000 (the first rung's `old` 0) | NOT PROVEN (LADDER F) |
| chain-out-of-order (rows 6 and 7 swapped, both sides) | NOT PROVEN (CHAIN F) |
| chain-old-not-102 (the first chain row's `old` 0) | NOT PROVEN (CHAIN F) |
| chain-extra (215 answered twice: 103 e30 t1 ip972 twice, stock only) | NOT PROVEN (CHAIN F, STATE F) |
| fork-extra-key / stock-extra-key (a real store off the route: 100 e0 t0 ip105 `Byte[13]:=9`, L91, the ambient-9 branch) | NOT PROVEN (NULL F; LADDER, CHAIN P) |
| writes-missing (no `Bit[3717]` on either side) | NOT PROVEN (WRITES F; NULL P) |
| unstable-outside-noise (Ilia's 106 e5 t1 ip165 `Bit[3712]:=1` in one stock run) | NOT PROVEN (STABLE F, STATE F) |
| hippaul-noise-only (Byte[472]:=2 at off 51 in two F runs and one S run) | PROVEN (NULL P, STABLE P, STATE P) |
| noise-wrong-site (Byte[472]:=2 at off 15, Hippaul's `:=1` site, in two F runs of three) | NOT PROVEN (STABLE F, STATE F) |
| noise-wrong-value (Byte[472]:=3 at off 51 in two F runs of three) | NOT PROVEN (STABLE F, STATE F) |
| start-dependent-equal (UInt16[19]=2, Byte[6]=2 on both sides) | PROVEN, and the report lists both with `after_o1` and 4.5's scope line |
| start-dependent-differs (the fork writes UInt16[19]=1799) | NOT PROVEN (NULL F, WRITES F, STATE F) |
| front-cut-residue (fld-70 residue only before the start) | PROVEN (START P) |
| start-residue-wrong (byte 2's residue 0 -> 101 on the stock side) | NOT PROVEN (START F) |
| front-cut-write (a `w` row in fld 70 before the start, fork only) | NOT PROVEN (START F; NULL P: cut) |
| start-first-missing (100's `Bit[191]:=0` ip30 row dropped on both sides, so the first `w` row in 100 is ip57's `Bit[184]:=0`) | NOT PROVEN (START F; NULL P) |
| residue-after-start (an `r` row on byte 0 after the start, fork only) | NOT PROVEN (RESIDUE F) |
| end-cut (rows in 61 past the end, stock only) | PROVEN |
| end-state-differs (one covered F run's `end_state` has Byte[472] 2) | NOT PROVEN (STATE F) |
| seam-leak (the fork's rows from 115 on filed under the real ids 115/116: the members' `Field()` left real) | NOT PROVEN (SEAM F, WRITES F; NULL P, LADDER P, CHAIN P): NULL alone would pass it, which is the point |
| jack-one-backed (one F run: 105 e7 t2 ip945 `Bit[3715]:=1`, and a `watch` row with Jack within `range_r` before it) | PROVEN, F 2 of 3 covered, that run VOID "walk divergence ... backed" |
| jack-one-unbacked (the same row, no evidence in the log) | NOT PROVEN (FORBIDDEN F); the run stays covered |
| jack-two-backed (two F runs, backed) | VOID (COVER V; VOID-ASYM P: a driver class, not every F run) |
| hotspot-backed (one S run: 103 e20's rows (600,-272), and a `press` row with control within 226+64 of it) | PROVEN, that run VOID |
| hotspot-unbacked (one F run: the same rows, no press) | NOT PROVEN (FORBIDDEN F) |
| dormant-card (every F run: 115 e17 t12's Byte[472]:=4 and Bit[7202]:=1 rows; no hot-spot position) | NOT PROVEN (FORBIDDEN F, NULL F) |
| forbidden-masked (one F run: Kupo's 115 e2 t3 rows on masked bytes only, no press `near` him) | NOT PROVEN (FORBIDDEN F, MASKED F) |
| forbidden-on-seam (one F run: 103 e20's hot-spot rows in REAL 103, across a seam) | NOT PROVEN (FORBIDDEN F, SEAM F) |
| off-route-by-a-step (one S run: rows in donor 112 after a `step` row whose crossing landed there) | PROVEN, that run VOID |
| off-route-scripted (one F run: a V11 drive attributed `game`, with rows in real 112 and no step behind the entry) | NOT PROVEN (FORBIDDEN F, VOID-ASYM F) |
| void-asym-all (every F run a V8 drive at (106, 1152), game; the S runs covered) | NOT PROVEN (VOID-ASYM F; COVER V) |
| void-asym-one (one F run a V4 drive at (104, 1150), game) | NOT PROVEN (VOID-ASYM F; COVER P) |
| mismatched (one F run whose member rows name another donor) | PROVEN, that run VOID (A-MISMATCH) |
| beat-missing (`climbed` False in two S runs) | VOID (COVER V; VOID-ASYM P: A-BEATS is the driver's) |
| no-start-row (one S run whose trace never reaches 100) | PROVEN, that run VOID (A-NOSTART) |
| trace-without-off | VOID |
| install-changed | VOID |
| join-failure (a row one byte off a real store) | NOT PROVEN (JOIN F) |
| predictions-changed | NOT PROVEN (FROZEN F) |

Plus four unit cases that call the checks' helpers directly (no session):
- **span-selector:** a `w` row of `Global.Byte[1]` is selected by LADDER's byte-span filter and fails the ladder. No
  real route site writes bytes 0-3 through another width, so this cannot be a joined session case.
- **text-rule-defect:** `text_rule` with uk = stock us reads ok with KNOWN-KIT-DEFECT 1.
- **text-rule-session:** with us = stock uk it reads FAIL.
- **text-rule-garbage:** with fr = bytes no language has, it reads FAIL.

It prints O1's style of summary line and "N/N cases as registered", and exits 1 on any miss.

---

## 9. Build order, tests, commits (the implementers take PART A, then B, then C; no deploy, no game, no full suite)

Run pytest from `ff9mapkit/`; run the study scripts from the worktree root. A SKIPPED test is not a pass: each
required-green pytest run below must report 0 failed, and its skips and xfails must be exactly the pre-existing ones of
the PART's baseline (take it before the PART's first change). A new skip fails the PART. A failure that passes on an
immediate re-run of that test alone is a timing flake: it is named in the commit message, never ignored.

The whole `tests/test_harness.py` was measured at HEAD 9d0e7780 in this worktree: **574 passed, 1 xfailed, 0 skipped, in
1902 s (about 32 minutes) serially.** That is its baseline for PART B.

Commit on the branch when a step is green, one step per commit. Every commit message ends with
"Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>".

### PART A -- the shared machinery, the O1 refactor, the O1 regression gate
1. **A0: the baseline, FIRST.** Write `segment_regress.py` importing only the O1 modules as they are, and run
   `py studies/story-trace/segment_regress.py --capture`. Commit it with `research/o1_regress_baseline.json` and its
   `.gitattributes` line, before any other code change (1.6 G0).
2. **A1: `segment_drive.RouteVoid` and `pick_for`**, extended per 1.4. `o1_opening` imports and re-exports them.
   - Test: `test_o2_pick_for_scopes_rules_by_sc_and_once`, plus the whole O1 set.
3. **A2: `segment_trace`'s pure helpers**, with unit tests:
   - `place`, `key_matches` / `is_noise` (strict; `test_key_matches_refuses_unknown_fields`,
     `test_is_noise_keeps_o1s_legacy_form`);
   - `cut_at_end` on frozen places and `cut_at_start` (`test_cut_at_start_keeps_residue_out_of_the_kept_rows`,
     `test_cut_at_start_needs_a_w_row_in_the_start_place`);
   - `row_keys` (`test_row_keys_maps_every_joined_row_to_its_digest_key`).
4. **A3: `segment_trace.Segment`**, with `o1_opening` rewritten as `O1Segment` plus wrappers (1.2, 1.3), and
   `all_run_checks` in `judge`.
   - `test_segment_session_loop_on_the_fake`: a stub Segment (preflight, fingerprint and roots stubbed; a drive that
     reaches or VOIDs on cue, with a class) runs S F S F S F on the FakeGame. It checks the session record (the VOID
     class copied), each run's trace and log file, the re-run of a short side, and the finished and report files.
   - `test_segment_throw_check_fails_on_an_engine_exception`: the same loop with `g.exceptions_since` returning a
     NullReferenceException through EventEngine: the THROW check FAILS. This is the mutant the THROW check never had.
   - `test_o1_segment_run_pins_o1s_session_surface`: `O1Segment.run` on the FakeGame, stubbed as above, sends
     `warp 50 0 -1` and `warp 31200 0 -1`, writes `o1_session.json` and `o1_report.txt`, prints `[o1] run 1 (S)`, and
     titles its THROW check with O1's exact text.

**PART A REQUIRED-GREEN** (after A0, and again after each of A1-A3):

| Command | Expected |
|---|---|
| `py studies/story-trace/segment_regress.py` | exit 0; G1-G7 each PASS (G0 is the capture) |
| `py studies/story-trace/o1_dryrun.py` | exit 0; "16/16 cases as registered" |
| `py studies/story-trace/o1_opening.py --analyse C:\gd\Dream-World-IX\.harness-runs\20260929-213149-story-o1e --predictions studies/story-trace/o1_predictions_v4.json` | exit 0; `VERDICT: PROVEN` |
| `py studies/story-trace/o1_opening.py --offline-check` | exit 0; O1-BUILD PASS (140 files; 15 own-language, 105 us-build), O1-KEYS PASS (4 keys) |
| `py -m pytest tests/test_harness.py -q -p no:cacheprovider -W ignore -k "o1_ or overlay_hint or segment or pick_for or key_matches or is_noise or cut_at or row_keys"` | all passed, 0 failed, 0 skipped |

### PART B -- the harness additions and the beat-table driver
1. **B1: H4**, the FakeGame first: the warp's arguments and residue, the ladder model, the region keys (`take`,
   `arrive_control`) and the watched bits, with its three fake tests. The H1 and H2 tests below need these keys.
2. **B2: H1** plus its 4 tests, with `exit_frames = 50` wherever a region warps.
3. **B3: H2** plus its 4 tests.
4. **B4: H3** plus its 3 tests.
5. **B5: H6** plus its test.
6. **B6: H5** (the kit's `content/pathfind.py`, additive) plus its test in `tests/test_route_avoiding.py`. It touches
   the kit: whether the full-suite pre-merge exception applies at merge is the lead's call. This design does not run
   it.
7. **B7: `segment_drive.drive`**, the step executors, the evidence rows, the watchdog, and the shared `forbidden_hits` /
   `backing`, with these FakeGame tests (fields 30810, 30820 and 30821 from the fixture; `exit_frames = 50` in every
   one that crosses):
   - `test_o2_drive_walks_its_table_to_the_end`: a confirm step opens a default-take choice; the answer warps into a
     scene field; a wait_sc step is released by a director setting `scenario`; a cross lands in the end field THROUGH
     the fade; the end state is read. The beats, choices, steps and `end_state` are as expected, and no `up`/`down`
     press is executed.
   - `test_o2_drive_climbs_after_the_ladder_confirm`: H2 through the driver; beat `climbed`.
   - `test_o2_drive_leaves_at_once`: an `immediate` leave_now. The first hold comes within 0.2 s of wall time of the
     control grant; the same cell without `immediate` waits at least `settle_s`. A walking "Jack" object never reaches
     him, and the `watch` rows include the ring's samples from inside the call.
   - `test_o2_drive_cross_waits_out_the_fade_inside_the_exit`: `exit_frames = 50`, with a hint left up (control off) in
     a `no_pages` cell during the fade: `done`, never V5.
   - `test_o2_drive_cross_counts_a_loss_outside_the_exit_as_interrupted`: a director takes control before the exit
     (the bump): `interrupted`, then the step runs again and lands. And a walk that ends with control held and nothing
     crossed is `failed`, then V7 once `attempts` are spent.
   - `test_o2_drive_cross_inside_loss_without_a_field_change_is_interrupted`: an H4 `take` region inside the exit zone,
     listed first: after `exit_wait_s`, `interrupted`; under leave_now, V7.
   - `test_o2_drive_confirm_walks_deep_before_pressing`: the press's `pre` sample stands in the region at depth >=
     `min_depth`; a goal at the region's edge gives `failed` with nothing pressed.
   - `test_o2_drive_counts_steps_per_visit`: three `until` triggers in one cell, each taken by a director at its
     threshold.
   - `test_o2_drive_voids_control_without_a_cell`: V4, class and `by` game.
   - `test_o2_drive_voids_a_once_choice_asked_again`: V2, plus an SC-scoped rule at the wrong SC (V1).
   - `test_o2_drive_voids_when_the_default_is_not_the_pick`: V3; the cursor is left alone.
   - `test_o2_drive_voids_a_page_in_a_no_pages_cell`: V5; no Confirm is executed.
   - `test_o2_drive_voids_a_watched_object_in_reach`: V6.
   - `test_o2_drive_voids_leaving_the_route`: V11 three ways: a cross whose exit lands, through the fade, in a field
     that is not its `to` (`by` driver); a scripted transition into an off-route field (`by` game); and, on the F side,
     a REAL route field reached from a member.
   - `test_o2_drive_live_scan_ignores_the_warp_residue`: H4's warp writes its three residue rows in the old field; the
     scan starts at the start row and does not VOID on them. In the same kind of run, a backed forbidden row after the
     start still VOIDs it (V12).
   - `test_o2_drive_voids_a_backed_forbidden_row`: a `press` with control near a hot-spot, then its rows: V12.
   - `test_o2_drive_logs_an_unbacked_forbidden_row_and_goes_on`: the same rows with no press: a `forbidden` log row
     with `backed: false`, and the run reaches the end.
   - `test_o2_drive_scans_once_more_at_the_end`: a forbidden row written after the last new visit is found before
     `reached`.
   - `test_o2_drive_voids_when_nothing_changes`: V14 with `no_progress_s` set small; the progress signature resets on
     any published change.
   - `test_o2_drive_records_presses_and_watch_samples`: the `press` rows' `pre`/`post`/`near` and the `watch` rows'
     shape.

**PART B REQUIRED-GREEN.** H4 (B1) and H1 (B2) change shared harness verbs, so the WHOLE file runs after each of them,
and once more at the end of PART B (after B7). B3-B6 add new verbs, an accessor and a kit option, so they run the
subset and their own files.

| When | Command | Expected |
|---|---|---|
| after B1, B2 and B7 | `py -m pytest tests/test_harness.py -q -p no:cacheprovider -W ignore` | 574 + the new tests passed, 1 xfailed (the pre-existing one), 0 skipped, 0 failed |
| after B3, B4, B5 and B6 | `py -m pytest tests/test_harness.py -q -p no:cacheprovider -W ignore -k "o1_ or o2_ or segment or climb or lunge or handoff or overlay or fake_ or states_since"` | all passed, 0 skipped, 0 failed |
| after B6 and B7 | `py -m pytest tests/test_route_avoiding.py tests/test_movement.py tests/test_floorplan.py tests/test_floor_aware_sweeps.py tests/test_behavior_autoroute.py -q -p no:cacheprovider -W ignore` (every pathfind user) | all passed, 0 failed; skips identical to the pre-B6 baseline |
| after every B step | `py studies/story-trace/segment_regress.py` | exit 0: the harness changes must not move O1 |

### PART C -- O2 itself
1. **C1: `o2_alexandria.py`**: the draft predictions, `text_rule`, the O2 checks (all-run and core), `why_void`, the
   offline checks, the preflight and P-LANG, `--analyse`, `--draft`, `--freeze`; and `o2_forks.json`; and the
   `.gitattributes` line for `o2_predictions*.json`. Tests:
   - `test_o2_text_rule_*` (the four text cases of section 8 as pytest units);
   - `test_o2_p_lang_reads_the_last_localization_line` (a log whose language changed mid-launch reads the last line;
     English(UK) or a ForceLanguage of 1 fails);
   - `test_o2_freeze_refuses_an_existing_file` (a tmp path, twice);
   - `test_o2_draft_members_are_the_campaigns`.
2. **C2: `o2_dryrun.py`**: every case of section 8 as registered.
3. **C3: `o2_rehearse.py`** plus `--rehearsal-report`. Test: `test_o2_rehearse_plumbing_on_the_fake`: one stage on a
   fake two-field route, where the record file has every section of 7.2.
4. **C4: the O2 section in `PLAN.md`**: the design in brief, "draft: rehearsals pending, freeze pending", the uk
   KNOWN-KIT-DEFECT, and the lead's kit fix as a precondition of the deploy.

**PART C REQUIRED-GREEN** (after each of C1-C4, as far as it exists):

| Command | Expected |
|---|---|
| `py studies/story-trace/o2_alexandria.py --offline-check` | exit 0; 5 PASS: O2-BUILD (126 files, own-language), O2-TEXT (6 byte-equal, KNOWN-KIT-DEFECT 1, FAIL 0, with a printed `KNOWN-KIT-DEFECT` line for uk), O2-KEYS (48 sites, values computed, none masked), O2-REGIONS (26 regions, 17 hot-spots), O2-GOALS (14 steps) |
| `py studies/story-trace/o2_alexandria.py --preflight` | exit 1, and exactly: P-MANIFEST, P-DEPLOY, P-EB, P-FLOOR FAIL (not deployed); P-STOCK, P-TEXT ("no mod folder ships block 33"), P-RECOVERY PASS |
| `py studies/story-trace/o2_alexandria.py --draft` | exit 0; the draft JSON |
| `py studies/story-trace/o2_dryrun.py` | exit 0; "N/N cases as registered" (every case and unit case of section 8) |
| `py studies/story-trace/segment_regress.py` | exit 0 |
| `py -m pytest tests/test_harness.py -q -p no:cacheprovider -W ignore -k "o2_ or segment or rehearse"` | all passed, 0 failed, 0 skipped |

---

## 10. Open risks (what only the game can settle)
- **The climb** (F1). The input path was read, never run. If `hold up` does not reach B_KEY(16), O2 stops before any
  session: an agent patch is the owner's call.
- **Jack's timing** (F2). His contact window is 45-61 ticks, 1.5-2.0 s, from control (0.2 #10). The rehearsal measures
  both sides of the race. V6 and V12 keep a lost race out of the verdict, and the `watch` evidence keeps it from
  reading as a finding.
- **The exits' fade and the map switch** (F7). `exit_wait_s` 8 s covers the fade (about 0.85 s) and the switch by a wide
  margin, but the id-flip latency was never measured. The rehearsal records it per exit.
- **mbg101 sets the target FPS while it plays.** The tick clock re-measures, but the page and choice waits planned in
  ticks must not run during a rate flip; the rehearsal records the flip. Its length also bounds `no_progress_s` (F7).
- **Kupo near the ladder at stage 10.** A Confirm could reach his talk instead of the ladder. The ladder point is about
  889u from him. Only the rehearsal (R-115a, R-FULL) proves it; a talk would show as a V1 choice, or as a forbidden hit
  whose `near` evidence says which.
- **116's narrow walks** (wall gaps 74-137 along the line). Puck stays ahead at speed 68 (the driver critique's check);
  R-116 proves the pace.
- **The facing for tag-3 Confirms** (the booth, the ladder). Neither region is facing-gated or overridden (no
  QuadTalkable or QuadCircle key for 103 or 115). O1's candle took a plain Confirm, and these are assumed to as well;
  F4 proves it.
- **61's FMV003 under `end_run`'s warp** (F8). O1's warp left 100 mid-MBG; a type-0 FMV is untested.
- **The uk text defect ships with today's build** (6.4). The session is unaffected (P-LANG: US), but a deploy as built
  shows US text to UK players in stock 100-117. The lead's kit fix and a rebuild should precede the owner-gated deploy.

---

## 11. Critique log

Each item of the two critiques of 9d0e7780, what was re-checked, and the disposition. "D" is the driver-robustness
critique (the fresh re-run), "C" the claim-integrity critique. Both were read in full.

### 11.1 Driver robustness
| # | Claim | Re-checked | Disposition |
|---|---|---|---|
| D1 (blocker) | Every exit is a race the cross/leave_now executors can lose: under `handoff` they return when control drops, before `Field()`, and log "interrupted". 106 e14 VOIDs by V5 when a hint is up; 105 e11 is a coin flip against `interrupts: 0`. | Every route exit's tag 2 runs ExitField, then FadeFilter(24) and op_22(25), then `Field()` (L100/L105/L106 listings). MOVQ zeroes `usercontrol` at once (DoEventCode.cs:859-869), and MJPOS walks to the first-edge projection (:2247-2270). `_walk_leg` settles after each hold (session.py:3269-3271), and `_route_leg` returns "walk" on control loss (:4454). Measured 105 e11's walk at 884u / 34 = 26 ticks. 106 e14's first edge is the west edge. 106 e14 t2 has no CloseWindow. FakeGame `exit_frames` defaults to 0. | ADOPTED, with a longer bound. 2.3 judges a control loss by where it happened (`record["lost"]`, H1): at or inside the target (`exit_slack` 40u) means the executor waits for the field change itself; outside means `interrupted`. The wait is 8 s draft, not about 3 s: the map switch after `Field()` was never measured, and F7 re-sizes it from the rehearsal. Every warping test sets `exit_frames = 50`, and each branch has a test (9, B7). 0.2 #12 records the mechanism. |
| D2 (blocker) | The live V12 `donor_not_in` rule matches the warp's own residue rows (field 70), so every run VOIDs at its first visit; the FakeGame has no residue. | Ff9mkDebugMenu.cs:2129-2135 writes both values directly before SetNextMap. Rung 1 saw the residue "in field 70 before the load". FakeGame does not model the residue net (fakegame.py:223-227), and its `warp` drops both args. | ADOPTED. The scan reads only `w` rows from the run's start row on (2.2 rule 3, 4.7). H4's warp writes the residue rows in the old field, and a test proves the scan ignores them (B7). With C3 the scan also stops VOIDing unbacked hits. |
| D3 | Jack's contact window is about 1.5-2.0 s, not 1.9-2.7 s. | `range_r = 4*(collRad+collRad) + speed + 60` (HarnessAgent.cs:2349-2355); RADIUS arg 2 is collRad (DoEventCode.cs:1498-1502); Jack 26, Vivi 30: 299. Walked his legs at 15u a tick: within 299 of the lookout at tick 73.5, at (-206,2858). FieldTPS is 30. | ADOPTED: 0.2 #10, 2.4, and F2 now compares measured latency against measured contact time with the published `range_r`, with a 0.5 s margin. |
| D4 | No stall watchdog: any hang costs the 1800 s run budget. | Rule 9 only sleeps; research dispute 13 (the fldfmv gate) is untested. | ADOPTED: `budget.no_progress_s` 120 and V14 (2.2), with a FakeGame test. The signature includes the storytrace row count. F7 sizes it from the longest no-progress stretch seen, mbg101 included, so the movie cannot trip it. |
| D5 | The real stage-10 grant and the whole 115 scene are rehearsed only by R-FULL. | 115 e0 t0 ip231-302: SC 1153 (or 1152) sets `Int16[2]:=213`, and SWITCH case 213 starts stage 1. | ADOPTED: R-115a `warp 115 213 1153` -> 116, 2 runs (7.1). F10 reads the grant from it. Under C12 its trace proves mechanics only. |
| D6 | Confirm steps pass `zone=`, so the walk stops at the region's edge, not the deep goal. | session.py:3199-3200 returns "arrived" on the first sample inside. TreadQuad reads the transform (TreadQuad.cs:9-10). No QuadCircle or QuadTalkable key for 103 or 115. | ADOPTED WITH A CHANGE. Confirm steps walk without `zone`, settle, then require `region_contains` and a depth floor before pressing (2.3). The floor is `min_depth` 40, not 80: the ladder quad's deepest point is 90 (measured; its z extent is 184u), so a floor of 80 is a 24u band that a walk whose smallest press moves about 30u cannot reliably land in. A settled sample equals the transform position, so 40 absorbs the rest. O2-GOALS proves `depth(goal) - tolerance >= min_depth` for both goals (155 and 45). |
| cleared | The Rat Kid bump cannot be outrun; hot-spots are press-edge and out of reach; the ladder loop holds y; every choice defaults to 0; Puck stays ahead in 116; calibration survives. | Hot-spot reach re-derived from each tag 1's compare (2.5): every control point and confirm goal is 469u or more beyond every reach. | Kept. One wording fix adopted: the 116 rows no longer say "wait behind him, never push", which is not what `npcs=True` does (2.4). |
| retracted (notes) | Puck blocking 116 #3 (the critic's F4). | The critic retracted it: `TimedTurn(...,64)` is a 4-8 tick turn. | Nothing to do. |

### 11.2 Claim integrity
| # | Claim | Re-checked | Disposition |
|---|---|---|---|
| C1 (high) | O2-TEXT/P-TEXT check the text against the tool that wrote it; the build's uk 33.mes is the US text; the language is not pinned. | Read every language's block 33 by the ResourceManager path (mainData + resources.assets): us 4751874951, uk 8c94536b6c, and the build's uk equals stock us. Both score 826 under `_lang_score`. Live blocks 2, 187 and 276 in FF9CustomMap ship uk = stock us too. Memoria.log "Updating text localization [English(US)]", ForceLanguage -1. | ADOPTED PER THE LEAD'S RULING: `text_rule` over the ResourceManager-path references, a hard FAIL for us, KNOWN-KIT-DEFECT lines for a foreign-language copy, FAIL otherwise (0.1, 6.1, 6.2); P-LANG and `lang` in the fingerprint (6.2, 6.3); the defect is in `o2_forks.json` (6.4). The KIT fix is REJECTED ON THIS BRANCH per the ruling: the lead makes it. The live blocks 2/187/276 are the lead's to report. |
| C2 | O2-NULL cannot see seam keys, and on the F side the driver counts a real route field as on the route. | `Comparison.stock_only` excludes keys with a seam count (storytrace.py:1076). The driver's `members.get(fid, fid)` maps real 103 to 103. `digest` files seam rows under `seam_keys` (:948). | ADOPTED: O2-SEAM (5.3), V11 on the F side for any positive id that is neither a member on the route nor an end field (2.2 rule 2), forbidden matching on raw rows including seam rows (4.7), and the seam-leak and forbidden-on-seam cases (8). |
| C3 | Forbidden patterns VOID whole runs whatever caused them, so a fork-caused forbidden write hides and PROVEN stands; the pickup-function list was incomplete; V1/V2/V4/V5/V8/V11 hide structural deviations the same way. | The additional writers are real: 106 e16 t12, 115 e17 t16, 116 e21 t14 (called by the hot-spots) and 115 e17 t12 (only via the dormant e14 t3, which also writes Byte[472]:=4 and Bit[7202]:=1). Each hot-spot writes its own position into Int16[220]/[222] first. | ADOPTED. A hit VOIDs a run only when the driver's own log backs its cause, per 4.7's backing rule (`press`, `watch` and `step` evidence, 2.2). Otherwise it is a finding, O2-FORBIDDEN over every run. The list is corrected (0.2 #9). O2-VOID-ASYM reads attributed VOID classes per side (2.7, 5.3). Its rule (a) applies to game-attributed classes only, both directions: the critic's "a trace-visible class only on F" would turn one lost Jack race, a driver fault the evidence shows, into NOT PROVEN. Rule (b), every run of a side VOID in one class, applies to any class. |
| C4 | The analysis cannot repeat forbidden checks whose events write only masked bytes; nothing scans after the last new visit. | `digest` drops noise sites before keying (storytrace.py:815-819). Kupo's paths store only Bit[184]/Bit[189]/the mailbox except case 202's Bit[3784]. | ADOPTED: patterns match raw kept `w` rows, masked and seam rows included, live and offline (4.7); a last scan runs before `reached` (2.2 rule 1). |
| C5 | The live scan pre-empts O2-START; `at` can be a residue row; START(a) is too loose. | Rung 1: the residue is in field 70. The old `cut_at_start` took the first `w` or `r` row with don 100. | ADOPTED: one window for both scans (from the start row on), `at` is the first `w` row in the start PLACE (frozen members), `pre` must be exactly `start_residue` (bytes and values), and post-start residue is O2-RESIDUE's (5.2, 5.3). |
| C6 | The O1 gate is exact for one archive only; G3 compares verdicts; a widened `is_noise` passes; `run()` is exercised only through a stub. | o1d analyses to VOID at HEAD. The dry-run reports are deterministic and path-free (run twice, byte-equal). o1e has no field-mode Byte[206]/[199] key. v1-v3 raise KeyError 'battle_won'. | ADOPTED: G0 captures the full (checks, report) of o1e, o1d, all 16 dry-run cases and the offline check before any change; G3/G5 require byte-equality; G6 is the field-mode Byte[206] mutant; G7 includes `test_o1_segment_run_pins_o1s_session_surface`; PART B runs all of `tests/test_harness.py` (574 passed, 1 xfailed at HEAD, about 32 minutes) after H4 and H1, the steps that change shared verbs, and at its end. One change: the mutant lives in `segment_regress.py`, not `o1_dryrun.py`, because O1's files stay unedited as part of the gate. |
| C7 | The noise pattern format is undefined, and the drafted noise entry cannot pass O2-KEYS (no `ip`). | `keys_check` builds a Row from `(sid, tag, ip)` (o1:211). WriteKey has no `ip`. | ADOPTED: noise names exactly the 8 WriteKey fields plus `ip`/`op`/`why` metadata, `key_matches` raises on anything else, and only forbidden patterns carry operators (4.6). Mutants: noise-wrong-site and noise-wrong-value (8). |
| C8 | The claim is narrower than stated: Bit[191]/Bit[184] are masked; NULL compares sets, so write order is unseen. | Both are in `STORY_NOISE_REGION_NAMES` (flags.py:553). | ADOPTED: 4.4's sentence corrected; START(b) reads raw rows; O2-KEYS checks no key is masked; O2-MASKED (per-side region names, counts reported); O2-STATE with BOTH halves: (a) the trace-derived write history per target, and (b) the live `end_state` on arrival in 61 through `watch` (5.3, 2.2). |
| C9 | "SC nowhere else" / "Int16[2] nowhere else" are checked by name; residue is never judged. | A census of the route listings: bytes 0-3 are stored only as UInt16[0] (12) and Int16[2] (42), so no joined session case can exercise another width. | ADOPTED: LADDER/CHAIN select rows by byte span (4.2, 4.3, 5.3); O2-RESIDUE with `residue_after_start` registered empty; the span selector is proven by a unit case (8). |
| C10 | Values are typed by hand; O2-KEYS proves sites only; `op` is optional. | `text_at` read at the five compound sites gives `const(c) B_OR_LET` / `B_AND_LET` / `B_POST_PLUS` exactly. The critic re-derived all 48 sites: none wrong. | ADOPTED: `op` mandatory, the text anchored on the target, compound values computed from a named `prior` (a registered key or `newgame0`, witnessed by R-FULL's `old`, F6) (4.1, 4.4, 6.1). |
| C11 | The start-dependence claim holds for gEventGlobal values only. | O1 S#3's differing bytes and their readers, as the critic listed. | ADOPTED: 0.2 #8 and 4.5's report line state the scope. |
| C12 | Staged rehearsals could leak into the predictions (115 at SC 1155 writes Int16[2]:=215). | 115 e0 t0 ip287. | ADOPTED: only R-FULL traces define or change the ladder, chain, writes, noise, residue and end state; staged runs prove mechanics, compared within their stage (7.1, F6). |
| C13 | The fork side uses two donor sources; `mismatched` is only a note; LADDER/CHAIN compare raw `ip`. | The cuts used `r.don`; `digest` keys through its `donor_of`, which prefers the members map (:800); `mismatched` is a note (:871-876). | ADOPTED: the frozen members map everywhere (`place()`, 1.2, 5.2); a non-empty `mismatched` uncovers the run (5.1); LADDER/CHAIN compare the digest's own joined keys through `row_keys`, with no kit change (5.3). |
| C14 | Several checks have no mutant that makes them fail. | | ADOPTED: THROW (`test_segment_throw_check_fails_on_an_engine_exception`), TEXT (three text-rule units), NULL/SEAM on a seam leak, forbidden rows masked or on a seam, START's residue value, O1's field-mode noise (G6), noise at the wrong site or value, SC through another width (unit) and residue after the start, and a chain whose first `old` is not 102 (8, 9). |

Nothing was rejected outright. Four items were adopted with a change, each for the reason in its row:
- D1's wait bound (8 s, re-sized by F7);
- D6's depth floor (40, not 80);
- C3's VOID-asymmetry rule (by attribution);
- C6's mutant (it lives in the gate, not in O1's files).

One part of C1 (the kit fix itself) is out of this branch by the lead's ruling.

### 11.3 Implementation notes (PART A)
Where the build found the design silent or wrong, the smallest correct thing was done, and it is recorded here.

| Step | The design said | Found | Done |
|---|---|---|---|
| A0 | G6's mutant row is "a real 50 store site" of a field-mode Byte[206]. | No such site exists. 50's stock US `.eb` has 80 gEventGlobal store sites, none at byte 206, and neither do the 19 other donors of O1's chain (every instruction's stores walked with `storytrace.instruction_stores`). A field-mode row that joins nothing is only a JOIN failure: no key reaches O1-NULL, and the mutant would not tell a widened `is_noise` from O1's. | The row is a field-mode ADDITION-BUFFER store (`add` 1, `tag` -1, 50 e17), which `storytrace._locate` keys with no join: `WriteKey(50, 1, "eb", 17, -1, 40, "Global.Byte[206]", v)`. Proven both ways: at HEAD it reads O1-NULL False, O1-JOIN True, `NOT PROVEN: O1-NULL`; with `is_noise` widened to every mode it reads PROVEN, and G6 fails. |
| A0 | G7 includes the A3 pinning test. | The gate is written before that test exists. | `segment_regress.REQUIRED_TESTS` names tests G7 must find passing, each added with the step that adds it; every test the baseline collected must also still run. G7 reads the outcomes from pytest's JUnit XML, by name. |
| A0 | G0 captures once. | A baseline captured from code that already fails its own gate would freeze the failure. | `--capture` runs G1-G7's baseline-free halves first (the archive equality, the verdicts, `run_cases`, the pytest selection) and writes nothing unless all pass. Two captures under different `PYTHONHASHSEED` values were byte-identical. |
