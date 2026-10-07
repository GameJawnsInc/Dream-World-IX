"""PROBE: where does `world-terrain` (terrain.reshape) READ a block from -- pristine stock, or the deployed
mod override?  Three kit docstrings say it reads the deployed override and writes it back
(mesh.py:347-351 'terrain.reshape' listed as a read-modify-write writer; entrance.py fresh_discard_note
'exactly as for terrain.reshape'); terrain.py:98-104 + :132-143 say the opposite for the same-disc case
('deliberate, so a re-run re-shapes from stock instead of COMPOUNDING on its own last pass').

INSTRUMENT + CALIBRATION.  We do NOT touch the install or any mod folder: both candidate readers are
replaced by counting stubs that hand back a tiny synthetic block, and `reshape` is called with
dry_run=True (so deploy_override / auto_mirror never run).  Calibration controls:
  C1  target_disc != disc  -> terrain.py:132-138 documents the STACKED reader; the probe MUST see
      read_block_stacked called and read_block NOT called.  If it does not, the probe cannot tell the
      two readers apart and its verdict on the same-disc case is void.
  C2  a deliberately WRONG expectation is asserted to FAIL (break-it control), so the check can fail.
Then the question itself:
  Q   target_disc None (== disc) -> which reader?

Rerun:  py studies/terrain-malleability/operators/probe_reshape_read_source.py
"""
import sys
sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")

import types
from ff9mapkit.world import extract as X, terrain as T, entrance as E


class FakeBM:
    """Just enough of a BlockMesh for deform_radial/flatten (verts) -- no chan_arrays, so _walk_gate no-ops."""
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.verts = [[8.0, 0.0, -8.0], [16.0, 0.0, -8.0], [8.0, 0.0, -16.0]]
        self.tris = [(0, 1, 2)]
        self.vcount = 3


calls = {"read_block": [], "read_block_stacked": []}


def fake_read_block(bx, by, **kw):
    calls["read_block"].append((bx, by, kw.get("disc")))
    return FakeBM(bx, by)


def fake_stacked(mod_folder, bx, by, **kw):
    calls["read_block_stacked"].append((bx, by, kw.get("disc")))
    return FakeBM(bx, by)


def run(target_disc):
    calls["read_block"].clear(); calls["read_block_stacked"].clear()
    orig_rb, orig_st = X.read_block, E.read_block_stacked
    X.read_block, E.read_block_stacked = fake_read_block, fake_stacked
    try:
        # radius 8 around a point inside block (3,3): one block touched. dry_run => nothing is written.
        s = T.reshape("FF9CustomMap-PROBE-NEVER-WRITTEN", at=(3 * 64 + 12.0, -(3 * 64 + 12.0)), radius=8.0,
                      amount=1.0, disc=1, target_disc=target_disc, dry_run=True)
    finally:
        X.read_block, E.read_block_stacked = orig_rb, orig_st
    return s, len(calls["read_block"]), len(calls["read_block_stacked"])


ok = True

s1, rb1, st1 = run(9)
c1 = (rb1 == 0 and st1 >= 1)
print(f"C1 target_disc=9 : read_block calls={rb1} read_block_stacked calls={st1}  -> calibration {'PASS' if c1 else 'FAIL'}"
      "  (expect stacked only)")
ok &= c1

# C2: break-it control -- the assertion 'same-disc reads STACKED' is the WRONG expectation if the code is
# as terrain.py:139-143 says; here we check the probe can distinguish by asserting the C1 shape on target_disc=9
# is NOT what we see for a stub swap (swap the two stubs and confirm the counts swap).
orig_rb, orig_st = X.read_block, E.read_block_stacked
X.read_block, E.read_block_stacked = fake_stacked_swap = (lambda bx, by, **kw: (calls["read_block_stacked"].append((bx, by, kw.get("disc"))), FakeBM(bx, by))[1]), \
                                                   (lambda mf, bx, by, **kw: (calls["read_block"].append((bx, by, kw.get("disc"))), FakeBM(bx, by))[1])
try:
    calls["read_block"].clear(); calls["read_block_stacked"].clear()
    T.reshape("FF9CustomMap-PROBE-NEVER-WRITTEN", at=(3 * 64 + 12.0, -(3 * 64 + 12.0)), radius=8.0, amount=1.0,
              disc=1, target_disc=9, dry_run=True)
    swapped = (len(calls["read_block"]), len(calls["read_block_stacked"]))
finally:
    X.read_block, E.read_block_stacked = orig_rb, orig_st
c2 = swapped[0] >= 1 and swapped[1] == 0          # with swapped stubs the counters must swap -> probe is sensitive
print(f"C2 swapped stubs : counters (read_block-label, stacked-label) = {swapped} -> sensitivity {'PASS' if c2 else 'FAIL'}")
ok &= c2

s0, rb0, st0 = run(None)
print(f"Q  target_disc=None (same disc as read disc 1): read_block calls={rb0} read_block_stacked calls={st0}")
verdict = "PRISTINE STOCK (non-composing)" if (rb0 >= 1 and st0 == 0) else ("DEPLOYED OVERRIDE (composing)" if (st0 >= 1 and rb0 == 0) else "MIXED/UNKNOWN")
print("VERDICT:", verdict, "| probe calibrated:", ok)
sys.exit(0 if ok else 3)
