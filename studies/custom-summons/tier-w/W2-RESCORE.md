# W2 — THE CONTENT RESCORE: stock Bahamut, reframed, durations unchanged

**TIER W rung 2.** Deliverables: `rescore.py` (install reader + declarative delta + same-length
splice + staging ledger + revert), `bahamut_rescore.toml` (the declarative surface),
`test_rescore.py`, `w2_gates.py`, this report.
**Built and STAGED only** — nothing was written to the game install and nothing was deployed. The
staged mod root is `C:\gd\SCRATCH\summon-format\rescore-w2\mod\`.

---

## 0. HEADLINE

> **Four bytes.** The rebuilt 823,296-byte Bahamut container differs from the user's own install in
> exactly **4 bytes**, all four inside one camera sub-file, all four inside one keyframe of one
> shot: two pose bytes and the two halves of one projection distance. Every duration byte, every
> frame word, every other sub-file and the entire id-2 directory are byte-identical, and the patched
> container still round-trips byte-exact through the unmodified W1 path.

W1 proved a stock summon camera can be *read* losslessly. W2 spends that: a stock cinematic is now
**editable in place** from a small TOML, with the stock install untouched and a revert that restores
the target folder to a byte-identical prior state.

---

## 1. Gate table

| gate | result | numbers |
|---|---|---|
| **X0** no regression | **PASS** | tier-r `r1_gates` 8/8 · `r2_gates` 6/6 · `r3_gates` 5/5 · tier-w `w1_gates` **5/5** · tests 41+70+31+34+**34** = **210 passed** (`test_rescore.py` is the 34 new ones) · `summon_camera.py` **and** `camera_codec.py` working tree **UNMODIFIED** |
| **X1** unchanged everything else | **PASS** | **4 / 823,296** bytes differ. **19** duration fields and **28** frame words across all three shots: all identical. **83** other sub-files across **2** chunk archives: all identical. id-2 directory, **84** entries over 2 chunks: identical. Bytes outside the target block (sequence stream, programs, art, headers): **0** |
| **X2** round-trip | **PASS** | container header re-parses **strict** (`cursor_end == size`, `0xc9000`) · **3/3** camera blocks byte-exact through the unmodified codec · the rescored block alone 192 B → parse → serialize → 192 B **byte-exact** · W1's four invariants **4/4 hold on the block we wrote** |
| **X3** three-sequence check | **PASS** | the target block declares **1** sequence — **no alternate takes**, so the bit-3 selector has nothing to pick instead of ours. The guard is not vacuous: it **fires** on a synthetic 3-track block whose alternates differ |
| **X4** revert | **PASS** | tree-hash manifest before / staged / after, in **both** cases: fresh folder (0 → 1 → 0 files) and a folder already carrying an `ef227` override (1 → 1 → 1, prior bytes restored). Before-hash == after-hash in both; staged-hash differs from both |
| **X5** provenance | **PASS** | **0** byte literals of ≥6 non-uniform bytes in the committable sources appear in the target container or anywhere in the 372-file corpus · stock read at run time from the install's `resources.assets` · drift guard **matches** · staged output under `C:\gd\SCRATCH\summon-format\rescore-w2\` · a repo-relative staging root is **refused** |

Reproduce: `py studies/custom-summons/tier-w/w2_gates.py` (needs the install and the W1 corpus).
Tests run without either: `py -m pytest studies/custom-summons/tier-w/test_rescore.py -q`.

---

## 2. THE EDIT — which shot, and what changed

**Target: ef227 shot A — chunk 0, id-2 sub-file 6, 192 B, one declared sequence.** This is the
`PLAY_CAMERA` that installs at sequence tick 11 and governs Bahamut's **entrance**; W1's merged
timeline shows it as the first camera event of the whole cinematic, and TIER R's in-game capture
recorded its opening projection change at frame 58.

**Keyframe: local frame 1** — shot A's instantaneous placement, the very first authored frame. One
Code, no ambiguity (shot A *does* carry doubled frames later, at f121 and f148; the tool refuses
those without an explicit `occurrence`).

**Three levers, all in place, four bytes:**

| lever | stock | rescored | why this one |
|---|---:|---:|---|
| camera `orientation` (yaw) | 17 `[stock]` | 81 | a large yaw swing — the entrance is seen from a different side |
| camera `roll` | 0 `[stock]` | 128 | the shot rolls half a turn. 128 is **not invented**: stock ef227 already uses that roll value on later keyframes of this same effect, so the engine's pose evaluator provably handles it |
| focal **H**, the projection distance | 256 `[stock]` | 96 | H is the one camera value TIER R's capture observed directly. Pulled far back = a much **wider** opening frame. Deliberately wide rather than tight: a 3× zoom-*in* can degenerate into a screen of texture, which reads as "broken" rather than "different" |

**Why this is self-evidencing.** Shot A's *next* focal keyframe is at local frame 71 and is
untouched, so the reframe runs ~70 ticks and then **snaps back to stock framing**. The playtester
does not have to remember what Bahamut used to look like — they see the opening seconds re-framed
and the remaining ~15 seconds exactly as they remember. A change that reverts on schedule is much
harder to mistake for a rendering glitch than one that persists.

**What was deliberately NOT changed:** every duration (movement, focal), every frame word, every
other keyframe, the other two shots, the sequence stream, the effect programs. The two clocks W1
measured stay aligned by construction, because no byte that either clock reads was touched.

---

## 3. X1 — the byte diff, and what each byte means

Four bytes, at file offsets `0x29d51`, `0x29d52`, `0x29d5c`, `0x29d5d` — block-relative **13, 14,
24, 25** inside the 192-byte sub-file:

| block+ | what it is |
|---:|---|
| 13 | sequence0 → Code 0 (local frame 1) → camera-pose sub-block → **orientation** |
| 14 | sequence0 → Code 0 (local frame 1) → camera-pose sub-block → **roll** |
| 24 | sequence0 → Code 0 (local frame 1) → focal sub-block → **H**, low byte |
| 25 | sequence0 → Code 0 (local frame 1) → focal sub-block → **H**, high byte |

The gate does not assert this from the spec — it re-derives the meaning of every changed offset by
walking the block's group table, then each Code's flags through the codec's own field order, and
**fails if a changed byte lands in a field named `duration`** or in no field at all. That is the
difference between "we intended to change four bytes" and "four bytes changed and here is what each
of them is."

Everything else, measured rather than asserted: 19 duration fields and 28 frame words identical
across all three shots; 83 other sub-files identical across both chunk archives; all 84 id-2
directory entries identical; zero changed bytes outside the target block.

---

## 4. X3 — the three-sequence verdict

**The target block declares ONE sequence.** All three of ef227's shots do. So the trap W1 §6 named
— 332 of 798 corpus blocks carry genuinely different alternate takes chosen at runtime by the bit-3
selector, and a one-track edit there produces a cast that may look unchanged — **does not apply
here**, and there is nothing to fan out to.

That is a fact about ef227, not a general reprieve, so the guard is in the tool rather than in this
paragraph: `build` **refuses** a single-track edit on any block whose alternates are not
byte-identical, and `all_sequences = true` fans the same delta across every declared track. X3
proves the guard fires by running it against a synthetic 3-track block with differing alternates.

One subtlety worth recording, because getting it wrong inverts the check: **the alternates signature
must be taken BEFORE any edit is applied.** Taken afterwards, editing track 0 of a block whose
alternates really *were* identical makes them look different, and the check would then wave through
exactly the one-track edit it exists to refuse. The first implementation had this bug; the test
`test_byte_identical_alternates_need_no_fan_out` is what caught it and now pins it.

---

## 5. The mechanism — how the override reaches the engine

`SFX.Play` loads the effect by `AssetManager.LoadBytes("SpecialEffects/ef227", …)`. That name is not
`Data/`-prefixed, so it belongs to no asset bundle and `LoadBytesMultiple` falls through to the
**on-disc mod pass**, which probes `<mod folder>/FF9_Data/SpecialEffects/ef227` for each folder in
`Memoria.ini [Mod] FolderNames` order, **before** `Resources.Load`. There is no cache: a new
`SFXData` is constructed per action and the bytes are re-read per play, which is why **no relaunch is
required** for a content change to the override itself.

Four properties of that path shape the build, and each has a call-site guard:

* **EXTENSIONLESS.** `LoadFromDisc` reads the raw path, so `ef227.bytes` would never be found.
  `stage` refuses a destination with a suffix.
* **`ModFileList.txt` is a trust gate.** If a mod folder has one, the loader trusts it and never
  calls `File.Exists` — an unlisted file is invisible, and it is read once at init so a list change
  *does* need a relaunch. The ledger appends the lowercase `specialeffects/ef227` line **only if a
  list already exists**, and never creates one (creating one would make every *other* file in that
  folder invisible).
* **It is a whole-container copy.** ~803 KB of the user's own bytes frozen in a mod folder, which
  would silently shadow a future Steam/Moguri patch to this effect forever. Mitigated two ways: a
  registered sha256 **drift guard** refuses an install whose ef227 has changed, and the build
  **always re-derives from `resources.assets`** — never from a previously written override.
* **Failure is SILENT.** `SFX.Play` passes `suppressMissingError = true`, so a wrong folder, a wrong
  name, an extension, an unlisted file, or another mod folder earlier in `FolderNames` shipping its
  own `ef227` all log *nothing* and simply play the stock camera. "Nothing changed" is the only
  symptom of every misresolution — which is the whole reason the first delta is deliberately large.

---

## 5b. The op-146 gate — the program DOES write projection registers, and where that lands

The PLAN made this rung's *first* obligation the op-146 read-vs-write question, because it is the
difference between "the camera is entirely sequence data" and "the effect program is a second author
of the frame." It is now settled, and the answer is **both, but disjointly**:

* **Op 146 (`gte_project_vertices`) WRITES `gteOFX` and `gteOFY`** — the projection *offsets*, from
  its own arguments (hence ef227's 160/112, i.e. a half-screen centre). The writes are **scoped**:
  the entry values are saved to stack locals and restored at two sites that dominate the function's
  single `ret`. Every access is direct RIP-relative with a proven direction; the one indirect
  candidate is a read base.
* **Op 146 only READS `gteH`.** So the projection *distance* — the lever this rescore moves — is
  never written by the program at all. Ops 121/122 (`set_projection_distance?`) have **zero call
  sites corpus-wide**, and op 148 reads `gteH` too. **No effect program in the corpus sets the zoom.**
* The probe R3 §4a proposed — sample the registers before and after the call — **would have
  misled**: it sees no change, which is the right answer for `gteH` and the wrong one for
  `gteOFX`/`gteOFY`, precisely because op 146 restores them.

**Which ef227 phases do it**, from R3's recovered spine: `ef227:c0` **s1** (program-local ticks
95–120) and **s5** (178→end), and `ef227:c1` **s4** (117–132). Three of the eleven phases. ef227
never calls 121/122/148 at all.

**How that constrains a rescore.** Two ways, and this rung is inside both:

1. **Do not treat `gteOFX`/`gteOFY` as an authoring surface.** They are program state, written and
   restored inside a single native call, and there is no camera-block field that reaches them. A
   "recentre the frame" edit has no data lever — it would be a program edit, which is a different
   (and much more dangerous) rung.
2. **`gteH` remains a clean data lever, and it is safe at this keyframe.** The edited focal fires at
   sequence tick 11 and holds until tick 81. Mapping the program clock (c0's program starts at
   sequence tick 12): that window is entirely inside **c0 s0**, which does **not** call 146 — the
   first 146 phase, c0 s1, does not begin until sequence tick 107, well after our value has already
   been replaced by the untouched stock focal at f71. So the reframe cannot collide with a
   projection write even in principle.

Net: W1's assumption survives contact — **a camera rescore is a sequence-and-camera-data edit**, and
the program's projection writes are a disjoint, self-restoring concern.

---

## 6. THE CAST PROTOCOL

### 6.1 Deploy

The build is currently **staged, not deployed**. To deploy for real:

```
cd studies/custom-summons/tier-w
py rescore.py build bahamut_rescore.toml --live ^
   --mod-root "C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\FF9CustomMap" ^
   --work-dir C:\gd\SCRATCH\summon-format\rescore-w2
```

`--live` is required: without it the tool **refuses** any destination inside the game install. It
re-reads the install, re-applies the delta, re-runs the whole self-check, then writes
`<FF9CustomMap>\FF9_Data\SpecialEffects\ef227` and emits
`C:\gd\SCRATCH\summon-format\rescore-w2\revert_summon_camera_227.py`.

`FF9CustomMap` is first in `FolderNames`, so it wins over `MoguriMain`. If any *other* stacked folder
ships its own `FF9_Data/SpecialEffects/ef227`, check it is not earlier in the list.

### 6.2 Relaunch?

**No relaunch for the override itself** — `LoadBytes` re-reads per cast and nothing caches the
container. If the game is already running, the very next Bahamut cast picks it up.
**Relaunch IS required** if (a) the target mod folder has a `ModFileList.txt` and the build added a
line to it, or (b) you do the ability wiring in 6.3, which changes `Actions.csv`.

### 6.3 How to cast STOCK ef227 on the bench

⚠ **The bench field 30301's abilities do not currently play ef227.** "Bahamut Cinema" points at
`vfx1 = 84` and "Nimbra" at `vfx1 = 80 / vfx2 = 91` — all three are *our own private* effect folders,
which the ef227 override does not touch. Casting either of those proves nothing.

**The wiring needed — a toml edit plus a field redeploy plus a relaunch:** append one ability row to
`studies/custom-summons/rung8-epic/bench/rung8.field.toml`, at the **end** of
`[playable.abilities.command1].abilities` so the existing custom ids 194/195 do not move:

```toml
{ name = "Stock Bahamut", from = "Bahamut", targets = "AllEnemy", vfx1 = 227, vfx2 = 227, type = 0, power = 30, mp = 8 },
```

`type = 0` matters for the same reason it does for Nimbra — stock Bahamut ships `type = 4`, and with
`GARNET_SUMMON_FLAG` set that quadruples the MP cost. Then:

```
py tools/deploy_field.py studies/custom-summons/rung8-epic/bench/rung8.field.toml --id 30301
```

and **relaunch** (a `BattlePatch` / `Actions.csv` change is launch-time). In game: `~` → Warp to
field → 30301, start the bench battle, pick Iviv's *Spark* command, cast **Stock Bahamut** on the
enemy group.

**The zero-edit alternative:** any save where Garnet can summon Bahamut in a normal battle plays the
same ef227. If one is to hand, that is a cleaner proof — it is the real game's own cast path with no
bench wiring at all.

### 6.4 What you should SEE if it worked

The **first ~2 seconds** of the Bahamut cinematic — the entrance, before he closes in — are framed
completely differently: the shot is **rolled** (the horizon is on its head) and much **wider/further
out**, from a different angle. Then, about two seconds in, the camera **snaps back** to the framing
you remember, and the rest of the cast — the approach, Mega Flare, the outro — is **exactly** as
stock, landing on exactly the same beats.

Both halves matter. The re-framed opening is the mechanism proof; the untouched remainder is the
durations proof.

### 6.5 What a failure looks like

* **The cinematic is completely unchanged.** The override did not land. In likelihood order: the
  ability you cast points at one of our private ef folders instead of 227 (§6.3); the file went to
  the wrong mod folder, or is not extensionless, or the folder has a `ModFileList.txt` that does not
  list it; another `FolderNames` entry earlier in the list ships its own `ef227`. Nothing will be in
  the log either way — `suppressMissingError` is on.
* **The opening is re-framed but the beats drift.** Should be impossible — no duration byte moved —
  and would mean the two-clocks model is wrong somewhere W1 did not look. Report it; it is a finding,
  not a bug in the delta.
* **A black or frozen cast.** Revert immediately
  (`py C:\gd\SCRATCH\summon-format\rescore-w2\revert_summon_camera_227.py`) and report. The offline
  self-check says the container is structurally sound, so this would mean the pose evaluator rejects
  a value the *format* accepts — worth knowing, and cheap to bisect (drop the roll, keep H).

### 6.6 Revert

```
py C:\gd\SCRATCH\summon-format\rescore-w2\revert_summon_camera_227.py
```

Stdlib only, idempotent, and X4-proven to restore the folder to a byte-identical prior state whether
or not an `ef227` override was already there. No relaunch needed to revert the override.

---

## 7. The riskiest assumption, and what W2 does NOT settle

**The riskiest assumption is that a pose byte means what its name says.** W1 §5 is explicit: the
degree conventions `camera_codec._pose_bytes` uses are a **battle-side heuristic, not confirmed for
SFX**, and there is still no offline geometric predictor from (pitch, orientation, roll, focal) to a
world-space eye/look-at. So the *direction* and *magnitude* of the reframe are predictions, not
computations. The mitigation is that the mechanism proof does not depend on them: three independent
levers were moved by large amounts, and the projection distance is the one lever TIER R's capture
observed directly, so at least one of the three should read even if the pose conventions are wrong.
If the cast comes back "different, but not how you described" — the rung still passes; the pose
calibration is the follow-up.

Also unsettled and unchanged from W1: the frame word's high bits (never written here), the bit-3
selector's input grammar (copied verbatim), outer-flags bit 9, and movement `type` values beyond
0/1/2. All are carried verbatim rather than authored.

**And the size ceiling stands.** Same-length splices only. Adding or removing a keyframe needs an
id-2 directory writer that shifts every later sub-file and re-checks the native walker's sector sum
— that is W3's prerequisite, not a surprise to discover mid-rung.

---

## 8. Files

| file | what |
|---|---|
| `studies/custom-summons/tier-w/rescore.py` | install reader (drift-guarded) + Code field map + declarative delta + same-length splice + self-check + staging ledger + revert emitter; verbs `plan` / `build` / `verify` |
| `studies/custom-summons/tier-w/bahamut_rescore.toml` | the declarative surface — the edit above, in W1's own vocabulary |
| `studies/custom-summons/tier-w/test_rescore.py` | 34 tests; all but 6 run with no install and no corpus |
| `studies/custom-summons/tier-w/w2_gates.py` | X0–X5 |
| `C:\gd\SCRATCH\summon-format\rescore-w2\` | the staged mod root, the backups, and `revert_summon_camera_227.py` — **stock-derived, SCRATCH only** |
