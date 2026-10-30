import re, glob, collections, statistics
BASE = r'C:/gd/Dream-World-IX/.harness-runs'
TS = re.compile(r'^(\d\d)\.(\d\d)\.(\d{4}) (\d\d):(\d\d):(\d\d) ')
# [ff9mapkit netsync s164] the tolerant stamp tail: an s164 engine ends the tap and queued lines with " (t T ms)" (QPC ms). When
# BOTH lines of a pair carry one, the stamp is preferred over the whole-second prefix: the offset is then measured in ms on the
# swap clocks (THETA_QPC for final.py / conv.py on a stamped session; ~ the lane latency when both games share one machine).
STAMP = re.compile(r' \(t (\d+) ms\)$')
def stamp(line):
    m = STAMP.search(line.strip())
    return int(m.group(1)) if m else None
def parse(p):
    o = []
    for n, line in enumerate(open(p, encoding='utf-8', errors='replace')):
        m = TS.match(line)
        if m:
            h, mi, s = map(int, m.groups()[3:]); o.append((h*3600+mi*60+s, n, line[20:]))
    return o
for sess in ['twopc-r3-20261027', 'twopc-s158-20261028', 'twopc-s161-20261028', 'twopc-s163-20261029']:
    H = parse(glob.glob(f'{BASE}/{sess}/desktop-host*.log')[0]); G = parse(glob.glob(f'{BASE}/{sess}/laptop-guest*.log')[0])
    taps, tms = {}, {}
    for t, n, l in H:
        m = re.search(r'(?:dialog tap: .* seq (\d+)(?: \(t (\d+) ms\))?$|key tap: .* seq (\d+)|relayed \(seq (\d+)\))', l.strip())
        if m:
            s = int(next(g for g in (m.group(1), m.group(3), m.group(4)) if g))
            taps[s] = t
            if m.group(2):
                tms[s] = int(m.group(2))
    q, qms = {}, {}
    for t, n, l in G:
        m = re.search(r'host seq (\d+) queued', l)
        if m:
            q.setdefault(int(m.group(1)), t)
            if stamp(l) is not None:
                qms.setdefault(int(m.group(1)), stamp(l))
    both = [s for s in sorted(q) if s in tms and s in qms]
    if both:                                                # stamped pairs: the offset in ms, no whole-second bucketing
        dms = [tms[s] - qms[s] for s in both]
        print(sess, 'stamped pairs', len(dms), 'tap - queued median %.0f ms, min %d, max %d' % (statistics.median(dms), min(dms), max(dms)))
        continue
    ds = [taps[s] - q[s] for s in sorted(q) if s in taps]
    half = len(ds) // 2
    def est(x):
        c = collections.Counter(x); lo = min(k for k in c if c[k] >= 2)
        x2 = [v for v in x if v in (lo, lo + 1)]
        p = sum(1 for v in x2 if v == lo + 1) / len(x2)
        return round(lo + p, 2), round((p * (1 - p) / len(x2)) ** .5, 2), len(x2)
    print(sess, 'all', est(ds), 'first half', est(ds[:half]), 'second half', est(ds[half:]))
