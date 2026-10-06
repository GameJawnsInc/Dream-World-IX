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
