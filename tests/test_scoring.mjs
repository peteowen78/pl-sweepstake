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

test('accepts pot teams as {name, flag} objects (the app passes its display POTS)', () => {
  const pots = { D: { teams: [{ name: 'Sunderland', flag: '🔴' }], win: 8, draw: 4 } };
  const scoring = makeScoring(pots);
  const results = { f1: { team1: 'Sunderland', team2: 'Wolves', score1: 3, score2: 0, finished: true } };
  assert.equal(scoring.calcTeamPoints('Sunderland', results), 9);
});

test('calcEntryPoints sums the four teams', () => {
  const scoring = makeScoring(ref.pots);
  const results = { f1: { team1: 'Sunderland', team2: 'Wolves', score1: 3, score2: 0, finished: true } };
  // Sunderland (pot D win + bonus) = 9; other three teams played nothing
  const entry = { teams: { A: 'Liverpool', B: 'Brighton', C: 'Everton', D: 'Sunderland' } };
  assert.equal(scoring.calcEntryPoints(entry, results), 9);
});
