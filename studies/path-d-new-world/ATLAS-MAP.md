# THE ATLAS MAP (study angle 4) — the terrain atlas decoded from stock usage

> Registered in VSHORE-SEAL-PREDICTION.md "STUDY ANGLES" §4; built 2026-08-02
> after the seam-forensics round (the band-bottom poison measurement during the
> apron retexture was this study's first ad-hoc deliverable — now systematic).

## Method

`atlas_map.py` scans every stock disc-1 Terrain face (260 blocks) and clusters
the uv rectangles stock ACTUALLY binds — no atlas-image guessing:

- **WALL bands** (|ny| ≤ 0.35): keyed by their v-pin pair (walls sample thin
  horizontal atlas strips pinned between two v rows).
- **GROUND fields** (|ny| ≥ 0.7): keyed by topo class (grounds tile large
  regions; reported at p1–p99 of usage).

Each entry annotated from the atlas itself: mean RGB + **alpha-0 fraction**
(alpha-0 renders WHITE in-game — the blank-tile law). Queryable table:
`atlas_map.json` (committed).

## Headline decode (57 wall bands, 31 ground fields)

| band | v range | u range | topo | look | faces |
|---|---|---|---|---|---|
| highland-dirt lip | [0.872,0.902] | [0.428,0.676] | 58 | brown (124,89,69) | 2905 |
| grass lip | [0.893,0.923] | [0.699,0.947] | 58 | grey-green rock (107,114,106) | 2077 |
| forest wall | [0.908,0.938] | [0.112,0.656] | 37/36 | dark green (89,92,62) | 1581 |
| desert wall | [0.566,0.597] + [0.535,0.566] | [0.222,0.781] | 38 | tan | ~980 |
| snow/ice wall | [0.944,0.975] | [0.004,0.507] | 59/58 | pale blue-white (154,170,181) | 443 |
| canyon walls (many rows) | [0.27–0.43] | [0.004,0.252] | 49 | red-brown | ~1200 |

Ground fields: the big topos (0/49/17/19/…) each span wide u/v regions with
**5–10% alpha-0 poison INSIDE the usage rect** — ground fields are tile
mosaics with blank gaps, so a rect query is NOT a safety proof; per-footprint
texel validation (the translate-clone validator) remains mandatory for ground.
Wall bands are clean (0% poison in every major band).

## The laws this bakes in

- **The band-bottom poison** (measured during the apron retexture): rows just
  BELOW the grass-lip band (v > 0.9229) are white / 34% alpha-0 — continuing a
  wall band past its stock pin is the white-sliver class. **Never extrapolate
  past a band's stock v-pin; fold back or stop.**
- The grass-lip band's bottom row (v=0.9229) is the dark waterline row —
  stock ends every grass-family wall exactly there.
- The lip-family discriminant (grass vs highland-dirt) is now one JSON lookup
  instead of a re-census.
- Validation recipe for any new WALL uv assignment: its (v_lo,v_hi,u) must
  match a stock band row in `atlas_map.json` (same pins, u within band); for
  GROUND: full texel-footprint rasterization against the atlas (no shortcut).
