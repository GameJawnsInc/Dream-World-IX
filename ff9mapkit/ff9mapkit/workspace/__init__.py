"""The FF9 Map Kit **workspace** -- a modern PySide6 (Qt) shell for the kit's GUIs.

Phase 3 of the GUI makeover: one dockable window whose left rail IS the journey > campaign > field >
object hierarchy, a clickable breadcrumb, a central document area, a right inspector, and a bottom
Output/Problems dock -- the genuinely-modern, scalable replacement for the tkinter ``apps/*.pyw`` suite,
shipped side-by-side with them.

The shell **reuses the kit's tk-free backends unchanged** -- ``editor.feedback`` (Verdict/Problem),
``editor.breadcrumb`` (Crumb/trail), ``campaign`` (CampaignPlan/graph), ``editor.forms``/``editor.model``
-- so only the Qt view layer is new. ``style`` (the QSS builder) is PySide6-FREE and unit-testable; the
Qt widgets live in ``shell`` (imported lazily by the launcher so this package stays importable headless).
"""

from __future__ import annotations

from . import style  # noqa: F401  (re-export the PySide6-free QSS builder)

__all__ = ["style"]
