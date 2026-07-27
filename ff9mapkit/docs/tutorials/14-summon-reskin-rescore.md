# 14 — Recolour and reframe a stock summon in place (`summon-reskin` / `summon-rescore`)

Edit a **stock** FF9 summon's own cinematic — its palette, its camera — with no donor swap and no
new model at all. Where tutorial 11 wears a stock summon's bones with *your own* creature,
`summon-reskin` and `summon-rescore` edit the stock creature's own container bytes in place: a CLUT
recolour (reskin) and a camera pose/focal-distance reframe (rescore), each spliced back at the exact
same file offsets so nothing else in the container moves. Design notes, the full spec-toml schema,
every refusal, and the laws behind them: [SUMMONS.md](../SUMMONS.md).

**Prerequisites:** the kit set up with the `assets` extra (`py -m pip install "ff9mapkit[assets]"` —
both verbs read the stock container out of your install's `resources.assets` via UnityPy); the FF9
install; nothing else. **Stock Memoria is enough** — neither verb touches the engine DLL, only mod-
folder data.

This tutorial works one effect end to end: **Phoenix, `ef211`**. It was chosen deliberately, not for
being the easiest case — its creature happens to hit a real refusal partway through, which is the
best way to see the tools' guard rails do their job instead of just reading about them.

## Part A — recolour it: `summon-reskin`

### 1. Scaffold a spec from your own install

```powershell
ff9mapkit summon-reskin scaffold --ef 211 --out phoenix_reskin.toml
```

This reads `ef211` out of your install, derives every palette the container actually declares —
creature parts *and* the effect's own scenery cells, whichever exist — measures each one's hue/
saturation/value and its 5-bit headroom, and writes a complete TOML: the drift-guard `expect_sha256`
filled in from your own bytes, every span guard, and one `[[reskin.target]]` row per declared
palette, every row `enabled = false`. Nothing has been recoloured yet — this step only reads.

### 2. Read what it found, then dial the art

Open `phoenix_reskin.toml`. Two things about Phoenix specifically are worth watching for before you
touch anything, because they are exactly the refusals [SUMMONS.md](../SUMMONS.md#the-laws-behind-the-refusals-house-voice-study-grounded)
documents in the abstract:

- **The `creature.part0`–`part5` rows will not build past `enabled = true` at a cold hue.** Phoenix
  is one of the two most saturated creatures in the whole stock cast, and its fire ramp's apparent
  brightness is carried by *hue*, not by value — rotate it cold and the gate that protects relative
  luminance ordering refuses. This is THE SATURATED-RAMP LAW, not a bug in your numbers; leave the
  creature rows off (or dial `hue_to` within stock ±25°) and read the scenery instead.
- **The scenery rows (`pal.s0.x…`) are where a Phoenix reskin actually lives.** Set a shared cold key
  across them:

  ```toml
  [[reskin.target]]
  name    = "pal.s0.x0_y247.e256"   # the fire field -- the largest thing on screen
  enabled = true
  hue_to  = 280.0                    # violet: pushes INTO the channel additive blending keeps (R)
  saturation = 1.00                  # never LOWER saturation on an already-max-sat fire ramp
  value      = 1.00
  ```

  Repeat for the other declared scenery rows at the SET KEY, checking each one's own frontier in the
  scaffold's comments — the shipped Phoenix spec keys most rows to 250° and raises only the two
  vivid flame-bound cells to 280° (the in-game calibration), and one page tops out at 240° and says
  so rather than being silently clamped. A set key is a target, not a uniform: each palette holds it
  only as far as its own frontier allows. (This exact key is not a guess: it's the calibrated value THE
  ADDITIVE-COMPOSITING COROLLARY produced after a first, colder attempt washed out in the actual
  cast — see [SUMMONS.md](../SUMMONS.md#the-laws-behind-the-refusals-house-voice-study-grounded).)

### 3. Plan — resolve every target, no write

```powershell
ff9mapkit summon-reskin plan phoenix_reskin.toml
```

Prints the resolved delta for every enabled row (old value → new, byte count, the luminance-ordering
ρ each recoloured palette survives at) and every refusal a disabled or misconfigured row would hit if
you switched it on. Nothing is written to disk yet — run this after every edit to the toml.

### 4. Build — stage it locally

```powershell
ff9mapkit summon-reskin build phoenix_reskin.toml --out C:/gd/SCRATCH/summon-format/reskin/ef211
```

Reads the install again (re-checking the drift guard), splices every enabled target, re-parses the
patched container through the same reader that decoded it (the self-check), renders preview PNGs of
every recoloured page, and writes the container + a manifest + a standalone deploy/revert script pair
under the given local-only staging root. Omit `--out` to use the tool's own per-effect default —
either way, a checkout path, a mod-asset tree, or (without an explicit allow) the game install all
refuse outright; this step never writes into your live mod folder itself.

### 5. Verify — check what's staged, as bytes

```powershell
ff9mapkit summon-reskin verify phoenix_reskin.toml --out C:/gd/SCRATCH/summon-format/reskin/ef211
```

(`--out` here names the same staging root `build` used in step 4 — pass it again, or omit both to
let the tool's own per-effect default agree with itself.)

Re-derives the container from the spec and the install *right now* and compares it byte-for-byte
against what step 4 wrote — not "did a file get written" but "are the bytes on disc still what this
spec produces today". A stale manifest, a missing preview, or a hand-edited container are each
reported as their own distinct failure.

### 6. Deploy — write the override into a real mod folder

```powershell
ff9mapkit summon-reskin deploy phoenix_reskin.toml --mod-folder FF9CustomMap
```

Writes straight into `<mod folder>/FF9_Data/SpecialEffects/ef211` (extensionless — the engine's
on-disc override path reads the raw name) through the same write/backup/readback ledger every summon
verb uses, and emits a `--root`-rebasable revert script beside it. **Refuses outright** if that mod
folder already carries a `ModFileList.txt` — see THE SILENT-FALLBACK LAW in
[SUMMONS.md](../SUMMONS.md#the-laws-behind-the-refusals-house-voice-study-grounded); this verb never
creates one either. Add `--dry-run` first if you want to see exactly what would land without writing
it.

### 7. Cast it, and judge

No relaunch, and no `~ → Reload` — the override is re-read from disc on every cast. Fight anything
that summons Phoenix (or trigger your own bench encounter) and watch the fire-field key change while
the bird itself keeps its stock colouring — that split is the refusal from step 2 made visible
on-screen, not a mistake. If nothing changed at all: check the failure table in
[SUMMONS.md](../SUMMONS.md#refusals) — a wrong mod folder, a stray extension, or another
`FolderNames` entry shipping its own `ef211` earlier in priority all produce the identical symptom,
because `SFX.Play` logs nothing on a miss.

### 8. Revert

```powershell
ff9mapkit summon-reskin revert phoenix_reskin.toml
```

Runs the ledger's own revert script where **the plan recorded its writes** — which for a `deploy` is
the folder it resolved, so the ordinary flow is unchanged. An explicit `--root` or `--mod-folder`
RE-TARGETS it; `$FF9_MOD_FOLDER` and `.ff9deploy.toml` do not, because a revert's destination is a
historical fact, not a preference — rebasing a plan onto a folder it never wrote to would delete an
override it never created. The script restores or deletes as recorded — restoring the pre-existing file if one existed, or deleting the
override if it did not, and dropping the `ModFileList.txt` line if one was added. Add `--dry-run` to
preview it without writing anything. This undoes a `deploy`, not a mere `build`: a `build`-only stage
never touched a mod folder, so there's nothing there to restore — delete the local staging root
instead if you want to clear it out.

## Part B — reframe its camera: `summon-rescore`

The same six-verb shape, a different lever. A summon's camera is not reachable from its own effect
program — it is played by the container's sequence stream, the same block format the battle engine's
camera codec already round-trips — so a rescore reads the shot table, applies a declarative pose/
focal-distance delta, and splices the result back at the **same byte length**, with every duration
untouched (the camera and the effect program are two clocks the original author kept aligned; a
content rescore moves neither).

```powershell
ff9mapkit summon-rescore scaffold --ef 211 --out phoenix_rescore.toml
```

The scaffold prints the shot table (letter, chunk, sub-file, every keyframe's local frame) and a
reframe-budget verdict per shot, cross-referenced against the effect's own phase table: a shot that
draws the effect's own scenery is TIGHT (THE EFFECT-OWNED SCENERY LAW — widening the frame there
finds the set's edges), a creature-only shot is forgiving. Author one `[[edit]]`:

```toml
[rescore]
effect = 211
label  = "phoenix-w5-focal-pull"
expect_sha256 = "…"           # filled in by scaffold

[[edit]]
shot     = "A"
chunk    = 0
subfile  = 8
sequence = 0
frame    = 87                  # the shot's ONLY focal keyframe -- ef211 has just one camera op at all

focal = { distance = 288 }     # H 384 -> 288 (x0.75): a modest pull back, not a dramatic zoom
```

Phoenix's own camera happens to make an easy first example: it declares exactly one op, one shot,
one sequence (no alternate takes for THE THREE-SEQUENCE TRAP to catch you on), and zero
runtime-chosen ops — so `acknowledge_dynamic_ops` isn't needed here at all. A more typical stock
summon isn't this forgiving: **324 of 372 effects** carry at least one `PLAY_CAMERA arg2=3` op, and
on one of those `build` refuses until `[rescore] acknowledge_dynamic_ops = true` states you
understand that op's target is chosen by the battle field at runtime and cannot be enumerated
offline (THE DYNAMIC-OP DISCLOSURE, [SUMMONS.md](../SUMMONS.md#the-dynamic-op-disclosure)). Then
the same four verbs as Part A: `plan` (prints the delta and the alternates-track verdict), `build`
(splices + self-checks + stages), `verify` (re-derives and byte-compares), `deploy` (writes into the
mod folder, same `ModFileList.txt` refusal), and the emitted revert script.

## Shipping both together — orthogonality

A reskin and a rescore of the *same* effect can ship in one container, but don't just assume it —
name the sibling and let the tool prove it:

```toml
[reskin.orthogonality]
rescore = "phoenix_rescore.toml"   # resolved relative to THIS file's own directory
```

`summon-reskin verify` (and its `plan`/`build`) then rebuild `phoenix_rescore.toml` from its own spec
and intersect its changed-offset set with the reskin's — an empty intersection is the proof the two
edits land in disjoint bytes. Name a sibling that doesn't exist and the gate FAILS; name none and it
SKIPS with that stated, so an unproven disjointness is never reported as a proven one.

## Command map

| step | reskin | rescore |
|---|---|---|
| read the install, emit a guarded spec | `summon-reskin scaffold --ef N` | `summon-rescore scaffold --ef N` |
| resolve + print the delta, no write | `summon-reskin plan <spec>` | `summon-rescore plan <spec>` |
| splice + self-check + stage locally | `summon-reskin build <spec>` | `summon-rescore build <spec>` |
| re-derive and byte-compare what's staged | `summon-reskin verify <spec>` | `summon-rescore verify <spec>` |
| write the override into a mod folder | `summon-reskin deploy <spec>` | `summon-rescore deploy <spec>` |
| undo exactly what `deploy` wrote | `summon-reskin revert <spec>` | `summon-rescore revert <spec>` |

## Part C — repaint its texture: the texel lane (`[[reskin.texel]]`)

`summon-reskin` recolours; it cannot move a texel from one palette index to another, so it can
never change a shape, an edge, or a silhouette. The texel lane is the second lever on the same
verb, and this rung ships it for **creature texture pages only** (the one texel class measured
free of every hazard the corpus carries) — scenery pages refuse by name, deferred to a later rung.
This part walks the emblem walk: export a paintable page, edit it in index space, build, and see
the composed artifact (a recolour *and* a brand, in one container).

### 1. Export the paintable art

```powershell
ff9mapkit summon-reskin export-art --ef 227 --out C:/gd/SCRATCH/summon-format/repaint/ef227/art
```

Decodes every creature page Bahamut declares (six parts) to a **P-mode indexed PNG** — the pixels
ARE the palette indices, the loaded palette is display-only (the container stays the palette
authority; this lane writes zero CLUT bytes) — plus a `.coverage.png` per part (green hatch = the
texels no face ever samples; paint there is inert) and two sidecars: `art.manifest.json` (the
stock sha256 drift guard + every page's derived offset/size/palette) and `texel.scaffold.toml` (a
fully guarded `[[reskin.texel]]` table, every row `enabled = false`).

### 2. Edit the indexed PNG

Open `tex.part0.png` in a **palette/indexed-mode** editor (not a generic RGBA one — an editor that
flattens to RGBA on save breaks the byte-identity round trip this lane's whole gate rests on).
Paint using the page's *existing* indices only — this lane moves indices around, it never mints a
new colour. Keep `tex.part0.coverage.png` open beside it: anything outside the hatched pad is
readable in-game, anything inside it is on-screen but never sampled.

One boundary matters more than any other: index 0 is the model's transparent cutout on every stock
summon. Paint through it (turning a hole opaque) or over its edge (turning opaque texels into a
new hole) and the build will refuse until you say `acknowledge_cutout_reshape = true` on that row —
THE CUTOUT LAW, [SUMMONS.md](../SUMMONS.md#the-cutout-law-at-the-texel-level). Reshaping a torn
wing edge on purpose is legitimate; painting through a hole by accident is exactly what this catches.

### 3. Author the spec — recolour AND repaint, one container

The texel lane composes onto the CLUT lane rather than competing with it. Reusing `phoenix_reskin.toml`'s shape for Bahamut, one spec can carry both tables:

```toml
[reskin]
effect = 227
label  = "bahamut-emblem"
expect_sha256 = "…"                # filled in by export-art's manifest / summon-reskin scaffold

[[reskin.target]]                  # LEVER #1 -- the CLUT recolour (optional; omit for a bare repaint)
name    = "creature.part0"
enabled = true
hue_to  = 200.0

[[reskin.texel]]                   # LEVER #2 -- the texel repaint
name    = "tex.part0"
source  = "art/tex.part0.png"      # relative to THIS spec file
enabled = true
expect_page_offset = 0x0004a1a0    # filled in by export-art's scaffold
expect_page_bytes  = 0x4000
expect_page_wh     = [128, 128]
# palette_from = "creature.part0"  # optional; omitted = the stock palette, 0 CLUT bytes touched
```

A spec naming only `[[reskin.texel]]` rows is a bare repaint; naming only `[[reskin.target]]` rows
is the plain recolour from Part A. **With both present, `build` resolves the recolour first and
hands its patched bytes to the repaint** — one container, one ledger, one revert, with the two
lanes' changed-byte sets gated disjoint ("THE COMPOSED HALVES ARE DISJOINT" in the self-check).

There's a second route to the same artifact: instead of repeating the `[[reskin.target]]` row
inline, a **texel-only** spec (no `[[reskin.target]]` table at all) can point at an
**already-shipped** reskin spec and compose onto its rebuild:

```toml
[reskin.orthogonality]
reskin  = "bahamut_reskin.toml"    # the CLUT lane's own spec, resolved relative to THIS file
compose = true
```

### 4. Plan, build, verify, deploy, revert — the same ladder

```powershell
ff9mapkit summon-reskin plan   bahamut_emblem.toml
ff9mapkit summon-reskin build  bahamut_emblem.toml --out C:/gd/SCRATCH/summon-format/repaint/ef227
ff9mapkit summon-reskin verify bahamut_emblem.toml --out C:/gd/SCRATCH/summon-format/repaint/ef227
ff9mapkit summon-reskin deploy bahamut_emblem.toml --mod-folder FF9CustomMap
```

`plan`/`build` print both lanes' self-checks when both tables are present — the recolour's gates,
then a note that the texel lever is COMPOSING onto its patched bytes, then the texel lane's own
gates (the inverted region partition, the cutout census, the dead-pad report, the texanim
co-transform check, and the region invariant).
`deploy` writes through the same ledger every summon verb uses; `revert` undoes exactly what it
wrote. The texel lever's hot-reload guarantee is the *stronger* of the two: `SFX.Play` re-reads the
container and unconditionally resets the texture cache on every cast, and a page upload IS the
event that invalidates it — so, like the CLUT lane, no `~ → Reload` and no relaunch, but here
there is no "wrong track" ambiguity either, because the whole cache is always dropped.

### The texanim table — five summons that are no longer off-limits

Five stock creature packages carry a small **texture-animation** table: **ef038** (Shiva) and
**ef177 / ef493 / ef494 / ef495** (Carbuncle, shipped four times over). Earlier releases refused
*every* creature edit on those five — recolour and repaint alike — because the table's layout was
unread and it might have been swapping the creature's palette mid-cast.

**It isn't.** The table copies a small rectangle of palette *indices* from a spare strip into a live
window inside one creature part's own texture page — Shiva's eyelid, Carbuncle's eye and mouth. It
cannot touch a palette at all. So what changed for you:

* **a recolour of any of the five now just works**, with no acknowledgement key. If your spec still
  carries `acknowledge_texanim = true`, it keeps building — the key is a **deprecated no-op** now,
  the build says so, and `scaffold` no longer writes it. Delete the line. (One corner keeps the key
  meaningful, and it never applies to a stock container: an armed table the tool *cannot decode*
  falls back to the old rules — creature refuses outright, scenery still needs the key.)
* **a repaint of any of the five now works too.** A whole-page repaint needs no key. A *localised*
  one only has to be consistent: if you repaint the animated window, repaint the frames it swaps in
  as well. Leave them stock and the build refuses with a **work order** — the clip, what you painted,
  and the exact rectangles you left behind — because the first time the clip runs, the window pops
  back to art your repaint never touched. `acknowledge_texanim_frames = true` on that row says the
  asymmetry is what you wanted.

`plan` and `export-art` both print the table now (each clip's part, frames and rectangle, plus the
protected set), so you can see what to avoid before you open the PNG. Bahamut carries no table at
all, which is why it's still this tutorial's donor — but the five are no longer a wall.

One rule the tool now enforces on your behalf, on every summon: it never resizes, moves or rewrites
that region. The engine keys a real decision on where it starts, and both levers are in-place splices
that never need to — so every build checks the region came out byte-identical and tells you so.

### The dead-texel report

`export-art`'s coverage measurement generalises: only 64.0% of the corpus's creature texels are
ever sampled by a face. Paint outside the hatched pad and the build still succeeds — it's reported
as an inert edit (dead texel count, per target), never a failure, exactly like a CLUT hue rotation
on an achromatic cloud band.

### What's NOT here yet — the scenery texel lane (W6b)

Everything past a creature's own texture pages — the ground, sky, and fire-field textures a summon's
effect draws itself — is out of scope for this rung and refuses by name: mixed bit depths sharing
one VRAM column (SAME-BYTES-TWO-BINDINGS), pages written by more than one chunk at different cast
phases (CO-TRANSFORM), models whose UVs spill into a neighbouring VRAM column (U-SPILL), and 15bpp-
direct pages with no CLUT to index against at all. Full detail:
[SUMMONS.md](../SUMMONS.md#w6b-deferred--the-scenery-texel-lane).

## Provenance, one more time

The stock container is read fresh from *your* install's `resources.assets` on every `build`/`deploy`
— never from the repo, and never from a previous override, so a Steam/Moguri patch can't be silently
shadowed forever. A sha256 drift guard refuses to splice into bytes an edit wasn't derived against.
Everything staged offline is local-only by the same guard every summon verb shares (no repo path, no
mod-asset tree, no install path without an explicit allow, no `--force`); the only bytes that ever
reach a real mod folder are written by `deploy`, deliberately, into a folder you named.
