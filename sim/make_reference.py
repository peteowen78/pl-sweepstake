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
