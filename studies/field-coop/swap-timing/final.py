import re, sys, glob, statistics as st
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
def first(L, pat, t0, t1, n0=-1):
    for t, n, l in L:
        if t0 <= t <= t1 and n > n0 and re.search(pat, l):
            return (t, n, l)
    return None
allrows = []
for sess in THETA:
    th = THETA[sess]
    H = parse(glob.glob(f'{BASE}/{sess}/desktop-host*.log')[0])
    G = parse(glob.glob(f'{BASE}/{sess}/laptop-guest*.log')[0])
    taps = []
    for t, n, l in H:
        m = re.search(r'dialog tap: win (\d+) text (\d+) .* seq (\d+)$', l)
        if m: taps.append((t, n, int(m.group(1)), int(m.group(2)), int(m.group(3))))
    opens = [(t, n, int(m.group(1)), int(m.group(2))) for t, n, l in G for m in [re.search(r'dialogue lock: win (\d+) text (\d+) opened locked', l)] if m]
    Q = {}; C = {}
    for t, n, l in G:
        m = re.search(r'dialogue: host seq (\d+) queued \(field (\d+)', l)
        if m: Q.setdefault(int(m.group(1)), (t, n, int(m.group(2))))
        m = re.search(r'dialogue: win \d+ text \d+ (?:closed|advanced) \(host seq (\d+)', l)
        if m: C.setdefault(int(m.group(1)), (t, n))
    hi = [(t, n, int(re.search(r'field (\d+) \(nonce', l).group(1))) for t, n, l in H if 'transition intent ->' in l]
    for k, (t, n, f) in enumerate(hi):
        tend = hi[k + 1][0] if k + 1 < len(hi) else t + 300
        hl = [x for x in (first(H, rf'Map: {f} ', t, t + 3, n), first(H, r'host scene: ended .* field change', t, t + 3, n), first(H, r'leader guard: the host-side leader is now', t, t + 2, n)) if x]
        HL = min(x[0] for x in hl) if hl else None
        HGS = first(H, rf'ghost spawned .* on field {f} ', t, tend, n)
        HR = first(H, rf'host scene: rose \(nonce \d+, field {f}\)', t, min(tend, t + 15), n)
        gt0 = int(t - th) - 4; gt1 = int(tend - th)
        GI = first(G, rf'following the peer to field {f}\b', gt0, gt1)
        g0 = GI[0] - 1 if GI else gt0
        BOUNCE = first(G, r'gateway \(bounced', g0, (GI[0] + 2) if GI else gt0 + 6)
        PASS = first(G, rf'(own Field\({f}\) passes|follow-warp to field {f} cancelled: this load already landed)', g0, gt0 + 10)
        GL = first(G, rf'(self-dress: field {f} |Map: {f} |ghost spawned .* on field {f} )', g0, gt1)
        if GI and 'parallel' in GI[2]:
            cat = 'PAR' + ('+BOUNCE' if BOUNCE else '') + ('+OWNPASS' if PASS and 'cancelled' in PASS[2] else '')
        elif GI:
            cat = 'SERIAL'
        elif PASS:
            cat = 'OWN(ATE)'
        elif GL and f == (hi[k - 1][2] if k else -1):
            cat = 'OWN-RELOAD'
        elif GL:
            cat = 'OWN?'
        else:
            cat = 'none'
        # dialogue on f after the guest landing, host taps between landing and next intent
        ftaps = [x for x in taps if t <= x[0] <= tend]
        seqinfo = []
        for (ht, hn, w, tx, s) in ftaps:
            if s not in Q or s not in C: seqinfo.append((s, '?', None)); continue
            nc = C[s][1]
            o = [x for x in opens if x[2] == w and x[3] == tx and x[1] < nc and x[0] >= Q[s][0] - 60]
            if not o: seqinfo.append((s, '?', None)); continue
            o = o[-1]
            order = 'W' if o[1] < Q[s][1] else 'B'   # W: guest waited (open before host close arrived); B: behind
            seqinfo.append((s, order, C[s][0] + th - ht))
        conv = None
        for i, (s, o, cl) in enumerate(seqinfo):
            if o == 'W':
                conv = i + 1; break
        pattern = ''.join(o for s, o, cl in seqinfo[:12])
        row = dict(sess=sess[6:], t=hms(t), f=f, cat=cat,
                   h_load=(HL - t) if HL is not None else None,
                   lag1=(HGS[0] - (HL if HL is not None else t)) if HGS else None,
                   hgs_from_i=(HGS[0] - t) if HGS else None,
                   g_follow=(GL[0] - GI[0]) if (GI and GL) else None,
                   lagX=round(GL[0] + th - (HL if HL is not None else t), 2) if GL else None,
                   scene=bool(HR), rose=(HR[0] - (HL if HL is not None else t)) if HR else None,
                   first_cl=(round(seqinfo[0][2], 2) if seqinfo and seqinfo[0][2] is not None else None),
                   conv=conv, pattern=pattern)
        allrows.append(row)
        print(row)
import json
json.dump(allrows, open(str(__import__('pathlib').Path(__file__).with_name('rows.json')), 'w'), indent=1)
for cat in ('PAR', 'PAR+BOUNCE', 'PAR+OWNPASS', 'OWN(ATE)', 'OWN-RELOAD', 'SERIAL'):
    r = [x for x in allrows if x['cat'] == cat]
    l1 = [x['lag1'] for x in r if x['lag1'] is not None]
    lx = [x['lagX'] for x in r if x['lagX'] is not None]
    gf = [x['g_follow'] for x in r if x['g_follow'] is not None]
    hl = [x['h_load'] for x in r if x['h_load'] is not None]
    print(cat, 'n', len(r), 'lag1(host clock) mean %.2f n%d' % (st.mean(l1), len(l1)) if l1 else '', 'vals', l1,
          '| lagX mean %.2f' % st.mean(lx) if lx else '', '| guest follow->land mean %.2f %s' % (st.mean(gf), gf) if gf else '',
          '| host intent->land mean %.2f %s' % (st.mean(hl), hl) if hl else '')
