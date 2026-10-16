import os
import sys
import re
import json
import math
import base64
import subprocess
import requests
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional
from PIL import Image

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
except Exception:
    pass

try:
    import torch
except ImportError:
    torch = None

try:
    import cv2
except ImportError:
    cv2 = None


def get_device():
    return torch.device("cuda" if (torch is not None and torch.cuda.is_available()) else "cpu")


def extract_multiscale_image_embedding(model_obj, img: Image.Image, device: Any) -> Any:
    """
    Генерирует взвешенный батч-эмбеддинг на GPU:
    - 50% полный кадр
    - 25% центральный кроп (фокус на архитектуре)
    - 25% полоса горизонта (горы / силуэт застройки)
    """
    w, h = img.size
    crops = [
        img,                                                                     # 1. Полный кадр
        img.crop((int(w * 0.15), int(h * 0.15), int(w * 0.85), int(h * 0.85))), # 2. Центр
        img.crop((0, int(h * 0.20), w, int(h * 0.75)))                           # 3. Линия горизонта
    ]
    weights = torch.tensor([0.50, 0.25, 0.25], device=device).unsqueeze(1)

    tensors = [model_obj.image_encoder.preprocess_image(c) for c in crops]
    batch = torch.cat(tensors, dim=0).to(device)

    with torch.no_grad():
        embs = model_obj.image_encoder(batch)
        embs = embs / embs.norm(dim=-1, keepdim=True)
        combined = (embs * weights).sum(dim=0, keepdim=True)
        combined = combined / combined.norm(dim=-1, keepdim=True)
        return combined


_OCR_READER = None


def get_ocr_reader():
    global _OCR_READER
    if _OCR_READER is None:
        try:
            import easyocr
            model_dir = Path.home() / ".EasyOCR" / "model"
            has_models = (
                model_dir.exists()
                and any(f.name.endswith((".pth", ".bin")) for f in model_dir.glob("*"))
            )
            if not has_models:
                _OCR_READER = False
                return None
            _OCR_READER = easyocr.Reader(['ru', 'en'], gpu=(torch is not None and torch.cuda.is_available()), verbose=False, download_enabled=False)
        except Exception:
            _OCR_READER = False
    return _OCR_READER if _OCR_READER is not False else None


# Стоп-слова, которые часто встречаются внутри зданий и дают ложные совпадения в OSM
INDOOR_OCR_STOPWORDS = {
    "выход", "шығу", "exit", "вход", "кіру", "enter", "welcome", "қош", "келдіңіздер",
    "касса", "туалет", "wc", "этаж", "қабат", "лифт", "акция", "скидки", "sale",
    "открыто", "ашық", "закрыто", "жабық", "меню", "menu", "coffee", "кофе",
    "чай", "tea", "open", "close", "push", "pull", "на себя", "от себя", "wifi", "wi-fi",
    "гардероб", "зал", "зона", "терминал", "банкомат", "администрация", "информация", "ақпарат",
    "стойка", "паркинг", "parking", "p1", "p2", "p3", "цоколь", "цокольный",
    "осторожно", "внимание", "намазхана", "намаз", "smoking", "курение"
}

# Казахстанские телефонные коды фиксированной связи
KZ_PHONE_CODES = {
    "727": ("Almaty", 43.2389, 76.8897),
    "7172": ("Astana", 51.1694, 71.4491),
    "7252": ("Shymkent", 42.3417, 69.5901),
    "7212": ("Karaganda", 49.8047, 73.1094),
    "7162": ("Kokshetau / Burabay", 53.0837, 70.2709),
    "7292": ("Aktau", 43.6532, 51.1691),
    "7232": ("Ust-Kamenogorsk", 49.9483, 82.6285),
    "7222": ("Semey", 50.4111, 80.2275),
    "7182": ("Pavlodar", 52.2873, 76.9674),
    "7112": ("Uralsk", 51.2333, 51.3667),
    "7132": ("Aktobe", 50.2839, 57.1670),
    "7282": ("Taldykorgan", 45.0156, 78.3739),
    "7262": ("Taraz", 42.9000, 71.3667),
    "7242": ("Kyzylorda", 44.8488, 65.4823),
    "7142": ("Kostanay", 53.2144, 63.6246),
    "7152": ("Petropavlovsk", 54.8728, 69.1430),
    "7122": ("Atyrau", 47.0945, 51.9238),
    "73522": ("Zhezkazgan", 47.7833, 67.7667),
}

# Регионы автомобильных номеров РК
KZ_PLATE_REGIONS = {
    "01": ("Astana", 51.1694, 71.4491),
    "02": ("Almaty", 43.2389, 76.8897),
    "03": ("Akmola (Kokshetau)", 53.2833, 69.3833),
    "04": ("Aktobe", 50.2839, 57.1670),
    "05": ("Almaty Region", 43.8667, 77.0833),
    "06": ("Atyrau", 47.0945, 51.9238),
    "07": ("West Kazakhstan (Uralsk)", 51.2333, 51.3667),
    "08": ("Zhambyl (Taraz)", 42.9000, 71.3667),
    "09": ("Karaganda", 49.8047, 73.1094),
    "10": ("Kostanay", 53.2144, 63.6246),
    "11": ("Kyzylorda", 44.8488, 65.4823),
    "12": ("Mangystau (Aktau)", 43.6532, 51.1691),
    "13": ("Turkestan", 43.2973, 68.2517),
    "14": ("Pavlodar", 52.2873, 76.9674),
    "15": ("North Kazakhstan (Petropavlovsk)", 54.8728, 69.1430),
    "16": ("East Kazakhstan (Ust-Kamenogorsk)", 49.9483, 82.6285),
    "17": ("Shymkent", 42.3417, 69.5901),
    "18": ("Abay (Semey)", 50.4111, 80.2275),
    "19": ("Zhetysu (Taldykorgan)", 45.0156, 78.3739),
    "20": ("Ulytau (Zhezkazgan)", 47.7833, 67.7667),
}

# Почтовые индексы РК
KZ_POSTAL_PREFIXES = {
    "01": ("Astana", 51.1694, 71.4491),
    "02": ("Almaty Region", 43.3000, 76.9000),
    "03": ("Aktobe", 50.2839, 57.1670),
    "04": ("Taldykorgan", 45.0156, 78.3739),
    "05": ("Almaty", 43.2389, 76.8897),
    "06": ("Atyrau", 47.0945, 51.9238),
    "07": ("Ust-Kamenogorsk", 49.9483, 82.6285),
    "08": ("Taraz", 42.9000, 71.3667),
    "09": ("Uralsk", 51.2333, 51.3667),
    "10": ("Karaganda", 49.8047, 73.1094),
    "11": ("Kostanay", 53.2144, 63.6246),
    "12": ("Kyzylorda", 44.8488, 65.4823),
    "13": ("Aktau", 43.6532, 51.1691),
    "14": ("Pavlodar", 52.2873, 76.9674),
    "15": ("Petropavlovsk", 54.8728, 69.1430),
    "16": ("Shymkent", 42.3417, 69.5901),
}

KAZPOST_NEW_LETTERS = {
    "A": ("Almaty", 43.2389, 76.8897),
    "Z": ("Astana", 51.1694, 71.4491),
    "B": ("Almaty Region", 43.8667, 77.0833),
    "C": ("Akmola (Kokshetau)", 53.2833, 69.3833),
    "D": ("Aktobe", 50.2839, 57.1670),
    "E": ("Atyrau", 47.0945, 51.9238),
    "F": ("East Kazakhstan", 49.9483, 82.6285),
    "H": ("Zhambyl (Taraz)", 42.9000, 71.3667),
    "L": ("West Kazakhstan (Uralsk)", 51.2333, 51.3667),
    "M": ("Karaganda", 49.8047, 73.1094),
    "P": ("Kostanay", 53.2144, 63.6246),
    "N": ("Kyzylorda", 44.8488, 65.4823),
    "R": ("Mangystau (Aktau)", 43.6532, 51.1691),
    "S": ("Pavlodar", 52.2873, 76.9674),
    "T": ("North Kazakhstan", 54.8728, 69.1430),
    "X": ("Turkestan / Shymkent", 42.3417, 69.5901),
}

# Обогащённая опорная сетка Казахстана (города, парки и ключевые природные зоны)
KZ_HUBS = [
    # 1. Бурабай / Боровое (Жумбактас, Окжетпес)
    ("Burabay (Borovoe), Zhumbaktas & Okzhetpes", 53.0837, 70.2709, 8000, 50),
    # 2. Алматы и знаковые локации
    ("Almaty City & Arbat", 43.2389, 76.8897, 20000, 180),
    ("Almaty, First President Park", 43.1903, 76.8858, 3000, 40),
    ("Almaty, Central Park (Gorky Park)", 43.2625, 76.9686, 2500, 40),
    ("Almaty, Botanical Garden", 43.2197, 76.9136, 2000, 40),
    ("Almaty, Kok-Tobe & Terrenkur", 43.2330, 76.9760, 4000, 50),
    ("Almaty, Panfilov Park & Zenkov Cathedral", 43.2588, 76.9535, 3000, 40),
    ("Almaty, Medeu High-Altitude Skating Rink", 43.1575, 77.0589, 7000, 60),
    ("Almaty, Shymbulak Ski Resort", 43.1284, 77.0811, 6000, 60),
    ("Almaty, Big Almaty Lake (BAO)", 43.0506, 76.9850, 6000, 80),
    # 3. Природные жемчужины Алматинского региона
    ("Kolsai Lakes National Park", 42.9897, 78.3256, 8000, 80),
    ("Kaindy Lake (Sunken Forest)", 42.9844, 78.4660, 6000, 80),
    ("Charyn Canyon (Valley of Castles)", 43.3550, 79.0792, 9000, 80),
    # 4. Астана (Левый берег, Байтерек, Мечеть, Ботанический)
    ("Astana, Baiterek, Central Park & Botanical Garden", 51.1280, 71.4300, 18000, 150),
    ("Astana, Grand Mosque & Expo", 51.0729, 71.4096, 12000, 120),
    # 5. Другие крупные города РК
    ("Karaganda, Central Park & City", 49.8047, 73.1094, 15000, 180),
    ("Shymkent, Parks & City", 42.3417, 69.5901, 16000, 180),
    ("Turkestan, Khoja Ahmed Yasawi Mausoleum", 43.2973, 68.2517, 10000, 120),
    ("Aktau & Caspian Sea Coast", 43.6532, 51.1691, 12000, 180),
    ("Mangystau, Bozzhira Tract (Ustyurt)", 43.4167, 54.0667, 10000, 100),
    ("Ust-Kamenogorsk & Altai Foothills", 49.9483, 82.6285, 12000, 200),
    ("East Kazakhstan, Katon-Karagay & Belukha", 49.1667, 85.6000, 12000, 120),
    ("Aktobe", 50.2839, 57.1670, 10000, 200),
    ("Taraz", 42.9000, 71.3667, 10000, 200),
    ("Pavlodar", 52.2873, 76.9674, 10000, 200),
    ("Semey", 50.4111, 80.2275, 10000, 200),
    ("Atyrau", 47.0945, 51.9238, 10000, 200),
    ("Kokshetau", 53.2833, 69.3833, 10000, 200),
    ("Kostanay", 53.2144, 63.6246, 10000, 200),
    ("Kyzylorda", 44.8488, 65.4823, 10000, 200),
    ("Uralsk", 51.2333, 51.3667, 10000, 200),
    ("Petropavlovsk", 54.8728, 69.1430, 10000, 200),
    ("Taldykorgan", 45.0156, 78.3739, 10000, 200),
]

_KZ_GALLERY_SET = False


def _build_grid(lat: float, lon: float, radius_m: float, step_m: float) -> np.ndarray:
    lat_step = 1.0 / 111320.0
    lon_step = 1.0 / (111320.0 * max(0.1, math.cos(math.radians(lat))))
    n = max(1, int(radius_m / step_m))
    y, x = np.ogrid[-n:n+1, -n:n+1]
    mask = (x * x + y * y) <= (n * n)
    dy, dx = np.where(mask)
    dy = dy - n
    dx = dx - n
    pts_lat = lat + dy * (step_m * lat_step)
    pts_lon = lon + dx * (step_m * lon_step)
    return np.column_stack((pts_lat, pts_lon)).astype(np.float32)


def _unwrap_geoclip(geoclip_model):
    for attr in [None, "model", "geoclip", "_model"]:
        obj = geoclip_model if attr is None else getattr(geoclip_model, attr, None)
        if obj is not None and (hasattr(obj, "location_encoder") or hasattr(obj, "gps_gallery") or hasattr(obj, "gps_encoder")):
            return obj
    return None


def lock_geoclip_to_kazakhstan(geoclip_model):
    """Заменяет глобальную сетку GeoCLIP на плотную сетку городов, парков и природных зон Казахстана."""
    global _KZ_GALLERY_SET
    if _KZ_GALLERY_SET or torch is None:
        return
    model_obj = _unwrap_geoclip(geoclip_model)
    if model_obj is None or not hasattr(model_obj, "gps_gallery"):
        return
    try:
        device = model_obj.gps_gallery.device
        grids = [_build_grid(lat, lon, r, s) for (_, lat, lon, r, s) in KZ_HUBS]
        kz_arr = np.vstack(grids)
        model_obj.gps_gallery = torch.tensor(kz_arr, dtype=torch.float32, device=device)
        _KZ_GALLERY_SET = True
    except Exception:
        pass


def enrich_geoclip_gallery(geoclip_model):
    """Алиас для lock_geoclip_to_kazakhstan."""
    lock_geoclip_to_kazakhstan(geoclip_model)


def detect_indoor_cv(image_path: str) -> Dict[str, Any]:
    """
    Локальная эвристика OpenCV для определения фото внутри здания с защитой ночных уличных фото:
    1. Анализ открытого неба в верхней трети кадра (sky_ratio).
    2. Анализ ночного неба: низкая средняя яркость V < 50, низкая плотность граней Canny.
    3. При ночной уличной съемке не блокирует уличную привязку.
    """
    if cv2 is None:
        return {"is_indoor_heuristic": False, "indoor_prob": 0.0, "sky_ratio": 0.0, "is_night_outdoor": False}
    try:
        img = cv2.imread(image_path)
        if img is None:
            return {"is_indoor_heuristic": False, "indoor_prob": 0.0, "sky_ratio": 0.0, "is_night_outdoor": False}

        h, w, _ = img.shape
        top_crop = img[0:max(1, int(h * 0.3)), :]
        hsv_top = cv2.cvtColor(top_crop, cv2.COLOR_BGR2HSV)

        gray_top = cv2.cvtColor(top_crop, cv2.COLOR_BGR2GRAY)
        canny_top = cv2.Canny(gray_top, 50, 150)
        edge_density_top = float(np.count_nonzero(canny_top)) / float(gray_top.size)

        v_channel = hsv_top[:, :, 2]
        mean_v_top = float(np.mean(v_channel))

        # Дневное открытое небо
        sky_mask_blue = cv2.inRange(hsv_top, (90, 30, 120), (135, 255, 255))
        if edge_density_top > 0.035:
            sky_ratio = float(np.count_nonzero(sky_mask_blue)) / float(top_crop.shape[0] * top_crop.shape[1])
        else:
            sky_mask_bright = cv2.inRange(hsv_top, (0, 0, 215), (180, 40, 255))
            sky_ratio = float(np.count_nonzero(sky_mask_blue | sky_mask_bright)) / float(top_crop.shape[0] * top_crop.shape[1])

        is_night_outdoor = False
        if sky_ratio < 0.03 and mean_v_top < 50 and edge_density_top < 0.035:
            is_night_outdoor = True

        if sky_ratio >= 0.04:
            indoor_prob = 0.15
        elif is_night_outdoor:
            indoor_prob = 0.20
        elif sky_ratio < 0.03:
            indoor_prob = 0.75
        else:
            indoor_prob = 0.45

        return {
            "is_indoor_heuristic": (indoor_prob >= 0.6) and not is_night_outdoor,
            "indoor_prob": round(indoor_prob, 2),
            "sky_ratio": round(sky_ratio, 4),
            "is_night_outdoor": is_night_outdoor,
            "top_mean_v": round(mean_v_top, 1),
            "top_edge_density": round(edge_density_top, 4),
        }
    except Exception:
        return {"is_indoor_heuristic": False, "indoor_prob": 0.0, "sky_ratio": 0.0, "is_night_outdoor": False}


def normalize_kz_address_query(text: str) -> str:
    """Нормализует казахские адресные маркеры перед отправкой в OSM."""
    t = text
    t = re.sub(r"(?i)\b(шағын\s*ауданы?|ш\/а|мкрн?|м-н)\b", "мкр.", t)
    t = re.sub(r"(?i)\b(көшесі|к-сі)\b", "улица", t)
    t = re.sub(r"(?i)\b(даңғылы|даңғ\.?)\b", "проспект", t)
    return t.strip()


def extract_kz_metadata_clues(texts: List[str]) -> Dict[str, Any]:
    """
    Ищет казахстанские микро-признаки: почтовые индексы, городские коды телефонов,
    автомобильные номера регионов и БИН/ИИН для точной географической привязки.
    """
    clues = {
        "postal_code": None,
        "phone_code": None,
        "plate_region": None,
        "bin": None,
        "inferred_city": None,
        "anchor_lat": None,
        "anchor_lon": None,
        "confidence": 0.0,
        "matched_clues": []
    }
    if not texts:
        return clues

    joined = " ".join([str(t) for t in texts])

    # 1. Почтовые индексы (старый 6-значный 010000..169999)
    m_post_old = re.search(r"\b(0[1-9]|1[0-6])\d{4}\b", joined)
    if m_post_old:
        code = m_post_old.group(0)
        prefix = code[:2]
        if prefix in KZ_POSTAL_PREFIXES:
            city_name, lat, lon = KZ_POSTAL_PREFIXES[prefix]
            clues["postal_code"] = code
            clues["inferred_city"] = city_name
            clues["anchor_lat"] = lat
            clues["anchor_lon"] = lon
            clues["confidence"] = 0.90
            clues["matched_clues"].append(f"Postal Code {code} -> {city_name}")

    # Новый 7-значный индекс Казпочты (например, A05B2Y3)
    if not clues["postal_code"]:
        m_post_new = re.search(r"\b([A-Z])\d{2}[A-Z0-9]{4}\b", joined)
        if m_post_new:
            code = m_post_new.group(0)
            first_letter = code[0]
            if first_letter in KAZPOST_NEW_LETTERS:
                city_name, lat, lon = KAZPOST_NEW_LETTERS[first_letter]
                clues["postal_code"] = code
                clues["inferred_city"] = city_name
                clues["anchor_lat"] = lat
                clues["anchor_lon"] = lon
                clues["confidence"] = 0.88
                clues["matched_clues"].append(f"Kazpost {code} -> {city_name}")

    # 2. Телефонные коды городов (+7 727, (7172), 8(7252))
    for code, (city_name, lat, lon) in KZ_PHONE_CODES.items():
        pattern = rf"(?:\+7|8)[\s\-\(]*{code}[\s\-\)]*\d+"
        if re.search(pattern, joined):
            clues["phone_code"] = code
            if not clues["inferred_city"]:
                clues["inferred_city"] = city_name
                clues["anchor_lat"] = lat
                clues["anchor_lon"] = lon
                clues["confidence"] = 0.85
            clues["matched_clues"].append(f"Phone Code {code} -> {city_name}")
            break

    # 3. Автомобильные номера РК (123 ABC 02 или 02 | 123 ABC)
    plate_match = re.search(r"\b\d{3}\s?[A-Z]{2,3}\s?(0[1-9]|1[0-9]|20)\b", joined) or \
                  re.search(r"\b(0[1-9]|1[0-9]|20)\s?\|\s?\d{3}\s?[A-Z]{2,3}\b", joined)
    if plate_match:
        reg = plate_match.group(1)
        if reg in KZ_PLATE_REGIONS:
            city_name, lat, lon = KZ_PLATE_REGIONS[reg]
            clues["plate_region"] = reg
            if not clues["inferred_city"]:
                clues["inferred_city"] = city_name
                clues["anchor_lat"] = lat
                clues["anchor_lon"] = lon
                clues["confidence"] = 0.80
            clues["matched_clues"].append(f"License Plate Region {reg} -> {city_name}")

    # 4. БИН / ИИН (12 цифр)
    bin_match = re.search(r"\b(БИН|ИИН|BIN|IIN)[:\s]*([0-9]{12})\b", joined, re.IGNORECASE)
    if bin_match:
        clues["bin"] = bin_match.group(2)
        clues["matched_clues"].append(f"Kazakh Fiscal BIN: {clues['bin']}")

    return clues


def search_overpass_brand_cluster(
    brands: List[str],
    city_lat: float,
    city_lon: float,
    radius_m: int = 15000,
    cluster_radius_m: int = 120
) -> Optional[Dict[str, Any]]:
    """
    Ищет пространственное пересечение брендов/магазинов/кафе (co-occurrence) внутри одного ТРЦ/БЦ.
    Если >= 2 брендов из разных категорий находятся в радиусе 120м друг от друга — сужает координаты до 35м.
    """
    clean_brands = []
    seen = set()
    for b in brands:
        cb = re.sub(r"[^\w\s\-\.]", "", str(b)).strip()
        low = cb.lower()
        if len(cb) >= 3 and low not in INDOOR_OCR_STOPWORDS and low not in seen:
            seen.add(low)
            clean_brands.append(cb)

    if len(clean_brands) < 2:
        return None

    escaped = [re.escape(b) for b in clean_brands[:8]]
    brand_regex = "|".join(escaped)

    overpass_query = f"""
    [out:json][timeout:10];
    (
      node["name"~"({brand_regex})",i](around:{radius_m},{city_lat},{city_lon});
      way["name"~"({brand_regex})",i](around:{radius_m},{city_lat},{city_lon});
      node["brand"~"({brand_regex})",i](around:{radius_m},{city_lat},{city_lon});
      way["brand"~"({brand_regex})",i](around:{radius_m},{city_lat},{city_lon});
      node["shop"~"({brand_regex})",i](around:{radius_m},{city_lat},{city_lon});
      way["shop"~"({brand_regex})",i](around:{radius_m},{city_lat},{city_lon});
      node["amenity"~"({brand_regex})",i](around:{radius_m},{city_lat},{city_lon});
      way["amenity"~"({brand_regex})",i](around:{radius_m},{city_lat},{city_lon});
    );
    out center tags 40;
    """

    headers = {"User-Agent": "GeoSleuthResearch/3.2 (brand-clustering)"}
    try:
        r = requests.post("https://overpass-api.de/api/interpreter", data={"data": overpass_query}, headers=headers, timeout=10)
        if not r.ok:
            return None
        elements = r.json().get("elements", [])
        if len(elements) < 2:
            return None

        points = []
        for el in elements:
            lat = el.get("lat") or el.get("center", {}).get("lat")
            lon = el.get("lon") or el.get("center", {}).get("lon")
            if lat is None or lon is None:
                continue
            tags = el.get("tags", {})
            name = tags.get("name") or tags.get("brand") or tags.get("operator") or ""
            matched_brand = None
            for cb in clean_brands:
                if cb.lower() in name.lower() or cb.lower() in tags.get("brand", "").lower():
                    matched_brand = cb
                    break
            if not matched_brand:
                matched_brand = name

            points.append({
                "lat": float(lat),
                "lon": float(lon),
                "brand": matched_brand,
                "name": name,
                "building": tags.get("building") or tags.get("mall") or tags.get("amenity")
            })

        def haversine_m(lat1, lon1, lat2, lon2):
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            a = math.sin(dlat / 2.0)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            return 6371000 * c

        best_cluster = None
        min_cluster_dist = 999999

        for i in range(len(points)):
            for j in range(i + 1, len(points)):
                p1, p2 = points[i], points[j]
                if p1["brand"].lower() == p2["brand"].lower():
                    continue
                dist = haversine_m(p1["lat"], p1["lon"], p2["lat"], p2["lon"])
                if dist <= cluster_radius_m:
                    if dist < min_cluster_dist:
                        min_cluster_dist = dist
                        best_cluster = (p1, p2, dist)

        if best_cluster:
            p1, p2, dist = best_cluster
            cl_lat = (p1["lat"] + p2["lat"]) / 2.0
            cl_lon = (p1["lon"] + p2["lon"]) / 2.0
            brand_label = f"ТРЦ / Торговый кластер ({p1['brand']} + {p2['brand']})"
            return {
                "lat": round(cl_lat, 6),
                "lon": round(cl_lon, 6),
                "radius_m": 35,
                "name": brand_label,
                "matched_brands": [p1["brand"], p2["brand"]],
                "distance_m": round(dist, 1),
                "method": "Indoor Brand Cluster (Overpass)"
            }
    except Exception:
        pass
    return None


def fetch_mapillary_street_view(lat: float, lon: float, radius_m: int = 50, limit: int = 3) -> List[Dict[str, Any]]:
    """
    Запрашивает ближайшие снимки Street View из Mapillary Graph API для визуального подтверждения точки.
    """
    token = os.getenv("MAPILLARY_TOKEN") or os.getenv("MAPILLARY_ACCESS_TOKEN", "")
    token = token.strip().strip('"').strip("'")
    if not token:
        return []

    url = "https://graph.mapillary.com/images"
    params = {
        "fields": "id,computed_geometry,thumb_1024_url,compass_angle",
        "closeto": f"{lon},{lat}",
        "limit": limit,
    }
    headers = {"Authorization": f"OAuth {token}"}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=5)
        if not r.ok:
            params["access_token"] = token
            r = requests.get(url, params=params, timeout=5)

        if r.ok:
            data = r.json().get("data", [])
            matches = []
            for item in data:
                geom = item.get("computed_geometry", {}).get("coordinates", [])
                matches.append({
                    "id": item.get("id"),
                    "lon": geom[0] if len(geom) > 0 else lon,
                    "lat": geom[1] if len(geom) > 1 else lat,
                    "thumb_url": item.get("thumb_1024_url"),
                    "compass_angle": item.get("compass_angle"),
                })
            return matches
    except Exception:
        pass
    return []


def analyze_with_gemini_vision(image_path: str) -> Dict[str, Any]:
    """
    Использует GEMINI_API_KEY для:
    1) Распознавания типа сцены (is_indoor vs outdoor).
    2) Window View анализа: силуэт гор Заилийского Алатау, Байтерек, Есентай, Хан Шатыр, солнце.
    3) Определения известных интерьеров (ТРЦ, аэропорты, станции, кафе).
    4) Защиты от угадывания случайных координат на типовых интерьерах (ставит lat/lon в null).
    5) Извлечения поисковых запросов и брендов для OpenStreetMap.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip().strip('"').strip("'")
    if not api_key:
        for p in [".env", "../.env", "../../.env"]:
            if os.path.isfile(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip().startswith("GEMINI_API_KEY="):
                                api_key = line.strip().split("=", 1)[1].strip().strip('"').strip("'")
                                os.environ["GEMINI_API_KEY"] = api_key
                                break
                except Exception:
                    pass
            if api_key:
                break

    if not api_key:
        return {"status": "skipped", "reason": "No GEMINI_API_KEY"}

    try:
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")

        prompt = (
            "You are an expert OSINT geolocator specializing in Kazakhstan (Almaty, Astana, Shymkent, Burabay, Karaganda, city parks, streets, buildings) and CIS.\n"
            "First, determine if the photo is taken INDOORS (inside a building, mall, cafe, office, room, station, airport) or OUTDOORS (street, park, nature, facade).\n\n"
            "If INDOORS:\n"
            "1. Inspect mall atrium architecture (e.g. MEGA Alma-Ata, MEGA Silk Way, Dostyk Plaza, Khan Shatyr, Esentai Mall, Forum), "
            "storefront brand names, posters, signs, or receipts.\n"
            "2. WINDOW VIEW ANALYSIS: If windows or balconies are visible, carefully inspect the view outside: "
            "mountains (Zailiyskiy Alatau south of Almaty, Burabay granite rocks, flat steppe of Astana), "
            "prominent towers (Esentai Tower, Almaty Towers, KazZhol, Abu Dhabi Plaza, Khan Shatyr, Baiterek, Kok-Tobe TV Tower).\n"
            "3. DO NOT guess random coordinates if the room is generic or unidentifiable — set lat and lon to null if confidence is below 0.65.\n\n"
            "ALMATY MOUNTAIN BEARING & SECTOR TRIANGULATION (CRITICAL FOR ALMATY & FOOTHILLS):\n"
            "If analyzing a photo in Almaty, from a window/balcony, or with mountains visible in Kazakhstan:\n"
            "1. Detect visibility of Zailiyskiy Alatau mountain ridge and/or Kok-Tobe TV Tower (the southern horizon of Almaty).\n"
            "2. Determine shooting direction and angle towards the mountains (e.g. 'Looking South towards mountains', 'Looking South-East towards Kok-Tobe', 'Looking North away from mountains').\n"
            "3. Determine the estimated city sector based on distance and perspective to the mountain ridge:\n"
            "   - 'Верхняя часть / Медеу' (close towering slopes, foothills, Dostyk / Al-Farabi / Baganashyl / Medeu; lat ~43.215, lon ~76.945)\n"
            "   - 'Центр' (mid-distance mountain ridge panorama, Abay / Satpayev / Panfilov / Arbat; lat ~43.245, lon ~76.930)\n"
            "   - 'Нижняя часть' (distant low mountains over flat urban plains, Rayimbek / Sayakhat / Almaty-1; lat ~43.310, lon ~76.940)\n\n"
            "If OUTDOORS:\n"
            "Identify the exact landmark, park, street, building, or nature spot.\n\n"
            "Return ONLY valid JSON matching this schema:\n"
            "{\n"
            '  "is_indoor": true/false,\n'
            '  "scene_type": "mall|cafe|office|residential|station|airport|street|park|nature",\n'
            '  "confidence": 0.85,\n'
            '  "place_name": "exact name or null",\n'
            '  "city": "city or null",\n'
            '  "country": "Kazakhstan",\n'
            '  "osm_search_query": "search query for OpenStreetMap",\n'
            '  "lat": 43.2389_or_null,\n'
            '  "lon": 76.8897_or_null,\n'
            '  "radius_m": 30,\n'
            '  "search_queries": ["identifiable brand, mall, landmark or window view"],\n'
            '  "detected_text": ["visible text"],\n'
            '  "almaty_mountain_bearing": {\n'
            '    "mountain_visible": true/false,\n'
            '    "kok_tobe_visible": true/false,\n'
            '    "shooting_angle": "Looking South toward Zailiyskiy Alatau",\n'
            '    "city_sector": "Верхняя часть / Медеу|Центр|Нижняя часть",\n'
            '    "sector_lat": 43.215_or_null,\n'
            '    "sector_lon": 76.945_or_null,\n'
            '    "notes": "mountain distance and perspective description"\n'
            '  },\n'
            '  "window_view": {\n'
            '    "has_window_view": true/false,\n'
            '    "window_landmarks": ["landmark name"],\n'
            '    "azimuth_deg": 180,\n'
            '    "notes": "description"\n'
            '  }\n'
            "}"
        )
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/jpeg", "data": b64}}
                ]
            }],
            "generationConfig": {"temperature": 0.1, "response_mime_type": "application/json"}
        }

        models_to_try = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.0-flash"]
        last_err = ""

        for model_name in models_to_try:
            endpoints = [
                (f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}", {}),
                (f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent", {"x-goog-api-key": api_key}),
            ]
            for url, headers in endpoints:
                try:
                    r = requests.post(url, json=payload, headers=headers, timeout=10)

                    if r.ok:
                        candidate = r.json().get("candidates", [{}])[0]
                        parts = candidate.get("content", {}).get("parts", [])
                        txt = "\n".join([p.get("text", "") for p in parts if "text" in p])
                        m = re.search(r"\{.*\}", txt, re.S)
                        if m:
                            data = json.loads(m.group(0))
                            has_coords = data.get("lat") is not None and data.get("lon") is not None
                            conf = float(data.get("confidence") or (0.85 if has_coords else 0.0))
                            if has_coords and conf >= 0.65:
                                return {"status": "ok", "data": data}
                            return {"status": "indoor_or_uncertain", "data": data}
                    else:
                        last_err = f"HTTP {r.status_code}: {r.text[:150]}"
                except Exception as ex:
                    last_err = str(ex)

        return {"status": "error", "error": last_err}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def extract_text_from_photo(image_path: str, is_indoor: bool = False) -> List[str]:
    """
    Локальное чтение русского, казахского и английского текста на фото.
    При is_indoor фильтрует бытовые таблички ('выход', 'касса', 'акция').
    """
    reader = get_ocr_reader()
    if reader is None or cv2 is None:
        return []
    found: List[str] = []
    try:
        img = cv2.imread(image_path)
        if img is None:
            return []
        h, w = img.shape[:2]
        crops = [
            img,
            cv2.resize(img[0:int(h * 0.35), :], None, fx=1.6, fy=1.6, interpolation=cv2.INTER_CUBIC),
            cv2.resize(img[int(h * 0.65):h, :], None, fx=1.6, fy=1.6, interpolation=cv2.INTER_CUBIC),
        ]
        seen = set()
        for crop in crops:
            for item in reader.readtext(crop, detail=1, paragraph=True):
                txt = item[1].strip() if len(item) > 1 else ""
                txt = re.sub(r"[^\w\s\-\.,№/а-яА-ЯёЁәіңғүұқөһӘІҢҒҮҰҚӨҺ]", " ", txt)
                txt = re.sub(r"\s+", " ", txt).strip()
                low = txt.lower()
                if len(txt) >= 3 and low not in seen:
                    if low in INDOOR_OCR_STOPWORDS:
                        continue
                    if is_indoor and len(txt) < 4:
                        if not any(token in low for token in ["пр", "ул", "к-сі", "д.", "мкр"]):
                            continue
                    seen.add(low)
                    found.append(txt)
    except Exception:
        pass
    return found


def geocode_in_kazakhstan(
    candidates: List[str],
    is_indoor: bool = False,
    city_lat: Optional[float] = None,
    city_lon: Optional[float] = None
) -> Optional[Dict[str, Any]]:
    """Ищет адрес, название объекта или ТРЦ по карте Казахстана (Nominatim + Overpass API)."""
    headers = {"User-Agent": "GeoSleuthResearchKZ/3.2 (indoor-protected)"}
    queries: List[str] = []
    for c in candidates:
        clean = re.sub(r"[^\w\s\-\.,№/а-яА-ЯёЁәіңғүұқөһӘІҢҒҮҰҚӨҺ]", " ", str(c)).strip()
        clean = normalize_kz_address_query(clean)
        low = clean.lower()
        if len(clean) >= 3 and low not in INDOOR_OCR_STOPWORDS:
            if is_indoor and len(clean) < 4:
                continue
            queries.append(clean)

    if len(queries) >= 2:
        queries.insert(0, f"{queries[0]} {queries[1]}")

    viewbox_params = {}
    if city_lat is not None and city_lon is not None:
        deg = 20.0 / 111.32
        viewbox_params = {
            "viewbox": f"{city_lon - deg},{city_lat + deg},{city_lon + deg},{city_lat - deg}",
            "bounded": 0,
        }

    for q in queries[:12]:
        try:
            params = {
                "q": q,
                "countrycodes": "kz",
                "format": "jsonv2",
                "limit": 3,
                "addressdetails": 1,
                **viewbox_params
            }
            r = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params=params,
                headers=headers,
                timeout=6,
            )
            if r.ok and r.json():
                hit = r.json()[0]
                return {
                    "lat": float(hit["lat"]),
                    "lon": float(hit["lon"]),
                    "name": hit.get("display_name", q),
                    "matched_query": q,
                    "radius_m": 50 if is_indoor else 15,
                }
        except Exception:
            pass

        if len(q) >= 4:
            overpass_q = f"""
            [out:json][timeout:8];
            area["ISO3166-1"="KZ"]->.kz;
            (
              node["name"~"{q}",i](area.kz);
              way["name"~"{q}",i](area.kz);
              relation["name"~"{q}",i](area.kz);
            );
            out center 3;
            """
            try:
                r = requests.post("https://overpass-api.de/api/interpreter", data={"data": overpass_q}, timeout=8)
                if r.ok:
                    els = r.json().get("elements", [])
                    if els:
                        el = els[0]
                        lat = el.get("lat") or el.get("center", {}).get("lat")
                        lon = el.get("lon") or el.get("center", {}).get("lon")
                        if lat and lon:
                            return {
                                "lat": float(lat),
                                "lon": float(lon),
                                "name": f"{el.get('tags', {}).get('name', q)}, Казахстан",
                                "matched_query": q,
                                "radius_m": 50 if is_indoor else 15,
                            }
            except Exception:
                pass
    return None


def refine_dense_grid_gpu(
    geoclip_model,
    image_path: str,
    center_lat: float,
    center_lon: float,
    is_indoor: bool = False
) -> dict:
    if is_indoor:
        return {
            "status": "skipped_indoor",
            "lat": center_lat,
            "lon": center_lon,
            "radius_m": 2500,
            "warning": "Снимок внутри помещения: уличная сетка отключена."
        }

    model_obj = _unwrap_geoclip(geoclip_model)
    if model_obj is None or torch is None or not torch.cuda.is_available():
        return refine_dense_grid_cpu(geoclip_model, image_path, center_lat, center_lon, is_indoor)

    device = get_device()
    try:
        if next(model_obj.parameters()).device != device:
            model_obj.to(device)
    except Exception:
        pass

    loc_enc = getattr(model_obj, "gps_encoder", getattr(model_obj, "location_encoder", None))
    if loc_enc is None:
        return refine_dense_grid_cpu(geoclip_model, image_path, center_lat, center_lon, is_indoor)

    try:
        img = Image.open(image_path).convert("RGB")
        img_emb = extract_multiscale_image_embedding(model_obj, img, device)

        # Проход 1: Ультраплотная сетка на GPU: радиус 5 км с шагом 50 м (~31 400 точек)
        pts1 = _build_grid(center_lat, center_lon, radius_m=5000, step_m=50)
        t_pts1 = torch.tensor(pts1, dtype=torch.float32, device=device)

        with torch.no_grad():
            loc_emb1 = loc_enc(t_pts1)
            loc_emb1 = loc_emb1 / loc_emb1.norm(dim=-1, keepdim=True)
            scores1 = (img_emb @ loc_emb1.T).squeeze(0)
            best_idx1 = int(torch.argmax(scores1).item())
            max_score = float(scores1[best_idx1].item())

            # Гейтинг уверенности: если max_score < 0.21 -> блокировать ложное сужение
            if max_score < 0.21:
                return {
                    "status": "low_confidence",
                    "lat": center_lat,
                    "lon": center_lon,
                    "radius_m": 2500,
                    "score": round(max_score, 4),
                    "device": "cuda",
                    "warning": "Низкая уверенность визуальной привязки (score < 0.21)."
                }

            mid_lat, mid_lon = float(pts1[best_idx1][0]), float(pts1[best_idx1][1])

            # Проход 2: микро-сетка 300 м с шагом 10 м (итоговая точность radius_m: 15)
            pts2 = _build_grid(mid_lat, mid_lon, radius_m=300, step_m=10)
            t_pts2 = torch.tensor(pts2, dtype=torch.float32, device=device)
            loc_emb2 = loc_enc(t_pts2)
            loc_emb2 = loc_emb2 / loc_emb2.norm(dim=-1, keepdim=True)
            scores2 = (img_emb @ loc_emb2.T).squeeze(0)
            best_idx2 = int(torch.argmax(scores2).item())

            return {
                "status": "ok",
                "lat": float(pts2[best_idx2][0]),
                "lon": float(pts2[best_idx2][1]),
                "score": round(float(scores2[best_idx2].item()), 4),
                "radius_m": 15,
                "device": "cuda"
            }
    except Exception:
        return refine_dense_grid_cpu(geoclip_model, image_path, center_lat, center_lon, is_indoor)


def refine_dense_grid_cpu(
    geoclip_model,
    image_path: str,
    base_lat: float,
    base_lon: float,
    is_indoor: bool = False
) -> Dict[str, Any]:
    if is_indoor:
        return {
            "status": "skipped_indoor",
            "lat": base_lat,
            "lon": base_lon,
            "radius_m": 2500,
            "warning": "Снимок сделан внутри помещения: уличная сетка GeoCLIP отключена во избежание ложной точки."
        }

    model_obj = _unwrap_geoclip(geoclip_model)
    if model_obj is None or torch is None:
        return {"status": "skipped", "lat": base_lat, "lon": base_lon, "radius_m": 250}

    try:
        device = next(model_obj.parameters()).device
        img = Image.open(image_path).convert("RGB")
        img_tensor = model_obj.image_encoder.preprocess_image(img).unsqueeze(0).to(device)

        with torch.no_grad():
            img_emb = model_obj.image_encoder(img_tensor)
            img_emb = img_emb / img_emb.norm(dim=-1, keepdim=True)

            g = _build_grid(base_lat, base_lon, radius_m=450, step_m=15)
            t = torch.tensor(g, dtype=torch.float32, device=device)
            loc_enc = getattr(model_obj, "location_encoder", getattr(model_obj, "gps_encoder", None))
            loc_emb = loc_enc(t)
            loc_emb = loc_emb / loc_emb.norm(dim=-1, keepdim=True)
            scores = (img_emb @ loc_emb.T).squeeze(0)
            idx = int(torch.argmax(scores).item())
            best_score = float(scores[idx].item())

            if best_score < 0.21:
                return {
                    "status": "low_visual_confidence",
                    "lat": base_lat,
                    "lon": base_lon,
                    "score": round(best_score, 4),
                    "radius_m": 2000,
                    "warning": "Низкая уверенность визуальной привязки (возможно, фото внутри помещения или крупный план)."
                }

            return {
                "status": "ok",
                "lat": float(g[idx][0]),
                "lon": float(g[idx][1]),
                "score": round(best_score, 4),
                "radius_m": 15,
                "device": "cpu"
            }
    except Exception as e:
        return {"status": "error", "lat": base_lat, "lon": base_lon, "radius_m": 150, "error": str(e)}


def refine_dense_grid(
    geoclip_model,
    image_path: str,
    base_lat: float,
    base_lon: float,
    is_indoor: bool = False
) -> Dict[str, Any]:
    if is_indoor:
        return {
            "status": "skipped_indoor",
            "lat": base_lat,
            "lon": base_lon,
            "radius_m": 2500,
            "warning": "Снимок внутри помещения: уличная сетка отключена."
        }
    if torch is not None and torch.cuda.is_available():
        return refine_dense_grid_gpu(geoclip_model, image_path, base_lat, base_lon, is_indoor)
    return refine_dense_grid_cpu(geoclip_model, image_path, base_lat, base_lon, is_indoor)


def locate_exact_spot(geoclip_model, image_path: str, city_lat: float, city_lon: float) -> Dict[str, Any]:
    """
    Главный конвейер геолокации с поддержкой глубоких модулей:
    1. OpenCV эвристика интерьера с защитой ночных уличных фото (detect_indoor_cv).
    2. Gemini Vision v3.2 (детекция indoor/outdoor, окно/панорама гор, вывески, бренды).
    3. Парсер казахстанских микро-признаков (индексы, телефонные коды, номера авто).
    4. Пространственное пересечение брендов (Overpass API Brand Cluster -> точность 35м).
    5. Верификация через Mapillary Street-View (при radius_m <= 150).
    6. Алматинский горный пеленг (триангуляция секторов города).
    7. Двухэтапная ультраплотная GPU-сетка GeoCLIP (точность до 15м).
    """
    if geoclip_model is not None:
        enrich_geoclip_gallery(geoclip_model)

    # 0. Локальная эвристика интерьера с защитой ночной улицы
    cv_indoor = detect_indoor_cv(image_path)
    is_indoor = cv_indoor.get("is_indoor_heuristic", False)
    is_night_outdoor = cv_indoor.get("is_night_outdoor", False)

    # 1. Gemini Vision v3.2 (определение места, вывесок, окна, проверка indoor/outdoor)
    vlm = analyze_with_gemini_vision(image_path)
    vlm_data = vlm.get("data", {}) if isinstance(vlm.get("data"), dict) else {}

    if vlm_data.get("is_indoor") is not None:
        if is_night_outdoor and not vlm_data.get("is_indoor"):
            is_indoor = False
        else:
            is_indoor = bool(vlm_data.get("is_indoor"))

    # Извлекаем OCR текст заранее
    ocr_texts = extract_text_from_photo(image_path, is_indoor=is_indoor)
    all_texts = ocr_texts + vlm_data.get("detected_text", [])

    # 2. Парсер казахстанских микро-признаков (индексы, автономера, коды телефонов)
    kz_clues = extract_kz_metadata_clues(all_texts)
    if kz_clues.get("anchor_lat") and kz_clues.get("anchor_lon"):
        if not (40.0 <= city_lat <= 56.0 and 46.0 <= city_lon <= 88.0) or kz_clues.get("confidence", 0) >= 0.85:
            city_lat = kz_clues["anchor_lat"]
            city_lon = kz_clues["anchor_lon"]

    # 3. Window View Analysis: если из окна видны горы или знаковые высотки
    window_view = vlm_data.get("window_view", {})
    if window_view.get("has_window_view") and window_view.get("window_landmarks"):
        window_queries = [str(lm) for lm in window_view["window_landmarks"] if lm]
        win_hit = geocode_in_kazakhstan(window_queries, is_indoor=False, city_lat=city_lat, city_lon=city_lon)
        if win_hit:
            street_views = fetch_mapillary_street_view(win_hit["lat"], win_hit["lon"])
            return {
                "exact_lat": win_hit["lat"],
                "exact_lon": win_hit["lon"],
                "radius_m": 75,
                "is_indoor": is_indoor,
                "matched_label": f"Вид из окна на {win_hit['name']}",
                "method": f"Window View Landmark: «{win_hit['matched_query']}»",
                "street_view_matches": street_views,
                "diagnostics": {
                    "gemini_vision": vlm_data,
                    "window_view": window_view,
                    "osm_refined": win_hit,
                    "kz_clues": kz_clues,
                    "cv_indoor": cv_indoor
                }
            }

    # 4. Пространственное пересечение брендов (Overpass API Brand Cluster -> 35м)
    if is_indoor:
        brand_candidates = []
        for b in vlm_data.get("search_queries", []) + ocr_texts + vlm_data.get("detected_text", []):
            if b and str(b).lower() not in INDOOR_OCR_STOPWORDS:
                brand_candidates.append(str(b))

        brand_cluster = search_overpass_brand_cluster(brand_candidates, city_lat, city_lon, radius_m=15000, cluster_radius_m=120)
        if brand_cluster:
            street_views = fetch_mapillary_street_view(brand_cluster["lat"], brand_cluster["lon"])
            return {
                "exact_lat": brand_cluster["lat"],
                "exact_lon": brand_cluster["lon"],
                "radius_m": 35,
                "is_indoor": True,
                "scene_type": vlm_data.get("scene_type", "mall"),
                "matched_label": brand_cluster["name"],
                "method": "Indoor Brand Cluster (Overpass)",
                "street_view_matches": street_views,
                "diagnostics": {
                    "brand_cluster": brand_cluster,
                    "gemini_vision": vlm_data,
                    "kz_clues": kz_clues,
                    "cv_indoor": cv_indoor
                }
            }

    # 4b. Горный пеленг для Алматы
    mountain_bearing = vlm_data.get("almaty_mountain_bearing", {})
    sector_name = mountain_bearing.get("city_sector") if isinstance(mountain_bearing, dict) else None
    has_mountain = bool(mountain_bearing.get("mountain_visible") or mountain_bearing.get("kok_tobe_visible")) if isinstance(mountain_bearing, dict) else False
    is_almaty_area = (
        (43.10 <= city_lat <= 43.45 and 76.70 <= city_lon <= 77.15)
        or (vlm_data.get("city") and "almaty" in str(vlm_data.get("city")).lower())
        or has_mountain
    )

    almaty_sector_applied = None
    if is_almaty_area and sector_name:
        s_low = str(sector_name).lower()
        if "верхн" in s_low or "медеу" in s_low or "самал" in s_low or "аль-фараби" in s_low:
            almaty_sector_applied = "Верхняя часть / Медеу"
            sector_lat, sector_lon = 43.2150, 76.9450
        elif "нижн" in s_low or "турксиб" in s_low or "жетысу" in s_low or "райымбек" in s_low:
            almaty_sector_applied = "Нижняя часть"
            sector_lat, sector_lon = 43.3100, 76.9400
        elif "центр" in s_low or "алмалы" in s_low or "бостандык" in s_low:
            almaty_sector_applied = "Центр"
            sector_lat, sector_lon = 43.2450, 76.9300
        else:
            sector_lat, sector_lon = None, None

        if sector_lat and sector_lon:
            if not (vlm.get("status") == "ok" and vlm_data.get("lat") and float(vlm_data.get("confidence", 0)) >= 0.75):
                city_lat = sector_lat
                city_lon = sector_lon

    # 5. Прямой результат Gemini Vision с высокой уверенностью
    if vlm.get("status") == "ok" and vlm_data.get("lat") and vlm_data.get("lon"):
        v_lat, v_lon = float(vlm_data["lat"]), float(vlm_data["lon"])
        osm_q = [
            q for q in [vlm_data.get("osm_search_query"), vlm_data.get("place_name")]
            + vlm_data.get("search_queries", [])
            + vlm_data.get("detected_text", [])
            if q and str(q).lower() not in INDOOR_OCR_STOPWORDS
        ]
        osm_hit = geocode_in_kazakhstan(osm_q, is_indoor=is_indoor, city_lat=v_lat, city_lon=v_lon)
        if osm_hit:
            v_lat, v_lon = osm_hit["lat"], osm_hit["lon"]

        label = f"{vlm_data.get('place_name', '')}, {vlm_data.get('city', 'Kazakhstan')}".strip(", ")
        rad = int(vlm_data.get("radius_m", 50 if is_indoor else 15))
        street_views = fetch_mapillary_street_view(v_lat, v_lon) if rad <= 150 else []
        return {
            "exact_lat": v_lat,
            "exact_lon": v_lon,
            "radius_m": rad,
            "is_indoor": is_indoor,
            "scene_type": vlm_data.get("scene_type", "indoor" if is_indoor else "outdoor"),
            "matched_label": label,
            "method": f"Gemini Vision + OSM: {label}",
            "street_view_matches": street_views,
            "diagnostics": {
                "gemini_vision": vlm_data,
                "mountain_bearing": mountain_bearing,
                "osm_refined": osm_hit,
                "kz_clues": kz_clues,
                "cv_indoor": cv_indoor
            }
        }

    # 6. Поиск известных ТРЦ/аэропортов/станций по названиям брендов
    if is_indoor and vlm_data.get("search_queries"):
        indoor_osm_hit = geocode_in_kazakhstan(
            vlm_data.get("search_queries"),
            is_indoor=True,
            city_lat=city_lat,
            city_lon=city_lon
        )
        if indoor_osm_hit:
            street_views = fetch_mapillary_street_view(indoor_osm_hit["lat"], indoor_osm_hit["lon"])
            return {
                "exact_lat": indoor_osm_hit["lat"],
                "exact_lon": indoor_osm_hit["lon"],
                "radius_m": 50,
                "is_indoor": True,
                "scene_type": vlm_data.get("scene_type", "indoor"),
                "matched_label": indoor_osm_hit["name"],
                "method": f"Indoor Landmark Search: «{indoor_osm_hit['matched_query']}»",
                "street_view_matches": street_views,
                "diagnostics": {
                    "gemini_vision": vlm_data,
                    "matched_poi": indoor_osm_hit,
                    "kz_clues": kz_clues,
                    "cv_indoor": cv_indoor
                }
            }

    # 7. Локальный OCR поиск по вывескам/табличкам
    ocr_hit = geocode_in_kazakhstan(ocr_texts, is_indoor=is_indoor, city_lat=city_lat, city_lon=city_lon)
    if ocr_hit:
        street_views = fetch_mapillary_street_view(ocr_hit["lat"], ocr_hit["lon"])
        return {
            "exact_lat": ocr_hit["lat"],
            "exact_lon": ocr_hit["lon"],
            "radius_m": 50 if is_indoor else 15,
            "is_indoor": is_indoor,
            "matched_label": ocr_hit["name"],
            "method": f"OCR Text/Address Match: «{ocr_hit['matched_query']}»",
            "street_view_matches": street_views,
            "diagnostics": {
                "ocr_texts": ocr_texts,
                "matched_place": ocr_hit,
                "kz_clues": kz_clues,
                "is_indoor": is_indoor,
                "gemini_status": vlm
            }
        }

    # 8. GeoCLIP доводка с защитой от ошибок на интерьерах
    grid_res = refine_dense_grid(geoclip_model, image_path, city_lat, city_lon, is_indoor=is_indoor)

    # Формируем итоговый вердикт
    if is_indoor:
        method_name = "Indoor Scene Detected (City Anchor)"
        warning_msg = grid_res.get("warning", "Снимок внутри помещения: уличный радиус заблокирован.")
        street_views = []
    elif grid_res.get("status") in ("low_visual_confidence", "low_confidence"):
        method_name = "Low Confidence Visual Anchor (City Level)"
        warning_msg = grid_res.get("warning")
        street_views = []
    elif almaty_sector_applied:
        method_name = f"Almaty Mountain Bearing ({almaty_sector_applied}) + Outdoor Grid (15m)"
        warning_msg = None
        street_views = fetch_mapillary_street_view(grid_res.get("lat", city_lat), grid_res.get("lon", city_lon))
    else:
        method_name = "Kazakhstan Outdoor Grid (15m)"
        warning_msg = None
        street_views = fetch_mapillary_street_view(grid_res.get("lat", city_lat), grid_res.get("lon", city_lon))

    return {
        "exact_lat": grid_res.get("lat", city_lat),
        "exact_lon": grid_res.get("lon", city_lon),
        "radius_m": grid_res.get("radius_m", 2500 if is_indoor else 15),
        "is_indoor": is_indoor,
        "matched_label": None,
        "method": method_name,
        "warning": warning_msg,
        "street_view_matches": street_views,
        "diagnostics": {
            "is_indoor": is_indoor,
            "cv_indoor": cv_indoor,
            "kz_clues": kz_clues,
            "gemini_status": vlm,
            "mountain_bearing": mountain_bearing,
            "ocr_texts": ocr_texts,
            "dense_grid": grid_res,
        },
    }
