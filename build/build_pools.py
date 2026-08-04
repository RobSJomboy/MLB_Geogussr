#!/usr/bin/env python3
"""Join Baseball Reference career WAR onto the StatsAPI people list and pick
which players ship in the game's per-state pools."""
import csv, json, sys
from collections import defaultdict

people = json.load(open('people.json'))

war = defaultdict(float)          # mlb_ID -> career WAR (bat + pitch)
war_bat = defaultdict(float)
war_pitch = defaultdict(float)
pa = defaultdict(int)
ipouts = defaultdict(int)
years = defaultdict(set)
brid = {}                          # mlb_ID -> baseball-reference player id
peak = defaultdict(lambda: (0.0, ''))   # best single season

def num(v):
    if v in ('', 'NULL', None):
        return 0.0
    try:
        return float(v)
    except ValueError:
        return 0.0

def load(path, is_pitch):
    n = 0
    with open(path, newline='', encoding='utf-8', errors='replace') as f:
        for row in csv.DictReader(f):
            mid = (row.get('mlb_ID') or '').strip()
            if not mid or mid == 'NULL':
                continue
            bb = (row.get('player_ID') or '').strip()
            if bb and bb != 'NULL':
                brid.setdefault(mid, bb)
            w = num(row.get('WAR'))
            yr = (row.get('year_ID') or '').strip()
            war[mid] += w
            (war_pitch if is_pitch else war_bat)[mid] += w
            if is_pitch:
                ipouts[mid] += int(num(row.get('IPouts')))
            else:
                pa[mid] += int(num(row.get('PA')))
            if yr:
                years[mid].add(yr)
            n += 1
    print(f'{path}: {n} season-stints', file=sys.stderr)

load('war_bat.txt', False)
load('war_pitch.txt', True)

# peak season = best combined WAR in a single year
season_war = defaultdict(lambda: defaultdict(float))
for path, in (('war_bat.txt',), ('war_pitch.txt',)):
    with open(path, newline='', encoding='utf-8', errors='replace') as f:
        for row in csv.DictReader(f):
            mid = (row.get('mlb_ID') or '').strip()
            yr = (row.get('year_ID') or '').strip()
            if mid and mid != 'NULL' and yr:
                season_war[mid][yr] += num(row.get('WAR'))
for mid, ys in season_war.items():
    y, w = max(ys.items(), key=lambda kv: kv[1])
    peak[mid] = (round(w, 1), y)

print(f'WAR records for {len(war)} mlb_IDs', file=sys.stderr)

# ---- US states only (plus DC and territories Geoguessr can drop you in) ----
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
FULL2ABBR = {v.lower(): k for k, v in STATES.items()}

by_state = defaultdict(list)
skipped_state = defaultdict(int)
for pid, p in people.items():
    if p['ctry'] not in ('USA', 'United States', 'Puerto Rico', 'U.S. Virgin Islands', 'Guam'):
        continue
    st = (p['st'] or '').strip()
    if p['ctry'] == 'Puerto Rico':
        st = 'PR'
    elif p['ctry'] == 'U.S. Virgin Islands':
        st = 'VI'
    elif p['ctry'] == 'Guam':
        st = 'GU'
    if st not in STATES:
        st = FULL2ABBR.get(st.lower(), '')
    if not st:
        skipped_state[p['st']] += 1
        continue
    w = war.get(pid)
    rec = dict(p)
    rec['st'] = st
    rec['war'] = round(war.get(pid, 0.0), 1)
    rec['warBat'] = round(war_bat.get(pid, 0.0), 1)
    rec['warPit'] = round(war_pitch.get(pid, 0.0), 1)
    rec['pa'] = pa.get(pid, 0)
    rec['ip'] = round(ipouts.get(pid, 0) / 3.0, 1)
    rec['peak'] = peak[pid][0] if pid in peak else 0.0
    rec['peakYr'] = peak[pid][1] if pid in peak else ''
    rec['seasons'] = len(years.get(pid, ()))
    rec['hasWar'] = pid in war
    rec['br'] = brid.get(pid, '')
    by_state[st].append(rec)

print('\nunmatched birth states (top 15):', file=sys.stderr)
for k, v in sorted(skipped_state.items(), key=lambda kv: -kv[1])[:15]:
    print(f'   {k!r}: {v}', file=sys.stderr)

TOP_PER_STATE = 120
WAR_FLOOR = 5.0

selected = {}
counts = {}
for st, lst in by_state.items():
    lst.sort(key=lambda r: (-r['war'], -r['pa'], r['name']))
    keep = lst[:TOP_PER_STATE] + [r for r in lst[TOP_PER_STATE:] if r['war'] >= WAR_FLOOR]
    counts[st] = (len(lst), len(keep))
    for r in keep:
        selected[r['id']] = r

print(f'\nstates: {len(by_state)}   selected players: {len(selected)}', file=sys.stderr)
for st in sorted(counts, key=lambda s: -counts[s][0])[:12]:
    print(f'   {st}: {counts[st][0]} born, {counts[st][1]} shipped', file=sys.stderr)
thin = [f'{s}({counts[s][0]})' for s in sorted(counts, key=lambda s: counts[s][0])[:10]]
print('   thinnest:', ', '.join(thin), file=sys.stderr)

json.dump(selected, open('selected.json', 'w'))
print(f'\nwrote selected.json ({len(selected)} players)', file=sys.stderr)
