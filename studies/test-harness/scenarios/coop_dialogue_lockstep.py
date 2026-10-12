"""RETIRED -- superseded by coop_dialogue_authority.py (F3.2 C2, memoria-patch s96).

This was the F3 dialogue-lockstep acceptance test (s84: 40/40 on 2026-09-04, run
`.harness-runs/20260904-170049-coop_dialogue_lockstep`, recorded in studies/field-coop/F1-BUILD.md). It
encoded the F3 CONTRACT, which F3.2 deleted on purpose (studies/field-coop/F3.2-DESIGN.md):

  * B5 held an unmatched frame for DialogWaitMs (8 s), then handed the line back to the guest ('timed out --
    local advance restored'). F3.2 never hands a locked line back on a timer: the event ages out, and the
    line waits for host state (the orphan rule, the link dead, the panic unlock).
  * The lockstep engaged only under `l1`, on a MATCHED frame. F3.2 locks a line from the frame it opens.
  * The L1 pin and snap checks. F3.2 C1 (s95) deleted both (THE L1 LAW).
  * The netsync keys it read (`pending`, `wait_armed`, `wait_ms`, `wait_limit_ms`, `align_win`,
    `applied_seq`) are pinned to their "nothing" values by the F3.2 agent.

Against an F3.2 engine its assertions fail by design, and against the old one they pass: the opposite of a
calibration. Its benches live on, rewritten for the new contract:
B1 -> A1, B2 -> A2, B2b -> A2b, B5 -> A3 (no hand-back), L1 -> coop_talk_relay.py T1, RESET -> RESET.

The file is kept, not deleted, because the F3 build records name it. Loading it refuses with a HarnessError
BEFORE play.py launches a game. In a suite the refusal is that member's error verdict. A SystemExit would get
past the suite's `except Exception` and end the whole run.

    py tools/play.py studies/test-harness/scenarios/coop_dialogue_authority.py --field 30801
"""
try:                                     # play.py puts tools/ on sys.path before it loads a scenario
    from harness import HarnessError
except ImportError:                      # pragma: no cover - imported outside the driver
    HarnessError = RuntimeError          # HarnessError IS a RuntimeError

SUPERSEDED_BY = "studies/test-harness/scenarios/coop_dialogue_authority.py"

raise HarnessError(
    "coop_dialogue_lockstep.py is RETIRED: it tested the F3 lockstep contract (the 8 s 'local advance "
    "restored' hand-back, the L1 pin), which F3.2 deleted on purpose. Run " + SUPERSEDED_BY + " (F3.2 C2) "
    "instead -- see that file's docstring for the bench-by-bench mapping."
)
