"""VERIFY C3's "nine special full values": a WIDER scan for full-IDALL equality tests than consumer_map.py's regex.

consumer_map.py's IDALL-FULL pattern needs a 3-5 digit (or hex) literal and a left side named mapid/.id/num, so it
cannot see e.g. `id == 56`. This scan accepts ANY integer/hex literal and any left side whose name is an IDALL
carrier (id, idall, IDALL, mapid, m_moveActorID, *.id), in every file that touches w_moveCHRStatus / WMMesh, and
then drops lines where the literal sits inside an m_GetID* decode (a bit-field test, not a full-value test).
It also normalises the literals so a value written twice in different bases (0xFEE == 4078) counts ONCE.

Read-only on the Memoria clone. Rerun:  py studies/terrain-malleability/consumption/verify_fullvalue_scan.py
"""
import re
import sys
from pathlib import Path

ACS = Path(r"C:\gd\FFIX\Memoria\Assembly-CSharp")
FILES = ["Global/ff9/ff9.cs", "Global/WM/WMBlock/WMBlock.cs", "Global/WM/WMPhysics.cs", "Global/WM/WMWorld/WMWorld.cs",
         "Global/Event/EventCollision.cs", "Global/Dialog/DialogManager.cs", "Global/WM/WMActor/WMActor.cs",
         "Global/EIcon.cs", "Global/Event/EventInput.cs", "Global/MainMenuUI.cs", "Global/UI/UIManager.cs"]
LHS = r"(?:\b(?:id|idall|IDALL|mapid|num|m_moveActorID)|\.id)"
PAT = re.compile(LHS + r"\s*(==|!=)\s*(0x[0-9A-Fa-f]+|\d+)\b")


def main():
    hits = []
    for rel in FILES:
        p = ACS / rel
        if not p.is_file():
            continue
        for i, ln in enumerate(p.read_text(encoding="utf-8", errors="replace").split("\n"), 1):
            s = ln.strip()
            if s.startswith("//"):
                continue
            for m in PAT.finditer(ln):
                pre = ln[:m.start()]
                if re.search(r"m_GetID(Topograph|Area|Event)\([^)]*$", pre) or "m_GetID" in ln[max(0, m.start() - 40):m.start()]:
                    continue
                hits.append((rel, i, int(m.group(2), 0), s[:120]))
    # keep only sites whose left side is a mesh-hit id (exclude obvious non-IDALL num uses by context words)
    world = [h for h in hits if any(k in h[3] for k in ("s_moveCHRStatus.id", "mapid", "num != 4078", "num != 4088",
                                                          "num != 2040", "(id == ", "id == 5"))]
    vals = sorted({h[2] for h in world})
    for h in world:
        print(f"  {h[0].split('/')[-1]}:{h[1]:<6} value={h[2]:<6} (0x{h[2]:X})  {h[3]}")
    print(f"distinct full-IDALL test values: {len(vals)} -> {[hex(v) for v in vals]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
