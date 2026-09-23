"""Regenerate ``_shadowparams.py`` -- the per-model field BLOB SHADOW (size + intensity) real fields give each
model, so :mod:`ff9mapkit.content.shadow` can cast the stock shadow under a kit-field actor.

A real field never scripts its actors' shadows: its MapConfigData (:mod:`ff9mapkit.mapconfig`) does, per
field and per model, through ``fldmcf.ff9fieldMCFService``. So the census reads BOTH halves of every shipping
field -- the ``.eb`` for WHICH models appear (every object Init's literal ``SetModel``, the player's included),
the MCF for WHAT the engine then applies to each (:meth:`MapConfig.effective_shadow`: the model's own row else
the ``0xFFFF`` default row, plus the default light) -- and each field votes ONCE per model it shows. Per model
we bake the MODAL ``shadowR`` (the SIZE -- it tracks the model: Zidane 9, Garnet 8, Steiner 11, Quina 16) and
the modal ``shadowI`` (the INTENSITY -- it tracks the room's light, so it is mostly 3-4 everywhere), as two
separate marginals, because the engine applies them independently. ``DEFAULT`` is the same pair over every
vote, for a model no real field shows (a minted/custom model). Because intensity is the ROOM's more than the
model's, a model seen in fewer than ``MIN_INTENSITY_VOTES`` fields takes ``DEFAULT``'s intensity -- one room's
light is not that model's shadow (a 1-vote rig would otherwise bake a near-invisible ``shadowI = 1``).

THE SECOND TABLE, ``STOCK_CASTS``, is the SCRIPT half: whether stock lets that model's shadow show at all. The
MCF gives every actor a shadow, but an object's Init can ``DisableShadow`` (0x80) it, and stock does exactly
that to most set dressing -- 476 of the 556 free-standing accessory objects that are not chests (the tent, the
save book, the letter, the cactus) -- while its chests (all but 3 of 224) and casks keep theirs. So per model, over every stock object wearing it whose
Init ``SetModel``\\ s it literally and which is NOT an ``AttachObject`` target (a held item disables its shadow
for a different reason -- 139 of 140 do), an object votes "disabled" when a ``DisableShadow`` block
DOMINATES every exit of its Init (:class:`ff9mapkit.eb.cfg.FuncFlow` -- on every path, not behind a story
branch), else "casts"; the majority wins and a tie goes to "disabled" (``_modal``'s smaller value). This is
what a ``[[prop]]`` follows; ``PROP_DEFAULT_CASTS`` covers a model no stock object shows standing free.

Provenance: DERIVED METADATA (model ids + small ints -- no Square-Enix bytes), exactly like
``_npcparams``. Run with the install reachable (``$FF9_GAME_PATH`` or run from the game dir):

    python -m ff9mapkit._regen_shadowparams
"""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from ._regen_stamp import stamp_line

MIN_INTENSITY_VOTES = 5      # below this many fields, a model's intensity is one room's light -> use DEFAULT's
DISABLE_SHADOW = 0x80        # SHADOWOFF -> ff9shadow.FF9ShadowOffField: char attr bit 16, the quad's renderer off
ATTACH_OBJECT = 0x4C         # AttachObject(attachedUid, carryingUid, bone)
INIT_OBJECT = 0x09           # InitObject(entry, uid) -- uid 0 = the entry's own index


def _modal(c: Counter) -> int:
    """The most common value; a tie goes to the SMALLER value so the table is deterministic."""
    return min(c.items(), key=lambda kv: (-kv[1], kv[0]))[0]


def _mapconfigs() -> dict:
    """``{evt_name_lower: MCF bytes}`` straight out of the field event bundle (where MapConfigData lives)."""
    from . import extract
    env = extract._load_env(extract._streaming_assets() / extract._events_bundle())
    marker = "commonasset/mapconfigdata/"
    out = {}
    for k, obj in env.container.items():
        kl = k.lower()
        i = kl.find(marker)
        if i >= 0 and kl.endswith(".bytes"):
            out[kl[i + len(marker):-len(".bytes")]] = extract._raw_bytes(obj.read())
    return out


def _disables_on_every_path(eb, f0) -> bool:
    """True when a ``DisableShadow`` block of the Init ``f0`` dominates every exit of it -- the object's
    shadow is off whichever way its Init runs. Raises :class:`ff9mapkit.eb.cfg.CfgError` on an Init the
    flow analysis cannot soundly read (the caller skips and counts it)."""
    from .eb.cfg import FuncFlow
    from .eb.disasm import jump_target
    fl = FuncFlow.build(eb.data, f0.abs_start, f0.abs_end)
    offs = [b.index for b in fl.blocks if any(i.op == DISABLE_SHADOW for i in b.instrs)]
    if not offs:
        return False
    dom = fl._dom                                           # per-block dominator bitmask, 0 = unreachable
    exits = [b.index for b in fl.blocks if dom[b.index]
             and (not b.succs or (b.instrs[-1].op in (0x01, 0x02, 0x03)
                                  and jump_target(b.instrs[-1]) == f0.abs_end))]
    return bool(exits) and any(all((dom[e] >> d) & 1 for e in exits) for d in offs)


def _cast_votes(eb) -> dict:
    """``{model: Counter("casts"/"disabled")}`` for one field -- one vote per free-standing object (see the
    module docstring): its Init's literal ``SetModel``, skipped when the object is an ``AttachObject``
    target anywhere in the script (matched by uid: ``InitObject``'s, else the entry index)."""
    from .eb.cfg import CfgError
    uids, attached = defaultdict(set), set()
    for e in eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            for ins in eb.instrs(f):
                if ins.op == INIT_OBJECT and ins.imm(0) is not None:
                    uids[ins.imm(0)].add(ins.imm(1) or ins.imm(0))
                elif ins.op == ATTACH_OBJECT and ins.imm(0) is not None:
                    attached.add(ins.imm(0))
    out: dict = defaultdict(Counter)
    for e in eb.entries:
        f0 = None if e.empty else e.func_by_tag(0)
        if f0 is None:
            continue
        sm = next((i for i in eb.instrs(f0) if i.op == 0x2F), None)
        if sm is None or sm.imm(0) is None or (uids.get(e.index, set()) | {e.index}) & attached:
            continue
        try:
            off = _disables_on_every_path(eb, f0)
        except CfgError:                                    # an Init the flow can't soundly read: no vote
            continue
        out[int(sm.imm(0))]["disabled" if off else "casts"] += 1
    return out


def _scan() -> tuple:
    """``(per_model, overall, fields, casts)`` -- per model ``{"size": Counter, "intensity": Counter}`` of
    the engine's effective values, one vote per (field, model); ``overall`` the same over every vote;
    ``casts`` per model the ``Counter("casts"/"disabled")`` of its free-standing stock objects
    (:func:`_cast_votes`, every field with a script -- the MCF is not consulted)."""
    from . import extract, mapconfig
    from .eb import EbScript

    bundle = extract.EventBundle()
    mcfs = _mapconfigs()
    acc: dict = defaultdict(lambda: {"size": Counter(), "intensity": Counter()})
    overall = {"size": Counter(), "intensity": Counter()}
    casts: dict = defaultdict(Counter)
    fields = 0
    for fid, evt in extract.ID_TO_EVT.items():
        eb_bytes = bundle.eb_for_id(fid)
        mcf = mcfs.get(evt.lower())
        if not eb_bytes:
            continue
        try:
            eb = EbScript.from_bytes(eb_bytes)
        except Exception:                                  # noqa: BLE001 -- a field we can't parse: skip
            continue
        for m, c in _cast_votes(eb).items():
            casts[m].update(c)
        if mcf is None:
            continue
        try:
            mc = mapconfig.parse(mcf)
        except Exception:                                  # noqa: BLE001 -- a field we can't parse: skip
            continue
        models = set()
        for e in eb.entries:
            if e.empty:
                continue
            f0 = e.func_by_tag(0)
            if f0 is None:
                continue
            sm = next((i for i in eb.instrs(f0) if i.op == 0x2F), None)
            if sm is None or any(sm.arg_is_expr):
                continue
            models.add(int(sm.args[0]))
        if not models:
            continue
        fields += 1
        for m in models:
            eff = mc.effective_shadow(m)
            if eff is None:
                continue
            si, sr = eff
            for bucket in (acc[m], overall):
                bucket["size"][sr] += 1
                bucket["intensity"][si] += 1
    return acc, overall, fields, casts


def _render(per_model: dict, overall: dict, fields: int, casts: dict, *, stamp: str) -> str:
    from ._modeldb import MODELS
    L = ['"""Auto-generated per-model field BLOB SHADOW -- ``(size, intensity)`` = the modal MapConfigData',
         "``shadowR`` / ``shadowI`` real fields apply to each model (``fldmcf.ff9fieldMCFService``), one vote",
         f"per (field, model) over {fields} shipping fields. :mod:`ff9mapkit.content.shadow` emits them as",
         "``SetShadowSize(size, size)`` + ``SetShadowAmplifier(intensity << 3)`` -- the same two engine calls.",
         "``STOCK_CASTS`` is the script half: whether stock lets a model's shadow show at all (its free-standing",
         "objects' Inits ``DisableShadow`` it on every path, or not) -- what a ``[[prop]]`` follows.",
         "",
         "DO NOT EDIT BY HAND. Regenerate with:  python -m ff9mapkit._regen_shadowparams",
         "Provenance: derived metadata (model ids + small ints), no Square-Enix bytes.",
         '"""',
         stamp,
         "",
         "# a model no shipping field shows (minted / custom): the modal pair over every vote",
         f"DEFAULT = ({_modal(overall['size'])}, {_modal(overall['intensity'])})",
         "",
         f"# model id: (size, intensity)    # name, field votes  (under {MIN_INTENSITY_VOTES} votes the intensity is DEFAULT's)",
         "SHADOW_PARAMS = {"]
    default_i = _modal(overall["intensity"])
    for m in sorted(per_model):
        c = per_model[m]
        votes = sum(c["size"].values())
        si = _modal(c["intensity"]) if votes >= MIN_INTENSITY_VOTES else default_i
        L.append(f"    {m}: ({_modal(c['size'])}, {si}),    # {MODELS.get(m, '?')}, {votes}")
    L.append("}")
    verdict = {m: _modal(Counter({1: c["casts"], 0: c["disabled"]})) == 1 for m, c in casts.items()}
    acc = [m for m in verdict if MODELS.get(m, "").startswith("GEO_ACC_")]
    acc_casting = sum(verdict[m] for m in acc)
    prop_default = _modal(Counter({1: acc_casting, 0: len(acc) - acc_casting})) == 1
    L += ["",
          "# a [[prop]] whose model no stock object shows standing free (minted / custom / only ever held): the",
          f"# verdict of stock's set-dressing models -- {acc_casting} of {len(acc)} GEO_ACC_* models cast one",
          f"PROP_DEFAULT_CASTS = {prop_default}",
          "",
          "# model id: does stock let its shadow show?    # name, free-standing objects casting / disabled",
          "STOCK_CASTS = {"]
    for m in sorted(casts):
        c = casts[m]
        L.append(f"    {m}: {verdict[m]},    # {MODELS.get(m, '?')}, {c['casts']} / {c['disabled']}")
    L.append("}")
    L.append("")
    return "\n".join(L)


def main() -> int:
    per_model, overall, fields, casts = _scan()
    dest = Path(__file__).resolve().parent / "_shadowparams.py"
    dest.write_text(_render(per_model, overall, fields, casts,
                            stamp=stamp_line("install", "_regen_shadowparams.py")),
                    encoding="utf-8", newline="\n")
    n_cast = sum(1 for c in casts.values() if c["casts"] > c["disabled"])
    print(f"wrote {dest}  ({len(per_model)} models over {fields} fields; {n_cast} of {len(casts)} cast)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
