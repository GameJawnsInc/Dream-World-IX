"""verify (gui skeptic): gui_proto_cold's two children (shipped / fast = F1+F2+F3), but INTERLEAVED (s, f, s, f, ...)
so a disk-cache or load drift cannot favour the variant that ran second, as the lane's back-to-back order could.
The children are the lane's own (`gui_proto_cold.py --child <variant>`), unchanged.

    py studies/overworld-editor/perf/verify_gui_cold.py [pairs]
Evidence: out/perf/gui/verify/verify_gui_cold.json
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gui_common as C                                                # noqa: E402

C.OUT = C.OUT / "verify"
C.OUT.mkdir(parents=True, exist_ok=True)


def main():
    pairs = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    env = dict(os.environ)
    env.pop("PYTHONDONTWRITEBYTECODE", None)
    env["PYTHONPYCACHEPREFIX"] = sys.pycache_prefix
    res = {"shipped": [], "fast": []}
    for i in range(pairs):
        for variant in (("shipped", "fast") if i % 2 == 0 else ("fast", "shipped")):
            r = subprocess.run([sys.executable, str(HERE / "gui_proto_cold.py"), "--child", variant],
                               capture_output=True, text=True, env=env, cwd=str(C.KIT), timeout=600)
            line = next((ln for ln in r.stdout.splitlines() if ln.startswith("RESULT ")), None)
            assert line, r.stdout[-2000:] + r.stderr[-3000:]
            res[variant].append(json.loads(line[7:]))
            print(res[variant][-1], flush=True)
    out = {"runs": res, **{k: C.stats([x["first_load_s"] for x in v]) for k, v in res.items()}}
    print({k: (out[k]["min_s"], out[k]["median_s"]) for k in res})
    C.dump("verify_gui_cold.json", out)


if __name__ == "__main__":
    main()
