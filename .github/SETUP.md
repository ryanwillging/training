# GitHub Actions Setup

## Configuring Secrets

To enable the daily sync workflow, add these secrets to your GitHub repository:

1. Go to: https://github.com/ryanwillging/training/settings/secrets/actions
2. Click "New repository secret"
3. Add each secret below:

### Required Secrets

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `DATABASE_URL` | Neon PostgreSQL connection string | `postgresql://user:pass@host/db` |
| `GARMIN_EMAIL` | Garmin Connect login email | `your-email@gmail.com` |
| `GARMIN_PASSWORD` | Garmin Connect password | `your-password` |
| `HEVY_API_KEY` | Hevy API Bearer token | `hvy_xxx...` |
| `ATHLETE_ID` | Athlete ID in database (usually `1`) | `1` |

### Getting Secret Values

**From Vercel:**
```bash
# View current Vercel environment variables
vercel env ls

# Pull a specific value
vercel env pull .env.github
# Then copy values from .env.github
```

**From local .env.prod:**
```bash
cat .env.prod
# Copy each value to GitHub secrets
```

## Testing the Workflow

### Manual Trigger
1. Go to: https://github.com/ryanwillging/training/actions/workflows/daily-sync.yml
2. Click "Run workflow"
3. Select branch: `main`
4. Click "Run workflow"

### Check Results
1. Click on the running workflow
2. Click "sync-data" job
3. Expand "Run sync" step to see output
4. Should show:
   - Wellness sync complete: X days
   - Activity sync complete: X imported, X skipped
   - Hevy sync complete: X imported, X skipped
   - ✓ Logged sync to CronLog

### Verify in Dashboard
After workflow completes:
```bash
curl https://training.ryanwillging.com/api/cron/sync/status | jq
```

Should show:
- Recent `run_date` (just ran)
- `status: "success"`
- Import counts > 0

## Troubleshooting

### Workflow fails with "ModuleNotFoundError"
- Check that `requirements.txt` includes all dependencies
- Python version in workflow matches project requirement (3.9)

### Workflow fails with "Authentication failed"
- Verify `GARMIN_EMAIL` and `GARMIN_PASSWORD` secrets are correct
- Test locally: `python scripts/run_sync.py` with same credentials

### Database connection fails
- Verify `DATABASE_URL` secret is correct
- Check Neon console for IP allowlist (GitHub Actions IPs may need whitelisting)

### Workflow succeeds but dashboard shows stale data
- Check workflow logs - may have succeeded with 0 imports
- Verify data sources (Garmin/Hevy) have new data to import
- Check for errors in "Run sync" step output

## Monitoring

### Email Notifications
GitHub sends email if workflow fails. Configure in:
Settings → Notifications → Actions

### Workflow History
View past runs: https://github.com/ryanwillging/training/actions/workflows/daily-sync.yml

### Sync Status
Check via API:
```bash
curl https://training.ryanwillging.com/api/cron/sync/status
```

Or view dashboard: https://training.ryanwillging.com/dashboard
