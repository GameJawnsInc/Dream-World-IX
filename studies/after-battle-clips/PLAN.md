# Clips lost on a battle return (the frame-smoother NullReferenceException)

## The symptom

A burst of `NullReferenceException at Memoria.SmoothFrameUpdater_Field.RegisterState () / HonoBehaviorSystem.Update ()`
in Unity's output_log, first seen in 1 of 4 harness runs of the sims rung-5 bench (field 30434,
`.harness-runs/20261009-233226-rung5_social`: 38 exceptions, logged straight after the post-battle field load)
and in no other archived run.

## The mechanism (engine read, then reproduced)

- `RegisterState` reads `anim[AnimationDB[actor.anim]].time` for every visible actor. A null `AnimationState`
  (the actor's current clip is not on its `Animation` component) throws, and keeps throwing every frame
  until the actor's clip changes.
- A battle return rebuilds every field model (`EventEngine.updateModelsToBeAdded` -> `ModelFactory.CreateModel`)
  and puts back only:
  1. the clips the field's `CommonAsset/EventEngine/EventAnimation/EVT_<name>.txt` lists for that model
     (`AnimationFactory.AddAnimToGameObject`). Every stock field ships this list, but no kit field did
     (Memoria.log: `Memoria asset not found: .../EventAnimation/EVT_TEST30434.txt`);
  2. the five locomotion slots: idle, walk, run, turn left, turn right (`ReassignBasicAnimationForField`).
- The player's INACTIVE clip (`SetInactiveAnimation 57` = `ANH_MAIN_F0_ZDN_BREAK1_XARM`, Zidane's
  arms-crossed fidget) is in neither. The engine's idle timer (`CheckSleep` -> `ExecAnim(p, p.sleep)`) plays
  it without adding it, so the first fidget after a battle plays a clip the rebuilt model does not have.
  The timer is random, `(200 + rand8) << 1..2` ticks, which explains the 1-in-4 rate.
- **The posed-holds hypothesis is ruled out.** Every pose clip `hold_ground` + `anim` plays is also put in
  a slot (stand and walk), and its undo restores the stand/walk slots, so a rebuilt model always gets the
  pose clip back. The repro bench has no behavior at all and fails every time.

## The repro: `fidget.field.toml` (slot 30470) + `fidget_after_battle.py`

The player stands still for 70 s (past the longest idle timer) twice: arm A on a fresh field load (the
control), arm B after a real battle.

| build | arm A (fresh load) | arm B (after the battle) |
|---|---|---|
| no clip list (the live EVT file moved aside) | 0 exceptions | **260** smoother NullReferenceExceptions |
| with the clip list, 3 runs | 0 / 0 / 0 | **0 / 0 / 0** |

In the post-fix runs the screenshots catch the fidget playing after the battle; the pre-fix run never shows
it. So the clean runs are not clean just because the fidget never fired.

## The fix (kit layer, stock Memoria)

`ff9mapkit.eventanim`: the build writes `EVT_<name>.txt.bytes` from the field's own compiled `.eb`, using the
stock format. It lists every literal clip id the script plays or slots (stand/walk/run/turns, RunAnimation,
SetInactiveAnimation, SetJumpAnimation, RunAnimationEx, SetLogicalAnimationEx), grouped per model family.
`deploy_field.py` ships it and its revert removes it. Campaign and journey deploys copy the whole built tree.

Two engine rules the list has to obey, both pinned in `tests/test_eventanim.py`:
- every clip on a model line must also be on the `animation:` line, or model creation throws KeyNotFound;
- only list a clip the engine's by-name load resolves. A clip it can't load reaches `Animation.AddClip` as
  null. Minted or unknown ids stay with the script op that adds them, as before.

No engine patch: a null guard in `RegisterState` would only hide the missing clip, and only on our engine.

## Open

- A FORK that the s23+ remap points at its donor loads the DONOR's stock list (`HonoluluFieldMain`:
  `assetKeyName` = the donor's event name). Clips from kit content added to such a fork are not in the
  donor's list, so the same loss is possible there after a battle. Not measured.
