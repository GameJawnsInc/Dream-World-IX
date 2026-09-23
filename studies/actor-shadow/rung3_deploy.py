"""Deploy rung 3's bench (rung3_variants.py) as ON or CONTROL -- the SAME toml, built two ways.

    py studies/actor-shadow/rung3_deploy.py on|control --id N

on       tools/deploy_field.py as it is: on this MCF field the stock-dark cactus and the held cup get stock's
         DisableShadow (content.prop.inject_prop mcf=True)
control  the same deploy through the pre-fix call: on an MCF field inject_prop got neither `mcf` nor a
         `shadow` value, so both are dropped (dropping only `mcf` would cast census ops on the casting props,
         bytes no build ever shipped). The two builds differ by exactly those two DisableShadow ops.
         A held prop has no toml switch that restores the old bytes, so the control is made in code.
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "ff9mapkit"))
from ff9mapkit.content import prop as _prop  # noqa: E402

TOML = HERE / "imported" / "rung3" / "set_pieces_mcf.field.toml"


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in ("on", "control"):
        raise SystemExit(__doc__)
    variant, rest = sys.argv[1], sys.argv[2:]
    if variant == "control":
        real = _prop.inject_prop

        def pre_fix(*a, **kw):
            if kw.pop("mcf", False):       # an MCF field: the pre-fix build passed no shadow value at all
                kw["shadow"] = None
            return real(*a, **kw)

        _prop.inject_prop = pre_fix
    sys.argv = [str(REPO / "tools" / "deploy_field.py"), str(TOML), *rest]
    runpy.run_path(sys.argv[0], run_name="__main__")


if __name__ == "__main__":
    main()
