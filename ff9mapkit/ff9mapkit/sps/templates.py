"""Curated named SPS effect TEMPLATES -- the friendly starting points for the Tier-2 creator (``[[sps]]
template = "fire"``). Each template is a ``copy_from`` preset pointing at a known-good donor effect in a
common, always-present field (the Ice Cavern, disc 1), so it reuses the proven Route-A path (clone a real
effect's texture + colours + animation, then optionally re-author the geometry). No new art, no DLL.

Picked from an offline preview survey of the donor effects (distinct, recognisable types). The registry is
just identifiers (field token + sps id) -- the bytes are read from the user's install at build time, like
``copy_from``; nothing here is Square-Enix data. Browsable (``list_templates``) so the CLI + a future GUI
creator picker read the same set. Extend freely -- add a row pointing at any donor effect.
-> [[project-ff9-sps-authoring]], docs/SPS.md.
"""
from __future__ import annotations

from dataclasses import dataclass

# common donor fields (Ice Cavern, disc 1 -- every install has them)
_ICCV_JMP = "fbg_n05_iccv_map088_ic_jmp_0"
_ICCV_BRI = "fbg_n05_iccv_map089_ic_bri_0"


@dataclass(frozen=True)
class Template:
    description: str
    field: str          # donor field token (what copy_from / extract takes)
    sps: int            # donor effect id to clone


# name -> Template. `[[sps]] template = "<name>"` resolves to copy_from {field, sps}.
TEMPLATES: dict[str, Template] = {
    "fire":    Template("a small flickering red flame", _ICCV_JMP, 2266),   # the in-game-proven melt-fire
    "bonfire": Template("a large orange flame", _ICCV_BRI, 2272),
    "smoke":   Template("a soft white smoke / mist cloud", _ICCV_JMP, 231),
    "sparkle": Template("twinkling gold sparkle motes", _ICCV_JMP, 180),
    "embers":  Template("scattered drifting orange embers", _ICCV_BRI, 2273),
    "glimmer": Template("a soft crystalline glint", _ICCV_BRI, 344),
}


def resolve(name: str):
    """The :class:`Template` for ``name`` (raises ``KeyError`` if unknown -- the caller maps it to its
    own error type with the known-names hint)."""
    return TEMPLATES[name]


def list_templates() -> list[tuple[str, str, str, int]]:
    """``[(name, description, donor_field, donor_sps), ...]`` -- for the CLI / GUI picker."""
    return [(n, t.description, t.field, t.sps) for n, t in TEMPLATES.items()]
