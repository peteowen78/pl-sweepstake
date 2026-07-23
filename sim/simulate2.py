import csv, random, itertools, statistics

POT_TEAMS = {
    'A': ['Liverpool','Arsenal','Man City','Chelsea','Man United'],
    'B': ['Newcastle','Tottenham','Aston Villa','Brighton'],
    'C': ['Crystal Palace',"Nott'm Forest",'Bournemouth','Everton','Fulham','Brentford'],
    'D': ['West Ham','Wolves','Leeds','Burnley','Sunderland'],
}
TEAM_POT = {t: p for p, ts in POT_TEAMS.items() for t in ts}

ORIG  = {'A': (2,1), 'B': (4,2), 'C': (6,3), 'D': (8,4)}   # (win, draw)
TWEAK = {'A': (3,1), 'B': (4,2), 'C': (6,3), 'D': (8,4)}   # Pot A wins worth 3

rows = list(csv.DictReader(open('results2526.csv', encoding='latin-1')))

def season_points(weights):
    pts = {t: 0 for t in TEAM_POT}
    for r in rows:
        h, a = r['HomeTeam'], r['AwayTeam']
        hg, ag = int(r['FTHG']), int(r['FTAG'])
        for team, gf, ga in ((h, hg, ag), (a, ag, hg)):
            w, d = weights[TEAM_POT[team]]
            if gf > ga: pts[team] += w
            elif gf == ga: pts[team] += d
            if gf >= 3: pts[team] += 1
    return pts

orig_pts, tweak_pts = season_points(ORIG), season_points(TWEAK)

random.seed(42)
all_combos = list(itertools.product(*[POT_TEAMS[p] for p in 'ABCD']))
entries = random.sample(all_combos, 70)

o_tot = {e: sum(orig_pts[t] for t in e) for e in entries}
t_tot = {e: sum(tweak_pts[t] for t in e) for e in entries}
o_rank = {e: i+1 for i, e in enumerate(sorted(entries, key=lambda e: -o_tot[e]))}
t_rank = {e: i+1 for i, e in enumerate(sorted(entries, key=lambda e: -t_tot[e]))}

print('=== Pot gaps (best minus worst team in pot) ===')
for p in 'ABCD':
    for name, pts in (('orig', orig_pts), ('tweak', tweak_pts)):
        vals = sorted((pts[t] for t in POT_TEAMS[p]), reverse=True)
        print(f"  Pot {p} {name:5s}: best {vals[0]:3d} worst {vals[-1]:3d} gap {vals[0]-vals[-1]}")

print('\n=== Team points under tweak (Pot A only changes) ===')
for t in POT_TEAMS['A']:
    print(f"  {t:12s} {orig_pts[t]:3d} -> {tweak_pts[t]:3d}")

print('\nRANK | PLAYER    | A-pick / B-pick / C-pick / D-pick | ORIG | TWK | TWK-RANK')
for e in sorted(entries, key=lambda e: -o_tot[e]):
    short = [t.replace('Man United','Man Utd').replace('Crystal Palace','Palace').replace("Nott'm Forest",'Forest').replace('Bournemouth','Bmouth').replace('Sunderland','Sndrlnd').replace('Tottenham','Spurs').replace('Aston Villa','Villa').replace('Newcastle','Ncastle').replace('Brighton','Brightn').replace('Liverpool','Lpool').replace('Brentford','Brentfd').replace('West Ham','WestHam').replace('Chelsea','Chelsea').replace('Burnley','Burnley') for t in e]
    print(f"{o_rank[e]:4d} | Player {o_rank[e]:2d} | {short[0]:8s} {short[1]:8s} {short[2]:8s} {short[3]:8s} | {o_tot[e]:3d} | {t_tot[e]:3d} | {t_rank[e]}")

os_, ts_ = sorted(o_tot.values()), sorted(t_tot.values())
print(f"\nOrig : {os_[0]}-{os_[-1]} (range {os_[-1]-os_[0]}), median {statistics.median(os_)}")
print(f"Tweak: {ts_[0]}-{ts_[-1]} (range {ts_[-1]-ts_[0]}), median {statistics.median(ts_)}")
moves = [abs(o_rank[e]-t_rank[e]) for e in entries]
print(f"Rank movement orig->tweak: max {max(moves)}, avg {sum(moves)/len(moves):.1f}")
