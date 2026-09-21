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
  `Found 106 errors` or lower (the nightly gate now judges an INCREASE as `lint-up`).
- **Collect**: `pytest --collect-only -q` from the repo root was **8503** after item 9 (PySide6 importable here; ~7687 without it) (this
  container; `test_forkreport.py` is ignore-collected here — it reads the alex100 fixture and
  the base templates at MODULE level, so it runs only where the install is provisioned).
- Container facts (do not assume they persist): no game install / templates / `UnityPy`; `Pillow`,
  `hypothesis`, `pytest-xdist`, `ruff`, `markdown`, `PySide6` (+ apt `libegl1 libgl1 libxkbcommon0
  libfontconfig1 libdbus-1-3 libxcb-cursor0 …`) were installed by hand. `git push`
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
6. Item 5's template-gated files -- `test_content`, `test_ladder`, `test_jump`, `test_platform`,
   `test_savepoint`, `test_object_graft`, `test_eventscan`, `test_textcarry` -- green, and every
   bundled example built at `bcd3ba7` and at `ef4ebec`: the dist `.eb`s byte-identical.
7. Item 6's leftovers: the 19 EbScript round-trip tautologies whose tests SKIP here (blank template /
   fixtures) and the 51 in the six template-gated files (`test_content`, `test_player_graft`,
   `test_object_graft`, `test_savepoint`, `test_textcarry`, `test_playerswap`) -- convert to
   `eblint.errors(eblint.lint_eb(out)) == []` where it passes, a structural fact where it does not; and a
   `[[ladder]]`/`[[jump]]`/`[[platform]]` example built end-to-end so their key paths enter `ENFORCED`.
8. Item 7: rerun all thirteen generators (`python -m ff9mapkit._regen_*` with `--memoria`, `eb._regen_optables`,
   `tools/bake_narrowmap.py`, `_regen_npcparams` / `tools/regen_bone_labels.py` / `tools/extract_attach_poses.py
   --build-kit` against the install, `_regen_fieldschema`) -> every `Memoria@unknown` becomes the clone's
   revision and NOTHING else in any table changes (the free currency check).

## The queue, ranked by value per byte of new surface

### Done since handoff — items 1-9
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
- **4 (2b)** `_isolate_user_config` in `ff9mapkit/conftest.py` wraps `provision._user_dir` (config →
  tmp, data/cache pass through); the old `_isolate_prefs` is gone; `qt_drain` deliberately stays in
  `tests/conftest.py` (all users there, no Qt in blender/tests). Three tests, two trees. The container
  now has PySide6 + GL/xcb libs, so the Qt suite runs headless (`QT_QPA_PLATFORM=offscreen NO_THUMBS=1`):
  full-suite baseline here = 13 environmental failures (listed in `bcd3ba7`'s commit message), 7647 passed.
- **5 (F06/F14)** five commits `ad4ffa3`…`ef4ebec`: `eb.model.pack_entry` owns the func-table
  serializer (ELEVEN copies, not ten — `tools/ladder_real.py` carried one too), `region.pack_entry_funcs`
  is the region-default call (the owner sits in `eb/` because nothing in `eb/` imports `content/` and
  `ebsrc` must reach it); the u16-fpos guard is on the owner; `reinit.add_reinit` and `ladder_real`
  splice through `edit.add_function` (an empty entry 0 now raises). Proof without templates: Hypothesis
  (3000 examples per shape, every old text transcribed verbatim) + a 1070-key snapshot over 40 synthetic
  ebs, calibrated at every step. `tests/test_pack_entry.py` (4), `test_reinit.py` (+1).
- **6 (F10/F11/F13)** five commits `611f7f0`…`66899ce4`: the verbatim ignore set names all seven
  build_script-only blocks (AST census; qte/numeric_input/siege/behavior are REFUSED by validate,
  shop/synthesis warned, the rest wired on both paths); `LintReport.tagged` is the one print seam (deploy
  prints `[schema]` again); a `[[ladder]]` with a key outside its 17-key vocabulary is REFUSED with a
  difflib hint (the harvested lint does not enforce ladder/jump/platform -- no example completes offline);
  the four `.eb` round-trip tautologies that RUN here assert something (eblint ×3, a structural size check
  where eblint rightly flags placeholder switch targets); `behaviortoml.dry_compile` owns the seat+build+
  compile the CLI and Workspace lanes carried, and `lint_all` dry-compiles `[behavior]` after the walkmesh
  resolve (a 97-flag table on a 96-flag band is now a lint ERROR). Recorder containment: 93/93 calls,
  124/124 compiles.
- **7 (F47)** `e78e03d6`: `_regen_stamp.py` owns the `# generated-from: <source> by <generator>` stamp (the
  line after each table's docstring; `Memoria@<git rev>` for the nine Memoria-derived tables, `install` /
  `examples` for the rest, no date) and the registry of SIXTEEN tables from THIRTEEN generators (the queue
  said ten/nine). Every generator emits it (required `stamp` keyword); the tables are hand-stamped
  `Memoria@unknown` until regenerated. 28 tests in `tests/test_generated_tables.py`.
- **8 (F48)** `d1ecf848`: `tests/test_docs_cli_drift.py` -- every verb the 75 hand-written pages name AS A
  COMMAND (code span / fenced line; prose is not a command) exists among the parser's 140; the docsite's
  generated per-verb pages already gate the other direction. Clean today (`gui` is named as ABSENT and
  the test checks that citation). The root-key half is a hard ratchet, not a warning: only `[[folklore]]`
  is undocumented -- document it and shrink the set.
- **9 (F07 / F08)** `c0501b6d` + `5dee89a8`: step zero pins the whole verbatim appended-text ladder in one
  test (`test_text.py`, every rung's txid, counts in lockstep, contiguous 1000..1010); step one gives each
  block ONE selector -- `_verbatim_voiced_npcs` (voiced, silent), `_verbatim_npc_choices` + `_choice_replies`,
  `_verbatim_voiced_props` -- and derives the counts from them; the dead cutscene count and the nested
  `_aslist2` twin are gone. `twins_differ.py` (old copies transcribed verbatim vs the new owners) ALL EQUAL,
  calibration on the prop selector FAILED `['prop_count']`. test_build 51 passed; the extraction is untouched.


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
