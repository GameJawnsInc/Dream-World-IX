# Player-Function Graft

> **Status: SHIPPED + in-game proven.** This began as an implementation-ready design doc; the implementation now
> lives in `content/player.py` (`graft_player_funcs`, `PlayerTagAllocator`, `ensure_player_anim_packs`,
> `remap_player_func_siblings`) with build wiring in `build.py` and the `import <field> --graft-player-funcs` CLI
> flag. The §2/§5/§6 "ships in v1 / NEW file surface / phased build order" framing below is the ORIGINAL design
> record — read it as as-built; the genuinely-deferred items (non-Zidane-donor anim-bearing graft) are still marked.

> The step after faithful object carry (`docs/OBJECT_CARRY.md`). Grafts the donor field's PLAYER functions
> onto the fork player so that forked stock-map interactions (the field-122 cask EXAMINE, the box push/examine
> gestures) actually fire — instead of being dropped to `init_only`. Generalizes the proven one-function
> jump/ladder player graft to N functions with tag allocation + a TAG-arg remap. Every number below is from a
> full 676-field census, corrected by each dimension's adversarial verdict (produced by the
> `player-func-graft-research` ultracode workflow, 13 agents); every primitive is verified against the real code.

---

## 1. SUMMARY

For each carried object/region/jump, the object scanner already records `player_tags_needed` — the donor player
function tags that object's interactive `RunScript`s call. The graft reads those donor player functions, classifies
each for graftability (refusing TEXT / EXOTIC / non-Zidane-animation / missing / sibling-driving funcs), and
**grafts the safe ones verbatim onto the fork player entry at a fresh high tag band via the proven
`eb.edit.add_function` primitive** (the exact mechanism `jump.inject_jump` and `ladder.inject_ladder` already use
for one function). The genuinely new dimension is a **tag remap**: when a donor player function lands at a new tag
`T'`, the carried object's `RunScript(player, T)` arg2 (and any intra-graft player→player call) must be rewritten
`T → T'` — a same-length 1-byte patch reusing `content/object._arg_byte_offset(ins, 2)`. The **transitive closure
is empirically depth-0 for the object path** (no object-referenced player func calls another player tag, verified
across all 676 fields), so v1 needs no closure walker — it grafts the seed functions directly. **Headline scoping
number: ~76% of object-referenced player functions are graftable on a Zidane donor, and ~90% of GEO_ACC
set-dressing (chests/casks/boxes — the target) — which flips the user's own field-122 cask and boxes from
`init_only` to whole-entry carry.**

---

## 2. WHAT SHIPS vs WHAT'S DEFERRED

*(Original design record, read as as-built — the "ships" set shipped; the "deferred" set is still deferred.)*

### Shipped (the GEO_ACC win)

Grafts the **CLEAN and uid-remappable** player functions on a **Zidane-player donor**, flipping their carried
objects from `init_only` to whole-entry carry.

- **Object-referenced player funcs that are v1-graftable: ~76% (conservative).** The census gave two numbers: a
  loose **74.5%** that admits a `SOFT_OPS` set (scripted `Walk`/`InitWalk`/`SetWalkSpeed`, `EnableMenu`/
  `DisableMenu`, `RunSoundCode`) as portable, and a conservative **65.6%** that blocks them. The Dimension-1
  verdict flagged scripted-Walk as **risky on a fork** (its coords are perspective/walkmesh-tuned to the donor
  field, the jump-arc caveat but *without* the verbatim-copy guarantee). **The graft refuses SOFT_OPS** and states
  the exclusion so the number is reproducible.
- **By model family (the decisive cut): GEO_ACC ~90% graftable** (224/250) — chests/casks/boxes, the "missing
  barrel" target. GEO_NPC ~42%, GEO_SUB ~45% (dialogue/sibling-driven → correctly refuse). This is a
  *set-dressing-interaction* win, not an NPC win.
- **The driving case proves out:** field 122 `needed = {11, 12, 24}`, all three CLEAN, depth-0, Zidane donor →
  cask tag-24 (`SetTurnSpeed`/`TurnTowardPosition`/`WaitTurn`) and box tags 11/12 (`TimedTurn`/`SetStandAnimation`/
  `RunAnimation`/`WaitAnimation`) all graft, and their objects carry whole.

### Refuses (object stays `init_only`, renders faithfully, lint-warns)

| Refuse class | Census (object-path) | Why |
|---|---|---|
| **TEXT** (`WindowSync 0x1F`/`WindowAsync 0x20`/`WindowSyncEx 0x95`/`WindowAsyncEx 0x96`) | ~11–13% | references a donor `.mes` TXID the fork doesn't carry → empty window (engine returns `String.Empty`, not a crash). Carried by the text-carry subsystem (`--carry-text`, **shipped** — docs/TEXT_CARRY.md). |
| **EXOTIC / SOFT_OPS** (`RunSharedScript`/STARTSEQ 0x43, `AddItem`/`AddGi`, `Field 0x2B`/`Battle 0x2A`/`WorldMap 0xB6`/`PreloadField 0xFD`, `MoveCamera 0x6F`/`ReleaseCamera 0x70`/`SetFieldCamera 0x7E`/`FadeFilter`, scripted `Walk`/`InitWalk`) | ~13% | dangle on missing shared-script entries, fire warps/give-items/camera-hijacks mid-interaction. (Reuse `eventscan.NON_NAVIGABLE_OPS`.) |
| **non-Zidane player + anim-bearing** | ~8% of object seeds (15/30 non-Zidane) | donor player rig is not a Zidane field form → clip ids are Garnet/Steiner clips that won't match the fork's Zidane. The set of accepted Zidane field forms is `eventscan.ZIDANE_MODELS = {93, 98, 203, 432, 532, 668, 669, 670}` — **model 532 `GEO_MAIN_F0_ZDD` IS a valid Zidane rig (graftable), not a mismatch** (likewise 203/432/668–670). The classifier refuses only `donor_model not in ZIDANE_MODELS`; ~11 placement-only seeds are a salvage follow-on. |
| **MISSING** (referenced tag absent on the donor player entry) | ~5% (16–20 funcs) | field 1850/1854/`mdsr_map573a` style — the donor player itself lacks the tag (dead/conditional cutscene refs). Graft cannot invent it. |
| **sibling-driving** (a player func `RunScript`s/`TurnTowardObject`s another object) | 3 funcs RunScript a sibling game-wide; 35 `TurnTowardObject` a sibling | **hard-refuses** any player func whose body references an UNcarried sibling uid. (Carried-sibling refs are now remapped by `remap_player_func_siblings`, so only UNcarried siblings refuse.) |
| **transitive** (a player func that `RunScript`s another player tag) | depth-0 on the object path (0 occurrences game-wide) | the target tag is enqueued and grafted too, so the closure stays self-consistent; the func itself stays graftable (`init_only` only if a transitively-needed tag is non-`clean`). |

### Deferred (with justification)

- **Text-bearing player funcs + the 96% of talkable carried NPCs' own tag-3 dialogue** → the **text-carry
  subsystem** (`--carry-text`, `content/textcarry.py`): extract donor zone `.mes` by event id → re-emit at a
  disjoint import-text band ≥ 600 → 2-byte textID remap. **SHIPPED since** (scoped as a self-contained follow-on
  so its real payoff — faithful NPC dialogue, *separate from* and *larger than* the 11% player-func slice — would
  not gate the GEO_ACC win; it later landed + is in-game proven — docs/TEXT_CARRY.md).
- **Non-Zidane donors** (animation fidelity / character-clip carry) → deferred; 19% of fields, but only ~10% of
  carried-interaction fields.
- **Deep/unsafe transitive closures** → the object path is **depth-0**, so nothing to defer there; the region path
  reaches **depth-1 in exactly one field (1254)**. Keep a depth-1 guard for the future region-carry path; ship no
  closure walker for objects.

---

## 3. THE TAG-REMAP + REFERENCE-REMAP

### 3.1 The tag band — dynamic next-free, coordinated across all three grafters

The collision surface on the fork player entry is `{0,1}` (`eventscan.FORK_PLAYER_TAGS`) ∪ ladder band
(`FIRST_CLIMB_TAG = 17`) ∪ jump band (`FIRST_JUMP_TAG = 40`) ∪ the object band's own assignments. The donor's own
tag numbers never land on the fork (only the referenced funcs are grafted, at new tags), so the band needn't clear
the game-max player tag of 88. A fixed `FIRST_OBJECT_PLAYER_TAG = 64` is fragile (a field with > 24 jumps pushes
the jump band into 64). The robust form is a **single shared allocator** threaded through ladders → jumps → objects:

```python
class PlayerTagAllocator:
    FLOORS = {"ladder": 17, "jump": 40, "object": 64}      # named bands, matching today
    def __init__(self, eb):
        self._used = {f.tag for f in player_entry(eb).funcs}   # {0,1} on a blank fork
    def take(self, kind, n=1):
        t, out = self.FLOORS[kind], []
        for _ in range(n):
            while t in self._used: t += 1                  # slide past any prior band's overflow
            self._used.add(t); out.append(t); t += 1
        return out
```

- Ladders `take("ladder", L)` → `17,18,…` (byte-identical to today). Jumps `take("jump", J)` → `40,41,…`.
  Objects `take("object", P)` → `64,65,…`.
- **Backward-compat:** for every shipped field (census worst case: 8 object tags, 8 jumps, 2 ladders; worst
  combined = 10 in field 682), `take` returns exactly today's fixed-counter tags → the hut SHA-256 golden + the
  jump/ladder in-game proofs are preserved. The allocator only changes the previously-broken overflow case.
  `add_function`'s dup-tag raise (`eb/edit.py:137`) is the loud backstop.

### 3.2 The old→new tag map

Per field, union every carried object's `player_tags_needed` into `needed` (sorted, deduped; field 122 →
`{11,12,24}`). Allocate sequentially: `tagmap = {donor_tag: fork_tag}` (field 122 → `{11:64, 12:65, 24:66}`). This
single dict drives both the grafted bodies and every reference rewrite.

### 3.3 Remap site (a) — the carried object's `RunScript(player, T)` arg2

This dimension is now a parameter of `remap_entry_refs` itself — `remap_entry_refs(..., player_tag_remap=tagmap)`
rewrites the **tag** arg2 inline, in the same pass it already used for the **uid** arg1 (not a separate post-pass).
Verified byte layout for `RunScriptSync(2, 250, 24)` = `14 00 02 fa 18`:

| offset | 0 | 1 | 2 | 3 | 4 |
|---|---|---|---|---|---|
| byte | `14` op | `00` argflag | `02` level (arg0) | `fa`=250 uid (arg1) | `18`=24 tag (arg2) |

`_arg_byte_offset(ins, 2)` returns **4** (verified live), `argsize(0x14, 2) == 1` → a **same-length 1-byte in-place
patch** at `ins.off + 4`. **The discriminator is load-bearing** (the field-122 cask tag-2 has BOTH forms in one func):

```
RunScript(level=6, uid=23=player-entry-index, tag=24)  -> remap arg2 (24 -> fork tag 66)
RunScript(level=0, uid=255=self,              tag=30)  -> KEEP arg2 (30 is the cask's OWN tag)
```

**Remap arg2 against `tagmap` iff arg1 resolves to the player** (`uid == 250` or `uid == donor_player_entry`);
otherwise leave arg2 verbatim. Guard with `if bo is not None` (`_arg_byte_offset` returns `None` on a preceding
expression operand — a rare computed-uid RunScript — correctly skipping the patch).

### 3.4 Remap site (b) — intra-closure player→player calls (depth-0 in practice)

When a grafted player function's body contains `RunScript(250|255, T2)` with `T2 ∈ tagmap`, rewrite arg2
`T2 → tagmap[T2]`. **Census: 0 occurrences on the object path** — a zero-cost defensive pass. Internal jumps
(`0x01/0x02/0x03`, switch `0x06`) are function-relative and survive `add_function` untouched.

### 3.5 Remap site (c) — sibling uids inside a grafted body

A grafted player func that `TurnTowardObject(sibling)` / `RunScript(sibling, tag)` carries a uid ref to another
object. A **CARRIED-sibling** ref is now remapped to the sibling's fork slot by `remap_player_func_siblings(data,
tagmap, slot_map)` — a post-graft, same-length 1-byte patch that runs after both grafts (the save-Moogle pose funcs
13/14/15 each `TurnTowardObject` a carried Moogle slot). Only an **UNcarried** sibling reference is hard-refused
(only 3 funcs RunScript a sibling game-wide); a player/self/party uid is never in `slot_map`, so it is never
touched.

---

## 4. THE GRAFT ALGORITHM

```
# ---- SCAN (eventscan.py) -----------------------------------------------------------------
# scan_objects_verbatim already gives, per object: player_tags_needed[], donor_player_entry, carry_tags, graft_safety.
# NEW: scan_player_funcs(eb_bytes) emits the graft specs, with a per-tag safety classification.

def resolve_player_entries(eb):
    # CLOSE the GAP: a field can have >1 DefinePlayerCharacter (fields 820/108/316-319/332/459/573...).
    return [e.index for e in eb.entries if not e.empty and any(i.op == DEFINE_PC for f in e.funcs for i in eb.instrs(f))]

def player_func_safety(eb, player_entries, donor_player_model, needed_tag):
    f = first(eb.entry(pe).func_by_tag(needed_tag) for pe in player_entries if ...)
    if f is None:                                   return "missing"
    ops = {ins.op for ins in eb.instrs(f)}
    if ops & TEXT_OPS:                              return "text"     # 0x1F/0x20/0x95/0x96
    if ops & EXOTIC_OPS:                            return "exotic"   # NON_NAVIGABLE_OPS
    if body_references_sibling(eb, f, carried):    return "sibling"
    if (ops & ANIM_OPS) and donor_model not in ZIDANE_MODELS:  return "model"   # ZIDANE_MODELS = {93,98,203,432,532,668,669,670}; 532=ZDD is a valid Zidane rig
    if body_runscripts_player_tag(eb, f):          enqueue(target_tag)            # depth-0 in practice
    return "clean"

# ---- BUILD (build.py, after the existing object graft branch) ----------------------------
alloc = PlayerTagAllocator(eb)                      # threaded through ladder(17+)/jump(40+) FIRST
... ladders take("ladder",L); jumps take("jump",J) ...      # unchanged emit
player_funcs = project.raw.get("player_func", [])
objects      = project.raw.get("object", [])
if player_funcs:
    graftable = [p for p in player_funcs if p["safety"] == "clean"]
    fork_tags = alloc.take("object", len(graftable))
    tagmap    = {int(p["donor_tag"]): ft for p, ft in zip(graftable, fork_tags)}
    eb = ensure_player_anim_packs(eb, donor_init_clip_loads(graftable))   # Dim4: generalize jump.ensure_jump_animation
    for p in graftable:
        body = load(p["bin"]); body = remap_player_tag_calls(body, tagmap)   # site (b), 0 patches in practice
        eb   = edit.add_function(eb, fork_pe, tagmap[int(p["donor_tag"])], body)   # raises on collision
if objects:
    eb = graft_objects(eb, objects, load=..., player_tag_remap=tagmap or None)    # site (a) arg2 remap
```

**Refuse rules (object stays `init_only`, lint-warns):** a carried object keeps `init_only` if **any** of its
`player_tags_needed` resolves to a non-`clean` safety (text/exotic/model/missing/sibling). All-or-nothing **per
seeding object** (partial carry would `RunScriptSync` into a half-grafted closure → freeze), but per-object
granularity means box A can carry whole while box B stays `init_only` in the same field.

**The clip-load caveat (Dimension 4 — applies even to Zidane donors):** the blank fork player Init loads only anim
pack 912; **86% of Zidane fields with a high-clip needed func load extra `RunModelCode(…, pack)` calls (907/914/
915/923/924/909) in the donor player Init** that the fork lacks. Field 122's boxes play clips 2590/2605/2606 from
packs 907/914. Grafting the func body alone leaves the clip unloaded → **silent broken animation**.
`ensure_player_anim_packs` must splice the donor Init's `RunModelCode`-pack loads (de-duped, idempotent) into the
fork player Init after `DefinePlayerCharacter` — generalizing `jump.ensure_jump_animation`'s single-clip splice.
Gated on the model match (packs are model-keyed).

---

## 5. THE API / FILE SURFACE (as built)

| File | Change | Stays untouched |
|---|---|---|
| **`eventscan.py`** | **Add** `resolve_player_entries(eb)` (multi-`DEFINE_PC`; `_player_entry_index`:202 returns only the first). **Add** `scan_player_funcs(eb_bytes)` → per-tag `{donor_tag, body, safety, runscript_tags[], donor_init_packs[]}`. **Add** `TEXT_OPS`/`EXOTIC_OPS`(=`NON_NAVIGABLE_OPS`)/`ANIM_OPS` + a donor-player-model read. **Widen** `_graft_safety(entry, refs, fork_player_tags, *, graftable_player_tags=frozenset())` — `available = fork_player_tags | graftable_player_tags`; **default `frozenset()` ⇒ byte-identical**. **Add** `graft_player_funcs=False` kwarg to `scan_objects_verbatim` (opt-in). | `REF_OPS`, `_classify_entry_refs`, `scan_objects`, the default `scan_content` contract. |
| **`content/player.py`** | `graft_player_funcs(data, specs, tagmap, *, load, graftable_safeties)` (N-function generalization of `inject_jump`/`inject_ladder`); `remap_player_tag_calls(body, tagmap)` (site b); `ensure_player_anim_packs(data, packs)` (Dim4 splice); `remap_player_func_siblings(data, tagmap, slot_map)` (site c, carried-sibling uid remap); `FIRST_OBJECT_PLAYER_TAG = 64` + `PlayerTagAllocator`. Imports only `eb/edit`, `eb/disasm`, `eb/opcodes`; reuses `object._arg_byte_offset` + `ladder.find_player_entry`. | Never imports `inject_npc`/`inject_prop`/`inject_jump`/`inject_ladder`. |
| **`content/object.py`** | `graft_objects(..., player_tag_remap=None)`; when present, after `remap_entry_refs` (uid), call the arg2 tag-remap (site a) per object. **Factor `_arg_byte_offset` to a shared spot** (or import). | `remap_entry_refs` uid path, `carry_bytes`, `_arm` — unchanged when `player_tag_remap is None`. |
| **`extract.py`** | Emit a **`<name>.playerfuncN.bin`** sidecar (verbatim donor body, **gitignored** like `.object*.bin`) + a **`[[player_func]]`** TOML block (`bin`, `donor_tag`, `safety`, optional `calls=[...]`), gated on `out_dir`. When active, `scan_objects_verbatim(..., graft_player_funcs=True)` so flipped objects emit whole-entry (no `carry_tags` subset). Opt-in `--graft-player-funcs` flag on `import` (default off in v1). | the `[[object]]` emit, `_object_block`, native/editable fork paths. |
| **`build.py`** | Consume `[[player_func]]`: thread the `PlayerTagAllocator` through ladder→jump→object; call `ensure_player_anim_packs` + `graft_player_funcs` before `graft_objects(..., player_tag_remap=tagmap)`. **Lint:** (1) each `bin` exists+decodes; (2) **dangling-tag error** — every `[[object]]` RunScript to a player tag must be in `{0,1} ∪ {donor_tag of [[player_func]]}`; (3) **band-collision error**; (4) **warn** on a non-Zidane donor. | authored `[[npc]]`/`[[prop]]`/jump/ladder branches; **gated on `project.raw.get("player_func")`** so authored builds never enter (hut golden preserved). |

**Tag bands:** player `{0,1}` · ladder `17+` · jump `40+` · object-player-funcs `64+`, all dispensed by the one
`PlayerTagAllocator`. **Untouched by construction:** the authored path, the jump/ladder grafts, and
`eb.edit.add_function` (no new primitive needed).

---

## 6. PHASED BUILD ORDER WITH REGRESSION CHECKPOINTS

*(The original phased plan — all phases landed; kept as the build record. Run the suite from `ff9mapkit/`: `py -m
pytest -q` — see the test suite for the current count.)*

| Phase | Work | Gating tests (must stay green) | Tests to add | In-game gate |
|---|---|---|---|---|
| **P0 — multi-player-entry + safety classify** | `resolve_player_entries`, `scan_player_funcs`, `TEXT/EXOTIC/ANIM_OPS`, per-tag safety. Pure decode, no graft. | `test_eventscan.py`, `test_object_graft.py`, hut goldens | `test_scan_player_funcs_classifies_122` (11/12/24 clean, depth-0), `test_missing_tag_marked`, `test_sibling_func_refused`, `test_text_func_refused`, `test_multi_player_entry_resolved` | none |
| **P1 — policy flip (opt-in)** | widen `_graft_safety` (default `frozenset()`); `scan_objects_verbatim(graft_player_funcs=True)`; flip `init_only → clean` when all needed tags graftable. | **`test_eventscan.py` cask `init_only` oracle**, **the two SHA-256 hut oracles** | `test_default_scan_byte_identical`, `test_policy_flip_makes_122_clean` | none |
| **P2 — `content/player.py` graft + tag remap + allocator** | `graft_player_funcs`, `remap_player_tag_calls`, `PlayerTagAllocator`; `graft_objects(player_tag_remap=)` arg2 remap; `ensure_player_anim_packs`. | **`test_object_graft.py`** (incl. cask `init_only` with `player_tag_remap=None`), **`test_jump.py`**, **`test_ladder.py`**, `test_eb.py` | `test_clean_func_grafts_and_object_arg2_remaps`, `test_arg2_remap_only_when_arg1_is_player` (122 self-call tag-30 stays), `test_tag_band_no_collision_ladder_jump_object`, `test_clip_pack_prologue_carried`, `test_grafted_eb_roundtrips` | none |
| **P3 — extract sidecar + build wiring + lint** | `[[player_func]]` + `.playerfuncN.bin` emit (gitignored); build consumes; the 4 lint checks. | all above + `test_build.py` flag-band identity; the hut SHA-256 re-assert after importing `content.player` | `test_extract_emits_playerfunc_sidecar`, `test_lint_dangling_player_tag_errors`, `test_lint_band_collision_errors`, `test_authored_path_unchanged_by_player_module` | none |
| **P4 — the ONE in-game gate (PROVEN)** | `import fbg_n08_udft_map122_uf_sto_0 --graft-player-funcs` → build → deploy → F6 → Warp | full suite + new, all green | — | **the cask turns to face you on EXAMINE (tag-24 fires) and the boxes push/examine (tags 11/12 fire)** — confirmed in-game. |

---

## 7. OPEN RISKS & UNKNOWNS

**Verified in-game (the P4 gate, PROVEN):**
- The field-122 cask EXAMINE turn + box push/examine fire on the fork.

**Watch-outs that were checked / remain edge-case risks:**
- That the **clip-pack prologue** suffices: do `SetStandAnimation(2605)`/`RunAnimation(2606)` resolve once
  `ensure_player_anim_packs` splices packs 907/914 into the fork Init? If the box gesture plays no animation, the
  prologue is missing a `Set*Animation` declaration the func depends on, not just the pack load.

**Worst-case failure modes:**
- **Dangling-tag softlock** — a carried object `RunScriptSync`s a player tag that wasn't grafted. Mitigations: the
  lint dangling-tag **error** (hard build stop) + `add_function`'s dup-tag **raise**. The all-or-nothing per-object
  policy prevents a half-grafted closure freeze.
- **Mismatched-model animation** — a non-Zidane donor func slips through → Zidane plays a wrong/empty clip.
  Mitigation: refuse the whole non-Zidane set in v1; the model read + lint warn surface it.
- **Wrong-text window** — only if TEXT refusal is bypassed; v1 refuses all TEXT (engine returns `String.Empty`).
- **Scripted-Walk drift** — a grafted `Walk(x,z)` uses donor-field coords on the fork. Mitigation: v1 refuses SOFT_OPS.

**The text-carry follow-on — SHIPPED (`--carry-text`, `content/textcarry.py`).** It serves BOTH the refused
text-bearing player funcs (~11%) AND the **96% of carried NPCs whose own tag-3 talk is a window** — the larger
prize. As built it bakes the `eventIDToMESID` table (provenance-clean), keys the donor text zone on the
**event id** (field-122's event id is 407 → zone 50, *not* 122; uses `FBG_TO_EVT[0]`), extracts the specific `.mes`
entries per language, re-emits at a disjoint import-text band ≥ 600, and patches each window op's **2-byte** textID
immediate. The carried `.mes` strings are SE-derived → gitignored. See docs/TEXT_CARRY.md.

---

**Provenance:** the `.playerfuncN.bin` sidecars are verbatim SE-derived player-function bytes → gitignored (same
posture as `.object*.bin`/`.jump.bin`). Design produced by the `player-func-graft-research` workflow; full key-file
citations in the workflow output.
