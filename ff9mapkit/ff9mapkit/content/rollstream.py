"""The roll stream's generator -- the ONE owner of its constants and its math (studies/roll-stream/).

Every random draw the kit used to emit is ``B_SYSVAR[0]`` (``Comn.random8`` = ``UnityEngine.Random.Range(0, 256)``):
shared with the whole engine, never seeded, never saved -- a reload re-rolls it and nothing can predict it. A
**roll stream** is a Lehmer recurrence over ONE ``gScriptVector`` cell::

    x' = A * x mod M        A = 236, M = 65537

* **Full period.** M is prime and A is a primitive root, so every state 1..65536 appears exactly once per period
  and 0 (a fixed point) is never reached. A draw reads the state S after one advance.
* **It fits the 26-bit CalcStack.** Every operator result wraps mod 2^26 (``EBin.cs:1270-1274`` / ``:1682-1684``,
  measured in-game by rung 0), so ``A * (M - 1)`` must stay below 2^25: 236 * 65536 = 15,466,496 (2.17x headroom,
  below the 15,532,032 rung 0 read back in-game). A textbook MINSTD (16807 * x mod 2^31 - 1) is UNREPRESENTABLE
  here -- its products need 46 bits.
* **Why 236.** Among the cheap full-period multipliers it has the best worst-case lattice over lags 1..16 (2-D
  spectral nu2 >= 131); 237, the first candidate, satisfies 39*x_i + 7*x_{i+2} = 0 mod M -- every second draw lies
  on a 39.6-spaced lattice (two consumers sharing a stream, or a d100 read on alternate draws, would feel it).
* **Offline oracle.** The recurrence is pure integer arithmetic, so the build can print -- and tests and the
  harness can check -- the exact in-game sequence: :func:`states`, :func:`roll_value`, :func:`wander_target`.

This module imports nothing from the behavior compiler (it owns the math; ``behavior`` owns the emission).
"""
from __future__ import annotations

import hashlib

from ..eb import opcodes as _opcodes

A, M = 236, 65537
GEN_TAG = f"lehmer{A}.{M}"
SEED_SALT = b"ff9mapkit.stream.v1"
SEED_MIN, SEED_MAX = 1, 2 ** 31 - 1
RANGE_N_MIN, RANGE_N_MAX = 2, 256
PREDICT_K = 8


def _is_prime(n: int) -> bool:
    if n < 2:
        return False
    i = 2
    while i * i <= n:
        if n % i == 0:
            return False
        i += 1
    return True


def _prove_generator(a: int = A, m: int = M) -> None:
    """Refuse a generator that cannot run on the engine or would not visit every state. Raises RuntimeError
    (never an assert: ``python -O`` must not switch the proof off)."""
    if not _is_prime(m) or (m - 1) & (m - 2) != 0:
        raise RuntimeError(f"roll stream: M = {m} must be a prime of the form 2^k + 1 (65537)")
    if not 1 < a <= 0x7FFF:
        raise RuntimeError(f"roll stream: A = {a} must fit a const() (2..32767)")
    if pow(a, (m - 1) // 2, m) != m - 1:          # m - 1 = 2^16: a is a primitive root iff this
        raise RuntimeError(f"roll stream: A = {a} is not a primitive root of {m} -- the stream would not "
                           f"visit every state")
    if a * (m - 1) > _opcodes.EXPR_VALUE_MAX:
        raise RuntimeError(f"roll stream: A * (M - 1) = {a * (m - 1)} overflows the 26-bit CalcStack (every "
                           f"operator result wraps mod 2^26) -- a textbook MINSTD (16807 * x mod 2^31 - 1) is "
                           f"UNREPRESENTABLE in .eb RPN")


_prove_generator()


def backing_key(name: str) -> str:
    """The internal table key of a declared stream. It folds the generator in, so a persistent stream's check word
    (which hashes the key) changes with the generator and every saved stream re-seeds."""
    return f"{name}.{GEN_TAG}"


def wander_key(owner: str) -> str:
    """The internal table key of a unit's private seeded-wander stream."""
    return f"{owner}.wander.{GEN_TAG}"


def wander_ident(owner: str) -> str:
    return f"wander:{owner}"


def seed_problem(seed) -> "str | None":
    """The seed law (one text for the compiler and the TOML validate)."""
    if not isinstance(seed, int) or isinstance(seed, bool) or not SEED_MIN <= seed <= SEED_MAX:
        return (f"seed must be an int {SEED_MIN}..{SEED_MAX} (got {seed!r}) -- a roll stream is never "
                f"time-seeded; 0 is refused so it can't be read as 'random' (the build hashes (name, seed) "
                f"to its start state and prints it)")
    return None


def seed_state(ident: str, seed: int) -> int:
    """The start state x0 for ``(ident, seed)``: a hash, exactly uniform over 1..65536 and never 0. Hashed rather
    than used directly so neighbouring seeds are unrelated streams (direct seeds differ by a constant factor A^n,
    so their rolls agree structurally) and two streams sharing a seed stay independent."""
    d = hashlib.sha256(SEED_SALT + b"\0" + ident.encode("utf-8") + b"\0" + str(int(seed)).encode("ascii")).digest()
    return 1 + int.from_bytes(d[:4], "little") % (M - 1)


def advance(s: int) -> int:
    return (A * s) % M


def states(s: int, k: int) -> list:
    """The next ``k`` states after ``s`` -- what the first ``k`` draws read."""
    out = []
    for _ in range(k):
        s = advance(s)
        out.append(s)
    return out


def roll_value(s: int, lo: int, hi: int) -> int:
    """The value a roll into ``[lo, hi]`` writes from state ``s``: ``lo + s % n``. Bias at most 1/floor(65536/n):
    0 for a power of two, 0.009% for n = 6, 0.39% for n = 255."""
    return lo + s % (hi - lo + 1)


def _ctrunc(a: int, b: int) -> int:
    q = abs(a) // abs(b)
    return q if (a < 0) == (b < 0) else -q


def wander_target(s: int, cx: int, cz: int, r: int) -> tuple:
    """The (x, z) a seeded wander re-roll picks from state ``s``: x from the low byte of S, z from the next --
    (S % 256, S / 256 % 256) visits every byte pair exactly once per period -- offset (byte - 128) * r / 128
    with C#'s truncating division, the stock wander's own formula."""
    lo, hi = s % 256, (s // 256) % 256
    return cx + _ctrunc((lo - 128) * r, 128), cz + _ctrunc((hi - 128) * r, 128)


def max_bias(n: int) -> float:
    """The worst relative bias of ``s % n`` over one full period."""
    return 1.0 / ((M - 1) // n)
