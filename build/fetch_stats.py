#!/usr/bin/env python3
"""Hydrate career hitting/pitching lines + awards for the shipped players."""
import json, sys, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

selected = json.load(open('selected.json'))
ids = sorted(selected.keys(), key=int)
BATCH = 40

def get(url):
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                return json.loads(r.read())
        except Exception as e:
            if attempt == 3:
                print('FAIL', e, file=sys.stderr)
                return None
    return None

def batch(chunk):
    q = urllib.parse.urlencode({
        'personIds': ','.join(chunk),
        'hydrate': 'stats(group=[hitting,pitching],type=[career]),awards',
    })
    d = get(f'https://statsapi.mlb.com/api/v1/people?{q}')
    return (d or {}).get('people', [])

chunks = [ids[i:i + BATCH] for i in range(0, len(ids), BATCH)]
out = {}
done = 0
with ThreadPoolExecutor(max_workers=6) as ex:
    for ppl in ex.map(batch, chunks):
        for p in ppl:
            pid = str(p['id'])
            rec = {}
            for s in p.get('stats', []):
                grp = s['group']['displayName']
                if not s.get('splits'):
                    continue
                st = s['splits'][0]['stat']
                if grp == 'hitting':
                    rec['h'] = {
                        'g': st.get('gamesPlayed'), 'pa': st.get('plateAppearances'),
                        'ab': st.get('atBats'), 'h': st.get('hits'), 'hr': st.get('homeRuns'),
                        'rbi': st.get('rbi'), 'r': st.get('runs'), 'sb': st.get('stolenBases'),
                        'avg': st.get('avg'), 'obp': st.get('obp'), 'slg': st.get('slg'),
                        'ops': st.get('ops'), 'bb': st.get('baseOnBalls'), 'so': st.get('strikeOuts'),
                        'db': st.get('doubles'), 'tp': st.get('triples'),
                    }
                elif grp == 'pitching':
                    rec['p'] = {
                        'g': st.get('gamesPlayed'), 'gs': st.get('gamesStarted'),
                        'w': st.get('wins'), 'l': st.get('losses'), 'era': st.get('era'),
                        'ip': st.get('inningsPitched'), 'so': st.get('strikeOuts'),
                        'bb': st.get('baseOnBalls'), 'sv': st.get('saves'),
                        'whip': st.get('whip'), 'cg': st.get('completeGames'),
                        'sho': st.get('shutouts'),
                    }
            aw = p.get('awards', [])
            names = [a.get('name', '') for a in aw]
            rec['hof'] = any('Hall Of Fame' in n for n in names)
            rec['as'] = sum(1 for n in names if 'All-Star' in n and 'Game MVP' not in n)
            rec['ws'] = sum(1 for n in names if n == 'World Series Championship')
            big = []
            for a in aw:
                n = a.get('name', '')
                yr = a.get('season', '')
                if 'Most Valuable Player' in n and 'Series' not in n and 'Game' not in n:
                    big.append(f'MVP {yr}')
                elif 'Cy Young' in n:
                    big.append(f'Cy Young {yr}')
                elif 'Rookie of the Year' in n:
                    big.append(f'ROY {yr}')
                elif 'Gold Glove' in n:
                    big.append('GG')
                elif 'Silver Slugger' in n:
                    big.append('SS')
                elif 'World Series MVP' in n:
                    big.append(f'WS MVP {yr}')
            rec['awards'] = big
            out[pid] = rec
        done += 1
        if done % 20 == 0:
            print(f'{done}/{len(chunks)} batches ({len(out)} players)', file=sys.stderr)

json.dump(out, open('stats.json', 'w'))
missing = [i for i in ids if i not in out]
print(f'wrote stats.json: {len(out)} players, {len(missing)} missing', file=sys.stderr)
