# W6b-3 — THE ARCHIVE HYPOTHESIS (recon synthesis: a false premise, a mis-read record, 73 cells, and a wall that holds harder)

> **Status: RECON COMPLETE — HYPOTHESIS FALSIFIED, A DIFFERENT CHANNEL FOUND, NOTHING SHIPPED.**
> Two sweep lanes, two refuters and a completeness critic. No kit code changed, no deploy, no
> game-install read or write, no `git commit`. §0–§7 and §9's counts are the RECON record; §8 is an
> argument; §10 is the gate board.
>
> **The question this rung was given:** `W6b-SCENERY.md` §5's cast ladder says the invisible drawn
> binding behind ef446's salmon checker is *"most plausibly an **id-2 archive model** — sweeping id-2
> model records for tpage/clut is the named future attribution channel."* **That sentence is wrong on
> both halves and should be corrected in that record rather than left standing** (§3). The sweep it
> named nevertheless found a real channel — just not the one it named, and not in the place it looked.
>
> **Records under extension:** `W6b-SCENERY.md` (§5's cast ladder, THE DEPTH COROLLARY, THE
> GHOST-LAYER OBSERVATION) · `W6b2-ATTRIBUTION.md` (§2's attribution table, §5's posture framework,
> §3's residue, §10.1's dome cast) · `PLAN.md`.
> **Recon this document distils** — all outside the checkout, all Square-Enix-derived, never in the
> repo, under `C:\gd\SCRATCH\summon-format\texel-w6b\w6b3\`: `L1-ID2-SWEEP.md` + `id2_sweep.json`
> (+ `id2_analysis / _control / _ghost / _residue`, `p0_where`…`p4_field_shape`) · `L2-ID2-JOIN.md`
> + `id2_join.json` + `join_run.log` · `v1-DECODER-REFUTATION.md` + `v1_decode / _diff / _walker /
> _parts / _null / _order / _wide / _private` · `v2_walk / _join / _probe / _hazard / _partrange /
> _ghostalt` · `CRITIC.md` + `c1_walker`…`c7_clutnull`.
>
> **RE-MEASURABILITY, SCOPED HONESTLY.** **§0–§7 and §9 are re-measured by `w6b3_gates.py` on each
> run — 10/10**, from the 372-container corpus, the census and the shipped kit modules; the lane
> JSONs are *not* read back as answers. **§8 is an argument, not a measurement**, and the two in-game
> facts it turns on (the dome cast HELD; the ef251 cast FAILED) are `W6b-SCENERY.md` §5's and
> `W6b2-ATTRIBUTION.md` §10.1's, **not re-measured here** — but **§8.3's cast shortlist IS**: G7
> prints the 26 clean cells by name and the 4-cell intersection the recommendation rests on, so the
> vehicle choice is checkable rather than asserted. **§6 carries refuter-owned numbers this
> file does NOT re-roll and they are labelled where they appear** — refuter 1's three constructed
> record nulls (*0 hits in 13,555 trials*), its `1/72` other-container null and its `23/309` random
> draw (this file's own seeded re-roll of the same null scores **62/309 = 20.1 %**, and **that** is
> the number §1.2 quotes), and refuter 2's permutation null (`0.691`, p `0.0040`) and
> independent-marginal null (`0.606`). Everything else in the scoped sections is printed by a gate.
> **Where a number disagrees with a dossier, both predicates are stated** rather than reconciled
> away; §6 collects them and **each row carries its refuter's own verdict word verbatim**.
> Siblings re-run unchanged: `w6b2_gates.py` **17/17** · `w6b_gates.py` **7/7** ·
> `w6b2i_gates.py` **11/11** · `w6q_gates.py` **20/20**.

---

## 0. THE SEVEN THINGS THIS RUNG DECIDED

1. **★ THE HYPOTHESIS'S PREMISE IS FALSE — and that is the finding, not a failed round.** The round
   was asked whether **id-2 sub-file archive models** are a binding source the census's walker cannot
   see. **It sees all of them.** `reskin.attribution` walks `EC.scan_geom(blob)`, a **whole-blob
   needle scan with no resource filter**, so it already descends into every sub-file id: the kit's
   own bindings resolve to resources **{2: 175, 6: 137, 8: 20, 10: 8}** and it binds id-2-resident
   models in **60 containers**. Id 2 *is* the archive (`EC.RESOURCE_IDS[2] = SUBFILE_ARCHIVE`) and it
   *is* the largest home for embedded models — **658 of the corpus's 981** non-creature GEOM blocks —
   but residency was never the blind spot.
2. **★★ THE BLINDNESS IS IN THE RECORD READER, AND IT IS A FORMAT BUG.** The `so` record is a
   **MULTI-PART BINDING ARRAY**, not a single binding. `reskin.so_record` hard-probes `recLen` in
   `(0x10, 0x08)` only and returns `None` for anything longer, so **126 records — and all 309 of
   their binding slots — are invisible to the kit**: the record, slot 0, and every `part >= 1` slot.
   The corpus holds `P = 0..7`. The one-part reading survived because **340 of the 376 records the
   kit accepts are `P == 1`** and the other **36 are `P == 0`**.
3. **★ FOLLOW-THE-EVIDENCE CORRECTION, STATED LOUDLY: this is a RECORD-LENGTH channel, not an id-2
   channel.** The 126 invisible records split **id-2 61 / id-6 53 / id-3 12**, so naming it *"the id-2
   archive channel"* would be wrong on **65 of 126** — and the framing costs **52 % of the reach**,
   measured: restricted to id-2-resident records the gain falls **65 → 31**, while the invisible
   *slots* split **id-6 158 / id-2 127 / id-3 24**. **Id-6 carries more than id-2.**
4. **THE REACH IS 73 CELLS — 65 unanimous + 8 dual — AND IT DEFLATES TO 26.** 73 scenery page-cells
   are new against **every** channel (census, P, G). **All 73 come out of the 861 covered-but-
   uncovered class**, so the residue moves **2,139 → 2,066** if the 73 were adopted, **2,074** for the
   65 unanimous, and **2,113** after the honest hazard re-score to **26 genuinely clean** cells. **0
   come from behind the wall.**
5. **★ THE STRUCTURAL WALL HOLDS HARDER THAN EITHER LANE COULD SAY.** W6b-2 proved the ceiling by
   ABSENCE OF MODELS (222 containers, 0 non-creature GEOM blocks). This rung tested it **from the
   other side**, which nobody had: over **934** halfword-aligned `so` magic sites corpus-wide,
   **502** are shape-valid and **502/502 target a GEOM base — 0 target anything else**; inside the
   222 blind containers there are **164** magic sites and **0** shape-valid. **There is no `so`-shaped
   binding record on a non-GEOM drawable anywhere in the corpus.** That is a positive law where the
   old claim was an absence.
6. **★★ THE GHOST-LAYER PREDICTION FAILED — 0 hits, 4 misses, 2 vacuous passes over six named
   cells** (§3). The archive channel says **nothing** about ef446's 8bpp reader, nothing about
   ef251's x512, and nothing (as predicted) about ef429. It is not that the reader is hiding in a
   longer record: **ef446 and ef429 have ZERO recordless GEOM blocks**, so every model in those two
   containers is now enumerated and its depth read.
7. **★ AND THE ROUND'S MOST IMPORTANT PRODUCT IS A SAFETY FINDING, NOT A DEPTH GAIN.** The dropped
   records make the **SHIPPED** palette lane publish **five FALSE "DERIVED PRIVATE" verdicts** — a
   wrong answer a user acts on, not a missing depth (§7). Fixing the reader is a **different
   decision** from licensing its depths, and §8 splits them.

---

# 1. THE FORMAT FINDING — the record is a MULTI-PART BINDING ARRAY

## 1.1 The layout, and which halfword carries the load

```
+0x00 u16  magic     == 0x6F73 ('so')
+0x02 u16  textured
+0x04 u16  recLen    == 8 + 8P     -- self-describing: recordBase + recLen == GEOM base
+0x06 u16  arrayB    == 8 + 4P
+0x08      P x { u16 tpage, u16 clut }   at STRIDE 4, selected by the primitive's `part` byte
+arrayB    P x { u16, u16 }              OPAQUE
                       P = (recLen - 8) // 8 = (arrayB - 8) // 4
```

⚠ **`recLen == 8 + 8P` IS NEAR-TAUTOLOGICAL AND IS FLAGGED AS SUCH.** With `P` *defined* as
`(recLen - 8) // 8`, that equation asserts only `recLen ≡ 0 mod 8`. **The load is carried by
`arrayB`, an INDEPENDENT halfword agreeing 502/502** — and **126 records take an `arrayB` outside the
two constants `{8, 12}` a `P ≤ 1` corpus could ever supply, so the informative population is exactly
the novel one.** `recordBase + recLen == geomBase` on **502/502**: the record is self-describing, and
the acceptance test is therefore **two independent 16-bit matches**.

The `textured` halfword at `+0x02` is a near-redundant restatement of `P >= 1` — true on **501/502**,
the single exception being the ef226 outlier `reskin.so_record`'s own docstring already names by
offset and value. **It reads 1 at P = 7, so the "part count" reading of that field is refuted.**
15bpp slots carry `clut == 0` on **69/69**, consistent with the kit's direct-colour model.

## 1.2 What earned this reading — the controls, because a reading never contrasted with a wrong one is an assertion

Scored on the **declared-column** predicate over the **309** kit-invisible slots:

| reading | declared column | legal 9-bit page word | CLUT word in the container's own id-0 list | its bucket agrees |
|---|---:|---:|---:|---:|
| **SHIPPED — `+0x08`, stride 4, interleaved** | **279/309 = 90.3 %** | **309/309** | **264/264** | **264/264** |
| wrong stride 8 *(the first reading tried, then discarded)* | 144/309 = 46.6 % | — | — | — |
| phase +2 *(the CLUT halfword read AS a tpage)* | 0/309 | 45/309 | — | — |
| the IN-RECORD NULL *(the second array at `+arrayB`)* | 0/309 | — | 0/264 | — |
| ★ **SPLIT-ARRAY — `tpage[P]` then `clut[P]`** *(the creature header's own house style)* | 146/309 = 47.2 % | 194/309 | 147/264 | 85/264 |

* **The in-record null's "legal tpage 309/309" is VACUOUS** — its values are all in
  `{0, 16, 32, 64, 80, 128}` — and is printed rather than quoted.
* **The honest floor**, because two 0/309 rows are suspiciously clean: a random halfword drawn from
  the record's own bytes scores **62/309 = 20.1 %** on this file's own seeded re-roll (refuter 1
  measured **23/309 = 7.4 %** on its draw, and **1/72** for the same offsets read out of a *different*
  container). **The shipped reading clears the floor by ~4–12x depending on the draw.**
* **★ THE SPLIT-ARRAY CONTROL is the only alternative with a provenance argument behind it and it
  was unrun by every lane.** The kit's own `EC.ModelPackage` — the id-4 CREATURE header, provenance
  the DLL disassembly — stores its per-part binding as **two separate arrays**, `u16 tpage[P]` at
  `+0x18` then `u16 clut[P]` at `+0x24`. If the `so` record follows the same house style, `+0x08` is
  `tpage[P]` followed by `clut[P]` — which consumes **exactly 4P bytes**, ends **exactly at
  `arrayB`**, and at `P == 1` is **byte-identical**. Neither `recLen`, nor `arrayB`, nor the 340/340
  slot-0 rung, nor any of the four independent re-walks can tell them apart. **The shipped
  interleaved reading wins on all four predicates.**

## 1.3 The two checks that come from OUTSIDE the record's own header

Every check above except the CLUT column is scored on fields of the same 8-byte header, which can be
jointly wrong. Two instruments reach outside it:

* **★ THE PART-BYTE RANGE TEST (refuter 2).** Every textured face carries a `part` byte **selecting**
  one entry of the binding array (`container.PRIM_FIELDS`). Over **502** records, **0** have
  `max(part) >= P`; the part histogram is **{0: 465, 1: 126, 2: 28, 3: 16, 4: 10, 5: 2, 6: 1}**,
  topping out below the corpus max `P` of 7; and **every P ≥ 2 record actually exercises more than
  one part (126/126)**, so the extra entries are **live**, not dead bytes. Under stride 8,
  `P' = (recLen-8)//16` and **all 126 P ≥ 2 records would index past their array** — a **categorical**
  falsification, strictly stronger than a 90.3 %-vs-46.6 % score.
* **★★ THE CLUT-ARITY TEST — the only rung in this round with power over a `P >= 2` byte, and NO
  LANE AND NO REFUTER OPENED IT** (§7). The container's **id-0 payload header** independently
  declares each palette's entry count (`+0x0c nClut4`, `+0x0e nClut8`, `+0x10 clutWord[]`), and
  **16 entries ⇔ 4bpp / 256 ⇔ 8bpp**, while the tpage's bits 7–8 state the binding's depth. Two halves
  of one fact, never joined. Over the **264** kit-invisible **indexed** slots (309 minus the 45
  direct-15bpp): **AGREE 264 / DISAGREE 0**; **exact-word membership 264/264** — the CLUT halfword is
  *literally* a member of the container's own `clutWord` list — landing in the bucket the tpage's
  depth demands **264/264**. Over all **649** slots: **576 AGREE / 0 DISAGREE / 69 direct-15bpp /
  4 unresolvable, and all 4 unresolvable are KIT-VISIBLE.** ⚠ **With its own nulls, because 264/264
  with no floor is an assertion:** cells declaring a *single* arity **264/264** (so no row is
  vacuous), random halfword from the record's own bytes **429/2,640 = 16.2 %**, the in-record null
  **0/264**, the split reading **147/264** in-list and **85/264** bucket-ok, and an ambient
  accidental-arity floor of **53.3 %** — which the exact-word test's **264/264** clears and the
  split's **85/264** does not.
  **BY-PRODUCT, answering a question the round also asked: ARCHIVES CARRY NO PALETTES.** All 264
  invisible CLUT words are already members of the id-0 header's own list — the read-side twin of
  *"no writer record lives in an id-2 resource"* (§3).

> ⚠ **AND ONE CLAUSE OF THE SPEC IS NOT MEASURED AND MUST NOT SHIP AS IF IT WERE.** *"indexed by the
> primitive's `part` byte"* states an **arity** and an **order**. The arity is measured twice
> (part-byte range, CLUT arity). **The order is not.** L1's declared-column control is
> permutation-invariant by construction; refuter 1's non-invariant UV predicate could not
> discriminate either **and was built on a broken UV operand** (§7); re-run here on corrected UVs with
> a bpp-sensitive page-fit predicate over the **50** depth-mixing records / **109** parts:
> **identity 69 = 63.3 %, reversed 61 = 56.0 %, 50 random permutations 3,237/5,450 = 59.4 %.**
> Identity is best and reversed worst — the first time the ranking has come out that way — but it
> sits ~0.9σ above random. **It does not touch the 73/65-cell depth gain** (the rollup pairs a slot's
> page with that same slot's own bpp, index-free), and it is load-bearing for anything that maps a
> PART to a cell: **82 of 126** multi-part records name more than one distinct tpage.

## 1.4 The window and the shadowing caveat — both CLOSED

L1 shipped *"no farther record was shadowed by a nearer false positive is made improbable, NOT
proved; beyond 0x4000, unknown."* Both halves are now measured. Keeping **every** candidate that
passes the length test, **0 of 981** GEOM blocks has more than one — so *nearest* and *farthest* are
the same record everywhere and the tie-break was never load-bearing. A **0x10000** window with **no
resource floor** finds **0** additional records on **981/981**; the longest `recLen` in the corpus is
**64** (P = 7), and since `recordBase + recLen == geomBase` a window can only ever exclude a *longer*
record.

---

# 2. THE SWEEP AND THE JOIN — the numbers

**Population** (`w6b3_gates.py` G1, re-measured; four independently-written walkers agree at
symmetric difference **0**):

```
981  non-creature GEOM blocks          by resource  {2: 658, 6: 282, 8: 20, 3: 12, 10: 9}
502  with a decodable binding record   by resource  {2: 252, 6: 209, 8: 20, 3: 12, 10: 9}
649  binding slots                     P histogram  {0:36, 1:340, 2:98, 3:12, 4:6, 5:8, 6:1, 7:1}
126  records INVISIBLE to the kit      by resource  {2: 61, 6: 53, 3: 12}
309  binding slots INVISIBLE           by resource  {2: 127, 6: 158, 3: 24}   depths {4:74, 8:190, 15:45}
444  recordless but UV-BEARING         by resource  {2: 374, 6: 70}
 35  recordless with no UV faces
     502 + 444 + 35 = 981  -- the residue closes EXACTLY
```

**Containers, disambiguated** — because *"containers with archives"* is 145, 372, 72, 80 or 28
depending on the question, and all five are true: **145** hold a non-creature GEOM block inside an
id-2 archive · **all 372** carry an id-2 **resource** · **72** have a decodable id-2 record · **80**
have any record at all · **28** hold at least one **invisible** record.

**The declared-cell pivot.** The 309 invisible slots name **109 DECLARED page-cells: 87 id0 + 19 id9
+ 3 CREATURE → 106 scenery.** That 3-cell pivot explains two published numbers at once (§6 row 10).
A further **61 slot hits over 7 cells** name a column the container **never uploads at all** — they
attribute nothing, by the same rule channel P applies to its own 5 undeclared columns.

**The join** (G3). Census **2,665** rows = **2,572** scenery + 93 creature; **2,385** scenery cells
depth-unknown. Channel **P** (the shipped `depth_attribution` table): **221** rows = 199 unanimous +
22 dual → **189** gains. Channel **G** re-derived **live** from the containers: **57** gains + **8**
dual. Channel **A** (this rung): **73** new, **65** unanimous + **8** dual.
**Double-count checks all empty — P∩G 0, P∩A 0, G∩A 0, A∩census-known 0 — so 189 + 57 + 73 = 319 and
the totals ADD.**

---

# 3. ★★ THE GHOST-LAYER VERDICT — scored prediction by prediction

Predictions were written into the probe's docstring **before** the numbers were read. Each vehicle
contributes **two stacked cells**, so the score is over **six named cells**.

| vehicle | the in-game fact (`W6b-SCENERY.md` §5) | PREDICTED | declared column | UV cover *(corrected UVs)* | spill target | verdict |
|---|---|---|---|---|---|---|
| **ef446** x448 | census 15bpp; **DREW at 8bpp** (the salmon checker; THE DEPTH COROLLARY) | an invisible archive binding names this column at 8bpp | **0** invisible slots, 1 of any kind, depths **[15]** | **0** | `448` + `512` → **1** slot, 15bpp | **MISS ×2** |
| **ef251** x512 | channel P registered tpage 312 = 15bpp; **DREW indexed / 4bpp** (the bumper strip) | an invisible archive binding names x512 at 4bpp | **0** invisible **and 0 of any kind** | **0** | `448` + `512` + `576` → **0** slots | **MISS ×2** |
| **ef429** x448 | census 15bpp; **BOUND-NEVER-DRAWN** on both covers | *nothing* — a channel that "explained" this would be over-fitting | 0 invisible, 1 of any kind, depths **[15]** | **0** | `384` + `448` + `512` → **1** slot, 15bpp | **VACUOUS PASS ×2** |

**FULL SCORE: 0 hits, 4 misses, 2 vacuous passes.** The archive channel says **nothing** about **6 of
the 6** named cells, and `W6b-SCENERY.md` §5's *"most plausibly an id-2 archive model"* should be
corrected in that record.

⚠ **THE BASE-RATE CAVEAT ON THE VACUOUS PASSES, STATED RATHER THAN BANKED.** ef429 "passes" by
predicting nothing, on a container with **1** GEOM block and **1** record. That is not evidence for
the reading; it is the absence of evidence against it, and it is counted separately for exactly that
reason. **A channel scores 2 vacuous passes on this ladder by doing nothing at all.**

**AND THE CONTAINERS ARE NOW EXHAUSTED, WHICH IS THE STRONGER STATEMENT.** *"A model we have not
found yet"* is **closed** for two of the three vehicles: **ef446 has 5 records / 5 GEOM blocks / 0
recordless**, and **ef429 has 1 / 1 / 0**. Every model in those containers is enumerated and its depth
read. **ef251 is the exception** — **0 records over 38 UV-bearing GEOM blocks**, split id-6 35 / id-2
3 — so even its residual population is **not** an id-2 story.

**A SHARPENING L1's TABLE DID NOT HAVE: ef446 DOES bind 8bpp** — GEOM `0x2c094` at page **(704,256)**,
a **different** column, through a record the kit **already reads**, and that binding resolves to the
very CLUT cell the screen showed. So the container already holds the exact palette at the exact depth
the screen showed, on another column; **no invisible model is needed to supply it, and whatever draws
the nucleus at 8bpp is not a GEOM model in ef446 at all.**

**WHERE THE GHOST COULD STILL BE**, and it is a larger population than this lane recovers: **444**
UV-bearing GEOM blocks corpus-wide carry no record (id-2 374 / id-6 70). But ef446 and ef429 hold
**zero** of them. The surviving candidates for those two are the **id-3 program's own primitives**
(already confirmed once in-game, on ef211's dome) or **another container's surface** — and refuter 2's
strongest surviving explanation, that the drawn depth is **submission-time GPU state** rather than a
stored model property, is untouched by anything measured here (§9).

**THE PRIOR THIS LANE INHERITS, SIZED.** Only **14** scenery page-cells corpus-wide carry a census
15bpp and **6** have been probed in-game — **a 43 % sample, every one of which was bound-never-drawn
or drawn at another depth.** THE GHOST-LAYER OBSERVATION generalises over close to half its own
population, which is stronger than *"3 vehicles"* makes it sound — and it lands on **4** of this
lane's own gains (§4).

**A CLOSED CANDIDATE, RECORDED SO NOBODY RE-RUNS IT.** The round named *"a draw-call reference from
the id-3 program into the archive"* as the drawn/undrawn discriminator. Measured: **7,872** id-2
directory entries (22 negative) name **360** GEOM blocks and **253** records, and the split is
**deterministic** — **{2: 252, 10: 1}**, with every id-6, id-3 and id-8 record unnamed. On the
vehicles it discriminates **nothing**: ef429 (bound-never-drawn) **1/1** named, ef446 (DREW at 8bpp)
**5/5**. **"Directory-named" is RESIDENCY, not a reference.**

**AND W6b-2 §3 PROBE 1 / W6b-1 Q4, SHARPENED IN PASSING:** **20 of ef390's 32** slots name page
**(448,256)** at 15bpp — a page ef390 never uploads — not the 10 W6b-2 recorded; and **0 of the
corpus's 2,741** census page-cell **writer** records lives in an id-2 resource (**{0: 2531, 4: 93,
9: 117}**). **No archive uploads a page in any container**, so the residual-VRAM hypothesis survives
untouched and the refusal stays permanent.

---

# 4. THE REACH AND ITS SPLIT

**73 cells new against every channel = 65 unanimous + 8 DUAL-DEPTH** (a hazard, not a vote).
Depths of the 65: **{4bpp 15 · 8bpp 46 · 15bpp 4}**. The 73 is **stable under both subtraction
predicates** (strict: census-known + P's 221 rows + G's 65-cell coverage; conservative: the whole
so-page roll).

**THE REACH'S ACTUAL MOVEMENT ON THE RESIDUE — which neither lane stated.** All **73** are drawn from
the **861** covered-but-uncovered class; their intersection with the **1,278** blind cells is
**empty**.

```
residue 2,139 = 1,278 behind the wall + 861 in model-BEARING containers
  adopt the 73   ->  2,066   (the 861 becomes 788)
  adopt the 65   ->  2,074
  adopt the 26   ->  2,113   <- the honest number, after the hazard re-score below
```

**THE DEFLATION — 65 gained a DEPTH; 26 clear everything else.** ⚠ **65/65 of the gained cells are
READERLESS**, and the census's `hz_multi_palette` is **reader-derived**, so its clean **0** on this
set is **VACUOUS, not a clear**. Re-derived from the **binders** at column granularity:

| | cells |
|---|---:|
| genuinely CLEAN | **26** |
| class C — the column is bound with **2–4 distinct CLUT words** (a DISCLOSURE, not a refusal) | **34** |
| `hz_program_write` — **all 7 in `ef415`** | **7** |
| *(2 cells carry both, so the three rows sum to 65 with the overlap counted once)* | **65** |

⚠ `hz_attribution_blind` is **container-level**, not cell-level, so **40** of the 65 carry it and
**25** do not while **all 65** are readerless. It is reported and then **excluded** from the clean
predicate — the same reasoning W6b-2 §6 row 3 used to call its strict-10 count circular. A reader who
counts it as a disqualifier gets **25**, and that number is here rather than suppressed.

⚠ **31 of the 65 are LOWER halves** — and **five of them are DIRECT READS, not inherited** (§7): the
container's own UV pool sees an invisible model sample those bytes at `v >= 128` on
**ef130.x448_y384 · ef155.x448_y384 · ef179.x576_y384 · ef184.x576_y384 · ef424.x704_y384**. The
remaining **26 of the 31** are inherited from the column, and no instrument has seen a model sample
them. *(That 26 is the lower-half remainder and has nothing to do with the 26 clean cells above —
the collision is a coincidence and is flagged so no reader adds them.)*

⚠ **4 of the 65 are 15bpp** — `ef210.x704_y256/384` and `ef226.x768_y256/384` — and carry §3's
GHOST-LAYER prior in full. **They are the weakest cells in the reach.**

⚠ **THE 65 HAVE NO SECOND WITNESS OF ANY *CHANNEL* — but the flat form of that sentence is false and
must be split.** Census 0, channel P 0, channel G 0, channel H 0 (H cannot fire: **65/65** of their
containers ship both CLUT arities, so the narrowing structurally cannot narrow). **But the CLUT-arity
STRUCTURE corroborates the binding that names them, 264/264** (§1.3). *"No second channel"* is true;
*"no second witness of any kind"* is false.

---

# 5. THE CONFLICTS — named cells, both predicates

## 5.1 The agreement statistic, and the control it does not clear

| | n | AGREE | COMPATIBLE | FLAT |
|---|---:|---:|---:|---:|
| archive vs the `so` **CENSUS**, L2's predicate | 21 | **17 = 81.0 %** | 3 | 1 |
| archive vs the `so` **CENSUS**, including the census-DUAL row L2 drops | 22 | **17 = 77.3 %** | 4 | 1 |
| archive vs **CHANNEL G**, which the kit **LICENSES** | 33 | **25** | 6 | **2** |

⚠ **★ AND THE 81.0 % CARRIES ALMOST NO INFORMATION.** The census depth and the archive depth for a
comparable cell are **two records naming ONE column**, so they agree unless the container draws that
column at two depths. **THE TAUTOLOGY CONTROL, run entirely inside the census's OWN instrument:** over
the **65** columns bound by **≥2 kit-VISIBLE** models, **51 are single-depth = 78.5 %**. Corpus-wide,
**141 of 162** bound columns = **87.0 %**. **Observed and control are within noise of each other.**
Two weaker nulls from refuter 2 point the same way (independent-marginal **0.606**; permutation
**0.691**, p = **0.0040** — and *that* p is inflated precisely because shuffling destroys the
structural dependency the tautology control preserves). **The decode is well supported — by four
independent re-walks, the part-byte test and the CLUT-arity test. It is NOT supported by this
statistic**, and the statistic should not be quoted as if it were a calibration.

⚠ **The comparable set is also SCARCE BY CONSTRUCTION**, and for the same structural reason channel
P's N = 10 was: this channel **is** the set of records the census cannot read, so of the 106 declared
scenery cells only **21–22** carry a census depth. The 21 rows sit on **17 distinct columns**, so the
effective N is nearer 17.

## 5.2 The named cells, with both predicates

**THE MULTI-VALUED HAZARD CLASS IS 12 CELLS, NOT 8** — L1 counted only the ones that are *also* new,
and a hazard bites hardest exactly where another channel already covers the cell:

```
ef130.x576_y256/384 [4, 8]   ef179.x448_y256/384 [4, 8]   ef186.x576_y256/384 [4, 8]
ef226.x704_y256/384 [4, 8]   ef382.x448_y256/384 [4, 8]   ef508.x576_y256/384 [4, 15]
```

**THE SAFETY POPULATION IS 5 CENSUS-ATTRIBUTED CELLS, and the fifth is the class's own CONTROL** —
without it, *"the archive contradicts census cells"* reads as a property of the archive rather than of
four specific cells:

| cell | census | archive | verdict |
|---|---:|---|---|
| `ef179.x448_y256` | 4 | [4, 8] | **DUAL** — the archive's set *contains* the census depth |
| `ef186.x576_y256` | 8 | [4, 8] | **DUAL** |
| `ef186.x576_y384` | 8 | [4, 8] | **DUAL** |
| **`ef184.x448_y256`** | **4** | **[8]** | ★ **FLAT CONTRADICTION** |
| `ef381.x576_y384` | 8 | [8] | **AGREES** — the control |

**THE FLAT CONTRADICTION IS TWO CELLS, NOT ONE, AND THE SECOND HITS A LICENSED CHANNEL.** Against
channel G — which the kit **licenses** — the FLAT rows are **`ef184.x448_y256` AND `ef184.x448_y384`**.
Both predicates, on the same bytes of the same container:

```
ef184  kit-VISIBLE  GEOM 0x86bfc   record 0x86bec  P=1          tpage  23 -> 4bpp
       INVISIBLE    GEOM 0x7b2e0   record 0x7b2c8  P=2, part 1  tpage 151 -> 8bpp
       true UV cover  0x86bfc hx 448..479   0x7b2e0 part 1 hx 448..511   -- OVERLAP on 448..479
```

**The same texels are read at 4bpp by one model and 8bpp by the other.** That is **THE DEPTH
COROLLARY's mechanism demonstrated on shared bytes for the first time** — not a repeal of it, and not
an error in either instrument. **Adjudicated, not explained.**

⚠ Two corrections this record makes to its own inputs on these cells: the **published UV strings for
both models were wrong** (L1 and refuter 1 read the pool INDEX, not the pool), so the two-column
"spill" they imply **does not exist**; and the critic's inference that `ef184.x448_y384` is therefore
**directly sampled** over-reaches — true max `v` is **127**, i.e. line **383**, the *last line of the
upper cell*. **That cell's depth is INHERITED, like 26 of the 31 lower halves.** (§7.)

---

# 6. SHARPENINGS — where a lane and its refuter disagreed, both predicates named

Each row carries **the refuter's or critic's own verdict word, verbatim**. Rows marked
`SELF-MEASURED, UNREFUTED` had no external reviewer and say so in those words.

| # | claim as recorded | as re-measured | verdict |
|---:|---|---|---|
| 1 | **L1's record decode** — 502 records / 649 slots / 126 invisible / 309 invisible slots, fields at `+0x00/+0x02/+0x04/+0x06/+0x08` stride 4 | reproduced by **three further independently-written walkers** with **opposite tie-breaks** (nearest / direct-probe / forward-scan-farthest) at **symmetric difference 0** on every record and slot field | **[CONFIRMED ×2]** — refuter 1 and refuter 2 both. The single strongest thing this round can say. |
| 2 | **L1 F1: `recLen == 8+8P`** offered as the format's self-describing check | near-tautological given `P := (recLen-8)//8`; **`arrayB` is the independent halfword**, 502/502, and **126** records take a value outside a P≤1 corpus's two constants | **[CONFIRMED]** *(refuter 1)* — L1's own caveat conceded it; the sharpening is that the informative population is exactly the novel one. **Quote `arrayB`, not `recLen`.** |
| 3 | **"indexed by the primitive's `part` byte"** shipped as a measured clause | **ARITY corroborated** from outside the header (part bytes 465/465, 0 over-runs, 0 gaps; stride 8 falsified **126/126**). **ORDER untested by every control in the round** — L1's is permutation-invariant; refuter 1's non-invariant one scored reversed *higher*; re-run on corrected UVs, identity 69 / reversed 61 / permutations 59.4 % | **[MIXED]** *(refuter 1)* — **conclusion survives, evidence replaced.** Do not ship the ordering clause as measured; cite §1.3, not `v1_order.py`. |
| 4 | **the hypothesis's premise** — that archive models are invisible to the census walker | `EC.scan_geom` is a whole-blob needle scan with no resource filter; verified **without re-implementing it** by mapping the shipped `attribution`'s own Bindings back to their owning resource | **[CONFIRMED]** *(refuter 1)* — the premise is **FALSE** and the round says so rather than rescuing it. |
| 5 | **L1 §1.4's measured example** — "ef184 GEOM 0x7b2e0 … it is inside an id-2 archive" | ef184 has **9** records, **9/9 res_id 6**, **ZERO** in an id-2 archive | **[REFUTED-AS-STATED]** *(refuter 1; caught first by L2)* — the conclusion is untouched, **the demonstration is not**, and it is the same ef184 that supplies the round's only flat contradictions. **W6b-2 §6 row 5's "data right, prose wrong" shape, again.** |
| 6 | **L1's five / L2's eight calibration rungs** offered as satisfying the calibrate-before-judging law | **zero of them evaluates a byte only the new reading reaches** — ef211 holds **0** multi-part records, KA2's block is P=1, R3 runs only on records the kit accepts, R4 compares the kit's own population | **[MIXED]** *(refuter 1)* — the law was honoured on the OLD channel; the novel channel was calibrated by nobody until the part-byte census (arity only) and, in this record, the **CLUT-arity test** (§1.3). **The gate prints this limit rather than leaving it to be inferred.** |
| 7 | **L1's four controls** (90.3 % / 46.6 % / 0 / 0) | reproduced **exactly**, plus three nulls neither lane ran, because two 0/309 rows are too clean for a floor | **[CONFIRMED]** *(refuter 1)* |
| 8 | **L1's caveat**: shadowing "made improbable, NOT proved"; "beyond 0x4000, unknown" | **0 of 981** blocks has more than one passing candidate; a **0x10000** window with no resource floor finds **0** more on 981/981 | **[REFUTED-AS-STATED]** *(refuter 1)* — both halves now **measured**, so both caveats are retired rather than repeated. |
| 9 | **L2's ghost-layer verdicts** (ef446/ef251 MISS, ef429 vacuous) | re-measured independently, and **widened twice** — a UV-cover predicate and a **spill-target** predicate the ef446 cast specifically demands — every one still **MISS** | **[CONFIRMED]** *(refuter 2)*. ⚠ **And the scoping was under-argued as published**: both lanes scoped by DECLARED COLUMN, which cannot see a reader reaching a cell by UV spill — *the exact mechanism ef446's own cast proved*. |
| 10 | **L1's "64 slot→column hits name 10 cells the container NEVER UPLOADS"** | **61 hits over 7 cells.** The missing 3 (`ef179`/`ef186`/`ef276` at `x320_y384`) **ARE** uploaded — as **CREATURE** pages. The same pivot explains L1's 106 against the true 109 declared cells | **[REFUTED-AS-STATED]** *(refuter 2)* — both counts are right under their own predicate; **the prose is not**, and the live fact underneath (non-creature models binding **creature** pages, in three containers) is recorded nowhere and is unexamined. |
| 11 | **L2's "17/21 AGREE = 81.0 %"**, offered as the join's calibration | matches a **78.5 %** column-homogeneity tautology control measured inside the census's own instrument; corpus-wide 87.0 % | **[REFUTED-AS-STATED]** *(refuter 2)* — **the count is right, its evidential value is not**, and no baseline was published. Sharpened here: it **cannot** bear on the multi-part decode even in principle. |
| 12 | **L2's comparable set of 21** | **22** archive-named cells carry a census attribution; the extra is `ef381.x576_y384`'s sibling `ef381.x576_y256`, census-**DUAL** so it has no single depth to agree with | **[MIXED]** *(refuter 2)* — excluding it is defensible and unstated, and it moves the headline from 77.3 % (just below the control) to 81.0 % (just above). **Both are printed.** |
| 13 | **L2's deflation to 26**, its 12-cell multi-valued class and its two-cell flat contradiction | reproduced **cell for cell** | **[CONFIRMED]** *(refuter 2)* |
| 14 | **L2's blind-wall three-predicate table** (222 / 222 / 0) | reproduced exactly — **but only after the refuter's own probe failed first**: a `Resource` object passed where `parse_directory` wants an **offset**, with a bare `except Exception` turning a `TypeError` into a confident negative | **[CONFIRMED]** *(refuter 2)* — ⚠ **recorded as a live instance of the house law**: a swallowed exception presented as a measurement, exposed only by disagreeing with a rival lane. |
| 15 | **an alternative refuter 2 proposed and then KILLED** — that ef446's surprise is SAME-SOURCE-BYTES (the edited cell's source bytes also written where the 8bpp reader samples) | falsified: **0** shared cells for all 5 vehicle cells, and corpus-wide **0 of 2,665** page-cells share source-file bytes with another. The writer records **partition** the file | **[REFUTED-AS-STATED]** *(refuter 2, of its own lead)* — reported rather than dropped, because a proposed-and-killed alternative is worth more than an unstated one. |
| 16 | **L1's own headline** "658 of 1,005 GEOM blocks live in id-2" | printed **verbatim** in `container.py`'s source comment above `_GEOM_NEEDLE`, which the sweep imports | **[minor finding, refuter 1]** — a documented fact re-derived, not a new measurement. The genuinely new counts are the **container** counts (145 / 222 / 80 / 72 / 28), all four confirmed. |
| 17 | **this record's own §1.4, §3 directory probe and §7 CLUT-arity rung** | run after every refuter lane closed | **[SELF-MEASURED, UNREFUTED]** — ⚠ their verdict words are **this synthesis's own**. The CLUT-arity test's four nulls and the directory probe's determinism are the strongest **self**-checks available, and that is not the same thing. |

---

# 7. THE CRITIC'S FINDINGS

The completeness critic ran after both refuters and found the round's central claim **correct and,
for the first time, properly calibrated — but not by anything the round had run.**

1. **★★ THE CLUT-ARITY CHANNEL — sitting unopened in the primary artifact's own `clut` column.**
   Every lane and every refuter named it in their caveats as the thing nobody did. It is the round's
   **only rung with power over a `P >= 2` byte** and it agrees **264/264** against a **16.2 %** random
   floor and a **53.3 %** ambient (§1.3). **It discharges refuter 1's critical finding #1 from
   conditional to established** — that finding's own stated condition was *"conditional on the
   multi-part reading's CLUT halfword, which no lane has resolved against a real palette"* — and it
   **discharges the class-C derivation as a theorem** (`clut_word_xy` is a bijection, so distinct
   words are distinct palettes and the 34 stands). ⚠ **Honest bound: it corroborates a BINDING's
   depth; it does not independently name a CELL's depth, and it gains 0 cells.**
2. **★★ THE UV COVER IS DECODED FROM THE WRONG OPERAND — in L1 *and* in refuter 1.** `iter_primitives`
   returns a face's `uv` as an **index into the mesh's UV pool** (its own docstring says so, and
   `repaint.bound_models` dereferences it); both lanes applied the right arithmetic to the **index**.
   L1's caveat 9 and L2's caveat 8 certify the **formula** against `bound_models` — and the formula is
   right; the **operand** is not. Calibrated first (**41/41** against the kit's own answer), the
   damage is **`vy` wrong on 648/648** and **`hx` on 627/648**; published corpus max `v` = **7** (pool
   indices), true max = **255**. It is load-bearing on the round's most-quoted result (§5.2).
3. **★ FIVE OF THE 65 GAINS ARE DIRECT READS, MISLABELLED AS INHERITED.** Both dossiers ship
   *"31 of the 65 are LOWER halves — depth INHERITED, never direct. No instrument has seen a model
   sample those bytes."* The container's own UV pool **is** that instrument and nobody pointed it at
   them: **24** invisible slots reach `v >= 128`, naming **12** lower cells directly, **5** of them
   inside the 65. **The error runs in the safe direction — into false modesty — and any disclosure
   built from the two dossiers would under-license exactly the cells it should license first.**
4. **★ THE STRUCTURAL WALL WAS NEVER TESTED FROM THE OTHER SIDE** (§0 item 5). Both lanes proved the
   ceiling by absence of GEOM blocks. Nobody asked whether an `so` record can exist **without** one —
   the only shape the channel could have taken behind the wall. **934 sites, 502 shape-valid,
   502/502 targeting a GEOM, 0 otherwise; 164 sites inside the blind 222, 0 shape-valid.**
5. **★ THE ROUND'S OWN NAMED DRAWN/UNDRAWN CANDIDATE WAS NEVER CHECKED** (§3, closing paragraph).
   A closed lead is worth more than an unstated one, and this one is now closed by measurement.
6. **★ THE SPLIT-ARRAY CONTROL WAS UNRUN** (§1.2) — the only alternative reading with a provenance
   argument, indistinguishable from the shipped one by every header field, and **it loses on all
   four predicates.** The interleaving was **earned**, not assumed.
7. **THE ORDER QUESTION is reopened by the corrected UVs and still not settled** (§1.3) — but
   refuter 1's published evidence for it must be **withdrawn**, since it ran on the broken operand.

**And the critic's list of numbers that were stated and backed by no artifact** — all four corrected
in this record and re-measured by the gate: L1's **"37/37"** P==0 records (measured **36/36**), L1's
**"465/466"** textured records (measured **465/465**), `id2_sweep.json`'s **"UV cover present
309/309"** (true only as *"the part has textured faces"*, which is a different statement), and the two
ef184 UV strings (§5.2).

---

# 8. ★ THE KIT POSTURE RECOMMENDATION

> **This section is an argument, not a measurement.** Its two in-game facts are
> `W6b-SCENERY.md` §5's and `W6b2-ATTRIBUTION.md` §10.1's.

## 8.1 The two photographed branches, and why "an archive binding is a binding" settles nothing

W6b-2 §5 drew its line on **kind**: **channel G LICENSES** because it is *the correct reading of
evidence the kit already ships on* — the same `so` record, at the granularity the hardware uses;
**channel P DISCLOSES** because a registration is *the same shape of evidence one layer up*, and
`BINDING-IS-NOT-A-DRAW` cost two playtests.

Both branches have since been **photographed**, and they went opposite ways:

* **THE DOME (ef211 x704,384) — a channel-G BINDING depth HELD.** Four 12-row bands at the derived
  8bpp: *"bright yellow bands. fits the fire really well"* — clean bands, no 4bpp pin-striping, no
  15bpp wrong-solid. **REGISTRATION-IS-A-DRAW-ENOUGH is TRUE of channel G's flagship.**
* **ef251 x512 — a channel-P REGISTRATION depth FAILED its first trigger cast.** tpage 312's depth
  bits say 15bpp; the self-diagnosing white bands drew the **4-cycle bumper strip** of a 4bpp read.
  **REGISTRATION-IS-NOT-A-DRAW, confirmed with teeth.**

**So where does an archive binding sit?** The tempting syllogism is *"an archive binding is a
binding; the binding branch is the one that held; therefore license it."* **That syllogism is
unsound, and this rung's own evidence is why.** The binding class is **1-for-2 on screen**: the dome
held, and **ef446 is a BINDING-side failure** — a census 15bpp binding that did **not** govern the
draw, which is exactly what THE DEPTH COROLLARY was minted to name. What licensed channel G was never
*binding-ness*. It was three things together: **(a)** it is the **same record the kit already reads**,
**(b)** its calibration had **informative rows** (16/18 on the rows that could have falsified it,
including one against a genuinely independent witness — **W6b-2 §5's number, gated by
`w6b2_gates.py` H10, not re-measured here**), and **(c)** a cast.

**Channel A has (a) and nothing else.**

* Its agreement statistic is **indistinguishable from the corpus's column-homogeneity base rate**
  (77.3 % observed vs a 78.5 % control) and cannot bear on the decode even in principle (§5.1).
* It **contradicts the licensed channel G on two cells** and the census on one (§5.2). *A channel that
  contradicts a channel the kit licenses cannot be granted the same authority without adjudication,
  and the adjudication is exactly what nobody has.*
* Its reach deflates **65 → 26**, its own multi-valued class is **12 cells**, and **4** of the 65 are
  15bpp and therefore carry the ghost-layer prior at 43 % sample strength (§3, §4).
* The **ORDER clause of its own format spec is unmeasured** (§1.3). It does not touch the 65 — but a
  posture that licensed the channel would be licensing a spec one clause of which nobody has tested.
* **Nothing here is in-game.**

## 8.2 THE LINE — and it is two decisions, not one

> ## THE READER FIX IS UNCONDITIONAL. THE DEPTH DISCLOSES AT CHANNEL P's TIER.
>
> **1. FIX `reskin.so_record` — and ship it as a SAFETY fix, not a reach.** The kit mis-reads a
> documented format. The consequence is **not** 73 missing depths; it is **five FALSE "DERIVED
> PRIVATE" palette verdicts** the shipped `summon-reskin` path publishes today, each of which invites
> an author to recolour a palette another model reads — *"exactly one GEOM model binds this cell"*
> where the true binder count is 2, or (on `ef381 pal.s0.x0_y248.e256`) **seven**. This is precisely
> the guard-rail `_apply_attribution`'s own docstring says a hand table would defeat *"by
> construction"*. **The field spec is earned** (§1.2–§1.3: four independent walkers, the part-byte
> range test, the CLUT-arity test at 264/264, the split-array control refuted on all four predicates).
> ⚠ Ship the **arity**, not the ordering clause. ⛳ **And note the blindness is ASYMMETRIC:** it also
> depresses coverage in the **safe** direction — **83** SHARED-UNKNOWN palettes would gain a named
> binder — so the fix makes the kit *less* conservative only in the `len(binders) == 1` branch, which
> is the branch that is currently wrong.
>
> **2. THE DEPTHS — DISCLOSE, at channel P's tier**, behind
> `acknowledge_program_derived_depth`'s exact shape (a literal-boolean ack **AND** a matching
> author-stated `expect_bpp`), with its own reason string naming **the archive record and the part
> index**. Not channel G's LICENSE, despite being the same record class, for the five reasons in
> §8.1 — of which the decisive one is the kit's own precedent: *`expect_bpp` is stated by the author
> and CHECKED against the derivation, never chosen.* **A weaker channel cannot be granted a stronger
> authority.**
>
> **3. REFUSE OUTRIGHT, by name:** the **12** archive multi-valued cells (§5.2), and the **2** cells
> where the archive contradicts the **licensed** channel G (`ef184.x448_y256`, `ef184.x448_y384`) —
> *both predicates true of the same bytes, and a kit that silently picks one manufactures a false
> certainty.* ⚠ Note this refusal is **not vacuous** the way W6b-2's spill-conflict was: it protects
> cells that would otherwise be disclosed.
>
> **4. DISCLOSE class C at the same granularity as the depth** — **34** of the 65 sit on a column
> bound with 2–4 distinct CLUT words, and the census's reader-derived flag **cannot see it** because
> **65/65 of these cells are readerless**. This is W6b-2 §10 correction 1 **repeating on a new
> channel, on identical evidence**; shipping "65 gained a depth" without it would make the kit less
> honest on the new lane than W6b-1 was on the old one.

## 8.3 The upgrade path, named rather than left implicit — and its cheapest experiment

Channel A earns **LICENSE** when **(i)** the ordering clause is measured, **and (ii)** a cast proves
an archive-derived depth on screen on a cell **no other channel names**.

**(ii) has four ready vehicles, and the offline work to pick them is done.** Of the **26** genuinely
clean cells, exactly four are also **DIRECTLY SAMPLED** by the invisible model's own UVs — the
strongest evidence class this channel has:

```
ef130.x448_y384   8bpp    ef179.x576_y384   8bpp
ef184.x576_y384   8bpp    ef424.x704_y384   8bpp
```

All four are **structurally identical to THE DOME**: single writer, **zero readers**, program verdict
clean, no spill-in, no co-transform, one CLUT on the column, **addressable only through the per-cell
map W6b-1 shipped**. `ef424.x704_y384` and `ef130.x448_y384` are the cleanest picks;
**`ef184.x576_y384` should be avoided** despite qualifying — it sits in the container that supplies
this round's flat contradictions, and a cast there would be read as ambiguous.

⚠ **The figure class is fixed by the same argument the dome's was: TRANSLATION-INVARIANT ONLY**
(stripes/bands). These cells have **no declared reader UVs of the kit's own**, so the offline
UV-flatness screen cannot clear a shape — and the ladder shape is the dome's exactly: a **cover-zero
probe first** (depth-invariant, so it tests *drawn-ness* without testing depth), then a **depth-bearing
band stamp** as the actual verdict cast. Preflight is W6b-1 §5.5's, unchanged and non-negotiable.

---

# 9. NAMED NON-ATTRIBUTIONS, AND THE RECON'S OWN RESIDUE

**Evidence recorded, zero cells claimed:**

* **61 slot hits over 7 cells** name a column the container **never uploads** — `ef058.x448_y256/384`,
  `ef300.x448_y256/384`, `ef390.x448_y256/384`, `ef415.x576_y384`. Evidence about somebody else's page.
* **3 more cells are named but are CREATURE-class** — `ef179`/`ef186`/`ef276` at `x320_y384` — the
  population this attribution excludes **by rule**. ⛳ **The live fact underneath is unexamined and
  is recorded here so it is not lost: non-creature models in three containers carry binding slots
  naming CREATURE pages**, a cross-class binding the scenery census is not built to see.
* **444 UV-bearing GEOM blocks carry no binding record at all** (id-2 374 / id-6 70); a 0x10000
  window with no resource floor adds none. **This lane states nothing about their depths.**
* **12 invisible records live inside id-3 PROGRAM images** — every GEOM block in an id-3 image carries
  a multi-part record and the census reads none of them. Unexamined beyond that count.
* **Resource id 10** exists in the corpus (4 resources, 2 containers, 9 GEOM blocks, all 9 with a
  record) and sits outside the documented 10-entry dispatch table. Not investigated. ⚠ It is also
  already named in `container.py`'s own source comment, so this is a re-derivation, not a discovery.
* **The 1,278 cells behind the structural wall gain NOTHING**, and the 0 is an **identity**, not a
  measurement: a blind container has no GEOM block, so no record, so no cell. **Do not project 65
  forward onto 2,139.**

**⚠ THE RECON'S OWN NAMED RESIDUE:**

* **NOTHING HERE IS IN-GAME.** Every number is a **BINDING-side** fact. `BINDING-IS-NOT-A-DRAW` and
  `THE DEPTH COROLLARY` apply in full; the ef184 pair is a **fresh instance of the corollary's
  mechanism**, not a repeal of it.
* **★ THE STRONGEST SURVIVING EXPLANATION OF ALL THREE DEPTH SURPRISES IS NOT A MODEL AT ALL, AND IT
  PUTS A CEILING ON THE WHOLE ATTRIBUTION PROGRAMME.** *"A model we have not found yet"* is now closed
  for ef446 and ef429. What remains fits one mechanism: **the record's tpage/clut pair is a DEFAULT
  the drawing program can override per submission** — i.e. the **drawn** depth is submission-time GPU
  state, not a stored model property. Every binding-side channel behaves exactly as that predicts:
  channel P has **0** rows for ef429 and ef446 and is *actively wrong* on ef251; channel G would say
  15bpp on both ef429 and ef446 cells; the archive says nothing anywhere. **If it holds, no
  binding-side channel can ever settle a draw depth, and the programme's ceiling is the EVIDENCE
  CLASS, not the 1,278 cells behind the wall.** This is refuter 2's, it is not refuted by anything
  measured here, and **it is the most important open question in the arc.**
* **The ordering clause of the published format spec is UNMEASURED** (§1.3), and 82 of 126 multi-part
  records name more than one tpage.
* **The `so`-magic search cannot see a COMPRESSED or relocated model.** If any sub-file stores a model
  in a form `scan_geom`'s needle misses, this lane says nothing about it.
* **The invisible bindings' CLUT words were resolved to a declared ARITY, not to a live palette
  image.** Depth was the question; W6b-2 §10 correction 1 is the precedent for how the palette side
  bites.
* **The census delta is only as fresh as `census/pages.json`** (post-`w6b2_census_restamp`). The 73 is
  stable under both subtraction predicates; the 65 additionally depends on the archive-dual rule,
  which this lane **inherited** from W6b-2 rather than measured.
* **The reach was not re-scored against the co-transform / writer / spill hazards individually** —
  only against the three that fire. W6b-2 §6 row 3 is the precedent for how that shrinks.
* **§1.4's window probe, §3's directory probe and §1.3's CLUT-arity rung have NO REFUTER** (§6 row 17).
  Their verdict words are this synthesis's own.

---

# 10. GATES AND SUITES

`py w6b3_gates.py` — **10/10**, corpus + the SCRATCH lane artifacts only (no install read, no deploy,
no install write, no `git commit`), ~1 min:

| gate | what it proves |
|---|---|
| **G0** | **CALIBRATE BEFORE JUDGING** — the decoder against `reskin` over 512/512 words, then **two known answers re-found first** (ef211's column-704 binding; the ef226 outlier `so_record`'s own docstring names by offset AND value), the 340/340 slot-0 rung and the 376/340 population — **and the SUBSTITUTION declared, and THE LIMIT OF ALL FOUR PRINTED**: 0 of them evaluates a `P >= 2` byte |
| **G1** | the population and the format: 981 / 502 / 649 / 126 / 309 by resource; `arrayB` as the load-bearing halfword with `recLen` flagged near-tautological; the residue closing 502 + 444 + 35 = 981; the five container counts disambiguated; **two of L1's published numbers corrected**; and **two of its standing caveats retired by measurement** |
| **G2** | **the hypothesis's premise falsified** — the shipped `attribution`'s own Bindings mapped back to their owning resource, without re-implementing the walker; and the **record-length-not-id-2** correction costed at 65 of 126 |
| **G3** | the sweep and the join: 109 declared cells (87 + 19 + 3 creature → 106 scenery); the channels re-derived live; **73 / 65 / 8 / 31**; every double-count check; the residue closing **2,385 − 246 = 2,139 = 1,278 + 861**; and **the reach's actual movement on it** (2,139 → 2,066 / 2,074 / 2,113) |
| **G4** | **the ghost-layer verdict, per cell**: three vehicles × three predicates, **0 hits / 4 misses / 2 vacuous**, the two exhausted containers, ef446's 8bpp binding on a different column, the 43 % 15bpp sample, and the ef390 / writer-record channel boundary |
| **G5** | the conflicts by name with both predicates; the agreement under **both** comparable definitions; and **the TAUTOLOGY CONTROL the agreement does not clear** (78.5 % vs 77.3 %) |
| **G6** | **the controls** — L1's four reproduced, the honest random floor, refuter 2's part-byte range test, ★ **the CLUT-arity test with its four nulls**, and ★ **the split-array control** losing on all four predicates |
| **G7** | the deflation **65 → 26** with the vacuous-flag reasoning printed, and ★ **the five FALSE DERIVED PRIVATE verdicts, produced by running the SHIPPED path unmodified** |
| **G8** | the critic's corrections re-measured — the UV operand (**calibrated 41/41 first**), the five direct reads, ef184 re-adjudicated, **the wall from the other side**, **the directory as residency**, and the order question reopened and still open |
| **G9** | provenance — an AST-level byte-constant scan over **every new file `git status` reports**, not a hand-written list |

**Siblings re-run unchanged — a failure there would have been a finding, not something to fix
quietly:** `w6b2_gates.py` **17/17** · `w6b_gates.py` **7/7** · `w6b2i_gates.py` **11/11** ·
`w6q_gates.py` **20/20**.

---

## PROVENANCE

What this rung commits is a **derivation, its gate and this record** — offsets, counts, tpage/clut
integers, cell coordinates, depths and effect ids, **never a stock byte string or a hex run of
container content**.

**THE COMMITTABLE SURFACE, NAMED EXHAUSTIVELY — TWO files, both in
`studies/custom-summons/tier-w/`**, so that a `git add -A` cannot sweep an unowned script into this
round's commit:

| file | owner |
|---|---|
| `w6b3_gates.py` | this synthesis — G0–G9 |
| `W6b3-ARCHIVE.md` | this record |

**Extended at W6b-3i (§11) — the integration's committable surface:** `w6b3i_gates.py` (I0–I11) ·
`W6B3I-PIN-DELTA.md` · the kit edits (`summons/reskin.py`, `summons/repaint.py`,
`summons/depth_attribution.py`) · the test edits (`tests/test_summon_reskin.py`,
`tests/test_summon_repaint.py`, this dir's `test_reskin.py`) · the amended boards (`w6b3_gates.py`,
`w6q_gates.py` G6b) · the declared narrowings (`w6b2_gates.py`, `w6b2i_gates.py`,
`w6b2_tpage_sweep.py`, `w6b2_census_restamp.py`, `w6b2_v1a_check.py`). All swept by the live
`git status` provenance gates (G9 + I11): 0 leaks, the two pre-existing benign literals adjudicated by
name on all four boards.

**THE CENSUS FREEZE (decided at W6b-3i):** `texel-w6b/census/pages.json` is **FROZEN, not re-stamped**
— the shipped census channel is incumbent-narrowed and byte-identical, so the artifact still describes
it exactly, and this record's 73/65/26 are deltas measured against that snapshot; re-stamping would
collapse the record's own subject to zero by construction. The freeze is verified every run by
`w6b3i_gates` I10 rather than trusted.

**Every lane script and every lane dossier stays OUTSIDE the checkout**, under
`C:\gd\SCRATCH\summon-format\texel-w6b\w6b3\` — the sweep, the join, both refuter suites and the
critic's seven probes, together with every JSON that carries decoded byte content. G9 asserts each
named dossier resolves outside the repo and scans every new text file `git status --porcelain`
reports against all 372 corpus containers: **0 byte constants of ≥ 6 non-uniform bytes found, 0
adjudicated, 0 unadjudicated leaks, 0 stock-shaped files added to the checkout.** `_ADJUDICATED` is
**empty** and stays empty unless a literal is named in it with its reason. `export.assert_local_only`
is asked to refuse a repo destination and does.

**RECON ONLY, honoured:** no kit code changed, no deploy, no game-install read or write, no
`Memoria.ini` or engine edit, no `git commit`. The corpus is read from `C:\gd\SCRATCH\summon-format`,
which is extracted from the user's own install and is not in the repo.

---

# 11. W6b-3i — WHAT SHIPPED (the kit integration)

> **Status: SHIPPED, offline.** §8's posture implemented; every number below measured through the
> SHIPPED code path (the moved-pin itemisation is `W6B3I-PIN-DELTA.md`; boards: `w6b3i_gates.py`
> 13/13 · `w6b3_gates.py` 10/10 amended · `w6b2i_gates` 11/11 · `w6b2` 17/17 · `w6b` 7/7 ·
> `w6q` 19/20 with both exceptions named below). NOTHING here is in-game; §9's residue stands whole.

**§8.2 item 1 — the reader fix, UNCONDITIONAL.** `so_record` reads the full multi-part array
(acceptance on `arrayB`, the independent halfword; `MAX_SO_PARTS` bounds a hostile blob; the P=0
record is still a record; the ef226 outlier kept by offset and value). The five FALSE `DERIVED
PRIVATE` verdicts repair to 0 — and the newly-armed guard set is EXACTLY those five palettes, asserted
as an identity. THE DEDUPE LAW ships with it: the verdict counts distinct GEOM **models**, never
binding slots (3 verdict-flipping + 2 count-only palettes, named).

**★ §8.2's ⛳ ASYMMETRY NOTE IS CORRECTED — the original stays visible above, per house rule.** It
says *"the fix makes the kit less conservative only in the `len(binders) == 1` branch."* **Measured
false:** the true record population also flips `so`-coverage COMPLETE on **19 containers**, which
would have silently released **122 palettes** from `acknowledge_shared` — 24× the repaired
population, in the permissive direction, on a channel with **0 in-game hits**. THE INTEGRATION DOES
NOT TAKE THAT RELEASE: coverage stays honest (502-based), and those palettes take the
`UNBOUND at COMPLETE so-coverage (NOVEL-DEPENDENT)` verdict with `shared = True` — **the guard stays
ARMED**. ⛳ **OPEN — OWNER DECISION: the 122-palette release** (ratify, or upgrade by a cast). The
46 palettes released by the private-flip are the safety fix's own direction (a palette with exactly
one named binder is private) and DID ship.

**§8.2 item 2 — CHANNEL A (`so-array`) DISCLOSES**, behind `acknowledge_array_derived_depth` + a
matching `expect_bpp`, reasons naming the record offset and slot index as identification only; 65
cells (26 clean / 34 class-C / 7 program-write, overlap 2); **A is for ARRAY, not ARCHIVE**. The
containment is THE WITNESS PARTITION (incumbent ≡ pre-fix, 340/340 / 376/376 / 0 of 372 differing);
census and channel G are narrowed at ten grep-findable call sites and their scopes are byte-identical.
The ORDER clause ships UNMEASURED: `parts` is a SET everywhere, display keys tie-break on values,
the direct-read refinement (§7 finding 3) and §8.3's cast shortlist stay study-side, and a
permutation-invariance gate (I8b, no carve-outs) proves no verdict consumes storage order.

**§8.2 item 3 — the refusals, LITERAL COMPLIANCE.** All **12** archive-dual cells refuse
(`array-dual-depth`, derived live; the `incumbent == ∅` 8/4 structure printed as derivation, the
treatment uniform) and the **2** ef184 cells refuse (`array-vs-column-depth`), withdrawing their
licensed pages. **The measured cost of the literal reading, stated rather than absorbed:** licensed
addressability −6 / census 0 — and one of the four covered withdrawals is `ef179 cell.s0.x448_y256`,
**a W6q paint vehicle**, so `w6q_gates` G6b was amended to pin the withdrawal by name (any other
withdrawal still goes red). The softer treatment considered and NOT shipped — hazard stated alongside,
page kept, cost −2 — is documented in the design record and remains ⛳ **owner-ratifiable** if the 4
covered cells should return.

**§8.2 item 4 — class-C for the 34** at the depth's own granularity, binder-derived (the census flag
is reader-derived and vacuously 0 here — printed beside the real answer), every key named, an
alternate PNG per key.

**Inherited finding, not this rung's:** `w6q_gates` G16's creature mean-covered-fraction pin
(0.640 ± 0.001) measures 0.644309 **at HEAD too** (A/B with the three kit modules restored: identical
digits) — stale before this integration, previously masked by G6b's abort. Left red and named; owner
call. **Resolved since:** the cause is the QUAD-ORDER Z-fan fix (kit `6ed66133`), which landed on
master after the W6q board was pinned on the recon lane and rode this very merge (`a3c16bcd`); the
perimeter fan re-measures 0.640017 in A/B. Re-pinned **0.6443** — `QUAD-ORDER-DELTA.md` §6,
`w6q_QUANTIZE.md` §4 item 3.
