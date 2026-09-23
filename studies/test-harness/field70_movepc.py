"""s87 verification -- field 70's MovePC NullReferenceException storm is gone, and nothing else moved.

    py tools/play.py studies/test-harness/field70_movepc.py --label s87-field70

Field 70 ("Opening-For FMV", the New Game field) builds no walkmesh (FieldMap.LoadFieldMap returns early),
and stock MovePC's PSXMovementMethod slope multiply dereferenced it on every tick. BEFORE s87, the same
New Game with no input and no warp logged 3676 `FieldMapActorController.MovePC` NREs in output_log over
the 123 s opening (29.8/s) and 0 in 4600 -- run 20260923-110034-movepc-field70 in the MAIN repo's
.harness-runs. Every harness run's "~26-30 per bench" was that storm during the newgame->warp dwell.

F0  New Game lands in field 70
F1  ZERO MovePC NREs for the whole field-70 stay (was ~30/s) -- no input, no warp
F2  field 70 still leaves on its OWN script's Field() (the movie plays and hands off as before)
F3  the player still WALKS on the destination (the guard is identity on a field with a walkmesh)
F4  zero MovePC NREs on the destination while walking
"""
from __future__ import annotations

import time

FIELD_70 = 70


def _movepc(g, mark) -> int:
    return sum(1 for e in g.exceptions_since(mark) if e.through("FieldMapActorController.MovePC"))


def _others(g, mark) -> dict:
    out: dict = {}
    for e in g.exceptions_since(mark):
        if not e.through("FieldMapActorController.MovePC"):
            out[str(e)] = out.get(str(e), 0) + 1
    return out


def run(g) -> None:
    g.note("s87 field-70 MovePC guard")
    st = g.newgame()
    m0 = g.log_mark()
    t0 = time.monotonic()
    g.check(st.field_id == FIELD_70, "F0: New Game lands in field 70", f"field {st.field_id}")

    g.wait_frames(150)
    g.shot("field70-dwell")
    print(f"[s87] 150 frames into field 70: MovePC NRE = {_movepc(g, m0)} (was 74 before s87)")

    left = True
    try:
        g.wait_for(lambda s: s.field_id not in (FIELD_70, 0), timeout=240.0,
                   what="field 70's script to leave on its own")
    except Exception as err:                              # noqa: BLE001 -- reported as F2's failure
        left = False
        print(f"[s87] field 70 never left: {err}")
    dwell = time.monotonic() - t0
    m1 = g.log_mark()
    n70 = _movepc(g, m0)
    print(f"[s87] field 70 stay {dwell:.1f}s: MovePC NRE = {n70} (was 3676 in 123 s); "
          f"others {_others(g, m0) or 'none'}")
    g.check(n70 == 0, "F1: zero MovePC NREs for the whole field-70 stay", f"{n70} in {dwell:.1f}s")
    g.check(left, "F2: field 70 leaves on its own script's Field()",
            f"-> field {g.state.field_id} after {dwell:.1f}s")
    if not left:
        return

    dest = g.wait_playable(timeout=60.0)
    x0, z0 = dest.player_x, dest.player_z
    far = 0.0
    for d in ("up", "right", "down", "left"):
        g.walk(d, 15)
        g.wait_frames(19)
        s = g.state
        if None not in (x0, z0, s.player_x, s.player_z):
            far = max(far, abs(s.player_x - x0) + abs(s.player_z - z0))
    g.shot("destination-walked")
    g.check(far > 100, f"F3: the player walks on field {dest.field_id}", f"max displacement {far:.0f}u")
    n_dest = _movepc(g, m1)
    g.check(n_dest == 0, f"F4: zero MovePC NREs on field {dest.field_id} while walking",
            f"{n_dest}; others {_others(g, m1) or 'none'}")
