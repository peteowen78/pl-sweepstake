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
