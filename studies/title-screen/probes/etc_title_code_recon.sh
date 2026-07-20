#!/usr/bin/env bash
# ETC lens: engine-title-code recon reproduction (READ-ONLY greps over the Memoria clone).
# Re-run each to verify the ETC-* claims. Requires ripgrep (rg).
MEM="C:/gd/FFIX/Memoria/Assembly-CSharp"
PATCHES="C:/gd/Dream-World-IX/.claude/worktrees/title-screen-exploration-0f5fb6/memoria-patches"

echo "== ETC-1/2 TitleUI class + UIScene base =="
rg -n "class TitleUI : UIScene" "$MEM/Global/TitleUI.cs"

echo "== ETC-2 UIManager Title-state dispatch + TitleScene field =="
rg -n 'loadedLevelName == "Title"|ChangeUIState\(UIManager.UIState.Title\)|public TitleUI TitleScene|case UIManager.UIState.Title' "$MEM/Global/UI/UIManager.cs"

echo "== ETC-3 boot bootstrap: GUIManager -> Replace(Title) =="
rg -n 'SceneDirector.Replace\("Title"|Camera_SplashTitle|_skipMenuScene' "$MEM/Global/GUIManager.cs"

echo "== ETC-4 menu buttons are prefab children (Awake indices) + click dispatch =="
rg -n 'MenuGroupPanel.GetChild|OnNewGameButtonClick|OnContinueButtonClick|OnLoadGameButtonClick|OnCloudGameButtonClick' "$MEM/Global/TitleUI.cs"

echo "== ETC-5 New Game call chain =="
rg -n 'private void OnNewGameButtonClick' -A8 "$MEM/Global/TitleUI.cs"

echo "== ETC-6 title background art + logo override (dll-free) =="
rg -n 'title_bg|title_logo|SearchAssetOnDisc|MenuPanelObject.GetChild' "$MEM/Global/TitleUI.cs"

echo "== ETC-7 title BGM = FMV000 -> music033 =="
rg -n 'PlayMovieMusic\("FMV000"|case "FMV000"' "$MEM/Global/TitleUI.cs" "$MEM/Global/Sound/Lib/SoundLib.cs"

echo "== ETC-8 attract/idle slideshow + FMV000 movie + logos =="
rg -n 'idleTime|idleScreen.Play|LoadMovie\("FMV000"\)|logo_sqex|logo_sst|title_image_0' "$MEM/Global/TitleUI.cs"

echo "== ETC-9 splash warning text + SkipIntros =="
rg -n 'Title/warning|SplashScreenEnabled|SkipIntros' "$MEM/Global/TitleUI.cs"
rg -n 'SkipIntros' "$MEM/Memoria/Configuration/Structure/GraphicsSection.cs"

echo "== ETC-10 patches DO NOT touch title/boot/splash structurally =="
rg -n 'TitleUI|PlaySplashScreen|SplashScreenEnabled|FMV000|SkipIntros|title_bg' "$PATCHES" || echo "(only s37 netsync FMV000/SplashScreenEnabled=true return-to-title)"
