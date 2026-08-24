---
name: building-the-memoria-engine
description: Build and patch the local custom Memoria engine -- a rare, DANGEROUS workflow. Confirm a DLL rebuild is truly needed before starting (most tasks need none), then build via `py tools/build_memoria.py` -- it enforces the pre-build DLL backup (the raw build AUTO-DEPLOYS over the live install), the exact msbuild flags, and post-deploy sha verification. Use when the user rebuilds `Assembly-CSharp.dll`, adds/edits a memoria-patch (the `memoria-patches/` stack, s12-s58), works on the fork-donor remap suite (sweeping a hardcoded `fldMapNo` in its four forms -- `==` compare, local alias, name-key, lookup-arg -- via `EffectiveFieldId`/`EffectiveFieldName`/`FieldLocationName`), or runs `verify_fork_gates` / `restore_memoria_dll`. Covers the MSBuild recipe (`/p:SolutionDir=C:\gd\FFIX\Memoria\` trailing slash required, add new `.cs` to the csproj), version-match commit `6b8bb2d5`, the fork-gate census, and why forked fields require the bundle while novel fields run on stock. For deploying mod content (not engine code) see `deploying-ff9-mods`; for USING the fork gates see `forking-ff9-fields`.
---

> Thin router — link the canonical doc (Layer 3) and the memory recipe (Layer 2); do NOT recopy opcode tables, TOML schemas, or coast laws — those live once in docs/ and memory/ and would rot if forked here.

# Building the Memoria Engine

## STOP -- confirm a DLL change is truly required

Most tasks need NO engine rebuild. A novel field (from-scratch or BG-borrow) runs on **stock
Memoria**; mod CONTENT — fields, campaigns, battles, models, audio, items — deploys without
touching the DLL (see the `deploying-ff9-mods` skill). Only an **engine-code** change needs a
rebuild: editing/adding a `memoria-patches/` patch, wrapping a new fork gate, an debug-menu
feature. If it is not certain the change is engine-side, STOP and ask the user before
proceeding. A DLL change also requires a full game **relaunch** (~ reload is not enough) and
a human playtest — the agent cannot see the running game.

## Build through the wrapper — `py tools/build_memoria.py [--label L]`

**The build AUTO-DEPLOYS to the game** (the csproj `AfterBuild` copies the built
`Assembly-CSharp.dll` + `Memoria.Prime.dll` + `UnityEngine.UI.dll` into BOTH arches' Managed
folders), and the wrapper is the enforcement call site for the four laws that used to be
procedural: it **refuses to build until the full 3x2 pre-build snapshot exists** (via
`backup_memoria_dll.py`; a missed backup is only recoverable by re-running
`Memoria.Patcher.exe`), invokes msbuild with the exact mandated flags as a **list-args
subprocess** (no shell → immune to the bash/MSYS `/t:` mangling → MSB1008 class), always
passes **`-p:SolutionDir=<clone>\`** with the load-bearing trailing backslash (else the
machine's .NET v4.0 mscorlib leaks in → `CS1703`/`CS0433`), and **verifies post-deploy** that
Output sha256 == both arches' live copies — a build while FF9 runs can fail the Deploy task
partway, and a MIXED deploy is flagged loudly with the restore one-liner. `--no-deploy` =
compile-check only (refused if the clone's csproj lacks the s45 `DWIXNoDeploy` condition).
It also reports the shared clone's in-flight edit count first — a build deploys other
sessions' edits too. Tests: `ff9mapkit/tests/test_build_memoria.py`.

New `.cs` files must be added to the csproj `<Compile Include>`. The raw msbuild recipe
(for debugging the wrapper itself), one-time References setup, and every known gotcha:
[`references/build-recipe.md`](references/build-recipe.md).

## Version-match 6b8bb2d5

Stay near the installed compile-date's Memoria `main` commit **`6b8bb2d5`**
(`git checkout 6b8bb2d5` in `C:\gd\FFIX\Memoria\`). Building from a newer HEAD drifts the DLL
~months against the rest of the install unless the sibling DLLs are rebuilt as a matched set.
Detail: [`references/build-recipe.md`](references/build-recipe.md).

## The four-form fldMapNo sweep + levers

Any engine behavior hardcoded on a real `fldMapNo` (or FBG name) is LOST on a custom-id fork.
A fork-gate sweep must cover FOUR forms — a `== N` compare, a local alias
(`Int16 mapNo = fldMapNo`), a NAME key, and a lookup ARGUMENT — each fixed by the matching
lever: `EffectiveFieldId` (s23/s24/s29/s30), `EffectiveFieldName` (s31/s32),
`FieldLocationName` (s33). s34 = the overworld loose-mesh override; s35 = the overlay-texture
cache. Lever map, lessons, and the `ForkDonorPatch.txt` linchpin:
[`references/fork-gate-census.md`](references/fork-gate-census.md); the per-site census lives
in `ff9mapkit/docs/FORK_IDGATE_MAP.md`.

## The verification harness

`py tools/verify_fork_gates.py` bakes each s29 gate's seed + observability verdict (`--list`
= the table; `--emit <field>` = a per-target fork+deploy+~ playbook). The remap only fires
when the deploy emitted `ForkDonorPatch.txt` (`<forkId> <donorRealId>` lines, read at launch).
Method + findings: memory `project-ff9-fork-verification-harness`.

## Restore / revert

- `py tools/restore_memoria_dll.py <selector>` — copies the newest backup set whose name
  contains `<selector>` back into both Managed folders. `<selector>` = the timestamp
  `backup_memoria_dll.py` / `build_memoria.py` printed for YOUR pre-build snapshot — it is
  REQUIRED (a bare run prints usage + the newest backups and exits 2; the old no-arg default
  chased the long-gone `baseline` set). Run from the MAIN repo (`backups/` lives there).
- The restore is **ALL-OR-NOTHING**: every destination is probed before the first copy, so a
  running FF9 (which memory-maps only the arch it runs) can no longer produce a half-restored
  mixed-version engine — it refuses and says to close the game.
- TRUE stock = re-run the Memoria patcher (`Memoria.Patcher.exe`).

## Engine-independence split

A NOVEL field runs on stock Memoria; a FORKED field REQUIRES the custom bundle (stock +
s23–s33 + the debug menu) — without it a fork loses the id-gated engine behaviors (Dante's
off-mesh exemption, narrow-map width, the fake-battle return, the softlock fixes). The shipped
faithful-opening therefore ships our custom Memoria (`dwix-custom-memoria-*.zip` = the dev
engine). Canonical statement + install paths: `ff9mapkit/docs/ENGINE.md`.

## Additional resources

- `ff9mapkit/docs/ENGINE.md` — stock vs custom engine, the three install paths, upstreaming.
- `ff9mapkit/docs/FORK_IDGATE_MAP.md` — the per-site fork-gate census + verification ledger.
- `memoria-patches/` + `memoria-patches/README.md` — every patch file and its status.
- Memory (read on demand): [[project-ff9-memoria-build]] — the full build recipe + gotchas;
  [[project-ff9-doeventcode-fork-gates]] — the four gate classes + the suite's origin story;
  [[project-ff9-fork-verification-harness]] — the harness method + verdicts.
