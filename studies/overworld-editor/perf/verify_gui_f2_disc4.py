"""verify (gui skeptic): the lane proved F2 (gui_proto_cold's numpy channel decode) == the shipped
extract._decode_world_mesh on the 946 disc-1 parts the map reads only. F2 would replace the decoder EVERY world verb
uses, so this decodes EVERY Mesh object of the disc-1 AND disc-4 worldmap bundles (read only) both ways and compares
the BlockMesh ==, plus the raw float bit patterns of every channel (== on floats hides -0.0 vs 0.0 and NaN).

    py studies/overworld-editor/perf/verify_gui_f2_disc4.py
Evidence: out/perf/gui/verify/verify_gui_f2_disc4.json
"""
from __future__ import annotations

import struct
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gui_common as C                                                # noqa: E402

C.OUT = C.OUT / "verify"


def bits(chan_arrays):
    return {ci: struct.pack("<%dd" % sum(len(r) for r in rows), *[v for r in rows for v in r])
            for ci, rows in chan_arrays.items()}


def main():
    from ff9mapkit.world import extract as X
    shipped = X._decode_world_mesh
    import gui_proto_cold as PC
    orig = PC.install_fast()                                          # (patches X in this process only)
    fast = X._decode_world_mesh
    X._decode_world_mesh = shipped
    X._find_block_part = orig["find"]
    out = {}
    for disc in (1, 4):
        env = X._worldmap_env(disc, C.GAME)
        idx = X._mesh_index(env)
        n = same = same_bits = errs_same = 0
        bad = []
        ts = tf = 0.0
        for c, o in idx.items():
            t = time.perf_counter()
            try:
                a = shipped(o, disc=disc, x=0, y=0, lod="0_1")
            except Exception as e:                                    # noqa: BLE001
                a = ("error", type(e).__name__, str(e))
            ts += time.perf_counter() - t
            t = time.perf_counter()
            try:
                b = fast(o, disc=disc, x=0, y=0, lod="0_1")
            except Exception as e:                                    # noqa: BLE001
                b = ("error", type(e).__name__, str(e))
            tf += time.perf_counter() - t
            n += 1
            if isinstance(a, tuple) or isinstance(b, tuple):
                errs_same += int(a == b)
                if a != b:
                    bad.append((c, str(a)[:120], str(b)[:120]))
                continue
            eq = a == b
            same += int(eq)
            sb = bits(a.chan_arrays) == bits(b.chan_arrays)
            same_bits += int(sb)
            if not (eq and sb):
                bad.append((c, eq, sb))
        out[f"disc{disc}"] = {"meshes": n, "decoded_equal": same, "channel_bits_equal": same_bits,
                              "both_raised_same_error": errs_same, "mismatches": bad[:10],
                              "shipped_decode_s": round(ts, 2), "fast_decode_s": round(tf, 2)}
        print(disc, out[f"disc{disc}"], flush=True)
    C.dump("verify_gui_f2_disc4.json", out)


if __name__ == "__main__":
    main()
