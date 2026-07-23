import csv, random, itertools, statistics

# Pots as they'd have been drawn in Aug 2025, from pre-season title odds.
# Same shape as Pete's 2026-27 split (5/4/6/5).
POTS = {
    'A': dict(teams=['Liverpool','Arsenal','Man City','Chelsea','Man United'], win=2, draw=1),
    'B': dict(teams=['Newcastle','Tottenham','Aston Villa','Brighton'], win=4, draw=2),
    'C': dict(teams=['Crystal Palace',"Nott'm Forest",'Bournemouth','Everton','Fulham','Brentford'], win=6, draw=3),
    'D': dict(teams=['West Ham','Wolves','Leeds','Burnley','Sunderland'], win=8, draw=4),
}
TEAM_POT = {t: p for p, d in POTS.items() for t in d['teams']}

rows = list(csv.DictReader(open('results2526.csv', encoding='latin-1')))
assert len(rows) == 380

pts = {t: 0 for t in TEAM_POT}          # sweepstake points
bonus_count = {t: 0 for t in TEAM_POT}
real = {t: dict(P=0, W=0, D=0, L=0, GF=0, GA=0) for t in TEAM_POT}

for r in rows:
    h, a = r['HomeTeam'], r['AwayTeam']
    hg, ag = int(r['FTHG']), int(r['FTAG'])
    for team, gf, ga in ((h, hg, ag), (a, ag, hg)):
        pot = POTS[TEAM_POT[team]]
        if gf > ga:
            pts[team] += pot['win']; real[team]['W'] += 1; real[team]['P'] += 3
        elif gf == ga:
            pts[team] += pot['draw']; real[team]['D'] += 1; real[team]['P'] += 1
        else:
            real[team]['L'] += 1
        if gf >= 3:
            pts[team] += 1; bonus_count[team] += 1
        real[team]['GF'] += gf; real[team]['GA'] += ga

# Real league table for context
table = sorted(real.items(), key=lambda kv: (-kv[1]['P'], -(kv[1]['GF']-kv[1]['GA']), -kv[1]['GF']))
print('=== Real 2025-26 final table (top 6 / bottom 4) ===')
for i, (t, s) in enumerate(table, 1):
    if i <= 6 or i >= 17:
        print(f"{i:2d}. {t:16s} {s['P']:3d}pts  GD {s['GF']-s['GA']:+d}")

print('\n=== Sweepstake points per team (pot, swpts, of which 3+goal bonuses) ===')
for t, p in sorted(pts.items(), key=lambda kv: -kv[1]):
    print(f"  Pot {TEAM_POT[t]}  {t:16s} {p:3d}  (bonus {bonus_count[t]:2d})")

# 70 unique entries, one team per pot
random.seed(42)
all_combos = list(itertools.product(*[POTS[p]['teams'] for p in 'ABCD']))
entries = random.sample(all_combos, 70)
totals = sorted((sum(pts[t] for t in e), e) for e in entries)

scores = [s for s, _ in totals]
print('\n=== 70-entry simulation ===')
print(f"Winner: {totals[-1][0]} pts  {totals[-1][1]}")
print(f"2nd:    {totals[-2][0]} pts  {totals[-2][1]}")
print(f"3rd:    {totals[-3][0]} pts  {totals[-3][1]}")
print(f"Last:   {totals[0][0]} pts  {totals[0][1]}")
print(f"Spread: {min(scores)}-{max(scores)}  (range {max(scores)-min(scores)}), median {statistics.median(scores)}")
best = max(all_combos, key=lambda e: sum(pts[t] for t in e))
print(f"Best possible combo: {sum(pts[t] for t in best)} pts  {best}")

# How many distinct scores / ties at the top
from collections import Counter
c = Counter(scores)
top_score = max(scores)
print(f"Tied at top: {c[top_score]} entries")

# Which pot decides the game: spread of team points within each pot
print('\n=== Points spread inside each pot (best team vs worst) ===')
for p, d in POTS.items():
    vals = sorted((pts[t] for t in d['teams']), reverse=True)
    print(f"  Pot {p}: best {vals[0]}, worst {vals[-1]}, gap {vals[0]-vals[-1]}")

# Histogram
print('\n=== Score distribution (70 entries) ===')
lo = min(scores) // 10 * 10
for b in range(lo, max(scores) + 10, 10):
    n = sum(1 for s in scores if b <= s < b + 10)
    if n: print(f"  {b:3d}-{b+9:3d}  {'#' * n} {n}")
