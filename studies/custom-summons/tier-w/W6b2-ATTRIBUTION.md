# W6b-2 — DEPTH ATTRIBUTION (recon synthesis: two channels, 246 cells, one structural wall)

> **Status: RECON COMPLETE — and KIT INTEGRATION SHIPPED (§10).** Two sweep lanes, three refuters
> and a completeness critic; §0–§9 are the RECON record, written before any kit code changed, and are
> left as written. §7 is the build list — **now built**; §10 is the integration round, its gates
> (`w6b2i_gates.py` 11/11) and the two corrections its review forces on §7's own numbers; §8 is the
> cast recommendation (cast B now runs through the shipped lane).
>
> **Record under extension:** `W6b-SCENERY.md` (W6b-1's classes, §1.2 class C, §3.2's depth-unknown
> refusal, §5's cast ladder, §7.2 open questions **1, 2, 3 and 4 — all four now answered**), `PLAN.md`.
> **Recon this document distils** — all outside the checkout, all Square-Enix-derived, never in the
> repo, under `C:\gd\SCRATCH\summon-format\texel-w6b\w6b2\`: `A4-TPAGE-ATTRIBUTION.md` (the decision
> dossier, cited below as *A4 §N*) · `L1-TPAGE-SWEEP.md` + `tpage_sweep.json` + `tpage_discover.json` ·
> `L2-WRITE-SCAN.md` + `write_scan.json` · `V1A-VERIFY.md` + `v1a_verify.json` + `v1a_scan.json` ·
> `V1B-VERIFY.md` + `v1b_audit.json` + `v1b_recheck*.json` · `V2-VERIFY.md` + `v2_check.json` ·
> `CRITIC.md`.
>
> **RE-MEASURABILITY, SCOPED HONESTLY** (the previous draft claimed this for every number and was
> wrong — and its first re-scoping was *still* wrong: the completeness critic tokenised the scoped
> sections against the gate's own stdout and found **ten** stated numbers that appeared nowhere in
> it): **§0–§4, §6 and §7 are re-measured by `w6b2_gates.py` on each run — 17/17**, and that now
> includes every one of the ten the critic named — the residue headline and the surface percentage
> (H1), the largest caveat and the calibration headline (H2), the ambient rate (H9), the
> pointer-table refusal rate and the warning container's call count (H13). **No number in the scoped
> sections is stated but ungated.** §5 is an argument, not a measurement. §8's in-game facts are
> `W6b-SCENERY.md` §5's, not re-measured here. Where a number disagrees with a dossier, **both
> predicates are stated** rather than reconciled away; §6 collects them, and each row carries **its
> refuter's verdict word verbatim *where a refuter produced one*** — rows 7 and 8 are
> `SELF-MEASURED, UNREFUTED` and say so in those words, and row 11 prints both words.
> `w6b_gates.py` was re-run unchanged and is still **7/7**.

---

## 0. THE SIX THINGS THIS RUNG DECIDED

1. **The wall is real, the lever is real, and the lever is BOUNDED BY THE WALL.** W6b-1 closed
   attribution-limited: **2,385 of 2,572** scenery page-cells (92.7 %) had no `so` reader, so the
   container stated no depth and the edit lane refused them by name. **246 of them (10.31 %) now
   carry a depth the container states somewhere else** — **189** from the id-3 program's own texture
   registration (channel **P**) and **57** from re-reading the container's own `so` records at
   **page** rather than **UV** granularity (channel **G**). **2,139 remain refused.**
2. **★ THE CEILING IS STRUCTURAL, NOT STATISTICAL — this is the finding that bounds the arc.** The
   program idiom registers a texture **onto a model**. **222 of 372 containers declare zero
   non-creature GEOM blocks**, have no model to register on, and make **zero** such calls — and they
   hold **1,278** of the unknown cells (53.6 %). Sharpened by the refuter: in those 222, calls to
   *any* texture-registration op are **0**, to the effect-model draw op **0**, while **221/222** do
   make thousands of other resolved engine calls. **The whole named model-draw surface is silent
   there.** Whatever draws those pages, **it is not these containers' own id-3 programs.**
   **Do not project 10.31 % forward to the 92.7 % surface. That projection goes through a wall.**
3. **★ AND THE LEVER COVERS 86.55 % OF ITS OWN SURFACE, NOT 100 %.** The recovered idiom accounts
   for **238 of 275** textured-registration call sites corpus-wide. **37 sites in 11 containers stay
   dark**, refused on a predicate the refuter rated **PLAUSIBLE, not confirmed** (§2). This number
   belongs in the headline and is in it.
4. **★ CHANNEL G WAS FREE — AND IT IS A GRANULARITY BUG FIX WITH NO INDEPENDENT REACH.** The census
   attributed an `so` record's depth **only to the cells its stored UVs physically touched**: the
   right instrument for READERSHIP, the wrong one for DEPTH, since a page's draw mode governs all
   **256 lines** — both stacked cells of its column. Re-reading at page granularity needs no
   disassembly at all. **But all 57 of its cells are `y = 384` lower halves, and 57/57 have a stacked
   partner the census already knew: channel G opens ZERO new columns.** It propagates a depth the
   container had already stated *downward across a cell boundary*. That is worth having — it is
   exactly W6b-1's blind spot, fixed as a class — and it is not a new source of evidence.
5. **THE POSTURE: CHANNEL G LICENSES, CHANNEL P DISCLOSES.** A program-derived depth **is** the
   container stating a depth — and it is still a **REGISTRATION**, which W6b-1's own cast ladder
   spent two playtests proving is not a draw. §5 argues it; the short form is that the kit already
   refuses to *choose* a depth where its evidence is strongest, so a weaker channel cannot be granted
   a stronger authority.
6. **THE WRITE-REFUSAL LIST IS EXACTLY RIGHT — delta 0 in both directions**, now **refuted by a
   genuinely independent instrument** rather than cross-checked against itself (§6 row 12), **and the
   one load-bearing unverified assumption underneath it is settled**: the VRAM transfer op that
   W6b-1's DIRECTION LAW reads as a **READ** really is one, grounded in the engine's own dispatch
   table and handler rather than in an op-table arity that **could not discriminate it**. The 113
   disclosed cells and the W6b-1 cast licence no longer rest on a name nobody had checked.

---

# 1. THE GRANULARITY STATEMENT — and its own exception

```
one texture-page word  =  a 64-halfword x 256-line PAGE
one census page-cell   =  a 64-halfword x 128-line CELL
                       => one page word names a COLUMN of TWO STACKED CELLS
```

A recovered constant page word therefore attributes depth to **both** stacked cells of its column.
That is sound — the draw mode governs all 256 lines while the page is sampled — and it carries one
honest consequence: **the lower half's depth is INHERITED FROM THE COLUMN, never direct.** No
instrument has seen a model sample those bytes; what is established is the mode under which the page
they live in is read.

> **THE RULE THIS MINTS — and the kit must carry all three lines of it:**
> **DEPTH is a property of the PAGE. READERSHIP is a property of the UVs.**
> **A page's draw mode governs all 256 lines FOR A GIVEN DRAW** — on this hardware a page can be
> bound at one depth by one primitive and another by the next, so a page drawn twice at two depths is
> the **22-cell hazard class of §2**, not a contradiction.
> Collapsing the first two lines is what produced the `y = 384` blind spot. Dropping the third would
> license an unsound generalisation the first time someone quotes the law without §2.

**AND A DURABLE INSTRUMENT LAW, about tooling rather than about this rung.** A MIPS call's **delay
slot executes before the call**, so an argument can be produced there. **Any future
argument-recovery tool that reads the register file AT the `jalr` is silently wrong.** Measured on
the recovered idiom: **0 of 238** page-word arguments come from a delay slot, which is why both
disassemblers agreed — both handle it. ⚠ **The split, corrected — the earlier parenthetical said
"218 straight-line, 4 across a branch" and summed to 222, not 238.** `V1A-VERIFY.md` §3's actual
split of the same 238: **218** fold straight-line · **4** cross a branch · **16** are non-constant to
the refuter's folder, of which **12** close under the wider window (the two-window composition H9
gates, §9) and the remaining **4** are L1's genuinely runtime-computed sites, which the refuter's
folder independently also calls runtime. **218 + 4 + 12 + 4 = 238.** The flag-argument half of
the law (every one of the same 238 sites takes its flags *from* the delay slot, and ~12,360
argument slots corpus-wide are delay-slot-produced) is `V1A-VERIFY.md`'s and is **not** re-measured
here.

**AND A SECOND INSTRUMENT CONVENTION, recorded so no future lane re-derives a phantom
disagreement.** L2's pointer-table "median **16**" is `sorted[n//2]` — the 28th of 54 values — where
the true median of the same 54 is **15**. A *number convention*, not a data disagreement; the
quotable form is *"a median of 15–16 in-image code pointers"*. (*A4 §1 row 15.*)

---

# 2. THE ATTRIBUTION TABLE

Classes a refuter rated **REFUTED as stated** are **not in this table**; they are in §6, with the
word.

| # | class | cells | confidence | posture |
|---:|---|---:|---|---|
| **P1** | program texture-registration, strong dispatch chain (225 sites / 76 containers) | **181** | **CONFIRMED** — two independently written disassemblers agree on **238/238** call sites and **233/233** values; a third, prior source (the tier-R annotator, months earlier) records the same site count; **238/238** sites lie inside the reachability closure | DISCLOSE → edit behind an ack (§5) |
| **P2** | program texture-registration, corroborated tier (8 sites, 2 images) | **8** | **CONFIRMED — and the sweep UNDER-RATED it.** The refuter's whole-image base resolution rates them **8/8** genuine; ship the 233-hit variant, not the 225-hit one | same as P1 |
| **G1** | the container's own `so` records at PAGE granularity | **57** | **CONFIRMED as a measurement, DEFLATED as a reach.** 138/140 against the census — of which **122 rows compare an `so` record against itself**; **16/18** on the informative rows; **0 new columns opened** | **LICENSE**, behind the new spill-conflict guard — **56 build, 1 refuses** |
| | **total depth-resolved** | **246** | | |
| **H** | ★ **CLUT ARITY (`bpp_hint`)** — the container's **own id-0 payload header** `nClut4`/`nClut8` (`reskin.id0_palettes`), which W6b-1's census already called *"the one lawful narrowing"* and which **no lane in this round opened**, though every lane read the artifact carrying it | **0** attributed **·** **351** NARROWED (**286** toward 4bpp-or-15bpp · **65** toward the 8bpp family) | **A NARROWING, NOT AN ATTRIBUTION** — `hint = 4` means *"this container ships no 8-entry-per-byte CLUT, so this page is 4 bpp **or** 15 bpp"*. **It licenses no decode alone.** Calibrated **12/12** on cells whose depth **is** known — the field cannot calibrate itself, being populated only where the depth is unknown | **DISCLOSE ONLY — it attributes nothing and moves no total.** What it does do: **17 of the 246** attributed cells gain a **SECOND WITNESS** (**P 9 · G 8**; 15 exact, 2 compatible-15bpp), at **0** conflicts with either channel, and it breaks **0 of the 30** dual-depth ties — a clean negative, recorded so nobody tries |

**Calibration** — P **10/10** · G **138/140 overall, 16/18 informative** · cross-channel,
census-independent, **10/10** · H **12/12** on the cells whose depth is known.

⚠ **P's ground truth against the `so` census is N = 10, and it cannot be grown FROM THAT CENSUS**:
the program channel speaks precisely where the `so` census is quiet, so overlap is scarce **by
construction**. At page level the refuter measured it — of the **121** pages a program constant
names, **112 (92.6 %) carry no `so` record at all**; the critic found the same fact a second way,
**177 of the 189 gains sit in containers with zero `so` records**. That is the single largest caveat
on this rung and it is structural, not an oversight.

⛳ **RE-STATED, BECAUSE THE FLAT FORM — *"N = 10 and CANNOT BE GROWN"* — IS FALSIFIED.** Channel H is
a witness the `so` census is not, and at **cell** level P's corroborated set goes **10 → 19 (+90 %)**
for the cost of one join, with **0** conflicts. ⚠ **Scope it exactly: the 92.6 % is a *page*-level
figure, and the page-level restatement under channel H is one further join that NOBODY IN THIS ROUND
RAN.** Quote the cell-level number; do not re-derive a page one from it.

⛳ **AND ALMOST NO SHIPPED CELL HAS TWO WITNESSES — but 17 of the 246 DO, so the flat form of this
sentence is falsified too.** P and G are **exactly disjoint** on the gained set
(189 + 57 = 246, overlap **0**), so no cell rests on both of *those two* — but the earlier sentence
generalised that to *"no shipped cell has two witnesses"* and missed channel H, which corroborates
**17** of them (row H above) while attributing none. The cross-channel 10/10 agreement remains
evidence about the **instruments**, never about any cell being shipped.

### The refusals this rung MINTS — 32 cells, three classes, three different populations

| class | cells | population | why |
|---|---:|---|---|
| **program-derived MULTI-VALUED depth** | **22**, in 10 containers | **INSIDE the 2,385** — a **subset of the 861 residue**, not an addend | unanimity is the verdict rule; two values is a hazard, not a vote. Verified at data level that no majority is silently taken. **The census could not see this class at all.** |
| **channel-G MULTI-VALUED depth** | **8** | **INSIDE the 2,385**, disjoint from the 22 | ★ **named in NO lane dossier** — found by the calibration refuter. A lane building the refusal list from the sweep dossier alone would ship 8 cells unlisted. |
| **SPILL-vs-OWN-PAGE conflict** | **2** | ⚠ **OUTSIDE the 2,385 entirely** — these cells **had** a depth and now have **two** | both predicates true of the same bytes; genuinely dual-depth; **STAYS REFUSED**. ⚠ **It protects ZERO cells no existing hazard already refuses.** Non-vacuous as a **predicate**, adds nothing as **protection** — it exists to carry the **reason**. |

**Read the population column**: a reader of a flat residue table can double-count 24 cells.

### Named non-attributions (evidence recorded, zero cells claimed)

Runtime-computed page arguments **4** · refused dispatch **1** (independently the only site both
instruments rate weakest) · page words naming a column their container never uploads **5** ·
**37 textured-registration sites in 11 containers behind pointer tables** —
**[PLAUSIBLE — refusal correct in kind, gap under-stated]**: refused at a measured 39.3 % shape-hit
rate, i.e. chance, **but on an ANY-halfword predicate when the op is by its own name a LIST**, and
the structural tests were never tried. A weak predicate returning chance is not evidence that a
strong one would. **The recovered idiom covers 86.55 % of the textured-registration surface, not
100 %.** ⛳ **And this path is now COSTED — a ceiling of ≤ 119 cells, 5.0 % of the surface; the
container ids are named in §3 probe 2.**

---

# 3. THE NAMED RESIDUE — 2,139 cells, and why each is still unknown

The arithmetic closes exactly: **2,385 = 246 gained + 1,278 blind + 861 covered-but-uncovered.**
The two multi-valued classes above are *inside* these rows, not additional to them.

| residue | cells | why |
|---|---:|---|
| inside the 222 `so`-blind containers | **1,278** | their programs register nothing and draw nothing through the model API — **not a scanner shortfall**: 221 of the 222 make thousands of other resolved calls |
| in 135 model-BEARING containers the lever does not cover | **861** | the container has models, but no recovered page word and no `so` page covers these particular cells. **The sharpest warning in the corpus lives here: one container (`ef381`) has 73 GEOM blocks, 750 engine calls and 34 page-word-shaped immediates while making zero registration calls.** 189 is a FLOOR. |

⛳ **AND THE "why each is still unknown" COLUMN IS INCOMPLETE — the clause the two rows above do not
carry.** **334 of these 2,139 cells carry a CONTAINER-DECLARED NARROWING** (channel H, §2 row H:
`bpp_hint` from the container's own id-0 `nClut4`/`nClut8` arity — 351 in the 2,385 minus the 17 that
sit on already-attributed cells). They stay refused, because **a narrowing is not a depth** —
`hint = 4` still leaves 4 bpp or 15 bpp — but *"the container states nothing about this cell"* is
**false** for 334 of them, and the reason string should say which of the two it means.

**And a residue INSIDE the hand-off:** of the 246 depth-resolved cells, **199** clear every other
edit hazard under the per-cell map W6b-1 shipped and **79** under the census's stale rect addressing
(§6 row 3). The gap is **not** closed by more disassembly — it is attribution-blindness, program
writes and co-transform. **Depth is ONE gate of several.**

**Where the next probe belongs, in order — RE-SPECIFIED, because the previously ranked-first probe
was near-vacuous:**

1. **Cross-container VRAM CO-RESIDENCY.** ⚠ The obvious version of this — *"are the blind 222's pages
   consumed by a different container's program?"* — **joins over an 11-element page space and returns
   yes for 1,278 of 1,278 cells.** It discriminates nothing. The predicate that would is **which
   containers are simultaneously live in VRAM during one cast**, and that lives in the `.seq` /
   SFXRework cast graph, not in the page map. **Re-spec before spending a lane.**
   ⛳ **AND THIS IS ALSO WHERE W6b-1 §7.2 Q4 CLOSES, so the answer lives in the record it closes and
   not only in a gate's stdout:** `ef390`'s **10** writerless **15 bpp** bindings name page
   **(448, 256)**, a page `ef390` **never uploads** (it uploads columns 704 and 768 only). **The
   residual-VRAM hypothesis is the only survivor**, and the refusal is **permanent absent a
   co-residency probe** — the same probe this row re-specifies. (Re-measured by H13.)
2. **The one textured-registration path still dark** (37 sites, 11 containers) — fold the pointer and
   read the pointee as a **typed array**, not "any page-shaped halfword anywhere".
   ⛳ **COSTED — the earlier draft said "nobody can cost this follow-up because the sweep artifact
   does not record which containers they are". The ids were one join away from `v1a_scan.json`,
   which resolves every `jalr` to an op index:**

   ```
   op  19  Hi_RegisterTexListModel : 35 sites /  9 effects  {226, 231, 276, 297, 301, 381, 418, 435, 445}  ->  92 depth-unknown cells
   op 171  Hi_RegisterTexPtrModel  :  2 sites /  2 effects  {210, 508}                                     ->  27 depth-unknown cells
   UNION                           : 37 sites / 11 effects                                                 -> <= 119 cells = 5.0 % of 2,385
   ```

   **119 is a CEILING, not an estimate** — an op need not name every column of its container.
   ⚠ **RE-RANK BEFORE SPENDING A LANE:** a typed-pointee disassembly for **≤ 119** cells is **not
   obviously ahead of channel H's 351-for-a-join** (§2 row H), and it is barely twice channel G's
   **57 for free**. And note what the eleven contain: **`ef381`** — the 73-GEOM / 750-call warning
   container of the residue table above — and **`ef435`**, the canonical false positive of the flat
   scan (§6 row 8). Two of the eleven are already known to be hard for unrelated reasons.
3. The unnamed majority of the op surface, only if 1 and 2 fail.
4. ~~A corpus-wide store-level sweep~~ — **CLOSED this round** (§6 row 7).
5. ~~The id-4 model-package header, the census's third evidence class~~ — ⛳ **CLOSED FOREVER, as a
   NAMED REFUSAL rather than an untried option.** It covers **93** cells and they are **93/93
   creature-class, 0 scenery**. It is **structurally vacuous for the population this lever serves**
   and can never attribute a scenery cell. No future lane should spend on it. (Re-measured by H16.)

---

# 4. WHAT DID *NOT* CHANGE

* **No cell moved out of a WRITE refusal. Delta 0 in both directions** — now on two instruments that
  share no scan code, agreeing at **site level on 77 of 77** candidates, plus a blind control (20
  containers the sweep called clean, re-scanned in isolation → **0** candidates).
  ⚠ **With one clause, now on the record instead of only in SCRATCH:** the scan finds **13** read
  ids and the shipped list has **12** — one container both writes and reads, and is classified as a
  WRITER because the kit tests WRITE first. "Delta 0 in both directions" is true **only** with that
  clause.
* The by-cell hard refusals re-derive unchanged.
* The 113 `read-storeimage` DISCLOSE cells stay disclosed — now on an **engine-grounded** direction
  law instead of an inherited name (§6 row 10).
* **The falsified coherence probe stays dead.** Nothing here is a statistical inference about byte
  contents; every number is a recovered constant or a container's own record.
* `w6b_gates.py` still passes **7/7**, re-run unchanged.

---

# 5. ★ THE KIT POSTURE RECOMMENDATION

**The refusal's own words:** *"the container declares no model that samples the cell, so its bit
depth is not a fact it states."*

**The case for licensing an edit.** A constant page word folded out of the container's own id-3
program **is** the container stating the depth — those bits **are** the GPU draw mode. It is not an
inference about the bytes; it is the machine's own declaration of how they will be read. And it is
recovered by two independently written disassemblers agreeing to the site and to the value, in a call
whose **sibling arguments score 0.0 %** on the same predicates. **This is a categorically different
object from the probe that was falsified at 54.5 %**, which guessed a depth from the bytes' own
statistics and lost a 3-way choice. The distinction is not rhetorical: one is a *recovered constant*,
the other was an *inference over content*. **A refusal with a name beats a guess — but a recovered
constant is not a guess.**

**The case against — for channel P.**

1. **REGISTRATION IS NOT A DRAW.** W6b-1 minted `BINDING-IS-NOT-A-DRAW` at the cost of two negative
   playtests: an `so` record proves a model *can* sample a cell, never that it is drawn or visible.
   A texture registration is the **same shape of evidence one layer up** — it proves a texture was
   registered onto a model at depth D, not that the model is drawn, nor that this cell's bytes are
   what the visible surface samples. **The generalisation from "binding" to "registration" is itself
   untested in-game**, and this rung is entirely offline.
2. **92.6 % of channel P's output has no second source at PAGE level**, and that sample cannot be
   grown *from the `so` census* — it is scarce by construction, not by neglect. ⛳ **Re-stated
   against channel H (§2 row H):** at **cell** level the corroborated set does move, **10 → 19** at
   **0** conflicts. It does **not** move this page-level figure, because the page-level join was
   never run. The case against P survives; the flat *"cannot be grown"* does not.
3. **The evidence is COLUMN-granular** (§1) — the lower half's depth is inherited, never direct.
4. **The 22-cell multi-valued residue is a hazard class the census could not see.** Licensing P
   without shipping that refusal would hand authors a depth the container names twice. The refuter
   then found **8 more** the sweep had not named at all — evidence that this class is still being
   discovered, which is itself an argument against granting P edit authority this rung.
5. **★ THE DECISIVE PRECEDENT IS THE KIT'S OWN.** `expect_bpp` (W6b-1 §3.1 item 4) is **stated by
   the author and CHECKED against the derivation — never chosen.** The kit already declines to
   *choose* a depth in the case where its evidence is strongest. A weaker channel cannot be granted
   a stronger authority. *A law in a docstring is a wish; a rule not enforced at the call site is not
   enforced.*

**And the case FOR licensing channel G, which is a different case entirely.** G is **not new
evidence**. It is the *correct reading of evidence the kit already ships on* — the same `so` record,
at the granularity the hardware uses. Calling it an inference would mean the kit's existing depth
source has been an inference all along. Its refuter deflated its **reach** (0 new columns) and
**circularity-checked its calibration** (122 of 140 rows are an identity) — but neither finding
touches its *kind*: on the **18 informative rows it is 16/18**, and the two failures are the
spill-conflict class it must refuse anyway. Notably the single row in the entire calibration that
rests on a **genuinely independent witness** — a depth the census read out of the model-package
header, from a source channel G does not consult — **agrees**.

⚠ **AND THAT ROW'S OWN LIMIT, NAMED — it is evidence about the INSTRUMENT, not from the population
the lever serves.** `ef179.x320_y384`, called above the strongest row in the table, is itself
**creature-class**, and the id-4 model-package header it rests on is **93/93 creature-class, 0
scenery** (§3 probe 5). Creature cells are precisely the population this rung's attribution excludes
**by rule**. The row still shows channel G agreeing with a witness it does not consult — that is
real, and it is about the *instrument*. It is **not** a scenery datum, and the calibration's
strongest independent row therefore cannot be quoted as one.

> ## THE LINE
> **CHANNEL G LICENSES. CHANNEL P DISCLOSES, and edits only behind an explicit acknowledgement.**
>
> * **Channel G (57 cells) — LICENSE.** The same record, read at the hardware's granularity.
>   **Guard:** the spill-vs-own-page conflict refuses first, and **one of the 57 refuses anyway on a
>   program write** (§7 row 7).
> * **Channel P (189 cells) — DISCLOSE by default.** The refusal reason gains the evidence ("no `so`
>   reader samples this cell; the container's own program registers this page at N bpp at *k* call
>   sites"). An edit unlocks only with `acknowledge_program_derived_depth = true` **AND** an
>   author-stated `expect_bpp` that **matches** the derived depth — the
>   `acknowledge_texanim_frames` / `acknowledge_cutout_reshape` shape exactly.
>   **The author carries the judgement; the kit carries the check.**
>
> **The upgrade path is named, not left implicit:** channel P earns LICENSE when a cast proves a
> program-derived depth on screen (§8), or when a second independent channel corroborates more than
> 7.4 % of its pages. ⚠ **Channel H is that second channel and it has NOT triggered this clause:**
> it corroborates **9** of P's **cells** at 0 conflicts (§2 row H), but the clause is written at
> **PAGE** level and the page-level join was never run. Do not read a cell-level gain as satisfying
> a page-level threshold.

---

# 6. SHARPENINGS — where a lane and its refuter disagreed, both predicates named

Each row carries **the refuter's own verdict word — where a refuter produced one.** ⚠ **Two rows had
no refuter at all** and are labelled `SELF-MEASURED, UNREFUTED` in their verdict cell: **row 7** (the
corpus-wide store-level sweep, written into `w6b2_gates.py` *after* all three refuter lanes had
closed) and **row 8** (whose adjudication is this synthesis's own reading of a lane artifact). Their
verdict words are **self-authored**, and that is said here in those words rather than left to be
inferred. **Row 11 prints both words**, because the record's reading is harsher than its refuter's.
Full reconciliation: *A4 §1* (24 rows).

| # | claim as recorded | as re-measured | verdict |
|---:|---|---|---|
| 1 | **channel G disagrees with the census on 2 cells** | on both cells **every** census reader is a binding on the **neighbouring** page whose u range crosses the column boundary, while the cell's own page is named at the other depth | **BOTH PREDICATES TRUE — the SPILL-vs-OWN-PAGE class.** *"A model whose UVs land here reads at N"* and *"this cell's page draws at M"* are different questions. Not an error in either instrument; **genuinely dual-depth, must stay refused.** Silently picking one number would have manufactured a false certainty. |
| 2 | **the sweep's calibration: "declared column 97.8 % vs the runner-up's 53 % = chance"** | the refuter measured the null four ways. Sibling arguments of the *same call* **0.0 %**; ambient small constants **0.349** given shaped; **permutation null — the sweep's own value multiset with container pairing broken — 0.856** (p = 0.005) | **[REFUTED AS STATED] · CONCLUSION SURVIVES.** The conditional null is **85.6 %**, not ~50 %, so declared-column carries ~12 points, not ~45. The load is carried by the **shape predicate at 225/225 against an ambient 22.8 %** plus the **0.0 % sibling control**. ⚠ And the **runner-up rejection is STRONGER than the sweep realised**: 53 % is *below* the 85.6 % null — worse than chance for a real page word. |
| 3 | **"246 cells can be handed to the texel edit lane"** | re-scored against every other census hazard. **FOUR predicates, all measured:** **246** gain a depth · **199** clear every other edit hazard under the per-cell map W6b-1 shipped · **79** under the census's **pre-W6b-1 rect** addressing — the refuter's number · **10** if "no `so` reader" is also allowed to disqualify | **[REFUTED AS STATED] · RIGHT IN KIND, OVERSTATED IN DEGREE.** The refuter counted the lower-half flag (138 of the 246) as disqualifying — but that flag records what the **pre-W6b-1** rect key could name, and the per-cell map **shipped in W6b-1 for exactly those cells**. **Asked directly for the first time: the shipped map names 93/93 of them, and the DOME is a real key.** The strict 10 is **circular**. **The measurement stands under every predicate; only the framing moved.** ⚠ **And the census's `addressable_via` field is STALE** — which is why one instrument scored 79 and another 199, and it will keep regenerating the dispute until a census refresh re-stamps it. |
| 4 | **the sweep ships its conservative 225-hit variant as the headline** | the refuter resolves the dispatch parent across the **whole image** and finds the demoted tier **8/8** genuine | **SHIP THE FULL 233, NOT 225** — the conservative variant costs 8 real sites for no gain in soundness. **8 cells rest solely on that tier**, re-measured. Any downstream claim must name which variant it used. |
| 5 | **the sweep's dossier prose on which sites make up its corroborated tier** | its own JSON says otherwise — different effects, different image count, and the effect the prose calls corroborated is the **refused** one | **DOCUMENTATION DEFECT — data right, prose wrong.** The count is correct; the sentence telling a reader *which sites to hand-check* is not. |
| 6 | **"the idiom was ranked blind, not asserted"** | the mechanism *is* blind and two refuters reproduce the winner with their own scorers (one finds it the **only pair of 100** to reach declared-column ≥ 0.9) — **but** the same value histogram was already published in the annotator table the sweep opens for op names, **and the artifact keeps only the survivors**, so ~666 scored-and-dropped pairs are invisible to an auditor | **[PLAUSIBLE — framing overstated.]** Independent in code, a rediscovery in fact. ⛳ Concrete casualty now closed: the draw op W6b-1 §7.2 Q1 named **by name** *was* ranked and lost (page-Y bit set on 0 of its sites, declared column on 0, score 0.25) — **checked and negative**, and no dossier had said so. |
| 7 | **"no primitive-level draw-mode store exists" — with the sweep's own caveat that this was "searched and not found ON THE RECON IMAGES, not absent corpus-wide"** | ⛳ **the corpus-wide store-level sweep has now been RUN** (nobody had): every halfword and word store in every id-3 program, const-folded, scored on the same two predicates, **against its own ambient null in the same pass** | **[SELF-MEASURED, UNREFUTED]** — ⚠ **this row has NO refuter and its verdict word is the synthesis lane's own about the synthesis lane's own measurement.** H14 landed after V1a, V1b and V2 had all closed, so nothing external has tested it; the ambient-null-in-the-same-pass construction is what makes it the strongest *self*-check in the round, and that is not the same thing. **CONFIRMED, SCOPE UPGRADED — CLEAN NEGATIVE.** Stores carry page-shaped constants at **less than half the ambient rate**, and their declared-column rate sits **at** the ambient rate; the recovered idiom scores **1.000 / 0.973** on the same predicates and the positive control is **233/233**. ⚠ **SCOPE, NAMED:** the folder resolves 31 % of stores; the rest are runtime-computed and this instrument states nothing about them. The claim earned is *"no const-foldable store carries a page word, corpus-wide"* — an upgrade on "not found on the recon images", **not** a proof that no store ever does. |
| 8 | **a flat call-shape scan disagrees with the sweep on 18 containers** — the disagreement list is **DATA**, read from `v1b_audit.json` block **A5** in SCRATCH, **not a refuter's verdict**: the artifact contains rows and no verdict word, and the script that produced it was disclaimed by every lane and is **not in the committable surface** (see PROVENANCE) | **every row adjudicated from primary data — 0 unexplained** (the "extra" values are not registration arguments at all under an independent per-site scan; the "missing" are undeclared-column words its own filter drops, and the wide-window register shape another refuter closed) | **[SELF-MEASURED, UNREFUTED]** — ⚠ **the adjudication below is the synthesis's own word about a data block, not a refuter's verdict; A5 states no verdict.** **THE FLAT SCAN IS THE WEAKER INSTRUMENT ON THIS PREDICATE. THE SWEEP STANDS.** ⚠ **And the block delivers a corroboration the sweep could not:** across the 295 containers the sweep reports zero hits for (73 of them *with* models), the reachability-free scan nominates a candidate in **0**. |
| 9 | **`w6b_gates` G6's printed "linear write set" vs the shipped refusal list** | the omission is confined to **one printed intermediate**; G6's actual derivation **does** include the texanim arm and **does** assert equality with the shipped set | **TWO PREDICATES, ONE CORPUS, NO CONTRADICTION** — the sweep's literal wording is true and its framing overstated. Both are printed by the gate so anyone diffing them knows why. ⚠ **Separately, G6's own prose has a small defect** (it says a shape is absent when what is absent is that shape's *call form*). **NOT fixed here — that file is read-only to this round.** |
| 10 | **"the engine's own stub arities corroborate which transfer op is the READ"** | the two ops are **the same arity and the same argument kinds** and both touch the same callback — **the arities cannot discriminate them**; the stated corroboration was vacuous | **THE ASSIGNMENT WAS UNVERIFIED AND LOAD-BEARING; NOW SETTLED, AND THE SHIPPED READING IS CORRECT.** Grounded end to end and read-only: op index → **the interpreter's own dispatch table** (whose extent matches the op space exactly) → native fn → callback code → the engine's handler. ⚠ **The counter-argument nearly won and is recorded:** by population the readback op has 15 real sites and the upload op 1, which on this hardware looks backwards — beaten by the handler names, because **programs do not upload; the loader does**. Had population beaten the engine, the direction law would have inverted and 113 cells **including W6b-1's cast vehicle** would have been re-refused. ⚠ **AND A DEAD-CODE TRAP THAT ALREADY BIT ONE INSTRUMENT IN THIS VERY ROUND, carried out of SCRATCH so the next lane does not re-derive the law from a branch that never runs:** `SFX.cs`'s **`DebugRoomCallback` cases 100/101/102 are DEAD CODE** — it is called with an already-shifted code and shifts again. **The live path is `BattleCallback`**, which is what the write lane cited. A mid-round audit read the dead branch as *independent corroboration* of the direction law; it is not corroboration of anything. Both observations are true and the lanes agree on the answer — one site simply never executes. (*A4 §1 row 20; a source reading, not a corpus measurement, so it is not gated.*) |
| 11 | **"channel G calibrates at 138/140"** | the refuter classified the ground-truth rows by whether the census's reader records and the page-owning records are the **same set**: **122 are TAUTOLOGICAL** — an `so` record compared against itself | **[MIXED (V1b) / REFUTED AS STATED (this record's reading)]** — ⚠ **both words printed, because they differ:** the string `REFUTED` appears **0** times in `V1B-VERIFY.md`; its verdict table's word for this row is **MIXED** and its prose says two claims *"must be **RESTATED**"*. This record is **harsher** than its refuter, not softer, so nothing is hidden — but the harsher word is **ours**. · **BOTH PREDICATES MUST BE PRINTED.** *"138/140 = 0.9857"* — true. *"16/18 on the informative rows"* — also true, and it is the number that carries evidence. ⚠ **Both genuinely disjoint rows disagree**: every row that *could* have falsified the page predicate **did**, and both are the spill class. ⚠ One further sharpening this record adds: the refuter's "16 partial" includes a row with **no `so` reader at all**, whose census depth comes from an entirely different source — **the strongest row in the table, not a partial one**, and it agrees. Both splits give the same informative agreement. |
| 12 | **"the write list is hardened by four instruments"** (this record's own previous draft) | those four were the write lane's **four internal instruments**, not four lanes. **Nothing had refuted it** | **THE GAP WAS REAL AND IS NOW CLOSED.** An independent instrument sharing no scan code agrees at **site level on 77 of 77**, reproduces both shipped id sets exactly, adds a blind control, **replaces the lookback SWEEP with a window-FREE proof** that no site can hide, and **downgrades one of its own discriminators** on finding it fires on 6 of the 23 real sites. |

---

# 7. WHAT W6b-2 PROPER SHOULD IMPLEMENT AND GATE

Every proposed gate below was **run against the corpus before being proposed** (`w6b2_gates.py` H11–
H13). Row 7 is here in its corrected form: **as first drafted it would have failed on day one.**

| # | deliverable | its gate |
|---:|---|---|
| 1 | **a PAGE-granular depth view** in `reskin`, beside the UV reader view — never merged | the two agree on every cell a reader's UVs touch: **138/140**, **16/18 on the informative rows**, and the **2** exceptions are FLAGGED, not reconciled |
| 2 | **the SPILL-vs-OWN-PAGE conflict hazard** — a REFUSAL | ⚠ **state it plainly: it adds 0 cells to the refused set as PROTECTION** (both already refuse on other hazards). It is non-vacuous as a **predicate** and exists to carry the **reason**. A gate asserting it protects ≥ 1 new cell would fail. |
| 3 | **the PROGRAM-DUAL-DEPTH hazard** — a REFUSAL | 22 cells in 10 containers, re-derived per run |
| 4 | **★ the CHANNEL-G-DUAL-DEPTH hazard** — a REFUSAL nobody had named | **8 cells**, listed by name; the two ambiguous sets are **disjoint**, so the true refused set is **32**, not 24 |
| 5 | **the program-derived depth table as a corpus constant, WITH A RE-DERIVATION PIN** | the `w6b_gates` G6 precedent: **a constant that caches a measurement must be re-measured somewhere**, because a disassembly walk cannot run per build |
| 6 | **the depth-unknown refusal reason gains the derived evidence** (DISCLOSE) | the refusal matrix names the new string |
| 7 | **`acknowledge_program_derived_depth` + a MANDATORY matching `expect_bpp`** | an ack without a matching `expect_bpp` must FAIL by name; a mismatching one must FAIL by name |
| 8 | **channel G adopted as a depth SOURCE**, not merely a disclosure | ⚠ **CORRECTED: 57 gain a depth; 56 clear every other hazard; 1 refuses on a program write.** *(As originally drafted — "the 57 cells build" — this gate fails.)* **55 of the 57 are lower halves, buildable ONLY through the per-cell map**, so this deliverable also depends on row 9. ⛳ **CORRECTED AGAIN IN §10: the 56 was CLASS-C-BLIND — the honest split is 49 clean + 7 class-C + 1 program-write.** |
| 9 | **re-stamp the census's `addressable_via` field** | it still asserts "UNADDRESSABLE" for cells the shipped per-cell map names — measured: the map names **93/93** of the program-gained lower halves. **A stale flag that contradicts the kit is how the 79-vs-199 dispute regenerates.** ⚠ **TWO PREDICATES ON THE SAME CELLS, BOTH PRINTED so a future reader does not read a contradiction:** **93** = *all* program-gained `y = 384` cells (this record's number, and the one the map is asked about); **83** = the subset that *carries the census's stale `hz_unaddressable_lower_half` flag* (a mid-round audit's number). **83 + 55 channel-G = 138**, the `y = 384` hazard total quoted in §6 row 3. Nothing in the checkout printed both until now. |
| 10 | **2,139 cells keep refusing by name**, with the residue split in the reason string | the census gate re-measures the split and its arithmetic closure |

---

# 8. ★ THE NEXT-CAST RECOMMENDATION

**First, a correction to this rung's own framing.** The question as posed to the recon was *"does any
newly-attributed cell give the photographable-SHAPE verdict a flat-UV vehicle?"* — **that verdict is
no longer open.** W6b-1's cast **1f** closed it: the pool wheels rendered, **THE PHOTOGRAPHABLE SHAPE
VERDICT ON SCENERY IS YES**, and the pool cell is positively identified. The pool candidates this
rung was asked about are unaffected and need nothing from it.

**So the honest answer to the question asked is: NO, and it does not matter.**

## 8.1 Why no newly-attributed cell could have been that vehicle anyway

Every newly-attributed cell is **by construction** one that no `so` record samples (or one whose
readers spill in from elsewhere). **No reader ⇒ no declared UVs ⇒ flatness cannot be checked
offline** — and W6b-1 minted exactly that offline flatness screen as the instrument for choosing a
shape-bearing surface. Staking a shape verdict on a newly-attributed cell would have thrown away the
screen. Measured on the anchor: the DOME has **0 readers**.

## 8.2 What this rung DOES mint — the cast that tests the LEVER, not the codec

```
THE DOME   (ef211's lower-half dome cell)
  depth        8bpp  -- channel G, from the container's own binding on the column's page
  writer       single (the lower half of the tall rect whose UPPER half was W6b-1's cast-1 cell)
  readers      0     -- which is exactly why the census had to refuse it
  hazards      dual-depth NO . co-transform NO . multi-palette NO . shared-read NO
               spill-in NO . attribution-blind NO . program-write NO
  program      a READ.  Disclose, do not refuse.
  addressable  ONLY through the per-cell map W6b-1 shipped
  ON SCREEN    PROVEN -- the cast ladder's stripes banded the rolling-fire dome through this cell
```

It is **the only cell in the corpus that is simultaneously depth-attributed by this rung, proven
drawn in-game, and free of every other hazard.**

~~⚠ **AND ITS DEPTH IS STILL UNTESTED IN-GAME**~~ ⛳ **RETIRED — the depth-bearing edit ran and
the depth HELD (§10.1: clean bands, no pin-striping, no wrong-solid).** The paragraph below is the
pre-cast reasoning, kept because its logic is why the cast was decisive: the cell probe that proved
the dome is drawn **zero-writes**, and zero-writing is **depth-invariant** — a zeroed texel is the
absence of ink at 4bpp, 8bpp and 15bpp alike. So the ladder's evidence that this cell is live art
said **nothing** about its depth, there was **no** second depth datum to reconcile with channel G's
8 bpp, and a depth-BEARING edit was the first possible test of **REGISTRATION-IS-A-DRAW-ENOUGH**
on a surface already shown to reach the screen. It passed.

## 8.3 The recommended sequence

| | cast | vehicle | proves | figure |
|---|---|---|---|---|
| **A** | the **15 bpp** cast already staged | the staged 15bpp vehicle (no bench row exists yet — that is its cost) | the last unproven **CODEC** | per that lane's own screen |
| **B** | **new, this rung** | THE DOME — 8 bpp | ⛳ the **ATTRIBUTION** verdict: a depth that exists only because the container's own record was re-read at page granularity, on a cell the census called depth-unknown | **translation-invariant ONLY** (stripes/bands — the one figure class proven to read on this exact surface). **Do not attempt a shape here**: this cell has no declared UVs, so the offline flatness screen cannot clear it. |

**B is nearly free**: same container, **bench 30301, ability row 198**, the same deploy script, no
relaunch, no new bench row. Ship A and B as **separate artifacts** — B's whole value is that its
depth came from the new channel, and composing it with anything else makes the read ambiguous (the
same argument W6b-1 §5.2 used to refuse composing the earlier recolour).

⚠ **Preflight is unchanged and non-negotiable** (W6b-1 §5.5): verify the SFX-hybrid switch is off; no
mod-file list omitting the vehicle container; a first-deploy snapshot per root; the SFX probe armed
**and its log archived to SCRATCH the same session**; re-read the live container sha and confirm the
stock baseline. **The install is shared mutable state and many sessions run concurrently — a campaign
deploy wiped a probe mid-ladder once already.**

---

# 9. GATES, SUITES, AND THE RECON'S OWN RESIDUE

`py w6b2_gates.py` — **17/17**, corpus + the SCRATCH lane artifacts only (no install read, no deploy,
no install write, no git commit):

| gate | what it proves |
|---|---|
| **H0** | **CALIBRATE BEFORE JUDGING** — this rung's own page-word decoder against the kit's over all 512 words, then **two known answers re-found first** before anything is believed |
| **H1** | the population, and the 17-cell gap between "depth unknown" and "no depth recorded" **accounted for** as the dual-depth class rather than rounded away; **plus the residue arithmetic and the surface percentage printed rather than quoted** (2,385 − 246 = 2,139; 92.7 %) |
| **H2** | **channel P re-rolled from the RAW hits** — the sweep's per-cell rollup deliberately **not** read; **plus the 97.8 % calibration headline (220/225) and the 92.6 % page-level caveat (112 of 121) re-derived here rather than quoted** |
| **H3** | **channel G re-read from the 372 containers**; the 189 / 57 / 246 headline computed here |
| **H4** | the calibration table, with **every disagreement adjudicated by name** as spill-vs-own-page |
| **H5** | the structural ceiling, its **arithmetic closure**, and a **third instrument's** corroboration |
| **H6** | **THE FIRST TWO REFUTERS' CHECKS REPRODUCED, not restated** — the hand-off re-scored under all four predicates, the 18-row disagreement list explained to **0 unexplained** |
| **H7** | the write delta — the adjudicated site list **re-summed into id sets here**; the G6 predicate disagreement printed, not reconciled away |
| **H8** | provenance — byte constants, integer sequences and hex runs over **every new file `git status` reports** (not a hand-written list, because the surface moves mid-round), one literal **adjudicated benign by name** |
| **H9** | ★ the **238/238 · 233/233** claim — the sentence that makes channel P a recovered constant — gated at last, **including the two-window composition its prose elided**, the delay-slot law, and the calibration **REFUTED as stated** with the controls that carry the load instead |
| **H10** | ★ channel G's calibration re-derived and shown **87 % tautological**; its 57 cells open **0 new columns**; **P ∩ G = 0**, so every shipped cell rests on one channel |
| **H11** | ★ the refused set is **32, not 24** — the 8 unnamed cells named — and the residue's three populations annotated so nobody adds them up |
| **H12** | ★ the build list's own gates **pre-tested**, catching one that would have failed on day one; and the assumption under the 79-vs-199 dispute finally **put to `reskin` itself** |
| **H13** | ★ the next probe **costed before the budget is committed**; two of W6b-1's open questions closed in passing; **and the ranked-#2 dark path costed at ≤ 119 cells** (op 19 = 35 sites / 9 effects → 92 cells, op 171 = 2 / 2 → 27, union 37 sites / 11 effects = 5.0 % of the surface), with the 39.3 % refusal rate and `ef381`'s 750 engine calls re-measured |
| **H14** | ★ **the store-level sweep the sweep lane's own caveat named and nobody ran**, with its own ambient null and its own positive control |
| **H15** | ★ the write lane's refuter reproduced at **site level**, the read-list subtraction put on the record, and the op-index → native-fn link closed |
| **H16** | ★ **CHANNEL H — the CLUT-arity narrowing that sat in the primary artifact all round and that NO lane opened**: 351 cells (286 / 65), calibrated **12/12** where the depth *is* known, **17** second witnesses on the shipped 246 at **0** conflicts, **0 of 30** dual-depth ties broken, **334** hint-carrying cells inside the residue — and the id-4 header channel **closed** at 93/93 creature-class |

`py w6b_gates.py` — **7/7**, re-run unchanged. Nothing this round should have touched it, so a
failure there would have been a finding, not something to fix quietly.

## ⚠ THE RECON'S OWN NAMED RESIDUE

* **Nothing here is in-game.** `REGISTRATION-IS-NOT-A-DRAW` is still an untested *generalisation* of
  a law that cost two playtests. §8's cast B is the experiment that would test it.
* **92.6 % of channel P's output has no second source AT PAGE LEVEL**, and that page-level sample
  cannot be grown from the `so` census. ⛳ At **cell** level channel H moves it **10 → 19**; **the
  page-level restatement under channel H was never computed** — by anyone, this round.
* **Channel H is a NARROWING and is proposed as nothing more.** `hint = 4` means "4 or 15". Anyone
  promoting it past disclosure must first measure how many of the **351** sit in containers that draw
  15 bpp at all — that measurement does not exist.
* **The pointer-table registration refusal rests on a weak predicate** (39.3 % on an ANY-halfword
  test). ⛳ Its follow-up **is** now costed — ≤ 119 cells, §3 probe 2 — so the earlier residue line
  *"its artifact cannot cost its own follow-up"* is retired.
* **The store sweep covers const-foldable stores only** — 31 % of that surface — **and it has no
  refuter** (§6 row 7).
* **Two of the four textured-registration ops were never disassembled at all.**
* **A shared gate's prose defect and a stale census field are both left in place** (§6 rows 9 and 3):
  those files are read-only to this round, and §7 row 9 carries the fix into the build list.

---

# 10. THE INTEGRATION ROUND — W6b-2 PROPER, SHIPPED

> Implemented as a 7-agent round (implement + the census re-stamp → three adversarial review lenses
> → fix → verify): **11 confirmed findings (1 critical, 4 major), all fixed, none skipped.** Gates:
> **`w6b2i_gates.py` I0–I10, 11/11** — every §7 gate implemented as stated, plus its own calibration
> (I0 re-finds THE DOME with an independent roll before believing the shipped view) and provenance
> rungs. Siblings green and BYTE-UNTOUCHED: w6b2 17/17 · w6b 7/7 · w6q 20/20 · w4 8/8. Kit summon
> suites green (one pre-existing failure in the behavior-compiler subsystem, unrelated, spun off).

**What shipped, mapped to §7:**

- **`ff9mapkit/ff9mapkit/summons/depth_attribution.py`** — the cached channel-P table at CELL
  granularity, **221 rows = 199 unanimous + 22 dual** (the 10 extra unanimous rows are P's own
  census ground truth, import-asserted as `GAIN_PROGRAM + 10` so they can never read as gains);
  count pins assert at IMPORT so a truncated table fails loudly; **I2 re-derives the whole table
  from `tpage_sweep.json` + the corpus and asserts EQUALITY** (row 5's pin, the G6 precedent).
  Channels G, H and the spill conflict are **DERIVED LIVE** from the container's own records — only
  the disassembly is cached, because only the disassembly cannot run per build.
- **THE CHANNEL SET** — the one design decision §7 left open, and what keeps the read-only sibling
  pins (w6b G6, w6q G1/G16) green without touching them: `repaint.CENSUS_CHANNELS = ('so-uv',)` is
  `scenery_surface`'s default — **W6b-1 byte-for-byte, refusal REASON TEXT included** (a channel a
  caller does not consult states neither depths NOR refusals; I5 asserts the census view names none
  of the three new classes). `repaint.LICENSED_CHANNELS = ('so-uv', 'so-page', 'program')` is the
  default of every author-facing path (`scenery_texel_pages` / `texel_page` / `export_art` /
  `build`). ⚠ `'program'` in the set means **CONSULTED** (disclosure + the dual refusal), never
  ADOPTED — emission additionally requires the ack. The default-on adoption deltas were MEASURED
  before being backed out, so a future re-pinning round inherits numbers, not guesses.
- **The refusals:** `program-dual-depth` (22 / 10 containers) · `channel-g-dual-depth` (8) ·
  `spill-vs-own-page` (2 — I4 proves it protects EXACTLY ZERO new cells by COUNTERFACTUAL, re-running
  `export_art`'s filter with the class added to the blocking set, not by an identity that could never
  fail) · **`program-depth-no-palette` — minted IN REVIEW, absent from this record's own §7** (see
  correction 2). Precedence: reader → G-dual → P-dual → G adopt → P adopt (ack) → depth-unknown;
  hazards outrank adoption, and the disjointness that makes the order a statement rather than a
  tie-break is asserted, not assumed.
- **The ack ladder** (`acknowledge_program_derived_depth`, LITERAL boolean + a mandatory MATCHING
  `expect_bpp`): every rung fails BY NAME — no ack / string-`'true'` / ack without `expect_bpp` /
  mismatch / a dual cell outranks the ack (I7, plus kit tests on synthetic containers).
- **The in-game caveats are CALL-SITED CONSTANTS, not prose**: `REGISTRATION_CAVEAT` (the upgrade
  path's first trigger FIRED AND FAILED — ef251, tpage 312, 15 bpp claimed, drawn as the 4-cycle
  bumper strip of a 4 bpp read), `DEPTH_COROLLARY` (ef446 — a stated depth is a BINDING-side fact),
  `INHERITED_LINE` — gated on **the COLUMN (`y % 256`), never the writer rect** (10 id-9 alternate
  blocks sit at y = 384 with `lower_half == False` and inherited depth; a reviewer caught the
  conflation live, on shipped output). I6 asserts all 189 disclosed reasons carry them.
- **`W6B_REASON` states BOTH depth-unknown populations** with the closing arithmetic — 2,298 refuse
  by name on the edit surface (189 of them DISCLOSING), 2,139 have no depth on any channel
  (1,278 + 861) — and I9 regex-extracts and re-measures both numbers; no substring pins.
- **The census re-stamp landed** (`w6b2_census_restamp.py`, idempotent, backup kept): 1,179 cells;
  both row-9 predicates printed and re-derived — **93** map-named program-gained lower halves (10 of
  them id-9 alternate blocks, resolved through the writer's `cls`, which is why a naive tag join
  under-reports 83/93) / **83** stale-flagged / 83 + 55 = 138 against H6/H12's own pins.

## ★ THE TWO CORRECTIONS THE REVIEW FORCES ON THIS RECORD'S OWN NUMBERS

1. **§7 row 8's "56 build / 1 refuses" was CLASS-C-BLIND.** The kit's `palette_cells` came from
   READERS only, so a readerless channel-G cell could never carry the multi-palette hazard — **7 of
   the 57 sit on columns bound with 2–3 distinct CLUTs** (ef179 · ef211 (640,384) · ef226 · ef390 ·
   ef447 with THREE · ef498 · ef510) and would have silently shipped one rendering of several: the
   kit LESS honest on the new licensed path than W6b-1 was on the old one, on identical evidence,
   visible INSIDE one column of ef211. Fixed at the same granularity as the depth — class-C evidence
   now comes from the COLUMN's binders where readers are absent; the alternates are named and
   exported. **The honest row-8 split: 49 clean + 7 class-C (DISCLOSED, not refused — the
   display-palette rule) + 1 program-write.**
2. **THE ACK'S REAL SURFACE IS 55 CELLS, NOT 189.** Channel P states a DEPTH AND NOTHING ELSE — it
   names no CLUT. An INDEXED (4/8 bpp) P cell therefore has **no key to render against, and no
   combination of acknowledgement keys reaches it**: of the 189, **134 are indexed** (102 refuse as
   `program-depth-no-palette`; 32 refuse first on program-VRAM verdicts) and **the ack reaches the
   55 direct 15 bpp cells, 43 of which carry no refusal at all**. As first implemented the refusal
   handed those authors a READER-shaped message formatting `None`/`0` as measurements, and the
   disclosure promised a remedy 134 cells cannot use — both lenses' top finding. The disclosure now
   offers the ack ONLY where it can work and says plainly why it cannot elsewhere. (§5's posture
   survives untouched: this narrows the ack's REACH, not its terms.)

~~**Still true, and now said in the shipped docstrings: NOTHING HERE IS IN-GAME.**~~
⛳ **RETIRED SAME-DAY — §10.1: THE DOME CAST RAN AND PASSED.**

## 10.1 ★★ THE DOME CAST — the attribution verdict, ON SCREEN

§8.2's experiment ran through the shipped licensed lane itself, same day as the integration:
**`phoenix_dome.toml`** (stock ef211 + four 12-row max-luminance bands into `cell.s0.x704_y384`,
6,112 bytes, generator **`dome_band_stamp.py`** — ink index 255 derived from the display palette,
**24 cutout texels SKIPPED** so THE CUTOUT LAW needed no acknowledgement and the silhouette stayed
a non-variable; the law FIRED on the first draft that inked them, which is the refusal doing its
job). Shipped as a SEPARATE artifact per §8.3 — the resident pool wheel stepped aside and its
absence was the control. **The row carried ZERO acknowledgement keys**: `expect_bpp = 8` stated
and checked against the channel-G derivation, nothing else — the LICENSE posture, live.

**Verdict (owner, bench 30301 row 198): "bright yellow bands. fits the fire really well" —
CLEAN bands, no 4bpp pin-striping, no 15bpp wrong-solid.** The self-diagnosing figure key ran in
reverse for once: the depth HELD.

**Scope, stated exactly:** this is the EXISTENCE PROOF — one cell, one cast. A channel-G depth on
a proven-drawn, readerless surface governed the actual draw: **REGISTRATION-IS-A-DRAW-ENOUGH is
TRUE of channel G's flagship**, where channel P's counterpart claim was refuted on its first trial
(ef251). It does not blanket-prove the other 56 G cells, and it does not repeal THE DEPTH
COROLLARY — a stated depth is still a binding-side fact (ef446 showed one failing to bind the
draw); the dome shows one holding. The two results are the corollary's two branches, now both
photographed. Resting: ef211 REVERTED to the pool wheel (`cbcc9fde`, the snapshot's pre-state);
the dome artifact (`b0af62a0`) regenerates from the committed spec.

---

## PROVENANCE

What this rung commits is a **derivation, its gates and this record** — cell coordinates, depths,
hazard predicates, effect ids and counts, never a stock byte.

**THE COMMITTABLE SURFACE, NAMED EXHAUSTIVELY — six files, all in
`studies/custom-summons/tier-w/`**, so that a `git add -A` cannot sweep an unowned script into this
round's commit:

| file | owner |
|---|---|
| `w6b2_tpage_sweep.py` | the tpage sweep lane (L1) |
| `w6b2_write_scan.py` | the write-scan lane (L2) |
| `w6b2_v1a_check.py` | the argument-recovery refuter (V1a) |
| `w6b2_v2_check.py` | the write refuter (V2) |
| `w6b2_gates.py` | this synthesis — H0–H16 |
| `W6b2-ATTRIBUTION.md` | this record |

⛳ **§10 adds two more, same rules** (plus the kit files themselves, which its I10 and H8 both scan):
`w6b2i_gates.py` (the integration round — I0–I10) and `w6b2_census_restamp.py` (row 9's re-stamp;
its SE-derived input and output stay in SCRATCH, the script commits only coordinates and counts).
⛳ **§10.1 adds the cast pair's two:** `phoenix_dome.toml` (the spec — guards, counts and a hash
prefix, no stock byte) and `dome_band_stamp.py` (the generator; the stamped PNG it writes is
SE-derived and stays in SCRATCH under `repaint-w6b\ef211-dome\`).

⛳ **A SEVENTH FILE WAS PRESENT AND IS NOW GONE, BY DECISION rather than by drift.**
`w6b2_v1b_audit.py` (28 KB) sat untracked in the checkout and **every lane that could have owned it
disclaimed it**, while a script of the same name and different content lived in SCRATCH. It has been
**copied to `C:\gd\SCRATCH\summon-format\texel-w6b\w6b2\w6b2_v1b_audit.worktree-orphan.py` for the
record and DELETED from the worktree.** Its artifact `v1b_audit.json` block **A5** survives in
SCRATCH and §6 row 8 now cites it **as data, not as a refuter** — which is what it always was.

`w6b2_gates.py` carries **zero Square-Enix bytes**: H8 scans every new file `git status` reports
against all 372 corpus containers and reports **0 unadjudicated leaks** and **0 stock-shaped files**,
with the one matching literal adjudicated **by name** rather than suppressed. **The lane dossiers,
the decoded listings and every recovered constant stay outside the checkout**, under
`C:\gd\SCRATCH\summon-format\texel-w6b\w6b2\`. No shared file was modified; nothing was written to
the game install, the engine DLL, or `Memoria.ini`. No `git commit` was run.
