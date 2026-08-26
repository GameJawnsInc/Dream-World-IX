import re, glob, os, collections
D = r"C:/gd/FFIX/reference/test2"
hits = []
counts = collections.Counter()
for p in sorted(glob.glob(os.path.join(D, "test2_*.txt"))):
    try:
        lines = open(p, encoding="utf-8", errors="replace").read().splitlines()
    except Exception as e:
        continue
    for i, l in enumerate(lines):
        if "WindowAsync" in l:
            # look ahead up to 25 lines for IsButton before another WindowSync/blocking op
            for j in range(i+1, min(i+26, len(lines))):
                if "IsButton" in lines[j]:
                    hits.append((os.path.basename(p), i+1, j+1, l.strip(), lines[j].strip()))
                    counts[os.path.basename(p)] += 1
                    break
print("files with WindowAsync followed by IsButton within 25 lines:", len(counts))
print("total sites:", len(hits))
for f, c in counts.most_common(25):
    print(f, c)
print("---- sample sites ----")
for h in hits[:40]:
    print(h[0], "async@", h[1], "poll@", h[2], "|", h[3][:70], "||", h[4][:80])
