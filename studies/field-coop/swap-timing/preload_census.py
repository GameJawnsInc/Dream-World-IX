import re, sys, os, collections
root = sys.argv[1]
rf = re.compile(r'^\s*Field\(\s*(\d+)\s*\)')
rp = re.compile(r'PreloadField\(\s*(\d+)\s*,\s*(\d+)\s*\)')
rw = re.compile(r'^\s*Wait\(\s*(\d+)\s*\)')
rfade = re.compile(r'FadeFilter\(\s*(\d+)\s*,\s*(\d+)\s*,')
rfunc = re.compile(r'^\s*Function\s|^\s*function\s|^Function ')
tot=0; paired=0; mismatch=0; nopre=0
gaps=collections.Counter(); fades=collections.Counter()
for fn in os.listdir(root):
    if not fn.endswith('.txt'): continue
    lines=open(os.path.join(root,fn),encoding='utf-8',errors='replace').read().split('\n')
    for i,l in enumerate(lines):
        m=rf.match(l)
        if not m: continue
        tot+=1; dest=m.group(1)
        found=None; waits=0; fade=None
        for j in range(i-1, max(-1,i-60), -1):
            lj=lines[j]
            if 'Function ' in lj and lj.strip().startswith('Function'): break
            if rf.match(lj): break
            w=rw.match(lj)
            if w: waits+=int(w.group(1))
            f=rfade.search(lj)
            if f and fade is None: fade=(f.group(1),f.group(2))
            p=rp.search(lj)
            if p:
                found=p.group(2); break
        if found is None: nopre+=1
        elif found==dest:
            paired+=1; gaps[min(waits,200)//10*10]+=1
            if fade: fades[fade]+=1
        else: mismatch+=1
print('Field calls',tot,'preceded by PreloadField(same dest)',paired,'different dest',mismatch,'none within window',nopre)
print('Wait ticks between PreloadField and Field (bucketed by 10):',sorted(gaps.items()))
print('top FadeFilter (mode,frames) in paired windows:',fades.most_common(8))
