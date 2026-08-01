# U2 — THE GENERALISATION CAST. Four log-only casts in one launch: ef227, ef446, ef424, ef038

> **STATE — PRE-REGISTERED, NOT YET CAST.** This document is written *before* the cast and must not be
> edited after the log is read except to append a scored result under §10. Everything in §3 is a
> prediction on the record; changing a prediction after seeing the log destroys the only thing this
> document is for.
>
> **REPAIRED PRE-CAST, after FIVE independent adversarial verifications across four rounds, and
> CLEARED TO CAST.** All five returned the same top-line verdict: **keep the vehicle** — ef227 survives adversarial testing, every archive
> figure was re-derived to the digit, and the live stock bytes hash-match the corpus dump — but the
> *scoring path* and the *owner steps* still had defects that would let an instrument artefact or an
> owner mistake be read as a result. Every repair was free: **no re-cast, no re-deploy, no rebuild, no
> change of vehicle, no change to a prediction.**
>
> - **Rounds 1–2** added the OR model (§2.1, §3.1), replaced the control gate's equality test with
>   containment where the tri-count says the key is pooled (§4.4), pre-registered a 15 bpp liveness
>   cohort (§4.6), promoted the ef424 cast from optional to required, added a third container (§5),
>   and rebuilt the failure ladder (§8).
> - **Round 4 — THE OWNER ROUND** found the sharpest class yet: **the ability window shows only FIVE
>   rows and scrolls**, so this document's own *"take the last row / the bottom one"* pointed **at the
>   decoy** (§7.0a), and **the warp box is pre-filled with `5000` and does not select-all**, so the
>   documented success signal — "the menu closes and the screen fades" — **fires for the wrong
>   destination too** (§7 step 4). It also added the one free mis-pick tell the protocol had never
>   given (**8 MP against the decoy's 56**, plus the expected creature per cast, §7.0b), dropped a
>   promise of intro BGM this install cannot keep (`MusicVolume = 0`), stated that battles run in
>   **Simultaneous** mode and that the summon therefore plays **without its cinematic camera**
>   (§7.0c), rewrote the report-back list around the rungs it actually has to decide (§7.3), gave
>   cast 4 its stakes in **both** directions (§5, §7 step 13), **split the ladder into MACHINE-fired
>   `L…`/`R…` ids and HUMAN-JUDGED `H-…` ids** — seven ids in the old table were fired by nothing and
>   two of them collided with real ones (§8, §8.0b) — and named the scorer's **real** JSON output
>   fields (§2.1; `span_matches` and `histogram_verdict` never existed).
> - **Round 4's CLOSE-OUT** fixed the last two defects of the round's own headline class, both found
>   by re-attacking the fixes rather than the protocol. **In the scorer:** the report died with a
>   traceback — taking the whole `LADDER:` line with it — on any answer slot whose rows were ALL
>   filtered out (all SPRT-sourced, or all point samples), which is exactly the shape of a null the
>   ladder exists to name; two new backstop rungs (`L0c`, `L0e`) then closed the last three routes by
>   which a mistyped flag could print a bare "SCORED / OK" over a healthy log. **All 24 rungs are now
>   driven through a real console and asserted to print their detail in full.** **In the owner steps:**
>   the New-Game route passes through a scene that **fills the party to four**, and the bench's recruit
>   seats its two characters in *empty* slots — so lingering before the warp makes it **fail silently**,
>   leaving no `Spark` and no `Rune`, and the document's only prescribed recovery (New Game) returned
>   to the same scene: **a loop.** The warp now happens first, the party is counted before the first
>   battle, and the real 20-second fix (the field menu's `Party` submenu) is named
>   (§7 steps 3–6, §8 `H-PARTY-FULL`).
> - **★ THE CALL: SHIP IT.** Round 1 found structural defects, round 2 scoring defects, round 3 a crash
>   in a rung that had never executed, round 4 the owner steps plus one more crash of that same class.
>   What remains is polish the cast itself will settle faster than another review. **Cast it.**
> - **Round 3** folded the two rival scorers into ONE (`score_uvr.py`, §9.2),
>   deleted the branch that licensed a cut-short cast as a real no-draw, made an ABSENT hard control a
>   FAIL, **inverted the operation read to SPAN-then-HISTOGRAM** because the "OR-unique" values turn
>   out to be the NO-DISPLACEMENT values (§2.1), wrote the join rule for the **three** key collisions
>   rather than one (§5.1), spent the spare MP on a **fourth cast** that replicates the arc's
>   foundational measurement in the same log (§5.4), and rewrote the owner section around what the
>   menu, the warp and the boosters actually do (§7).
>
> **WHAT IT PROMOTES.** U1 measured, at 0.97 on **one** container (ef038), that the `so` record's
> second array is a per-slot texel DISPLACEMENT baked into the primitive stream — pair position 0
> moves u, position 1 moves v, 0x80 = +128 texels. One container is not a law. This session reads
> **three more** containers and, because of how the vehicles were chosen, separates the models that
> fit ef038 equally well — and re-measures ef038 itself, in the same log, as a replication control.
>
> **COST: ZERO.** Nothing is deployed, nothing is written to the install, no field is modified, no
> revert exists because there is nothing to revert. The owner launches, casts four abilities, quits.
> The entire apparatus of `U1-SECOND-ARRAY-CAST.md` §2 — the ledger, the `pre`/`pre.ABSENT` markers,
> the emitted `revert_probe.py`, THE LEDGER TRAP — **is out of scope here.** There is no probe
> container. The one habit that survives: archive the log to SCRATCH the same session.

---

## 0. THE TWO QUESTIONS, AND WHY THIS VEHICLE ANSWERS BOTH

| | question | why it is open | what settles it |
|---|---|---|---|
| **Q1 GENERALISATION** | does the mechanism hold on a container that is not ef038? | one container, one cast | any second container's UVR log |
| **Q2 THE OPERATION** | is the halfword a texel *count*, a *boolean* meaning "+128", or a *bit set*? | ef038 carries only `{0, 0x80}` with every raw u < 128, where **add, or, and xor are all the same function** | a slot whose value is outside `{0, 0x80}` — read **SPAN FIRST to exclude NO-DISPLACEMENT, then the value histogram** to name the operation (§2.1) |

**Q2 IS AN OPERATION QUESTION, NOT A MAGNITUDE QUESTION** — and the kit's own live constant already
says so. `depth_attribution.U_DISPLACEMENT_CAVEAT` rider (2) reads: *"THE OPERATION, not merely its
size: ef038 carries only the halfword values 0 and 128, so adding 128 to the byte and toggling the
byte's top bit are THE SAME FUNCTION on every observation here."* Framing this cast as
"magnitude vs flag" would under-enumerate it and walk straight into the failure §3 exists to prevent.
On `A = 0x10` those functions come apart, and the answer slot resolves **five** of them (§3.1) — **but
only in two steps, and only in this order.** The span alone cannot tell ADD from OR; the histogram
alone cannot tell OR from a surface that never displaced at all, because **every value that separates
OR from the other displaced models is also a NO-DISPLACEMENT value** (§2.1). **THE SPAN EXCLUDES
NO-DISPLACEMENT; ONLY THEN DOES THE HISTOGRAM NAME THE OPERATION.**

**ef227 answers both in one cast** because record `0xbe020` carries `A = 0x10` — a value outside the
standard set — on a surface that is **already proven to draw** (§4.1), on a key that pools **nothing
else** (§4.2), at a depth **no ef038 measurement covered** (§3.5).

**THE CORPUS GIVES Q2 A NARROW SHOULDER.** Both independent censuses agree: of 649 binding slots
across 372 containers, exactly **14 slots in 7 containers** carry any value outside `{0, 0x80}`
(2.2%). Of those 7 containers only **two** are castable without a relaunch — ef227 and ef446 — and one
more (ef405) *looks* bench-resident but is **structurally unreachable, verifiable against engine
source** (§8.1 item 5 carries the citation). **This session spends both** (§5): if the answer surface
no-shows on ef227, the fallback data is already in the same log. Every remaining Q2 discriminator
costs a deploy and a relaunch. **The roster is therefore provably maximal for Q2 without a relaunch** —
this is not "the two we happened to find".

*(Count reconciliation, so nobody reads a contradiction: the kit's caveat says "six containers already
carry a third value" and this document says seven. Same population, different predicate — **six** carry
an outlier on the **u** axis (ef227, ef405, ef446, ef381, ef447, ef427); the **seventh**, ef261, carries
the corpus's only **v**-axis outlier, on `P = 2` records that `ORDER_UNMEASURED` forbids pairing.)*

### 0.1 A premise of the framing was backwards, and it changed the choice

The obvious reading is that a *large* outlier separates the models best. It is the opposite. Magnitude
predicts `uMin + V`; flag predicts `uMin + 128`; the gap between them is **`128 - V`**, so **smaller
outliers separate wider**. `A = 0x10` gives a 112-texel gap; `A = 0x40` gives only 64. The three
`A = 0x10` slots are the corpus's best discriminators, and ef427's `A = 0x40` — the largest outlier —
is the *weakest* of the four **on the magnitude-vs-flag axis**.

⚠ **That is not the same as "ef427 is the weakest vehicle", and the earlier draft of this document said
so wrongly.** ef427 is the corpus's *only* de-confounder for a different question entirely — see §0.2.
It is weak at Q2 and unique at Q3.

### 0.2 ★ THE ARRAY-VS-BINDING CONFOUND — unaddressed in ef038 AND in ef227

Every measurement in this arc so far reads *one* binding slot per key and compares it to *its own* raw
UV pool. That design cannot distinguish two claims:

- **THE ARRAY CLAIM** — the second array's value is what displaces. Change the value, the texels move.
- **THE BINDING CLAIM** — the *binding as a whole* (record, page, clut, geometry) is what selects a
  displaced source window, and the second array merely labels it.

ef038 cannot separate them (its displacing and non-displacing slots sit on different pages). **Neither
can ef227**, for the same reason. The separation needs two slots that are **identical in everything but
the second-array value**, and a corpus sweep found exactly one:

| | measured |
|---|---|
| containers with `so` records | 80 |
| groups sharing (page bits, clut) but differing in second-array value | **14, across 11 containers** |
| of those, groups whose *only* difference is the second-array value **on the outlier axis** | **exactly 1** |

That one is **ef427**, records `0x029844` (`A = 0x00`, `B = 0x80`) and `0x02a940` (`A = 0x40`,
`B = 0x80`): same page field `0x5A`, same clut `0x0000`, same face count, same raw u span `[0,63]`,
differing in **nothing but pair position 0**. It is the corpus's only vehicle that can attribute the
offset to the **array** rather than to the **binding**.

**ef427 therefore stays relaunch-class and second in line (§8.1), but its REASON changes from "weakest"
to "the only array-vs-binding de-confounder".** Note also that ef427 can *never* answer Q2: on its pool
`{0, 62, 63}`, ADD, OR and XOR all collapse to the identical value set `{64, 126, 127}`. It answers Q3
and nothing else. **Q3 is out of scope for this session and is recorded here so it is not lost.**

---

## 1. PREFLIGHT — measured this session, read-only, in this order

Every line below was verified against the live install at authoring time. The install is shared mutable
state and many sessions run concurrently, so **re-check items 1, 2, 6, 9 and 12 immediately before the
cast.** Item 12's booster STATE is not in any file, so it can only be re-checked in-game (§7 step 5).

⚠ **ITEM 9 IS THE ONE MOST LIKELY TO HAVE GONE STALE, AND IT IS THE ONE THAT MAKES §7's OPENING
SENTENCE TRUE.** "Launching is SAFE" holds only because the log standing in the install is already
archived byte-for-byte. **If anyone launches the game between authoring and the cast, that log is
overwritten and the archived copy no longer matches** — and launching then destroys a capture nobody
saved. **Re-hash both files immediately before step 1** (`sha256` of `<game>\sfxmeshprobe.log` against
`capture-logs\sfxmeshprobe.LIVE-preserved-2026-07-31T2106.log`). If they differ, archive the live log
under a fresh tagged name *before* launching, exactly as §7 step 15 does.

| # | check | measured | why it is load-bearing |
|---|---|---|---|
| 1 | **`[SfxHybrid] Enabled`** | **`0`** — but `EffectId = 227`, `HideNative = 1` | ⚠ **THE ef227-SPECIFIC TRAP.** This vehicle is the exact effect the hybrid drive is pinned to. If anyone re-arms it, the drive poses a managed model and suppresses the native meshes — the cast would look like it ran and log nothing on the answer key. **Check the number, not the section.** |
| 2 | **`[SfxProbe] Enabled` / `CapturePrims`** | `1` / `1` | The s77 UVR row is emitted only under `CapturePrims` (patch line 29: `if (CapturePrims && (mesh._key & HAS_TEXTURE) != 0)`). With it off, MESH rows still appear and UVR rows silently do not — **the exact shape of an instrument-defect null.** |
| 3 | **the engine DLL, BOTH arches** | sha256 `44d4b974…acf6a2`, 5,740,544 B, identical on `x64` and `x86` | Matches the recorded s76+s77 build. A mismatched arch is how a "the instrument is deployed" claim goes wrong — the launcher picks the arch, not us. |
| 4 | **field 30301 registered** | `FieldScene 30301` **and** `MessageFile 30301` present in `FF9CustomMap\DictionaryPatch.txt` | Already registered ⇒ no relaunch for the warp. |
| 5 | **bench rows 196 / 202 / 203 / 200 live** | `Actions.csv`: `Stock Bahamut;196;…;227;227;…`, `Stock Atomos;202;…;446;446;…`, `Stock Odin Short;203;…;424;424;…`, `Stock Shiva;200;…;38;38;…` | `vfx1 == vfx2` on all **four**, so the short-summon roll **structurally cannot** substitute another effect (this is what rules ef405 out, §8.1). Row 200 is the §5.4 replication cast. |
| 6 | **no override for 227 / 446 / 424 / 38** | `FF9CustomMap\FF9_Data\SpecialEffects\` holds **only `ef211`**; `FF9CustomMap-world` and `MoguriMain` have no `SpecialEffects` tree; `FF9CustomMap\StreamingAssets\Data\SpecialEffects` does not exist | The cast must read **pure stock** bytes. |
| 7 | **live stock ef227 / ef446 / ef424 == the corpus dumps** | sha256 equal on **all three**, via `rescore.read_stock_effect(N)` reading `x64\FF9_Data\resources.assets` | Re-verified by `prereg_ef227.py`, `prereg_ef446.py`, `prereg_ef424.py`, each of which **refuses to emit a prediction table** if they differ (§9.1). ef446 matters most: it is the only container with no archived draw, so a drifted dump there would go unnoticed. ⚠ **ef038 has NO pre-cast gate** — it does not need one: §5.4's expectations are the *archived measured result*, and `score_uvr.py --selftest` re-asserts them against the new log. |
| 8 | **`ModFileList.txt`** | absent at the game root, in `FF9CustomMap`, in `FF9CustomMap-world`; **present in `MoguriMain`** | ⚠ Note the law runs *backwards* for a stock cast. The SILENT-FALLBACK LAW normally warns that a listed-but-missing override reads as absent. Here we **want** stock bytes, and `MoguriMain` carries no `SpecialEffects` tree at all, so its list cannot shadow ef227 either way. Benign — recorded so nobody re-derives it under alarm. |
| 9 | **game running?** | `FF9.exe` NOT running at authoring time; the live `<game>\sfxmeshprobe.log` is **byte-identical (sha256, 27,043,776 B) to its archived copy** `capture-logs\sfxmeshprobe.LIVE-preserved-2026-07-31T2106.log` | ⇒ one launch needed. **A launch TRUNCATES the probe log** (§6.3) — but the log standing in the install right now is already saved, **so launching costs nothing.** Stated because a careful owner otherwise stops at step 1. |
| 10 | ★ **the scorer refuses the wrong log** | `py score_uvr.py <the OLD ef038 log>` returns rung **`L0b-WRONGLOG`** and scores nothing (this is the null battery's case S9, run on the real archive) | ⚠ **THE MOST DANGEROUS DEFECT THE REPAIR FIXED.** The U1 parser `v_parse_uvr.py` pins its input at module level (line 22) with **no argv override**; run "on the new cast" it silently re-reads the ef038 log and emits a confident, well-formed report containing **zero ef227 rows** — indistinguishable from "the cast never fired". §9.2 names the **one** scorer, and its log path is **positional and mandatory**. **Prove it refuses before you trust it to accept.** ⚠ The rung keys on *"not one REQUIRED cast is present"*, **never** on *"ef038 is present"* — which is what lets §5.4 put ef038 in this session's log deliberately. |
| 11 | **MP at level 1** | deployed `BaseStats.csv`: Iviv Magic **40** ⇒ **80 MP**; Steiniv Magic **12** ⇒ **24 MP** | Every stock bench row costs **8 MP** (`Actions.csv` field `mp` = 8 on all four). Iviv spends 8 of 80. Steiniv's 24 MP is **exactly three** casts and he now owns **all three** (§5). **There is no spare left** — if one of his casts must be repeated, full-heal him first (item 12). |
| 12 | ★ **the boosters, and which are armed** | live `Memoria.ini [Cheats]`: `SpeedMode 1` / `SpeedFactor 3` (**F1**), `BattleAssistance 1` (**F2**), `Attack9999 1` (**F3**), `NoRandomEncounter 1` (**F4**); `AutoBattle 1`. The three IRREVERSIBLE boosters — `MasterSkill`, `LvMax`, `GilMax` — are **all `0`** | ⚠ **The hazard is the BARE FUNCTION KEYS, not the debug menu.** F1–F4 are live at all times and F3 would end every fight on the first hit. **Reassurance worth stating to the owner: nothing reachable by accident here is irreversible.** ⚠ **The toggle STATE is not in any ini** — it lives in game state, so `No encounters` can already be ON from an earlier session on this shared install. The debug menu's **Cheats** tab draws it as `[x]` / `[  ]`; that is the only way to read it. The same tab's **Full heal party** restores HP *and* MP with no file write — that, not the save point, is the MP rescue. |

**Nothing in this table requires a relaunch to change, because nothing in it needs changing.**

---

## 2. THE DISCRIMINANT, NAMED

**Container ef227 · record `0xbe020` · P = 1 · slot 0 · `A = 0x0010`, `B = 0x0080`.**
15 bpp, page column 576, page row 256, clut word 0, 64 textured faces (all FT4), 256 UV entries.
**s77 join key `598000`** (masked `key & 0x7FFFFF`).

Raw, pre-displacement span from the container's own primitive UV bytes: **u ∈ [0, 111]**, **v ∈ [16, 127]**.

Each candidate operation was applied to the slot's **actual 256-entry UV pool**, not to its `[min,max]`
envelope — an envelope is wrong for any non-monotonic operation, and xor is non-monotonic:

| operation | predicted `uMin, uMax` | predicted `vMin, vMax` | reading |
|---|---|---|---|
| **ADD (magnitude)** `u + V` | **16, 127** | **144, 255** | the halfword is a texel count |
| **OR (bit set)** `u \| V` | **16, 127** | **144, 255** | the halfword is a bit *set* — ⚠ **same span as ADD** |
| **XOR (bit toggle)** `u ^ V` | **9, 127** | **144, 255** | the halfword is a mask toggled into the byte |
| **FLAG** (non-zero ⇒ +128 *or* ⇒ toggle bit 7) | **128, 239** | **144, 255** | the halfword is a boolean |
| **NO DISPLACEMENT** | **0, 111** | **16, 127** | — |

`ADD_MOD256` is degenerate with ADD on this slot; `FLAG_ADD128` and `FLAG_XOR128` are degenerate with
each other. **No prediction overflows the u or v byte** (max 255), so R4's wrap/clamp caveat cannot
confound this read — and §3.6 shows why no stock cast could have tested wrap anyway.

⚠ **ADD and XOR differ only at `uMin` — 16 vs 9, seven texels — and agree exactly at `uMax = 127`.**
A pre-registration carrying only "magnitude vs flag" would see `uMax = 127`, call it MAGNITUDE, and
never notice. **`uMin` is the byte that decides ADD from XOR.**

⚠⚠ **ADD and OR agree at BOTH ends.** Reading the span alone and publishing "MAGNITUDE — the halfword
is a texel count" would be wrong exactly where it matters: the kit's `eff_A_linear` / `eff_A_mod256`
do arithmetic, whereas **under OR the displacement is a NO-OP on 3 of the 5 raw values** in this pool
(25, 55, 85 all already carry bit 4). The span cannot tell them apart. §2.1 can.

★ **THE READ ORDER — SPAN FIRST, HISTOGRAM SECOND. IT IS NOT INTERCHANGEABLE.**

> **STEP 1 — THE SPAN MUST EXCLUDE NO-DISPLACEMENT.** On the answer slot that means the observed
> `uMin, uMax` reaches `16, 127` (or `9, 127`, or `128, 239`) and is **NOT** `0, 111`. Until the span
> has done that, **no histogram sighting means anything.**
>
> **STEP 2 — ONLY THEN does the histogram name the operation**, among the models the span left alive.
>
> ⚠ **WHY THE ORDER IS LOAD-BEARING, and why round 3 inverted it.** Every value that separates OR
> from the other *displaced* models — `25, 55, 85` here, `27, 55, 83` on ef446 — **is also a value of
> the NO-DISPLACEMENT set.** OR has **no** value that is unique among all six models; on ef446 its
> separates-from-all set is literally **empty**. So **a partial draw of an UNDISPLACED surface emits
> exactly the "OR" values.** An earlier draft headed that column "values unique to this model" and
> routed a sighting of `25 / 55 / 85` straight to "OR" — which would convert a null into a published
> result. The span is what makes the histogram readable; run it the other way round and the
> instrument publishes the answer it was never given.

### 2.1 ★ THE VALUE HISTOGRAM IS THE OPERATION READ — once the span has cleared it to speak

The answer slot has only **five distinct raw u values** — `{0: x32, 25: x64, 55: x64, 85: x64,
111: x32}` — so every model maps the pool onto a five-element **value set**, and a per-frame extreme
can only ever take a value **from that set**. Log the histogram of `uMin` and `uMax` across all ~292
rows instead of only their global extremes, and the models separate on values the span hides:

| model | value set on the real pool | span | **values that separate this model from the other DISPLACED models** |
|---|---|---|---|
| **NONE** | `{0, 25, 55, 85, 111}` | `0,111` | `0, 111` |
| **ADD** | `{16, 41, 71, 101, 127}` | `16,127` | **`41, 71, 101`** |
| **OR** | `{16, 25, 55, 85, 127}` | `16,127` | **`25, 55, 85`** — ⚠ every one of them is also a NONE value |
| **XOR** | `{9, 16, 39, 69, 127}` | `9,127` | **`9, 39, 69`** |
| **FLAG** | `{128, 153, 183, 213, 239}` | `128,239` | `128, 153, 183, 213, 239` |

⚠⚠ **THE COLUMN HEADING IS THE FIX, NOT A WORDING PREFERENCE.** It says *separate from the other
**displaced** models* — it does **not** say "unique to this model". `25 / 55 / 85` appear in **both**
OR and NONE; OR owns nothing that NONE does not also own. **A partial draw of an undisplaced surface
emits exactly `{25, 55, 85}`.** So:

> **THE SPAN MUST FIRST EXCLUDE NONE — `uMin` at 16 (or 9, or 128), never 0; `uMax` at 127 (or 239),
> never 111 — BEFORE ANY SIGHTING OF 25, 55 OR 85 MEANS "OR".** Without that step the sighting means
> nothing at all, and reading it as OR converts a null into a result.

**With the span clear: one sighting of 41, 71 or 101 proves ADD and refutes OR. With the span clear,
one sighting of 25, 55 or 85 proves OR and refutes ADD.** `16` and `127` are shared by ADD, OR and XOR
and decide nothing. This costs nothing extra: the rows are already in the log; the scorer just has to
count values instead of taking a min and a max (`score_uvr.py`, §9.2, does exactly this and keeps the
span read and the histogram read in **separate JSON fields** so the difference is visible, and refuses
with `R-NONE-SURVIVES` rather than naming OR when the span has not cleared NONE).

⚠ **THE FIELD NAMES, so a reader can actually find them.** An earlier draft told the reader to check
`span_matches` and `histogram_verdict`; **neither field exists and neither ever did.** The behaviour is
there and it is correct — it is carried by the fields below, in `score-out\score.<log-stem>.json`.

★ **WHERE TO LOOK: every field in this table lives on a GROUP object**, at
`effects.<effectId>.by_cast.<n>.groups[i]` — one group per `(effect, masked key)` per cast. The answer
group is the one whose `key` is `598000` and whose `is_answer_slot` is true. (`verdict`, `observed`,
`scored_on`, `tri_ratio` and `isolation` sit on the same object.)

| what you want to read | the field that carries it |
|---|---|
| **the SPAN read**, per model | `model_tests[<MODEL>].span_u` / `.span_v` (booleans), with the raw relation in `.rel_u` / `.rel_v` (`EQUAL` / `CONTAINS` / `INSIDE` / `OVERLAP` / `DISJOINT`) |
| which gate the span was gated by | `span_test_mode` — `"EQUALITY (ratio 1.00)"` or `"CONTAINMENT (pooled)"` |
| **the HISTOGRAM read** | `value_hist` (`umin` / `umax` / `vmin` / `vmax` counts) and `observed_value_set` (`u` / `v`) |
| which values could resolve the operation, and which were seen | `model_exclusive_values[<MODEL>].u_exclusive` / `.u_exclusive_observed` (and the `v_` pair) |
| whether the histogram is allowed to EXCLUDE a model at all | `value_test_decisive` — **false on a pooled key**, where a value violation is advisory because it may be foreign geometry |
| **the verdict** | `models_surviving` / `models_excluded`, plus `exact_fits` and `partial_draw_on_survivors` |

`model_tests[<MODEL>]` also carries `values_u_ok` / `values_v_ok` and `values_u_violating` /
`values_v_violating` — the per-model histogram pass and the exact values that broke it.

⚠ **"ADD = OR" IS A COINCIDENCE OF THIS POOL, NOT AN IDENTITY. A later container must not inherit a
false equivalence from this document.** On **ef381** the two give *different spans*: ADD `u[32,95]`
against OR `u[32,63]` — because that pool carries values whose low bits collide with the halfword.
The degeneracy here is a property of ef227's five values, nothing more.

**Margin robustness, measured on the pool.** Every discriminating extreme is carried by a whole
primitive band, not a stray vertex:

| extreme | comes from | support |
|---|---|---|
| NO-DISPLACEMENT `uMin = 0` | raw u = 0 | **32 entries** |
| ADD/OR `uMin = 16` | raw u = 0 | **32 entries** |
| **XOR `uMin = 9`** | raw u = 25 | **64 entries** |
| **ADD-separating `41`** | raw u = 25 | **64 entries** |
| **OR-separating `25`** *(shared with NONE — span first)* | raw u = 25 | **64 entries** |
| FLAG `uMin = 128` | raw u = 0 | **32 entries** |
| ADD/OR/XOR `uMax = 127` | raw u = 111 | 32 entries |

The archived cast draws this surface at 124.2 of 128 triangles — about **3% lost to backface culling**,
nowhere near enough to erase a 32- or 64-entry band.

**Structural bonus on the key:** this slot's clut word is 0, so the two branches of the engine's key
construction (`clut | HAS_TEXTURE` vs `HAS_TEXTURE` alone) produce the **same** value. The join key is
correct under either reading of the direct-15bpp branch.

---

## 3. THE PRE-REGISTERED READ

> **The U1 arc's one recorded process failure was a pre-registration that enumerated neither of the two
> branches that actually fired.** §3.2 therefore enumerates the model space exhaustively, including the
> three models the framing did not name, and §3.4 enumerates the split-by-family cases explicitly —
> **including the "both branches observed, split by family" case, which is what actually happened
> last time.**

### 3.1 The answer row

Log row: `UVR,227,<frame>,<index>,00598000,<src>,<prims>,<uMin>,<uMax>,<vMin>,<vMax>,<tpage>,<clut>`

**Enter this table by the SPAN column, left to right.** The histogram column is only ever read on a
row the span has already reached.

| observed span **(read this first)** | plus histogram evidence | verdict |
|---|---|---|
| **`16, 127`** | any of **`41 / 71 / 101`** seen | **ADD — the halfword is a texel count** |
| **`16, 127`** | any of **`25 / 55 / 85`** seen | **OR — the halfword is a bit set.** ⚠ Same span as ADD. Publishing "magnitude" here would be **wrong**: OR is a no-op on 3 of the 5 raw values. ⚠ **This row is reachable ONLY from the `16, 127` span** — those three values are NONE's values too (§2.1). |
| **`16, 127`** | **only `16` and `127` ever seen** | **ADD-or-OR (magnitude class), OPERATION UNRESOLVED.** Q2 answers *"not a flag, not a sentinel"* and the OPERATION sub-rider stays open (§3.4). Do not name a winner. |
| **`9, 127`** | `9 / 39 / 69` | **XOR — the halfword is a bit mask** ⚠ differs from ADD at `uMin` only |
| **`128, 239`** | `153 / 183 / 213` | **FLAG — the halfword is a boolean** (add-128 and toggle-bit-7 stay degenerate) |
| `0, 111` | `0 / 25 / 55 / 85 / 111` | the slot did not displace on u — go to §3.2, do **not** stop at "refuted", and do **not** read `25 / 55 / 85` here as OR |
| a span **narrower than** `0, 111` whose values are all NONE's | — | **NOT a result: an undisplaced surface drawing partially.** §8 `R-NONE-SURVIVES`. This is exactly the shape a mis-read publishes as OR. |
| anything else | — | §8 `L4-SPRT-CONTAMINATION` / `L5-KEY-COLLIDER` — read `src`, `prims` and the join first |

**Read the span before the histogram, and `uMin` before `uMax`.** The span's only job is to kill
NO-DISPLACEMENT; it cannot tell ADD from OR. The histogram's only job is to name the operation among
the survivors; it cannot tell OR from a surface that never moved. Three of the five branches share a
`uMax`; two share the entire span. `uMax` alone cannot tell ADD from XOR.

### 3.2 The model space, exhaustive

`u@ans` = the answer key's u span. `u@0x80` = record `0xc2254`, the 8 bpp `A = 0x80` witness (raw
u [0,127]; displaced ⇒ [128,255]) — ⚠ **pooled 2.00x, so it is a containment test, not an equality
test** (§4.4), and the clean u-arm lives on ef424 (§5.3). `v@15` = the answer key's v span (raw
[16,127]; displaced ⇒ [144,255]). `v@4` = the 4 bpp `B = 0x80` family (§4.3).

| model | `u@ans` | `u@0x80` | `v@15` | `v@4` | reading |
|---|---|---|---|---|---|
| **M1 ADD (magnitude)** | 16,127 **+ `41/71/101`** | 128,255 | 144,255 | displaced | the halfword is a texel count. **Q1 ok, Q2 ok** |
| **M1o OR (bit set)** — *not named in the framing* | 16,127 **+ `25/55/85`** | 128,255 | 144,255 | displaced | the halfword is a bit *set*. **Q1 ok, Q2 ok**, and it would mean the kit's linear column arithmetic is wrong for every value whose bits already sit in the byte. |
| **M1x XOR (bit toggle)** — *not named in the framing* | **9,127** | 128,255 | 144,255 | displaced | the halfword is a mask toggled into the byte. **Q1 ok, Q2 ok**, and it would mean the kit's linear column arithmetic is wrong for any value that is not a clean high bit. |
| **M2 FLAG (uniform)** | 128,239 | 128,255 | 144,255 | displaced | any non-zero value ⇒ +128 (or ⇒ toggle bit 7 — degenerate). **Q1 ok, Q2 ok** |
| **M3 SENTINEL** — *not named in the framing* | 0,111 | 128,255 | 144,255 | displaced | **only the literal value `0x80` is a displacement**; other non-zero values are inert or mean something else. Q1 ok (the `0x80` families generalise), Q2 answered in a third way. ⚠ degenerate with M6 — see §3.5. |
| **M4 NO GENERALISATION** | 0,111 | 0,127 | 16,127 | raw | the mechanism is ef038-specific. **Q1 refuted.** Only credible if the §4.4 controls read clean (§8 `R-UNDISPLACED`). |
| **M5 AXIS-SPLIT** — *not named in the framing* | 0,111 | 0,127 | 144,255 | displaced | position 1 displaces v; position 0 does **not** displace u on this container. Q1 partial. |
| **M6 DEPTH-SPLIT** — *not named in the framing* | 0,111 | 128,255 | 16,127 | displaced | 4/8 bpp displaces, 15 bpp does not. ⚠ degenerate with M3 on `u@ans` alone; **`v@15` separates them** — see §3.5. |
| **M7 INSTRUMENT NULL** | *(no row)* | *(no row)* | — | — | not a model. §8 `L0-*` / `L1b-15BPP-SUSPECT` / `L3a-CUT-SHORT`. |

### 3.3 Every observable, pre-registered

All eleven ef227 binding slots. "raw" = the span the container's own bytes carry; a model that does not
displace that slot predicts exactly the raw span. `drew?` is from the archived ef227 cast (§4.1).

**★ THE `tris` COLUMN IS NEW AND IT CHANGES HOW ROWS ARE SCORED.** It is the archived max per-frame
`triCount` on that key divided by the bound mesh's own textured triangles. `1.00` means the logged row
**is** that mesh and nothing else — score it by **EQUALITY**. Above `1.00` the key is **POOLED** with
geometry that carries no `so` record and appears in no census; pooling only ever **widens** a span, so
score it by **CONTAINMENT**. Below `1.00` the mesh never draws whole and a partial draw **narrows** a
span, so neither gate is sound — corroboration only.

⚠ **`facesT` COUNTS FACES, NOT TRIANGLES, AND THE TWO KINDS ARE MIXED — DO NOT DOUBLE IT.**
**Textured triangles = 2 x every 4-sided textured face + 1 x every 3-sided textured face.** Doubling
`facesT` is right only where every textured face is a quad, which is *most* rows here but **not all**:
row 8 is `FT4 x64 + FT3 x4 + F3 x8` — 76 faces, of which **68 are textured** and **132 are textured
triangles** (64x2 + 4x1), not 136; and row 4 is `GT3 x160` — **160 triangles, not 320.** §4.4 uses the
triangle number, and says there what a reader who doubles `facesT` instead would do to the session's
primary hard control.

| # | record | A | B | key | bpp | facesT | **tris** | **gate** | drew? (rows/frames) | raw u | raw v | u under M1/M1o | u under M2 | v under M1 & M2 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **1 ★ ANSWER** | `0xbe020` | `0x10` | `0x80` | `598000` | 15 | 64 | **1.00** | **EQUALITY** | **292 / 73**, frames 433–505 | 0,111 | 16,127 | **16,127** *(M1x: **9,127**)* | **128,239** | **144,255** |
| 2 ⚠ | `0xc2254` | `0x80` | `0` | `37BD80` | 8 | 96 | **2.00** | CONTAINMENT | 107 / 27, frames 422–448 | 0,127 | 2,127 | 128,255 | 128,255 | 2,127 |
| 3 | `0x2ba18` | `0` | `0x80` | `19BD00` | 4 | 24 | **14.33** | CONTAINMENT | 93 / 70, frames 58–127 | 0,191 | 1,63 | 0,191 | 0,191 | 129,191 |
| 4 | `0x8a020` | `0` | `0x80` | `18BD00` | 4 | 160 | **0.00** | n/a | **0 / 0 — SILENT** | 192,255 | 1,63 | *(no row expected)* | *(no row expected)* | *(no row expected)* |
| 5–7 | `0x8d878`, `0x8fc10`, `0xbb0d8` | `0` | `0x80` | `17BD0C` | 4 | 20,20,40 | **2.25** | CONTAINMENT | 569 / 140, frames 256–497 | 0,255 | 65,127 | 0,255 | 0,255 | 193,255 |
| **8 ★ CONTROL** | `0x29e04` | `0` | `0` | `39BE40` | 8 | 68 | **1.00** | **EQUALITY** | 93 / 70, frames 58–127 | 0,255 | 1,127 | **0,255** | **0,255** | **1,127** |
| **9 ★ CONTROL** | `0x8c408` | `0` | `0` | `3DBE00` | 8 | 32 | **1.00** | **EQUALITY** | 15 / 11, frames 167–177 | 0,127 | 1,127 | **0,127** | **0,127** | **1,127** |
| 10 | `0x8dcbc` | `0` | `0` | `3BBD40` | 8 | 192 | **0.70** | corroboration | 564 / 167, frames 178–380 | 0,254 | 1,255 | 0,254 | 0,254 | 1,255 |
| 11 | `0xbc2fc` | `0` | `0` | `3DBEC0` | 8 | 60 | **4.47** | CONTAINMENT | 492 / 67, frames 440–506 | 0,63 | 1,191 | 0,63 | 0,63 | 1,191 |

⚠ **ROW 2's KEY `37BD80` IS A CROSS-CONTAINER COLLIDER** — ef424 binds the same masked key with a
**different** `(A,B)` (`0x80,0x80` against this row's `0x80,0`), and both casts land in one log. A
key-only join would make this **u-only** witness appear to displace **v** as well. §5.1 lists all three
collisions and the join that defuses them.

Rows 8–11 are the in-cast `(0,0)` controls (§4.4) — **bold** now marks only the two that a model must
reproduce *exactly*. Rows 5–7 pool onto one key but are **value-homogeneous** (all three carry the same
`(0, 0x80)` and the same raw span), so that pooling costs nothing. Row 4 is pre-registered as
**bound-never-drawn**: its absence is expected and is **not** a failure (§8 `H-REAL-NO-DRAW`).

**★ ROW 1 IS THE ONLY OPERATION LEVER IN ef227.** Applying every candidate operation to every
displacing slot of ef227 *and* ef424: row 1 yields **five** distinct value sets; every other slot
yields at most **two** (displaced / not), because their value is `0x80` and their raw spans sit below
128, where add, or and xor coincide exactly as they do on ef038. Every other slot can testify that the
mechanism *fired*; **only row 1 can say what it did.** ef446's answer slot is the second such lever and
is cast in the same session (§5.2).

### 3.4 The split cases, explicitly

The failure this document exists to prevent is scoring a mixed result as a single verdict. All of these
are legal outcomes and each has a name:

| observed pattern | verdict | note |
|---|---|---|
| every displaced slot moves, answer key at `16,127` **with `41/71/101`** | **M1 ADD**, clean | promote with the §3.5 scope caveat |
| every displaced slot moves, answer key at `16,127` **with `25/55/85`** | **M1o OR**, clean | promote, **and flag the kit's `eff_A_linear` / `eff_A_mod256` arithmetic for review** |
| every displaced slot moves, answer key at `16,127`, **no separating value ever seen** | **MAGNITUDE CLASS, operation unresolved** | Q1 answered, Q2 half-answered. **Write it that way.** Keep the OPERATION sub-rider open and hand it to ef446 (§5.2), whose separating values are `43/71/99` (ADD) and `27/55/83` (OR) — and read ef446's span first too, for the same reason (§2.1). |
| every displaced slot moves, answer key at `9,127` | **M1x XOR**, clean | promote, **and flag the kit's linear column arithmetic for review** |
| every displaced slot moves, answer key at `128,239` | **M2 FLAG**, clean | promote with the §3.5 scope caveat |
| ★ **ef227 says one operation and ef446 says another** | **BOTH BRANCHES OBSERVED, SPLIT BY CONTAINER** | **This is the case the arc has actually hit before.** Do not average it and do not pick the prettier one. Record both spans, both histograms, both containers, and stop — the mechanism is not container-uniform and that is itself the finding. |
| ★ **the same container's rows split by FRAME — early frames raw, late frames displaced (or vice versa)** | **TEXANIM DRIFT, not displacement** | §8 `H-TEXANIM-DRIFT`. The W7 texture-animation lane rewrites display-list UVs mid-cast. This hypothesis is **outside** the model space above and must not be fitted into it. |
| all `0x80` slots move, answer key alone reads raw | **M3 or M6** — read `v@15` next | §3.5 |
| all v slots move, no u slot moves (incl. row 2 and ef424's `37BC80`) | **M5** | position 0 is not a u displacement here |
| all 4 bpp/8 bpp slots move, the 15 bpp answer reads raw **on both axes** | **M6** | 15 bpp is the exception — but first clear §4.6, or this is an instrument null wearing M6's clothes |
| some `0x80` slots move and others do not, **not** split by axis or depth | **UNMODELLED** | do not force it into M1–M6; record the split and stop |
| nothing moves, controls clean | **M4** — Q1 refuted | §8 `R-UNDISPLACED` — and only after the §4.4 self-test passes |
| nothing moves, controls **not** clean | **NOT A RESULT** | §8 `L6p-CONTROL-FAIL` — instrument defect |
| nothing moves and a hard control is **ABSENT** rather than wrong | **NOT A RESULT** | §8 `L6q-CONTROL-ABSENT`. An absent ratio-1.00 control is the signature of a partial log, a wrong window, or an early-frame emission failure — never a licence to score. |
| ★ **ef038's replication arms disagree with the archived U1 result** | **THE SESSION IS VOID** | §8 `L9-REPLICATION-FAILED` (§5.4). Nothing else in the log may be scored, whatever it says. |

### 3.5 ★ THE SCOPE CAVEAT — value and depth are perfectly confounded corpus-wide

Measured independently by both censuses over all 649 slots:

- 15 bpp displacing slots: **14**. Their `A` values are only `{0, 0x10, 0x20, 0x40}`.
- **15 bpp slots carrying `A = 0x80`: ZERO.**
- **Non-15 bpp slots carrying an `A` outside `{0, 0x80}`: ZERO.**

**Every outlier value in FF9 lives at 15 bpp, and every `0x80` lives at 4 or 8 bpp.** The consequence is
sharp and nobody gets to wish it away:

1. **M3 (sentinel) and M6 (depth-split) cannot be separated on the u axis by any cast of any stock
   container.** The corpus contains no 15 bpp `A = 0x80` slot and no 8 bpp `A = 0x10` slot.
2. **But ef227 breaks the confound in-cast, on the v axis, for free.** The answer slot is 15 bpp *and*
   carries `B = 0x80`. If `v@15` reads `144,255`, then 15 bpp demonstrably displaces — **M6 is dead**
   and a raw `u@ans` is M3 or M5. This is why `B = 0x80` on the answer slot is not merely a positive
   control: **it is the depth-confound breaker**, and it is the single strongest reason to prefer ef227
   over any other vehicle. §4.5 explains why it is also the *only* in-frame positive control there is.
3. **Even a clean M1 read licenses "magnitude, at 15 bpp".** The arc has no stock witness anywhere for
   a magnitude-valued displacement at 4 or 8 bpp, and cannot obtain one. Any constant or doc text
   promoted from this cast must carry that scope, or it will be a wish in a docstring.

### 3.6 ★ THE WRAP/CLAMP QUESTION IS FORECLOSED — stop carrying it as castable

R4 left open whether a displacement that would push a byte past 255 wraps or clamps. **No stock cast of
any container can ever test it**, and the corpus says so without ambiguity. Over the 468 slots whose UV
pool resolves offline (of 649 total):

| | measured |
|---|---|
| slots carrying `A = 0x80` | **150** (104 with a resolvable pool) — **max raw `uMax` among them: 127** |
| slots carrying `B = 0x80` | **216** (160 with a resolvable pool) — **max raw `vMax` among them: 127** |
| resolved slots with raw `uMax >= 128` | **140** — of which carrying **any** u displacement: **0** |
| resolved slots with raw `vMax >= 128` | **96** — of which carrying **any** v displacement: **0** |
| exceptions, either axis | **0 of 468** |

Displacement is **perfectly anti-correlated** with high raw UV. Whoever authored these containers never
displaced a page that was already in the high half — so no stock byte, anywhere, is in a position to
overflow.

★ **THE ANSWER CONTAINER DEMONSTRATES THE LAW INSIDE ITSELF, on one record.** §3.3 row 4
(`0x8a020`, `A = 0`, `B = 0x80`) carries raw **u `[192,255]` — the high half — with NO u
displacement**, and raw **v `[1,63]` — the low half — WITH v displacement.** Both halves of the
corpus-wide anti-correlation, on the two axes of a single slot. That is worth saying plainly: the law
is not an artefact of aggregating 468 slots, it is visible one record at a time. (Row 4 is also the
pre-registered bound-never-drawn slot, so it testifies offline and is expected to be silent in the
log — see §8 `H-REAL-NO-DRAW`.)

**The arc should stop listing wrap-vs-clamp as an open castable question.** It is answerable
only by *writing* a displacement onto a high-UV slot ourselves, which is a repaint experiment, not a
measurement, and belongs to a different rung.

---

## 4. THE IN-CAST CONTROLS

### 4.1 BINDING-IS-NOT-A-DRAW — satisfied **before** the owner is asked for anything

The arc's standing law, and its DEPTH COROLLARY, say a record stating a binding is no evidence anything
sampled it. It has cost this arc real rounds (ef429 lawful but bound-never-drawn after three probe
casts; ef211's wheel invisible twice). It is satisfied here **offline, from an archive**, not promised:

In `capture-logs\sfxmeshprobe.pre-odin-cast.2026-07-28.log`, ef227 emits **15,031 MESH rows over 504
distinct frames spanning [11..515]** — 504 of 505 possible frames, i.e. one contiguous cast, not an
aggregate of several. The answer key `598000` accounts for **292 rows over 73 distinct frames
[433..505]**, 36,280 triangles. That is **124.2 tris/row against the slot's 64 quads = 128 triangles** —
the whole surface, minus backfaces.

**The one inference, and it is now empirical.** That archive predates s77 and has zero UVR rows, so it
proves MESH emission, not UVR emission. The bridge — "a textured MESH row carries a UVR row" — was
checked against the s77 log rather than taken from the patch's comment: ef038 emitted **9,449 MESH and
8,587 UVR** rows, and the difference of **862** is *exactly* the row count of the untextured key
`000000`. Zero UVR rows lack a MESH row. The join is 1:1 and total over textured meshes.

★ **AND IT HOLDS EXACTLY PER DEPTH, not merely in aggregate.** Counting ef038's s77 log by the key's
own depth field: **4 bpp — 3,479 textured MESH rows and 3,479 UVR rows. 8 bpp — 5,108 and 5,108.**
Two depths, two exact identities, no residue. An aggregate match could hide an offsetting pair of
errors; a per-depth match cannot.

⚠ **That bridge has been exercised at 4 bpp and 8 bpp only** — because those are the only depths
ef038 has ever drawn textured (§4.6). Every Q2 discriminator is 15 bpp.

### 4.2 Key isolation — against the DRAW population, not just the census

The weaker claim is "no other `so`-census slot in ef227 shares key `598000`". That is true but
insufficient: ef227 also draws its creature lane and a SPRT lane, and **neither carries an `so` record,
so neither appears in any census.**

Measured against the archive instead: **37 distinct masked keys drew in ef227. Exactly one masks to
`598000`, and it has exactly one raw form (`00598000`)** — one ABR, no FILTER bit. Nothing else in the
container's entire draw population pools into the answer row. The tri-count confirms it independently:
`598000`'s max per-frame `triCount` is **128**, exactly the mesh's own 128 textured triangles —
**ratio 1.00, the only clean u measurement in the whole arc** (§4.7).

⚠ Confusable neighbours a sloppy join would catch: `408000` and `428000` both end `8000`. **Match the
full masked key, never a suffix.** (Those two are not merely confusable — they are load-bearing in
their own right now: they are the 15 bpp liveness cohort, §4.6.)

### 4.3 The displaced controls — Q1's second and third witnesses

Rows 2, 3 and 5–7 of §3.3. Row 2 (`A = 0x80`, 8 bpp) is the u-axis replication; rows 3 and 5–7
(`B = 0x80`, 4 bpp) are the v-axis replication at a **third** depth. Three of ef038's four `(A,B)`
families reproduce on independent bytes in this one cast. ef227 has no `(0x80, 0x80)` slot; that
family comes from **cast 3**, ef424 (§5.3).

⚠ **BUT ROW 2 IS POOLED 2.00x, SO ef227 ALONE CANNOT ATTRIBUTE Q1's u ARM.** Its logged span can only
be tested for *containment* of `[128,255]`, and a containing span is consistent with "the bound mesh
displaced" **and** with "foreign geometry natively sits high". **This is why the ef424 cast is required,
not optional** — ef424's `37BC80` is the arc's clean, isolated `A = 0x80` u witness (§5.3).

### 4.4 ★ THE (0,0) CONTROLS ARE THE INSTRUMENT'S SELF-TEST — scored by the RIGHT gate

Rows 8–11. Four slots carrying `(0, 0)`, whose spans are **four distinct, non-trivial values**:
`u [0,255] / [0,127] / [0,254] / [0,63]` and `v [1,127] / [1,127] / [1,255] / [1,191]`.

This control does two jobs:

1. **It tells a displaced span from a container that merely uses high UVs.** Rows 5–7 raw-span u to
   `[0,255]` and row 8 to `[0,255]` with *no* displacement at all. Without the controls, "high numbers
   in the log" proves nothing.
2. **It converts an ambiguous null into a decidable one.** If the instrument demonstrably measures real
   per-mesh UV bytes on this container in this cast, then **a null on the displaced slots is a
   MEASUREMENT, not a defect.** If it does not, nothing else in the log may be scored at all.

⚠ **THE EARLIER DRAFT GOT THE GATE AND THE ROSTER BOTH WRONG.** It demanded that the log *"reproduce
all four control spans EXACTLY"* and named rows **8, 10 and 11** as the load-bearing three. A tri-count
test says row 11 is pooled **4.47x** and row 10 never draws whole (**0.70**), so an exact-equality gate
**fails on row 11 for an artefact** and makes the publishable-negative rung (§8 `R-UNDISPLACED`) unreachable. The
two clean controls are rows **8 and 9** — and row 9 is the one the draft demoted to "thin".

⚠ **READ "mesh's own tris" AS TRIANGLES, AND DO NOT RECOMPUTE IT BY DOUBLING `facesT`.**
**Textured triangles = 2 x every 4-sided textured face + 1 x every 3-sided textured face.** Row 8 is
the case that bites: its buckets are `FT4 x64 + FT3 x4 + F3 x8` — **76 faces, 68 of them textured,
132 textured TRIANGLES** (64x2 + 4x1). `132 / 132 = 1.00`. A reader who doubles the 68 gets 136,
computes `132 / 136 = 0.97`, and by this document's own rule ("below 1.00 buys corroboration and
nothing else") **demotes the session's PRIMARY hard control**, leaving only the thin one. One
sentence prevents it, so here it is twice (§3.3 carries the other copy).

| row | key | records bound | max tris logged | mesh's own tris | **ratio** | **gate** | what a miss means |
|---|---|---|---|---|---|---|---|
| **8** | `39BE40` | 1 | 132 | 132 | **1.00 ISOLATED** | **EQUALITY — hard stop** | instrument defect. Score nothing. |
| **9** | `3DBE00` | 1 | 64 | 64 | **1.00 ISOLATED** | **EQUALITY — hard stop** | instrument defect. Score nothing. Thin (15 rows / 11 frames) but *clean*, which beats thick and pooled. |
| 11 | `3DBEC0` | 1 | 536 | 120 | 4.47 POOLED | CONTAINMENT — soft | expected to contain `u[0,63] v[1,191]`. A miss is a flag to investigate, **never** a hard stop. |
| 10 | `3BBD40` | 1 | 270 | 384 | 0.70 PARTIAL | corroboration only | the mesh never draws whole; a partial draw narrows a span, so **neither** gate is sound here. |
| — | `17BD0C` | 3 | 360 | 160 | 2.25 POOLED | CONTAINMENT — soft | the value-homogeneous v-family (rows 5–7). |
| — | `19BD00` | 1 | 688 | 48 | 14.33 POOLED | CONTAINMENT — soft | the most heavily pooled key in the container. |
| — | `37BD80` | 1 | 384 | 192 | 2.00 POOLED | CONTAINMENT — soft | row 2, the u-axis replication (§4.3). ⚠ **CROSS-CONTAINER COLLIDER** — the same masked key is ef424's `(0x80,0x80)` slot (§5.1, §5.3). |

**THE RULE:** *equality* on the ratio-1.00 keys is the hard gate; *containment* on the pooled keys is a
soft check; a ratio below 1.00 buys corroboration and nothing else. **THE U1 CAST-1 MISTAKE IS THE ONE
THIS PREVENTS** — that cast returned a null that was read as evidence and turned out to be an
instrument defect. **No verdict of any kind is entered until rows 8 and 9 pass equality.**

⚠⚠ **AN ABSENT HARD CONTROL IS A FAIL, NOT A SHRUG.** A ratio-1.00 equality control that emitted
**nothing** used to be recorded as "no rows, not gating" — which let **both** hard controls go missing
while the run still scored. An absent hard control is the signature of a partial log, a wrong frame
window, or an early-frame emission failure; every one of those invalidates everything downstream.
It must be **PRE-REGISTERED** rather than derived from the log, because an absent key has no tri
ratio at all — log-derived isolation literally cannot tell "the control failed" from "the control
never arrived". **The roster: ef227 `39BE40` + `3DBE00`; ef424 `19BD04` + `37BCC0`; ef446 NONE (no
archived draw, so every key scores UNPROVEN by construction); ef038 NONE (its `(0,0)` key `3ABD40`
measures ratio 0.52 — the mesh never draws whole, so neither gate is sound).** Absent ⇒ §8
`L6q-CONTROL-ABSENT`, and nothing is scored.

### 4.5 ⚠ THERE IS NO CO-TEMPORAL UNPOOLED CONTROL — the answer's own v axis is the only one

The answer surface draws in frames **[433..505]**. Every other ef227 key that draws in that window is
**pooled**:

| key | frames | ratio |
|---|---|---|
| `3DBEC0` | 440–506 | 4.47 POOLED |
| `37BD80` | 422–448 | 2.00 POOLED — ⚠ also ef424's key (§5.1) |
| `17BD0C` | 256–497 | 2.25 POOLED |

The two ratio-1.00 controls draw at **[58..127]** and **[167..177]** — entirely **before** the answer
window. So a defect that begins mid-cast (a state change, a page upload, a texanim arm) would be
invisible to the clean controls by construction.

**Consequence, stated plainly rather than as a bonus:** the answer slot's **own v axis** — `B = 0x80`,
predicted `v[144,255]` under every displacing model against raw `v[16,127]` — is the **SOLE in-frame
positive control this cast has.** §3.5 (2) uses it as the depth-confound breaker; §4.4's clean rows
cannot corroborate it because they are not on screen at the same time. If `v@15` reads `144,255` while
`u@ans` reads raw, that is a real axis split (M5) measured by the only witness in the room.

### 4.6 ★ THE 15 BPP LIVENESS COHORT — pre-registered, because 15 bpp has NEVER HAD THE CHANCE to emit

Counted across **all nine archived logs**: the s77 instrument has emitted UVR rows for exactly **one**
effect (ef038, **8,587** rows), and their depths are `tp` **0 and 1 only** — **3,479** at 4 bpp,
**5,108** at 8 bpp, and **ZERO at 15 bpp**. Every one of the six A-outlier discriminators is `tp = 2`.

★ **THAT ZERO IS FULLY EXPLAINED OFFLINE, AND ROUND 3 DE-ESCALATED THIS SECTION TO MATCH.** Counting
**textured MESH** rows by depth across **all five ef038 logs**: **`tp = 0` 19,916 · `tp = 1` 29,574 ·
`tp = 2/3` ZERO.** **ef038 draws no textured 15 bpp geometry at all** — the only vehicle s77 has ever
run on has never presented the instrument with a 15 bpp textured mesh. So "s77 has never emitted a
15 bpp UVR row" is a statement about **the absence of an opportunity**, not about a code path that
might be broken, and the two must not be conflated: an untried path with no counter-evidence is a
much weaker worry than a path that was tried and failed. **Nothing here has ever failed.**

What remains true, and is why the cohort is still pre-registered: the path is **untried**, so it
cannot be *asserted* either. `SFXKey.cs` was read — the `num >> 5 == 2` branch is dead as written, but
`clut == 0` makes both branches yield `0x598000` anyway, and an archived MESH row already proves
`mesh._key == 00598000`. **An UNTESTED path, not a known break** — and the whole §8.1 fallback chain
is 15 bpp too, so a blind retry would loop through the same untested path.

**The fix is free, because ef227 already draws two other `tp = 2` keys that carry no `so` record:**

| raw key | masked | tx, ty, tp | archived rows / frames | window |
|---|---|---|---|---|
| `24C08000` | `408000` | 0, 0, **2** | 212 / 64 | [167..432] |
| `24C28000` | `428000` | 2, 0, **2** | 212 / 64 | [167..432] |

Both draw **before** the answer window and neither is in any census. **Pre-registered reading:**

| observation | verdict |
|---|---|
| the cohort emits UVR rows and `598000` does too | 15 bpp is live and the answer is scoreable — proceed to §3.1 |
| the cohort emits UVR rows and `598000` does not | **the 15 bpp path was alive BEFORE frame 433 — and that is ALL it says.** It is **NOT** a licence to call the missing answer a real no-draw. Go to §8 `L3a-CUT-SHORT` and read the **late** witnesses. |
| **NO `tp = 2` key anywhere in the log emits a UVR row** | ⚠ **SUSPECT THE INSTRUMENT (§8 `L1b-15BPP-SUSPECT`). Score nothing 15 bpp.** Not a result, and not a reason to try the next 15 bpp fallback |

⚠⚠ **THE COHORT CANNOT SPEAK TO THE ANSWER WINDOW, AND ROUND 3 DELETED THE BRANCH THAT SAID IT
COULD.** The cohort draws over frames **[167..432]**; the answer surface draws over **[433..505]**.
Those windows are **adjacent and disjoint**. A cast quit at frame ~430 leaves the whole cohort and
every early control looking perfectly healthy while the answer never had a chance to draw — and the
pre-round-3 scorer issued a *"the 15 bpp path works, so this is a real no-draw"* licence on exactly
that evidence. The only sound witness for "the cast ran long enough" is a key that draws **inside or
after** the answer window: `3DBEC0` (~440–506) and `37BD80` (~422–448) — both read as
`(227, key)`, since `37BD80` is also an ef424 key (§5.1). See §8 `L3a-CUT-SHORT`.

⚠ Both cohort keys carry high bits in their raw form, so they may log as `src = S`. That is fine for a
*liveness* question — the gate is `CapturePrims && (key & HAS_TEXTURE)`, and both keys set bit 15 — but
it means the cohort proves *emission at 15 bpp*, not *emission on the P path at 15 bpp*.

★ **THE ONLY P-PATH 15 BPP WITNESS IN THE SESSION IS ef424's `598000`, AND IT LIVES ON THE CAST THE
DEGRADATION RULE USED TO DROP FIRST.** All 212 of ef227's cohort rows on each cohort key carry the
high-bit raw form, so they will almost certainly log as the sprite path. ef424's `598000` is the
session's **only** key whose raw form carries no high bits and therefore rides the polygon path at
`tp = 2` — about **~65 of that key's ~103 rows per cast** (§5.3 on why every archived ef424 figure
halves). §5 states the consequence plainly: **a two-cast degradation
forfeits the P-path 15 bpp liveness check** — it does not merely "weaken a corroboration".

### 4.7 ★ ef038's u ARM RESTS ON A NON-ISOLATED KEY — and that strengthens this vehicle

Applying the same tri-count test backwards to the U1 measurement:

| ef038 key | records bound | ratio | what it can support |
|---|---|---|---|
| `3ABDC0` (**the u arm**) | **20** | **0.31** | ⚠ one cannot formally exclude *"the 20 bound meshes never drew and those triangles are foreign geometry that natively sits at u >= 128"* |
| `38BE00` (the v arm) | 1 | **1.00** | airtight — single record, prims constant at 72 |

**Only ef038's v arm is airtight.** Its u arm is suggestive, not proven. **This is an argument FOR
ef227, not against U1:** the answer key's ratio-1.00 isolation would make it **the first isolated u
measurement in the entire arc.** The document should say so rather than presenting ef038's u result as
settled — and §10's follow-on text must not inherit the overstatement.

---

## 5. ★ THE SESSION IS FOUR CASTS, NOT ONE — and only the last is droppable

The earliest draft offered ef424 as "optional, worth doing". It is not optional: **ef227 alone cannot
attribute Q1's u arm**, because its only `A = 0x80` slot is pooled 2.00x (§4.3). A third container
fits for free (§5.2), which converts the worst null in the ladder from "come back for another session"
into "the fallback data is already in the log". And round 3 found the budget already held **a fourth
cast nobody had spent** (§5.4).

**MP arithmetic, measured (§1 item 11):** every stock bench row costs **8 MP**. ef227 is Iviv's (Spark,
row 196), and Iviv has **80 MP** — one cast of ten. ef446, ef424 and ef038 are Steiniv's (Rune, rows
202, 203 and 200), and Steiniv has **24 MP = exactly three** casts. **All three are now spent, exactly.**
There is no MP margin left; if a Steiniv cast must be repeated, full-heal him from the debug menu's
**Cheats → Full heal party** first (§7), which writes nothing.

| order | cast | menu | container | ~length | what it uniquely buys |
|---|---|---|---|---|---|
| **1** | **Stock Bahamut** (row 196) | Iviv → Spark | **ef227** (§2) | **36.5 s** (547 sfx ticks) | **THE ANSWER.** The isolated `A = 0x10` operation lever, the depth-confound breaker, the 15 bpp liveness cohort |
| **2** | **Stock Atomos** (row 202) | Steiniv → Rune | **ef446** (§5.2) | **11.0 s** (165 sfx ticks) | **THE SECOND OPERATION LEVER** — the pre-emptive rescue, and the only container whose draw nobody can prove offline |
| **3** | **Stock Odin Short** (row 203) | Steiniv → Rune | **ef424** (§5.3) | **3.9 s** (59 sfx ticks) | **Q1's CLEAN u ARM** + two ratio-1.00 `(0,0)` controls + the `(0x80,0x80)` family + the session's **only P-path 15 bpp liveness witness** (§4.6) + a free ORDER_UNMEASURED probe |
| **4 ★** | **Stock Shiva** (row 200) | Steiniv → Rune | **ef038** (§5.4) | **24.3 s** (364 sfx ticks) | **THE REPLICATION.** A same-log, same-launch, same-DLL re-measurement of the arc's foundational 0.97 result — the session's only defence against a session-level instrument regression |

**THE ORDER IS DELIBERATE.** Cast 1 is the answer, so it goes first and is on disk before anything can
go wrong. **Cast 2 is the rescue** — it is what turns §8 `H-REAL-NO-DRAW` ("the answer surface never drew") from
"come back for another session" into "the rescue data is already in the log", and that only works if
it is cast *before* the session degrades. Cast 3 carries evidence nothing else in the session carries.
Cast 4 validates the instrument for the whole session and is cheap, but it validates rather than
measures, so **it is the one to drop.**

⚠⚠ **"THE ONE TO DROP" IS NOT "THE ONE THAT DOES NOT MATTER", AND THE OWNER MUST BE TOLD BOTH HALVES.**
Cast 4 is the only cast in this session that can **void** it: if its arms disagree with the archived
result, casts 1–3 are discarded however clean they look (§8 `L9-REPLICATION-FAILED`). It is also the
only cast whose *absence* costs nothing that can be recovered later — **the check has to live in the
same log**, so a skipped replication cannot be added afterwards by any means. **It is last because it
is the cheapest to lose, not because it is optional**, and §7 step 13 now says so at the point of
decision.

⚠ **THE DEGRADATION RULE, AND WHAT EACH STEP DOWN ACTUALLY COSTS.** State the forfeit; do not call it
"weaker corroboration".

| if only … fit | do | what is forfeited |
|---|---|---|
| **four** | 1, 2, 3, 4 | nothing |
| **three** | **1, 2, 3** | ★ **the replication control** (§5.4). Read the forfeit in full: casts 1–3 would be published **with no evidence at all that the instrument was healthy during the session that produced them** — the engine hash was taken before the launch and cannot see a runtime regression, and the check is only valid **in the same log**, so it cannot be added later. An instrument regression that hit this whole session would go unseen, and `L9-REPLICATION-FAILED` cannot fire because there is nothing to fire on |
| **two** | **1, 2** | the above **plus Q1's clean u arm, both of ef424's ratio-1.00 controls, and the session's ONLY P-path 15 bpp liveness witness** (§4.6). The 15 bpp emission check degrades to the sprite-path cohort alone. |
| **one** | **1** | everything above **plus the rescue**: if ef227's answer surface no-shows, the session produced nothing and must be re-run |

**Durations are from the arc's own measurement, not estimates:**
`studies/custom-summons/rung8-epic/census/summon_durations.csv` — ef227 547 sfx ticks / 36.47 s
(38.13 s with the cast wrapper), ef038 364 / 24.27 s (26.53 s), ef446 165 / **11.0 s** (12.67 s),
ef424 59 / 3.93 s (5.60 s). **~76 s of animation across the four**, which is why the owner's real time
goes on the route, not on the casts.

⚠ **PREFER ONE ENCOUNTER PER CAST.** The bench rows are `power 30 AllEnemy` and may end the fight
before the second action. **The probe log is session-cumulative** — it truncates at *launch*, not at
battle end (§6.3) — so **four** separate encounters cost only walking time and lose nothing.

⚠ **THE "CAST IT FIRST AND ALONE (SHARED VRAM)" RULE IS DROPPED.** It was inherited from the *visual*
U1 protocol, where VRAM contention genuinely mattered because the verdict was a screenshot. **The s77
UVR row accumulates the primitive struct's OWN u,v bytes out of the display list**, so nothing another
effect does to video memory can change a logged value. Keeping the rule would block the four-cast
session for no measurement benefit. **What replaces it:** if per-frame spans *drift* within one cast in
a way partial draw does not explain, suspect the **W7 TEXTURE-ANIMATION lane** rewriting display-list
UVs mid-cast — not the displacement. That hypothesis is deliberately **outside** the §3.2 model space
and lands as its own ladder rung (§8 `H-TEXANIM-DRIFT`).

### 5.1 ⚠ THE JOIN RULE — a key-only join does not blur this read, it MANUFACTURES EVIDENCE

**THERE ARE THREE CROSS-CONTAINER KEY COLLISIONS IN THIS SESSION, NOT ONE.** The earlier draft wrote
the rule for the first and named neither of the others — and it printed `37BD80` as ef227's key in two
places and as ef424's in a third with no cross-note that they are **the same key**, and did the same
with `3BBDC0`. **Write the assertion for a SET.** Enumerated from the gates
(`prereg_ef446.py` emits `cross_container_collisions`):

| masked key | claimed by | second-array value | why it is dangerous |
|---|---|---|---|
| **`598000`** | ef227 `0xbe020` **(the ANSWER)** · ef424 `0x29f88`, `0x2bc94` | `A=0x10 B=0x80` vs `A=0x00 B=0x80` | ef424's contributes `uMin = 0` under *every* model ⇒ the pooled row reads the **NO-DISPLACEMENT signature** for the answer. **A false refutation.** |
| **`37BD80`** | ef227 `0xc2254` (§3.3 row 2) · ef424 `0x2d334` (§5.3) | `A=0x80 B=0x00` vs `A=0x80 B=0x80` | ⚠ **WORSE THAN THE FIRST, and it was unnamed.** It merges two *displacing* slots with **different `(A,B)`** — a key-only join makes ef227's **u-only** witness appear to displace **v as well**. **That is manufactured evidence for the very models this cast exists to separate.** |
| **`3BBDC0`** | ef424 `0x2f9a4` (the `P = 2` slot 1) · ef446 `0x2c084` (a `(0,0)` control) | `A=0 B=0` on both | The mildest of the three — but it silently pools ef446's control with ef424's ORDER_UNMEASURED probe, so a control "failure" could be another container's geometry. |

**Every one of the three is invisible until two of this session's casts share a log — which is the
whole design.** Cast them separately and the collisions do not arise; cast them into one file, as this
protocol requires, and a key-only join is guaranteed to hit all three.

**THE RULE: join every UVR row on `(effectId, key & 0x7FFFFF)`. Never on the key alone. Never on a
substring. Never on the raw key either** — ef424's `598000` collider has **two** raw forms,
`00598000` and `00D98000`, and the first is **byte-identical** to ef227's answer key. The `0x7FFFFF`
mask is what makes the two forms one key: **bit 23 is ABR**, which at draw time comes from the
primitive's flag byte, not the tpage word.

**The scorer enforces it as a set, not as a special case:** every masked key carried by more than one
effect is listed in `join_evidence['colliders']` with which effect claims it as an answer slot, and
`L5-KEY-COLLIDER` fires stating what a key-only join would have merged. No row credited to
`(227, 598000)` may carry `effectId != 227`, and the run refuses if one does (§9.2).

### 5.2 ef446 `Atomos__Short`, bench row 202 — the SECOND operation lever, cast pre-emptively

Same `A = 0x10 / B = 0x80` signature as ef227's answer, on a **much larger surface**: record `0x2d134`,
15 bpp, **288 faces / 768 UV entries** against ef227's 64 / 256. Key **`578000`**, and **no other ef446
census slot shares it**. Raw pool `u [0,111]`, `v [16,127]`.

Its value sets differ from ef227's, which is the point — it is an **independent** operation read:

| model | value set | span | values that separate this model from the other DISPLACED models |
|---|---|---|---|
| NONE | `{0, 27, 55, 83, 111}` | `0,111` | `0, 111` |
| **ADD** | `{16, 43, 71, 99, 127}` | `16,127` | **`43, 71, 99`** |
| **OR** | `{16, 27, 55, 83, 127}` | `16,127` | **`27, 55, 83`** — ⚠ every one of them is also a NONE value |
| **XOR** | `{11, 16, 39, 67, 127}` | `11,127` | **`11, 39, 67`** |
| FLAG | `{128, 155, 183, 211, 239}` | `128,239` | `128, 155, 183, 211, 239` |

⚠ **Three of those cells were wrong before round 3 and the gate caught them** (`prereg_vs_document.py`,
§9.1): ADD was written `43, 99` — **71 was missing**; OR was written `27, 83` — **55 was missing**; FLAG
was written `155, 211, 239` — **128 and 183 were missing**. All are separating values and all of them
count.

⚠⚠ **THE SAME SPAN-FIRST PRECONDITION APPLIES HERE, HARDER.** On ef446, OR's separates-from-**all**
set is literally **empty** — every value that distinguishes OR from the other displaced models is a
NONE value. **`27 / 55 / 83` mean OR only after the span has reached `16,127` and excluded `0,111`.**

⚠ **ef446 CAN ONLY CORROBORATE THE OPERATION READ. IT CAN NEVER CARRY IT ALONE.** It has **no archived
draw anywhere**, so all of its keys score at gate `UNPROVEN` and it has **no ratio-1.00 hard control by
construction** (§4.4). A container that cannot pass an instrument self-test cannot be the sole witness
for a mechanism claim — it can agree with ef227, it can disagree with ef227 (which is the §3.4
**BOTH BRANCHES OBSERVED** row, itself a finding), and it can rescue a session that lost ef227's
surface, but a lone ef446 result is written as *"suggestive, uncontrolled"* and nothing more.

Its three other slots all carry `(0,0)` and are the container's controls: `1ABD01` (two records, 4 bpp,
pool `u[0,127] v[1,127]`) and `3BBDC0` (8 bpp, pool `u[0,111] v[0,111]`). ⚠ **`3BBDC0` IS A CROSS-
CONTAINER COLLIDER** — the same masked key is ef424's `P = 2` slot-1 key (§5.3), and both casts land in
one log. Join on `(effectId, key)` (§5.1) or ef446's control reads ef424's geometry.

⚠ **ef446 appears in NO archived log, so its draw is UNPROVEN** — the very gate ef227 passes in
advance, and the reason it is cast *second* rather than first. All three of its keys therefore score at
gate **UNPROVEN**: an absent row on any of them is uninformative, and a present row that does not
contain its pool span means the mesh drew partially, not that the model is wrong. **Its own no-draw is
itself worth having** — it would close the corpus's last relaunch-free Q2 discriminator and send the
arc to §8.1.

⚠ If ef446 lands, the arc's recorded W6b-SCENERY spill note for this cell was computed on the *raw* u
window and is stated against the wrong window; re-derive it.

### 5.3 ef424 `Odin__Short`, bench row 203 — Q1's clean u arm, and three riders

**3.93 s** (59 sfx ticks). It carries the **complete non-zero 2x2** — `(0,0)`, `(0,0x80)`, `(0x80,0)`,
`(0x80,0x80)` — and **all 13 of its keys drew** in the archived `cast-c` log.

⚠⚠ **EVERY ef424 FIGURE EVER QUOTED FROM THAT ARCHIVE IS A TWO-CAST MERGE, AND THE ROW COUNTS BELOW
ARE THE HALVES.** The `cast-c` log holds **two** ef424 casts back to back — the frame counter goes
*backwards* between them, which is the segmentation — and its ef424 totals are **2,322 MESH rows over
per-cast spans [41..96] and [41..97]**, i.e. **~1,160 MESH per cast, not ~2,300.** Per key, merged →
per cast: `37BC80` 115 → **~57**; `598000` 206 → **~103**; the `P = 2` pair 307 → **~153 each**;
`19BD04` 198 → ~99; `37BCC0` 155 → ~78; `37BD40` 112 → ~56; `37BD80` 57 → ~28. **Frame counts do NOT
halve** (each cast spans the same ~16/27/48 frames; only the rows double). §6.2's health check uses
these numbers, so quoting the merge there is how **a perfectly healthy single cast reads as thin and
invites a false "cut short" call.**

| key | records | A, B | ratio | pool | what it buys (**rows are PER CAST**) |
|---|---|---|---|---|---|
| **`37BC80`** | `0x2ec24` | `0x80, 0` | **1.00 ISOLATED** | u `[0,62]` v `[65,191]` | ★ **Q1's CLEAN u ARM.** Predicts displaced **u `[128,190]`** against raw `[0,62]`. **~57 rows / 16 frames** [41..56]. **The only unpooled `A = 0x80` witness in the session.** |
| `19BD04` | `0x2dbb4` | `0, 0` | **1.00 ISOLATED** | u `[0,127]` v `[65,191]` | EQUALITY control, 4 bpp — **PRE-REGISTERED HARD CONTROL**, absent ⇒ `L6q` (§4.4). ~99 rows / 33 frames |
| `37BCC0` | 4 records | `0, 0` | **1.00 ISOLATED** | u `[0,111]` v `[0,111]` | EQUALITY control, 8 bpp, value-homogeneous — **PRE-REGISTERED HARD CONTROL**. ~78 rows / 26 frames |
| `37BD80` | `0x2d334` | `0x80, 0x80` | 2.00 POOLED | u `[0,63]` v `[65,127]` | the `(0x80,0x80)` family ef227 lacks — containment only. ~28 rows / 12 frames. ⚠ **COLLIDER: this is the same masked key as ef227 §3.3 row 2** (`0xc2254`, `A=0x80 B=0`) — different `(A,B)`, both displacing (§5.1) |
| `37BD40` | `0x2e750` | `0x80, 0` | 4.00 POOLED | u `[0,63]` v `[1,63]` | second u witness — containment only. ~56 rows / 20 frames |
| `598000` | `0x29f88`, `0x2bc94` | `0, 0x80` | 5.52 POOLED | u `[0,63]` v `[65,127]` | ⚠ **COLLIDER with ef227's ANSWER KEY** (§5.1) — and the session's **only P-path** `tp = 2` liveness witness (§4.6). ~103 rows / 27 frames |
| `37BE00` + `3BBDC0` | `0x2f9a4` (**P = 2**) | slot 0 `0x80,0` / slot 1 `0,0` | unproven | — | ★ a free **ORDER_UNMEASURED** probe: one `P = 2` record whose two entries carry **different keys** and **both draw** (**~153 rows / 48 frames each, per cast**). If slot 0's key displaces on u and slot 1's does not, the entry-to-slot pairing order is confirmed on live bytes for the first time. ⚠ **`3BBDC0` COLLIDES with ef446's `(0,0)` control** (§5.2). |

### 5.4 ★ ef038 `Shiva__Full`, bench row 200 — THE FOURTH CAST, the replication this session lacked

**The budget already held it and nobody had spent it.** §5's MP arithmetic says Steiniv has exactly
three casts and the earlier draft spent two — *"one is spare"*, and there it sat. **Rune row 4 is
`Stock Shiva`, and `Actions.csv` gives it `vfx1 = vfx2 = 38`: it is ef038, the U1 container itself,**
at **8 MP** and **24.3 s**.

**WHAT IT BUYS, AND NOTHING ELSE IN THIS DOCUMENT BUYS IT.** Every other control in this session
proves the instrument works **on ef227's own geometry, in ef227's own cast**. The DLL hash (§1 item 3)
is taken **before the launch** and cannot see a runtime regression. So there is no check anywhere that
the s77 instrument still measures what it measured when it produced the arc's foundational result —
**until the log contains a re-measurement of that exact result, taken in the same log, from the same
launch, on the same DLL, minutes apart from the answer.** That is what casting ef038 here is.

**PRE-REGISTERED EXPECTATIONS — the three archived ef038 results, restated as predictions:**

| key | axis | pool | expected | gate |
|---|---|---|---|---|
| **`3ABDC0`** | **u arm** | raw u `[0,127]` | **`128, 255`** — displaced; `NONE` must **not** survive | ⚠ POOLED (20 `so` records, ratio **0.31**) — corroboration only, and §4.7 explains why: this is exactly the arm that is *suggestive, not proven* |
| **`38BE00`** | **v arm** | raw v `[65,127]` | **`193, 255`** — displaced, and **`prims` CONSTANT at 72** | **ratio 1.00 ISOLATED — the airtight one.** A `prims` histogram that is not a single bucket at 72 is itself a failure |
| `3ABD40` | the `(0,0)` control | u `[0,126]` v `[1,127]` | **raw, both axes** — undisplaced | ratio **0.52** — the mesh never draws whole, so **corroboration only, NOT a hard control** (§4.4's roster gives ef038 none, deliberately) |

**HOW IT IS SCORED — it is already mechanical.** `score_uvr.py --selftest` asserts exactly these three
results and **exits non-zero if any fails**. Run against this session's log rather than the archive,
that flag *is* the replication check:

```
py score_uvr.py <the archived session log> --require 227,446,424,38 --selftest
```

⚠⚠ **IF THE REPLICATION FAILS, THE SESSION IS VOID — not "one weaker rider".** ef038's arms are the
measurement everything downstream of U1 rests on. If they do not reproduce **in the same log** as the
answer, then whatever ef227 said was said by an instrument that is demonstrably not the one that
produced the 0.97 read, and **no ef227, ef446 or ef424 number in that log may be published.** It is
§8 `L9-REPLICATION-FAILED`, it outranks every result rung, and it is unmissable by design.

**TWO FREE SIDE-EFFECTS.** (1) It **defuses the decoy hazard**: `Stock Shiva` sits at Rune row 4, two
rows above the wanted `Stock Atomos` at row 6, and a mis-pick used to fill the log with ef038 rows that
the ladder diagnosed as *"you are scoring the old U1 file"* — **two causes, one output.** Making row 4
an *intended* pick collapses that ambiguity. (2) It costs **~30 s and one encounter.**

⚠ **IT REQUIRES ONE PIECE OF PROSE TO BE RIGHT.** The wrong-log rung must key on **"227 is ABSENT"**,
never on **"38 is PRESENT"** — because ef038 is now deliberately present. The scorer's rule already
does this correctly (`L0b-WRONGLOG` fires when *not one REQUIRED cast* appears); it was only the
document's prose that was wrong, and §8 `L0b` now says so.

---

## 6. THE LOG — where it lands, what gates it, what healthy looks like

### 6.1 Location and gating

The probe writes to **`<game>\sfxmeshprobe.log`** (game root, beside `Memoria.log`). The UVR row is
emitted inside the MESH loop and gated on **`CapturePrims = 1` AND the mesh key's texture bit**. Row
shape:

```
UVR,effectId,frame,index,keyHex,src,prims,uMin,uMax,vMin,vMax,tpage,clut
```

`src`: `P` = polygon (primitive-carried tpage — the path this cast wants), `S` = SPRT (current page),
`M` = both folded into one accumulator. `prims` = contributing primitive count; `prims = 1` with
`uMin == uMax` is a point sample and is not evidence of a span.

**`src` is structurally predictable for the answer key.** The SPRT path always ORs `FILTER_BILINEAR`
into its key; the answer key's archived raw form is `00598000`, which carries no bit above `0x7FFFFF`,
so it cannot come from the SPRT path. Corroborated across the whole s77 log: of 8,587 UVR rows, every
row whose raw key has no high bits is `src = P` (2,910 of 2,910), and every `S` row carries
`FILTER_BILINEAR`. **Expect `src = P` on the answer row; anything else is §8 `L4-SPRT-CONTAMINATION`.**
⚠ **The scored aggregate is filtered to `src = P` AND `prims > 1` UNCONDITIONALLY**, not only when
contamination is noticed — three stray `src = S` rows once destroyed a cleanly five-way-separating
result while the run still reported itself scored. The discarded rows are reported with counts, per-`src`
breakdown and **line numbers**, and a group whose every row is discarded returns `NO-SCORABLE-ROWS`
rather than a span.

⚠ **The key's own depth field is at bits 5–6 of the tpage word, not 7–8.** The SFX key packs
`tx(0-3) ty(4) tp(5-6) abr(7-8)` — which is why the engine's own 15 bpp test is `num >> 5 == 2`. The
U1 parser's `decode_key()` reads the PSX packing instead and therefore **swaps the `abr` and `tp`
labels**. Anything that filters or reports on depth must use the key packing, or every 15 bpp row will
be filed under the wrong depth. (This is the second reason §9.2 does not reuse that parser.)

### 6.2 Row budget — what a healthy log looks like

Calibrated from the archives, not guessed. One ef038 cast (342 frames) produced 9,449 MESH / 8,587 UVR
/ 415,426 PRIM rows in ~25 MB.

| | expect | derivation |
|---|---|---|
| ef227 cast length | ~504 frames, **36.5 s**, uninterruptible | archived cast spanned frames 11–515; 547 sfx ticks |
| ef227 MESH rows | ~15,000 | archived ef227 cast: 15,031 |
| ef227 UVR rows | **~13,500** | 15,031 − 1,516 untextured (key `000000`) |
| **★ UVR rows on `(227, 598000)`** | **~292, over ~73 frames, in the last ~15% of the cast** | the archived draw |
| **★ UVR rows on the 15 bpp cohort** | **~212 each on `(227, 408000)` and `(227, 428000)`**, frames ~167–432 | the archived draw (§4.6) |
| **ef424 cast — PER CAST, NOT THE MERGE** | **~56 frames, ~1,160 MESH, ~1,160 UVR**, 13 keys | archived `cast-c` **holds TWO ef424 casts**: 2,322 MESH over spans [41..96] and [41..97] (§5.3). ⚠ Every ef424 row count in that archive halves; **the frame counts do not.** Not one archived ef424 MESH row is untextured, so MESH and UVR come out equal |
| ef446 cast | **11.0 s** (165 sfx ticks; 12.67 s with the cast wrapper) — **row counts UNKNOWN, no archive exists** | duration from `rung8-epic/census/summon_durations.csv`; §5.2 for why the rows cannot be pre-computed |
| ef038 cast (§5.4) | **24.3 s** (364 sfx ticks), ~9,450 MESH / **~8,590 UVR** | the archived s77 ef038 cast, exactly |
| PRIM+STATE rows | see the PrimCap table below | measured per effect, not scaled |
| file size | **~55–75 MB** for the four-cast session | ~25 MB per ef038-sized cast |

**A log under ~10 MB, or with fewer than ~1,000 UVR rows for effect 227, is not a healthy ef227 cast.**
**But do not apply the merged ef424 numbers as a health check** — a healthy single ef424 cast at
~1,160 MESH rows would read as half-dead against them and invite a false "cut short" call (§5.3).

★ **PrimCap — MEASURED HEADROOM, and this is the FIRST session in which it can matter.**
`SfxMeshProbe.cs:787-791` caps per-primitive rows for the **PROCESS LIFETIME**, not per cast, with a
static warned-flag that never resets; the live `Memoria.ini [SfxProbe] PrimCap = 3000000`. One
archived log (`w6b-cast-ladder`) already sits at **exactly 3,000,000 with a truncation marker**, so
this is not hypothetical. The repair turned a one-cast session into a four-cast one, which is
**the first time PrimCap and the UV instrument can meet.** Use these; stop estimating:

| effect | PRIM+STATE rows, **measured, per cast** | source |
|---|---|---|
| ef227 | **600,413** | `pre-odin-cast` archive |
| ef038 | **445,803** | the s77 ef038 archive |
| ef446 | **~181,000** — the only estimate here, scaled by duration (165 / 547 sfx ticks) | no archive exists |
| ef424 | **~38,900** | `cast-c`, 77,800 over two casts |
| *(for scale)* ef211 | 948,917 | `pre-odin-cast` — one effect, a third of the whole cap |

**Four casts ≈ 1.27 M of 3 M — safe, with better than half the cap unspent.** ⚠ **But that margin is
spent by ONE re-cast of ef227**, which is exactly what §8 `L3a-CUT-SHORT` tells the owner to do. If
the session ends up with two ef227 casts plus the other three, it is still inside the cap — barely —
and a third would not be.

The s77 patch places the UV accumulation *before* both the `PrimSummary` early-return and the
`PrimCap` drop specifically so that UVR does not degrade when PRIM does. **That ordering is asserted
by the patch and has never been exercised** — no archived log with UVR rows ever reached the cap — and
**a truncated UVR read scored as complete is the danger it guards.** So the marker is now a scored
step, not a note: the scorer reads `# PRIM CAPTURE TRUNCATED` out of the comment stream, counts
PRIM+STATE rows per effect against `--primcap`, warns at 80% of the cap, and **refuses** on the marker
(§8 `L8-PRIMCAP-TRUNCATED`, §9.2 step 2).

### 6.3 ⚠ THE LOG TRUNCATES AT EVERY LAUNCH

Confirmed: both archived s77 logs contain **exactly one** probe header block. The file is rewritten,
not appended, when the game starts. **A relaunch destroys the previous session's log** — but *battles*
do not: the file accumulates across encounters within one launch, which is what makes the
one-encounter-per-cast rule (§5) free. Archive before launching again — the arc has already lost a
delta this way once and only recovered it by chance.

---

## 7. OWNER STEPS

**Nothing is deployed. No file of yours is modified. No relaunch is needed beyond starting the game,
and there is nothing to revert afterwards.** This is a read-only measurement: launch, cast four
abilities, quit.

**Time: budget 20–25 minutes, not 10.** The casts themselves are ~76 seconds of animation. Everything
else is the route in.

**Launching is SAFE — the log standing in the install right now is already saved.** Starting the game
wipes `<game>\sfxmeshprobe.log`, but a byte-identical copy is already archived at
`capture-logs\sfxmeshprobe.LIVE-preserved-2026-07-31T2106.log` (verified sha256, §1 item 9). Nothing
is lost by launching. ⚠ **That sentence expires if anyone launches the game before you do** — §1 item 9
says to re-hash the two files immediately before step 1, and it takes ten seconds.

### 7.0 Before you start — one reassurance, one hazard, and three things that will look like faults

**A. The three irreversible boosters are OFF and cannot be turned on by accident.** `MasterSkill`,
`LvMax` and `GilMax` are all `0` in `Memoria.ini`. Nothing you can press here permanently changes a
save.

**B. But `F1`–`F4` ARE live, and they are bare function keys, not menu items.**

| key | booster | why it matters here |
|---|---|---|
| **F1** | speed x3 | would compress the animation this cast measures |
| **F2** | battle assistance (the menu calls it `ATB full`) | not harmful, not wanted |
| **F3** | **all attacks inflict 9999** | ⚠ **would end most fights on the first hit — before you get to cast** |
| **F4** | no random encounters | ⚠ **would make step 7 — "walk until a battle starts" — never end** |
| **`J`** *(or the pad's right trigger)* | **auto-battle** — not a booster, and **the `Cheats` tab cannot show it** | ⚠ **the party fights by itself and the ability list never opens — every cast becomes a plain Attack.** It persists between battles. If a fight starts running itself, press `J` once. |

**Do not press F1–F4 at any point.** The debug menu (`~`) is safe; the bare function keys are the
hazard. ⚠ **And the toggles' STATE is not stored in any file — it lives in game state, so any of them
can already be ON from an earlier session on this shared install.** That is why step 5 exists.

### 7.0a ★★ THE ABILITY WINDOW SHOWS **FIVE** ROWS AND SCROLLS — NEVER TAKE "THE BOTTOM ROW"

**This is the single most likely way to cast the wrong thing, and this document's own earlier wording
pointed straight at it.**

Live `Memoria.ini` `[Interface] BattleRowCount = 5`, `BattleColumnCount = 1`. `BattleHUD` builds the
ability panel with `ChangeDims(1, 5, …)` and `GOSubPanel` sets its scroll view's
`VisibleItem = colCount * rowCount` = **5**. So **any list longer than five rows shows rows 1–5 and
you scroll for the rest.**

| command | rows | what you see on the FIRST page | what needs scrolling |
|---|---|---|---|
| **Spark** (Iviv) | **7** | 1 `Blizzard` · 2 `Cure` · 3 `Voltflare` · 4 `Soul Leech` · **5 `Bahamut Cinema`** | 6 `Nimbra` · **7 `Stock Bahamut` ← THE ANSWER** |
| **Rune** (Steiniv) | **8** | 1 `Iron Edge` · 2 `Stock Phoenix` · 3 `Stock Madeen` · **4 `Stock Shiva`** · 5 `Stock Octopus` | **6 `Stock Atomos`** · **7 `Stock Odin Short`** · 8 `Stock Magic Hammer` |

⚠⚠ **ON SPARK, THE ROW THAT *LOOKS* LIKE THE BOTTOM ONE IS THE DECOY.** With five rows visible, the
visually bottom row of the first page is row 5 — **`Bahamut Cinema`**, same creature, wrong effect.
Earlier drafts said *"the LAST row of the list"*, *"row 7 — the bottom one"*, *"Take the last row"*.
**The ordinals were right and the word "bottom" was wrong**: a cold reader who does not scroll takes
row 5 and casts the decoy. **Count from the top of the FULL list and scroll to reach the row.**

⚠ **ON RUNE, TWO OF THE THREE WANTED ROWS ARE OFF-SCREEN.** `Stock Atomos` (row 6, cast 2) and
`Stock Odin Short` (row 7, cast 3) are both below the fold; only `Stock Shiva` (row 4, cast 4) is on
the first page. The eight-row list printed at step 11 is the FULL list, not what is on screen.

### 7.0b ★ THE ONE-GLANCE MIS-PICK TELL — the MP cost, and the creature

**Every ability row draws its MP cost beside the name** (`BattleHUD.DisplayAbilityDetail`). On **Spark**
that alone separates the answer from the decoy:

| Spark row | MP |
|---|---|
| 1 `Blizzard` / 2 `Cure` — the two stock spells | **6** each |
| 3 `Voltflare` / 4 `Soul Leech` | 18 / 12 |
| **5 `Bahamut Cinema` — THE DECOY** | **56** |
| 6 `Nimbra` | 24 |
| **7 `Stock Bahamut` — THE ANSWER** | **8** |

**The answer is the ONLY 8 MP row on Spark; the decoy is the ONLY 56 MP row.** Read the number, not
just the name. **And there is a free check afterwards: Iviv starts on 80 MP. Right pick ⇒ 72 left.
Decoy ⇒ 24 left.**

⚠ **On Rune the MP tell does NOT work** — every `Stock …` row costs 8. Use the creature instead:

| cast | row | **the creature you should see** |
|---|---|---|
| 1 | Spark 7 `Stock Bahamut` | **BAHAMUT** |
| 2 | Rune 6 `Stock Atomos` | **ATOMOS** |
| 3 | Rune 7 `Stock Odin Short` | **ODIN** |
| 4 | Rune 4 `Stock Shiva` | **SHIVA** |

Four visually distinct creatures. **If the creature on screen is not the one named for that cast, you
picked the wrong row — write it down and say so in §7.3.** Until now the owner had no in-the-moment
confirmation for casts 2, 3 or 4 at all.

### 7.0c ★ THREE THINGS ABOUT THIS INSTALL THAT WILL LOOK LIKE FAULTS AND ARE NOT

**1. THERE IS NO MUSIC. AT ALL.** Live `Memoria.ini` `[Audio] MusicVolume = 0` (SoundVolume `10`,
MovieVolume `15`). **No intro BGM, no field BGM, no battle BGM** — the whole session is scored silent.
Sound effects and the opening FMV's own audio still play. **Silence is the configured state of this
install, not a broken launch.**

**2. BATTLES RUN IN SIMULTANEOUS MODE, SO THE FIGHT DOES NOT WAIT FOR YOU.** `[Battle] Speed = 5`.
**The enemy keeps acting while you read the ability list** — take your time reading the names, but know
that a battle really can end while you are choosing, or part-way through an animation. If that happens
it is not a disaster; it is §7.3 question 6, and the cast is simply repeated in the next encounter.

**3. THE SUMMON PLAYS WITHOUT ITS CINEMATIC CAMERA.** At `Speed >= 3` — **in an ordinary battle phase,
which is every battle in this protocol** — the sequencer skips `PlayCamera` (`UnifiedBattleSequencer.cs:828`,
gated on `Speed >= 3` **and** `btl_phase == PHASE_NORMAL`), so the creature performs on the ordinary battle camera.
**It will look flatter and less framed than every archived cast video of the same summon.** That is
configuration, not a fault, **and it cannot affect this measurement**: the s77 UVR row reads the
primitive struct's own u,v bytes out of the display list, and the camera never touches them.

⚠ **Do NOT "fix" any of the three by editing `Memoria.ini`.** All of them are read at launch, so a
change costs a relaunch — and a relaunch wipes the log (§6.3). **This session has exactly one launch.**

### 7.1 The steps, in order

1. **Start the game.** (`FF9.exe` was not running when this was written, so expect a normal launch.)

2. ★ **NEW GAME. Not Continue.** The two bench characters are a `[[playable]]` **party-init** recruit —
   a save made before the bench was deployed has no Iviv and no Steiniv, so **no "Spark" and no "Rune"
   command exists to cast from.** Picking Continue lands you at the right field with no way to cast and
   produces a log that reads exactly like "the cast never fired" (§8 `H-SAVE-LOADED`).

   ⚠ **THE ROUTE IN IS LONGER THAN AN EARLIER DRAFT SAID — AND IT IS SILENT.** Expect, in order:
   **the opening FMV** (the field-70 override preserves it deliberately and **the FMV skip has NOT been
   applied**; `SkipIntros = 3` skips only the splash/logo), **a fade to black**, **a character rename
   screen** (`Memoria.ini [Hacks] DisableNameChoice = 0`, so the rename windows appear — just accept
   the default with Confirm), and then **`Field(6000)`, a verbatim fork that opens on its own scripted
   scene.** Several minutes can pass before you hold the controller. **This is all expected. None of it
   is a failure.**
   ⚠ **DO NOT EXPECT MUSIC — there is none, anywhere in this session** (`MusicVolume = 0`, §7.0c).
   An earlier draft promised "the intro BGM", which is exactly the kind of promise that makes a
   correct launch feel broken.

3. **WAIT UNTIL YOU HAVE CONTROL** — you can walk the character around — **and only then press `~`.**

   > ⚠⚠ ★★ **AND THEN WARP STRAIGHT AWAY. DO NOT EXPLORE, DO NOT READ ANYTHING FIRST, DO NOT WANDER —
   > GO TO STEP 4 AND WARP. THE CLOCK IS RUNNING AND IT CAN SILENTLY COST YOU THE SESSION.**
   > You arrive on field 6000, whose opening scene is **still running** while you stand there, and part
   > of what it does is **fill the party to its full four members** (Zidane, then Cinna, Marcus and
   > Blank). The bench room's recruit adds Iviv and Steiniv **into empty party slots** — and when there
   > are none left it **fails silently**: no message, no error, nothing on screen. You would simply
   > reach the first battle and find **no `Spark` and no `Rune` to cast with**, and the log would be
   > indistinguishable from "the cast never fired" (§8 `H-PARTY-FULL`).
   > **You gain control BEFORE that scene finishes, which is why warping immediately works.** This is
   > not fatal if it happens — step 6 catches it and the fix takes 20 seconds — but avoiding it is free.
   > *(The booster check that used to sit here has moved to step 5, after you arrive. That tab works
   > anywhere; the warp is the part that is time-sensitive.)*

4. **`~` → `Go` tab → get to field `30301`. DO THIS FIRST, BEFORE ANYTHING ELSE IN THE MENU.**
   ⚠ **The `Go` tab has TWO buttons labelled `Go`** — one under **`Warp to field`** and one under
   **`Teleport on this field`**. **You want the first one.**

   ★ **PREFERRED, AND IT REMOVES THIS WHOLE STEP'S HAZARD: CLICK THE FAVOURITE.** The `Go` tab draws a
   **`Favorites`** chip grid **above** the warp box, and **`30301` is already pinned on this machine**
   (the pin list lives in the game's own settings store and survives relaunches). **Click the chip whose
   label starts `30301`.** Nothing to type, nothing to mis-type.
   ⚠ **It is one of TEN pins laid out three to a row, so look for it — it is the ninth chip, on the
   third row, labelled `30301  TEST30301`.** ⚠⚠ **AND EACH CHIP HAS A NARROW UNLABELLED `x` BUTTON
   IMMEDIATELY TO ITS RIGHT THAT DELETES THE PIN ON THE SPOT, WITH NO CONFIRMATION.** Click the chip
   itself, not the `x`. (A mis-click there is not dangerous to the game or the save — it just
   permanently unpins `30301` for every future session, so mention it in §7.3 if it happens.)
   *(The pin list is shared machine state, so another session could have unpinned it already. If the
   chip is not there, use the box — and read the next paragraph first.)*

   ⚠⚠ **IF YOU USE THE BOX, CLEAR IT FIRST. IT IS NOT EMPTY.** The warp box is **pre-filled with
   `5000`** (`Ff9mkDebugMenu.cs:70`, `_warpText = "5000"`), it takes up to **six** characters, and
   **clicking it does NOT select the existing text** — the caret simply lands where you clicked and
   your digits are *inserted*. **Typing `30301` into a box already reading `5000` gives you `500030`.**
   **Delete every character. Confirm the box reads exactly `30301`. Then click `Go`.**

   ⚠⚠ **AND THE FADE IS NOT THE SUCCESS SIGNAL — IT FIRES FOR THE WRONG ID TOO.** `500030` parses as a
   perfectly good number (`Int32.TryParse` succeeds), and the warp path **never checks that the id is
   registered**: it locks control, starts the fade and defers the map change (`:1956-1977`). So a wrong
   id produces **exactly** the menu-closes-and-fades-to-black that a correct one does, and then lands
   you on an id that does not exist and is past the Int16 ceiling anyway.

   > ★ **SUCCESS = A ROOM YOU CAN SEE AND WALK AROUND IN.** Not the fade. Field 30301 is the bench
   > room; on arrival its `Main_Init` recruits Iviv and Steiniv. **If the fade does not resolve into a
   > room you can move the character in, you warped nowhere** — quit and redo from step 1.
   > *(Relaunching here is free: nothing has been cast yet, so the log holds nothing worth keeping.
   > That stops being true the moment cast 1 lands — from step 9 on, a relaunch destroys the session's
   > data, §6.3.)*

   ⚠ **IF `Go` APPEARS TO DO NOTHING, there are THREE causes — and the one that speaks is not the one
   an earlier draft named as "the only cause".**

   | what happened | does it say anything? | what to do |
   |---|---|---|
   | **you are not in the field HUD** — still in the opening, in a battle, or in a cutscene | **SILENT.** `Warp` returns early and the caller at `:1949-1954` throws the result away without setting a status | close the menu, wait until you can walk, try again |
   | **the box does not hold a number.** Most often a stray **`` ` ``** typed into it: with a text box focused the tilde key **types a character** instead of closing the menu (`UIKeyTrigger.cs:163-165` — deliberate, so typing `` ` `` cannot slam the menu shut) | **SILENT.** `Int32.TryParse` fails and `Warp` is never called at all | clear the box, retype `30301`, `Go` |
   | **the warp itself threw** | **YES — a status line appears** (`:1979-1982` sets one) | read it, and report the text in §7.3 |

   ⚠ **A FOURTH NO-OP HAPPENS EARLIER STILL: during the opening the debug menu will not open.** The
   `~` toggle is gated on being in the field, battle or world HUD (`UIKeyTrigger.cs:166-174`), so
   pressing `~` during the FMV, the rename screen or the scripted opening scene does **nothing at all**.
   That is what step 3 is for.

5. **NOW, in the bench room, `~` → `Cheats` tab. Read the four booster rows** — `Speed`, `ATB full`,
   `Attack 9999`, `No encounters`. Each is drawn as `[x] label` (on) or `[  ] label` (off), and
   clicking one flips it. **`No encounters` MUST read `[  ]`, or step 7 never ends.** Flip `Speed` and
   `Attack 9999` off too if either shows `[x]`.
   *(While you are here: `Full heal party` on this tab restores HP and MP and writes nothing. That —
   not the save point — is the fix if a character runs out of MP. Use it on the field, between
   battles, not mid-combat.)*
   ⚠ **THERE IS A FIFTH TOGGLE AND THIS TAB CANNOT SHOW IT: AUTO-BATTLE, bound to `J` (or the right
   trigger on a pad).** With it on, the party attacks by itself and **the ability list never opens** —
   every one of your four casts silently becomes a plain Attack. It persists between battles on this
   shared install. **If the first battle starts fighting itself without you, press `J` once.**

6. ★★ **OPEN THE FIELD MENU AND COUNT THE PARTY — 15 seconds, and it is the check that saves the
   session.** You are looking for **Iviv** and **Steiniv** in the roster.

   > **If they are BOTH there — good, go to step 7.**
   > **If either is MISSING, do not quit and do not start a New Game** — that returns you to the same
   > opening scene, the same party rebuild and the same failure. **Read who IS in the party and write
   > it down** (§7.3 q1b), then fix it right here:
   > ★ **FIELD MENU → `Party` → seat Iviv and Steiniv directly.** This install lists every defined
   > character in that submenu regardless of story state, so they are selectable even though the
   > automatic recruit did not fire. Their abilities and MP are correct once seated.
   > *(What happened: the room adds them into empty party slots, and the opening scene had already
   > filled all four. It fails silently by design — §8 `H-PARTY-FULL`. A three-member party gives the
   > half-case: `Spark` present, `Rune` missing.)*
   > ⚠ **`Full heal party` cannot reach a character who is not seated**, so do this before step 7.

7. **Walk until a random battle starts.** ⚠ **Note where you are when it happens** — §7.3 asks, and it
   is the one question that catches a mis-warp after the fact.

8. ⚠ **CHECK THE MENU NOW, in this first battle, before you cast anything.** Confirm **Iviv has
   `Spark`** and **Steiniv has `Rune`** — **look for BOTH, and remember the answer either way**, because
   §7.3 question 1 asks whether both were present and no other evidence in the log can tell the reader.
   **If either command is missing, flee the battle and go back to step 6** — it is the party, and it is
   fixable in the field menu without losing anything. **Only if the Party submenu will not seat them
   either** have you loaded a save: quit, **New Game**, redo from step 2.
   *(This step used to sit before the step that starts the battle, where the menu cannot be seen — and
   it used to prescribe New Game for both causes, which is a loop for the commoner one.)*

9. **CAST 1 — THE ANSWER. Iviv → `Spark` → `Stock Bahamut`, ROW 7 OF 7. ⚠ YOU MUST SCROLL TO SEE IT.**

   > ⚠⚠ **THE WINDOW SHOWS FIVE ROWS AND SPARK HAS SEVEN (§7.0a). `Stock Bahamut` IS NOT ON THE FIRST
   > PAGE. SCROLL DOWN TWO ROWS.**
   > ⚠⚠ **DO NOT TAKE THE ROW THAT LOOKS LIKE THE BOTTOM ONE.** On the first page that is row 5,
   > **`Bahamut Cinema`** — the decoy: same creature, wrong effect. That is the mistake this whole
   > paragraph exists to stop.
   > ★ **THE ONE-GLANCE TELL: `Stock Bahamut` costs `8 MP`. `Bahamut Cinema` costs `56 MP`.** The MP
   > cost is drawn beside every name; the answer is the **only 8 MP row** on Spark and the decoy is the
   > **only 56 MP row**. **Read the number as well as the name before you confirm.**
   > ★ **FREE CHECK AFTERWARDS: Iviv had 80 MP. Right pick ⇒ he reads 72. Decoy ⇒ he reads 24.**
   > ★ **The creature on screen should be BAHAMUT** — flat-lit and un-framed, because the cinematic
   > camera is skipped on this install (§7.0c). That is normal.

   **Let the whole animation finish — 36.5 seconds.** ⚠ **The fight does NOT pause while you choose,
   and it does not pause during the animation** (§7.0c) — if the battle ends part-way through, that is
   §7.3 question 6, and the cast is simply repeated in a later encounter.
   **LANDMARK: the measured window is the LAST ~7 seconds and it straddles the damage numbers.** It
   opens ~3.5 s *before* the damage figures pop (they land at tick 486 of 547) and closes ~1.3 s
   after. **If you saw the damage numbers land and the battle hand control back on its own, the whole
   window was captured.** Do not skip, do not quit, do not press `F1`.
   *(There is no need to cast it "first and alone" — §5. Other effects in the same battle cannot
   corrupt this measurement.)*

10. **Finish or flee the battle**, then walk into a **second** encounter.

11. **CAST 2 — THE RESCUE. Steiniv → `Rune` → `Stock Atomos`, ROW 6 OF 8. ⚠ YOU MUST SCROLL TO SEE IT.**

    > ⚠⚠ **THE WINDOW SHOWS FIVE ROWS AND RUNE HAS EIGHT (§7.0a). `Stock Atomos` IS NOT ON THE FIRST
    > PAGE.** The list below is the **FULL** list, not what is on screen — the first page ends at
    > row 5, `Stock Octopus`.
    > ⚠ **`Rune` IS A FIELD OF DECOYS. Eight rows, SEVEN of them beginning with the word "Stock":**
    > 1 `Iron Edge` · 2 `Stock Phoenix` · 3 `Stock Madeen` · **4 `Stock Shiva`** · 5 `Stock Octopus`
    > *— first page ends here —* · **6 `Stock Atomos`** · **7 `Stock Odin Short`** ·
    > 8 `Stock Magic Hammer`.
    > **The three you want are rows 4, 6 and 7. Rows 6 and 7 are adjacent, with a decoy immediately
    > above them and another immediately below.**
    > **Read the full name every time — MP cannot help you here: every `Stock …` row costs 8.**
    > ★ **THE TELL IS THE CREATURE: this cast must show ATOMOS.** If a different creature appears, you
    > picked the wrong row; note it and say so in §7.3.
    > A mis-pick of `Stock Octopus` or `Stock Magic Hammer` wastes 8 MP you do not have spare; a
    > mis-pick of `Stock Shiva` fills the log with ef038 rows — which is *also* what a genuinely wrong
    > log looks like (§8 `L0b-WRONGLOG`). Casting Shiva is step 13's job; casting it *here* costs the
    > session cast 4.

    **11.0 seconds.** Let it finish.

12. **Finish or flee**, walk into a **third** encounter.
    **CAST 3 — THE u ARM. Steiniv → `Rune` → `Stock Odin Short`, ROW 7 OF 8 — directly below Atomos,
    and ⚠ ALSO BELOW THE FOLD. Scroll.**
    ★ **The creature must be ODIN.** **3.9 seconds** — it is over almost immediately. Let it finish.

13. **Finish or flee**, walk into a **fourth** encounter.
    **CAST 4 — THE REPLICATION. Steiniv → `Rune` → `Stock Shiva`, ROW 4 OF 8 — the one wanted row that
    IS on the first page.** ★ **The creature must be SHIVA.** **24.3 seconds.** Let it finish.

    > ★★ **DO NOT SKIP THIS ONE, EVEN IF YOU ARE OUT OF TIME. IT IS NOT A BONUS.**
    > It re-measures the arc's foundational result **inside this same log, from this same launch, on
    > this same engine build** (§5.4) — and that is the session's **only** check that the instrument
    > still measures what it measured when it produced that result. The engine hash in §1 was taken
    > *before* the launch and cannot see a runtime regression.
    > **BOTH DIRECTIONS, stated plainly:**
    > **If you cast it and it disagrees with the archived result, the ENTIRE SESSION IS VOID** — casts
    > 1, 2 and 3 are all discarded however clean they look (§8 `L9-REPLICATION-FAILED`). That is a
    > painful outcome and it is exactly the outcome worth having, because the alternative is publishing
    > it.
    > **If you SKIP it, nothing is void — but nothing is defended either.** Casts 1–3 would then be
    > published with no evidence at all that the instrument was healthy during the session that
    > produced them. **Three casts and no replication is a weaker session than three casts and a
    > replication; it is not "the same session, minus a nice-to-have".**
    > *(It is also the reason row 4 is an **intended** pick rather than a hazard — see step 11.)*

    ⚠ **Steiniv's 24 MP is now exactly spent.** If he is out of MP before this, go back to step 5 and
    use `Full heal party`.

14. **Quit the game** — any normal quit is fine, including closing the window. **The probe log is
    flushed on every write, so an abrupt close loses nothing.**

15. **Archive the log. THE FILENAME MATTERS.** Copy

    `<game>\sfxmeshprobe.log`  →  `C:\gd\SCRATCH\summon-format\repaint-w6b\capture-logs\`

    **and name it `sfxmeshprobe.u2-generalisation-cast.2026-08-01.log`** (use the real date). That
    directory already holds **nine** tagged logs; an untagged copy is what the next session silently
    overwrites. Do this **before launching anything again** — the file is wiped at every launch (§6.3),
    though it is **not** wiped between battles, which is why all four casts are in the one file.

### 7.2 What is normal, and what actually means STOP

**NORMAL — do not stop for any of these:** the intro FMV; **complete silence — there is no music
anywhere in this session** (§7.0c); a **character rename screen** (accept the default); **the summon
playing on the ordinary battle camera instead of its cinematic one** (§7.0c); **the enemy acting while
you are still reading the ability list** (§7.0c); the battle result screen; the debug menu's own status
line; a booster icon on the HUD if one was already on (turn it off, step 5).

**STOP only for a prompt that mentions DEPLOYING, REVERTING, PATCHING or OVERWRITING MOD FILES.** This
protocol issues none, so one would mean another session is running against the same install.

⚠ **"Nothing is written" is very nearly, but not exactly, true.** If you use the bench's **save point**
you write a real save slot on a shared install, and the game will then ask you to confirm overwriting
a slot — **which would false-fire the stop rule above, and it is not this protocol's prompt.** So:
**do not use the save point.** `~ → Cheats → Full heal party` does the same job and writes nothing.

### 7.3 ★ REPORT BACK — NINE questions, and every one of them is a rung the log cannot decide alone

**This list is derived FROM the ladder, question by question. Each row names the rung that hangs on
it.** ⚠ **The five-question version did not ask the two things the ladder needs most** — whether both
commands were *present* (`H-SAVE-LOADED` turns on exactly that, and the old list only asked which row
was picked), and **where the battles happened** (which, given the warp box's pre-filled `5000`, is the
one answer that catches a mis-warp after the fact).

**Answer all nine, even where the answer is "yes, all fine".**

| # | question | why — the rung it decides |
|---|---|---|
| **1** | ★ **Were BOTH commands present in the battle menu — `Spark` on Iviv AND `Rune` on Steiniv?** (step 8) Answer for each: Spark ______ Rune ______ | **`H-SAVE-LOADED`.** A pre-deploy save has neither character. If a cast is missing from the log, this is the ONLY thing that separates "a save was loaded" from "the cast failed" — and **nothing in the log can tell them apart.** |
| **1b** | ★★ **WHO WAS IN THE PARTY?** List all of them. | **`H-SAVE-LOADED` vs `H-PARTY-FULL` — and this ONE answer separates them.** Both look identical from the log: a command is missing and the cast never fired. **A full four of Zidane / Cinna / Marcus / Blank means the party was already full and the recruit silently no-opped** (fixable in the field menu, §7 step 6). **An empty or short roster with no bench characters means a save was loaded** (only that one needs a New Game). Without this answer the reader cannot tell, and the wrong recovery is an infinite loop. |
| **2** | **Which menu row did you pick for each cast, by full name?** cast 1 ______ · cast 2 ______ · cast 3 ______ · cast 4 ______ | **`L2-NEVER-FIRED`**, and the decoys. Also say **which creature actually appeared** if it was not the one §7.0b names — that is a mis-pick you saw happen. |
| **3** | ★ **What did the `Go` box read when you clicked it — or did you use the `30301` favourite chip?** | **THE MIS-WARP CATCH.** The box is pre-filled `5000` and does not select-all, so `500030` is one careless click away, and it fades to black exactly like a correct warp (step 5). If the answer is anything but `30301` or "the chip", the whole session was cast somewhere else. |
| **4** | ★ **Where did the battles happen — the bench room you warped to, or somewhere else?** Same room for all four? | **`H-NO-BATTLE`** and the mis-warp catch again, from the other side. |
| **5** | **Did all four casts happen?** If not, which ran? | **`L2-NEVER-FIRED` / `L3c-ANSWER-MISSING`**, and the §5 degradation table — which forfeits what. |
| **6** | **Did each animation run to the end, or did any battle end mid-animation?** Which one? | **`L3a-CUT-SHORT`.** ⚠ Battles run in Simultaneous mode here (§7.0c), so this is a *real* possibility, not a formality. |
| **7** | **Was any row cast more than once** (a retry, a mis-pick, a repeat)? | **`L7-MULTICAST`** — it tells a deliberate repeat from a segmentation artefact, and it triggers the PrimCap budget re-check (§6.2). |
| **8** | ★ **Did you use the save point at any time?** And: **was any of `Speed` / `Attack 9999` / `No encounters` showing `[x]` when you checked in step 5?** | The save point is **forbidden** by §7.2 — it writes a real slot on a shared install and its overwrite prompt false-fires the STOP rule. The boosters change what the log contains (`F3` ends fights early, `F1` compresses the animation). **And: did any battle start fighting by itself?** That is auto-battle (`J`), which the `Cheats` tab cannot display — with it on, the ability list never opens and every cast becomes a plain Attack. |

⚠ **A "no" is an answer.** "I did not use the save point", "no battle ended early", "both commands were
there" are all load-bearing; a blank is not.

---

## 8. THE FAILURE LADDER

**Do not skip a rung** — the rung ids are what separate a defect from a result, and every null below is
distinguishable from every other null by evidence in the log or by one question to the owner.
⚠ **The tables below are a LOOKUP, not the running order.** Severity order is the machine list a few
lines down (and `RUNG_ORDER` in the scorer); the order the checks are actually *run* in is §9.2's
numbered scoring order. Use the tables to look an id up, not to decide what outranks what.

★ **TWO KINDS OF RUNG, AND THE PREFIX TELLS YOU WHICH — READ THIS BEFORE THE TABLE.**

> **`L…` and `R…` rungs are MACHINE-FIRED.** `score_uvr.py` fires them by these exact ids out of its
> own `RUNG_ORDER`, ranks them by severity, and summarises every run on one line —
> `LADDER: <n> rung(s) fired.  TOP: <id> [<verdict>]`. If you see one of these in the output, you can
> look it up here and the id will match character for character. **That `LADDER:` line is the LAST
> line of every run, in both modes.** *(Under `--selftest` a `SELFTEST` block prints too — **above**
> the ladder line, never below it, precisely so the loudest failure in the session cannot print
> beneath the line the reader is told to keep. A failed replication also sets a non-zero exit
> code — §9.2.)*
>
> **`H-…` rungs are HUMAN-JUDGED. No scorer fires them and no output line will ever carry one.** They
> are the calls only the reader or the owner can make — "was a save loaded", "did a battle happen at
> all", "is that drift or is that displacement", "did a pre-cast gate refuse". They are legitimate
> rungs and they are in the ladder because the diagnosis needs them; they carry a different prefix
> **so a reader can never look up a machine id and land on a judgement row, or hunt the output for an
> id nothing prints.**
>
> ⚠ **THIS PARAGRAPH IS A REPAIR, NOT DECORATION.** The pre-round-4 draft claimed *"the rung names
> below are the scorer's own — `score_uvr.py` fires them by these exact ids"* and then listed seven ids
> the scorer has never fired. **Two of them collided with real ones**: a row headed `L4b` described
> TEXANIM drift while the scorer fires `L4b-POINT-SAMPLES`, and a row headed `L7` described a pre-cast
> gate refusal while the scorer fires `L7-MULTICAST` — so a reader who saw `L7-MULTICAST` in the
> output and looked up "L7" was told *"that vehicle is mis-specified — do not cast it."* Both are now
> `H-` ids.

**THE COMPLETE MACHINE LIST, in the scorer's own severity order** (`RUNG_ORDER`, most severe first).
Nothing outside this list is ever printed as a `TOP:` id:

**24 ids, most severe first.** The first two void the instrument and outrank *every* `R-*` result:

`L0d-SCORER-TEXT-DEFECT` · `L9-REPLICATION-FAILED` · `L0-NO-LOG` · `L0-NO-ROWS` · `L0-PRE-S77` ·
`L8-PRIMCAP-TRUNCATED` · `L0b-WRONGLOG` · `L0c-ANSWER-KEY-UNRESOLVED` ·
`L0e-REFUSED-NOTHING-SCORED` · `L2-NEVER-FIRED` · `L3a-CUT-SHORT` · `L3c-ANSWER-MISSING` ·
`L6p-CONTROL-FAIL` · `L6q-CONTROL-ABSENT` · `L1b-15BPP-SUSPECT` · `L4-SPRT-CONTAMINATION` ·
`L4b-POINT-SAMPLES` · `L7-MULTICAST` · `L5-KEY-COLLIDER` · `R-NO-MODEL-FITS` · `R-NONE-SURVIVES` ·
`R-UNDISPLACED` · `R-OPERATION-RESOLVED` · `R-OPERATION-OPEN`

*(`RUNG_ORDER` in `score_uvr.py` is the authority on the exact index; this list is the authority on
the exact spelling. `py score_uvr.py --audit-rung-text <log>` re-checks the scorer against itself.)*

**THE THREE `L0*` OPERATOR/INSTRUMENT RUNGS ARE NEW IN ROUND 4 AND ARE NOT IN THE MAIN TABLE** —
they are about the *scorer and the command line*, not about the cast:

| rung | when it fires | what to do |
|---|---|---|
| **`L0d-SCORER-TEXT-DEFECT` ★★** | the scorer's static self-audit finds a **non-ASCII character in its own rung text** | ⚠ **NOTHING ON THE PAGE CAN BE TRUSTED.** This console is cp1252: one such character *killed* a rung mid-print in an earlier build, taking the whole ladder with it. Ranked first, above everything. Fix the scorer, re-run; the JSON is written first and survives. |
| **`L0c-ANSWER-KEY-UNRESOLVED`** | a declared answer key (from `--answer`, or from the prereg table) **resolves to no scorable group** — it is in neither the log nor the container, *or* it drew but binds to no `so` record | **OPERATOR ERROR, not a result.** One mistyped hex digit does this. The detail lists the keys that effect actually carries. Re-check against the container, remembering the join masks `& 0x7FFFFF`. |
| **`L0e-REFUSED-NOTHING-SCORED`** | **no rung fired, but refusals were raised** — e.g. `--effects` excluded a declared target that drew | **OPERATOR ERROR.** This is the backstop that makes a bare "SCORED / OK" mean what it says. Read the REFUSALS block and drop the flag that caused it. |

**"SCORED / OK" is not a pass mark**: it prints only when *nothing* fired, **including no
RESULT rung and no refusal**, which means the log produced nothing scoreable at all. The `R-*` rungs
are the RESULT family (`R-UNDISPLACED`, `R-OPERATION-RESOLVED:<model>`, `R-OPERATION-OPEN`,
`R-NONE-SURVIVES`, `R-NO-MODEL-FITS`) — **an answer that scores must NAME what it concluded.**
⚠ **That invariant is now enforced, not merely asserted.** Round 4 found three live routes to a bare
"SCORED / OK" over a *healthy* log — a mistyped `--answer` key, an `--answer` key that drew but binds
to nothing, and `--effects` excluding a target that drew. `L0c` and `L0e` close all three: a
declaration the scorer cannot honour now **refuses**, and never falls through to the summary.

⚠ **`R-OPERATION-RESOLVED` PRINTS WITH ITS SURVIVORS APPENDED** — the literal top line reads
`TOP: R-OPERATION-RESOLVED:ADD|ADD_MOD256 [RESULT]`, the models joined by `|`. Look it up under
`R-OPERATION-RESOLVED`; everything after the first colon is the answer, not part of the id.

⚠ **`R-UNDISPLACED` IS THE PUBLISHABLE NEGATIVE.** Earlier drafts called that rung
`L6-PUBLISHABLE-NEGATIVE` — **one outcome, two names, and only one of them is real.** The scorer fires
`R-UNDISPLACED`; this document now uses that id everywhere and keeps "the publishable negative" as
prose only.

| rung | what it looks like | what it means | what to do |
|---|---|---|---|
| **`L0-NO-LOG` / `L0-NO-ROWS` / `L0-PRE-S77`** | no `sfxmeshprobe.log`; or it parses with no rows; or it has MESH rows and **zero UVR rows anywhere** (a pre-s77 file) | probe never armed, `CapturePrims = 0`, the running DLL is not the s77 build, or the log was truncated by a later launch | **INSTRUMENT.** Re-check §1 items 2 and 3 (both arches). Not a result. `L0-PRE-S77` is the exact shape of U1 cast 1's null. |
| **`L0b-WRONGLOG` ★** | the log parses fine, but **not one of the REQUIRED casts (227 / 446 / 424) appears anywhere in it** | ⚠ **YOU ARE SCORING THE WRONG FILE** — almost certainly the U1 ef038 log that `v_parse_uvr.py` hardcodes | **NOT A RESULT.** Re-run with this session's archived copy as the positional argument. §1 item 10. ⚠ **THE TEST IS "227 IS ABSENT", NOT "38 IS PRESENT"** — §5.4 puts ef038 in this log deliberately, and an earlier draft's prose would have condemned the correct file. |
| **`L1b-15BPP-SUSPECT` ★** | UVR rows present, but **not one at `tp = 2/3`** — the cohort keys `408000`/`428000` are silent **and** ef424's `598000` is silent | the 15 bpp emission path has never been exercised (§4.6) and cannot be asserted | **INSTRUMENT SUSPECT. Score nothing 15 bpp**, and do **not** try the next 15 bpp fallback — it would loop through the same untested path. Escalate to a patch read. |
| *(no rung)* | cohort keys **do** emit UVR rows | the 15 bpp path was alive **before frame 433** | **This LICENSES NOTHING about the answer window.** The old `L1c` rung claimed it did; it is deleted. See `L3a`. |
| **`L2-NEVER-FIRED`** | a required effect appears **nowhere** — no MESH row, no UVR row | the cast never fired: wrong menu row, or the battle ended first | **VEHICLE.** Re-check §1 item 5. **ASK THE OWNER §7.3 questions 1 and 2** — were both commands present, and which row did they pick? Then go to `H-SAVE-LOADED` / `H-NO-BATTLE` below before recasting. Not a result. |
| **`L3a-CUT-SHORT` ★★** | the answer key has **no rows**, **and any registered LATE witness is also silent** — for ef227 those are `3DBEC0` (~440–506) and `37BD80` (~422–448) | **THE CAST WAS CUT SHORT.** The answer surface draws at frames 433–505 of a 515-frame cast. **The 15 bpp cohort cannot save you here: its window ends at 432 and the answer's begins at 433 — adjacent and disjoint** (§4.6), so a cast quit at ~430 leaves the cohort *and* every early control looking perfectly healthy | **NOT A RESULT.** This is the trap §7 step 9's landmark exists for. Recast and let it finish. ⚠ An effect with **no registered late witness refuses too**, rather than guessing. ⚠ **Budget check before you recast: one more ef227 cast spends the PrimCap margin** (§6.2). |
| **`L3c-ANSWER-MISSING` ★** | a REQUIRED effect's answer key has no rows **and** the late witnesses show the cast did reach the answer window | one vehicle's answer is missing while another's is present | **NOT A RESULT for the session.** ⚠ This rung exists because a run used to report itself scored when *one* of the answers was missing. **One missing answer fires this even when every other cast scored.** |
| **`L4-SPRT-CONTAMINATION` / `L4b-POINT-SAMPLES`** | rows on the answer key with `src` = `S` or `M`, or `prims = 1` with `uMin == uMax` | a SPRT contribution folded the current page's span into the same accumulator, or the row is a point sample | **CONFOUNDED.** The aggregate is filtered to `src = P` **and** `prims > 1` **unconditionally** (§6.1), and the discarded rows are reported with line numbers. If no scorable row survives, the group returns `NO-SCORABLE-ROWS` — a null, not a verdict. Structurally unexpected (§6.1). ⚠ **`L4b-POINT-SAMPLES` IS THE ONLY `L4b`** — texture-animation drift is `H-TEXANIM-DRIFT` below, and used to be printed here as a second, colliding "`L4b`". |
| **`L5-KEY-COLLIDER` ★** | a masked key in the log is claimed by more than one effect | the three cross-container collisions (§5.1) | **JOIN-ENFORCED, not fatal** — the scorer already joined on `(effectId, key & 0x7FFFFF)`, so each row was credited to its own effect. The rung exists so the reader **sees** what a key-only join would have merged: on `37BD80` it would have made ef227's u-only witness appear to displace v as well. |
| **`L7-MULTICAST` ★** | one effect's frame index **decreases** partway through the file | the same effect was cast **more than once** in this log | **SEGMENTED, not fatal.** The scorer splits and scores casts separately. ⚠ **This is the file the ladder's own recovery instruction produces** ("recast and let it finish"), so it is expected and named. **ASK THE OWNER §7.3 question 7** to tell a deliberate repeat from an artefact, and **re-check the PrimCap budget** (§6.2). |
| **`L8-PRIMCAP-TRUNCATED` ★** | the log carries a `# PRIM CAPTURE TRUNCATED` marker, or an effect's PRIM+STATE count is at `--primcap` | ⚠ **`SfxMeshProbe.cs:787-791` caps per-primitive rows for the PROCESS LIFETIME**, with a static warned-flag that never resets. One archived log already sits at exactly 3,000,000 | **NOT A RESULT.** The patch's "UV accumulation runs before the PrimCap drop" ordering **has never been exercised**, and a truncated UVR read scored as complete is precisely the danger (§6.2). Do not score across the marker. |
| **`R-NO-MODEL-FITS`** | clean `src = P` rows on the answer key, span/histogram is none of the **five** predicted value sets | an unmodelled behaviour (a second transform, a mask this document did not enumerate) | **Record the observed histogram verbatim and stop.** Do not fit it to M1–M6 after the fact. `op_space.py` (§11) re-runs any further candidate operation against the real pool — extend the model space there, not in prose. |
| **`R-NONE-SURVIVES` ★★** | the span has **not** excluded NO-DISPLACEMENT, whatever the histogram shows | ⚠ **THE UNDISPLACED-SURFACE TRAP.** A partial draw of a surface that never moved emits exactly the values that separate OR from the other displaced models (§2.1) | **NOT AN OPERATION RESULT, and specifically NOT "OR".** Reading it as OR is how a null publishes itself. Span first, always. |
| **`R-OPERATION-OPEN` (was L5b) ★** | span is `16,127` and **only the shared values `16` and `127`** ever appear | ADD and OR are both alive (§2.1) | **MAGNITUDE CLASS, OPERATION UNRESOLVED.** A legitimate partial result. Publish it as such, keep the OPERATION sub-rider open, and read ef446's histogram (`43/71/99` vs `27/55/83`, span first) from the same log before concluding. |
| **`R-UNDISPLACED`** *(the PUBLISHABLE NEGATIVE — earlier drafts called it `L6-PUBLISHABLE-NEGATIVE`, which no scorer fires)* | everything reads its raw span — displaced slots included — **and §4.4's ratio-1.00 controls (rows 8 and 9) reproduce EXACTLY** | the clean control spans prove the instrument works on this container in this cast, so this is a **measurement**: **M4, Q1 refuted at 15/8/4 bpp on ef227** | **A REAL, PUBLISHABLE NEGATIVE.** It would falsify the generalisation, and that is a result worth having. Confirm rows 8 and 9 value by value before writing it down. |
| **`L6p-CONTROL-FAIL`** | a ratio-1.00 control **drew** and **failed** equality | the instrument is not measuring what it claims on this container | **NOT A RESULT.** Back to `L0`. |
| **`L6q-CONTROL-ABSENT` ★** | a **pre-registered** ratio-1.00 control emitted **nothing at all** | ⚠ the signature of a partial log, a wrong window, or an early-frame emission failure — **kept separate from `L6p` so "drew and failed" is never confused with "never arrived"** | **NOT A RESULT.** An absent key has no tri ratio, so this roster **cannot** be derived from the log — it is pre-registered (§4.4). Both of ef227's hard controls used to be able to go missing while the run still scored. |
| **`L9-REPLICATION-FAILED` ★★** | ef038's `3ABDC0` / `38BE00` arms do **not** reproduce the archived U1 result in this log. **It fires from `--selftest`, is ranked above the whole `R-*` family, and its outcome is carried in the JSON** — so a failed replication changes the `TOP:` line and cannot hide behind a clean-looking result | ⚠ **A SESSION-LEVEL INSTRUMENT REGRESSION.** The DLL hash was taken before the launch and cannot see one; §5.4's fourth cast is the only thing in this protocol that can | **THE WHOLE SESSION IS VOID. Publish nothing from this log** — not ef227, not ef446, not ef424 — regardless of how clean they look. This outranks every result rung. Re-derive the instrument before re-casting. ⚠ **It only ever fires if you passed `--selftest`** — §9.2's command does; a run without it has no replication check at all. |

### 8.0b THE HUMAN-JUDGED RUNGS — `H-` prefixed, and **no scorer prints one**

These are real rungs and the diagnosis needs them, but every one of them is decided by the reader, by
the owner's §7.3 answers, or by a *different* tool (the pre-cast gates). **Do not search the scorer's
output for an `H-` id; it will not be there.** Each row names what it used to be called, because the
old name is what a stale note or an earlier draft will say.

| rung | *(old name)* | what it looks like | what it means | what to do |
|---|---|---|---|---|
| **`H-SAVE-LOADED` ★** | was `L2s` | `L2-NEVER-FIRED` fired, the owner reports **either command missing** (§7.3 q1), **and the party roster (§7.3 q1b) is empty, short, or not the opening four** | ⚠ **A SAVE WAS LOADED.** The `[[playable]]` recruit is party-init; a pre-deploy save has neither character, so no command exists to cast from | **NOT A RESULT, and not a vehicle failure.** Quit, **New Game**, redo §7 from step 2 — **but read `H-PARTY-FULL` first, because for the other cause New Game is not a fix, it is a loop.** |
| **`H-PARTY-FULL` ★★** *(new in round 4)* | **the same symptom** — a command missing from the battle menu — but §7.3 q1b reports a **FULL four-member party**, classically **Zidane / Cinna / Marcus / Blank** | ⚠ **THE RECRUIT SILENTLY NO-OPPED.** `EventEngine.partyadd` walks for the first empty slot and, on a full party, **returns a failure flag that field 30301's `Main_Init` never tests** — no message, nothing on screen. The New-Game route passes through field 6000, whose opening scene *rebuilds the party to four* while the owner stands there, so **the longer they linger before warping, the likelier this is.** ⚠ **The partial case is worse**: a three-member party seats Iviv and fails Steiniv, giving `Spark` but no `Rune` — cast 1 scores and casts 2/3/4 are impossible, which reads downstream as a cut-short session | **NOT A RESULT — and DO NOT "fix" it with New Game; that returns to the same opening, the same rebuild and the same failure.** ★ **THE RECOVERY IS 20 SECONDS AND IT IS IN THE FIELD MENU:** this install runs `[Hacks] AllCharactersAvailable = 1`, so the **Party** submenu lists *every* defined character regardless of story state — **seat Iviv and Steiniv there directly** and cast normally. Their learn lists and MP are correct. ⚠ **`~ → Cheats → Full heal party` cannot help a character who is not seated** — it iterates the party only. |
| **`H-NO-BATTLE`** | was `L2b` | **no MESH rows for any effect at all**, or a log of a few KB; §7.3 q4 says the battles did not happen where they should have | the battle never happened — wrong field, or the game was quit before combat | **NOT A RESULT.** Redo §7 from step 4, and check §7.3 q4 against field 30301. |
| **`H-REAL-NO-DRAW`** | was `L3b` | no row on the answer key, late witnesses present, §4.4 passes — i.e. **`L3a` and `L3c` both refused to fire** | the answer surface genuinely never drew this cast | **A REAL NULL on the vehicle.** ⚠ Do **not** read it as "the mechanism failed" — a surface that never draws says nothing about displacement. **Score ef446's `578000` from the SAME log** (§5.2) — that is what casting it pre-emptively bought, **and ef446 is CAST 2, so in a normal session it has already run.** ⚠ **If cast 2 never ran**, ef446 is one more *encounter* away, not another session: relaunching would truncate the log (§6.3), so archive first, then re-launch and cast ef446 alone. Row 4 (`18BD00`) is pre-registered as silent; its absence is expected and irrelevant. |
| **`H-TEXANIM-DRIFT` ★** | was a second, colliding `L4b` | clean `src = P` rows, but the per-frame span **moves through the cast** — early frames raw, late frames displaced — in a way partial draw does not explain | ⚠ **TEXANIM DRIFT.** The W7 texture-animation lane rewrites display-list UVs mid-cast; ef038 is the corpus's only `Hi_StartSummonTexAnim` caller, but the lane is not ef038-exclusive | **NOT A DISPLACEMENT READING.** Outside §3.2 by design — do not fit it to M1–M6. Record the per-frame series verbatim, check whether `prims` is constant across the drift, and open it as its own rung. ⚠ **The scorer does not detect this** — it is a judgement made by reading the per-frame series the report prints. |
| **`H-POOLED-CONTROL-SOFT`** | was `L6''` | rows 8 and 9 pass, but a **pooled** control fails containment | a pooled key drew less than its bound mesh | **SOFT FLAG, not a stop** (§4.4). Note it, score on. |
| **`H-PREREG-REFUSED`** | was `L7` *(which collides with the real `L7-MULTICAST`)* | **any** of `prereg_ef227.py` / `prereg_ef446.py` / `prereg_ef424.py` refuses **before** the cast | the live stock container no longer matches the dump its predictions were derived from, or its answer record no longer reads the halfwords §2/§5.2 state | **That vehicle is mis-specified — the "it turned out to be 0/0x80 after all" case.** Do not cast it. Re-derive its table first. A refusal on ef446 is the one to expect: it is the only container with no archived draw to cross-check against. |
| **`H-DOC-DIVERGES` ★** | was `L7b` | `prereg_vs_document.py` exits non-zero | the gate and this document disagree on a cell | **The gate is right and this document is stale (§9.1).** Score against the gate's JSON, and fix the document cell before publishing anything. |

**PROVEN, NOT PROMISED.** `null_battery.py` (§11) feeds the scorer **15 cases landing on 14 distinct
named rungs** — cut-short, answer-absent, a true OR, SPRT contamination, a two-cast log, an absent hard
control, a key collider, a PrimCap-truncated log, **the real archived wrong-log file**, three
UNDISPLACED lanes (`R-UNDISPLACED`, `R-NONE-SURVIVES`, `R-NO-MODEL-FITS`), a **failed replication**, a
mistyped answer key, and a passing replication run as its contrast — and asserts that each lands on a
**different** named rung, that **not one prints "SCORED / OK"**, that **not one produces a traceback**,
and that **every run ends on its `LADDER:` line**. It passes 15 of 15. A healthy baseline is also run,
to prove the ladder does not over-block: it fires exactly one rung, a **RESULT**.

⚠ **THE BATTERY RUNS EVERY CASE VERBOSE, AND THAT IS THE POINT.** It used to run everything `--quiet`,
which prints only ASCII summary fields — so **no rung's DETAIL string was ever encoded** and a whole
class of defect was invisible to it. That is exactly how a crash survived in the one rung whose job is
stopping a null being published as a result. A separate check (`exercise.py`, §11) drives **all 24
`RUNG_ORDER` ids** through a real cp1252 console and asserts each printed its detail in full.

### 8.1 Fallbacks, in order — everything below this line costs a relaunch

ef446 and ef424 are **no longer fallbacks**; they are cast in the session (§5). What remains:

1. **ef427 `Waterga`** — ★ **promoted, for a different reason than the earlier draft gave.** It is the
   corpus's **only** array-vs-binding de-confounder (§0.2), and that confound sits under **both** ef038
   and ef227. It is genuinely weak at Q2 — `A = 0x40` gives the smallest magnitude-vs-flag gap (§0.1),
   its two slots share key `5A8000` so the row pools both, and on its pool `{0,62,63}` ADD, OR and XOR
   collapse to the identical set `{64,126,127}` — **so do not cast it for Q2. Cast it for Q3.**
2. **ef381 `Ark__Full`** — relaunch class (a new `Actions.csv` row, appended **last** so it takes id 205
   and rows 192–204 do not renumber). 96-texel separation, the richest container in the corpus (85
   slots, 37 displacing, all four families), and — uniquely useful after §2.1 — **its ADD and OR spans
   differ** (`u[32,95]` vs `u[32,63]`), so it can resolve the operation on the *span* alone.
3. **ef447** — duplicates ef381's slot signature; no new information.
4. **ef261** — the only v-axis outlier, but 10 primitives total, no mesh at the slot index,
   `ORDER_UNMEASURED`, and relaunch class.
5. **ef405 is NOT a fallback — and this is the document's one load-bearing STRUCTURAL claim, so here
   is its source.** It carries an identical discriminator to ef227's and *appears* on the bench as row
   194's `vfx2` (`Bahamut Cinema;194;…;84;405;…`), but it is **unreachable, verifiable in two lines of
   engine source**:
   - **`btl_vfx.cs:99-100`** returns `(SpecialEffect)cmd.aa.Vfx2` **only** when
     `(Target == ManyAny && cursor == 0) || meteor_miss != 0 || short_summon != 0 || <Beatrix
     alternate>`. **Bench row 194 targets `AllEnemy(8)`, not `ManyAny(3)`** — the first disjunct is
     false by data.
   - **`btl_cmd.cs:1583-1615` (`DecideSummonType`)** is the only writer of `short_summon = 1`, and it
     **returns early** unless the ability id is one of a **hardcoded whitelist of stock
     `BattleAbilityId`s** (Shiva, Ifrit, Ramuh, Atomos, Odin, Leviathan, Bahamut, Ark, Carbuncle x4,
     Fenrir x2, Phoenix, Madeen). **A minted id — 194 — is in none of them**, so `short_summon` stays
     `0`.
   Both disjuncts are false by construction, so `vfx1` always plays. **Structurally unreachable** —
   which is what makes §0's roster of two relaunch-free Q2 discriminators **provably maximal**, not
   merely "the two we found".

---

## 9. SCORING

### 9.1 Before the cast

**Run all three gates — one per MEASURING cast — then the cross-check.** Each re-reads its container's
live stock bytes through the kit, **refuses to emit anything** if they do not hash-match the corpus
dump, and re-derives that container's whole table from its own bytes. ⚠ **Round 3 shipped the ef446 and
ef424 gates; before that only ef227 had one**, which left every ef446 and ef424 fact with no hash-match
refusal and no live re-derivation — worst on ef446, the one container with no archived draw, exactly
where a drifted dump would go unnoticed:

| gate | covers | what only it can prove |
|---|---|---|
| `prereg_ef227.py` | cast 1, the answer container | the §3.3 eleven-slot table and the answer slot's **whole model space with value sets** |
| `prereg_ef446.py` | cast 2, the rescue | ef446 is the ONE container with no archived draw — the gate re-derives record/key/faces/UV-entries/pools/value sets from bytes, and **scans all nine archived logs to prove** the no-draw rather than assert it |
| `prereg_ef424.py` | cast 3, the clean u arm | the key table with tri-count gates, **and that every archived ef424 figure is a TWO-CAST MERGE** (the log holds two casts; one healthy cast is ~half every row count quoted in §5.3) |

**Cast 4 (ef038, §5.4) has NO gate and needs none** — its expectations are not derived offline, they
are the *archived measured result*, and `score_uvr.py --selftest` re-asserts them against the new log.

Each gate takes `--selftest`, which flips one byte in memory and asserts the gate refuses. **Run it
once — a refusal nobody has ever seen fire is a wish in a docstring.** All three have now fired.

**The predictions scored against the log must be the ones these scripts emit, not the ones typed
above** — if they ever diverge, the scripts are right and this document is stale. **That clause is now
safe to obey, and it was not before:** the earlier gate emitted three models (MAGNITUDE / FLAG /
NO_MECHANISM) and no value sets, so the artifact run immediately before the cast contradicted §2.1's
five-model space *by omission* and the tie-break resolved it in favour of the pre-repair space. The
gates now emit **NONE, ADD, ADD_MOD256, OR, XOR, FLAG** with each model's value set, its degeneracy
class, and — per model — **which values separate it from the other DISPLACED models, and which of
those are also NONE's values.**

**The clause is enforced, not promised:** `prereg_vs_document.py` parses this document's tables and
compares them cell by cell against what the three gates emit, printing AGREE/DIVERGE per assertion and
exiting non-zero if anything diverges. **Run it after any edit to §2, §2.1, §3.3, §4.4, §5.2 or §5.3.**

Then run the §1 item 10 gate: run **`py score_uvr.py <the OLD ef038 log>`** and confirm it returns
`L0b-WRONGLOG` and scores nothing. **Then run `py null_battery.py`** — nine nulls, nine distinct named
rungs, no "SCORED / OK" (§8) — and **`py calibrate_scorer.py`**, which asks the other half of the
question: can the scorer tell the MODELS apart at all?

### 9.2 After the cast — ★ THERE IS EXACTLY ONE SCORER, AND THIS IS ITS COMMAND

⚠ **TWO RIVAL SCORERS USED TO EXIST AND THIS DOCUMENT NAMED THE WEAKER ONE.** `protocol\score_u2.py`
had no cast segmentation, no prims/span constancy check, no self-test and no calibration harness; the
other had all four. They took **different CLI shapes**, so the command printed here was *wrong for the
stronger one* — and a reader following it scored a cast with the half that cannot see a two-cast log.
**They are now folded into one.** `protocol\score_u2.py` no longer exists: it is
`protocol\score_u2.py.RETIRED-DO-NOT-RUN`, tombstoned so that even running it explicitly prints the
correct command instead of a stale report.

> ### THE ONE SCORER
>
> ```
> py C:\gd\SCRATCH\summon-format\repaint-w6b\second-container-cast\score_uvr.py <archived log>
>        --require 227,446,424,38 --selftest
> ```
>
> ★ **THE LOG PATH IS POSITIONAL AND MANDATORY. There is NO `--log` flag.** Any command anywhere that
> reads `score_u2.py --log X` is stale on **both** counts.
> Useful options: `--require LIST` (the session's required casts — **add `38` for the §5.4 fourth
> cast**), `--selftest` (assert the three known ef038 results; **this is the §5.4 replication check**
> when it is run against *this session's* log, and it is what fires `L9-REPLICATION-FAILED` —
> **a run without `--selftest` has no replication check at all**), `--primcap N` (default 3,000,000,
> the live ini value), `--liveness LIST`, `--detail HEX`, `--quiet`.
> ⚠ **`--answer EFF:KEY` OVERRIDES THE ANSWER KEY AND IS EASY TO MISTYPE** — one wrong hex digit names
> a key that exists in neither the log nor the container. **The scorer now REFUSES that rather than
> falling through** (`L0c-ANSWER-KEY-UNRESOLVED`, and the detail prints the keys the effect really
> carries), so a mistype is loud instead of silent. Run it only when you mean to re-point the read.
> ⚠ **`--effects LIST` is a debugging filter, not part of the scoring command.** Excluding a declared
> target that drew is refused (`L0e-REFUSED-NOTHING-SCORED`). Do not use it on the session's log.
> Every run ends on **`LADDER: <n> rung(s) fired.  TOP: <rung> [<verdict>]`** — **that line is always
> last** — with the full JSON at `score-out\score.<log-stem>.json` including `ladder`, `top_rung`,
> `scored_ok`, `selftest` and `answer_keys_unresolved`. Under `--selftest` a **`SELFTEST`** block
> prints **above** the ladder line, and a failure also sets a non-zero exit code — so **read the exit
> code, not only the last line.**

⚠ **DO NOT reuse `…\u1-second-array\s77-read\v_parse_uvr.py`.** It pins its input at line 22 to the old
ef038 log with **no argv override**, and its `decode_key()` mislabels the key's depth field (§6.1). Run
on the new cast as the earliest draft instructed, it emits a confident, well-formed report containing
**zero ef227 rows**.

`score_uvr.py` joins on `(effectId, key & 0x7FFFFF)`, measures each key's tri-count ratio **from the
log and the container** rather than from any table (so it works on a cast nobody has seen), applies the
gate that ratio implies, and keeps the span read and the histogram read in **separate** JSON fields so
§2.1's distinction cannot be lost — `model_tests[<MODEL>].span_u`/`.span_v` (with `.rel_u`/`.rel_v`) for
the span, `value_hist` + `observed_value_set` + `model_exclusive_values` for the histogram, and
`value_test_decisive` for whether the histogram is even allowed to exclude a model on this key.
**§2.1 carries the full field table; `span_matches` and `histogram_verdict` are not field names and
never were.**

**Scoring order, and it is not optional. Steps 2, 4, 6 and 14 are NEW; step 10 is INVERTED; step 5
gained the ABSENT case:**

1. **Is this the right log?** At least one of the REQUIRED casts must appear. If none does →
   `L0b-WRONGLOG`, stop. ⚠ **Do not test for "38 is present" — 38 is supposed to be here** (§5.4).
2. ★ **Is the capture complete?** A `# PRIM CAPTURE TRUNCATED` marker, or an effect at `--primcap`
   → `L8-PRIMCAP-TRUNCATED`, stop. Read the printed PRIMCAP BUDGET section even when it passes.
3. **§4.6 liveness.** Did any `tp = 2/3` key emit a UVR row? If none → `L1b-15BPP-SUSPECT`, stop.
4. ★ **Was any effect cast more than once?** A frame index that decreases → `L7-MULTICAST`: score the
   casts **separately**, and ask §7.3 question 7.
5. **§4.4 controls, by the right gate.** Rows 8 (`39BE40`) and 9 (`3DBE00`) must reproduce their raw
   spans **exactly** — that is the hard stop (`L6p-CONTROL-FAIL`). ★ **An ABSENT hard control is a
   FAIL too** (`L6q-CONTROL-ABSENT`), from the pre-registered roster. Pooled keys are checked for
   **containment** only; a miss there is a soft flag (`H-POOLED-CONTROL-SOFT`), never a stop. Row 10 (`3BBD40`, ratio
   0.70) is corroboration and gates nothing. ⚠ Read "mesh's own tris" as **triangles** — §4.4's
   conversion sentence, or you will demote the primary control on arithmetic.
6. ★ **Is an answer key silent?** If so, **read the LATE witnesses before anything else**:
   `L3a-CUT-SHORT` if any is also silent (**the 15 bpp cohort cannot license a no-draw** — §4.6);
   `L3c-ANSWER-MISSING` if the late witnesses show the cast did reach the window.
7. **The join assertion, as a SET.** No row credited to `(227, 598000)` may carry `effectId != 227`,
   and the same applies to `37BD80` and `3BBDC0` (§5.1). The scorer refuses if one does and reports
   every collider it saw.
8. **`src` and `prims`** on the answer rows → `L4-SPRT-CONTAMINATION` / `L4b-POINT-SAMPLES`. The
   filter to `src = P` and `prims > 1` is **unconditional**; check what it discarded.
9. **Per-frame stability.** Do the spans move through the cast beyond what partial draw explains?
   → `H-TEXANIM-DRIFT` before any model is fitted — a JUDGEMENT the reader makes from the printed per-frame series, **not** a rung the scorer fires (§8.0b).
10. ★ **THE ANSWER SPAN FIRST, THEN THE HISTOGRAM, `uMin` before `uMax`** → §3.1. **This step was
    written the other way round and round 3 inverted it.** If the span has not excluded
    NO-DISPLACEMENT, the read is `R-NONE-SURVIVES` and **a sighting of 25/55/85 is NOT "OR"** (§2.1).
    A span of `16,127` with no separating value is `R-OPERATION-OPEN`, not a MAGNITUDE verdict.
11. **`v@15`** → §3.5 (2), which kills or keeps M6.
12. **The displaced controls** (rows 2, 3, 5–7 by containment; ef424's `37BC80` by **equality** — it is
    the only clean u witness) → §3.4's split table.
13. **ef446's `578000`** from the same log → the independent operation read (§5.2), **span first there
    too**. If it disagrees with ef227, that is the **BOTH BRANCHES OBSERVED** row of §3.4, not a tie to
    be broken — and ef446 **corroborates, never carries** (§5.2).
14. ★ **THE REPLICATION.** `--selftest` must pass on ef038's `3ABDC0` and `38BE00` (§5.4). **If it does
    not, stop and publish nothing** — `L9-REPLICATION-FAILED` voids the session.
15. Only then write a verdict, and write the *pattern*, not just the winner.

### 9.3 Confidence discipline

A single clean session reproducing the §3.3 table promotes the mechanism from "one container" to
**"four containers, three depths, four families"** — ef038, ef227, ef446 and ef424, all in one log —
a corpus LAW at the level of evidence this arc uses. ⚠ **Count ef038 as the REPLICATION, not as a
fourth independent witness**: it is the container the claim came from, re-measured to prove the
instrument, and §4.7 already says only its **v** arm is airtight. The three *new* containers are what
carry generalisation. It does **not** license dropping the §3.5 scope, and it does **not** license the
word "magnitude" unless §2.1's read — **span first, then histogram** — earned it. Write the law with
its depth qualifier and its operation qualifier both attached.

---

## 10. WHAT MOVES IN THE REPO — NOTHING, UNTIL THE LOG IS SCORED

**No constant changes as part of this cast.** If the read lands, the follow-on is a **coordinated** text
change, never a string edit: `depth_attribution.U_DISPLACEMENT_CAVEAT` is consumed by `repaint.py`
(7 call sites), `reskin.py`, `tests/test_summon_repaint.py` (4 assertions including a per-piece
substring loop) and `u1_gates.py`, and it is spent through a `txt % detail` path so it **may never
contain a literal `%`**. That edit is a separate rung with its own review.

★ **AND THE RUNG HAS A NAME — this document used to end without saying it, leaving "what happens next"
split across two files with the answer in the other one.** It is **OPTION-3 ADOPTION: the kit MODELS
the displacement rather than merely disclosing it** (`studies/custom-summons/tier-w/PLAN.md` — the
gate is already MET and adoption was deliberately **sequenced after this cast, because ADD-vs-OR
changes the arithmetic the kit would ship**: `eff_A_linear` / `eff_A_mod256` do addition, and under OR
the displacement is a no-op wherever the raw byte already carries the halfword's bits). **That is why
Q2 is worth a session, and it is the only thing waiting on this log.**

⚠ **A CONCURRENT SESSION IS EDITING THAT CONSTANT RIGHT NOW.** At authoring time the worktree carried
uncommitted changes to `depth_attribution.py`, `repaint.py`, `reskin.py`, `test_summon_repaint.py`,
`u1_gates.py` and `CHANGELOG.md` that this protocol did not make and did not touch. The constant has
already been rewritten from three open riders to **five**, folding in the s77 mechanism read. **Two of
this cast's targets are now named riders in shipped kit text:**

- **rider (1) GENERALISATION** — "ONE CONTAINER, ONE CAST … a second container's log-only cast is what
  would make it a law". That is precisely Q1.
- **rider (2) THE OPERATION** — quoted in §0. That is precisely Q2, and its framing is what caught the
  missing XOR branch (§3.1) — and, on re-reading, the missing **OR** branch too (§2.1).

Rider (3) DEPTH is the same confound §3.5 measures from the other direction. **Re-read the live
constant before scoring**, and treat §10's description of it as a snapshot, not a source of truth.

Two further text obligations this repair created, to be spent in that same coordinated edit — not here:

- ef038's **u** arm rests on a key pooling 20 records at ratio 0.31 (§4.7). Any kit or doc text that
  states the u result as settled is overstated; only the v arm is airtight today.
- **Wrap and clamp are not castable** on stock bytes (§3.6). Text that carries them as an open
  measurable question should say "not testable without authoring a high-UV displacement ourselves".

*(Append the scored result here after the cast. Do not edit §3.)*

---

## 11. ARTIFACTS

Everything decoded lives in SCRATCH; this document carries only counts, ids, spans and confidences.

**★ THE THREE THAT ARE RUN, and nothing else is:**

| when | command |
|---|---|
| **before the casts** | `py protocol\prereg_ef227.py` · `py protocol\prereg_ef446.py` · `py protocol\prereg_ef424.py` · then `py protocol\prereg_vs_document.py` |
| **after the casts** | `py score_uvr.py <archived log> --require 227,446,424,38 --selftest` |
| **to trust the scorer** | `py calibrate_scorer.py` (can it tell the MODELS apart?) · `py null_battery.py` (can it tell a NULL from a RESULT — nine cases?) |

Directly under `C:\gd\SCRATCH\summon-format\repaint-w6b\second-container-cast\`:

| file | what it is |
|---|---|
| ★★ `score_uvr.py` | **THE ONE SCORER — run this after the cast. The log path is POSITIONAL and mandatory; there is no `--log` flag** (§9.2). Joins on `(effectId, key & 0x7FFFFF)`, measures each key's tri-count ratio from the log **and** the container rather than a table, assigns the EQUALITY / CONTAINMENT / corroboration gate that ratio implies, filters the aggregate to `src = P` and `prims > 1` unconditionally, segments repeat casts, keeps the span read (`model_tests[M].span_u`/`.rel_u`) and the histogram read (`value_hist`, `observed_value_set`, `model_exclusive_values`) in separate JSON fields (§2.1 names them all), and ends on a **named ladder rung**. `--selftest` asserts the three known ef038 results, fires `L9-REPLICATION-FAILED` and exits non-zero if any fails — which is also §5.4's replication check when it is pointed at this session's log. |
| ★ `null_battery.py` / `null-battery\` | **the proof that a null cannot print "SCORED / OK".** Nine cases — cut-short, answer-absent, a true OR, SPRT contamination, a two-cast log, an absent hard control, a key collider, a PrimCap-truncated log, and **the real archived wrong-log file** — each asserted to land on a **distinct named rung**. Passes 9 of 9. It also runs a healthy baseline, which fires exactly one rung and that rung is a RESULT. |
| ★ `calibrate_scorer.py` / `calibration\` | the model-discrimination harness: synthetic ADD / OR / XOR / FLAG / NONE casts, asserting the scorer names the right one. **It shares `null_battery.py`'s fixture generators**, so there is one fixture source, not two that drift. |

Under `…\second-container-cast\protocol\`:

| file | what it is |
|---|---|
| `prereg_common.py` | the shared gate machinery: the layout-law record walk, the key derivation, **THE MODEL SPACE** (`axis_model_space` — every model applied to a slot's actual byte pool, degeneracy classes, separating values), the hash gate and its `--selftest`, and the archive segmenter. |
| ★ `prereg_ef227.py` | **run this before cast 1.** Re-derives §2/§2.1/§3.3/§4.4 from the live stock bytes by the layout law directly (not via `so_record`), emits all six model names with value sets, and refuses if the dump has drifted from the install. |
| ★ `prereg_ef446.py` | **run this before cast 2.** ef446 is the one container with NO archived draw, so this gate matters most: it re-derives record `0x2d134`, key `578000`, the bucket/face/triangle/UV-entry counts, the pools and the value sets, **scans all nine archives to prove the no-draw**, and lists the three cross-container key collisions. |
| ★ `prereg_ef424.py` | **run this before cast 3.** The full key table with per-key tri-count gates and raw key forms, the ratio-1.00 isolated u arm stated for quotation, and **the two-cast segmentation of the cast-c archive** — every ef424 row count in §5.3 is a merge of two casts. |
| ★ `prereg_vs_document.py` | **the enforcement of §9.1's authority clause.** Parses this document's tables and compares every cell it can against the three gates' JSON; prints AGREE/DIVERGE per assertion and exits non-zero on any divergence. |
| `prereg-ef227.json` / `prereg-ef446.json` / `prereg-ef424.json` / `prereg-vs-document.json` | their outputs — every slot with keys, buckets, face/triangle/UV counts, raw pools and per-axis model spaces; the key census with pool unions and tri sums; the archive join; and the cell-by-cell agreement ledger. |
| ⚠ `score_u2.py.RETIRED-DO-NOT-RUN` | **the retired second scorer, kept only as a tombstone.** It opens with a `raise SystemExit` that prints the correct command, so even an explicit `py <this path>` cannot produce a stale report; its `__pycache__` was removed so it cannot be imported either. **Nothing references it.** Everything it owned — the named ladder rungs, the wrong-log refusal, the 15 bpp cohort, the `(0,0)` control roster — was folded into `score_uvr.py`. |
| ★ `u2_repair_checks.py` / `u2-repair-checks.json` | the measurements the eight repair fixes are stated on: the UVR-by-depth census across all nine archived logs, the corpus wrap/clamp anti-correlation, the per-key draw table with raw key forms, and the cross-container key collisions. |
| `budget_from_logs.py` / `budget-from-logs.json` | §4.1 draw evidence and §6.2 row budget, derived from the archives. |
| `risk_checks.py` / `risk-checks.json` | §4.2 isolation against the draw population, §6.1 `src` prediction, and the `598000` collision — **the first of §5.1's three**; `prereg_ef446.py` owns the full set. |
| `ef424_pair.py` / `ef424-pair.json` | the `598000` collision resolved to the exact records, and ef424's full 2x2. |
| `op_space.py` / `op-space.json` | **§2/§3.1 the operation space** — every candidate byte operation applied to the real UV pool of every displacing slot in both containers, with degeneracies marked. Extend the model space here if `R-NO-MODEL-FITS` fires. |

Upstream, unchanged: the two censuses under `…\second-container-cast\censusA\` and `…\censusB\`, the
adversarial verifier outputs under `…\repaint-w6b\adversarial-u2\` (`isolation.json` owns the tri-count
ratios, `deconfound.json` owns §0.2's group sweep, `verify\exotic-opsets.json` owns §2.1's value sets),
the mechanism read at `…\u1-second-array\s77-read\REPORT-S77-READ.md`, and the archived logs in
`…\repaint-w6b\capture-logs\`.

⚠ `…\u1-second-array\s77-read\v_parse_uvr.py` is kept for provenance of the **U1** read only. It is
**not** the scorer for this cast (§9.2).

The engine instrument is `memoria-patches/s77-sfx-uv-range.patch`, already built and deployed on both
arches. **This protocol does not rebuild, redeploy, or revert it.**
