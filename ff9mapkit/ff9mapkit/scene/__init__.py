"""Background-scene libraries.

  cam    - the camera math: project / decompose / synthesize any FF9 camera + the canvas map
  bgx    - the pure-Memoria background scene text format (overlays + camera)
  bgi    - the walkmesh codec + flat-floor / obj builder
  guide  - author a camera from a spec, frame a floor, emit a paint guide
"""

from . import bgi, bgx, cam, guide

__all__ = ["cam", "bgx", "bgi", "guide"]
