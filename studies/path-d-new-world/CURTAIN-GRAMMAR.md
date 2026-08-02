# CURTAIN GRAMMAR — how stock SEALS a surface edge to lower ground (questions registered BEFORE the instrument ran)

2026-08-01. The walkability round closed with one open defect, owner-confirmed twice
(LAWN-CLIP-PREDICTION.md, "THE V-SHORE GAP, measured"): the carried wall HOVERS
1.5-3.2u over the descending shore at the two coast crossings — east (448.8,−507.8),
11 once-edges / 22u; west (382.4,−511.6). Mechanism known: `fits_bench` clips the
apron at the bench GRASS edge, so the carried skirt terminates mid-air exactly where
the bench shore descends below the lawn datum. The owner: *"i have a feeling it may
be complicated"* — and the site is where four systems meet (the carried wall, the
bench coast band, the sea sheets, the block-7 border).

Per the authorship law (GROUND-JUNCTION-SYNTHESIS.md: THE DEFECT FOLLOWS THE
AUTHORSHIP, 12/13) no fix is built before its grammar is measured. This seventh wall
study decodes the class no prior study asked about: **what stock ships where a
raised surface's edge sits over lower ground** — the sealing vocabulary — and then
classifies OUR two sites inside that vocabulary.

## What is already in hand (not re-derived here)

- **THE TAPER LAW** (ENDPOINT-GRAMMAR.md): 42/42 real wall crest endpoints taper to
  ground; a wall that "just stops" does not exist in stock. But that census measured
  walls ending ON GROUND — none of its endpoints was at a coast.
- **THE FREE-BASE LAW** (coast-mosaic, pillar D — measured on the COASTAL cliff
  class): ZERO face base edges map-wide land on walkable terrain; bases terminate
  FREE at/below the waterline. If wall-meets-coast resolves to this class, the fix
  is a descent, not a seal.
- **The blob curtain signature** (found during the underlay build, full_skirt.py
  ~1511): the carried forest blob's rim is closed by plan-degenerate vertical faces
  — every plan edge there has 3 owners, so the rim has NO once-edges. Donor bytes;
  the in-hand exemplar of a stock seal.
- **The 40° curtain regime** (GROUND-JUNCTION-SYNTHESIS, S1 surviving form): stock
  ground's uv vocabulary breaks at 40° — steeper faces leave the plan-budget rule.
- **THE BAND-CONTINUATION LAW** (the base-tile study): a wall's bottom band is the
  column's uv continuation, 100% seam-continuous — the candidate uv rule for a
  curtain.

## Questions — registered before running

**C1 — THE CURTAIN CENSUS (does a general sealing class exist?).** Across stock
disc-1 terrain blocks: every near-vertical face group (|geometric ny| ≤ ~0.2, i.e.
past the 40° break well into the curtain regime) OUTSIDE the two decoded wall
classes (topo-49 crest-seeded walls; the topo-58 coastal cliff strip). Per group:
what sits ABOVE its top edge and BELOW its bottom edge (surface class, topograph);
its drop height; its plan-owner signature (the blob's 3-owners-per-plan-edge — is
that the class invariant?); its texture family and topograph; its frequency by
context (forest rim / terrace edge / riverbank / plateau lip / shore). The census
must answer: **is "curtain" one class with one construction, or several?**

**C2 — THE CURTAIN UV RULE (what a mint would have to emit).** On the donor
exemplar (the (15,14) forest blob rim) and every C1 family: is the curtain's uv the
band-continuation of the surface above (THE BAND-CONTINUATION LAW's prediction), a
dedicated atlas strip (the coastal cliff's V-corner-role pattern), or the surface
BELOW's continuation? Plus the v-orientation (grows downward?), the tile rows used,
and whether the top edge pins to a painted lip row (the cliff-lip texel-row law's
analogue).

**C3 — WALL-MEETS-COAST (the site class our V-notch claims to be).** Census every
stock site where an interior rock mass (topo 49/50, the wall body class) comes
within ~8u plan of a sea/beach sheet. At each: does the rock BODY descend below the
waterline (THE FREE-BASE LAW generalizing to interior walls), does GROUND always
wrap the foot (the apron never ends before the rock does), or does a curtain seal
the junction? The frequency of each resolution, with drop heights and the ground
class present at the junction. **This is the discriminant question**: it decides
whether our sites are curtain sites at all, or apron-extension sites, or
descend-into-the-sea sites.

**C4 — OUR TWO SITES, MEASURED (the patient's anatomy before the prescription).**
On the deployed bench bytes: at each hover cluster, the exact carried boundary
chain (its verts, heights, and owner tris), the bench surface below (class,
topograph, descent profile from the lawn datum to the waterline), the plan gap
between the carried edge and the nearest bench once-edge, and the block-7 border's
position relative to the cluster. Output: a per-site section view + plan render.
Then the classification: for each site, which C3 resolution the analogous stock
configuration uses.

## Alternatives held on the table (the round chooses AFTER the study)

1. **THE CURTAIN MINT** — emit the donor's own sealing idiom along the clipped
   boundary (only registrable if C1/C2 name one construction and C3 says stock
   seals here).
2. **THE APRON EXTENSION** — relax `fits_bench` past the grass edge so the donor's
   own ground carries onto the coast band (only if C3 says ground always wraps; note
   it RELOCATES the junction to the waterline rather than removing it unless the
   carried apron conforms to the descending shore).
3. **THE COAST-NAV CLIFF** — the bench's own shore idiom stamped at the crossings
   (the coast-mosaic machinery; only if C3 resolves wall-meets-coast to the coastal
   cliff class).
4. **THE FREE DESCENT** — carry/extend the wall body down below the waterline per
   THE FREE-BASE LAW (only if C3 finds interior rock doing exactly that at coasts).

## Method

Read-only vs stock disc-1 (`ff9mapkit.world.extract`: `list_blocks` / `read_block`
/ `decode_id`, terrain part) + the deployed bench bytes for C4 (`walk_sim.load_world`).
Multi-agent: parallel instruments for C1-C4, each load-bearing finding adversarially
re-measured by a different method before it is believed (the synthesis study's
discipline — 5 of 6 laws there died under their skeptic). Instruments →
`studies/overworld-topography/curtain_*.py` + the C4 probe beside this file;
artifacts → `out/`. Nothing deploys; the live bench stays as the owner last saw it.

## Success criterion

C1/C2 name the sealing construction(s) with numbers, C3 resolves wall-meets-coast
to a dominant idiom, and C4 classifies both hover sites → the V-shore round becomes
registrable with ONE named fix class and a falsifiable prediction. It FAILS if the
census finds no consistent sealing grammar — in which case the round's default
falls to the smallest-authorship alternative (the apron extension, which mints no
new surface class) and says so honestly.
