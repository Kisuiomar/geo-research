#!/usr/bin/env python3
"""Solar Position and Shadow Forensic Analysis Engine.

Adapted and optimized from geo-sleuth and Ubinam (MIT).
Calculates exact solar altitude and azimuth from timestamp and coordinates,
and provides reverse constraints on camera azimuth and geographic latitude.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Optional, Dict

def calculate_solar_position(lat: float, lon: float, dt: datetime) -> dict:
    """Computes solar altitude (elevation) and azimuth angles in degrees.
    
    Uses standard astronomical solar equations.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
        
    year = dt.year
    month = dt.month
    day = dt.day
    hour = dt.hour + dt.minute / 60.0 + dt.second / 3600.0

    # Julian Day Number
    if month <= 2:
        year -= 1
        month += 12
    a = math.floor(year / 100)
    b = 2 - a + math.floor(a / 4)
    jd = math.floor(365.25 * (year + 4716)) + math.floor(30.6001 * (month + 1)) + day + b - 1524.5 + hour / 24.0
    t = (jd - 2451545.0) / 36525.0

    # Geometric Mean Longitude of the Sun (deg)
    l0 = (280.46646 + t * (36000.76983 + t * 0.0003032)) % 360.0
    # Mean anomaly of the Sun (deg)
    m = (357.52911 + t * (35999.05029 - 0.0001537 * t)) % 360.0
    # Sun equation of center
    c = math.sin(math.radians(m)) * (1.914602 - t * (0.004817 + 0.000014 * t)) + \
        math.sin(math.radians(2 * m)) * (0.019993 - 0.000101 * t) + \
        math.sin(math.radians(3 * m)) * 0.000289
    sun_true_lon = l0 + c
    
    # Obliquity of the ecliptic
    eps0 = 23.0 + (26.0 + (21.448 - t * (46.8150 + t * (0.0059 - t * 0.001813))) / 60.0) / 60.0
    eps = eps0 + 0.00256 * math.cos(math.radians(125.04 - 1934.136 * t))

    # Sun Right Ascension and Declination
    sin_dec = math.sin(math.radians(eps)) * math.sin(math.radians(sun_true_lon))
    dec = math.degrees(math.asin(sin_dec))

    cos_dec = math.cos(math.radians(dec))
    sin_ra = (math.cos(math.radians(eps)) * math.sin(math.radians(sun_true_lon))) / cos_dec
    cos_ra = math.cos(math.radians(sun_true_lon)) / cos_dec
    ra = math.degrees(math.atan2(sin_ra, cos_ra)) % 360.0

    # Greenwich Mean Sidereal Time
    gmst0 = 280.46061837 + 360.98564736629 * (jd - 2451545.0) + t * t * 0.000387933
    gmst = gmst0 % 360.0
    lmst = (gmst + lon) % 360.0
    hour_angle = (lmst - ra) % 360.0

    # Altitude
    lat_r = math.radians(lat)
    dec_r = math.radians(dec)
    ha_r = math.radians(hour_angle)
    sin_alt = math.sin(lat_r) * math.sin(dec_r) + math.cos(lat_r) * math.cos(dec_r) * math.cos(ha_r)
    alt = math.degrees(math.asin(max(-1.0, min(1.0, sin_alt))))

    # Azimuth
    cos_az = (math.sin(dec_r) - math.sin(lat_r) * sin_alt) / (math.cos(lat_r) * math.cos(math.radians(alt)))
    cos_az = max(-1.0, min(1.0, cos_az))
    az = math.degrees(math.acos(cos_az))
    if math.sin(ha_r) > 0:
        az = (360.0 - az) % 360.0

    # Shadow ray (shadow falls in opposite direction to sun)
    shadow_azimuth = (az + 180.0) % 360.0
    # Shadow length ratio (L / H) = cot(altitude)
    shadow_ratio = 1.0 / math.tan(math.radians(max(0.5, alt))) if alt > 0 else 999.0

    return {
        "solar_altitude_deg": round(alt, 2),
        "solar_azimuth_deg": round(az, 2),
        "shadow_azimuth_deg": round(shadow_azimuth, 2),
        "shadow_ratio": round(shadow_ratio, 2),
        "sun_visible": alt > 0,
        "declination_deg": round(dec, 2)
    }

def estimate_camera_bearing_from_shadow(solar_azimuth: float, shadow_clock_angle: float) -> float:
    """Estimates camera compass bearing from shadow orientation in image frame.
    
    shadow_clock_angle: 0 deg (shadow pointing straight ahead), 90 deg (to right), 180 deg (towards camera).
    """
    shadow_world_az = (solar_azimuth + 180.0) % 360.0
    camera_bearing = (shadow_world_az - shadow_clock_angle) % 360.0
    return round(camera_bearing, 1)
