"""RUNG F attempt 2 -- THE STOCK-TRUTH EYE BRIEF (read-only render composite).

The attempt-2 guidance: when the S-wall carry is falsified and option (c) is staged alone, "brief the
eye render set to include a stock-truth panel of the basin_envelope finding: the real pocket is
PARTIAL and open n/e, so the judgment standard is the MEASURED pocket, not the first sitting's
full-ring reading."

This composites the decisive renders into ONE briefing image with the measured findings as text, so
the fresh eye judges the staged build against measured stock, not an imagined full mountain ring:
  top-left   : STOCK -- the junction in its real massif context (calib_context_oblique)
  top-right  : STAGED BUILD -- the option (c) ecotone carry on the minted grass island (context obl.)
  bottom     : the MEASURED partial-pocket facts (basin_envelope / swall_probe / swall_perim), the
               falsification of the S-wall carry, and the judgment standard for the eye.

Reads only existing PNGs + the measurement JSONs. Writes out/rung_f/renders/rung_f_eye_brief.png.
Run: cd studies/overworld-topography && py rung_f_eye_panel.py
"""
from __future__ import annotations
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
RD = HERE / "out" / "rung_f" / "renders"
OUTJ = HERE / "out" / "rung_f"


def _load(name, w=None):
    p = RD / name
    if not p.exists():
        return None
    im = Image.open(p).convert("RGB")
    if w and im.width != w:
        im = im.resize((w, int(im.height * w / im.width)))
    return im


def main():
    be = json.loads((OUTJ / "basin_envelope.json").read_text(encoding="utf-8"))
    sp = json.loads((OUTJ / "swall_probe.json").read_text(encoding="utf-8"))
    pe = json.loads((OUTJ / "swall_perim.json").read_text(encoding="utf-8"))

    COLW = 760
    stock = _load("calib_context_oblique.png", COLW)
    build = _load("rung_f_context_oblique.png", COLW)
    plan = _load("rung_f_planview.png", 560)
    calibplan = _load("calib_context_plan.png", 560)
    if stock is None or build is None:
        print("missing base renders; run rung_f_eye_calib.py + rung_f_frame.py first")
        return

    pad = 16
    top_h = max(stock.height, build.height)
    mid_h = max(plan.height if plan else 0, calibplan.height if calibplan else 0)
    text_h = 300
    W = pad * 3 + COLW * 2
    H = pad + 24 + top_h + pad + 24 + mid_h + pad + text_h
    img = Image.new("RGB", (W, H), (18, 20, 24))
    dr = ImageDraw.Draw(img)

    dr.text((pad, 6), "RUNG F -- THE EYE BRIEF (attempt 2): judge the staged build against the MEASURED "
            "partial-pocket standard, NOT an imagined full mountain ring", fill=(240, 228, 150))
    y = pad + 24
    dr.text((pad, y - 16), "STOCK -- the real junction in its Daguerreo-massif context (the FORM the eye wanted)",
            fill=(200, 210, 235))
    dr.text((pad * 2 + COLW, y - 16), "STAGED BUILD -- option (c): the verbatim ecotone carry on the minted grass island",
            fill=(200, 235, 205))
    img.paste(stock, (pad, y))
    img.paste(build, (pad * 2 + COLW, y))
    y += top_h + pad + 24
    if calibplan:
        dr.text((pad, y - 16), "STOCK planview -- ecotone = the MARGIN of a continuous rock MASS (grey), pinned",
                fill=(200, 210, 235))
        img.paste(calibplan, (pad, y))
    if plan:
        dr.text((pad * 2 + COLW, y - 16), "STAGED planview -- ecotone (tan) two-ground character carried verbatim (R2/R3=stock)",
                fill=(200, 235, 205))
        img.paste(plan, (pad * 2 + COLW, y))
    y += mid_h + pad

    S = be["enclosing_rock_envelope"]
    perim = pe["sides"]
    lines = [
        ("THE MEASURED STOCK POCKET IS PARTIAL, NOT A RING (basin_envelope.json):", (245, 220, 120)),
        (f"   S: {int(S['S']['frac_rays_hitting_rock']*100)}% of rays hit rock (walled)   "
         f"W: {int(S['W']['frac_rays_hitting_rock']*100)}% (thin wall)   "
         f"N: {int(S['N']['frac_rays_hitting_rock']*100)}% (mostly open)   "
         f"E: {int(S['E']['frac_rays_hitting_rock']*100)}% (open) -- the real form is a SOUTH-walled, open-N/E pocket.", (215, 215, 220)),
        ("THE S-WALL TRUE-MESH CARRY WAS RIGOROUSLY FALSIFIED (3 read-only measurements, zero playtest cost):", (245, 220, 120)),
        (f"   swall_probe: the S wall DOES terminate to a lowland foot (0% mid-massif, foot 68-80u) -- so a strip could weld its foot; BUT", (215, 215, 220)),
        (f"   swall_perim: the SHAPED (ecotone+S-band) keep footprint has a non-weldable EAST edge -- "
         f"{int(perim['E']['edge_cliff_frac']*100)}% rock-cliff, p50 {perim['E']['edge_h_p50']}u max {perim['E']['edge_h_max']}u "
         f"(the continuous massif's east flank).", (230, 190, 190)),
        (f"   The massif is CONTINUOUS S<->E, so no keep-S / drop-E cut exists without an internal cut face. The ecotone is PINNED against the massif.", (230, 190, 190)),
        (f"   attempt-1: the rectangular 4x4 window's east edge is a 37u topo-49 cliff too; the full 448x384u massif cannot fit the 320x256u ocean site.", (230, 190, 190)),
        ("WHAT SHIPS, AND THE JUDGMENT STANDARD:", (245, 220, 120)),
        (f"   The two-ground CHARACTER ships by construction: R2 sat 0.4976/0.6303 fringe 0.8008, R3 backing 143/iface 127 -- BIT-IDENTICAL to stock (verbatim carry, code-disjoint CONFIRMED).", (200, 235, 205)),
        (f"   R1 realized standoff 46.8/48.9/49.5u > floors 39.95/44.64/42.97 on the NEW coast. Plumbing + contract GREEN.", (200, 235, 205)),
        (f"   F1 (the massif ENCLOSURE) is UNSOLVABLE at an isolated ocean island -- it needs a CONTINENTAL FUSE beside the real massif (a mechanism change).", (230, 205, 170)),
        (f"   => EYE: judge the ecotone-on-grass against the MEASURED partial pocket (S-walled, open N/E, pinned) -- is the two-ground margin faithful at THIS achievable site?", (245, 235, 180)),
    ]
    ty = y
    for txt, col in lines:
        dr.text((pad, ty), txt, fill=col)
        ty += 22

    out = RD / "rung_f_eye_brief.png"
    img.save(out)
    print(f"-> {out}  ({W}x{H})")
    return str(out)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
