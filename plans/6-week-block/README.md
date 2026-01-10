# Ryan Health — 6-Week Swim Workouts (Garmin + CSV)

This repo contains **12 structured swim workouts** (2x/week for 6 weeks) generated as:
- Garmin **.FIT workout files** (ready to copy onto a watch)
- Source **FIT CSV Tool** `.csv` files (editable; regenerate .FIT as needed)

## Folder layout

- `garmin/swim/fit/25y/` — the **.FIT workout files** for a **25-yard pool**
- `garmin/swim/csv/25y/` — the source CSV definitions used to generate the .FIT files
- `plans/6-week-block/` — the human-readable plan, test protocol, and pacing notes
- `scripts/` — helper scripts (optional)

## Import to Garmin Forerunner 945 (manual USB method)

1. Connect the watch to your computer via USB.
2. Open the watch storage and navigate to: `GARMIN/NEWFILES/`
3. Copy the `.fit` files from `garmin/swim/fit/25y/` into `GARMIN/NEWFILES/`
4. Safely eject the watch; it will import the files (Garmin typically moves them into the workouts folder on-device).

On the watch: **Training → Workouts → Swim** (exact menu varies slightly by device firmware).

> Note: Some Garmin devices use MTP (can be awkward on macOS) and some devices may require placing the file directly in `GARMIN/WORKOUTS/`.

## Baseline tests

Week 1 Swim 1 (`W1S1`) is a CSS-style baseline:
- 400y time trial
- 3:00 rest
- 200y time trial

**CSS pace per 100y** (rough guide):
- CSS100 = (T400 − T200) / 2  (time in seconds)

Track:
- 400y time, 200y time
- average split consistency (how much you fade)
- stroke rate and RPE notes (optional)

## Regenerate .FIT from CSV (optional)

Garmin’s FIT SDK includes the **FitCSVTool** which converts CSV → FIT.

Example command (once you have FitCSVTool.jar):
```bash
java -jar /path/to/FitCSVTool.jar -c garmin/swim/csv/25y/W1S1_25y.csv garmin/swim/fit/25y/W1S1_25y.fit
```

## GitHub setup (recommended)

If you use GitHub CLI:
```bash
gh repo create ryan-health-workouts --private --source . --remote origin --push
```

Or create a repo in the GitHub UI and push:
```bash
git init
git add .
git commit -m "Add 6-week Garmin swim workouts"
git branch -M main
git remote add origin <YOUR_REPO_URL>
git push -u origin main
```
