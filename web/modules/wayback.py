#!/usr/bin/env python3
"""Esri World Imagery Wayback Engine.

Adapted and optimized from Ubinam (MIT).
Retrieves historical satellite imagery versions since 2014 without API keys.
Allows chronological comparison of landscape, construction, and water bodies.
"""
from __future__ import annotations

import json
import math
import urllib.request
from pathlib import Path
from typing import Optional, List, Dict
from PIL import Image

WAYBACK_CONFIG_URL = "https://s3-us-west-2.amazonaws.com/config.maptiles.arcgis.com/waybackconfig.json"
WAYBACK_TILE_URL = "https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/{rel}/{z}/{y}/{x}"

_CONFIG_CACHE: Optional[dict] = None

def get_wayback_config() -> dict:
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE
    try:
        req = urllib.request.Request(WAYBACK_CONFIG_URL, headers={"User-Agent": "GeoSleuth/2.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            _CONFIG_CACHE = json.loads(resp.read().decode("utf-8"))
            return _CONFIG_CACHE
    except Exception as e:
        print(f"Wayback config fetch error: {e}")
        return {}

def get_releases() -> list[dict]:
    """Returns sorted releases from newest to oldest."""
    cfg = get_wayback_config()
    releases = []
    for k, v in cfg.items():
        title = v.get("itemTitle", "")
        date_str = title.split("Wayback ")[-1].rstrip(")") if "Wayback " in title else title
        releases.append({
            "release_id": int(k),
            "date": date_str,
            "title": title
        })
    return sorted(releases, key=lambda r: r["date"], reverse=True)

def deg2num(lat_deg: float, lon_deg: float, zoom: int) -> tuple[int, int]:
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return xtile, ytile

def fetch_wayback_tile(release_id: int, lat: float, lon: float, zoom: int = 17, out_path: Optional[Path] = None) -> Optional[Path]:
    """Downloads a single historical tile for the given release and coordinate."""
    xtile, ytile = deg2num(lat, lon, zoom)
    url = WAYBACK_TILE_URL.format(rel=release_id, z=zoom, y=ytile, x=xtile)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "GeoSleuth/2.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
            if len(data) > 1000:
                if out_path:
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(out_path, "wb") as f:
                        f.write(data)
                    return out_path
    except Exception as e:
        print(f"Wayback tile fetch failed for rel={release_id}: {e}")
    return None

def fetch_wayback_comparison(lat: float, lon: float, out_dir: Path, job_id: str, zoom: int = 17, count: int = 3) -> list[dict]:
    """Downloads a timeline comparison (e.g. current vs past 3 years) for coordinates."""
    rels = get_releases()
    if not rels:
        return []
    
    # Pick recent, 3 years ago, and oldest available
    selected = [rels[0]]
    if len(rels) > 40:
        selected.append(rels[35])  # ~3-4 years back
    if len(rels) > 80:
        selected.append(rels[80])  # ~8 years back
    
    results = []
    for item in selected[:count]:
        rel_id = item["release_id"]
        date_str = item["date"].replace("-", "")
        tile_file = out_dir / f"wayback_{job_id}_{rel_id}_{date_str}.jpg"
        p = fetch_wayback_tile(rel_id, lat, lon, zoom=zoom, out_path=tile_file)
        if p and p.exists():
            results.append({
                "release_id": rel_id,
                "date": item["date"],
                "url": f"/static/uploads/{p.name}",
                "path": str(p)
            })
    return results
