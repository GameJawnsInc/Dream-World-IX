"""SAME-LENGTH raw17 ``btlseq`` operand patches -- the first sequence *authoring* step (read = :mod:`seqdis`).

The safest sequence edit is a *literal* one: change one operand in place without moving any bytes -- retime a
``Wait``/``MoveTo*`` frame count, swap an ``Anim`` code or a ``SetCamera`` id, tweak a ``Scale``/``FadeOut``
value. No length change means no ``seqOffset``/``camOffset`` repack and no risk of mis-packing -- byte-accurate by
construction (the seqcodec identity holds), exactly like :mod:`aipatch` (enemy AI) and ``scene_data`` (raw16).

Addressing is by BYTE OFFSET (from ``battle-seq --sites``) + a required OLD-value guard: the patch only applies
if the operand at that offset currently equals ``old`` (a stale/wrong offset fails LOUD instead of corrupting a
byte), and ``new`` must fit the SAME field (width + signedness). raw17 bytecode is language-independent, so a
forked scene ships one raw17 for all languages -- the patch applies once.

This reaches OPERAND LITERALS only (frame counts, ids, masks, coords). Length-changing edits (inserting/removing
instructions, a new sequence) are the deferred assembler/codec-repack tier (:mod:`seqcodec` provides the model).
The 0x19 ``Sfx`` discarded-pad byte is NOT a site (the engine ignores it); the Move ``Next`` advance is not in the
bytes at all (hard-coded in the engine) so there is no Next site to patch.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import seqcodec as _sc


class SeqPatchError(ValueError):
    pass


@dataclass(frozen=True)
class Site:
    """One patchable operand in a sequence body."""
    sub_no: int        # the canonical sub_no (attack index) owning this body (shared bodies: the first slot)
    offset: int        # absolute byte offset of the operand's first byte (the ``at`` you cite)
    width: int         # 1 or 2
    signed: bool
    kind: str          # frames | anim_code | camera | vfx | svfx | sfx | mesh_mask | message | coord | ...
    value: int         # the current decoded value (signed per the field)
    where: str         # human context, e.g. "sub0 Anim anim_code"

    @property
    def vmin(self) -> int:
        return -(1 << (8 * self.width - 1)) if self.signed else 0

    @property
    def vmax(self) -> int:
        return (1 << (8 * self.width - 1)) - 1 if self.signed else (1 << (8 * self.width)) - 1


def _canonical_sub(model: _sc.Raw17, body: _sc.Body) -> int:
    for sub in range(model.seq_count):
        if model.seq_offset[sub] == body.offset:
            return sub
    return -1


def constant_sites(raw17: bytes) -> list:
    """Every patchable operand in a raw17's sequence bodies, in byte order. The ``offset`` of each is the ``at``
    you cite in a ``[[scene.seq_patch]]``; ``battle-seq --sites`` prints them. The 0x19 discarded-pad byte and
    terminator/no-operand opcodes contribute no sites."""
    try:
        model = _sc.parse(raw17)
    except _sc.SeqCodecError as ex:
        raise SeqPatchError(f"malformed raw17: {ex}")
    out = []
    for body in model.bodies:
        sub = _canonical_sub(model, body)
        for ins in body.instrs:
            for (name, rel, w, signed, kind), val in zip(ins.fields, ins.operands):
                if kind == "pad":
                    continue
                out.append(Site(sub, ins.offset + rel, w, signed, kind, val, f"sub{sub} {ins.name} {name}"))
    return out


def apply_seq_patches(raw17: bytes, patches) -> tuple:
    """Apply ``[{at, old, new, seq?}, ...]`` same-length operand patches to ``raw17``. Each ``at`` must be a real
    operand site whose current value == ``old`` (the guard) and whose field fits ``new``. Returns (patched, warns).
    Raises SeqPatchError on a bad offset / old-mismatch / range-overflow -- so a wrong patch fails the build,
    never the game."""
    if not isinstance(patches, list):
        raise SeqPatchError("[[scene.seq_patch]] must be a list of tables")
    sites = {s.offset: s for s in constant_sites(raw17)}
    b = bytearray(raw17)
    warnings: list = []
    seen: dict = {}
    for n, p in enumerate(patches):
        if not isinstance(p, dict):
            raise SeqPatchError(f"[[scene.seq_patch]] #{n} must be a table (got {type(p).__name__})")
        at, old, new = p.get("at"), p.get("old"), p.get("new")
        for k, v in (("at", at), ("old", old), ("new", new)):
            if not isinstance(v, int) or isinstance(v, bool):
                raise SeqPatchError(f"[[scene.seq_patch]] #{n} needs integer {k} (at = offset, old/new = values)")
        site = sites.get(at)
        if site is None:
            raise SeqPatchError(f"[[scene.seq_patch]] #{n}: no patchable operand at offset {at} "
                                f"(cite an offset from `battle-seq --sites`)")
        seq = p.get("seq")
        if seq is not None and seq != site.sub_no:
            warnings.append(f"[[scene.seq_patch]] #{n}: seq={seq} but offset {at} belongs to sub {site.sub_no} "
                            f"(a shared/aliased body) -- patching by offset regardless")
        if at in seen:
            warnings.append(f"[[scene.seq_patch]] #{n} and #{seen[at]} both patch offset {at} -- the later wins")
        seen[at] = n
        if site.value != old:
            raise SeqPatchError(f"[[scene.seq_patch]] #{n}: expected old = {old} at offset {at}, but the raw17 has "
                                f"{site.value} ({site.where}) -- wrong offset, or already patched?")
        if not site.vmin <= new <= site.vmax:
            raise SeqPatchError(f"[[scene.seq_patch]] #{n}: new = {new} does not fit the {site.width}-byte "
                                f"{'signed' if site.signed else 'unsigned'} {site.kind} operand at offset {at} "
                                f"({site.vmin}..{site.vmax}) -- a same-length patch can't widen it")
        b[at:at + site.width] = int(new).to_bytes(site.width, "little", signed=site.signed)
    return bytes(b), warnings


def validate_patches(raw17: bytes, patches) -> list:
    """Offline problems (empty => OK): re-run the patch on a copy and surface any SeqPatchError as a message."""
    try:
        apply_seq_patches(raw17, patches)
        return []
    except SeqPatchError as ex:
        return [str(ex)]
