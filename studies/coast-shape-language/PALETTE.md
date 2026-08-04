# THE PALETTE — guarded re-census, 2026-08-02 (SUPERSEDES everything below)

**7 masses carry real land.** Every row measured by mass-attributed carried terrain, with
`excise_plan`'s carried-subject guard active; the three previously-unconfirmed rows were
then verified against the game with a real `--dry-run`.

| donor | size | area | relief | walk | carries | |
|---|---|---|---|---|---|---|
| `(9,5)` | 2x3 | 5312u² | **19.1** | 0.67 | **917** | the comma — DEPLOYED |
| `(6,6)` | 2x2 | 3616u² | 8.2 | **0.79** | **578** | the isthmus — DEPLOYED, excise-only |
| `(6,4)` | 2x2 | 2592u² | 6.9 | 0.00 | 551 | the crystal reef, unlandable by design |
| **`(0,0)`** | **1x1** | **1584u²** | **8.9** | **0.61** | **406** | **new — a clean single-block carry** |
| `(7,17)` | 4x2 | 2080u² | 5.0 | 0.76 | 314 | the island chain |
| `(6,4)` | 1x2 | 544u² | 8.0 | 0.00 | 113 | reef fragment |
| `(17,16)` | 2x1 | 736u² | 3.3 | 0.70 | 108 | small |

`(0,0)` is the find: **1584u², 61% walkable, 406 triangles out of ONE block, gates clean,
no excise needed.** Earlier censuses missed it because they required ≥500u² *and* applied a
clearance test that the map-corner block fails.

**Confirmed not carryable:** Daguerreo (keeps 25, drops 1670), the sinuous island (keeps 0),
the `(14,0)` crescent (5 interior waterline verts), and four continents too big for any rect.

## Excise's honest scorecard

Of the 7, **one** — the isthmus — needed excise at all. The other six carry clean without it.
Excise cost two traps (ring-cut, carried-subject) and three wrong palettes. What it bought
that lasts is the **guard**, which is now load-bearing for every carry, excise or not.

## THE INSTRUMENT LAW

Three censuses, three faults, each caught by a number that was internally consistent but
IMPOSSIBLE — never by reading the code:

1. **one rect per mass, never retried** → Daguerreo "unavailable" when another rect held it.
2. **credited a mass with any land in the rect** → mass 9 (544u²) reported 798, the reef's
   own number, for a mass a fifth its size.
3. **double-offset coordinates** (`world_tris` already returns world coords) → the palette
   collapsed to exactly one mass, and it was the one at block `(0,0)`, where the offset is
   zero.

Every fault moved the headline the same way — fewer real carries than claimed: 16 → 10 → 4
→ 7. **A census is an instrument, and an unfalsified instrument is a hypothesis.** The rule
that now applies: no palette figure is quotable until the rows are verified against the game
by `--dry-run`, and `carried: terrain:N` is read on every one.

---

# (superseded) THE PALETTE — what we can carry, verified (2026-08-02)

> ## ⚠ CORRECTION 2026-08-02 — the table below was WRONG. Read this first.
>
> The "10 verified" figure counted rects that passed every gate. **Six of them carried a
> crumb or nothing at all**, because no gate asks whether the island you wanted is still in
> the carry. Measured `carried: terrain:N` per row:
>
> | rect | carried | verdict |
> |---|---|---|
> | `(9,5)` 2x3 comma | **917** | real |
> | `(6,4)` 2x2 reef | **798** | real |
> | `(6,6)` 2x2 isthmus | **578** | real |
> | `(7,17)` 4x2 chain | **504** | real |
> | `(6,4)` 1x2 | 177 | small |
> | `(17,16)` 2x1 | 126 | small |
> | `(7,16)` 2x2 | 23 | **crumb** |
> | `(5,15)` 3x2 **Daguerreo** | 25 of a 9264u² island | **crumb** |
> | `(3,11)` 2x4 **the sinuous island** | **0 — pure ocean** | **EMPTY** |
> | `(7,17)` 2x1 · `(16,16)` 2x1 | 0 | **EMPTY** |
>
> **So excise has unlocked exactly ONE landmass: the isthmus.** Daguerreo and the sinuous
> island are NOT carryable — the claim that excise made them so was wrong, and it survived
> because "gates CLEAN" was read as "the carry worked". The real palette is four masses,
> three of which needed no excise at all.
>
> Guarded now: `excise_plan` refuses when a carry keeps no more land than it drops
> (`keep_largest=True`, the default). Calibrated on every case above; a kept-FRACTION
> threshold was tried first and falsified.


Every row below was run through a real `--dry-run` against the live install. The offline
shortlist is not quotable on its own: 16 rects were predicted, **10 verified**.

## Verified carryable — 10 masses

| donor | size | area | relief | walk | how |
|---|---|---|---|---|---|
| `(9,5)` | 2x3 | 5312u² | 19.1 | 0.67 | clean — **deployed as the Fraying Tail anchor** |
| `(6,6)` | 2x2 | 3616u² | 8.2 | 0.79 | excise 43 cells — **the waisted isthmus** |
| `(3,11)` | 2x4 | 3584u² | 5.9 | **0.87** | excise 180 cells — **the sinuous S-curve** |
| `(6,4)` | 2x2 | 2592u² | 6.9 | **0.00** | clean — the crystal reef, *unlandable by design* |
| `(7,17)` | 4x2 | 2080u² | 5.0 | 0.76 | clean — the island chain |
| `(7,16)` | 2x2 | 1120u² | 6.9 | 0.84 | excise 50 cells |
| `(7,17)` | 2x1 | 864u² | 3.4 | 0.85 | excise 44 cells |
| `(17,16)` | 2x1 | 736u² | 3.3 | 0.70 | excise 26 cells |
| `(16,16)` | 2x1 | 544u² | 3.1 | 0.74 | excise 53 cells |
| `(6,4)` | 1x2 | 544u² | 8.0 | 0.00 | excise 61 cells |

**Plus Daguerreo** — see the census bug below — so the real figure is **11**, against 7
before excise.

## What failed, and why each failure is different

* **`(5,14)` 3x4 Daguerreo — `weld-audit` FAIL (1 pair).** But **`(5,15)` 3x2 carries the
  same mass and gates fully CLEAN** (verified). So Daguerreo *is* in the palette; the
  census simply picked the wrong rect for it.
  **THE CENSUS BUG: one rect is chosen per mass, by least excise, and never re-tried.**
  A mass whose best-by-excise rect fails is reported as unavailable even when another rect
  carries it. The verified count is therefore a FLOOR, not a total.
* **`(14,0)` 4x3 — excise refused, 5 interior waterline verts.** The genuinely-interior
  case the frame fix deliberately does not cover. This one hurts: 8624u², 78% walkable,
  and the most distinctive silhouette in the pool (a swept crescent — a long tapering west
  arm opening into a broad east body). **The single highest-value target for excise v3.**
* **`(4,13)`, `(3,15)`, `(2,10)`, `(5,14)` 2x2 — "every assembly crosses the frame".**
  The offline clearance test works on the 4u cell bbox; the real one works on mesh vertices
  and is stricter. Over-prediction in the census, not a capability gap.

## Reading the palette

Relief is what carries the horizon at the game camera (the outline census measured this;
plan shape does not read). On that axis the pool is thin: **only `(9,5)` at 19.1 has real
vertical presence**, and it is already deployed. Everything else is 3–8u — low, flat land.
Daguerreo (23.5) is the one untapped high-relief mass, which is a second reason to prefer
its `(5,15)` rect.

`(6,4)`'s **walk 0.00** is not a defect: the crystal reef is unlandable in stock too. It is
the pool's only pure-scenery object — useful precisely because you sail past it.

---

## THE RING-CUT TRAP — playtest of the isthmus, 2026-08-02

**Verdict: walkable, renders, shape reads.** Criteria 1–3 and 5 pass. One real artifact,
and one thing I got wrong.

### What I got wrong: the Wang advisory

I relayed the gate's "18 cropped-Wang frame seams" as something the owner would see at the
island's rim. The owner checked and **the land edge has working transition tiles against
that depth** — the advisory says an adjacency is unusual, not that it renders wrong. Passing
a gate's advisory along as a visual prediction is a category error; the gate scores
element-vs-marginals and has never had an opinion about pixels.

### The real artifact: the shallow ring is CUT at the rect frame

The deployed sheets are byte-faithful to stock — normal constant `(-0.121, 0.979, 0.167)`,
all-negative winding, identical tri counts. Nothing is malformed. What is wrong is the
carry's EXTENT:

| stock shallow tris (sea1/2/3/5) around donor `(6,6)+2x2` | |
|---|---|
| inside the rect | `(6,6)` 391, `(7,6)` 247, `(6,7)` 0, `(7,7)` 6 |
| **north, OUTSIDE the rect** | **`(6,5)` 278, `(7,5)` 16** |

**294 triangles of shallow water continue north past the rect frame and were cut.** The
island's ring therefore terminates along straight block-frame lines in open ocean — a hard
sea3→sea4 edge with no ladder, which from water level reads as a plate standing in the sea.

### THE RING-CUT TRAP: a BIGGER rect can destroy the carry

The obvious fix — enlarge the rect to contain the ring — **fails, and destructively**:

| rect | carried terrain | dropped terrain | wang |
|---|---|---|---|
| `(6,6)+2x2` (shipped) | **578** | 109 | 18 incoherent |
| `(6,5)+2x3` | **34** | 1003 | 0 incoherent |
| `(5,5)+3x3` | **34** | 1590 | 0 incoherent |

Because **excise's unit is the ASSEMBLY — island plus its welded water ring** — enlarging
the rect enlarges the assembly, which then touches the *new* frame, is classified foreign,
and is dropped. The island is excised and a 34-triangle crumb is carried in its place.

**And every gate goes GREEN while this happens** — `wang-carry incoherent=0`,
`weld-audit pairs=0`, `census miss=0 introduced=0`, `dry run: gates CLEAN`. The gates score
what was carried; none asks whether the thing you wanted is still in it. A carry that drops
its own subject is indistinguishable, gate-wise, from a clean one.

**Guard needed:** compare carried terrain against the target mass's known tri count and
refuse when the carry loses its subject. Until then, read `carried:` on every excise run.
