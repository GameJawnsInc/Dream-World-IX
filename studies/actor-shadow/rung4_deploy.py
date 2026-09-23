"""Deploy rung 4's bench (rung4_variants.py) as ON, INIT-ONLY or CONTROL -- the SAME toml, built three ways.

    py studies/actor-shadow/rung4_deploy.py on|init-only|control --id N --name SHD4F --text-block N

on         this change: on the MCF field every `shadow = false` actor gets stock's DisableShadow, the save act's
           landings keep it off, and the player re-disables it before the RETURN of its jump arc
init-only  on, minus the player's post-jump re-disable (its Init op stays) -- the instrument's negative
           control: the engine's FinishJump must bring the player's shadow back after the landing
control    the pre-change calls, byte-identical to a HEAD build: on an MCF field every injector got no
           `shadow` value and no `mcf`, the act kept its EnableShadow, the player got nothing
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "ff9mapkit"))
from ff9mapkit.content import chest as _chest, npc as _npc, savepoint as _sp, shadow as _shadow  # noqa: E402
from ff9mapkit.eb import edit, opcodes  # noqa: E402

TOML = HERE / "imported" / "rung4" / "shadow_off.field.toml"


def _pre_change(real):
    """``real`` called as the build called it before this change: on an MCF field (``mcf=True``) no value."""
    def call(*a, **kw):
        if kw.pop("mcf", False):
            kw["shadow"] = None
        return real(*a, **kw)
    return call


def _init_only(data):
    pe, rel = _shadow._player_anchor(data)
    return edit.insert_in_function(data, pe, 0, rel, opcodes.encode(_shadow.DISABLE_SHADOW))


def apply(variant: str) -> None:
    """Patch the kit in-process for ``variant`` (also used by the offline byte comparison)."""
    if variant == "init-only":
        _shadow.keep_player_shadow_off = _init_only
    elif variant == "control":
        _npc.inject_npc = _pre_change(_npc.inject_npc)
        _chest.inject_chest = _pre_change(_chest.inject_chest)
        _sp.inject_barrel_pop_reveal = _pre_change(_sp.inject_barrel_pop_reveal)
        real_act = _sp.act_save_body
        _sp.act_save_body = lambda **kw: real_act(**{**kw, "keep_shadow_off": False})
        _shadow.keep_player_shadow_off = lambda data: data
    elif variant != "on":
        raise SystemExit(__doc__)


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    apply(sys.argv[1])
    sys.argv = [str(REPO / "tools" / "deploy_field.py"), str(TOML), *sys.argv[2:]]
    runpy.run_path(sys.argv[0], run_name="__main__")


if __name__ == "__main__":
    main()
