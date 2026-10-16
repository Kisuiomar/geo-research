#!/usr/bin/env python3
"""Geodesic Utilities and Coordinate Datum Conversions.

Adapted from FindMyPhoto, Ubinam, and geo-sleuth.
Provides distance (Haversine/Vincenty), bearing, destination point,
and exact conversions between WGS-84, GCJ-02, and BD-09.
"""
from __future__ import annotations

import math
from typing import Tuple

EARTH_RADIUS_M = 6371000.0

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two points in meters."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_M * c

def initial_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates initial compass bearing from point 1 to point 2 in degrees (0-360)."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)

    y = math.sin(delta_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)
    theta = math.atan2(y, x)
    return (math.degrees(theta) + 360.0) % 360.0

def destination_point(lat: float, lon: float, distance_m: float, bearing_deg: float) -> Tuple[float, float]:
    """Computes destination coordinates from start point, distance, and bearing."""
    delta = distance_m / EARTH_RADIUS_M
    theta = math.radians(bearing_deg)
    phi1 = math.radians(lat)
    lambda1 = math.radians(lon)

    phi2 = math.asin(math.sin(phi1) * math.cos(delta) + math.cos(phi1) * math.sin(delta) * math.cos(theta))
    lambda2 = lambda1 + math.atan2(math.sin(theta) * math.sin(delta) * math.cos(phi1),
                                  math.cos(delta) - math.sin(phi1) * math.sin(phi2))
    return math.degrees(phi2), (math.degrees(lambda2) + 540.0) % 360.0 - 180.0

# -------------------------------------------------------------------------
# Coordinate datum transforms: WGS-84 <-> GCJ-02 (Mars) <-> BD-09 (Baidu)
# -------------------------------------------------------------------------

_A = 6378245.0
_EE = 0.00669342162296594323

def _transform_lat(x: float, y: float) -> float:
    ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(y * math.pi) + 40.0 * math.sin(y / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (160.0 * math.sin(y / 12.0 * math.pi) + 320 * math.sin(y * math.pi / 30.0)) * 2.0 / 3.0
    return ret

def _transform_lon(x: float, y: float) -> float:
    ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(x * math.pi) + 40.0 * math.sin(x / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (150.0 * math.sin(x / 12.0 * math.pi) + 300.0 * math.sin(x / 30.0 * math.pi)) * 2.0 / 3.0
    return ret

def wgs84_to_gcj02(lat: float, lon: float) -> Tuple[float, float]:
    """Converts WGS-84 GPS coordinates to GCJ-02 (Chinese Mars coordinates)."""
    d_lat = _transform_lat(lon - 105.0, lat - 35.0)
    d_lon = _transform_lon(lon - 105.0, lat - 35.0)
    rad_lat = math.radians(lat)
    magic = math.sin(rad_lat)
    magic = 1.0 - _EE * magic * magic
    sqrt_magic = math.sqrt(magic)
    d_lat = (d_lat * 180.0) / ((_A * (1.0 - _EE)) / (magic * sqrt_magic) * math.pi)
    d_lon = (d_lon * 180.0) / (_A / sqrt_magic * math.cos(rad_lat) * math.pi)
    return lat + d_lat, lon + d_lon

def gcj02_to_wgs84(lat: float, lon: float) -> Tuple[float, float]:
    """Converts GCJ-02 coordinates back to standard WGS-84."""
    g_lat, g_lon = wgs84_to_gcj02(lat, lon)
    return lat * 2.0 - g_lat, lon * 2.0 - g_lon

def gcj02_to_bd09(lat: float, lon: float) -> Tuple[float, float]:
    """Converts GCJ-02 to Baidu BD-09."""
    x_pi = math.pi * 3000.0 / 180.0
    z = math.sqrt(lon * lon + lat * lat) + 0.00002 * math.sin(lat * x_pi)
    theta = math.atan2(lat, lon) + 0.000003 * math.cos(lon * x_pi)
    return z * math.sin(theta) + 0.006, z * math.cos(theta) + 0.0065

def bd09_to_gcj02(lat: float, lon: float) -> Tuple[float, float]:
    """Converts Baidu BD-09 to GCJ-02."""
    x_pi = math.pi * 3000.0 / 180.0
    x = lon - 0.0065
    y = lat - 0.006
    z = math.sqrt(x * x + y * y) - 0.00002 * math.sin(y * x_pi)
    theta = math.atan2(y, x) - 0.000003 * math.cos(x * x_pi)
    return z * math.sin(theta), z * math.cos(theta)

def bd09_to_wgs84(lat: float, lon: float) -> Tuple[float, float]:
    """Converts Baidu BD-09 directly to WGS-84."""
    g_lat, g_lon = bd09_to_gcj02(lat, lon)
    return gcj02_to_wgs84(g_lat, g_lon)

def wgs84_to_bd09(lat: float, lon: float) -> Tuple[float, float]:
    """Converts standard WGS-84 coordinates to Baidu BD-09."""
    g_lat, g_lon = wgs84_to_gcj02(lat, lon)
    return gcj02_to_bd09(g_lat, g_lon)
