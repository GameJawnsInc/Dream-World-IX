import sys
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit")
from ff9mapkit.workspace import placedoc as P
from ff9mapkit import imagefield as IF
cases = {"ccw":[(0,0),(100,0),(100,100),(0,100)], "cw":[(0,0),(0,100),(100,100),(100,0)],
         "bowtie":[(0,0),(100,100),(100,0),(0,100)], "concave":[(0,0),(100,0),(20,20),(0,100)],
         "degenerate-line":[(0,0),(50,0),(100,0),(150,0)], "tiny":[(0,0),(1,0),(1,1),(0,1)]}
for k,q in cases.items():
    d={}; P.place_event(d, q); d["event"][0]["message"]="hi"
    r=P.region_rows(d)[0]; print(k, IF.zone_fan_audit(r["quad"]), "| warn:", r["warn"])
# empty message passes region_rows quietly
d={}; P.place_event(d, cases["ccw"]); P.set_event_message(d, 0, "")
print("empty message warn:", P.region_rows(d)[0]["warn"], d["event"][0])
from ff9mapkit import build
print("build _event_shows_text:", build._event_shows_text(d["event"][0]))
