#!/usr/bin/env bash
# Prior-art recon: Memoria engine SOURCE evidence for the built-in title override path.
# Read-only. Re-runnable.
SRC="C:/gd/FFIX/Memoria/Assembly-CSharp"

echo "== TitleUI built-in DLL-free title override (title_bg / title_logo) =="
grep -nE 'title_bg|title_logo|SearchAssetOnDisc\("EmbeddedAsset/UI' "$SRC/Global/TitleUI.cs"

echo; echo "== SplashScreen.cs custom SE-splash (SplashTitle.png, game-root only) =="
grep -nE 'CUSTOM_SPLASH_PATH|SplashTitle|LoadImage|LoadLevel' "$SRC/Global/SplashScreen.cs"

echo; echo "== FMV000 = title background movie/BGM =="
grep -nE 'FMV000' "$SRC/Global/TitleUI.cs"

echo; echo "== SkipIntros knob definition + title-loop consumer =="
grep -rn 'SkipIntros' "$SRC/Memoria/Configuration/Structure/GraphicsSection.cs" "$SRC/Global/TitleUI.cs"

echo; echo "== SearchAssetOnDisc iterates mod folders (FolderHighToLow) =="
grep -nE 'FolderHighToLow|TryFindAssetInModOnDisc' "$SRC/Global/Asset/AssetManager.cs" | head
