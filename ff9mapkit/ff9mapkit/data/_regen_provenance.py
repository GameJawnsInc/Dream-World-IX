"""MAINTAINER tool: regenerate the provenance artifacts (patches + manifest) from a vanilla FF9
install, so the public repo can ship ZERO Square Enix bytes.

Run from a repo checkout with $FF9_GAME_PATH set (or --game), against an UNMODIFIED install:

    python -m ff9mapkit.data._regen_provenance

It writes ff9mapkit/data/provenance/{manifest.json, blank.<lang>.patch, region_template.patch}
-- all OURS (copy/insert diffs + hashes + source field names; no game bytes) -- and verifies that
`ff9mapkit extract-templates` would reproduce the current on-disk blobs byte-for-byte. The actual
game-derived blobs (blank_field/, region_template.bin, the binary test fixtures) are NOT committed;
end users regenerate them locally from their own install.

This is the inverse bookend of provision.extract_templates: this AUTHORS the patches; that APPLIES them.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from .. import provision
from ..config import LANGS

HERE = Path(__file__).resolve().parent
PROV = HERE / "provenance"

# --- the base fields the kit's assets are derived from (all present in a vanilla install) ----------
BLANK_SRC = "fbg_n11_ldbm_map203_lb_hng_0"     # field 1357 (L.Castle/Hangar) -> the cleaned blank field
REGION_SRC = "fbg_n01_alxt_map031_at_wpn_0"    # ALEX3_AT_WEAPON -> the exit-region template
ALEX_SRC = "fbg_n01_alxt_map016_at_msa_0"      # ALEX1_AT_STREET_A (vanilla field 100) -> eventscan oracle
GRGR_SRC = "fbg_n21_grgr_map420_gr_cen_0"      # Gargan Roo centre -> camera fixture
MULTIFLOOR_SRC = "fbg_n00_tshp_map008_th_upr_0"  # Prima Vista upper deck (3 floors) -> multi-floor walkmesh
#   (chosen because its real .bgi round-trips byte-exact through the kit's codec AND is seam-clean:
#    fully walk-reachable, strands on obj re-export, reconciles -- so it exercises the seam machinery.)

# the Session-12 Alexandria door, re-injected onto the vanilla field so the eventscan oracle keeps its
# "3 real exits + 1 injected door" shape without redistributing AlternateFantasy's modified bytes.
ALEX_DOOR = {"target": 4000, "entrance": 0,
             "zone": [[-700, 2200], [200, 2200], [200, 3400], [-700, 3400]]}

sha = lambda b: hashlib.sha256(b).hexdigest()


def main(argv=None) -> int:
    import argparse
    from .. import extract
    ap = argparse.ArgumentParser(description="regenerate ff9mapkit provenance patches + manifest")
    ap.add_argument("--game", help="FF9 install path (else $FF9_GAME_PATH / config)")
    args = ap.parse_args(argv)
    game = args.game

    PROV.mkdir(parents=True, exist_ok=True)
    manifest: dict = {
        "_note": ("ff9mapkit ships NO Final Fantasy IX game data. These entries describe how to "
                  "regenerate the small set of base assets the kit needs from YOUR OWN install via "
                  "`ff9mapkit extract-templates`. The .patch files contain only our edits + copy "
                  "offsets (never game bytes). See docs/PROVENANCE.md."),
    }

    # 1) blank field: per-language copy/insert patch (1357 -> our cleaned blank)
    blank_sha = {}
    for lang in LANGS:
        src = extract.extract_event_script(BLANK_SRC, game=game, lang=lang)
        dst = (HERE / "blank_field" / f"{lang}.eb.bytes").read_bytes()   # current on-disk blank
        patch = provision.make_patch(src, dst)
        (PROV / f"blank.{lang}.patch").write_text(json.dumps(patch), encoding="utf-8")
        assert provision.apply_patch(src, patch) == dst, f"blank {lang} patch round-trip failed"
        bad = provision.patch_game_runs(src, patch)
        assert not bad, f"blank {lang}: patch would ship game-byte runs {bad}"
        blank_sha[lang] = sha(dst)
        print(f"  blank.{lang}.patch  insert={patch['insert_bytes']}B (no game runs)  -> reproduces blank OK")
    manifest["blank"] = {"source_fbg": BLANK_SRC, "patch": "blank.{lang}.patch", "sha256": blank_sha}

    # 2) region template: single patch (ALEX3_AT_WEAPON -> our 272B exit-region template)
    src = extract.extract_event_script(REGION_SRC, game=game, lang="us")
    dst = (HERE / "region_template.bin").read_bytes()
    patch = provision.make_patch(src, dst)
    (PROV / "region_template.patch").write_text(json.dumps(patch), encoding="utf-8")
    assert provision.apply_patch(src, patch) == dst, "region patch round-trip failed"
    assert not provision.patch_game_runs(src, patch), "region patch would ship game-byte runs"
    manifest["region_template"] = {"source_fbg": REGION_SRC, "lang": "us",
                                   "patch": "region_template.patch", "sha256": sha(dst)}
    print(f"  region_template.patch  insert={patch['insert_bytes']}B  -> reproduces template OK")

    # 3) test fixtures, regenerated from the install (sha recorded so extract-templates self-verifies)
    fixtures = {}
    fix_dir = HERE.parent.parent / "tests" / "fixtures"

    #   alex100: vanilla field 100 + the kit's own door injection (no AlternateFantasy bytes)
    from ..content import gateway as _gw
    van = extract.extract_event_script(ALEX_SRC, game=game, lang="us")
    door = _gw.inject_gateway(van, ALEX_DOOR["target"], entrance=ALEX_DOOR["entrance"],
                              zone=_gw.quad_zone(ALEX_DOOR["zone"]))
    fixtures["alex100-us.eb.bytes"] = {"source_fbg": ALEX_SRC, "kind": "event_with_gateway",
                                       "lang": "us", "gateway": ALEX_DOOR, "sha256": sha(door)}
    if fix_dir.is_dir():
        (fix_dir / "alex100-us.eb.bytes").write_bytes(door)

    #   grgr.bgx: the real GRGR camera (extracted as a borrowable .bgx)
    #   multifloor.bgi.bytes: a real 3-floor walkmesh that round-trips byte-exact (codec + seam tests)
    import tempfile
    tg = Path(tempfile.mkdtemp())
    extract.extract_field(GRGR_SRC, tg, game=game)
    grgr_bgx = (tg / "camera.bgx").read_bytes()
    tm = Path(tempfile.mkdtemp())
    extract.extract_field(MULTIFLOOR_SRC, tm, game=game)
    mf_bgi = (tm / "walkmesh.bgi").read_bytes()
    fixtures["grgr.bgx"] = {"source_fbg": GRGR_SRC, "kind": "camera_bgx", "sha256": sha(grgr_bgx)}
    fixtures["multifloor.bgi.bytes"] = {"source_fbg": MULTIFLOOR_SRC, "kind": "walkmesh_verbatim",
                                        "sha256": sha(mf_bgi)}
    if fix_dir.is_dir():
        (fix_dir / "grgr.bgx").write_bytes(grgr_bgx)
        (fix_dir / "multifloor.bgi.bytes").write_bytes(mf_bgi)
    manifest["fixtures"] = fixtures
    print(f"  fixtures: alex100-us({len(door)}B) grgr.bgx({len(grgr_bgx)}B) "
          f"multifloor.bgi({len(mf_bgi)}B)")

    # 4) build goldens: the hut example's build outputs are DERIVATIVE (embed the blank), so we ship a
    #    hash, not the bytes. The build test compares fresh build output's hash to this.
    manifest["goldens"] = _golden_hashes(game)
    print(f"  goldens (hash-only): {list(manifest['goldens'])}")

    (PROV / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nwrote {PROV/'manifest.json'} + patches")
    return 0


def _golden_hashes(game) -> dict:
    """SHA-256 of the hut example's build outputs (the independent build-golden reference)."""
    import tempfile
    from ..build import FieldProject, build_mod, ModLayout
    example = HERE.parent.parent / "examples" / "vivi-hut" / "hut_int.field.toml"
    out = Path(tempfile.mkdtemp())
    build_mod([FieldProject.load(example)], out, mod_name="GoldenCheck")
    L = ModLayout(out)
    return {"EVT_HUT_INT.eb.bytes/us": sha(L.eb_path("us", "EVT_HUT_INT.eb.bytes").read_bytes())}


if __name__ == "__main__":
    sys.exit(main())
