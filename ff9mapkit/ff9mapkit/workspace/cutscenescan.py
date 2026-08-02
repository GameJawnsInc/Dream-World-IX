"""Offline STAGING checks for a cutscene — the Qt-free lane behind the Cutscene tab's
"Check the staging" button (the twin of :mod:`behaviorscan` for the behavior tab).

THE DEFECT THIS EXISTS TO CLOSE. :func:`ff9mapkit.build._validate_cutscene_movement` already
writes exactly the sentence a scene author needs — *"the actor presses into the wall and the
scene hangs"* — but it is reached only through ``_validate_content_placement``, which only
``lint`` / ``walkmesh verify`` call. The Workspace's Check runs ``validate`` + ``lint_logic``,
neither of which touches it, so **no GUI call site could reach it even in principle**. A
correct mechanism that no call site spends is this project's most-repeated defect.

Nothing here re-derives the geometry: it drives the BUILD'S OWN checker over the open
document, so what the panel says is what ``ff9mapkit lint`` says. The one disk read (the
walkmesh) is shared with the behavior lane's loader.

TWO TRUTHS, and the caller must say so on its face: the **mesh** comes from the SAVED file,
the **steps** from the open document. Editing steps never changes the mesh, so the split is
honest — but a just-reshaped, unsaved walkmesh is not what this checked.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field

from ..editor import forms as _forms
from . import behaviorscan as _bscan

# ONE disk read, shared with the behavior lane -- both want the field's own [walkmesh]
# bgi/reference when it ships one, else the resolved built mesh (build.behavior_walkmesh).
load_walkmesh = _bscan.load_walkmesh


@dataclass
class StagingResult:
    """What the panel paints. ``error`` set => the check could not run at all."""
    error: str = ""
    warnings: list = field(default_factory=list)   # the build's own sentences, verbatim
    scenes: int = 0                                # how many [[cutscene]] blocks were considered
    cast_scenes: int = 0                           # ...of which have a cast (only those move)
    skipped: list = field(default_factory=list)    # (scene label, why) the checker could NOT walk

    def summary(self) -> str:
        if self.error:
            return self.error
        if not self.cast_scenes:
            return ("No cast scene to stage — a narration cutscene (no `actors`) has no movement "
                    "to check.")
        scope = ("1 scene" if self.cast_scenes == 1 else f"{self.cast_scenes} scenes")
        bits = []
        if self.warnings:
            n = len(self.warnings)
            bits.append(f"⚠ {n} staging problem{'' if n == 1 else 's'}")
        # NEVER a bare tick over work that was not done. `_validate_cutscene_movement` SKIPS a scene
        # whose names it cannot resolve (a typo'd marker, an unknown gesture) -- silently, via
        # `except ValueError: continue`. Reporting "every walk reaches its target" for a scene nobody
        # walked is the false green this panel exists to prevent.
        if self.skipped:
            bits.append(f"{len(self.skipped)} scene{'' if len(self.skipped) == 1 else 's'} "
                        f"NOT checked (unresolved names — run Check)")
        if bits:
            return " · ".join(bits) + f" across {scope}."
        return f"✓ Every walk in {scope} reaches its target."


def has_cast_scene(raw: dict) -> bool:
    """Is there anything for the staging check to do? Only a scene with a cast MOVES anyone."""
    return any(b.get("actors") for b in _forms.all_blocks((raw or {}).get("cutscene")))


def check_staging(raw: dict, base_dir, wmesh) -> StagingResult:
    """Run the build's own walk-stall check over the open document. Worker material — pure, no Qt,
    no disk (pass ``wmesh`` from :func:`load_walkmesh`). Never raises: a half-typed scene is the
    normal case here, and an unresolved name is already ``validate()``'s job to report."""
    from .. import build as _build
    blocks = _forms.all_blocks((raw or {}).get("cutscene"))
    res = StagingResult(scenes=len(blocks),
                        cast_scenes=sum(1 for b in blocks if b.get("actors")))
    if wmesh is None:
        res.error = "No walkmesh resolved — save the field first, then check the staging."
        return res
    if not res.cast_scenes:
        return res
    warnings: list = []
    try:
        # deepcopy: the checker resolves names/animations against the project and must never
        # mutate (or race) the dict the GUI is editing.
        project = _build.FieldProject(copy.deepcopy(raw), base_dir)
        res.skipped = _unwalkable(project, wmesh, blocks)
        _build._validate_cutscene_movement(project, wmesh, warnings)
    except Exception as e:                 # noqa: BLE001 -- the message is the teaching
        res.error = f"Could not check the staging — {e}"
        return res
    res.warnings = warnings
    return res


def _unwalkable(project, wmesh, blocks) -> list:
    """Which cast scenes ``_validate_cutscene_movement`` will SILENTLY SKIP, and why.

    It resolves each scene's steps and does ``except ValueError: continue`` — correct (``validate()``
    owns those messages) but invisible: a scene with one typo'd marker contributes no warnings and is
    indistinguishable from a clean one. We run the same resolution first so the panel can say a scene
    went unchecked instead of implying it passed."""
    from .. import build as _build
    out = []
    for k, b in enumerate(blocks):
        cast = [str(a) for a in (b.get("actors") or [])]
        if not cast:
            continue
        lbl = "[cutscene]" if len(blocks) == 1 else f"[cutscene] #{k}"
        try:
            _build._resolve_conductor_steps(b.get("steps", []), project, cast=cast,
                                            walkmesh=wmesh, beat=_build._scene_beat(b))
        except ValueError as e:
            out.append((lbl, str(e)))
        except Exception:                  # noqa: BLE001 -- never let the probe break the check
            pass
    return out
