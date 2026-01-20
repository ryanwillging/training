#!/usr/bin/env python3
"""
Capture API response snapshots before refactoring.
These can be compared after refactoring to ensure behavior is preserved.

Usage:
    python scripts/capture_snapshots.py capture    # Save current responses
    python scripts/capture_snapshots.py verify     # Compare against saved
"""

import os
import sys
import json
import hashlib
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests

BASE_URL = os.getenv("BASE_URL", "https://training.ryanwillging.com")
SNAPSHOT_DIR = Path(__file__).parent.parent / "tests" / "snapshots"

# Endpoints to snapshot (path, expected_type, key_fields_to_compare)
ENDPOINTS = [
    ("/health", "json", ["status", "database"]),
    ("/api/cron/sync/status", "json", ["status", "endpoint"]),
    ("/api/plan/status", "json", ["is_initialized", "plan_name"]),
    ("/api/plan/evaluation-context", "json", ["current_week", "ai_instructions"]),
    ("/api/reports/list", "json", ["count"]),
    ("/dashboard", "html", None),
    ("/upcoming", "html", None),
    ("/reviews", "html", None),
    ("/metrics", "html", None),
    ("/api/reports/daily", "html", None),
    ("/api/reports/weekly", "html", None),
]


def get_response(path: str):
    """Fetch a response from the API."""
    url = f"{BASE_URL}{path}"
    try:
        response = requests.get(url, timeout=30)
        return {
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type", ""),
            "body": response.text,
            "json": response.json() if "application/json" in response.headers.get("content-type", "") else None
        }
    except Exception as e:
        return {"error": str(e)}


def hash_html_structure(html: str) -> str:
    """Create a hash of HTML structure (ignoring dynamic content)."""
    import re
    # Remove dynamic content like dates, timestamps, IDs
    cleaned = re.sub(r'\d{4}-\d{2}-\d{2}', 'DATE', html)
    cleaned = re.sub(r'\d{2}:\d{2}:\d{2}', 'TIME', cleaned)
    cleaned = re.sub(r'id="\d+"', 'id="ID"', cleaned)
    cleaned = re.sub(r'data-review-id="\d+"', 'data-review-id="ID"', cleaned)
    # Hash the cleaned structure
    return hashlib.md5(cleaned.encode()).hexdigest()[:16]


def capture_snapshots():
    """Capture current API responses."""
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

    snapshots = {
        "captured_at": datetime.now().isoformat(),
        "base_url": BASE_URL,
        "endpoints": {}
    }

    print(f"Capturing snapshots from {BASE_URL}...\n")

    for path, expected_type, key_fields in ENDPOINTS:
        print(f"  {path}...", end=" ")
        response = get_response(path)

        if "error" in response:
            print(f"ERROR: {response['error']}")
            snapshots["endpoints"][path] = {"error": response["error"]}
            continue

        snapshot = {
            "status_code": response["status_code"],
            "content_type": response["content_type"],
            "type": expected_type,
        }

        if expected_type == "json" and response["json"]:
            if key_fields:
                snapshot["key_fields"] = {k: response["json"].get(k) for k in key_fields}
            snapshot["full_response_keys"] = list(response["json"].keys())
        elif expected_type == "html":
            snapshot["html_length"] = len(response["body"])
            snapshot["html_structure_hash"] = hash_html_structure(response["body"])
            # Check for key elements
            snapshot["has_nav"] = "nav" in response["body"].lower()
            snapshot["has_style"] = "<style" in response["body"]
            snapshot["has_errors"] = any(err in response["body"].lower()
                                         for err in ["traceback", "exception", "error 500"])

        snapshots["endpoints"][path] = snapshot
        print(f"OK (status={response['status_code']})")

    # Save snapshots
    snapshot_file = SNAPSHOT_DIR / "api_snapshots.json"
    with open(snapshot_file, "w") as f:
        json.dump(snapshots, f, indent=2)

    print(f"\nSnapshots saved to {snapshot_file}")
    return snapshots


def verify_snapshots():
    """Compare current responses against saved snapshots."""
    snapshot_file = SNAPSHOT_DIR / "api_snapshots.json"

    if not snapshot_file.exists():
        print("No snapshots found. Run 'capture' first.")
        return False

    with open(snapshot_file) as f:
        saved = json.load(f)

    print(f"Comparing against snapshots from {saved['captured_at']}...\n")

    passed = 0
    failed = 0

    for path, expected_type, key_fields in ENDPOINTS:
        print(f"  {path}...", end=" ")

        if path not in saved["endpoints"]:
            print("SKIP (no saved snapshot)")
            continue

        saved_snap = saved["endpoints"][path]
        if "error" in saved_snap:
            print(f"SKIP (saved had error)")
            continue

        response = get_response(path)
        if "error" in response:
            print(f"FAIL (error: {response['error']})")
            failed += 1
            continue

        issues = []

        # Check status code
        if response["status_code"] != saved_snap["status_code"]:
            issues.append(f"status {response['status_code']} != {saved_snap['status_code']}")

        # Check JSON key fields
        if expected_type == "json" and response["json"] and "key_fields" in saved_snap:
            for key, expected_val in saved_snap["key_fields"].items():
                actual_val = response["json"].get(key)
                if actual_val != expected_val:
                    issues.append(f"{key}: {actual_val} != {expected_val}")

        # Check HTML structure
        if expected_type == "html":
            current_hash = hash_html_structure(response["body"])
            # Allow some variance in HTML structure
            if saved_snap.get("has_errors") != any(err in response["body"].lower()
                                                    for err in ["traceback", "exception", "error 500"]):
                issues.append("error state changed")
            if saved_snap.get("has_nav") and "nav" not in response["body"].lower():
                issues.append("nav missing")
            if saved_snap.get("has_style") and "<style" not in response["body"]:
                issues.append("styles missing")

        if issues:
            print(f"FAIL ({', '.join(issues)})")
            failed += 1
        else:
            print("OK")
            passed += 1

    print(f"\n{passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/capture_snapshots.py [capture|verify]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "capture":
        capture_snapshots()
    elif command == "verify":
        success = verify_snapshots()
        sys.exit(0 if success else 1)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
