# The Memoria engine build recipe

Distilled from memory `project-ff9-memoria-build` (the canonical deep recipe — read it for the
full history) and the repo brief `CLAUDE.md` §4. Load-bearing lines below are quoted verbatim
from those sources; where they conflict, the memory file wins.

## Preconditions (in order, before any build)

1. **STOP-confirm** the change is truly engine-side (see SKILL.md — most tasks need no rebuild).
2. **Back up the game's live DLLs first** — the build auto-deploys with no backup (below).
   Snapshot `Assembly-CSharp.dll` from BOTH `x64\FF9_Data\Managed\` and `x86\FF9_Data\Managed\`
   to `backups/<file>.<timestamp>`.

## Toolchain (verified on this machine)

- MSBuild: `C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\MSBuild\Current\Bin\amd64\MSBuild.exe`
  — "use the **amd64** one; MSBuild 18.6.3". No standalone `nuget.exe` needed
  (`msbuild -t:Restore` restores the lone PackageReference, Newtonsoft.Json 13.0.4). No .NET
  SDK needed (Framework v3.5 target).
- Source clone: `C:\gd\FFIX\Memoria\` (gitignored; shared, not per-worktree).

## Version matching — commit `6b8bb2d5`

The installed engine's `Memoria.log` line `[Initialization] Memoria version: YYYY-MM-DD` is the
assembly **compile date**, not a tag. Installed here = **2025-07-13** → build from the `main`
commit nearest that date = **`6b8bb2d5`** (`git checkout 6b8bb2d5`). Do NOT build from a much
newer HEAD for a drop-in `Assembly-CSharp.dll` unless Memoria.Prime/UI/native are rebuilt and
deployed as a matched set. Sanity check: built sibling DLL sizes ≈ installed (Memoria.Prime
189456, UnityEngine.UI 205840; a fresh compile is within a few %, not identical).

## One-time References setup

The repo's `Memoria\References\*.dll` Unity/framework refs are encrypted in
`References\Dependencies.7z` (CI-only password). Instead copy them from the game's Managed
folder (`…\FINAL FANTASY IX\x64\FF9_Data\Managed\` → `Memoria\References\`):
`Assembly-CSharp-firstpass.dll, mscorlib.dll, System.dll, System.Core.dll,
System.Runtime.Serialization.dll, UnityEngine.dll, UnityEngine.UI.dll,
UnityEngine.Networking.dll, Mono.Security.dll`. (`Memoria.MSBuild.dll` + `Microsoft.Build.*`
are already in References.)

## THE build command (critical quirk — quote verbatim)

```
msbuild Assembly-CSharp\Assembly-CSharp.csproj /t:Build /p:Configuration=Release /p:SolutionDir=C:\gd\FFIX\Memoria\ /m
```

- "**`/p:SolutionDir=...\Memoria\` (trailing backslash) is REQUIRED.**" Building the .csproj
  directly leaves `$(SolutionDir)` undefined → `FrameworkPathOverride` breaks → MSBuild pulls
  the machine's .NET **v4.0 mscorlib** alongside References → `CS1703`/`CS0433` duplicate-type
  errors (`Func`/`Action`) in Memoria.Prime + UnityEngine.UI. Defining SolutionDir makes the
  framework resolve from References → clean build (and fixes the Deploy UsingTask path).
- "**Do NOT use a global `/p:NoStdLib=true`**" to "fix" the above — it breaks
  Memoria.XInputDotNetPure (no explicit mscorlib ref). SolutionDir is the right fix.
- **Run from PowerShell, not bash** — "bash mangles the `/p:SolutionDir=C:\gd\FFIX\Memoria\`
  backslashes → MSB1008".
- Build is ~5-7s. Output → `Memoria\Output\Assembly-CSharp.dll` (~5.5 MB). Warnings
  (CS0414/CS0169 unused fields) are normal.

## AUTO-DEPLOY — building == deploying (and NO pristine backup is kept)

The csproj `AfterBuild` runs `Memoria.MSBuild.Deploy`, which "auto-finds the game via
`FF9_Launcher.exe` and copies the built `Assembly-CSharp.dll` + `Memoria.Prime.dll` +
`UnityEngine.UI.dll` into BOTH `x64\` and `x86\` `FF9_Data\Managed\`". It does NOT keep a
backup — hence precondition 2. (`XInputDotNetPure.dll` / `Newtonsoft.Json.dll` are not
redeployed.) A rebuild also bumps the Assembly-CSharp FileVersion, so the Scripts-DLL drift
check may fire even on an API-compatible rebuild — recompile the mod scripts DLL once the game
is closed to clear the cosmetic stamp.

## Adding code / recording patches

- **New `.cs` files must be added to the csproj `<Compile Include>`** — a file on disk alone
  is not compiled.
- Source edits are tracked as patches in `memoria-patches/*.patch`, applied on top of base
  `6b8bb2d5`; regenerate a patch as `git -C <clone> diff` of the touched paths against base
  (use `git add -N` first for new files), then reverse-check it applies cleanly.
- **Serialization trap (verbatim law):** "NEVER add a SERIALIZED (public / [SerializeField])
  field to a baked MonoBehaviour" — components like `WMWorld` are serialized into prefabs
  baked in p0data; a new serialized field shifts the layout → the component deserializes
  corrupt → black screen. Runtime-only cache fields must be `[System.NonSerialized] public`
  (or `private`). Adding new METHODS is always safe. Diagnose such crashes via
  `<game>/x64/FF9_Data/output_log.txt`, NOT just `Memoria.log` (Unity engine NREs only land
  in output_log.txt).

## Offline verification (the agent cannot run the game)

- New TYPE/FIELD names land in the DLL metadata string heap → grep the binary for the needle
  and confirm the game's copy == `Output\` bytes.
- Method-body-only edits are not greppable here → rely on a clean compile (0 errors) + the
  saved source patch. In-game behavior still needs a human playtest after a full relaunch.

## Restore / revert / bisect

- `py tools/restore_memoria_dll.py baseline` — copies the no-edits
  `*.baseline-rebuild-6b8bb2d5.*` backups back to both Managed folders (isolates "my edits"
  from "the rebuild itself"). Verify the baseline files actually exist in `backups/` before
  relying on this (they have gone missing before).
- True original install: re-run `Memoria.Patcher.exe` (or Steam verify-integrity + re-patch).
- Close FF9 first: restore hits `WinError 1224` on any DLL the running game has memory-mapped
  (byte-identical copies are no-ops).
