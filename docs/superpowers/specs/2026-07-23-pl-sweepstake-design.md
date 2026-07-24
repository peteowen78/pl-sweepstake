# Premier League Sweepstake 2026–27 — Design Spec

**Date:** 2026-07-23
**Status:** Draft for review
**Based on:** the WC2026 Sweepstake app (`~/Projects/WC2026 Sweepstake/index.html`)

## Overview

A season-long sweepstake for the 2026–27 Premier League, adapted from the proven
World Cup 2026 sweepstake app. Each player picks one team from each of four pots
(pots set by pre-season title odds). Teams earn sweepstake points from every real
match all season; the leaderboard updates automatically from a live results feed —
no manual score entry.

The format was validated by simulating the full 2025–26 season (380 real results,
70 entries): scores spread 296–456 with a single outright winner and a two-point
gap at the top. See "Simulation findings" below.

## Game rules

### Pots (from title odds at July 2026)

| Pot | Teams | Win | Draw |
|-----|-------|-----|------|
| A | Arsenal, Man City, Liverpool, Man Utd, Chelsea | 2 | 1 |
| B | Tottenham, Aston Villa, Newcastle, Brighton | 4 | 2 |
| C | Bournemouth, Everton, Brentford, Nott'm Forest, Crystal Palace, Leeds, Fulham | 6 | 3 |
| D | Sunderland, Coventry, Ipswich, Hull | 8 | 4 |

(Fulham moved C-ward 24 Jul 2026 after a multi-source odds check — priced 500/1,
level with Leeds/Palace, not with the 750/1+ outsiders. Pots now 5/4/7/4 = 560
combinations.)

Pots may be re-checked against the odds just before the draw closes; the table
is finalised at draw time and the app is built from the final table (combination
counts below assume the sizes shown). Pot sizes are intentionally uneven
(5/4/6/5).

### Scoring

- Win: pot win value (2/4/6/8). Draw: pot draw value (1/2/3/4). Loss: 0.
- **Bonus:** +1 point any time one of your teams scores 3 or more goals in a
  single match (win, draw or lose).
- No other bonuses — no season-end, position or knockout bonuses (mirrors how
  the WC game was actually played).
- A player's total = sum of their four teams' points across all 380 fixtures.
- **Ties:** shown as shared positions on the leaderboard; tied prize positions
  split the money (settled offline). No in-app tiebreaker.

### Entries

- Each player picks **one team from each pot** (4 teams per entry).
- The same team may appear in any number of entries, but no two entries may be
  the identical four-team combination (enforced at entry time, as in the WC app).
- 600 unique combinations exist (5×4×6×5); expected field is ~70 players.
- Entry fee and prize split configurable in admin (same as WC app).
- **Email:** each entry includes the player's email address (required at entry
  time, basic format validation). Shown only in the admin entries list, with a
  "copy all emails" button so periodic updates can be sent from Pete's own
  email account. The app itself sends no email (no mail service integration).
  One email may cover multiple entries (a player buying several combinations);
  the copy-all list de-duplicates. The entry form carries a one-line privacy
  note ("your email is only used for game updates").
- **Entry lock:** an admin toggle closes the entry form (intended use: lock at
  first kickoff of the season). New in this version — the WC app had no lock.
  Like the admin password, it is a client-side gate under the open-writes trust
  model (see Security).

## App architecture

A fork of the WC2026 single-page app, keeping its proven structure:

- **One `index.html`** (vanilla JS + CSS, no build step), hosted on GitHub Pages.
- **Firebase Realtime Database** (same pattern as WC app, new Firebase project):
  stores entries, settings, and match results. Clients recalculate all points
  locally from raw results; the leaderboard updates live via Firebase's
  real-time sync.
- **Views:** Leaderboard · Fixtures/Results · Rules · Entry form · Admin.
- **Removed from WC version:** knockout rounds/bracket, groups, fifth pot,
  penalty-shootout logic, GMT kickoff conversions specific to WC venues.
- **Changed:** 380-fixture season calendar (grouped by gameweek), 20 PL teams
  with club colours/crest emoji, 4 pots.

New folder `Premierleague/` in `~/Projects` (this repo), published via GitHub
Pages like the AT Moores quote app.

## Automatic results (the new part)

- **Source:** Fantasy Premier League public API
  (`fantasy.premierleague.com/api/fixtures/` + `bootstrap-static/`) — free, no
  key, covers every PL fixture with kickoff times and final scores. Verified
  reachable; it has already rolled over to 2026–27 (0 played fixtures, all 20
  teams correct).
- **Pipeline:** a scheduled **GitHub Action** (cron, roughly hourly on match
  days) fetches fixtures/results and writes raw scores into Firebase via its
  REST API. Under the open-writes trust model no credential is needed; the
  database URL is a GitHub Actions repo variable (it is public in the page
  anyway). The Action only mirrors raw data; all points logic stays
  client-side.
- **Fallback:** the admin panel keeps manual score entry/override, so a feed
  outage never blocks the game. football-data.org (free tier) is the documented
  backup source if the FPL API changes.
- **Failure behaviour:** if a fetch fails, the Action exits non-zero (visible in
  the repo's Actions tab) and simply retries on the next scheduled run; existing
  data in Firebase is never overwritten with blanks. A result is only written
  once the API marks the fixture finished.

## Security / config

- Firebase config is public in the page (normal for client-side Firebase).
- **Trust model: same as the WC app.** The admin password is a client-side UI
  gate only; database writes are open to app users (anonymous Firebase auth),
  exactly as in the World Cup game. This is a deliberate choice for a friendly
  sweepstake among known players — accepted risk, not an oversight. The GitHub
  Action writes results over the same open-rules REST API (no credential).
- Optional future hardening (out of scope for v1): a real Firebase Auth admin
  account with rules restricting results/settings writes.
- **Emails:** entrant emails are stored in the same open database, so they are
  technically readable by anyone with the app (the UI hides them outside
  admin). Accepted under the same friendly-game trust model; noted so it's a
  known choice.

## Testing

- Unit-testable scoring function: the 2025–26 CSV + simulation scripts are
  committed under `Premierleague/sim/` and serve as the reference
  implementation — a regression check confirms the app's scoring matches them
  for all 380 matches.
- Manual test plan: enter test entries, inject a fake finished fixture into
  Firebase, confirm leaderboard updates without reload.

## Simulation findings (2025–26 season, real results)

- 70 entries: min 296, max 456, median 381; single winner, 2-point margin.
- Pot D pick dominates (best-to-worst gap 96 pts vs 25 for Pot A); all podium
  entries held Sunderland. This is accepted as a feature of the format.
- A tested variant (Pot A wins = 3) moved players on average 1.9 rank places —
  not worth the added explanation. Original scoring retained.

## Known constraints

- The FPL API's 2026–27 fixture list is live now, but scores obviously only
  flow once the season starts (mid-August 2026).
- If a match is abandoned/replayed, the feed reflects whatever the FPL API
  publishes; admin override covers edge cases.

## Out of scope

- User accounts/logins for players (entries are name-based, as in the WC app).
- Payments — entry fees collected offline, admin marks entries paid.
- Native app / notifications.
- Automated email sending — the app only collects addresses; mail goes out
  manually via the admin "copy all emails" list.
