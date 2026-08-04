#!/usr/bin/env python3
"""Pull every player who appeared in an MLB season 1876-2026 from StatsAPI.

One request per season gives full person records (birth city/state/country,
primary position, debut, bats/throws) so this is ~150 requests total.
"""
import json, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor

SEASONS = range(1876, 2027)
OUT = 'people.json'

def get(url):
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.loads(r.read())
        except Exception as e:
            if attempt == 3:
                print('FAIL', url, e, file=sys.stderr)
                return None
    return None

def season(y):
    d = get(f'https://statsapi.mlb.com/api/v1/sports/1/players?season={y}')
    if not d:
        return y, []
    return y, d.get('people', [])

people = {}
with ThreadPoolExecutor(max_workers=8) as ex:
    for y, ppl in ex.map(season, SEASONS):
        for p in ppl:
            pid = p['id']
            prev = people.get(pid)
            if prev is None:
                people[pid] = p
        print(f'{y}: {len(ppl):4d} players (total {len(people)})', file=sys.stderr)

keep = {}
for pid, p in people.items():
    pos = p.get('primaryPosition') or {}
    keep[pid] = {
        'id': pid,
        'name': p.get('fullName') or '',
        'bd': p.get('birthDate') or '',
        'city': p.get('birthCity') or '',
        'st': p.get('birthStateProvince') or '',
        'ctry': p.get('birthCountry') or '',
        'pos': pos.get('abbreviation') or '',
        'posName': pos.get('name') or '',
        'ht': p.get('height') or '',
        'wt': p.get('weight') or 0,
        'bats': (p.get('batSide') or {}).get('code') or '',
        'throws': (p.get('pitchHand') or {}).get('code') or '',
        'debut': (p.get('mlbDebutDate') or '')[:4],
        'last': (p.get('lastPlayedDate') or '')[:4],
        'died': (p.get('deathDate') or '')[:4],
    }

json.dump(keep, open(OUT, 'w'))
print(f'wrote {OUT}: {len(keep)} players', file=sys.stderr)
