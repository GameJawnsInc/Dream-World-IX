"""READ-ONLY: each jump row's stock airborne window as a fraction of its clip (the source on Zidane vs the twin's own modal
SetJumpAnimation window) -- the frame-proportional sampling's fit (s157, studies/field-coop/GUEST-TRAVERSAL-TWO-PC.md
Finding 2).

The window census is jumpwindows.json beside this file: every literal `SetJumpAnimation( id, jump0, jump1 )` across ALL
language blocks of the 817 HW exports (C:\\gd\\FFIX\\reference\\test2, not in the repo), as {id: [[jump0, jump1, count],
...]} -- ids and frame indices only. It is regenerated from the exports when they are present (``--rescan`` forces it),
else read as committed. Writes jump_window_fit.txt beside this file."""
import collections
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EXPORTS = r"C:\gd\FFIX\reference\test2"
WINDOWS = os.path.join(HERE, "jumpwindows.json")
PAT = re.compile(r"SetJumpAnimation\( (\d+), (\d+), (\d+) \)")


def scan_exports() -> dict:
    win = collections.defaultdict(collections.Counter)
    for fn in sorted(os.listdir(EXPORTS)):
        if not (fn.startswith("test2_") and fn.endswith(".txt")):
            continue
        with open(os.path.join(EXPORTS, fn), encoding="utf-8", errors="replace") as f:
            for line in f:
                for m in PAT.finditer(line):
                    win[int(m.group(1))][(int(m.group(2)), int(m.group(3)))] += 1
    return {str(i): [[a, b, n] for (a, b), n in sorted(c.items())] for i, c in sorted(win.items())}


def load_windows() -> dict:
    if os.path.isdir(EXPORTS) and ("--rescan" in sys.argv or not os.path.exists(WINDOWS)):
        data = scan_exports()
        with open(WINDOWS, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=1)
    with open(WINDOWS, encoding="utf-8") as f:
        data = json.load(f)
    return {int(i): collections.Counter({(a, b): n for a, b, n in rows}) for i, rows in data.items()}


def main() -> None:
    rows = json.load(open(os.path.join(HERE, "twin_rows.json"), encoding="utf-8"))
    win = load_windows()

    def modal(i):
        return win[i].most_common(1)[0][0] if win.get(i) else None

    def frac(w, n):
        return "%.2f-%.2f" % (w[0] / n, w[1] / n) if w else "-"

    out = []
    for r in rows:
        if not r["suf"].startswith("JUMP"):
            continue
        sw = modal(r["src"]) or modal(r["src2"])
        tw = modal(r["twin"])
        out.append("%-8s ZDN_%-6s %s (%s of %d) -> %s_%-6s %s (%s of %d)" % (
            r["who"], r["suf"], frac(sw, r["fs"]), sw, r["fs"], r["tok"], r["tsuf"], frac(tw, r["ft"]), tw, r["ft"]))
    with open(os.path.join(HERE, "jump_window_fit.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
