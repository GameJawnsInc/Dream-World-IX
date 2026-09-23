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

Provenance: DERIVED METADATA (model ids + small ints -- no Square-Enix bytes), exactly like
``_npcparams``. Run with the install reachable (``$FF9_GAME_PATH`` or run from the game dir):

    python -m ff9mapkit._regen_shadowparams
"""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from ._regen_stamp import stamp_line

MIN_INTENSITY_VOTES = 5      # below this many fields, a model's intensity is one room's light -> use DEFAULT's


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


def _scan() -> tuple:
    """``(per_model, overall, fields)`` -- per model ``{"size": Counter, "intensity": Counter}`` of the
    engine's effective values, one vote per (field, model); ``overall`` the same over every vote."""
    from . import extract, mapconfig
    from .eb import EbScript

    bundle = extract.EventBundle()
    mcfs = _mapconfigs()
    acc: dict = defaultdict(lambda: {"size": Counter(), "intensity": Counter()})
    overall = {"size": Counter(), "intensity": Counter()}
    fields = 0
    for fid, evt in extract.ID_TO_EVT.items():
        eb_bytes = bundle.eb_for_id(fid)
        mcf = mcfs.get(evt.lower())
        if not eb_bytes or mcf is None:
            continue
        try:
            eb = EbScript.from_bytes(eb_bytes)
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
    return acc, overall, fields


def _render(per_model: dict, overall: dict, fields: int, *, stamp: str) -> str:
    from ._modeldb import MODELS
    L = ['"""Auto-generated per-model field BLOB SHADOW -- ``(size, intensity)`` = the modal MapConfigData',
         "``shadowR`` / ``shadowI`` real fields apply to each model (``fldmcf.ff9fieldMCFService``), one vote",
         f"per (field, model) over {fields} shipping fields. :mod:`ff9mapkit.content.shadow` emits them as",
         "``SetShadowSize(size, size)`` + ``SetShadowAmplifier(intensity << 3)`` -- the same two engine calls.",
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
    L.append("")
    return "\n".join(L)


def main() -> int:
    per_model, overall, fields = _scan()
    dest = Path(__file__).resolve().parent / "_shadowparams.py"
    dest.write_text(_render(per_model, overall, fields,
                            stamp=stamp_line("install", "_regen_shadowparams.py")),
                    encoding="utf-8", newline="\n")
    print(f"wrote {dest}  ({len(per_model)} models over {fields} fields)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
