#!/usr/bin/env bash
# LENS: prior-art -- title-screen modding levers this project already owns.
# Re-run to reproduce every citation in the ART-* claims. READ-ONLY on game+Memoria clone.
set -u
MEM="C:/gd/FFIX/Memoria/Assembly-CSharp"
GAME="C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"
REPO="C:/gd/Dream-World-IX/.claude/worktrees/title-screen-exploration-0f5fb6"

echo "===== (b) memoria-patches stack ====="
ls "$REPO/memoria-patches/"

echo "===== (a) kit FMV skip tool + music swap module ====="
sed -n '1,15p' "$REPO/tools/skip_opening_fmv.py"
sed -n '1,14p' "$REPO/ff9mapkit/ff9mapkit/sound.py"
grep -n "fmv-swap\|fmv_swap" "$REPO/ff9mapkit/docs/FORK_FIDELITY.md"

echo "===== TitleUI.cs -- title attract movie + audio + SkipIntros + loose sprite hooks ====="
grep -n 'LoadMovie\|PlayMovieMusic("FMV000"\|SkipIntros\|title_bg\|title_logo\|SearchAssetOnDisc' "$MEM/Global/TitleUI.cs"

echo "===== Title BGM = music033 = 'Title Music' ====="
grep -n 'case "FMV000"' "$MEM/Global/Sound/Lib/SoundLib.cs"
grep -n 'music033' "$MEM/Memoria/Assets/Text/AudioResources.cs"

echo "===== UI atlas loose-override load sites (Screen Button Atlas etc.) ====="
grep -n 'EmbeddedAsset/UI/Atlas/\|Screen Button Atlas' "$MEM/Assets/Sources/Scripts/UI/Common/FF9UIDataTool.cs"

echo "===== (d) live Memoria.ini boot/title/movie settings ====="
grep -nE 'SkipIntros|MovieVolume|MusicVolume|PriorityToOGG|FolderNames|BattleSwirlFrames' "$GAME/Memoria.ini"

echo "===== (e) Moguri proves DLL-free title override in the wild ====="
ls "$GAME/MoguriMain/FF9_Data/EmbeddedAsset/ui/sprites"
ls "$GAME/MoguriMain/FF9_Data/EmbeddedAsset/ui/atlas"
head -1 "$GAME/MoguriVideo/ModFileList.txt"   # ma/fmv000.bytes -> title attract FMV, DLL-free

echo "===== kit already owns the UIAtlas.OverrideAtlas mechanism (Face Atlas) ====="
grep -n 'OverrideAtlas\|EmbeddedAsset/UI/Atlas' "$REPO/ff9mapkit/ff9mapkit/content/portrait.py"
