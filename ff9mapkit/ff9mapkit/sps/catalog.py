"""Live enumeration of a field's ``.sps`` effects from the install (Tier 0 catalog). INSTALL-GATED, like
``extract.py``: nothing is baked -- the ``.sps``/``spt.tcb`` bytes are Square-Enix game data (gitignored, never
shipped), and there is no Memoria name-table to transcribe -- so this reads the bundle on demand and degrades to
``[]`` / ``None`` with no install or UnityPy. Reuses the same enumeration trio ``extract.write_native_project``
uses: ``find_field`` -> ``env.container`` prefix filter -> ``_raw_bytes``. -> [[project-ff9-sps-authoring]].
"""
from __future__ import annotations

from dataclasses import dataclass

from . import codec


@dataclass(frozen=True)
class SpsEntry:
    field_token: str    # what import/extract takes (a field id or an FBG/mapid token)
    folder: str         # the donor FBG folder the effect lives under
    sps_id: int         # the numeric .sps id (filename stem == the RunSPSCode arg)
    container_key: str  # the env.container key, for a lazy byte read


def _fieldmaps_prefix(folder: str) -> str:
    return f"assets/resources/fieldmaps/{folder}/"


def list_field_sps(field, *, game=None, bundle=None) -> list[SpsEntry]:
    """Every ``.sps`` effect bin in a field's FBG folder, sorted by id. ``[]`` if the install/UnityPy is absent
    or the field has no effects."""
    try:
        from .. import extract
        _bundle, folder, _roles, env = extract.find_field(field, game=game, bundle=bundle)
    except Exception:  # noqa: BLE001 -- no install / no UnityPy / unknown field -> empty catalog
        return []
    pref = _fieldmaps_prefix(folder)
    out: list[SpsEntry] = []
    for key in env.container:
        if not key.startswith(pref) or not key.endswith(".sps.bytes"):
            continue
        stem = key.rsplit("/", 1)[-1][: -len(".sps.bytes")]
        try:
            sid = int(stem)
        except ValueError:
            continue
        out.append(SpsEntry(str(field), folder, sid, key))
    return sorted(out, key=lambda e: e.sps_id)


def load_sps_bytes(entry: SpsEntry, *, game=None, bundle=None) -> bytes:
    """Raw bytes of one effect bin."""
    from .. import extract
    _bundle, _folder, _roles, env = extract.find_field(entry.field_token, game=game, bundle=bundle)
    return extract._raw_bytes(env.container[entry.container_key].read())


def load_sps(entry: SpsEntry, *, game=None, bundle=None) -> codec.Sps:
    """Parse one effect to its codec model (the detail/preview source)."""
    return codec.parse(load_sps_bytes(entry, game=game, bundle=bundle))


def load_tcb(field, *, game=None, bundle=None) -> bytes | None:
    """The field's shared ``spt.tcb`` texture bytes (every effect in the field samples it), or ``None``."""
    try:
        from .. import extract
        _bundle, folder, _roles, env = extract.find_field(field, game=game, bundle=bundle)
    except Exception:  # noqa: BLE001
        return None
    from .. import extract
    key = _fieldmaps_prefix(folder) + "spt.tcb.bytes"
    for k, obj in env.container.items():            # ContainerHelper has no .get(); iterate items
        if k == key:
            return extract._raw_bytes(obj.read())
    return None


def effect_facts(sps: codec.Sps) -> list[tuple[str, str]]:
    """Human-readable facts about one effect (for the CLI / Info Hub detail pane)."""
    prims = [len(f) for f in sps.frames]
    tp = sps.tpage
    return [
        ("kind", "SPS field effect"),
        ("frames", str(sps.frame_count)),
        ("prims/frame", f"{min(prims)}-{max(prims)}" if prims else "0"),
        ("quad half-size", f"{sps.half_w}x{sps.half_h}"),
        ("uv cells", str(len(sps.uv_table))),
        ("ramp colours", str(len(sps.rgb_table))),
        ("tpage", f"TP{tp['TP']} TX{tp['TX']} TY{tp['TY']}"),
        ("clut", f"Y{sps.clut['ClutY']} X{sps.clut['ClutX']}"),
    ]
