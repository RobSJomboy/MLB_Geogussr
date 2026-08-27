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
| [`control.html`](control.html) | Host panel. Everything on one screen, no scrolling: timer and state grid on the left, player search and scouting report in the middle, lineup, final and live preview on the right. |
| [`display.html`](display.html) | The overlay. Transparent 1920×1080, no controls, reads the topic. The lineup board, the player card and the random-draw spin all share the right-hand side and take turns. |
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

1. **START** the timer — it pops up on the overlay and counts down, and last round's
   state banner comes down with it. `Space` starts/pauses, `R` resets, **+30s** if
   you're feeling generous.
2. When they call it, **click the state in the grid**. That's what puts
   *WHERE THEY LANDED* on screen — and it eases the timer off at the same time,
   resetting it to full for the next round. Then either **✅ GOT IT** (they choose)
   or **❌ MISSED IT** (the wheel chooses), which stamps the verdict onto the banner
   that's already up.
3. *Got it:* search the state's players — the list is ranked by WAR, with position
   eligibility and career span. **Clicking a player puts his card straight on air**,
   so there's no second click between calling the name and showing the guy.
   *Missed it:* pick a draw pool and hit **🎲 ROLL** — the overlay runs the
   slot-machine spin and lands on the guy.
4. Read the **scouting report** on the control page: bio, career line, accolades,
   peak season, and a link straight to his Baseball Reference page. That's your
   "here's who this guy is" copy for whoever's playing.
5. Assign a spot and **LOCK IN**. The board updates and the running WAR total goes up.

**Right state, wrong player.** If they nail the state but name someone who isn't
from there, hit **🎲 Wrong player — draw Top 25 WAR** in the *Got it* panel. The
wheel picks from that state's top 25 by WAR, the overlay explains why
("Right State, Wrong Player"), and the pick is marked forced. The state banner
still reads **GOT IT**, because they did get the state.

**The card takes over the right-hand side.** The player card, the random draw
and the lineup board all live in the same place, so only one is up at a time.
**Show Card** puts the player up big — a full-height portrait panel with the
headshot, career WAR, stat line and accolades — and the lineup board steps
aside for it. Hit it again (it reads **Hide Card**) and the board slides back.
Locking a player in does the same thing automatically: the card eases off and
the board returns with him on it.

**The timer and the state banner trade places.** START brings the clock in and
clears the old banner; clicking the state eases the clock off (resetting it to
full, ready for the next round) and brings the banner in. You never have to hide
or reset either one by hand. The clock holds its last reading on the way out, so
the reset doesn't flash on screen.

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

## Not going down mid-show

The overlay talks to **five independent ntfy servers at once**:

```
ntfy.sh   ntfy.envs.net   ntfy.mzte.de   ntfy.hostux.net   ntfy.adminforge.de
```

Every change is published to all of them and a send counts as delivered the
moment **any one** accepts it. The overlay subscribes to all five and throws away
the duplicates. One server rate-limiting you, timing out, or falling over is a
non-event — during testing, four of the five were killed outright and the overlay
never missed a beat. The dots next to the topic box show which relays are
healthy, and the footer reads e.g. `4 sent · 5/5 relays`.

Why this matters: ntfy's free tier rate-limits per IP, and those limits are *per
host*. Five hosts means five independent budgets and five independent failures.

Everything else is still tuned to keep usage tiny:

- **The preview costs nothing.** The preview iframe runs over a
  `BroadcastChannel`, not the network — instant, free, and it keeps working even
  with every relay down.
- **The overlay doesn't poll.** One long-lived stream per relay. They ping every
  45s, so a request is only spent when that heartbeat actually goes missing.
- **The control page only sends when the overlay's picture would change.**
  Browsing players or fiddling with slots before the reveal costs nothing, and
  bursts of clicks coalesce into one message.
- **The timer is never resynced on a loop.** The overlay counts down on its own,
  and every message carries an absolute deadline so a reloaded OBS source still
  lands on the right time.

Each message carries a clock-based sequence number, so the five copies of the
same change are drawn once, not five times. If every relay somehow refuses at
once, the message goes back in the queue and retries with backoff, always
sending the newest state — nothing is lost and nothing freezes.

**Last resort.** The **Backup URL** button copies a link with the entire game
state packed into it. Paste that into an OBS browser source and the correct
screen paints with no network at all — frozen, but right. Good for the moment
something is badly wrong and you just need the graphic on screen.

Topics are public to anyone who knows the name, which is why the random tail
matters.
