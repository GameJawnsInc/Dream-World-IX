"""The provenance stamp every generated table carries on the line after its docstring (scout F47)::

    # generated-from: Memoria@<git revision> by _regen_modeldb.py

``<source>`` names what the generator READ. ``Memoria@<rev>`` is a table transcribed from the Memoria
source checkout -- the one input outside this repo, so its revision IS the table's currency (a
regeneration then shows in ``git diff`` exactly which Memoria revision moved it); ``install`` is a table
harvested from the user's FF9 install and ``examples`` one harvested from this repo's own bundled examples
(both histories live in this repo); ``Memoria@unknown by hand`` marks the three tables transcribed by
hand with no generator. No date: a date turns every regeneration into a diff even when nothing changed.
``TABLES`` is the registry ``tests/test_generated_tables.py`` walks; every generator emits its stamp
through :func:`stamp_line` / :func:`memoria_stamp`. A stamp of ``Memoria@unknown`` on a generated table
means it has not been regenerated since the stamps were introduced -- rerun its generator to record one.
"""
from __future__ import annotations

import re
import subprocess

#: generated table (package-relative) -> (the generator that writes it, what it reads)
TABLES = {
    "_animdb.py": ("_regen_animdb.py", "Memoria"),
    "_animdb_all.py": ("_regen_animdb_all.py", "Memoria"),
    "_fieldtable.py": ("_regen_fieldtable.py", "Memoria"),
    "_fieldtext.py": ("_regen_fieldtext.py", "Memoria"),
    "_modelalias.py": ("_regen_modelalias.py", "Memoria"),
    "_modeldb.py": ("_regen_modeldb.py", "Memoria"),
    "_scenedb.py": ("_regen_scenedb.py", "Memoria"),
    "eb/_optables.py": ("eb/_regen_optables.py", "Memoria"),
    "_narrowmap_data.py": ("tools/bake_narrowmap.py", "Memoria"),
    "_npcparams.py": ("_regen_npcparams.py", "install"),
    "_bonelabeldb.py": ("tools/regen_bone_labels.py", "install"),
    "_held_poses.py": ("tools/extract_attach_poses.py", "install"),
    "_fieldschema.py": ("_regen_fieldschema.py", "examples"),
    "_itemdb.py": ("hand", "Memoria"),
    "eb/_exprtable.py": ("hand", "Memoria"),
    "eb/_membertable.py": ("hand", "Memoria"),
}

STAMP_RE = re.compile(r"^# generated-from: (?P<source>\S+) by (?P<generator>\S+)$")


def stamp_line(source: str, generator: str) -> str:
    return f"# generated-from: {source} by {generator}"


def memoria_rev(memoria_path) -> str:
    """The Memoria checkout's short git revision (``git -C <path> rev-parse``, so any path inside the
    clone works), or ``unknown`` when it is not a git checkout (a source zip) or git is absent."""
    try:
        out = subprocess.run(["git", "-C", str(memoria_path), "rev-parse", "--short=12", "HEAD"],
                             capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    rev = out.stdout.strip()
    return rev if out.returncode == 0 and rev else "unknown"


def memoria_stamp(memoria_path, generator: str) -> str:
    return stamp_line(f"Memoria@{memoria_rev(memoria_path)}", generator)


def read_stamp(line: str):
    """``(source, generator)`` parsed from one line, or ``None`` when it is not a stamp."""
    m = STAMP_RE.match(line.rstrip("\n"))
    return (m.group("source"), m.group("generator")) if m else None
