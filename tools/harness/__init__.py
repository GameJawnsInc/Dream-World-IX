"""The FF9 test harness -- drive a real running game from Python and assert on what it does.

The long-standing hard constraint on this project was "I cannot play the game": a change could be
built, deployed and screenshotted, but not *exercised*, so every behavioural claim cost a human
playtest. This package plus memoria-patch s83 closes that loop.

Two halves:

* ``Memoria/Harness/HarnessAgent.cs`` (engine, s83) -- injects virtual controller input at
  ``HonoInputManager``, publishes per-frame state, captures frames from inside the renderer.
* this package -- owns the process, sends steps, waits on state, records checks.

Read ``ff9mapkit/docs/TEST_HARNESS.md`` for the guide; ``tools/play.py`` is the CLI entry point.
"""
from .channel import BUTTONS, PROTOCOL, Channel, HarnessError, State
from .session import Session, ff9_pids
from .suite import Scenario, SuiteRunner, load_manifest

__all__ = ["Session", "State", "Channel", "HarnessError", "BUTTONS", "PROTOCOL", "ff9_pids",
           "SuiteRunner", "Scenario", "load_manifest"]
