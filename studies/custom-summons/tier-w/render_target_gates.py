r"""THE RENDER-TARGET FOLD-IN -- `py render_target_gates.py` prints R1..R6 with PASS/FAIL.

The headless raster's `routes` census (`headless/raster.py routes`, every corpus container run through
the user's own plugin) found that once an effect renders into its DR_AREA target, Memoria hands every
15bpp page at x >= 384 the TARGET, never VRAM -- and that every 15bpp cell on the texel lane's default
edit surface is in such an effect.  The kit now carries the census as a table
(`ff9mapkit/summons/render_target.py`), refuses at build a 15bpp edit no 15bpp read samples, and names
the cells that draw the target.  The table is a CACHE OF A MEASUREMENT, so this runner re-derives it:

R1  THE RE-DERIVATION PIN.  The census on disk (`routes.json` + every container's `summary.json`) is
    re-read and compared with the shipped `_ROUTE_ROWS` / `_TARGET_ROWS` / `_FEED_ROWS` ROW FOR ROW, and
    the census must cover the corpus (372 containers, 0 errors) with the shipped id set and the shipped
    UNPORTED set.
R2  THE CORPUS VERDICT, TWO JOINS.  The kit's per-cell join (`scenery_texel_pages` ->
    `hazards.render_route`) and an independent join computed here straight off `routes.json` must give
    every 15bpp cell the SAME verdict and the same own-feed depths, on the default surface and on the
    surface every acknowledgement widens -- and both must equal the module's pins, including how many
    default-surface remedies name a cell the indexed lane can hand out (the number the docs quote).
R3  THE FALSIFIER.  `routes --control` ran ef429 with `isCreateGenTexture` held down; its 15bpp page
    (448,256) must then read VRAM, on exactly the mesh renders the census saw read the target.  A census
    that could only ever say "the target" would measure nothing.
R4  THE LAW IN THE SOURCE.  The Memoria clone's `SFXMesh.GetTexture` must test the blur key, then the
    ground key, then `isCreateGenTexture`, and only then fall through to VRAM; `SFXRenderTextureEnd`
    must set the flag and `PSXTextureMgr.Reset` clear it; and `SFXData.cs` must still set it inside the
    raw pre-run -- the Speed >= 3 caveat the kit states.
R5  THE CAST RECORD, RETRODICTED.  ef429's own cast spec (`octopus_texel.toml`) refuses, saying no road
    reaches the screen; with the key it rebuilds the EXACT bytes that were cast (the key moves no byte);
    ef446's painted cell is NEVER_VRAM with its own bytes fed at 4 and 8 bpp (the salmon checker), and
    ef251's is NEVER_VRAM fed at 8 and 4 bpp (the bumper strip).
R6  PROVENANCE.  `render_target.py` carries ids, coordinates, depths, frames and counts only -- no bytes
    constant, no hex run.

Reads `C:\gd\SCRATCH\summon-format` and the Memoria source clone ONLY -- no install read, no deploy, no
install write, no commit.
"""
from __future__ import annotations

import ast
import json
import os
import re
import sys
from collections import Counter
from typing import List

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import reskin as RS                                              # noqa: E402,F401  (sets up sys.path)
from ff9mapkit.summons import render_target as RT                # noqa: E402
from ff9mapkit.summons import repaint as RP                      # noqa: E402

_REPO = os.path.normpath(os.path.join(_HERE, "..", "..", ".."))
# THE WORKTREE PIN: a study script that silently imported the MAIN checkout's kit would grade the
# wrong code and pass.  Assert the module under test is THIS tree's.
assert os.path.normcase(os.path.abspath(RT.__file__)).startswith(
    os.path.normcase(os.path.join(_REPO, "ff9mapkit"))), RT.__file__

CORPUS = r"C:\gd\SCRATCH\summon-format"
ROUTES_DIR = os.path.join(CORPUS, "headless", "raster", "routes")
MEMORIA = r"C:\gd\FFIX\Memoria\Assembly-CSharp"
EF429_CAST = os.path.join(CORPUS, "repaint-w6b", "ef429-15bpp", "cast-b", "build_manifest.json")
WIDE = dict(program_depth=True, array_depth=True, displacement_ack=True)
_FAILS: List[str] = []


def chk(name: str, got, want) -> None:
    """Compare a re-measured value against its pin; collect rather than raise, so the board prints."""
    if got != want:
        _FAILS.append("%s: measured %r, pinned %r" % (name, got, want))


def _load(ef: int) -> bytes:
    with open(os.path.join(CORPUS, "ef%03d.bytes" % ef), "rb") as fh:
        return fh.read()


def _census():
    with open(os.path.join(ROUTES_DIR, "routes.json"), encoding="utf-8") as fh:
        return json.load(fh)


def _summary(ef: int) -> dict:
    with open(os.path.join(ROUTES_DIR, "ef%03d" % ef, "summary.json"), encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------------- R1
def r1_rederive() -> None:
    doc = _census()
    rows = doc["rows"]
    errors = sorted(e for e, r in rows.items() if "error" in r)
    route, target, feed, unported = [], [], [], set()
    for e, r in sorted(rows.items()):
        ef = int(e[2:])
        for k, (n, f0, f1) in sorted(r.get("routes", {}).items()):
            page, kind = k.split("/")
            m = re.match(r"x(\d+)_y(\d+)@15$", page)
            if m:
                route.append((ef, int(m.group(1)), int(m.group(2)), kind, n, f0, f1))
        s = _summary(ef)
        if s.get("unported_special"):
            unported.add(ef)
        if r.get("dr_area"):
            target.append((ef, r["dr_area_first_frame"]))
            for c, v in sorted((s.get("render_target_cells") or {}).items()):
                m = re.match(r"x(\d+)_y(\d+)@(\d+)$", c)
                feed.append((ef, int(m.group(1)), int(m.group(2)), int(m.group(3)), v["pixels"],
                             v["n_frames"]))
    print("   census: %d containers, %d errors; %d 15bpp route rows, %d targets, %d feeder rows"
          % (doc["containers"], len(errors), len(route), len(target), len(feed)))
    chk("R1 the census covers the corpus with no error", (doc["containers"], errors), (372, []))
    chk("R1 the census ids are the shipped ids", {int(e[2:]) for e in rows}, set(RT.CENSUS_IDS))
    chk("R1 the route rows, ROW FOR ROW", tuple(route), RT._ROUTE_ROWS)
    chk("R1 the target rows, ROW FOR ROW", tuple(target), RT._TARGET_ROWS)
    chk("R1 the feeder rows, ROW FOR ROW", tuple(feed), RT._FEED_ROWS)
    chk("R1 the unported set", unported, set(RT.UNPORTED))


# --------------------------------------------------------------------------- R2
def _independent(ef: int, cell, rows) -> tuple:
    """The verdict computed HERE, off the census file, never through `render_target`."""
    if ef in RT.UNPORTED:
        return "UNPORTED", ()
    kinds = set()
    for k in rows["ef%03d" % ef].get("routes", {}):
        page, kind = k.split("/")
        m = re.match(r"x(\d+)_y(\d+)@15$", page)
        if m and int(m.group(1)) <= cell[0] < int(m.group(1)) + 256 and \
                int(m.group(2)) == cell[1] // 256 * 256:
            kinds.add(kind)
    v = ("UNREAD" if not kinds else "READS_VRAM" if kinds == {"IMAGE"} else
         "MIXED" if "IMAGE" in kinds else "NEVER_VRAM")
    if v != "NEVER_VRAM":
        return v, ()
    own = tuple(sorted(int(c.split("@")[1]) for c in (_summary(ef).get("render_target_cells") or {})
                       if c.split("@")[0] == "x%d_y%d" % tuple(cell)))
    return v, own


def r2_two_joins() -> None:
    rows = _census()["rows"]
    for tag, kw, pins in (
            ("default", {}, (RT.SURFACE_15BPP, RT.SURFACE_15BPP_CONTAINERS, RT.SURFACE_15BPP_OWN_FEED,
                             RT.SURFACE_15BPP_VERDICTS)),
            ("wide", WIDE, (RT.WIDE_15BPP, RT.WIDE_15BPP_CONTAINERS, RT.WIDE_15BPP_OWN_FEED,
                            RT.WIDE_15BPP_VERDICTS))):
        kit, ind, efs, paintable = {}, {}, set(), 0
        for ef in sorted(RT.CENSUS_IDS):
            if not os.path.isfile(os.path.join(CORPUS, "ef%03d.bytes" % ef)):
                continue
            try:
                pages = RP.scenery_texel_pages(_load(ef), ef, **kw)
            except Exception:                                    # a refused derivation has no surface
                continue
            for p in pages:
                if p.bpp != 15:
                    continue
                efs.add(ef)
                rt = p.hazards.render_route
                kit[(ef, p.name)] = (rt.verdict, tuple(sorted(f.bpp for f in rt.own_feeds)))
                paintable += "in the indexed lane" in p.hazards.render_remedy
                ind[(ef, p.name)] = _independent(ef, p.cell, rows)
        verdicts = dict(Counter(v for v, _o in kit.values()))
        own = sum(1 for _v, o in kit.values() if o)
        print("   %-7s surface: %d 15bpp cells over %d containers, %s, %d fed by their own bytes"
              % (tag, len(kit), len(efs), verdicts, own))
        chk("R2 %s: the kit's join == the independent join, cell for cell" % tag, kit, ind)
        chk("R2 %s: the pins" % tag, (len(kit), len(efs), own, verdicts), pins)
        if tag == "default":
            print("   default surface: %d of %d remedies name a cell the indexed lane hands out"
                  % (paintable, len(kit)))
            chk("R2 default: the remedies that name a paintable cell", paintable,
                RT.SURFACE_15BPP_PAINTABLE_REMEDY)


# --------------------------------------------------------------------------- R3
def r3_falsifier() -> None:
    path = os.path.join(ROUTES_DIR, "control.json")
    if not os.path.isfile(path):
        _FAILS.append("R3: no control at %s -- run `headless/raster.py routes --control`" % path)
        return
    with open(path, encoding="utf-8") as fh:
        ctl = json.load(fh)
    page = "x448_y256@15"
    census = [r for r in RT.routes(429) if r.page == (448, 256)]
    print("   ef429 %s, target suppressed: %s; in the census: %s"
          % (page, {k: v for k, v in ctl["routes"].items() if k.startswith(page)},
             [r.describe() for r in census]))
    chk("R3 the control held the flag down", (ctl["effect"], ctl["target_suppressed"],
                                              ctl["gen_texture_used"]), (429, True, False))
    chk("R3 THE FALSIFIER fired: the page reads VRAM", ctl["kinds"], ["IMAGE"])
    chk("R3 ...on exactly the reads the census saw go to the target",
        ctl["routes"].get(page + "/IMAGE"), [census[0].renders, census[0].frames[0], census[0].frames[1]]
        if census and census[0].kind == "GENERATED" else None)


# --------------------------------------------------------------------------- R4
def _src(rel: str) -> str:
    with open(os.path.join(MEMORIA, rel), encoding="utf-8-sig") as fh:
        return fh.read()


def r4_source() -> None:
    if not os.path.isdir(MEMORIA):
        _FAILS.append("R4: no Memoria source clone at %s" % MEMORIA)
        return
    mesh = _src(os.path.join("Global", "SFXMesh", "SFXMesh.cs"))
    body = mesh[mesh.index("if (SFXKey.GetTextureMode(_key) != 2u)"):]
    body = body[:body.index("public UInt32 GetKey()")]
    order = [body.find(s) for s in ("SFXKey.IsBlurTexture(textureKey)", "== PSXTextureMgr.bgKey",
                                     "if (PSXTextureMgr.isCreateGenTexture)", "Kind.GENERATED")]
    tail = body[order[-1]:]
    print("   GetTexture: blur @%d, ground @%d, target flag @%d, GENERATED @%d, then %s"
          % tuple(order + ["VRAM" if "PSXTextureMgr.GetTexture(_key)" in tail else "?"]))
    chk("R4 the order: blur, ground, target, then VRAM",
        (all(o >= 0 for o in order) and order == sorted(order), "PSXTextureMgr.GetTexture(_key)" in tail),
        (True, True))
    key = _src(os.path.join("Global", "SFXKey.cs"))
    blur = key[key.index("public static Boolean IsBlurTexture(UInt32 key)"):]
    chk("R4 the blur key is a page left of x 384 (tx < 6)",
        "return (key >> 16 & 0xFu) < 6u;" in blur[:blur.index("}")], True)
    end = _src(os.path.join("Global", "SFXRender", "Texture", "SFXRenderTextureEnd.cs"))
    mgr = _src(os.path.join("Global", "PSXTexture", "PSXTextureMgr.cs"))
    reset = mgr[mgr.index("public static void Reset()"):]
    reset = reset[:reset.index("}")]
    data = _src(os.path.join("Memoria", "Battle", "SFX", "SFXData.cs"))
    raw = data[data.index("public Boolean LoadSFXRawLoop()"):data.index("public void LoadSFXRawEnd()")]
    chk("R4 SFXRenderTextureEnd sets the flag", "PSXTextureMgr.isCreateGenTexture = true;" in end, True)
    chk("R4 PSXTextureMgr.Reset clears it", "PSXTextureMgr.isCreateGenTexture = false;" in reset, True)
    chk("R4 the raw pre-run sets it every frame (the Speed >= 3 caveat)",
        "PSXTextureMgr.isCreateGenTexture = true;" in raw, True)


# --------------------------------------------------------------------------- R5
def r5_casts() -> None:
    spec_path = os.path.join(_HERE, "octopus_texel.toml")
    blob = _load(429)
    spec = RP.load_spec(spec_path)
    try:
        RP.build(spec, spec_path, blob=blob)
        fired, msg = False, ""
    except RP.RepaintError as e:
        fired, msg = True, str(e)
    chk("R5 ef429's cast spec refuses, saying no road reaches the screen",
        (fired, msg.startswith("RENDER TARGET, cell.s0.x448_y256:"), "no measured road" in msg),
        (True, True, True))
    for row in spec["reskin"]["texel"]:
        row[RT.ACK_KEY] = True
    sha = RP.build(spec, spec_path, blob=blob).sha_out
    want = None
    if os.path.isfile(EF429_CAST):
        with open(EF429_CAST, encoding="utf-8") as fh:
            want = json.load(fh)["patched_sha256"]
    print("   ef429 with the key: %s; the cast's own manifest: %s" % (sha[:16], (want or "?")[:16]))
    chk("R5 ...and with the key rebuilds the exact cast bytes", sha, want)
    for ef, cell, own, what in ((429, (448, 256), (), "never showed"),
                                (446, (448, 256), (4, 8), "the salmon checker"),
                                (251, (512, 256), (4, 8), "the bumper strip")):
        rt = RT.cell_route(ef, cell)
        got = (rt.verdict, tuple(sorted(f.bpp for f in rt.own_feeds)))
        print("   ef%03d x%d_y%d (%s): %s, own bytes fed at %s"
              % (ef, cell[0], cell[1], what, got[0], "/".join(map(str, got[1])) or "no depth"))
        chk("R5 ef%03d retrodicts %s" % (ef, what), got, ("NEVER_VRAM", own))


# --------------------------------------------------------------------------- R6
def r6_provenance() -> None:
    path = RT.__file__
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    tree = ast.parse(src)
    blobs = [n for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, bytes)]
    ints = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant)
            and isinstance(n.value, int) and not isinstance(n.value, bool)]
    hexrun = re.findall(r"(?:\\x[0-9a-fA-F]{2}){4,}|\b[0-9a-fA-F]{16,}\b", src)
    print("   %s: %d bytes constant(s), %d int literal(s) (max %d), %d hex run(s)"
          % (os.path.basename(path), len(blobs), len(ints), max(ints), len(hexrun)))
    chk("R6 no bytes constant", len(blobs), 0)
    chk("R6 no hex run", hexrun, [])
    chk("R6 every integer is an id, a coordinate, a frame or a fragment count", max(ints) <= 10 ** 7, True)


GATES = [
    ("R1", "THE RE-DERIVATION PIN -- the census re-read, row for row", r1_rederive),
    ("R2", "THE CORPUS VERDICT -- the kit's join == an independent one, == the pins", r2_two_joins),
    ("R3", "THE FALSIFIER -- ef429 with its target held down reads VRAM", r3_falsifier),
    ("R4", "THE LAW IN THE SOURCE -- GetTexture's order, the flag's set and clear", r4_source),
    ("R5", "THE CAST RECORD, RETRODICTED -- and the key moves no byte", r5_casts),
    ("R6", "PROVENANCE -- ids, coordinates and counts, never a stock byte", r6_provenance),
]


def main(argv=None) -> int:
    only = set(a.upper() for a in (argv or sys.argv[1:]) if a.upper().startswith("R"))
    print("RENDER-TARGET GATES -- the routes census folded into the texel lane, the table re-derived")
    print("corpus: %s" % CORPUS)
    print("=" * 72)
    board = []
    for tag, title, fn in GATES:
        if only and tag not in only:
            continue
        before = len(_FAILS)
        print("%s  %s" % (tag, title))
        try:
            fn()
            ok = len(_FAILS) == before
        except Exception as exc:                                   # a crashed gate is a red gate
            _FAILS.append("%s raised %s: %s" % (tag, type(exc).__name__, exc))
            ok = False
        board.append((tag, title, ok))
        print("   [%s] %s\n" % ("PASS" if ok else "FAIL", tag))
    print("=" * 72)
    for tag, title, ok in board:
        print("%-4s %s %s" % ("PASS" if ok else "FAIL", tag, title))
    if _FAILS:
        print("-" * 72)
        for f in _FAILS:
            print("  FAIL  %s" % f)
    print("=" * 72)
    print("%d/%d gates pass" % (sum(1 for _, _, ok in board if ok), len(board)))
    return 1 if _FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
