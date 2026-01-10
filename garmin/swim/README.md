# Garmin Swim Workouts

This folder stores swim workouts in editable CSV form:

- `csv/25y`: editable CSV definitions for pool-length workouts (25 yards).

## Update workflow

1. Edit or add workouts in `garmin/swim/csv/25y`.
2. Convert CSV → FIT with the helper script:

```bash
scripts/convert_swim_csvs.sh /path/to/FitCSVTool.jar garmin/swim/csv/25y garmin/swim/fit/25y
```

## Notes

- These CSV files use Garmin's FitCSVTool format.
- `garmin/swim/fit/25y` is generated output and should not be committed.
- Keep file names consistent across CSV and FIT so Garmin workouts stay organized.
