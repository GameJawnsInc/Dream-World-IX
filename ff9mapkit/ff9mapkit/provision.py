"""Bring-your-own-install provisioning -- so the public repo ships ZERO Square Enix game data.

``ff9mapkit`` is an authoring *tool*, not a game distribution. A few base assets it needs are DERIVED
from FF9's own field data:

  * the **blank field** (956 B/language) -- the minimal playable field every built field starts from;
    it is a *cleaned* clone of a base game field (popups removed, movement fixed, an after-battle
    reinit added),
  * the **exit-region template** (272 B) -- the standard field-exit entry the gateway injector patches,
  * a handful of **test fixtures** (a real field script / camera / walkmesh) used by the offline suite.

Rather than bundle those copyrighted bytes, the repo ships only **our** part:

  * tiny copy/insert **patches** -- the edits we made to a base field, i.e. our own bytes plus
    *copy-from-offset* directives (never the game's bytes), exactly like an IPS/BPS ROM-hack patch, and
  * a **manifest** naming which base fields to read and the SHA-256 of every regenerated blob.

``ff9mapkit extract-templates`` reads the user's OWN, legally-owned FF9 install, applies the patches,
and writes the assets into a local cache (gitignored). This mirrors how emulators / ROM-hack tools
handle copyrighted assets: you must own the game. No FF9 bytes are ever redistributed by this project.

The patch *apply* path is pure-stdlib; only the extraction step imports UnityPy (lazily, via
``extract``) and needs the game install.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from .config import LANGS

# ---- where the regenerated (gitignored) assets live -----------------------------------------------
# Default: the package's own ``data/`` dir (works for the documented editable/clone install -- the
# files land in the working tree, gitignored). Override with $FF9MAPKIT_DATA for a read-only wheel
# install or a shared cache.
_PKG_DATA = Path(__file__).resolve().parent / "data"
PROVENANCE = _PKG_DATA / "provenance"          # tracked: ships our patches + manifest (no game bytes)
MANIFEST = PROVENANCE / "manifest.json"


def data_dir() -> Path:
    env = os.environ.get("FF9MAPKIT_DATA")
    return Path(env) if env else _PKG_DATA


def blank_dir() -> Path:
    return data_dir() / "blank_field"


def region_template_path() -> Path:
    return data_dir() / "region_template.bin"


# ---- copy/insert patch format ---------------------------------------------------------------------
# A patch transforms a base field's bytes into one of our derived blobs. It is a list of ops:
#   ["c", off, length]   copy ``length`` bytes from the SOURCE at ``off`` (references, not bytes)
#   ["i", "<hex>"]       insert these literal bytes (OUR edits -- the only game-independent content)
# Stored as JSON with the source's SHA-256 (so we can verify the user extracted the right base) and
# the expected output length. Apply is exact + pure-stdlib.

def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


_MIN_COPY = 4   # any run >= this that exists in the source is referenced (copied), never shipped


def _decompose_insert(src: bytes, b: bytes) -> list:
    """Turn a would-be insert ``b`` into ops that ship only bytes NOT present in ``src``: any run of
    >= _MIN_COPY bytes found in the source becomes a copy (a reference, not data); the rest are true
    inserts. This is the airtight guarantee -- the patch can't ship a meaningful game-byte run, even
    one difflib failed to align (e.g. the per-language field name)."""
    out: list = []
    i, n = 0, len(b)
    novel = bytearray()

    def flush():
        if novel:
            out.append(["i", bytes(novel).hex()])
            novel.clear()

    while i < n:
        j = i + 1                                   # longest prefix b[i:j] that occurs in src
        while j <= n and src.find(b[i:j]) >= 0:
            j += 1
        run = j - 1 - i
        if run >= _MIN_COPY:
            flush()
            out.append(["c", src.find(b[i:i + run]), run])
            i += run
        else:
            novel.append(b[i])
            i += 1
    flush()
    return out


def make_patch(src: bytes, dst: bytes) -> dict:
    """Build a copy/insert patch turning ``src`` -> ``dst`` (maintainer side). difflib maximizes
    copies; then every insert is decomposed so no run of >= _MIN_COPY bytes present in the source is
    ever shipped (only our genuinely-novel edits remain as inserts)."""
    import difflib  # noqa: PLC0415 - only the maintainer regen path needs it
    ops: list = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=src, b=dst, autojunk=False).get_opcodes():
        if tag == "equal":
            ops.append(["c", i1, i2 - i1])
        elif tag in ("replace", "insert"):
            ops.extend(_decompose_insert(src, dst[j1:j2]))
        # 'delete' -> drop (copy nothing)
    inserted = sum(len(bytes.fromhex(op[1])) for op in ops if op[0] == "i")
    return {"src_sha256": sha256(src), "out_len": len(dst), "out_sha256": sha256(dst),
            "insert_bytes": inserted, "ops": ops}


def patch_game_runs(src: bytes, patch: dict, min_run: int = _MIN_COPY) -> list:
    """The airtight audit: any INSERT run of >= ``min_run`` bytes that also occurs in ``src`` (i.e. a
    game-byte run the patch would ship). Should always be empty -- :func:`make_patch` decomposes those
    into copies. Returned as a list of (hex, src_offset) so a violation is inspectable."""
    bad = []
    for op in patch["ops"]:
        if op[0] == "i":
            b = bytes.fromhex(op[1])
            if len(b) >= min_run and src.find(b) >= 0:
                bad.append((b.hex(), src.find(b)))
    return bad


def apply_patch(src: bytes, patch: dict) -> bytes:
    """Apply a copy/insert patch to a freshly-extracted base field -> the derived blob (runtime side).

    Verifies the source matches the patch's recorded hash (clear error if the user's base field
    differs -- e.g. a non-vanilla install) and that the result matches the expected output hash."""
    if patch.get("src_sha256") and sha256(src) != patch["src_sha256"]:
        raise ValueError(
            "source field bytes don't match the expected base (a modified/non-vanilla install?). "
            "Re-run against an unmodified FF9 install, or report this with your Memoria version.")
    out = bytearray()
    for op in patch["ops"]:
        if op[0] == "c":
            _, off, length = op
            out += src[off:off + length]
        elif op[0] == "i":
            out += bytes.fromhex(op[1])
        else:
            raise ValueError(f"unknown patch op {op[0]!r}")
    res = bytes(out)
    if len(res) != patch["out_len"] or ("out_sha256" in patch and sha256(res) != patch["out_sha256"]):
        raise ValueError("patched output didn't match the expected hash -- patch/source mismatch.")
    return res


# ---- manifest -------------------------------------------------------------------------------------
def load_manifest() -> dict:
    if not MANIFEST.is_file():
        raise FileNotFoundError(f"missing provenance manifest at {MANIFEST}")
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def templates_present() -> bool:
    """True if the load-bearing base assets (blank field + region template) have been extracted."""
    bd = blank_dir()
    return region_template_path().is_file() and all((bd / f"{l}.eb.bytes").is_file() for l in LANGS)


MISSING_MSG = (
    "FF9 base templates not found. ff9mapkit ships no game data -- it regenerates the few base assets\n"
    "it needs from YOUR FF9 install. Run:\n\n"
    "    ff9mapkit extract-templates\n\n"
    "(needs UnityPy + your FF9 install path; see docs/PROVENANCE.md). This is a one-time step."
)


# ---- extraction orchestration (needs the install; UnityPy lazy via `extract`) ---------------------
def _write(path: Path, b: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b)


def extract_templates(game=None, *, fixtures: bool = True, verbose: bool = True) -> dict:
    """Regenerate the kit's base assets from the user's FF9 install per the manifest. Writes the blank
    field + region template into the data cache, and (if ``fixtures`` and a repo checkout is present)
    the test fixtures into ``tests/fixtures``. Verifies every output against its manifest SHA-256.

    Returns a report dict. Raises with guidance if the install / a base field can't be read."""
    from . import extract  # noqa: PLC0415 - lazy: only this path needs UnityPy + the install
    man = load_manifest()
    report = {"written": [], "verified": [], "skipped": []}

    def _event(fbg, lang):
        b = extract.extract_event_script(fbg, game=game, lang=lang)
        if not b:
            raise FileNotFoundError(
                f"couldn't read event script for {fbg} ({lang}) from the install -- is the game path "
                f"correct and the field present? (ff9mapkit doctor)")
        return b

    # 1) blank field: per-language patch from the base field's event script
    blk = man["blank"]
    for lang in LANGS:
        src = _event(blk["source_fbg"], lang)
        patch = json.loads((PROVENANCE / blk["patch"].format(lang=lang)).read_text(encoding="utf-8"))
        out = apply_patch(src, patch)
        if sha256(out) != blk["sha256"][lang]:
            raise ValueError(f"blank {lang}: regenerated bytes don't match the manifest hash")
        _write(blank_dir() / f"{lang}.eb.bytes", out)
        report["written"].append(f"blank_field/{lang}.eb.bytes")
        report["verified"].append(f"blank {lang}")
        if verbose:
            print(f"  blank_field/{lang}.eb.bytes  ({len(out)} B)  OK")

    # 2) region template: single patch from the base field's exit region
    reg = man["region_template"]
    src = _event(reg["source_fbg"], reg["lang"])
    patch = json.loads((PROVENANCE / reg["patch"]).read_text(encoding="utf-8"))
    out = apply_patch(src, patch)
    if sha256(out) != reg["sha256"]:
        raise ValueError("region_template: regenerated bytes don't match the manifest hash")
    _write(region_template_path(), out)
    report["written"].append("region_template.bin")
    report["verified"].append("region_template")
    if verbose:
        print(f"  region_template.bin  ({len(out)} B)  OK")

    # 3) test fixtures (only when run from a repo checkout that has tests/)
    fixtures_dir = _PKG_DATA.parent.parent / "tests" / "fixtures"
    if fixtures and fixtures_dir.is_dir():
        for name, spec in man.get("fixtures", {}).items():
            out = _extract_fixture(extract, spec, game)
            if sha256(out) != spec["sha256"]:
                raise ValueError(f"fixture {name}: regenerated bytes don't match the manifest hash")
            _write(fixtures_dir / name, out)
            report["written"].append(f"tests/fixtures/{name}")
            report["verified"].append(name)
            if verbose:
                print(f"  tests/fixtures/{name}  ({len(out)} B)  OK")
    elif fixtures and verbose:
        print("  (no tests/ checkout -- skipping test fixtures)")
        report["skipped"].append("fixtures")

    return report


def _extract_fixture(extract, spec: dict, game) -> bytes:
    """Regenerate one test fixture from the install per its manifest ``kind``."""
    kind = spec["kind"]
    if kind in ("event_verbatim", "event_with_gateway"):
        b = extract.extract_event_script(spec["source_fbg"], game=game, lang=spec.get("lang", "us"))
        if not b:
            raise FileNotFoundError(f"couldn't read {spec['source_fbg']} from the install")
        if kind == "event_with_gateway":   # vanilla field + the kit's own door (no third-party mod bytes)
            from .content import gateway as _gw  # noqa: PLC0415
            g = spec["gateway"]
            b = _gw.inject_gateway(b, g["target"], entrance=g["entrance"], zone=_gw.quad_zone(g["zone"]))
        return b
    if kind in ("walkmesh_verbatim", "camera_bgx"):
        import tempfile  # noqa: PLC0415
        td = Path(tempfile.mkdtemp())
        extract.extract_field(spec["source_fbg"], td, game=game)
        f = td / ("walkmesh.bgi" if kind == "walkmesh_verbatim" else "camera.bgx")
        return f.read_bytes()
    raise ValueError(f"unknown fixture kind {kind!r}")
