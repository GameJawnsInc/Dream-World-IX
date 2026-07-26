"""Offline evaluation of WORLD11 entry-15 tag-1's BOARD gate, mirroring the DECOMPILED evaluator.

Every op below replicates a specific line of `C:\\gd\\FFIX\\Memoria`. Nothing here is guessed:

  obj(uid).f[0] / .f[2]   EBin.cs:1751-1793  getvobj case 0 / case 2 ->
                          `CastFloatToIntWithChecking(((PosObj)obj).pos[0 or 2])`.
                          EBin.cs:1830-1840  CastFloatToIntWithChecking is a plain round-to-int:
                          Floor/Ceil/Round agreement, NO scaling.
                          => the field is the actor's position in **WORLD UNITS**, not x256 fixed point.
                          (case 1 / Y is additionally negated: `-1 * Cast...`.)
                          `if (obj.cid != 4) return 0;` -- a non-actor reads 0; a NULL obj would
                          NullReference (no guard), which does not happen in game, so both uids resolve.
  GetObjUID(250)          EventEngine.cs:943-955  `if (uid == 250) uid = this._context.controlUID;`
                          => "whoever currently holds control" -- the walking avatar while on foot.
  GetObjUID(15)           same function, falls through to the activeObj walk -> the boat.
  B_MINUS                 EBin.cs:691-698   Int32 subtract, pushed via expr_Push_v0_Int24.
  B_LT                    EBin.cs:715-730   signed Int32 `<`. (Two hardcoded hacks exist -- Treno
                          fldMapNo 908/1908 with gCur.uid 0 and t3 == 80, and gCur.uid 13 with
                          t3 == -300 -- NEITHER applies to WORLD11 / uid 15 / our constants.)
  B_CONST4                EBin.cs:1241-1246 `(int & 0x3FFFFFF) | Int26`, and the read-back at
                          EBin.cs:1682-1684 sign-extends `(t0 << 6) >> 6`.
                          => constants are signed 26-bit: -33554432 .. 33554431.
  operand order           `A B B_LT` evaluates t3 = B (popped first, i.e. last pushed) then _v0 = A,
                          and yields `A < B`.

Run:  py studies/custom-vehicle/range_gate/eval_gate.py
"""
from __future__ import annotations

INT26_MASK = 0x3FFFFFF


def _sx26(t0: int) -> int:
    """(t0 << 6) >> 6 on a 32-bit signed register -- the engine's Int26 read-back."""
    v = (t0 & 0xFFFFFFFF) << 6 & 0xFFFFFFFF
    if v & 0x80000000:
        v -= 1 << 32
    return v >> 6


def c4(v: int) -> int:
    return _sx26(v & INT26_MASK)


def f(pos: tuple, idx: int) -> int:
    """obj(uid).f[idx] for a world actor: round-to-int of pos[idx], WORLD UNITS."""
    return round(pos[0] if idx == 0 else pos[1])          # (x, z) tuple; idx 0 = X, 2 = Z


# ---- the two gate expressions ---------------------------------------------------------------

def gate_old(player: tuple, boat: tuple, near_const: int) -> bool:
    """The DEPLOYED gate: a two-sided difference test against `near_const`.

        (p.x - b.x) < K && (b.x - p.x) < K && (p.z - b.z) < K && (b.z - p.z) < K
    """
    K = c4(near_const)
    px, pz = f(player, 0), f(player, 2)
    bx, bz = f(boat, 0), f(boat, 2)
    return ((px - bx) < K and (bx - px) < K and (pz - bz) < K and (bz - pz) < K)


def gate_new(player: tuple, x_lo: int, x_hi: int, z_lo: int, z_hi: int) -> bool:
    """The CORRECTED gate: an absolute constant window around the mooring, in world units.

        LO < p.x  &&  p.x < HI  &&  LO < p.z  &&  p.z < HI      (all signed B_LT)
    """
    px, pz = f(player, 0), f(player, 2)
    return (c4(x_lo) < px and px < c4(x_hi) and c4(z_lo) < pz and pz < c4(z_hi))


# ---- probe points ---------------------------------------------------------------------------

MOORING = (492, -1130)
DOCK = (493, -1114)
PROBES = [
    ("mooring   (beside the beached boat)", MOORING, True),
    ("dock      (493,-1114)", DOCK, True),
    ("Ashvale quay      (48,-1168)", (48, -1168), False),
    ("Tidefall trigger  (420,-1232)", (420, -1232), False),
    ("far ocean         (1200,-400)", (1200, -400), False),
]

# the window the owner specified: X 452..532, Z -1170..-1090 (a +/-40u box on the mooring).
# Expressed as STRICT bounds one unit outside, so the inclusive box is exactly [452,532]x[-1170,-1090].
X_LO, X_HI = 451, 533
Z_LO, Z_HI = -1171, -1089

print("=" * 100)
print("SANITY: does const4 round-trip a negative through the 26-bit Int26 encoding?")
print("=" * 100)
for v in (-1171, -1089, 25600, 100, -289280):
    print(f"  const4({v & INT26_MASK:>10}) [raw {v}] -> reads back {c4(v):>8}   {'OK' if c4(v) == v else '** MISMATCH **'}")
print(f"  (and the deployed MoveInstantXZY z arg 4294678016 reads back {c4(4294678016)} = -1130*256)")

print()
print("=" * 100)
print("THE DEPLOYED GATE -- two-sided difference vs const4(25600)")
print("  25600 was authored as '100u x 256' (the FIXED-POINT domain of MoveInstantXZY args and the")
print("  gEventGlobal position record) but f[] reads WORLD UNITS. The FF9 overworld spans ~1536u in x")
print("  and ~1280u in z, so the largest possible |delta| anywhere (~2000u) is still far below 25600.")
print("=" * 100)
print(f"  {'probe':<38}{'|dx|':>7}{'|dz|':>8}{'gate':>8}   expected")
allok = True
for label, p, want in PROBES:
    got = gate_old(p, MOORING, 25600)
    dx, dz = abs(f(p, 0) - f(MOORING, 0)), abs(f(p, 2) - f(MOORING, 2))
    allok &= (got == want)
    print(f"  {label:<38}{dx:>7}{dz:>8}{str(got):>8}   {want}{'' if got == want else '   <-- WRONG'}")
print(f"  => the deployed gate is {'ALWAYS TRUE (broken open)' if all(gate_old(p, MOORING, 25600) for _, p, _ in PROBES) else 'selective'}")

print()
print("=" * 100
      )
print(f"THE CORRECTED GATE -- absolute window, world units: x in ({X_LO},{X_HI}) z in ({Z_LO},{Z_HI})")
print("=" * 100)
print(f"  {'probe':<38}{'x':>7}{'z':>9}{'gate':>8}   expected")
ok = True
for label, p, want in PROBES:
    got = gate_new(p, X_LO, X_HI, Z_LO, Z_HI)
    ok &= (got == want)
    print(f"  {label:<38}{f(p,0):>7}{f(p,2):>9}{str(got):>8}   {want}{'' if got == want else '   <-- WRONG'}")
print()
print("=" * 100)
old_always_true = all(gate_old(p, MOORING, 25600) for _, p, _ in PROBES)
print("VERDICT")
print(f"  deployed gate always-true everywhere (the bug): {old_always_true}   <- must be True")
print(f"  corrected gate matches every probe:             {ok}   <- must be True")
print("=" * 100)
raise SystemExit(0 if (ok and old_always_true) else 1)
