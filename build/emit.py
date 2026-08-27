#!/usr/bin/env python3
"""Assemble players.js — the single data file the game loads."""
import json, sys
from collections import Counter

sel = json.load(open('selected.json'))
stats = json.load(open('stats.json'))
field = json.load(open('fielding.json'))
awards = json.load(open('awards.json'))

# order matters — this is the accolade line read on camera
ACCOLADES = [
    ('MVP', 'MVP', True), ('CY', 'Cy Young', True), ('ROY', 'ROY', True),
    ('AS', 'All-Star', False), ('GG', 'Gold Glove', False),
    ('SS', 'Silver Slugger', False), ('WSMVP', 'WS MVP', True),
    ('LCSMVP', 'LCS MVP', False), ('ASMVP', 'ASG MVP', False),
]

def accolades(pid):
    a = awards.get(str(pid)) or {}
    out = []
    for tag, label, show_years in ACCOLADES:
        yrs = [y for y in a.get(tag, []) if y]
        n = len(yrs)
        if not n:
            continue
        if n == 1:
            out.append(f'{label} {yrs[0]}' if show_years else f'{label} {yrs[0]}')
        elif show_years and n <= 3:
            out.append(f'{n}× {label} ({", ".join(yrs)})')
        else:
            out.append(f'{n}× {label}')
    return out, len(a.get('WS', [])), bool(a.get('HOF'))

STATES = {
 'AL':'Alabama','AK':'Alaska','AZ':'Arizona','AR':'Arkansas','CA':'California',
 'CO':'Colorado','CT':'Connecticut','DE':'Delaware','FL':'Florida','GA':'Georgia',
 'HI':'Hawaii','ID':'Idaho','IL':'Illinois','IN':'Indiana','IA':'Iowa','KS':'Kansas',
 'KY':'Kentucky','LA':'Louisiana','ME':'Maine','MD':'Maryland','MA':'Massachusetts',
 'MI':'Michigan','MN':'Minnesota','MS':'Mississippi','MO':'Missouri','MT':'Montana',
 'NE':'Nebraska','NV':'Nevada','NH':'New Hampshire','NJ':'New Jersey','NM':'New Mexico',
 'NY':'New York','NC':'North Carolina','ND':'North Dakota','OH':'Ohio','OK':'Oklahoma',
 'OR':'Oregon','PA':'Pennsylvania','RI':'Rhode Island','SC':'South Carolina',
 'SD':'South Dakota','TN':'Tennessee','TX':'Texas','UT':'Utah','VT':'Vermont',
 'VA':'Virginia','WA':'Washington','WV':'West Virginia','WI':'Wisconsin','WY':'Wyoming',
 'DC':'District of Columbia','PR':'Puerto Rico','VI':'U.S. Virgin Islands','GU':'Guam',
}

FIELD_POS = ['C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF']

def positions(pid, rec):
    """(primary, eligible[]) from career games by position."""
    g = {k: v for k, v in (field.get(str(pid)) or {}).items() if v}
    lineup = {k: v for k, v in g.items() if k in FIELD_POS}
    pitched = g.get('P', 0)
    st = stats.get(str(pid), {})
    ip = rec.get('ip', 0)

    primary = rec.get('pos') or ''
    if primary in ('X', 'PH', 'PR', '', 'OF', 'IF', 'DH'):
        if lineup:
            primary = max(lineup.items(), key=lambda kv: kv[1])[0]
        elif pitched or ip > 0:
            primary = 'P'
        elif primary == 'OF':
            primary = 'CF'
        elif primary in ('DH', 'PH', 'PR'):
            primary = 'DH'
        else:
            primary = 'DH'

    is_pitcher = pitched >= 5 or ip >= 20
    elig = set()
    if lineup:
        # a real position, not a cameo: 5% of his games in the field, min 20
        cut = max(20, 0.05 * sum(lineup.values()))
        elig = {p for p, n in lineup.items() if n >= cut}
        # position players always get their most-played spot even if short of the cut,
        # but a pitcher's one inning in left doesn't make him an outfielder
        if not elig and not is_pitcher:
            elig = {max(lineup.items(), key=lambda kv: kv[1])[0]}
    if is_pitcher:
        elig.add('P')
    if not elig:
        elig = {primary} if primary in FIELD_POS + ['P'] else {'1B'}
    if primary in FIELD_POS + ['P']:
        elig.add(primary)
    return primary, sorted(elig, key=lambda p: (FIELD_POS + ['P']).index(p))

by_state = {}
for pid, rec in sel.items():
    st = rec['st']
    prim, elig = positions(pid, rec)
    s = stats.get(pid, {})
    yrs = ''
    if rec.get('debut'):
        yrs = rec['debut'] + '-' + (rec.get('last') or '')
    p = {
        'id': int(pid),
        'n': rec['name'],
        'p': prim,
        'e': elig,
        'w': rec['war'],
        'wb': rec['warBat'],
        'wp': rec['warPit'],
        'pk': rec['peak'],
        'pky': rec['peakYr'],
        'sn': rec['seasons'],
        'y': yrs,
        'c': rec['city'],
        'b': rec['bats'],
        't': rec['throws'],
        'ht': rec['ht'],
        'wt': rec['wt'],
        'br': rec.get('br', ''),
        'tm': rec.get('tm', []),
        'bd': rec['bd'],
        'dd': rec['died'],
    }
    acc, ws, hof = accolades(pid)
    if hof:
        p['hof'] = 1
    if ws:
        p['ws'] = ws
    if acc:
        p['aw'] = acc
    if s.get('h') and (s['h'].get('pa') or 0) > 0:
        p['h'] = s['h']
    if s.get('p') and (s['p'].get('g') or 0) > 0:
        p['pi'] = s['p']
    by_state.setdefault(st, []).append(p)

for st in by_state:
    by_state[st].sort(key=lambda p: (-p['w'], p['n']))

payload = {
    'meta': {
        'built': '2026-08-04',
        'players': sum(len(v) for v in by_state.values()),
        'source': 'MLB StatsAPI (bio/stats) + Baseball Reference career WAR',
    },
    'stateNames': STATES,
    'states': by_state,
}

js = 'window.GEO_DATA = ' + json.dumps(payload, separators=(',', ':')) + ';\n'
open('players.js', 'w').write(js)
print(f"players.js: {len(js)/1024/1024:.2f} MB, {payload['meta']['players']} players", file=sys.stderr)

# sanity
for st in ('CA', 'WY', 'AK', 'PR'):
    lst = by_state.get(st, [])
    print(f'\n{st} ({len(lst)}):', file=sys.stderr)
    for p in lst[:4]:
        print(f"   {p['n']:<22} {p['p']:<3} {'/'.join(p['e']):<12} WAR {p['w']}", file=sys.stderr)
print('\nprimary pos spread:', Counter(p['p'] for v in by_state.values() for p in v).most_common(), file=sys.stderr)
# any state missing a position?
for st, lst in sorted(by_state.items()):
    have = {pos for p in lst for pos in p['e']}
    missing = [x for x in FIELD_POS + ['P'] if x not in have]
    if missing:
        print(f'   {st} cannot field: {missing}', file=sys.stderr)
