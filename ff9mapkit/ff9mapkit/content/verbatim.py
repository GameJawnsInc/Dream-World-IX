"""Verbatim-`.eb` fork -- ship a real field's WHOLE event script instead of re-synthesizing it.

The faithful realization of "entry-0 carry" (docs/FORK_FIDELITY.md): a story field's entry-0 ``Main_Init``
arms its objects/regions and gates the cast by ScenarioCounter, and the gated doors read MAP vars it sets --
so the only way those references resolve is to keep the donor's WHOLE entry layout. This mode does exactly
that: the build ships the donor's `.eb` verbatim (entry-0 + every object + every gateway, slots intact) and
only **remaps the `Field()` destinations**; the field then runs its real logic. Proven in-game on Dali Inn
(the gated door opens, the cast gates by story beat).

The declarative content blocks ([[npc]]/[[gateway]]/...) are NOT used in this mode -- the `.eb` is whole, so
there is nothing to synthesize. Pair with a `[startup]` block to boot a chosen beat. LIMITS (vs a perfect
clone): the donor `.mes` text is a separate carry (TXIDs may not resolve until then), and a fork reached by
debug-menu warp has no entrance fade to mask first-frame model streaming.

PER-LANGUAGE bytecode. A field's event script is NOT language-identical: only 238 of 818 stock fields match
across the 7 languages once the name block is masked -- dialogue-window operands, text-pacing waits and voice
sound ids differ, and 94 fields differ in LENGTH (studies/eb-roundtrip/FINDINGS.md). So ``bin`` holds the
``us`` donor and import captures every other language's own donor beside it as ``<bin stem>.<lang><ext>``
(``X.verbatim_eb.bin`` -> ``X.verbatim_eb.jp.bin``; :func:`lang_bin_rel`). The build ships each language its
own donor, each Field()-remapped the same way; a language with no captured donor falls back to ``us`` and the
build says so. The siblings are found by name, so an older fork's toml needs no edit -- re-import it (or
``fetch-assets --force`` for a campaign) to capture them.
"""
from __future__ import annotations

import json
import struct

from ..eb import EbScript

FIELD_OP = 0x2B           # Field(dest) -- the warp; dest is a 2-byte literal at instruction offset +2
BASE_LANG = "us"          # the language ``[verbatim_eb] bin`` holds; every other language is a sibling of it


def remap_fields(eb_bytes: bytes, retarget: dict) -> bytes:
    """Patch every ``Field(id)`` literal whose id is in ``retarget`` (real destination -> fork id). Ids NOT in
    the map are left as live seams (the door warps back into the real game). Empty ``retarget`` -> unchanged."""
    if not retarget:
        return eb_bytes
    eb = EbScript.from_bytes(eb_bytes)
    buf = bytearray(eb_bytes)
    for e in eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            for i in eb.instrs(f):
                if i.op == FIELD_OP and i.imm(0) in retarget:
                    struct.pack_into("<H", buf, i.off + 2, int(retarget[i.imm(0)]) & 0xFFFF)
    return bytes(buf)


def render_retarget(dests, id_remap=None):
    """The ``[verbatim_eb] retarget`` portion for a verbatim fork's ``Field()`` exits, plus the count of
    exits actually retargeted.

    ``dests`` = the field's distinct ``Field(id)`` destinations (real ids). With ``id_remap`` (a
    ``{real_id: fork_id}`` map from import-chain) this emits a LIVE ``retarget = {...}`` table for the
    in-chain destinations and a comment listing the rest (left as live seams back into the real game) --
    so a forked CHAIN's doors warp into its OWN member forks. Without ``id_remap`` (single-field
    ``import --verbatim``) it emits the commented-out fill-in template the author edits by hand, BYTE-FOR-BYTE
    as before (so the single-field golden is unchanged). Returns ``(toml_text, n_retargeted)``."""
    dests = list(dests)
    if id_remap:
        inchain = [(d, int(id_remap[d])) for d in dests if d in id_remap]
        if inchain:
            seams = [d for d in dests if d not in id_remap]
            tbl = "retarget = { " + ", ".join(f"{a} = {b}" for a, b in inchain) + " }\n"
            note = ("# (the rest are live seams back into the real game -- not in this chain: "
                    + ", ".join(map(str, seams)) + ")\n") if seams else ""
            return tbl + note, len(inchain)
    body = "".join(f"#   {d} = 0\n" for d in dests) or "#   (this field has no Field() exits)\n"
    return ("# retarget = {\n" + body + "# }\n"), 0


def lang_bin_rel(bin_rel: str, lang: str) -> str:
    """Where ``lang``'s own donor `.eb` sits beside the ``us`` ``bin``: the language goes before the extension
    (``X.verbatim_eb.bin`` -> ``X.verbatim_eb.jp.bin``; no extension -> ``X.jp``). ``us`` is ``bin`` itself."""
    if lang == BASE_LANG:
        return bin_rel
    cut = max(bin_rel.rfind("/"), bin_rel.rfind("\\")) + 1
    head, base = bin_rel[:cut], bin_rel[cut:]
    stem, dot, ext = base.rpartition(".")
    return head + (f"{stem}.{lang}.{ext}" if dot and stem else f"{base}.{lang}")


def has_lang_donor(project, lang: str) -> bool:
    """Does this verbatim fork carry ``lang``'s OWN donor `.eb`? ``us`` always does (it is ``bin``); any other
    language only when import captured its sibling (:func:`lang_bin_rel`). ``False`` for a non-verbatim
    project."""
    spec = project.raw.get("verbatim_eb")
    if not spec or not spec.get("bin"):
        return False
    return lang == BASE_LANG or project.path(lang_bin_rel(spec["bin"], lang)).is_file()


def verbatim_eb(project, lang: str = BASE_LANG):
    """The verbatim `.eb` to ship for ``project`` in ``lang`` (from its ``[verbatim_eb]`` block, ``bin`` +
    optional ``retarget``), Field-remapped -- or ``None`` if the project isn't a verbatim fork (the build then
    synthesizes from the field.toml as usual). The bytecode is per-language (see the module docstring): this
    reads ``lang``'s own captured donor, or the ``us`` ``bin`` when that language has none
    (:func:`has_lang_donor` tells the two apart; the build warns on the fallback). The retarget is applied to
    whichever file is read -- :func:`remap_fields` self-locates, so it is right for every language's layout."""
    spec = project.raw.get("verbatim_eb")
    if not spec or not spec.get("bin"):
        return None
    retarget = {int(k): int(v) for k, v in (spec.get("retarget") or {}).items()}
    rel = lang_bin_rel(spec["bin"], lang) if has_lang_donor(project, lang) else spec["bin"]
    return remap_fields(project.path(rel).read_bytes(), retarget)


def verbatim_mes(project, lang: str):
    """The donor field's WHOLE `.mes` text body to ship for ``lang`` (from the ``[verbatim_eb] text`` JSON
    sidecar, ``{lang: body}``) -- the verbatim `.eb`'s index-txids resolve straight into it. Falls back to the
    ``us`` body for a language the dialogue reader couldn't distinguish. ``None`` if the fork carries no text."""
    spec = project.raw.get("verbatim_eb") or {}
    tf = spec.get("text")
    if not tf:
        return None
    data = json.loads(project.path(tf).read_text(encoding="utf-8"))
    return data.get(lang) or data.get("us")
