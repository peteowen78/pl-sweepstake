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
        # finished_provisional flips at full time; FPL's plain `finished` can
        # lag it by hours (it waits on bonus confirmation, which we don't use).
        done_flag = bool(f.get('finished') or f.get('finished_provisional'))
        finished = done_flag and \
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
