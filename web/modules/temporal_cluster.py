#!/usr/bin/env python3
"""Temporal Photo Clustering and GPS Interpolation Engine.

Adapted from FindMyPhoto (AGPL-3.0).
Interpolates plausible coordinates for unplaced photos based on temporal proximity
to photos in the same album, session, or day that already have verified GPS coordinates.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional, List, Dict
from pathlib import Path
from PIL import Image, ExifTags

def parse_exif_timestamp(exif_date_str: str) -> Optional[datetime]:
    """Parses standard EXIF date format 'YYYY:MM:DD HH:MM:SS'."""
    if not exif_date_str:
        return None
    try:
        clean = exif_date_str.strip()
        parts = clean.split()
        if len(parts) == 2:
            date_part = parts[0].replace(":", "-")
            time_part = parts[1]
            return datetime.fromisoformat(f"{date_part}T{time_part}").replace(tzinfo=timezone.utc)
    except Exception:
        pass
    return None

def interpolate_from_timeline(target_time: datetime, timeline_anchors: list[dict], max_delta_hours: float = 6.0) -> Optional[dict]:
    """Finds the nearest verified GPS anchor in time and computes confidence bonus.
    
    timeline_anchors: list of {'lat': float, 'lon': float, 'time': datetime, 'title': str}
    """
    if not target_time or not timeline_anchors:
        return None

    best_anchor = None
    min_diff_sec = float('inf')

    for anc in timeline_anchors:
        anc_time = anc.get("time")
        if not anc_time:
            continue
        diff_sec = abs((target_time - anc_time).total_seconds())
        if diff_sec < min_diff_sec:
            min_diff_sec = diff_sec
            best_anchor = anc

    if not best_anchor:
        return None

    diff_hours = min_diff_sec / 3600.0
    if diff_hours > max_delta_hours:
        return None

    # Temporal confidence decay
    if diff_hours < 0.1:  # < 6 minutes
        confidence = "HIGH (В пределах 6 минут от подтвержденной точки)"
        radius_m = 300
    elif diff_hours < 1.0: # < 1 hour
        confidence = "MEDIUM (В пределах 1 часа от точки маршрута)"
        radius_m = 2500
    else:
        confidence = "LOW (Временная корреляция того же дня)"
        radius_m = 15000

    return {
        "lat": best_anchor["lat"],
        "lon": best_anchor["lon"],
        "anchor_title": best_anchor.get("title", "Ориентир"),
        "time_diff_minutes": round(min_diff_sec / 60.0, 1),
        "confidence": confidence,
        "estimated_radius_m": radius_m,
        "note": f"Снимок сделан за {round(min_diff_sec / 60.0, 1)} мин до/после объекта «{best_anchor.get('title')}»."
    }
