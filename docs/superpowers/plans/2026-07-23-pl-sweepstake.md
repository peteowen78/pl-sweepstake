# PL Sweepstake 2026–27 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Premier League 2026–27 sweepstake web app forked from the WC2026 app, with automatic results via a scheduled GitHub Action pulling the FPL API into Firebase.

**Architecture:** Single-page vanilla JS app (`index.html`) + an extracted pure scoring module (`scoring.js`) shared by the page and Node tests. Firebase Realtime Database holds entries/settings/results; clients compute points locally and re-render on Firebase pushes. A Python script (run by cron GitHub Action) mirrors FPL fixtures/results into Firebase over REST.

**Tech Stack:** Vanilla JS/HTML/CSS (no build step), Firebase RTDB compat SDK 9.23.0, Python 3 stdlib (Action script), Node (test runner via `node --test`), GitHub Actions + Pages.

**Spec:** `Premierleague/docs/superpowers/specs/2026-07-23-Premierleague-design.md`
**Reference app:** `~/Projects/WC2026 Sweepstake/index.html` (2,923 lines — path has a space, always quote it)

---

## File structure

| File | Responsibility |
|---|---|
| `Premierleague/scoring.js` | Pure scoring: pot tables, `calcTeamPoints`, `calcEntryPoints`. No DOM, no Firebase. Works in browser (`<script>`) and Node (`module.exports` guard). |
| `Premierleague/index.html` | The app: views (leaderboard, fixtures, rules, enter, admin), Firebase wiring, rendering. Forked from WC app. |
| `Premierleague/scripts/update_results.py` | Fetch FPL `bootstrap-static` + `fixtures`, transform, write `results` node to Firebase REST. Used by the Action and run manually to seed. Pure-transform function separated for testing. |
| `Premierleague/.github/workflows/update-results.yml` | Hourly cron + manual trigger, runs the script. Lives at repo root of the *deployed* GitHub repo (Premierleague folder is pushed as its own repo). |
| `Premierleague/sim/make_reference.py` | Emits `sim/reference_team_points.json` (per-team 2025–26 totals) from the CSV — the scoring ground truth. |
| `Premierleague/tests/test_scoring.mjs` | Node test: runs `scoring.js` over all 380 real 2025–26 results, compares every team's total to the reference JSON. |
| `Premierleague/tests/test_update_transform.py` | Python test: FPL-fixture-JSON → results-node transform, against a small inline sample. |
| `Premierleague/tests/fpl_sample.json` | Recorded slice of real FPL fixtures API output (3 fixtures: finished, upcoming, postponed-null-kickoff). |
| `Premierleague/README.md` | Setup: Firebase project, deploy repo, Pages, Action, seeding. |

**Canonical team names = FPL names** (from `bootstrap-static` `teams[].name`), used everywhere (pots, results, entries): Arsenal, Aston Villa, Bournemouth, Brentford, Brighton, Chelsea, Coventry City, Crystal Palace, Everton, Fulham, Hull City, Ipswich Town, Leeds, Liverpool, Man City, Man Utd, Newcastle, Nott'm Forest, Spurs, Sunderland. This kills any name-mapping layer.

**Firebase data model** (root node `plsweep2627`):

```
settings: { entryFee: 5, adminPassword: "...", entriesLocked: false }
entries:  { <pushId>: { name, email, teams: {A,B,C,D}, paid, createdAt } }
results:  { f<fplFixtureId>: { team1, team2, score1, score2, gw, kickoff, finished } }
```

- `results` is keyed by FPL fixture id (e.g. `f123`) because PL pairings occur twice a season — team-name keys (WC approach, `fixtureId()` at WC line 2340) would collide. All 380 fixtures are seeded up front with `finished:false, score1:null, score2:null`; the Action flips them as they finish.
- Scoring only counts fixtures where `finished === true` and both scores are numbers.
- The Action is source of truth for `results`; the admin override edits the same keys (an override of a *finished* fixture will be re-overwritten next run — documented in README as "override is for feed outages, correct data at source recovers itself").

**2026–27 pots (spec):**

| Pot | win/draw | Teams (FPL names) |
|---|---|---|
| A | 2/1 | Arsenal, Man City, Liverpool, Man Utd, Chelsea |
| B | 4/2 | Spurs, Aston Villa, Newcastle, Brighton |
| C | 6/3 | Bournemouth, Everton, Brentford, Nott'm Forest, Crystal Palace, Leeds |
| D | 8/4 | Fulham, Sunderland, Coventry City, Ipswich Town, Hull City |

+1 bonus per match where the team scores ≥3. No other bonuses.

---

### Task 1: Reference scoring data (ground truth)

The committed `sim/simulate.py` already computes 2025–26 per-team totals. Extract them to JSON so the JS engine can be tested against real data.

**Files:**
- Create: `Premierleague/sim/make_reference.py`
- Create (generated): `Premierleague/sim/reference_team_points.json`

- [ ] **Step 1: Write the generator**

```python
#!/usr/bin/env python3
"""Emit reference_team_points.json: each 2025-26 team's sweepstake points,
computed from the real results CSV. Ground truth for the JS scoring tests."""
import csv, json, os

HERE = os.path.dirname(os.path.abspath(__file__))

# 2025-26 pots (as used in simulate.py — keep in sync)
POTS = {
    'A': dict(teams=['Liverpool','Arsenal','Man City','Chelsea','Man United'], win=2, draw=1),
    'B': dict(teams=['Newcastle','Tottenham','Aston Villa','Brighton'], win=4, draw=2),
    'C': dict(teams=['Crystal Palace',"Nott'm Forest",'Bournemouth','Everton','Fulham','Brentford'], win=6, draw=3),
    'D': dict(teams=['West Ham','Wolves','Leeds','Burnley','Sunderland'], win=8, draw=4),
}
TEAM_POT = {t: p for p, d in POTS.items() for t in d['teams']}

pts = {t: 0 for t in TEAM_POT}
with open(os.path.join(HERE, 'results2526.csv'), encoding='latin-1') as f:
    rows = list(csv.DictReader(f))
assert len(rows) == 380, f"expected 380 matches, got {len(rows)}"

for r in rows:
    h, a = r['HomeTeam'], r['AwayTeam']
    hg, ag = int(r['FTHG']), int(r['FTAG'])
    for team, gf, ga in ((h, hg, ag), (a, ag, hg)):
        w, d = POTS[TEAM_POT[team]]['win'], POTS[TEAM_POT[team]]['draw']
        if gf > ga: pts[team] += w
        elif gf == ga: pts[team] += d
        if gf >= 3: pts[team] += 1

out = {'pots': {p: d for p, d in POTS.items()}, 'teamPoints': pts}
with open(os.path.join(HERE, 'reference_team_points.json'), 'w') as f:
    json.dump(out, f, indent=2, sort_keys=True)
print('wrote', len(pts), 'teams; Sunderland =', pts['Sunderland'])
```

- [ ] **Step 2: Run it and sanity-check**

Run: `python3 Premierleague/sim/make_reference.py`
Expected output: `wrote 20 teams; Sunderland = 165` (165 matches the validated simulation).

- [ ] **Step 3: Commit**

```bash
git add Premierleague/sim/make_reference.py Premierleague/sim/reference_team_points.json
git commit -m "feat: reference team points from real 2025-26 results"
```

---

### Task 2: `scoring.js` (TDD)

Pure module. The pots are passed in (not hardcoded) so tests use 2025–26 pots while the app uses 2026–27.

**Files:**
- Create: `Premierleague/scoring.js`
- Test: `Premierleague/tests/test_scoring.mjs`

- [ ] **Step 1: Write the failing test**

```js
// tests/test_scoring.mjs — run with: node --test Premierleague/tests/test_scoring.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const { makeScoring } = require(join(HERE, '..', 'scoring.js'));

const ref = JSON.parse(readFileSync(join(HERE, '..', 'sim', 'reference_team_points.json'), 'utf8'));

// Parse the real 2025-26 CSV into the app's results shape
function loadResults() {
  const csv = readFileSync(join(HERE, '..', 'sim', 'results2526.csv'), 'latin1');
  const lines = csv.trim().split(/\r?\n/);
  const header = lines[0].split(',');
  const col = name => header.indexOf(name);
  const [iH, iA, iHG, iAG] = [col('HomeTeam'), col('AwayTeam'), col('FTHG'), col('FTAG')];
  const results = {};
  lines.slice(1).forEach((line, n) => {
    const c = line.split(',');
    results['f' + n] = {
      team1: c[iH], team2: c[iA],
      score1: parseInt(c[iHG], 10), score2: parseInt(c[iAG], 10),
      finished: true,
    };
  });
  assert.equal(Object.keys(results).length, 380);
  return results;
}

test('all 20 team totals match the Python reference over 380 real matches', () => {
  const scoring = makeScoring(ref.pots);
  const results = loadResults();
  for (const [team, expected] of Object.entries(ref.teamPoints)) {
    assert.equal(scoring.calcTeamPoints(team, results), expected, team);
  }
});

test('unfinished and null-score fixtures score nothing', () => {
  const scoring = makeScoring(ref.pots);
  const results = {
    f1: { team1: 'Liverpool', team2: 'Arsenal', score1: 9, score2: 0, finished: false },
    f2: { team1: 'Liverpool', team2: 'Arsenal', score1: null, score2: null, finished: true },
  };
  assert.equal(scoring.calcTeamPoints('Liverpool', results), 0);
});

test('calcEntryPoints sums the four teams', () => {
  const scoring = makeScoring(ref.pots);
  const results = { f1: { team1: 'Sunderland', team2: 'Wolves', score1: 3, score2: 0, finished: true } };
  // Sunderland (pot D win + bonus) = 9; other three teams played nothing
  const entry = { teams: { A: 'Liverpool', B: 'Brighton', C: 'Everton', D: 'Sunderland' } };
  assert.equal(scoring.calcEntryPoints(entry, results), 9);
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `node --test Premierleague/tests/test_scoring.mjs`
Expected: FAIL — `Cannot find module '.../scoring.js'`

- [ ] **Step 3: Implement `scoring.js`**

```js
// scoring.js — pure sweepstake scoring. No DOM, no Firebase.
// Loaded by index.html (browser global `makeScoring`) and by Node tests.
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.makeScoring = factory().makeScoring;
}(typeof self !== 'undefined' ? self : this, function () {

  // pots: { A: {teams:[names...], win, draw}, ... }
  function makeScoring(pots) {
    const teamPot = {};
    for (const [key, pot] of Object.entries(pots)) {
      const teams = Array.isArray(pot.teams) ? pot.teams : [];
      for (const t of teams) teamPot[typeof t === 'string' ? t : t.name] = key;
    }

    function played(r) {
      return r && r.finished === true &&
        Number.isInteger(r.score1) && Number.isInteger(r.score2);
    }

    // results: { id: {team1, team2, score1, score2, finished} }
    function calcTeamPoints(teamName, results) {
      const potKey = teamPot[teamName];
      if (!potKey) return 0;
      const { win, draw } = pots[potKey];
      let pts = 0;
      for (const r of Object.values(results || {})) {
        if (!played(r)) continue;
        const isHome = r.team1 === teamName;
        if (!isHome && r.team2 !== teamName) continue;
        const mine = isHome ? r.score1 : r.score2;
        const theirs = isHome ? r.score2 : r.score1;
        if (mine > theirs) pts += win;
        else if (mine === theirs) pts += draw;
        if (mine >= 3) pts += 1;
      }
      return pts;
    }

    function calcEntryPoints(entry, results) {
      return Object.values((entry && entry.teams) || {})
        .reduce((sum, t) => sum + calcTeamPoints(t, results), 0);
    }

    return { calcTeamPoints, calcEntryPoints, teamPot };
  }

  return { makeScoring };
}));
```

Note: `makeScoring` accepts pot teams as strings **or** `{name, flag}` objects, so `index.html` can pass its display-oriented `POTS` straight in.

- [ ] **Step 4: Run tests to verify they pass**

Run: `node --test Premierleague/tests/test_scoring.mjs`
Expected: `pass 3`, `fail 0`. If any team total mismatches, the failure names the team — debug the engine, not the reference.

- [ ] **Step 5: Commit**

```bash
git add Premierleague/scoring.js Premierleague/tests/test_scoring.mjs
git commit -m "feat: pure scoring engine, verified against 380 real 2025-26 results"
```

---

### Task 3: Fork the app shell

Copy the WC app and do the mechanical PL conversion: data, branding, 4 pots, scoring delegation, strip knockout machinery. After this task the app runs locally in offline-demo mode (no Firebase config yet) with entry form and leaderboard working.

**Files:**
- Create: `Premierleague/index.html` (from `"/Users/peteowen/Projects/WC2026 Sweepstake/index.html"`)

- [ ] **Step 1: Copy the file**

```bash
cp "/Users/peteowen/Projects/WC2026 Sweepstake/index.html" Premierleague/index.html
```

- [ ] **Step 2: Rebrand and rewire config** (WC line references in parentheses)

- `<title>` and header text (~lines 1–20, 1020–1040): "PL Sweepstake 2026/27". Update the hero sub-line (WC 1105) to "Premier League 2026/27 · 20 teams · Aug–May".
- Firebase config block (WC 1304–1312): replace values with placeholder comments (`// PASTE plsweep2627 Firebase config here — see README`) so the app boots in offline-demo mode until Task 9.
- `const ROOT = 'wc2026'` (WC 1321) → `const ROOT = 'plsweep2627'`.
- Add `<script src="scoring.js"></script>` before the main inline script (before WC 1300).

- [ ] **Step 3: Replace the data layer**

- Replace `POTS` (WC 1327–1406) with the four 2026–27 pots from the table above. Keep the same shape `{label, odds, win, draw, teams:[{name, flag}]}`; `label`/`odds` per spec table ("Favourites 7/4–10/1", "Contenders 28/1–300/1", "Dark Horses 500/1–750/1", "Outsiders 1000/1+"). For `flag` use a club-coloured emoji (🔴 Arsenal, 🔵 Chelsea etc. — cosmetic, pick sensibly).
- Delete: `KNOCKOUT_BONUS` (1414), `FIXTURE_DATES` (1417–1526), `KNOCKOUT_FIXTURES` (1534–1570), `GROUP_FIXTURES` (1583–1716), `R32_TEAMS`/`isTeamEliminated`/`eliminationMark` (1790–1832) — replace `eliminationMark(...)` call sites (1990, 2292, 2750) with `''`.
- State (WC 1726–1731): `matches` → `results: {}`, drop `teamRounds`; settings default `{ entryFee: 5, adminPassword: 'plsweep', entriesLocked: false }`.
- Pot E: `selected` (2014) → `{A:null,B:null,C:null,D:null}` (also the two reset sites 2123, 2136); rules view HTML (1109–1119) → four pots' win/draw values plus the +1 bonus line (keep 1120) and a ties line ("ties share positions and split prize money").

- [ ] **Step 4: Delegate scoring**

Replace `calcTeamPoints` (WC 1738–1784) and `calcEntryPoints` (1786–1788) with:

```js
const scoring = makeScoring(POTS);
const calcTeamPoints = (team) => scoring.calcTeamPoints(team, state.results);
const calcEntryPoints = (entry) => scoring.calcEntryPoints(entry, state.results);
```

All render call sites keep working unchanged. Delete `calcMatchPts` (2678–2702) and `renderTeamPointsTable` (2704–2761) plus its container div and `renderAdminPanel` call — the WC matchday/knockout breakdown table doesn't fit a 38-game season (the fixtures view from Task 4 covers per-match detail).

- [ ] **Step 5: Strip remaining knockout/manual-fixture machinery**

Delete functions and their HTML containers/callers: `addMatch` (2172–2208), `renderMatchLog` (2210–2228), `renderTeamStatusGrid`/`setTeamRound` (2240–2278), `renderGroupTabs`/`switchGroupTab`/`renderGroupFixtures` (2348–2409), `switchScoreView`/`renderDateTabs`/`switchDateTab`/`renderDateFixtures` (2429–2507), `knockoutFixturePlayed`/`renderKnockoutFixtures`/`saveKnockoutFixture`/`findMatchForFixture` (2509–2514, 2763–2851), `buildMatchdayLookup` (2657–2676), `fixtureId` (2340–2346). Trim `renderAdminPanel` (2853–2863) to `admin-fee` + entries list (fixture override is rebuilt in Task 4). Update Firebase listeners (2868–2895): `matches` listener → `results`, drop `teamRounds` listener. Rework `renderNextMatches`/`renderRecentMatches` (2516–2655) to read `state.results` (kickoff-sorted; next = not finished, recent = finished — details in Task 4).

- [ ] **Step 6: Rebuild the entry form markup**

⚠️ The WC file's `#view-enter` (WC 1094–1099) now holds only a static "Entries Are Closed" notice — the form HTML was deleted when WC entries closed. The entry-form **JS** survives intact (`buildPotPickers` 2016, `selectTeam` 2040, `updateEntryForm` 2058, `submitEntry` 2099) and the CSS still exists (`.entry-summary` 622–641, `.team-grid`/`.team-btn` 529–573). Reconstruct inside `#view-enter`:

```html
<div class="section-title">Enter the Sweepstake</div>
<div class="section-sub">£<span id="fee-display-entry">5</span> entry · pick one team from each pot</div>
<!-- id must start with "fee-display" — the settings listener (WC 2892) auto-updates all such spans -->
<label class="form-label" for="entry-name">Your name</label>
<input type="text" class="form-input" id="entry-name" placeholder="Name" oninput="updateEntryForm()">
<div id="pot-pickers"></div>
<div id="entry-summary" style="display:none">
  <div class="card-title">Your entry</div>
  <div class="entry-summary-row"><span class="entry-summary-label">Name</span><span class="entry-summary-value" id="summary-name">—</span></div>
  <div id="summary-teams"></div>
  <div class="entry-summary-row"><span class="entry-summary-label">Entry fee</span><span class="entry-summary-value">£<span id="summary-fee">5</span></span></div>
</div>
<button class="btn-primary" id="submit-btn" disabled onclick="submitEntry()">Submit entry →</button>
```

(Match surrounding class names/ids exactly — the JS looks these ids up.) Wire `buildPotPickers()` + `updateEntryForm()` into page init (next to `initFirebaseListeners()` at WC 2919) so the pots render on load, not only after a submit.

- [ ] **Step 7: Verify in the browser**

Serve: `npx serve Premierleague` and open it (or use the preview browser). Check: no console errors; entry form shows exactly 4 pots/20 teams; submitting an offline-demo entry shows it on the leaderboard with 0 pts; rules view shows PL pots.
Expected: clean console (Firebase init warning is fine pre-config).

- [ ] **Step 8: Commit**

```bash
git add Premierleague/index.html
git commit -m "feat: fork WC app as PL sweepstake shell (4 pots, results-driven scoring)"
```

---

### Task 4: Gameweek fixtures view + admin override

**Files:**
- Modify: `Premierleague/index.html`

- [ ] **Step 1: Public "Fixtures" view** — new nav tab + view div. Gameweek tab strip (GW1–38, current GW auto-selected = first GW with an unfinished fixture; ✓ on complete GWs, à la WC `renderGroupTabs`). Each fixture row: kickoff (`toLocaleDateString('en-GB', {weekday:'short', day:'numeric', month:'short'})` + `toLocaleTimeString('en-GB', {hour:'2-digit', minute:'2-digit'})` — kickoffs are UTC ISO strings, local rendering handles BST), teams with pot-coloured tags, score if finished else "v". Read-only.
- [ ] **Step 2: Admin override** — in the admin panel, reuse the same GW tab strip but render each row with score inputs + Save (adapting WC `saveFixture` 2411–2427): writes `{score1, score2, finished:true}` to `results/f<id>` via `dbRef`. Include a "clear result" button (sets scores null, `finished:false`). Note next to the section: "Feed overwrites overrides for fixtures FPL marks finished — use for outages only."
- [ ] **Step 3: Leaderboard widgets** — `renderNextMatches`: next 4 by kickoff where `!finished`; `renderRecentMatches`: last 4 finished by kickoff. Both from `state.results`; delete WC's `FIXTURE_DATES` lookups (`findFixtureDateTime`).
- [ ] **Step 4: Verify** — temporarily hand-seed `state.results` in the console with 3 fake fixtures (one finished): fixtures view renders GW tabs, admin override saves locally, leaderboard team tags show points. Screenshot for the record.
- [ ] **Step 5: Commit** — `git commit -m "feat: gameweek fixtures view with admin override"`

---

### Task 5: Entry form — email, privacy note, entry lock

**Files:**
- Modify: `Premierleague/index.html`

- [ ] **Step 1: Email field** — in the entry form rebuilt in Task 3 Step 6, directly below the `#entry-name` input: `<input type="email" class="form-input" id="entry-email" placeholder="Email" oninput="updateEntryForm()">` + privacy line "Your email is only used for game updates." Extend `updateEntryForm` (2058) and `submitEntry` (2099): require `/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)`; store `email` on the entry. One email may cover multiple entries — no uniqueness check on email (only on the team combination, `isDuplicateEntry` 2087 unchanged).
- [ ] **Step 2: Entry lock** — in `submitEntry` and on the Enter view: if `state.settings.entriesLocked`, show "Entries are closed — the season has started" and hide the form. Admin toggle button writes `settings.entriesLocked` via `saveSetting` (2165).
- [ ] **Step 3: Verify** — browser: submit blocked without valid email; toggling lock in admin hides/shows the form live in a second tab (offline mode: same tab re-render is enough).
- [ ] **Step 4: Commit** — `git commit -m "feat: entry email, privacy note, entry lock"`

---

### Task 6: Admin entries list — emails + copy-all

**Files:**
- Modify: `Premierleague/index.html` (`renderAdminEntries`, WC 2280–2310)

- [ ] **Step 1:** Show `e.email` under each entry name (admin only — the public leaderboard never renders email). Add a "📋 Copy all emails" button above the list:

```js
function copyAllEmails() {
  const emails = [...new Set(Object.values(state.entries)
    .map(e => (e.email || '').trim().toLowerCase()).filter(Boolean))];
  navigator.clipboard.writeText(emails.join(', '))
    .then(() => toast(`${emails.length} unique emails copied`, 'success'))
    .catch(() => prompt('Copy emails:', emails.join(', ')));
}
```

- [ ] **Step 2: Verify** — two offline entries sharing an email → button copies 1 address, toast says "1 unique emails copied".
- [ ] **Step 3: Commit** — `git commit -m "feat: admin email list with dedup copy-all"`

---

### Task 7: FPL → Firebase update script (TDD on the transform)

**Files:**
- Create: `Premierleague/scripts/update_results.py`
- Test: `Premierleague/tests/test_update_transform.py`
- Create: `Premierleague/tests/fpl_sample.json`

- [ ] **Step 1: Record the sample** — `curl -s "https://fantasy.premierleague.com/api/fixtures/" -H "User-Agent: Mozilla/5.0" | python3 -c "import json,sys; d=json.load(sys.stdin); print(json.dumps(d[:3], indent=2))" > Premierleague/tests/fpl_sample.json`. Then hand-edit: give fixture 1 `finished:true, team_h_score:2, team_a_score:1`; fixture 3 `event:null, kickoff_time:null` (postponed shape).

- [ ] **Step 2: Write the failing test**

```python
# tests/test_update_transform.py — run with: python3 -m unittest discover -s Premierleague/tests
import json, os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
from update_results import transform

TEAMS = {i: n for i, n in enumerate([
    'Arsenal','Aston Villa','Bournemouth','Brentford','Brighton','Chelsea',
    'Coventry City','Crystal Palace','Everton','Fulham','Hull City','Ipswich Town',
    'Leeds','Liverpool','Man City','Man Utd','Newcastle',"Nott'm Forest",
    'Spurs','Sunderland'], start=1)}

class TransformTest(unittest.TestCase):
    def setUp(self):
        here = os.path.dirname(__file__)
        with open(os.path.join(here, 'fpl_sample.json')) as f:
            self.fixtures = json.load(f)

    def test_all_fixtures_present_keyed_by_id(self):
        out = transform(self.fixtures, TEAMS)
        self.assertEqual(set(out), {'f' + str(f['id']) for f in self.fixtures})

    def test_finished_fixture_carries_scores(self):
        out = transform(self.fixtures, TEAMS)
        done = out['f' + str(self.fixtures[0]['id'])]
        self.assertTrue(done['finished'])
        self.assertEqual((done['score1'], done['score2']), (2, 1))
        self.assertEqual(done['team1'], TEAMS[self.fixtures[0]['team_h']])

    def test_unfinished_fixture_has_null_scores(self):
        out = transform(self.fixtures, TEAMS)
        pending = out['f' + str(self.fixtures[1]['id'])]
        self.assertFalse(pending['finished'])
        self.assertIsNone(pending['score1'])

    def test_finished_without_scores_treated_unfinished(self):
        broken = [dict(self.fixtures[0], team_h_score=None)]
        out = transform(broken, TEAMS)
        self.assertFalse(out['f' + str(broken[0]['id'])]['finished'])
```

Run: `python3 -m unittest discover -s Premierleague/tests` → FAIL (`No module named 'update_results'`).

- [ ] **Step 3: Implement**

```python
#!/usr/bin/env python3
"""Mirror FPL fixtures/results into the sweepstake's Firebase RTDB.

Usage: FIREBASE_DB_URL=https://<project>-default-rtdb.<region>.firebasedatabase.app \
       python3 update_results.py
Writes to <FIREBASE_DB_URL>/plsweep2627/results.json (open-rules DB; no auth).
Stdlib only — safe to run in a bare GitHub Actions python.
"""
import json, os, sys, urllib.request

API = 'https://fantasy.premierleague.com/api/'
UA = {'User-Agent': 'Mozilla/5.0 (Premierleague results mirror)'}

def fetch(path):
    req = urllib.request.Request(API + path, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def transform(fixtures, team_names):
    """FPL fixtures list -> {f<id>: {team1, team2, score1, score2, gw, kickoff, finished}}"""
    out = {}
    for f in fixtures:
        finished = bool(f.get('finished')) and \
            f.get('team_h_score') is not None and f.get('team_a_score') is not None
        out['f%d' % f['id']] = {
            'team1': team_names[f['team_h']],
            'team2': team_names[f['team_a']],
            'score1': f['team_h_score'] if finished else None,
            'score2': f['team_a_score'] if finished else None,
            'gw': f.get('event'),          # None while postponed/unscheduled
            'kickoff': f.get('kickoff_time'),
            'finished': finished,
        }
    return out

def main():
    db_url = os.environ.get('FIREBASE_DB_URL', '').rstrip('/')
    if not db_url:
        sys.exit('FIREBASE_DB_URL env var is required')
    teams = {t['id']: t['name'] for t in fetch('bootstrap-static/')['teams']}
    results = transform(fetch('fixtures/'), teams)
    if len(results) < 380:
        sys.exit('refusing to write: only %d fixtures returned' % len(results))
    body = json.dumps(results).encode()
    req = urllib.request.Request(
        db_url + '/plsweep2627/results.json', data=body, method='PUT',
        headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as r:
        r.read()
    done = sum(1 for v in results.values() if v['finished'])
    print('wrote %d fixtures (%d finished)' % (len(results), done))

if __name__ == '__main__':
    main()
```

Design notes: full `PUT` of the whole `results` node each run keeps the mirror exact and idempotent (spec: "a result is only written once the API marks the fixture finished" — the `finished` guard does that); the `< 380` check is the "never overwrite with blanks" protection against a half-broken API response. Team ids come fresh from `bootstrap-static` each run, so no hardcoded id map to rot.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest discover -s Premierleague/tests` → `OK (4 tests)`.

- [ ] **Step 5: Commit**

```bash
git add Premierleague/scripts/update_results.py Premierleague/tests/test_update_transform.py Premierleague/tests/fpl_sample.json
git commit -m "feat: FPL results mirror script with tested transform"
```

---

### Task 8: GitHub Action workflow

**Files:**
- Create: `Premierleague/.github/workflows/update-results.yml`

- [ ] **Step 1: Write it**

```yaml
name: Update results
on:
  schedule:
    - cron: '15 * * * *'   # hourly at :15 UTC
  workflow_dispatch: {}     # manual "run now" button
jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Mirror FPL results into Firebase
        env:
          FIREBASE_DB_URL: ${{ vars.FIREBASE_DB_URL }}
        run: python3 scripts/update_results.py
```

Notes: paths are relative to the *deployed* repo root (this folder is pushed as its own GitHub repo — Task 10). `FIREBASE_DB_URL` is a repo **variable**, not a secret (it's already public inside index.html). Scheduled workflows pause after 60 days without repo activity — README documents the one-click "Enable" if GitHub emails about it.

- [ ] **Step 2: Validate syntax** — `python3 -c "import yaml,sys; yaml.safe_load(open('Premierleague/.github/workflows/update-results.yml')); print('yaml ok')"` (PyYAML is present on macOS system python; if not, `npx yaml-lint` or eyeball it — real validation happens on first push).
- [ ] **Step 3: Commit** — `git commit -m "feat: hourly results workflow"`

---

### Task 9: README + Firebase project (human-gated)

**Files:**
- Create: `Premierleague/README.md`

- [ ] **Step 1: Write README** covering: what it is (link spec); local dev (`npx serve Premierleague`); tests (`node --test Premierleague/tests/test_scoring.mjs` and `python3 -m unittest discover -s Premierleague/tests`); **Firebase setup** (console.firebase.google.com → new project `Premierleague` → Realtime Database, europe-west1, start in *test mode*, rules `.read: true, .write: true` with the spec's trust-model caveat quoted → project settings → web app → paste config into index.html); **seeding** (`FIREBASE_DB_URL=... python3 Premierleague/scripts/update_results.py` — writes all 380 fixtures); **deploy** (Task 10 steps); **the override caveat** (feed re-overwrites finished fixtures); **backup feed** (football-data.org free tier is the documented fallback source if the FPL API changes shape — swapping it in means a new `transform()` only); **no-credential note** (the Action writes without auth by design — the spec's open-writes trust model; the DB URL repo variable is already public in the page).
- [ ] **Step 2: Commit** — `git commit -m "docs: setup and ops README"`
- [ ] **Step 3: Pete creates the Firebase project** following the README, pastes the config into `index.html`, commits. ⚠️ **Blocked on Pete** — everything before this works offline; ask him to do this step (needs his Google account), or pair on it in a session with browser access to his account.

---

### Task 10: Seed, end-to-end verify, deploy

- [ ] **Step 1: Seed fixtures** — run the script with the real `FIREBASE_DB_URL`. Expected: `wrote 380 fixtures (0 finished)`.
- [ ] **Step 2: Live E2E** — serve locally with real config: fixtures view shows GW1–38 with kickoff times; submit a real test entry (then delete it in admin); simulate a result — `curl -X PATCH "$FIREBASE_DB_URL/plsweep2627/results/f1.json" -d '{"score1":3,"score2":0,"finished":true}'` — and watch the open leaderboard/fixtures update **without reloading**; confirm points match pots by hand; then re-run the seed script (Step 1), which resets f1 to unfinished — proving feed self-healing.
- [ ] **Step 3: Create deploy repo** (with Pete's go-ahead): `gh repo create Premierleague --public`; push the `Premierleague/` folder contents as repo root (`git subtree split` or a plain copy-push); enable Pages (deploy from branch, root); set repo variable `FIREBASE_DB_URL`; run the workflow once via "Run workflow" and check the Actions log shows `wrote 380 fixtures`.
- [ ] **Step 4: Verify live site** — open the Pages URL on desktop + phone width; console clean; entry flow works. Screenshot proof.
- [ ] **Step 5: Update memory** — mark project live in `Premierleague` memory file; note the deploy repo URL.

---

## Post-plan follow-ups (not in this plan)

- Run `superpowers:requesting-code-review` before merging the branch.
- August: confirm pots against final odds before the draw; lock entries at first kickoff (Fri 14 Aug 2026 expected).
