"""Lane jobs, step 1: make the lane's draft of FF9CustomMap-world (outside the install), build each card's Check and
Accept argv with the card's own command() builders, and compare them, token for token, to the argv the real card's
runner captured in the labs (out/c*_prep.json), modulo the draft path and the temp report path.

    py studies/overworld-editor/perf/jobs_argv.py
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jobs_common as J  # noqa: E402

LAB = {"forest": "c1_prep.json", "mountain": "c2_prep.json", "hill": "c6h_prep.json", "island": "c5i_prep.json",
       "carry": "c5t_prep.json", "coast": "c5c_prep.json", "sink": "c5_prep.json", "river": "c5r_prep.json"}


def norm(argv):
    out = []
    for a in argv:
        a = str(a)
        if a.endswith(".draft"):
            a = "<DRAFT>"
        elif a.endswith("verdict.json") or a.endswith("verdict4.json"):
            a = "<REPORT" + ("4>" if a.endswith("verdict4.json") else ">")
        elif a.lower().endswith("python.exe"):
            a = "<PY>"
        out.append(a)
    return out


def main():
    d = J.draft()
    res = {"draft": str(d), "verbs": {}}
    labs = J.WT / "studies" / "overworld-editor" / "out"
    for verb in J.VERBS:
        chk = J.prefix() + J.card_calls(verb, d, kind="check", report=Path("x/verdict.json"))[0]
        acc = [J.prefix() + c for c in J.card_calls(verb, d, kind="accept", report=Path("x/verdict.json"),
                                                    report4=Path("x/verdict4.json"))]
        lab = json.loads((labs / LAB[verb]).read_text(encoding="utf-8"))["tool"]["argvs"]
        mine = [norm(chk)] + [norm(a) for a in acc]
        theirs = [norm(a) for a in lab[:len(mine)]]
        same = mine == theirs
        res["verbs"][verb] = {"check": chk, "accept": acc, "lab_match": same,
                              "lab_argvs": [norm(a) for a in lab]}
        print(f"{verb:9s} lab-argv match: {same}")
        if not same:
            for m, t in zip(mine, theirs):
                if m != t:
                    print("   mine :", m)
                    print("   lab  :", t)
    (J.OUT / "argvs.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("draft:", d)


if __name__ == "__main__":
    main()
