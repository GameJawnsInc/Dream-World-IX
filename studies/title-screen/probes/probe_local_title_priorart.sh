#!/usr/bin/env bash
# Prior-art recon: what LOCAL mod folders touch the FF9 title/boot surface.
# Read-only. Re-runnable. Cites the exact ModFileList/ModDescription evidence.
GAME="C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"

echo "== [Mod] FolderNames stack (Memoria.ini) =="
grep -nE '^FolderNames|^SkipIntros|^DisplayPSXDiscChanges' "$GAME/Memoria.ini"

echo; echo "== title/boot assets each mod overrides (ModFileList.txt) =="
for d in FF9CustomMap MoguriMain MoguriVideo FF9CustomMap-world; do
  fl="$GAME/$d/ModFileList.txt"
  echo "--- $d ---"
  if [ -f "$fl" ]; then
    grep -inE 'title|logo|splash|mainmenu|fmv000|opening|copyright|press|start' "$fl" || echo "  (no title/boot lines)"
  else
    echo "  (no ModFileList.txt)"
  fi
done

echo; echo "== SplashTitle.png present anywhere (SE splash swap, game-root only) =="
find "$GAME" -iname 'SplashTitle*' 2>/dev/null || echo "  (none)"

echo; echo "== FMV000 override on disk (title cinematic/BGM) =="
find "$GAME"/*/StreamingAssets/ma -iname 'FMV000*' 2>/dev/null
