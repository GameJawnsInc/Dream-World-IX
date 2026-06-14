"""Compile a battle.toml into a Memoria mod (custom battle map). Offline + deterministic (stdlib only).

Mirrors build.FieldProject / build.build_mod. A battle map ships as a loose FBX (+ image#.png textures)
at ModLayout.battlemap_dir(bbg); registration has three modes:
  * default  -- bbg = an existing real slot -> the FBX OVERRIDES that map (no patch line, no relaunch).
  * repoint  -- repoint_scene = <id> -> a BattlePatch.txt 'BattleBackground' line points that scene's bg
                at `bbg` (relaunch).
  * MINT (tier c, in-game proven) -- scene_id + scene_name + a forked `scene/` dir (raw16/raw17/eb/mes,
                produced by `battle-import --fork-scene`) -> a net-new, independently-triggerable battle:
                a DictionaryPatch 'BattleScene <id> <NAME> <BBG>' line + the scene's gameplay/sequence/
                camera/text assets, and (for a new BBG_B<N> number) a static INB. No camera authoring is
                needed -- the donor's raw17 carries a working camera. Trigger it with a field encounter
                pointing at scene_id (deploy_battle.py --trigger-field, or a field.toml [encounter]).

The scene assets are SE-derived (forked from the user's install into a gitignored project dir); this
module only COPIES them, staying stdlib-only. The INB is authored here (pure struct.pack).
"""
from __future__ import annotations

import re
import shutil
import struct
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from ..config import LANGS, ModLayout
from . import camera_codec as _camera_codec
from . import camera_data as _camera_data
from . import event_data as _event_data
from . import fbx as _fbx
from . import scene_codec as _scene_codec
from . import scene_data as _scene_data
from . import scenelint as _scenelint

_BBG_RE = re.compile(r"^BBG_[A-Z]\d+$")
# Real shipping battle maps are BBG_B001..177; a NEW number (>= this) = a wholly custom map that needs
# its own static INB authored. Below it, a mint reuses the real slot's bundled INB.
_REAL_BBG_MAX = 177


class BattleBuildError(RuntimeError):
    pass


def _bbg_number(bbg: str) -> int:
    return int(re.sub(r"\D", "", bbg.split("_")[-1]))     # 'BBG_B200' -> 200


@dataclass
class BattleProject:
    raw: dict
    base_dir: Path

    @classmethod
    def load(cls, toml_path) -> "BattleProject":
        p = Path(toml_path)
        with p.open("rb") as fh:
            raw = tomllib.load(fh)
        return cls(raw, p.parent)

    @property
    def bm(self) -> dict:
        return self.raw.get("battlemap", {})

    @property
    def bbg(self) -> str:
        return self.bm["bbg"]

    @property
    def fbx_rel(self) -> str:
        return self.bm.get("fbx", f"{self.bbg}.fbx")

    @property
    def scene_id(self):
        return self.bm.get("scene_id")

    @property
    def scene_name(self):
        return self.bm.get("scene_name")

    @property
    def is_mint(self) -> bool:
        return self.scene_id is not None and bool(self.scene_name)

    @property
    def scene_dir(self) -> Path:
        return self.base_dir / "scene"

    def path(self, rel: str) -> Path:
        return (self.base_dir / rel).resolve()


def _ai_entries(scene_cfg: dict, mc: int):
    """``[[scene.enemy]]`` -> a per-slot AI-entry override list (parallel to the ``mc`` spawned slots; a None element
    keeps ``rewrite_main_init``'s default ``1+type`` binding). Raises TypeError/ValueError on a non-int ``ai_entry``
    (a TOML array/table etc) -- the callers turn that into a clean problem/BattleBuildError, never a raw traceback."""
    by_slot = {int(e["slot"]): int(e["ai_entry"])
               for e in scene_cfg.get("enemy", []) if isinstance(e, dict) and "ai_entry" in e and "slot" in e}
    return [by_slot.get(s) for s in range(mc)] if by_slot else None


def _resolve_reskins(scene_cfg: dict, *, game=None):
    """Resolve any ``[[scene.enemy]]`` re-skin (``model =`` / ``model_scene =``) to a REAL donor monster block,
    injecting it as ``_reskin_block`` so ``scene_data.apply_scene_edits`` transplants it. Returns
    (scene_cfg-or-copy, warnings). Install-gated, but ONLY enemies WITH a re-skin trigger the read -- a
    re-skin-free scene is returned untouched (so non-re-skin builds/tests never touch the install)."""
    from . import reskin as _reskin
    enemies = scene_cfg.get("enemy") or []
    resolved, warns, touched = [], [], False
    for e in enemies:
        spec = _reskin.reskin_spec(e) if isinstance(e, dict) else None
        if spec is not None:
            block, prov = _reskin.resolve_donor_block(spec, game=game)
            e = dict(e, _reskin_block=block)
            warns.append(f"slot {e.get('slot')}: re-skinned BODY to {prov} -- idle/damage/death use the new "
                         f"model, but ATTACK animations stay the target enemy's (a full re-skin would also "
                         f"need the donor's raw17 btlseq + AA_DATA)")
            touched = True
        resolved.append(e)
    return (dict(scene_cfg, enemy=resolved), warns) if touched else (scene_cfg, [])


def validate_battle(project: BattleProject) -> list[str]:
    """Return human-readable problems (empty => OK)."""
    problems: list[str] = []
    bm = project.bm
    if not bm:
        return ["[battlemap] section is required"]
    bbg = bm.get("bbg")
    if not bbg:
        problems.append("[battlemap] missing 'bbg' (the slot this map ships as, e.g. BBG_B013)")
    elif not _BBG_RE.match(bbg):
        problems.append(f"[battlemap] bbg {bbg!r} must look like BBG_B013 (BBG_<letter><digits>)")
    if not project.path(project.fbx_rel).is_file():
        problems.append(f"[battlemap] fbx not found: {project.fbx_rel}")
    if "scene_id" in bm and "repoint_scene" in bm:
        problems.append("[battlemap] set only ONE of scene_id (mint) or repoint_scene")
    if project.scene_id is not None and not project.scene_name:
        problems.append("[battlemap] scene_id (mint) also needs scene_name")
    if project.is_mint:
        sd = project.scene_dir
        need = [sd / "dbfile0000.raw16.bytes", sd / "btlseq.raw17.bytes"]
        need += [sd / "eb" / f"{l}.eb.bytes" for l in LANGS]
        need += [sd / "mes" / f"{l}.mes" for l in LANGS]
        missing = [str(p.relative_to(project.base_dir)) for p in need if not p.is_file()]
        if missing:
            problems.append("[battlemap] mint needs forked scene assets (run `battle-import --fork-scene "
                            "<donor>`); missing: " + ", ".join(missing[:4])
                            + (" …" if len(missing) > 4 else ""))
        elif "scene" in project.raw:                 # tune-the-fight overrides -> validate vs the raw16
            problems += _scene_data.validate_scene(
                (sd / "dbfile0000.raw16.bytes").read_bytes(), project.raw["scene"])
            sc = project.raw["scene"] if isinstance(project.raw["scene"], dict) else {}
            from . import reskin as _reskin           # re-skin SHAPE check (model vs model_scene); install-free
            for e in sc.get("enemy", []):             # (the donor read/name resolution happens at build -- needs the install)
                if isinstance(e, dict) and any(e.get(k) is not None for k in ("model", "model_scene", "model_type")):
                    try:
                        _reskin.reskin_spec(e)
                    except _scene_data.SceneEditError as ex:
                        problems.append(str(ex))
            ai_patches, ai_funcs = sc.get("ai_patch"), sc.get("ai_function")
            ai_phases, ai_inserts = sc.get("ai_phase"), sc.get("ai_insert")
            eb0 = sd / "eb" / f"{LANGS[0]}.eb.bytes"
            has_ai_override = any(isinstance(e, dict) and "ai_entry" in e for e in sc.get("enemy", []))
            if has_ai_override and sc.get("monster_count") is None:      # ai_entry only takes effect via the
                problems.append("[[scene.enemy]] ai_entry has no effect without [scene] monster_count -- the "    # rebind
                                "AI-binding override is applied only when monster_count re-authors Main_Init")
            if sc.get("monster_count") is not None and eb0.is_file():   # dry-run the Main_Init AI-binding rebind so a
                try:                                                    # bad ai_entry / non-standard donor is caught
                    patched16, _ = _scene_data.apply_scene_edits(       # offline (it raises a clean BattleBuildError
                        (sd / "dbfile0000.raw16.bytes").read_bytes(), sc)   # at build time, but validate is friendlier)
                    mc = patched16[9]
                    slot_types = [patched16[8 + 8 + 12 * s] for s in range(mc)]
                    _event_data.rewrite_main_init(eb0.read_bytes(), slot_types, _ai_entries(sc, mc))
                except (ValueError, TypeError, _scene_data.SceneEditError) as ex:   # TypeError: a non-int (list/table)
                    problems.append(f"[[scene]] monster_count AI-binding: {ex}")    # ai_entry -> a clean problem, not a crash
            if (ai_patches or ai_funcs or ai_phases or ai_inserts) and eb0.is_file():   # Phase-6b/6c: validate +
                from . import aipatch as _aipatch, aiauthor as _aiauthor, ailint as _ailint   # LINT the COMPOSED eb
                atk = None
                try:                                 # the scene attack count enables the Attack-index lint check
                    atk = _scene_data.parse_counts((sd / "dbfile0000.raw16.bytes").read_bytes())[2]
                except Exception:                    # noqa: BLE001 -- optional
                    atk = None
                composed = eb0.read_bytes()
                if ai_patches:                       # same-length first (its offsets stay valid), then length-changing
                    problems += [f"[[scene.ai_patch]]: {p}" for p in _aipatch.validate_patches(composed, ai_patches)]
                    try:
                        composed, _ = _aipatch.apply_ai_patches(composed, ai_patches)
                    except _aipatch.AiPatchError:    # the spec error is already reported by validate_patches
                        pass
                if ai_funcs:
                    try:
                        composed = _aiauthor.apply_ai_functions(composed, ai_funcs)
                    except _aiauthor.AiAuthorError as ex:
                        problems.append(f"[[scene.ai_function]]: {ex}")
                # ai_phase / ai_insert (length-changing splices) compose + lint the SAME way the per-lang build ships
                # (ai_phase gets atk_count so out-of-range then/else -- invisible to the composed lint -- is caught here)
                if sc.get("ai_phase"):
                    try:
                        composed = _aiauthor.apply_ai_phases(composed, sc["ai_phase"], atk_count=atk)
                    except _aiauthor.AiAuthorError as ex:
                        problems.append(f"[[scene.ai_phase]]: {ex}")
                if sc.get("ai_insert"):
                    try:
                        composed = _aiauthor.apply_ai_inserts(composed, sc["ai_insert"])
                    except _aiauthor.AiAuthorError as ex:
                        problems.append(f"[[scene.ai_insert]]: {ex}")
                # lint the FINAL composed bytecode -- EXACTLY what the per-lang build ships, so an ai_patch / ai_function
                # / ai_phase / ai_insert that puts a jump / Attack index out of range (or a runaway branch) is caught.
                problems += [f"[[scene.ai]] lint: {i}" for i in _ailint.lint_ai(composed, atk_count=atk)]
    return problems


def _author_inb(bbg: str, tint=(128, 128, 128), shadow: int = 32) -> bytes:
    """A static BBGINFO (.inb): bbgnumber from `bbg`, all anim flags 0 (texanim/objanim/uvcount), a char
    light tint + shadow. 16 bytes, layout per BBGINFO.cs. Static dodges the hardcoded per-id anim tables."""
    r, g, b = (list(tint) + [128, 128, 128])[:3]
    return struct.pack("<6h4B", _bbg_number(bbg), 0, 0, 0, 0, 0,
                       r & 255, g & 255, b & 255, shadow & 255)


@dataclass
class BattleResult:
    bbg: str
    dict_line: str | None
    battle_patch_lines: list           # list[str]
    warnings: list                     # list[str]
    written: list = field(default_factory=list)   # list[Path] -- every file emitted into the layout
    lint: list = field(default_factory=list)       # list[scenelint.Finding] -- offline balance notes


def build_battlemap(project: BattleProject, layout: ModLayout, *, game=None) -> BattleResult:
    problems = validate_battle(project)
    if problems:
        raise BattleBuildError("battle.toml problems:\n  " + "\n  ".join(problems))
    bbg = project.bbg
    written: list[Path] = []

    # 1) the map: loose FBX + its textures
    dst = layout.battlemap_dir(bbg)
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(project.path(project.fbx_rel), dst / f"{bbg}.fbx")
    written.append(dst / f"{bbg}.fbx")
    for png in sorted(project.base_dir.glob("*.png")):
        shutil.copyfile(png, dst / png.name)
        written.append(dst / png.name)

    bm = project.bm
    dict_line = None
    bp: list[str] = []
    warnings: list[str] = []
    lint: list = []

    # 2) MINT: copy the forked scene assets + author a static INB for a new bbg number + register
    if project.is_mint:
        name, sid = project.scene_name, int(project.scene_id)
        sd = project.scene_dir
        scene_out = layout.battle_scene_dir(name)
        scene_out.mkdir(parents=True, exist_ok=True)
        scene_cfg = project.raw.get("scene") if isinstance(project.raw.get("scene"), dict) else None
        raw16 = (sd / "dbfile0000.raw16.bytes").read_bytes()
        if scene_cfg:                                # tune the fight (positions/stats/rewards/camera selector)
            try:                                     # re-skin: resolve donor model blocks (install I/O) first
                scene_cfg, reskin_warns = _resolve_reskins(scene_cfg, game=game)
            except _scene_data.SceneEditError as ex:
                raise BattleBuildError(f"re-skin: {ex}")
            warnings += reskin_warns
            raw16, scene_warns = _scene_data.apply_scene_edits(raw16, scene_cfg)
            warnings += scene_warns
        (scene_out / "dbfile0000.raw16.bytes").write_bytes(raw16)
        # offline BALANCE lint of the final (tuned) scene -- "I can't see the game" leverage. Advisory only:
        # a lint failure must NEVER crash the build, so degrade to no findings on ANY error.
        try:
            lint = _scenelint.lint_scene(_scene_codec.parse_scene(raw16))
        except Exception:                                # noqa: BLE001 -- best-effort, build must not fail on lint
            lint = []
        # raw17: tweak the OPENING camera's keyframes IN PLACE (yaw/pitch/zoom) -- no offset repack. Which
        # camera plays = raw16 pattern Camera byte (the `[scene] camera` selector); tweak that one (0-2) or
        # all of 0/1/2 if it's random/unpinned.
        raw17 = (sd / "btlseq.raw17.bytes").read_bytes()
        cam_idx = _camera_data.opening_indices(scene_cfg.get("camera")) if scene_cfg else []
        if scene_cfg and scene_cfg.get("camera_keyframes"):     # tier ii: author the opening from scratch
            try:
                raw17 = _camera_codec.author_opening(raw17, cam_idx, scene_cfg["camera_keyframes"])
            except ValueError as ex:
                raise BattleBuildError(f"camera keyframe authoring failed: {ex}")
        if scene_cfg and any(k in scene_cfg for k in ("camera_yaw", "camera_pitch", "camera_zoom")):
            raw17 = _camera_data.tweak_opening(                 # tier i: offset (composes over keyframes)
                raw17, cam_idx,
                yaw_deg=float(scene_cfg.get("camera_yaw", 0)),
                pitch_deg=float(scene_cfg.get("camera_pitch", 0)),
                zoom=float(scene_cfg.get("camera_zoom", 1.0)))
        (scene_out / f"{sid}.raw17.bytes").write_bytes(raw17)
        written += [scene_out / "dbfile0000.raw16.bytes", scene_out / f"{sid}.raw17.bytes"]

        # spawn composition re-authors the eb's Main_Init to bind one enemy-AI object per spawned slot, so
        # the AI binding matches the (now-uniform) pattern -- this is what lets a mint EXCEED the donor's
        # natural enemy count without the player-model twitch. slot types come from the patched raw16.
        slot_types = ai_entries = None
        if scene_cfg and "monster_count" in scene_cfg:
            mc = raw16[9]                                          # pattern 0 MonsterCount (now uniform)
            slot_types = [raw16[8 + 8 + 12 * s] for s in range(mc)]
            ai_entries = _ai_entries(scene_cfg, mc)               # explicit per-slot AI-entry overrides (validate-gated)
        try:                                                      # the scene attack count -> ai_phase then/else guard
            _atk_count = _scene_data.parse_counts(raw16)[2]
        except Exception:                                         # noqa: BLE001 -- optional, falls back to the byte cap
            _atk_count = None
        for lang in LANGS:
            eb_dst = layout.battle_eb_path(lang, name)
            eb_dst.parent.mkdir(parents=True, exist_ok=True)
            eb = (sd / "eb" / f"{lang}.eb.bytes").read_bytes()
            if slot_types is not None:
                try:
                    eb = _event_data.rewrite_main_init(eb, slot_types, ai_entries)
                except ValueError as ex:
                    raise BattleBuildError(f"spawn composition needs a Main_Init re-author this donor "
                                           f"can't support: {ex}")
            if scene_cfg and scene_cfg.get("ai_patch"):     # Phase-6b: same-length AI constant patches (eb).
                from . import aipatch as _aipatch          # The bytecode is language-identical -> same offsets.
                try:
                    eb, ai_warns = _aipatch.apply_ai_patches(eb, scene_cfg["ai_patch"])
                    if lang == LANGS[0]:
                        warnings += ai_warns
                except _aipatch.AiPatchError as ex:
                    raise BattleBuildError(str(ex))
            if scene_cfg and (scene_cfg.get("ai_function") or scene_cfg.get("ai_phase")
                              or scene_cfg.get("ai_insert")):   # Phase-6c: length-changing AI edits (AFTER ai_patch
                from . import aiauthor as _aiauthor            # so the same-length patch offsets stayed valid).
                try:
                    if scene_cfg.get("ai_function"):           # replace/add a WHOLE function
                        eb = _aiauthor.apply_ai_functions(eb, scene_cfg["ai_function"])
                    if scene_cfg.get("ai_phase"):              # generate + splice an HP-threshold phase branch
                        eb = _aiauthor.apply_ai_phases(eb, scene_cfg["ai_phase"], atk_count=_atk_count)
                    if scene_cfg.get("ai_insert"):             # splice an explicit branch fragment
                        eb = _aiauthor.apply_ai_inserts(eb, scene_cfg["ai_insert"])
                except _aiauthor.AiAuthorError as ex:
                    raise BattleBuildError(str(ex))
            eb_dst.write_bytes(eb)
            mes_dst = layout.battle_text_dir(lang) / f"{sid}.mes"
            mes_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(sd / "mes" / f"{lang}.mes", mes_dst)
            written += [eb_dst, mes_dst]
        if _bbg_number(bbg) > _REAL_BBG_MAX:     # a wholly new map -> author its static INB
            inb = _author_inb(bbg, tuple(bm.get("char_tint", (128, 128, 128))), int(bm.get("shadow", 32)))
            inb_dst = layout.battle_info_dir / f"{bbg.replace('BBG', 'INB')}.inb.bytes"
            inb_dst.parent.mkdir(parents=True, exist_ok=True)
            inb_dst.write_bytes(inb)
            written.append(inb_dst)
        dict_line = f"BattleScene {sid} {name} {bbg}"

    # 3) repoint an existing scene's background at this map
    if bm.get("repoint_scene") is not None:
        bp.append(f"Battle: {int(bm['repoint_scene'])}")
        bp.append(f"BattleBackground {bbg}")

    return BattleResult(bbg=bbg, dict_line=dict_line, battle_patch_lines=bp, warnings=warnings,
                        written=written, lint=lint)


def build_battle_mod(projects, out_root, *, mod_name="FF9CustomMap", author="", description="", game=None) -> dict:
    """Build battle map(s) into a mod at ``out_root``; write/append the registration files. ``game`` (an FF9
    install dir) is only consulted by an enemy re-skin (`[[scene.enemy]] model =`), which reads a donor model
    block live from the install; None = the default resolution ($FF9_GAME_PATH / config / common Steam paths)."""
    layout = ModLayout(Path(out_root).resolve())
    layout.root.mkdir(parents=True, exist_ok=True)
    results = [build_battlemap(p, layout, game=game) for p in projects]

    dlines = [r.dict_line for r in results if r.dict_line]
    if dlines:
        # append to any existing DictionaryPatch (so a co-built field mod isn't clobbered)
        prior = (layout.dictionary_patch.read_text(encoding="utf-8").splitlines()
                 if layout.dictionary_patch.exists() else [])
        layout.dictionary_patch.write_text(
            "\n".join([ln for ln in prior if ln.strip()] + dlines) + "\n",
            encoding="utf-8", newline="\n")

    bplines = [ln for r in results for ln in r.battle_patch_lines]
    if bplines:
        prior = (layout.battle_patch.read_text(encoding="utf-8").splitlines()
                 if layout.battle_patch.exists() else [])
        layout.battle_patch.write_text(
            "\n".join([ln for ln in prior if ln.strip()] + bplines) + "\n",
            encoding="utf-8", newline="\n")

    if not layout.mod_description.exists():
        layout.mod_description.write_text(
            "<Mod>\n"
            f"    <Name>{mod_name}</Name>\n"
            f"    <Author>{author}</Author>\n"
            f"    <InstallationPath>{mod_name}</InstallationPath>\n"
            "    <Category></Category>\n"
            f"    <Description>{description}</Description>\n"
            "</Mod>\n",
            encoding="utf-8", newline="\n")

    return {"root": str(layout.root), "maps": [r.bbg for r in results],
            "dictionary": dlines, "battle_patch": bplines,
            "written": [str(p) for r in results for p in r.written],
            "warnings": [w for r in results for w in r.warnings],
            "lint": [str(f) for r in results for f in r.lint]}
