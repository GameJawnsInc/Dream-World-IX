"""The game's world-map fog, as the editor's "as the game sees it" view draws it (overworld editor rung C18).

MEASURED, NOT DERIVED. Memoria's world map layers two fogs (``ff9.cs``'s weather update): the world shaders' own
linear fog (``_FogStartDistance`` / ``_FogEndDistance``) and Unity's GlobalFog image effect with a height mist in the
Mist years (``w_frameFog == 1``: height 29, density ``MistDensity``), their distances from Memoria.ini ``[Worldmap]``.
The compiled shaders are not in Memoria's source, so the equation is not read: it is fitted from C7's nine in-game
stills (``studies/overworld-editor/c18_fog_fit.py``) -- each still's decoded camera drawn with its depth, the near
pixels giving the game's lighting, the far ones the haze, the fraction between them binned by depth and height:

* linear in VIEW DEPTH (along the view, not the ray: it fits better), from ``START`` to an end that grows with the
  point's height -- low ground is full of fog by 61u, a peak 20u up only by 116u: the Mist is a ground fog, the
  highlands stand out of it;
* the colour is the weather table's ``fogDW`` (``WeatherColors.csv``, which Memoria reads; the stills were taken in
  "Daylight 0", (205, 217, 247), and so is the default), and the engine clears the sky to it.

The numbers were measured at this install's ``[Worldmap]`` (MistStartDistance 25, MistEndDistance 250, MistDensity
15, MistStartDistance_base 40) in the Mist years, on foot; held out one spot at a time they score 0.051-0.066 (fog
fraction rmse) on the spot left out, against 0.71-0.83 with no fog. Another install's Mist settings would fog
differently, and :meth:`Fog.note` says so where the view shows it.

THE TWO YEARS. Mist is not position-keyed (Memoria's ``WorldConfiguration.UseMist``): it follows the scenario counter,
on before the Exterior Continent (5990) and after disc 4 (11090). In between the fog is the shaders' linear one at the
ini's ``FogStartDistance`` / ``FogEndDistance`` (``RenderSettings``; Memoria's own default 250 / 350 for a key the ini
leaves out) -- C8's stills, taken there, show no fog inside 250u at this install's 400 / 490, and the mist model on
them is worse than none.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

#: fog fraction = clamp((depth - START) / (end(y) - START), 0, 1), end(y) = END + PER_U * max(0, y - FLOOR)
START, END, PER_U, FLOOR = 15.0, 61.0, 2.75, 0.0
FOG_RGB = (205, 217, 247)                                       # "Daylight 0"'s fogDW, as the stills measured it
MEASURED_AT = ("Mist years, on foot, Daylight 0; Memoria.ini [Worldmap] MistStartDistance 25, MistEndDistance 250, "
               "MistDensity 15, MistStartDistance_base 40")
#: the weather table rows Memoria loads (Data/World/WeatherColors.csv); the editor draws daylight
WEATHER_CSV = Path("StreamingAssets") / "Data" / "World" / "WeatherColors.csv"
DAYLIGHT = 0


#: the [Worldmap] Mist settings the model was measured at (gamecam.Settings' names)
MEASURED_MIST = {"mist_start": 25.0, "mist_end": 250.0, "mist_density": 15.0, "mist_base": 40.0}


@dataclass(frozen=True)
class Fog:
    """The fog the view draws: its ramp (``start`` to ``end`` + ``per_u`` per unit of height above ``floor``) and
    colour (0..255). ``mist`` names the year; ``unmeasured`` lists the install's Mist settings that differ from the
    ones measured."""
    start: float = START
    end: float = END
    per_u: float = PER_U
    floor: float = FLOOR
    rgb: tuple = FOG_RGB
    mist: bool = True
    unmeasured: tuple = ()

    def note(self) -> str:
        """The fog in words, for the view's tooltip: which year, where its numbers come from."""
        if not self.mist:
            return (f"The fog of the years without mist: from {self.start:g}u to {self.end:g}u, this install's "
                    "Memoria.ini [Worldmap] FogStartDistance / FogEndDistance (Memoria's own default where it leaves "
                    "one out).")
        out = ("The Mist, as measured from the game's own frames (depth 15u to 61u, longer over high ground: the "
               "highlands stand out of it), in the daylight fog colour.")
        if self.unmeasured:
            out += (" This install's Mist settings differ from the ones it was measured at ("
                    + ", ".join(self.unmeasured) + "), so the game's mist may reach farther or nearer.")
        return out

    def factor(self, depth, y):
        """The fog fraction for points at view ``depth`` and world height ``y`` (scalars or numpy arrays)."""
        import numpy as np
        end = self.end + self.per_u * np.maximum(0.0, np.asarray(y, dtype=float) - self.floor)
        return np.clip((np.asarray(depth, dtype=float) - self.start) / np.maximum(end - self.start, 1e-6), 0.0, 1.0)

    def apply(self, rgb, depth, y):
        """``rgb`` (..., 3, 0..255) fogged: blended toward the fog colour by :meth:`factor` (inf depth at a finite
        height is all fog; :func:`fog_still` gives the sky the floor's height)."""
        import numpy as np
        f = self.factor(np.where(np.isfinite(depth), depth, 1e9), y)[..., None]
        return np.asarray(rgb, dtype=float) * (1.0 - f) + np.asarray(self.rgb, dtype=float) * f


def fog_still(img, depth, view, fog: Fog):
    """A ``render.raster`` still (and its ``want_depth`` buffer) fogged as the 3D view's shader fogs the same view:
    each pixel's world height from its ray, the sky (inf depth) all fog. The software twin of the GPU's fog."""
    import math

    import numpy as np
    H, W = depth.shape
    eye = np.asarray(view["eye"], dtype=np.float64)
    fwd = np.asarray(view["at"], dtype=np.float64) - eye
    fwd /= np.linalg.norm(fwd)
    right = np.cross([0.0, 1.0, 0.0], fwd)
    right /= np.linalg.norm(right)
    up = np.cross(fwd, right)
    fpx = (H / 2.0) / math.tan(math.radians(view["fov"]) / 2.0)
    yy, xx = np.mgrid[0:H, 0:W]
    ray_y = fwd[1] + ((xx + 0.5 - W / 2.0) / fpx) * right[1] - ((yy + 0.5 - H / 2.0) / fpx) * up[1]
    sky = ~np.isfinite(depth)
    d = np.where(sky, 1e9, depth)
    y = np.where(sky, fog.floor, eye[1] + d * ray_y)          # the sky is the fog's colour, whatever its ray's height
    return np.rint(fog.apply(img, d, y)).clip(0, 255).astype(np.uint8)   # rounded, as GL does


def weather_rgb(game, row: int = DAYLIGHT):
    """``fogDW`` of the weather table's ``row`` in the ``WeatherColors.csv`` the game reads (the stack's first, then
    the base game's: ``gamecam.world_csv``, as Memoria's GetCsvWithHighestPriority), or None when it cannot be read."""
    from .gamecam import world_csv
    try:
        lines = world_csv(game, WEATHER_CSV).read_text(encoding="utf-8").splitlines()
    except (OSError, TypeError, AttributeError):
        return None
    rows = [ln for ln in lines if ln.strip() and not ln.lstrip().startswith("#")]
    if not 0 <= row < len(rows):
        return None
    cols = rows[row].split(";")
    try:
        return tuple(max(0, min(255, int(cols[i]))) for i in (25, 26, 27))   # fogDW.vx, .vy, .vz
    except (IndexError, ValueError):
        return None


def from_game(game, *, mist: bool = True) -> Fog:
    """The fog of the Mist years (``mist``, measured) or the years without (the ini's linear fog), in the install's own
    daylight fog colour (the measured colour when the table is missing)."""
    from .gamecam import Settings
    rgb = (weather_rgb(game) if game is not None else None) or FOG_RGB
    s = Settings.from_game(game) if game is not None else Settings()
    if not mist:
        return Fog(start=float(s.fog_start), end=max(float(s.fog_end), float(s.fog_start) + 1.0), per_u=0.0,
                   rgb=rgb, mist=False)
    names = {"mist_start": "MistStartDistance", "mist_end": "MistEndDistance", "mist_density": "MistDensity",
             "mist_base": "MistStartDistance_base"}
    differ = tuple(f"{names[k]} {getattr(s, k):g}" for k, v in MEASURED_MIST.items() if abs(getattr(s, k) - v) > 1e-6)
    return Fog(rgb=rgb, unmeasured=differ)
