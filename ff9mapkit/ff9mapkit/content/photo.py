"""Photo mode (``[photo]``) -- the player takes the camera: pan, hide, grade, and hand it back.

Board entry #8 (studies/eb-uses-board), rung 1. Rung 0 (studies/photo-mode/PLAN.md) proved every mechanism below in-game
with a study-local daemon, 154/154 checks over six harness runs, and the owner playtested it: hotkeys, pan speed and the
exit glide confirmed, and one defect (a snap when the player walks during the exit glide) fixed by THE TRACKING
RELEASE. This module turns that daemon into a field feature.

::

    [photo]                           # a bare table turns it on; every key is optional
    open_button  = "select"           # select l1 r1 l2 r2
    close_button = "cancel"           # cancel select l1 r1 l2 r2 (may equal open_button: a toggle)
    hide_button  = "r1"               # each press hides the next step
    grade_button = "l1"               # toggles a held warm tint
    hide  = ["player", "all"]         # "player", an [[npc]] / [[prop]] name, and "all" (last) -- [] turns it off
    grade = true

THE CAMERA LAWS (engine-read, then proven in-game):

* ``MoveCamera`` (0x6F) itself TAKES the camera: a finished move HOLDS and follow stays off until a ``ReleaseCamera``.
  ``EnableCameraServices(0)`` clears the field's Active bit and every later MoveCamera is dropped -- never emitted.
* The engine never clamps Y, and clamps X only at issue under widescreen to a narrowed window: the daemon clamps to
  the camera's own vrp box, relative to the engine's readback (``CalculateScreenOrigin`` 0xEA -> ``B_SYSVAR[12]/[13]``),
  so the widescreen narrowing costs no wind-up.
* THE TRACKING RELEASE: one ``ReleaseCamera`` computes its target ONCE; control comes back at close, so a player who
  walks during the glide gets a camera that lands where they WERE and then snaps (113 px in one tick, measured).
  ``ReleaseCamera(n_k, 0)`` re-issued every tick with :data:`RELEASE_TABLE` eases like ``ReleaseCamera(16, 8)`` on a
  still player (within 1 px in-game) and lands on a walking one (largest step 28 px).

THE DAEMON keeps all state in its OWN Instance locals (no Global / Map write), reads only its buttons (B_KEY, a
per-tick latch -- never B_KEYON, which arms the dialog turbo), usercontrol, the camera index, the view, the kit's
conductor / stay-locked MAP bits, and its targets' flags. It opens only after 30 ticks of player control, closes
itself (a full, exact restore) when another script GRANTS control back (an EnableMove), a conductor scene starts
(MAP 110) or the camera switches, and hides by running a function seated on each target's own entry (0x93 is
self-only), restoring exactly what it hid. (A foreign DisableMove while it is open is invisible to it -- usercontrol is
already 0 -- and its closing EnableMove would release that lock; the conductor's watchdog re-locks within a tick.)

On the Japanese build the engine swaps logical Cancel and Confirm for SCRIPTS (ETb.ProcessJapaneseLayout, B_KEY's
JP flag) but not for the talk check, so a role bound to ``cancel`` tests 0x20000 in the ``jp`` daemon: the player's
Cancel press, never the Confirm that would also talk.

``problems(raw)`` is the one refusal text validate, lint and the build share; ``arm`` seats and arms the daemon LAST in
``build_script`` and proves THE ORDER LAW (armed after every target's InitObject) and the whole-script laws on the
final bytes.
"""
from __future__ import annotations

import math
import re
import struct
from dataclasses import dataclass

from ..eb import EbScript, disasm as D, edit as eb_edit, exprasm, opcodes
from ..eb.labelasm import JMP, JMP_IFNOT, asm, label


class PhotoError(ValueError):
    """A [photo] rule -- the text validate, lint and the build all report."""


# ============================================================== tables
#: logical input bits (EventInput.cs:537-562) -- what B_KEY tests. NOT the physical names [[event]] mask_buttons uses.
BUTTONS = {"select": 0x1, "start": 0x8, "up": 0x10, "right": 0x20, "down": 0x40, "left": 0x80,
           "cancel": 0x10000, "confirm": 0x20000, "special": 0x80000, "l1": 0x100000, "r1": 0x200000,
           "l2": 0x400000, "r2": 0x800000, "menu": 0x1000000}
#: a shoulder press sets its logical bit AND its PSX physical alias (EventInput.cs:521-531) -- a poller written with the
#: physical int (a [[behavior.pool]] button = 1024) fires on the same press
_PHYS_TWIN = {"l1": 0x400, "r1": 0x800, "l2": 0x100, "r2": 0x200}
_CANCEL, _CONFIRM = 0x10000, 0x20000
ROLES = ("open_button", "close_button", "hide_button", "grade_button")
DEFAULTS = {"open_button": "select", "close_button": "cancel", "hide_button": "r1", "grade_button": "l1"}
_SAFE = frozenset({"cancel", "select", "l1", "r1", "l2", "r2"})
ROLE_OK = {"open_button": frozenset({"select", "l1", "r1", "l2", "r2"}), "close_button": _SAFE,
           "hide_button": _SAFE, "grade_button": _SAFE}
_WHY_NOT = {
    "start": "Start pauses the game (UIScene.cs:156-166)",
    "menu": "Menu opens the main menu, and photo mode's closing EnableMove re-enables it in the same tick",
    "up": "the d-pad pans photo mode and walks the player outside it",
    "down": "the d-pad pans photo mode and walks the player outside it",
    "left": "the d-pad pans photo mode and walks the player outside it",
    "right": "the d-pad pans photo mode and walks the player outside it",
    "confirm": "the daemon runs before the engine's talk check (ProcessEvents.cs), so the same press would also talk "
               "or duel -- and co-op spectators have it filtered",
    "special": "the daemon runs before the engine's talk check (ProcessEvents.cs), so the same press would also talk "
               "or duel -- and co-op spectators have it filtered",
}
_KEYS = ("open_button", "close_button", "hide_button", "grade_button", "hide", "grade")
DEFAULT_HIDE = ("player", "all")
MAX_STEPS, MAX_PARTS = 8, 15

STEP = 4                              # pan px per tick (owner-confirmed on bench 30955)
SETTLE = 30                           # ticks of player control before photo mode may open (1 s)
SYNC_LEVEL = 2                        # RunScriptSync's level -- the stock cutscene idiom; a finished Init is level 7
PHOTO_TAG_BASE = 96                   # hide/show functions seated on a target take the first free pair from here
SCENE_BIT = 110                       # content.conductor.WATCHDOG_MAP_FLAG: a conductor scene is running
STAY_LOCKED_BIT = 156                 # content.region.STAY_LOCKED_IDX: something latched the player locked
GRADE = (2, 8, 0, 0, 64, 128)         # FadeFilter SUB over 8 ticks: white 235 -> (235, 171, 107), gamma-space, held
GRADE_CLEAR = (2, 8, 0, 0, 0, 0)
PSX_W_169 = 398                       # PsxFieldWidth at 16:9 = (Int16)(224 * 16 / 9)
_HALF_4_3 = 160


def release_table(n: int = 16) -> tuple:
    """The cosine ease ReleaseCamera(n, 8) re-expressed as per-tick fractions of the REMAINDER: step k covers
    (e(k) - e(k-1)) / (1 - e(k-1)) of what is left, e(k) = (1 - cos(pi k / n)) / 2, and a linear ReleaseCamera(m, 0)
    covers 1/m of it in its first frame. The last step is 1: it lands and follow resumes."""
    e = [(1 - math.cos(math.pi * k / n)) / 2 for k in range(n + 1)]
    return tuple(max(1, min(254, round((1 - e[k - 1]) / (e[k] - e[k - 1])))) for k in range(1, n + 1))


RELEASE_TABLE = (104, 35, 21, 15, 11, 9, 7, 6, 5, 4, 4, 3, 2, 2, 1, 1)
assert RELEASE_TABLE == release_table(), "RELEASE_TABLE drifted from the ease it encodes"

#: the daemon's own Instance locals (Int16, BYTE offsets)
LOCALS = {"ST": 0, "HX": 2, "GR": 4, "RT": 6, "HELD": 8, "PREV": 10, "CTL": 12, "VX": 14, "VY": 16,
          "CAM0": 18, "PRIOR": 20, "LOX": 22, "HIX": 24, "LOY": 26, "HIY": 28}
LOC = 30
ROLE_BIT = {"open_button": 1, "close_button": 2, "hide_button": 4, "grade_button": 8}
PAD = {"right": 0x20, "left": 0x80, "down": 0x40, "up": 0x10}

DAEMON_OPS = frozenset({0x05, 0x01, 0x02, 0x22, 0x04, 0xEA, 0x6F, 0x70, 0x2D, 0x2E, 0x14, 0xEC, 0xD5, 0xD6})
_REFUSED_OPS = frozenset({0x71, 0x73, 0x74, 0x1E, 0xA9, 0x10, 0x12, 0x7E})


# ============================================================== the spec
@dataclass(frozen=True)
class PhotoSpec:
    buttons: dict                     # role -> button name
    steps: tuple                      # hide steps, in press order
    grade: bool

    def mask(self, role: str, lang: str = "us") -> int:
        """The B_KEY mask for a role on this language's build: the jp daemon tests Confirm's bit for a Cancel role
        (the engine swaps the two for scripts on the Japanese layout)."""
        m = BUTTONS[self.buttons[role]]
        return _CONFIRM if lang == "jp" and m == _CANCEL else m

    def roles(self) -> tuple:
        """The roles this spec polls (hide only with steps, grade only when on)."""
        out = ["open_button", "close_button"]
        if self.steps:
            out.append("hide_button")
        if self.grade:
            out.append("grade_button")
        return tuple(out)

    def bit(self, role: str) -> int:
        if role == "close_button" and self.mask("close_button") == self.mask("open_button"):
            return ROLE_BIT["open_button"]                 # a toggle: one button, one latch bit
        return ROLE_BIT[role]


@dataclass(frozen=True)
class Part:
    """One hidden object: its step, uid, entry and the hide/show tags seated on that entry."""
    step: int
    uid: int
    entry: int
    hide_tag: int
    show_tag: int


@dataclass(frozen=True)
class PanBox:
    cam: int
    w: int
    h: int
    viewport: tuple                   # (lox, hix, loy, hiy): the camera's vrp box = what the daemon clamps to
    x169: tuple | None                # the X box under widescreen 16:9, None when X is pinned
    ok: bool                          # the viewport lies inside the painting (scroll_bounds)

    @property
    def pans_x_43(self) -> bool:
        return self.viewport[1] - self.viewport[0] > 1

    @property
    def pans_y(self) -> bool:
        return self.viewport[3] - self.viewport[2] > 1


def any_photo(raw: dict) -> bool:
    return (raw or {}).get("photo") is not None


def _is_bool(v) -> bool:
    return isinstance(v, bool)


def parse(raw: dict) -> PhotoSpec:
    """The [photo] table as a :class:`PhotoSpec`. Raises :class:`PhotoError` on the first rule it breaks."""
    t = raw.get("photo")
    if not isinstance(t, dict):
        raise PhotoError("[photo]: must be a table -- write [photo] on its own line (one photo mode per field)")
    unknown = sorted(set(t) - set(_KEYS))
    if unknown:
        raise PhotoError(f"[photo]: unknown key(s) {unknown} -- known: {', '.join(_KEYS)}")
    buttons = {}
    for role in ROLES:
        v = t.get(role, DEFAULTS[role])
        if not isinstance(v, str) or v not in BUTTONS:
            raise PhotoError(f"[photo] {role} {v!r}: not a button name -- one of {', '.join(BUTTONS)}")
        if v not in ROLE_OK[role]:
            why = ("Cancel is the walk modifier -- every tap while moving would open photo mode"
                   if (role, v) == ("open_button", "cancel") else _WHY_NOT.get(v, "not allowed for this role"))
            raise PhotoError(f"[photo] {role} {v!r}: {why}; use one of {', '.join(sorted(ROLE_OK[role]))}")
        buttons[role] = v
    hide = t.get("hide", list(DEFAULT_HIDE))
    if not isinstance(hide, list) or not all(isinstance(s, str) and s for s in hide):
        raise PhotoError("[photo] hide: must be a list of names -- \"player\", an [[npc]] / [[prop]] name, or "
                         "\"all\" (last)")
    if len(hide) > MAX_STEPS:
        raise PhotoError(f"[photo] hide: at most {MAX_STEPS} steps, got {len(hide)}")
    dups = sorted({s for s in hide if hide.count(s) > 1})
    if dups:
        raise PhotoError(f"[photo] hide: {dups} listed twice -- each step hides something new")
    if "all" in hide and hide[-1] != "all":
        raise PhotoError("[photo] hide: \"all\" must be the last step -- nothing after it can hide anything new")
    grade = t.get("grade", True)
    if not _is_bool(grade):
        raise PhotoError(f"[photo] grade: must be true or false, got {grade!r}")
    spec = PhotoSpec(buttons=buttons, steps=tuple(hide), grade=grade)
    polled = spec.roles()
    for i, a in enumerate(polled):
        for b in polled[i + 1:]:
            if buttons[a] == buttons[b] and {a, b} != {"open_button", "close_button"}:
                raise PhotoError(f"[photo] {a} and {b} are both {buttons[a]!r} -- every role needs its own button "
                                 f"(only close_button may equal open_button: a toggle)")
    if "hide_button" in t and not hide:
        raise PhotoError("[photo] hide_button is set but hide = [] -- nothing to hide")
    if "grade_button" in t and not grade:
        raise PhotoError("[photo] grade_button is set but grade = false -- nothing to toggle")
    return spec


# ============================================================== targets
def _named(raw: dict, kind: str, name: str) -> list:
    return [(i, d) for i, d in enumerate(raw.get(kind) or []) if isinstance(d, dict) and d.get("name") == name]


def _parts_of_prop(p: dict) -> int:
    from .. import prop_archetypes as _pa
    n = p.get("prop")
    if isinstance(n, str) and _pa.is_composite(n):
        return len(_pa.resolve_composite(n))
    return 1


def _target_problems(raw: dict, spec: PhotoSpec) -> list:
    from . import behaviortoml as _bt
    out, parts = [], 0
    try:
        pooled = set(_bt.pooled_npcs(raw))
        members = {m for u in _bt.units(raw) if isinstance(u, dict) for m in _bt.row_members(u)}
    except Exception:                                      # noqa: BLE001 -- behavior validate() reports its own
        pooled, members = set(), set()
    carriers = {p.get("attach_to") for p in (raw.get("prop") or []) if isinstance(p, dict) and p.get("attach_to")}
    cs = raw.get("cutscene")
    free_cast = {str(a) for c in (cs if isinstance(cs, list) else [cs] if isinstance(cs, dict) else [])
                 if isinstance(c, dict) and c.get("owns_control", True) is False for a in (c.get("actors") or [])}
    busy = ("an actor of a [[cutscene]] with owns_control = false (it walks while the player can still open photo "
            "mode: a hide or show would wait on its walk, and if it walks into the locked player they wait on each "
            "other for ever)")
    for step in spec.steps:
        if step == "all":
            continue
        if step == "player":
            parts += 1
            if "player" in free_cast:
                out.append(f"[photo] hide 'player': {busy}")
            continue
        npcs, props = _named(raw, "npc", step), _named(raw, "prop", step)
        if not npcs and not props:
            out.append(f"[photo] hide {step!r}: no [[npc]] or [[prop]] is named {step!r} (a [[prop]] is matched by "
                       f"its `name` key)")
            continue
        if len(npcs) + len(props) > 1:
            out.append(f"[photo] hide {step!r}: {len(npcs)} [[npc]] and {len(props)} [[prop]] share that name -- "
                       f"a hide target must be one object")
            continue
        d = (npcs or props)[0][1]
        why = [k for k in ("requires_flag", "requires_flag_clear", "scenario_min", "scenario_max") if k in d]
        if npcs:
            parts += 1
            if step in pooled:
                why.append("a pooled behavior unit")
            elif step in members:
                why.append("a [behavior] unit (its duty loop re-shows it every pass)")
            if d.get("holds"):
                why.append("holds")
            if step in carriers:
                why.append("carries a [[prop]] (attach_to)")
            if d.get("lock") is False:
                why.append("lock = false (its dialogue leaves the player free, so photo mode can open over it, and a "
                           "hide of it would wait until the window closes)")
            if step in free_cast:
                why.append(busy)
        else:
            parts += _parts_of_prop(d)
            if d.get("attach_to"):
                why.append("attach_to")
        if why:
            out.append(f"[photo] hide {step!r}: {', '.join(why)} -- a hide target must exist, unchanged, for the "
                       f"whole visit: RunScriptSync on an absent object re-runs for ever (DoEventCode.cs:206-209), so "
                       f"photo mode would freeze with the player locked")
    if parts > MAX_PARTS:
        out.append(f"[photo] hide: at most {MAX_PARTS} parts (a composite [[prop]] counts every part), got {parts}")
    return out


# ============================================================== pan boxes
def _camera_cfgs(raw: dict) -> list:
    c = raw.get("camera")
    if isinstance(c, list):
        return [x for x in c if isinstance(x, dict)]
    return [c] if isinstance(c, dict) else []


def _ints(v, n: int) -> bool:
    return isinstance(v, (list, tuple)) and len(v) == n and all(isinstance(x, int) and not isinstance(x, bool)
                                                                 for x in v)


def _shape_problem(c: dict, i: int) -> str | None:
    if "range" in c and not _ints(c["range"], 2):
        return f"[photo] camera {i}: range must be [width, height] (two integers) to size the pan box, got {c['range']!r}"
    if "viewport" in c and not _ints(c["viewport"], 4):
        return (f"[photo] camera {i}: viewport must be [min_x, max_x, min_y, max_y] (four integers), got "
                f"{c['viewport']!r}")
    return None


def pan_boxes(raw: dict) -> list:
    """Per camera, the box the daemon clamps to -- the camera's own vrp box, chosen exactly as the build's
    ``_resolve_one_camera`` does (explicit ``viewport``, else ``scroll_bounds(range)`` on a scrolling field, else the
    default viewport) -- and its X box under widescreen 16:9, where the engine narrows X by
    ``d = min(PsxFieldWidth - 320, hix - lox) / 2`` (BGCAM_DEF.cs RefreshCache). A borrowed camera has no box here."""
    from ..scene import cam as _cam, guide as _guide
    cfgs = _camera_cfgs(raw)
    scrolling = bool(cfgs and (cfgs[0].get("scroll") or {}).get("enabled"))
    out = []
    for i, c in enumerate(cfgs):
        if "borrow" in c or _shape_problem(c, i):
            continue                                        # problems() reports a malformed range / viewport
        w, h = (int(v) for v in c.get("range", (384, 448)))
        if "viewport" in c:
            vp = tuple(int(v) for v in c["viewport"])
        elif scrolling:
            vp = tuple(_cam.scroll_bounds((w, h)))
        else:
            vp = tuple(_guide.DEFAULT_VIEWPORT)
        sb = _cam.scroll_bounds((w, h))
        ok = (len(vp) == 4 and sb[0] <= vp[0] <= vp[1] <= sb[1] and sb[2] <= vp[2] <= vp[3] <= sb[3])
        d = min(PSX_W_169 - 2 * _HALF_4_3, max(0, vp[1] - vp[0])) // 2 if len(vp) == 4 else 0
        x169 = (vp[0] + d, vp[1] - d) if len(vp) == 4 and vp[1] - vp[0] - 2 * d > 1 else None
        out.append(PanBox(cam=i, w=w, h=h, viewport=vp, x169=x169, ok=ok))
    return out


def box_lines(raw: dict) -> list:
    """The camera section of lint: what photo mode can pan, per camera, at 4:3 and 16:9."""
    if not any_photo(raw):
        return []
    out = []
    for b in pan_boxes(raw):
        lox, hix, loy, hiy = b.viewport
        x43 = f"X {lox}..{hix} ({hix - lox} px)" if b.pans_x_43 else f"X {lox} pinned"
        yy = f"Y {loy}..{hiy} ({hiy - loy} px)" if b.pans_y else f"Y {loy} pinned"
        x169 = f"X {b.x169[0]}..{b.x169[1]} ({b.x169[1] - b.x169[0]} px)" if b.x169 else "X pinned"
        out.append(f"[photo] camera {b.cam} {b.w}x{b.h}: 4:3 {x43}, {yy} | 16:9 {x169}, {yy}")
    return out


# ============================================================== refusals
def problems(raw: dict, *, donor=None) -> list:
    """Every refusal for ``raw`` -- the same texts validate, lint and the build report. ``donor`` =
    ``build.donor_field_id(raw)`` (passed in: this module never imports build)."""
    if not any_photo(raw):
        return []
    try:
        spec = parse(raw)
    except PhotoError as e:
        return [str(e)]
    out: list = []
    fork = []
    if raw.get("verbatim_eb") is not None:
        fork.append("[verbatim_eb]")
    if donor is not None:
        fork.append(f"a donor (field {donor})")
    if any("borrow" in c for c in _camera_cfgs(raw)):
        fork.append("[camera] borrow")
    fld = raw.get("field") or {}
    for k in ("bgs", "borrow_bg"):
        if fld.get(k):
            fork.append(f"[field] {k}")
    if fork:
        out.append(f"[photo]: novel fields only -- this field has {' and '.join(fork)}. A donor's own camera ops, its "
                   f"other cameras and its widescreen width are invisible to the build -- forks are rung 2")
    out += _collision_problems(raw, spec)
    out += _target_problems(raw, spec)
    shapes = [p for i, c in enumerate(_camera_cfgs(raw)) for p in [_shape_problem(c, i)] if p]
    out += shapes
    if not fork and not shapes:
        boxes = pan_boxes(raw)
        for b in boxes:
            if not b.ok:
                out.append(f"[photo] camera {b.cam}: viewport {b.viewport} reaches past the painting (scroll_bounds = "
                           f"{(_HALF_4_3, b.w - _HALF_4_3, 112, b.h - 112)}) -- photo mode clamps to the engine's own "
                           f"box, so it would pan off the art; use a viewport inside scroll_bounds(range)")
        if boxes and not any(b.x169 or b.pans_y for b in boxes):
            b = boxes[0]
            out.append(f"[photo]: no camera can pan either axis at 16:9 (camera 0 {b.w}x{b.h}: X pinned, Y "
                       f"{b.viewport[2]} pinned) -- widen or heighten the canvas")
    return out


def _collision_problems(raw: dict, spec: PhotoSpec) -> list:
    out = []
    ob = spec.buttons["open_button"]
    om = BUTTONS[ob] | _PHYS_TWIN.get(ob, 0)
    if raw.get("ate") and om & 0x1:
        out.append(f"[photo] open_button {ob!r} is also [ate]'s menu button (content/ate.py) -- one press opens one and "
                   f"silently shadows the other; rebind (l2 / r2 are free) or drop [ate]")
    try:
        from . import behaviortoml as _bt
        pools = _bt.pool_specs(raw)
    except Exception:                                      # noqa: BLE001 -- behavior validate() reports its own
        pools = []
    for k, ps in enumerate(pools):
        if ps.button is not None and int(ps.button) & om:
            if raw.get("siege"):
                out.append(f"[photo] open_button {ob!r} is also [siege]'s council button (button = true by default) "
                           f"-- the council opens over photo mode and its EnableMove frees the player under the "
                           f"held camera; rebind one of them")
            else:
                out.append(f"[photo] open_button {ob!r} is also [[behavior.pool]] #{k}'s hire button -- the hire menu "
                           f"opens over photo mode and its EnableMove frees the player under the held camera; rebind "
                           f"one of them")
            break
    return out


def lint_notes(raw: dict) -> list:
    """ACTIONABLE advisories only -- `ff9mapkit lint` exits 1 on any, so what is merely true of a field (its pan box,
    a pinned X, several cameras) goes in the build report (:func:`report_notes`) instead. Never raises; skips what
    :func:`problems` refuses."""
    if not any_photo(raw):
        return []
    try:
        spec = parse(raw)
    except PhotoError:
        return []
    out = []
    from .movement import button_mask
    for kind in ("event", "on_entry"):
        for i, e in enumerate(raw.get(kind) or []):
            if not isinstance(e, dict) or e.get("mask_buttons") is None:
                continue
            try:
                m = button_mask(e["mask_buttons"])
            except Exception:                              # noqa: BLE001 -- validate() reports a bad name
                continue
            # the mask clears PHYSICAL bits (EventInput.cs:192): Select and the d-pad share their logical bit, a
            # shoulder's logical bit survives its physical mask -- so only these two can block photo mode
            sel = 0x1 if spec.buttons["open_button"] == "select" else 0
            hit = [(n, v) for n, bit, v in (("select (the open button)", sel, "open"), ("the d-pad (the pan)", 0xF0, "pan"))
                   if m & bit]
            if hit:
                out.append(f"[photo]: [[{kind}]] #{i} mask_buttons masks {' and '.join(n for n, _v in hit)} -- while "
                           f"that mask holds photo mode cannot {' or '.join(v for _n, v in hit)}")
    if "all" in spec.steps:
        try:
            from . import behaviortoml as _bt
            pooled = bool(_bt.pooled_npcs(raw)) or bool(_bt.pool_specs(raw))
        except Exception:                                  # noqa: BLE001
            pooled = False
        if pooled:
            out.append("[photo] hide \"all\": this field spawns pooled units at runtime -- one spawned while \"all\" is "
                       "up comes back hidden at the close (it was not there to be snapshotted) until its next duty "
                       "pass re-shows it; drop \"all\" to avoid the blink")
    return out


def report_notes(raw: dict) -> list:
    """What is TRUE of a [photo] field -- printed with the build's report, not as a lint warning."""
    out = list(box_lines(raw))
    boxes = pan_boxes(raw)
    for b in boxes:
        if b.pans_x_43 and not b.x169:
            out.append(f"[photo] camera {b.cam} ({b.w} wide): X pans at 4:3 but is pinned under widescreen -- a canvas "
                       f"wider than {PSX_W_169} px pans sideways on every screen")
    if len(boxes) > 1:
        out.append("[photo]: several cameras -- a camera switch closes photo mode (the player is locked while it is "
                   "open, so a [[camera_zone]] cannot switch it)")
    if raw.get("behavior") or raw.get("siege"):
        out.append("[photo]: [behavior] / [siege] keep running while photo mode is open -- units move, countdowns "
                   "tick, a Flash overwrites the grade, and units re-show themselves under \"all\"")
    return out


# ============================================================== the daemon
def _x(e: str) -> bytes:
    return exprasm.assemble(e + " B_EXPR_END")


def _stmt(text: str) -> bytes:
    return opcodes.encode(0x05, _x(text), arg_flags=0b1)


def L(name: str) -> str:
    return f"Instance.Int16[{LOCALS[name]}]"


def _set(name: str, expr: str) -> bytes:
    return _stmt(f"{L(name)} {expr} B_LET")


def _k(mask: int) -> str:
    """A key mask literal: B_CONST is a signed Int16, so a mask >= 0x8000 is const4 (a const would read negative)."""
    return f"const({mask})" if mask <= 0x7FFF else f"const4({mask})"


def _key(mask: int) -> str:
    return f"{_k(mask)} B_KEY"


def _edge(bit: int) -> str:
    """1 on the tick a latched button goes down: (HELD & bit) > (PREV & bit)."""
    return f"{L('HELD')} const({bit}) B_AND {L('PREV')} const({bit}) B_AND B_GT"


def _sum(terms: list) -> str:
    return terms[0] + "".join(f" {t} B_PLUS" for t in terms[1:])


def _clamp(name: str, lo: str, hi: str) -> list:
    v = L(name)
    return [_stmt(f"{v} {v} {v} {L(hi)} B_GT {v} {L(hi)} B_MINUS B_MULT B_MINUS B_LET"),
            _stmt(f"{v} {v} {v} {L(lo)} B_LT {L(lo)} {v} B_MINUS B_MULT B_PLUS B_LET")]


def flag_function(uid: int, show: bool) -> bytes:
    """The body seated as a target's hide / show function: SetObjectFlags(its flags with bit 0 cleared / set).
    0x93 writes flags = (flags & ~63) | (arg & 63), so the other five low bits ride through. Byte-identical to rung 0's
    in-game-proven ``photo0_bench.flag_function``."""
    e = f"obj(uid={uid}).f[4] const(1) B_OR" if show else f"obj(uid={uid}).f[4] const(62) B_AND"
    return opcodes.encode(0x93, _x(e), arg_flags=0b1) + opcodes.RETURN


def daemon_body(spec: PhotoSpec, parts, boxes, lang: str = "us") -> bytes:
    """The photo daemon: a prelude zeroing its locals, then one tick per loop pass. ``parts`` = [:class:`Part`];
    ``boxes`` = [(lox, hix, loy, hiy)] per camera index; ``lang`` = the build's language (the jp daemon tests the
    swapped Cancel bit, :meth:`PhotoSpec.mask`)."""
    parts = list(parts)
    steps = spec.steps
    roles = spec.roles()
    held = {}
    for r in roles:                                        # one latch bit per distinct button
        held.setdefault(spec.bit(r), spec.mask(r, lang))
    sys2, sys1 = "B_SYSVAR[2]", "B_SYSVAR[1]"
    B: list = [_set(n, "const(0)") for n in LOCALS]
    B += [label("top"),
          _set("HELD", _sum([f"{_key(m)} const({b}) B_MULT" for b, m in sorted(held.items())])),
          _set("CTL", f"{L('CTL')} {L('CTL')} const({SETTLE}) B_LT B_PLUS {sys2} const(0) B_NE B_MULT"),
          _set("RT", f"{L('RT')} {L('RT')} const(0) B_GT B_PLUS {L('RT')} const({len(RELEASE_TABLE)}) B_LT B_MULT"),
          _stmt(f"{L('ST')} const(0) B_NE"), (JMP_IFNOT, "closed"),
          (JMP, "read"),
          label("closed"),
          _stmt(f"{_edge(spec.bit('open_button'))} {sys2} const(0) B_NE B_ANDAND {L('CTL')} const({SETTLE}) B_GE "
                f"B_ANDAND Map.Bit[{SCENE_BIT}] const(0) B_EQ B_ANDAND Map.Bit[{STAY_LOCKED_BIT}] const(0) B_EQ "
                f"B_ANDAND"), (JMP_IFNOT, "track"),
          label("read"),                                    # THE one 0xEA, copied at once (0xA9 shares the registers)
          opcodes.calculate_screen_origin(), _set("VX", "B_SYSVAR[12]"), _set("VY", "B_SYSVAR[13]"),
          _stmt(f"{L('ST')} const(0) B_EQ"), (JMP_IFNOT, "opened"),
          # ---- open: lock, THEN take the camera where it is (rung 0's order), and pick this camera's box. A tracking
          # glide still counting (RT > 0) is inert while open: only the closed path re-issues, and the close resets RT.
          opcodes.encode(0x2D),
          opcodes.move_camera(_x(L("VX")), _x(L("VY")), 1, 0),
          _set("CAM0", sys1),
          _set("LOX", L("VX")), _set("HIX", L("VX")), _set("LOY", L("VY")), _set("HIY", L("VY"))]  # fail closed
    for k, (lox, hix, loy, hiy) in enumerate(boxes):
        B += [_stmt(f"{L('CAM0')} const({k}) B_EQ"), (JMP_IFNOT, f"box{k}"),
              _set("LOX", f"const({lox})"), _set("HIX", f"const({hix})"),
              _set("LOY", f"const({loy})"), _set("HIY", f"const({hiy})"), (JMP, "boxed"), label(f"box{k}")]
    B += [label("boxed"),
          _set("ST", "const(1)"), _set("HX", "const(0)"), _set("GR", "const(0)"), _set("PRIOR", "const(0)"),
          (JMP, "tail"),
          # ---- closed and not opening: the tracking release, one step a tick
          label("track"),
          _stmt(f"{L('RT')} const(0) B_NE"), (JMP_IFNOT, "tail"),
          _stmt(f"{sys1} {L('CAM0')} B_EQ"), (JMP_IFNOT, "retarget"),
          label("chain")]
    for k, n in enumerate(RELEASE_TABLE[1:], 2):
        B += [_stmt(f"{L('RT')} const({k}) B_EQ"), (JMP_IFNOT, f"rel{k}"), opcodes.release_camera(n, 0),
              (JMP, "tail"), label(f"rel{k}")]
    B += [(JMP, "tail"),
          # a camera switch mid-glide (a [[camera_zone]] the player walked into): keep tracking -- the next re-issue
          # re-reads the follow point on the NEW camera and lands there (stopping would leave the last release gliding
          # to the old camera's point, then snap)
          label("retarget"), _set("CAM0", sys1), (JMP, "chain"),
          # ---- open: yield (a full close) when anything else takes over, else hide / grade / pan
          label("opened"),
          _stmt(f"{sys2} const(0) B_NE {sys1} {L('CAM0')} B_NE B_OROR Map.Bit[{SCENE_BIT}] const(0) B_NE B_OROR "
                f"{_edge(spec.bit('close_button'))} B_OROR"), (JMP_IFNOT, "stay"),
          (JMP, "close"),
          label("stay")]
    if steps:
        B += [_stmt(_edge(spec.bit("hide_button"))), (JMP_IFNOT, "hidden")]
        for t, step in enumerate(steps):
            B += [_stmt(f"{L('HX')} const({t}) B_EQ"), (JMP_IFNOT, f"hs{t}")]
            if step == "all":
                B.append(opcodes.encode(0xD5))
            for j, p in enumerate(parts):
                if p.step == t:
                    B += [_set("PRIOR", f"{L('PRIOR')} obj(uid={p.uid}).f[4] const(1) B_AND const({1 << j}) B_MULT "
                                        f"B_PLUS"),
                          opcodes.run_script_sync(SYNC_LEVEL, p.uid, p.hide_tag)]
            B += [(JMP, "hsinc"), label(f"hs{t}")]
        B += [label("hsinc"),
              _set("HX", f"{L('HX')} {L('HX')} const({len(steps)}) B_LT B_PLUS"),
              label("hidden")]
    if spec.grade:
        B += [_stmt(_edge(spec.bit("grade_button"))), (JMP_IFNOT, "graded"),
              _stmt(f"{L('GR')} const(0) B_EQ"), (JMP_IFNOT, "gradeoff"),
              opcodes.fade_filter(*GRADE), _set("GR", "const(1)"), (JMP, "graded"),
              label("gradeoff"),
              opcodes.fade_filter(*GRADE_CLEAR), _set("GR", "const(0)"),
              label("graded")]
    kr, kl, kd, ku = (_key(PAD[d]) for d in ("right", "left", "down", "up"))
    B += [_stmt(f"{kr} {kl} B_OROR {kd} B_OROR {ku} B_OROR"), (JMP_IFNOT, "tail"),
          _set("VX", f"{L('VX')} {kr} {kl} B_MINUS const({STEP}) B_MULT B_PLUS"),
          _set("VY", f"{L('VY')} {kd} {ku} B_MINUS const({STEP}) B_MULT B_PLUS"),
          *_clamp("VX", "LOX", "HIX"), *_clamp("VY", "LOY", "HIY"),
          opcodes.move_camera(_x(L("VX")), _x(L("VY")), 1, 0),
          (JMP, "tail"),
          # ---- close: restore exactly what was hidden (REVERSE order: "all" first), clear the grade, hand back
          label("close")]
    if "all" in steps:
        ia = steps.index("all")
        B += [_stmt(f"{L('HX')} const({ia}) B_GT"), (JMP_IFNOT, "unall"), opcodes.encode(0xD6), label("unall")]
    for t in range(len(steps) - 1, -1, -1):
        for j, p in enumerate(parts):
            if p.step == t:
                B += [_stmt(f"{L('HX')} const({t}) B_GT {L('PRIOR')} const({1 << j}) B_AND B_ANDAND"),
                      (JMP_IFNOT, f"un{j}"), opcodes.run_script_sync(SYNC_LEVEL, p.uid, p.show_tag), label(f"un{j}")]
    if spec.grade:
        B += [_stmt(f"{L('GR')} const(0) B_NE"), (JMP_IFNOT, "ungraded"), opcodes.fade_filter(*GRADE_CLEAR),
              label("ungraded")]
    B += [opcodes.release_camera(RELEASE_TABLE[0], 0), _set("RT", "const(1)"), _set("CAM0", sys1),
          opcodes.encode(0x2E),
          _set("ST", "const(0)"), _set("HX", "const(0)"), _set("GR", "const(0)"), _set("PRIOR", "const(0)"),
          _set("CTL", f"const({SETTLE})"),
          label("tail"),
          _set("PREV", L("HELD")),
          opcodes.wait(1), (JMP, "top"), opcodes.RETURN]
    return asm(B)


# ============================================================== the self-audit
_TOKENS_OK = {"B_LET", "B_PLUS", "B_MINUS", "B_MULT", "B_AND", "B_OR", "B_GT", "B_LT", "B_GE", "B_EQ", "B_NE",
              "B_ANDAND", "B_OROR", "B_KEY", "B_EXPR_END"}


def audit_body(body: bytes, spec: PhotoSpec, parts, boxes) -> list:
    """The daemon's laws on its EMITTED bytes. Returns the violations."""
    from ..eb import exprsem
    bad: list = []
    parts = list(parts)
    uids = {p.uid for p in parts}
    tags = {p.uid: {p.hide_tag, p.show_tag} for p in parts}
    ops = list(D.iter_code(body, 0, len(body)))
    count = {}
    for i in ops:
        count[i.op] = count.get(i.op, 0) + 1
        if i.op in _REFUSED_OPS:
            bad.append(f"op 0x{i.op:02X} at +{i.off} is refused in the photo daemon")
        elif i.op not in DAEMON_OPS:
            bad.append(f"op 0x{i.op:02X} at +{i.off} is not a photo-daemon op")
    ea = [i for i in ops if i.op == 0xEA]
    if len(ea) != 1:
        bad.append(f"exactly one 0xEA, found {len(ea)}")
    else:
        k = ops.index(ea[0])
        nxt = [D.pretty_expr(body, ops[k + j].off + 1)[0] for j in (1, 2) if k + j < len(ops) and ops[k + j].op == 0x05]
        if nxt != [f"{{{L('VX')} B_SYSVAR[12] B_LET B_EXPR_END}}", f"{{{L('VY')} B_SYSVAR[13] B_LET B_EXPR_END}}"]:
            bad.append("the 0xEA must be followed at once by VX := B_SYSVAR[12] and VY := B_SYSVAR[13]")
    mc = [i for i in ops if i.op == 0x6F]
    if len(mc) != 2 or any(body[i.off + 1] != 0x03 or body[i.end - 2] != 1 or body[i.end - 1] != 0 for i in mc):
        bad.append("exactly two MoveCamera, each (expr X, expr Y, 1, 0)")
    rc = [i for i in ops if i.op == 0x70]
    if sorted(body[i.off + 2] for i in rc) != sorted(RELEASE_TABLE) or any(
            body[i.off + 1] != 0 or body[i.off + 3] != 0 for i in rc):
        bad.append(f"the ReleaseCameras must be exactly RELEASE_TABLE, literal, type 0 -- got "
                   f"{sorted(body[i.off + 2] for i in rc)}")
    if count.get(0x2D, 0) != 1 or count.get(0x2E, 0) != 1:
        bad.append("exactly one DisableMove and one EnableMove")
    if count.get(0x04, 0) != 1:
        bad.append("exactly one RETURN (the unreachable tail) -- a RETURN in the loop stops photo mode for the visit")
    for i in ops:
        if i.op == 0x14:
            lv, uid, tg = body[i.off + 2], body[i.off + 3], body[i.off + 4]
            if body[i.off + 1] != 0 or lv != SYNC_LEVEL or uid not in uids or tg not in tags.get(uid, ()):
                bad.append(f"RunScriptSync at +{i.off} ({lv}, {uid}, {tg}) is not a seated part's hide/show")
    want_all = 1 if "all" in spec.steps else 0
    if count.get(0xD5, 0) != want_all or count.get(0xD6, 0) != want_all:
        bad.append("HideAllObjects / ShowAllObjects once each iff \"all\" is a step")
    fades = sorted(tuple(body[i.off + 2:i.end]) for i in ops if i.op == 0xEC)
    if fades != (sorted([GRADE, GRADE_CLEAR, GRADE_CLEAR]) if spec.grade else []):
        bad.append(f"the FadeFilters must be exactly the grade and its two clears -- got {fades}")
    waits = [i for i in ops if i.op == 0x22]
    if len(waits) != 1 or body[waits[0].off + 2] != 1:
        bad.append("the loop must yield with exactly one Wait(1) per tick")
    else:
        after = [i for i in ops if i.off > waits[0].off]
        if not after or after[0].op != 0x01 or [i.op for i in after] != [0x01, 0x04]:
            bad.append("the Wait(1) must be followed by exactly the closing JMP and an unreachable RETURN")
        elif D.jump_target(after[0]) != (ops[len(LOCALS)].off if len(ops) > len(LOCALS) else -1):
            bad.append("the closing JMP must return to the top of the tick")
    prelude = [D.pretty_expr(body, i.off + 1)[0] for i in ops[:len(LOCALS)] if i.op == 0x05]
    if prelude != [f"{{{L(n)} const(0) B_LET B_EXPR_END}}" for n in LOCALS]:
        bad.append("the prelude must zero every local exactly once, in order, before the loop")
    offs = set()
    for i in ops:
        if i.op != 0x05 and not any(t is not None for t in _expr_operands(body, i)):
            continue
        for txt in _expr_texts(body, i):
            inner = txt.strip().strip("{}").strip()
            try:
                exprsem.analyze(inner if inner.endswith("B_EXPR_END") else inner + " B_EXPR_END")
            except Exception as e:                       # noqa: BLE001 -- the audit reports, it never crashes
                bad.append(f"expression {inner[:60]!r}: {e}")
            toks = inner.split()
            for n, tok in enumerate(toks):
                m = re.fullmatch(r"Instance\.Int16\[(\d+)\]", tok)
                mo = re.fullmatch(r"obj\(uid=(\d+)\)\.f\[4\]", tok)
                if m:
                    offs.add(int(m.group(1)))
                elif mo:
                    if int(mo.group(1)) not in uids:
                        bad.append(f"obj(uid={mo.group(1)}) is not a hide target")
                elif tok.startswith("const4("):
                    v = int(tok[7:-1])
                    if v not in BUTTONS.values() or v < 0x8000 or n + 1 >= len(toks) or toks[n + 1] != "B_KEY":
                        bad.append(f"{tok} is not a button mask read by B_KEY")
                elif re.fullmatch(r"const\(\d+\)", tok):
                    if int(tok[6:-1]) > 0x7FFF:
                        bad.append(f"{tok} reads back NEGATIVE in the engine (B_CONST is a signed Int16)")
                elif tok in ("B_SYSVAR[1]", "B_SYSVAR[2]", "B_SYSVAR[12]", "B_SYSVAR[13]",
                             f"Map.Bit[{SCENE_BIT}]", f"Map.Bit[{STAY_LOCKED_BIT}]"):
                    pass                                  # read only: the write rule below refuses any other target
                elif tok not in _TOKENS_OK:
                    bad.append(f"token {tok!r} is not allowed in the photo daemon")
            if toks and not re.fullmatch(r"Instance\.Int16\[\d+\]", toks[0]) and "B_LET" in toks:
                bad.append(f"a write to something other than the daemon's own locals: {inner[:60]!r}")
    if offs != set(LOCALS.values()):
        bad.append(f"the locals sit at Instance byte offsets {sorted(offs)}, not exactly {sorted(LOCALS.values())}")
    if re.search(rb"\x7d[\x00-\xff][\x80-\xff]\x59", body):
        bad.append("a const(>= 0x8000) key mask -- the engine reads it negative")
    return bad


def _expr_operands(body: bytes, ins) -> list:
    try:
        return D.instr_expr_tokens(body, ins)
    except ValueError:
        return []


def _expr_texts(body: bytes, ins) -> list:
    if ins.op == 0x05:
        return [D.pretty_expr(body, ins.off + 1)[0]]
    out, pos = [], ins.off + 1
    flags = body[pos]
    pos += 1
    from ..eb import opcodes as _o
    for k in range(_o.OP_ARG_COUNT[ins.op]):
        if flags & (1 << k):
            txt, pos = D.pretty_expr(body, pos)
            out.append(txt)
        else:
            pos += D.argsize(ins.op, k)
    return out


def entry_bytes(spec: PhotoSpec, parts, boxes, lang: str = "us") -> bytes:
    """The seated code entry -- type 0, ONE tag-0 function at fpos 4 -- self-audited: raises :class:`PhotoError`."""
    body = daemon_body(spec, parts, boxes, lang)
    bad = audit_body(body, spec, parts, boxes)
    if bad:
        raise PhotoError("[photo]: the photo daemon failed its self-audit: " + "; ".join(bad[:4]))
    return bytes([0x00, 0x01]) + struct.pack("<HH", 0, 4) + body


# ============================================================== seating on the built script
_OP_SETMODEL, _OP_INITOBJ = 0x2F, 0x09


def player_entry(eb: bytes) -> int:
    s = EbScript.from_bytes(eb)
    hits = [e.index for e in s.entries if e.size > 0 and e.funcs
            and any(i.op == 0x2C for i in D.iter_code(eb, e.funcs[0].abs_start, e.funcs[0].abs_end))]
    if len(hits) != 1:
        raise PhotoError(f"[photo]: expected ONE DefinePlayerCharacter entry, found {hits}")
    return hits[0]


def _free_pair(eb: bytes, entry: int) -> tuple:
    used = {f.tag for f in EbScript.from_bytes(eb).entry(entry).funcs}
    t = PHOTO_TAG_BASE
    while t in used or t + 1 in used:
        t += 2
    if t + 1 > 255:
        raise PhotoError(f"[photo]: entry {entry} has no free function tag pair at or above {PHOTO_TAG_BASE}")
    return t, t + 1


def _target_law(eb: bytes, slot: int, name: str, model: int | None = None) -> list:
    """A hide target's Init must finish (level 7 -- RunScriptSync(2, ...) is accepted only then) and be the object the
    toml names: a SetModel (of ``model`` when the build knows it -- THE SLOT-MAP LAW), no backward jump, a RETURN."""
    s = EbScript.from_bytes(eb)
    if not 0 <= slot < s.entry_count or s.entry(slot).size <= 0:
        return [f"hide {name!r}: slot {slot} does not exist"]
    f0 = s.entry(slot).func_by_tag(0)
    if f0 is None:
        return [f"hide {name!r}: slot {slot} has no Init"]
    ops = list(D.iter_code(eb, f0.abs_start, f0.abs_end))
    out = []
    sm = [struct.unpack_from("<H", eb, i.off + 2)[0] for i in ops if i.op == _OP_SETMODEL and eb[i.off + 1] == 0]
    if not sm:
        out.append(f"hide {name!r}: slot {slot}'s Init sets no model (THE SLOT-MAP LAW)")
    elif model is not None and model not in sm:
        out.append(f"hide {name!r}: slot {slot}'s Init sets model {sm[0]}, not the {model} the toml names (THE "
                   f"SLOT-MAP LAW)")
    if any(i.op in (0x01, 0x03) and (D.jump_target(i) or 0) < i.off for i in ops):
        out.append(f"hide {name!r}: slot {slot}'s Init loops -- it never finishes, so a RunScriptSync on it waits "
                   f"for ever")
    if not ops or ops[-1].op != 0x04:
        out.append(f"hide {name!r}: slot {slot}'s Init does not end in RETURN")
    return out


_KEY_READS = (0x59, 0x4F, 0x58)                  # B_KEY / B_KEYON / B_KEYOFF


def _whole_script_laws(eb: bytes, photo_slot: int, spec: PhotoSpec) -> list:
    """CAMERA-OWNER (0x6F / 0x70 / 0xEA only in the photo entry; 0x71 only as EnableCameraServices(1, ...); 0x73 /
    0x74 / 0x1E nowhere) and E-POLL (no key read outside the photo entry may test the open button -- its logical bit
    or, for a shoulder button, its physical twin -- and none may take a computed mask) on the FINAL bytes."""
    out = []
    ob = spec.buttons["open_button"]
    om = BUTTONS[ob] | _PHYS_TWIN.get(ob, 0)
    s = EbScript.from_bytes(eb)
    for e in s.entries:
        if e.size <= 0 or e.index == photo_slot:
            continue
        for fn in e.funcs:
            for i in D.iter_code(eb, fn.abs_start, fn.abs_end):
                where = f"entry {e.index} tag {fn.tag}"
                if i.op in (0x6F, 0x70, 0xEA):
                    out.append(f"{where} runs 0x{i.op:02X} -- photo mode owns the scripted camera (CAMERA-OWNER)")
                elif i.op in (0x73, 0x74, 0x1E):
                    out.append(f"{where} runs 0x{i.op:02X} -- it rewrites the clamp photo mode relies on")
                elif i.op == 0x71 and (eb[i.off + 1] & 1 or eb[i.off + 2] != 1):
                    out.append(f"{where} runs EnableCameraServices with a first operand other than a literal 1 -- "
                               f"0 drops every MoveCamera")
                for toks in _expr_operands(eb, i):
                    if not toks:
                        continue
                    for n, (op, _v) in enumerate(toks):
                        if op in _KEY_READS:
                            prev = toks[n - 1] if n else (None, None)
                            if prev[0] not in (0x7D, 0x7E):
                                out.append(f"{where} reads a key with a computed mask -- it may be photo mode's "
                                           f"open button (E-POLL)")
                            elif int(prev[1]) & om:
                                out.append(f"{where} also polls the open button {ob!r} (E-POLL) -- one press would "
                                           f"open photo mode and fire it")
    return out


def _seat_daemon(eb: bytes, entry: bytes) -> tuple:
    """Seat the daemon in the first free slot that is not 64 above a STARTSEQ entry (THE 64-STRIDE LAW: a Seq there
    takes uid slot and disposes the object), so a ladder in the player entry never refuses a field another slot fits."""
    from . import motion as _motion, object as _object
    s = EbScript.from_bytes(eb)
    free = [e.index for e in s.entries if e.empty] + list(range(s.entry_count, 250))   # append_entry grows the table
    for slot in free:
        if not 1 <= slot <= 249:
            continue
        out, dslot = _object.seat_entry(eb, entry, loc=LOC, slot=slot)
        if not _motion._stride_problems(out, dslot, "photo daemon"):
            return out, dslot
    raise PhotoError("[photo]: no free entry slot in 1..249 clears THE 64-STRIDE LAW for the photo daemon")


def arm(eb: bytes, raw: dict, *, prop_seats, npc_slots, donor=None, lang: str = "us") -> tuple:
    """Seat and arm the photo daemon (LAST in build_script). ``prop_seats`` = [(prop dict, model, slot)] from the
    build's [[prop]] loop; ``npc_slots`` = {npc name: slot}; ``lang`` = this build's language (the jp daemon tests the
    swapped Cancel bit). Returns (bytes, daemon slot, report lines). Raises :class:`PhotoError` on any law."""
    from . import motion as _motion
    probs = problems(raw, donor=donor)
    if probs:
        raise PhotoError(probs[0])
    spec = parse(raw)
    out = eb
    pl = player_entry(out)
    parts: list = []
    slots = [pl]
    for t, step in enumerate(spec.steps):
        if step == "all":
            continue
        if step == "player":
            targets = [(pl, 250, "player", None)]
        elif _named(raw, "npc", step):
            slot = npc_slots.get(step)
            if slot is None:
                raise PhotoError(f"[photo] hide {step!r}: the [[npc]] was not seated")
            targets = [(slot, slot, step, None)]
        else:
            p = _named(raw, "prop", step)[0][1]
            mine = [(slot, mid) for q, mid, slot in prop_seats if q is p]
            if not mine:
                raise PhotoError(f"[photo] hide {step!r}: the [[prop]] was not seated")
            targets = [(slot, slot, step, mid) for slot, mid in mine]
        for entry, uid, name, model in targets:
            if uid != 250:
                if not 1 <= uid <= 249:
                    raise PhotoError(f"[photo] hide {name!r}: slot {uid} is outside 1..249")
                bad = _target_law(out, entry, name, model) + _motion._stride_problems(out, entry, "hide target")
                if bad:
                    raise PhotoError("[photo] " + "; ".join(bad))
                slots.append(entry)
            ht, st = _free_pair(out, entry)
            out = eb_edit.add_function(out, entry, ht, flag_function(uid, show=False))
            out = eb_edit.add_function(out, entry, st, flag_function(uid, show=True))
            parts.append(Part(step=t, uid=uid, entry=entry, hide_tag=ht, show_tag=st))
    boxes = [b.viewport for b in pan_boxes(raw)]
    entry = entry_bytes(spec, parts, boxes, lang)
    out, dslot = _seat_daemon(out, entry)
    main = EbScript.from_bytes(out).entry(0).func_by_tag(0)
    lasts = []
    for sl in slots:
        hits = [off for e, t, off in _motion._calls(out, _OP_INITOBJ, sl) if (e, t) == (0, 0)]
        if len(hits) != 1:
            raise PhotoError(f"[photo]: hide target slot {sl} must be created by exactly one InitObject in Main_Init, "
                             f"found {len(hits)} (THE ORDER LAW)")
        if sl != pl and out[hits[0] + 2] not in (0, sl):  # InitObject(entry, uid): 0 = the entry's own slot; the
            # player is addressed as uid 250 (controlUID), whatever its InitObject names
            raise PhotoError(f"[photo]: hide target slot {sl} is created with uid {out[hits[0] + 2]} -- photo mode "
                             f"addresses it as uid {sl}")
        lasts.append(hits[0])
    ins = next(i for i in D.iter_code(out, main.abs_start, main.abs_end) if i.off == max(lasts))
    out = eb_edit.insert_in_function(out, 0, 0, ins.end - main.abs_start, opcodes.init_code(dslot, 0))
    bad = _motion.arming_problems(out, dslot, slots, noun="hide target",
                                  why="a hide on tick 0 would RunScriptSync an object that has not run its Init")
    bad += _whole_script_laws(out, dslot, spec)
    if bad:
        raise PhotoError("[photo]: " + "; ".join(bad[:3]))
    return out, dslot, report_lines(spec, parts, boxes, dslot, len(entry), raw)


def report_lines(spec: PhotoSpec, parts, boxes, slot: int, nbytes: int, raw: dict | None = None) -> list:
    """What the build prints: the daemon, each hide step, and what is true of the field's cameras
    (:func:`report_notes`: the pan box at 4:3 and 16:9, a widescreen-pinned X, several cameras, a live ticker)."""
    b = spec.buttons
    steps = ", ".join(spec.steps) if spec.steps else "none"
    out = [f"[photo] daemon entry {slot} ({LOC} B of locals, {nbytes} bytes): open {b['open_button']} after "
           f"{SETTLE} ticks of control, pan {STEP} px/tick, hide {b['hide_button'] if spec.steps else '-'} "
           f"({steps}), grade {b['grade_button'] if spec.grade else 'off'}, close {b['close_button']} + tracking "
           f"release; state = the daemon's own locals"]
    for t, step in enumerate(spec.steps):
        if step == "all":
            out.append(f"[photo] hide {t + 1} 'all': HideAllObjects / ShowAllObjects (chests stay)")
            continue
        mine = [p for p in parts if p.step == t]
        where = ", ".join(f"tags {p.hide_tag}/{p.show_tag} on entry {p.entry}" for p in mine)
        out.append(f"[photo] hide {t + 1} {step!r}: flags ({where})")
    if raw is not None:
        out += report_notes(raw)
    else:
        for k, (lox, hix, loy, hiy) in enumerate(boxes):
            out.append(f"[photo] camera {k}: the pan box X {lox}..{hix}, Y {loy}..{hiy} (4:3)")
    return out
