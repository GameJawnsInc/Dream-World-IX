# Handoff — BEACH-MINT rung 3 (the virgin-shore mint)

> **STATUS UPDATE (2026-07-11, the continuation session — branch
> `claude/handoff-beach-mint-rung3-4ac731`):** §3's step 1 is DONE — the one-cell
> band-conversion probe is BUILT (`band_convert` in `coastmorph.py` + CLI
> `world-transplant --band-convert CX,CZ:PART`, kit `0676004`), offline-gated (the
> discrete role-decode / per-block float dialect / shade-agreement law — see the
> updated brief §Frontier and the coast-mosaic memory), and DEPLOYED at cell
> **(10,4)** (a (7,17) clone; probe = beach-west ring cell (116,-281) sea3→sea1;
> references = the (11,6)/(11,7) mints). Deployed-bytes differential vs (11,7) is
> exactly the 3 probed cells' water. **★ IN-GAME PROVEN 2026-07-11** ("reads as
> faithful compared to the verbatim") — merged to master; next is §3 step 4
> (the full ladder composition around a synthesized beach).

**Written:** 2026-07-11, end of a session that shipped rungs 1–2a of BEACH-MINT and
cracked rung 3's blocker. **Why this file exists:** the work continues in a *new*
Claude session on a *different Anthropic account*, so nothing in that session's
auto-memory (`~/.claude/projects/.../memory/`) or this conversation is guaranteed to
carry over. This doc is self-contained — read it, then optionally cross-check the
richer memory file named at the bottom if your environment happens to expose it.

**Start here in the codebase:** repo-root `CLAUDE.md` (agent brief — read it first,
it has the hard constraints and environment paths) and
`ff9mapkit/ff9mapkit/world/coastmorph.py` (all code below lives there).

---

## 1. Where things stand

This is the **coast-morph pillar** of `ff9mapkit` (an FF9/Memoria custom-content
toolkit) — specifically **BEACH-MINT**, the capstone: authoring a wholly new beach
(sand + foam assembly) on the overworld from declarative chain specs instead of
carrying/reshaping a real one.

- **Rung 1 — ★ in-game proven** (prior session): `beach_mint(donor, width=)` /
  `--beach-mint WIDTH|auto`. Re-mints a *real* beach's sand+foam assembly with the
  land chain and waterline pinned (untouched), only the interior sand-seam chain
  synthesized at a target width. Deployed at world cell **(11,7)**.
- **Rung 2a — ★ in-game proven** (this session, user confirmed "pass"):
  `beach_mint(donor, width=, land=)` / `--beach-mint WIDTH|auto[:LAND]`. The **land
  chain becomes synthetic too** — it's pushed `land` units landward (sin²-eased,
  cap ends pinned), conformed to the berm surface, and the berm terrain is
  **BSP-clipped** at the new chain (pure real bytes: convex-triangle clip, merged-loop
  re-triangulation, canonical float snaps, full ledger set). Deployed at **(11,6)**
  (north of the rung-1 mint) at `land=2.4`; passed playtest (wider beach, clean
  sand-grass clip seam, zero water delta).
- **Rung 3 — the TRUE virgin-shore mint** (a beach on a bare coast with *no* donor
  beach at all): **not built yet**, but its blocker was identified and **cracked
  offline this session** — see §2. This is the next piece of work.

All work is **merged to `master`** in the main repo checkout
(`C:\gd\Dream-World-IX`, not the worktree). Relevant commits, newest first:

```
dc61f79  Merge -- the deformed-tile rect law: conforming strip tier byte-learned
0ce705b  docs(brief): the deformed-tile rect law -- rung 3's blocker cracked offline
71eb870  feat(world): THE DEFORMED-TILE RECT LAW -- convergence-fan vocabulary byte-learned
3104434  Merge -- beach-mint rung 2a in-game proven
2ace8d2  docs(brief): BEACH-MINT rung 2a IN-GAME PROVEN -- (11,6) land=2.4 mint passes
27cba00  docs(brief): BEACH-MINT rung 2a deployed at (11,6), awaiting playtest
289453c  feat(world): BEACH-MINT rung 2a -- the free-footprint mint, landward
fd7ba10  Merge -- beach-mint rung 1 in-game proven (prior session)
```

(`master` also has unrelated concurrent work from another session in between —
Overload-hooks battle rebalance commits — ignore those, they don't touch coastmorph.)

**If your session starts fresh:** pull/checkout `master` in `C:\gd\Dream-World-IX`,
then branch off it for rung-3 work (e.g. `claude/rung-3-virgin-mint`). The old
worktree branch `claude/rung-2-virgin-shore-mint-2bc4f1` is fully merged and can be
ignored/deleted.

---

## 2. What was learned this session (the rung-3 unlock)

### 2a. The window census (why a naive virgin mint doesn't work)

Map-wide byte censuses (scripts were scratch, not committed — re-derive if needed,
they're cheap: iterate `transplant.world_tris(bx, by, part)` over the 24×20 grid):

- **Beach berms are topo-0 (grass) ONLY** — 664/702 land-chain welds map-wide. A
  virgin cove backed by highland (topo-27/49) is off-language.
- **The lattice band-adjacency law**: legal owner-cell neighbor pairs are only
  `{sea2:sea2,sea1}`, `{sea1:sea1,sea2,sea3,sea5}`, `{sea3:sea1,sea3,sea5}`,
  `{sea5:sea1,sea3,sea4,sea5}`, `{sea4:sea4,sea5}` — **sea3 never touches sea4
  anywhere on the map** (sea5 always interposes).
- **Beaches never share verts** — minimum separation between two distinct sand
  components is 4.06u (a grass tongue).
- The 5 wash-fronted "virgin pocket" candidates found map-wide
  ((7,17)/(3,13)/(9,17)/(16,5) + one more) are all **one lattice column too short**
  and pinch-share with an *existing* beach, or (the one clean cove, (8,3)) fail the
  topo-0 berm law. **None of the 5 are usable as-is.**
- The real blocker: the water bands' **conforming (non-lattice) tiles** — where
  sea1/sea2/sea3/sea5 fan together at a beach's convergence point / any curved
  coast — had **no known UV-emission rule**. Every earlier hypothesis (affine
  continuation of a neighbor lattice tile; own-band placement on a cell frame)
  **falsified** at map-wide scale. Rung 3 needs to *emit new* conforming tiles
  (the wash/ring termination around a new beach), so this had to be solved first.

### 2b. THE DEFORMED-TILE RECT LAW (cracked, offline-proven)

**The law:** a strip tile's (sea1/sea5) UV map is a **≤2u × ≤2v snap-rect assigned
to its corner verts**, independent of geometric deformation. When the coast outline
drags a tile's verts out of the 4u lattice, the UVs *stay at their corner values* —
the map deforms *with* the tile. This is exactly why every position-evaluated fit
(continuation of a neighbor's affine map) failed: it assumed the UV was a function
of world position, but it's actually a function of *which corner role* the vert
plays, transported through the deformation. Verts *inserted* by a clip (not present
in the un-clipped tile) carry **edge-lerped** UVs at their own positional parameter
along the edge — the Sutherland–Hodgman signature.

**Coverage (map-wide, both tiers unified under one snap vocabulary):**
- sea1 lattice: 186/186 decode. sea5 lattice: 1622/1624 decode.
- sea1 conforming: 233/248 decode (~94%). sea5 conforming: 871/911 (~96%).
- Residual (~5%, rotation-ambiguous / cross-group lerp anchors / oddballs) is named
  and stays verbatim — the same tolerance the sand-band and cap laws accepted.
- **The sea1 convergence fans at real beach ends are PURE corner assignment** (zero
  lerps needed in every specimen dumped) — this is the good news for rung 3: the
  fan tier a new beach's ring needs is the *simple* half of the law. The
  interpolated/lerp-heavy tier belongs to sea2/sea3, and — because sea3 never
  touches sea4 (§2a) — **the virgin mint's ladder can skip sea3 entirely** and
  only needs sea2 (proven `mains_uv` machinery, already used everywhere) plus
  sea1/sea5 via this new law.

**Shipped** (in `coastmorph.py`, all offline, no deploy):
- `STRIP_U_SNAPS`, `STRIP_V_SNAPS` — the empirical snap-value constants (texels/1024).
- `_deformed_strip_groups(tris)` — decodes a strip band's triangle list into groups:
  union-find over UV-equal shared edges, **with a row-boundary merge guard** (a
  merge is only allowed if the union of corner values still fits ≤2u×≤2v — else
  you silently fuse two adjacent strip rows into a fake "tile", which is exactly
  the bug the guard exists to prevent). Yields `(tris, kind, detail)` with
  `kind ∈ {"rect", "residual"}`; tries both the unrotated and transposed
  (u↔v-swapped) role assignment before giving up.
- `conforming_rebuild(donor, parts=("sea1","sea5"))` — the **identity round-trip**
  completeness proof (same pattern as the earlier `cap_rebuild`/`sand_rebuild`):
  re-derives every decodable conforming group's UVs from the law (corners
  transport their exact donor floats; lerp verts are recomputed purely from
  position) under a byte-equality gate. Proven zero-drift on (7,17)/(3,13)/(9,17).
- 3 new tests in `ff9mapkit/tests/test_coastmorph.py`
  (`test_deformed_rect_law_decodes_the_strip_tiers`,
  `test_conforming_rebuild_golden`, plus the rung-2a golden pair from earlier).
  Full file: 35 tests, all green. Wider suite (`py -m pytest -n 6 -q` from
  `ff9mapkit/`) was clean at merge time (2641 passed / 199 skipped, one unrelated
  GUI-theme test flakes only under xdist parallelism — passes alone, ignore it).

**Deliberately NOT done:** deploying an identity-rebuild-only clone. An
identity-byte deploy proves nothing in-game (the bytes are unchanged by
definition) — the in-game exercise has to be the *first fresh emission* (§3).

---

## 3. The next step (rung 3, concrete)

**Goal:** the one-cell band-conversion probe — the first time this law emits a
*genuinely new* deformed tile, not a byte-identical rebuild.

**Suggested shape of the work:**
1. Pick a donor with a clean conforming sea1↔sea5 boundary near a lattice cell
   that's currently owned by (say) sea4 or sea5 in lattice form. Re-band that one
   cell: drop it, emit it as a sea1 (or sea5) tile whose corner UVs are assigned
   via the rect law (pick the snap-rect that keeps it edge-consistent with its
   real conforming neighbors — this is the first place you must *choose* a rect,
   not just transport one, so it's the real generative test).
2. Gate it: the emitted tile's edges must uv-match its real neighbors exactly at
   shared verts (no new residual/lerp verts — a lattice-cell target has none to
   worry about), and `_deformed_strip_groups` should decode the new tile as
   `"rect"` when re-scanned.
3. Deploy as a small in-place tweak (`morph_in_place`, like the coast-morph nose
   bumps were proven) or a clone via `world-transplant`, next to an identity
   reference cell, and ask the human to playtest (per the hard constraint — you
   cannot see the game).
4. Once the single-cell conversion is proven, scale up to: wash termination
   (proven `mains_uv`/sea2 machinery, no new law needed) + ring/sea5 termination
   (this law) + sea1 convergence fan at the beach ends (this law, the "pure
   corner assignment" case — should be the easiest part) = the full ladder around
   a synthesized beach on a bare coast. That composition *is* rung 3.

**Cautions carried over from the whole coast-morph pillar (read before touching
water bytes):** water tiles must never be position-re-evaluated past their own 4u
footprint (extrapolation reads as smush/border-tiling — a hard-learned lesson);
every new geometric edit needs a T-vertex gate against its real neighborhood
(float32-scale, not float64 — the deployed `.ff9mesh` is float32 and double-precision
scans silently miss real cracks); and any new drop/emit tweak should carry an
exact area or count ledger the way every prior morph in this file does. The full
list of these laws (much longer, exhaustively documented) is in the project memory
file named below — read it if you can see it.

---

## 4. Practical pointers

- **Game/mod paths:** `C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\`.
  Live mod folder for dev testing: `<game>\FF9CustomMap\`. Deployed test cells you'll
  find already overridden there (don't be surprised by them): the rung-1/2a beach
  mints at world blocks **(11,7)** and **(11,6)**, an identity reference at
  **(13,8)**, plus a long list of prior coast-morph proofs (r6–r19 rows) — see
  `FF9_Data/WorldMap/Disc1/0_1/` under that folder for the full list.
- **Dev loop:** `py -m ff9mapkit world-transplant --mod-folder FF9CustomMap --cell BX,BY --donor DX,DY <morph flags> --dry-run` first (gates run offline, nothing written), then drop
  `--dry-run` to deploy. F6 in-game → Warp/teleport to check. Full CLI reference:
  `py -m ff9mapkit world-transplant --help` from the `ff9mapkit/` directory.
- **Tests:** `cd ff9mapkit && py -m pytest tests/test_coastmorph.py -q` (fast, 35
  tests) or `py -m pytest -n 6 -q` for the whole suite. These need the real FF9
  install (`config.find_game_path`) — they skip cleanly without it.
- **The one memory file that matters most, if visible to you:**
  `project-ff9-overworld-coast-mosaic.md` in the auto-memory store — it's the full
  deep recipe for the entire coast-morph pillar (every law, gate, and in-game
  proof going back to the first cliff morph), far more exhaustive than this note.
  This handoff exists precisely so you're not stuck without it.
- **Repo convention:** commit freely on a feature branch, merge to `master` with a
  descriptive message once a piece is proven (offline-proof commits and
  in-game-proof commits are usually separate, per the pattern in §1's commit
  list). Outward-facing actions (push to a remote, PRs) are confirm-first.

Good luck — the hard part (the UV law) is done; rung 3 is mostly composition now.
