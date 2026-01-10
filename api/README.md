# Garmin FIT Import API

This FastAPI service uploads `.fit` files to Garmin Connect using the
[`python-garminconnect`](https://github.com/cyberjunky/python-garminconnect) client.

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Export credentials:

```bash
export GARMIN_EMAIL="you@example.com"
export GARMIN_PASSWORD="your-password"
```

## Run locally

```bash
uvicorn api.app:app --reload
```

## Upload a FIT file

```bash
curl -F "file=@/path/to/workout.fit" http://127.0.0.1:8000/import/fit
```

## Notes

- The API uses `Garmin.upload_activity()` to send the FIT file to Garmin Connect.
- Keep the CSV files in `garmin/swim/csv/25y` as the source of truth and generate
  FIT files locally when you need to upload.
