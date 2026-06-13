#!/usr/bin/env python3
"""Prove the OFFLINE overlay-art assembler matches Memoria's in-game `[Export] Field=1` dump.

The kit assembles each field's per-overlay background PNGs straight from the atlas in p0data
(`extract._overlay_art` / `scene.bgart`), so a custom field / editable fork / campaign port no
longer needs the multi-minute in-game export. This script is the standing parity proof: for every
field already dumped under `<game>/StreamingAssets/FieldMaps/<FBG>/`, it assembles the overlays
OFFLINE through the production code path and diffs them against the engine's own PNGs.

Two checks per field:
  * BYTE-EXACT: cropping the engine's OWN dumped `atlas.png` (codec-independent) must reproduce each
    `Overlay{i}.png` with diff == 0 -- proves the cell math / flip / dims / placement are exact.
  * OFFLINE: the real p0data path (`_overlay_art`) must match within a small per-channel delta -- the
    only slack is the sub-LSB noise of re-decoding a DXT-compressed atlas (Moguri ships DXT5).

Usage:
    py tools/verify_overlay_export_parity.py [--limit N] [--threshold D] [--field SUBSTR]
Exit code 0 iff every compared overlay is size-exact, byte-exact (where atlas.png exists), and the
offline path is within --threshold (default 16) per channel.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "ff9mapkit"))   # run against the local package


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="only check the first N fields (0 = all)")
    ap.add_argument("--threshold", type=int, default=16, help="max allowed offline per-channel delta")
    ap.add_argument("--field", default=None, help="only fields whose folder contains this substring")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    import numpy as np
    from PIL import Image, ImageChops

    from ff9mapkit import config, extract
    from ff9mapkit.scene import bgs

    ts = extract._active_tilesize(None)
    fmroot = config.find_game_path(None) / "StreamingAssets" / "FieldMaps"
    if not fmroot.is_dir():
        print(f"no FieldMaps dump at {fmroot} -- nothing to verify against")
        return 0
    folders = sorted(d.name for d in fmroot.iterdir()
                     if d.is_dir() and (d / "Overlay0.png").is_file())
    if args.field:
        folders = [f for f in folders if args.field.lower() in f.lower()]
    if args.limit:
        folders = folders[: args.limit]

    print(f"TileSize={ts}  fields to verify={len(folders)}")
    n_fields = n_overlays = 0
    worst_offline = []          # (maxdelta, folder)
    byte_exact_fail = []
    size_mismatch = []
    errors = []
    skipped_unresolved = 0

    for folder in folders:
        fdir = fmroot / folder
        try:
            _, _, roles, env = extract.find_field(folder.lower())
        except Exception:
            skipped_unresolved += 1
            continue
        if "bgs" not in roles:
            skipped_unresolved += 1
            continue
        try:
            bgs_bytes = extract._raw_bytes(env.container[roles["bgs"]].read())
            # BYTE-EXACT: the engine's own atlas.png (codec-independent)
            da = fdir / "atlas.png"
            if da.is_file():
                atlas = Image.open(da).convert("RGBA")
                _, ov = bgs.parse_overlays(bgs_bytes)
                bgs.resolve_sprites(bgs_bytes, ov, atlas.size[0], ts)
                from ff9mapkit.scene import bgart
                for i, got in bgart.assemble_overlays(atlas, ov, ts).items():
                    png = fdir / f"Overlay{i}.png"
                    if not png.is_file():
                        continue
                    ref = Image.open(png).convert("RGBA")
                    if got.size != ref.size:
                        size_mismatch.append(f"{folder}/Overlay{i}: {got.size} != {ref.size}")
                    elif ImageChops.difference(got, ref).getbbox() is not None:
                        byte_exact_fail.append(f"{folder}/Overlay{i}")
            # OFFLINE: the real production path
            res = extract._overlay_art(folder.lower())
            if res is None:
                errors.append((folder, "_overlay_art returned None"))
                continue
            overlays, provider, factor, source, _atlas = res
        except Exception as e:           # noqa: BLE001
            errors.append((folder, repr(e)[:90]))
            continue
        n_fields += 1
        fmax = 0
        for i in range(len(overlays)):
            png = fdir / f"Overlay{i}.png"
            got = provider(i)
            if got is None or not png.is_file():
                continue
            ref = Image.open(png).convert("RGBA")
            n_overlays += 1
            if got.size != ref.size:
                size_mismatch.append(f"{folder}/Overlay{i}: {got.size} != {ref.size} (offline,{source})")
                continue
            d = np.abs(np.asarray(got).astype(int) - np.asarray(ref).astype(int))
            fmax = max(fmax, int(d.max()))
        worst_offline.append((fmax, folder))
        if args.verbose:
            print(f"  {folder}: offline maxdelta={fmax} src={source}")

    worst_offline.sort(reverse=True)
    print(f"\nverified {n_fields} fields, {n_overlays} overlays")
    print(f"  unresolved (skipped): {skipped_unresolved}")
    print(f"  byte-exact (vs engine atlas.png): {'ALL PASS' if not byte_exact_fail else f'{len(byte_exact_fail)} FAIL'}")
    print(f"  offline maxdelta==0: {sum(1 for d,_ in worst_offline if d==0)}/{len(worst_offline)}")
    print(f"  offline maxdelta<=4: {sum(1 for d,_ in worst_offline if d<=4)}/{len(worst_offline)}")
    print(f"  offline maxdelta<={args.threshold}: {sum(1 for d,_ in worst_offline if d<=args.threshold)}/{len(worst_offline)}")
    print("  worst offline fields:", worst_offline[:8])
    ok = True
    if byte_exact_fail:
        ok = False
        print(f"\nBYTE-EXACT FAILURES ({len(byte_exact_fail)}):")
        for s in byte_exact_fail[:25]:
            print("  ", s)
    if size_mismatch:
        ok = False
        print(f"\nSIZE MISMATCHES ({len(size_mismatch)}):")
        for s in size_mismatch[:25]:
            print("  ", s)
    over = [(d, f) for d, f in worst_offline if d > args.threshold]
    if over:
        ok = False
        print(f"\nOFFLINE OVER THRESHOLD ({len(over)}):")
        for d, f in over[:25]:
            print(f"   {f}: maxdelta {d}")
    if errors:
        print(f"\nERRORS ({len(errors)}):")
        for s in errors[:25]:
            print("  ", s)
    print("\nRESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
