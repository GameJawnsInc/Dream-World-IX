#!/usr/bin/env bash
# LENS: mod-override-surface — verify the title-screen override surfaces in the
# Memoria C# source AND the installed Moguri mod folder (ground-truth precedent).
# READ-ONLY. Run from Git Bash. Re-runnable.
set -u
SRC="C:/gd/FFIX/Memoria/Assembly-CSharp"
GAME="C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"

echo "########## (a) ASSET RESOLUTION CORE ##########"
echo "--- AssetManager loose-file path prefixes (GetResourcesAssetsPath / GetStreamingAssetsPath) ---"
grep -n 'return "FF9_Data"\|return "StreamingAssets"\|GetResourcesBasePath\|IsEmbededAssets\|IsMemoriaAssets' "$SRC/Global/Asset/AssetManagerUtil.cs"
echo "--- AssetFolder.TryFindAssetInModOnDisc (pathOnDisc = FolderPath + prefix + assetPath) ---"
grep -n 'pathOnDisc = this.FolderPath' "$SRC/Global/Asset/AssetManager.cs"
echo "--- Texture ext rule (.png / .jpg for atlas_a), TextAsset .bytes ---"
grep -n 'atlas_a\|".png"\|".jpg"\|".bytes"' "$SRC/Global/Asset/AssetManagerUtil.cs"

echo
echo "########## (b) TITLE-SCREEN EXPLICIT HOOKS (TitleUI.cs) ##########"
grep -n 'title_bg\|title_logo\|SearchAssetOnDisc\|StreamingAssets/UI/Sprites/US\|EmbeddedAsset/UI/Sprites/title_image_0\|LoadSprite\|EmbeddedAsset/Text/.*Title/warning' "$SRC/Global/TitleUI.cs"

echo
echo "########## (c) BOOT/INTRO CONFIG (SkipIntros) ##########"
grep -n 'SkipIntros' "$SRC/Memoria/Configuration/Structure/GraphicsSection.cs" "$SRC/Global/TitleUI.cs"
echo "--- user Memoria.ini [Graphics] SkipIntros + [Mod] FolderNames + [Audio] ---"
grep -n 'FolderNames\|SkipIntros\|PriorityToOGG\|MovieVolume' "$GAME/Memoria.ini"

echo
echo "########## (d) PROVEN SWAP SURFACES ##########"
echo "--- FMV movie: MovieMaterial.Open() -> ma/<key>.bytes over mod folders ---"
grep -n '"ma/" + this.MovieFile\|movieKey + ".bytes"\|TryFindAssetInModOnDisc(moviePath' "$SRC/Assets/Sources/Graphics/Movie/MovieMaterial.cs"
echo "--- Music/sound: SoundLoaderResources -> Sounds/<id>.akb + loose Sounds/<id>.ogg ---"
grep -n 'Sounds/" + profile.ResourceID + ".akb"\|Sounds/" + profile.ResourceID + ".ogg"' "$SRC/Global/Sound/Loader/SoundLoaderResources.cs"
echo "--- title theme: FMV000 -> MovieAudio index Sounds01/BGM_/music033 ---"
grep -n 'FMV000\|MovieAudio' "$SRC/Global/Sound/Lib/SoundLib.cs" | head -4

echo
echo "########## MOGURI GROUND-TRUTH (installed mod folder proves the convention) ##########"
for f in \
  "$GAME/MoguriMain/FF9_Data/EmbeddedAsset/ui/sprites/title_bg.png" \
  "$GAME/MoguriMain/FF9_Data/EmbeddedAsset/ui/sprites/title_logo.png" \
  "$GAME/MoguriVideo/StreamingAssets/ma/FMV000.bytes" ; do
  if [ -f "$f" ]; then echo "EXISTS: $f"; else echo "MISSING: $f"; fi
done
echo "--- Moguri NGUI atlas override precedent (.png + .tpsheet) ---"
ls "$GAME/MoguriMain/FF9_Data/EmbeddedAsset/ui/atlas/" 2>/dev/null
