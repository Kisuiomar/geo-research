import asyncio
import json
import re
import urllib.request
import urllib.parse
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = ROOT_DIR / "geo-sleuth" / "skills" / "geo-sleuth" / "scripts"

async def auto_geolocate(image_path: Path):
    out_dir = ROOT_DIR / "auto_rev"
    out_dir.mkdir(exist_ok=True)
    
    # Run revimg.py via subprocess
    cmd = [
        "uv", "run", "--with", "playwright", "--with", "pillow",
        "python", str(SCRIPTS_DIR / "revimg.py"),
        str(image_path),
        "--out-dir", str(out_dir),
        "--engines", "yandex"
    ]
    
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    print("revimg finished.")
    
    # Read output json
    stem = image_path.stem
    json_path = out_dir / f"{stem}_yandex.json"
    if not json_path.exists():
        return None
        
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    text_head = data.get("text_head", "")
    lines = [line.strip() for line in text_head.split("\n") if line.strip()]
    
    candidates = []
    # Look for "Кажется, на изображении" block
    if "Кажется, на изображении" in lines:
        idx = lines.index("Кажется, на изображении")
        candidates = lines[idx+1:idx+6]
        
    # Also add link titles
    for link in data.get("links", []):
        t = link.get("title", "")
        if len(t) > 5 and not re.match(r'^\d+×\d+', t):
            candidates.append(t)
            
    print("Extracted candidates:", candidates[:5])
    
    # Try geocoding top candidates via Nominatim
    for cand in candidates:
        clean_cand = re.sub(r'[\(\)\[\]«»"\'\?!\*]', ' ', cand).strip()
        # Take first 4-5 words
        query = " ".join(clean_cand.split()[:5])
        if len(query) < 3:
            continue
        try:
            url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(query)}&format=json&limit=1"
            req = urllib.request.Request(url, headers={"User-Agent": "GeoSleuth/2.0"})
            resp = json.loads(urllib.request.urlopen(req, timeout=5).read().decode("utf-8"))
            if resp:
                hit = resp[0]
                lat = float(hit["lat"])
                lon = float(hit["lon"])
                print(f"Matched '{query}' -> ({lat}, {lon}) {hit.get('display_name')}")
                return {
                    "matched_query": query,
                    "lat": lat,
                    "lon": lon,
                    "display_name": hit.get("display_name"),
                    "candidates": candidates
                }
        except Exception as e:
            print("Geocode error for", query, ":", e)
            
    return None

async def main():
    res = await auto_geolocate(Path("photo_3.jpg"))
    print("Result:", res)

if __name__ == "__main__":
    asyncio.run(main())
