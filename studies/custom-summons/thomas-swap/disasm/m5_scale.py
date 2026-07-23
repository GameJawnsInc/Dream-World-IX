import collections, math
LOG=r"C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX/sfxmeshprobe.log"
root={}
for ln in open(LOG,'r',errors='ignore'):
    if not ln.startswith('ROOT,'): continue
    p=ln.split(','); root[int(p[2])]=[int(x) for x in p[3:]]
segs=[]; prev=None
for f in sorted(root):
    R=root[f][1:10]; t=tuple(root[f][10:])
    # column norms /4096 = per-axis scale of the R*S matrix
    c=[math.sqrt(R[0+i]**2+R[3+i]**2+R[6+i]**2)/4096 for i in range(3)]
    key=(round(c[0],2),round(c[1],2),round(c[2],2))
    if prev is None or key!=prev[0]:
        segs.append([key,f,f,t,t]); prev=segs[-1]
    else:
        prev[2]=f; prev[4]=t
print(f"{'scale(col norms)':>22}  frames        t(first)              t(last)")
for k,a,b,t0,t1 in segs:
    print(f"{str(k):>22}  {a:4d}..{b:4d}  {str(t0):>22}  {str(t1):>22}")
