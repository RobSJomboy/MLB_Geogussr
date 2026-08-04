#!/usr/bin/env python3
"""Career games-by-position for every shipped player -> real lineup eligibility."""
import json, sys, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

ids = sorted(json.load(open('selected.json')).keys(), key=int)
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
        'hydrate': 'stats(group=[fielding],type=[career])',
    })
    return (get(f'https://statsapi.mlb.com/api/v1/people?{q}') or {}).get('people', [])

chunks = [ids[i:i + BATCH] for i in range(0, len(ids), BATCH)]
out, done = {}, 0
with ThreadPoolExecutor(max_workers=6) as ex:
    for ppl in ex.map(batch, chunks):
        for p in ppl:
            games = {}
            for s in p.get('stats', []):
                for sp in s.get('splits', []):
                    ab = (sp.get('position') or {}).get('abbreviation')
                    g = sp['stat'].get('gamesPlayed') or 0
                    if ab:
                        games[ab] = games.get(ab, 0) + g
            out[str(p['id'])] = games
        done += 1
        if done % 30 == 0:
            print(f'{done}/{len(chunks)} batches', file=sys.stderr)

json.dump(out, open('fielding.json', 'w'))
print(f'wrote fielding.json: {len(out)} players', file=sys.stderr)
