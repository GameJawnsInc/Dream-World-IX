"""Bundled binary data + accessors.

Contents
--------
blank_field/<lang>.eb.bytes
    The canonical *blank field* event script (956 bytes), one per language. This is the
    proven minimal playable field used as the starting point for every built field: a clean
    Main_Init (no stray popups, standard movement) plus a single player object. Content
    injectors clone/extend it; the builder writes it (with content) per language.

region_template.bin
    The 272-byte field-exit region body (a SetRegion polygon -> CalculateExitPosition /
    ExitField -> PreloadField -> set FieldEntrance -> Field(target)). The gateway injector
    patches its polygon / entrance / target and appends it as a new entry.

Provenance / distribution note
------------------------------
These blobs are DERIVED from Final Fantasy IX field data (the blank field is a cleaned clone of a
base field; the region template is a base field's exit region). To avoid redistributing Square Enix
game bytes, the public repo ships **none** of them -- they are regenerated from the user's own,
legally-owned FF9 install by ``ff9mapkit extract-templates`` (see :mod:`ff9mapkit.provision` and
docs/PROVENANCE.md) into a local, gitignored cache. The accessors below read that cache and raise a
clear "run extract-templates" message if it isn't present yet.
"""

from __future__ import annotations

from ..config import LANGS
from .. import provision


# Verified bytes, once per process. EVERY synthesized field is built on these blobs, so a change here
# that nothing notices is embedded silently into everything the kit emits.
_VERIFIED: dict = {}


def _read_verified(path, expect_sha: str, what: str) -> bytes:
    """Read a cached template and CHECK IT AGAINST THE MANIFEST HASH.

    ``extract-templates`` verifies these blobs when it WRITES them (:mod:`ff9mapkit.provision`), and
    nothing verified them when they were READ -- the accessors did ``is_file()`` then ``read_bytes()``.
    The cache is a gitignored directory outside version control, on a machine shared by many worktrees,
    so between that write and this read it can be truncated by a full disk, half-written by an
    interrupted extraction, hand-edited, or left over from a different kit version whose patch produced
    different bytes. Any of those was embedded silently into every field built afterwards -- the blank
    field IS the starting point for every synthesized script.

    The manifest ships in the wheel (pyproject package-data), so this is not a check that quietly stops
    running when installed from PyPI. Hashed once per process: 956 bytes x 7 languages is nothing beside
    a build, and a campaign reads them thousands of times.
    """
    key = str(path)
    hit = _VERIFIED.get(key)
    if hit is not None:
        return hit
    if not path.is_file():
        raise FileNotFoundError(provision.MISSING_MSG)
    b = path.read_bytes()
    got = provision.sha256(b)
    if expect_sha and got != expect_sha:
        raise ValueError(
            f"{what}: the extracted template at {path} does not match the manifest hash it was written "
            f"with (expected {expect_sha[:16]}..., got {got[:16]}...). This cache is regenerated from "
            f"YOUR install and is not version-controlled, so it can be truncated, half-written by an "
            f"interrupted extraction, or left over from a different kit version. EVERY synthesized field "
            f"is built on these bytes -- re-run `ff9mapkit extract-templates` rather than building on "
            f"them.")
    _VERIFIED[key] = b
    return b


def blank_field_bytes(lang: str = "us") -> bytes:
    """Bytes of the blank field event script for *lang* (defaults to 'us'). Regenerated from the user's
    FF9 install by ``ff9mapkit extract-templates``; raises if that hasn't been run, or if the cached
    bytes no longer match the manifest hash they were written with."""
    if lang not in LANGS:
        raise ValueError(f"unknown language {lang!r}; expected one of {LANGS}")
    p = provision.blank_dir() / f"{lang}.eb.bytes"
    expect = (provision.load_manifest().get("blank", {}).get("sha256") or {}).get(lang, "")
    return _read_verified(p, expect, f"blank field ({lang})")


def region_template() -> bytes:
    """The 272-byte field-exit region template (regenerated from the user's install), checked against
    the manifest hash it was written with."""
    p = provision.region_template_path()
    expect = provision.load_manifest().get("region_template", {}).get("sha256", "")
    return _read_verified(p, expect, "region template")
