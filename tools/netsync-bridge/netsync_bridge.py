#!/usr/bin/env python3
"""ws->wss bridge for FF9 co-op ghost sync -- standalone launcher.

The canonical implementation lives in the ff9mapkit package
(``ff9mapkit/netsync_bridge.py``) and is normally started for you by
``ff9mapkit coop host`` / ``coop join``. This shim keeps the old standalone
entry point working: it uses the installed package when present, else the
package from this checkout (this file lives at ``tools/netsync-bridge/``).
"""

import sys
from pathlib import Path

try:
    from ff9mapkit.netsync_bridge import *          # noqa: F401,F403 -- re-export for importers
    from ff9mapkit.netsync_bridge import main
except ImportError:                                  # no installed kit -> use the checkout's package
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
    from ff9mapkit.netsync_bridge import *          # noqa: F401,F403
    from ff9mapkit.netsync_bridge import main

if __name__ == "__main__":
    sys.exit(main())
