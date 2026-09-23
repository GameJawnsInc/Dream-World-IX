"""Calibrate the test interpreter's arithmetic against the ENGINE before any roll-stream claim leans on it.

The in-game rows are the values studies/roll-stream rung 0 read off a HUD strip in the running game
(.harness-runs/20260923-004842-rs-rung0); the source rows are C# semantics the engine code states
(EBin.cs:645-682 -- a zero divisor pushes the NUMERATOR; truncation toward zero)."""
import pytest

from ._ebengine import Engine


@pytest.mark.parametrize("expr,want", [
    ("const(237) const4(65536) B_MULT const4(65537) B_REM", 65300),       # in-game, rung 0
    ("const(237) const4(12345) B_MULT const4(65537) B_REM", 42137),       # in-game, rung 0
    ("const4(65536) const(237) B_MULT", 15532032),                         # in-game, rung 0
    ("const4(33554431) const(1) B_PLUS", -33554432),                       # in-game, rung 0: the 2^26 WRAP
    ("const4(65535) const(256) B_DIV", 255),                               # in-game, rung 0
])
def test_the_interpreter_reproduces_rung_0s_in_game_rows(expr, want):
    assert Engine().eval(expr + " B_EXPR_END") == want


@pytest.mark.parametrize("expr,want", [
    ("const(-7) const(2) B_DIV", -3),          # C# truncates toward zero (Python's // would give -4)
    ("const(-7) const(3) B_REM", -1),          # the sign of the dividend
    ("const(7) const(0) B_DIV", 7),            # a zero divisor pushes the numerator
    ("const(7) const(0) B_REM", 7),
    ("const4(33554431) const4(33554431) B_PLUS", -2),       # wraps, never raises
    ("const4(-33554432) const(1) B_MINUS", 33554431),
])
def test_the_interpreter_follows_the_engine_source(expr, want):
    assert Engine().eval(expr + " B_EXPR_END") == want
