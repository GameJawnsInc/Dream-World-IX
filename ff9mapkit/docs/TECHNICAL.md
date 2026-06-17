# How it works — the hard problems

`ff9mapkit` looks like "fill in a TOML, get a map." Underneath, a handful of things had to be
reverse-engineered or solved from scratch before any of that was possible. This is the record of the
non-obvious parts — both as documentation and because the interesting work is invisible from the
surface.

Everything below was validated **offline**: the engine can't be scripted from the outside, and the
final visual judgement is a human's, so correctness is established by byte-exact round-trips against
real game data and by math checked against the engine's own source — not by "it looked right."

---

## 1. Minting a brand-new field on a stock engine

FF9 resolves a field by ID into three independent things: a background, an event script, and a text
block. Memoria's `DictionaryPatch` `FieldScene` directive exposes that decoupling:

```
FieldScene <id> <area> <MAPID> <SCRIPTNAME> <textid>
```

So a brand-new ID can run a **custom script** while pointing its background lookup at either a real
field's art (BG-borrow) or its own shipped scene. The one sharp edge: the engine builds the
background name as `"FBG_N" + areaID` with **no zero-padding**, and the asset loader reads exactly two
characters for the area — so single-digit areas (`0`–`9`) silently black-screen. The kit forces a
custom scene's area `>= 10` and refuses a BG-borrow of a single-digit-area field with a clear message.

This is the piece the community had treated as unsolved: no shipped FF9 mod had minted a playable
new field. Hades Workshop's "Export as Custom Field" produces a UV-broken atlas and corrupts the
script when *adding* an entry — both dead ends this toolkit routes around.

## 2. The camera projection (so any angle is authorable)

FF9 places the player and the walkmesh through the PSX **GTE RTPT** transform — a fixed-point
pinhole projection. The in-game FieldCreator tries to solve a camera from five screen↔world anchors,
but for a flat floor (all y = 0) that system is rank-deficient: the solve blows up and the walkmesh
flies off-screen. That's why novel angles weren't a thing.

Reading the projection out of the engine source instead of fighting the solver surfaced the
invariant that makes everything else work:

```
R_ff9 = diag(1, k, 1) · R_ortho     with k = 14/15 = 0.9333…  (a GLOBAL constant)
```

The orientation matrix isn't a pure rotation — row 1 carries a fixed **vertical-focal aspect
correction** (the GTE has one projection distance for both axes). `k = 14/15` held across all six
real cameras sampled (3/4-tilt, 90° yaw, oblique, inverted) to ~1e-4. With that, the camera can be
**decomposed** (recover pitch/yaw/FOV/position) and **re-synthesized** byte-faithfully (Int16 `r[][]`
+ Int32 `t[]`), so you can author a camera from pitch/yaw/FOV/distance and write it back exactly as
the engine expects. The synthesis was confirmed in-game by regenerating a real room's camera and
seeing it render unchanged.

## 3. The canvas↔screen map (so the paint guide is exact)

To tell the artist where the floor lands on the painting, you need the world→painted-pixel map. After
an in-engine probe (a temporary debug block logging the GTE result for a grid of floor points), the
map turned out to be **exact, scale-1**:

```
canvasX = rawProj.x + range.w/2 ;  canvasY = range.h/2 − rawProj.y
```

reproduced to **0.0005 px**. An earlier hand-fit (`sx≈0.926, sy≈0.889`) had silently been absorbing
two *different* physical constants — the player **collision radius** (`bgiRad*4 ≈ 48` world units,
which stops the player centre short of any wall) and the character-vs-floor offset (below). Replacing
the eyeball scale with the exact map + those two named constants is what made the guide reliable at
any pitch.

## 4. Character planting — the offset that wasn't

FF9 draws the 2D background and the 3D character through related-but-not-identical projections, the
classic "3D char vs 2D BG" vertical mismatch. Every painted room had drifted a little at the back
edge, and a `CHARACTER_GROUND_OFFSET_Z = 298` had been carried to compensate. A second engine probe
(logging the player's true world position vs. where its feet rendered, at multiple pitches) measured
the real offset: **zero**. The 298 was the partner of a `(0,0,300)` origin the walkmesh *builder* had
been injecting — a near-cancelling double-count, camera-dependent, which is exactly what produced the
years-old "back edge drifts" symptom. The honest model is `frame = world` (org 0, no offset); the
walkmesh in true world coordinates *is* the painted floor.

## 5. The event script (`.eb`) — byte-exact authoring without Hades Workshop

The field event binary is PSX-style bytecode. The format was reverse-engineered and is now a
lossless codec (`EbScript.from_bytes(x).to_bytes() == x` for every shipped/authored script):

- header + 84-byte PSX name → entry table at `0x80` (10 slots × 8 bytes);
- each entry: `type, funcCount, (tag, fpos)×funcCount, code` — with the one subtlety that
  `funcBasePos = entryStart + 2` (fpos is measured from *before* the func table);
- opcodes decoded from tables **baked from Memoria source** (no runtime dependency), including the
  expression sub-language (opcode `0x05`: an RPN stack of var pushes / consts / operators).

Content is injected **without shifting bytecode** wherever possible: an appended entry never moves
existing code, and it's activated by overwriting a 3-byte `Wait` filler with an equal-length `Init*`
call. When an insert is unavoidable the entry table is kept consistent. Hades Workshop, by contrast,
reuses the base field's fixed entry table and overwrites the player object when adding an entry — so
the kit owns the script side entirely.

The validation discipline matters here: every injected `.eb` is disassembled and checked before
deploy, and building the worked examples reproduces an in-game-verified script **byte-for-byte**.

## 6. The walkmesh frame (so an imported field lands on its art)

A real `.bgi` stores each floor's vertices **corner-origin in its own frame**; the world position is
universal:

```
world_vert = vert + bgi.orgPos + floor.org
```

(`orgPos == minPos`, the world position of the corner; `floor.org` tiles the floors of a multi-floor
field). This single rule places an imported walkmesh exactly on its painted art and in the engine's
collision frame — verified across single-floor and 23-floor fields. Reshaping a multi-floor fork is
the inverse problem: FF9 floors use disjoint vertex sets, so rebuilding neighbor links from geometry
can't recover cross-floor seams. The kit extracts those seams as world-position edge pairs and
**reconciles them by position** onto your edited geometry (warning, not silently dropping, if you move
a connecting edge).

## 7. Import — forking any real field

`import` reads a field's camera (`.bgs`), walkmesh (`.bgi`), and art straight out of the
`p0data*.bin` assetbundles, offline. Mapping the background folder to its event script (different
naming: `FBG_N21_GRGR…` ↔ `EVT_GARGAN…`) is done with a table **joined from two source registries on
field id** (`EventEngineUtils.eventIDToFBGID` ⋈ `FF9DBAll.EventDB`), baked into the kit — no fragile
suffix-guessing. The script is then scanned for content with unambiguous byte patterns: an exit is an
entry holding both `SetRegion` and `Field`, with the destination's entrance read from the `D8:02`
assignment immediately preceding the `Field` call. So a fork keeps the real place's exits,
encounters, music, and movement tuning — not just its look.

## 8. Engine quirks that cost a playtest each (now encoded as rules)

- **Cutscene animation runs in the LOOP, not the Init.** `ProcessAnime` only advances animation
  frames while an object's `state == running (1)`; an object's Init executes at `state == 2`. Actor
  choreography spliced into a NPC's Init *moves* the transform but freezes the skeleton (it glides).
  The fix — proved with an in-engine `animFrame` probe — is to run it from the NPC's loop function.
- **`op_01` is the engine's undocumented unconditional JMP.** A `Wait` right after one is dead code;
  activation sites must sit in the proven-executed region.
- **`NewGame()` doesn't create the party** — the entered field's script does. A New-Game warp has to
  route through a field that sets the party up, or it lands party-less.
- **Walk turn-radius / warm-up / blocking waits** — issuing an actor command during the entry-fade
  makes it circle; a `Walk` to a point *behind* the actor orbits forever; `WaitTurn`/`WaitAnimation`
  on a player-cloned NPC never complete. The cutscene layer is built non-blocking around all three.

## 9. Why you can trust it without the game running

The hard constraint throughout was that the running game is unobservable from tooling and final
alignment is a human call. So the kit is built to be **provably correct offline**:

- every codec round-trips real game assets byte-for-byte;
- compiling the worked examples reproduces in-game-verified outputs exactly (golden masters);
- camera/projection math is regression-tested against six real cameras and the engine's own formulas;
- 1,500+ kit + 60 Blender tests, all offline;
- the few engine facts that *can't* be derived offline were each pinned with a temporary in-engine
  probe, then removed.
