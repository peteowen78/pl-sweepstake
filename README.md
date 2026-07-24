# Premier League Sweepstake 2026–27

A season-long sweepstake web app. Players pick one team from each of four pots
(set by pre-season title odds); teams earn points from every real Premier League
result, mirrored automatically from the Fantasy Premier League API — no manual
score entry. Full design: [docs/superpowers/specs/2026-07-23-pl-sweepstake-design.md](docs/superpowers/specs/2026-07-23-pl-sweepstake-design.md).

**The game:** wins earn 2/4/6/8 points by pot (draws half that), +1 bonus any
time your team scores 3+ in a match. £2 entry (configurable in admin). Ties
share positions and split prize money. No two entries may have the identical
four-team combination.

## Local development

```bash
npx serve Premierleague        # then open the printed URL
```

Without Firebase config the app runs in offline demo mode (entries live in
memory). Tests:

```bash
node --test Premierleague/tests/test_scoring.mjs        # scoring engine vs 380 real 2025-26 results
python3 -m unittest discover -s Premierleague/tests     # FPL transform tests
```

`sim/` holds the 2025–26 season reference data and the simulation scripts that
validated the format; `sim/reference_team_points.json` is the scoring ground
truth the JS tests compare against.

**Admin access:** the default admin password is `plsweep` — change it in
Admin → Settings after your first login.

## One-time setup

### 1. Firebase project (needs Pete's Google account)

1. [console.firebase.google.com](https://console.firebase.google.com) → Add project → name it (e.g. `pl-sweepstake`). Analytics off is fine.
2. Databases & Storage (left sidebar) → Realtime Database → Create database →
   **europe-west1** → start in test mode.
3. Rules tab → set and publish:
   ```json
   { "rules": { ".read": true, ".write": true } }
   ```
   Open writes are a deliberate choice for a friendly game among known players
   (see the spec's trust-model section) — the admin password is a UI gate, not
   database security.
4. Project settings (gear) → General → Your apps → Web app (`</>`) → register →
   copy the `firebaseConfig` object into `index.html` where the placeholder
   comment says `PASTE plsweep2627 Firebase config here`.
5. Note the `databaseURL` value — that's `FIREBASE_DB_URL` below.

### 2. Seed the fixtures

```bash
FIREBASE_DB_URL=https://<project>-default-rtdb.europe-west1.firebasedatabase.app \
  python3 Premierleague/scripts/update_results.py
```

Expected output: `wrote 380 fixtures (0 finished)`. Safe to re-run any time —
it mirrors whatever the FPL API currently says.

### 3. Deploy (GitHub Pages + Actions)

The `Premierleague/` folder is pushed as its own GitHub repo (the workflow
paths assume it's the repo root):

1. Create a public repo; push this folder's contents to its root.
2. Settings → Pages → deploy from branch, root folder.
3. Settings → Secrets and variables → Actions → **Variables** → add
   `FIREBASE_DB_URL` (it's a variable, not a secret — the URL is already
   public inside `index.html`).
4. Actions tab → "Update results" → Run workflow (manual test). The log should
   end `wrote 380 fixtures (0 finished)`.

The workflow then runs hourly at :15. GitHub pauses scheduled workflows after
60 days without repo activity — if GitHub emails about it, one click re-enables.

## How results flow (and their honest limits)

- The Action mirrors the full FPL fixtures list into Firebase every hour. A
  result appears only once FPL marks the fixture finished — typically **30–60
  minutes after full time** (FPL waits for bonus-point confirmation), plus up
  to an hour of schedule. Matchday scores are not live-minute updates; that's
  by design.
- **Admin score override is for feed outages only.** The hourly mirror rewrites
  the whole results node, so an override only sticks while the Action is
  failing or disabled. To force a result permanently (e.g. an abandoned match
  FPL never settles), disable the workflow first (Actions tab → Update results
  → ⋯ → Disable workflow), set the score, and re-enable when the feed is sane.
- **End of season — IMPORTANT:** disable the workflow after the final gameweek
  (late May). When FPL resets for the next season (June/July), its fixtures API
  starts returning the NEW season's 380 blank fixtures, and a still-running
  hourly mirror would overwrite the final 2026–27 standings while prize money
  still matters.
- Occasional red runs in the Actions tab are normal (the FPL API throws
  transient errors); the next hourly run self-heals. Sustained failures are
  worth a look.
- **Backup data source** if the FPL API ever changes shape: football-data.org
  (free tier covers the PL). Only `transform()` in `scripts/update_results.py`
  would need rewriting; everything else is agnostic.

## Credits

Club crests and the Premier League logo come from a community Figma file, used
for this private friendly game. Trademarks belong to their owners.
