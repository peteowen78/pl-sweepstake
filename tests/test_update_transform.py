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

    def test_provisionally_finished_fixture_counts(self):
        # FPL can leave finished=false for hours after full time while
        # finished_provisional=true (bonus not confirmed). The score is what
        # we mirror, so provisional must count. Seen live: GW1 2026-27.
        prov = [dict(self.fixtures[0], finished=False, finished_provisional=True,
                     team_h_score=3, team_a_score=0)]
        out = transform(prov, TEAMS)
        r = out['f' + str(prov[0]['id'])]
        self.assertTrue(r['finished'])
        self.assertEqual((r['score1'], r['score2']), (3, 0))

    def test_gw_is_int_or_none_never_string(self):
        out = transform(self.fixtures, TEAMS)
        for v in out.values():
            self.assertTrue(v['gw'] is None or isinstance(v['gw'], int))
