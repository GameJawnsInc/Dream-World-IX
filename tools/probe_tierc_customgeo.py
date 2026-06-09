"""TEMP Tier-c probe (step C2): a WHOLLY ORIGINAL battle -- new SCENE + new BBG NUMBER + custom geometry.

Builds on C1 (probe_tierc_scene.py, proven). Where C1 minted a scene on the donor's OWN map (BBG_B013) to
isolate the scene-mint variable, C2 proves the last unknown: a BRAND-NEW bbg NUMBER (BBG_B200, >177) with
our OWN geometry renders for a minted scene on stock Memoria -- i.e. nothing reuses a real battle-map slot.

  * Geometry = BBG_B013's mesh forked to a loose FBX (the proven tier-b path) placed under BBG_B200, with
    its textures TINTED BLUE so the proof is UNAMBIGUOUS: if you fight on a blue Evil Forest, the engine
    loaded OUR BBG_B200 from disc (not a fallback to the real B013). Reshaping the mesh is the same loose-
    FBX code path -- this isolates "does a new bbg NUMBER work" from "does a reshaped mesh work" (tier b).
  * INB_B200 = B013's .inb (already fully static: texanim=0, objanim=0) with bbgnumber:=200. Static dodges
    the hardcoded per-id object/uv-anim tables; `nf_BbgNumber` is only ever compared `== <specific id>`,
    never used as an array index, so 200 hits no bound (verified in battlebg.cs).
  * Scene 5501 (TIERC_GEO) = forked donor EF_R007 raw16/raw17/eb/mes (same as C1), MapModel -> BBG_B200.
  * Trigger: field 5000's encounter repointed to 5501 (derived from C1's clean .tierc_orig backup).

Reversible (_tierc_geo_revert.py). RELAUNCH FF9 (new BattleScene line), warp to 5000, walk. Delete once
the full mint (scene + bbg + geometry) is wired into ff9mapkit (C4).
"""
from __future__ import annotations

import shutil
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))   # tools/ -> import the C1 probe's helpers
from probe_tierc_scene import grab, _lang_of, GAME, SA, MOD, RES, LANGS, ROOT  # noqa: E402

from PIL import Image                                        # noqa: E402
import UnityPy                                               # noqa: E402
from ff9mapkit.battle import extract as bx, fbx as bfbx      # noqa: E402
from ff9mapkit.eb import opcodes                             # noqa: E402

# ---- config -----------------------------------------------------------------------------------------
DONOR_EB = "EVT_BATTLE_EF_R007"
DONOR_SCENE = 67
SRC_BBG = "BBG_B013"          # geometry + textures + INB donor (Evil Forest)
NEW_BBG = "BBG_B200"          # a brand-new bbg NUMBER (>177) -- the thing C2 proves
NEW_ID = 5501
NEW_NAME = "TIERC_GEO"
NEW_EB = f"EVT_BATTLE_{NEW_NAME}"
FIELD_NAME = "TEST5000"


def _tint(path: Path) -> None:
    """Blue-tint a texture in place (RGBA, alpha preserved) so BBG_B200 is visibly OURS, not stock B013."""
    im = Image.open(path).convert("RGBA")
    r, g, b, a = im.split()
    r = r.point(lambda v: int(v * 0.40))
    g = g.point(lambda v: int(v * 0.55))
    b = b.point(lambda v: min(255, int(v * 1.30) + 40))
    Image.merge("RGBA", (r, g, b, a)).save(path)


def build_bbg() -> None:
    """Fork SRC_BBG geometry+textures -> loose FBX under NEW_BBG (tinted) + a static INB_B200."""
    bbg_dir = RES / "BattleMap" / "BattleModel" / "battleMap_all" / NEW_BBG
    bbg_dir.mkdir(parents=True, exist_ok=True)
    groups, env, _ = bx.read_bbg(SRC_BBG, GAME)
    text, ngeo = bfbx.emit_fbx(groups)
    (bbg_dir / f"{NEW_BBG}.fbx").write_text(text, encoding="ascii", newline="\n")
    saved = bx._save_textures(env, SRC_BBG, bbg_dir, bfbx.textures_used(groups))
    for nm in saved:
        _tint(bbg_dir / f"{nm}.png")
    print(f"[geo] {NEW_BBG}.fbx ({ngeo} geo / {len(groups)} groups) + {len(saved)} tinted textures")

    # INB_B200 = B013's static .inb with bbgnumber := 200
    inb = grab(env, {"inb": f"battleinfo/{SRC_BBG.lower().replace('bbg_', 'inb_')}.inb.bytes"}).get("inb")
    if not inb or len(inb) < 16:
        raise SystemExit("INB_B013 not found")
    f = list(struct.unpack_from("<6h4B", inb, 0))
    f[0] = 200                       # bbgnumber
    f[1] = 0; f[4] = 0; f[5] = 0     # texanim, objanim, uvcount -> static (B013 already is)
    new_inb = struct.pack("<6h4B", *f)
    inb_dir = RES / "BattleMap" / "BattleInfo"
    inb_dir.mkdir(parents=True, exist_ok=True)
    (inb_dir / f"INB_B200.inb.bytes").write_bytes(new_inb)
    print(f"[geo] INB_B200.inb (bbgnumber=200, static): {new_inb.hex()}")


def mint_scene() -> None:
    """Fork donor raw16/raw17/eb/mes -> scene NEW_ID/NEW_NAME (same as C1, new id/name)."""
    env2 = UnityPy.load(str(SA / "p0data2.bin"))
    g2 = grab(env2, {"raw16": f"battlescene/{DONOR_EB.lower()}/dbfile0000.raw16.bytes",
                     "raw17": f"battlescene/{DONOR_EB.lower()}/{DONOR_SCENE}.raw17.bytes"})
    raw16, raw17 = g2.get("raw16"), g2.get("raw17")
    env7 = UnityPy.load(str(SA / "p0data7.bin"))
    ebs = grab(env7, {lang: f"eventbinary/battle/{lang}/{DONOR_EB.lower()}.eb.bytes" for lang in LANGS})
    if not raw16 or not raw17 or any(l not in ebs for l in LANGS):
        raise SystemExit("donor scene assets incomplete")
    scene_dir = RES / "BattleMap" / "BattleScene" / NEW_EB
    scene_dir.mkdir(parents=True, exist_ok=True)
    (scene_dir / "dbfile0000.raw16.bytes").write_bytes(raw16)
    (scene_dir / f"{NEW_ID}.raw17.bytes").write_bytes(raw17)
    for lang in LANGS:
        d = RES / "CommonAsset" / "EventEngine" / "EventBinary" / "Battle" / lang
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{NEW_EB}.eb.bytes").write_bytes(ebs[lang])
    print(f"[scene] minted {NEW_EB} (raw16/raw17 + eb x{len(LANGS)})")

    # battle text (load-bearing -- see C1)
    ra = GAME / "x64" / "FF9_Data" / "resources.assets"
    env_ra = UnityPy.load(str(ra))
    by, eng = {}, None
    for o in env_ra.objects:
        if o.type.name != "TextAsset":
            continue
        d = o.read()
        if d.m_Name != f"{DONOR_SCENE}.mes":
            continue
        from ff9mapkit.extract import _raw_bytes
        raw = _raw_bytes(d)
        lang = _lang_of(raw.decode("utf-8", "replace"))
        if lang == "en":
            eng = raw
        elif lang:
            by[lang] = raw
    src = {"us": eng, "uk": eng, "fr": by.get("fr"), "gr": by.get("gr"),
           "it": by.get("it"), "es": by.get("es"), "jp": by.get("jp")}
    for lang in LANGS:
        raw = src.get(lang) or eng or next(iter(by.values()))
        d = MOD / "FF9_Data" / "embeddedasset" / "text" / lang / "battle"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{NEW_ID}.mes").write_bytes(raw)
    print(f"[scene] forked battle text {DONOR_SCENE}.mes -> {NEW_ID}.mes x{len(LANGS)}")


def wire() -> None:
    # DictionaryPatch: add our BattleScene line idempotently (preserve C1's 5500 line + everything else)
    dp = MOD / "DictionaryPatch.txt"
    keep = [ln for ln in dp.read_text(encoding="utf-8").splitlines()
            if ln.strip() and f"{NEW_ID} {NEW_NAME}" not in ln]
    keep.append(f"BattleScene {NEW_ID} {NEW_NAME} {NEW_BBG}")
    dp.write_text("\n".join(keep) + "\n", encoding="utf-8")
    print(f"[wire] DictionaryPatch += BattleScene {NEW_ID} {NEW_NAME} {NEW_BBG}")

    # repoint field 5000's encounter -> NEW_ID, derived from C1's clean .tierc_orig (the stock 67 eb)
    old = opcodes.set_random_battles(1, DONOR_SCENE, DONOR_SCENE, DONOR_SCENE, DONOR_SCENE)
    new = opcodes.set_random_battles(1, NEW_ID, NEW_ID, NEW_ID, NEW_ID)
    n = 0
    for lang in LANGS:
        eb_path = (RES / "CommonAsset" / "EventEngine" / "EventBinary" / "Field"
                   / lang / f"EVT_{FIELD_NAME}.eb.bytes")
        if not eb_path.exists():
            continue
        orig = eb_path.with_suffix(".bytes.tierc_orig")
        if not orig.exists():
            shutil.copy(eb_path, orig)
        eb = orig.read_bytes()
        if eb.count(old) != 1:
            raise SystemExit(f"{lang}: clean .tierc_orig must contain exactly 1 SetRandomBattles(1,67x4)")
        eb_path.write_bytes(eb.replace(old, new))
        n += 1
    print(f"[wire] field {FIELD_NAME} encounter -> {NEW_ID} x{n} (C1's 5500 scene stays registered, untriggered)")


def write_revert() -> None:
    bbg_dir = RES / "BattleMap" / "BattleModel" / "battleMap_all" / NEW_BBG
    scene_dir = RES / "BattleMap" / "BattleScene" / NEW_EB
    (ROOT / "tools" / "_tierc_geo_revert.py").write_text(
        '"""AUTO-GENERATED by probe_tierc_customgeo.py -- undo the C2 probe."""\n'
        "import shutil\nfrom pathlib import Path\n\n"
        f"MOD = Path(r{str(MOD)!r})\nRES = Path(r{str(RES)!r})\n"
        f"BBG_DIR = Path(r{str(bbg_dir)!r})\nSCENE_DIR = Path(r{str(scene_dir)!r})\n"
        f"INB = RES/'BattleMap'/'BattleInfo'/'INB_B200.inb.bytes'\n"
        f"LANGS = {LANGS!r}\nNEW_EB = {NEW_EB!r}\nNEW_ID = {NEW_ID}\nFIELD_NAME = {FIELD_NAME!r}\nNEW_NAME = {NEW_NAME!r}\n\n"
        "dp = MOD/'DictionaryPatch.txt'\n"
        "lines=[l for l in dp.read_text(encoding='utf-8').splitlines() if l.strip() and f'{NEW_ID} {NEW_NAME}' not in l]\n"
        "dp.write_text(chr(10).join(lines)+chr(10), encoding='utf-8'); print('removed BattleScene', NEW_ID)\n"
        "for lang in LANGS:\n"
        "    eb = RES/'CommonAsset'/'EventEngine'/'EventBinary'/'Field'/lang/f'EVT_{FIELD_NAME}.eb.bytes'\n"
        "    orig = eb.with_suffix('.bytes.tierc_orig')\n"
        "    if orig.exists(): shutil.copy(orig, eb)  # restore stock-67 encounter (also undoes C1's repoint)\n"
        "    bd = RES/'CommonAsset'/'EventEngine'/'EventBinary'/'Battle'/lang/f'{NEW_EB}.eb.bytes'\n"
        "    if bd.exists(): bd.unlink()\n"
        "    mes = MOD/'FF9_Data'/'embeddedasset'/'text'/lang/'battle'/f'{NEW_ID}.mes'\n"
        "    if mes.exists(): mes.unlink()\n"
        "for p in (SCENE_DIR, BBG_DIR):\n"
        "    if p.exists(): shutil.rmtree(p)\n"
        "if INB.exists(): INB.unlink()\n"
        "print('C2 reverted. Relaunch FF9. (Run _tierc_revert.py too to remove C1 scene 5500.)')\n",
        encoding="utf-8")
    print("[wire] wrote tools/_tierc_geo_revert.py")


def main() -> int:
    print(f"[tierc-geo] mod={MOD}")
    build_bbg()
    mint_scene()
    wire()
    write_revert()
    print(f"\n[tierc-geo] DONE. RELAUNCH FF9, F6 -> Warp 5000, walk. PASS = a BLUE Evil Forest battle"
          f" (= BBG_B200 + scene {NEW_ID} loaded from our files). revert: py tools/_tierc_geo_revert.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
