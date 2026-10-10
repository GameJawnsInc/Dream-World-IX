"""The field's EventAnimation clip list -- what the engine re-adds to a model it (re)creates.

A field model's ``Animation`` component holds only the clips something added to it. Script ops add their
own clip as they run (``SetStandAnimation``, ``RunAnimation``, ``SetInactiveAnimation``, ...), so a field
that never leaves looks fine. A BATTLE RETURN rebuilds every model from scratch (``updateModelsToBeAdded``)
and the engine then re-adds only two things:

  1. the clips the field's ``CommonAsset/EventEngine/EventAnimation/EVT_<name>.txt`` lists for that model
     (``ModelFactory.CreateModel -> AnimationFactory.AddAnimToGameObject``); every stock field ships one;
  2. the five locomotion slots, idle/walk/run/turn-left/turn-right (``ReassignBasicAnimationForField``).

A kit field shipped no list, so after a battle anything outside those five slots was gone -- above all the
player's INACTIVE clip (``SetInactiveAnimation``, Zidane's arms-crossed fidget): when the idle timer fired it,
the engine played a clip the model no longer had, and Memoria's ``SmoothFrameUpdater_Field.RegisterState``
threw a NullReferenceException every frame until the clip ended (the sims rung-5 burst; the repro is
``studies/after-battle-clips/``). A clip a one-shot was still playing when the battle started went the same
way. This module writes the stock list from the field's own compiled script, so a rebuilt model gets back
every clip the field can play on it.

THE FORMAT (``AnimationFactory.LoadAnimationUseInEvent``): line 1 is ``animation:`` + every clip name, comma-
separated; each further line is ``<GEO model name>:<clip>,<clip>,...``. Two engine facts bind it:
  * every clip a model line names MUST be on line 1 -- the model add indexes the line-1 dictionary and a
    missing name throws KeyNotFoundException inside model creation;
  * a line-1 clip the engine cannot load is stored as null and handed to ``Animation.AddClip`` unguarded --
    so only a clip the engine's by-name load resolves is listed (a stock ANH name whose token-owner model the
    GEO table knows: ``catalog.animation_folder``, the same rule the script ops' own adds go through). A raw or
    minted id outside the stock table is left to the script op that adds it, exactly as before.
"""
from __future__ import annotations

from . import catalog
from ._animdb_all import ANIMATIONS
from ._modeldb import MODELS
from .eb.model import EbScript

# opcode -> the operand index that holds a clip id (Memoria EventEngine.DoEventCode)
CLIP_ARG = {
    0x33: 0,    # SetStandAnimation
    0x34: 0,    # SetWalkAnimation
    0x35: 0,    # SetRunAnimation
    0x40: 0,    # RunAnimation
    0x52: 0,    # SetInactiveAnimation -- the player's idle fidget; NOT one of the five re-added slots
    0x7A: 0,    # SetLeftAnimation
    0x7B: 0,    # SetRightAnimation
    0x94: 0,    # SetJumpAnimation -- not re-added either
    0xBD: 1,    # RunAnimationEx(entry, anim)
    0x119: 2,   # SetLogicalAnimationEx(entry, kind, anim)
}
SET_MODEL_OP = 0x2F                     # SetModel(model, animset)


def scan(eb: bytes) -> tuple[set, set]:
    """``(clip ids, model ids)`` every entry of one ``.eb`` names as an immediate operand."""
    script = EbScript.from_bytes(eb)
    clips, models = set(), set()
    for entry in script.entries:
        if entry.empty:
            continue
        for func in entry.funcs:
            for ins in script.instrs(func):
                if ins.op in CLIP_ARG:
                    v = ins.imm(CLIP_ARG[ins.op])
                    if v is not None:
                        clips.add(int(v))
                elif ins.op == SET_MODEL_OP:
                    v = ins.imm(0)
                    if v is not None:
                        models.add(int(v))
    return clips, models


def _family(name: str):
    """(group, token) of a GEO model or ANH clip name -- the join a model's clips share across forms."""
    if name.startswith("ANH_"):
        s = catalog.split_anh(name)
        return (s[0], s[2]) if s else None
    p = name.split("_")
    return (p[1], p[3]) if len(p) > 3 and p[0] == "GEO" else None


def event_animation_text(ebs) -> "str | None":
    """The ``EVT_<name>.txt`` body for a field whose per-language ``.eb`` bytes are ``ebs`` (the clips of every
    language, unioned), or None when the field plays no listable clip. Each model the script creates, and each
    clip's own token-owner model, gets a line of every listed clip of its (group, token) family -- a clip of
    another form is only ADDED, never played, so the over-list is harmless; a model the field never creates
    is never looked up."""
    clips, models = set(), set()
    for eb in ebs:
        c, m = scan(eb)
        clips |= c
        models |= m
    names = sorted({ANIMATIONS[a] for a in clips
                    if a in ANIMATIONS and catalog.animation_folder(a) is not None})
    if not names:
        return None
    keys = {MODELS[m] for m in models if m in MODELS}
    for nm in names:
        s = catalog.split_anh(nm)
        keys.add(f"GEO_{s[0]}_{s[1]}_{s[2]}")
    lines = ["animation:" + ",".join(names)]
    for key in sorted(keys):
        fam = _family(key)
        own = [nm for nm in names if fam is not None and _family(nm) == fam]
        if own:
            lines.append(f"{key}:" + ",".join(own))
    return "\n".join(lines) + "\n"
