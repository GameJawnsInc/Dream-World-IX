"""Look at a field. The cheapest possible scenario, and the one I reach for first.

Warps somewhere, captures a frame, and prints where the character stands. Before this existed,
answering "what is actually in room 30810 and where is the chest" meant asking a human to go and
look. Now it is 30 seconds and a PNG I can read.

    py tools/play.py studies/test-harness/scenarios/recon.py --field 30810
"""

FIELD = 30810


def run(g, field: int = FIELD):
    g.note(f"recon {field}")
    g.newgame()
    g.warp(field)
    g.wait_frames(90)

    st = g.state
    g.shot(f"recon-{field}")
    print(f"[recon] field {st.field_id} ({st.field_name})")
    print(f"[recon] player at {st.pos}  facing {st.raw.get('player', {}).get('dir')}  "
          f"floor {st.raw.get('player', {}).get('floor')}")
    print(f"[recon] ui={st.ui_state} scene={st.scene} control={st.control}")
    if st.dialog_open:
        print(f"[recon] dialogue already open: {st.text!r}")
    g.check(st.field_id == field, f"arrived on field {field}", repr(st))
