"""Visit every registered field in one launch and report what is on each.

One game start amortised across every bench, instead of ~40 seconds of boot per field. Answers
"what have I actually got to test against" -- which, given field ids are a global namespace shared
with every other worktree's deploys, changes from day to day.

    py tools/play.py studies/test-harness/scenarios/recon_all.py
"""


def run(g, field: int | None = None):
    g.note("recon_all")
    available = sorted(g.registered_fields())
    print(f"[recon] registered: {available}")

    g.newgame()
    visited = []

    for fid in available:
        try:
            g.warp(fid, timeout=45.0)
        except Exception as err:
            print(f"[recon] {fid}: UNREACHABLE -- {err}")
            visited.append({"field": fid, "ok": False, "note": str(err)[:120]})
            continue

        g.wait_frames(45)
        st = g.state
        g.shot(f"recon-{fid}")

        # A quick Confirm on the spot: cheap, and tells us whether there is anything to talk to here
        # without walking the whole room.
        opened = g.interact(timeout=2.5)
        speaks = bool(opened and (opened.text.strip() or opened.choice))
        if opened:
            for _ in range(3):
                if not g.state.dialog_open:
                    break
                g.press("cancel", 3)
                g.wait_frames(8)

        row = {
            "field": fid,
            "ok": True,
            "name": st.field_name,
            "pos": [st.player_x, st.player_z],
            "control": st.control,
            "speaks_on_arrival": speaks,
        }
        visited.append(row)
        print(f"[recon] {fid}: {st.field_name}  at {row['pos']}  control={st.control}  "
              f"talks-here={speaks}")

    reachable = [v for v in visited if v.get("ok")]
    g.check(len(reachable) == len(available),
            "every registered field was reachable",
            f"{len(reachable)}/{len(available)}")
    g.check(all(v.get("control") for v in reachable),
            "every reachable field handed over control",
            str([v["field"] for v in reachable if not v.get("control")]))
