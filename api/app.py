from fastapi import FastAPI, File, HTTPException, UploadFile
from garminconnect import Garmin
import os
from pathlib import Path
import tempfile


app = FastAPI(title="Garmin FIT Import API")


def get_garmin_client() -> Garmin:
    email = os.environ.get("GARMIN_EMAIL")
    password = os.environ.get("GARMIN_PASSWORD")
    if not email or not password:
        raise HTTPException(status_code=500, detail="GARMIN_EMAIL and GARMIN_PASSWORD must be set")

    client = Garmin(email, password)
    client.login()
    return client


@app.post("/import/fit")
async def import_fit(file: UploadFile = File(...)) -> dict:
    if not file.filename or not file.filename.lower().endswith(".fit"):
        raise HTTPException(status_code=400, detail="Upload a .fit file")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir) / file.filename
        temp_path.write_bytes(data)

        client = get_garmin_client()
        result = client.upload_activity(str(temp_path))

    return {
        "filename": file.filename,
        "garmin_response": result,
    }
