#!/bin/bash
# As s133run/selftest_block.sh, but ALSO blanks [Netsync] GhostAs (s139 acceptance step 2); the owner's Memoria.ini
# snapshotted at start and restored byte-exact from that snapshot on ANY exit (as selftest_block.sh: never an old fixed
# backup). Usage: selftest_block_noghost.sh <outdir> <label>:<field>:<scenario>[:ENV=VAL,...]
set -u
WT=/c/gd/Dream-World-IX/.claude/worktrees/gallant-easley-04ab74
G="/c/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"
BK=/c/gd/Dream-World-IX/backups
# the s139-era fixed backup: a restore SOURCE only when the start snapshot cannot be taken AND the live INI is byte-identical
# to it (then it IS the start state); otherwise the block refuses to start
BAK="$BK/Memoria.ini.pre-r3-phase1.20261014-222737"
OUT="$1"; shift; mkdir -p "$OUT"
START=$(sha256sum "$G/Memoria.ini" | cut -c1-64)
echo "INI at start ${START:0:16}"
SNAP="$BK/Memoria.ini.pre-selftest-block.$(date +%Y%m%d-%H%M%S).$$"
if ! { mkdir -p "$BK" && cp -p "$G/Memoria.ini" "$SNAP" && [ "$(sha256sum "$SNAP" | cut -c1-64)" = "$START" ]; }; then
  if [ -f "$BAK" ] && [ "$(sha256sum "$BAK" | cut -c1-64)" = "$START" ]; then
    echo "INI snapshot FAILED ($SNAP); the live INI equals $BAK byte for byte -- restoring from that"; SNAP="$BAK"
  else
    echo "STOP: could not snapshot $G/Memoria.ini to $SNAP (and it differs from $BAK) -- nothing edited"; exit 1
  fi
fi
echo "INI snapshot $SNAP"
restore() {
  cp -p "$SNAP" "$G/Memoria.ini"
  NOW=$(sha256sum "$G/Memoria.ini" | cut -c1-64)
  if [ "$NOW" = "$START" ]; then
    echo "INI restored ${NOW:0:16} (byte-exact to the start, from $SNAP)"
  else
    echo "WARNING: INI restore MISMATCH ${NOW:0:16} != start ${START:0:16} -- copy $SNAP back by hand"
  fi
}
trap restore EXIT
INI="$G/Memoria.ini" py -I -c "
import os,re
p=os.environ['INI']; b=open(p,'rb').read()
i=b.index(b'[Netsync]'); j=b.find(b'\n[',i+1); sec=b[i:j]
new,n=re.subn(rb'(?m)^Enabled = 1(\r?)$', rb'Enabled = 0\1', sec)
assert n==1, n
new,m=re.subn(rb'(?m)^GhostAs = auto(\r?)$', rb'GhostAs = \1', new)
assert m==1, m
open(p,'wb').write(b[:i]+new+b[j:])
print('Enabled -> 0, GhostAs -> blank')
" || exit 1
cd "$WT" || { echo "STOP: WT=$WT is missing -- point WT= at your checkout"; exit 1; }
for spec in "$@"; do
  IFS=: read -r label field scen envs <<< "$spec"
  echo "=== $label $(date +%T)"
  env $(echo "${envs:-}" | tr ',' ' ') PYTHONIOENCODING=utf-8 py tools/play.py "studies/test-harness/scenarios/$scen.py" --field "$field" > "$OUT/$label.txt" 2>&1
  grep -E "checks passed" "$OUT/$label.txt"
  grep -E "^  FAIL  " "$OUT/$label.txt" | cut -c1-220
  grep -E "PASS  [A-Z0-9]+-CAL:" "$OUT/$label.txt" | cut -c1-240
done
echo "BLOCK DONE $(date +%T)"
