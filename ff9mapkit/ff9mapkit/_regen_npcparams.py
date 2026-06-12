"""Regenerate ``_npcparams.py`` -- the per-model NPC OBJECT params (animset / head-focus / logical-size /
movement clips) that :func:`ff9mapkit.content.npc.build_npc_init` uses to emit a byte-faithful standing NPC
for ANY model, not just moogles.

We scan every real field's ``.eb`` for non-player object entries (those WITHOUT ``DefinePlayerCharacter``),
read each one's Init -- ``SetModel`` (model + animset), ``SetObjectLogicalSize``, ``SetHeadFocusMask``, and
the five movement-anim setters (ops 0x33/0x34/0x35/0x7A/0x7B) -- and bake, per model, the MODAL (most common)
value of each. Only ``GEO_NPC_*`` / ``GEO_MON_*`` models with a COMPLETE set (animset + head-focus +
logical-size + five clips) are kept: those are the real standing-NPC/creature rigs. Party (``GEO_MAIN``) and
accessory (``GEO_ACC``) models are excluded -- party characters are the player's job and accessories are
props (their own ``inject_prop`` path), so they must not drive generic NPC synthesis.

Provenance: the output is DERIVED METADATA (model ids + small ints only -- no Square-Enix bytes), exactly
like ``_modeldb`` / ``_animdb``. Run with the install reachable (``$FF9_GAME_PATH`` or run from the game dir):

    python -m ff9mapkit._regen_npcparams
"""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

# op -> the movement-clip slot it sets (the from-scratch Init's five setters, in ANIM_ORDER)
_ANIM_OPS = {0x33: "stand", 0x34: "walk", 0x35: "run", 0x7A: "left", 0x7B: "right"}
_SLOTS = ("stand", "walk", "run", "left", "right")


def _scan() -> dict:
    """``{model: {animset, head_focus, logical_size, anims}}`` -- the modal real-NPC params per model."""
    from . import extract
    from .eb import EbScript
    from ._modeldb import MODELS

    bundle = extract.EventBundle()
    acc: dict = defaultdict(lambda: {"animset": Counter(), "hf": Counter(), "ls": Counter(), "anims": Counter()})
    for fid in extract.ID_TO_FBG:
        eb_bytes = bundle.eb_for_id(fid)
        if not eb_bytes:
            continue
        try:
            eb = EbScript.from_bytes(eb_bytes)
        except Exception:                                  # noqa: BLE001 -- a field we can't parse: skip
            continue
        for e in eb.entries:
            if e.empty:
                continue
            f0 = e.func_by_tag(0)
            if f0 is None:
                continue
            ins = list(eb.instrs(f0))
            if any(i.op == 0x2C for i in ins):             # the player (DefinePlayerCharacter) -- not an NPC
                continue
            sm = next((i for i in ins if i.op == 0x2F), None)
            if sm is None:
                continue
            model, animset = int(sm.args[0]), int(sm.args[1])
            a = acc[model]
            a["animset"][animset] += 1
            ls = next((tuple(i.args) for i in ins if i.op == 0x4B), None)
            if ls:
                a["ls"][ls] += 1
            hf = next((tuple(i.args) for i in ins if i.op == 0x8B), None)
            if hf:
                a["hf"][hf] += 1
            clips = {}
            for i in ins:
                if i.op in _ANIM_OPS and _ANIM_OPS[i.op] not in clips:
                    clips[_ANIM_OPS[i.op]] = int(i.args[0])
            if len(clips) == 5:
                a["anims"][tuple(clips[s] for s in _SLOTS)] += 1

    out = {}
    for model, c in acc.items():
        name = MODELS.get(model, "")
        if not (name.startswith("GEO_NPC") or name.startswith("GEO_MON")):
            continue                                       # only real NPC / creature rigs (no party / accessory)
        if not (c["animset"] and c["hf"] and c["ls"] and c["anims"]):
            continue                                       # incomplete -> the defaults in npc.py cover it
        anims = c["anims"].most_common(1)[0][0]
        out[model] = {
            "animset": c["animset"].most_common(1)[0][0],
            "head_focus": tuple(c["hf"].most_common(1)[0][0]),
            "logical_size": tuple(c["ls"].most_common(1)[0][0]),
            "anims": {s: anims[i] for i, s in enumerate(_SLOTS)},
        }
    return out


def _render(params: dict) -> str:
    from ._modeldb import MODELS
    L = ['"""Auto-generated per-model NPC OBJECT params -- the canonical (modal) animset / head-focus /',
         "logical-size / movement clips real standing NPCs use, so ``content.npc.build_npc_init`` emits a",
         "byte-faithful NPC for any GEO_NPC_* / GEO_MON_* model (not just moogles).",
         "",
         "DO NOT EDIT BY HAND. Regenerate with:  python -m ff9mapkit._regen_npcparams",
         "Provenance: derived metadata (model ids + small ints), no Square-Enix bytes.",
         '"""',
         "",
         "NPC_PARAMS = {"]
    for model in sorted(params):
        p = params[model]
        a = p["anims"]
        L.append(f"    {model}: {{  # {MODELS.get(model, '?')}")
        L.append(f"        \"animset\": {p['animset']}, \"head_focus\": {p['head_focus']}, "
                 f"\"logical_size\": {p['logical_size']},")
        L.append(f"        \"anims\": {{\"stand\": {a['stand']}, \"walk\": {a['walk']}, \"run\": {a['run']}, "
                 f"\"left\": {a['left']}, \"right\": {a['right']}}},")
        L.append("    },")
    L.append("}")
    L.append("")
    return "\n".join(L)


def main() -> int:
    params = _scan()
    dest = Path(__file__).resolve().parent / "_npcparams.py"
    dest.write_text(_render(params), encoding="utf-8", newline="\n")
    print(f"wrote {dest}  ({len(params)} models)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
