# The choice-menu memory leak is the sound-effect leak in stock Memoria's SaXAudio

**Verdict.** Every sound effect FF9 plays grows `FF9.exe` by about 0.75 MB, and the memory is never returned.
A dialogue choice plays about two sound effects: the cursor blip when the cursor moves (SE 103, `Dialog.OnItemSelect`
-> `ETb.SndMove`) and the confirm blip on close (`Dialog.Hide` -> `ETb.SndOK`, gated on `HasChoices`). A plain
window plays none. The leak is in the **native audio plugin `SaXAudio.dll` that stock Memoria ships** (the July-2025
build that the Memoria patcher installed in `x64/FF9_Data/Plugins/`). None of our patches touch the sound path; they
only call `FF9SFX_Play`. Upstream already fixed it: Albeoris/Memoria `b39389de` "Fix SFX playback memory leak in
SaXAudio" (#1388, 2026-04-09), which landed after our base commit `6b8bb2d5`.

It was not the cause of the owner's lag (a restart fixed that). It is general: battles, field SFX and menus all leak at
the same rate per sound played. The choice menu was just the first place anyone measured it.

## Measurements (harness, 2026-10-10, ~60 fps, `memprobe.private_mb` = Win32 PrivateUsage)

| Run | What | Result |
|---|---|---|
| `choice_soak.py` on bench 30431 | idle 35 s | flat (0.0 MB) |
| | 30 pot menus, open + decline at once | **+1.41 MB/menu** |
| | 10 pot menus, each held open 10 s | +1.67 MB/menu (5x longer open, about the same cost, so it is per event, not per frame) |
| `bench_soak.py` on LEAKBENCH 30487 (no HUD, no behavior) | 30 plain windows | **+0.015 MB/window (flat)** |
| | 30 plain 2-option choices | **+1.57 MB/choice** |
| | 30 plain windows with the "!" bubble | flat |
| | 30 choices with the "!" bubble | +1.57 MB/choice (bubble irrelevant) |
| | ONE choice held open, cursor moved 60 times | **+0.81 MB per cursor move** |
| | 60 choices (same launch) | +1.56 MB/choice, linear |
| `se_soak.py` on SEBENCH 30488 | an NPC's behavior plays SE 103 about once a second; no window, no UI, no input | **+0.72 MB/s, linear (+86 MB in 120 s)** |

The harness choice moves the cursor once and confirms once, so 2 x ~0.78 MB matches the ~1.57 MB per choice. The
owner's ~3 MB per menu without the harness fits a human moving the cursor a few more times. Raw samples are in `data/`.

## Mechanism (source of the matching SaXAudio build, SamsamTS/SaXAudio @ `019bbb51`, 2025-07-12)

- `SaXAudio::CreateVoice` (SaXAudio.cpp ~466-520) builds a three-effect chain for **every** voice:
  `XAudio2CreateReverb`, `CreateFX(FXEQ)`, `CreateFX(FXEcho, { MaxDelay = 3000 ms })`, then `CreateSourceVoice` with
  that chain.
- `SaXAudio::RemoveVoice` (~1099-1150, called from `AudioVoice::OnBufferEnd` when a one-shot finishes) calls
  `SourceVoice->DestroyVoice()`, then `voice->Reset()` and recycles the `AudioVoice` to its pool. **Nothing calls
  `Release()` on the three `pEffect` XAPOs**: XAudio2 drops only its own reference, so the app's reference leaks.
  The echo's 3-second delay line dominates the ~0.75 MB.
- The C# side (`SdLibAPIWithSaXAudio.CreateSound`) asks for a new voice on every play (`CreateVoice(bankID, busID)`).
  The decoded bank is cached once in `sfxImmediateDB`, so the bank is not the leak. The managed per-play bookkeeping
  (`sounds` dictionary, `AllSoundDispatchPlayer.sfxChanels`) is a few bytes per play.

Upstream's fix (#1388) creates the effect chain only when the C# side applies a preset, frees buffers instead of
pooling them, and releases bus effects. Their note reports going from about 4 MB per SFX to occasional 0.1 MB.

## Attribution checks that came back clean

- Dialog/choice code (`Dialog.InitializeChoiceProcess`/`ResetChoose`, `ButtonGroupState`, `PointerManager`, the
  dialog pool): every per-open allocation is destroyed or pooled.
- Our dialog-touching patches: s84/s85 netsync L2 is gated on role + socket and allocates 8-byte frames. The s83
  harness choice publisher builds throwaway strings. s88 story-trace is gated and keyed by write site. s24/s29/s65
  only swap `fldMapNo` for `EffectiveFieldId`. No patch edits `Global/Sound`, `Global/Sd` or the SaXAudio wrapper
  (`git status` in the clone).
- No per-frame exception spam in Memoria.log or output_log.txt during the soaks.

## Fix options (not applied: none is small, and each changes the shared install)

1. **Backport upstream.** Build `SaXAudio.dll` from Memoria's in-repo `SaXAudio/` project at `b39389de` or later
   (#1391 `d9a3f2cc` follows up), and port the C# half of #1388 (`SdLibAPIWithSaXAudio.cs`, `SoundPlayer.cs`
   stale-SoundID handling). Also check that `AudioEffectManager.ApplyPresetOnSound` still works with the lazy chain.
   This puts a new native plugin in `Plugins/` and in the dwix engine bundle. Medium effort.
2. **Minimal native patch** to the July source: `Release()` the three `pEffect`s right after `CreateSourceVoice`
   (XAudio2 holds its own reference for the voice's lifetime). Small C++ change, but it still needs a native
   toolchain and a plugin swap.
3. **Config workaround, no code:** `[Audio] Backend = 2` (SoLoud) in Memoria.ini. Not measured here. It changes
   audio for everyone on the install, so it needs the owner's call.

## Reproduce

```
py tools/deploy_field.py studies/menu-leak/bench/leakbench.field.toml --id 30487
py tools/deploy_field.py studies/menu-leak/bench/sebench.field.toml --id 30488
py tools/play.py studies/menu-leak/bench_soak.py                        # SOAK_SPOTS / SOAK_N / SOAK_EVERY
py tools/play.py studies/menu-leak/se_soak.py                           # SOAK_SECONDS / SOAK_EVERY_S
py tools/play.py studies/menu-leak/choice_soak.py                       # bench 30431; needs studies/sims/bench/
```

A fix is proven when `se_soak.py` reads flat (well under 0.05 MB/s) and `bench_soak.py`'s choice arm matches its
plain arm.
