# W4 — THE RESKIN: stock Bahamut's whole palette set recoloured in place, stock bytes untouched

**TIER W rung 4.** Deliverables: `reskin.py` (header-derived palette map + HSV transform + self-check +
staging ledger + deploy/revert emitter + preview renderer), `bahamut_reskin.toml` (the declarative
surface), `test_reskin.py`, `w4_gates.py`, this report. Recon inputs: `w4-recon/A1-TEXTURES.md`,
`A2-ATTRIBUTION.md`, `A3-RENDERPATH.md`, `A4-PRIORART.md`.
**Built and STAGED only.** Nothing in this rung's own tooling writes to the game install. `reskin.py
build` (no `--live`) produces one container artifact, thirteen preview PNGs, and two stdlib-only
scripts — `deploy_reskin.py`, `revert_summon_reskin_227.py` — under
`C:\gd\SCRATCH\summon-format\reskin-w4\`. Those two scripts are what touch the install, and **they have
not been run against the live game by this report** — §6 is the protocol for the orchestrator to run
them and judge the cast. **The rung is not done until the cast is judged.**

*Method note.* This report is a synthesis, not a fresh measurement pass: B1 derived the transform
(THE KEY: SPECTRAL MIST, settled against the previews by sweep, not guessed) and built the tool; B2 ran
the full gate suite; B3 found and fixed a structurally-dead gate (the channel-clamp counter could never
fire) and replaced it with a real HSV-blowout gate, re-verifying the artifact was byte-for-byte
unchanged by the fix; V1 independently re-derived every load-bearing claim from raw bytes with its own
tooling, never importing `reskin.py`. This report additionally **re-ran `py reskin.py plan
bahamut_reskin.toml` fresh this session** — every number in §1 and §3 below was reproduced directly
against the live install, not copied from the prior reports, and **opened three of the staged preview
PNGs directly** (`creature-sheet.png`, `swatches.png`, `scenery-fire_column.png`,
`scenery-aerial_ground.png`) to confirm the recolour by eye, not just by number. MEASURED / INFERRED
labels below are carried from B1–V1 except where this report states its own direct reproduction.

---

## 0. HEADLINE

> **4,832 bytes, thirteen palettes, zero texels.** The staged `ef227` container differs from the
> user's own pristine stock in exactly **4,832 of 823,296 bytes (0.587 %)** — six 256-entry creature
> CLUT rows and seven scenery CLUT rows/sub-rows, all inside the four byte spans A2's attribution map
> named, all of them palette data, none of them a pixel, a UV, a vertex, a program instruction, a
> sequence tick, or a camera byte. The container is the same length in and out
> (823,296 → 823,296), the drift-guarded stock read is `fe590d00…ed167`, and the staged artifact is
> `7fef205f…688b89a` — the same hash B1 first produced, unchanged by B3's gate fix, re-confirmed by this
> report's own run.
>
> **The whole cast reads in one new key.** Bahamut's violet wing membrane, gold plating and dark hide
> rotate together (+182° on every one of the creature's six pages, so the shared hide material lands on
> one hue and does not fracture across pages) into a spectral mist-green dragon with cold silver-blue
> plating; the effect's own scenery — sky dome, aerial ground, fire column, energy rings — recolours
> independently (A2's texture-disjointness proof: creature and scenery share no page, no CLUT, not one
> VRAM halfword) into a matching deep-teal-and-ghost-blue key. One palette, `scenery.cloud_bands`, is
> **measured pure greyscale (S = 0.00 on all 15 live entries)** and is mathematically inert under this
> transform — declared ON anyway so the set's key is stated in one place, gaps disclosed rather than
> hidden.
>
> **Lever #1 only, and it is provably orthogonal to W2 and W3.** The self-check rebuilds W2's rescore
> and W3's retime from their own specs and intersects the changed-offset sets: **empty both times** — W4
> moved no camera byte and no clock byte, and vice versa. Lever #2 (texel repaint) is explicitly
> deferred; §5 records why.

---

## 1. Gate table

| gate | result | numbers |
|---|---|---|
| **X0** no regression | **PASS** | `r1_gates` 8/8 · `r2_gates` 6/6 · `r3_gates` 5/5 · `w1_gates` 5/5 · `w2_gates` 6/6 · `w3_gates` full run · **294 tests passed** total across the tier (142 r-suite + 34 + 34 + 46 + **38** `test_reskin.py`, up from 32 after B3's gate-fix added 6) · `rescore.py`, `retime.py`, `summon_camera.py`, `camera_codec.py`, `ef_container.py` and the tier-r tools **imported, never edited** |
| **X1** byte accounting | **PASS** | **4,832** of 823,296 bytes changed (0.587 %), against A2's **8,192-byte** four-span whole-set ceiling — 2× margin. 0 unexplained, every byte inside a named target inside a derived span. Per-target: creature parts 505/504/506/509/509/506; `sky_dome` 449, `water_and_sky_gradient` 19, `aerial_ground` 456, `fire_column` 338, `energy_rings` 238, `cloud_sheet` 293, `cloud_bands` 0 (measured invariant) — **re-reproduced exactly by this report's own `plan` run** |
| **X2** round-trip + orthogonality | **PASS** | container re-parses **STRICT** (`cursor_end == 0xc9000`) · **25 regions gated (420,524 B), 0 hits** — sector 0, both id-3 program images, all 3 camera blocks, the id-5 model image, the whole id-4 header + all 6 texel pages · W1's 3 camera blocks re-extract byte-exact · 98,304 B of creature texels bit-identical, `texture_check` still passes on the patched container · **W2 rebuilt from its own spec: 4 bytes, intersection 0. W3 rebuilt from its own spec: 24 aligned + 12 mis-retime bytes, intersection 0** |
| **X3** the five hard rules | **PASS** | STP population **identical** stock-vs-patched on all 13 palettes · **234** transparent (`0x0000`) entries held, none moved either direction · entry 0 unchanged on all 12 palettes that had `0x0000` there (`aerial_ground` is the one row with none) · **0** entries clamped at the channel step (the structural belt — see §3.3) · HSV blow-out census: **19 of 2,614 live entries (0.7 %)** clipped — `creature.part4` 12/255 (4.7 %) value-clipped, `scenery.cloud_sheet` 7/255 (2.7 %) saturation-clipped, every other target 0 % — worst fraction is a **2× margin** under the 10 % `BLOWOUT_FRACTION` refusal gate |
| **X4** revert sandbox | **PASS** | all three cases in a temp sandbox, never the live install: fresh mod folder / already-overridden mod folder / explicit `--root` with no baked default — every case **EXACT RESTORE** (pre-manifest hash == post-manifest hash), staged-manifest hash differs from both |
| **X5** provenance | **PASS** | **2** byte literals of ≥6 non-uniform bytes found in the committable sources (test fixtures); **0** of those appear in the target container or anywhere in the 372-file corpus. Staging root is SCRATCH, never the repo; a repo-relative root and an install-relative root are both **refused** unless `--live`. 0 stock-shaped files in the repo working tree |
| **X6** previews + colour report | **PASS** | **13/13** manifest-listed previews exist on disc (6 creature pages + 1 creature contact sheet + 5 scenery pages + 1 swatch strip) — **directly confirmed present by this report** — and the colour report's mean-H-before→after numbers match B1's per-target figures exactly |
| **negative refusals** | **PASS** | 7/7: an unacknowledged SHARED palette, an unknown target name, a drifted stock hash, a saturation past the 4× ceiling, a span guard mismatch, a per-target offset guard mismatch, a VRAM guard mismatch — all refuse |

Reproduce: `py studies/custom-summons/tier-w/w4_gates.py` (X0 re-invokes the whole tier's gate runners,
so a full pass is the slowest single command in the tier — treat it the same way as W3's nested-cost
note, §5 item below). Fast self-check only, no full regression: `py reskin.py plan bahamut_reskin.toml`
(what this report ran to reproduce §1/§3's numbers). Tests alone:
`py -m pytest studies/custom-summons/tier-w/test_reskin.py -q` (38 tests, no install required for the
great majority — a handful skip without one).

---

## 2. THE EDIT — four spans, span by span

**All four spans are re-derived from the container's own headers at build time** (`reskin.py`'s
`id0_palettes`/`creature_palettes`), then asserted against the TOML's `expect_*` guards — a guard that
disagrees with the derivation refuses the build rather than splicing into the wrong bytes. This settled
the one A1-vs-A2 disagreement on the record along the way: chunk 1's id-0 header declares `nPageRects =
3`, not 1, closing exactly at the payload boundary in both chunks.

| span | file range | size | rows it carries | targets in it |
|---|---|---:|---|---|
| `creature_clut_strip` | `0x0621A0..0x062DA0` | 3,072 B | 6 rows, one per creature part | `creature.part0`..`part5` (all ON) |
| `c0_clut_band0` | `0x000870..0x001470` | 3,072 B | 6 rows, VRAM y=244..249 | `scenery.water_and_sky_gradient` (244, SHARED), `scenery.cloud_bands` (244, SHARED, different x), `scenery.sky_dome` (245), `scenery.energy_rings` (246), an unattributed row 247 (not a target), `scenery.cloud_sheet` (248), `scenery.aerial_ground` (249) |
| `c1_clut_band0` | `0x0A2048..0x0A2448` | 1,024 B | 2 rows, VRAM y=242..243 | `spare.c1_x0_y242`, `spare.c1_x0_y243` — both `enabled = false` |
| `c1_clut_band1` | `0x0A2450..0x0A2850` | 1,024 B | 2 rows, VRAM y=250..251 | `scenery.fire_column` (251); row 250 is declared by the header but not named as a target at all |

**Total whole-set envelope: 8,192 B (1.0 % of the container).** Of that, **4,832 B actually changed** —
the gap is the unattributed spare rows (declared OFF, byte-identical by construction) and
`scenery.cloud_bands`, whose 32-byte row changed **0** bytes because it is measured pure greyscale.

**Guard rails A2 named, both enforced at the call site, not in a comment:**
1. Entry `0x0000` must round-trip byte-exact, and bit 15 (STP) is sliced off and OR'd back onto every
   output word, never recomputed. `apply_word` special-cases `word == 0` before anything else runs.
2. A palette read by more than one set piece (`water_and_sky_gradient` — water/ice sheet *and* the sky
   gradient shell; `cloud_bands` — cloud bands A, B *and* C) may only be named as its **group**; the
   build refuses a target on a shared palette unless the spec says `acknowledge_shared = true`.

**Deliberately untouched, and proved so rather than assumed** (X2): sector 0 (the resource table + W3's
sequence stream), both id-3 effect-program images (W3's E1), every camera sub-file (W2's four bytes, W3's
eleven), the id-5 `SUMMON_MODEL` image, the whole id-4 header and all six 128×128 8bpp creature texel
pages (98,304 B, bit-identical), and every `GEOM` block `ef_container.scan_geom` finds (the scenery's own
geometry and UVs) — 25 named regions, 420,524 B, zero hits.

---

## 3. THE TRANSFORM SPEC — the numbers, re-measured fresh this session

Every `hue_rotate` below is **`target hue − the palette's own saturation-weighted mean hue`** — derived
from the stock palette, not guessed — and every mean-H figure is reproduced live by this report's own
`reskin.py plan` run (matches B1 exactly).

### 3.1 The creature — one hue, six pages, per-part saturation/value

A single dark-hide material appears on five of the six pages, so the hue is **one number for the whole
creature** (+182°); the per-part knobs are what separate "gold plating" from "cream claw" from
"membrane" inside a page that carries all three.

| target | VRAM | sat | val | bytes changed | mean H before → after | reads as |
|---|---|---:|---:|---:|---|---|
| `creature.part0` | (256,230) | 0.95 | 1.05 | 505/512 | 326.1 → 147.9 | violet wing membrane → spectral mist-green (the hero surface) |
| `creature.part1` | (256,231) | 0.80 | 1.02 | 504/512 | 21.0 → 202.0 | dark hide + cream claws/horn tips → pale spectral tint |
| `creature.part2` | (256,232) | 0.55 | 1.12 | 506/512 | 28.2 → 211.1 | gold neck/belly plating → cold silver-blue (desaturation is what reads as metal) |
| `creature.part3` | (256,233) | 0.90 | 1.08 | 509/512 | 4.8 → 186.5 | the dark body mass — kept a shadow |
| `creature.part4` | (256,234) | 0.55 | 1.12 | 509/512 | 25.6 → 207.7 | gold tail/underbelly — **identical sat/val to part2** so the same material lands the same colour on both pages |
| `creature.part5` | (256,235) | 0.68 | 1.06 | 506/512 | 23.0 → 204.7 | the mixed page (scales/plates/claws) — sat/val between the plating's 0.55 and the hide's 0.90 |

+182° is a **compromise**, not the first try: B1's sweep (+140 baseline, then +170/178/190/200/205/215
on parts 0/2) showed the membrane reads green anywhere in +170..+215, but the gold plating only reads
cold-silver at the bottom of that range (+190 pushes it periwinkle-violet; +170 leaves the membrane a
warm emerald). +182 is where both land acceptably.

### 3.2 The scenery — tuned independently (A2's texture-disjointness proof licenses this)

| target | VRAM | hue | sat | val | bytes changed | mean H before → after | reads as |
|---|---|---:|---:|---:|---:|---|---|
| `scenery.sky_dome` | (0,245) | −54 | 1.00 | 0.98 | 449/512 | 243.6 → 189.8 | deep teal; white cumulus (S=0) stay white by construction |
| `scenery.water_and_sky_gradient` | (0,244) SHARED | −18 | 1.00 | 1.00 | 19/32 | 206.0 → 188.5 | held in the dome's key |
| `scenery.aerial_ground` | (0,249) | +52 | 1.30 | 1.15 | 456/512 | 129.6 → 183.4 | satellite-view terrain → mist grey-teal (stock S is 0.18; a 1.00 lift would be invisible at this depth) |
| `scenery.fire_column` | (0,251) | +186 | 0.82 | 1.00 | 338/512 | 27.8 → 213.2 | amber flame → ghost-blue flame |
| `scenery.energy_rings` | (0,246) | +158 | 0.90 | 1.00 | 238/512 | 32.8 → 190.7 | orange impact rings → cyan |
| `scenery.cloud_sheet` | (0,248) | +40 | 1.30 | 1.00 | 293/512 | 159.9 → 202.2 | near-achromatic (S≈0.16); only its faint cast cools |
| `scenery.cloud_bands` | (192,244) SHARED | −18 | 1.00 | 1.00 | **0/32** | 0.0 → 0.0 | **measured pure greyscale (S=0.00, all 15 live entries) — mathematically INERT under hue/sat; declared ON so the gap is stated, not hidden** |

**Declared but OFF** (a knob one word away, not silently expanded scope): `spare.c1_x0_y242` /
`spare.c1_x0_y243` (hot saturated ramps, 109 and 80 live entries — read like flash/flame sprites) and
`spare.c0_x0_y247` (green, 254 live entries) — all three are declared by the container's own header but
attributed to **no GEOM model** by A2's 675-model census, so recolouring them would be authoring blind.

### 3.3 The clip census — the gate B3 found dead and fixed

The self-check counts the clip that can **actually** happen: a target's own `sat`/`val` knob asking for
a value outside the HSV unit cube, which `_clamp01` then flattens onto the ceiling. (The separate
0..31 channel clamp is structurally unreachable through this code path — `_clamp01` bounds the HSV
inputs before `hsv_to_rgb`, whose largest output channel is exactly `v` — so a counter on *that* step
reports 0 for every input, including a ruinous one, and B3's fix is what turned the always-true gate into
this real one.) At the shipped numbers: **19 of 2,614 live entries (0.7 %)** clip — `creature.part4`
12/255 (4.7 %, asked for `value × 1.12` against a stock peak channel of 28/31) and
`scenery.cloud_sheet` 7/255 (2.7 %, seven entries already sit at `S = 1.00` so the 1.30 lift cannot move
them further). Every other target clips nothing. Worst fraction 4.7 % against the 10 % refusal
(`BLOWOUT_FRACTION`) — a 2× margin, and the gate is proven to actually bite: B3 measured a plausible
owner retune (value 1.35 on part0) failing at 11.0 %, and value 1.6 failing at 24.7 %.

---

## 4. THE PREVIEWS — the rung's own offline eye, and what they show

Rendered by the existing kit decoder (`ff9mapkit.summons.texture`), never a repaint — stock-vs-recolour,
side by side, under `C:\gd\SCRATCH\summon-format\reskin-w4\previews\` (stock-derived art, **SCRATCH
only**, never in the repo). This report opened four of the thirteen files directly rather than trusting
B1's/V1's description alone:

- **`creature-sheet.png`** (all six creature pages through their own CLUTs): the violet, veined wing
  membrane becomes spectral green with every vein still legible; the amber-gold plating on parts 2/4
  becomes cold ice-blue with the ribbed highlights still separating from the surrounding hide; the pad
  colour filling each page's unused atlas area shifts from dusty rose to teal-grey along with everything
  else. No banding, no posterization beyond what the 5-bit palette already has.
- **`swatches.png`** (all 13 targets, stock strip over recolour strip, one cell per palette entry, a
  magenta pip marking every `0x0000` cutout): every magenta pip sits at the **same index** in both
  strips on every row — the visual confirmation that rule 1 (entry `0x0000` preserved) held. The
  `cloud_bands` row is visibly the same grey ramp top and bottom, confirming the declared invariance.
- **`scenery-fire_column.png`**: the amber flame becomes a coherent ghost-blue flame, same silhouette,
  same white highlight cores.
- **`scenery-aerial_ground.png`**: the desaturated green satellite terrain (the W2 cast's "ground that is
  not the arena") shifts to a cooler blue-green mist — subtle, because the source palette is dark and
  low-saturation, exactly as the toml's own comment predicts.

This is consistent with V1's independently-rendered preview set and its verdict ("reads as a coherent
recolour, not banding or garbage").

---

## 5. What W4 does NOT settle

1. **Lever #2 (texel repaint) is deferred, on purpose, and the hazards it would face are named, not
   hidden.** A2 §4.3 identifies two real repaint traps a palette recolour is structurally immune to:
   - **The dual-depth pack.** VRAM column 448 rows 321–383 is read as **4bpp cloud band** (CLUT
     192,244) *and* as **8bpp energy rings** (CLUT 0,246) at the same halfword addresses — a texel
     repaint there changes two pictures at once; a CLUT recolour does not, because the two readings use
     separate palettes.
   - **Time-shared columns.** Chunk 1's page uploads at VRAM x=576/640/832 overwrite chunk 0's own
     uploads at the same columns (93.0 %/89.6 % byte-different — genuinely different art per phase, not
     a redundant re-upload); a texel repaint there needs to patch both sources or the look changes only
     for part of the cast. A CLUT recolour is immune because it never touches the pixel stream.
   If a future rung wants lever #2, these two hazards are the first gate it needs, not a surprise
   mid-build.
2. **The texanim generalisation gate (A1) does not apply to ef227 and was never exercised here.** ef227's
   texanim region is **0 bytes long** — the effect never arms it — so this rung says nothing about
   whether a palette *or* texel edit interacts with a running texanim. A1 measured that only 5 of 24
   summons with the same creature-package shape carry a nonzero texanim region (`ef038` 116 B; `ef177` /
   `ef493` / `ef494` / `ef495` 364 B each), and only `ef038` actually arms it. **Any future generalisation
   of this reskin tool past ef227 must refuse or warn on `ef038`/`ef177`/`ef493-495` until the texanim
   table's internal format is read** — it is still OPAQUE (A1 §recommendations), and co-transforming a
   running texanim source alongside its CLUT is an unsolved problem this rung did not need to solve.
3. **The runtime tint's headroom, not its hue.** A3 measured that `Hi_ModifySummonModelRGB` composes
   multiplicatively and is always achromatic, so the recolour's hue survives every runtime tint tick —
   but the effect's own `colorIntensity` multiplies the palette 1.5×/2× at points in the cast, and stock's
   palette was implicitly authored with headroom for that (its brightest channel never exceeds 28 of 31).
   `creature.part4`'s 4.7 % value-clip (§3.3) is exactly this margin being spent, deliberately, and
   within the gate's own 10 % ceiling — not a defect, but the one place this rung's own numbers show the
   headroom being used up rather than banked.
4. **The three unattributed "spare" rows stay off.** They are declared by the container's own header,
   which is why `reskin.py plan` prints them at all, but no GEOM model in A2's 675-model census claims
   them — turning them on would be recolouring something the recon cannot say what it draws.
5. **Pose/geometry/timing semantics remain exactly as W1/W2/W3 left them** — this rung is a palette
   transform only; it settles nothing new about degree conventions, the bit-3 sequence selector, or the
   two-clocks law, and does not need to.

---

## 6. THE CAST PROTOCOL

### 6.1 Deploy — run by the ORCHESTRATOR, not by this report

The build is **staged, not deployed**. `deploy_reskin.py` and `revert_summon_reskin_227.py` already
exist, under `C:\gd\SCRATCH\summon-format\reskin-w4\`, generated by:

```
cd studies/custom-summons/tier-w
py reskin.py build bahamut_reskin.toml
```

(already run — the manifest, container and previews on disc are current, confirmed by this report's own
`plan` re-run matching the manifest's sha256s exactly). To deploy for real:

```
py C:\gd\SCRATCH\summon-format\reskin-w4\deploy_reskin.py
```

`--root` defaults to the live `FF9CustomMap`; the script refuses if that folder has a `ModFileList.txt`
that doesn't already list `ef227` (handle it by hand first), and it takes a **first-deploy snapshot** of
whatever the folder holds before writing — currently that is **W2's resting state**, container sha
`8146eff4…` (the 4-byte camera reframe, no retime, no reskin — confirmed live by this report). The
snapshot is per-root and taken once, so a re-deploy still reverts all the way back to the true pre-W4
state.

**⚠ Deploying the reskin REPLACES whatever container is currently live, exactly as W3 replaced W2's.**
`reskin.py` derives its container from **pristine stock** (`resources.assets`), never from a
previously-written override, so the staged artifact carries stock camera framing and stock timing plus
only the palette edit — **not** W2's 4-byte reframe and **not** W3's retime. Deploying it therefore
*supersedes* W2's currently-live camera override: the entrance reverts to stock framing/timing while
gaining the new colours. This is not a bug in the reskin; it is the same posture W3's own §6.1 already
documented for W2, one layer further down the stack. (The orthogonality proof in §1/X2 shows the three
rungs' edits are byte-disjoint and *could* be composed into one container in a future step — this build
is not that step; it is stock + reskin only.)

### 6.2 Relaunch — NONE, and this rung's hot-reload guarantee is stronger than W2/W3's

`SFX.Play()` re-reads the container fresh from disc on every cast (the same mechanism W2/W3 already
proved), **and additionally wipes the entire 50-slot managed texture cache unconditionally at the top of
every single cast** (`PSXTextureMgr.Reset()`, A3, MEASURED from the shader/engine source) — so even a
same-effect re-cast in one game session is guaranteed a cache miss and a fresh decode from the
just-written bytes. Recast to see it; no `~` reload, no field warp, no relaunch.

### 6.3 How to cast

Same delivery path W2/W3 already wired and proved: bench field 30301's ability row 196, **"Stock
Bahamut"** (`vfx1 = vfx2 = 227`, `type = 0`), confirmed still present in
`studies/custom-summons/rung8-epic/bench/rung8.field.toml:124`. `~` → Warp to field → 30301, start the
bench battle, Iviv → *Spark* → **Stock Bahamut** on the enemy group. Cleaner alternative: any save where
Garnet can summon Bahamut normally plays the same override, no bench wiring at all.

### 6.4 What you should SEE if it worked

**The whole cinematic in the new palette**, not just the creature. Bahamut himself reads as a
spectral-mist dragon — green wing membrane with its veining still visible, cold silver-blue plating
where the gold used to be, the dark hide a cooled shadow — and the effect's own satellite-view ground,
sky and fire column that show during the aerial beats (THE EFFECT-OWNED SCENERY LAW, PLAN.md) recolour
to match: a deep-teal sky and mist grey-teal ground, a ghost-blue fire column, cyan impact rings. The
camera angles and every beat land **exactly where stock always has** — this rung moved zero timing and
zero camera bytes — but because the container is built from pristine stock rather than layered on
W2/W3, the entrance is framed and timed exactly as **stock**, not as W2's wide/rolled reframe or W3's
stretched entrance (§6.1).

### 6.5 Failure table

| symptom | likely cause / what to do |
|---|---|
| Nothing changed at all | same delivery-path checklist as W2/W3 §6.5: wrong ability cast (must point at 227, not a private `ef080/084/091`), wrong mod folder, missing extension, a `ModFileList.txt` that doesn't list it, or another `FolderNames` entry shipping its own `ef227` earlier in priority. **Nothing logs either way** — `suppressMissingError` is on; this is the identical silent-fallback symptom W2/W3 already documented, now for a texture override |
| Only PART of the cast recoloured (e.g. the dragon but not the ground, or vice versa) | expected to be impossible by X2's disjointness proof and the per-target byte accounting — would mean either a stale texture-cache slot survived (shouldn't happen, A3's `Reset()` is unconditional) or a wrong/partial file landed. Report it as a finding, not operator error |
| A hole or a solid-black patch appears somewhere on the model | the one failure class a palette recolour could in principle cause — a CLUT entry drifted to/from exactly `0x0000` with STP mismatched. X3 measures this held on all 13 palettes offline; if it shows up live, it means the render path's STP-collapse behaved differently than A3's read of the shader source, and is worth reporting precisely (which body part, which frame) |
| The recolour looks washed out / a whole region reads as one flat colour | check against §3.3's clip census — `creature.part4` and `scenery.cloud_sheet` are the two targets with any clipping at all, and both are small (≤4.7%); a much larger flat region would be a genuine finding, not the disclosed headroom spend |
| Black or frozen cast | revert immediately (§6.6) and report — would mean the render path rejects something the offline self-check's HSV/STP model missed despite the round-trip proof |

### 6.6 Revert

```
py C:\gd\SCRATCH\summon-format\reskin-w4\revert_summon_reskin_227.py
```

Restores whatever the mod folder held before the **first** W4 deploy to that root — currently **W2's
resting state**, byte-for-byte (container sha `8146eff4…`, no text override). Stdlib only, idempotent,
X4-proven EXACT RESTORE in all three sandbox cases (fresh folder, already-overridden folder, explicit
`--root`). No relaunch needed to revert.

---

## 7. Files

| file | what |
|---|---|
| `studies/custom-summons/tier-w/reskin.py` | header-derived palette map (creature + both chunks' id-0 scenery CLUTs) + HSV transform with the five hard rules as refusals + self-check (byte accounting / hard rules / untouched regions / W2-W3 orthogonality / quality) + preview renderer + staging ledger + deploy/revert script emitter; verbs `plan` / `build` / `verify` |
| `studies/custom-summons/tier-w/bahamut_reskin.toml` | the declarative surface — THE KEY: SPECTRAL MIST, every hue/sat/val knob and why, in W1/W2/W3's own vocabulary |
| `studies/custom-summons/tier-w/test_reskin.py` | 38 tests; the large majority run on a synthesised container, no install needed |
| `studies/custom-summons/tier-w/w4_gates.py` | X0–X6 + the 7 negative-refusal checks |
| `studies/custom-summons/tier-w/w4-recon/A1-TEXTURES.md`..`A4-PRIORART.md` | the recon this rung's spans and transform are derived from |
| `C:\gd\SCRATCH\summon-format\reskin-w4\` | the staged mod root, 13 previews, `build_manifest.json`, `deploy_reskin.py`, `revert_summon_reskin_227.py` — **stock-derived, SCRATCH only** |

---

## CAST VERDICT — PENDING

Staged and self-checked (18/18 `reskin.py` gates, `w4_gates.py` X0–X6 + 7/7 negative refusals, 294 tests
tier-wide), previews rendered and reviewed offline (this report opened four of the thirteen directly), and
the artifact independently re-derived byte-for-byte by V1 without importing any of this rung's own code.
**Not yet cast.** The orchestrator runs §6.1's deploy script, casts per §6.3, and judges against §6.4's
"what you should SEE" and §6.5's failure table. This rung closes only when that verdict is recorded here.
