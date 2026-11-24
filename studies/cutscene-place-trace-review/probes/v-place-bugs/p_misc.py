from ff9mapkit.workspace import placedoc as P
from ff9mapkit import imagefield, build
# P11 degenerate zones
for name, q in [("collinear", [[0,0],[100,0],[200,0],[300,0]]),
                ("collapsed", [[0,0],[0,0],[100,100],[0,100]]),
                ("all-same", [[5,5],[5,5],[5,5],[5,5]])]:
    d = {"gateway": [{"name": "g", "to": 100, "zone": q}]}
    print(name, imagefield.zone_fan_audit([tuple(map(float, p)) for p in q]), "warn:", P.region_rows(d)[0]["warn"])
# P10 empty message
d = {"event": [{"name": "zone0", "message": "...", "zone": [[0,0],[100,0],[100,100],[0,100]]}]}
P.set_event_message(d, 0, "")
print("empty msg warn:", P.region_rows(d)[0]["warn"], "| shows text:", build._event_shows_text(d["event"][0]))
# P12 bands
for to in (9005, 3500, 20000, 0):
    d = {"gateway": [{"name": "g", "to": to, "zone": [[0,0],[100,0],[100,100],[0,100]]}]}
    print("to", to, "warn:", P.region_rows(d)[0]["warn"])
# P12 worldmap retarget
d = {"gateway": [{"name": "g", "to": "worldmap", "zone": [[0,0],[100,0],[100,100],[0,100]]}]}
print("worldmap row warn:", P.region_rows(d)[0]["warn"])
cur = d["gateway"][0].get("to") or 0
print("dialog initial value would be:", max(1, int(cur) if isinstance(cur, int) and cur > 0 else 1))
P.set_gateway_target(d, 0, 100); print("after retarget:", d["gateway"][0])
# P13
d = {}
P.place_prop(d, 0, 0); P.place_prop(d, 1, 1); del d["prop"][0]; P.place_prop(d, 2, 2)
print("props:", [p["name"] for p in d["prop"]])
