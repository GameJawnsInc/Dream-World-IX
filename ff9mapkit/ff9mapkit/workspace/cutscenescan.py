"""The Cutscene tab's Qt-free model layer (the twin of :mod:`behaviorscan` for the behavior tab):
staging checks, the rail/ladder/stage projections, the beat-indexed storyboard, and the mutation ops.

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
    return any(b.get("actors") for b in _blocks(raw))


def check_staging(raw: dict, base_dir, wmesh) -> StagingResult:
    """Run the build's own walk-stall check over the open document. Worker material — pure, no Qt,
    no disk (pass ``wmesh`` from :func:`load_walkmesh`). Never raises: a half-typed scene is the
    normal case here, and an unresolved name is already ``validate()``'s job to report."""
    from .. import build as _build
    blocks = _blocks(raw)
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


# ======================================================================================
# The Cutscene DOC TAB's model layer (the redesign). Everything below is pure over its
# arguments, Qt-free, and import-light at module scope (`build` / `content` load lazily,
# the check_staging idiom). Three lanes, by cost:
#
#   * PROJECTIONS  -- raw-dict only, never raise, safe per-render on the GUI thread
#     (scene_rows / ladder_rows / dispatch_problems / scene_problems / stage_model).
#   * WORKER LANES -- take the walkmesh, drive the BUILD'S OWN resolvers, never raise
#     (storyboard / stage_verdicts). Deep-copied input; run them off-thread.
#   * OPS          -- mutate the raw dict in place and RETURN THE UNDO LABEL (the
#     behaviorscan idiom: the doc never composes a label, `_checkpoint` folds no-ops).
# ======================================================================================

def _blocks(raw) -> list:
    """Every [[cutscene]] block of the open doc (a singleton comes out as one), author order.
    Hardened past ``all_blocks``: a garbage section (``cutscene = 17``) is [] here, because the
    projections' contract is NEVER RAISE over a half-typed doc."""
    cur = None
    if isinstance(raw, dict):
        cur = raw.get("cutscene")
    if cur is None or isinstance(cur, (dict, list)):
        return _forms.all_blocks(cur)
    return []


def _block(raw, k) -> dict:
    """Scene ``k``'s dict for a WRITE (singleton == index 0). IndexError on a bad index — the
    caller (the doc) owns its indices; a miss here is a programming error, not user input."""
    cur = raw.get("cutscene")
    if isinstance(cur, dict):
        if k != 0:
            raise IndexError(k)
        return cur
    return cur[k]


# --------------------------------------------------------------------- projections
def gate_text(block: dict) -> str:
    """The scene's story gate as one short line for the rail — "always" when ungated."""
    bits = []
    if block.get("requires_scenario") is not None:
        bits.append(f"plays at beat {block['requires_scenario']}")
    if block.get("requires_flag") is not None:
        bits.append(f"needs flag {block['requires_flag']}")
    if block.get("requires_flag_clear") is not None:
        bits.append(f"needs flag {block['requires_flag_clear']} clear")
    return " · ".join(bits) if bits else "always"


def scene_rows(raw) -> list:
    """The scene rail's model: one row per [[cutscene]] block, 0-based like the build's own lint."""
    rows = []
    for k, b in enumerate(_blocks(raw)):
        cast = ([str(a) for a in b["actors"]] if isinstance(b.get("actors"), list) else [])
        steps = b.get("steps") if isinstance(b.get("steps"), list) else []
        rows.append({
            "idx": k,
            "label": f"scene #{k}",
            "gate": gate_text(b),
            "cast": cast,
            "narration": not cast,
            "steps": len(steps),
            "once": bool(b.get("once", True)),
            "ate": bool(b.get("ate")),
            "then_warp": b.get("then_warp"),
        })
    return rows


def ladder_rows(raw, scene_idx: int) -> list:
    """The step ladder's model for scene ``scene_idx`` — grouping by the COMPILER'S own parallel
    rule (:func:`content.conductor.group_parallel`), never a re-derivation. ``group`` is the beat
    ordinal: rows sharing one are one beat (`with_prev`)."""
    from ..content import conductor as _conductor      # lazy -- keep module import content-free
    blocks = _blocks(raw)
    if not (0 <= scene_idx < len(blocks)):
        return []
    steps = blocks[scene_idx].get("steps")
    if not isinstance(steps, list):
        return []
    safe = [s if isinstance(s, dict) else {} for s in steps]   # indices stay AUTHORED indices
    group_of = {}
    for g, grp in enumerate(_conductor.group_parallel(safe)):
        for i, _s in grp:
            group_of[i] = g
    rows = []
    for i, s in enumerate(safe):
        k = _forms.step_key(s)
        rows.append({
            "idx": i,
            "kind": k,
            "verb": k or "(empty)",
            "actor": s.get("actor") or "",
            "detail": _forms.step_value_text(s),
            "with_prev": bool(s.get("with_prev")),
            "group": group_of.get(i, i),
            "is_text": k in _forms.TEXT_STEPS,
            "valueless": _forms.STEP_KIND.get(k) == _forms.BOOL,
            "extras": sorted(kk for kk in s
                             if kk not in _forms.STEP_KIND and kk not in ("actor", "with_prev")),
        })
    return rows


def dispatch_problems(raw) -> list:
    """The DISPATCH gate rule, mirrored from ``build.validate`` (same key, same wording) so the tab
    warns LIVE while the author sets gates instead of at the next full Check. Drift-fenced against
    the build's own output in test_cutscenescan — if the compiler's rule moves, the fence goes red."""
    blocks = _blocks(raw)
    if len(blocks) <= 1:
        return []
    problems, gates = [], {}
    for ci, cs in enumerate(blocks):
        key = (cs.get("requires_scenario"), cs.get("requires_flag"), cs.get("requires_flag_clear"))
        if key in gates:
            what = "both UNGATED" if key == (None, None, None) else f"the same gate {key}"
            problems.append(f"[cutscene] #{gates[key]} and #{ci} have {what} -- a [[cutscene]] dispatch "
                            f"needs pairwise-distinct requires_scenario / requires_flag gates (else both "
                            f"scenes fire, and lock control, on the same load).")
        else:
            gates[key] = ci
    return problems


def _target_names(raw) -> set:
    """Names a walk/teleport/path may reference — the raw-dict twin of the build's
    ``_position_registry`` NAME set (player/spawn need a spawn; an npc/marker needs name + pos —
    a path-only marker is deliberately absent, exactly like the registry)."""
    names = set()
    pl = (raw or {}).get("player")
    if isinstance(pl, dict) and pl.get("spawn"):
        names |= {"player", "spawn"}
    for sect in ("npc", "marker"):
        for e in (raw or {}).get(sect) or []:
            if isinstance(e, dict) and e.get("name") and e.get("pos"):
                names.add(str(e["name"]))
    return names


def scene_problems(raw) -> list:
    """The always-on PROBLEMS lane: cheap raw-only structural checks in plain sentences (the shell's
    ``_node_problems`` speaks HTML; the instruments pane speaks text). Pass the MERGED doc — a
    scene.toml field keeps its markers/NPC positions there. 0-based ``scene #k`` prefixes on a
    dispatch, the GUI's own convention."""
    out = []
    blocks = _blocks(raw)
    names = _target_names(raw)
    npc_names = {str(n["name"]) for n in (raw or {}).get("npc") or []
                 if isinstance(n, dict) and n.get("name")}

    def _bad_name(v):
        if not isinstance(v, str):
            return False
        nm = v[1:] if v.startswith("@") else v
        return nm not in names

    for k, b in enumerate(blocks):
        tag = f"scene #{k}: " if len(blocks) > 1 else ""
        cast = ([str(a) for a in b["actors"]] if isinstance(b.get("actors"), list) else [])
        for a in cast:
            if a != "player" and a not in npc_names:
                out.append(f'{tag}cast member "{a}" is not an [[npc]] on this field (or "player")')
        steps = b.get("steps") if isinstance(b.get("steps"), list) else []
        for i, s in enumerate(steps):
            if not isinstance(s, dict):
                continue
            kk = _forms.step_key(s)
            actor = s.get("actor")
            if actor and cast and actor not in cast:
                out.append(f'{tag}step {i} actor "{actor}" is not in the cast ({", ".join(cast)})')
            if kk in _forms.ACTOR_STEPS and not cast:
                out.append(f'{tag}step {i} ({kk}) needs a cast -- add actors = ["<npc name>"]')
            if s.get("with_prev"):
                if i == 0:
                    out.append(f"{tag}step 0 can't run with a previous beat (there isn't one)")
                elif kk not in _forms.PARALLEL_STEPS:
                    out.append(f"{tag}step {i} ({kk}) can't run in parallel -- only "
                               f"{', '.join(_forms.PARALLEL_STEPS)} can ride with_prev")
            for mk in ("walk", "teleport"):
                if mk in s and _bad_name(s.get(mk)):
                    out.append(f'{tag}step {i} {mk} target "{s[mk]}" is not a known marker/NPC/player')
            if isinstance(s.get("path"), list):
                for j, leg in enumerate(s["path"]):
                    if _bad_name(leg):
                        out.append(f'{tag}step {i} path point {j} "{leg}" is not a known '
                                   f'marker/NPC/player')
    return out


def wrap_width(raw):
    """The dialogue auto-wrap budget over the OPEN doc — the raw-dict twin of ``build._wrap_width``
    (mirror-fenced) so the storyboard's say lines wrap exactly like the game will. ``None`` = off."""
    from ..content import text as _text
    dl = (raw or {}).get("dialogue")
    w = dl.get("wrap", _text.DEFAULT_WRAP_WIDTH) if isinstance(dl, dict) else _text.DEFAULT_WRAP_WIDTH
    if w is False or w == 0:
        return None
    if w is True:
        return _text.DEFAULT_WRAP_WIDTH
    try:
        return float(w)
    except (TypeError, ValueError):            # a garbage value: validate() reports it; wrap sanely
        return _text.DEFAULT_WRAP_WIDTH


# --------------------------------------------------------------------- stage / storyboard
def stage_model(raw, scene_idx: int) -> dict:
    """The CHEAP stage lane: what the canvas can draw from the raw dict alone — no walkmesh, no
    FieldProject, never raises, safe on the GUI thread per keystroke. A half-typed scene renders:
    an unresolvable movement target drops its leg and is COUNTED (``unresolved``) so the canvas
    says "2 targets unresolved" instead of lying by omission. Routing, approach offsets and
    verdicts belong to the worker lanes (:func:`storyboard` / :func:`stage_verdicts`)."""
    raw = raw or {}
    blocks = _blocks(raw)
    b = blocks[scene_idx] if 0 <= scene_idx < len(blocks) else {}
    cast = ([str(a) for a in b["actors"]] if isinstance(b.get("actors"), list) else [])

    def _xz(v):
        if isinstance(v, (list, tuple)) and len(v) >= 2:
            try:
                return (int(v[0]), int(v[1]))
            except (TypeError, ValueError):
                return None
        return None

    pl = raw.get("player")
    player = _xz(pl.get("spawn")) if isinstance(pl, dict) else None
    npcs = {}
    for n in raw.get("npc") or []:
        if isinstance(n, dict) and n.get("name") and _xz(n.get("pos")):
            npcs[str(n["name"])] = _xz(n["pos"])
    markers = []
    for m in raw.get("marker") or []:
        if isinstance(m, dict) and m.get("name") and _xz(m.get("pos")):
            x, z = _xz(m["pos"])
            markers.append({"name": str(m["name"]), "x": x, "z": z})
    reg = {}
    if player:
        reg["player"] = reg["spawn"] = player
    reg.update(npcs)
    reg.update({mm["name"]: (mm["x"], mm["z"]) for mm in markers})   # markers WIN a clash (registry order)

    cast_rows = []
    for name in cast:
        p = player if name == "player" else npcs.get(name)
        cast_rows.append({"name": name, "x": (p[0] if p else None), "z": (p[1] if p else None),
                          "is_player": name == "player", "placed": p is not None})
    obstacles = [{"name": nm, "x": p[0], "z": p[1]} for nm, p in npcs.items() if nm not in cast]

    def _pt(v):
        if isinstance(v, str):
            nm = v[1:] if v.startswith("@") else v
            return reg.get(nm)
        return _xz(v)

    legs, unresolved = [], 0
    steps = b.get("steps") if isinstance(b.get("steps"), list) else []
    pos = {c["name"]: (c["x"], c["z"]) for c in cast_rows if c["placed"]}
    sole = cast[0] if len(cast) == 1 else None
    for i, s in enumerate(steps):
        if not isinstance(s, dict):
            continue
        kk = _forms.step_key(s)
        if kk not in ("walk", "path", "teleport"):
            continue
        actor = s.get("actor") or sole
        if actor not in pos:
            unresolved += 1
            continue
        if kk == "path":
            pts = ([_pt(x) for x in s["path"]] if isinstance(s.get("path"), list) else [])
            if pts and all(p is not None for p in pts):
                legs.append({"actor": actor, "step": i, "kind": "path", "points": [pos[actor]] + pts})
                pos[actor] = pts[-1]
            else:
                unresolved += 1
        else:
            p = _pt(s.get(kk))
            if p is None:
                unresolved += 1
                continue
            legs.append({"actor": actor, "step": i, "kind": kk, "points": [pos[actor], p]})
            pos[actor] = p
    return {"markers": markers, "cast": cast_rows, "obstacles": obstacles, "player": player,
            "legs": legs, "unresolved": unresolved}


def storyboard(raw, base_dir, wmesh, scene_idx: int) -> dict:
    """The BEAT-indexed storyboard (never a clock: ``say`` blocks on the player, so a seconds axis
    would be fiction — the review's §4 verdict). Worker material — deep-copies, never raises.

    Beats are the compiler's own parallel groups. Each beat carries the step indices, the first
    text line (raw — the doc wraps it for display), the movement legs, and the END-of-beat cast
    positions (chained through every earlier beat). With a walkmesh the legs are the compiler's
    routed polylines (a blocked walk becomes its real ``path``); without one they run straight,
    and the ledger says so."""
    out = {"error": "", "beats": [], "narration": False, "notes": []}
    try:
        from .. import build as _build
        from ..content import conductor as _conductor
        blocks = _blocks(raw)
        if not (0 <= scene_idx < len(blocks)):
            out["error"] = f"scene #{scene_idx} does not exist"
            return out
        b = blocks[scene_idx]
        cast = ([str(a) for a in b["actors"]] if isinstance(b.get("actors"), list) else [])
        out["narration"] = not cast
        steps = b.get("steps") if isinstance(b.get("steps"), list) else []
        project = _build.FieldProject(copy.deepcopy(raw), base_dir)
        if cast:
            try:
                steps = _build._resolve_conductor_steps(steps, project, cast=cast, walkmesh=wmesh,
                                                        beat=_build._scene_beat(b))
            except ValueError as e:            # a half-typed scene is the NORMAL case here
                out["error"] = str(e)
                return out
        npc_by_name = {n.get("name"): n for n in project.raw.get("npc", [])}
        pos = {}
        for name in cast:
            anpc = (_build._pseudo_player_npc(project) if name == "player"
                    else npc_by_name.get(name))
            if anpc and anpc.get("pos"):
                pos[name] = (int(anpc["pos"][0]), int(anpc["pos"][1]))
        safe = [s if isinstance(s, dict) else {} for s in steps]
        for gk, grp in enumerate(_conductor.group_parallel(safe)):
            say, say_who, legs = None, "", []
            for i, s in grp:
                kk = _forms.step_key(s)
                if kk in _forms.TEXT_STEPS and say is None:
                    say = s.get(kk)
                    say_who = s.get("speaker") or s.get("actor") or ""
                actor = s.get("actor")
                if not actor or actor not in pos:
                    continue
                if kk == "teleport" and isinstance(s.get("teleport"), (list, tuple)):
                    p = (int(s["teleport"][0]), int(s["teleport"][1]))
                    legs.append({"actor": actor, "step": i, "kind": "teleport",
                                 "points": [pos[actor], p]})
                    pos[actor] = p
                elif kk == "walk" and isinstance(s.get("walk"), (list, tuple)):
                    p = (int(s["walk"][0]), int(s["walk"][1]))
                    legs.append({"actor": actor, "step": i, "kind": "walk",
                                 "points": [pos[actor], p], "follow": bool(s.get("follow"))})
                    pos[actor] = p
                elif kk == "path" and isinstance(s.get("path"), list) and s["path"]:
                    pts = [(int(p[0]), int(p[1])) for p in s["path"]]
                    legs.append({"actor": actor, "step": i, "kind": "path",
                                 "points": [pos[actor]] + pts})
                    pos[actor] = pts[-1]
            out["beats"].append({"k": gk, "step_idxs": [i for i, _s in grp],
                                 "say": say, "say_actor": say_who,
                                 "positions": dict(pos), "legs": legs})
        # THE HONESTY LEDGER -- on the strip's face, not in a docstring.
        out["notes"] = [
            "beat axis, no clock -- a say waits for the player, so seconds would be fiction",
            "walks are the compiler's routed polylines, not the engine's smooth path",
            "@player resolves to [player] spawn; the real player stands wherever they walked",
        ]
        if wmesh is None and cast:
            out["notes"].insert(1, "no walkmesh loaded -- legs shown straight "
                                   "(Check the staging routes them)")
    except Exception as e:                     # noqa: BLE001 -- worker material must never raise
        out["error"] = f"Could not build the storyboard -- {e}"
    return out


def stage_verdicts(raw, base_dir, wmesh) -> list:
    """PAINTABLE staging verdicts: the same legs, the same sentences as :func:`check_staging`
    (parity-fenced), but with the leg geometry attached so the canvas can draw the failure where
    it happens — jam-style. The chaining below is ``build._validate_cutscene_movement``'s own
    (follow-skip, teleport repositioning, per-path-leg checks), driven leg by leg to capture
    ``(a, b)`` per sentence. Never raises; an unresolvable scene contributes nothing (that is
    ``StagingResult.skipped``'s job to report)."""
    if wmesh is None:
        return []
    out = []
    try:
        from .. import build as _build
        project = _build.FieldProject(copy.deepcopy(raw), base_dir)
        npc_by_name = {n.get("name"): n for n in project.raw.get("npc", [])}
        blocks = _forms.all_blocks(project.raw.get("cutscene"))
        for ci, cs in enumerate(blocks):
            lbl = "[cutscene]" if len(blocks) == 1 else f"[cutscene] #{ci}"
            cast = [str(a) for a in (cs.get("actors") or [])]
            if not cast:
                continue
            beat = _build._scene_beat(cs)
            try:
                steps = _build._resolve_conductor_steps(cs.get("steps", []), project, cast=cast,
                                                        walkmesh=wmesh, beat=beat)
            except ValueError:
                continue
            for name in cast:
                anpc = (_build._pseudo_player_npc(project) if name == "player"
                        else npc_by_name.get(name))
                if not anpc or not anpc.get("pos"):
                    continue
                pos = (int(anpc["pos"][0]), int(anpc["pos"][1]))
                for k, s in enumerate(steps):
                    if s.get("actor") != name:
                        continue
                    if "teleport" in s:
                        pos = (int(s["teleport"][0]), int(s["teleport"][1]))
                    elif "walk" in s:
                        tgt = (int(s["walk"][0]), int(s["walk"][1]))
                        if s.get("follow"):    # an engine follow ends ON CONTACT -- can't stall
                            pos = tgt
                            continue
                        w = []
                        _build._check_walk_leg(project, wmesh, k, pos, tgt, name, w, beat, lbl)
                        out.extend({"scene": ci, "step": k, "actor": name,
                                    "a": pos, "b": tgt, "text": t} for t in w)
                        pos = tgt
                    elif "path" in s:
                        for wp in s["path"]:
                            tgt = (int(wp[0]), int(wp[1]))
                            w = []
                            _build._check_walk_leg(project, wmesh, k, pos, tgt, name, w, beat, lbl)
                            out.extend({"scene": ci, "step": k, "actor": name,
                                        "a": pos, "b": tgt, "text": t} for t in w)
                            pos = tgt
    except Exception:                          # noqa: BLE001 -- the paint lane must never raise
        return []
    return out


# --------------------------------------------------------------------------- ops
# Every op mutates ``raw`` in place and returns the undo-step label (the behaviorscan idiom).
# Index errors are PROGRAMMING errors -- the doc owns its indices -- so they raise, not soften.

_SCENE_MINT = {"steps": [{"say": "A new scene."}]}   # narration, runnable as-is; add a cast to stage it


def add_scene(raw) -> str:
    """Append a scene. Owns the dict→list promotion — a singleton [cutscene] becomes the first
    block of a [[cutscene]] dispatch the moment a second scene exists."""
    cur = raw.get("cutscene")
    block = copy.deepcopy(_SCENE_MINT)
    if cur is None:
        raw["cutscene"] = [block]              # a LIST from birth: the next add is a plain append
    elif isinstance(cur, dict):
        raw["cutscene"] = [cur, block]         # the dispatch is born here
    else:
        cur.append(block)
    return "add cutscene scene"


def duplicate_scene(raw, k: int) -> str:
    cur = raw.get("cutscene")
    if isinstance(cur, dict):
        if k != 0:
            raise IndexError(k)
        raw["cutscene"] = cur = [cur]
    cur.insert(k + 1, copy.deepcopy(cur[k]))
    return f"duplicate cutscene scene #{k}"


def delete_scene(raw, k: int) -> str:
    """Delete ONE scene (never the section behind a singular label — the A4 lesson); the emptied
    section is dropped so no bare [[cutscene]] litter survives."""
    cur = raw.get("cutscene")
    if isinstance(cur, dict):
        if k != 0:
            raise IndexError(k)
        del raw["cutscene"]
        return "delete cutscene scene #0"
    cur.pop(k)
    if not cur:
        del raw["cutscene"]
    return f"delete cutscene scene #{k}"


def apply_scene_settings(raw, k: int, entity: dict, managed) -> str:
    """Fold the settings card into scene ``k``: every ``managed`` key is authoritative from
    ``entity`` (absent = pop), everything else (steps, keys the card doesn't own) is preserved."""
    b = _block(raw, k)
    for key in managed:
        if key in entity:
            b[key] = entity[key]
        else:
            b.pop(key, None)
    return f"edit cutscene scene #{k}"


def add_step(raw, k: int, at: int, step: dict) -> str:
    b = _block(raw, k)
    st = b.setdefault("steps", [])
    st.insert(max(0, min(int(at), len(st))), step)
    return "add cutscene step"


def update_step(raw, k: int, i: int, step: dict, managed=()) -> str:
    """Rewrite step ``i``. ``managed`` keys are authoritative from ``step`` (absent = pop, so the
    editor can CLEAR a speaker); action keys are replaced wholesale (a step has exactly one);
    everything else the editor does not know is PRESERVED — the old form's extras rule, with the
    editor now owning more keys."""
    st = _block(raw, k)["steps"]
    old = st[i] if isinstance(st[i], dict) else {}
    keep = {kk: vv for kk, vv in old.items()
            if kk not in _forms.STEP_KIND and kk not in managed}
    st[i] = {**keep, **step}
    return "edit cutscene step"


def remove_step(raw, k: int, i: int) -> str:
    _block(raw, k)["steps"].pop(i)
    return "remove cutscene step"


def move_step(raw, k: int, i: int, delta: int) -> str:
    st = _block(raw, k)["steps"]
    j = i + (1 if delta > 0 else -1)
    if not (0 <= i < len(st)) or not (0 <= j < len(st)):
        raise IndexError(j)                    # the doc disables the button at the boundary
    st[i], st[j] = st[j], st[i]
    return "reorder cutscene steps"


def duplicate_step(raw, k: int, i: int) -> str:
    st = _block(raw, k)["steps"]
    st.insert(i + 1, copy.deepcopy(st[i]))
    return "duplicate cutscene step"


def set_step_target(raw, k: int, i: int, x, z, waypoint=None) -> str:
    """The stage-drop lane: aim step ``i``'s movement target at ``(x, z)``. A NAMED target
    (marker / @player) becomes the literal coordinate — the label says so, because that edit
    changes MEANING (the step no longer tracks the name)."""
    s = _block(raw, k)["steps"][i]
    kk = _forms.step_key(s)
    x, z = int(round(x)), int(round(z))
    if waypoint is not None:
        if kk != "path":
            raise ValueError(f"step {i} is {kk!r}, not a path")
        was = s["path"][int(waypoint)]
        s["path"][int(waypoint)] = [x, z]
        lbl = f"move path point {int(waypoint)} of step {i} to ({x}, {z})"
        return lbl + (f' (was "{was}")' if isinstance(was, str) else "")
    if kk not in ("walk", "teleport"):
        raise ValueError(f"step {i} is {kk!r}, not a movement step")
    was = s[kk]
    s[kk] = [x, z]
    lbl = f"aim {kk} step {i} at ({x}, {z})"
    return lbl + (f' (was "{was}")' if isinstance(was, str) else "")


def insert_path_point(raw, k: int, i: int, j: int) -> str:
    """Insert a waypoint after point ``j`` (the midpoint toward the next point, or +64u on x at
    the tail). A NAMED point refuses with a reason — there is no midpoint toward a name."""
    pts = _block(raw, k)["steps"][i]["path"]
    p = pts[j]
    if not (isinstance(p, (list, tuple)) and len(p) >= 2):
        raise ValueError(f"path point {j} is a name ({p!r}) -- aim it at coords first, then split")
    q = pts[j + 1] if j + 1 < len(pts) else None
    if isinstance(q, (list, tuple)) and len(q) >= 2:
        np = [(int(p[0]) + int(q[0])) // 2, (int(p[1]) + int(q[1])) // 2]
    else:
        np = [int(p[0]) + 64, int(p[1])]
    pts.insert(j + 1, np)
    return f"insert a path point after {j} in step {i}"


def delete_path_point(raw, k: int, i: int, j: int) -> str:
    pts = _block(raw, k)["steps"][i]["path"]
    if len(pts) <= 1:
        raise ValueError("a path needs at least one point -- delete the step instead")
    pts.pop(j)
    return f"delete path point {j} of step {i}"
