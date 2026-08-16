#!/usr/bin/env pythonw
"""Double-click launcher for **Docs Studio** -- the standalone manager for the Dream World IX
Manual (docsite/). Create, edit, and reorganize the Manual's pages; run the build gates, the
docsite tests, the screenshot jobs, a local preview server, and (confirm-first) the live deploy.

Or run:  py docsite/studio.py
Needs PySide6 plus the docs build deps (markdown, pygments).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "docsite"))

from studio import main  # noqa: E402

if __name__ == "__main__":
    main()
