"""THE GAME'S OWN WORLD CAMERA, decoded: the free-roam chase camera ``ff9.w_cameraUpdate`` drives, as the settled pose
it converges to, in the kit's ``render`` camera dict (``kind``, ``eye``, ``at``, ``fov``), so the 3D view and
``world-render`` can frame the world as the game sees it.

The source is Memoria's ``Assembly-CSharp/Global/ff9/ff9.cs`` (the version-matched clone): ``w_cameraSystemConstructor``
(the posstat conversion), ``w_cameraChangeUpdate`` / ``w_cameraGetPosstat`` / ``w_cameraGetHeightParam`` (which posstat,
blended by the player's altitude and the camera's tilt), ``w_cameraUpdate`` (the field of view and the eye offset)
and ``w_cameraSetEyeAim`` (the aim on the player, the eye lifted over the terrain). The tables are its literals,
verbatim. Only the camera's runtime state is not in the source: its yaw (``rotation``, degrees) and tilt
(``upperCounter``, 0..4096), which the harness publishes as ``cam_rot`` / ``cam_upper``.

THE VEHICLES (``TransportControls.csv``, read through the mod stack as Memoria reads it): each travel MODE
(``gEventGlobal[190]``: 0 on foot, 1-5 the ground chocobos, 6 the gold chocobo in the air, 7 the Blue Narciss, 8-9
the airships) names a movement ``type`` (0 ground, 1 flight, 2 boat) and a ``type_cam`` (the camera element's row).
Beyond the element, the vehicle changes four things, all decoded here:
  * the field of view: flight takes FieldOfView itself; the boat divides pers by 9.5 (not 8); a ground chocobo over
    forest (topographs 36-38) takes FieldOfView itself too;
  * the eye's floor: a flyer's eye never sits below 17.578125, and its terrain probe is capped at 33.2 (37.1 else);
  * the final Y nudges (``FixTypeCam``, on by default), scaled by CameraHeight / CameraAimHeight. They ease toward a
    TARGET that depends on how the vehicle was reached, not only on the vehicle (:func:`fix_target`, measured in game
    in C21): 558 / 312 on foot and on a chocobo, 320 / 701 on the boat and 1419 / 996 on an airship as a load leaves
    them, but a RunScriptSync hook keyed on the tag NUMBER (tag 19 -> 1419 / 996, tag 21 -> 558 / 312) lands on
    different events in different world scripts -- so the gold chocobo flies with 558 / 312 on disc 1 and 1419 / 996
    on disc 4, a Dead Pepper in the air raises it on disc 1, and the boat and the Hilda Garde III boarded on foot on
    disc 1 take 558 / 312;
  * nothing else at rest: the speed's FOV widening and the turn's roll both return to zero once the craft stops.

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
WALK_Y, BOAT_Y, RISEN_Y = (558, 312), (320, 701), (1419, 996)   # FixTypeCam's (eye, aim) nudges, raw /256
#: FixTypeCam's nudge TARGET as ``w_movementChange`` (RunWorldCode 1) leaves it, per ``type_cam``
#: (ff9.cs w_movementChange's tail). type_cam 4 -- the gold chocobo flying -- sets the nudge but NOT the target, so
#: the next ``w_cameraUpdate`` eases it straight back to the target already standing (the ground chocobo's).
FIX_ON_CHANGE = {0: WALK_Y, 1: WALK_Y, 2: BOAT_Y, 3: RISEN_Y}
FIX_TYPE_Y = {**FIX_ON_CHANGE, 4: WALK_Y}         # each type_cam's target as it is ordinarily reached (disc 1)
#: EventEngine.DoEventCode's RunScriptSync (REQEW) hook in world mode: these tags set the target, whatever the
#: function under them is
TAG_FIX = {19: RISEN_Y, 21: WALK_Y}
#: what each free-roam dispatcher runs under tags 19 / 21 -- the census of its own request blocks (C21.md, and the
#: install-gated test that re-derives it): ``takeoff`` (the gold chocobo's, [190] = 6), ``pepper`` (a Dead Pepper fed
#: in the air: the rise toward the Air Garden) and ``board`` (mode -> the tag its on-foot boarding runs after
#: RunWorldCode(1, mode)). WORLD08 / 09 number the chocobo's functions one higher than WORLD00-07: their take-off is
#: tag 19 and their pepper tag 20, which no hook reads.
DISPATCHER_TAGS = {9000: {"pepper": 19}, 9003: {"pepper": 19, "board": {7: 21}}, 9005: {"pepper": 19},
                   9007: {"pepper": 19, "board": {8: 21}}, 9008: {"takeoff": 19}, 9009: {"takeoff": 19}}
FIX_HOWS = ("boarded", "pepper", "loaded")
FLYER_EYE_FLOOR = 17.578125        # w_cameraSetEyeAim's ``num``: a flyer's eye never lower
FLYER_TERRAIN_CAP = 33.2
FOREST_TOPOS = (36, 37, 38)        # a ground chocobo over these takes FieldOfView itself

#: the stock ``TransportControls.csv`` rows: mode -> (type, type_cam), the fallback when no file is read
TRANSPORT = {0: (0, 0), 1: (0, 1), 2: (0, 1), 3: (0, 1), 4: (0, 1), 5: (0, 1), 6: (1, 4), 7: (2, 2), 8: (1, 3),
             9: (1, 3), 10: (3, 0), 11: (0, 0)}
MODE_NAMES = {0: "on foot", 1: "yellow chocobo", 2: "light blue chocobo", 3: "red chocobo", 4: "deep blue chocobo",
              5: "gold chocobo", 6: "gold chocobo, flying", 7: "Blue Narciss", 8: "Hilda Garde III",
              9: "Invincible"}


def world_csv(game, rel):
    """The data file at ``rel`` (under a folder root, e.g. ``StreamingAssets/Data/World/WeatherColors.csv``) the game
    reads: Memoria's ``AssetManager.GetCsvWithHighestPriority``, the first folder of the stack (Memoria.ini
    FolderNames) that has it, then the base game. None when no root has it (or the stack cannot be read)."""
    from pathlib import Path
    if game is None:
        return None
    try:
        from .render import game_stack
        roots = list(game_stack(game) or ()) + [Path(game)]
    except Exception:                                       # noqa: BLE001 -- unknown: the caller's safe answer
        return None
    return next((Path(r) / rel for r in roots if (Path(r) / rel).is_file()), None)


def csv_text(path) -> str:
    """A data file's text as Memoria's CsvReader reads it (a .NET StreamReader): a byte-order mark detected and
    stripped -- UTF-16 as Notepad's "Unicode" saves it, UTF-8 as Excel's "CSV UTF-8" -- else UTF-8, a bad byte
    replaced. A mod's file may be any of these (review of the C18 fixes: a kept mark read as a row)."""
    import codecs
    from pathlib import Path
    data = Path(path).read_bytes()
    utf16 = data.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE))
    return data.decode("utf-16" if utf16 else "utf-8-sig", errors="replace")


def transport_table(game=None) -> dict:
    """``mode -> (type, type_cam)`` from the ``TransportControls.csv`` the game reads (:func:`world_csv`). The stock
    rows when none can be read."""
    from pathlib import Path
    f = world_csv(game, Path("StreamingAssets") / "Data" / "World" / "TransportControls.csv")
    if f is None:
        return dict(TRANSPORT)
    rows = [ln.split(";") for ln in csv_text(f).splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    try:
        return {i: (int(r[0]), int(r[15])) for i, r in enumerate(rows)}
    except (ValueError, IndexError):
        return dict(TRANSPORT)
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
    # the fog's (world.fog, overworld editor C18): the defaults Memoria binds each key with (WorldmapSection's
    # BindInt32), which is what a key the ini leaves out runs at -- not the ini comment's "vanilla" numbers
    fog_start: float = 250.0                      # FogStartDistance / FogEndDistance: the no-mist years (u)
    fog_end: float = 350.0
    mist_start: float = 25.0                      # MistStartDistance / MistEndDistance / MistDensity /
    mist_end: float = 250.0                       # MistStartDistance_base: the Mist years
    mist_density: float = 15.0
    mist_base: float = 40.0

    @classmethod
    def from_ini(cls, text: str) -> "Settings":
        """Read ``[Worldmap]`` from a Memoria.ini's text; a missing key keeps Memoria's default."""
        keys = {"FieldOfView": "field_of_view", "CameraDistance": "camera_distance", "CameraHeight": "camera_height",
                "CameraAimHeight": "camera_aim_height", "FogStartDistance": "fog_start", "FogEndDistance": "fog_end",
                "MistStartDistance": "mist_start", "MistEndDistance": "mist_end", "MistDensity": "mist_density",
                "MistStartDistance_base": "mist_base"}
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


def fov(pers: float, s: Settings, *, type_cam: int = 0, move_type: int = 0, topograph: int | None = None) -> float:
    """``w_cameraUpdate``'s vertical field of view (degrees), at rest: ``pers / 8`` (9.5 for the Blue Narciss) scaled by
    the user's FieldOfView over 44; flight, and a ground chocobo over forest, take FieldOfView itself."""
    if move_type == 1 or (type_cam == 1 and topograph in FOREST_TOPOS):
        return float(s.field_of_view)
    return pers / (9.5 if type_cam == 2 else 8.0) * (s.field_of_view / 44.0)


def dispatcher_for(mode: int, disc: int = 1) -> int:
    """The free-roam dispatcher a vehicle is met in: disc 4 is WORLD08 (9008); on disc 1 the Blue Narciss sails in
    WORLD03 (9003) and everything else here is WORLD07's (9007: the Hilda Garde III, the gold chocobo)."""
    if int(disc) == 4:
        return 9008
    return 9003 if int(mode) == 7 else 9007


def fix_target(mode: int, *, how: str = "boarded", world: int | None = None, disc: int = 1, table=None) -> tuple:
    """FixTypeCam's (eye, aim) nudge target for travel ``mode`` in dispatcher ``world`` (default
    :func:`dispatcher_for` on ``disc``), reached ``how``:
      * ``boarded`` (the default): as play reaches it -- boarded on foot, or the gold chocobo taken off from the
        ground: the mode's own target, then whatever the world's boarding / take-off script's tag sets;
      * ``pepper``: the gold chocobo after a Dead Pepper fed in the air (mode 6 only);
      * ``loaded``: the dispatcher loaded with the mode already set (back from the airship's bridge, a battle's
        return, a save): ``w_movementChange``'s target alone.
    Measured in game (C21): disc 1 -- the gold chocobo flying 558 / 312, after a Dead Pepper 1419 / 996, the Hilda
    Garde III boarded 558 / 312 (loaded 1419 / 996, C8); the rest is the census read the same way."""
    if how not in FIX_HOWS:
        raise ValueError(f"how must be one of {FIX_HOWS}, not {how!r}")
    type_cam = (table or TRANSPORT).get(int(mode), TRANSPORT.get(int(mode), (0, 0)))[1]
    tags = DISPATCHER_TAGS.get(int(world) if world is not None else dispatcher_for(mode, disc), {})
    if type_cam == 4:                                    # the gold chocobo flying: the take-off sets no target itself
        if how == "loaded":
            return WALK_Y                                # not measured: the ground chocobo's target, as it stands
        target = TAG_FIX.get(tags.get("takeoff"), WALK_Y)
        if how == "pepper":
            target = TAG_FIX.get(tags.get("pepper"), target)
        return target
    if how == "pepper":
        raise ValueError("a Dead Pepper in the air is the flying gold chocobo's (mode 6) only")
    target = FIX_ON_CHANGE.get(type_cam, WALK_Y)
    if how == "boarded":
        target = TAG_FIX.get(tags.get("board", {}).get(int(mode)), target)
    return target


def pose(player, rotation: float, *, settings: Settings = Settings(), area: int = 14, type_cam: int = 0,
         upper_counter: int = 0, ground=None, eye_dy: float = 0.0, aim_dy: float = 0.0, move_type: int = 0,
         topograph: int | None = None, mode: int | None = None, table=None, how: str = "boarded",
         world: int | None = None, disc: int = 1, fix: tuple | None = None) -> dict:
    """The settled chase-camera pose for the party at ``player`` ``(x, y, z)`` with the camera's yaw ``rotation``
    (``cam_rot``, degrees): a ``render`` camera dict, plus the decode's own numbers under ``"game"``.

    ``ground(x, z)`` is the terrain's height there (None off any ground): the eye is lifted to ``correct`` above the
    highest of its four probes when that is above its own height. ``eye_dy`` / ``aim_dy`` move the eye / aim inside
    their settle bands (``EYE_BAND`` / ``AIM_BAND``).

    A vehicle: ``mode`` (gEventGlobal[190]) looks its ``type`` and ``type_cam`` up in ``table`` (:func:`transport_table`;
    the stock rows by default), or pass ``move_type`` / ``type_cam`` directly; ``topograph`` is the cell's under the
    party (a ground chocobo's forest field of view). The final Y nudges are :func:`fix_target`'s for ``mode``,
    ``how``, ``world`` / ``disc`` (``fix`` gives the (eye, aim) target outright; with no ``mode``, the type_cam's
    ordinary one)."""
    if mode is not None:
        move_type, type_cam = (table or TRANSPORT).get(int(mode), TRANSPORT.get(int(mode), (0, 0)))
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
            h = min(max(hs), FLYER_TERRAIN_CAP if move_type == 1 else TERRAIN_CAP)
            if correct + h > ey:
                lifted = correct + h - ey
                ey = correct + h
    if move_type == 1 and ey < FLYER_EYE_FLOOR:              # a flyer's eye never sits lower (w_cameraSetEyeAim)
        lifted += FLYER_EYE_FLOOR - ey
        ey = FLYER_EYE_FLOOR
    if fix is None:
        fix = (fix_target(mode, how=how, world=world, disc=disc, table=table) if mode is not None
               else FIX_TYPE_Y.get(type_cam, WALK_Y))
    ty_eye, ty_aim = fix
    eye = (ex, ey + eye_dy + ty_eye / 256.0 * s_pct(settings.camera_height), ez)
    at = (px, py + aim_off + aim_dy + ty_aim / 256.0 * s_pct(settings.camera_aim_height), pz)
    return {"kind": "persp", "eye": eye, "at": at,
            "fov": fov(pers, settings, type_cam=type_cam, move_type=move_type, topograph=topograph),
            "game": {"pers": pers, "distance": dist, "height": height, "correct": correct, "aim": aim,
                     "lifted": lifted, "rotation": float(rotation), "upper_counter": int(upper_counter),
                     "type": int(move_type), "type_cam": int(type_cam), "how": how, "fix": tuple(fix)}}


def s_pct(v: float) -> float:
    return float(v) / 100.0
