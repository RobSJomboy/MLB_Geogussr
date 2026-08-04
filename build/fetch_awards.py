#!/usr/bin/env python3
"""Awards by type (one request per award, all seasons) — the per-player hydrate
truncates its list, this doesn't."""
import json, sys, urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

AWARDS = {
    'MLBHOF': 'HOF', 'ALMVP': 'MVP', 'NLMVP': 'MVP', 'ALCY': 'CY', 'NLCY': 'CY',
    'MLBCY': 'CY', 'ALROY': 'ROY', 'NLROY': 'ROY', 'MLBROY': 'ROY',
    'WSMVP': 'WSMVP', 'WSCHAMP': 'WS', 'ASMVP': 'ASMVP',
    'ALAS': 'AS', 'NLAS': 'AS', 'ALSS': 'SS', 'NLSS': 'SS',
    'ALGG': 'GG', 'NLGG': 'GG', 'MLGG': 'GG',
    'ALCSMVP': 'LCSMVP', 'NLCSMVP': 'LCSMVP',
    'ALBAT': 'BATTITLE', 'NLBAT': 'BATTITLE',
}

def fetch(aid):
    url = f'https://statsapi.mlb.com/api/v1/awards/{aid}/recipients'
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                return aid, json.loads(r.read()).get('awards', [])
        except Exception as e:
            if attempt == 3:
                print('FAIL', aid, e, file=sys.stderr)
                return aid, []
    return aid, []

out = defaultdict(lambda: defaultdict(list))   # pid -> tag -> [seasons]
with ThreadPoolExecutor(max_workers=6) as ex:
    for aid, recs in ex.map(fetch, AWARDS):
        tag = AWARDS[aid]
        for r in recs:
            pl = r.get('player') or {}
            pid = pl.get('id')
            if pid:
                out[str(pid)][tag].append(str(r.get('season') or ''))
        print(f'{aid}: {len(recs)}', file=sys.stderr)

final = {p: {t: sorted(set(s)) for t, s in d.items()} for p, d in out.items()}
json.dump(final, open('awards.json', 'w'))
print(f'wrote awards.json: {len(final)} players', file=sys.stderr)
