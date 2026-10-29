import re, glob, json
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
rows = json.load(open(str(__import__('pathlib').Path(__file__).with_name('rows.json'))))
for sess, th in THETA.items():
    H = parse(glob.glob(f'{BASE}/{sess}/desktop-host*.log')[0]); G = parse(glob.glob(f'{BASE}/{sess}/laptop-guest*.log')[0])
    hi = [(t, n, int(re.search(r'field (\d+) \(nonce', l).group(1))) for t, n, l in H if 'transition intent ->' in l]
    for k, (t, n, f) in enumerate(hi):
        r = [x for x in rows if x['sess'] == sess[6:] and x['t'] == hms(t)][0]
        if not r['scene']: continue
        tend = hi[k + 1][0] if k + 1 < len(hi) else t + 300
        rose = next((x for x in H if t <= x[0] <= tend and x[1] > n and re.search(rf'host scene: rose \(nonce \d+, field {f}\)', x[2])), None)
        tap = next((x for x in H if t <= x[0] <= tend and x[1] > n and 'dialog tap:' in x[2]), None)
        if not rose or not tap: continue
        w, tx = re.search(r'win (\d+) text (\d+)', tap[2]).groups()
        # guest: first open on f after landing marker
        gl = next((x for x in G if int(t - th) - 4 <= x[0] and re.search(rf'(self-dress: field {f} |Map: {f} |ghost spawned .* on field {f} )', x[2])), None)
        if not gl: continue
        go = next((x for x in G if x[1] > gl[1] and re.search(r'dialogue lock: win \d+ text \d+ opened locked', x[2])), None)
        same = go and re.search(rf'win {w} text {tx} opened', go[2])
        gx = next((x for x in G if x[1] > gl[1] and re.search(rf'dialogue lock: win {w} text {tx} opened locked', x[2])), None)
        print(f"{sess[6:10]} {hms(t)} ->{f} {r['cat']:12s} host land+{r['rose']}s rose {hms(rose[0])}; first tap w{w} t{tx} at {hms(tap[0])} | guest land {hms(gl[0])}; first guest open {'SAME' if same else 'other: ' + (go[2][29:75] if go else '-')}; guest open of t{tx} {hms(gx[0]) if gx else '-'} -> openLagX {round(gx[0] + th - rose[0], 2) if gx and same else 'n/a'}")
