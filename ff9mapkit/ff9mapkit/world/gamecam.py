"""THE GAME'S OWN WORLD CAMERA, decoded: the free-roam chase camera ``ff9.w_cameraUpdate`` drives, as the settled pose
it converges to, in the kit's ``render`` camera dict (``kind``, ``eye``, ``at``, ``fov``), so the 3D view and
``world-render`` can frame the world as the game sees it.

The source is Memoria's ``Assembly-CSharp/Global/ff9/ff9.cs`` (the version-matched clone): ``w_cameraSystemConstructor``
(the posstat conversion), ``w_cameraChangeUpdate`` / ``w_cameraGetPosstat`` / ``w_cameraGetHeightParam`` (which posstat,
blended by the player's altitude and the camera's tilt), ``w_cameraUpdate`` (the field of view and the eye offset)
and ``w_cameraSetEyeAim`` (the aim on the player, the eye lifted over the terrain). The tables are its literals,
verbatim. Only the camera's runtime state is not in the source: its yaw (``rotation``, degrees) and tilt
(``upperCounter``, 0..4096), which the harness publishes as ``cam_rot`` / ``cam_upper``.

THE SETTLED POSE AND ITS ONE SLACK. The eye's x and z follow the player exactly every frame. Its height and the aim's
height EASE toward their targets and stop inside a deadband: the eye within 1u of its target, the aim within 0.5u
(``w_cameraSetEyeAim``'s ``num17`` and its 0.5 test). So a pose rebuilt from the player's position and the camera's
yaw is exact in plan and good to those bands in height; ``eye_dy`` / ``aim_dy`` carry a measured residual.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

#: ``ff9.w_cameraPosstat``, raw (PSX fixed point; :func:`posstat` converts as the constructor does)
POSSTAT_RAW = (
    # cameraPers, cameraDistance, cameraHeight, cameraCorrect, aimHeight
    (320.0, 5000.0, -2200.0, -3000.0, -1000.0),     # 0  on foot, low
    (350.0, 6000.0, -3200.0, -3000.0, -1200.0),     # 1  (the constructor's first pose)
    (350.0, 5500.0, -2400.0, -3000.0, -500.0),      # 2  on foot, high ground
    (350.0, 7000.0, -4400.0, -500.0, -1500.0),      # 3
    (320.0, 6750.0, -400.0, -3600.0, 0.0),          # 4
    (320.0, 6750.0, -400.0, -3400.0, 0.0),          # 5
    (320.0, 6750.0, -400.0, -3600.0, 0.0),          # 6
    (350.0, 4000.0, -7500.0, -3000.0, -1200.0),     # 7  the tilted-up ("fly") pose
    (320.0, 5000.0, -400.0, -3500.0, 0.0),          # 8
    (380.0, 7000.0, -2200.0, -2400.0, -1500.0),     # 9
)

#: ``ff9.w_cameraElement[type_cam, place]`` = (down, up, fly) posstat indices
ELEMENT = (
    ((0, 2, 7), (3, 2, 7), (1, 2, 7)),              # 0 on foot
    ((1, 2, 7), (3, 2, 7), (1, 2, 7)),              # 1
    ((9, 2, 7), (9, 2, 7), (9, 2, 7)),              # 2
    ((6, 6, 6), (5, 5, 5), (4, 4, 4)),              # 3
    ((8, 8, 8), (8, 8, 8), (8, 8, 8)),              # 4
)

#: ``ff9.w_cameraArea2Place``: a cell's AREA (0..63, ``w_frameGetParameter(192)``) -> the camera's place
AREA2PLACE = (0,) * 27 + (2,) * 13 + (1,) * 6 + (0,) * 5 + (2,) * 13

TWEAK_EYE_Y = 558 / 256.0          # ``ff9.tweaker.w_cameraWorldEye_Y`` * 1/256 (w_tweakSomeValues: every status)
TWEAK_AIM_Y = 312 / 256.0          # ``ff9.tweaker.w_cameraWorldAim_Y`` * 1/256
FUZZY = 5.5                        # the eye's terrain probe: four samples this far round it (w_cameraFuzzy)
TERRAIN_CAP = 37.1                 # ... the probe's height is capped here on foot (33.2 flying)
EYE_BAND, AIM_BAND = 1.0, 0.5      # the settle deadbands (module docstring)


@dataclass(frozen=True)
class Settings:
    """Memoria.ini ``[Worldmap]``: the user's own camera settings (percent, and the field of view in degrees)."""
    field_of_view: float = 44.0
    camera_distance: float = 100.0
    camera_height: float = 100.0
    camera_aim_height: float = 100.0

    @classmethod
    def from_ini(cls, text: str) -> "Settings":
        """Read ``[Worldmap]`` from a Memoria.ini's text; a missing key keeps Memoria's default."""
        keys = {"FieldOfView": "field_of_view", "CameraDistance": "camera_distance", "CameraHeight": "camera_height",
                "CameraAimHeight": "camera_aim_height"}
        out, section = {}, None
        for line in text.splitlines():
            s = line.split(";", 1)[0].strip()
            if s.startswith("[") and s.endswith("]"):
                section = s[1:-1].strip()
            elif section == "Worldmap" and "=" in s:
                k, v = (p.strip() for p in s.split("=", 1))
                if k in keys:
                    try:
                        out[keys[k]] = float(v)
                    except ValueError:
                        pass
        return cls(**out)

    @classmethod
    def from_game(cls, game) -> "Settings":
        from pathlib import Path
        ini = Path(game) / "Memoria.ini"
        return cls.from_ini(ini.read_text(encoding="utf-8", errors="ignore")) if ini.is_file() else cls()


def posstat(i: int) -> tuple:
    """Posstat ``i`` converted as ``w_cameraSystemConstructor`` does: ``(pers, distance, height, correct, aim)`` in
    world units (pers unchanged; the heights flip sign: PSX's y ran down)."""
    p, d, h, c, a = POSSTAT_RAW[i]
    return (p, d / 256.0, -h / 256.0, -c / 256.0, -a / 256.0)


def height_param(y: float) -> int:
    """``w_cameraGetHeightParam``: the player's altitude as a 0..4096 blend."""
    h = int(y * 256.0)
    h = (h + 1000) * 4096
    h = int(h / 4500) if h >= 0 else -int(-h / 4500)          # C#'s integer division truncates toward zero
    return max(0, min(4096, h))


def tilt_param(upper_counter: int) -> int:
    """``rsin(upperCounter / 4)`` (the fixed-point sine ``w_cameraChangeUpdate`` passes as the tilt blend)."""
    deg = (int(upper_counter) // 4) / 4096.0 * 360.0
    return int(math.sin(math.radians(deg)) * 4096.0)


def _lerp(a, b, t: int):
    f = t / 4096.0
    return tuple(x + (y - x) * f for x, y in zip(a, b))


def blend(y: float, *, area: int = 14, type_cam: int = 0, upper_counter: int = 0) -> tuple:
    """``w_cameraGetPosstat`` at rest: down -> up by the player's altitude, then -> fly by the tilt."""
    down, up, fly = ELEMENT[type_cam][AREA2PLACE[int(area) & 63]]
    base = _lerp(posstat(down), posstat(up), height_param(y))
    return _lerp(base, posstat(fly), tilt_param(upper_counter))


def fov(pers: float, s: Settings, *, type_cam: int = 0) -> float:
    """``w_cameraUpdate``'s vertical field of view (degrees): ``pers / 8`` (9.5 for the Blue Narciss) scaled by the
    user's FieldOfView over 44. (Flight, and the chocobo over forest, take FieldOfView itself: not decoded here.)"""
    return pers / (9.5 if type_cam == 2 else 8.0) * (s.field_of_view / 44.0)


def pose(player, rotation: float, *, settings: Settings = Settings(), area: int = 14, type_cam: int = 0,
         upper_counter: int = 0, ground=None, eye_dy: float = 0.0, aim_dy: float = 0.0) -> dict:
    """The settled chase-camera pose for the party at ``player`` ``(x, y, z)`` with the camera's yaw ``rotation``
    (``cam_rot``, degrees): a ``render`` camera dict, plus the decode's own numbers under ``"game"``.

    ``ground(x, z)`` is the terrain's height there (None off any ground): the eye is lifted to ``correct`` above the
    highest of its four probes when that is above its own height. ``eye_dy`` / ``aim_dy`` move the eye / aim inside
    their settle bands (``EYE_BAND`` / ``AIM_BAND``)."""
    px, py, pz = (float(v) for v in player)
    pers, dist, height, correct, aim = blend(py, area=area, type_cam=type_cam, upper_counter=upper_counter)
    aim_off = aim * s_pct(settings.camera_aim_height)
    ex = px + math.sin(math.radians(rotation)) * dist * s_pct(settings.camera_distance)
    ez = pz + math.cos(math.radians(rotation)) * dist * s_pct(settings.camera_distance)
    ey = py + height * s_pct(settings.camera_height)
    lifted = 0.0
    if ground is not None:
        dx, dz = px - ex, pz - ez
        n = math.hypot(dx, dz) or 1.0
        cx, cz = ex + dx / n / 4.0, ez + dz / n / 4.0          # ``w_cameraDirVector / 4``: a quarter unit toward him
        hs = [ground(cx + FUZZY, cz), ground(cx - FUZZY, cz), ground(cx, cz + FUZZY), ground(cx, cz - FUZZY)]
        hs = [h for h in hs if h is not None]
        if hs:
            h = min(max(hs), TERRAIN_CAP)
            if correct + h > ey:
                lifted = correct + h - ey
                ey = correct + h
    eye = (ex, ey + eye_dy + TWEAK_EYE_Y, ez)
    at = (px, py + aim_off + aim_dy + TWEAK_AIM_Y, pz)
    return {"kind": "persp", "eye": eye, "at": at, "fov": fov(pers, settings, type_cam=type_cam),
            "game": {"pers": pers, "distance": dist, "height": height, "correct": correct, "aim": aim,
                     "lifted": lifted, "rotation": float(rotation), "upper_counter": int(upper_counter)}}


def s_pct(v: float) -> float:
    return float(v) / 100.0
