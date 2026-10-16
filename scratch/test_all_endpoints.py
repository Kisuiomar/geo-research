import urllib.request
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8765"
tests_passed = 0
tests_total = 0

def test(name, url, method="GET", data=None):
    global tests_passed, tests_total
    tests_total += 1
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8") if data else None,
        headers={"Content-Type": "application/json"} if data else {}
    )
    req.get_method = lambda: method
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            tests_passed += 1
            print(f"[PASS] {name} (Status {resp.status})")
            return body
    except Exception as e:
        print(f"[FAIL] {name}: {e}")
        return None

print("=== Running GeoResearch Kazakhstan Test Suite ===")

# 1. Health
h = test("Health Check", f"{BASE_URL}/api/health")

# 2. Cases
cases = test("Get Cases", f"{BASE_URL}/api/cases")
first_case_id = cases[0]["id"] if cases else "case-d27f6837"

# 3. KZ Regions
regs = test("20 KZ Regions Gazetteer", f"{BASE_URL}/api/kz/regions")
if regs and len(regs.get("regions", {})) == 20:
    print("  -> Confirmed 20 administrative regions of Kazakhstan loaded.")

# 4. KZ Landmarks
lms = test("KZ Landmarks Gazetteer", f"{BASE_URL}/api/kz/landmarks")
if lms and len(lms.get("landmarks", [])) >= 30:
    print(f"  -> Confirmed {len(lms['landmarks'])} verified landmarks loaded.")

# 5. KZ Knowledge
k = test("Searching-skill 262-rule Reference", f"{BASE_URL}/api/kz/knowledge")

# 6. Geo-Guesser First Answer
fa = test("Geo-Guesser First Answer Protocol", f"{BASE_URL}/api/kz/first-answer", "POST", {
    "text": "Автобус 123 ABC 02 Абай даңғылы көшесі Алматы Тянь-Шань",
    "visual_tags": ["горы", "автобус"]
})
if fa:
    print(f"  -> First Answer: {fa.get('region_name')} ({fa.get('confidence_percent')}%) - {fa.get('primary_rationale')}")

# 7. Ubinam Confidence Ladder
ub = test("Ubinam 5-Tier Confidence Ladder", f"{BASE_URL}/api/cases/{first_case_id}/ubinam-ladder")
if ub:
    ladder = ub.get("ladder", {})
    print(f"  -> Ubinam Tier: {ladder.get('current_tier')} ({ladder.get('tier_name')}), Error Radius: ±{ladder.get('error_radius_m')}m")

# 8. FindMyPhoto Distance Matrix
dm = test("FindMyPhoto Distance Matrix", f"{BASE_URL}/api/cases/{first_case_id}/distance-matrix")
if dm:
    nearest = dm.get("matrix", {}).get("nearest_settlement", {})
    print(f"  -> Nearest Regional Center: {nearest.get('city')} ({nearest.get('distance_km')} km)")

# 9. SpyBrain IIN/BIN Validator
iin = test("SpyBrain IIN/BIN Validator", f"{BASE_URL}/api/kz/validate-iin-bin", "POST", {
    "code": "920514301254"
})
if iin:
    print(f"  -> IIN Entity: {iin.get('entity_type')}, Valid: {iin.get('valid')}")

# 10. Kazakh Signboard Mining
sg = test("Kazakh Signboard Mining & 2GIS", f"{BASE_URL}/api/kz/mine-signboards", "POST", {
    "text": "Мәңгілік ел даңғылы, 55 МФЦА AIFC дүкен Magnum дәріхана Europharma"
})
if sg:
    print(f"  -> Mined Streets: {sg.get('streets')}, Businesses: {sg.get('businesses')}")

# 11. Kazakhstan Phone Lookup
ph = test("Kazakhstan Phone Operator Lookup", f"{BASE_URL}/api/analyze/phone", "POST", {
    "raw_input": "+7 701 555 12 34",
    "default_region": "KZ"
})
if ph:
    print(f"  -> Carrier: {ph.get('type')}, Region: {ph.get('region')}")

# 12. Sun & Shadow Calculator (UTC+5 Unified)
sun = test("Solar Azimuth & Shadow Math (UTC+5)", f"{BASE_URL}/api/analyze/sun-shadow", "POST", {
    "lat": 51.169392,
    "lon": 71.449074,
    "date_str": "2026-10-14T12:00:00Z"
})
if sun:
    print(f"  -> Sun Azimuth: {sun.get('solar_azimuth_deg')}°, Elevation: {sun.get('solar_elevation_deg')}°, Shadow Heading: {sun.get('shadow_heading_deg')}°")

# 13. FindMyPhoto Geotag EXIF Injection
gt = test("FindMyPhoto EXIF Geotag Injection", f"{BASE_URL}/api/cases/{first_case_id}/geotag-exif", "POST")
if gt:
    print(f"  -> Download URL: {gt.get('download_url')}")

print(f"\nSummary: {tests_passed}/{tests_total} tests passed successfully!")
