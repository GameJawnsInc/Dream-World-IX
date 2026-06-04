#!/usr/bin/env python3
"""SPIKE: read FF9 Steam p0data*.bin (UnityRaw 5.2.3 assetbundle) offline.

Proves we can crack a base-game asset archive with NO in-game step, locate a field's background
assets (walkmesh / cameras / atlas) by their container path, and hand raw bytes to the kit's parsers.

    py tools/spike_p0data.py find  <keyword>            # which bundle(s) hold matching asset paths
    py tools/spike_p0data.py inv   <p0dataNN.bin>       # type inventory of one bundle
    py tools/spike_p0data.py grab  <p0dataNN.bin> <path-substr>   # dump matching assets to tools/scroll_out/p0spike/
"""
import sys, os, glob, collections

import UnityPy

GAME = r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\StreamingAssets"
OUT = os.path.join(os.path.dirname(__file__), "scroll_out", "p0spike")


def bundles():
    return sorted(glob.glob(os.path.join(GAME, "p0data*.bin")))


def _raw_bytes(data):
    """Raw bytes of a TextAsset across UnityPy versions."""
    for attr in ("m_Script", "script"):
        v = getattr(data, attr, None)
        if isinstance(v, bytes):
            return v
        if isinstance(v, str):
            return v.encode("utf-8", "surrogateescape")
    return None


def cmd_find(keyword):
    kw = keyword.lower()
    for path in bundles():
        try:
            env = UnityPy.load(path)
            hits = [k for k in env.container if kw in k.lower()]
        except Exception as e:
            print(f"  !! {os.path.basename(path)}: {e}")
            continue
        if hits:
            print(f"{os.path.basename(path):16s} {len(hits):5d} hits  e.g. {hits[0]}")


def cmd_inv(bundle):
    path = bundle if os.path.sep in bundle else os.path.join(GAME, bundle)
    env = UnityPy.load(path)
    by_type = collections.Counter()
    for k, v in env.container.items():
        by_type[v.type.name] += 1
    print(f"{len(env.container)} container entries in {os.path.basename(path)}:")
    for t, c in by_type.most_common():
        ex = next(k for k, v in env.container.items() if v.type.name == t)
        print(f"  {c:6d}  {t:14s}  e.g. {ex}")


def cmd_grab(bundle, substr):
    path = bundle if os.path.sep in bundle else os.path.join(GAME, bundle)
    sub = substr.lower()
    os.makedirs(OUT, exist_ok=True)
    env = UnityPy.load(path)
    n = 0
    for k, v in env.container.items():
        if sub not in k.lower():
            continue
        data = v.read()
        base = k.split("/")[-1]
        if v.type.name == "TextAsset":
            raw = _raw_bytes(data)
            with open(os.path.join(OUT, base), "wb") as f:
                f.write(raw)
            print(f"  TextAsset {base:48s} {len(raw):8d} B")
        elif v.type.name == "Texture2D":
            try:
                img = data.image
                outp = os.path.join(OUT, base if base.endswith(".png") else base + ".png")
                img.save(outp)
                print(f"  Texture2D {base:48s} {img.size}")
            except Exception as e:
                print(f"  Texture2D {base:48s} <decode err {e}>")
        else:
            print(f"  {v.type.name} {base}")
        n += 1
    print(f"grabbed {n} assets -> {OUT}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "find"
    if cmd == "find":
        cmd_find(sys.argv[2])
    elif cmd == "inv":
        cmd_inv(sys.argv[2])
    elif cmd == "grab":
        cmd_grab(sys.argv[2], sys.argv[3])
