"""The roll stream's generator (content/rollstream.py) -- the ONE owner of its constants and math.

Goldens pin the contract (a persistent stream's check word folds GEN_TAG in, so these numbers are a promise
to every save that holds a stream); the lattice test documents why 236 and not 237."""
import math
from pathlib import Path

import pytest

from ff9mapkit.content import rollstream as R
from ff9mapkit.eb import opcodes


def test_the_generator_constants_and_goldens():
    assert (R.A, R.M, R.GEN_TAG) == (236, 65537, "lehmer236.65537")
    assert [(ident, R.seed_state(ident, seed)) for ident, seed in
            (("eph", 1), ("dwix_rs1", 1), ("wander:walker", 1), ("hilo", 4242), ("eph", 2))] == \
        [("eph", 14369), ("dwix_rs1", 28707), ("wander:walker", 30217), ("hilo", 16315), ("eph", 19479)]
    assert R.states(14369, 4) == [48697, 23517, 44904, 45887]
    assert R.roll_value(48697, 0, 5) == 1 and R.roll_value(24541, 1, 100) == 42
    assert R.wander_target(53216, 0, -1100, 300) == (225, -915)
    assert R.backing_key("eph") == "eph.lehmer236.65537"


def test_the_period_is_full():
    s, n = 1, 0
    while True:
        s = R.advance(s)
        n += 1
        if s == 1:
            break
    assert n == R.M - 1


@pytest.mark.parametrize("a,m,msg", [
    (16807, 2 ** 31 - 1, "prime of the form"),        # MINSTD: not 2^k+1, and would overflow anyway
    (4, 65537, "not a primitive root"),
    (236, 65536, "prime"),
    (600, 65537, "overflows the 26-bit CalcStack"),   # a primitive root whose product needs > 25 bits
])
def test_an_unrunnable_generator_is_refused_at_import(a, m, msg):
    if m == 65537 and a == 600:
        assert pow(600, (m - 1) // 2, m) == m - 1     # 600 IS full-period: the refusal is the envelope
    with pytest.raises(RuntimeError, match=msg):
        R._prove_generator(a, m)
    R._prove_generator()                              # the shipped constants pass
    assert R.A * (R.M - 1) <= opcodes.EXPR_VALUE_MAX


def _nu2(a: int, lag: int) -> float:
    """Shortest non-zero vector of the lattice {(x, a^lag x mod M)} (Gauss reduction)."""
    u, v = (1, pow(a, lag, R.M)), (0, R.M)
    while True:
        if u[0] ** 2 + u[1] ** 2 > v[0] ** 2 + v[1] ** 2:
            u, v = v, u
        k = round((u[0] * v[0] + u[1] * v[1]) / (u[0] ** 2 + u[1] ** 2))
        if k == 0:
            return math.hypot(*u)
        v = (v[0] - k * u[0], v[1] - k * u[1])


def test_236_has_no_short_lattice_where_237_does():
    """237 satisfies 39*x_i + 7*x_{i+2} = 0 mod M: every second draw lies on a 39.6-spaced lattice (two
    consumers sharing a stream, or wander targets k and k+2, would feel it). 236's worst lag in 1..16 is 131."""
    assert (39 + 7 * pow(237, 2, R.M)) % R.M == 0
    assert _nu2(237, 2) < 50
    assert min(_nu2(R.A, lag) for lag in range(1, 17)) >= 120


def test_seeds_are_hashed_uniform_and_refused_when_bad():
    xs = {R.seed_state(f"s{i}", i) for i in range(1, 4000)}
    assert all(1 <= x <= R.M - 1 for x in xs)
    # neighbouring seeds are unrelated streams: their first d6 rolls agree ~1/6 of the time, not always
    agree = sum(R.roll_value(R.advance(R.seed_state("n", k)), 1, 6)
                == R.roll_value(R.advance(R.seed_state("n", k + 1)), 1, 6) for k in range(1, 1001))
    assert 110 <= agree <= 230
    for bad in (0, -1, 2 ** 31, True, 1.5, "7", None):
        assert R.seed_problem(bad)
    assert R.seed_problem(1) is None and R.seed_problem(2 ** 31 - 1) is None


@pytest.mark.parametrize("n", [2, 3, 6, 100, 255, 256])
def test_the_roll_bias_stays_under_half_a_percent(n):
    counts = [0] * n
    for s in range(1, R.M):
        counts[R.roll_value(s, 0, n - 1)] += 1
    assert (max(counts) - min(counts)) / min(counts) <= R.max_bias(n) + 1e-12 <= 0.004


def test_the_wander_bytes_visit_every_pair_once():
    """wander_target's byte split: at radius 128 an offset IS (byte - 128), so over one period the targets are
    exactly the 256 x 256 grid, each once -- x from the low byte, z from the next (a swapped or repeated byte
    would collapse the set)."""
    targets = [R.wander_target(s, 0, 0, 128) for s in range(1, R.M)]
    assert set(targets) == {(x, z) for x in range(-128, 128) for z in range(-128, 128)}
    assert R.wander_target(0x1234 + 0x10000 * 0, 0, 0, 128) == (0x34 - 128, 0x12 - 128)


def test_the_import_itself_runs_the_proof():
    """The module proves its constants AT IMPORT: the same source with an overflowing multiplier refuses to
    load (a proof that only a test calls is a proof the shipped build never runs)."""
    src = Path(R.__file__).read_text(encoding="utf-8")
    assert src.count("A, M = 236, 65537") == 1
    ns = {"__name__": "ff9mapkit.content._rollstream_probe", "__package__": "ff9mapkit.content"}
    exec(compile(src, R.__file__, "exec"), dict(ns))                  # the shipped source loads
    with pytest.raises(RuntimeError, match="overflows the 26-bit CalcStack"):
        exec(compile(src.replace("A, M = 236, 65537", "A, M = 600, 65537"), R.__file__, "exec"), dict(ns))
