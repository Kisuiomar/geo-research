import sys
import time
import requests
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

test_image = Path(r"C:\Users\user\Downloads\photo_2026-10-09_12-38-42.jpg")
print(f"Testing auto-scan with Burabay photo: {test_image}")

with open(test_image, "rb") as f:
    files = {"file": (test_image.name, f, "image/jpeg")}
    res = requests.post("http://127.0.0.1:8765/api/scan", files=files)
    job_id = res.json()["job_id"]

print(f"Job started: {job_id}")

last_log_count = 0
for _ in range(60):
    time.sleep(1)
    status_res = requests.get(f"http://127.0.0.1:8765/api/scan/{job_id}")
    data = status_res.json()
    logs = data.get("logs", [])
    while last_log_count < len(logs):
        print(f"[{data.get('progress', 0)}%] {logs[last_log_count]}")
        last_log_count += 1
    
    if data.get("status") in ("completed", "error"):
        print(f"\nFinal status: {data.get('status')}")
        if data.get("case"):
            c = data["case"]
            print(f"Title: {c.get('title')}")
            print(f"Target: {c.get('target_name')}")
            print(f"Coordinates: {c.get('target_lat')}, {c.get('target_lon')}")
            print(f"Country: {c.get('country')}, Region: {c.get('region')}")
            print(f"Confidence: {c.get('confidence')}")
            print(f"Evidence count: {len(c.get('evidence_photos', []))}")
        break
