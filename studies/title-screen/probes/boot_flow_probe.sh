#!/usr/bin/env bash
# LENS: boot-flow — FF9 (Steam, Memoria) boot sequence + pre-title insertion seams.
# Re-runnable evidence collector. All READ-ONLY. Paths quoted (spaces).
# Run with: bash boot_flow_probe.sh
set -u
MEM="C:/gd/FFIX/Memoria/Assembly-CSharp"
GAME="C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"
PATCHES="C:/gd/Dream-World-IX/.claude/worktrees/title-screen-exploration-0f5fb6/memoria-patches"

echo "############ BOOT ORDER (runtime, via Debug.Log tags + LoadLevel chain) ############"
echo "--- BootUp hop 1: BundleSceneSelector (tag '10') -> LoadLevel(SplashScreen) ---"
grep -n 'Debug.Log("10\|LoadLevel("SplashScreen")\|SteamAPIRestartAppIfNecessary\|TryInitialize' "$MEM/Global/Bundle/BundleSceneSelector.cs"
echo "--- hop 2: SplashScreen (tag '20') -> shows Square splash sprite -> LoadLevel(Bundle) ---"
grep -n 'Debug.Log("20\|LoadLevel("Bundle")\|CUSTOM_SPLASH_PATH\|SplashTitle.png' "$MEM/Global/SplashScreen.cs"
echo "--- hop 3: BundleScene.Awake GameInitializer.Initial + bundle load -> ReplaceNow(MainMenu) ---"
grep -n 'GameInitializer.Initial\|ReplaceNow("MainMenu")\|_skipBundleScene' "$MEM/Global/Bundle/BundleScene.cs"

echo
echo "############ TITLE SCENE (MainMenu = TitleUI, a Unity UIScene — NOT a .eb field) ############"
echo "--- PlaySplashScreen: warning text + logos(sqex/sst) + intro movie FMV000 (all hardcoded) ---"
grep -n 'warning\|logo_sqex\|logo_sst\|LoadMovie("FMV000")\|PlaySplashScreen' "$MEM/Global/TitleUI.cs"
echo "--- SkipIntros gating of logos/movie/loop ---"
grep -n 'SkipIntros' "$MEM/Global/TitleUI.cs"

echo
echo "############ SEAM (c): New Game -> field 70 (engine side) ############"
echo "--- TitleUI.OnNewGameButtonClick: ReInitStateSystem + Replace(FieldMap) ---"
grep -n 'OnNewGameButtonClick\|ReInitStateSystem()\|Replace("FieldMap"' "$MEM/Global/TitleUI.cs"
echo "--- ReInitStateSystem -> EventEngine.NewGame() ---"
grep -n 'ReInitStateSystem\|EventEngine>.Instance.NewGame' "$MEM/Global/ff9/State/FF9StateSystem.cs"
echo "--- EventEngine.NewGame: fldMapNo = 70 (Opening-For FMV) ---"
grep -n 'fldMapNo = 70\|public void NewGame\|ReplaceFieldMap' "$MEM/Global/Event/Engine/EventEngine.Initialize.cs"

echo
echo "############ SEAM (a): intro movie is a loose, mod-overridable .bytes file ############"
echo "--- stock intro movie file exists in game install ma/ ---"
ls "$GAME/StreamingAssets/ma/FMV000.bytes"
echo "--- Moguri mod overrides FMV000 via a mod folder StreamingAssets/ma/ (ground truth) ---"
ls "$GAME/MoguriVideo/StreamingAssets/ma/FMV000.bytes"
echo "--- MBG.LoadMovie loads by NAME (path resolves through mod-folder-stacked AssetManager) ---"
grep -n 'public void LoadMovie\|movieMaterial.Load' "$MEM/Global/MBG.cs"

echo
echo "############ SEAM (d): boot-related config flags ############"
grep -n 'SkipIntros' "$MEM/Memoria/Configuration/Structure/GraphicsSection.cs"
echo "--- live install Memoria.ini value (user's actual boot behavior) ---"
grep -niE 'SkipIntros *=' "$GAME/Memoria.ini"
echo "--- custom-splash + title asset swap hooks in TitleUI.Show (DLL-free asset swap) ---"
grep -n 'title_bg\|title_logo\|SearchAssetOnDisc' "$MEM/Global/TitleUI.cs"

echo
echo "############ SEAM (b): patch house-style calibration (unified diff over Assembly-CSharp) ############"
echo "--- smallest reference patch: s18 field-reload hotkey (single hunk in HonoLateUpdate) ---"
wc -l "$PATCHES/s18-field-reload-hotkey.patch"
head -8 "$PATCHES/s18-field-reload-hotkey.patch"
