# Codebase scout — what to chase next

> Handoff for the session that continues [`REPORT.md`](REPORT.md). Everything in the report's
> "Where to start" (items 1–9) has SHIPPED on `claude/codebase-improvement-scout-t2sag7`
> (10 commits, `c8741de`..`f564e93`). This file is the ranked queue that follows, with enough
> file:line to execute each without re-scouting. Verify a line number before editing — every
> edit above it shifts the ones below.

## How the last nine landed (keep this rhythm)

- **Walk the change through before coding**, one piece at a time; the owner approves each.
- **Calibrate**: write the test first, show it RED on the current tree, then fix, then GREEN.
  A test that was never red proves nothing (CLAUDE.md §7).
- **One commit per step**, gate summary in the message: which test files, counts, ruff, collect.
- **Ratchet**: `cd ff9mapkit && python -m ruff check --select F --no-cache ff9mapkit` must stay
  `Found 107 errors` or lower (the nightly gate now judges an INCREASE as `lint-up`).
- **Collect**: `pytest --collect-only -q` from the repo root was **7641** after items 1-3 (this
  container; `test_forkreport.py` is ignore-collected here — it reads the alex100 fixture and
  the base templates at MODULE level, so it runs only where the install is provisioned).
- Container facts (do not assume they persist): no game install / templates; `Pillow`,
  `UnityPy`-less, `pytest-xdist`, `ruff`, `markdown` were pip-installed by hand. `git push`
  works (the owner granted the App write access mid-session).

## Install-gated proofs still owed to the owner (batch into one session)

1. `py tools/nightly_gate.py --smoke` in the gate worktree → collect +52, `ruff F: 109 … no
   baseline yet`.
2. `pytest tests/test_forkreport.py` with the alex100 fixture; `ff9mapkit fork-report 354` (+2
   more ids) before/after `8d7b7ab` → byte-identical (eblint's 0-jump-fault sweep says it must be).
3. One field deploy with explicit `--id` to a confirmed-unregistered scratch id → `warning:`
   lines print; sha256 of the dist before/after `f8b0221` identical.
4. One summon deploy + revert against a scratch folder → `DictionaryPatch.txt` and
   `Memoria.ini` return to pre-deploy bytes; a second deploy while a lock is held → rc 2.
5. One id-less `summon-deploy --dry-run` into a folder that already registers a `GEO_WEP` mint
   (or with `FF9CustomMap-world` registering a `3DModel`) → the receipt's id skips it; the same
   block pinned to that id → the `3DMODEL ID COLLISION` banner, rc 0.

## The queue, ranked by value per byte of new surface

### Done since handoff (commits `2ccbff6`, `2642e61`, item 3 below) — items 1-3
- **1** `import re` in `cli.py` (+ `world/mesh.py`'s `"BlockMesh"` under `TYPE_CHECKING`): F821 = 0,
  ruff F 109 → 107. Regression test in `tests/test_chain.py`.
- **2 (9b)** `alloc_mint_id` seeds from `deploystack.model_ids_at` + a foreign-folder `avoid` set;
  `_warn_model_id_collision` prints the sibling lanes' banner once per emit; `stage_import` threads
  `out`; a dry run's mirror is seeded with the live `DictionaryPatch.txt` (`_dry_run_mirror`);
  `summon-deploy --dry-run` honours `--mod-folder`; `models.mint.MINT_BAND_END`. 14 tests in
  `tests/test_summon_alloc.py`. An adversarial review of the first cut caught a `stage_import`
  double banner, a `game=None` crash line, and a dry-run false banner — all fixed there.
  Install side still owed: mint on a folder that already holds a `GEO_WEP` (item 5 below).
- **3 (3b)** `behaviortoml.placeholder_slots` replaces FIVE inline seatings (the queue said four;
  `build.lint_flag_bands`'s recompute was the fifth, and the "real seating" it cited is that lint,
  not the build's `_inject_npcs` map). Differ: old vs new IDENTICAL over 93 build calls / 124
  compiles (raw, slots, whole blackboard, `pool_hireable`, siege choice flags, compiled-body
  hashes); calibration moved 40 slot dicts + 13 bodies and held every flag. Two tests in
  `tests/test_cli_behavior.py`. Pre-existing red noticed on the way: `test_journalfield.py`'s
  checked-in bench TOML has drifted from its generator (2 tests) — not touched.


### 4. 2b — hoist the suite-wide guards above every tree  · small · offline
`ff9mapkit/tests/conftest.py`'s autouse `_isolate_prefs` (monkeypatches `prefs._path`) and
`qt_drain` cover `tests/` only; `ff9mapkit/conftest.py` sits above `tests/` AND
`blender/tests/`. Move them up; re-anchor the guard to the seam `provision._user_dir(sub)` with
a pass-through for non-config subs (`data`/`cache` are live in CI); the sibling seam
`update_check._state_path` writes JSON into the real `%LOCALAPPDATA%` and is covered by nobody.
Do NOT add a shared test-support module — every step must end with FEWER readers of the real
machine (report §5). Since step 2 moved the 32 files, the remaining beneficiaries are
`blender/tests/` and that `update_check` seam.

### 5. F06 + F14 — the entry serializer ×10 and the entry-table splice ×3  · medium · BYTE-EMITTING
Copies of the type-1 func-table serializer (`<tag:u16><fpos:u16>` × N, then bodies):
`content/{shop.py:88, platform.py:200, savepoint.py:673, jump.py:95}` (`_assemble_entry`,
code-identical; the four docstrings each cite a DIFFERENT sibling as the reference), inlined at
`ladder.py:439`, `cutscene.py:130`, `object.py:50`, `region.py:414`, hand-unrolled at
`savepoint.py:1128`, tenth at `eb/ebsrc.py:698-713` — the ONLY copy with the
`fpos > 0xFFFF` guard. Splice copies: `content/reinit.py:57-80` vs `eb/edit.py:178-212`
(its docstring says it IS reinit "generalized") vs `tools/ladder_real.py:40-67`.
Sequence, each its own commit: (1) `ENTRY_TABLE_OFF`/`ENTRY_SLOT_SIZE` (owned at
`eb/model.py:40-41`) for the bare `128` / `i * 8` in `reinit.py:59/75/77`,
`eventscan.py:184/375/1029` — no bytes move, grep becomes complete; (2)
`region.pack_entry_funcs(funcs, *, entry_type=REGION_ENTRY_TYPE)` holding the existing loop
verbatim, delete the copies (also cleans `platform.py:110`'s `[1:]` slice); (3)
`object.carry_bytes` last — its docstring promises a byte-for-byte round-trip; (4)
`reinit.add_reinit` onto `edit.add_function` (pure gain: raises on an empty entry where
`add_reinit` silently returns a corrupt file); (5) only THEN the fpos guard on the single owner.
Proof: a throwaway `old(x) == new(x)` differ over every shape, calibrated by deliberately
perturbing one copy to confirm it goes red, run WHERE TEMPLATES EXIST (a bare worktree
collects nothing and passes vacuously). Do NOT mint an `EbEntry`/`EntryBuilder` class — the
whole safety argument is "character-for-character". Leave `battle/ailint.py:52-63` and both
`eb/edit.py` jump inlines alone (correct, sanctioned).

### 6. The offline gate that doesn't gate (F10 / F11 / F13)  · medium · mostly offline
- `_VERBATIM_IGNORED_BLOCKS` (`build.py:3284`) names ONE block; on a verbatim fork `ladder`,
  `platform`, `jump`, `savepoint` (+ `ate`, `object`) build clean and are absent in game — their
  injectors live inside `build_script` (`6842`, `6895`, `6947`, `7066`), which `build.py:9085`
  bypasses. Correct the set to exactly those. Do NOT invert it into an allow-list: `sps` is
  wired at `6248`, `qte`/`numeric_input` are fatal at `2439`/`2468`, `shop`/`synthesis` are
  warned at `9060-9070`, and `cli.py:1186` exits 1 on any warning — one mislabel breaks every
  fork's build gate.
- `LintReport` gets a `tagged` property; `cli.py:1181` and `deploy.py:599` iterate ONE seam
  (`deploy` prints five of six slots — it drops `unknown`, the typo'd-key check).
- `navigable = true` typo silently selects a DIFFERENT ladder mechanism (`build.py:1674`
  branches on `la.get("navigable")`, `1705` catches the fallthrough): make the discriminant
  explicit.
- 31 `.eb` "round-trip" assertions reduce to `bytes(x) == x` because `EbScript.to_bytes()` is
  `return self.data` (`eb/model.py:108-109`); convert the ~20 genuinely bare ones (they sit on
  the length-changing splice primitives) to `eblint.errors(eblint.lint_eb(out)) == []`.
- `content/behavior.py` (4,141 lines, 166 `raise BehaviorError`) is never compiled by
  `build.validate`: call a dry compile from `lint_all` AFTER the walkmesh resolve
  (~`build.py:4121`), not beside `lint_region_overlaps` at `4111` where no routed plan exists.

### 7. F47 — generated tables carry no provenance  · small · offline
Ten `_*.py` tables (~22.7k lines; `_animdb_all.py` alone 14,125) from nine `_regen_*`
generators; none records the Memoria revision it was read from and no test asserts currency.
Add a machine-readable header line per file (`# generated-from: Memoria@<sha> by
_regen_<x>.py on <date>`) and ONE test that parses all ten. Not CI regeneration — that needs a
Memoria clone in CI, which the provenance gate forbids.

### 8. F48 — docs ↔ CLI drift  · small · offline
138 verbs, 18+ generated docsite pages, two hand-written TOML specs (`docs/FORMAT.md`,
`docs/BEHAVIOR.md`), `_fieldschema.py` generated FROM the bundled examples. One test: walk
`build_parser()`, assert every verb named in `docs/*.md` and `docsite/nav.toml` exists
(documented ⊆ implemented — that direction only). Second, as a WARNING: every key in
`_fieldschema.VOCAB['']` appears in `FORMAT.md`.

### 9. `build.py` — only the twins, never the extraction (F07 / F08)  · small · byte-neutral if careful
`_verbatim_prop_message_count:5717` and `_verbatim_choice_message_count:5676` are unowned
predicate twins (drift = silently wrong dialogue in a shipped fork, correct flags, no log);
`_verbatim_cutscene_message_count:5723-5728` is DEAD (zero callers); `_aslist`:1649 /
`_aslist2`:1659 are byte-identical two-liners ten lines apart. Step ZERO is a no-install
characterization test of the full eight-block txid ladder (`FieldProject(raw, tmp_path)` with
no donor falls back to `CARRY_BASE_TXID` — the report cites `test_text.py:275`,
`test_logic_add.py:365`). Never reorder a `validate` call (problem ORDER is what the diff
harness asserts); the `.mes` block order is NOT the injector call order (choice/prop land above
event/chest). A full `validate()` decomposition mints more surface than it removes — do not.

### 10. Small, local, all offline (F03 / F44 / F40 / F01 leftovers)
- `hub.validate_hub` (`hub.py:241`) lacks the `9000-9012` world-map hole that
  `workspace/shell.py:3759` already guards — add the `WORLD_ID_LO/HI` branch.
- `build.py:9884` reads `p[3]` (mapid) as the field name; the emitter at `9127` is
  `FieldScene <id> <area> <mapid> <name> <block>` → `p[4]`.
- `_cmd_world_ledger` (`cli.py:~5477`) resolves `find_game_path(args.game) / args.mod_folder`
  directly and is untested (`test_world_ledger.py` covers the writer only); `health.py:137` and
  `editor/jobs.py:113` hardcode `FF9CustomMap` → route all three through
  `config.resolve_mod_folder`.
- `.ff9deploy.toml`'s `id` key retargets the human's Build-tab "Test slot" radio at
  `workspace/builddoc.py:172/618/982` (`tid = self.worktree_id or 4003`) — the costliest
  documented incident on this file lives only in CLAUDE.md §3. Label the slot as
  pinned-and-overridable in the tab; say in `editor/jobs.detect_deploy_target`'s docstring that
  its `field_id` is a human-visible default. `text_block` is honoured by 1 of 8 pin readers.
- Leftovers from item 2's review: `battle/skinmint.py:30` `_MINT_MAX` and `content/itemdata.py:367`'s
  literal `32767` are private twins of `models.mint.MINT_BAND_END` — point them at it;
  `deploystack.model_ids_at` / `dictionary_ids_at` miss a BOM'd first line (`utf-8-sig` fixes both,
  no kit writer emits one); a dry run still validates `private_ef` against the mirror's EMPTY
  `ef` tree (`validate_private_ef(for_alloc=True)`), the same infidelity the registry seed just
  closed for the GEO id; an id-less `[[summon]]` re-mints a fresh id on every redeploy (the
  allocator sees its own prior mint) — a documented trait, decide whether it should key on name.

## Refuted — do not re-open without new evidence
The report's "Considered and rejected" lists 25 findings two adversarial reviewers killed,
most by the repo's own written reasoning (`studies/deploy-field-promotion/PLAN.md`,
`test_world_frames.py:1-11`, `tests/conftest.py` docstrings). Read that section before
proposing any of: unifying the deploystack guard suites, the two `.eb` encoders, opcode
constants from `OP_NAMES`, splitting `build_parser()`, structured `validate()` records, a
QGraphicsView base class, merging the summon write-ledgers, one boundary-ring tracer, one weld
key, one `_game_ready()`, one Qt bootstrap, one field-token resolver, promoting private
reach-ins, decomposing the Workspace god class, moving `_smoke` into tests, one exception root.
