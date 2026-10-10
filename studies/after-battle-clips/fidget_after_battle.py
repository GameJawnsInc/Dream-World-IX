"""THE FIDGET AFTER A BATTLE -- the deterministic repro of the sims rung-5 smoother burst (PLAN.md here).

    py tools/deploy_field.py studies/after-battle-clips/fidget.field.toml --id 30470   # bench (relaunch on first deploy)
    py tools/play.py studies/after-battle-clips/fidget_after_battle.py                 # this

The player stands still until the engine's idle timer plays the player's INACTIVE clip (SetInactiveAnimation 57,
Zidane's arms-crossed fidget) -- twice: once on a fresh field load (arm A, the control) and once after a real
battle (arm B). EnableMove sets the timer to (200 + rand8) << 2 ticks, at most 1820 ticks = ~61 s at the 30 Hz
event tick, so each ~70 s stand holds at least one fidget. Arm A's clip was added by the op that set it; arm B's
model was rebuilt by the battle return, which re-adds only the field's EventAnimation list + the five locomotion
slots. Without the list the fidget plays a clip the model does not have and Memoria's frame smoother
(SmoothFrameUpdater_Field.RegisterState) throws a NullReferenceException every frame until the clip ends.
"""
from __future__ import annotations

import time

FID = 30470
SCENE = 67                    # a lone Goblin a New Game party can beat
STAND = 70.0                  # seconds -- past the longest idle timer (~61 s), so a fidget fires in every arm


def _smoother(excs) -> list:
    return [e for e in excs if e.through("SmoothFrameUpdater_Field")]


def _stand(g, tag: str) -> tuple[list, list]:
    """Hold still for STAND seconds with no input; return (every exception, the smoother's) over the stand."""
    mark = g.log_mark()
    end = time.monotonic() + STAND
    n = 0
    while time.monotonic() < end:
        time.sleep(7.0)
        n += 1
        g.shot(f"{tag}-{n:02d}")
    excs = g.exceptions_since(mark)
    print(f"[fidget] {tag}: {len(excs)} exception(s), {len(_smoother(excs))} from the frame smoother")
    return excs, _smoother(excs)


def run(g) -> None:
    g.newgame()
    g.warp(FID)
    g.no_encounters()
    g.wait_for(lambda s: s.field_id == FID and s.control and s.ui_state == "FieldHUD", timeout=30,
               what="control on the bench")

    excs, smo = _stand(g, "A-fresh")
    g.check(not excs, "A: on a fresh field load the player's fidget plays with no exception (the control)",
            "; ".join(str(e) for e in excs[:5]))

    epoch = g.state.battle_epoch
    g.start_battle(SCENE)
    result = g.fight()
    g.check(result in (1, 2), "the party wins the battle", f"result {result}")
    g.wait_for(lambda s: s.field_id == FID and s.control and not s.in_battle and s.battle_epoch != epoch,
               timeout=60, what="the return to the bench")

    excs, smo = _stand(g, "B-after-battle")
    g.check(not smo, "B: after a battle return the player's fidget plays with no frame-smoother exception",
            f"{len(smo)} smoother NullReferenceException(s)")
    g.check(not excs, "B: no exception at all over the after-battle stand",
            "; ".join(str(e) for e in excs[:5]))
