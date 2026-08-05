"""Shared plumbing for the Path-D Rung-6 WORLD-SIDE scripts (splice_exit.py / arm_tiles.py).

Nothing here writes anything. It resolves the toolkit import, the two independent roots
(``--game`` = the REAL install, read-only, the p0data source for the WORLD00 trigger template;
``--target-root`` = where the mod folder that gets PATCHED lives -- the install for a real deploy,
a scratch copy for offline verification), and the shared backup-dir convention.

THE BACKUP RULE (memory ``project-ff9-worktree-parked-backups``): backups of INSTALL files go to
the MAIN repo's ``backups/``, never a worktree-relative dir -- a worktree is deleted when its
branch merges and would take the only copy of the pre-edit bytes with it.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

# --------------------------------------------------------------------------- constants

#: the real install (read-only for these scripts except for the deliberate deploy writes)
DEFAULT_GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
#: the toolkit's distribution root -- the local package must shadow any editable install
KIT_ROOT = Path(r"C:\gd\Dream-World-IX\.claude\worktrees\path-d-rung-6-handoff-e2535a\ff9mapkit")
#: MAIN repo backups dir (NOT the worktree -- see the module docstring)
DEFAULT_BACKUP_PARENT = Path(r"C:\gd\Dream-World-IX\backups")

#: the stacked mod folder that owns the custom overworld (Memoria.ini FolderNames)
MOD_FOLDER = "FF9CustomMap-world"
#: the world dispatcher this rung patches -- world state 9013 (engine patch s73 band 9013-9099)
WORLD_EB_NAME = "EVT_WORLD_WORLD13.eb.bytes"
#: Path D resolves its per-cell WorldMap overrides against the SENTINEL disc (engine patch s74)
SENTINEL_DISC = 9

# ---- the SITE SPEC (site-selection agent, studies/path-d-new-world/rung6/site.json) ----
DEST_FIELD = 30950            # the field-side half's destination id
WORLD_STATE = 9013            # recorded into GLOB[1062] so the field's return gateway knows the world
TRIGGER_CELL = (13, 17)       # cell (cx, cz) -> block (6, 8), tag 0x9135
TRIGGER_EVENT = 1             # event bits 1..3; 1 is the only event id in use on Path D terrain
#: the retarget disc is NOT at the cell's geometric centre. The site survey measured the centre
#: (432, -560) as 1u from the shore -- its all-clean radius is 0u. (424, -553) is the centroid of
#: the cell's clean-grass lobe; max all-clean radius there is 8.0u (which exactly touches the cell
#: edges at x=416 / z=-545), and 6.0u keeps a 2u margin inside them.
TRIGGER_CENTER = (424.0, -553.0)
TRIGGER_RADIUS = 6.0


# --------------------------------------------------------------------------- imports / paths

def import_kit():
    """Put the worktree's ``ff9mapkit/`` on ``sys.path`` FRONT so the local package shadows any
    editable/site-packages install (repo rule: run the CLI from ``ff9mapkit/``)."""
    p = str(KIT_ROOT)
    if p not in sys.path:
        sys.path.insert(0, p)
    return p


def world_eb_path(target_root: Path, lang: str, *, mod_folder: str = MOD_FOLDER,
                  name: str = WORLD_EB_NAME) -> Path:
    """``<target_root>/<mod_folder>/StreamingAssets/.../world/<lang>/EVT_WORLD_WORLD13.eb.bytes``.

    The subdir constant comes from ``entrance._WORLD_EB_SUBDIR`` so this can never drift from the
    path the kit's own author_entrance writes."""
    from ff9mapkit.world.entrance import _WORLD_EB_SUBDIR
    return Path(target_root) / mod_folder / _WORLD_EB_SUBDIR / lang / name


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def file_sha(p: Path) -> str | None:
    p = Path(p)
    return sha(p.read_bytes()) if p.is_file() else None


def timestamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def resolve_backup_dir(arg, *, label: str) -> Path:
    """``--backup-dir`` or a fresh timestamped dir under the MAIN repo's ``backups/``.

    Never created here -- the caller creates it only when it is actually about to back something up
    (a ``--dry-run`` must leave no trace)."""
    if arg:
        return Path(arg)
    return DEFAULT_BACKUP_PARENT / f"rung6-worldside-{timestamp()}-{label}"


def backup_file(src: Path, backup_dir: Path, relname: str, *, dry_run: bool) -> dict:
    """Copy ``src`` into ``backup_dir/relname`` (parents made) and return a manifest row.

    Refuses to overwrite an existing backup file -- a backup that silently replaces an older backup
    of DIFFERENT bytes is worse than no backup at all."""
    src = Path(src)
    row = {"source": str(src), "sha256": file_sha(src), "bytes": src.stat().st_size,
           "backup": str(Path(backup_dir) / relname)}
    if dry_run:
        row["written"] = False
        return row
    dest = Path(backup_dir) / relname
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        raise SystemExit(f"refusing to overwrite an existing backup: {dest}\n"
                         f"    pass a fresh --backup-dir (default is timestamped)")
    dest.write_bytes(src.read_bytes())
    row["written"] = True
    return row


def write_report(path, payload: dict) -> None:
    if not path:
        return
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, indent=1, default=str), encoding="utf-8")


class Log:
    """Print + capture, so every run can drop a transcript next to its JSON report."""

    def __init__(self):
        self.lines: list[str] = []

    def __call__(self, *a):
        s = " ".join(str(x) for x in a)
        self.lines.append(s)
        print(s, flush=True)

    def rule(self, title: str = ""):
        self("=" * 78)
        if title:
            self(title)

    def save(self, path) -> None:
        if path:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text("\n".join(self.lines) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- .eb structural walk

def parse_body(body: bytes):
    """``(status, n_instr, err)`` for one function body.

    ``status`` is ``"clean"`` (decodes end-to-end), ``"empty"`` (zero-length -- a legitimate stock
    shape: 16 of WORLD13's 96 funcs have ``fpos == the next func's fpos``, so their body is 0 bytes;
    counting those as failures would make a green baseline impossible), or ``"ragged"`` (a real
    decode failure -- the thing a bad splice produces)."""
    from ff9mapkit.eb import disasm as D
    if not body:
        return "empty", 0, None
    try:
        ins = list(D.iter_code(body, 0, len(body)))
    except Exception as e:                                  # noqa: BLE001 -- any decoder blow-up
        return "ragged", 0, f"{type(e).__name__}: {e}"
    if not ins:
        return "ragged", 0, "no instructions decoded from a non-empty body"
    end = ins[-1].off + ins[-1].length
    if end != len(body):
        return "ragged", len(ins), f"ragged: last instr ends at {end}, body is {len(body)}"
    return "clean", len(ins), None


def structural_walk(data: bytes) -> dict:
    """Decode EVERY function of EVERY non-empty entry. Returns
    ``{"entries", "funcs", "clean", "empty", "ragged": [(entry, func_idx, tag, err), ...]}``."""
    from ff9mapkit.eb.model import EbScript
    eb = EbScript(data)
    out = {"entries": eb.entry_count, "funcs": 0, "clean": 0, "empty": 0, "ragged": []}
    for e in eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            out["funcs"] += 1
            st, _n, err = parse_body(data[f.abs_start:f.abs_end])
            if st == "ragged":
                out["ragged"].append((e.index, f.index, f.tag, err))
            else:
                out[st] += 1
    return out


def func_map(data: bytes) -> dict:
    """``{(entry_index, func_index): (tag, body_bytes)}`` -- the whole file's function inventory.

    Keyed POSITIONALLY, because a tag is not unique inside an entry, and because both
    ``add_function`` (appends at the end of the entry's func table) and ``replace_function_body``
    preserve every existing function's index. Comparing this map before/after a splice proves that
    exactly one function changed and no other byte of code moved semantically."""
    from ff9mapkit.eb.model import EbScript
    eb = EbScript(data)
    return {(e.index, f.index): (f.tag, data[f.abs_start:f.abs_end])
            for e in eb.entries if not e.empty for f in e.funcs}


def eb_headroom(data: bytes) -> dict:
    """The two u16 ceilings ``add_function`` does NOT itself check: the biggest entry-table offset
    and the whole-file budget (both ``0xFFFF``). A splice that overruns either produces a file the
    engine mis-indexes -- the null-.eb black screen."""
    from ff9mapkit.binutils import EB_FILE_BUDGET, eb_budget_used
    from ff9mapkit.eb.model import EbScript
    eb = EbScript(data)
    max_off = max((e.off for e in eb.entries if not e.empty), default=0)
    used = eb_budget_used(data)
    return {"max_entry_off": max_off, "off_headroom": EB_FILE_BUDGET - max_off,
            "budget_used": used, "budget_headroom": EB_FILE_BUDGET - used,
            "ok": max_off <= EB_FILE_BUDGET and used <= EB_FILE_BUDGET}


def disasm_text(body: bytes, title: str) -> str:
    """A hex + per-instruction listing of one function body (the format the rung-6 spike used)."""
    from ff9mapkit.eb import disasm as D
    lines = [f"; {title}  ({len(body)} bytes)", "; " + body.hex()]
    try:
        for i in D.iter_code(body, 0, len(body)):
            try:
                args = " ".join(str(a) for a in (i.args or []))
            except Exception:                               # noqa: BLE001
                args = "<args?>"
            lines.append(f"{i.off:5d}: {D.op_name(i.op):<22} len={i.length:<3} {args}")
    except Exception as e:                                  # noqa: BLE001
        lines.append(f"!! decode error: {type(e).__name__}: {e}")
    return "\n".join(lines)
