# W6B3I-PIN-DELTA — every pin the W6b-3i integration moved, and every one it deliberately did not

> **The `QUAD-ORDER-DELTA.md` shape: a provenance record for moved numbers, not a narrative.** The
> integration is `W6b3-ARCHIVE.md` §11; the design + its binding addendum live in the session records.
> Every value below was measured through the SHIPPED code path over the 372-container corpus before it
> was pinned; nothing was carried from the recon dossiers on trust.

## 0. The calibration line first

**THE WITNESS PARTITION IS EXACT.** The fixed `reskin.so_record`, filtered to the INCUMBENT witness
(`P <= 1`), reproduces the pre-W6b-3 population **tuple for tuple: 340/340 bindings, 376/376 accepted
records, 0 of 372 containers differing** (`w6b3i_gates.py` I0). Every consumer narrowed to that witness
is therefore byte-identical **at its input** — which is why the census and channel G rows below read
UNCHANGED, and why a leak anywhere would light I4 rather than hide.

## 1. Moved pins, old → new

### `ff9mapkit/tests/test_summon_reskin.py`
| pin | old → new | note |
|---|---|---|
| `(total, len10, textured)` | (376, 340, 339) → **(502, 340, 465)** | `len10` (P==1 records) is INVARIANT at 340; `tpage_bearing == 466` added; the incumbent triple (376, 340, 339) KEPT as the containment rung |
| `so_record` docstring count | "339" → **"465"** | the ef226 outlier literals (`0x9c804`/`0x9c7f4`/`0x97`/`0x3e00`) all kept by offset AND value |
| `off_n / on_n` | 316 / 340 → **580 / 649** | under the new `WITNESS_ALL` default |
| `(direct, effects)` | (24, 12) → **(69, 17)** | ditto |
| `[b for b in a1.bindings if not b.direct] == a0.bindings` | **UNCHANGED** | still holds container-for-container under `WITNESS_ALL` |

### `ff9mapkit/tests/test_summon_repaint.py`
| pin | old → new | note |
|---|---|---|
| CENSUS half of the W6b-1/W6b-2 block (187 / 2,385 / hazards 17/25/93/36/36/24) | **UNCHANGED, byte-identical** | the containment's headline; pinned as such |
| LICENSED `so-uv` served | 187 → **183** | −4 = the covered `array-dual` cells (ef179 x448_y256, ef186 x576_y256/384) + ef184 x448_y256 |
| LICENSED `so-page` served | 57 → **55** | −2 = ef184 x448_y256/384 (`array-vs-column-depth`) |
| LICENSED depth-unknown | 2,298 → **2,290** | −8 = the ∅-incumbent `array-dual` cells, renamed to their real refusal |
| LICENSED closure | `238+2290+22+8+12+2 = 2,572` | two new refusal buckets; identity holds |
| licensed hazards: multi-palette / shared-read | 32 → **30** / 93 → **90** | emission-surface only; census twins unmoved |

### `studies/custom-summons/tier-w/w6b3_gates.py` (the board whose SUBJECT is the delta)
| pin | old → new | class |
|---|---|---|
| G2 "kit-blind records" | 126 → **0 shipped / 126 legacy** | INVERTED; `_LEGACY_SO_RECORD` (the retired 9-line reader, frozen in-gate) keeps the historical predicate non-vacuous |
| R3 / R4 | kept **against the legacy copy** (340/340, 376/340) | + new rungs pinning the shipped reader at **502 / 466** |
| `n_private / n_shared / n_unknown` | 107 / 87 / 2,600 → **148 / 129 / 2,395** | through the shipped `palette_map` |
| UNBOUND-at-COMPLETE | 301 → **301 + 122 NOVEL-DEPENDENT (guard ARMED)** | the A1 split; total 3,095 identity holds |
| FALSE PRIVATE | 5 → **0** | INVERTED; the five historical names kept and printed |
| SHARED-UNKNOWN gaining a binder | 83 → **split 46 PRIVATE + 37 SHARED** (by model; 43+40 by slot, printed beside) | |
| `complete_flips` | unwired → **wired: 19 containers by name** | |
| self-shared / count-only dedupe classes | — → **3 / 2** (named) | ADDED |
| G0 KA limit, G1, G3–G8, G9 | **UNCHANGED** | downstream of the frozen instruments |

### `studies/custom-summons/tier-w/w6q_gates.py` (amended, not re-pinned)
G6b no longer calls the licensed resolver bare: `_author_surface_withdrawals()` re-derives the
channel-A-withdrawn set live each run, G6b sweeps the still-addressable surface (**15/15 byte-exact**)
and **pins the withdrawal by NAME** — `ef179 cell.s0.x448_y256`, `ef184 cell.s0.x448_y256`,
`ef186 cell.s0.x576_y256`, `ef186 cell.s0.x576_y384` — asserting every withdrawal's class is channel
A's. A different cell, or a non-channel-A class, goes RED instead of aborting. +80 lines, 0 deletions,
0 pin values re-aimed; §1.4's `len(cc)==16` untouched with the reason in place.
**G16 is left RED on purpose**: `creature mean covered fraction` measures **0.644309** against its
0.640 ± 0.001 pin — **pre-existing at HEAD** (A/B: the kit's three edited modules restored from HEAD
give the identical 0.644309; every other G16 row green both ways). It was masked only because the board
died at G6b first. A W6q-dossier number; owner call; not this rung's to re-pin.
**Since resolved:** the cause is the QUAD-ORDER Z-fan fix (kit `6ed66133`, perimeter → Z fan) riding
the `a3c16bcd` merge — the recon lane pinned 0.640 against the old fan (A/B at the re-pin: old fan
0.640017, Z fan 0.644309; 37/93 pages gain, 0 lose, +6,539 texels). Re-pinned **0.6443**; provenance
`w6q_QUANTIZE.md` §4 item 3 and `QUAD-ORDER-DELTA.md` §6.

### `studies/custom-summons/tier-w/w6b2i_gates.py`
**Every pin VALUE unchanged — 11/11** via `W6B2_CHANNELS = LICENSED_CHANNELS − {"so-array"}`, declared
at the top with its reason: the board measures **W6b-2i's shipped surface**, a historical instrument,
and freezing its channel set is the same discipline as `_LEGACY_SO_RECORD`. Its census tripwire (187)
passes on the live default — the containment proof, not a freeze. `_ADJUDICATED` mirrored (the two
pre-existing benign literals the other three boards already clear by name).

### `studies/custom-summons/tier-w/test_reskin.py`
**No pin moved** (every fixture is P=1); an explicit incumbent-invariance rung added instead.

## 2. The four corrections to the design's own input maps
1. Post-fix verdicts are **148/129**, not 145/132 — the verdict counts distinct GEOM **models**, never
   binding slots (3 palettes flip back under the dedupe).
2. The 83's split is **46 + 37** by model (43 + 40 by slot — both measured, both printed, the first ships).
3. **THE SELF-SHARED CLASS (3 palettes)** — one model, two entries, one palette, sole binder: slot-counting
   would publish "2 GEOM models" about one.
4. **THE COUNT-ONLY CLASS (2 palettes)** — verdict right, printed count wrong by one without the dedupe.

## 3. What deliberately did NOT move, and why
- **Census scope: 187 / 2,385 and every census hazard** — `bound_models` and the census walk are
  incumbent-narrowed at the call site; byte-identical, pinned by I4 and `w6b_gates` 7/7 (control, untouched).
- **Channel G's own derivation** — `page_depth_view` default INCUMBENT; `w6b2_gates` 17/17 untouched
  except two declared narrowings; the licensed-path 57→55 is the ef184 REFUSAL displacing emission,
  not a change to G.
- **`GAIN_SO_PAGE` (57), `CHANNEL_G_DUAL_CELLS` (8), `REFUSED_AMBIGUOUS` (32), `RESIDUE_LINE`,
  `GAIN_EITHER == 246` and every import-time assert in `depth_attribution.py`** — W6b-2's arithmetic
  still describes W6b-2's channel set exactly; the shipped surface's −6/−8 is carried by
  `DA.A2_SCOPE_NOTE`, quoted at `W6B_REASON` and the live channel-G disclosure, and all of them are now
  **re-derivation-pinned** (I9) instead of self-consistently asserted.
- **`w4/w5/w6/w7/w6b/w6q(≠G6b,G16)` gate pins and the three cast-proven CLUT artifact shas** — no
  bytes-out path was touched (verified by review: the whole change is read-side).
- *A frozen number with a stated reason is evidence; a frozen number with no reason is a stale pin.*

## 4. The narrowing sites (all findable: `grep -rn "witness=" ff9mapkit/ studies/`)
Kit: `repaint.bound_models` · `reskin.page_depth_view`. Study: `w6b2_gates` :355 and :1368 (the ef390
roll — found by measurement, missing from the design) · `w6b2i_gates` :249 · `w6b2_tpage_sweep` :295 ·
`w6b2_census_restamp` :223 · `w6b2_v1a_check` :412 · `w6b3_gates` F2/F3 freezes. Deliberately
un-narrowed, each with its printed reason: `w6b2_gates` KA1 (ef211 holds 0 multi-part records — the
calibration stays a genuine re-read), `w6b3_gates` colclut union (invariance asserted, not assumed),
`w6b3_gates` G7's `palette_map` default (the site whose pins are SUPPOSED to invert).

## 5. The census artifact
`texel-w6b/census/pages.json` is **FROZEN, not re-stamped** — the shipped census channel is unmoved, so
the artifact still describes it exactly, and the recon's 73/65/26 are deltas measured against this
snapshot. The freeze is **verified every run** (I10), not trusted.

## 6. The counterfactual record
The naive-fix leak (channel G widened to ALL: page origins 122→162, single-depth 108→141, dual 14→21;
the census gaining the novel covers) is re-measured live by I4's B-half each run — the durable form of
the A/B, kept as a gate rather than an archived file. The licensed-path addressability counterfactual
is I6's: **−6 shipped / 0 census**, with the considered-and-refused softer treatment's **−2** printed
beside it.
