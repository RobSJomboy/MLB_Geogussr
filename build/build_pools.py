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
team_years = defaultdict(lambda: defaultdict(set))   # mlb_ID -> team -> {years}
# era split: the live ball era starts in 1920
LIVE_BALL_FROM = 1920
era_seasons = defaultdict(lambda: [set(), set()])    # mlb_ID -> [dead years, live years]
era_time = defaultdict(lambda: [0, 0])               # mlb_ID -> [dead, live] PA + IPouts
peak = defaultdict(lambda: (0.0, ''))   # best single season

def num(v):
    if v in ('', 'NULL', None):
        return 0.0
    try:
        return float(v)
    except ValueError:
        return 0.0

def resolve_aliases():
    """Baseball Reference leaves mlb_ID NULL for some players — every Negro
    Leagues great among them — and this whole join runs on mlb_ID, so they were
    being dropped silently: Josh Gibson, Bullet Rogan, Turkey Stearnes, Oscar
    Charleston, Cool Papa Bell. Match those rows to StatsAPI by name, accepting
    only an unambiguous single name match whose career overlaps, and carry them
    in under the right id.
    """
    by_name = defaultdict(list)
    for pid, p in people.items():
        by_name[p['name']].append(pid)

    orphan = {}                      # bbref id -> [name, {years}]
    for path in ('war_bat.txt', 'war_pitch.txt'):
        with open(path, newline='', encoding='utf-8', errors='replace') as f:
            for row in csv.DictReader(f):
                mid = (row.get('mlb_ID') or '').strip()
                if mid and mid != 'NULL':
                    continue
                bb = (row.get('player_ID') or '').strip()
                if not bb:
                    continue
                e = orphan.setdefault(bb, [row.get('name_common', ''), set()])
                yr = (row.get('year_ID') or '').strip()
                if yr.isdigit():
                    e[1].add(int(yr))

    alias, skipped = {}, 0
    for bb, (name, yrs) in orphan.items():
        cands = by_name.get(name, [])
        if len(cands) != 1 or not yrs:
            skipped += 1
            continue
        pid = cands[0]
        p = people[pid]
        debut = int(p['debut']) if (p.get('debut') or '').isdigit() else None
        last = int(p['last']) if (p.get('last') or '').isdigit() else None
        # the two records have to describe the same career, not just the same name
        if debut and last and not (min(yrs) <= last + 2 and max(yrs) >= debut - 2):
            skipped += 1
            continue
        alias[bb] = pid
    print(f'recovered {len(alias)} players with a NULL mlb_ID '
          f'({skipped} left unmatched)', file=sys.stderr)
    return alias


ALIAS = {}


def mlb_id(row):
    """mlb_ID, falling back to a name-resolved alias for the NULL rows."""
    mid = (row.get('mlb_ID') or '').strip()
    if mid and mid != 'NULL':
        return mid
    return ALIAS.get((row.get('player_ID') or '').strip(), '')


def load(path, is_pitch):
    n = 0
    with open(path, newline='', encoding='utf-8', errors='replace') as f:
        for row in csv.DictReader(f):
            mid = mlb_id(row)
            if not mid:
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
            tm = (row.get('team_ID') or '').strip()
            if tm and tm != 'NULL' and yr.isdigit():
                team_years[mid][tm].add(int(yr))
            if yr.isdigit():
                era = 1 if int(yr) >= LIVE_BALL_FROM else 0
                era_seasons[mid][era].add(int(yr))
                era_time[mid][era] += int(num(row.get('IPouts'))) if is_pitch else int(num(row.get('PA')))
            n += 1
    print(f'{path}: {n} season-stints', file=sys.stderr)

ALIAS = resolve_aliases()
load('war_bat.txt', False)
load('war_pitch.txt', True)

# peak season = best combined WAR in a single year
season_war = defaultdict(lambda: defaultdict(float))
for path, in (('war_bat.txt',), ('war_pitch.txt',)):
    with open(path, newline='', encoding='utf-8', errors='replace') as f:
        for row in csv.DictReader(f):
            mid = mlb_id(row)
            yr = (row.get('year_ID') or '').strip()
            if mid and yr:
                season_war[mid][yr] += num(row.get('WAR'))
for mid, ys in season_war.items():
    y, w = max(ys.items(), key=lambda kv: kv[1])
    peak[mid] = (round(w, 1), y)

def span(ys):
    a, b = min(ys), max(ys)
    if a == b:
        return str(a)
    # short end year unless the century turned over: 1920-34, but 1998-2003
    return f'{a}-{b % 100:02d}' if a // 100 == b // 100 else f'{a}-{b}'

def is_live_ball(mid):
    """Most of his career in the live ball era (1920 on).

    Measured in playing time (plate appearances for hitters, outs recorded for
    pitchers) rather than season count. Counting seasons calls Grover Alexander
    a live ball pitcher on 11 seasons to 9, when he threw more innings and
    earned more of his WAR before 1920 — he is a dead ball great. Season count
    only breaks an exact tie.

    Ruth (1914-35) and Hornsby (1915-37) are in; Cobb, Speaker, Walter Johnson,
    Eddie Collins and every pre-1920 star is out. Negro Leagues play is
    1920-1948 in MLB's records, so those men are live ball throughout.
    """
    dt, lt = era_time.get(mid, [0, 0])
    if lt != dt:
        return lt > dt
    dead, live = era_seasons.get(mid, [set(), set()])
    return len(live) > len(dead)


def team_list(mid):
    tms = team_years.get(mid)
    if not tms:
        return []
    # chronological by first season, longest stint first on ties
    ordered = sorted(tms.items(), key=lambda kv: (min(kv[1]), -len(kv[1])))
    return [f'{t} {span(ys)}' for t, ys in ordered][:10]

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
dead_ball = 0
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
    if not is_live_ball(pid):
        dead_ball += 1
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
    rec['tm'] = team_list(pid)
    by_state[st].append(rec)

print(f'\ndropped as pre-live-ball: {dead_ball}', file=sys.stderr)
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
