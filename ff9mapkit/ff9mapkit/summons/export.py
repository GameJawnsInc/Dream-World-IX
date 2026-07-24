"""The user-facing OFFLINE export surface for the summon-transplant study (TRANSPLANT.md section 3.3 /
milestone ladder rung 2): turn a caller-supplied stock ``ef###.bytes`` creature into a Blender-openable
glTF ``.glb``.

Two exporters, both driving the kit's own proven glTF writer (``models.gltf.emit_model_gltf``) so a summon
reuses every bit of the model edit loop's emission machinery without touching its p0data reads:

  * :func:`export_summon_glb` -- the FULL creature: skeleton (``bone000..bone09N``) + rigid one-bone-per-
    vertex skinned mesh + every decoded motion clip, so a modder can open, scrub and study the real dragon.
  * :func:`export_rig_ref`   -- the 93-bone RIG REFERENCE only (skeleton + rest pose + ``bone{NNN:D3}``
    names, NO stock mesh, NO clips) -- the armature the user skins their OWN mesh onto for the hybrid /
    baked-clip transplant (TRANSPLANT.md section 2.2). Same rig as the full export, geometry stripped.

PROVENANCE (TRANSPLANT.md section 5, STRICT): this module is committable CODE -- it reads a caller-supplied
LOCAL blob (a stock ``ef###.bytes`` the user extracted from their OWN install, kept only under
``C:/gd/SCRATCH/...``) and embeds zero game bytes. But its OUTPUT is stock-derived Square-Enix content (the
dragon's mesh / rig / baked clips), so both exporters DEFAULT their output under
:data:`DEFAULT_OUT_DIR` (``C:/gd/SCRATCH/summon-transplant/``) and REFUSE (:class:`SummonExportError`) any
output path inside a committable/distributable location -- the git repo tree, a Memoria mod folder
(a ``StreamingAssets`` tree), or the FF9 install. There is deliberately NO ``--force`` override: a
stock-creature export must never land somewhere it could be committed or shipped.
"""
from __future__ import annotations

import struct
from pathlib import Path
from typing import List, Optional, Tuple

from .. import config
from ..models import gltf as _gltf
from ..models._gltf_io import GltfBuffer
from . import build, container, motion

__all__ = [
    "SummonExportError", "DEFAULT_OUT_DIR", "DEFAULT_SCALE", "DEFAULT_FPS",
    "assert_local_only", "default_out",
    "export_summon_glb", "export_rig_ref",
]

# The local, gitignored home for every stock-derived summon export (TRANSPLANT.md section 5). Not inside any
# repo, mod folder, or the FF9 install -- so the guard below never refuses the default.
DEFAULT_OUT_DIR = Path(r"C:/gd/SCRATCH/summon-transplant")
DEFAULT_SCALE = _gltf.DEFAULT_SCALE           # 0.01 -- FF9's hundreds-of-units models -> a few Blender metres
DEFAULT_FPS = build.DEFAULT_FPS               # 15.0 -- a preview playback default, not a measured tick rate


class SummonExportError(RuntimeError):
    """Raised for a bad blob (no creature package / parser drift) or a refused output path."""


# --------------------------------------------------------------------------- the local-only WRITE guard
_REFUSE_MSG = (
    "refusing to write a stock-creature export to {out}\n"
    "  ({why}).\n"
    "  A summon export is Square-Enix content -- it must stay LOCAL (the default is {default}).\n"
    "  Point --out somewhere outside the repo / a mod folder / the FF9 install, or drop the flag to use "
    "the default. (There is no --force: this is a provenance rule, not a safety prompt.)"
)


def _within(child: Path, parent: Path) -> bool:
    """True if ``child`` is ``parent`` or lives under it (pure path test, no I/O)."""
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def assert_local_only(out_path) -> Path:
    """Refuse a stock-creature export bound for a committable / distributable location; else return the
    resolved output path. A location is refused when it is:

      1. inside a git repo (any ancestor holds a ``.git`` file OR dir -- catches the kit itself, this
         worktree, and any other checkout, without hardcoding the repo root);
      2. inside a Memoria mod folder -- any ``StreamingAssets`` segment on the path; or
      3. inside the resolved FF9 install (when one is resolvable; absent an install, checks 1+2 stand).

    The default :data:`DEFAULT_OUT_DIR` passes all three by construction.
    """
    p = Path(out_path).resolve()
    for anc in (p, *p.parents):                          # 1) a git checkout == committable source tree
        if (anc / ".git").exists():
            raise SummonExportError(_REFUSE_MSG.format(
                out=p, why=f"inside the git repo at {anc}", default=DEFAULT_OUT_DIR))
    if any(seg.lower() == "streamingassets" for seg in p.parts):   # 2) a mod folder
        raise SummonExportError(_REFUSE_MSG.format(
            out=p, why="inside a Memoria mod folder (a StreamingAssets tree)", default=DEFAULT_OUT_DIR))
    try:                                                  # 3) the FF9 install (best-effort -- may be absent)
        game = config.find_game_path().resolve()
    except config.ConfigError:
        game = None
    if game is not None and _within(p, game):
        raise SummonExportError(_REFUSE_MSG.format(
            out=p, why=f"inside the FF9 install at {game}", default=DEFAULT_OUT_DIR))
    return p


def default_out(ef_bytes_path, *, rig: bool = False) -> Path:
    """The default local output path for an ``ef###.bytes`` input: ``<DEFAULT_OUT_DIR>/<stem>[_rig].glb``."""
    stem = Path(ef_bytes_path).stem
    return DEFAULT_OUT_DIR / f"{stem}{'_rig' if rig else ''}.glb"


# --------------------------------------------------------------------------- shared read + rest-pose helper
def _read_creature(ef_bytes_path) -> Tuple[bytes, "container.ModelPackage", "container.Geom"]:
    """Read the local blob and reach its creature package + GEOM, or raise :class:`SummonExportError`."""
    try:
        blob = Path(ef_bytes_path).read_bytes()
    except OSError as e:
        raise SummonExportError(f"cannot read {ef_bytes_path}: {e}") from e
    try:
        mp = container.creature_package(blob)
        if mp is None:
            raise SummonExportError(
                f"{ef_bytes_path} carries no creature (no id-4 + id-5 model package) -- it is not a "
                f"summon-creature effect. Try a creature effect like ef227 (Bahamut) / ef261 (Odin).")
        g = container.creature_geom(blob, mp)
    except (container.ContainerError, struct.error) as e:
        raise SummonExportError(f"{ef_bytes_path}: not a well-formed ef###.bytes container ({e})") from e
    return blob, mp, g


def _rest_angles(blob: bytes, g: "container.Geom", mp: "container.ModelPackage",
                 rest: str) -> Optional[List[Tuple[int, int, int]]]:
    """Resolve the ``rest`` knob to a per-node angle list (or None = identity). TRANSPLANT.md 3.1's
    "clip[0]f0" option gives a recognizable posed dragon instead of the straight-identity default."""
    if rest in (None, "", "identity"):
        return None
    if rest == "clip0":
        if mp.motion_count == 0:
            raise SummonExportError("rest='clip0' needs at least one motion clip, but this creature has none")
        clip0 = motion.read_clip_header(blob, 0, mp.motion_file_offsets[0])
        return build.rest_angles_from_clip(blob, g.bone_count, clip0, frame=0)
    raise SummonExportError(f"rest must be 'identity' or 'clip0' (got {rest!r})")


def _select_clips(blob: bytes, mp: "container.ModelPackage", bone_count: int, geo_id: int, anims,
                  fps: float) -> list:
    """Which motion clips to embed -> the ``[(label, key, folder, clip)]`` tuple list
    ``models.gltf.emit_model_gltf`` consumes. ``folder == geo_id`` (a summon clip is never a donor-folder
    redirect, so it is never marked as one in the manifest). ``anims`` is 'all'/'auto' (every clip, file
    order), 'none'/'off' (no clips), or a comma/space list of clip INDICES."""
    if anims in (None, "none", "off"):
        return []
    decoded = build.adapt_all_clips(blob, mp, bone_count, fps=fps)     # every clip, in file order
    if anims in ("all", "auto", "", "default"):
        sel = list(range(len(decoded)))
    else:
        sel = []
        for tok in str(anims).replace(",", " ").split():
            if not tok.isdigit():
                raise SummonExportError(
                    f"--anims for a summon takes clip INDICES (0..{len(decoded) - 1}), 'all', or 'none' -- "
                    f"got {tok!r}")
            i = int(tok)
            if not (0 <= i < len(decoded)):
                raise SummonExportError(f"clip index {i} out of range (this creature has {len(decoded)} clips)")
            sel.append(i)
    return [(decoded[i]["name"], i, geo_id, decoded[i]) for i in sel]


# --------------------------------------------------------------------------- the two exporters
def export_summon_glb(ef_bytes_path, out_path, *, geo: str = "SUMMON", geo_id: int = 0, anims="all",
                      scale: float = DEFAULT_SCALE, rest: str = "identity", fps: float = DEFAULT_FPS,
                      bone_labels: bool = False) -> dict:
    """Export a stock summon creature ``ef###.bytes`` -> a Blender-openable ``.glb`` (skeleton + skinned
    mesh + motion clips). ``out_path`` is guarded LOCAL-ONLY (:func:`assert_local_only`). Returns the
    :func:`~ff9mapkit.models.gltf.emit_model_gltf` manifest, extended with ``clip_frames`` / ``rest`` /
    ``creature`` (``clip_frames`` and ``creature['clips']`` count only the clips actually EMBEDDED in the
    ``.glb`` -- a 1-frame clip carries no animation channel and is dropped, so both agree with ``anims``).
    ``anims`` = 'all' / 'none' / a clip-index list; ``rest`` = 'identity' / 'clip0';
    ``bone_labels`` off by default (raw ``bone{NNN:D3}`` names the retarget binds by)."""
    out = assert_local_only(out_path)
    blob, mp, g = _read_creature(ef_bytes_path)
    rest_angles = _rest_angles(blob, g, mp, rest)
    model = build.adapt_model(blob, g, geo=geo, geo_id=geo_id, rest_angles=rest_angles)
    clips = _select_clips(blob, mp, g.bone_count, geo_id, anims, fps)
    man = _gltf.emit_model_gltf(model, clips, GltfBuffer(), out, scale=scale, bone_labels=bone_labels)
    # emit_model_gltf DROPS any clip that yields no animation channel -- a rotation channel needs >=2 keys, so
    # a 1-frame clip embeds nothing (3 of the 24 stock creatures carry such clips: ef381 has 4, ef184/ef447
    # are single 1-frame clips). Report clip_frames / creature.clips over ONLY the clips that actually reached
    # the .glb (``man["anims"]``, matched by the summon clip's unique "clip{i}" label), so clip_frames,
    # creature.clips, ``man["anims"]`` and the .glb's animation count all agree -- a caller can enumerate the
    # embedded clips from any of them without over-counting the dropped 1-frame clips.
    embedded = set(man["anims"])
    kept = [c for _l, _k, _f, c in clips if _l in embedded]
    man["clip_frames"] = [len(c["bones"]["bone000"]["rot"]) for c in kept]
    man["rest"] = "identity" if rest_angles is None else rest
    man["creature"] = {"bones": g.bone_count, "meshes": g.mesh_count,
                       "verts": sum(m.n_vert for m in g.meshes), "clips": len(kept)}
    return man


def export_rig_ref(ef_bytes_path, out_path, *, geo: str = "SUMMON", geo_id: int = 0, rest: str = "identity",
                   scale: float = DEFAULT_SCALE, bone_labels: bool = False) -> dict:
    """Export ONLY the summon's rig reference -> a ``.glb`` with the N-bone skeleton (``bone{NNN:D3}``
    names, parent tree, rest pose) and NO stock mesh, NO clips -- the armature the user skins their own
    mesh onto (TRANSPLANT.md section 2.2). Same rig the full export carries, geometry stripped; still
    stock-derived, so ``out_path`` is guarded LOCAL-ONLY. Returns the emit manifest (``meshes`` == 0)."""
    out = assert_local_only(out_path)
    blob, mp, g = _read_creature(ef_bytes_path)
    rest_angles = _rest_angles(blob, g, mp, rest)
    model = build.adapt_model(blob, g, geo=geo, geo_id=geo_id, rest_angles=rest_angles)
    model = dict(model)
    model["meshes"] = []                                  # skeleton-only: strip the stock geometry + materials
    model["materials"] = []
    man = _gltf.emit_model_gltf(model, [], GltfBuffer(), out, scale=scale, bone_labels=bone_labels)
    man["rest"] = "identity" if rest_angles is None else rest
    man["creature"] = {"bones": g.bone_count, "meshes": 0, "verts": 0, "clips": 0}
    return man
