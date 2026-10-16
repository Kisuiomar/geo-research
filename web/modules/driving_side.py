#!/usr/bin/env python3
"""Driving Side & Road Traffic Geolocation Module.

Adapted and enhanced from Geo-Guesser (MIT).
Allows decisive planetary elimination based on observed traffic flow,
driver seating position (LHD/RHD), or road lane arrows.
"""
from __future__ import annotations

# Territories that drive on the LEFT (LHT). Everything not listed is RHT.
LEFT_DRIVE_COUNTRIES = {
    # Asia
    "India", "Pakistan", "Bangladesh", "Nepal", "Bhutan", "Sri Lanka", "Maldives",
    "Indonesia", "Thailand", "Malaysia", "Singapore", "Brunei", "East Timor",
    "Japan", "Hong Kong", "Macau",
    # Oceania
    "Australia", "New Zealand", "Fiji", "Papua New Guinea", "Solomon Islands",
    "Vanuatu", "Samoa", "Tonga", "Kiribati", "Tuvalu", "Nauru",
    # Africa
    "Kenya", "Tanzania", "Uganda", "South Africa", "Zimbabwe", "Botswana",
    "Zambia", "Malawi", "Mozambique", "Lesotho", "Eswatini", "Namibia",
    "Seychelles", "Mauritius", "Madagascar",
    # Europe
    "United Kingdom", "Ireland", "Cyprus", "Malta",
    # Americas & Caribbean
    "Guyana", "Suriname", "Jamaica", "Trinidad and Tobago", "Barbados",
    "Bahamas", "Belize", "Antigua and Barbuda", "Dominica", "Grenada",
    "Saint Lucia", "Saint Vincent and the Grenadines", "Saint Kitts and Nevis"
}

def is_country_left_hand(country_name: str) -> bool:
    """Checks if a given country or territory uses Left-Hand Traffic (LHT)."""
    c = (country_name or "").strip().lower()
    for lht in LEFT_DRIVE_COUNTRIES:
        if lht.lower() in c or c in lht.lower():
            return True
    # Common Russian/multilingual names
    ru_lht = ["великобритания", "англия", "япония", "австралия", "индия", "таиланд", "тайланд", 
              "кипр", "мальта", "юар", "новая зеландия", "индонезия", "малайзия", "сингапур",
              "пакистан", "бангладеш", "шри-ланка", "непал", "ирландия", "ямайка", "кения", "танзания"]
    return any(r in c for r in ru_lht)

def analyze_driving_side(observed_side: str, country_name: str = "") -> dict:
    """Evaluates the traffic side and returns eliminated/candidate territory sets."""
    if country_name:
        is_lht = is_country_left_hand(country_name)
        side = "left" if is_lht else "right"
    else:
        side = observed_side.strip().lower()
        if side in ("rht", "right", "правостороннее", "правое"):
            side = "right"
        elif side in ("lht", "left", "левостороннее", "левое"):
            side = "left"
        else:
            side = "right" if not is_country_left_hand(observed_side) else "left"
    
    is_left = (side == "left")
    if is_left:
        return {
            "valid": True,
            "driving_side": "LHT",
            "country": country_name or observed_side,
            "observed_side": "LEFT (Левостороннее движение / LHT)",
            "driver_position": "RIGHT (Правый руль / RHD)",
            "retained_countries_count": len(LEFT_DRIVE_COUNTRIES),
            "retained_countries": sorted(LEFT_DRIVE_COUNTRIES),
            "eliminated_summary": "Исключены все страны с правосторонним движением (включая Казахстан, РФ, страны ЕС кроме Кипра/Мальты, США, Китай и др.).",
            "key_candidates": ["Великобритания", "Япония", "Австралия", "Индия", "Таиланд", "Индонезия", "ЮАР", "Кипр"]
        }
    else:
        return {
            "valid": True,
            "driving_side": "RHT",
            "country": country_name or observed_side,
            "observed_side": "RIGHT (Правостороннее движение / RHT)",
            "driver_position": "LEFT (Левый руль / LHD)",
            "eliminated_countries_count": len(LEFT_DRIVE_COUNTRIES),
            "eliminated_countries": sorted(LEFT_DRIVE_COUNTRIES),
            "eliminated_summary": f"Исключены {len(LEFT_DRIVE_COUNTRIES)} стран с левосторонним движением (Великобритания, Япония, Австралия, Индия, Таиланд, ЮАР и др.).",
            "candidate_regions": ["Казахстан", "Евразия (СНГ/ЕС)", "Северная Америка", "Китай", "Ближний Восток", "Южная Америка (кроме Гайаны/Суринама)"]
        }
