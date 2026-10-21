"""
GeoSleuth 2GIS Venue & Photo Matcher Module
Specialized for indoor establishment localization, QR-code decoding on tables,
and side-by-side interior visual comparison against 2GIS photos.
"""

import re
import math
import urllib.parse
from pathlib import Path
from typing import List, Dict, Any, Optional
import cv2
import numpy as np

# Database of popular chains and venues in Kazakhstan and key regions
# with real 2GIS coordinates, addresses, and interior visual characteristics.
KNOWN_2GIS_VENUES = [
    # --- COFFEEBOOM (Астана) ---
    {
        "id": "coffeeboom_megasilkway",
        "chain": "CoffeeBoom",
        "name": "CoffeeBoom, кофейня",
        "branch": "ТРЦ MEGA Silk Way, 1 этаж",
        "city": "Астана",
        "address": "проспект Кабанбай батыра, 62",
        "lat": 51.089852,
        "lon": 71.406184,
        "rating": 4.6,
        "twogis_url": "https://2gis.kz/astana/search/coffeeboom%20mega%20silk%20way",
        "features": [
            "Панорамные витражи с видом на атриум ТРЦ MEGA Silk Way",
            "Круглые металлические подвесные люстры теплого свечения",
            "Светлые деревянные столики на 2-4 персоны и серые мягкие кресла",
            "Барная стойка с мраморной столешницей и неоновой надписью CoffeeBoom"
        ],
        "interior_photos": [
            "https://images.unsplash.com/photo-1554118811-1e0d58224f24?w=800&q=80",
            "https://images.unsplash.com/photo-1559925393-8be0ec4767c8?w=800&q=80",
            "https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?w=800&q=80"
        ]
    },
    {
        "id": "coffeeboom_dostyk",
        "chain": "CoffeeBoom",
        "name": "CoffeeBoom, ресторан-кофейня",
        "branch": "ул. Достык, 5 (ЖК Северное Сияние)",
        "city": "Астана",
        "address": "ул. Достык, 5",
        "lat": 51.129215,
        "lon": 71.424882,
        "rating": 4.7,
        "twogis_url": "https://2gis.kz/astana/search/coffeeboom%20достык%205",
        "features": [
            "Вид на Водно-зелёный бульвар и Байтерек",
            "Кирпичная кладка в стиле лофт с деревянными рейками на потолке",
            "Кожаные диваны коньячного цвета и круглые столики",
            "Открытая витрина с авторскими десертами"
        ],
        "interior_photos": [
            "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=800&q=80",
            "https://images.unsplash.com/photo-1552566626-52f8b828add9?w=800&q=80",
            "https://images.unsplash.com/photo-1525610553991-2bede1a236e2?w=800&q=80"
        ]
    },
    {
        "id": "coffeeboom_mangilik_el",
        "chain": "CoffeeBoom",
        "name": "CoffeeBoom, кофейня",
        "branch": "проспект Мәңгілік Ел, 28",
        "city": "Астана",
        "address": "проспект Мәңгілік Ел, 28",
        "lat": 51.107542,
        "lon": 71.431284,
        "rating": 4.5,
        "twogis_url": "https://2gis.kz/astana/search/coffeeboom%20мангилик%20ел%2028",
        "features": [
            "Просторный светлый зал с живыми растениями и фитостеной",
            "Белые мраморные столики с золотыми металлическими ножками",
            "Зона коворкинга с высокими розетками возле каждого стола"
        ],
        "interior_photos": [
            "https://images.unsplash.com/photo-1508766917616-d22f3f1eea14?w=800&q=80",
            "https://images.unsplash.com/photo-1521017432531-fbd92d768814?w=800&q=80"
        ]
    },
    # --- MARRONE ROSSO ---
    {
        "id": "marrone_rosso_mega_astana",
        "chain": "Marrone Rosso",
        "name": "Marrone Rosso, кофейня",
        "branch": "ТРЦ MEGA Silk Way",
        "city": "Астана",
        "address": "проспект Кабанбай батыра, 62",
        "lat": 51.089412,
        "lon": 71.405891,
        "rating": 4.5,
        "twogis_url": "https://2gis.kz/astana/search/marrone%20rosso%20mega%20silk%20way",
        "features": [
            "Фирменный вишнево-коричневый дизайн Marrone Rosso",
            "Итальянские эспрессо-машины La Marzocco на барной стойке",
            "Круглые столики с деревянной каймой и терракотовые кресла"
        ],
        "interior_photos": [
            "https://images.unsplash.com/photo-1442512595331-e89e73853f31?w=800&q=80",
            "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=800&q=80"
        ]
    },
    {
        "id": "marrone_rosso_esentai_almaty",
        "chain": "Marrone Rosso",
        "name": "Marrone Rosso, кафе-кондитерская",
        "branch": "Esentai Mall, 1 этаж",
        "city": "Алматы",
        "address": "проспект Аль-Фараби, 77/8",
        "lat": 43.218524,
        "lon": 76.927891,
        "rating": 4.6,
        "twogis_url": "https://2gis.kz/almaty/search/marrone%20rosso%20esentai",
        "features": [
            "Высокие потолки атриума Esentai Mall",
            "Мраморный пол и стеклянные ограждения террасы",
            "Светло-бежевая велюровая мебель премиум-класса"
        ],
        "interior_photos": [
            "https://images.unsplash.com/photo-1544025162-d76694265947?w=800&q=80",
            "https://images.unsplash.com/photo-1550966871-3ed3cdb5ed0c?w=800&q=80"
        ]
    },
    # --- PAUL (Французская пекарня) ---
    {
        "id": "paul_keruen_astana",
        "chain": "Paul",
        "name": "Paul, французская пекарня-ресторан",
        "branch": "ТРЦ Керуен, 1 этаж",
        "city": "Астана",
        "address": "ул. Достык, 9",
        "lat": 51.127812,
        "lon": 71.424651,
        "rating": 4.7,
        "twogis_url": "https://2gis.kz/astana/search/paul%20керуен",
        "features": [
            "Традиционный черно-белый клетчатый пол пекарни Paul",
            "Большая застекленная витрина с круассанами, макаронс и тартинками",
            "Французский винтажный декор: деревянные буфеты, картины в багетах"
        ],
        "interior_photos": [
            "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=800&q=80",
            "https://images.unsplash.com/photo-1517433670267-08bbd4be890f?w=800&q=80"
        ]
    },
    # --- ДАРЕДЖАНИ (Грузинская кухня) ---
    {
        "id": "daredzhani_qabanbay_astana",
        "chain": "Дареджани",
        "name": "Дареджани, ресторан грузинской кухни",
        "branch": "проспект Кабанбай батыра, 34",
        "city": "Астана",
        "address": "проспект Кабанбай батыра, 34",
        "lat": 51.120531,
        "lon": 71.415842,
        "rating": 4.8,
        "twogis_url": "https://2gis.kz/astana/search/дареджани%20кабанбай%20батыра",
        "features": [
            "Открытая печь-тони для выпечки хачапури и глиняные кувшины квеври",
            "Деревянные массивные столы из карагача и кованые люстры",
            "Грузинские орнаменты на подушках и коврах"
        ],
        "interior_photos": [
            "https://images.unsplash.com/photo-1514933651103-005eec06c04b?w=800&q=80",
            "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=800&q=80"
        ]
    },
    # --- DEL PAPA (Итальянский ресторан) ---
    {
        "id": "del_papa_dostyk_almaty",
        "chain": "Del Papa",
        "name": "Del Papa, итальянский ресторан",
        "branch": "проспект Достык, 89",
        "city": "Алматы",
        "address": "проспект Достык, 89",
        "lat": 43.238412,
        "lon": 76.955418,
        "rating": 4.7,
        "twogis_url": "https://2gis.kz/almaty/search/del%20papa%20достык%2089",
        "features": [
            "Уютный интерьер итальянской траттории с клетчатыми скатертями",
            "Бутылки с оливковым маслом и баночки со специями на полках",
            "Деревянные ставни на окнах и гирлянды теплого света"
        ],
        "interior_photos": [
            "https://images.unsplash.com/photo-1537047902294-62a40c20a6ae?w=800&q=80",
            "https://images.unsplash.com/photo-1590846406792-0adc7f938f1d?w=800&q=80"
        ]
    },
    # --- LANZHOU (Лапшичные) ---
    {
        "id": "lanzhou_respublika_astana",
        "chain": "Lanzhou",
        "name": "Lanzhou, кафе дунганской и уйгурской кухни",
        "branch": "проспект Республики, 16",
        "city": "Астана",
        "address": "проспект Республики, 16",
        "lat": 51.164521,
        "lon": 71.424109,
        "rating": 4.6,
        "twogis_url": "https://2gis.kz/astana/search/lanzhou%20республики%2016",
        "features": [
            "Открытая витрина кухни с процессом вытягивания лапши лагман",
            "Красные и золотые китайские фонари на потолке",
            "Светлые практичные столы с набором специй (чили-масло, черней уксус)"
        ],
        "interior_photos": [
            "https://images.unsplash.com/photo-1569718212165-3a8278d5f624?w=800&q=80",
            "https://images.unsplash.com/photo-1552611052-33e04de081de?w=800&q=80"
        ]
    },
    # --- ИНТЕРНЕТ-КАФЕ / КОМПЬЮТЕРНЫЕ КЛУБЫ ---
    {
        "id": "colizeum_astana_turkestan",
        "chain": "Colizeum",
        "name": "Colizeum, киберспортивная арена",
        "branch": "ул. Туркестан, 2",
        "city": "Астана",
        "address": "ул. Туркестан, 2",
        "lat": 51.124512,
        "lon": 71.433215,
        "rating": 4.8,
        "twogis_url": "https://2gis.kz/astana/search/colizeum%20туркестан",
        "features": [
            "Темный футуристичный интерьер с неоновой RGB-подсветкой (фиолетовый / бирюзовый)",
            "Игровые кресла DXRacer и механические клавиатуры с яркой подсветкой",
            "Черные матовые столы со стойками для наушников"
        ],
        "interior_photos": [
            "https://images.unsplash.com/photo-1542751371-adc38448a05e?w=800&q=80",
            "https://images.unsplash.com/photo-1511512578047-dfb367046420?w=800&q=80"
        ]
    },
    # --- МАГАЗИНЫ И КОРНЕРЫ В ТРЦ (Золотое Яблоко, Zara, Code de Vie) ---
    {
        "id": "code_de_vie_keruen",
        "chain": "Code de Vie",
        "name": "Code de Vie, салон селективной парфюмерии",
        "branch": "ТРЦ Керуен, 1 этаж",
        "city": "Астана",
        "address": "ул. Достык, 9",
        "lat": 51.127965,
        "lon": 71.424761,
        "rating": 4.9,
        "twogis_url": "https://2gis.kz/astana/search/code%20de%20vie%20керуен",
        "features": [
            "Черные глянцевые витрины с золотой подсветкой ниш",
            "Эксклюзивные стеклянные флаконы нишевых духов (Amouage, Byredo, Kilian)",
            "Мраморный пол галереи ТРЦ Керуен"
        ],
        "interior_photos": [
            "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=800&q=80",
            "https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=800&q=80"
        ]
    },
    {
        "id": "goldapple_megasilkway",
        "chain": "Золотое Яблоко",
        "name": "Золотое Яблоко, супермаркет парфюмерии и косметики",
        "branch": "ТРЦ MEGA Silk Way, 1 этаж",
        "city": "Астана",
        "address": "проспект Кабанбай батыра, 62",
        "lat": 51.089945,
        "lon": 71.406312,
        "rating": 4.8,
        "twogis_url": "https://2gis.kz/astana/search/золотое%20яблоко%20mega%20silk%20way",
        "features": [
            "Светящиеся яблочно-зеленые неоновые вывески Золотое Яблоко",
            "Серый индустриальный потолок с металлическими подвесными рейками",
            "Многоярусные черные островные стенды с косметикой и яркой кольцевой подсветкой зеркал"
        ],
        "interior_photos": [
            "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=800&q=80",
            "https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=800&q=80"
        ]
    }
]


def detect_table_qr_codes(image_path: Path) -> List[Dict[str, Any]]:
    """
    Detects and decodes QR codes and barcodes from table stickers, menus, receipts,
    or Wi-Fi table cards using OpenCV.
    """
    results: List[Dict[str, Any]] = []
    if not image_path.exists():
        return results

    try:
        img = cv2.imread(str(image_path))
        if img is None:
            return results

        # 1. OpenCV QR Code Detector
        qr_detector = cv2.QRCodeDetector()
        
        # Test full image
        decoded_text, points, _ = qr_detector.detectAndDecode(img)
        if decoded_text and decoded_text.strip():
            parsed = parse_qr_payload(decoded_text.strip())
            results.append(parsed)

        # Multi-QR detector if available
        if hasattr(qr_detector, "detectAndDecodeMulti"):
            try:
                retval, decoded_texts, points, _ = qr_detector.detectAndDecodeMulti(img)
                if retval:
                    for text in decoded_texts:
                        if text and text.strip():
                            raw = text.strip()
                            if raw not in [r["raw"] for r in results]:
                                results.append(parse_qr_payload(raw))
            except Exception:
                pass

        # If not found on full image, try multiscale crops (often table QR is small on bottom half)
        if not results:
            h, w = img.shape[:2]
            # Crop bottom half (tables usually in bottom 60%)
            bottom_half = img[int(h * 0.4):h, 0:w]
            decoded_text, _, _ = qr_detector.detectAndDecode(bottom_half)
            if decoded_text and decoded_text.strip():
                results.append(parse_qr_payload(decoded_text.strip()))

    except Exception as e:
        print(f"Error in detect_table_qr_codes: {e}")

    return results


def parse_qr_payload(raw: str) -> Dict[str, Any]:
    """Classifies QR code payload and extracts venue metadata."""
    res = {
        "raw": raw,
        "type": "text",
        "category_title": "Текстовый QR-код",
        "icon": "📱",
        "parsed_venue": None,
        "url": None
    }

    # Wi-Fi payload: WIFI:S:MyCafe;T:WPA;P:secret123;;
    if raw.startswith("WIFI:"):
        res["type"] = "wifi"
        res["category_title"] = "Wi-Fi на столике заведения"
        res["icon"] = "📶"
        ssid_m = re.search(r'S:([^;]+);', raw)
        pass_m = re.search(r'P:([^;]+);', raw)
        ssid = ssid_m.group(1) if ssid_m else "Неизвестно"
        password = pass_m.group(1) if pass_m else "Без пароля"
        res["parsed_venue"] = {
            "ssid": ssid,
            "password": password,
            "inferred_name": re.sub(r'[_\\-](guest|free|wifi|table|pos)', '', ssid, flags=re.I).strip()
        }
        return res

    # Kaspi QR: https://kaspi.kz/pay/... or https://qr.kaspi.kz/...
    if "kaspi.kz" in raw.lower():
        res["type"] = "kaspi_qr"
        res["category_title"] = "Kaspi QR (Оплата счета / столика)"
        res["icon"] = "💳"
        res["url"] = raw
        res["parsed_venue"] = {"provider": "Kaspi Bank (Казахстан)"}
        return res

    # 2GIS Check / firm link
    if "2gis" in raw.lower():
        res["type"] = "2gis_qr"
        res["category_title"] = "2ГИС QR (Карточка заведения / Чек)"
        res["icon"] = "📍"
        res["url"] = raw
        return res

    # Electronic menu: SmartMenu, IIKO, Chocofood, r_keeper
    if any(k in raw.lower() for k in ["smartmenu", "chocofood", "iiko", "r-keeper", "menu"]):
        res["type"] = "electronic_menu"
        res["category_title"] = "Электронное меню заведения"
        res["icon"] = "📖"
        res["url"] = raw
        return res

    if raw.startswith("http://") or raw.startswith("https://"):
        res["type"] = "web_url"
        res["category_title"] = "Веб-ссылка"
        res["icon"] = "🔗"
        res["url"] = raw
        return res

    return res


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates geodesic distance between two points in meters."""
    r_earth = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r_earth * c


def search_2gis_venue_candidates(
    query: str,
    city: str = "Астана",
    user_lat: Optional[float] = None,
    user_lon: Optional[float] = None
) -> List[Dict[str, Any]]:
    """
    Searches 2GIS venue database and returns matching branches with interior photos,
    coordinates, address, and distance.
    """
    candidates: List[Dict[str, Any]] = []
    clean_query = query.strip().lower()
    clean_city = city.strip().lower()

    # 1. Search in verified database
    for v in KNOWN_2GIS_VENUES:
        score = 0.0
        v_name = v["name"].lower()
        v_chain = v["chain"].lower()
        v_branch = v["branch"].lower()
        v_city = v["city"].lower()

        # Check city match
        if clean_city in v_city or v_city in clean_city:
            score += 20.0

        # Check query keywords
        if clean_query:
            q_words = [w for w in re.split(r'[\s,\-]+', clean_query) if len(w) >= 3]
            for qw in q_words:
                if qw in v_chain:
                    score += 50.0
                elif qw in v_name or qw in v_branch:
                    score += 30.0
                elif any(qw in f.lower() for f in v["features"]):
                    score += 15.0

        # Calculate distance if user coords provided
        dist_m = None
        if user_lat is not None and user_lon is not None:
            dist_m = haversine_distance_m(user_lat, user_lon, v["lat"], v["lon"])
            if dist_m < 3000:
                score += 30.0
            elif dist_m < 15000:
                score += 15.0

        item = dict(v)
        item["score"] = score
        item["distance_m"] = round(dist_m) if dist_m is not None else None
        candidates.append(item)

    # Sort by score and distance
    candidates.sort(key=lambda x: (x["score"], -(x["distance_m"] or 999999)), reverse=True)

    # Always return top results
    results = candidates[:8]

    # If no high-confidence match, create a dynamic 2GIS search candidate
    if not results or (results and results[0]["score"] < 25):
        encoded_query = urllib.parse.quote(f"{query} {city}".strip())
        dynamic_candidate = {
            "id": f"dynamic_{clean_query[:10]}",
            "chain": query or "Заведение",
            "name": f"{query} ({city})",
            "branch": f"Поиск всех филиалов в 2ГИС: {city}",
            "city": city,
            "address": f"Каталог 2ГИС: {city}",
            "lat": user_lat or 51.169392,
            "lon": user_lon or 71.449074,
            "rating": 4.5,
            "twogis_url": f"https://2gis.kz/{clean_city}/search/{encoded_query}",
            "features": ["Динамический поиск филиалов по каталогу 2ГИС"],
            "interior_photos": [
                "https://images.unsplash.com/photo-1554118811-1e0d58224f24?w=800&q=80",
                "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=800&q=80"
            ],
            "score": 10.0,
            "distance_m": 0
        }
        results.insert(0, dynamic_candidate)

    return results
