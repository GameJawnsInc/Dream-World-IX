"""FF9 pure-Memoria background scene (``.bgx``) text format.

A ``.bgx`` is a small line-oriented text file describing how a field's background renders:
a sequence of blocks (``OVERLAY`` layers, a ``CAMERA``, optional ``ANIMATION`` /
``USE_BASE_SCENE`` / ``LANGUAGE``). Memoria parses it whitespace-insensitively (blank and
``#``/``//`` comment lines are skipped), so this module models blocks structurally and emits
a canonical form. Two helpers cover the kit's needs:

  * :class:`BgxScene` — parse / serialize / inspect (overlays + camera) / surgically replace.
  * :func:`build` — assemble a scene from a :class:`~ff9mapkit.scene.cam.Cam` + overlays.

OVERLAY keys: OverlayId? CameraId ViewportId Position(x,y,z) Size(w,h) Image Shader.
CAMERA keys : ViewDistance CenterOffset Position Range DepthOffset Viewport
              OrientationMatrix (9) | OrientationAngles (3).
Overlay Z (Position 3rd value) is the depth: smaller = nearer the camera (drawn in front).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import cam as _cam

BLOCK_TYPES = ("LANGUAGE", "USE_BASE_SCENE", "OVERLAY", "ANIMATION", "CAMERA")
DEFAULT_SHADER = "PSX/FieldMap_Abr_None"


@dataclass
class Overlay:
    """One background layer."""

    image: str
    position: tuple = (0, 0, 0)      # x, y, z(depth)
    size: tuple = (384, 448)         # w, h
    shader: str = DEFAULT_SHADER
    camera_id: int = 0
    viewport_id: int = 0
    overlay_id: int | None = None

    def to_lines(self) -> list[str]:
        lines = ["OVERLAY"]
        if self.overlay_id is not None:
            lines.append(f"OverlayId: {self.overlay_id}")
        lines.append(f"CameraId: {self.camera_id}")
        lines.append(f"ViewportId: {self.viewport_id}")
        lines.append(f"Position: {self.position[0]}, {self.position[1]}, {self.position[2]}")
        lines.append(f"Size: {self.size[0]}, {self.size[1]}")
        lines.append(f"Image: {self.image}")
        lines.append(f"Shader: {self.shader}")
        return lines

    @classmethod
    def from_fields(cls, fields: list[tuple]) -> "Overlay":
        o = cls(image="")
        for key, val in fields:
            args = [a.strip() for a in val.split(",")]
            if key == "OverlayId":
                o.overlay_id = int(args[0])
            elif key == "CameraId":
                o.camera_id = int(args[0])
            elif key == "ViewportId":
                o.viewport_id = int(args[0])
            elif key == "Position":
                o.position = (int(args[0]), int(args[1]), int(args[2]))
            elif key == "Size":
                o.size = (int(args[0]), int(args[1]))
            elif key == "Image":
                o.image = val.strip()
            elif key == "Shader":
                o.shader = val.strip()
        return o


def _camera_to_lines(cam: _cam.Cam) -> list[str]:
    # reuse cam.format_bgx_camera (already validated faithful) minus its trailing newline
    return _cam.format_bgx_camera(cam).rstrip("\n").split("\n")


@dataclass
class _Block:
    type: str
    fields: list = field(default_factory=list)   # ordered (key, value) for non-comment lines


class BgxScene:
    """Structured view of a ``.bgx``: leading comments, ordered blocks (overlays / camera / ...)."""

    def __init__(self):
        self.header_comments: list[str] = []     # comment lines before the first block
        self.blocks: list[_Block] = []

    # ---- parse ----
    @classmethod
    def parse(cls, text: str) -> "BgxScene":
        self = cls()
        cur: _Block | None = None
        seen_block = False
        for raw in text.splitlines():
            s = raw.strip()
            if not s:
                continue
            if s.startswith("#") or s.startswith("//"):
                if not seen_block:
                    self.header_comments.append(s)
                continue
            if s in BLOCK_TYPES:
                cur = _Block(s)
                self.blocks.append(cur)
                seen_block = True
                continue
            if cur is not None and ":" in s:
                key, _, val = s.partition(":")
                cur.fields.append((key.strip(), val.strip()))
        return self

    @classmethod
    def from_file(cls, path) -> "BgxScene":
        with open(path, encoding="utf-8", errors="replace") as fh:
            return cls.parse(fh.read())

    # ---- serialize (canonical) ----
    def to_text(self) -> str:
        out: list[str] = list(self.header_comments)
        for blk in self.blocks:
            if blk.type == "OVERLAY":
                out += self.overlay_of(blk).to_lines()
            elif blk.type == "CAMERA":
                out += _camera_to_lines(self.camera_of(blk))
            else:
                out.append(blk.type)
                out += [f"{k}: {v}" for k, v in blk.fields]
            out.append("")  # blank line between blocks
        return "\n".join(out).rstrip("\n") + "\n"

    # ---- typed views ----
    @staticmethod
    def overlay_of(blk: _Block) -> Overlay:
        return Overlay.from_fields(blk.fields)

    @staticmethod
    def camera_of(blk: _Block) -> _cam.Cam:
        text = "CAMERA\n" + "\n".join(f"{k}: {v}" for k, v in blk.fields) + "\n"
        return _cam.parse_bgx_cameras_text(text)[0]

    @property
    def overlays(self) -> list[Overlay]:
        return [self.overlay_of(b) for b in self.blocks if b.type == "OVERLAY"]

    @property
    def cameras(self) -> list[_cam.Cam]:
        return [self.camera_of(b) for b in self.blocks if b.type == "CAMERA"]

    # ---- edits ----
    def set_camera(self, cam: _cam.Cam) -> None:
        """Replace the (first) CAMERA block's fields from a Cam, preserving everything else."""
        lines = _camera_to_lines(cam)[1:]  # drop the "CAMERA" header
        fields = [tuple(s.split(": ", 1)) for s in lines]
        for blk in self.blocks:
            if blk.type == "CAMERA":
                blk.fields = [(k, v) for k, v in fields]
                return
        self.blocks.append(_Block("CAMERA", [(k, v) for k, v in fields]))


def build(camera: _cam.Cam, overlays: list[Overlay], *, header_comment: str | None = None,
          base_scene: str | None = None) -> str:
    """Assemble a complete ``.bgx`` text from a camera + ordered overlays."""
    out: list[str] = []
    if header_comment:
        out.append(f"# {header_comment}")
    if base_scene:
        out += ["USE_BASE_SCENE", f"Name: {base_scene}", ""]
    for ov in overlays:
        out += ov.to_lines()
        out.append("")
    out += _camera_to_lines(camera)
    out.append("")
    return "\n".join(out).rstrip("\n") + "\n"
