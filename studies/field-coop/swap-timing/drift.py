import re, glob, collections
BASE = r'C:/gd/Dream-World-IX/.harness-runs'
TS = re.compile(r'^(\d\d)\.(\d\d)\.(\d{4}) (\d\d):(\d\d):(\d\d) ')
def parse(p):
    o = []
    for n, line in enumerate(open(p, encoding='utf-8', errors='replace')):
        m = TS.match(line)
        if m:
            h, mi, s = map(int, m.groups()[3:]); o.append((h*3600+mi*60+s, n, line[20:]))
    return o
for sess in ['twopc-r3-20261027', 'twopc-s158-20261028', 'twopc-s161-20261028', 'twopc-s163-20261029']:
    H = parse(glob.glob(f'{BASE}/{sess}/desktop-host*.log')[0]); G = parse(glob.glob(f'{BASE}/{sess}/laptop-guest*.log')[0])
    taps = {}
    for t, n, l in H:
        m = re.search(r'(?:dialog tap: .* seq (\d+)$|key tap: .* seq (\d+)|relayed \(seq (\d+)\))', l.strip())
        if m: taps[int(next(g for g in m.groups() if g))] = t
    q = {}
    for t, n, l in G:
        m = re.search(r'host seq (\d+) queued', l)
        if m: q.setdefault(int(m.group(1)), t)
    ds = [taps[s] - q[s] for s in sorted(q) if s in taps]
    half = len(ds) // 2
    def est(x):
        c = collections.Counter(x); lo = min(k for k in c if c[k] >= 2)
        x2 = [v for v in x if v in (lo, lo + 1)]
        p = sum(1 for v in x2 if v == lo + 1) / len(x2)
        return round(lo + p, 2), round((p * (1 - p) / len(x2)) ** .5, 2), len(x2)
    print(sess, 'all', est(ds), 'first half', est(ds[:half]), 'second half', est(ds[half:]))
