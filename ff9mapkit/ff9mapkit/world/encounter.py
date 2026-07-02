"""Overworld ENCOUNTER-RATE authoring -- retune the random-battle frequency in the world ``.eb`` (no DLL).

The overworld encounter roll is ``p = 1 / (w_frameEventBattleProb + 1)`` per eligible frame (``ff9.cs:4235``;
gated on moving + topograph 36-38 + a >400-frame settle). ``w_frameEventBattleProb`` is **not** hardcoded -- each
world-state dispatcher (``EVT_WORLD_WORLDxx`` = ``EventDB[9000..9012]``) SETS it from its own ``.eb`` via the
``RunWorldCode`` opcode (``0xC4``, ``EventEngine.DoEventCode.cs:2485``) with world-function **26**
(``w_frameSetParameter`` case 26 -> ``w_frameEventBattleProb``, ``ff9.cs:3920``). So retuning the encounter rate is a
pure ``.eb`` immediate rewrite -- the SAME surface as ``world-entrance`` / ``reveal_markers`` -- with **no engine
change and no world-pack codec** (that heavier axis is the monster *table*; this is just the *rate*).

**The shipping layout** (probed from all 13 dispatchers, every language): the 9 free-roam states
(9000/02/03/05/07/08/09/10/11) each carry exactly **2** immediate SET-26 writes -- entry-0 tag-0 (``Main_Init``, the
load-time default) and entry-0 tag-10 (``Main_Reinit``, the after-battle restore); the 4 cutscene states
(9001/04/06/12) carry none. The game ships only two danger values: ``prob 231`` (p=1/232, the standard rate) and
``prob 365`` (p=1/366, the gentler disc-1 free-roam ``Main_Init`` rate, which normalizes to 232 after the first
battle). Every language carries the same writes (JP at different byte offsets -- its dispatcher layout differs -- so
each language's OWN copy is patched in place).

Three knobs (mutually exclusive):
  * ``multiplier`` -- an encounter-**frequency** multiplier: ``2.0`` = twice as many encounters, ``0.5`` = half.
    Preserves the game's relative danger structure (scales the period ``prob+1``, so 366 stays proportionally
    rarer than 232). Idempotent across re-runs: the source value is always the pristine dispatcher's, not the
    already-scaled override.
  * ``set_prob`` -- force an absolute ``w_frameEventBattleProb`` everywhere (advanced; p = 1/(set_prob+1)).
  * ``peaceful`` -- a near-encounter-free overworld (``prob = 0xFFFF`` -> p = 1/65536).

Deploy is a per-language ``.eb`` shadow into the mod folder (stacking on any ``world-entrance`` edit); RELAUNCH or
re-enter the overworld to apply.
"""
from __future__ import annotations

WPRM = 0xC4                 # RunWorldCode opcode (EventEngine.DoEventCode.cs:2485)
FUNC_ENCOUNT = 26           # w_frameSetParameter function id -> w_frameEventBattleProb (ff9.cs:3920)
PROB_MAX = 0xFFFF           # w_frameEventBattleProb is UInt16
# world .eb mod path + languages -- shared with world/entrance.py (same dispatcher assets)
_WORLD_EB_SUBDIR = "StreamingAssets/assets/resources/commonasset/eventengine/eventbinary/world"
LANGS = ("us", "uk", "jp", "es", "fr", "gr", "it")


# --------------------------------------------------------------------------- the rate math

def transform_prob(prob: int, *, multiplier=None, set_prob=None, peaceful: bool = False) -> int:
    """Map a source ``w_frameEventBattleProb`` to its retuned value (clamped to 0..65535).

    ``peaceful`` -> ``PROB_MAX`` (encounters ~never). ``set_prob`` -> that absolute value. ``multiplier`` -> scale
    the *frequency*: new period = ``(prob+1) / multiplier``, so ``multiplier=2`` halves the period (2x encounters).
    Exactly one mode must be given."""
    if peaceful:
        return PROB_MAX
    if set_prob is not None:
        return max(0, min(PROB_MAX, int(set_prob)))
    if multiplier is not None:
        if not (isinstance(multiplier, (int, float)) and not isinstance(multiplier, bool)) or multiplier <= 0:
            raise ValueError(f"multiplier must be a positive number (got {multiplier!r}); use peaceful=True to disable")
        new_period = (int(prob) + 1) / float(multiplier)
        return max(0, min(PROB_MAX, int(round(new_period)) - 1))
    raise ValueError("give exactly one of multiplier / set_prob / peaceful")


def _validate_mode(multiplier, set_prob, peaceful):
    given = [k for k, v in (("multiplier", multiplier), ("set", set_prob), ("peaceful", peaceful or None))
             if v is not None]
    if len(given) != 1:
        raise ValueError(f"give exactly one of --multiplier / --set / --peaceful (got: {given or 'none'})")
    transform_prob(232, multiplier=multiplier, set_prob=set_prob, peaceful=peaceful)   # surface a bad value early


# --------------------------------------------------------------------------- locate + rewrite the SET-26 writes

def rate_writes(data: bytes):
    """Yield ``(entry_index, func_tag, ordinal, Instr)`` for each ``RunWorldCode(26, <immediate>)`` in ``data``
    (a world dispatcher ``.eb``). Only the immediate form is yielded (an expression-valued rate can't be statically
    retuned); such writes are absent in the shipping dispatchers but a caller can compare counts if paranoid.
    ``ordinal`` disambiguates repeats within one ``(entry, tag)`` (always 0 in shipping data -- 1 write per func)."""
    from ..eb.model import EbScript
    s = EbScript(data)
    seen: dict = {}
    for e in s.entries:
        for f in e.funcs:
            for i in s.instrs(f):
                if i.op == WPRM and i.imm(0) == FUNC_ENCOUNT and len(i.arg_is_expr) >= 2 and not i.arg_is_expr[1]:
                    key = (e.index, f.tag)
                    ordv = seen.get(key, 0)
                    seen[key] = ordv + 1
                    yield (e.index, f.tag, ordv, i)


def apply_encounter_rate(data: bytes, *, pristine: bytes | None = None,
                         multiplier=None, set_prob=None, peaceful: bool = False):
    """Return ``(new_bytes, changes)`` -- ``data`` with every immediate SET-26 encounter-rate write retuned.

    A pure in-place 2-byte rewrite of each write's ``v2`` immediate (instruction length is preserved, so all offsets
    -- and any ``world-entrance`` additions in ``data`` -- stay intact). If ``pristine`` is given, each write's SOURCE
    value is read from it (matched by ``entry/tag/ordinal``) so ``--multiplier`` is idempotent across re-runs even
    when ``data`` is an already-retuned override; otherwise the source is ``data``'s own current value.
    ``changes`` = ``[{entry, tag, from, to, off}]``."""
    _validate_mode(multiplier, set_prob, peaceful)
    b = bytearray(data)
    pmap: dict = {}
    if pristine is not None:
        for (ei, tag, ordv, instr) in rate_writes(pristine):
            pmap[(ei, tag, ordv)] = instr.imm(1) & 0xFFFF
    changes = []
    for (ei, tag, ordv, instr) in rate_writes(data):
        src = pmap.get((ei, tag, ordv), instr.imm(1) & 0xFFFF)
        new = transform_prob(src, multiplier=multiplier, set_prob=set_prob, peaceful=peaceful)
        voff = instr.end - 2                              # v2 is the trailing 2-byte LE immediate
        b[voff] = new & 0xFF
        b[voff + 1] = (new >> 8) & 0xFF
        changes.append({"entry": ei, "tag": tag, "from": src, "to": new, "off": voff})
    return bytes(b), changes


# --------------------------------------------------------------------------- deploy

def deploy_encounter_rate(*, mod_folder: str, game=None, multiplier=None, set_prob=None, peaceful: bool = False,
                          langs=None, dry_run: bool = False) -> dict:
    """Retune the overworld encounter rate across every dispatcher, per language, into the mod folder.

    Reads each dispatcher STACKED (an already-deployed mod-folder ``.eb`` override if present -- so this composes
    with ``world-entrance`` -- else the pristine p0data dispatcher), retunes, and writes the ``.eb`` back under
    ``<mod>/<world-eb-subdir>/<lang>/EVT_WORLD_WORLDxx.eb.bytes``. Returns a summary. RELAUNCH / re-enter the
    overworld to apply. Raises ``ValueError`` on a bad mode."""
    from pathlib import Path
    from .. import config
    from . import entrance as _entrance
    _validate_mode(multiplier, set_prob, peaceful)
    langs = list(langs) if langs else list(LANGS)
    alld = _entrance.load_all_dispatchers(game)           # {name: {lang: pristine bytes}}
    root = config.find_mod_root(config.find_game_path(game), mod_folder)
    eb_root = Path(root) / _WORLD_EB_SUBDIR
    summary = {"mode": ("peaceful" if peaceful else f"set={set_prob}" if set_prob is not None
                        else f"multiplier={multiplier}"),
               "langs": langs, "dry_run": dry_run, "dispatchers": [], "written": [], "skipped_no_writes": []}
    for name in sorted(alld):
        us = alld[name].get("us")
        if not us or not any(True for _ in rate_writes(us)):
            summary["skipped_no_writes"].append(name)     # cutscene state (9001/04/06/12) -> no encounter logic
            continue
        fname = name.upper() + ".eb.bytes"
        disp_report = {"name": name, "writes": None}
        for lang in langs:
            pristine = alld[name].get(lang)
            if pristine is None:
                continue
            mod_p = eb_root / lang / fname
            base = mod_p.read_bytes() if mod_p.is_file() else pristine
            out, changes = apply_encounter_rate(base, pristine=pristine, multiplier=multiplier,
                                                set_prob=set_prob, peaceful=peaceful)
            if not changes:
                continue
            if lang == "us" or disp_report["writes"] is None:
                disp_report["writes"] = [{"entry": c["entry"], "tag": c["tag"], "from": c["from"], "to": c["to"]}
                                         for c in changes]
            if not dry_run:
                mod_p.parent.mkdir(parents=True, exist_ok=True)
                mod_p.write_bytes(out)
            summary["written"].append(str(mod_p))
        summary["dispatchers"].append(disp_report)
    return summary
