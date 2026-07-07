"""The kit's HEALTH CHECKS as a pure, importable report -- the engine behind the Workspace's
Setup & Health page (and a superset of what ``ff9mapkit doctor`` prints).

Qt-free and NEVER raises: every probe degrades to a row with level ``"bad"``/``"warn"`` and an
actionable ``advice`` string, because the whole point is to be runnable on the most broken install.
Each row: ``{"label", "value", "level", "advice"}`` with level in ``ok | warn | bad``.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from . import __version__


def _row(label, value, level="ok", advice=""):
    return {"label": label, "value": str(value), "level": level, "advice": advice}


def find_game() -> tuple:
    """(game_path | None, error message) -- the shared resolve step, exception-free."""
    try:
        from . import config
        return config.find_game_path(), ""
    except Exception as e:  # noqa: BLE001  (ConfigError or anything else -> unconfigured)
        return None, str(e)


def health_report(game=None) -> list:
    """Every check, in reading order. ``game`` (optional) overrides the resolved install path."""
    rows = [_row("Kit version", __version__)]

    try:
        import UnityPy  # noqa: F401
        rows.append(_row("UnityPy", "present"))
    except Exception:   # noqa: BLE001
        rows.append(_row("UnityPy", "absent", "warn",
                         "needed for import / thumbnails / catalogs — py -m pip install UnityPy"))

    try:
        import PySide6
        rows.append(_row("PySide6", getattr(PySide6, "__version__", "present")))
    except Exception:   # noqa: BLE001
        rows.append(_row("PySide6", "absent", "warn", "the GUI extra — py -m pip install PySide6"))

    ff = shutil.which("ffmpeg")
    ff_disp = ff if (not ff or len(ff) <= 58) else "…" + ff[-55:]     # winget paths run absurdly long
    rows.append(_row("ffmpeg", ff_disp or "absent", "ok" if ff else "warn",
                     "" if ff else "needed only for [music] file custom tracks — install ffmpeg "
                                   "or set $FFMPEG"))

    if game is None:
        game, err = find_game()
    else:
        game, err = Path(game), ""
    if game is None:
        rows.append(_row("FF9 install", "NOT FOUND", "bad",
                         "point the kit at your install: Locate game…, or set $FF9_GAME_PATH. "
                         f"({err})"))
        return rows                                    # everything below needs the install
    rows.append(_row("FF9 install", game))
    rows.append(_row("FF9_Launcher.exe", "found" if (Path(game) / "FF9_Launcher.exe").is_file()
                     else "MISSING", "ok" if (Path(game) / "FF9_Launcher.exe").is_file() else "bad",
                     "" if (Path(game) / "FF9_Launcher.exe").is_file()
                     else "this doesn't look like an FF9 Steam/GOG install"))
    sa = Path(game) / "StreamingAssets"
    rows.append(_row("StreamingAssets", "found" if sa.is_dir() else "MISSING",
                     "ok" if sa.is_dir() else "bad",
                     "" if sa.is_dir() else "this doesn't look like an FF9 Steam/GOG install"))

    try:
        from . import memoria
        st = memoria.memoria_status(game)
        if st.get("installed"):
            ver = None
            try:
                ver = memoria.read_assembly_version(Path(game) / "x64" / "FF9_Data" / "Managed"
                                                    / "Assembly-CSharp.dll")
            except Exception:   # noqa: BLE001
                pass
            rows.append(_row("Memoria engine", f"installed{f' (Assembly {ver})' if ver else ''}"))
        else:
            rows.append(_row("Memoria engine", "not detected", "warn",
                             "novel fields run on stock Memoria; FORKED fields need the custom engine "
                             "bundle — install Memoria first, then Install engine patches…"))
    except Exception as e:  # noqa: BLE001
        rows.append(_row("Memoria engine", f"probe failed ({e})", "warn", ""))

    try:
        from . import provision
        ok = provision.templates_present()
        rows.append(_row("Base templates", "extracted" if ok else "NOT extracted",
                         "ok" if ok else "warn",
                         "" if ok else "Run setup extracts them from your install (~1–2 min, once)"))
    except Exception as e:  # noqa: BLE001
        rows.append(_row("Base templates", f"probe failed ({e})", "warn", ""))

    try:
        from . import config as _cfg
        layout = _cfg.ModLayout(Path(game) / "FF9CustomMap")
        rows.append(_row("Mod folder", f"{layout.root}"
                         + ("" if layout.root.is_dir() else "  (created on first deploy)")))
    except Exception:   # noqa: BLE001
        pass
    return rows


def worst_level(rows) -> str:
    levels = {r["level"] for r in rows}
    return "bad" if "bad" in levels else ("warn" if "warn" in levels else "ok")


def quick_issues() -> list:
    """The 0-2 line summary for the Home banner -- CHEAP (no UnityPy import, no engine probe): is the
    install resolvable, and are the base templates extracted? Empty list = healthy enough to hide."""
    out = []
    game, _err = find_game()
    if game is None:
        out.append("FF9 install not configured")
        return out                                     # templates need the install anyway
    try:
        from . import provision
        if not provision.templates_present():
            out.append("base templates not extracted")
    except Exception:   # noqa: BLE001
        pass
    return out
