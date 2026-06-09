"""TEMP Tier-c probe (step C1): MINT A BRAND-NEW BATTLE SCENE on stock Memoria.

Forks donor EF_R007 (scene 67, Evil Forest random battle) -- its raw16 (gameplay), raw17 (btlseq +
camera), and battle .eb (AI/events, all 7 langs) -- verbatim into a NET-NEW scene id (5500, name
TIERC_TEST) pointing at the proven BBG_B013 map, and wires a field-5000 encounter at it.

Proves the open-frontier claim: a brand-new BattleScene id (with its own gameplay + sequence + camera,
none of which the engine has ever seen at that id) LOADS and is FIGHTABLE without an engine rebuild.
  * Camera = the donor's working raw17 -> NO camera authoring needed (the managed SFX_DATA_CAMERA path
    is a TODO no-op; we ride the native plugin on the donor's data).
  * bbg = BBG_B013 itself (donor's own map) -> isolates the SCENE-MINT variable from custom geometry
    (tier b, already proven). C2 will swap in custom geometry.
  * .mes (battle text) is DEFERRED -> enemy names render blank; the fight still runs. Added in C2.

Reversible + idempotent: clean originals are saved as *.tierc_orig and every run re-derives from them.
Writes tools/_tierc_revert.py to undo. Relaunch FF9 (new DictionaryPatch line), warp to 5000, walk
until the encounter fires. Delete this probe once the path is wired into ff9mapkit.
"""
from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # worktree root
KIT = ROOT / "ff9mapkit"
sys.path.insert(0, str(KIT))                            # use THIS worktree's package

import UnityPy                                          # noqa: E402
from ff9mapkit import config                            # noqa: E402
from ff9mapkit.eb import opcodes                         # noqa: E402
from ff9mapkit.extract import _raw_bytes                # noqa: E402

# ---- config -----------------------------------------------------------------------------------------
DONOR_EB = "EVT_BATTLE_EF_R007"   # scene 67, Evil Forest random battle
DONOR_SCENE = 67
BBG = "BBG_B013"                  # donor's own map (proven tiers a/b); no geometry override here
NEW_ID = 5500
NEW_NAME = "TIERC_TEST"
NEW_EB = f"EVT_BATTLE_{NEW_NAME}"
FIELD_NAME = "TEST5000"           # the existing field-5000 slot in this worktree
LANGS = config.LANGS
TS = time.strftime("%Y%m%d-%H%M%S")


def _mod_folder() -> str:
    for line in (ROOT / ".ff9deploy.toml").read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line.startswith("mod_folder"):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("no mod_folder in .ff9deploy.toml")


GAME = config.find_game_path(None)
SA = GAME / "StreamingAssets"
MOD = GAME / _mod_folder()
RES = MOD / "StreamingAssets" / "Assets" / "Resources"
BAK = ROOT / "backups"


def _lang_of(text: str) -> str | None:
    """Classify a battle-text variant by language signature (the 7 langs share entry COUNT/order, so
    indices are language-independent -- only the displayed strings differ)."""
    if any("぀" <= c <= "ヿ" or "一" <= c <= "鿿" for c in text):
        return "jp"
    if "Coltellata" in text or "Niente" in text:
        return "it"
    if "Gobelin" in text or "Gobelipunch" in text:
        return "fr"
    if "Duende" in text:
        return "es"
    if "Isegrim" in text or "Nichts" in text:
        return "gr"
    if "Goblin" in text and "Fang" in text:
        return "en"
    return None


def fork_battle_text() -> int:
    """Fork donor <DONOR_SCENE>.mes (battle text, all langs) from resources.assets -> <NEW_ID>.mes in
    the mod folder. The donor's raw16 is forked verbatim (same enemies), so the same text indices apply.
    GetBattleText(<NEW_ID>) returning non-null is REQUIRED -- ApplyBattlePatch NREs on a null otherwise."""
    ra = GAME / "x64" / "FF9_Data" / "resources.assets"
    if not ra.exists():
        ra = GAME / "FF9_Data" / "resources.assets"
    env = UnityPy.load(str(ra))
    by: dict[str, bytes] = {}
    eng: bytes | None = None
    for o in env.objects:
        if o.type.name != "TextAsset":
            continue
        d = o.read()
        if d.m_Name != f"{DONOR_SCENE}.mes":
            continue
        raw = _raw_bytes(d)
        lang = _lang_of(raw.decode("utf-8", "replace"))
        if lang == "en":
            eng = raw
        elif lang:
            by[lang] = raw
    if eng is None and not by:
        raise SystemExit(f"donor {DONOR_SCENE}.mes not found in resources.assets")
    src = {"us": eng, "uk": eng, "fr": by.get("fr"), "gr": by.get("gr"),
           "it": by.get("it"), "es": by.get("es"), "jp": by.get("jp")}
    written = 0
    for lang in LANGS:
        raw = src.get(lang) or eng or next(iter(by.values()))
        d = MOD / "FF9_Data" / "embeddedasset" / "text" / lang / "battle"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{NEW_ID}.mes").write_bytes(raw)
        written += 1
    print(f"[tierc] forked battle text {DONOR_SCENE}.mes -> {NEW_ID}.mes x{written} langs "
          f"(en + {sorted(by)})")
    return written


def grab(env, suffixes: dict[str, str]) -> dict[str, bytes]:
    """{key: bytes} for the TextAsset whose container ends with suffixes[key] (case-insensitive)."""
    want = {k: v.lower() for k, v in suffixes.items()}
    out: dict[str, bytes] = {}
    for o in env.objects:
        if o.type.name != "TextAsset":
            continue
        c = (getattr(o, "container", None) or "").lower()
        for k, suf in want.items():
            if k not in out and c.endswith(suf):
                out[k] = _raw_bytes(o.read())
    return out


def main() -> int:
    print(f"[tierc] game={GAME}\n[tierc] mod ={MOD}")

    # 1) extract donor scene assets ----------------------------------------------------------------
    print(f"[tierc] reading donor {DONOR_EB} (scene {DONOR_SCENE}) from p0data2/p0data7 ...")
    env2 = UnityPy.load(str(SA / "p0data2.bin"))
    g2 = grab(env2, {
        "raw16": f"battlescene/{DONOR_EB.lower()}/dbfile0000.raw16.bytes",
        "raw17": f"battlescene/{DONOR_EB.lower()}/{DONOR_SCENE}.raw17.bytes",
    })
    raw16, raw17 = g2.get("raw16"), g2.get("raw17")
    if not raw16 or not raw17:
        raise SystemExit(f"donor raw16/raw17 not found ({list(g2)})")

    env7 = UnityPy.load(str(SA / "p0data7.bin"))
    eb_suf = {lang: f"eventbinary/battle/{lang}/{DONOR_EB.lower()}.eb.bytes" for lang in LANGS}
    ebs = grab(env7, eb_suf)
    missing = [l for l in LANGS if l not in ebs]
    if missing:
        raise SystemExit(f"donor battle eb missing for langs: {missing}")
    print(f"[tierc]   raw16={len(raw16)}B  raw17={len(raw17)}B  eb x{len(ebs)} langs "
          f"({min(len(b) for b in ebs.values())}..{max(len(b) for b in ebs.values())}B)")

    # 2) write the minted scene assets into the mod folder -----------------------------------------
    scene_dir = RES / "BattleMap" / "BattleScene" / NEW_EB
    scene_dir.mkdir(parents=True, exist_ok=True)
    (scene_dir / "dbfile0000.raw16.bytes").write_bytes(raw16)
    (scene_dir / f"{NEW_ID}.raw17.bytes").write_bytes(raw17)
    for lang in LANGS:
        d = RES / "CommonAsset" / "EventEngine" / "EventBinary" / "Battle" / lang
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{NEW_EB}.eb.bytes").write_bytes(ebs[lang])
    print(f"[tierc] wrote scene assets -> {scene_dir.relative_to(MOD)} (+ battle eb x{len(LANGS)})")

    # 2b) fork the battle TEXT (.mes) -- load-bearing: a missing 5500.mes -> GetBattleText null ->
    #     ApplyBattlePatch NRE -> no enemies/party. (DataPatchers.cs:66; found via Memoria.log.)
    fork_battle_text()

    # 3) DictionaryPatch: register the new BattleScene ---------------------------------------------
    dp = MOD / "DictionaryPatch.txt"
    dp_orig = dp.with_suffix(".txt.tierc_orig")
    if not dp_orig.exists():
        shutil.copy(dp, dp_orig)
        shutil.copy(dp, BAK / f"DictionaryPatch.txt.{TS}")   # durable convention backup
    line = f"BattleScene {NEW_ID} {NEW_NAME} {BBG}"
    text = dp_orig.read_text(encoding="utf-8").rstrip("\n")
    dp.write_text(text + "\n" + line + "\n", encoding="utf-8")
    print(f"[tierc] DictionaryPatch += {line!r}")

    # 4) field 5000 eb: REPOINT its existing encounter from the donor scene to the new id (all langs).
    #    TEST5000 already fires SetRandomBattles(1, 67,67,67,67) + freq + a tag-10 reinit (the tier-a/b
    #    setup), so we don't add an entry -- we swap the 4 scene operands 67 -> 5500 (length-preserving,
    #    no offset shift) so the SAME encounter now triggers our minted scene.
    old = opcodes.set_random_battles(1, DONOR_SCENE, DONOR_SCENE, DONOR_SCENE, DONOR_SCENE)
    new = opcodes.set_random_battles(1, NEW_ID, NEW_ID, NEW_ID, NEW_ID)
    assert len(old) == len(new), "scene operands must be equal width"
    patched = 0
    for lang in LANGS:
        eb_path = (RES / "CommonAsset" / "EventEngine" / "EventBinary" / "Field"
                   / lang / f"EVT_{FIELD_NAME}.eb.bytes")
        if not eb_path.exists():
            print(f"[tierc]   WARN field eb missing: {lang}")
            continue
        orig = eb_path.with_suffix(".bytes.tierc_orig")
        if not orig.exists():
            shutil.copy(eb_path, orig)
        eb = orig.read_bytes()                                 # always start from a clean original
        n = eb.count(old)
        if n != 1:
            raise SystemExit(f"{lang}: expected exactly 1 SetRandomBattles(1,{DONOR_SCENE}x4); found {n}")
        eb_path.write_bytes(eb.replace(old, new))
        patched += 1
    print(f"[tierc] field {FIELD_NAME} eb repointed: encounter scene {DONOR_SCENE} -> {NEW_ID} x{patched}")

    # 5) emit the revert script --------------------------------------------------------------------
    _write_revert(scene_dir)
    print("\n[tierc] DONE. RELAUNCH FF9 (new DictionaryPatch line), F6 -> Warp 5000, walk until battle.")
    print("[tierc] revert: py tools/_tierc_revert.py")
    return 0


def _write_revert(scene_dir: Path) -> None:
    revert = ROOT / "tools" / "_tierc_revert.py"
    revert.write_text(
        '"""AUTO-GENERATED by probe_tierc_scene.py -- undo the Tier-c C1 probe."""\n'
        "import shutil\nfrom pathlib import Path\n\n"
        f"MOD = Path(r{str(MOD)!r})\n"
        f"RES = Path(r{str(RES)!r})\n"
        f"SCENE_DIR = Path(r{str(scene_dir)!r})\n"
        f"LANGS = {LANGS!r}\n"
        f"NEW_EB = {NEW_EB!r}\nFIELD_NAME = {FIELD_NAME!r}\nNEW_ID = {NEW_ID}\n\n"
        "dp = MOD / 'DictionaryPatch.txt'\n"
        "dp_orig = dp.with_suffix('.txt.tierc_orig')\n"
        "if dp_orig.exists():\n"
        "    shutil.copy(dp_orig, dp); dp_orig.unlink()\n"
        "    print('restored DictionaryPatch.txt')\n"
        "for lang in LANGS:\n"
        "    eb = RES/'CommonAsset'/'EventEngine'/'EventBinary'/'Field'/lang/f'EVT_{FIELD_NAME}.eb.bytes'\n"
        "    orig = eb.with_suffix('.bytes.tierc_orig')\n"
        "    if orig.exists():\n"
        "        shutil.copy(orig, eb); orig.unlink()\n"
        "    bd = RES/'CommonAsset'/'EventEngine'/'EventBinary'/'Battle'/lang/f'{NEW_EB}.eb.bytes'\n"
        "    if bd.exists(): bd.unlink()\n"
        "    mes = MOD/'FF9_Data'/'embeddedasset'/'text'/lang/'battle'/f'{NEW_ID}.mes'\n"
        "    if mes.exists(): mes.unlink()\n"
        "if SCENE_DIR.exists():\n"
        "    shutil.rmtree(SCENE_DIR); print('removed', SCENE_DIR.name)\n"
        "print('Tier-c C1 probe reverted. Relaunch FF9.')\n",
        encoding="utf-8")
    print(f"[tierc] wrote {revert.relative_to(ROOT)}")


if __name__ == "__main__":
    raise SystemExit(main())
