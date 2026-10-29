import json, sys, glob, os
for run in sorted(glob.glob('*/.harness-runs/*duo-coop_follow_race_duo') + glob.glob('*/.harness-runs/*duo-s154-follow*')):
    steps = [json.loads(l) for l in open(os.path.join(run, 'host', 'steps.jsonl'))]
    warps = [s for s in steps if s.get('kind') == 'step' and any(str(x).startswith('warp ') for x in s.get('steps', []))]
    for leg, dest in (('FE1', 30602), ('FE2', 250)):
        f = os.path.join(run, 'guest', f'follow-{leg}.jsonl')
        if not os.path.exists(f):
            continue
        rows = [json.loads(l) for l in open(f)]
        t0 = rows[0]['t']; t1 = rows[-1]['t']
        # host warp to dest sent inside the stream window
        cand = [w for w in warps if any(str(x).startswith(f'warp {dest} ') for x in w['steps']) and t0 - 1 <= w['t'] <= t1]
        tsend = cand[0]['t'] if cand else None
        def first(pred, start=0):
            for i in range(start, len(rows)):
                if pred(rows[i]): return i
            return None
        i_rise = first(lambda r: r['pending'] == dest)
        i_fall = first(lambda r: r['pending'] != dest, i_rise) if i_rise is not None else None
        i_fld = first(lambda r: r['field'] == dest, i_rise or 0)
        i_hud = first(lambda r: r['field'] == dest and r['ui'] == 'FieldHUD' and not r['fading'], i_fld or 0)
        i_ctl = first(lambda r: r['field'] == dest and r['control'], i_fld or 0)
        def br(i):
            if i is None: return 'NA'
            lo = rows[i-1]['t'] if i > 0 else rows[i]['t']
            return '[%.3f,%.3f]' % (lo - tsend, rows[i]['t'] - tsend)
        print(os.path.basename(run)[:15], leg, 'send->rise', br(i_rise), 'commit', br(i_fall), 'field', br(i_fld), 'hud', br(i_hud), 'control', br(i_ctl))
