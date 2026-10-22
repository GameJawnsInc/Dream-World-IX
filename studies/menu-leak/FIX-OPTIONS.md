# Fixing the SaXAudio sound-effect leak: take upstream's fix, or write our own

This expands the "Fix options" section of [`FINDINGS.md`](FINDINGS.md) into what each path would actually take.
Nothing here is applied. The facts below were checked against the shared clone `C:\gd\FFIX\Memoria` (base
`6b8bb2d5`, `origin/main` fetched up to `ac44a41f`) and the live install.

## Status: A1 is built but not installed

- `py tools/build_saxaudio.py` builds both arches from the pinned `5b49756c` through `git archive`, so the shared
  clone is never checked out. The output goes to `build/saxaudio/5b49756ce04e/out/` in the main repo. x64 sha256
  is `6e369399132dd2fc…` and x86 is `57d13987e811c7dd…`. Both match the live July DLLs exactly: the same 55
  exports and the same import list (CRT plus system `xaudio2_9.dll`).
- **It is held, not installed.** The harness belongs to the s145 run, and swapping `Plugins/SaXAudio.dll`
  would change that run's conditions. Once s145 finishes, run `py tools/build_saxaudio.py --install --label
  pre-saxaudio-fix` with FF9 closed, relaunch, and run `se_soak.py`. Undo with `--restore`.
- Bundle and installer plumbing (step 3) and A2 have not started.

## What we found while mapping it

- **Upstream fixed the leak in four commits after our base, not one.** All are missing from `6b8bb2d5`:

  | Commit | PR | Side | What it does |
  |---|---|---|---|
  | `3f8f929f` | #1354 | C# (2 lines) | `SoundPlayer.StaticCreateSound` returns early when the profile already has a `SoundID`, so a profile does not mint a second voice |
  | `1576c4c2` | #1386 | build | Vendors SaXAudio's C++ source into `SaXAudio/` and drops the prebuilt DLLs. This is the only place the source lives in the repo |
  | `b39389de` | #1388 | **native + C#** | **The leak fix.** It builds the reverb/EQ/echo chain only when a preset is applied (`SetReverb`/`SetEq`/`SetEcho` create it on demand), calls `Release()` on the effects in `RemoveVoice` and `RemoveBus`, and frees buffers instead of pooling them. The C# half guards against stale or unknown `SoundID`s (`TryGetValue`, `VoiceExist`, `IsExist` before reuse) |
  | `d9a3f2cc` / `5b49756c` | #1391 / #1404 | mostly C# + 13 native lines | A refactor that moves effect presets to CSV (about 600 lines, plus SoundDebugRoom), and two `AudioVoice.cpp` fixes: restart a voice that still has queued buffers, and keep `Looping` on `Stop` |

- **The native interface did not change.** The installed July-2025 `SaXAudio.dll` exports the same 55 symbols as the
  `.def` at `1576c4c2`, `b39389de` and `origin/main` (checked with `dumpbin /exports`). A DLL built from upstream
  source therefore drops in under our current `Assembly-CSharp` with **no C# change**. The C# half can be done
  later, or not at all.
- **The native code has barely moved since it was vendored.** `git diff 1576c4c2 origin/main -- SaXAudio` is just
  #1388, #1391 and #1404 (2 files, +50/−66). Whatever we choose, the native work is small.
- **None of our patches touch the files the C# half edits.** No patch in `memoria-patches/` touches
  `SoundPlayer.cs`, `SdLibAPIWithSaXAudio.cs` or `AudioEffectManager.cs`. `FF9Snd.cs` (s141) and
  `AllSoundDispatchPlayer.cs` (s65, s145) are touched, but upstream's hunks there are comment-only or absent.
- **The engine bundle cannot ship a native plugin today.** `ff9mapkit/memoria.py` `ENGINE_DLLS` installs exactly
  three managed DLLs into `FF9_Data/Managed`. `SaXAudio.dll` lives in `FF9_Data/Plugins` (x64 and x86), which
  nothing in the kit installs, backs up, or restores. `build_memoria.py` never writes `Plugins` either: the live
  DLL still has the patcher's timestamp, 2025-07-13.
- **A native toolchain is installed.** VS Build Tools 2026 has the v145 C++ toolset and Windows SDK 10.0.26100. The
  vcxproj asks for v143, so build with `-p:PlatformToolset=v145` or add the v143 component. It links the CRT
  dynamically (`/MD`, vcruntime140), the same as the shipped DLL.
- **No managed-only fix is possible.** The leaked references are the native `pEffect` pointers, and the native
  `AudioVoice::OnBufferEnd` → `RemoveVoice` path tears a one-shot voice down. C# never sees either one. Every real
  fix ships a new `SaXAudio.dll`.

## Option A: take upstream's fix (recommended)

**A1, native only.** Build `SaXAudio.dll` (x64 and x86, Release) from `origin/main:SaXAudio/` as it is. That source
is "vendored + #1388 + #1391 + #1404". Put it in `Plugins/` and leave `Assembly-CSharp` alone.
- Effort: an afternoon. Most of it is the build and ship plumbing described below, not code.
- What it buys: the leak goes, voices without a preset no longer allocate effect chains (less CPU and memory per
  SFX), and the two `AudioVoice` fixes come along.
- Risk: low. The exports match. The lazy chain is invisible to our C#: `AudioEffectManager.ApplyPresetOnSound` still
  calls `SetReverb`/`SetEq`/`SetEcho`, and those now create the chain on demand. The one behaviour change to listen
  for is buffer pooling being removed (more alloc/free churn on bank load and unload).

**A2, the C# hardening (optional, separate patch, e.g. `s151-audio-leak-backport.patch`).** Port #1354 and #1388's
`SoundPlayer.cs` and `SdLibAPIWithSaXAudio.cs` hunks (about 60 lines). Skip #1391's EffectPreset CSV refactor: it is
a feature, it is large, and it rewrites `SoundViewController`.
- What it buys: no `KeyNotFoundException` on a stale `SoundID`, and a profile does not mint duplicate voices.
- ⚠ **Interaction with s145.** The netsync s145 music witness (`AllSoundDispatchPlayer.NetSyncMusicSoundId`)
  assumes that "a restart mints a new SoundID instance". #1354/#1388 make `StaticCreateSound` **reuse** a SoundID
  whose voice still exists. Re-run the world-coop music witness after A2. It may need a different signal.
- Needs a normal engine rebuild through `build_memoria.py`, and goes into the bundle like any other patch.

## Option B: fix it ourselves (minimal native patch)

Start from the source as first vendored (`1576c4c2:SaXAudio/`, the pre-fix code). Add only the `Release()` loop:
in `RemoveVoice`, after `DestroyVoice`, release the three `EffectData.descriptors[i].pEffect` and null them. Do the
same in `RemoveBus`. That is about 15 lines of C++, the same as upstream's hunk.
- What it buys: the leak goes and nothing else changes. Every voice keeps its eager reverb/EQ/3-second-echo chain.
- What it costs: **the same build and ship plumbing as A1**, because the native build is the expensive part either
  way. It also adds a native fork we own, where A1 converges with upstream. Allocating the three XAPOs on every
  play is still a CPU and churn cost, even though it no longer leaks.
- When to pick it: only if A1's lazy chain or the buffer-pool removal turns out to cause an audible regression we
  can't fix. Then B is the narrow fallback.

**Verdict: A1 is better than B in practice.** The upstream diff is tiny, the ABI is identical, and the plumbing is
shared, so writing our own fix saves nothing.

## Option C: change the config instead (no build)

`[Audio] Backend = 2` (SoLoud) in `Memoria.ini`. The install is currently on `1` (SaXAudio, the default).
- Cost: one ini line, reversible in seconds. It is an install-wide change (owner's call), and the kit could also set
  it through `ff9mapkit setup`.
- Unknowns: **not measured.** SoLoud may have its own per-play cost. `AudioEffectManager` presets only work on
  SaXAudio, so any reverb/EQ preset is lost. It is also a different mixer, which needs a listening pass (music
  fades, looping ambience, battle SFX).
- It is worth trying as a 5-minute experiment: run `se_soak.py` on Backend 2 to get a second data point. It is not
  the fix to ship.

## Ship and build plumbing (needed by A1 and B)

1. **Build.** `msbuild SaXAudio/SaXAudio.vcxproj -p:Configuration=Release -p:Platform=x64 -p:PlatformToolset=v145`,
   then the same with `Win32`. Use dash-style switches from Git Bash (the s60 lesson). The output goes to
   `Output\Global\Sound\SaXAudio\{x64,x86}\`. The toolset is the only new thing to wrap. Either teach
   `build_memoria.py` a `--native-audio` step or add a small `tools/build_saxaudio.py`. Either way, back up
   `Plugins/SaXAudio.dll` first (CLAUDE.md §2) and check the SHA after deploy.
2. **Dev install.** Copy into `<game>\x64\FF9_Data\Plugins\` and `x86\...`. Harness instances share `Plugins` through
   `tools/harness/instance.py` `DATA_DIRS`, so duo runs pick it up. The DLL loads at launch, so a **relaunch** is
   needed.
3. **Bundle and installer.** Extend `memoria.py` so `install_engine` also installs, backs up and restores
   `Plugins/SaXAudio.dll` for both arches. This is a new class of file with its own backup path, `--uninstall`
   symmetry, and `setup` report line. Add it to the bundle zip, and add a `restore_memoria_dll` mode.
4. **Provenance.** It is clean: SaXAudio is MIT (`SaXAudio/LICENSE`, SamsamTS), built from source, with no Square
   Enix bytes. Ship the LICENSE in the zip.
5. **Docs.** The `memoria-patches/README.md` status row, `ENGINE.md` ("the bundle replaces only managed DLLs" stops
   being true), and the CHANGELOG.

## Proof (same bar as FINDINGS)

- `py tools/play.py studies/menu-leak/se_soak.py` on SEBENCH 30488 should read **flat (< 0.05 MB/s)**. Today it
  reads +0.72 MB/s.
- `bench_soak.py`'s choice arm should match its plain arm.
- Owner listening pass, one change per test: menu blips, a battle, a looping ambient field, a music fade or
  transition, and a field that uses an effect preset, if any is configured.
- After A2 only: the world-coop s145 music witness.

## Suggested order

1. (Optional, 5 minutes) C as a measurement only, then revert.
2. A1, native only: build, back up, install, run `se_soak`, then the owner listens. Commit the build helper.
3. Ship plumbing (step 3 above) so bundle users get it. This is the real work.
4. A2 as its own patch and test, after checking the s145 interaction.
