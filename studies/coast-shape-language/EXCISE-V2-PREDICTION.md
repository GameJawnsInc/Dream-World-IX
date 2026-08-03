# EXCISE v2 — the refusal reason was WRONG (registered + scored 2026-08-02)

## What v1 said

```
--excise refused: 39 waterline vertex/vertices of the excised assembly do not lie on the
deep sheet -- the mass owns a shallow-water ladder, which excise v1 does not re-zip.
```

That reads as: *the excised island owns a ring of shallows, and filling its footprint
means rebuilding a water ladder.* Rebuilding a ladder is expensive and touches
THE SEA-SHEET LAWS, so the capability was priced as a large round.

## Measured before building anything

Both rects the refusal was blocking, classified by where each weld-missing vertex sits:

| donor rect | weld-missing | ON THE RECT FRAME | interior sheet hole | welded to a KEPT assembly |
|---|---|---|---|---|
| Daguerreo `(5,15)+3x2` | 39 | **39** | 0 | 0 |
| sinuous island `(3,11)+2x4` | 41 | **41** | 0 | 0 |

**100% of them lie exactly on the rect frame. Not one is an interior hole, and not one is
welded to the island being carried.** The independent per-assembly probe
(`excise_v2_probe.py`) agrees: across all three blocked rects, the class
*"welded to a KEPT assembly"* never occurs — the excised ladder is never bonded to the
mass we keep, so no shared surface ever has to be cut.

The ladder *was already being dropped* — v1 takes components over every part except sea4
(`dropped={'terrain': 1670, 'sea3': 550, 'sea5': 262}`). The failure was never the ladder.
It was that the excised mass's ladder **runs out to the rect frame**, so sea4 has no
vertex there to weld to — and it should not have one. Beyond the frame is the neighbouring
cell's ocean, which the region's own border re-partition and the prefab handle.

**A waterline vertex on the rect frame needs no sea4 partner inside the rect.**

## The change

One predicate: in THE EXACTNESS GATE, a non-sea4 waterline vertex lying on the donor
rect's outer frame is legitimate (counted as `frame_waterline`) instead of a weld failure.
Genuinely interior misses still refuse.

## Predictions

* **E-1** Both blocked rects reach `weld_exact=True`. **CONFIRMED** — and `frame_waterline`
  41 / 39.
* **E-2** The fill is geometrically sound, not merely un-refused: the placement census
  stays clean. **CONFIRMED** — `census: miss=0 inherited=0 introduced=0` on both
  (3456 and 4608 samples), and `border-census: holes=0`.
* **E-3** No regression on the crumb case v1 already handled. **CONFIRMED** — the waisted
  isthmus rect `(6,6)+2x2` still gates fully CLEAN.
* **E-4** Interior holes must still refuse. **CONFIRMED**, and mutation-verified: making
  `_on_frame` return `True` unconditionally is caught.

---

## FINDINGS — a real advance, and an HONEST residual

**The diagnosis was the deliverable.** A refusal that named the wrong cause had priced
this capability as "rebuild a water ladder" when the actual fix is one predicate about
the rect frame. Both large rects now build a sound fill.

**But they do not yet ship.** With `weld_exact` satisfied, both hit a *different* gate:

```
(5,15)+3x2   GATE weld-audit: pairs=4  frame_pairs=0  border_t_pairs=0 -> FAIL
(3,11)+2x4   GATE weld-audit: pairs=1  frame_pairs=0  border_t_pairs=0 -> FAIL
```

Localised precisely, one pair being `d=0.0239` apart:

```
a (37.705882, 0.0, -64.0)
b (37.729736, 0.0, -64.0)
```

Both at **y=0 (water level)** and **z=-64 exactly — an interior block border of the target
region**. Neither vertex exists in the donor's stock parts *or* in the emitted fill: both
are created by the region's border re-partition. And the fill itself is clean — measured
against every surviving part and against itself, **zero** near-misses.

So the residual is not in the fill. Two edges cross the interior border at slightly
different x, and the re-partition splits each at its own crossing. That is the
DENSIFY-FIRST class: two surfaces sharing a boundary must be built on ONE chain. It is a
distinct defect from the one fixed here and deserves its own measured round rather than a
tail-end guess — this arc's record on "one more quick geometry fix" is poor.

**Status: the frame diagnosis and fix are shipped and covered; the two large laddered
rects are one border-crack round away.** The gate refuses them, so nothing unsound can
ship in the meantime.

### Coverage

Both directions mutation-verified. The first pass MISSED the frame law entirely (the fix
had no call-site test — the third time today), and the negative direction was added only
after a second mutation showed `_on_frame -> True` passing the whole suite.
