"""The editor's data model: load / edit / serialize a ``field.toml`` (bpy/tk-FREE, fully testable).

The kit reads TOML with the stdlib ``tomllib`` (read-only). For writing we ship a small, schema-aware
serializer (:func:`dumps`) so the editor regenerates a clean ``field.toml`` with **zero new
dependencies** -- no ``tomli_w``/``tomlkit``. The contract that makes it safe is round-trip equality:

    tomllib.loads(dumps(d)) == d          # for every value type the field.toml schema uses

(see ``tests/test_editor_model.py``: proven on a representative doc AND every bundled example).

:class:`FieldDoc` wraps a loaded field.toml. It edits + saves the **logic** file only; a sibling
``<stem>.scene.toml`` (Blender-owned, spatial) is loaded read-only for the merged display view and is
never written, so the editor can't clobber a Blender scene. The merged view reuses the kit's own
``build._merge_scene`` so what the editor shows is exactly what ``ff9mapkit build`` will compile.

NOTE: regenerating the file drops hand-written comments (the intended audience edits via the UI, not
the text). The data always round-trips.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

# Dict values emitted INLINE as ``key = {..}`` (small value-tables, not their own [section]).
_INLINE_TABLE_KEYS = frozenset({"anims", "scene", "scroll", "frame"})
# List-of-table values emitted as a multiline inline-table array ``key = [ {..}, {..} ]``.
_INLINE_AOT_KEYS = frozenset({"steps"})

# Canonical section order for readable output (unknown keys keep their insertion order, appended).
_ROOT_ORDER = ("field", "camera", "walkmesh", "layers", "player", "npc", "gateway", "event",
               "camera_zone", "encounter", "music", "cutscene", "scene")


# --------------------------------------------------------------------------- serializer
def _fmt_str(s) -> str:
    """A TOML basic-string literal with the special characters escaped."""
    s = (str(s).replace("\\", "\\\\").replace('"', '\\"')
         .replace("\n", "\\n").replace("\t", "\\t").replace("\r", "\\r"))
    return f'"{s}"'


def _fmt_value(v) -> str:
    """Any TOML value as an inline literal: scalar, array, or inline table (recursive)."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return repr(v)                       # shortest round-trip repr (Python >= 3.1)
    if isinstance(v, str):
        return _fmt_str(v)
    if isinstance(v, dict):
        return "{" + ", ".join(f"{k} = {_fmt_value(x)}" for k, x in v.items()) + "}"
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(_fmt_value(x) for x in v) + "]"
    raise TypeError(f"cannot serialize {type(v).__name__} to TOML: {v!r}")


def _is_aot(v) -> bool:
    """True if v is a non-empty array of tables (list of dicts)."""
    return isinstance(v, (list, tuple)) and len(v) > 0 and all(isinstance(x, dict) for x in v)


def _fmt_inline_aot(key, items) -> str:
    """A readable multiline inline-table array, e.g. cutscene ``steps``."""
    lines = [f"{key} = ["]
    for it in items:
        lines.append("  " + _fmt_value(it) + ",")
    lines.append("]")
    return "\n".join(lines)


def _ordered_items(table):
    """(key, value) pairs in canonical root order first (for the top level), else insertion order."""
    keys = list(table.keys())
    if any(k in _ROOT_ORDER for k in keys):
        rank = {k: i for i, k in enumerate(_ROOT_ORDER)}
        keys.sort(key=lambda k: (rank.get(k, len(_ROOT_ORDER)), ))   # stable: unknown keep order
    return [(k, table[k]) for k in keys]


def _emit_table(path, table, out, *, ordered=False):
    """Emit one table's scalars/inline values, then its sub-tables / arrays-of-tables as sections."""
    items = _ordered_items(table) if ordered else list(table.items())
    deferred = []
    for k, v in items:
        if isinstance(v, dict) and k not in _INLINE_TABLE_KEYS:
            deferred.append((k, v, "table"))
        elif _is_aot(v) and k not in _INLINE_AOT_KEYS:
            deferred.append((k, v, "aot"))
        elif _is_aot(v) and k in _INLINE_AOT_KEYS:
            out.append(_fmt_inline_aot(k, v))
        else:
            out.append(f"{k} = {_fmt_value(v)}")
    for k, v, kind in deferred:
        sub = f"{path}.{k}" if path else k
        if kind == "table":
            out.append("")
            out.append(f"[{sub}]")
            _emit_table(sub, v, out)
        else:
            for elem in v:
                out.append("")
                out.append(f"[[{sub}]]")
                _emit_table(sub, elem, out)


def dumps(data: dict) -> str:
    """Serialize a field.toml dict to TOML text (round-trip-safe; canonical section order)."""
    out: list[str] = []
    _emit_table("", data, out, ordered=True)
    return "\n".join(out).strip("\n") + "\n"


def loads(text: str) -> dict:
    """Parse TOML text into a dict (thin wrapper over tomllib)."""
    return tomllib.loads(text)


# --------------------------------------------------------------------------- save guard
def _within(p: Path, base: Path) -> bool:
    """True if ``p`` is ``base`` or sits underneath it (lexical; no filesystem access)."""
    try:
        return p == base or p.is_relative_to(base)
    except ValueError:
        return False


def protected_reason(path) -> "str | None":
    """A reason string if ``path`` is a location the editor must NOT overwrite, else None.

    Guards the footgun where Save clobbers a shipped asset (e.g. the golden
    ``examples/vivi-hut/hut_int.field.toml``) or an installed package file -- both have bitten us.
    Pure + unit-testable (no Tk). Author on a copy, or scaffold a fresh project with
    ``ff9mapkit new``.
    """
    try:
        p = Path(path).resolve()
    except (OSError, ValueError):
        return None
    if any(part.lower() in ("site-packages", "dist-packages") for part in p.parts):
        return "that path is inside Python's site-packages (an installed copy of the kit)"
    pkg = Path(__file__).resolve().parents[1]          # the importable `ff9mapkit` package dir
    if _within(p, pkg):
        return "that path is inside the installed ff9mapkit package"
    if _within(p, pkg.parent / "examples"):            # bundled examples in a source checkout
        return "that is a bundled example -- edit a copy, or scaffold one with `ff9mapkit new`"
    return None


# --------------------------------------------------------------------------- the document
def _find_scene_path(field_path: Path, data: dict):
    """The sibling scene file for a field.toml: explicit ``[scene] file`` wins, else ``<stem>.scene.toml``
    (``<x>.field.toml`` -> ``<x>.scene.toml``). Returns a Path (may not exist) or None."""
    ref = data.get("scene", {}).get("file")
    if ref:
        return (field_path.parent / ref)
    stem = field_path.name
    stem = stem[:-len(".field.toml")] if stem.endswith(".field.toml") else field_path.stem
    return field_path.parent / f"{stem}.scene.toml"


class FieldDoc:
    """An open field.toml: its raw logic ``data`` (edited + saved) + a read-only Blender ``scene``.

    Edit ``data`` (or via the section helpers), then :meth:`save`. The scene file is never written.
    :meth:`merged` is the build-accurate view (logic + scene spatial), for display/validation.
    """

    def __init__(self, path: Path, data: dict, scene_path=None, scene_data=None):
        self.path = Path(path)
        self.data = data
        self.scene_path = Path(scene_path) if scene_path else None
        self.scene_data = scene_data

    # ---- io ----
    @classmethod
    def load(cls, path) -> "FieldDoc":
        path = Path(path)
        with path.open("rb") as fh:
            data = tomllib.load(fh)
        sp = _find_scene_path(path, data)
        scene_data = None
        if sp and sp.is_file():
            with sp.open("rb") as fh:
                scene_data = tomllib.load(fh)
        else:
            sp = None
        return cls(path, data, sp, scene_data)

    @classmethod
    def new(cls, path, field_id=4003, name="MY_ROOM", area=11, text_block=1073) -> "FieldDoc":
        """A fresh in-memory doc (not yet written) with a minimal [field] + a borrow camera stub."""
        data = {"field": {"id": int(field_id), "name": str(name), "area": int(area),
                          "text_block": int(text_block)},
                "camera": {"borrow": "camera.bgx"}}
        return cls(Path(path), data)

    def save(self) -> None:
        """Write the logic file (``data``) as TOML. The scene file is left untouched."""
        self.path.write_text(dumps(self.data), encoding="utf-8", newline="\n")

    def to_text(self) -> str:
        """The TOML text that :meth:`save` would write (for previews/diffs)."""
        return dumps(self.data)

    # ---- merged (build-accurate) view ----
    def merged(self) -> dict:
        """The field overlaid with its Blender scene (spatial), exactly as ``ff9mapkit build`` sees it.
        Reuses the kit's own merge so the editor's display matches the compiler."""
        if self.scene_data is None:
            return self.data
        from .. import build                     # lazy: avoid importing the builder unless needed
        return build._merge_scene(self.data, self.scene_data)

    # ---- section helpers (operate on the editable logic ``data``) ----
    @property
    def field(self) -> dict:
        return self.data.setdefault("field", {})

    def section(self, name: str) -> dict:
        """Get-or-create a single-table section ([camera]/[encounter]/[music]/[cutscene]/...)."""
        return self.data.setdefault(name, {})

    def list_section(self, name: str) -> list:
        """Get-or-create an array-of-tables section ([[npc]]/[[gateway]]/[[event]]/...)."""
        return self.data.setdefault(name, [])

    def remove_section(self, name: str) -> None:
        self.data.pop(name, None)

    def scene_entities(self, name: str) -> dict:
        """Scene-side spatial entities of a kind, keyed by ``name`` (for showing pos/zone), {} if none."""
        if not self.scene_data:
            return {}
        return {e["name"]: e for e in self.scene_data.get(name, []) if "name" in e}
