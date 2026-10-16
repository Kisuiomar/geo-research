#!/usr/bin/env python3
"""Knowledge Rules & Regional Geolocation Signatures Engine.

Synthesizes high-precision rules from Searching-skill (26,177 rules)
for vehicle license plates, linguistic alphabets, utility infrastructure,
road markings, and landscape biomes.
"""
from __future__ import annotations

import re
from typing import Optional, List, Dict

# Kazakhstan 20-region license plate codes
KAZAKHSTAN_OBLAST_PLATES = {
    "01": {"region": "г. Астана", "center": "Астана", "lat": 51.169392, "lon": 71.449074},
    "02": {"region": "г. Алматы", "center": "Алматы", "lat": 43.238949, "lon": 76.889709},
    "03": {"region": "Акмолинская область", "center": "Кокшетау", "lat": 53.283333, "lon": 69.383333},
    "04": {"region": "Актюбинская область", "center": "Актобе", "lat": 50.300000, "lon": 57.166667},
    "05": {"region": "Алматинская область", "center": "Конаев", "lat": 43.883333, "lon": 77.066667},
    "06": {"region": "Атырауская область", "center": "Атырау", "lat": 47.116667, "lon": 51.883333},
    "07": {"region": "Западно-Казахстанская область (ЗКО)", "center": "Уральск (Орал)", "lat": 51.233333, "lon": 51.366667},
    "08": {"region": "Жамбылская область", "center": "Тараз", "lat": 42.900000, "lon": 71.366667},
    "09": {"region": "Карагандинская область", "center": "Караганда", "lat": 49.800000, "lon": 73.100000},
    "10": {"region": "Костанайская область", "center": "Костанай", "lat": 53.216667, "lon": 63.633333},
    "11": {"region": "Кызылординская область", "center": "Кызылорда", "lat": 44.850000, "lon": 65.516667},
    "12": {"region": "Мангистауская область", "center": "Актау", "lat": 43.650000, "lon": 51.150000},
    "13": {"region": "Туркестанская область", "center": "Туркестан", "lat": 43.300000, "lon": 68.250000},
    "14": {"region": "Павлодарская область", "center": "Павлодар", "lat": 52.300000, "lon": 76.950000},
    "15": {"region": "Северо-Казахстанская область (СКО)", "center": "Петропавловск", "lat": 54.866667, "lon": 69.150000},
    "16": {"region": "Восточно-Казахстанская область (ВКО)", "center": "Усть-Каменогорск (Өскемен)", "lat": 49.950000, "lon": 82.616667},
    "17": {"region": "г. Шымкент", "center": "Шымкент", "lat": 42.341667, "lon": 69.595833},
    "18": {"region": "Область Абай", "center": "Семей", "lat": 50.416667, "lon": 80.250000},
    "19": {"region": "Область Жетысу", "center": "Талдыкорган", "lat": 45.016667, "lon": 78.366667},
    "20": {"region": "Область Улытау", "center": "Жезказган", "lat": 47.783333, "lon": 67.716667}
}

# Regional utility pole marking rules (from Searching-skill/哈萨克斯坦.md)
KZ_UTILITY_POLE_PAINT_RULES = {
    "красно-бело-черный": "Западно-Казахстанская область (ЗКО)",
    "сине-бело-черный": "Атырауская область",
    "узкая красная, белая, узкая черная": "Акмолинская область",
    "бирюзовый и желтый": "Костанайская область",
    "белый и светло-серый": "Северо-Казахстанская область (Петропавловск)",
    "красно-желто-черный": "Жамбылская область (Тараз)",
    "желто-красно-белый": "Кызылординская область",
    "красно-желтый": "г. Рудный / Щучинск",
    "светло-голубой": "г. Кокшетау"
}

# Language-specific unique characters
SCRIPT_FINGERPRINTS = {
    "Казахский язык": {
        "chars": set("әғқңөұүһіӘҒҚҢӨҰҮҺІ"),
        "country": "Казахстан",
        "weight": 1.0
    },
    "Кыргызский язык": {
        "chars": set("ңөүҢӨҮ"),
        "country": "Кыргызстан",
        "weight": 0.8
    },
    "Монгольский язык (Кириллица)": {
        "chars": set("өүӨҮ"),
        "country": "Монголия",
        "weight": 0.7
    },
    "Украинский язык": {
        "chars": set("іїєґІЇЄҐ"),
        "country": "Украина",
        "weight": 1.0
    },
    "Грузинский язык": {
        "chars": set("აბგდევზთიკლმნოპჟრსტუფქღყშჩცძწჭხჯჰ"),
        "country": "Грузия",
        "weight": 1.0
    },
    "Армянский язык": {
        "chars": set("աբգդեզէըթժիլխծկհձղճմյնշոչպջռսվտրցուփքօֆ"),
        "country": "Армения",
        "weight": 1.0
    }
}

def analyze_license_plates(text: str) -> list[dict]:
    """Scans for vehicle license plate codes."""
    matches = []
    # 1. Match standard suffix plate: 123 ABC 01 or 123 АБВ 01
    kz_pat_suffix = r'\b(\d{3})\s*([A-Za-zА-Яа-яЁё]{2,3})\s*(0[1-9]|1[0-9]|20)\b'
    for m in re.finditer(kz_pat_suffix, text):
        num, letters, code = m.groups()
        info = KAZAKHSTAN_OBLAST_PLATES.get(code)
        if info:
            matches.append({
                "type": "Госномер РК (Стандарт 2012+)",
                "plate": f"{num} {letters} {code}",
                "code": code,
                "region": info["region"],
                "center": info["center"],
                "lat": info["lat"],
                "lon": info["lon"],
                "status": "Активный регион",
                "confidence": "HIGH"
            })
            
    # 2. Match prefix plate: 01 123 ABC or KZ 01 123 ABC
    kz_pat_prefix = r'\b(?:KZ\s*)?(0[1-9]|1[0-9]|20)\s+(\d{3})\s+([A-Za-zА-Яа-яЁё]{2,3})\b'
    for m in re.finditer(kz_pat_prefix, text, re.IGNORECASE):
        code, num, letters = m.groups()
        info = KAZAKHSTAN_OBLAST_PLATES.get(code)
        if info and not any(x["code"] == code for x in matches):
            matches.append({
                "type": "Госномер РК (Префиксный формат)",
                "plate": f"{code} {num} {letters}",
                "code": code,
                "region": info["region"],
                "center": info["center"],
                "lat": info["lat"],
                "lon": info["lon"],
                "status": "Активный регион",
                "confidence": "HIGH"
            })

    # 3. Standalone 2-digit regional code check (requires explicit keyword prefix to avoid matching dates or house numbers)
    if not matches:
        code_pat = r'\b(?:код|регион|обл|kz|госномер|номер)\s*[:№#-]?\s*(0[1-9]|1[0-9]|20)\b'
        for m in re.finditer(code_pat, text, re.IGNORECASE):
            code = m.group(1)
            info = KAZAKHSTAN_OBLAST_PLATES.get(code)
            if info and not any(x["code"] == code for x in matches):
                matches.append({
                    "type": "Региональный автокод РК",
                    "plate": f"Код {code}",
                    "code": code,
                    "region": info["region"],
                    "center": info["center"],
                    "lat": info["lat"],
                    "lon": info["lon"],
                    "status": "Активный регион",
                    "confidence": "MEDIUM"
                })
    return matches

def analyze_script_and_language(text: str) -> list[dict]:
    """Detects unique national script letters in text."""
    results = []
    for lang, data in SCRIPT_FINGERPRINTS.items():
        found = [c for c in set(text) if c in data["chars"]]
        if found:
            results.append({
                "language": lang,
                "country": data["country"],
                "chars_detected": found,
                "count": len(found),
                "weight": data["weight"]
            })
    return results

def evaluate_photo_clues(ocr_text: str, visual_tags: list[str]) -> dict:
    """Combines all OSINT rules to extract high-confidence geographic anchors."""
    plates = analyze_license_plates(ocr_text)
    scripts = analyze_script_and_language(ocr_text)
    
    clues = []
    suggested_location = None
    kazakh_letters = []
    
    if plates:
        best_plate = plates[0]
        clues.append(f"Автомобильный номер {best_plate['plate']} указывает на регион: {best_plate['region']}.")
        suggested_location = {
            "region": best_plate["region"],
            "city": best_plate["center"],
            "lat": best_plate["lat"],
            "lon": best_plate["lon"],
            "confidence": "OSINT_HIGH"
        }
        
    for s in scripts:
        clues.append(f"Обнаружены характерные буквы ({', '.join(s['chars_detected'])}): {s['language']} ({s['country']}).")
        if s["country"] == "Казахстан":
            kazakh_letters.extend(s["chars_detected"])
            if not suggested_location:
                suggested_location = {
                    "region": "Республика Казахстан",
                    "city": "Астана",
                    "lat": 51.169392,
                    "lon": 71.449074,
                    "confidence": "OSINT_MEDIUM"
                }

    # Utility pole schemes matching
    pole_paints = []
    t_lower = ocr_text.lower()
    for scheme, reg in KZ_UTILITY_POLE_PAINT_RULES.items():
        if scheme in t_lower or any(p in t_lower for p in scheme.split(',')):
            pole_paints.append({"scheme": scheme, "region": reg})

    return {
        "plates": plates,
        "scripts": scripts,
        "clues": clues,
        "kazakh_letters": sorted(list(set(kazakh_letters))),
        "pole_paints": pole_paints,
        "suggested_location": suggested_location
    }
