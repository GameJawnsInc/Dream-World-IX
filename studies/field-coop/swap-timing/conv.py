import re, sys, glob
BASE = r'C:/gd/Dream-World-IX/.harness-runs'
TS = re.compile(r'^(\d\d)\.(\d\d)\.(\d{4}) (\d\d):(\d\d):(\d\d) ')
THETA = {'twopc-r3-20261027': 0.17, 'twopc-s158-20261028': 1.40, 'twopc-s161-20261028': 1.50, 'twopc-s163-20261029': 1.87}
def parse(path):
    out = []
    for n, line in enumerate(open(path, encoding='utf-8', errors='replace')):
        m = TS.match(line)
        if not m: continue
        h, mi, s = map(int, m.groups()[3:])
        out.append((h * 3600 + mi * 60 + s, n, line.rstrip('\n')[20:]))
    return out
def hms(t): return '%02d:%02d:%02d' % (t // 3600, t // 60 % 60, t % 60)
# [ff9mapkit netsync s164] the tolerant stamp tail: an s164 engine ends a dialogue line with " (t T ms)" on its swap clock (QPC ms).
# A stamp is preferred over the whole-second prefix when BOTH lines of a comparison carry one (a cross-machine one then takes
# THETA_QPC, the stamped session's clock offset from drift.py; 0 on one machine), never THETA.
STAMP = re.compile(r' \(t (\d+) ms\)$')
THETA_QPC = {}
def stamp(line):
    m = STAMP.search(line)
    return int(m.group(1)) if m else None
for sess in sys.argv[1:]:
    th = THETA[sess]
    H = parse(glob.glob(f'{BASE}/{sess}/desktop-host*.log')[0])
    G = parse(glob.glob(f'{BASE}/{sess}/laptop-guest*.log')[0])
    taps = {}
    for t, n, l in H:
        m = re.search(r'dialog tap: win (\d+) text (\d+) kind (\d) .* page (\d+)( closes)? seq (\d+)(?: \(t (\d+) ms\))?$', l)
        if m: taps[int(m.group(6))] = (t, int(m.group(1)), int(m.group(2)), int(m.group(7)) if m.group(7) else None)
    # guest events
    opens = []  # (t, n, win, text, stamp)
    Q = {}; C = {}
    land = []
    for t, n, l in G:
        m = re.search(r'dialogue lock: win (\d+) text (\d+) opened locked', l)
        if m: opens.append((t, n, int(m.group(1)), int(m.group(2)), stamp(l)))
        m = re.search(r'dialogue: host seq (\d+) queued \(field (\d+) win (\d+) text (\d+)', l)
        if m and int(m.group(1)) not in Q: Q[int(m.group(1))] = (t, n, int(m.group(2)), int(m.group(3)), int(m.group(4)), stamp(l))
        m = re.search(r'dialogue: win (\d+) text (\d+) (closed|advanced) \(host seq (\d+)', l)
        if m: C.setdefault(int(m.group(4)), (t, n, stamp(l)))
        m = re.search(r'(self-dress: field (\d+) |Map: (\d+) )', l)
        if m: land.append((t, n))
    print(f'##### {sess} theta={th}   cols: seq field win text | Hclose | Gopen Gqueued Gclose (guest clock) | order wait=Q-O closeLag=C+theta-H')
    prevf = None
    for s in sorted(Q):
        if s not in taps: continue
        tq, nq, f, w, tx, qms = Q[s]
        # guest open: latest open of (w,tx) with n < close line (or < nq+5)
        nc = C.get(s, (None, 10**9))[1]
        cand = [o for o in opens if o[2] == w and o[3] == tx and o[1] < nc and o[0] >= tq - 60]
        o = cand[-1] if cand else None
        if f != prevf:
            print(f'  -- field {f}')
            prevf = f
        hc, hms_ = taps[s][0], taps[s][3]
        if s in C and o:
            order = 'Q<O' if nq < o[1] else 'O<Q'
            wait = (qms - o[4]) / 1000.0 if (qms is not None and o[4] is not None) else tq - o[0]
            cms = C[s][2]
            cl = (cms - hms_) / 1000.0 + THETA_QPC.get(sess, 0.0) if (cms is not None and hms_ is not None) else C[s][0] + th - hc
            print(f'  {s:3d} {f:4d} w{w} t{tx:4d} | H {hms(hc)} | O {hms(o[0])} Q {hms(tq)} C {hms(C[s][0])} | {order} wait={wait:+} closeLag={cl:+.2f}')
        else:
            print(f'  {s:3d} {f:4d} w{w} t{tx:4d} | H {hms(hc)} | O {hms(o[0]) if o else "--"} Q {hms(tq)} C {"--" if s not in C else hms(C[s][0])} | (no close/open pair)')
