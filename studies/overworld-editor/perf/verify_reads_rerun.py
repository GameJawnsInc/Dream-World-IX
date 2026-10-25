"""verify_reads_rerun: re-run the reads lane's own probes UNCHANGED, but with their evidence and their draft redirected
to the verifier's folder (out/perf/reads/verify/), so the lane's evidence files are not overwritten and every write
goes into the verifier's own draft (a fresh copy of the live FF9CustomMap-world; the install is read only).

    py studies/overworld-editor/perf/verify_reads_rerun.py <module> [module args...]
    e.g.  verify_reads_rerun.py reads_soup
          verify_reads_rerun.py reads_card 3
          verify_reads_rerun.py reads_proto_card 3 base,A,B,C,ABC
Children the lane's probes spawn (``[python, __file__, "--child", ...]``) are routed back through this wrapper
(VERIFY_MOD names the module), so they too see the redirected folders."""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import reads_common as RC  # noqa: E402

VOUT = RC.WT / "studies" / "overworld-editor" / "out" / "perf" / "reads" / "verify"
VOUT.mkdir(parents=True, exist_ok=True)
RC.OUT = VOUT
RC.DRAFTS = VOUT / "drafts"


def _load(name):
    import importlib
    mod = importlib.import_module(name)
    mod.__file__ = str(Path(__file__).resolve())         # its children come back through this wrapper
    for k in ("OUT", "DRAFTS"):
        if hasattr(mod, k):
            setattr(mod, k, getattr(RC, k))
    return mod


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--child":
        mod = _load(os.environ["VERIFY_MOD"])
        if os.environ["VERIFY_MOD"] == "reads_cold":
            mod.child(sys.argv[2], sys.argv[3:])
        else:
            mod.child(*sys.argv[2:])
    else:
        name = sys.argv[1]
        os.environ["VERIFY_MOD"] = name
        mod = _load(name)
        sys.argv = [mod.__file__] + sys.argv[2:]
        mod.main()
