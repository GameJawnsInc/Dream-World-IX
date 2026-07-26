# A4 — LIVE STATE + THE OUTER (text .seq) CLOCK

**TIER W rung 3 recon.** Read-only throughout: no game-install writes, no stock-file edits, no repo
code changes. Four verifications (measured, against the live install) and one analysis (the outer-clock
question, built from those verifications plus the existing studies).

Ground truth referenced throughout: `W1-READOUT.md` (the two-clocks law, the merged timeline),
`W2-RESCORE.md` (the staged/deployed camera edit, the override mechanism), `EF227-CHOREOGRAPHY.md`
(the phase spine, the slti-at-0x1278 evidence), `PLAN.md` (the tier ladder, the effect-owned-scenery
law), `rung2-seq-hot-edit/README.md` and `rung4-effectpoint/README.md` (the outer/nested text `.seq`
mechanism and its own prior probes).

**Provenance.** All raw bytes and raw stock `.seq` text this recon read are stock, user-owned data —
none of it is reproduced verbatim at length here. Full copies, hashes, and the cumulative-tick working
notes live at `C:\gd\SCRATCH\summon-format\retime-w3-recon\` (SCRATCH only, never committed): a byte-diff
script + its output, a hash script, verbatim copies of the two stock text `.seq` files, and
`OUTER-TICK-MAP.md` (the full cumulative-tick reconstruction this report's §4 summarises). This report
names DSL keywords (`EffectPoint`, `SetBackgroundIntensity`, `PlaySound`, …) and tick numbers, which is
the same convention already committed in `rung2-seq-hot-edit/README.md` and `rung4-effectpoint/README.md`
— it does not reproduce either stock file's content at length.

---

## 1. THE LIVE OVERRIDE — verified BYTE-EXACT match to W2's artifact

```
C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\FF9CustomMap\FF9_Data\SpecialEffects\ef227
```

exists, is **823,296 bytes** (matches both the stock container and W2's rebuilt artifact size), and was
diffed byte-for-byte against `C:\gd\SCRATCH\summon-format\ef227.bytes` (the stock container) with a
throwaway script (`C:\gd\SCRATCH\summon-format\retime-w3-recon\diff_live_vs_stock.py`).

**Result: exactly 4 differing bytes, at exactly the 4 offsets W2-RESCORE.md §3 predicted:**

| offset | stock byte | live byte | field (per W2's own derivation) |
|---|---:|---:|---|
| 0x29d51 | 0x11 (17) | 0x51 (81) | camera orientation/yaw |
| 0x29d52 | 0x00 (0) | 0x80 (128) | camera roll |
| 0x29d5c | 0x00 | 0x60 | focal H, low byte |
| 0x29d5d | 0x01 | 0x00 | focal H, high byte |

Decoded as little-endian u16, offsets 0x29d5c-0x29d5d: stock H = 0x0100 = **256**, live H = 0x0060 =
**96** — matching W2-RESCORE.md's stated 256→96 exactly. Orientation 17→81 and roll 0→128 also match
exactly. **This is W2's artifact, unmodified, and nothing else in the 823,296-byte container differs.**

The W2 revert script also confirmed present and non-empty:
`C:\gd\SCRATCH\summon-format\rescore-w2\revert_summon_camera_227.py` (1,459 B).

**Method:** direct byte comparison of the two files (`open().read()` + index-by-index compare), not a
hash comparison — a hash match would only prove "identical," an exhaustive index diff is what proves
"identical *except these four*." Verified both files are exactly 823,296 B before diffing (a length
mismatch would have made an index-aligned diff meaningless).

---

## 2. THE FOLDER STACK — clean, as required for the override to resolve

Live `Memoria.ini [Mod] FolderNames` (read directly, not assumed from a prior session's notes):

```
FolderNames = "FF9CustomMap", "FF9CustomMap-world", "MoguriMain", "MoguriVideo"
```

Every folder in that list, checked for (a) its own `FF9_Data/SpecialEffects/ef227`, (b) its own
`StreamingAssets/Data/SpecialEffects/ef227` (the loose-text override path rungs 2/4 used), and (c) a
`ModFileList.txt` at its root:

| folder | FF9_Data/…/ef227 | StreamingAssets/…/ef227 | ModFileList.txt |
|---|---|---|---|
| **FF9CustomMap** (priority 0) | **present** — the W2 override, confirmed §1 | **absent** | **absent** |
| FF9CustomMap-world | absent | absent | absent |
| MoguriMain | absent | absent | **present** (506,654 B) |
| MoguriVideo | absent | absent | **present** (646 B) |

Both required conditions hold: **FF9CustomMap has no `ModFileList.txt`** (so W2-RESCORE.md §5's trust-gate
concern doesn't apply — the loader falls through to a plain `File.Exists` probe for this folder, and the
override is visible), and **no other folder in the stack ships a competing `ef227`** at any priority that
could shadow or race FF9CustomMap's copy (FF9CustomMap is priority 0 regardless, but this rules out a
higher-priority collision entirely, not just "it happens to be fine this time").

MoguriMain/MoguriVideo do have their own `ModFileList.txt` files, but per W2-RESCORE.md's own mechanism
description that trust gate is per-folder — it governs whether *that folder's* other files are visible
via list-lookup vs `File.Exists`, and has no bearing on FF9CustomMap's own resolution. Noted for
completeness, not a risk.

**Confirmed reverted:** `FF9CustomMap/StreamingAssets/Data/SpecialEffects/` contains **no `ef227/`
directory** (it has `ef080/`, `ef084/`, `ef091/` — Nimbra's own private ids and rung 3's fresh-id Bahamut
copy, all unrelated to ef227). Rung 2's `PlayerSequence.seq` override and rung 4's `Sequence.seq` override
are both gone. **Stock plays for both outer text `.seq` files right now** — the premise §4 depends on.

**Method:** direct filesystem enumeration (`ls`/`find`) against the live install and a direct read of
`Memoria.ini`, not a memory/notes lookup — the brief's own warning ("many agent worktrees run
concurrently... re-verify before any destructive action") applies equally to read-verification: a stale
assumption here would have invalidated §4 silently.

---

## 3. THE BENCH — Actions.csv row confirmed live and correct

Live ability row, read from
`FF9CustomMap/StreamingAssets/Data/Battle/Actions.csv` (the header at the top of this file gives the
column order):

```
Stock Bahamut;196;None(0);AllEnemy(8);0;0;0;0;227;227;85;30;0;0;22;0;8;0;159;# Stock Bahamut
```

Mapped against the file's own header (`Comment;id;menuWindow;targets;defaultAlly;forDead;defaultOnDead;
defaultCamera;animationId1;animationId2;scriptId;power;elements;rate;category;statusIndex;mp;type;
commandTitle`):

| field | value | matches spec? |
|---|---|---|
| id | 196 | yes |
| targets | AllEnemy(8) | yes |
| animationId1 (vfx1) | **227** | yes |
| animationId2 (vfx2) | **227** | yes |
| power | 30 | yes |
| mp | 8 | yes |
| **type** | **0** | yes — critical: stock Bahamut ships `type=4`, which with `GARNET_SUMMON_FLAG` quadruples MP cost; this row correctly overrides to 0 |

This row traces to `studies/custom-summons/rung8-epic/bench/rung8.field.toml` line 124 (the exact
`{ name = "Stock Bahamut", from = "Bahamut", targets = "AllEnemy", vfx1 = 227, vfx2 = 227, type = 0,
power = 30, mp = 8 }` W2-RESCORE.md §6.3 specified). That field.toml's own `[field] id = 4814`
("MISTBENCH") is re-slotted at deploy time to scratch id **30301** (confirmed from the toml's own header
comment and `rung8-epic/README.md`'s file table: "Field id 4814 / MISTBENCH, deployed to slot 30301") —
matching W2-RESCORE.md §6.3's cast protocol (warp to field 30301, Iviv → Spark → **Stock Bahamut**).

**Method:** direct read of the live CSV, column-mapped against the file's own embedded header line (not
assumed from the toml source) — confirms the *deployed* state, not merely that the *authored* toml looks
right.

---

## 4. THE OUTER CLOCK — analysis

### 4.0 Two clocks named "sequence," and why they are not the same file

TIER W/R's existing camera work (`op.seq_tick`, W1's merged timeline, `EF227-CHOREOGRAPHY.md`'s phase
spine) all describe **one** clock: the binary `id-3` program container's own `SequenceCode` op stream —
`PLAY_CAMERA` (`0x29`), `RUN_PROGRAM` (`0x80+N`), etc., ticking inside the 823,296-byte `ef227` file that
§1 diffed. Call this **the CONTAINER clock**. It is what W3's planned edit touches.

Rungs 2 and 4 (`rung2-seq-hot-edit/`, `rung4-effectpoint/`) documented a **second, textually separate**
system: two loose plain-text `.seq` DSL files —

- `Data/SpecialEffects/ef227/PlayerSequence.seq` (the OUTER script — caster animation, `LoadSFX`,
  `PlaySFX`, `WaitSFXDone`; 36 content lines)
- `Data/SpecialEffects/ef227/Sequence.seq` (the NESTED/shared script, loaded from inside the outer one by
  `LoadSFX: SFX=Bahamut__Full ; ...` per rung 3's nested-load law; carries `EffectPoint` — the real damage
  trigger — plus `PlaySound`, `ShowMesh`, `SetBackgroundIntensity`; 73 content lines)

read via `AssetManager.LoadString` through the same stacked-mod-folder path as everything else, **re-read
from disk on every cast, no cache** (rung 2 §"No cache" / rung 4 §1). Call this **the OUTER clock**. It is
driven purely by literal `Wait: Time=N` line sums inside each text file — it has no mechanism that reads
anything inside the binary container, and the container's program has no mechanism that reads it either
(R2/R3's own finding, reaffirmed by `EF227-CHOREOGRAPHY.md` §4a: the camera and program are two clocks
the *author* kept aligned by construction — never a live coupling).

**§2 confirms the premise the task states as given:** no mod folder currently overrides either OUTER-clock
file, so stock plays right now, on this install.

### 4.1 What the OUTER clock actually contains (measured)

Both stock text files were read directly from the base game (`StreamingAssets/Data/SpecialEffects/ef227/`
— they ship as loose text in the base install, not packed inside `resources.assets`; this is how
`build_rung2.py`/`build_rung4.py` obtain "a fresh copy of the stock file" for their own drift guards).
Their sha256 hashes matched `build_rung2.py`'s and `build_rung4.py`'s own `EXPECTED_SHA256` constants
exactly — **no drift since those rungs' recons.**

`PlayerSequence.seq` carries exactly **one** tick-scheduled event (`SetBackgroundIntensity: Time=12` at
line 19), and it is timed against the caster's own chant-animation length, not against the container's
clock — it fires before `WaitSFXLoaded` even resolves. Everything else in that file is animation- or
signal-gated (`WaitAnimation`, `WaitSFXDone`, …) or sits inside a `StartThread` whose condition is false
for an ordinary player-cast-on-enemies. **`PlayerSequence.seq` has nothing for a W3 co-retime to touch.**

`Sequence.seq` is where the schedule lives. Reconstructing its own cumulative-tick timeline by summing
every `Wait: Time=N` in file order (full working table:
`C:\gd\SCRATCH\summon-format\retime-w3-recon\OUTER-TICK-MAP.md`) reproduces, independently, the exact
numbers `rung4-effectpoint/README.md`'s verifier addendum already cited — **tick 434** (the flare's
`SetBackgroundIntensity` ramp begins, `HoldDuration=82`), **tick 486** (`EffectPoint Type=Effect` — the
damage computation), **tick 498** (`EffectPoint Type=Figure` — the damage-number popup), **tick 516** (the
next `SetBackgroundIntensity` — "lights back on" — fires exactly as the flare's own hold ends: `52 + 12 +
18 == 82`, a clean handoff). This cross-check is a genuine independent confirmation, not a re-quote: it
was derived by hand-summing the full stock file read fresh from the install, not copied from the rung-4
report.

The reconstruction adds the landmarks rung 4 didn't need for its own narrower probe: **ticks 0, 18, 60,
116, 140, 166, 222, 250, 289, 324, 330, 401, 403, 411, 420, 422**, and the file's own end at **tick 547**
(from the closing `Wait: Time=31`). In total the OUTER script schedules roughly two dozen beats — six
`PlaySound` clusters (4 sounds each), two `Song`-type cues, seven `ShowMesh`/`SetBackgroundIntensity`
fade events, and the `EffectPoint` pair — none of which reference the container at all.

### 4.2 The native-frame ↔ outer-tick correspondence — INFERRED, with stated uncertainty

**No FULL TICK MAP file existed in the rung-4 study to reuse** — `rung4-effectpoint/README.md`'s
verifier addendum only worked out the four landmarks above (434/486/498/516) for its own narrower
purpose. §4.1's reconstruction fills that gap for THIS recon's needs; it is built from the stock files
themselves (already-hashed as un-drifted against the rung-2/4 recons), not from a fresh binary extraction
— consistent with the task's instruction not to re-extract game assets when a map already exists in
substance.

The harder question — what CONTAINER seq_tick a given OUTER Sequence.seq tick corresponds to — is **not
measured anywhere** and this recon does not fabricate an exact conversion. What the existing studies DO
support, cited plainly as separate facts:

- **MEASURED, this session:** live `Memoria.ini` has `BattleTPS = 15` ("tick per second," the file's own
  comment). This is the rate `Wait: Time=N` in the OUTER `.seq` counts against — rung 2/4's own real-time
  conversions (`Time=12` ≈ 0.8 s, `+12` ticks ≈ 0.8 s) already assumed this and this session's direct read
  confirms it for the live install.
- **MEASURED, prior study (`rung8-epic/PLAN.md` / `FORMAT.md`):** `SFXDataMesh.cs:849-861`'s own equation
  — "one **sequence tick** advances one clip frame ÷ Speed" — ties a generically-named "sequence tick" to
  `BattleTPS` explicitly, for the creature's animation-clip stepping.
- **STRUCTURAL, this session:** `PlayerSequence.seq`'s own `PlaySFX: SFX=Bahamut__Full` line (its line 25)
  is the single point where the OUTER script hands off to both the CONTAINER (which `SFX_Play` loads and
  starts, per `PLAN.md`'s DLL-export citation) and the NESTED `Sequence.seq` (whose own tick-0 is this
  file's own first line). Both children start at the same `PlaySFX` call.
- **CIRCUMSTANTIAL, this session:** the reconstructed OUTER script's own total length (547 ticks) is the
  same order of magnitude as the CONTAINER's independently-captured cinematic span
  (`EF227-CHOREOGRAPHY.md` §4: captured frames 11-561, ~550-frame range) — consistent with, but not proof
  of, a shared ~15 Hz rate.
- **NOT MEASURED anywhere:** the exact fixed offset (if any) between "CONTAINER seq_tick 0" and "OUTER
  `Sequence.seq` tick 0" — whether they are frame-for-frame synchronized or offset by a small constant
  (e.g. one tick of load-then-start latency). W1's own "two clocks" constants (47 for the camera, 45 for
  the program, against the CAPTURE's own frame counter — itself a third, differently-anchored clock, the
  battle scene's render-frame count since capture start, not since `PlaySFX`) are not evidence about this
  specific OUTER-vs-CONTAINER offset; they answer a related but different question.

**Working hypothesis, stated as such and not stronger:** OUTER `Sequence.seq` tick *T* corresponds to
CONTAINER seq_tick *T* ± a small (single-digit, unmeasured) constant. Everything below follows from that
hypothesis; a direct capture correlating the two clocks (log `frameIndex` from `SFX_Update`'s own `ref`
out-param alongside the OUTER script's own tick counter on the same cast) is the only way to pin the
offset exactly, and this recon did not run one — it is READ-ONLY, and no such probe exists in the studies.

### 4.3 (a) What visibly drifts, and by how much, for N ≈ ±45

W3's planned edit shifts every CONTAINER op at seq_tick ≥ 82 by N (task prompt + `W1-READOUT.md` +
`EF227-CHOREOGRAPHY.md` agree: `ef227:c0` state 0 spans seq ticks 12-81, the `slti $v0,$s5,69` transition
at file offset `0x1278` fires the state change at seq_tick 82). Under §4.2's hypothesis, OUTER tick 82
lands **inside** the `Wait: Time=56` spanning OUTER ticks 60→116 — no OUTER event fires exactly there, but
**every OUTER event from tick 116 onward** (15 of the ~18 named beats in §4.1's table — everything from
the first flash-and-PlaySound-cluster after the opening blackout through the closing fade) is causally
"after" the point where the CONTAINER retime begins. Only the very first three OUTER beats (ticks 0, 18,
60 — the initial dim, the blackout/`ShiftWorld`, and the first `PlaySound` cluster) precede it.

Since the OUTER schedule's own tick counts are **literal and fixed** — nothing in the `.seq` DSL reads a
container tick — none of those 15+ beats moves when the CONTAINER retimes. The CONTAINER's own visuals
(camera cuts, creature draws, effect-model draws) from seq_tick 82 onward all shift by N; the OUTER
beats from OUTER-tick ~82 onward do not. The two schedules — built to coincide by the original author, per
`EF227-CHOREOGRAPHY.md` §4a's "two clocks kept aligned by construction" — desynchronize by exactly N ticks
from that point on.

At the confirmed live `BattleTPS = 15`, N = ±45 ticks is **±3.0 seconds exactly**. Concretely, if this
hypothesis holds:

- **N = +45 (entrance stretched):** the CONTAINER's visuals — including whatever beat was originally
  timed to coincide with the `EffectPoint` damage computation near OUTER-tick 486 — arrive **3.0 s
  later** than authored. The `EffectPoint` hit (and its damage-number popup 12 ticks later) still fires
  at the OUTER schedule's fixed tick 486/498, so it now lands **3.0 s before** the visual beat it used to
  land inside. Every `PlaySound` cluster and `ShowMesh`/`SetBackgroundIntensity` fade from tick 116 onward
  is similarly 3.0 s ahead of its intended visual partner.
- **N = -45 (entrance shortened):** the reverse — the CONTAINER's visuals arrive 3.0 s **earlier**, so the
  `EffectPoint` damage beat (fixed at 486/498) now fires **3.0 s after** the visual moment it was authored
  to coincide with, and likewise for every later `PlaySound`/`ShowMesh` cue.

This is the **same class of symptom** rung 4's own probe demonstrated on purpose (relocating `EffectPoint`
decouples the damage cue from the visual spectacle) — arrived at from the opposite direction: retiming the
CONTAINER without co-retiming the OUTER text produces the identical decoupling.

**Caveat on the offset:** because §4.2's cross-clock alignment is a hypothesis, not a measurement, the
*direction* and *rough magnitude* of the drift (~N ticks, ~N/15 s) is the confident claim; the *exact*
tick each OUTER beat lands on relative to a specific CONTAINER visual frame carries whatever unmeasured
constant offset §4.2 flags — plausibly a few ticks, not tens.

### 4.4 (b) The cheapest coherent co-retime

Because §4.1's OUTER tick 82-equivalent falls inside a single `Wait: Time=56` line (`Sequence.seq` line
14 in the stock file), and every later tick in the reconstruction is a running sum that includes that
line's value, **the cheapest coherent co-retime is a one-line edit**: change that line to
`Wait: Time=56+N`. That single change shifts every one of the 15+ downstream OUTER beats — both
`EffectPoint` calls, the flare ramp, all four remaining `PlaySound` clusters, both `Song` cues, and the
closing fade — uniformly by N ticks, restoring their intended coincidence with the (now similarly
shifted) CONTAINER visuals, under §4.2's hypothesis. No other line needs to change; `Wait` durations are
purely relative/incremental, which is exactly the mechanism rung 2 already proved works in this same
engine path (a single `Wait: Time=` edit uniformly delays everything after it) and rung 4 already proved
is hot-reloadable with no relaunch.

Delivery matches the task's framing exactly: a mod-folder override at
`FF9CustomMap/StreamingAssets/Data/SpecialEffects/ef227/Sequence.seq` (§2 confirms this path is currently
clean — no folder in the stack ships one), re-read from disk on every cast (§4.0's "no cache" citation),
reverted by deleting the file (§2's own revert scripts, `revert_rung2.py`/`revert_rung4.py`, already
demonstrate the clean-removal shape for this exact folder). **Unlike rung 2's edit, this would be OUR
OWN mod-folder override of a file that is not itself the provenance-sensitive artifact** — the *edit* (a
single integer bumped in one `Wait:` line) is fully authorable and committable as a small script + diff,
in the same shape `build_rung2.py`/`build_rung4.py` already use; the *edited copy itself*, like theirs,
would still be SE-derived content and would stay out of the repo (deployed straight to the live mod
folder, per those scripts' own provenance sections).

Not attempted or verified in this recon — this is a *design* answer to "what would the fix look like,"
not a claim that it has been built, staged, or tested. The exact value of N and the exact anchor line
depend on whatever W3 actually ships; the mechanism (one-line `Wait:` edit, same anchor line identified
above) is the reusable part.

### 4.5 (c) Can the W3 gate be judged without the text co-retime?

**Yes.** PLAN.md's W3 gate is specifically about **phase-cut alignment** — camera cuts (CONTAINER
`PLAY_CAMERA` ops) staying synchronized with program phase boundaries (CONTAINER `RUN_PROGRAM` state
transitions) after a retime. Per `W1-READOUT.md`'s two-clocks law, that alignment is a relationship
**entirely inside the 823,296-byte container** — both halves of it (the camera sub-file's own duration
bytes and the program's `clock >=` threshold immediates) are bytes W1/W2's own tooling already reads,
diffs, and round-trips, with zero dependency on either OUTER text `.seq` file. A retimed container can be
decoded and its internal camera/phase alignment checked in exactly the way W1's merged timeline already
does, independent of whether `Sequence.seq` was ever touched.

The OUTER-clock drift this section derives is real, visible in a cast, and **separate**: it is a
desynchronization between the CONTAINER's (retimed) visuals and the OUTER script's (untouched) damage/
sound/fade cues — not a desynchronization *within* the container, which is what the gate tests. A cast
report that doesn't distinguish the two risks exactly the failure mode rung 4's own README warned about
for its own edit: a viewer sees "the damage number felt off" and attributes it to the retime being wrong,
when the retime (the thing under test) may be internally perfect and the OUTER schedule is simply doing
what it always did — count its own fixed ticks, unaware anything upstream changed.

**Recommendation for whoever runs the W3 cast:** judge the gate from the container-internal alignment
alone (as design intends), but disclose the OUTER-clock drift as a known, separate, cheaply-fixable
side effect in the same report — exactly the posture this recon takes here, not a silent omission.

---

## 5. Anything else live under `FF9_Data/SpecialEffects/`

**Only `ef227`.** `FF9CustomMap/FF9_Data/SpecialEffects/` contains exactly one entry (confirmed by direct
directory listing, §1/§2's method). No other binary `ef###` container is overridden in any mod folder in
the live stack.

For completeness (a different path, not what this item asked, noted so it isn't mistaken for something
under `FF9_Data`): `FF9CustomMap/StreamingAssets/Data/SpecialEffects/` — the loose-TEXT-and-model side,
unrelated to `ef227`'s binary container — carries three folders: `ef080/` and `ef091/` (Nimbra's own
private effect ids, each with a `PlayerSequence.seq`, `.sfxmodel` manifests, and a `FileList.txt`) and
`ef084/` (rung 3's fresh-id private Bahamut copy, with its own `PlayerSequence.seq`, `Sequence.seq`, and
`creature_manifest.sfxmodel`). None of these three is `ef227`; none was touched by this recon; §2 already
confirmed `ef227` itself is absent from this directory (the loose-text overrides from rungs 2/4 are
cleanly reverted).

---

## 6. Summary — measured vs. inferred, at a glance

| claim | status | basis |
|---|---|---|
| Live `ef227` container == W2's artifact (4/4 bytes, exact offsets/values) | **MEASURED** | full index-aligned byte diff, this session |
| W2 revert script present | **MEASURED** | filesystem check |
| Folder stack clean (no ModFileList.txt on FF9CustomMap, no competing `ef227` anywhere, rung 2/4 text overrides reverted) | **MEASURED** | direct `Memoria.ini` read + filesystem enumeration of all 4 folders |
| Bench Actions.csv row 196 "Stock Bahamut" vfx1=227 vfx2=227 type=0 | **MEASURED** | direct CSV read, column-mapped to the file's own header |
| Only `ef227` under `FF9_Data/SpecialEffects/` | **MEASURED** | directory listing |
| OUTER `Sequence.seq` cumulative-tick landmarks (434/486/498/516/547 + 12 more) | **MEASURED** (re-derived independently from the stock file, cross-checks rung 4's own math exactly) | hand-summed `Wait:` chain over the hashed, un-drifted stock text |
| `BattleTPS = 15` live | **MEASURED** | direct `Memoria.ini` read |
| OUTER-clock tick ≈ CONTAINER seq_tick (near-1:1, offset ≈ 0) | **INFERRED**, moderate confidence | shared `PlaySFX` origin (structural), shared order-of-magnitude total length (circumstantial), one prior equation tying "sequence tick" to `BattleTPS` for a different subsystem (partial) — no direct cross-clock capture exists |
| Exact drift magnitude/direction for a given N | **DERIVED from the inference above** — directionally solid, exact tick-for-tick offset unconfirmed | |
| W3 gate is judgeable without the text co-retime | **ANALYSIS**, grounded in W1's own container-internal framing of the two-clocks law | |

**Bottom line for W3 planning:** the live install is exactly where the studies say it should be — W2's
edit is live and isolated, the folder stack is clean, the bench ability is wired correctly, and stock
plays for both OUTER text `.seq` files. A W3 retime of the CONTAINER alone is safe to judge on its own
terms (phase-cut alignment, entirely internal). It will also, separately and predictably, desynchronize
the OUTER script's damage/sound/fade cues by roughly N ticks (~N/15 s) from whatever CONTAINER tick 82
onward now shows — a real, disclosed, and (per §4.4) cheaply fixable side effect, not a defect in the
retime itself.
