# R2 recon: cluster D's falls and the plateau it drops from

**Status:** registered before measuring (2026-10-20). Reads only: stock disc-1 bytes, nothing written but
`out/falls_recon.json`. No launch.

**The question** (RECON.md R2): can `world-mountain`'s ensemble carry take cluster D's falls the way it takes the
horseshoe's? RECON parked it on one fact: the falls "drops from a plateau at 26 to the lowland, and the plateau is
not a qualified massif". This recon measures that plateau's anatomy and decides whether any lawful unit holds it.

**What is already known** (`../../overworld-topography/README.md` THE TERMINATION CENSUS, `out/census.json`):
- Cluster D is one welded water system over (18,13), (19,10-13), (20,10-11), both tips MASSIF:
  - a plateau river at y 26.1-26.4 in (19,10), (20,10), (20,11);
  - the falls, 22 tris in (19,11), from 26.07 down to 2.96;
  - a joint and river at its foot (y 1.8-2.6);
  - a valley stream south through (19,11)-(19,13) and west into (18,13), at y 0.4-2.7.
- Disc 1 has 3 falls blocks: the horseshoe's (5,15), (5,16) and cluster D's (19,11). The horseshoe's falls drops
  from about 26 to a river at 15.2 inside a bounded massif, and `world-mountain --donor horseshoe` carries it (in
  game).
- 5c (`RUNG5.md`): the high ground (top > 6.5) reached from cluster C's source is one component of 20,904 tris over
  65 blocks, bbox x 754-1459, z -1055 to -569. Cluster D's falls (x 1251-1280, z -705 to -733) lies inside that
  box.

## The instrument

THE CUT-LINE LAW (`../../overworld-topography/README.md`, the v4 transplant census): a lawful cut crosses only land
at y <= 6.5, and high relief is cut around, never through. A massif carry's rim sits on lowland, so the smallest
lawful unit holding the falls is the whole high component it stands in. `falls_recon.py`:
- **A. The system:** cluster D's water parts welded into one component; its tips (plateau end, valley end), each
  with its nearest rock and sea.
- **B. The high components, map-wide** (terrain tris with top > 6.5, joined by shared plan edges, as 5c's
  `high_component`), and the one each seed lands in:
  - cluster D's falls lip, its plateau tip and its valley tip;
  - cluster C's source tip (5c's seed);
  - **the control:** the horseshoe's falls lip. It is a carriable falls, so its component must come out bounded,
    about the catalogued massif (blocks 5-6,15-16). If it floods the continent, the instrument cannot tell a
    carriable falls from an uncarriable one and B decides nothing.
- **C. The rock component** (topo 49 joined by shared edges, the massif census's definition) holding the rock the
  falls welds to, ranked map-wide. The massif census calls its largest one, comp0, "the continental rock network"
  and does not qualify it.
- **D. The falls itself, D against the horseshoe:** sheets, drop, and what every falls boundary edge welds to (top,
  bottom, sides).

## Registered predictions

| # | prediction | falsified if |
|---|---|---|
| P0 | the control: the horseshoe lip's high component is bounded, at most 6 blocks | it reaches more than 6 blocks |
| P1 | cluster D welds into one system; both tips within 8u of rock | it splits, or a tip is SEA or OPEN |
| P2 | **decisive:** cluster D's falls lip stands in 5c's continental high component (the same tri set, 65 blocks) | it lands in a component of at most 6 blocks |
| P3 | the plateau tip and the valley tip land in that same component, as cluster C's source does | either lands elsewhere |
| P4 | the rock the falls welds to belongs to the map's largest rock component | it belongs to a smaller one |
| P5 | the horseshoe's falls ends on a terrace at about 15 inside its massif; cluster D's falls drops about 23u to the lowland, at the escarpment | D's foot is above 6.5 |

**If P2 holds:** cluster D's falls cannot be carried, for the reason 5c gave for cluster C's source: the plateau is
the continental highland, not a massif. R2 then closes for cluster D, and the horseshoe stays the only carriable
falls on disc 1 (it already ships). If P2 fails, the bounded component becomes a donor candidate, and the next step
is the massif census's qualification (a level foot, no vertical rim steps, `../mountaindonors/NOTES.md`).
