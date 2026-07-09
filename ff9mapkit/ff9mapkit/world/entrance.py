"""Author a complete custom OVERWORLD ENTRANCE end-to-end -- the one-shot fold of the whole proven flow
(model -> place -> seat -> trigger) into a single call.

An overworld entrance is NOT just an event tile: walking onto a tile whose IDALL event bits are set fires
``ff9.WorldEvent(cellX, cellZ, id)``, which packs a **cell tag** ``0x8000 | (cellZ<<8) | (cellX<<2) | (id&3)`` and
``GetIP``-matches it against **object-0** (entry 0)'s function tags in the loaded world dispatcher ``.eb``. The
matched function sets ``Map.Byte[39] = <case>`` and ``RunScriptAsync(6, 1, 11)`` -> the shared entry-1/tag-1
dispatcher, whose base-2 AREA switch reads that case and emits ``Field(dest)`` (with the proper vehicle / scenario
gating + fade). So a working entrance is THREE things wired together, each of which this module authors:

  1. **the trigger function** -- clone WORLD00's proven Ice-Cavern entrance func (:data:`TEMPLATE_TAG` ``0x9895``,
     29 bytes), patch its single ``Byte[39]=<case>`` literal to the destination case, retag it to the new cell,
     and add it (via :func:`ff9mapkit.eb.edit.add_function`) to EVERY dispatcher whose AREA switch carries that
     case -- deployed to all 7 language folders (the bytecode is language-identical). There are 13 dispatchers
     (``EVT_WORLD_WORLD00..12``) selected by entry/story state, so an entrance authored into only one is dead in
     every other state -- this covers them all.
  2. **the event tile(s)** -- set the terrain tiles in the cell to ``event=<id> area=<case>`` (a loose Terrain
     ``.ff9mesh`` override) so walking there fires ``WorldEvent`` with the matching tag.
  3. **(optional) the building** -- a Blender-modelled OBJ placed + seated in the cell as the Object mesh (the
     visible structure you walk up to), via :func:`ff9mapkit.world.blendio.build_from_obj`.

Everything is a loose override / mod-folder ``.eb`` -- reversible by deleting the printed files (or re-deploying
the journey). Needs the s34 ``WorldMeshOverride`` engine patch for the mesh overrides; the ``.eb`` funcs run on
stock Memoria. In-game proven 2026-07-01 (cell 35,25 -> forked Ice Cavern); this module generalises that spike.
"""
from __future__ import annotations

import glob
import re
import shutil
from pathlib import Path

from .. import config
from . import extract as W, mesh as M

LANGS = ("us", "uk", "jp", "es", "fr", "gr", "it")
TEMPLATE_TAG = 0x9895            # WORLD00 object-0's Ice-Cavern (case 4) entrance func -- the proven clone donor
_BYTE39_PAT = b"\xD5\x27\x7D"    # opD5(39) op7D ... : the Map.Byte[39]=<case> assignment; the case lo byte follows 7D
_WORLD_EB_SUBDIR = "StreamingAssets/assets/resources/commonasset/eventengine/eventbinary/world"
_AREA_SWITCH_BASE = 2
CELL_SIZE = 32                   # a world CELL is 32u (two cells per 64u block per axis)


# --------------------------------------------------------------------------- cell <-> tag <-> block geometry

def pack_cell_tag(cell_x: int, cell_z: int, event: int = 1) -> int:
    """The object-0 function tag that ``ff9.WorldEvent`` GetIP-matches for a walk onto cell ``(cell_x, cell_z)``
    whose event bits == ``event``: ``0x8000 | (cell_z<<8) | (cell_x<<2) | (event&3)``."""
    if not 0 <= cell_x <= 0x3F:
        raise ValueError(f"cell_x {cell_x} out of range 0..63 (6 bits)")
    if not 0 <= cell_z <= 0x7F:
        raise ValueError(f"cell_z {cell_z} out of range 0..127 (7 bits)")
    if not 1 <= event <= 3:
        raise ValueError(f"event {event} out of range 1..3 (0 = not an entrance tile)")
    return 0x8000 | ((cell_z & 0x7F) << 8) | ((cell_x & 0x3F) << 2) | (event & 3)


def unpack_cell_tag(tag: int):
    """``(cell_x, cell_z, event)`` for an object-0 entrance tag, or ``None`` if ``tag`` is not a cell tag
    (top bit unset -- an ordinary object function)."""
    if not tag & 0x8000:
        return None
    return ((tag >> 2) & 0x3F, (tag >> 8) & 0x7F, tag & 3)


def cell_to_block(cell_x: int, cell_z: int) -> tuple:
    """The terrain block ``(x, y)`` that contains cell ``(cell_x, cell_z)`` (32u cells, 64u blocks -> ``//2``)."""
    return (cell_x * CELL_SIZE // W.BLOCK_SIZE, cell_z * CELL_SIZE // W.BLOCK_SIZE)


def cell_world_center(cell_x: int, cell_z: int) -> tuple:
    """The world ``(x, z)`` centre of cell ``(cell_x, cell_z)`` -- ``z`` is negated (``w_worldPos2Cell`` inverse).
    Matches the F6 World-tab cell readout / :func:`ff9mapkit.world.extract.block_world_origin` frame."""
    return (cell_x * CELL_SIZE + CELL_SIZE // 2, -(cell_z * CELL_SIZE + CELL_SIZE // 2))


# --------------------------------------------------------------------------- world dispatchers (the .eb layer)

_WORLD_RE = re.compile(r"eventbinary/world/([a-z]{2})/(evt_world_world\d+)\.eb")


def load_all_dispatchers(game=None) -> dict:
    """``{name: {lang: bytes}}`` for every pristine ``EVT_WORLD_WORLDxx`` in EVERY language, from p0data (p0data7).

    ⚠ The world dispatchers are NOT fully language-identical: JP carries localized inline event dialogue in the
    dispatcher entries and a DIFFERENT byte layout (its ``WORLD00`` is 16 B shorter than US), while uk/es/fr/gr/it
    are code-identical to US (differ only in the header/name region). So an edit MUST patch each language's OWN copy
    -- cloning the US bytecode into ``jp/`` would overwrite the Japanese dialogue. (uk/es/fr/gr/it are safe, but we
    patch them per-lang too, uniformly.)"""
    from ..extract import _unitypy
    _unitypy()
    import UnityPy
    sa = config.find_game_path(game) / "StreamingAssets"
    out: dict = {}
    for p in sorted(glob.glob(str(sa / "p0data*.bin")),
                    key=lambda q: (0 if "p0data7." in Path(q).name else 1, q)):
        try:
            env = UnityPy.load(p)
        except Exception:                                # noqa: BLE001 -- odd/non-bundle file, keep scanning
            continue
        for o in env.objects:
            if o.type.name != "TextAsset":
                continue
            m = _WORLD_RE.search((getattr(o, "container", None) or "").lower())
            if not m:
                continue
            lang, name = m.group(1), m.group(2)
            s = o.read().m_Script
            out.setdefault(name, {})[lang] = s.encode("utf-8", "surrogateescape") if isinstance(s, str) else bytes(s)
        if out:
            break
    if not out:
        raise ValueError("no EVT_WORLD_WORLDxx dispatchers found in StreamingAssets/p0data*.bin "
                         "-- is this a full FF9 install?")
    return out


def load_world_dispatchers(game=None) -> dict:
    """``{name: us_bytes}`` -- the US view of :func:`load_all_dispatchers` (the entrance-func template + the case
    coverage are language-independent, so US is the reference). The per-language deploy uses ``load_all_dispatchers``."""
    return {name: langs["us"] for name, langs in load_all_dispatchers(game).items() if "us" in langs}


def dispatcher_cases(dispatcher_bytes: bytes):
    """The set of base-2 AREA-switch case values in a dispatcher's entry-1/tag-1 function, or ``None`` if it has no
    such switch (a tiny cutscene-state dispatcher). A destination case is only reachable in dispatchers that carry it."""
    from ..eb.model import EbScript
    from ..eb import disasm as D
    s = EbScript(dispatcher_bytes)
    try:
        f1 = next(f for f in s.entry(1).funcs if f.tag == 1)
    except StopIteration:
        return None
    for i in D.iter_code(s.data, f1.abs_start, f1.abs_end):
        if i.is_switch:
            si = D.decode_switch(i) or i.switch()
            if si and si.base == _AREA_SWITCH_BASE:
                return {ed.value for ed in si.edges if not ed.is_default}
    return None


# --------------------------------------------------------------------------- the trigger function body

def byte39_value(body: bytes):
    """Read the ``Map.Byte[39] = <case>`` literal an entrance-function body assigns (via disasm), or ``None``."""
    from ..eb import disasm as D
    for i in D.iter_code(body, 0, len(body)):
        if i.op == 0x05 and i.args:
            m = re.search(r"opD5\(39\)\s+op7D\((\d+),(\d+)\)", str(i.args[0]))
            if m:
                return int(m.group(1)) + int(m.group(2)) * 256
    return None


def patch_byte39(body: bytes, case: int) -> bytes:
    """Return ``body`` with its ``Map.Byte[39] = <case>`` destination literal rewritten to ``case``. The literal is
    the ``op7D`` immediate right after the unique ``opD5(39)`` (bytes ``D5 27 7D <lo> <hi>``); ``case`` (a switch
    case, 0-63) fits the low byte. Raises if the assignment is missing or not unique (a wrong template)."""
    if not 0 <= case <= 0xFFFF:
        raise ValueError(f"case {case} out of range 0..65535")
    b = bytearray(body)
    idx = b.find(_BYTE39_PAT)
    if idx < 0 or b.find(_BYTE39_PAT, idx + 1) != -1:
        raise ValueError("entrance-func template: the Map.Byte[39] literal (D5 27 7D) is missing or not unique")
    b[idx + 3] = case & 0xFF
    b[idx + 4] = (case >> 8) & 0xFF
    out = bytes(b)
    got = byte39_value(out)
    if got != case:
        raise ValueError(f"patched Byte[39] reads back as {got}, expected {case}")
    return out


def entrance_func_body(case: int, *, game=None, dispatchers=None) -> bytes:
    """The trigger-function body for a destination ``case``: WORLD00's :data:`TEMPLATE_TAG` body, patched so it sets
    ``Map.Byte[39] = case``. Portable across dispatchers (references only globals + RunScriptAsync)."""
    from ..eb.model import EbScript
    disp = dispatchers if dispatchers is not None else load_world_dispatchers(game)
    w00 = EbScript(disp["evt_world_world00"])
    f = w00.entry(0).func_by_tag(TEMPLATE_TAG)
    if f is None:
        raise ValueError(f"WORLD00 has no template entrance func 0x{TEMPLATE_TAG:04X}")
    return patch_byte39(w00.data[f.abs_start:f.abs_end], case)


# --------------------------------------------------------------------------- destination resolution

def resolve_destination(*, field=None, case=None, game=None) -> dict:
    """Resolve the destination to a base-2 AREA-switch ``case`` (== the ``Byte[39]`` value) + its default field.

    ``case`` given -> validate it exists in WORLD00's switch, report its field. ``field`` given -> invert the
    dispatch table (prefer a case whose ``default`` branch leads there). Returns ``{case, field, note}``."""
    from .locate import area_to_fields
    a2f = area_to_fields(game=game)
    if case is not None and field is not None:
        raise ValueError("give a destination as EITHER field=<id> OR case=<n>, not both")
    if case is not None:
        if case not in a2f:
            raise ValueError(f"case {case} is not a live overworld dispatch case (see `world-locate`)")
        default = next((f for c, f in a2f[case] if c == "default"), None)
        return {"case": case, "field": default, "note": f"case {case} -> {a2f[case]}"}
    if field is not None:
        cands = [(c, cond) for c, branches in a2f.items() for cond, f in branches if f == field]
        if not cands:
            reachable = sorted({f for br in a2f.values() for _, f in br if f is not None})
            raise ValueError(f"no overworld dispatch case leads to field {field}. Reachable base fields: "
                             f"{reachable}. (Fork/journey redirects happen at the engine level -- author the "
                             f"entrance to the BASE field and let field_remap/s28 send it to your fork.)")
        default_cases = [c for c, cond in cands if cond == "default"]
        chosen = (sorted(default_cases) or sorted(c for c, _ in cands))[0]
        note = f"field {field} <- case {chosen}"
        if len(set(c for c, _ in cands)) > 1:
            note += f" (ambiguous; also cases {sorted(set(c for c, _ in cands))} -- picked {chosen})"
        return {"case": chosen, "field": field, "note": note}
    raise ValueError("give a destination: field=<id> or case=<n>")


# --------------------------------------------------------------------------- stacked block reads (compose edits)

def read_block_stacked(mod_folder: str, x: int, y: int, *, disc: int = 1, lod: str = "0_1", part: str = "terrain",
                       game=None, missing_ok: bool = False, fresh: bool = False):
    """Read block ``(x, y)``'s ``part`` mesh, preferring an already-deployed mod-folder ``.ff9mesh`` OVERRIDE (so a
    new edit stacks on a prior one) and falling back to the pristine p0data block. ``fresh=True`` IGNORES the override
    and reads pristine -- for re-iterating a block cleanly (GEOMETRY edits like a flatten pad / a kept building would
    otherwise COMPOUND on re-run). ``missing_ok`` returns ``None`` when neither exists (a block with no stock mesh)."""
    if not fresh:
        dest = config.find_game_path(game) / mod_folder / M.override_relpath(disc, x, y, lod, part.capitalize())
        if dest.is_file():
            return M.blockmesh_from_ff9mesh(dest, disc=disc, x=x, y=y, lod=lod, part=part)
    try:
        return W.read_block(x, y, disc=disc, lod=lod, part=part, game=game)
    except (ValueError, FileNotFoundError):
        if missing_ok:
            return None
        raise


# --------------------------------------------------------------------------- the one-shot author

def _timestamp() -> str:
    import time
    return time.strftime("%Y%m%d-%H%M%S")


# on-foot walkable topographs, decoded from Memoria's on-foot control limit {0x0010667F, 0xD8FF3CFF} (ff9.cs:1487):
# w_movementCheckTopographID tests bit `topo` of the 64-bit mask (check[0]=topo 32-63, check[1]=topo 0-31).
_WALK_TOPO = frozenset(t for t in range(64)
                       if (((0x0010667F >> (t - 32)) & 1) if t >= 32 else ((0xD8FF3CFF >> t) & 1)))


def _cell_openness_note(ter, cwx, cwz, ox, oz, summary, stock_obj=None):
    """Warn if the entrance cell is a POOR spot: much BLOCKED terrain (topo not on-foot-walkable = river/cliff) or an
    existing building/town collision beside it -- both pinch a trap-pocket around a placed structure (the cell-(35,25)
    soft-lock: 34% topo-49 river + Dali town adjacent). A good entrance cell is open walkable land."""
    from .extract import decode_id
    walk = blocked = 0
    for tri in ter.tris:
        cx = (ter.verts[tri[0]][0] + ter.verts[tri[1]][0] + ter.verts[tri[2]][0]) / 3.0 + ox
        cz = (ter.verts[tri[0]][2] + ter.verts[tri[1]][2] + ter.verts[tri[2]][2]) / 3.0 + oz
        if abs(cx - cwx) <= 16 and abs(cz - cwz) <= 16:
            if decode_id(int(round(ter.tangents[tri[0]][0])))["topograph"] in _WALK_TOPO:
                walk += 1
            else:
                blocked += 1
    total = walk + blocked
    if total and blocked / total > 0.20:
        summary.setdefault("notes", []).append(
            f"POOR SPOT: the entrance cell is {100 * blocked / total:.0f}% BLOCKED terrain (topo not on-foot-"
            f"walkable -- river/cliff); the player may get trapped. Prefer an open, all-walkable cell.")
    if stock_obj is not None:
        near = 0
        for tri in stock_obj.tris:
            if decode_id(int(round(stock_obj.tangents[tri[0]][0])))["topograph"] == 59:
                cx = (stock_obj.verts[tri[0]][0] + stock_obj.verts[tri[1]][0] + stock_obj.verts[tri[2]][0]) / 3.0 + ox
                cz = (stock_obj.verts[tri[0]][2] + stock_obj.verts[tri[1]][2] + stock_obj.verts[tri[2]][2]) / 3.0 + oz
                if abs(cx - cwx) <= 22 and abs(cz - cwz) <= 22:
                    near += 1
        if near:
            summary.setdefault("notes", []).append(
                f"POOR SPOT: an existing town/building ({near} collision tiles) is beside this cell -- placing a "
                f"structure here can pinch a trap-pocket against it. Prefer an open cell away from towns.")


def _building_world_box(building, default_at, margin: float = 2.0):
    """The world-XZ bounding box ``(xmin, xmax, zmin, zmax)`` a building occupies once placed (its XZ centroid at its
    ``at`` / ``default_at``), padded by ``margin``. Entrance-trigger tiles are kept OUT of this box so the player never
    triggers from UNDER the impassable structure (which would box them in -- the soft-lock the castle caused)."""
    from . import blendio as BIO
    ov = BIO.read_obj(building["obj"])["V"]
    if not ov:
        return None
    at = tuple(building["at"]) if building.get("at") else default_at
    xs = [v[0] for v in ov]; zs = [v[2] for v in ov]
    bcx = (min(xs) + max(xs)) / 2.0; bcz = (min(zs) + max(zs)) / 2.0   # bbox centre (matches build_from_obj's anchor)
    return (at[0] + (min(xs) - bcx) - margin, at[0] + (max(xs) - bcx) + margin,
            at[1] + (min(zs) - bcz) - margin, at[1] + (max(zs) - bcz) + margin)


def _building_world_hull(building, default_at):
    """The building's XZ CONVEX HULL in WORLD coords (its centroid placed at ``at``/``default_at``) -- the tight
    outline of the structure, so the footprint block matches the VISIBLE castle instead of a padded bounding box
    (which leaves an invisible collision skirt beyond the towers). Returns a list of ``(x, z)`` or ``None``."""
    from . import blendio as BIO, mesh as M
    ov = BIO.read_obj(building["obj"])["V"]
    if not ov:
        return None
    at = tuple(building["at"]) if building.get("at") else default_at
    xs = [v[0] for v in ov]; zs = [v[2] for v in ov]
    bcx = (min(xs) + max(xs)) / 2.0; bcz = (min(zs) + max(zs)) / 2.0   # bbox centre (matches build_from_obj's anchor)
    hull = M._convex_hull_xz([(v[0], v[2]) for v in ov])
    return [(at[0] + (hx - bcx), at[1] + (hz - bcz)) for (hx, hz) in hull] or None


def _capped_flatten_radius(requested: float, building, summary: dict) -> float:
    """Cap a ``--flatten-pad`` radius to the building's XZ footprint so the flattened (step-prone) ground stays UNDER
    the impassable structure. A flatten pad WIDER than the building leaves flat ground meeting the bumpy natural
    terrain out in the WALKABLE approach -- an edge step you can walk down into but (the overworld only raycasts DOWN)
    can't climb back out of = stuck. With ``radius == footprint`` the smoothstep falloff reaches natural terrain
    exactly at the building perimeter, so nothing walkable has a step. Records a note when it caps / when there's no
    building to hide the pad."""
    if not building:
        summary.setdefault("notes", []).append(
            "flatten-pad with no --building reshapes WALKABLE ground -- its edge is a step you can get stuck on; "
            "prefer seating the structure (no flatten) or add a building to cover the pad")
        return requested
    from . import blendio as BIO
    ov = BIO.read_obj(building["obj"])["V"]
    if not ov:
        return requested
    # The building seats with its XZ CENTROID at the pad centre; the pad must stay under it on EVERY side, so the
    # safe radius is the INSCRIBED circle from the centroid to the footprint's bounding box (min extent), NOT the max
    # corner distance -- an asymmetric structure (wide in X, shallow in Z) would otherwise leave the pad poking past
    # its narrow sides into walkable ground (the stuck-step).
    xs = [v[0] for v in ov]; zs = [v[2] for v in ov]
    bcx = sum(xs) / len(xs); bcz = sum(zs) / len(zs)
    foot_r = min(bcx - min(xs), max(xs) - bcx, bcz - min(zs), max(zs) - bcz)
    if requested > foot_r:
        summary.setdefault("notes", []).append(
            f"flatten-pad {requested:.0f} capped to the building's inscribed footprint {foot_r:.1f} -- a wider flat "
            f"pad pokes past the structure into walkable ground, leaving an edge-step you get stuck on. (Seating "
            f"alone usually suffices; the building skirt hides a small float.)")
        return foot_r
    return requested


def author_entrance(*, cell, mod_folder: str, field=None, case=None, event: int = 1, disc: int = 1, lod: str = "0_1",
                    trigger_at=None, trigger_radius: float = 14.0, set_tile_area: bool = True,
                    building=None, flatten_pad=None, block_footprint: bool = True, fresh: bool = False,
                    backup_dir=None, dry_run: bool = False, game=None) -> dict:
    """Author + deploy a complete overworld entrance at ``cell=(cell_x, cell_z)`` into ``mod_folder``.

    Destination: ``field=<id>`` (resolved to a dispatch case) or ``case=<n>`` (raw). ``event`` is the tile trigger
    id (1-3). ``trigger_at``/``trigger_radius`` place the event-tile cluster (default: the cell centre, r=14, kept
    inside the 32u cell). ``building`` (a dict ``{obj, at?, seat?, keep_block?, topograph?}``) additionally models +
    seats a structure in the cell. ``block_footprint`` (default True) makes the TERRAIN under the building impassable
    (topo 59) so the player stops at its edge and can't wander into a hollow model's interior and get boxed -- the
    terrain conforms to the ground, so it blocks reliably where a flat prop base would bury/float on uneven land.
    ``flatten_pad=radius`` optionally flattens a pad under the building. ``fresh`` re-reads the block from pristine
    p0data (ignoring a prior deployed override) so re-doing a block doesn't COMPOUND. ``dry_run`` reports the plan."""
    from ..eb.model import EbScript
    from ..eb import edit as E

    game_path = config.find_game_path(game)
    cell_x, cell_z = cell
    tag = pack_cell_tag(cell_x, cell_z, event)
    bx, by = cell_to_block(cell_x, cell_z)
    cwx, cwz = cell_world_center(cell_x, cell_z)

    if building and not Path(building["obj"]).is_file():   # fail BEFORE any write, so a bad path can't half-deploy
        raise ValueError(f"--building OBJ not found: {building['obj']}")

    alld = load_all_dispatchers(game)                      # {name: {lang: bytes}} -- per-lang (JP layout differs)
    us_disp = {n: L["us"] for n, L in alld.items() if "us" in L}
    dest = resolve_destination(field=field, case=case, game=game)
    the_case = dest["case"]
    body = entrance_func_body(the_case, dispatchers=us_disp)   # the func body is pure logic -> language-independent

    # dispatchers whose AREA switch carries this case (the states the entrance can fire in)
    targets = sorted(name for name, L in alld.items()
                     if "us" in L and (cases := dispatcher_cases(L["us"])) is not None and the_case in cases)
    if not targets:
        raise ValueError(f"no world dispatcher carries case {the_case} -- cannot route this entrance")

    eb_root = game_path / mod_folder / _WORLD_EB_SUBDIR
    summary = {
        "cell": [cell_x, cell_z], "tag": tag, "tag_hex": f"0x{tag:04X}", "block": [bx, by],
        "case": the_case, "field": dest["field"], "dest_note": dest["note"], "event": event,
        "cell_center": [cwx, cwz], "dispatchers_all": targets, "langs": list(LANGS),
        "dispatchers_written": [], "dispatchers_skipped": [], "backups": [], "dry_run": dry_run,
    }

    # (1) the trigger function -> every carrying dispatcher, patched into EACH language's OWN base (stacking on any
    #     existing mod-folder .eb). Per-lang because JP's dispatcher carries localized dialogue + a distinct layout.
    bkdir = Path(backup_dir) if backup_dir else (Path.cwd() / "backups" / "world-entrance")
    for name in targets:
        fname = name.upper() + ".eb.bytes"
        us_mod = eb_root / "us" / fname
        us_base = us_mod.read_bytes() if us_mod.is_file() else alld[name]["us"]
        if EbScript.from_bytes(us_base).entry(0).func_by_tag(tag) is not None:
            summary["dispatchers_skipped"].append(name)                    # cell already has an entrance here
            continue
        out_by_lang = {}                                                   # patch each lang's own base (stack if present)
        for lang in LANGS:
            lang_mod = eb_root / lang / fname
            base_l = lang_mod.read_bytes() if lang_mod.is_file() else alld[name].get(lang, alld[name]["us"])
            out_by_lang[lang] = E.add_function(base_l, 0, tag, body)
        if not dry_run:
            if us_mod.is_file():                                           # back up the pre-edit representative
                bkdir.mkdir(parents=True, exist_ok=True)
                bk = bkdir / f"{name.upper()}.us.{_timestamp()}.eb.bytes"
                shutil.copy2(us_mod, bk)
                summary["backups"].append(str(bk))
            for lang in LANGS:
                p = eb_root / lang / fname
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(out_by_lang[lang])
        summary["dispatchers_written"].append({"name": name, "base_len": len(us_base),
                                               "out_len": len(out_by_lang["us"])})

    # (2) event tile(s) on the cell's terrain block (+ optional flatten pad under the building), stacked
    ter = read_block_stacked(mod_folder, bx, by, disc=disc, lod=lod, part="terrain", game=game, fresh=fresh)
    try:                                                    # WARN if the cell is a poor spot (river/cliff or a town)
        _stock_obj = W.read_block(bx, by, disc=disc, lod=lod, part="object", game=game)
    except (ValueError, FileNotFoundError):
        _stock_obj = None
    _cell_openness_note(ter, cwx, cwz, *W.block_world_origin(bx, by), summary, stock_obj=_stock_obj)
    at = tuple(trigger_at) if trigger_at else (cwx, cwz)
    n_flat = 0
    if flatten_pad:
        pad_at = tuple(building["at"]) if (building and building.get("at")) else (cwx, cwz)
        eff_r = _capped_flatten_radius(float(flatten_pad), building, summary)
        pad_h = M.sample_ground_y(ter, pad_at[0] - bx * W.BLOCK_SIZE, pad_at[1] + by * W.BLOCK_SIZE)
        n_flat = M.flatten_region(ter, radius=eff_r, center=pad_at, height=pad_h,
                                  world_origin=W.block_world_origin(bx, by))
        M.recompute_normals(ter)
        summary["flatten_radius"] = eff_r
    hull = _building_world_hull(building, (cwx, cwz)) if building else None   # the building's tight world outline
    n_block = 0
    if hull and block_footprint:                            # make the terrain UNDER the building impassable (conforms
        from .extract import decode_id                       # to the ground; the tight HULL avoids an invisible skirt)
        # split_retarget_by_polygon (not the whole-triangle-centroid retarget_tiles) so the
        # blocked boundary traces the hull EXACTLY -- a real donor terrain triangle can be far
        # bigger than a small building footprint, and a centroid test over/under-shoots the
        # visible edge by up to half a triangle ("some collision, but not aligned", 2026-07-09)
        ter = M.split_retarget_by_polygon(ter, hull, topograph=59,
                                          world_origin=W.block_world_origin(bx, by))
        n_block = sum(1 for tri in ter.tris
                     if decode_id(int(round(ter.tangents[tri[0]][0])))["topograph"] == 59)
    n_tiles = M.retarget_tiles(ter, event=event, area=(the_case if set_tile_area else None),
                               center=at, radius=trigger_radius, world_origin=W.block_world_origin(bx, by),
                               exclude_polygon=hull)         # triggers OUTSIDE the building outline (walkable beside it)
    summary["tiles_set"] = n_tiles
    summary["footprint_blocked"] = n_block
    summary["pad_flattened"] = n_flat
    if hull:
        summary["building_hull_pts"] = len(hull)
    if not dry_run:
        summary["terrain_override"] = str(M.deploy_override(ter, mod_folder=mod_folder, game=game, lod=lod,
                                                            part="Terrain"))
    if n_tiles == 0:
        summary["warning"] = (f"no terrain tiles matched at {at} r{trigger_radius} in block[{bx}][{by}] -- the "
                              f"trigger will never fire (widen --trigger-radius or check --trigger-at/--cell)")

    # (3) optional building -> Object mesh in the cell (seated on the possibly-flattened terrain, stacked on stock)
    if building:
        b_at = tuple(building["at"]) if building.get("at") else (cwx, cwz)
        keep = building.get("keep_block", True)
        if dry_run:
            summary["building"] = {"obj": building["obj"], "at": list(b_at), "seat": building.get("seat", True),
                                   "keep_block": keep, "topograph": building.get("topograph", 59), "planned": True}
        else:
            from . import blendio as BIO
            stock = read_block_stacked(mod_folder, bx, by, disc=disc, lod=lod, part="object", game=game,
                                       missing_ok=True, fresh=fresh) if keep else None
            summary["building"] = BIO.build_from_obj(
                building["obj"], into_block=(bx, by), mod_folder=mod_folder, disc=disc, part="object", lod=lod,
                topograph=building.get("topograph", 59), at=b_at, seat=building.get("seat", True),
                keep_block=keep, solid_base=building.get("solid_base", False), stock_bm=stock, terrain_bm=ter,
                game=game)
    return summary
