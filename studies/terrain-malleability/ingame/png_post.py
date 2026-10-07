"""OFFLINE RE-SCORE of a png_session.py run directory -- the same checks (png_judge.evaluate), recomputed from the
archived frames and the archived Memoria.log, so a verdict never rests on the live run's own bookkeeping.

    py studies/terrain-malleability/ingame/png_post.py <run dir>
Writes <run dir>/png_post.json and prints every check.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import png_judge as J                                   # noqa: E402


def rescore(run_dir: Path) -> dict:
    rec = json.loads((run_dir / "png_session.json").read_text(encoding="utf-8"))
    prep = json.loads(J.PREP_JSON.read_text(encoding="utf-8"))
    shots_dir = run_dir / "shots"
    # 1. frames: recount every shot from the PNG on disk
    for pose in (rec.get("poses") or {}).values():
        for cell in ("A", "B"):
            row = pose.get(cell) or {}
            files = []
            for i, sh in enumerate(row.get("shots") or []):
                f = shots_dir / sh["file"]
                c = J.frame_counts(f)
                c["file"] = sh["file"]
                row["shots"][i] = c
                files.append(f)
            if len(files) > 1 and row["shots"][0]["w"] > 8:
                reg = J.lower_region(row["shots"][0]["w"], row["shots"][0]["h"])
                row["gray_change"] = [J.gray_change(files[k], files[k + 1], reg) for k in range(len(files) - 1)]
    rl = rec.get("reload") or {}
    for i, sh in enumerate(rl.get("shots") or []):
        c = J.frame_counts(shots_dir / sh["file"])
        c["file"] = sh["file"]
        rl["shots"][i] = c
    # 2. receipts: re-parse each visit's slice of the ARCHIVED engine log (same byte offsets: it is a copy)
    log = run_dir / "Memoria.log"
    if log.exists():
        data = log.read_bytes()
        visits = rec.get("visits") or []
        for i, v in enumerate(visits):
            start = int(v["mark"][1] or 0)
            end = int(visits[i + 1]["mark"][1]) if i + 1 < len(visits) and visits[i + 1]["mark"][1] else len(data)
            if end <= start:
                end = len(data)
            rows = J.receipts(data[start:end].decode("utf-8", errors="replace"))
            v["rows"], v["summary"] = rows, J.receipt_summary(rows)
    checks = J.evaluate(rec, prep)
    out = {"run_dir": str(run_dir), "checks": [{"ok": ok, "what": w, "detail": d} for ok, w, d in checks],
           "passed": sum(ok for ok, _, _ in checks), "total": len(checks)}
    (run_dir / "png_post.json").write_text(json.dumps({"rescored_record": rec, **out}, indent=1, default=str),
                                           encoding="utf-8")
    return out


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    out = rescore(Path(argv[1]))
    for c in out["checks"]:
        print(("PASS " if c["ok"] else "FAIL ") + c["what"] + ("  -- " + c["detail"] if c["detail"] else ""))
    print(f"{out['passed']}/{out['total']} checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
