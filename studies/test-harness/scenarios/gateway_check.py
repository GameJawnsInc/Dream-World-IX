"""Find and cross a gateway. The field-transition acceptance test.

Gateways are the most common mechanic in this project and the least visible: a trigger is an
invisible region, so "is the gateway where I think it is" has been a question only a human walking
into it could answer. Room A (30820) is a bare checkerboard with no marker at all.

So this DISCOVERS rather than assumes -- walks outward on eight bearings, reports every spot that
changed the field, warps back and keeps going, mapping the whole perimeter in one pass. Then it
crosses a found gateway deliberately and asserts the destination.

    py tools/play.py studies/test-harness/scenarios/gateway_check.py --field 30820
"""

FIELD = 30820


def run(g, field: int = FIELD):
    g.note("gateway_check: find and cross a field transition")
    g.newgame()
    g.warp(field)
    g.wait_frames(45)
    g.calibrate_axes()

    home = g.state
    print(f"[gate] room {home.field_id} ({home.field_name}) arrival {home.pos}")
    g.shot("gate-00-room")

    found = g.find_transitions(radius=430.0, back_to=field)
    for f in found:
        print(f"[gate] bearing {f['bearing']:>3}deg toward {f['toward']} -> field {f['field']}")

    g.check(bool(found), "found at least one gateway out of this room",
            f"{len(found)} transition(s): {[(f['bearing'], f['field']) for f in found]}")
    if not found:
        return

    # Cross a discovered one deliberately, and assert the destination this time rather than
    # discovering it -- the difference between "a gateway exists" and "this gateway goes there".
    target = found[0]
    g.warp(field)
    g.wait_frames(45)
    dest = g.cross(target["toward"][0], target["toward"][1], expect=target["field"])
    g.shot("gate-01-destination")
    st = g.state
    g.check(dest == target["field"], "crossed the gateway to the expected field",
            f"landed on {dest} ({st.field_name}) at {st.pos}")
    g.check(st.control, "the destination handed over control", repr(st))
    print(f"[gate] crossed into {dest} ({st.field_name}) at {st.pos}")
