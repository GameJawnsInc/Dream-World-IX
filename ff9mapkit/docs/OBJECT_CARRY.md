# Faithful Object Carry via Real-Engine `.eb` Entry Grafting — Implementation-Ready Design

> Produced by the `object-graft-research` ultracode workflow (11 agents, 5 dimensions, adversarially
> verified against real FF9 bytes + the Memoria engine source). This is the design that replaces the
> lossy player-clone object emit for IMPORTED fields. The authored `[[npc]]`/`[[prop]]` path is untouched.

## 1. SUMMARY

Faithful object carry replaces the lossy player-clone synthesis (`content/npc.py::inject_npc` /
`content/prop.py::inject_prop`) that today renders an imported FF9 prop as "Zidane in a barrel skin" with a
**verbatim graft of the real object's `.eb` entry**: append the donor entry's bytes at a free slot via
`eb/edit.append_entry` (auto-grows the table past 10), arm it from `Main_Init` with `InitObject(slot, arg)`, and
remap only the entry's explicit slot/uid references — a same-length 1-byte in-place patch. This is the direct
generalization of `content/ladder.py::inject_ladder`'s proven `sequences` graft (append a helper entry at a free
slot + remap its `STARTSEQ` arg) from one helper function to a whole object entry plus its instancing. It renders
exactly like the source field because the engine selects an entry's bytecode by slot (`Obj.cs:50`
`ebData = allObjsEBData[sid]`) and `GetIP` is entry-local, so a verbatim entry survives a slot move untouched
except for explicit references (independently re-derived: a 7212-byte moogle entry grafted to a blank field
round-trips byte-identical with all 313 internal jumps intact). **The headline census number that scopes v1: of
1351 genuine carried objects, ~74.8% are self-contained (corrected down from the finding's 82.2% by the
adversarial verdict) — and critically, only objects whose references resolve to self/player-by-uid-250/party graft
cleanly, because the fork's blank player has only function tags [0, 1] (verified), so any carried object that
`RunScript`s a player tag ≥ 2 dangles.** v1 therefore ships verbatim graft for objects that are reference-clean OR
reference the player only by uid 250 with a tag the fork's player has — which is dominated by truly-static
`GEO_ACC` set-dressing (tents, the cask's Init, signs).

## 2. WHAT SHIPS IN V1 vs DEFERRED

**The numbers (corrected per the adversarial verdicts — trust the verdict over the finding):**

| Bucket | Share of 1351 genuine carried objects | v1? |
|---|---|---|
| **Self-contained** (no ref ops, or only self/player-uid-250) | **~74.8%** (verdict, down from finding's 82.2%) | **v1** |
| sibling-closure (refs only within the carried set) | ~3.7–6.9% | deferred (v1.5) |
| uncarried-ref (refs a sibling/region NOT carried) | ~14–18% | refuse/stub |
| expr-uid (computed, un-remappable) | 1 object total (Desert Palace scale, field 2204) | refuse/stub |

**The decisive cut is the model family.** ACC set-dressing — the actual "missing barrel/moogle" target — is
**93.5% self-contained at the Init level** (the finding), but the verdict sharpens this: the *truly
graftable-with-zero-dangling-player-tag* ACC fraction is **~55–60%**, because ~40.1% of ACC objects `RunScript`
into a **field-specific player function tag** the fork's player lacks. So:

**V1 SHIPS:**
- **Reference-clean objects** (no ref ops at all — 42.2% of all carried; the field-300 save tent is the canonical
  clean ACC graft, single tag-0 entry, zero refs).
- **Objects whose only references are self (255) or player-by-uid-250 targeting a tag the fork player has (0/1)** —
  kept verbatim, no remap.
- **Arg-instanced rows** grafted once + N `InitObject` calls (the box-row pattern).

**V1 REFUSES (falls through to the existing `[[npc]]`/`[[prop]]` author-stub, or omits):**
- Any object that `RunScript`s a **player tag ≥ 2** (e.g. field-122 cask tag-2 → player tag 24; boxes → player
  tags 11/12). These compile but dispatch to a nonexistent tag → no-op or `IndexOutOfRange`/softlock. **The user's
  own cask+boxes case hits this** — so v1 carries the cask's *placement faithfully via Init-only graft* (see §4)
  but must drop/stub its interactive tag-2.
- Any object referencing the **player by entry index** (56 objects game-wide dispatch this way) unless normalized
  to 250 first.
- Any **uncarried sibling/region** reference.

**DEFERRED:**
- **v1.5 — sibling-closure + STARTSEQ-helper-closure:** carry the referenced siblings too and remap mutually
  (reuses `inject_ladder`'s exact `sequences` machinery). Climbs coverage from ~75% to ~86%. The dominant tail
  mechanism is `STARTSEQ → type-1 Seq-helper entries` (169 refs) — identical to what the ladder grafter handles.
- **Save-point transitive closure — DEFER ENTIRELY, re-scope as synthesis.** The save point is **5 hidden objects
  + 2 STARTSEQ helpers = 7 entries PLUS mandatory player-object surgery** (moogle tag3 → player tags 13/14/15;
  player tags 13/14/15 → moogle = a cycle through the player) PLUS a shared `gEventGlobal`/MAP state contract. The
  graft appends sibling entries; it cannot rewrite the fork's player. A future `content/savepoint.py` should
  **synthesize** a save region + visible set-dressing props + optional cosmetic jump-out invoking the engine
  save-menu opcode directly — not graft 6700 bytes of donor menu bytecode. Already excluded by `scan_objects`'
  hidden-flag gate; v1 adds the visible-cask refuse-rule so no fragment leaks.

## 3. THE CROSS-REFERENCE REMAP TABLE

The complete, verified set of reference-bearing opcodes and expression tokens the remap pass must inspect.
**Every listed ref arg is a 1-byte immediate, so every patch is same-length** (length-preserving, like the ladder
STARTSEQ patch). Arg widths confirmed against `eb/_optables.py`; uid resolution confirmed against
`EventEngine.cs:899` `GetObjUID` and `DoEventCode.cs` handlers.

**Remap value rules** (computed per object: `uid_old = arg2==0 ? S_old : arg2`; `uid_new = arg2==0 ? S_new : arg2`):
- **250 (player) / 255 (self) / 251–254 (party)** → **KEEP verbatim** (slot-independent engine specials).
- **donor player ENTRY INDEX** (e.g. 23 in field 122) → **rewrite to 250** (the slot-independent `controlUID`
  alias — 250 dynamically resolves to whoever holds control).
- **a sibling we ARE carrying** → rewrite to that sibling's `uid_new`/`S_new`.
- **a sibling we are NOT carrying** → **REFUSE** the standalone graft (or carry the closure in v1.5).
- **a computed (expression) uid** → **cannot statically remap → REFUSE**.

**Immediate-arg opcodes (uid resolved via `GetObj1=GetObjUID(getv1())`):**

| Hex | Name | Ref arg(s) | Space |
|----|------|-----------|-------|
| **0x09** | InitObject (NEW3) | arg0 = slot; arg1 = uid (0⇒slot) | SLOT + UID |
| **0x07** | InitCode (NEW) | arg0 = slot; arg1 = uid | SLOT + UID |
| **0x08** | InitRegion (NEW2) | arg0 = slot; arg1 = uid | SLOT + UID |
| **0x10** | RunScriptAsync (REQ) | arg1 = uid | UID |
| **0x12** | RunScript (REQSW) | arg1 = uid | UID |
| **0x14** | RunScriptSync (REQEW) | arg1 = uid | UID |
| **0x24** | WalkTowardObject (MOVA) | arg0 = uid | UID |
| **0x39** | ShowObject (MESHSHOW) | arg0 = uid | UID |
| **0x3A** | HideObject (MESHHIDE) | arg0 = uid | UID |
| **0x4C** | AttachObject (ATTACH) | arg0 attachedUid, arg1 carryingUid (arg2 bone = NOT a uid) | UID×2 |
| **0x4D** | DetachObject (DETACH) | arg0 = uid | UID |
| **0x51** | TurnTowardObject (TURNA) | arg0 = uid | UID |
| **0x87** | TurnInstantEx (DDIR) | arg0 = uid | UID |
| **0x8A** | SetSoundObjectPosition (SEPVA) | arg0 = uid | UID |
| **0x8F** | SetModelColor (CHRCOLOR) | arg0 = uid | UID |
| **0x95** | WindowSyncEx (MESA) | arg0 = uid | UID |
| **0x96** | WindowAsyncEx (MESAN) | arg0 = uid | UID |
| **0x97** | ReturnEntryFunctions (DRET) | arg0 = uid | UID |
| **0x9F** | SetObjectSize (CHRSCALE) | arg0 = uid | UID |
| **0xA9** | CalculateScreenPosition (GETSCREEN) | arg0 = uid | UID |
| **0xAD** | MoveInstantXZYEx (DPOS3) | arg0 = uid | UID |
| **0xBB–0xBE** | TimedTurn/WaitTurn/RunAnim/WaitAnim Ex | arg0 = uid | UID |
| **0xBF** | MoveInstantEx (DPOS) | arg0 = uid | UID |
| **0xB5** | PretendToBe (PRETEND) | arg0 = uid | UID |
| **0xC2** | StopTextureAnimation (TEXSTOP) | arg0 = uid | UID |
| **0x43** | RunSharedScript (STARTSEQ) | arg0 = entry index | SLOT (the ladder remap model) |
| **0x44 / 0x45** | WaitSharedScript / StopSharedScript | arg0 = entry index | SLOT |

**Expression-token references (must walk `disasm.read_expr` streams — NOT raw-byte search; ~49% of carried
objects contain one):**

| Token | Layout | Ref | Remap |
|-------|--------|-----|-------|
| **0x78** B_OBJSPECA (obj-var read) | `78 <uid> <field>` (uid first; `region.obj_var` order) | UID | 250/255 keep; sibling→new uid; else refuse |
| **B_PTR** (obj-uid→value) | 1 immediate uid byte | UID | static, remappable (rare) |
| **B_ANGLEA / B_DISTANCEA** | uid = computed sub-expression | UID (dynamic) | **un-remappable** unless bare const → flag |

**KEEP (no remappable operand — do NOT touch):**
- **0x16 / 0x18 / 0x1A** RunScriptObject* (REPLY*) — target = `getSender(gExec)`, the dynamic caller, no operand.
- **0x1D** CreateObject, **0xA2** WalkXZY, **0xD4** AttachObjectOffset, **0x44/0x45** seq-self — act on `gCur`/self,
  no uid operand. (Note: AttachObjectOffset 0xD4 has **2-byte args** `[2,2,2]` — not a uid, but don't mis-decode
  it as 1-byte.)

## 4. THE GRAFT ALGORITHM

**Critical policy decision (per all four adversarial verdicts): graft the Init-defining behavior, not blindly the
whole multi-func entry.** The field-122 cask is a **384-byte, 5-function entry** (tags 0,1,2,30,29) whose
tag-2/30 interactive funcs `RunScript` the player and self by field-specific tags. v1's faithful render needs
**tag 0 (model/pose/placement/flags) + tag 1 (loop)** carried verbatim; the interactive tags must be **dropped or
stubbed** if they reference a player tag the fork lacks. So the carry policy is per-object:

- **Whole-entry verbatim** when every function's refs are clean (self/player-tag-0-or-1/carried-sibling).
  Maximizes fidelity.
- **Init-only (+ loop) verbatim** when later tags `RunScript` an absent player tag → carry tags {0,1} + any
  purely-visual tags, drop interactive tags. Still renders the object identically (model/pose/facing/flags/size
  all live in Init); only loses the field-specific puzzle interaction (which can't port anyway).

**Position-source classes** (`scan_objects` already classifies these): (a) self-positioning via the object's OWN
Init D9 consts — **the common case, field 122 cask is this**, no Main_Init D9 needed; (b) self-positioning via
literal `MoveInstantXZY` immediate; (c) Main_Init-D9-positioned (the classic "moogle" pattern — rare, NOT present
in field 122). For (a)/(b) the position rides along inside the verbatim entry; only (c) needs a Main_Init D9
splice immediately before the `InitObject`.

```
graft_objects(data, specs, load):
    # PASS 1 — reserve all slots first (so sibling cross-refs can resolve)
    donor2new = {}
    for spec in specs:
        slot = EbScript.from_bytes(data).first_free_slot()
        raw  = carry_bytes(load(spec.bin), spec.carry_tags)   # whole-entry, or Init+loop subset
        data = edit.append_entry(data, slot, raw)             # verbatim; auto-grows past 10
        donor2new[spec.donor_idx] = slot

    # PASS 2 — remap refs in place + arm from Main_Init
    for spec in specs:
        slot = donor2new[spec.donor_idx]
        remap_uid, remap_slot = build_value_map(spec.donor_player_entry, donor2new)
        data = remap_refs_in_place(data, slot, remap_uid, remap_slot,
                                   self_old=spec.donor_idx, self_new=slot)
        for arg in spec.instances:          # arg-instanced row -> N InitObjects, one entry
            if spec.needs_d9:               # class (c): D9 sets immediately before InitObject
                block = b"".join(region.set_var(0xD9, i, v) for i,v in spec.needs_d9.items())
                block += opcodes.init_object(slot, arg)
                data = edit.insert_bytes(data, main_init_start(data), block)
            else:                           # class (a)/(b): plain arm into a Wait filler / insert
                data = edit.activate(data, opcodes.init_object(slot, arg))
    return data

remap_refs_in_place(data, slot, remap_uid, remap_slot, self_old, self_new):
    region_bytes = entry_slice(data, slot)
    for ins in iter_code(region_bytes, 0, len(region_bytes)):
        spec = REF_OPS.get(ins.op)
        if spec:
            for kind, idxs in (("uid", spec.get("uid",[])), ("slot", spec.get("slot",[]))):
                fn = remap_uid if kind=="uid" else remap_slot
                for ai in idxs:
                    if not ins.arg_is_expr[ai]:                 # immediate only
                        bpos = _arg_byte_offset(ins, ai)        # DECODER-derived, never fixed +N
                        old = region_bytes[bpos]
                        region_bytes[bpos] = (self_new if old==self_old else fn(old)) & 0xFF
        _remap_expr_obj_uids(region_bytes, ins, remap_uid)      # walk 0x78 tokens in expr args
    write_entry_slice(data, slot, region_bytes)                 # same length -> no relayout
```

**Three correctness invariants (each a verdict-validated gotcha):**
1. **`_arg_byte_offset(ins, ai)` must be decoder-derived** = `head(1 or 2 if 0xFF-paged) + argflag(1 if op≥0x10
   and argc≠0) + Σ widths of args 0..ai-1`. The ladder's hardcoded `body[ins.off+2]` is correct only for
   STARTSEQ's single no-argflag arg; multi-arg ops with an argflag byte need the computed offset.
2. **Expression-uid remap walks `read_expr` token streams** for the `0x78 <uid>` token (49% of objects have one)
   — a raw-byte 0x78 scan produces false positives (verified). Skip B_ANGLEA/B_DISTANCEA computed uids → refuse.
3. **Same-length patches only** — assert each patched arg width == 1 before writing, so internal `0x0B`/`0x06`
   switch jumps (function-relative) survive untouched.

## 5. THE NEW API / FILE SURFACE

**NEW `ff9mapkit/ff9mapkit/content/object.py`** — the graft module (structurally a clone of `inject_ladder`,
~80–120 lines):
- `graft_objects(data, specs, load) -> bytes` — the two-pass driver above.
- `remap_refs_in_place(...)`, `build_value_map(donor_player_entry, donor2new)`, `_arg_byte_offset(ins, ai)`,
  `_remap_expr_obj_uids(...)`, `REF_OPS` (the §3 table), `carry_bytes(entry_bytes, carry_tags)`.
- Imports **only** `eb/edit.py` + `eb/disasm.py` + `eb/opcodes.py` + `content/region.py` (for `set_var`/`obj_var`).
  **Never imports `inject_npc`/`inject_prop`.**

**`ff9mapkit/ff9mapkit/eventscan.py`** — add `scan_objects_verbatim(eb_bytes) -> list`:
- Reuses the existing `scan_objects` Main_Init walk + skip rules (player/`GEO_MAIN`/hidden) and `_entry_bytes`.
- **Add the player-entry-index guard** (`if e.index == _player_entry_index(eb): continue`) — `scan_jumps` already
  does exactly this at line 349; closes the 15-field player-false-positive bug (`scan_objects` line 463 only skips
  `DefinePlayerCharacter`-in-own-Init).
- Returns per object: `donor_idx`, **verbatim entry bytes**, `instances` (InitObject args), `needs_d9` `{idx:val}`
  (empty for class a/b), `donor_player_entry`, a **classified ref map** (each ref's op/arg/old-value/class ∈
  {self,player,party,sibling,uncarried,expr}), and a **graft_safety flag** (`clean` | `init_only` | `refuse`).
- `scan_objects` stays unchanged (feeds the human-readable `[[npc]]`/`[[prop]]` TODO stubs); add
  `scan_objects_verbatim` to `scan_content`.

**`ff9mapkit/ff9mapkit/extract.py`** — `_imported_content_toml`:
- Emit an **`[[object]]`** block + `<name>.objectI.bin` sidecar (verbatim entry slice, **gitignored as
  SE-derived** like `.jump.bin`/`.climb.bin`), gated on `out_dir is not None` (mirrors the ladder/jump sidecar
  emit at `extract.py:310,333`). TOML carries `bin`, `instances`, `needs_d9` (only if class c),
  `donor_player_entry`, `carry_tags`, `kind`. Keep the CLI summary key **`"objects"`** stable.

**`ff9mapkit/ff9mapkit/build.py`** — after the jumps block (~line 1428):
```python
objs = project.raw.get("object", [])
if objs:
    from .content import object as _object
    eb = _object.graft_objects(eb, objs, load=lambda ref: project.path(ref).read_bytes())
```
Plus a **lint hook** near the `[[jump]]` checks: assert each `bin` exists + decodes; resolve refs through the
value-map; **error on any dangling slot/uid** (uncarried sibling, or a player-tag the fork player lacks); warn on
instance-uid collision and on talkable-carry (missing `.mes` text). Gated entirely on `project.raw.get("object")`.

**`eb/edit.py`** — **no new primitive needed** (`append_entry`, `activate`, `insert_bytes`, `grow_entry_table` all
suffice; optionally factor `_arg_byte_offset` here). **`.gitignore`** — add `*.object*.bin`.

**UNTOUCHED (the additive guarantee):** `content/npc.py`, `content/prop.py`, `prop_archetypes.py`,
`archetypes.py`, `_held_poses.py`, the `build.py` `[[npc]]`/`[[prop]]` loops (1104–1187). Authored single-field
builds stay byte-identical (the new branch is a no-op when `[[object]]` is absent; `first_free_slot` returns the
same value).

## 6. PHASED BUILD ORDER WITH REGRESSION CHECKPOINTS

**Baseline to hold green: 628 passed (verified ~51–57s).** Every PR must show ≥ 628 + new tests, all green. The
headline tripwire is **`test_build.py::test_build_reproduces_hut_int_eb_byte_exact`** (SHA-256 pin on the whole
authored pipeline — flips if slot allocation or any shared primitive changes).

**Phase 1 — `scan_objects_verbatim` + the player-entry guard.**
- Gate (must stay green): `test_eventscan.py` (all 18, incl. `test_scan_objects_skips_script_hidden_save_machinery`),
  `test_eb.py` round-trips.
- Add: a test that `scan_objects_verbatim` returns verbatim entry bytes + a correct classified ref map for the
  field-122 cask (install-gated) and a kit-injected prop (pure); a test that the player-entry-index guard drops
  the 15-field false-positive (pick one, e.g. field 1663).
- In-game playtest: none yet (offline scan only).

**Phase 2 — `content/object.py` graft + remap, no build wiring.**
- Gate: `test_ladder.py`, `test_jump.py` (the graft precedents — `graft_objects` reuses their primitives),
  `test_eb.py` append/grow identity (`test_grow_entry_table_is_a_noop`,
  `test_append_entry_autogrows_past_template_ceiling`).
- Add (`tests/test_object_graft.py`, pure): verbatim-bytes equality except the documented remap patch; grafted-eb
  round-trips + every entry disassembles; `scan_objects_verbatim` reads back the grafted object identically;
  sibling-uid remap lands on the new slot while 250/255 stay; arg-instanced row grafted once + N InitObjects;
  table grows past 10.
- In-game playtest: none yet.

**Phase 3 — build wiring (`[[object]]` consume) + lint.**
- Gate: **`test_build_reproduces_hut_int_eb_byte_exact`** (the authored golden — proves additivity),
  `test_build.py:535` flag-band identity, `test_content.py` NPC/prop byte oracles.
- Add: `test_authored_path_unchanged_by_graft_module_import` (importing `object.py` + the new branch leaves
  `inject_npc`/`inject_prop` output identical); the dangling-ref lint error fires on a cask that RunScripts player
  tag 24.
- In-game playtest: none yet (build is offline).

**Phase 4 — extract emit (`[[object]]` + sidecar) — THE ONE EMIT-SHAPE CHANGE.**
- **Update:** `test_eventscan.py::test_imported_content_toml_is_valid_and_complete` (lines 109–123). Keep the
  summary `"objects": 1` (stable CLI contract). Change the call to pass **`out_dir=tmp_path`** (objects need a
  sidecar dir, gated like ladders/jumps), then assert `(tmp_path/"field.object0.bin").exists()` and the parsed
  TOML has a length-1 `[[object]]` list with the carried `slot`/`instances`. (No committed import-text golden
  exists — verified by grep — so nothing else regenerates.)
- Add: `test_imported_content_emits_object_sidecar` (the inverse of the emit change).
- In-game playtest: none yet.

**Phase 5 — THE CLOSING IN-GAME PLAYTEST (the only thing offline tests can't prove).**
- Add (install-gated): `test_field122_cask_grafts_upright_at_expected_pos` — graft the field-122 cask, assert
  `scan_objects_verbatim` of the result reports `model == "GEO_ACC_F0_CSK"`, `pose == 1904`, **`(x,z) == (-250,
  -571)`** (measured), and the grafted Init bytes (`SetModel`/`SetStandAnimation(1904)`/
  `MoveInstantXZY(-250,-2,-571)`/`SetObjectLogicalSize(1,50,50)`/`SetObjectFlags(37)`) match the source verbatim
  with **zero Zidane-only ops** (the anti-"barrel skin" assertion).
- **Human playtest (the commit gate):** `ff9mapkit import fbg_n08_udft_map122_uf_sto_0 --out F` → `build` →
  `tools/deploy_field.py` → F6 → Warp → confirm the cask renders **upright at the right spot** (not the
  upside-down player-clone) and the two box rows carry. Also confirm the box-instancing switch actually yields 3
  distinct positions (the one mechanism the verdict flagged as asserted-but-unverified). Per the project's "run
  the branch like the others" cadence, hold the commit until this lands.

## 7. OPEN RISKS & UNKNOWNS

**Needs an in-game check (cannot self-verify):**
1. **The cask renders upright at (-250,-571).** Offline proves the bytes are verbatim + correctly placed; only a
   playtest proves the visual. This is the Phase-5 commit gate.
2. **Arg-instancing yields 3 distinct box positions.** The field-122 box switch reads a **Map/Instance-scoped
   var** (`opD1(45)`, src Map), NOT the uid as the cross-ref finding claimed (verdict correction). Grafting one
   entry + 3 `InitObject(slot, 128/129/130)` *should* reproduce 3 positions if the switch keys on the instance var
   the engine seeds per `InitObject` — but this is **asserted, not demonstrated**. If positions collapse, the row
   needs per-instance D9 seeding in Main_Init.
3. **Talkable carry.** ~33% of carried objects are talkable; their tag-3 `WindowSync(textid)` references a TXID
   absent from the fork's `.mes` → empty/garbage window. v1 default should **stub tag-3** for talkable carries
   (lint-warn), not graft it verbatim.

**Worst-case failure modes:**
- **Dangling player-tag → softlock.** A carried object that `RunScriptSync`s an absent player tag *waits forever*
  on a callee that never completes → frozen field. Mitigation: the Init-only carry policy (§4) + the lint
  refuse-rule must catch every player-tag-≥2 reference. **This is not a tail case — it fires on the user's own
  cask+boxes**, so the refuse/Init-only logic is load-bearing on the very first import.
- **Mis-patched arg offset** → corrupts the wrong byte → garbage object or crash. Mitigation: decoder-derived
  `_arg_byte_offset` + assert width==1; covered by the remap round-trip test.
- **Un-remapped expression-uid** (the 0x78 token or B_ANGLEA) → object placed at (0,0) or follows the wrong
  sibling. Mitigation: expression-aware remap pass; refuse computed uids.
- **Slot-allocation drift breaking the hut golden** → the SHA-256 pin flips. Mitigation: the entire path is gated
  on `project.raw.get("object")` (empty for authored fields); Phase-3 `test_authored_path_unchanged` is the guard.
- **Scope creep into the save point.** The save cluster (7 entries + player surgery + state contract) is
  structurally un-graftable; v1 must hard-refuse it and the deferred work must be re-scoped to synthesis.

**Minor cleanup found en route (not blocking):** `content/prop.py`'s comment "save-moogle (field 300, entry 5)"
is **stale** — field 300 entry 5 is a type-1 region; the moogle is entry 9 (shown, Mene). Fix to "field 122
entries 5–10 (hidden-in-cask); field 300 entry 9 (shown, Mene)."

---

**Engine ground truth:** `Memoria/Assembly-CSharp/Global/Objects/Obj.cs:18,50`,
`.../Event/Engine/EventEngine.cs:899`, `.../EventEngine.DoEventCode.cs:119,143,3428`, `.../Global/EBin.cs:1207,1664`.
**Verified facts:** blank-fork player = entry 1, tags **[0,1]** only; field-122 cask = slot 10, 384B, tags
[0,1,2,30,29], (-250,-571), pose 1904; baseline 628 tests pass.
