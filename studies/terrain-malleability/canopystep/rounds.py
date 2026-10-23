"""The canopy-step rounds: one config per donor, picked by $CANOPY_DONOR (default comp26, round 22, so its scripts rerun
unchanged). Every lab script of this lane reads its island, donor, ground, carve points and lab folder from here.

  comp26  round 22: a desert crag with its scrub canopy (topo 38) -- in game, owner-passed, catalogued (desert-scrub)
  comp10  round 23: a grass massif with its forest canopy (topo 37), donor rect 14-16,14 (the canopy runs into block
          16,14); carries once the down gate keeps its two stock near-vertical walls (mountaindonors/STEP.md round 2)
"""
from __future__ import annotations

import os
from pathlib import Path

HERE = Path(__file__).resolve().parent

ROUNDS = {
    "comp26": {
        "round": 22, "label": "canopy-step", "out": "lab", "ground": "desert", "ground_topo": 17, "canopy_topo": 38,
        "island": ["--ground", "desert", "--center", "1380,-100", "--radius", "55", "--lobes", "1", "--patches", "0",
                   "--seed", "42"],
        "near": (1380.0, -100.0), "variants": {"A": 0, "B": 90, "C": 200, "D": 270},
        "what": "comp26 with its scrub canopy on a desert island",
    },
    "comp10": {
        "round": 23, "label": "canopy-step-comp10", "out": "lab_comp10", "ground": "grass", "ground_topo": 0,
        "canopy_topo": 37,
        "island": ["--ground", "grass", "--center", "1380,-96", "--radius", "66", "--lobes", "1", "--patches", "0",
                   "--seed", "42"],
        "near": (1380.0, -96.0), "variants": {"A": 0, "B": 90, "C": 200, "D": 270},
        "what": "comp10 with its forest canopy on a grass island",
    },
}
NAME = os.environ.get("CANOPY_DONOR", "comp26")
if NAME not in ROUNDS:
    raise SystemExit(f"CANOPY_DONOR={NAME!r}: not one of {sorted(ROUNDS)}")
R = ROUNDS[NAME]
LAB = HERE / "out" / R["out"]
