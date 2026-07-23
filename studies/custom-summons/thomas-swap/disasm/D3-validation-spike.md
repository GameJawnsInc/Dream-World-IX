# D3 — THE REAL-BYTES VALIDATION SPIKE (geometry + skeleton + motion, cross-checked live)

**Slice D3 (validation spike).** A design that hasn't touched real bytes is a hypothesis. This spike
takes the *faithful transplant* thesis — *put OUR model where the real creature renders so it inherits
the creature's actual animation + camera* — and drives it into the actual bytes of a stock creature,
far enough to answer the load-bearing questions the transplant depends on, and cross-checks the offline
decode against the **live s53 BONES probe**.

Instrument: **`transplant_spike.py`** (this directory, committable — reads a caller-supplied LOCAL blob
and prints counts/offsets/sample values; **no stock bytes embedded or emitted**). Geometry decode is
delegated to the committable `ef_container.py`; the spike adds the **motion-clip decoder** (M5) and the
**forward-kinematics pose composition** (M4/M5), both logic not content. Reference creature: **ef227 =
`Bahamut__Full`** (`SpecialEffect.cs:99`); generalisation checked on **ef261 = Odin** and the negative
control **ef000**. Live cross-check reads only the user's own
`…/FINAL FANTASY IX/sfxmeshprobe.log` (local, not committed).

Every number below is reproducible: `py transplant_spike.py` (defaults to the local ef227 + the install
log). Native claims cite `fn@rva` (x64 `FF9SpecialEffectPlugin.dll`, ImageBase `0x180000000`); format
claims cite `M4/M5/D3` which are themselves byte-validated.

---

## 0. HEADLINE — the transplant's data dependencies are REAL

The faithful lever is **viable at the data level, and now proven on real bytes**:

| the transplant needs… | on real ef227 bytes | verdict |
|---|---|---|
| the creature's skeleton, as a portable hierarchy | **93 nodes, a forward-referencing parent+length tree** | ✅ PROVEN |
| skinning simple enough to re-bind our mesh | **rigid, run-length, exactly ONE bone per vertex** (`maxVtxIdx == nVert−1`, both meshes) | ✅ PROVEN |
| the creature's real per-frame motion, offline | **8 Euler clips decode, tile exactly, frame counts exact, angles well-formed** | ✅ PROVEN |
| the decode to actually reconstruct the real pose | **offline model-space skeleton reproduces the LIVE per-axis extent to ~1 %** (2 of 3 sorted axes) | ✅ PROVEN (magnitude) |
| a faithful DCC→clip *exporter* | the exact PSX RotMatrix Euler **order** is still not disasm-derived | ⚠️ the one fuzzy piece |

The single sharpest result: an offline skeleton composed purely from `ef227.bytes` (clip 0, frame 0) has
sorted axis spans **[614, 2657, 4437]**; the live BONES probe's nearest at-scale-1 frame (f224) has
sorted spans **[740, 2619, 4431]** — ratios **[0.83, 1.01, 1.00]**. Two of three axes match to within
1.4 %, from data alone. The decode is not a hypothesis; it reconstructs the creature.

---

## 1. Q1 — SKELETON: bones + hierarchy (PROVEN, export-ready)

`ef_container.creature_geom` → `Geom.bones` (the `BoneLink[boneCount−1]` table at GEOM `+0x18`,
authority `fn 0x7de7 @0x81aa`). The spike lifts it into `parents[]` / `lengths[]` (node 0 = the implicit
root; row `r` describes child node `r+1`).

* **bone count = 93**, bonelink rows = 92. Matches the live **s53 BONES probe `n = 93`** across the
  whole cast (480 rows, `live_n = [93]`, one value only). The most important number for a transplant —
  the format and the running engine agree on the skeleton size.
* **forward-referencing tree**: `parent < child` in **92/92** links; middle byte 0 in **92/92** (a
  well-formed tree with no sort pass — the format's hard ordering constraint, M5 §4). `parent[1..15] =
  [0,1,2,3,4,5,6,7,8,1,10,11,12,13,14]` — the `…8,1,10…` is a second limb branching back at node 1;
  **66 distinct parents** ⇒ a genuinely branched skeleton, not a chain.
* bone **lengths** sane (`145,220,589,467,467,467,467,348,…` units) — the `(0,0,length)` local
  translations (M5 §4).
* **Generalises**: Odin (ef261) = **97 nodes**, 96 links, forward-referencing 96/96, 75 distinct
  parents. ef000 (non-summon) correctly has **no creature package**.

---

## 2. Q2 — SKINNING: run-length rigid, one bone per vertex (PROVEN, export-ready)

`verts_per_bone[boneCount]` + the D3 chain-closure invariant `maxVertexIndex == nVert − 1`
(authority `fn 0x4eb0 @0x509d`, the per-bone vertex run loop).

| ef227 | mesh0 | mesh1 |
|---|---|---|
| nVert (= Σ verts_per_bone) | 797 | 642 |
| max vertex index used by any primitive | **796** | **641** |
| closure `maxVtxIdx == nVert−1` | ✅ | ✅ |
| one bone per vertex (`len(bone_of_vertex) == nVert`) | ✅ | ✅ |
| bones that actually own vertices | 45 / 93 | 57 / 93 |

Sample `vertex→bone`: mesh0 verts 0–9 all belong to **bone 1**; the mid-mesh sample (vtx ~398) belongs
to **bone 54** — contiguous runs, exactly the run-length model. **There is no per-vertex weight and no
per-vertex bone index**; the bone is *implied by the run* (M4 §4 confirmed). This is the property that
makes re-binding trivial: our mesh needs only a one-bone-per-vertex assignment (or a hard-skin
conversion), never a weight solve.

**Transplant consequence (hard constraint, now confirmed on bytes):** FF9 skinning is rigid. A DCC rig
with soft weights must be hard-bound (each vertex → its dominant bone) before it can wear this format —
or the transplant drives *our* mesh in *our* engine (the SFXDataMesh route) and only borrows the bone
*matrices*, sidestepping the constraint. Both lanes are open; the constraint only bites the "emit a
stock-format creature" lane.

---

## 3. Q3 — MOTION: the per-frame Euler tracks decode and tile (PROVEN structure)

The spike ports M5 §2 end-to-end: header (0x14 B), root translation (constant-or-`s16`-track per axis
gated by clip `flags`), and the **12-bit two-stream rotation** (8-bit coarse track + 4-bit fine nibble,
or a literal per axis gated by the per-node RotKey flags). Authority: `fn 0x7820` branch M
(`0x7a20..0x7dba`), decode cites in M5 §11.

**All 8 Bahamut clips (frame counts `[24,30,26,48,40,68,82,28]` — exact to M5 §3 and D3 §5.2):**

* **Tiling is exact, 8/8.** Decoding *every* frame and tracking the highest motion-relative byte any
  read touches, `max_touched ≤ span` for all 8 clips (e.g. clip0 touched `0x1070` == span `0x1070`; the
  ≤2-byte slacks are the 4-byte alignment pads between clips, D3 §4.1). A wrong header, offset, stride,
  or frame-count could not tile.
* **Angles are well-formed.** Interpreted as `s16` reduced mod 4096 (the value PSX RotMatrix uses).
  **Literal channels decoded**: RotKey field stores `angle/16` signed — clip0 node0 coarseKey
  `c0ff 0000 0000 0700` → flags 0x7 (all literal), a0 `0xffc0` = −64 → −64×16 = **−1024 = −90° constant
  root pitch**. This retired the earlier "64512 out of range" red herring (it was `0xFC00`, i.e. −1024
  before the mod).
* **Animated fraction 63–157 of 279 channels = 22.6 %–56.3 %** — matches M5 §3.1's independent
  measurement (22 %–56 %) to the tenth of a percent.
* **Track continuity (Bahamut): smooth.** Frame-to-frame circular 12-bit step over *all animated
  channels*: **p95 = 25–87 / 4096 (≈2–8°/frame)**. The occasional `max` of ~2047 is a single joint
  **snapping to rest** in a clip's tail (clip2 node0 axis0: `…2060, 2047, 2047, 0, 0…`), not decode
  garbage — the values before and after are clean and the p95 stays tiny.

**Generalisation (Odin ef261):** 7 clips `[70,14,20,49,21,60,45]`, all tile within span, animated
167–235/291. Continuity is **choppier** (p95 up to 603 on a 14-frame clip) — consistent with Odin's
violent, short summon rather than a decode fault (a fine-nibble error would be ≤15/4096, not 600; these
are genuine fast coarse-track moves). So **structure is PROVEN across creatures; the *smoothness* of the
motion is a per-creature semantic, not a universal invariant** — don't gate a tool on "continuous."

**The cast vs a clip (don't conflate):** clips are short (24–82 frames) and are *sequenced/looped by the
`.seq`* into the ~510-frame cast (log frames 50–561). "Frame count matches the cast" is the wrong test;
the right test — each clip's header frame count matching its exact byte tiling — passes 8/8. Loop-vs-hold
is a `.seq` operand, not clip data (M5 §6).

---

## 4. Q4 — CROSS-CHECK: the offline pose reconstructs the live creature (PROVEN magnitude)

The spike composes the full 93-node world skeleton for clip0/frame0 via the hierarchy pass
(`world.R[k] = R[parent]·local.R[k]`, `world.t[k] = R[parent]·(0,0,len) + t[parent]`, M5 §4/§5), with
the runtime root `R_root/S/T` omitted (identity/1/0), then compares its node-translation AABB against the
live **s53 BONES** AABB (which *is* the composed node-translation cloud, `*(SummonData+0x38)`).

* **`n = 93` matches** (both agree on the skeleton size — §1).
* **Sorted axis spans (the sharpest falsifiable number):** offline **[614, 2657, 4437]** vs live f224
  **[740, 2619, 4431]** → ratios **[0.83, 1.01, 1.00]**. The axis *permutation* between the two is the
  live pose's world-frame rotation `R_root` (which my model-space pose omits); the sorted multiset is
  rotation-invariant and **two of three axes match to ≤1.4 %**, from bytes alone.
* **Robust to the unverified Euler order.** Recomputing the posed half-diagonal under all 6 XYZ
  composition orders gives **2319–2604** — a ≤12 % spread, all near the live **2600**. So the magnitude
  cross-check does **not** depend on guessing the Euler order right; bone-length accumulation dominates
  the extent. (ZYX happens to best-fit the live per-axis shape.)
* **Scale sanity confirmed.** The live half-diag band is **42 → 7771** (M5's authored scale sweep
  0.02×→3.0×); the posed scale-1 value 2604 lands inside it and the nearest frame (f224) is squarely in
  M5's scale≈1.0 "settle" region (frames 178–300). Independent confirmation of M5 §8's scale finding.
* **Invariant radius** (rotation-independent max root→leaf accumulated |length| = **4213**) exceeds the
  median folded live half-diag (3647) — the skeleton folds inward from its fully-extended bound, as it
  must. (It's below the live *max* 7771 because that frame is scaled ~3×; expected.)

---

## 5. WHAT PARSED CLEANLY (export-ready) vs WHAT IS STILL FUZZY

**EXPORT-READY (byte-validated, cross-checked, PROVEN):**
1. the skeleton hierarchy — node count, parent indices, bone lengths, the forward-reference ordering
   constraint;
2. the rigid run-length skinning — vertex→bone from `verts_per_bone`, one bone per vertex, closure exact;
3. the geometry pools themselves — already round-trip byte-identical via `ef_geom_writer.py` (M4/D3);
4. the motion clip **reader** — header, root translation, the coarse+fine 12-bit rotation, literal vs
   track gating, exact tiling; angles reconstruct the real pose to ~1 %.

**STILL FUZZY (named, so the next rung can close them):**
1. **The PSX RotMatrix Euler composition ORDER.** The three `RotMatrix` calls are axis x,y,z (M5 §2.3
   cites `0x37a0/0x3850/0x3910`) but whether the net is `Rz·Ry·Rx` or another order is **not
   disasm-derived**. *Not* load-bearing for reading the creature or for driving our mesh by the live
   bone matrices (those come pre-composed from `*(SummonData+0x38)`). *Is* load-bearing for a faithful
   **DCC→clip exporter** (a wrong order distorts the posed shape — the axis magnitudes stay but land on
   the wrong axes). Closing it = single-step `fn 0x7820`'s three RotMatrix calls (or match a known
   psyq RotMatrix source) and confirm against a live single-bone matrix from the probe.
2. **No motion round-trip harness yet.** Geometry has one (`ef_geom_writer`, byte-identity); motion does
   not. The reader is functionally validated (tiling + pose reconstruction), but a couple of secondary
   fine-path bit-lanes (M5 cites a `shl …,0x14` in the fine assembly) aren't *proven* byte-exact by an
   emit→compare loop. Recommend a `motion_writer.py` with the same byte-identity acceptance before the
   exporter ships.
3. **The rest-snap steps (2047/2048).** Benign and real (tail-frame joints snapping to 0), but their
   exact authoring intent (padding vs a genuine keyframe) is unconfirmed. A reader must reproduce them;
   an exporter should be able to emit them.

**Not touched here (out of this slice, per the roadmap):** the texture/CLUT payload (D3 §5, needed for a
stock-*look* creature, not for OUR-model transplant), the texanim table, and the id-3 MIPS staging
program (`.seq` R_root/S/T draw args — the only genuinely runtime term).

---

## 6. THE PRACTICAL TRANSPLANT PATH THIS SPIKE DE-RISKS

Reading the bone matrices to drive our own model is choreography/pose data (the sanctioned class, like
the camera track). The spike shows the data supports two faithful lanes:

* **Lane A (drive our mesh with the live skeleton).** Extend `SfxMeshProbe.cs` to log the per-bone world
  matrices `*(SummonData+0x38) + k*0x20` (`Hi_GetSummonBoneMatrix @0x18630` reads exactly one), and pose
  OUR bone-named FBX (the model pillar, `SFXDataMesh.cs`) by binding each of our bones to the creature's
  node of the same index each frame. Our mesh inherits the creature's *real* animation and the native
  camera. Requires our rig to be **skeleton-compatible** (same node count / forward-ordered / one bone
  per vertex or hard-skinnable). This is the "faithful transplant the overlay could never be."
* **Lane B (emit a stock-format creature from our model).** Fully specified by M4/D3 (writer) + this
  spike (skeleton/skinning constraints) + M5 (motion). Blocked only on fuzzy item #1 (Euler order) for
  the motion clip; the geometry writer is already byte-identical.

Either way the deliverable stays a **pipeline + tools** operating on the user's own locally-decoded
motion; no stock creature mesh/anim is shipped.

---

## 7. PROVENANCE

Read-only static analysis of the user's own installed `FF9SpecialEffectPlugin.dll`, plus a structural
read of locally-extracted stock `ef###.bytes` under `C:/gd/SCRATCH/summon-format/` and the user's own
`sfxmeshprobe.log`. **No DLL modified or redistributed. Nothing game-derived — geometry, animation,
texture, or raw container bytes — written into the repository.** `transplant_spike.py` embeds no game
bytes; it reads a caller-supplied blob and prints counts / offsets / sample values / field statistics.

## 8. FILES

* **`transplant_spike.py`** (this directory, committable) — the spike: motion-clip decoder
  (`read_clip_header` / `decode_rotation` / `decode_root_translation`), forward kinematics
  (`compose_skeleton` / `max_chain_length`), and the live-log cross-check (`read_bones_log`). CLI:
  `py transplant_spike.py [EF_BYTES] [--log LOG] [--clip N] [--frame F]`.
* Depends on the already-committed `ef_container.py` (geometry) / `ef_geom_writer.py` (geometry writer,
  byte-identity harness).
