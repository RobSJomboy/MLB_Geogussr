# Talkin' Baseball — Geoguessr Lineup Challenge

Remote-control overlay pack for the bit where Trev and Jake play Geoguessr and have to
build a lineup out of it.

**The game:** three minutes on the map. Guess the state you got dropped in and you get to
*pick* any player born there. Miss it and the wheel picks for you — you're stuck with him.
Fill out a traditional NL lineup (C, 1B, 2B, 3B, SS, LF, CF, RF, P), add up the career WAR,
and see how the team fares. Then the reveal: the **best team that could have been built**
from the exact states they visited, and how much WAR they left on the table.

Two pages, same as the Trade Deadline setup — you drive `control.html` from anywhere,
`display.html` goes in an OBS Browser Source, and they talk over an
[ntfy.sh](https://ntfy.sh) topic.

| Page | What it is |
|---|---|
| [`control.html`](control.html) | Host panel. Timer, state picker, player search, scouting reports, random draws, lineup board, final results. |
| [`display.html`](display.html) | The overlay. Transparent 1920×1080, no controls, reads the topic. |
| [`index.html`](index.html) | Landing page with links to both. |
| `players.js` | The data — 6,278 players. |

## Setup

1. Open **control.html** (from GitHub Pages, not a local file — see below).
2. Type a topic name with a random tail so nobody else wanders into it,
   e.g. `jomboy-geo-lineup-7k3x9`. Hit **Connect**.
3. Hit **Copy Display URL**, and paste that into an OBS **Browser Source**:
   width **1920**, height **1080**, and tick *Shutdown source when not visible* off.
4. The **Live Preview** box on the control page is that same display page loaded the same
   way OBS loads it. If it looks right there, it looks right in OBS.

Both pages must be served over http(s). Opening `control.html` as a `file://` path won't
work — the OBS machine can't reach a path on your laptop, and the display URL it copies
would be meaningless. Push to GitHub and turn on Pages (Settings → Pages → deploy from
`main`, root).

## Running a round

1. **START** the timer — it pops up on the overlay and counts down. `Space` starts/pauses,
   `R` resets, **+30s** if you're feeling generous.
2. When they call it, click the state in the grid, then either
   **✅ GOT IT** (they choose) or **❌ MISSED IT** (the wheel chooses). Either one puts the
   state and the verdict on screen right away.
3. *Got it:* search the state's players — the list is ranked by WAR, with position
   eligibility and career span. *Missed it:* pick a draw pool and hit **🎲 ROLL** —
   the overlay runs the slot-machine spin and lands on the guy.
4. Read the **scouting report** on the control page: bio, career line, accolades,
   peak season, and a link straight to his Baseball Reference page. That's your
   "here's who this guy is" copy for whoever's playing.
5. Assign a spot and **LOCK IN**. The board updates and the running WAR total goes up.

Little things that matter on air:

- The **name on screen** is editable. MLB's records carry legal suffixes, so Nolan Ryan is
  filed as "Nolan Ryan Jr." Fix it in the box and the overlay follows.
- The lineup spot is pre-selected from the positions a player *actually played*. If none of
  them are still open, nothing is pre-selected and you get a warning instead — so a second
  baseman never quietly ends up at catcher.
- **🎲 FORCED** marks the players they got stuck with, on the board and in the final.
- Everything survives a page refresh (it's in `localStorage`), so a mid-show reload or an
  OBS source restart doesn't lose the game.

## The finale

- **Reveal Total WAR** — the total, plus a grade ("Legit World Series Team", "Triple-A At Best").
- **Build Best Possible Team** — the optimal lineup from the states they actually visited,
  side by side with theirs, and the WAR gap.

By default the best team obeys the same rule they played by: **one player per state**
(solved exactly, not greedily — it will happily move Honus Wagner to first base if that
frees Pennsylvania up for someone better). Untick the box to let one loaded state fill
several spots.

## The data

`players.js` — **6,278 players** across 50 states, DC, Puerto Rico, the U.S. Virgin Islands
and Guam.

- **Career WAR** from Baseball Reference's public bulk files (`war_daily_bat` + `war_daily_pitch`),
  summed across every season, pitching and hitting.
- **Birthplace, bio, career stats and awards** from the MLB Stats API.
- **Position eligibility** from real career games-by-position: a spot counts if he played at
  least 5% of his games in the field there (minimum 20 games), so Ty Cobb is CF/RF and
  Randy Johnson's single inning in left doesn't make him an outfielder.
- Includes **Negro Leagues players**, who MLB recognized as major leaguers in 2020 and who
  Baseball Reference has WAR for.

Per state we carry the **top 120 by career WAR, plus everyone at 5+ WAR**. So California
ships 604 players and Wyoming ships 17 — the random draw pulls from that pool, not from
literally everyone ever born there. The count is on every state button.

Names come from MLB's own records. Trailing "Sr." is stripped (nobody is introduced that
way); "Jr." is kept, because Ripken Jr. and Griffey Jr. read correctly — and anything that
doesn't is editable per pick.

### Rebuilding the data

Only needed when you want a fresh season folded in. Takes a few minutes and ~50MB of
downloads:

```bash
cd build && python3 fetch_people.py && python3 build_pools.py && python3 fetch_stats.py && python3 fetch_fielding.py && python3 fetch_awards.py && python3 emit.py && mv players.js ..
```

`fetch_people.py` needs `war_daily_bat.txt` and `war_daily_pitch.txt` from
`https://www.baseball-reference.com/data/` in the same folder first.

## A note on ntfy limits

The free ntfy.sh tier rate-limits by IP, and hitting it mid-show freezes the overlay. This
is built to stay well under:

- The control page only sends when something the display is **actually drawing** would
  change — browsing players or fiddling with slots before the reveal costs nothing.
- The timer is **not** resynced on a loop. The overlay counts down on its own, and every
  message carries an absolute deadline so a reloaded OBS source still lands on the right time.
- The overlay leans on SSE and only polls as a slow safety net.

A full nine-round game runs about 45–60 messages. If you do hit the limit, the control page
says so in the bottom bar (it won't fail silently) — wait a minute, or switch to a fresh
topic name. **Force Resync** pushes the current state again if the overlay ever looks stale.

Topics are public to anyone who knows the name, which is why the random tail matters.
