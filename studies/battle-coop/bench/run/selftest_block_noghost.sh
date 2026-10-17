#!/bin/bash
# As s133run/selftest_block.sh, but ALSO blanks [Netsync] GhostAs (s139 acceptance step 2); the owner's Memoria.ini restored
# byte-exact from the same backup on ANY exit. Usage: selftest_block_noghost.sh <outdir> <label>:<field>:<scenario>[:ENV=VAL,...]
set -u
WT=/c/gd/Dream-World-IX/.claude/worktrees/zealous-dubinsky-016505
G="/c/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"
BAK=/c/gd/Dream-World-IX/backups/Memoria.ini.pre-r3-phase1.20261014-222737
OUT="$1"; shift; mkdir -p "$OUT"
echo "INI at start $(sha256sum "$G/Memoria.ini" | cut -c1-16)"
restore() { cp -p "$BAK" "$G/Memoria.ini"; echo "INI restored $(sha256sum "$G/Memoria.ini" | cut -c1-16)"; }
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
cd "$WT"
for spec in "$@"; do
  IFS=: read -r label field scen envs <<< "$spec"
  echo "=== $label $(date +%T)"
  env $(echo "${envs:-}" | tr ',' ' ') PYTHONIOENCODING=utf-8 py tools/play.py "studies/test-harness/scenarios/$scen.py" --field "$field" > "$OUT/$label.txt" 2>&1
  grep -E "checks passed" "$OUT/$label.txt"
  grep -E "^  FAIL  " "$OUT/$label.txt" | cut -c1-220
  grep -E "PASS  [A-Z0-9]+-CAL:" "$OUT/$label.txt" | cut -c1-240
done
echo "BLOCK DONE $(date +%T)"
