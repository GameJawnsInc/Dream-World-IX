"""VERIFIER for CAP-4's far-plane sub-claim (READ-ONLY on the install).

CAP-4 derived the world far plane as (PsxGeomScreen+ClipDistance)/256 ~= 1173 u from WMWorld.PsxProj2UnityProj.
But that matrix is only installed by WMWorld.CreateProjectionMatrix, whose ONLY caller is
WMScriptDirector.HonoLateUpdate behind `useCustomProjectionMatrix` -- a private, non-serialized bool that only
the editor [ContextMenu] sets true. At runtime the world camera therefore renders with its own Unity
perspective (fieldOfView written by ff9.cs:2676) and its SCENE-SERIALIZED near/far planes.

This script finds the GameObject named "WorldCamera" in the player's scene files (x64/FF9_Data/level*) and
prints its Camera component's serialized near/far clip planes and FOV.

Calibration: the same scan must find at least one Camera component at all (else the instrument is blind).
Run:  py studies/terrain-malleability/capacity/verify_world_camera.py
"""
import json
from pathlib import Path

import UnityPy

G = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
OUT = Path(__file__).resolve().parent / "out"


def main():
    found, n_cams = [], 0
    for lv in sorted((G / "x64" / "FF9_Data").glob("level*")):
        try:
            env = UnityPy.load(str(lv))
        except Exception:
            continue
        for o in env.objects:
            if o.type.name != "Camera":
                continue
            n_cams += 1
            try:
                cam = o.read()
                go = cam.m_GameObject.read()
                name = go.m_Name
            except Exception:
                continue
            if "world" in name.lower():
                tt = o.read_typetree()
                found.append({"scene": lv.name, "go": name,
                              "near": tt.get("near clip plane"), "far": tt.get("far clip plane"),
                              "fov": tt.get("field of view"), "ortho": tt.get("orthographic")})
    res = {"cameras_scanned": n_cams, "world_cameras": found}
    OUT.mkdir(exist_ok=True)
    (OUT / "verify_world_camera.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
