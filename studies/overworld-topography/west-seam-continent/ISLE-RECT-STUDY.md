# The isle rect study — can Daguerreo (the horseshoe's home island) be carried at all, and to where?

Registered 2026-10-06 BEFORE the instrument (`isle_rect_study.py`) existed or ran. Follows
[`HORSESHOE-ISLE-BENCH.md`](HORSESHOE-ISLE-BENCH.md), whose round stopped at the excise refusal.

## Prior art found AFTER the bench round (it should have been read before)

`studies/coast-shape-language/PALETTE.md` (guarded re-census, 2026-08-02) lists **"Confirmed not
carryable: Daguerreo (keeps 25, drops 1670)"**. That is this island and this exact refusal.
- `DESIGN-MENU.md`: "We can carry the pattern; we cannot carry Daguerreo."
- `EXCISE-PREDICTION.md`: "its own land crosses the rect frame, so it is not an excise case at all."
- The superseded palette table records `(5,14)+3x4` Daguerreo failing ONLY `weld-audit`, on 1 pair. It
  is the one larger rect ever dry-run. That was before the carried-subject guard existed, so its carried
  terrain was never read.

**The mechanism, from the code** (`transplant.excise_plan`): land-fit and excise judge crossing on LAND
within `land_margin` (2u) of the frame. Daguerreo's land runs z −962..−1086 (raster), i.e. within 2u of
BOTH z −960 and z −1088. So any rect whose z-range is exactly rows 15–16 sees the island as crossing.

## Questions

**Q1 — THE RECT.** Run `excise_plan` (the builder itself) for each candidate around the island:
- sizes 3×2, 3×3, 3×4, 4×3, 4×4;
- anchors covering x 320–512 and rows 14–17 (all anchors whose rect contains the island's raster bbox);
- per rect, report: refused or not, kept vs dropped land, and the foreign assemblies dropped.

Every rect that keeps the island is then `--dry-run` with `--shift 0,0` against an open-ocean target of
its size (any such target; a dry run writes nothing). Report each gate and the `carried: terrain:N`.

**Q2 — THE TARGET.** Enumerate every open-ocean window (no stock parts, no `FF9CustomMap-world`
overrides) of each needed size on the 24×20 grid, and rank by block distance to our continent.
**Read in `transplant_region` whether a target rect may cross the x-seam (col 23→0) or the z-wrap
(row 19→0)** before counting any wrapping window.

**Q3 — THE WELD PAIR.** For the best rect, locate the weld-audit pair(s). Then run the same audit on the
donor's OWN stock bytes, untranslated, to settle whether the pair is inherited from stock or introduced
by the carry.

## Registered predictions

- **P-R1.** No rect with fewer than 4 rows keeps the island. The smallest that does is `(5,14)+3x4`
  (rows 14–17).
- **P-R2.** At 4 rows, at least one foreign mass in rows 14 or 17 crosses the new frame. Excise either
  drops it cleanly or refuses (if it owns a shallow ladder). Prediction: at least one candidate 4-row
  rect excises cleanly and keeps the island (kept land > dropped).
- **P-R3.** No 3×4 open-ocean target window touches our continent's block ring without crossing a
  wrap. If the verb accepts no wrapping target, the nearest lawful window is ≥ 2 blocks from our
  continent.
- **P-R4.** The `(5,14)+3x4` weld pair is INHERITED (present in the donor's own stock bytes).

## What each outcome means

| outcome | means |
|---|---|
| no rect keeps the island and passes the gates | Daguerreo is uncarryable as a whole island with today's verb; (c2b) is dead. Back to the owner: (c2a), (d), or another island |
| a rect passes, and a target exists by our continent | re-register the bench round with that rect, target and `--shift 0,0` |
| a rect passes, but the only targets are far away | (c2b) works only as a distant island; the owner decides whether that is still R4 |
| the weld pair is introduced | it is a carry defect to diagnose before any build |
| the weld pair is inherited | the gate needs the donor-baseline subtraction (the no-introduced-misses pattern), not a geometry fix |

## RESULT

(appended after the run, below this line; nothing above edited)

Run 2026-10-06 (`isle_rect_study.py`, data `isle_rect_study.json`). Read-only; no dry run was reached.

### The registered score

| | measured | verdict |
|---|---|---|
| **P-R1** a 4-row rect keeps the island | **NO rect keeps it.** All 16 candidates (3×2, 3×3, 3×4, 4×3, 4×4 around the island) are refused by the carried-subject guard: kept 25–61 land tris vs dropped 1,670–5,134 | **FAILS** |
| **P-R2** a 4-row rect excises cleanly | none does: in every rect the island sits inside the frame-crossing assembly | **FAILS** |
| **P-R3** no wrap-free 3×4 target by our continent | the only 3×4 open window on the grid is (0,12), 3 blocks away; no 4×4 exists. The verb refuses wrapping targets (`transplant_region`: 0 ≤ bx, bx + w ≤ 24, likewise rows) | **HOLDS** |
| **P-R4** the weld pair is inherited | not reached (no rect got to a dry run) | — |

**Open windows by size** (no stock parts, no `FF9CustomMap-world` override; distance in blocks to our continent):

| size | windows | nearest |
|---|---|---|
| 3×2 | 11 | (19,1) / (20,1) / (21,1) at d 2 |
| 3×3 | 5 | (19,0) / (20,0) / (21,0) at d 2 |
| 4×3 | 2 | (19,0) / (20,0) at d 2 |
| 3×4 | 1 | (0,12) at d 3 |
| 4×4 | 0 | — |

### The mechanism, verified (post-registration, not scored)

Components were taken the way `excise_plan` takes them:

- **On land alone, the island is a separate mass:** 1,448 land tris, x 326.6..460.0, z −1086.3..−962.9.
  In the 3×4 rect `(5,14)` it does NOT reach the frame. In 3×2 and in 4×4 `(4,13)` it does, by the 2u land
  margin: its land comes within 1.3u of z −1088.
- **With the shallow-water parts included, its assembly holds OTHER land:**

| rect | island assembly | other land masses in it | one that crosses the frame |
|---|---|---|---|
| 3×2 `(5,15)` | 2,376 tris | 2 masses | 27 tris at the north frame |
| 3×4 `(5,14)` | 4,326 tris | 6 masses (1,063 tris) | 546 at the north, 131 at the south, 86 at the west |
| 4×4 `(4,13)` | 7,003 tris | 6 masses (2,837 tris) | 1,842 crossing |

So Daguerreo is one member of an archipelago that shares a single continuous shallow ladder. The verb's
excise unit is the assembly, so it cannot drop the neighbours without dropping the island. Separating them
means cutting a shallow sheet. That is THE STRICT SHORE / SHALLOWS-ARE-SHORE-BOUND class, and excise v2
named it ("rebuilding a ladder is the v2 job, and it is a genuinely bigger one") and never solved it.

This upgrades the palette's verdict ("Confirmed not carryable", recorded without a mechanism) with the
mechanism: **the island is separable on land and entangled through its water.**

### What it means

- **(c2b) as registered is not buildable with today's verb.** No rect carries the island, and no 4-row target
  exists near the continent anyway.
- **To make it buildable needs a NEW capability: a ladder-aware excise.** Drop the neighbours' land and
  their exclusive ladder, keep the shared shallows around the island, and re-tile the cut through the
  learned Wang table (the `strips_rebuild` / `world-rim-retile` machinery). It is a research arc with its
  own registered rounds, and its outcome is uncertain.
- **The carryable palette already holds whole-island mountains:**
  - Uaho `(0,0)` 1×1: 1,584u², relief 8.9, carried clean with no excise;
  - the comma `(9,5)` 2×3: relief 19.1.
  Uaho is R5's planned donor, and its bare carry passed in July.
