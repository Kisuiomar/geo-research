#!/usr/bin/env python3
"""Global and Regional Telephone Number OSINT Geolocation Engine.

Adapted and enhanced from Geo-Guesser and Searching-skill.
Uses libphonenumber (via phonenumbers package) and specialized regional tables
for Kazakhstan, CIS, and global area codes.
"""
from __future__ import annotations

import re
from typing import Optional, List, Dict

try:
    import phonenumbers
    from phonenumbers import geocoder, carrier, timezone
except ImportError:
    phonenumbers = None

# Kazakhstan landline codes mapping
KZ_LANDLINE_AREA_CODES = {
    "7172": {"city": "г. Астана", "region": "Акмолинская область / Столица", "lat": 51.169392, "lon": 71.449074},
    "727": {"city": "г. Алматы", "region": "Алматинская область", "lat": 43.238949, "lon": 76.889709},
    "7252": {"city": "г. Шымкент", "region": "Туркестанская область", "lat": 42.341667, "lon": 69.595833},
    "7162": {"city": "г. Кокшетау", "region": "Акмолинская область", "lat": 53.283333, "lon": 69.383333},
    "71636": {"city": "г. Щучинск / Бурабай", "region": "Акмолинская область", "lat": 52.933333, "lon": 70.200000},
    "7132": {"city": "г. Актобе", "region": "Актюбинская область", "lat": 50.300000, "lon": 57.166667},
    "7282": {"city": "г. Талдыкорган", "region": "Область Жетысу", "lat": 45.016667, "lon": 78.366667},
    "7122": {"city": "г. Атырау", "region": "Атырауская область", "lat": 47.116667, "lon": 51.883333},
    "7232": {"city": "г. Усть-Каменогорск (Өскемен)", "region": "Восточно-Казахстанская область", "lat": 49.950000, "lon": 82.616667},
    "7222": {"city": "г. Семей", "region": "Область Абай", "lat": 50.416667, "lon": 80.250000},
    "7262": {"city": "г. Тараз", "region": "Жамбылская область", "lat": 42.900000, "lon": 71.366667},
    "7112": {"city": "г. Уральск (Орал)", "region": "Западно-Казахстанская область", "lat": 51.233333, "lon": 51.366667},
    "7212": {"city": "г. Караганда", "region": "Карагандинская область", "lat": 49.800000, "lon": 73.100000},
    "7102": {"city": "г. Жезказган", "region": "Область Улытау", "lat": 47.783333, "lon": 67.716667},
    "7142": {"city": "г. Костанай", "region": "Костанайская область", "lat": 53.216667, "lon": 63.633333},
    "7242": {"city": "г. Кызылорда", "region": "Кызылординская область", "lat": 44.850000, "lon": 65.516667},
    "7292": {"city": "г. Актау", "region": "Мангистауская область", "lat": 43.650000, "lon": 51.150000},
    "7182": {"city": "г. Павлодар", "region": "Павлодарская область", "lat": 52.300000, "lon": 76.950000},
    "7152": {"city": "г. Петропавловск", "region": "Северо-Казахстанская область", "lat": 54.866667, "lon": 69.150000},
    "72533": {"city": "г. Туркестан", "region": "Туркестанская область", "lat": 43.300000, "lon": 68.250000}
}

KZ_MOBILE_PREFIXES = {
    "700": "Altel / Tele2 (Казахстан)",
    "701": "Kcell / Activ (Казахстан)",
    "702": "Kcell / Activ (Казахстан)",
    "705": "Beeline (Казахстан)",
    "706": "Izi (Казахстан)",
    "707": "Tele2 (Казахстан)",
    "708": "Altel (Казахстан)",
    "747": "Tele2 (Казахстан)",
    "771": "Beeline (Казахстан)",
    "775": "Kcell / Activ (Казахстан)",
    "776": "Beeline (Казахстан)",
    "777": "Beeline (Казахстан)",
    "778": "Kcell / Activ (Казахстан)"
}

def extract_phone_candidates(text: str) -> list[str]:
    """Finds potential phone numbers in OCR or string snippets."""
    cleaned = re.sub(r'[\r\n\t]', ' ', text)
    patterns = [
        r'\+?\b[78]\s*[\(\-]?\s*\d{3,4}\s*[\)\-]?\s*\d{2,3}[\-\s]?\d{2}[\-\s]?\d{2}\b',
        r'\b\+?\d{1,3}[\s\-]?\(?\d{2,4}\)?[\s\-]?\d{3}[\s\-]?\d{2,4}\b',
        r'\b8\s*7\d{2}\s*\d{3}\s*\d{2}\s*\d{2}\b',
        r'\b\+7\s*7\d{2}\s*\d{3}\s*\d{2}\s*\d{2}\b',
        r'\b1[3-9]\d{9}\b'  # Chinese mobile
    ]
    found = []
    for pat in patterns:
        for m in re.finditer(pat, cleaned):
            cand = m.group(0).strip()
            digits = re.sub(r'\D', '', cand)
            if 7 <= len(digits) <= 15 and cand not in found:
                found.append(cand)
    return found

def lookup_phone_number(raw: str, default_region: str = "KZ") -> dict:
    """Parses a phone number and returns country, city/oblast, carrier and coordinates."""
    clean = raw.strip()
    digits = re.sub(r'\D', '', clean)
    
    # Check Kazakhstan local area codes first
    if digits.startswith("8") and len(digits) == 11:
        kz_digits = "7" + digits[1:]
    elif digits.startswith("7") and len(digits) == 11:
        kz_digits = digits
    elif len(digits) == 10 and digits.startswith("7"):
        kz_digits = "7" + digits
    else:
        kz_digits = None

    if kz_digits:
        # Check landline prefixes
        for prefix, loc in KZ_LANDLINE_AREA_CODES.items():
            if kz_digits.startswith(prefix):
                return {
                    "raw": clean,
                    "valid": True,
                    "country": "Казахстан",
                    "country_code": "KZ",
                    "region": loc["region"],
                    "city": loc["city"],
                    "type": "Городской стационарный номер",
                    "lat": loc["lat"],
                    "lon": loc["lon"],
                    "note": f"Код города {prefix} указывает на {loc['city']} ({loc['region']})"
                }
        # Check mobile prefixes
        for m_pref, op in KZ_MOBILE_PREFIXES.items():
            if kz_digits[1:4] == m_pref:
                return {
                    "raw": clean,
                    "valid": True,
                    "country": "Казахстан",
                    "country_code": "KZ",
                    "region": "Республика Казахстан",
                    "city": "Казахстан (Мобильный оператор)",
                    "type": f"Сотовая связь ({op})",
                    "lat": 51.169392,
                    "lon": 71.449074,
                    "note": f"Мобильный номер оператора {op}"
                }

    # Universal libphonenumber lookup
    if phonenumbers:
        try:
            num = phonenumbers.parse(clean, default_region)
            valid = phonenumbers.is_valid_number(num)
            if valid or phonenumbers.is_possible_number(num):
                country = geocoder.country_name_for_number(num, "ru") or geocoder.country_name_for_number(num, "en") or "Не определено"
                region = geocoder.description_for_number(num, "ru") or geocoder.description_for_number(num, "en") or ""
                car = carrier.name_for_number(num, "ru") or carrier.name_for_number(num, "en") or ""
                tz = ", ".join(timezone.time_zones_for_number(num)) or ""
                e164 = phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164)
                return {
                    "raw": clean,
                    "e164": e164,
                    "valid": valid,
                    "country": country,
                    "region": region or country,
                    "city": region or country,
                    "carrier": car,
                    "timezone": tz,
                    "type": "Международный телефонный номер",
                    "note": f"Формат {e164}, оператор: {car or 'не указан'}, часовой пояс: {tz}"
                }
        except Exception as e:
            return {"raw": clean, "valid": False, "error": str(e)}

    return {
        "raw": clean,
        "valid": False,
        "note": "Номер не удалось привязать к конкретному региону."
    }
