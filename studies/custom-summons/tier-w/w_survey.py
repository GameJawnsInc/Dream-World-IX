r"""TIER W rung 5 -- THE SURVEY: a per-effect capability matrix over the whole summon corpus.

    py w_survey.py --summons              # the 17-summon table (agent4.md sec 2), FULL + SHORT
    py w_survey.py --corpus               # the full 372-container sweep, summarised
    py w_survey.py --ef 211               # one effect's row, verbose
    py w_survey.py --self-check           # the falsifiable claims below, checked against the bytes

WHAT THIS IS
------------
B1 (``reskin.py``), B2 (``rescore.py`` / ``summon_camera.py``) and B3 (``retime.py`` /
``retime_derive.py``) each generalised ONE lever off ef227.  This module answers the question a
caster needs before reaching for any of them on a NEW effect: **which levers does this container
actually carry, and which of W5's five hard hazards does it trip?**  Nothing here is re-derived --
every fact is read straight through the lane's own detector:

* **texanim** -- ``reskin.texanim_region`` / ``reskin.palette_map(...).texanim``;
* **the creature package, and whether it is ever DRAWN** -- ``ff9mapkit.summons.container
  .creature_package`` for presence, and a corpus-wide op census over every id-3 image
  (``tier_r_disasm.id3_images`` / ``walk_image``) for **HLE op 25 (Hi_DrawSummonModel) >= 1**.  This
  is the ef447 lesson (agent4.md sec 4 item 1): Ark Short ships a full 6-part creature package and
  calls op 25 **zero** times across all three of its chunks -- it draws Ark entirely through op 24
  (``Hi_DrawEffModel``).  Creature-package-present is NOT sufficient; a scaffold or a caster must
  check the model is actually reachable from the program;
* **program class** -- ``summon_inspect.corpus_census``'s own recovery verdict (clean-switch /
  trivial / defeated), per id-3 image;
* **camera shots / alternates / dynamic ops** -- ``summon_camera.extract_shots`` +
  ``rescore.alternates_signature`` / ``rescore.dynamic_ops``;
* **CLUT hazards** -- ``reskin.palette_map(...).hazards`` (multi-writer / dual-depth cells);
* **twin-texture groups** -- RE-DERIVED here (not hardcoded) by hashing each creature's own texture
  pages + CLUT strip and grouping containers whose bytes come back byte-identical.  agent4.md sec 4
  item 2 measured three such groups; :func:`twin_groups` reproduces them from the corpus itself so a
  reskin of one twin can warn about the other (ef211/ef225, ef210/ef226, and the six 1-part
  specials' shared placeholder);
* **DLL frame gates** -- CITED, never re-derived (that would need x64 DLL disassembly, a tool this
  lane does not carry): ``SFX.cs:607-613`` (Ark FULL flips ``SFX.subOrder`` at frameIndex == 1004 and
  == 1193) and ``SFX.cs:1378-1379`` (Atomos FULL/SHORT gate on frameIndex > 350 / > 150).  A W3
  retime of either effect desyncs an engine constant no container byte reaches;
* **short-id creature absence** -- the 12 SHORT vfx ids carry no id-4 package at all; ef447 (Ark
  Short) is the one exception, and it is exactly the op-25-absent creature above.

THE FULL/SHORT ID MAP is a derived fact from engine source (``btl_cmd.cs:1583-1615``,
``SpecialEffect.cs:86-118``) plus ``Actions.csv``, cross-checked three ways in agent4.md sec 1; it is
re-cited here as :data:`SUMMON_TABLE`, not re-read (that read is agent4's own census).

THE EF038 TEXANIM SIDE-RECON (:func:`ef038_texanim_side_recon`) is the one cheap experiment
agent3.md sec 2.3 names as capable of discriminating "texanim = a VRAM re-upload" from "texanim = a
binding/UV mutation in PSX RAM": does ef038's own id-3 program touch a VRAM-transfer HLE op (0
LoadImage / 1 StoreImage / 166 MoveImage)?  It is REPORT-ONLY -- it does not, and cannot, lift D3's
texanim gate (only reading the table's own internal format would).  The *other* half of that
experiment, the DLL's "loader-script opcode 0x07" (A1-TEXTURES.md:269-270), lives in the DLL's
resource-loader dispatch (``fn 0x318a2``) -- a different opcode space than the 216 HLE ops this
lane's tools decode (``hle_ops.json`` op 7 is ``native_fn 0x2f70``, an unrelated function) -- so it
is CITED as an engine fact below, not measured.

PROVENANCE
----------
Every number here is a count, an offset, a verdict string or a SHA-256 digest -- never a stock byte
run.  Containers are read from the extracted corpus (``summon_camera.SCRATCH_CORPUS``) or the user's
own install at run time; nothing stock is committed.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
_STUDY = os.path.dirname(_HERE)
for _p in (_HERE, os.path.join(_STUDY, "tier-r"), os.path.join(_STUDY, "thomas-swap", "disasm")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import reskin as RS                                             # noqa: E402  (sets up sys.path)
import rescore as R                                              # noqa: E402
import summon_camera as W                                        # noqa: E402
import ef_container as EC                                        # noqa: E402
import tier_r_disasm as T                                        # noqa: E402
import summon_inspect as S                                       # noqa: E402
from ff9mapkit.summons import container as KC                    # noqa: E402
from ff9mapkit.summons import texture as KT                      # noqa: E402


class SurveyError(RuntimeError):
    pass


# ============================================================ (0) the citable facts
#: the 17 stock summons' FULL/SHORT vfx pair.  DERIVED from engine source + Actions.csv
#: (btl_cmd.cs:1583-1615 `DecideSummonType`, SpecialEffect.cs:86-118, Actions.csv's own rows),
#: cross-checked three independent ways in agent4.md sec 1 -- re-cited here, not re-read.
SUMMON_TABLE: Tuple[Tuple[str, int, int], ...] = (
    ("Shiva", 38, 407),
    ("Ifrit", 276, 445),
    ("Ramuh", 186, 415),
    ("Atomos", 184, 446),
    ("Odin", 261, 424),
    ("Leviathan", 179, 406),
    ("Bahamut", 227, 405),
    ("Ark", 381, 447),
    ("Fenrir (Earth)", 210, 508),
    ("Fenrir (Wind)", 226, 509),
    ("Carbuncle (Reflect/Ruby)", 177, 504),
    ("Carbuncle (Haste/Emerald)", 494, 506),
    ("Carbuncle (Shell/Pearl)", 493, 505),
    ("Carbuncle (Vanish/Diamond)", 495, 507),
    ("Phoenix", 211, 510),
    ("Rebirth Flame", 225, 225),
    ("Madeen", 251, 378),
)

#: the corpus class whose id-4 texanim region is non-empty (D3's gate) -- reskin.py's own docstring
#: measurement, restated here as the value :func:`self_check` falsifies against.
TEXANIM_CLASS: Tuple[int, ...] = (38, 177, 493, 494, 495)

#: DLL-hardcoded per-effect ABSOLUTE FRAME gates -- a fifth clock this rung's audit never met on
#: ef227.  CITED from the user's own local Memoria clone (never reproduced as an executable
#: dependency, and never re-derived here -- that would need x64 DLL disassembly, which is a
#: different instrument than anything in this lane): `SFX.cs:607-613` (Ark FULL flips
#: `SFX.subOrder` at frameIndex == 1004 and == 1193) and `SFX.cs:1378-1379` (Atomos FULL gates on
#: frameIndex > 350, Atomos SHORT on > 150).  A W3 retime of either effect desyncs an engine
#: constant the container cannot reach -- agent4.md sec 4 item 5.
DLL_FRAME_GATES: Dict[int, str] = {
    381: "Ark FULL -- SFX.cs:607-613: SFX.subOrder flips at frameIndex == 1004 and == 1193",
    184: "Atomos FULL -- SFX.cs:1378-1379: gated on frameIndex > 350",
    446: "Atomos SHORT -- SFX.cs:1378-1379: gated on frameIndex > 150",
}

#: HLE op 25 == Hi_DrawSummonModel (tier-r's own `A1-op-census.txt` names it so on ef227's two
#: programs).  Presence of an id-4 creature package is NOT sufficient for the model to be drawn --
#: ef447 is the corpus's one counter-example -- so a caster-facing gate must check this too.
OP_DRAW_SUMMON_MODEL = 25

#: HLE ops that can reach a VRAM-transfer command (A1-TEXTURES.md:266-267): 0 LoadImage,
#: 1 StoreImage, 166 MoveImage.  Used only by :func:`ef038_texanim_side_recon`.
VRAM_TRANSFER_OPS: Dict[int, str] = {0: "LoadImage", 1: "StoreImage", 166: "MoveImage"}


# ============================================================ (1) per-container detectors
@dataclass(frozen=True)
class OpCensus:
    """Every HLE op call every id-3 image in a container makes -- op 25 is the ef447 lesson."""
    total_calls: int
    op25: int
    distinct_ops: Tuple[int, ...]
    per_image: Tuple[Tuple[str, int], ...]     # (image label, op25 count) -- which chunk draws it


def op_census(blob: bytes, source: str) -> OpCensus:
    calls: List[int] = []
    per_image: List[Tuple[str, int]] = []
    for img in T.id3_images(blob, source):
        wr = T.walk_image(img)
        ops = [c.hle_op for c in wr.calls if c.kind == "hle" and c.hle_op is not None]
        calls.extend(ops)
        per_image.append((img.label, sum(1 for o in ops if o == OP_DRAW_SUMMON_MODEL)))
    return OpCensus(total_calls=len(calls),
                    op25=sum(1 for o in calls if o == OP_DRAW_SUMMON_MODEL),
                    distinct_ops=tuple(sorted(set(calls))), per_image=tuple(per_image))


@dataclass(frozen=True)
class ClutSurvey:
    """W4/W5's own hazard census, read straight off ``reskin.palette_map`` -- nothing re-derived."""
    creature_present: bool
    creature_error: str
    texanim_present: bool
    texanim_armed: bool
    texanim_bytes: int
    multi_writer_cells: Tuple[Tuple[int, int], ...]
    dual_depth_cells: Tuple[Tuple[int, int], ...]
    n_palettes: int
    envelope: int


def clut_survey(blob: bytes, effect: Optional[int] = None) -> ClutSurvey:
    pmap = RS.palette_map(blob, effect=effect)
    haz = pmap.hazards
    ta = pmap.texanim
    return ClutSurvey(
        creature_present=not pmap.creature_error, creature_error=pmap.creature_error,
        texanim_present=bool(ta and ta.present), texanim_armed=bool(ta and ta.armed),
        texanim_bytes=ta.nbytes if ta else 0,
        multi_writer_cells=tuple(sorted(k for k, c in haz.items() if c.multi_writer)),
        dual_depth_cells=tuple(sorted(k for k, c in haz.items() if c.dual_depth)),
        n_palettes=len(pmap.palettes), envelope=pmap.envelope)


@dataclass(frozen=True)
class CameraSurvey:
    """W1/W2's own extraction, read straight off ``summon_camera.extract_shots``."""
    shots: int
    max_sequences: int
    dynamic_ops: int
    alternates_differ_shots: Tuple[str, ...]     # "slot{S}.idx{I}" labels where tracks GENUINELY differ


def camera_survey(blob: bytes, source: str) -> CameraSurvey:
    ex = W.extract_shots(blob, source)
    differ: List[str] = []
    max_seq = 0
    for sh in ex.shots:
        seqs = sh.camera.get("sequences") or []
        max_seq = max(max_seq, len(seqs))
        verdict = R.check_alternates(R.alternates_signature(sh), [])
        if verdict.alternates_differ:
            differ.append("slot%d.idx%d" % sh.key)
    return CameraSurvey(shots=len(ex.shots), max_sequences=max_seq, dynamic_ops=ex.dynamic,
                        alternates_differ_shots=tuple(differ))


def creature_signature(blob: bytes) -> Optional[str]:
    """SHA-256 over one creature's texture pages + CLUT strip -- the twin-texture fingerprint.

    Two containers whose creature reads back byte-identical here share art (agent4.md sec 4 item 2:
    `{210,226}`, `{211,225}`, and the six 1-part specials' shared placeholder).  Re-derived per
    corpus sweep by :func:`twin_groups`, never hardcoded.
    """
    mp = KC.creature_package(blob)
    if mp is None:
        return None
    chk = KT.texture_check(blob, mp)
    if not chk["decodable"]:
        return None
    lo = mp.tex_file_offset
    hi = mp.tex_file_offset + mp.tex_bytes + mp.clut_bytes
    return hashlib.sha256(blob[lo:hi]).hexdigest()


def twin_groups(root: Optional[str] = None) -> Dict[str, List[int]]:
    """``{signature: [effect ids]}`` for every creature signature shared by MORE than one effect."""
    root = root or W.SCRATCH_CORPUS
    by_sig: Dict[str, List[int]] = {}
    for path in W.corpus_paths(root):
        name = os.path.splitext(os.path.basename(path))[0]
        try:
            ef = int(name[2:])
        except ValueError:                                       # pragma: no cover - non-"efNNN" name
            continue
        with open(path, "rb") as fh:
            blob = fh.read()
        sig = creature_signature(blob)
        if sig is not None:
            by_sig.setdefault(sig, []).append(ef)
    return {sig: sorted(ids) for sig, ids in by_sig.items() if len(ids) > 1}


_PROGRAM_CENSUS_CACHE: Dict[str, Dict[str, "S.CensusRow"]] = {}


def program_class_rows(root: Optional[str] = None) -> Dict[str, "S.CensusRow"]:
    """``{image label: CensusRow}`` -- ``summon_inspect.corpus_census``'s own recovery, memoised."""
    root = root or W.SCRATCH_CORPUS
    if root not in _PROGRAM_CENSUS_CACHE:
        rows = S.corpus_census(root=root)
        _PROGRAM_CENSUS_CACHE[root] = {r.image: r for r in rows}
    return _PROGRAM_CENSUS_CACHE[root]


# ============================================================ (2) the per-effect row
@dataclass
class EffectRow:
    effect: int
    source: str
    has_creature: bool
    creature_error: str
    op25: int
    drawn: bool                                  # has_creature AND op25 >= 1 -- the ef447 lesson
    texanim_bytes: int
    texanim_armed: bool
    multi_writer_cells: Tuple[Tuple[int, int], ...]
    dual_depth_cells: Tuple[Tuple[int, int], ...]
    program_classes: Tuple[Tuple[str, str, int, int], ...]   # (image, verdict, phases, ticks)
    shots: int
    max_sequences: int
    dynamic_ops: int
    alternates_differ_shots: Tuple[str, ...]
    twin_partners: Tuple[int, ...]
    dll_gate: str

    @property
    def hazard(self) -> bool:
        return bool(self.multi_writer_cells or self.dual_depth_cells)


def load_effect(effect: int, root: Optional[str] = None, game=None) -> Tuple[bytes, str]:
    """Corpus first (this lane's read-only, provenance-gated fixture set), install as a fallback."""
    root = root or W.SCRATCH_CORPUS
    path = os.path.join(root, "ef%03d.bytes" % effect)
    if os.path.isfile(path):
        with open(path, "rb") as fh:
            return fh.read(), path
    return R.read_stock_effect(effect, game)


def survey_effect(blob: bytes, effect: int, source: str,
                  twins: Optional[Dict[str, List[int]]] = None,
                  prog_rows: Optional[Dict[str, "S.CensusRow"]] = None) -> EffectRow:
    """Every capability fact for ONE container, all of it read through the lanes' own detectors."""
    oc = op_census(blob, source)
    cs = clut_survey(blob, effect=effect)
    cam = camera_survey(blob, source)
    sig = creature_signature(blob)
    twin_ids: List[int] = []
    if twins is not None and sig is not None and sig in twins:
        twin_ids = [e for e in twins[sig] if e != effect]
    prog_rows = prog_rows or {}
    classes = tuple((lbl, prog_rows[lbl].verdict, prog_rows[lbl].phases, prog_rows[lbl].ticks or 0)
                    for lbl in sorted(prog_rows) if lbl.startswith(source + ":"))
    return EffectRow(
        effect=effect, source=source,
        has_creature=cs.creature_present, creature_error=cs.creature_error,
        op25=oc.op25, drawn=cs.creature_present and oc.op25 >= 1,
        texanim_bytes=cs.texanim_bytes, texanim_armed=cs.texanim_armed,
        multi_writer_cells=cs.multi_writer_cells, dual_depth_cells=cs.dual_depth_cells,
        program_classes=classes, shots=cam.shots, max_sequences=cam.max_sequences,
        dynamic_ops=cam.dynamic_ops, alternates_differ_shots=cam.alternates_differ_shots,
        twin_partners=tuple(sorted(twin_ids)), dll_gate=DLL_FRAME_GATES.get(effect, ""))


# ============================================================ (3) the corpus sweep
@dataclass
class SweepResult:
    rows: List[EffectRow]
    crashes: List[str]


def corpus_sweep(root: Optional[str] = None) -> SweepResult:
    root = root or W.SCRATCH_CORPUS
    twins = twin_groups(root)
    prog = program_class_rows(root)
    rows: List[EffectRow] = []
    crashes: List[str] = []
    for path in W.corpus_paths(root):
        name = os.path.splitext(os.path.basename(path))[0]
        try:
            ef = int(name[2:])
        except ValueError:                                       # pragma: no cover
            continue
        with open(path, "rb") as fh:
            blob = fh.read()
        try:
            rows.append(survey_effect(blob, ef, name, twins=twins, prog_rows=prog))
        except Exception as exc:                                 # the sweep must never stop on one
            crashes.append("%s: %s: %s" % (name, type(exc).__name__, exc))
    return SweepResult(rows=rows, crashes=crashes)


# ============================================================ (4) the ef038 side-recon
def ef038_texanim_side_recon(root: Optional[str] = None) -> List[str]:
    """agent3.md sec 2.3's one cheap experiment: does ef038 ALSO reach a VRAM-transfer op?

    REPORT-ONLY -- this does not, and cannot, lift D3's texanim gate (only reading the 116-byte
    table's own internal format would).  The "loader-script opcode 0x07" A1-TEXTURES.md:269-270
    measured corpus-wide (9 of 372 containers) is a DIFFERENT dispatch than the 216 HLE ops these
    tools decode (`hle_ops.json` op 7 is `native_fn 0x2f70`, an unrelated function to the loader's
    own `0x64000000` issuer at `0x3193e`) -- it needs x64 DLL disassembly this lane's tools do not
    carry, so it is CITED here as an engine fact, never measured.
    """
    root = root or W.SCRATCH_CORPUS
    path = os.path.join(root, "ef038.bytes")
    lines = ["ef038 TEXANIM SIDE-RECON (report-only; does NOT lift the D3 texanim gate)"]
    if not os.path.isfile(path):
        lines.append("  ef038.bytes not found under %s -- skipped" % root)
        return lines
    with open(path, "rb") as fh:
        blob = fh.read()
    for img in T.id3_images(blob, "ef038"):
        wr = T.walk_image(img)
        ops = [c.hle_op for c in wr.calls if c.kind == "hle" and c.hle_op is not None]
        hits = {op: ops.count(op) for op in VRAM_TRANSFER_OPS if op in ops}
        lines.append("  %s: %d HLE call site(s), VRAM-transfer op(s): %s"
                     % (img.label, len(ops),
                        ", ".join("op %d %s x%d" % (op, VRAM_TRANSFER_OPS[op], n)
                                  for op, n in sorted(hits.items())) or "NONE"))
    lines.append("  => ef038 reaches NO op-0/1/166 VRAM-transfer call in either program: the texanim "
                "table's arming (op 12) is NOT accompanied by a re-upload through the ops this "
                "lane's tools can see -- consistent with, but not proof of, a binding/UV mutation "
                "in PSX RAM rather than a VRAM re-upload.")
    lines.append("  loader-script opcode 0x07 (DLL fn 0x318a2, corpus-wide 9/372 containers, "
                "A1-TEXTURES.md:269-270): CITED as an engine fact, NOT independently re-derived "
                "here -- see this function's docstring for why.")
    return lines


# ============================================================ (5) formatting
def describe_row(row: EffectRow) -> List[str]:
    L = ["ef%03d" % row.effect]
    L.append("  creature       : %s%s"
            % ("present" if row.has_creature else "ABSENT", (" -- %s" % row.creature_error)
               if row.creature_error else ""))
    if row.has_creature:
        L.append("  op25 (draw)    : %d call(s) -- %s"
                % (row.op25, "DRAWN" if row.drawn else "*** NEVER DRAWN (creature package present, "
                                                       "op 25 never called) ***"))
    L.append("  texanim        : %s"
            % ("ARMED %d B" % row.texanim_bytes if row.texanim_armed else "empty/absent"))
    L.append("  CLUT hazards   : %s"
            % ("; ".join(filter(None, [
                  "multi-writer %s" % (row.multi_writer_cells,) if row.multi_writer_cells else "",
                  "dual-depth %s" % (row.dual_depth_cells,) if row.dual_depth_cells else ""]))
               or "none"))
    L.append("  program class  : %s"
            % ("; ".join("%s=%s(%dph/%dt)" % (img, v, ph, tk) for img, v, ph, tk in row.program_classes)
               or "(no id-3 image recovered)"))
    L.append("  camera         : %d shot(s), max %d sequence(s), %d dynamic op(s)%s"
            % (row.shots, row.max_sequences, row.dynamic_ops,
               "; ALTERNATES GENUINELY DIFFER on %s" % (row.alternates_differ_shots,)
               if row.alternates_differ_shots else ""))
    L.append("  twin texture   : %s" % ("shares art with %s" % (row.twin_partners,)
                                        if row.twin_partners else "none"))
    if row.dll_gate:
        L.append("  DLL FRAME GATE : %s" % row.dll_gate)
    return L


def describe_summons(root: Optional[str] = None) -> List[str]:
    root = root or W.SCRATCH_CORPUS
    twins = twin_groups(root)
    prog = program_class_rows(root)
    L = ["=" * 100, "THE 17-SUMMON CAPABILITY MATRIX (agent4.md sec 2)", "=" * 100]
    for name, full, short in SUMMON_TABLE:
        L.append("")
        L.append("-- %s -- FULL vfx %d, SHORT vfx %d" % (name, full, short))
        for tag, ef in (("FULL ", full), ("SHORT", short)):
            try:
                blob, src = load_effect(ef, root)
                row = survey_effect(blob, ef, "ef%03d" % ef, twins=twins, prog_rows=prog)
                L.append("  [%s] ef%03d" % (tag, ef))
                for ln in describe_row(row)[1:]:            # [0] is the "ef###" header, redundant here
                    L.append("      " + ln)
            except Exception as exc:                             # pragma: no cover - defensive
                L.append("  [%s] ef%03d ERROR: %s: %s" % (tag, ef, type(exc).__name__, exc))
    L.append("")
    L += ef038_texanim_side_recon(root)
    return L


def describe_corpus(root: Optional[str] = None) -> List[str]:
    root = root or W.SCRATCH_CORPUS
    sw = corpus_sweep(root)
    n = len(sw.rows)
    creature = [r for r in sw.rows if r.has_creature]
    never_drawn = [r.effect for r in creature if not r.drawn]
    texanim = [r.effect for r in sw.rows if r.texanim_armed]
    multi = [r.effect for r in sw.rows if r.multi_writer_cells]
    dual = [r.effect for r in sw.rows if r.dual_depth_cells]
    dynamic = [r.effect for r in sw.rows if r.dynamic_ops]
    twins = twin_groups(root)
    L = ["=" * 100, "THE CORPUS SWEEP (%d containers, %d CRASHED)" % (n, len(sw.crashes)),
        "=" * 100]
    for c in sw.crashes:
        L.append("  CRASH %s" % c)
    L.append("creature-bearing containers : %d" % len(creature))
    L.append("  ... of which NEVER DRAWN (op25 == 0): %s" % (sorted(never_drawn),))
    L.append("TEXANIM armed                : %s" % (sorted(texanim),))
    L.append("MULTI-WRITER CLUT containers : %s" % (sorted(multi),))
    L.append("DUAL-DEPTH CLUT containers   : %s" % (sorted(dual),))
    L.append("runtime-chosen camera op(s)  : %d of %d containers carry at least one" % (
        len(dynamic), n))
    L.append("TWIN TEXTURE GROUPS          : %s"
            % (sorted(tuple(sorted(v)) for v in twins.values()),))
    return L


# ============================================================ (6) the survey self-check
@dataclass
class SelfCheck:
    ok: bool
    lines: Tuple[str, ...]


def self_check(root: Optional[str] = None) -> SelfCheck:
    """The survey's OWN falsifiable claim: every re-derived fact above still matches what
    agent4.md's recon measured by hand, checked directly against the corpus's bytes."""
    root = root or W.SCRATCH_CORPUS
    if not W.corpus_paths(root):
        return SelfCheck(False, ("no extracted corpus at %s" % root,))
    sw = corpus_sweep(root)
    lines: List[str] = []
    ok = True

    lines.append("corpus sweep: %d containers, %d CRASHED"
                % (len(sw.rows) + len(sw.crashes), len(sw.crashes)))
    for c in sw.crashes:
        lines.append("  CRASH %s" % c)
    ok = ok and not sw.crashes

    texanim = sorted(r.effect for r in sw.rows if r.texanim_armed)
    lines.append("TEXANIM armed: %s" % (texanim,))
    ok = ok and texanim == sorted(TEXANIM_CLASS)

    multi = sorted(r.effect for r in sw.rows if r.multi_writer_cells)
    lines.append("MULTI-WRITER containers: %s" % (multi,))
    # w4_gates.py X7 already established this set: ef381 (19 cells, up to 5 writers) AND ef447 --
    # ef447's one dual-depth cell ALSO satisfies `multi_writer` (its two depths sit at two different
    # file offsets by construction), so it is a member of BOTH censuses, not an error in either.
    ok = ok and multi == [381, 447]

    dual = sorted(r.effect for r in sw.rows if r.dual_depth_cells)
    lines.append("DUAL-DEPTH containers: %s" % (dual,))
    ok = ok and dual == [447]

    creature = [r for r in sw.rows if r.has_creature]
    lines.append("creature-bearing containers: %d (agent4.md sec 2.3: 24 creature packages)"
                % len(creature))
    ok = ok and len(creature) == 24

    drawn = sorted(r.effect for r in creature if r.drawn)
    never_drawn = sorted(r.effect for r in creature if not r.drawn)
    want_drawn = sorted(full for _n, full, _s in SUMMON_TABLE)
    lines.append("op-25 PRESENT (drawn): %d effect(s), matches the 17 summon FULL ids: %s"
                % (len(drawn), drawn == want_drawn))
    ok = ok and drawn == want_drawn
    lines.append("op-25 ABSENT despite a creature package (the ef447 lesson): %s" % (never_drawn,))
    ok = ok and never_drawn == sorted([431, 432, 435, 438, 439, 447, 498])

    twins = twin_groups(root)
    groups = sorted(tuple(sorted(v)) for v in twins.values())
    lines.append("TWIN TEXTURE GROUPS (re-derived from bytes): %s" % (groups,))
    ok = ok and (210, 226) in groups and (211, 225) in groups
    six = next((g for g in groups if len(g) == 6), None)
    lines.append("the six 1-part specials share one placeholder: %s" % (six,))
    ok = ok and six == (431, 432, 435, 438, 439, 498)

    return SelfCheck(ok, tuple(lines))


# ============================================================ CLI
def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--summons", action="store_true", help="the 17-summon capability table")
    ap.add_argument("--corpus", action="store_true", help="the full corpus sweep, summarised")
    ap.add_argument("--ef", type=int, default=None, help="one effect's row, verbose")
    ap.add_argument("--self-check", action="store_true", help="the survey's own falsifiable claims")
    ap.add_argument("--texanim-recon", action="store_true", help="the ef038 side-recon alone")
    ap.add_argument("--root", default=None, help="corpus root (default: summon_camera.SCRATCH_CORPUS)")
    a = ap.parse_args(argv)
    root = a.root or W.SCRATCH_CORPUS

    if a.self_check:
        sc = self_check(root)
        print("\n".join(sc.lines))
        print("\nSURVEY SELF-CHECK: %s" % ("OK" if sc.ok else "FAILED"))
        return 0 if sc.ok else 1
    if a.texanim_recon:
        print("\n".join(ef038_texanim_side_recon(root)))
        return 0
    if a.summons:
        print("\n".join(describe_summons(root)))
        return 0
    if a.corpus:
        print("\n".join(describe_corpus(root)))
        return 0
    if a.ef is not None:
        blob, src = load_effect(a.ef, root)
        row = survey_effect(blob, a.ef, "ef%03d" % a.ef, twins=twin_groups(root),
                            prog_rows=program_class_rows(root))
        print("source: %s" % src)
        print("\n".join(describe_row(row)))
        return 0
    ap.print_help()
    return 1


if __name__ == "__main__":                                       # pragma: no cover
    raise SystemExit(main())
